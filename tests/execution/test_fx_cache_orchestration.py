"""Canonical-path orchestration tests for the FX observation cache
(PRODUCT-INTEL.8A-FX-A1).

Production-shaped: real ``ResearchRun`` execution through
``execute_research_run`` with a mocked Serper/page pipeline and the
canonical ECB feed exercised by mocking ``urllib.request.urlopen``
(the repo's established ``tests/providers/test_fx_transport.py``
pattern). The wall-clock seam
(``fx_observation_cache._utc_now``) is pinned to deterministic FUTURE
weekend instants so that:

* every weekday of the run day is covered deterministically;
* the provider's real retrieved_at (wall clock) always precedes the
  pinned proof instant, keeping stored rows internally consistent.

Coverage:
* USD-only -> zero cache/store + zero provider call (discovery first);
* canonical ``fx_provider=None`` is cache-eligible;
* explicit fake / real EcbFxProvider / subclass / wrapper bypass the
  cache entirely (zero store interaction);
* CACHE_HIT -> zero provider calls, original retrieved_at preserved,
  required currencies projected from the full cached set;
* LIVE -> exactly one full-set provider fetch, store row written;
* working-day / Monday-boundary / stale-proof -> live revalidation;
* live FxProviderError remains nonfatal;
* cache corruption / unsupported codec / unexpected storage errors
  propagate (fail closed — never a silent live fallback);
* run publication failure after cache persistence leaves the store row
  (feed content, not run evidence);
* concurrency: identical content converges on one row;
* replay of a CACHE_HIT run: zero live calls, zero cache acquisition,
  persisted provenance preserved.
"""

from __future__ import annotations

from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from unittest.mock import MagicMock, patch
from zoneinfo import ZoneInfo

import pytest
import urllib.error

from product_intelligence.domain import ResearchRequest
from product_intelligence.domain.enums import ResearchRunState
from product_intelligence.execution import execute_research_run, ExecutionError
from product_intelligence.execution import fx_observation_cache
from product_intelligence.execution.compact_quote_replay import (
    replay_compact_quote_projection,
)
from product_intelligence.execution.compact_quote_public_replay import (
    replay_public_compact_quote_projection,
)
from product_intelligence.providers.fx import (
    FX_FEED_ID_ECB_DAILY,
    EcbFxProvider,
    FxObservationSet,
    FxProviderError,
    FxRateObservation,
)
from product_intelligence.providers.page import FetchedPage, PageFetchRequest
from product_intelligence.providers.search import (
    SearchProvider,
    SearchQuery,
    SearchResponse,
    SearchResult,
)
from product_intelligence.research.fx_cache_contract import (
    fx_document_content_sha256,
)
from product_intelligence.research.fx_codec import (
    decode_fx_observation,
    encode_fx_observation,
)
from product_intelligence.runs.models import (
    FxObservationStore,
    PriceIntelligenceSnapshot,
    ResearchFxSnapshot,
    ResearchRun,
)

UTC = timezone.utc
BRUSSELS = ZoneInfo("Europe/Brussels")

# Canonical document rates (full set; EUR page => required {EUR, USD}).
DOC_RATES = (
    FxRateObservation(currency_code="USD", rate=Decimal("1.0934")),
    FxRateObservation(currency_code="JPY", rate=Decimal("160.1234")),
    FxRateObservation(currency_code="EUR", rate=Decimal("1.0")),
    FxRateObservation(currency_code="GBP", rate=Decimal("0.8567")),
)
DOC_PROVIDER_ID = "ECB"
DOC_BASE = "EUR"


def _next_brussels_local(weekday: int, hour: int = 9) -> datetime:
    """Next FUTURE instant at ``hour`` Brussels local time on the given
    weekday (0=Monday..6=Sunday). 09:00 local is never in the ambiguous
    DST-transition window (01:00-02:00 local), so construction is safe."""
    now_utc = datetime.now(UTC)
    now_br = now_utc.astimezone(BRUSSELS)
    for delta in range(0, 8):
        d = now_br.date() + timedelta(days=delta)
        candidate = datetime(d.year, d.month, d.day, hour, 0, 0,
                             tzinfo=BRUSSELS)
        if candidate.weekday() == weekday and candidate > now_utc:
            return candidate
    raise AssertionError("unreachable: no future weekend instant found")


# Pinned instants (FUTURE, deterministic weekdays):
SAT_09 = _next_brussels_local(5)      # Saturday 09:00 Brussels
SUN_09 = SAT_09 + timedelta(days=1)   # Sunday 09:00 Brussels
MON_09 = SAT_09 + timedelta(days=2)   # Monday 09:00 Brussels
MON_10 = MON_09 + timedelta(hours=1)  # Monday 10:00 Brussels

# The document's observation date: the Friday before SAT_09.
DOC_OBS_DATE = (SAT_09 - timedelta(days=1)).date()


