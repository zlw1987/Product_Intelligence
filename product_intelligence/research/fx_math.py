"""Decimal-only FX mathematics for USD-equivalent calculation (PRODUCT-INTEL.4D-C-A).

This module provides pure, deterministic functions to convert a price amount
from one currency to USD using persisted ECB reference rates. It is:

* Pure: no I/O, no network, no Django, no persistence
* Decimal-only: no binary float anywhere in the arithmetic path
* Deterministic: same inputs always produce same output
* Fail-closed: missing rates produce "unavailable", never a guess

ECB reference rates are EUR-based:
    1 EUR = rate_C C
    1 EUR = rate_USD USD

For a non-USD, non-EUR currency C:
    USD Equivalent = amount_C / rate_C * rate_USD

For EUR itself:
    USD Equivalent = amount_EUR * rate_USD
    (rate_EUR = 1 by definition, not always in the rate set)

For USD:
    USD Equivalent = original USD amount (pass-through)

What this module deliberately does NOT do:
* fetch live rates (that is providers/fx.py)
* persist anything (that is research/fx_codec.py + runs/models.py)
* round or format values (that is presentation layer work)
* validate currency codes beyond what rates support
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from product_intelligence.research.fx_codec import FxObservationSnapshot


# ---------------------------------------------------------------------------
# Result types
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class UsdEquivalentResult:
    """The result of converting one price to USD equivalent.

    Attributes:
        original_amount: The original price amount (Decimal).
        original_currency: The original currency code.
        usd_equivalent: The USD-equivalent amount, or None if unavailable.
        conversion_available: True if the conversion succeeded.
        reason: Explanation when conversion is unavailable, or None if available.
    """

    original_amount: Decimal
    original_currency: str
    usd_equivalent: Decimal | None
    conversion_available: bool
    reason: str | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.original_amount, Decimal):
            raise TypeError(
                f"original_amount must be a Decimal, got "
                f"{type(self.original_amount).__name__}"
            )
        if not self.original_amount.is_finite():
            raise ValueError("original_amount must be finite")

        if not isinstance(self.original_currency, str):
            raise TypeError(
                f"original_currency must be a string, got "
                f"{type(self.original_currency).__name__}"
            )
        if not self.original_currency.strip():
            raise ValueError("original_currency must be non-empty")

        if self.usd_equivalent is not None:
            if not isinstance(self.usd_equivalent, Decimal):
                raise TypeError(
                    f"usd_equivalent must be a Decimal or None, got "
                    f"{type(self.usd_equivalent).__name__}"
                )
            if not self.usd_equivalent.is_finite():
                raise ValueError("usd_equivalent must be finite when present")

        if self.conversion_available:
            if self.usd_equivalent is None:
                raise ValueError(
                    "conversion_available=True requires a non-None usd_equivalent"
                )
            if self.reason is not None:
                raise ValueError(
                    "conversion_available=True requires reason=None"
                )
        else:
            if self.usd_equivalent is not None:
                raise ValueError(
                    "conversion_available=False requires usd_equivalent=None"
                )


# ---------------------------------------------------------------------------
# Core conversion
# ---------------------------------------------------------------------------


def compute_usd_equivalent(
    amount: Decimal,
    currency: str,
    fx_snapshot: FxObservationSnapshot | None,
) -> UsdEquivalentResult:
    """Compute the USD equivalent of a price using persisted FX rates.

    Uses the ECB formula with Decimal-only arithmetic:
        For USD: pass-through (USD Equivalent = original amount)
        For EUR: amount_EUR * rate_USD
        For other currency C: amount_C / rate_C * rate_USD
        For unknown currency: unavailable

    Args:
        amount: The original price amount (must be Decimal, finite).
        currency: The original currency code (e.g. "USD", "EUR", "GBP").
        fx_snapshot: The persisted FX observation snapshot, or None
            if FX evidence is not available for this run.

    Returns:
        UsdEquivalentResult with the conversion result.
    """
    # Validate inputs
    if not isinstance(amount, Decimal):
        raise TypeError(
            f"amount must be a Decimal, got {type(amount).__name__}"
        )
    if not amount.is_finite():
        raise ValueError("amount must be finite")

    currency_upper = currency.strip().upper() if isinstance(currency, str) else currency

    # No FX evidence at all
    if fx_snapshot is None:
        if currency_upper == "USD":
            return UsdEquivalentResult(
                original_amount=amount,
                original_currency=currency_upper,
                usd_equivalent=amount,
                conversion_available=True,
            )
        return UsdEquivalentResult(
            original_amount=amount,
            original_currency=currency_upper,
            usd_equivalent=None,
            conversion_available=False,
            reason="no FX evidence persisted for this run",
        )

    base_currency = fx_snapshot.base_currency.upper()

    # USD is always pass-through, regardless of FX evidence
    if currency_upper == "USD":
        return UsdEquivalentResult(
            original_amount=amount,
            original_currency=currency_upper,
            usd_equivalent=amount,
            conversion_available=True,
        )

    # Need rate_USD for any non-USD conversion
    usd_rate_entry = None
    for entry in fx_snapshot.rates:
        if entry.currency_code == "USD":
            usd_rate_entry = entry
            break

    if usd_rate_entry is None:
        return UsdEquivalentResult(
            original_amount=amount,
            original_currency=currency_upper,
            usd_equivalent=None,
            conversion_available=False,
            reason="USD rate not available in FX evidence",
        )

    rate_usd = usd_rate_entry.rate

    # EUR is the base currency — rate_EUR = 1 by definition
    if currency_upper == base_currency:
        # USD Equivalent = amount_EUR * rate_USD
        usd_equiv = amount * rate_usd
        return UsdEquivalentResult(
            original_amount=amount,
            original_currency=currency_upper,
            usd_equivalent=usd_equiv,
            conversion_available=True,
        )

    # General case: find rate for currency C
    currency_rate_entry = None
    for entry in fx_snapshot.rates:
        if entry.currency_code == currency_upper:
            currency_rate_entry = entry
            break

    if currency_rate_entry is None:
        return UsdEquivalentResult(
            original_amount=amount,
            original_currency=currency_upper,
            usd_equivalent=None,
            conversion_available=False,
            reason=f"rate for {currency_upper} not available in FX evidence",
        )

    rate_c = currency_rate_entry.rate

    # ECB formula: USD Equivalent = amount_C / rate_C * rate_USD
    # Using Decimal arithmetic throughout
    usd_equiv = (amount / rate_c) * rate_usd

    return UsdEquivalentResult(
        original_amount=amount,
        original_currency=currency_upper,
        usd_equivalent=usd_equiv,
        conversion_available=True,
    )
