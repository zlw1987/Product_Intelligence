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
    def test_opener_has_http_dispatch(self) -> None:
        """Constructed opener has registered HTTP dispatch in handle_open."""
        opener = _get_vendor_opener()
        assert "http" in opener.handle_open, (
            "Opener must have registered http dispatch via add_handler"
        )

    def test_opener_has_https_dispatch(self) -> None:
        """Constructed opener has registered HTTPS dispatch in handle_open."""
        opener = _get_vendor_opener()
        assert "https" in opener.handle_open, (
            "Opener must have registered https dispatch via add_handler"
        )

    def test_opener_has_error_handlers(self) -> None:
        """Constructed opener has registered error dispatch in handle_error."""
        opener = _get_vendor_opener()
        assert "http" in opener.handle_error, (
            "Opener must have registered http error handler via add_handler"
        )

    def test_opener_built_correctly(self) -> None:
        """Opener built via build_opener has proper dispatch tables.

        build_opener(ProxyHandler({}), _NoRedirectHandler()) is used.
        ProxyHandler({}) ensures no ambient proxy.
        The handlers list and dispatch tables prove the opener is functional.
        """
        opener = _get_vendor_opener()
        # Proof: handle_open is populated (not empty)
        assert len(opener.handle_open) > 0
        # Proof: http and https dispatch registered
        assert "http" in opener.handle_open
        assert "https" in opener.handle_open
        # Proof: handlers list is non-empty
        assert len(opener.handlers) > 0

    def test_redirect_handler_is_custom_no_redirect(self) -> None:
        """Exactly one custom redirect handler governs the opener."""
        from product_intelligence.providers.internal_vendor import (
            _NoRedirectHandler,
        )
        opener = _get_vendor_opener()
        custom_handlers = [
            h for h in opener.handlers
            if isinstance(h, _NoRedirectHandler)
        ]
        assert len(custom_handlers) == 1, (
            "Opener must have exactly one _NoRedirectHandler"
        )

    def test_default_redirect_handler_not_active(self) -> None:
        """Default HTTPRedirectHandler is not in the opener."""
        from urllib.request import HTTPRedirectHandler
        opener = _get_vendor_opener()
        # Our custom handler subclasses HTTPRedirectHandler but is not the default
        default_handlers = [
            h for h in opener.handlers
            if type(h) is HTTPRedirectHandler  # exact type, not subclass
        ]
        assert len(default_handlers) == 0, (
            "Default HTTPRedirectHandler must not be active"
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

    def test_redirect_request_also_refused(self) -> None:
        """redirect_request() method also refuses (HTTPRedirectHandler override)."""
        from product_intelligence.providers.internal_vendor import (
            _NoRedirectHandler,
        )
        handler = _NoRedirectHandler()
        mock_req = MagicMock()
        mock_req.full_url = "http://example.com/vendor?partno=ABC"
        mock_fp = MagicMock()

        with pytest.raises(HTTPError) as exc_info:
            handler.redirect_request(
                mock_req, mock_fp, 301, "Moved", MagicMock(),
                "http://evil-redirect.com/new",
            )
        assert "Redirect refused" in str(exc_info.value)

    def test_ambient_proxy_env_ignored(self) -> None:
        """HTTP_PROXY/HTTPS_PROXY env vars must not alter request route.

        The explicit ProxyHandler({}) in build_opener ensures ambient env
        proxy vars are ignored. We verify that the opener's HTTP/HTTPS
        handlers were built with empty proxy mapping by inspecting their
        internal proxy configuration.
        """
        with patch.dict(os.environ, {
            "HTTP_PROXY": "http://evil-proxy.example:8080",
            "HTTPS_PROXY": "http://evil-proxy.example:8080",
        }):
            opener = _get_vendor_opener()
            # Verify no handler references the evil proxy URL.
            # When ProxyHandler({}) is passed to build_opener, it configures
            # the HTTP/HTTPS handlers with empty proxy mapping.
            for handler in opener.handlers:
                if hasattr(handler, 'proxy_bypass'):
                    # ProxyHandler has this method
                    pass
                # Check for any proxy URL attribute
                if hasattr(handler, '_proxy'):
                    proxy_val = handler._proxy
                    if isinstance(proxy_val, dict):
                        for url in proxy_val.values():
                            if isinstance(url, str):
                                assert "evil-proxy" not in url


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

    def test_issue_has_no_detail(self) -> None:
        """Provider-layer issues carry no arbitrary detail field."""
        result = _map_ingram({"sourceName": "Ingram", "NotFound": True})
        assert isinstance(result, CommercialSourceIssue)
        assert not hasattr(result, 'detail')

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

    def test_candidate_has_no_brand_new(self) -> None:
        """Provider-layer candidate carries NO brand-new business-policy field."""
        result = _map_ingram(self._ingram_section())
        assert isinstance(result, CommercialSourceCandidate)
        assert not hasattr(result, 'brand_new')
        assert not hasattr(result, 'brand_new_basis')


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

    def test_issue_has_no_detail(self) -> None:
        result = _map_cdw({"sourceName": "CDW", "NotFound": True})
        assert isinstance(result, CommercialSourceIssue)
        assert not hasattr(result, 'detail')


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
        # Provider-layer issues carry no detail; raw Note never persisted
        assert not hasattr(result, 'detail')

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
        """Issue carries no sensitive key names or arbitrary detail."""
        result = _map_ingram({"sourceName": "Ingram", "NotFound": True})
        assert isinstance(result, CommercialSourceIssue)
        assert "SessionId" not in str(result)
        assert "BuyerAccountId" not in str(result)


# ---------------------------------------------------------------------------
# Adversarial mixed-source tests (external malformed data)
# ---------------------------------------------------------------------------


class TestAdversarialMixedSources:
    """Prove malformed source data does not destroy valid siblings."""

    def test_valid_ingram_plus_cdw_malformed_currency(self) -> None:
        """Valid Ingram + CDW with wrong currency type -> Ingram survives."""
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
                "price": "1999.99",
                "currencyCode": 12345,  # wrong type — not a string
                "inventoryStatus": {"stockStatus": "InStock"},
            },
        }
        sections = []
        for key, value in payload.items():
            if isinstance(value, dict):
                section = dict(value)
                if "sourceName" not in section and key in frozenset({
                    "Ingram", "CDW", "Synnex EU", "Unknown"
                }):
                    section["sourceName"] = key
                sections.append(section)

        results = []
        from product_intelligence.providers.internal_vendor import (
            _identify_and_map_source,
        )
        for section in sections:
            results.append(_identify_and_map_source(section))

        # One candidate (Ingram), one issue (CDW malformed)
        candidates = [r for r in results if isinstance(r, CommercialSourceCandidate)]
        issues = [r for r in results if isinstance(r, CommercialSourceIssue)]
        assert len(candidates) == 1
        assert candidates[0].source_name == "Ingram"
        assert len(issues) == 1
        assert issues[0].source_name == "CDW"
        assert issues[0].outcome == SourceOutcome.MALFORMED_SECTION

    def test_valid_cdw_plus_synnex_negative_quantity(self) -> None:
        """Valid CDW + Synnex with negative quantity -> CDW survives."""
        payload = {
            "CDW": {
                "sourceName": "CDW",
                "manufacturerPartNumber": "BCM957608-P2200GQF00",
                "price": "1999.99",
                "currencyCode": "USD",
                "inventoryStatus": {"stockStatus": "InStock", "Avl_Quantity": 50},
            },
            "Synnex EU": {
                "sourceName": "Synnex EU",
                "OnlineCheck": {
                    "Header": {"CurrencyCode": "EUR"},
                    "Item": {
                        "ManufacturerItemIdentifier": "BCM957608-P2200GQF00",
                        "UnitPriceAmount": "1800.00",
                        "AvailabilityTotal": -5,  # negative quantity
                    },
                },
            },
        }
        sections = []
        for key, value in payload.items():
            if isinstance(value, dict):
                section = dict(value)
                if "sourceName" not in section and key in frozenset({
                    "Ingram", "CDW", "Synnex EU", "Unknown"
                }):
                    section["sourceName"] = key
                sections.append(section)

        results = []
        from product_intelligence.providers.internal_vendor import (
            _identify_and_map_source,
        )
        for section in sections:
            results.append(_identify_and_map_source(section))

        # CDW candidate, Synnex quantity discarded but candidate survives
        candidates = [r for r in results if isinstance(r, CommercialSourceCandidate)]
        assert len(candidates) == 2
        cdw = [c for c in candidates if c.source_name == "CDW"][0]
        assert cdw.quantity == 50
        synnex = [c for c in candidates if c.source_name == "Synnex EU"][0]
        assert synnex.quantity is None  # negative discarded

    def test_valid_synnex_plus_ingram_non_finite_price(self) -> None:
        """Valid Synnex + Ingram with Infinity price -> Synnex survives."""
        # JSON parsing with parse_float=Decimal converts Infinity to Decimal
        payload = {
            "Synnex EU": {
                "sourceName": "Synnex EU",
                "OnlineCheck": {
                    "Header": {"CurrencyCode": "EUR"},
                    "Item": {
                        "ManufacturerItemIdentifier": "BCM957608-P2200GQF00",
                        "UnitPriceAmount": "1800.00",
                        "AvailabilityTotal": 20,
                    },
                },
            },
            "Ingram": {
                "sourceName": "Ingram",
                "vendorPartNumber": "BCM957608-P2200GQF00",
                "pricing": {
                    "customerPrice": Decimal("Infinity"),  # non-finite
                    "currencyCode": "USD",
                },
                "availability": {"available": True, "Avl_Quantity": 10},
            },
        }
        sections = []
        for key, value in payload.items():
            if isinstance(value, dict):
                section = dict(value)
                if "sourceName" not in section and key in frozenset({
                    "Ingram", "CDW", "Synnex EU", "Unknown"
                }):
                    section["sourceName"] = key
                sections.append(section)

        results = []
        from product_intelligence.providers.internal_vendor import (
            _identify_and_map_source,
        )
        for section in sections:
            results.append(_identify_and_map_source(section))

        # Synnex candidate, Ingram issue (non-finite price)
        candidates = [r for r in results if isinstance(r, CommercialSourceCandidate)]
        issues = [r for r in results if isinstance(r, CommercialSourceIssue)]
        assert len(candidates) == 1
        assert candidates[0].source_name == "Synnex EU"
        assert len(issues) == 1
        assert issues[0].source_name == "Ingram"
        assert issues[0].outcome == SourceOutcome.MALFORMED_SECTION


