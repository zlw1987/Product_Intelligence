"""The Semantic V2 PERF instrumentation contract adapter
(SEMANTIC-V2-PERF Phase 0 — the A1 versioned successor).

PRODUCT-INTEL.SEMANTIC-V2-PERF-PHASE0 registers the bounded
per-attempt performance instrumentation of the production Semantic V2
runtime as a VERSIONED SUCCESSOR of the frozen V2 persistence adapter,
through the codec's explicit version-adapter extension point (the
S2-B-FU1 / Q3-B5-P5 R1 registry precedent). It owns, and ONLY it owns:

* the PERF contract identity: the SAME semantic contract ``V2`` (the
  final S2-C semantic contract — unchanged), the SAME prompt (mirrored
  from the frozen V2 adapter constant), the SAME recorded input schema
  version 1 (the recorded ``SemanticMatchCaseV2`` is byte-identical —
  the input contract does not move), a NEW recorded output schema
  version 2 (the recorded execution provenance gains the bounded
  per-attempt instrumentation: integer-millisecond latency, the
  provider-reported prompt / completion token counts with explicit
  null = unknown, and the bounded finish reason), and the SAME
  authority contract (``SEMANTIC_AUTHORITY_V2_S2A_FU2`` — the
  derivation, the derived audit snapshots, and the explicit
  ``V2_AUTHORITY_QUALIFIED is False`` boundary are unchanged —
  instrumentation grants no authority) — the exact tuple
  ``V2_PERF_CONTRACT_BINDING``; anything else is outside this adapter
  and fails closed (never silently reinterpreted);
* the V2 pinned route mirror (``amax`` / ``qwen3.8-27b`` primary and
  ``vllm-262k`` / ``Qwen3.6-27B-262K`` fallback — imported from the
  frozen V2 adapter, drift-pinned by tests to the V2 runtime): a
  PERF-bound record's attempts followed this exact route;
* the version-neutral transport-provenance value objects REUSED from
  the first registered adapter (``AttemptRole`` / ``AttemptOutcome``);
  the PERF per-attempt record (``SemanticDecisionAttemptPerf``) is the
  V2 recorded attempt (role, number, provider, model, outcome) PLUS
  exactly the three bounded instrumentation fields — no raw response,
  no prompt text, no provider body, no credential, no unbounded
  provider metadata, no float;
* the PERF typed record (``SemanticDecisionRecordV2Perf``) with the
  PERF exact-binding check (output schema 2 — a record bound to any
  other tuple is un-constructible), the V2 route pin, the same V2
  input contract validation, the same strict structured V2 output
  coherence, the same evaluation/execution coherence rules, the same
  derived audit snapshots under the same authority contract, and the
  self-verifying section digests (the input digest covers binding +
  the PERF contract section + case — it is distinct from the
  same-case V2 input digest by exactly the recorded output-schema
  axis; the output digest covers evaluation + the instrumented
  execution section + derived);
* the strict PERF payload codec (the exact PERF section shapes — the
  universal framing + the V2 case / evaluation / derived sections
  byte-identical + the instrumented execution section; fail closed);
* the PERF pure zero-live replay (the same reconstruction + S2-A
  re-derivation + derived-agreement proof the V2 replay performs —
  the instrumentation is provenance, never authority input: the
  replay re-derives over the case / evaluation, exactly as the V2
  replay does);
* the PERF run-binding check (the recorded V2 input's target MPN /
  description must equal the run's canonical request — the same
  check the V2 adapter performs);
* the registered instance ``SEMANTIC_V2_PERF_ADAPTER`` (envelope
  schema 1 — the SAME universal row, NO migration — semantic contract
  V2, supported bindings = (V2_PERF_CONTRACT_BINDING,), record type =
  SemanticDecisionRecordV2Perf), appended to the codec registry AFTER
  the V2 and V2-FU4 adapters (registration order preserved: V1, V2,
  V2-FU4, V2-PERF).

Versioning discipline (the anti-reinterpretation rule, Phase 0):

* HISTORICAL V2 records (output schema 1) decode and replay
  byte-identically through the FROZEN V2 adapter — unchanged, and the
  codec's claim-based dispatch keeps claiming them for that adapter
  alone. The PERF adapter claims ONLY the output-schema-2 binding; a
  V2 payload is refused by it (missing instrumentation keys) and a
  PERF payload is refused by the V2 adapter (unexpected keys + the
  frozen output-schema-1 binding pin) — the two versions never
  reinterpret one another.
* UNAVAILABLE provider telemetry is the EXPLICIT unknown (null),
  never zero and never an invented measurement: a provider that
  reported no usage records ``prompt_tokens: null`` /
  ``completion_tokens: null``; a provider that reported no (or an
  out-of-grammar) finish reason records ``finish_reason: null``.
  Latency is the measured integer-millisecond form (the canonical
  encoding admits no float — sub-millisecond precision is not
  persisted, the nearest whole millisecond is).
* The instrumentation is EVIDENCE-ONLY: it changes no prompt, no
  route identity, no temperature, no max_tokens, no timeout, no
  fallback eligibility, no semantic decision, no authority surface —
  ``V2_PERF_AUTHORITY_QUALIFIED`` mirrors the frozen V2 marker
  (False) and is drift-pinned by tests.

The universal parts — the envelope framing, the adapter registry and
claim-based dispatch, the row-level tamper anchor, the persistence
service, the universal replay dispatch — live in
``semantic_decision_record.py`` / ``semantic_decision_codec.py`` /
``semantic_decision_replay.py`` and the runs/execution layers, and
they own no V2 provider/model/prompt assumption (none of them is
changed by this module — the registry entry is the only additive
touch, in the codec).

This module is pure research-layer contract: stdlib + the research
package's public export surface + the frozen V2 adapter module
(``semantic_decision_v2`` — imported constants / key sets / section
encoders / the case decoder; the frozen module itself is
byte-unchanged) + the envelope foundation only; no Django, no I/O, no
clock, no float authority data, no network, no production
semantic-runtime import (the bounded finish-reason grammar the V2
runtime projects to is mirrored, drift-pinned by tests).
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime
from typing import Final

from product_intelligence.research import (
    AttemptOutcome,
    AttemptRole,
    AuthorityDecisionV2,
    AuthorityRuleV2,
    AuthorityTier,
    ConflictClass,
    ContextProvenance,
    IdentityStateAssessmentV2,
    ProductEvidenceProfileV2,
    ProductEvidenceQuality,
    RelationshipAuthority,
    RelationshipRequirement,
    SemanticAttributeDimensionV2,
    SemanticDecisionAttempt,
    SemanticEvaluationStateV2,
    SemanticEvaluationV2,
    SemanticFallbackReason,
    SemanticFailureClass,
    SemanticMatchCaseV2,
    SemanticReasonCodeV2,
    V2Confidence,
    V2SemanticDecision,
    derive_authority_tier,
    derive_product_evidence_quality,
    derive_relationship_authority,
    substate_relationship_requirement,
)
from product_intelligence.research.semantic_decision_record import (
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
    _validate_binding_fields,
    _validate_digest,
    _validate_str,
    _validate_timestamp,
    canonical_sha256,
)
from product_intelligence.research.semantic_decision_v2 import (
    AUTHORITY_CONTRACT_VERSION_V2,
    FALLBACK_MODEL_V2,
    FALLBACK_PROVIDER_V2,
    PRIMARY_MODEL_V2,
    PRIMARY_PROVIDER_V2,
    PROMPT_VERSION_V2,
    SEMANTIC_CONTRACT_VERSION_V2,
    SEMANTIC_INPUT_SCHEMA_VERSION_V2,
    V2_AUTHORITY_QUALIFIED,
    _V2_CONTRACT_KEYS,
    _V2_DERIVED_KEYS,
    _V2_EVALUATION_KEYS,
    _V2_EXECUTION_KEYS,
    _V2_INTEGRITY_KEYS,
    _V2_ONE_ATTEMPT_FAILURE_CLASSES,
    _V2_TOP_LEVEL_KEYS,
    _V2_TWO_ATTEMPT_FAILURE_CLASSES,
    _dec_v2_attribute_list,
    _dec_v2_case,
    _v2_derived_section,
    _v2_evaluation_section,
)
from product_intelligence.research.semantic_v2 import (
    SemanticAttributeV2,
    SemanticMatchResponseV2,
)

__all__ = [
    "AUTHORITY_CONTRACT_VERSION_V2_PERF",
    "FALLBACK_MODEL_V2_PERF",
    "FALLBACK_PROVIDER_V2_PERF",
    "PERF_FINISH_REASON_MAX_LENGTH",
    "PRIMARY_MODEL_V2_PERF",
    "PRIMARY_PROVIDER_V2_PERF",
    "PROMPT_VERSION_V2_PERF",
    "SEMANTIC_CONTRACT_VERSION_V2_PERF",
    "SEMANTIC_INPUT_SCHEMA_VERSION_V2_PERF",
    "SEMANTIC_OUTPUT_SCHEMA_VERSION_V2_PERF",
    "SEMANTIC_V2_PERF_ADAPTER",
    "V2_PERF_AUTHORITY_QUALIFIED",
    "V2_PERF_CONTRACT_BINDING",
    "SemanticDecisionAttemptPerf",
    "SemanticDecisionReplayV2Perf",
    "SemanticDecisionRecordV2Perf",
    "SemanticV2PerfContractAdapter",
    "encode_v2_perf_payload",
    "is_bounded_perf_finish_reason",
    "record_input_digest_v2_perf",
    "record_output_digest_v2_perf",
    "reconstruct_identity_context_v2_perf",
    "reconstruct_semantic_evaluation_v2_perf",
    "replay_v2_perf_record",
]


# ---------------------------------------------------------------------------
# The PERF contract identity (owned by THIS adapter, not by the envelope)
# ---------------------------------------------------------------------------

SEMANTIC_CONTRACT_VERSION_V2_PERF: Final[str] = SEMANTIC_CONTRACT_VERSION_V2
"""The semantic contract axis of the PERF binding — the SAME final V2
semantic contract (imported from the frozen V2 adapter; the
instrumentation is a versioned extension of its RECORDING, not a new
semantic contract)."""

PROMPT_VERSION_V2_PERF: Final[str] = PROMPT_VERSION_V2
"""The prompt axis of the PERF binding — the SAME frozen prompt
(imported; the prompt does not move)."""

SEMANTIC_INPUT_SCHEMA_VERSION_V2_PERF: Final[int] = (
    SEMANTIC_INPUT_SCHEMA_VERSION_V2
)
"""The input schema axis of the PERF binding — the SAME recorded input
section (imported; the exact ``SemanticMatchCaseV2`` is
byte-identical under the PERF binding)."""

SEMANTIC_OUTPUT_SCHEMA_VERSION_V2_PERF: Final[int] = 2
"""The NEW recorded output section version: the V2 recorded output +
execution provenance gains the bounded per-attempt instrumentation
(integer-millisecond latency, provider-reported prompt / completion
token counts with explicit null = unknown, bounded finish reason).
This axis — and ONLY this axis — discriminates the PERF binding from
the frozen V2 binding (the Q3-B5 per-binding discipline: each
binding's record carries its own version, never a silent
reinterpretation)."""

AUTHORITY_CONTRACT_VERSION_V2_PERF: Final[str] = AUTHORITY_CONTRACT_VERSION_V2
"""The authority axis of the PERF binding — the SAME frozen S2-A
authority contract (imported; the derivation and the derived audit
snapshots are unchanged — the instrumentation is not a derivation
input and grants no authority)."""

#: The EXACT contract binding this adapter interprets and replays:
#: (semantic contract, prompt, input schema, output schema, authority
#: contract). One entry. A future binding is a future adapter — never
#: an implicit reinterpretation of this one.
V2_PERF_CONTRACT_BINDING: Final[tuple[str, str, int, int, str]] = (
    SEMANTIC_CONTRACT_VERSION_V2_PERF,
    PROMPT_VERSION_V2_PERF,
    SEMANTIC_INPUT_SCHEMA_VERSION_V2_PERF,
    SEMANTIC_OUTPUT_SCHEMA_VERSION_V2_PERF,
    AUTHORITY_CONTRACT_VERSION_V2_PERF,
)

#: The V2 pinned route — imported from the frozen V2 adapter (drift-
#: pinned by tests to the V2 runtime): a PERF-bound record's attempts
#: followed this exact route.
PRIMARY_PROVIDER_V2_PERF: Final[str] = PRIMARY_PROVIDER_V2
PRIMARY_MODEL_V2_PERF: Final[str] = PRIMARY_MODEL_V2
FALLBACK_PROVIDER_V2_PERF: Final[str] = FALLBACK_PROVIDER_V2
FALLBACK_MODEL_V2_PERF: Final[str] = FALLBACK_MODEL_V2

#: The explicit qualification-boundary marker — the instrumentation
#: does NOT qualify the route (imported from the frozen V2 marker;
#: drift-pinned by tests to the V2 runtime marker). V2 outputs remain
#: evidence/provenance awaiting Qualification V3.
V2_PERF_AUTHORITY_QUALIFIED: Final[bool] = V2_AUTHORITY_QUALIFIED

#: The bounded finish-reason grammar — MIRROR of the transport world's
#: ``semantic.runtime.FINISH_REASON_MAX_LENGTH`` / bounded
#: finish-identifier projection (drift-pinned by tests; the pure
#: research layer imports no production runtime). The V2 runtime
#: projects the provider-reported value through this exact grammar
#: before the attempt is recorded: the persisted value is the
#: provider's own bounded identifier, or an explicit null — never
#: raw provider text, never a reformatted or truncated value.
PERF_FINISH_REASON_MAX_LENGTH: Final[int] = 64

_PERF_FINISH_REASON_PATTERN: Final[re.Pattern] = re.compile(
    r"^[a-z][a-z0-9_]{0,63}$"
)


def is_bounded_perf_finish_reason(value: object) -> bool:
    """True when ``value`` matches the bounded finish-reason grammar
    (the research mirror the V2 runtime drift-pins against)."""
    return isinstance(
        value, str
    ) and _PERF_FINISH_REASON_PATTERN.match(value) is not None


# ---------------------------------------------------------------------------
# The PERF per-attempt record (the V2 recorded attempt + bounded
# instrumentation)
# ---------------------------------------------------------------------------


#: The exact key set of one PERF recorded attempt: the V2 recorded
#: attempt's five keys + the three bounded instrumentation keys.
_V2_PERF_ATTEMPT_KEYS: Final[frozenset[str]] = frozenset(
    {
        "role",
        "attempt_number",
        "provider",
        "model",
        "outcome",
        "latency_ms",
        "prompt_tokens",
        "completion_tokens",
        "finish_reason",
    }
)


@dataclass(frozen=True)
class SemanticDecisionAttemptPerf:
    """One provider attempt of a recorded PERF evaluation, in call
    order — the V2 recorded attempt (role, number, provider, model,
    outcome) plus the bounded per-attempt instrumentation.

    Instrumentation fields (all fail closed at construction):

    * ``latency_ms`` — the measured attempt latency in INTEGER
      milliseconds (the canonical encoding admits no float; the
      bounded persistence form of the in-memory float measurement);
    * ``prompt_tokens`` / ``completion_tokens`` — the
      provider-reported counts; explicit ``None`` = the provider
      reported none (an unknown, NEVER zero and never invented);
    * ``finish_reason`` — the provider-reported stop reason as
      bounded by the transport-world grammar (mirrored above);
      explicit ``None`` = unreported / out of grammar.

    Carries no raw response, no prompt text, no provider body, no
    credential, no http/provider identity metadata beyond the route
    pin, and no float.
    """

    role: AttemptRole
    attempt_number: int
    provider: str
    model: str
    outcome: AttemptOutcome
    latency_ms: int
    prompt_tokens: int | None
    completion_tokens: int | None
    finish_reason: str | None

    def __post_init__(self) -> None:
        # The base attempt fields are validated by the frozen V1
        # recorded-attempt constructor (role/number consistency,
        # non-empty route, bounded outcome) — the PERF attempt MUST be
        # a legal V2 recorded attempt first (no drift of the base
        # rules).
        try:
            SemanticDecisionAttempt(
                role=self.role,
                attempt_number=self.attempt_number,
                provider=self.provider,
                model=self.model,
                outcome=self.outcome,
            )
        except (TypeError, ValueError) as exc:
            raise type(exc)(str(exc)) from None

        if isinstance(self.latency_ms, bool) or not isinstance(
            self.latency_ms, int
        ):
            raise TypeError(
                "latency_ms must be the integer-millisecond int "
                f"(no float), got {type(self.latency_ms).__name__}"
            )
        if self.latency_ms < 0:
            raise ValueError(
                f"latency_ms must be >= 0, got {self.latency_ms}"
            )
        for name in ("prompt_tokens", "completion_tokens"):
            value = getattr(self, name)
            if value is None:
                continue
            if isinstance(value, bool) or not isinstance(value, int):
                raise TypeError(
                    f"{name} must be int or None (explicit unknown), "
                    f"got {type(value).__name__}"
                )
            if value < 0:
                raise ValueError(
                    f"{name} must be >= 0, got {value}"
                )
        if self.finish_reason is not None and not (
            is_bounded_perf_finish_reason(self.finish_reason)
        ):
            raise ValueError(
                "finish_reason must be None (explicit unknown) or a "
                "bounded provider finish-identifier; unbounded "
                "provider text is never recorded"
            )

    def canonical(self) -> dict[str, object]:
        return {
            "role": self.role.value,
            "attempt_number": self.attempt_number,
            "provider": self.provider,
            "model": self.model,
            "outcome": self.outcome.value,
            "latency_ms": self.latency_ms,
            "prompt_tokens": self.prompt_tokens,
            "completion_tokens": self.completion_tokens,
            "finish_reason": self.finish_reason,
        }


# ---------------------------------------------------------------------------
# PERF section encodings (the exact PERF payload shapes)
# ---------------------------------------------------------------------------


def _v2_perf_contract_section() -> dict[str, object]:
    """The PERF contract binding section (the V2 section with the new
    output-schema axis)."""
    return {
        "semantic_contract_version": SEMANTIC_CONTRACT_VERSION_V2_PERF,
        "prompt_version": PROMPT_VERSION_V2_PERF,
        "input_schema_version": SEMANTIC_INPUT_SCHEMA_VERSION_V2_PERF,
        "output_schema_version": SEMANTIC_OUTPUT_SCHEMA_VERSION_V2_PERF,
        "authority_contract_version": AUTHORITY_CONTRACT_VERSION_V2_PERF,
    }


def _v2_perf_execution_section(
    attempts: tuple[SemanticDecisionAttemptPerf, ...],
    fallback_used: bool,
    fallback_reason: SemanticFallbackReason | None,
    error_type: SemanticFailureClass | None,
    actual_provider: str | None,
    actual_model: str | None,
    evaluation_started_at: str | None,
    evaluation_finished_at: str | None,
) -> dict[str, object]:
    """The instrumented execution section — the V2 execution section
    whose attempts carry the bounded per-attempt instrumentation."""
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


# ---------------------------------------------------------------------------
# The PERF typed record (the version-owned artifact of the PERF
# binding)
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class SemanticDecisionRecordV2Perf:
    """One complete, immutable Semantic V2 decision / provenance
    artifact WITH the bounded per-attempt performance instrumentation
    (SEMANTIC-V2-PERF Phase 0 — the versioned successor of
    ``SemanticDecisionRecordV2``).

    This is the PERF contract adapter's typed record — the FOURTH
    registered semantic contract adapter, NOT a reinterpretation of
    the frozen V2 record. Every version-specific rule of the V2
    record — the exact contract binding (except the recorded output
    schema version, which is 2 under this binding), the V2 pinned
    route, the V2 input contract validation, the strict structured V2
    output coherence, the evaluation/execution coherence rules, the
    derived audit snapshots under the bound authority contract, and
    the self-verifying section digests — is preserved; the recorded
    execution provenance gains exactly the bounded per-attempt
    instrumentation (``SemanticDecisionAttemptPerf``).

    The record stores no float, no raw response, no prompt text, no
    credential, no unbounded provider metadata, reads no clock,
    performs no I/O, and grants no authority: it is a record of what
    happened — and how long it took, in bounded form — verifiable
    under the PERF contract binding.
    """

    # -- universal binding (envelope-level addressing) -------------------------
    run_id: str
    assessment_index: int
    source_url: str

    # -- PERF contract binding (adapter-owned identity) -------------------------
    semantic_contract_version: str
    prompt_version: str
    input_schema_version: int
    output_schema_version: int
    authority_contract_version: str

    # -- exact recorded V2 input (case; byte-identical to the V2 axis) ----------
    case: SemanticMatchCaseV2

    # -- recorded strict structured V2 output (unchanged) -----------------------
    evaluation_state: SemanticEvaluationStateV2
    decision: V2SemanticDecision | None
    confidence: V2Confidence | None
    reason_code: SemanticReasonCodeV2 | None
    conflict_classes: frozenset[ConflictClass]
    matched_attributes: tuple[SemanticAttributeV2, ...]
    conflicting_attributes: tuple[SemanticAttributeV2, ...]
    missing_critical_attributes: tuple[SemanticAttributeDimensionV2, ...]

    # -- recorded V2 runtime provenance (the instrumented attempts) -------------
    attempts: tuple[SemanticDecisionAttemptPerf, ...]
    fallback_used: bool
    fallback_reason: SemanticFallbackReason | None
    error_type: SemanticFailureClass | None
    actual_provider: str | None
    actual_model: str | None
    evaluation_started_at: str | None
    evaluation_finished_at: str | None

    # -- derived audit snapshots (unchanged; replay proves agreement) -----------
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
                    f"conflicting_attributes[{i}] must be SemanticAttributeV2, "
                    f"got {type(item).__name__}"
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
                "attempts must be a tuple, "
                f"got {type(self.attempts).__name__}"
            )
        for i, attempt in enumerate(self.attempts):
            if not isinstance(attempt, SemanticDecisionAttemptPerf):
                raise TypeError(
                    f"attempts[{i}] must be SemanticDecisionAttemptPerf, "
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

    # -- PERF contract binding (the adapter's exact pin) ---------------------------

    def _validate_contract_binding(self) -> None:
        # The PERF adapter interprets exactly one contract binding:
        # the V2 binding with the recorded output schema version 2.
        # Anything else is outside this adapter's safe-replay envelope
        # and fails closed at construction (never silently
        # reinterpreted) — in particular the historical output-schema-
        # 1 binding belongs to the frozen V2 adapter, not here.
        if self.semantic_contract_version != (
            SEMANTIC_CONTRACT_VERSION_V2_PERF
        ):
            raise ValueError(
                "semantic_contract_version must be "
                f"{SEMANTIC_CONTRACT_VERSION_V2_PERF!r} for this PERF "
                f"record, got {self.semantic_contract_version!r}; an "
                "artifact bound to another semantic contract is outside "
                "the PERF adapter and fails closed"
            )
        if self.prompt_version != PROMPT_VERSION_V2_PERF:
            raise ValueError(
                "prompt_version must be "
                f"{PROMPT_VERSION_V2_PERF!r} for the PERF binding, got "
                f"{self.prompt_version!r}"
            )
        for name, value, expected in (
            (
                "input_schema_version",
                self.input_schema_version,
                SEMANTIC_INPUT_SCHEMA_VERSION_V2_PERF,
            ),
            (
                "output_schema_version",
                self.output_schema_version,
                SEMANTIC_OUTPUT_SCHEMA_VERSION_V2_PERF,
            ),
        ):
            if isinstance(value, bool) or not isinstance(value, int):
                raise TypeError(
                    f"{name} must be int, got {type(value).__name__}"
                )
            if value != expected:
                raise ValueError(
                    f"{name} must be {expected} for the PERF binding, "
                    f"got {value}; a historical output-schema-1 record "
                    "is the frozen V2 adapter's, never reinterpreted "
                    "here"
                )
        if self.authority_contract_version != (
            AUTHORITY_CONTRACT_VERSION_V2_PERF
        ):
            raise ValueError(
                "authority_contract_version must be "
                f"{AUTHORITY_CONTRACT_VERSION_V2_PERF!r} for the PERF "
                f"binding, got {self.authority_contract_version!r}; "
                "the derived audit snapshots of this artifact were "
                "produced under the exact bound authority contract, "
                "and no other"
            )

    # -- evaluation + execution coherence (the V2 route pin lives here) -----------

    def _validate_evaluation_and_execution(self) -> None:
        state = self.evaluation_state

        if state is SemanticEvaluationStateV2.NOT_EVALUATED:
            # No call happened: no output, no execution, no instants,
            # no instrumentation (an unevaluated record has no
            # attempts to instrument).
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
                        f"NOT_EVALUATED may not carry {name}; a record "
                        "that was never evaluated has no semantic output "
                        "and no runtime provenance (absence is never "
                        "defaulted)"
                    )
            if self.conflict_classes:
                raise ValueError(
                    "NOT_EVALUATED may not carry conflict classes; "
                    "conflicts are observed by an evaluation"
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
                    "NOT_EVALUATED may not carry attempts; no provider "
                    "was called"
                )
            if self.fallback_used or self.fallback_reason is not None:
                raise ValueError(
                    "NOT_EVALUATED may not record fallback use or a "
                    "fallback reason"
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
        # Role / number / route pinning (the V2 pinned route; the
        # attempts are recorded in call order).
        for i, attempt in enumerate(self.attempts):
            if attempt.attempt_number != i + 1:
                raise ValueError(
                    f"attempts[{i}].attempt_number must be {i + 1} "
                    f"(call order), got {attempt.attempt_number}"
                )
            if i == 0:
                if (
                    attempt.provider != PRIMARY_PROVIDER_V2_PERF
                    or attempt.model != PRIMARY_MODEL_V2_PERF
                ):
                    raise ValueError(
                        "the primary attempt of a PERF-bound record "
                        "must be the pinned primary "
                        f"{PRIMARY_PROVIDER_V2_PERF}/"
                        f"{PRIMARY_MODEL_V2_PERF}, got "
                        f"{attempt.provider}/{attempt.model}"
                    )
            else:
                if (
                    attempt.provider != FALLBACK_PROVIDER_V2_PERF
                    or attempt.model != FALLBACK_MODEL_V2_PERF
                ):
                    raise ValueError(
                        "the fallback attempt of a PERF-bound record "
                        "must be the pinned fallback "
                        f"{FALLBACK_PROVIDER_V2_PERF}/"
                        f"{FALLBACK_MODEL_V2_PERF}, got "
                        f"{attempt.provider}/{attempt.model}"
                    )

        if attempt_count == 2 and not self.fallback_used:
            raise ValueError(
                "fallback_used must be True when two attempts were "
                "recorded"
            )
        if attempt_count == 1 and self.fallback_used:
            raise ValueError(
                "fallback_used must be False when one attempt was "
                "recorded"
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
            # attempt, and provenance attributed to exactly that
            # attempt (the same coherence rules the V2 record owns).
            if (
                self.decision is None
                or self.confidence is None
                or self.reason_code is None
            ):
                raise ValueError(
                    "EVALUATED requires a decision, a confidence, and "
                    "the bounded V2 reason code"
                )
            if self.error_type is not None:
                raise ValueError(
                    "EVALUATED may not carry an error_type; the "
                    "evaluation produced an accepted response"
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
                    "a successful primary is final: a two-attempt "
                    "record cannot have an OK primary attempt"
                )
            ok_attempt = self.attempts[-1]
            if self.actual_provider != ok_attempt.provider:
                raise ValueError(
                    "actual_provider must be the provider of the OK "
                    "attempt"
                )
            if self.actual_model != ok_attempt.model:
                raise ValueError(
                    "actual_model must be the model of the OK attempt"
                )
            # The strict structured V2 output must be coherent under
            # the frozen reason-code rules (the V2 input contract's
            # response validation re-runs and fails closed).
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
            # Failure: never shaped like a decision (a runtime
            # failure is NEVER interpreted as NO_MATCH or anything
            # else evidence-shaped).
            if (
                self.decision is not None
                or self.confidence is not None
                or self.reason_code is not None
            ):
                raise ValueError(
                    "RUNTIME_FAILURE may not carry a decision, "
                    "confidence, or reason code; a runtime failure is "
                    "never interpreted as NO_MATCH"
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
                    "RUNTIME_FAILURE must not name an actual provider "
                    "or model; no provider produced an accepted "
                    "response"
                )
            if any(
                attempt.outcome is AttemptOutcome.OK
                for attempt in self.attempts
            ):
                raise ValueError(
                    "a RUNTIME_FAILURE record must not contain an OK "
                    "attempt"
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
                    f"error_type {self.error_type.value} is "
                    f"inconsistent with {attempt_count} recorded "
                    "attempt(s)"
                )

    # -- derived snapshots (types only; agreement is replay's job) ------------------

    def _validate_derived_types(self) -> None:
        if not self.fired_rules:
            raise ValueError(
                "an authority decision must record at least one fired "
                "rule"
            )

    # -- integrity self-verification ---------------------------------------------------

    def _validate_digests(self) -> None:
        _validate_digest(self.input_digest, "input_digest")
        _validate_digest(self.output_digest, "output_digest")
        expected_input = record_input_digest_v2_perf(self)
        expected_output = record_output_digest_v2_perf(self)
        if self.input_digest != expected_input:
            raise ValueError(
                "input_digest does not agree with the record's input "
                "sections (binding, PERF contract, case); the artifact "
                "is corrupt or was built with the wrong digest"
            )
        if self.output_digest != expected_output:
            raise ValueError(
                "output_digest does not agree with the record's output "
                "sections (evaluation, instrumented execution, "
                "derived); the artifact is corrupt or was built with "
                "the wrong digest"
            )

    # -- section accessors (shared by the PERF codec and the digest functions) --------

    def case_section(self) -> dict[str, object]:
        return self.case.canonical()

    def binding_section(self) -> dict[str, object]:
        return _binding_section(
            self.run_id, self.assessment_index, self.source_url
        )

    def contract_section(self) -> dict[str, object]:
        return _v2_perf_contract_section()

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
        return _v2_perf_execution_section(
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
        matched_attributes: tuple,
        conflicting_attributes: tuple,
        missing_critical_attributes: tuple,
        attempts: tuple[SemanticDecisionAttemptPerf, ...],
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
    ) -> "SemanticDecisionRecordV2Perf":
        """Build a PERF record, computing the self-verifying section
        digests.

        The contract binding is the PERF one (semantic contract V2,
        the frozen prompt, input schema 1, output schema 2, the frozen
        authority contract): the builder takes no version parameters
        so a PERF artifact cannot be bound to a contract this adapter
        does not know.
        """
        input_digest = canonical_sha256(
            {
                "binding": _binding_section(
                    run_id, assessment_index, source_url
                ),
                "contract": _v2_perf_contract_section(),
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
                "execution": _v2_perf_execution_section(
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
            semantic_contract_version=SEMANTIC_CONTRACT_VERSION_V2_PERF,
            prompt_version=PROMPT_VERSION_V2_PERF,
            input_schema_version=SEMANTIC_INPUT_SCHEMA_VERSION_V2_PERF,
            output_schema_version=SEMANTIC_OUTPUT_SCHEMA_VERSION_V2_PERF,
            authority_contract_version=(
                AUTHORITY_CONTRACT_VERSION_V2_PERF
            ),
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


def record_input_digest_v2_perf(record: SemanticDecisionRecordV2Perf) -> str:
    """SHA-256 over the canonical encoding of the PERF record's INPUT
    sections: binding + the PERF contract section + the exact recorded
    V2 input (case). Distinct from the same-case V2 input digest by
    exactly the recorded output-schema axis."""
    return canonical_sha256(
        {
            "binding": record.binding_section(),
            "contract": record.contract_section(),
            "case": record.case_section(),
        }
    )


def record_output_digest_v2_perf(
    record: SemanticDecisionRecordV2Perf,
) -> str:
    """SHA-256 over the canonical encoding of the PERF record's OUTPUT
    sections: recorded V2 evaluation + the instrumented V2 execution
    provenance + derived audit snapshots."""
    return canonical_sha256(
        {
            "evaluation": record.evaluation_section(),
            "execution": record.execution_section(),
            "derived": record.derived_section(),
        }
    )


# ---------------------------------------------------------------------------
# The PERF payload codec (the exact PERF section shapes; strict, fail
# closed)
# ---------------------------------------------------------------------------


def encode_v2_perf_payload(
    record: SemanticDecisionRecordV2Perf,
) -> dict[str, object]:
    """Encode a ``SemanticDecisionRecordV2Perf`` into the full framed
    payload (envelope schema 1 — the SAME universal row — semantic
    contract V2, output schema 2).

    The returned dict contains only native JSON types (str, int, bool,
    list, dict, None) — no enum members, no dataclass objects, no
    floats. Set-valued fields are encoded as sorted unique value
    lists; order-significant fields (attempts, attribute lists) keep
    their order.

    Raises ``TypeError`` if the input is not a PERF record (caller
    defect).
    """
    if not isinstance(record, SemanticDecisionRecordV2Perf):
        raise TypeError(
            f"expected SemanticDecisionRecordV2Perf, got "
            f"{type(record).__name__}"
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


def _dec_v2_perf_attempt(
    data: dict[str, object], path: str
) -> SemanticDecisionAttemptPerf:
    _check_keys(data, _V2_PERF_ATTEMPT_KEYS, path)
    return SemanticDecisionAttemptPerf(
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
        latency_ms=_dec_int(
            _dec_required(data, "latency_ms", path),
            f"{path}.latency_ms",
        ),
        prompt_tokens=_dec_optional_int(
            _dec_required(data, "prompt_tokens", path),
            f"{path}.prompt_tokens",
        ),
        completion_tokens=_dec_optional_int(
            _dec_required(data, "completion_tokens", path),
            f"{path}.completion_tokens",
        ),
        finish_reason=_dec_optional_str(
            _dec_required(data, "finish_reason", path),
            f"{path}.finish_reason",
        ),
    )


def _dec_optional_int(raw: object, path: str) -> int | None:
    """Decode an explicit-unknown int (null = the provider reported
    none — an unknown, never zero)."""
    if raw is None:
        return None
    return _dec_int(raw, path)


def _decode_v2_perf_payload(
    payload: dict[str, object],
) -> SemanticDecisionRecordV2Perf:
    """Decode a PERF-framed payload into a validated PERF record.

    Raises ``SemanticDecisionCodecError`` for any structural violation
    and wraps every record-constructor failure (including the
    self-verifying digest check and the PERF exact-binding check) in
    the same bounded error.
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

    # -- contract (the PERF binding: the V2 axes + output schema 2) --
    contract = _dec_mapping(
        _dec_required(payload, "contract", "top-level"), "contract"
    )
    _check_keys(contract, _V2_CONTRACT_KEYS, "contract")
    semantic_contract_version = _dec_str(
        _dec_required(
            contract, "semantic_contract_version", "contract"
        ),
        "contract.semantic_contract_version",
        allow_empty=False,
    )
    prompt_version = _dec_str(
        _dec_required(contract, "prompt_version", "contract"),
        "contract.prompt_version",
        allow_empty=False,
    )
    input_schema_version = _dec_int(
        _dec_required(
            contract, "input_schema_version", "contract"
        ),
        "contract.input_schema_version",
    )
    output_schema_version = _dec_int(
        _dec_required(
            contract, "output_schema_version", "contract"
        ),
        "contract.output_schema_version",
    )
    authority_contract_version = _dec_str(
        _dec_required(
            contract, "authority_contract_version", "contract"
        ),
        "contract.authority_contract_version",
        allow_empty=False,
    )

    # -- case (the exact recorded V2 input — the frozen V2 case
    #    decoder, byte-identical shape) --
    case = _dec_v2_case(
        _dec_mapping(_dec_required(payload, "case", "top-level"), "case"),
        "case",
    )

    # -- evaluation (the strict structured V2 output — the V2 shape) --
    evaluation_data = _dec_mapping(
        _dec_required(payload, "evaluation", "top-level"), "evaluation"
    )
    _check_keys(evaluation_data, _V2_EVALUATION_KEYS, "evaluation")
    evaluation_state = _dec_str_enum(
        SemanticEvaluationStateV2,
        _dec_required(
            evaluation_data, "evaluation_state", "evaluation"
        ),
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
                _dec_required(
                    evaluation_data, "conflict_classes", "evaluation"
                ),
                "evaluation.conflict_classes",
            )
        )
    )
    matched_attributes = _dec_v2_attribute_list(
        _dec_list(
            _dec_required(
                evaluation_data, "matched_attributes", "evaluation"
            ),
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
                    evaluation_data,
                    "missing_critical_attributes",
                    "evaluation",
                ),
                "evaluation.missing_critical_attributes",
            )
        )
    )

    # -- execution (the instrumented attempts) --
    execution_data = _dec_mapping(
        _dec_required(payload, "execution", "top-level"), "execution"
    )
    _check_keys(execution_data, _V2_EXECUTION_KEYS, "execution")
    attempts_raw = _dec_list(
        _dec_required(execution_data, "attempts", "execution"),
        "execution.attempts",
    )
    attempts = tuple(
        _dec_v2_perf_attempt(
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
        _dec_required(
            execution_data, "evaluation_started_at", "execution"
        ),
        "execution.evaluation_started_at",
    )
    evaluation_finished_at = _dec_optional_str(
        _dec_required(
            execution_data, "evaluation_finished_at", "execution"
        ),
        "execution.evaluation_finished_at",
    )

    # -- derived (the V2 shape under the bound authority contract) --
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
                _dec_required(
                    derived_data, "fired_rules", "derived"
                ),
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

    # The PERF record constructor re-validates everything (types,
    # coherence, the PERF exact contract binding, the V2 route pin,
    # the instrumented attempts, digests) and fails closed; any
    # constructor violation is wrapped in the bounded codec error by
    # the caller.
    return SemanticDecisionRecordV2Perf(
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
# The PERF pure zero-live replay / reconstruction
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class SemanticDecisionReplayV2Perf:
    """The verified reconstruction of one persisted PERF semantic
    decision.

    Carries the original PERF record (for provenance — including the
    bounded per-attempt instrumentation), the reconstructed S2-A
    authority inputs (the exact recorded V2 input case is the
    authority input), the re-derived authority decision (proved to
    agree with the stored derived audit snapshots), the recorded V2
    input, and the recorded PERF contract binding. The instrumentation
    is NEVER a derivation input: the re-derivation runs over the case /
    evaluation exactly as the V2 replay does.
    """

    record: SemanticDecisionRecordV2Perf
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


def reconstruct_identity_context_v2_perf(
    record: SemanticDecisionRecordV2Perf,
) -> IdentityStateAssessmentV2:
    """Reconstruct the deterministic V2 context from the persisted
    PERF record's exact recorded input (the same frozen constructor
    re-validation the V2 replay performs)."""
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


def reconstruct_semantic_evaluation_v2_perf(
    record: SemanticDecisionRecordV2Perf,
) -> SemanticEvaluationV2:
    """Reconstruct the exact historical V2 semantic evaluation from a
    PERF record (the same mapping the V2 replay performs: EVALUATED ->
    the recorded decision / confidence / conflict classes;
    RUNTIME_FAILURE -> the explicit runtime-failure state, NEVER
    interpreted as NO_MATCH; NOT_EVALUATED -> the explicit
    not-evaluated state)."""
    if record.evaluation_state is SemanticEvaluationStateV2.EVALUATED:
        if record.decision is None or record.confidence is None:
            raise SemanticDecisionReplayError(
                "an EVALUATED record must carry the recorded decision "
                "and confidence; the artifact is corrupt"
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


def _v2_perf_contract_binding(
    record: SemanticDecisionRecordV2Perf,
) -> tuple[str, str, int, int, str]:
    return (
        record.semantic_contract_version,
        record.prompt_version,
        record.input_schema_version,
        record.output_schema_version,
        record.authority_contract_version,
    )


def _replay_v2_perf_record(record: object) -> SemanticDecisionReplayV2Perf:
    """The PERF adapter's zero-live replay of one PERF record.

    Steps (each fails closed with ``SemanticDecisionReplayError``):

    1. **PERF exact-binding gate.** The record's exact (semantic
       contract, prompt, input schema, output schema, authority
       contract) binding must be ``V2_PERF_CONTRACT_BINDING`` — the
       output-schema-2 binding. Anything else (including the
       historical output-schema-1 V2 binding, which belongs to the
       frozen V2 adapter) is refused explicitly — never silently
       reinterpreted.
    2. **Reconstruction.** The historical evaluation, the V2 context,
       the context provenances, and the authority-side product
       evidence are reconstructed from the EXACT recorded V2 input
       (constructor-validated) — the instrumentation is not read.
    3. **Re-derivation under the bound authority contract.** The S2-A
       derivation is re-run on the reconstructed inputs (the same
       frozen functions the V2 replay uses).
    4. **Derived-agreement proof.** Every stored derived audit
       snapshot must EXACTLY agree with the re-derivation (the same
       tamper / version-drift detection the V2 replay performs).

    Performs zero live AI calls and zero provider/network calls.
    """
    if not isinstance(record, SemanticDecisionRecordV2Perf):
        raise TypeError(
            "the PERF replay adapter expects a "
            "SemanticDecisionRecordV2Perf, got "
            f"{type(record).__name__}"
        )
    binding = _v2_perf_contract_binding(record)
    if binding not in (V2_PERF_CONTRACT_BINDING,):
        raise SemanticDecisionReplayError(
            "unsupported contract binding "
            f"(semantic contract {binding[0]!r}, prompt {binding[1]!r}, "
            f"input schema {binding[2]}, output schema {binding[3]}, "
            f"authority contract {binding[4]!r}); the PERF adapter "
            "cannot safely replay it and refuses to reinterpret a "
            "historical decision under a contract it does not know"
        )

    case = record.case
    try:
        identity_context = reconstruct_identity_context_v2_perf(record)
        semantic_evaluation = reconstruct_semantic_evaluation_v2_perf(
            record
        )
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

    return SemanticDecisionReplayV2Perf(
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


def replay_v2_perf_record(
    record: SemanticDecisionRecordV2Perf,
) -> SemanticDecisionReplayV2Perf:
    """Public PERF replay entry (delegates to the adapter
    implementation)."""
    return _replay_v2_perf_record(record)


def _v2_perf_run_binding_violation(
    record: object,
    *,
    request_mpn: str,
    request_description: str,
) -> str | None:
    """The PERF-specific run-binding check: the recorded V2 input's
    target MPN / description must equal the run's canonical request
    (the universal parts are checked by the persistence service)."""
    if not isinstance(record, SemanticDecisionRecordV2Perf):
        raise TypeError(
            "the PERF run-binding check expects a "
            "SemanticDecisionRecordV2Perf, got "
            f"{type(record).__name__}"
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
# The registered PERF adapter (the fourth entry of the universal
# registry — appended after the V2-FU4 adapter)
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class SemanticV2PerfContractAdapter(SemanticDecisionContractAdapter):
    """The registered adapter for the V2 PERF instrumentation binding
    (envelope schema 1, semantic contract V2, output schema 2)."""

    def encode(self, record: object) -> dict[str, object]:
        return encode_v2_perf_payload(record)

    def decode(
        self, payload: dict[str, object]
    ) -> SemanticDecisionRecordV2Perf:
        return _decode_v2_perf_payload(payload)

    def replay(self, record: object) -> SemanticDecisionReplayV2Perf:
        return _replay_v2_perf_record(record)

    def run_binding_violation(
        self,
        record: object,
        *,
        request_mpn: str,
        request_description: str,
    ) -> str | None:
        return _v2_perf_run_binding_violation(
            record,
            request_mpn=request_mpn,
            request_description=request_description,
        )


SEMANTIC_V2_PERF_ADAPTER: Final[SemanticV2PerfContractAdapter] = (
    SemanticV2PerfContractAdapter(
        envelope_schema_version=1,
        semantic_contract_version=SEMANTIC_CONTRACT_VERSION_V2_PERF,
        supported_bindings=(V2_PERF_CONTRACT_BINDING,),
        record_type=SemanticDecisionRecordV2Perf,
    )
)
