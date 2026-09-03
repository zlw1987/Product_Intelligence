"""Tests for reviewed price aggregation.

PRODUCT-INTEL.HUMAN-REVIEW.

Validates:
- Unreviewed/rejected candidates contribute nothing
- Confirmed candidates can contribute
- Deterministic + confirmed produce correct reviewed statistics
- Machine baseline remains unchanged
- Confirmed identity with invalid price is excluded
- Deduplication behavior matches existing 4A
- Median/min/max/count reuse authoritative arithmetic
- Result preserves deterministic vs human-confirmed provenance
"""

from __future__ import annotations

from decimal import Decimal
from typing import TYPE_CHECKING

import pytest

from product_intelligence.domain import ResearchRequest
from product_intelligence.domain.enums import (
    ConfidenceLevel,
    EvidenceDecision,
    IdentityMatchType,
    VerificationStatus,
)
from product_intelligence.research.matching import (
    EvidenceSource,
    IdentityRejectionReason,
)
from product_intelligence.research.normalization import (
    NormalizedAvailability,
    NormalizedCondition,
)
from product_intelligence.research.aggregation import (
    PriceAggregationExclusionReason,
    aggregate_listing_prices,
    aggregate_reviewed_listing_prices,
    ReviewedPriceAggregationResult,
    ReviewedListingOrigin,
)
from product_intelligence.research.matching import ListingIdentityAssessment
from product_intelligence.research.normalization import NormalizedListingObservation
from product_intelligence.research.listings import ListingObservation

if TYPE_CHECKING:
    pass


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_listing(
    url: str,
    price: Decimal,
    currency: str = "USD",
    condition: str = "NEW",
    mpn: str = "TEST-001",
) -> ListingObservation:
    from product_intelligence.research.listings import ExtractionMethod
    return ListingObservation(
        source_url=url,
        extraction_method=ExtractionMethod.JSON_LD,
        manufacturer_part_number_text=mpn,
        sku_text="SKU-001",
        price_text=str(price),
        currency_text=currency,
        condition_text=condition,
    )


def _make_assessment(
    obs: ListingObservation,
    decision: EvidenceDecision,
    mpn: str = "TEST-001",
    price: Decimal | None = None,
    currency: str = "USD",
    condition: NormalizedCondition = NormalizedCondition.NEW,
) -> ListingIdentityAssessment:
    from product_intelligence.research.normalization import NormalizedAvailability
    from product_intelligence.research.matching import IdentityRejectionReason
    price_amount = price if price is not None else Decimal("99.99")
    normalized = NormalizedListingObservation(
        observation=obs,
        price_amount=price_amount,
        currency_code=currency,
        condition=condition,
        availability=NormalizedAvailability.UNKNOWN,
        seller_name="Test Seller",
        normalization_issues=(),
    )
    if decision is EvidenceDecision.ACCEPTED:
        return ListingIdentityAssessment(
            normalized_listing=normalized,
            requested_part_number=mpn,
            candidate_part_number_raw=mpn,
            candidate_part_number_compared=mpn,
            candidate_evidence_source=EvidenceSource.EXPLICIT_MPN_FIELD,
            match_type=IdentityMatchType.EXACT,
            decision=decision,
            rejection_reason=None,
        )
    elif decision is EvidenceDecision.AI_ASSISTED_MATCH:
        # Frozen FU3B semantics: this is the ORIGINAL deterministic REJECTED
        # assessment (semantic-eligible). The candidate record is separate
        # semantic authority. We use TITLE_TEXT evidence to be human-review-eligible.
        from product_intelligence.research.listings import ExtractionMethod
        # Create observation with MPN in title (TITLE_TEXT evidence)
        eligible_obs = ListingObservation(
            source_url=obs.source_url,
            extraction_method=ExtractionMethod.JSON_LD,
            manufacturer_part_number_text="",
            sku_text=None,
            product_title=f"Product for {mpn}",
            price_text=str(price_amount),
            currency_text=currency,
            condition_text="NEW",
        )
        eligible_normalized = NormalizedListingObservation(
            observation=eligible_obs,
            price_amount=price_amount,
            currency_code=currency,
            condition=condition,
            availability=NormalizedAvailability.UNKNOWN,
            seller_name="Test Seller",
            normalization_issues=(),
        )
        return ListingIdentityAssessment(
            normalized_listing=eligible_normalized,
            requested_part_number=mpn,
            candidate_part_number_raw=mpn,
            candidate_part_number_compared=mpn,
            candidate_evidence_source=EvidenceSource.TITLE_TEXT,
            match_type=IdentityMatchType.UNKNOWN,
            decision=EvidenceDecision.REJECTED,
            rejection_reason=IdentityRejectionReason.NO_EXPLICIT_MPN_EVIDENCE,
        )
    else:
        return ListingIdentityAssessment(
            normalized_listing=normalized,
            requested_part_number=mpn,
            candidate_part_number_raw="",
            candidate_part_number_compared="",
            candidate_evidence_source=EvidenceSource.NONE,
            match_type=IdentityMatchType.UNKNOWN,
            decision=decision,
            rejection_reason=IdentityRejectionReason.NO_EXPLICIT_MPN_EVIDENCE,
        )


@pytest.fixture
def research_request() -> ResearchRequest:
    return ResearchRequest(
        manufacturer_part_number="TEST-001",
        description="Test product description",
    )



def _make_listing_no_mpn(
    url: str,
    price: Decimal,
    currency: str = "USD",
) -> ListingObservation:
    """Create a listing without explicit MPN (for AI-assisted match tests)."""
    from product_intelligence.research.listings import ExtractionMethod
    return ListingObservation(
        source_url=url,
        extraction_method=ExtractionMethod.JSON_LD,
        sku_text="SKU-001",
        price_text=str(price),
        currency_text=currency,
        condition_text="NEW",
    )

# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestUnreviewedCandidateContributesNothing:
    def test_no_confirmed_indices_excludes_all_ai_assisted(self, research_request) -> None:
        """With no confirmed indices, all AI-assisted candidates are excluded."""
        obs = _make_listing("https://example.com/1", Decimal("99.99"))
        assessment = _make_assessment(obs, EvidenceDecision.AI_ASSISTED_MATCH)
        assessments = (assessment,)
        confirmed = frozenset()

        result = aggregate_reviewed_listing_prices(
            request=research_request,
            assessments=assessments,
            confirmed_assessment_indices=confirmed,
        )

        assert len(result.buckets) == 0
        assert len(result.exclusions) == 1
        assert result.exclusions[0].reason is PriceAggregationExclusionReason.IDENTITY_NOT_ACCEPTED

    def test_machine_baseline_unchanged(self, research_request) -> None:
        """The deterministic machine baseline is not affected by review."""
        obs = _make_listing("https://example.com/1", Decimal("99.99"))
        assessment = _make_assessment(obs, EvidenceDecision.AI_ASSISTED_MATCH)
        assessments = (assessment,)

        # Machine aggregation excludes AI-assisted
        machine_result = aggregate_listing_prices(research_request, assessments)
        assert len(machine_result.buckets) == 0

        # Reviewed aggregation also excludes it (no confirmed)
        reviewed_result = aggregate_reviewed_listing_prices(
            request=research_request,
            assessments=assessments,
            confirmed_assessment_indices=frozenset(),
        )
        assert len(reviewed_result.buckets) == 0


class TestRejectedCandidateContributesNothing:
    def test_rejected_candidate_not_in_confirmed_set(self, research_request) -> None:
        """A rejected candidate is simply not in the confirmed indices set,
        so it behaves the same as unreviewed."""
        obs = _make_listing("https://example.com/1", Decimal("99.99"))
        assessment = _make_assessment(obs, EvidenceDecision.AI_ASSISTED_MATCH)
        assessments = (assessment,)
        # Rejected means NOT in confirmed indices
        confirmed = frozenset()

        result = aggregate_reviewed_listing_prices(
            request=research_request,
            assessments=assessments,
            confirmed_assessment_indices=confirmed,
        )
        assert len(result.buckets) == 0


class TestConfirmedCandidateContributes:
    def test_confirmed_candidate_enters_bucket(self, research_request) -> None:
        """A confirmed AI-assisted candidate contributes to the reviewed price."""
        obs = _make_listing("https://example.com/1", Decimal("99.99"))
        assessment = _make_assessment(obs, EvidenceDecision.AI_ASSISTED_MATCH)
        assessments = (assessment,)
        confirmed = frozenset({0})

        result = aggregate_reviewed_listing_prices(
            request=research_request,
            assessments=assessments,
            confirmed_assessment_indices=confirmed,
        )

        assert len(result.buckets) == 1
        bucket = result.buckets[0]
        assert bucket.count == 1
        assert bucket.deterministic_count == 0
        assert bucket.human_confirmed_count == 1
        assert bucket.median == Decimal("99.99")

    def test_confirmed_candidate_shows_human_confirmed_origin(self, research_request) -> None:
        """The provenance tracks human-confirmed vs deterministic."""
        obs1 = _make_listing("https://example.com/1", Decimal("89.99"))
        det_assessment = _make_assessment(obs1, EvidenceDecision.ACCEPTED, price=Decimal("89.99"))
        obs2 = _make_listing("https://example.com/2", Decimal("99.99"))
        ai_assessment = _make_assessment(obs2, EvidenceDecision.AI_ASSISTED_MATCH, price=Decimal("99.99"))
        assessments = (det_assessment, ai_assessment)
        confirmed = frozenset({1})

        result = aggregate_reviewed_listing_prices(
            request=research_request,
            assessments=assessments,
            confirmed_assessment_indices=confirmed,
        )

        assert len(result.buckets) == 1
        bucket = result.buckets[0]
        assert bucket.count == 2
        assert bucket.deterministic_count == 1
        assert bucket.human_confirmed_count == 1
        assert bucket.low == Decimal("89.99")
        assert bucket.high == Decimal("99.99")
        # Median of 89.99 and 99.99
        assert bucket.median == Decimal("94.99")


class TestDeterministicPlusConfirmed:
    def test_deterministic_and_confirmed_produce_correct_stats(self, research_request) -> None:
        """Deterministic ACCEPTED + confirmed AI-assisted produce correct stats."""
        prices = [Decimal("79.99"), Decimal("89.99"), Decimal("109.99")]
        obs_list = [
            _make_listing(f"https://example.com/{i}", p)
            for i, p in enumerate(prices)
        ]
        assessments = tuple(
            _make_assessment(obs, EvidenceDecision.ACCEPTED, price=Decimal(obs.price_text))
            for obs in obs_list[:2]
        ) + (_make_assessment(obs_list[2], EvidenceDecision.AI_ASSISTED_MATCH, price=Decimal(obs_list[2].price_text),),)
        confirmed = frozenset({2})

        result = aggregate_reviewed_listing_prices(
            request=research_request,
            assessments=assessments,
            confirmed_assessment_indices=confirmed,
        )

        assert len(result.buckets) == 1
        bucket = result.buckets[0]
        assert bucket.count == 3
        assert bucket.deterministic_count == 2
        assert bucket.human_confirmed_count == 1
        assert bucket.low == Decimal("79.99")
        assert bucket.median == Decimal("89.99")
        assert bucket.high == Decimal("109.99")
        assert bucket.confidence == ConfidenceLevel.MEDIUM


