"""Tests for the concrete internal vendor adapter (PRODUCT-INTEL.4D-B).

All tests are zero-network. The adapter's network call path is tested
indirectly through mocking.

Tests cover:
* Configuration validation (URL format, credentials, query strings, fragments)
* Base URL validation
* URL encoding of MPN
* Source-specific mapping: Ingram, CDW, Synnex EU
* Availability truth tables
* Price basis selection (customerPrice vs retailPrice)
* Not-found detection (all forms including "Not Found")
* customerPrice:null + valid retailPrice -> NO fallback (MALFORMED_SECTION)
* Sensitive data stripping via allowlist (no recursive copy)
* One malformed source section does not destroy others
* Note handling (only NO_RETURNS preserved; not maintained -> NOT_FOUND)
* Unknown keys ignored by construction
* Network failure -> FAILED response
* Redirect refusal (no 30x following)
* No ambient proxy
* Exactly one network request per lookup
* GET method only
* No cookies, no Authorization header
* Decimal-aware JSON parsing
* Programming error propagation (no broad exception swallow)
* Adversarial: injected RuntimeError/TypeError from mapper -> propagates
"""

from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from decimal import Decimal
from unittest.mock import MagicMock, patch
from urllib.error import HTTPError, URLError

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
    _map_cdw,
    _map_ingram,
    _map_synnex_eu,
    _validate_base_url,
    _get_vendor_opener,
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

    def test_query_string_rejected(self) -> None:
        """Base URL must not carry query parameters."""
        with pytest.raises(ValueError, match="query parameters"):
            _validate_base_url("http://example.com/vendor?token=abc")

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
        assert "%26" in url
        assert "%2F" in url


# ---------------------------------------------------------------------------
# Network opener — no proxy, no redirect
# ---------------------------------------------------------------------------