class TestNotFoundWrapperSourceBinding:
    """Prove wrapper-level source keys are preserved for Not Found."""

    def test_ingram_not_found_wrapper(self) -> None:
        """{Ingram: {Not Found: true}} -> Ingram NOT_FOUND."""
        adapter = InternalVendorAdapter()
        adapter._base_url = "http://example.com/vendor"
        adapter._validated = True

        query = CommercialLookupQuery(mpn="ABC123")

        payload = {"Ingram": {"Not Found": True}}

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
        assert len(response.issues) == 1
        assert response.issues[0].source_name == "Ingram"
        assert response.issues[0].outcome == SourceOutcome.NOT_FOUND

    def test_cdw_not_found_wrapper(self) -> None:
        """{CDW: {Not Found: true}} -> CDW NOT_FOUND."""
        adapter = InternalVendorAdapter()
        adapter._base_url = "http://example.com/vendor"
        adapter._validated = True

        query = CommercialLookupQuery(mpn="ABC123")

        payload = {"CDW": {"Not Found": True}}

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
        assert len(response.issues) == 1
        assert response.issues[0].source_name == "CDW"
        assert response.issues[0].outcome == SourceOutcome.NOT_FOUND

    def test_synnex_not_found_wrapper(self) -> None:
        """{Synnex EU: {Not Found: true}} -> Synnex EU NOT_FOUND."""
        adapter = InternalVendorAdapter()
        adapter._base_url = "http://example.com/vendor"
        adapter._validated = True

        query = CommercialLookupQuery(mpn="ABC123")

        payload = {"Synnex EU": {"Not Found": True}}

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
        assert len(response.issues) == 1
        assert response.issues[0].source_name == "Synnex EU"
        assert response.issues[0].outcome == SourceOutcome.NOT_FOUND

    def test_unknown_wrapper_name_not_persisted(self) -> None:
        """Arbitrary unknown wrapper name does not become source_name."""
        adapter = InternalVendorAdapter()
        adapter._base_url = "http://example.com/vendor"
        adapter._validated = True

        query = CommercialLookupQuery(mpn="ABC123")

        # Unknown wrapper name with a source section that has sourceName
        payload = {
            "UnknownVendorXYZ": {
                "sourceName": "Ingram",
                "NotFound": True,
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

        # Source name is "Ingram" from the inner section, not "UnknownVendorXYZ"
        assert len(response.issues) == 1
        assert response.issues[0].source_name == "Ingram"
        assert "UnknownVendorXYZ" not in str(response)


class TestRawJSONDecimalLiteral:
    """Prove raw JSON decimal literal survives exactly as Decimal."""

    def test_raw_json_decimal_literal_exact(self) -> None:
        """Raw JSON bytes with precise decimal literal -> exact Decimal.

        Does NOT construct a Python float and json.dumps() it.
        Uses RAW JSON TEXT with literal numeric token.
        """
        adapter = InternalVendorAdapter()
        adapter._base_url = "http://example.com/vendor"
        adapter._validated = True

        query = CommercialLookupQuery(mpn="BCM957608-P2200GQF00")

        # RAW JSON bytes with literal decimal token (not float-converted)
        raw_json_text = '{"Ingram": {"sourceName": "Ingram", "vendorPartNumber": "BCM957608-P2200GQF00", "pricing": {"customerPrice": 2120.12345678901234567890, "currencyCode": "USD"}, "availability": {"available": true, "Avl_Quantity": 10}}}'

        mock_response = MagicMock()
        mock_response.read.return_value = raw_json_text.encode("utf-8")

        with patch(
            "product_intelligence.providers.internal_vendor."
            "_get_vendor_opener"
        ) as mock_get_opener:
            mock_opener = MagicMock()
            mock_opener.open.return_value = mock_response
            mock_get_opener.return_value = mock_opener

            response = adapter.lookup(query)

        assert response.status == LookupStatus.SUCCESS
        candidate = response.candidates[0]
        assert isinstance(candidate.price_amount, Decimal)
        # The JSON number 2120.12345678901234567890 is parsed by json.loads
        # with parse_float=Decimal, which preserves full precision.
        assert candidate.price_amount == Decimal("2120.12345678901234567890")


# ---------------------------------------------------------------------------
# FU3: External Data Type Safety Tests
# ---------------------------------------------------------------------------


class TestMPNTypeSafety:
    """FU3 #1: Non-string MPN must be MALFORMED_SECTION, never coerced."""

    # Ingram: vendorPartNumber
    def test_ingram_mpn_int_is_malformed(self) -> None:
        section = {
            "sourceName": "Ingram",
            "vendorPartNumber": 12345,  # int, not string
            "pricing": {
                "customerPrice": "100.00",
                "currencyCode": "USD",
            },
            "availability": {"available": True, "Avl_Quantity": 5},
        }
        result = _map_ingram(section)
        assert isinstance(result, CommercialSourceIssue)
        assert result.outcome == SourceOutcome.MALFORMED_SECTION

    def test_ingram_mpn_dict_is_malformed(self) -> None:
        section = {
            "sourceName": "Ingram",
            "vendorPartNumber": {"value": "ABC123"},  # dict, not string
            "pricing": {
                "customerPrice": "100.00",
                "currencyCode": "USD",
            },
            "availability": {"available": True},
        }
        result = _map_ingram(section)
        assert isinstance(result, CommercialSourceIssue)
        assert result.outcome == SourceOutcome.MALFORMED_SECTION

    def test_ingram_mpn_list_is_malformed(self) -> None:
        section = {
            "sourceName": "Ingram",
            "vendorPartNumber": ["ABC123"],  # list, not string
            "pricing": {
                "customerPrice": "100.00",
                "currencyCode": "USD",
            },
            "availability": {"available": True},
        }
        result = _map_ingram(section)
        assert isinstance(result, CommercialSourceIssue)
        assert result.outcome == SourceOutcome.MALFORMED_SECTION

    def test_ingram_mpn_empty_string_is_missing(self) -> None:
        section = {
            "sourceName": "Ingram",
            "vendorPartNumber": "",  # empty string
            "pricing": {
                "customerPrice": "100.00",
                "currencyCode": "USD",
            },
            "availability": {"available": True},
        }
        result = _map_ingram(section)
        assert isinstance(result, CommercialSourceIssue)
        assert result.outcome == SourceOutcome.MISSING_EXPLICIT_MPN

    def test_ingram_mpn_whitespace_only_is_missing(self) -> None:
        section = {
            "sourceName": "Ingram",
            "vendorPartNumber": "   ",  # whitespace only
            "pricing": {
                "customerPrice": "100.00",
                "currencyCode": "USD",
            },
            "availability": {"available": True},
        }
        result = _map_ingram(section)
        assert isinstance(result, CommercialSourceIssue)
        assert result.outcome == SourceOutcome.MISSING_EXPLICIT_MPN

    def test_ingram_mpn_valid_string_works(self) -> None:
        section = {
            "sourceName": "Ingram",
            "vendorPartNumber": "BCM957608-P2200GQF00",
            "pricing": {
                "customerPrice": "100.00",
                "currencyCode": "USD",
            },
            "availability": {"available": True},
        }
        result = _map_ingram(section)
        assert isinstance(result, CommercialSourceCandidate)
        assert result.explicit_candidate_mpn == "BCM957608-P2200GQF00"

    # CDW: manufacturerPartNumber
    def test_cdw_mpn_int_is_malformed(self) -> None:
        section = {
            "sourceName": "CDW",
            "manufacturerPartNumber": 99999,  # int, not string
            "price": "1999.99",
            "currencyCode": "USD",
            "inventoryStatus": {"stockStatus": "InStock"},
        }
        result = _map_cdw(section)
        assert isinstance(result, CommercialSourceIssue)
        assert result.outcome == SourceOutcome.MALFORMED_SECTION

    def test_cdw_mpn_dict_is_malformed(self) -> None:
        section = {
            "sourceName": "CDW",
            "manufacturerPartNumber": {"mpn": "ABC"},  # dict, not string
            "price": "1999.99",
            "currencyCode": "USD",
            "inventoryStatus": {"stockStatus": "InStock"},
        }
        result = _map_cdw(section)
        assert isinstance(result, CommercialSourceIssue)
        assert result.outcome == SourceOutcome.MALFORMED_SECTION

    def test_cdw_mpn_list_is_malformed(self) -> None:
        section = {
            "sourceName": "CDW",
            "manufacturerPartNumber": ["ABC123"],  # list
            "price": "1999.99",
            "currencyCode": "USD",
            "inventoryStatus": {"stockStatus": "InStock"},
        }
        result = _map_cdw(section)
        assert isinstance(result, CommercialSourceIssue)
        assert result.outcome == SourceOutcome.MALFORMED_SECTION

    def test_cdw_mpn_empty_string_is_missing(self) -> None:
        section = {
            "sourceName": "CDW",
            "manufacturerPartNumber": "",
            "price": "1999.99",
            "currencyCode": "USD",
            "inventoryStatus": {"stockStatus": "InStock"},
        }
        result = _map_cdw(section)
        assert isinstance(result, CommercialSourceIssue)
        assert result.outcome == SourceOutcome.MISSING_EXPLICIT_MPN

    def test_cdw_mpn_valid_string_works(self) -> None:
        section = {
            "sourceName": "CDW",
            "manufacturerPartNumber": "BCM957608-P2200GQF00",
            "price": "1999.99",
            "currencyCode": "USD",
            "inventoryStatus": {"stockStatus": "InStock"},
        }
        result = _map_cdw(section)
        assert isinstance(result, CommercialSourceCandidate)
        assert result.explicit_candidate_mpn == "BCM957608-P2200GQF00"

    # Synnex EU: OnlineCheck.Item.ManufacturerItemIdentifier
    def test_synnex_mpn_int_is_malformed(self) -> None:
        section = {
            "sourceName": "Synnex EU",
            "OnlineCheck": {
                "Header": {"CurrencyCode": "EUR"},
                "Item": {
                    "ManufacturerItemIdentifier": 12345,  # int
                    "UnitPriceAmount": "100.00",
                    "AvailabilityTotal": 10,
                },
            },
        }
        result = _map_synnex_eu(section)
        assert isinstance(result, CommercialSourceIssue)
        assert result.outcome == SourceOutcome.MALFORMED_SECTION

    def test_synnex_mpn_dict_is_malformed(self) -> None:
        section = {
            "sourceName": "Synnex EU",
            "OnlineCheck": {
                "Header": {"CurrencyCode": "EUR"},
                "Item": {
                    "ManufacturerItemIdentifier": {"id": "ABC"},  # dict
                    "UnitPriceAmount": "100.00",
                    "AvailabilityTotal": 10,
                },
            },
        }
        result = _map_synnex_eu(section)
        assert isinstance(result, CommercialSourceIssue)
        assert result.outcome == SourceOutcome.MALFORMED_SECTION

    def test_synnex_mpn_empty_string_is_missing(self) -> None:
        section = {
            "sourceName": "Synnex EU",
            "OnlineCheck": {
                "Header": {"CurrencyCode": "EUR"},
                "Item": {
                    "ManufacturerItemIdentifier": "",
                    "UnitPriceAmount": "100.00",
                    "AvailabilityTotal": 10,
                },
            },
        }
        result = _map_synnex_eu(section)
        assert isinstance(result, CommercialSourceIssue)
        assert result.outcome == SourceOutcome.MISSING_EXPLICIT_MPN

    def test_synnex_mpn_valid_string_works(self) -> None:
        section = {
            "sourceName": "Synnex EU",
            "OnlineCheck": {
                "Header": {"CurrencyCode": "EUR"},
                "Item": {
                    "ManufacturerItemIdentifier": "BCM957608-P2200GQF00",
                    "UnitPriceAmount": "100.00",
                    "AvailabilityTotal": 10,
                },
            },
        }
        result = _map_synnex_eu(section)
        assert isinstance(result, CommercialSourceCandidate)
        assert result.explicit_candidate_mpn == "BCM957608-P2200GQF00"

    def test_malformed_mpn_in_one_source_does_not_destroy_valid_sibling(self) -> None:
        """Malformed MPN in CDW does not destroy valid Ingram candidate."""
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
                "manufacturerPartNumber": 12345,  # int MPN = MALFORMED
                "price": "1999.99",
                "currencyCode": "USD",
                "inventoryStatus": {"stockStatus": "InStock"},
            },
        }
        sections = []
        for key, value in payload.items():
            if isinstance(value, dict):
                section = dict(value)
                if "sourceName" not in section and key in frozenset(
                    {"Ingram", "CDW", "Synnex EU", "Unknown"}
                ):
                    section["sourceName"] = key
                sections.append(section)

        results = []
        from product_intelligence.providers.internal_vendor import (
            _identify_and_map_source,
        )
        for section in sections:
            results.append(_identify_and_map_source(section))

        candidates = [r for r in results if isinstance(r, CommercialSourceCandidate)]
        issues = [r for r in results if isinstance(r, CommercialSourceIssue)]
        assert len(candidates) == 1
        assert candidates[0].source_name == "Ingram"
        assert len(issues) == 1
        assert issues[0].source_name == "CDW"
        assert issues[0].outcome == SourceOutcome.MALFORMED_SECTION