def _doc_xml(observation_date: date = DOC_OBS_DATE) -> bytes:
    rows = "\n".join(
        f'      <Cube currency="{r.currency_code}" rate="{r.rate}"/>'
        for r in DOC_RATES
    )
    return f"""<?xml version="1.0" encoding="UTF-8"?>
<gesmes:Envelope xmlns:gesmes="http://www.gesmes.org/xml/2002-08-01"
                 xmlns="http://www.ecb.int/vocabulary/2002-08-01/eurofxref">
  <Cube><Cube><TimeSeries>
    <Cube time="{observation_date.isoformat()}">
{rows}
    </Cube>
  </TimeSeries></Cube></Cube>
</gesmes:Envelope>
""".encode("utf-8")


class _FakeResponse:
    def __init__(self, body: bytes) -> None:
        self._body = body

    def read(self, size: int = -1) -> bytes:
        return self._body

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return None


def _seed_store_row(
    *,
    last_proven_at: datetime,
    original_retrieved_at: datetime | None = None,
    observation_date: date = DOC_OBS_DATE,
    payload: dict | None = None,
    rates: tuple[FxRateObservation, ...] | None = None,
) -> FxObservationStore:
    """Seed a store row directly (pinned instants; digest-consistent)."""
    rates = rates if rates is not None else DOC_RATES
    original_retrieved_at = (
        original_retrieved_at
        if original_retrieved_at is not None
        else last_proven_at - timedelta(minutes=2)
    )
    return FxObservationStore.objects.create(
        feed_id=FX_FEED_ID_ECB_DAILY,
        provider_id=DOC_PROVIDER_ID,
        base_currency=DOC_BASE,
        observation_date=observation_date,
        content_sha256=fx_document_content_sha256(
            provider_id=DOC_PROVIDER_ID, base_currency=DOC_BASE,
            observation_date=observation_date,
            rates=[(r.currency_code, r.rate) for r in rates],
        ),
        payload=payload if payload is not None else encode_fx_observation(
            provider_id=DOC_PROVIDER_ID, observation_date=observation_date,
            base_currency=DOC_BASE, rates=rates,
            retrieved_at=original_retrieved_at,
        ),
        original_retrieved_at=original_retrieved_at,
        last_proven_at=last_proven_at,
        created_at=original_retrieved_at,
    )


@pytest.fixture(autouse=True)
def _clean_fx_cache_rows():
    """Explicit per-test isolation (shared in-memory test database;
    this repo has no pytest-django). The run cascade cleanup is the
    existing autouse ``clean_execution_runs`` fixture."""
    yield
    FxObservationStore.objects.all().delete()


# ---------------------------------------------------------------------------
# Run pipeline helpers (mocked search + page with an EUR bucket)
# ---------------------------------------------------------------------------


def _eur_page_html() -> str:
    return """
    <html><head>
    <script type="application/ld+json">
    {
        "@context": "https://schema.org",
        "@type": "Product",
        "name": "Test Product",
        "mpn": "MZ-QL23T800",
        "offers": [
            {
                "@type": "Offer",
                "price": "1700.00",
                "priceCurrency": "EUR",
                "itemCondition": "https://schema.org/NewCondition"
            }
        ]
    }
    </script></head><body>Test</body></html>
    """


def _usd_page_html() -> str:
    return _eur_page_html().replace(
        '"priceCurrency": "EUR"', '"priceCurrency": "USD"'
    )


def _make_pipeline():
    """Mocked search + page pipeline (deterministic, no network)."""
    html = _eur_page_html()
    search_result = SearchResult(
        source_url="https://example.com/product",
        title="Test Product",
        snippet="Test",
        price_hint_text=None,
        part_number_hint="MZ-QL23T800",
        raw_reference=None,
    )
    response = SearchResponse(
        provider_id="test",
        query=SearchQuery(text="test"),
        retrieved_at=datetime.now(tz=UTC),
        results=(search_result,),
        raw_response_reference=None,
    )
    provider = MagicMock(spec=SearchProvider)
    provider.search.return_value = response

    def fake_fetch(request: PageFetchRequest) -> FetchedPage:
        return FetchedPage(
            requested_url=request.url,
            final_url=request.url,
            retrieved_at=datetime.now(tz=UTC),
            status_code=200,
            body_text=html,
            content_type="text/html",
            body_byte_count=len(html.encode("utf-8")),
            redirect_count=0,
            fetcher_id="test",
        )

    page_fetcher = MagicMock()
    page_fetcher.fetch.side_effect = fake_fetch
    return provider, page_fetcher


def _make_usd_pipeline():
    provider, page_fetcher = _make_pipeline()
    html = _usd_page_html()

    def fake_fetch(request: PageFetchRequest) -> FetchedPage:
        return FetchedPage(
            requested_url=request.url,
            final_url=request.url,
            retrieved_at=datetime.now(tz=UTC),
            status_code=200,
            body_text=html,
            content_type="text/html",
            body_byte_count=len(html.encode("utf-8")),
            redirect_count=0,
            fetcher_id="test",
        )

    page_fetcher.fetch.side_effect = fake_fetch
    return provider, page_fetcher


