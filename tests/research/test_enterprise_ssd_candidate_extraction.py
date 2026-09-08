"""Enterprise SSD candidate extraction tests (PRODUCT-INTEL.7A).

Tests the pure research extraction function that discovers candidate
product observations from embedded JSON product data arrays.
"""

from __future__ import annotations

from datetime import datetime, timezone

from product_intelligence.research.enterprise_ssd_candidate_extraction import (
    extract_enterprise_ssd_candidate_observations,
)
from product_intelligence.research.specifications import SourceAuthority

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_RETRIEVED_AT = datetime(2026, 9, 4, 20, 42, 23, tzinfo=timezone.utc)
_SOURCE_NAME = "Seagate Enterprise Support"
_SOURCE_URL = "https://www.seagate.com/support/enterprise-storage/solid-state-drives/nytro-5050/"
_AUTHORITY = SourceAuthority.AUTHORITATIVE


def _build_document(records_json: str) -> str:
    """Wrap a JSON array in the supportSpecsData assignment pattern."""
    return (
        "<script>\n"
        "var supportSpecsData = JSON.parse('"
        + records_json
        + "');\n"
        "</script>\n"
    )


def _extract(records_json: str) -> tuple:
    """Convenience: build document and extract."""
    doc = _build_document(records_json)
    return extract_enterprise_ssd_candidate_observations(
        document=doc,
        source_name=_SOURCE_NAME,
        source_url=_SOURCE_URL,
        retrieved_at=_RETRIEVED_AT,
        source_authority=_AUTHORITY,
    )


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestEmptyAndMissing:
    def test_empty_document(self) -> None:
        """Empty document produces no observations."""
        result = extract_enterprise_ssd_candidate_observations(
            document="",
            source_name=_SOURCE_NAME,
            source_url=_SOURCE_URL,
            retrieved_at=_RETRIEVED_AT,
            source_authority=_AUTHORITY,
        )
        assert result == ()

    def test_no_support_specs_data(self) -> None:
        """Document with no supportSpecsData produces no observations."""
        doc = '<script>var otherVar = JSON.parse("[1,2,3]");</script>'
        result = extract_enterprise_ssd_candidate_observations(
            document=doc,
            source_name=_SOURCE_NAME,
            source_url=_SOURCE_URL,
            retrieved_at=_RETRIEVED_AT,
            source_authority=_AUTHORITY,
        )
        assert result == ()

    def test_unrelated_json_parse_ignored(self) -> None:
        """JSON.parse assigned to a different variable is ignored."""
        records = '[{"skuNumber":"ABC","title":"test"}]'
        doc = (
            '<script>\n'
            "var someOtherData = JSON.parse('"
            + records + "');\n"
            "</script>\n"
        )
        result = extract_enterprise_ssd_candidate_observations(
            document=doc,
            source_name=_SOURCE_NAME,
            source_url=_SOURCE_URL,
            retrieved_at=_RETRIEVED_AT,
            source_authority=_AUTHORITY,
        )
        assert result == ()

    def test_same_script_unrelated_json_parse_cannot_leak(self) -> None:
        """An unrelated JSON.parse in the same <script> tag cannot leak
        candidate observations even if supportSpecsData is also present."""
        # Both in the same script — only supportSpecsData's array should matter
        fake_records = '[{"skuNumber":"FAKE001","title":"Fake Product"}]'
        real_records = '[{"skuNumber":"REAL001","title":"Real Product"}]'
        doc = (
            '<script>\n'
            "var someOtherData = JSON.parse('" + fake_records + "');\n"
            "var supportSpecsData = JSON.parse('" + real_records + "');\n"
            "</script>\n"
        )
        result = extract_enterprise_ssd_candidate_observations(
            document=doc,
            source_name=_SOURCE_NAME,
            source_url=_SOURCE_URL,
            retrieved_at=_RETRIEVED_AT,
            source_authority=_AUTHORITY,
        )
        assert len(result) == 1
        assert result[0].manufacturer_part_number_raw == "REAL001"
        # FAKE001 must NOT appear
        for obs in result:
            assert obs.manufacturer_part_number_raw != "FAKE001"


