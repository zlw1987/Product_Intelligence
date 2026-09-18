"""Tests for the concrete internal vendor adapter (PRODUCT-INTEL.4D-B).

All tests are zero-network. The adapter's network call path is tested
indirectly through mocking. Configuration, mapping, and sensitive data
handling are tested directly.

Tests cover:
* Configuration validation (URL format, credentials, etc.)
* Base URL validation
* URL encoding of MPN
* Source-specific mapping: Ingram, CDW, Synnex EU
* Availability truth tables
* Price basis selection (customerPrice vs retailPrice)
* Not-found detection
* Sensitive data stripping (SessionId, BuyerAccountId, SystemId)
* One malformed source section does not destroy others
* Malformed-present customerPrice does NOT fall back to retailPrice
* Note handling (only NO_RETURNS preserved)
* Unknown keys dropped by allowlist
"""

from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from decimal import Decimal
from unittest.mock import MagicMock, patch
from urllib.error import URLError

import pytest

from product_intelligence.providers.commercial import (
    CommercialAvailability,
    CommercialLookupQuery,
    CommercialNoteKind,
    CommercialPriceBasis,
    CommercialSourceCandidate,
    CommercialSourceIssue,
    CommercialSourceResponse,
    LookupStatus,
    SourceOutcome,
)
from product_intelligence.providers.internal_vendor import (
    InternalVendorAdapter,
    _build_lookup_url,
    _filter_sensitive,
    _is_sensitive_key,
    _map_cdw,
    _map_ingram,
    _map_synnex_eu,
    _validate_base_url,
)


# ---------------------------------------------------------------------------
# Configuration validation
# ---------------------------------------------------------------------------


class TestBaseURLValidation:
    def test_valid_http_url(self) -> None:
        result = _validate_base_url("http://157.22.244.39:8808/vendor")
        assert result == "http://157.22.244.39:8808/vendor"

    def test_valid_https_url(self) -> None:
        result = _validate_base_url("https://vendor.internal.example/api")
        assert result == "https://vendor.internal.example/api"

    def test_empty_url_rejected(self) -> None:
        with pytest.raises(ValueError, match="not configured"):
            _validate_base_url("")

    def test_whitespace_only_rejected(self) -> None:
        with pytest.raises(ValueError, match="not configured"):
            _validate_base_url("   ")

    def test_non_http_scheme_rejected(self) -> None:
        with pytest.raises(ValueError, match="http or https"):
            _validate_base_url("ftp://example.com")

    def test_no_host_rejected(self) -> None:
        with pytest.raises(ValueError, match="host"):
            _validate_base_url("http://")

    def test_embedded_credentials_rejected(self) -> None:
        with pytest.raises(ValueError, match="credentials"):
            _validate_base_url("http://user:pass@example.com")

    def test_fragment_rejected(self) -> None:
        with pytest.raises(ValueError, match="fragment"):
            _validate_base_url("http://example.com#section")

    def test_url_stripped(self) -> None:
        result = _validate_base_url("  http://example.com/vendor  ")
        assert result == "http://example.com/vendor"


# ---------------------------------------------------------------------------
# URL building
# ---------------------------------------------------------------------------


class TestBuildLookupUrl:
    def test_simple_mpn(self) -> None:
        url = _build_lookup_url("http://example.com/vendor", "ABC123")
        assert url == "http://example.com/vendor?partno=ABC123"

    def test_mpn_url_encoded(self) -> None:
        url = _build_lookup_url(
            "http://example.com/vendor", "BCM957608-P2200GQF00"
        )
        assert "partno=BCM957608-P2200GQF00" in url

    def test_special_chars_encoded(self) -> None:
        url = _build_lookup_url("http://example.com/vendor", "A/B&C")
        assert "partno=" in url
        # & must be encoded as %26 in the value
        assert "%26" in url  # & encoded
        assert "%2F" in url  # / encoded


