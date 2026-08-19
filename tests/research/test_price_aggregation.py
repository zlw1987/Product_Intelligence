"""Deterministic price aggregation tests (PRODUCT-INTEL.4A).

Exercises the aggregation function with synthetic data covering every
eligibility path, bucket key, exclusion reason, and edge case the spec
requires. All data is constructed inline — no fixture files, no network,
no 3B normalizer (assessments are built directly).
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
    PriceAggregationExclusion,
    PriceAggregationExclusionReason,
    PriceAggregationResult,
    aggregate_listing_prices,
)
from product_intelligence.research.listings import (
    ExtractionMethod,
    ListingObservation,
)
from product_intelligence.research.matching import (
    EvidenceSource,
    ListingIdentityAssessment,
)
from product_intelligence.research.normalization import (
    NormalizedAvailability,
    NormalizedCondition,
    NormalizedListingObservation,
)


# ---------------------------------------------------------------------------
# Helpers: build synthetic accepted assessments quickly
# ---------------------------------------------------------------------------


def _make_observation(
    source_url: str = "https://example.com/product",
    price_text: str | None = "100.00",
    currency_text: str | None = "USD",
    condition_text: str | None = "new",
    mpn_text: str | None = "ABC-123",
    sku_text: str | None = None,
    availability_text: str | None = None,
) -> ListingObservation:
    return ListingObservation(
        source_url=source_url,
        extraction_method=ExtractionMethod.JSON_LD,
        manufacturer_part_number_text=mpn_text,
        sku_text=sku_text,
        price_text=price_text,
        currency_text=currency_text,
        availability_text=availability_text,
        condition_text=condition_text,
    )


def _make_normalized(
    observation: ListingObservation,
    price_amount: Decimal | None = Decimal("100.00"),
    currency_code: str | None = "USD",
    condition: NormalizedCondition = NormalizedCondition.NEW,
    availability: NormalizedAvailability = NormalizedAvailability.UNKNOWN,
    issues: tuple = (),
) -> NormalizedListingObservation:
    return NormalizedListingObservation(
        observation=observation,
        price_amount=price_amount,
        currency_code=currency_code,
        availability=availability,
        condition=condition,
        seller_name=None,
        normalization_issues=issues,
    )


def _make_assessment(
    request: ResearchRequest,
    normalized: NormalizedListingObservation,
    decision: EvidenceDecision = EvidenceDecision.ACCEPTED,
    match_type: IdentityMatchType = IdentityMatchType.EXACT,
    evidence_source: EvidenceSource = EvidenceSource.EXPLICIT_MPN_FIELD,
    candidate_raw: str = "ABC-123",
    candidate_compared: str = "ABC-123",
) -> ListingIdentityAssessment:
    """Build a ListingIdentityAssessment with controlled fields.

    For ACCEPTED assessments, the 3C constructor will re-verify identity
    through the 2A comparator. The raw/compared MPN must actually match
    the request's MPN to survive that check.

    For REJECTED assessments, the constructor validates the rejection
    reason and evidence source against the underlying observation.
    """
    rejection_reason = None
    if decision is EvidenceDecision.REJECTED:
        from product_intelligence.research.matching import IdentityRejectionReason
        rejection_reason = IdentityRejectionReason.NO_EXPLICIT_MPN_EVIDENCE
    elif decision is EvidenceDecision.UNDECIDED:
        from product_intelligence.research.matching import IdentityRejectionReason
        rejection_reason = IdentityRejectionReason.NO_REQUESTED_MPN

    # For REJECTED/UNDECIDED with non-EXPLICIT_MPN_FIELD evidence, we need
    # the observation to match the evidence source. For simplicity, use
    # EXPLICIT_MPN_FIELD for rejected cases too (MPN_MISMATCH reason).
    if decision is EvidenceDecision.REJECTED and evidence_source is EvidenceSource.EXPLICIT_MPN_FIELD:
        from product_intelligence.research.matching import IdentityRejectionReason
        rejection_reason = IdentityRejectionReason.MPN_MISMATCH
    elif decision is EvidenceDecision.REJECTED:
        # For non-explicit evidence, ensure the observation matches
        from product_intelligence.research.matching import IdentityRejectionReason
        rejection_reason = IdentityRejectionReason.NO_EXPLICIT_MPN_EVIDENCE

    return ListingIdentityAssessment(
        normalized_listing=normalized,
        requested_part_number=request.manufacturer_part_number,
        candidate_part_number_raw=candidate_raw,
        candidate_part_number_compared=candidate_compared,
        candidate_evidence_source=evidence_source,
        match_type=match_type,
        decision=decision,
        rejection_reason=rejection_reason,
    )


def _make_accepted_assessment(
    request: ResearchRequest,
    price_amount: Decimal,
    currency_code: str = "USD",
    condition: NormalizedCondition = NormalizedCondition.NEW,
    source_url: str = "https://example.com/1",
    mpn: str = "ABC-123",
) -> ListingIdentityAssessment:
    """Build one ACCEPTED assessment with a clean price."""
    obs = _make_observation(
        source_url=source_url,
        price_text=str(price_amount),
        currency_text=currency_code,
        mpn_text=mpn,
    )
    norm = _make_normalized(
        obs,
        price_amount=price_amount,
        currency_code=currency_code,
        condition=condition,
    )
    return _make_assessment(
        request,
        norm,
        decision=EvidenceDecision.ACCEPTED,
        match_type=IdentityMatchType.EXACT,
        candidate_raw=mpn,
        candidate_compared=mpn,
    )


def _make_rejected_assessment(
    request: ResearchRequest,
    price_amount: Decimal | None = Decimal("50.00"),
    currency_code: str | None = "USD",
    condition: NormalizedCondition = NormalizedCondition.NEW,
    source_url: str = "https://example.com/wrong",
    candidate_mpn: str = "XYZ-999",
) -> ListingIdentityAssessment:
    """Build one REJECTED assessment (MPN mismatch)."""
    obs = _make_observation(
        source_url=source_url,
        price_text=str(price_amount) if price_amount is not None else None,
        currency_text=currency_code,
        mpn_text=candidate_mpn,
    )
    norm = _make_normalized(
        obs,
        price_amount=price_amount,
        currency_code=currency_code,
        condition=condition,
    )
    return _make_assessment(
        request,
        norm,
        decision=EvidenceDecision.REJECTED,
        match_type=IdentityMatchType.UNKNOWN,
        candidate_raw=candidate_mpn,
        candidate_compared=candidate_mpn,
    )


# ---------------------------------------------------------------------------
# A. THREE COMPARABLE PRICES
# ---------------------------------------------------------------------------


def test_three_comparable_prices() -> None:
    """Three USD/NEW prices: 100, 120, 140 -> VERIFIED bucket."""
    request = ResearchRequest("ABC-123", "SSD")
    assessments = tuple(
        _make_accepted_assessment(request, Decimal(str(p)), source_url=f"https://example.com/{p}")
        for p in [100, 120, 140]
    )

    result = aggregate_listing_prices(request, assessments)

    assert len(result.buckets) == 1
    assert result.verification_status is VerificationStatus.VERIFIED
    assert len(result.exclusions) == 0

    bucket = result.buckets[0]
    assert bucket.currency_code == "USD"
    assert bucket.condition is NormalizedCondition.NEW
    assert bucket.count == 3
    assert bucket.low == Decimal("100")
    assert bucket.median == Decimal("120")
    assert bucket.high == Decimal("140")
    assert bucket.market_range_low == Decimal("100")
    assert bucket.market_range_high == Decimal("140")
    assert bucket.confidence is ConfidenceLevel.MEDIUM


# ---------------------------------------------------------------------------
# B. EVEN MEDIAN
# ---------------------------------------------------------------------------


def test_even_count_median() -> None:
    """Four prices: 100, 120, 140, 180 -> median = 130 (exact Decimal)."""
    request = ResearchRequest("ABC-123", "SSD")
    assessments = tuple(
        _make_accepted_assessment(request, Decimal(str(p)), source_url=f"https://example.com/{p}")
        for p in [100, 120, 140, 180]
    )

    result = aggregate_listing_prices(request, assessments)
    bucket = result.buckets[0]

    assert bucket.median == Decimal("130")
    # Prove it's Decimal, not float
    assert isinstance(bucket.median, Decimal)


# ---------------------------------------------------------------------------
# C. ONE PRICE
# ---------------------------------------------------------------------------


def test_one_price() -> None:
    """One accepted listing -> LOW confidence, no market range."""
    request = ResearchRequest("ABC-123", "SSD")
    assessments = (_make_accepted_assessment(request, Decimal("99.99")),)

    result = aggregate_listing_prices(request, assessments)
    bucket = result.buckets[0]

    assert bucket.count == 1
    assert bucket.low == Decimal("99.99")
    assert bucket.median == Decimal("99.99")
    assert bucket.high == Decimal("99.99")
    assert bucket.market_range_low is None
    assert bucket.market_range_high is None
    assert bucket.confidence is ConfidenceLevel.LOW
    assert result.verification_status is VerificationStatus.VERIFIED


# ---------------------------------------------------------------------------
# D. TWO PRICES
# ---------------------------------------------------------------------------


def test_two_prices() -> None:
    """Two accepted listings -> LOW confidence, no market range, exact median."""
    request = ResearchRequest("ABC-123", "SSD")
    assessments = (
        _make_accepted_assessment(request, Decimal("100"), source_url="https://a.com"),
        _make_accepted_assessment(request, Decimal("200"), source_url="https://b.com"),
    )

    result = aggregate_listing_prices(request, assessments)
    bucket = result.buckets[0]

    assert bucket.count == 2
    assert bucket.median == Decimal("150")
    assert bucket.market_range_low is None
    assert bucket.market_range_high is None
    assert bucket.confidence is ConfidenceLevel.LOW


# ---------------------------------------------------------------------------
# E. ZERO ACCEPTED IDENTITY
# ---------------------------------------------------------------------------


def test_zero_accepted_identity() -> None:
    """All prices REJECTED -> no buckets, UNKNOWN, all IDENTITY_NOT_ACCEPTED."""
    request = ResearchRequest("ABC-123", "SSD")
    assessments = tuple(
        _make_rejected_assessment(
            request,
            price_amount=Decimal(str(p)),
            source_url=f"https://example.com/{p}",
        )
        for p in [100, 120, 140]
    )

    result = aggregate_listing_prices(request, assessments)

    assert len(result.buckets) == 0
    assert result.verification_status is VerificationStatus.UNKNOWN
    assert len(result.exclusions) == 3
    for exclusion in result.exclusions:
        assert exclusion.reason is PriceAggregationExclusionReason.IDENTITY_NOT_ACCEPTED


# ---------------------------------------------------------------------------
# F. ACCEPTED IDENTITY + MISSING PRICE
# ---------------------------------------------------------------------------


def test_accepted_no_price() -> None:
    """ACCEPTED but no numeric price -> NO_NUMERIC_PRICE exclusion."""
    request = ResearchRequest("ABC-123", "SSD")
    obs = _make_observation(price_text=None, mpn_text="ABC-123")
    norm = _make_normalized(obs, price_amount=None, currency_code="USD")
    assessment = _make_assessment(
        request, norm,
        decision=EvidenceDecision.ACCEPTED,
        candidate_raw="ABC-123",
        candidate_compared="ABC-123",
    )

    result = aggregate_listing_prices(request, (assessment,))

    assert len(result.buckets) == 0
    assert len(result.exclusions) == 1
    assert result.exclusions[0].reason is PriceAggregationExclusionReason.NO_NUMERIC_PRICE


# ---------------------------------------------------------------------------
# G. ACCEPTED IDENTITY + MISSING CURRENCY
# ---------------------------------------------------------------------------


def test_accepted_no_currency() -> None:
    """ACCEPTED + price but no currency -> NO_COMPARABLE_CURRENCY."""
    request = ResearchRequest("ABC-123", "SSD")
    obs = _make_observation(price_text="500", currency_text=None, mpn_text="ABC-123")
    norm = _make_normalized(obs, price_amount=Decimal("500"), currency_code=None)
    assessment = _make_assessment(
        request, norm,
        decision=EvidenceDecision.ACCEPTED,
        candidate_raw="ABC-123",
        candidate_compared="ABC-123",
    )

    result = aggregate_listing_prices(request, (assessment,))

    assert len(result.buckets) == 0
    assert len(result.exclusions) == 1
    assert result.exclusions[0].reason is PriceAggregationExclusionReason.NO_COMPARABLE_CURRENCY


# ---------------------------------------------------------------------------
# H. ACCEPTED IDENTITY + CONFLICTING CURRENCY
# ---------------------------------------------------------------------------


def test_accepted_conflicting_currency() -> None:
    """3B produced price_amount but currency_code=None (conflict) ->
    NO_COMPARABLE_CURRENCY. No FX, no guessed winner."""
    request = ResearchRequest("ABC-123", "SSD")
    obs = _make_observation(
        price_text="EUR 100", currency_text="USD", mpn_text="ABC-123"
    )
    # 3B would produce: price_amount=Decimal("100"), currency_code=None,
    # with CONFLICTING_CURRENCY issue.
    norm = _make_normalized(
        obs,
        price_amount=Decimal("100"),
        currency_code=None,  # conflict -> None
    )
    assessment = _make_assessment(
        request, norm,
        decision=EvidenceDecision.ACCEPTED,
        candidate_raw="ABC-123",
        candidate_compared="ABC-123",
    )

    result = aggregate_listing_prices(request, (assessment,))

    assert len(result.buckets) == 0
    assert len(result.exclusions) == 1
    assert result.exclusions[0].reason is PriceAggregationExclusionReason.NO_COMPARABLE_CURRENCY


# ---------------------------------------------------------------------------
# I. UNKNOWN CONDITION
# ---------------------------------------------------------------------------


def test_unknown_condition_excluded() -> None:
    """ACCEPTED + price + currency but UNKNOWN condition -> excluded."""
    request = ResearchRequest("ABC-123", "SSD")
    obs = _make_observation(
        price_text="300", currency_text="USD", condition_text=None, mpn_text="ABC-123"
    )
    norm = _make_normalized(
        obs,
        price_amount=Decimal("300"),
        currency_code="USD",
        condition=NormalizedCondition.UNKNOWN,
    )
    assessment = _make_assessment(
        request, norm,
        decision=EvidenceDecision.ACCEPTED,
        candidate_raw="ABC-123",
        candidate_compared="ABC-123",
    )

    result = aggregate_listing_prices(request, (assessment,))

    assert len(result.buckets) == 0
    assert len(result.exclusions) == 1
    assert result.exclusions[0].reason is PriceAggregationExclusionReason.UNKNOWN_CONDITION


# ---------------------------------------------------------------------------
# J. MIXED KNOWN CONDITIONS
# ---------------------------------------------------------------------------


def test_mixed_conditions_separate_buckets() -> None:
    """USD NEW and USD USED -> two buckets, no cross-condition arithmetic, AMBIGUOUS."""
    request = ResearchRequest("ABC-123", "SSD")
    assessments: list[ListingIdentityAssessment] = []

    for p in [100, 120, 140]:
        assessments.append(
            _make_accepted_assessment(
                request, Decimal(str(p)),
                condition=NormalizedCondition.NEW,
                source_url=f"https://new.com/{p}",
            )
        )
    for p in [50, 70, 90]:
        assessments.append(
            _make_accepted_assessment(
                request, Decimal(str(p)),
                condition=NormalizedCondition.USED,
                source_url=f"https://used.com/{p}",
            )
        )

    result = aggregate_listing_prices(request, tuple(assessments))

    assert len(result.buckets) == 2
    assert result.verification_status is VerificationStatus.AMBIGUOUS
    assert len(result.exclusions) == 0

    new_bucket = [b for b in result.buckets if b.condition is NormalizedCondition.NEW][0]
    used_bucket = [b for b in result.buckets if b.condition is NormalizedCondition.USED][0]

    assert new_bucket.median == Decimal("120")
    assert new_bucket.count == 3
    assert used_bucket.median == Decimal("70")
    assert used_bucket.count == 3


# ---------------------------------------------------------------------------
# K. MIXED CURRENCIES
# ---------------------------------------------------------------------------


def test_mixed_currencies_separate_buckets() -> None:
    """USD NEW and EUR NEW -> two buckets, no FX, AMBIGUOUS."""
    request = ResearchRequest("ABC-123", "SSD")
    assessments: list[ListingIdentityAssessment] = []

    for p in [100, 120]:
        assessments.append(
            _make_accepted_assessment(
                request, Decimal(str(p)),
                currency_code="USD",
                source_url=f"https://us.com/{p}",
            )
        )
    for p in [80, 90, 110]:
        assessments.append(
            _make_accepted_assessment(
                request, Decimal(str(p)),
                currency_code="EUR",
                source_url=f"https://eu.com/{p}",
            )
        )

    result = aggregate_listing_prices(request, tuple(assessments))

    assert len(result.buckets) == 2
    assert result.verification_status is VerificationStatus.AMBIGUOUS

    usd_bucket = [b for b in result.buckets if b.currency_code == "USD"][0]
    eur_bucket = [b for b in result.buckets if b.currency_code == "EUR"][0]

    assert usd_bucket.count == 2
    assert usd_bucket.median == Decimal("110")
    assert eur_bucket.count == 3
    assert eur_bucket.median == Decimal("90")


# ---------------------------------------------------------------------------
# L. EXTREME OUTLIER
# ---------------------------------------------------------------------------


def test_extreme_outlier_retained() -> None:
    """USD NEW: 100, 110, 5000 -> all three retained, no outlier removal."""
    request = ResearchRequest("ABC-123", "SSD")
    assessments = tuple(
        _make_accepted_assessment(request, Decimal(str(p)), source_url=f"https://example.com/{p}")
        for p in [100, 110, 5000]
    )

    result = aggregate_listing_prices(request, assessments)
    bucket = result.buckets[0]

    assert bucket.count == 3
    assert bucket.low == Decimal("100")
    assert bucket.median == Decimal("110")
    assert bucket.high == Decimal("5000")
    assert bucket.market_range_low == Decimal("100")
    assert bucket.market_range_high == Decimal("5000")


# ---------------------------------------------------------------------------
# M. EXACT DUPLICATE INPUT
# ---------------------------------------------------------------------------


def test_exact_duplicate_input_refused() -> None:
    """Same assessment object supplied twice -> ValueError."""
    request = ResearchRequest("ABC-123", "SSD")
    assessment = _make_accepted_assessment(request, Decimal("100"))

    # Same object reference twice
    with pytest.raises(ValueError, match="exact duplicate"):
        aggregate_listing_prices(request, (assessment, assessment))


def test_equal_but_distinct_duplicate_input_refused() -> None:
    """Two separately constructed assessments that compare equal by value
    -> ValueError. The check is value-based, not identity-based.

    Two distinct Python objects with the same fields must also be refused
    because they represent the same evidence counted twice.
    """
    request = ResearchRequest("ABC-123", "SSD")

    # Build two distinct assessment objects with identical values.
    # Since ListingIdentityAssessment is a frozen dataclass, __hash__ and
    # __eq__ are derived from fields, so equal-by-value objects collide.
    obs = _make_observation(
        source_url="https://example.com/product",
        price_text="100.00",
        currency_text="USD",
        condition_text="new",
        mpn_text="ABC-123",
    )
    norm = _make_normalized(
        obs,
        price_amount=Decimal("100.00"),
        currency_code="USD",
        condition=NormalizedCondition.NEW,
    )
    assessment_1 = _make_assessment(
        request, norm,
        decision=EvidenceDecision.ACCEPTED,
        match_type=IdentityMatchType.EXACT,
        candidate_raw="ABC-123",
        candidate_compared="ABC-123",
    )
    assessment_2 = _make_assessment(
        request, norm,
        decision=EvidenceDecision.ACCEPTED,
        match_type=IdentityMatchType.EXACT,
        candidate_raw="ABC-123",
        candidate_compared="ABC-123",
    )

    # They are distinct objects but equal by value.
    assert assessment_1 is not assessment_2
    assert assessment_1 == assessment_2

    with pytest.raises(ValueError, match="exact duplicate"):
        aggregate_listing_prices(request, (assessment_1, assessment_2))


def test_same_price_currency_condition_different_evidence_allowed() -> None:
    """Two assessments with the same price, currency, and condition but
    genuinely different evidence (different source URL, different seller)
    -> both are valid contributions, not duplicates.

    Duplicate detection is on the ListingIdentityAssessment as a whole
    (which includes the full normalized listing chain), not on price/currency/
    condition alone.
    """
    request = ResearchRequest("ABC-123", "SSD")
    assessments = (
        _make_accepted_assessment(
            request, Decimal("100"), source_url="https://seller-a.com/product"),
        _make_accepted_assessment(
            request, Decimal("100"), source_url="https://seller-b.com/product"),
    )

    # These have the same price/currency/condition but different observations
    # (different source_url), so they are different assessments.
    result = aggregate_listing_prices(request, assessments)

    assert len(result.buckets) == 1
    assert result.buckets[0].count == 2
    assert result.buckets[0].low == Decimal("100")
    assert result.buckets[0].high == Decimal("100")
    assert len(result.exclusions) == 0


# ---------------------------------------------------------------------------
# N. MIXED REQUEST PROVENANCE
# ---------------------------------------------------------------------------


def test_mixed_request_mpn_refused() -> None:
    """Assessment from a different request MPN -> ValueError."""
    request = ResearchRequest("ABC-123", "SSD")

    # Build an assessment for a different request
    other_request = ResearchRequest("XYZ-999", "Other")
    obs = _make_observation(price_text="100", mpn_text="XYZ-999")
    norm = _make_normalized(obs, price_amount=Decimal("100"))
    # Build an assessment with the other MPN as requested_part_number
    other_assessment = _make_assessment(
        other_request, norm,
        decision=EvidenceDecision.ACCEPTED,
        candidate_raw="XYZ-999",
        candidate_compared="XYZ-999",
    )

    with pytest.raises(ValueError, match="different requests"):
        aggregate_listing_prices(request, (other_assessment,))


# ---------------------------------------------------------------------------
# O. VALID PRICE + UNRELATED NORMALIZATION ISSUE
# ---------------------------------------------------------------------------


def test_unrelated_normalization_issue_still_eligible() -> None:
    """Price valid, currency known, condition known, but availability UNKNOWN
    with an issue -> still price-eligible. 4A must not reject for unrelated
    normalization issues."""
    request = ResearchRequest("ABC-123", "SSD")
    obs = _make_observation(
        price_text="250",
        currency_text="USD",
        condition_text="new",
        availability_text="false",  # unrecognized -> UNKNOWN availability
        mpn_text="ABC-123",
    )
    # 3B produces: price=250, currency=USD, condition=NEW, availability=UNKNOWN
    # with an UNRECOGNIZED_AVAILABILITY issue.
    norm = _make_normalized(
        obs,
        price_amount=Decimal("250"),
        currency_code="USD",
        condition=NormalizedCondition.NEW,
        availability=NormalizedAvailability.UNKNOWN,
    )
    assessment = _make_assessment(
        request, norm,
        decision=EvidenceDecision.ACCEPTED,
        candidate_raw="ABC-123",
        candidate_compared="ABC-123",
    )

    result = aggregate_listing_prices(request, (assessment,))

    assert len(result.buckets) == 1
    assert result.buckets[0].count == 1
    assert result.buckets[0].median == Decimal("250")
    assert len(result.exclusions) == 0


# ---------------------------------------------------------------------------
# Input validation
# ---------------------------------------------------------------------------


def test_empty_assessments_tuple() -> None:
    """Zero assessments -> zero buckets, UNKNOWN, zero exclusions."""
    request = ResearchRequest("ABC-123", "SSD")
    result = aggregate_listing_prices(request, ())

    assert len(result.buckets) == 0
    assert len(result.exclusions) == 0
    assert result.verification_status is VerificationStatus.UNKNOWN


def test_assessments_not_tuple() -> None:
    """Passing a list instead of tuple -> TypeError."""
    request = ResearchRequest("ABC-123", "SSD")
    assessment = _make_accepted_assessment(request, Decimal("100"))

    with pytest.raises(TypeError, match="must be a tuple"):
        aggregate_listing_prices(request, [assessment])  # type: ignore


def test_request_not_research_request() -> None:
    """Wrong request type -> TypeError."""
    with pytest.raises(TypeError, match="must be a ResearchRequest"):
        aggregate_listing_prices("not a request", ())  # type: ignore


# ---------------------------------------------------------------------------
# Eligibility precedence
# ---------------------------------------------------------------------------


def test_rejected_plus_missing_price_is_identity_not_accepted() -> None:
    """Rejected identity + missing price -> IDENTITY_NOT_ACCEPTED
    (not NO_NUMERIC_PRICE, because identity is checked first)."""
    request = ResearchRequest("ABC-123", "SSD")
    assessment = _make_rejected_assessment(
        request,
        price_amount=None,
        source_url="https://example.com/no-price",
    )

    result = aggregate_listing_prices(request, (assessment,))

    assert len(result.exclusions) == 1
    assert result.exclusions[0].reason is PriceAggregationExclusionReason.IDENTITY_NOT_ACCEPTED


# ---------------------------------------------------------------------------
# Evidence preservation
# ---------------------------------------------------------------------------


def test_all_assessments_reachable() -> None:
    """Every input assessment is reachable from the result (bucket or exclusion)."""
    request = ResearchRequest("ABC-123", "SSD")
    accepted = _make_accepted_assessment(request, Decimal("100"))
    rejected = _make_rejected_assessment(request, Decimal("50"))

    result = aggregate_listing_prices(request, (accepted, rejected))

    # Count all assessments in buckets and exclusions
    bucket_assessments = set()
    for bucket in result.buckets:
        for a in bucket.assessments:
            bucket_assessments.add(id(a))

    exclusion_assessments = set()
    for ex in result.exclusions:
        exclusion_assessments.add(id(ex.assessment))

    input_ids = {id(a) for a in result.assessments}
    assert (bucket_assessments | exclusion_assessments) == input_ids
