"""Versioned codec for ComparableResearchResult (PRODUCT-INTEL.7C-A).

Pure research-layer serialisation. Encodes a ComparableResearchResult into a
versioned JSON-serialisable dict and decodes the persisted payload back into
the canonical contract object.

This module may import stdlib, domain contracts/enums, and existing research
contracts. It must not import Django, runs, web, execution, providers,
evaluation, network libraries, or filesystem libraries.

No dataclasses.asdict, no pickle, no generic object framework, no float.

The codec encodes ONLY the corrected pure read-model projection:
    - AuthorityAttemptResult
    - DatasheetAttemptResult
    - ProductEnrichmentAudit (product_mpn + attempts only)
    - EvidenceSourceReference (with source_authority + retrieved_at)
    - FieldAssessmentResult (with comparison_state, resolution states, Decimal similarity)
    - ComparableCandidateResult (scalar MPN fields + scoring scalars)
    - ComparableResearchResult

It does NOT persist/encode the full raw graphs of:
    ProductIdentity, ComparableCandidate, ProductSpecificationSet,
    SpecificationResolution, NormalizedSpecificationObservation,
    SpecificationObservation — those are not fields of the corrected projection.

Decimal values are stored as strings. Enums are stored as their .value strings.
"""

from __future__ import annotations

from decimal import Decimal, InvalidOperation
from typing import Any

from product_intelligence.domain.errors import DomainValidationError
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
from product_intelligence.research.enterprise_ssd_similarity import (
    ComparisonState,
)
from product_intelligence.research.specifications import (
    ResolutionState,
    SourceAuthority,
)


# ---------------------------------------------------------------------------
# Public constants and exceptions
# ---------------------------------------------------------------------------

COMPARABLE_RESULT_SCHEMA_VERSION = 1
"""Current (and only supported) V1 schema version."""


class ComparableResultCodecError(ValueError):
    """Raised when a persisted payload cannot be decoded."""


# ---------------------------------------------------------------------------
# Enum registries
# ---------------------------------------------------------------------------

_STRING_ENUMS: dict[type, dict[str, object]] = {
    ComparableResultKind: {m.value: m for m in ComparableResultKind},
    AuthorityAuditOutcomeKind: {m.value: m for m in AuthorityAuditOutcomeKind},
    DatasheetAuditOutcomeKind: {m.value: m for m in DatasheetAuditOutcomeKind},
    EvidenceLayer: {m.value: m for m in EvidenceLayer},
    SourceAuthority: {m.value: m for m in SourceAuthority},
    ResolutionState: {m.value: m for m in ResolutionState},
    ComparisonState: {m.value: m for m in ComparisonState},
}


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _enc_enum(value: object) -> str:
    return value.value  # type: ignore[attr-defined]


def _dec_enum(cls: type, raw: object, path: str) -> object:
    if not isinstance(raw, str):
        raise ComparableResultCodecError(
            f"{path}: expected string for {cls.__name__}, got {type(raw).__name__}"
        )
    mapping = _STRING_ENUMS[cls]
    if raw not in mapping:
        raise ComparableResultCodecError(
            f"{path}: unknown {cls.__name__} value {raw!r}"
        )
    return mapping[raw]


def _dec_decimal(raw: object, path: str) -> Decimal:
    if isinstance(raw, bool):
        raise ComparableResultCodecError(f"{path}: expected Decimal string, got bool")
    if isinstance(raw, (int, float)):
        raise ComparableResultCodecError(
            f"{path}: Decimal must be stored as a string, got {type(raw).__name__}"
        )
    if not isinstance(raw, str):
        raise ComparableResultCodecError(
            f"{path}: expected Decimal string, got {type(raw).__name__}"
        )
    try:
        value = Decimal(raw)
    except InvalidOperation:
        raise ComparableResultCodecError(f"{path}: malformed Decimal string") from None
    if not value.is_finite():
        raise ComparableResultCodecError(f"{path}: Decimal must be finite; got {raw!r}")
    return value


def _dec_optional_decimal(raw: object | None, path: str) -> Decimal | None:
    if raw is None:
        return None
    return _dec_decimal(raw, path)


def _dec_int(raw: object, path: str) -> int:
    if isinstance(raw, bool):
        raise ComparableResultCodecError(f"{path}: expected int, got bool")
    if not isinstance(raw, int):
        raise ComparableResultCodecError(
            f"{path}: expected int, got {type(raw).__name__}"
        )
    return raw


