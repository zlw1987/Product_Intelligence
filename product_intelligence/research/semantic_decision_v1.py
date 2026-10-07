"""The Semantic V1 contract adapter (S2-B / S2-B-FU1).

PRODUCT-INTEL.SEMANTIC-AUTHORITY-V2-S2-B-FU1 moved every Semantic V1
assumption out of the universal persistence envelope and into this
version-specific adapter — the FIRST registered adapter, kept because it is
useful for tests and demonstrates the architecture. This module owns, and
ONLY this module owns:

* the V1 contract identity: semantic contract ``V1`` (the frozen FU3A
  production semantic contract), prompt ``1.1``, recorded prompt-input
  schema version 1, recorded semantic-output schema version 1, authority
  contract ``SEMANTIC_AUTHORITY_V2_S2A_FU2`` — the exact tuple
  ``V1_CONTRACT_BINDING``; anything else is outside this adapter and fails
  closed (never silently reinterpreted);
* the V1 pinned runtime route: ``amax`` / ``qwen3.8-27b`` primary and
  ``vllm-262k`` / ``Qwen3.6-27B-262K`` fallback — a V1 contract rule, not a
  persistence-envelope invariant (a future semantic contract may pin a
  different qualified route without redesigning the envelope);
* the V1 bounded runtime-provenance vocabulary (attempt roles / outcomes,
  failure classes, fallback reasons — mirrors of the frozen FU3A runtime,
  drift-pinned by tests; the pure research layer never imports the runtime);
* the V1 recorded prompt-input shape (``SemanticPromptInput`` — the exact
  V1 case fields, from which the historical prompt is deterministically
  reconstructable without any live call);
* the V1 typed record (``SemanticDecisionRecordV1``) with the V1 exact
  binding check, the V1 route pin, the S2-A context validation, the
  evaluation/execution coherence rules, and the self-verifying section
  digests;
* the V1 payload codec (the exact V1 section shapes; strict, fail closed);
* the V1 zero-live replay (reconstruction + re-derivation under the frozen
  S2-A module + the derived-agreement proof);
* the V1 run-binding check (the recorded prompt-input request identity must
  equal the run's canonical request).

The universal parts — the envelope framing (payload schema version +
binding + contract dispatch key), the adapter registry and dispatch, the
row-level tamper anchor, the persistence service — live in
``semantic_decision_record.py`` / ``semantic_decision_codec.py`` /
``semantic_decision_replay.py`` and the runs/execution layers, and they own
no V1 provider/model/prompt assumption.

This module is pure research-layer contract: stdlib + the research package's
public export surface only; no Django, no I/O, no clock, no float authority
data, no network, no production semantic-runtime import.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Final

from product_intelligence.research import (
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
    SemanticEvaluationStateV2,
    SemanticEvaluationV2,
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
    _validate_str_tuple,
    _validate_timestamp,
    canonical_sha256,
)

__all__ = [
    "AUTHORITY_CONTRACT_VERSION",
    "FALLBACK_MODEL_V1",
    "FALLBACK_PROVIDER_V1",
    "PRIMARY_MODEL_V1",
    "PRIMARY_PROVIDER_V1",
    "PROMPT_VERSION_V1",
    "SEMANTIC_CONTRACT_VERSION",
    "SEMANTIC_INPUT_SCHEMA_VERSION",
    "SEMANTIC_OUTPUT_SCHEMA_VERSION",
    "SEMANTIC_V1_ADAPTER",
    "SemanticDecisionAttempt",
    "SemanticDecisionReplay",
    "SemanticDecisionRecordV1",
    "SemanticFallbackReason",
    "SemanticFailureClass",
    "SemanticPromptInput",
    "SemanticV1ContractAdapter",
    "AttemptOutcome",
    "AttemptRole",
    "V1_CONTRACT_BINDING",
    "encode_v1_payload",
    "record_input_digest",
    "record_output_digest",
    "reconstruct_identity_context",
    "reconstruct_semantic_evaluation",
    "replay_v1_record",
]


# ---------------------------------------------------------------------------
# The V1 contract identity (owned by THIS adapter, not by the envelope)
# ---------------------------------------------------------------------------

SEMANTIC_CONTRACT_VERSION: Final[str] = "V1"
"""The frozen FU3A production semantic contract this adapter interprets:
pinned primary/fallback route, fallback-on-execution-failure-only policy,
prompt v1.1, strict response parser. A payload bound to any other semantic
contract version is outside this adapter (the universal dispatch refuses it
when no adapter is registered for it; this adapter additionally never
interprets a non-V1 payload)."""

PROMPT_VERSION_V1: Final[str] = "1.1"
"""The exact frozen prompt version of the V1 semantic contract (mirrors the
production semantic contract; drift-pinned by tests)."""

SEMANTIC_INPUT_SCHEMA_VERSION: Final[int] = 1
"""Version of the V1 recorded prompt-input section (the case fields the
prompt renderer consumes)."""

SEMANTIC_OUTPUT_SCHEMA_VERSION: Final[int] = 1
"""Version of the V1 recorded semantic-output section (decision /
confidence / bounded attributes / reason code)."""

AUTHORITY_CONTRACT_VERSION: Final[str] = "SEMANTIC_AUTHORITY_V2_S2A_FU2"
"""The identity of the Semantic Authority Contract V2 AS FROZEN THROUGH
S2-A-FU2 — the exact contract under which the derived audit snapshots in a
V1 artifact were produced. The V1 replay re-derives under the current
frozen S2-A module and requires exact agreement with the stored snapshots;
a future authority contract version is explicitly refused (never silently
reinterpreted)."""

#: The EXACT contract binding this adapter interprets and replays:
#: (semantic contract, prompt, input schema, output schema, authority
#: contract). One entry. A future binding is a future adapter — never an
#: implicit reinterpretation of this one.
V1_CONTRACT_BINDING: Final[tuple[str, str, int, int, str]] = (
    SEMANTIC_CONTRACT_VERSION,
    PROMPT_VERSION_V1,
    SEMANTIC_INPUT_SCHEMA_VERSION,
    SEMANTIC_OUTPUT_SCHEMA_VERSION,
    AUTHORITY_CONTRACT_VERSION,
)

# The frozen FU3A pinned production route (mirrored; drift-pinned by
# tests). A V1-bound record's attempts followed this exact route — any
# other provider/model in a V1 record is a V1 contract violation and fails
# closed. This is a rule of the V1 semantic contract, NOT an invariant of
# the persistence envelope: a future semantic contract may pin another
# qualified route.
PRIMARY_PROVIDER_V1: Final[str] = "amax"
PRIMARY_MODEL_V1: Final[str] = "qwen3.8-27b"
FALLBACK_PROVIDER_V1: Final[str] = "vllm-262k"
FALLBACK_MODEL_V1: Final[str] = "Qwen3.6-27B-262K"


# ---------------------------------------------------------------------------
# Bounded runtime-provenance vocabulary (V1 mirrors of the frozen FU3A runtime)
# ---------------------------------------------------------------------------


class AttemptRole(str, Enum):
    """The route role of one provider attempt (V1 routing: primary first,
    the fallback second)."""

    PRIMARY = "PRIMARY"
    FALLBACK = "FALLBACK"


#: The attempt-number -> role binding (V1 runtime routing). Frozen entry
#: tuple, no mutable state.
_ATTEMPT_NUMBER_TO_ROLE: Final[tuple[tuple[int, AttemptRole], ...]] = (
    (1, AttemptRole.PRIMARY),
    (2, AttemptRole.FALLBACK),
)


def _role_for_attempt_number(attempt_number: int) -> AttemptRole:
    for number, role in _ATTEMPT_NUMBER_TO_ROLE:
        if number == attempt_number:
            return role
    raise ValueError(f"no role for attempt number {attempt_number}")


class AttemptOutcome(str, Enum):
    """Bounded outcome of one provider attempt (V1).

    Mirrors the frozen production semantic runtime's attempt-status
    vocabulary (independent of it, exactly as ``V2SemanticDecision``
    mirrors the frozen V1 decision vocabulary): the pure research layer
    does not import the runtime. The mirror is drift-pinned by
    ``tests/research/test_semantic_decision_boundaries.py``.
    """

    OK = "OK"
    TIMEOUT = "TIMEOUT"
    DNS_ERROR = "DNS_ERROR"
    TLS_ERROR = "TLS_ERROR"
    CONNECTION_ERROR = "CONNECTION_ERROR"
    RATE_LIMITED = "RATE_LIMITED"
    HTTP_ERROR = "HTTP_ERROR"
    AUTHENTICATION_FAILED = "AUTHENTICATION_FAILED"
    MODEL_NOT_FOUND = "MODEL_NOT_FOUND"
    PROVIDER_UNAVAILABLE = "PROVIDER_UNAVAILABLE"
    PROVIDER_NOT_CONFIGURED = "PROVIDER_NOT_CONFIGURED"
    INVALID_REQUEST_CONFIGURATION = "INVALID_REQUEST_CONFIGURATION"
    UNSUPPORTED_PARAMETER = "UNSUPPORTED_PARAMETER"
    EMPTY_RESPONSE = "EMPTY_RESPONSE"
    MALFORMED_JSON = "MALFORMED_JSON"
    SCHEMA_INVALID = "SCHEMA_INVALID"
    INVALID_RESPONSE = "INVALID_RESPONSE"
    MODEL_IDENTITY_MISMATCH = "MODEL_IDENTITY_MISMATCH"
    CASE_REJECTED = "CASE_REJECTED"
    UNKNOWN_ERROR = "UNKNOWN_ERROR"


class SemanticFailureClass(str, Enum):
    """Bounded final failure classification of one V1 semantic evaluation.

    Mirrors the frozen production semantic runtime's error-type vocabulary
    (independent of it; drift-pinned by tests). No raw exception text and
    no provider-specific message ever appears in an artifact.
    """

    # Primary attempt failures.
    PRIMARY_TIMEOUT = "PRIMARY_TIMEOUT"
    PRIMARY_CONNECTION_ERROR = "PRIMARY_CONNECTION_ERROR"
    PRIMARY_RATE_LIMITED = "PRIMARY_RATE_LIMITED"
    PRIMARY_HTTP_ERROR = "PRIMARY_HTTP_ERROR"
    PRIMARY_AUTHENTICATION_FAILED = "PRIMARY_AUTHENTICATION_FAILED"
    PRIMARY_MODEL_NOT_FOUND = "PRIMARY_MODEL_NOT_FOUND"
    PRIMARY_PROVIDER_UNAVAILABLE = "PRIMARY_PROVIDER_UNAVAILABLE"
    PRIMARY_INVALID_RESPONSE = "PRIMARY_INVALID_RESPONSE"
    PRIMARY_EMPTY_RESPONSE = "PRIMARY_EMPTY_RESPONSE"
    PRIMARY_MALFORMED_JSON = "PRIMARY_MALFORMED_JSON"
    PRIMARY_SCHEMA_INVALID = "PRIMARY_SCHEMA_INVALID"
    PRIMARY_MODEL_IDENTITY_MISMATCH = "PRIMARY_MODEL_IDENTITY_MISMATCH"
    PRIMARY_INVALID_REQUEST_CONFIGURATION = "PRIMARY_INVALID_REQUEST_CONFIGURATION"
    PRIMARY_UNSUPPORTED_PARAMETER = "PRIMARY_UNSUPPORTED_PARAMETER"
    PRIMARY_CASE_REJECTED = "PRIMARY_CASE_REJECTED"
    PRIMARY_UNKNOWN_ERROR = "PRIMARY_UNKNOWN_ERROR"

    # Fallback attempt failures (no third provider exists in the V1 route).
    FALLBACK_TIMEOUT = "FALLBACK_TIMEOUT"
    FALLBACK_CONNECTION_ERROR = "FALLBACK_CONNECTION_ERROR"
    FALLBACK_RATE_LIMITED = "FALLBACK_RATE_LIMITED"
    FALLBACK_HTTP_ERROR = "FALLBACK_HTTP_ERROR"
    FALLBACK_AUTHENTICATION_FAILED = "FALLBACK_AUTHENTICATION_FAILED"
    FALLBACK_MODEL_NOT_FOUND = "FALLBACK_MODEL_NOT_FOUND"
    FALLBACK_PROVIDER_UNAVAILABLE = "FALLBACK_PROVIDER_UNAVAILABLE"
    FALLBACK_INVALID_RESPONSE = "FALLBACK_INVALID_RESPONSE"
    FALLBACK_EMPTY_RESPONSE = "FALLBACK_EMPTY_RESPONSE"
    FALLBACK_MALFORMED_JSON = "FALLBACK_MALFORMED_JSON"
    FALLBACK_SCHEMA_INVALID = "FALLBACK_SCHEMA_INVALID"
    FALLBACK_MODEL_IDENTITY_MISMATCH = "FALLBACK_MODEL_IDENTITY_MISMATCH"
    FALLBACK_CASE_REJECTED = "FALLBACK_CASE_REJECTED"
    FALLBACK_UNKNOWN_ERROR = "FALLBACK_UNKNOWN_ERROR"

    # Local configuration errors (fail closed, never fallback).
    CONFIG_INVALID = "CONFIG_INVALID"
    PROVIDER_NOT_CONFIGURED = "PROVIDER_NOT_CONFIGURED"

    # Both providers attempted, neither produced an accepted response.
    BOTH_UNAVAILABLE = "BOTH_UNAVAILABLE"


#: Bounded failure families per attempt count (the V1 record's own
#: consistency rules, mirroring the V1 runtime's routing contract at value
#: level): a one-attempt failure is classified by the PRIMARY family (or a
#: local configuration error); a two-attempt failure is classified by the
#: FALLBACK family (or BOTH_UNAVAILABLE).
_ONE_ATTEMPT_FAILURE_CLASSES: Final[frozenset[SemanticFailureClass]] = frozenset(
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

_TWO_ATTEMPT_FAILURE_CLASSES: Final[frozenset[SemanticFailureClass]] = frozenset(
    {
        SemanticFailureClass.BOTH_UNAVAILABLE,
    }
    | {
        member
        for member in SemanticFailureClass
        if member.value.startswith("FALLBACK_")
    }
)


class SemanticFallbackReason(str, Enum):
    """Why the V1 fallback provider was entered (every member is an
    EXECUTION failure of the primary attempt; semantic disagreement has no
    member). Mirrors the frozen production semantic runtime's fallback-
    reason vocabulary (independent of it; drift-pinned by tests)."""

    NONE = "NONE"
    TIMEOUT = "TIMEOUT"
    DNS_ERROR = "DNS_ERROR"
    TLS_ERROR = "TLS_ERROR"
    CONNECTION_ERROR = "CONNECTION_ERROR"
    RATE_LIMITED = "RATE_LIMITED"
    HTTP_ERROR = "HTTP_ERROR"
    AUTHENTICATION_FAILED = "AUTHENTICATION_FAILED"
    MODEL_NOT_FOUND = "MODEL_NOT_FOUND"
    PROVIDER_UNAVAILABLE = "PROVIDER_UNAVAILABLE"
    EMPTY_RESPONSE = "EMPTY_RESPONSE"
    MALFORMED_JSON = "MALFORMED_JSON"
    SCHEMA_INVALID = "SCHEMA_INVALID"
    INVALID_RESPONSE = "INVALID_RESPONSE"
    MODEL_IDENTITY_MISMATCH = "MODEL_IDENTITY_MISMATCH"


# ---------------------------------------------------------------------------
# V1 section encodings (the exact V1 payload shapes)
# ---------------------------------------------------------------------------


def _contract_section() -> dict[str, object]:
    """The V1 contract binding section (frozen; see module constants)."""
    return {
        "semantic_contract_version": SEMANTIC_CONTRACT_VERSION,
        "prompt_version": PROMPT_VERSION_V1,
        "input_schema_version": SEMANTIC_INPUT_SCHEMA_VERSION,
        "output_schema_version": SEMANTIC_OUTPUT_SCHEMA_VERSION,
        "authority_contract_version": AUTHORITY_CONTRACT_VERSION,
    }


def _context_section(
    identity_state: IdentityStateV2,
    substate: (
        VerifiedSubstateV2
        | UncertainSubstateV2
        | ConflictSubstateV2
        | UnevaluableSubstateV2
    ),
    relationship_signals: frozenset[IdentityRelationshipSignal],
    normalized_requested_part_number: str,
    normalized_candidate_part_number: str,
    relationship_requirement: RelationshipRequirement,
    context_provenances: frozenset[ContextProvenance],
) -> dict[str, object]:
    return {
        "identity_state": identity_state.value,
        "substate": substate.value,
        "relationship_signals": sorted(
            signal.value for signal in relationship_signals
        ),
        "normalized_requested_part_number": normalized_requested_part_number,
        "normalized_candidate_part_number": normalized_candidate_part_number,
        "relationship_requirement": relationship_requirement.value,
        "context_provenances": sorted(
            provenance.value for provenance in context_provenances
        ),
    }


def _product_evidence_section(
    profile: ProductEvidenceProfileV2,
    quality: ProductEvidenceQuality,
) -> dict[str, object]:
    return {
        "profile": {
            "has_usable_product_title": profile.has_usable_product_title,
            "matched_facts": sorted(
                (
                    {
                        "dimension": fact.dimension.value,
                        "sources": sorted(
                            source.value for source in fact.sources
                        ),
                    }
                    for fact in profile.matched_facts
                ),
                key=lambda fact: (fact["dimension"], fact["sources"]),
            ),
        },
        "quality": quality.value,
    }


def _evaluation_section(
    evaluation_state: SemanticEvaluationStateV2,
    decision: V2SemanticDecision | None,
    confidence: V2Confidence | None,
    conflict_classes: frozenset[ConflictClass],
    reason_code: str | None,
    matched_attributes: tuple[str, ...],
    conflicting_attributes: tuple[str, ...],
    missing_critical_attributes: tuple[str, ...],
) -> dict[str, object]:
    return {
        "evaluation_state": evaluation_state.value,
        "decision": decision.value if decision is not None else None,
        "confidence": confidence.value if confidence is not None else None,
        "conflict_classes": sorted(
            conflict.value for conflict in conflict_classes
        ),
        "reason_code": reason_code,
        "matched_attributes": list(matched_attributes),
        "conflicting_attributes": list(conflicting_attributes),
        "missing_critical_attributes": list(missing_critical_attributes),
    }


def _execution_section(
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
        "fallback_reason": fallback_reason.value
        if fallback_reason is not None
        else None,
        "error_type": error_type.value if error_type is not None else None,
        "actual_provider": actual_provider,
        "actual_model": actual_model,
        "evaluation_started_at": evaluation_started_at,
        "evaluation_finished_at": evaluation_finished_at,
    }


def _derived_section(
    relationship_authority: RelationshipAuthority,
    authority_tier: AuthorityTier,
    fired_rules: frozenset[AuthorityRuleV2],
) -> dict[str, object]:
    return {
        "relationship_authority": relationship_authority.value,
        "authority_tier": authority_tier.value,
        "fired_rules": sorted(rule.value for rule in fired_rules),
    }


# ---------------------------------------------------------------------------
# Recorded prompt input (the exact V1 semantic case fields)
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class SemanticPromptInput:
    """The recorded prompt case fields of one V1 semantic evaluation.

    These are the EXACT inputs the V1 prompt renders (semantic contract
    V1, prompt v1.1): from them the historical prompt is deterministically
    reconstructable without any live call. Nullable candidate fields are
    recorded as ``None`` (absent), never as a defaulted sentinel string.
    """

    case_id: str
    target_mpn: str
    target_description: str
    candidate_title: str
    candidate_mpn_field: str | None
    candidate_sku: str | None
    candidate_specs: str | None
    evidence_source: str

    def __post_init__(self) -> None:
        _validate_str(self.case_id, "case_id", allow_empty=False)
        _validate_str(self.target_mpn, "target_mpn")
        _validate_str(self.target_description, "target_description")
        _validate_str(self.candidate_title, "candidate_title")
        if self.candidate_mpn_field is not None:
            _validate_str(self.candidate_mpn_field, "candidate_mpn_field")
        if self.candidate_sku is not None:
            _validate_str(self.candidate_sku, "candidate_sku")
        if self.candidate_specs is not None:
            _validate_str(self.candidate_specs, "candidate_specs")
        _validate_str(self.evidence_source, "evidence_source", allow_empty=False)

    def canonical(self) -> dict[str, object]:
        return {
            "case_id": self.case_id,
            "target_mpn": self.target_mpn,
            "target_description": self.target_description,
            "candidate_title": self.candidate_title,
            "candidate_mpn_field": self.candidate_mpn_field,
            "candidate_sku": self.candidate_sku,
            "candidate_specs": self.candidate_specs,
            "evidence_source": self.evidence_source,
        }


# ---------------------------------------------------------------------------
# One recorded V1 provider attempt
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class SemanticDecisionAttempt:
    """One provider attempt of a recorded V1 evaluation, in call order.

    Carries the bounded outcome only — no latency, no raw body, no
    exception text, no credential.
    """

    role: AttemptRole
    attempt_number: int
    provider: str
    model: str
    outcome: AttemptOutcome

    def __post_init__(self) -> None:
        if not isinstance(self.role, AttemptRole):
            raise TypeError(
                f"role must be AttemptRole, got {type(self.role).__name__}"
            )
        if isinstance(self.attempt_number, bool) or not isinstance(
            self.attempt_number, int
        ):
            raise TypeError("attempt_number must be int")
        if self.attempt_number not in (1, 2):
            raise ValueError(
                "attempt_number must be 1 (primary) or 2 (fallback); "
                f"got {self.attempt_number}"
            )
        _validate_str(self.provider, "provider", allow_empty=False)
        _validate_str(self.model, "model", allow_empty=False)
        if not isinstance(self.outcome, AttemptOutcome):
            raise TypeError(
                "outcome must be AttemptOutcome, "
                f"got {type(self.outcome).__name__}"
            )
        if self.role is not _role_for_attempt_number(self.attempt_number):
            raise ValueError(
                f"role {self.role.value} is inconsistent with attempt "
                f"number {self.attempt_number}"
            )

    def canonical(self) -> dict[str, object]:
        return {
            "role": self.role.value,
            "attempt_number": self.attempt_number,
            "provider": self.provider,
            "model": self.model,
            "outcome": self.outcome.value,
        }


# ---------------------------------------------------------------------------
# The V1 typed record (the version-owned artifact of the V1 contract)
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class SemanticDecisionRecordV1:
    """One complete, immutable Semantic V1 decision / provenance artifact
    for one candidate assessment of one research run (S2-B).

    This is the V1 contract adapter's typed record — the FIRST registered
    semantic contract, NOT the universal persistence schema. The universal
    envelope (the runs row + the payload framing: envelope schema version,
    binding, contract identity, integrity anchor) is contract-agnostic;
    every version-specific rule of this record — the exact V1 contract
    binding, the V1 pinned route, the V1 section shapes, the V1 digest
    layout — is a rule of the V1 semantic contract owned by this adapter.

    Sections
    --------

    * **binding** — the universal persistence binding (run identity, the
      assessment's stable position in the run's ordered assessment tuple,
      the listing source URL);
    * **contract** — the EXACT V1 semantic / prompt / input / output /
      authority contract versions under which the evaluation happened and
      the derived snapshots were produced (the V1 adapter refuses any
      other binding);
    * **context** — the deterministic V2 context (state, sub-state,
      relationship signals, normalized keys) plus the derived
      relationship-requirement snapshot;
    * **product_evidence** — the bounded product-evidence profile plus the
      derived quality snapshot;
    * **prompt_input** — the exact recorded V1 prompt case fields;
    * **evaluation** — the recorded V1 semantic output (evaluation state,
      decision, confidence, structured conflict classes, bounded reason
      code, recorded attribute lists);
    * **execution** — the recorded V1 runtime provenance (attempts in call
      order on the pinned V1 route, fallback use/reason, bounded failure
      class, actual provider/model, evaluation instants);
    * **derived** — the derived audit snapshots (relationship authority,
      authority tier, fired rules) under the bound authority contract
      version; replay proves they agree with re-derivation;
    * **integrity** — self-verifying input/output section digests.

    The ledger records an entry-point candidate: under the bound authority
    contract, only ``DETERMINISTIC_UNCERTAIN`` contexts are semantic entry
    points, so any other context fails closed here.

    The record stores no float, reads no clock, performs no I/O, and grants
    no authority: it is a record of what happened, verifiable under the
    V1 contract binding.
    """

    # -- universal binding (envelope-level addressing) -------------------------
    run_id: str
    assessment_index: int
    source_url: str

    # -- V1 contract binding (adapter-owned identity) ---------------------------
    semantic_contract_version: str
    prompt_version: str
    input_schema_version: int
    output_schema_version: int
    authority_contract_version: str

    # -- deterministic V2 context (source inputs) ------------------------------
    identity_state: IdentityStateV2
    substate: (
        VerifiedSubstateV2
        | UncertainSubstateV2
        | ConflictSubstateV2
        | UnevaluableSubstateV2
    )
    relationship_signals: frozenset[IdentityRelationshipSignal]
    normalized_requested_part_number: str
    normalized_candidate_part_number: str
    relationship_requirement: RelationshipRequirement  # derived audit snapshot

    # -- product evidence (source inputs) ---------------------------------------
    product_evidence: ProductEvidenceProfileV2
    product_evidence_quality: ProductEvidenceQuality  # derived audit snapshot

    # -- context provenance (source inputs) ------------------------------------
    context_provenances: frozenset[ContextProvenance]

    # -- recorded V1 prompt input -------------------------------------------------
    case_id: str
    target_mpn: str
    target_description: str
    candidate_title: str
    candidate_mpn_field: str | None
    candidate_sku: str | None
    candidate_specs: str | None
    evidence_source: str

    # -- recorded V1 semantic output -----------------------------------------------
    evaluation_state: SemanticEvaluationStateV2
    decision: V2SemanticDecision | None
    confidence: V2Confidence | None
    conflict_classes: frozenset[ConflictClass]
    reason_code: str | None
    matched_attributes: tuple[str, ...]
    conflicting_attributes: tuple[str, ...]
    missing_critical_attributes: tuple[str, ...]

    # -- recorded V1 runtime provenance ---------------------------------------------
    attempts: tuple[SemanticDecisionAttempt, ...]
    fallback_used: bool
    fallback_reason: SemanticFallbackReason | None
    error_type: SemanticFailureClass | None
    actual_provider: str | None
    actual_model: str | None
    evaluation_started_at: str | None
    evaluation_finished_at: str | None

    # -- derived audit snapshots (replay proves agreement) ---------------------------
    relationship_authority: RelationshipAuthority
    authority_tier: AuthorityTier
    fired_rules: frozenset[AuthorityRuleV2]

    # -- integrity ---------------------------------------------------------------------
    input_digest: str
    output_digest: str

    def __post_init__(self) -> None:
        self._validate_types()
        self._validate_binding()
        self._validate_contract_binding()
        self._validate_context()
        self._validate_evaluation_and_execution()
        self._validate_derived_types()
        self._validate_digests()

    # -- type validation ------------------------------------------------------------

    def _validate_types(self) -> None:
        if not isinstance(self.identity_state, IdentityStateV2):
            raise TypeError(
                "identity_state must be IdentityStateV2, "
                f"got {type(self.identity_state).__name__}"
            )
        substate_type = type(self.substate)
        if substate_type not in (
            VerifiedSubstateV2,
            UncertainSubstateV2,
            ConflictSubstateV2,
            UnevaluableSubstateV2,
        ):
            raise TypeError(
                "substate must be a V2 sub-state enum member, "
                f"got {substate_type.__name__}"
            )
        if not isinstance(self.relationship_signals, frozenset):
            raise TypeError(
                "relationship_signals must be a frozenset, "
                f"got {type(self.relationship_signals).__name__}"
            )
        for signal in self.relationship_signals:
            if not isinstance(signal, IdentityRelationshipSignal):
                raise TypeError(
                    "relationship_signals must contain only "
                    f"IdentityRelationshipSignal members, got {signal!r}"
                )
        _validate_str(
            self.normalized_requested_part_number,
            "normalized_requested_part_number",
        )
        _validate_str(
            self.normalized_candidate_part_number,
            "normalized_candidate_part_number",
        )
        if not isinstance(
            self.relationship_requirement, RelationshipRequirement
        ):
            raise TypeError(
                "relationship_requirement must be RelationshipRequirement, "
                f"got {type(self.relationship_requirement).__name__}"
            )
        if not isinstance(self.product_evidence, ProductEvidenceProfileV2):
            raise TypeError(
                "product_evidence must be ProductEvidenceProfileV2, "
                f"got {type(self.product_evidence).__name__}"
            )
        if not isinstance(
            self.product_evidence_quality, ProductEvidenceQuality
        ):
            raise TypeError(
                "product_evidence_quality must be ProductEvidenceQuality, "
                f"got {type(self.product_evidence_quality).__name__}"
            )
        if not isinstance(self.context_provenances, frozenset):
            raise TypeError(
                "context_provenances must be a frozenset, "
                f"got {type(self.context_provenances).__name__}"
            )
        for provenance in self.context_provenances:
            if not isinstance(provenance, ContextProvenance):
                raise TypeError(
                    "context_provenances must contain only ContextProvenance "
                    f"members, got {provenance!r}"
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
        if self.reason_code is not None:
            _validate_str(self.reason_code, "reason_code", allow_empty=False)
        _validate_str_tuple(self.matched_attributes, "matched_attributes")
        _validate_str_tuple(
            self.conflicting_attributes, "conflicting_attributes"
        )
        _validate_str_tuple(
            self.missing_critical_attributes, "missing_critical_attributes"
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

    # -- V1 contract binding (the adapter's exact pin) ------------------------------

    def _validate_contract_binding(self) -> None:
        # The V1 adapter interprets exactly one contract binding. Anything
        # else is outside this adapter's safe-replay envelope and fails
        # closed at construction (never silently reinterpreted).
        if self.semantic_contract_version != SEMANTIC_CONTRACT_VERSION:
            raise ValueError(
                "semantic_contract_version must be "
                f"{SEMANTIC_CONTRACT_VERSION!r} for this V1 record, got "
                f"{self.semantic_contract_version!r}; an artifact bound to "
                "another semantic contract is outside the V1 adapter and "
                "fails closed"
            )
        if self.prompt_version != PROMPT_VERSION_V1:
            raise ValueError(
                "prompt_version must be "
                f"{PROMPT_VERSION_V1!r} for semantic contract "
                f"{SEMANTIC_CONTRACT_VERSION}, got {self.prompt_version!r}"
            )
        for name, value, expected in (
            (
                "input_schema_version",
                self.input_schema_version,
                SEMANTIC_INPUT_SCHEMA_VERSION,
            ),
            (
                "output_schema_version",
                self.output_schema_version,
                SEMANTIC_OUTPUT_SCHEMA_VERSION,
            ),
        ):
            if isinstance(value, bool) or not isinstance(value, int):
                raise TypeError(
                    f"{name} must be int, got {type(value).__name__}"
                )
            if value != expected:
                raise ValueError(
                    f"{name} must be {expected} for schema v1, got {value}"
                )
        if self.authority_contract_version != AUTHORITY_CONTRACT_VERSION:
            raise ValueError(
                "authority_contract_version must be "
                f"{AUTHORITY_CONTRACT_VERSION!r} for schema v1, got "
                f"{self.authority_contract_version!r}; the derived audit "
                "snapshots of this artifact were produced under the exact "
                "bound authority contract, and no other"
            )

    # -- deterministic V2 context ------------------------------------------------------

    def _validate_context(self) -> None:
        # The recorded context must be a legitimate S2-A context: the
        # frozen V2 constructor validates state/sub-state consistency, the
        # exactly-one primary signal rule, and per-sub-state signal
        # permission (fail closed).
        IdentityStateAssessmentV2(
            state=self.identity_state,
            substate=self.substate,
            relationship_signals=self.relationship_signals,
            normalized_requested_part_number=(
                self.normalized_requested_part_number
            ),
            normalized_candidate_part_number=(
                self.normalized_candidate_part_number
            ),
        )
        # Only semantic entry points are ledgered.
        if self.identity_state is not IdentityStateV2.DETERMINISTIC_UNCERTAIN:
            raise ValueError(
                "a semantic decision record covers a semantic entry point: "
                "the bound authority contract admits only "
                f"{IdentityStateV2.DETERMINISTIC_UNCERTAIN.value} contexts; "
                f"got {self.identity_state.value}"
            )

    # -- evaluation + execution coherence (V1 route pin lives here) ------------------

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
                (
                    "evaluation_started_at",
                    self.evaluation_started_at,
                ),
                (
                    "evaluation_finished_at",
                    self.evaluation_finished_at,
                ),
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
        # Role / number / route pinning (V1 semantic contract = the frozen
        # pinned route; the attempts are recorded in call order).
        for i, attempt in enumerate(self.attempts):
            if attempt.attempt_number != i + 1:
                raise ValueError(
                    f"attempts[{i}].attempt_number must be {i + 1} "
                    f"(call order), got {attempt.attempt_number}"
                )
            if i == 0:
                if (
                    attempt.provider != PRIMARY_PROVIDER_V1
                    or attempt.model != PRIMARY_MODEL_V1
                ):
                    raise ValueError(
                        "the primary attempt of a V1-bound record must be "
                        f"the pinned primary {PRIMARY_PROVIDER_V1}/"
                        f"{PRIMARY_MODEL_V1}, got {attempt.provider}/"
                        f"{attempt.model}"
                    )
            else:
                if (
                    attempt.provider != FALLBACK_PROVIDER_V1
                    or attempt.model != FALLBACK_MODEL_V1
                ):
                    raise ValueError(
                        "the fallback attempt of a V1-bound record must be "
                        f"the pinned fallback {FALLBACK_PROVIDER_V1}/"
                        f"{FALLBACK_MODEL_V1}, got {attempt.provider}/"
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
            # Success: a decision with confidence, an OK final attempt, and
            # provenance attributed to exactly that attempt.
            if self.decision is None or self.confidence is None:
                raise ValueError(
                    "EVALUATED requires both a decision and a confidence"
                )
            if self.error_type is not None:
                raise ValueError(
                    "EVALUATED may not carry an error_type; the evaluation "
                    "produced an accepted response"
                )
            if self.reason_code is None:
                raise ValueError(
                    "EVALUATED requires the recorded bounded reason code"
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
        else:  # RUNTIME_FAILURE
            # Failure: never shaped like a decision (a runtime failure is
            # NEVER interpreted as NO_MATCH or anything else evidence-shaped).
            if self.decision is not None or self.confidence is not None:
                raise ValueError(
                    "RUNTIME_FAILURE may not carry a decision or confidence; "
                    "a runtime failure is never interpreted as NO_MATCH"
                )
            if self.reason_code is not None:
                raise ValueError(
                    "RUNTIME_FAILURE may not carry a reason code"
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
                _ONE_ATTEMPT_FAILURE_CLASSES
                if attempt_count == 1
                else _TWO_ATTEMPT_FAILURE_CLASSES
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
        expected_input = record_input_digest(self)
        expected_output = record_output_digest(self)
        if self.input_digest != expected_input:
            raise ValueError(
                "input_digest does not agree with the record's input "
                "sections (binding, contract, context, product evidence, "
                "prompt input); the artifact is corrupt or was built with "
                "the wrong digest"
            )
        if self.output_digest != expected_output:
            raise ValueError(
                "output_digest does not agree with the record's output "
                "sections (evaluation, execution, derived); the artifact "
                "is corrupt or was built with the wrong digest"
            )

    # -- section accessors (shared by the V1 codec and the digest functions) ----------

    def prompt_input(self) -> SemanticPromptInput:
        return SemanticPromptInput(
            case_id=self.case_id,
            target_mpn=self.target_mpn,
            target_description=self.target_description,
            candidate_title=self.candidate_title,
            candidate_mpn_field=self.candidate_mpn_field,
            candidate_sku=self.candidate_sku,
            candidate_specs=self.candidate_specs,
            evidence_source=self.evidence_source,
        )

    def binding_section(self) -> dict[str, object]:
        return _binding_section(
            self.run_id, self.assessment_index, self.source_url
        )

    def contract_section(self) -> dict[str, object]:
        return _contract_section()

    def context_section(self) -> dict[str, object]:
        return _context_section(
            self.identity_state,
            self.substate,
            self.relationship_signals,
            self.normalized_requested_part_number,
            self.normalized_candidate_part_number,
            self.relationship_requirement,
            self.context_provenances,
        )

    def product_evidence_section(self) -> dict[str, object]:
        return _product_evidence_section(
            self.product_evidence, self.product_evidence_quality
        )

    def evaluation_section(self) -> dict[str, object]:
        return _evaluation_section(
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
        return _execution_section(
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
        return _derived_section(
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
        identity_state: IdentityStateV2,
        substate: (
            VerifiedSubstateV2
            | UncertainSubstateV2
            | ConflictSubstateV2
            | UnevaluableSubstateV2
        ),
        relationship_signals: frozenset[IdentityRelationshipSignal],
        normalized_requested_part_number: str,
        normalized_candidate_part_number: str,
        relationship_requirement: RelationshipRequirement,
        product_evidence: ProductEvidenceProfileV2,
        product_evidence_quality: ProductEvidenceQuality,
        context_provenances: frozenset[ContextProvenance],
        case_id: str,
        target_mpn: str,
        target_description: str,
        candidate_title: str,
        candidate_mpn_field: str | None,
        candidate_sku: str | None,
        candidate_specs: str | None,
        evidence_source: str,
        evaluation_state: SemanticEvaluationStateV2,
        decision: V2SemanticDecision | None,
        confidence: V2Confidence | None,
        conflict_classes: frozenset[ConflictClass],
        reason_code: str | None,
        matched_attributes: tuple[str, ...],
        conflicting_attributes: tuple[str, ...],
        missing_critical_attributes: tuple[str, ...],
        attempts: tuple[SemanticDecisionAttempt, ...],
        fallback_used: bool,
        fallback_reason: SemanticFallbackReason | None,
        error_type: SemanticFailureClass | None,
        actual_provider: str | None,
        actual_model: str | None,
        evaluation_started_at: str | None,
        evaluation_finished_at: str | None,
        relationship_authority: RelationshipAuthority,
        authority_tier: AuthorityTier,
        fired_rules: frozenset[AuthorityRuleV2],
    ) -> "SemanticDecisionRecordV1":
        """Build a V1 record, computing the self-verifying section digests.

        The contract binding is the V1 frozen one (semantic contract V1,
        prompt v1.1, input/output schema v1, authority contract S2-A-FU2):
        the builder takes no version parameters so a V1 artifact cannot be
        bound to a contract this adapter does not know.
        """
        input_digest = canonical_sha256(
            {
                "binding": _binding_section(
                    run_id, assessment_index, source_url
                ),
                "contract": _contract_section(),
                "context": _context_section(
                    identity_state,
                    substate,
                    relationship_signals,
                    normalized_requested_part_number,
                    normalized_candidate_part_number,
                    relationship_requirement,
                    context_provenances,
                ),
                "product_evidence": _product_evidence_section(
                    product_evidence, product_evidence_quality
                ),
                "prompt_input": SemanticPromptInput(
                    case_id=case_id,
                    target_mpn=target_mpn,
                    target_description=target_description,
                    candidate_title=candidate_title,
                    candidate_mpn_field=candidate_mpn_field,
                    candidate_sku=candidate_sku,
                    candidate_specs=candidate_specs,
                    evidence_source=evidence_source,
                ).canonical(),
            }
        )
        output_digest = canonical_sha256(
            {
                "evaluation": _evaluation_section(
                    evaluation_state,
                    decision,
                    confidence,
                    conflict_classes,
                    reason_code,
                    matched_attributes,
                    conflicting_attributes,
                    missing_critical_attributes,
                ),
                "execution": _execution_section(
                    attempts,
                    fallback_used,
                    fallback_reason,
                    error_type,
                    actual_provider,
                    actual_model,
                    evaluation_started_at,
                    evaluation_finished_at,
                ),
                "derived": _derived_section(
                    relationship_authority, authority_tier, fired_rules
                ),
            }
        )
        return cls(
            run_id=run_id,
            assessment_index=assessment_index,
            source_url=source_url,
            semantic_contract_version=SEMANTIC_CONTRACT_VERSION,
            prompt_version=PROMPT_VERSION_V1,
            input_schema_version=SEMANTIC_INPUT_SCHEMA_VERSION,
            output_schema_version=SEMANTIC_OUTPUT_SCHEMA_VERSION,
            authority_contract_version=AUTHORITY_CONTRACT_VERSION,
            identity_state=identity_state,
            substate=substate,
            relationship_signals=relationship_signals,
            normalized_requested_part_number=normalized_requested_part_number,
            normalized_candidate_part_number=normalized_candidate_part_number,
            relationship_requirement=relationship_requirement,
            product_evidence=product_evidence,
            product_evidence_quality=product_evidence_quality,
            context_provenances=context_provenances,
            case_id=case_id,
            target_mpn=target_mpn,
            target_description=target_description,
            candidate_title=candidate_title,
            candidate_mpn_field=candidate_mpn_field,
            candidate_sku=candidate_sku,
            candidate_specs=candidate_specs,
            evidence_source=evidence_source,
            evaluation_state=evaluation_state,
            decision=decision,
            confidence=confidence,
            conflict_classes=conflict_classes,
            reason_code=reason_code,
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
            relationship_authority=relationship_authority,
            authority_tier=authority_tier,
            fired_rules=fired_rules,
            input_digest=input_digest,
            output_digest=output_digest,
        )


def record_input_digest(record: SemanticDecisionRecordV1) -> str:
    """SHA-256 over the canonical encoding of the V1 record's INPUT
    sections: binding + contract + context + product evidence + recorded
    V1 prompt input (everything that feeds the semantic evaluation and the
    S2-A authority derivation)."""
    return canonical_sha256(
        {
            "binding": record.binding_section(),
            "contract": record.contract_section(),
            "context": record.context_section(),
            "product_evidence": record.product_evidence_section(),
            "prompt_input": record.prompt_input().canonical(),
        }
    )


def record_output_digest(record: SemanticDecisionRecordV1) -> str:
    """SHA-256 over the canonical encoding of the V1 record's OUTPUT
    sections: recorded V1 semantic evaluation + recorded V1 execution
    provenance + derived audit snapshots (everything the evaluation
    produced)."""
    return canonical_sha256(
        {
            "evaluation": record.evaluation_section(),
            "execution": record.execution_section(),
            "derived": record.derived_section(),
        }
    )


# ---------------------------------------------------------------------------
# The V1 payload codec (the exact V1 section shapes; strict, fail closed)
# ---------------------------------------------------------------------------


_V1_TOP_LEVEL_KEYS: Final[frozenset[str]] = frozenset(
    {
        "schema_version",
        "binding",
        "contract",
        "context",
        "product_evidence",
        "prompt_input",
        "evaluation",
        "execution",
        "derived",
        "integrity",
    }
)

_V1_CONTRACT_KEYS: Final[frozenset[str]] = frozenset(
    {
        "semantic_contract_version",
        "prompt_version",
        "input_schema_version",
        "output_schema_version",
        "authority_contract_version",
    }
)

_V1_CONTEXT_KEYS: Final[frozenset[str]] = frozenset(
    {
        "identity_state",
        "substate",
        "relationship_signals",
        "normalized_requested_part_number",
        "normalized_candidate_part_number",
        "relationship_requirement",
        "context_provenances",
    }
)

_V1_PRODUCT_EVIDENCE_KEYS: Final[frozenset[str]] = frozenset(
    {"profile", "quality"}
)

_V1_PROFILE_KEYS: Final[frozenset[str]] = frozenset(
    {"has_usable_product_title", "matched_facts"}
)

_V1_FACT_KEYS: Final[frozenset[str]] = frozenset({"dimension", "sources"})

_V1_PROMPT_INPUT_KEYS: Final[frozenset[str]] = frozenset(
    {
        "case_id",
        "target_mpn",
        "target_description",
        "candidate_title",
        "candidate_mpn_field",
        "candidate_sku",
        "candidate_specs",
        "evidence_source",
    }
)

_V1_EVALUATION_KEYS: Final[frozenset[str]] = frozenset(
    {
        "evaluation_state",
        "decision",
        "confidence",
        "conflict_classes",
        "reason_code",
        "matched_attributes",
        "conflicting_attributes",
        "missing_critical_attributes",
    }
)

_V1_EXECUTION_KEYS: Final[frozenset[str]] = frozenset(
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

_V1_ATTEMPT_KEYS: Final[frozenset[str]] = frozenset(
    {"role", "attempt_number", "provider", "model", "outcome"}
)

_V1_DERIVED_KEYS: Final[frozenset[str]] = frozenset(
    {"relationship_authority", "authority_tier", "fired_rules"}
)

_V1_INTEGRITY_KEYS: Final[frozenset[str]] = frozenset(
    {"input_digest", "output_digest"}
)


def encode_v1_payload(record: SemanticDecisionRecordV1) -> dict[str, object]:
    """Encode a ``SemanticDecisionRecordV1`` into the full framed payload
    (envelope schema version 1).

    The returned dict contains only native JSON types (str, int, bool,
    list, dict, None) — no enum members, no dataclass objects, no floats.
    Set-valued fields are encoded as sorted unique value lists;
    order-significant fields (attempts, attribute lists) keep their order.

    Raises ``TypeError`` if the input is not a V1 record (caller defect).
    """
    if not isinstance(record, SemanticDecisionRecordV1):
        raise TypeError(
            f"expected SemanticDecisionRecordV1, got {type(record).__name__}"
        )
    return {
        "schema_version": 1,
        "binding": record.binding_section(),
        "contract": record.contract_section(),
        "context": record.context_section(),
        "product_evidence": record.product_evidence_section(),
        "prompt_input": record.prompt_input().canonical(),
        "evaluation": record.evaluation_section(),
        "execution": record.execution_section(),
        "derived": record.derived_section(),
        "integrity": record.integrity_section(),
    }


def _dec_v1_attempt(data: dict[str, object], path: str) -> SemanticDecisionAttempt:
    _check_keys(data, _V1_ATTEMPT_KEYS, path)
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


def _dec_v1_fact(data: dict[str, object], path: str) -> ProductEvidenceFactV2:
    _check_keys(data, _V1_FACT_KEYS, path)
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


def _dec_v1_profile(data: dict[str, object], path: str) -> ProductEvidenceProfileV2:
    _check_keys(data, _V1_PROFILE_KEYS, path)
    has_title = _dec_bool(
        _dec_required(data, "has_usable_product_title", path),
        f"{path}.has_usable_product_title",
    )
    facts_raw = _dec_list(_dec_required(data, "matched_facts", path), f"{path}.matched_facts")
    facts: list[ProductEvidenceFactV2] = []
    seen: set[tuple[str, tuple[str, ...]]] = set()
    for i, item in enumerate(facts_raw):
        fact = _dec_v1_fact(_dec_mapping(item, f"{path}.matched_facts[{i}]"), f"{path}.matched_facts[{i}]")
        key = (
            fact.dimension.value,
            tuple(sorted(source.value for source in fact.sources)),
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
# families, so decoding by value is well-defined; the record constructor
# then re-validates the state/sub-state pairing and fails closed).
_SUBSTATE_ENUM_FAMILIES = (
    VerifiedSubstateV2,
    UncertainSubstateV2,
    ConflictSubstateV2,
    UnevaluableSubstateV2,
)


def _dec_v1_substate(raw: object, path: str):
    """Decode a sub-state value across the four frozen V2 families."""
    value = _dec_str(raw, path, allow_empty=False)
    for family in _SUBSTATE_ENUM_FAMILIES:
        for member in family:
            if member.value == value:
                return member
    raise SemanticDecisionCodecError(
        f"{path}: unknown V2 sub-state value {value!r}"
    )


def _decode_v1_payload(payload: dict[str, object]) -> SemanticDecisionRecordV1:
    """Decode a V1-framed payload into a validated V1 record.

    Raises ``SemanticDecisionCodecError`` for any structural violation and
    wraps every record-constructor failure (including the self-verifying
    digest check and the V1 exact-binding check) in the same bounded error.
    """
    _check_keys(payload, _V1_TOP_LEVEL_KEYS, "top-level")

    # -- binding (the universal section; re-validated strictly here) --
    binding = _dec_mapping(_dec_required(payload, "binding", "top-level"), "binding")
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

    # -- contract (the exact frozen V1 binding) --
    contract = _dec_mapping(
        _dec_required(payload, "contract", "top-level"), "contract"
    )
    _check_keys(contract, _V1_CONTRACT_KEYS, "contract")
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

    # -- context --
    context = _dec_mapping(
        _dec_required(payload, "context", "top-level"), "context"
    )
    _check_keys(context, _V1_CONTEXT_KEYS, "context")
    identity_state = _dec_str_enum(
        IdentityStateV2,
        _dec_required(context, "identity_state", "context"),
        "context.identity_state",
    )
    substate = _dec_v1_substate(
        _dec_required(context, "substate", "context"), "context.substate"
    )
    relationship_signals = frozenset(
        _dec_str_enum(
            IdentityRelationshipSignal, value, f"context.relationship_signals[{i}]"
        )
        for i, value in enumerate(
            _dec_sorted_unique_str_list(
                _dec_required(context, "relationship_signals", "context"),
                "context.relationship_signals",
            )
        )
    )
    normalized_requested_part_number = _dec_str(
        _dec_required(
            context, "normalized_requested_part_number", "context"
        ),
        "context.normalized_requested_part_number",
    )
    normalized_candidate_part_number = _dec_str(
        _dec_required(
            context, "normalized_candidate_part_number", "context"
        ),
        "context.normalized_candidate_part_number",
    )
    relationship_requirement = _dec_str_enum(
        RelationshipRequirement,
        _dec_required(context, "relationship_requirement", "context"),
        "context.relationship_requirement",
    )
    context_provenances = frozenset(
        _dec_str_enum(
            ContextProvenance, value, f"context.context_provenances[{i}]"
        )
        for i, value in enumerate(
            _dec_sorted_unique_str_list(
                _dec_required(context, "context_provenances", "context"),
                "context.context_provenances",
            )
        )
    )

    # -- product evidence --
    product_evidence_data = _dec_mapping(
        _dec_required(payload, "product_evidence", "top-level"),
        "product_evidence",
    )
    _check_keys(product_evidence_data, _V1_PRODUCT_EVIDENCE_KEYS, "product_evidence")
    product_evidence = _dec_v1_profile(
        _dec_mapping(
            _dec_required(product_evidence_data, "profile", "product_evidence"),
            "product_evidence.profile",
        ),
        "product_evidence.profile",
    )
    product_evidence_quality = _dec_str_enum(
        ProductEvidenceQuality,
        _dec_required(product_evidence_data, "quality", "product_evidence"),
        "product_evidence.quality",
    )

    # -- V1 prompt input --
    prompt_input_data = _dec_mapping(
        _dec_required(payload, "prompt_input", "top-level"), "prompt_input"
    )
    _check_keys(prompt_input_data, _V1_PROMPT_INPUT_KEYS, "prompt_input")
    case_id = _dec_str(
        _dec_required(prompt_input_data, "case_id", "prompt_input"),
        "prompt_input.case_id",
        allow_empty=False,
    )
    target_mpn = _dec_str(
        _dec_required(prompt_input_data, "target_mpn", "prompt_input"),
        "prompt_input.target_mpn",
    )
    target_description = _dec_str(
        _dec_required(prompt_input_data, "target_description", "prompt_input"),
        "prompt_input.target_description",
    )
    candidate_title = _dec_str(
        _dec_required(prompt_input_data, "candidate_title", "prompt_input"),
        "prompt_input.candidate_title",
    )
    candidate_mpn_field = _dec_optional_str(
        _dec_required(prompt_input_data, "candidate_mpn_field", "prompt_input"),
        "prompt_input.candidate_mpn_field",
    )
    candidate_sku = _dec_optional_str(
        _dec_required(prompt_input_data, "candidate_sku", "prompt_input"),
        "prompt_input.candidate_sku",
    )
    candidate_specs = _dec_optional_str(
        _dec_required(prompt_input_data, "candidate_specs", "prompt_input"),
        "prompt_input.candidate_specs",
    )
    evidence_source = _dec_str(
        _dec_required(prompt_input_data, "evidence_source", "prompt_input"),
        "prompt_input.evidence_source",
        allow_empty=False,
    )

    # -- evaluation --
    evaluation_data = _dec_mapping(
        _dec_required(payload, "evaluation", "top-level"), "evaluation"
    )
    _check_keys(evaluation_data, _V1_EVALUATION_KEYS, "evaluation")
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
    reason_code = _dec_optional_str(
        _dec_required(evaluation_data, "reason_code", "evaluation"),
        "evaluation.reason_code",
    )
    matched_attributes = _dec_str_list(
        _dec_required(evaluation_data, "matched_attributes", "evaluation"),
        "evaluation.matched_attributes",
    )
    conflicting_attributes = _dec_str_list(
        _dec_required(evaluation_data, "conflicting_attributes", "evaluation"),
        "evaluation.conflicting_attributes",
    )
    missing_critical_attributes = _dec_str_list(
        _dec_required(
            evaluation_data, "missing_critical_attributes", "evaluation"
        ),
        "evaluation.missing_critical_attributes",
    )

    # -- execution --
    execution_data = _dec_mapping(
        _dec_required(payload, "execution", "top-level"), "execution"
    )
    _check_keys(execution_data, _V1_EXECUTION_KEYS, "execution")
    attempts_raw = _dec_list(
        _dec_required(execution_data, "attempts", "execution"),
        "execution.attempts",
    )
    attempts = tuple(
        _dec_v1_attempt(_dec_mapping(item, f"execution.attempts[{i}]"), f"execution.attempts[{i}]")
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
    _check_keys(derived_data, _V1_DERIVED_KEYS, "derived")
    relationship_authority = _dec_str_enum(
        RelationshipAuthority,
        _dec_required(derived_data, "relationship_authority", "derived"),
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
    _check_keys(integrity_data, _V1_INTEGRITY_KEYS, "integrity")
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

    # The V1 record constructor re-validates everything (types, coherence,
    # the V1 route pin, the V1 exact contract binding, digests) and fails
    # closed; any constructor violation is wrapped in the bounded codec
    # error by the caller.
    return SemanticDecisionRecordV1(
        run_id=run_id,
        assessment_index=assessment_index,
        source_url=source_url,
        semantic_contract_version=semantic_contract_version,
        prompt_version=prompt_version,
        input_schema_version=input_schema_version,
        output_schema_version=output_schema_version,
        authority_contract_version=authority_contract_version,
        identity_state=identity_state,
        substate=substate,
        relationship_signals=relationship_signals,
        normalized_requested_part_number=normalized_requested_part_number,
        normalized_candidate_part_number=normalized_candidate_part_number,
        relationship_requirement=relationship_requirement,
        product_evidence=product_evidence,
        product_evidence_quality=product_evidence_quality,
        context_provenances=context_provenances,
        case_id=case_id,
        target_mpn=target_mpn,
        target_description=target_description,
        candidate_title=candidate_title,
        candidate_mpn_field=candidate_mpn_field,
        candidate_sku=candidate_sku,
        candidate_specs=candidate_specs,
        evidence_source=evidence_source,
        evaluation_state=evaluation_state,
        decision=decision,
        confidence=confidence,
        conflict_classes=conflict_classes,
        reason_code=reason_code,
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
        relationship_authority=relationship_authority,
        authority_tier=authority_tier,
        fired_rules=fired_rules,
        input_digest=input_digest,
        output_digest=output_digest,
    )


# ---------------------------------------------------------------------------
# The V1 pure zero-live replay / reconstruction
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class SemanticDecisionReplay:
    """The verified reconstruction of one persisted V1 semantic decision.

    Carries the original record (for provenance), the reconstructed S2-A
    authority inputs, the re-derived authority decision (proved to agree
    with the stored derived audit snapshots), and the recorded V1 prompt
    input (from which the exact historical prompt is deterministically
    reconstructable without any live call).
    """

    record: SemanticDecisionRecordV1
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
    record: SemanticDecisionRecordV1,
) -> IdentityStateAssessmentV2:
    """Reconstruct the deterministic V2 context from the persisted V1
    record. The frozen V2 constructor re-validates the recorded state /
    sub-state / signal combination (fail closed): a context that is not a
    legitimate S2-A context cannot be reconstructed."""
    return IdentityStateAssessmentV2(
        state=record.identity_state,
        substate=record.substate,
        relationship_signals=record.relationship_signals,
        normalized_requested_part_number=record.normalized_requested_part_number,
        normalized_candidate_part_number=record.normalized_candidate_part_number,
    )


def reconstruct_semantic_evaluation(
    record: SemanticDecisionRecordV1,
) -> SemanticEvaluationV2:
    """Reconstruct the exact historical V1 semantic evaluation.

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


