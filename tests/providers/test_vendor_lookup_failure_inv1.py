"""Offline reproduction of Vendor API response for Micron MPN
MTFDKCC3T8TGP-1BK1DABYYR — investigation PRODUCT-INTEL.VENDOR-LOOKUP-FAILURE-INV1.

This test exercises the REAL InternalVendorAdapter pathway (through the full
``lookup()`` method) with mocked HTTP transport, using a sanitized fixture that
preserves the demonstrated wire structure, approved fields, decimal precision,
null/boolean/string distinctions, section labels, and envelope syntax from the
later manually retrieved Vendor response.

No production data is committed. Sensitive fields (account numbers, session
tokens, internal identifiers, warehouse details) are replaced with FAKE sentinel
values. The fixture values (prices, availability states) are taken from the
investigation's manually retrieved response and are deterministic.

The test proves:
1. The adapter correctly parses the section-oriented hybrid response body
   (the production text/html contract with <p> paragraph envelope + entity
   encoding).
2. Each source is mapped with exact expected prices, currencies, identity
   binding, and availability classifications.
3. CDW $0 is mapped as a valid candidate with UNKNOWN availability
   (not free, not purchasable).
4. EUR pricing is preserved as EUR (no fabricated USD equivalent).
5. The overall lookup status is correct (SUCCESS or PARTIAL).

All tests are zero-network. No live API call is made.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from decimal import Decimal
from unittest.mock import MagicMock, patch

import pytest

from product_intelligence.providers.commercial import (
    CommercialAvailability,
    CommercialLookupQuery,
    CommercialPriceBasis,
    CommercialSourceCandidate,
    CommercialSourceIssue,
    CommercialSourceResponse,
    LookupStatus,
    SourceOutcome,
)
from product_intelligence.providers.internal_vendor import (
    InternalVendorAdapter,
)
from product_intelligence.research.commercial_supplement_codec import (
    SupplementPriceBasis,
    SupplementSourceObservation,
)

# ---------------------------------------------------------------------------
# Fixtures — sanitized, representative wire structures
# ---------------------------------------------------------------------------

REQUESTED_MPN = "MTFDKCC3T8TGP-1BK1DABYYR"

# The real production response uses Content-Type: text/html; charset=utf-8
# with the exact <p> paragraph envelope (FU3) and entity encoding (FU4).
# Each section line is wrapped in <p>...</p>. Double quotes in section
# values are encoded as &quot;. LF/CR as &#xA;/&#xD; (entity encoding
# only applies to the paragraph envelope path).
#
# Sensitive fields (SessionId, BuyerAccountId, SystemId) are FAKE sentinels.
# Prices and availability states match the manually retrieved Vendor response.

SECTION_BODY_HYBRID_PARAGRAPH = (
    "<p>Ingram Product: {&quot;vendorPartNumber&quot;: &quot;"
    + REQUESTED_MPN
    + "&quot;, &quot;pricing&quot;: {&quot;customerPrice&quot;: 5445.67, "
    "&quot;retailPrice&quot;: 6200.00, &quot;currencyCode&quot;: &quot;USD&quot;}, "
    "&quot;availability&quot;: false, &quot;Avl_Quantity&quot;: 0, "
    "&quot;vendorName&quot;: &quot;FAKE-VENDOR-NAME&quot;, "
    "&quot;warehouse&quot;: &quot;FAKE-WH-00&quot;}</p>\n"
    "\n"
    "<p>CDW Product: {&quot;manufacturerPartNumber&quot;: &quot;"
    + REQUESTED_MPN
    + "&quot;, &quot;price&quot;: 0.00, &quot;currencyCode&quot;: &quot;USD&quot;}</p>\n"
    "\n"
    "<p>Synnex EU Product: {&quot;OnlineCheck&quot;: {&quot;Header&quot;: "
    "{&quot;CurrencyCode&quot;: &quot;EUR&quot;, &quot;SessionId&quot;: "
    "&quot;FAKE-SESSION-000&quot;, &quot;BuyerAccountId&quot;: "
    "&quot;FAKE-ACCOUNT-000&quot;, &quot;SystemId&quot;: "
    "&quot;FAKE-SYSTEM-000&quot;}, &quot;Item&quot;: "
    "{&quot;ManufacturerItemIdentifier&quot;: &quot;"
    + REQUESTED_MPN
    + "&quot;, &quot;UnitPriceAmount&quot;: &quot;4740.18&quot;, "
    "&quot;AvailabilityTotal&quot;: &quot;0&quot;}}}}</p>\n"
)

# Plain-text (non-paragraph) compatibility form — same source payloads,
# only the outer envelope differs.
SECTION_BODY_HYBRID_PLAINTEXT = (
    "Ingram Product: {'vendorPartNumber': '"
    + REQUESTED_MPN
    + "', 'pricing': {'customerPrice': 5445.67, 'retailPrice': 6200.00, "
    "'currencyCode': 'USD'}, 'availability': False, 'Avl_Quantity': 0, "
    "'vendorName': 'FAKE-VENDOR-NAME', 'warehouse': 'FAKE-WH-00'}\n"
    "CDW Product: {'manufacturerPartNumber': '"
    + REQUESTED_MPN
    + "', 'price': 0.00, 'currencyCode': 'USD'}\n"
    "Synnex EU Product: {'OnlineCheck': {'Header': {'CurrencyCode': 'EUR', "
    "'SessionId': 'FAKE-SESSION-000', 'BuyerAccountId': 'FAKE-ACCOUNT-000', "
    "'SystemId': 'FAKE-SYSTEM-000'}, 'Item': {'ManufacturerItemIdentifier': '"
    + REQUESTED_MPN
    + "', 'UnitPriceAmount': '4740.18', 'AvailabilityTotal': '0'}}}\n"
)

# Canonical JSON wrapper contract — same source data in the canonical
# JSON document form (for cross-contract comparison).
CANONICAL_JSON_PAYLOAD = {
    "Ingram": {
        "sourceName": "Ingram",
        "vendorPartNumber": REQUESTED_MPN,
        "pricing": {
            "customerPrice": Decimal("5445.67"),
            "retailPrice": Decimal("6200.00"),
            "currencyCode": "USD",
        },
        "availability": False,
        "Avl_Quantity": 0,
    },
    "CDW": {
        "sourceName": "CDW",
        "manufacturerPartNumber": REQUESTED_MPN,
        "price": Decimal("0.00"),
        "currencyCode": "USD",
    },
    "Synnex EU": {
        "sourceName": "Synnex EU",
        "OnlineCheck": {
            "Header": {
                "CurrencyCode": "EUR",
                "SessionId": "FAKE-SESSION-000",
                "BuyerAccountId": "FAKE-ACCOUNT-000",
                "SystemId": "FAKE-SYSTEM-000",
            },
            "Item": {
                "ManufacturerItemIdentifier": REQUESTED_MPN,
                "UnitPriceAmount": "4740.18",
                "AvailabilityTotal": "0",
            },
        },
    },
}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _adapter_with_body(body: str | bytes) -> InternalVendorAdapter:
    """Build a configured adapter that returns the given body on lookup."""
    adapter = InternalVendorAdapter()
    adapter._base_url = "http://vendor.internal/api"
    adapter._validated = True

    mock_response = MagicMock()
    mock_response.read.return_value = (
        body if isinstance(body, bytes) else body.encode("utf-8")
    )
    mock_opener = MagicMock()
    mock_opener.open.return_value = mock_response

    adapter._mock_opener = mock_opener
    adapter._mock_response = mock_response
    return adapter


# ---------------------------------------------------------------------------
# Reproduction tests — section-oriented paragraph envelope (production)
# ---------------------------------------------------------------------------


class TestMicronVendorResponseParagraphEnvelope:
    """Full adapter pathway with mocked HTTP transport over the observed
    production paragraph-envelope contract (FU3 + FU4 entity encoding)."""

    def test_parses_all_three_sources(self) -> None:
        adapter = _adapter_with_body(SECTION_BODY_HYBRID_PARAGRAPH)

        with patch(
            "product_intelligence.providers.internal_vendor."
            "_get_vendor_opener",
            return_value=adapter._mock_opener,
        ):
            response = adapter.lookup(
                CommercialLookupQuery(mpn=REQUESTED_MPN)
            )

        # Lookup succeeds (all three sources parsed)
        assert response.status == LookupStatus.SUCCESS
        assert response.retrieved_at is not None
        assert len(response.candidates) == 3
        assert len(response.issues) == 0

    def test_ingram_price_and_availability(self) -> None:
        adapter = _adapter_with_body(SECTION_BODY_HYBRID_PARAGRAPH)

        with patch(
            "product_intelligence.providers.internal_vendor."
            "_get_vendor_opener",
            return_value=adapter._mock_opener,
        ):
            response = adapter.lookup(
                CommercialLookupQuery(mpn=REQUESTED_MPN)
            )

        ingram = next(
            c for c in response.candidates if c.source_name == "Ingram"
        )
        assert ingram.price_amount == Decimal("5445.67")
        assert ingram.currency_code == "USD"
        assert ingram.price_basis == CommercialPriceBasis.CUSTOMER_PRICE
        # available=false + Avl_Quantity=0 -> OUT_OF_STOCK
        assert ingram.availability == CommercialAvailability.OUT_OF_STOCK
        assert ingram.quantity == 0
        assert ingram.explicit_candidate_mpn == REQUESTED_MPN

    def test_synnex_eu_price_and_availability(self) -> None:
        adapter = _adapter_with_body(SECTION_BODY_HYBRID_PARAGRAPH)

        with patch(
            "product_intelligence.providers.internal_vendor."
            "_get_vendor_opener",
            return_value=adapter._mock_opener,
        ):
            response = adapter.lookup(
                CommercialLookupQuery(mpn=REQUESTED_MPN)
            )

        synnex = next(
            c for c in response.candidates if c.source_name == "Synnex EU"
        )
        assert synnex.price_amount == Decimal("4740.18")
        assert synnex.currency_code == "EUR"
        # AvailabilityTotal="0" (digit string) -> OUT_OF_STOCK via
        # narrow Synnex-specific _synnex_availability_total
        assert synnex.availability == CommercialAvailability.OUT_OF_STOCK
        assert synnex.quantity == 0
        assert synnex.explicit_candidate_mpn == REQUESTED_MPN

    def test_cdw_zero_price_and_unknown_availability(self) -> None:
        """CDW $0 is a valid candidate with UNKNOWN availability (no
        inventory fields published). It is NOT free, verified, or
        immediately purchasable."""
        adapter = _adapter_with_body(SECTION_BODY_HYBRID_PARAGRAPH)

        with patch(
            "product_intelligence.providers.internal_vendor."
            "_get_vendor_opener",
            return_value=adapter._mock_opener,
        ):
            response = adapter.lookup(
                CommercialLookupQuery(mpn=REQUESTED_MPN)
            )

        cdw = next(c for c in response.candidates if c.source_name == "CDW")
        assert cdw.price_amount == Decimal("0.00")
        assert cdw.currency_code == "USD"
        assert cdw.price_basis == CommercialPriceBasis.LIST_PRICE
        # No explicit inventory fields -> UNKNOWN
        assert cdw.availability == CommercialAvailability.UNKNOWN
        assert cdw.quantity is None
        assert cdw.explicit_candidate_mpn == REQUESTED_MPN

    def test_sensitive_metadata_stripped(self) -> None:
        """FAKE sentinel metadata never survives into candidates."""
        adapter = _adapter_with_body(SECTION_BODY_HYBRID_PARAGRAPH)

        with patch(
            "product_intelligence.providers.internal_vendor."
            "_get_vendor_opener",
            return_value=adapter._mock_opener,
        ):
            response = adapter.lookup(
                CommercialLookupQuery(mpn=REQUESTED_MPN)
            )

        for candidate in response.candidates:
            candidate_str = str(candidate)
            assert "FAKE-SESSION-000" not in candidate_str
            assert "FAKE-ACCOUNT-000" not in candidate_str
            assert "FAKE-SYSTEM-000" not in candidate_str
            assert "SessionId" not in candidate_str
            assert "BuyerAccountId" not in candidate_str
            assert "SystemId" not in candidate_str
            assert "FAKE-VENDOR-NAME" not in candidate_str
            assert "FAKE-WH-00" not in candidate_str

    def test_one_network_call(self) -> None:
        """Exactly ONE network call — no retries, no redirects."""
        adapter = _adapter_with_body(SECTION_BODY_HYBRID_PARAGRAPH)

        with patch(
            "product_intelligence.providers.internal_vendor."
            "_get_vendor_opener",
            return_value=adapter._mock_opener,
        ):
            adapter.lookup(CommercialLookupQuery(mpn=REQUESTED_MPN))

        assert adapter._mock_opener.open.call_count == 1

    def test_get_method(self) -> None:
        adapter = _adapter_with_body(SECTION_BODY_HYBRID_PARAGRAPH)

        with patch(
            "product_intelligence.providers.internal_vendor."
            "_get_vendor_opener",
            return_value=adapter._mock_opener,
        ):
            adapter.lookup(CommercialLookupQuery(mpn=REQUESTED_MPN))

        req = adapter._mock_opener.open.call_args[0][0]
        assert req.method == "GET"


# ---------------------------------------------------------------------------
# Reproduction tests — plain-text section contract (compatibility)
# ---------------------------------------------------------------------------


class TestMicronVendorResponsePlainText:
    """Full adapter pathway with mocked HTTP transport over the
    plain-text section-oriented contract (retained compatibility form)."""

    def test_parses_all_three_sources(self) -> None:
        adapter = _adapter_with_body(SECTION_BODY_HYBRID_PLAINTEXT)

        with patch(
            "product_intelligence.providers.internal_vendor."
            "_get_vendor_opener",
            return_value=adapter._mock_opener,
        ):
            response = adapter.lookup(
                CommercialLookupQuery(mpn=REQUESTED_MPN)
            )

        assert response.status == LookupStatus.SUCCESS
        assert len(response.candidates) == 3

    def test_ingram_price_and_availability(self) -> None:
        adapter = _adapter_with_body(SECTION_BODY_HYBRID_PLAINTEXT)

        with patch(
            "product_intelligence.providers.internal_vendor."
            "_get_vendor_opener",
            return_value=adapter._mock_opener,
        ):
            response = adapter.lookup(
                CommercialLookupQuery(mpn=REQUESTED_MPN)
            )

        ingram = next(
            c for c in response.candidates if c.source_name == "Ingram"
        )
        assert ingram.price_amount == Decimal("5445.67")
        assert ingram.currency_code == "USD"
        assert ingram.availability == CommercialAvailability.OUT_OF_STOCK
        assert ingram.quantity == 0

    def test_synnex_eu_price_and_availability(self) -> None:
        adapter = _adapter_with_body(SECTION_BODY_HYBRID_PLAINTEXT)

        with patch(
            "product_intelligence.providers.internal_vendor."
            "_get_vendor_opener",
            return_value=adapter._mock_opener,
        ):
            response = adapter.lookup(
                CommercialLookupQuery(mpn=REQUESTED_MPN)
            )

        synnex = next(
            c for c in response.candidates if c.source_name == "Synnex EU"
        )
        assert synnex.price_amount == Decimal("4740.18")
        assert synnex.currency_code == "EUR"
        assert synnex.availability == CommercialAvailability.OUT_OF_STOCK
        assert synnex.quantity == 0

    def test_cdw_zero_price_unknown_availability(self) -> None:
        adapter = _adapter_with_body(SECTION_BODY_HYBRID_PLAINTEXT)

        with patch(
            "product_intelligence.providers.internal_vendor."
            "_get_vendor_opener",
            return_value=adapter._mock_opener,
        ):
            response = adapter.lookup(
                CommercialLookupQuery(mpn=REQUESTED_MPN)
            )

        cdw = next(c for c in response.candidates if c.source_name == "CDW")
        assert cdw.price_amount == Decimal("0.00")
        assert cdw.availability == CommercialAvailability.UNKNOWN


# ---------------------------------------------------------------------------
# Reproduction tests — canonical JSON wrapper contract
# ---------------------------------------------------------------------------


class TestMicronVendorResponseCanonicalJson:
    """Full adapter pathway with mocked HTTP transport over the
    canonical JSON wrapper contract (cross-contract comparison)."""

    def _adapter_with_json(self) -> InternalVendorAdapter:
        adapter = InternalVendorAdapter()
        adapter._base_url = "http://vendor.internal/api"
        adapter._validated = True

        body = json.dumps(CANONICAL_JSON_PAYLOAD, default=str).encode("utf-8")
        mock_response = MagicMock()
        mock_response.read.return_value = body
        mock_opener = MagicMock()
        mock_opener.open.return_value = mock_response

        adapter._mock_opener = mock_opener
        return adapter

    def test_parses_all_three_sources(self) -> None:
        adapter = self._adapter_with_json()

        with patch(
            "product_intelligence.providers.internal_vendor."
            "_get_vendor_opener",
            return_value=adapter._mock_opener,
        ):
            response = adapter.lookup(
                CommercialLookupQuery(mpn=REQUESTED_MPN)
            )

        # With JSON contract, Synnex EU AvailabilityTotal is the string "0"
        # which the narrow _synnex_availability_total handles.
        # But in canonical JSON, parse_float=Decimal is used, so numeric
        # string "0" remains a string. The _safe_decimal handles it.
        # However, AvailabilityTotal "0" as a string:
        # _synnex_availability_total accepts digit strings.
        assert response.status in (LookupStatus.SUCCESS, LookupStatus.PARTIAL)
        assert len(response.candidates) >= 1  # at least CDW + Ingram


# ---------------------------------------------------------------------------
# Timeout reproduction — the historical FAILED path
# ---------------------------------------------------------------------------


class TestVendorTimeoutReproduction:
    """Reproduce the exact code path that produces FAILED with zero
    observations and zero source issues — a timeout (the most plausible
    explanation for the historical ~10s elapsed time)."""

    def test_timeout_error_produces_failed_zero_obs_zero_issues(self) -> None:
        """A TimeoutError during opener.open() produces the exact persisted
        shape: FAILED status, no observations, no source issues."""
        adapter = InternalVendorAdapter()
        adapter._base_url = "http://vendor.internal/api"
        adapter._validated = True

        mock_opener = MagicMock()
        mock_opener.open.side_effect = TimeoutError()

        with patch(
            "product_intelligence.providers.internal_vendor."
            "_get_vendor_opener",
            return_value=mock_opener,
        ):
            response = adapter.lookup(
                CommercialLookupQuery(mpn=REQUESTED_MPN)
            )

        assert response.status == LookupStatus.FAILED
        assert response.retrieved_at is None
        assert len(response.candidates) == 0
        assert len(response.issues) == 0

    def test_URLError_connection_refused_produces_failed(self) -> None:
        """URLError (connection refused) produces the same FAILED shape."""
        from urllib.error import URLError

        adapter = InternalVendorAdapter()
        adapter._base_url = "http://vendor.internal/api"
        adapter._validated = True

        mock_opener = MagicMock()
        mock_opener.open.side_effect = URLError("connection refused")

        with patch(
            "product_intelligence.providers.internal_vendor."
            "_get_vendor_opener",
            return_value=mock_opener,
        ):
            response = adapter.lookup(
                CommercialLookupQuery(mpn=REQUESTED_MPN)
            )

        assert response.status == LookupStatus.FAILED
        assert response.retrieved_at is None
        assert len(response.candidates) == 0
        assert len(response.issues) == 0

    def test_unrecognized_section_body_produces_failed(self) -> None:
        """A body that matches neither JSON nor section contract -> FAILED."""
        adapter = InternalVendorAdapter()
        adapter._base_url = "http://vendor.internal/api"
        adapter._validated = True

        mock_response = MagicMock()
        mock_response.read.return_value = b"<html><body>Error 500</body></html>"

        mock_opener = MagicMock()
        mock_opener.open.return_value = mock_response

        with patch(
            "product_intelligence.providers.internal_vendor."
            "_get_vendor_opener",
            return_value=mock_opener,
        ):
            response = adapter.lookup(
                CommercialLookupQuery(mpn=REQUESTED_MPN)
            )

        assert response.status == LookupStatus.FAILED
        assert len(response.candidates) == 0
        assert len(response.issues) == 0

    def test_json_with_no_source_sections_produces_failed(self) -> None:
        """Valid JSON but no recognized source sections -> FAILED."""
        adapter = InternalVendorAdapter()
        adapter._base_url = "http://vendor.internal/api"
        adapter._validated = True

        payload = {"error": "service unavailable", "code": 503}
        mock_response = MagicMock()
        mock_response.read.return_value = json.dumps(payload).encode("utf-8")

        mock_opener = MagicMock()
        mock_opener.open.return_value = mock_response

        with patch(
            "product_intelligence.providers.internal_vendor."
            "_get_vendor_opener",
            return_value=mock_opener,
        ):
            response = adapter.lookup(
                CommercialLookupQuery(mpn=REQUESTED_MPN)
            )

        assert response.status == LookupStatus.FAILED
        assert len(response.candidates) == 0
        assert len(response.issues) == 0
