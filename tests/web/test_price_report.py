"""Web report tests for price intelligence snapshot (PRODUCT-INTEL.4B).

Tests that:
* A run without snapshot shows "no research result" (not fabricated data)
* A run with valid decoded snapshot shows evidence
* Corrupt payloads are shown as unavailable (fail-closed)
* Provenance mismatch shows zero numbers (fail-closed)
* Unsupported schema versions show zero numbers (fail-closed)
* Report never transitions the run
* External URLs are hyperlinked only when safe
"""

from __future__ import annotations

from decimal import Decimal

import pytest
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
    ListingIdentityAssessment,
    ListingObservation,
    PriceAggregateBucket,
    PriceAggregationResult,
    decode_price_aggregation_result,
    encode_price_aggregation_result,
)
from product_intelligence.research.listings import ExtractionMethod
from product_intelligence.research.matching import EvidenceSource, IdentityRejectionReason
from product_intelligence.research.normalization import (
    NormalizedAvailability,
    NormalizedCondition,
    NormalizedListingObservation,
)
from product_intelligence.runs.models import PriceIntelligenceSnapshot, ResearchRun
from product_intelligence.research import PriceResultCodecError


def _create_run(
    mpn: str = "MZ-V8P1T0B/AM",
    description: str = "1TB NVMe M.2 solid state drive",
) -> ResearchRun:
    return ResearchRun.objects.create_from_request(
        ResearchRequest(
            manufacturer_part_number=mpn,
            description=description,
        ),
    )


def _detail_url(run: ResearchRun) -> str:
    return reverse("research-detail", kwargs={"run_id": run.id})


