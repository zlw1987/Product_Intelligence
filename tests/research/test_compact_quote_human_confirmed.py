"""Tests for the human-confirmed Compact Quote projection (PROD-FIX1,
defect 4 — research/projection layer).

A valid run-scoped, human-CONFIRMED semantic candidate MAY contribute to the
Compact Quote for that SAME ResearchRun. Human confirmation establishes
IDENTITY authority only — it must NEVER invent or upgrade other facts:

* price/currency come from the persisted PriceIntelligenceSnapshot
  assessment (exactly the frozen normalized values);
* condition is EXACTLY the persisted normalized condition (UNKNOWN stays
  "Unknown" — never upgraded to Yes);
* a confirmed candidate without persisted price/currency evidence produces
  NO row;
* the projection is display-only: it cannot mutate the frozen 4A artifact.
"""

from __future__ import annotations

from decimal import Decimal

import pytest

from product_intelligence.domain import ResearchRequest
from product_intelligence.domain.enums import (
    ConfidenceLevel,
    EvidenceDecision,
    IdentityMatchType,
    VerificationStatus,
)
from product_intelligence.research.aggregation import (
    PriceAggregateBucket,
    PriceAggregationResult,
)
from product_intelligence.research.compact_quote import (
    CompactQuoteProjectionError,
    project_ai_assisted_rows,
    project_human_confirmed_rows,
    project_public_rows,
)
from product_intelligence.research.fx_codec import FxObservationSnapshot, FxRateEntry
from product_intelligence.research.listings import (
    ExtractionMethod,
    ListingObservation,
)
from product_intelligence.research.matching import (
    EvidenceSource,
    IdentityRejectionReason,
    ListingIdentityAssessment,
)
from product_intelligence.research.normalization import (
    NormalizedAvailability,
    NormalizedCondition,
    NormalizedListingObservation,
)


# ---------------------------------------------------------------------------
# Builders
# ---------------------------------------------------------------------------


def _semantic_assessment(
    mpn: str,
    *,
    source_url: str,
    price_amount: "Decimal | None" = Decimal("1890.00"),
    currency_code: "str | None" = "USD",
    condition: NormalizedCondition = NormalizedCondition.UNKNOWN,
    availability: NormalizedAvailability = NormalizedAvailability.UNKNOWN,
    reason: IdentityRejectionReason = (
        IdentityRejectionReason.NO_EXPLICIT_MPN_EVIDENCE
    ),
    evidence_source: EvidenceSource = EvidenceSource.TITLE_TEXT,
) -> ListingIdentityAssessment:
    """One semantic-eligible REJECTED assessment (frozen FU3B shape)."""
    obs = ListingObservation(
        source_url=source_url,
        extraction_method=ExtractionMethod.JSON_LD,
        product_title=f"Listing for {mpn}",
        manufacturer_part_number_text="",
        sku_text=None,
        brand_text=None,
        price_text=str(price_amount) if price_amount is not None else None,
        currency_text=currency_code,
        availability_text="Unknown",
        condition_text="unknown",
        seller_text="Some Seller",
        offer_url_text=None,
        raw_reference=None,
    )
    norm = NormalizedListingObservation(
        observation=obs,
        price_amount=price_amount,
        currency_code=currency_code,
        availability=availability,
        condition=condition,
        seller_name="Some Seller",
        normalization_issues=(),
    )
    return ListingIdentityAssessment(
        normalized_listing=norm,
        requested_part_number=mpn,
        # The title publishes the requested MPN token; _find_evidence
        # derives (TITLE_TEXT, requested_mpn) from the observation.
        candidate_part_number_raw=mpn,
        candidate_part_number_compared=mpn,
        candidate_evidence_source=evidence_source,
        match_type=IdentityMatchType.UNKNOWN,
        decision=EvidenceDecision.REJECTED,
        rejection_reason=reason,
    )