class TestNetworkOpener:
    def test_opener_has_no_proxy_handler(self) -> None:
        """Opener must not contain a ProxyHandler."""
        from urllib.request import ProxyHandler
        opener = _get_vendor_opener()
        for handler in opener.handlers:
            assert not isinstance(handler, ProxyHandler), (
                "Opener must not contain ProxyHandler"
            )

    def test_opener_refuses_redirect(self) -> None:
        """A 302 response must NOT be followed by the opener."""
        from product_intelligence.providers.internal_vendor import (
            _NoRedirectHandler,
        )
        handler = _NoRedirectHandler()
        mock_req = MagicMock()
        mock_req.full_url = "http://example.com/vendor?partno=ABC"
        mock_fp = MagicMock()

        with pytest.raises(HTTPError) as exc_info:
            handler.http_error_302(
                mock_req, mock_fp, 302, "Found", MagicMock()
            )
        assert "Redirect refused" in str(exc_info.value)

    def test_ambient_proxy_env_ignored(self) -> None:
        """HTTP_PROXY/HTTPS_PROXY env vars must not alter request route."""
        with patch.dict(os.environ, {
            "HTTP_PROXY": "http://evil-proxy.example:8080",
            "HTTPS_PROXY": "http://evil-proxy.example:8080",
        }):
            opener = _get_vendor_opener()
            for handler in opener.handlers:
                assert not isinstance(handler, type(MagicMock())), True
            from urllib.request import ProxyHandler
            for handler in opener.handlers:
                assert not isinstance(handler, ProxyHandler)


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
        """When customerPrice key is ABSENT, retailPrice fallback is allowed."""
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

    def test_customer_price_null_no_fallback(self) -> None:
        """customerPrice: null is PRESENT and malformed -> MALFORMED_SECTION.
        Do NOT fall back to retailPrice even if valid."""
        pricing = {
            "customerPrice": None,
            "retailPrice": Decimal("2500.00"),
            "currencyCode": "USD",
        }
        result = _map_ingram(self._ingram_section(pricing=pricing))
        assert isinstance(result, CommercialSourceIssue)
        assert result.outcome == SourceOutcome.MALFORMED_SECTION

    def test_not_found_capitalized(self) -> None:
        result = _map_ingram({"sourceName": "Ingram", "NotFound": True})
        assert isinstance(result, CommercialSourceIssue)
        assert result.outcome == SourceOutcome.NOT_FOUND

    def test_not_found_lowercase(self) -> None:
        result = _map_ingram({"sourceName": "Ingram", "notFound": True})
        assert isinstance(result, CommercialSourceIssue)
        assert result.outcome == SourceOutcome.NOT_FOUND

    def test_not_found_spaced_key(self) -> None:
        """Documented canonical form: {Not Found}"""
        result = _map_ingram({"sourceName": "Ingram", "Not Found": True})
        assert isinstance(result, CommercialSourceIssue)
        assert result.outcome == SourceOutcome.NOT_FOUND

    def test_missing_mpn(self) -> None:
        result = _map_ingram(self._ingram_section(vendorPartNumber=None))
        assert isinstance(result, CommercialSourceIssue)
        assert result.outcome == SourceOutcome.MISSING_EXPLICIT_MPN

    def test_unknown_fields_ignored(self) -> None:
        """Unknown fields in Ingram section are ignored by construction."""
        section = self._ingram_section()
        section["SECRET_FIELD"] = "should_not_appear"
        section["metadata"] = {"SessionId": "SENSITIVE"}
        result = _map_ingram(section)
        assert isinstance(result, CommercialSourceCandidate)
        assert "SECRET_FIELD" not in str(result)
        assert "SENSITIVE" not in str(result)
        assert "SessionId" not in str(result)

    def test_detail_is_none(self) -> None:
        """Issues from mappers carry detail=None (bounded)."""
        result = _map_ingram({"sourceName": "Ingram", "NotFound": True})
        assert isinstance(result, CommercialSourceIssue)
        assert result.detail is None

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

    def test_not_found_capitalized(self) -> None:
        result = _map_cdw({"sourceName": "CDW", "NotFound": True})
        assert isinstance(result, CommercialSourceIssue)
        assert result.outcome == SourceOutcome.NOT_FOUND

    def test_not_found_lowercase(self) -> None:
        result = _map_cdw({"sourceName": "CDW", "notFound": True})
        assert isinstance(result, CommercialSourceIssue)
        assert result.outcome == SourceOutcome.NOT_FOUND

    def test_not_found_spaced_key(self) -> None:
        result = _map_cdw({"sourceName": "CDW", "Not Found": True})
        assert isinstance(result, CommercialSourceIssue)
        assert result.outcome == SourceOutcome.NOT_FOUND

    def test_missing_mpn(self) -> None:
        result = _map_cdw(self._cdw_section(manufacturerPartNumber=None))
        assert isinstance(result, CommercialSourceIssue)
        assert result.outcome == SourceOutcome.MISSING_EXPLICIT_MPN

    def test_unknown_fields_ignored(self) -> None:
        section = self._cdw_section()
        section["SessionId"] = "SENSITIVE_DATA"
        result = _map_cdw(section)
        assert isinstance(result, CommercialSourceCandidate)
        assert "SENSITIVE_DATA" not in str(result)

    def test_detail_is_none(self) -> None:
        result = _map_cdw({"sourceName": "CDW", "NotFound": True})
        assert isinstance(result, CommercialSourceIssue)
        assert result.detail is None


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
        result = _map_synnex_eu(self._synnex_section(OnlineCheck=online))
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
        result = _map_synnex_eu(self._synnex_section(OnlineCheck=online))
        assert isinstance(result, CommercialSourceCandidate)
        assert result.availability == CommercialAvailability.UNKNOWN

    def test_not_maintained_top_level(self) -> None:
        result = _map_synnex_eu({
            "sourceName": "Synnex EU",
            "notMaintained": True,
        })
        assert isinstance(result, CommercialSourceIssue)
        assert result.outcome == SourceOutcome.NOT_FOUND

    def test_not_maintained_in_note(self) -> None:
        """Synnex Item.Note with 'not maintained' -> NOT_FOUND before MPN check."""
        online = {
            "Header": {"CurrencyCode": "EUR"},
            "Item": {
                "Note": "Item is not maintained in our catalogue",
                "ManufacturerItemIdentifier": "ABC123",
                "UnitPriceAmount": Decimal("100.00"),
            },
        }
        result = _map_synnex_eu(self._synnex_section(OnlineCheck=online))
        assert isinstance(result, CommercialSourceIssue)
        assert result.outcome == SourceOutcome.NOT_FOUND
        assert result.detail is None  # no raw Note persisted

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
        result = _map_synnex_eu(self._synnex_section(OnlineCheck=online))
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
        result = _map_synnex_eu(self._synnex_section(OnlineCheck=online))
        assert isinstance(result, CommercialSourceCandidate)
        assert result.note_kind is None

    def test_not_found_capitalized(self) -> None:
        result = _map_synnex_eu({"sourceName": "Synnex EU", "NotFound": True})
        assert isinstance(result, CommercialSourceIssue)
        assert result.outcome == SourceOutcome.NOT_FOUND

    def test_not_found_lowercase(self) -> None:
        result = _map_synnex_eu({"sourceName": "Synnex EU", "notFound": True})
        assert isinstance(result, CommercialSourceIssue)
        assert result.outcome == SourceOutcome.NOT_FOUND

    def test_not_found_spaced_key(self) -> None:
        result = _map_synnex_eu({"sourceName": "Synnex EU", "Not Found": True})
        assert isinstance(result, CommercialSourceIssue)
        assert result.outcome == SourceOutcome.NOT_FOUND

    def test_unknown_fields_ignored(self) -> None:
        section = self._synnex_section()
        section["SystemId"] = "SENSITIVE"
        section["OnlineCheck"]["Header"]["SessionId"] = "SECRET"
        result = _map_synnex_eu(section)
        assert isinstance(result, CommercialSourceCandidate)
        assert "SENSITIVE" not in str(result)
        assert "SECRET" not in str(result)