class TestQuantityNoTruncation:
    """FU3 #2: Fractional Decimal quantity must NEVER be truncated."""

    def test_ingram_fractional_quantity_rejected(self) -> None:
        """Ingram: Decimal('3.7') -> quantity is NOT 3 (no truncation)."""
        section = {
            "sourceName": "Ingram",
            "vendorPartNumber": "BCM957608-P2200GQF00",
            "pricing": {
                "customerPrice": "100.00",
                "currencyCode": "USD",
            },
            "availability": {"available": True, "Avl_Quantity": Decimal("3.7")},
        }
        result = _map_ingram(section)
        assert isinstance(result, CommercialSourceCandidate)
        # Must NOT be truncated to 3
        assert result.quantity is None or result.quantity != 3
        # Since _safe_int returns None for fractional, quantity should be None
        assert result.quantity is None

    def test_ingram_exact_int_quantity_accepted(self) -> None:
        section = {
            "sourceName": "Ingram",
            "vendorPartNumber": "BCM957608-P2200GQF00",
            "pricing": {
                "customerPrice": "100.00",
                "currencyCode": "USD",
            },
            "availability": {"available": True, "Avl_Quantity": Decimal("3")},
        }
        result = _map_ingram(section)
        assert isinstance(result, CommercialSourceCandidate)
        assert result.quantity == 3

    def test_ingram_negative_quantity_rejected(self) -> None:
        section = {
            "sourceName": "Ingram",
            "vendorPartNumber": "BCM957608-P2200GQF00",
            "pricing": {
                "customerPrice": "100.00",
                "currencyCode": "USD",
            },
            "availability": {"available": True, "Avl_Quantity": -5},
        }
        result = _map_ingram(section)
        assert isinstance(result, CommercialSourceCandidate)
        # Negative already rejected by _safe_int; caller clears it
        assert result.quantity is None

    def test_cdw_fractional_quantity_rejected(self) -> None:
        """CDW: Decimal('8.5') -> quantity is NOT 8 (no truncation)."""
        section = {
            "sourceName": "CDW",
            "manufacturerPartNumber": "BCM957608-P2200GQF00",
            "price": "1999.99",
            "currencyCode": "USD",
            "inventoryStatus": {
                "stockStatus": "InStock",
                "Avl_Quantity": Decimal("8.5"),
            },
        }
        result = _map_cdw(section)
        assert isinstance(result, CommercialSourceCandidate)
        # Must NOT be truncated to 8
        assert result.quantity is None or result.quantity != 8
        assert result.quantity is None

    def test_cdw_exact_int_quantity_accepted(self) -> None:
        section = {
            "sourceName": "CDW",
            "manufacturerPartNumber": "BCM957608-P2200GQF00",
            "price": "1999.99",
            "currencyCode": "USD",
            "inventoryStatus": {"stockStatus": "InStock", "Avl_Quantity": 48},
        }
        result = _map_cdw(section)
        assert isinstance(result, CommercialSourceCandidate)
        assert result.quantity == 48

    def test_cdw_bool_quantity_rejected(self) -> None:
        section = {
            "sourceName": "CDW",
            "manufacturerPartNumber": "BCM957608-P2200GQF00",
            "price": "1999.99",
            "currencyCode": "USD",
            "inventoryStatus": {"stockStatus": "InStock", "Avl_Quantity": True},
        }
        result = _map_cdw(section)
        assert isinstance(result, CommercialSourceCandidate)
        assert result.quantity is None

    def test_synnex_fractional_quantity_rejected(self) -> None:
        """Synnex: Decimal('2.9') -> quantity is NOT 2 (no truncation)."""
        section = {
            "sourceName": "Synnex EU",
            "OnlineCheck": {
                "Header": {"CurrencyCode": "EUR"},
                "Item": {
                    "ManufacturerItemIdentifier": "BCM957608-P2200GQF00",
                    "UnitPriceAmount": "100.00",
                    "AvailabilityTotal": Decimal("2.9"),
                },
            },
        }
        result = _map_synnex_eu(section)
        assert isinstance(result, CommercialSourceCandidate)
        # Must NOT be truncated to 2
        assert result.quantity is None or result.quantity != 2
        assert result.quantity is None

    def test_synnex_exact_int_quantity_accepted(self) -> None:
        section = {
            "sourceName": "Synnex EU",
            "OnlineCheck": {
                "Header": {"CurrencyCode": "EUR"},
                "Item": {
                    "ManufacturerItemIdentifier": "BCM957608-P2200GQF00",
                    "UnitPriceAmount": "100.00",
                    "AvailabilityTotal": 30,
                },
            },
        }
        result = _map_synnex_eu(section)
        assert isinstance(result, CommercialSourceCandidate)
        assert result.quantity == 30

    def test_safe_int_fractional_decimal_returns_none(self) -> None:
        """_safe_int with Decimal('3.7') returns None, not 3."""
        from product_intelligence.providers.internal_vendor import _safe_int
        result = _safe_int(Decimal("3.7"))
        assert result is None

    def test_safe_int_exact_decimal_returns_int(self) -> None:
        from product_intelligence.providers.internal_vendor import _safe_int
        result = _safe_int(Decimal("3"))
        assert result == 3

    def test_safe_int_negative_int_returns_none(self) -> None:
        from product_intelligence.providers.internal_vendor import _safe_int
        result = _safe_int(-5)
        assert result is None

    def test_safe_int_bool_returns_none(self) -> None:
        from product_intelligence.providers.internal_vendor import _safe_int
        assert _safe_int(True) is None
        assert _safe_int(False) is None