def _accepted_assessment(
    mpn: str,
    *,
    source_url: str,
    price: Decimal = Decimal("100.00"),
    currency: str = "USD",
) -> ListingIdentityAssessment:
    obs = ListingObservation(
        source_url=source_url,
        extraction_method=ExtractionMethod.JSON_LD,
        product_title=f"Accepted for {mpn}",
        manufacturer_part_number_text=mpn,
        sku_text=None,
        brand_text=None,
        price_text=str(price),
        currency_text=currency,
        availability_text="In Stock",
        condition_text="New",
        seller_text=None,
        offer_url_text=None,
        raw_reference=None,
    )
    norm = NormalizedListingObservation(
        observation=obs,
        price_amount=price,
        currency_code=currency,
        availability=NormalizedAvailability.IN_STOCK,
        condition=NormalizedCondition.NEW,
        seller_name=None,
        normalization_issues=(),
    )
    return ListingIdentityAssessment(
        normalized_listing=norm,
        requested_part_number=mpn,
        candidate_part_number_raw=mpn,
        candidate_part_number_compared=mpn,
        candidate_evidence_source=EvidenceSource.EXPLICIT_MPN_FIELD,
        match_type=IdentityMatchType.EXACT,
        decision=EvidenceDecision.ACCEPTED,
        rejection_reason=None,
    )


def _make_result(
    mpn: str,
    assessments: tuple,
    buckets: "tuple | None" = None,
) -> PriceAggregationResult:
    """Build a contract-valid PriceAggregationResult.

    Every input assessment must appear in exactly one bucket or exclusion
    (frozen 4A invariant). Non-bucket assessments are excluded with the
    correct 4A reason: REJECTED -> IDENTITY_NOT_ACCEPTED; ACCEPTED -> the
    first failing price-eligibility reason.
    """
    from product_intelligence.research.aggregation import (
        PriceAggregationExclusion,
        PriceAggregationExclusionReason,
    )

    if buckets is None:
        buckets = ()
    buckets = tuple(buckets)
    if not buckets:
        status = VerificationStatus.UNKNOWN
    elif len(buckets) == 1:
        status = VerificationStatus.VERIFIED
    else:
        status = VerificationStatus.AMBIGUOUS

    bucketed = set()
    for bucket in buckets:
        for a in bucket.assessments:
            bucketed.add(a)

    exclusions = []
    for assessment in assessments:
        if assessment in bucketed:
            continue
        if assessment.decision is not EvidenceDecision.ACCEPTED:
            exclusions.append(
                PriceAggregationExclusion(
                    assessment=assessment,
                    reason=PriceAggregationExclusionReason.IDENTITY_NOT_ACCEPTED,
                )
            )
        else:
            norm = assessment.normalized_listing
            if norm.price_amount is None:
                reason = PriceAggregationExclusionReason.NO_NUMERIC_PRICE
            elif norm.currency_code is None:
                reason = PriceAggregationExclusionReason.NO_COMPARABLE_CURRENCY
            elif norm.condition is NormalizedCondition.UNKNOWN:
                reason = PriceAggregationExclusionReason.UNKNOWN_CONDITION
            else:
                raise AssertionError(
                    "accepted, price-eligible assessment must be in a bucket"
                )
            exclusions.append(
                PriceAggregationExclusion(assessment=assessment, reason=reason)
            )

    return PriceAggregationResult(
        request=ResearchRequest(manufacturer_part_number=mpn, description="x"),
        assessments=assessments,
        buckets=buckets,
        exclusions=tuple(exclusions),
        verification_status=status,
    )


def _fx_snapshot() -> FxObservationSnapshot:
    return FxObservationSnapshot(
        provider_id="ECB",
        observation_date="2026-09-23",
        base_currency="EUR",
        rates=(
            FxRateEntry(currency_code="USD", rate=Decimal("1.0934")),
            FxRateEntry(currency_code="EUR", rate=Decimal("1")),
        ),
        retrieved_at="2026-09-23T12:00:00+00:00",
    )


MPN = "HC-MPN-001"


# ---------------------------------------------------------------------------
# Core projection behavior
# ---------------------------------------------------------------------------


