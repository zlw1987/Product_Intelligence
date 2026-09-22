# ============================================================================
# BLOCKER 1 (FU3): Fail-closed propagation tests
# ============================================================================

from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
from unittest.mock import patch

import pytest

from product_intelligence.execution.compact_quote_replay import (
    replay_compact_quote_projection,
)
from product_intelligence.research.compact_quote import (
    CompactQuoteProjectionError,
)


# ---------------------------------------------------------------------------
# Test fixtures — build real research objects used in replay mocking
# ---------------------------------------------------------------------------

def _build_real_price_result() -> object:
    """Build a real PriceAggregationResult for testing."""
    from product_intelligence.domain import ResearchRequest
    from product_intelligence.domain.enums import (
        IdentityMatchType,
        VerificationStatus,
    )
    from product_intelligence.research.aggregation import (
        PriceAggregateBucket,
        PriceAggregationResult,
        ConfidenceLevel,
    )
    from product_intelligence.research.listings import (
        ListingObservation,
        ExtractionMethod,
    )
    from product_intelligence.research.matching import (
        ListingIdentityAssessment,
        EvidenceDecision,
        EvidenceSource,
    )
    from product_intelligence.research.normalization import (
        NormalizedCondition,
        normalize_listing_observation,
    )

    obs = ListingObservation(
        source_url="https://example.com/product",
        extraction_method=ExtractionMethod.JSON_LD,
        product_title="Test Product",
        manufacturer_part_number_text="TEST-MPN",
        sku_text=None,
        brand_text="TestBrand",
        price_text="2500.00",
        currency_text="USD",
        availability_text="https://schema.org/InStock",
        condition_text="NEW",
        seller_text=None,
        offer_url_text=None,
        raw_reference=None,
    )
    normalized = normalize_listing_observation(obs)
    assessment = ListingIdentityAssessment(
        normalized_listing=normalized,
        requested_part_number="TEST-MPN",
        candidate_part_number_raw="TEST-MPN",
        candidate_part_number_compared="TEST-MPN",
        candidate_evidence_source=EvidenceSource.EXPLICIT_MPN_FIELD,
        match_type=IdentityMatchType.EXACT,
        decision=EvidenceDecision.ACCEPTED,
        rejection_reason=None,
    )
    bucket = PriceAggregateBucket(
        currency_code="USD",
        condition=NormalizedCondition("NEW"),
        assessments=(assessment,),
        count=1,
        low=Decimal("2500.00"),
        median=Decimal("2500.00"),
        high=Decimal("2500.00"),
        market_range_low=None,
        market_range_high=None,
        confidence=ConfidenceLevel.LOW,
    )
    request = ResearchRequest(
        manufacturer_part_number="TEST-MPN",
        description="Test",
    )
    return PriceAggregationResult(
        request=request,
        assessments=(assessment,),
        buckets=(bucket,),
        exclusions=(),
        verification_status=VerificationStatus.VERIFIED,
    )


def _build_real_vendor_commercial() -> object:
    """Build a real VendorCommercialResult for testing."""
    from product_intelligence.research.commercial_supplement_codec import (
        VendorCommercialResult,
        SupplementLookupStatus,
        SupplementSourceObservation,
    )

    obs = SupplementSourceObservation(
        source_name="Ingram",
        explicit_candidate_mpn="TEST-MPN",
        vendor_mpn_match_type="EXACT",
        price_amount=Decimal("2023.27"),
        currency_code="USD",
        availability="IN_STOCK",
        price_basis="LIST_PRICE",
        quantity=1,
        note_kind=None,
        brand_new=True,
        brand_new_basis="VENDOR_API_POLICY",
    )
    return VendorCommercialResult(
        lookup_status=SupplementLookupStatus.SUCCESS,
        retrieved_at=datetime(2024, 1, 15, 12, 0, 0, tzinfo=timezone.utc),
        observations=(obs,),
        source_issues=(),
    )


