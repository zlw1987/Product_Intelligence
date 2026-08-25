"""Listing normalization for execution.

PRODUCT-INTEL.4C-B corrections:
* Uses ExecutionDetailCode enum directly
* Appends normalized results to collection ONLY AFTER evidence write succeeds
* Primitive failure does NOT wrap evidence write in same try/except
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from product_intelligence.domain import ResearchRequest
from product_intelligence.domain.evidence import ExecutionDetailCode, ExecutionOutcome, ExecutionStage
from product_intelligence.research.listings import ListingObservation
from product_intelligence.research.normalization import (
    NormalizedListingObservation,
    normalize_listing_observation,
)

if TYPE_CHECKING:
    from collections.abc import Sequence

    from product_intelligence.execution.evidence_writer import ExecutionEvidenceWriter

logger = logging.getLogger(__name__)


def normalize_listings(
    listings: Sequence[ListingObservation],
    evidence_writer: ExecutionEvidenceWriter,
    candidate_url: str,
) -> tuple[Sequence[NormalizedListingObservation], list[str]]:
    """Normalize a sequence of listing observations.

    Parameters
    ----------
    listings : Sequence[ListingObservation]
        Raw observations to normalize.
    evidence_writer : ExecutionEvidenceWriter
        For recording normalization attempts.
    candidate_url : str
        The URL these listings came from.

    Returns
    -------
    tuple[Sequence[NormalizedListingObservation], list[str]]
        - Normalized listings (may be empty)
        - List of detail codes for each normalization attempt
    """
    if not listings:
        return [], []

    normalized_listings = []
    detail_codes = []

    for obs in listings:
        try:
            normalized = normalize_listing_observation(obs)
        except Exception as exc:
            logger.warning(
                "Normalization failed for listing from %s: %s", candidate_url, exc, exc_info=True
            )
            detail_codes.append("")
            # Primitive failure - no detail code
            evidence_writer.append_execution_attempt(
                stage=ExecutionStage.NORMALIZE,
                outcome=ExecutionOutcome.FAILED,
                candidate_url=candidate_url,
                detail_code=None,
            )
            continue

        # Successful normalization - record evidence
        # NO_PRICE is used whenever price_amount is None, regardless of other issues
        # Other normalization issues are recorded on the listing, not in detail_code
        if normalized.price_amount is None:
            detail_codes.append("NO_PRICE")
            evidence_writer.append_execution_attempt(
                stage=ExecutionStage.NORMALIZE,
                outcome=ExecutionOutcome.SUCCESS,
                candidate_url=candidate_url,
                detail_code=ExecutionDetailCode.NO_PRICE,
            )
        else:
            detail_codes.append("OK")
            evidence_writer.append_execution_attempt(
                stage=ExecutionStage.NORMALIZE,
                outcome=ExecutionOutcome.SUCCESS,
                candidate_url=candidate_url,
                detail_code=ExecutionDetailCode.OK,
            )

        # Append to collection ONLY AFTER evidence write succeeds
        normalized_listings.append(normalized)

    return normalized_listings, detail_codes