def _make_result_with_data(
    run: ResearchRun,
    *,
    product_title: str | None = "Samsung 980 PRO 1TB",
    seller_name: str | None = "Example Store",
    price_text: str | None = "$109.99",
    source_url: str | None = "https://example.com/ssd-1tb",
) -> PriceAggregationResult:
    """Build a VERIFIED result with customizable observation fields.

    For external-text escaping regression tests.
    """
    mpn = run.manufacturer_part_number or "TEST-001"
    obs = ListingObservation(
        source_url=source_url or "https://example.com/ssd-1tb",
        extraction_method=ExtractionMethod.JSON_LD,
        product_title=product_title,
        manufacturer_part_number_text=mpn,
        sku_text="SSD-980-1T",
        brand_text="Samsung",
        price_text=price_text or "$109.99",
        currency_text="USD",
        availability_text="In Stock",
        condition_text="New",
        seller_text=seller_name or "Example Store",
        offer_url_text=None,
        raw_reference=source_url or "https://example.com/ssd-1tb",
    )
    norm = NormalizedListingObservation(
        observation=obs,
        price_amount=Decimal("109.99"),
        currency_code="USD",
        availability=NormalizedAvailability.IN_STOCK,
        condition=NormalizedCondition.NEW,
        seller_name=seller_name,
        normalization_issues=(),
    )
    assess = ListingIdentityAssessment(
        normalized_listing=norm,
        requested_part_number=mpn,
        candidate_part_number_raw=mpn,
        candidate_part_number_compared=mpn,
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


def _make_simple_result(run: ResearchRun) -> PriceAggregationResult:
    """Build a minimal VERIFIED result for testing."""
    mpn = run.manufacturer_part_number or "TEST-001"
    obs = ListingObservation(
        source_url="https://example.com/ssd-1tb",
        extraction_method=ExtractionMethod.JSON_LD,
        product_title="Samsung 980 PRO 1TB",
        manufacturer_part_number_text=mpn,
        sku_text="SSD-980-1T",
        brand_text="Samsung",
        price_text="$109.99",
        currency_text="USD",
        availability_text="In Stock",
        condition_text="New",
        seller_text="Example Store",
        offer_url_text=None,
        raw_reference="https://example.com/ssd-1tb",
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
        requested_part_number=mpn,
        candidate_part_number_raw=mpn,
        candidate_part_number_compared=mpn,
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


def _make_unknown_result(run: ResearchRun) -> PriceAggregationResult:
    """Build a minimal UNKNOWN result with exclusions."""
    mpn = run.manufacturer_part_number or "TEST-001"
    obs = ListingObservation(
        source_url="https://example.com/wrong-product",
        extraction_method=ExtractionMethod.JSON_LD,
        product_title="Different Product",
        manufacturer_part_number_text="WRONG-MPN",
        sku_text=None,
        brand_text=None,
        price_text="$50.00",
        currency_text="USD",
        availability_text="In Stock",
        condition_text="New",
        seller_text="Wrong Seller",
        offer_url_text=None,
        raw_reference=None,
    )
    norm = NormalizedListingObservation(
        observation=obs,
        price_amount=Decimal("50.00"),
        currency_code="USD",
        availability=NormalizedAvailability.IN_STOCK,
        condition=NormalizedCondition.NEW,
        seller_name="Wrong Seller",
        normalization_issues=(),
    )
    assess = ListingIdentityAssessment(
        normalized_listing=norm,
        requested_part_number=mpn,
        candidate_part_number_raw="WRONG-MPN",
        candidate_part_number_compared="WRONG-MPN",
        candidate_evidence_source=EvidenceSource.EXPLICIT_MPN_FIELD,
        match_type=IdentityMatchType.UNKNOWN,
        decision=EvidenceDecision.REJECTED,
        rejection_reason=IdentityRejectionReason.MPN_MISMATCH,
    )
    from product_intelligence.research.aggregation import PriceAggregationExclusion, PriceAggregationExclusionReason
    return PriceAggregationResult(
        request=run.to_research_request(),
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


def _attach_snapshot(run: ResearchRun, result: PriceAggregationResult) -> None:
    payload = encode_price_aggregation_result(result)
    PriceIntelligenceSnapshot.objects.create(
        run=run,
        schema_version=1,
        payload=payload,
    )


# ---------------------------------------------------------------------------
# Test cases
# ---------------------------------------------------------------------------


class TestNoSnapshot(TestCase):
    """A run without a snapshot shows no fabricated data."""

    def test_no_snapshot_shows_notice(self) -> None:
        run = _create_run()
        response = self.client.get(_detail_url(run))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "No research result available")

    def test_no_snapshot_shows_no_prices(self) -> None:
        run = _create_run()
        response = self.client.get(_detail_url(run))
        html = response.content.decode()

        for fabricated in ("$0", "N/A", "0.00"):
            self.assertNotIn(fabricated, html)

    def test_no_snapshot_shows_no_median(self) -> None:
        run = _create_run()
        response = self.client.get(_detail_url(run))
        html = response.content.decode()

        self.assertNotIn("Median", html)
        self.assertNotIn("median", html.lower())

    def test_no_snapshot_shows_no_109(self) -> None:
        """No placeholder price number appears."""
        run = _create_run()
        response = self.client.get(_detail_url(run))
        html = response.content.decode()

        self.assertNotIn("109", html)


class TestValidSnapshot(TestCase):
    """A run with a valid decoded snapshot shows evidence."""

    def test_verified_snapshot_shows_status(self) -> None:
        run = _create_run()
        result = _make_simple_result(run)
        _attach_snapshot(run, result)

        response = self.client.get(_detail_url(run))

        self.assertContains(response, "VERIFIED")
        self.assertContains(response, "USD")
        self.assertContains(response, "109.99")

    def test_verified_snapshot_shows_median(self) -> None:
        run = _create_run()
        result = _make_simple_result(run)
        _attach_snapshot(run, result)

        response = self.client.get(_detail_url(run))

        self.assertContains(response, "Median")
        self.assertContains(response, "109.99")

    def test_verified_snapshot_shows_confidence(self) -> None:
        run = _create_run()
        result = _make_simple_result(run)
        _attach_snapshot(run, result)

        response = self.client.get(_detail_url(run))

        self.assertContains(response, "LOW")

    def test_verified_snapshot_shows_source_url(self) -> None:
        run = _create_run()
        result = _make_simple_result(run)
        _attach_snapshot(run, result)

        response = self.client.get(_detail_url(run))

        self.assertContains(response, "https://example.com/ssd-1tb")

    def test_verified_snapshot_shows_seller(self) -> None:
        run = _create_run()
        result = _make_simple_result(run)
        _attach_snapshot(run, result)

        response = self.client.get(_detail_url(run))

        self.assertContains(response, "Example Store")

    def test_verified_snapshot_shows_product_title(self) -> None:
        run = _create_run()
        result = _make_simple_result(run)
        _attach_snapshot(run, result)

        response = self.client.get(_detail_url(run))

        self.assertContains(response, "Samsung 980 PRO 1TB")

    def test_verified_snapshot_shows_match_type(self) -> None:
        run = _create_run()
        result = _make_simple_result(run)
        _attach_snapshot(run, result)

        response = self.client.get(_detail_url(run))

        self.assertContains(response, "EXACT")

    def test_verified_snapshot_shows_observation_count(self) -> None:
        run = _create_run()
        result = _make_simple_result(run)
        _attach_snapshot(run, result)

        response = self.client.get(_detail_url(run))

        self.assertContains(response, "Observations")
        self.assertContains(response, "1")

    def test_unknown_snapshot_shows_exclusions(self) -> None:
        run = _create_run()
        result = _make_unknown_result(run)
        _attach_snapshot(run, result)

        response = self.client.get(_detail_url(run))

        self.assertContains(response, "UNKNOWN")
        self.assertContains(response, "Excluded listings")
        self.assertContains(response, "Exclusion reason")

    def test_unknown_snapshot_shows_no_median_price(self) -> None:
        """UNKNOWN result has no bucket, so no median is shown."""
        run = _create_run()
        result = _make_unknown_result(run)
        _attach_snapshot(run, result)

        response = self.client.get(_detail_url(run))

        self.assertNotContains(response, "Median")
        # Exclusions show raw price text as evidence, which is correct.
        # What we must not show is a median/aggregate price.


class TestCorruptSnapshot(TestCase):
    """Corrupt or invalid payloads are shown as unavailable."""

    def test_corrupt_payload_shows_unavailable(self) -> None:
        """Store garbage JSON that fails codec decode."""
        run = _create_run()
        PriceIntelligenceSnapshot.objects.create(
            run=run,
            schema_version=1,
            payload="not valid json structure",
        )

        response = self.client.get(_detail_url(run))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "unavailable")
        # No fabricated numbers
        html = response.content.decode()
        self.assertNotIn("109", html)

    def test_unsupported_schema_version_shows_unavailable(self) -> None:
        """Store valid JSON with unsupported schema version."""
        run = _create_run()
        PriceIntelligenceSnapshot.objects.create(
            run=run,
            schema_version=99,
            payload={"verification_status": "UNKNOWN"},
        )

        response = self.client.get(_detail_url(run))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "unavailable")

    def test_malformed_bucket_data_shows_unavailable(self) -> None:
        """Payload with missing required keys fails decode."""
        run = _create_run()
        PriceIntelligenceSnapshot.objects.create(
            run=run,
            schema_version=1,
            payload={
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
                        # missing "low", "median", "high", "confidence"
                    },
                ],
                "exclusions": [],
                "verification_status": "VERIFIED",
            },
        )

        response = self.client.get(_detail_url(run))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "unavailable")


