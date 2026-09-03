"""Dedicated DB isolation for execution/ tests that use human-review fixtures.

Tests that need DB isolation must explicitly request the
`human_review_db_isolation` fixture.

The fixture is identical in behaviour to the one in tests/runs/conftest.py.
It is defined here separately so that pytest can discover it when running
tests from the execution/ directory.

The original execution test fixtures (clean_execution_runs, search_request,
research_run, fake_search_provider, etc.) are preserved below.
"""
from __future__ import annotations

import pytest


def _is_django_test_case(cls) -> bool:
    """Return True if cls is a Django TestCase or SimpleTestCase."""
    from django.test import SimpleTestCase
    return issubclass(cls, SimpleTestCase)


@pytest.fixture
def human_review_db_isolation(request) -> None:
    """Dedicated DB isolation for HUMAN-REVIEW execution tests.

    Only applies to tests that explicitly request this fixture.
    Cleans up runs/-model data after each test in FK-safe order.

    Tests that inherit from django.test.TestCase or
    django.test.SimpleTestCase are skipped because they provide
    their own transaction rollback or do not allow DB access.
    """
    yield  # Run the test

    test_class = getattr(request.node, "cls", None)
    if test_class is not None and _is_django_test_case(test_class):
        return

    if "no_django_db" in request.fixturenames:
        return

    from django.db import transaction
    from product_intelligence.runs.models import (
        AiAssistedReviewCandidate,
        ExecutionEvidenceRecord,
        PriceIntelligenceSnapshot,
        ResearchRun,
    )
    with transaction.atomic():
        AiAssistedReviewCandidate.objects.all().delete()
        ExecutionEvidenceRecord.objects.all().delete()
        PriceIntelligenceSnapshot.objects.all().delete()
        ResearchRun.objects.all().delete()


# ---------------------------------------------------------------------------
# ORIGINAL EXECUTION TEST FIXTURES
# ---------------------------------------------------------------------------

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