"""The persisted semantic-decision artifact (S2-B).

PRODUCT-INTEL.SEMANTIC-AUTHORITY-V2-S2-B introduces a first-class, immutable,
versioned artifact — ``SemanticDecisionRecord`` — that records the COMPLETE
semantic evaluation / provenance for one candidate assessment of one research
run, for ALL semantic outcomes:

* ``EVALUATED`` with decision MATCH / NO_MATCH / UNCERTAIN (with or without
  the fallback provider), and
* ``RUNTIME_FAILURE`` (primary-only or both-providers), and
* ``NOT_EVALUATED`` (an entry-point candidate for which no semantic call was
  made; the deterministic state governs).

What this module is
-------------------

A pure, stdlib-only research-layer contract. It defines:

* the artifact value object and its bounded runtime-provenance vocabulary
  (attempt roles / outcomes, failure classes, fallback reasons — mirrored,
  independent of the production semantic runtime, exactly as
  ``V2SemanticDecision`` mirrors the frozen V1 decision vocabulary: the pure
  research layer never imports the runtime, and the mirror is drift-pinned by
  tests);
* the exact contract-version binding the artifact records
  (semantic contract version, prompt version, input/output schema versions,
  authority contract version);
* canonical section encodings and the self-verifying input/output digests.

The versioned CODEC (``research/semantic_decision_codec.py``) turns the
artifact into the opaque persisted payload and back. The pure REPLAY /
reconstruction path (``research/semantic_decision_replay.py``) verifies the
artifact and re-derives the frozen S2-A authority inputs under the bound
contract version. Persistence (the ``runs.SemanticDecisionRecord`` row and
the execution-layer service) stores the opaque payload; it does not
interpret it.

Persisted vs re-derived
-----------------------

The artifact stores the SOURCE INPUTS (binding, contract versions, V2
deterministic context, product-evidence profile, context provenances, the
recorded prompt input, the recorded semantic output, the recorded runtime
provenance) and a small set of DERIVED AUDIT SNAPSHOTS (relationship
requirement, product evidence quality, relationship authority, authority
tier, fired rules). The derived snapshots are strictly re-derivable from the
stored inputs under the bound authority contract version; they are persisted
because they serve tamper/audit needs (a reviewer sees exactly what the
frozen contract produced at evaluation time), and the replay path MUST prove
stored and re-derived values agree (they are not silently reinterpreted).

Nothing float-valued is stored. No clock is read. No I/O is performed. The
record is a ledger entry about a semantic evaluation that already happened;
it grants no authority by itself and changes no production behavior in S2-B
(nothing writes or reads it yet — live execution wiring is S2-C).

Relationship to ``AiAssistedReviewCandidate``
---------------------------------------------

``SemanticDecisionRecord`` is the semantic EXECUTION / PROVENANCE LEDGER
(one record per assessed entry-point candidate, immutable after creation,
all outcomes). ``AiAssistedReviewCandidate`` is the HUMAN-REVIEW WORKFLOW
artifact (MATCH outcomes only, mutable review state, forged-confirmation
protections). They share the narrow explicit (run, assessment_index) stable
binding and deliberately reference NEITHER each other's rows: a NO_MATCH /
UNCERTAIN / failure outcome has no review candidate and must still be
ledgered; a review state never mutates the ledger.
"""

from __future__ import annotations

import hashlib
import json
import re
import uuid
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Final

from product_intelligence.research import (
    AuthorityRuleV2,
    AuthorityTier,
    ConflictClass,
    ConflictSubstateV2,
    ContextProvenance,
    IdentityRelationshipSignal,
    IdentityStateAssessmentV2,
    IdentityStateV2,
    ProductEvidenceProfileV2,
    ProductEvidenceQuality,
    RelationshipAuthority,
    RelationshipRequirement,
    SemanticEvaluationStateV2,
    UncertainSubstateV2,
    UnevaluableSubstateV2,
    V2Confidence,
    V2SemanticDecision,
    VerifiedSubstateV2,
)

__all__ = [
    "AttemptOutcome",
    "AttemptRole",
    "AUTHORITY_CONTRACT_VERSION",
    "CanonicalDigestError",
    "FALLBACK_PROVIDER_V1",
    "FALLBACK_MODEL_V1",
    "PRIMARY_PROVIDER_V1",
    "PRIMARY_MODEL_V1",
    "PROMPT_VERSION_V1",
    "SEMANTIC_CONTRACT_VERSION",
    "SEMANTIC_INPUT_SCHEMA_VERSION",
    "SEMANTIC_OUTPUT_SCHEMA_VERSION",
    "SemanticDecisionAttempt",
    "SemanticDecisionRecord",
    "SemanticFallbackReason",
    "SemanticFailureClass",
    "SemanticPromptInput",
    "canonical_sha256",
    "record_input_digest",
    "record_output_digest",
]


