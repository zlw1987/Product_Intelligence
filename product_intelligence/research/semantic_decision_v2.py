"""The Semantic V2 contract adapter (S2-C).

The FIRST registered adapter for the final Semantic V2 contract. It owns,
and ONLY it owns:

* the V2 contract identity: semantic contract ``V2`` (the final S2-C
  semantic contract), prompt ``2.0``, recorded V2 input schema version 1,
  recorded V2 output schema version 1, authority contract
  ``SEMANTIC_AUTHORITY_V2_S2A_FU2`` — the exact tuple
  ``V2_CONTRACT_BINDING``; anything else is outside this adapter and
  fails closed (never silently reinterpreted);
* the V2 pinned runtime route: ``amax`` / ``qwen3.8-27b`` primary and
  ``vllm-262k`` / ``Qwen3.6-27B-262K`` fallback — the currently frozen
  qualified route identities, carried as V2 CONTRACT data (a V2
  contract rule, not a persistence-envelope invariant; drift-pinned to
  the V2 runtime), so a future qualification may move the V2 route
  without touching the V1 contract or the envelope;
* the explicit ``V2_AUTHORITY_QUALIFIED`` marker (False in S2-C: the V2
  route is NOT qualified for the new contract; Qualification V3 happens
  after S2-C; drift-pinned to the V2 runtime marker);
* the version-neutral transport-provenance value objects are REUSED from
  the first registered adapter module (``AttemptRole`` /
  ``AttemptOutcome`` / ``SemanticFailureClass`` / ``SemanticFallbackReason``
  / ``SemanticDecisionAttempt`` — they carry no route and no contract
  assumption); the V2 route pin and the V2 family-consistency rules are
  V2-adapter-owned;
* the V2 typed record (``SemanticDecisionRecordV2``) with the V2 exact
  binding check, the V2 route pin, the frozen V2 input contract
  validation (the recorded ``SemanticMatchCaseV2`` is itself the
  deterministic S2-A context, the context provenance, and the
  authority-side product evidence), the strict structured V2 output
  coherence (the frozen reason-code rules), the evaluation/execution
  coherence rules, and the self-verifying section digests;
* the strict V2 payload codec (the exact V2 section shapes; fail closed);
* the V2 pure zero-live replay (reconstruction + S2-A re-derivation +
  the derived-agreement proof);
* the V2 run-binding check (the recorded V2 input's target MPN /
  description must equal the run's canonical request);
* the registered instance ``SEMANTIC_V2_ADAPTER`` (envelope schema 1,
  semantic contract V2, supported bindings = (V2_CONTRACT_BINDING,),
  record type = SemanticDecisionRecordV2).

The universal parts — the envelope framing (payload schema version +
binding + contract dispatch key), the adapter registry and dispatch, the
row-level tamper anchor, the persistence service — live in
``semantic_decision_record.py`` / ``semantic_decision_codec.py`` /
``semantic_decision_replay.py`` and the runs/execution layers, and they
own no V2 provider/model/prompt assumption.

This module is pure research-layer contract: stdlib + the research
package's public export surface + the final V2 contract module
(``semantic_v2``) only; no Django, no I/O, no clock, no float authority
data, no network, no production semantic-runtime import (the V2 runtime
vocabulary it names is mirrored, drift-pinned by tests).
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Final

from product_intelligence.research import (
    AttemptOutcome,
    AttemptRole,
    AuthorityDecisionV2,
    AuthorityRuleV2,
    AuthorityTier,
    CandidateProductEvidenceSource,
    ConflictClass,
    ConflictSubstateV2,
    ContextProvenance,
    IdentityRelationshipSignal,
    IdentityStateAssessmentV2,
    IdentityStateV2,
    ProductEvidenceDimension,
    ProductEvidenceFactV2,
    ProductEvidenceProfileV2,
    ProductEvidenceQuality,
    RelationshipAuthority,
    RelationshipRequirement,
    SemanticDecisionAttempt,
    SemanticEvaluationStateV2,
    SemanticEvaluationV2,
    SemanticFallbackReason,
    SemanticFailureClass,
    UncertainSubstateV2,
    UnevaluableSubstateV2,
    V2Confidence,
    V2SemanticDecision,
    VerifiedSubstateV2,
    derive_authority_tier,
    derive_product_evidence_quality,
    derive_relationship_authority,
    substate_relationship_requirement,
)
from product_intelligence.research.semantic_decision_record import (
    SemanticDecisionCodecError,
    SemanticDecisionContractAdapter,
    SemanticDecisionReplayError,
    _BINDING_KEYS,
    _binding_section,
    _check_keys,
    _dec_bool,
    _dec_int,
    _dec_list,
    _dec_mapping,
    _dec_optional_str,
    _dec_optional_str_enum,
    _dec_required,
    _dec_sorted_unique_str_list,
    _dec_str,
    _dec_str_enum,
    _dec_str_list,
    _validate_binding_fields,
    _validate_digest,
    _validate_str,
    _validate_timestamp,
    canonical_sha256,
)
from product_intelligence.research.semantic_v2 import (
    CandidateCommercialEvidenceV2,
    CandidateEvidenceSourceV2,
    CandidateObservationFactV2,
    CandidateProductEvidenceV2,
    CandidateSalesUnitEvidenceV2,
    PackagingEvidenceStateV2,
    ReviewedTargetContextV2,
    SalesUnitKindV2,
    SemanticAttributeDimensionV2,
    SemanticAttributeV2,
    SemanticMatchCaseV2,
    SemanticMatchResponseV2,
    SemanticReasonCodeV2,
    TargetEvidenceV2,
    TargetIdentifierRelationKindV2,
)

__all__ = [
    "AUTHORITY_CONTRACT_VERSION_V2",
    "FALLBACK_MODEL_V2",
    "FALLBACK_PROVIDER_V2",
    "PRIMARY_MODEL_V2",
    "PRIMARY_PROVIDER_V2",
    "PROMPT_VERSION_V2",
    "SEMANTIC_CONTRACT_VERSION_V2",
    "SEMANTIC_INPUT_SCHEMA_VERSION_V2",
    "SEMANTIC_OUTPUT_SCHEMA_VERSION_V2",
    "SEMANTIC_V2_ADAPTER",
    "SemanticDecisionReplayV2",
    "SemanticDecisionRecordV2",
    "SemanticV2ContractAdapter",
    "V2_CONTRACT_BINDING",
    "V2_AUTHORITY_QUALIFIED",
    "encode_v2_payload",
    "record_input_digest_v2",
    "record_output_digest_v2",
    "reconstruct_identity_context_v2",
    "reconstruct_semantic_evaluation_v2",
    "replay_v2_record",
]


# ---------------------------------------------------------------------------
# The V2 contract identity (owned by THIS adapter, not by the envelope)
# ---------------------------------------------------------------------------

SEMANTIC_CONTRACT_VERSION_V2: Final[str] = "V2"
"""The final Semantic V2 contract this adapter interprets: the S2-C
frozen V2 input/output contracts, prompt 2.0, the V2 pinned route
(identities of the currently frozen qualified route), fallback-on-
execution-failure-only, strict structured response. A payload bound to
any other semantic contract version is outside this adapter (the
universal dispatch refuses it when no adapter is registered for it; this
adapter additionally never interprets a non-V2 payload)."""

PROMPT_VERSION_V2: Final[str] = "2.0"
"""The exact final prompt version of the V2 semantic contract (mirrors
``semantic.contract_v2.SEMANTIC_PROMPT_VERSION_V2``; drift-pinned by
tests)."""

SEMANTIC_INPUT_SCHEMA_VERSION_V2: Final[int] = 1
"""Version of the V2 recorded input section (the exact
``SemanticMatchCaseV2`` the V2 prompt renderer consumes)."""

SEMANTIC_OUTPUT_SCHEMA_VERSION_V2: Final[int] = 1
"""Version of the V2 recorded output section (strict structured V2
response: decision / confidence / bounded reason code / structured
attributes / conflict classes)."""

AUTHORITY_CONTRACT_VERSION_V2: Final[str] = "SEMANTIC_AUTHORITY_V2_S2A_FU2"
"""The identity of the Semantic Authority Contract V2 AS FROZEN THROUGH
S2-A-FU2 — the exact contract under which the derived audit snapshots in
a V2 artifact are produced. The V2 replay re-derives under the current
frozen S2-A module and requires exact agreement with the stored
snapshots; a future authority contract version is explicitly refused
(never silently reinterpreted)."""

#: The EXACT contract binding this adapter interprets and replays:
#: (semantic contract, prompt, input schema, output schema, authority
#: contract). One entry. A future binding is a future adapter — never an
#: implicit reinterpretation of this one.
V2_CONTRACT_BINDING: Final[tuple[str, str, int, int, str]] = (
    SEMANTIC_CONTRACT_VERSION_V2,
    PROMPT_VERSION_V2,
    SEMANTIC_INPUT_SCHEMA_VERSION_V2,
    SEMANTIC_OUTPUT_SCHEMA_VERSION_V2,
    AUTHORITY_CONTRACT_VERSION_V2,
)

# The V2 pinned route — the currently frozen qualified route identities,
# carried as V2 contract data (mirrored; drift-pinned by tests against
# the V2 runtime). A V2-bound record's attempts followed this exact
# route — any other provider/model in a V2 record is a V2 contract
# violation and fails closed. This is a rule of the V2 semantic
# contract, NOT an invariant of the persistence envelope.
PRIMARY_PROVIDER_V2: Final[str] = "amax"
PRIMARY_MODEL_V2: Final[str] = "qwen3.8-27b"
FALLBACK_PROVIDER_V2: Final[str] = "vllm-262k"
FALLBACK_MODEL_V2: Final[str] = "Qwen3.6-27B-262K"

#: The explicit S2-C qualification-boundary marker (mirrored; drift-
#: pinned by tests against the V2 runtime): the V2 route is NOT
#: qualified for the new V2 contract. V2 outputs are evidence/provenance
#: awaiting Qualification V3; no production authority code path treats
#: a V2 MATCH/HIGH as pricing-authoritative.
V2_AUTHORITY_QUALIFIED: Final[bool] = False


# ---------------------------------------------------------------------------
# Family-consistency rules (V2-adapter-owned; the values mirror the
# version-neutral failure vocabulary)
# ---------------------------------------------------------------------------


#: Bounded failure families per attempt count (the V2 record's own
#: consistency rules, mirroring the V2 runtime's routing contract at
#: value level): a one-attempt failure is classified by the PRIMARY
#: family (or a local configuration error); a two-attempt failure is
#: classified by the FALLBACK family (or BOTH_UNAVAILABLE).
_V2_ONE_ATTEMPT_FAILURE_CLASSES: Final[frozenset[SemanticFailureClass]] = (
    frozenset(
        {
            SemanticFailureClass.CONFIG_INVALID,
            SemanticFailureClass.PROVIDER_NOT_CONFIGURED,
        }
        | {
            member
            for member in SemanticFailureClass
            if member.value.startswith("PRIMARY_")
        }
    )
)

_V2_TWO_ATTEMPT_FAILURE_CLASSES: Final[frozenset[SemanticFailureClass]] = (
    frozenset(
        {
            SemanticFailureClass.BOTH_UNAVAILABLE,
        }
        | {
            member
            for member in SemanticFailureClass
            if member.value.startswith("FALLBACK_")
        }
    )
)


# ---------------------------------------------------------------------------
# V2 section encodings (the exact V2 payload shapes)
# ---------------------------------------------------------------------------


def _v2_contract_section() -> dict[str, object]:
    """The V2 contract binding section (frozen; see module constants)."""
    return {
        "semantic_contract_version": SEMANTIC_CONTRACT_VERSION_V2,
        "prompt_version": PROMPT_VERSION_V2,
        "input_schema_version": SEMANTIC_INPUT_SCHEMA_VERSION_V2,
        "output_schema_version": SEMANTIC_OUTPUT_SCHEMA_VERSION_V2,
        "authority_contract_version": AUTHORITY_CONTRACT_VERSION_V2,
    }


def _v2_evaluation_section(
    evaluation_state: SemanticEvaluationStateV2,
    decision: V2SemanticDecision | None,
    confidence: V2Confidence | None,
    conflict_classes: frozenset[ConflictClass],
    reason_code: SemanticReasonCodeV2 | None,
    matched_attributes: tuple[SemanticAttributeV2, ...],
    conflicting_attributes: tuple[SemanticAttributeV2, ...],
    missing_critical_attributes: tuple[SemanticAttributeDimensionV2, ...],
) -> dict[str, object]:
    return {
        "evaluation_state": evaluation_state.value,
        "decision": decision.value if decision is not None else None,
        "confidence": confidence.value if confidence is not None else None,
        "reason_code": reason_code.value if reason_code is not None else None,
        "conflict_classes": sorted(
            conflict.value for conflict in conflict_classes
        ),
        "matched_attributes": [
            attribute.canonical() for attribute in matched_attributes
        ],
        "conflicting_attributes": [
            attribute.canonical() for attribute in conflicting_attributes
        ],
        "missing_critical_attributes": [
            dimension.value for dimension in missing_critical_attributes
        ],
    }


def _v2_execution_section(
    attempts: tuple[SemanticDecisionAttempt, ...],
    fallback_used: bool,
    fallback_reason: SemanticFallbackReason | None,
    error_type: SemanticFailureClass | None,
    actual_provider: str | None,
    actual_model: str | None,
    evaluation_started_at: str | None,
    evaluation_finished_at: str | None,
) -> dict[str, object]:
    return {
        "attempts": [attempt.canonical() for attempt in attempts],
        "fallback_used": fallback_used,
        "fallback_reason": (
            fallback_reason.value if fallback_reason is not None else None
        ),
        "error_type": error_type.value if error_type is not None else None,
        "actual_provider": actual_provider,
        "actual_model": actual_model,
        "evaluation_started_at": evaluation_started_at,
        "evaluation_finished_at": evaluation_finished_at,
    }


def _v2_derived_section(
    product_evidence_quality: ProductEvidenceQuality,
    relationship_authority: RelationshipAuthority,
    authority_tier: AuthorityTier,
    fired_rules: frozenset[AuthorityRuleV2],
) -> dict[str, object]:
    return {
        "product_evidence_quality": product_evidence_quality.value,
        "relationship_authority": relationship_authority.value,
        "authority_tier": authority_tier.value,
        "fired_rules": sorted(rule.value for rule in fired_rules),
    }


# ---------------------------------------------------------------------------
# The V2 typed record (the version-owned artifact of the V2 contract)
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class SemanticDecisionRecordV2:
    """One complete, immutable Semantic V2 decision / provenance artifact
    for one candidate assessment of one research run (S2-C).

    This is the V2 contract adapter's typed record — the SECOND
    registered semantic contract, NOT the universal persistence schema.
    The universal envelope (the runs row + the payload framing: envelope
    schema version, binding, contract identity, integrity anchor) is
    contract-agnostic; every version-specific rule of this record — the
    exact V2 contract binding, the V2 pinned route, the V2 section
    shapes, the V2 digest layout — is a rule of the V2 semantic contract
    owned by this adapter.

    Sections
    --------

    * **binding** — the universal persistence binding (run identity, the
      assessment's stable position in the run's ordered assessment
      tuple, the listing source URL);
    * **contract** — the EXACT V2 semantic / prompt / input / output /
      authority contract versions under which the evaluation happened
      and the derived snapshots were produced (the V2 adapter refuses
      any other binding);
    * **case** — the EXACT final V2 input (``SemanticMatchCaseV2``): the
      target, the candidate listing (price/package context as context
      only, never identity proof), the deterministic S2-A identity
      context (state / sub-state / primary signal / bounded signals /
      normalized keys / the frozen relationship-requirement snapshot),
      the context provenance classes as present (customer retrieval
      labeled retrieval-only), and the authority-side product evidence
      (deterministic/reviewed only — never model output);
    * **evaluation** — the recorded strict structured V2 output
      (evaluation state, decision, confidence, bounded reason code,
      structured conflict classes, bounded structured matched /
      conflicting attributes, bounded missing-critical dimensions);
    * **execution** — the recorded V2 runtime provenance (attempts in
      call order on the V2 pinned route, fallback use/reason, bounded
      failure class, actual provider/model, evaluation instants);
    * **derived** — the derived audit snapshots (product evidence
      quality, relationship authority, authority tier, fired rules)
      under the bound authority contract version; replay proves they
      agree with re-derivation;
    * **integrity** — self-verifying input/output section digests.

    The ledger records an entry-point candidate: under the bound
    authority contract, only ``DETERMINISTIC_UNCERTAIN`` contexts are
    semantic entry points (the V2 input contract enforces this), so any
    other context fails closed here.

    The record stores no float, reads no clock, performs no I/O, and
    grants no authority: it is a record of what happened, verifiable
    under the V2 contract binding.
    """

    # -- universal binding (envelope-level addressing) -------------------------
    run_id: str
    assessment_index: int
    source_url: str

    # -- V2 contract binding (adapter-owned identity) ---------------------------
    semantic_contract_version: str
    prompt_version: str
    input_schema_version: int
    output_schema_version: int
    authority_contract_version: str

    # -- exact recorded V2 input (case; the S2-A context + provenance +
    #    authority-side product evidence live INSIDE it) ------------------------
    case: SemanticMatchCaseV2

    # -- recorded strict structured V2 output -----------------------------------
    evaluation_state: SemanticEvaluationStateV2
    decision: V2SemanticDecision | None
    confidence: V2Confidence | None
    reason_code: SemanticReasonCodeV2 | None
    conflict_classes: frozenset[ConflictClass]
    matched_attributes: tuple[SemanticAttributeV2, ...]
    conflicting_attributes: tuple[SemanticAttributeV2, ...]
    missing_critical_attributes: tuple[SemanticAttributeDimensionV2, ...]

    # -- recorded V2 runtime provenance -------------------------------------------
    attempts: tuple[SemanticDecisionAttempt, ...]
    fallback_used: bool
    fallback_reason: SemanticFallbackReason | None
    error_type: SemanticFailureClass | None
    actual_provider: str | None
    actual_model: str | None
    evaluation_started_at: str | None
    evaluation_finished_at: str | None

    # -- derived audit snapshots (replay proves agreement) -------------------------
    product_evidence_quality: ProductEvidenceQuality
    relationship_authority: RelationshipAuthority
    authority_tier: AuthorityTier
    fired_rules: frozenset[AuthorityRuleV2]

    # -- integrity -------------------------------------------------------------------
    input_digest: str
    output_digest: str

    def __post_init__(self) -> None:
        self._validate_types()
        self._validate_binding()
        self._validate_contract_binding()
        self._validate_evaluation_and_execution()
        self._validate_derived_types()
        self._validate_digests()

    # -- type validation ------------------------------------------------------------

    def _validate_types(self) -> None:
        if not isinstance(self.case, SemanticMatchCaseV2):
            raise TypeError(
                "case must be SemanticMatchCaseV2, "
                f"got {type(self.case).__name__}"
            )
        if not isinstance(
            self.evaluation_state, SemanticEvaluationStateV2
        ):
            raise TypeError(
                "evaluation_state must be SemanticEvaluationStateV2, "
                f"got {type(self.evaluation_state).__name__}"
            )
        if (
            self.decision is not None
            and not isinstance(self.decision, V2SemanticDecision)
        ):
            raise TypeError(
                "decision must be V2SemanticDecision or None, "
                f"got {type(self.decision).__name__}"
            )
        if (
            self.confidence is not None
            and not isinstance(self.confidence, V2Confidence)
        ):
            raise TypeError(
                "confidence must be V2Confidence or None, "
                f"got {type(self.confidence).__name__}"
            )
        if (
            self.reason_code is not None
            and not isinstance(self.reason_code, SemanticReasonCodeV2)
        ):
            raise TypeError(
                "reason_code must be SemanticReasonCodeV2 or None, "
                f"got {type(self.reason_code).__name__}"
            )
        if not isinstance(self.conflict_classes, frozenset):
            raise TypeError(
                "conflict_classes must be a frozenset, "
                f"got {type(self.conflict_classes).__name__}"
            )
        for conflict in self.conflict_classes:
            if not isinstance(conflict, ConflictClass):
                raise TypeError(
                    "conflict_classes must contain only ConflictClass "
                    f"members, got {conflict!r}"
                )
        if not isinstance(self.matched_attributes, tuple):
            raise TypeError(
                "matched_attributes must be a tuple, "
                f"got {type(self.matched_attributes).__name__}"
            )
        for i, item in enumerate(self.matched_attributes):
            if not isinstance(item, SemanticAttributeV2):
                raise TypeError(
                    f"matched_attributes[{i}] must be SemanticAttributeV2, "
                    f"got {type(item).__name__}"
                )
        if not isinstance(self.conflicting_attributes, tuple):
            raise TypeError(
                "conflicting_attributes must be a tuple, "
                f"got {type(self.conflicting_attributes).__name__}"
            )
        for i, item in enumerate(self.conflicting_attributes):
            if not isinstance(item, SemanticAttributeV2):
                raise TypeError(
                    f"conflicting_attributes[{i}] must be "
                    f"SemanticAttributeV2, got {type(item).__name__}"
                )
        if not isinstance(self.missing_critical_attributes, tuple):
            raise TypeError(
                "missing_critical_attributes must be a tuple, "
                f"got {type(self.missing_critical_attributes).__name__}"
            )
        for i, item in enumerate(self.missing_critical_attributes):
            if not isinstance(item, SemanticAttributeDimensionV2):
                raise TypeError(
                    f"missing_critical_attributes[{i}] must be "
                    "SemanticAttributeDimensionV2, "
                    f"got {type(item).__name__}"
                )
        if not isinstance(self.attempts, tuple):
            raise TypeError(
                f"attempts must be a tuple, got {type(self.attempts).__name__}"
            )
        for i, attempt in enumerate(self.attempts):
            if not isinstance(attempt, SemanticDecisionAttempt):
                raise TypeError(
                    f"attempts[{i}] must be SemanticDecisionAttempt, "
                    f"got {type(attempt).__name__}"
                )
        if not isinstance(self.fallback_used, bool):
            raise TypeError(
                "fallback_used must be bool, "
                f"got {type(self.fallback_used).__name__}"
            )
        if (
            self.fallback_reason is not None
            and not isinstance(self.fallback_reason, SemanticFallbackReason)
        ):
            raise TypeError(
                "fallback_reason must be SemanticFallbackReason or None, "
                f"got {type(self.fallback_reason).__name__}"
            )
        if (
            self.error_type is not None
            and not isinstance(self.error_type, SemanticFailureClass)
        ):
            raise TypeError(
                "error_type must be SemanticFailureClass or None, "
                f"got {type(self.error_type).__name__}"
            )
        if self.actual_provider is not None:
            _validate_str(
                self.actual_provider, "actual_provider", allow_empty=False
            )
        if self.actual_model is not None:
            _validate_str(self.actual_model, "actual_model", allow_empty=False)
        _validate_timestamp(self.evaluation_started_at, "evaluation_started_at")
        _validate_timestamp(self.evaluation_finished_at, "evaluation_finished_at")
        if not isinstance(
            self.product_evidence_quality, ProductEvidenceQuality
        ):
            raise TypeError(
                "product_evidence_quality must be ProductEvidenceQuality, "
                f"got {type(self.product_evidence_quality).__name__}"
            )
        if not isinstance(
            self.relationship_authority, RelationshipAuthority
        ):
            raise TypeError(
                "relationship_authority must be RelationshipAuthority, "
                f"got {type(self.relationship_authority).__name__}"
            )
        if not isinstance(self.authority_tier, AuthorityTier):
            raise TypeError(
                "authority_tier must be AuthorityTier, "
                f"got {type(self.authority_tier).__name__}"
            )
        if not isinstance(self.fired_rules, frozenset):
            raise TypeError(
                "fired_rules must be a frozenset, "
                f"got {type(self.fired_rules).__name__}"
            )
        for rule in self.fired_rules:
            if not isinstance(rule, AuthorityRuleV2):
                raise TypeError(
                    "fired_rules must contain only AuthorityRuleV2 "
                    f"members, got {rule!r}"
                )

    # -- universal binding (validated by the envelope foundation) ----------------

    def _validate_binding(self) -> None:
        _validate_binding_fields(
            self.run_id, self.assessment_index, self.source_url
        )

    # -- V2 contract binding (the adapter's exact pin) ------------------------------

    def _validate_contract_binding(self) -> None:
        # The V2 adapter interprets exactly one contract binding. Anything
        # else is outside this adapter's safe-replay envelope and fails
        # closed at construction (never silently reinterpreted).
        if self.semantic_contract_version != SEMANTIC_CONTRACT_VERSION_V2:
            raise ValueError(
                "semantic_contract_version must be "
                f"{SEMANTIC_CONTRACT_VERSION_V2!r} for this V2 record, got "
                f"{self.semantic_contract_version!r}; an artifact bound to "
                "another semantic contract is outside the V2 adapter and "
                "fails closed"
            )
        if self.prompt_version != PROMPT_VERSION_V2:
            raise ValueError(
                "prompt_version must be "
                f"{PROMPT_VERSION_V2!r} for semantic contract "
                f"{SEMANTIC_CONTRACT_VERSION_V2}, got {self.prompt_version!r}"
            )
        for name, value, expected in (
            (
                "input_schema_version",
                self.input_schema_version,
                SEMANTIC_INPUT_SCHEMA_VERSION_V2,
            ),
            (
                "output_schema_version",
                self.output_schema_version,
                SEMANTIC_OUTPUT_SCHEMA_VERSION_V2,
            ),
        ):
            if isinstance(value, bool) or not isinstance(value, int):
                raise TypeError(
                    f"{name} must be int, got {type(value).__name__}"
                )
            if value != expected:
                raise ValueError(
                    f"{name} must be {expected} for the V2 contract, "
                    f"got {value}"
                )
        if self.authority_contract_version != AUTHORITY_CONTRACT_VERSION_V2:
            raise ValueError(
                "authority_contract_version must be "
                f"{AUTHORITY_CONTRACT_VERSION_V2!r} for the V2 contract, "
                f"got {self.authority_contract_version!r}; the derived "
                "audit snapshots of this artifact were produced under the "
                "exact bound authority contract, and no other"
            )

    # -- evaluation + execution coherence (the V2 route pin lives here) -----------

    def _validate_evaluation_and_execution(self) -> None:
        state = self.evaluation_state

        if state is SemanticEvaluationStateV2.NOT_EVALUATED:
            # No call happened: no output, no execution, no instants.
            for name, value in (
                ("decision", self.decision),
                ("confidence", self.confidence),
                ("reason_code", self.reason_code),
                ("error_type", self.error_type),
                ("actual_provider", self.actual_provider),
                ("actual_model", self.actual_model),
                ("evaluation_started_at", self.evaluation_started_at),
                ("evaluation_finished_at", self.evaluation_finished_at),
            ):
                if value is not None:
                    raise ValueError(
                        f"NOT_EVALUATED may not carry {name}; a record that "
                        "was never evaluated has no semantic output and no "
                        "runtime provenance (absence is never defaulted)"
                    )
            if self.conflict_classes:
                raise ValueError(
                    "NOT_EVALUATED may not carry conflict classes; conflicts "
                    "are observed by an evaluation"
                )
            if (
                self.matched_attributes
                or self.conflicting_attributes
                or self.missing_critical_attributes
            ):
                raise ValueError(
                    "NOT_EVALUATED may not carry recorded attribute lists"
                )
            if self.attempts:
                raise ValueError(
                    "NOT_EVALUATED may not carry attempts; no provider was "
                    "called"
                )
            if self.fallback_used or self.fallback_reason is not None:
                raise ValueError(
                    "NOT_EVALUATED may not record fallback use or a fallback "
                    "reason"
                )
            return

        # EVALUATED and RUNTIME_FAILURE both attempted: instants required.
        if (
            self.evaluation_started_at is None
            or self.evaluation_finished_at is None
        ):
            raise ValueError(f"{state.value} requires both evaluation instants")
        started = datetime.fromisoformat(
            self.evaluation_started_at.replace("Z", "+00:00")
        )
        finished = datetime.fromisoformat(
            self.evaluation_finished_at.replace("Z", "+00:00")
        )
        if finished < started:
            raise ValueError(
                "evaluation_finished_at must not precede "
                "evaluation_started_at"
            )

        attempt_count = len(self.attempts)
        if attempt_count not in (1, 2):
            raise ValueError(
                f"{state.value} requires exactly one or two recorded "
                f"attempts, got {attempt_count}"
            )
        # Role / number / route pinning (V2 semantic contract = the V2
        # pinned route; the attempts are recorded in call order).
        for i, attempt in enumerate(self.attempts):
            if attempt.attempt_number != i + 1:
                raise ValueError(
                    f"attempts[{i}].attempt_number must be {i + 1} "
                    f"(call order), got {attempt.attempt_number}"
                )
            if i == 0:
                if (
                    attempt.provider != PRIMARY_PROVIDER_V2
                    or attempt.model != PRIMARY_MODEL_V2
                ):
                    raise ValueError(
                        "the primary attempt of a V2-bound record must be "
                        f"the pinned primary {PRIMARY_PROVIDER_V2}/"
                        f"{PRIMARY_MODEL_V2}, got {attempt.provider}/"
                        f"{attempt.model}"
                    )
            else:
                if (
                    attempt.provider != FALLBACK_PROVIDER_V2
                    or attempt.model != FALLBACK_MODEL_V2
                ):
                    raise ValueError(
                        "the fallback attempt of a V2-bound record must be "
                        f"the pinned fallback {FALLBACK_PROVIDER_V2}/"
                        f"{FALLBACK_MODEL_V2}, got {attempt.provider}/"
                        f"{attempt.model}"
                    )

        if attempt_count == 2 and not self.fallback_used:
            raise ValueError(
                "fallback_used must be True when two attempts were recorded"
            )
        if attempt_count == 1 and self.fallback_used:
            raise ValueError(
                "fallback_used must be False when one attempt was recorded"
            )
        if attempt_count == 2 and self.fallback_reason is None:
            raise ValueError(
                "a two-attempt record must record the fallback reason"
            )
        if (
            attempt_count == 2
            and self.fallback_reason is SemanticFallbackReason.NONE
        ):
            raise ValueError(
                "the recorded fallback reason must not be NONE when a "
                "fallback attempt was made"
            )
        if attempt_count == 1 and self.fallback_reason is not None:
            raise ValueError(
                "a one-attempt record must not carry a fallback reason"
            )

        if state is SemanticEvaluationStateV2.EVALUATED:
            # Success: a strict structured V2 response, an OK final
            # attempt, and provenance attributed to exactly that attempt.
            if (
                self.decision is None
                or self.confidence is None
                or self.reason_code is None
            ):
                raise ValueError(
                    "EVALUATED requires a decision, a confidence, and the "
                    "bounded V2 reason code"
                )
            if self.error_type is not None:
                raise ValueError(
                    "EVALUATED may not carry an error_type; the evaluation "
                    "produced an accepted response"
                )
            if self.attempts[-1].outcome is not AttemptOutcome.OK:
                raise ValueError(
                    "an EVALUATED record must end with an OK attempt"
                )
            if (
                attempt_count == 2
                and self.attempts[0].outcome is AttemptOutcome.OK
            ):
                raise ValueError(
                    "a successful primary is final: a two-attempt record "
                    "cannot have an OK primary attempt"
                )
            ok_attempt = self.attempts[-1]
            if self.actual_provider != ok_attempt.provider:
                raise ValueError(
                    "actual_provider must be the provider of the OK attempt"
                )
            if self.actual_model != ok_attempt.model:
                raise ValueError(
                    "actual_model must be the model of the OK attempt"
                )
            # The strict structured V2 output must be coherent under the
            # frozen reason-code rules (unknown decision/confidence/reason
            # codes, unknown conflict classes, missing fields, extra
            # fields, and decision/conflict incoherence all fail closed).
            SemanticMatchResponseV2(
                decision=self.decision,
                confidence=self.confidence,
                reason_code=self.reason_code,
                matched_attributes=self.matched_attributes,
                conflicting_attributes=self.conflicting_attributes,
                missing_critical_attributes=(
                    self.missing_critical_attributes
                ),
                conflict_classes=self.conflict_classes,
            )
        else:  # RUNTIME_FAILURE
            # Failure: never shaped like a decision (a runtime failure is
            # NEVER interpreted as NO_MATCH or anything else evidence-
            # shaped).
            if (
                self.decision is not None
                or self.confidence is not None
                or self.reason_code is not None
            ):
                raise ValueError(
                    "RUNTIME_FAILURE may not carry a decision, confidence, "
                    "or reason code; a runtime failure is never "
                    "interpreted as NO_MATCH"
                )
            if (
                self.conflict_classes
                or self.matched_attributes
                or self.conflicting_attributes
                or self.missing_critical_attributes
            ):
                raise ValueError(
                    "RUNTIME_FAILURE may not carry conflict classes or "
                    "recorded attribute lists"
                )
            if (
                self.actual_provider is not None
                or self.actual_model is not None
            ):
                raise ValueError(
                    "RUNTIME_FAILURE must not name an actual provider or "
                    "model; no provider produced an accepted response"
                )
            if any(
                attempt.outcome is AttemptOutcome.OK
                for attempt in self.attempts
            ):
                raise ValueError(
                    "a RUNTIME_FAILURE record must not contain an OK attempt"
                )
            if self.error_type is None:
                raise ValueError(
                    "RUNTIME_FAILURE requires the bounded failure class"
                )
            allowed_family = (
                _V2_ONE_ATTEMPT_FAILURE_CLASSES
                if attempt_count == 1
                else _V2_TWO_ATTEMPT_FAILURE_CLASSES
            )
            if self.error_type not in allowed_family:
                raise ValueError(
                    f"error_type {self.error_type.value} is inconsistent "
                    f"with {attempt_count} recorded attempt(s)"
                )

    # -- derived snapshots (types only; agreement is replay's job) ------------------

    def _validate_derived_types(self) -> None:
        if not self.fired_rules:
            raise ValueError(
                "an authority decision must record at least one fired rule"
            )

    # -- integrity self-verification ---------------------------------------------------

    def _validate_digests(self) -> None:
        _validate_digest(self.input_digest, "input_digest")
        _validate_digest(self.output_digest, "output_digest")
        expected_input = record_input_digest_v2(self)
        expected_output = record_output_digest_v2(self)
        if self.input_digest != expected_input:
            raise ValueError(
                "input_digest does not agree with the record's input "
                "sections (binding, contract, case); the artifact is "
                "corrupt or was built with the wrong digest"
            )
        if self.output_digest != expected_output:
            raise ValueError(
                "output_digest does not agree with the record's output "
                "sections (evaluation, execution, derived); the artifact "
                "is corrupt or was built with the wrong digest"
            )

    # -- section accessors (shared by the V2 codec and the digest functions) ----------

    def case_section(self) -> dict[str, object]:
        return self.case.canonical()

    def binding_section(self) -> dict[str, object]:
        return _binding_section(
            self.run_id, self.assessment_index, self.source_url
        )

    def contract_section(self) -> dict[str, object]:
        return _v2_contract_section()

    def evaluation_section(self) -> dict[str, object]:
        return _v2_evaluation_section(
            self.evaluation_state,
            self.decision,
            self.confidence,
            self.conflict_classes,
            self.reason_code,
            self.matched_attributes,
            self.conflicting_attributes,
            self.missing_critical_attributes,
        )

    def execution_section(self) -> dict[str, object]:
        return _v2_execution_section(
            self.attempts,
            self.fallback_used,
            self.fallback_reason,
            self.error_type,
            self.actual_provider,
            self.actual_model,
            self.evaluation_started_at,
            self.evaluation_finished_at,
        )

    def derived_section(self) -> dict[str, object]:
        return _v2_derived_section(
            self.product_evidence_quality,
            self.relationship_authority,
            self.authority_tier,
            self.fired_rules,
        )

    def integrity_section(self) -> dict[str, str]:
        return {
            "input_digest": self.input_digest,
            "output_digest": self.output_digest,
        }

    # -- construction convenience --------------------------------------------------------

    @classmethod
    def build(
        cls,
        *,
        run_id: str,
        assessment_index: int,
        source_url: str,
        case: SemanticMatchCaseV2,
        evaluation_state: SemanticEvaluationStateV2,
        decision: V2SemanticDecision | None,
        confidence: V2Confidence | None,
        reason_code: SemanticReasonCodeV2 | None,
        conflict_classes: frozenset[ConflictClass],
        matched_attributes: tuple[SemanticAttributeV2, ...],
        conflicting_attributes: tuple[SemanticAttributeV2, ...],
        missing_critical_attributes: tuple[SemanticAttributeDimensionV2, ...],
        attempts: tuple[SemanticDecisionAttempt, ...],
        fallback_used: bool,
        fallback_reason: SemanticFallbackReason | None,
        error_type: SemanticFailureClass | None,
        actual_provider: str | None,
        actual_model: str | None,
        evaluation_started_at: str | None,
        evaluation_finished_at: str | None,
        product_evidence_quality: ProductEvidenceQuality,
        relationship_authority: RelationshipAuthority,
        authority_tier: AuthorityTier,
        fired_rules: frozenset[AuthorityRuleV2],
    ) -> "SemanticDecisionRecordV2":
        """Build a V2 record, computing the self-verifying section digests.

        The contract binding is the V2 frozen one (semantic contract V2,
        prompt 2.0, input/output schema 1, authority contract S2-A-FU2):
        the builder takes no version parameters so a V2 artifact cannot
        be bound to a contract this adapter does not know.
        """
        input_digest = canonical_sha256(
            {
                "binding": _binding_section(run_id, assessment_index, source_url),
                "contract": _v2_contract_section(),
                "case": case.canonical(),
            }
        )
        output_digest = canonical_sha256(
            {
                "evaluation": _v2_evaluation_section(
                    evaluation_state,
                    decision,
                    confidence,
                    conflict_classes,
                    reason_code,
                    matched_attributes,
                    conflicting_attributes,
                    missing_critical_attributes,
                ),
                "execution": _v2_execution_section(
                    attempts,
                    fallback_used,
                    fallback_reason,
                    error_type,
                    actual_provider,
                    actual_model,
                    evaluation_started_at,
                    evaluation_finished_at,
                ),
                "derived": _v2_derived_section(
                    product_evidence_quality,
                    relationship_authority,
                    authority_tier,
                    fired_rules,
                ),
            }
        )
        return cls(
            run_id=run_id,
            assessment_index=assessment_index,
            source_url=source_url,
            semantic_contract_version=SEMANTIC_CONTRACT_VERSION_V2,
            prompt_version=PROMPT_VERSION_V2,
            input_schema_version=SEMANTIC_INPUT_SCHEMA_VERSION_V2,
            output_schema_version=SEMANTIC_OUTPUT_SCHEMA_VERSION_V2,
            authority_contract_version=AUTHORITY_CONTRACT_VERSION_V2,
            case=case,
            evaluation_state=evaluation_state,
            decision=decision,
            confidence=confidence,
            reason_code=reason_code,
            conflict_classes=conflict_classes,
            matched_attributes=matched_attributes,
            conflicting_attributes=conflicting_attributes,
            missing_critical_attributes=missing_critical_attributes,
            attempts=attempts,
            fallback_used=fallback_used,
            fallback_reason=fallback_reason,
            error_type=error_type,
            actual_provider=actual_provider,
            actual_model=actual_model,
            evaluation_started_at=evaluation_started_at,
            evaluation_finished_at=evaluation_finished_at,
            product_evidence_quality=product_evidence_quality,
            relationship_authority=relationship_authority,
            authority_tier=authority_tier,
            fired_rules=fired_rules,
            input_digest=input_digest,
            output_digest=output_digest,
        )


def record_input_digest_v2(record: SemanticDecisionRecordV2) -> str:
    """SHA-256 over the canonical encoding of the V2 record's INPUT
    sections: binding + contract + the exact recorded V2 input (case)."""
    return canonical_sha256(
        {
            "binding": record.binding_section(),
            "contract": record.contract_section(),
            "case": record.case_section(),
        }
    )


def record_output_digest_v2(record: SemanticDecisionRecordV2) -> str:
    """SHA-256 over the canonical encoding of the V2 record's OUTPUT
    sections: recorded V2 evaluation + recorded V2 execution provenance +
    derived audit snapshots."""
    return canonical_sha256(
        {
            "evaluation": record.evaluation_section(),
            "execution": record.execution_section(),
            "derived": record.derived_section(),
        }
    )


# ---------------------------------------------------------------------------
# The V2 payload codec (the exact V2 section shapes; strict, fail closed)
# ---------------------------------------------------------------------------


_V2_TOP_LEVEL_KEYS: Final[frozenset[str]] = frozenset(
    {
        "schema_version",
        "binding",
        "contract",
        "case",
        "evaluation",
        "execution",
        "derived",
        "integrity",
    }
)

_V2_CONTRACT_KEYS: Final[frozenset[str]] = frozenset(
    {
        "semantic_contract_version",
        "prompt_version",
        "input_schema_version",
        "output_schema_version",
        "authority_contract_version",
    }
)

_V2_CASE_KEYS: Final[frozenset[str]] = frozenset(
    {
        "case_id",
        "target",
        "candidate",
        "deterministic_identity_context",
        "context_provenance",
        "product_evidence",
    }
)

_V2_TARGET_KEYS: Final[frozenset[str]] = frozenset(
    {"mpn", "description_raw_text", "reviewed_context"}
)

_V2_REVIEWED_TARGET_CONTEXT_KEYS: Final[frozenset[str]] = frozenset(
    {
        "manufacturer",
        "category",
        "matched_base_part_number",
        "relation_kind",
        "relation_family_part_numbers",
        "source_name",
        "source_url",
        "retrieved_at",
        "evidence_body_sha256",
    }
)

_V2_CANDIDATE_KEYS: Final[frozenset[str]] = frozenset(
    {
        "source_url",
        "mpn_field",
        "sku",
        "evidence_source",
        "product",
        "commercial",
    }
)

_V2_CANDIDATE_PRODUCT_KEYS: Final[frozenset[str]] = frozenset(
    {
        "product_family",
        "generation",
        "capacity",
        "interface",
        "form_factor",
        "product_role",
        "accessory_relation",
        "brand",
        "revision_or_suffix",
        "raw_title_text",
        "raw_specification_text",
    }
)

_V2_CANDIDATE_COMMERCIAL_KEYS: Final[frozenset[str]] = frozenset(
    {
        "condition",
        "price",
        "currency",
        "availability",
        "seller",
        "offer_url",
        "sales_unit",
    }
)

_V2_OBSERVATION_FACT_KEYS: Final[frozenset[str]] = frozenset(
    {"value", "source"}
)

_V2_SALES_UNIT_KEYS: Final[frozenset[str]] = frozenset(
    {"state", "kind", "quantity", "raw_detail", "source"}
)

_V2_IDENTITY_CONTEXT_KEYS: Final[frozenset[str]] = frozenset(
    {
        "identity_state",
        "substate",
        "primary_relationship_signal",
        "relationship_signals",
        "normalized_requested_part_number",
        "normalized_candidate_part_number",
        "relationship_requirement",
    }
)

_V2_PRODUCT_EVIDENCE_KEYS: Final[frozenset[str]] = frozenset(
    {"has_usable_product_title", "matched_facts"}
)

_V2_FACT_KEYS: Final[frozenset[str]] = frozenset({"dimension", "sources"})

_V2_EVALUATION_KEYS: Final[frozenset[str]] = frozenset(
    {
        "evaluation_state",
        "decision",
        "confidence",
        "reason_code",
        "conflict_classes",
        "matched_attributes",
        "conflicting_attributes",
        "missing_critical_attributes",
    }
)

_V2_EXECUTION_KEYS: Final[frozenset[str]] = frozenset(
    {
        "attempts",
        "fallback_used",
        "fallback_reason",
        "error_type",
        "actual_provider",
        "actual_model",
        "evaluation_started_at",
        "evaluation_finished_at",
    }
)

_V2_ATTEMPT_KEYS: Final[frozenset[str]] = frozenset(
    {"role", "attempt_number", "provider", "model", "outcome"}
)

_V2_ATTRIBUTE_KEYS: Final[frozenset[str]] = frozenset({"dimension", "detail"})

_V2_DERIVED_KEYS: Final[frozenset[str]] = frozenset(
    {
        "product_evidence_quality",
        "relationship_authority",
        "authority_tier",
        "fired_rules",
    }
)

_V2_INTEGRITY_KEYS: Final[frozenset[str]] = frozenset(
    {"input_digest", "output_digest"}
)


def encode_v2_payload(record: SemanticDecisionRecordV2) -> dict[str, object]:
    """Encode a ``SemanticDecisionRecordV2`` into the full framed payload
    (envelope schema version 1, semantic contract V2).

    The returned dict contains only native JSON types (str, int, bool,
    list, dict, None) — no enum members, no dataclass objects, no floats.
    Set-valued fields are encoded as sorted unique value lists;
    order-significant fields (attempts, attribute lists) keep their order.

    Raises ``TypeError`` if the input is not a V2 record (caller defect).
    """
    if not isinstance(record, SemanticDecisionRecordV2):
        raise TypeError(
            f"expected SemanticDecisionRecordV2, got {type(record).__name__}"
        )
    return {
        "schema_version": 1,
        "binding": record.binding_section(),
        "contract": record.contract_section(),
        "case": record.case_section(),
        "evaluation": record.evaluation_section(),
        "execution": record.execution_section(),
        "derived": record.derived_section(),
        "integrity": record.integrity_section(),
    }


def _dec_v2_attempt(data: dict[str, object], path: str) -> SemanticDecisionAttempt:
    _check_keys(data, _V2_ATTEMPT_KEYS, path)
    return SemanticDecisionAttempt(
        role=_dec_str_enum(
            AttemptRole, _dec_required(data, "role", path), f"{path}.role"
        ),
        attempt_number=_dec_int(
            _dec_required(data, "attempt_number", path),
            f"{path}.attempt_number",
        ),
        provider=_dec_str(
            _dec_required(data, "provider", path),
            f"{path}.provider",
            allow_empty=False,
        ),
        model=_dec_str(
            _dec_required(data, "model", path),
            f"{path}.model",
            allow_empty=False,
        ),
        outcome=_dec_str_enum(
            AttemptOutcome,
            _dec_required(data, "outcome", path),
            f"{path}.outcome",
        ),
    )


def _dec_v2_fact(data: dict[str, object], path: str):
    """Decode one authority-side matched-attribute fact (the frozen S2-A
    vocabulary; the source set has NO model-claim member)."""
    _check_keys(data, _V2_FACT_KEYS, path)
    sources_raw = _dec_sorted_unique_str_list(
        _dec_required(data, "sources", path), f"{path}.sources"
    )
    sources = frozenset(
        _dec_str_enum(
            CandidateProductEvidenceSource,
            value,
            f"{path}.sources[{i}]",
        )
        for i, value in enumerate(sources_raw)
    )
    if not sources:
        raise SemanticDecisionCodecError(
            f"{path}: a matched-attribute fact requires at least one "
            "bounded candidate-side source"
        )
    return ProductEvidenceFactV2(
        dimension=_dec_str_enum(
            ProductEvidenceDimension,
            _dec_required(data, "dimension", path),
            f"{path}.dimension",
        ),
        sources=sources,
    )


def _dec_v2_profile(data: dict[str, object], path: str) -> ProductEvidenceProfileV2:
    _check_keys(data, _V2_PRODUCT_EVIDENCE_KEYS, path)
    has_title = _dec_bool(
        _dec_required(data, "has_usable_product_title", path),
        f"{path}.has_usable_product_title",
    )
    facts_raw = _dec_list(
        _dec_required(data, "matched_facts", path), f"{path}.matched_facts"
    )
    facts: list = []
    seen: set = set()
    for i, item in enumerate(facts_raw):
        fact = _dec_v2_fact(
            _dec_mapping(item, f"{path}.matched_facts[{i}]"),
            f"{path}.matched_facts[{i}]",
        )
        key = (
            fact.dimension.value,
            tuple(sorted(s.value for s in fact.sources)),
        )
        if key in seen:
            raise SemanticDecisionCodecError(
                f"{path}.matched_facts[{i}]: duplicate matched-attribute fact"
            )
        seen.add(key)
        facts.append(fact)
    return ProductEvidenceProfileV2(
        has_usable_product_title=has_title,
        matched_facts=frozenset(facts),
    )


# The four frozen V2 sub-state enum families (values are unique across
# families, so decoding by value is well-defined; the case constructor
# then re-validates the state/sub-state pairing and fails closed).
_SUBSTATE_ENUM_FAMILIES = (
    VerifiedSubstateV2,
    UncertainSubstateV2,
    ConflictSubstateV2,
    UnevaluableSubstateV2,
)


def _dec_v2_substate(raw: object, path: str):
    """Decode a sub-state value across the four frozen V2 families."""
    value = _dec_str(raw, path, allow_empty=False)
    for family in _SUBSTATE_ENUM_FAMILIES:
        for member in family:
            if member.value == value:
                return member
    raise SemanticDecisionCodecError(
        f"{path}: unknown V2 sub-state value {value!r}"
    )


def _dec_v2_attribute_list(data: list[object], path: str) -> tuple[SemanticAttributeV2, ...]:
    out: list[SemanticAttributeV2] = []
    seen: set = set()
    for i, item in enumerate(data):
        item_data = _dec_mapping(item, f"{path}[{i}]")
        _check_keys(item_data, _V2_ATTRIBUTE_KEYS, f"{path}[{i}]")
        dimension = _dec_str_enum(
            SemanticAttributeDimensionV2,
            _dec_required(item_data, "dimension", f"{path}[{i}]"),
            f"{path}[{i}].dimension",
        )
        detail = _dec_str(_dec_required(item_data, "detail", f"{path}[{i}]"), f"{path}[{i}].detail")
        key = (dimension.value, detail)
        if key in seen:
            raise SemanticDecisionCodecError(
                f"{path}[{i}]: duplicate structured attribute"
            )
        seen.add(key)
        out.append(SemanticAttributeV2(dimension=dimension, detail=detail))
    return tuple(out)


def _dec_v2_observation_fact(
    data: object, path: str
) -> CandidateObservationFactV2 | None:
    """Decode one bounded candidate observation fact (absent = null)."""
    if data is None:
        return None
    fact = _dec_mapping(data, path)
    _check_keys(fact, _V2_OBSERVATION_FACT_KEYS, path)
    value = _dec_str(
        _dec_required(fact, "value", path), f"{path}.value", allow_empty=False
    )
    source = _dec_str_enum(
        CandidateEvidenceSourceV2,
        _dec_required(fact, "source", path),
        f"{path}.source",
    )
    return CandidateObservationFactV2(value=value, source=source)


def _dec_v2_sales_unit(data: object, path: str) -> CandidateSalesUnitEvidenceV2:
    """Decode the bounded packaging / sales-unit channel (always present,
    always an explicit state)."""
    su = _dec_mapping(data, path)
    _check_keys(su, _V2_SALES_UNIT_KEYS, path)
    state = _dec_str_enum(
        PackagingEvidenceStateV2,
        _dec_required(su, "state", path),
        f"{path}.state",
    )
    kind = _dec_optional_str_enum(
        SalesUnitKindV2,
        _dec_required(su, "kind", path),
        f"{path}.kind",
    )
    quantity_raw = _dec_required(su, "quantity", path)
    quantity = (
        None
        if quantity_raw is None
        else _dec_int(quantity_raw, f"{path}.quantity")
    )
    raw_detail = _dec_optional_str(
        _dec_required(su, "raw_detail", path), f"{path}.raw_detail"
    )
    source = _dec_optional_str_enum(
        CandidateEvidenceSourceV2,
        _dec_required(su, "source", path),
        f"{path}.source",
    )
    return CandidateSalesUnitEvidenceV2(
        state=state,
        kind=kind,
        quantity=quantity,
        raw_detail=raw_detail,
        source=source,
    )


def _dec_v2_reviewed_target_context(
    data: object, path: str
) -> ReviewedTargetContextV2 | None:
    """Decode the reviewed manufacturer target context (absent = null)."""
    if data is None:
        return None
    ctx = _dec_mapping(data, path)
    _check_keys(ctx, _V2_REVIEWED_TARGET_CONTEXT_KEYS, path)
    manufacturer = _dec_str(
        _dec_required(ctx, "manufacturer", path),
        f"{path}.manufacturer",
        allow_empty=False,
    )
    category = _dec_str(
        _dec_required(ctx, "category", path), f"{path}.category",
        allow_empty=False,
    )
    matched_base_part_number = _dec_str(
        _dec_required(ctx, "matched_base_part_number", path),
        f"{path}.matched_base_part_number",
        allow_empty=False,
    )
    relation_kind = _dec_str_enum(
        TargetIdentifierRelationKindV2,
        _dec_required(ctx, "relation_kind", path),
        f"{path}.relation_kind",
    )
    relation_family_part_numbers = _dec_str_list(
        _dec_required(ctx, "relation_family_part_numbers", path),
        f"{path}.relation_family_part_numbers",
    )
    source_name = _dec_str(
        _dec_required(ctx, "source_name", path), f"{path}.source_name",
        allow_empty=False,
    )
    source_url = _dec_str(
        _dec_required(ctx, "source_url", path), f"{path}.source_url",
        allow_empty=False,
    )
    retrieved_at = _dec_str(
        _dec_required(ctx, "retrieved_at", path), f"{path}.retrieved_at",
        allow_empty=False,
    )
    evidence_body_sha256 = _dec_str(
        _dec_required(ctx, "evidence_body_sha256", path),
        f"{path}.evidence_body_sha256",
        allow_empty=False,
    )
    return ReviewedTargetContextV2(
        manufacturer=manufacturer,
        category=category,
        matched_base_part_number=matched_base_part_number,
        relation_kind=relation_kind,
        relation_family_part_numbers=relation_family_part_numbers,
        source_name=source_name,
        source_url=source_url,
        retrieved_at=retrieved_at,
        evidence_body_sha256=evidence_body_sha256,
    )


def _dec_v2_case(data: dict[str, object], path: str) -> SemanticMatchCaseV2:
    _check_keys(data, _V2_CASE_KEYS, path)

    case_id = _dec_str(
        _dec_required(data, "case_id", path), f"{path}.case_id", allow_empty=False
    )

    target = _dec_mapping(_dec_required(data, "target", path), f"{path}.target")
    _check_keys(target, _V2_TARGET_KEYS, f"{path}.target")
    target_mpn = _dec_str(
        _dec_required(target, "mpn", f"{path}.target"),
        f"{path}.target.mpn",
        allow_empty=False,
    )
    target_description_raw_text = _dec_optional_str(
        _dec_required(target, "description_raw_text", f"{path}.target"),
        f"{path}.target.description_raw_text",
    )
    reviewed_target_context = _dec_v2_reviewed_target_context(
        _dec_required(target, "reviewed_context", f"{path}.target"),
        f"{path}.target.reviewed_context",
    )

    candidate = _dec_mapping(
        _dec_required(data, "candidate", path), f"{path}.candidate"
    )
    _check_keys(candidate, _V2_CANDIDATE_KEYS, f"{path}.candidate")
    candidate_source_url = _dec_str(
        _dec_required(candidate, "source_url", f"{path}.candidate"),
        f"{path}.candidate.source_url",
        allow_empty=False,
    )
    candidate_mpn_field = _dec_optional_str(
        _dec_required(candidate, "mpn_field", f"{path}.candidate"),
        f"{path}.candidate.mpn_field",
    )
    candidate_sku = _dec_optional_str(
        _dec_required(candidate, "sku", f"{path}.candidate"),
        f"{path}.candidate.sku",
    )
    candidate_evidence_source = _dec_str(
        _dec_required(candidate, "evidence_source", f"{path}.candidate"),
        f"{path}.candidate.evidence_source",
        allow_empty=False,
    )

    product_data = _dec_mapping(
        _dec_required(candidate, "product", f"{path}.candidate"),
        f"{path}.candidate.product",
    )
    _check_keys(
        product_data, _V2_CANDIDATE_PRODUCT_KEYS, f"{path}.candidate.product"
    )
    product_dimension_fields = (
        "product_family",
        "generation",
        "capacity",
        "interface",
        "form_factor",
        "product_role",
        "accessory_relation",
        "brand",
        "revision_or_suffix",
    )
    product_kwargs: dict[str, object] = {
        field: _dec_v2_observation_fact(
            _dec_required(product_data, field, f"{path}.candidate.product"),
            f"{path}.candidate.product.{field}",
        )
        for field in product_dimension_fields
    }
    product_kwargs["raw_title_text"] = _dec_optional_str(
        _dec_required(product_data, "raw_title_text", f"{path}.candidate.product"),
        f"{path}.candidate.product.raw_title_text",
    )
    product_kwargs["raw_specification_text"] = _dec_optional_str(
        _dec_required(
            product_data, "raw_specification_text", f"{path}.candidate.product"
        ),
        f"{path}.candidate.product.raw_specification_text",
    )
    candidate_product = CandidateProductEvidenceV2(**product_kwargs)

    commercial_data = _dec_mapping(
        _dec_required(candidate, "commercial", f"{path}.candidate"),
        f"{path}.candidate.commercial",
    )
    _check_keys(
        commercial_data, _V2_CANDIDATE_COMMERCIAL_KEYS,
        f"{path}.candidate.commercial",
    )
    commercial_fields = ("condition", "price", "currency", "availability", "seller")
    commercial_kwargs: dict[str, object] = {
        field: _dec_v2_observation_fact(
            _dec_required(
                commercial_data, field, f"{path}.candidate.commercial"
            ),
            f"{path}.candidate.commercial.{field}",
        )
        for field in commercial_fields
    }
    commercial_kwargs["offer_url"] = _dec_optional_str(
        _dec_required(commercial_data, "offer_url", f"{path}.candidate.commercial"),
        f"{path}.candidate.commercial.offer_url",
    )
    commercial_kwargs["sales_unit"] = _dec_v2_sales_unit(
        _dec_required(commercial_data, "sales_unit", f"{path}.candidate.commercial"),
        f"{path}.candidate.commercial.sales_unit",
    )
    candidate_commercial = CandidateCommercialEvidenceV2(**commercial_kwargs)

    identity_context = _dec_mapping(
        _dec_required(data, "deterministic_identity_context", path),
        f"{path}.deterministic_identity_context",
    )
    _check_keys(
        identity_context, _V2_IDENTITY_CONTEXT_KEYS,
        f"{path}.deterministic_identity_context",
    )
    identity_state = _dec_str_enum(
        IdentityStateV2,
        _dec_required(
            identity_context, "identity_state",
            f"{path}.deterministic_identity_context",
        ),
        f"{path}.deterministic_identity_context.identity_state",
    )
    substate = _dec_v2_substate(
        _dec_required(
            identity_context, "substate",
            f"{path}.deterministic_identity_context",
        ),
        f"{path}.deterministic_identity_context.substate",
    )
    primary_relationship_signal = _dec_str_enum(
        IdentityRelationshipSignal,
        _dec_required(
            identity_context, "primary_relationship_signal",
            f"{path}.deterministic_identity_context",
        ),
        f"{path}.deterministic_identity_context.primary_relationship_signal",
    )
    relationship_signals = frozenset(
        _dec_str_enum(
            IdentityRelationshipSignal,
            value,
            f"{path}.deterministic_identity_context.relationship_signals[{i}]",
        )
        for i, value in enumerate(
            _dec_sorted_unique_str_list(
                _dec_required(
                    identity_context, "relationship_signals",
                    f"{path}.deterministic_identity_context",
                ),
                f"{path}.deterministic_identity_context.relationship_signals",
            )
        )
    )
    normalized_requested_part_number = _dec_str(
        _dec_required(
            identity_context, "normalized_requested_part_number",
            f"{path}.deterministic_identity_context",
        ),
        f"{path}.deterministic_identity_context.normalized_requested_part_number",
    )
    normalized_candidate_part_number = _dec_str(
        _dec_required(
            identity_context, "normalized_candidate_part_number",
            f"{path}.deterministic_identity_context",
        ),
        f"{path}.deterministic_identity_context.normalized_candidate_part_number",
    )
    relationship_requirement = _dec_str_enum(
        RelationshipRequirement,
        _dec_required(
            identity_context, "relationship_requirement",
            f"{path}.deterministic_identity_context",
        ),
        f"{path}.deterministic_identity_context.relationship_requirement",
    )

    context_provenances = frozenset(
        _dec_str_enum(
            ContextProvenance, value, f"{path}.context_provenance[{i}]"
        )
        for i, value in enumerate(
            _dec_sorted_unique_str_list(
                _dec_required(data, "context_provenance", path),
                f"{path}.context_provenance",
            )
        )
    )

    product_evidence = _dec_v2_profile(
        _dec_mapping(
            _dec_required(data, "product_evidence", path),
            f"{path}.product_evidence",
        ),
        f"{path}.product_evidence",
    )

    # The V2 case constructor re-validates everything (the S2-A context
    # legitimacy, the UNCERTAIN-only entry point, the frozen requirement
    # table agreement, the authority-side evidence support) and fails
    # closed; any constructor violation is wrapped in the bounded codec
    # error by the caller.
    return SemanticMatchCaseV2(
        case_id=case_id,
        target=TargetEvidenceV2(
            mpn=target_mpn,
            description_raw_text=target_description_raw_text,
            reviewed_context=reviewed_target_context,
        ),
        candidate_source_url=candidate_source_url,
        candidate_mpn_field=candidate_mpn_field,
        candidate_sku=candidate_sku,
        candidate_evidence_source=candidate_evidence_source,
        candidate_product=candidate_product,
        candidate_commercial=candidate_commercial,
        identity_state=identity_state,
        substate=substate,
        primary_relationship_signal=primary_relationship_signal,
        relationship_signals=relationship_signals,
        normalized_requested_part_number=normalized_requested_part_number,
        normalized_candidate_part_number=normalized_candidate_part_number,
        relationship_requirement=relationship_requirement,
        context_provenances=context_provenances,
        product_evidence=product_evidence,
    )


def _decode_v2_payload(payload: dict[str, object]) -> SemanticDecisionRecordV2:
    """Decode a V2-framed payload into a validated V2 record.

    Raises ``SemanticDecisionCodecError`` for any structural violation and
    wraps every record-constructor failure (including the self-verifying
    digest check and the V2 exact-binding check) in the same bounded
    error.
    """
    _check_keys(payload, _V2_TOP_LEVEL_KEYS, "top-level")

    # -- binding (the universal section; re-validated strictly here) --
    binding = _dec_mapping(
        _dec_required(payload, "binding", "top-level"), "binding"
    )
    _check_keys(binding, _BINDING_KEYS, "binding")
    run_id = _dec_str(
        _dec_required(binding, "run_id", "binding"),
        "binding.run_id",
        allow_empty=False,
    )
    assessment_index = _dec_int(
        _dec_required(binding, "assessment_index", "binding"),
        "binding.assessment_index",
    )
    source_url = _dec_str(
        _dec_required(binding, "source_url", "binding"),
        "binding.source_url",
        allow_empty=False,
    )

    # -- contract (the exact frozen V2 binding) --
    contract = _dec_mapping(
        _dec_required(payload, "contract", "top-level"), "contract"
    )
    _check_keys(contract, _V2_CONTRACT_KEYS, "contract")
    semantic_contract_version = _dec_str(
        _dec_required(contract, "semantic_contract_version", "contract"),
        "contract.semantic_contract_version",
        allow_empty=False,
    )
    prompt_version = _dec_str(
        _dec_required(contract, "prompt_version", "contract"),
        "contract.prompt_version",
        allow_empty=False,
    )
    input_schema_version = _dec_int(
        _dec_required(contract, "input_schema_version", "contract"),
        "contract.input_schema_version",
    )
    output_schema_version = _dec_int(
        _dec_required(contract, "output_schema_version", "contract"),
        "contract.output_schema_version",
    )
    authority_contract_version = _dec_str(
        _dec_required(contract, "authority_contract_version", "contract"),
        "contract.authority_contract_version",
        allow_empty=False,
    )

    # -- case (the exact recorded V2 input) --
    case = _dec_v2_case(
        _dec_mapping(_dec_required(payload, "case", "top-level"), "case"),
        "case",
    )

    # -- evaluation (the strict structured V2 output) --
    evaluation_data = _dec_mapping(
        _dec_required(payload, "evaluation", "top-level"), "evaluation"
    )
    _check_keys(evaluation_data, _V2_EVALUATION_KEYS, "evaluation")
    evaluation_state = _dec_str_enum(
        SemanticEvaluationStateV2,
        _dec_required(evaluation_data, "evaluation_state", "evaluation"),
        "evaluation.evaluation_state",
    )
    decision = _dec_optional_str_enum(
        V2SemanticDecision,
        _dec_required(evaluation_data, "decision", "evaluation"),
        "evaluation.decision",
    )
    confidence = _dec_optional_str_enum(
        V2Confidence,
        _dec_required(evaluation_data, "confidence", "evaluation"),
        "evaluation.confidence",
    )
    reason_code = _dec_optional_str_enum(
        SemanticReasonCodeV2,
        _dec_required(evaluation_data, "reason_code", "evaluation"),
        "evaluation.reason_code",
    )
    conflict_classes = frozenset(
        _dec_str_enum(
            ConflictClass, value, f"evaluation.conflict_classes[{i}]"
        )
        for i, value in enumerate(
            _dec_sorted_unique_str_list(
                _dec_required(evaluation_data, "conflict_classes", "evaluation"),
                "evaluation.conflict_classes",
            )
        )
    )
    matched_attributes = _dec_v2_attribute_list(
        _dec_list(
            _dec_required(evaluation_data, "matched_attributes", "evaluation"),
            "evaluation.matched_attributes",
        ),
        "evaluation.matched_attributes",
    )
    conflicting_attributes = _dec_v2_attribute_list(
        _dec_list(
            _dec_required(
                evaluation_data, "conflicting_attributes", "evaluation"
            ),
            "evaluation.conflicting_attributes",
        ),
        "evaluation.conflicting_attributes",
    )
    missing_critical_attributes = tuple(
        _dec_str_enum(
            SemanticAttributeDimensionV2,
            value,
            f"evaluation.missing_critical_attributes[{i}]",
        )
        for i, value in enumerate(
            _dec_sorted_unique_str_list(
                _dec_required(
                    evaluation_data, "missing_critical_attributes", "evaluation"
                ),
                "evaluation.missing_critical_attributes",
            )
        )
    )

    # -- execution --
    execution_data = _dec_mapping(
        _dec_required(payload, "execution", "top-level"), "execution"
    )
    _check_keys(execution_data, _V2_EXECUTION_KEYS, "execution")
    attempts_raw = _dec_list(
        _dec_required(execution_data, "attempts", "execution"),
        "execution.attempts",
    )
    attempts = tuple(
        _dec_v2_attempt(
            _dec_mapping(item, f"execution.attempts[{i}]"),
            f"execution.attempts[{i}]",
        )
        for i, item in enumerate(attempts_raw)
    )
    fallback_used = _dec_bool(
        _dec_required(execution_data, "fallback_used", "execution"),
        "execution.fallback_used",
    )
    fallback_reason = _dec_optional_str_enum(
        SemanticFallbackReason,
        _dec_required(execution_data, "fallback_reason", "execution"),
        "execution.fallback_reason",
    )
    error_type = _dec_optional_str_enum(
        SemanticFailureClass,
        _dec_required(execution_data, "error_type", "execution"),
        "execution.error_type",
    )
    actual_provider = _dec_optional_str(
        _dec_required(execution_data, "actual_provider", "execution"),
        "execution.actual_provider",
    )
    actual_model = _dec_optional_str(
        _dec_required(execution_data, "actual_model", "execution"),
        "execution.actual_model",
    )
    evaluation_started_at = _dec_optional_str(
        _dec_required(execution_data, "evaluation_started_at", "execution"),
        "execution.evaluation_started_at",
    )
    evaluation_finished_at = _dec_optional_str(
        _dec_required(execution_data, "evaluation_finished_at", "execution"),
        "execution.evaluation_finished_at",
    )

    # -- derived --
    derived_data = _dec_mapping(
        _dec_required(payload, "derived", "top-level"), "derived"
    )
    _check_keys(derived_data, _V2_DERIVED_KEYS, "derived")
    product_evidence_quality = _dec_str_enum(
        ProductEvidenceQuality,
        _dec_required(
            derived_data, "product_evidence_quality", "derived"
        ),
        "derived.product_evidence_quality",
    )
    relationship_authority = _dec_str_enum(
        RelationshipAuthority,
        _dec_required(
            derived_data, "relationship_authority", "derived"
        ),
        "derived.relationship_authority",
    )
    authority_tier = _dec_str_enum(
        AuthorityTier,
        _dec_required(derived_data, "authority_tier", "derived"),
        "derived.authority_tier",
    )
    fired_rules = frozenset(
        _dec_str_enum(
            AuthorityRuleV2, value, f"derived.fired_rules[{i}]"
        )
        for i, value in enumerate(
            _dec_sorted_unique_str_list(
                _dec_required(derived_data, "fired_rules", "derived"),
                "derived.fired_rules",
            )
        )
    )

    # -- integrity --
    integrity_data = _dec_mapping(
        _dec_required(payload, "integrity", "top-level"), "integrity"
    )
    _check_keys(integrity_data, _V2_INTEGRITY_KEYS, "integrity")
    input_digest = _dec_str(
        _dec_required(integrity_data, "input_digest", "integrity"),
        "integrity.input_digest",
        allow_empty=False,
    )
    output_digest = _dec_str(
        _dec_required(integrity_data, "output_digest", "integrity"),
        "integrity.output_digest",
        allow_empty=False,
    )

    # The V2 record constructor re-validates everything (types, coherence,
    # the V2 route pin, the V2 exact contract binding, the strict
    # structured output coherence, digests) and fails closed; any
    # constructor violation is wrapped in the bounded codec error by the
    # caller.
    return SemanticDecisionRecordV2(
        run_id=run_id,
        assessment_index=assessment_index,
        source_url=source_url,
        semantic_contract_version=semantic_contract_version,
        prompt_version=prompt_version,
        input_schema_version=input_schema_version,
        output_schema_version=output_schema_version,
        authority_contract_version=authority_contract_version,
        case=case,
        evaluation_state=evaluation_state,
        decision=decision,
        confidence=confidence,
        reason_code=reason_code,
        conflict_classes=conflict_classes,
        matched_attributes=matched_attributes,
        conflicting_attributes=conflicting_attributes,
        missing_critical_attributes=missing_critical_attributes,
        attempts=attempts,
        fallback_used=fallback_used,
        fallback_reason=fallback_reason,
        error_type=error_type,
        actual_provider=actual_provider,
        actual_model=actual_model,
        evaluation_started_at=evaluation_started_at,
        evaluation_finished_at=evaluation_finished_at,
        product_evidence_quality=product_evidence_quality,
        relationship_authority=relationship_authority,
        authority_tier=authority_tier,
        fired_rules=fired_rules,
        input_digest=input_digest,
        output_digest=output_digest,
    )


# ---------------------------------------------------------------------------
# The V2 pure zero-live replay / reconstruction
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class SemanticDecisionReplayV2:
    """The verified reconstruction of one persisted V2 semantic decision.

    Carries the original record (for provenance), the reconstructed S2-A
    authority inputs (the exact recorded V2 input case is the authority
    input: the deterministic context, the context provenances, and the
    authority-side product evidence), the re-derived authority decision
    (proved to agree with the stored derived audit snapshots), the
    recorded V2 input (from which the exact historical prompt is
    deterministically reconstructable without any live call), and the
    recorded contract binding.
    """

    record: SemanticDecisionRecordV2
    identity_context: IdentityStateAssessmentV2
    semantic_evaluation: SemanticEvaluationV2
    context_provenances: frozenset[ContextProvenance]
    product_evidence: ProductEvidenceProfileV2
    product_evidence_quality: ProductEvidenceQuality
    relationship_requirement: RelationshipRequirement
    relationship_authority: RelationshipAuthority
    authority_decision: AuthorityDecisionV2
    case: SemanticMatchCaseV2
    contract_binding: tuple[str, str, int, int, str]


def reconstruct_identity_context_v2(
    record: SemanticDecisionRecordV2,
) -> IdentityStateAssessmentV2:
    """Reconstruct the deterministic V2 context from the persisted V2
    record's exact recorded input. The frozen V2 constructor re-validates
    the recorded state / sub-state / signal combination (fail closed):
    a context that is not a legitimate S2-A context cannot be
    reconstructed."""
    case = record.case
    return IdentityStateAssessmentV2(
        state=case.identity_state,
        substate=case.substate,
        relationship_signals=case.relationship_signals,
        normalized_requested_part_number=(
            case.normalized_requested_part_number
        ),
        normalized_candidate_part_number=(
            case.normalized_candidate_part_number
        ),
    )


def reconstruct_semantic_evaluation_v2(
    record: SemanticDecisionRecordV2,
) -> SemanticEvaluationV2:
    """Reconstruct the exact historical V2 semantic evaluation.

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


