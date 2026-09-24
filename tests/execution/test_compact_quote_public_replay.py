"""Tests for the public-only compact quote replay (PRODUCT-INTEL.4D-C, FU2).

The DENIED branch of the compact quote summary browser rendering uses a
bounded execution/read-side service:
``replay_public_compact_quote_projection``.

FU2 authority ownership: the replay loads and decodes the run's OWN
persisted ``PriceIntelligenceSnapshot`` itself; no caller-supplied price
aggregation result is an authority source (the ``price_result`` parameter
was removed). These tests prove:
* PUBLIC_LISTING rows only — vendor rows can never appear, even when a
  real ResearchSupplementSnapshot exists for the run
* the supplemental artifact access path is NEVER touched (armed with
  RuntimeError fail-fast sentinels)
* ZERO live provider/network/semantic work (armed fail-fast sentinels)
* persisted FX evidence drives the USD Equivalent display
* fail-closed: malformed FX artifact propagates (no partial summary)
* fail-closed: request-provenance-corrupt persisted snapshot is refused
* fail-closed: missing / malformed persisted price artifact propagates
* no API surface accepts a caller-supplied (duck-typed or canonical)
  price result as authority
* programming errors (wrong types) propagate, never swallowed
"""

from __future__ import annotations

import ast
import inspect
from datetime import date, datetime, timezone
from decimal import Decimal
from pathlib import Path
from unittest.mock import patch

import pytest

from product_intelligence.domain import ResearchRequest
from product_intelligence.domain.enums import (
    ConfidenceLevel,
    EvidenceDecision,
    IdentityMatchType,
    VerificationStatus,
)
from product_intelligence.execution.compact_quote_public_replay import (
    PublicCompactQuoteReplayResult,
    replay_public_compact_quote_projection,
)
from product_intelligence.providers.fx import (
    EcbFxProvider,
    FxRateObservation,
)
from product_intelligence.research import encode_price_aggregation_result
from product_intelligence.research.aggregation import (
    PriceAggregateBucket,
    PriceAggregationResult,
)
from product_intelligence.research.compact_quote import (
    CompactQuoteProjection,
    CompactQuoteProjectionError,
)
from product_intelligence.research.commercial_supplement_codec import (
    ResearchSupplementResult,
    SupplementAvailability,
    SupplementLookupStatus,
    SupplementPriceBasis,
    SupplementSourceObservation,
    VendorCommercialResult,
    decode_research_supplement_result,
    encode_research_supplement_result,
)
from product_intelligence.research.fx_codec import (
    FxCodecError,
    encode_fx_observation,
)
from product_intelligence.research.listings import (
    ExtractionMethod,
    ListingObservation,
)
from product_intelligence.research.matching import (
    EvidenceSource,
    ListingIdentityAssessment,
)
from product_intelligence.research.normalization import (
    NormalizedAvailability,
    NormalizedCondition,
    NormalizedListingObservation,
)
from product_intelligence.runs.models import (
    PriceIntelligenceSnapshot,
    ResearchFxSnapshot,
    ResearchRun,
    ResearchSupplementSnapshot,
)


# ---------------------------------------------------------------------------
# Fixtures / builders
# ---------------------------------------------------------------------------

MPN = "PUB-REPLAY-MPN"


