"""4D-D FU1 — runtime reachability + query-semantics closure regressions.

These tests close the three independently verified acceptance blockers of
PRODUCT-INTEL.4D-D:

BLOCKER 1 — the REAL default runtime must be able to fetch the reviewed
Micron 7500 family-catalog JSON. The ordinary default candidate-page
fetcher stays HTML-only (frozen 3A: ``application/json`` refused by
default); the JSON capability is explicit, additive, immutable
constructor configuration on the SAME ``HttpPageFetcher``. Proven here
with the REAL ``HttpPageFetcher`` implementation and network internals
safely monkeypatched/offline (public DNS fixture + controlled opener
returning the PRE2-recorded Micron catalog bytes with
``Content-Type: application/json;charset=utf-8``):

* JSON-configured real fetcher + recorded bytes ->
  ``acquire_micron_alias_eligibility`` reaches ESTABLISHED for
  ``MTFDKCC3T8TGP-1BK1DABYYR`` (matched base
  ``MTFDKCC3T8TGP-1BK1DABYY``, manufacturer Micron, category SSD);
* default (HTML-only) real fetcher + the SAME recorded bytes ->
  ``PageFetchError`` (content type refused), and bounded
  ``FETCH_FAILED`` through the authority pipeline — i.e. the default
  configuration cannot reach ESTABLISHED;
* DEFAULT production wiring (``execute_research_run`` with
  ``page_fetcher=None``) -> the catalog request is sent with
  ``Accept: application/json`` by the lazily created JSON authority
  fetcher, the bounded audit persists ESTABLISHED, and exactly ONE paid
  search goes out with the frozen OR query.

BLOCKER 2 — the alias-expanded query is the frozen OR shape
(``("REQUESTED" OR "ALIAS1" OR "ALIAS2") description``): exact-string
proofs for all three canonical request forms, with and without a
description.

BLOCKER 3 — no broad exception catch in the authority pipeline: bare
``Exception`` and ``RuntimeError`` propagate (proofs in
``test_micron_alias_authority.py``); only the expected provider
classes are downgraded (PageFetchError -> FETCH_FAILED,
UnsafeFetchTargetError -> SOURCE_REFUSED, also proven there).

Also: the separately tested transport-classification fix from
14981e3 (``_build_opener`` OSError -> bounded ``PageFetchError``,
non-OSError programming errors still propagate) is regression-tested
here.
"""

from __future__ import annotations

import io
import os
import socket
from datetime import datetime, timezone
from email.message import Message
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from product_intelligence.domain import ResearchRequest
from product_intelligence.domain.enums import ResearchRunState
from product_intelligence.execution import execute_research_run
from product_intelligence.execution.micron_alias_authority import (
    acquire_micron_alias_eligibility,
)
from product_intelligence.execution.search_query import (
    build_alias_expanded_search_query,
)
from product_intelligence.providers import http_page
from product_intelligence.providers.http_page import (
    ACCEPTED_MEDIA_TYPES,
    DEFAULT_ACCEPT_HEADER,
    JSON_ACCEPTED_MEDIA_TYPES,
    JSON_ACCEPT_HEADER,
    HttpPageFetcher,
)
from product_intelligence.providers.page import PageFetchError, PageFetchRequest
from product_intelligence.providers.search import (
    SearchProvider,
    SearchQuery,
    SearchResponse,
)
from product_intelligence.research.micron_alias_codec import (
    decode_micron_alias_snapshot,
)
from product_intelligence.research.micron_packaging_alias import (
    MICRON_7500_CATEGORY,
    MICRON_7500_MANUFACTURER,
    MICRON_7500_REQUESTED_CATALOG_URL,
    MicronAliasEligibilityStatus,
    build_packaging_alias_relation,
)
from product_intelligence.runs.models import (
    ResearchMicronAliasSnapshot,
    ResearchRun,
)

pytestmark = pytest.mark.django_db

BASE = "MTFDKCC3T8TGP-1BK1DABYY"
BASER = f"{BASE}R"
BASET = f"{BASE}T"
CATALOG_URL = MICRON_7500_REQUESTED_CATALOG_URL
FIXTURES = Path(__file__).resolve().parents[1] / "fixtures" / "pages"

#: The PRE2-recorded Content-Type of the production authority endpoint.
MICRON_CONTENT_TYPE = "application/json;charset=utf-8"

