"""The page-fetch boundary (PRODUCT-INTEL.3A).

A second boundary in this package, sitting beside the search boundary and
answering a different question:

```text
SearchQuery       ->  SearchProvider.search(query)  ->  SearchResponse
                                                          |- SearchResult, ...
PageFetchRequest  ->  PageFetcher.fetch(request)    ->  FetchedPage
```

A `SearchResult` is **what a search provider said about a URL**. A
`FetchedPage` is **what that URL actually returned**. They are not the same
observation, and this phase keeps them apart deliberately: a snippet is a third
party's description of a page, and the page is the page. Collapsing them would
let a search summary be reported as page evidence.

Neither of them is a listing. Turning a fetched document into raw listing
fields is deterministic extraction, and it lives in the research core
(`product_intelligence.research.extraction`), which fetches nothing. The two
halves meet only in a caller that holds both — never by one importing the
other.

What this module is *not*
-------------------------

**It is not a fetcher.** Nothing here opens a socket, resolves a host, reads a
credential, or names a vendor. This module is data contracts plus a
`Protocol`; the concrete standard-library implementation lives in
`product_intelligence.providers.http_page`, and a guard test keeps this module
as network-free as the search contracts beside it.

**It is not a crawler.** There is no link traversal, no sitemap, no frontier,
no queue, no politeness scheduler, and no asset fetching. One request names one
document, and one fetch retrieves that document only — not its images,
scripts, stylesheets, fonts, or frames.

**It is not extraction.** A `FetchedPage` carries what was returned. It holds
no title, no price, no part number, no seller, and no judgement about whether
the page describes a product at all.

**It is not a browser.** No JavaScript is executed, no form is submitted, and
no session is maintained. A page whose content exists only after client-side
rendering returns whatever its static document actually contains, which may be
nothing useful — and that outcome is evidence about the source, not a defect to
be routed around by acquiring browser infrastructure.

**It is not persistence.** Nothing here is stored. The run lifecycle imports no
part of this package.

Retrieval is bounded, and the bounds are the implementation's
-------------------------------------------------------------

Timeout, redirect limit, response-size limit, accepted content types, and the
destination-address policy are properties of a concrete fetcher, not of this
contract. They are stated on `HttpPageFetcher`, where they can be read next to
the code that enforces them. What this module fixes is only the shape of the
request and of the answer.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Protocol
from urllib.parse import urlsplit

#: The only schemes a page fetch may target. Identical in spirit to the search
#: boundary's rule, and kept separately rather than shared, because the two
#: boundaries constrain different things: one judges a URL it was *told about*,
#: the other judges a URL it is about to *open*.
ALLOWED_FETCH_SCHEMES: frozenset[str] = frozenset({"http", "https"})


class PageFetchError(Exception):
    """A page could not be retrieved.

    One general failure concept, following the search boundary's precedent: a
    taxonomy of timeout / status / parse / transport failures designed before
    real pages have failed would be wrong in the places that matter. The real
    failures observed during this phase are recorded in the plan document
    rather than encoded as classes.

    Constructing a `PageFetchRequest` or a `FetchedPage` with invalid input is a
    caller defect and raises `TypeError` or `ValueError` instead. This exception
    means the retrieval itself did not produce a usable page.
    """


class UnsafeFetchTargetError(PageFetchError):
    """The fetcher refused to open a destination.

    The one subclass that earns its place. Every other failure is something the
    outside world did — a timeout, a 403, a malformed response. This one is a
    decision *this code* made: the destination was refused before, or instead
    of, being contacted. A caller that cannot tell "we declined to go there"
    apart from "the site was down" cannot report either honestly, and the two
    have opposite meanings for whether a retry could ever succeed.
    """


def _require_text(value: object, field_name: str) -> str:
    if not isinstance(value, str):
        raise TypeError(f"{field_name} must be a string, got {type(value).__name__}")
    return value.strip()


def _optional_text(value: object, field_name: str) -> str | None:
    if value is None:
        return None
    return _require_text(value, field_name) or None


def require_fetchable_url(value: object, field_name: str = "url") -> str:
    """Return an absolute, credential-free http(s) URL, or raise `ValueError`.

    Three structural rules, applied to the URL *string*:

    * the scheme is `http` or `https` — a fetcher that honoured a `file:` URL
      would read the server's disk, and one that honoured anything else would
      be guessing what it had been handed;
    * a host is present, so relative (`/path`) and scheme-relative
      (`//host/path`) values are refused rather than silently resolved against
      something;
    * there is no userinfo component, so a credential can never be carried into
      a fetch by the URL itself. This rule is structural and therefore belongs
      here rather than in a fetcher: a request that *cannot hold* a credential
      is a stronger guarantee than a fetcher that promises to strip one.

    What this deliberately does *not* do is judge the destination. Whether a
    host resolves to a private address, where a redirect leads, and what comes
    back are runtime questions a fetcher answers — see `HttpPageFetcher`. This
    is a string check, not a security subsystem, and it is not a substitute for
    one.
    """
    text = _require_text(value, field_name)
    if not text:
        raise ValueError(f"{field_name} is required; there is nothing to fetch")

    parts = urlsplit(text)
    if parts.scheme.lower() not in ALLOWED_FETCH_SCHEMES:
        raise ValueError(
            f"{field_name} must be an absolute http:// or https:// URL, got {text!r}"
        )
    if not parts.hostname:
        raise ValueError(f"{field_name} must include a host, got {text!r}")
    if parts.username is not None or parts.password is not None:
        raise ValueError(
            f"{field_name} must not embed credentials; a fetch target carries no "
            "authentication"
        )
    return text


@dataclass(frozen=True)
class PageFetchRequest:
    """One document to retrieve, named by URL and nothing else.

    Deliberately one field. A fetch depth, a render mode, a proxy selection, a
    header override, a cookie jar, or a per-request user agent would each be a
    policy no phase has taken, and every one of them is a way for a caller to
    weaken a fetcher's own rules from outside. Bounds belong to the fetcher.

    The URL is validated at construction by `require_fetchable_url`, so an
    unfetchable request cannot exist.
    """

    url: str

    def __post_init__(self) -> None:
        object.__setattr__(self, "url", require_fetchable_url(self.url, "url"))


@dataclass(frozen=True)
class FetchedPage:
    """What one URL returned, recorded rather than interpreted.

    Every field is **untrusted external content**. A fetched page is data to be
    analysed, never an instruction to be followed (§19) — which matters more
    here than anywhere so far, because this is the first phase in which text
    written by strangers enters the system in bulk.

    `requested_url` and `final_url` are kept separately and both are required.
    A redirect is evidence: a listing reached at a different address than the
    one a search result advertised is a fact a reviewer needs, and storing only
    one of the two would quietly discard it. When nothing redirected they are
    equal, which is the honest representation of that case rather than a `None`.

    `retrieved_at` must be timezone-aware and is **supplied by the fetcher**,
    never generated in this module — the rule the domain (AD-015) and the
    search contracts already follow.

    `status_code` is the status of the final response. In practice only a
    successful response becomes a `FetchedPage`; the field records which success
    it was rather than asserting anything.

    `content_type` is the raw `Content-Type` header value as received, unparsed
    — parameters, casing, and all.

    `body_text` is the decoded document, and it is the page evidence this phase
    preserves. It is what extraction reads and what a recorded fixture is
    derived from. It is **not** trimmed, normalized, minified, or reduced to
    fields: the whole point of keeping it is that a later reader can check what
    a parser did against what the page actually said.

    `body_byte_count` is how many bytes were read off the wire before decoding,
    so a reviewer can tell a genuinely small page from an aggressively truncated
    one without re-encoding the text.

    `redirect_count` is how many hops were followed to reach `final_url`.

    `fetcher_id` identifies the implementation that produced this observation,
    for provenance only. It is runtime data — a string a fetcher supplies — and
    deliberately not an enumeration: no business rule may branch on it, and this
    boundary contains no list of fetchers.

    Deliberately absent, because extraction (3A), normalization (3B), and
    matching (3C) own them: title, price, currency, part number, seller,
    availability, condition, and any accept/reject decision. Also absent:
    response headers as a mapping, cookies, and a rendered DOM — the first would
    invite business logic to read one, and the other two do not exist here by
    design.
    """

    requested_url: str
    final_url: str
    retrieved_at: datetime
    status_code: int
    body_text: str
    content_type: str | None = None
    body_byte_count: int = 0
    redirect_count: int = 0
    fetcher_id: str = "unknown"

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "requested_url",
            require_fetchable_url(self.requested_url, "requested_url"),
        )
        object.__setattr__(
            self, "final_url", require_fetchable_url(self.final_url, "final_url")
        )

        if not isinstance(self.retrieved_at, datetime):
            raise TypeError(
                "retrieved_at must be a datetime, got "
                f"{type(self.retrieved_at).__name__}"
            )
        if self.retrieved_at.tzinfo is None or self.retrieved_at.utcoffset() is None:
            raise ValueError(
                "retrieved_at must be timezone-aware; a retrieval time without an "
                "offset cannot be compared with another observation"
            )

        if isinstance(self.status_code, bool) or not isinstance(self.status_code, int):
            raise TypeError(
                f"status_code must be an int, got {type(self.status_code).__name__}"
            )

        if not isinstance(self.body_text, str):
            raise TypeError(
                f"body_text must be a string, got {type(self.body_text).__name__}"
            )

        object.__setattr__(
            self, "content_type", _optional_text(self.content_type, "content_type")
        )

        for name in ("body_byte_count", "redirect_count"):
            value = getattr(self, name)
            if isinstance(value, bool) or not isinstance(value, int):
                raise TypeError(f"{name} must be an int, got {type(value).__name__}")
            if value < 0:
                raise ValueError(f"{name} must not be negative, got {value}")

        fetcher_id = _require_text(self.fetcher_id, "fetcher_id")
        if not fetcher_id:
            raise ValueError(
                "fetcher_id is required; an observation with no provenance cannot "
                "be attributed to anything"
            )
        object.__setattr__(self, "fetcher_id", fetcher_id)

    @property
    def was_redirected(self) -> bool:
        """Whether the document came from an address other than the one asked for."""
        return self.redirect_count > 0


class PageFetcher(Protocol):
    """The boundary a caller depends on instead of an HTTP library.

    One synchronous method, and a `Protocol` rather than a base class for the
    reason the search boundary is one: an implementation conforms by shape and
    inherits nothing.

    An implementation is expected to:

    * accept a `PageFetchRequest` and return a `FetchedPage` describing what the
      destination returned;
    * raise `PageFetchError` when retrieval fails, and `UnsafeFetchTargetError`
      when it refuses a destination;
    * bound its own timeout, redirects, and response size, and revalidate every
      redirect hop against the same rules as the original target;
    * send no credential, no cookie, and no authorization header of any kind;
    * execute no JavaScript, submit no form, and issue no request other than the
      GET for the document itself;
    * decide nothing about identity, price, or whether the page is a listing.

    A browser-rendering implementation could satisfy this same protocol later,
    if real evidence ever justifies the cost. None is implemented, and none is
    assumed.
    """

    def fetch(self, request: PageFetchRequest) -> FetchedPage:
        """Retrieve one document and return what the destination returned."""
        ...