def _run_canonical(research_run: ResearchRun, page_html: str | None = None):
    """Canonical path: fx_provider=None (the cache-eligible path)."""
    if page_html is None:
        search_provider, page_fetcher = _make_pipeline()
    else:
        search_provider, page_fetcher = _make_usd_pipeline()
    return execute_research_run(
        str(research_run.id),
        search_provider=search_provider,
        page_fetcher=page_fetcher,
    )


def _arm_store_sentinels():
    """Patch both cache-service entry points to raise if touched."""
    return (
        patch.object(
            fx_observation_cache, "try_reuse_latest_observation",
            side_effect=AssertionError("cache store was read"),
        ),
        patch.object(
            fx_observation_cache, "record_live_observation",
            side_effect=AssertionError("cache store was written"),
        ),
    )


class _UrlopenPatch:
    """Context manager exposing ``.mock`` (the urlopen MagicMock)."""

    def __init__(self, patcher, mock) -> None:
        self._patcher = patcher
        self.mock = mock

    def __enter__(self):
        self._patcher.start()
        return self

    def __exit__(self, *args):
        self._patcher.stop()
        return None


def _arm_urlopen(body: bytes | None = None, *, fail: bool = False):
    """Patch urllib.request.urlopen: valid ECB document by default;
    armed fail-fast when ``fail`` (zero-network assertions)."""
    if fail:
        mock = MagicMock(
            side_effect=AssertionError("live ECB call during zero-network")
        )
    elif body is None:
        mock = MagicMock(return_value=_FakeResponse(_doc_xml()))
    else:
        mock = MagicMock(return_value=_FakeResponse(body))
    return _UrlopenPatch(patch("urllib.request.urlopen", mock), mock)


class _FakeFxProvider:
    """Deterministic injected provider (records its exact call)."""

    def __init__(self, *, fail: bool = False) -> None:
        self.call_count = 0
        self.last_requested: frozenset[str] | None = None
        self._fail = fail

    def fetch_rates(
        self, requested_currencies: frozenset[str] | None = None,
    ) -> FxObservationSet:
        self.call_count += 1
        self.last_requested = requested_currencies
        if self._fail:
            raise FxProviderError("simulated FX failure")
        rates = DOC_RATES
        if requested_currencies:
            upper = frozenset(c.strip().upper() for c in requested_currencies)
            rates = tuple(r for r in DOC_RATES if r.currency_code in upper)
        return FxObservationSet(
            provider_id="ECB",
            observation_date=DOC_OBS_DATE,
            base_currency="EUR",
            rates=rates,
            retrieved_at=datetime(2026, 6, 1, 12, 0, 0, tzinfo=UTC),
        )


class _CountingEcbSubclass(EcbFxProvider):
    """Explicit subclass injection: must bypass the cache like any
    injected provider (class identity is not eligibility)."""

    def __init__(self) -> None:
        super().__init__()
        self.call_count = 0

    def fetch_rates(self, requested_currencies=None) -> FxObservationSet:
        self.call_count += 1
        return super().fetch_rates(requested_currencies=requested_currencies)


class _WrapperProvider:
    """Wrapper around EcbFxProvider: injected => bypasses the cache."""

    def __init__(self) -> None:
        self.inner = EcbFxProvider()
        self.call_count = 0

    def fetch_rates(self, requested_currencies=None) -> FxObservationSet:
        self.call_count += 1
        return self.inner.fetch_rates(
            requested_currencies=requested_currencies,
        )


# ===========================================================================
# USD-only: zero cache + zero provider
# ===========================================================================


class TestUsdOnlyZeroWork:
    def test_usd_only_zero_cache_zero_provider(self, research_run):
        # A reusable weekend row exists; the run must not touch it.
        _seed_store_row(last_proven_at=SAT_09 - timedelta(minutes=2))
        read_sentinel, write_sentinel = _arm_store_sentinels()
        urlopen = _arm_urlopen(fail=True)
        with read_sentinel, write_sentinel, urlopen, patch.object(
            fx_observation_cache, "_utc_now", return_value=SAT_09,
        ):
            result = _run_canonical(research_run, page_html=_usd_page_html())
        assert result.run.current_state == ResearchRunState.COMPLETED
        # Discovery first: zero provider calls AND zero cache work.
        urlopen.mock.assert_not_called()
        with pytest.raises(ResearchFxSnapshot.DoesNotExist):
            ResearchFxSnapshot.objects.get(run=research_run)
        # The seeded row is untouched (still exactly one).
        assert FxObservationStore.objects.count() == 1


# ===========================================================================
# Canonical LIVE path
# ===========================================================================