class TestPayloadStructure:
    def test_malformed_support_specs_data_fails_closed(self) -> None:
        """Malformed JSON in supportSpecsData produces no observations
        from that block, but valid sibling blocks can still survive."""
        # First script: malformed
        doc = (
            '<script>\n'
            "var supportSpecsData = JSON.parse('not valid json at all');\n"
            "</script>\n"
        )
        result = extract_enterprise_ssd_candidate_observations(
            document=doc,
            source_name=_SOURCE_NAME,
            source_url=_SOURCE_URL,
            retrieved_at=_RETRIEVED_AT,
            source_authority=_AUTHORITY,
        )
        assert result == ()

    def test_malformed_block_sibling_valid_survives(self) -> None:
        """If a valid supportSpecsData block exists alongside a malformed
        one, the valid block still produces observations."""
        malformed = "not valid json"
        valid = '[{"skuNumber":"GOOD001","title":"Good"}]'
        doc = (
            '<script>\n'
            "var supportSpecsData = JSON.parse('" + malformed + "');\n"
            "</script>\n"
            '<script>\n'
            "var supportSpecsData = JSON.parse('" + valid + "');\n"
            "</script>\n"
        )
        result = extract_enterprise_ssd_candidate_observations(
            document=doc,
            source_name=_SOURCE_NAME,
            source_url=_SOURCE_URL,
            retrieved_at=_RETRIEVED_AT,
            source_authority=_AUTHORITY,
        )
        assert len(result) == 1
        assert result[0].manufacturer_part_number_raw == "GOOD001"

    def test_non_list_payload_ignored(self) -> None:
        """If supportSpecsData is not an array, no observations produced."""
        doc = _build_document('{"skuNumber": "ABC123"}')
        result = extract_enterprise_ssd_candidate_observations(
            document=doc,
            source_name=_SOURCE_NAME,
            source_url=_SOURCE_URL,
            retrieved_at=_RETRIEVED_AT,
            source_authority=_AUTHORITY,
        )
        assert result == ()

    def test_non_dict_records_ignored(self) -> None:
        """Records that are not dicts are ignored."""
        doc = _build_document('[1, "string", {"skuNumber": "ABC"}]')
        result = extract_enterprise_ssd_candidate_observations(
            document=doc,
            source_name=_SOURCE_NAME,
            source_url=_SOURCE_URL,
            retrieved_at=_RETRIEVED_AT,
            source_authority=_AUTHORITY,
        )
        assert len(result) == 1
        assert result[0].manufacturer_part_number_raw == "ABC"


