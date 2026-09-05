"""Enterprise SSD Category-Specific Specification Schema (PRODUCT-INTEL.6B).

First category-specific schema built on the frozen 6A specification framework.

Defines exactly 12 specification fields for enterprise SSD products:
    capacity, storage_protocol, pcie_generation, pcie_lane_count,
    physical_form_factor, interface_connector, sequential_read,
    sequential_write, random_read_iops, random_write_iops,
    endurance_dwpd, power_loss_protection.

Normalization is representation-only:
    - Input: SpecificationObservation already bound to an established
      ProductIdentity and one SpecificationDefinition from this schema.
    - Output: NormalizedSpecificationObservation with either a canonical
      SpecificationValue or a normalization issue.
    - No extraction, no resolution, no authority inference, no identity
      creation, no network access.

Category logic is Enterprise SSD generic — no manufacturer-specific rules.
"""

from __future__ import annotations

import re
from decimal import Decimal, InvalidOperation

from product_intelligence.research.specifications import (
    CategorySchema,
    NormalizedSpecificationObservation,
    SpecificationDefinition,
    SpecificationObservation,
    SpecificationValue,
    SpecificationValueKind,
)


# ---------------------------------------------------------------------------
# Schema identifiers
# ---------------------------------------------------------------------------

ENTERPRISE_SSD_SCHEMA_ID = "enterprise-ssd"
ENTERPRISE_SSD_SCHEMA_VERSION = "1.0"

# ---------------------------------------------------------------------------
# Normalization issue codes
# ---------------------------------------------------------------------------

_MISSING_OR_EMPTY_VALUE = "MISSING_OR_EMPTY_VALUE"
_UNRECOGNIZED_FORMAT = "UNRECOGNIZED_FORMAT"
_UNSUPPORTED_UNIT = "UNSUPPORTED_UNIT"
_OUT_OF_RANGE_OR_NON_POSITIVE = "OUT_OF_RANGE_OR_NON_POSITIVE"
_AMBIGUOUS_VALUE = "AMBIGUOUS_VALUE"


# ---------------------------------------------------------------------------
# Schema definitions
# ---------------------------------------------------------------------------

def _build_definitions() -> dict[str, SpecificationDefinition]:
    """Build the 12-field Enterprise SSD schema v1 definitions."""
    return {
        "capacity": SpecificationDefinition(
            key="capacity",
            label="Capacity",
            value_kind=SpecificationValueKind.DECIMAL,
            unit="TB",
        ),
        "storage_protocol": SpecificationDefinition(
            key="storage_protocol",
            label="Storage Protocol",
            value_kind=SpecificationValueKind.ENUM,
            allowed_values=("NVMe", "SATA", "SAS"),
        ),
        "pcie_generation": SpecificationDefinition(
            key="pcie_generation",
            label="PCIe Generation",
            value_kind=SpecificationValueKind.ENUM,
            allowed_values=("PCIe 3.0", "PCIe 4.0", "PCIe 5.0"),
        ),
        "pcie_lane_count": SpecificationDefinition(
            key="pcie_lane_count",
            label="PCIe Lane Count",
            value_kind=SpecificationValueKind.DECIMAL,
        ),
        "physical_form_factor": SpecificationDefinition(
            key="physical_form_factor",
            label="Physical Form Factor",
            value_kind=SpecificationValueKind.ENUM,
            allowed_values=("2.5-inch", "M.2", "E1.S", "E3.S"),
        ),
        "interface_connector": SpecificationDefinition(
            key="interface_connector",
            label="Interface / Connector",
            value_kind=SpecificationValueKind.TEXT,
        ),
        "sequential_read": SpecificationDefinition(
            key="sequential_read",
            label="Sequential Read",
            value_kind=SpecificationValueKind.DECIMAL,
            unit="MB/s",
        ),
        "sequential_write": SpecificationDefinition(
            key="sequential_write",
            label="Sequential Write",
            value_kind=SpecificationValueKind.DECIMAL,
            unit="MB/s",
        ),
        "random_read_iops": SpecificationDefinition(
            key="random_read_iops",
            label="Random Read IOPS",
            value_kind=SpecificationValueKind.DECIMAL,
            unit="IOPS",
        ),
        "random_write_iops": SpecificationDefinition(
            key="random_write_iops",
            label="Random Write IOPS",
            value_kind=SpecificationValueKind.DECIMAL,
            unit="IOPS",
        ),
        "endurance_dwpd": SpecificationDefinition(
            key="endurance_dwpd",
            label="Endurance",
            value_kind=SpecificationValueKind.DECIMAL,
            unit="DWPD",
        ),
        "power_loss_protection": SpecificationDefinition(
            key="power_loss_protection",
            label="Power Loss Protection",
            value_kind=SpecificationValueKind.BOOLEAN,
        ),
    }