class TestCanonicalLive:
    def test_live_empty_store_one_fetch_row_written(
        self, research_run,
    ):
        with _arm_urlopen() as urlopen, patch.object(
            fx_observation_cache, "_utc_now", return_value=SAT_09,
        ):
            result = _run_canonical(research_run)
            # The provider's OWN filtered fetch of the same mocked
            # document (projection-equivalence reference).
            direct = EcbFxProvider().fetch_rates(
                requested_currencies=frozenset({"USD", "EUR"}),
            )
        assert result.run.current_state == ResearchRunState.COMPLETED
        # Exactly ONE full-set provider fetch for the run (the direct
        # reference call above is a separate, test-side fetch).
        assert urlopen.mock.call_count == 2
        # The cross-run content entry was persisted (full document).
        assert FxObservationStore.objects.count() == 1
        row = FxObservationStore.objects.get()
        assert row.feed_id == FX_FEED_ID_ECB_DAILY
        assert row.observation_date == DOC_OBS_DATE
        assert row.last_proven_at == SAT_09  # pinned successful proof
        # original retrieved_at is the provider's own instant (real wall
        # clock of the mocked fetch) — close to now, not the proof pin.
        assert (
            abs((row.original_retrieved_at - datetime.now(UTC)).total_seconds())
            < 300
        )
        codes = {e["currency_code"] for e in row.payload["rates"]}
        assert codes == {"USD", "JPY", "EUR", "GBP"}  # FULL set stored
        # The run's own snapshot: LIVE acquisition, projected rates.
        fx = ResearchFxSnapshot.objects.get(run=research_run)
        assert fx.acquisition == ResearchFxSnapshot.ACQUISITION_LIVE
        decoded = decode_fx_observation(fx.payload)
        assert [e.currency_code for e in decoded.rates] == ["USD", "EUR"]
        # Projection equivalence: the canonical payload equals the
        # provider's OWN filtered fetch of the same document (all
        # fields except the two distinct live fetch instants).
        expected = encode_fx_observation(
            provider_id="ECB", observation_date=DOC_OBS_DATE,
            base_currency="EUR", rates=direct.rates,
            retrieved_at=direct.retrieved_at,
        )
        assert fx.payload["rates"] == expected["rates"]
        assert fx.payload["provider_id"] == expected["provider_id"]
        assert fx.payload["observation_date"] == expected["observation_date"]
        assert fx.payload["base_currency"] == expected["base_currency"]
        assert fx.payload["schema_version"] == 1

    def test_live_working_day_proof_stays_live(self, research_run):
        # A row proven Monday (working day) is NEVER reusable: the run
        # live-fetches and re-proves (bounded reconciliation converges
        # on the same content identity via the real uniqueness constraint).
        row = _seed_store_row(last_proven_at=MON_09)
        seeded_id = row.id
        urlopen = _arm_urlopen()
        with urlopen, patch.object(
            fx_observation_cache, "_utc_now", return_value=MON_10,
        ):
            result = _run_canonical(research_run)
        assert result.run.current_state == ResearchRunState.COMPLETED
        assert urlopen.mock.call_count == 1
        fx = ResearchFxSnapshot.objects.get(run=research_run)
        assert fx.acquisition == ResearchFxSnapshot.ACQUISITION_LIVE
        # Converged: still ONE row for the identical content (same
        # identity); the proof instant advanced; original retrieval
        # untouched.
        assert FxObservationStore.objects.count() == 1
        row.refresh_from_db()
        assert row.id == seeded_id
        assert row.last_proven_at == MON_10
        assert row.original_retrieved_at == row.created_at

    def test_live_monday_boundary_revalidates(self, research_run):
        # Saturday proof; use at Monday 09:00 Brussels (the stretch
        # edge): NOT reusable -> live revalidation, re-proof converges.
        row = _seed_store_row(last_proven_at=SAT_09)
        original_retrieved = row.original_retrieved_at
        urlopen = _arm_urlopen()
        with urlopen, patch.object(
            fx_observation_cache, "_utc_now", return_value=MON_09,
        ):
            result = _run_canonical(research_run)
        assert result.run.current_state == ResearchRunState.COMPLETED
        assert urlopen.mock.call_count == 1
        assert (
            ResearchFxSnapshot.objects.get(run=research_run).acquisition
            == ResearchFxSnapshot.ACQUISITION_LIVE
        )
        row.refresh_from_db()
        assert row.last_proven_at == MON_09
        assert row.original_retrieved_at == original_retrieved


# ===========================================================================
# Canonical CACHE_HIT path
# ===========================================================================


