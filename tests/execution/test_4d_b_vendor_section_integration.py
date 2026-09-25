"""Integration proof: production section-oriented Vendor response (PROD-FIX1;
FU1 faithful production-wire shape; FU3 observed paragraph envelope).

For the exact requested MPN ``MTFDKBA480TFR-1BC1ZABYYR`` with a synthetic
envelope that mirrors the ACTUAL production nesting/key placement (fake/
redacted sensitive values only), this proves through the REAL execution
pipeline (``execute_research_run``) that:

* Ingram (hybrid production form: explicit vendorPartNumber + nested
  pricing customerPrice/retailPrice/currencyCode + top-level boolean
  availability false + top-level Avl_Quantity 0 + unrelated non-
  authoritative fields) creates exactly one usable observation (exact MPN,
  customer price 1515.72 USD, OUT_OF_STOCK, quantity 0);
* CDW creates a NOT_FOUND issue;
* Synnex EU (REAL nested form: OnlineCheck.Header.CurrencyCode with
  fake/redacted SessionId / BuyerAccountId / SystemId at their realistic
  structural locations + OnlineCheck.Item.ManufacturerItemIdentifier /
  UnitPriceAmount / AvailabilityTotal) creates exactly one usable
  observation (exact MPN, 962.86 EUR, OUT_OF_STOCK, quantity 0);
* sensitive upstream metadata is absent from the ENCODED supplemental
  payload (the persisted artifact);
* the Compact Quote replay produces the corresponding Vendor rows and no
  CDW row;
* Vendor remains supplemental only: it does NOT modify Machine Price,
  does NOT enter semantic input, does NOT create 4A buckets, and does NOT
  suppress the Serper search call.

FU3: the same proofs are re-established for the OBSERVED production outer
envelope — each section line wrapped in the exact HTML paragraph opener
(``<p>Ingram Product: ...</p>`` / ``<p>CDW Product: ...</p>`` /
``<p>Synnex EU Product: ...</p>``) — including the execution-time 4D-C FX
currency discovery (usable Synnex EUR observation => EUR + USD requested
from the FX provider) and the persisted USD Equivalent on the Synnex
Compact Quote row.

FU4: the same proofs are re-established for the CURRENT observed
production representation — the exact ``<p>`` wrapper PLUS the observed
paragraph-envelope entity encoding (every literal double quote
``&quot;``-encoded; ``&nbsp;`` / ``&cr;`` carrying LF / CR in a non-
authoritative synthetic Ingram field), the nested Synnex
``UnitPriceAmount`` as the production-observed numeric string, and the
nested Synnex ``AvailabilityTotal`` as the production-observed digit
string ``"0"``. The live production price is mutable upstream commercial
data; the fixture values are explicitly synthetic and deterministic.
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
from product_intelligence.research.fx_codec import (
    FxObservationSnapshot,
    decode_fx_observation,
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

# Synthetic envelope mirroring the ACTUAL production nesting/key placement
# (FU1). The real Synnex payload carries SessionId / BuyerAccountId /
# SystemId in the OnlineCheck.Header block; this fixture uses FAKE sentinel
# values at their realistic structural locations. The real Synnex payload is
# the REAL nested OnlineCheck form; the flat forms are separately tested
# compatibility forms, not the production wire shape.
SECTION_BODY = (
    f"Ingram Product: {{'vendorPartNumber': '{REQUESTED_MPN}', "
    "'pricing': {'customerPrice': 1515.72, 'retailPrice': 2036.36, "
    "'currencyCode': 'USD'}, 'availability': False, 'Avl_Quantity': 0, "
    "'vendorName': 'FAKE-VENDOR-NAME', 'warehouse': 'FAKE-WH-00'}\n"
    "CDW Product: {Not Found}\n"
    "Synnex EU Product: {'OnlineCheck': {'Header': {'CurrencyCode': 'EUR', "
    "'SessionId': 'FAKE-SESSION-000', 'BuyerAccountId': 'FAKE-ACCOUNT-000', "
    "'SystemId': 'FAKE-SYSTEM-000'}, 'Item': {'ManufacturerItemIdentifier': "
    f"'{REQUESTED_MPN}', 'UnitPriceAmount': 962.86, 'AvailabilityTotal': 0}}}}}}\n"
)

SENTINELS = (
    "FAKE-SESSION-000",
    "FAKE-ACCOUNT-000",
    "FAKE-SYSTEM-000",
    "SessionId",
    "BuyerAccountId",
    "SystemId",
)

# ---------------------------------------------------------------------------
# FU4: the CURRENT observed production representation — the exact <p>
# paragraph wrapper PLUS the observed paragraph-envelope entity encoding
# (every literal double quote &quot;-encoded; the observed &nbsp; / &cr;
# literals carrying LF / CR in a non-authoritative synthetic Ingram
# field), the nested Synnex UnitPriceAmount as the production-observed
# numeric string, and the nested Synnex AvailabilityTotal as the
# production-observed digit string "0". Same synthetic source payload /
# fake sentinels as SECTION_BODY_PARAGRAPH. The live production price is
# mutable upstream commercial data; the values here are explicitly
# synthetic and deterministic.
# ---------------------------------------------------------------------------
SECTION_BODY_PARAGRAPH_ENTITY = (
    "<p>Ingram Product: {&quot;vendorPartNumber&quot;: &quot;"
    + REQUESTED_MPN
    + "&quot;, &quot;pricing&quot;: {&quot;customerPrice&quot;: 1515.72, "
    "&quot;retailPrice&quot;: 2036.36, &quot;currencyCode&quot;: &quot;USD&quot;}, "
    "&quot;availability&quot;: False, &quot;Avl_Quantity&quot;: 0, "
    "&quot;vendorName&quot;: &quot;FAKE-VENDOR-NAME&nbsp;lf&nbsp;&cr;cr&quot;}</p>\n"
    "\n"
    "<p>CDW Product: {Not Found}</p>\n"
    "\n"
    "<p>Synnex EU Product: {&quot;OnlineCheck&quot;: {&quot;Header&quot;: "
    "{&quot;CurrencyCode&quot;: &quot;EUR&quot;, &quot;SessionId&quot;: "
    "&quot;FAKE-SESSION-000&quot;, &quot;BuyerAccountId&quot;: "
    "&quot;FAKE-ACCOUNT-000&quot;, &quot;SystemId&quot;: "
    "&quot;FAKE-SYSTEM-000&quot;}, &quot;Item&quot;: "
    "{&quot;ManufacturerItemIdentifier&quot;: &quot;"
    + REQUESTED_MPN
    + "&quot;, &quot;UnitPriceAmount&quot;: &quot;962.86&quot;, "
    "&quot;AvailabilityTotal&quot;: &quot;0&quot;}}}}</p>\n"
)

# ---------------------------------------------------------------------------
# FU3: the OBSERVED production outer envelope — each section line wrapped
# in the exact HTML paragraph opener ("<p>..."), single-line sections
# mirroring the observed production layout. Same synthetic source payload
# (hybrid Ingram + nested Synnex with fake sentinels + CDW Not Found) as
# the plain-text fixture above; ONLY the outer line envelope differs.
# ---------------------------------------------------------------------------
SECTION_BODY_PARAGRAPH = (
    f"<p>Ingram Product: {{'vendorPartNumber': '{REQUESTED_MPN}', "
    "'pricing': {'customerPrice': 1515.72, 'retailPrice': 2036.36, "
    "'currencyCode': 'USD'}, 'availability': False, 'Avl_Quantity': 0, "
    "'vendorName': 'FAKE-VENDOR-NAME'}</p>\n"
    "\n"
    "<p>CDW Product: {Not Found}</p>\n"
    "\n"
    "<p>Synnex EU Product: {'OnlineCheck': {'Header': {'CurrencyCode': 'EUR', "
    "'SessionId': 'FAKE-SESSION-000', 'BuyerAccountId': 'FAKE-ACCOUNT-000', "
    "'SystemId': 'FAKE-SYSTEM-000'}, 'Item': {'ManufacturerItemIdentifier': "
    f"'{REQUESTED_MPN}', 'UnitPriceAmount': 962.86, 'AvailabilityTotal': 0}}}}}}</p>\n"
)


class _RecordingFxProvider:
    """Deterministic ECB-shaped FX provider that records every requested
    currency set — proves the EXISTING 4D-C execution-time currency
    discovery (usable Synnex EUR observation => EUR + USD requested)
    without altering any FX production code."""

    def __init__(self) -> None:
        self.call_count = 0
        self.requested_currencies_calls: list[frozenset[str]] = []

    def fetch_rates(self, requested_currencies=None) -> FxObservationSet:
        self.call_count += 1
        self.requested_currencies_calls.append(
            frozenset(requested_currencies or ())
        )
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

        # Ingram: one usable observation, exact MPN, customer price
        # authoritative (retailPrice 2036.36 present but not used),
        # OUT_OF_STOCK / 0 from the top-level availability boolean +
        # top-level Avl_Quantity (hybrid production placement)
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

        # Synnex EU: one usable observation, exact MPN, REAL nested form
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


class TestVendorParagraphSectionIntegration(TestCase):
    """FU3: the OBSERVED production outer envelope (exact "<p>" paragraph
    wrapper on each section line) through the REAL execution pipeline.

    Same proofs as the plain-text class above, plus the execution-time 4D-C
    FX currency discovery and the persisted USD Equivalent — the existing
    FX production code is unchanged; only the injected deterministic
    provider differs.
    """

    def _execute(self, fx_provider) -> ResearchRun:
        request = ResearchRequest(
            manufacturer_part_number=REQUESTED_MPN,
            description="Micron 480TB datacenter SSD",
        )
        run = ResearchRun.objects.create_from_request(request)

        mock_response = MagicMock()
        mock_response.read.return_value = SECTION_BODY_PARAGRAPH.encode("utf-8")
        mock_opener = MagicMock()
        mock_opener.open.return_value = mock_response

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

        self._mock_opener = mock_opener
        self._mock_search = mock_search
        self._fx_provider = fx_provider
        return run

    def test_paragraph_execute_persists_ingram_and_synnex_observations(
        self,
    ) -> None:
        """Proof level 3: the paragraph-wrapped real structural fixture
        travels through the actual Vendor adapter and persists."""
        run = self._execute(_FakeFxProvider())

        # Exactly ONE vendor network call; zero retries
        assert self._mock_opener.open.call_count == 1

        run.refresh_from_db()
        assert run.current_state == ResearchRunState.COMPLETED

        supplement = ResearchSupplementSnapshot.objects.get(run=run)
        decoded = decode_research_supplement_result(supplement.payload)
        vcr = decoded.vendor_commercial_result

        # Contract recognized: bounded PARTIAL (Ingram + Synnex usable,
        # CDW NOT_FOUND) with retrieved_at present (it was None in the
        # broken production result).
        assert vcr.lookup_status == "PARTIAL"
        assert vcr.retrieved_at is not None

        observations = {o.source_name: o for o in vcr.observations}
        assert set(observations) == {"Ingram", "Synnex EU"}

        # Ingram: hybrid production form through the paragraph envelope
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

        # Synnex EU: REAL nested form through the paragraph envelope
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

    def test_paragraph_sensitive_metadata_absent_from_persisted_snapshot(
        self,
    ) -> None:
        run = self._execute(_FakeFxProvider())
        supplement = ResearchSupplementSnapshot.objects.get(run=run)
        encoded = json.dumps(supplement.payload, sort_keys=True)
        for sentinel in SENTINELS + ("FAKE-VENDOR-NAME", "vendorName"):
            assert sentinel not in encoded, (
                f"sensitive metadata {sentinel!r} leaked into the persisted "
                "supplemental payload"
            )

    def test_paragraph_machine_price_unchanged(self) -> None:
        run = self._execute(_FakeFxProvider())
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

    def test_paragraph_compact_quote_replay_vendor_rows_zero_live(self) -> None:
        """Proof level 4: historical Compact Quote replay of the
        paragraph-envelope run — Ingram Vendor row + Synnex Vendor row,
        no CDW row, armed zero-live boundaries."""
        run = self._execute(_FakeFxProvider())

        with (
            patch(
                "product_intelligence.providers.serper."
                "SerperSearchProvider.search",
                side_effect=RuntimeError(
                    "SearchProvider.search called during replay"
                ),
            ),
            patch(
                "product_intelligence.providers.http_page."
                "HttpPageFetcher.fetch",
                side_effect=RuntimeError("PageFetcher.fetch during replay"),
            ),
            patch(
                "product_intelligence.providers.internal_vendor."
                "InternalVendorAdapter.lookup",
                side_effect=RuntimeError("Vendor API during replay"),
            ),
            patch(
                "product_intelligence.providers.fx."
                "EcbFxProvider.fetch_rates",
                side_effect=RuntimeError("EcbFxProvider.fetch_rates during replay"),
            ),
            patch(
                "product_intelligence.providers.fx."
                "EcbFxProvider.__init__",
                side_effect=RuntimeError("EcbFxProvider instantiated during replay"),
            ),
            patch(
                "product_intelligence.execution.semantic_integration."
                "evaluate_semantic_matches",
                side_effect=RuntimeError("Semantic runtime during replay"),
            ),
            patch(
                "urllib.request.urlopen",
                side_effect=RuntimeError("Network call during replay"),
            ),
        ):
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
        # USD Equivalent from the PERSISTED FX snapshot (zero live)
        expected_usd = Decimal("962.86") / Decimal("1") * USD_RATE
        assert synnex.usd_equivalent_amount == expected_usd
        assert synnex.inventory == "Out of Stock"
        assert synnex.brand_new == "Yes"

    def test_paragraph_synnex_eur_triggers_execution_time_fx_discovery(
        self,
    ) -> None:
        """Proof level 5: because the usable Synnex Vendor observation is
        EUR, the EXISTING 4D-C execution-time currency discovery requests
        EUR + USD from the FX provider, and the injected deterministic
        provider's success persists a ResearchFxSnapshot (no FX
        production code altered by FU3)."""
        fx_provider = _RecordingFxProvider()
        run = self._execute(fx_provider)

        # Exactly one FX fetch, requesting exactly {EUR, USD}
        assert fx_provider.call_count == 1
        assert fx_provider.requested_currencies_calls == [
            frozenset({"EUR", "USD"}),
        ]

        # Persisted ResearchFxSnapshot (schema V1) with both rates
        fx_snapshot = ResearchFxSnapshot.objects.get(run=run)
        assert fx_snapshot.schema_version == 1
        decoded_fx: FxObservationSnapshot = decode_fx_observation(
            fx_snapshot.payload
        )
        assert decoded_fx.provider_id == "ECB"
        assert {r.currency_code for r in decoded_fx.rates} == {"EUR", "USD"}

    def test_paragraph_vendor_remains_supplemental_only(self) -> None:
        run = self._execute(_FakeFxProvider())
        # The paid Serper fallback search still happened exactly once —
        # vendor evidence never suppresses search.
        assert self._mock_search.search.call_count == 1
        # Vendor data is not semantic input (no review candidates carry
        # vendor source names).
        for candidate in AiAssistedReviewCandidate.objects.filter(run=run):
            for token in ("Ingram", "CDW", "Synnex"):
                assert token not in candidate.candidate_title


class TestVendorParagraphEntitySectionIntegration(TestCase):
    """FU4: the CURRENT observed production representation — the exact
    <p> paragraph wrapper PLUS the observed paragraph-envelope entity
    encoding (&quot; / &nbsp; / &cr;), the nested Synnex UnitPriceAmount
    as a numeric string, and the nested Synnex AvailabilityTotal as the
    digit string "0" — through the REAL execution pipeline.

    Same authority / supplemental-only / zero-live proofs as the FU3
    paragraph class, re-established against the production-shaped
    encoded wire. The live production price is mutable upstream
    commercial data; the fixture values are explicitly synthetic and
    deterministic.
    """

    def _execute(self, fx_provider) -> ResearchRun:
        request = ResearchRequest(
            manufacturer_part_number=REQUESTED_MPN,
            description="Micron 480TB datacenter SSD",
        )
        run = ResearchRun.objects.create_from_request(request)

        mock_response = MagicMock()
        mock_response.read.return_value = (
            SECTION_BODY_PARAGRAPH_ENTITY.encode("utf-8")
        )
        mock_opener = MagicMock()
        mock_opener.open.return_value = mock_response

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

        self._mock_opener = mock_opener
        self._mock_search = mock_search
        self._fx_provider = fx_provider
        return run

    def test_entity_execute_persists_ingram_and_synnex_observations(
        self,
    ) -> None:
        """The encoded paragraph fixture travels through the real Vendor
        adapter and REAL ``execute_research_run``: one Vendor network
        call, COMPLETED run, bounded PARTIAL supplement with both
        observations and the CDW NOT_FOUND issue."""
        run = self._execute(_FakeFxProvider())

        # Exactly ONE vendor network call; zero retries
        assert self._mock_opener.open.call_count == 1

        run.refresh_from_db()
        assert run.current_state == ResearchRunState.COMPLETED

        supplement = ResearchSupplementSnapshot.objects.get(run=run)
        decoded = decode_research_supplement_result(supplement.payload)
        vcr = decoded.vendor_commercial_result

        assert vcr.lookup_status == "PARTIAL"
        assert vcr.retrieved_at is not None

        observations = {o.source_name: o for o in vcr.observations}
        assert set(observations) == {"Ingram", "Synnex EU"}

        # Ingram: entity-encoded wire through the bounded decoding +
        # unchanged mappers (exact MPN, 1515.72 USD CUSTOMER_PRICE,
        # OUT_OF_STOCK, quantity 0).
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

        # Synnex EU: nested wire with the production-observed numeric
        # string price and digit string "0" availability maps to
        # OUT_OF_STOCK / quantity 0.
        synnex = observations["Synnex EU"]
        assert synnex.explicit_candidate_mpn == REQUESTED_MPN
        assert synnex.vendor_mpn_match_type == "EXACT"
        assert synnex.price_amount == Decimal("962.86")
        assert synnex.currency_code == "EUR"
        assert synnex.price_basis == "LIST_PRICE"
        assert synnex.availability == "OUT_OF_STOCK"
        assert synnex.quantity == 0

        # CDW: NOT_FOUND issue (no candidate row)
        issues = {i.source_name: i for i in vcr.source_issues}
        assert set(issues) == {"CDW"}
        assert issues["CDW"].outcome == "NOT_FOUND"
        assert issues["CDW"].detail is None

    def test_entity_sensitive_metadata_absent_from_persisted_snapshot(
        self,
    ) -> None:
        run = self._execute(_FakeFxProvider())
        supplement = ResearchSupplementSnapshot.objects.get(run=run)
        encoded = json.dumps(supplement.payload, sort_keys=True)
        for sentinel in SENTINELS + ("FAKE-VENDOR-NAME", "vendorName"):
            assert sentinel not in encoded, (
                f"sensitive metadata {sentinel!r} leaked into the persisted "
                "supplemental payload"
            )
        # The observed entity spellings never survive into the artifact
        for entity in ("&quot;", "&nbsp;", "&cr;"):
            assert entity not in encoded, (
                f"raw entity spelling {entity!r} leaked into the persisted "
                "supplemental payload"
            )

    def test_entity_machine_price_unchanged(self) -> None:
        # Deterministic fixture with zero public-search evidence: the
        # authority proof is unambiguous — Machine Price has zero buckets
        # and NO vendor commercial value enters the artifact.
        run = self._execute(_FakeFxProvider())
        price_snapshot = PriceIntelligenceSnapshot.objects.get(run=run)
        decoded = decode_price_aggregation_result(
            price_snapshot.payload,
            schema_version=price_snapshot.schema_version,
        )
        assert decoded.buckets == ()
        encoded = json.dumps(price_snapshot.payload, sort_keys=True)
        assert "1515.72" not in encoded
        assert "962.86" not in encoded
        assert "Ingram" not in encoded
        assert "Synnex" not in encoded

    def test_entity_compact_quote_replay_vendor_rows_zero_live(self) -> None:
        """Historical Compact Quote replay from the persisted snapshots —
        Ingram Vendor row + Synnex Vendor row present, CDW row absent,
        Synnex USD Equivalent from the persisted ResearchFxSnapshot, and
        ZERO live Search / Page / Vendor / ECB / semantic / urllib work
        (armed fail-fast patches exactly as the existing FU3 zero-live
        test)."""
        run = self._execute(_FakeFxProvider())

        with (
            patch(
                "product_intelligence.providers.serper."
                "SerperSearchProvider.search",
                side_effect=RuntimeError(
                    "SearchProvider.search called during replay"
                ),
            ),
            patch(
                "product_intelligence.providers.http_page."
                "HttpPageFetcher.fetch",
                side_effect=RuntimeError("PageFetcher.fetch during replay"),
            ),
            patch(
                "product_intelligence.providers.internal_vendor."
                "InternalVendorAdapter.lookup",
                side_effect=RuntimeError("Vendor API during replay"),
            ),
            patch(
                "product_intelligence.providers.fx."
                "EcbFxProvider.fetch_rates",
                side_effect=RuntimeError(
                    "EcbFxProvider.fetch_rates during replay"
                ),
            ),
            patch(
                "product_intelligence.providers.fx."
                "EcbFxProvider.__init__",
                side_effect=RuntimeError(
                    "EcbFxProvider instantiated during replay"
                ),
            ),
            patch(
                "product_intelligence.execution.semantic_integration."
                "evaluate_semantic_matches",
                side_effect=RuntimeError("Semantic runtime during replay"),
            ),
            patch(
                "urllib.request.urlopen",
                side_effect=RuntimeError("Network call during replay"),
            ),
        ):
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
        # USD Equivalent from the PERSISTED FX snapshot (zero live)
        expected_usd = Decimal("962.86") / Decimal("1") * USD_RATE
        assert synnex.usd_equivalent_amount == expected_usd
        assert synnex.inventory == "Out of Stock"
        assert synnex.brand_new == "Yes"

    def test_entity_synnex_eur_triggers_execution_time_fx_discovery(
        self,
    ) -> None:
        """Because a usable Synnex EUR observation now exists during
        execution, the EXISTING 4D-C execution-time currency discovery
        requests EUR + USD from the FX provider; the deterministic
        injected provider succeeds and a ResearchFxSnapshot persists
        EUR + USD (no FX production code modification)."""
        fx_provider = _RecordingFxProvider()
        run = self._execute(fx_provider)

        # Exactly one FX fetch, requesting exactly {EUR, USD}
        assert fx_provider.call_count == 1
        assert fx_provider.requested_currencies_calls == [
            frozenset({"EUR", "USD"}),
        ]

        # Persisted ResearchFxSnapshot (schema V1) with both rates
        fx_snapshot = ResearchFxSnapshot.objects.get(run=run)
        assert fx_snapshot.schema_version == 1
        decoded_fx: FxObservationSnapshot = decode_fx_observation(
            fx_snapshot.payload
        )
        assert decoded_fx.provider_id == "ECB"
        assert {r.currency_code for r in decoded_fx.rates} == {"EUR", "USD"}

    def test_entity_vendor_remains_supplemental_only(self) -> None:
        # Vendor must still: not suppress paid search, not become
        # semantic input, not gain public-search authority (no public
        # rows are minted from vendor evidence), not gain human-confirmed
        # authority (no review candidate carries a vendor source name).
        run = self._execute(_FakeFxProvider())
        assert self._mock_search.search.call_count == 1
        for candidate in AiAssistedReviewCandidate.objects.filter(run=run):
            for token in ("Ingram", "CDW", "Synnex"):
                assert token not in candidate.candidate_title
        replay = replay_compact_quote_projection(str(run.id))
        public_rows = [
            r for r in replay.projection.rows
            if r.source_type == "PUBLIC_LISTING"
        ]
        assert public_rows == []