class TestHumanConfirmedProjection:
    def test_unknown_condition_renders_unknown_never_upgraded(self) -> None:
        """Candidate: price 1890 USD, condition UNKNOWN, human confirmed.
        Compact Quote may show the price with Brand New = Unknown and
        explicit Human Confirmed provenance — NEVER Yes/NEW."""
        sem = _semantic_assessment(MPN, source_url="https://one.example.com/a")
        result = _make_result(MPN, (sem,))
        rows = project_human_confirmed_rows(result, frozenset({0}))
        assert len(rows) == 1
        row = rows[0]
        assert row.source_type == "HUMAN_CONFIRMED"
        assert row.price_amount == Decimal("1890.00")
        assert row.price_currency == "USD"
        assert row.price_original == "$1,890.00 USD"
        assert row.brand_new == "Unknown"
        assert row.condition == "UNKNOWN"
        assert row.assessment_index == 0
        assert "Human Confirmed" in (row.note or "")
        assert row.source == "one.example.com"

    def test_new_condition_renders_yes_truthfully(self) -> None:
        """Candidate: price 1635 USD, condition NEW, human confirmed.
        May truthfully show Brand New = Yes with Human Confirmed provenance."""
        sem = _semantic_assessment(
            MPN,
            source_url="https://two.example.com/b",
            price_amount=Decimal("1635.00"),
            condition=NormalizedCondition.NEW,
        )
        result = _make_result(MPN, (sem,))
        rows = project_human_confirmed_rows(result, frozenset({0}))
        assert len(rows) == 1
        row = rows[0]
        assert row.price_original == "$1,635.00 USD"
        assert row.brand_new == "Yes"
        assert row.note == "Human Confirmed"

    def test_used_condition_renders_no(self) -> None:
        sem = _semantic_assessment(
            MPN,
            source_url="https://three.example.com/c",
            price_amount=Decimal("500.00"),
            condition=NormalizedCondition.USED,
        )
        result = _make_result(MPN, (sem,))
        rows = project_human_confirmed_rows(result, frozenset({0}))
        assert rows[0].brand_new == "No"

    def test_missing_price_produces_no_row(self) -> None:
        """Confirmation cannot create price evidence that did not exist."""
        sem = _semantic_assessment(MPN, source_url="https://four.example.com", price_amount=None)
        result = _make_result(MPN, (sem,))
        rows = project_human_confirmed_rows(result, frozenset({0}))
        assert rows == ()

    def test_missing_currency_produces_no_row(self) -> None:
        sem = _semantic_assessment(MPN, source_url="https://five.example.com", currency_code=None)
        result = _make_result(MPN, (sem,))
        rows = project_human_confirmed_rows(result, frozenset({0}))
        assert rows == ()

    def test_empty_index_set_projects_no_rows(self) -> None:
        sem = _semantic_assessment(MPN, source_url="https://six.example.com")
        result = _make_result(MPN, (sem,))
        assert project_human_confirmed_rows(result, frozenset()) == ()

    def test_multiple_indices_deterministic_order(self) -> None:
        sem0 = _semantic_assessment(
            MPN, source_url="https://a.example.com/0",
            price_amount=Decimal("10.00"),
        )
        sem1 = _semantic_assessment(
            MPN, source_url="https://b.example.com/1",
            price_amount=Decimal("20.00"),
        )
        result = _make_result(MPN, (sem0, sem1))
        rows = project_human_confirmed_rows(result, frozenset({1, 0}))
        assert [r.price_amount for r in rows] == [Decimal("10.00"), Decimal("20.00")]
        assert rows[0].source == "a.example.com"
        assert rows[1].source == "b.example.com"

    def test_usd_equivalent_from_persisted_fx(self) -> None:
        sem = _semantic_assessment(
            MPN,
            source_url="https://eur.example.com/e",
            price_amount=Decimal("962.86"),
            currency_code="EUR",
            condition=NormalizedCondition.NEW,
        )
        result = _make_result(MPN, (sem,))
        rows = project_human_confirmed_rows(
            result, frozenset({0}), fx_snapshot=_fx_snapshot()
        )
        assert rows[0].usd_equivalent_amount == Decimal("962.86") * Decimal("1.0934")

    def test_no_fx_evidence_usd_only_passthrough(self) -> None:
        sem = _semantic_assessment(
            MPN,
            source_url="https://usd.example.com/u",
            price_amount=Decimal("1890.00"),
        )
        result = _make_result(MPN, (sem,))
        rows = project_human_confirmed_rows(result, frozenset({0}))
        # USD pass-through requires no FX evidence
        assert rows[0].usd_equivalent == "$1,890.00 USD"
        assert rows[0].usd_equivalent_amount == Decimal("1890.00")

    def test_non_usd_without_fx_unavailable(self) -> None:
        sem = _semantic_assessment(
            MPN,
            source_url="https://zar.example.com/z",
            price_amount=Decimal("30999.0"),
            currency_code="ZAR",
        )
        result = _make_result(MPN, (sem,))
        rows = project_human_confirmed_rows(result, frozenset({0}))
        assert rows[0].usd_equivalent == "Unavailable"
        assert rows[0].usd_equivalent_amount is None
        # ZAR formatting: code rendered once
        assert rows[0].price_original == "ZAR 30,999.0"

    def test_availability_persisted_value_used(self) -> None:
        sem = _semantic_assessment(
            MPN,
            source_url="https://stock.example.com/s",
            availability=NormalizedAvailability.IN_STOCK,
        )
        result = _make_result(MPN, (sem,))
        rows = project_human_confirmed_rows(result, frozenset({0}))
        assert rows[0].inventory == "In Stock"
        # No availability note + provenance note
        assert rows[0].note == "Human Confirmed"

    def test_availability_note_combined_with_provenance(self) -> None:
        sem = _semantic_assessment(
            MPN,
            source_url="https://limited.example.com/l",
            availability=NormalizedAvailability.LIMITED,
        )
        result = _make_result(MPN, (sem,))
        rows = project_human_confirmed_rows(result, frozenset({0}))
        assert rows[0].inventory == "In Stock"
        assert rows[0].note == "Limited; Human Confirmed"