def _dec_str(raw: object, path: str) -> str:
    if not isinstance(raw, str):
        raise ComparableResultCodecError(
            f"{path}: expected string, got {type(raw).__name__}"
        )
    return raw


def _dec_optional_str(raw: object | None, path: str) -> str | None:
    if raw is None:
        return None
    return _dec_str(raw, path)


def _dec_mapping(raw: object, path: str) -> dict[str, object]:
    if not isinstance(raw, dict):
        raise ComparableResultCodecError(
            f"{path}: expected mapping, got {type(raw).__name__}"
        )
    return raw


def _dec_list(raw: object, path: str) -> list[object]:
    if not isinstance(raw, list):
        raise ComparableResultCodecError(
            f"{path}: expected list, got {type(raw).__name__}"
        )
    return raw


def _dec_required_key(data: dict[str, object], key: str, path: str) -> object:
    if key not in data:
        raise ComparableResultCodecError(f"{path}: missing required key {key!r}")
    return data[key]


def _check_no_extra_keys(data: dict[str, object], allowed: set[str], path: str) -> None:
    extra = set(data.keys()) - allowed
    if extra:
        raise ComparableResultCodecError(f"{path}: unexpected keys {sorted(extra)}")


# ---------------------------------------------------------------------------
# AuthorityAttemptResult encoding
# ---------------------------------------------------------------------------


def _enc_authority_attempt_result(
    obj: AuthorityAttemptResult,
) -> dict[str, object]:
    return {
        "outcome": _enc_enum(obj.outcome),
        "source_name": obj.source_name,
        "source_url": obj.source_url,
        "matched_mpn": obj.matched_mpn,
        "raw_reference": obj.raw_reference,
    }


def _dec_authority_attempt_result(
    data: dict[str, object], path: str,
) -> AuthorityAttemptResult:
    _check_no_extra_keys(
        data,
        {"outcome", "source_name", "source_url", "matched_mpn", "raw_reference"},
        path,
    )
    return AuthorityAttemptResult(
        outcome=_dec_enum(
            AuthorityAuditOutcomeKind,
            _dec_required_key(data, "outcome", path),
            f"{path}.outcome",
        ),
        source_name=_dec_optional_str(
            _dec_required_key(data, "source_name", path), f"{path}.source_name"
        ),
        source_url=_dec_optional_str(
            _dec_required_key(data, "source_url", path), f"{path}.source_url"
        ),
        matched_mpn=_dec_optional_str(
            _dec_required_key(data, "matched_mpn", path), f"{path}.matched_mpn"
        ),
        raw_reference=_dec_optional_str(
            _dec_required_key(data, "raw_reference", path), f"{path}.raw_reference"
        ),
    )


# ---------------------------------------------------------------------------
# DatasheetAttemptResult encoding
# ---------------------------------------------------------------------------


def _enc_datasheet_attempt_result(
    obj: DatasheetAttemptResult,
) -> dict[str, object]:
    return {
        "outcome": _enc_enum(obj.outcome),
        "source_name": obj.source_name,
        "source_url": obj.source_url,
        "final_url": obj.final_url,
        "retrieved_at": obj.retrieved_at,
        "observation_count": obj.observation_count,
    }


def _dec_datasheet_attempt_result(
    data: dict[str, object], path: str,
) -> DatasheetAttemptResult:
    _check_no_extra_keys(
        data,
        {"outcome", "source_name", "source_url", "final_url",
         "retrieved_at", "observation_count"},
        path,
    )
    obs_count_raw = _dec_required_key(data, "observation_count", path)
    return DatasheetAttemptResult(
        outcome=_dec_enum(
            DatasheetAuditOutcomeKind,
            _dec_required_key(data, "outcome", path),
            f"{path}.outcome",
        ),
        source_name=_dec_optional_str(
            _dec_required_key(data, "source_name", path), f"{path}.source_name"
        ),
        source_url=_dec_optional_str(
            _dec_required_key(data, "source_url", path), f"{path}.source_url"
        ),
        final_url=_dec_optional_str(
            _dec_required_key(data, "final_url", path), f"{path}.final_url"
        ),
        retrieved_at=_dec_optional_str(
            _dec_required_key(data, "retrieved_at", path), f"{path}.retrieved_at"
        ),
        observation_count=(
            _dec_int(obs_count_raw, f"{path}.observation_count")
            if obs_count_raw is not None
            else None
        ),
    )


# ---------------------------------------------------------------------------
# ProductEnrichmentAudit encoding (pure projection: product_mpn + attempts)
# ---------------------------------------------------------------------------


