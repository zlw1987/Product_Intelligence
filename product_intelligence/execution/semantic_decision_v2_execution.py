"""Semantic V2 live execution wiring (S2-C).

Wires the FINAL Semantic V2 contract into the comparable-research
execution flow for V2-eligible candidates (the frozen S2-A
``DETERMINISTIC_UNCERTAIN`` states: U1 / U2 / U3 / U4 / U5).

S2-C boundary (binding):

* MAY: execute V2 semantic evaluation; persist ``SemanticDecisionRecordV2``
  (ALL outcomes: MATCH / NO_MATCH / UNCERTAIN / RUNTIME_FAILURE, with or
  without fallback); expose the result internally to later phases (the
  ledger + replay are the interface).
* MUST NOT: add V2 results to canonical comparable price buckets; modify
  4A Machine Price; create new AI-Assisted Comparable pricing output;
  modify Reviewed Price; make V2 results alter the public price summary;
  change current UI authority presentation; create V2 human-review
  candidates. Before Qualification V3, V2 output is evidence/provenance
  awaiting model qualification (``V2_AUTHORITY_QUALIFIED`` is False and
  no authority code path reads a V2 record).

The V1 live path is UNCHANGED: ``evaluate_semantic_matches`` (FU3B) keeps
its frozen eligibility predicate, its evidence writes, and its
``AiAssistedMatchResult`` / review-candidate creation. For the
V1-eligible overlap (U1 / U2 / U3 with a usable title), the live path
now runs BOTH the unchanged V1 evaluation (which may create a review
candidate on V1 MATCH) and the NEW V2 evaluation (which only persists a
ledger record). V2 additionally reaches U4 (no-MPN usable title) and U5
(bounded near-miss MPN) — the candidates the frozen V1 predicate never
evaluates (the motivating Micron-style explicit near miss).

Context provenance in the live path: the only customer-retrieval-relation
source wired into production is the 4D-D alias-expanded paid search. When
a run's paid search used the ESTABLISHED alias-expanded query, the
search-batch candidates carry ``CUSTOMER_RETRIEVAL_RELATION`` (retrieval
hint only — it confers zero identity authority and is labeled as such in
the recorded V2 input); all other candidates carry no provenance. No
reviewed manufacturer provenance source is wired into the live path, so
``MANUFACTURER_RELATION_AUTHORITY`` / ``MANUFACTURER_PRODUCT_CONTEXT``
appear in V2 records only when a future reviewed source supplies them.

Product evidence in the live path: the SAFE builder
(``build_v2_product_evidence_profile``) with ZERO matched facts — the
current main-flow deterministic extraction proves no exact bounded
identity-dimension equality for listing candidates (documented
limitation; no fabricated facts; candidates remain at most LIMITED /
WEAK under the frozen S2-A bar).

Candidate observation evidence in the live path (S2-C-FU1): the bounded
evidence builders read ONLY the page-published structured fields the 3A
extractor actually carries (brand, the commercial fields). The published
title is RAW observation text — no title token is parsed into a
structured fact. The sales-unit / packaging channel is the explicit
UNAVAILABLE state (the extractor publishes no packaging field; nothing is
inferred from price).

Reviewed target context in the live path (S2-C-FU1): when the run's 4D-D
alias acquisition is ESTABLISHED, its re-verified reviewed fields
(manufacturer, verified category, exact source-published base MPN,
customer-retrieval relation, bounded fetch provenance) are carried in
section A of every recorded V2 input as STRUCTURED/REVIEWED target-side
observation evidence — zero identity authority (the relation kind is
bounded to customer retrieval), never a candidate-side evidence source,
and it grounds no authority fact. Non-ESTABLISHED acquisitions carry none
(explicit absence).

Execution evidence: V2 writes no ``ExecutionEvidenceRecord`` rows and
adds no new ``ExecutionDetailCode`` vocabulary. The semantic-decision
LEDGER record (per-attempt bounded provenance, failure class, fallback
reason, evaluation instants) is the S2-B-designed audit surface for
semantic calls.
"""

from __future__ import annotations

import hashlib
import logging
from dataclasses import dataclass
from datetime import timezone
from typing import TYPE_CHECKING, Mapping