# ---------------------------------------------------------------------------
# Schema instance
# ---------------------------------------------------------------------------

ENTERPRISE_SSD_SCHEMA = CategorySchema(
    schema_id=ENTERPRISE_SSD_SCHEMA_ID,
    schema_version=ENTERPRISE_SSD_SCHEMA_VERSION,
    label="Enterprise SSD",
    definitions=_build_definitions(),
)

# ---------------------------------------------------------------------------
# Internal helper: validate observation belongs to this schema
# ---------------------------------------------------------------------------

def _validate_observation(observation: SpecificationObservation) -> None:
    """Validate that the observation's definition belongs to this schema.

    Uses exact object identity against the schema's own definition objects.
    Value-equal independently-constructed definitions are rejected.

    Raises TypeError if the observation is not a SpecificationObservation.
    Raises ValueError if the observation's definition is not the exact
    definition object from ENTERPRISE_SSD_SCHEMA.
    """
    if not isinstance(observation, SpecificationObservation):
        raise TypeError(
            f"observation must be a SpecificationObservation, got "
            f"{type(observation).__name__}"
        )
    # Identity check: the observation's definition must be the exact
    # object from this schema, not merely a value-equal clone.
    schema_def = ENTERPRISE_SSD_SCHEMA.definitions.get(
        observation.definition.key
    )
    if schema_def is not observation.definition:
        raise ValueError(
            f"Observation's definition '{observation.definition.key}' "
            f"(kind={observation.definition.value_kind.value}) does not belong to "
            f"the Enterprise SSD schema. "
            f"Only observations bound to the exact definition objects from "
            f"ENTERPRISE_SSD_SCHEMA may be normalized by this module."
        )


# ---------------------------------------------------------------------------
# Internal helper: issue result
# ---------------------------------------------------------------------------

def _issue(observation: SpecificationObservation, issue: str) -> NormalizedSpecificationObservation:
    """Return an issue-only NormalizedSpecificationObservation."""
    return NormalizedSpecificationObservation(
        observation=observation,
        normalization_issue=issue,
    )


def _canonical(observation: SpecificationObservation, value: object) -> NormalizedSpecificationObservation:
    """Return a canonical-value NormalizedSpecificationObservation."""
    return NormalizedSpecificationObservation(
        observation=observation,
        canonical_value=SpecificationValue(value=value),
    )


# ---------------------------------------------------------------------------
# Internal helper: positive finite Decimal
# ---------------------------------------------------------------------------

def _is_positive_finite_decimal(d: Decimal) -> bool:
    """Check that d is a positive finite Decimal (not zero, not NaN, not Inf)."""
    return d.is_finite() and d > 0


# ---------------------------------------------------------------------------
# Internal helper: strict numeric token validation
# ---------------------------------------------------------------------------