def _enc_product_enrichment_audit(
    obj: ProductEnrichmentAudit,
) -> dict[str, object]:
    return {
        "product_mpn": obj.product_mpn,
        "attempts": [
            _enc_datasheet_attempt_result(a) for a in obj.attempts
        ],
    }


def _dec_product_enrichment_audit(
    data: dict[str, object], path: str,
) -> ProductEnrichmentAudit:
    _check_no_extra_keys(data, {"product_mpn", "attempts"}, path)
    attempts_raw = _dec_list(
        _dec_required_key(data, "attempts", path), f"{path}.attempts"
    )
    attempts = tuple(
        _dec_datasheet_attempt_result(
            _dec_mapping(item, f"{path}.attempts[{i}]"),
            f"{path}.attempts[{i}]",
        )
        for i, item in enumerate(attempts_raw)
    )
    return ProductEnrichmentAudit(
        product_mpn=_dec_str(
            _dec_required_key(data, "product_mpn", path), f"{path}.product_mpn"
        ),
        attempts=attempts,
    )


# ---------------------------------------------------------------------------
# EvidenceSourceReference encoding (with source_authority + retrieved_at)
# ---------------------------------------------------------------------------


def _enc_evidence_source_reference(
    obj: EvidenceSourceReference,
) -> dict[str, object]:
    return {
        "source_name": obj.source_name,
        "source_url": obj.source_url,
        "evidence_layer": _enc_enum(obj.evidence_layer),
        "source_authority": _enc_enum(obj.source_authority),
        "retrieved_at": obj.retrieved_at,
    }


def _dec_evidence_source_reference(
    data: dict[str, object], path: str,
) -> EvidenceSourceReference:
    _check_no_extra_keys(
        data, {"source_name", "source_url", "evidence_layer",
               "source_authority", "retrieved_at"},
        path,
    )
    return EvidenceSourceReference(
        source_name=_dec_str(
            _dec_required_key(data, "source_name", path), f"{path}.source_name"
        ),
        source_url=_dec_str(
            _dec_required_key(data, "source_url", path), f"{path}.source_url"
        ),
        evidence_layer=_dec_enum(
            EvidenceLayer,
            _dec_required_key(data, "evidence_layer", path),
            f"{path}.evidence_layer",
        ),
        source_authority=_dec_enum(
            SourceAuthority,
            _dec_required_key(data, "source_authority", path),
            f"{path}.source_authority",
        ),
        retrieved_at=_dec_str(
            _dec_required_key(data, "retrieved_at", path), f"{path}.retrieved_at"
        ),
    )


# ---------------------------------------------------------------------------
# FieldAssessmentResult encoding (with comparison_state, resolution states, Decimal)
# ---------------------------------------------------------------------------


def _enc_field_assessment_result(
    obj: FieldAssessmentResult,
) -> dict[str, object]:
    payload: dict[str, object] = {
        "definition_key": obj.definition_key,
        "comparison_state": _enc_enum(obj.comparison_state),
        "target_resolution_state": _enc_enum(obj.target_resolution_state),
        "candidate_resolution_state": _enc_enum(obj.candidate_resolution_state),
        "target_value": obj.target_value,
        "candidate_value": obj.candidate_value,
        "target_evidence": [
            _enc_evidence_source_reference(e) for e in obj.target_evidence
        ],
        "candidate_evidence": [
            _enc_evidence_source_reference(e) for e in obj.candidate_evidence
        ],
    }
    # field_similarity: Decimal stored as string, None when not SCORED
    if obj.field_similarity is not None:
        payload["field_similarity"] = str(obj.field_similarity)
    else:
        payload["field_similarity"] = None
    return payload


