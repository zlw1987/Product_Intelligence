"""Tests for product_intelligence.execution.

PRODUCT-INTEL.4C-B — Complete PRICE MVP Backend Research Execution

This test suite validates the orchestration layer that connects the
deterministic research primitives into a complete end-to-end research pipeline.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import TYPE_CHECKING
from unittest.mock import MagicMock, patch

import pytest
from django.utils import timezone as django_timezone

from product_intelligence.domain import ResearchRequest
from product_intelligence.domain.enums import (
    ConfidenceLevel,
    EvidenceDecision,
    IdentityMatchType,
    ResearchRunState,
    VerificationStatus,
)
from product_intelligence.domain.evidence import ExecutionDetailCode, ExecutionOutcome, ExecutionStage
from product_intelligence.execution import execute_research_run, ExecutionError
from product_intelligence.providers.search import SearchProvider, SearchQuery, SearchResponse
from product_intelligence.research.matching import ListingIdentityAssessment
from product_intelligence.research.normalization import NormalizedCondition, NormalizedListingObservation

from product_intelligence.runs.models import ResearchRun

if TYPE_CHECKING:
    from product_intelligence.providers.page import FetchedPage, PageFetcher
    from product_intelligence.research.listings import ListingObservation

# Constants from integration tests
CANONICAL_MPN = "MZ-QL23T800"
CANONICAL_DESCRIPTION = "Samsung SSD 970 EVO Plus 1TB NVMe PCIe M.2 Internal Solid State Drive"


# ---------------------------------------------------------------------------
# DATABASE ISOLATION FIXTURE
# ---------------------------------------------------------------------------

@pytest.fixture(autouse=True)
def clean_execution_runs() -> None:
    """Clean up ResearchRun rows after each test.

    This fixture ensures test isolation by deleting all ResearchRun records
    after each test. Cascade deletion removes snapshots and evidence.
    The cleanup runs even when a test fails.
    """
    yield
    # Clean up after test
    ResearchRun.objects.all().delete()


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def search_request() -> ResearchRequest:
    """Create a research request for testing."""
    return ResearchRequest(
        manufacturer_part_number="MZ-QL23T800",
        description="Samsung SSD 970 EVO Plus 1TB NVMe PCIe M.2 Internal Solid State Drive",
    )


@pytest.fixture
def search_request_description_only() -> ResearchRequest:
    """Create a research request with only description."""
    return ResearchRequest(
        manufacturer_part_number="",
        description="Samsung SSD 970 EVO Plus 1TB NVMe PCIe M.2 Internal Solid State Drive",
    )


@pytest.fixture
def search_request_mpn_only() -> ResearchRequest:
    """Create a research request with only MPN."""
    return ResearchRequest(
        manufacturer_part_number="MZ-QL23T800",
        description="",
    )


@pytest.fixture
def search_request_mz_ql23t800() -> ResearchRequest:
    """Create a research request for the canonical MZ-QL23T800 test case."""
    return ResearchRequest(
        manufacturer_part_number=CANONICAL_MPN,
        description=CANONICAL_DESCRIPTION,
    )


@pytest.fixture
def research_run_mz_ql23t800(search_request_mz_ql23t800: ResearchRequest) -> ResearchRun:
    """Create a research run for the canonical MZ-QL23T800 test case."""
    return ResearchRun.objects.create_from_request(search_request_mz_ql23t800)


@pytest.fixture
def research_run(search_request: ResearchRequest) -> ResearchRun:
    """Create a research run for testing."""
    return ResearchRun.objects.create_from_request(search_request)


@pytest.fixture
def search_result_mocks() -> list[MagicMock]:
    """Create mock search results."""
    results = []
    for i in range(2):
        result = MagicMock()
        result.source_url = f"https://example{i}.com/product/{i}"
        result.title = f"Product {i}"
        result.snippet = f"Description for product {i}"
        result.price_hint_text = None
        result.part_number_hint = None
        result.raw_reference = None
        results.append(result)
    return results


@pytest.fixture
def search_response_mock(search_result_mocks: list[MagicMock]) -> MagicMock:
    """Create a mock search response."""
    response = MagicMock()
    response.provider_id = "test-provider"
    response.query = MagicMock(spec=SearchQuery)
    response.retrieved_at = datetime.now(tz=timezone.utc)
    response.results = tuple(search_result_mocks)
    response.raw_response_reference = None
    return response


@pytest.fixture
def fake_search_provider(search_response_mock: MagicMock) -> MagicMock:
    """Create a fake search provider."""
    provider = MagicMock(spec=SearchProvider)
    provider.search.return_value = search_response_mock
    return provider


@pytest.fixture
def fake_page_fetcher() -> MagicMock:
    """Create a fake page fetcher with real FetchedPage contract."""
    fetcher = MagicMock()
    # Create a FetchedPage using the real contract
    from product_intelligence.providers.page import FetchedPage
    
    fetched = FetchedPage(
        requested_url="https://example.com",
        final_url="https://example.com",
        retrieved_at=datetime.now(tz=timezone.utc),
        status_code=200,
        body_text="<html><body>Test</body></html>",
        content_type="text/html",
        body_byte_count=31,
        redirect_count=0,
        fetcher_id="test",
    )
    fetcher.fetch.return_value = fetched
    return fetcher