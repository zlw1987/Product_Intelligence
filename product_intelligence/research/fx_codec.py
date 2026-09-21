"""Versioned codec for FX evidence snapshot (PRODUCT-INTEL.4D-C-A).

This module encodes and decodes the ``ResearchFxSnapshot`` payload
(``schema_version`` 1). It is pure Python and has no dependencies on
Django, providers, or evaluation.

Codec rules:
* Strict required keys — reject missing keys
* Reject extra keys (fail closed)
* Decimal encoded as strings; finite only; NaN/Infinity rejected
* Dates encoded as ISO 8601 (YYYY-MM-DD)
* Timezone-aware datetime encoded deterministically (ISO 8601 UTC)
* Controlled provider_id (free-form string but must be non-empty)
* Fail closed on malformed persisted payload
* Encode/decode round-trip
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timezone
from decimal import Decimal, InvalidOperation
from typing import Any


# ---------------------------------------------------------------------------
# Exception
# ---------------------------------------------------------------------------


class FxCodecError(Exception):
    """Error encoding or decoding an FX snapshot payload."""


# ---------------------------------------------------------------------------
# Domain result objects (pure)
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class FxRateEntry:
    """One persisted FX rate observation."""

    currency_code: str
    rate: Decimal

    def __post_init__(self) -> None:
        if not isinstance(self.currency_code, str):
            raise TypeError("currency_code must be a string")
        if not self.currency_code.strip():
            raise ValueError("currency_code must be non-empty")

        if not isinstance(self.rate, Decimal):
            raise TypeError("rate must be a Decimal")
        if not self.rate.is_finite():
            raise ValueError("rate must be finite; NaN/Infinity rejected")
        if self.rate <= 0:
            raise ValueError("rate must be positive")


@dataclass(frozen=True)
class FxObservationSnapshot:
    """Persisted FX observation set for one ResearchRun."""

    provider_id: str
    observation_date: str  # ISO 8601 date string (YYYY-MM-DD)
    base_currency: str
    rates: tuple[FxRateEntry, ...]
    retrieved_at: str | None  # ISO 8601 UTC datetime string or None

    def __post_init__(self) -> None:
        if not isinstance(self.provider_id, str) or not self.provider_id.strip():
            raise ValueError("provider_id must be a non-empty string")

        # Validate observation_date is a valid ISO date string
        try:
            date.fromisoformat(self.observation_date)
        except (ValueError, TypeError) as exc:
            raise ValueError(
                f"observation_date must be a valid ISO date: "
                f"{self.observation_date!r}"
            ) from exc

        if not isinstance(self.base_currency, str):
            raise TypeError("base_currency must be a string")
        if not self.base_currency.strip():
            raise ValueError("base_currency must be non-empty")

        if not isinstance(self.rates, tuple):
            raise TypeError("rates must be a tuple")
        for i, r in enumerate(self.rates):
            if not isinstance(r, FxRateEntry):
                raise TypeError(
                    f"rates[{i}] must be FxRateEntry, got {type(r).__name__}"
                )

        if self.retrieved_at is not None:
            if not isinstance(self.retrieved_at, str):
                raise TypeError("retrieved_at must be a string or None")


# ---------------------------------------------------------------------------
# V1 Codec helpers
# ---------------------------------------------------------------------------

_SCHEMA_VERSION_V1 = 1

_V1_TOP_KEYS = frozenset({
    "schema_version",
    "provider_id",
    "observation_date",
    "base_currency",
    "rates",
    "retrieved_at",
})

_V1_RATE_KEYS = frozenset({"currency_code", "rate"})


def _encode_date(d: date) -> str:
    return d.isoformat()


def _decode_date(value: Any, field_name: str) -> str:
    if not isinstance(value, str):
        raise FxCodecError(
            f"{field_name} must be a string in codec, got {type(value).__name__}"
        )
    try:
        date.fromisoformat(value)
    except ValueError as exc:
        raise FxCodecError(
            f"{field_name} is not a valid ISO date: {value!r}"
        ) from exc
    return value


def _encode_datetime(dt: datetime | None) -> str | None:
    if dt is None:
        return None
    if dt.tzinfo is None or dt.utcoffset() is None:
        raise FxCodecError(
            "Cannot encode naive datetime; must be timezone-aware"
        )
    utc_dt = dt.astimezone(timezone.utc)
    return utc_dt.strftime("%Y-%m-%dT%H:%M:%S+00:00")


def _decode_datetime(value: Any, field_name: str) -> str | None:
    if value is None:
        return None
    if not isinstance(value, str):
        raise FxCodecError(
            f"{field_name} must be a string or null, got {type(value).__name__}"
        )
    # Accept the deterministic format we encode
    if value.endswith("+00:00"):
        base = value[:-6]
    elif value.endswith("Z"):
        base = value[:-1]
    else:
        raise FxCodecError(
            f"{field_name} must be UTC (ends with +00:00 or Z): {value!r}"
        )
    try:
        datetime.strptime(base, "%Y-%m-%dT%H:%M:%S")
    except ValueError as exc:
        raise FxCodecError(
            f"{field_name} is not a valid datetime: {value!r}"
        ) from exc
    return value


def _encode_decimal(value: Decimal) -> str:
    if not isinstance(value, Decimal):
        raise FxCodecError(
            f"Cannot encode non-Decimal value: {type(value).__name__}"
        )
    if not value.is_finite():
        raise FxCodecError(f"Cannot encode non-finite Decimal: {value}")
    return str(value)


def _decode_decimal(value: Any, field_name: str) -> Decimal:
    if not isinstance(value, str):
        raise FxCodecError(
            f"{field_name} must be a string in codec, got {type(value).__name__}"
        )
    upper = value.upper().strip()
    if upper in ("NAN", "INF", "INFINITY", "-INF", "-INFINITY"):
        raise FxCodecError(f"{field_name} is non-finite: {value!r}")
    try:
        result = Decimal(value)
    except (InvalidOperation, ValueError) as exc:
        raise FxCodecError(
            f"{field_name} is not a valid decimal: {value!r}"
        ) from exc
    if not result.is_finite():
        raise FxCodecError(f"{field_name} is non-finite: {value!r}")
    if result <= 0:
        raise FxCodecError(f"{field_name} must be positive: {value!r}")
    return result


# ---------------------------------------------------------------------------
# Public encode/decode
# ---------------------------------------------------------------------------


def encode_fx_observation(
    provider_id: str,
    observation_date: date,
    base_currency: str,
    rates: tuple["FxRateObservation", ...],
    retrieved_at: datetime | None = None,
) -> dict[str, Any]:
    """Encode an FX observation into a V1 payload dict.

    Import FxRateObservation lazily to avoid circular dependency
    with the provider module in the codec.

    Args:
        provider_id: Provider identifier (e.g. "ECB").
        observation_date: The date of the rates.
        base_currency: The base currency code (e.g. "EUR").
        rates: Tuple of rate observations (from providers/fx.py).
        retrieved_at: When the rates were fetched (timezone-aware).

    Returns:
        A JSON-serializable dict for persistence.
    """
    # Validate inputs
    if not isinstance(provider_id, str) or not provider_id.strip():
        raise FxCodecError("provider_id must be a non-empty string")
    if not isinstance(observation_date, date):
        raise FxCodecError(
            f"observation_date must be a date, got {type(observation_date).__name__}"
        )
    if not isinstance(base_currency, str) or not base_currency.strip():
        raise FxCodecError("base_currency must be a non-empty string")
    if not isinstance(rates, tuple):
        raise FxCodecError("rates must be a tuple")

    rate_dicts = []
    for obs in rates:
        rate_dicts.append({
            "currency_code": obs.currency_code,
            "rate": _encode_decimal(obs.rate),
        })

    return {
        "schema_version": _SCHEMA_VERSION_V1,
        "provider_id": provider_id.strip(),
        "observation_date": _encode_date(observation_date),
        "base_currency": base_currency.strip().upper(),
        "rates": rate_dicts,
        "retrieved_at": _encode_datetime(retrieved_at),
    }


def decode_fx_observation(
    payload: dict[str, Any],
) -> FxObservationSnapshot:
    """Decode a V1 FX payload dict into an FxObservationSnapshot.

    Raises FxCodecError on any validation failure.
    Rejects extra keys and unknown values (fail closed).
    """
    if not isinstance(payload, dict):
        raise FxCodecError("payload must be a dict")

    top_keys = set(payload.keys())
    extra_keys = top_keys - _V1_TOP_KEYS
    if extra_keys:
        raise FxCodecError(f"unexpected top-level keys: {sorted(extra_keys)}")
    missing_keys = _V1_TOP_KEYS - top_keys
    if missing_keys:
        raise FxCodecError(f"missing top-level keys: {sorted(missing_keys)}")

    # Schema version
    schema_version = payload.get("schema_version")
    if schema_version != _SCHEMA_VERSION_V1:
        raise FxCodecError(
            f"unsupported schema_version: {schema_version!r}; "
            f"expected {_SCHEMA_VERSION_V1}"
        )

    # Provider ID
    provider_id = payload["provider_id"]
    if not isinstance(provider_id, str) or not provider_id.strip():
        raise FxCodecError("provider_id must be a non-empty string")

    # Observation date
    observation_date = _decode_date(payload["observation_date"], "observation_date")

    # Base currency
    base_currency = payload["base_currency"]
    if not isinstance(base_currency, str) or not base_currency.strip():
        raise FxCodecError("base_currency must be a non-empty string")

    # Rates
    rates_raw = payload["rates"]
    if not isinstance(rates_raw, list):
        raise FxCodecError("rates must be a list")

    rate_entries: list[FxRateEntry] = []
    for idx, rate_raw in enumerate(rates_raw):
        if not isinstance(rate_raw, dict):
            raise FxCodecError(f"rates[{idx}] must be a dict")

        rate_keys = set(rate_raw.keys())
        extra_rate_keys = rate_keys - _V1_RATE_KEYS
        if extra_rate_keys:
            raise FxCodecError(
                f"unexpected keys in rates[{idx}]: {sorted(extra_rate_keys)}"
            )
        missing_rate_keys = _V1_RATE_KEYS - rate_keys
        if missing_rate_keys:
            raise FxCodecError(
                f"missing keys in rates[{idx}]: {sorted(missing_rate_keys)}"
            )

        currency_code = rate_raw["currency_code"]
        if not isinstance(currency_code, str) or not currency_code.strip():
            raise FxCodecError(
                f"rates[{idx}].currency_code must be a non-empty string"
            )

        rate_val = _decode_decimal(rate_raw["rate"], f"rates[{idx}].rate")

        rate_entries.append(FxRateEntry(
            currency_code=currency_code.strip().upper(),
            rate=rate_val,
        ))

    # Retrieved at
    retrieved_at = _decode_datetime(payload["retrieved_at"], "retrieved_at")

    return FxObservationSnapshot(
        provider_id=provider_id.strip(),
        observation_date=observation_date,
        base_currency=base_currency.strip().upper(),
        rates=tuple(rate_entries),
        retrieved_at=retrieved_at,
    )