def _dec_field_assessment_result(
    data: dict[str, object], path: str,
) -> FieldAssessmentResult:
    _check_no_extra_keys(
        data,
        {"definition_key", "comparison_state", "target_resolution_state",
         "candidate_resolution_state", "field_similarity",
         "target_value", "candidate_value",
         "target_evidence", "candidate_evidence"},
        path,
    )
    target_ev_raw = _dec_list(
        _dec_required_key(data, "target_evidence", path), f"{path}.target_evidence"
    )
    target_evidence = tuple(
        _dec_evidence_source_reference(
            _dec_mapping(item, f"{path}.target_evidence[{i}]"),
            f"{path}.target_evidence[{i}]",
        )
        for i, item in enumerate(target_ev_raw)
    )
    candidate_ev_raw = _dec_list(
        _dec_required_key(data, "candidate_evidence", path),
        f"{path}.candidate_evidence",
    )
    candidate_evidence = tuple(
        _dec_evidence_source_reference(
            _dec_mapping(item, f"{path}.candidate_evidence[{i}]"),
            f"{path}.candidate_evidence[{i}]",
        )
        for i, item in enumerate(candidate_ev_raw)
    )
    field_similarity_raw = _dec_required_key(data, "field_similarity", path)
    return FieldAssessmentResult(
        definition_key=_dec_str(
            _dec_required_key(data, "definition_key", path), f"{path}.definition_key"
        ),
        comparison_state=_dec_enum(
            ComparisonState,
            _dec_required_key(data, "comparison_state", path),
            f"{path}.comparison_state",
        ),
        target_resolution_state=_dec_enum(
            ResolutionState,
            _dec_required_key(data, "target_resolution_state", path),
            f"{path}.target_resolution_state",
        ),
        candidate_resolution_state=_dec_enum(
            ResolutionState,
            _dec_required_key(data, "candidate_resolution_state", path),
            f"{path}.candidate_resolution_state",
        ),
        field_similarity=_dec_optional_decimal(
            field_similarity_raw, f"{path}.field_similarity"
        ),
        target_value=_dec_optional_str(
            _dec_required_key(data, "target_value", path), f"{path}.target_value"
        ),
        candidate_value=_dec_optional_str(
            _dec_required_key(data, "candidate_value", path), f"{path}.candidate_value"
        ),
        target_evidence=target_evidence,
        candidate_evidence=candidate_evidence,
    )


# ---------------------------------------------------------------------------
# ComparableCandidateResult encoding (pure scalar projection)
# ---------------------------------------------------------------------------


def _enc_comparable_candidate_result(
    obj: ComparableCandidateResult,
) -> dict[str, object]:
    payload: dict[str, object] = {
        "candidate_mpn": obj.candidate_mpn,
        "candidate_normalized_mpn": obj.candidate_normalized_mpn,
        "scored_field_count": obj.scored_field_count,
        "evidence_coverage": str(obj.evidence_coverage),
        "field_assessments": [
            _enc_field_assessment_result(fa) for fa in obj.field_assessments
        ],
        "enrichment_audit": _enc_product_enrichment_audit(obj.enrichment_audit),
    }
    if obj.observed_similarity is not None:
        payload["observed_similarity"] = str(obj.observed_similarity)
    else:
        payload["observed_similarity"] = None
    if obj.evidence_weighted_similarity is not None:
        payload["evidence_weighted_similarity"] = str(obj.evidence_weighted_similarity)
    else:
        payload["evidence_weighted_similarity"] = None
    return payload


def _dec_comparable_candidate_result(
    data: dict[str, object], path: str,
) -> ComparableCandidateResult:
    _check_no_extra_keys(
        data,
        {"candidate_mpn", "candidate_normalized_mpn",
         "scored_field_count", "evidence_coverage",
         "observed_similarity", "evidence_weighted_similarity",
         "field_assessments", "enrichment_audit"},
        path,
    )
    field_assessments_raw = _dec_list(
        _dec_required_key(data, "field_assessments", path),
        f"{path}.field_assessments",
    )
    field_assessments = tuple(
        _dec_field_assessment_result(
            _dec_mapping(item, f"{path}.field_assessments[{i}]"),
            f"{path}.field_assessments[{i}]",
        )
        for i, item in enumerate(field_assessments_raw)
    )
    return ComparableCandidateResult(
        candidate_mpn=_dec_str(
            _dec_required_key(data, "candidate_mpn", path), f"{path}.candidate_mpn"
        ),
        candidate_normalized_mpn=_dec_str(
            _dec_required_key(data, "candidate_normalized_mpn", path),
            f"{path}.candidate_normalized_mpn",
        ),
        scored_field_count=_dec_int(
            _dec_required_key(data, "scored_field_count", path),
            f"{path}.scored_field_count",
        ),
        evidence_coverage=_dec_decimal(
            _dec_required_key(data, "evidence_coverage", path),
            f"{path}.evidence_coverage",
        ),
        observed_similarity=_dec_optional_decimal(
            _dec_required_key(data, "observed_similarity", path),
            f"{path}.observed_similarity",
        ),
        evidence_weighted_similarity=_dec_optional_decimal(
            _dec_required_key(data, "evidence_weighted_similarity", path),
            f"{path}.evidence_weighted_similarity",
        ),
        field_assessments=field_assessments,
        enrichment_audit=_dec_product_enrichment_audit(
            _dec_mapping(
                _dec_required_key(data, "enrichment_audit", path),
                f"{path}.enrichment_audit",
            ),
            f"{path}.enrichment_audit",
        ),
    )