# ---------------------------------------------------------------------------
# Fail-closed authority checks
# ---------------------------------------------------------------------------


class TestFailClosed:
    def test_duck_typed_price_result_rejected(self) -> None:
        class FakeResult:
            assessments = ()

        with pytest.raises(CompactQuoteProjectionError, match="PriceAggregationResult"):
            project_human_confirmed_rows(FakeResult(), frozenset())

    def test_non_frozenset_rejected(self) -> None:
        sem = _semantic_assessment(MPN, source_url="https://x.example.com")
        result = _make_result(MPN, (sem,))
        with pytest.raises(CompactQuoteProjectionError, match="frozenset"):
            project_human_confirmed_rows(result, {0})
        with pytest.raises(CompactQuoteProjectionError, match="frozenset"):
            project_human_confirmed_rows(result, (0,))

    def test_non_int_index_rejected(self) -> None:
        sem = _semantic_assessment(MPN, source_url="https://x.example.com")
        result = _make_result(MPN, (sem,))
        with pytest.raises(CompactQuoteProjectionError, match="int"):
            project_human_confirmed_rows(result, frozenset({"0"}))

    def test_bool_index_rejected(self) -> None:
        """bool is a subclass of int — must be rejected by exact type."""
        sem = _semantic_assessment(MPN, source_url="https://x.example.com")
        result = _make_result(MPN, (sem,))
        with pytest.raises(CompactQuoteProjectionError, match="int"):
            project_human_confirmed_rows(result, frozenset({True}))

    def test_out_of_range_index_rejected(self) -> None:
        sem = _semantic_assessment(MPN, source_url="https://x.example.com")
        result = _make_result(MPN, (sem,))
        with pytest.raises(CompactQuoteProjectionError, match="out of range"):
            project_human_confirmed_rows(result, frozenset({5}))
        with pytest.raises(CompactQuoteProjectionError, match="out of range"):
            project_human_confirmed_rows(result, frozenset({-1}))

    def test_accepted_assessment_cannot_be_quoted(self) -> None:
        """A human confirmation of a NON semantic-eligible assessment can
        never enter the Compact Quote (fail closed). An ACCEPTED listing is
        not human-review eligible — even a stale/foreign CONFIRMED
        candidate bound to its index cannot produce a row."""
        obs = ListingObservation(
            source_url="https://acc.example.com",
            extraction_method=ExtractionMethod.JSON_LD,
            product_title="Accepted product",
            manufacturer_part_number_text=MPN,
            sku_text=None,
            brand_text=None,
            price_text="100.00",
            currency_text="USD",
            availability_text="In Stock",
            condition_text="unknown",
            seller_text=None,
            offer_url_text=None,
            raw_reference=None,
        )
        norm = NormalizedListingObservation(
            observation=obs,
            price_amount=Decimal("100.00"),
            currency_code="USD",
            availability=NormalizedAvailability.IN_STOCK,
            condition=NormalizedCondition.UNKNOWN,
            seller_name=None,
            normalization_issues=(),
        )
        acc = ListingIdentityAssessment(
            normalized_listing=norm,
            requested_part_number=MPN,
            candidate_part_number_raw=MPN,
            candidate_part_number_compared=MPN,
            candidate_evidence_source=EvidenceSource.EXPLICIT_MPN_FIELD,
            match_type=IdentityMatchType.EXACT,
            decision=EvidenceDecision.ACCEPTED,
            rejection_reason=None,
        )
        result = _make_result(MPN, (acc,))
        with pytest.raises(CompactQuoteProjectionError, match="human-review"):
            project_human_confirmed_rows(result, frozenset({0}))

    def test_mpn_mismatch_rejection_not_eligible(self) -> None:
        obs = ListingObservation(
            source_url="https://mm.example.com",
            extraction_method=ExtractionMethod.JSON_LD,
            product_title="Other product",
            manufacturer_part_number_text="OTHER-MPN-999",
            sku_text=None,
            brand_text=None,
            price_text="100.00",
            currency_text="USD",
            availability_text="In Stock",
            condition_text="New",
            seller_text=None,
            offer_url_text=None,
            raw_reference=None,
        )
        norm = NormalizedListingObservation(
            observation=obs,
            price_amount=Decimal("100.00"),
            currency_code="USD",
            availability=NormalizedAvailability.IN_STOCK,
            condition=NormalizedCondition.NEW,
            seller_name=None,
            normalization_issues=(),
        )
        sem = ListingIdentityAssessment(
            normalized_listing=norm,
            requested_part_number=MPN,
            candidate_part_number_raw="OTHER-MPN-999",
            candidate_part_number_compared="OTHER-MPN-999",
            candidate_evidence_source=EvidenceSource.EXPLICIT_MPN_FIELD,
            match_type=IdentityMatchType.UNKNOWN,
            decision=EvidenceDecision.REJECTED,
            rejection_reason=IdentityRejectionReason.MPN_MISMATCH,
        )
        result = _make_result(MPN, (sem,))
        with pytest.raises(CompactQuoteProjectionError, match="human-review"):
            project_human_confirmed_rows(result, frozenset({0}))


