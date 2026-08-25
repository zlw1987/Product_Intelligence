"""Regression tests for exact structural duplicate ListingObservation deduplication.

PRODUCT-INTEL.4C-B-FU corrective follow-up.

Real UAT defect: A real page may publish the exact same Product/Offer node
multiple times in its structured data (HTML/structured-data duplication).
This is HTML duplication, NOT multiple independent market observations.

Before fix: Exact duplicate ListingObservation objects passed through
normalize->match->aggregate producing duplicate ListingIdentityAssessment
values, causing 4A's _refuse_duplicate_assessments() to raise ValueError:
"one or more assessments are exact duplicates of a previously supplied
assessment (by value); the same assessment must not be counted twice"

After fix: Exact structural duplicates are deduplicated BEFORE
normalization/matching, so only one copy propagates forward.
"""

from datetime import datetime, timezone
from typing import TYPE_CHECKING
from unittest.mock import MagicMock

import pytest

from product_intelligence.domain.enums import ResearchRunState
from product_intelligence.execution import execute_research_run
from product_intelligence.providers.page import FetchedPage
from product_intelligence.providers.search import SearchProvider, SearchQuery
from product_intelligence.runs.models import PriceIntelligenceSnapshot, ResearchRun

if TYPE_CHECKING:
    pass


# ---------------------------------------------------------------------------
# Helper to build a mock search response with one result
# ---------------------------------------------------------------------------

def _make_search_response(url: str) -> MagicMock:
    result = MagicMock()
    result.source_url = url
    result.title = "Samsung SSD PM9A3"
    result.snippet = "960GB M.2 NVMe"
    result.price_hint_text = None
    result.part_number_hint = None
    result.raw_reference = None

    response = MagicMock()
    response.provider_id = "test"
    response.query = MagicMock(spec=SearchQuery)
    response.retrieved_at = datetime.now(tz=timezone.utc)
    response.results = (result,)
    response.raw_response_reference = None
    return response


def _make_provider(response: MagicMock) -> MagicMock:
    provider = MagicMock(spec=SearchProvider)
    provider.search.return_value = response
    return provider


def _make_fetched_page(url: str, html: str) -> FetchedPage:
    return FetchedPage(
        requested_url=url,
        final_url=url,
        retrieved_at=datetime.now(tz=timezone.utc),
        status_code=200,
        body_text=html,
        content_type="text/html",
        body_byte_count=len(html),
        redirect_count=0,
        fetcher_id="test",
    )


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

