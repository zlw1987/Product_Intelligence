"""The provider-neutral search contracts (PRODUCT-INTEL.2B).

These are contract tests, so they test the decisions rather than the dataclass
machinery. Four decisions carry the phase:

* a `SearchQuery` is one external operation and not a `ResearchRequest`;
* a result URL is an absolute web address, so an observation stays traceable and
  a `javascript:`/`data:`/`file:` value never reaches a report;
* a price hint is text a provider displayed, not a price — the contract has no
  numeric price field at all, and it must not acquire one by convenience;
* a part-number hint is an unverified observation, kept exactly as published.

Everything a provider returns is untrusted external text (§19). The tests below
therefore also assert that odd, script-shaped, and non-ASCII values are
*preserved as data* rather than cleaned, decoded, or interpreted.
"""

from __future__ import annotations

from dataclasses import FrozenInstanceError, fields
from datetime import datetime, timedelta, timezone

import pytest

from product_intelligence.providers import (
    SearchProviderError,
    SearchQuery,
    SearchResponse,
    SearchResult,
)

RETRIEVED_AT = datetime(2026, 3, 4, 5, 6, 7, tzinfo=timezone.utc)
RESULT_URL = "https://example.invalid/catalog/abc123-x"


def a_result(**overrides: object) -> SearchResult:
    values: dict[str, object] = {"source_url": RESULT_URL}
    values.update(overrides)
    return SearchResult(**values)  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# SearchQuery
# ---------------------------------------------------------------------------


def test_a_query_carries_the_text_that_will_be_sent() -> None:
    query = SearchQuery(text="ABC123-X price")

    assert query.text == "ABC123-X price"


def test_surrounding_whitespace_is_removed_from_query_text() -> None:
    """The interior is untouched — only the edges are transport noise."""
    query = SearchQuery(text="  ABC123-X  24 port switch \n")

    assert query.text == "ABC123-X  24 port switch"


@pytest.mark.parametrize("text", ["", "   ", "\t\n"])
def test_a_blank_query_is_rejected(text: str) -> None:
    with pytest.raises(ValueError):
        SearchQuery(text=text)


@pytest.mark.parametrize("text", [None, 42, ["ABC123-X"], b"ABC123-X"])
def test_query_text_must_be_a_string(text: object) -> None:
    with pytest.raises(TypeError):
        SearchQuery(text=text)  # type: ignore[arg-type]


def test_a_query_is_immutable_and_compares_by_value() -> None:
    query = SearchQuery(text="ABC123-X")

    assert query == SearchQuery(text=" ABC123-X ")
    with pytest.raises(FrozenInstanceError):
        query.text = "something else"  # type: ignore[misc]


def test_a_query_is_not_a_research_request() -> None:
    """One field, and no description: the two contracts are different things.

    A `SearchQuery` is one concrete external operation; a `ResearchRequest` is a
    person's research input. Query generation — turning one request into one or
    more queries — is research-core work that does not exist yet, and a provider
    accepting a `ResearchRequest` would have to do it itself.
    """
    assert [field.name for field in fields(SearchQuery)] == ["text"]

    from product_intelligence.domain import ResearchRequest

    assert not isinstance(SearchQuery(text="ABC123-X"), ResearchRequest)
    with pytest.raises(TypeError):
        SearchQuery(  # type: ignore[call-arg]
            text="ABC123-X", description="24-port switch"
        )


# ---------------------------------------------------------------------------
# SearchResult — the URL is what makes an observation traceable
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "url",
    [
        "http://example.invalid/p/1",
        "https://example.invalid/p/1",
        "https://example.invalid:8443/p/1?q=abc123-x#frag",
        "HTTPS://EXAMPLE.INVALID/p/1",
    ],
)
def test_absolute_web_urls_are_accepted_as_observed(url: str) -> None:
    """Accepted, and returned unchanged: a URL is evidence, not a value to rewrite."""
    assert a_result(source_url=url).source_url == url


