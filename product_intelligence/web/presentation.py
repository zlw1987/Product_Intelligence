"""Presentation helpers for the price intelligence report (PRODUCT-INTEL.4B).

This module reads decoded ``PriceAggregationResult`` fields and prepares
display-only dictionaries for the Django template. It does not:

* decide identity
* decide price eligibility
* recompute low/median/high
* regroup buckets
* recalculate confidence
* remove outliers
* convert currencies
* choose a preferred bucket

It uses the 4A values exactly as supplied.

URL safety: external page URLs are validated before being made into
hyperlinks. Only absolute ``http``/``https`` URLs with a hostname are
hyperlinked. All other text is displayed escaped with no ``href``.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from urllib.parse import urlsplit

from product_intelligence.research.aggregation import (
    PriceAggregationResult,
)
from product_intelligence.research.matching import ListingIdentityAssessment

# ---------------------------------------------------------------------------
# URL safety
# ---------------------------------------------------------------------------


def _is_safe_href_url(url: str) -> bool:
    """Return True if ``url`` is safe to use as an ``href`` value.

    Requires:
    * absolute URL with ``http`` or ``https`` scheme (case-insensitive)
    * hostname exists (non-empty after ``://``)
    * no HTML-breaking characters (double-quote, single-quote, angle brackets, newlines)
    * no embedded credentials (userinfo)

    Rejects ``javascript:``, ``data:``, ``file:``, relative URLs, and
    scheme-relative URLs. No network request is made.

    Parsing itself is fail-closed: malformed URLs (e.g. bracketed IPv6
    that trip ``urlsplit``) return False rather than raising.
    """
    if not url:
        return False
    # Reject HTML-breaking characters that could escape the href attribute
    for bad in ('"', "'", "<", ">", "\n", "\r", "\t"):
        if bad in url:
            return False
    # urlsplit can raise ValueError on malformed URLs (e.g. bad IPv6)
    try:
        parsed = urlsplit(url)
    except ValueError:
        return False
    if parsed.scheme.lower() not in ("http", "https"):
        return False
    if not parsed.hostname:
        return False
    # Reject embedded credentials — public evidence links need no userinfo
    if parsed.username is not None or parsed.password is not None:
        return False
    return True


# ---------------------------------------------------------------------------
# Display data structures
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class _DisplayAssessment:
    """One contributing or excluded assessment for display."""
    source_url: str
    source_url_safe: bool
    product_title: str | None
    seller_name: str | None
    normalized_price: str | None
    currency_code: str | None
    condition: str | None
    candidate_evidence_source: str | None
    raw_candidate_mpn: str
    compared_candidate_mpn: str
    match_type: str | None
    decision: str | None
    rejection_reason: str | None
    raw_price_text: str | None
    raw_currency_text: str | None
    raw_condition_text: str | None


@dataclass(frozen=True)
class _DisplayBucket:
    """One price bucket for display."""
    currency_code: str
    condition: str
    count: int
    low: str
    median: str
    high: str
    market_range_low: str | None
    market_range_high: str | None
    confidence: str
    has_market_range: bool
    assessments: tuple[_DisplayAssessment, ...]


@dataclass(frozen=True)
class _DisplayExclusion:
    """One excluded assessment for display."""
    assessment: _DisplayAssessment
    exclusion_reason: str


@dataclass
class ReportPresentation:
    """Display-ready data for one ``PriceAggregationResult``."""
    verification_status: str = ""
    buckets: list[_DisplayBucket] = field(default_factory=list)
    exclusions: list[_DisplayExclusion] = field(default_factory=list)


def _make_display_assessment(
    assess: ListingIdentityAssessment,
) -> _DisplayAssessment:
    norm = assess.normalized_listing
    obs = norm.observation
    source_url = obs.source_url
    return _DisplayAssessment(
        source_url=source_url,
        source_url_safe=_is_safe_href_url(source_url),
        product_title=obs.product_title,
        seller_name=norm.seller_name,
        normalized_price=str(norm.price_amount) if norm.price_amount is not None else None,
        currency_code=norm.currency_code,
        condition=norm.condition.value,
        candidate_evidence_source=assess.candidate_evidence_source.value,
        raw_candidate_mpn=assess.candidate_part_number_raw,
        compared_candidate_mpn=assess.candidate_part_number_compared,
        match_type=assess.match_type.value,
        decision=assess.decision.value,
        rejection_reason=(
            assess.rejection_reason.value
            if assess.rejection_reason is not None
            else None
        ),
        raw_price_text=obs.price_text,
        raw_currency_text=obs.currency_text,
        raw_condition_text=obs.condition_text,
    )


def build_report_presentation(
    result: PriceAggregationResult,
) -> ReportPresentation:
    """Build display-only data from a decoded ``PriceAggregationResult``.

    This function reads values and prepares them for the template. It does
    not recompute, regroup, or reinterpret any 4A decision.
    """
    presentation = ReportPresentation()
    presentation.verification_status = result.verification_status.value

    # Buckets
    for bucket in result.buckets:
        bucket_assessments = tuple(
            _make_display_assessment(a) for a in bucket.assessments
        )
        presentation.buckets.append(
            _DisplayBucket(
                currency_code=bucket.currency_code,
                condition=bucket.condition.value,
                count=bucket.count,
                low=str(bucket.low),
                median=str(bucket.median),
                high=str(bucket.high),
                market_range_low=(
                    str(bucket.market_range_low)
                    if bucket.market_range_low is not None
                    else None
                ),
                market_range_high=(
                    str(bucket.market_range_high)
                    if bucket.market_range_high is not None
                    else None
                ),
                confidence=bucket.confidence.value,
                has_market_range=(
                    bucket.market_range_low is not None
                    and bucket.market_range_high is not None
                ),
                assessments=bucket_assessments,
            )
        )

    # Exclusions
    for excl in result.exclusions:
        display_assess = _make_display_assessment(excl.assessment)
        presentation.exclusions.append(
            _DisplayExclusion(
                assessment=display_assess,
                exclusion_reason=excl.reason.value,
            )
        )

    return presentation