def _build_non_reportable_vendor_commercial() -> object:
    """Build a NON-REPORTABLE VendorCommercialResult (brand_new=False)."""
    from product_intelligence.research.commercial_supplement_codec import (
        VendorCommercialResult,
        SupplementLookupStatus,
        SupplementSourceObservation,
    )

    obs = SupplementSourceObservation(
        source_name="Ingram",
        explicit_candidate_mpn="TEST-MPN",
        vendor_mpn_match_type="EXACT",
        price_amount=Decimal("2023.27"),
        currency_code="USD",
        availability="IN_STOCK",
        price_basis="LIST_PRICE",
        quantity=1,
        note_kind=None,
        brand_new=False,  # Non-reportable
        brand_new_basis="VENDOR_API_POLICY",
    )
    return VendorCommercialResult(
        lookup_status=SupplementLookupStatus.SUCCESS,
        retrieved_at=datetime(2024, 1, 15, 12, 0, 0, tzinfo=timezone.utc),
        observations=(obs,),
        source_issues=(),
    )


# ---------------------------------------------------------------------------
# BLOCKER 1 (FU3) fail-closed tests
#
# Django test database is configured by tests/conftest.py (session-scoped).
# Tests use real ResearchRun/PriceIntelligenceSnapshot model instances.
# Only the projection layer (project_*) is patched to control scenarios.
# ---------------------------------------------------------------------------

pytestmark = pytest.mark.django_db


def _create_completed_run() -> object:
    """Helper: create a ResearchRun in COMPLETED state."""
    from product_intelligence.runs.models import ResearchRun
    run = ResearchRun.objects.create(
        state="CREATED",
        manufacturer_part_number="TEST-MPN",
        description="Test",
    )
    run.transition_to("RUNNING")
    run.transition_to("COMPLETED")
    return run


