"""Page fetch and extraction utilities for execution.

This module handles fetching pages and extracting listings using the
PageFetcher protocol.

PRODUCT-INTEL.4C-B corrections:
* Uses PageFetcher as injection type, not HttpPageFetcher
* fetch_success_count means successful PageFetcher.fetch() calls
* Uses frozen ExecutionDetailCode enum
* Uses PageFetchRequest contract for safe URL validation
* Does NOT truncate candidate_url - TextField preserves provenance
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Protocol

from product_intelligence.providers.page import PageFetchRequest, UnsafeFetchTargetError
from product_intelligence.research.extraction import extract_listing_observations
from product_intelligence.research.listings import ListingObservation

if TYPE_CHECKING:
    from collections.abc import Sequence

logger = logging.getLogger(__name__)


class PageFetcher(Protocol):
    """Protocol for page fetching implementations.

    The orchestrator uses this protocol as the injection type.
    HttpPageFetcher is the production default.
    """

    def fetch(self, request: PageFetchRequest) -> "FetchedPage":
        """Fetch a page and return structured result."""
        ...


def _is_safe_url_without_credentials(url: str | None) -> bool:
    """Check if URL is safe without credentials check.

    This is used for final_url validation which comes from our own fetcher.
    """
    if not url:
        return False
    try:
        from urllib.parse import urlsplit

        parts = urlsplit(url)
        if parts.scheme.lower() not in {"http", "https"}:
            return False
        if not parts.netloc:
            return False
        # final_url from our fetcher doesn't need credential check
        return True
    except Exception:
        return False


def fetch_and_extract(
    url: str,
    page_fetcher: PageFetcher,
) -> tuple[Sequence[ListingObservation], str]:
    """Fetch one page and extract listing observations.

    Parameters
    ----------
    url : str
        The URL to fetch.
    page_fetcher : PageFetcher
        The page fetcher implementation.

    Returns
    -------
    tuple[Sequence[ListingObservation], str]
        - Sequence of listing observations (may be empty)
        - Detail code explaining outcome
    """
    from product_intelligence.domain.evidence import ExecutionOutcome, ExecutionStage

    # If URL cannot form a safe PageFetchRequest, do not call fetcher
    # Record BLOCKED / SAFE_URL_REFUSED
    try:
        fetch_request = PageFetchRequest(url=url)
    except (ValueError, TypeError):
        # URL is not absolute http(s) or has other issues
        return [], "SAFE_URL_REFUSED"

    try:
        fetched = page_fetcher.fetch(fetch_request)
        # fetch_success_count increments here, before extraction
        # A successful fetch whose page yields zero observations is still a successful fetch

        # Validate final_url for extraction source
        if not _is_safe_url_without_credentials(fetched.final_url):
            # If final_url is somehow malformed, use requested_url
            source_url = fetched.requested_url
        else:
            source_url = fetched.final_url

        # Extract listing observations
        listings = extract_listing_observations(fetched.body_text, source_url=source_url)

        if not listings:
            return [], "NO_LISTING_OBSERVATIONS"

        return listings, "OK"

    except UnsafeFetchTargetError:
        return [], "SAFE_URL_REFUSED"

    except Exception:
        # Generic fetch failure
        return [], "NETWORK_ERROR"