# ---------------------------------------------------------------------------
# Sensitive data filtering
# ---------------------------------------------------------------------------


class TestSensitiveDataFiltering:
    def test_session_id_stripped(self) -> None:
        data = {"SessionId": "secret123", "vendorPartNumber": "ABC123"}
        result = _filter_sensitive(data)
        assert "SessionId" not in result
        assert "secret123" not in str(result)

    def test_buyer_account_id_stripped(self) -> None:
        data = {"BuyerAccountId": "BUY456", "price": 100}
        result = _filter_sensitive(data)
        assert "BuyerAccountId" not in result
        assert "BUY456" not in str(result)

    def test_system_id_stripped(self) -> None:
        data = {"SystemId": "SYS789", "sourceName": "Ingram"}
        result = _filter_sensitive(data)
        assert "SystemId" not in result
        assert "SYS789" not in str(result)

    def test_nested_sensitive_stripped(self) -> None:
        data = {
            "sourceName": "Ingram",
            "metadata": {"SessionId": "secret", "BuyerAccountId": "buy123"},
        }
        result = _filter_sensitive(data)
        assert "SessionId" not in str(result)
        assert "BuyerAccountId" not in str(result)
        assert "secret" not in str(result)

    def test_sensitive_at_deep_nesting(self) -> None:
        data = {
            "OnlineCheck": {
                "Header": {"SystemId": "sys999", "CurrencyCode": "USD"},
                "Item": {"vendorPartNumber": "ABC123"},
            }
        }
        result = _filter_sensitive(data)
        assert "SystemId" not in str(result)
        assert "sys999" not in str(result)
        # Non-sensitive fields preserved
        assert "CurrencyCode" in json.dumps(result)

    def test_non_sensitive_keys_preserved(self) -> None:
        data = {
            "sourceName": "Ingram",
            "vendorPartNumber": "ABC123",
            "price": 100,
        }
        result = _filter_sensitive(data)
        assert result["sourceName"] == "Ingram"
        assert result["vendorPartNumber"] == "ABC123"

    def test_is_sensitive_key(self) -> None:
        assert _is_sensitive_key("SessionId") is True
        assert _is_sensitive_key("BuyerAccountId") is True
        assert _is_sensitive_key("SystemId") is True
        assert _is_sensitive_key("vendorPartNumber") is False
        assert _is_sensitive_key("price") is False


# ---------------------------------------------------------------------------
# Ingram mapping
# ---------------------------------------------------------------------------


