"""Deterministic regression for PRODUCT-INTEL.PUBLIC-RESEARCH-RECALL-FU1.

Production request (request ID
bb280c99-7b75-445e-b476-f612cadc1b27):

    MPN:         MTC20F2085S1RC64BH1T
    Description: Micron 32GB DDR5-6400 ECC 2Rx8 RDIMM CL52 Tray

Defect: the one paid search issued the blended query
``"<MPN>" <description>``. Search engines treat the quoted phrase as a soft
ranking signal; the high-document-frequency description terms let the engine
replace exact-MPN retrieval with broad "Micron 32GB DDR5" matches (the
production response contained only generic aggregator pages, all correctly
rejected NO_EXPLICIT_MPN_EVIDENCE), and the adapter relied on the provider's
default 10-result page, truncating the candidate set at the wire.

This suite reproduces the defect boundary at the REAL orchestration
pipeline (``execute_research_run``) with controlled provider/search
fixtures — no live internet:

* the paid query for an explicit-MPN request is the exact-MPN phrase, a
  first-class retrieval path (the description is not a co-ranked term and
  therefore has no channel to displace exact-MPN results);
* exact-requested-MPN candidates are NOT displaced by broad description
  candidates — even ranked LAST in the response they reach the identity
  pipeline and are ACCEPTED on their explicit MPN field;
* generic "Micron 32GB DDR5" candidates still fail closed
  (NO_EXPLICIT_MPN_EVIDENCE) — recall was improved without weakening the
  frozen 3C identity gate;
* explicit conflicting MPNs still fail closed (MPN_MISMATCH) — including
  the T-stripped base form, which the 4D-D customer rule NEVER makes
  authoritative for identity;
* the Micron 7500 SSD alias policy is NOT_APPLICABLE to this established
  non-SSD (memory-module) request, with ZERO catalog fetches.

No test here mocks the final accepted result: the acceptance flows through
the real fetch/extract/normalize/match/aggregate pipeline.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import TYPE_CHECKING
from unittest.mock import MagicMock, patch

import pytest

from product_intelligence.domain import ResearchRequest
from product_intelligence.domain.enums import (
    EvidenceDecision,
    ResearchRunState,
)
from product_intelligence.execution import orchestration as orchestration_module
from product_intelligence.execution import execute_research_run
from product_intelligence.execution.search_query import build_search_query
from product_intelligence.providers.page import (
    FetchedPage,
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
    derive_lookup_base_candidate,
)
from product_intelligence.research.price_result_codec import (
    decode_price_aggregation_result,
)
from product_intelligence.runs.models import (
    AiAssistedReviewCandidate,
    PriceIntelligenceSnapshot,
    ResearchMicronAliasSnapshot,
    ResearchRun,
)

if TYPE_CHECKING:
    from collections.abc import Callable

# The production request (exact MPN + description), kept verbatim as the
# regression fixture. The rules under test are general (explicit-MPN
# requests, generic memory pages); nothing here is Micron-specific.
PRODUCTION_MPN = "MTC20F2085S1RC64BH1T"
PRODUCTION_DESCRIPTION = "Micron 32GB DDR5-6400 ECC 2Rx8 RDIMM CL52 Tray"

CATALOG_URL = MICRON_7500_REQUESTED_CATALOG_URL

# Candidate URLs (fictitious; no domain is privileged by this test).
BROAD_AGG_URL = "https://broad-aggregator.example/micron-32gb-ddr5"
BROAD_TITLE_URL = "https://broad-title.example/micron-ddr5-modules"
CONFLICT_BASE_URL = "https://conflict-base.example/module"
CONFLICT_OTHER_URL = "https://conflict-other.example/module"
EXACT_URL = "https://exact-reseller.example/memory-module"

# Deterministic price published by the exact-MPN candidate.
EXACT_PRICE = "1499.00"


def _product_page(
    *,
    title: str | None = None,
    mpn: str | None = None,
    sku: str | None = None,
    price: str | None = None,
    currency: str = "USD",
) -> str:
    """One JSON-LD Product page; absent fields are omitted."""
    product: dict = {"@context": "https://schema.org", "@type": "Product"}
    if title is not None:
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
        "<html><head><script type=\"application/ld+json\">"
        + json.dumps(product)
        + "</script></head><body></body></html>"
    )


def _empty_page() -> str:
    return "<html><head></head><body>no listings</body></html>"


def _candidate_bodies() -> dict[str, str]:
    """The production-shaped candidate set.

    * broad aggregator page — a genuine "Micron 32GB DDR5" listing with NO
      explicit MPN evidence (must stay REJECTED / NO_EXPLICIT_MPN_EVIDENCE);
    * broad title page — the MPN appears only in the title (must stay
      REJECTED / NO_EXPLICIT_MPN_EVIDENCE, TITLE_TEXT is not identity);
    * conflicting base form — publishes the T-stripped base MPN as its
      explicit MPN (must stay REJECTED / MPN_MISMATCH; the 4D-D customer
      rule never grants identity authority for the stripped form);
    * conflicting other form — publishes a different final character;
    * exact page — publishes the FULL requested MPN with a price (the only
      candidate the frozen 3C gate can ACCEPT).
    """
    return {
        BROAD_AGG_URL: _product_page(
            title="Micron 32GB DDR5-6400 ECC RDIMM Server Memory",
            price="1380.00",
        ),
        BROAD_TITLE_URL: _product_page(
            title=f"Micron 32GB DDR5 {PRODUCTION_MPN} Module",
            price="1385.00",
        ),
        CONFLICT_BASE_URL: _product_page(
            title="Micron RDIMM 32GB",
            mpn=derive_lookup_base_candidate(PRODUCTION_MPN),
            price="1390.00",
        ),
        CONFLICT_OTHER_URL: _product_page(
            title="Micron RDIMM 32GB",
            mpn=f"{PRODUCTION_MPN[:-1]}U",
            price="1395.00",
        ),
        EXACT_URL: _product_page(
            title="Micron 32GB DDR5-6400 ECC 2Rx8 RDIMM",
            mpn=PRODUCTION_MPN,
            price=EXACT_PRICE,
        ),
    }


def _make_run(mpn: str = PRODUCTION_MPN, description: str = PRODUCTION_DESCRIPTION) -> ResearchRun:
    return ResearchRun.objects.create_from_request(
        ResearchRequest(manufacturer_part_number=mpn, description=description)
    )


def _routed_page_fetcher(routes: dict[str, str]):
    """Fake PageFetcher: exact-URL routes, empty page otherwise.

    Returns (fetcher, fetched_urls) with every requested URL recorded in
    call order.
    """
    fetched_urls: list[str] = []

    def side_effect(request: PageFetchRequest) -> FetchedPage:
        fetched_urls.append(request.url)
        body = routes.get(request.url, _empty_page())
        return FetchedPage(
            requested_url=request.url,
            final_url=request.url,
            retrieved_at=datetime.now(tz=timezone.utc),
            status_code=200,
            body_text=body,
            content_type="application/json" if request.url == CATALOG_URL else "text/html",
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


def _install_recording_no_op_semantic(recorded: "list") -> "patch":
    """Patch the semantic boundary: RECORD what would be evaluated and
    return NO authority (no AiAssistedMatchResult). Keeps the suite
    deterministic and offline while proving the deterministic gate alone
    owns every acceptance/rejection."""

    def spy(request, assessments, evidence_writer, runtime=None):
        recorded.extend(assessments)
        return ()

    return patch.object(orchestration_module, "evaluate_semantic_matches", spy)


@pytest.fixture
def no_preferred_or_vendor_env(monkeypatch) -> None:
    """Deterministic environment: no direct acquisition, no vendor lookup."""
    monkeypatch.delenv("PI_PREFERRED_SEARCH_DOMAINS", raising=False)
    monkeypatch.delenv("PI_VENDOR_LOOKUP_BASE_URL", raising=False)


# ---------------------------------------------------------------------------
# 1. Query construction: exact-MPN first-class retrieval path (pure)
# ---------------------------------------------------------------------------


class TestExactMpnQueryConstruction:
    """The paid query for an explicit-MPN request is the exact-MPN phrase.

    General rule — no manufacturer, MPN, or domain is hard-coded here beyond
    the fixture values themselves.
    """

    def test_production_mpn_plus_description_is_exact_mpn_phrase(self) -> None:
        request = ResearchRequest(
            manufacturer_part_number=PRODUCTION_MPN,
            description=PRODUCTION_DESCRIPTION,
        )
        query = build_search_query(request)
        assert query.text == f'"{PRODUCTION_MPN}"'
        # The description is pipeline context, never a paid-query term: it
        # has no channel to displace exact-MPN retrieval.
        assert PRODUCTION_DESCRIPTION not in query.text

    def test_other_mpn_plus_description_is_exact_mpn_phrase(self) -> None:
        request = ResearchRequest(
            manufacturer_part_number="ABC-123",
            description="Some other widget with a long description",
        )
        query = build_search_query(request)
        assert query.text == '"ABC-123"'
        assert "widget" not in query.text

    def test_mpn_only_form_unchanged(self) -> None:
        request = ResearchRequest(
            manufacturer_part_number="MZ-QL23T800",
            description="",
        )
        assert build_search_query(request).text == "MZ-QL23T800"

    def test_description_only_form_unchanged(self) -> None:
        request = ResearchRequest(
            manufacturer_part_number="",
            description="4 port 25G switch",
        )
        assert build_search_query(request).text == "4 port 25G switch"


# ---------------------------------------------------------------------------
# 2. End-to-end recall through the real orchestration pipeline
# ---------------------------------------------------------------------------


class TestExactMpnRecallEndToEnd:
    """execute_research_run with controlled providers reproduces the
    production defect boundary and proves the fix (the autouse
    clean_execution_runs fixture isolates the DB per test)."""

    def test_exact_mpn_query_issued_and_candidates_not_displaced(
        self, no_preferred_or_vendor_env: None
    ) -> None:
        """The exact-MPN candidate ranked LAST among broad candidates still
        reaches the identity pipeline and is ACCEPTED; broad and conflicting
        candidates fail closed; the paid query is the exact-MPN phrase."""
        recorded_semantic: list = []
        provider = _search_provider(
            (
                BROAD_AGG_URL,
                BROAD_TITLE_URL,
                CONFLICT_BASE_URL,
                CONFLICT_OTHER_URL,
                EXACT_URL,
            )
        )
        fetcher, fetched_urls = _routed_page_fetcher(_candidate_bodies())
        run = _make_run()
        with _install_recording_no_op_semantic(recorded_semantic):
            result = execute_research_run(
                str(run.id), search_provider=provider, page_fetcher=fetcher
            )

        # Exactly ONE paid search, with the exact-MPN phrase as the entire
        # query (no description term that could displace it).
        provider.search.assert_called_once()
        sent_query = provider.search.call_args.args[0]
        assert sent_query.text == f'"{PRODUCTION_MPN}"'
        assert PRODUCTION_DESCRIPTION not in sent_query.text

        # Run completed with one comparable NEW listing (the exact page).
        assert result.run.current_state is ResearchRunState.COMPLETED
        assert result.accepted_assessment_count == 1
        assert result.price_buckets == 1

        # Every candidate URL was processed (no client-side cap displaced
        # the exact candidate by order).
        for url in (
            BROAD_AGG_URL,
            BROAD_TITLE_URL,
            CONFLICT_BASE_URL,
            CONFLICT_OTHER_URL,
            EXACT_URL,
        ):
            assert url in fetched_urls

        # The Micron 7500 SSD catalog was NEVER fetched for this
        # established memory-module request (NOT_APPLICABLE, zero fetches).
        assert CATALOG_URL not in fetched_urls

        # Decoded persisted price result: exactly one bucket (USD / NEW /
        # count 1) holding ONLY the exact-MPN candidate's price.
        snapshot = PriceIntelligenceSnapshot.objects.get(run=run)
        price_result = decode_price_aggregation_result(
            snapshot.payload, schema_version=snapshot.schema_version
        )
        assert len(price_result.buckets) == 1
        bucket = price_result.buckets[0]
        assert bucket.currency_code == "USD"
        assert bucket.count == 1
        assert str(bucket.low) == EXACT_PRICE
        assert str(bucket.high) == EXACT_PRICE
        accepted = [
            a for a in price_result.assessments if a.decision is EvidenceDecision.ACCEPTED
        ]
        assert len(accepted) == 1
        assert accepted[0].match_type.value == "EXACT"
        assert accepted[0].candidate_part_number_compared == PRODUCTION_MPN
        assert (
            accepted[0].normalized_listing.observation.source_url == EXACT_URL
        )

        # Broad + conflicting candidates are all excluded with their
        # frozen 3C rejection reasons — recall improved, gate unchanged.
        rejected = {
            a.normalized_listing.observation.source_url: a
            for a in price_result.assessments
            if a.decision is EvidenceDecision.REJECTED
        }
        assert set(rejected) == {
            BROAD_AGG_URL,
            BROAD_TITLE_URL,
            CONFLICT_BASE_URL,
            CONFLICT_OTHER_URL,
        }
        assert rejected[BROAD_AGG_URL].rejection_reason.value == "NO_EXPLICIT_MPN_EVIDENCE"
        assert rejected[BROAD_TITLE_URL].rejection_reason.value == "NO_EXPLICIT_MPN_EVIDENCE"
        # The T-stripped base form is an explicit CONFLICTING MPN, not an
        # alias: the customer rule never grants it identity authority.
        assert rejected[CONFLICT_BASE_URL].rejection_reason.value == "MPN_MISMATCH"
        assert rejected[CONFLICT_BASE_URL].candidate_part_number_compared == (
            derive_lookup_base_candidate(PRODUCTION_MPN)
        )
        assert rejected[CONFLICT_OTHER_URL].rejection_reason.value == "MPN_MISMATCH"

        # The semantic boundary saw the search-batch assessments but granted
        # nothing (deterministic gate owned the outcome).
        assert len(recorded_semantic) == 5

        # No human-review candidate was created.
        assert AiAssistedReviewCandidate.objects.filter(run=result.run).count() == 0

        # The persisted alias audit is NOT_APPLICABLE with zero fetch
        # provenance (the SSD catalog was never claimed as the applicable
        # authority for this product).
        alias_snapshot = ResearchMicronAliasSnapshot.objects.get(run=run)
        decoded_alias = decode_micron_alias_snapshot(
            alias_snapshot.payload, schema_version=alias_snapshot.schema_version
        )
        assert decoded_alias.status is MicronAliasEligibilityStatus.NOT_APPLICABLE
        assert decoded_alias.requested_source_url is None
        assert decoded_alias.fetched_final_url is None
        assert decoded_alias.source_name is None
        assert decoded_alias.retrieved_at is None
        assert decoded_alias.body_sha256 is None
        # The retrieval pointer is still recorded truthfully (shape-only,
        # authority-free).
        assert decoded_alias.lookup_base_candidate == (
            derive_lookup_base_candidate(PRODUCTION_MPN)
        )

    def test_exact_mpn_candidate_survives_large_broad_result_page(
        self, no_preferred_or_vendor_env: None
    ) -> None:
        """Candidate limits/order: 11 broad candidates + the exact one LAST
        (beyond the provider's old default 10-result page) — the exact
        candidate is still ACCEPTED and every result is processed."""
        broad_urls = tuple(
            f"https://broad-{i}.example/micron-32gb-ddr5" for i in range(11)
        )
        routes = dict(_candidate_bodies())
        for url in broad_urls:
            routes[url] = _product_page(
                title="Micron 32GB DDR5-6400 ECC RDIMM Server Memory",
                price="1380.00",
            )
        recorded_semantic: list = []
        provider = _search_provider(broad_urls + (EXACT_URL,))
        fetcher, fetched_urls = _routed_page_fetcher(routes)
        run = _make_run()
        with _install_recording_no_op_semantic(recorded_semantic):
            result = execute_research_run(
                str(run.id), search_provider=provider, page_fetcher=fetcher
            )

        assert result.run.current_state is ResearchRunState.COMPLETED
        # All 12 results processed — no client-side candidate cap.
        assert len(fetched_urls) == 12
        assert EXACT_URL in fetched_urls
        # Only the exact candidate is accepted; the broad ones stay excluded.
        assert result.accepted_assessment_count == 1
        snapshot = PriceIntelligenceSnapshot.objects.get(run=run)
        price_result = decode_price_aggregation_result(
            snapshot.payload, schema_version=snapshot.schema_version
        )
        accepted = [
            a for a in price_result.assessments if a.decision is EvidenceDecision.ACCEPTED
        ]
        assert len(accepted) == 1
        assert accepted[0].normalized_listing.observation.source_url == EXACT_URL
        assert len(price_result.buckets) == 1
        assert price_result.buckets[0].count == 1
        assert str(price_result.buckets[0].low) == EXACT_PRICE


# ---------------------------------------------------------------------------
# 3. Serper wire contract: the request carries ONLY the query text (no
#    explicit result-count parameter — PUBLIC-RESEARCH-RECALL-FU2) and the
#    adapter maps every returned organic item (no client-side truncation)
# ---------------------------------------------------------------------------


class TestSerperProviderRecallPage:
    def test_wire_body_carries_only_the_query_text_without_result_count(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """One paid request; the wire body carries ONLY the exact query
        text (FU1's `num=50` wire-body pin replaced in place — the
        correction authorized by production provider evidence, FU2).

        The production Serper account rejects an explicit `num`
        result-count override on this request (HTTP 400, "Query pattern
        not allowed for free accounts"), while the identical exact-quoted-
        MPN query WITHOUT `num` returns HTTP 200 with exact-MPN evidence.
        The provider's default organic result count therefore applies. The
        complete-payload pin asserts the exact query text AND the absence
        of every other field — no count, no pagination, no retry
        parameter.
        """
        from product_intelligence.providers import serper

        captured: dict = {}

        def fake_urlopen(request, timeout=None):  # noqa: ANN001
            captured["body"] = request.data

            class _Resp:
                def read(self) -> bytes:
                    return b'{"organic": []}'

                def __enter__(self):
                    return self

                def __exit__(self, *exc):
                    return None

            return _Resp()

        monkeypatch.setattr(
            "product_intelligence.providers.serper.urllib.request.urlopen",
            fake_urlopen,
        )
        provider = serper.SerperSearchProvider("k")
        provider.search(SearchQuery(text=f'"{PRODUCTION_MPN}"'))
        payload = json.loads(captured["body"].decode("utf-8"))
        assert payload["q"] == f'"{PRODUCTION_MPN}"'
        assert "num" not in payload
        assert payload == {"q": f'"{PRODUCTION_MPN}"'}

    def test_adapter_maps_every_returned_organic_item(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """A 50-result organic page is mapped in full — no adapter-side
        truncation of exact-MPN candidates beyond position 10."""
        items = [
            {
                "title": f"result {i}",
                "link": f"https://page-{i}.example/p",
                "snippet": "s",
            }
            for i in range(50)
        ]

        def fake_urlopen(request, timeout=None):  # noqa: ANN001
            class _Resp:
                def read(self) -> bytes:
                    return json.dumps({"organic": items}).encode("utf-8")

                def __enter__(self):
                    return self

                def __exit__(self, *exc):
                    return None

            return _Resp()

        monkeypatch.setattr(
            "product_intelligence.providers.serper.urllib.request.urlopen",
            fake_urlopen,
        )
        from product_intelligence.providers.serper import SerperSearchProvider

        provider = SerperSearchProvider("k")
        response = provider.search(SearchQuery(text=f'"{PRODUCTION_MPN}"'))
        assert len(response.results) == 50
        assert [r.source_url for r in response.results][-1] == (
            "https://page-49.example/p"
        )


# ---------------------------------------------------------------------------
# 4. Alias policy applicability at the real acquisition boundary
# ---------------------------------------------------------------------------


class TestAliasPolicyApplicabilityGate:
    """The Micron 7500 SSD catalog policy is NOT_APPLICABLE to established
    memory-module requests, with zero fetches — while legitimate 7500 SSD
    behavior is untouched."""

    @staticmethod
    def _catalog_fetcher() -> "MagicMock":
        from pathlib import Path

        body = (
            Path(__file__).resolve().parents[1]
            / "fixtures"
            / "pages"
            / "micron_7500_part_catalog.json"
        ).read_text(encoding="utf-8")
        fetcher = MagicMock(spec=PageFetcher)
        fetcher.fetch.return_value = FetchedPage(
            requested_url=CATALOG_URL,
            final_url=CATALOG_URL,
            retrieved_at=datetime(2026, 9, 22, 23, 20, 25, tzinfo=timezone.utc),
            status_code=200,
            body_text=body,
            content_type="application/json;charset=utf-8",
            body_byte_count=len(body.encode("utf-8")),
            redirect_count=0,
            fetcher_id="test",
        )
        return fetcher

    def test_ddr5_rdimm_request_is_not_applicable_with_zero_fetches(self) -> None:
        from product_intelligence.execution.micron_alias_authority import (
            acquire_micron_alias_eligibility,
        )

        fetcher = self._catalog_fetcher()
        request = ResearchRequest(
            manufacturer_part_number=PRODUCTION_MPN,
            description=PRODUCTION_DESCRIPTION,
        )
        result = acquire_micron_alias_eligibility(
            request=request, page_fetcher=fetcher
        )
        assert result.status is MicronAliasEligibilityStatus.NOT_APPLICABLE
        assert fetcher.fetch.call_count == 0
        assert result.lookup_base_candidate == (
            derive_lookup_base_candidate(PRODUCTION_MPN)
        )
        assert result.manufacturer is None
        assert result.category is None
        assert result.alias_relation is None

    def test_lower_case_memory_description_is_not_applicable(self) -> None:
        from product_intelligence.execution.micron_alias_authority import (
            acquire_micron_alias_eligibility,
        )

        fetcher = self._catalog_fetcher()
        request = ResearchRequest(
            manufacturer_part_number=PRODUCTION_MPN,
            description="micron 32gb ddr5 rdimm cl52 tray",
        )
        result = acquire_micron_alias_eligibility(
            request=request, page_fetcher=fetcher
        )
        assert result.status is MicronAliasEligibilityStatus.NOT_APPLICABLE
        assert fetcher.fetch.call_count == 0

    def test_absent_mpn_stays_no_requested_mpn_before_applicability(self) -> None:
        """Priority: NO_REQUESTED_MPN < NOT_APPLICABLE — an absent MPN is
        still persisted as missing input, never as policy non-applicability."""
        from product_intelligence.execution.micron_alias_authority import (
            acquire_micron_alias_eligibility,
        )

        fetcher = self._catalog_fetcher()
        request = ResearchRequest(
            manufacturer_part_number="",
            description=PRODUCTION_DESCRIPTION,
        )
        result = acquire_micron_alias_eligibility(
            request=request, page_fetcher=fetcher
        )
        assert result.status is MicronAliasEligibilityStatus.NO_REQUESTED_MPN
        assert fetcher.fetch.call_count == 0

    def test_ssd_description_still_reaches_the_catalog(self) -> None:
        """Legitimate 7500 SSD behavior intact: a 7500 SSD request (no
        memory-module evidence) still fetches the catalog and ESTABLISHES."""
        from product_intelligence.execution.micron_alias_authority import (
            acquire_micron_alias_eligibility,
        )

        fetcher = self._catalog_fetcher()
        request = ResearchRequest(
            manufacturer_part_number="MTFDKCC3T8TGP-1BK1DABYYT",
            description="Micron 7500 3.84TB datacenter SSD",
        )
        result = acquire_micron_alias_eligibility(
            request=request, page_fetcher=fetcher
        )
        assert fetcher.fetch.call_count == 1
        assert result.status is MicronAliasEligibilityStatus.ESTABLISHED
        assert result.alias_relation is not None

    def test_non_micron_ssd_still_fetches_catalog_and_abstains(self) -> None:
        """The gate is NOT a manufacturer check: a non-Micron SSD request
        without memory-module evidence still consults the catalog and gets
        the bounded NO_AUTHORITY_MATCH (frozen 4D-D behavior unchanged)."""
        from product_intelligence.execution.micron_alias_authority import (
            acquire_micron_alias_eligibility,
        )

        fetcher = self._catalog_fetcher()
        request = ResearchRequest(
            manufacturer_part_number="MZ-QL23T800",
            description="Samsung SSD 970 EVO Plus 1TB",
        )
        result = acquire_micron_alias_eligibility(
            request=request, page_fetcher=fetcher
        )
        assert fetcher.fetch.call_count == 1
        assert result.status is MicronAliasEligibilityStatus.NO_AUTHORITY_MATCH
