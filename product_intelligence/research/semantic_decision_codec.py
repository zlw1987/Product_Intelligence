"""Strict versioned codec for the persisted semantic-decision artifact
(S2-B).

Encodes a ``SemanticDecisionRecord`` (the pure research-layer artifact) into
an opaque versioned JSON-serialisable payload dict, and decodes a persisted
payload back into the validated artifact.

This module is **pure research-layer serialisation**. It may import stdlib
and research contracts. It must not import Django, ``runs``, ``web``,
``execution``, ``providers``, ``semantic``, ``evaluation``, network
libraries, or filesystem libraries.

The discipline follows the frozen price-result codec precedent:

* exact schema version (``SEMANTIC_DECISION_SCHEMA_VERSION = 1``; anything
  else fails closed — no best-effort migration, no permissive unknown-field
  acceptance);
* strict field set at every level (missing keys AND extra keys rejected);
* strict enums (unknown enum values rejected — a value the bound contract
  vocabulary does not define never decodes);
* no float authority data (the record module refuses floats at canonical
  encoding; the payload is checked on decode);
* no lossy serialization (order-significant lists keep their order;
  order-insensitive sets are encoded sorted and duplicates are rejected);
* no silent defaulting of missing safety fields (nullable means the key is
  present with a null value; an absent key is a codec error);
* decode wraps every constructor/validation failure in the bounded
  ``SemanticDecisionCodecError``.

The payload is what the ``runs.SemanticDecisionRecord`` row stores in its
opaque ``payload`` column; the row's separate ``payload_digest`` column
holds ``canonical_payload_digest(payload)`` computed at write time, so a
whole-artifact tamper is provable from outside the payload itself.
"""

from __future__ import annotations