class TestIngramMapping:
    def _ingram_section(self, **overrides) -> dict:
        base = {
            "sourceName": "Ingram",
            "vendorPartNumber": "BCM957608-P2200GQF00",
            "pricing": {
                "customerPrice": Decimal("2120.00"),
                "retailPrice": Decimal("2500.00"),
                "currencyCode": "USD",
            },
            "availability": {
                "available": True,
                "Avl_Quantity": 10,
            },
        }
        base.update(overrides)
        return base

    def test_customer_price_wins(self) -> None:
        result = _map_ingram(self._ingram_section())
        assert isinstance(result, CommercialSourceCandidate)
        assert result.price_amount == Decimal("2120.00")
        assert result.price_basis == CommercialPriceBasis.CUSTOMER_PRICE

    def test_retail_fallback_when_customer_absent(self) -> None:
        pricing = {
            "retailPrice": Decimal("2500.00"),
            "currencyCode": "USD",
        }
        result = _map_ingram(self._ingram_section(pricing=pricing))
        assert isinstance(result, CommercialSourceCandidate)
        assert result.price_amount == Decimal("2500.00")
        assert result.price_basis == CommercialPriceBasis.RETAIL_PRICE_FALLBACK

    def test_malformed_customer_price_no_fallback(self) -> None:
        """If customerPrice is PRESENT but malformed, do NOT fall back to retail."""
        pricing = {
            "customerPrice": "not_a_number",
            "retailPrice": Decimal("2500.00"),
            "currencyCode": "USD",
        }
        result = _map_ingram(self._ingram_section(pricing=pricing))
        assert isinstance(result, CommercialSourceIssue)
        assert result.outcome == SourceOutcome.MALFORMED_SECTION

    def test_not_found(self) -> None:
        result = _map_ingram({"sourceName": "Ingram", "NotFound": True})
        assert isinstance(result, CommercialSourceIssue)
        assert result.outcome == SourceOutcome.NOT_FOUND

    def test_not_found_lowercase(self) -> None:
        result = _map_ingram({"sourceName": "Ingram", "notFound": True})
        assert isinstance(result, CommercialSourceIssue)
        assert result.outcome == SourceOutcome.NOT_FOUND

    def test_missing_mpn(self) -> None:
        result = _map_ingram(
            self._ingram_section(vendorPartNumber=None)
        )
        assert isinstance(result, CommercialSourceIssue)
        assert result.outcome == SourceOutcome.MISSING_EXPLICIT_MPN

    # Availability truth table
    def test_avail_true_qty_positive_in_stock(self) -> None:
        result = _map_ingram(self._ingram_section(
            availability={"available": True, "Avl_Quantity": 5}
        ))
        assert isinstance(result, CommercialSourceCandidate)
        assert result.availability == CommercialAvailability.IN_STOCK

    def test_avail_true_qty_none_in_stock(self) -> None:
        result = _map_ingram(self._ingram_section(
            availability={"available": True}
        ))
        assert isinstance(result, CommercialSourceCandidate)
        assert result.availability == CommercialAvailability.IN_STOCK

    def test_avail_false_qty_zero_out_of_stock(self) -> None:
        result = _map_ingram(self._ingram_section(
            availability={"available": False, "Avl_Quantity": 0}
        ))
        assert isinstance(result, CommercialSourceCandidate)
        assert result.availability == CommercialAvailability.OUT_OF_STOCK

    def test_avail_false_qty_positive_unknown(self) -> None:
        result = _map_ingram(self._ingram_section(
            availability={"available": False, "Avl_Quantity": 5}
        ))
        assert isinstance(result, CommercialSourceCandidate)
        assert result.availability == CommercialAvailability.UNKNOWN

    def test_avail_true_qty_zero_unknown(self) -> None:
        result = _map_ingram(self._ingram_section(
            availability={"available": True, "Avl_Quantity": 0}
        ))
        assert isinstance(result, CommercialSourceCandidate)
        assert result.availability == CommercialAvailability.UNKNOWN

    def test_avail_none_qty_positive_in_stock(self) -> None:
        result = _map_ingram(self._ingram_section(
            availability={"Avl_Quantity": 5}
        ))
        assert isinstance(result, CommercialSourceCandidate)
        assert result.availability == CommercialAvailability.IN_STOCK

    def test_avail_none_qty_zero_unknown(self) -> None:
        result = _map_ingram(self._ingram_section(
            availability={"Avl_Quantity": 0}
        ))
        assert isinstance(result, CommercialSourceCandidate)
        assert result.availability == CommercialAvailability.UNKNOWN

    def test_avail_false_qty_none_unknown(self) -> None:
        result = _map_ingram(self._ingram_section(
            availability={"available": False}
        ))
        assert isinstance(result, CommercialSourceCandidate)
        assert result.availability == CommercialAvailability.UNKNOWN

    def test_brand_new_policy(self) -> None:
        result = _map_ingram(self._ingram_section())
        assert isinstance(result, CommercialSourceCandidate)
        assert result.brand_new is True
        assert result.brand_new_basis == "VENDOR_API_POLICY"


# ---------------------------------------------------------------------------
# CDW mapping
# ---------------------------------------------------------------------------