# ---------------------------------------------------------------------------
# Contract-version binding (S2-B artifact v1)
# ---------------------------------------------------------------------------

SEMANTIC_CONTRACT_VERSION: Final[str] = "V1"
"""The frozen FU3A production semantic contract under which the recorded
evaluation happened: pinned primary/fallback route, fallback-on-execution-
failure-only policy, prompt v1.1, strict response parser. An artifact bound
to any other semantic contract version is outside this schema and fails
closed (it is never silently reinterpreted)."""

PROMPT_VERSION_V1: Final[str] = "1.1"
"""The exact frozen prompt version of the bound semantic contract V1
(mirrors the production semantic contract; drift-pinned by tests)."""

SEMANTIC_INPUT_SCHEMA_VERSION: Final[int] = 1
"""Version of the recorded prompt-input section (the case fields the prompt
renderer consumes). The artifact's own codec-owned shape, not the model's."""

SEMANTIC_OUTPUT_SCHEMA_VERSION: Final[int] = 1
"""Version of the recorded semantic-output section (decision / confidence /
bounded attributes / reason code)."""

AUTHORITY_CONTRACT_VERSION: Final[str] = "SEMANTIC_AUTHORITY_V2_S2A_FU2"
"""The identity of the Semantic Authority Contract V2 AS FROZEN THROUGH
S2-A-FU2 — the exact contract under which the derived audit snapshots in the
artifact were produced. Replay re-derives under the current frozen S2-A
module and requires exact agreement with the stored snapshots; a future
authority contract version is explicitly refused (never silently
reinterpreted)."""

# The frozen FU3A pinned production route (mirrored; drift-pinned by tests).
# An artifact bound to semantic contract V1 records attempts that followed
# this exact route — any other provider/model in a V1-bound record is a
# contract violation and fails closed.
PRIMARY_PROVIDER_V1: Final[str] = "amax"
PRIMARY_MODEL_V1: Final[str] = "qwen3.8-27b"
FALLBACK_PROVIDER_V1: Final[str] = "vllm-262k"
FALLBACK_MODEL_V1: Final[str] = "Qwen3.6-27B-262K"


# ---------------------------------------------------------------------------
# Bounded runtime-provenance vocabulary (mirrors of the frozen FU3A runtime)
# ---------------------------------------------------------------------------


class AttemptRole(str, Enum):
    """The route role of one provider attempt."""

    PRIMARY = "PRIMARY"
    FALLBACK = "FALLBACK"


#: The attempt-number -> role binding (runtime routing: primary first, the
#: fallback second). Frozen entry tuple, no mutable state.
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
    """Bounded outcome of one provider attempt.

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
    """Bounded final failure classification of one semantic evaluation.

    Mirrors the frozen production semantic runtime's error-type vocabulary
    (independent of it; drift-pinned by tests). No raw exception text and no
    provider-specific message ever appears in an artifact.
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

    # Fallback attempt failures (no third provider exists).
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


#: Bounded failure families per attempt count (the artifact's own
#: consistency rules, mirroring the runtime's routing contract at value
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
    """Why the fallback provider was entered (every member is an EXECUTION
    failure of the primary attempt; semantic disagreement has no member).

    Mirrors the frozen production semantic runtime's fallback-reason
    vocabulary (independent of it; drift-pinned by tests).
    """

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
# Canonical encoding + digests
# ---------------------------------------------------------------------------

_TIMESTAMP_PATTERN = re.compile(
    r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(\.\d{1,6})?Z$"
)
_DIGEST_PATTERN = re.compile(r"^[0-9a-f]{64}$")


class CanonicalDigestError(ValueError):
    """A section value cannot be canonically encoded (not JSON-native)."""


def canonical_sha256(value: object) -> str:
    """SHA-256 hex digest of the canonical JSON encoding of ``value``.

    Canonical encoding: sorted mapping keys, compact separators, ASCII.
    The value must be JSON-native (dict / list / str / int / bool / None) —
    this function refuses anything else rather than silently formatting it,
    and refuses floats outright (no float authority data).
    """
    _assert_json_native(value, "<canonical>")
    encoded = json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=True
    )
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()


def _assert_json_native(value: object, path: str) -> None:
    if value is None or isinstance(value, (str, bool)):
        return
    if isinstance(value, float):
        raise CanonicalDigestError(
            f"{path}: float values are not permitted in the canonical "
            "encoding (no float authority data, no lossy serialization)"
        )
    if isinstance(value, int):
        return
    if isinstance(value, dict):
        for key, item in value.items():
            if not isinstance(key, str):
                raise CanonicalDigestError(
                    f"{path}: mapping keys must be str, got "
                    f"{type(key).__name__}"
                )
            _assert_json_native(item, f"{path}.{key}")
        return
    if isinstance(value, (list, tuple)):
        for i, item in enumerate(value):
            _assert_json_native(item, f"{path}[{i}]")
        return
    raise CanonicalDigestError(
        f"{path}: value of type {type(value).__name__} is not JSON-native"
    )


