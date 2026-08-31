"""Semantic integration for execution (PRODUCT-INTEL.FU3B).

Wires the frozen FU3A semantic runtime into real research execution.

Architecture:
    Deterministic search/fetch/extract/normalize/match produces identity
    assessments. Candidates that are not deterministically accepted and
    are explicitly semantic-eligible receive exactly one semantic runtime
    call. The semantic decision produces an in-memory AI-assisted match
    collection that stays OUTSIDE 4A aggregation.

This module:
1. Decides which deterministic non-accepted candidates are eligible for
   semantic evaluation based on frozen authority semantics.
2. Constructs the frozen semantic prompt from existing evidence fields.
3. Calls the approved SemanticRuntime exactly once per eligible candidate.
4. Maps semantic decisions to execution dispositions.
5. Records safe bounded provenance.

Semantic eligibility (frozen from 3C authority model):
    - ACCEPTED: never semantic (deterministic already resolved)
    - REJECTED + MPN_MISMATCH: never semantic (explicit MPN conflict)
    - REJECTED + NO_EXPLICIT_MPN_EVIDENCE + TITLE_TEXT: eligible
    - REJECTED + NO_EXPLICIT_MPN_EVIDENCE + SKU_FIELD: eligible
    - REJECTED + PARTIAL_MPN_ONLY: eligible
    - REJECTED + NO_EXPLICIT_MPN_EVIDENCE + NONE: not eligible
    - UNDECIDED: not eligible in this integration phase

What this module is NOT:
- It does not change deterministic matching semantics.
- It does not override deterministic ACCEPT or REJECT.
- It does not feed AI-assisted results into 4A aggregation.
- It does not create new database models or migrations.
- It does not implement UI or human checkbox selection.
- Programming exceptions from the runtime propagate.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import TYPE_CHECKING

from product_intelligence.domain import ResearchRequest
from product_intelligence.domain.enums import EvidenceDecision
from product_intelligence.domain.evidence import (
    ExecutionDetailCode,
    ExecutionOutcome,
    ExecutionStage,
)
from product_intelligence.research.matching import (
    EvidenceSource,
    IdentityRejectionReason,
    ListingIdentityAssessment,
)
from product_intelligence.research.listings import ListingObservation
from product_intelligence.semantic import (
    SemanticDecision,
    SemanticRuntime,
    SemanticRuntimeResult,
    get_default_runtime,
)

if TYPE_CHECKING:
    from collections.abc import Sequence
    from product_intelligence.execution.evidence_writer import ExecutionEvidenceWriter

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class AiAssistedMatchResult:
    """One AI-assisted semantic match result.

    Carries the original deterministic assessment (preserving deterministic
    provenance), the semantic runtime result (safe bounded provenance),
    and the derived EvidenceDecision disposition.

    This is NOT a ListingIdentityAssessment. It is a parallel record that
    preserves both layers of evidence independently.

    Self-validates at construction to prevent impossible authority states.
    """

    original_assessment: ListingIdentityAssessment
    semantic_result: SemanticRuntimeResult
    disposition: EvidenceDecision

    def __post_init__(self) -> None:
        """Validate impossible authority states cannot be constructed."""
        if not isinstance(self.original_assessment, ListingIdentityAssessment):
            raise TypeError(
                f"original_assessment must be ListingIdentityAssessment, "
                f"got {type(self.original_assessment).__name__}"
            )
        if self.original_assessment.decision is EvidenceDecision.ACCEPTED:
            raise ValueError(
                "AiAssistedMatchResult cannot wrap a deterministic ACCEPTED assessment"
            )
        if not isinstance(self.semantic_result, SemanticRuntimeResult):
            raise TypeError(
                f"semantic_result must be SemanticRuntimeResult, "
                f"got {type(self.semantic_result).__name__}"
            )
        if self.semantic_result.error_type is not None:
            raise ValueError(
                "AiAssistedMatchResult semantic_result must not carry an error_type"
            )
        if self.semantic_result.decision is not SemanticDecision.MATCH:
            raise ValueError(
                f"AiAssistedMatchResult requires SemanticDecision.MATCH, "
                f"got {self.semantic_result.decision}"
            )
        if self.disposition is not EvidenceDecision.AI_ASSISTED_MATCH:
            raise ValueError(
                f"AiAssistedMatchResult disposition must be AI_ASSISTED_MATCH, "
                f"got {self.disposition}"
            )
        _validate_semantic_eligible_assessment(self.original_assessment)
        _validate_provenance(self.original_assessment, self.semantic_result)

def _validate_provenance(
    assessment: ListingIdentityAssessment,
    semantic_result: SemanticRuntimeResult,
) -> None:
    """Validate that the semantic result provenance mechanically agrees
    with the deterministic assessment it claims to evaluate.

    This prevents an AiAssistedMatchResult from pairing an eligible
    deterministic assessment with a SemanticRuntimeResult produced
    for a different target/candidate.
    """
    observation = assessment.normalized_listing.observation

    if semantic_result.target_mpn != assessment.requested_part_number:
        raise ValueError(
            f"Provenance mismatch: semantic_result.target_mpn "
            f"({semantic_result.target_mpn!r}) != assessment.requested_part_number "
            f"({assessment.requested_part_number!r})"
        )

    expected_title = observation.product_title or ""
    if semantic_result.candidate_title != expected_title:
        raise ValueError(
            f"Provenance mismatch: semantic_result.candidate_title "
            f"({semantic_result.candidate_title!r}) != observation.product_title "
            f"({observation.product_title!r})"
        )

    expected_mpn = (
        observation.manufacturer_part_number_text
        if observation.manufacturer_part_number_text
        else None
    )
    if semantic_result.candidate_mpn_field != expected_mpn:
        raise ValueError(
            f"Provenance mismatch: semantic_result.candidate_mpn_field "
            f"({semantic_result.candidate_mpn_field!r}) != observation.manufacturer_part_number_text "
            f"({observation.manufacturer_part_number_text!r})"
        )

    expected_sku = (
        observation.sku_text
        if observation.sku_text
        else None
    )
    if semantic_result.candidate_sku != expected_sku:
        raise ValueError(
            f"Provenance mismatch: semantic_result.candidate_sku "
            f"({semantic_result.candidate_sku!r}) != observation.sku_text "
            f"({observation.sku_text!r})"
        )

    expected_source = assessment.candidate_evidence_source.value
    if semantic_result.evidence_source != expected_source:
        raise ValueError(
            f"Provenance mismatch: semantic_result.evidence_source "
            f"({semantic_result.evidence_source!r}) != assessment.candidate_evidence_source.value "
            f"({assessment.candidate_evidence_source.value!r})"
        )


def _validate_semantic_eligible_assessment(
    assessment: ListingIdentityAssessment,
) -> None:
    """Raise unless the assessment is one of the explicitly semantic-eligible states."""
    decision = assessment.decision
    if decision is EvidenceDecision.ACCEPTED:
        raise ValueError("ACCEPTED assessments are not semantic-eligible")
    rejection = assessment.rejection_reason
    source = assessment.candidate_evidence_source
    if decision is EvidenceDecision.REJECTED:
        if rejection is IdentityRejectionReason.MPN_MISMATCH:
            raise ValueError("MPN_MISMATCH REJECTED is not semantic-eligible")
        if rejection is IdentityRejectionReason.NO_EXPLICIT_MPN_EVIDENCE:
            if source not in (EvidenceSource.TITLE_TEXT, EvidenceSource.SKU_FIELD):
                raise ValueError(
                    f"NO_EXPLICIT_MPN_EVIDENCE with source {source} is not "
                    f"semantic-eligible (need TITLE_TEXT or SKU_FIELD)"
                )
        elif rejection is IdentityRejectionReason.PARTIAL_MPN_ONLY:
            pass
        else:
            raise ValueError(
                f"REJECTED with reason {rejection} is not semantic-eligible"
            )
    else:
        raise ValueError(
            f"Decision {decision} is not a semantic-eligible deterministic state"
        )


def _is_semantic_eligible(assessment: ListingIdentityAssessment) -> bool:
    """Decide whether this assessment is eligible for semantic evaluation."""
    decision = assessment.decision
    if decision is EvidenceDecision.ACCEPTED:
        return False
    if decision is EvidenceDecision.UNDECIDED:
        return False
    if decision is not EvidenceDecision.REJECTED:
        return False
    rejection = assessment.rejection_reason
    source = assessment.candidate_evidence_source
    if rejection is IdentityRejectionReason.MPN_MISMATCH:
        return False
    if rejection is IdentityRejectionReason.PARTIAL_MPN_ONLY:
        return True
    if rejection is IdentityRejectionReason.NO_EXPLICIT_MPN_EVIDENCE:
        return source in (EvidenceSource.TITLE_TEXT, EvidenceSource.SKU_FIELD)
    return False


def _has_usable_evidence(assessment: ListingIdentityAssessment) -> bool:
    """Check whether the candidate has usable evidence for semantic."""
    observation = assessment.normalized_listing.observation
    if not observation.product_title:
        return False
    return True


def _build_semantic_fields(
    request: ResearchRequest,
    assessment: ListingIdentityAssessment,
) -> dict:
    """Extract semantic prompt fields from the assessment's evidence."""
    observation = assessment.normalized_listing.observation
    return {
        "target_mpn": assessment.requested_part_number,
        "target_description": request.description,
        "candidate_title": observation.product_title or "",
        "candidate_mpn_field": (
            observation.manufacturer_part_number_text
            if observation.manufacturer_part_number_text
            else None
        ),
        "candidate_sku": (
            observation.sku_text
            if observation.sku_text
            else None
        ),
        "candidate_specs": _build_candidate_specs(observation),
        "evidence_source": assessment.candidate_evidence_source.value,
    }