class TestConfirmedWithInvalidPrice:
    def test_confirmed_with_missing_price_excluded(self, research_request) -> None:
        """A confirmed identity with invalid/missing price is excluded."""
        from product_intelligence.research.listings import ExtractionMethod
        from product_intelligence.research.normalization import NormalizedAvailability
        # Listing with no structured identifier but MPN in title (TITLE_TEXT evidence)
        obs = ListingObservation(
            source_url="https://example.com/1",
            extraction_method=ExtractionMethod.JSON_LD,
            manufacturer_part_number_text="",
            sku_text=None,
            product_title="Product for TEST-001",
        )
        normalized = NormalizedListingObservation(
            observation=obs,
            price_amount=None,
            currency_code="USD",
            condition=NormalizedCondition.NEW,
            availability=NormalizedAvailability.UNKNOWN,
            seller_name="Test Seller",
            normalization_issues=(),
        )
        assessment = ListingIdentityAssessment(
            normalized_listing=normalized,
            requested_part_number="TEST-001",
            candidate_part_number_raw="TEST-001",
            candidate_part_number_compared="TEST-001",
            candidate_evidence_source=EvidenceSource.TITLE_TEXT,
            match_type=IdentityMatchType.UNKNOWN,
            decision=EvidenceDecision.REJECTED,
            rejection_reason=IdentityRejectionReason.NO_EXPLICIT_MPN_EVIDENCE,
        )
        assessments = (assessment,)
        confirmed = frozenset({0})

        result = aggregate_reviewed_listing_prices(
            request=research_request,
            assessments=assessments,
            confirmed_assessment_indices=confirmed,
        )

        # The confirmed identity has no price, so it's excluded for price reason
        assert len(result.buckets) == 0
        assert len(result.exclusions) == 1
        assert result.exclusions[0].reason is PriceAggregationExclusionReason.NO_NUMERIC_PRICE
        assert result.exclusions[0].origin is ReviewedListingOrigin.HUMAN_CONFIRMED


class TestCurrencyAndConditionGrouping:
    def test_non_comparable_currency_separate_bucket(self, research_request) -> None:
        """Different currencies produce separate buckets following 4A rules."""
        obs_usd = _make_listing("https://example.com/1", Decimal("99.99"), "USD")
        det_assessment = _make_assessment(obs_usd, EvidenceDecision.ACCEPTED, currency="USD")
        obs_eur = _make_listing("https://example.com/2", Decimal("89.99"), "EUR")
        ai_assessment = _make_assessment(obs_eur, EvidenceDecision.AI_ASSISTED_MATCH, price=Decimal("89.99"), currency="EUR")
        assessments = (det_assessment, ai_assessment)
        confirmed = frozenset({1})

        result = aggregate_reviewed_listing_prices(
            request=research_request,
            assessments=assessments,
            confirmed_assessment_indices=confirmed,
        )

        assert len(result.buckets) == 2
        currencies = {b.currency_code for b in result.buckets}
        assert currencies == {"USD", "EUR"}


class TestDeduplicationBehavior:
    def test_deduplication_same_as_4a(self, research_request) -> None:
        """Deduplication is handled at the assessment level — each assessment
        is unique. The reviewed aggregation reuses the same grouping logic."""
        # Each assessment is a unique listing — no deduplication needed at
        # the aggregation level. Deduplication happens at observation level
        # before assessments are created.
        obs1 = _make_listing("https://example.com/1", Decimal("99.99"))
        obs2 = _make_listing("https://example.com/2", Decimal("99.99"))
        assessment1 = _make_assessment(obs1, EvidenceDecision.ACCEPTED)
        assessment2 = _make_assessment(obs2, EvidenceDecision.AI_ASSISTED_MATCH)
        assessments = (assessment1, assessment2)
        confirmed = frozenset({1})

        result = aggregate_reviewed_listing_prices(
            request=research_request,
            assessments=assessments,
            confirmed_assessment_indices=confirmed,
        )

        # Both unique listings contribute
        assert len(result.buckets) == 1
        assert result.buckets[0].count == 2


class TestArithmeticCorrectness:
    def test_median_calculation(self, research_request) -> None:
        """Median is computed correctly for odd and even counts."""
        prices = [Decimal("50.00"), Decimal("75.00"), Decimal("100.00")]
        obs_list = [_make_listing(f"https://example.com/{i}", p) for i, p in enumerate(prices)]
        assessments = tuple(
            _make_assessment(obs, EvidenceDecision.AI_ASSISTED_MATCH, price=Decimal(obs.price_text))
            for obs in obs_list
        )
        confirmed = frozenset({0, 1, 2})

        result = aggregate_reviewed_listing_prices(
            request=research_request,
            assessments=assessments,
            confirmed_assessment_indices=confirmed,
        )

        bucket = result.buckets[0]
        assert bucket.median == Decimal("75.00")  # Middle value of 3

    def test_median_even_count(self, research_request) -> None:
        """Median of even count is average of two middle values."""
        prices = [Decimal("50.00"), Decimal("100.00")]
        obs_list = [_make_listing(f"https://example.com/{i}", p) for i, p in enumerate(prices)]
        assessments = tuple(
            _make_assessment(obs, EvidenceDecision.AI_ASSISTED_MATCH, price=Decimal(obs.price_text))
            for obs in obs_list
        )
        confirmed = frozenset({0, 1})

        result = aggregate_reviewed_listing_prices(
            request=research_request,
            assessments=assessments,
            confirmed_assessment_indices=confirmed,
        )

        bucket = result.buckets[0]
        assert bucket.median == Decimal("75.00")  # (50 + 100) / 2


class TestVerificationStatus:
    def test_single_bucket_is_verified(self, research_request) -> None:
        result = aggregate_reviewed_listing_prices(
            request=research_request,
            assessments=(_make_assessment(_make_listing("https://example.com/1", Decimal("99.99")), EvidenceDecision.AI_ASSISTED_MATCH),),
            confirmed_assessment_indices=frozenset({0}),
        )
        assert result.verification_status == VerificationStatus.VERIFIED

    def test_no_buckets_is_unknown(self, research_request) -> None:
        result = aggregate_reviewed_listing_prices(
            request=research_request,
            assessments=(),
            confirmed_assessment_indices=frozenset(),
        )
        assert result.verification_status == VerificationStatus.UNKNOWN