def _make_public_result(
    run: ResearchRun,
    *,
    source_url: str = "https://www.example.com/product/abc",
    price_text: str = "1705.35",
    currency_text: str = "EUR",
    price_amount: Decimal = Decimal("1705.35"),
    currency_code: str = "EUR",
) -> PriceAggregationResult:
    """Build a VERIFIED PriceAggregationResult bound to the run with one
    public EUR bucket-member assessment."""
    obs = ListingObservation(
        source_url=source_url,
        extraction_method=ExtractionMethod.JSON_LD,
        product_title="Public Listing Product",
        manufacturer_part_number_text=run.manufacturer_part_number or MPN,
        sku_text=None,
        brand_text=None,
        price_text=price_text,
        currency_text=currency_text,
        availability_text="In Stock",
        condition_text="New",
        seller_text="Example Store",
        offer_url_text=None,
        raw_reference=None,
    )
    norm = NormalizedListingObservation(
        observation=obs,
        price_amount=price_amount,
        currency_code=currency_code,
        availability=NormalizedAvailability.IN_STOCK,
        condition=NormalizedCondition.NEW,
        seller_name="Example Store",
        normalization_issues=(),
    )
    assess = ListingIdentityAssessment(
        normalized_listing=norm,
        requested_part_number=run.manufacturer_part_number or MPN,
        candidate_part_number_raw=run.manufacturer_part_number or MPN,
        candidate_part_number_compared=run.manufacturer_part_number or MPN,
        candidate_evidence_source=EvidenceSource.EXPLICIT_MPN_FIELD,
        match_type=IdentityMatchType.EXACT,
        decision=EvidenceDecision.ACCEPTED,
        rejection_reason=None,
    )
    return PriceAggregationResult(
        request=run.to_research_request(),
        assessments=(assess,),
        exclusions=(),
        buckets=(
            PriceAggregateBucket(
                currency_code=currency_code,
                condition=NormalizedCondition.NEW,
                assessments=(assess,),
                count=1,
                low=price_amount,
                median=price_amount,
                high=price_amount,
                market_range_low=None,
                market_range_high=None,
                confidence=ConfidenceLevel.LOW,
            ),
        ),
        verification_status=VerificationStatus.VERIFIED,
    )


def _persist_price(run: ResearchRun, result: PriceAggregationResult) -> None:
    """Persist the canonical price snapshot the replay must load itself.

    FU2: the replay owns its authority source; tests establish the
    persisted artifact exactly as execution would, then call the replay
    with the run alone.
    """
    PriceIntelligenceSnapshot.objects.create(
        run=run,
        schema_version=1,
        payload=encode_price_aggregation_result(result),
    )


def _persist_fx(run: ResearchRun) -> None:
    """Persist a real V1 FX snapshot (EUR base, USD rate)."""
    rates = (
        FxRateObservation(currency_code="USD", rate=Decimal("1.0934")),
        FxRateObservation(currency_code="EUR", rate=Decimal("1.0")),
    )
    payload = encode_fx_observation(
        provider_id="ECB",
        observation_date=date(2024, 1, 15),
        base_currency="EUR",
        rates=rates,
        retrieved_at=datetime(2024, 1, 15, 12, 0, 0, tzinfo=timezone.utc),
    )
    ResearchFxSnapshot.objects.create(
        run=run, schema_version=1, payload=payload
    )


def _persist_supplement(run: ResearchRun) -> None:
    """Persist a REAL ResearchSupplementSnapshot with a recognizable
    sentinel vendor price (91827.43 USD, Ingram)."""
    result = ResearchSupplementResult(
        vendor_commercial_result=VendorCommercialResult(
            lookup_status=SupplementLookupStatus.SUCCESS,
            retrieved_at=datetime(2025, 1, 15, 12, 0, 0, tzinfo=timezone.utc),
            observations=(
                SupplementSourceObservation(
                    source_name="Ingram",
                    explicit_candidate_mpn=run.manufacturer_part_number or MPN,
                    vendor_mpn_match_type="EXACT",
                    price_amount=Decimal("91827.43"),
                    currency_code="USD",
                    availability=SupplementAvailability.IN_STOCK,
                    price_basis=SupplementPriceBasis.CUSTOMER_PRICE,
                    quantity=1,
                    note_kind=None,
                    brand_new=True,
                    brand_new_basis="VENDOR_API_POLICY",
                ),
            ),
            source_issues=(),
        ),
    )
    ResearchSupplementSnapshot.objects.create(
        run=run,
        schema_version=1,
        payload=encode_research_supplement_result(result),
    )