class TestRecordFields:
    def test_missing_sku_number_ignored(self) -> None:
        """Records without skuNumber are ignored."""
        doc = _build_document('[{"title": "No SKU"}, {"skuNumber": "ABC123"}]')
        result = extract_enterprise_ssd_candidate_observations(
            document=doc,
            source_name=_SOURCE_NAME,
            source_url=_SOURCE_URL,
            retrieved_at=_RETRIEVED_AT,
            source_authority=_AUTHORITY,
        )
        assert len(result) == 1
        assert result[0].manufacturer_part_number_raw == "ABC123"

    def test_blank_sku_number_ignored(self) -> None:
        """Records with blank skuNumber are ignored."""
        doc = _build_document('[{"skuNumber": "   "}, {"skuNumber": "ABC123"}]')
        result = extract_enterprise_ssd_candidate_observations(
            document=doc,
            source_name=_SOURCE_NAME,
            source_url=_SOURCE_URL,
            retrieved_at=_RETRIEVED_AT,
            source_authority=_AUTHORITY,
        )
        assert len(result) == 1
        assert result[0].manufacturer_part_number_raw == "ABC123"

    def test_title_optional(self) -> None:
        """Records without title still produce observations."""
        doc = _build_document('[{"skuNumber": "ABC123"}]')
        result = extract_enterprise_ssd_candidate_observations(
            document=doc,
            source_name=_SOURCE_NAME,
            source_url=_SOURCE_URL,
            retrieved_at=_RETRIEVED_AT,
            source_authority=_AUTHORITY,
        )
        assert len(result) == 1
        assert result[0].product_name_raw is None

    def test_title_preserved_exactly(self) -> None:
        """Title is preserved exactly as published."""
        doc = _build_document(
            '[{"skuNumber": "ABC123", "title": "Nytro 5350H SSD 15.36TB"}]'
        )
        result = extract_enterprise_ssd_candidate_observations(
            document=doc,
            source_name=_SOURCE_NAME,
            source_url=_SOURCE_URL,
            retrieved_at=_RETRIEVED_AT,
            source_authority=_AUTHORITY,
        )
        assert len(result) == 1
        assert result[0].product_name_raw == "Nytro 5350H SSD 15.36TB"

    def test_sku_number_preserved_exactly(self) -> None:
        """skuNumber is preserved exactly as published (no normalization)."""
        doc = _build_document('[{"skuNumber": "XP15360SE70005"}]')
        result = extract_enterprise_ssd_candidate_observations(
            document=doc,
            source_name=_SOURCE_NAME,
            source_url=_SOURCE_URL,
            retrieved_at=_RETRIEVED_AT,
            source_authority=_AUTHORITY,
        )
        assert len(result) == 1
        assert result[0].manufacturer_part_number_raw == "XP15360SE70005"

    def test_arbitrary_visible_text_not_mined(self) -> None:
        """Text outside the supportSpecsData JSON is not mined for MPNs."""
        doc = (
            '<p>Product MPN is ABCDEFGH and we love it.</p>\n'
            + _build_document('[]')
        )
        result = extract_enterprise_ssd_candidate_observations(
            document=doc,
            source_name=_SOURCE_NAME,
            source_url=_SOURCE_URL,
            retrieved_at=_RETRIEVED_AT,
            source_authority=_AUTHORITY,
        )
        assert result == ()

    def test_feature_values_cannot_create_candidates(self) -> None:
        """Features array values are not mined for candidate MPNs."""
        doc = _build_document(
            '['
            '{"skuNumber": "TARGET001", "title": "Product", '
            '"features": [{"title": "Interface", "value": "PCIe Gen4 x4 NVMe"}, '
            '{"title": "Form Factor", "value": "2.5in"}]'
            '}'
            ']'
        )
        result = extract_enterprise_ssd_candidate_observations(
            document=doc,
            source_name=_SOURCE_NAME,
            source_url=_SOURCE_URL,
            retrieved_at=_RETRIEVED_AT,
            source_authority=_AUTHORITY,
        )
        assert len(result) == 1
        assert result[0].manufacturer_part_number_raw == "TARGET001"

    def test_unicode_trademark_preserved_exactly(self) -> None:
        """Non-ASCII literal Unicode (trademark symbol) in title is
        preserved exactly, not corrupted by unicode_escape round-trip.

        The bounded decoder handles JS string escapes but preserves
        already-literal Unicode text exactly.
        """
        trademark = chr(0x00AE)  # registered trademark
        json_inner = (
            '{"skuNumber": "UNI001", "title": "Nytro' + trademark + '"}'
        )
        doc = _build_document("[" + json_inner + "]")
        result = extract_enterprise_ssd_candidate_observations(
            document=doc,
            source_name=_SOURCE_NAME,
            source_url=_SOURCE_URL,
            retrieved_at=_RETRIEVED_AT,
            source_authority=_AUTHORITY,
        )
        assert len(result) == 1
        assert result[0].product_name_raw == f"Nytro{trademark}"
        assert trademark in result[0].product_name_raw

    def test_unicode_escaped_js_string_decoded_correctly(self) -> None:
        """JS unicode escapes in the supportSpecsData string are decoded
        correctly by the bounded decoder (mirrors real fixture behavior).

        The real fixture uses double-escaped JS strings: \\\\u003c in the
        HTML source. After regex capture, this becomes \\u003c (one backslash
        + u003c). The bounded decoder handles this, and JSON then converts
        \\u003c to <.
        """
        trademark = chr(0x00AE)
        # Construct with literal backslashes using chr(92)
        # This mirrors the real fixture's double-backslash JS escaping
        bs = chr(92)  # single backslash
        # In the JS string: \\u003c (two backslashes) -> captured as \\u003c
        # decoder -> \u003c -> JSON -> <
        js_content = (
            '['
            '{"skuNumber":"ESC001","title":"Product'
            + bs + bs + 'u003csup'
            + bs + bs + 'u003e'
            + bs + bs + 'u00ae'
            + bs + bs + 'u003c/sup'
            + bs + bs + 'u003e'
            '"}'
            ']'
        )
        doc = (
            '<script>\n'
            "var supportSpecsData = JSON.parse('"
            + js_content
            + "');\n"
            '</script>\n'
        )
        result = extract_enterprise_ssd_candidate_observations(
            document=doc,
            source_name=_SOURCE_NAME,
            source_url=_SOURCE_URL,
            retrieved_at=_RETRIEVED_AT,
            source_authority=_AUTHORITY,
        )
        assert len(result) == 1
        # \\u003c = <, \\u003e = >, \\u00ae = registered trademark
        assert result[0].product_name_raw == f"Product<sup>{trademark}</sup>"

    def test_literal_non_ascii_not_corrupted(self) -> None:
        """Already-literal non-ASCII characters in JSON are not corrupted
        by the decoder. The old .encode().decode(unicode_escape) would
        re-interpret UTF-8 bytes and corrupt them.
        """
        o_umlaut = chr(0x00D6)   # O with diaeresis
        a_umlaut = chr(0x00E4)   # a with diaeresis
        title_text = o_umlaut + "ffensives " + a_umlaut + "rger"
        json_record = (
            '{"skuNumber": "NLS001", "title": "' + title_text + '"}'
        )
        doc = _build_document("[" + json_record + "]")
        result = extract_enterprise_ssd_candidate_observations(
            document=doc,
            source_name=_SOURCE_NAME,
            source_url=_SOURCE_URL,
            retrieved_at=_RETRIEVED_AT,
            source_authority=_AUTHORITY,
        )
        assert len(result) == 1
        assert result[0].product_name_raw == title_text
        # Prove exact code points survived extraction
        assert result[0].product_name_raw[0] == o_umlaut
        assert result[0].product_name_raw[11] == a_umlaut


