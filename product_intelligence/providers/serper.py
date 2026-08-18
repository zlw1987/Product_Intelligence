"""The Serper adapter — the first real `SearchProvider` (PRODUCT-INTEL.2C).

This module is where a vendor is allowed to exist. `SerperSearchProvider`
implements the `SearchProvider` protocol from `product_intelligence.providers
.search` by calling Serper's ordinary Google Search endpoint
(`https://google.serper.dev/search`) and mapping its `organic` results onto
the provider-neutral `SearchResult` / `SearchResponse` contracts. Google
Shopping is not used here — that is a distinct future decision, not this
phase's.

What stays out of this file
----------------------------

* **No identity decision.** The adapter never calls
  `product_intelligence.research.identity`. A Serper organic result does not
  publish a structured part-number field, so every mapped result carries
  `part_number_hint=None` — a hint is only ever the value a provider *itself*
  publishes, never something inferred from a title, snippet, or URL.
* **No price.** Ordinary Google Search results are text, not a price feed.
  `price_hint_text` stays `None` for the same reason: nothing about an
  organic snippet is a price a provider "displayed" in the sense the 2B
  contract means, and regexing one out of free text would be extraction
  (3A/3C), not observation.
* **No persistence, no Django, no research/runs/web import.** This module
  depends on nothing but the standard library and
  `product_intelligence.providers.search`.

Credential handling
--------------------

The API key is supplied to `SerperSearchProvider.__init__` and, for ordinary
use, obtained from the `SERPER_API_KEY` server environment variable through
`SerperSearchProvider.from_environment()`. It is sent exactly once per
request, in the `X-API-KEY` header Serper's API documents — never in the URL,
never in `raw_reference` or `raw_response_reference`, and never interpolated
into a `SearchProviderError` message. Reading the environment happens only in
`from_environment()`, an adapter-local edge; the generic boundary in
`search.py` still reads no configuration of any kind.

`DEFAULT_ENDPOINT` is fixed and is **not** a constructor parameter on either
`__init__` or `from_environment`: this adapter implements exactly one Serper
mode, and an overridable endpoint would let a caller point the credential at
an arbitrary host. `timeout` and `clock` stay overridable — neither affects
where the credential is sent.

Raw material
------------

Serper's JSON is understood only inside `_map_serper_payload` /
`_map_organic_item`. Each mapped `SearchResult.raw_reference` is a serialized
copy of that one organic item's data (`json.dumps` over the parsed item, not
the original response bytes); `SearchResponse.raw_response_reference`
preserves the full response body text exactly as received. Neither is parsed
by anything outside this module — business logic reads the normalized fields
only.
"""

from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from collections.abc import Callable
from datetime import datetime, timezone

from product_intelligence.providers.search import (
    SearchProviderError,
    SearchQuery,
    SearchResponse,
    SearchResult,
)

#: The environment variable ordinary operation reads the credential from.
#: Never read outside `SerperSearchProvider.from_environment`.
SERPER_API_KEY_ENV_VAR = "SERPER_API_KEY"

#: Serper's ordinary Google Search endpoint. Google Shopping is a different
#: endpoint and is out of scope for this phase.
DEFAULT_ENDPOINT = "https://google.serper.dev/search"

#: A bounded timeout so one slow call cannot hang a caller indefinitely. No
#: retry policy accompanies it — a single unmet deadline is
#: `SearchProviderError`, not a scheduler.
DEFAULT_TIMEOUT_SECONDS = 10.0

#: `SearchResponse.provider_id` for every response this adapter returns.
PROVIDER_ID = "serper"


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _map_organic_item(item: object) -> SearchResult | None:
    """Map one Serper `organic` entry, or discard it.

    Real external data is not trustworthy: an item with no usable absolute
    `http`/`https` URL is not traceable and must not become a fabricated
    `SearchResult`. It is simply skipped — the surrounding raw response text
    still preserves it for inspection.
    """
    if not isinstance(item, dict):
        return None

    link = item.get("link")
    if not isinstance(link, str) or not link.strip():
        return None

    title = item.get("title")
    snippet = item.get("snippet")

    try:
        return SearchResult(
            source_url=link,
            title=title if isinstance(title, str) else None,
            snippet=snippet if isinstance(snippet, str) else None,
            price_hint_text=None,
            part_number_hint=None,
            raw_reference=json.dumps(item, ensure_ascii=False),
        )
    except (TypeError, ValueError):
        # A structurally present but unusable "link" (wrong scheme, no host,
        # ...). Discard rather than invent a fake evidence record.
        return None


