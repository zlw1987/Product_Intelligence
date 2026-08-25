"""Identity matching for execution.

PRODUCT-INTEL.4C-B corrections:
* Uses ExecutionDetailCode enum directly
* Correct detail codes based on actual assessment outcomes
* Appends assessments to collection ONLY AFTER evidence write succeeds
* Primitive failure does NOT wrap evidence write in same try/except
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from product_intelligence.domain import ResearchRequest
from product_intelligence.domain.enums import EvidenceDecision
from product_intelligence.domain.evidence import ExecutionDetailCode, ExecutionOutcome, ExecutionStage
from product_intelligence.research.matching import (
    IdentityRejectionReason,
    ListingIdentityAssessment,
    assess_listing_identity,
)

if TYPE_CHECKING:
    from collections.abc import Sequence

    from product_intelligence.execution.evidence_writer import ExecutionEvidenceWriter
    from product_intelligence.research.normalization import NormalizedListingObservation

logger = logging.getLogger(__name__)


def assess_identity(
    request: ResearchRequest,
    normalized_listings: Sequence[NormalizedListingObservation],
    evidence_writer: ExecutionEvidenceWriter,
    candidate_url: str,
) -> tuple[Sequence[ListingIdentityAssessment], str]:
    """Assess identity for normalized listings.

    Parameters
    ----------
    request : ResearchRequest
        The original research request.
    normalized_listings : Sequence[NormalizedListingObservation]
        Normalized listings to assess.
    evidence_writer : ExecutionEvidenceWriter
        For recording match attempts.
    candidate_url : str
        The URL these listings came from.

    Returns
    -------
    tuple[Sequence[ListingIdentityAssessment], str]
        - Identity assessments (one per normalized listing)
        - Detail code explaining overall outcome
    """
    if not normalized_listings:
        return [], "NO_LISTINGS"

    assessments = []
    any_successful = False

    for norm_obs in normalized_listings:
        assessment: ListingIdentityAssessment
        try:
            assessment = assess_listing_identity(request, norm_obs)
        except Exception as exc:
            logger.warning(
                "Identity match failed for listing from %s: %s", candidate_url, exc, exc_info=True
            )
            # Primitive failure - no detail code
            evidence_writer.append_execution_attempt(
                stage=ExecutionStage.MATCH,
                outcome=ExecutionOutcome.FAILED,
                candidate_url=candidate_url,
                detail_code=None,
            )
            continue

        # Successful assessment - record evidence with correct detail code
        if assessment.decision is EvidenceDecision.ACCEPTED:
            evidence_writer.append_execution_attempt(
                stage=ExecutionStage.MATCH,
                outcome=ExecutionOutcome.SUCCESS,
                candidate_url=candidate_url,
                detail_code=ExecutionDetailCode.ACCEPTED,
            )
        elif (
            assessment.decision is EvidenceDecision.REJECTED
            and assessment.rejection_reason is IdentityRejectionReason.NO_EXPLICIT_MPN_EVIDENCE
        ):
            evidence_writer.append_execution_attempt(
                stage=ExecutionStage.MATCH,
                outcome=ExecutionOutcome.SUCCESS,
                candidate_url=candidate_url,
                detail_code=ExecutionDetailCode.NO_MPN_IN_OBSERVATION,
            )
        elif assessment.decision is EvidenceDecision.REJECTED:
            evidence_writer.append_execution_attempt(
                stage=ExecutionStage.MATCH,
                outcome=ExecutionOutcome.SUCCESS,
                candidate_url=candidate_url,
                detail_code=ExecutionDetailCode.IDENTITY_REJECTED,
            )
        else:
            # UNDECIDED - no detail code (description-only request, etc.)
            evidence_writer.append_execution_attempt(
                stage=ExecutionStage.MATCH,
                outcome=ExecutionOutcome.SUCCESS,
                candidate_url=candidate_url,
                detail_code=None,
            )

        # Append to collection ONLY AFTER evidence write succeeds
        assessments.append(assessment)
        any_successful = True

    detail_code = "OK" if any_successful else "NO_ASSESSMENTS"
    return tuple(assessments), detail_code