def _validate_timestamp(value: str | None, path: str) -> None:
    """Strict ISO-8601 UTC 'Z' instant grammar (microsecond precision)."""
    if value is None:
        return
    if not isinstance(value, str):
        raise TypeError(f"{path} must be str or None")
    if not _TIMESTAMP_PATTERN.match(value):
        raise ValueError(
            f"{path}: must be an ISO-8601 UTC instant ending in 'Z' "
            f"('YYYY-MM-DDTHH:MM:SS[.ffffff]Z'), got {value!r}"
        )
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ValueError(
            f"{path}: not a valid calendar instant: {value!r}"
        ) from None
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise ValueError(f"{path}: must be a timezone-aware UTC instant")


def _validate_digest(value: str, path: str) -> None:
    if not isinstance(value, str) or not _DIGEST_PATTERN.match(value):
        raise ValueError(
            f"{path}: must be a 64-character lowercase hex SHA-256 digest"
        )


def _validate_str(
    value: object, path: str, *, allow_empty: bool = True
) -> None:
    if not isinstance(value, str):
        raise TypeError(f"{path} must be str, got {type(value).__name__}")
    if not allow_empty and not value:
        raise ValueError(f"{path} must be non-empty")


def _validate_str_tuple(value: object, path: str) -> None:
    if not isinstance(value, tuple):
        raise TypeError(f"{path} must be a tuple, got {type(value).__name__}")
    for i, item in enumerate(value):
        if not isinstance(item, str):
            raise TypeError(f"{path}[{i}] must be str, got {type(item).__name__}")


# ---------------------------------------------------------------------------
# Canonical section encodings (shared by the record, the digests, the codec)
# ---------------------------------------------------------------------------


def _binding_section(
    run_id: str, assessment_index: int, source_url: str
) -> dict[str, object]:
    return {
        "run_id": run_id,
        "assessment_index": assessment_index,
        "source_url": source_url,
    }


