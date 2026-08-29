"""Contract-fabrication tests for 4A price aggregation.

Prove that directly constructed public 4A contracts reject materially
impossible states. These tests bypass the normal builder entirely and
construct contracts by hand to check the __post_init__ invariants.
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
# Helpers: build a minimal accepted assessment for bucket testing
# ---------------------------------------------------------------------------


def _make_accepted_assessment_for_test(
    price: Decimal,
    currency: str = "USD",
    condition: NormalizedCondition = NormalizedCondition.NEW,
) -> ListingIdentityAssessment:
    """Build an ACCEPTED assessment for invariant testing."""
    obs = ListingObservation(
        source_url="https://example.com/test",
        extraction_method=ExtractionMethod.JSON_LD,
        manufacturer_part_number_text="ABC-123",
        price_text=str(price),
        currency_text=currency,
        condition_text="new",
    )
    norm = NormalizedListingObservation(
        observation=obs,
        price_amount=price,
        currency_code=currency,
        availability=NormalizedAvailability.UNKNOWN,
        condition=condition,
        seller_name=None,
        normalization_issues=(),
    )
    return ListingIdentityAssessment(
        normalized_listing=norm,
        requested_part_number="ABC-123",
        candidate_part_number_raw="ABC-123",
        candidate_part_number_compared="ABC-123",
        candidate_evidence_source=EvidenceSource.EXPLICIT_MPN_FIELD,
        match_type=IdentityMatchType.EXACT,
        decision=EvidenceDecision.ACCEPTED,
        rejection_reason=None,
    )


def _make_rejected_assessment_for_test(
    price: Decimal | None = Decimal("50"),
    currency: str | None = "USD",
    condition: NormalizedCondition = NormalizedCondition.NEW,
) -> ListingIdentityAssessment:
    """Build a REJECTED assessment for exclusion testing."""
    obs = ListingObservation(
        source_url="https://example.com/rejected",
        extraction_method=ExtractionMethod.JSON_LD,
        manufacturer_part_number_text="XYZ-999",
        price_text=str(price) if price is not None else None,
        currency_text=currency,
        condition_text="new",
    )
    norm = NormalizedListingObservation(
        observation=obs,
        price_amount=price,
        currency_code=currency,
        availability=NormalizedAvailability.UNKNOWN,
        condition=condition,
        seller_name=None,
        normalization_issues=(),
    )
    from product_intelligence.research.matching import IdentityRejectionReason
    return ListingIdentityAssessment(
        normalized_listing=norm,
        requested_part_number="ABC-123",
        candidate_part_number_raw="XYZ-999",
        candidate_part_number_compared="XYZ-999",
        candidate_evidence_source=EvidenceSource.EXPLICIT_MPN_FIELD,
        match_type=IdentityMatchType.UNKNOWN,
        decision=EvidenceDecision.REJECTED,
        rejection_reason=IdentityRejectionReason.MPN_MISMATCH,
    )


# ---------------------------------------------------------------------------
# PriceAggregateBucket fabrication tests
# ---------------------------------------------------------------------------


class TestPriceAggregateBucketFabrication:
    """Direct construction of PriceAggregateBucket must reject impossible states."""

    def test_empty_assessments_refused(self) -> None:
        """A bucket must contain at least one assessment."""
        with pytest.raises(ValueError, match="at least one"):
            PriceAggregateBucket(
                currency_code="USD",
                condition=NormalizedCondition.NEW,
                assessments=(),
                count=0,
                low=Decimal("0"),
                median=Decimal("0"),
                high=Decimal("0"),
                market_range_low=None,
                market_range_high=None,
                confidence=ConfidenceLevel.LOW,
            )

    def test_count_inconsistent_with_assessments(self) -> None:
        """Bucket count != len(assessments) -> ValueError."""
        a1 = _make_accepted_assessment_for_test(Decimal("100"))
        a2 = _make_accepted_assessment_for_test(Decimal("200"))
        with pytest.raises(ValueError, match="count"):
            PriceAggregateBucket(
                currency_code="USD",
                condition=NormalizedCondition.NEW,
                assessments=(a1, a2),
                count=1,  # wrong
                low=Decimal("100"),
                median=Decimal("150"),
                high=Decimal("200"),
                market_range_low=None,
                market_range_high=None,
                confidence=ConfidenceLevel.LOW,
            )

    def test_low_inconsistent_with_prices(self) -> None:
        """low != recomputed minimum -> ValueError."""
        a1 = _make_accepted_assessment_for_test(Decimal("100"))
        with pytest.raises(ValueError, match="low"):
            PriceAggregateBucket(
                currency_code="USD",
                condition=NormalizedCondition.NEW,
                assessments=(a1,),
                count=1,
                low=Decimal("50"),  # wrong
                median=Decimal("100"),
                high=Decimal("100"),
                market_range_low=None,
                market_range_high=None,
                confidence=ConfidenceLevel.LOW,
            )

    def test_median_inconsistent_with_prices(self) -> None:
        """median != recomputed median -> ValueError."""
        a1 = _make_accepted_assessment_for_test(Decimal("100"))
        a2 = _make_accepted_assessment_for_test(Decimal("200"))
        with pytest.raises(ValueError, match="median"):
            PriceAggregateBucket(
                currency_code="USD",
                condition=NormalizedCondition.NEW,
                assessments=(a1, a2),
                count=2,
                low=Decimal("100"),
                median=Decimal("100"),  # wrong (should be 150)
                high=Decimal("200"),
                market_range_low=None,
                market_range_high=None,
                confidence=ConfidenceLevel.LOW,
            )

    def test_high_inconsistent_with_prices(self) -> None:
        """high != recomputed maximum -> ValueError."""
        a1 = _make_accepted_assessment_for_test(Decimal("100"))
        with pytest.raises(ValueError, match="high"):
            PriceAggregateBucket(
                currency_code="USD",
                condition=NormalizedCondition.NEW,
                assessments=(a1,),
                count=1,
                low=Decimal("100"),
                median=Decimal("100"),
                high=Decimal("999"),  # wrong
                market_range_low=None,
                market_range_high=None,
                confidence=ConfidenceLevel.LOW,
            )

    def test_currency_inconsistent_with_member(self) -> None:
        """Bucket currency != a member's currency -> ValueError."""
        a1 = _make_accepted_assessment_for_test(Decimal("100"), currency="EUR")
        with pytest.raises(ValueError, match="currency"):
            PriceAggregateBucket(
                currency_code="USD",  # wrong vs EUR
                condition=NormalizedCondition.NEW,
                assessments=(a1,),
                count=1,
                low=Decimal("100"),
                median=Decimal("100"),
                high=Decimal("100"),
                market_range_low=None,
                market_range_high=None,
                confidence=ConfidenceLevel.LOW,
            )

    def test_condition_inconsistent_with_member(self) -> None:
        """Bucket condition != a member's condition -> ValueError."""
        a1 = _make_accepted_assessment_for_test(
            Decimal("100"), condition=NormalizedCondition.USED
        )
        with pytest.raises(ValueError, match="condition"):
            PriceAggregateBucket(
                currency_code="USD",
                condition=NormalizedCondition.NEW,  # wrong vs USED
                assessments=(a1,),
                count=1,
                low=Decimal("100"),
                median=Decimal("100"),
                high=Decimal("100"),
                market_range_low=None,
                market_range_high=None,
                confidence=ConfidenceLevel.LOW,
            )

    def test_unknown_condition_in_bucket_refused(self) -> None:
        """A bucket containing UNKNOWN condition -> ValueError."""
        obs = ListingObservation(
            source_url="https://example.com/unknown-cond",
            extraction_method=ExtractionMethod.JSON_LD,
            manufacturer_part_number_text="ABC-123",
            price_text="100",
            currency_text="USD",
        )
        norm = NormalizedListingObservation(
            observation=obs,
            price_amount=Decimal("100"),
            currency_code="USD",
            availability=NormalizedAvailability.UNKNOWN,
            condition=NormalizedCondition.UNKNOWN,
            seller_name=None,
            normalization_issues=(),
        )
        assessment = ListingIdentityAssessment(
            normalized_listing=norm,
            requested_part_number="ABC-123",
            candidate_part_number_raw="ABC-123",
            candidate_part_number_compared="ABC-123",
            candidate_evidence_source=EvidenceSource.EXPLICIT_MPN_FIELD,
            match_type=IdentityMatchType.EXACT,
            decision=EvidenceDecision.ACCEPTED,
            rejection_reason=None,
        )
        with pytest.raises(ValueError, match="UNKNOWN condition"):
            PriceAggregateBucket(
                currency_code="USD",
                condition=NormalizedCondition.UNKNOWN,
                assessments=(assessment,),
                count=1,
                low=Decimal("100"),
                median=Decimal("100"),
                high=Decimal("100"),
                market_range_low=None,
                market_range_high=None,
                confidence=ConfidenceLevel.LOW,
            )

    def test_rejected_assessment_in_bucket_refused(self) -> None:
        """A bucket containing a 3C-REJECTED assessment -> ValueError."""
        rejected = _make_rejected_assessment_for_test()
        with pytest.raises(ValueError, match="ACCEPTED"):
            PriceAggregateBucket(
                currency_code="USD",
                condition=NormalizedCondition.NEW,
                assessments=(rejected,),
                count=1,
                low=Decimal("50"),
                median=Decimal("50"),
                high=Decimal("50"),
                market_range_low=None,
                market_range_high=None,
                confidence=ConfidenceLevel.LOW,
            )

    def test_float_price_already_refused_by_3b(self) -> None:
        """A float price is already refused by NormalizedListingObservation
        (3B). The bucket's check catches any further bypass. Since we can't
        construct a NormalizedListingObservation with a float price (3B
        rejects it), this test verifies the 3B invariant still holds."""
        obs = ListingObservation(
            source_url="https://example.com/float",
            extraction_method=ExtractionMethod.JSON_LD,
            manufacturer_part_number_text="ABC-123",
            price_text="100",
            currency_text="USD",
            condition_text="new",
        )
        # 3B already rejects float prices, so this should raise TypeError
        # at the 3B level before reaching the bucket check.
        with pytest.raises(TypeError, match="float"):
            NormalizedListingObservation(
                observation=obs,
                price_amount=float("100"),  # float, not Decimal
                currency_code="USD",
                availability=NormalizedAvailability.UNKNOWN,
                condition=NormalizedCondition.NEW,
                seller_name=None,
                normalization_issues=(),
            )

    def test_low_confidence_for_count_3_refused(self) -> None:
        """3 assessments -> MEDIUM required, LOW rejected."""
        assessments = tuple(
            _make_accepted_assessment_for_test(Decimal(str(p)))
            for p in [100, 120, 140]
        )
        with pytest.raises(ValueError, match="confidence"):
            PriceAggregateBucket(
                currency_code="USD",
                condition=NormalizedCondition.NEW,
                assessments=assessments,
                count=3,
                low=Decimal("100"),
                median=Decimal("120"),
                high=Decimal("140"),
                market_range_low=Decimal("100"),
                market_range_high=Decimal("140"),
                confidence=ConfidenceLevel.LOW,  # wrong for count=3
            )

    def test_market_range_present_for_count_1_refused(self) -> None:
        """1 observation but market range present -> ValueError."""
        a1 = _make_accepted_assessment_for_test(Decimal("100"))
        with pytest.raises(ValueError, match="< 3"):
            PriceAggregateBucket(
                currency_code="USD",
                condition=NormalizedCondition.NEW,
                assessments=(a1,),
                count=1,
                low=Decimal("100"),
                median=Decimal("100"),
                high=Decimal("100"),
                market_range_low=Decimal("100"),  # wrong for count=1
                market_range_high=Decimal("100"),
                confidence=ConfidenceLevel.LOW,
            )

    def test_market_range_missing_for_count_3_refused(self) -> None:
        """3 observations but market range None -> ValueError."""
        assessments = tuple(
            _make_accepted_assessment_for_test(Decimal(str(p)))
            for p in [100, 120, 140]
        )
        with pytest.raises(ValueError, match=">= 3"):
            PriceAggregateBucket(
                currency_code="USD",
                condition=NormalizedCondition.NEW,
                assessments=assessments,
                count=3,
                low=Decimal("100"),
                median=Decimal("120"),
                high=Decimal("140"),
                market_range_low=None,  # wrong for count=3
                market_range_high=None,
                confidence=ConfidenceLevel.MEDIUM,
            )

    def test_high_confidence_refused(self) -> None:
        """4A must never produce HIGH confidence."""
        a1 = _make_accepted_assessment_for_test(Decimal("100"))
        with pytest.raises(ValueError, match="HIGH"):
            PriceAggregateBucket(
                currency_code="USD",
                condition=NormalizedCondition.NEW,
                assessments=(a1,),
                count=1,
                low=Decimal("100"),
                median=Decimal("100"),
                high=Decimal("100"),
                market_range_low=None,
                market_range_high=None,
                confidence=ConfidenceLevel.HIGH,  # 4A never produces HIGH
            )

    # -- Type validation for bucket result fields --

    def test_low_float_refused(self) -> None:
        """low=100.0 (float) -> TypeError."""
        a1 = _make_accepted_assessment_for_test(Decimal("100"))
        with pytest.raises(TypeError, match="low"):
            PriceAggregateBucket(
                currency_code="USD",
                condition=NormalizedCondition.NEW,
                assessments=(a1,),
                count=1,
                low=100.0,  # float
                median=Decimal("100"),
                high=Decimal("100"),
                market_range_low=None,
                market_range_high=None,
                confidence=ConfidenceLevel.LOW,
            )

    def test_median_int_refused(self) -> None:
        """median=100 (int) -> TypeError."""
        a1 = _make_accepted_assessment_for_test(Decimal("100"))
        with pytest.raises(TypeError, match="median"):
            PriceAggregateBucket(
                currency_code="USD",
                condition=NormalizedCondition.NEW,
                assessments=(a1,),
                count=1,
                low=Decimal("100"),
                median=100,  # int
                high=Decimal("100"),
                market_range_low=None,
                market_range_high=None,
                confidence=ConfidenceLevel.LOW,
            )

    def test_high_float_refused(self) -> None:
        """high=100.0 (float) -> TypeError."""
        a1 = _make_accepted_assessment_for_test(Decimal("100"))
        with pytest.raises(TypeError, match="high"):
            PriceAggregateBucket(
                currency_code="USD",
                condition=NormalizedCondition.NEW,
                assessments=(a1,),
                count=1,
                low=Decimal("100"),
                median=Decimal("100"),
                high=100.0,  # float
                market_range_low=None,
                market_range_high=None,
                confidence=ConfidenceLevel.LOW,
            )

    def test_count_bool_refused(self) -> None:
        """count=True (bool, subclass of int) -> TypeError."""
        a1 = _make_accepted_assessment_for_test(Decimal("100"))
        with pytest.raises(TypeError, match="count"):
            PriceAggregateBucket(
                currency_code="USD",
                condition=NormalizedCondition.NEW,
                assessments=(a1,),
                count=True,  # bool
                low=Decimal("100"),
                median=Decimal("100"),
                high=Decimal("100"),
                market_range_low=None,
                market_range_high=None,
                confidence=ConfidenceLevel.LOW,
            )

    def test_confidence_string_refused(self) -> None:
        """confidence="LOW" (string, not ConfidenceLevel) -> TypeError."""
        a1 = _make_accepted_assessment_for_test(Decimal("100"))
        with pytest.raises(TypeError, match="confidence"):
            PriceAggregateBucket(
                currency_code="USD",
                condition=NormalizedCondition.NEW,
                assessments=(a1,),
                count=1,
                low=Decimal("100"),
                median=Decimal("100"),
                high=Decimal("100"),
                market_range_low=None,
                market_range_high=None,
                confidence="LOW",  # type: ignore  # string, not enum
            )

    def test_market_range_low_float_refused(self) -> None:
        """market_range_low=100.0 (float) -> TypeError."""
        assessments = tuple(
            _make_accepted_assessment_for_test(Decimal(str(p)))
            for p in [100, 120, 140]
        )
        with pytest.raises(TypeError, match="market_range_low"):
            PriceAggregateBucket(
                currency_code="USD",
                condition=NormalizedCondition.NEW,
                assessments=assessments,
                count=3,
                low=Decimal("100"),
                median=Decimal("120"),
                high=Decimal("140"),
                market_range_low=100.0,  # float
                market_range_high=Decimal("140"),
                confidence=ConfidenceLevel.MEDIUM,
            )

    # -- One-sided market range --

    def test_one_sided_range_low_only_refused(self) -> None:
        """market_range_low present but market_range_high None -> ValueError."""
        a1 = _make_accepted_assessment_for_test(Decimal("100"))
        with pytest.raises(ValueError, match="one-sided"):
            PriceAggregateBucket(
                currency_code="USD",
                condition=NormalizedCondition.NEW,
                assessments=(a1,),
                count=1,
                low=Decimal("100"),
                median=Decimal("100"),
                high=Decimal("100"),
                market_range_low=Decimal("100"),  # present
                market_range_high=None,  # absent
                confidence=ConfidenceLevel.LOW,
            )

    def test_one_sided_range_high_only_refused(self) -> None:
        """market_range_low None but market_range_high present -> ValueError."""
        a1 = _make_accepted_assessment_for_test(Decimal("100"))
        with pytest.raises(ValueError, match="one-sided"):
            PriceAggregateBucket(
                currency_code="USD",
                condition=NormalizedCondition.NEW,
                assessments=(a1,),
                count=1,
                low=Decimal("100"),
                median=Decimal("100"),
                high=Decimal("100"),
                market_range_low=None,  # absent
                market_range_high=Decimal("100"),  # present
                confidence=ConfidenceLevel.LOW,
            )

    # -- Duplicate assessment refusal (shared with PriceAggregationResult) --

    def test_bucket_same_object_twice_refused(self) -> None:
        """Same assessment object reference twice in bucket -> ValueError.

        PriceAggregateBucket itself must refuse (a1, a1) rather than
        silently computing count=2 over duplicated evidence."""
        a1 = _make_accepted_assessment_for_test(Decimal("100"))
        with pytest.raises(ValueError, match="exact duplicate"):
            PriceAggregateBucket(
                currency_code="USD",
                condition=NormalizedCondition.NEW,
                assessments=(a1, a1),
                count=2,
                low=Decimal("100"),
                median=Decimal("100"),
                high=Decimal("100"),
                market_range_low=None,
                market_range_high=None,
                confidence=ConfidenceLevel.LOW,
            )

    def test_bucket_equal_but_distinct_duplicate_refused(self) -> None:
        """Two distinct objects equal by value in bucket -> ValueError.

        a1 is not a2, but a1 == a2 (same fields). The check is
        value-based, not identity-based."""
        a1 = _make_accepted_assessment_for_test(Decimal("100"))
        a2 = _make_accepted_assessment_for_test(Decimal("100"))

        assert a1 is not a2
        assert a1 == a2

        with pytest.raises(ValueError, match="exact duplicate"):
            PriceAggregateBucket(
                currency_code="USD",
                condition=NormalizedCondition.NEW,
                assessments=(a1, a2),
                count=2,
                low=Decimal("100"),
                median=Decimal("100"),
                high=Decimal("100"),
                market_range_low=None,
                market_range_high=None,
                confidence=ConfidenceLevel.LOW,
            )

    def test_bucket_different_assessments_same_price_allowed(self) -> None:
        """Two genuinely different assessments with the same price,
        currency, and condition -> both valid, count=2.

        Duplicate detection is on the full assessment (which carries
        the entire observation chain), not on price/currency/condition
        alone."""
        obs_a = ListingObservation(
            source_url="https://seller-a.com/product",
            extraction_method=ExtractionMethod.JSON_LD,
            manufacturer_part_number_text="ABC-123",
            price_text="100",
            currency_text="USD",
            condition_text="new",
        )
        obs_b = ListingObservation(
            source_url="https://seller-b.com/product",
            extraction_method=ExtractionMethod.JSON_LD,
            manufacturer_part_number_text="ABC-123",
            price_text="100",
            currency_text="USD",
            condition_text="new",
        )
        norm_a = NormalizedListingObservation(
            observation=obs_a,
            price_amount=Decimal("100"),
            currency_code="USD",
            availability=NormalizedAvailability.UNKNOWN,
            condition=NormalizedCondition.NEW,
            seller_name=None,
            normalization_issues=(),
        )
        norm_b = NormalizedListingObservation(
            observation=obs_b,
            price_amount=Decimal("100"),
            currency_code="USD",
            availability=NormalizedAvailability.UNKNOWN,
            condition=NormalizedCondition.NEW,
            seller_name=None,
            normalization_issues=(),
        )
        a1 = ListingIdentityAssessment(
            normalized_listing=norm_a,
            requested_part_number="ABC-123",
            candidate_part_number_raw="ABC-123",
            candidate_part_number_compared="ABC-123",
            candidate_evidence_source=EvidenceSource.EXPLICIT_MPN_FIELD,
            match_type=IdentityMatchType.EXACT,
            decision=EvidenceDecision.ACCEPTED,
            rejection_reason=None,
        )
        a2 = ListingIdentityAssessment(
            normalized_listing=norm_b,
            requested_part_number="ABC-123",
            candidate_part_number_raw="ABC-123",
            candidate_part_number_compared="ABC-123",
            candidate_evidence_source=EvidenceSource.EXPLICIT_MPN_FIELD,
            match_type=IdentityMatchType.EXACT,
            decision=EvidenceDecision.ACCEPTED,
            rejection_reason=None,
        )

        assert a1 is not a2
        assert a1 != a2  # different observations -> different assessments

        bucket = PriceAggregateBucket(
            currency_code="USD",
            condition=NormalizedCondition.NEW,
            assessments=(a1, a2),
            count=2,
            low=Decimal("100"),
            median=Decimal("100"),
            high=Decimal("100"),
            market_range_low=None,
            market_range_high=None,
            confidence=ConfidenceLevel.LOW,
        )
        assert bucket.count == 2
        assert len(bucket.assessments) == 2


