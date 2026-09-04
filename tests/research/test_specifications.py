"""Comprehensive tests for PRODUCT-INTEL.6A — Product Specification Framework.

Tests all seven canonical contracts and the resolver:
    SpecificationDefinition, SpecificationValue, SpecificationObservation,
    NormalizedSpecificationObservation, SpecificationResolution,
    CategorySchema, ProductSpecificationSet, resolve_specification()

Coverage areas:
A. Definition contracts
B. Identity binding
C. Observation
D. Normalized observation
E. Resolution
F. ProductSpecificationSet
G. Immutability / deterministic behaviour
"""

from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
from typing import Any

import pytest

from product_intelligence.domain.enums import IdentityMatchType
from product_intelligence.domain.models import ProductIdentity
from product_intelligence.research.specifications import (
    CategorySchema,
    NormalizedSpecificationObservation,
    ProductSpecificationSet,
    ResolutionState,
    SourceAuthority,
    SpecificationDefinition,
    SpecificationObservation,
    SpecificationResolution,
    SpecificationValue,
    SpecificationValueKind,
    resolve_specification,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


def _established_identity_exact() -> ProductIdentity:
    """A ProductIdentity with EXACT match — established."""
    return ProductIdentity(
        manufacturer_part_number="ABC-123",
        match_type=IdentityMatchType.EXACT,
    )


def _established_identity_normalized() -> ProductIdentity:
    """A ProductIdentity with NORMALIZED_EXACT match — established."""
    return ProductIdentity(
        manufacturer_part_number="ABC-123",
        normalized_part_number="ABC-123",
        match_type=IdentityMatchType.NORMALIZED_EXACT,
    )


def _unestablished_identity_unknown() -> ProductIdentity:
    """A ProductIdentity with UNKNOWN match — not established."""
    return ProductIdentity(
        match_type=IdentityMatchType.UNKNOWN,
    )


def _unestablished_identity_partial() -> ProductIdentity:
    """A ProductIdentity with PARTIAL match — not established."""
    return ProductIdentity(
        manufacturer_part_number="ABC",
        match_type=IdentityMatchType.PARTIAL,
    )


def _unestablished_identity_description_only() -> ProductIdentity:
    """A ProductIdentity with DESCRIPTION_ONLY match — not established."""
    return ProductIdentity(
        product_name="Some Product",
        match_type=IdentityMatchType.DESCRIPTION_ONLY,
    )


def _now_aware() -> datetime:
    return datetime(2025, 1, 15, 12, 0, 0, tzinfo=timezone.utc)


def _capacity_definition() -> SpecificationDefinition:
    return SpecificationDefinition(
        key="capacity",
        label="Storage Capacity",
        value_kind=SpecificationValueKind.DECIMAL,
        unit="TB",
    )


def _interface_definition() -> SpecificationDefinition:
    return SpecificationDefinition(
        key="interface",
        label="Interface Connector",
        value_kind=SpecificationValueKind.TEXT,
    )


def _form_factor_definition() -> SpecificationDefinition:
    return SpecificationDefinition(
        key="form_factor",
        label="Form Factor",
        value_kind=SpecificationValueKind.ENUM,
        allowed_values=("2.5\"", "M.2", "U.2"),
    )


def _nvme_support_definition() -> SpecificationDefinition:
    return SpecificationDefinition(
        key="nvme_support",
        label="NVMe Support",
        value_kind=SpecificationValueKind.BOOLEAN,
    )


# ===================================================================
# A. Definition contracts
# ===================================================================


class TestSpecificationDefinition:
    """Test SpecificationDefinition construction and validation."""

    # --- All four valid kinds ---

    def test_text_definition(self) -> None:
        defn = SpecificationDefinition(
            key="name", label="Name", value_kind=SpecificationValueKind.TEXT
        )
        assert defn.key == "name"
        assert defn.label == "Name"
        assert defn.value_kind is SpecificationValueKind.TEXT
        assert defn.unit is None
        assert defn.allowed_values == ()

    def test_decimal_definition_with_unit(self) -> None:
        defn = SpecificationDefinition(
            key="capacity",
            label="Capacity",
            value_kind=SpecificationValueKind.DECIMAL,
            unit="TB",
        )
        assert defn.value_kind is SpecificationValueKind.DECIMAL
        assert defn.unit == "TB"

    def test_boolean_definition(self) -> None:
        defn = SpecificationDefinition(
            key="enabled",
            label="Enabled",
            value_kind=SpecificationValueKind.BOOLEAN,
        )
        assert defn.value_kind is SpecificationValueKind.BOOLEAN
        assert defn.unit is None
        assert defn.allowed_values == ()

    def test_enum_definition_with_allowed_values(self) -> None:
        defn = SpecificationDefinition(
            key="color",
            label="Color",
            value_kind=SpecificationValueKind.ENUM,
            allowed_values=("RED", "GREEN", "BLUE"),
        )
        assert defn.value_kind is SpecificationValueKind.ENUM
        assert defn.allowed_values == ("RED", "GREEN", "BLUE")

    # --- Invalid kind ---

    def test_invalid_value_kind_raises(self) -> None:
        with pytest.raises(TypeError, match="value_kind must be a SpecificationValueKind"):
            SpecificationDefinition(
                key="x", label="X", value_kind="NOT_A_KIND"  # type: ignore
            )

    # --- DECIMAL accepts Decimal, rejects float ---

    def test_decimal_definition_validates_decimal(self) -> None:
        defn = _capacity_definition()
        assert defn.validate_canonical_value(Decimal("3.84")) is True

    def test_decimal_definition_rejects_float(self) -> None:
        defn = _capacity_definition()
        assert defn.validate_canonical_value(3.84) is False

    def test_decimal_definition_rejects_int(self) -> None:
        defn = _capacity_definition()
        assert defn.validate_canonical_value(4) is False

    def test_decimal_definition_rejects_string(self) -> None:
        defn = _capacity_definition()
        assert defn.validate_canonical_value("3.84") is False

    # --- Non-finite Decimal rejected ---

    def test_decimal_definition_rejects_nan(self) -> None:
        """NaN is a Decimal but is not finite — must be rejected."""
        defn = _capacity_definition()
        assert defn.validate_canonical_value(Decimal("NaN")) is False

    def test_decimal_definition_rejects_snan(self) -> None:
        """sNaN is a Decimal but is not finite — must be rejected."""
        defn = _capacity_definition()
        assert defn.validate_canonical_value(Decimal("sNaN")) is False

    def test_decimal_definition_rejects_positive_infinity(self) -> None:
        """Infinity is a Decimal but is not finite — must be rejected."""
        defn = _capacity_definition()
        assert defn.validate_canonical_value(Decimal("Infinity")) is False

    def test_decimal_definition_rejects_negative_infinity(self) -> None:
        """-Infinity is a Decimal but is not finite — must be rejected."""
        defn = _capacity_definition()
        assert defn.validate_canonical_value(Decimal("-Infinity")) is False

    def test_decimal_definition_accepts_negative_finite(self) -> None:
        """Negative finite Decimal is accepted (negative values are a
        category/schema concern, not a generic 6A concern)."""
        defn = _capacity_definition()
        assert defn.validate_canonical_value(Decimal("-1.5")) is True

    def test_decimal_definition_accepts_zero(self) -> None:
        defn = _capacity_definition()
        assert defn.validate_canonical_value(Decimal("0")) is True

    def test_decimal_definition_accepts_finite(self) -> None:
        defn = _capacity_definition()
        assert defn.validate_canonical_value(Decimal("123456789.0123456789")) is True

    # --- BOOLEAN type enforcement ---

    def test_boolean_definition_validates_true(self) -> None:
        defn = _nvme_support_definition()
        assert defn.validate_canonical_value(True) is True

    def test_boolean_definition_validates_false(self) -> None:
        defn = _nvme_support_definition()
        assert defn.validate_canonical_value(False) is True

    def test_boolean_definition_rejects_integer_1(self) -> None:
        """1 is truthy but not a bool in Python."""
        defn = _nvme_support_definition()
        assert defn.validate_canonical_value(1) is False

    def test_boolean_definition_rejects_integer_0(self) -> None:
        defn = _nvme_support_definition()
        assert defn.validate_canonical_value(0) is False

    def test_boolean_definition_rejects_string(self) -> None:
        defn = _nvme_support_definition()
        assert defn.validate_canonical_value("true") is False

    # --- ENUM valid / invalid member ---

    def test_enum_definition_validates_valid_member(self) -> None:
        defn = _form_factor_definition()
        assert defn.validate_canonical_value("M.2") is True

    def test_enum_definition_validates_each_member(self) -> None:
        defn = _form_factor_definition()
        for v in defn.allowed_values:
            assert defn.validate_canonical_value(v) is True

    def test_enum_definition_rejects_invalid_member(self) -> None:
        defn = _form_factor_definition()
        assert defn.validate_canonical_value("3.5\"") is False

    def test_enum_definition_rejects_empty_string(self) -> None:
        defn = _form_factor_definition()
        assert defn.validate_canonical_value("") is False

    # --- Unit semantics ---

    def test_decimal_definition_no_unit(self) -> None:
        defn = SpecificationDefinition(
            key="ratio",
            label="Ratio",
            value_kind=SpecificationValueKind.DECIMAL,
        )
        assert defn.unit is None

    def test_unit_stripped(self) -> None:
        defn = SpecificationDefinition(
            key="x", label="X", value_kind=SpecificationValueKind.DECIMAL, unit=" TB "
        )
        assert defn.unit == "TB"

    # --- Malformed definition configuration ---

    def test_empty_key_raises(self) -> None:
        with pytest.raises(ValueError, match="key must be a non-empty string"):
            SpecificationDefinition(
                key="", label="Label", value_kind=SpecificationValueKind.TEXT
            )

    def test_whitespace_key_raises(self) -> None:
        with pytest.raises(ValueError, match="key must be a non-empty string"):
            SpecificationDefinition(
                key="  ", label="Label", value_kind=SpecificationValueKind.TEXT
            )

    def test_empty_label_raises(self) -> None:
        with pytest.raises(ValueError, match="label must be a non-empty string"):
            SpecificationDefinition(
                key="x", label="", value_kind=SpecificationValueKind.TEXT
            )

    def test_non_string_key_raises(self) -> None:
        with pytest.raises(ValueError, match="key must be a non-empty string"):
            SpecificationDefinition(
                key=123, label="Label", value_kind=SpecificationValueKind.TEXT  # type: ignore
            )

    def test_empty_unit_raises(self) -> None:
        with pytest.raises(ValueError, match="unit must be a non-empty string"):
            SpecificationDefinition(
                key="x", label="X", value_kind=SpecificationValueKind.DECIMAL, unit=""
            )

    def test_non_string_unit_raises(self) -> None:
        """42 is not a string, so it raises ValueError from the unit check."""
        with pytest.raises(ValueError, match="unit must be a non-empty string"):
            SpecificationDefinition(
                key="x", label="X", value_kind=SpecificationValueKind.DECIMAL, unit=42  # type: ignore
            )

    def test_enum_without_allowed_values_raises(self) -> None:
        with pytest.raises(ValueError, match="ENUM specification requires"):
            SpecificationDefinition(
                key="x",
                label="X",
                value_kind=SpecificationValueKind.ENUM,
                allowed_values=(),
            )

    def test_enum_with_non_string_allowed_values_raises(self) -> None:
        with pytest.raises(TypeError, match="allowed_values must contain only strings"):
            SpecificationDefinition(
                key="x",
                label="X",
                value_kind=SpecificationValueKind.ENUM,
                allowed_values=("a", 1, "c"),  # type: ignore
            )

    def test_allowed_values_not_tuple_raises(self) -> None:
        with pytest.raises(TypeError, match="allowed_values must be a tuple"):
            SpecificationDefinition(
                key="x",
                label="X",
                value_kind=SpecificationValueKind.ENUM,
                allowed_values=["a", "b"],  # type: ignore
            )

    def test_key_stripped(self) -> None:
        defn = SpecificationDefinition(
            key="  capacity  ",
            label="Cap",
            value_kind=SpecificationValueKind.DECIMAL,
        )
        assert defn.key == "capacity"

    def test_label_stripped(self) -> None:
        defn = SpecificationDefinition(
            key="cap",
            label="  Capacity  ",
            value_kind=SpecificationValueKind.DECIMAL,
        )
        assert defn.label == "Capacity"

    def test_frozen(self) -> None:
        defn = _capacity_definition()
        with pytest.raises((AttributeError, Exception)):
            defn.key = "other"  # type: ignore

    # --- TEXT validates any string ---

    def test_text_validates_any_string(self) -> None:
        defn = _interface_definition()
        assert defn.validate_canonical_value("SATA") is True
        assert defn.validate_canonical_value("") is True
        assert defn.validate_canonical_value("anything goes") is True

    def test_text_rejects_non_string(self) -> None:
        defn = _interface_definition()
        assert defn.validate_canonical_value(123) is False
        assert defn.validate_canonical_value(Decimal("3.14")) is False


# ===================================================================
# B. Identity binding
# ===================================================================


class TestIdentityBinding:
    """SpecificationObservation must require established ProductIdentity."""

    def test_exact_identity_accepted(self) -> None:
        identity = _established_identity_exact()
        obs = SpecificationObservation(
            product_identity=identity,
            definition=_capacity_definition(),
            source_name="manufacturer",
            source_url="https://example.com/spec",
            retrieved_at=_now_aware(),
            raw_value="3.84",
            source_authority=SourceAuthority.AUTHORITATIVE,
        )
        assert obs.product_identity is identity

    def test_normalized_exact_identity_accepted(self) -> None:
        identity = _established_identity_normalized()
        obs = SpecificationObservation(
            product_identity=identity,
            definition=_capacity_definition(),
            source_name="retailer",
            source_url="https://example.com/spec",
            retrieved_at=_now_aware(),
            raw_value="3.84",
            source_authority=SourceAuthority.SECONDARY,
        )
        assert obs.product_identity is identity

    def test_unknown_identity_rejected(self) -> None:
        identity = _unestablished_identity_unknown()
        with pytest.raises(ValueError, match="established ProductIdentity"):
            SpecificationObservation(
                product_identity=identity,
                definition=_capacity_definition(),
                source_name="x",
                source_url="https://x.com",
                retrieved_at=_now_aware(),
                raw_value="val",
                source_authority=SourceAuthority.SECONDARY,
            )

    def test_partial_identity_rejected(self) -> None:
        identity = _unestablished_identity_partial()
        with pytest.raises(ValueError, match="established ProductIdentity"):
            SpecificationObservation(
                product_identity=identity,
                definition=_capacity_definition(),
                source_name="x",
                source_url="https://x.com",
                retrieved_at=_now_aware(),
                raw_value="val",
                source_authority=SourceAuthority.SECONDARY,
            )

    def test_description_only_identity_rejected(self) -> None:
        identity = _unestablished_identity_description_only()
        with pytest.raises(ValueError, match="established ProductIdentity"):
            SpecificationObservation(
                product_identity=identity,
                definition=_capacity_definition(),
                source_name="x",
                source_url="https://x.com",
                retrieved_at=_now_aware(),
                raw_value="val",
                source_authority=SourceAuthority.SECONDARY,
            )

    def test_non_product_identity_type_rejected(self) -> None:
        with pytest.raises(TypeError, match="product_identity must be a ProductIdentity"):
            SpecificationObservation(
                product_identity="not-an-identity",  # type: ignore
                definition=_capacity_definition(),
                source_name="x",
                source_url="https://x.com",
                retrieved_at=_now_aware(),
                raw_value="val",
                source_authority=SourceAuthority.SECONDARY,
            )


# ===================================================================
# C. Observation
# ===================================================================


class TestSpecificationObservation:
    """Test SpecificationObservation construction and provenance."""

    def test_provenance_preserved(self) -> None:
        obs = SpecificationObservation(
            product_identity=_established_identity_exact(),
            definition=_capacity_definition(),
            source_name="Manufacturer Site",
            source_url="https://example.com/product/abc-123",
            retrieved_at=_now_aware(),
            raw_value="3,840 GB",
            source_authority=SourceAuthority.AUTHORITATIVE,
            raw_reference="JSON-LD Product > @graph[0] > sd:capacity",
        )
        assert obs.source_name == "Manufacturer Site"
        assert obs.source_url == "https://example.com/product/abc-123"
        assert obs.raw_value == "3,840 GB"
        assert obs.raw_reference == "JSON-LD Product > @graph[0] > sd:capacity"
        assert obs.source_authority is SourceAuthority.AUTHORITATIVE

    def test_timezone_aware_retrieval_time_required(self) -> None:
        naive_dt = datetime(2025, 1, 15, 12, 0, 0)
        with pytest.raises(ValueError, match="timezone-aware"):
            SpecificationObservation(
                product_identity=_established_identity_exact(),
                definition=_capacity_definition(),
                source_name="x",
                source_url="https://x.com",
                retrieved_at=naive_dt,
                raw_value="val",
                source_authority=SourceAuthority.SECONDARY,
            )

    def test_product_spec_binding_preserved(self) -> None:
        identity = _established_identity_exact()
        defn = _capacity_definition()
        obs = SpecificationObservation(
            product_identity=identity,
            definition=defn,
            source_name="x",
            source_url="https://x.com",
            retrieved_at=_now_aware(),
            raw_value="val",
            source_authority=SourceAuthority.SECONDARY,
        )
        assert obs.product_identity is identity
        assert obs.definition is defn

    def test_source_authority_required(self) -> None:
        with pytest.raises(TypeError, match="source_authority must be a SourceAuthority"):
            SpecificationObservation(
                product_identity=_established_identity_exact(),
                definition=_capacity_definition(),
                source_name="x",
                source_url="https://x.com",
                retrieved_at=_now_aware(),
                raw_value="val",
                source_authority="AUTHORITATIVE",  # type: ignore
            )

    def test_source_authority_validated_enum(self) -> None:
        for auth in (SourceAuthority.AUTHORITATIVE, SourceAuthority.SECONDARY):
            obs = SpecificationObservation(
                product_identity=_established_identity_exact(),
                definition=_capacity_definition(),
                source_name="x",
                source_url="https://x.com",
                retrieved_at=_now_aware(),
                raw_value="val",
                source_authority=auth,
            )
            assert obs.source_authority is auth

    def test_raw_values_preserved(self) -> None:
        obs = SpecificationObservation(
            product_identity=_established_identity_exact(),
            definition=_capacity_definition(),
            source_name="x",
            source_url="https://x.com",
            retrieved_at=_now_aware(),
            raw_value="  3.84 TB  ",
            source_authority=SourceAuthority.SECONDARY,
        )
        # raw_value is preserved (not stripped per contract — interior preserved)
        assert obs.raw_value == "  3.84 TB  "

    def test_source_name_stripped(self) -> None:
        obs = SpecificationObservation(
            product_identity=_established_identity_exact(),
            definition=_capacity_definition(),
            source_name="  Manufacturer  ",
            source_url="https://x.com",
            retrieved_at=_now_aware(),
            raw_value="val",
            source_authority=SourceAuthority.SECONDARY,
        )
        assert obs.source_name == "Manufacturer"

    def test_source_url_stripped(self) -> None:
        obs = SpecificationObservation(
            product_identity=_established_identity_exact(),
            definition=_capacity_definition(),
            source_name="x",
            source_url="  https://x.com  ",
            retrieved_at=_now_aware(),
            raw_value="val",
            source_authority=SourceAuthority.SECONDARY,
        )
        assert obs.source_url == "https://x.com"

    def test_empty_source_name_rejected(self) -> None:
        with pytest.raises(ValueError, match="source_name"):
            SpecificationObservation(
                product_identity=_established_identity_exact(),
                definition=_capacity_definition(),
                source_name="",
                source_url="https://x.com",
                retrieved_at=_now_aware(),
                raw_value="val",
                source_authority=SourceAuthority.SECONDARY,
            )

    def test_empty_source_url_rejected(self) -> None:
        with pytest.raises(ValueError, match="source_url"):
            SpecificationObservation(
                product_identity=_established_identity_exact(),
                definition=_capacity_definition(),
                source_name="x",
                source_url="",
                retrieved_at=_now_aware(),
                raw_value="val",
                source_authority=SourceAuthority.SECONDARY,
            )

    def test_raw_reference_optional(self) -> None:
        obs = SpecificationObservation(
            product_identity=_established_identity_exact(),
            definition=_capacity_definition(),
            source_name="x",
            source_url="https://x.com",
            retrieved_at=_now_aware(),
            raw_value="val",
            source_authority=SourceAuthority.SECONDARY,
        )
        assert obs.raw_reference is None

    def test_raw_reference_stripped_and_trailing_empty_becomes_none(self) -> None:
        obs = SpecificationObservation(
            product_identity=_established_identity_exact(),
            definition=_capacity_definition(),
            source_name="x",
            source_url="https://x.com",
            retrieved_at=_now_aware(),
            raw_value="val",
            source_authority=SourceAuthority.SECONDARY,
            raw_reference="  ref  ",
        )
        assert obs.raw_reference == "ref"

    def test_non_string_raw_value_raises(self) -> None:
        with pytest.raises(TypeError, match="raw_value must be a string"):
            SpecificationObservation(
                product_identity=_established_identity_exact(),
                definition=_capacity_definition(),
                source_name="x",
                source_url="https://x.com",
                retrieved_at=_now_aware(),
                raw_value=123,  # type: ignore
                source_authority=SourceAuthority.SECONDARY,
            )

    def test_frozen(self) -> None:
        obs = SpecificationObservation(
            product_identity=_established_identity_exact(),
            definition=_capacity_definition(),
            source_name="x",
            source_url="https://x.com",
            retrieved_at=_now_aware(),
            raw_value="val",
            source_authority=SourceAuthority.SECONDARY,
        )
        with pytest.raises((AttributeError, Exception)):
            obs.source_name = "other"  # type: ignore


# ===================================================================
# D. Normalized observation
# ===================================================================


class TestNormalizedSpecificationObservation:
    """Test NormalizedSpecificationObservation construction."""

    def _canonical_obs(self) -> SpecificationObservation:
        return SpecificationObservation(
            product_identity=_established_identity_exact(),
            definition=_capacity_definition(),
            source_name="x",
            source_url="https://x.com",
            retrieved_at=_now_aware(),
            raw_value="3.84",
            source_authority=SourceAuthority.AUTHORITATIVE,
        )

    # --- canonical-value path ---

    def test_canonical_value_path(self) -> None:
        obs = self._canonical_obs()
        normalized = NormalizedSpecificationObservation(
            observation=obs,
            canonical_value=SpecificationValue(value=Decimal("3.84")),
        )
        assert normalized.canonical_value.value == Decimal("3.84")
        assert normalized.normalization_issue is None
        assert normalized.is_usable is True

    def test_original_observation_preserved(self) -> None:
        obs = self._canonical_obs()
        normalized = NormalizedSpecificationObservation(
            observation=obs,
            canonical_value=SpecificationValue(value=Decimal("3.84")),
        )
        assert normalized.observation is obs

    # --- issue-only path ---

    def test_issue_only_path(self) -> None:
        obs = self._canonical_obs()
        normalized = NormalizedSpecificationObservation(
            observation=obs,
            normalization_issue="Ambiguous value: 'up to 7.68 TB depending on model'",
        )
        assert normalized.canonical_value is None
        assert normalized.normalization_issue == "Ambiguous value: 'up to 7.68 TB depending on model'"
        assert normalized.is_usable is False

    # --- impossible states rejected ---

    def test_both_canonical_and_issue_rejected(self) -> None:
        obs = self._canonical_obs()
        with pytest.raises(ValueError, match="exactly one of"):
            NormalizedSpecificationObservation(
                observation=obs,
                canonical_value=SpecificationValue(value=Decimal("3.84")),
                normalization_issue="some issue",
            )

    def test_neither_canonical_nor_issue_rejected(self) -> None:
        obs = self._canonical_obs()
        with pytest.raises(ValueError, match="exactly one of"):
            NormalizedSpecificationObservation(
                observation=obs,
            )

    # --- wrong-kind canonical value rejected ---

    def test_wrong_kind_canonical_value_rejected(self) -> None:
        """A TEXT value for a DECIMAL definition must be rejected."""
        obs = SpecificationObservation(
            product_identity=_established_identity_exact(),
            definition=_capacity_definition(),  # DECIMAL kind
            source_name="x",
            source_url="https://x.com",
            retrieved_at=_now_aware(),
            raw_value="3.84",
            source_authority=SourceAuthority.SECONDARY,
        )
        with pytest.raises(ValueError, match="not valid for definition"):
            NormalizedSpecificationObservation(
                observation=obs,
                canonical_value=SpecificationValue(value="not a decimal"),
            )

    def test_float_for_decimal_definition_rejected(self) -> None:
        """float is rejected at SpecificationValue construction, before definition check."""
        with pytest.raises(TypeError, match="must be str, Decimal, or bool"):
            SpecificationValue(value=3.84)

    def test_valid_enum_member_accepted(self) -> None:
        obs = SpecificationObservation(
            product_identity=_established_identity_exact(),
            definition=_form_factor_definition(),
            source_name="x",
            source_url="https://x.com",
            retrieved_at=_now_aware(),
            raw_value="M.2",
            source_authority=SourceAuthority.SECONDARY,
        )
        normalized = NormalizedSpecificationObservation(
            observation=obs,
            canonical_value=SpecificationValue(value="M.2"),
        )
        assert normalized.is_usable is True

    def test_invalid_enum_member_rejected(self) -> None:
        obs = SpecificationObservation(
            product_identity=_established_identity_exact(),
            definition=_form_factor_definition(),
            source_name="x",
            source_url="https://x.com",
            retrieved_at=_now_aware(),
            raw_value="3.5-inch",
            source_authority=SourceAuthority.SECONDARY,
        )
        with pytest.raises(ValueError, match="not valid for definition"):
            NormalizedSpecificationObservation(
                observation=obs,
                canonical_value=SpecificationValue(value="3.5-inch"),
            )

    def test_empty_normalization_issue_rejected(self) -> None:
        obs = self._canonical_obs()
        with pytest.raises(ValueError, match="normalization_issue must be a non-empty"):
            NormalizedSpecificationObservation(
                observation=obs,
                normalization_issue="  ",
            )

    def test_normalization_issue_stripped(self) -> None:
        obs = self._canonical_obs()
        normalized = NormalizedSpecificationObservation(
            observation=obs,
            normalization_issue="  Ambiguous parsing  ",
        )
        assert normalized.normalization_issue == "Ambiguous parsing"

    def test_frozen(self) -> None:
        obs = self._canonical_obs()
        normalized = NormalizedSpecificationObservation(
            observation=obs,
            canonical_value=SpecificationValue(value=Decimal("3.84")),
        )
        with pytest.raises((AttributeError, Exception)):
            normalized.canonical_value = None  # type: ignore


# ===================================================================
# E. Resolution
# ===================================================================


class TestSpecificationResolution:
    """Test resolve_specification and SpecificationResolution."""

    def _make_normalized(
        self,
        identity: ProductIdentity,
        definition: SpecificationDefinition,
        raw_value: str,
        canonical_value: Any | None,
        authority: SourceAuthority,
    ) -> NormalizedSpecificationObservation:
        obs = SpecificationObservation(
            product_identity=identity,
            definition=definition,
            source_name="source",
            source_url="https://example.com",
            retrieved_at=_now_aware(),
            raw_value=raw_value,
            source_authority=authority,
        )
        return NormalizedSpecificationObservation(
            observation=obs,
            canonical_value=SpecificationValue(value=canonical_value) if canonical_value is not None else None,
            normalization_issue=None if canonical_value is not None else "Normalization failed",
        )

    def _make_issue_only(
        self,
        identity: ProductIdentity,
        definition: SpecificationDefinition,
        raw_value: str,
        authority: SourceAuthority,
    ) -> NormalizedSpecificationObservation:
        obs = SpecificationObservation(
            product_identity=identity,
            definition=definition,
            source_name="source",
            source_url="https://example.com",
            retrieved_at=_now_aware(),
            raw_value=raw_value,
            source_authority=authority,
        )
        return NormalizedSpecificationObservation(
            observation=obs,
            normalization_issue="Ambiguous value",
        )

    # --- UNKNOWN ---

    def test_zero_observations_is_unknown(self) -> None:
        identity = _established_identity_exact()
        defn = _capacity_definition()
        result = resolve_specification(identity, defn, ())
        assert result.state is ResolutionState.UNKNOWN
        assert result.resolved_value is None

    def test_only_issue_only_observations_is_unknown(self) -> None:
        identity = _established_identity_exact()
        defn = _capacity_definition()
        obs = self._make_issue_only(identity, defn, "up to 3.84", SourceAuthority.SECONDARY)
        result = resolve_specification(identity, defn, (obs,))
        assert result.state is ResolutionState.UNKNOWN
        assert result.resolved_value is None
        assert len(result.evidence) == 1
        assert len(result.issue_only_evidence) == 1

    # --- VERIFIED ---

    def test_authoritative_single_is_verified(self) -> None:
        identity = _established_identity_exact()
        defn = _capacity_definition()
        obs = self._make_normalized(identity, defn, "3.84", Decimal("3.84"), SourceAuthority.AUTHORITATIVE)
        result = resolve_specification(identity, defn, (obs,))
        assert result.state is ResolutionState.VERIFIED
        assert result.resolved_value.value == Decimal("3.84")

    def test_authoritative_plus_secondary_agreement_is_verified(self) -> None:
        identity = _established_identity_exact()
        defn = _capacity_definition()
        auth = self._make_normalized(identity, defn, "3.84", Decimal("3.84"), SourceAuthority.AUTHORITATIVE)
        sec = self._make_normalized(identity, defn, "3.84", Decimal("3.84"), SourceAuthority.SECONDARY)
        result = resolve_specification(identity, defn, (auth, sec))
        assert result.state is ResolutionState.VERIFIED
        assert result.resolved_value.value == Decimal("3.84")

    # --- UNVERIFIED ---

    def test_secondary_only_agreement_is_unverified(self) -> None:
        identity = _established_identity_exact()
        defn = _interface_definition()  # TEXT kind
        s1 = self._make_normalized(identity, defn, "U.3", "U.3", SourceAuthority.SECONDARY)
        s2 = self._make_normalized(identity, defn, "U.3", "U.3", SourceAuthority.SECONDARY)
        result = resolve_specification(identity, defn, (s1, s2))
        assert result.state is ResolutionState.UNVERIFIED
        assert result.resolved_value.value == "U.3"

    def test_single_secondary_is_unverified(self) -> None:
        identity = _established_identity_exact()
        defn = _capacity_definition()
        s1 = self._make_normalized(identity, defn, "3.84", Decimal("3.84"), SourceAuthority.SECONDARY)
        result = resolve_specification(identity, defn, (s1,))
        assert result.state is ResolutionState.UNVERIFIED
        assert result.resolved_value.value == Decimal("3.84")

    # --- CONFLICT ---

    def test_authoritative_vs_secondary_disagreement_is_conflict(self) -> None:
        identity = _established_identity_exact()
        defn = _capacity_definition()
        auth = self._make_normalized(identity, defn, "3.84", Decimal("3.84"), SourceAuthority.AUTHORITATIVE)
        sec = self._make_normalized(identity, defn, "7.68", Decimal("7.68"), SourceAuthority.SECONDARY)
        result = resolve_specification(identity, defn, (auth, sec))
        assert result.state is ResolutionState.CONFLICT
        assert result.resolved_value is None

    def test_authoritative_vs_authoritative_disagreement_is_conflict(self) -> None:
        identity = _established_identity_exact()
        defn = _capacity_definition()
        a1 = self._make_normalized(identity, defn, "3.84", Decimal("3.84"), SourceAuthority.AUTHORITATIVE)
        a2 = self._make_normalized(identity, defn, "7.68", Decimal("7.68"), SourceAuthority.AUTHORITATIVE)
        result = resolve_specification(identity, defn, (a1, a2))
        assert result.state is ResolutionState.CONFLICT
        assert result.resolved_value is None

    def test_secondary_vs_secondary_disagreement_is_conflict(self) -> None:
        identity = _established_identity_exact()
        defn = _capacity_definition()
        s1 = self._make_normalized(identity, defn, "3.84", Decimal("3.84"), SourceAuthority.SECONDARY)
        s2 = self._make_normalized(identity, defn, "7.68", Decimal("7.68"), SourceAuthority.SECONDARY)
        result = resolve_specification(identity, defn, (s1, s2))
        assert result.state is ResolutionState.CONFLICT
        assert result.resolved_value is None

    def test_9_secondary_vs_1_authoritative_is_conflict(self) -> None:
        """9 SECONDARY A + 1 AUTHORITATIVE B = CONFLICT (not 9-to-1 voting)."""
        identity = _established_identity_exact()
        defn = _capacity_definition()
        observations: list[NormalizedSpecificationObservation] = []
        for _ in range(9):
            observations.append(
                self._make_normalized(identity, defn, "3.84", Decimal("3.84"), SourceAuthority.SECONDARY)
            )
        observations.append(
            self._make_normalized(identity, defn, "7.68", Decimal("7.68"), SourceAuthority.AUTHORITATIVE)
        )
        result = resolve_specification(identity, defn, tuple(observations))
        assert result.state is ResolutionState.CONFLICT
        assert result.resolved_value is None

    # --- Issue-only evidence preserved ---

    def test_issue_only_evidence_preserved_in_resolution(self) -> None:
        identity = _established_identity_exact()
        defn = _capacity_definition()
        usable = self._make_normalized(identity, defn, "3.84", Decimal("3.84"), SourceAuthority.AUTHORITATIVE)
        issue = self._make_issue_only(identity, defn, "up to 7.68", SourceAuthority.SECONDARY)
        result = resolve_specification(identity, defn, (usable, issue))
        assert result.state is ResolutionState.VERIFIED
        assert result.resolved_value.value == Decimal("3.84")
        assert len(result.evidence) == 2
        assert len(result.usable_evidence) == 1
        assert len(result.issue_only_evidence) == 1

    # --- Cross-product evidence rejected ---

    def test_mixed_product_identities_rejected(self) -> None:
        identity_a = _established_identity_exact()
        identity_b = _established_identity_normalized()
        defn = _capacity_definition()
        obs_a = self._make_normalized(identity_a, defn, "3.84", Decimal("3.84"), SourceAuthority.AUTHORITATIVE)
        obs_b = self._make_normalized(identity_b, defn, "3.84", Decimal("3.84"), SourceAuthority.SECONDARY)
        with pytest.raises(ValueError, match="Cross-product evidence rejected"):
            resolve_specification(identity_a, defn, (obs_a, obs_b))

    # --- Cross-specification evidence rejected ---

    def test_mixed_specification_definitions_rejected(self) -> None:
        identity = _established_identity_exact()
        defn_capacity = _capacity_definition()
        defn_interface = _interface_definition()
        obs_cap = self._make_normalized(identity, defn_capacity, "3.84", Decimal("3.84"), SourceAuthority.AUTHORITATIVE)
        obs_iface = self._make_normalized(identity, defn_interface, "SATA", "SATA", SourceAuthority.SECONDARY)
        with pytest.raises(ValueError, match="Cross-specification evidence rejected"):
            resolve_specification(identity, defn_capacity, (obs_cap, obs_iface))

    # --- Resolved value / state inconsistency ---

    def test_unknown_with_value_rejected(self) -> None:
        identity = _established_identity_exact()
        defn = _capacity_definition()
        with pytest.raises(ValueError, match="evidence derives no resolved value"):
            SpecificationResolution(
                product_identity=identity,
                definition=defn,
                state=ResolutionState.UNKNOWN,
                resolved_value=SpecificationValue(value=Decimal("3.84")),
                evidence=(),
            )

    def test_verified_without_value_rejected(self) -> None:
        identity = _established_identity_exact()
        defn = _capacity_definition()
        with pytest.raises(ValueError, match="evidence derives UNKNOWN"):
            SpecificationResolution(
                product_identity=identity,
                definition=defn,
                state=ResolutionState.VERIFIED,
                resolved_value=None,
                evidence=(),
            )

    def test_conflict_with_value_rejected(self) -> None:
        identity = _established_identity_exact()
        defn = _capacity_definition()
        with pytest.raises(ValueError, match="evidence derives UNKNOWN"):
            SpecificationResolution(
                product_identity=identity,
                definition=defn,
                state=ResolutionState.CONFLICT,
                resolved_value=SpecificationValue(value=Decimal("3.84")),
                evidence=(),
            )

    # --- Evidence cannot silently disappear ---

    def test_all_evidence_preserved_in_result(self) -> None:
        identity = _established_identity_exact()
        defn = _capacity_definition()
        obs1 = self._make_normalized(identity, defn, "3.84", Decimal("3.84"), SourceAuthority.AUTHORITATIVE)
        obs2 = self._make_normalized(identity, defn, "7.68", Decimal("7.68"), SourceAuthority.SECONDARY)
        result = resolve_specification(identity, defn, (obs1, obs2))
        assert len(result.evidence) == 2
        assert result.evidence[0] is obs1
        assert result.evidence[1] is obs2

    # --- Unestablished identity rejected by resolver ---

    def test_resolver_rejects_unestablished_identity(self) -> None:
        identity = _unestablished_identity_unknown()
        defn = _capacity_definition()
        with pytest.raises(ValueError, match="established ProductIdentity"):
            resolve_specification(identity, defn, ())

    # --- Non-tuple observations rejected ---

    def test_resolver_rejects_non_tuple_observations(self) -> None:
        identity = _established_identity_exact()
        defn = _capacity_definition()
        with pytest.raises(TypeError, match="observations must be a tuple"):
            resolve_specification(identity, defn, [])  # type: ignore

    # --- Resolution requires established identity at construction ---

    def test_resolution_requires_established_identity(self) -> None:
        identity = _unestablished_identity_unknown()
        defn = _capacity_definition()
        with pytest.raises(ValueError, match="established ProductIdentity"):
            SpecificationResolution(
                product_identity=identity,
                definition=defn,
                state=ResolutionState.UNKNOWN,
                resolved_value=None,
                evidence=(),
            )

    # --- Resolution cross-product evidence rejected at construction ---

    def test_resolution_construction_rejects_cross_product(self) -> None:
        identity_a = _established_identity_exact()
        identity_b = _established_identity_normalized()
        defn = _capacity_definition()
        obs_b = self._make_normalized(identity_b, defn, "3.84", Decimal("3.84"), SourceAuthority.SECONDARY)
        with pytest.raises(ValueError, match="Cross-product evidence rejected"):
            SpecificationResolution(
                product_identity=identity_a,
                definition=defn,
                state=ResolutionState.UNKNOWN,
                resolved_value=None,
                evidence=(obs_b,),
            )

    # --- Resolution cross-spec evidence rejected at construction ---

    def test_resolution_construction_rejects_cross_spec(self) -> None:
        identity = _established_identity_exact()
        defn_a = _capacity_definition()
        defn_b = _interface_definition()
        obs_b = self._make_normalized(identity, defn_b, "SATA", "SATA", SourceAuthority.SECONDARY)
        with pytest.raises(ValueError, match="Cross-specification evidence rejected"):
            SpecificationResolution(
                product_identity=identity,
                definition=defn_a,
                state=ResolutionState.UNKNOWN,
                resolved_value=None,
                evidence=(obs_b,),
            )

    # --- Resolution frozen ---

    def test_resolution_frozen(self) -> None:
        identity = _established_identity_exact()
        defn = _capacity_definition()
        result = resolve_specification(identity, defn, ())
        with pytest.raises((AttributeError, Exception)):
            result.state = ResolutionState.CONFLICT  # type: ignore


# ===================================================================
# F. ProductSpecificationSet
# ===================================================================


class TestProductSpecificationSet:
    """Test ProductSpecificationSet completeness enforcement."""

    def _build_schema(self) -> CategorySchema:
        return CategorySchema(
            schema_id="test-schema",
            schema_version="1.0",
            label="Test Schema",
            definitions={
                "capacity": _capacity_definition(),
                "interface": _interface_definition(),
                "form_factor": _form_factor_definition(),
                "nvme_support": _nvme_support_definition(),
            },
        )

    def _build_resolution(
        self,
        identity: ProductIdentity,
        definition: SpecificationDefinition,
        state: ResolutionState,
        value: Any,
        schema: CategorySchema,
    ) -> SpecificationResolution:
        return resolve_specification(
            identity, definition, tuple()
        )  # will be UNKNOWN; overridden by manual for other states

    # --- Complete valid set ---

    def test_complete_valid_set(self) -> None:
        identity = _established_identity_exact()
        schema = self._build_schema()
        resolutions = {}
        for key, defn in schema.definitions.items():
            res = resolve_specification(identity, defn, ())
            assert res.state is ResolutionState.UNKNOWN
            resolutions[key] = res
        pset = ProductSpecificationSet(
            product_identity=identity,
            category_schema=schema,
            resolutions=resolutions,
        )
        assert pset.product_identity is identity
        assert pset.category_schema is schema
        assert len(pset.resolutions) == 4

    def test_explicit_unknown_resolution_accepted(self) -> None:
        """UNKNOWN is explicitly representable — no missing resolution."""
        identity = _established_identity_exact()
        schema = self._build_schema()
        resolutions = {}
        for key, defn in schema.definitions.items():
            res = resolve_specification(identity, defn, ())
            resolutions[key] = res
        # All are UNKNOWN, but explicit
        for res in resolutions.values():
            assert res.state is ResolutionState.UNKNOWN
        pset = ProductSpecificationSet(
            product_identity=identity,
            category_schema=schema,
            resolutions=resolutions,
        )
        assert pset is not None

    # --- Missing resolution rejected ---

    def test_missing_resolution_rejected(self) -> None:
        identity = _established_identity_exact()
        schema = self._build_schema()
        resolutions = {}
        for key, defn in schema.definitions.items():
            if key != "capacity":
                res = resolve_specification(identity, defn, ())
                resolutions[key] = res
        # "capacity" is missing
        with pytest.raises(ValueError, match="Missing resolutions"):
            ProductSpecificationSet(
                product_identity=identity,
                category_schema=schema,
                resolutions=resolutions,
            )

    # --- Extra resolution rejected ---

    def test_extra_resolution_rejected(self) -> None:
        identity = _established_identity_exact()
        schema = self._build_schema()
        resolutions = {}
        for key, defn in schema.definitions.items():
            res = resolve_specification(identity, defn, ())
            resolutions[key] = res
        # Add extra resolution not in schema
        extra_defn = SpecificationDefinition(
            key="extra_spec",
            label="Extra",
            value_kind=SpecificationValueKind.TEXT,
        )
        resolutions["extra_spec"] = resolve_specification(identity, extra_defn, ())
        with pytest.raises(ValueError, match="not a definition in the CategorySchema"):
            ProductSpecificationSet(
                product_identity=identity,
                category_schema=schema,
                resolutions=resolutions,
            )

    # --- Duplicate resolution rejected ---

    def test_duplicate_resolution_rejected(self) -> None:
        """Two resolution keys that normalize to the same canonical key
        are rejected. Proves the canonical-key collision check works.

        A plain Python dict cannot hold duplicate keys, but keys that differ
        only by whitespace (e.g. "capacity" and " capacity ") are distinct
        dict keys that collide after canonical stripping. The constructor
        detects and rejects this.
        """
        identity = _established_identity_exact()
        schema = self._build_schema()
        resolutions = {}
        for key, defn in schema.definitions.items():
            res = resolve_specification(identity, defn, ())
            resolutions[key] = res
        # " capacity " strips to "capacity" which is already present
        resolutions[" capacity "] = resolutions["capacity"]
        with pytest.raises(ValueError, match="Duplicate resolution key"):
            ProductSpecificationSet(
                product_identity=identity,
                category_schema=schema,
                resolutions=resolutions,
            )

    def test_duplicate_key_after_strip_rejected(self) -> None:
        """Two resolution keys that differ only by whitespace are duplicates."""
        identity = _established_identity_exact()
        schema = self._build_schema()
        resolutions = {}
        for key, defn in schema.definitions.items():
            res = resolve_specification(identity, defn, ())
            resolutions[key] = res
        # Add a key that differs only by whitespace from an existing one
        # This would be "capacity " -> stripped "capacity" which is duplicate
        resolutions["capacity "] = resolutions["capacity"]
        with pytest.raises(ValueError, match="Duplicate resolution key"):
            ProductSpecificationSet(
                product_identity=identity,
                category_schema=schema,
                resolutions=resolutions,
            )

    # --- Cross-product resolution rejected ---

    def test_cross_product_resolution_rejected(self) -> None:
        identity_a = _established_identity_exact()
        identity_b = _established_identity_normalized()
        schema = self._build_schema()
        resolutions = {}
        for key, defn in schema.definitions.items():
            # All resolutions use identity_b, not identity_a
            res = resolve_specification(identity_b, defn, ())
            resolutions[key] = res
        with pytest.raises(ValueError, match="Cross-product resolution rejected"):
            ProductSpecificationSet(
                product_identity=identity_a,
                category_schema=schema,
                resolutions=resolutions,
            )

    # --- Wrong-definition resolution rejected ---

    def test_wrong_definition_resolution_rejected(self) -> None:
        identity = _established_identity_exact()
        schema = self._build_schema()
        resolutions = {}
        for key, defn in schema.definitions.items():
            res = resolve_specification(identity, defn, ())
            resolutions[key] = res
        # Replace capacity resolution with one using a different definition object
        # with the same key but a different instance
        different_defn = SpecificationDefinition(
            key="capacity",
            label="Storage Capacity (different instance)",
            value_kind=SpecificationValueKind.DECIMAL,
            unit="TB",
        )
        resolutions["capacity"] = resolve_specification(identity, different_defn, ())
        with pytest.raises(ValueError, match="does not match the CategorySchema"):
            ProductSpecificationSet(
                product_identity=identity,
                category_schema=schema,
                resolutions=resolutions,
            )

    # --- Unestablished set identity rejected ---

    def test_unestablished_set_identity_rejected(self) -> None:
        identity = _unestablished_identity_unknown()
        schema = self._build_schema()
        with pytest.raises(ValueError, match="established ProductIdentity"):
            ProductSpecificationSet(
                product_identity=identity,
                category_schema=schema,
                resolutions={},
            )


# ===================================================================
# G. Immutability / deterministic behaviour
# ===================================================================


class TestImmutability:
    """Frozen contracts and deterministic behaviour."""

    def test_specification_definition_frozen(self) -> None:
        defn = _capacity_definition()
        with pytest.raises((AttributeError, Exception)):
            defn.key = "other"  # type: ignore

    def test_specification_value_frozen(self) -> None:
        val = SpecificationValue(value=Decimal("3.84"))
        with pytest.raises((AttributeError, Exception)):
            val.value = Decimal("7.68")  # type: ignore

    def test_observations_frozen(self) -> None:
        obs = SpecificationObservation(
            product_identity=_established_identity_exact(),
            definition=_capacity_definition(),
            source_name="x",
            source_url="https://x.com",
            retrieved_at=_now_aware(),
            raw_value="val",
            source_authority=SourceAuthority.SECONDARY,
        )
        with pytest.raises((AttributeError, Exception)):
            obs.raw_value = "other"  # type: ignore

    def test_normalized_observations_frozen(self) -> None:
        obs = SpecificationObservation(
            product_identity=_established_identity_exact(),
            definition=_capacity_definition(),
            source_name="x",
            source_url="https://x.com",
            retrieved_at=_now_aware(),
            raw_value="val",
            source_authority=SourceAuthority.SECONDARY,
        )
        normalized = NormalizedSpecificationObservation(
            observation=obs,
            canonical_value=SpecificationValue(value=Decimal("3.84")),
        )
        with pytest.raises((AttributeError, Exception)):
            normalized.canonical_value = None  # type: ignore

    def test_resolution_frozen(self) -> None:
        identity = _established_identity_exact()
        defn = _capacity_definition()
        result = resolve_specification(identity, defn, ())
        with pytest.raises((AttributeError, Exception)):
            result.state = ResolutionState.VERIFIED  # type: ignore

    def test_category_schema_frozen(self) -> None:
        schema = CategorySchema(
            schema_id="x",
            schema_version="1.0",
            label="X",
            definitions={"capacity": _capacity_definition()},
        )
        with pytest.raises((AttributeError, Exception)):
            schema.schema_id = "other"  # type: ignore

    def test_product_spec_set_frozen(self) -> None:
        identity = _established_identity_exact()
        schema = CategorySchema(
            schema_id="x",
            schema_version="1.0",
            label="X",
            definitions={"capacity": _capacity_definition()},
        )
        res = resolve_specification(identity, schema.definitions["capacity"], ())
        pset = ProductSpecificationSet(
            product_identity=identity,
            category_schema=schema,
            resolutions={"capacity": res},
        )
        with pytest.raises((AttributeError, Exception)):
            pset.product_identity = identity  # type: ignore

    def test_same_input_produces_value_equal_output(self) -> None:
        """Determinism: same inputs -> equal outputs."""
        identity = _established_identity_exact()
        defn = _capacity_definition()
        result1 = resolve_specification(identity, defn, ())
        result2 = resolve_specification(identity, defn, ())
        assert result1.state is result2.state
        assert result1.resolved_value == result2.resolved_value
        assert result1.product_identity is result2.product_identity
        assert result1.definition is result2.definition

    def test_no_mutation_of_supplied_observations(self) -> None:
        """Resolver must not mutate the observations it receives."""
        identity = _established_identity_exact()
        defn = _capacity_definition()
        obs = SpecificationObservation(
            product_identity=identity,
            definition=defn,
            source_name="x",
            source_url="https://x.com",
            retrieved_at=_now_aware(),
            raw_value="3.84",
            source_authority=SourceAuthority.AUTHORITATIVE,
        )
        normalized = NormalizedSpecificationObservation(
            observation=obs,
            canonical_value=SpecificationValue(value=Decimal("3.84")),
        )
        # Resolve
        resolve_specification(identity, defn, (normalized,))
        # Verify observation unchanged
        assert normalized.observation is obs
        assert normalized.canonical_value.value == Decimal("3.84")
        assert normalized.is_usable is True


# ===================================================================
# H. CategorySchema tests
# ===================================================================


class TestCategorySchema:
    """Test CategorySchema construction and validation."""

    def test_valid_schema(self) -> None:
        schema = CategorySchema(
            schema_id="test-schema",
            schema_version="1.0",
            label="Test Category",
            definitions={
                "capacity": _capacity_definition(),
                "interface": _interface_definition(),
            },
        )
        assert schema.schema_id == "test-schema"
        assert schema.schema_version == "1.0"
        assert schema.label == "Test Category"
        assert len(schema.definitions) == 2
        assert "capacity" in schema.definitions
        assert "interface" in schema.definitions

    def test_empty_schema_id_rejected(self) -> None:
        with pytest.raises(ValueError, match="schema_id must be a non-empty"):
            CategorySchema(
                schema_id="",
                schema_version="1.0",
                label="X",
                definitions={},
            )

    def test_empty_schema_version_rejected(self) -> None:
        with pytest.raises(ValueError, match="schema_version must be a non-empty"):
            CategorySchema(
                schema_id="x",
                schema_version="",
                label="X",
                definitions={},
            )

    def test_empty_label_rejected(self) -> None:
        with pytest.raises(ValueError, match="label must be a non-empty"):
            CategorySchema(
                schema_id="x",
                schema_version="1.0",
                label="",
                definitions={},
            )

    def test_definitions_not_dict_rejected(self) -> None:
        with pytest.raises(TypeError, match="definitions must be a dict"):
            CategorySchema(
                schema_id="x",
                schema_version="1.0",
                label="X",
                definitions=[],  # type: ignore
            )

    def test_duplicate_schema_keys_rejected(self) -> None:
        defn = _capacity_definition()
        # Two definitions with the same key
        with pytest.raises(ValueError, match="Duplicate definition key"):
            CategorySchema(
                schema_id="x",
                schema_version="1.0",
                label="X",
                definitions={
                    "capacity": defn,
                    "capacity ": defn,  # stripped = "capacity" = duplicate
                },
            )

    def test_definitions_own_keys_must_be_unique(self) -> None:
        """Two definitions with the same SpecificationDefinition.key but
        different dict keys are rejected because mapping key must equal
        definition.key (Blocker C), which is checked before the duplicate
        key uniqueness check.
        """
        defn1 = SpecificationDefinition(
            key="shared",
            label="First",
            value_kind=SpecificationValueKind.TEXT,
        )
        defn2 = SpecificationDefinition(
            key="shared",
            label="Second",
            value_kind=SpecificationValueKind.TEXT,
        )
        with pytest.raises(ValueError, match="does not equal"):
            CategorySchema(
                schema_id="x",
                schema_version="1.0",
                label="X",
                definitions={
                    "first_key": defn1,
                    "second_key": defn2,
                },
            )

    def test_non_definition_value_rejected(self) -> None:
        with pytest.raises(TypeError, match="must be a SpecificationDefinition"):
            CategorySchema(
                schema_id="x",
                schema_version="1.0",
                label="X",
                definitions={"x": "not-a-definition"},  # type: ignore
            )


# ===================================================================
# I. SpecificationValue tests
# ===================================================================


class TestSpecificationValue:
    """Test SpecificationValue construction."""

    def test_string_value(self) -> None:
        val = SpecificationValue(value="SATA")
        assert val.value == "SATA"

    def test_decimal_value(self) -> None:
        val = SpecificationValue(value=Decimal("3.84"))
        assert val.value == Decimal("3.84")

    def test_boolean_value_true(self) -> None:
        val = SpecificationValue(value=True)
        assert val.value is True

    def test_boolean_value_false(self) -> None:
        val = SpecificationValue(value=False)
        assert val.value is False

    def test_float_rejected(self) -> None:
        with pytest.raises(TypeError, match="must be str, Decimal, or bool"):
            SpecificationValue(value=3.14)

    def test_int_rejected(self) -> None:
        with pytest.raises(TypeError, match="must be str, Decimal, or bool"):
            SpecificationValue(value=42)

    def test_none_rejected(self) -> None:
        with pytest.raises(TypeError, match="must be str, Decimal, or bool"):
            SpecificationValue(value=None)  # type: ignore


# ===================================================================
# J. Blocker A — Evidence-derived resolution (fabrication proofs)
# ===================================================================


class TestEvidenceDerivedResolution:
    """Blocker A: SpecificationResolution constructor MUST derive state/value
    from evidence. Manually constructed resolutions with fabricated state/value
    are mechanically rejected by the shared derivation helper.

    This proves the constructor cannot be used to create a state that
    contradicts what the evidence actually says.
    """

    def _make_normalized(
        self,
        identity: ProductIdentity,
        definition: SpecificationDefinition,
        canonical_value: Any | None,
        authority: SourceAuthority,
    ) -> NormalizedSpecificationObservation:
        obs = SpecificationObservation(
            product_identity=identity,
            definition=definition,
            source_name="source",
            source_url="https://example.com",
            retrieved_at=_now_aware(),
            raw_value="val",
            source_authority=authority,
        )
        return NormalizedSpecificationObservation(
            observation=obs,
            canonical_value=SpecificationValue(value=canonical_value) if canonical_value is not None else None,
            normalization_issue=None if canonical_value is not None else "Issue",
        )

    # --- Fabricated VERIFIED with zero usable evidence ---

    def test_fabricated_verified_zero_evidence_rejected(self) -> None:
        """VERIFIED with empty evidence must be rejected."""
        identity = _established_identity_exact()
        defn = _capacity_definition()
        with pytest.raises(ValueError, match="evidence derives UNKNOWN"):
            SpecificationResolution(
                product_identity=identity,
                definition=defn,
                state=ResolutionState.VERIFIED,
                resolved_value=SpecificationValue(value=Decimal("3.84")),
                evidence=(),
            )

    # --- Fabricated UNVERIFIED with zero usable evidence ---

    def test_fabricated_unverified_zero_evidence_rejected(self) -> None:
        identity = _established_identity_exact()
        defn = _capacity_definition()
        with pytest.raises(ValueError, match="evidence derives UNKNOWN"):
            SpecificationResolution(
                product_identity=identity,
                definition=defn,
                state=ResolutionState.UNVERIFIED,
                resolved_value=SpecificationValue(value=Decimal("3.84")),
                evidence=(),
            )

    # --- Fabricated CONFLICT with zero usable evidence ---

    def test_fabricated_conflict_zero_evidence_rejected(self) -> None:
        identity = _established_identity_exact()
        defn = _capacity_definition()
        with pytest.raises(ValueError, match="evidence derives UNKNOWN"):
            SpecificationResolution(
                product_identity=identity,
                definition=defn,
                state=ResolutionState.CONFLICT,
                resolved_value=None,
                evidence=(),
            )

    # --- Fabricated UNKNOWN with usable evidence ---

    def test_fabricated_unknown_with_usable_evidence_rejected(self) -> None:
        """UNKNOWN when evidence supports VERIFIED must be rejected."""
        identity = _established_identity_exact()
        defn = _capacity_definition()
        obs = self._make_normalized(
            identity, defn, Decimal("3.84"), SourceAuthority.AUTHORITATIVE
        )
        with pytest.raises(ValueError, match="evidence derives VERIFIED"):
            SpecificationResolution(
                product_identity=identity,
                definition=defn,
                state=ResolutionState.UNKNOWN,
                resolved_value=None,
                evidence=(obs,),
            )

    # --- VERIFIED when all usable evidence is SECONDARY ---

    def test_verified_when_all_secondary_rejected(self) -> None:
        """VERIFIED when all evidence is SECONDARY must be rejected (derives UNVERIFIED)."""
        identity = _established_identity_exact()
        defn = _capacity_definition()
        s1 = self._make_normalized(identity, defn, Decimal("3.84"), SourceAuthority.SECONDARY)
        s2 = self._make_normalized(identity, defn, Decimal("3.84"), SourceAuthority.SECONDARY)
        with pytest.raises(ValueError, match="evidence derives UNVERIFIED"):
            SpecificationResolution(
                product_identity=identity,
                definition=defn,
                state=ResolutionState.VERIFIED,
                resolved_value=SpecificationValue(value=Decimal("3.84")),
                evidence=(s1, s2),
            )

    # --- UNVERIFIED when AUTHORITATIVE evidence supports sole value ---

    def test_unverified_when_authoritative_exists_rejected(self) -> None:
        """UNVERIFIED when AUTHORITATIVE evidence exists must be rejected (derives VERIFIED)."""
        identity = _established_identity_exact()
        defn = _capacity_definition()
        auth = self._make_normalized(
            identity, defn, Decimal("3.84"), SourceAuthority.AUTHORITATIVE
        )
        with pytest.raises(ValueError, match="evidence derives VERIFIED"):
            SpecificationResolution(
                product_identity=identity,
                definition=defn,
                state=ResolutionState.UNVERIFIED,
                resolved_value=SpecificationValue(value=Decimal("3.84")),
                evidence=(auth,),
            )

    # --- VERIFIED with wrong resolved_value ---

    def test_verified_wrong_value_rejected(self) -> None:
        """VERIFIED with a value different from evidence must be rejected."""
        identity = _established_identity_exact()
        defn = _capacity_definition()
        obs = self._make_normalized(
            identity, defn, Decimal("3.84"), SourceAuthority.AUTHORITATIVE
        )
        with pytest.raises(ValueError, match="resolved_value mismatch"):
            SpecificationResolution(
                product_identity=identity,
                definition=defn,
                state=ResolutionState.VERIFIED,
                resolved_value=SpecificationValue(value=Decimal("7.68")),
                evidence=(obs,),
            )

    # --- UNVERIFIED with wrong resolved_value ---

    def test_unverified_wrong_value_rejected(self) -> None:
        identity = _established_identity_exact()
        defn = _capacity_definition()
        obs = self._make_normalized(
            identity, defn, Decimal("3.84"), SourceAuthority.SECONDARY
        )
        with pytest.raises(ValueError, match="resolved_value mismatch"):
            SpecificationResolution(
                product_identity=identity,
                definition=defn,
                state=ResolutionState.UNVERIFIED,
                resolved_value=SpecificationValue(value=Decimal("9.99")),
                evidence=(obs,),
            )

    # --- CONFLICT when only one unique usable value ---

    def test_conflict_single_value_rejected(self) -> None:
        """CONFLICT when evidence supports only one unique value must be rejected."""
        identity = _established_identity_exact()
        defn = _capacity_definition()
        obs = self._make_normalized(
            identity, defn, Decimal("3.84"), SourceAuthority.AUTHORITATIVE
        )
        with pytest.raises(ValueError, match="evidence derives VERIFIED"):
            SpecificationResolution(
                product_identity=identity,
                definition=defn,
                state=ResolutionState.CONFLICT,
                resolved_value=None,
                evidence=(obs,),
            )

    # --- VERIFIED when >1 unique values exist ---

    def test_verified_multiple_values_rejected(self) -> None:
        """VERIFIED when >1 unique values exist must be rejected (derives CONFLICT)."""
        identity = _established_identity_exact()
        defn = _capacity_definition()
        a1 = self._make_normalized(
            identity, defn, Decimal("3.84"), SourceAuthority.AUTHORITATIVE
        )
        a2 = self._make_normalized(
            identity, defn, Decimal("7.68"), SourceAuthority.SECONDARY
        )
        with pytest.raises(ValueError, match="evidence derives CONFLICT"):
            SpecificationResolution(
                product_identity=identity,
                definition=defn,
                state=ResolutionState.VERIFIED,
                resolved_value=SpecificationValue(value=Decimal("3.84")),
                evidence=(a1, a2),
            )

    # --- UNVERIFIED when >1 unique values exist ---

    def test_unverified_multiple_values_rejected(self) -> None:
        identity = _established_identity_exact()
        defn = _capacity_definition()
        s1 = self._make_normalized(
            identity, defn, Decimal("3.84"), SourceAuthority.SECONDARY
        )
        s2 = self._make_normalized(
            identity, defn, Decimal("7.68"), SourceAuthority.SECONDARY
        )
        with pytest.raises(ValueError, match="evidence derives CONFLICT"):
            SpecificationResolution(
                product_identity=identity,
                definition=defn,
                state=ResolutionState.UNVERIFIED,
                resolved_value=SpecificationValue(value=Decimal("3.84")),
                evidence=(s1, s2),
            )

    # --- Positive: correct evidence-derived construction succeeds ---

    def test_correct_unknown_construction(self) -> None:
        """UNKNOWN with zero evidence succeeds."""
        identity = _established_identity_exact()
        defn = _capacity_definition()
        result = SpecificationResolution(
            product_identity=identity,
            definition=defn,
            state=ResolutionState.UNKNOWN,
            resolved_value=None,
            evidence=(),
        )
        assert result.state is ResolutionState.UNKNOWN

    def test_correct_verified_construction(self) -> None:
        identity = _established_identity_exact()
        defn = _capacity_definition()
        obs = self._make_normalized(
            identity, defn, Decimal("3.84"), SourceAuthority.AUTHORITATIVE
        )
        result = SpecificationResolution(
            product_identity=identity,
            definition=defn,
            state=ResolutionState.VERIFIED,
            resolved_value=SpecificationValue(value=Decimal("3.84")),
            evidence=(obs,),
        )
        assert result.state is ResolutionState.VERIFIED
        assert result.resolved_value.value == Decimal("3.84")

    def test_correct_unverified_construction(self) -> None:
        identity = _established_identity_exact()
        defn = _capacity_definition()
        obs = self._make_normalized(
            identity, defn, Decimal("3.84"), SourceAuthority.SECONDARY
        )
        result = SpecificationResolution(
            product_identity=identity,
            definition=defn,
            state=ResolutionState.UNVERIFIED,
            resolved_value=SpecificationValue(value=Decimal("3.84")),
            evidence=(obs,),
        )
        assert result.state is ResolutionState.UNVERIFIED

    def test_correct_conflict_construction(self) -> None:
        identity = _established_identity_exact()
        defn = _capacity_definition()
        a1 = self._make_normalized(
            identity, defn, Decimal("3.84"), SourceAuthority.AUTHORITATIVE
        )
        a2 = self._make_normalized(
            identity, defn, Decimal("7.68"), SourceAuthority.SECONDARY
        )
        result = SpecificationResolution(
            product_identity=identity,
            definition=defn,
            state=ResolutionState.CONFLICT,
            resolved_value=None,
            evidence=(a1, a2),
        )
        assert result.state is ResolutionState.CONFLICT
        assert result.resolved_value is None


# ===================================================================
# K. Blocker B — Deep immutability
# ===================================================================


class TestDeepImmutability:
    """Blocker B: Frozen dataclasses must not contain mutable internal dicts.

    CategorySchema.definitions and ProductSpecificationSet.resolutions
    are wrapped in types.MappingProxyType for genuine immutability.
    Defensive copies ensure caller-owned dicts cannot mutate the objects.
    """

    def test_schema_definitions_cannot_be_mutated(self) -> None:
        """schema.definitions cannot be mutated after construction."""
        schema = CategorySchema(
            schema_id="test",
            schema_version="1.0",
            label="Test",
            definitions={"capacity": _capacity_definition()},
        )
        with pytest.raises(TypeError, match="mappingproxy"):
            schema.definitions["capacity"] = _interface_definition()  # type: ignore

    def test_schema_definitions_cannot_add_keys(self) -> None:
        """Cannot add new keys to schema.definitions after construction."""
        schema = CategorySchema(
            schema_id="test",
            schema_version="1.0",
            label="Test",
            definitions={"capacity": _capacity_definition()},
        )
        with pytest.raises(TypeError, match="mappingproxy"):
            schema.definitions["interface"] = _interface_definition()  # type: ignore

    def test_schema_definitions_cannot_delete_keys(self) -> None:
        """Cannot remove keys from schema.definitions after construction."""
        schema = CategorySchema(
            schema_id="test",
            schema_version="1.0",
            label="Test",
            definitions={"capacity": _capacity_definition()},
        )
        with pytest.raises(TypeError, match="mappingproxy"):
            del schema.definitions["capacity"]  # type: ignore

    def test_product_spec_set_resolutions_cannot_be_mutated(self) -> None:
        """ProductSpecificationSet.resolutions cannot be mutated after construction."""
        identity = _established_identity_exact()
        schema = CategorySchema(
            schema_id="test",
            schema_version="1.0",
            label="Test",
            definitions={"capacity": _capacity_definition()},
        )
        res = resolve_specification(identity, schema.definitions["capacity"], ())
        pset = ProductSpecificationSet(
            product_identity=identity,
            category_schema=schema,
            resolutions={"capacity": res},
        )
        with pytest.raises(TypeError, match="mappingproxy"):
            pset.resolutions["capacity"] = res  # type: ignore

    def test_product_spec_set_resolutions_cannot_add_keys(self) -> None:
        """Cannot add new keys to resolutions after construction."""
        identity = _established_identity_exact()
        schema = CategorySchema(
            schema_id="test",
            schema_version="1.0",
            label="Test",
            definitions={"capacity": _capacity_definition()},
        )
        res = resolve_specification(identity, schema.definitions["capacity"], ())
        pset = ProductSpecificationSet(
            product_identity=identity,
            category_schema=schema,
            resolutions={"capacity": res},
        )
        with pytest.raises(TypeError, match="mappingproxy"):
            pset.resolutions["extra"] = res  # type: ignore

    def test_caller_dict_mutation_does_not_affect_schema(self) -> None:
        """Mutating the caller's original definitions dict after construction
        does not change the schema (defensive copy proof)."""
        original_defs = {"capacity": _capacity_definition()}
        schema = CategorySchema(
            schema_id="test",
            schema_version="1.0",
            label="Test",
            definitions=original_defs,
        )
        # Mutate the caller's original dict
        original_defs["capacity"] = _interface_definition()
        original_defs["extra"] = _interface_definition()
        # Schema must still have the original definition
        assert len(schema.definitions) == 1
        assert schema.definitions["capacity"].key == "capacity"
        assert schema.definitions["capacity"].label == "Storage Capacity"

    def test_caller_dict_mutation_does_not_affect_product_spec_set(self) -> None:
        """Mutating the caller's original resolutions dict after construction
        does not change the set (defensive copy proof)."""
        identity = _established_identity_exact()
        schema = CategorySchema(
            schema_id="test",
            schema_version="1.0",
            label="Test",
            definitions={"capacity": _capacity_definition()},
        )
        res = resolve_specification(identity, schema.definitions["capacity"], ())
        original_resolutions = {"capacity": res}
        pset = ProductSpecificationSet(
            product_identity=identity,
            category_schema=schema,
            resolutions=original_resolutions,
        )
        # Mutate the caller's original dict
        empty_res = resolve_specification(identity, schema.definitions["capacity"], ())
        original_resolutions["capacity"] = empty_res
        # The set's completeness must remain intact
        assert len(pset.resolutions) == 1
        assert pset.resolutions["capacity"].state is ResolutionState.UNKNOWN

    def test_completeness_after_caller_mutation(self) -> None:
        """Completeness remains true after caller-owned input mappings are mutated."""
        identity = _established_identity_exact()
        schema_defs = {
            "capacity": _capacity_definition(),
            "interface": _interface_definition(),
        }
        schema = CategorySchema(
            schema_id="test",
            schema_version="1.0",
            label="Test",
            definitions=schema_defs,
        )
        # Mutate caller's original defs dict
        schema_defs.clear()
        # Schema is still complete
        assert len(schema.definitions) == 2
        assert "capacity" in schema.definitions
        assert "interface" in schema.definitions

        # Build resolutions
        resolutions = {}
        for key, defn in schema.definitions.items():
            resolutions[key] = resolve_specification(identity, defn, ())
        pset = ProductSpecificationSet(
            product_identity=identity,
            category_schema=schema,
            resolutions=resolutions,
        )
        # Mutate caller's original resolutions dict
        resolutions.clear()
        # Set is still complete
        assert len(pset.resolutions) == 2


# ===================================================================
# L. Blocker C — Schema key / definition key consistency
# ===================================================================


class TestSchemaKeyConsistency:
    """Blocker C: Schema mapping key MUST equal SpecificationDefinition.key
    after canonical whitespace handling. No schema may have two machine
    identities for one definition.
    """

    def test_schema_key_mismatch_rejected(self) -> None:
        """schema mapping key != definition.key -> rejected."""
        defn = SpecificationDefinition(
            key="form_factor",
            label="Form Factor",
            value_kind=SpecificationValueKind.ENUM,
            allowed_values=("M.2",),
        )
        with pytest.raises(ValueError, match="does not equal"):
            CategorySchema(
                schema_id="test",
                schema_version="1.0",
                label="Test",
                definitions={"capacity": defn},  # key mismatch
            )

    def test_schema_key_match_accepted(self) -> None:
        """Matching key and definition.key is accepted."""
        defn = SpecificationDefinition(
            key="capacity",
            label="Capacity",
            value_kind=SpecificationValueKind.DECIMAL,
        )
        schema = CategorySchema(
            schema_id="test",
            schema_version="1.0",
            label="Test",
            definitions={"capacity": defn},
        )
        assert "capacity" in schema.definitions

    def test_whitespace_alias_cannot_create_second_key(self) -> None:
        """Whitespace/key alias cannot create a second semantic key.

        "capacity" and " capacity " both strip to "capacity".
        If the definition.key is "capacity", the alias key still
        maps to the same canonical key and is rejected as duplicate.
        """
        defn1 = SpecificationDefinition(
            key="capacity",
            label="First",
            value_kind=SpecificationValueKind.DECIMAL,
        )
        defn2 = SpecificationDefinition(
            key="capacity",
            label="Second",
            value_kind=SpecificationValueKind.DECIMAL,
        )
        with pytest.raises(ValueError, match="Duplicate definition key"):
            CategorySchema(
                schema_id="test",
                schema_version="1.0",
                label="Test",
                definitions={
                    "capacity": defn1,
                    " capacity ": defn2,  # strips to "capacity" = duplicate
                },
            )

    def test_resolution_key_canonical_stripped(self) -> None:
        """Resolution mapping keys are canonical (stripped). Non-canonical
        alias keys are normalized to their stripped form and must still
        match a schema definition key.
        """
        identity = _established_identity_exact()
        schema = CategorySchema(
            schema_id="test",
            schema_version="1.0",
            label="Test",
            definitions={"capacity": _capacity_definition()},
        )
        res = resolve_specification(identity, schema.definitions["capacity"], ())
        pset = ProductSpecificationSet(
            product_identity=identity,
            category_schema=schema,
            resolutions={" capacity ": res},  # stripped -> "capacity"
        )
        # Key is canonical after construction
        assert "capacity" in pset.resolutions
        assert " capacity " not in pset.resolutions

    def test_resolution_key_mismatch_schema_rejected(self) -> None:
        """Resolution key that doesn't match any schema definition is rejected."""
        identity = _established_identity_exact()
        schema = CategorySchema(
            schema_id="test",
            schema_version="1.0",
            label="Test",
            definitions={"capacity": _capacity_definition()},
        )
        res = resolve_specification(identity, schema.definitions["capacity"], ())
        with pytest.raises(ValueError, match="not a definition in the CategorySchema"):
            ProductSpecificationSet(
                product_identity=identity,
                category_schema=schema,
                resolutions={"wrong_key": res},
            )

    def test_no_second_machine_identity_in_schema(self) -> None:
        """A schema cannot have two different dict keys pointing to
        the same semantic definition. Both 'cap' and 'capacity' cannot
        exist if definition.key is 'capacity'.
        """
        defn = SpecificationDefinition(
            key="capacity",
            label="Capacity",
            value_kind=SpecificationValueKind.DECIMAL,
        )
        with pytest.raises(ValueError, match="does not equal"):
            CategorySchema(
                schema_id="test",
                schema_version="1.0",
                label="Test",
                definitions={"cap": defn},  # "cap" != "capacity"
            )
