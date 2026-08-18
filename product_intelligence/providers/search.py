"""The search-provider boundary (PRODUCT-INTEL.2B).

One synchronous operation, three provider-neutral contracts:

```text
SearchQuery  ->  SearchProvider.search(query)  ->  SearchResponse
                                                     |- SearchResult, ...
```

This module is deliberately thin. It exists so that PRODUCT-INTEL.2C can
integrate exactly one real provider behind a shape the research core already
depends on — not so that the project owns a provider framework. There is no
registry, no factory, no plugin discovery, no fallback chain, no fan-out, no
retry policy, no rate limiter, and no async variant, because one provider
arrives next and none of that is needed to receive it. Replaceability is the
goal; simultaneity is not.

What this boundary is *not*
---------------------------

**It is not search.** Nothing here performs a request, opens a socket, reads a
credential, or names a vendor. The generic boundary is data contracts plus a
`Protocol`; the code that talks to a real service is an adapter, and no adapter
exists yet. Search-vendor selection is `UNDECIDED` until 2C.

**It is not extraction.** A `SearchResult` records what a provider was observed
to say. It does not parse a price, choose between a sale price and a monthly
payment, read a currency, count a multi-pack, judge a seller, or decide that a
result is a listing at all. That is 3A/3B work, and doing it here would put
market interpretation inside a transport adapter.

**It is not identity.** A provider never compares part numbers and never returns
"verified" results. When a provider explicitly publishes a part-number field, it
arrives as `part_number_hint` — an unverified observation — and the research
core decides what, if anything, it establishes by handing it to the
deterministic comparison in `product_intelligence.research.identity`. A provider
that owned that decision would make a vendor the authority on product identity,
which is the one thing the architecture never permits.

**It is not evidence storage.** Nothing here is persisted. `EvidenceReference`
in the domain remains the generic attributable observation and is deliberately
not widened into a universal provider result.

Raw provider material
---------------------

Real providers return more than these contracts carry, and some of it will turn
out to matter. The rule is not "widen the contract until it holds everything",
and it is certainly not "pass the vendor's payload through so the core can look
inside":

```text
provider adapter  ->  normalized SearchResult / SearchResponse fields
                  +   an opaque raw reference
```

Business logic reads the normalized fields. The opaque references
(`SearchResult.raw_reference`, `SearchResponse.raw_response_reference`) exist so
that what a provider actually returned can be preserved and re-inspected by a
human or a test — never so that the core can branch on a vendor-specific key.
They are strings, they are kept verbatim, and nothing in this project parses
them. A provider-shaped `dict` is deliberately not the type: it would be an open
invitation to read `payload["some_vendor_key"][0]` somewhere in a research rule,
and the vendor would be in the business logic from that moment on.

Recorded fixtures
-----------------

From 2C onward, provider adapters are regression-tested against **sanitized
recorded responses** — real provider output with credentials, tokens, request
secrets, and personal data removed — so the automated suite stays offline and
deterministic. Live calls belong only to an explicit, manually run integration
check. No such fixture exists yet, and none may be invented here: a fabricated
"real response" would be a guess about a provider that has not been chosen, and
it would pass regardless of what the real one does.
"""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from datetime import datetime
from typing import Protocol
from urllib.parse import urlsplit

# The only schemes a search result may point at. A result URL is a web address
# that a person or a later phase can open and re-read; `javascript:`, `data:`,
# and `file:` are not addresses of that kind, and a result carrying one is
# rejected at the boundary rather than stored and rendered later. This is one
# narrow rule, not a URL-security subsystem: it does not judge hosts, redirects,
# credentials embedded in a URL, or the content on the other end.
ALLOWED_URL_SCHEMES: frozenset[str] = frozenset({"http", "https"})


class SearchProviderError(Exception):
    """A search provider could not produce a response.

    One concept, deliberately. A taxonomy of timeout / quota / auth / rate-limit
    / parse failures would be designed against imagined failures before any real
    provider has produced one, and would then be wrong in exactly the places
    that matter. 2C sees the real error surface and may justify a small
    hierarchy underneath this base then.

    This is *not* what a malformed contract raises: constructing a `SearchQuery`,
    `SearchResult`, or `SearchResponse` with invalid input is a caller defect and
    raises `TypeError` or `ValueError`, the way the domain contracts do. This
    exception means the external operation failed.
    """


def _require_text(value: object, field_name: str) -> str:
    """Return `value` stripped of surrounding whitespace, or raise `TypeError`."""
    if not isinstance(value, str):
        raise TypeError(f"{field_name} must be a string, got {type(value).__name__}")
    return value.strip()