def _build_candidate_specs(observation: ListingObservation) -> str | None:
    """Build candidate specs from available observation fields."""
    parts = []
    if observation.brand_text:
        parts.append(f"Brand: {observation.brand_text}")
    if observation.manufacturer_part_number_text:
        parts.append(f"MPN: {observation.manufacturer_part_number_text}")
    if observation.sku_text:
        parts.append(f"SKU: {observation.sku_text}")
    if observation.condition_text:
        parts.append(f"Condition: {observation.condition_text}")
    if not parts:
        return None
    return " | ".join(parts)


def _get_semantic_detail_code(result: SemanticRuntimeResult) -> ExecutionDetailCode:
    if result.decision is SemanticDecision.MATCH:
        return ExecutionDetailCode.for_semantic_match()
    if result.decision is SemanticDecision.NO_MATCH:
        return ExecutionDetailCode.for_semantic_no_match()
    return ExecutionDetailCode.for_semantic_uncertain()


def _map_semantic_decision(result: SemanticRuntimeResult) -> EvidenceDecision:
    if result.decision is SemanticDecision.MATCH:
        return EvidenceDecision.AI_ASSISTED_MATCH
    return EvidenceDecision.UNDECIDED


def _candidate_case_id(assessment: ListingIdentityAssessment, index: int) -> str:
    """Generate a stable case identifier for one candidate."""
    url = assessment.normalized_listing.observation.source_url
    import hashlib
    url_hash = hashlib.sha256(url.encode()).hexdigest()[:8]
    return f"candidate-{url_hash}-{index}"