# ---------------------------------------------------------------------------
# PriceAggregationExclusion fabrication tests
# ---------------------------------------------------------------------------


class TestPriceAggregationExclusionFabrication:
    """Direct construction of PriceAggregationExclusion must reject contradictions."""

    def test_identity_not_accepted_with_accepted_assessment(self) -> None:
        """IDENTITY_NOT_ACCEPTED reason on an ACCEPTED assessment -> ValueError."""
        accepted = _make_accepted_assessment_for_test(Decimal("100"))
        with pytest.raises(ValueError, match="IDENTITY_NOT_ACCEPTED"):
            PriceAggregationExclusion(
                assessment=accepted,
                reason=PriceAggregationExclusionReason.IDENTITY_NOT_ACCEPTED,
            )

    def test_no_numeric_price_with_accepted_and_price(self) -> None:
        """NO_NUMERIC_PRICE on an ACCEPTED with a price -> ValueError."""
        accepted = _make_accepted_assessment_for_test(Decimal("100"))
        with pytest.raises(ValueError, match="NO_NUMERIC_PRICE"):
            PriceAggregationExclusion(
                assessment=accepted,
                reason=PriceAggregationExclusionReason.NO_NUMERIC_PRICE,
            )

    def test_no_comparable_currency_with_accepted_price_and_currency(self) -> None:
        """NO_COMPARABLE_CURRENCY when currency is present -> ValueError."""
        accepted = _make_accepted_assessment_for_test(Decimal("100"))
        with pytest.raises(ValueError, match="NO_COMPARABLE_CURRENCY"):
            PriceAggregationExclusion(
                assessment=accepted,
                reason=PriceAggregationExclusionReason.NO_COMPARABLE_CURRENCY,
            )

    def test_unknown_condition_with_known_condition(self) -> None:
        """UNKNOWN_CONDITION when condition is known -> ValueError."""
        accepted = _make_accepted_assessment_for_test(
            Decimal("100"), condition=NormalizedCondition.NEW
        )
        with pytest.raises(ValueError, match="UNKNOWN_CONDITION"):
            PriceAggregationExclusion(
                assessment=accepted,
                reason=PriceAggregationExclusionReason.UNKNOWN_CONDITION,
            )

    def test_no_numeric_price_with_rejected_identity(self) -> None:
        """NO_NUMERIC_PRICE on a REJECTED assessment -> ValueError
        (identity checked first)."""
        rejected = _make_rejected_assessment_for_test()
        with pytest.raises(ValueError, match="NO_NUMERIC_PRICE"):
            PriceAggregationExclusion(
                assessment=rejected,
                reason=PriceAggregationExclusionReason.NO_NUMERIC_PRICE,
            )


