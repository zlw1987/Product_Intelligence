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


def _condition_display(value: str | None) -> str:
    """Business-facing condition label without inventing missing facts."""
    if value == "NEW_VENDOR_POLICY":
        return "New (Vendor policy)"
    if not value or value == "UNKNOWN":
        return "Not stated"
    return value.replace("_", " ").title()


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
    price: str
    usd_equivalent: str
    inventory: str
    brand_new: str
    note: "str | None"
    source_type: str = ""
    condition: str = "Not stated"
    match_evidence: str = ""
    market_use: str = ""
    candidate_id: "str | None" = None
    review_anchor: "str | None" = None
    can_remove: bool = False


@dataclass(frozen=True)
class CompactMarketGroupDisplay:
    """One strict deterministic public-market group for top summary."""

    currency_code: str
    condition: str
    count: int
    low: str
    high: str
    median: "str | None"


@dataclass(frozen=True)
class CompactQuotePresentation:
    """Complete display-only presentation of one CompactQuoteProjection.

    Rows are preserved in the exact order produced by the server-side
    replay (vendor rows first when authorized, public rows only when
    denied). No row is added, removed, reordered, or re-derived.
    """

    rows: tuple[CompactQuoteRowDisplay, ...]
    show_usd_equivalent: bool = False
    quote_count: int = 0
    in_stock_count: int = 0
    lowest_in_stock_price: "str | None" = None
    lowest_in_stock_source: "str | None" = None
    quote_span_low: "str | None" = None
    quote_span_high: "str | None" = None
    usd_comparable_quote_count: int = 0
    market_groups: tuple[CompactMarketGroupDisplay, ...] = ()


# ---------------------------------------------------------------------------
# Presentation builder
# ---------------------------------------------------------------------------


