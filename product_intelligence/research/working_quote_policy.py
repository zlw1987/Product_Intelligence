"""Pure AI-assisted Working Quote placement policy.

This module does not read persistence, call models/providers, mutate review
state, or alter deterministic identity/price authority. Confidence is a
workflow tier, not a calibrated probability or correctness claim.
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
    REJECTED = "REJECTED"


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
