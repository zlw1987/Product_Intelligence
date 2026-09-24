"""Tests for the production section-oriented Vendor API contract (PROD-FIX1;
FU1 production-wire fidelity corrections).

The real production Vendor API answers HTTP 200 with
``Content-Type: text/html; charset=utf-8`` and a body that is NOT one JSON
document — a plain-text, section-oriented body::

    Ingram Product: { ... }
    CDW Product: {Not Found}
    Synnex EU Product: { ... }

These tests cover:
* the exact three bounded section labels (and refusal of arbitrary labels)
* the strict bounded literal parser (no eval / literal_eval / code execution)
* the exact bounded ``{Not Found}`` representation
* Decimal-exact monetary parsing (no binary float)
* the ACTUAL hybrid production Ingram field placement (explicit
  vendorPartNumber + nested pricing + top-level boolean availability +
  top-level Avl_Quantity) and the REAL nested Synnex EU form
  (OnlineCheck.Header.CurrencyCode / OnlineCheck.Item.*), including
  fake/redacted SessionId / BuyerAccountId / SystemId at their realistic
  structural locations
* the flat field forms as separately tested COMPATIBILITY forms (they are
  NOT the only or exact production wire shape)
* unknown/interstitial text between complete section literals is ignored
  (never parsed into data, never able to poison a complete mapping), while
  malformed content INSIDE a section literal still fails that source closed
* one malformed section must not destroy independently valid siblings
* sensitive upstream metadata stripped by the allowlist (synthetic fixtures
  with fake/redacted sentinel values only — never leaked production data)
* exactly ONE network call, transport/failure behavior preserved
* the canonical JSON wrapper contract still works (including flat sections)

All fixtures are synthetic; sensitive fields carry fake sentinel values.
"""

from __future__ import annotations

import json
from decimal import Decimal
from unittest.mock import MagicMock, patch

import pytest

from product_intelligence.providers.commercial import (
    CommercialAvailability,
    CommercialLookupQuery,
    CommercialNoteKind,
    CommercialPriceBasis,
    CommercialSourceCandidate,
    CommercialSourceIssue,
    LookupStatus,
    SourceOutcome,
)
from product_intelligence.providers.internal_vendor import (
    InternalVendorAdapter,
    _BoundedLiteralParser,
    _scan_section_oriented_body,
    _parse_and_map_section,
    _parse_section_value,
    _map_cdw,
    _map_ingram,
    _map_synnex_eu,
    _SectionValueParseError,
)


MPN = "MTFDKBA480TFR-1BC1ZABYYR"

# Synthetic fake sensitive values (redacted stand-ins; never production data)
FAKE_SESSION_ID = "FAKE-SESSION-000"
FAKE_BUYER_ACCOUNT_ID = "FAKE-ACCOUNT-000"
FAKE_SYSTEM_ID = "FAKE-SYSTEM-000"

# Synthetic FLAT compatibility envelope (single-quoted Python-repr style).
# FU1: the flat forms are retained compatibility forms — they are NOT the
# only or exact production wire shape (see the hybrid fixture below).
SECTION_BODY_REPR = (
    "Ingram Product: {'vendorPartNumber': 'MTFDKBA480TFR-1BC1ZABYYR', "
    "'customerPrice': 1515.72, 'currency': 'USD', 'quantity': 0}\n"
    "CDW Product: {Not Found}\n"
    "Synnex EU Product: {'SessionId': 'FAKE-SESSION-000', "
    "'BuyerAccountId': 'FAKE-ACCOUNT-000', 'SystemId': 'FAKE-SYSTEM-000', "
    "'ManufacturerItemIdentifier': 'MTFDKBA480TFR-1BC1ZABYYR', "
    "'UnitPriceAmount': 962.86, 'currency': 'EUR', 'AvailabilityTotal': 0}\n"
)

# Same flat compatibility envelope, double-quoted JSON-literal style
SECTION_BODY_JSON_STYLE = (
    'Ingram Product: {"vendorPartNumber": "MTFDKBA480TFR-1BC1ZABYYR", '
    '"customerPrice": 1515.72, "currency": "USD", "quantity": 0}\n'
    "CDW Product: {Not Found}\n"
    'Synnex EU Product: {"SessionId": "FAKE-SESSION-000", '
    '"BuyerAccountId": "FAKE-ACCOUNT-000", "SystemId": "FAKE-SYSTEM-000", '
    '"ManufacturerItemIdentifier": "MTFDKBA480TFR-1BC1ZABYYR", '
    '"UnitPriceAmount": 962.86, "currency": "EUR", "AvailabilityTotal": 0}\n'
)

# ---------------------------------------------------------------------------
# FU1: faithful HYBRID production envelopes — the ACTUAL production
# nesting/key placement (synthetic values at the observed structure)
# ---------------------------------------------------------------------------

# * Ingram: explicit vendorPartNumber; nested pricing block carrying
#   customerPrice + retailPrice + currencyCode; TOP-LEVEL boolean
#   availability (False); TOP-LEVEL Avl_Quantity (0); unrelated
#   non-authoritative fields (vendorName, warehouse) present and ignored.
# * CDW: the exact bounded {Not Found} marker.
# * Synnex EU: the REAL nested form — OnlineCheck.Header.CurrencyCode with
#   fake/redacted SessionId / BuyerAccountId / SystemId at their realistic
#   structural locations (the Header block), and
#   OnlineCheck.Item.ManufacturerItemIdentifier / UnitPriceAmount /
#   AvailabilityTotal.
SECTION_BODY_HYBRID_REPR = (
    "Ingram Product: {'vendorPartNumber': 'MTFDKBA480TFR-1BC1ZABYYR', "
    "'pricing': {'customerPrice': 1515.72, 'retailPrice': 2036.36, "
    "'currencyCode': 'USD'}, 'availability': False, 'Avl_Quantity': 0, "
    "'vendorName': 'FAKE-VENDOR-NAME', 'warehouse': 'FAKE-WH-00'}\n"
    "CDW Product: {Not Found}\n"
    "Synnex EU Product: {'OnlineCheck': {'Header': {'CurrencyCode': 'EUR', "
    "'SessionId': 'FAKE-SESSION-000', 'BuyerAccountId': 'FAKE-ACCOUNT-000', "
    "'SystemId': 'FAKE-SYSTEM-000'}, 'Item': {'ManufacturerItemIdentifier': "
    "'MTFDKBA480TFR-1BC1ZABYYR', 'UnitPriceAmount': 962.86, "
    "'AvailabilityTotal': 0}}}\n"
)