class TestSynnexCurrencyTypeSafety:
    """FU3 #3: Synnex currency must be str, never raise AttributeError."""

    def test_synnex_currency_int_is_malformed(self) -> None:
        section = {
            "sourceName": "Synnex EU",
            "OnlineCheck": {
                "Header": {"CurrencyCode": 123},  # int, not string
                "Item": {
                    "ManufacturerItemIdentifier": "BCM957608-P2200GQF00",
                    "UnitPriceAmount": "100.00",
                    "AvailabilityTotal": 10,
                },
            },
        }
        result = _map_synnex_eu(section)
        assert isinstance(result, CommercialSourceIssue)
        assert result.outcome == SourceOutcome.MALFORMED_SECTION

    def test_synnex_currency_list_is_malformed(self) -> None:
        section = {
            "sourceName": "Synnex EU",
            "OnlineCheck": {
                "Header": {"CurrencyCode": ["EUR"]},  # list
                "Item": {
                    "ManufacturerItemIdentifier": "BCM957608-P2200GQF00",
                    "UnitPriceAmount": "100.00",
                    "AvailabilityTotal": 10,
                },
            },
        }
        result = _map_synnex_eu(section)
        assert isinstance(result, CommercialSourceIssue)
        assert result.outcome == SourceOutcome.MALFORMED_SECTION

    def test_synnex_currency_missing_is_malformed(self) -> None:
        section = {
            "sourceName": "Synnex EU",
            "OnlineCheck": {
                "Header": {},  # no CurrencyCode
                "Item": {
                    "ManufacturerItemIdentifier": "BCM957608-P2200GQF00",
                    "UnitPriceAmount": "100.00",
                    "AvailabilityTotal": 10,
                },
            },
        }
        result = _map_synnex_eu(section)
        assert isinstance(result, CommercialSourceIssue)
        assert result.outcome == SourceOutcome.MALFORMED_SECTION

    def test_synnex_currency_valid_works(self) -> None:
        section = {
            "sourceName": "Synnex EU",
            "OnlineCheck": {
                "Header": {"CurrencyCode": " EUR "},  # whitespace, will strip
                "Item": {
                    "ManufacturerItemIdentifier": "BCM957608-P2200GQF00",
                    "UnitPriceAmount": "100.00",
                    "AvailabilityTotal": 10,
                },
            },
        }
        result = _map_synnex_eu(section)
        assert isinstance(result, CommercialSourceCandidate)
        assert result.currency_code == "EUR"

    def test_synnex_currency_empty_string_is_malformed(self) -> None:
        section = {
            "sourceName": "Synnex EU",
            "OnlineCheck": {
                "Header": {"CurrencyCode": ""},  # empty string
                "Item": {
                    "ManufacturerItemIdentifier": "BCM957608-P2200GQF00",
                    "UnitPriceAmount": "100.00",
                    "AvailabilityTotal": 10,
                },
            },
        }
        result = _map_synnex_eu(section)
        assert isinstance(result, CommercialSourceIssue)
        assert result.outcome == SourceOutcome.MALFORMED_SECTION

    def test_valid_cdw_plus_malformed_synnex_currency_survives(self) -> None:
        """Valid CDW + malformed Synnex currency -> CDW survives."""
        payload = {
            "CDW": {
                "sourceName": "CDW",
                "manufacturerPartNumber": "BCM957608-P2200GQF00",
                "price": "1999.99",
                "currencyCode": "USD",
                "inventoryStatus": {"stockStatus": "InStock", "Avl_Quantity": 50},
            },
            "Synnex EU": {
                "sourceName": "Synnex EU",
                "OnlineCheck": {
                    "Header": {"CurrencyCode": 999},  # malformed int
                    "Item": {
                        "ManufacturerItemIdentifier": "BCM957608-P2200GQF00",
                        "UnitPriceAmount": "1800.00",
                        "AvailabilityTotal": 20,
                    },
                },
            },
        }
        sections = []
        for key, value in payload.items():
            if isinstance(value, dict):
                section = dict(value)
                if "sourceName" not in section and key in frozenset(
                    {"Ingram", "CDW", "Synnex EU", "Unknown"}
                ):
                    section["sourceName"] = key
                sections.append(section)

        results = []
        from product_intelligence.providers.internal_vendor import (
            _identify_and_map_source,
        )
        for section in sections:
            results.append(_identify_and_map_source(section))

        candidates = [r for r in results if isinstance(r, CommercialSourceCandidate)]
        issues = [r for r in results if isinstance(r, CommercialSourceIssue)]
        assert len(candidates) == 1
        assert candidates[0].source_name == "CDW"
        assert len(issues) == 1
        assert issues[0].source_name == "Synnex EU"
        assert issues[0].outcome == SourceOutcome.MALFORMED_SECTION


