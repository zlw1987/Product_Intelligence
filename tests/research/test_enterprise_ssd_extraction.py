"""Tests for PRODUCT-INTEL.6C — Enterprise SSD specification extraction.

Tests the pure research extraction module:
    extract_enterprise_ssd_specification_observations(...)

Mechanism: Embedded JavaScript JSON product data arrays (JSON.parse('...')).
Real evidence: Seagate Nytro 5050 support page (XP15360SE70005).

Covers:
    - Empty document -> zero observations
    - Real Seagate fixture extracts >= 1 observation
    - Exact identity record is selected (no cross-record leak)
    - Adjacent model fields cannot leak
    - Real raw value preserved exactly
    - Unknown labels ignored
    - Raw values preserved exactly
    - Locator/raw_reference preserved
    - Source name, URL, retrieved_at, authority preserved
    - Exact ProductIdentity preserved
    - Exact schema definition object preserved
    - No normalization during extraction
    - Composite values are NOT split
    - Arbitrary visible text is NOT mined
    - Malformed JSON blocks do not poison sibling blocks
    - Unestablished identity rejected
    - Canonical snake_case keys NOT accepted (only real fixture labels)

Speculative mechanisms removed (no real evidence ever demonstrated):
    - JSON-LD additionalProperty/PropertyValue pairs
    - HTML specification tables
    - HTML definition lists

Synthetic fixtures remain for testing the extraction mechanism itself,
but they use the embedded JSON structure (not JSON-LD, tables, or dl).
"""

from __future__ import annotations

from datetime import datetime, timezone

import pytest