def _v2_contract_binding(
    record: SemanticDecisionRecordV2,
) -> tuple[str, str, int, int, str]:
    return (
        record.semantic_contract_version,
        record.prompt_version,
        record.input_schema_version,
        record.output_schema_version,
        record.authority_contract_version,
    )


def _replay_v2_record(record: object) -> SemanticDecisionReplayV2:
    """The V2 adapter's zero-live replay of one V2 record.

    Steps (each fails closed with ``SemanticDecisionReplayError``):

    1. **V2 exact-binding gate.** The record's exact
       (semantic contract, prompt, input schema, output schema,
       authority contract) binding must be the one the V2 adapter knows
       (``V2_CONTRACT_BINDING``). Anything else is refused explicitly —
       never silently reinterpreted, and never replayed "as if" the
       current V2 constants applied.
    2. **Reconstruction.** The historical evaluation, the V2 context,
       the context provenances, and the authority-side product evidence
       are reconstructed from the EXACT recorded V2 input (constructor-
       validated).
    3. **Re-derivation under the bound authority contract.** The S2-A
       derivation is re-run on the reconstructed inputs: relationship
       requirement, product evidence quality, relationship authority,
       and the authority decision (tier + fired rules, no human
       overlay — the overlay is a later workflow concern, not part of
       the evaluation).
    4. **Derived-agreement proof.** Every stored derived audit snapshot
       must EXACTLY agree with the re-derivation. Agreement proves the
       artifact was produced under the bound contract and is
       untampered; disagreement (or a derivation that fails closed on
       the recorded inputs) is a ``SemanticDecisionReplayError``.

    Performs zero live AI calls and zero provider/network calls: the
    recorded values are re-read and re-derived, never re-requested.
    """
    if not isinstance(record, SemanticDecisionRecordV2):
        raise TypeError(
            "the V2 replay adapter expects a SemanticDecisionRecordV2, "
            f"got {type(record).__name__}"
        )
    binding = _v2_contract_binding(record)
    if binding not in (V2_CONTRACT_BINDING,):
        raise SemanticDecisionReplayError(
            "unsupported contract binding "
            f"(semantic contract {binding[0]!r}, prompt {binding[1]!r}, "
            f"input schema {binding[2]}, output schema {binding[3]}, "
            f"authority contract {binding[4]!r}); the V2 adapter cannot "
            "safely replay it and refuses to reinterpret a historical "
            "decision under a contract it does not know"
        )

    case = record.case
    try:
        identity_context = reconstruct_identity_context_v2(record)
        semantic_evaluation = reconstruct_semantic_evaluation_v2(record)
        product_evidence = case.product_evidence
        context_provenances = case.context_provenances

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
    if requirement is not case.relationship_requirement:
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

    return SemanticDecisionReplayV2(
        record=record,
        identity_context=identity_context,
        semantic_evaluation=semantic_evaluation,
        context_provenances=context_provenances,
        product_evidence=product_evidence,
        product_evidence_quality=quality,
        relationship_requirement=requirement,
        relationship_authority=relationship_authority,
        authority_decision=authority_decision,
        case=case,
        contract_binding=binding,
    )