@pytest.mark.parametrize(
    "url",
    [
        "javascript:alert(1)",
        "JavaScript:alert(1)",
        "data:text/html;base64,PHNjcmlwdD4=",
        "file:///etc/passwd",
        "ftp://example.invalid/p/1",
        "mailto:sales@example.invalid",
    ],
)
def test_non_web_schemes_are_rejected(url: str) -> None:
    """A stored result is later rendered on a report; these are not addresses."""
    with pytest.raises(ValueError):
        a_result(source_url=url)


@pytest.mark.parametrize(
    "url",
    [
        "example.invalid/p/1",
        "/catalog/abc123-x",
        "//example.invalid/p/1",
        "https://",
        "http:example.invalid",
        "not a url at all",
    ],
)
def test_relative_or_malformed_urls_are_rejected(url: str) -> None:
    with pytest.raises(ValueError):
        a_result(source_url=url)


@pytest.mark.parametrize("url", ["", "   "])
def test_a_result_requires_a_url(url: str) -> None:
    """An observation nobody can go back and look at is not evidence."""
    with pytest.raises(ValueError):
        a_result(source_url=url)


def test_a_url_must_be_a_string() -> None:
    with pytest.raises(TypeError):
        a_result(source_url=None)


def test_surrounding_whitespace_is_removed_from_a_url() -> None:
    assert a_result(source_url=f"  {RESULT_URL}\n").source_url == RESULT_URL


# ---------------------------------------------------------------------------
# SearchResult — optional observations
# ---------------------------------------------------------------------------


def test_a_result_needs_nothing_but_a_url() -> None:
    """Real providers omit fields; a missing observation is absent, not empty."""
    result = a_result()

    assert result.title is None
    assert result.snippet is None
    assert result.price_hint_text is None
    assert result.part_number_hint is None
    assert result.raw_reference is None
    assert not result.has_price_hint
    assert not result.has_part_number_hint


@pytest.mark.parametrize(
    "field_name", ["title", "snippet", "price_hint_text", "part_number_hint"]
)
def test_a_blank_optional_observation_becomes_absent(field_name: str) -> None:
    assert getattr(a_result(**{field_name: "   "}), field_name) is None


@pytest.mark.parametrize(
    "field_name", ["title", "snippet", "price_hint_text", "part_number_hint"]
)
def test_an_optional_observation_must_be_a_string(field_name: str) -> None:
    with pytest.raises(TypeError):
        a_result(**{field_name: 12.5})


def test_observed_text_is_preserved_rather_than_cleaned() -> None:
    """Untrusted text is data. It is neither interpreted nor sanitized here.

    Escaping belongs to the layer that renders (the web shell already escapes and
    never marks user text safe); rewriting it at the boundary would destroy the
    thing a later normalization has to be reviewed against.
    """
    title = "<script>alert('x')</script> ABC123-X — 24‑port switch"
    result = a_result(title=title, snippet="Best price: see seller — 库存")

    assert result.title == title
    assert result.snippet == "Best price: see seller — 库存"


# ---------------------------------------------------------------------------
# SearchResult — a price hint is not a price
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "hint",
    ["$399.99", "$399.99 - $449.99", "from $399", "EUR 320", "$33/mo", "Call for price"],
)
def test_a_price_hint_stays_the_text_the_provider_showed(hint: str) -> None:
    result = a_result(price_hint_text=hint)

    assert result.price_hint_text == hint
    assert isinstance(result.price_hint_text, str)
    assert result.has_price_hint


def test_the_result_contract_has_no_numeric_price_field() -> None:
    """The exact field list, asserted, so a numeric price cannot be slipped in.

    A `Decimal` price on a search result would present a snippet as a verified
    market observation. Extraction (3A), normalization (3B), and aggregation (4A)
    exist because that conversion is a decision with rules — currency, pack size,
    sale versus shipping versus monthly payment — not a cast.
    """
    assert [field.name for field in fields(SearchResult)] == [
        "source_url",
        "title",
        "snippet",
        "price_hint_text",
        "part_number_hint",
        "raw_reference",
    ]

    annotations = {field.name: field.type for field in fields(SearchResult)}
    assert annotations["price_hint_text"] == "str | None"
    for forbidden in (
        "price",
        "price_amount",
        "currency",
        "unit_price",
        "quantity",
        "seller",
        "condition",
        "availability",
    ):
        assert forbidden not in annotations


