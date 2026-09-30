"""FX freshness display tests (PRODUCT-INTEL.8A-FX-A1).

The report gains ONE additive, bounded FX evidence line (observation
date + original provider retrieval instant + LIVE/CACHE_HIT
acquisition label) so FX freshness is auditable. These tests prove:

* the line renders on both replay branches (ALLOWED / DENIED);
* LIVE and CACHE_HIT label correctly;
* USD-only runs (no FX snapshot) render no FX line;
* no internal detail leaks (store IDs, digests, cache keys, schema
  versions, exception text);
* the GET path performs ZERO live work and ZERO cross-run cache
  acquisition;
* replaying never mutates the persisted acquisition provenance.
"""

from __future__ import annotations

from contextlib import contextmanager
from datetime import date, datetime, timezone
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import patch

import pytest
from django.test import Client
from django.urls import reverse

from product_intelligence.domain import ResearchRequest
from product_intelligence.domain.enums import (
    ConfidenceLevel,
    EvidenceDecision,
    IdentityMatchType,
    VerificationStatus,
)
from product_intelligence.research.aggregation import PriceAggregationResult
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
from product_intelligence.research.price_result_codec import (
    encode_price_aggregation_result,
)
from product_intelligence.research.fx_codec import encode_fx_observation
from product_intelligence.providers.fx import (
    EcbFxProvider,
    FxRateObservation,
)
from product_intelligence.runs.models import (
    FxObservationStore,
    PriceIntelligenceSnapshot,
    ResearchFxSnapshot,
    ResearchRun,
)
from product_intelligence.execution import fx_observation_cache

UTC = timezone.utc

ALLOWED_CIDRS = "10.0.0.0/8"
ALLOWED_ADDR = "10.0.0.1"

FX_OBSERVATION_DATE = date(2026, 1, 9)
FX_RETRIEVED_AT = datetime(2026, 1, 9, 16, 0, 0, tzinfo=UTC)


@pytest.fixture(autouse=True)
def _clean_rows():
    yield
    FxObservationStore.objects.all().delete()
    ResearchFxSnapshot.objects.all().delete()
    PriceIntelligenceSnapshot.objects.all().delete()
    ResearchRun.objects.all().delete()


def _mock_settings(cidrs: str | None = ALLOWED_CIDRS):
    return SimpleNamespace(PI_VENDOR_PRICE_ALLOWED_CIDRS=cidrs)


def _result_for_currency(run: ResearchRun, currency: str) -> PriceAggregationResult:
    mpn = run.manufacturer_part_number or "FX-MPN"
    price = Decimal("1700.00")
    obs = ListingObservation(
        source_url="https://example.com/product",
        extraction_method=ExtractionMethod.JSON_LD,
        product_title="FX Evidence Test Product",
        manufacturer_part_number_text=mpn,
        sku_text=None,
        brand_text=None,
        price_text=str(price),
        currency_text=currency,
        availability_text="In Stock",
        condition_text="New",
        seller_text="Example Store",
        offer_url_text=None,
        raw_reference=None,
    )
    norm = NormalizedListingObservation(
        observation=obs,
        price_amount=price,
        currency_code=currency,
        availability=NormalizedAvailability.IN_STOCK,
        condition=NormalizedCondition.NEW,
        seller_name="Example Store",
        normalization_issues=(),
    )
    assess = ListingIdentityAssessment(
        normalized_listing=norm,
        requested_part_number=mpn,
        candidate_part_number_raw=mpn,
        candidate_part_number_compared=mpn,
        candidate_evidence_source=EvidenceSource.EXPLICIT_MPN_FIELD,
        match_type=IdentityMatchType.EXACT,
        decision=EvidenceDecision.ACCEPTED,
        rejection_reason=None,
    )
    from product_intelligence.research.aggregation import PriceAggregateBucket

    return PriceAggregationResult(
        request=run.to_research_request(),
        assessments=(assess,),
        exclusions=(),
        buckets=(
            PriceAggregateBucket(
                currency_code=currency,
                condition=NormalizedCondition.NEW,
                assessments=(assess,),
                count=1,
                low=price,
                median=price,
                high=price,
                market_range_low=None,
                market_range_high=None,
                confidence=ConfidenceLevel.LOW,
            ),
        ),
        verification_status=VerificationStatus.VERIFIED,
    )


def _eur_result(run: ResearchRun) -> PriceAggregationResult:
    return _result_for_currency(run, "EUR")


def _usd_result(run: ResearchRun) -> PriceAggregationResult:
    return _result_for_currency(run, "USD")


def _fx_payload() -> dict:
    return encode_fx_observation(
        provider_id="ECB",
        observation_date=FX_OBSERVATION_DATE,
        base_currency="EUR",
        rates=(
            FxRateObservation(currency_code="USD", rate=Decimal("1.0934")),
            FxRateObservation(currency_code="EUR", rate=Decimal("1.0")),
        ),
        retrieved_at=FX_RETRIEVED_AT,
    )


def _create_run(
    *,
    with_fx: bool = True,
    acquisition: str = ResearchFxSnapshot.ACQUISITION_LIVE,
    usd_only: bool = False,
) -> ResearchRun:
    run = ResearchRun.objects.create_from_request(
        ResearchRequest(manufacturer_part_number="FX-MPN",
                        description="FX freshness display")
    )
    result = _usd_result(run) if usd_only else _eur_result(run)
    PriceIntelligenceSnapshot.objects.create(
        run=run, schema_version=1, payload=encode_price_aggregation_result(result)
    )
    if with_fx:
        ResearchFxSnapshot.objects.create(
            run=run, schema_version=1, payload=_fx_payload(),
            acquisition=acquisition,
        )
    return run


