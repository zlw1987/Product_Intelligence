"""External provider boundaries.

Two boundaries are planned:

    SearchProvider  -- finds candidate listings and pages
    LLMProvider     -- semantic assistance only (see the deterministic /
                       LLM split in docs/PRODUCT_INTELLIGENCE_PLAN.md)

Rules that hold from this phase onward:

* Business logic depends on the boundary, never on a specific vendor.
* Vendor names, request/response shapes, and credentials stay behind an
  adapter in this package and never reach the domain or the research core.
* Credentials are read from the server environment. No calling system ever
  supplies or holds them.
* Provider-native payload material is preserved as an opaque reference. It is
  never handed to business logic as a structure to read.
* A provider observes; it never decides identity, price, or acceptance.

Status: PRODUCT-INTEL.2B implemented the search boundary in `search` —
`SearchQuery`, `SearchResult`, `SearchResponse`, the `SearchProvider` protocol,
and one boundary exception. **No provider is integrated**: there is no adapter,
no HTTP call, no credential, and no vendor selection, and nothing in the system
calls `search()`. The first real provider is 2C, and it arrives with sanitized
recorded response fixtures. The LLM boundary is not implemented and is not
scheduled before 6A.
"""

from product_intelligence.providers.search import (
    ALLOWED_URL_SCHEMES,
    SearchProvider,
    SearchProviderError,
    SearchQuery,
    SearchResponse,
    SearchResult,
)

__all__ = [
    "ALLOWED_URL_SCHEMES",
    "SearchProvider",
    "SearchProviderError",
    "SearchQuery",
    "SearchResponse",
    "SearchResult",
]
