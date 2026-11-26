"""SEMANTIC-V2-A1 — the web report boundary over the versioned snapshot.

The report decodes the run's OWN persisted PriceIntelligenceSnapshot
through the SAME replay-facing decode entry point
(``decode_price_aggregation_result``, now the version dispatcher): a
schema-2 snapshot (the SEMANTIC-V2-A1 publication shape) renders exactly
like its schema-1 twin, and the web read-side allowlist is unchanged
(no new web import — the dispatcher symbol is the frozen one).
"""

from __future__ import annotations

from decimal import Decimal

from django.test import TestCase
from django.urls import reverse

from product_intelligence.domain import ResearchRequest
from product_intelligence.domain.enums import (
    ConfidenceLevel,
    EvidenceDecision,
    IdentityMatchType,
    VerificationStatus,
)
from product_intelligence.research import (
    CURRENT_PRICE_RESULT_SCHEMA_VERSION,
    PRICE_RESULT_SCHEMA_VERSION,
    ExtractionMethod,
    ListingObservation,
    NormalizedAvailability,
    NormalizedCondition,
    NormalizedListingObservation,
    PriceAggregationResult,
    PriceAggregateBucket,
    decode_price_aggregation_result,
    encode_price_aggregation_result_v2,
)
from product_intelligence.research.matching import (
    EvidenceSource,
    ListingIdentityAssessment,
)
from product_intelligence.runs.models import (
    PriceIntelligenceSnapshot,
    ResearchRun,
)

DESCRIPTION_TEXT = (
    "3.84TB enterprise NVMe SSD, U.2 15mm, PCIe Gen4 x4, 1 DWPD."
)


def _make_run() -> ResearchRun:
    return ResearchRun.objects.create_from_request(
        ResearchRequest(
            manufacturer_part_number="MZ-SV2A1-WEB",
            description="enterprise SSD",
        )
    )


def _accepted_result(run: ResearchRun, description: str | None = None):
    request = run.to_research_request()
    observation = ListingObservation(
        source_url="https://example.com/sv2a1-web",
        extraction_method=ExtractionMethod.JSON_LD,
        product_title="SV2-A1 web drive",
        manufacturer_part_number_text="MZ-SV2A1-WEB",
        price_text="109.99",
        currency_text="USD",
        availability_text="In Stock",
        condition_text="New",
        seller_text="Example Store",
        description_text=description,
    )
    normalized = NormalizedListingObservation(
        observation=observation,
        price_amount=Decimal("109.99"),
        currency_code="USD",
        availability=NormalizedAvailability.IN_STOCK,
        condition=NormalizedCondition.NEW,
        seller_name="Example Store",
        normalization_issues=(),
    )
    assessment = ListingIdentityAssessment(
        normalized_listing=normalized,
        requested_part_number=request.manufacturer_part_number,
        candidate_part_number_raw="MZ-SV2A1-WEB",
        candidate_part_number_compared="MZ-SV2A1-WEB",
        candidate_evidence_source=EvidenceSource.EXPLICIT_MPN_FIELD,
        match_type=IdentityMatchType.EXACT,
        decision=EvidenceDecision.ACCEPTED,
        rejection_reason=None,
    )
    bucket = PriceAggregateBucket(
        currency_code="USD",
        condition=NormalizedCondition.NEW,
        assessments=(assessment,),
        count=1,
        low=Decimal("109.99"),
        median=Decimal("109.99"),
        high=Decimal("109.99"),
        market_range_low=None,
        market_range_high=None,
        confidence=ConfidenceLevel.LOW,
    )
    return PriceAggregationResult(
        request=request,
        assessments=(assessment,),
        exclusions=(),
        buckets=(bucket,),
        verification_status=VerificationStatus.VERIFIED,
    )


def _detail_url(run: ResearchRun) -> str:
    return reverse("research-detail", kwargs={"run_id": run.id})


class TestWebReportOverSchema2Snapshot(TestCase):
    def setUp(self) -> None:
        self.run = _make_run()

    def test_the_report_decodes_the_published_schema2_snapshot(self) -> None:
        result = _accepted_result(self.run, DESCRIPTION_TEXT)
        snapshot = PriceIntelligenceSnapshot.objects.create(
            run=self.run,
            schema_version=CURRENT_PRICE_RESULT_SCHEMA_VERSION,
            payload=encode_price_aggregation_result_v2(result),
        )
        assert snapshot.schema_version == 2

        response = self.client.get(_detail_url(self.run))

        self.assertEqual(response.status_code, 200)
        html = response.content.decode()
        # The Machine Price renders from the schema-2 payload through the
        # dispatcher (same symbol as before the phase).
        self.assertContains(response, "109.99")
        self.assertNotIn(
            "The stored price result is invalid or in an unsupported", html
        )

    def test_the_schema2_payload_is_decoded_with_its_recorded_version(self) -> None:
        """The report boundary decodes with the row's OWN recorded version
        (never a hardcoded 1): the same persisted row that renders a price
        here decodes through the dispatcher with the recorded 2."""
        result = _accepted_result(self.run, DESCRIPTION_TEXT)
        snapshot = PriceIntelligenceSnapshot.objects.create(
            run=self.run,
            schema_version=CURRENT_PRICE_RESULT_SCHEMA_VERSION,
            payload=encode_price_aggregation_result_v2(result),
        )
        decoded = decode_price_aggregation_result(
            snapshot.payload, schema_version=snapshot.schema_version
        )
        assert (
            decoded.assessments[0].normalized_listing.observation.description_text
            == DESCRIPTION_TEXT
        )
        response = self.client.get(_detail_url(self.run))
        self.assertEqual(response.status_code, 200)

    def test_a_historical_schema1_snapshot_renders_unchanged(self) -> None:
        """The schema-1 twin renders identically: historical replay
        behavior is preserved through the dispatcher."""
        from product_intelligence.research import (
            encode_price_aggregation_result,
        )

        result = _accepted_result(self.run)
        PriceIntelligenceSnapshot.objects.create(
            run=self.run,
            schema_version=PRICE_RESULT_SCHEMA_VERSION,
            payload=encode_price_aggregation_result(result),
        )

        response = self.client.get(_detail_url(self.run))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "109.99")