# ---------------------------------------------------------------------------
# SearchResult — a part-number hint is an unverified observation
# ---------------------------------------------------------------------------


def test_a_part_number_hint_is_kept_exactly_as_published() -> None:
    """Not normalized, not compared, not called a match.

    Normalization and comparison are the 2A primitive's job, and the research
    core decides when to invoke it. A provider that normalized here would be
    making an identity decision inside a transport adapter.
    """
    result = a_result(part_number_hint="abc123 x")

    assert result.part_number_hint == "abc123 x"
    assert result.has_part_number_hint


def test_a_part_number_hint_says_nothing_about_the_requested_product() -> None:
    """`has_part_number_hint` reports presence, never agreement."""
    result = a_result(part_number_hint="ZZZ999")

    assert result.has_part_number_hint
    assert not hasattr(result, "match_type")
    assert not hasattr(result, "is_verified")
    assert not hasattr(result, "confidence")


# ---------------------------------------------------------------------------
# SearchResult — raw material stays opaque
# ---------------------------------------------------------------------------


def test_raw_reference_is_preserved_verbatim() -> None:
    """Not trimmed, not parsed: it is the artifact a fixture is compared against."""
    raw = '  {"title": "ABC123-X", "extra": [1, 2]}\n'
    result = a_result(raw_reference=raw)

    assert result.raw_reference == raw


def test_raw_reference_must_be_an_opaque_string_not_a_vendor_payload() -> None:
    """A dict here would invite business logic to read a vendor-specific key."""
    with pytest.raises(TypeError):
        a_result(raw_reference={"organic": [{"link": RESULT_URL}]})


def test_an_empty_raw_reference_is_absent() -> None:
    assert a_result(raw_reference="").raw_reference is None


def test_a_result_is_immutable() -> None:
    result = a_result(title="ABC123-X")

    with pytest.raises(FrozenInstanceError):
        result.title = "something else"  # type: ignore[misc]


# ---------------------------------------------------------------------------
# SearchResponse — provenance, time, and the batch
# ---------------------------------------------------------------------------


def test_a_response_carries_its_provider_query_and_retrieval_time() -> None:
    query = SearchQuery(text="ABC123-X price")
    response = SearchResponse(
        provider_id="example-search",
        query=query,
        retrieved_at=RETRIEVED_AT,
        results=[a_result(title="ABC123-X at Example")],
        raw_response_reference='{"status": "ok"}',
    )

    assert response.provider_id == "example-search"
    assert response.query == query
    assert response.query.text == "ABC123-X price"
    assert response.retrieved_at == RETRIEVED_AT
    assert response.result_count == 1
    assert response.raw_response_reference == '{"status": "ok"}'


@pytest.mark.parametrize("provider_id", ["", "   "])
def test_a_response_requires_provider_provenance(provider_id: str) -> None:
    """An observation with no attribution cannot be traced to anything."""
    with pytest.raises(ValueError):
        SearchResponse(
            provider_id=provider_id,
            query=SearchQuery(text="ABC123-X"),
            retrieved_at=RETRIEVED_AT,
        )


def test_provider_id_is_runtime_data_and_not_a_vocabulary() -> None:
    """Any adapter-supplied string is accepted; the boundary enumerates no vendor."""
    for provider_id in ("provider-a", "provider-b", "internal-distributor-feed"):
        response = SearchResponse(
            provider_id=provider_id,
            query=SearchQuery(text="ABC123-X"),
            retrieved_at=RETRIEVED_AT,
        )
        assert response.provider_id == provider_id


def test_a_naive_retrieval_time_is_rejected() -> None:
    """A retrieval time without an offset cannot be compared with another."""
    with pytest.raises(ValueError):
        SearchResponse(
            provider_id="example-search",
            query=SearchQuery(text="ABC123-X"),
            retrieved_at=datetime(2026, 3, 4, 5, 6, 7),
        )


