"""Comparable research presentation (PRODUCT-INTEL.7C-C).

Pure display-only module. Takes a decoded ``ComparableResearchResult`` and
returns immutable presentation objects for the Django template.

May import: stdlib, domain contracts/enums, research contracts/schema.
Must NOT import: runs, execution, providers, Django ORM.

No recomputation of similarity, ranking, or any comparable semantics.
Decimal values are displayed as string-exact.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from product_intelligence.research.comparable_research_results import (
        ComparableCandidateResult,
        ComparableResearchResult,
        FieldAssessmentResult,
        AuthorityAttemptResult,
        DatasheetAttemptResult,
        EvidenceSourceReference,
        ProductEnrichmentAudit,
        ComparableResultKind,
    )

# Reuse the authoritative URL safety helper from the existing presentation
# module — never duplicate it.
from .presentation import _is_safe_href_url


# ---------------------------------------------------------------------------
# Resolution state -> display label
# ---------------------------------------------------------------------------

_RESOLUTION_STATE_LABELS: dict[str, str] = {
    "VERIFIED": "Verified",
    "UNVERIFIED": "Unverified",
    "CONFLICT": "Conflict",
    "UNKNOWN": "Unknown",
}


# ---------------------------------------------------------------------------
# Evidence presentation
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class EvidenceReferenceDisplay:
    """Display object for one evidence source reference."""

    source_name: str
    source_url: str
    source_url_safe: bool
    source_authority: str
    evidence_layer: str
    retrieved_at: str


def _build_evidence_display(
    ref: Any,
) -> EvidenceReferenceDisplay:
    return EvidenceReferenceDisplay(
        source_name=ref.source_name,
        source_url=ref.source_url,
        source_url_safe=_is_safe_href_url(ref.source_url),
        source_authority=ref.source_authority.value,
        evidence_layer=ref.evidence_layer.value,
        retrieved_at=ref.retrieved_at,
    )


# ---------------------------------------------------------------------------
# Field assessment presentation
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class FieldAssessmentDisplay:
    """Display object for one specification field comparison."""

    definition_key: str
    definition_label: str
    unit: str | None
    comparison_state: str
    target_resolution_state: str
    candidate_resolution_state: str
    target_value: str | None
    candidate_value: str | None
    field_similarity: str | None
    target_evidence: tuple[EvidenceReferenceDisplay, ...]
    candidate_evidence: tuple[EvidenceReferenceDisplay, ...]


def _build_field_display(
    assessment: Any,
) -> FieldAssessmentDisplay:
    """Build a display object for one FieldAssessmentResult.

    Uses frozen ENTERPRISE_SSD_SCHEMA for label and unit.
    """
    from product_intelligence.research.enterprise_ssd import (
        ENTERPRISE_SSD_SCHEMA,
    )

    definition = ENTERPRISE_SSD_SCHEMA.definitions.get(assessment.definition_key)
    label = definition.label if definition else assessment.definition_key
    unit = definition.unit if definition else None

    # Decimal -> string (never float)
    sim_str: str | None = None
    if assessment.field_similarity is not None:
        sim_str = str(assessment.field_similarity)

    return FieldAssessmentDisplay(
        definition_key=assessment.definition_key,
        definition_label=label,
        unit=unit,
        comparison_state=assessment.comparison_state.value,
        target_resolution_state=assessment.target_resolution_state.value,
        candidate_resolution_state=assessment.candidate_resolution_state.value,
        target_value=assessment.target_value,
        candidate_value=assessment.candidate_value,
        field_similarity=sim_str,
        target_evidence=tuple(
            _build_evidence_display(ref) for ref in assessment.target_evidence
        ),
        candidate_evidence=tuple(
            _build_evidence_display(ref) for ref in assessment.candidate_evidence
        ),
    )


# ---------------------------------------------------------------------------
# Authority attempt presentation
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class AuthorityAttemptDisplay:
    """Display object for one authority audit attempt."""

    policy_id: str
    outcome: str
    requested_source_url: str | None
    requested_source_url_safe: bool
    fetched_final_url: str | None
    fetched_final_url_safe: bool
    retrieved_at: str | None
    matching_mpn: str | None


def _build_authority_attempt_display(
    attempt: Any,
) -> AuthorityAttemptDisplay:
    return AuthorityAttemptDisplay(
        policy_id=attempt.policy_id,
        outcome=attempt.outcome.value,
        requested_source_url=attempt.requested_source_url,
        requested_source_url_safe=(
            _is_safe_href_url(attempt.requested_source_url)
            if attempt.requested_source_url
            else False
        ),
        fetched_final_url=attempt.fetched_final_url,
        fetched_final_url_safe=(
            _is_safe_href_url(attempt.fetched_final_url)
            if attempt.fetched_final_url
            else False
        ),
        retrieved_at=attempt.retrieved_at,
        matching_mpn=attempt.matching_mpn,
    )


# ---------------------------------------------------------------------------
# Datasheet attempt presentation
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class DatasheetAttemptDisplay:
    """Display object for one datasheet enrichment attempt."""

    outcome: str
    source_name: str | None
    source_url: str | None
    source_url_safe: bool
    final_url: str | None
    final_url_safe: bool
    retrieved_at: str | None
    observation_count: int | None


def _build_datasheet_attempt_display(
    attempt: Any,
) -> DatasheetAttemptDisplay:
    return DatasheetAttemptDisplay(
        outcome=attempt.outcome.value,
        source_name=attempt.source_name,
        source_url=attempt.source_url,
        source_url_safe=(
            _is_safe_href_url(attempt.source_url)
            if attempt.source_url
            else False
        ),
        final_url=attempt.final_url,
        final_url_safe=(
            _is_safe_href_url(attempt.final_url)
            if attempt.final_url
            else False
        ),
        retrieved_at=attempt.retrieved_at,
        observation_count=attempt.observation_count,
    )


# ---------------------------------------------------------------------------
# Enrichment audit presentation
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class EnrichmentAuditDisplay:
    """Display object for a product enrichment audit."""

    product_mpn: str
    attempts: tuple[DatasheetAttemptDisplay, ...]


def _build_enrichment_audit_display(
    audit: Any,
) -> EnrichmentAuditDisplay:
    return EnrichmentAuditDisplay(
        product_mpn=audit.product_mpn,
        attempts=tuple(
            _build_datasheet_attempt_display(a) for a in audit.attempts
        ),
    )


# ---------------------------------------------------------------------------
# Candidate presentation
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class CandidateDisplay:
    """Display object for one comparable candidate."""

    candidate_mpn: str
    candidate_normalized_mpn: str
    scored_field_count: int
    total_field_count: int
    evidence_coverage: str
    observed_similarity: str | None
    evidence_weighted_similarity: str | None
    field_assessments: tuple[FieldAssessmentDisplay, ...]
    enrichment_audit: EnrichmentAuditDisplay


def _build_candidate_display(
    candidate: Any,
) -> CandidateDisplay:
    """Build a display object for one ComparableCandidateResult.

    Does NOT reorder, rank, or filter. Preserves exact persisted order.
    Decimal values remain string-exact (never float).
    """
    from product_intelligence.research.enterprise_ssd import (
        ENTERPRISE_SSD_SCHEMA,
    )

    total_field_count = len(ENTERPRISE_SSD_SCHEMA.definitions)

    return CandidateDisplay(
        candidate_mpn=candidate.candidate_mpn,
        candidate_normalized_mpn=candidate.candidate_normalized_mpn,
        scored_field_count=candidate.scored_field_count,
        total_field_count=total_field_count,
        evidence_coverage=str(candidate.evidence_coverage),
        observed_similarity=(
            str(candidate.observed_similarity)
            if candidate.observed_similarity is not None
            else None
        ),
        evidence_weighted_similarity=(
            str(candidate.evidence_weighted_similarity)
            if candidate.evidence_weighted_similarity is not None
            else None
        ),
        field_assessments=tuple(
            _build_field_display(fa) for fa in candidate.field_assessments
        ),
        enrichment_audit=_build_enrichment_audit_display(
            candidate.enrichment_audit
        ),
    )


# ---------------------------------------------------------------------------
# Top-level result presentation
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class ComparableResultPresentation:
    """Complete presentation for a decoded ComparableResearchResult."""

    kind: str
    target_mpn: str
    target_manufacturer: str | None
    target_enrichment_audit: EnrichmentAuditDisplay | None
    authority_audit: tuple[AuthorityAttemptDisplay, ...]
    candidates: tuple[CandidateDisplay, ...]


def build_comparable_result_presentation(
    result: Any,
) -> ComparableResultPresentation:
    """Build a complete presentation from a decoded ComparableResearchResult.

    Takes one decoded ``ComparableResearchResult`` and returns an immutable
    presentation object. Does not reorder candidates. Does not recompute
    any similarity values.

    Parameters
    ----------
    result
        A decoded ``ComparableResearchResult`` from the frozen codec.

    Returns
    -------
    ComparableResultPresentation
        Immutable display objects for the template.
    """
    return ComparableResultPresentation(
        kind=result.kind.value,
        target_mpn=result.target_mpn,
        target_manufacturer=result.target_manufacturer,
        target_enrichment_audit=(
            _build_enrichment_audit_display(result.target_enrichment_audit)
            if result.target_enrichment_audit is not None
            else None
        ),
        authority_audit=tuple(
            _build_authority_attempt_display(a) for a in result.authority_audit
        ),
        candidates=tuple(
            _build_candidate_display(c) for c in result.candidates
        ),
    )



