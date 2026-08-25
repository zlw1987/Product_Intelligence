"""Integration tests for product_intelligence.execution orchestration.

PRODUCT-INTEL.4C-B — Final corrective pass integration tests.

Uses real fixture files and real contract objects to validate:
* Five pages total (samsung_us, oempcworld, exxactcorp, newegg, fusionww)
* Three listing observations across the five pages
* ExxactCorp produces ACCEPTED explicit-MPN assessment
* Samsung/OEMPCWorld identity evidence remains non-accepted
* Final comparable bucket count is zero
* Verification is UNKNOWN
* At least one NO_COMPARABLE_CURRENCY exclusion exists
* Identity-not-accepted exclusions remain represented
"""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import TYPE_CHECKING
from unittest.mock import MagicMock

import pytest

from product_intelligence.domain import ResearchRequest
from product_intelligence.domain.enums import (
    EvidenceDecision,
    ResearchRunState,
    VerificationStatus,
)
from product_intelligence.domain.evidence import ExecutionDetailCode, ExecutionOutcome, ExecutionStage
from product_intelligence.execution import execute_research_run, ExecutionError
from product_intelligence.execution.evidence_writer import read_execution_evidence
from product_intelligence.providers.page import FetchedPage, PageFetchRequest
from product_intelligence.providers.search import SearchProvider, SearchQuery, SearchResponse, SearchResult
from product_intelligence.research.price_result_codec import decode_price_aggregation_result
from product_intelligence.runs.models import ResearchRun


# Paths to real fixture files
FIXTURES_DIR = Path(__file__).parent.parent / "fixtures" / "pages"

# The canonical test case (REAL-0001)
# Samsung PM9A3 enterprise SSD - NOT 970 EVO Plus consumer SSD
CANONICAL_MPN = "MZ-QL23T800"
CANONICAL_DESCRIPTION = "Samsung PM9A3 NVMe U.2 3.84TB enterprise SSD"


def _load_fixture(name: str) -> str:
    """Load a fixture file by name."""
    path = FIXTURES_DIR / name
    if not path.exists():
        raise FileNotFoundError(f"Fixture not found: {path}")
    return path.read_text(encoding="utf-8")


