"""Compact quote-summary projection (PRODUCT-INTEL.4D-C-A).

This module defines the provider-neutral, presentation-neutral projection
contract for the compact quote summary table. It produces pure data objects
that can later feed a 4D-C HTML table.

**No browser HTML is rendered here.** The projection produces Python objects
containing the display values. HTML rendering belongs to a later task after
the security gate is independently verified.

What this module does:
* Map public listing condition to Brand New display
* Map Vendor API availability to inventory display
* Compute USD Equivalent from persisted FX evidence
* Apply source-label conventions
* Preserve original source price amount and currency

What this module does NOT do:
* Render HTML or any browser-visible format
* Change Machine Price or Reviewed Price
* Enter semantic identity or comparable scoring
* Affect 4D-A fallback or search decisions
* Fetch live data (all inputs are provided by the caller)
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from product_intelligence.research.fx_codec import FxObservationSnapshot
from product_intelligence.research.fx_math import (
    UsdEquivalentResult,
    compute_usd_equivalent,
)

# ---------------------------------------------------------------------------
# Source label conventions
# ---------------------------------------------------------------------------

# Vendor API source labels (normalized)
_LABEL_INGRAM = "Ingram"
_LABEL_CDW = "CDW"
_LABEL_SYNNEX_EU = "Synnex EU (Vendor API)"

# Public listing source label: source_name as observed


# ---------------------------------------------------------------------------
# Inventory display mapping
# ---------------------------------------------------------------------------

# From frozen 3B NormalizedAvailability (public listings)
# and 4D-B CommercialAvailability (vendor API)


def _map_public_listing_inventory(
    availability: str,
) -> tuple[str, str | None]:
    """Map a public listing availability to (display_text, optional_note).

    Args:
        availability: NormalizedAvailability value from frozen 3B.

    Returns:
        (display_label, note_or_None)
    """
    if availability == "IN_STOCK":
        return "In Stock", None
    elif availability == "LIMITED":
        return "In Stock", "Limited"
    elif availability == "OUT_OF_STOCK":
        return "Out of Stock", None
    elif availability in ("PREORDER", "BACKORDER", "DISCONTINUED"):
        return "Out of Stock", availability
    else:
        # UNKNOWN or any other unmapped value
        return "Unknown", None


def _map_vendor_api_inventory(
    availability: str,
) -> tuple[str, str | None]:
    """Map a vendor API availability to (display_text, optional_note).

    Vendor API uses CommercialAvailability from 4D-B (IN_STOCK, OUT_OF_STOCK,
    UNKNOWN) plus the LIMITED mapping from the compact quote spec.

    Args:
        availability: CommercialAvailability or extended value.

    Returns:
        (display_label, note_or_None)
    """
    if availability == "IN_STOCK":
        return "In Stock", None
    elif availability == "LIMITED":
        return "In Stock", "Limited"
    elif availability == "OUT_OF_STOCK":
        return "Out of Stock", None
    elif availability in ("PREORDER", "BACKORDER", "DISCONTINUED"):
        return "Out of Stock", availability
    else:
        # UNKNOWN
        return "Unknown", None


# ---------------------------------------------------------------------------
# Brand New display mapping
# ---------------------------------------------------------------------------


def _map_public_listing_brand_new(condition: str) -> str:
    """Map a public listing condition to Brand New display.

    Rules:
        NEW -> Yes
        USED -> No
        REFURBISHED -> No
        DAMAGED -> No
        UNKNOWN -> Unknown

    Do NOT relabel UNKNOWN as New. Do NOT infer Brand New from source
    reputation, SKU, title, URL, price, or vendor policy.
    """
    if condition == "NEW":
        return "Yes"
    elif condition == "USED":
        return "No"
    elif condition == "REFURBISHED":
        return "No"
    elif condition == "DAMAGED":
        return "No"
    else:
        # UNKNOWN or any other unmapped value
        return "Unknown"


# ---------------------------------------------------------------------------
# Price formatting
# ---------------------------------------------------------------------------


def _format_price(amount: Decimal, currency: str) -> str:
    """Format a price as a human-readable string.

    Format: <symbol><amount> <currency>
    Uses standard comma grouping for thousands.

    Examples:
        $2,023.27 USD
        €1,705.35 EUR
    """
    # Currency symbol mapping
    symbol_map: dict[str, str] = {
        "USD": "$",
        "EUR": "€",
        "GBP": "£",
        "JPY": "¥",
        "CAD": "C$",
        "AUD": "A$",
        "CHF": "CHF",
        "CNY": "¥",
    }
    symbol = symbol_map.get(currency.upper(), currency)

    # Format with comma grouping — Decimal handles this natively
    # Use the quantize approach for consistent formatting
    formatted = _format_decimal_with_commas(amount)

    return f"{symbol}{formatted} {currency}"


def _format_decimal_with_commas(d: Decimal) -> str:
    """Format a Decimal with comma grouping for thousands.

    Uses Python's built-in formatting with comma separator.
    """
    # Convert to string first, then format with commas
    sign, digits, exponent = d.as_tuple()

    if exponent >= 0:
        # Integer or no decimal places
        int_str = ''.join(str(d) for d in digits) + '0' * exponent
        if sign:
            int_str = '-' + int_str
        # Add commas
        parts = int_str.split('-')
        if parts[0]:
            sign_prefix = '-' if len(parts) > 1 and parts[0] == '' else ''
            num_part = parts[-1] if len(parts) > 1 else parts[0]
            # Manual comma grouping from right
            grouped = _add_commas(num_part)
            return f"{sign_prefix}{grouped}"
        return int_str
    else:
        # Has decimal places
        decimal_places = -exponent
        digits_str = ''.join(str(d) for d in digits)
        # Pad with leading zeros if needed
        if len(digits_str) <= decimal_places:
            digits_str = '0' * (decimal_places - len(digits_str) + 1) + digits_str

        int_part = digits_str[:len(digits_str) - decimal_places] or '0'
        frac_part = digits_str[len(digits_str) - decimal_places:]

        int_formatted = _add_commas(int_part)

        result = f"{int_formatted}.{frac_part}"
        if sign:
            result = f"-{result}"
        return result


def _add_commas(num_str: str) -> str:
    """Add comma grouping to an integer string from the right."""
    if len(num_str) <= 3:
        return num_str
    groups = []
    while len(num_str) > 3:
        groups.append(num_str[-3:])
        num_str = num_str[:-3]
    groups.append(num_str)
    return ','.join(reversed(groups))


# ---------------------------------------------------------------------------
# Compact Quote Row
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class CompactQuoteRow:
    """One row in the compact quote summary projection.

    This is a pure data object, NOT HTML. It carries the display values
    that a later presentation layer can render.

    Attributes:
        source: The display source label (e.g. "Ingram", "CDW",
                or the public listing source name).
        source_type: "VENDOR_API" or "PUBLIC_LISTING".
        price_original: The original price string (e.g. "$2,023.27 USD").
        price_amount: The original price amount as Decimal.
        price_currency: The original currency code.
        usd_equivalent: The USD-equivalent string, or "Unavailable".
        usd_equivalent_amount: The USD-equivalent amount as Decimal, or None.
        inventory: The display inventory label (e.g. "In Stock").
        brand_new: The display Brand New label (e.g. "Yes", "No", "Unknown").
        note: Optional note text (e.g. "Limited", "PREORDER").
    """

    source: str
    source_type: str
    price_original: str
    price_amount: Decimal
    price_currency: str
    usd_equivalent: str
    usd_equivalent_amount: Decimal | None
    inventory: str
    brand_new: str
    note: str | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.source, str) or not self.source.strip():
            raise ValueError("source must be a non-empty string")

        if self.source_type not in ("VENDOR_API", "PUBLIC_LISTING"):
            raise ValueError(
                f"source_type must be VENDOR_API or PUBLIC_LISTING, "
                f"got {self.source_type!r}"
            )

        if not isinstance(self.price_amount, Decimal):
            raise TypeError(
                f"price_amount must be a Decimal, got "
                f"{type(self.price_amount).__name__}"
            )

        if not isinstance(self.price_currency, str) or not self.price_currency.strip():
            raise ValueError("price_currency must be a non-empty string")

        if self.usd_equivalent_amount is not None:
            if not isinstance(self.usd_equivalent_amount, Decimal):
                raise TypeError(
                    f"usd_equivalent_amount must be a Decimal or None, got "
                    f"{type(self.usd_equivalent_amount).__name__}"
                )


# ---------------------------------------------------------------------------
# Compact Quote Projection
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class CompactQuoteProjection:
    """The complete compact quote summary projection.

    This is the pure data contract for the compact quote table.
    It is NOT rendered to HTML here.

    Attributes:
        rows: Ordered tuple of CompactQuoteRow objects.
    """

    rows: tuple[CompactQuoteRow, ...]

    def __post_init__(self) -> None:
        if isinstance(self.rows, (str, bytes)):
            raise TypeError("rows must be a tuple of CompactQuoteRow")
        rows = tuple(self.rows)
        for i, r in enumerate(rows):
            if not isinstance(r, CompactQuoteRow):
                raise TypeError(
                    f"rows[{i}] must be a CompactQuoteRow, got "
                    f"{type(r).__name__}"
                )
        object.__setattr__(self, "rows", rows)


# ---------------------------------------------------------------------------
# Builder functions
# ---------------------------------------------------------------------------


def build_vendor_api_row(
    *,
    source_name: str,
    price_amount: Decimal,
    currency_code: str,
    availability: str,
    brand_new: bool,
    note: str | None = None,
    fx_snapshot: FxObservationSnapshot | None = None,
) -> CompactQuoteRow:
    """Build one CompactQuoteRow from a Vendor API observation.

    Vendor API rows use frozen-2A-bound identity and VENDOR_API_POLICY
    for brand-new status.

    Args:
        source_name: The vendor source name. Mapped to display label.
        price_amount: The original price amount (Decimal).
        currency_code: The original currency code.
        availability: CommercialAvailability value.
        brand_new: Whether the item is brand new (VENDOR_API_POLICY).
        note: Optional note from the observation.
        fx_snapshot: Persisted FX observation for USD conversion.

    Returns:
        A CompactQuoteRow with the display values.
    """
    # Map source name to display label
    source_upper = source_name.strip().upper()
    if "INGRAM" in source_upper:
        source_label = _LABEL_INGRAM
    elif "CDW" in source_upper:
        source_label = _LABEL_CDW
    elif "SYNNEX" in source_upper:
        source_label = _LABEL_SYNNEX_EU
    else:
        source_label = source_name.strip()

    # Original price formatting
    price_original = _format_price(price_amount, currency_code)

    # USD equivalent
    usd_result = compute_usd_equivalent(
        amount=price_amount,
        currency=currency_code,
        fx_snapshot=fx_snapshot,
    )

    if usd_result.conversion_available:
        usd_equiv_str = _format_price(
            usd_result.usd_equivalent, "USD"
        )
        usd_equiv_amount = usd_result.usd_equivalent
    else:
        usd_equiv_str = "Unavailable"
        usd_equiv_amount = None

    # Inventory mapping
    inventory_label, inventory_note = _map_vendor_api_inventory(availability)

    # Combine notes
    combined_note = _combine_notes(inventory_note, note)

    # Brand New: Vendor API always Yes (VENDOR_API_POLICY)
    brand_new_display = "Yes" if brand_new else "No"

    return CompactQuoteRow(
        source=source_label,
        source_type="VENDOR_API",
        price_original=price_original,
        price_amount=price_amount,
        price_currency=currency_code.upper(),
        usd_equivalent=usd_equiv_str,
        usd_equivalent_amount=usd_equiv_amount,
        inventory=inventory_label,
        brand_new=brand_new_display,
        note=combined_note,
    )


def build_public_listing_row(
    *,
    source_name: str,
    price_amount: Decimal,
    currency_code: str,
    availability: str,
    condition: str,
    fx_snapshot: FxObservationSnapshot | None = None,
) -> CompactQuoteRow:
    """Build one CompactQuoteRow from a public listing observation.

    Public listing rows use source-observed condition for brand-new display.

    Args:
        source_name: The public listing source name.
        price_amount: The original price amount (Decimal).
        currency_code: The original currency code.
        availability: NormalizedAvailability value from frozen 3B.
        condition: NormalizedCondition value from frozen 3B.
        fx_snapshot: Persisted FX observation for USD conversion.

    Returns:
        A CompactQuoteRow with the display values.
    """
    # Original price formatting
    price_original = _format_price(price_amount, currency_code)

    # USD equivalent
    usd_result = compute_usd_equivalent(
        amount=price_amount,
        currency=currency_code,
        fx_snapshot=fx_snapshot,
    )

    if usd_result.conversion_available:
        usd_equiv_str = _format_price(
            usd_result.usd_equivalent, "USD"
        )
        usd_equiv_amount = usd_result.usd_equivalent
    else:
        usd_equiv_str = "Unavailable"
        usd_equiv_amount = None

    # Inventory mapping
    inventory_label, inventory_note = _map_public_listing_inventory(availability)

    # Brand New from condition
    brand_new_display = _map_public_listing_brand_new(condition)

    return CompactQuoteRow(
        source=source_name.strip() if source_name.strip() else "Unknown Source",
        source_type="PUBLIC_LISTING",
        price_original=price_original,
        price_amount=price_amount,
        price_currency=currency_code.upper(),
        usd_equivalent=usd_equiv_str,
        usd_equivalent_amount=usd_equiv_amount,
        inventory=inventory_label,
        brand_new=brand_new_display,
        note=inventory_note,
    )


def _combine_notes(note1: str | None, note2: str | None) -> str | None:
    """Combine two optional notes into one."""
    if note1 and note2:
        return f"{note1}; {note2}"
    return note1 or note2


def build_compact_quote_projection(
    vendor_rows: tuple[CompactQuoteRow, ...] = (),
    public_rows: tuple[CompactQuoteRow, ...] = (),
) -> CompactQuoteProjection:
    """Build the complete compact quote projection from row tuples.

    Vendor API rows come first, then public listing rows.

    Args:
        vendor_rows: Tuple of vendor API CompactQuoteRow objects.
        public_rows: Tuple of public listing CompactQuoteRow objects.

    Returns:
        CompactQuoteProjection with all rows.
    """
    all_rows = vendor_rows + public_rows
    return CompactQuoteProjection(rows=all_rows)