# ---------------------------------------------------------------------------
# PriceAggregationResult fabrication tests
# ---------------------------------------------------------------------------


class TestPriceAggregationResultFabrication:
    """Direct construction of PriceAggregationResult must reject impossible states."""

    def test_verified_with_zero_buckets(self) -> None:
        """VERIFIED status but zero buckets -> ValueError."""
        request = ResearchRequest("ABC-123", "SSD")
        with pytest.raises(ValueError, match="zero buckets"):
            PriceAggregationResult(
                request=request,
                assessments=(),
                exclusions=(),
                buckets=(),
                verification_status=VerificationStatus.VERIFIED,
            )

    def test_unknown_with_bucket(self) -> None:
        """UNKNOWN status but a bucket exists -> ValueError."""
        request = ResearchRequest("ABC-123", "SSD")
        a1 = _make_accepted_assessment_for_test(Decimal("100"))
        bucket = PriceAggregateBucket(
            currency_code="USD",
            condition=NormalizedCondition.NEW,
            assessments=(a1,),
            count=1,
            low=Decimal("100"),
            median=Decimal("100"),
            high=Decimal("100"),
            market_range_low=None,
            market_range_high=None,
            confidence=ConfidenceLevel.LOW,
        )
        with pytest.raises(ValueError, match="one bucket"):
            PriceAggregationResult(
                request=request,
                assessments=(a1,),
                exclusions=(),
                buckets=(bucket,),
                verification_status=VerificationStatus.UNKNOWN,
            )

    def test_assessment_dropped_from_both(self) -> None:
        """Input assessment appears in neither bucket nor exclusion -> ValueError."""
        request = ResearchRequest("ABC-123", "SSD")
        a1 = _make_accepted_assessment_for_test(Decimal("100"))
        with pytest.raises(ValueError, match="do not appear"):
            PriceAggregationResult(
                request=request,
                assessments=(a1,),  # supplied as input
                exclusions=(),      # not in exclusion
                buckets=(),         # not in bucket
                verification_status=VerificationStatus.UNKNOWN,
            )

    def test_assessment_duplicated_across_buckets_refused(self) -> None:
        """Same assessment appears in two different buckets -> ValueError.
        An assessment has one currency and one condition, so both buckets
        must match those values for the bucket constructors to accept it."""
        request = ResearchRequest("ABC-123", "SSD")
        a1 = _make_accepted_assessment_for_test(Decimal("100"))
        bucket_1 = PriceAggregateBucket(
            currency_code="USD",
            condition=NormalizedCondition.NEW,
            assessments=(a1,),
            count=1,
            low=Decimal("100"),
            median=Decimal("100"),
            high=Decimal("100"),
            market_range_low=None,
            market_range_high=None,
            confidence=ConfidenceLevel.LOW,
        )
        # Fabricate a second bucket with the same assessment.
        # Since a1 has currency=USD and condition=NEW, the second bucket must
        # also claim USD+NEW for the bucket constructor to accept it. This
        # triggers the result's multiplicity check (input has 1, output has 2).
        bucket_2 = PriceAggregateBucket(
            currency_code="USD",
            condition=NormalizedCondition.NEW,  # same key as bucket_1
            assessments=(a1,),  # same object in second bucket
            count=1,
            low=Decimal("100"),
            median=Decimal("100"),
            high=Decimal("100"),
            market_range_low=None,
            market_range_high=None,
            confidence=ConfidenceLevel.LOW,
        )
        # This hits the multiplicity check first (input has 1, output has 2),
        # then would hit the duplicate bucket key check.
        with pytest.raises(ValueError, match="exactly once"):
            PriceAggregationResult(
                request=request,
                assessments=(a1,),
                exclusions=(),
                buckets=(bucket_1, bucket_2),
                verification_status=VerificationStatus.AMBIGUOUS,
            )

    def test_assessment_duplicated_in_exclusions_refused(self) -> None:
        """Same assessment appears twice in exclusions -> ValueError."""
        request = ResearchRequest("ABC-123", "SSD")
        rejected = _make_rejected_assessment_for_test()
        exclusion = PriceAggregationExclusion(
            assessment=rejected,
            reason=PriceAggregationExclusionReason.IDENTITY_NOT_ACCEPTED,
        )
        with pytest.raises(ValueError, match="exactly once"):
            PriceAggregationResult(
                request=request,
                assessments=(rejected,),
                exclusions=(exclusion, exclusion),  # same exclusion twice
                buckets=(),
                verification_status=VerificationStatus.UNKNOWN,
            )

    def test_assessment_invented_by_result_refused(self) -> None:
        """An assessment in a bucket/exclusion that was not in the input
        raises ValueError. This is the 'invented evidence' guard."""
        request = ResearchRequest("ABC-123", "SSD")
        a1 = _make_accepted_assessment_for_test(Decimal("100"))
        bucket = PriceAggregateBucket(
            currency_code="USD",
            condition=NormalizedCondition.NEW,
            assessments=(a1,),
            count=1,
            low=Decimal("100"),
            median=Decimal("100"),
            high=Decimal("100"),
            market_range_low=None,
            market_range_high=None,
            confidence=ConfidenceLevel.LOW,
        )
        # a1 is in the bucket but not in the input assessments tuple
        with pytest.raises(ValueError, match="were not.*supplied"):
            PriceAggregationResult(
                request=request,
                assessments=(),  # a1 not here
                exclusions=(),
                buckets=(bucket,),  # but a1 is here
                verification_status=VerificationStatus.VERIFIED,
            )

    def test_ambiguous_status_for_one_bucket(self) -> None:
        """AMBIGUOUS status for exactly one bucket -> ValueError."""
        request = ResearchRequest("ABC-123", "SSD")
        a1 = _make_accepted_assessment_for_test(Decimal("100"))
        bucket = PriceAggregateBucket(
            currency_code="USD",
            condition=NormalizedCondition.NEW,
            assessments=(a1,),
            count=1,
            low=Decimal("100"),
            median=Decimal("100"),
            high=Decimal("100"),
            market_range_low=None,
            market_range_high=None,
            confidence=ConfidenceLevel.LOW,
        )
        with pytest.raises(ValueError, match="one bucket"):
            PriceAggregationResult(
                request=request,
                assessments=(a1,),
                exclusions=(),
                buckets=(bucket,),
                verification_status=VerificationStatus.AMBIGUOUS,
            )

    # -- Request provenance --

    def test_assessment_belongs_to_different_request_refused(self) -> None:
        """Result request is ABC-123, but a bucket/assessment belongs to
        XYZ-999 -> ValueError. Direct construction must enforce request
        provenance."""
        # Build an assessment for a different request MPN.
        other_request = ResearchRequest("XYZ-999", "Other")
        obs = ListingObservation(
            source_url="https://example.com/test",
            extraction_method=ExtractionMethod.JSON_LD,
            manufacturer_part_number_text="XYZ-999",
            price_text="100",
            currency_text="USD",
            condition_text="new",
        )
        norm = NormalizedListingObservation(
            observation=obs,
            price_amount=Decimal("100"),
            currency_code="USD",
            availability=NormalizedAvailability.UNKNOWN,
            condition=NormalizedCondition.NEW,
            seller_name=None,
            normalization_issues=(),
        )
        other_assessment = ListingIdentityAssessment(
            normalized_listing=norm,
            requested_part_number="XYZ-999",
            candidate_part_number_raw="XYZ-999",
            candidate_part_number_compared="XYZ-999",
            candidate_evidence_source=EvidenceSource.EXPLICIT_MPN_FIELD,
            match_type=IdentityMatchType.EXACT,
            decision=EvidenceDecision.ACCEPTED,
            rejection_reason=None,
        )
        # Now build the result with a different request.
        result_request = ResearchRequest("ABC-123", "SSD")
        bucket = PriceAggregateBucket(
            currency_code="USD",
            condition=NormalizedCondition.NEW,
            assessments=(other_assessment,),
            count=1,
            low=Decimal("100"),
            median=Decimal("100"),
            high=Decimal("100"),
            market_range_low=None,
            market_range_high=None,
            confidence=ConfidenceLevel.LOW,
        )
        with pytest.raises(ValueError, match="same request"):
            PriceAggregationResult(
                request=result_request,
                assessments=(other_assessment,),
                exclusions=(),
                buckets=(bucket,),
                verification_status=VerificationStatus.VERIFIED,
            )

    # -- Unique bucket keys --

    def test_duplicate_bucket_keys_refused(self) -> None:
        """Two buckets with the same (currency_code, condition) -> ValueError.
        At most one bucket per exact currency+condition group."""
        request = ResearchRequest("ABC-123", "SSD")
        a1 = _make_accepted_assessment_for_test(Decimal("100"))
        a2 = _make_accepted_assessment_for_test(Decimal("200"))
        bucket_1 = PriceAggregateBucket(
            currency_code="USD",
            condition=NormalizedCondition.NEW,
            assessments=(a1,),
            count=1,
            low=Decimal("100"),
            median=Decimal("100"),
            high=Decimal("100"),
            market_range_low=None,
            market_range_high=None,
            confidence=ConfidenceLevel.LOW,
        )
        bucket_2 = PriceAggregateBucket(
            currency_code="USD",
            condition=NormalizedCondition.NEW,  # same key as bucket_1
            assessments=(a2,),
            count=1,
            low=Decimal("200"),
            median=Decimal("200"),
            high=Decimal("200"),
            market_range_low=None,
            market_range_high=None,
            confidence=ConfidenceLevel.LOW,
        )
        with pytest.raises(ValueError, match="duplicate bucket"):
            PriceAggregationResult(
                request=request,
                assessments=(a1, a2),
                exclusions=(),
                buckets=(bucket_1, bucket_2),
                verification_status=VerificationStatus.AMBIGUOUS,
            )

    # -- Duplicate input values (value-based, not identity-based) --

    def test_equal_but_distinct_duplicate_assessments_refused(self) -> None:
        """Two separately constructed assessments that compare equal by value
        in result.assessments -> ValueError. PriceAggregationResult itself
        must reject the same duplicate-value invariant the normal builder
        and PriceAggregateBucket already enforce.

        Before the 4A-FU1 fix, the Counter-based output-multiplicity check
        accepted this: Counter([a1, a2]) = {a1: 2} because a1 == a2, and
        the bucket containing (a1, a2) also counted as 2, so input == output.

        This test proves the result-level check independently by passing
        duplicates in result.assessments without constructing any bucket.
        PriceAggregateBucket itself now refuses duplicates too, so the
        old path (fabricating a duplicate bucket to test the result) is
        no longer possible.
        """
        request = ResearchRequest("ABC-123", "SSD")

        a1 = _make_accepted_assessment_for_test(Decimal("100"))
        a2 = _make_accepted_assessment_for_test(Decimal("100"))

        assert a1 is not a2
        assert a1 == a2

        with pytest.raises(ValueError, match="exact duplicate"):
            PriceAggregationResult(
                request=request,
                assessments=(a1, a2),
                exclusions=(),
                buckets=(),
                verification_status=VerificationStatus.UNKNOWN,
            )

    def test_same_object_twice_in_assessments_refused(self) -> None:
        """The same assessment object reference twice in result.assessments
        -> ValueError. Same-object duplicates are also caught by the
        value-based invariant (a == a for any frozen dataclass).

        Tests the result's own check independently, without constructing
        any bucket (PriceAggregateBucket itself now refuses duplicates).
        """
        request = ResearchRequest("ABC-123", "SSD")
        a1 = _make_accepted_assessment_for_test(Decimal("100"))

        with pytest.raises(ValueError, match="exact duplicate"):
            PriceAggregationResult(
                request=request,
                assessments=(a1, a1),
                exclusions=(),
                buckets=(),
                verification_status=VerificationStatus.UNKNOWN,
            )