from product_intelligence.domain import ResearchRequest
from product_intelligence.research import (
    AttemptOutcome,
    AttemptRole,
    ContextProvenance,
    IdentityStateAssessmentV2,
    ListingIdentityAssessment,
    ProductEvidenceProfileV2,
    ReviewedTargetContextV2,
    SemanticDecisionAttempt,
    SemanticEvaluationStateV2,
    SemanticEvaluationV2,
    SemanticFallbackReason,
    SemanticFailureClass,
    SemanticMatchCaseV2,
    TargetIdentifierRelationKindV2,
    build_semantic_match_case_v2,
    build_v2_product_evidence_profile,
    derive_authority_tier,
    derive_identity_state_v2,
    is_v2_semantic_eligible,
)
from product_intelligence.research.micron_packaging_alias import (
    MicronAliasEligibilityResult,
    MicronAliasEligibilityStatus,
)
from product_intelligence.research.semantic_decision_v2 import (
    SemanticDecisionRecordV2,
)
from product_intelligence.runs.models import ResearchRun
from product_intelligence.execution.semantic_decision_persistence import (
    persist_semantic_decision,
)
from product_intelligence.semantic.runtime_v2 import (
    SemanticRuntimeResultV2,
    SemanticRuntimeV2,
    get_default_runtime_v2,
)

logger = logging.getLogger(__name__)

if TYPE_CHECKING:
    from collections.abc import Sequence

__all__ = [
    "SemanticDecisionV2Outcome",
    "build_semantic_decision_records_v2",
    "evaluate_semantic_matches_v2",
    "persist_semantic_decision_records_v2",
    "reviewed_target_context_from_alias_result",
]


# ---------------------------------------------------------------------------
# Reviewed target context from the 4D-D alias acquisition (S2-C-FU1)
# ---------------------------------------------------------------------------


def reviewed_target_context_from_alias_result(
    alias_result: MicronAliasEligibilityResult,
) -> ReviewedTargetContextV2 | None:
    """The reviewed manufacturer TARGET context carried by a 4D-D alias
    acquisition (S2-C-FU1).

    Returns the bounded ``ReviewedTargetContextV2`` when the acquisition
    is ESTABLISHED — the reviewed v1 policy's manufacturer / verified
    category, the exact source-published base MPN, the CUSTOMER-DEFINED
    relation (retrieval only, zero identity authority), and the bounded
    fetch provenance. Every value is the result's own re-verified field:
    nothing is inferred. A non-ESTABLISHED result carries none of the
    authority fields and returns explicit None (absent, not guessed).

    An ESTABLISHED result missing any reviewed field is a data-integrity
    failure and fails closed (``ValueError``).
    """
    if not isinstance(alias_result, MicronAliasEligibilityResult):
        raise TypeError(
            "alias_result must be MicronAliasEligibilityResult, got "
            f"{type(alias_result).__name__}"
        )
    if alias_result.status is not MicronAliasEligibilityStatus.ESTABLISHED:
        return None
    relation = alias_result.alias_relation
    required: dict[str, object] = {
        "manufacturer": alias_result.manufacturer,
        "category": alias_result.category,
        "matched_base_mpn": alias_result.matched_base_mpn,
        "alias_relation": relation,
        "source_name": alias_result.source_name,
        "requested_source_url": alias_result.requested_source_url,
        "retrieved_at": alias_result.retrieved_at,
        "body_sha256": alias_result.body_sha256,
    }
    missing = sorted(name for name, value in required.items() if value is None)
    if missing:
        raise ValueError(
            "an ESTABLISHED 4D-D result is missing a reviewed field "
            f"({', '.join(missing)}); the target context cannot be "
            "constructed (fail closed)"
        )
    instant = (
        alias_result.retrieved_at.astimezone(timezone.utc)
        .isoformat()
        .replace("+00:00", "Z")
    )
    return ReviewedTargetContextV2(
        manufacturer=alias_result.manufacturer,
        category=alias_result.category,
        matched_base_part_number=alias_result.matched_base_mpn,
        relation_kind=TargetIdentifierRelationKindV2.CUSTOMER_RETRIEVAL_ALIAS,
        relation_family_part_numbers=tuple(relation.aliases),
        source_name=alias_result.source_name,
        source_url=alias_result.requested_source_url,
        retrieved_at=instant,
        evidence_body_sha256=alias_result.body_sha256,
    )


