"""Codec round-trip and fail-closed tests (PRODUCT-INTEL.4B).

Tests ``encode_price_aggregation_result`` and ``decode_price_aggregation_result``
for structural correctness, round-trip fidelity, corruption detection, and
architecture compliance.
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
from product_intelligence.research import (
    ListingIdentityAssessment,
    ListingObservation,
    PriceAggregateBucket,
    PriceAggregationExclusion,
    PriceAggregationExclusionReason,
    PriceAggregationResult,
    PriceResultCodecError,
    decode_price_aggregation_result,
    encode_price_aggregation_result,
)
from product_intelligence.research.listings import ExtractionMethod
from product_intelligence.research.matching import (
    EvidenceSource,
    IdentityRejectionReason,
)
from product_intelligence.research.normalization import (
    NormalizedAvailability,
    NormalizedCondition,
    NormalizedListingObservation,
)


# ---------------------------------------------------------------------------
# Fixtures: canonical test data
# ---------------------------------------------------------------------------


@pytest.fixture
def canonical_request() -> ResearchRequest:
    return ResearchRequest(
        manufacturer_part_number="MZ-V8P1T0B/AM",
        description="1TB NVMe M.2 solid state drive",
    )


@pytest.fixture
def single_observation() -> ListingObservation:
    return ListingObservation(
        source_url="https://example.com/ssd-1tb",
        extraction_method=ExtractionMethod.JSON_LD,
        product_title="Samsung 980 PRO 1TB",
        manufacturer_part_number_text="MZ-V8P1T0B/AM",
        sku_text="SSD-980-1T",
        brand_text="Samsung",
        price_text="$109.99",
        currency_text="USD",
        availability_text="In Stock",
        condition_text="New",
        seller_text="Example Store",
        offer_url_text="https://example.com/offer/1",
        raw_reference="https://example.com/ssd-1tb",
    )


@pytest.fixture
def normalized_observation(
    single_observation: ListingObservation,
) -> NormalizedListingObservation:
    return NormalizedListingObservation(
        observation=single_observation,
        price_amount=Decimal("109.99"),
        currency_code="USD",
        availability=NormalizedAvailability.IN_STOCK,
        condition=NormalizedCondition.NEW,
        seller_name="Example Store",
        normalization_issues=(),
    )


@pytest.fixture
def single_assessment(
    normalized_observation: NormalizedListingObservation,
) -> ListingIdentityAssessment:
    return ListingIdentityAssessment(
        normalized_listing=normalized_observation,
        requested_part_number="MZ-V8P1T0B/AM",
        candidate_part_number_raw="MZ-V8P1T0B/AM",
        candidate_part_number_compared="MZ-V8P1T0B/AM",
        candidate_evidence_source=EvidenceSource.EXPLICIT_MPN_FIELD,
        match_type=IdentityMatchType.EXACT,
        decision=EvidenceDecision.ACCEPTED,
        rejection_reason=None,
    )


@pytest.fixture
def multi_assessment(
    canonical_request: ResearchRequest,
) -> list[ListingIdentityAssessment]:
    """Build assessments for a single-bucket result."""
    obs1 = ListingObservation(
        source_url="https://example.com/ssd-1tb-1",
        extraction_method=ExtractionMethod.JSON_LD,
        product_title="Samsung 980 PRO 1TB",
        manufacturer_part_number_text="MZ-V8P1T0B/AM",
        sku_text="SSD-980-1T",
        brand_text="Samsung",
        price_text="$109.99",
        currency_text="USD",
        availability_text="In Stock",
        condition_text="New",
        seller_text="Example Store",
        offer_url_text=None,
        raw_reference="https://example.com/ssd-1tb-1",
    )
    norm1 = NormalizedListingObservation(
        observation=obs1,
        price_amount=Decimal("109.99"),
        currency_code="USD",
        availability=NormalizedAvailability.IN_STOCK,
        condition=NormalizedCondition.NEW,
        seller_name="Example Store",
        normalization_issues=(),
    )
    assess1 = ListingIdentityAssessment(
        normalized_listing=norm1,
        requested_part_number="MZ-V8P1T0B/AM",
        candidate_part_number_raw="MZ-V8P1T0B/AM",
        candidate_part_number_compared="MZ-V8P1T0B/AM",
        candidate_evidence_source=EvidenceSource.EXPLICIT_MPN_FIELD,
        match_type=IdentityMatchType.EXACT,
        decision=EvidenceDecision.ACCEPTED,
        rejection_reason=None,
    )

    obs2 = ListingObservation(
        source_url="https://other.com/ssd-1tb",
        extraction_method=ExtractionMethod.META,
        product_title="Samsung 980 PRO 1TB NVMe",
        manufacturer_part_number_text="MZ-V8P1T0B/AM",
        sku_text=None,
        brand_text="Samsung",
        price_text="$119.99",
        currency_text="USD",
        availability_text="In Stock",
        condition_text="New",
        seller_text="Other Store",
        offer_url_text=None,
        raw_reference="https://other.com/ssd-1tb",
    )
    norm2 = NormalizedListingObservation(
        observation=obs2,
        price_amount=Decimal("119.99"),
        currency_code="USD",
        availability=NormalizedAvailability.IN_STOCK,
        condition=NormalizedCondition.NEW,
        seller_name="Other Store",
        normalization_issues=(),
    )
    assess2 = ListingIdentityAssessment(
        normalized_listing=norm2,
        requested_part_number="MZ-V8P1T0B/AM",
        candidate_part_number_raw="MZ-V8P1T0B/AM",
        candidate_part_number_compared="MZ-V8P1T0B/AM",
        candidate_evidence_source=EvidenceSource.EXPLICIT_MPN_FIELD,
        match_type=IdentityMatchType.EXACT,
        decision=EvidenceDecision.ACCEPTED,
        rejection_reason=None,
    )

    obs3 = ListingObservation(
        source_url="https://cheap.com/ssd-1tb",
        extraction_method=ExtractionMethod.META,
        product_title="Samsung 980 PRO 1TB Open Box",
        manufacturer_part_number_text="MZ-V8P1T0B/AM",
        sku_text=None,
        brand_text="Samsung",
        price_text="$89.99",
        currency_text="USD",
        availability_text="In Stock",
        condition_text="Used",
        seller_text="Cheap Store",
        offer_url_text=None,
        raw_reference="https://cheap.com/ssd-1tb",
    )
    norm3 = NormalizedListingObservation(
        observation=obs3,
        price_amount=Decimal("89.99"),
        currency_code="USD",
        availability=NormalizedAvailability.IN_STOCK,
        condition=NormalizedCondition.USED,
        seller_name="Cheap Store",
        normalization_issues=(),
    )
    assess3 = ListingIdentityAssessment(
        normalized_listing=norm3,
        requested_part_number="MZ-V8P1T0B/AM",
        candidate_part_number_raw="MZ-V8P1T0B/AM",
        candidate_part_number_compared="MZ-V8P1T0B/AM",
        candidate_evidence_source=EvidenceSource.EXPLICIT_MPN_FIELD,
        match_type=IdentityMatchType.EXACT,
        decision=EvidenceDecision.ACCEPTED,
        rejection_reason=None,
    )

    return [assess1, assess2, assess3]


def _build_verifiable_result(
    request: ResearchRequest,
    assessments: list[ListingIdentityAssessment],
) -> PriceAggregationResult:
    """Build a valid result from accepted assessments.

    If no assessments are provided, returns an UNKNOWN result with no buckets.
    """
    if not assessments:
        return PriceAggregationResult(
            request=request,
            assessments=(),
            exclusions=(),
            buckets=(),
            verification_status=VerificationStatus.UNKNOWN,
        )

    sorted_prices = sorted(a.normalized_listing.price_amount for a in assessments)
    n = len(sorted_prices)
    if n % 2 == 1:
        median_price = sorted_prices[n // 2]
    else:
        median_price = (sorted_prices[n // 2 - 1] + sorted_prices[n // 2]) / 2

    return PriceAggregationResult(
        request=request,
        assessments=tuple(assessments),
        exclusions=(),
        buckets=(
            PriceAggregateBucket(
                currency_code="USD",
                condition=NormalizedCondition.NEW,
                assessments=tuple(assessments),
                count=n,
                low=min(sorted_prices),
                median=median_price,
                high=max(sorted_prices),
                market_range_low=min(sorted_prices) if n >= 3 else None,
                market_range_high=max(sorted_prices) if n >= 3 else None,
                confidence=ConfidenceLevel.LOW if n < 3 else ConfidenceLevel.MEDIUM,
            ),
        ),
        verification_status=VerificationStatus.VERIFIED,
    )


# ---------------------------------------------------------------------------
# Round-trip tests
# ---------------------------------------------------------------------------


class TestEncodeProducesCleanJson:
    """The encoded payload contains only JSON-safe types."""

    def test_encode_produces_no_decimal_objects(self) -> None:
        """All Decimal values become strings in the payload."""
        request = ResearchRequest(
            manufacturer_part_number="MZ-V8P1T0B/AM",
            description="1TB NVMe M.2 solid state drive",
        )
        obs = ListingObservation(
            source_url="https://example.com/test",
            extraction_method=ExtractionMethod.JSON_LD,
            product_title="Test Product",
            manufacturer_part_number_text="MZ-V8P1T0B/AM",
            sku_text=None,
            brand_text=None,
            price_text="$50.00",
            currency_text="USD",
            availability_text="In Stock",
            condition_text="New",
            seller_text="Test Seller",
            offer_url_text=None,
            raw_reference=None,
        )
        norm = NormalizedListingObservation(
            observation=obs,
            price_amount=Decimal("50.00"),
            currency_code="USD",
            availability=NormalizedAvailability.IN_STOCK,
            condition=NormalizedCondition.NEW,
            seller_name="Test Seller",
            normalization_issues=(),
        )
        assess = ListingIdentityAssessment(
            normalized_listing=norm,
            requested_part_number="MZ-V8P1T0B/AM",
            candidate_part_number_raw="MZ-V8P1T0B/AM",
            candidate_part_number_compared="MZ-V8P1T0B/AM",
            candidate_evidence_source=EvidenceSource.EXPLICIT_MPN_FIELD,
            match_type=IdentityMatchType.EXACT,
            decision=EvidenceDecision.ACCEPTED,
            rejection_reason=None,
        )
        result = PriceAggregationResult(
            request=request,
            assessments=(assess,),
            exclusions=(),
            buckets=(
                PriceAggregateBucket(
                    currency_code="USD",
                    condition=NormalizedCondition.NEW,
                    assessments=(assess,),
                    count=1,
                    low=Decimal("50.00"),
                    median=Decimal("50.00"),
                    high=Decimal("50.00"),
                    market_range_low=None,
                    market_range_high=None,
                    confidence=ConfidenceLevel.LOW,
                ),
            ),
            verification_status=VerificationStatus.VERIFIED,
        )

        payload = encode_price_aggregation_result(result)

        def _check_types(obj: Any, path: str = "") -> None:
            if isinstance(obj, dict):
                for k, v in obj.items():
                    _check_types(v, f"{path}.{k}")
            elif isinstance(obj, (list, tuple)):
                for i, item in enumerate(obj):
                    _check_types(item, f"{path}[{i}]")
            elif isinstance(obj, Decimal):
                pytest.fail(f"Decimal leaked into payload at {path}")
            elif hasattr(obj, "value") and hasattr(obj, "_name_"):
                pytest.fail(f"Enum leaked into payload at {path}")

        _check_types(payload)

    def test_encode_produces_no_enum_objects(self, canonical_request: ResearchRequest) -> None:
        """All enum values become plain strings."""
        obs = ListingObservation(
            source_url="https://example.com/enum-test",
            extraction_method=ExtractionMethod.JSON_LD,
            product_title="Enum Test",
            manufacturer_part_number_text="MZ-V8P1T0B/AM",
            sku_text=None,
            brand_text=None,
            price_text="$100",
            currency_text="USD",
            availability_text="In Stock",
            condition_text="New",
            seller_text="Enum Seller",
            offer_url_text=None,
            raw_reference=None,
        )
        norm = NormalizedListingObservation(
            observation=obs,
            price_amount=Decimal("100"),
            currency_code="USD",
            availability=NormalizedAvailability.IN_STOCK,
            condition=NormalizedCondition.NEW,
            seller_name="Enum Seller",
            normalization_issues=(),
        )
        assess = ListingIdentityAssessment(
            normalized_listing=norm,
            requested_part_number="MZ-V8P1T0B/AM",
            candidate_part_number_raw="MZ-V8P1T0B/AM",
            candidate_part_number_compared="MZ-V8P1T0B/AM",
            candidate_evidence_source=EvidenceSource.EXPLICIT_MPN_FIELD,
            match_type=IdentityMatchType.EXACT,
            decision=EvidenceDecision.ACCEPTED,
            rejection_reason=None,
        )

        result = _build_verifiable_result(canonical_request, [assess])
        payload = encode_price_aggregation_result(result)

        def _check_enums(obj: Any, path: str = "") -> None:
            if isinstance(obj, dict):
                for k, v in obj.items():
                    _check_enums(v, f"{path}.{k}")
            elif isinstance(obj, (list, tuple)):
                for i, item in enumerate(obj):
                    _check_enums(item, f"{path}[{i}]")
            elif hasattr(obj, "_name_"):
                pytest.fail(f"Enum object leaked into payload at {path}")

        _check_enums(payload)

    def test_encode_returns_flat_dict(self, canonical_request: ResearchRequest) -> None:
        """The encoded payload has exactly the expected top-level keys."""
        # Build a result with an assessment so the result is VERIFIED.
        obs = ListingObservation(
            source_url="https://example.com/test",
            extraction_method=ExtractionMethod.JSON_LD,
            product_title="Test",
            manufacturer_part_number_text="MZ-V8P1T0B/AM",
            sku_text=None,
            brand_text=None,
            price_text="$50",
            currency_text="USD",
            availability_text="In Stock",
            condition_text="New",
            seller_text="Test",
            offer_url_text=None,
            raw_reference=None,
        )
        norm = NormalizedListingObservation(
            observation=obs,
            price_amount=Decimal("50"),
            currency_code="USD",
            availability=NormalizedAvailability.IN_STOCK,
            condition=NormalizedCondition.NEW,
            seller_name="Test",
            normalization_issues=(),
        )
        assess = ListingIdentityAssessment(
            normalized_listing=norm,
            requested_part_number="MZ-V8P1T0B/AM",
            candidate_part_number_raw="MZ-V8P1T0B/AM",
            candidate_part_number_compared="MZ-V8P1T0B/AM",
            candidate_evidence_source=EvidenceSource.EXPLICIT_MPN_FIELD,
            match_type=IdentityMatchType.EXACT,
            decision=EvidenceDecision.ACCEPTED,
            rejection_reason=None,
        )
        result = _build_verifiable_result(canonical_request, [assess])
        payload = encode_price_aggregation_result(result)
        assert isinstance(payload, dict)
        assert set(payload.keys()) == {
            "request", "assessments", "buckets",
            "exclusions", "verification_status",
        }


class TestRoundTripFidelity:
    """Encode then decode must produce an object equal to the original."""

    def test_single_bucket_round_trip(
        self, canonical_request: ResearchRequest, multi_assessment: list
    ) -> None:
        result = _build_verifiable_result(
            canonical_request, multi_assessment[:2]  # Only NEW ones
        )
        payload = encode_price_aggregation_result(result)
        decoded = decode_price_aggregation_result(
            payload, schema_version=1
        )

        assert decoded.request == result.request
        assert len(decoded.assessments) == len(result.assessments)
        assert decoded.verification_status == result.verification_status
        assert len(decoded.buckets) == len(result.buckets)
        assert len(decoded.exclusions) == len(result.exclusions)

        for d_bucket, o_bucket in zip(decoded.buckets, result.buckets):
            assert d_bucket.currency_code == o_bucket.currency_code
            assert d_bucket.condition == o_bucket.condition
            assert d_bucket.count == o_bucket.count
            assert d_bucket.low == o_bucket.low
            assert d_bucket.median == o_bucket.median
            assert d_bucket.high == o_bucket.high
            assert d_bucket.market_range_low == o_bucket.market_range_low
            assert d_bucket.market_range_high == o_bucket.market_range_high
            assert d_bucket.confidence == o_bucket.confidence

    def test_empty_assessments_round_trip(self, canonical_request: ResearchRequest) -> None:
        result = PriceAggregationResult(
            request=canonical_request,
            assessments=(),
            exclusions=(),
            buckets=(),
            verification_status=VerificationStatus.UNKNOWN,
        )
        payload = encode_price_aggregation_result(result)
        decoded = decode_price_aggregation_result(payload, schema_version=1)

        assert decoded.request == result.request
        assert decoded.assessments == ()
        assert decoded.buckets == ()
        assert decoded.exclusions == ()
        assert decoded.verification_status == VerificationStatus.UNKNOWN

    def test_multiple_verification_statuses(
        self, canonical_request: ResearchRequest
    ) -> None:
        """Round-trip with UNKNOWN, VERIFIED, and AMBIGUOUS statuses.

        UNKNOWN is used with zero buckets. VERIFIED and AMBIGUOUS need buckets.
        """
        # UNKNOWN with zero buckets (valid by __post_init__)
        result = PriceAggregationResult(
            request=canonical_request,
            assessments=(),
            exclusions=(),
            buckets=(),
            verification_status=VerificationStatus.UNKNOWN,
        )
        payload = encode_price_aggregation_result(result)
        decoded = decode_price_aggregation_result(payload, schema_version=1)
        assert decoded.verification_status == VerificationStatus.UNKNOWN

        # VERIFIED with a single bucket
        obs = ListingObservation(
            source_url="https://example.com/test",
            extraction_method=ExtractionMethod.JSON_LD,
            product_title="Test",
            manufacturer_part_number_text="MZ-V8P1T0B/AM",
            sku_text=None,
            brand_text=None,
            price_text="$50",
            currency_text="USD",
            availability_text="In Stock",
            condition_text="New",
            seller_text="Test",
            offer_url_text=None,
            raw_reference=None,
        )
        norm = NormalizedListingObservation(
            observation=obs,
            price_amount=Decimal("50"),
            currency_code="USD",
            availability=NormalizedAvailability.IN_STOCK,
            condition=NormalizedCondition.NEW,
            seller_name="Test",
            normalization_issues=(),
        )
        assess = ListingIdentityAssessment(
            normalized_listing=norm,
            requested_part_number="MZ-V8P1T0B/AM",
            candidate_part_number_raw="MZ-V8P1T0B/AM",
            candidate_part_number_compared="MZ-V8P1T0B/AM",
            candidate_evidence_source=EvidenceSource.EXPLICIT_MPN_FIELD,
            match_type=IdentityMatchType.EXACT,
            decision=EvidenceDecision.ACCEPTED,
            rejection_reason=None,
        )
        result = PriceAggregationResult(
            request=canonical_request,
            assessments=(assess,),
            exclusions=(),
            buckets=(
                PriceAggregateBucket(
                    currency_code="USD",
                    condition=NormalizedCondition.NEW,
                    assessments=(assess,),
                    count=1,
                    low=Decimal("50"),
                    median=Decimal("50"),
                    high=Decimal("50"),
                    market_range_low=None,
                    market_range_high=None,
                    confidence=ConfidenceLevel.LOW,
                ),
            ),
            verification_status=VerificationStatus.VERIFIED,
        )
        payload = encode_price_aggregation_result(result)
        decoded = decode_price_aggregation_result(payload, schema_version=1)
        assert decoded.verification_status == VerificationStatus.VERIFIED

    def test_assessment_with_rejection_round_trip(self) -> None:
        obs = ListingObservation(
            source_url="https://example.com/diff",
            extraction_method=ExtractionMethod.JSON_LD,
            product_title="Diff",
            manufacturer_part_number_text="DIFF-MPN",
            sku_text=None,
            brand_text=None,
            price_text="$50",
            currency_text="USD",
            availability_text="In Stock",
            condition_text="New",
            seller_text="Diff",
            offer_url_text=None,
            raw_reference=None,
        )
        norm = NormalizedListingObservation(
            observation=obs,
            price_amount=Decimal("50"),
            currency_code="USD",
            availability=NormalizedAvailability.IN_STOCK,
            condition=NormalizedCondition.NEW,
            seller_name="Diff",
            normalization_issues=(),
        )
        assess = ListingIdentityAssessment(
            normalized_listing=norm,
            requested_part_number="REQ-MPN",
            candidate_part_number_raw="DIFF-MPN",
            candidate_part_number_compared="DIFF-MPN",
            candidate_evidence_source=EvidenceSource.EXPLICIT_MPN_FIELD,
            match_type=IdentityMatchType.UNKNOWN,
            decision=EvidenceDecision.REJECTED,
            rejection_reason=IdentityRejectionReason.MPN_MISMATCH,
        )
        result = PriceAggregationResult(
            request=ResearchRequest(manufacturer_part_number="REQ-MPN", description="Test"),
            assessments=(assess,),
            exclusions=(
                PriceAggregationExclusion(
                    assessment=assess,
                    reason=PriceAggregationExclusionReason.IDENTITY_NOT_ACCEPTED,
                ),
            ),
            buckets=(),
            verification_status=VerificationStatus.UNKNOWN,
        )
        payload = encode_price_aggregation_result(result)
        decoded = decode_price_aggregation_result(payload, schema_version=1)

        assert len(decoded.assessments) == 1
        assert decoded.assessments[0].rejection_reason == IdentityRejectionReason.MPN_MISMATCH
        assert decoded.assessments[0].decision == EvidenceDecision.REJECTED
        assert len(decoded.exclusions) == 1
        assert decoded.exclusions[0].reason == PriceAggregationExclusionReason.IDENTITY_NOT_ACCEPTED


# ---------------------------------------------------------------------------
# Fail-closed tests
# ---------------------------------------------------------------------------


class TestDecodeRejectsCorruption:
    """The decoder must refuse every form of corrupt payload."""

    def test_unsupported_schema_version(self) -> None:
        with pytest.raises(PriceResultCodecError, match="unsupported schema_version"):
            decode_price_aggregation_result({}, schema_version=0)

    def test_schema_version_99_rejected(self) -> None:
        with pytest.raises(PriceResultCodecError, match="unsupported schema_version"):
            decode_price_aggregation_result({}, schema_version=99)

    def test_schema_version_bool_rejected(self) -> None:
        with pytest.raises(PriceResultCodecError, match="schema_version must be int"):
            decode_price_aggregation_result({}, schema_version=True)

    def test_schema_version_float_rejected(self) -> None:
        with pytest.raises(PriceResultCodecError, match="schema_version must be int"):
            decode_price_aggregation_result({}, schema_version=1.0)

    def test_payload_not_dict(self) -> None:
        with pytest.raises(PriceResultCodecError):
            decode_price_aggregation_result("not a dict", schema_version=1)

    def test_payload_is_list(self) -> None:
        with pytest.raises(PriceResultCodecError):
            decode_price_aggregation_result([1, 2, 3], schema_version=1)

    def test_missing_request_key(self) -> None:
        with pytest.raises(PriceResultCodecError, match="missing required key"):
            decode_price_aggregation_result(
                {"assessments": [], "buckets": [], "exclusions": [], "verification_status": "UNKNOWN"},
                schema_version=1,
            )

    def test_missing_assessments_key(self) -> None:
        with pytest.raises(PriceResultCodecError, match="missing required key"):
            decode_price_aggregation_result(
                {
                    "request": {
                        "manufacturer_part_number": "X",
                        "description": "",
                    },
                    "buckets": [],
                    "exclusions": [],
                    "verification_status": "UNKNOWN",
                },
                schema_version=1,
            )

    def test_extra_top_level_keys(self) -> None:
        payload = {
            "request": {
                "manufacturer_part_number": "X",
                "description": "",
            },
            "assessments": [],
            "buckets": [],
            "exclusions": [],
            "verification_status": "UNKNOWN",
            "extra_key": "should not be here",
        }
        with pytest.raises(PriceResultCodecError, match="unexpected keys"):
            decode_price_aggregation_result(payload, schema_version=1)

    def test_unknown_verification_status(self) -> None:
        payload = {
            "request": {
                "manufacturer_part_number": "X",
                "description": "",
            },
            "assessments": [],
            "buckets": [],
            "exclusions": [],
            "verification_status": "INVALID_STATUS",
        }
        with pytest.raises(PriceResultCodecError, match="unknown.*VerificationStatus"):
            decode_price_aggregation_result(payload, schema_version=1)

    def test_assessment_index_out_of_range(self) -> None:
        """A bucket references a non-existent assessment index."""
        payload = {
            "request": {
                "manufacturer_part_number": "X",
                "description": "",
            },
            "assessments": [],
            "buckets": [
                {
                    "currency_code": "USD",
                    "condition": "NEW",
                    "assessment_indexes": [99],
                    "count": 1,
                    "low": "100",
                    "median": "100",
                    "high": "100",
                    "market_range_low": None,
                    "market_range_high": None,
                    "confidence": "LOW",
                },
            ],
            "exclusions": [],
            "verification_status": "VERIFIED",
        }
        with pytest.raises(PriceResultCodecError, match="out of range"):
            decode_price_aggregation_result(payload, schema_version=1)

    def test_negative_assessment_index(self) -> None:
        payload = {
            "request": {
                "manufacturer_part_number": "X",
                "description": "",
            },
            "assessments": [],
            "buckets": [],
            "exclusions": [
                {
                    "assessment_index": -1,
                    "reason": "IDENTITY_NOT_ACCEPTED",
                },
            ],
            "verification_status": "UNKNOWN",
        }
        with pytest.raises(PriceResultCodecError, match="out of range"):
            decode_price_aggregation_result(payload, schema_version=1)

    def test_float_decimal_in_bucket_low(self) -> None:
        """A float in a Decimal field is rejected — it loses precision."""
        payload = {
            "request": {
                "manufacturer_part_number": "X",
                "description": "",
            },
            "assessments": [],
            "buckets": [
                {
                    "currency_code": "USD",
                    "condition": "NEW",
                    "assessment_indexes": [],
                    "count": 0,
                    "low": 100.5,  # float, not string
                    "median": "100",
                    "high": "100",
                    "market_range_low": None,
                    "market_range_high": None,
                    "confidence": "LOW",
                },
            ],
            "exclusions": [],
            "verification_status": "VERIFIED",
        }
        with pytest.raises(PriceResultCodecError, match="Decimal must be stored as a string"):
            decode_price_aggregation_result(payload, schema_version=1)

    def test_int_decimal_in_bucket_low(self) -> None:
        """An int in a Decimal field is rejected — it loses precision context."""
        payload = {
            "request": {
                "manufacturer_part_number": "X",
                "description": "",
            },
            "assessments": [],
            "buckets": [
                {
                    "currency_code": "USD",
                    "condition": "NEW",
                    "assessment_indexes": [],
                    "count": 0,
                    "low": 100,  # int, not string
                    "median": "100",
                    "high": "100",
                    "market_range_low": None,
                    "market_range_high": None,
                    "confidence": "LOW",
                },
            ],
            "exclusions": [],
            "verification_status": "VERIFIED",
        }
        with pytest.raises(PriceResultCodecError, match="Decimal must be stored as a string"):
            decode_price_aggregation_result(payload, schema_version=1)

    def test_nan_decimal_rejected(self) -> None:
        payload = {
            "request": {
                "manufacturer_part_number": "X",
                "description": "",
            },
            "assessments": [],
            "buckets": [
                {
                    "currency_code": "USD",
                    "condition": "NEW",
                    "assessment_indexes": [],
                    "count": 0,
                    "low": "NaN",
                    "median": "100",
                    "high": "100",
                    "market_range_low": None,
                    "market_range_high": None,
                    "confidence": "LOW",
                },
            ],
            "exclusions": [],
            "verification_status": "VERIFIED",
        }
        with pytest.raises(PriceResultCodecError, match="must be finite"):
            decode_price_aggregation_result(payload, schema_version=1)

    def test_infinity_decimal_rejected(self) -> None:
        payload = {
            "request": {
                "manufacturer_part_number": "X",
                "description": "",
            },
            "assessments": [],
            "buckets": [
                {
                    "currency_code": "USD",
                    "condition": "NEW",
                    "assessment_indexes": [],
                    "count": 0,
                    "low": "Infinity",
                    "median": "100",
                    "high": "100",
                    "market_range_low": None,
                    "market_range_high": None,
                    "confidence": "LOW",
                },
            ],
            "exclusions": [],
            "verification_status": "VERIFIED",
        }
        with pytest.raises(PriceResultCodecError, match="must be finite"):
            decode_price_aggregation_result(payload, schema_version=1)

    def test_bool_as_int_for_count(self) -> None:
        """A bool in an int field is rejected — bool is subclass of int."""
        payload = {
            "request": {
                "manufacturer_part_number": "X",
                "description": "",
            },
            "assessments": [],
            "buckets": [
                {
                    "currency_code": "USD",
                    "condition": "NEW",
                    "assessment_indexes": [],
                    "count": True,  # bool, not int
                    "low": "100",
                    "median": "100",
                    "high": "100",
                    "market_range_low": None,
                    "market_range_high": None,
                    "confidence": "LOW",
                },
            ],
            "exclusions": [],
            "verification_status": "VERIFIED",
        }
        with pytest.raises(PriceResultCodecError, match="expected int, got bool"):
            decode_price_aggregation_result(payload, schema_version=1)

    def test_extra_keys_in_assessment(self) -> None:
        """Extra keys in an assessment object are rejected."""
        # First build a valid minimal assessment, then add an extra key.
        obs_payload = {
            "source_url": "https://example.com/test",
            "extraction_method": "JSON_LD",
            "product_title": "Test",
            "manufacturer_part_number_text": "X",
            "sku_text": None,
            "brand_text": None,
            "price_text": "$100",
            "currency_text": "USD",
            "availability_text": "In Stock",
            "condition_text": "New",
            "seller_text": "Test Seller",
            "offer_url_text": None,
            "raw_reference": None,
        }
        assess_payload = {
            "normalized_listing": {
                "observation": obs_payload,
                "price_amount": "100",
                "currency_code": "USD",
                "availability": "IN_STOCK",
                "condition": "NEW",
                "seller_name": "Test Seller",
                "normalization_issues": [],
            },
            "requested_part_number": "X",
            "candidate_part_number_raw": "X",
            "candidate_part_number_compared": "X",
            "candidate_evidence_source": "EXPLICIT_MPN_FIELD",
            "match_type": "EXACT",
            "decision": "ACCEPTED",
            "rejection_reason": None,
            "extra_field": "should not be here",
        }
        payload = {
            "request": {
                "manufacturer_part_number": "X",
                "description": "",
            },
            "assessments": [assess_payload],
            "buckets": [],
            "exclusions": [],
            "verification_status": "UNKNOWN",
        }
        with pytest.raises(PriceResultCodecError, match="unexpected keys"):
            decode_price_aggregation_result(payload, schema_version=1)

    def test_unknown_enum_in_bucket_condition(self) -> None:
        payload = {
            "request": {
                "manufacturer_part_number": "X",
                "description": "",
            },
            "assessments": [],
            "buckets": [
                {
                    "currency_code": "USD",
                    "condition": "INVALID_CONDITION",
                    "assessment_indexes": [],
                    "count": 0,
                    "low": "100",
                    "median": "100",
                    "high": "100",
                    "market_range_low": None,
                    "market_range_high": None,
                    "confidence": "LOW",
                },
            ],
            "exclusions": [],
            "verification_status": "VERIFIED",
        }
        with pytest.raises(PriceResultCodecError, match="unknown.*NormalizedCondition"):
            decode_price_aggregation_result(payload, schema_version=1)


class TestDecodeRebuildsValidContract:
    """A decoded result passes all 4A __post_init__ invariants."""

    def test_decoded_result_is_valid_aggregation(
        self, canonical_request: ResearchRequest, multi_assessment: list
    ) -> None:
        """The decoder uses __post_init__ validation."""
        result = _build_verifiable_result(
            canonical_request, multi_assessment[:2]  # Only NEW ones
        )
        payload = encode_price_aggregation_result(result)
        decoded = decode_price_aggregation_result(payload, schema_version=1)

        # These are all checked by __post_init__:
        # - unique assessments
        # - bucket statistics match
        # - bucket membership
        # - exclusions reference existing assessments
        # - no assessment in both buckets and exclusions
        # - request provenance
        # - unique bucket keys
        # - verification status validity

        assert decoded is not None  # if __post_init__ failed, we'd already be here
        assert decoded.request == result.request
        assert decoded.verification_status == result.verification_status


# ---------------------------------------------------------------------------
# Architecture tests
# ---------------------------------------------------------------------------


class TestCodecArchitecture:
    """The codec obeys research-layer boundaries."""

    def test_codec_imports_no_django(self) -> None:
        import product_intelligence.research.price_result_codec as codec

        import sys
        module = sys.modules[codec.__name__]
        import inspect
        source = inspect.getsource(module)
        assert "import django" not in source

    def test_codec_error_is_valueerror_subclass(self) -> None:
        assert issubclass(PriceResultCodecError, ValueError)

    def test_codec_version_constant(self) -> None:
        from product_intelligence.research.price_result_codec import (
            PRICE_RESULT_SCHEMA_VERSION,
        )
        assert PRICE_RESULT_SCHEMA_VERSION == 1
        assert isinstance(PRICE_RESULT_SCHEMA_VERSION, int)

    def test_encode_wrong_type_raises(self) -> None:
        with pytest.raises(TypeError, match="expected PriceAggregationResult"):
            encode_price_aggregation_result("not a result")

    def test_encode_wrong_type_for_list(self) -> None:
        with pytest.raises(TypeError, match="expected PriceAggregationResult"):
            encode_price_aggregation_result([])


# ---------------------------------------------------------------------------
# Issue 1 — Value-key mapping (never hash(value) as identity)
# ---------------------------------------------------------------------------


class TestEqualByValueAssessmentReference:
    """A. a1 is not a2 but a1 == a2: top-level uses a1, bucket/exclusion uses
    a2. encode + decode must succeed by value equality."""

    def test_bucket_refs_assessment_by_value_equality(self) -> None:
        """Top-level tuple holds a1, bucket holds a2 (a1 == a2, a1 is not a2).
        The encoder must map a2 to the same canonical index as a1.
        """
        obs = ListingObservation(
            source_url="https://example.com/test",
            extraction_method=ExtractionMethod.JSON_LD,
            product_title="Test",
            manufacturer_part_number_text="TEST-1",
            sku_text=None,
            brand_text=None,
            price_text="$100",
            currency_text="USD",
            availability_text="In Stock",
            condition_text="New",
            seller_text="Test",
            offer_url_text=None,
            raw_reference=None,
        )
        norm = NormalizedListingObservation(
            observation=obs,
            price_amount=Decimal("100"),
            currency_code="USD",
            availability=NormalizedAvailability.IN_STOCK,
            condition=NormalizedCondition.NEW,
            seller_name="Test",
            normalization_issues=(),
        )

        a1 = ListingIdentityAssessment(
            normalized_listing=norm,
            requested_part_number="TEST-1",
            candidate_part_number_raw="TEST-1",
            candidate_part_number_compared="TEST-1",
            candidate_evidence_source=EvidenceSource.EXPLICIT_MPN_FIELD,
            match_type=IdentityMatchType.EXACT,
            decision=EvidenceDecision.ACCEPTED,
            rejection_reason=None,
        )
        # a2 is equal by value but distinct by identity
        a2 = ListingIdentityAssessment(
            normalized_listing=norm,
            requested_part_number="TEST-1",
            candidate_part_number_raw="TEST-1",
            candidate_part_number_compared="TEST-1",
            candidate_evidence_source=EvidenceSource.EXPLICIT_MPN_FIELD,
            match_type=IdentityMatchType.EXACT,
            decision=EvidenceDecision.ACCEPTED,
            rejection_reason=None,
        )

        assert a1 is not a2
        assert a1 == a2

        result = PriceAggregationResult(
            request=ResearchRequest(
                manufacturer_part_number="TEST-1",
                description="Test product",
            ),
            assessments=(a1,),
            exclusions=(),
            buckets=(
                PriceAggregateBucket(
                    currency_code="USD",
                    condition=NormalizedCondition.NEW,
                    assessments=(a2,),  # a2, not a1
                    count=1,
                    low=Decimal("100"),
                    median=Decimal("100"),
                    high=Decimal("100"),
                    market_range_low=None,
                    market_range_high=None,
                    confidence=ConfidenceLevel.LOW,
                ),
            ),
            verification_status=VerificationStatus.VERIFIED,
        )

        # Encode must not raise; a2 must map to index 0
        payload = encode_price_aggregation_result(result)
        assert payload["buckets"][0]["assessment_indexes"] == [0]

        # Decode round-trip preserves the correct assessment
        decoded = decode_price_aggregation_result(payload, schema_version=1)
        assert len(decoded.assessments) == 1
        assert len(decoded.buckets) == 1
        assert decoded.buckets[0].assessments[0] == a1

    def test_exclusion_refs_assessment_by_value_equality(self) -> None:
        """Top-level holds a1, exclusion holds a2 (a1 == a2, a1 is not a2).
        Encode must map a2 to the same canonical index as a1.
        """
        obs = ListingObservation(
            source_url="https://example.com/diff",
            extraction_method=ExtractionMethod.JSON_LD,
            product_title="Diff",
            manufacturer_part_number_text="DIFF-MPN",
            sku_text=None,
            brand_text=None,
            price_text="$50",
            currency_text="USD",
            availability_text="In Stock",
            condition_text="New",
            seller_text="Diff",
            offer_url_text=None,
            raw_reference=None,
        )
        norm = NormalizedListingObservation(
            observation=obs,
            price_amount=Decimal("50"),
            currency_code="USD",
            availability=NormalizedAvailability.IN_STOCK,
            condition=NormalizedCondition.NEW,
            seller_name="Diff",
            normalization_issues=(),
        )

        a1 = ListingIdentityAssessment(
            normalized_listing=norm,
            requested_part_number="REQ-MPN",
            candidate_part_number_raw="DIFF-MPN",
            candidate_part_number_compared="DIFF-MPN",
            candidate_evidence_source=EvidenceSource.EXPLICIT_MPN_FIELD,
            match_type=IdentityMatchType.UNKNOWN,
            decision=EvidenceDecision.REJECTED,
            rejection_reason=IdentityRejectionReason.MPN_MISMATCH,
        )
        a2 = ListingIdentityAssessment(
            normalized_listing=norm,
            requested_part_number="REQ-MPN",
            candidate_part_number_raw="DIFF-MPN",
            candidate_part_number_compared="DIFF-MPN",
            candidate_evidence_source=EvidenceSource.EXPLICIT_MPN_FIELD,
            match_type=IdentityMatchType.UNKNOWN,
            decision=EvidenceDecision.REJECTED,
            rejection_reason=IdentityRejectionReason.MPN_MISMATCH,
        )

        assert a1 is not a2
        assert a1 == a2

        result = PriceAggregationResult(
            request=ResearchRequest(
                manufacturer_part_number="REQ-MPN",
                description="Test",
            ),
            assessments=(a1,),
            exclusions=(
                PriceAggregationExclusion(
                    assessment=a2,  # a2, not a1
                    reason=PriceAggregationExclusionReason.IDENTITY_NOT_ACCEPTED,
                ),
            ),
            buckets=(),
            verification_status=VerificationStatus.UNKNOWN,
        )

        payload = encode_price_aggregation_result(result)
        assert payload["exclusions"][0]["assessment_index"] == 0

        decoded = decode_price_aggregation_result(payload, schema_version=1)
        assert len(decoded.assessments) == 1
        assert len(decoded.exclusions) == 1
        assert decoded.exclusions[0].assessment == a1


class TestForcedHashCollision:
    """B. Force a hash collision between two genuinely different
    ListingIdentityAssessment values. Prove both get distinct canonical
    indexes and round-trip preserves correct provenance."""

    def test_hash_collision_between_unequal_assessments(self) -> None:
        """Temporarily monkeypatch __hash__ to a constant, putting two
        different assessments in one result. Both must receive distinct
        canonical indexes and round-trip must preserve provenance.

        This test MUST fail against a hash(assessment)->int implementation.
        """
        import product_intelligence.research.price_result_codec as codec_mod

        original_hash = ListingIdentityAssessment.__hash__

        def _constant_hash(self: object) -> int:  # noqa: ANN001
            return 42

        try:
            # Monkeypatch __hash__ to a constant value
            ListingIdentityAssessment.__hash__ = _constant_hash  # type: ignore[assignment]

            obs1 = ListingObservation(
                source_url="https://example.com/product-1",
                extraction_method=ExtractionMethod.JSON_LD,
                product_title="Product 1",
                manufacturer_part_number_text="TEST-MPN",
                sku_text=None,
                brand_text=None,
                price_text="$100",
                currency_text="USD",
                availability_text="In Stock",
                condition_text="New",
                seller_text="Seller 1",
                offer_url_text=None,
                raw_reference=None,
            )
            norm1 = NormalizedListingObservation(
                observation=obs1,
                price_amount=Decimal("100"),
                currency_code="USD",
                availability=NormalizedAvailability.IN_STOCK,
                condition=NormalizedCondition.NEW,
                seller_name="Seller 1",
                normalization_issues=(),
            )
            assess1 = ListingIdentityAssessment(
                normalized_listing=norm1,
                requested_part_number="TEST-MPN",
                candidate_part_number_raw="TEST-MPN",
                candidate_part_number_compared="TEST-MPN",
                candidate_evidence_source=EvidenceSource.EXPLICIT_MPN_FIELD,
                match_type=IdentityMatchType.EXACT,
                decision=EvidenceDecision.ACCEPTED,
                rejection_reason=None,
            )

            obs2 = ListingObservation(
                source_url="https://example.com/product-2",
                extraction_method=ExtractionMethod.META,
                product_title="Product 2",
                manufacturer_part_number_text="TEST-MPN",
                sku_text=None,
                brand_text=None,
                price_text="$200",
                currency_text="USD",
                availability_text="In Stock",
                condition_text="New",
                seller_text="Seller 2",
                offer_url_text=None,
                raw_reference=None,
            )
            norm2 = NormalizedListingObservation(
                observation=obs2,
                price_amount=Decimal("200"),
                currency_code="USD",
                availability=NormalizedAvailability.IN_STOCK,
                condition=NormalizedCondition.NEW,
                seller_name="Seller 2",
                normalization_issues=(),
            )
            assess2 = ListingIdentityAssessment(
                normalized_listing=norm2,
                requested_part_number="TEST-MPN",
                candidate_part_number_raw="TEST-MPN",
                candidate_part_number_compared="TEST-MPN",
                candidate_evidence_source=EvidenceSource.EXPLICIT_MPN_FIELD,
                match_type=IdentityMatchType.EXACT,
                decision=EvidenceDecision.ACCEPTED,
                rejection_reason=None,
            )

            # Both have the same hash but are genuinely different
            assert hash(assess1) == hash(assess2) == 42
            assert assess1 != assess2

            result = PriceAggregationResult(
                request=ResearchRequest(
                    manufacturer_part_number="TEST-MPN",
                    description="Test",
                ),
                assessments=(assess1, assess2),
                exclusions=(),
                buckets=(
                    PriceAggregateBucket(
                        currency_code="USD",
                        condition=NormalizedCondition.NEW,
                        assessments=(assess1, assess2),
                        count=2,
                        low=Decimal("100"),
                        median=Decimal("150"),
                        high=Decimal("200"),
                        market_range_low=None,
                        market_range_high=None,
                        confidence=ConfidenceLevel.LOW,
                    ),
                ),
                verification_status=VerificationStatus.VERIFIED,
            )

            # Encode must produce two distinct indexes
            payload = encode_price_aggregation_result(result)
            indexes = payload["buckets"][0]["assessment_indexes"]
            assert len(indexes) == 2
            assert indexes[0] == 0
            assert indexes[1] == 1
            # The indexes are distinct (not aliased by hash collision)
            assert indexes[0] != indexes[1]

            # Decode round-trip preserves correct provenance
            decoded = decode_price_aggregation_result(payload, schema_version=1)
            assert len(decoded.assessments) == 2
            assert decoded.assessments[0] == assess1
            assert decoded.assessments[1] == assess2
            assert decoded.buckets[0].assessments[0] == assess1
            assert decoded.buckets[0].assessments[1] == assess2

        finally:
            ListingIdentityAssessment.__hash__ = original_hash  # type: ignore[assignment]


class TestDecoderWrapping:
    """Issue 2: All nested constructor failures emerge as PriceResultCodecError."""

    def test_invalid_research_request_contract(self) -> None:
        """A V1 payload whose request has both fields empty triggers
        ResearchRequest constructor validation.
        """
        payload = {
            "request": {
                "manufacturer_part_number": "",
                "description": "",
            },
            "assessments": [],
            "buckets": [],
            "exclusions": [],
            "verification_status": "UNKNOWN",
        }
        with pytest.raises(PriceResultCodecError):
            decode_price_aggregation_result(payload, schema_version=1)

    def test_invalid_normalized_listing_contract(self) -> None:
        """A V1 payload whose normalized listing has price_amount as int
        violates the codec contract. Must emerge as PriceResultCodecError.
        """
        obs_payload = {
            "source_url": "https://example.com/test",
            "extraction_method": "JSON_LD",
            "product_title": "Test",
            "manufacturer_part_number_text": "X",
            "sku_text": None,
            "brand_text": None,
            "price_text": "$100",
            "currency_text": "USD",
            "availability_text": "In Stock",
            "condition_text": "New",
            "seller_text": "Test Seller",
            "offer_url_text": None,
            "raw_reference": None,
        }
        payload = {
            "request": {
                "manufacturer_part_number": "X",
                "description": "",
            },
            "assessments": [
                {
                    "normalized_listing": {
                        "observation": obs_payload,
                        "price_amount": 100,  # int, not string
                        "currency_code": "USD",
                        "availability": "IN_STOCK",
                        "condition": "NEW",
                        "seller_name": "Test Seller",
                        "normalization_issues": [],
                    },
                    "requested_part_number": "X",
                    "candidate_part_number_raw": "X",
                    "candidate_part_number_compared": "X",
                    "candidate_evidence_source": "EXPLICIT_MPN_FIELD",
                    "match_type": "EXACT",
                    "decision": "ACCEPTED",
                    "rejection_reason": None,
                }
            ],
            "buckets": [],
            "exclusions": [],
            "verification_status": "UNKNOWN",
        }
        # The codec catches this as a PriceResultCodecError
        # (the Decimal type check fires before the constructor).
        with pytest.raises(PriceResultCodecError):
            decode_price_aggregation_result(payload, schema_version=1)

    def test_impossible_assessment_contract(self) -> None:
        """A V1 payload with a structurally impossible assessment —
        e.g. EXACT match but decision REJECTED — which violates the
        ListingIdentityAssessment post-init invariant.
        """
        obs_payload = {
            "source_url": "https://example.com/test",
            "extraction_method": "JSON_LD",
            "product_title": "Test",
            "manufacturer_part_number_text": "X",
            "sku_text": None,
            "brand_text": None,
            "price_text": "$100",
            "currency_text": "USD",
            "availability_text": "In Stock",
            "condition_text": "New",
            "seller_text": "Test Seller",
            "offer_url_text": None,
            "raw_reference": None,
        }
        payload = {
            "request": {
                "manufacturer_part_number": "X",
                "description": "",
            },
            "assessments": [
                {
                    "normalized_listing": {
                        "observation": obs_payload,
                        "price_amount": "100",
                        "currency_code": "USD",
                        "availability": "IN_STOCK",
                        "condition": "NEW",
                        "seller_name": "Test Seller",
                        "normalization_issues": [],
                    },
                    "requested_part_number": "X",
                    "candidate_part_number_raw": "X",
                    "candidate_part_number_compared": "X",
                    "candidate_evidence_source": "EXPLICIT_MPN_FIELD",
                    "match_type": "EXACT",
                    "decision": "REJECTED",  # EXACT match with REJECTED — impossible
                    "rejection_reason": "MPN_MISMATCH",
                }
            ],
            "buckets": [],
            "exclusions": [],
            "verification_status": "UNKNOWN",
        }
        with pytest.raises(PriceResultCodecError, match="violates the V1 contract"):
            decode_price_aggregation_result(payload, schema_version=1)

    def test_wrong_bucket_median(self) -> None:
        """A V1 payload with a bucket median that doesn't match the
        assessment prices — PriceAggregateBucket __post_init__ rejects it.
        """
        obs_payload = {
            "source_url": "https://example.com/test",
            "extraction_method": "JSON_LD",
            "product_title": "Test",
            "manufacturer_part_number_text": "X",
            "sku_text": None,
            "brand_text": None,
            "price_text": "$100",
            "currency_text": "USD",
            "availability_text": "In Stock",
            "condition_text": "New",
            "seller_text": "Test Seller",
            "offer_url_text": None,
            "raw_reference": None,
        }
        payload = {
            "request": {
                "manufacturer_part_number": "X",
                "description": "",
            },
            "assessments": [
                {
                    "normalized_listing": {
                        "observation": obs_payload,
                        "price_amount": "100",
                        "currency_code": "USD",
                        "availability": "IN_STOCK",
                        "condition": "NEW",
                        "seller_name": "Test Seller",
                        "normalization_issues": [],
                    },
                    "requested_part_number": "X",
                    "candidate_part_number_raw": "X",
                    "candidate_part_number_compared": "X",
                    "candidate_evidence_source": "EXPLICIT_MPN_FIELD",
                    "match_type": "EXACT",
                    "decision": "ACCEPTED",
                    "rejection_reason": None,
                }
            ],
            "buckets": [
                {
                    "currency_code": "USD",
                    "condition": "NEW",
                    "assessment_indexes": [0],
                    "count": 1,
                    "low": "100",
                    "median": "999",  # wrong median — should be 100
                    "high": "100",
                    "market_range_low": None,
                    "market_range_high": None,
                    "confidence": "LOW",
                }
            ],
            "exclusions": [],
            "verification_status": "VERIFIED",
        }
        with pytest.raises(PriceResultCodecError, match="violates the V1 contract"):
            decode_price_aggregation_result(payload, schema_version=1)

    def test_inconsistent_exclusion_contract(self) -> None:
        """A V1 payload where an exclusion references an assessment index
        that exists but the reason field is wrong type.
        """
        payload = {
            "request": {
                "manufacturer_part_number": "X",
                "description": "",
            },
            "assessments": [
                {
                    "normalized_listing": {
                        "observation": {
                            "source_url": "https://example.com/test",
                            "extraction_method": "JSON_LD",
                            "product_title": "Test",
                            "manufacturer_part_number_text": "X",
                            "sku_text": None,
                            "brand_text": None,
                            "price_text": "$100",
                            "currency_text": "USD",
                            "availability_text": "In Stock",
                            "condition_text": "New",
                            "seller_text": "Test",
                            "offer_url_text": None,
                            "raw_reference": None,
                        },
                        "price_amount": "100",
                        "currency_code": "USD",
                        "availability": "IN_STOCK",
                        "condition": "NEW",
                        "seller_name": "Test",
                        "normalization_issues": [],
                    },
                    "requested_part_number": "X",
                    "candidate_part_number_raw": "X",
                    "candidate_part_number_compared": "X",
                    "candidate_evidence_source": "EXPLICIT_MPN_FIELD",
                    "match_type": "EXACT",
                    "decision": "ACCEPTED",
                    "rejection_reason": None,
                }
            ],
            "buckets": [],
            "exclusions": [
                {
                    "assessment_index": 0,
                    "reason": "INVALID_REASON",  # unknown enum value
                }
            ],
            "verification_status": "UNKNOWN",
        }
        with pytest.raises(PriceResultCodecError):
            decode_price_aggregation_result(payload, schema_version=1)