class TestCDWMapping:
    def _cdw_section(self, **overrides) -> dict:
        base = {
            "sourceName": "CDW",
            "manufacturerPartNumber": "BCM957608-P2200GQF00",
            "price": Decimal("2100.00"),
            "currencyCode": "USD",
            "inventoryStatus": {
                "stockStatus": "InStock",
                "Avl_Quantity": 48,
            },
        }
        base.update(overrides)
        return base

    def test_basic_mapping(self) -> None:
        result = _map_cdw(self._cdw_section())
        assert isinstance(result, CommercialSourceCandidate)
        assert result.price_amount == Decimal("2100.00")
        assert result.currency_code == "USD"
        assert result.quantity == 48

    def test_instock(self) -> None:
        result = _map_cdw(self._cdw_section())
        assert isinstance(result, CommercialSourceCandidate)
        assert result.availability == CommercialAvailability.IN_STOCK

    def test_outofstock(self) -> None:
        result = _map_cdw(self._cdw_section(
            inventoryStatus={"stockStatus": "OutOfStock"}
        ))
        assert isinstance(result, CommercialSourceCandidate)
        assert result.availability == CommercialAvailability.OUT_OF_STOCK

    def test_unknown_status(self) -> None:
        result = _map_cdw(self._cdw_section(
            inventoryStatus={"stockStatus": "Backorder"}
        ))
        assert isinstance(result, CommercialSourceCandidate)
        assert result.availability == CommercialAvailability.UNKNOWN

    def test_instock_qty_zero_contradiction(self) -> None:
        result = _map_cdw(self._cdw_section(
            inventoryStatus={"stockStatus": "InStock", "Avl_Quantity": 0}
        ))
        assert isinstance(result, CommercialSourceCandidate)
        assert result.availability == CommercialAvailability.UNKNOWN

    def test_outofstock_qty_positive_contradiction(self) -> None:
        result = _map_cdw(self._cdw_section(
            inventoryStatus={"stockStatus": "OutOfStock", "Avl_Quantity": 5}
        ))
        assert isinstance(result, CommercialSourceCandidate)
        assert result.availability == CommercialAvailability.UNKNOWN

    def test_not_found(self) -> None:
        result = _map_cdw({"sourceName": "CDW", "NotFound": True})
        assert isinstance(result, CommercialSourceIssue)
        assert result.outcome == SourceOutcome.NOT_FOUND

    def test_missing_mpn(self) -> None:
        result = _map_cdw(self._cdw_section(manufacturerPartNumber=None))
        assert isinstance(result, CommercialSourceIssue)
        assert result.outcome == SourceOutcome.MISSING_EXPLICIT_MPN


# ---------------------------------------------------------------------------
# Synnex EU mapping
# ---------------------------------------------------------------------------