# ---------------------------------------------------------------------------
# One in-memory V2 evaluation outcome (held until the atomic publication)
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class SemanticDecisionV2Outcome:
    """One V2 semantic evaluation outcome for one V2-eligible candidate.

    Carries the deterministic assessment, the frozen S2-A derived context,
    the authority-side product evidence (safe builder output), the
    recorded context provenance, the EXACT V2 input case, and the bounded
    V2 runtime result (accepted strict structured response, or the
    bounded final failure classification). This is an in-memory
    evidence/provenance container: it grants no authority and is not
    persisted as-is (the persistence record is built at publication).
    """

    assessment: ListingIdentityAssessment
    context: IdentityStateAssessmentV2
    product_evidence: ProductEvidenceProfileV2
    context_provenances: frozenset[ContextProvenance]
    case: SemanticMatchCaseV2
    result: SemanticRuntimeResultV2

    def __post_init__(self) -> None:
        if not isinstance(self.assessment, ListingIdentityAssessment):
            raise TypeError(
                "assessment must be ListingIdentityAssessment, "
                f"got {type(self.assessment).__name__}"
            )
        if not isinstance(self.context, IdentityStateAssessmentV2):
            raise TypeError(
                "context must be IdentityStateAssessmentV2, "
                f"got {type(self.context).__name__}"
            )
        if not isinstance(self.product_evidence, ProductEvidenceProfileV2):
            raise TypeError(
                "product_evidence must be ProductEvidenceProfileV2, "
                f"got {type(self.product_evidence).__name__}"
            )
        if not isinstance(self.context_provenances, frozenset):
            raise TypeError(
                "context_provenances must be a frozenset, "
                f"got {type(self.context_provenances).__name__}"
            )
        if not isinstance(self.case, SemanticMatchCaseV2):
            raise TypeError(
                f"case must be SemanticMatchCaseV2, "
                f"got {type(self.case).__name__}"
            )
        if not isinstance(self.result, SemanticRuntimeResultV2):
            raise TypeError(
                "result must be SemanticRuntimeResultV2, "
                f"got {type(self.result).__name__}"
            )
        # The outcome binds to one candidate: the case's recorded input
        # must agree with the assessment's frozen observation.
        if self.case.candidate_source_url != (
            self.assessment.normalized_listing.observation.source_url
        ):
            raise ValueError(
                "the V2 case does not bind to the outcome's assessment; "
                "an outcome cannot pair a foreign case with an assessment"
            )


# ---------------------------------------------------------------------------
# V2 case id (the same stable scheme the V1 integration uses)
# ---------------------------------------------------------------------------


def _v2_candidate_case_id(
    assessment: ListingIdentityAssessment, index: int
) -> str:
    url = assessment.normalized_listing.observation.source_url
    url_hash = hashlib.sha256(url.encode()).hexdigest()[:8]
    return f"candidate-{url_hash}-{index}"


# ---------------------------------------------------------------------------
# V2 semantic evaluation (outside the publication transaction)
# ---------------------------------------------------------------------------


