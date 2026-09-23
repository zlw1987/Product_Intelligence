"""Orchestration integration tests for PRODUCT-INTEL.4D-D.

Proves the execution-layer wiring of alias-authority acquisition into
``execute_research_run``:

* direct-sufficient runs: zero Micron authority fetch, zero Serper,
  no alias snapshot;
* eligible fallback: exactly ONE reviewed catalog fetch, the bounded
  alias audit persisted BEFORE the paid search, exactly ONE
  ``SearchProvider.search()``, the exact deterministic alias-expanded
  query for each BASE/R/T request form;
* bounded non-ESTABLISHED authority: snapshot persisted, ordinary
  frozen query, exactly ONE search;
* empty-MPN runs: no alias acquisition, ordinary description search,
  no snapshot;
* search failure after established eligibility: run FAILED, alias
  audit snapshot survives;
* alias snapshot persistence failure: propagates to the catastrophic
  boundary, run FAILED, search never issued;
* semantic firewall: with an ESTABLISHED alias-expanded search, ALL
  non-deterministically-ACCEPTED search-batch assessments do NOT reach
  ``evaluate_semantic_matches`` (proven with a spy boundary that WOULD
  match them), while direct and ordinary non-alias rejected assessments
  retain existing semantic behavior, and the deterministic exact
  requested-MPN assessment still enters normal frozen 4A.
"""

from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from django.db import OperationalError

from product_intelligence.domain import ResearchRequest
from product_intelligence.domain.enums import (
    EvidenceDecision,
    ResearchRunState,
)
from product_intelligence.execution import ExecutionError, execute_research_run
from product_intelligence.execution import orchestration as orchestration_module
from product_intelligence.execution.semantic_integration import (
    AiAssistedMatchResult,
    _has_usable_evidence,
    _is_semantic_eligible,
)
from product_intelligence.providers.page import (
    FetchedPage,
    PageFetchError,
    PageFetcher,
    PageFetchRequest,
)
from product_intelligence.providers.search import (
    SearchProvider,
    SearchQuery,
    SearchResponse,
    SearchResult,
)
from product_intelligence.research.micron_alias_codec import (
    decode_micron_alias_snapshot,
)
from product_intelligence.research.micron_packaging_alias import (
    MICRON_7500_REQUESTED_CATALOG_URL,
    MicronAliasEligibilityStatus,
)
from product_intelligence.research.price_result_codec import (
    decode_price_aggregation_result,
)
from product_intelligence.runs.models import (
    AiAssistedReviewCandidate,
    ResearchMicronAliasSnapshot,
    ResearchRun,
)
from product_intelligence.semantic.contract import ConfidenceLevel, SemanticDecision
from product_intelligence.semantic.runtime import (
    PRIMARY_MODEL,
    PRIMARY_PROVIDER,
    SemanticAttempt,
    SemanticAttemptStatus,
    SemanticRuntimeResult,
)

pytestmark = pytest.mark.django_db

BASE = "MTFDKCC3T8TGP-1BK1DABYY"
BASER = f"{BASE}R"
BASET = f"{BASE}T"
CATALOG_URL = MICRON_7500_REQUESTED_CATALOG_URL
FIXTURES = Path(__file__).resolve().parents[1] / "fixtures" / "pages"

# Frozen alias relation order (family order: base, R form, T form; the
# requested form excluded from its own alias list).
RELATION_ALIASES = {
    BASE: (BASER, BASET),
    BASER: (BASE, BASET),
    BASET: (BASE, BASER),
}


# ---------------------------------------------------------------------------
# Builders
# ---------------------------------------------------------------------------


def _catalog_body() -> str:
    return (FIXTURES / "micron_7500_part_catalog.json").read_text(
        encoding="utf-8"
    )