class TestSourceProvenance:
    def test_exact_source_provenance(self) -> None:
        """Observation preserves exact source provenance."""
        doc = _build_document('[{"skuNumber": "ABC123"}]')
        result = extract_enterprise_ssd_candidate_observations(
            document=doc,
            source_name=_SOURCE_NAME,
            source_url=_SOURCE_URL,
            retrieved_at=_RETRIEVED_AT,
            source_authority=_AUTHORITY,
        )
        assert result[0].source_name == _SOURCE_NAME
        assert result[0].source_url == _SOURCE_URL
        assert result[0].retrieved_at == _RETRIEVED_AT
        assert result[0].source_authority is _AUTHORITY

    def test_raw_reference_stable_and_bounded(self) -> None:
        """Raw reference is a stable bounded string, not the full payload."""
        doc = _build_document('[{"skuNumber": "ABC123"}]')
        result = extract_enterprise_ssd_candidate_observations(
            document=doc,
            source_name=_SOURCE_NAME,
            source_url=_SOURCE_URL,
            retrieved_at=_RETRIEVED_AT,
            source_authority=_AUTHORITY,
        )
        assert result[0].raw_reference is not None
        assert "embedded_json" in result[0].raw_reference
        # Should not contain the full JSON payload
        assert len(result[0].raw_reference) < 500


class TestRealSeagateFixture:
    def test_real_seagate_fixture_returns_real_record_set(self) -> None:
        """Real Seagate fixture returns the actual 81 product records."""
        import os

        fixture_path = os.path.join(
            os.path.dirname(__file__),
            "..",
            "fixtures",
            "specifications",
            "real_seagate_nytro_5050_xp15360se70005.html",
        )
        with open(fixture_path, "r", encoding="utf-8") as f:
            document = f.read()

        result = extract_enterprise_ssd_candidate_observations(
            document=document,
            source_name="Seagate Enterprise Support",
            source_url="https://www.seagate.com/support/enterprise-storage/solid-state-drives/nytro-5050/",
            retrieved_at=_RETRIEVED_AT,
            source_authority=_AUTHORITY,
        )

        assert len(result) == 81

        # Verify key MPNs are present
        mpns = {obs.manufacturer_part_number_raw for obs in result}
        assert "XP15360SE70005" in mpns  # Target
        assert "XP15360SE70015" in mpns  # Known sibling
        assert "XP3840SE70005" in mpns   # Known sibling

        # All observations must be AUTHORITATIVE
        for obs in result:
            assert obs.source_authority is SourceAuthority.AUTHORITATIVE

        # Raw MPN preserved exactly
        for obs in result:
            assert obs.manufacturer_part_number_raw.strip() == obs.manufacturer_part_number_raw
