"""The Serper adapter, tested offline (PRODUCT-INTEL.2C).

Two kinds of test live here:

* **Recorded-fixture tests** load the real, sanitized response in
  `tests/fixtures/providers/serper/` and exercise the real adapter mapping
  (`_map_serper_payload`) against it. They prove the mapping this adapter
  actually performs, not a mock of what it should return — mocking the
  expected `SearchResult` list directly would bypass the thing 2C exists to
  prove.
* **Edge-case / plumbing tests** use small synthetic payloads (never claimed
  to be recorded) to exercise malformed-item handling, error translation, and
  the HTTP call itself with `urllib.request.urlopen` monkeypatched — so the
  normal suite makes zero live requests to Serper.
"""

from __future__ import annotations

import json
import urllib.error
from dataclasses import fields
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pytest

from product_intelligence.providers.search import (
    SearchProviderError,
    SearchQuery,
    SearchResponse,
    SearchResult,
)
from product_intelligence.providers.serper import (
    DEFAULT_ENDPOINT,
    PROVIDER_ID,
    SERPER_API_KEY_ENV_VAR,
    SerperSearchProvider,
    _map_organic_item,
    _map_serper_payload,
)

FIXTURE_PATH = (
    Path(__file__).resolve().parents[1]
    / "fixtures"
    / "providers"
    / "serper"
    / "real_verified_mz_ql23t800_organic_search.json"
)
RETRIEVED_AT = datetime(2026, 8, 17, 12, 0, 0, tzinfo=timezone.utc)


def _fixture_text() -> str:
    return FIXTURE_PATH.read_text(encoding="utf-8")


def _query() -> SearchQuery:
    return SearchQuery(text="MZ-QL23T800")


# ---------------------------------------------------------------------------
# Recorded fixture -> real mapping
# ---------------------------------------------------------------------------


def test_the_fixture_exists_and_is_parseable_json() -> None:
    payload = json.loads(_fixture_text())
    assert isinstance(payload, dict)
    assert isinstance(payload.get("organic"), list)


def test_the_recorded_response_contains_no_credential_material() -> None:
    raw = _fixture_text().lower()
    for forbidden in ("x-api-key", "api_key", "apikey", "authorization", "bearer "):
        assert forbidden not in raw


def test_the_real_response_maps_to_a_search_response() -> None:
    query = _query()
    response = _map_serper_payload(_fixture_text(), query=query, retrieved_at=RETRIEVED_AT)

    assert isinstance(response, SearchResponse)
    assert response.provider_id == PROVIDER_ID == "serper"
    assert response.query is query


def test_result_count_is_deterministic_for_the_fixture() -> None:
    response = _map_serper_payload(_fixture_text(), query=_query(), retrieved_at=RETRIEVED_AT)

    assert response.result_count == 10
    assert len(response.results) == 10


def test_source_url_maps_from_the_organic_link_field() -> None:
    response = _map_serper_payload(_fixture_text(), query=_query(), retrieved_at=RETRIEVED_AT)

    assert response.results[0].source_url == (
        "https://www.samsung.com/us/business/memory-storage/nvme-ssd/"
        "pm9a3-nvme-u-2-ssd-3-8tb-sku-mz-ql23t800/"
    )


def test_title_maps_when_supplied() -> None:
    response = _map_serper_payload(_fixture_text(), query=_query(), retrieved_at=RETRIEVED_AT)

    assert response.results[0].title == "MZ-QL23T800 | PM9A3 NVMe® U.2 3.84TB"


def test_snippet_maps_when_supplied() -> None:
    response = _map_serper_payload(_fixture_text(), query=_query(), retrieved_at=RETRIEVED_AT)

    assert response.results[0].snippet is not None
    assert "Samsung's Enterprise SSD PM9A3" in response.results[0].snippet


def test_retrieved_at_is_timezone_aware() -> None:
    response = _map_serper_payload(_fixture_text(), query=_query(), retrieved_at=RETRIEVED_AT)

    assert response.retrieved_at.tzinfo is not None
    assert response.retrieved_at.utcoffset() is not None


def test_ordinary_results_do_not_fabricate_a_part_number_hint() -> None:
    """Serper organic results publish no structured part-number field."""
    response = _map_serper_payload(_fixture_text(), query=_query(), retrieved_at=RETRIEVED_AT)

    assert all(result.part_number_hint is None for result in response.results)
    assert all(not result.has_part_number_hint for result in response.results)


def test_ordinary_results_do_not_fabricate_a_numeric_price() -> None:
    """Snippets contain price-shaped text; none of it becomes price_hint_text."""
    response = _map_serper_payload(_fixture_text(), query=_query(), retrieved_at=RETRIEVED_AT)

    assert all(result.price_hint_text is None for result in response.results)
    assert all(not result.has_price_hint for result in response.results)
    # The recorded fixture genuinely contains price-shaped snippet text —
    # confirming this is not a vacuous assertion.
    assert any(
        result.snippet and "$" in result.snippet for result in response.results
    )


