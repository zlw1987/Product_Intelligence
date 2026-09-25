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




# ---------------------------------------------------------------------------
# Review candidate presentation — HUMAN-REVIEW
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class ReviewCandidatePresentation:
    """Presentation object for one AI-assisted review candidate.

    Combines the snapshot-backed listing evidence (authoritative) with
    the candidate's semantic/provenance metadata and review state.

    For invalid/stale/unbound candidates, binding_valid is False and
    listing evidence fields are None — the template shows neutral
    'Review evidence unavailable' and no Confirm/Reject/Undo actions.
    """
    candidate_id: str
    assessment_index: int
    binding_valid: bool
    review_state: str
    reviewed_at: "datetime | None"
    review_tier: str
    working_quote_included: bool

    # Listing evidence from the snapshot assessment (authoritative)
    source_url: "str | None"
    source_url_safe: bool
    seller_name: "str | None"
    normalized_price: "str | None"
    currency_code: "str | None"
    condition: "str | None"
    condition_display: "str | None"
    product_title: "str | None"

    # MPN/SKU evidence
    candidate_mpn_field: str
    candidate_sku: str

    # Semantic provenance
    semantic_confidence: str
    semantic_reason_code: str
    semantic_matched_attributes: "list[str]"
    semantic_conflicting_attributes: "list[str]"
    actual_provider: str
    actual_model: str
    prompt_version: str

    # Candidate binding fields (for validation display)
    source_url_candidate: str
    target_mpn: str
    candidate_title: str


def _build_review_candidate_presentations(
    candidates,
    assessments,
    logger,
):
    """Build ReviewCandidatePresentation objects for a list of candidates.

    Args:
        candidates: list of AiAssistedReviewCandidate instances
        assessments: tuple of ListingIdentityAssessment from decoded snapshot
        logger: logger instance

    Returns:
        list of ReviewCandidatePresentation objects
    """
    from datetime import datetime
    presentations = []
    for candidate in candidates:
        idx = candidate.assessment_index
        binding_valid = False
        assessment = None

        if 0 <= idx < len(assessments):
            assessment = assessments[idx]
            binding_valid = _check_candidate_binding(
                candidate, assessment, logger,
            )

        if binding_valid and assessment is not None:
            from product_intelligence.research.matching import (
                AiAssistedReviewTier,
                classify_ai_assisted_review_tier,
            )

            norm = assessment.normalized_listing
            obs = norm.observation
            source_url = obs.source_url
            review_tier = classify_ai_assisted_review_tier(
                candidate, assessment
            )
            working_quote_included = (
                candidate.review_state == "CONFIRMED"
                or (
                    candidate.review_state == "UNREVIEWED"
                    and review_tier is AiAssistedReviewTier.AUTO_INCLUDE
                )
            )
            raw_condition = (
                norm.condition.value if norm.condition is not None else None
            )
            condition_display = (
                "Not stated"
                if raw_condition == "UNKNOWN"
                else raw_condition.replace("_", " ").title()
                if raw_condition
                else None
            )
            presentations.append(ReviewCandidatePresentation(
                candidate_id=str(candidate.id),
                assessment_index=idx,
                binding_valid=True,
                review_state=candidate.review_state,
                reviewed_at=candidate.reviewed_at,
                review_tier=review_tier.value,
                working_quote_included=working_quote_included,
                source_url=source_url,
                source_url_safe=_is_safe_href_url(source_url),
                seller_name=norm.seller_name,
                normalized_price=(
                    str(norm.price_amount)
                    if norm.price_amount is not None
                    else None
                ),
                currency_code=norm.currency_code,
                condition=raw_condition,
                condition_display=condition_display,
                product_title=obs.product_title,
                candidate_mpn_field=candidate.candidate_mpn_field,
                candidate_sku=candidate.candidate_sku,
                semantic_confidence=candidate.semantic_confidence,
                semantic_reason_code=candidate.semantic_reason_code,
                semantic_matched_attributes=list(candidate.semantic_matched_attributes),
                semantic_conflicting_attributes=list(candidate.semantic_conflicting_attributes),
                actual_provider=candidate.actual_provider,
                actual_model=candidate.actual_model,
                prompt_version=candidate.prompt_version,
                source_url_candidate=candidate.source_url,
                target_mpn=candidate.target_mpn,
                candidate_title=candidate.candidate_title,
            ))
        else:
            # Unbound/stale candidate: neutral presentation, no listing evidence
            presentations.append(ReviewCandidatePresentation(
                candidate_id=str(candidate.id),
                assessment_index=idx,
                binding_valid=False,
                review_state=candidate.review_state,
                reviewed_at=candidate.reviewed_at,
                review_tier="INVALID",
                working_quote_included=False,
                source_url=None,
                source_url_safe=False,
                seller_name=None,
                normalized_price=None,
                currency_code=None,
                condition=None,
                condition_display=None,
                product_title=None,
                candidate_mpn_field=candidate.candidate_mpn_field,
                candidate_sku=candidate.candidate_sku,
                semantic_confidence=candidate.semantic_confidence,
                semantic_reason_code=candidate.semantic_reason_code,
                semantic_matched_attributes=list(candidate.semantic_matched_attributes),
                semantic_conflicting_attributes=list(candidate.semantic_conflicting_attributes),
                actual_provider=candidate.actual_provider,
                actual_model=candidate.actual_model,
                prompt_version=candidate.prompt_version,
                source_url_candidate=candidate.source_url,
                target_mpn=candidate.target_mpn,
                candidate_title=candidate.candidate_title,
            ))
    return presentations