def _map_serper_payload(
    raw_text: str, *, query: SearchQuery, retrieved_at: datetime
) -> SearchResponse:
    """Turn one raw Serper response body into a `SearchResponse`.

    Kept separate from the HTTP call so it can be exercised offline against a
    sanitized recorded fixture without a network dependency.
    """
    try:
        payload = json.loads(raw_text)
    except json.JSONDecodeError as exc:
        raise SearchProviderError(
            "Serper returned a response body that was not valid JSON"
        ) from exc

    if not isinstance(payload, dict):
        raise SearchProviderError(
            "Serper returned an unusable top-level response shape "
            f"({type(payload).__name__}, expected an object)"
        )

    organic = payload.get("organic", [])
    if not isinstance(organic, list):
        raise SearchProviderError(
            "Serper response 'organic' field was not a list"
        )

    results = tuple(
        result
        for item in organic
        if (result := _map_organic_item(item)) is not None
    )

    return SearchResponse(
        provider_id=PROVIDER_ID,
        query=query,
        retrieved_at=retrieved_at,
        results=results,
        raw_response_reference=raw_text or None,
    )


class SerperSearchProvider:
    """`SearchProvider` backed by Serper's ordinary Google Search endpoint.

    Conforms to the protocol structurally, like the test fake in 2B — it
    inherits nothing and exposes only `search`.
    """

    def __init__(
        self,
        api_key: str,
        *,
        timeout: float = DEFAULT_TIMEOUT_SECONDS,
        clock: Callable[[], datetime] = _utc_now,
    ) -> None:
        if not isinstance(api_key, str) or not api_key.strip():
            raise ValueError(
                "api_key is required; SerperSearchProvider cannot authenticate "
                "without one"
            )
        self._api_key = api_key.strip()
        self._timeout = timeout
        self._clock = clock

    @classmethod
    def from_environment(
        cls,
        *,
        timeout: float = DEFAULT_TIMEOUT_SECONDS,
        clock: Callable[[], datetime] = _utc_now,
    ) -> "SerperSearchProvider":
        """Build a provider from the `SERPER_API_KEY` server environment variable.

        Raises `ValueError` — a construction-time caller defect, the same
        category the 2B contracts use — when the variable is missing or
        blank. This is the only place in the adapter that reads the process
        environment.
        """
        api_key = os.environ.get(SERPER_API_KEY_ENV_VAR)
        if not api_key or not api_key.strip():
            raise ValueError(
                f"{SERPER_API_KEY_ENV_VAR} is not set in the server environment"
            )
        return cls(api_key, timeout=timeout, clock=clock)

    def search(self, query: SearchQuery) -> SearchResponse:
        """Execute one query against Serper's ordinary Google Search endpoint
        (`DEFAULT_ENDPOINT`) and return what it observed.

        The endpoint is fixed and not caller-configurable: this adapter
        implements exactly one Serper mode, and an overridable endpoint would
        let a caller redirect the `X-API-KEY` credential to an arbitrary host.
        """
        if not isinstance(query, SearchQuery):
            raise TypeError(f"query must be a SearchQuery, got {type(query).__name__}")

        request_body = json.dumps({"q": query.text}).encode("utf-8")
        request = urllib.request.Request(
            DEFAULT_ENDPOINT,
            data=request_body,
            headers={
                "X-API-KEY": self._api_key,
                "Content-Type": "application/json",
            },
            method="POST",
        )

        try:
            with urllib.request.urlopen(request, timeout=self._timeout) as response:
                raw_text = response.read().decode("utf-8")
        except urllib.error.HTTPError as exc:
            raise SearchProviderError(
                f"Serper search request failed with HTTP {exc.code}"
            ) from exc
        except urllib.error.URLError as exc:
            raise SearchProviderError(
                f"Serper search request failed: {exc.reason}"
            ) from exc
        except TimeoutError as exc:
            raise SearchProviderError("Serper search request timed out") from exc
        except OSError as exc:
            raise SearchProviderError(
                "Serper search request failed due to a transport error"
            ) from exc

        return _map_serper_payload(
            raw_text, query=query, retrieved_at=self._clock()
        )