def _validate_numeric_token(num_str: str) -> str | None:
    """Validate strict numeric token grammar with proper comma grouping.

    Accepted forms:
        123                (no grouping)
        1234               (no grouping)
        1234.5             (no grouping, with decimal)
        0.5                (fractional)
        1,000              (valid thousands grouping)
        1,234,567          (valid thousands grouping)
        1,234.5            (valid thousands grouping with decimal)
        1,000,000.25       (valid thousands grouping with decimal)

    Rejected forms:
        3,84               (group not 3 digits)
        1,23               (group not 3 digits)
        1,2,3              (irregular grouping)
        1,,000             (empty group)
        1,000,00           (final group not 3 digits before decimal)
        6,8                (group not 3 digits)

    Returns the cleaned numeric string (commas removed) if valid,
    or an issue string describing the problem.
    """
    if not num_str:
        return "UNRECOGNIZED_FORMAT: empty numeric token"

    # Split into integer and decimal parts
    if "." in num_str:
        parts = num_str.split(".")
        if len(parts) != 2:
            return "UNRECOGNIZED_FORMAT: malformed decimal point"
        int_part, dec_part = parts
        if not dec_part:
            return "UNRECOGNIZED_FORMAT: trailing decimal point"
        if not dec_part.isdigit():
            return "UNRECOGNIZED_FORMAT: non-digit decimal portion"
    else:
        int_part = num_str

    # Validate integer part digits
    if not int_part:
        return "UNRECOGNIZED_FORMAT: empty integer portion"

    # Validate comma grouping in integer part
    if "," in int_part:
        groups = int_part.split(",")
        # Must not have empty groups
        if any(g == "" for g in groups):
            return "UNRECOGNIZED_FORMAT: malformed comma grouping (empty group)"
        # First group: 1-3 digits
        if len(groups[0]) < 1 or len(groups[0]) > 3 or not groups[0].isdigit():
            return "UNRECOGNIZED_FORMAT: malformed comma grouping (first group)"
        # All subsequent groups: exactly 3 digits
        for i, g in enumerate(groups[1:], 2):
            if len(g) != 3 or not g.isdigit():
                return (
                    f"UNRECOGNIZED_FORMAT: malformed comma grouping "
                    f"(group {i} has {len(g)} digits, expected 3)"
                )

    # If no commas, just verify it's all digits
    elif not int_part.isdigit():
        return "UNRECOGNIZED_FORMAT: non-digit integer portion"

    return None  # Valid


# ---------------------------------------------------------------------------
# Field-specific normalizers
# ---------------------------------------------------------------------------

# ----- capacity -----

# Regex: optional negative sign, number (with optional commas, decimal point)
# followed by optional whitespace and then a unit token.
# The numeric portion is further validated by _validate_numeric_token.
_CAPACITY_RE = re.compile(
    r"^\s*"
    r"(?P<sign>-)?"
    r"(?P<num>[0-9]+(?:,[0-9]+)*(?:\.[0-9]+)?)"
    r"\s*"
    r"(?P<unit>TB|GB)\s*$"
    r"(?![a-zA-Z])"  # no trailing alpha (reject TiB, GiB)
    , re.IGNORECASE
)


def _normalize_capacity(observation: SpecificationObservation) -> NormalizedSpecificationObservation:
    """Normalize capacity to TB (decimal SI).

    Accepts:
        X TB -> Decimal X
        X GB -> Decimal X/1000

    Rejects:
        TiB, GiB (binary units — explicit non-support)
        unitless values
        zero, negative, NaN, Infinity
        ambiguous/range values
        malformed comma grouping
    """
    raw = observation.raw_value
    if not raw or not raw.strip():
        return _issue(observation, _MISSING_OR_EMPTY_VALUE)

    # Check for binary unit indicators early
    stripped = raw.strip()
    # If TiB or GiB appears anywhere in the value, reject
    if re.search(r"\bTiB\b", stripped, re.IGNORECASE):
        return _issue(observation, f"{_UNSUPPORTED_UNIT}: TiB is not a supported unit for capacity")
    if re.search(r"\bGiB\b", stripped, re.IGNORECASE):
        return _issue(observation, f"{_UNSUPPORTED_UNIT}: GiB is not a supported unit for capacity")

    # Check for range indicators before parsing
    if "-" in stripped.replace(",", "").replace(".", "").replace(" ", ""):
        # Could be a range like "6800-7000" or "3.84-7.68"
        # More precise: check if there's a range pattern
        if re.search(r"\d[\d,.]*\s*-\s*\d", stripped):
            return _issue(observation, f"{_AMBIGUOUS_VALUE}: capacity contains a range")

    # Check for "up to" or other qualifiers
    lower = stripped.lower()
    if lower.startswith("up to") or "depending" in lower or " or " in lower:
        # "up to 7.68 TB" -> ambiguous
        # "3.84 TB or 7.68 TB" -> ambiguous
        return _issue(observation, f"{_AMBIGUOUS_VALUE}: capacity value is not a single deterministic value")

    m = _CAPACITY_RE.match(stripped)
    if not m:
        return _issue(observation, f"{_UNRECOGNIZED_FORMAT}: capacity does not match expected numeric + SI unit")

    sign = m.group("sign")
    num_str = m.group("num")
    unit = m.group("unit")

    # Strict comma validation
    validation_error = _validate_numeric_token(num_str)
    if validation_error is not None:
        return _issue(observation, validation_error)

    cleaned = num_str.replace(",", "")
    try:
        value = Decimal(cleaned)
    except InvalidOperation:
        return _issue(observation, f"{_UNRECOGNIZED_FORMAT}: capacity numeric value is invalid")

    if sign:
        value = -value

    if not value.is_finite() or value <= 0:
        return _issue(observation, _OUT_OF_RANGE_OR_NON_POSITIVE)

    unit_upper = unit.upper()
    if unit_upper == "GB":
        value = value / Decimal("1000")

    return _canonical(observation, value)