from product_intelligence.domain.enums import IdentityMatchType
from product_intelligence.domain.models import ProductIdentity
from product_intelligence.research.enterprise_ssd import ENTERPRISE_SSD_SCHEMA
from product_intelligence.research.enterprise_ssd_extraction import (
    extract_enterprise_ssd_specification_observations,
)
from product_intelligence.research.specifications import (
    SourceAuthority,
    SpecificationObservation,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

def _identity() -> ProductIdentity:
    return ProductIdentity(
        manufacturer_part_number="MZ-QL23T800",
        match_type=IdentityMatchType.EXACT,
    )


def _seagate_identity() -> ProductIdentity:
    """Identity for the real Seagate fixture test."""
    return ProductIdentity(
        manufacturer_part_number="XP15360SE70005",
        match_type=IdentityMatchType.EXACT,
    )


def _now() -> datetime:
    return datetime(2025, 8, 20, 12, 0, 0, tzinfo=timezone.utc)


def _extract(
    document: str,
    identity: ProductIdentity | None = None,
    authority: SourceAuthority = SourceAuthority.AUTHORITATIVE,
    source_name: str = "Test Source",
) -> tuple[SpecificationObservation, ...]:
    return extract_enterprise_ssd_specification_observations(
        product_identity=identity or _identity(),
        document=document,
        source_name=source_name,
        source_url="https://example.com/requested",
        final_url="https://example.com/actual",
        retrieved_at=_now(),
        source_authority=authority,
    )


def _read_fixture(name: str) -> str:
    import os
    path = os.path.join(
        os.path.dirname(__file__),
        "..",
        "fixtures",
        "specifications",
        name,
    )
    with open(path, "r", encoding="utf-8") as f:
        return f.read()


def _make_embedded_json(
    records: list[dict],
) -> str:
    """Build a minimal HTML document with embedded JSON product data.

    Uses the same structure as the real Seagate fixture:
        var supportSpecsData = JSON.parse('[...]')

    Each record should have at minimum:
        - skuNumber: the MPN
        - features: list of {"title": label, "value": value}
    """
    import json
    json_str = json.dumps(records)
    # JS-escape the JSON string for inclusion in JSON.parse('...')
    js_escaped = json_str.replace("\\", "\\\\").replace("'", "\\'")
    return (
        '<script>\n'
        'var supportSpecsData = JSON.parse(\''
        f'{js_escaped}'
        '\');\n'
        '</script>'
    )


# ===================================================================
# A. Empty / minimal documents
# ===================================================================


class TestEmptyDocuments:
    """Empty document produces zero observations."""

    def test_empty_string(self) -> None:
        observations = _extract("")
        assert observations == ()
        assert len(observations) == 0

    def test_whitespace_only(self) -> None:
        observations = _extract("   \n\n   ")
        assert observations == ()

    def test_plain_text_no_structure(self) -> None:
        observations = _extract(
            "This product has 3.84TB capacity and NVMe interface."
        )
        assert observations == ()

    def test_arbitrary_visible_text_not_mined(self) -> None:
        """Arbitrary text mentioning TB, NVMe, GB/s etc. must NOT be mined."""
        observations = _extract(
            "<p>The new 3.84TB NVMe drive supports PCIe 4.0 x4.</p>"
            "<p>Sequential read up to 7 GB/s, random read 1M IOPS.</p>"
            "<p>Endurance rated at 1 DWPD with U.2 connector.</p>"
        )
        assert observations == ()

    def test_json_ld_not_extracted(self) -> None:
        """JSON-LD additionalProperty is NOT extracted (speculative mechanism removed)."""
        document = (
            '<script type="application/ld+json">'
            '{"@context":"https://schema.org/","@type":"Product",'
            '"additionalProperty":[{"@type":"PropertyValue",'
            '"name":"capacity","value":"3.84 TB"}]}'
            '</script>'
        )
        observations = _extract(document)
        assert observations == ()

    def test_html_table_not_extracted(self) -> None:
        """HTML tables are NOT extracted (speculative mechanism removed)."""
        document = (
            "<table>"
            "<tr><td>capacity</td><td>3.84 TB</td></tr>"
            "</table>"
        )
        observations = _extract(document)
        assert observations == ()

    def test_definition_list_not_extracted(self) -> None:
        """HTML definition lists are NOT extracted (speculative mechanism removed)."""
        document = (
            "<dl>"
            "<dt>capacity</dt><dd>3.84 TB</dd>"
            "</dl>"
        )
        observations = _extract(document)
        assert observations == ()


# ===================================================================
# B. Real Seagate fixture tests
# ===================================================================


class TestRealSeagateFixture:
    """Tests against the real Seagate Nytro 5050 fixture."""

    def _extract_seagate(self, document: str) -> tuple[SpecificationObservation, ...]:
        return _extract(document, identity=_seagate_identity())

    def test_real_fixture_extracts_at_least_one(self) -> None:
        """Real Seagate fixture extracts >= 1 observation."""
        document = _read_fixture("real_seagate_nytro_5050_xp15360se70005.html")
        observations = self._extract_seagate(document)
        assert len(observations) >= 1

    def test_real_fixture_form_factor_extracted(self) -> None:
        """Real Seagate fixture extracts Form Factor."""
        document = _read_fixture("real_seagate_nytro_5050_xp15360se70005.html")
        observations = self._extract_seagate(document)
        keys = {obs.definition.key for obs in observations}
        assert "physical_form_factor" in keys

    def test_real_fixture_raw_value_preserved(self) -> None:
        """Real raw value '2.5in' is preserved exactly."""
        document = _read_fixture("real_seagate_nytro_5050_xp15360se70005.html")
        observations = self._extract_seagate(document)
        ff_obs = [obs for obs in observations if obs.definition.key == "physical_form_factor"]
        assert len(ff_obs) >= 1
        assert ff_obs[0].raw_value == "2.5in"

    def test_real_fixture_exact_identity_selected(self) -> None:
        """Only the target MPN's record is selected."""
        document = _read_fixture("real_seagate_nytro_5050_xp15360se70005.html")
        observations = self._extract_seagate(document)
        for obs in observations:
            assert obs.product_identity.manufacturer_part_number == "XP15360SE70005"

    def test_real_fixture_adjacent_model_fields_do_not_leak(self) -> None:
        """Adjacent product records in the same fixture do not leak into
        the target record. The fixture has 81 records — only XP15360SE70005
        should contribute observations."""
        document = _read_fixture("real_seagate_nytro_5050_xp15360se70005.html")
        observations = self._extract_seagate(document)
        # All observations must be from the target identity
        for obs in observations:
            assert obs.product_identity.manufacturer_part_number == "XP15360SE70005"

    def test_real_fixture_interface_not_split(self) -> None:
        """The Interface feature value 'PCIe Gen4 x4 NVMe' is composite.
        It must NOT be split into separate storage_protocol/pcie_generation/pcie_lane_count."""
        document = _read_fixture("real_seagate_nytro_5050_xp15360se70005.html")
        observations = self._extract_seagate(document)
        # Interface is not mapped to any schema key (it's composite)
        # So it should not appear as any observation
        # Only Form Factor is mapped from the real fixture
        keys = {obs.definition.key for obs in observations}
        # storage_protocol should NOT be set from the composite Interface value
        assert "storage_protocol" not in keys
        assert "pcie_generation" not in keys
        assert "pcie_lane_count" not in keys

    def test_real_fixture_provenance_preserved(self) -> None:
        """Source provenance is correctly preserved from the real fixture."""
        document = _read_fixture("real_seagate_nytro_5050_xp15360se70005.html")
        observations = self._extract_seagate(document)
        for obs in observations:
            assert obs.source_name == "Test Source"
            assert obs.source_url == "https://example.com/actual"
            assert obs.retrieved_at == _now()
            assert obs.source_authority is SourceAuthority.AUTHORITATIVE


# ===================================================================
# C. Embedded JSON extraction (synthetic fixtures)
# ===================================================================


class TestEmbeddedJSONExtraction:
    """Test embedded JSON product data extraction with synthetic fixtures."""

    def test_basic_extraction(self) -> None:
        """Basic extraction from embedded JSON product array."""
        records = [
            {
                "skuNumber": "MZ-QL23T800",
                "title": "Test Product",
                "features": [
                    {"title": "Form Factor", "value": "2.5in"},
                    {"title": "Encryption", "value": "Standard"},
                ],
            }
        ]
        document = _make_embedded_json(records)
        observations = _extract(document)
        assert len(observations) == 1
        assert observations[0].definition.key == "physical_form_factor"
        assert observations[0].raw_value == "2.5in"

    def test_unknown_labels_ignored(self) -> None:
        """Unknown feature titles (not in schema mapping) are ignored."""
        records = [
            {
                "skuNumber": "MZ-QL23T800",
                "features": [
                    {"title": "Form Factor", "value": "2.5in"},
                    {"title": "Warranty", "value": "5 years"},
                    {"title": "Color", "value": "Black"},
                ],
            }
        ]
        document = _make_embedded_json(records)
        observations = _extract(document)
        assert len(observations) == 1
        assert observations[0].definition.key == "physical_form_factor"

    def test_malformed_json_does_not_poison(self) -> None:
        """A malformed JSON.parse block does not prevent extraction from
        a well-formed sibling block."""
        document = (
            '<script>var badData = JSON.parse(\'not valid json\');</script>'
            '<script>'
            'var supportSpecsData = JSON.parse(\''
            '[{"skuNumber":"MZ-QL23T800","features":'
            '[{"title":"Form Factor","value":"2.5in"}]}]'
            '\');'
            '</script>'
        )
        observations = _extract(document)
        assert len(observations) == 1
        assert observations[0].definition.key == "physical_form_factor"

    def test_exact_mpn_match(self) -> None:
        """Only exact MPN match selects the target record."""
        records = [
            {
                "skuNumber": "MZ-QL23T800",
                "features": [
                    {"title": "Form Factor", "value": "2.5in"},
                ],
            },
            {
                "skuNumber": "MZ-QL23T800-REV",
                "features": [
                    {"title": "Form Factor", "value": "M.2"},
                ],
            },
        ]
        document = _make_embedded_json(records)
        observations = _extract(document)
        assert len(observations) == 1
        assert observations[0].raw_value == "2.5in"

    def test_adjacent_record_fields_do_not_leak(self) -> None:
        """Fields from adjacent records in the same array do not leak."""
        records = [
            {
                "skuNumber": "MZ-QL23T800",
                "features": [
                    {"title": "Form Factor", "value": "2.5in"},
                ],
            },
            {
                "skuNumber": "OTHER-001",
                "features": [
                    {"title": "Form Factor", "value": "E3.S"},
                ],
            },
        ]
        document = _make_embedded_json(records)
        observations = _extract(document)
        assert len(observations) == 1
        assert observations[0].raw_value == "2.5in"
        assert observations[0].product_identity.manufacturer_part_number == "MZ-QL23T800"

    def test_raw_reference_preserved(self) -> None:
        """Raw reference locator is preserved."""
        records = [
            {
                "skuNumber": "MZ-QL23T800",
                "features": [
                    {"title": "Form Factor", "value": "2.5in"},
                ],
            }
        ]
        document = _make_embedded_json(records)
        observations = _extract(document)
        assert observations[0].raw_reference is not None
        assert "embedded_json" in observations[0].raw_reference
        assert "features" in observations[0].raw_reference

    def test_source_name_preserved(self) -> None:
        observations = _extract(
            _make_embedded_json([
                {"skuNumber": "MZ-QL23T800", "features": [
                    {"title": "Form Factor", "value": "2.5in"},
                ]}
            ]),
            source_name="Seagate",
        )
        assert observations[0].source_name == "Seagate"

    def test_final_url_preserved(self) -> None:
        observations = _extract(_make_embedded_json([
            {"skuNumber": "MZ-QL23T800", "features": [
                {"title": "Form Factor", "value": "2.5in"},
            ]}
        ]))
        assert observations[0].source_url == "https://example.com/actual"

    def test_retrieved_at_preserved(self) -> None:
        observations = _extract(_make_embedded_json([
            {"skuNumber": "MZ-QL23T800", "features": [
                {"title": "Form Factor", "value": "2.5in"},
            ]}
        ]))
        assert observations[0].retrieved_at == _now()

    def test_source_authority_preserved(self) -> None:
        observations = _extract(_make_embedded_json([
            {"skuNumber": "MZ-QL23T800", "features": [
                {"title": "Form Factor", "value": "2.5in"},
            ]}
        ]), authority=SourceAuthority.SECONDARY)
        assert observations[0].source_authority is SourceAuthority.SECONDARY

    def test_product_identity_preserved(self) -> None:
        identity = _identity()
        observations = extract_enterprise_ssd_specification_observations(
            product_identity=identity,
            document=_make_embedded_json([
                {"skuNumber": "MZ-QL23T800", "features": [
                    {"title": "Form Factor", "value": "2.5in"},
                ]}
            ]),
            source_name="Test",
            source_url="https://example.com",
            final_url="https://example.com",
            retrieved_at=_now(),
            source_authority=SourceAuthority.AUTHORITATIVE,
        )
        assert observations[0].product_identity is identity

    def test_definition_is_schema_object(self) -> None:
        observations = _extract(_make_embedded_json([
            {"skuNumber": "MZ-QL23T800", "features": [
                {"title": "Form Factor", "value": "2.5in"},
            ]}
        ]))
        schema_def = ENTERPRISE_SSD_SCHEMA.definitions["physical_form_factor"]
        assert observations[0].definition is schema_def

    def test_duplicate_distinct_claims_preserved(self) -> None:
        """Two features with the same title produce two observations."""
        records = [
            {
                "skuNumber": "MZ-QL23T800",
                "features": [
                    {"title": "Form Factor", "value": "2.5in"},
                    {"title": "Form Factor", "value": "E1.S"},
                ],
            }
        ]
        document = _make_embedded_json(records)
        observations = _extract(document)
        ff_obs = [o for o in observations if o.definition.key == "physical_form_factor"]
        assert len(ff_obs) == 2
        assert ff_obs[0].raw_value == "2.5in"
        assert ff_obs[1].raw_value == "E1.S"


# ===================================================================
# D. Composite values NOT split
# ===================================================================


class TestCompositeValuesNotSplit:
    """Composite values (e.g. 'PCIe Gen4 x4 NVMe') are preserved as-is.
    They are NOT split into multiple specification fields.
    """

    def test_composite_interface_not_split(self) -> None:
        """A feature with value 'PCIe Gen4 x4 NVMe' is not split."""
        records = [
            {
                "skuNumber": "MZ-QL23T800",
                "features": [
                    {"title": "Interface", "value": "PCIe Gen4 x4 NVMe"},
                ],
            }
        ]
        document = _make_embedded_json(records)
        observations = _extract(document)
        # "Interface" is not a mapped label — it has no schema key
        # (it's composite: protocol + gen + lanes, and we don't split)
        assert observations == ()

    def test_arbitrary_visible_text_not_mined(self) -> None:
        """Arbitrary HTML text is not mined for spec-like values."""
        document = (
            "<p>The Nytro 5050 series supports PCIe Gen4 x4 NVMe.</p>"
            "<p>Form Factor: 2.5-inch U.2 connector.</p>"
        )
        observations = _extract(document)
        assert observations == ()


# ===================================================================
# E. No normalization / no resolution in extraction
# ===================================================================


class TestNoNormalizationOrResolution:
    """Extraction does not normalize or resolve. It only creates raw observations."""

    def test_no_normalization_occurs(self) -> None:
        """Raw value is preserved exactly as extracted."""
        records = [
            {
                "skuNumber": "MZ-QL23T800",
                "features": [
                    {"title": "Form Factor", "value": "2.5in"},
                ],
            }
        ]
        observations = _extract(_make_embedded_json(records))
        assert observations[0].raw_value == "2.5in"

    def test_extraction_returns_raw_observations(self) -> None:
        """extract_enterprise_ssd_specification_observations returns
        SpecificationObservation (raw), not NormalizedSpecificationObservation."""
        records = [
            {
                "skuNumber": "MZ-QL23T800",
                "features": [
                    {"title": "Form Factor", "value": "2.5in"},
                ],
            }
        ]
        observations = _extract(_make_embedded_json(records))
        for obs in observations:
            assert isinstance(obs, SpecificationObservation)


# ===================================================================
# F. Provenance and identity
# ===================================================================


class TestProvenanceAndIdentity:
    """Test that all provenance fields are correctly preserved."""

    def test_source_authority_secondary(self) -> None:
        records = [
            {
                "skuNumber": "MZ-QL23T800",
                "features": [
                    {"title": "Form Factor", "value": "2.5in"},
                ],
            }
        ]
        observations = extract_enterprise_ssd_specification_observations(
            product_identity=_identity(),
            document=_make_embedded_json(records),
            source_name="Retailer",
            source_url="https://retailer.example.com/product",
            final_url="https://retailer.example.com/product-page",
            retrieved_at=_now(),
            source_authority=SourceAuthority.SECONDARY,
        )
        assert len(observations) == 1
        assert observations[0].source_authority is SourceAuthority.SECONDARY
        assert observations[0].source_name == "Retailer"

    def test_unestablished_identity_rejected(self) -> None:
        """Extraction requires established ProductIdentity."""
        unestablished = ProductIdentity(
            match_type=IdentityMatchType.UNKNOWN,
        )
        with pytest.raises(ValueError, match="established ProductIdentity"):
            extract_enterprise_ssd_specification_observations(
                product_identity=unestablished,
                document="<html></html>",
                source_name="Test",
                source_url="https://example.com",
                final_url="https://example.com",
                retrieved_at=_now(),
                source_authority=SourceAuthority.SECONDARY,
            )


# ===================================================================
# G. Speculative mechanisms removed
# ===================================================================


class TestSpeculativeMechanismsRemoved:
    """Verify that speculative extraction mechanisms are no longer present."""

    def test_json_ld_not_processed(self) -> None:
        """JSON-LD additionalProperty produces zero observations."""
        document = (
            '<script type="application/ld+json">'
            '{"@context":"https://schema.org/","@type":"Product",'
            '"additionalProperty":[{'
            '"@type":"PropertyValue","name":"capacity","value":"3.84 TB"'
            '}]}'
            '</script>'
        )
        observations = _extract(document)
        assert observations == ()

    def test_html_table_not_processed(self) -> None:
        """HTML tables produce zero observations."""
        document = (
            "<table>"
            "<tr><td>capacity</td><td>3.84 TB</td></tr>"
            "<tr><td>physical_form_factor</td><td>2.5-inch</td></tr>"
            "</table>"
        )
        observations = _extract(document)
        assert observations == ()

    def test_definition_list_not_processed(self) -> None:
        """HTML definition lists produce zero observations."""
        document = (
            "<dl>"
            "<dt>capacity</dt><dd>3.84 TB</dd>"
            "<dt>physical_form_factor</dt><dd>2.5-inch</dd>"
            "</dl>"
        )
        observations = _extract(document)
        assert observations == ()

    def test_real_samsung_page_produces_no_observations(self) -> None:
        """Real Samsung PM9A3 page still produces NO_OBSERVATIONS
        (its spec table is JS-rendered, no embedded JSON data)."""
        document = _read_fixture("real_samsung_pm9a3_mz_ql23t800.html")
        observations = _extract(document)
        assert observations == ()


# ===================================================================
# H. Structural anchoring (supportSpecsData only)
# ===================================================================


class TestStructuralAnchoring:
    """Extraction is anchored to the demonstrated structural marker:
    var supportSpecsData = JSON.parse(...)

    Only this exact variable name is accepted. Unrelated variable names
    with the same JSON structure produce zero observations.
    """

    def test_unrelated_json_parse_variable_zero_observations(self) -> None:
        """var unrelatedData = JSON.parse('[...target record...]') produces ZERO
        observations. The target skuNumber matches but the variable name
        is not supportSpecsData."""
        import json
        records = [
            {
                "skuNumber": "MZ-QL23T800",
                "features": [
                    {"title": "Form Factor", "value": "2.5in"},
                ],
            }
        ]
        json_str = json.dumps(records)
        js_escaped = json_str.replace("\\", "\\\\").replace("'", "\\'")
        document = (
            '<script>\n'
            'var unrelatedData = JSON.parse(\''
            f'{js_escaped}'
            '\');\n'
            '</script>'
        )
        observations = _extract(document)
        assert observations == ()

    def test_supportspecsdata_variable_name_extracted(self) -> None:
        """var supportSpecsData = JSON.parse('...') with exact target
        skuNumber produces the expected observations."""
        import json
        records = [
            {
                "skuNumber": "MZ-QL23T800",
                "features": [
                    {"title": "Form Factor", "value": "2.5in"},
                ],
            }
        ]
        json_str = json.dumps(records)
        js_escaped = json_str.replace("\\", "\\\\").replace("'", "\\'")
        document = (
            '<script>\n'
            'var supportSpecsData = JSON.parse(\''
            f'{js_escaped}'
            '\');\n'
            '</script>'
        )
        observations = _extract(document)
        assert len(observations) == 1
        assert observations[0].definition.key == "physical_form_factor"

    def test_malformed_json_does_not_poison(self) -> None:
        """A malformed JSON.parse block does not prevent extraction from
        a well-formed sibling block with supportSpecsData."""
        import json
        records = [
            {
                "skuNumber": "MZ-QL23T800",
                "features": [
                    {"title": "Form Factor", "value": "2.5in"},
                ],
            }
        ]
        json_str = json.dumps(records)
        js_escaped = json_str.replace("\\", "\\\\").replace("'", "\\'")
        document = (
            '<script>var badData = JSON.parse(\'not valid json\');</script>'
            '<script>'
            'var supportSpecsData = JSON.parse(\''
            f'{js_escaped}'
            '\');'
            '</script>'
        )
        observations = _extract(document)
        assert len(observations) == 1
        assert observations[0].definition.key == "physical_form_factor"

    # -- same-script assignment-binding adversarial tests --

    def test_same_script_supportspecsdata_empty_unrelated_data_with_target_rejected(self) -> None:
        """A. var supportSpecsData = JSON.parse('[]');
        var unrelatedData = JSON.parse('[...target record...]'  )

        supportSpecsData is empty. unrelatedData has the target MPN.
        Only the JSON.parse() DIRECTLY assigned to supportSpecsData
        is extracted. unrelatedData is mechanically excluded.
        """
        import json
        target_records = [
            {
                "skuNumber": "MZ-QL23T800",
                "features": [
                    {"title": "Form Factor", "value": "2.5in"},
                ],
            }
        ]
        target_json = json.dumps(target_records)
        target_escaped = target_json.replace("\\", "\\\\").replace("'", "\\'")
        document = (
            '<script>'
            'var supportSpecsData = JSON.parse(\'[]\');'
            'var unrelatedData = JSON.parse(\''
            f'{target_escaped}'
            '\');'
            '</script>'
        )
        observations = _extract(document)
        assert observations == ()

    def test_same_script_unrelated_data_first_supportspecsdata_empty_rejected(self) -> None:
        """B. var unrelatedData = JSON.parse('[...target record...]');
        var supportSpecsData = JSON.parse('[]');

        Order reversed. unrelatedData (with target) comes FIRST.
        supportSpecsData is empty.
        Result: ZERO observations (only supportSpecsData's own
        JSON.parse is captured, which is empty).
        """
        import json
        target_records = [
            {
                "skuNumber": "MZ-QL23T800",
                "features": [
                    {"title": "Form Factor", "value": "2.5in"},
                ],
            }
        ]
        target_json = json.dumps(target_records)
        target_escaped = target_json.replace("\\", "\\\\").replace("'", "\\'")
        document = (
            '<script>'
            'var unrelatedData = JSON.parse(\''
            f'{target_escaped}'
            '\');'
            'var supportSpecsData = JSON.parse(\'[]\');'
            '</script>'
        )
        observations = _extract(document)
        assert observations == ()

    def test_same_script_unrelated_data_first_supportspecsdata_with_target_accepted(self) -> None:
        """C. var unrelatedData = JSON.parse('[...unrelated...]');
        var supportSpecsData = JSON.parse('[...target record...]'  )

        unrelatedData has a non-matching MPN. supportSpecsData has the
        exact target MPN. Only supportSpecsData's JSON.parse is captured.
        Result: exactly the supportSpecsData observation.
        """
        import json
        unrelated_records = [
            {
                "skuNumber": "WRONG-MPN",
                "features": [
                    {"title": "Form Factor", "value": "M.2"},
                ],
            }
        ]
        target_records = [
            {
                "skuNumber": "MZ-QL23T800",
                "features": [
                    {"title": "Form Factor", "value": "2.5in"},
                ],
            }
        ]
        unrelated_json = json.dumps(unrelated_records)
        unrelated_escaped = unrelated_json.replace("\\", "\\\\").replace("'", "\\'")
        target_json = json.dumps(target_records)
        target_escaped = target_json.replace("\\", "\\\\").replace("'", "\\'")
        document = (
            '<script>'
            'var unrelatedData = JSON.parse(\''
            f'{unrelated_escaped}'
            '\');'
            'var supportSpecsData = JSON.parse(\''
            f'{target_escaped}'
            '\');'
            '</script>'
        )
        observations = _extract(document)
        assert len(observations) == 1
        assert observations[0].definition.key == "physical_form_factor"
        assert observations[0].raw_value == "2.5in"


# ===================================================================
# I. Raw value exact preservation
# ===================================================================


class TestRawValuePreservation:
    """Extraction preserves the exact source value without cleaning.
    Normalization (6B) handles any representation differences.
    """

    def test_leading_trailing_whitespace_preserved(self) -> None:
        """Source feature value ' 2.5in ' preserves exact whitespace.
        The extractor does NOT strip raw_value."""
        import json
        records = [
            {
                "skuNumber": "MZ-QL23T800",
                "features": [
                    {"title": "Form Factor", "value": " 2.5in "},
                ],
            }
        ]
        json_str = json.dumps(records)
        js_escaped = json_str.replace("\\", "\\\\").replace("'", "\\'")
        document = (
            '<script>\n'
            'var supportSpecsData = JSON.parse(\''
            f'{js_escaped}'
            '\');\n'
            '</script>'
        )
        observations = _extract(document)
        assert len(observations) == 1
        # Raw value preserves exact source string
        assert observations[0].raw_value == " 2.5in "

    def test_raw_value_not_stripped_by_extractor(self) -> None:
        """Extraction preserves raw_value exactly; 6B normalization
        can then normalize ' 2.5in ' (after strip) to '2.5-inch'."""
        import json
        records = [
            {
                "skuNumber": "MZ-QL23T800",
                "features": [
                    {"title": "Form Factor", "value": " 2.5in "},
                ],
            }
        ]
        json_str = json.dumps(records)
        js_escaped = json_str.replace("\\", "\\\\").replace("'", "\\'")
        document = (
            '<script>\n'
            'var supportSpecsData = JSON.parse(\''
            f'{js_escaped}'
            '\');\n'
            '</script>'
        )
        observations = _extract(document)
        assert observations[0].raw_value == " 2.5in "
        # 6B normalization would normalize this after stripping:
        from product_intelligence.research.enterprise_ssd import (
            normalize_enterprise_ssd_observation,
        )
        result = normalize_enterprise_ssd_observation(observations[0])
        # The normalizer strips before matching, so ' 2.5in ' -> '2.5in' -> '2.5-inch'
        assert result.canonical_value is not None
        assert result.canonical_value.value == "2.5-inch"
        # But the raw observation still has the original value
        assert result.observation.raw_value == " 2.5in "