PUBLIC_ADDRESS = "93.184.216.34"
RETRIEVED_AT = datetime(2026, 9, 23, 10, 0, 0, tzinfo=timezone.utc)


def _catalog_bytes() -> bytes:
    """The PRE2-recorded Micron 7500 family-catalog JSON bytes."""
    return (FIXTURES / "micron_7500_part_catalog.json").read_bytes()


def _headers(**values: str) -> Message:
    message = Message()
    for name, value in values.items():
        message[name.replace("_", "-")] = value
    return message


class _MicronResponse:
    """A controlled HTTP response carrying the PRE2-recorded catalog bytes."""

    def __init__(
        self,
        body: bytes,
        *,
        status: int = 200,
        content_type: str = MICRON_CONTENT_TYPE,
    ) -> None:
        self._body = io.BytesIO(body)
        self.status = status
        self.headers = _headers(Content_Type=content_type)

    def read(self, amount: int | None = None) -> bytes:
        return self._body.read(amount)

    def getcode(self) -> int:
        return self.status

    def __enter__(self) -> "_MicronResponse":
        return self

    def __exit__(self, *exc_info: object) -> None:
        return None


class _RecordingOpener:
    """Stands in for the real opener; records every request it is handed."""

    def __init__(self, outcome: object) -> None:
        self._outcome = outcome
        self.requests: list = []
        self.timeout = None

    def open(self, request, timeout=None):
        self.requests.append(request)
        self.timeout = timeout
        if isinstance(self._outcome, Exception):
            raise self._outcome
        return self._outcome


@pytest.fixture
def public_dns(monkeypatch: pytest.MonkeyPatch) -> None:
    """Every host resolves to one public address (no live DNS)."""
    monkeypatch.setattr(
        http_page.socket,
        "getaddrinfo",
        lambda host, port, **kwargs: [
            (socket.AF_INET, socket.SOCK_STREAM, 6, "", (PUBLIC_ADDRESS, port))
        ],
    )


@pytest.fixture
def no_preferred_or_vendor_env(monkeypatch) -> None:
    """Deterministic environment: no direct acquisition, no vendor lookup."""
    monkeypatch.delenv("PI_PREFERRED_SEARCH_DOMAINS", raising=False)
    monkeypatch.delenv("PI_VENDOR_LOOKUP_BASE_URL", raising=False)


# ---------------------------------------------------------------------------
# BLOCKER 1a — REAL HttpPageFetcher, JSON-configured, recorded Micron bytes
# ---------------------------------------------------------------------------


class TestRealAdapterJsonModeEstablishes:
    """The mandatory real-adapter integration proof.

    A REAL ``HttpPageFetcher`` (not a MagicMock) whose only network
    internals are monkeypatched (DNS fixture + controlled opener) carries
    the PRE2-recorded Micron catalog JSON with the recorded production
    Content-Type through the actual authority pipeline to ESTABLISHED.
    """

    def test_real_fetcher_json_mode_reaches_established(
        self, monkeypatch: pytest.MonkeyPatch, public_dns: None
    ) -> None:
        opener = _RecordingOpener(_MicronResponse(_catalog_bytes()))
        monkeypatch.setattr(http_page, "_build_opener", lambda: opener)

        fetcher = HttpPageFetcher(
            accepted_media_types=JSON_ACCEPTED_MEDIA_TYPES,
            accept_header=JSON_ACCEPT_HEADER,
            clock=lambda: RETRIEVED_AT,
        )
        result = acquire_micron_alias_eligibility(
            request=ResearchRequest(
                manufacturer_part_number=BASER,
                description="Micron 7500 3.84TB datacenter SSD",
            ),
            page_fetcher=fetcher,
        )

        assert result.status is MicronAliasEligibilityStatus.ESTABLISHED
        assert result.matched_base_mpn == BASE
        assert result.manufacturer == MICRON_7500_MANUFACTURER
        assert result.manufacturer == "Micron"
        assert result.category == MICRON_7500_CATEGORY
        assert result.category == "SSD"
        assert result.fetched_final_url == CATALOG_URL
        assert result.retrieved_at == RETRIEVED_AT
        assert result.body_sha256 is not None

        # The R/T retrieval relation: requested form excluded, family order.
        assert result.alias_relation is not None
        assert result.alias_relation.requested_mpn == BASER
        assert result.alias_relation.base_mpn == BASE
        assert result.alias_relation.aliases == (BASE, BASET)

        # Exactly one request, to the reviewed endpoint, announcing JSON.
        assert len(opener.requests) == 1
        assert opener.requests[0].full_url == CATALOG_URL
        assert opener.requests[0].get_header("Accept") == "application/json"
        assert opener.requests[0].get_method() == "GET"

    @pytest.mark.parametrize("mpn", [BASE, BASER, BASET])
    def test_real_fetcher_json_mode_established_for_all_request_forms(
        self, monkeypatch: pytest.MonkeyPatch, public_dns: None, mpn: str
    ) -> None:
        monkeypatch.setattr(
            http_page, "_build_opener",
            lambda: _RecordingOpener(_MicronResponse(_catalog_bytes())),
        )
        fetcher = HttpPageFetcher(
            accepted_media_types=JSON_ACCEPTED_MEDIA_TYPES,
            accept_header=JSON_ACCEPT_HEADER,
            clock=lambda: RETRIEVED_AT,
        )
        result = acquire_micron_alias_eligibility(
            request=ResearchRequest(manufacturer_part_number=mpn, description="d"),
            page_fetcher=fetcher,
        )
        assert result.status is MicronAliasEligibilityStatus.ESTABLISHED
        assert result.matched_base_mpn == BASE
        assert result.manufacturer == "Micron"
        assert result.category == "SSD"