class TestProvenanceMismatch(TestCase):
    """Snapshot for a different request is not presented."""

    def test_provenance_mismatch_shows_unavailable(self) -> None:
        """Store a result for a different MPN than the run."""
        run = _create_run(mpn="RIGHT-MPN")
        wrong_run = _create_run(mpn="WRONG-MPN")
        result = _make_simple_result(wrong_run)
        _attach_snapshot(run, result)

        response = self.client.get(_detail_url(run))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "does not match")
        # No fabricated numbers from the wrong request
        html = response.content.decode()
        self.assertNotIn("109.99", html)


class TestReportIsReadOnly(TestCase):
    """Viewing the report changes nothing."""

    def test_viewing_report_does_not_transition_run(self) -> None:
        run = _create_run()
        result = _make_simple_result(run)
        _attach_snapshot(run, result)

        for _ in range(3):
            self.client.get(_detail_url(run))

        run.refresh_from_db()
        self.assertEqual(run.state, "CREATED")

    def test_viewing_report_does_not_change_state_or_timestamps(self) -> None:
        """Prove GET does not mutate the run or snapshot by before/after."""
        run = _create_run()
        result = _make_simple_result(run)
        _attach_snapshot(run, result)

        snapshot = run.price_intelligence_snapshot

        # Capture before state.
        before_run_count = ResearchRun.objects.count()
        before_snap_count = PriceIntelligenceSnapshot.objects.count()
        before_state = run.state
        before_started = run.started_at
        before_finished = run.finished_at
        before_payload = dict(snapshot.payload)
        before_version = snapshot.schema_version
        before_created = snapshot.created_at

        for _ in range(3):
            self.client.get(_detail_url(run))

        run.refresh_from_db()
        snapshot.refresh_from_db()

        self.assertEqual(ResearchRun.objects.count(), before_run_count)
        self.assertEqual(PriceIntelligenceSnapshot.objects.count(), before_snap_count)
        self.assertEqual(run.state, before_state)
        self.assertEqual(run.started_at, before_started)
        self.assertEqual(run.finished_at, before_finished)
        self.assertEqual(snapshot.payload, before_payload)
        self.assertEqual(snapshot.schema_version, before_version)
        self.assertEqual(snapshot.created_at, before_created)