# ----- storage_protocol -----

_PROTOCOL_MAP: dict[str, str] = {
    "nvme": "NVMe",
    "sata": "SATA",
    "sas": "SAS",
}


def _normalize_storage_protocol(observation: SpecificationObservation) -> NormalizedSpecificationObservation:
    """Normalize storage protocol to one of NVMe, SATA, SAS.

    Case-insensitive exact match. Rejects composite values like
    'PCIe 4.0 x4 NVMe' because 'PCIe' alone is not a storage protocol.
    """
    raw = observation.raw_value.strip() if observation.raw_value else ""
    if not raw:
        return _issue(observation, _MISSING_OR_EMPTY_VALUE)

    # Reject composite/compound values that contain multiple tokens
    # e.g. "PCIe 4.0 x4 NVMe", "U.2 NVMe", "SATA III"
    # Only accept a single clean token
    words = raw.split()
    if len(words) != 1:
        return _issue(observation, f"{_AMBIGUOUS_VALUE}: storage protocol contains multiple tokens or qualifiers")

    canonical = _PROTOCOL_MAP.get(raw.lower())
    if canonical is None:
        return _issue(observation, f"{_UNRECOGNIZED_FORMAT}: unrecognized storage protocol")

    return _canonical(observation, canonical)


# ----- pcie_generation -----

_PCIE_GEN_MAP: dict[str, str] = {
    "pcie 3.0": "PCIe 3.0",
    "pcie 4.0": "PCIe 4.0",
    "pcie 5.0": "PCIe 5.0",
    "pci express 3.0": "PCIe 3.0",
    "pci express 4.0": "PCIe 4.0",
    "pci express 5.0": "PCIe 5.0",
    "gen3": "PCIe 3.0",
    "gen4": "PCIe 4.0",
    "gen5": "PCIe 5.0",
    "pcie gen3": "PCIe 3.0",
    "pcie gen4": "PCIe 4.0",
    "pcie gen5": "PCIe 5.0",
    "gen 3": "PCIe 3.0",
    "gen 4": "PCIe 4.0",
    "gen 5": "PCIe 5.0",
}


def _normalize_pcie_generation(observation: SpecificationObservation) -> NormalizedSpecificationObservation:
    """Normalize PCIe generation to PCIe 3.0 / 4.0 / 5.0.

    Accepts narrow exact equivalents. Rejects bare 'PCIe' without generation.
    """
    raw = observation.raw_value.strip().lower() if observation.raw_value else ""
    if not raw:
        return _issue(observation, _MISSING_OR_EMPTY_VALUE)

    canonical = _PCIE_GEN_MAP.get(raw)
    if canonical is None:
        return _issue(observation, f"{_UNRECOGNIZED_FORMAT}: unrecognized PCIe generation")

    return _canonical(observation, canonical)


# ----- pcie_lane_count -----

_LANE_RE = re.compile(
    r"^\s*(?:x(?P<xcount>\d+)|(?P<count>\d+)\s*(?:lanes?)?)\s*$"
)


def _normalize_pcie_lane_count(observation: SpecificationObservation) -> NormalizedSpecificationObservation:
    """Normalize PCIe lane count to a positive whole-number Decimal.

    Accepts: x4, 4, 4 lanes
    Rejects: 4.5, 0, negative, non-numeric
    """
    raw = observation.raw_value.strip() if observation.raw_value else ""
    if not raw:
        return _issue(observation, _MISSING_OR_EMPTY_VALUE)

    m = _LANE_RE.match(raw)
    if not m:
        return _issue(observation, f"{_UNRECOGNIZED_FORMAT}: unrecognized lane count format")

    count_str = m.group("xcount") or m.group("count")
    try:
        value = Decimal(count_str)
    except InvalidOperation:
        return _issue(observation, f"{_UNRECOGNIZED_FORMAT}: lane count is not a valid number")

    # Must be a positive integer (whole number)
    if not value.is_finite() or value <= 0 or value != int(value):
        return _issue(observation, _OUT_OF_RANGE_OR_NON_POSITIVE)

    return _canonical(observation, Decimal(str(int(value))))