class TestCanonicalCacheHit:
    ORIGINAL = SAT_09 - timedelta(minutes=4)  # pinned original retrieval
    PROOF = SAT_09 - timedelta(minutes=2)     # pinned proof (reusable state)

    def test_cache_hit_zero_provider_calls(self, research_run):
        _seed_store_row(
            last_proven_at=self.PROOF, original_retrieved_at=self.ORIGINAL,
        )
        urlopen = _arm_urlopen(fail=True)  # armed fail-fast
        with urlopen, patch.object(
            fx_observation_cache, "_utc_now", return_value=SAT_09,
        ):
            result = _run_canonical(research_run)
        assert result.run.current_state == ResearchRunState.COMPLETED
        # ZERO ECB calls on a hit.
        urlopen.mock.assert_not_called()
        # The current run receives its OWN ResearchFxSnapshot.
        fx = ResearchFxSnapshot.objects.get(run=research_run)
        assert fx.acquisition == ResearchFxSnapshot.ACQUISITION_CACHE_HIT
        assert fx.schema_version == 1
        decoded = decode_fx_observation(fx.payload)
        # Required currencies projected from the FULL cached set
        # (document order preserved: USD before EUR).
        assert [e.currency_code for e in decoded.rates] == ["USD", "EUR"]
        assert decoded.rates[0].rate == Decimal("1.0934")
        assert decoded.rates[1].rate == Decimal("1.0")
        # The ORIGINAL provider retrieved_at is preserved — never the
        # serving time (SAT_09 pin), never re-stamped.
        assert decoded.retrieved_at == self.ORIGINAL.astimezone(UTC).strftime(
            "%Y-%m-%dT%H:%M:%S+00:00"
        )
        # The store row is untouched by the read.
        assert FxObservationStore.objects.count() == 1
        row = FxObservationStore.objects.get()
        assert row.last_proven_at == self.PROOF

    def test_sunday_reuse_of_saturday_proof(self, research_run):
        _seed_store_row(last_proven_at=SAT_09 - timedelta(minutes=2))
        urlopen = _arm_urlopen(fail=True)
        with urlopen, patch.object(
            fx_observation_cache, "_utc_now", return_value=SUN_09,
        ):
            result = _run_canonical(research_run)
        assert result.run.current_state == ResearchRunState.COMPLETED
        urlopen.mock.assert_not_called()
        assert (
            ResearchFxSnapshot.objects.get(run=research_run).acquisition
            == ResearchFxSnapshot.ACQUISITION_CACHE_HIT
        )

    def test_cache_hit_payload_byte_identity_with_live_document(
        self, research_run,
    ):
        # The run payload under CACHE_HIT is the same V1 codec shape as
        # under LIVE for the same document (identical rates; retrieved_at
        # is the original — the LIVE path's retrieved_at differs only in
        # being its own fetch instant).
        _seed_store_row(
            last_proven_at=self.PROOF, original_retrieved_at=self.ORIGINAL,
        )
        with _arm_urlopen(fail=True), patch.object(
            fx_observation_cache, "_utc_now", return_value=SAT_09,
        ):
            result = _run_canonical(research_run)
        fx = ResearchFxSnapshot.objects.get(run=research_run)
        decoded = decode_fx_observation(fx.payload)
        assert decoded.retrieved_at == self.ORIGINAL.astimezone(UTC).strftime(
            "%Y-%m-%dT%H:%M:%S+00:00"
        )
        expected_payload = encode_fx_observation(
            provider_id="ECB",
            observation_date=DOC_OBS_DATE,
            base_currency="EUR",
            rates=(
                FxRateObservation(currency_code="USD", rate=Decimal("1.0934")),
                FxRateObservation(currency_code="EUR", rate=Decimal("1.0")),
            ),
            retrieved_at=self.ORIGINAL,
        )
        assert fx.payload == expected_payload


# ===========================================================================
# Injected providers: unconditional cache bypass
# ===========================================================================


class TestInjectedProviderBypass:
    def test_explicit_fake_provider_bypasses_cache(self, research_run):
        # A reusable weekend row exists; the injected fake must NOT
        # read or write it and must make today's exact filtered call.
        _seed_store_row(last_proven_at=SAT_09 - timedelta(minutes=2))
        read_sentinel, write_sentinel = _arm_store_sentinels()
        fake = _FakeFxProvider()
        with read_sentinel, write_sentinel:
            result = execute_research_run(
                str(research_run.id),
                search_provider=_make_pipeline()[0],
                page_fetcher=_make_pipeline()[1],
                fx_provider=fake,
            )
        assert result.run.current_state == ResearchRunState.COMPLETED
        assert fake.call_count == 1
        # Today's exact call: provider-side filtering with the required set.
        assert fake.last_requested is not None
        assert fake.last_requested == frozenset({"USD", "EUR"})
        fx = ResearchFxSnapshot.objects.get(run=research_run)
        assert fx.acquisition == ResearchFxSnapshot.ACQUISITION_LIVE
        assert fx.schema_version == 1
        # The store is untouched.
        assert FxObservationStore.objects.count() == 1
        row = FxObservationStore.objects.get()
        assert row.last_proven_at == SAT_09 - timedelta(minutes=2)

    def test_explicit_real_ecb_instance_bypasses_cache(self, research_run):
        # Class identity is not eligibility: an explicitly constructed
        # EcbFxProvider (the canonical class itself) is an injection and
        # bypasses the cache entirely.
        _seed_store_row(last_proven_at=SAT_09 - timedelta(minutes=2))
        read_sentinel, write_sentinel = _arm_store_sentinels()
        urlopen = _arm_urlopen()
        provider = EcbFxProvider()
        with read_sentinel, write_sentinel, urlopen, patch.object(
            fx_observation_cache, "_utc_now", return_value=SAT_09,
        ):
            result = execute_research_run(
                str(research_run.id),
                search_provider=_make_pipeline()[0],
                page_fetcher=_make_pipeline()[1],
                fx_provider=provider,
            )
        assert result.run.current_state == ResearchRunState.COMPLETED
        # Live fetch happened (bypass), and the store was never touched.
        assert urlopen.mock.call_count == 1
        assert FxObservationStore.objects.count() == 1
        assert (
            ResearchFxSnapshot.objects.get(run=research_run).acquisition
            == ResearchFxSnapshot.ACQUISITION_LIVE
        )

    def test_explicit_subclass_bypasses_cache(self, research_run):
        _seed_store_row(last_proven_at=SAT_09 - timedelta(minutes=2))
        read_sentinel, write_sentinel = _arm_store_sentinels()
        urlopen = _arm_urlopen()
        sub = _CountingEcbSubclass()
        with read_sentinel, write_sentinel, urlopen:
            result = execute_research_run(
                str(research_run.id),
                search_provider=_make_pipeline()[0],
                page_fetcher=_make_pipeline()[1],
                fx_provider=sub,
            )
        assert result.run.current_state == ResearchRunState.COMPLETED
        assert sub.call_count == 1
        assert urlopen.mock.call_count == 1  # injected adapter is live
        assert FxObservationStore.objects.count() == 1  # zero store writes

    def test_explicit_wrapper_bypasses_cache(self, research_run):
        _seed_store_row(last_proven_at=SAT_09 - timedelta(minutes=2))
        read_sentinel, write_sentinel = _arm_store_sentinels()
        urlopen = _arm_urlopen()
        wrapper = _WrapperProvider()
        with read_sentinel, write_sentinel, urlopen:
            result = execute_research_run(
                str(research_run.id),
                search_provider=_make_pipeline()[0],
                page_fetcher=_make_pipeline()[1],
                fx_provider=wrapper,
            )
        assert result.run.current_state == ResearchRunState.COMPLETED
        assert wrapper.call_count == 1
        assert urlopen.mock.call_count == 1
        assert FxObservationStore.objects.count() == 1