def _v1_contract_binding(record: SemanticDecisionRecordV1) -> tuple[str, str, int, int, str]:
    return (
        record.semantic_contract_version,
        record.prompt_version,
        record.input_schema_version,
        record.output_schema_version,
        record.authority_contract_version,
    )


def _replay_v1_record(record: object) -> SemanticDecisionReplay:
    """The V1 adapter's zero-live replay of one V1 record.

    Steps (each fails closed with ``SemanticDecisionReplayError``):

    1. **V1 exact-binding gate.** The record's exact
       (semantic contract, prompt, input schema, output schema, authority
       contract) binding must be the one the V1 adapter knows
       (``V1_CONTRACT_BINDING``). Anything else is refused explicitly —
       never silently reinterpreted, and never replayed "as if" the
       current V1 constants applied.
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
    if not isinstance(record, SemanticDecisionRecordV1):
        raise TypeError(
            "the V1 replay adapter expects a SemanticDecisionRecordV1, "
            f"got {type(record).__name__}"
        )
    binding = _v1_contract_binding(record)
    if binding not in (V1_CONTRACT_BINDING,):
        raise SemanticDecisionReplayError(
            "unsupported contract binding "
            f"(semantic contract {binding[0]!r}, prompt {binding[1]!r}, "
            f"input schema {binding[2]}, output schema {binding[3]}, "
            f"authority contract {binding[4]!r}); the V1 adapter cannot "
            "safely replay it and refuses to reinterpret a historical "
            "decision under a contract it does not know"
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


def replay_v1_record(record: SemanticDecisionRecordV1) -> SemanticDecisionReplay:
    """Public V1 replay entry (delegates to the adapter implementation)."""
    return _replay_v1_record(record)


def _v1_run_binding_violation(
    record: object,
    *,
    request_mpn: str,
    request_description: str,
) -> str | None:
    """The V1-specific run-binding check: the recorded V1 prompt-input
    request identity (target MPN / description) must equal the run's
    canonical request. Returns a bounded violation message, or None when
    the binding holds. (The universal parts — the row exists, the digest
    verifies, the recorded index is in range, and the recorded source URL
    matches the run's persisted assessment at that index — are checked by
    the persistence service.)"""
    if not isinstance(record, SemanticDecisionRecordV1):
        raise TypeError(
            "the V1 run-binding check expects a SemanticDecisionRecordV1, "
            f"got {type(record).__name__}"
        )
    if (
        record.target_mpn != request_mpn
        or record.target_description != request_description
    ):
        return (
            "the record's request identity does not match the run's "
            "canonical request; the artifact does not bind to this run"
        )
    return None


# ---------------------------------------------------------------------------
# The registered V1 adapter (the first entry of the universal registry)
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class SemanticV1ContractAdapter(SemanticDecisionContractAdapter):
    """The registered adapter for the Semantic V1 contract (envelope
    schema version 1, semantic contract V1)."""

    def encode(self, record: object) -> dict[str, object]:
        return encode_v1_payload(record)

    def decode(self, payload: dict[str, object]) -> SemanticDecisionRecordV1:
        return _decode_v1_payload(payload)

    def replay(self, record: object) -> SemanticDecisionReplay:
        return _replay_v1_record(record)

    def run_binding_violation(
        self,
        record: object,
        *,
        request_mpn: str,
        request_description: str,
    ) -> str | None:
        return _v1_run_binding_violation(
            record,
            request_mpn=request_mpn,
            request_description=request_description,
        )


SEMANTIC_V1_ADAPTER: Final[SemanticV1ContractAdapter] = (
    SemanticV1ContractAdapter(
        envelope_schema_version=1,
        semantic_contract_version=SEMANTIC_CONTRACT_VERSION,
        supported_bindings=(V1_CONTRACT_BINDING,),
        record_type=SemanticDecisionRecordV1,
    )
)
