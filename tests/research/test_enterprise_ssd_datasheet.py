"""Tests for the enterprise SSD datasheet table interpretation (PRODUCT-INTEL.6D — research layer).

Adversarial coverage for MPN -> table -> column -> row binding.
Bounded model-row grammar. Bounded spec-row grammar.
Global MPN uniqueness. Raw MPN exactness.
"""

import pytest
from datetime import datetime, timezone
from product_intelligence.domain.enums import IdentityMatchType
from product_intelligence.domain.models import ProductIdentity
from product_intelligence.research.enterprise_ssd_datasheet import (
    extract_datasheet_observations,
    extract_datasheet_observations_from_document,
    _ROW_GRAMMAR,
    _ALLOWED_SCHEMA_KEYS,
    _normalize_label,
    _resolve_row_label,
    _find_mpn_column,
    _find_mpn_column_global,
    _incorporate_row_unit,
    _is_model_row,
)
from product_intelligence.research.specifications import SourceAuthority


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

RETRIEVED_AT = datetime(2025, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
SOURCE_URL = "https://www.seagate.com/datasheet.pdf"


def _make_identity(mpn: str) -> ProductIdentity:
    return ProductIdentity(
        manufacturer=None,
        manufacturer_part_number=mpn,
        match_type=IdentityMatchType.EXACT,
    )


# Realistic Seagate-style table (Nytro 5350H page)
REALISTIC_TABLE: list[list[str | None]] = [
    ["Specifications", "Nytro 5350H 15mm—Read Intensive", "", "", ""],
    ["Capacity", "15.36TB", "7.68TB", "3.84TB", "1.92TB"],
    ["Standard Model", "XP15360SE70005", "XP7680SE70005", "XP3840SE70005", "XP1920SE70005"],
    ["SED Model1", "XP15360SE70015", "XP7680SE70015", "XP3840SE70015", "XP1920SE70015"],
    ["FIPS 140-3/Common Criteria Model1", "XP15360SE70025", "XP7680SE70025", "XP3840SE70025", "XP1920SE70025"],
    ["Features", "", "", "", ""],
    ["Interface (Single Port)", "-", "-", "-", "-"],
    ["Interface (Dual Port)", "PCIe Gen4 x4 NVMe", "PCIe Gen4 x4 NVMe", "PCIe Gen4 x4 NVMe", "PCIe Gen4 x4 NVMe"],
    ["Form Factor", "2.5 in × 15mm", "2.5 in × 15mm", "2.5 in × 15mm", "2.5 in × 15mm"],
    ["Performance", "", "", "", ""],
    ["Sequential Read (MB/s) Sustained, 128KB2", "7400MB/s", "7400MB/s", "7400MB/s", "7400MB/s"],
    ["Sequential Write (MB/s) Sustained, 128KB2", "7200", "7200", "6900", "3700"],
    ["Random Read (IOPS) Sustained, 4KB3", "1,700,000", "1,700,000", "1,700,000", "1,550,000"],
    ["Random Write (IOPS) Sustained, 4KB3", "195,000", "195,000", "195,000", "125,000"],
    ["Endurance/Reliability", "", "", "", ""],
    ["Lifetime Endurance (Drive Writes per Day)", "1", "1", "1", "1"],
]


# ---------------------------------------------------------------------------
# Six-field allowlist
# ---------------------------------------------------------------------------

class TestSixFieldAllowlist:
    def test_allowlist_size(self) -> None:
        assert len(_ALLOWED_SCHEMA_KEYS) == 6

    def test_all_six_present(self) -> None:
        expected = {"capacity", "sequential_read", "sequential_write",
                     "random_read_iops", "random_write_iops", "endurance_dwpd"}
        assert _ALLOWED_SCHEMA_KEYS == expected

    def test_physical_form_factor_not_in_allowlist(self) -> None:
        assert "physical_form_factor" not in _ALLOWED_SCHEMA_KEYS


# ---------------------------------------------------------------------------
# Row label normalization
# ---------------------------------------------------------------------------

class TestNormalizeLabel:
    def test_stripping(self) -> None:
        assert _normalize_label("  Capacity  ") == "capacity"

    def test_collapse_whitespace(self) -> None:
        assert _normalize_label("Sequential   Read") == "sequential read"

    def test_preserves_internal_chars(self) -> None:
        assert _normalize_label("Sequential Read (MB/s)") == "sequential read (mb/s)"


# ---------------------------------------------------------------------------
# Row label resolution (bounded grammar)
# ---------------------------------------------------------------------------

class TestResolveRowLabel:
    def test_capacity_matches(self) -> None:
        result = _resolve_row_label("Capacity")
        assert result is not None
        assert result[1] == "capacity"

    def test_sequential_read_exact(self) -> None:
        result = _resolve_row_label("Sequential Read (MB/s) Sustained, 128KB2")
        assert result is not None
        assert result[1] == "sequential_read"

    def test_sequential_write_exact(self) -> None:
        result = _resolve_row_label("Sequential Write (MB/s) Sustained, 128KB2")
        assert result is not None
        assert result[1] == "sequential_write"

    def test_random_read_exact(self) -> None:
        result = _resolve_row_label("Random Read (IOPS) Sustained, 4KB3")
        assert result is not None
        assert result[1] == "random_read_iops"

    def test_random_write_exact(self) -> None:
        result = _resolve_row_label("Random Write (IOPS) Sustained, 4KB3")
        assert result is not None
        assert result[1] == "random_write_iops"

    def test_lifetime_endurance_exact(self) -> None:
        result = _resolve_row_label("Lifetime Endurance (Drive Writes per Day)")
        assert result is not None
        assert result[1] == "endurance_dwpd"

    # Negative tests — semantically adjacent rows must NOT match
    def test_random_read_latency_no_match(self) -> None:
        assert _resolve_row_label("Random Read Latency") is None

    def test_random_write_latency_no_match(self) -> None:
        assert _resolve_row_label("Random Write Latency") is None

    def test_sequential_read_latency_no_match(self) -> None:
        assert _resolve_row_label("Sequential Read Latency") is None

    def test_sequential_write_endurance_no_match(self) -> None:
        assert _resolve_row_label("Sequential Write Endurance") is None

    def test_capacity_utilization_no_match(self) -> None:
        assert _resolve_row_label("Capacity Utilization") is None

    def test_unknown_row_returns_none(self) -> None:
        assert _resolve_row_label("NAND Flash Type") is None

    def test_form_factor_not_mapped(self) -> None:
        assert _resolve_row_label("Form Factor") is None


# ---------------------------------------------------------------------------
# Model row detection — bounded grammar
# ---------------------------------------------------------------------------

class TestIsModelRow:
    def test_standard_model(self) -> None:
        assert _is_model_row("Standard Model")

    def test_sed_model_with_footnote(self) -> None:
        assert _is_model_row("SED Model1")

    def test_fips_model(self) -> None:
        assert _is_model_row("FIPS 140-3/Common Criteria Model1")

    def test_capacity_not_model(self) -> None:
        assert not _is_model_row("Capacity")

    def test_sequential_read_not_model(self) -> None:
        assert not _is_model_row("Sequential Read (MB/s)")

    # Adversarial — must NOT match
    def test_recommended_model_not_model(self) -> None:
        assert not _is_model_row("Recommended Model")

    def test_controller_model_not_model(self) -> None:
        assert not _is_model_row("Controller Model")

    def test_model_notes_not_model(self) -> None:
        assert not _is_model_row("Model Notes")

    def test_model_description_not_model(self) -> None:
        assert not _is_model_row("Model Description")

    def test_model_number_not_model(self) -> None:
        assert not _is_model_row("Model Number")

    def test_model_family_not_model(self) -> None:
        assert not _is_model_row("Model Family")


# ---------------------------------------------------------------------------
# Unit incorporation
# ---------------------------------------------------------------------------

class TestIncorporateRowUnit:
    def test_unit_already_present(self) -> None:
        assert _incorporate_row_unit("7400MB/s", "MB/s") == "7400MB/s"

    def test_unit_not_present_appended(self) -> None:
        assert _incorporate_row_unit("7200", "MB/s") == "7200 MB/s"

    def test_iops_unit_not_present(self) -> None:
        assert _incorporate_row_unit("1,700,000", "IOPS") == "1,700,000 IOPS"

    def test_no_unit_mapping(self) -> None:
        assert _incorporate_row_unit("15.36TB", None) == "15.36TB"

    def test_empty_cell(self) -> None:
        assert _incorporate_row_unit("", "MB/s") == ""


# ---------------------------------------------------------------------------
# MPN -> column binding (single table)
# ---------------------------------------------------------------------------

class TestFindMpnColumn:
    def test_standard_model_mpn(self) -> None:
        loc = _find_mpn_column(REALISTIC_TABLE, "XP15360SE70005")
        assert loc is not None
        row_idx, col_idx = loc
        assert row_idx == 2
        assert col_idx == 1

    def test_sed_model_mpn(self) -> None:
        loc = _find_mpn_column(REALISTIC_TABLE, "XP15360SE70015")
        assert loc is not None
        assert loc[0] == 3
        assert loc[1] == 1

    def test_different_capacity_mpn(self) -> None:
        loc = _find_mpn_column(REALISTIC_TABLE, "XP3840SE70005")
        assert loc is not None
        assert loc[0] == 2
        assert loc[1] == 3

    def test_mpn_not_found(self) -> None:
        assert _find_mpn_column(REALISTIC_TABLE, "NONEXISTENT123") is None

    def test_ambiguous_mpn_raises(self) -> None:
        table = [
            ["Standard Model", "XP123", "XP123"],
        ]
        with pytest.raises(ValueError, match="found ambiguously"):
            _find_mpn_column(table, "XP123")

    # Raw MPN exactness — whitespace-mutated MPN must NOT match
    def test_whitespace_mutated_mpn_no_match(self) -> None:
        """MPN cell with leading/trailing space must not match."""
        table = [
            ["Standard Model", " XP15360SE70005", "XP3840SE70005"],
        ]
        loc = _find_mpn_column(table, "XP15360SE70005")
        assert loc is None  # Cell is " XP15360SE70005" != "XP15360SE70005"


# ---------------------------------------------------------------------------
# Global MPN uniqueness
# ---------------------------------------------------------------------------

class TestFindMpnColumnGlobal:
    def test_mpn_in_one_table(self) -> None:
        tables = [
            (0, 0, REALISTIC_TABLE),
        ]
        loc = _find_mpn_column_global(tables, "XP15360SE70005")
        assert loc is not None
        # Returns (list_index, page_idx, table_idx, row_idx, col_idx)
        assert loc == (0, 0, 0, 2, 1)

    def test_mpn_absent_everywhere(self) -> None:
        tables = [
            (0, 0, REALISTIC_TABLE),
        ]
        assert _find_mpn_column_global(tables, "NONEXISTENT999") is None

    def test_mpn_twice_in_one_table_raises(self) -> None:
        table = [
            ["Standard Model", "XP123", "XP123"],
            ["Capacity", "1TB", "2TB"],
        ]
        with pytest.raises(ValueError, match="ambiguous"):
            _find_mpn_column_global([(0, 0, table)], "XP123")

    def test_mpn_once_each_in_two_tables_raises(self) -> None:
        table1 = [
            ["Standard Model", "XP123", "XP456"],
            ["Capacity", "1TB", "2TB"],
        ]
        table2 = [
            ["Standard Model", "XP789", "XP123"],
            ["Capacity", "4TB", "8TB"],
        ]
        with pytest.raises(ValueError, match="globally"):
            _find_mpn_column_global([(0, 0, table1), (0, 1, table2)], "XP123")

    def test_mpn_on_two_pages_raises(self) -> None:
        table1 = [
            ["Standard Model", "XP123"],
            ["Capacity", "1TB"],
        ]
        table2 = [
            ["Standard Model", "XP123"],
            ["Capacity", "2TB"],
        ]
        with pytest.raises(ValueError, match="globally"):
            _find_mpn_column_global([(0, 0, table1), (1, 0, table2)], "XP123")

    def test_unrelated_tables_ignored(self) -> None:
        """Tables without the target MPN do not interfere."""
        unrelated_table = [
            ["Product", "Other Drive"],
            ["Capacity", "16TB"],
        ]
        tables = [
            (0, 0, unrelated_table),
            (0, 1, REALISTIC_TABLE),
        ]
        loc = _find_mpn_column_global(tables, "XP15360SE70005")
        assert loc is not None
        assert loc == (1, 0, 1, 2, 1)


# ---------------------------------------------------------------------------
# Full extraction — correct MPN selects correct column
# ---------------------------------------------------------------------------

class TestExtractObservationsTarget:
    """XP15360SE70005 selects column 1 (15.36TB)."""

    def test_six_observations(self) -> None:
        identity = _make_identity("XP15360SE70005")
        obs = extract_datasheet_observations(
            product_identity=identity,
            table=REALISTIC_TABLE,
            table_page=0, table_index=0,
            source_name="Seagate Datasheet",
            source_url=SOURCE_URL,
            retrieved_at=RETRIEVED_AT,
            source_authority=SourceAuthority.AUTHORITATIVE,
        )
        assert len(obs) == 6

    def test_capacity(self) -> None:
        obs = extract_datasheet_observations(
            product_identity=_make_identity("XP15360SE70005"),
            table=REALISTIC_TABLE,
            table_page=0, table_index=0,
            source_name="Seagate Datasheet",
            source_url=SOURCE_URL,
            retrieved_at=RETRIEVED_AT,
            source_authority=SourceAuthority.AUTHORITATIVE,
        )
        capacity_obs = [o for o in obs if o.definition.key == "capacity"]
        assert len(capacity_obs) == 1
        assert capacity_obs[0].raw_value == "15.36TB"

    def test_sequential_read(self) -> None:
        obs = extract_datasheet_observations(
            product_identity=_make_identity("XP15360SE70005"),
            table=REALISTIC_TABLE,
            table_page=0, table_index=0,
            source_name="Seagate Datasheet",
            source_url=SOURCE_URL,
            retrieved_at=RETRIEVED_AT,
            source_authority=SourceAuthority.AUTHORITATIVE,
        )
        sr = [o for o in obs if o.definition.key == "sequential_read"]
        assert sr[0].raw_value == "7400MB/s"

    def test_sequential_write_unit_incorporated(self) -> None:
        obs = extract_datasheet_observations(
            product_identity=_make_identity("XP15360SE70005"),
            table=REALISTIC_TABLE,
            table_page=0, table_index=0,
            source_name="Seagate Datasheet",
            source_url=SOURCE_URL,
            retrieved_at=RETRIEVED_AT,
            source_authority=SourceAuthority.AUTHORITATIVE,
        )
        sw = [o for o in obs if o.definition.key == "sequential_write"]
        assert sw[0].raw_value == "7200 MB/s"

    def test_random_read_iops_unit_incorporated(self) -> None:
        obs = extract_datasheet_observations(
            product_identity=_make_identity("XP15360SE70005"),
            table=REALISTIC_TABLE,
            table_page=0, table_index=0,
            source_name="Seagate Datasheet",
            source_url=SOURCE_URL,
            retrieved_at=RETRIEVED_AT,
            source_authority=SourceAuthority.AUTHORITATIVE,
        )
        rri = [o for o in obs if o.definition.key == "random_read_iops"]
        assert rri[0].raw_value == "1,700,000 IOPS"

    def test_endurance_dwpd(self) -> None:
        obs = extract_datasheet_observations(
            product_identity=_make_identity("XP15360SE70005"),
            table=REALISTIC_TABLE,
            table_page=0, table_index=0,
            source_name="Seagate Datasheet",
            source_url=SOURCE_URL,
            retrieved_at=RETRIEVED_AT,
            source_authority=SourceAuthority.AUTHORITATIVE,
        )
        dw = [o for o in obs if o.definition.key == "endurance_dwpd"]
        assert dw[0].raw_value == "1"


# ---------------------------------------------------------------------------
# Full extraction — SED model
# ---------------------------------------------------------------------------

class TestExtractObservationsSedModel:
    def test_sed_same_values_as_standard(self) -> None:
        standard_obs = extract_datasheet_observations(
            product_identity=_make_identity("XP15360SE70005"),
            table=REALISTIC_TABLE,
            table_page=0, table_index=0,
            source_name="Seagate Datasheet",
            source_url=SOURCE_URL,
            retrieved_at=RETRIEVED_AT,
            source_authority=SourceAuthority.AUTHORITATIVE,
        )
        sed_obs = extract_datasheet_observations(
            product_identity=_make_identity("XP15360SE70015"),
            table=REALISTIC_TABLE,
            table_page=0, table_index=0,
            source_name="Seagate Datasheet",
            source_url=SOURCE_URL,
            retrieved_at=RETRIEVED_AT,
            source_authority=SourceAuthority.AUTHORITATIVE,
        )
        for std, sed in zip(standard_obs, sed_obs):
            assert std.definition.key == sed.definition.key
            assert std.raw_value == sed.raw_value


# ---------------------------------------------------------------------------
# Full extraction — different capacity
# ---------------------------------------------------------------------------

class TestExtractObservationsDifferentCapacity:
    def test_different_capacity(self) -> None:
        obs = extract_datasheet_observations(
            product_identity=_make_identity("XP3840SE70005"),
            table=REALISTIC_TABLE,
            table_page=0, table_index=0,
            source_name="Seagate Datasheet",
            source_url=SOURCE_URL,
            retrieved_at=RETRIEVED_AT,
            source_authority=SourceAuthority.AUTHORITATIVE,
        )
        capacity_obs = [o for o in obs if o.definition.key == "capacity"]
        assert capacity_obs[0].raw_value == "3.84TB"

    def test_different_sequential_write(self) -> None:
        obs = extract_datasheet_observations(
            product_identity=_make_identity("XP3840SE70005"),
            table=REALISTIC_TABLE,
            table_page=0, table_index=0,
            source_name="Seagate Datasheet",
            source_url=SOURCE_URL,
            retrieved_at=RETRIEVED_AT,
            source_authority=SourceAuthority.AUTHORITATIVE,
        )
        sw = [o for o in obs if o.definition.key == "sequential_write"]
        assert sw[0].raw_value == "6900 MB/s"


# ---------------------------------------------------------------------------
# Column isolation
# ---------------------------------------------------------------------------

class TestColumnIsolation:
    def test_no_column_1_to_column_3_leak(self) -> None:
        obs = extract_datasheet_observations(
            product_identity=_make_identity("XP3840SE70005"),
            table=REALISTIC_TABLE,
            table_page=0, table_index=0,
            source_name="Seagate Datasheet",
            source_url=SOURCE_URL,
            retrieved_at=RETRIEVED_AT,
            source_authority=SourceAuthority.AUTHORITATIVE,
        )
        capacity_obs = [o for o in obs if o.definition.key == "capacity"]
        assert capacity_obs[0].raw_value == "3.84TB"


# ---------------------------------------------------------------------------
# Abstention
# ---------------------------------------------------------------------------

class TestAbstention:
    def test_mpn_not_found_returns_empty(self) -> None:
        obs = extract_datasheet_observations(
            product_identity=_make_identity("NONEXISTENT999"),
            table=REALISTIC_TABLE,
            table_page=0, table_index=0,
            source_name="Seagate Datasheet",
            source_url=SOURCE_URL,
            retrieved_at=RETRIEVED_AT,
            source_authority=SourceAuthority.AUTHORITATIVE,
        )
        assert obs == []

    def test_no_mpn_raises(self) -> None:
        identity = ProductIdentity(
            manufacturer_part_number=None,
            match_type=IdentityMatchType.UNKNOWN,
        )
        with pytest.raises(ValueError, match="requires an established"):
            extract_datasheet_observations(
                product_identity=identity,
                table=REALISTIC_TABLE,
                table_page=0, table_index=0,
                source_name="Seagate Datasheet",
                source_url=SOURCE_URL,
                retrieved_at=RETRIEVED_AT,
                source_authority=SourceAuthority.AUTHORITATIVE,
            )


# ---------------------------------------------------------------------------
# Ambiguous MPN
# ---------------------------------------------------------------------------

class TestAmbiguousMpn:
    def test_duplicate_mpn_raises(self) -> None:
        table = [
            ["Standard Model", "XP123", "XP123"],
            ["Capacity", "1TB", "2TB"],
        ]
        with pytest.raises(ValueError, match="found ambiguously"):
            _find_mpn_column(table, "XP123")


# ---------------------------------------------------------------------------
# Unknown row ignored
# ---------------------------------------------------------------------------

class TestUnknownRowIgnored:
    def test_only_six_fields_extracted(self) -> None:
        obs = extract_datasheet_observations(
            product_identity=_make_identity("XP15360SE70005"),
            table=REALISTIC_TABLE,
            table_page=0, table_index=0,
            source_name="Seagate Datasheet",
            source_url=SOURCE_URL,
            retrieved_at=RETRIEVED_AT,
            source_authority=SourceAuthority.AUTHORITATIVE,
        )
        keys = {o.definition.key for o in obs}
        assert keys == _ALLOWED_SCHEMA_KEYS


# ---------------------------------------------------------------------------
# Missing row does not shift columns
# ---------------------------------------------------------------------------

class TestMissingRowDoesNotShiftColumns:
    def test_missing_sequential_write(self) -> None:
        table = [row for row in REALISTIC_TABLE if "Sequential Write" not in (row[0] or "")]
        obs = extract_datasheet_observations(
            product_identity=_make_identity("XP15360SE70005"),
            table=table,
            table_page=0, table_index=0,
            source_name="Seagate Datasheet",
            source_url=SOURCE_URL,
            retrieved_at=RETRIEVED_AT,
            source_authority=SourceAuthority.AUTHORITATIVE,
        )
        keys = {o.definition.key for o in obs}
        assert "sequential_write" not in keys
        capacity = [o for o in obs if o.definition.key == "capacity"]
        assert capacity[0].raw_value == "15.36TB"


# ---------------------------------------------------------------------------
# No Interface splitting
# ---------------------------------------------------------------------------

class TestNoInterfaceSplitting:
    def test_interface_row_not_extracted(self) -> None:
        obs = extract_datasheet_observations(
            product_identity=_make_identity("XP15360SE70005"),
            table=REALISTIC_TABLE,
            table_page=0, table_index=0,
            source_name="Seagate Datasheet",
            source_url=SOURCE_URL,
            retrieved_at=RETRIEVED_AT,
            source_authority=SourceAuthority.AUTHORITATIVE,
        )
        keys = {o.definition.key for o in obs}
        assert "storage_protocol" not in keys


# ---------------------------------------------------------------------------
# Raw evidence preserved
# ---------------------------------------------------------------------------

class TestRawEvidencePreserved:
    def test_raw_value_not_stripped(self) -> None:
        """Prove that commas and structural formatting survive."""
        obs = extract_datasheet_observations(
            product_identity=_make_identity("XP15360SE70005"),
            table=REALISTIC_TABLE,
            table_page=0, table_index=0,
            source_name="Seagate Datasheet",
            source_url=SOURCE_URL,
            retrieved_at=RETRIEVED_AT,
            source_authority=SourceAuthority.AUTHORITATIVE,
        )
        rri = [o for o in obs if o.definition.key == "random_read_iops"]
        assert rri[0].raw_value == "1,700,000 IOPS"

    def test_raw_reference_identifies_structure(self) -> None:
        obs = extract_datasheet_observations(
            product_identity=_make_identity("XP15360SE70005"),
            table=REALISTIC_TABLE,
            table_page=2, table_index=1,
            source_name="Seagate Datasheet",
            source_url=SOURCE_URL,
            retrieved_at=RETRIEVED_AT,
            source_authority=SourceAuthority.AUTHORITATIVE,
        )
        for o in obs:
            assert o.raw_reference is not None
            assert "pdf_page[2]" in o.raw_reference
            assert "table1" in o.raw_reference


# ---------------------------------------------------------------------------
# Raw cell fidelity — whitespace preserved
# ---------------------------------------------------------------------------

class TestRawCellFidelity:
    def test_raw_value_with_whitespace(self) -> None:
        """Prove that leading/trailing whitespace in cells is preserved."""
        table = [
            ["Standard Model", "XP123"],
            ["Capacity", " 15.36TB "],
            ["Sequential Read (MB/s) Sustained, 128KB2", " 7400MB/s "],
        ]
        obs = extract_datasheet_observations(
            product_identity=_make_identity("XP123"),
            table=table,
            table_page=0, table_index=0,
            source_name="Test",
            source_url=SOURCE_URL,
            retrieved_at=RETRIEVED_AT,
            source_authority=SourceAuthority.AUTHORITATIVE,
        )
        # The raw_value should preserve the actual cell text
        capacity = [o for o in obs if o.definition.key == "capacity"]
        assert capacity[0].raw_value == " 15.36TB "
        sr = [o for o in obs if o.definition.key == "sequential_read"]
        assert sr[0].raw_value == " 7400MB/s "


# ---------------------------------------------------------------------------
# Identity and definition bindings
# ---------------------------------------------------------------------------

class TestIdentityAndDefinitionBindings:
    def test_product_identity_binding(self) -> None:
        identity = _make_identity("XP15360SE70005")
        obs = extract_datasheet_observations(
            product_identity=identity,
            table=REALISTIC_TABLE,
            table_page=0, table_index=0,
            source_name="Seagate Datasheet",
            source_url=SOURCE_URL,
            retrieved_at=RETRIEVED_AT,
            source_authority=SourceAuthority.AUTHORITATIVE,
        )
        for o in obs:
            assert o.product_identity is identity

    def test_definition_binding(self) -> None:
        obs = extract_datasheet_observations(
            product_identity=_make_identity("XP15360SE70005"),
            table=REALISTIC_TABLE,
            table_page=0, table_index=0,
            source_name="Seagate Datasheet",
            source_url=SOURCE_URL,
            retrieved_at=RETRIEVED_AT,
            source_authority=SourceAuthority.AUTHORITATIVE,
        )
        from product_intelligence.research.enterprise_ssd import ENTERPRISE_SSD_SCHEMA
        for o in obs:
            schema_def = ENTERPRISE_SSD_SCHEMA.definitions.get(o.definition.key)
            assert schema_def is o.definition


# ---------------------------------------------------------------------------
# Whole-document extraction (global MPN uniqueness)
# ---------------------------------------------------------------------------

class TestWholeDocumentExtraction:
    def test_mpn_in_one_of_two_tables(self) -> None:
        table1 = [
            ["Standard Model", "OTHER1", "OTHER2"],
            ["Capacity", "1TB", "2TB"],
        ]
        table2 = REALISTIC_TABLE
        obs = extract_datasheet_observations_from_document(
            product_identity=_make_identity("XP15360SE70005"),
            all_tables=[(0, 0, table1), (0, 1, table2)],
            source_name="Seagate Datasheet",
            source_url=SOURCE_URL,
            retrieved_at=RETRIEVED_AT,
            source_authority=SourceAuthority.AUTHORITATIVE,
        )
        assert len(obs) == 6

    def test_mpn_in_both_tables_raises(self) -> None:
        table1 = [
            ["Standard Model", "XP15360SE70005", "OTHER"],
            ["Capacity", "1TB", "2TB"],
            ["Sequential Read (MB/s) Sustained, 128KB2", "5000MB/s"],
        ]
        table2 = REALISTIC_TABLE
        with pytest.raises(ValueError, match="globally"):
            extract_datasheet_observations_from_document(
                product_identity=_make_identity("XP15360SE70005"),
                all_tables=[(0, 0, table1), (0, 1, table2)],
                source_name="Seagate Datasheet",
                source_url=SOURCE_URL,
                retrieved_at=RETRIEVED_AT,
                source_authority=SourceAuthority.AUTHORITATIVE,
            )
