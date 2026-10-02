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

import re
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


def _make_multi_observation_result(
    run: ResearchRun,
    specs: tuple[tuple[Decimal, str], ...],
) -> PriceAggregationResult:
    """Build a result from distinct accepted observations through the
    frozen 4A aggregation.

    *specs* is a tuple of ``(price, currency_code)`` pairs. Every
    observation is NEW / EXACT / ACCEPTED with a distinct source URL,
    title, and SKU, so the bucket statistics (count / low / exact
    Decimal median / high / market range / confidence) are computed by
    the unchanged domain code.
    """
    from product_intelligence.research.aggregation import aggregate_listing_prices

    mpn = run.manufacturer_part_number or "TEST-001"
    assessments = []
    for index, (price, currency) in enumerate(specs):
        obs = ListingObservation(
            source_url=f"https://example.com/ssd-1tb-{index}",
            extraction_method=ExtractionMethod.JSON_LD,
            product_title=f"Samsung 980 PRO 1TB variant {index}",
            manufacturer_part_number_text=mpn,
            sku_text=f"SSD-980-1T-{index}",
            brand_text="Samsung",
            price_text=str(price),
            currency_text=currency,
            availability_text="In Stock",
            condition_text="New",
            seller_text="Example Store",
            offer_url_text=None,
            raw_reference=f"https://example.com/ssd-1tb-{index}",
        )
        norm = NormalizedListingObservation(
            observation=obs,
            price_amount=price,
            currency_code=currency,
            availability=NormalizedAvailability.IN_STOCK,
            condition=NormalizedCondition.NEW,
            seller_name="Example Store",
            normalization_issues=(),
        )
        assessments.append(
            ListingIdentityAssessment(
                normalized_listing=norm,
                requested_part_number=mpn,
                candidate_part_number_raw=mpn,
                candidate_part_number_compared=mpn,
                candidate_evidence_source=EvidenceSource.EXPLICIT_MPN_FIELD,
                match_type=IdentityMatchType.EXACT,
                decision=EvidenceDecision.ACCEPTED,
                rejection_reason=None,
            )
        )
    return aggregate_listing_prices(run.to_research_request(), tuple(assessments))


#: Advanced Evidence & Audit — Price intelligence details block (literal
#: template text renders with a bare & and an em dash).
PRICE_ADVANCED_SECTION_MARKER = "Advanced Evidence & Audit — Price intelligence"

_BUCKET_H3_RE = re.compile(
    r"<h3>(?:Comparable price group|Price group: [^<]*)</h3>\s*<dl>(.*?)</dl>",
    re.S,
)


def _price_intelligence_advanced_section(html: str) -> str:
    """The rendered Advanced Evidence & Audit — Price intelligence block."""
    start = html.index(PRICE_ADVANCED_SECTION_MARKER)
    end = html.index("</details>", start)
    return html[start:end]


def _quote_market_summary_section(html: str) -> str:
    """The rendered Quote & Market Summary region (B2/B3), up to the
    Advanced Evidence price-intelligence block."""
    start = html.index("<h2>Quote & Market Summary</h2>")
    end = html.index(PRICE_ADVANCED_SECTION_MARKER)
    return html[start:end]