def evaluate_semantic_matches_v2(
    request: ResearchRequest,
    assessments: "Sequence[ListingIdentityAssessment]",
    *,
    context_provenances_by_assessment: Mapping[
        ListingIdentityAssessment, frozenset[ContextProvenance]
    ],
    reviewed_target_context: ReviewedTargetContextV2 | None,
    runtime_v2: SemanticRuntimeV2 | None = None,
) -> tuple[SemanticDecisionV2Outcome, ...]:
    """Execute the FINAL V2 semantic evaluation for every V2-eligible
    candidate (the frozen S2-A ``DETERMINISTIC_UNCERTAIN`` states).

    Rules:

    * Eligibility is the NEW explicit V2 predicate over the frozen S2-A
      derived state (``is_v2_semantic_eligible``): DETERMINISTIC_UNCERTAIN
      only — VERIFIED / CONFLICT / UNEVALUABLE are never evaluated. The
      V1 predicate is not consulted and is unchanged.
    * Every V2-eligible candidate is evaluated (no usable-title gate —
      the V2 input contract records absent candidate facts explicitly);
      the V2 runtime is constructed lazily on first need (zero
      V2-eligible candidates -> zero runtime construction -> zero
      transport calls).
    * Each candidate gets exactly one V2 evaluation: one primary call on
      the V2 pinned route; a fallback call ONLY for an execution failure
      named in the frozen allowlist (a valid primary response — MATCH /
      NO_MATCH / UNCERTAIN at any confidence — is final).
    * The authority-side product evidence is built by the SAFE builder
      with ZERO matched facts (the documented main-flow limitation); the
      model's matched_attributes never enter it.
    * The candidate observation evidence is built by the bounded
      S2-C-FU1 builders over the frozen observation: published
      structured fields only, the title as RAW observation text, and the
      explicit UNAVAILABLE sales-unit / packaging channel (nothing
      inferred from price or any other commercial fact).
    * ``reviewed_target_context`` is explicit: the reviewed manufacturer
      TARGET context the execution flow carries for this request (today:
      the ESTABLISHED 4D-D alias acquisition), or None when it carries
      none. It is recorded in section A of every case (target-side only;
      zero identity authority; it never grounds candidate-side authority
      facts).
    * ``context_provenances_by_assessment`` supplies the per-candidate
      bounded context provenance (absent entry -> no provenance).
    * Programming exceptions from the runtime propagate (a V2 defect
      terminalizes the run through the existing catastrophic boundary;
      it is never converted into a semantic outcome).

    Returns one ``SemanticDecisionV2Outcome`` per V2-eligible candidate,
    in assessment order.
    """
    if not isinstance(request, ResearchRequest):
        raise TypeError(
            "request must be ResearchRequest, "
            f"got {type(request).__name__}"
        )
    if not isinstance(context_provenances_by_assessment, Mapping):
        raise TypeError(
            "context_provenances_by_assessment must be a mapping of "
            "assessment -> frozenset[ContextProvenance]"
        )
    if reviewed_target_context is not None and not isinstance(
        reviewed_target_context, ReviewedTargetContextV2
    ):
        raise TypeError(
            "reviewed_target_context must be ReviewedTargetContextV2 or "
            f"None (explicit absence), got "
            f"{type(reviewed_target_context).__name__}"
        )

    outcomes: list[SemanticDecisionV2Outcome] = []
    runtime = runtime_v2

    for idx, assessment in enumerate(assessments):
        if not is_v2_semantic_eligible(assessment):
            continue
        if runtime is None:
            runtime = get_default_runtime_v2()

        context = derive_identity_state_v2(assessment)
        provenances = context_provenances_by_assessment.get(
            assessment, frozenset()
        )
        if not isinstance(provenances, frozenset):
            raise TypeError(
                "context_provenances_by_assessment values must be "
                "frozenset[ContextProvenance]"
            )
        observation = assessment.normalized_listing.observation
        product_evidence = build_v2_product_evidence_profile(
            observation=observation,
            context_provenances=provenances,
            matched_facts=frozenset(),
        )
        case = build_semantic_match_case_v2(
            case_id=_v2_candidate_case_id(assessment, idx),
            request=request,
            assessment=assessment,
            context=context,
            product_evidence=product_evidence,
            context_provenances=provenances,
            reviewed_target_context=reviewed_target_context,
        )
        result = runtime.evaluate(case)
        outcomes.append(
            SemanticDecisionV2Outcome(
                assessment=assessment,
                context=context,
                product_evidence=product_evidence,
                context_provenances=provenances,
                case=case,
                result=result,
            )
        )

    return tuple(outcomes)


# ---------------------------------------------------------------------------
# Record construction (pure; at publication, with the final indices)
# ---------------------------------------------------------------------------


def _evaluation_from_result(
    result: SemanticRuntimeResultV2,
) -> SemanticEvaluationV2:
    """The S2-A evaluation input for one V2 runtime result.

    An accepted strict structured response is the exact historical
    evaluation (decision / confidence / structured conflict classes —
    the reason code and attribute lists are recorded alongside but are
    not matrix inputs). A final failure is the explicit runtime-failure
    state — NEVER interpreted as NO_MATCH or anything evidence-shaped.
    """
    if result.response is not None:
        return SemanticEvaluationV2.evaluated(
            result.response.decision,
            result.response.confidence,
            result.response.conflict_classes,
        )
    return SemanticEvaluationV2.runtime_failure()


def _attempts_from_result(
    result: SemanticRuntimeResultV2,
) -> tuple[SemanticDecisionAttempt, ...]:
    """The bounded recorded attempts (call order; the V2 route pin is
    re-validated by the record constructor)."""
    attempts: list[SemanticDecisionAttempt] = []
    for number, attempt in enumerate(result.attempts, start=1):
        role = (
            AttemptRole.PRIMARY if number == 1 else AttemptRole.FALLBACK
        )
        attempts.append(
            SemanticDecisionAttempt(
                role=role,
                attempt_number=number,
                provider=attempt.provider,
                model=attempt.model,
                outcome=AttemptOutcome(attempt.status.value),
            )
        )
    return tuple(attempts)