# ---------------------------------------------------------------------------
# Authority isolation: projection does not touch frozen 4A output
# ---------------------------------------------------------------------------


class TestAuthorityIsolation:
    def test_machine_price_projection_unchanged(self) -> None:
        """The bucket-member (Machine Price) projection is byte-identical
        with or without human-confirmed rows present."""
        sem = _semantic_assessment(
            MPN,
            source_url="https://hc.example.com/h",
            price_amount=Decimal("1890.00"),
            condition=NormalizedCondition.NEW,
        )
        acc = _accepted_assessment(
            MPN, source_url="https://det.example.com/d", price=Decimal("1500.00")
        )
        bucket = PriceAggregateBucket(
            currency_code="USD",
            condition=NormalizedCondition.NEW,
            assessments=(acc,),
            count=1,
            low=Decimal("1500.00"),
            median=Decimal("1500.00"),
            high=Decimal("1500.00"),
            market_range_low=None,
            market_range_high=None,
            confidence=ConfidenceLevel.LOW,
        )
        result = _make_result(MPN, (acc, sem), buckets=(bucket,))

        before = project_public_rows(result)
        human = project_human_confirmed_rows(result, frozenset({1}))
        after = project_public_rows(result)

        assert before == after  # frozen 4A projection untouched
        assert len(before) == 1
        assert before[0].price_amount == Decimal("1500.00")
        assert human[0].price_amount == Decimal("1890.00")
        # The human row is a distinct row type — never a bucket member
        assert all(r.source_type == "PUBLIC_LISTING" for r in before)

    def test_semantic_match_alone_does_not_project(self) -> None:
        """UNREVIEWED / unconfirmed semantic candidates have no path into
        the projection: indices are an explicit input (identity authority
        comes from the validated review state, not from the match)."""
        sem = _semantic_assessment(MPN, source_url="https://unr.example.com")
        result = _make_result(MPN, (sem,))
        # No confirmed indices -> no rows
        assert project_human_confirmed_rows(result, frozenset()) == ()
        # And the public (Machine Price) projection excludes it entirely
        assert project_public_rows(result) == ()