class TestURLEscaping(TestCase):
    """External URLs are safe in the report."""

    def test_http_url_is_hyperlinked(self) -> None:
        """A valid http:// URL is an href."""
        run = _create_run()
        result = _make_simple_result(run)
        _attach_snapshot(run, result)

        response = self.client.get(_detail_url(run))

        self.assertContains(response, 'href="https://example.com/ssd-1tb"')

    def test_javascript_url_is_not_hyperlinked(self) -> None:
        """A javascript: URL is never an href."""
        run = _create_run()
        mpn = run.manufacturer_part_number or "TEST-001"
        obs = ListingObservation(
            source_url="javascript:alert('xss')",
            extraction_method=ExtractionMethod.JSON_LD,
            product_title="Test",
            manufacturer_part_number_text=mpn,
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
        assess = ListingIdentityAssessment(
            normalized_listing=norm,
            requested_part_number=mpn,
            candidate_part_number_raw=mpn,
            candidate_part_number_compared=mpn,
            candidate_evidence_source=EvidenceSource.EXPLICIT_MPN_FIELD,
            match_type=IdentityMatchType.EXACT,
            decision=EvidenceDecision.ACCEPTED,
            rejection_reason=None,
        )
        result = PriceAggregationResult(
            request=run.to_research_request(),
            assessments=(assess,),
            exclusions=(),
            buckets=(
                PriceAggregateBucket(
                    currency_code="USD",
                    condition=NormalizedCondition.NEW,
                    assessments=(assess,),
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
        _attach_snapshot(run, result)

        response = self.client.get(_detail_url(run))
        html = response.content.decode()

        # The URL text appears but NOT as an href.
        self.assertIn("javascript:alert", html)
        self.assertNotIn('href="javascript:', html)
        self.assertNotIn("href='javascript:", html)


class TestSnapshotTimestamp(TestCase):
    """The snapshot stored-at timestamp is shown correctly."""

    def test_snapshot_timestamp_is_shown(self) -> None:
        run = _create_run()
        result = _make_simple_result(run)
        _attach_snapshot(run, result)

        response = self.client.get(_detail_url(run))

        self.assertContains(response, "snapshot stored at")


class TestExternalTextEscaping(TestCase):
    """External listing text (product titles, seller names, raw text)
    is untrusted and must be HTML-escaped in the report. These are
    regression tests against the 1B escaping contract extended to
    the price intelligence report in 4B."""

    def test_external_product_title_is_escaped(self) -> None:
        """A product title containing HTML markup is escaped, not rendered."""
        run = _create_run()
        result = _make_result_with_data(
            run,
            product_title='<b>Special</b> SSD &amp; "NVMe" Drive',
        )
        _attach_snapshot(run, result)
        response = self.client.get(_detail_url(run))
        html = response.content.decode()

        # Raw tags must not appear rendered
        self.assertNotIn("<b>Special</b>", html)
        # Escaped form must appear
        self.assertIn("&lt;b&gt;Special&lt;/b&gt;", html)

    def test_external_seller_name_is_escaped(self) -> None:
        """A seller name containing HTML is escaped."""
        run = _create_run()
        result = _make_result_with_data(
            run,
            seller_name='<script>alert("xss")</script> Evil Store',
        )
        _attach_snapshot(run, result)
        response = self.client.get(_detail_url(run))
        html = response.content.decode()

        self.assertNotIn("<script>", html)
        self.assertIn("&lt;script&gt;", html)
        self.assertIn("Evil Store", html)

    def test_external_raw_price_text_is_escaped(self) -> None:
        """Raw price text from a listing is escaped."""
        run = _create_run()
        result = _make_result_with_data(
            run,
            price_text="<b>$109.99</b>",
        )
        _attach_snapshot(run, result)
        response = self.client.get(_detail_url(run))
        html = response.content.decode()

        self.assertNotIn("<b>$109.99</b>", html)
        self.assertIn("&lt;b&gt;$109.99&lt;/b&gt;", html)


class TestDecoderWrappingWeb(TestCase):
    """Issue 2: Persisted data with wrong bucket median shows unavailable."""

    def test_wrong_bucket_median_shows_unavailable(self) -> None:
        """Persist a structurally complete V1 payload whose bucket median
        is wrong. GET /research/<uuid> must return 200, show
        stored-result-unavailable, and show zero aggregate price values.
        """
        run = _create_run(mpn="TEST-1")
        mpn = "TEST-1"
        obs = ListingObservation(
            source_url="https://example.com/test",
            extraction_method=ExtractionMethod.JSON_LD,
            product_title="Test Product",
            manufacturer_part_number_text=mpn,
            sku_text=None,
            brand_text=None,
            price_text="$100",
            currency_text="USD",
            availability_text="In Stock",
            condition_text="New",
            seller_text="Test Seller",
            offer_url_text=None,
            raw_reference=None,
        )
        norm = NormalizedListingObservation(
            observation=obs,
            price_amount=Decimal("100"),
            currency_code="USD",
            availability=NormalizedAvailability.IN_STOCK,
            condition=NormalizedCondition.NEW,
            seller_name="Test Seller",
            normalization_issues=(),
        )
        assess = ListingIdentityAssessment(
            normalized_listing=norm,
            requested_part_number=mpn,
            candidate_part_number_raw=mpn,
            candidate_part_number_compared=mpn,
            candidate_evidence_source=EvidenceSource.EXPLICIT_MPN_FIELD,
            match_type=IdentityMatchType.EXACT,
            decision=EvidenceDecision.ACCEPTED,
            rejection_reason=None,
        )

        # Encode a valid result, then tamper with the median
        result = PriceAggregationResult(
            request=run.to_research_request(),
            assessments=(assess,),
            exclusions=(),
            buckets=(
                PriceAggregateBucket(
                    currency_code="USD",
                    condition=NormalizedCondition.NEW,
                    assessments=(assess,),
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
        payload = encode_price_aggregation_result(result)
        # Tamper: set a wrong median
        payload["buckets"][0]["median"] = "999"

        PriceIntelligenceSnapshot.objects.create(
            run=run,
            schema_version=1,
            payload=payload,
        )

        response = self.client.get(_detail_url(run))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "unavailable")
        # No fabricated numbers
        html = response.content.decode()
        self.assertNotIn("999", html)
        self.assertNotIn("Median", html)


class TestMalformedSourceURLWeb(TestCase):
    """Issue 3: Malformed source URL in a listing does not crash the report."""

    def test_malformed_ipv6_source_url_200(self) -> None:
        """A listing with a malformed bracketed IPv6 source URL does not
        cause the report view to 500. The URL is not an href.
        """
        run = _create_run(mpn="TEST-1")
        obs = ListingObservation(
            source_url="https://[::1:invalid]/product",
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
        assess = ListingIdentityAssessment(
            normalized_listing=norm,
            requested_part_number="TEST-1",
            candidate_part_number_raw="TEST-1",
            candidate_part_number_compared="TEST-1",
            candidate_evidence_source=EvidenceSource.EXPLICIT_MPN_FIELD,
            match_type=IdentityMatchType.EXACT,
            decision=EvidenceDecision.ACCEPTED,
            rejection_reason=None,
        )
        result = PriceAggregationResult(
            request=run.to_research_request(),
            assessments=(assess,),
            exclusions=(),
            buckets=(
                PriceAggregateBucket(
                    currency_code="USD",
                    condition=NormalizedCondition.NEW,
                    assessments=(assess,),
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
        _attach_snapshot(run, result)

        response = self.client.get(_detail_url(run))
        self.assertEqual(response.status_code, 200)
        html = response.content.decode()
        # The URL text appears in the page
        self.assertIn("[::1:invalid]", html)
        # But it is NOT an href
        self.assertNotIn('href="https://[::1:invalid]', html)


class TestExcludedEvidenceHTML(TestCase):
    """Issue 5: Prove the rendered HTML includes 3C rejection evidence."""

    def test_unknown_mpn_mismatch_shows_rejection_evidence(self) -> None:
        """For the existing UNKNOWN/MPN_MISMATCH example, prove the
        rendered HTML includes:
        - IDENTITY_NOT_ACCEPTED
        - MPN_MISMATCH
        - EXPLICIT_MPN_FIELD
        - WRONG-MPN (the candidate MPN)
        - compared candidate MPN
        """
        run = _create_run(mpn="MZ-V8P1T0B/AM")
        result = _make_unknown_result(run)
        _attach_snapshot(run, result)

        response = self.client.get(_detail_url(run))
        self.assertEqual(response.status_code, 200)
        html = response.content.decode()

        # 3C rejection evidence must be visible
        self.assertIn("IDENTITY_NOT_ACCEPTED", html)
        self.assertIn("MPN_MISMATCH", html)
        self.assertIn("EXPLICIT_MPN_FIELD", html)
        self.assertIn("WRONG-MPN", html)
        # The compared candidate MPN is shown
        self.assertIn("Compared candidate MPN", html)