def test_a_non_utc_timezone_aware_retrieval_time_is_accepted() -> None:
    retrieved_at = datetime(
        2026, 3, 4, 5, 6, 7, tzinfo=timezone(timedelta(hours=-5))
    )
    response = SearchResponse(
        provider_id="example-search",
        query=SearchQuery(text="ABC123-X"),
        retrieved_at=retrieved_at,
    )

    assert response.retrieved_at == retrieved_at


def test_retrieval_time_must_be_a_datetime() -> None:
    with pytest.raises(TypeError):
        SearchResponse(
            provider_id="example-search",
            query=SearchQuery(text="ABC123-X"),
            retrieved_at="2026-03-04T05:06:07Z",  # type: ignore[arg-type]
        )


def test_the_query_round_trips_and_must_be_a_query() -> None:
    with pytest.raises(TypeError):
        SearchResponse(
            provider_id="example-search",
            query="ABC123-X",  # type: ignore[arg-type]
            retrieved_at=RETRIEVED_AT,
        )


def test_zero_results_is_a_valid_answer() -> None:
    """A provider finding nothing is information, not a failure."""
    response = SearchResponse(
        provider_id="example-search",
        query=SearchQuery(text="ABC123-X"),
        retrieved_at=RETRIEVED_AT,
    )

    assert response.results == ()
    assert response.result_count == 0


def test_results_are_stored_as_an_immutable_tuple() -> None:
    results = [a_result(title="one"), a_result(title="two")]
    response = SearchResponse(
        provider_id="example-search",
        query=SearchQuery(text="ABC123-X"),
        retrieved_at=RETRIEVED_AT,
        results=results,
    )

    assert isinstance(response.results, tuple)
    assert response.result_count == 2

    results.append(a_result(title="three"))
    assert response.result_count == 2, "the response copied the sequence it was given"

    with pytest.raises(TypeError):
        response.results[0] = a_result()  # type: ignore[index]


def test_every_result_must_be_a_search_result() -> None:
    with pytest.raises(TypeError):
        SearchResponse(
            provider_id="example-search",
            query=SearchQuery(text="ABC123-X"),
            retrieved_at=RETRIEVED_AT,
            results=[a_result(), {"source_url": RESULT_URL}],  # type: ignore[list-item]
        )


def test_a_bare_string_is_not_a_result_sequence() -> None:
    with pytest.raises(TypeError):
        SearchResponse(
            provider_id="example-search",
            query=SearchQuery(text="ABC123-X"),
            retrieved_at=RETRIEVED_AT,
            results="not results",  # type: ignore[arg-type]
        )


def test_the_response_contract_carries_no_vendor_specific_field() -> None:
    assert [field.name for field in fields(SearchResponse)] == [
        "provider_id",
        "query",
        "retrieved_at",
        "results",
        "raw_response_reference",
    ]


def test_a_response_raw_reference_is_preserved_verbatim_and_opaque() -> None:
    raw = '{"meta": {"credits_used": 1}}\n'
    response = SearchResponse(
        provider_id="example-search",
        query=SearchQuery(text="ABC123-X"),
        retrieved_at=RETRIEVED_AT,
        raw_response_reference=raw,
    )

    assert response.raw_response_reference == raw

    with pytest.raises(TypeError):
        SearchResponse(
            provider_id="example-search",
            query=SearchQuery(text="ABC123-X"),
            retrieved_at=RETRIEVED_AT,
            raw_response_reference={"meta": {"credits_used": 1}},  # type: ignore[arg-type]
        )


# ---------------------------------------------------------------------------
# The boundary exception
# ---------------------------------------------------------------------------


def test_the_boundary_has_one_failure_concept() -> None:
    """One base, until a real provider shows what its failures actually are."""
    assert issubclass(SearchProviderError, Exception)
    assert SearchProviderError.__subclasses__() == []


def test_contract_misuse_is_not_a_provider_failure() -> None:
    """Invalid construction is a caller defect, not a failed external call."""
    with pytest.raises(ValueError) as blank_query:
        SearchQuery(text="")
    with pytest.raises(ValueError) as bad_url:
        a_result(source_url="javascript:alert(1)")

    assert not isinstance(blank_query.value, SearchProviderError)
    assert not isinstance(bad_url.value, SearchProviderError)