class TestTypeValidation:
    def test_invalid_research_request_type(self, request) -> None:
        with pytest.raises(TypeError):
            aggregate_reviewed_listing_prices(
                request="not a request",
                assessments=(),
                confirmed_assessment_indices=frozenset(),
            )

    def test_invalid_assessments_type(self, research_request) -> None:
        with pytest.raises(TypeError):
            aggregate_reviewed_listing_prices(
                request=research_request,
                assessments=[],  # Must be tuple
                confirmed_assessment_indices=frozenset(),
            )

    def test_invalid_confirmed_type(self, research_request) -> None:
        with pytest.raises(TypeError):
            aggregate_reviewed_listing_prices(
                request=research_request,
                assessments=(),
                confirmed_assessment_indices=set(),  # Must be frozenset
            )


class TestResultType:
    def test_returns_reviewed_price_aggregation_result(self, research_request) -> None:
        obs = _make_listing("https://example.com/1", Decimal("99.99"))
        assessment = _make_assessment(obs, EvidenceDecision.AI_ASSISTED_MATCH)
        result = aggregate_reviewed_listing_prices(
            request=research_request,
            assessments=(assessment,),
            confirmed_assessment_indices=frozenset({0}),
        )
        assert isinstance(result, ReviewedPriceAggregationResult)




def _make_norm(
    obs: ListingObservation,
    price: Decimal,
    currency: str = "USD",
    condition: NormalizedCondition = NormalizedCondition.NEW,
) -> NormalizedListingObservation:
    """Build a NormalizedListingObservation from an observation."""
    from product_intelligence.research.normalization import NormalizedAvailability
    return NormalizedListingObservation(
        observation=obs,
        price_amount=price,
        currency_code=currency,
        condition=condition,
        availability=NormalizedAvailability.UNKNOWN,
        seller_name="Test Seller",
        normalization_issues=(),
    )


class TestConfirmedIndexValidation:
    """Confirmed indices must be validated before use."""

    def test_negative_index_raises(self, research_request) -> None:
        """Negative index is refused."""
        obs = _make_listing("https://example.com/1", Decimal("99.99"))
        assessment = _make_assessment(obs, EvidenceDecision.AI_ASSISTED_MATCH)
        with pytest.raises(ValueError, match="negative"):
            aggregate_reviewed_listing_prices(
                request=research_request,
                assessments=(assessment,),
                confirmed_assessment_indices=frozenset({-1}),
            )

    def test_out_of_range_index_raises(self, research_request) -> None:
        """Out-of-range index is refused."""
        obs = _make_listing("https://example.com/1", Decimal("99.99"))
        assessment = _make_assessment(obs, EvidenceDecision.AI_ASSISTED_MATCH)
        with pytest.raises(ValueError, match="out-of-range"):
            aggregate_reviewed_listing_prices(
                request=research_request,
                assessments=(assessment,),
                confirmed_assessment_indices=frozenset({5}),
            )

    def test_bool_index_raises(self, research_request) -> None:
        """bool (True/False) is refused even though bool is a subclass of int."""
        obs = _make_listing("https://example.com/1", Decimal("99.99"))
        assessment = _make_assessment(obs, EvidenceDecision.AI_ASSISTED_MATCH)
        with pytest.raises(TypeError, match="bool"):
            aggregate_reviewed_listing_prices(
                request=research_request,
                assessments=(assessment,),
                confirmed_assessment_indices=frozenset({True}),
            )

    def test_accepted_index_refused(self, research_request) -> None:
        """Confirmed index pointing to ACCEPTED is refused.
        
        Human confirmation only upgrades identity authority for semantic-eligible
        REJECTED assessments, not for deterministic ACCEPTED ones.
        """
        obs = _make_listing("https://example.com/1", Decimal("99.99"))
        assessment = _make_assessment(obs, EvidenceDecision.ACCEPTED)
        with pytest.raises(ValueError, match="not human-review eligible"):
            aggregate_reviewed_listing_prices(
                request=research_request,
                assessments=(assessment,),
                confirmed_assessment_indices=frozenset({0}),
            )

    def test_rejected_index_refused(self, research_request) -> None:
        """Confirmed index pointing to non-eligible REJECTED is refused."""
        from product_intelligence.research.matching import IdentityRejectionReason
        from product_intelligence.research.listings import ExtractionMethod as EM
        # Create a listing that publishes a different MPN (MPN_MISMATCH = not eligible)
        obs = ListingObservation(
            source_url="https://example.com/1",
            extraction_method=EM.JSON_LD,
            manufacturer_part_number_text="WRONG-MPN",
            price_text="99.99",
            currency_text="USD",
            condition_text="new",
        )
        norm = NormalizedListingObservation(
            observation=obs,
            price_amount=Decimal("99.99"),
            currency_code="USD",
            condition=NormalizedCondition.NEW,
            availability=NormalizedAvailability.UNKNOWN,
            seller_name="Test Seller",
            normalization_issues=(),
        )
        assessment = ListingIdentityAssessment(
            normalized_listing=norm,
            requested_part_number="TEST-001",
            candidate_part_number_raw="WRONG-MPN",
            candidate_part_number_compared="WRONG-MPN",
            candidate_evidence_source=EvidenceSource.EXPLICIT_MPN_FIELD,
            match_type=IdentityMatchType.UNKNOWN,
            decision=EvidenceDecision.REJECTED,
            rejection_reason=IdentityRejectionReason.MPN_MISMATCH,
        )
        with pytest.raises(ValueError, match="not human-review eligible"):
            aggregate_reviewed_listing_prices(
                request=research_request,
                assessments=(assessment,),
                confirmed_assessment_indices=frozenset({0}),
            )

    def test_string_index_refused(self, research_request) -> None:
        """Confirmed index must be int, not string."""
        obs = _make_listing("https://example.com/1", Decimal("99.99"))
        assessment = _make_assessment(obs, EvidenceDecision.AI_ASSISTED_MATCH)
        with pytest.raises(TypeError, match="must contain int values"):
            aggregate_reviewed_listing_prices(
                request=research_request,
                assessments=(assessment,),
                confirmed_assessment_indices=frozenset({"0"}),
            )

    def test_valid_human_review_eligible_still_works(self, research_request) -> None:
        """Valid human-review-eligible confirmed index still works."""
        obs = _make_listing("https://example.com/1", Decimal("99.99"))
        assessment = _make_assessment(obs, EvidenceDecision.AI_ASSISTED_MATCH)
        result = aggregate_reviewed_listing_prices(
            request=research_request,
            assessments=(assessment,),
            confirmed_assessment_indices=frozenset({0}),
        )
        assert len(result.buckets) == 1
        assert result.buckets[0].count == 1
        assert result.buckets[0].human_confirmed_count == 1