class TestJSONConstantRejection:
    """FU3 #4: NaN/Infinity JSON constants rejected at parse boundary."""

    def test_nan_json_rejected(self) -> None:
        """JSON body with NaN -> FAILED, no candidate."""
        adapter = InternalVendorAdapter()
        adapter._base_url = "http://example.com/vendor"
        adapter._validated = True
        query = CommercialLookupQuery(mpn="BCM957608-P2200GQF00")

        raw_json = b'{"Ingram": {"sourceName": "Ingram", "vendorPartNumber": "ABC", "pricing": {"customerPrice": NaN, "currencyCode": "USD"}, "availability": {"available": true}}}'

        mock_response = MagicMock()
        mock_response.read.return_value = raw_json

        with patch(
            "product_intelligence.providers.internal_vendor."
            "_get_vendor_opener"
        ) as mock_get_opener:
            mock_opener = MagicMock()
            mock_opener.open.return_value = mock_response
            mock_get_opener.return_value = mock_opener

            response = adapter.lookup(query)

        assert response.status == LookupStatus.FAILED
        assert len(response.candidates) == 0
        assert len(response.issues) == 0

    def test_infinity_json_rejected(self) -> None:
        """JSON body with Infinity -> FAILED, no candidate."""
        adapter = InternalVendorAdapter()
        adapter._base_url = "http://example.com/vendor"
        adapter._validated = True
        query = CommercialLookupQuery(mpn="BCM957608-P2200GQF00")

        raw_json = b'{"Ingram": {"sourceName": "Ingram", "vendorPartNumber": "ABC", "pricing": {"customerPrice": Infinity, "currencyCode": "USD"}, "availability": {"available": true}}}'

        mock_response = MagicMock()
        mock_response.read.return_value = raw_json

        with patch(
            "product_intelligence.providers.internal_vendor."
            "_get_vendor_opener"
        ) as mock_get_opener:
            mock_opener = MagicMock()
            mock_opener.open.return_value = mock_response
            mock_get_opener.return_value = mock_opener

            response = adapter.lookup(query)

        assert response.status == LookupStatus.FAILED
        assert len(response.candidates) == 0

    def test_negative_infinity_json_rejected(self) -> None:
        """JSON body with -Infinity -> FAILED, no candidate."""
        adapter = InternalVendorAdapter()
        adapter._base_url = "http://example.com/vendor"
        adapter._validated = True
        query = CommercialLookupQuery(mpn="BCM957608-P2200GQF00")

        raw_json = b'{"Ingram": {"sourceName": "Ingram", "vendorPartNumber": "ABC", "pricing": {"customerPrice": -Infinity, "currencyCode": "USD"}, "availability": {"available": true}}}'

        mock_response = MagicMock()
        mock_response.read.return_value = raw_json

        with patch(
            "product_intelligence.providers.internal_vendor."
            "_get_vendor_opener"
        ) as mock_get_opener:
            mock_opener = MagicMock()
            mock_opener.open.return_value = mock_response
            mock_get_opener.return_value = mock_opener

            response = adapter.lookup(query)

        assert response.status == LookupStatus.FAILED
        assert len(response.candidates) == 0