def test_mapped_results_contain_no_vendor_specific_field() -> None:
    """`SearchResult` is the 2B contract; the adapter must not have widened it."""
    expected_fields = {
        "source_url",
        "title",
        "snippet",
        "price_hint_text",
        "part_number_hint",
        "raw_reference",
    }
    assert {f.name for f in fields(SearchResult)} == expected_fields


def test_raw_reference_preserves_the_organic_item_and_is_credential_free() -> None:
    response = _map_serper_payload(_fixture_text(), query=_query(), retrieved_at=RETRIEVED_AT)

    for result in response.results:
        assert result.raw_reference is not None
        parsed = json.loads(result.raw_reference)
        assert parsed["link"] == result.source_url
        assert "x-api-key" not in result.raw_reference.lower()


def test_raw_response_reference_is_the_full_body_text() -> None:
    response = _map_serper_payload(_fixture_text(), query=_query(), retrieved_at=RETRIEVED_AT)

    assert response.raw_response_reference == _fixture_text()


# ---------------------------------------------------------------------------
# Malformed / invalid individual results
# ---------------------------------------------------------------------------


def test_an_item_missing_a_link_is_discarded_not_fabricated() -> None:
    assert _map_organic_item({"title": "no link here"}) is None


def test_an_item_with_a_non_http_link_is_discarded() -> None:
    assert _map_organic_item({"title": "bad", "link": "javascript:alert(1)"}) is None


def test_an_item_with_a_relative_link_is_discarded() -> None:
    assert _map_organic_item({"title": "bad", "link": "/relative/path"}) is None


def test_a_non_dict_item_is_discarded() -> None:
    assert _map_organic_item("not a dict") is None
    assert _map_organic_item(None) is None
    assert _map_organic_item(["nope"]) is None


def test_a_valid_item_still_maps_when_other_items_are_malformed() -> None:
    payload = {
        "organic": [
            {"link": "not a valid url at all"},
            {"title": "Good", "link": "https://example.invalid/p/1", "snippet": "s"},
            "garbage",
            {"noLinkField": True},
        ]
    }
    response = _map_serper_payload(
        json.dumps(payload), query=_query(), retrieved_at=RETRIEVED_AT
    )

    assert response.result_count == 1
    assert response.results[0].source_url == "https://example.invalid/p/1"


def test_missing_organic_field_yields_zero_results_not_an_error() -> None:
    """Zero results is a valid answer, per the 2B contract."""
    response = _map_serper_payload(
        json.dumps({"searchParameters": {"q": "x"}}),
        query=_query(),
        retrieved_at=RETRIEVED_AT,
    )

    assert response.results == ()
    assert response.result_count == 0


def test_empty_organic_list_yields_zero_results() -> None:
    response = _map_serper_payload(
        json.dumps({"organic": []}), query=_query(), retrieved_at=RETRIEVED_AT
    )

    assert response.results == ()


# ---------------------------------------------------------------------------
# Response-level failure translation
# ---------------------------------------------------------------------------


def test_invalid_json_raises_search_provider_error() -> None:
    with pytest.raises(SearchProviderError):
        _map_serper_payload("not json at all {{{", query=_query(), retrieved_at=RETRIEVED_AT)


def test_a_non_object_top_level_response_raises_search_provider_error() -> None:
    with pytest.raises(SearchProviderError):
        _map_serper_payload("[1, 2, 3]", query=_query(), retrieved_at=RETRIEVED_AT)


def test_a_non_list_organic_field_raises_search_provider_error() -> None:
    with pytest.raises(SearchProviderError):
        _map_serper_payload(
            json.dumps({"organic": "not a list"}),
            query=_query(),
            retrieved_at=RETRIEVED_AT,
        )


# ---------------------------------------------------------------------------
# Construction and configuration
# ---------------------------------------------------------------------------


def test_construction_requires_a_non_blank_api_key() -> None:
    with pytest.raises(ValueError):
        SerperSearchProvider("")
    with pytest.raises(ValueError):
        SerperSearchProvider("   ")