class TestReviewedResultTypes:
    """Reviewed result types must be consistent and self-validating."""

    def test_exclusions_are_reviewed_type(self, research_request) -> None:
        """All exclusions in ReviewedPriceAggregationResult are ReviewedPriceAggregationExclusion."""
        from product_intelligence.research.aggregation import (
            ReviewedPriceAggregationExclusion,
        )
        from product_intelligence.research.matching import IdentityRejectionReason
        from product_intelligence.research.listings import ExtractionMethod as EM
        # ACCEPTED listing
        obs1 = _make_listing("https://example.com/1", Decimal("99.99"))
        accepted = _make_assessment(obs1, EvidenceDecision.ACCEPTED)
        # REJECTED listing with wrong MPN
        obs2 = ListingObservation(
            source_url="https://example.com/2",
            extraction_method=EM.JSON_LD,
            manufacturer_part_number_text="WRONG-MPN",
            price_text="50.00",
            currency_text="USD",
            condition_text="new",
        )
        norm2 = NormalizedListingObservation(
            observation=obs2,
            price_amount=Decimal("50.00"),
            currency_code="USD",
            condition=NormalizedCondition.NEW,
            availability=NormalizedAvailability.UNKNOWN,
            seller_name="Test Seller",
            normalization_issues=(),
        )
        rejected = ListingIdentityAssessment(
            normalized_listing=norm2,
            requested_part_number="TEST-001",
            candidate_part_number_raw="WRONG-MPN",
            candidate_part_number_compared="WRONG-MPN",
            candidate_evidence_source=EvidenceSource.EXPLICIT_MPN_FIELD,
            match_type=IdentityMatchType.UNKNOWN,
            decision=EvidenceDecision.REJECTED,
            rejection_reason=IdentityRejectionReason.MPN_MISMATCH,
        )
        assessments = (accepted, rejected)
        result = aggregate_reviewed_listing_prices(
            request=research_request,
            assessments=assessments,
            confirmed_assessment_indices=frozenset(),
        )
        # The rejected assessment should be excluded
        assert len(result.exclusions) == 1
        assert isinstance(result.exclusions[0], ReviewedPriceAggregationExclusion)

    def test_reviewed_entry_provenance(self, research_request) -> None:
        """ReviewedPriceEntry tracks per-listing origin."""
        from product_intelligence.research.aggregation import ReviewedPriceEntry
        obs1 = _make_listing("https://example.com/1", Decimal("50.00"))
        obs2 = _make_listing("https://example.com/2", Decimal("100.00"))
        accepted = _make_assessment(obs1, EvidenceDecision.ACCEPTED)
        ai_match = _make_assessment(obs2, EvidenceDecision.AI_ASSISTED_MATCH)
        assessments = (accepted, ai_match)
        result = aggregate_reviewed_listing_prices(
            request=research_request,
            assessments=assessments,
            confirmed_assessment_indices=frozenset({1}),
        )
        bucket = result.buckets[0]
        assert len(bucket.entries) == 2
        origins = {e.assessment: e.origin for e in bucket.entries}
        assert origins[accepted] is ReviewedListingOrigin.DETERMINISTIC
        assert origins[ai_match] is ReviewedListingOrigin.HUMAN_CONFIRMED

    def test_bucket_counts_derived_from_entries(self, research_request) -> None:
        """Bucket deterministic/human_confirmed counts match entries."""
        obs1 = _make_listing("https://example.com/1", Decimal("50.00"))
        obs2 = _make_listing("https://example.com/2", Decimal("100.00"))
        accepted = _make_assessment(obs1, EvidenceDecision.ACCEPTED)
        ai_match = _make_assessment(obs2, EvidenceDecision.AI_ASSISTED_MATCH)
        assessments = (accepted, ai_match)
        result = aggregate_reviewed_listing_prices(
            request=research_request,
            assessments=assessments,
            confirmed_assessment_indices=frozenset({1}),
        )
        bucket = result.buckets[0]
        assert bucket.deterministic_count == 1
        assert bucket.human_confirmed_count == 1
        assert bucket.count == 2

    def test_reviewed_entry_self_validates(self) -> None:
        """ReviewedPriceEntry __post_init__ rejects wrong types."""
        from product_intelligence.research.aggregation import ReviewedPriceEntry
        obs = _make_listing("https://example.com/1", Decimal("99.99"))
        assessment = _make_assessment(obs, EvidenceDecision.AI_ASSISTED_MATCH)
        # Valid entry works
        entry = ReviewedPriceEntry(assessment=assessment, origin=ReviewedListingOrigin.HUMAN_CONFIRMED)
        assert entry.origin is ReviewedListingOrigin.HUMAN_CONFIRMED
        # Wrong assessment type
        with pytest.raises(TypeError, match="assessment must be"):
            ReviewedPriceEntry(assessment="not an assessment", origin=ReviewedListingOrigin.HUMAN_CONFIRMED)