# ---------------------------------------------------------------------------
# BLOCKER 1b — the DEFAULT real fetcher remains HTML-only and refuses the
# same recorded Micron JSON (default application/json refusal stays green)
# ---------------------------------------------------------------------------


class TestRealAdapterDefaultStaysHtmlOnly:
    def test_default_real_fetcher_refuses_recorded_micron_json(
        self, monkeypatch: pytest.MonkeyPatch, public_dns: None
    ) -> None:
        """Same recorded bytes the JSON mode accepts: the default refuses."""
        opener = _RecordingOpener(_MicronResponse(_catalog_bytes()))
        monkeypatch.setattr(http_page, "_build_opener", lambda: opener)

        fetcher = HttpPageFetcher(clock=lambda: RETRIEVED_AT)
        with pytest.raises(PageFetchError, match="HTML documents only"):
            fetcher.fetch(PageFetchRequest(CATALOG_URL))

        # The default still announces the frozen HTML accept set.
        assert opener.requests[0].get_header("Accept") == "text/html,application/xhtml+xml"

    def test_default_real_fetcher_json_refusal_bounds_to_fetch_failed(
        self, monkeypatch: pytest.MonkeyPatch, public_dns: None
    ) -> None:
        """If the HTML-only default were (wrongly) used for the authority
        fetch, the pipeline bounds to FETCH_FAILED — never ESTABLISHED."""
        monkeypatch.setattr(
            http_page, "_build_opener",
            lambda: _RecordingOpener(_MicronResponse(_catalog_bytes())),
        )
        fetcher = HttpPageFetcher(clock=lambda: RETRIEVED_AT)
        result = acquire_micron_alias_eligibility(
            request=ResearchRequest(manufacturer_part_number=BASER, description="d"),
            page_fetcher=fetcher,
        )
        assert result.status is MicronAliasEligibilityStatus.FETCH_FAILED
        assert result.alias_relation is None
        assert result.matched_base_mpn is None
        assert result.manufacturer is None
        assert result.category is None


# ---------------------------------------------------------------------------
# BLOCKER 1c — DEFAULT production wiring (page_fetcher=None) does not feed
# the Micron JSON endpoint through the HTML-only configuration
# ---------------------------------------------------------------------------


