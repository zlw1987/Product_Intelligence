"""Compact quote summary browser presentation (PRODUCT-INTEL.4D-C).

Pure display-only module. Consumes a ``CompactQuoteProjection`` (already
produced server-side by either the frozen 4D-C-A authorized replay or the
public-only denied-branch replay) plus the provenance-validated
``PriceAggregationResult``, and produces display-only rows for the Django
template.

This module MUST NOT:
* establish research authority
* call providers
* read the database
* execute research
* import execution, runs, or providers

The security branch (authorized vs denied) has ALREADY happened in the
view before this module is called: a denied projection contains no vendor
rows at all, and this module never adds them back. It merely formats the
rows it is given.

Display rules:
* Vendor rows: append ``" (Vendor API)"`` to the frozen source label when
  it does not already end with it (never double-suffixed). Vendor rows
  NEVER receive a source URL.
* Public rows: display hostname with leading ``www.`` stripped; the full
  SAFE source URL — taken from the paired frozen 4A bucket-member
  assessment — remains the link target.
* Human-confirmed rows (PROD-FIX1): public-listing display rules apply
  (www.-stripped hostname; SAFE persisted-assessment URL as link target);
  the "Human Confirmed" provenance note passes through verbatim from the
  frozen row. They are identity-authority overlays on public evidence —
  never vendor data, never a re-derivation of price/condition.
* Public quote-only rows use the same safe public-link rules, but may
  reconcile only to frozen 4A UNKNOWN_CONDITION exclusions. They remain
  excluded from market arithmetic.
* Public row URL association is mechanically reconciled with the frozen
  4A bucket assessments in deterministic iteration order (bucket by
  bucket, assessment by assessment — the same order the frozen
  ``project_public_rows`` projects in). Any mapping mismatch fails closed
  by withholding the link; nothing is ever guessed.
* URL safety reuses ``presentation._is_safe_href_url`` (no duplication).
* Price / USD Equivalent / Inventory / Brand New / Note are the strings
  already produced by the frozen ``CompactQuoteRow``; nothing is
  recomputed here and no price authority is re-derived in the template.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import TYPE_CHECKING, Any
from urllib.parse import urlparse

if TYPE_CHECKING:
    from product_intelligence.research.compact_quote import (
        CompactQuoteProjection,
        CompactQuoteRow,
    )

# NOTE: this module deliberately does NOT import
# product_intelligence.research.aggregation (frozen boundary:
# tests/research/test_price_aggregation_boundaries.py permits only
# views/presentation/__init__ to do so). The provenance-validated
# PriceAggregationResult is consumed structurally (Any) — the module
# only reads its buckets/assessments for URL reconciliation.

# Reuse the authoritative URL safety helper from the existing presentation
# module — never duplicate it.
from .presentation import _is_safe_href_url


# ---------------------------------------------------------------------------
# Vendor source display
# ---------------------------------------------------------------------------

_VENDOR_API_SUFFIX = " (Vendor API)"


def _vendor_source_display(label: str) -> str:
    """Append " (Vendor API)" to a frozen vendor source label.

    The frozen 4D-C-A CompactQuoteRow source label may already carry the
    suffix (e.g. "Synnex EU (Vendor API)"). It is appended at most once —
    never duplicated.
    """
    if label.endswith(_VENDOR_API_SUFFIX):
        return label
    return label + _VENDOR_API_SUFFIX


# ---------------------------------------------------------------------------
# Public source display
# ---------------------------------------------------------------------------


def _public_source_display(label: str) -> str:
    """Display a public source hostname, stripping a leading ``www.``."""
    if label.startswith("www."):
        return label[len("www."):]
    return label


def _expected_public_source_from_url(url: "str | None") -> str:
    """Mirror the frozen 4D-C-A public-row source derivation.

    The frozen ``project_public_rows`` derives a public row's source from
    the paired assessment's observation URL hostname:
    ``urlparse(url).hostname or parsed.netloc or "Unknown Source"``,
    stripped, falling back to "Unknown Source" on blank or unparseable
    input. This helper re-derives the same value for mechanical
    reconciliation only — it establishes no authority.
    """
    if not url:
        return "Unknown Source"
    try:
        parsed = urlparse(url)
        source = parsed.hostname or parsed.netloc or "Unknown Source"
    except ValueError:
        return "Unknown Source"
    return source.strip() if source.strip() else "Unknown Source"


def _ordered_bucket_assessments(price_result: Any) -> list[Any]:
    """Deterministic frozen 4A bucket membership iteration order.

    Exactly the order the frozen ``project_public_rows`` projects in:
    bucket by bucket, assessment by assessment.
    """
    ordered: list[Any] = []
    for bucket in price_result.buckets:
        for assessment in bucket.assessments:
            ordered.append(assessment)
    return ordered


def _ordered_condition_unknown_assessments(price_result: Any) -> list[Any]:
    """Return frozen 4A UNKNOWN_CONDITION exclusions in persisted order."""
    ordered: list[Any] = []
    for exclusion in price_result.exclusions:
        reason = getattr(exclusion.reason, "value", exclusion.reason)
        if reason == "UNKNOWN_CONDITION":
            ordered.append(exclusion.assessment)
    return ordered


def _enum_value(value: Any) -> Any:
    """Return an enum's value without requiring an aggregation import."""
    return getattr(value, "value", value)


