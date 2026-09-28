"""Research adapter for AI-assisted Working Quote placement policy.

The framework-free workflow rules live in
product_intelligence.domain.working_quote_policy. This module binds those
rules to the frozen research identity contracts and authoritative 2A part
number comparator.
"""

from __future__ import annotations

from typing import Sequence

from product_intelligence.domain.working_quote_policy import (
    WorkingQuoteDisposition as AiWorkingQuoteDisposition,
    classify_working_quote_policy,
    has_hard_identity_conflict,
)
from product_intelligence.research.identity import compare_part_numbers
from product_intelligence.research.matching import (
    EvidenceSource,
    ListingIdentityAssessment,
    is_human_review_eligible_assessment,
)


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

    sku_identity = compare_part_numbers(target_mpn, candidate_sku)
    strong_sku = (
        assessment.candidate_evidence_source is EvidenceSource.SKU_FIELD
        and sku_identity.is_established
    )

    return classify_working_quote_policy(
        review_state=review_state,
        semantic_confidence=semantic_confidence,
        strong_sku_identity=strong_sku,
        conflicting_attributes=conflicting_attributes,
    )