def _detail_url(run: ResearchRun) -> str:
    return reverse("research-detail", kwargs={"run_id": run.id})


@contextmanager
def _armed_zero_live_boundaries():
    """Arm the live ECB network boundary AND the cross-run cache
    service: any touch raises."""

    def _boom(*args, **kwargs):
        raise RuntimeError("zero-live boundary touched on GET")

    with (
        patch("urllib.request.urlopen", side_effect=_boom),
        patch.object(
            fx_observation_cache, "try_reuse_latest_observation",
            side_effect=_boom,
        ),
        patch.object(
            fx_observation_cache, "record_live_observation",
            side_effect=_boom,
        ),
        patch.object(EcbFxProvider, "fetch_rates", side_effect=_boom),
    ):
        yield


class TestFxEvidenceLine:
    def test_live_label_renders_denied_branch(self):
        run = _create_run(acquisition=ResearchFxSnapshot.ACQUISITION_LIVE)
        response = Client().get(_detail_url(run), REMOTE_ADDR="127.0.0.1")
        assert response.status_code == 200
        html = response.content.decode()
        assert "ECB reference date" in html
        assert FX_OBSERVATION_DATE.isoformat() in html
        assert "Rates retrieved" in html
        assert "2026-01-09 16:00 UTC" in html
        assert "Retrieved live during this research run" in html
        assert "Reused from the canonical ECB observation cache" not in html

    def test_cache_hit_label_renders_denied_branch(self):
        run = _create_run(acquisition=ResearchFxSnapshot.ACQUISITION_CACHE_HIT)
        response = Client().get(_detail_url(run), REMOTE_ADDR="127.0.0.1")
        assert response.status_code == 200
        html = response.content.decode()
        assert "ECB reference date" in html
        assert FX_OBSERVATION_DATE.isoformat() in html
        assert "Reused from the canonical ECB observation cache" in html
        assert "Retrieved live during this research run" not in html

    def test_cache_hit_label_renders_allowed_branch(self):
        run = _create_run(acquisition=ResearchFxSnapshot.ACQUISITION_CACHE_HIT)
        with patch(
            "product_intelligence.web.commercial_access._django_settings",
            _mock_settings(),
        ), _armed_zero_live_boundaries():
            response = Client().get(_detail_url(run), REMOTE_ADDR=ALLOWED_ADDR)
        assert response.status_code == 200
        html = response.content.decode()
        assert "Reused from the canonical ECB observation cache" in html
        assert "Retrieved live during this research run" not in html

    def test_usd_only_run_renders_no_fx_line(self):
        run = _create_run(with_fx=False, usd_only=True)
        response = Client().get(_detail_url(run), REMOTE_ADDR="127.0.0.1")
        assert response.status_code == 200
        html = response.content.decode()
        assert "ECB reference date" not in html
        assert "Reused from the canonical ECB observation cache" not in html
        assert "Retrieved live during this research run" not in html

    def test_no_internal_details_exposed(self):
        # A store row exists (as it would after a real cached run);
        # none of its internals may appear in the rendered report.
        from product_intelligence.research.fx_cache_contract import (
            fx_document_content_sha256,
        )

        digest = fx_document_content_sha256(
            provider_id="ECB", base_currency="EUR",
            observation_date=FX_OBSERVATION_DATE,
            rates=[("USD", Decimal("1.0934")), ("EUR", Decimal("1.0"))],
        )
        row = FxObservationStore.objects.create(
            feed_id="ecb:eurofxref-daily",
            provider_id="ECB",
            base_currency="EUR",
            observation_date=FX_OBSERVATION_DATE,
            content_sha256=digest,
            payload=_fx_payload(),
            original_retrieved_at=FX_RETRIEVED_AT,
            last_proven_at=FX_RETRIEVED_AT,
            created_at=FX_RETRIEVED_AT,
        )
        run = _create_run(acquisition=ResearchFxSnapshot.ACQUISITION_CACHE_HIT)
        response = Client().get(_detail_url(run), REMOTE_ADDR="127.0.0.1")
        assert response.status_code == 200
        html = response.content.decode()
        assert digest not in html
        assert str(row.id) not in html
        assert "content_sha256" not in html
        assert "schema_version" not in html
        assert "ecb:eurofxref-daily" not in html

    def test_get_performs_zero_live_and_zero_cache_work(self):
        run = _create_run(acquisition=ResearchFxSnapshot.ACQUISITION_CACHE_HIT)
        with _armed_zero_live_boundaries():
            response = Client().get(_detail_url(run), REMOTE_ADDR="127.0.0.1")
        assert response.status_code == 200
        # Provenance preserved by the read: replay never mutates it.
        row = ResearchFxSnapshot.objects.get(run=run)
        assert row.acquisition == ResearchFxSnapshot.ACQUISITION_CACHE_HIT
        assert row.payload == _fx_payload()

    def test_default_acquisition_is_live_for_historical_rows(self):
        # Backward compatibility: a row persisted before 8A-FX-A1
        # (no explicit acquisition) is LIVE and renders the live label.
        run = ResearchRun.objects.create_from_request(
            ResearchRequest(manufacturer_part_number="FX-MPN",
                            description="historical row")
        )
        result = _eur_result(run)
        PriceIntelligenceSnapshot.objects.create(
            run=run, schema_version=1,
            payload=encode_price_aggregation_result(result),
        )
        ResearchFxSnapshot.objects.create(
            run=run, schema_version=1, payload=_fx_payload(),
        )
        row = ResearchFxSnapshot.objects.get(run=run)
        assert row.acquisition == "LIVE"
        response = Client().get(_detail_url(run), REMOTE_ADDR="127.0.0.1")
        assert response.status_code == 200
        html = response.content.decode()
        assert "Retrieved live during this research run" in html
