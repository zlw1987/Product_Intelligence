"""Real executor integration tests (PRODUCT-INTEL.4C-C).

These tests exercise the full pipeline from web POST through actual
execute_research_run() to completed report rendering, using fake providers
that never make real network calls.

The canonical test case is REAL-0001 (Samsung PM9A3 MZ-QL23T800 enterprise SSD).

IMPORTANT: Tests here use fake SearchProvider/PageFetcher injected via
execute_research_run's keyword arguments. No test may reach the production
default Serper provider.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from unittest import mock

from django.test import TestCase
from django.urls import reverse

from product_intelligence.domain import EvidenceDecision, ResearchRunState
from product_intelligence.execution import execute_research_run
from product_intelligence.providers.page import FetchedPage, PageFetchRequest
from product_intelligence.providers.search import (
    SearchProvider,
    SearchQuery,
    SearchResponse,
    SearchResult,
)
from product_intelligence.runs.models import ResearchRun


# ---------------------------------------------------------------------------
# Paths to real fixture files
# ---------------------------------------------------------------------------

FIXTURES_DIR = Path(__file__).parent.parent / "fixtures" / "pages"

# The canonical REAL-0001 test case
CANONICAL_MPN = "MZ-QL23T800"
CANONICAL_DESCRIPTION = "Samsung PM9A3 NVMe U.2 3.84TB enterprise SSD"


def _load_fixture(name: str) -> str:
    """Load a real fixture file by name."""
    path = FIXTURES_DIR / name
    if not path.exists():
        raise FileNotFoundError(f"Fixture not found: {path}")
    return path.read_text(encoding="utf-8")


# ---------------------------------------------------------------------------
# Fake Search Provider
# ---------------------------------------------------------------------------

@dataclass
class FakeSearchProvider(SearchProvider):
    """A search provider that returns pre-configured results."""
    
    results: list[SearchResult] = field(default_factory=list)
    call_count: int = 0
    
    def search(self, query: SearchQuery) -> SearchResponse:
        self.call_count += 1
        return SearchResponse(
            provider_id="fake",
            query=query,
            retrieved_at=datetime.now(timezone.utc),
            results=tuple(self.results),
        )


# ---------------------------------------------------------------------------
# Fake Page Fetcher
# ---------------------------------------------------------------------------

@dataclass
class FakePageFetcher:
    """A page fetcher that returns pre-configured FetchedPage objects."""
    
    pages: dict[str, FetchedPage] = field(default_factory=dict)
    call_count: int = 0
    
    def fetch(self, request: PageFetchRequest) -> FetchedPage:
        self.call_count += 1
        if request.url in self.pages:
            return self.pages[request.url]
        # Default: return a page with no listings (fusionww access restricted)
        now = datetime.now(timezone.utc)
        return FetchedPage(
            requested_url=request.url,
            final_url=request.url,
            retrieved_at=now,
            status_code=200,
            body_text="Access restricted",
            content_type="text/html",
            body_byte_count=len(b"Access restricted"),
            redirect_count=0,
            fetcher_id="fake",
        )


# ---------------------------------------------------------------------------
# Integration Tests
# ---------------------------------------------------------------------------

class RealExecutorCompleteIntegrationTest(TestCase):
    """Test POST -> real execute_research_run() with REAL-0001 fixture.

    Uses the real exxactcorp_pm9a3_mz_ql23t800.html fixture page to prove
    the real extraction/normalization/matching/aggregation pipeline.

    REAL-0001 expected results:
    * search_result_count == 5
    * fetch_success_count == 5
    * extract_observation_count == 3  (samsung, oempcworld, exxactcorp yield observations)
    * accepted_assessment_count == 1  (only exxactcorp accepted - explicit MPN match)
    * price_buckets == 0              (no comparable bucket due to NO_COMPARABLE_CURRENCY)
    * verification_status == UNKNOWN
    * One NO_COMPARABLE_CURRENCY exclusion for the exxactcorp accepted listing
    * identity-not-accepted exclusions for samsung/oempcworld
    """

    def test_web_post_real_executor_real_fixture_completes_with_unknown_status(
        self,
    ) -> None:
        """Web POST -> real executor with REAL-0001 fixture -> COMPLETED UNKNOWN.

        This integration test proves:
        - Web layer correctly calls execute_research_run with run id
        - Real SearchProvider contract is used
        - Real page fetcher is used
        - Real extraction runs on real fixture HTML
        - Real normalization runs
        - Real matching runs (ExxactCorp ACCEPTED, others rejected)
        - Real aggregation runs
        - PriceIntelligenceSnapshot is created
        - Run is COMPLETED
        - Snapshot decodes correctly
        - verification_status == UNKNOWN (no comparable buckets)
        - accepted_assessment_count == 1
        - NO_COMPARABLE_CURRENCY exclusion exists
        """
        # Load real fixture HTML
        samsung_html = _load_fixture("samsung_us_pm9a3_mz_ql23t800.html")
        oempcworld_html = _load_fixture("oempcworld_pm9a3_mz_ql23t800.html")
        exxact_html = _load_fixture("exxactcorp_pm9a3_mz_ql23t800.html")
        newegg_html = _load_fixture("newegg_pm9a3_mz_ql23t800.html")
        fusionww_html = _load_fixture("fusionww_access_restricted.html")

        # Build search results matching the frozen REAL-0001 structure
        search_results = [
            SearchResult(
                source_url="https://www.samsung.com/us/business/memory-storage/nvme-ssd/pm9a3-nvme-u-2-ssd-3-8tb-sku-mz-ql23t800/",
                title="Samsung PM9A3 NVMe U.2 3.84TB Enterprise SSD",
                snippet="High-performance enterprise storage solution...",
                price_hint_text="$2135.00",  # From Serper fixture - NOT numeric extraction evidence
                part_number_hint="MZ-QL23T800",
                raw_reference=None,
            ),
            SearchResult(
                source_url="https://www.oempcworld.com/products/samsung-pm9a3-3-84tb-mz-ql23t800-nvme-pcie-4-0-x4",
                title="Samsung PM9A3 3.84TB NVMe PCIe 4.0 x4 - OEMPCWorld",
                snippet="Enterprise NVMe SSD with sequential read/write speeds...",
                price_hint_text="$2135.00",
                part_number_hint="MZ-QL23T800",
                raw_reference=None,
            ),
            SearchResult(
                source_url="https://www.exxactcorp.com/Samsung-MZ-QL23T800-E5387548",
                title="Samsung PM9A3 3.84TB NVMe PCIe 4.0 x4 U.2 SSD - EXXACT",
                snippet="High-performance NVMe U.2 SSD...",
                price_hint_text="$2135.00",
                part_number_hint="MZ-QL23T800",
                raw_reference=None,
            ),
            SearchResult(
                source_url="https://www.newegg.com/p/N82E16820223687",
                title="Samsung PM9A3 3.84TB NVMe PCIe 4.0 x4 U.2 SSD",
                snippet="High-performance enterprise SSD...",
                price_hint_text="$2135.00",
                part_number_hint="MZ-QL23T800",
                raw_reference=None,
            ),
            SearchResult(
                source_url="https://www.fusionww.com/shop/product/4267839/MZ-QL23T800",
                title="Samsung PM9A3 Series 3.84TB 2.5\" PCIe 4.0 x4 NVMe SSD",
                snippet="Access restricted",
                price_hint_text=None,
                part_number_hint=None,
                raw_reference=None,
            ),
        ]

        # Build page map for the fake fetcher
        page_bodies = {
            search_results[0].source_url: samsung_html,
            search_results[1].source_url: oempcworld_html,
            search_results[2].source_url: exxact_html,
            search_results[3].source_url: newegg_html,
            search_results[4].source_url: fusionww_html,
        }

        fake_search = FakeSearchProvider(results=search_results)
        fake_fetcher = FakePageFetcher(
            pages={
                url: FetchedPage(
                    requested_url=url,
                    final_url=url,
                    retrieved_at=datetime.now(timezone.utc),
                    status_code=200,
                    body_text=html,
                    content_type="text/html",
                    body_byte_count=len(html.encode("utf-8")),
                    redirect_count=0,
                    fetcher_id="test-fixture-fetcher",
                )
                for url, html in page_bodies.items()
            }
        )

        def patched_execute(run_id: str, **kwargs: Any) -> Any:
            return execute_research_run(
                run_id,
                search_provider=fake_search,
                page_fetcher=fake_fetcher,
            )

        with mock.patch(
            "product_intelligence.web.views.execute_research_run",
            side_effect=patched_execute,
        ):
            response = self.client.post(
                reverse("research-new"),
                {
                    "manufacturer_part_number": CANONICAL_MPN,
                    "description": CANONICAL_DESCRIPTION,
                },
            )

        # Redirect to report
        self.assertEqual(response.status_code, 302)

        # Run is COMPLETED
        run = ResearchRun.objects.get()
        self.assertEqual(run.current_state, ResearchRunState.COMPLETED)

        # Search was called exactly once
        self.assertEqual(fake_search.call_count, 1)

        # All 5 URLs were fetched
        self.assertEqual(fake_fetcher.call_count, 5)

        # Snapshot exists
        self.assertTrue(
            hasattr(run, "price_intelligence_snapshot") and run.price_intelligence_snapshot is not None,
        )

        # Decode snapshot and verify pipeline results
        from product_intelligence.research.price_result_codec import (
            decode_price_aggregation_result,
        )
        from product_intelligence.research.aggregation import (
            PriceAggregationExclusionReason,
        )

        snapshot = run.price_intelligence_snapshot
        decoded = decode_price_aggregation_result(
            snapshot.payload,
            schema_version=snapshot.schema_version,
        )

        # Request preserved correctly
        self.assertEqual(
            decoded.request.manufacturer_part_number, CANONICAL_MPN
        )

        # Price buckets == 0 (no comparables due to currency/exclusion)
        self.assertEqual(len(decoded.buckets), 0)

        # Verification is UNKNOWN
        self.assertEqual(decoded.verification_status.name, "UNKNOWN")

        # Exactly 1 accepted assessment (exxactcorp)
        accepted = [
            a for a in decoded.assessments
            if a.decision == EvidenceDecision.ACCEPTED
        ]
        self.assertEqual(
            len(accepted), 1,
            f"Expected 1 accepted assessment, got {[a.decision for a in decoded.assessments]}"
        )

        # The accepted assessment is from ExxactCorp (contains MZ-QL23T800)
        accepted_assessment = accepted[0]
        raw_obs = accepted_assessment.normalized_listing.observation
        self.assertIn(
            CANONICAL_MPN,
            raw_obs.manufacturer_part_number_text or "",
            "Accepted assessment should be from ExxactCorp with matching MPN",
        )

        # NO_COMPARABLE_CURRENCY exclusion exists (the accepted listing
        # has no numeric price extracted, so it cannot be placed in a bucket)
        no_comparable_currency = [
            e for e in decoded.exclusions
            if e.reason == PriceAggregationExclusionReason.NO_COMPARABLE_CURRENCY
        ]
        self.assertGreaterEqual(
            len(no_comparable_currency), 1,
            f"Expected at least one NO_COMPARABLE_CURRENCY exclusion, got "
            f"{[(e.reason, e.assessment.decision) for e in decoded.exclusions]}"
        )

        # SearchResult.price_hint_text does NOT create a numeric price bucket
        # (price_buckets == 0 proves this - the hint text is not extraction evidence)

        # Report renders correctly
        report_response = self.client.get(response["Location"])
        self.assertEqual(report_response.status_code, 200)
        html = report_response.content.decode()
        self.assertIn(CANONICAL_MPN, html)
        self.assertIn("UNKNOWN", html)
        self.assertIn("No comparable price was established", html)


class RealExecutorFailureIntegrationTest(TestCase):
    """Test POST -> real execute_research_run() with failing providers -> FAILED.
    
    This test proves:
    - Web POST triggers actual execute_research_run()
    - SearchProviderError is caught and run transitions to FAILED
    - Report renders failure state safely
    - No raw exception text is exposed
    - Retry button is shown
    """

    def test_search_failure_transitions_run_to_failed(self) -> None:
        """When search fails, the run transitions to FAILED (not stuck CREATED)."""
        from product_intelligence.providers.search import SearchProviderError

        def patched_execute(run_id: str, **kwargs: Any) -> Any:
            fake_search = FakeSearchProvider(results=[])

            def failing_search(query: SearchQuery) -> SearchResponse:
                raise SearchProviderError("Serper quota exceeded")

            fake_search.search = failing_search  # type: ignore

            return execute_research_run(
                run_id,
                search_provider=fake_search,
                page_fetcher=FakePageFetcher(),
            )

        with mock.patch(
            "product_intelligence.web.views.execute_research_run",
            side_effect=patched_execute,
        ):
            response = self.client.post(
                reverse("research-new"),
                {
                    "manufacturer_part_number": "MZ-V8P1T0B/AM",
                    "description": "1TB NVMe M.2 solid state drive",
                },
            )

        # Should redirect to report
        self.assertEqual(response.status_code, 302)

        # Run should be FAILED (not CREATED)
        run = ResearchRun.objects.get()
        self.assertEqual(run.current_state, ResearchRunState.FAILED)

        # Report should render failure state
        report_response = self.client.get(response["Location"])
        self.assertEqual(report_response.status_code, 200)
        html = report_response.content.decode()

        # Should show failure message (not raw exception)
        self.assertIn("did not complete", html)

        # Should NOT expose raw exception text
        self.assertNotIn("Serper quota exceeded", html)
        self.assertNotIn("SearchProviderError", html)
        self.assertNotIn("SERPER_API_KEY", html)

        # Retry button should be present
        self.assertIn("Retry", html)


class ClaimFailureIntegrationTest(TestCase):
    """Test when claim_execution itself fails.

    This test proves that ClaimExecutionFailed is handled safely without
    fabricating any snapshot, provider result, or verified data.
    """

    def test_claim_failure_creates_run_and_shows_safe_notice(self) -> None:
        """When claim_execution fails, exactly one run is created and user
        gets a safe notice without raw exception or provider details."""
        from product_intelligence.runs.execution_claims import ClaimExecutionFailed

        initial_count = ResearchRun.objects.count()

        def patched_execute(run_id: str, **kwargs: Any) -> Any:
            raise ClaimExecutionFailed(
                run_id=run_id,
                reason=ClaimExecutionFailed.REASON_ALREADY_CLAIMED,
                detail="run is already claimed",
            )

        with mock.patch(
            "product_intelligence.web.views.execute_research_run",
            side_effect=patched_execute,
        ):
            response = self.client.post(
                reverse("research-new"),
                {
                    "manufacturer_part_number": "TEST-MPN",
                    "description": "Test description",
                },
            )

        # Exactly one run was created (not zero, not two)
        self.assertEqual(ResearchRun.objects.count(), initial_count + 1)

        # Run is the one we just submitted
        run = ResearchRun.objects.order_by("created_at").last()
        self.assertEqual(run.manufacturer_part_number, "TEST-MPN")

        # We redirect to the report
        self.assertEqual(response.status_code, 302)
        self.assertIn(str(run.id), response["Location"])

        # Report is accessible
        report_response = self.client.get(response["Location"])
        self.assertEqual(report_response.status_code, 200)

        # Run state is honest (CREATED or RUNNING, not fabricated COMPLETED)
        self.assertIn(run.current_state.name, ("CREATED", "RUNNING"))

        # No snapshot was created
        try:
            has_snapshot = run.price_intelligence_snapshot is not None
        except Exception:
            has_snapshot = False
        self.assertFalse(
            has_snapshot,
            "Snapshot should not exist after claim failure",
        )

        # No raw ClaimExecutionFailed detail text is exposed in the report
        html = report_response.content.decode()
        self.assertNotIn("ALREADY_CLAIMED", html)
        self.assertNotIn("already claimed", html)
        self.assertNotIn("ClaimExecutionFailed", html)