class TestDefaultProductionWiring:
    def test_default_wiring_reaches_established_and_single_or_search(
        self,
        monkeypatch: pytest.MonkeyPatch,
        public_dns: None,
        no_preferred_or_vendor_env: None,
    ) -> None:
        """execute_research_run with NO injected page fetcher.

        The real default runtime: HTML-only default candidate fetcher +
        lazily created JSON authority fetcher. Offline via the recorded
        catalog response. Proves:

        * the catalog request is announced with ``Accept: application/json``
          (not the HTML-only configuration, which would refuse it);
        * the bounded audit persists ESTABLISHED before the search;
        * exactly ONE paid search goes out, with the frozen OR query.
        """
        catalog_requests: list = []
        other_requests: list = []

        class _RoutingOpener:
            def open(self, request, timeout=None):
                if request.full_url == CATALOG_URL:
                    catalog_requests.append(request)
                    return _MicronResponse(_catalog_bytes())
                other_requests.append(request)
                return _MicronResponse(
                    b"<html><head></head><body>no listings</body></html>",
                    content_type="text/html",
                )

        monkeypatch.setattr(http_page, "_build_opener", lambda: _RoutingOpener())

        provider = MagicMock(spec=SearchProvider)
        provider.search.return_value = SearchResponse(
            provider_id="test",
            query=SearchQuery(text="unused"),
            retrieved_at=RETRIEVED_AT,
            results=(),
        )
        run = ResearchRun.objects.create_from_request(
            ResearchRequest(
                manufacturer_part_number=BASER,
                description="Micron 7500 3.84TB datacenter SSD",
            )
        )

        # page_fetcher intentionally NOT injected: the real default wiring.
        result = execute_research_run(str(run.id), search_provider=provider)

        assert result.run.current_state is ResearchRunState.COMPLETED
        # The reviewed catalog was fetched exactly once and announced JSON.
        assert len(catalog_requests) == 1
        assert catalog_requests[0].get_header("Accept") == "application/json"
        assert catalog_requests[0].get_method() == "GET"
        # Zero paid search results -> zero candidate-page fetches.
        assert other_requests == []

        # The bounded audit persisted ESTABLISHED (with the source base).
        snapshot = ResearchMicronAliasSnapshot.objects.get(run=run)
        decoded = decode_micron_alias_snapshot(
            snapshot.payload, schema_version=snapshot.schema_version
        )
        assert decoded.status is MicronAliasEligibilityStatus.ESTABLISHED
        assert decoded.matched_base_mpn == BASE
        assert decoded.manufacturer == "Micron"
        assert decoded.category == "SSD"

        # Exactly ONE paid search, with the frozen OR query shape.
        provider.search.assert_called_once()
        assert provider.search.call_args.args[0].text == (
            f'("{BASER}" OR "{BASE}" OR "{BASET}") '
            "Micron 7500 3.84TB datacenter SSD"
        )

    def test_default_wiring_never_fetches_catalog_on_direct_sufficient_run(
        self,
        monkeypatch: pytest.MonkeyPatch,
        public_dns: None,
        no_preferred_or_vendor_env: None,
    ) -> None:
        """A direct-sufficient run performs zero Micron authority fetch —
        and therefore never instantiates the JSON authority fetcher path.
        Proven by making ANY catalog fetch explode."""
        import json as _json

        from product_intelligence.providers.directmacro import DirectMacroLocator
        from product_intelligence.providers.direct_source import DirectSourceQuery

        direct_url = DirectMacroLocator().locate(
            DirectSourceQuery(manufacturer_part_number=BASER)
        )[0].url

        def _direct_page_body() -> bytes:
            product = {
                "@context": "https://schema.org",
                "@type": "Product",
                "name": "Micron 7500 3.84TB",
                "mpn": BASER,
                "offers": {
                    "@type": "Offer",
                    "price": "2500.00",
                    "priceCurrency": "USD",
                    "availability": "https://schema.org/InStock",
                    "itemCondition": "https://schema.org/NewCondition",
                },
            }
            return (
                b'<html><head><script type="application/ld+json">'
                + _json.dumps(product).encode("utf-8")
                + b"</script></head><body></body></html>"
            )

        seen: list = []

        class _RoutingOpener:
            def open(self, request, timeout=None):
                seen.append(request.full_url)
                if request.full_url == CATALOG_URL:
                    raise AssertionError(
                        "the reviewed catalog endpoint must never be fetched "
                        "on a direct-sufficient run"
                    )
                return _MicronResponse(
                    _direct_page_body(), content_type="text/html"
                )

        monkeypatch.setattr(http_page, "_build_opener", lambda: _RoutingOpener())

        provider = MagicMock(spec=SearchProvider)
        provider.search.return_value = SearchResponse(
            provider_id="test",
            query=SearchQuery(text="unused"),
            retrieved_at=RETRIEVED_AT,
            results=(),
        )
        run = ResearchRun.objects.create_from_request(
            ResearchRequest(
                manufacturer_part_number=BASER,
                description="Micron 7500 3.84TB datacenter SSD",
            )
        )

        with patch.dict(
            os.environ, {"PI_PREFERRED_SEARCH_DOMAINS": "directmacro.com"}
        ):
            result = execute_research_run(str(run.id), search_provider=provider)

        assert result.run.current_state is ResearchRunState.COMPLETED
        # Direct page fetched; zero catalog fetch; zero paid search.
        assert seen == [direct_url]
        provider.search.assert_not_called()
        assert ResearchMicronAliasSnapshot.objects.filter(run=run).count() == 0