# ---------------------------------------------------------------------------
# AI_ASSISTED_MATCH is outside 4A aggregation entirely
# ---------------------------------------------------------------------------


def _make_ai_assisted_assessment_for_test(
    price: Decimal = Decimal("100"),
    currency: str = "USD",
    condition: NormalizedCondition = NormalizedCondition.NEW,
) -> ListingIdentityAssessment:
    """Build an AI_ASSISTED_MATCH assessment with a perfectly valid price.

    Everything a bucket needs is present and well-formed: a Decimal price, a
    currency, and a known condition. The ONLY thing that differs from an
    accepted listing is that identity came from a semantic model rather than
    from the deterministic 2A comparator.
    """
    obs = ListingObservation(
        source_url="https://example.com/ai-assisted",
        extraction_method=ExtractionMethod.JSON_LD,
        manufacturer_part_number_text="ABC-123",
        price_text=str(price),
        currency_text=currency,
        condition_text="new",
    )
    norm = NormalizedListingObservation(
        observation=obs,
        price_amount=price,
        currency_code=currency,
        availability=NormalizedAvailability.UNKNOWN,
        condition=condition,
        seller_name=None,
        normalization_issues=(),
    )
    return ListingIdentityAssessment(
        normalized_listing=norm,
        requested_part_number="ABC-123",
        candidate_part_number_raw="ABC-123",
        candidate_part_number_compared="ABC-123",
        candidate_evidence_source=EvidenceSource.EXPLICIT_MPN_FIELD,
        match_type=IdentityMatchType.EXACT,
        decision=EvidenceDecision.AI_ASSISTED_MATCH,
        rejection_reason=None,
    )