# ===========================================================================
# Failure semantics
# ===========================================================================


class TestFailureSemantics:
    def test_live_provider_error_remains_nonfatal(self, research_run):
        # Canonical path, empty store, live fetch fails (network):
        # NONFATAL — run completes, no snapshot, store untouched.
        mock_urlopen = MagicMock(
            side_effect=urllib.error.URLError("simulated outage")
        )
        with patch("urllib.request.urlopen", mock_urlopen), patch.object(
            fx_observation_cache, "_utc_now", return_value=SAT_09,
        ):
            result = _run_canonical(research_run)
        assert result.run.current_state == ResearchRunState.COMPLETED
        with pytest.raises(ResearchFxSnapshot.DoesNotExist):
            ResearchFxSnapshot.objects.get(run=research_run)
        assert FxObservationStore.objects.count() == 0

    def test_injected_provider_error_remains_nonfatal(self, research_run):
        fake = _FakeFxProvider(fail=True)
        result = execute_research_run(
            str(research_run.id),
            search_provider=_make_pipeline()[0],
            page_fetcher=_make_pipeline()[1],
            fx_provider=fake,
        )
        assert result.run.current_state == ResearchRunState.COMPLETED
        assert fake.call_count == 1
        with pytest.raises(ResearchFxSnapshot.DoesNotExist):
            ResearchFxSnapshot.objects.get(run=research_run)

    def test_cache_corruption_propagates_not_live_fallback(
        self, research_run,
    ):
        # A corrupt EXISTING cache payload in an otherwise reusable
        # weekend state is NOT a cache miss: it fails closed and the
        # live path is NOT silently taken.
        _seed_store_row(
            last_proven_at=SAT_09 - timedelta(minutes=2),
            payload={"garbage": True},
        )
        urlopen = _arm_urlopen(fail=True)  # must NOT be called
        with urlopen, patch.object(
            fx_observation_cache, "_utc_now", return_value=SAT_09,
        ):
            with pytest.raises(ExecutionError):
                _run_canonical(research_run)
        urlopen.mock.assert_not_called()
        research_run.refresh_from_db()
        assert research_run.current_state == ResearchRunState.FAILED
        # The corrupted row remains (visible, never deleted).
        assert FxObservationStore.objects.count() == 1

    def test_unsupported_cache_codec_propagates(self, research_run):
        payload = encode_fx_observation(
            provider_id="ECB", observation_date=DOC_OBS_DATE,
            base_currency="EUR", rates=DOC_RATES,
            retrieved_at=SAT_09 - timedelta(minutes=2),
        )
        payload["schema_version"] = 99
        _seed_store_row(
            last_proven_at=SAT_09 - timedelta(minutes=2), payload=payload,
        )
        urlopen = _arm_urlopen(fail=True)
        with urlopen, patch.object(
            fx_observation_cache, "_utc_now", return_value=SAT_09,
        ):
            with pytest.raises(ExecutionError):
                _run_canonical(research_run)
        urlopen.mock.assert_not_called()
        research_run.refresh_from_db()
        assert research_run.current_state == ResearchRunState.FAILED

    def test_unexpected_storage_error_propagates(self, research_run):
        from django.db import OperationalError

        urlopen = _arm_urlopen()
        with urlopen, patch.object(
            fx_observation_cache, "_utc_now", return_value=SAT_09,
        ), patch.object(
            FxObservationStore.objects, "create",
            side_effect=OperationalError("disk full"),
        ):
            with pytest.raises(ExecutionError):
                _run_canonical(research_run)
        # Live fetch happened (one call) but the run did NOT complete:
        # a storage failure is not silently swallowed.
        assert urlopen.mock.call_count == 1
        research_run.refresh_from_db()
        assert research_run.current_state == ResearchRunState.FAILED
        assert FxObservationStore.objects.count() == 0