# ----- physical_form_factor -----

_FORM_FACTOR_MAP: dict[str, str] = {
    "2.5-inch": "2.5-inch",
    "2.5\"": "2.5-inch",
    '2.5"': "2.5-inch",
    "2.5 in": "2.5-inch",
    "2.5 inch": "2.5-inch",
    "2.5in": "2.5-inch",  # evidence-backed: real Seagate Nytro 5050 source
    "m.2": "M.2",
    "e1.s": "E1.S",
    "e3.s": "E3.S",
}


def _normalize_physical_form_factor(observation: SpecificationObservation) -> NormalizedSpecificationObservation:
    """Normalize physical form factor to 2.5-inch / M.2 / E1.S / E3.S.

    U.2 and U.3 are NOT valid form factors — they are connector names.
    """
    raw = observation.raw_value.strip().lower() if observation.raw_value else ""
    if not raw:
        return _issue(observation, _MISSING_OR_EMPTY_VALUE)

    # Explicit check for U.2/U.3 which are connectors not form factors
    u_check = raw.replace(" ", "")
    if u_check in ("u.2", "u2", "u-2", "u.3", "u3", "u-3"):
        return _issue(observation, f"{_UNRECOGNIZED_FORMAT}: U.2/U.3 are connector types, not physical form factors")

    canonical = _FORM_FACTOR_MAP.get(raw)
    if canonical is None:
        return _issue(observation, f"{_UNRECOGNIZED_FORMAT}: unrecognized physical form factor")

    return _canonical(observation, canonical)


# ----- interface_connector -----

_CONNECTOR_MAP: dict[str, str] = {
    "u.2": "U.2",
    "u2": "U.2",
    "u-2": "U.2",
    "u.3": "U.3",
    "u3": "U.3",
    "u-3": "U.3",
    "m.2": "M.2",
    "m2": "M.2",
}


def _normalize_interface_connector(observation: SpecificationObservation) -> NormalizedSpecificationObservation:
    """Normalize interface connector with narrow known spellings.

    For recognized spellings: return canonical form.
    For other non-empty values: return an issue — do not invent a taxonomy.
    """
    raw = observation.raw_value.strip() if observation.raw_value else ""
    if not raw:
        return _issue(observation, _MISSING_OR_EMPTY_VALUE)

    # Check known spellings (case-insensitive)
    lower = raw.lower()
    canonical = _CONNECTOR_MAP.get(lower)
    if canonical is not None:
        return _canonical(observation, canonical)

    # Not a known spelling — abstain rather than invent taxonomy
    return _issue(observation, f"{_UNRECOGNIZED_FORMAT}: interface connector cannot be normalized safely")


# ----- sequential_read / sequential_write (shared logic) -----

_THROUGHPUT_RE = re.compile(
    r"^\s*"
    r"(?P<sign>-)?"
    r"(?P<num>[0-9]+(?:,[0-9]+)*(?:\.[0-9]+)?)"
    r"\s*"
    r"(?P<unit>GB/s|MB/s)\s*$"
    r"(?![a-zA-Z])"  # no trailing alpha (reject GiB/s, MiB/s)
    , re.IGNORECASE
)


def _normalize_throughput(observation: SpecificationObservation) -> NormalizedSpecificationObservation:
    """Normalize throughput (sequential read/write) to MB/s (decimal SI).

    Accepts:
        X MB/s -> Decimal X
        X GB/s -> Decimal X * 1000

    Rejects:
        MiB/s, GiB/s (binary units)
        unitless values
        <= 0
        ranges
        malformed comma grouping
    """
    raw = observation.raw_value.strip() if observation.raw_value else ""
    if not raw:
        return _issue(observation, _MISSING_OR_EMPTY_VALUE)

    # Check for binary unit indicators
    if re.search(r"\bMiB/s\b", raw, re.IGNORECASE):
        return _issue(observation, f"{_UNSUPPORTED_UNIT}: MiB/s is not a supported unit")
    if re.search(r"\bGiB/s\b", raw, re.IGNORECASE):
        return _issue(observation, f"{_UNSUPPORTED_UNIT}: GiB/s is not a supported unit")

    # Check for range
    if re.search(r"\d[\d,.]*\s*-\s*\d", raw):
        return _issue(observation, f"{_AMBIGUOUS_VALUE}: throughput contains a range")

    m = _THROUGHPUT_RE.match(raw)
    if not m:
        return _issue(observation, f"{_UNRECOGNIZED_FORMAT}: throughput does not match expected format")

    sign = m.group("sign")
    num_str = m.group("num")
    unit = m.group("unit")

    # Strict comma validation
    validation_error = _validate_numeric_token(num_str)
    if validation_error is not None:
        return _issue(observation, validation_error)

    cleaned = num_str.replace(",", "")
    try:
        value = Decimal(cleaned)
    except InvalidOperation:
        return _issue(observation, f"{_UNRECOGNIZED_FORMAT}: throughput numeric value is invalid")

    if sign:
        value = -value

    if not value.is_finite() or value <= 0:
        return _issue(observation, _OUT_OF_RANGE_OR_NON_POSITIVE)

    if unit.upper() == "GB/S":
        value = value * Decimal("1000")

    return _canonical(observation, value)


