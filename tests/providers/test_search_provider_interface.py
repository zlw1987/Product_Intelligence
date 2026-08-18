"""The `SearchProvider` interface, exercised with a fake (PRODUCT-INTEL.2B).

A fake is the only implementation that may exist in this phase. It proves three
things and nothing more: that the protocol is satisfiable by shape alone, that
one call returns a `SearchResponse`, and that no network, credential, or vendor
package is involved in either.

The fake is **not** a recorded fixture and must not be mistaken for one. It
returns values invented for a test, so it can only demonstrate the interface —
never that a real provider's payload maps correctly onto these contracts. That
is 2C's job, with sanitized recordings of real responses.
"""

from __future__ import annotations

from datetime import datetime, timezone

import pytest

from product_intelligence.providers import (
    SearchProvider,
    SearchProviderError,
    SearchQuery,
    SearchResponse,
    SearchResult,
)

RETRIEVED_AT = datetime(2026, 3, 4, 5, 6, 7, tzinfo=timezone.utc)


class FakeSearchProvider:
    """Conforms to `SearchProvider` structurally: it inherits nothing."""

    provider_id = "fake-provider"

    def __init__(self, results: tuple[SearchResult, ...] = ()) -> None:
        self._results = results
        self.calls: list[SearchQuery] = []

    def search(self, query: SearchQuery) -> SearchResponse:
        self.calls.append(query)
        return SearchResponse(
            provider_id=self.provider_id,
            query=query,
            retrieved_at=RETRIEVED_AT,
            results=self._results,
            raw_response_reference='{"fake": true}',
        )


class FailingSearchProvider:
    def search(self, query: SearchQuery) -> SearchResponse:
        raise SearchProviderError("the fake provider was asked to fail")


def run_one_search(provider: SearchProvider, query: SearchQuery) -> SearchResponse:
    """A caller written against the boundary, not against an implementation."""
    return provider.search(query)


def test_a_fake_satisfies_the_protocol_without_inheriting_anything() -> None:
    assert FakeSearchProvider.__bases__ == (object,)
    assert callable(FakeSearchProvider().search)


def test_calling_through_the_boundary_returns_a_response() -> None:
    provider = FakeSearchProvider(
        results=(
            SearchResult(
                source_url="https://example.invalid/p/1",
                title="ABC123-X 24-port switch",
                price_hint_text="$399.99",
                part_number_hint="ABC123-X",
                raw_reference='{"position": 1}',
            ),
        )
    )
    query = SearchQuery(text="ABC123-X price")

    response = run_one_search(provider, query)

    assert isinstance(response, SearchResponse)
    assert response.query is query
    assert response.provider_id == "fake-provider"
    assert response.result_count == 1
    assert response.results[0].price_hint_text == "$399.99"
    assert provider.calls == [query]


def test_a_provider_may_legitimately_return_nothing() -> None:
    response = run_one_search(FakeSearchProvider(), SearchQuery(text="ABC123-X"))

    assert response.results == ()
    assert response.result_count == 0


def test_a_failing_provider_raises_the_boundary_exception() -> None:
    with pytest.raises(SearchProviderError):
        run_one_search(FailingSearchProvider(), SearchQuery(text="ABC123-X"))


def test_the_interface_is_synchronous_and_has_one_method() -> None:
    """One method, no async variant, and no lifecycle to implement.

    A second entry point — `close`, `configure`, `health_check`, a batch call —
    would be designed before any implementation exists. 2C adds what a real
    provider turns out to need.
    """
    import inspect

    public = [
        name
        for name in vars(SearchProvider)
        if not name.startswith("_") and callable(vars(SearchProvider)[name])
    ]

    assert public == ["search"]
    assert not inspect.iscoroutinefunction(SearchProvider.search)


def test_the_boundary_does_not_compare_part_numbers_for_the_caller() -> None:
    """A provider observes; the research core decides what a hint establishes.

    The published hint arrives unchanged and unjudged. Comparing it is a
    deliberate, separate step taken by a caller that also owns the rejection —
    demonstrated here rather than performed by the provider.
    """
    from product_intelligence.domain import IdentityMatchType
    from product_intelligence.research.identity import compare_part_numbers

    provider = FakeSearchProvider(
        results=(
            SearchResult(
                source_url="https://example.invalid/p/1",
                part_number_hint="abc123 x",
            ),
        )
    )

    response = run_one_search(provider, SearchQuery(text="ABC123-X"))
    hint = response.results[0].part_number_hint

    assert hint == "abc123 x", "the provider stored the hint as published"
    assessment = compare_part_numbers("ABC123-X", hint)
    assert assessment.match_type is IdentityMatchType.NORMALIZED_EXACT