def _product_page(
    title: str,
    *,
    mpn: str | None = None,
    sku: str | None = None,
    price: str | None = None,
    currency: str = "USD",
) -> str:
    """One JSON-LD Product page. Absent mpn/sku/price -> field omitted."""
    product: dict = {"@context": "https://schema.org", "@type": "Product"}
    if title:
        product["name"] = title
    if mpn is not None:
        product["mpn"] = mpn
    if sku is not None:
        product["sku"] = sku
    if price is not None:
        product["offers"] = {
            "@type": "Offer",
            "price": price,
            "priceCurrency": currency,
            "availability": "https://schema.org/InStock",
            "itemCondition": "https://schema.org/NewCondition",
        }
    return (
        '<html><head><script type="application/ld+json">'
        + json.dumps(product)
        + "</script></head><body></body></html>"
    )


def _empty_page() -> str:
    return "<html><head></head><body>no listings</body></html>"


def _routed_page_fetcher(routes: "dict[str, str]"):
    """Fake PageFetcher: exact-URL routes, empty page otherwise.

    Returns (fetcher, fetched_urls) where fetched_urls records every
    requested URL in call order.
    """
    fetched_urls: list = []

    def side_effect(request: PageFetchRequest) -> FetchedPage:
        fetched_urls.append(request.url)
        body = routes.get(request.url, _empty_page())
        return FetchedPage(
            requested_url=request.url,
            final_url=request.url,
            retrieved_at=datetime.now(tz=timezone.utc),
            status_code=200,
            body_text=body,
            content_type="application/json"
            if request.url == CATALOG_URL
            else "text/html",
            body_byte_count=len(body.encode("utf-8")),
            redirect_count=0,
            fetcher_id="test",
        )

    fetcher = MagicMock(spec=PageFetcher)
    fetcher.fetch.side_effect = side_effect
    return fetcher, fetched_urls


def _search_provider(urls: "tuple[str, ...]") -> "MagicMock":
    provider = MagicMock(spec=SearchProvider)
    provider.search.return_value = SearchResponse(
        provider_id="test",
        query=SearchQuery(text="unused"),
        retrieved_at=datetime.now(tz=timezone.utc),
        results=tuple(SearchResult(source_url=u) for u in urls),
    )
    return provider


def _make_run(mpn: str, description: str = "Micron 7500 3.84TB datacenter SSD") -> ResearchRun:
    return ResearchRun.objects.create_from_request(
        ResearchRequest(manufacturer_part_number=mpn, description=description)
    )


@pytest.fixture
def no_preferred_or_vendor_env(monkeypatch) -> None:
    """Deterministic environment: no direct acquisition, no vendor lookup."""
    monkeypatch.delenv("PI_PREFERRED_SEARCH_DOMAINS", raising=False)
    monkeypatch.delenv("PI_VENDOR_LOOKUP_BASE_URL", raising=False)


# ---------------------------------------------------------------------------
# Spy semantic boundary: WOULD match every eligible rejected assessment
# ---------------------------------------------------------------------------


def _install_spy_semantic(recorded: list) -> "patch":
    def spy(request, assessments, evidence_writer, runtime=None):
        recorded.extend(assessments)
        matches = []
        for assessment in assessments:
            if not _is_semantic_eligible(assessment):
                continue
            if not _has_usable_evidence(assessment):
                continue
            obs = assessment.normalized_listing.observation
            semantic_result = SemanticRuntimeResult(
                case_id=f"spy-{len(matches) + 1}",
                target_mpn=assessment.requested_part_number,
                target_description=request.description,
                candidate_title=obs.product_title or "",
                candidate_mpn_field=(
                    obs.manufacturer_part_number_text
                    if obs.manufacturer_part_number_text
                    else None
                ),
                candidate_sku=obs.sku_text if obs.sku_text else None,
                candidate_specs="",
                evidence_source=assessment.candidate_evidence_source.value,
                requested_primary_provider=PRIMARY_PROVIDER,
                requested_primary_model=PRIMARY_MODEL,
                attempts=(
                    SemanticAttempt(
                        provider=PRIMARY_PROVIDER,
                        model=PRIMARY_MODEL,
                        status=SemanticAttemptStatus.OK,
                        latency_ms=1.0,
                    ),
                ),
                fallback_used=False,
                fallback_reason=None,
                actual_provider=PRIMARY_PROVIDER,
                actual_model=PRIMARY_MODEL,
                decision=SemanticDecision.MATCH,
                confidence=ConfidenceLevel.HIGH,
                matched_attributes=("mpn",),
                conflicting_attributes=(),
                missing_critical_attributes=(),
                reason_code="SPY_MATCH",
                error_type=None,
            )
            matches.append(
                AiAssistedMatchResult(
                    original_assessment=assessment,
                    semantic_result=semantic_result,
                    disposition=EvidenceDecision.AI_ASSISTED_MATCH,
                )
            )
        return tuple(matches)

    return patch.object(orchestration_module, "evaluate_semantic_matches", spy)


