"""Pure AI-assisted Working Quote placement policy.

This module does not read persistence, call models/providers, mutate review
state, or alter deterministic identity/price authority. Confidence is a
workflow tier, not a calibrated probability or correctness claim.

Explicit identity conflicts are policy exclusions, not human review actions:
they never become Working Quote / Reviewed Price authority merely because a
semantic confidence tier is HIGH or a stale review state says CONFIRMED.
"""

from __future__ import annotations

from enum import Enum
from typing import Sequence

from product_intelligence.research.identity import compare_part_numbers
from product_intelligence.research.matching import (
    EvidenceSource,
    ListingIdentityAssessment,
    is_human_review_eligible_assessment,
)


class AiWorkingQuoteDisposition(str, Enum):
    AUTO_INCLUDE_UNVERIFIED = "AUTO_INCLUDE_UNVERIFIED"
    CONFIRMED = "CONFIRMED"
    NEEDS_REVIEW = "NEEDS_REVIEW"
    LOW_CONFIDENCE = "LOW_CONFIDENCE"
    HARD_CONFLICT = "HARD_CONFLICT"
    REJECTED = "REJECTED"


_HARD_IDENTITY_CONFLICT_TERMS = (
    "mpn",
    "part number",
    "manufacturer part number",
    "model",
    "suffix",
    "revision",
    "capacity",
    "memory size",
    "form factor",
    "interface",
    "connector",
    "accessory",
    "compatible with",
    "replacement",
    "multipack",
    "multi pack",
    "pack size",
    "pack quantity",
    "product type",
    "manufacturer",
    "brand",
)


def _normalize_conflict_text(value: str) -> str:
    return " ".join(
        value.strip().lower().replace("_", " ").replace("-", " ").split()
    )


def has_hard_identity_conflict(
    conflicting_attributes: Sequence[str],
) -> bool:
    """Return True only for explicit identity-critical semantic conflicts.

    Unknown/non-identity conflict labels remain reviewable. Malformed
    non-string conflict entries fail closed as hard conflicts.
    """
    if conflicting_attributes is None:
        return False
    if isinstance(conflicting_attributes, (str, bytes)):
        values = (conflicting_attributes,)
    else:
        try:
            values = tuple(conflicting_attributes)
        except TypeError:
            return True

    for raw in values:
        if not isinstance(raw, str):
            return True
        normalized = _normalize_conflict_text(raw)
        if not normalized:
            continue
        if any(term in normalized for term in _HARD_IDENTITY_CONFLICT_TERMS):
            return True
    return False


def classify_ai_match_for_working_quote(
    assessment: ListingIdentityAssessment,
    *,
    review_state: str,
    semantic_confidence: str,
    candidate_sku: str,
    target_mpn: str,
    conflicting_attributes: Sequence[str],
) -> AiWorkingQuoteDisposition:
    """Classify one binding-valid semantic MATCH candidate for Working Quote."""
    if not isinstance(assessment, ListingIdentityAssessment):
        raise TypeError("assessment must be a ListingIdentityAssessment")
    if not is_human_review_eligible_assessment(assessment):
        raise ValueError("assessment is not human-review eligible")

    state = (review_state or "").strip().upper()
    if state == "REJECTED":
        return AiWorkingQuoteDisposition.REJECTED

    if has_hard_identity_conflict(conflicting_attributes):
        return AiWorkingQuoteDisposition.HARD_CONFLICT

    if state == "CONFIRMED":
        return AiWorkingQuoteDisposition.CONFIRMED
    if state != "UNREVIEWED":
        raise ValueError(f"unsupported review state: {review_state!r}")

    confidence = (semantic_confidence or "").strip().upper()
    if confidence == "LOW":
        return AiWorkingQuoteDisposition.LOW_CONFIDENCE
    if confidence == "MEDIUM":
        return AiWorkingQuoteDisposition.NEEDS_REVIEW

    if confidence == "HIGH":
        sku_identity = compare_part_numbers(target_mpn, candidate_sku)
        strong_sku = (
            assessment.candidate_evidence_source is EvidenceSource.SKU_FIELD
            and sku_identity.is_established
        )
        if strong_sku and not bool(tuple(conflicting_attributes)):
            return AiWorkingQuoteDisposition.AUTO_INCLUDE_UNVERIFIED
        return AiWorkingQuoteDisposition.NEEDS_REVIEW

    return AiWorkingQuoteDisposition.NEEDS_REVIEW
