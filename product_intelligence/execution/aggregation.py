"""Aggregation for execution.

PRODUCT-INTEL.4C-B corrections:
* Evidence write is separated from primitive call
* AGGREGATE/SUCCESS has no detail code per vocabulary
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from product_intelligence.domain import ResearchRequest
from product_intelligence.domain.evidence import ExecutionOutcome, ExecutionStage
from product_intelligence.research.aggregation import (
    PriceAggregationResult,
    aggregate_listing_prices,
)

if TYPE_CHECKING:
    from collections.abc import Sequence

    from product_intelligence.execution.evidence_writer import ExecutionEvidenceWriter
    from product_intelligence.research.matching import ListingIdentityAssessment

logger = logging.getLogger(__name__)


def aggregate_prices(
    request: ResearchRequest,
    assessments: Sequence[ListingIdentityAssessment],
    evidence_writer: ExecutionEvidenceWriter,
) -> PriceAggregationResult:
    """Aggregate accepted listings by currency/condition.

    Parameters
    ----------
    request : ResearchRequest
        The original research request.
    assessments : Sequence[ListingIdentityAssessment]
        Identity assessments (may include rejected listings).
    evidence_writer : ExecutionEvidenceWriter
        For recording aggregation attempts.

    Returns
    -------
    PriceAggregationResult
        Price aggregation result with buckets and exclusions.

    Raises
    ------
    Exception
        If aggregation primitive fails. Evidence write failure propagates.
    """
    # Call aggregation primitive in isolated try
    try:
        aggregation_result = aggregate_listing_prices(request, tuple(assessments))
    except Exception:
        # Record aggregation failure OUTSIDE primitive try
        # AGGREGATE/FAILED has no additional detail code
        evidence_writer.append_execution_attempt(
            stage=ExecutionStage.AGGREGATE,
            outcome=ExecutionOutcome.FAILED,
            candidate_url="",
            detail_code=None,
        )
        raise

    # Record aggregation success OUTSIDE primitive try
    # SUCCESS evidence write failure must not be relabeled as primitive failure
    # AGGREGATE/SUCCESS has no additional detail code
    evidence_writer.append_execution_attempt(
        stage=ExecutionStage.AGGREGATE,
        outcome=ExecutionOutcome.SUCCESS,
        candidate_url="",
        detail_code=None,
    )

    return aggregation_result