class TestExactStructuralDuplicateDeduplication:
    """Regression tests for exact structural duplicate ListingObservation deduplication."""

    def test_exact_duplicate_observations_do_not_catastrophically_fail_aggregation(
        self,
        research_run: ResearchRun,
    ) -> None:
        """Regression: five identical observations must not cause AGGREGATE FAILED.

        Before fix: Five identical ListingObservation objects from one page would
        pass through normalize->match->aggregate, producing five identical
        ListingIdentityAssessment values. 4A's _refuse_duplicate_assessments()
        correctly raises ValueError, causing AGGREGATE FAILED.

        After fix: Only one copy of each unique observation propagates forward,
        so aggregation succeeds and run reaches COMPLETED.
        """
        url = "https://example.com/product"

        # Build HTML that produces 5 identical JSON-LD Product/Offer nodes
        # Use MPN matching the research_run fixture (MZ-QL23T800)
        # Include itemCondition so condition normalizes to NEW, not UNKNOWN
        five_identical_html = """<!DOCTYPE html><html><head>
        <script type="application/ld+json">
        [
          {"@type":"Product","name":"Samsung SSD PM9A3 960GB","mpn":"MZ-QL23T800","offers":{"@type":"Offer","price":"1055.85","priceCurrency":"USD","itemCondition":"https://schema.org/NewCondition"}},
          {"@type":"Product","name":"Samsung SSD PM9A3 960GB","mpn":"MZ-QL23T800","offers":{"@type":"Offer","price":"1055.85","priceCurrency":"USD","itemCondition":"https://schema.org/NewCondition"}},
          {"@type":"Product","name":"Samsung SSD PM9A3 960GB","mpn":"MZ-QL23T800","offers":{"@type":"Offer","price":"1055.85","priceCurrency":"USD","itemCondition":"https://schema.org/NewCondition"}},
          {"@type":"Product","name":"Samsung SSD PM9A3 960GB","mpn":"MZ-QL23T800","offers":{"@type":"Offer","price":"1055.85","priceCurrency":"USD","itemCondition":"https://schema.org/NewCondition"}},
          {"@type":"Product","name":"Samsung SSD PM9A3 960GB","mpn":"MZ-QL23T800","offers":{"@type":"Offer","price":"1055.85","priceCurrency":"USD","itemCondition":"https://schema.org/NewCondition"}}
        ]
        </script></head><body></body></html>"""

        response = _make_search_response(url)
        provider = _make_provider(response)
        page_fetcher = MagicMock()
        page_fetcher.fetch.return_value = _make_fetched_page(url, five_identical_html)

        # Execute - before fix this raises ExecutionError(Aggregation failed)
        result = execute_research_run(
            str(research_run.id),
            search_provider=provider,
            page_fetcher=page_fetcher,
        )

        # Run completes successfully (not FAILED)
        assert result.run.current_state == ResearchRunState.COMPLETED

        # Snapshot exists
        assert result.snapshot is not None
        assert PriceIntelligenceSnapshot.objects.filter(run=result.run).exists()

        # extract_observation_count reflects deduplicated count (1, not 5)
        assert result.extract_observation_count == 1

        # Verification status is VERIFIED (one accepted price)
        assert result.verification_status.value == "VERIFIED"

    def test_distinct_same_page_observations_are_not_collapsed(
        self,
        research_run: ResearchRun,
    ) -> None:
        """Adversarial: two distinct observations from same page must both survive.

        Exact-value dedup must NOT collapse genuinely different observations
        merely because they came from the same page/source_url.
        """
        url = "https://example.com/product"

        # Build HTML that returns two distinct observations (different titles)
        distinct_html = """<!DOCTYPE html><html><head>
        <script type="application/ld+json">
        [
          {"@type":"Product","name":"Samsung SSD PM9A3 960GB M.2 NVMe","mpn":"MZ-QL23T800","offers":{"@type":"Offer","price":"1055.85","priceCurrency":"USD","itemCondition":"https://schema.org/NewCondition"}},
          {"@type":"Product","name":"Samsung SSD PM9A3 960GB M.2 NVMe Gen4","mpn":"MZ-QL23T800","offers":{"@type":"Offer","price":"1055.85","priceCurrency":"USD","itemCondition":"https://schema.org/NewCondition"}}
        ]
        </script></head><body></body></html>"""

        response = _make_search_response(url)
        provider = _make_provider(response)
        page_fetcher = MagicMock()
        page_fetcher.fetch.return_value = _make_fetched_page(url, distinct_html)

        result = execute_research_run(
            str(research_run.id),
            search_provider=provider,
            page_fetcher=page_fetcher,
        )

        # Both distinct observations survive (2, not 1)
        assert result.extract_observation_count == 2
        assert result.run.current_state == ResearchRunState.COMPLETED

    def test_same_page_different_prices_both_survive(
        self,
        research_run: ResearchRun,
    ) -> None:
        """Two observations same page/diff price must both reach aggregation."""
        url = "https://example.com/product"

        # Two identical offers EXCEPT for price
        diff_price_html = """<!DOCTYPE html><html><head>
        <script type="application/ld+json">
        [
          {"@type":"Product","name":"Samsung SSD","mpn":"MZ-QL23T800","offers":{"@type":"Offer","price":"1055.85","priceCurrency":"USD","itemCondition":"https://schema.org/NewCondition"}},
          {"@type":"Product","name":"Samsung SSD","mpn":"MZ-QL23T800","offers":{"@type":"Offer","price":"1099.99","priceCurrency":"USD","itemCondition":"https://schema.org/NewCondition"}}
        ]
        </script></head><body></body></html>"""

        response = _make_search_response(url)
        provider = _make_provider(response)
        page_fetcher = MagicMock()
        page_fetcher.fetch.return_value = _make_fetched_page(url, diff_price_html)

        result = execute_research_run(
            str(research_run.id),
            search_provider=provider,
            page_fetcher=page_fetcher,
        )

        # Both distinct price observations survive
        assert result.extract_observation_count == 2
        assert result.run.current_state == ResearchRunState.COMPLETED

    def test_three_identical_observations_deduplicate_to_one(
        self,
        research_run: ResearchRun,
    ) -> None:
        """Three identical JSON-LD nodes produce exactly one unique observation."""
        url = "https://example.com/product"

        # Three identical JSON-LD nodes
        triple_dup_html = """<!DOCTYPE html><html><head>
        <script type="application/ld+json">
        [
          {"@type":"Product","name":"Samsung SSD","mpn":"MZ-QL23T800","offers":{"@type":"Offer","price":"1055.85","priceCurrency":"USD","itemCondition":"https://schema.org/NewCondition"}},
          {"@type":"Product","name":"Samsung SSD","mpn":"MZ-QL23T800","offers":{"@type":"Offer","price":"1055.85","priceCurrency":"USD","itemCondition":"https://schema.org/NewCondition"}},
          {"@type":"Product","name":"Samsung SSD","mpn":"MZ-QL23T800","offers":{"@type":"Offer","price":"1055.85","priceCurrency":"USD","itemCondition":"https://schema.org/NewCondition"}}
        ]
        </script></head><body></body></html>"""

        response = _make_search_response(url)
        provider = _make_provider(response)
        page_fetcher = MagicMock()
        page_fetcher.fetch.return_value = _make_fetched_page(url, triple_dup_html)

        result = execute_research_run(
            str(research_run.id),
            search_provider=provider,
            page_fetcher=page_fetcher,
        )

        # After dedup at observation level, only 1 unique observation
        assert result.extract_observation_count == 1
        assert result.run.current_state == ResearchRunState.COMPLETED