# ---------------------------------------------------------------------------
# 1. Direct-sufficient: zero alias authority work
# ---------------------------------------------------------------------------


class TestDirectSufficientNoAlias:
    def test_zero_alias_fetch_zero_serper_no_snapshot(
        self, no_preferred_or_vendor_env: None
    ) -> None:
        from product_intelligence.providers.directmacro import DirectMacroLocator
        from product_intelligence.providers.direct_source import DirectSourceQuery

        direct_url = DirectMacroLocator().locate(
            DirectSourceQuery(manufacturer_part_number=BASER)
        )[0].url

        fetcher, fetched_urls = _routed_page_fetcher(
            {direct_url: _product_page("Micron 7500 3.84TB", mpn=BASER, price="2500.00")}
        )
        provider = _search_provider(())
        run = _make_run(BASER)

        with patch.dict(os.environ, {"PI_PREFERRED_SEARCH_DOMAINS": "directmacro.com"}):
            result = execute_research_run(
                str(run.id), search_provider=provider, page_fetcher=fetcher
            )

        assert result.run.current_state is ResearchRunState.COMPLETED
        # Direct evidence sufficient: no paid search, no alias snapshot.
        provider.search.assert_not_called()
        assert CATALOG_URL not in fetched_urls
        assert ResearchMicronAliasSnapshot.objects.filter(run=run).count() == 0
        # The direct acceptance still produces the ordinary frozen bucket.
        decoded = decode_price_aggregation_result(
            result.snapshot.payload, schema_version=result.snapshot.schema_version
        )
        assert len(decoded.buckets) == 1


# ---------------------------------------------------------------------------
# 2. Eligible fallback: established alias-expanded search
# ---------------------------------------------------------------------------


