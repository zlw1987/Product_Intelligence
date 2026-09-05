"""Comprehensive tests for PRODUCT-INTEL.6B — Enterprise SSD Category Schema.

Tests schema definition, all 12 field normalizers, abstention behavior,
evidence invariants, wrong-schema rejection, and batch helper.
"""

from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
from typing import Any

import pytest

from product_intelligence.domain.enums import IdentityMatchType
from product_intelligence.domain.models import ProductIdentity
from product_intelligence.research.enterprise_ssd import (
    ENTERPRISE_SSD_SCHEMA,
    ENTERPRISE_SSD_SCHEMA_ID,
    ENTERPRISE_SSD_SCHEMA_VERSION,
    normalize_enterprise_ssd_observation,
    normalize_enterprise_ssd_observations,
)
from product_intelligence.research.specifications import (
    NormalizedSpecificationObservation,
    SpecificationDefinition,
    SpecificationObservation,
    SpecificationValue,
    SpecificationValueKind,
    SourceAuthority,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

def _identity() -> ProductIdentity:
    return ProductIdentity(
        manufacturer_part_number="MZ-QL23T8",
        match_type=IdentityMatchType.EXACT,
    )


def _now() -> datetime:
    return datetime(2025, 6, 1, 10, 0, 0, tzinfo=timezone.utc)


def _observation(definition: SpecificationDefinition, raw_value: str) -> SpecificationObservation:
    return SpecificationObservation(
        product_identity=_identity(),
        definition=definition,
        source_name="Test Source",
        source_url="https://example.com/spec",
        retrieved_at=_now(),
        raw_value=raw_value,
        source_authority=SourceAuthority.AUTHORITATIVE,
    )


def _normalize(raw_value: str, key: str) -> NormalizedSpecificationObservation:
    """Helper: build an observation from the SSD schema and normalize it."""
    defn = ENTERPRISE_SSD_SCHEMA.definitions[key]
    obs = _observation(defn, raw_value)
    return normalize_enterprise_ssd_observation(obs)


def _canonical(raw_value: str, key: str) -> Decimal | str | bool | None:
    """Helper: normalize and return the canonical value or None if issue."""
    result = _normalize(raw_value, key)
    if result.canonical_value is not None:
        return result.canonical_value.value
    return None


def _has_issue(raw_value: str, key: str) -> bool:
    """Helper: True if normalization produced an issue."""
    return _normalize(raw_value, key).normalization_issue is not None


# ===================================================================
# A. Schema contract
# ===================================================================


class TestEnterpriseSSDSchema:
    """Test Enterprise SSD schema structure and invariants."""

    def test_schema_id(self) -> None:
        assert ENTERPRISE_SSD_SCHEMA_ID == "enterprise-ssd"
        assert ENTERPRISE_SSD_SCHEMA.schema_id == "enterprise-ssd"

    def test_schema_version(self) -> None:
        assert ENTERPRISE_SSD_SCHEMA_VERSION == "1.0"
        assert ENTERPRISE_SSD_SCHEMA.schema_version == "1.0"

    def test_schema_label(self) -> None:
        assert ENTERPRISE_SSD_SCHEMA.label == "Enterprise SSD"

    def test_exact_12_keys(self) -> None:
        expected_keys = {
            "capacity",
            "storage_protocol",
            "pcie_generation",
            "pcie_lane_count",
            "physical_form_factor",
            "interface_connector",
            "sequential_read",
            "sequential_write",
            "random_read_iops",
            "random_write_iops",
            "endurance_dwpd",
            "power_loss_protection",
        }
        assert set(ENTERPRISE_SSD_SCHEMA.definitions.keys()) == expected_keys

    def test_exact_12_count(self) -> None:
        assert len(ENTERPRISE_SSD_SCHEMA.definitions) == 12

    def test_mapping_key_equals_definition_key(self) -> None:
        for key, defn in ENTERPRISE_SSD_SCHEMA.definitions.items():
            assert key == defn.key

    def test_value_kinds(self) -> None:
        expected_kinds = {
            "capacity": SpecificationValueKind.DECIMAL,
            "storage_protocol": SpecificationValueKind.ENUM,
            "pcie_generation": SpecificationValueKind.ENUM,
            "pcie_lane_count": SpecificationValueKind.DECIMAL,
            "physical_form_factor": SpecificationValueKind.ENUM,
            "interface_connector": SpecificationValueKind.TEXT,
            "sequential_read": SpecificationValueKind.DECIMAL,
            "sequential_write": SpecificationValueKind.DECIMAL,
            "random_read_iops": SpecificationValueKind.DECIMAL,
            "random_write_iops": SpecificationValueKind.DECIMAL,
            "endurance_dwpd": SpecificationValueKind.DECIMAL,
            "power_loss_protection": SpecificationValueKind.BOOLEAN,
        }
        for key, expected_kind in expected_kinds.items():
            assert (
                ENTERPRISE_SSD_SCHEMA.definitions[key].value_kind
                is expected_kind
            )

    def test_decimal_units(self) -> None:
        expected_units = {
            "capacity": "TB",
            "sequential_read": "MB/s",
            "sequential_write": "MB/s",
            "random_read_iops": "IOPS",
            "random_write_iops": "IOPS",
            "endurance_dwpd": "DWPD",
        }
        for key, expected_unit in expected_units.items():
            assert (
                ENTERPRISE_SSD_SCHEMA.definitions[key].unit == expected_unit
            )

    def test_decimal_no_unit(self) -> None:
        assert ENTERPRISE_SSD_SCHEMA.definitions["pcie_lane_count"].unit is None

    def test_enum_allowed_values_storage_protocol(self) -> None:
        allowed = ENTERPRISE_SSD_SCHEMA.definitions[
            "storage_protocol"
        ].allowed_values
        assert allowed == ("NVMe", "SATA", "SAS")

    def test_enum_allowed_values_pcie_generation(self) -> None:
        allowed = ENTERPRISE_SSD_SCHEMA.definitions[
            "pcie_generation"
        ].allowed_values
        assert allowed == ("PCIe 3.0", "PCIe 4.0", "PCIe 5.0")

    def test_enum_allowed_values_physical_form_factor(self) -> None:
        allowed = ENTERPRISE_SSD_SCHEMA.definitions[
            "physical_form_factor"
        ].allowed_values
        assert allowed == ("2.5-inch", "M.2", "E1.S", "E3.S")

    def test_text_no_unit(self) -> None:
        assert ENTERPRISE_SSD_SCHEMA.definitions["interface_connector"].unit is None

    def test_boolean_no_unit(self) -> None:
        assert (
            ENTERPRISE_SSD_SCHEMA.definitions["power_loss_protection"].unit
            is None
        )

    def test_schema_frozen_via_mapping_proxy(self) -> None:
        """The definitions mapping is immutable (MappingProxyType)."""
        with pytest.raises((TypeError, AttributeError)):
            ENTERPRISE_SSD_SCHEMA.definitions["extra"] = "no"  # type: ignore


# ===================================================================
# B. Capacity normalization
# ===================================================================


class TestCapacityNormalization:
    """capacity: TB decimal-SI normalization."""

    def test_tb_plain(self) -> None:
        assert _canonical("3.84 TB", "capacity") == Decimal("3.84")

    def test_tb_lowercase(self) -> None:
        assert _canonical("3.84 tb", "capacity") == Decimal("3.84")

    def test_gb_conversion(self) -> None:
        assert _canonical("3840 GB", "capacity") == Decimal("3.84")

    def test_gb_no_space(self) -> None:
        assert _canonical("7680GB", "capacity") == Decimal("7.68")

    def test_gb_lowercase(self) -> None:
        assert _canonical("3840 gb", "capacity") == Decimal("3.84")

    def test_tib_rejected(self) -> None:
        assert _has_issue("3.84 TiB", "capacity")

    def test_gib_rejected(self) -> None:
        assert _has_issue("3840 GiB", "capacity")

    def test_unitless_rejected(self) -> None:
        assert _has_issue("3.84", "capacity")

    def test_zero_rejected(self) -> None:
        assert _has_issue("0 TB", "capacity")

    def test_negative_rejected(self) -> None:
        assert _has_issue("-1 TB", "capacity")

    def test_empty_rejected(self) -> None:
        assert _has_issue("  ", "capacity")

    def test_whitespace_rejected(self) -> None:
        assert _has_issue("   ", "capacity")

    def test_ambiguous_range_rejected(self) -> None:
        assert _has_issue("3.84-7.68 TB", "capacity")

    def test_up_to_rejected(self) -> None:
        assert _has_issue("up to 7.68 TB", "capacity")

    def test_up_to_with_model_rejected(self) -> None:
        assert _has_issue("up to 7.68 TB depending on model", "capacity")

    def test_comma_separated_tb(self) -> None:
        assert _canonical("1,920 GB", "capacity") == Decimal("1.92")

    def test_double_value_rejected(self) -> None:
        """'3.84 TB / 7.68 TB' should be ambiguous."""
        assert _has_issue("3.84 TB / 7.68 TB", "capacity")


# ===================================================================
# C. Storage protocol normalization
# ===================================================================


class TestStorageProtocolNormalization:
    """storage_protocol: ENUM NVMe / SATA / SAS."""

    def test_nvme_upper(self) -> None:
        assert _canonical("NVMe", "storage_protocol") == "NVMe"

    def test_nvme_lower(self) -> None:
        assert _canonical("nvme", "storage_protocol") == "NVMe"

    def test_nvme_mixed(self) -> None:
        assert _canonical("Nvme", "storage_protocol") == "NVMe"

    def test_sata(self) -> None:
        assert _canonical("SATA", "storage_protocol") == "SATA"

    def test_sata_lower(self) -> None:
        assert _canonical("sata", "storage_protocol") == "SATA"

    def test_sas(self) -> None:
        assert _canonical("SAS", "storage_protocol") == "SAS"

    def test_sas_lower(self) -> None:
        assert _canonical("sas", "storage_protocol") == "SAS"

    def test_pcie_rejected(self) -> None:
        """PCIe alone is not a storage protocol."""
        assert _has_issue("PCIe", "storage_protocol")

    def test_pcie_4_0_rejected(self) -> None:
        assert _has_issue("PCIe 4.0", "storage_protocol")

    def test_u2_rejected(self) -> None:
        assert _has_issue("U.2", "storage_protocol")

    def test_u3_rejected(self) -> None:
        assert _has_issue("U.3", "storage_protocol")

    def test_compound_rejected(self) -> None:
        """'PCIe 4.0 x4 NVMe' is compound — reject."""
        assert _has_issue("PCIe 4.0 x4 NVMe", "storage_protocol")

    def test_empty_rejected(self) -> None:
        assert _has_issue("  ", "storage_protocol")


# ===================================================================
# D. PCIe generation normalization
# ===================================================================


class TestPCIeGenerationNormalization:
    """pcie_generation: ENUM PCIe 3.0 / 4.0 / 5.0."""

    def test_pcie_3_0(self) -> None:
        assert _canonical("PCIe 3.0", "pcie_generation") == "PCIe 3.0"

    def test_pcie_4_0(self) -> None:
        assert _canonical("PCIe 4.0", "pcie_generation") == "PCIe 4.0"

    def test_pcie_5_0(self) -> None:
        assert _canonical("PCIe 5.0", "pcie_generation") == "PCIe 5.0"

    def test_gen4(self) -> None:
        assert _canonical("Gen4", "pcie_generation") == "PCIe 4.0"

    def test_gen3(self) -> None:
        assert _canonical("Gen3", "pcie_generation") == "PCIe 3.0"

    def test_gen5(self) -> None:
        assert _canonical("Gen5", "pcie_generation") == "PCIe 5.0"

    def test_pci_express_4_0(self) -> None:
        assert _canonical("PCI Express 4.0", "pcie_generation") == "PCIe 4.0"

    def test_pcie_gen4(self) -> None:
        assert _canonical("PCIe Gen4", "pcie_generation") == "PCIe 4.0"

    def test_gen_4(self) -> None:
        assert _canonical("Gen 4", "pcie_generation") == "PCIe 4.0"

    def test_bare_pcie_rejected(self) -> None:
        assert _has_issue("PCIe", "pcie_generation")

    def test_high_speed_rejected(self) -> None:
        assert _has_issue("high-speed PCIe", "pcie_generation")

    def test_empty_rejected(self) -> None:
        assert _has_issue("  ", "pcie_generation")


# ===================================================================
# E. Lane count normalization
# ===================================================================


class TestLaneCountNormalization:
    """pcie_lane_count: positive whole number."""

    def test_x4(self) -> None:
        assert _canonical("x4", "pcie_lane_count") == Decimal("4")

    def test_plain_4(self) -> None:
        assert _canonical("4", "pcie_lane_count") == Decimal("4")

    def test_4_lanes(self) -> None:
        assert _canonical("4 lanes", "pcie_lane_count") == Decimal("4")

    def test_4_lane(self) -> None:
        assert _canonical("4 lane", "pcie_lane_count") == Decimal("4")

    def test_x16(self) -> None:
        assert _canonical("x16", "pcie_lane_count") == Decimal("16")

    def test_zero_rejected(self) -> None:
        assert _has_issue("0", "pcie_lane_count")

    def test_negative_rejected(self) -> None:
        assert _has_issue("-1", "pcie_lane_count")

    def test_fraction_rejected(self) -> None:
        assert _has_issue("4.5", "pcie_lane_count")

    def test_empty_rejected(self) -> None:
        assert _has_issue("  ", "pcie_lane_count")


# ===================================================================
# F. Physical form factor normalization
# ===================================================================


class TestFormFactorNormalization:
    """physical_form_factor: ENUM 2.5-inch / M.2 / E1.S / E3.S."""

    def test_2_5_inch(self) -> None:
        assert _canonical("2.5-inch", "physical_form_factor") == "2.5-inch"

    def test_2_5_quote(self) -> None:
        assert _canonical('2.5"', "physical_form_factor") == "2.5-inch"

    def test_2_5_in(self) -> None:
        assert _canonical("2.5 in", "physical_form_factor") == "2.5-inch"

    def test_2_5_in_no_space(self) -> None:
        """Real Seagate Nytro 5050 manufacturer evidence: '2.5in' (no space).
        Authorized evidence-backed corrective addition to frozen 6B.
        """
        assert _canonical("2.5in", "physical_form_factor") == "2.5-inch"

    def test_m2_lower(self) -> None:
        assert _canonical("m.2", "physical_form_factor") == "M.2"

    def test_e1s(self) -> None:
        assert _canonical("E1.S", "physical_form_factor") == "E1.S"

    def test_e1s_lower(self) -> None:
        assert _canonical("e1.s", "physical_form_factor") == "E1.S"

    def test_e3s(self) -> None:
        assert _canonical("E3.S", "physical_form_factor") == "E3.S"

    def test_e3s_lower(self) -> None:
        assert _canonical("e3.s", "physical_form_factor") == "E3.S"

    def test_u2_rejected(self) -> None:
        """U.2 is a connector, NOT a form factor."""
        assert _has_issue("U.2", "physical_form_factor")

    def test_u3_rejected(self) -> None:
        assert _has_issue("U.3", "physical_form_factor")

    def test_empty_rejected(self) -> None:
        assert _has_issue("  ", "physical_form_factor")


# ===================================================================
# G. Interface connector normalization
# ===================================================================


class TestInterfaceConnectorNormalization:
    """interface_connector: TEXT with narrow canonical spellings."""

    def test_u2_norm(self) -> None:
        assert _canonical("U.2", "interface_connector") == "U.2"

    def test_u2_variants(self) -> None:
        assert _canonical("U2", "interface_connector") == "U.2"
        assert _canonical("U-2", "interface_connector") == "U.2"

    def test_u3_norm(self) -> None:
        assert _canonical("U.3", "interface_connector") == "U.3"

    def test_u3_variants(self) -> None:
        assert _canonical("U3", "interface_connector") == "U.3"
        assert _canonical("U-3", "interface_connector") == "U.3"

    def test_m2_norm(self) -> None:
        assert _canonical("M.2", "interface_connector") == "M.2"

    def test_m2_variant(self) -> None:
        assert _canonical("M2", "interface_connector") == "M.2"

    def test_unrecognized_abstains(self) -> None:
        """Arbitrary connector string should abstain."""
        assert _has_issue("SFF-8639", "interface_connector")

    def test_unrecognized_sff_abstains(self) -> None:
        assert _has_issue("SFF-8654", "interface_connector")

    def test_empty_rejected(self) -> None:
        assert _has_issue("  ", "interface_connector")


# ===================================================================
# H. Sequential read/write normalization
# ===================================================================


class TestSequentialReadNormalization:
    """sequential_read: MB/s decimal-SI."""

    def test_mbs(self) -> None:
        assert _canonical("6800 MB/s", "sequential_read") == Decimal("6800")

    def test_gbs_conversion(self) -> None:
        assert _canonical("6.8 GB/s", "sequential_read") == Decimal("6800")

    def test_gbs_plain(self) -> None:
        assert _canonical("7 GB/s", "sequential_read") == Decimal("7000")

    def test_mbs_no_space(self) -> None:
        assert _canonical("6800MB/s", "sequential_read") == Decimal("6800")

    def test_comma_mbs(self) -> None:
        assert _canonical("7,500 MB/s", "sequential_read") == Decimal("7500")

    def test_mib_rejected(self) -> None:
        assert _has_issue("7000 MiB/s", "sequential_read")

    def test_gib_rejected(self) -> None:
        assert _has_issue("7 GiB/s", "sequential_read")

    def test_unitless_rejected(self) -> None:
        assert _has_issue("6800", "sequential_read")

    def test_zero_rejected(self) -> None:
        assert _has_issue("0 MB/s", "sequential_read")

    def test_negative_rejected(self) -> None:
        assert _has_issue("-100 MB/s", "sequential_read")

    def test_range_rejected(self) -> None:
        assert _has_issue("6800-7000 MB/s", "sequential_read")

    def test_empty_rejected(self) -> None:
        assert _has_issue("  ", "sequential_read")


class TestSequentialWriteNormalization:
    """sequential_write: same semantics as sequential_read."""

    def test_mbs(self) -> None:
        assert _canonical("5200 MB/s", "sequential_write") == Decimal("5200")

    def test_gbs(self) -> None:
        assert _canonical("5.2 GB/s", "sequential_write") == Decimal("5200")


# ===================================================================
# I. Random IOPS normalization
# ===================================================================


class TestRandomReadIopsNormalization:
    """random_read_iops: IOPS with K/M SI multipliers."""

    def test_plain_iops(self) -> None:
        assert _canonical("1000000 IOPS", "random_read_iops") == Decimal("1000000")

    def test_comma_iops(self) -> None:
        assert _canonical("1,000,000 IOPS", "random_read_iops") == Decimal("1000000")

    def test_k_iops(self) -> None:
        assert _canonical("1000K IOPS", "random_read_iops") == Decimal("1000000")

    def test_m_iops(self) -> None:
        assert _canonical("1M IOPS", "random_read_iops") == Decimal("1000000")

    def test_plain_no_unit_rejected(self) -> None:
        """Plain number without IOPS token is rejected (IOPS token required)."""
        assert _has_issue("1000000", "random_read_iops")

    def test_k_no_unit_rejected(self) -> None:
        """K multiplier without IOPS token is rejected."""
        assert _has_issue("1000K", "random_read_iops")

    def test_m_no_unit_rejected(self) -> None:
        """M multiplier without IOPS token is rejected."""
        assert _has_issue("1M", "random_read_iops")

    def test_zero_rejected(self) -> None:
        assert _has_issue("0 IOPS", "random_read_iops")

    def test_negative_rejected(self) -> None:
        assert _has_issue("-100 IOPS", "random_read_iops")

    def test_range_rejected(self) -> None:
        assert _has_issue("900000-1000000 IOPS", "random_read_iops")

    def test_empty_rejected(self) -> None:
        assert _has_issue("  ", "random_read_iops")


class TestRandomWriteIopsNormalization:
    """random_write_iops: same semantics."""

    def test_plain_iops(self) -> None:
        assert _canonical("800000 IOPS", "random_write_iops") == Decimal("800000")

    def test_m_iops(self) -> None:
        assert _canonical("800K IOPS", "random_write_iops") == Decimal("800000")


# ===================================================================
# J. DWPD normalization
# ===================================================================


class TestDWPDNormalization:
    """endurance_dwpd: positive finite Decimal."""

    def test_dwpd(self) -> None:
        assert _canonical("1 DWPD", "endurance_dwpd") == Decimal("1")

    def test_dwpd_float(self) -> None:
        assert _canonical("1.0 DWPD", "endurance_dwpd") == Decimal("1.0")

    def test_dwpd_high(self) -> None:
        assert _canonical("3 DWPD", "endurance_dwpd") == Decimal("3")

    def test_plain_numeric(self) -> None:
        """Plain numeric is accepted because field implies DWPD."""
        assert _canonical("1", "endurance_dwpd") == Decimal("1")

    def test_plain_0_5(self) -> None:
        assert _canonical("0.5", "endurance_dwpd") == Decimal("0.5")

    def test_zero_rejected(self) -> None:
        assert _has_issue("0 DWPD", "endurance_dwpd")

    def test_negative_rejected(self) -> None:
        assert _has_issue("-1 DWPD", "endurance_dwpd")

    def test_tbw_rejected(self) -> None:
        """TBW is not derivable to DWPD."""
        assert _has_issue("3.84 PB TBW", "endurance_dwpd")

    def test_pbw_rejected(self) -> None:
        """PBW is not derivable to DWPD."""
        assert _has_issue("3.84 PBW", "endurance_dwpd")

    def test_warranty_years_rejected(self) -> None:
        """Years are not DWPD."""
        assert _has_issue("5 years", "endurance_dwpd")

    def test_empty_rejected(self) -> None:
        assert _has_issue("  ", "endurance_dwpd")


# ===================================================================
# K. Power loss protection normalization
# ===================================================================


class TestPowerLossProtectionNormalization:
    """power_loss_protection: explicit boolean only."""

    # TRUE forms
    def test_yes(self) -> None:
        assert _canonical("yes", "power_loss_protection") is True

    def test_true(self) -> None:
        assert _canonical("true", "power_loss_protection") is True

    def test_supported(self) -> None:
        assert _canonical("supported", "power_loss_protection") is True

    def test_enabled(self) -> None:
        assert _canonical("enabled", "power_loss_protection") is True

    def test_yes_upper(self) -> None:
        assert _canonical("YES", "power_loss_protection") is True

    def test_true_upper(self) -> None:
        assert _canonical("TRUE", "power_loss_protection") is True

    # FALSE forms
    def test_no(self) -> None:
        assert _canonical("no", "power_loss_protection") is False

    def test_false(self) -> None:
        assert _canonical("false", "power_loss_protection") is False

    def test_not_supported(self) -> None:
        assert _canonical("not supported", "power_loss_protection") is False

    def test_disabled(self) -> None:
        assert _canonical("disabled", "power_loss_protection") is False

    # Prose rejected
    def test_prose_rejected(self) -> None:
        assert _has_issue(
            "Enterprise SSD with advanced power-loss circuitry",
            "power_loss_protection",
        )

    def test_maybe_rejected(self) -> None:
        assert _has_issue("maybe", "power_loss_protection")

    def test_empty_rejected(self) -> None:
        assert _has_issue("  ", "power_loss_protection")


# ===================================================================
# L. Evidence invariants
# ===================================================================


class TestEvidenceInvariants:
    """Original observation is preserved; provenance unchanged."""

    def _build_obs(self, key: str, raw_value: str) -> SpecificationObservation:
        return _observation(
            ENTERPRISE_SSD_SCHEMA.definitions[key],
            raw_value,
        )

    def test_original_observation_preserved(self) -> None:
        obs = self._build_obs("capacity", "3.84 TB")
        result = normalize_enterprise_ssd_observation(obs)
        assert result.observation is obs
        assert result.canonical_value.value == Decimal("3.84")

    def test_identity_preserved(self) -> None:
        obs = self._build_obs("capacity", "3.84 TB")
        result = normalize_enterprise_ssd_observation(obs)
        assert result.observation.product_identity is obs.product_identity

    def test_definition_preserved(self) -> None:
        obs = self._build_obs("capacity", "3.84 TB")
        result = normalize_enterprise_ssd_observation(obs)
        assert result.observation.definition is obs.definition

    def test_source_name_preserved(self) -> None:
        obs = self._build_obs("capacity", "3.84 TB")
        result = normalize_enterprise_ssd_observation(obs)
        assert result.observation.source_name == "Test Source"

    def test_source_url_preserved(self) -> None:
        obs = self._build_obs("capacity", "3.84 TB")
        result = normalize_enterprise_ssd_observation(obs)
        assert result.observation.source_url == "https://example.com/spec"

    def test_retrieved_at_preserved(self) -> None:
        obs = self._build_obs("capacity", "3.84 TB")
        result = normalize_enterprise_ssd_observation(obs)
        assert result.observation.retrieved_at == _now()

    def test_source_authority_preserved(self) -> None:
        obs = self._build_obs("capacity", "3.84 TB")
        result = normalize_enterprise_ssd_observation(obs)
        assert result.observation.source_authority is SourceAuthority.AUTHORITATIVE

    def test_raw_value_preserved(self) -> None:
        obs = self._build_obs("capacity", "  3.84 TB  ")
        result = normalize_enterprise_ssd_observation(obs)
        # raw_value is preserved exactly as stored by SpecificationObservation
        assert result.observation.raw_value == "  3.84 TB  "

    def test_issue_path_preserves_observation(self) -> None:
        obs = self._build_obs("capacity", "TiB only")
        result = normalize_enterprise_ssd_observation(obs)
        assert result.observation is obs
        assert result.normalization_issue is not None
        assert result.canonical_value is None


# ===================================================================
# M. Wrong schema / definition rejection
# ===================================================================


class TestWrongDefinitionRejection:
    """Observations from other schemas must be rejected."""

    def test_independent_definition_rejected(self) -> None:
        """Same key but independently constructed definition -> reject.

        Even with EXACTLY the same fields (key, label, value_kind, unit),
        an independently-constructed definition is rejected because
        schema membership requires exact object identity, not value equality.
        """
        # Value-equal clone of the actual schema capacity definition
        other_def = SpecificationDefinition(
            key="capacity",
            label="Capacity",
            value_kind=SpecificationValueKind.DECIMAL,
            unit="TB",
        )
        obs = SpecificationObservation(
            product_identity=_identity(),
            definition=other_def,
            source_name="x",
            source_url="https://x.com",
            retrieved_at=_now(),
            raw_value="3.84",
            source_authority=SourceAuthority.SECONDARY,
        )
        with pytest.raises(ValueError, match="does not belong to"):
            normalize_enterprise_ssd_observation(obs)

    def test_value_equal_clone_rejected(self) -> None:
        """Value-equal clone of capacity definition MUST be rejected.

        Clone with EXACTLY identical fields (key, label, value_kind, unit,
        allowed_values) to ENTERPRISE_SSD_SCHEMA.definitions['capacity'].
        Must fail because identity check is required, not value equality.
        """
        real_def = ENTERPRISE_SSD_SCHEMA.definitions["capacity"]
        clone_def = SpecificationDefinition(
            key=real_def.key,
            label=real_def.label,
            value_kind=real_def.value_kind,
            unit=real_def.unit,
            allowed_values=real_def.allowed_values,
        )
        # Verify they are value-equal but not identity-equal
        assert clone_def == real_def, "clone must be value-equal to real definition"
        assert clone_def is not real_def, "clone must not be identity-equal"

        obs = SpecificationObservation(
            product_identity=_identity(),
            definition=clone_def,
            source_name="x",
            source_url="https://x.com",
            retrieved_at=_now(),
            raw_value="3.84 TB",
            source_authority=SourceAuthority.SECONDARY,
        )
        with pytest.raises(ValueError, match="does not belong to"):
            normalize_enterprise_ssd_observation(obs)

    def test_real_schema_definition_accepted(self) -> None:
        """The actual schema definition object MUST be accepted."""
        real_def = ENTERPRISE_SSD_SCHEMA.definitions["capacity"]
        obs = SpecificationObservation(
            product_identity=_identity(),
            definition=real_def,
            source_name="x",
            source_url="https://x.com",
            retrieved_at=_now(),
            raw_value="3.84 TB",
            source_authority=SourceAuthority.SECONDARY,
        )
        result = normalize_enterprise_ssd_observation(obs)
        assert result.canonical_value is not None
        assert result.canonical_value.value == Decimal("3.84")

    def test_unrelated_definition_rejected(self) -> None:
        """Definition from a different schema -> reject."""
        other_def = SpecificationDefinition(
            key="cpu_clock_speed",
            label="Clock Speed",
            value_kind=SpecificationValueKind.DECIMAL,
            unit="GHz",
        )
        obs = SpecificationObservation(
            product_identity=_identity(),
            definition=other_def,
            source_name="x",
            source_url="https://x.com",
            retrieved_at=_now(),
            raw_value="3.2",
            source_authority=SourceAuthority.SECONDARY,
        )
        with pytest.raises(ValueError, match="does not belong to"):
            normalize_enterprise_ssd_observation(obs)

    def test_non_observaton_type_rejected(self) -> None:
        with pytest.raises(TypeError, match="must be a SpecificationObservation"):
            normalize_enterprise_ssd_observation("not an observation")  # type: ignore


# ===================================================================
# N. Batch helper
# ===================================================================


class TestBatchHelper:
    """normalize_enterprise_ssd_observations: order, no mutation."""

    def test_order_preserved(self) -> None:
        obs1 = _observation(
            ENTERPRISE_SSD_SCHEMA.definitions["capacity"], "3.84 TB"
        )
        obs2 = _observation(
            ENTERPRISE_SSD_SCHEMA.definitions["storage_protocol"], "NVMe"
        )
        results = normalize_enterprise_ssd_observations((obs1, obs2))
        assert len(results) == 2
        assert results[0].canonical_value.value == Decimal("3.84")
        assert results[1].canonical_value.value == "NVMe"

    def test_tuple_in_tuple_out(self) -> None:
        obs = _observation(
            ENTERPRISE_SSD_SCHEMA.definitions["capacity"], "3.84 TB"
        )
        results = normalize_enterprise_ssd_observations((obs,))
        assert isinstance(results, tuple)

    def test_empty_tuple(self) -> None:
        results = normalize_enterprise_ssd_observations(())
        assert results == ()

    def test_non_tuple_raises(self) -> None:
        with pytest.raises(TypeError, match="must be a tuple"):
            normalize_enterprise_ssd_observations([])  # type: ignore

    def test_caller_error_propagates(self) -> None:
        """If one observation has a wrong definition, it raises."""
        good = _observation(
            ENTERPRISE_SSD_SCHEMA.definitions["capacity"], "3.84 TB"
        )
        bad = SpecificationObservation(
            product_identity=_identity(),
            definition=SpecificationDefinition(
                key="other",
                label="Other",
                value_kind=SpecificationValueKind.TEXT,
            ),
            source_name="x",
            source_url="https://x.com",
            retrieved_at=_now(),
            raw_value="val",
            source_authority=SourceAuthority.SECONDARY,
        )
        with pytest.raises(ValueError, match="does not belong to"):
            normalize_enterprise_ssd_observations((good, bad))

    def test_mixed_canonical_and_issue(self) -> None:
        """Batch can contain both successful and failed normalizations."""
        cap_ok = _observation(
            ENTERPRISE_SSD_SCHEMA.definitions["capacity"], "3.84 TB"
        )
        cap_bad = _observation(
            ENTERPRISE_SSD_SCHEMA.definitions["capacity"], "TiB"
        )
        results = normalize_enterprise_ssd_observations((cap_ok, cap_bad))
        assert len(results) == 2
        assert results[0].canonical_value is not None
        assert results[1].normalization_issue is not None


# ===================================================================
# O. Adversarial composite values
# ===================================================================


class TestAdversarialCompositeValues:
    """Composite/ambiguous values should abstain, not be parsed."""

    def test_capacity_range(self) -> None:
        assert _has_issue("3.84 TB / 7.68 TB", "capacity")

    def test_capacity_up_to(self) -> None:
        assert _has_issue("up to 7.68 TB", "capacity")

    def test_pcie_4_0_x4_nvme_as_protocol(self) -> None:
        """'PCIe 4.0 x4 NVMe' as protocol -> reject."""
        assert _has_issue("PCIe 4.0 x4 NVMe", "storage_protocol")

    def test_u3_nvme_as_protocol(self) -> None:
        assert _has_issue("U.3 NVMe", "storage_protocol")

    def test_2_5_inch_u3_as_form_factor(self) -> None:
        """'2.5-inch U.3' as form factor -> reject (composite)."""
        assert _has_issue("2.5-inch U.3", "physical_form_factor")

    def test_1_dwpd_5_years(self) -> None:
        """'1 DWPD (5 years)' -> reject (extra qualifier)."""
        assert _has_issue("1 DWPD (5 years)", "endurance_dwpd")

    def test_throughput_range(self) -> None:
        assert _has_issue("6800-7000 MB/s", "sequential_read")

    def test_iops_range(self) -> None:
        assert _has_issue("900000-1000000 IOPS", "random_read_iops")

    def test_capacity_or_variants(self) -> None:
        """'3.84 TB or 7.68 TB' -> ambiguous."""
        assert _has_issue("3.84 TB or 7.68 TB", "capacity")


# ===================================================================
# P. Strict numeric comma grouping
# ===================================================================


class TestStrictNumericCommaGrouping:
    """Adversarial tests for malformed comma grouping in numeric fields."""

    # --- capacity ---
    def test_capacity_malformed_comma_384_tb(self) -> None:
        """'3,84 TB' has 2-digit group after comma -> rejected."""
        assert _has_issue("3,84 TB", "capacity")

    def test_capacity_malformed_comma_123_gb(self) -> None:
        """'1,23 GB' has 2-digit group after comma -> rejected."""
        assert _has_issue("1,23 GB", "capacity")

    def test_capacity_malformed_comma_12_3_tb(self) -> None:
        """'1,2,3 TB' has irregular grouping -> rejected."""
        assert _has_issue("1,2,3 TB", "capacity")

    def test_capacity_valid_comma_1000_gb(self) -> None:
        """'1,000 GB' is valid 3-digit grouping -> accepted."""
        assert _canonical("1,000 GB", "capacity") == Decimal("1")

    def test_capacity_valid_comma_1234567_gb(self) -> None:
        """'1,234,567 GB' is valid -> accepted."""
        assert _canonical("1,234,567 GB", "capacity") == Decimal("1234.567")

    # --- sequential_read ---
    def test_throughput_malformed_68_mbs(self) -> None:
        """'6,8 MB/s' has 1-digit group after comma -> rejected."""
        assert _has_issue("6,8 MB/s", "sequential_read")

    def test_throughput_malformed_1_000_00_mbs(self) -> None:
        """'1,000,00 MB/s' has 2-digit final group -> rejected."""
        assert _has_issue("1,000,00 MB/s", "sequential_read")

    def test_throughput_valid_7500_mbs(self) -> None:
        """'7,500 MB/s' is valid -> accepted."""
        assert _canonical("7,500 MB/s", "sequential_read") == Decimal("7500")

    # --- sequential_write ---
    def test_sequential_write_malformed_comma(self) -> None:
        """'5,2 MB/s' -> rejected."""
        assert _has_issue("5,2 MB/s", "sequential_write")

    # --- random_read_iops ---
    def test_iops_malformed_15M_IOPS(self) -> None:
        """'1,5M IOPS' has 1-digit group after comma -> rejected."""
        assert _has_issue("1,5M IOPS", "random_read_iops")

    def test_iops_malformed_1000_00_IOPS(self) -> None:
        """'1,000,00 IOPS' has 2-digit final group -> rejected."""
        assert _has_issue("1,000,00 IOPS", "random_read_iops")

    def test_iops_malformed_double_comma(self) -> None:
        """'1,,000 MB/s' -> empty group rejected."""
        assert _has_issue("1,,000 MB/s", "sequential_read")

    def test_iops_valid_1M_IOPS(self) -> None:
        """'1M IOPS' -> accepted as 1000000."""
        assert _canonical("1M IOPS", "random_read_iops") == Decimal("1000000")

    def test_iops_valid_1000000_IOPS(self) -> None:
        """'1,000,000 IOPS' -> accepted as 1000000."""
        assert _canonical("1,000,000 IOPS", "random_read_iops") == Decimal("1000000")

    # --- random_write_iops ---
    def test_random_write_iops_malformed_comma(self) -> None:
        """'8,00K IOPS' -> rejected."""
        assert _has_issue("8,00K IOPS", "random_write_iops")

    # --- endurance_dwpd ---
    def test_dwpd_malformed_15_dwpd(self) -> None:
        """'1,5 DWPD' has 1-digit group -> rejected."""
        assert _has_issue("1,5 DWPD", "endurance_dwpd")

    def test_dwpd_malformed_1_dwpd(self) -> None:
        """'1, DWPD' -> empty group -> rejected."""
        assert _has_issue("1, DWPD", "endurance_dwpd")

    def test_dwpd_valid_plain(self) -> None:
        """'1' -> accepted as plain numeric."""
        assert _canonical("1", "endurance_dwpd") == Decimal("1")

    def test_dwpd_valid_0_5(self) -> None:
        """'0.5' -> accepted."""
        assert _canonical("0.5", "endurance_dwpd") == Decimal("0.5")


# ===================================================================
# Q. Negative / zero OUT_OF_RANGE classification
# ===================================================================


class TestNegativeZeroOutOfRange:
    """Values <= 0 are classified as OUT_OF_RANGE_OR_NON_POSITIVE."""

    def test_capacity_negative_issue_code(self) -> None:
        """'-1 TB' produces OUT_OF_RANGE_OR_NON_POSITIVE."""
        result = _normalize("-1 TB", "capacity")
        assert result.normalization_issue is not None
        assert "OUT_OF_RANGE_OR_NON_POSITIVE" in result.normalization_issue

    def test_capacity_zero_issue_code(self) -> None:
        """'0 TB' produces OUT_OF_RANGE_OR_NON_POSITIVE."""
        result = _normalize("0 TB", "capacity")
        assert result.normalization_issue is not None
        assert "OUT_OF_RANGE_OR_NON_POSITIVE" in result.normalization_issue

    def test_throughput_negative_issue_code(self) -> None:
        """'-100 MB/s' produces OUT_OF_RANGE_OR_NON_POSITIVE."""
        result = _normalize("-100 MB/s", "sequential_read")
        assert result.normalization_issue is not None
        assert "OUT_OF_RANGE_OR_NON_POSITIVE" in result.normalization_issue

    def test_iops_negative_issue_code(self) -> None:
        """'-100 IOPS' produces OUT_OF_RANGE_OR_NON_POSITIVE."""
        result = _normalize("-100 IOPS", "random_read_iops")
        assert result.normalization_issue is not None
        assert "OUT_OF_RANGE_OR_NON_POSITIVE" in result.normalization_issue

    def test_dwpd_negative_issue_code(self) -> None:
        """'-1 DWPD' produces OUT_OF_RANGE_OR_NON_POSITIVE."""
        result = _normalize("-1 DWPD", "endurance_dwpd")
        assert result.normalization_issue is not None
        assert "OUT_OF_RANGE_OR_NON_POSITIVE" in result.normalization_issue

    def test_iops_zero_issue_code(self) -> None:
        """'0 IOPS' produces OUT_OF_RANGE_OR_NON_POSITIVE."""
        result = _normalize("0 IOPS", "random_read_iops")
        assert result.normalization_issue is not None
        assert "OUT_OF_RANGE_OR_NON_POSITIVE" in result.normalization_issue

    def test_dwpd_zero_issue_code(self) -> None:
        """'0 DWPD' produces OUT_OF_RANGE_OR_NON_POSITIVE."""
        result = _normalize("0 DWPD", "endurance_dwpd")
        assert result.normalization_issue is not None
        assert "OUT_OF_RANGE_OR_NON_POSITIVE" in result.normalization_issue


# ===================================================================
# R. IOPS explicit unit required
# ===================================================================


class TestIopsExplicitUnitRequired:
    """IOPS field requires explicit 'IOPS' unit token."""

    def test_unitless_plain_rejected(self) -> None:
        """'1000000' without IOPS token -> issue."""
        assert _has_issue("1000000", "random_read_iops")

    def test_unitless_k_rejected(self) -> None:
        """'1000K' without IOPS token -> issue."""
        assert _has_issue("1000K", "random_read_iops")

    def test_unitless_m_rejected(self) -> None:
        """'1M' without IOPS token -> issue."""
        assert _has_issue("1M", "random_read_iops")

    def test_with_unit_accepted(self) -> None:
        """'1000000 IOPS' -> accepted."""
        assert _canonical("1000000 IOPS", "random_read_iops") == Decimal("1000000")

    def test_with_unit_comma_accepted(self) -> None:
        """'1,000,000 IOPS' -> accepted."""
        assert _canonical("1,000,000 IOPS", "random_read_iops") == Decimal("1000000")

    def test_with_unit_k_accepted(self) -> None:
        """'1000K IOPS' -> accepted."""
        assert _canonical("1000K IOPS", "random_read_iops") == Decimal("1000000")

    def test_with_unit_m_accepted(self) -> None:
        """'1M IOPS' -> accepted."""
        assert _canonical("1M IOPS", "random_read_iops") == Decimal("1000000")

    def test_write_unitless_rejected(self) -> None:
        """Write IOPS also requires unit token."""
        assert _has_issue("800000", "random_write_iops")

    def test_write_with_unit_accepted(self) -> None:
        """Write IOPS with unit -> accepted."""
        assert _canonical("800000 IOPS", "random_write_iops") == Decimal("800000")


# ===================================================================
# S. Final adversarial proof
# ===================================================================


class TestFinalAdversarialProof:
    """Direct proof of every adversarial case from the 6B corrective closure."""

    def test_clone_of_capacity_rejected(self) -> None:
        """Clone of capacity definition with identical fields -> rejected."""
        real_def = ENTERPRISE_SSD_SCHEMA.definitions["capacity"]
        clone_def = SpecificationDefinition(
            key=real_def.key,
            label=real_def.label,
            value_kind=real_def.value_kind,
            unit=real_def.unit,
            allowed_values=real_def.allowed_values,
        )
        obs = SpecificationObservation(
            product_identity=_identity(),
            definition=clone_def,
            source_name="x",
            source_url="https://x.com",
            retrieved_at=_now(),
            raw_value="3.84 TB",
            source_authority=SourceAuthority.SECONDARY,
        )
        with pytest.raises(ValueError, match="does not belong to"):
            normalize_enterprise_ssd_observation(obs)

    def test_real_schema_capacity_accepted(self) -> None:
        """Real ENTERPRISE_SSD_SCHEMA capacity definition -> accepted."""
        result = _normalize("3.84 TB", "capacity")
        assert result.canonical_value.value == Decimal("3.84")

    def test_384_TB_issue(self) -> None:
        """'3,84 TB' -> issue (malformed comma grouping)."""
        assert _has_issue("3,84 TB", "capacity")

    def test_68_GB_s_issue(self) -> None:
        """'6,8 GB/s' -> issue (malformed comma grouping)."""
        assert _has_issue("6,8 GB/s", "sequential_read")

    def test_15M_IOPS_issue(self) -> None:
        """'1,5M IOPS' -> issue (malformed comma grouping)."""
        assert _has_issue("1,5M IOPS", "random_read_iops")

    def test_15_DWPD_issue(self) -> None:
        """'1,5 DWPD' -> issue (malformed comma grouping)."""
        assert _has_issue("1,5 DWPD", "endurance_dwpd")

    def test_1000000_IOPS_accepted(self) -> None:
        """'1,000,000 IOPS' -> 1000000."""
        assert _canonical("1,000,000 IOPS", "random_read_iops") == Decimal("1000000")

    def test_1M_IOPS_accepted(self) -> None:
        """'1M IOPS' -> 1000000."""
        assert _canonical("1M IOPS", "random_read_iops") == Decimal("1000000")

    def test_unitless_1000000_IOPS_issue(self) -> None:
        """'1000000' -> issue for IOPS (missing unit token)."""
        assert _has_issue("1000000", "random_read_iops")

    def test_unitless_1000K_IOPS_issue(self) -> None:
        """'1000K' -> issue for IOPS (missing unit token)."""
        assert _has_issue("1000K", "random_read_iops")

    def test_plain_1_DWPD_accepted(self) -> None:
        """'1' -> still accepted for DWPD (plain numeric exception)."""
        assert _canonical("1", "endurance_dwpd") == Decimal("1")