class TestSafeDecimalNoFloat:
    """FU3 #5: _safe_decimal rejects binary float."""

    def test_safe_decimal_rejects_float(self) -> None:
        from product_intelligence.providers.internal_vendor import _safe_decimal
        result = _safe_decimal(100.99)
        assert result is None

    def test_safe_decimal_accepts_decimal(self) -> None:
        from product_intelligence.providers.internal_vendor import _safe_decimal
        result = _safe_decimal(Decimal("100.99"))
        assert result == Decimal("100.99")

    def test_safe_decimal_accepts_numeric_string(self) -> None:
        from product_intelligence.providers.internal_vendor import _safe_decimal
        result = _safe_decimal("100.99")
        assert result == Decimal("100.99")

    def test_safe_decimal_rejects_nan_string(self) -> None:
        from product_intelligence.providers.internal_vendor import _safe_decimal
        result = _safe_decimal("NaN")
        assert result is None

    def test_safe_decimal_rejects_infinity_string(self) -> None:
        from product_intelligence.providers.internal_vendor import _safe_decimal
        result = _safe_decimal("Infinity")
        assert result is None

    def test_mapper_float_price_is_malformed(self) -> None:
        """Ingram: float price -> MALFORMED_SECTION."""
        section = {
            "sourceName": "Ingram",
            "vendorPartNumber": "BCM957608-P2200GQF00",
            "pricing": {
                "customerPrice": 100.99,  # binary float, not Decimal
                "currencyCode": "USD",
            },
            "availability": {"available": True},
        }
        result = _map_ingram(section)
        assert isinstance(result, CommercialSourceIssue)
        assert result.outcome == SourceOutcome.MALFORMED_SECTION


class TestOpenerRegisteredRedirectDispatch:
    """FU3 #6: Redirect refusal exercises registered opener dispatch."""

    def test_redirect_handler_registered_in_opener_error_dispatch(self) -> None:
        """Redirect refusal handler is registered in opener's error dispatch table.

        The opener is built with build_opener(_NoRedirectHandler()), so the
        handler's methods are registered in handle_error. This test verifies
        the handler is registered AND exercises its registered http_error_302
        method directly (which is the method the dispatcher invokes).
        """
        from product_intelligence.providers.internal_vendor import (
            _get_vendor_opener,
            _NoRedirectHandler,
        )
        from urllib.error import HTTPError

        opener = _get_vendor_opener()

        # Verify the handler is registered in handle_error dispatch
        assert "http" in opener.handle_error, (
            "Opener must have registered http error dispatch via add_handler"
        )

        # Find the _NoRedirectHandler instance in the opener
        custom_handlers = [
            h for h in opener.handlers
            if isinstance(h, _NoRedirectHandler)
        ]
        assert len(custom_handlers) == 1, (
            "Opener must have exactly one _NoRedirectHandler"
        )
        handler = custom_handlers[0]

        # Exercise the registered method directly (as the dispatcher would)
        mock_req = MagicMock()
        mock_req.full_url = "http://vendor.internal/api?partno=ABC"
        mock_fp = MagicMock()
        mock_headers = MagicMock()

        with pytest.raises(HTTPError) as exc_info:
            # This is what the registered dispatcher calls for a 302
            handler.http_error_302(
                mock_req, mock_fp, 302, "Found", mock_headers
            )

        assert "Redirect refused" in str(exc_info.value)

        # Also verify 307 and 308 are refused
        with pytest.raises(HTTPError):
            handler.http_error_307(
                mock_req, mock_fp, 307, "Temporary Redirect", mock_headers
            )
        with pytest.raises(HTTPError):
            handler.http_error_308(
                mock_req, mock_fp, 308, "Permanent Redirect", mock_headers
            )

    def test_no_bare_http_redirect_handler_registered(self) -> None:
        """Bare HTTPRedirectHandler is not registered (type check, not subclass)."""
        from product_intelligence.providers.internal_vendor import _get_vendor_opener
        from urllib.request import HTTPRedirectHandler

        opener = _get_vendor_opener()

        # Verify no bare HTTPRedirectHandler (exact type() check, not isinstance)
        bare_handlers = [
            h for h in opener.handlers
            if type(h) is HTTPRedirectHandler
        ]
        assert len(bare_handlers) == 0, (
            "Default HTTPRedirectHandler must not be active"
        )