def replay_v2_record(record: SemanticDecisionRecordV2) -> SemanticDecisionReplayV2:
    """Public V2 replay entry (delegates to the adapter implementation)."""
    return _replay_v2_record(record)


def _v2_run_binding_violation(
    record: object,
    *,
    request_mpn: str,
    request_description: str,
) -> str | None:
    """The V2-specific run-binding check: the recorded V2 input's target
    MPN / description must equal the run's canonical request. Returns a
    bounded violation message, or None when the binding holds. (The
    universal parts — the row exists, the digest verifies, the recorded
    index is in range, and the recorded source URL matches the run's
    persisted assessment at that index — are checked by the persistence
    service.)"""
    if not isinstance(record, SemanticDecisionRecordV2):
        raise TypeError(
            "the V2 run-binding check expects a SemanticDecisionRecordV2, "
            f"got {type(record).__name__}"
        )
    if (
        record.case.target.mpn != request_mpn
        or (record.case.target.description_raw_text or "")
        != (request_description or "")
    ):
        return (
            "the record's request identity does not match the run's "
            "canonical request; the artifact does not bind to this run"
        )
    return None


# ---------------------------------------------------------------------------
# The registered V2 adapter (the second entry of the universal registry)
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class SemanticV2ContractAdapter(SemanticDecisionContractAdapter):
    """The registered adapter for the final Semantic V2 contract
    (envelope schema version 1, semantic contract V2)."""

    def encode(self, record: object) -> dict[str, object]:
        return encode_v2_payload(record)

    def decode(self, payload: dict[str, object]) -> SemanticDecisionRecordV2:
        return _decode_v2_payload(payload)

    def replay(self, record: object) -> SemanticDecisionReplayV2:
        return _replay_v2_record(record)

    def run_binding_violation(
        self,
        record: object,
        *,
        request_mpn: str,
        request_description: str,
    ) -> str | None:
        return _v2_run_binding_violation(
            record,
            request_mpn=request_mpn,
            request_description=request_description,
        )


SEMANTIC_V2_ADAPTER: Final[SemanticV2ContractAdapter] = (
    SemanticV2ContractAdapter(
        envelope_schema_version=1,
        semantic_contract_version=SEMANTIC_CONTRACT_VERSION_V2,
        supported_bindings=(V2_CONTRACT_BINDING,),
        record_type=SemanticDecisionRecordV2,
    )
)
