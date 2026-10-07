"""Pure replay / reconstruction for persisted semantic-decision artifacts
(S2-B).

``replay_semantic_decision`` is the ZERO-LIVE reconstruction path: from a
persisted (decoded) ``SemanticDecisionRecord`` it reconstructs, under the
EXACT contract version the artifact was bound to,

* the historical semantic evaluation (``SemanticEvaluationV2``) — the exact
  decision / confidence / conflict classes the evaluation produced, or the
  explicit RUNTIME_FAILURE / NOT_EVALUATED state;
* the S2-A authority inputs — the deterministic V2 context
  (``IdentityStateAssessmentV2``), the bounded product-evidence profile,
  and the context provenances as present at evaluation time; and
* the frozen S2-A authority derivation under the bound authority contract
  version — and PROVES the stored derived audit snapshots (relationship
  requirement, product evidence quality, relationship authority, authority
  tier, fired rules) agree with re-derivation.

Contract-version discipline (the anti-reinterpretation rule)
------------------------------------------------------------

The artifact is bound to the semantic / prompt / input / output / authority
contract versions under which it was produced. This module knows exactly
one safe-replay envelope (``SUPPORTED_CONTRACT_BINDINGS``): the frozen V1
semantic contract (prompt v1.1) under the S2-A authority contract as frozen
through S2-A-FU2. A record bound to any other version — including a FUTURE
newer version this code does not know — is refused explicitly
(``SemanticDecisionReplayError``). An old persisted semantic decision is
NEVER silently reinterpreted under a newer contract, and the historical
recorded values are never substituted by current module constants: the
binding gate reads the RECORD's versions, and the re-derivation agreement
check would fail if the frozen S2-A contract under this module had moved.

Zero live work
--------------

This module is pure: stdlib + the frozen research contracts only. It imports
no runtime, no transport, no network or file I/O, no Django, and reads no
clock. It performs zero live AI calls and zero provider/network calls by
construction (the recorded values are re-read and re-derived, never
re-requested). Boundary tests enforce the import discipline; replay tests
arm fail-fast sentinels on the live runtime and network surfaces.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Final

from product_intelligence.research import (
    AuthorityDecisionV2,
    ContextProvenance,
    IdentityStateAssessmentV2,
    ProductEvidenceProfileV2,
    ProductEvidenceQuality,
    RelationshipAuthority,
    RelationshipRequirement,
    SemanticEvaluationStateV2,
    SemanticEvaluationV2,
    derive_authority_tier,
    derive_product_evidence_quality,
    derive_relationship_authority,
    substate_relationship_requirement,
)
from product_intelligence.research.semantic_decision_record import (
    AUTHORITY_CONTRACT_VERSION,
    PROMPT_VERSION_V1,
    SEMANTIC_CONTRACT_VERSION,
    SEMANTIC_INPUT_SCHEMA_VERSION,
    SEMANTIC_OUTPUT_SCHEMA_VERSION,
    SemanticDecisionRecord,
    SemanticPromptInput,
)

__all__ = [
    "SUPPORTED_CONTRACT_BINDINGS",
    "SemanticDecisionReplay",
    "SemanticDecisionReplayError",
    "reconstruct_identity_context",
    "reconstruct_semantic_evaluation",
    "replay_semantic_decision",
]


class SemanticDecisionReplayError(ValueError):
    """The persisted artifact cannot be safely replayed.

    Bounded causes: an unknown / unsupported contract binding (including
    any future version this code does not know), recorded inputs that
    violate the bound authority contract, or stored derived audit snapshots
    that do not agree with re-derivation (tamper / version drift).

    Messages name the failing check, never raw payload content.
    """


#: The exact (semantic contract, prompt, input schema, output schema,
#: authority contract) bindings this code can safely replay. One entry:
#: the frozen V1 semantic contract (prompt v1.1) under the S2-A authority
#: contract as frozen through S2-A-FU2. A future binding is a future
#: decision — never an implicit reinterpretation.
SUPPORTED_CONTRACT_BINDINGS: Final[
    tuple[tuple[str, str, int, int, str], ...]
] = (
    (
        SEMANTIC_CONTRACT_VERSION,
        PROMPT_VERSION_V1,
        SEMANTIC_INPUT_SCHEMA_VERSION,
        SEMANTIC_OUTPUT_SCHEMA_VERSION,
        AUTHORITY_CONTRACT_VERSION,
    ),
)


@dataclass(frozen=True)
class SemanticDecisionReplay:
    """The verified reconstruction of one persisted semantic decision.

    Carries the original record (for provenance), the reconstructed S2-A
    authority inputs, the re-derived authority decision (proved to agree
    with the stored derived audit snapshots), and the recorded prompt
    input (from which the exact historical prompt is deterministically
    reconstructable without any live call).
    """

    record: SemanticDecisionRecord
    identity_context: IdentityStateAssessmentV2
    semantic_evaluation: SemanticEvaluationV2
    context_provenances: frozenset[ContextProvenance]
    product_evidence: ProductEvidenceProfileV2
    product_evidence_quality: ProductEvidenceQuality
    relationship_requirement: RelationshipRequirement
    relationship_authority: RelationshipAuthority
    authority_decision: AuthorityDecisionV2
    prompt_input: SemanticPromptInput
    contract_binding: tuple[str, str, int, int, str]


def reconstruct_identity_context(
    record: SemanticDecisionRecord,
) -> IdentityStateAssessmentV2:
    """Reconstruct the deterministic V2 context from the persisted record.

    The frozen V2 constructor re-validates the recorded state / sub-state /
    signal combination (fail closed): a context that is not a legitimate
    S2-A context cannot be reconstructed.
    """
    return IdentityStateAssessmentV2(
        state=record.identity_state,
        substate=record.substate,
        relationship_signals=record.relationship_signals,
        normalized_requested_part_number=record.normalized_requested_part_number,
        normalized_candidate_part_number=record.normalized_candidate_part_number,
    )


def reconstruct_semantic_evaluation(
    record: SemanticDecisionRecord,
) -> SemanticEvaluationV2:
    """Reconstruct the exact historical semantic evaluation.

    * ``EVALUATED`` -> the recorded decision / confidence / conflict
      classes (the exact evaluation used at the time);
    * ``RUNTIME_FAILURE`` -> the explicit runtime-failure state (NEVER
      interpreted as NO_MATCH or anything evidence-shaped);
    * ``NOT_EVALUATED`` -> the explicit not-evaluated state (the
      deterministic state governs; this is not an AI failure).
    """
    if record.evaluation_state is SemanticEvaluationStateV2.EVALUATED:
        if record.decision is None or record.confidence is None:
            raise SemanticDecisionReplayError(
                "an EVALUATED record must carry the recorded decision and "
                "confidence; the artifact is corrupt"
            )
        return SemanticEvaluationV2.evaluated(
            record.decision, record.confidence, record.conflict_classes
        )
    if record.evaluation_state is SemanticEvaluationStateV2.RUNTIME_FAILURE:
        return SemanticEvaluationV2.runtime_failure()
    if record.evaluation_state is SemanticEvaluationStateV2.NOT_EVALUATED:
        return SemanticEvaluationV2.not_evaluated()
    raise SemanticDecisionReplayError(
        "the record carries an unknown evaluation state; nothing to "
        "reconstruct"
    )


def _contract_binding(record: SemanticDecisionRecord) -> tuple[str, str, int, int, str]:
    return (
        record.semantic_contract_version,
        record.prompt_version,
        record.input_schema_version,
        record.output_schema_version,
        record.authority_contract_version,
    )


def replay_semantic_decision(
    record: SemanticDecisionRecord,
) -> SemanticDecisionReplay:
    """Pure zero-live replay of one persisted semantic decision.

    Steps (each fails closed with ``SemanticDecisionReplayError``):

    1. **Contract-binding gate.** The record's exact
       (semantic contract, prompt, input schema, output schema, authority
       contract) binding must be one this code can safely replay
       (``SUPPORTED_CONTRACT_BINDINGS``). Unknown or future versions are
       refused explicitly — never silently reinterpreted, and never
       replayed "as if" the current module constants applied.
    2. **Reconstruction.** The historical evaluation, the V2 context, the
       product-evidence profile, and the context provenances are
       reconstructed from the recorded values (constructor-validated).
    3. **Re-derivation under the bound authority contract.** The S2-A
       derivation is re-run on the reconstructed inputs: relationship
       requirement, product evidence quality, relationship authority, and
       the authority decision (tier + fired rules, no human overlay — the
       overlay is a later workflow concern, not part of the evaluation).
    4. **Derived-agreement proof.** Every stored derived audit snapshot
       must EXACTLY agree with the re-derivation. Agreement proves the
       artifact was produced under the bound contract and is untampered;
       disagreement (or a derivation that fails closed on the recorded
       inputs) is a ``SemanticDecisionReplayError``.

    Performs zero live AI calls and zero provider/network calls: the
    recorded values are re-read and re-derived, never re-requested.
    """
    binding = _contract_binding(record)
    if binding not in SUPPORTED_CONTRACT_BINDINGS:
        raise SemanticDecisionReplayError(
            "unsupported contract binding "
            f"(semantic contract {binding[0]!r}, prompt {binding[1]!r}, "
            f"input schema {binding[2]}, output schema {binding[3]}, "
            f"authority contract {binding[4]!r}); this code cannot safely "
            "replay it and refuses to reinterpret a historical decision "
            "under a contract it does not know"
        )

    try:
        identity_context = reconstruct_identity_context(record)
        semantic_evaluation = reconstruct_semantic_evaluation(record)
        product_evidence = record.product_evidence
        context_provenances = record.context_provenances

        requirement = substate_relationship_requirement(
            identity_context.substate,
            identity_context.primary_relationship_signal,
        )
        quality = derive_product_evidence_quality(
            product_evidence, context_provenances
        )
        relationship_authority = derive_relationship_authority(
            identity_context, context_provenances
        )
        authority_decision = derive_authority_tier(
            identity_context,
            semantic_evaluation,
            context_provenances,
            product_evidence,
        )
    except SemanticDecisionReplayError:
        raise
    except (TypeError, ValueError):
        raise SemanticDecisionReplayError(
            "the recorded inputs violate the bound authority contract; "
            "the artifact is corrupt and cannot be replayed"
        ) from None

    # -- derived-agreement proof (tamper / version-drift detection) ---------
    mismatches: list[str] = []
    if requirement is not record.relationship_requirement:
        mismatches.append("relationship_requirement")
    if quality is not record.product_evidence_quality:
        mismatches.append("product_evidence_quality")
    if relationship_authority is not record.relationship_authority:
        mismatches.append("relationship_authority")
    if authority_decision.tier is not record.authority_tier:
        mismatches.append("authority_tier")
    if authority_decision.fired_rules != record.fired_rules:
        mismatches.append("fired_rules")
    if mismatches:
        raise SemanticDecisionReplayError(
            "stored derived audit snapshots do not agree with "
            f"re-derivation under the bound authority contract: "
            f"{', '.join(mismatches)}; the artifact is tampered or was "
            "produced under a contract this code cannot verify"
        )

    return SemanticDecisionReplay(
        record=record,
        identity_context=identity_context,
        semantic_evaluation=semantic_evaluation,
        context_provenances=context_provenances,
        product_evidence=product_evidence,
        product_evidence_quality=quality,
        relationship_requirement=requirement,
        relationship_authority=relationship_authority,
        authority_decision=authority_decision,
        prompt_input=record.prompt_input(),
        contract_binding=binding,
    )