class TestHistoricalReplayFailClosed:
    """BLOCKER 1 (FU3): Historical replay is fail-closed.

    Once a persisted canonical artifact exists, any exception from
    project_public_rows or project_vendor_api_row MUST propagate.
    The replay does NOT swallow codec/contract/programming errors
    and return a partial projection.

    Each test creates real Django model instances (with proper DB state)
    but patches the projection functions to control the test scenarios.
    """

    def test_public_projection_runtime_error_propagates(self) -> None:
        """BLOCKER 1 (FU3): project_public_rows RuntimeError propagates."""
        from product_intelligence.runs.models import (
            PriceIntelligenceSnapshot,
            ResearchFxSnapshot,
        )
        from product_intelligence.research.price_result_codec import (
            encode_price_aggregation_result,
        )

        price_result = _build_real_price_result()
        encoded = encode_price_aggregation_result(price_result)

        run = _create_completed_run()
        PriceIntelligenceSnapshot.objects.create(
            run=run,
            payload=encoded,
            schema_version=1,
        )
        # No FX snapshot — ResearchFxSnapshot.DoesNotExist raised

        run_id = str(run.id)

        # Patch project_public_rows to raise RuntimeError.
        # The replay MUST propagate — it does NOT catch and
        # return a partial empty projection.
        with patch(
            'product_intelligence.execution.compact_quote_replay.project_public_rows',
            side_effect=RuntimeError(
                "project_public_rows programming defect",
            ),
        ):
            with pytest.raises(
                RuntimeError,
                match="project_public_rows programming defect",
            ):
                replay_compact_quote_projection(run_id)

    def test_vendor_projection_runtime_error_propagates(self) -> None:
        """BLOCKER 1 (FU3): project_vendor_api_row RuntimeError propagates."""
        from product_intelligence.runs.models import (
            PriceIntelligenceSnapshot,
            ResearchSupplementSnapshot,
        )
        from product_intelligence.research.price_result_codec import (
            encode_price_aggregation_result,
        )
        from product_intelligence.research.commercial_supplement_codec import (
            encode_research_supplement_result,
            ResearchSupplementResult,
        )

        price_result = _build_real_price_result()
        vendor_commercial = _build_real_vendor_commercial()
        encoded_price = encode_price_aggregation_result(price_result)
        supplement_result = ResearchSupplementResult(
            vendor_commercial_result=vendor_commercial,
        )
        encoded_supplement = encode_research_supplement_result(supplement_result)

        run = _create_completed_run()
        PriceIntelligenceSnapshot.objects.create(
            run=run,
            payload=encoded_price,
            schema_version=1,
        )
        ResearchSupplementSnapshot.objects.create(
            run=run,
            payload=encoded_supplement,
            schema_version=1,
        )

        run_id = str(run.id)

        # Patch project_vendor_api_row to raise RuntimeError.
        # The replay MUST propagate — it does NOT catch and skip.
        with patch(
            'product_intelligence.execution.compact_quote_replay.project_vendor_api_row',
            side_effect=RuntimeError(
                "project_vendor_api_row programming defect",
            ),
        ):
            with pytest.raises(
                RuntimeError,
                match="project_vendor_api_row programming defect",
            ):
                replay_compact_quote_projection(run_id)

    def test_malformed_supplement_payload_propagates(self) -> None:
        """BLOCKER 1 (FU3): Malformed supplemental payload propagates codec error."""
        from product_intelligence.runs.models import (
            PriceIntelligenceSnapshot,
            ResearchSupplementSnapshot,
        )
        from product_intelligence.research.price_result_codec import (
            encode_price_aggregation_result,
        )
        from product_intelligence.research.commercial_supplement_codec import (
            SupplementCodecError,
        )

        price_result = _build_real_price_result()
        encoded_price = encode_price_aggregation_result(price_result)

        run = _create_completed_run()
        PriceIntelligenceSnapshot.objects.create(
            run=run,
            payload=encoded_price,
            schema_version=1,
        )
        # Malformed supplemental payload — schema_version as int where
        # observations is a non-list (triggers SupplementCodecError)
        ResearchSupplementSnapshot.objects.create(
            run=run,
            payload={'schema_version': 1, 'observations': 999},
            schema_version=1,
        )

        run_id = str(run.id)

        with pytest.raises(SupplementCodecError):
            replay_compact_quote_projection(run_id)

    def test_malformed_price_payload_propagates(self) -> None:
        """BLOCKER 1 (FU3): Malformed price payload propagates codec error."""
        from product_intelligence.runs.models import PriceIntelligenceSnapshot
        from product_intelligence.research.price_result_codec import (
            PriceResultCodecError,
        )

        run = _create_completed_run()
        # Malformed price payload — invalid top-level structure that
        # decode_price_aggregation_result will reject
        PriceIntelligenceSnapshot.objects.create(
            run=run,
            payload={'schema_version': 1, 'not_a_valid_field': True},
            schema_version=1,
        )

        run_id = str(run.id)

        with pytest.raises(PriceResultCodecError):
            replay_compact_quote_projection(run_id)

    def test_non_reportable_observation_projection_error_propagates(self) -> None:
        """BLOCKER 1 (FU3): Non-reportable SupplementSourceObservation fails replay."""
        from product_intelligence.runs.models import (
            PriceIntelligenceSnapshot,
            ResearchSupplementSnapshot,
        )
        from product_intelligence.research.price_result_codec import (
            encode_price_aggregation_result,
        )
        from product_intelligence.research.commercial_supplement_codec import (
            encode_research_supplement_result,
            ResearchSupplementResult,
        )

        price_result = _build_real_price_result()
        vendor_commercial = _build_non_reportable_vendor_commercial()
        encoded_price = encode_price_aggregation_result(price_result)
        supplement_result = ResearchSupplementResult(
            vendor_commercial_result=vendor_commercial,
        )
        encoded_supplement = encode_research_supplement_result(supplement_result)

        run = _create_completed_run()
        PriceIntelligenceSnapshot.objects.create(
            run=run,
            payload=encoded_price,
            schema_version=1,
        )
        ResearchSupplementSnapshot.objects.create(
            run=run,
            payload=encoded_supplement,
            schema_version=1,
        )

        run_id = str(run.id)

        # The non-reportable observation's projection error propagates.
        # replay does NOT silently skip the row.
        with pytest.raises(
            CompactQuoteProjectionError,
            match="brand_new=True",
        ):
            replay_compact_quote_projection(run_id)