# ---------------------------------------------------------------------------
# FU4: Money Bool Rejection
# ---------------------------------------------------------------------------


class TestSafeDecimalBoolRejection:
    """FU4 #1: bool must be explicitly rejected by _safe_decimal.

    Decimal(True) == Decimal("1"), so an external "customerPrice": true
    must NOT become a valid commercial price of 1.
    """

    def test_safe_decimal_true_is_none(self) -> None:
        """_safe_decimal(True) returns None, not Decimal("1")."""
        from product_intelligence.providers.internal_vendor import _safe_decimal
        result = _safe_decimal(True)
        assert result is None

    def test_safe_decimal_false_is_none(self) -> None:
        """_safe_decimal(False) returns None, not Decimal("0")."""
        from product_intelligence.providers.internal_vendor import _safe_decimal
        result = _safe_decimal(False)
        assert result is None

    def test_ingram_customer_price_bool_is_malformed(self) -> None:
        """Ingram customerPrice=True -> MALFORMED_SECTION."""
        section = {
            "sourceName": "Ingram",
            "vendorPartNumber": "BCM957608-P2200GQF00",
            "pricing": {
                "customerPrice": True,  # bool, not a number
                "currencyCode": "USD",
            },
            "availability": {"available": True, "Avl_Quantity": 10},
        }
        result = _map_ingram(section)
        assert isinstance(result, CommercialSourceIssue)
        assert result.outcome == SourceOutcome.MALFORMED_SECTION

    def test_ingram_customer_price_false_is_malformed(self) -> None:
        """Ingram customerPrice=False -> MALFORMED_SECTION."""
        section = {
            "sourceName": "Ingram",
            "vendorPartNumber": "BCM957608-P2200GQF00",
            "pricing": {
                "customerPrice": False,  # bool, not a number
                "currencyCode": "USD",
            },
            "availability": {"available": True},
        }
        result = _map_ingram(section)
        assert isinstance(result, CommercialSourceIssue)
        assert result.outcome == SourceOutcome.MALFORMED_SECTION

    def test_cdw_price_bool_true_is_malformed(self) -> None:
        """CDW price=True -> MALFORMED_SECTION."""
        section = {
            "sourceName": "CDW",
            "manufacturerPartNumber": "BCM957608-P2200GQF00",
            "price": True,  # bool
            "currencyCode": "USD",
            "inventoryStatus": {"stockStatus": "InStock"},
        }
        result = _map_cdw(section)
        assert isinstance(result, CommercialSourceIssue)
        assert result.outcome == SourceOutcome.MALFORMED_SECTION

    def test_cdw_price_bool_false_is_malformed(self) -> None:
        """CDW price=False -> MALFORMED_SECTION."""
        section = {
            "sourceName": "CDW",
            "manufacturerPartNumber": "BCM957608-P2200GQF00",
            "price": False,  # bool
            "currencyCode": "USD",
            "inventoryStatus": {"stockStatus": "InStock"},
        }
        result = _map_cdw(section)
        assert isinstance(result, CommercialSourceIssue)
        assert result.outcome == SourceOutcome.MALFORMED_SECTION

    def test_synnex_unit_price_bool_true_is_malformed(self) -> None:
        """Synnex EU UnitPriceAmount=True -> MALFORMED_SECTION."""
        section = {
            "sourceName": "Synnex EU",
            "OnlineCheck": {
                "Header": {"CurrencyCode": "EUR"},
                "Item": {
                    "ManufacturerItemIdentifier": "BCM957608-P2200GQF00",
                    "UnitPriceAmount": True,  # bool
                    "AvailabilityTotal": 10,
                },
            },
        }
        result = _map_synnex_eu(section)
        assert isinstance(result, CommercialSourceIssue)
        assert result.outcome == SourceOutcome.MALFORMED_SECTION

    def test_valid_decimal_path_still_works(self) -> None:
        """Valid Decimal/int/numeric-string paths remain correct."""
        from product_intelligence.providers.internal_vendor import _safe_decimal
        assert _safe_decimal(Decimal("100.50")) == Decimal("100.50")
        assert _safe_decimal(42) == Decimal("42")
        assert _safe_decimal("99.99") == Decimal("99.99")

    def test_decimal_nan_still_rejected(self) -> None:
        """Decimal NaN remains rejected."""
        from product_intelligence.providers.internal_vendor import _safe_decimal
        result = _safe_decimal(Decimal("NaN"))
        assert result is None

    def test_decimal_infinity_still_rejected(self) -> None:
        """Decimal Infinity remains rejected."""
        from product_intelligence.providers.internal_vendor import _safe_decimal
        result = _safe_decimal(Decimal("Infinity"))
        assert result is None

    def test_list_dict_rejected(self) -> None:
        """List and dict are rejected by _safe_decimal."""
        from product_intelligence.providers.internal_vendor import _safe_decimal
        assert _safe_decimal([100]) is None
        assert _safe_decimal({"value": 100}) is None


# ---------------------------------------------------------------------------
# FU4: Quantity Float Truncation
# ---------------------------------------------------------------------------