def _create_run() -> ResearchRun:
    return ResearchRun.objects.create_from_request(
        ResearchRequest(manufacturer_part_number=MPN, description="Public replay")
    )


# ---------------------------------------------------------------------------
# Happy path: public rows only, persisted FX
# ---------------------------------------------------------------------------


class TestPublicOnlyReplay:
    def test_public_rows_with_persisted_fx(self) -> None:
        run = _create_run()
        result = _make_public_result(run)
        _persist_price(run, result)
        _persist_fx(run)
        # A real supplement exists in the DB — the public replay must
        # ignore it entirely.
        _persist_supplement(run)

        replay = replay_public_compact_quote_projection(run=run)

        assert isinstance(replay, PublicCompactQuoteReplayResult)
        assert isinstance(replay.projection, CompactQuoteProjection)
        assert replay.run is run
        assert replay.fx_snapshot is not None
        assert replay.fx_snapshot.provider_id == "ECB"

        rows = replay.projection.rows
        assert len(rows) == 1
        assert rows[0].source_type == "PUBLIC_LISTING"
        # Original EUR price preserved
        assert rows[0].price_amount == Decimal("1705.35")
        assert rows[0].price_currency == "EUR"
        # USD equivalent from persisted FX: 1705.35 * 1.0934
        assert rows[0].usd_equivalent_amount == Decimal("1705.35") * Decimal("1.0934")

    def test_zero_vendor_rows_even_with_real_supplement(self) -> None:
        run = _create_run()
        result = _make_public_result(run)
        _persist_price(run, result)
        _persist_fx(run)
        _persist_supplement(run)

        replay = replay_public_compact_quote_projection(run=run)

        for row in replay.projection.rows:
            assert row.source_type == "PUBLIC_LISTING"
        assert all("91827.43" not in row.price_original for row in replay.projection.rows)

    def test_no_fx_evidence_still_projects_public_rows(self) -> None:
        run = _create_run()
        result = _make_public_result(run)
        _persist_price(run, result)

        replay = replay_public_compact_quote_projection(run=run)

        assert replay.fx_snapshot is None
        rows = replay.projection.rows
        assert len(rows) == 1
        # Non-USD row without FX evidence: USD equivalent unavailable
        assert rows[0].usd_equivalent == "Unavailable"
        assert rows[0].usd_equivalent_amount is None
        # Original price still valid
        assert rows[0].price_amount == Decimal("1705.35")
        assert rows[0].price_currency == "EUR"

    def test_usd_row_without_fx_evidence_passes_through(self) -> None:
        run = _create_run()
        result = _make_public_result(
            run,
            source_url="https://usd.example.com/product",
            price_text="$109.99",
            currency_text="USD",
            price_amount=Decimal("109.99"),
            currency_code="USD",
        )
        _persist_price(run, result)

        replay = replay_public_compact_quote_projection(run=run)

        row = replay.projection.rows[0]
        assert row.usd_equivalent_amount == Decimal("109.99")
        assert row.price_amount == Decimal("109.99")

    def test_empty_bucket_result_projects_zero_rows(self) -> None:
        run = _create_run()
        result = PriceAggregationResult(
            request=run.to_research_request(),
            assessments=(),
            buckets=(),
            exclusions=(),
            verification_status=VerificationStatus.UNKNOWN,
        )
        _persist_price(run, result)

        replay = replay_public_compact_quote_projection(run=run)

        assert replay.projection.rows == ()


# ---------------------------------------------------------------------------
# Supplemental artifact access is never touched (armed fail-fast)
# ---------------------------------------------------------------------------