class TestSynnexEUMapping:
    def _synnex_section(self, **overrides) -> dict:
        base = {
            "sourceName": "Synnex EU",
            "OnlineCheck": {
                "Header": {"CurrencyCode": "EUR"},
                "Item": {
                    "ManufacturerItemIdentifier": "BCM957608-P2200GQF00",
                    "UnitPriceAmount": Decimal("1950.00"),
                    "AvailabilityTotal": 30,
                },
            },
        }
        base.update(overrides)
        return base

    def test_basic_mapping(self) -> None:
        result = _map_synnex_eu(self._synnex_section())
        assert isinstance(result, CommercialSourceCandidate)
        assert result.price_amount == Decimal("1950.00")
        assert result.currency_code == "EUR"
        assert result.quantity == 30
        assert result.availability == CommercialAvailability.IN_STOCK

    def test_avail_zero_out_of_stock(self) -> None:
        online = {
            "Header": {"CurrencyCode": "EUR"},
            "Item": {
                "ManufacturerItemIdentifier": "ABC123",
                "UnitPriceAmount": Decimal("100.00"),
                "AvailabilityTotal": 0,
            },
        }
        result = _map_synnex_eu(
            self._synnex_section(OnlineCheck=online)
        )
        assert isinstance(result, CommercialSourceCandidate)
        assert result.availability == CommercialAvailability.OUT_OF_STOCK

    def test_avail_missing_unknown(self) -> None:
        online = {
            "Header": {"CurrencyCode": "EUR"},
            "Item": {
                "ManufacturerItemIdentifier": "ABC123",
                "UnitPriceAmount": Decimal("100.00"),
            },
        }
        result = _map_synnex_eu(
            self._synnex_section(OnlineCheck=online)
        )
        assert isinstance(result, CommercialSourceCandidate)
        assert result.availability == CommercialAvailability.UNKNOWN

    def test_not_maintained(self) -> None:
        result = _map_synnex_eu({
            "sourceName": "Synnex EU",
            "notMaintained": True,
        })
        assert isinstance(result, CommercialSourceIssue)
        assert result.outcome == SourceOutcome.NOT_FOUND

    def test_no_returns_note(self) -> None:
        online = {
            "Header": {"CurrencyCode": "EUR"},
            "Item": {
                "ManufacturerItemIdentifier": "ABC123",
                "UnitPriceAmount": Decimal("100.00"),
                "AvailabilityTotal": 10,
                "Note": "No Returns",
            },
        }
        result = _map_synnex_eu(
            self._synnex_section(OnlineCheck=online)
        )
        assert isinstance(result, CommercialSourceCandidate)
        assert result.note_kind == CommercialNoteKind.NO_RETURNS

    def test_arbitrary_note_dropped(self) -> None:
        online = {
            "Header": {"CurrencyCode": "EUR"},
            "Item": {
                "ManufacturerItemIdentifier": "ABC123",
                "UnitPriceAmount": Decimal("100.00"),
                "AvailabilityTotal": 10,
                "Note": "Some arbitrary free-form note text",
            },
        }
        result = _map_synnex_eu(
            self._synnex_section(OnlineCheck=online)
        )
        assert isinstance(result, CommercialSourceCandidate)
        assert result.note_kind is None  # arbitrary notes dropped

    def test_not_found_flag(self) -> None:
        result = _map_synnex_eu({
            "sourceName": "Synnex EU",
            "NotFound": True,
        })
        assert isinstance(result, CommercialSourceIssue)
        assert result.outcome == SourceOutcome.NOT_FOUND


# ---------------------------------------------------------------------------
# Adapter configuration
# ---------------------------------------------------------------------------