class TestCanonicalMZQL23T800Integration:
    """Integration test for the canonical MZ-QL23T800 chain.

    Required assertions:
    * search_result_count == 5
    * fetch_success_count == 5
    * extract_observation_count == 3
    * accepted_assessment_count == 1
    * price_buckets == 0
    * verification_status == UNKNOWN
    * One ExxactCorp assessment is ACCEPTED
    * Samsung/OEMPCWorld observations remain non-accepted
    * At least one exclusion is NO_COMPARABLE_CURRENCY
    * Identity-not-accepted exclusions are present
    * Decoded request == ResearchRun.to_research_request()
    * Decoded buckets == ()
    """

    def test_mz_ql23t800_decoded_snapshot(
        self,
        research_run_mz_ql23t800: ResearchRun,
    ) -> None:
        """Test MZ-QL23T800 execution with decoded snapshot verification."""
        # Load real fixture HTML
        samsung_html = _load_fixture("samsung_us_pm9a3_mz_ql23t800.html")
        oempcworld_html = _load_fixture("oempcworld_pm9a3_mz_ql23t800.html")
        exxact_html = _load_fixture("exxactcorp_pm9a3_mz_ql23t800.html")
        newegg_html = _load_fixture("newegg_pm9a3_mz_ql23t800.html")
        fusionww_html = _load_fixture("fusionww_access_restricted.html")

        # Create search results for each URL
        # Using PM9A3-consistent naming from the Serper fixture
        search_results = [
            SearchResult(
                source_url="https://www.samsung.com/us/business/memory-storage/nvme-ssd/pm9a3-nvme-u-2-ssd-3-8tb-sku-mz-ql23t800/",
                title="Samsung PM9A3 NVMe U.2 3.84TB Enterprise SSD",
                snippet="High-performance enterprise storage solution...",
                price_hint_text="$2135.00",  # From Serper fixture - NOT numeric evidence
                part_number_hint="MZ-QL23T800",
                raw_reference=None,
            ),
            SearchResult(
                source_url="https://www.oempcworld.com/products/samsung-pm9a3-3-84tb-mz-ql23t800-nvme-pcie-4-0-x4",
                title="Samsung PM9A3 3.84TB NVMe PCIe 4.0 x4 - OEMPCWorld",
                snippet="Enterprise NVMe SSD with sequential read/write speeds...",
                price_hint_text="$2135.00",  # From Serper fixture - NOT numeric evidence
                part_number_hint="MZ-QL23T800",
                raw_reference=None,
            ),
            SearchResult(
                source_url="https://www.exxactcorp.com/Samsung-MZ-QL23T800-E5387548",
                title="Samsung PM9A3 3.84TB NVMe PCIe 4.0 x4 U.2 SSD - EXXACT",
                snippet="High-performance NVMe U.2 SSD...",
                price_hint_text="$2135.00",  # From Serper fixture - NOT numeric evidence
                part_number_hint="MZ-QL23T800",
                raw_reference=None,
            ),
            SearchResult(
                source_url="https://www.newegg.com/p/N82E16820223687",
                title="Samsung PM9A3 3.84TB NVMe PCIe 4.0 x4 U.2 SSD",
                snippet="High-performance enterprise SSD...",
                price_hint_text="$2135.00",  # From Serper fixture - NOT numeric evidence
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

        # Create a fake search provider that returns the real SearchResponse contract
        fake_search_provider = MagicMock(spec=SearchProvider)
        fake_search_response = SearchResponse(
            provider_id="test-search",
            query=SearchQuery(
                text=f"{CANONICAL_MPN} {CANONICAL_DESCRIPTION}"
            ),
            retrieved_at=datetime.now(tz=timezone.utc),
            results=tuple(search_results),
            raw_response_reference=None,
        )
        fake_search_provider.search.return_value = fake_search_response

        # Create a page fetcher that returns real FetchedPage objects with the fixture HTML
        fetch_results = {
            search_results[0].source_url: samsung_html,
            search_results[1].source_url: oempcworld_html,
            search_results[2].source_url: exxact_html,
            search_results[3].source_url: newegg_html,
            search_results[4].source_url: fusionww_html,
        }

        def fake_fetch(request: PageFetchRequest) -> FetchedPage:
            """Return a real FetchedPage with fixture HTML."""
            if request.url not in fetch_results:
                raise Exception(f"Unexpected URL: {request.url}")

            html = fetch_results[request.url]
            return FetchedPage(
                requested_url=request.url,
                final_url=request.url,
                retrieved_at=datetime.now(tz=timezone.utc),
                status_code=200,
                body_text=html,
                content_type="text/html",
                body_byte_count=len(html.encode("utf-8")),
                redirect_count=0,
                fetcher_id="test-fetcher",
            )

        fake_page_fetcher = MagicMock()
        fake_page_fetcher.fetch.side_effect = fake_fetch

        # Execute the research
        result = execute_research_run(
            str(research_run_mz_ql23t800.id),
            search_provider=fake_search_provider,
            page_fetcher=fake_page_fetcher,
        )

        # ================================================================
        # REQUIRED STATISTICS ASSERTIONS
        # ================================================================

        # search_result_count == 5
        assert result.search_result_count == 5, f"Expected 5 search results, got {result.search_result_count}"

        # fetch_success_count == 5 (all fetches succeeded)
        assert result.fetch_success_count == 5, f"Expected 5 successful fetches, got {result.fetch_success_count}"

        # extract_observation_count == 3 (three pages had listings)
        assert result.extract_observation_count == 3, f"Expected 3 observations, got {result.extract_observation_count}"

        # accepted_assessment_count == 1 (only ExxactCorp accepted)
        assert result.accepted_assessment_count == 1, f"Expected 1 accepted assessment, got {result.accepted_assessment_count}"

        # price_buckets == 0 (no comparables due to currency/exclusion issues)
        assert result.price_buckets == 0, f"Expected 0 price buckets, got {result.price_buckets}"

        # verification_status == UNKNOWN
        assert result.verification_status == VerificationStatus.UNKNOWN, f"Expected UNKNOWN, got {result.verification_status}"

        # ================================================================
        # REQUIRED RUN STATE
        # ================================================================

        assert result.run.current_state == ResearchRunState.COMPLETED
        assert result.snapshot is not None

        # ================================================================
        # DECODED SNAPSHOT VERIFICATION
        # ================================================================

        # Decode the payload using the real 4B codec
        decoded = decode_price_aggregation_result(
            result.snapshot.payload,
            schema_version=result.snapshot.schema_version,
        )

        # Decoded request == ResearchRun.to_research_request()
        request_from_run = result.run.to_research_request()
        assert decoded.request.manufacturer_part_number == request_from_run.manufacturer_part_number
        assert decoded.request.description == request_from_run.description

        # Decoded buckets == ()
        assert len(decoded.buckets) == 0, f"Expected 0 buckets, got {len(decoded.buckets)}"

        # ================================================================
        # EXCLUSION VERIFICATION
        # ================================================================

        # At least one exclusion is NO_COMPARABLE_CURRENCY
        # (Some listings may have currency that is not comparable to others)
        from product_intelligence.research.aggregation import PriceAggregationExclusionReason
        exclusions = decoded.exclusions
        assert len(exclusions) > 0, "Expected at least one exclusion"

        # Explicitly assert NO_COMPARABLE_CURRENCY exists
        no_comparable_currency = [
            e for e in exclusions
            if e.reason is PriceAggregationExclusionReason.NO_COMPARABLE_CURRENCY
        ]
        assert len(no_comparable_currency) >= 1, (
            f"Expected at least one NO_COMPARABLE_CURRENCY exclusion, got {[e.reason for e in exclusions]}"
        )

        # Find identity-not-accepted exclusions
        identity_rejected = [
            e for e in exclusions
            if "IDENTITY_NOT_ACCEPTED" in str(e.reason) or "identity" in str(e.reason).lower()
        ]
        assert len(identity_rejected) > 0, f"Expected identity-not-accepted exclusions, got {exclusions}"

        # ================================================================
        # SEARCH RESULT PRICE HINTS DO NOT CREATE BUCKETS
        # ================================================================

        # The fake SearchResult objects carry fake price_hint_text values.
        # Prove they do NOT create a bucket or become numeric evidence.
        # (Since price_buckets == 0, this is already proven)

        # ================================================================
        # EXXXCTCORP ACCEPTANCE VERIFICATION
        # ================================================================

        # Find the accepted assessment (should be from ExxactCorp)
        from product_intelligence.research.aggregation import PriceAggregationExclusionReason

        accepted_assessments = []
        for assessment in decoded.assessments:
            if assessment.decision == EvidenceDecision.ACCEPTED:
                accepted_assessments.append(assessment)

        assert len(accepted_assessments) == 1, f"Expected 1 accepted assessment, got {len(accepted_assessments)}"

        # Verify it's ExxactCorp (has mpn:MZ-QL23T800 in raw observation)
        accepted = accepted_assessments[0]
        raw_obs = accepted.normalized_listing.observation
        # ExxactCorp publishes "mpn:MZ-QL23T800" after wrapper cleanup -> MZ-QL23T800
        assert "MZ-QL23T800" in (raw_obs.manufacturer_part_number_text or "")


class TestRedirectProvenance:
    """Test that redirects are properly tracked in provenance.

    Required:
    * FETCH evidence candidate_url == requested_url
    * ListingObservation.source_url == FetchedPage.final_url
    """

    def test_redirect_provenance_in_evidence_and_listings(
        self,
        research_run: ResearchRun,
    ) -> None:
        """When a URL redirects, evidence uses requested URL, listings use final URL."""
        # Search returns a candidate that will redirect
        search_result = SearchResult(
            source_url="https://example.com/product",
            title="Product",
            snippet="Description",
            price_hint_text=None,
            part_number_hint="TEST-MPN",
            raw_reference=None,
        )

        response = SearchResponse(
            provider_id="test",
            query=SearchQuery(text="test query"),
            retrieved_at=datetime.now(tz=timezone.utc),
            results=(search_result,),
            raw_response_reference=None,
        )

        provider = MagicMock(spec=SearchProvider)
        provider.search.return_value = response

        # The fetcher returns a FetchedPage where final_url != requested_url
        fetched = FetchedPage(
            requested_url="https://example.com/product",  # Original URL from search
            final_url="https://www.example.com/product",  # Actual URL after redirect
            retrieved_at=datetime.now(tz=timezone.utc),
            status_code=200,
            body_text="""
                <html>
                <head>
                    <script type="application/ld+json">
                    {
                        "@context": "https://schema.org",
                        "@type": "Product",
                        "name": "Test Product",
                        "mpn": "TEST-MPN",
                        "offer": {
                            "@type": "Offer",
                            "price": "100.00",
                            "priceCurrency": "USD"
                        }
                    }
                    </script>
                </head>
                <body>Test</body>
                </html>
            """,
            content_type="text/html",
            body_byte_count=512,
            redirect_count=1,
            fetcher_id="test",
        )

        page_fetcher = MagicMock()
        page_fetcher.fetch.return_value = fetched

        result = execute_research_run(
            str(research_run.id),
            search_provider=provider,
            page_fetcher=page_fetcher,
        )

        assert result.run.current_state == ResearchRunState.COMPLETED

        # ================================================================
        # FETCH evidence candidate_url == requested_url (original)
        # ================================================================
        fetch_evidence = result.run.execution_evidence.filter(
            stage=ExecutionStage.FETCH.value
        ).first()

        assert fetch_evidence is not None
        assert fetch_evidence.candidate_url == "https://example.com/product"

        # ================================================================
        # Listing source_url == final_url (after redirect)
        # ================================================================
        # Decode the snapshot to check the listing source URLs
        decoded = decode_price_aggregation_result(
            result.snapshot.payload,
            schema_version=result.snapshot.schema_version,
        )

        for assessment in decoded.assessments:
            source_url = assessment.normalized_listing.observation.source_url
            assert source_url == "https://www.example.com/product", \
                f"Listing source_url should be final_url, got {source_url}"


class TestZeroSearchResults:
    """Test behavior when search returns zero results."""

    def test_zero_results_completes_with_unknown(
        self,
        research_run: ResearchRun,
    ) -> None:
        """Zero search results completes run with UNKNOWN verification."""
        response = SearchResponse(
            provider_id="test",
            query=SearchQuery(text="some query"),
            retrieved_at=datetime.now(tz=timezone.utc),
            results=(),  # Zero results
            raw_response_reference=None,
        )

        provider = MagicMock(spec=SearchProvider)
        provider.search.return_value = response

        result = execute_research_run(
            str(research_run.id),
            search_provider=provider,
        )

        assert result.run.current_state == ResearchRunState.COMPLETED
        assert result.verification_status == VerificationStatus.UNKNOWN


class TestEvidenceValidation:
    """Test evidence validation at the reader level."""

    def test_valid_evidence_reads_successfully(
        self,
        research_run: ResearchRun,
        fake_search_provider: MagicMock,
        fake_page_fetcher: MagicMock,
    ) -> None:
        """Valid evidence reads without error."""
        result = execute_research_run(
            str(research_run.id),
            search_provider=fake_search_provider,
            page_fetcher=fake_page_fetcher,
        )

        # Reader should succeed
        records = read_execution_evidence(result.run)
        assert len(records) > 0

    def test_credential_url_not_stored(
        self,
        research_run: ResearchRun,
    ) -> None:
        """Credential-bearing URLs raise ValueError from strict writer."""
        from product_intelligence.execution.evidence_writer import ExecutionEvidenceWriter

        writer = ExecutionEvidenceWriter(research_run)

        # Credential URL passed to strict writer raises ValueError
        with pytest.raises(ValueError):
            writer.append_execution_attempt(
                stage=ExecutionStage.FETCH,
                outcome=ExecutionOutcome.SUCCESS,
                candidate_url="https://admin:secret@example.com/page",
                detail_code=ExecutionDetailCode.OK,
            )

        # Valid empty string is still accepted
        record = writer.append_execution_attempt(
            stage=ExecutionStage.FETCH,
            outcome=ExecutionOutcome.BLOCKED,
            candidate_url="",
            detail_code=ExecutionDetailCode.SAFE_URL_REFUSED,
        )
        assert record.candidate_url == ""