class TestPublicOnlyReplayNeverTouchesSupplement:
    def test_supplement_lookup_arms_and_still_succeeds(self) -> None:
        """Arming the exact supplemental lookup/decode path used by the
        authorized replay must not affect the public-only replay: if the
        public path read ResearchSupplementSnapshot or called
        decode_research_supplement_result, RuntimeError would propagate."""
        run = _create_run()
        result = _make_public_result(run)
        _persist_price(run, result)
        _persist_fx(run)
        _persist_supplement(run)

        def _boom(*args, **kwargs):
            raise RuntimeError(
                "ResearchSupplementSnapshot was accessed on the public-only path"
            )

        with (
            patch.object(ResearchSupplementSnapshot.objects, "get", side_effect=_boom),
            patch.object(
                ResearchSupplementSnapshot.objects, "filter", side_effect=_boom
            ),
            patch(
                "product_intelligence.research.commercial_supplement_codec"
                ".decode_research_supplement_result",
                side_effect=_boom,
            ),
        ):
            replay = replay_public_compact_quote_projection(run=run)

        assert len(replay.projection.rows) == 1
        assert replay.projection.rows[0].source_type == "PUBLIC_LISTING"

    def test_related_supplement_access_arms_and_still_succeeds(self) -> None:
        """Even the run-related descriptor path is armed."""
        run = _create_run()
        result = _make_public_result(run)
        _persist_price(run, result)
        _persist_supplement(run)

        class _BoomDescriptor:
            def __get__(self, instance, owner):
                raise RuntimeError(
                    "supplement related descriptor was touched on the public path"
                )

        with patch.object(
            type(run), "research_supplement_snapshot", new=_BoomDescriptor()
        ):
            replay = replay_public_compact_quote_projection(run=run)

        assert len(replay.projection.rows) == 1


# ---------------------------------------------------------------------------
# Zero live provider / network / semantic work (armed fail-fast)
# ---------------------------------------------------------------------------


class TestPublicOnlyReplayZeroLiveWork:
    def test_live_boundaries_armed_and_replay_succeeds(self) -> None:
        run = _create_run()
        result = _make_public_result(run)
        _persist_price(run, result)
        _persist_fx(run)
        _persist_supplement(run)

        from product_intelligence.execution import semantic_integration
        from product_intelligence.providers.http_page import HttpPageFetcher
        from product_intelligence.providers.internal_vendor import (
            InternalVendorAdapter,
        )
        from product_intelligence.providers.serper import SerperSearchProvider
        from product_intelligence.semantic.runtime import SemanticRuntime
        import urllib.request

        def _live_boom(*args, **kwargs):
            raise RuntimeError("live provider/network boundary touched")

        with (
            patch.object(SerperSearchProvider, "search", side_effect=_live_boom),
            patch.object(HttpPageFetcher, "fetch", side_effect=_live_boom),
            patch.object(
                InternalVendorAdapter, "lookup", side_effect=_live_boom
            ),
            patch.object(EcbFxProvider, "__init__", side_effect=_live_boom),
            patch.object(EcbFxProvider, "fetch_rates", side_effect=_live_boom),
            patch.object(SemanticRuntime, "evaluate", side_effect=_live_boom),
            patch.object(
                semantic_integration,
                "evaluate_semantic_matches",
                side_effect=_live_boom,
            ),
            patch("urllib.request.urlopen", side_effect=_live_boom),
            patch(
                "urllib.request.OpenerDirector.open", side_effect=_live_boom
            ),
        ):
            replay = replay_public_compact_quote_projection(run=run)

        assert len(replay.projection.rows) == 1
        assert replay.fx_snapshot is not None


# ---------------------------------------------------------------------------
# Fail-closed behavior
# ---------------------------------------------------------------------------


