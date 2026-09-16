"""Comparable research orchestration (PRODUCT-INTEL.7C-B).

Composes the frozen comparable-research primitives into one bounded
execution pipeline:

    claim ComparableResearchExecution
        -> exact parent ResearchRun request
        -> PRE1 authority acquisition
        -> target frozen 6C specification extraction
        -> frozen 7A candidate discovery
        -> candidate ProductIdentity bridge (frozen 7B)
        -> candidate 6C from HELD authoritative support documents
        -> ONE frozen 6D batch enrichment (target + candidates)
        -> frozen 6C + 6D composition
        -> pure frozen 7B similarity scoring
        -> pure ComparableResearchResult projection
        -> frozen V1 comparable codec
        -> atomic ComparableResearchExecution completion

No web presentation or trigger routes are implemented here.
No frozen contract is modified.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import datetime
from typing import Final

from product_intelligence.domain.models import ProductIdentity
from product_intelligence.execution.comparable_discovery import (
    ComparableCandidateSourceOutcomeState,
    discover_enterprise_ssd_comparable_candidates,
)
from product_intelligence.execution.comparable_research_authority import (
    AuthoritySourceOutcomeState,
    acquire_comparable_research_authority_context,
)
from product_intelligence.execution.specification_enrichment import (
    BatchEnrichmentIdentityResult,
    DatasheetOutcomeState,
    DatasheetSourceOutcome,
    compose_6c_6d_specifications,
    enrich_enterprise_ssd_specifications_batch,
)
from product_intelligence.execution.specification_evidence import (
    research_enterprise_ssd_specifications,
)
from product_intelligence.providers.page import (
    PageFetchError,
    PageFetchRequest,
    UnsafeFetchTargetError,
)
from product_intelligence.research.comparable_candidates import (
    ComparableCandidateSource,
)
from product_intelligence.research.comparable_research_results import (
    AUTHORITY_FATAL_OUTCOMES,
    AuthorityAttemptResult,
    AuthorityAuditOutcomeKind,
    ComparableCandidateResult,
    ComparableResearchResult,
    ComparableResultKind,
    DatasheetAttemptResult,
    DatasheetAuditOutcomeKind,
    EvidenceLayer,
    EvidenceSourceReference,
    FieldAssessmentResult,
    ProductEnrichmentAudit,
)
from product_intelligence.research.comparable_result_codec import (
    COMPARABLE_RESULT_SCHEMA_VERSION,
    ComparableResultCodecError,
    encode_comparable_result,
)
from product_intelligence.research.enterprise_ssd import (
    ENTERPRISE_SSD_SCHEMA,
    normalize_enterprise_ssd_observation,
)
from product_intelligence.research.enterprise_ssd_extraction import (
    extract_enterprise_ssd_specification_observations,
)
from product_intelligence.research.enterprise_ssd_similarity import (
    ComparableCandidateSpecificationProfile,
    SpecificationSimilarityFieldAssessment,
    establish_candidate_product_identity,
    score_enterprise_ssd_candidate_similarity,
)
from product_intelligence.research.specifications import (
    NormalizedSpecificationObservation,
    ProductSpecificationSet,
    resolve_specification,
)
from product_intelligence.runs.comparable_execution_claims import (
    claim_comparable_research,
    complete_comparable_research,
    fail_comparable_research,
)
from product_intelligence.runs.models import (
    ComparableResearchFailureReason,
    ComparableResearchExecution,
)

__all__ = [
    "ComparableResearchExecutionError",
    "execute_comparable_research",
]


# ---------------------------------------------------------------------------
# Public bounded execution error
# ---------------------------------------------------------------------------


class ComparableResearchExecutionError(Exception):
    """Expected bounded comparable-research execution failure.

    Raised only AFTER the claimed child has been terminalised FAILED through
    the frozen runs-layer failure primitive with one of the bounded
    ComparableResearchFailureReason constants.

    This error is the public signal that one bounded execution failure
    occurred. It is NOT a wrapper for arbitrary programming exceptions —
    those propagate unchanged via the INTERNAL_ERROR best-effort path.
    """


# ---------------------------------------------------------------------------
# Module-private bounded-failure signal
# ---------------------------------------------------------------------------


class _BoundedComparableFailure(Exception):
    """Internal pipeline signal for an expected bounded failure.

    Carries the exact frozen ComparableResearchFailureReason.
    The public operation terminalises the child before raising the public
    ComparableResearchExecutionError.
    """

    def __init__(self, reason: str, detail: str) -> None:
        super().__init__(detail)
        self.reason = reason
        self.detail = detail


# ---------------------------------------------------------------------------
# Exhaustive outcome mapping tables
# ---------------------------------------------------------------------------

_AUTHORITY_STATE_TO_AUDIT_KIND: Final[dict[AuthoritySourceOutcomeState, AuthorityAuditOutcomeKind]] = {
    AuthoritySourceOutcomeState.MATCHED: AuthorityAuditOutcomeKind.MATCHED,
    AuthoritySourceOutcomeState.NO_REQUESTED_MPN: AuthorityAuditOutcomeKind.NO_REQUESTED_MPN,
    AuthoritySourceOutcomeState.NO_MPN_IN_SOURCE: AuthorityAuditOutcomeKind.NO_MPN_IN_SOURCE,
    AuthoritySourceOutcomeState.AMBIGUOUS_MPN_MATCH: AuthorityAuditOutcomeKind.AMBIGUOUS_MPN_MATCH,
    AuthoritySourceOutcomeState.AUTHORITY_HOST_ESCAPED: AuthorityAuditOutcomeKind.AUTHORITY_HOST_ESCAPED,
    AuthoritySourceOutcomeState.AUTHORITY_SOURCE_REFUSED: AuthorityAuditOutcomeKind.AUTHORITY_SOURCE_REFUSED,
    AuthoritySourceOutcomeState.AUTHORITY_FETCH_FAILED: AuthorityAuditOutcomeKind.AUTHORITY_FETCH_FAILED,
    AuthoritySourceOutcomeState.NO_STRUCTURAL_OBSERVATIONS: AuthorityAuditOutcomeKind.NO_STRUCTURAL_OBSERVATIONS,
}

_AUTHORITY_INCOMPLETE_FAILURE_REASONS: Final[dict[AuthorityAuditOutcomeKind, str]] = {
    AuthorityAuditOutcomeKind.AUTHORITY_FETCH_FAILED: ComparableResearchFailureReason.AUTHORITY_FETCH_FAILED,
    AuthorityAuditOutcomeKind.AUTHORITY_SOURCE_REFUSED: ComparableResearchFailureReason.AUTHORITY_SOURCE_REFUSED,
    AuthorityAuditOutcomeKind.AUTHORITY_HOST_ESCAPED: ComparableResearchFailureReason.AUTHORITY_HOST_ESCAPED,
    AuthorityAuditOutcomeKind.NO_STRUCTURAL_OBSERVATIONS: ComparableResearchFailureReason.AUTHORITY_NO_STRUCTURAL_OBSERVATIONS,
}

_DATASHEET_STATE_TO_AUDIT_KIND: Final[dict[DatasheetOutcomeState, DatasheetAuditOutcomeKind]] = {
    DatasheetOutcomeState.ENRICHED: DatasheetAuditOutcomeKind.ENRICHED,
    DatasheetOutcomeState.NO_OBSERVATIONS: DatasheetAuditOutcomeKind.NO_OBSERVATIONS,
    DatasheetOutcomeState.FETCH_FAILED: DatasheetAuditOutcomeKind.FETCH_FAILED,
    DatasheetOutcomeState.SOURCE_REFUSED: DatasheetAuditOutcomeKind.SOURCE_REFUSED,
    DatasheetOutcomeState.PARSE_FAILED: DatasheetAuditOutcomeKind.PARSE_FAILED,
}


# ---------------------------------------------------------------------------
# Module-private data helpers
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class _HeldCandidateDocument:
    source: ComparableCandidateSource
    body_text: str
    final_url: str
    retrieved_at: datetime


@dataclass(frozen=True)
class _HeldCandidateSpecResearch:
    spec_set: ProductSpecificationSet
    normalized_observations: tuple[NormalizedSpecificationObservation, ...]


# ---------------------------------------------------------------------------
# Evidence-layer classification (object-identity pools)
# ---------------------------------------------------------------------------


class _EvidencePools:
    """Classify final NormalizedSpecificationObservation evidence by exact
    object identity into SUPPORT_PAGE (6C) or DATASHEET_PDF (6D) pools.

    An observation that appears in neither pool, or in both, is a
    programming/invariant error.
    """

    __slots__ = ("_support_ids", "_datasheet_ids")

    def __init__(
        self,
        *,
        support_page_observations: tuple[NormalizedSpecificationObservation, ...],
        datasheet_observations: tuple[NormalizedSpecificationObservation, ...],
    ) -> None:
        self._support_ids = frozenset(id(o) for o in support_page_observations)
        self._datasheet_ids = frozenset(id(o) for o in datasheet_observations)

    def classify(
        self, observation: NormalizedSpecificationObservation
    ) -> EvidenceLayer:
        obs_id = id(observation)
        in_support = obs_id in self._support_ids
        in_datasheet = obs_id in self._datasheet_ids
        if in_support and in_datasheet:
            raise ValueError(
                "invariant: evidence observation belongs to both the "
                "SUPPORT_PAGE and DATASHEET_PDF pools"
            )
        if in_support:
            return EvidenceLayer.SUPPORT_PAGE
        if in_datasheet:
            return EvidenceLayer.DATASHEET_PDF
        raise ValueError(
            "invariant: final evidence observation belongs to neither "
            "product evidence pool"
        )


# ---------------------------------------------------------------------------
# Authorised failure helper
# ---------------------------------------------------------------------------


def _terminate_failed(child_pk: str, reason: str) -> None:
    """Terminalise the claimed child as FAILED with the exact bounded reason.

    If the publication itself fails the error propagates — the caller must
    not claim the child was terminalised when persistence failed.
    """
    fail_comparable_research(child_pk, reason)


# ---------------------------------------------------------------------------
# Pipeline helpers
# ---------------------------------------------------------------------------


def _project_authority_audit(
    source_outcomes: tuple[object, ...],
) -> tuple[AuthorityAttemptResult, ...]:
    """Project every PRE1 source outcome into the frozen 7C-A audit tuple.

    Uses the frozen _AuthoritySourceOutcome public fields directly. Does not
    import the private _AuthoritySourceOutcome class.
    """
    attempts: list[AuthorityAttemptResult] = []
    for outcome in source_outcomes:
        kind = _AUTHORITY_STATE_TO_AUDIT_KIND[outcome.outcome_state]
        attempts.append(
            AuthorityAttemptResult(
                policy_id=outcome.policy_id,
                outcome=kind,
                requested_source_url=outcome.requested_source_url,
                fetched_final_url=outcome.fetched_final_url,
                retrieved_at=(
                    outcome.retrieved_at.isoformat()
                    if outcome.retrieved_at is not None
                    else None
                ),
                matching_mpn=outcome.matching_mpn_evidence,
            )
        )
    return tuple(attempts)


def _first_incomplete_authority_attempt(
    authority_audit: tuple[AuthorityAttemptResult, ...],
) -> AuthorityAttemptResult | None:
    for attempt in authority_audit:
        if attempt.outcome in AUTHORITY_FATAL_OUTCOMES:
            return attempt
    return None


def _abstention_result_kind(
    authority_audit: tuple[AuthorityAttemptResult, ...],
) -> ComparableResultKind:
    """Derive the COMPLETED abstention kind from the projected authority audit."""
    outcomes = tuple(a.outcome for a in authority_audit)
    if not outcomes:
        raise ValueError("authority audit is empty; cannot derive abstention kind")
    if all(o is AuthorityAuditOutcomeKind.NO_REQUESTED_MPN for o in outcomes):
        return ComparableResultKind.NO_REQUESTED_MPN
    matched_count = sum(
        1 for o in outcomes
        if o is AuthorityAuditOutcomeKind.MATCHED
    )
    if (
        any(
            o is AuthorityAuditOutcomeKind.AMBIGUOUS_MPN_MATCH for o in outcomes
        )
        or matched_count > 1
    ):
        return ComparableResultKind.AMBIGUOUS_AUTHORITY
    if all(o is AuthorityAuditOutcomeKind.NO_MPN_IN_SOURCE for o in outcomes):
        return ComparableResultKind.NO_AUTHORITY_MATCH
    raise ValueError(
        "unclassifiable authority abstention shape: "
        f"{[o.value for o in outcomes]}"
    )


def _project_datasheet_attempt(
    outcome: DatasheetSourceOutcome,
) -> DatasheetAttemptResult:
    return DatasheetAttemptResult(
        outcome=_DATASHEET_STATE_TO_AUDIT_KIND[outcome.outcome_state],
        source_name=outcome.source.source_name,
        source_url=outcome.source.source_url,
        final_url=outcome.final_url,
        retrieved_at=(
            outcome.retrieved_at.isoformat()
            if outcome.retrieved_at is not None
            else None
        ),
        observation_count=outcome.observation_count,
    )


def _acquire_held_candidate_documents(
    discovery_result,
    page_fetcher,
) -> tuple[_HeldCandidateDocument, ...]:
    """Fetch each unique EXTRACTED 7A source exactly ONCE for candidate 6C."""
    unique_sources: list[ComparableCandidateSource] = []
    seen: set[ComparableCandidateSource] = set()

    for outcome in discovery_result.source_outcomes:
        if outcome.outcome_state is not ComparableCandidateSourceOutcomeState.EXTRACTED:
            continue
        source = outcome.source
        if source in seen:
            continue
        seen.add(source)
        unique_sources.append(source)

    held: list[_HeldCandidateDocument] = []
    for source in unique_sources:
        try:
            fetched = page_fetcher.fetch(PageFetchRequest(url=source.source_url))
        except UnsafeFetchTargetError:
            continue
        except PageFetchError:
            continue
        held.append(
            _HeldCandidateDocument(
                source=source,
                body_text=fetched.body_text,
                final_url=fetched.final_url,
                retrieved_at=fetched.retrieved_at,
            )
        )
    return tuple(held)


def _research_candidate_specifications_from_held_documents(
    *,
    candidate_identity: ProductIdentity,
    held_documents: tuple[_HeldCandidateDocument, ...],
) -> _HeldCandidateSpecResearch:
    """Pure per-candidate 6C extraction from HELD documents."""
    raw_observations: list[object] = []
    for held in held_documents:
        raw_observations.extend(
            extract_enterprise_ssd_specification_observations(
                product_identity=candidate_identity,
                document=held.body_text,
                source_name=held.source.source_name,
                source_url=held.source.source_url,
                final_url=held.final_url,
                retrieved_at=held.retrieved_at,
                source_authority=held.source.source_authority,
            )
        )

    normalized: list[NormalizedSpecificationObservation] = [
        normalize_enterprise_ssd_observation(obs) for obs in raw_observations
    ]

    obs_by_def: dict[str, list[NormalizedSpecificationObservation]] = {
        key: [] for key in ENTERPRISE_SSD_SCHEMA.definitions
    }
    for norm in normalized:
        obs_by_def[norm.observation.definition.key].append(norm)

    resolutions = {
        key: resolve_specification(
            candidate_identity, definition, tuple(obs_by_def[key])
        )
        for key, definition in ENTERPRISE_SSD_SCHEMA.definitions.items()
    }
    spec_set = ProductSpecificationSet(
        product_identity=candidate_identity,
        category_schema=ENTERPRISE_SSD_SCHEMA,
        resolutions=resolutions,
    )
    return _HeldCandidateSpecResearch(
        spec_set=spec_set,
        normalized_observations=tuple(normalized),
    )


def _validate_batch_mapping(identities, batch_results) -> None:
    if len(batch_results) != len(identities):
        raise ValueError(
            f"batch returned {len(batch_results)} results for "
            f"{len(identities)} identities"
        )
    for identity, result in zip(identities, batch_results):
        if result.product_identity is not identity:
            raise ValueError(
                "6D batch result identity does not match the requested "
                "identity order"
            )


def _compose_product_specifications(
    *,
    identity: ProductIdentity,
    product_mpn: str,
    frozen_6c_spec_set: ProductSpecificationSet,
    batch_result: BatchEnrichmentIdentityResult,
) -> tuple[ProductSpecificationSet, ProductEnrichmentAudit]:
    enrichment = batch_result.enrichment_result
    if enrichment is None:
        if batch_result.datasheet_source is not None:
            raise ValueError(
                "invariant: enrichment_result is None but datasheet_source is set"
            )
        audit = ProductEnrichmentAudit(
            product_mpn=product_mpn,
            attempts=(
                DatasheetAttemptResult(
                    outcome=DatasheetAuditOutcomeKind.NO_DATASHEET_SOURCE
                ),
            ),
        )
        return frozen_6c_spec_set, audit

    attempts = tuple(
        _project_datasheet_attempt(o) for o in enrichment.source_outcomes
    )
    audit = ProductEnrichmentAudit(product_mpn=product_mpn, attempts=attempts)
    composed = compose_6c_6d_specifications(
        product_identity=identity,
        frozen_6c_spec_set=frozen_6c_spec_set,
        enrichment_result=enrichment,
    )
    return composed, audit


# ---------------------------------------------------------------------------
# Field-level durable projection helpers
# ---------------------------------------------------------------------------


def _project_resolved_value(resolution) -> str | None:
    value = resolution.resolved_value
    if value is None:
        return None
    return str(value.value)


def _project_evidence_reference(
    normalized_observation: NormalizedSpecificationObservation,
    pools: _EvidencePools,
) -> EvidenceSourceReference:
    obs = normalized_observation.observation
    return EvidenceSourceReference(
        source_name=obs.source_name,
        source_url=obs.source_url,
        source_authority=obs.source_authority,
        retrieved_at=obs.retrieved_at.isoformat(),
        evidence_layer=pools.classify(normalized_observation),
    )


def _project_evidence_tuple(
    evidence: tuple[NormalizedSpecificationObservation, ...],
    pools: _EvidencePools,
) -> tuple[EvidenceSourceReference, ...]:
    return tuple(_project_evidence_reference(e, pools) for e in evidence)


def _project_field_assessment(
    assessment: SpecificationSimilarityFieldAssessment,
    target_pools: _EvidencePools,
    candidate_pools: _EvidencePools,
) -> FieldAssessmentResult:
    return FieldAssessmentResult(
        definition_key=assessment.definition.key,
        comparison_state=assessment.comparison_state,
        target_resolution_state=assessment.target_resolution.state,
        candidate_resolution_state=assessment.candidate_resolution.state,
        field_similarity=assessment.field_similarity,
        target_value=_project_resolved_value(assessment.target_resolution),
        candidate_value=_project_resolved_value(assessment.candidate_resolution),
        target_evidence=_project_evidence_tuple(
            assessment.target_resolution.evidence, target_pools
        ),
        candidate_evidence=_project_evidence_tuple(
            assessment.candidate_resolution.evidence, candidate_pools
        ),
    )


def _project_candidate_result(
    *,
    candidate,
    similarity,
    enrichment_audit: ProductEnrichmentAudit,
    support_page_observations: tuple[NormalizedSpecificationObservation, ...],
    datasheet_observations: tuple[NormalizedSpecificationObservation, ...],
    target_pools: _EvidencePools,
) -> ComparableCandidateResult:
    candidate_pools = _EvidencePools(
        support_page_observations=support_page_observations,
        datasheet_observations=datasheet_observations,
    )
    field_assessments = tuple(
        _project_field_assessment(fa, target_pools, candidate_pools)
        for fa in similarity.field_assessments
    )
    return ComparableCandidateResult(
        candidate_mpn=candidate.manufacturer_part_number,
        candidate_normalized_mpn=candidate.normalized_part_number,
        scored_field_count=similarity.scored_field_count,
        evidence_coverage=similarity.evidence_coverage,
        observed_similarity=similarity.observed_similarity,
        evidence_weighted_similarity=similarity.evidence_weighted_similarity,
        field_assessments=field_assessments,
        enrichment_audit=enrichment_audit,
    )


# ---------------------------------------------------------------------------
# Core pipeline (returns the pure result; fails via _BoundedComparableFailure)
# ---------------------------------------------------------------------------


def _run_comparable_pipeline(
    *,
    parent_run,
    page_fetcher,
    document_fetcher,
) -> ComparableResearchResult:
    # 2/3. Exact parent request from persisted fields.
    request = parent_run.to_research_request()

    # 4. PRE1 authority acquisition (frozen public function, no policies).
    authority = acquire_comparable_research_authority_context(
        request=request,
        page_fetcher=page_fetcher,
    )
    authority_audit = _project_authority_audit(authority.source_outcomes)

    # PRE1 failure / abstention precedence (source outcomes, not status).
    incomplete = _first_incomplete_authority_attempt(authority_audit)
    if incomplete is not None:
        raise _BoundedComparableFailure(
            reason=_AUTHORITY_INCOMPLETE_FAILURE_REASONS[incomplete.outcome],
            detail=(
                f"authority acquisition incomplete: "
                f"{incomplete.outcome.value} "
                f"(policy {incomplete.policy_id})"
            ),
        )

    context = authority.context
    if context is None:
        return ComparableResearchResult(
            kind=_abstention_result_kind(authority_audit),
            target_mpn=request.manufacturer_part_number,
            target_manufacturer=None,
            target_enrichment_audit=None,
            authority_audit=authority_audit,
            candidates=(),
        )

    # 5. Target frozen 6C.
    target_6c = research_enterprise_ssd_specifications(
        product_identity=context.target_identity,
        sources=(context.specification_source,),
        page_fetcher=page_fetcher,
    )
    target_spec_set = target_6c.product_specification_set

    # 6. Frozen 7A discovery.
    discovery = discover_enterprise_ssd_comparable_candidates(
        target_identity=context.target_identity,
        target_specification_set=target_spec_set,
        sources=(context.comparable_source,),
        page_fetcher=page_fetcher,
    )

    # 7. Candidate identities (frozen 7B bridge, original order).
    candidates = discovery.candidates
    candidate_identities = tuple(
        establish_candidate_product_identity(candidate) for candidate in candidates
    )

    # 8. Candidate 6C from HELD authoritative support documents.
    held_documents = (
        _acquire_held_candidate_documents(discovery, page_fetcher)
        if candidate_identities
        else ()
    )
    candidate_spec_research = {
        identity: _research_candidate_specifications_from_held_documents(
            candidate_identity=identity,
            held_documents=held_documents,
        )
        for identity in candidate_identities
    }

    # 9. ONE frozen 6D batch (target + candidates).
    batch_identities = (context.target_identity, *candidate_identities)
    batch_results = enrich_enterprise_ssd_specifications_batch(
        identities=batch_identities,
        discovery_result=discovery,
        page_fetcher=page_fetcher,
        document_fetcher=document_fetcher,
    )
    _validate_batch_mapping(batch_identities, batch_results)

    # 10. 6C + 6D composition + enrichment audit.
    target_batch = batch_results[0]
    target_final_spec_set, target_enrichment_audit = _compose_product_specifications(
        identity=context.target_identity,
        product_mpn=context.target_identity.manufacturer_part_number,
        frozen_6c_spec_set=target_spec_set,
        batch_result=target_batch,
    )

    candidate_final_sets: list[ProductSpecificationSet] = []
    candidate_audits: list[ProductEnrichmentAudit] = []
    candidate_ds_obs: list[tuple[NormalizedSpecificationObservation, ...]] = []
    for idx, identity in enumerate(candidate_identities):
        final_set, audit = _compose_product_specifications(
            identity=identity,
            product_mpn=identity.manufacturer_part_number,
            frozen_6c_spec_set=candidate_spec_research[identity].spec_set,
            batch_result=batch_results[idx + 1],
        )
        candidate_final_sets.append(final_set)
        candidate_audits.append(audit)
        enrichment = batch_results[idx + 1].enrichment_result
        candidate_ds_obs.append(
            enrichment.normalized_observations if enrichment is not None else ()
        )

    # 11. Pure frozen 7B scoring (discovery order, no ranking).
    similarities = []
    for idx, candidate in enumerate(candidates):
        profile = ComparableCandidateSpecificationProfile(
            candidate=candidate,
            candidate_identity=candidate_identities[idx],
            specification_set=candidate_final_sets[idx],
        )
        similarities.append(
            score_enterprise_ssd_candidate_similarity(
                target_specification_set=target_final_spec_set,
                candidate_profile=profile,
            )
        )

    # 12. Field-level durable projection.
    target_pools = _EvidencePools(
        support_page_observations=target_6c.normalized_observations,
        datasheet_observations=(
            target_batch.enrichment_result.normalized_observations
            if target_batch.enrichment_result is not None
            else ()
        ),
    )

    projected_candidates: list[ComparableCandidateResult] = []
    for idx, candidate in enumerate(candidates):
        projected_candidates.append(
            _project_candidate_result(
                candidate=candidate,
                similarity=similarities[idx],
                enrichment_audit=candidate_audits[idx],
                support_page_observations=candidate_spec_research[
                    candidate_identities[idx]
                ].normalized_observations,
                datasheet_observations=candidate_ds_obs[idx],
                target_pools=target_pools,
            )
        )

    # 13. FULL result (target from authoritative context identity).
    return ComparableResearchResult(
        kind=ComparableResultKind.FULL,
        target_mpn=context.target_identity.manufacturer_part_number,
        target_manufacturer=context.target_identity.manufacturer,
        target_enrichment_audit=target_enrichment_audit,
        authority_audit=authority_audit,
        candidates=tuple(projected_candidates),
    )


# ---------------------------------------------------------------------------
# Public operation
# ---------------------------------------------------------------------------


def execute_comparable_research(
    child_id: uuid.UUID | str,
    *,
    page_fetcher,
    document_fetcher,
) -> ComparableResearchExecution:
    """Execute one already-created PENDING ComparableResearchExecution.

    Parameters
    ----------
    child_id
        The ComparableResearchExecution to execute.
    page_fetcher
        Page acquisition protocol (PageFetcher).
    document_fetcher
        Document acquisition protocol (DocumentFetcher).

    Returns
    -------
    ComparableResearchExecution
        The refreshed terminal row.

    Raises
    ------
    ComparableResearchExecutionError
        Expected bounded failure after the child was terminalised FAILED.
    ComparableResearchClaimError
        If the child cannot be claimed (before any pipeline work).
    Exception
        Unexpected programming/invariant exceptions propagate after a
        best-effort INTERNAL_ERROR publication.
    """
    # 1. Claim (PENDING -> RUNNING). Claim errors propagate; no child
    # was terminalised before this point.
    claimed = claim_comparable_research(child_id)
    child_pk = str(claimed.id)

    try:
        result = _run_comparable_pipeline(
            parent_run=claimed.parent_run,
            page_fetcher=page_fetcher,
            document_fetcher=document_fetcher,
        )
        payload = encode_comparable_result(result)
    except _BoundedComparableFailure as bounded:
        _terminate_failed(child_pk, bounded.reason)
        raise ComparableResearchExecutionError(bounded.detail) from bounded
    except ComparableResearchExecutionError:
        raise
    except ComparableResultCodecError as exc:
        _terminate_failed(
            child_pk,
            ComparableResearchFailureReason.RESULT_ENCODING_FAILED,
        )
        raise ComparableResearchExecutionError(
            "comparable result encoding failed"
        ) from exc
    except Exception:
        try:
            fail_comparable_research(
                child_pk,
                ComparableResearchFailureReason.INTERNAL_ERROR,
            )
        except Exception:
            pass
        raise

    # Terminal completion — DB publication failures propagate as-is;
    # the child may remain RUNNING and must NOT be rewritten to FAILED.
    return complete_comparable_research(
        child_pk,
        COMPARABLE_RESULT_SCHEMA_VERSION,
        payload,
    )