def build_compact_quote_presentation(
    *,
    projection: Any,
    price_result: Any,
    confirmed_assessment_indices: "frozenset[int] | None" = None,
    review_candidates: "list[Any] | tuple[Any, ...] | None" = None,
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
            if source_url is not None and _is_safe_href_url(source_url):
                links[id(row)] = (source_url, True)
            # Unsafe/missing URLs are deliberately NOT recorded: the
            # display row then renders the source as plain text and the
            # raw unsafe string never enters the template context.

    # Semantic overlay rows carry their persisted snapshot assessment index.
    # Reconcile that exact index to a source URL; never guess by hostname alone.
    semantic_links: dict[int, tuple["str | None", bool]] = {}
    assessments = price_result.assessments
    for row in projection.rows:
        if row.source_type not in ("HUMAN_CONFIRMED", "AI_ASSISTED"):
            continue
        idx = getattr(row, "assessment_index", None)
        if type(idx) is not int or idx < 0 or idx >= len(assessments):
            continue
        assessment = assessments[idx]
        norm = assessment.normalized_listing
        observation = norm.observation
        source_url = observation.source_url if observation is not None else None
        if _expected_public_source_from_url(source_url) != row.source:
            continue
        if source_url is not None and _is_safe_href_url(source_url):
            semantic_links[id(row)] = (source_url, True)

    # Backward-compatible reconciliation for historical/test human rows that
    # predate assessment_index on CompactQuoteRow.
    legacy_human_rows = [
        row for row in projection.rows
        if row.source_type == "HUMAN_CONFIRMED"
        and getattr(row, "assessment_index", None) is None
    ]
    if legacy_human_rows and confirmed_assessment_indices:
        expected_assessments: list[Any] = []
        for idx in sorted(confirmed_assessment_indices):
            if 0 <= idx < len(assessments):
                norm = assessments[idx].normalized_listing
                if norm.price_amount is not None and norm.currency_code is not None:
                    expected_assessments.append(assessments[idx])
        if len(expected_assessments) == len(legacy_human_rows):
            for row, assessment in zip(legacy_human_rows, expected_assessments):
                observation = assessment.normalized_listing.observation
                source_url = observation.source_url if observation is not None else None
                if _expected_public_source_from_url(source_url) != row.source:
                    continue
                if source_url is not None and _is_safe_href_url(source_url):
                    semantic_links[id(row)] = (source_url, True)

    candidate_by_index = {
        candidate.assessment_index: candidate
        for candidate in (review_candidates or ())
        if getattr(candidate, "binding_valid", False)
    }

    public_assessment_by_row_id: dict[int, Any] = {}
    if len(public_rows) == len(bucket_assessments):
        for row, assessment in zip(public_rows, bucket_assessments):
            public_assessment_by_row_id[id(row)] = assessment

    rows: list[CompactQuoteRowDisplay] = []
    for row in projection.rows:
        if row.source_type == "VENDOR_API":
            # Vendor rows never receive a public source URL.
            source_display = _vendor_source_display(row.source)
            source_url: "str | None" = None
            source_url_safe = False
        elif row.source_type in ("HUMAN_CONFIRMED", "AI_ASSISTED"):
            source_display = _public_source_display(row.source)
            link = semantic_links.get(id(row))
            if link is not None:
                source_url, source_url_safe = link
            else:
                source_url, source_url_safe = None, False
        else:
            source_display = _public_source_display(row.source)
            link = links.get(id(row))
            if link is not None:
                source_url, source_url_safe = link
            else:
                source_url, source_url_safe = None, False

        candidate = None
        idx = getattr(row, "assessment_index", None)
        if type(idx) is int:
            candidate = candidate_by_index.get(idx)

        if row.source_type == "VENDOR_API":
            match_evidence = "Vendor API"
            market_use = "Quote only — vendor supplemental"
        elif row.source_type == "HUMAN_CONFIRMED":
            confidence = (
                getattr(candidate, "semantic_confidence", "") if candidate else ""
            )
            match_evidence = (
                f"AI {confidence} — Human confirmed"
                if confidence else "AI — Human confirmed"
            )
            market_use = "Included — reviewed market"
        elif row.source_type == "AI_ASSISTED":
            confidence = (
                getattr(candidate, "semantic_confidence", "HIGH")
                if candidate else "HIGH"
            )
            match_evidence = f"AI {confidence} — Not human verified"
            market_use = "Working quote only"
        else:
            assessment = public_assessment_by_row_id.get(id(row))
            match_type = getattr(getattr(assessment, "match_type", None), "value", "")
            if match_type == "EXACT":
                match_evidence = "Exact MPN"
            elif match_type == "NORMALIZED_EXACT":
                match_evidence = "Normalized exact MPN"
            else:
                match_evidence = "Deterministic match"
            market_use = (
                "Included — condition not stated group"
                if getattr(row, "condition", "UNKNOWN") == "UNKNOWN"
                else "Included — public market"
            )

        candidate_id = (
            getattr(candidate, "candidate_id", None)
            if row.source_type in ("HUMAN_CONFIRMED", "AI_ASSISTED")
            else None
        )

        rows.append(
            CompactQuoteRowDisplay(
                source_display=source_display,
                source_url=source_url,
                source_url_safe=source_url_safe,
                price=row.price_original,
                usd_equivalent=row.usd_equivalent,
                inventory=row.inventory,
                brand_new=row.brand_new,
                note=row.note,
                source_type=row.source_type,
                condition=_condition_display(getattr(row, "condition", None)),
                match_evidence=match_evidence,
                market_use=market_use,
                candidate_id=candidate_id,
                review_anchor=(
                    f"ai-candidate-{candidate_id}" if candidate_id else None
                ),
                can_remove=(
                    candidate_id is not None
                    and row.source_type in ("HUMAN_CONFIRMED", "AI_ASSISTED")
                ),
            )
        )

    show_usd_equivalent = any(
        getattr(row, "price_currency", "").upper() != "USD"
        for row in projection.rows
    )

    usd_rows = [
        (raw, display)
        for raw, display in zip(projection.rows, rows)
        if raw.usd_equivalent_amount is not None
    ]
    in_stock_rows = [
        (raw, display)
        for raw, display in usd_rows
        if raw.inventory == "In Stock"
    ]

    lowest_in_stock_price = None
    lowest_in_stock_source = None
    if in_stock_rows:
        lowest_raw, lowest_display = min(
            in_stock_rows,
            key=lambda pair: pair[0].usd_equivalent_amount,
        )
        lowest_in_stock_price = lowest_raw.usd_equivalent
        lowest_in_stock_source = lowest_display.source_display

    quote_span_low = None
    quote_span_high = None
    if usd_rows:
        low_raw, _ = min(
            usd_rows, key=lambda pair: pair[0].usd_equivalent_amount
        )
        high_raw, _ = max(
            usd_rows, key=lambda pair: pair[0].usd_equivalent_amount
        )
        quote_span_low = low_raw.usd_equivalent
        quote_span_high = high_raw.usd_equivalent

    market_groups: list[CompactMarketGroupDisplay] = []
    for bucket in price_result.buckets:
        condition_value = getattr(bucket.condition, "value", str(bucket.condition))
        market_groups.append(
            CompactMarketGroupDisplay(
                currency_code=bucket.currency_code,
                condition=_condition_display(condition_value),
                count=bucket.count,
                low=str(bucket.low),
                high=str(bucket.high),
                # With one or two observations the standard mathematical
                # median is valid but operationally unhelpful and is easily
                # mistaken for an "average". Show it only at n >= 3.
                median=str(bucket.median) if bucket.count >= 3 else None,
            )
        )

    return CompactQuotePresentation(
        rows=tuple(rows),
        show_usd_equivalent=show_usd_equivalent,
        quote_count=len(rows),
        in_stock_count=sum(1 for row in projection.rows if row.inventory == "In Stock"),
        lowest_in_stock_price=lowest_in_stock_price,
        lowest_in_stock_source=lowest_in_stock_source,
        quote_span_low=quote_span_low,
        quote_span_high=quote_span_high,
        usd_comparable_quote_count=len(usd_rows),
        market_groups=tuple(market_groups),
    )