def test_from_environment_reads_the_documented_variable(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv(SERPER_API_KEY_ENV_VAR, "test-key-value")

    provider = SerperSearchProvider.from_environment()

    assert isinstance(provider, SerperSearchProvider)
    # The key must never surface on the instance under a public/printable name.
    assert "test-key-value" not in repr(provider)


def test_from_environment_raises_when_the_variable_is_missing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv(SERPER_API_KEY_ENV_VAR, raising=False)

    with pytest.raises(ValueError, match=SERPER_API_KEY_ENV_VAR):
        SerperSearchProvider.from_environment()


def test_from_environment_raises_when_the_variable_is_blank(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv(SERPER_API_KEY_ENV_VAR, "   ")

    with pytest.raises(ValueError):
        SerperSearchProvider.from_environment()


def test_the_constructor_accepts_no_endpoint_argument() -> None:
    """The credential must not be redirectable to an arbitrary host.

    `endpoint` is deliberately absent from the public API: this adapter
    implements exactly one Serper mode, and an overridable endpoint would let
    a caller send the `X-API-KEY` credential wherever they chose.
    """
    with pytest.raises(TypeError):
        SerperSearchProvider("k", endpoint="https://attacker.invalid/collect")  # type: ignore[call-arg]


def test_from_environment_accepts_no_endpoint_argument(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv(SERPER_API_KEY_ENV_VAR, "test-key-value")

    with pytest.raises(TypeError):
        SerperSearchProvider.from_environment(
            endpoint="https://attacker.invalid/collect"  # type: ignore[call-arg]
        )


def test_search_rejects_a_non_search_query_argument() -> None:
    provider = SerperSearchProvider("k")

    with pytest.raises(TypeError):
        provider.search("not a SearchQuery")  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# The HTTP call itself, with urlopen monkeypatched (no network)
# ---------------------------------------------------------------------------


class _FakeHTTPResponse:
    def __init__(self, body: bytes) -> None:
        self._body = body

    def read(self) -> bytes:
        return self._body

    def __enter__(self) -> "_FakeHTTPResponse":
        return self

    def __exit__(self, *exc_info: object) -> None:
        return None


def test_search_sends_the_credential_in_a_header_never_in_the_url(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured: dict[str, Any] = {}

    def fake_urlopen(request, timeout=None):  # noqa: ANN001
        captured["url"] = request.full_url
        captured["headers"] = dict(request.header_items())
        captured["body"] = request.data
        captured["timeout"] = timeout
        return _FakeHTTPResponse(json.dumps({"organic": []}).encode("utf-8"))

    monkeypatch.setattr(
        "product_intelligence.providers.serper.urllib.request.urlopen", fake_urlopen
    )

    provider = SerperSearchProvider("secret-key-123", clock=lambda: RETRIEVED_AT)
    response = provider.search(_query())

    assert captured["url"] == DEFAULT_ENDPOINT
    assert "secret-key-123" not in captured["url"]
    header_names = {name.lower() for name in captured["headers"]}
    assert "x-api-key" in header_names
    assert captured["headers"][
        next(n for n in captured["headers"] if n.lower() == "x-api-key")
    ] == "secret-key-123"
    assert b"secret-key-123" not in captured["body"]
    assert json.loads(captured["body"].decode("utf-8")) == {"q": "MZ-QL23T800"}
    assert response.results == ()


def test_search_translates_an_http_error_without_leaking_the_credential(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fake_urlopen(request, timeout=None):  # noqa: ANN001
        raise urllib.error.HTTPError(
            DEFAULT_ENDPOINT, 401, "Unauthorized", hdrs=None, fp=None  # type: ignore[arg-type]
        )

    monkeypatch.setattr(
        "product_intelligence.providers.serper.urllib.request.urlopen", fake_urlopen
    )

    provider = SerperSearchProvider("secret-key-123")

    with pytest.raises(SearchProviderError) as excinfo:
        provider.search(_query())

    assert "secret-key-123" not in str(excinfo.value)
    assert "401" in str(excinfo.value)


def test_search_translates_a_url_error(monkeypatch: pytest.MonkeyPatch) -> None:
    def fake_urlopen(request, timeout=None):  # noqa: ANN001
        raise urllib.error.URLError("name resolution failed")

    monkeypatch.setattr(
        "product_intelligence.providers.serper.urllib.request.urlopen", fake_urlopen
    )

    provider = SerperSearchProvider("k")

    with pytest.raises(SearchProviderError):
        provider.search(_query())


def test_search_translates_a_timeout(monkeypatch: pytest.MonkeyPatch) -> None:
    def fake_urlopen(request, timeout=None):  # noqa: ANN001
        raise TimeoutError("timed out")

    monkeypatch.setattr(
        "product_intelligence.providers.serper.urllib.request.urlopen", fake_urlopen
    )

    provider = SerperSearchProvider("k")

    with pytest.raises(SearchProviderError):
        provider.search(_query())


def test_search_translates_invalid_json_from_a_live_looking_response(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fake_urlopen(request, timeout=None):  # noqa: ANN001
        return _FakeHTTPResponse(b"not json")

    monkeypatch.setattr(
        "product_intelligence.providers.serper.urllib.request.urlopen", fake_urlopen
    )

    provider = SerperSearchProvider("k")

    with pytest.raises(SearchProviderError):
        provider.search(_query())


def test_zero_results_from_a_live_looking_call_is_not_an_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fake_urlopen(request, timeout=None):  # noqa: ANN001
        return _FakeHTTPResponse(json.dumps({"organic": []}).encode("utf-8"))

    monkeypatch.setattr(
        "product_intelligence.providers.serper.urllib.request.urlopen", fake_urlopen
    )

    provider = SerperSearchProvider("k")
    response = provider.search(_query())

    assert response.results == ()
    assert response.result_count == 0