# ===========================================================================
# Run publication atomicity (cache content outlives run publication)
# ===========================================================================


class TestRunPublicationAtomicity:
    def test_cache_row_survives_failed_run_publication(self, research_run):
        # Live ECB fetch succeeds, cache content is persisted (its own
        # transaction), then the current-run publication fails. The
        # cache row remains legitimate external evidence and must not
        # imply the run completed.
        from product_intelligence.runs import (
            complete_execution as real_complete_execution,
        )

        def _fail_only_completed(run, *, target_state):
            if target_state == ResearchRunState.COMPLETED:
                raise RuntimeError("simulated publication failure")
            return real_complete_execution(run=run, target_state=target_state)

        with _arm_urlopen() as urlopen, patch.object(
            fx_observation_cache, "_utc_now", return_value=SAT_09,
        ), patch(
            "product_intelligence.execution.orchestration.complete_execution",
            side_effect=_fail_only_completed,
        ):
            with pytest.raises(ExecutionError):
                _run_canonical(research_run)
        # Store row persisted (its transaction completed).
        assert FxObservationStore.objects.count() == 1
        row = FxObservationStore.objects.get()
        assert row.last_proven_at == SAT_09
        # The run did NOT complete; no run snapshot was published.
        research_run.refresh_from_db()
        assert research_run.current_state == ResearchRunState.FAILED
        with pytest.raises(PriceIntelligenceSnapshot.DoesNotExist):
            PriceIntelligenceSnapshot.objects.get(run=research_run)
        with pytest.raises(ResearchFxSnapshot.DoesNotExist):
            ResearchFxSnapshot.objects.get(run=research_run)
        # The cache row carries no run authority (no run linkage at all).
        assert not hasattr(row, "run")

    def test_a_later_run_may_legitimately_reuse_the_surviving_row(self):
        # A later canonical run in a reusable state may serve from a
        # surviving store row (it is feed data, proven by a live
        # acquisition — run authority is not attached to it).
        _seed_store_row(
            last_proven_at=SAT_09 - timedelta(minutes=2),
            original_retrieved_at=SAT_09 - timedelta(minutes=4),
        )
        assert FxObservationStore.objects.count() == 1
        new_run = ResearchRun.objects.create_from_request(
            ResearchRequest(
                manufacturer_part_number="MZ-QL23T800",
                description="Samsung SSD 970 EVO Plus 1TB",
            )
        )
        urlopen = _arm_urlopen(fail=True)
        with urlopen, patch.object(
            fx_observation_cache, "_utc_now", return_value=SAT_09,
        ):
            result2 = _run_canonical(new_run)
        assert result2.run.current_state == ResearchRunState.COMPLETED
        urlopen.mock.assert_not_called()
        assert (
            ResearchFxSnapshot.objects.get(run=new_run).acquisition
            == ResearchFxSnapshot.ACQUISITION_CACHE_HIT
        )


# ===========================================================================
# Concurrency
# ===========================================================================