def _optional_text(value: object, field_name: str) -> str | None:
    """Normalize an optional observed text field.

    Surrounding whitespace is removed and an empty result becomes `None`, so
    "the provider said nothing here" has one representation. The *interior* of a
    value is never touched: observed text is data, and rewriting it would
    destroy the thing later phases have to review their normalization against.
    """
    if value is None:
        return None
    return _require_text(value, field_name) or None


def _opaque_reference(value: object, field_name: str) -> str | None:
    """Accept preserved provider material without touching it.

    Unlike an observed text field, this is not trimmed. It is the artifact a
    reviewer or a recorded fixture is compared against, so it is kept exactly as
    the adapter captured it — trailing newline and all. An empty string carries
    nothing and becomes `None`; anything else is passed through unchanged and
    unparsed.
    """
    if value is None:
        return None
    if not isinstance(value, str):
        raise TypeError(
            f"{field_name} must be a string or None, got {type(value).__name__}; "
            "provider-native material is preserved as an opaque reference, not "
            "as a structure for business logic to read"
        )
    return value or None


def _require_web_url(value: object, field_name: str) -> str:
    """Return an absolute `http(s)` URL, or raise.

    The check is structural and small: the scheme must be `http` or `https`, and
    a host must be present, so a scheme-relative (`//host/path`) or relative
    (`/path`) value is refused along with `javascript:`, `data:`, and `file:`.
    The value is then returned **as observed** — surrounding whitespace removed
    and nothing else — because a result URL is evidence, and re-serializing it
    from parsed components would quietly change what the provider said.
    """
    text = _require_text(value, field_name)
    if not text:
        raise ValueError(
            f"{field_name} is required; a result with no URL is untraceable"
        )

    parts = urlsplit(text)
    if parts.scheme.lower() not in ALLOWED_URL_SCHEMES:
        raise ValueError(
            f"{field_name} must be an absolute http:// or https:// URL, got {text!r}"
        )
    if not parts.netloc:
        raise ValueError(f"{field_name} must include a host, got {text!r}")

    return text


@dataclass(frozen=True)
class SearchQuery:
    """One concrete external search operation.

    Deliberately **not** a `ResearchRequest`. The two are different things, and
    conflating them would hand the provider a product-research problem:

    ```text
    ResearchRequest  a person's research input: MPN + description
    SearchQuery      one string sent to one external search service
    ```

    One research request may later produce several queries — a part number
    alone, a part number with a qualifier, a description phrasing — and deciding
    which is query *generation*, which belongs to the research core and does not
    exist yet (§12, 3A onward). A provider that accepted a `ResearchRequest`
    would have to make that decision itself, which is how a transport adapter
    becomes responsible for research semantics.

    Contract: `text` is a string, surrounding whitespace is removed, and what
    remains must be non-empty. Nothing else — no category, no locale, no result
    limit, no vendor-specific search mode, no pagination cursor, no shopping
    flag. Each of those is a policy decision no phase has taken, and 2C can
    integrate a real provider without any of them.
    """

    text: str

    def __post_init__(self) -> None:
        text = _require_text(self.text, "query text")
        if not text:
            raise ValueError(
                "a search query requires non-empty text; there is nothing to ask "
                "an external service for"
            )
        object.__setattr__(self, "text", text)


@dataclass(frozen=True)
class SearchResult:
    """One provider-observed result, recorded rather than interpreted.

    Every field is **untrusted external text**. It is data to be analysed, never
    an instruction to follow (§19) and never a fact the system has established.

    `source_url` is the only required field, because it is what makes the
    observation traceable: an observation nobody can go back and look at is not
    evidence. It must be an absolute `http`/`https` URL.

    `title` and `snippet` are what the provider displayed. They are optional —
    real providers omit them — and they are stored as observed.

    `price_hint_text` is **not a price.** It is whatever price-shaped text the
    provider showed: `"$399.99"`, `"$399.99 - $449.99"`, `"from $399"`,
    `"EUR 320"`, `"$33/mo"`. It stays a string here and is never converted to a
    `Decimal`, assigned a currency, resolved between a sale price and a shipping
    charge, or used in arithmetic. There is deliberately **no numeric price
    field on this contract at all** — adding one would make a search snippet
    look like a verified market observation, and price extraction (3A),
    normalization (3B), and aggregation (4A) each exist precisely because that
    conversion is a decision with rules, not a cast.

    `part_number_hint` is an **unverified** candidate part number, present only
    when a provider explicitly publishes such a field. It is not a match, not a
    verification, and not a claim about the product. Nothing here normalizes or
    compares it: the research core passes it to the deterministic comparison
    (2A) when it decides to. A part number *inferred* from a title, a snippet, or
    a URL is not this field — that is extraction from noisy text, and it belongs
    to 3A/3C where rejection reasons are recorded. Blurring the two would let a
    guess enter the system wearing the same name as a published value.

    `raw_reference` is opaque preserved material identifying what the provider
    returned for this result. It is never parsed, and no business rule may read
    inside it.

    Deliberately absent, because 3A/3B own them and a guessed schema would be
    wrong: seller, quantity, pack size, unit price, currency, condition,
    availability, shipping, rank, score, and any accept/reject decision.
    """

    source_url: str
    title: str | None = None
    snippet: str | None = None
    price_hint_text: str | None = None
    part_number_hint: str | None = None
    raw_reference: str | None = None

    def __post_init__(self) -> None:
        object.__setattr__(
            self, "source_url", _require_web_url(self.source_url, "source_url")
        )
        for name in ("title", "snippet", "price_hint_text", "part_number_hint"):
            object.__setattr__(self, name, _optional_text(getattr(self, name), name))
        object.__setattr__(
            self,
            "raw_reference",
            _opaque_reference(self.raw_reference, "raw_reference"),
        )

    @property
    def has_price_hint(self) -> bool:
        """Whether price-shaped text was observed — not whether a price is known."""
        return self.price_hint_text is not None

    @property
    def has_part_number_hint(self) -> bool:
        """Whether the provider published a part number — not whether it matches."""
        return self.part_number_hint is not None