# ---------------------------------------------------------------------------
# AI-assisted HIGH Working Quote projection (policy already proved upstream)
# ---------------------------------------------------------------------------


class TestAiAssistedWorkingQuoteProjection:
    def test_unknown_condition_is_preserved_and_not_upgraded(self) -> None:
        sem = _semantic_assessment(
            MPN, source_url="https://ai.example.com/a",
            price_amount=Decimal("2969.01"),
            condition=NormalizedCondition.UNKNOWN,
            availability=NormalizedAvailability.IN_STOCK,
        )
        result = _make_result(MPN, (sem,))

        rows = project_ai_assisted_rows(result, frozenset({0}))

        assert len(rows) == 1
        row = rows[0]
        assert row.source_type == "AI_ASSISTED"
        assert row.assessment_index == 0
        assert row.price_amount == Decimal("2969.01")
        assert row.inventory == "In Stock"
        assert row.brand_new == "Unknown"
        assert row.condition == "UNKNOWN"
        assert "AI High" in (row.note or "")
        assert "Not human verified" in (row.note or "")

    def test_new_condition_is_preserved_truthfully(self) -> None:
        sem = _semantic_assessment(
            MPN, source_url="https://ai.example.com/new",
            condition=NormalizedCondition.NEW,
        )
        result = _make_result(MPN, (sem,))
        row = project_ai_assisted_rows(result, frozenset({0}))[0]
        assert row.condition == "NEW"
        assert row.brand_new == "Yes"

    def test_missing_price_or_currency_never_created_by_ai_projection(self) -> None:
        no_price = _semantic_assessment(
            MPN, source_url="https://ai.example.com/no-price", price_amount=None
        )
        no_currency = _semantic_assessment(
            MPN, source_url="https://ai.example.com/no-currency", currency_code=None
        )
        result = _make_result(MPN, (no_price, no_currency))
        assert project_ai_assisted_rows(result, frozenset({0, 1})) == ()

    def test_non_review_eligible_index_fails_closed(self) -> None:
        accepted = _accepted_assessment(
            MPN, source_url="https://deterministic.example.com/product"
        )
        bucket = PriceAggregateBucket(
            currency_code="USD",
            condition=NormalizedCondition.NEW,
            assessments=(accepted,),
            count=1,
            low=Decimal("100.00"),
            median=Decimal("100.00"),
            high=Decimal("100.00"),
            market_range_low=None,
            market_range_high=None,
            confidence=ConfidenceLevel.LOW,
        )
        result = _make_result(MPN, (accepted,), buckets=(bucket,))
        with pytest.raises(CompactQuoteProjectionError, match="not semantic-review eligible"):
            project_ai_assisted_rows(result, frozenset({0}))

    def test_selection_requires_frozenset_exact_ints(self) -> None:
        sem = _semantic_assessment(MPN, source_url="https://ai.example.com/a")
        result = _make_result(MPN, (sem,))
        with pytest.raises(CompactQuoteProjectionError, match="frozenset"):
            project_ai_assisted_rows(result, {0})
        with pytest.raises(CompactQuoteProjectionError, match="exact ints"):
            project_ai_assisted_rows(result, frozenset({True}))