def evaluate_semantic_matches(
    request: ResearchRequest,
    assessments: Sequence[ListingIdentityAssessment],
    evidence_writer: ExecutionEvidenceWriter,
    runtime: SemanticRuntime | None = None,
) -> tuple[AiAssistedMatchResult, ...]:
    """Evaluate semantic matches for eligible unresolved candidates.

    This is the main integration entry point called after deterministic
    identity assessment in the execution pipeline.

    Rules:
    - Only semantic-eligible candidates are evaluated
    - Candidates must have usable extracted evidence (at minimum, title)
    - The default SemanticRuntime is constructed lazily on first need
    - Each eligible candidate gets exactly one semantic runtime call
    - Programming exceptions from the runtime propagate
    """
    ai_assisted_results: list[AiAssistedMatchResult] = []

    for idx, assessment in enumerate(assessments):
        if not _is_semantic_eligible(assessment):
            continue
        if not _has_usable_evidence(assessment):
            continue

        if runtime is None:
            runtime = get_default_runtime()

        fields = _build_semantic_fields(request, assessment)
        case_id = _candidate_case_id(assessment, idx)
        url = assessment.normalized_listing.observation.source_url

        semantic_result = runtime.evaluate(
            case_id=case_id,
            target_mpn=fields["target_mpn"],
            target_description=fields["target_description"],
            candidate_title=fields["candidate_title"],
            candidate_mpn_field=fields["candidate_mpn_field"],
            candidate_sku=fields["candidate_sku"],
            candidate_specs=fields["candidate_specs"],
            evidence_source=fields["evidence_source"],
        )

        if semantic_result.error_type is not None:
            evidence_writer.append_execution_attempt(
                stage=ExecutionStage.SEMANTIC,
                outcome=ExecutionOutcome.FAILED,
                candidate_url=url,
                detail_code=ExecutionDetailCode.for_semantic_unavailable(),
            )
        else:
            detail_code = _get_semantic_detail_code(semantic_result)
            evidence_writer.append_execution_attempt(
                stage=ExecutionStage.SEMANTIC,
                outcome=ExecutionOutcome.SUCCESS,
                candidate_url=url,
                detail_code=detail_code,
            )

        disposition = _map_semantic_decision(semantic_result)
        if disposition is EvidenceDecision.AI_ASSISTED_MATCH:
            ai_assisted_results.append(
                AiAssistedMatchResult(
                    original_assessment=assessment,
                    semantic_result=semantic_result,
                    disposition=disposition,
                )
            )

    return tuple(ai_assisted_results)