# ---------------------------------------------------------------------------
# Encode — V1
# ---------------------------------------------------------------------------


def encode_comparable_result(
    result: ComparableResearchResult,
) -> dict[str, object]:
    """Encode a ComparableResearchResult into a V1 JSON-serialisable dict."""
    if not isinstance(result, ComparableResearchResult):
        raise TypeError(
            f"expected ComparableResearchResult, got {type(result).__name__}"
        )

    return {
        "kind": _enc_enum(result.kind),
        "target_mpn": result.target_mpn,
        "target_manufacturer": result.target_manufacturer,
        "target_enrichment_audit": (
            _enc_product_enrichment_audit(result.target_enrichment_audit)
            if result.target_enrichment_audit is not None
            else None
        ),
        "authority_audit": [
            _enc_authority_attempt_result(a) for a in result.authority_audit
        ],
        "candidates": [
            _enc_comparable_candidate_result(c) for c in result.candidates
        ],
    }


# ---------------------------------------------------------------------------
# Decode — V1
# ---------------------------------------------------------------------------


def _decode_v1_payload(payload: dict[str, object]) -> ComparableResearchResult:
    """Decode a V1 payload into a validated ComparableResearchResult."""
    _check_no_extra_keys(
        payload,
        {"kind", "target_mpn", "target_manufacturer", "target_enrichment_audit",
         "authority_audit", "candidates"},
        "top-level",
    )

    kind = _dec_enum(
        ComparableResultKind,
        _dec_required_key(payload, "kind", "top-level"),
        "kind",
    )
    target_mpn = _dec_str(
        _dec_required_key(payload, "target_mpn", "top-level"), "target_mpn"
    )
    target_manufacturer = _dec_optional_str(
        _dec_required_key(payload, "target_manufacturer", "top-level"),
        "target_manufacturer",
    )
    target_enrichment_audit_raw = _dec_required_key(
        payload, "target_enrichment_audit", "top-level"
    )
    target_enrichment_audit = (
        _dec_product_enrichment_audit(
            _dec_mapping(target_enrichment_audit_raw, "target_enrichment_audit"),
            "target_enrichment_audit",
        )
        if target_enrichment_audit_raw is not None
        else None
    )
    authority_raw = _dec_list(
        _dec_required_key(payload, "authority_audit", "top-level"),
        "authority_audit",
    )
    authority_audit = tuple(
        _dec_authority_attempt_result(
            _dec_mapping(item, f"authority_audit[{i}]"),
            f"authority_audit[{i}]",
        )
        for i, item in enumerate(authority_raw)
    )
    candidates_raw = _dec_list(
        _dec_required_key(payload, "candidates", "top-level"), "candidates"
    )
    candidates = tuple(
        _dec_comparable_candidate_result(
            _dec_mapping(item, f"candidates[{i}]"),
            f"candidates[{i}]",
        )
        for i, item in enumerate(candidates_raw)
    )

    return ComparableResearchResult(
        kind=kind,
        target_mpn=target_mpn,
        target_manufacturer=target_manufacturer,
        target_enrichment_audit=target_enrichment_audit,
        authority_audit=authority_audit,
        candidates=candidates,
    )


def decode_comparable_result(
    payload: object,
    *,
    schema_version: int,
) -> ComparableResearchResult:
    """Decode a persisted payload into a ComparableResearchResult.

    Strict decode: unsupported schema_version, missing keys, extra keys,
    wrong types, unknown enums all raise ComparableResultCodecError.
    """
    if isinstance(schema_version, bool) or not isinstance(schema_version, int):
        raise ComparableResultCodecError(
            f"schema_version must be int, got {type(schema_version).__name__}"
        )
    if schema_version != COMPARABLE_RESULT_SCHEMA_VERSION:
        raise ComparableResultCodecError(
            f"unsupported schema_version {schema_version}; "
            f"only version {COMPARABLE_RESULT_SCHEMA_VERSION} is supported"
        )

    if not isinstance(payload, dict):
        raise ComparableResultCodecError(
            f"payload must be a mapping, got {type(payload).__name__}"
        )

    try:
        return _decode_v1_payload(payload)
    except ComparableResultCodecError:
        raise
    except (DomainValidationError, TypeError, ValueError):
        raise ComparableResultCodecError(
            "stored comparable result violates the V1 contract"
        ) from None