def _contract_section() -> dict[str, object]:
    """The schema-v1 contract binding (frozen; see module constants)."""
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
    """The recorded prompt case fields of one semantic evaluation.

    These are the EXACT inputs the bound prompt version renders (semantic
    contract V1, prompt v1.1): from them the historical prompt is
    deterministically reconstructable without any live call. Nullable
    candidate fields are recorded as ``None`` (absent), never as a
    defaulted sentinel string.
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
# One recorded provider attempt
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class SemanticDecisionAttempt:
    """One provider attempt of the recorded evaluation, in call order.

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
# The artifact
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class SemanticDecisionRecord:
    """One complete, immutable semantic decision / provenance ledger entry
    for one candidate assessment of one research run (S2-B).

    Sections
    --------

    * **binding** — run identity, the assessment's stable position in the
      run's ordered assessment tuple, and the listing source URL;
    * **contract** — the exact semantic / prompt / input / output /
      authority contract versions under which the evaluation happened and
      the derived snapshots were produced (replay refuses any binding it
      does not know);
    * **context** — the deterministic V2 context (state, sub-state,
      relationship signals, normalized keys) plus the derived
      relationship-requirement snapshot;
    * **product_evidence** — the bounded product-evidence profile plus the
      derived quality snapshot;
    * **prompt_input** — the exact recorded prompt case fields;
    * **evaluation** — the recorded semantic output (evaluation state,
      decision, confidence, structured conflict classes, bounded reason
      code, recorded attribute lists);
    * **execution** — the recorded runtime provenance (attempts in call
      order, fallback use/reason, bounded failure class, actual
      provider/model, evaluation instants);
    * **derived** — the derived audit snapshots (relationship authority,
      authority tier, fired rules) under the bound authority contract
      version; replay proves they agree with re-derivation;
    * **integrity** — self-verifying input/output section digests.

    The ledger records an entry-point candidate: under the bound authority
    contract, only ``DETERMINISTIC_UNCERTAIN`` contexts are semantic entry
    points, so any other context fails closed here.

    The record stores no float, reads no clock, performs no I/O, and grants
    no authority: it is a record of what happened, verifiable under the
    bound contract versions.
    """

    # -- binding ------------------------------------------------------------
    run_id: str
    assessment_index: int
    source_url: str

    # -- contract binding -----------------------------------------------------
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

    # -- recorded prompt input ---------------------------------------------------
    case_id: str
    target_mpn: str
    target_description: str
    candidate_title: str
    candidate_mpn_field: str | None
    candidate_sku: str | None
    candidate_specs: str | None
    evidence_source: str

    # -- recorded semantic output -------------------------------------------------
    evaluation_state: SemanticEvaluationStateV2
    decision: V2SemanticDecision | None
    confidence: V2Confidence | None
    conflict_classes: frozenset[ConflictClass]
    reason_code: str | None
    matched_attributes: tuple[str, ...]
    conflicting_attributes: tuple[str, ...]
    missing_critical_attributes: tuple[str, ...]

    # -- recorded runtime provenance ------------------------------------------------
    attempts: tuple[SemanticDecisionAttempt, ...]
    fallback_used: bool
    fallback_reason: SemanticFallbackReason | None
    error_type: SemanticFailureClass | None
    actual_provider: str | None
    actual_model: str | None
    evaluation_started_at: str | None
    evaluation_finished_at: str | None

    # -- derived audit snapshots (replay proves agreement) -----------------------------
    relationship_authority: RelationshipAuthority
    authority_tier: AuthorityTier
    fired_rules: frozenset[AuthorityRuleV2]

    # -- integrity -----------------------------------------------------------------------
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

    # -- binding ------------------------------------------------------------------

    def _validate_binding(self) -> None:
        _validate_str(self.run_id, "run_id", allow_empty=False)
        try:
            parsed_run = uuid.UUID(self.run_id)
        except ValueError:
            raise ValueError(
                f"run_id must be a canonical UUID string, got {self.run_id!r}"
            ) from None
        if str(parsed_run) != self.run_id:
            raise ValueError(
                f"run_id must be in canonical UUID form, got {self.run_id!r}"
            )
        if isinstance(self.assessment_index, bool) or not isinstance(
            self.assessment_index, int
        ):
            raise TypeError(
                "assessment_index must be int, "
                f"got {type(self.assessment_index).__name__}"
            )
        if self.assessment_index < 0:
            raise ValueError(
                f"assessment_index must be >= 0, got {self.assessment_index}"
            )
        _validate_str(self.source_url, "source_url", allow_empty=False)

    # -- contract binding -----------------------------------------------------------

    def _validate_contract_binding(self) -> None:
        # Schema v1 is bound to exactly one known contract tuple. Anything
        # else is outside this artifact's safe-replay envelope and fails
        # closed at construction (never silently reinterpreted).
        if self.semantic_contract_version != SEMANTIC_CONTRACT_VERSION:
            raise ValueError(
                "semantic_contract_version must be "
                f"{SEMANTIC_CONTRACT_VERSION!r} for schema v1, got "
                f"{self.semantic_contract_version!r}; an artifact bound to "
                "another semantic contract is outside this schema and fails "
                "closed"
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

    # -- evaluation + execution coherence -----------------------------------------------------

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
        # Role / number / route pinning (semantic contract V1 = the frozen
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

    # -- derived snapshots (types only; agreement is replay's job) ---------------------------

    def _validate_derived_types(self) -> None:
        if not self.fired_rules:
            raise ValueError(
                "an authority decision must record at least one fired rule"
            )

    # -- integrity self-verification -------------------------------------------------------------

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

    # -- section accessors (shared by the codec and the digest functions) -------------------------

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

    # -- construction convenience ---------------------------------------------------------------

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
    ) -> "SemanticDecisionRecord":
        """Build a record, computing the self-verifying section digests.

        The contract binding is the schema-v1 frozen one (semantic contract
        V1, prompt v1.1, input/output schema v1, authority contract
        S2-A-FU2): the builder takes no version parameters so a v1 artifact
        cannot be bound to a contract this artifact does not know.
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


def record_input_digest(record: SemanticDecisionRecord) -> str:
    """SHA-256 over the canonical encoding of the record's INPUT sections:
    binding + contract + context + product evidence + recorded prompt
    input (everything that feeds the semantic evaluation and the S2-A
    authority derivation)."""
    return canonical_sha256(
        {
            "binding": record.binding_section(),
            "contract": record.contract_section(),
            "context": record.context_section(),
            "product_evidence": record.product_evidence_section(),
            "prompt_input": record.prompt_input().canonical(),
        }
    )


def record_output_digest(record: SemanticDecisionRecord) -> str:
    """SHA-256 over the canonical encoding of the record's OUTPUT sections:
    recorded semantic evaluation + recorded execution provenance + derived
    audit snapshots (everything the evaluation produced)."""
    return canonical_sha256(
        {
            "evaluation": record.evaluation_section(),
            "execution": record.execution_section(),
            "derived": record.derived_section(),
        }
    )
