"""Persistence tests for PriceIntelligenceSnapshot (PRODUCT-INTEL.4B).

Tests that the snapshot model stores and retrieves the codec-encoded
payload correctly, and that the model's constraints hold.

Uses Django TestCase for proper transaction isolation.
"""

from __future__ import annotations

from decimal import Decimal

import pytest
from django.db import IntegrityError
from django.test import TestCase

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
    PriceAggregationResult,
    decode_price_aggregation_result,
    encode_price_aggregation_result,
)
from product_intelligence.research.listings import ExtractionMethod
from product_intelligence.research.matching import EvidenceSource
from product_intelligence.research.normalization import (
    NormalizedAvailability,
    NormalizedCondition,
    NormalizedListingObservation,
)
from product_intelligence.runs.models import PriceIntelligenceSnapshot, ResearchRun


def _make_research_run() -> ResearchRun:
    return ResearchRun.objects.create_from_request(
        ResearchRequest(
            manufacturer_part_number="MZ-V8P1T0B/AM",
            description="1TB NVMe M.2 solid state drive",
        ),
    )


def _make_minimal_result(run: ResearchRun) -> PriceAggregationResult:
    return PriceAggregationResult(
        request=run.to_research_request(),
        assessments=(),
        exclusions=(),
        buckets=(),
        verification_status=VerificationStatus.UNKNOWN,
    )


def _make_result_with_data(run: ResearchRun) -> PriceAggregationResult:
    obs = ListingObservation(
        source_url="https://example.com/ssd",
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
        raw_reference="https://example.com/ssd",
    )
    norm = NormalizedListingObservation(
        observation=obs,
        price_amount=Decimal("109.99"),
        currency_code="USD",
        availability=NormalizedAvailability.IN_STOCK,
        condition=NormalizedCondition.NEW,
        seller_name="Example Store",
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
    return PriceAggregationResult(
        request=run.to_research_request(),
        assessments=(assess,),
        exclusions=(),
        buckets=(
            PriceAggregateBucket(
                currency_code="USD",
                condition=NormalizedCondition.NEW,
                assessments=(assess,),
                count=1,
                low=Decimal("109.99"),
                median=Decimal("109.99"),
                high=Decimal("109.99"),
                market_range_low=None,
                market_range_high=None,
                confidence=ConfidenceLevel.LOW,
            ),
        ),
        verification_status=VerificationStatus.VERIFIED,
    )


class TestSnapshotCreation(TestCase):
    def test_snapshot_is_tied_to_its_run(self) -> None:
        run = _make_research_run()
        result = _make_minimal_result(run)
        payload = encode_price_aggregation_result(result)
        snapshot = PriceIntelligenceSnapshot.objects.create(
            run=run,
            schema_version=1,
            payload=payload,
        )
        assert snapshot.run_id == run.id

    def test_snapshot_is_found_through_run(self) -> None:
        run = _make_research_run()
        result = _make_minimal_result(run)
        payload = encode_price_aggregation_result(result)
        PriceIntelligenceSnapshot.objects.create(
            run=run,
            schema_version=1,
            payload=payload,
        )
        snapshot = run.price_intelligence_snapshot
        assert snapshot.run_id == run.id

    def test_only_one_snapshot_per_run(self) -> None:
        run = _make_research_run()
        result = _make_minimal_result(run)
        payload = encode_price_aggregation_result(result)
        PriceIntelligenceSnapshot.objects.create(
            run=run,
            schema_version=1,
            payload=payload,
        )
        with pytest.raises(IntegrityError):
            PriceIntelligenceSnapshot.objects.create(
                run=run,
                schema_version=1,
                payload=payload,
            )

    def test_snapshot_cannot_have_zero_version(self) -> None:
        run = _make_research_run()
        result = _make_minimal_result(run)
        payload = encode_price_aggregation_result(result)
        with pytest.raises(IntegrityError):
            PriceIntelligenceSnapshot.objects.create(
                run=run,
                schema_version=0,
                payload=payload,
            )

    def test_snapshot_has_created_at(self) -> None:
        run = _make_research_run()
        result = _make_minimal_result(run)
        payload = encode_price_aggregation_result(result)
        snapshot = PriceIntelligenceSnapshot.objects.create(
            run=run,
            schema_version=1,
            payload=payload,
        )
        assert snapshot.created_at is not None

    def test_snapshot_str(self) -> None:
        run = _make_research_run()
        result = _make_minimal_result(run)
        payload = encode_price_aggregation_result(result)
        snapshot = PriceIntelligenceSnapshot.objects.create(
            run=run,
            schema_version=1,
            payload=payload,
        )
        assert str(snapshot.run_id) in str(snapshot)
        assert "v1" in str(snapshot)


class TestSnapshotDoesNotInterpret(TestCase):
    """The snapshot model is storage, not interpretation."""

    def test_payload_is_stored_as_json_not_columns(self) -> None:
        run = _make_research_run()
        result = _make_result_with_data(run)
        payload = encode_price_aggregation_result(result)
        snapshot = PriceIntelligenceSnapshot.objects.create(
            run=run,
            schema_version=1,
            payload=payload,
        )
        snapshot.refresh_from_db()
        # The payload is a raw JSON dict, not structured fields.
        assert isinstance(snapshot.payload, dict)
        assert "verification_status" in snapshot.payload
        assert "assessments" in snapshot.payload
        assert "buckets" in snapshot.payload


class TestSnapshotRoundTrip(TestCase):
    """Store encoded result, read it back, decode, compare."""

    def test_store_and_decode_unknown_result(self) -> None:
        run = _make_research_run()
        result = _make_minimal_result(run)
        payload = encode_price_aggregation_result(result)
        PriceIntelligenceSnapshot.objects.create(
            run=run,
            schema_version=1,
            payload=payload,
        )
        snapshot = run.price_intelligence_snapshot
        decoded = decode_price_aggregation_result(
            snapshot.payload,
            schema_version=snapshot.schema_version,
        )
        assert decoded.request == result.request
        assert decoded.verification_status == VerificationStatus.UNKNOWN

    def test_store_and_decode_verified_result(self) -> None:
        run = _make_research_run()
        result = _make_result_with_data(run)
        payload = encode_price_aggregation_result(result)
        PriceIntelligenceSnapshot.objects.create(
            run=run,
            schema_version=1,
            payload=payload,
        )
        snapshot = run.price_intelligence_snapshot
        decoded = decode_price_aggregation_result(
            snapshot.payload,
            schema_version=snapshot.schema_version,
        )
        assert decoded.request == result.request
        assert decoded.verification_status == VerificationStatus.VERIFIED
        assert len(decoded.buckets) == 1
        assert decoded.buckets[0].median == Decimal("109.99")

    def test_cascade_deletes_snapshot_when_run_is_deleted(self) -> None:
        run = _make_research_run()
        result = _make_minimal_result(run)
        payload = encode_price_aggregation_result(result)
        PriceIntelligenceSnapshot.objects.create(
            run=run,
            schema_version=1,
            payload=payload,
        )
        run_id = run.id
        run.delete()
        assert PriceIntelligenceSnapshot.objects.filter(run_id=run_id).count() == 0