def _condition_display(assessment: Any | None) -> str:
    """Business-facing condition label from persisted normalized evidence."""
    if assessment is None:
        return "Evidence unavailable"
    condition = _enum_value(assessment.normalized_listing.condition)
    return {
        "NEW": "New",
        "USED": "Used",
        "REFURBISHED": "Refurbished",
        "DAMAGED": "Damaged",
        "UNKNOWN": "Not stated",
    }.get(condition, "Not stated")


def _deterministic_match_display(assessment: Any | None) -> str:
    """Compact business label; detailed provenance remains in the audit."""
    if assessment is None:
        return "Evidence unavailable"
    match_type = _enum_value(assessment.match_type)
    if match_type in ("EXACT", "NORMALIZED_EXACT"):
        return "Exact MPN"
    return "Deterministic match"


def _format_currency_amount(amount: Decimal, currency: str) -> str:
    """Display one already-authoritative amount without changing its value."""
    symbols = {
        "USD": "$",
        "EUR": "€",
        "GBP": "£",
        "JPY": "¥",
        "CAD": "C$",
        "AUD": "A$",
        "CNY": "¥",
    }
    code = currency.upper()
    symbol = symbols.get(code)
    rendered = f"{amount:,.2f}"
    if symbol is not None:
        return f"{symbol}{rendered} {code}"
    return f"{code} {rendered}"


def _format_usd_amount(amount: Decimal) -> str:
    return _format_currency_amount(amount, "USD")


# ---------------------------------------------------------------------------
# Display data structures
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class CompactQuoteRowDisplay:
    """One display-only row for the compact quote summary table.

    Attributes:
        source_display: Display source text (vendor label or public
            hostname without leading "www.").
        source_url: Full safe source URL link target for public rows.
            Always None for vendor rows and for public rows whose link
            failed closed.
        source_url_safe: True only when source_url passed the existing
            URL safety helper.
        price: Original price string from the frozen CompactQuoteRow.
        usd_equivalent: USD-equivalent string from the frozen row
            ("Unavailable" when no persisted FX conversion exists).
        inventory: Display inventory label from the frozen row.
        brand_new: Display brand-new label from the frozen row.
        note: Bounded display note; None renders blank.
    """

    source_display: str
    source_url: "str | None"
    source_url_safe: bool
    source_type: str
    price: str
    usd_equivalent: str
    usd_equivalent_amount: "Decimal | None"
    inventory: str
    condition: str
    match_evidence: str
    market_use: str
    brand_new: str
    note: "str | None"


@dataclass(frozen=True)
class CompactQuotePresentation:
    """Complete display-only presentation of one CompactQuoteProjection.

    Rows are preserved in the exact order produced by the server-side
    replay (vendor rows first when authorized, public rows only when
    denied). No row is added, removed, reordered, or re-derived.
    """

    rows: tuple[CompactQuoteRowDisplay, ...]
    quotes_found: int
    in_stock_count: int
    lowest_in_stock_price: "str | None"
    lowest_in_stock_source: "str | None"
    quote_span_low: "str | None"
    quote_span_high: "str | None"
    public_market_count: int
    public_market_currency: "str | None"
    public_market_low: "str | None"
    public_market_high: "str | None"
    public_market_median: "str | None"
    public_market_median_note: "str | None"


# ---------------------------------------------------------------------------
# Presentation builder
# ---------------------------------------------------------------------------