from product_intelligence.research import (
    AuthorityRuleV2,
    AuthorityTier,
    CandidateProductEvidenceSource,
    ConflictClass,
    ConflictSubstateV2,
    ContextProvenance,
    IdentityRelationshipSignal,
    IdentityStateV2,
    ProductEvidenceDimension,
    ProductEvidenceFactV2,
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
from product_intelligence.research.semantic_decision_record import (
    AUTHORITY_CONTRACT_VERSION,
    AttemptOutcome,
    AttemptRole,
    PROMPT_VERSION_V1,
    SEMANTIC_CONTRACT_VERSION,
    SEMANTIC_INPUT_SCHEMA_VERSION,
    SEMANTIC_OUTPUT_SCHEMA_VERSION,
    SemanticDecisionAttempt,
    SemanticDecisionRecord,
    SemanticFallbackReason,
    SemanticFailureClass,
    SemanticPromptInput,
    canonical_sha256,
)

__all__ = [
    "SEMANTIC_DECISION_SCHEMA_VERSION",
    "SemanticDecisionCodecError",
    "canonical_payload_digest",
    "decode_semantic_decision_record",
    "encode_semantic_decision_record",
]


SEMANTIC_DECISION_SCHEMA_VERSION: int = 1
"""Current (and only supported) semantic-decision artifact schema version."""


class SemanticDecisionCodecError(ValueError):
    """Raised when a persisted semantic-decision payload cannot be decoded.

    Covers: unsupported schema version, malformed payload, missing or extra
    fields, unknown enums, wrong types, duplicate set members, and any
    structural failure of the record constructor during decode (including
    the record's self-verifying digest check).

    Messages are bounded: they name the failing path, never raw payload
    content that may carry external text.
    """


# ---------------------------------------------------------------------------
# Strict field sets (one per payload section)
# ---------------------------------------------------------------------------

_TOP_LEVEL_KEYS: frozenset[str] = frozenset(
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

_BINDING_KEYS: frozenset[str] = frozenset(
    {"run_id", "assessment_index", "source_url"}
)

_CONTRACT_KEYS: frozenset[str] = frozenset(
    {
        "semantic_contract_version",
        "prompt_version",
        "input_schema_version",
        "output_schema_version",
        "authority_contract_version",
    }
)

_CONTEXT_KEYS: frozenset[str] = frozenset(
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

_PRODUCT_EVIDENCE_KEYS: frozenset[str] = frozenset(
    {"profile", "quality"}
)

_PROFILE_KEYS: frozenset[str] = frozenset(
    {"has_usable_product_title", "matched_facts"}
)

_FACT_KEYS: frozenset[str] = frozenset({"dimension", "sources"})

_PROMPT_INPUT_KEYS: frozenset[str] = frozenset(
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

_EVALUATION_KEYS: frozenset[str] = frozenset(
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

_EXECUTION_KEYS: frozenset[str] = frozenset(
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

_ATTEMPT_KEYS: frozenset[str] = frozenset(
    {"role", "attempt_number", "provider", "model", "outcome"}
)

_DERIVED_KEYS: frozenset[str] = frozenset(
    {"relationship_authority", "authority_tier", "fired_rules"}
)

_INTEGRITY_KEYS: frozenset[str] = frozenset(
    {"input_digest", "output_digest"}
)


# ---------------------------------------------------------------------------
# Internal strict decode helpers
# ---------------------------------------------------------------------------


def _dec_mapping(raw: object, path: str) -> dict[str, object]:
    if not isinstance(raw, dict):
        raise SemanticDecisionCodecError(
            f"{path}: expected mapping, got {type(raw).__name__}"
        )
    return raw


def _dec_list(raw: object, path: str) -> list[object]:
    if not isinstance(raw, list):
        raise SemanticDecisionCodecError(
            f"{path}: expected list, got {type(raw).__name__}"
        )
    return raw


def _dec_required(
    data: dict[str, object], key: str, path: str
) -> object:
    if key not in data:
        raise SemanticDecisionCodecError(
            f"{path}: missing required key {key!r}"
        )
    return data[key]


def _check_keys(data: dict[str, object], allowed: frozenset[str], path: str) -> None:
    missing = allowed - set(data.keys())
    if missing:
        raise SemanticDecisionCodecError(
            f"{path}: missing required keys {sorted(missing)}"
        )
    extra = set(data.keys()) - allowed
    if extra:
        raise SemanticDecisionCodecError(
            f"{path}: unexpected keys {sorted(extra)}"
        )


def _dec_str(raw: object, path: str, *, allow_empty: bool = True) -> str:
    if not isinstance(raw, str):
        raise SemanticDecisionCodecError(
            f"{path}: expected string, got {type(raw).__name__}"
        )
    if not allow_empty and not raw:
        raise SemanticDecisionCodecError(f"{path}: must be non-empty")
    return raw


def _dec_optional_str(raw: object, path: str) -> str | None:
    if raw is None:
        return None
    return _dec_str(raw, path)


def _dec_int(raw: object, path: str) -> int:
    if isinstance(raw, bool) or not isinstance(raw, int):
        raise SemanticDecisionCodecError(
            f"{path}: expected int, got {type(raw).__name__}"
        )
    return raw


def _dec_bool(raw: object, path: str) -> bool:
    if not isinstance(raw, bool):
        raise SemanticDecisionCodecError(
            f"{path}: expected bool, got {type(raw).__name__}"
        )
    return raw


def _dec_str_enum(enum_cls: type, raw: object, path: str):
    """Decode a string into an exact enum member; unknown values fail."""
    value = _dec_str(raw, path, allow_empty=False)
    for member in enum_cls:
        if member.value == value:
            return member
    raise SemanticDecisionCodecError(
        f"{path}: unknown {enum_cls.__name__} value {value!r}"
    )


def _dec_optional_str_enum(enum_cls: type, raw: object, path: str):
    if raw is None:
        return None
    return _dec_str_enum(enum_cls, raw, path)


# The four frozen V2 sub-state enum families (values are unique across
# families, so decoding by value is well-defined; the record constructor
# then re-validates the state/sub-state pairing and fails closed).
_SUBSTATE_ENUM_FAMILIES = (
    VerifiedSubstateV2,
    UncertainSubstateV2,
    ConflictSubstateV2,
    UnevaluableSubstateV2,
)


def _dec_substate(raw: object, path: str):
    """Decode a sub-state value across the four frozen V2 families."""
    value = _dec_str(raw, path, allow_empty=False)
    for family in _SUBSTATE_ENUM_FAMILIES:
        for member in family:
            if member.value == value:
                return member
    raise SemanticDecisionCodecError(
        f"{path}: unknown V2 sub-state value {value!r}"
    )


def _dec_sorted_unique_str_list(raw: object, path: str) -> list[str]:
    """Decode a sorted list of unique non-empty strings (set encoding).

    The canonical form of a frozenset is its sorted unique values; a list
    that is not sorted or has duplicates is not the strict encoding and is
    rejected (no lossy collapsing).
    """
    items = _dec_list(raw, path)
    out: list[str] = []
    for i, item in enumerate(items):
        out.append(_dec_str(item, f"{path}[{i}]", allow_empty=False))
    if out != sorted(out):
        raise SemanticDecisionCodecError(
            f"{path}: set values must be encoded in sorted order"
        )
    if len(out) != len(set(out)):
        raise SemanticDecisionCodecError(
            f"{path}: set values must be unique"
        )
    return out


def _dec_str_list(raw: object, path: str) -> tuple[str, ...]:
    """Decode an order-significant list of strings."""
    items = _dec_list(raw, path)
    return tuple(_dec_str(item, f"{path}[{i}]") for i, item in enumerate(items))


def _refuse_floats_anywhere(value: object, path: str) -> None:
    """Walk the decoded payload and refuse float values outright.

    No float authority data, no lossy serialization: a float anywhere in a
    persisted semantic artifact is rejected, not rounded.
    """
    if isinstance(value, dict):
        for key, item in value.items():
            _refuse_floats_anywhere(item, f"{path}.{key}")
        return
    if isinstance(value, list):
        for i, item in enumerate(value):
            _refuse_floats_anywhere(item, f"{path}[{i}]")
        return
    if isinstance(value, float):
        raise SemanticDecisionCodecError(
            f"{path}: float values are not permitted in a semantic "
            "decision payload (no float authority data)"
        )


# ---------------------------------------------------------------------------
# Encode — schema v1
# ---------------------------------------------------------------------------


def encode_semantic_decision_record(
    record: SemanticDecisionRecord,
) -> dict[str, object]:
    """Encode a ``SemanticDecisionRecord`` into the schema-v1 payload.

    The returned dict contains only native JSON types (str, int, bool,
    list, dict, None) — no enum members, no dataclass objects, no floats.
    Set-valued fields are encoded as sorted unique value lists;
    order-significant fields (attempts, attribute lists) keep their order.

    Raises ``TypeError`` if the input is not a ``SemanticDecisionRecord``
    (caller defect).
    """
    if not isinstance(record, SemanticDecisionRecord):
        raise TypeError(
            f"expected SemanticDecisionRecord, got {type(record).__name__}"
        )

    profile = record.product_evidence
    return {
        "schema_version": SEMANTIC_DECISION_SCHEMA_VERSION,
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


def canonical_payload_digest(payload: dict[str, object]) -> str:
    """The canonical SHA-256 digest of a full payload.

    This is what the persistence layer stores in the row's separate
    ``payload_digest`` column at write time and re-verifies at read time:
    a whole-artifact tamper anchor that cannot be regenerated from within
    the payload alone.
    """
    return canonical_sha256(payload)


# ---------------------------------------------------------------------------
# Decode — schema v1
# ---------------------------------------------------------------------------


def _dec_attempt(data: dict[str, object], path: str) -> SemanticDecisionAttempt:
    _check_keys(data, _ATTEMPT_KEYS, path)
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


def _dec_fact(data: dict[str, object], path: str) -> ProductEvidenceFactV2:
    _check_keys(data, _FACT_KEYS, path)
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


def _dec_profile(data: dict[str, object], path: str) -> ProductEvidenceProfileV2:
    _check_keys(data, _PROFILE_KEYS, path)
    has_title = _dec_bool(
        _dec_required(data, "has_usable_product_title", path),
        f"{path}.has_usable_product_title",
    )
    facts_raw = _dec_list(_dec_required(data, "matched_facts", path), f"{path}.matched_facts")
    facts: list[ProductEvidenceFactV2] = []
    seen: set[tuple[str, tuple[str, ...]]] = set()
    for i, item in enumerate(facts_raw):
        fact = _dec_fact(_dec_mapping(item, f"{path}.matched_facts[{i}]"), f"{path}.matched_facts[{i}]")
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


def _decode_v1_payload(payload: dict[str, object]) -> SemanticDecisionRecord:
    """Decode a schema-v1 payload into a validated record.

    Raises ``SemanticDecisionCodecError`` for any structural violation and
    wraps every record-constructor failure (including the self-verifying
    digest check) in the same bounded error.
    """
    _check_keys(payload, _TOP_LEVEL_KEYS, "top-level")

    # -- binding --
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

    # -- contract (the exact frozen v1 binding) --
    contract = _dec_mapping(
        _dec_required(payload, "contract", "top-level"), "contract"
    )
    _check_keys(contract, _CONTRACT_KEYS, "contract")
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
    _check_keys(context, _CONTEXT_KEYS, "context")
    identity_state = _dec_str_enum(
        IdentityStateV2,
        _dec_required(context, "identity_state", "context"),
        "context.identity_state",
    )
    substate = _dec_substate(
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
    _check_keys(product_evidence_data, _PRODUCT_EVIDENCE_KEYS, "product_evidence")
    product_evidence = _dec_profile(
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

    # -- prompt input --
    prompt_input_data = _dec_mapping(
        _dec_required(payload, "prompt_input", "top-level"), "prompt_input"
    )
    _check_keys(prompt_input_data, _PROMPT_INPUT_KEYS, "prompt_input")
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
    _check_keys(evaluation_data, _EVALUATION_KEYS, "evaluation")
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
    _check_keys(execution_data, _EXECUTION_KEYS, "execution")
    attempts_raw = _dec_list(
        _dec_required(execution_data, "attempts", "execution"),
        "execution.attempts",
    )
    attempts = tuple(
        _dec_attempt(_dec_mapping(item, f"execution.attempts[{i}]"), f"execution.attempts[{i}]")
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
    _check_keys(derived_data, _DERIVED_KEYS, "derived")
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
    _check_keys(integrity_data, _INTEGRITY_KEYS, "integrity")
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

    # The record constructor re-validates everything (types, coherence,
    # route pinning, digests) and fails closed; any constructor violation
    # is wrapped in the bounded codec error by the caller.
    return SemanticDecisionRecord(
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


def decode_semantic_decision_record(
    payload: object,
    *,
    schema_version: int,
) -> SemanticDecisionRecord:
    """Decode a persisted payload into a validated ``SemanticDecisionRecord``.

    The payload is treated as untrusted/corruptible state. Decoding is
    strict:

    * unsupported ``schema_version`` fails closed (only
      ``SEMANTIC_DECISION_SCHEMA_VERSION`` is supported — no best-effort
      migration, no permissive acceptance of unknown schemas);
    * missing keys, extra keys, wrong types, unknown enums, unsorted or
      duplicated set encodings, and float values all raise
      ``SemanticDecisionCodecError``;
    * the final record is constructed through its normal validation
      (including the self-verifying input/output digest check); any
      ``TypeError`` / ``ValueError`` from persisted data violating a
      contract is wrapped as ``SemanticDecisionCodecError``.

    Returns a fully validated record or raises. Never returns a partially
    decoded object.
    """
    if isinstance(schema_version, bool) or not isinstance(schema_version, int):
        raise SemanticDecisionCodecError(
            f"schema_version must be int, got {type(schema_version).__name__}"
        )
    if schema_version != SEMANTIC_DECISION_SCHEMA_VERSION:
        raise SemanticDecisionCodecError(
            f"unsupported schema_version {schema_version}; only version "
            f"{SEMANTIC_DECISION_SCHEMA_VERSION} is supported"
        )
    if not isinstance(payload, dict):
        raise SemanticDecisionCodecError(
            f"payload must be a mapping, got {type(payload).__name__}"
        )
    _refuse_floats_anywhere(payload, "top-level")
    try:
        return _decode_v1_payload(payload)
    except SemanticDecisionCodecError:
        raise
    except (TypeError, ValueError):
        raise SemanticDecisionCodecError(
            "stored semantic decision payload violates the v1 contract"
        ) from None