def _check_candidate_binding(candidate, assessment, logger):
    """Check if a candidate's binding to one assessment is valid.

    Returns True if ALL binding checks pass against the assessment's
    normalized listing observation. Returns False for any failure.

    FU1: the binding RULES live in exactly one place — the pure
    lower-layer primitive ``research.matching.is_review_candidate_binding_valid``
    — which is shared by this web path, the 8-step review-POST validation,
    and the historical compact-quote replay boundary. This function is a
    thin logging wrapper: it adds no rules of its own and cannot diverge
    from the replay boundary.

    Uses the human-review eligibility predicate (inside the shared
    primitive) rather than checking assessment.decision ==
    AI_ASSISTED_MATCH, because the frozen FU3B execution path produces
    ORIGINAL deterministic REJECTED assessments (never AI_ASSISTED_MATCH
    in the snapshot).
    """
    from product_intelligence.research.matching import (
        is_review_candidate_binding_valid,
    )

    if is_review_candidate_binding_valid(candidate, assessment):
        return True

    logger.warning(
        "Candidate %s (assessment_index=%s) failed the shared "
        "candidate-to-assessment binding validation; binding invalid.",
        candidate.id, getattr(candidate, "assessment_index", None),
    )
    return False



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


# ---------------------------------------------------------------------------
# Reviewed presentation — HUMAN-REVIEW
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class _ReviewedDisplayEntry:
    """One contributing assessment in a reviewed bucket with origin."""
    assessment: _DisplayAssessment
    origin: str  # "DETERMINISTIC" or "HUMAN_CONFIRMED"


@dataclass(frozen=True)
class _ReviewedDisplayBucket:
    """One reviewed price bucket for display."""
    currency_code: str
    condition: str
    count: int
    deterministic_count: int
    human_confirmed_count: int
    low: str
    median: str
    high: str
    market_range_low: str | None
    market_range_high: str | None
    confidence: str
    has_market_range: bool
    assessments: tuple[_DisplayAssessment, ...]
    entries: tuple[_ReviewedDisplayEntry, ...]


@dataclass
class ReviewedReportPresentation:
    """Display-ready data for reviewed price aggregation."""
    verification_status: str = ""
    buckets: list[_ReviewedDisplayBucket] = None
    exclusions: list[_DisplayExclusion] = None

    def __post_init__(self):
        if self.buckets is None:
            self.buckets = []
        if self.exclusions is None:
            self.exclusions = []


def build_reviewed_report_presentation(
    reviewed_result,
) -> ReviewedReportPresentation:
    """Build display data from a ReviewedPriceAggregationResult.

    This is for the reviewed (human-confirmed) price section on the report.
    """
    presentation = ReviewedReportPresentation()
    presentation.verification_status = reviewed_result.verification_status.value

    for bucket in reviewed_result.buckets:
        bucket_assessments = tuple(
            _make_display_assessment(a) for a in bucket.assessments
        )
        display_entries = tuple(
            _ReviewedDisplayEntry(
                assessment=_make_display_assessment(e.assessment),
                origin=e.origin.value,
            )
            for e in bucket.entries
        )
        presentation.buckets.append(
            _ReviewedDisplayBucket(
                currency_code=bucket.currency_code,
                condition=bucket.condition.value,
                count=bucket.count,
                deterministic_count=bucket.deterministic_count,
                human_confirmed_count=bucket.human_confirmed_count,
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
                entries=display_entries,
            )
        )

    # Map reviewed exclusions to display format
    for excl in reviewed_result.exclusions:
        display_assess = _make_display_assessment(excl.assessment)
        presentation.exclusions.append(
            _DisplayExclusion(
                assessment=display_assess,
                exclusion_reason=excl.reason.value,
            )
        )

    return presentation