class TestInternalVendorAdapter:
    def test_lookup_without_config(self) -> None:
        """When PI_VENDOR_LOOKUP_BASE_URL is absent, lookup fails with ValueError."""
        adapter = InternalVendorAdapter()
        with patch.dict(os.environ, {}, clear=True):
            # Remove the config if present
            os.environ.pop("PI_VENDOR_LOOKUP_BASE_URL", None)
            adapter._validated = False
            with pytest.raises(ValueError, match="not configured"):
                adapter.lookup(CommercialLookupQuery(mpn="ABC123"))

    def test_adapter_does_not_read_config_at_init(self) -> None:
        """Adapter __init__ must not read environment."""
        with patch.dict(os.environ, {}, clear=True):
            os.environ.pop("PI_VENDOR_LOOKUP_BASE_URL", None)
            adapter = InternalVendorAdapter()
            assert adapter._validated is False

    def test_network_failure_returns_failed_response(self) -> None:
        """Network failure produces FAILED response, not exception."""
        adapter = InternalVendorAdapter()
        adapter._base_url = "http://example.com/vendor"
        adapter._validated = True

        query = CommercialLookupQuery(mpn="ABC123")
        with patch(
            "product_intelligence.providers.internal_vendor.urlopen",
            side_effect=URLError("connection refused"),
        ):
            response = adapter.lookup(query)

        assert response.status == LookupStatus.FAILED
        assert response.retrieved_at is None

    def test_invalid_json_returns_failed_response(self) -> None:
        """Invalid JSON response produces FAILED response."""
        adapter = InternalVendorAdapter()
        adapter._base_url = "http://example.com/vendor"
        adapter._validated = True

        query = CommercialLookupQuery(mpn="ABC123")

        mock_response = MagicMock()
        mock_response.read.return_value = b"not json at all"

        with patch(
            "product_intelligence.providers.internal_vendor.urlopen",
            return_value=mock_response,
        ):
            response = adapter.lookup(query)

        assert response.status == LookupStatus.FAILED

    def test_oversized_response_returns_failed(self) -> None:
        """Response exceeding 1 MiB returns FAILED."""
        adapter = InternalVendorAdapter()
        adapter._base_url = "http://example.com/vendor"
        adapter._validated = True

        query = CommercialLookupQuery(mpn="ABC123")

        mock_response = MagicMock()
        mock_response.read.return_value = b"X" * (2 * 1024 * 1024)  # 2 MiB

        with patch(
            "product_intelligence.providers.internal_vendor.urlopen",
            return_value=mock_response,
        ):
            response = adapter.lookup(query)

        assert response.status == LookupStatus.FAILED

    def test_sensitive_data_not_in_payload(self) -> None:
        """Sensitive keys are stripped before processing."""
        adapter = InternalVendorAdapter()
        adapter._base_url = "http://example.com/vendor"
        adapter._validated = True

        query = CommercialLookupQuery(mpn="BCM957608-P2200GQF00")

        payload = {
            "Ingram": {
                "sourceName": "Ingram",
                "vendorPartNumber": "BCM957608-P2200GQF00",
                "pricing": {
                    "customerPrice": "2120.00",
                    "retailPrice": "2500.00",
                    "currencyCode": "USD",
                },
                "availability": {
                    "available": True,
                    "Avl_Quantity": 10,
                },
            },
            "SessionId": "SENSITIVE_SESSION_123",
            "BuyerAccountId": "SENSITIVE_BUYER_456",
            "SystemId": "SENSITIVE_SYSTEM_789",
        }

        mock_response = MagicMock()
        mock_response.read.return_value = json.dumps(payload).encode("utf-8")

        with patch(
            "product_intelligence.providers.internal_vendor.urlopen",
            return_value=mock_response,
        ):
            response = adapter.lookup(query)

        assert response.status == LookupStatus.SUCCESS
        # Verify sensitive data does not appear anywhere in the response
        assert "SENSITIVE_SESSION_123" not in str(response)
        assert "SENSITIVE_BUYER_456" not in str(response)
        assert "SENSITIVE_SYSTEM_789" not in str(response)
        assert "SessionId" not in str(response)
        assert "BuyerAccountId" not in str(response)
        assert "SystemId" not in str(response)

    def test_malformed_one_source_does_not_destroy_others(self) -> None:
        """One malformed source section does not destroy valid sections."""
        adapter = InternalVendorAdapter()
        adapter._base_url = "http://example.com/vendor"
        adapter._validated = True

        query = CommercialLookupQuery(mpn="BCM957608-P2200GQF00")

        payload = {
            "Ingram": {
                "sourceName": "Ingram",
                "vendorPartNumber": "BCM957608-P2200GQF00",
                "pricing": {
                    "customerPrice": "2120.00",
                    "currencyCode": "USD",
                },
                "availability": {"available": True, "Avl_Quantity": 10},
            },
            "CDW": {
                "sourceName": "CDW",
                "manufacturerPartNumber": "BCM957608-P2200GQF00",
                "price": "malformed_not_a_number",
                "currencyCode": "USD",
                "inventoryStatus": {"stockStatus": "InStock"},
            },
        }

        mock_response = MagicMock()
        mock_response.read.return_value = json.dumps(payload).encode("utf-8")

        with patch(
            "product_intelligence.providers.internal_vendor.urlopen",
            return_value=mock_response,
        ):
            response = adapter.lookup(query)

        assert response.status == LookupStatus.PARTIAL
        assert len(response.candidates) >= 1  # Ingram should succeed
        assert len(response.issues) >= 1  # CDW should have an issue
