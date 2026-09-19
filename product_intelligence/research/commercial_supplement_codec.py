"""Versioned codec for the research supplemental snapshot (PRODUCT-INTEL.4D-B).

This module encodes and decodes the ``ResearchSupplementSnapshot`` payload
(``schema_version`` 1). It is pure Python, provider-neutral, and has no
dependencies on Django, providers, research identity, or evaluation.

Codec rules:
* Strict required keys — reject missing keys
* Reject extra keys (fail closed)
* Decimal encoded as strings; finite only; NaN/Infinity rejected
* Timezone-aware datetime encoded deterministically (ISO 8601 UTC)
* Naive datetime rejected on encode
* Controlled enum/value validation
* Fail closed on malformed persisted payload
* Encode/decode round-trip
* quantity: int only, bool rejected, nonnegative
* brand_new_basis: exactly "VENDOR_API_POLICY" for V1
* vendor_mpn_match_type: EXACT or NORMALIZED_EXACT only
* No provider imports
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
from math import isfinite
from typing import Any


# ---------------------------------------------------------------------------
# Exception
# ---------------------------------------------------------------------------


class SupplementCodecError(Exception):
    """Error encoding or decoding a supplemental payload."""


# ---------------------------------------------------------------------------
# Domain result objects (pure, no provider imports)
# ---------------------------------------------------------------------------


class SupplementLookupStatus:
    """Vocabulary for lookup status."""
    SUCCESS = "SUCCESS"
    PARTIAL = "PARTIAL"
    FAILED = "FAILED"
    ALL = frozenset({SUCCESS, PARTIAL, FAILED})


class SupplementSourceOutcome:
    """Vocabulary for per-source outcomes."""
    USABLE = "USABLE"
    NOT_FOUND = "NOT_FOUND"
    MALFORMED_SECTION = "MALFORMED_SECTION"
    MISSING_EXPLICIT_MPN = "MISSING_EXPLICIT_MPN"
    MPN_MISMATCH = "MPN_MISMATCH"
    ALL = frozenset({
        USABLE, NOT_FOUND, MALFORMED_SECTION,
        MISSING_EXPLICIT_MPN, MPN_MISMATCH,
    })


class SupplementAvailability:
    """Vocabulary for commercial availability."""
    IN_STOCK = "IN_STOCK"
    OUT_OF_STOCK = "OUT_OF_STOCK"
    UNKNOWN = "UNKNOWN"
    ALL = frozenset({IN_STOCK, OUT_OF_STOCK, UNKNOWN})


class SupplementPriceBasis:
    """Vocabulary for price basis."""
    CUSTOMER_PRICE = "CUSTOMER_PRICE"
    RETAIL_PRICE_FALLBACK = "RETAIL_PRICE_FALLBACK"
    LIST_PRICE = "LIST_PRICE"
    ALL = frozenset({CUSTOMER_PRICE, RETAIL_PRICE_FALLBACK, LIST_PRICE})


class SupplementNoteKind:
    """Vocabulary for bounded note kinds."""
    NO_RETURNS = "NO_RETURNS"
    ALL = frozenset({NO_RETURNS})


@dataclass(frozen=True)
class SupplementSourceObservation:
    """One identity-bound commercial observation in the supplemental result."""

    source_name: str
    explicit_candidate_mpn: str
    vendor_mpn_match_type: str  # EXACT or NORMALIZED_EXACT
    price_amount: Decimal
    currency_code: str
    availability: str
    price_basis: str
    quantity: int | None
    note_kind: str | None
    brand_new: bool
    brand_new_basis: str

    def __post_init__(self) -> None:
        # source_name
        if not isinstance(self.source_name, str) or not self.source_name.strip():
            raise ValueError("source_name must be a non-empty string")

        # explicit_candidate_mpn
        if not isinstance(self.explicit_candidate_mpn, str):
            raise TypeError("explicit_candidate_mpn must be a string")
        if not self.explicit_candidate_mpn.strip():
            raise ValueError("explicit_candidate_mpn must be non-empty")

        # vendor_mpn_match_type — EXACT or NORMALIZED_EXACT only
        if self.vendor_mpn_match_type not in ("EXACT", "NORMALIZED_EXACT"):
            raise ValueError(
                f"vendor_mpn_match_type must be EXACT or NORMALIZED_EXACT, "
                f"got {self.vendor_mpn_match_type!r}"
            )

        # price_amount — Decimal only, finite only
        if not isinstance(self.price_amount, Decimal):
            raise TypeError("price_amount must be a Decimal")
        if not isfinite(float(self.price_amount)):
            raise ValueError("price_amount must be finite; NaN/Infinity rejected")
        if self.price_amount < 0:
            raise ValueError("price_amount must not be negative")

        # currency_code
        if not isinstance(self.currency_code, str) or not self.currency_code.strip():
            raise ValueError("currency_code must be a non-empty string")

        # availability
        if self.availability not in SupplementAvailability.ALL:
            raise ValueError(f"invalid availability: {self.availability!r}")

        # price_basis
        if self.price_basis not in SupplementPriceBasis.ALL:
            raise ValueError(f"invalid price_basis: {self.price_basis!r}")

        # quantity — int only, bool rejected, nonnegative
        if self.quantity is not None:
            if type(self.quantity) is not int:
                raise TypeError(
                    f"quantity must be an int or None, got "
                    f"{type(self.quantity).__name__}"
                )
            if self.quantity < 0:
                raise ValueError("quantity must not be negative")

        # note_kind
        if self.note_kind is not None:
            if not isinstance(self.note_kind, str):
                raise TypeError("note_kind must be a string or None")
            if self.note_kind not in SupplementNoteKind.ALL:
                raise ValueError(f"invalid note_kind: {self.note_kind!r}")

        # brand_new
        if not isinstance(self.brand_new, bool):
            raise TypeError("brand_new must be a bool")

        # brand_new_basis — V1 requires exactly VENDOR_API_POLICY
        if self.brand_new_basis != "VENDOR_API_POLICY":
            raise ValueError(
                f"brand_new_basis must be 'VENDOR_API_POLICY', "
                f"got {self.brand_new_basis!r}"
            )


@dataclass(frozen=True)
class SupplementSourceIssue:
    """One per-source issue in the supplemental result."""

    source_name: str
    outcome: str
    detail: str | None

    def __post_init__(self) -> None:
        if not isinstance(self.source_name, str) or not self.source_name.strip():
            raise ValueError("source_name must be a non-empty string")

        if self.outcome not in SupplementSourceOutcome.ALL:
            raise ValueError(f"invalid outcome: {self.outcome!r}")

        if self.detail is not None and not isinstance(self.detail, str):
            raise TypeError("detail must be a string or None")


@dataclass(frozen=True)
class VendorCommercialResult:
    """The vendor-commercial lookup result for the supplemental snapshot."""

    lookup_status: str  # SUCCESS, PARTIAL, FAILED
    retrieved_at: datetime | None  # timezone-aware datetime
    observations: tuple[SupplementSourceObservation, ...]
    source_issues: tuple[SupplementSourceIssue, ...]

    def __post_init__(self) -> None:
        if self.lookup_status not in SupplementLookupStatus.ALL:
            raise ValueError(f"invalid lookup_status: {self.lookup_status!r}")

        if self.retrieved_at is not None:
            if not isinstance(self.retrieved_at, datetime):
                raise TypeError("retrieved_at must be a datetime or None")
            if self.retrieved_at.tzinfo is None:
                raise ValueError("retrieved_at must be timezone-aware when present")
            if self.retrieved_at.utcoffset() is None:
                raise ValueError("retrieved_at must be timezone-aware when present")

        if not isinstance(self.observations, tuple):
            raise TypeError("observations must be a tuple")
        for i, obs in enumerate(self.observations):
            if not isinstance(obs, SupplementSourceObservation):
                raise TypeError(
                    f"observations[{i}] must be SupplementSourceObservation"
                )

        if not isinstance(self.source_issues, tuple):
            raise TypeError("source_issues must be a tuple")
        for i, issue in enumerate(self.source_issues):
            if not isinstance(issue, SupplementSourceIssue):
                raise TypeError(
                    f"source_issues[{i}] must be SupplementSourceIssue"
                )


@dataclass(frozen=True)
class ResearchSupplementResult:
    """The complete supplemental research result."""

    vendor_commercial_result: VendorCommercialResult

    def __post_init__(self) -> None:
        if not isinstance(self.vendor_commercial_result, VendorCommercialResult):
            raise TypeError(
                "vendor_commercial_result must be VendorCommercialResult"
            )


# ---------------------------------------------------------------------------
# V1 Codec
# ---------------------------------------------------------------------------

_SCHEMA_VERSION_V1 = 1

# Required keys at each level
_V1_TOP_KEYS = frozenset({"schema_version", "vendor_commercial_result"})
_V1_VCR_KEYS = frozenset({
    "lookup_status",
    "retrieved_at",
    "observations",
    "source_issues",
})
_V1_OBSERVATION_KEYS = frozenset({
    "source_name",
    "explicit_candidate_mpn",
    "vendor_mpn_match_type",
    "price_amount",
    "currency_code",
    "availability",
    "price_basis",
    "quantity",
    "note_kind",
    "brand_new",
    "brand_new_basis",
})
_V1_ISSUE_KEYS = frozenset({
    "source_name",
    "outcome",
    "detail",
})


def _encode_datetime(dt: datetime | None) -> str | None:
    """Encode a timezone-aware datetime as ISO 8601 UTC string.

    Raises SupplementCodecError if datetime is naive.
    """
    if dt is None:
        return None
    if dt.tzinfo is None or dt.utcoffset() is None:
        raise SupplementCodecError(
            "Cannot encode naive datetime; must be timezone-aware"
        )
    utc_dt = dt.astimezone(timezone.utc)
    return utc_dt.strftime("%Y-%m-%dT%H:%M:%S+00:00")


def _decode_datetime(value: str | None) -> datetime | None:
    """Decode an ISO 8601 UTC string to a timezone-aware datetime.

    Raises SupplementCodecError on malformed input or non-UTC offset.
    """
    if value is None:
        return None
    if not isinstance(value, str):
        raise SupplementCodecError(
            f"retrieved_at must be a string or null, got {type(value).__name__}"
        )
    try:
        # Parse the deterministic format
        if value.endswith("+00:00"):
            base = value[:-6]
        elif value.endswith("Z"):
            base = value[:-1]
        else:
            raise SupplementCodecError(
                f"retrieved_at must be UTC (ends with +00:00 or Z): {value!r}"
            )
        dt = datetime.strptime(base, "%Y-%m-%dT%H:%M:%S")
        return dt.replace(tzinfo=timezone.utc)
    except (ValueError, TypeError) as exc:
        raise SupplementCodecError(
            f"invalid retrieved_at datetime: {value!r}"
        ) from exc


def _encode_decimal(value: Decimal) -> str:
    """Encode a Decimal as its string representation.

    Raises SupplementCodecError for non-finite values.
    """
    if not isinstance(value, Decimal):
        raise SupplementCodecError(
            f"Cannot encode non-Decimal value: {type(value).__name__}"
        )
    if not isfinite(float(value)):
        raise SupplementCodecError(
            f"Cannot encode non-finite Decimal: {value}"
        )
    return str(value)


def _decode_decimal(value: Any, field_name: str) -> Decimal:
    """Decode a string value as Decimal, fail closed.

    Rejects NaN, Infinity, non-string values.
    """
    if not isinstance(value, str):
        raise SupplementCodecError(
            f"{field_name} must be a string in codec, got "
            f"{type(value).__name__}"
        )
    # Reject explicit NaN/Infinity strings
    upper = value.upper().strip()
    if upper in ("NAN", "INF", "INFINITY", "-INF", "-INFINITY"):
        raise SupplementCodecError(
            f"{field_name} is non-finite: {value!r}"
        )
    try:
        result = Decimal(value)
    except (InvalidOperation, ValueError) as exc:
        raise SupplementCodecError(
            f"{field_name} is not a valid decimal: {value!r}"
        ) from exc
    # Reject NaN/Infinity that Decimal might parse
    if not isfinite(float(result)):
        raise SupplementCodecError(
            f"{field_name} is non-finite: {value!r}"
        )
    return result


def encode_research_supplement_result(
    result: ResearchSupplementResult,
) -> dict[str, Any]:
    """Encode a ResearchSupplementResult to a V1 payload dict.

    Returns a JSON-serializable dict suitable for persistence.
    Raises SupplementCodecError on any validation failure.
    """
    vcr = result.vendor_commercial_result

    # Validate lookup_status before encoding
    if vcr.lookup_status not in SupplementLookupStatus.ALL:
        raise SupplementCodecError(
            f"invalid lookup_status for encoding: {vcr.lookup_status!r}"
        )

    observations = []
    for obs in vcr.observations:
        observations.append({
            "source_name": obs.source_name,
            "explicit_candidate_mpn": obs.explicit_candidate_mpn,
            "vendor_mpn_match_type": obs.vendor_mpn_match_type,
            "price_amount": _encode_decimal(obs.price_amount),
            "currency_code": obs.currency_code,
            "availability": obs.availability,
            "price_basis": obs.price_basis,
            "quantity": obs.quantity,
            "note_kind": obs.note_kind,
            "brand_new": obs.brand_new,
            "brand_new_basis": obs.brand_new_basis,
        })

    source_issues = []
    for issue in vcr.source_issues:
        source_issues.append({
            "source_name": issue.source_name,
            "outcome": issue.outcome,
            "detail": issue.detail,
        })

    return {
        "schema_version": _SCHEMA_VERSION_V1,
        "vendor_commercial_result": {
            "lookup_status": vcr.lookup_status,
            "retrieved_at": _encode_datetime(vcr.retrieved_at),
            "observations": observations,
            "source_issues": source_issues,
        },
    }


def decode_research_supplement_result(
    payload: dict[str, Any],
) -> ResearchSupplementResult:
    """Decode a V1 payload dict to a ResearchSupplementResult.

    Raises SupplementCodecError on any validation failure.
    Rejects extra keys and unknown values (fail closed).
    retrieved_at is decoded through _decode_datetime -> timezone-aware datetime.
    """
    # Check schema version
    if not isinstance(payload, dict):
        raise SupplementCodecError("payload must be a dict")

    top_keys = set(payload.keys())
    extra_keys = top_keys - _V1_TOP_KEYS
    if extra_keys:
        raise SupplementCodecError(
            f"unexpected top-level keys: {sorted(extra_keys)}"
        )
    missing_keys = _V1_TOP_KEYS - top_keys
    if missing_keys:
        raise SupplementCodecError(
            f"missing top-level keys: {sorted(missing_keys)}"
        )

    schema_version = payload.get("schema_version")
    if schema_version != _SCHEMA_VERSION_V1:
        raise SupplementCodecError(
            f"unsupported schema_version: {schema_version!r}; "
            f"expected {_SCHEMA_VERSION_V1}"
        )

    # Decode vendor_commercial_result
    vcr_raw = payload["vendor_commercial_result"]
    if not isinstance(vcr_raw, dict):
        raise SupplementCodecError("vendor_commercial_result must be a dict")

    vcr_keys = set(vcr_raw.keys())
    extra_vcr_keys = vcr_keys - _V1_VCR_KEYS
    if extra_vcr_keys:
        raise SupplementCodecError(
            f"unexpected vendor_commercial_result keys: {sorted(extra_vcr_keys)}"
        )
    missing_vcr_keys = _V1_VCR_KEYS - vcr_keys
    if missing_vcr_keys:
        raise SupplementCodecError(
            f"missing vendor_commercial_result keys: {sorted(missing_vcr_keys)}"
        )

    # lookup_status
    lookup_status = vcr_raw["lookup_status"]
    if lookup_status not in SupplementLookupStatus.ALL:
        raise SupplementCodecError(
            f"invalid lookup_status: {lookup_status!r}"
        )

    # retrieved_at — decode through datetime decoder (returns aware datetime)
    retrieved_at_raw = vcr_raw["retrieved_at"]
    retrieved_at = _decode_datetime(retrieved_at_raw)

    # Decode observations
    obs_raw_list = vcr_raw["observations"]
    if not isinstance(obs_raw_list, list):
        raise SupplementCodecError("observations must be a list")

    observations: list[SupplementSourceObservation] = []
    for idx, obs_raw in enumerate(obs_raw_list):
        if not isinstance(obs_raw, dict):
            raise SupplementCodecError(
                f"observations[{idx}] must be a dict"
            )
        obs_keys = set(obs_raw.keys())
        extra_obs_keys = obs_keys - _V1_OBSERVATION_KEYS
        if extra_obs_keys:
            raise SupplementCodecError(
                f"unexpected keys in observations[{idx}]: {sorted(extra_obs_keys)}"
            )
        missing_obs_keys = _V1_OBSERVATION_KEYS - obs_keys
        if missing_obs_keys:
            raise SupplementCodecError(
                f"missing keys in observations[{idx}]: {sorted(missing_obs_keys)}"
            )

        # Validate enums
        availability = obs_raw["availability"]
        if availability not in SupplementAvailability.ALL:
            raise SupplementCodecError(
                f"invalid availability in observations[{idx}]: {availability!r}"
            )

        price_basis = obs_raw["price_basis"]
        if price_basis not in SupplementPriceBasis.ALL:
            raise SupplementCodecError(
                f"invalid price_basis in observations[{idx}]: {price_basis!r}"
            )

        vendor_mpn_match_type = obs_raw["vendor_mpn_match_type"]
        if vendor_mpn_match_type not in ("EXACT", "NORMALIZED_EXACT"):
            raise SupplementCodecError(
                f"invalid vendor_mpn_match_type in observations[{idx}]: "
                f"{vendor_mpn_match_type!r}"
            )

        note_kind = obs_raw["note_kind"]
        if note_kind is not None:
            if not isinstance(note_kind, str):
                raise SupplementCodecError(
                    f"note_kind in observations[{idx}] must be a string or null"
                )
            if note_kind not in SupplementNoteKind.ALL:
                raise SupplementCodecError(
                    f"invalid note_kind in observations[{idx}]: {note_kind!r}"
                )

        quantity = obs_raw["quantity"]
        if quantity is not None:
            # bool MUST be rejected (bool is subclass of int)
            if type(quantity) is not int:
                raise SupplementCodecError(
                    f"quantity in observations[{idx}] must be an int or null, "
                    f"got {type(quantity).__name__}"
                )
            if quantity < 0:
                raise SupplementCodecError(
                    f"quantity in observations[{idx}] must be non-negative"
                )

        brand_new = obs_raw["brand_new"]
        if not isinstance(brand_new, bool):
            raise SupplementCodecError(
                f"brand_new in observations[{idx}] must be a bool"
            )

        price_amount = _decode_decimal(obs_raw["price_amount"], "price_amount")

        # brand_new_basis validation
        brand_new_basis = obs_raw["brand_new_basis"]
        if brand_new_basis != "VENDOR_API_POLICY":
            raise SupplementCodecError(
                f"invalid brand_new_basis in observations[{idx}]: "
                f"{brand_new_basis!r}"
            )

        observations.append(SupplementSourceObservation(
            source_name=obs_raw["source_name"],
            explicit_candidate_mpn=obs_raw["explicit_candidate_mpn"],
            vendor_mpn_match_type=vendor_mpn_match_type,
            price_amount=price_amount,
            currency_code=obs_raw["currency_code"],
            availability=availability,
            price_basis=price_basis,
            quantity=quantity,
            note_kind=note_kind,
            brand_new=brand_new,
            brand_new_basis=brand_new_basis,
        ))

    # Decode source_issues
    issues_raw_list = vcr_raw["source_issues"]
    if not isinstance(issues_raw_list, list):
        raise SupplementCodecError("source_issues must be a list")

    source_issues: list[SupplementSourceIssue] = []
    for idx, issue_raw in enumerate(issues_raw_list):
        if not isinstance(issue_raw, dict):
            raise SupplementCodecError(
                f"source_issues[{idx}] must be a dict"
            )
        issue_keys = set(issue_raw.keys())
        extra_issue_keys = issue_keys - _V1_ISSUE_KEYS
        if extra_issue_keys:
            raise SupplementCodecError(
                f"unexpected keys in source_issues[{idx}]: {sorted(extra_issue_keys)}"
            )
        missing_issue_keys = _V1_ISSUE_KEYS - issue_keys
        if missing_issue_keys:
            raise SupplementCodecError(
                f"missing keys in source_issues[{idx}]: {sorted(missing_issue_keys)}"
            )

        outcome = issue_raw["outcome"]
        if outcome not in SupplementSourceOutcome.ALL:
            raise SupplementCodecError(
                f"invalid outcome in source_issues[{idx}]: {outcome!r}"
            )

        source_issues.append(SupplementSourceIssue(
            source_name=issue_raw["source_name"],
            outcome=outcome,
            detail=issue_raw["detail"],
        ))

    return ResearchSupplementResult(
        vendor_commercial_result=VendorCommercialResult(
            lookup_status=lookup_status,
            retrieved_at=retrieved_at,
            observations=tuple(observations),
            source_issues=tuple(source_issues),
        ),
    )