# ---------------------------------------------------------------------------
# JSON-mode boundaries: explicit capability, no silent broadening
# ---------------------------------------------------------------------------


class TestJsonModeBoundaries:
    @pytest.mark.parametrize(
        "content_type",
        [
            "application/json",
            "application/json;charset=utf-8",
            "APPLICATION/JSON; charset=UTF-8",
        ],
    )
    def test_json_mode_accepts_json_with_parameters_and_casing(
        self,
        monkeypatch: pytest.MonkeyPatch,
        public_dns: None,
        content_type: str,
    ) -> None:
        monkeypatch.setattr(
            http_page,
            "_build_opener",
            lambda: _RecordingOpener(
                _MicronResponse(_catalog_bytes(), content_type=content_type)
            ),
        )
        fetcher = HttpPageFetcher(
            accepted_media_types=JSON_ACCEPTED_MEDIA_TYPES,
            accept_header=JSON_ACCEPT_HEADER,
            clock=lambda: RETRIEVED_AT,
        )
        page = fetcher.fetch(PageFetchRequest(CATALOG_URL))
        assert page.status_code == 200
        assert page.body_text.startswith("{")

    @pytest.mark.parametrize(
        "content_type",
        [
            "text/html",
            "application/xhtml+xml",
            "text/json",
            "application/ld+json",
            "application/xml",
            "image/jpeg",
            "",
        ],
    )
    def test_json_mode_does_not_broaden_past_application_json(
        self,
        monkeypatch: pytest.MonkeyPatch,
        public_dns: None,
        content_type: str,
    ) -> None:
        monkeypatch.setattr(
            http_page,
            "_build_opener",
            lambda: _RecordingOpener(
                _MicronResponse(b"x", content_type=content_type)
            ),
        )
        fetcher = HttpPageFetcher(
            accepted_media_types=JSON_ACCEPTED_MEDIA_TYPES,
            accept_header=JSON_ACCEPT_HEADER,
            clock=lambda: RETRIEVED_AT,
        )
        with pytest.raises(PageFetchError, match="JSON documents only"):
            fetcher.fetch(PageFetchRequest(CATALOG_URL))


class TestMediaTypeConfiguration:
    def test_default_configuration_is_exactly_the_frozen_html_behavior(
        self,
    ) -> None:
        fetcher = HttpPageFetcher()
        assert fetcher._accepted_media_types == ACCEPTED_MEDIA_TYPES
        assert fetcher._accepted_media_types == frozenset(
            {"text/html", "application/xhtml+xml"}
        )
        assert fetcher._accept_header == DEFAULT_ACCEPT_HEADER
        assert fetcher._accept_header == "text/html,application/xhtml+xml"

    def test_default_and_json_sets_are_disjoint(self) -> None:
        assert JSON_ACCEPTED_MEDIA_TYPES == frozenset({"application/json"})
        assert ACCEPTED_MEDIA_TYPES & JSON_ACCEPTED_MEDIA_TYPES == frozenset()
        assert JSON_ACCEPT_HEADER == "application/json"

    @pytest.mark.parametrize(
        "kwargs",
        [
            {"accepted_media_types": frozenset()},
            {"accepted_media_types": set()},
            {"accepted_media_types": ()},
            {"accepted_media_types": {"application/json", ""}},
            {"accepted_media_types": {"application/json", 123}},
            {"accept_header": ""},
            {"accept_header": "   "},
        ],
    )
    def test_invalid_media_configuration_is_refused(self, kwargs: dict) -> None:
        with pytest.raises((TypeError, ValueError)):
            HttpPageFetcher(**kwargs)

    def test_media_configuration_must_be_a_set_like_container(self) -> None:
        with pytest.raises(TypeError):
            HttpPageFetcher(accepted_media_types="application/json")

    def test_json_mode_still_sends_no_credential_no_cookie(self,
                                                         monkeypatch: pytest.MonkeyPatch,
                                                         public_dns: None) -> None:
        opener = _RecordingOpener(_MicronResponse(_catalog_bytes()))
        monkeypatch.setattr(http_page, "_build_opener", lambda: opener)
        fetcher = HttpPageFetcher(
            accepted_media_types=JSON_ACCEPTED_MEDIA_TYPES,
            accept_header=JSON_ACCEPT_HEADER,
            clock=lambda: RETRIEVED_AT,
        )
        fetcher.fetch(PageFetchRequest(CATALOG_URL))
        sent = {name.lower() for name in opener.requests[0].headers}
        assert sent == {"user-agent", "accept", "accept-encoding"}