def build_compact_quote_presentation(
    *,
    projection: Any,
    price_result: Any,
    confirmed_assessment_indices: "frozenset[int] | None" = None,
) -> CompactQuotePresentation:
    """Build display-only rows from a CompactQuoteProjection.

    Parameters
    ----------
    projection
        A ``CompactQuoteProjection`` produced by the server-side replay
        (authorized full replay or public-only denied-branch replay).
    price_result
        The provenance-validated ``PriceAggregationResult`` (typed as
        Any to respect the frozen web-aggregation import boundary)
        used to associate public projected rows with their exact frozen
        4A bucket-member assessments (and therefore their source URLs).
    confirmed_assessment_indices
        (PROD-FIX1) The run-scoped, binding-validated indices of
        human-CONFIRMED semantic candidates, in the same deterministic
        form the projection used. Used ONLY to mechanically reconcile
        HUMAN_CONFIRMED rows with their persisted assessments for source
        link targets. Any mismatch fails closed (link withheld; nothing
        is guessed).

    Returns
    -------
    CompactQuotePresentation
        Immutable display-only rows for the template.
    """
    # Reconcile public rows with the frozen 4A bucket membership in
    # deterministic iteration order. FAIL CLOSED on any mismatch: a
    # public row that cannot be mechanically reconciled simply loses its
    # source link — a URL is never guessed.
    public_rows = [
        row for row in projection.rows if row.source_type == "PUBLIC_LISTING"
    ]
    bucket_assessments = _ordered_bucket_assessments(price_result)

    links: dict[int, tuple["str | None", bool]] = {}
    public_assessment_by_row: dict[int, Any] = {}
    if len(public_rows) == len(bucket_assessments):
        for row, assessment in zip(public_rows, bucket_assessments):
            normalized_listing = assessment.normalized_listing
            observation = normalized_listing.observation
            source_url = (
                observation.source_url if observation is not None else None
            )
            if _expected_public_source_from_url(source_url) != row.source:
                # Mapping mismatch — withhold the link, do not guess.
                continue
            public_assessment_by_row[id(row)] = assessment
            if source_url is not None and _is_safe_href_url(source_url):
                links[id(row)] = (source_url, True)
            # Unsafe/missing URLs are deliberately NOT recorded: the
            # display row then renders the source as plain text and the
            # raw unsafe string never enters the template context.

    # Quote-only public rows may receive a source link only when they
    # mechanically reconcile with the exact persisted UNKNOWN_CONDITION
    # exclusions that authorized those rows.
    quote_only_rows = [
        row for row in projection.rows if row.source_type == "PUBLIC_QUOTE_ONLY"
    ]
    quote_only_assessments = _ordered_condition_unknown_assessments(price_result)
    quote_only_links: dict[int, tuple["str | None", bool]] = {}
    quote_only_assessment_by_row: dict[int, Any] = {}
    if len(quote_only_rows) == len(quote_only_assessments):
        for row, assessment in zip(quote_only_rows, quote_only_assessments):
            normalized_listing = assessment.normalized_listing
            observation = normalized_listing.observation
            source_url = (
                observation.source_url if observation is not None else None
            )
            if _expected_public_source_from_url(source_url) != row.source:
                continue
            quote_only_assessment_by_row[id(row)] = assessment
            if source_url is not None and _is_safe_href_url(source_url):
                quote_only_links[id(row)] = (source_url, True)

    # (PROD-FIX1) Reconcile human-confirmed rows with their persisted
    # assessments in the exact deterministic order the projection used:
    # ascending index, skipping assessments without persisted price or
    # currency (confirmation cannot create such evidence, so no row was
    # projected for them). FAIL CLOSED on any count mismatch or source
    # label mismatch: the link is withheld, never guessed.
    human_rows = [
        row for row in projection.rows if row.source_type == "HUMAN_CONFIRMED"
    ]
    human_links: dict[int, tuple["str | None", bool]] = {}
    human_assessment_by_row: dict[int, Any] = {}
    if human_rows:
        expected_assessments: list[Any] = []
        if confirmed_assessment_indices:
            assessments = price_result.assessments
            for idx in sorted(confirmed_assessment_indices):
                if 0 <= idx < len(assessments):
                    norm = assessments[idx].normalized_listing
                    if (
                        norm.price_amount is not None
                        and norm.currency_code is not None
                    ):
                        expected_assessments.append(assessments[idx])
        if len(expected_assessments) == len(human_rows):
            for row, assessment in zip(human_rows, expected_assessments):
                normalized_listing = assessment.normalized_listing
                observation = normalized_listing.observation
                source_url = (
                    observation.source_url if observation is not None else None
                )
                if _expected_public_source_from_url(source_url) != row.source:
                    continue  # mapping mismatch — withhold the link
                human_assessment_by_row[id(row)] = assessment
                if source_url is not None and _is_safe_href_url(source_url):
                    human_links[id(row)] = (source_url, True)

    rows: list[CompactQuoteRowDisplay] = []
    for row in projection.rows:
        if row.source_type == "VENDOR_API":
            # Vendor rows never receive a public source URL.
            source_display = _vendor_source_display(row.source)
            source_url: "str | None" = None
            source_url_safe = False
            condition = "New"
            match_evidence = "Vendor API"
            market_use = "Quote only — Vendor supplemental"
        elif row.source_type == "PUBLIC_QUOTE_ONLY":
            source_display = _public_source_display(row.source)
            link = quote_only_links.get(id(row))
            if link is not None:
                source_url, source_url_safe = link
            else:
                source_url, source_url_safe = None, False
            assessment = quote_only_assessment_by_row.get(id(row))
            condition = "Not stated"
            match_evidence = _deterministic_match_display(assessment)
            market_use = "Quote only — condition not stated"
        elif row.source_type == "HUMAN_CONFIRMED":
            # Human-confirmed rows are public-listing evidence: the
            # www.-stripped hostname display applies, and the link target
            # (when mechanically reconciled and safe) is the persisted
            # assessment's source URL.
            source_display = _public_source_display(row.source)
            link = human_links.get(id(row))
            if link is not None:
                source_url, source_url_safe = link
            else:
                source_url, source_url_safe = None, False
            assessment = human_assessment_by_row.get(id(row))
            condition = _condition_display(assessment)
            match_evidence = "AI-assisted — Human confirmed"
            market_use = "Quote only — AI-assisted"
        else:
            source_display = _public_source_display(row.source)
            link = links.get(id(row))
            if link is not None:
                source_url, source_url_safe = link
            else:
                source_url, source_url_safe = None, False
            assessment = public_assessment_by_row.get(id(row))
            condition = _condition_display(assessment)
            match_evidence = _deterministic_match_display(assessment)
            market_use = "Included in public market"

        rows.append(
            CompactQuoteRowDisplay(
                source_display=source_display,
                source_url=source_url,
                source_url_safe=source_url_safe,
                source_type=row.source_type,
                price=row.price_original,
                usd_equivalent=row.usd_equivalent,
                usd_equivalent_amount=row.usd_equivalent_amount,
                inventory=row.inventory,
                condition=condition,
                match_evidence=match_evidence,
                market_use=market_use,
                brand_new=row.brand_new,
                note=row.note,
            )
        )

    # Business summary over the rows already authorized by replay. Quote
    # span/lowest-in-stock use persisted USD equivalents only; they are
    # explicitly quote metrics, not canonical market statistics.
    quote_pairs = list(zip(projection.rows, rows))
    in_stock_pairs = [
        (raw, display)
        for raw, display in quote_pairs
        if raw.inventory == "In Stock"
    ]
    in_stock_count = len(in_stock_pairs)
    priced_in_stock = [
        (raw, display)
        for raw, display in in_stock_pairs
        if raw.usd_equivalent_amount is not None
    ]
    if priced_in_stock:
        lowest_raw, lowest_display = min(
            priced_in_stock,
            key=lambda pair: pair[0].usd_equivalent_amount,
        )
        lowest_in_stock_price = _format_usd_amount(
            lowest_raw.usd_equivalent_amount
        )
        lowest_in_stock_source = lowest_display.source_display
    else:
        lowest_in_stock_price = None
        lowest_in_stock_source = None

    usd_amounts = [
        raw.usd_equivalent_amount
        for raw in projection.rows
        if raw.usd_equivalent_amount is not None
    ]
    if usd_amounts:
        quote_span_low = _format_usd_amount(min(usd_amounts))
        quote_span_high = _format_usd_amount(max(usd_amounts))
    else:
        quote_span_low = None
        quote_span_high = None

    # Primary market summary stays on frozen 4A authority. Only NEW
    # bucket(s) are candidates. We never merge non-comparable currencies.
    new_buckets = [
        bucket
        for bucket in price_result.buckets
        if _enum_value(bucket.condition) == "NEW"
    ]
    public_market_count = sum(bucket.count for bucket in new_buckets)
    public_market_currency = None
    public_market_low = None
    public_market_high = None
    public_market_median = None
    public_market_median_note = None

    if len(new_buckets) == 1:
        bucket = new_buckets[0]
        public_market_currency = bucket.currency_code
        public_market_low = _format_currency_amount(
            bucket.low, bucket.currency_code
        )
        public_market_high = _format_currency_amount(
            bucket.high, bucket.currency_code
        )
        if bucket.count >= 3:
            public_market_median = _format_currency_amount(
                bucket.median, bucket.currency_code
            )
        else:
            public_market_median_note = (
                "Not shown — fewer than 3 comparable NEW listings."
            )
    elif len(new_buckets) > 1:
        public_market_median_note = (
            "Not combined — multiple non-comparable currency groups. "
            "See Advanced Evidence & Audit."
        )
    else:
        public_market_median_note = "No strict comparable NEW listings."

    return CompactQuotePresentation(
        rows=tuple(rows),
        quotes_found=len(rows),
        in_stock_count=in_stock_count,
        lowest_in_stock_price=lowest_in_stock_price,
        lowest_in_stock_source=lowest_in_stock_source,
        quote_span_low=quote_span_low,
        quote_span_high=quote_span_high,
        public_market_count=public_market_count,
        public_market_currency=public_market_currency,
        public_market_low=public_market_low,
        public_market_high=public_market_high,
        public_market_median=public_market_median,
        public_market_median_note=public_market_median_note,
    )
