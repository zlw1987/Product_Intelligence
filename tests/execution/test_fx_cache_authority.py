"""Authority-invariance and eligibility-guard tests (PRODUCT-INTEL.8A-FX-A1).

Proves the cache cannot change anything but FX evidence ACQUISITION:

* Machine Price (the persisted PriceIntelligenceSnapshot) is
  byte-identical across LIVE / CACHE_HIT / FX-absent runs of the same
  request;
* the compact-quote USD equivalent is identical between a LIVE run and
  a CACHE_HIT run of the same document (FX stays DISPLAY-SUPPLEMENTAL);
* provider class identity is NOT cache-eligibility logic: the new
  cache modules contain no isinstance/issubclass over provider classes,
  and the orchestration declares eligibility exactly at the
  canonical-default construction site (``fx_provider is None``);
* the new orchestration FX step catches only the bounded
  ``FxProviderError`` (programming/contract defects propagate).
"""

from __future__ import annotations

import ast
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from pathlib import Path
from unittest.mock import MagicMock, patch
import urllib.error
from zoneinfo import ZoneInfo

import pytest

from product_intelligence.domain import ResearchRequest
from product_intelligence.domain.enums import ResearchRunState
from product_intelligence.execution import execute_research_run
from product_intelligence.execution import fx_observation_cache
from product_intelligence.execution.compact_quote_replay import (
    replay_compact_quote_projection,
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
from product_intelligence.research.fx_codec import encode_fx_observation
from product_intelligence.runs.models import (
    FxObservationStore,
    PriceIntelligenceSnapshot,
    ResearchFxSnapshot,
    ResearchRun,
)

UTC = timezone.utc

REPO_ROOT = Path(__file__).resolve().parents[2]

# Pinned FUTURE weekend instants (deterministic weekdays, and always
# after the provider's real wall-clock retrieved_at).
BRUSSELS = ZoneInfo("Europe/Brussels")


def _next_brussels_local(weekday: int, hour: int = 9) -> datetime:
    now_utc = datetime.now(UTC)
    now_br = now_utc.astimezone(BRUSSELS)
    for delta in range(0, 8):
        d = now_br.date() + timedelta(days=delta)
        candidate = datetime(d.year, d.month, d.day, hour, 0, 0,
                             tzinfo=BRUSSELS)
        if candidate.weekday() == weekday and candidate > now_utc:
            return candidate
    raise AssertionError("unreachable: no future weekend instant found")


SAT_09 = _next_brussels_local(5)
DOC_OBS_DATE = (SAT_09 - timedelta(days=1)).date()

DOC_RATES = (
    ("USD", Decimal("1.0934")),
    ("JPY", Decimal("160.1234")),
    ("EUR", Decimal("1.0")),
    ("GBP", Decimal("0.8567")),
)


@pytest.fixture(autouse=True)
def _clean_fx_cache_rows():
    yield
    FxObservationStore.objects.all().delete()
    ResearchRun.objects.all().delete()


def _doc_xml() -> bytes:
    rows = "\n".join(
        f'      <Cube currency="{code}" rate="{rate}"/>'
        for code, rate in DOC_RATES
    )
    return f"""<?xml version="1.0" encoding="UTF-8"?>
<gesmes:Envelope xmlns:gesmes="http://www.gesmes.org/xml/2002-08-01"
                 xmlns="http://www.ecb.int/vocabulary/2002-08-01/eurofxref">
  <Cube><Cube><TimeSeries>
    <Cube time="{DOC_OBS_DATE.isoformat()}">
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


def _arm_urlopen(*, fail: bool = False):
    if fail:
        mock = MagicMock(
            side_effect=urllib.error.URLError("simulated outage")
        )
    else:
        mock = MagicMock(return_value=_FakeResponse(_doc_xml()))
    return patch("urllib.request.urlopen", mock)


def _seed_reusable_row() -> FxObservationStore:
    """Ensure a reusable row for the canonical document (idempotent:
    a LIVE run of the same document may have already proved it)."""
    from product_intelligence.providers.fx import FxRateObservation

    rates = tuple(
        FxRateObservation(currency_code=c, rate=r) for c, r in DOC_RATES
    )
    digest = fx_document_content_sha256(
        provider_id="ECB", base_currency="EUR",
        observation_date=DOC_OBS_DATE, rates=list(DOC_RATES),
    )
    existing = FxObservationStore.objects.filter(
        feed_id="ecb:eurofxref-daily",
        observation_date=DOC_OBS_DATE,
        content_sha256=digest,
    ).first()
    if existing is not None:
        return existing
    original = SAT_09 - timedelta(minutes=4)
    return FxObservationStore.objects.create(
        feed_id="ecb:eurofxref-daily",
        provider_id="ECB",
        base_currency="EUR",
        observation_date=DOC_OBS_DATE,
        content_sha256=digest,
        payload=encode_fx_observation(
            provider_id="ECB", observation_date=DOC_OBS_DATE,
            base_currency="EUR", rates=rates, retrieved_at=original,
        ),
        original_retrieved_at=original,
        last_proven_at=SAT_09 - timedelta(minutes=2),
        created_at=original,
    )


def _make_run(description: str = "Authority invariance fixture") -> ResearchRun:
    return ResearchRun.objects.create_from_request(
        ResearchRequest(manufacturer_part_number="MZ-QL23T800",
                        description=description)
    )


def _pipeline():
    html = """
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
    sr = SearchResult(
        source_url="https://example.com/product", title="Test Product",
        snippet="Test", price_hint_text=None,
        part_number_hint="MZ-QL23T800", raw_reference=None,
    )
    resp = SearchResponse(
        provider_id="test", query=SearchQuery(text="test"),
        retrieved_at=datetime.now(tz=UTC), results=(sr,),
        raw_response_reference=None,
    )
    sp = MagicMock(spec=SearchProvider)
    sp.search.return_value = resp

    def ff(req: PageFetchRequest) -> FetchedPage:
        return FetchedPage(
            requested_url=req.url, final_url=req.url,
            retrieved_at=datetime.now(tz=UTC), status_code=200,
            body_text=html, content_type="text/html",
            body_byte_count=len(html.encode("utf-8")), redirect_count=0,
            fetcher_id="test",
        )

    pf = MagicMock()
    pf.fetch.side_effect = ff
    return sp, pf


# ===========================================================================
# Authority invariance under caching
# ===========================================================================


class TestAuthorityInvariance:
    """The cache substitutes only FX acquisition. Machine Price, the
    price snapshot bytes, and the USD-equivalent display are
    invariant."""

    def _live_run(self) -> ResearchRun:
        run = _make_run()
        with _arm_urlopen(), patch.object(
            fx_observation_cache, "_utc_now", return_value=SAT_09,
        ):
            result = execute_research_run(
                str(run.id), search_provider=_pipeline()[0],
                page_fetcher=_pipeline()[1],
            )
        assert result.run.current_state == ResearchRunState.COMPLETED
        return run

    def _cache_hit_run(self) -> ResearchRun:
        _seed_reusable_row()
        run = _make_run()
        with _arm_urlopen(fail=True), patch.object(
            fx_observation_cache, "_utc_now", return_value=SAT_09,
        ):
            result = execute_research_run(
                str(run.id), search_provider=_pipeline()[0],
                page_fetcher=_pipeline()[1],
            )
        assert result.run.current_state == ResearchRunState.COMPLETED
        return run

    def _fx_absent_run(self) -> ResearchRun:
        run = _make_run()
        with _arm_urlopen(fail=True), patch.object(
            fx_observation_cache, "_utc_now", return_value=SAT_09,
        ):
            result = execute_research_run(
                str(run.id), search_provider=_pipeline()[0],
                page_fetcher=_pipeline()[1],
            )
        assert result.run.current_state == ResearchRunState.COMPLETED
        return run

    def test_machine_price_bytes_identical_live_cachehit_fxabsent(self):
        # Ordered so each scenario sees the store state it documents:
        # FX-absent first (empty store; the failed live refresh writes
        # nothing), then LIVE (proves the document), then CACHE_HIT
        # (reuses the proven row — idempotent seed).
        run_absent = self._fx_absent_run()
        run_live = self._live_run()
        run_hit = self._cache_hit_run()

        # All three runs must carry FX-evidence-independent Machine
        # Price: identical persisted price snapshot payloads.
        p_live = PriceIntelligenceSnapshot.objects.get(run=run_live).payload
        p_hit = PriceIntelligenceSnapshot.objects.get(run=run_hit).payload
        p_absent = PriceIntelligenceSnapshot.objects.get(run=run_absent).payload
        assert p_live == p_hit == p_absent

        # FX acquisition states as expected (the only thing that differs).
        assert (
            ResearchFxSnapshot.objects.get(run=run_live).acquisition
            == ResearchFxSnapshot.ACQUISITION_LIVE
        )
        assert (
            ResearchFxSnapshot.objects.get(run=run_hit).acquisition
            == ResearchFxSnapshot.ACQUISITION_CACHE_HIT
        )
        with pytest.raises(ResearchFxSnapshot.DoesNotExist):
            ResearchFxSnapshot.objects.get(run=run_absent)

    def test_usd_equivalent_identical_live_vs_cache_hit(self):
        run_live = self._live_run()
        # The LIVE run above proved the document; the hit run reuses it.
        run_hit = self._cache_hit_run()

        def usd_rows(run: ResearchRun) -> list[str]:
            replay = replay_compact_quote_projection(str(run.id))
            return [
                row.usd_equivalent
                for row in replay.projection.rows
                if row.usd_equivalent and row.usd_equivalent != "Unavailable"
            ]

        assert usd_rows(run_live) == usd_rows(run_hit)
        assert usd_rows(run_live), "expected a USD-equivalent row"
        # Original price/currency stay authoritative in both.
        replay_hit = replay_compact_quote_projection(str(run_hit.id))
        currencies = {
            row.price_currency
            for row in replay_hit.projection.rows
            if row.price_currency
        }
        assert "EUR" in currencies


# ===========================================================================
# Eligibility guards: provider class identity is NOT cache semantics
# ===========================================================================


def _function_source(path: Path, func_name: str) -> str:
    text = path.read_text(encoding="utf-8")
    tree = ast.parse(text)
    for node in tree.body:
        if isinstance(node, ast.FunctionDef) and node.name == func_name:
            return ast.get_source_segment(text, node)
    raise AssertionError(f"{func_name} not found in {path}")


def _parse_function(path: Path, func_name: str) -> ast.Module:
    """Parse one top-level function's source segment on its own."""
    return ast.parse(_function_source(path, func_name))


PROVIDER_CLASS_NAMES = {
    "EcbFxProvider", "FxProvider", "FxObservationSet", "FxRateObservation",
}


class TestEligibilityGuards:
    """Mechanical proof that cache eligibility is the canonical-default
    declaration (``fx_provider is None``), not provider-class identity."""

    def test_cache_service_has_no_provider_class_identity_checks(self):
        path = (
            REPO_ROOT / "product_intelligence" / "execution"
            / "fx_observation_cache.py"
        )
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
                if node.func.id in ("isinstance", "issubclass"):
                    names = {
                        n.id for n in ast.walk(node)
                        if isinstance(n, ast.Name)
                    }
                    assert not (names & PROVIDER_CLASS_NAMES), (
                        f"provider class identity used in "
                        f"{node.func.id}(): {sorted(names)}"
                    )

    def test_pure_contract_has_no_provider_class_identity_checks(self):
        path = (
            REPO_ROOT / "product_intelligence" / "research"
            / "fx_cache_contract.py"
        )
        source = path.read_text(encoding="utf-8")
        for name in sorted(PROVIDER_CLASS_NAMES):
            assert name not in source
        tree = ast.parse(source)
        for node in ast.walk(tree):
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
                if node.func.id in ("isinstance", "issubclass"):
                    names = {
                        n.id for n in ast.walk(node)
                        if isinstance(n, ast.Name)
                    }
                    assert not (names & PROVIDER_CLASS_NAMES)

    def test_eligibility_declared_at_canonical_construction_site(self):
        path = REPO_ROOT / "product_intelligence" / "execution" / "orchestration.py"
        tree = _parse_function(path, "_try_fetch_fx_rates")
        found = False
        for node in ast.walk(tree):
            if (
                isinstance(node, ast.Assign)
                and len(node.targets) == 1
                and isinstance(node.targets[0], ast.Name)
                and node.targets[0].id == "fx_cache_eligible"
                and isinstance(node.value, ast.Compare)
                and isinstance(node.value.left, ast.Name)
                and node.value.left.id == "fx_provider"
                and len(node.value.ops) == 1
                and isinstance(node.value.ops[0], ast.Is)
                and isinstance(node.value.comparators[0], ast.Constant)
                and node.value.comparators[0].value is None
            ):
                found = True
        assert found, (
            "cache eligibility must be declared as "
            "`fx_cache_eligible = fx_provider is None` at the "
            "canonical-default construction site"
        )

    def test_no_provider_class_identity_in_fx_acquisition_step(self):
        path = REPO_ROOT / "product_intelligence" / "execution" / "orchestration.py"
        tree = _parse_function(path, "_try_fetch_fx_rates")
        for node in ast.walk(tree):
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
                if node.func.id in ("isinstance", "issubclass"):
                    names = {
                        n.id for n in ast.walk(node)
                        if isinstance(n, ast.Name)
                    }
                    assert not (names & PROVIDER_CLASS_NAMES), (
                        "provider class identity is not cache eligibility "
                        f"semantics; found in {node.func.id}(): {names}"
                    )

    def test_fx_step_catches_only_bounded_provider_error(self):
        path = REPO_ROOT / "product_intelligence" / "execution" / "orchestration.py"
        tree = _parse_function(path, "_try_fetch_fx_rates")
        for node in ast.walk(tree):
            if isinstance(node, ast.ExceptHandler):
                if node.type is None:
                    raise AssertionError("bare except in the FX step")
                if isinstance(node.type, ast.Name):
                    assert node.type.id == "FxProviderError", (
                        f"the FX step catches {node.type.id}; only the "
                        "bounded FxProviderError may be caught there"
                    )
                elif isinstance(node.type, ast.Tuple):
                    for elt in node.type.elts:
                        assert isinstance(elt, ast.Name)
                        assert elt.id == "FxProviderError"


class TestNoNewDependencyInversion:
    """The new modules respect the frozen dependency direction."""

    def test_cache_service_imports_only_approved_layers(self):
        import sys

        import product_intelligence.execution.fx_observation_cache as m

        path = Path(m.__file__)
        tree = ast.parse(path.read_text(encoding="utf-8"))
        modules = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom) and node.module and not node.level:
                modules.add(node.module)
            elif isinstance(node, ast.Import):
                modules.update(a.name for a in node.names)
        allowed_prefixes = (
            "product_intelligence.providers",
            "product_intelligence.research",
            "product_intelligence.runs",
            "product_intelligence.execution",
        )
        for module in sorted(modules):
            if module.startswith("product_intelligence"):
                assert module.startswith(allowed_prefixes), (
                    f"cache service imports {module} (dependency inversion)"
                )
            else:
                assert (
                    module in sys.stdlib_module_names
                    or module == "django"
                    or module.startswith("django.")
                ), f"cache service imports third-party {module}"

    def test_cache_service_never_imported_by_web_or_research_or_runs(self):
        for rel in (
            "product_intelligence/web",
            "product_intelligence/research",
            "product_intelligence/runs",
        ):
            root = REPO_ROOT / rel
            for path in root.rglob("*.py"):
                tree = ast.parse(path.read_text(encoding="utf-8"))
                for node in ast.walk(tree):
                    if isinstance(node, ast.ImportFrom) and node.module:
                        assert node.module != \
                            "product_intelligence.execution.fx_observation_cache", (
                            f"{path} imports the execution cache service"
                        )
                        if node.module == "product_intelligence.execution":
                            names = {a.name for a in node.names}
                            assert "fx_observation_cache" not in names, (
                                f"{path} imports the execution cache service"
                            )
                    elif isinstance(node, ast.Import):
                        for alias in node.names:
                            assert alias.name != \
                                "product_intelligence.execution.fx_observation_cache", (
                                f"{path} imports the execution cache service"
                            )