# ----- random IOPS (read and write, shared logic) -----

_IOPS_RE = re.compile(
    r"^\s*"
    r"(?P<sign>-)?"
    r"(?P<num>[0-9]+(?:,[0-9]+)*(?:\.[0-9]+)?)"
    r"\s*"
    r"(?P<multiplier>[KM])?\s*"
    r"IOPS\s*$"
)


def _normalize_iops(observation: SpecificationObservation) -> NormalizedSpecificationObservation:
    """Normalize IOPS to a positive finite Decimal.

    Accepts:
        X IOPS
        X,XXX IOPS
        X K IOPS  (K = 1000)
        X M IOPS  (M = 1,000,000)

    Rejects:
        unitless values (IOPS token is required)
        ranges, <= 0, binary prefixes
        malformed comma grouping
    """
    raw = observation.raw_value.strip() if observation.raw_value else ""
    if not raw:
        return _issue(observation, _MISSING_OR_EMPTY_VALUE)

    # Check for range
    if re.search(r"\d[\d,.]*\s*-\s*\d", raw):
        return _issue(observation, f"{_AMBIGUOUS_VALUE}: IOPS value contains a range")

    m = _IOPS_RE.match(raw)
    if not m:
        return _issue(observation, f"{_UNRECOGNIZED_FORMAT}: unrecognized IOPS format (IOPS token required)")

    sign = m.group("sign")
    num_str = m.group("num")
    multiplier_str = m.group("multiplier")

    # Strict comma validation
    validation_error = _validate_numeric_token(num_str)
    if validation_error is not None:
        return _issue(observation, validation_error)

    cleaned = num_str.replace(",", "")
    try:
        value = Decimal(cleaned)
    except InvalidOperation:
        return _issue(observation, f"{_UNRECOGNIZED_FORMAT}: IOPS numeric value is invalid")

    if multiplier_str:
        if multiplier_str.upper() == "K":
            value = value * Decimal("1000")
        elif multiplier_str.upper() == "M":
            value = value * Decimal("1000000")
        else:
            return _issue(observation, f"{_UNRECOGNIZED_FORMAT}: unrecognized IOPS multiplier")

    if sign:
        value = -value

    if not value.is_finite() or value <= 0:
        return _issue(observation, _OUT_OF_RANGE_OR_NON_POSITIVE)

    return _canonical(observation, value)


# ----- endurance_dwpd -----

_DWPD_RE = re.compile(
    r"^\s*"
    r"(?P<sign>-)?"
    r"(?P<num>[0-9]+(?:,[0-9]+)*(?:\.[0-9]+)?)"
    r"\s*"
    r"(?:DWPD)?\s*$"
)