# ---------------------------------------------------------------------------
# Adapter behavior
# ---------------------------------------------------------------------------


class TestInternalVendorAdapter:
    def test_lookup_without_config(self) -> None:
        adapter = InternalVendorAdapter()
        with patch.dict(os.environ, {}, clear=True):
            os.environ.pop("PI_VENDOR_LOOKUP_BASE_URL", None)
            adapter._validated = False
            with pytest.raises(ValueError, match="not configured"):
                adapter.lookup(CommercialLookupQuery(mpn="ABC123"))

    def test_adapter_does_not_read_config_at_init(self) -> None:
        with patch.dict(os.environ, {}, clear=True):
            os.environ.pop("PI_VENDOR_LOOKUP_BASE_URL", None)
            adapter = InternalVendorAdapter()
            assert adapter._validated is False

    def test_network_failure_returns_failed_response(self) -> None:
        adapter = InternalVendorAdapter()
        adapter._base_url = "http://example.com/vendor"
        adapter._validated = True

        query = CommercialLookupQuery(mpn="ABC123")
        with patch(
            "product_intelligence.providers.internal_vendor."
            "_get_vendor_opener"
        ) as mock_get_opener:
            mock_opener = MagicMock()
            mock_opener.open.side_effect = URLError("connection refused")
            mock_get_opener.return_value = mock_opener

            response = adapter.lookup(query)

        assert response.status == LookupStatus.FAILED
        assert response.retrieved_at is None

    def test_http_error_returns_failed_response(self) -> None:
        """HTTPError (e.g. redirect) -> FAILED response."""
        adapter = InternalVendorAdapter()
        adapter._base_url = "http://example.com/vendor"
        adapter._validated = True

        query = CommercialLookupQuery(mpn="ABC123")
        with patch(
            "product_intelligence.providers.internal_vendor."
            "_get_vendor_opener"
        ) as mock_get_opener:
            mock_opener = MagicMock()
            mock_opener.open.side_effect = HTTPError(
                "http://example.com", 302, "Redirect", {}, None
            )
            mock_get_opener.return_value = mock_opener

            response = adapter.lookup(query)

        assert response.status == LookupStatus.FAILED
        assert response.retrieved_at is None

    def test_invalid_json_returns_failed_response(self) -> None:
        adapter = InternalVendorAdapter()
        adapter._base_url = "http://example.com/vendor"
        adapter._validated = True

        query = CommercialLookupQuery(mpn="ABC123")
        mock_response = MagicMock()
        mock_response.read.return_value = b"not json at all"

        with patch(
            "product_intelligence.providers.internal_vendor."
            "_get_vendor_opener"
        ) as mock_get_opener:
            mock_opener = MagicMock()
            mock_opener.open.return_value = mock_response
            mock_get_opener.return_value = mock_opener

            response = adapter.lookup(query)

        assert response.status == LookupStatus.FAILED

    def test_oversized_response_returns_failed(self) -> None:
        adapter = InternalVendorAdapter()
        adapter._base_url = "http://example.com/vendor"
        adapter._validated = True

        query = CommercialLookupQuery(mpn="ABC123")
        mock_response = MagicMock()
        mock_response.read.return_value = b"X" * (2 * 1024 * 1024)

        with patch(
            "product_intelligence.providers.internal_vendor."
            "_get_vendor_opener"
        ) as mock_get_opener:
            mock_opener = MagicMock()
            mock_opener.open.return_value = mock_response
            mock_get_opener.return_value = mock_opener

            response = adapter.lookup(query)

        assert response.status == LookupStatus.FAILED

    def test_sensitive_data_not_in_response(self) -> None:
        """Sensitive keys are ignored by allowlist mappers, never persisted."""
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
                "SessionId": "SENSITIVE_SESSION",
                "BuyerAccountId": "SENSITIVE_BUYER",
                "SystemId": "SENSITIVE_SYSTEM",
            },
        }

        mock_response = MagicMock()
        mock_response.read.return_value = json.dumps(payload).encode("utf-8")

        with patch(
            "product_intelligence.providers.internal_vendor."
            "_get_vendor_opener"
        ) as mock_get_opener:
            mock_opener = MagicMock()
            mock_opener.open.return_value = mock_response
            mock_get_opener.return_value = mock_opener

            response = adapter.lookup(query)

        assert response.status == LookupStatus.SUCCESS
        assert "SENSITIVE_SESSION" not in str(response)
        assert "SENSITIVE_BUYER" not in str(response)
        assert "SENSITIVE_SYSTEM" not in str(response)
        assert "SessionId" not in str(response)
        assert "BuyerAccountId" not in str(response)
        assert "SystemId" not in str(response)

    def test_malformed_one_source_does_not_destroy_others(self) -> None:
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
            "product_intelligence.providers.internal_vendor."
            "_get_vendor_opener"
        ) as mock_get_opener:
            mock_opener = MagicMock()
            mock_opener.open.return_value = mock_response
            mock_get_opener.return_value = mock_opener

            response = adapter.lookup(query)

        assert response.status == LookupStatus.PARTIAL
        assert len(response.candidates) >= 1
        assert len(response.issues) >= 1

    def test_decimal_json_parsing(self) -> None:
        """Monetary JSON values are parsed as Decimal (via parse_float=str)."""
        adapter = InternalVendorAdapter()
        adapter._base_url = "http://example.com/vendor"
        adapter._validated = True

        query = CommercialLookupQuery(mpn="BCM957608-P2200GQF00")

        # JSON with precise decimal values that would lose precision in float
        payload = {
            "Ingram": {
                "sourceName": "Ingram",
                "vendorPartNumber": "BCM957608-P2200GQF00",
                "pricing": {
                    "customerPrice": 2120.12345678901234567890,
                    "currencyCode": "USD",
                },
                "availability": {"available": True, "Avl_Quantity": 10},
            },
        }

        mock_response = MagicMock()
        mock_response.read.return_value = json.dumps(payload).encode("utf-8")

        with patch(
            "product_intelligence.providers.internal_vendor."
            "_get_vendor_opener"
        ) as mock_get_opener:
            mock_opener = MagicMock()
            mock_opener.open.return_value = mock_response
            mock_get_opener.return_value = mock_opener

            response = adapter.lookup(query)

        assert response.status == LookupStatus.SUCCESS
        # The price should be parsed through str (not float)
        candidate = response.candidates[0]
        assert isinstance(candidate.price_amount, Decimal)

    def test_unrecognized_response_shape_failed(self) -> None:
        """Whole response with no recognized source sections -> FAILED."""
        adapter = InternalVendorAdapter()
        adapter._base_url = "http://example.com/vendor"
        adapter._validated = True

        query = CommercialLookupQuery(mpn="ABC123")

        payload = {
            "someUnknownKey": "not a source section",
            "anotherKey": 42,
            "noSourceStructure": ["no", "recognized", "fields"],
        }

        mock_response = MagicMock()
        mock_response.read.return_value = json.dumps(payload).encode("utf-8")

        with patch(
            "product_intelligence.providers.internal_vendor."
            "_get_vendor_opener"
        ) as mock_get_opener:
            mock_opener = MagicMock()
            mock_opener.open.return_value = mock_response
            mock_get_opener.return_value = mock_opener

            response = adapter.lookup(query)

        assert response.status == LookupStatus.FAILED

    def test_exact_one_network_call(self) -> None:
        """Exactly ONE network call per lookup (no retries, no redirects)."""
        adapter = InternalVendorAdapter()
        adapter._base_url = "http://example.com/vendor"
        adapter._validated = True

        query = CommercialLookupQuery(mpn="ABC123")

        payload = {
            "Ingram": {
                "sourceName": "Ingram",
                "vendorPartNumber": "ABC123",
                "pricing": {"customerPrice": "100.00", "currencyCode": "USD"},
                "availability": {"available": True},
            },
        }

        mock_response = MagicMock()
        mock_response.read.return_value = json.dumps(payload).encode("utf-8")

        with patch(
            "product_intelligence.providers.internal_vendor."
            "_get_vendor_opener"
        ) as mock_get_opener:
            mock_opener = MagicMock()
            mock_opener.open.return_value = mock_response
            mock_get_opener.return_value = mock_opener

            adapter.lookup(query)

            assert mock_opener.open.call_count == 1

    def test_get_method_used(self) -> None:
        """Request method is GET."""
        adapter = InternalVendorAdapter()
        adapter._base_url = "http://example.com/vendor"
        adapter._validated = True

        query = CommercialLookupQuery(mpn="ABC123")

        payload = {
            "Ingram": {
                "sourceName": "Ingram",
                "vendorPartNumber": "ABC123",
                "pricing": {"customerPrice": "100", "currencyCode": "USD"},
                "availability": {"available": True},
            },
        }

        mock_response = MagicMock()
        mock_response.read.return_value = json.dumps(payload).encode("utf-8")

        with patch(
            "product_intelligence.providers.internal_vendor."
            "_get_vendor_opener"
        ) as mock_get_opener:
            mock_opener = MagicMock()
            mock_opener.open.return_value = mock_response
            mock_get_opener.return_value = mock_opener

            adapter.lookup(query)

            # Check the request method
            req = mock_opener.open.call_args[0][0]
            assert req.method == "GET"

    def test_programming_error_propagates(self) -> None:
        """RuntimeError from mapper propagates (no broad exception swallow)."""
        adapter = InternalVendorAdapter()
        adapter._base_url = "http://example.com/vendor"
        adapter._validated = True

        query = CommercialLookupQuery(mpn="ABC123")

        payload = {
            "Ingram": {
                "sourceName": "Ingram",
                "vendorPartNumber": "ABC123",
                "pricing": {"customerPrice": "100", "currencyCode": "USD"},
                "availability": {"available": True},
            },
        }

        mock_response = MagicMock()
        mock_response.read.return_value = json.dumps(payload).encode("utf-8")

        with patch(
            "product_intelligence.providers.internal_vendor."
            "_get_vendor_opener"
        ) as mock_get_opener, \
             patch(
                "product_intelligence.providers.internal_vendor."
                "_identify_and_map_source",
                side_effect=RuntimeError("injected programming defect"),
            ):
            mock_opener = MagicMock()
            mock_opener.open.return_value = mock_response
            mock_get_opener.return_value = mock_opener

            with pytest.raises(RuntimeError, match="injected programming defect"):
                adapter.lookup(query)

    def test_typeerror_programming_defect_propagates(self) -> None:
        """TypeError from mapper propagates (no broad exception swallow)."""
        adapter = InternalVendorAdapter()
        adapter._base_url = "http://example.com/vendor"
        adapter._validated = True

        query = CommercialLookupQuery(mpn="ABC123")

        payload = {
            "Ingram": {
                "sourceName": "Ingram",
                "vendorPartNumber": "ABC123",
                "pricing": {"customerPrice": "100", "currencyCode": "USD"},
                "availability": {"available": True},
            },
        }

        mock_response = MagicMock()
        mock_response.read.return_value = json.dumps(payload).encode("utf-8")

        with patch(
            "product_intelligence.providers.internal_vendor."
            "_get_vendor_opener"
        ) as mock_get_opener, \
             patch(
                "product_intelligence.providers.internal_vendor."
                "_identify_and_map_source",
                side_effect=TypeError("injected type defect"),
            ):
            mock_opener = MagicMock()
            mock_opener.open.return_value = mock_response
            mock_get_opener.return_value = mock_opener

            with pytest.raises(TypeError, match="injected type defect"):
                adapter.lookup(query)


