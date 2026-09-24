"""Integration proof: production section-oriented Vendor response (PROD-FIX1).

For the exact requested MPN ``MTFDKBA480TFR-1BC1ZABYYR`` with a synthetic
production-equivalent section-oriented envelope (fake/redacted sensitive
values only), this proves through the REAL execution pipeline
(``execute_research_run``) that:

* Ingram creates exactly one usable observation (exact MPN, customer price
  1515.72 USD, availability/quantity faithfully mapped);
* CDW creates a NOT_FOUND issue;
* Synnex EU creates exactly one usable observation (exact MPN, 962.86 EUR,
  availability/quantity faithfully mapped);
* sensitive upstream metadata is absent from the ENCODED supplemental
  payload (the persisted artifact);
* the Compact Quote replay produces the corresponding Vendor rows and no
  CDW row;
* Vendor remains supplemental only: it does NOT modify Machine Price,
  does NOT enter semantic input, does NOT create 4A buckets, and does NOT
  suppress the Serper search call.
"""

from __future__ import annotations

import json
import os
from datetime import date, datetime, timezone
from decimal import Decimal
from unittest.mock import MagicMock, patch

from django.test import TestCase

from product_intelligence.domain import ResearchRequest
from product_intelligence.domain.enums import ResearchRunState
from product_intelligence.providers.fx import (
    FxObservationSet,
    FxRateObservation,
)
from product_intelligence.research.commercial_supplement_codec import (
    decode_research_supplement_result,
)
from product_intelligence.research.price_result_codec import (
    decode_price_aggregation_result,
)
from product_intelligence.runs.models import (
    AiAssistedReviewCandidate,
    PriceIntelligenceSnapshot,
    ResearchFxSnapshot,
    ResearchRun,
    ResearchSupplementSnapshot,
)
from product_intelligence.execution import replay_compact_quote_projection

REQUESTED_MPN = "MTFDKBA480TFR-1BC1ZABYYR"

USD_RATE = Decimal("1.0934")

# Synthetic production-equivalent section-oriented envelope. The real
# Synnex payload contains SessionId / BuyerAccountId / SystemId; this
# fixture uses FAKE sentinel values only.
SECTION_BODY = (
    f"Ingram Product: {{'vendorPartNumber': '{REQUESTED_MPN}', "
    "'customerPrice': 1515.72, 'currency': 'USD', 'quantity': 0}\n"
    "CDW Product: {Not Found}\n"
    "Synnex EU Product: {'SessionId': 'FAKE-SESSION-000', "
    "'BuyerAccountId': 'FAKE-ACCOUNT-000', 'SystemId': 'FAKE-SYSTEM-000', "
    f"'ManufacturerItemIdentifier': '{REQUESTED_MPN}', "
    "'UnitPriceAmount': 962.86, 'currency': 'EUR', 'AvailabilityTotal': 0}\n"
)

SENTINELS = (
    "FAKE-SESSION-000",
    "FAKE-ACCOUNT-000",
    "FAKE-SYSTEM-000",
    "SessionId",
    "BuyerAccountId",
    "SystemId",
)


class _FakeFxProvider:
    """Deterministic ECB-shaped FX provider (USD rate fixed)."""

    def __init__(self) -> None:
        self.call_count = 0

    def fetch_rates(self, requested_currencies=None) -> FxObservationSet:
        self.call_count += 1
        return FxObservationSet(
            provider_id="ECB",
            observation_date=date(2026, 9, 23),
            base_currency="EUR",
            rates=(
                FxRateObservation(currency_code="USD", rate=USD_RATE),
                FxRateObservation(currency_code="EUR", rate=Decimal("1")),
            ),
            retrieved_at=datetime(2026, 9, 23, 12, 0, 0, tzinfo=timezone.utc),
        )