class TestPublicOnlyReplayFailClosed:
    def test_malformed_fx_payload_propagates(self) -> None:
        run = _create_run()
        result = _make_public_result(run)
        _persist_price(run, result)
        ResearchFxSnapshot.objects.create(
            run=run, schema_version=1, payload={"garbage": True}
        )

        with pytest.raises(FxCodecError):
            replay_public_compact_quote_projection(run=run)

    def test_unsupported_fx_schema_version_propagates(self) -> None:
        run = _create_run()
        result = _make_public_result(run)
        _persist_price(run, result)
        valid = encode_fx_observation(
            provider_id="ECB",
            observation_date=date(2024, 1, 15),
            base_currency="EUR",
            rates=(FxRateObservation(currency_code="USD", rate=Decimal("1.0934")),),
            retrieved_at=datetime(2024, 1, 15, 12, 0, 0, tzinfo=timezone.utc),
        )
        valid["schema_version"] = 99
        ResearchFxSnapshot.objects.create(
            run=run, schema_version=1, payload=valid
        )

        with pytest.raises(FxCodecError):
            replay_public_compact_quote_projection(run=run)

    def test_provenance_mismatch_is_refused(self) -> None:
        """FU2: the authority source is the PERSISTED snapshot, so a
        request-provenance corruption is proven by persisting a snapshot
        whose decoded result is bound to a DIFFERENT run's request.
        The replay must fail closed (no summary, no borrowed evidence).
        The same safety contract as before holds: a foreign-request
        price result is never projected for this run."""
        run = _create_run()
        other_run = ResearchRun.objects.create_from_request(
            ResearchRequest(manufacturer_part_number="OTHER-MPN", description="x")
        )
        # A valid result — but bound to a DIFFERENT run's request —
        # persisted as THIS run's snapshot (request-provenance corrupt).
        foreign_result = _make_public_result(other_run)
        _persist_price(run, foreign_result)

        with pytest.raises(CompactQuoteProjectionError, match="provenance"):
            replay_public_compact_quote_projection(run=run)

    def test_missing_price_snapshot_fails_closed(self) -> None:
        """FU2: no persisted price artifact => fail closed with the
        existing persisted-artifact behavior (DoesNotExist propagates,
        exactly as the authorized replay's documented behavior; the web
        view maps it to 'summary unavailable')."""
        run = _create_run()
        assert not PriceIntelligenceSnapshot.objects.filter(run=run).exists()

        with pytest.raises(PriceIntelligenceSnapshot.DoesNotExist):
            replay_public_compact_quote_projection(run=run)

    def test_malformed_price_snapshot_payload_fails_closed(self) -> None:
        """FU2: a corrupt persisted price payload fails closed through
        the canonical codec (no partial summary)."""
        run = _create_run()
        PriceIntelligenceSnapshot.objects.create(
            run=run, schema_version=1, payload={"garbage": True}
        )

        from product_intelligence.research.price_result_codec import (
            PriceResultCodecError,
        )

        with pytest.raises(PriceResultCodecError):
            replay_public_compact_quote_projection(run=run)

    def test_duck_typed_price_result_is_refused(self) -> None:
        """FU2: there is NO API surface accepting a caller-supplied price
        result (duck-typed or canonical) as the authority source.
        Mechanical proof: the parameter is gone — supplying one raises
        TypeError — and the projection derives solely from the persisted
        snapshot even when a foreign in-memory object exists."""
        run = _create_run()

        params = inspect.signature(
            replay_public_compact_quote_projection
        ).parameters
        assert "price_result" not in params

        class FakeResult:
            request = run.to_research_request()
            buckets = ()

        with pytest.raises(TypeError):
            replay_public_compact_quote_projection(
                run=run, price_result=FakeResult()  # type: ignore[call-arg]
            )

        # Behavior: the persisted snapshot is the only authority source.
        persisted = _make_public_result(run)
        _persist_price(run, persisted)
        _ = FakeResult()
        replay = replay_public_compact_quote_projection(run=run)
        assert len(replay.projection.rows) == 1
        assert replay.projection.rows[0].price_amount == Decimal("1705.35")

    def test_wrong_run_type_is_programming_error(self) -> None:
        with pytest.raises(TypeError):
            replay_public_compact_quote_projection(
                run="not-a-run",  # type: ignore[arg-type]
            )

    def test_frozen_projection_failure_propagates(self) -> None:
        """If the frozen project_public_rows raises
        CompactQuoteProjectionError (authority defect), it propagates —
        no partial public summary."""
        run = _create_run()
        result = _make_public_result(run)
        _persist_price(run, result)

        with patch(
            "product_intelligence.execution.compact_quote_public_replay"
            ".project_public_rows",
            side_effect=CompactQuoteProjectionError("injected authority defect"),
        ):
            with pytest.raises(CompactQuoteProjectionError, match="injected"):
                replay_public_compact_quote_projection(run=run)

    def test_runtime_error_in_fx_decode_propagates(self) -> None:
        """A programming RuntimeError inside the FX decode path propagates
        and is never swallowed."""
        run = _create_run()
        result = _make_public_result(run)
        _persist_price(run, result)
        _persist_fx(run)

        with patch(
            "product_intelligence.execution.compact_quote_public_replay"
            ".decode_fx_observation",
            side_effect=RuntimeError("injected programming defect"),
        ):
            with pytest.raises(RuntimeError, match="injected programming defect"):
                replay_public_compact_quote_projection(run=run)