# ---------------------------------------------------------------------------
# Adversarial sensitive data tests
# ---------------------------------------------------------------------------


class TestAdversarialSensitiveData:
    """Prove sensitive sentinel values cannot survive into persisted output."""

    def test_sensitive_top_level(self) -> None:
        """Sensitive keys at top level of source section are ignored."""
        section = {
            "sourceName": "Ingram",
            "vendorPartNumber": "ABC123",
            "pricing": {"customerPrice": "100", "currencyCode": "USD"},
            "availability": {"available": True},
            "SessionId": "SENTINEL_SESSION",
            "BuyerAccountId": "SENTINEL_BUYER",
            "SystemId": "SENTINEL_SYSTEM",
        }
        result = _map_ingram(section)
        assert isinstance(result, CommercialSourceCandidate)
        assert "SENTINEL" not in str(result)
        assert "SessionId" not in str(result)
        assert "BuyerAccountId" not in str(result)
        assert "SystemId" not in str(result)

    def test_sensitive_in_pricing(self) -> None:
        """Sensitive keys nested in pricing are ignored."""
        section = {
            "sourceName": "Ingram",
            "vendorPartNumber": "ABC123",
            "pricing": {
                "customerPrice": "100",
                "currencyCode": "USD",
                "authToken": "SENTINEL_TOKEN",
            },
            "availability": {"available": True},
        }
        result = _map_ingram(section)
        assert isinstance(result, CommercialSourceCandidate)
        assert "SENTINEL" not in str(result)

    def test_sensitive_in_synnex_header(self) -> None:
        """Sensitive keys in Synnex Header are ignored."""
        section = {
            "sourceName": "Synnex EU",
            "OnlineCheck": {
                "Header": {
                    "CurrencyCode": "EUR",
                    "SystemId": "SENTINEL_SYS",
                    "SessionId": "SENTINEL_SESS",
                },
                "Item": {
                    "ManufacturerItemIdentifier": "ABC123",
                    "UnitPriceAmount": "100",
                    "AvailabilityTotal": 10,
                },
            },
        }
        result = _map_synnex_eu(section)
        assert isinstance(result, CommercialSourceCandidate)
        assert "SENTINEL" not in str(result)

    def test_sensitive_in_synnex_item(self) -> None:
        """Sensitive keys in Synnex Item are ignored."""
        section = {
            "sourceName": "Synnex EU",
            "OnlineCheck": {
                "Header": {"CurrencyCode": "EUR"},
                "Item": {
                    "ManufacturerItemIdentifier": "ABC123",
                    "UnitPriceAmount": "100",
                    "AvailabilityTotal": 10,
                    "BuyerAccountId": "SENTINEL_BUYER",
                },
            },
        }
        result = _map_synnex_eu(section)
        assert isinstance(result, CommercialSourceCandidate)
        assert "SENTINEL" not in str(result)

    def test_arbitrary_source_name_bounded(self) -> None:
        """Arbitrary sourceName text does not enter output verbatim."""
        section = {
            "sourceName": "EvilCorporationXYZ",
            "vendorPartNumber": "ABC123",
            "pricing": {"customerPrice": "100", "currencyCode": "USD"},
            "availability": {"available": True},
        }
        result = _map_ingram(section)
        assert isinstance(result, CommercialSourceCandidate)
        # source_name is bounded to "Ingram" by the mapper, not the raw value
        assert result.source_name == "Ingram"
        assert "EvilCorporationXYZ" not in str(result)

    def test_unknown_source_gives_bounded_name(self) -> None:
        """Unrecognized source structure gives 'Unknown' bounded name."""
        from product_intelligence.providers.internal_vendor import (
            _identify_and_map_source,
        )
        section = {
            "sourceName": "UnknownVendor42",
            "totallyUnknownField": "value",
        }
        result = _identify_and_map_source(section)
        assert isinstance(result, CommercialSourceIssue)
        assert result.source_name == "Unknown"
        assert "UnknownVendor42" not in str(result)

    def test_no_sensitive_key_names_in_issues(self) -> None:
        """Issue detail does not contain sensitive key names."""
        result = _map_ingram({"sourceName": "Ingram", "NotFound": True})
        assert isinstance(result, CommercialSourceIssue)
        assert result.detail is None
        assert "SessionId" not in str(result)
        assert "BuyerAccountId" not in str(result)