class TestAiAssistedMatchIsOutsideAggregation:
    """AI_ASSISTED_MATCH does not enter a bucket at all.

    Frozen 4A invariant: ONLY ``EvidenceDecision.ACCEPTED`` enters aggregation.
    An LLM is never the sole authority for exact product identity, so a
    semantic match must not be able to produce a reported price - not even a
    low-confidence one. The guard is that the listing never becomes an
    observation, not merely that the overall status avoids VERIFIED.
    """

    def test_ai_assisted_match_is_excluded_from_every_bucket(self) -> None:
        """A valid numeric price on an AI_ASSISTED_MATCH creates no bucket."""
        request = ResearchRequest("ABC-123", "SSD")
        assessment = _make_ai_assisted_assessment_for_test(Decimal("100"))

        # The listing really is numerically perfect - the exclusion below is
        # about identity authority, not about a missing price.
        assert assessment.normalized_listing.price_amount == Decimal("100")
        assert assessment.normalized_listing.currency_code == "USD"
        assert assessment.normalized_listing.condition is NormalizedCondition.NEW

        result = aggregate_listing_prices(request, (assessment,))

        assert result.buckets == ()
        assert len(result.exclusions) == 1
        assert result.exclusions[0].reason is (
            PriceAggregationExclusionReason.IDENTITY_NOT_ACCEPTED
        )
        assert result.exclusions[0].assessment is assessment

    def test_ai_assisted_match_cannot_produce_verified_output(self) -> None:
        """Three priced AI_ASSISTED_MATCH listings still report UNKNOWN.

        Three comparable observations in one currency and condition is exactly
        the shape that would otherwise yield a VERIFIED bucket.
        """
        request = ResearchRequest("ABC-123", "SSD")
        assessments = tuple(
            _make_ai_assisted_assessment_for_test(price)
            for price in (Decimal("90"), Decimal("100"), Decimal("110"))
        )

        result = aggregate_listing_prices(request, assessments)

        assert result.verification_status is VerificationStatus.UNKNOWN
        assert result.buckets == ()
        assert len(result.exclusions) == 3

    def test_ai_assisted_match_does_not_join_an_accepted_bucket(self) -> None:
        """It cannot ride along in a bucket built from accepted listings.

        The bucket's statistics must be computed from the ACCEPTED listings
        alone; the semantic one may not widen the range or move the median.
        """
        request = ResearchRequest("ABC-123", "SSD")
        accepted = (
            _make_accepted_assessment_for_test(Decimal("100")),
            _make_accepted_assessment_for_test(Decimal("110")),
            _make_accepted_assessment_for_test(Decimal("120")),
        )
        ai_assisted = _make_ai_assisted_assessment_for_test(Decimal("999"))

        result = aggregate_listing_prices(request, accepted + (ai_assisted,))

        assert len(result.buckets) == 1
        bucket = result.buckets[0]

        assert bucket.count == 3
        assert bucket.high == Decimal("120")
        assert bucket.median == Decimal("110")
        assert ai_assisted not in bucket.assessments

        assert len(result.exclusions) == 1
        assert result.exclusions[0].assessment is ai_assisted

    def test_a_bucket_refuses_an_ai_assisted_member_outright(self) -> None:
        """Hand-constructing a bucket around one is refused at construction.

        The builder excludes it; the contract also refuses to hold it, so no
        caller can fabricate the state the builder will not produce.
        """
        assessment = _make_ai_assisted_assessment_for_test(Decimal("100"))

        with pytest.raises(ValueError, match="only ACCEPTED listings"):
            PriceAggregateBucket(
                currency_code="USD",
                condition=NormalizedCondition.NEW,
                assessments=(assessment,),
                count=1,
                low=Decimal("100"),
                median=Decimal("100"),
                high=Decimal("100"),
                market_range_low=None,
                market_range_high=None,
                confidence=ConfidenceLevel.LOW,
            )

    def test_ai_assisted_match_is_not_accepted(self) -> None:
        """The two decisions are distinct members, not aliases."""
        assert EvidenceDecision.AI_ASSISTED_MATCH is not EvidenceDecision.ACCEPTED
        assert EvidenceDecision.AI_ASSISTED_MATCH != EvidenceDecision.ACCEPTED