class TestConcurrency:
    def test_identical_concurrent_content_converges_on_one_row(self):
        # Deterministic reproduction of the concurrent double-miss race:
        # two runs start with the store empty, BOTH evaluate their
        # pre-fetch lookup before either insert commits, and BOTH then
        # live-fetch the same document. Run A's insert commits first;
        # run B's insert hits the REAL uniqueness constraint and the
        # bounded reconciliation converges. (True in-flight DB writers
        # are not exercised here: the pilot's single-node shared-cache
        # SQLite serializes writers, and the repository's concurrency
        # discipline — deterministic uniqueness + bounded
        # reconciliation, no locking — is what is under test.)
        run_a = ResearchRun.objects.create_from_request(
            ResearchRequest(manufacturer_part_number="MZ-QL23T800",
                            description="concurrent A")
        )
        run_b = ResearchRun.objects.create_from_request(
            ResearchRequest(manufacturer_part_number="MZ-QL23T800",
                            description="concurrent B")
        )
        # Phase 1: run A reaches the empty store first and commits its
        # content row.
        with _arm_urlopen(), patch.object(
            fx_observation_cache, "_utc_now", return_value=SAT_09,
        ):
            sp_a, pf_a = _make_pipeline()
            result_a = execute_research_run(
                str(run_a.id), search_provider=sp_a, page_fetcher=pf_a,
            )
        assert result_a.run.current_state == ResearchRunState.COMPLETED
        assert FxObservationStore.objects.count() == 1
        # Phase 2: run B's lookup had already seen the (concurrently)
        # empty store; its real insert now collides and reconciles.
        with _arm_urlopen(), patch.object(
            fx_observation_cache, "_utc_now", return_value=SAT_09,
        ), patch.object(
            fx_observation_cache, "try_reuse_latest_observation",
            return_value=None,
        ):
            sp_b, pf_b = _make_pipeline()
            result_b = execute_research_run(
                str(run_b.id), search_provider=sp_b, page_fetcher=pf_b,
            )
        assert result_b.run.current_state == ResearchRunState.COMPLETED
        # ONE row for the identical content; both runs published their
        # own LIVE snapshots; no IntegrityError escaped.
        assert FxObservationStore.objects.count() == 1
        row = FxObservationStore.objects.get()
        assert row.last_proven_at == SAT_09
        assert (
            ResearchFxSnapshot.objects.get(run=run_a).acquisition
            == ResearchFxSnapshot.ACQUISITION_LIVE
        )
        assert (
            ResearchFxSnapshot.objects.get(run=run_b).acquisition
            == ResearchFxSnapshot.ACQUISITION_LIVE
        )

    def test_same_date_changed_content_remains_distinct(self):
        # A correction (same observation_date, changed rates) yields a
        # distinct content identity — never overwriting the revision.
        first = _seed_store_row(last_proven_at=MON_09)
        corrected = (
            FxRateObservation(currency_code="USD", rate=Decimal("1.0950")),
        ) + DOC_RATES[1:]
        second = _seed_store_row(
            last_proven_at=MON_10,
            original_retrieved_at=MON_10 - timedelta(minutes=2),
            rates=corrected,
        )
        assert first.content_sha256 != second.content_sha256
        assert FxObservationStore.objects.count() == 2
        # Latest selection serves the most recently proven revision.
        latest = (
            FxObservationStore.objects.filter(feed_id=FX_FEED_ID_ECB_DAILY)
            .order_by("-observation_date", "-last_proven_at")
            .first()
        )
        assert latest.id == second.id


# ===========================================================================
# Replay: zero live, zero cache, provenance preserved
# ===========================================================================


class TestReplayBehavior:
    def _completed_cache_hit_run(self, research_run) -> ResearchRun:
        _seed_store_row(last_proven_at=SAT_09 - timedelta(minutes=2))
        with _arm_urlopen(fail=True), patch.object(
            fx_observation_cache, "_utc_now", return_value=SAT_09,
        ):
            result = _run_canonical(research_run)
        assert result.run.current_state == ResearchRunState.COMPLETED
        return research_run

    def test_replay_performs_no_live_or_cache_work(self, research_run):
        run = self._completed_cache_hit_run(research_run)
        fx_before = ResearchFxSnapshot.objects.get(run=run)
        assert fx_before.acquisition == ResearchFxSnapshot.ACQUISITION_CACHE_HIT

        read_sentinel, write_sentinel = _arm_store_sentinels()
        urlopen = _arm_urlopen(fail=True)
        with read_sentinel, write_sentinel, urlopen:
            replay = replay_compact_quote_projection(str(run.id))
            public_replay = replay_public_compact_quote_projection(run=run)

        urlopen.mock.assert_not_called()
        # The replay read the persisted snapshot (FX present in both).
        assert replay.fx_snapshot is not None
        assert public_replay.fx_snapshot is not None
        # Provenance preserved: replay never mutates the stored value.
        fx_after = ResearchFxSnapshot.objects.get(run=run)
        assert fx_after.acquisition == ResearchFxSnapshot.ACQUISITION_CACHE_HIT
        assert fx_after.payload == fx_before.payload
        # The compact quote projection carries the FX-based USD equivalent.
        rows = [
            r for r in replay.projection.rows
            if r.usd_equivalent and r.usd_equivalent != "Unavailable"
        ]
        assert rows, "expected a USD-equivalent quote row from persisted FX"

    def test_replay_of_live_run_preserves_live(self, research_run):
        # A run acquired LIVE replays as LIVE (never relabeled).
        with _arm_urlopen(), patch.object(
            fx_observation_cache, "_utc_now", return_value=SAT_09,
        ):
            result = _run_canonical(research_run)
        assert result.run.current_state == ResearchRunState.COMPLETED
        assert (
            ResearchFxSnapshot.objects.get(run=research_run).acquisition
            == ResearchFxSnapshot.ACQUISITION_LIVE
        )
        read_sentinel, write_sentinel = _arm_store_sentinels()
        with read_sentinel, write_sentinel, _arm_urlopen(fail=True):
            replay = replay_compact_quote_projection(str(research_run.id))
        assert replay.fx_snapshot is not None
        assert (
            ResearchFxSnapshot.objects.get(run=research_run).acquisition
            == ResearchFxSnapshot.ACQUISITION_LIVE
        )