class TestEligibleFallbackEstablished:
    @pytest.mark.parametrize("mpn", [BASE, BASER, BASET])
    def test_established_alias_expanded_query_single_search(
        self, no_preferred_or_vendor_env: None, mpn: str
    ) -> None:
        fetcher, fetched_urls = _routed_page_fetcher({CATALOG_URL: _catalog_body()})
        provider = _search_provider(())
        run = _make_run(mpn)

        result = execute_research_run(
            str(run.id), search_provider=provider, page_fetcher=fetcher
        )

        assert result.run.current_state is ResearchRunState.COMPLETED
        # Exactly one reviewed catalog fetch; no other page fetch.
        assert fetched_urls == [CATALOG_URL]
        # Exactly one search with the exact deterministic alias-expanded
        # query: one parenthesized OR group (requested MPN first, then the
        # established aliases in deterministic relation order) plus the
        # ordinary description. Frozen 4D-D shape — an AND grouping would
        # require every identifier simultaneously and defeat recall.
        provider.search.assert_called_once()
        sent_query = provider.search.call_args.args[0]
        quoted = [f'"{mpn}"'] + [f'"{alias}"' for alias in RELATION_ALIASES[mpn]]
        grouped = "(" + " OR ".join(quoted) + ")"
        expected = grouped + " Micron 7500 3.84TB datacenter SSD"
        assert sent_query.text == expected

        # The bounded alias audit was persisted and is ESTABLISHED.
        snapshot = ResearchMicronAliasSnapshot.objects.get(run=run)
        assert snapshot.schema_version == 1
        decoded_alias = decode_micron_alias_snapshot(
            snapshot.payload, schema_version=snapshot.schema_version
        )
        assert decoded_alias.status is MicronAliasEligibilityStatus.ESTABLISHED
        assert decoded_alias.matched_base_mpn == BASE
        assert decoded_alias.request == run.to_research_request()

    def test_snapshot_persisted_before_search(
        self, no_preferred_or_vendor_env: None
    ) -> None:
        fetcher, _ = _routed_page_fetcher({CATALOG_URL: _catalog_body()})
        run = _make_run(BASER)
        snapshot_count_at_search = []

        def search_side_effect(query: SearchQuery) -> SearchResponse:
            snapshot_count_at_search.append(
                ResearchMicronAliasSnapshot.objects.filter(run=run).count()
            )
            return SearchResponse(
                provider_id="test",
                query=query,
                retrieved_at=datetime.now(tz=timezone.utc),
                results=(),
            )

        provider = MagicMock(spec=SearchProvider)
        provider.search.side_effect = search_side_effect

        execute_research_run(
            str(run.id), search_provider=provider, page_fetcher=fetcher
        )
        assert snapshot_count_at_search == [1]

    def test_query_deterministic_across_runs(
        self, no_preferred_or_vendor_env: None
    ) -> None:
        seen_queries = []
        for _ in range(2):
            fetcher, _ = _routed_page_fetcher({CATALOG_URL: _catalog_body()})
            run = _make_run(BASET)

            def record_query(query: SearchQuery, _seen=seen_queries) -> SearchResponse:
                _seen.append(query.text)
                return SearchResponse(
                    provider_id="test",
                    query=query,
                    retrieved_at=datetime.now(tz=timezone.utc),
                    results=(),
                )

            provider = MagicMock(spec=SearchProvider)
            provider.search.side_effect = record_query
            execute_research_run(
                str(run.id), search_provider=provider, page_fetcher=fetcher
            )
        assert seen_queries[0] == seen_queries[1]
        # Frozen OR shape: requested MPN first, aliases in relation order.
        assert seen_queries[0] == (
            f'("{BASET}" OR "{BASE}" OR "{BASER}") '
            "Micron 7500 3.84TB datacenter SSD"
        )


# ---------------------------------------------------------------------------
# 3. Bounded non-established authority: ordinary query, one search
# ---------------------------------------------------------------------------