def _bucket_stats_blocks(section: str) -> list[str]:
    """The statistics <dl> of every price bucket in *section* (render
    order)."""
    return _BUCKET_H3_RE.findall(section)


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
        """A legitimate (count >= 3) exact sample median renders in the
        Advanced Evidence bucket statistics.

        FU1 presentation gate: this test previously used the shared
        count-1 fixture, where the page-global "Median" assertion could
        only pass via the frozen B2/B3 Quote & Market Summary sub-3
        note — proving the wrong region. The original intended contract
        ("a legitimate median is rendered") is now proven with a
        genuine 3-observation bucket, scoped to the Advanced Evidence
        section.
        """
        run = _create_run()
        result = _make_multi_observation_result(
            run,
            (
                (Decimal("100.00"), "USD"),
                (Decimal("109.99"), "USD"),
                (Decimal("119.99"), "USD"),
            ),
        )
        _attach_snapshot(run, result)

        response = self.client.get(_detail_url(run))

        self.assertContains(response, "109.99")
        section = _price_intelligence_advanced_section(response.content.decode())
        stats = _bucket_stats_blocks(section)[0]
        self.assertIn("<dt>Median</dt>", stats)
        # 109.99 is the exact 4A sample median; in the statistics block it
        # appears exactly once (Low=100.00, High=119.99 are the other two).
        self.assertEqual(stats.count("USD 109.99"), 1)
        # count >= 3 preserves the observed market range presentation.
        self.assertIn("<strong>Observed market range:</strong>", section)

    def test_verified_snapshot_count_1_suppresses_median_in_advanced_evidence(self) -> None:
        """FU1 presentation gate: a count-1 bucket publishes NO numeric
        Median row in Advanced Evidence. The domain median is unchanged
        (it equals the sole observation); only its presentation is
        gated. Count / Low / High / Confidence / the truthful
        small-sample notice remain, and the frozen B2/B3 Quote & Market
        Summary keeps its own sub-3 median contract."""
        run = _create_run()
        result = _make_simple_result(run)  # count=1, sole value 109.99 USD
        _attach_snapshot(run, result)

        response = self.client.get(_detail_url(run))
        html = response.content.decode()

        section = _price_intelligence_advanced_section(html)
        stats = _bucket_stats_blocks(section)[0]
        # No Median row in the bucket statistics block...
        self.assertNotIn("<dt>Median</dt>", stats)
        # ...and the sole observation value appears in the statistics
        # block exactly twice (Low and High) — never a third Median entry.
        self.assertEqual(stats.count("USD 109.99"), 2)
        # Observation count / Low / High / Confidence remain rendered.
        for label in (
            "<dt>Observations</dt>",
            "<dd>1</dd>",
            "<dt>Low</dt>",
            "<dt>High</dt>",
            "<dt>Confidence</dt>",
            "<dd>LOW</dd>",
        ):
            self.assertIn(label, stats)
        # The truthful small-sample explanation remains rendered.
        collapsed = " ".join(section.split())
        self.assertIn(
            "Sample size is too small (1 observation) to establish an "
            "observed market range.",
            collapsed,
        )
        self.assertNotIn("<strong>Observed market range:</strong>", section)
        # The frozen B2/B3 Quote & Market Summary still applies its own
        # sub-3 contract (this is the ONLY legitimate "Median" text on
        # the page for a count-1 bucket — distinct from Advanced
        # Evidence).
        summary = _quote_market_summary_section(html)
        self.assertIn(
            "<strong>Median:</strong> Not shown — fewer than 3 comparable "
            "NEW listings.",
            " ".join(summary.split()),
        )

    def test_verified_snapshot_count_2_suppresses_median_in_advanced_evidence(self) -> None:
        """FU1 presentation gate: a count-2 bucket publishes NO numeric
        Median row in Advanced Evidence. The exact 4A midpoint (102.50)
        is neither Low (100.00) nor High (105.00), so it must not appear
        anywhere in the section — the number itself is suppressed, not
        merely a label."""
        run = _create_run()
        result = _make_multi_observation_result(
            run,
            ((Decimal("100.00"), "USD"), (Decimal("105.00"), "USD")),
        )
        _attach_snapshot(run, result)

        response = self.client.get(_detail_url(run))
        html = response.content.decode()

        section = _price_intelligence_advanced_section(html)
        stats = _bucket_stats_blocks(section)[0]
        self.assertNotIn("<dt>Median</dt>", stats)
        # The domain median (exact midpoint 102.50) is not published
        # anywhere in the Advanced Evidence section.
        self.assertNotIn("102.50", section)
        # Low / High / count / confidence remain rendered.
        for label in (
            "<dt>Observations</dt>",
            "<dd>2</dd>",
            "USD 100.00",
            "USD 105.00",
            "<dt>Confidence</dt>",
            "<dd>LOW</dd>",
        ):
            self.assertIn(label, stats)
        collapsed = " ".join(section.split())
        self.assertIn(
            "Sample size is too small (2 observations) to establish an "
            "observed market range.",
            collapsed,
        )
        self.assertNotIn("<strong>Observed market range:</strong>", section)

    def test_ambiguous_snapshot_count_1_buckets_suppress_median_in_advanced_evidence(self) -> None:
        """FU1 presentation gate applies to EVERY Advanced Evidence
        price-bucket presentation: the AMBIGUOUS branch (two non-
        comparable sub-3 buckets) publishes no numeric Median row in
        either bucket statistics block."""
        run = _create_run()
        result = _make_multi_observation_result(
            run,
            ((Decimal("100.00"), "USD"), (Decimal("1500.00"), "EUR")),
        )
        _attach_snapshot(run, result)

        response = self.client.get(_detail_url(run))
        html = response.content.decode()

        section = _price_intelligence_advanced_section(html)
        self.assertContains(response, "AMBIGUOUS")
        stats_blocks = _bucket_stats_blocks(section)
        self.assertEqual(len(stats_blocks), 2)
        for stats in stats_blocks:
            self.assertNotIn("<dt>Median</dt>", stats)
        collapsed = " ".join(section.split())
        self.assertEqual(collapsed.count("Sample size is too small (1 observation)"), 2)
        self.assertNotIn("<strong>Observed market range:</strong>", section)

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
        # No aggregate price values are rendered when decoding fails
        html = response.content.decode()
        # Assert that Median field is not rendered as price-result content
        # (not as metadata, which may appear in debug info)
        # The median is only shown in the context of a bucket, not as raw text
        self.assertNotRegex(html.lower(), r"median.*\$?")
        # No bucket-level price content is shown
        self.assertNotRegex(html.lower(), r"\$\d+(\.\d+)?")


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