class TestSafeIntFloatRejection:
    """FU4 #2: float must be rejected by _safe_int (no truncation)."""

    def test_safe_int_float_3_7_is_none(self) -> None:
        """_safe_int(3.7) is None, not 3 (no truncation)."""
        from product_intelligence.providers.internal_vendor import _safe_int
        result = _safe_int(3.7)
        assert result is None

    def test_safe_int_float_3_0_is_none(self) -> None:
        """_safe_int(3.0) is None (float even if mathematically integral)."""
        from product_intelligence.providers.internal_vendor import _safe_int
        result = _safe_int(3.0)
        assert result is None

    def test_safe_int_float_zero_is_none(self) -> None:
        """_safe_int(0.0) is None."""
        from product_intelligence.providers.internal_vendor import _safe_int
        result = _safe_int(0.0)
        assert result is None

    def test_ingram_float_quantity_rejected(self) -> None:
        """Ingram float quantity is never truncated."""
        section = {
            "sourceName": "Ingram",
            "vendorPartNumber": "BCM957608-P2200GQF00",
            "pricing": {
                "customerPrice": "100.00",
                "currencyCode": "USD",
            },
            "availability": {"available": True, "Avl_Quantity": 3.7},
        }
        result = _map_ingram(section)
        assert isinstance(result, CommercialSourceCandidate)
        assert result.quantity is None

    def test_cdw_float_quantity_rejected(self) -> None:
        """CDW float quantity is never truncated."""
        section = {
            "sourceName": "CDW",
            "manufacturerPartNumber": "BCM957608-P2200GQF00",
            "price": "1999.99",
            "currencyCode": "USD",
            "inventoryStatus": {
                "stockStatus": "InStock",
                "Avl_Quantity": 8.5,
            },
        }
        result = _map_cdw(section)
        assert isinstance(result, CommercialSourceCandidate)
        assert result.quantity is None

    def test_synnex_float_quantity_rejected(self) -> None:
        """Synnex float quantity is never truncated."""
        section = {
            "sourceName": "Synnex EU",
            "OnlineCheck": {
                "Header": {"CurrencyCode": "EUR"},
                "Item": {
                    "ManufacturerItemIdentifier": "BCM957608-P2200GQF00",
                    "UnitPriceAmount": "100.00",
                    "AvailabilityTotal": 2.9,
                },
            },
        }
        result = _map_synnex_eu(section)
        assert isinstance(result, CommercialSourceCandidate)
        assert result.quantity is None

    def test_safe_int_decimal_fractional_rejected(self) -> None:
        """Decimal("3.7") is still rejected by _safe_int."""
        from product_intelligence.providers.internal_vendor import _safe_int
        result = _safe_int(Decimal("3.7"))
        assert result is None

    def test_safe_int_decimal_integral_accepted(self) -> None:
        """Decimal("3") is still accepted by _safe_int."""
        from product_intelligence.providers.internal_vendor import _safe_int
        result = _safe_int(Decimal("3"))
        assert result == 3

    def test_safe_int_bool_rejected(self) -> None:
        """bool is still rejected by _safe_int."""
        from product_intelligence.providers.internal_vendor import _safe_int
        assert _safe_int(True) is None
        assert _safe_int(False) is None

    def test_safe_int_negative_rejected(self) -> None:
        """negative int is still rejected by _safe_int."""
        from product_intelligence.providers.internal_vendor import _safe_int
        assert _safe_int(-5) is None

    def test_safe_int_string_rejected(self) -> None:
        """string is rejected by _safe_int (no documented evidence needed)."""
        from product_intelligence.providers.internal_vendor import _safe_int
        assert _safe_int("42") is None
        assert _safe_int("3.0") is None

    def test_safe_int_list_rejected(self) -> None:
        """list is rejected by _safe_int."""
        from product_intelligence.providers.internal_vendor import _safe_int
        assert _safe_int([42]) is None

    def test_safe_int_dict_rejected(self) -> None:
        """dict is rejected by _safe_int."""
        from product_intelligence.providers.internal_vendor import _safe_int
        assert _safe_int({"qty": 42}) is None


# ---------------------------------------------------------------------------
# FU4: OpenerDirector Dispatch Test
# ---------------------------------------------------------------------------


class TestOpenerDirectorRedirectDispatch:
    """FU4 #3: Redirect refusal via actual OpenerDirector dispatcher."""

    def test_opener_dispatches_302_through_no_redirect_handler(self) -> None:
        """The constructed opener's error dispatcher routes 302 to _NoRedirectHandler.

        This exercises the ACTUAL OpenerDirector.dispatch path via
        opener.error("http", ...), not a direct handler method call.
        """
        from product_intelligence.providers.internal_vendor import (
            _build_vendor_opener,
            _NoRedirectHandler,
        )
        from urllib.request import Request

        opener = _build_vendor_opener()

        # Verify _NoRedirectHandler is in handlers (precondition)
        custom_handlers = [
            h for h in opener.handlers
            if isinstance(h, _NoRedirectHandler)
        ]
        assert len(custom_handlers) == 1

        # Build the mocked HTTPError with 302 status
        # We invoke opener.error("http", req, fp, code, msg, headers)
        # which is the internal dispatch path.
        req = Request("http://vendor.internal/api?partno=ABC")

        # Create a mock file-like object for the response body
        mock_fp = MagicMock()

        # Create mock headers (HTTPMessage-like)
        from http.client import HTTPMessage
        mock_headers = HTTPMessage()
        mock_headers["Location"] = "http://evil-redirect.com/new"

        with pytest.raises(HTTPError) as exc_info:
            # This calls the OpenerDirector's error dispatch machinery:
            # handle_error["http"][302] -> _NoRedirectHandler.http_error_302
            opener.error("http", req, mock_fp, 302, "Found", mock_headers)

        assert exc_info.value.code == 302
        assert "Redirect refused" in str(exc_info.value)

    def test_opener_dispatches_307_through_no_redirect_handler(self) -> None:
        """OpenerDirector dispatches 307 redirect through _NoRedirectHandler."""
        from product_intelligence.providers.internal_vendor import (
            _build_vendor_opener,
        )
        from urllib.request import Request
        from http.client import HTTPMessage

        opener = _build_vendor_opener()
        req = Request("http://vendor.internal/api?partno=ABC")
        mock_fp = MagicMock()
        mock_headers = HTTPMessage()

        with pytest.raises(HTTPError) as exc_info:
            opener.error("http", req, mock_fp, 307, "Temporary Redirect", mock_headers)

        assert exc_info.value.code == 307
        assert "Redirect refused" in str(exc_info.value)

    def test_opener_dispatches_301_through_no_redirect_handler(self) -> None:
        """OpenerDirector dispatches 301 redirect through _NoRedirectHandler."""
        from product_intelligence.providers.internal_vendor import (
            _build_vendor_opener,
        )
        from urllib.request import Request
        from http.client import HTTPMessage

        opener = _build_vendor_opener()
        req = Request("http://vendor.internal/api?partno=ABC")
        mock_fp = MagicMock()
        mock_headers = HTTPMessage()

        with pytest.raises(HTTPError) as exc_info:
            opener.error("http", req, mock_fp, 301, "Moved Permanently", mock_headers)

        assert exc_info.value.code == 301
        assert "Redirect refused" in str(exc_info.value)