class TestBoundedAuthorityFailure:
    def test_fetch_failed_bounded_ordinary_query_single_search(
        self, no_preferred_or_vendor_env: None
    ) -> None:
        fetched_urls: list = []

        def side_effect(request: PageFetchRequest) -> FetchedPage:
            fetched_urls.append(request.url)
            if request.url == CATALOG_URL:
                raise PageFetchError("catalog down")
            return FetchedPage(
                requested_url=request.url,
                final_url=request.url,
                retrieved_at=datetime.now(tz=timezone.utc),
                status_code=200,
                body_text=_empty_page(),
                content_type="text/html",
                body_byte_count=10,
                redirect_count=0,
                fetcher_id="test",
            )

        fetcher = MagicMock(spec=PageFetcher)
        fetcher.fetch.side_effect = side_effect
        provider = _search_provider(())
        run = _make_run(BASER)

        result = execute_research_run(
            str(run.id), search_provider=provider, page_fetcher=fetcher
        )

        assert result.run.current_state is ResearchRunState.COMPLETED
        provider.search.assert_called_once()
        assert (
            provider.search.call_args.args[0].text
            == f'"{BASER}" Micron 7500 3.84TB datacenter SSD'
        )
        snapshot = ResearchMicronAliasSnapshot.objects.get(run=run)
        decoded_alias = decode_micron_alias_snapshot(
            snapshot.payload, schema_version=snapshot.schema_version
        )
        assert decoded_alias.status is MicronAliasEligibilityStatus.FETCH_FAILED

    def test_parse_failed_bounded_ordinary_query_single_search(
        self, no_preferred_or_vendor_env: None
    ) -> None:
        fetcher, _ = _routed_page_fetcher({CATALOG_URL: "<html>not json</html>"})
        provider = _search_provider(())
        run = _make_run(BASER)

        result = execute_research_run(
            str(run.id), search_provider=provider, page_fetcher=fetcher
        )

        assert result.run.current_state is ResearchRunState.COMPLETED
        provider.search.assert_called_once()
        assert (
            provider.search.call_args.args[0].text
            == f'"{BASER}" Micron 7500 3.84TB datacenter SSD'
        )
        decoded_alias = decode_micron_alias_snapshot(
            ResearchMicronAliasSnapshot.objects.get(run=run).payload,
            schema_version=1,
        )
        assert decoded_alias.status is MicronAliasEligibilityStatus.PARSE_FAILED

    def test_no_authority_match_bounded_ordinary_query_single_search(
        self, no_preferred_or_vendor_env: None
    ) -> None:
        fetcher, _ = _routed_page_fetcher({CATALOG_URL: _catalog_body()})
        provider = _search_provider(())
        run = _make_run("NOT-IN-CATALOG")

        result = execute_research_run(
            str(run.id), search_provider=provider, page_fetcher=fetcher
        )

        assert result.run.current_state is ResearchRunState.COMPLETED
        provider.search.assert_called_once()
        assert (
            provider.search.call_args.args[0].text
            == '"NOT-IN-CATALOG" Micron 7500 3.84TB datacenter SSD'
        )
        decoded_alias = decode_micron_alias_snapshot(
            ResearchMicronAliasSnapshot.objects.get(run=run).payload,
            schema_version=1,
        )
        assert decoded_alias.status is MicronAliasEligibilityStatus.NO_AUTHORITY_MATCH


# ---------------------------------------------------------------------------
# 4. Empty MPN: no alias acquisition at all
# ---------------------------------------------------------------------------


class TestEmptyMpn:
    def test_no_alias_acquisition_ordinary_description_search(
        self, no_preferred_or_vendor_env: None
    ) -> None:
        fetcher, fetched_urls = _routed_page_fetcher({})
        provider = _search_provider(())
        run = _make_run("", description="some generic server drive")

        result = execute_research_run(
            str(run.id), search_provider=provider, page_fetcher=fetcher
        )

        assert result.run.current_state is ResearchRunState.COMPLETED
        provider.search.assert_called_once()
        assert provider.search.call_args.args[0].text == "some generic server drive"
        assert CATALOG_URL not in fetched_urls
        assert ResearchMicronAliasSnapshot.objects.filter(run=run).count() == 0


# ---------------------------------------------------------------------------
# 5. Search failure after established eligibility
# ---------------------------------------------------------------------------


class TestSearchFailureAfterEstablished:
    def test_run_fails_alias_snapshot_survives(
        self, no_preferred_or_vendor_env: None
    ) -> None:
        fetcher, _ = _routed_page_fetcher({CATALOG_URL: _catalog_body()})
        provider = MagicMock(spec=SearchProvider)
        provider.search.side_effect = RuntimeError("search exploded")
        run = _make_run(BASE)

        with pytest.raises(ExecutionError):
            execute_research_run(
                str(run.id), search_provider=provider, page_fetcher=fetcher
            )

        run.refresh_from_db()
        assert run.current_state is ResearchRunState.FAILED
        snapshot = ResearchMicronAliasSnapshot.objects.get(run=run)
        decoded_alias = decode_micron_alias_snapshot(
            snapshot.payload, schema_version=snapshot.schema_version
        )
        assert decoded_alias.status is MicronAliasEligibilityStatus.ESTABLISHED
        assert decoded_alias.matched_base_mpn == BASE


