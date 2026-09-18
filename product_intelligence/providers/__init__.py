"""External provider boundaries.

Three boundaries are planned:

    SearchProvider  -- finds candidate listings and pages
    PageFetcher     -- retrieves one document from one URL
    LLMProvider     -- semantic assistance only (see the deterministic /
                       LLM split in docs/PRODUCT_INTELLIGENCE_PLAN.md)

Four boundaries exist:

    CommercialSourceProvider -- structured commercial observations from
                                internal vendor API (4D-B)

Rules that hold from this phase onward:

* Business logic depends on the boundary, never on a specific vendor.
* Vendor names, request/response shapes, and credentials stay behind an
  adapter in this package and never reach the domain or the research core.
* Credentials are read from the server environment. No calling system ever
  supplies or holds them.
* Provider-native payload material is preserved as an opaque reference. It is
  never handed to business logic as a structure to read.
* A provider observes; it never decides identity, price, or acceptance.

A ``SearchResult``, a ``FetchedPage``, a listing observation, and a
commercial-source candidate are four different things and are never collapsed.

Status: PRODUCT-INTEL.2B implemented the search boundary in ``search`` —
``SearchQuery``, ``SearchResult``, ``SearchResponse``, the ``SearchProvider``
protocol, and one boundary exception. 2C added the first real search adapter
behind it. 3A added the page-fetch boundary in ``page`` —
``PageFetchRequest``, ``FetchedPage``, the ``PageFetcher`` protocol, and its
two exceptions — together with one concrete standard-library fetcher in
``http_page``: bounded, credential-free, GET-only, and refusing non-public
destinations on every redirect hop. 6D added the document/PDF boundary in
``document`` and its concrete fetcher in ``http_pdf``. 4D-A added the
direct-source boundary in ``direct_source`` with the DirectMacro locator in
``directmacro``. 4D-B added the commercial-source boundary in ``commercial``
with the internal vendor adapter in ``internal_vendor``.

**Current calling topology:** ``runs/`` and ``web/`` import no part of this
package. The execution layer (``execution/orchestration.py``) calls the search
boundary (SearchProvider), page-fetch boundary (PageFetcher), and commercial
source provider (CommercialSourceProvider) during research execution. The
direct-source boundary (``direct_source``) is called by the orchestrator for
preferred-source acquisition. The LLM boundary is not yet implemented as a
generic ``LLMProvider`` protocol; the existing FU3A/FU3B semantic runtime
uses its own transport module.
"""

from product_intelligence.providers.direct_source import (
    DirectSourceLocator,
    DirectSourceQuery,
    DirectSourceTarget,
)
from product_intelligence.providers.document import (
    DocumentFetchError,
    DocumentFetchRequest,
    DocumentFetcher,
    FetchedDocument,
)
from product_intelligence.providers.page import (
    ALLOWED_FETCH_SCHEMES,
    FetchedPage,
    PageFetcher,
    PageFetchError,
    PageFetchRequest,
    UnsafeFetchTargetError,
)
from product_intelligence.providers.search import (
    ALLOWED_URL_SCHEMES,
    SearchProvider,
    SearchProviderError,
    SearchQuery,
    SearchResponse,
    SearchResult,
)
from product_intelligence.providers.commercial import (
    CommercialAvailability,
    CommercialLookupQuery,
    CommercialNoteKind,
    CommercialPriceBasis,
    CommercialSourceCandidate,
    CommercialSourceIssue,
    CommercialSourceProvider,
    CommercialSourceResponse,
    LookupStatus,
    SourceOutcome,
)

__all__ = [
    "ALLOWED_FETCH_SCHEMES",
    "ALLOWED_URL_SCHEMES",
    "CommercialAvailability",
    "CommercialLookupQuery",
    "CommercialNoteKind",
    "CommercialPriceBasis",
    "CommercialSourceCandidate",
    "CommercialSourceIssue",
    "CommercialSourceProvider",
    "CommercialSourceResponse",
    "DocumentFetchError",
    "DocumentFetchRequest",
    "DocumentFetcher",
    "DirectSourceLocator",
    "DirectSourceQuery",
    "DirectSourceTarget",
    "FetchedDocument",
    "FetchedPage",
    "LookupStatus",
    "PageFetchError",
    "PageFetchRequest",
    "PageFetcher",
    "SearchProvider",
    "SearchProviderError",
    "SearchQuery",
    "SearchResponse",
    "SearchResult",
    "SourceOutcome",
    "UnsafeFetchTargetError",
]