# ---------------------------------------------------------------------------
# Module boundary guards (source-level)
# ---------------------------------------------------------------------------


def _module_source() -> str:
    path = (
        Path(__file__).resolve().parents[2]
        / "product_intelligence"
        / "execution"
        / "compact_quote_public_replay.py"
    )
    return path.read_text(encoding="utf-8")


class TestPublicOnlyReplayModuleBoundaries:
    def test_module_never_references_live_provider_paths(self) -> None:
        source = _module_source()
        for forbidden in (
            "InternalVendorAdapter",
            "providers.commercial",
            "providers.internal_vendor",
            "SerperSearchProvider",
            "providers.serper",
            "providers.search",
            "HttpPageFetcher",
            "http_page",
            "SemanticRuntime",
            "semantic_integration",
            "EcbFxProvider",
            "providers.fx",
        ):
            assert forbidden not in source, (
                f"public-only replay module references live provider path "
                f"{forbidden!r}"
            )

    def test_module_imports_no_provider_or_supplement_symbol(self) -> None:
        """Mechanical AST proof: the module imports no provider submodule,
        no semantic module, no supplement codec symbol, and never names the
        ResearchSupplementSnapshot model in code."""
        tree = ast.parse(_module_source())
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom) and node.module:
                assert not node.module.startswith("product_intelligence.providers"), (
                    f"imports provider submodule {node.module!r}"
                )
                assert not node.module.startswith("product_intelligence.semantic"), (
                    f"imports semantic module {node.module!r}"
                )
                assert not node.module.endswith("commercial_supplement_codec"), (
                    "imports the commercial supplement codec"
                )
                if node.module == "product_intelligence.runs.models":
                    imported = {alias.name for alias in node.names}
                    assert imported <= {
                        "ResearchRun",
                        "ResearchFxSnapshot",
                        # FU2: the persisted price authority source.
                        "PriceIntelligenceSnapshot",
                    }, (
                        f"imports unapproved runs.models symbols {sorted(imported)}"
                    )
            if isinstance(node, ast.Import):
                for alias in node.names:
                    assert not alias.name.startswith("product_intelligence.providers")
                    assert not alias.name.startswith("product_intelligence.semantic")
            if isinstance(node, ast.Name):
                assert node.id != "ResearchSupplementSnapshot", (
                    "module references the ResearchSupplementSnapshot model"
                )
                assert node.id != "decode_research_supplement_result", (
                    "module references decode_research_supplement_result"
                )

    def test_public_api_exported_from_execution_package(self) -> None:
        from product_intelligence.execution import (  # noqa: F401
            replay_public_compact_quote_projection as exported,
        )

        assert exported is replay_public_compact_quote_projection