def _normalize_endurance_dwpd(observation: SpecificationObservation) -> NormalizedSpecificationObservation:
    """Normalize endurance (DWPD) to a positive finite Decimal.

    Accepts:
        X DWPD
        X.0 DWPD
        X (plain numeric, accepted because field key implies DWPD)

    Rejects:
        TBW, PBW (not derived)
        <= 0
        malformed comma grouping
    """
    raw = observation.raw_value.strip() if observation.raw_value else ""
    if not raw:
        return _issue(observation, _MISSING_OR_EMPTY_VALUE)

    # Reject TBW / PBW — not derivable without separate policy
    if re.search(r"\bTBW\b", raw, re.IGNORECASE):
        return _issue(observation, f"{_UNSUPPORTED_UNIT}: TBW cannot be derived to DWPD without a separate policy")
    if re.search(r"\bPBW\b", raw, re.IGNORECASE):
        return _issue(observation, f"{_UNSUPPORTED_UNIT}: PBW cannot be derived to DWPD without a separate policy")

    # Check for range
    if re.search(r"\d[\d,.]*\s*-\s*\d", raw):
        return _issue(observation, f"{_AMBIGUOUS_VALUE}: DWPD value contains a range")

    m = _DWPD_RE.match(raw)
    if not m:
        return _issue(observation, f"{_UNRECOGNIZED_FORMAT}: unrecognized DWPD format")

    sign = m.group("sign")
    num_str = m.group("num")

    # Strict comma validation
    validation_error = _validate_numeric_token(num_str)
    if validation_error is not None:
        return _issue(observation, validation_error)

    cleaned = num_str.replace(",", "")
    try:
        value = Decimal(cleaned)
    except InvalidOperation:
        return _issue(observation, f"{_UNRECOGNIZED_FORMAT}: DWPD numeric value is invalid")

    if sign:
        value = -value

    if not value.is_finite() or value <= 0:
        return _issue(observation, _OUT_OF_RANGE_OR_NON_POSITIVE)

    return _canonical(observation, value)


# ----- power_loss_protection -----

_BOOL_TRUE: set[str] = {"yes", "true", "supported", "enabled"}
_BOOL_FALSE: set[str] = {"no", "false", "not supported", "disabled"}


def _normalize_power_loss_protection(observation: SpecificationObservation) -> NormalizedSpecificationObservation:
    """Normalize power loss protection to True/False.

    Only explicit boolean-like tokens. Prose is rejected.
    """
    raw = observation.raw_value.strip().lower() if observation.raw_value else ""
    if not raw:
        return _issue(observation, _MISSING_OR_EMPTY_VALUE)

    if raw in _BOOL_TRUE:
        return _canonical(observation, True)
    if raw in _BOOL_FALSE:
        return _canonical(observation, False)

    return _issue(observation, f"{_UNRECOGNIZED_FORMAT}: power loss protection value is not an explicit boolean")


# ---------------------------------------------------------------------------
# Dispatcher
# ---------------------------------------------------------------------------

_NORMALIZERS: dict[str, callable] = {
    "capacity": _normalize_capacity,
    "storage_protocol": _normalize_storage_protocol,
    "pcie_generation": _normalize_pcie_generation,
    "pcie_lane_count": _normalize_pcie_lane_count,
    "physical_form_factor": _normalize_physical_form_factor,
    "interface_connector": _normalize_interface_connector,
    "sequential_read": _normalize_throughput,
    "sequential_write": _normalize_throughput,
    "random_read_iops": _normalize_iops,
    "random_write_iops": _normalize_iops,
    "endurance_dwpd": _normalize_endurance_dwpd,
    "power_loss_protection": _normalize_power_loss_protection,
}


def normalize_enterprise_ssd_observation(
    observation: SpecificationObservation,
) -> NormalizedSpecificationObservation:
    """Normalize one Enterprise SSD specification observation.

    The observation must be bound to a definition from ENTERPRISE_SSD_SCHEMA.
    The normalizer reads ONLY observation.raw_value and produces either a
    canonical SpecificationValue or a normalization issue.

    Raises:
        TypeError: observation is not a SpecificationObservation.
        ValueError: observation's definition does not belong to
            ENTERPRISE_SSD_SCHEMA.
    """
    _validate_observation(observation)
    key = observation.definition.key
    normalizer = _NORMALIZERS.get(key)
    if normalizer is None:
        # Should not happen if the definition is from this schema
        raise ValueError(
            f"No normalizer for Enterprise SSD definition '{key}'. "
            f"This indicates a schema/normalizer mismatch."
        )
    return normalizer(observation)


def normalize_enterprise_ssd_observations(
    observations: tuple[SpecificationObservation, ...],
) -> tuple[NormalizedSpecificationObservation, ...]:
    """Normalize a batch of Enterprise SSD specification observations.

    Order is preserved. No mutation of the input. Each observation is
    processed independently and caller errors propagate.

    Returns:
        Tuple of NormalizedSpecificationObservation, one per input.
    """
    if not isinstance(observations, tuple):
        raise TypeError("observations must be a tuple of SpecificationObservation")
    return tuple(normalize_enterprise_ssd_observation(obs) for obs in observations)