class TestVendorSectionIntegration(TestCase):
    """The exact-MPN production section response through real execution."""

    def _execute(self) -> ResearchRun:
        request = ResearchRequest(
            manufacturer_part_number=REQUESTED_MPN,
            description="Micron 480TB datacenter SSD",
        )
        run = ResearchRun.objects.create_from_request(request)

        mock_response = MagicMock()
        mock_response.read.return_value = SECTION_BODY.encode("utf-8")
        mock_opener = MagicMock()
        mock_opener.open.return_value = mock_response

        fx_provider = _FakeFxProvider()

        with patch.dict(
            os.environ,
            {"PI_VENDOR_LOOKUP_BASE_URL": "http://157.22.244.39:8808/vendor"},
        ):
            mock_search = MagicMock()
            mock_search.search.return_value = MagicMock(results=())
            with patch(
                "product_intelligence.providers.serper."
                "SerperSearchProvider.from_environment",
                return_value=mock_search,
            ), patch(
                "product_intelligence.providers.internal_vendor."
                "_get_vendor_opener",
                return_value=mock_opener,
            ):
                from product_intelligence.execution import execute_research_run
                execute_research_run(
                    str(run.id),
                    fx_provider=fx_provider,
                )

        # store for assertions
        self._mock_opener = mock_opener
        self._mock_search = mock_search
        self._fx_provider = fx_provider
        return run

    def test_supplement_snapshot_exact_mpn_observations(self) -> None:
        run = self._execute()

        # Exactly ONE vendor network call; zero retries
        assert self._mock_opener.open.call_count == 1

        run.refresh_from_db()
        assert run.current_state == ResearchRunState.COMPLETED

        supplement = ResearchSupplementSnapshot.objects.get(run=run)
        decoded = decode_research_supplement_result(supplement.payload)
        vcr = decoded.vendor_commercial_result

        assert vcr.lookup_status == "PARTIAL"
        assert vcr.retrieved_at is not None  # was None in the broken production result

        observations = {o.source_name: o for o in vcr.observations}
        assert set(observations) == {"Ingram", "Synnex EU"}

        # Ingram: one usable observation, exact MPN, customer price, faithful
        # availability/quantity mapping
        ingram = observations["Ingram"]
        assert ingram.explicit_candidate_mpn == REQUESTED_MPN
        assert ingram.vendor_mpn_match_type == "EXACT"
        assert ingram.price_amount == Decimal("1515.72")
        assert ingram.currency_code == "USD"
        assert ingram.price_basis == "CUSTOMER_PRICE"
        assert ingram.availability == "OUT_OF_STOCK"
        assert ingram.quantity == 0
        assert ingram.brand_new is True
        assert ingram.brand_new_basis == "VENDOR_API_POLICY"

        # Synnex EU: one usable observation, exact MPN, faithful mapping
        synnex = observations["Synnex EU"]
        assert synnex.explicit_candidate_mpn == REQUESTED_MPN
        assert synnex.vendor_mpn_match_type == "EXACT"
        assert synnex.price_amount == Decimal("962.86")
        assert synnex.currency_code == "EUR"
        assert synnex.price_basis == "LIST_PRICE"
        assert synnex.availability == "OUT_OF_STOCK"
        assert synnex.quantity == 0

        # CDW: NOT_FOUND issue (no row)
        issues = {i.source_name: i for i in vcr.source_issues}
        assert set(issues) == {"CDW"}
        assert issues["CDW"].outcome == "NOT_FOUND"
        assert issues["CDW"].detail is None

    def test_sensitive_metadata_absent_from_encoded_payload(self) -> None:
        run = self._execute()
        supplement = ResearchSupplementSnapshot.objects.get(run=run)
        encoded = json.dumps(supplement.payload, sort_keys=True)
        for sentinel in SENTINELS:
            assert sentinel not in encoded, (
                f"sensitive metadata {sentinel!r} leaked into the persisted "
                "supplemental payload"
            )

    def test_compact_quote_replay_vendor_rows(self) -> None:
        run = self._execute()
        replay = replay_compact_quote_projection(str(run.id))
        rows = list(replay.projection.rows)

        vendor_rows = [r for r in rows if r.source_type == "VENDOR_API"]
        public_rows = [r for r in rows if r.source_type == "PUBLIC_LISTING"]
        # No search results -> no public rows; exactly two vendor rows
        assert public_rows == []
        assert [r.source for r in vendor_rows] == [
            "Ingram",
            "Synnex EU (Vendor API)",
        ]
        # CDW NOT_FOUND creates no row
        assert not any(r.source.startswith("CDW") for r in rows)

        ingram = vendor_rows[0]
        assert ingram.price_original == "$1,515.72 USD"
        assert ingram.usd_equivalent == "$1,515.72 USD"
        assert ingram.inventory == "Out of Stock"
        assert ingram.brand_new == "Yes"

        synnex = vendor_rows[1]
        assert synnex.price_original == "\u20ac962.86 EUR"
        expected_usd = Decimal("962.86") / Decimal("1") * USD_RATE
        assert synnex.usd_equivalent_amount == expected_usd
        assert synnex.inventory == "Out of Stock"
        assert synnex.brand_new == "Yes"

    def test_machine_price_not_modified_by_vendor(self) -> None:
        run = self._execute()
        price_snapshot = PriceIntelligenceSnapshot.objects.get(run=run)
        decoded = decode_price_aggregation_result(
            price_snapshot.payload,
            schema_version=price_snapshot.schema_version,
        )
        # Zero vendor-derived buckets: no search evidence was published
        assert decoded.buckets == ()
        encoded = json.dumps(price_snapshot.payload, sort_keys=True)
        # Vendor prices never enter the Machine Price artifact
        assert "1515.72" not in encoded
        assert "962.86" not in encoded
        assert "Ingram" not in encoded
        assert "Synnex" not in encoded

    def test_fx_snapshot_persisted_for_vendor_eur(self) -> None:
        run = self._execute()
        assert self._fx_provider.call_count == 1
        assert ResearchFxSnapshot.objects.filter(run=run).exists()

    def test_vendor_does_not_suppress_search(self) -> None:
        run = self._execute()
        # The paid Serper fallback search still happened exactly once
        assert self._mock_search.search.call_count == 1

    def test_vendor_does_not_enter_semantic_input(self) -> None:
        run = self._execute()
        # No semantic-eligible listings exist (no search results), so no
        # review candidates were created; vendor data is not semantic input.
        candidates = AiAssistedReviewCandidate.objects.filter(run=run)
        for candidate in candidates:
            assert "Ingram" not in candidate.candidate_title
            assert "CDW" not in candidate.candidate_title
            assert "Synnex" not in candidate.candidate_title