# The faithful hybrid envelope PLUS an unknown label line and a harmless
# interstitial line between two valid known sections (FU1 section-scanner
# correctness proof: unknown content never becomes data and never poisons a
# complete known mapping that has already ended).
SECTION_BODY_HYBRID_WITH_INTERSTITIAL = (
    "Ingram Product: {'vendorPartNumber': 'MTFDKBA480TFR-1BC1ZABYYR', "
    "'pricing': {'customerPrice': 1515.72, 'retailPrice': 2036.36, "
    "'currencyCode': 'USD'}, 'availability': False, 'Avl_Quantity': 0}\n"
    "Acme Product: {'vendorPartNumber': 'EVIL-MPN', 'customerPrice': 99999, "
    "'currency': 'USD', 'quantity': 42}\n"
    "==== section separator (interstitial noise) ====\n"
    "CDW Product: {Not Found}\n"
    "Synnex EU Product: {'OnlineCheck': {'Header': {'CurrencyCode': 'EUR'}, "
    "'Item': {'ManufacturerItemIdentifier': 'MTFDKBA480TFR-1BC1ZABYYR', "
    "'UnitPriceAmount': 962.86, 'AvailabilityTotal': 0}}}\n"
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _adapter_with_body(body: "str | bytes") -> InternalVendorAdapter:
    adapter = InternalVendorAdapter()
    adapter._base_url = "http://vendor.internal/api"
    adapter._validated = True
    return adapter


def _lookup_body(body: "str | bytes", mpn: str = MPN):
    """Run one adapter lookup against a mock transport returning *body*."""
    adapter = _adapter_with_body(body)
    if isinstance(body, str):
        body = body.encode("utf-8")
    mock_response = MagicMock()
    mock_response.read.return_value = body
    mock_opener = MagicMock()
    mock_opener.open.return_value = mock_response
    with patch(
        "product_intelligence.providers.internal_vendor._get_vendor_opener",
        return_value=mock_opener,
    ):
        response = adapter.lookup(CommercialLookupQuery(mpn=mpn))
    return response, mock_opener


# ---------------------------------------------------------------------------
# Section scanning
# ---------------------------------------------------------------------------


class TestSectionScanning:
    def test_all_three_labels_found_in_order(self) -> None:
        sections = _scan_section_oriented_body(SECTION_BODY_REPR)
        assert [s[0] for s in sections] == ["Ingram", "CDW", "Synnex EU"]

    def test_no_labels_returns_none(self) -> None:
        assert _scan_section_oriented_body("hello world\nnothing here") is None

    def test_unknown_labels_not_trusted(self) -> None:
        body = "Acme Product: {'x': 1}\nBeta Product: {'y': 2}\n"
        assert _scan_section_oriented_body(body) is None

    def test_unknown_labels_ignored_among_known(self) -> None:
        body = (
            "Ingram Product: {'vendorPartNumber': 'A'}\n"
            "Acme Product: {'vendorPartNumber': 'EVIL'}\n"
            "CDW Product: {Not Found}\n"
        )
        sections = _scan_section_oriented_body(body)
        assert [s[0] for s in sections] == ["Ingram", "CDW"]

    def test_label_case_sensitive(self) -> None:
        body = "ingram product: {'a': 1}\n"
        assert _scan_section_oriented_body(body) is None

    def test_label_not_at_line_start_not_recognized(self) -> None:
        body = "prefix Ingram Product: {'a': 1}\n"
        assert _scan_section_oriented_body(body) is None

    def test_label_without_colon_not_recognized(self) -> None:
        body = "Ingram Product {'a': 1}\n"
        assert _scan_section_oriented_body(body) is None

    def test_text_before_first_header_ignored(self) -> None:
        body = (
            "Vendor lookup result for MTFDKBA480TFR-1BC1ZABYYR\n"
            "--------------------------------------------------\n"
            + SECTION_BODY_REPR
        )
        sections = _scan_section_oriented_body(body)
        assert [s[0] for s in sections] == ["Ingram", "CDW", "Synnex EU"]

    def test_duplicate_label_first_wins(self) -> None:
        body = (
            "Ingram Product: {Not Found}\n"
            "Ingram Product: {'vendorPartNumber': 'X', 'customerPrice': 1, "
            "'currency': 'USD'}\n"
        )
        sections = _scan_section_oriented_body(body)
        assert len(sections) == 1
        assert sections[0][0] == "Ingram"
        assert "Not Found" in sections[0][1]

    def test_multiline_value_captured_until_next_header(self) -> None:
        body = (
            "Ingram Product: {'vendorPartNumber': 'A',\n"
            "  'customerPrice': 1.50,\n"
            "  'currency': 'USD'}\n"
            "CDW Product: {Not Found}\n"
        )
        sections = _scan_section_oriented_body(body)
        ingram_value = sections[0][1]
        assert "'customerPrice': 1.50" in ingram_value
        assert "CDW" not in ingram_value

    def test_leading_whitespace_before_label_tolerated(self) -> None:
        body = "   Ingram Product: {'a': 1}\n\tCDW Product: {Not Found}\n"
        sections = _scan_section_oriented_body(body)
        assert [s[0] for s in sections] == ["Ingram", "CDW"]


# ---------------------------------------------------------------------------
# Strict bounded literal parser
# ---------------------------------------------------------------------------


class TestBoundedLiteralParser:
    def _parse(self, text: str):
        return _BoundedLiteralParser(text).parse_value()

    def test_single_quoted_mapping(self) -> None:
        value = self._parse("{'a': 'x', 'b': 1}")
        assert value == {"a": "x", "b": 1}

    def test_double_quoted_mapping(self) -> None:
        value = self._parse('{"a": "x", "b": 1}')
        assert value == {"a": "x", "b": 1}

    def test_mixed_quote_mapping(self) -> None:
        value = self._parse("{'a': \"x\", 'b': 2}")
        assert value == {"a": "x", "b": 2}

    def test_decimal_number_exact_from_text(self) -> None:
        value = self._parse("{'p': 1515.72}")
        assert value["p"] == Decimal("1515.72")
        assert isinstance(value["p"], Decimal)

    def test_int_number(self) -> None:
        value = self._parse("{'q': 0}")
        assert value["q"] == Decimal("0")

    def test_negative_decimal(self) -> None:
        value = self._parse("{'n': -3.25}")
        assert value["n"] == Decimal("-3.25")

    def test_booleans_python_and_json(self) -> None:
        assert self._parse("True") is True
        assert self._parse("False") is False
        assert self._parse("true") is True
        assert self._parse("false") is False

    def test_none_and_null(self) -> None:
        assert self._parse("None") is None
        assert self._parse("null") is None

    def test_nested_mapping_and_list(self) -> None:
        value = self._parse("{'a': {'b': [1, 'x', None]}, 'c': []}")
        assert value == {"a": {"b": [1, "x", None]}, "c": []}

    def test_empty_mapping(self) -> None:
        assert self._parse("{}") == {}

    def test_string_escapes(self) -> None:
        assert self._parse("'a\\'b'") == "a'b"
        assert self._parse('"a\\"b"') == 'a"b'
        assert self._parse("'\\n\\t'") == "\n\t"
        assert self._parse("'\\u00e9'") == "\u00e9"
        assert self._parse("'\\\\'") == "\\"

    def test_duplicate_key_rejected(self) -> None:
        with pytest.raises(_SectionValueParseError):
            self._parse("{'a': 1, 'a': 2}")

    def test_non_string_key_rejected(self) -> None:
        with pytest.raises(_SectionValueParseError):
            self._parse("{1: 2}")
        with pytest.raises(_SectionValueParseError):
            self._parse("{a: 1}")

    def test_malformed_number_rejected(self) -> None:
        with pytest.raises(_SectionValueParseError):
            self._parse("{'a': 1.2.3}")
        with pytest.raises(_SectionValueParseError):
            self._parse("{'a': -}")
        with pytest.raises(_SectionValueParseError):
            self._parse("{'a': 1e5}")

    def test_unterminated_string_rejected(self) -> None:
        with pytest.raises(_SectionValueParseError):
            self._parse("{'a': 'x")

    def test_invalid_escape_rejected(self) -> None:
        with pytest.raises(_SectionValueParseError):
            self._parse("'\\q'")

    def test_expression_rejected(self) -> None:
        with pytest.raises(_SectionValueParseError):
            self._parse("{'a': 1 + 1}")
        with pytest.raises(_SectionValueParseError):
            self._parse("{'a': (1)}")

    def test_code_injection_never_executes(self) -> None:
        """A 'code-looking' value is refused by the strict grammar."""
        with pytest.raises(_SectionValueParseError):
            self._parse("{'a': __import__('os').system('id')}")

    def test_trailing_comma_tolerated(self) -> None:
        assert self._parse("{'a': 1,}") == {"a": 1}
        assert self._parse("[1, 2,]") == [1, 2]

    def test_depth_bound_enforced(self) -> None:
        deep = "{" * 40 + "}" * 40
        with pytest.raises(_SectionValueParseError):
            self._parse(deep)

    def test_entry_bound_enforced(self) -> None:
        big = "{" + ", ".join(f"'k{i}': {i}" for i in range(300)) + "}"
        with pytest.raises(_SectionValueParseError):
            self._parse(big)


class TestParseSectionValue:
    def test_not_found_exact(self) -> None:
        assert _parse_section_value("{Not Found}") == ("not_found", None)

    def test_not_found_whitespace_tolerant(self) -> None:
        assert _parse_section_value("   {  Not   Found  }  ") == (
            "not_found",
            None,
        )

    def test_notfound_without_space_is_not_the_marker(self) -> None:
        with pytest.raises(_SectionValueParseError):
            _parse_section_value("{NotFound}")

    def test_not_found_lower_case_not_the_marker(self) -> None:
        with pytest.raises(_SectionValueParseError):
            _parse_section_value("{not found}")

    def test_mapping_value(self) -> None:
        kind, value = _parse_section_value("{'a': 1}")
        assert kind == "mapping"
        assert value == {"a": 1}

    def test_non_mapping_top_level_rejected(self) -> None:
        with pytest.raises(_SectionValueParseError):
            _parse_section_value("[1, 2]")
        with pytest.raises(_SectionValueParseError):
            _parse_section_value("'just a string'")

    def test_trailing_garbage_rejected(self) -> None:
        # FU1 contract correction: a COMPLETE bounded literal is
        # authoritative — unknown text AFTER it is ignored interstitial
        # content (see test_trailing_interstitial_after_complete_mapping).
        # Trailing garbage that makes the literal itself INCOMPLETE (here:
        # the mapping is never closed) still fails that section closed.
        with pytest.raises(_SectionValueParseError):
            _parse_section_value("{'a': 1 trailing junk")

    def test_trailing_interstitial_after_complete_mapping_ignored(self) -> None:
        # FU1: unknown/interstitial lines between a complete section literal
        # and the next recognized header are never parsed into data and
        # cannot poison the complete mapping.
        kind, value = _parse_section_value(
            "{'a': 1}\nAcme Product: {'vendorPartNumber': 'EVIL'}\n"
            "==== end of ingram section ====\n"
        )
        assert kind == "mapping"
        assert value == {"a": 1}

    def test_trailing_interstitial_after_not_found_marker_ignored(self) -> None:
        kind, _ = _parse_section_value(
            "{Not Found}\ninterstitial noise line\n"
        )
        assert kind == "not_found"

    def test_interstitial_never_parsed_as_data(self) -> None:
        # The trailing content, even when it looks like another complete
        # literal, is unknown interstitial text: it is ignored, not parsed
        # into the section's data.
        kind, value = _parse_section_value(
            "{'a': 1}\n{'b': 2}\n"
        )
        assert kind == "mapping"
        assert value == {"a": 1}

    def test_missing_opening_brace_rejected(self) -> None:
        with pytest.raises(_SectionValueParseError):
            _parse_section_value("{'a': 1")
        with pytest.raises(_SectionValueParseError):
            _parse_section_value("a: 1")


# ---------------------------------------------------------------------------
# Section -> source mapping (flat production forms)
# ---------------------------------------------------------------------------


class TestFlatSectionMapping:
    def test_ingram_flat_production_fields(self) -> None:
        text = (
            "{'vendorPartNumber': 'MTFDKBA480TFR-1BC1ZABYYR', "
            "'customerPrice': 1515.72, 'currency': 'USD', 'quantity': 0}"
        )
        result = _parse_and_map_section("Ingram", text)
        assert isinstance(result, CommercialSourceCandidate)
        assert result.source_name == "Ingram"
        assert result.explicit_candidate_mpn == "MTFDKBA480TFR-1BC1ZABYYR"
        assert result.price_amount == Decimal("1515.72")
        assert result.price_basis == CommercialPriceBasis.CUSTOMER_PRICE
        assert result.currency_code == "USD"
        assert result.availability == CommercialAvailability.OUT_OF_STOCK
        assert result.quantity == 0

    def test_ingram_flat_retail_fallback(self) -> None:
        text = (
            "{'vendorPartNumber': 'A', 'retailPrice': 2500.00, "
            "'currency': 'USD', 'quantity': 5}"
        )
        result = _parse_and_map_section("Ingram", text)
        assert isinstance(result, CommercialSourceCandidate)
        assert result.price_basis == CommercialPriceBasis.RETAIL_PRICE_FALLBACK
        assert result.price_amount == Decimal("2500.00")
        assert result.availability == CommercialAvailability.IN_STOCK
        assert result.quantity == 5

    def test_ingram_flat_customer_price_present_but_malformed_no_fallback(self):
        text = (
            "{'vendorPartNumber': 'A', 'customerPrice': 'not_a_number', "
            "'retailPrice': 2500.00, 'currency': 'USD'}"
        )
        result = _parse_and_map_section("Ingram", text)
        assert isinstance(result, CommercialSourceIssue)
        assert result.outcome == SourceOutcome.MALFORMED_SECTION

    def test_ingram_flat_customer_price_null_no_fallback(self):
        text = (
            "{'vendorPartNumber': 'A', 'customerPrice': None, "
            "'retailPrice': 2500.00, 'currency': 'USD'}"
        )
        result = _parse_and_map_section("Ingram", text)
        assert isinstance(result, CommercialSourceIssue)
        assert result.outcome == SourceOutcome.MALFORMED_SECTION

    def test_ingram_flat_available_flag_truth_table(self) -> None:
        text = (
            "{'vendorPartNumber': 'A', 'customerPrice': 10, 'currency': 'USD', "
            "'available': False, 'quantity': 0}"
        )
        result = _parse_and_map_section("Ingram", text)
        assert isinstance(result, CommercialSourceCandidate)
        assert result.availability == CommercialAvailability.OUT_OF_STOCK

        text = (
            "{'vendorPartNumber': 'A', 'customerPrice': 10, 'currency': 'USD', "
            "'available': True, 'quantity': 0}"
        )
        result = _parse_and_map_section("Ingram", text)
        assert isinstance(result, CommercialSourceCandidate)
        # flag/quantity contradiction => UNKNOWN (never fabricated)
        assert result.availability == CommercialAvailability.UNKNOWN

    def test_ingram_flat_missing_price_malformed(self) -> None:
        text = "{'vendorPartNumber': 'A', 'currency': 'USD'}"
        result = _parse_and_map_section("Ingram", text)
        assert isinstance(result, CommercialSourceIssue)
        assert result.outcome == SourceOutcome.MALFORMED_SECTION

    def test_cdw_flat_found_form(self) -> None:
        text = (
            "{'manufacturerPartNumber': 'A', 'price': 1999.99, "
            "'currency': 'USD', 'quantity': 48}"
        )
        result = _parse_and_map_section("CDW", text)
        assert isinstance(result, CommercialSourceCandidate)
        assert result.price_amount == Decimal("1999.99")
        assert result.currency_code == "USD"
        assert result.availability == CommercialAvailability.IN_STOCK
        assert result.quantity == 48

    def test_cdw_flat_stock_status(self) -> None:
        text = (
            "{'manufacturerPartNumber': 'A', 'price': 10, 'currency': 'USD', "
            "'stockStatus': 'OutOfStock'}"
        )
        result = _parse_and_map_section("CDW", text)
        assert isinstance(result, CommercialSourceCandidate)
        assert result.availability == CommercialAvailability.OUT_OF_STOCK

    def test_cdw_not_found_form(self) -> None:
        result = _parse_and_map_section("CDW", "{Not Found}")
        assert isinstance(result, CommercialSourceIssue)
        assert result.outcome == SourceOutcome.NOT_FOUND
        assert result.source_name == "CDW"

    def test_synnex_flat_production_fields_with_sensitive_metadata(self) -> None:
        text = (
            "{'SessionId': 'FAKE-SESSION-000', 'BuyerAccountId': 'FAKE-ACCOUNT-000', "
            "'SystemId': 'FAKE-SYSTEM-000', 'ManufacturerItemIdentifier': 'A', "
            "'UnitPriceAmount': 962.86, 'currency': 'EUR', 'AvailabilityTotal': 0}"
        )
        result = _parse_and_map_section("Synnex EU", text)
        assert isinstance(result, CommercialSourceCandidate)
        assert result.price_amount == Decimal("962.86")
        assert result.currency_code == "EUR"
        assert result.availability == CommercialAvailability.OUT_OF_STOCK
        assert result.quantity == 0
        # CRITICAL PRIVACY INVARIANT: sensitive metadata never enters the
        # provider-neutral candidate.
        rendered = str(result)
        assert "FAKE-SESSION-000" not in rendered
        assert "FAKE-ACCOUNT-000" not in rendered
        assert "FAKE-SYSTEM-000" not in rendered
        assert "SessionId" not in rendered
        assert "BuyerAccountId" not in rendered
        assert "SystemId" not in rendered

    def test_synnex_flat_not_maintained_note(self) -> None:
        text = (
            "{'ManufacturerItemIdentifier': 'A', 'UnitPriceAmount': 100, "
            "'currency': 'EUR', 'Note': 'not maintained in our catalogue'}"
        )
        result = _parse_and_map_section("Synnex EU", text)
        assert isinstance(result, CommercialSourceIssue)
        assert result.outcome == SourceOutcome.NOT_FOUND

    def test_synnex_flat_no_returns_note(self) -> None:
        text = (
            "{'ManufacturerItemIdentifier': 'A', 'UnitPriceAmount': 100, "
            "'currency': 'EUR', 'AvailabilityTotal': 10, 'Note': 'No Returns'}"
        )
        result = _parse_and_map_section("Synnex EU", text)
        assert isinstance(result, CommercialSourceCandidate)
        assert result.note_kind == CommercialNoteKind.NO_RETURNS

    def test_synnex_flat_arbitrary_note_dropped(self) -> None:
        text = (
            "{'ManufacturerItemIdentifier': 'A', 'UnitPriceAmount': 100, "
            "'currency': 'EUR', 'AvailabilityTotal': 10, "
            "'Note': 'free form secret text SENTINEL-NOTE'}"
        )
        result = _parse_and_map_section("Synnex EU", text)
        assert isinstance(result, CommercialSourceCandidate)
        assert result.note_kind is None
        assert "SENTINEL-NOTE" not in str(result)

    def test_malformed_section_value_is_bounded_issue(self) -> None:
        result = _parse_and_map_section("Ingram", "{garbage without structure")
        assert isinstance(result, CommercialSourceIssue)
        assert result.outcome == SourceOutcome.MALFORMED_SECTION
        assert result.source_name == "Ingram"

    def test_section_value_not_a_mapping_is_bounded(self) -> None:
        result = _parse_and_map_section("CDW", "[1, 2, 3]")
        assert isinstance(result, CommercialSourceIssue)
        assert result.outcome == SourceOutcome.MALFORMED_SECTION

    def test_nested_canonical_forms_still_work(self) -> None:
        # Canonical nested Ingram through the same mapper
        nested = {
            "sourceName": "Ingram",
            "vendorPartNumber": "A",
            "pricing": {"customerPrice": Decimal("1.00"), "currencyCode": "USD"},
            "availability": {"available": True, "Avl_Quantity": 2},
        }
        result = _map_ingram(nested)
        assert isinstance(result, CommercialSourceCandidate)
        assert result.availability == CommercialAvailability.IN_STOCK
        assert result.quantity == 2


# ---------------------------------------------------------------------------
# FU1: faithful hybrid production field placement (adapter-level)
# ---------------------------------------------------------------------------


class TestHybridProductionSection:
    """The ACTUAL production Ingram/Synnex nesting, through the real
    adapter lookup path (not a scanner-only or mapper-only test).

    * Ingram hybrid: nested pricing (customerPrice authoritative) +
      top-level boolean availability + top-level Avl_Quantity.
    * Synnex EU: the REAL nested OnlineCheck form with fake/redacted
      sensitive Header metadata.
    * Unknown/interstitial content between complete known sections is
      ignored and never becomes data.
    """

    def test_hybrid_envelope_maps_faithfully(self) -> None:
        response, mock_opener = _lookup_body(SECTION_BODY_HYBRID_REPR)
        assert response.status == LookupStatus.PARTIAL
        # Exactly ONE network call
        assert mock_opener.open.call_count == 1

        candidates = {c.source_name: c for c in response.candidates}
        assert set(candidates) == {"Ingram", "Synnex EU"}

        # Ingram: the exact requested MPN, customer price authoritative
        # (retailPrice 2036.36 present but NOT used), USD from the nested
        # pricing block, OUT_OF_STOCK / 0 from the TOP-LEVEL availability
        # boolean + TOP-LEVEL Avl_Quantity.
        ingram = candidates["Ingram"]
        assert ingram.explicit_candidate_mpn == MPN
        assert ingram.price_amount == Decimal("1515.72")
        assert ingram.price_basis == CommercialPriceBasis.CUSTOMER_PRICE
        assert ingram.currency_code == "USD"
        assert ingram.availability == CommercialAvailability.OUT_OF_STOCK
        assert ingram.quantity == 0

        # Synnex EU: real nested form, exact MPN, 962.86 EUR, OOS / 0.
        synnex = candidates["Synnex EU"]
        assert synnex.explicit_candidate_mpn == MPN
        assert synnex.price_amount == Decimal("962.86")
        assert synnex.price_basis == CommercialPriceBasis.LIST_PRICE
        assert synnex.currency_code == "EUR"
        assert synnex.availability == CommercialAvailability.OUT_OF_STOCK
        assert synnex.quantity == 0

        issues = {i.source_name: i for i in response.issues}
        assert set(issues) == {"CDW"}
        assert issues["CDW"].outcome == SourceOutcome.NOT_FOUND

        # Sensitive + non-authoritative metadata absent from the whole
        # normalized response (allowlist boundary).
        rendered = str(response)
        for sentinel in (
            FAKE_SESSION_ID,
            FAKE_BUYER_ACCOUNT_ID,
            FAKE_SYSTEM_ID,
            "SessionId",
            "BuyerAccountId",
            "SystemId",
            "FAKE-VENDOR-NAME",
            "FAKE-WH-00",
            "vendorName",
            "warehouse",
            "retailPrice",
            "2036.36",
        ):
            assert sentinel not in rendered

    def test_unknown_label_and_interstitial_between_known_sections(self) -> None:
        """FULL adapter-level proof (FU1 section-scanner correctness):
        an unknown label line AND a harmless interstitial line between two
        valid known sections never become data and never poison the
        complete known mappings."""
        response, mock_opener = _lookup_body(
            SECTION_BODY_HYBRID_WITH_INTERSTITIAL
        )
        assert mock_opener.open.call_count == 1

        candidates = {c.source_name: c for c in response.candidates}
        # BOTH complete known sections mapped faithfully, in order
        assert set(candidates) == {"Ingram", "Synnex EU"}
        assert candidates["Ingram"].price_amount == Decimal("1515.72")
        assert candidates["Ingram"].availability == (
            CommercialAvailability.OUT_OF_STOCK
        )
        assert candidates["Ingram"].quantity == 0
        assert candidates["Synnex EU"].price_amount == Decimal("962.86")

        issues = {i.source_name: i for i in response.issues}
        assert set(issues) == {"CDW"}
        assert issues["CDW"].outcome == SourceOutcome.NOT_FOUND

        # The unknown section never becomes data: no EVIL-MPN candidate,
        # no 99999 price, no Acme issue of any kind.
        rendered = str(response)
        assert "EVIL-MPN" not in rendered
        assert "99999" not in rendered
        assert "Acme" not in rendered
        assert "interstitial" not in rendered

    def test_hybrid_ingram_in_stock_true_positive(self) -> None:
        text = (
            "{'vendorPartNumber': 'A', "
            "'pricing': {'customerPrice': 10.00, 'currencyCode': 'USD'}, "
            "'availability': True, 'Avl_Quantity': 25}"
        )
        result = _parse_and_map_section("Ingram", text)
        assert isinstance(result, CommercialSourceCandidate)
        assert result.availability == CommercialAvailability.IN_STOCK
        assert result.quantity == 25

    def test_hybrid_ingram_contradiction_fails_closed_unknown(self) -> None:
        # true + 0 => contradiction => UNKNOWN (never fabricated)
        text = (
            "{'vendorPartNumber': 'A', "
            "'pricing': {'customerPrice': 10.00, 'currencyCode': 'USD'}, "
            "'availability': True, 'Avl_Quantity': 0}"
        )
        result = _parse_and_map_section("Ingram", text)
        assert isinstance(result, CommercialSourceCandidate)
        assert result.availability == CommercialAvailability.UNKNOWN

        # false + positive => contradiction => UNKNOWN
        text = (
            "{'vendorPartNumber': 'A', "
            "'pricing': {'customerPrice': 10.00, 'currencyCode': 'USD'}, "
            "'availability': False, 'Avl_Quantity': 7}"
        )
        result = _parse_and_map_section("Ingram", text)
        assert isinstance(result, CommercialSourceCandidate)
        assert result.availability == CommercialAvailability.UNKNOWN

    def test_hybrid_ingram_lone_flag_fails_closed_unknown(self) -> None:
        # false with NO quantity evidence => UNKNOWN (never fabricated)
        text = (
            "{'vendorPartNumber': 'A', "
            "'pricing': {'customerPrice': 10.00, 'currencyCode': 'USD'}, "
            "'availability': False}"
        )
        result = _parse_and_map_section("Ingram", text)
        assert isinstance(result, CommercialSourceCandidate)
        assert result.availability == CommercialAvailability.UNKNOWN
        assert result.quantity is None

    def test_hybrid_ingram_no_flag_quantity_evidence_kept(self) -> None:
        # Top-level Avl_Quantity alone (no boolean signal): the quantity
        # evidence is preserved, availability stays UNKNOWN (no lone
        # signal fabricates a stock state in the nested-pricing branch).
        text = (
            "{'vendorPartNumber': 'A', "
            "'pricing': {'customerPrice': 10.00, 'currencyCode': 'USD'}, "
            "'Avl_Quantity': 0}"
        )
        result = _parse_and_map_section("Ingram", text)
        assert isinstance(result, CommercialSourceCandidate)
        assert result.availability == CommercialAvailability.UNKNOWN
        assert result.quantity == 0

    def test_hybrid_ingram_customer_price_authoritative_over_retail(self) -> None:
        text = (
            "{'vendorPartNumber': 'A', "
            "'pricing': {'customerPrice': 100.00, 'retailPrice': 200.00, "
            "'currencyCode': 'USD'}, 'availability': False, "
            "'Avl_Quantity': 0}"
        )
        result = _parse_and_map_section("Ingram", text)
        assert isinstance(result, CommercialSourceCandidate)
        assert result.price_amount == Decimal("100.00")
        assert result.price_basis == CommercialPriceBasis.CUSTOMER_PRICE

    def test_hybrid_ingram_retail_fallback_only_when_key_absent(self) -> None:
        text = (
            "{'vendorPartNumber': 'A', "
            "'pricing': {'retailPrice': 200.00, 'currencyCode': 'USD'}, "
            "'availability': True, 'Avl_Quantity': 3}"
        )
        result = _parse_and_map_section("Ingram", text)
        assert isinstance(result, CommercialSourceCandidate)
        assert result.price_amount == Decimal("200.00")
        assert result.price_basis == CommercialPriceBasis.RETAIL_PRICE_FALLBACK

    def test_hybrid_ingram_customer_price_malformed_no_fallback(self) -> None:
        # customerPrice PRESENT but malformed: authoritative key => the
        # section fails closed (no retail fallback), even in the hybrid
        # placement.
        text = (
            "{'vendorPartNumber': 'A', "
            "'pricing': {'customerPrice': 'not_a_number', "
            "'retailPrice': 200.00, 'currencyCode': 'USD'}, "
            "'availability': False, 'Avl_Quantity': 0}"
        )
        result = _parse_and_map_section("Ingram", text)
        assert isinstance(result, CommercialSourceIssue)
        assert result.outcome == SourceOutcome.MALFORMED_SECTION

    def test_hybrid_canonical_availability_dict_still_canonical(self) -> None:
        # The canonical nested availability dict takes precedence over the
        # hybrid top-level placement (a section does not publish both).
        text = (
            "{'vendorPartNumber': 'A', "
            "'pricing': {'customerPrice': 10.00, 'currencyCode': 'USD'}, "
            "'availability': {'available': True, 'Avl_Quantity': 4}}"
        )
        result = _parse_and_map_section("Ingram", text)
        assert isinstance(result, CommercialSourceCandidate)
        assert result.availability == CommercialAvailability.IN_STOCK
        assert result.quantity == 4

    def test_hybrid_malformed_inside_literal_still_fails_closed(self) -> None:
        # Malformed content INSIDE a known section's literal (the mapping
        # is never closed) fails that source closed — while the complete
        # sibling sections survive.
        body = (
            "Ingram Product: {'vendorPartNumber': 'A', 'pricing': {"
            "'customerPrice': 10.00, 'currencyCode': 'USD',\n"
            "CDW Product: {Not Found}\n"
            "Synnex EU Product: {'OnlineCheck': {'Header': {'CurrencyCode': 'EUR'}, "
            "'Item': {'ManufacturerItemIdentifier': 'A', 'UnitPriceAmount': 1.0, "
            "'AvailabilityTotal': 2}}}\n"
        )
        response, _ = _lookup_body(body, mpn="A")
        assert response.status == LookupStatus.PARTIAL
        candidates = {c.source_name: c for c in response.candidates}
        assert set(candidates) == {"Synnex EU"}
        assert candidates["Synnex EU"].quantity == 2
        issues = {i.source_name: i for i in response.issues}
        assert issues["Ingram"].outcome == SourceOutcome.MALFORMED_SECTION
        assert issues["CDW"].outcome == SourceOutcome.NOT_FOUND

    def test_synnex_nested_form_mapper_direct(self) -> None:
        text = (
            "{'OnlineCheck': {'Header': {'CurrencyCode': 'EUR', "
            "'SessionId': 'FAKE-SESSION-000', 'BuyerAccountId': 'FAKE-ACCOUNT-000', "
            "'SystemId': 'FAKE-SYSTEM-000'}, 'Item': {'ManufacturerItemIdentifier': "
            "'A', 'UnitPriceAmount': 962.86, 'AvailabilityTotal': 0}}}}"
        )
        result = _parse_and_map_section("Synnex EU", text)
        assert isinstance(result, CommercialSourceCandidate)
        assert result.price_amount == Decimal("962.86")
        assert result.currency_code == "EUR"
        assert result.availability == CommercialAvailability.OUT_OF_STOCK
        assert result.quantity == 0
        # PRIVACY INVARIANT: the Header's sensitive metadata never enters
        # the provider-neutral candidate.
        rendered = str(result)
        for sentinel in (
            FAKE_SESSION_ID,
            FAKE_BUYER_ACCOUNT_ID,
            FAKE_SYSTEM_ID,
            "SessionId",
            "BuyerAccountId",
            "SystemId",
        ):
            assert sentinel not in rendered


# ---------------------------------------------------------------------------
# Adapter-level: section body through the full lookup path
# ---------------------------------------------------------------------------


class TestAdapterSectionContract:
    def test_production_equivalent_envelope(self) -> None:
        response, mock_opener = _lookup_body(SECTION_BODY_REPR)
        assert response.status == LookupStatus.PARTIAL
        assert response.retrieved_at is not None
        # Exactly ONE network call
        assert mock_opener.open.call_count == 1

        candidates = {c.source_name: c for c in response.candidates}
        assert set(candidates) == {"Ingram", "Synnex EU"}

        ingram = candidates["Ingram"]
        assert ingram.explicit_candidate_mpn == MPN
        assert ingram.price_amount == Decimal("1515.72")
        assert ingram.currency_code == "USD"
        assert ingram.price_basis == CommercialPriceBasis.CUSTOMER_PRICE
        assert ingram.availability == CommercialAvailability.OUT_OF_STOCK
        assert ingram.quantity == 0

        synnex = candidates["Synnex EU"]
        assert synnex.explicit_candidate_mpn == MPN
        assert synnex.price_amount == Decimal("962.86")
        assert synnex.currency_code == "EUR"
        assert synnex.availability == CommercialAvailability.OUT_OF_STOCK
        assert synnex.quantity == 0

        issues = {i.source_name: i for i in response.issues}
        assert set(issues) == {"CDW"}
        assert issues["CDW"].outcome == SourceOutcome.NOT_FOUND

        # Sensitive metadata absent from the whole response
        rendered = str(response)
        for sentinel in (
            FAKE_SESSION_ID,
            FAKE_BUYER_ACCOUNT_ID,
            FAKE_SYSTEM_ID,
            "SessionId",
            "BuyerAccountId",
            "SystemId",
        ):
            assert sentinel not in rendered

    def test_json_style_envelope(self) -> None:
        response, _ = _lookup_body(SECTION_BODY_JSON_STYLE)
        assert response.status == LookupStatus.PARTIAL
        candidates = {c.source_name: c for c in response.candidates}
        assert candidates["Ingram"].price_amount == Decimal("1515.72")
        assert candidates["Synnex EU"].price_amount == Decimal("962.86")

    def test_malformed_one_source_does_not_destroy_others(self) -> None:
        body = (
            "Ingram Product: {'vendorPartNumber': 'A', 'customerPrice': 10.5, "
            "'currency': 'USD', 'quantity': 3}\n"
            "CDW Product: {Not Found}\n"
            "Synnex EU Product: {broken grammar here\n"
        )
        response, _ = _lookup_body(body, mpn="A")
        assert response.status == LookupStatus.PARTIAL
        candidates = {c.source_name: c for c in response.candidates}
        assert "Ingram" in candidates
        assert candidates["Ingram"].quantity == 3
        issues = {i.source_name: i for i in response.issues}
        assert issues["CDW"].outcome == SourceOutcome.NOT_FOUND
        assert issues["Synnex EU"].outcome == SourceOutcome.MALFORMED_SECTION

    def test_all_sections_not_found_is_partial(self) -> None:
        body = (
            "Ingram Product: {Not Found}\n"
            "CDW Product: {Not Found}\n"
            "Synnex EU Product: {Not Found}\n"
        )
        response, _ = _lookup_body(body)
        assert response.status == LookupStatus.PARTIAL
        assert response.candidates == ()
        assert {i.source_name for i in response.issues} == {
            "Ingram",
            "CDW",
            "Synnex EU",
        }
        assert all(i.outcome == SourceOutcome.NOT_FOUND for i in response.issues)

    def test_all_sections_malformed_is_failed(self) -> None:
        body = (
            "Ingram Product: {oops\n"
            "CDW Product: [1, 2]\n"
            "Synnex EU Product: trailing after {'a': 1} junk\n"
        )
        response, _ = _lookup_body(body)
        assert response.status == LookupStatus.FAILED
        assert response.candidates == ()
        assert len(response.issues) == 3

    def test_no_recognized_contract_failed(self) -> None:
        response, _ = _lookup_body("this is not any supported contract at all")
        assert response.status == LookupStatus.FAILED
        assert response.retrieved_at is None
        assert response.candidates == ()
        assert response.issues == ()

    def test_json_contract_still_works(self) -> None:
        """The canonical JSON wrapper contract is retained."""
        payload = {
            "Ingram": {
                "sourceName": "Ingram",
                "vendorPartNumber": MPN,
                "pricing": {"customerPrice": "1515.72", "currencyCode": "USD"},
                "availability": {"available": False, "Avl_Quantity": 0},
            },
        }
        response, mock_opener = _lookup_body(json.dumps(payload).encode("utf-8"))
        assert response.status == LookupStatus.SUCCESS
        assert mock_opener.open.call_count == 1
        candidate = response.candidates[0]
        assert candidate.price_amount == Decimal("1515.72")

    def test_json_wrapper_with_flat_sections(self) -> None:
        """A JSON wrapper document carrying flat production sections is
        also parsed (the allowlist mappers accept both forms)."""
        payload = {
            "Ingram": {
                "vendorPartNumber": MPN,
                "customerPrice": "1515.72",
                "currency": "USD",
                "quantity": 0,
            },
            "Synnex EU": {
                "ManufacturerItemIdentifier": MPN,
                "UnitPriceAmount": "962.86",
                "currency": "EUR",
                "AvailabilityTotal": 0,
                "SessionId": FAKE_SESSION_ID,
            },
        }
        response, _ = _lookup_body(json.dumps(payload).encode("utf-8"))
        assert response.status == LookupStatus.SUCCESS
        candidates = {c.source_name: c for c in response.candidates}
        assert candidates["Ingram"].price_amount == Decimal("1515.72")
        assert candidates["Synnex EU"].price_amount == Decimal("962.86")
        assert FAKE_SESSION_ID not in str(response)

    def test_transport_failure_behavior_unchanged(self) -> None:
        from urllib.error import URLError

        adapter = _adapter_with_body(None)
        mock_opener = MagicMock()
        mock_opener.open.side_effect = URLError("connection refused")
        with patch(
            "product_intelligence.providers.internal_vendor._get_vendor_opener",
            return_value=mock_opener,
        ):
            response = adapter.lookup(CommercialLookupQuery(mpn=MPN))
        assert response.status == LookupStatus.FAILED
        assert response.retrieved_at is None

    def test_oversized_section_body_failed(self) -> None:
        body = "Ingram Product: {'a': 1}\n" + "x" * (2 * 1024 * 1024)
        response, _ = _lookup_body(body)
        assert response.status == LookupStatus.FAILED
        assert response.retrieved_at is None

    def test_non_utf8_body_failed(self) -> None:
        response, _ = _lookup_body(b"\xff\xfe\x00\x01binary")
        assert response.status == LookupStatus.FAILED
        assert response.retrieved_at is None

    def test_sensitive_metadata_never_in_response(self) -> None:
        """CRITICAL PRIVACY INVARIANT at the adapter boundary.

        The real Synnex payload carries SessionId / BuyerAccountId /
        SystemId. Synthetic equivalents here use fake sentinel values; the
        allowlist mapper must strip them from the response.
        """
        body = (
            "Ingram Product: {'vendorPartNumber': 'A', 'customerPrice': 1, "
            "'currency': 'USD', 'SessionId': 'SENTINEL-S'}\n"
            "CDW Product: {'manufacturerPartNumber': 'A', 'price': 2, "
            "'currencyCode': 'USD', 'BuyerAccountId': 'SENTINEL-B'}\n"
            "Synnex EU Product: {'SystemId': 'SENTINEL-Y', "
            "'ManufacturerItemIdentifier': 'A', 'UnitPriceAmount': 3, "
            "'currency': 'EUR'}\n"
        )
        response, _ = _lookup_body(body, mpn="A")
        rendered = str(response)
        for sentinel in ("SENTINEL-S", "SENTINEL-B", "SENTINEL-Y"):
            assert sentinel not in rendered
        for key in ("SessionId", "BuyerAccountId", "SystemId"):
            assert key not in rendered

    def test_arbitrary_section_labels_never_persisted(self) -> None:
        body = (
            "EvilCorp Product: {'vendorPartNumber': 'A', 'customerPrice': 1, "
            "'currency': 'USD'}\n"
            "Ingram Product: {Not Found}\n"
        )
        response, _ = _lookup_body(body, mpn="A")
        rendered = str(response)
        assert "EvilCorp" not in rendered
        # Only the recognized Ingram section is processed
        assert response.issues == (
            CommercialSourceIssue(source_name="Ingram", outcome=SourceOutcome.NOT_FOUND),
        )

    def test_raw_body_not_logged_or_retained(self) -> None:
        """The response object carries no raw body text."""
        response, _ = _lookup_body(SECTION_BODY_REPR)
        rendered = repr(response)
        # No raw upstream dictionary text survives in the response object
        assert "customerPrice" not in rendered
        assert "'quantity': 0" not in rendered