def build_semantic_decision_records_v2(
    run: ResearchRun,
    published_assessments: tuple[ListingIdentityAssessment, ...],
    outcomes: tuple[SemanticDecisionV2Outcome, ...],
) -> tuple[SemanticDecisionRecordV2, ...]:
    """Build one ``SemanticDecisionRecordV2`` per V2 outcome, bound to
    the run's PUBLISHED assessment tuple (the stable
    ``assessment_index`` the ledger and the replay binding use).

    The derived audit snapshots (product evidence quality, relationship
    authority, authority tier, fired rules) are computed under the bound
    authority contract (S2-A as frozen through S2-A-FU2) with NO human
    overlay — the overlay is a later workflow concern, not part of the
    evaluation. A V2 MATCH at any confidence never raises a tier beyond
    what the frozen gates allow, and the record is a PERSISTENCE
    artifact: nothing here grants authority.

    Fails closed (``ValueError``) when an outcome's assessment is absent
    from the published tuple (a data-integrity failure — the same
    fail-closed contract the review-candidate publication uses).
    """
    if not isinstance(run, ResearchRun):
        raise TypeError(
            f"run must be a ResearchRun, got {type(run).__name__}"
        )
    if not isinstance(published_assessments, tuple):
        raise TypeError("published_assessments must be the ordered tuple")

    index_by_assessment: dict = {}
    for idx, assessment in enumerate(published_assessments):
        index_by_assessment[assessment] = idx

    records: list[SemanticDecisionRecordV2] = []
    for outcome in outcomes:
        idx = index_by_assessment.get(outcome.assessment)
        if idx is None:
            raise ValueError(
                f"SemanticDecisionV2Outcome assessment not found in the "
                f"published assessments tuple for run {run.id}. This "
                "indicates a data integrity failure."
            )
        result = outcome.result
        evaluation = _evaluation_from_result(result)
        tier_decision = derive_authority_tier(
            outcome.context,
            evaluation,
            outcome.context_provenances,
            outcome.product_evidence,
        )
        if result.response is not None:
            response = result.response
            evaluation_state = SemanticEvaluationStateV2.EVALUATED
            decision = response.decision
            confidence = response.confidence
            reason_code = response.reason_code
            conflict_classes = response.conflict_classes
            matched_attributes = response.matched_attributes
            conflicting_attributes = response.conflicting_attributes
            missing_critical_attributes = (
                response.missing_critical_attributes
            )
            error_type_value = None
        else:
            evaluation_state = SemanticEvaluationStateV2.RUNTIME_FAILURE
            decision = None
            confidence = None
            reason_code = None
            conflict_classes = frozenset()
            matched_attributes = ()
            conflicting_attributes = ()
            missing_critical_attributes = ()
            error_type_value = (
                SemanticFailureClass(result.error_type.value)
            )
        records.append(
            SemanticDecisionRecordV2.build(
                run_id=str(run.id),
                assessment_index=idx,
                source_url=outcome.case.candidate_source_url,
                case=outcome.case,
                evaluation_state=evaluation_state,
                decision=decision,
                confidence=confidence,
                reason_code=reason_code,
                conflict_classes=conflict_classes,
                matched_attributes=matched_attributes,
                conflicting_attributes=conflicting_attributes,
                missing_critical_attributes=missing_critical_attributes,
                attempts=_attempts_from_result(result),
                fallback_used=result.fallback_used,
                fallback_reason=(
                    SemanticFallbackReason(result.fallback_reason.value)
                    if result.fallback_reason is not None
                    else None
                ),
                error_type=error_type_value,
                actual_provider=result.actual_provider,
                actual_model=result.actual_model,
                evaluation_started_at=result.evaluation_started_at,
                evaluation_finished_at=result.evaluation_finished_at,
                product_evidence_quality=tier_decision.product_evidence_quality,
                relationship_authority=(
                    tier_decision.relationship_authority
                ),
                authority_tier=tier_decision.tier,
                fired_rules=tier_decision.fired_rules,
            )
        )
    return tuple(records)


# ---------------------------------------------------------------------------
# Ledger persistence (the single service write path; inside the atomic
# publication block)
# ---------------------------------------------------------------------------


def persist_semantic_decision_records_v2(
    run: ResearchRun,
    records: tuple[SemanticDecisionRecordV2, ...],
) -> int:
    """Persist every V2 record through the S2-B persistence service
    (append-only; never overwrites; the service owns no authority logic).

    Returns the number of records persisted. A second persist for the
    same (run, assessment_index) fails closed
    (``SemanticDecisionAlreadyRecordedError``).
    """
    for record in records:
        persist_semantic_decision(run, record)
    return len(records)