# ---------------------------------------------------------------------------
# 6. Alias snapshot persistence failure propagates
# ---------------------------------------------------------------------------


class TestSnapshotPersistenceFailure:
    def test_persistence_failure_propagates_search_never_issued(
        self, no_preferred_or_vendor_env: None
    ) -> None:
        fetcher, _ = _routed_page_fetcher({CATALOG_URL: _catalog_body()})
        provider = _search_provider(())
        run = _make_run(BASER)

        with patch.object(
            ResearchMicronAliasSnapshot.objects,
            "create",
            side_effect=OperationalError("simulated DB persistence failure"),
        ):
            with pytest.raises(ExecutionError):
                execute_research_run(
                    str(run.id), search_provider=provider, page_fetcher=fetcher
                )

        run.refresh_from_db()
        assert run.current_state is ResearchRunState.FAILED
        provider.search.assert_not_called()
        assert ResearchMicronAliasSnapshot.objects.filter(run=run).count() == 0


# ---------------------------------------------------------------------------
# 7. Semantic firewall (ESTABLISHED alias-expanded search)
# ---------------------------------------------------------------------------


class TestSemanticFirewall:
    def test_rejected_alias_search_assessments_do_not_reach_semantic(
        self, no_preferred_or_vendor_env: None
    ) -> None:
        # Request BASER -> ESTABLISHED. Search batch pages:
        #  a) BASE sibling published in SKU field  -> semantic-eligible reject
        #  b) BASET sibling published in SKU field -> semantic-eligible reject
        #  c) title-only page (BASER token)        -> semantic-eligible reject
        #  d) exact requested MPN + price          -> deterministic ACCEPTED
        routes = {
            CATALOG_URL: _catalog_body(),
            "https://sibling-base.example/p1": _product_page(
                "Micron 7500 3.84TB datacenter SSD", sku=BASE, price="2400.00"
            ),
            "https://sibling-baset.example/p2": _product_page(
                "Micron 7500 3.84TB datacenter SSD", sku=BASET, price="2410.00"
            ),
            "https://title-only.example/p3": _product_page(
                f"Micron 7500 {BASER} 3.84TB SSD", price="2420.00"
            ),
            "https://exact.example/p4": _product_page(
                "Micron 7500 3.84TB datacenter SSD", mpn=BASER, price="2500.00"
            ),
        }
        fetcher, _ = _routed_page_fetcher(routes)
        provider = _search_provider(
            (
                "https://sibling-base.example/p1",
                "https://sibling-baset.example/p2",
                "https://title-only.example/p3",
                "https://exact.example/p4",
            )
        )
        recorded: list = []
        run = _make_run(BASER)

        with _install_spy_semantic(recorded):
            result = execute_research_run(
                str(run.id), search_provider=provider, page_fetcher=fetcher
            )

        assert result.run.current_state is ResearchRunState.COMPLETED
        # The spy boundary WOULD match: the only assessment it may lawfully
        # see from the search batch is the deterministic ACCEPTED one.
        assert len(recorded) == 1
        assert recorded[0].decision is EvidenceDecision.ACCEPTED
        assert "exact.example" in recorded[0].normalized_listing.observation.source_url
        # Zero AI_ASSISTED_MATCH and zero review candidates from the
        # rejected alias sibling/base/title assessments.
        assert result.ai_assisted_matches == ()
        assert AiAssistedReviewCandidate.objects.filter(run=run).count() == 0

        # The rejected assessments remain in total_assessments, frozen 4A
        # exclusions, and the persisted PriceAggregationResult.
        decoded = decode_price_aggregation_result(
            result.snapshot.payload, schema_version=result.snapshot.schema_version
        )
        assert len(decoded.assessments) == 4
        assert len(decoded.exclusions) == 3
        assert len(decoded.buckets) == 1
        bucket = decoded.buckets[0]
        assert bucket.assessments[0].decision is EvidenceDecision.ACCEPTED
        assert bucket.low == bucket.high
        assert str(bucket.low) in ("2500.00", "2500")
        excluded_urls = {
            e.assessment.normalized_listing.observation.source_url for e in decoded.exclusions
        }
        assert excluded_urls == {
            "https://sibling-base.example/p1",
            "https://sibling-baset.example/p2",
            "https://title-only.example/p3",
        }

    def test_ordinary_non_alias_search_retains_semantic_behavior(
        self, no_preferred_or_vendor_env: None
    ) -> None:
        # Non-7500 MPN -> bounded NO_AUTHORITY_MATCH -> ordinary query ->
        # the semantic firewall must NOT apply: an eligible rejected
        # search-batch assessment reaches the spy and yields a review
        # candidate (existing frozen behavior).
        routes = {
            CATALOG_URL: _catalog_body(),
            "https://retailer.example/item": _product_page(
                "Generic SSD product", sku="OTHER-SKU-1", price="99.00"
            ),
        }
        fetcher, _ = _routed_page_fetcher(routes)
        provider = _search_provider(("https://retailer.example/item",))
        recorded: list = []
        run = _make_run("MZ-QL23T800", description="Samsung SSD 970 EVO Plus 1TB")

        with _install_spy_semantic(recorded):
            result = execute_research_run(
                str(run.id), search_provider=provider, page_fetcher=fetcher
            )

        assert result.run.current_state is ResearchRunState.COMPLETED
        decoded_alias = decode_micron_alias_snapshot(
            ResearchMicronAliasSnapshot.objects.get(run=run).payload,
            schema_version=1,
        )
        assert decoded_alias.status is MicronAliasEligibilityStatus.NO_AUTHORITY_MATCH
        # Firewall off: the eligible rejected search assessment reached
        # semantic evaluation and produced the existing behavior.
        assert len(recorded) == 1
        assert recorded[0].decision is EvidenceDecision.REJECTED
        assert len(result.ai_assisted_matches) == 1
        candidates = AiAssistedReviewCandidate.objects.filter(run=run)
        assert candidates.count() == 1
        assert candidates.first().source_url == "https://retailer.example/item"

    def test_direct_rejected_assessments_retain_semantic_behavior(
        self, no_preferred_or_vendor_env: None
    ) -> None:
        # Direct (4D-A) acquisition is eligible for the firewall exemption:
        # its rejected assessments keep existing semantic behavior even when
        # the fallback search was ESTABLISHED alias-expanded.
        from product_intelligence.providers.directmacro import DirectMacroLocator
        from product_intelligence.providers.direct_source import DirectSourceQuery

        direct_url = DirectMacroLocator().locate(
            DirectSourceQuery(manufacturer_part_number=BASER)
        )[0].url

        routes = {
            CATALOG_URL: _catalog_body(),
            # Direct page: SKU-only sibling (BASE) -> semantic-eligible reject.
            direct_url: _product_page("Micron 7500 3.84TB datacenter SSD", sku=BASE),
        }
        fetcher, _ = _routed_page_fetcher(routes)
        provider = _search_provider(())  # fallback finds nothing new
        recorded: list = []
        run = _make_run(BASER)

        with (
            patch.dict(os.environ, {"PI_PREFERRED_SEARCH_DOMAINS": "directmacro.com"}),
            _install_spy_semantic(recorded),
        ):
            result = execute_research_run(
                str(run.id), search_provider=provider, page_fetcher=fetcher
            )

        assert result.run.current_state is ResearchRunState.COMPLETED
        provider.search.assert_called_once()
        # The DIRECT rejected assessment reached the semantic boundary.
        direct_recorded = [
            a for a in recorded
            if "directmacro.com" in a.normalized_listing.observation.source_url
        ]
        assert len(direct_recorded) == 1
        assert direct_recorded[0].decision is EvidenceDecision.REJECTED
        assert len(result.ai_assisted_matches) == 1
        candidate = AiAssistedReviewCandidate.objects.get(run=run)
        assert "directmacro.com" in candidate.source_url