# ---------------------------------------------------------------------------
# 14981e3 transport-classification fix (opener OSError) — separately tested
# ---------------------------------------------------------------------------


class TestOpenerConstructionFailure:
    def test_opener_oserror_is_bounded_page_fetch_error(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Secure-transport setup failure (TLS context creation) is a
        transport failure: classified PageFetchError, never a raw OSError."""

        def _raise_oserror():
            raise OSError("TLS context unavailable")

        monkeypatch.setattr(http_page, "_build_opener", _raise_oserror)
        fetcher = HttpPageFetcher()
        with pytest.raises(PageFetchError, match="secure transport"):
            fetcher.fetch(PageFetchRequest("https://example.com/p"))

    def test_opener_non_oserror_programming_defect_propagates(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        def _raise_runtime():
            raise RuntimeError("programming defect")

        monkeypatch.setattr(http_page, "_build_opener", _raise_runtime)
        with pytest.raises(RuntimeError, match="programming defect"):
            HttpPageFetcher().fetch(PageFetchRequest("https://example.com/p"))


# ---------------------------------------------------------------------------
# BLOCKER 2 — exact frozen OR query strings
# ---------------------------------------------------------------------------


class TestOrQueryBuilder:
    @pytest.mark.parametrize(
        ("mpn", "expected"),
        [
            (
                BASE,
                '("MTFDKCC3T8TGP-1BK1DABYY" OR "MTFDKCC3T8TGP-1BK1DABYYR" '
                'OR "MTFDKCC3T8TGP-1BK1DABYYT") Micron 7500 3.84TB datacenter SSD',
            ),
            (
                BASER,
                '("MTFDKCC3T8TGP-1BK1DABYYR" OR "MTFDKCC3T8TGP-1BK1DABYY" '
                'OR "MTFDKCC3T8TGP-1BK1DABYYT") Micron 7500 3.84TB datacenter SSD',
            ),
            (
                BASET,
                '("MTFDKCC3T8TGP-1BK1DABYYT" OR "MTFDKCC3T8TGP-1BK1DABYY" '
                'OR "MTFDKCC3T8TGP-1BK1DABYYR") Micron 7500 3.84TB datacenter SSD',
            ),
        ],
    )
    def test_exact_or_strings_with_description(self, mpn: str, expected: str) -> None:
        relation = build_packaging_alias_relation(mpn, BASE)
        query = build_alias_expanded_search_query(
            ResearchRequest(
                manufacturer_part_number=mpn,
                description="Micron 7500 3.84TB datacenter SSD",
            ),
            relation,
        )
        assert query.text == expected

    @pytest.mark.parametrize(
        ("mpn", "expected"),
        [
            (BASE, '("MTFDKCC3T8TGP-1BK1DABYY" OR "MTFDKCC3T8TGP-1BK1DABYYR" OR "MTFDKCC3T8TGP-1BK1DABYYT")'),
            (BASER, '("MTFDKCC3T8TGP-1BK1DABYYR" OR "MTFDKCC3T8TGP-1BK1DABYY" OR "MTFDKCC3T8TGP-1BK1DABYYT")'),
            (BASET, '("MTFDKCC3T8TGP-1BK1DABYYT" OR "MTFDKCC3T8TGP-1BK1DABYY" OR "MTFDKCC3T8TGP-1BK1DABYYR")'),
        ],
    )
    def test_exact_or_strings_without_description(self, mpn: str, expected: str) -> None:
        relation = build_packaging_alias_relation(mpn, BASE)
        query = build_alias_expanded_search_query(
            ResearchRequest(manufacturer_part_number=mpn, description=""),
            relation,
        )
        assert query.text == expected

    def test_requested_mpn_is_first_and_relation_order_is_deterministic(
        self,
    ) -> None:
        relation = build_packaging_alias_relation(BASE, BASE)
        assert relation.aliases == (BASER, BASET)
        query = build_alias_expanded_search_query(
            ResearchRequest(manufacturer_part_number=BASE, description="d"),
            relation,
        )
        assert query.text == f'("{BASE}" OR "{BASER}" OR "{BASET}") d'
        # The requested form never aliases itself.
        assert BASE not in relation.aliases