@dataclass(frozen=True)
class SearchResponse:
    """One provider's answer to one query, with its provenance.

    A bare list of results would lose the two things that make the observation
    reviewable later: **who** returned it and **when**. Prices are observations
    at a moment (§11), so a batch of results with no retrieval time is already
    unusable as evidence by the time anyone reads it.

    `provider_id` identifies the provider that answered, for provenance only. It
    is runtime data — a string an adapter supplies — and deliberately not an
    enumeration: the generic boundary must never contain a list of vendors, and
    no business rule may branch on this value.

    `query` is the `SearchQuery` that was executed, carried back so a response
    can be read on its own.

    `retrieved_at` must be timezone-aware and is **always supplied by the
    adapter**, never generated here — the same rule the domain follows (AD-015),
    which keeps tests deterministic and keeps time out of the contracts.

    `results` is an immutable tuple, possibly empty. **Zero results is a valid
    answer**, not an error: "the provider found nothing" is information, and
    raising instead would push a legitimate outcome into the failure path.

    `raw_response_reference` is opaque preserved material for the response as a
    whole, under the same rule as `SearchResult.raw_reference`.
    """

    provider_id: str
    query: SearchQuery
    retrieved_at: datetime
    results: tuple[SearchResult, ...] = ()
    raw_response_reference: str | None = None

    def __post_init__(self) -> None:
        provider_id = _require_text(self.provider_id, "provider_id")
        if not provider_id:
            raise ValueError(
                "provider_id is required; an observation with no provenance "
                "cannot be attributed to anything"
            )
        object.__setattr__(self, "provider_id", provider_id)

        if not isinstance(self.query, SearchQuery):
            raise TypeError(
                f"query must be a SearchQuery, got {type(self.query).__name__}"
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

        results = self.results
        if isinstance(results, (str, bytes)) or not isinstance(results, Iterable):
            raise TypeError(
                "results must be an iterable of SearchResult, got "
                f"{type(results).__name__}"
            )
        materialized = tuple(results)
        for index, result in enumerate(materialized):
            if not isinstance(result, SearchResult):
                raise TypeError(
                    f"results[{index}] must be a SearchResult, got "
                    f"{type(result).__name__}"
                )
        object.__setattr__(self, "results", materialized)

        object.__setattr__(
            self,
            "raw_response_reference",
            _opaque_reference(self.raw_response_reference, "raw_response_reference"),
        )

    @property
    def result_count(self) -> int:
        return len(self.results)


class SearchProvider(Protocol):
    """The boundary the research core depends on instead of a vendor.

    One synchronous method. A `Protocol` rather than a base class, so an adapter
    (or a test fake) conforms by shape and inherits nothing: there is no
    lifecycle to share, no constructor to agree on, and no behaviour worth
    putting in a superclass before a single implementation exists.

    An implementation is expected to:

    * accept a `SearchQuery` and return a `SearchResponse` describing what it
      observed, including an empty one when the provider found nothing;
    * raise `SearchProviderError` when the external operation fails;
    * keep every vendor concern — endpoint, credentials read from the server
      environment, payload shape, pagination, rate limits, retries — inside
      itself, and expose none of it through these contracts;
    * decide nothing about identity, price, or whether a result is a listing.
    """

    def search(self, query: SearchQuery) -> SearchResponse:
        """Execute one query and return what the provider observed."""
        ...