class TestReviewedBucketAdversarialConstruction:
    """ReviewedPriceAggregateBucket __post_init__ must refuse fabricated states.

    Proves the self-validating contract catches adversarial direct construction
    where provenance entries, assessments, currency, condition, or prices do not
    match the bucket invariants.
    """

    # -----------------------------------------------------------------------
    # A. Entry / assessment provenance mismatch
    # -----------------------------------------------------------------------

    def test_entries_assessments_mismatch_refused(self) -> None:
        """Entries referencing listing B while assessments tuple has listing A
        is refused by the provenance correspondence check."""
        from product_intelligence.research.aggregation import (
            ReviewedPriceAggregateBucket,
            ReviewedPriceEntry,
        )
        # Listing A — the assessment that will go in the assessments tuple
        obs_a = _make_listing("https://example.com/A", Decimal("99.99"))
        assessment_a = _make_assessment(obs_a, EvidenceDecision.ACCEPTED, price=Decimal("99.99"))

        # Listing B — a different assessment that will go in the entry
        obs_b = _make_listing("https://example.com/B", Decimal("88.88"))
        assessment_b = _make_assessment(obs_b, EvidenceDecision.ACCEPTED, price=Decimal("88.88"))

        # Entry claims listing B, but assessments tuple holds listing A
        entry_b = ReviewedPriceEntry(
            assessment=assessment_b,
            origin=ReviewedListingOrigin.DETERMINISTIC,
        )

        with pytest.raises(ValueError, match="does not correspond"):
            ReviewedPriceAggregateBucket(
                currency_code="USD",
                condition=NormalizedCondition.NEW,
                assessments=(assessment_a,),
                entries=(entry_b,),
                count=1,
                deterministic_count=1,
                human_confirmed_count=0,
                low=Decimal("99.99"),
                median=Decimal("99.99"),
                high=Decimal("99.99"),
                market_range_low=None,
                market_range_high=None,
                confidence=ConfidenceLevel.LOW,
            )

    def test_entries_assessments_length_mismatch_refused(self) -> None:
        """Different lengths between entries and assessments is refused."""
        from product_intelligence.research.aggregation import (
            ReviewedPriceAggregateBucket,
            ReviewedPriceEntry,
        )
        obs_a = _make_listing("https://example.com/A", Decimal("99.99"))
        assessment_a = _make_assessment(obs_a, EvidenceDecision.ACCEPTED)
        entry_a = ReviewedPriceEntry(
            assessment=assessment_a,
            origin=ReviewedListingOrigin.DETERMINISTIC,
        )
        obs_b = _make_listing("https://example.com/B", Decimal("55.00"))
        assessment_b = _make_assessment(obs_b, EvidenceDecision.ACCEPTED, price=Decimal("55.00"))

        # Two assessments but only one entry
        with pytest.raises(ValueError, match="same length"):
            ReviewedPriceAggregateBucket(
                currency_code="USD",
                condition=NormalizedCondition.NEW,
                assessments=(assessment_a, assessment_b),
                entries=(entry_a,),
                count=1,
                deterministic_count=1,
                human_confirmed_count=0,
                low=Decimal("55.00"),
                median=Decimal("55.00"),
                high=Decimal("99.99"),
                market_range_low=None,
                market_range_high=None,
                confidence=ConfidenceLevel.LOW,
            )

    # -----------------------------------------------------------------------
    # B. Wrong bucket currency
    # -----------------------------------------------------------------------

    def test_wrong_bucket_currency_refused(self) -> None:
        """Assessment with EUR currency in a USD bucket is refused."""
        from product_intelligence.research.aggregation import (
            ReviewedPriceAggregateBucket,
            ReviewedPriceEntry,
        )
        obs = _make_listing("https://example.com/1", Decimal("99.99"))
        norm_eur = _make_norm(obs, Decimal("99.99"), currency="EUR")
        assessment = ListingIdentityAssessment(
            normalized_listing=norm_eur,
            requested_part_number="TEST-001",
            candidate_part_number_raw="TEST-001",
            candidate_part_number_compared="TEST-001",
            candidate_evidence_source=EvidenceSource.EXPLICIT_MPN_FIELD,
            match_type=IdentityMatchType.EXACT,
            decision=EvidenceDecision.ACCEPTED,
            rejection_reason=None,
        )
        entry = ReviewedPriceEntry(
            assessment=assessment,
            origin=ReviewedListingOrigin.DETERMINISTIC,
        )

        with pytest.raises(ValueError, match="currency"):
            ReviewedPriceAggregateBucket(
                currency_code="USD",  # Wrong: assessment is EUR
                condition=NormalizedCondition.NEW,
                assessments=(assessment,),
                entries=(entry,),
                count=1,
                deterministic_count=1,
                human_confirmed_count=0,
                low=Decimal("99.99"),
                median=Decimal("99.99"),
                high=Decimal("99.99"),
                market_range_low=None,
                market_range_high=None,
                confidence=ConfidenceLevel.LOW,
            )

    # -----------------------------------------------------------------------
    # C. Wrong bucket condition
    # -----------------------------------------------------------------------

    def test_wrong_bucket_condition_refused(self) -> None:
        """Assessment with USED condition in a NEW bucket is refused."""
        from product_intelligence.research.aggregation import (
            ReviewedPriceAggregateBucket,
            ReviewedPriceEntry,
        )
        obs = _make_listing("https://example.com/1", Decimal("99.99"))
        norm_used = _make_norm(obs, Decimal("99.99"), condition=NormalizedCondition.USED)
        assessment = ListingIdentityAssessment(
            normalized_listing=norm_used,
            requested_part_number="TEST-001",
            candidate_part_number_raw="TEST-001",
            candidate_part_number_compared="TEST-001",
            candidate_evidence_source=EvidenceSource.EXPLICIT_MPN_FIELD,
            match_type=IdentityMatchType.EXACT,
            decision=EvidenceDecision.ACCEPTED,
            rejection_reason=None,
        )
        entry = ReviewedPriceEntry(
            assessment=assessment,
            origin=ReviewedListingOrigin.DETERMINISTIC,
        )

        with pytest.raises(ValueError, match="condition"):
            ReviewedPriceAggregateBucket(
                currency_code="USD",
                condition=NormalizedCondition.NEW,  # Wrong: assessment is USED
                assessments=(assessment,),
                entries=(entry,),
                count=1,
                deterministic_count=1,
                human_confirmed_count=0,
                low=Decimal("99.99"),
                median=Decimal("99.99"),
                high=Decimal("99.99"),
                market_range_low=None,
                market_range_high=None,
                confidence=ConfidenceLevel.LOW,
            )

    # -----------------------------------------------------------------------
    # D. Missing / non-numeric price
    # -----------------------------------------------------------------------

    def test_missing_price_refused(self) -> None:
        """Assessment with no price_amount is refused in a reviewed bucket."""
        from product_intelligence.research.aggregation import (
            ReviewedPriceAggregateBucket,
            ReviewedPriceEntry,
        )
        from product_intelligence.research.listings import ExtractionMethod
        obs = ListingObservation(
            source_url="https://example.com/1",
            extraction_method=ExtractionMethod.JSON_LD,
            manufacturer_part_number_text="TEST-001",
            sku_text="SKU-001",
            price_text=None,
            currency_text="USD",
            condition_text="new",
        )
        norm_no_price = NormalizedListingObservation(
            observation=obs,
            price_amount=None,
            currency_code="USD",
            condition=NormalizedCondition.NEW,
            availability=NormalizedAvailability.UNKNOWN,
            seller_name="Test Seller",
            normalization_issues=(),
        )
        assessment = ListingIdentityAssessment(
            normalized_listing=norm_no_price,
            requested_part_number="TEST-001",
            candidate_part_number_raw="TEST-001",
            candidate_part_number_compared="TEST-001",
            candidate_evidence_source=EvidenceSource.EXPLICIT_MPN_FIELD,
            match_type=IdentityMatchType.EXACT,
            decision=EvidenceDecision.ACCEPTED,
            rejection_reason=None,
        )
        entry = ReviewedPriceEntry(
            assessment=assessment,
            origin=ReviewedListingOrigin.DETERMINISTIC,
        )

        with pytest.raises(ValueError, match="price_amount"):
            ReviewedPriceAggregateBucket(
                currency_code="USD",
                condition=NormalizedCondition.NEW,
                assessments=(assessment,),
                entries=(entry,),
                count=1,
                deterministic_count=1,
                human_confirmed_count=0,
                low=Decimal("99.99"),
                median=Decimal("99.99"),
                high=Decimal("99.99"),
                market_range_low=None,
                market_range_high=None,
                confidence=ConfidenceLevel.LOW,
            )

    def test_unknown_condition_member_refused(self) -> None:
        """Assessment with UNKNOWN condition is refused in a reviewed bucket.

        This is a per-assessment invariant enforced by the reviewed bucket,
        consistent with the PriceAggregateBucket contract.
        """
        from product_intelligence.research.aggregation import (
            ReviewedPriceAggregateBucket,
            ReviewedPriceEntry,
        )
        from product_intelligence.research.listings import ExtractionMethod
        obs = ListingObservation(
            source_url="https://example.com/1",
            extraction_method=ExtractionMethod.JSON_LD,
            manufacturer_part_number_text="TEST-001",
            sku_text="SKU-001",
            price_text="99.99",
            currency_text="USD",
            condition_text=None,
        )
        norm_unknown = NormalizedListingObservation(
            observation=obs,
            price_amount=Decimal("99.99"),
            currency_code="USD",
            condition=NormalizedCondition.UNKNOWN,
            availability=NormalizedAvailability.UNKNOWN,
            seller_name="Test Seller",
            normalization_issues=(),
        )
        assessment = ListingIdentityAssessment(
            normalized_listing=norm_unknown,
            requested_part_number="TEST-001",
            candidate_part_number_raw="TEST-001",
            candidate_part_number_compared="TEST-001",
            candidate_evidence_source=EvidenceSource.EXPLICIT_MPN_FIELD,
            match_type=IdentityMatchType.EXACT,
            decision=EvidenceDecision.ACCEPTED,
            rejection_reason=None,
        )
        entry = ReviewedPriceEntry(
            assessment=assessment,
            origin=ReviewedListingOrigin.DETERMINISTIC,
        )

        with pytest.raises(ValueError, match="UNKNOWN condition"):
            ReviewedPriceAggregateBucket(
                currency_code="USD",
                condition=NormalizedCondition.UNKNOWN,
                assessments=(assessment,),
                entries=(entry,),
                count=1,
                deterministic_count=1,
                human_confirmed_count=0,
                low=Decimal("99.99"),
                median=Decimal("99.99"),
                high=Decimal("99.99"),
                market_range_low=None,
                market_range_high=None,
                confidence=ConfidenceLevel.LOW,
            )

    # -----------------------------------------------------------------------
    # E. Positive: legitimate HUMAN_CONFIRMED REJECTED assessment works
    # -----------------------------------------------------------------------

    def test_human_confirmed_rejected_assessment_direct_construction(self) -> None:
        """A HUMAN_CONFIRMED entry wrapping a REJECTED assessment is valid
        via direct construction, proving the bucket does NOT require
        decision == ACCEPTED (identity authority comes from the entry origin)."""
        from product_intelligence.research.aggregation import (
            ReviewedPriceAggregateBucket,
            ReviewedPriceEntry,
        )
        # Create a human-review-eligible REJECTED assessment
        obs = _make_listing("https://example.com/1", Decimal("129.99"))
        ai_assessment = _make_assessment(
            obs, EvidenceDecision.AI_ASSISTED_MATCH, price=Decimal("129.99")
        )
        # This assessment's decision is REJECTED (from AI_ASSISTED_MATCH helper)
        assert ai_assessment.decision is EvidenceDecision.REJECTED

        # Build a HUMAN_CONFIRMED entry for it
        entry = ReviewedPriceEntry(
            assessment=ai_assessment,
            origin=ReviewedListingOrigin.HUMAN_CONFIRMED,
        )

        # Direct construction of a valid reviewed bucket
        bucket = ReviewedPriceAggregateBucket(
            currency_code="USD",
            condition=NormalizedCondition.NEW,
            assessments=(ai_assessment,),
            entries=(entry,),
            count=1,
            deterministic_count=0,
            human_confirmed_count=1,
            low=Decimal("129.99"),
            median=Decimal("129.99"),
            high=Decimal("129.99"),
            market_range_low=None,
            market_range_high=None,
            confidence=ConfidenceLevel.LOW,
        )

        assert bucket.count == 1
        assert bucket.deterministic_count == 0
        assert bucket.human_confirmed_count == 1
        assert bucket.median == Decimal("129.99")
        assert bucket.currency_code == "USD"
        assert bucket.condition is NormalizedCondition.NEW

    def test_equal_by_value_distinct_assessment_correspondence_allowed(self) -> None:
        """An equal-by-value but distinct (not is) assessment in the entry is
        accepted. Correspondence is value-based, not object-identity-based."""
        from product_intelligence.research.aggregation import (
            ReviewedPriceAggregateBucket,
            ReviewedPriceEntry,
        )
        obs = _make_listing("https://example.com/1", Decimal("99.99"))
        assessment_a = _make_assessment(obs, EvidenceDecision.ACCEPTED, price=Decimal("99.99"))

        # Build an exact equal-by-value copy via reconstruction.
        # ListingIdentityAssessment is a frozen dataclass so == uses field values.
        assessment_a_copy = ListingIdentityAssessment(
            normalized_listing=assessment_a.normalized_listing,
            requested_part_number=assessment_a.requested_part_number,
            candidate_part_number_raw=assessment_a.candidate_part_number_raw,
            candidate_part_number_compared=assessment_a.candidate_part_number_compared,
            candidate_evidence_source=assessment_a.candidate_evidence_source,
            match_type=assessment_a.match_type,
            decision=assessment_a.decision,
            rejection_reason=assessment_a.rejection_reason,
        )

        assert assessment_a == assessment_a_copy
        assert assessment_a is not assessment_a_copy

        entry = ReviewedPriceEntry(
            assessment=assessment_a_copy,
            origin=ReviewedListingOrigin.DETERMINISTIC,
        )

        # Must succeed — value equality is sufficient
        bucket = ReviewedPriceAggregateBucket(
            currency_code="USD",
            condition=NormalizedCondition.NEW,
            assessments=(assessment_a,),
            entries=(entry,),
            count=1,
            deterministic_count=1,
            human_confirmed_count=0,
            low=Decimal("99.99"),
            median=Decimal("99.99"),
            high=Decimal("99.99"),
            market_range_low=None,
            market_range_high=None,
            confidence=ConfidenceLevel.LOW,
        )

        assert bucket.count == 1
        assert bucket.median == Decimal("99.99")

    def test_duplicate_assessments_refused(self) -> None:
        """A reviewed bucket containing the same assessment value twice
        is refused, matching the PriceAggregateBucket invariant."""
        from product_intelligence.research.aggregation import (
            ReviewedPriceAggregateBucket,
            ReviewedPriceEntry,
        )
        obs = _make_listing("https://example.com/1", Decimal("99.99"))
        assessment_a = _make_assessment(obs, EvidenceDecision.ACCEPTED, price=Decimal("99.99"))
        # Exact equal-by-value copy
        assessment_a_copy = ListingIdentityAssessment(
            normalized_listing=assessment_a.normalized_listing,
            requested_part_number=assessment_a.requested_part_number,
            candidate_part_number_raw=assessment_a.candidate_part_number_raw,
            candidate_part_number_compared=assessment_a.candidate_part_number_compared,
            candidate_evidence_source=assessment_a.candidate_evidence_source,
            match_type=assessment_a.match_type,
            decision=assessment_a.decision,
            rejection_reason=assessment_a.rejection_reason,
        )
        entry_a = ReviewedPriceEntry(
            assessment=assessment_a,
            origin=ReviewedListingOrigin.DETERMINISTIC,
        )
        entry_a_copy = ReviewedPriceEntry(
            assessment=assessment_a_copy,
            origin=ReviewedListingOrigin.DETERMINISTIC,
        )

        # Both entries correspond correctly (value-equal), but assessments
        # contain a duplicate value — must be refused
        with pytest.raises(ValueError, match="duplicate"):
            ReviewedPriceAggregateBucket(
                currency_code="USD",
                condition=NormalizedCondition.NEW,
                assessments=(assessment_a, assessment_a_copy),
                entries=(entry_a, entry_a_copy),
                count=2,
                deterministic_count=2,
                human_confirmed_count=0,
                low=Decimal("99.99"),
                median=Decimal("99.99"),
                high=Decimal("99.99"),
                market_range_low=None,
                market_range_high=None,
                confidence=ConfidenceLevel.LOW,
            )
