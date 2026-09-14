"""Versioned codec for ComparableResearchResult (PRODUCT-INTEL.7C-A).

Pure research-layer serialisation. Encodes a ComparableResearchResult into a
versioned JSON-serialisable dict and decodes the persisted payload back into
the canonical contract object.

This module may import stdlib, domain contracts/enums, and existing research
contracts. It must not import Django, runs, web, execution, providers,
evaluation, network libraries, or filesystem libraries.

No dataclasses.asdict, no pickle, no generic object framework, no float.
"""

from __future__ import annotations

from datetime import datetime as _datetime
from decimal import Decimal, InvalidOperation
from typing import Any, Mapping

from product_intelligence.domain.errors import DomainValidationError
from product_intelligence.domain.models import ProductIdentity
from product_intelligence.research.comparable_candidates import (
    ComparableCandidate,
    ComparableCandidateAssessment,
    ComparableCandidateObservation,
    ComparableCandidateSource,
    CandidateDisposition,
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
from product_intelligence.research.specifications import (
    CategorySchema,
    NormalizedSpecificationObservation,
    ProductSpecificationSet,
    ResolutionState,
    SourceAuthority,
    SpecificationDefinition,
    SpecificationObservation,
    SpecificationResolution,
    SpecificationValue,
    SpecificationValueKind,
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
    SpecificationValueKind: {m.value: m for m in SpecificationValueKind},
    CandidateDisposition: {m.value: m for m in CandidateDisposition},
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


def _dec_bool(raw: object, path: str) -> bool:
    if not isinstance(raw, bool):
        raise ComparableResultCodecError(
            f"{path}: expected bool, got {type(raw).__name__}"
        )
    return raw


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


def _dec_datetime(raw: object, path: str) -> _datetime:
    if not isinstance(raw, str):
        raise ComparableResultCodecError(
            f"{path}: expected ISO-8601 datetime string, got {type(raw).__name__}"
        )
    try:
        return _datetime.fromisoformat(raw)
    except (ValueError, TypeError):
        raise ComparableResultCodecError(
            f"{path}: malformed ISO-8601 datetime"
        ) from None


def _enc_datetime(dt: _datetime) -> str:
    return dt.isoformat()


# ---------------------------------------------------------------------------
# SpecificationValue encoding (str | Decimal | bool)
# ---------------------------------------------------------------------------


def _enc_spec_value(obj: SpecificationValue) -> dict[str, object]:
    val = obj.value
    if isinstance(val, bool):
        return {"type": "bool", "value": val}
    if type(val) is Decimal:
        return {"type": "decimal", "value": str(val)}
    if isinstance(val, str):
        return {"type": "str", "value": val}
    raise TypeError(f"SpecificationValue has unsupported value type {type(val).__name__}")


def _dec_spec_value(data: dict[str, object], path: str) -> SpecificationValue:
    _check_no_extra_keys(data, {"type", "value"}, path)
    vtype = _dec_str(_dec_required_key(data, "type", path), f"{path}.type")
    raw = _dec_required_key(data, "value", path)

    if vtype == "bool":
        if not isinstance(raw, bool):
            raise ComparableResultCodecError(
                f"{path}.value: expected bool for type=bool"
            )
        return SpecificationValue(value=raw)
    elif vtype == "decimal":
        return SpecificationValue(value=_dec_decimal(raw, f"{path}.value"))
    elif vtype == "str":
        return SpecificationValue(value=_dec_str(raw, f"{path}.value"))
    else:
        raise ComparableResultCodecError(
            f"{path}.type: unknown value type {vtype!r}"
        )


# ---------------------------------------------------------------------------
# SpecificationDefinition encoding
# ---------------------------------------------------------------------------


def _enc_spec_definition(obj: SpecificationDefinition) -> dict[str, object]:
    return {
        "key": obj.key,
        "label": obj.label,
        "value_kind": _enc_enum(obj.value_kind),
        "unit": obj.unit,
        "allowed_values": list(obj.allowed_values),
    }


def _dec_spec_definition(data: dict[str, object], path: str) -> SpecificationDefinition:
    _check_no_extra_keys(
        data, {"key", "label", "value_kind", "unit", "allowed_values"}, path
    )
    allowed_raw = _dec_list(
        _dec_required_key(data, "allowed_values", path), f"{path}.allowed_values"
    )
    return SpecificationDefinition(
        key=_dec_str(_dec_required_key(data, "key", path), f"{path}.key"),
        label=_dec_str(_dec_required_key(data, "label", path), f"{path}.label"),
        value_kind=_dec_enum(
            SpecificationValueKind,
            _dec_required_key(data, "value_kind", path),
            f"{path}.value_kind",
        ),
        unit=_dec_optional_str(
            _dec_required_key(data, "unit", path), f"{path}.unit"
        ),
        allowed_values=tuple(
            _dec_str(v, f"{path}.allowed_values[{i}]")
            for i, v in enumerate(allowed_raw)
        ),
    )


# ---------------------------------------------------------------------------
# CategorySchema encoding
# ---------------------------------------------------------------------------


def _enc_category_schema(obj: CategorySchema) -> dict[str, object]:
    return {
        "schema_id": obj.schema_id,
        "schema_version": obj.schema_version,
        "label": obj.label,
        "definitions": {
            k: _enc_spec_definition(v)
            for k, v in obj.definitions.items()
        },
    }


def _dec_category_schema(data: dict[str, object], path: str) -> CategorySchema:
    _check_no_extra_keys(
        data, {"schema_id", "schema_version", "label", "definitions"}, path
    )
    defs_raw = _dec_mapping(
        _dec_required_key(data, "definitions", path), f"{path}.definitions"
    )
    definitions = {
        k: _dec_spec_definition(
            _dec_mapping(v, f"{path}.definitions[{k!r}]"),
            f"{path}.definitions[{k!r}]",
        )
        for k, v in defs_raw.items()
    }
    return CategorySchema(
        schema_id=_dec_str(
            _dec_required_key(data, "schema_id", path), f"{path}.schema_id"
        ),
        schema_version=_dec_str(
            _dec_required_key(data, "schema_version", path),
            f"{path}.schema_version",
        ),
        label=_dec_str(_dec_required_key(data, "label", path), f"{path}.label"),
        definitions=definitions,
    )


# ---------------------------------------------------------------------------
# ProductIdentity encoding
# ---------------------------------------------------------------------------


def _enc_product_identity(obj: ProductIdentity) -> dict[str, object]:
    from product_intelligence.domain.enums import IdentityMatchType

    return {
        "manufacturer_part_number": obj.manufacturer_part_number,
        "normalized_part_number": obj.normalized_part_number,
        "match_type": _enc_enum(obj.match_type),
        "manufacturer": obj.manufacturer,
        "product_name": obj.product_name,
    }


def _dec_product_identity(data: dict[str, object], path: str) -> ProductIdentity:
    from product_intelligence.domain.enums import IdentityMatchType

    _check_no_extra_keys(
        data,
        {"manufacturer_part_number", "normalized_part_number",
         "match_type", "manufacturer", "product_name"},
        path,
    )
    return ProductIdentity(
        manufacturer_part_number=_dec_str(
            _dec_required_key(data, "manufacturer_part_number", path),
            f"{path}.manufacturer_part_number",
        ),
        normalized_part_number=_dec_optional_str(
            _dec_required_key(data, "normalized_part_number", path),
            f"{path}.normalized_part_number",
        ),
        match_type=_dec_enum(
            IdentityMatchType,
            _dec_required_key(data, "match_type", path),
            f"{path}.match_type",
        ),
        manufacturer=_dec_optional_str(
            _dec_required_key(data, "manufacturer", path), f"{path}.manufacturer"
        ),
        product_name=_dec_optional_str(
            _dec_required_key(data, "product_name", path), f"{path}.product_name"
        ),
    )


# ---------------------------------------------------------------------------
# SpecificationObservation encoding
# ---------------------------------------------------------------------------


def _enc_spec_observation(obj: SpecificationObservation) -> dict[str, object]:
    return {
        "product_identity": _enc_product_identity(obj.product_identity),
        "definition": _enc_spec_definition(obj.definition),
        "source_name": obj.source_name,
        "source_url": obj.source_url,
        "retrieved_at": _enc_datetime(obj.retrieved_at),
        "raw_value": obj.raw_value,
        "source_authority": _enc_enum(obj.source_authority),
        "raw_reference": obj.raw_reference,
    }


def _dec_spec_observation(
    data: dict[str, object], path: str,
    product_identity: ProductIdentity | None = None,
    definition: SpecificationDefinition | None = None,
) -> SpecificationObservation:
    """Decode a SpecificationObservation, optionally reusing canonical
    product_identity and definition objects for identity binding."""
    _check_no_extra_keys(
        data,
        {"product_identity", "definition", "source_name", "source_url",
         "retrieved_at", "raw_value", "source_authority", "raw_reference"},
        path,
    )
    # If canonical objects are provided, use them for identity binding.
    # Otherwise decode from payload.
    if product_identity is None:
        product_identity = _dec_product_identity(
            _dec_mapping(
                _dec_required_key(data, "product_identity", path),
                f"{path}.product_identity",
            ),
            f"{path}.product_identity",
        )
    if definition is None:
        definition = _dec_spec_definition(
            _dec_mapping(
                _dec_required_key(data, "definition", path),
                f"{path}.definition",
            ),
            f"{path}.definition",
        )

    return SpecificationObservation(
        product_identity=product_identity,
        definition=definition,
        source_name=_dec_str(
            _dec_required_key(data, "source_name", path), f"{path}.source_name"
        ),
        source_url=_dec_str(
            _dec_required_key(data, "source_url", path), f"{path}.source_url"
        ),
        retrieved_at=_dec_datetime(
            _dec_required_key(data, "retrieved_at", path), f"{path}.retrieved_at"
        ),
        raw_value=_dec_str(
            _dec_required_key(data, "raw_value", path), f"{path}.raw_value"
        ),
        source_authority=_dec_enum(
            SourceAuthority,
            _dec_required_key(data, "source_authority", path),
            f"{path}.source_authority",
        ),
        raw_reference=_dec_optional_str(
            _dec_required_key(data, "raw_reference", path), f"{path}.raw_reference"
        ),
    )


# ---------------------------------------------------------------------------
# NormalizedSpecificationObservation encoding
# ---------------------------------------------------------------------------


def _enc_normalized_spec_observation(
    obj: NormalizedSpecificationObservation,
) -> dict[str, object]:
    payload: dict[str, object] = {
        "observation": _enc_spec_observation(obj.observation),
        "normalization_issue": obj.normalization_issue,
    }
    if obj.canonical_value is not None:
        payload["canonical_value"] = _enc_spec_value(obj.canonical_value)
    else:
        payload["canonical_value"] = None
    return payload


def _dec_normalized_spec_observation(
    data: dict[str, object], path: str,
    product_identity: ProductIdentity | None = None,
    definition: SpecificationDefinition | None = None,
) -> NormalizedSpecificationObservation:
    _check_no_extra_keys(
        data, {"observation", "canonical_value", "normalization_issue"}, path
    )
    obs_data = _dec_mapping(
        _dec_required_key(data, "observation", path), f"{path}.observation"
    )
    observation = _dec_spec_observation(
        obs_data, f"{path}.observation",
        product_identity=product_identity,
        definition=definition,
    )
    canonical_value_raw = _dec_required_key(data, "canonical_value", path)
    canonical_value = (
        _dec_spec_value(
            _dec_mapping(canonical_value_raw, f"{path}.canonical_value"),
            f"{path}.canonical_value",
        )
        if canonical_value_raw is not None
        else None
    )
    normalization_issue = _dec_optional_str(
        _dec_required_key(data, "normalization_issue", path),
        f"{path}.normalization_issue",
    )
    return NormalizedSpecificationObservation(
        observation=observation,
        canonical_value=canonical_value,
        normalization_issue=normalization_issue,
    )


# ---------------------------------------------------------------------------
# SpecificationResolution encoding
# ---------------------------------------------------------------------------


def _enc_spec_resolution(obj: SpecificationResolution) -> dict[str, object]:
    return {
        "product_identity": _enc_product_identity(obj.product_identity),
        "definition": _enc_spec_definition(obj.definition),
        "state": _enc_enum(obj.state),
        "resolved_value": (
            _enc_spec_value(obj.resolved_value)
            if obj.resolved_value is not None
            else None
        ),
        "evidence": [
            _enc_normalized_spec_observation(e) for e in obj.evidence
        ],
    }


def _dec_spec_resolution(
    data: dict[str, object], path: str,
) -> SpecificationResolution:
    _check_no_extra_keys(
        data, {"product_identity", "definition", "state",
               "resolved_value", "evidence"},
        path,
    )
    # Decode canonical product_identity and definition first,
    # then reuse them for evidence observations (identity binding).
    product_identity = _dec_product_identity(
        _dec_mapping(
            _dec_required_key(data, "product_identity", path),
            f"{path}.product_identity",
        ),
        f"{path}.product_identity",
    )
    definition = _dec_spec_definition(
        _dec_mapping(
            _dec_required_key(data, "definition", path),
            f"{path}.definition",
        ),
        f"{path}.definition",
    )
    evidence_raw = _dec_list(
        _dec_required_key(data, "evidence", path), f"{path}.evidence"
    )
    evidence = tuple(
        _dec_normalized_spec_observation(
            _dec_mapping(item, f"{path}.evidence[{i}]"),
            f"{path}.evidence[{i}]",
            product_identity=product_identity,
            definition=definition,
        )
        for i, item in enumerate(evidence_raw)
    )
    resolved_value_raw = _dec_required_key(data, "resolved_value", path)
    resolved_value = (
        _dec_spec_value(
            _dec_mapping(resolved_value_raw, f"{path}.resolved_value"),
            f"{path}.resolved_value",
        )
        if resolved_value_raw is not None
        else None
    )
    state = _dec_enum(
        ResolutionState,
        _dec_required_key(data, "state", path),
        f"{path}.state",
    )

    return SpecificationResolution(
        product_identity=product_identity,
        definition=definition,
        state=state,
        resolved_value=resolved_value,
        evidence=evidence,
    )


# ---------------------------------------------------------------------------
# ProductSpecificationSet encoding
# ---------------------------------------------------------------------------


def _enc_product_specification_set(obj: ProductSpecificationSet) -> dict[str, object]:
    return {
        "product_identity": _enc_product_identity(obj.product_identity),
        "category_schema": _enc_category_schema(obj.category_schema),
        "resolutions": {
            k: _enc_spec_resolution(v)
            for k, v in obj.resolutions.items()
        },
    }


def _dec_product_specification_set(
    data: dict[str, object], path: str,
) -> ProductSpecificationSet:
    _check_no_extra_keys(
        data, {"product_identity", "category_schema", "resolutions"}, path
    )
    resolutions_raw = _dec_mapping(
        _dec_required_key(data, "resolutions", path), f"{path}.resolutions"
    )
    resolutions = {
        k: _dec_spec_resolution(
            _dec_mapping(v, f"{path}.resolutions[{k!r}]"),
            f"{path}.resolutions[{k!r}]",
        )
        for k, v in resolutions_raw.items()
    }
    return ProductSpecificationSet(
        product_identity=_dec_product_identity(
            _dec_mapping(
                _dec_required_key(data, "product_identity", path),
                f"{path}.product_identity",
            ),
            f"{path}.product_identity",
        ),
        category_schema=_dec_category_schema(
            _dec_mapping(
                _dec_required_key(data, "category_schema", path),
                f"{path}.category_schema",
            ),
            f"{path}.category_schema",
        ),
        resolutions=resolutions,
    )


# ---------------------------------------------------------------------------
# ComparableCandidate encoding
# ---------------------------------------------------------------------------


def _enc_comparable_candidate_source(
    obj: ComparableCandidateSource,
) -> dict[str, object]:
    return {
        "source_name": obj.source_name,
        "source_url": obj.source_url,
        "source_authority": _enc_enum(obj.source_authority),
    }


def _enc_comparable_candidate_observation(
    obj: ComparableCandidateObservation,
) -> dict[str, object]:
    return {
        "manufacturer_part_number_raw": obj.manufacturer_part_number_raw,
        "product_name_raw": obj.product_name_raw,
        "source_name": obj.source_name,
        "source_url": obj.source_url,
        "retrieved_at": _enc_datetime(obj.retrieved_at),
        "source_authority": _enc_enum(obj.source_authority),
        "raw_reference": obj.raw_reference,
    }


def _enc_comparable_candidate_assessment(
    obj: ComparableCandidateAssessment,
) -> dict[str, object]:
    return {
        "target_identity": _enc_product_identity(obj.target_identity),
        "observation": _enc_comparable_candidate_observation(obj.observation),
        "normalized_part_number": obj.normalized_part_number,
        "disposition": _enc_enum(obj.disposition),
    }


def _enc_comparable_candidate(obj: ComparableCandidate) -> dict[str, object]:
    return {
        "manufacturer_part_number": obj.manufacturer_part_number,
        "normalized_part_number": obj.normalized_part_number,
        "evidence": [
            _enc_comparable_candidate_assessment(e) for e in obj.evidence
        ],
    }


# ---------------------------------------------------------------------------
# Authority / Datasheet / Enrichment encoding
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


def _enc_product_enrichment_audit(
    obj: ProductEnrichmentAudit,
) -> dict[str, object]:
    return {
        "target_identity": _enc_product_identity(obj.target_identity),
        "authority_audit": [
            _enc_authority_attempt_result(a) for a in obj.authority_audit
        ],
        "datasheet_audit": [
            _enc_datasheet_attempt_result(a) for a in obj.datasheet_audit
        ],
        "specification_set": (
            _enc_product_specification_set(obj.specification_set)
            if obj.specification_set is not None
            else None
        ),
    }


def _enc_evidence_source_reference(
    obj: EvidenceSourceReference,
) -> dict[str, object]:
    return {
        "source_name": obj.source_name,
        "source_url": obj.source_url,
        "layer": _enc_enum(obj.layer),
    }


def _enc_field_assessment_result(
    obj: FieldAssessmentResult,
) -> dict[str, object]:
    return {
        "field_name": obj.field_name,
        "target_value": obj.target_value,
        "candidate_value": obj.candidate_value,
        "target_evidence": [
            _enc_evidence_source_reference(e) for e in obj.target_evidence
        ],
        "candidate_evidence": [
            _enc_evidence_source_reference(e) for e in obj.candidate_evidence
        ],
    }


def _enc_comparable_candidate_result(
    obj: ComparableCandidateResult,
) -> dict[str, object]:
    return {
        "candidate": _enc_comparable_candidate(obj.candidate),
        "enrichment_audit": _enc_product_enrichment_audit(obj.enrichment_audit),
        "field_assessments": [
            _enc_field_assessment_result(fa) for fa in obj.field_assessments
        ],
    }


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
        "candidate_enrichment_audits": [
            _enc_product_enrichment_audit(a)
            for a in result.candidate_enrichment_audits
        ],
    }


# ---------------------------------------------------------------------------
# Decode helpers — V1
# ---------------------------------------------------------------------------


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


def _dec_comparable_candidate_source(
    data: dict[str, object], path: str,
) -> ComparableCandidateSource:
    _check_no_extra_keys(
        data, {"source_name", "source_url", "source_authority"}, path
    )
    return ComparableCandidateSource(
        source_name=_dec_str(
            _dec_required_key(data, "source_name", path), f"{path}.source_name"
        ),
        source_url=_dec_str(
            _dec_required_key(data, "source_url", path), f"{path}.source_url"
        ),
        source_authority=_dec_enum(
            SourceAuthority,
            _dec_required_key(data, "source_authority", path),
            f"{path}.source_authority",
        ),
    )


def _dec_comparable_candidate_observation(
    data: dict[str, object], path: str,
) -> ComparableCandidateObservation:
    _check_no_extra_keys(
        data,
        {"manufacturer_part_number_raw", "product_name_raw", "source_name",
         "source_url", "retrieved_at", "source_authority", "raw_reference"},
        path,
    )
    return ComparableCandidateObservation(
        manufacturer_part_number_raw=_dec_str(
            _dec_required_key(data, "manufacturer_part_number_raw", path),
            f"{path}.manufacturer_part_number_raw",
        ),
        product_name_raw=_dec_optional_str(
            _dec_required_key(data, "product_name_raw", path),
            f"{path}.product_name_raw",
        ),
        source_name=_dec_str(
            _dec_required_key(data, "source_name", path), f"{path}.source_name"
        ),
        source_url=_dec_str(
            _dec_required_key(data, "source_url", path), f"{path}.source_url"
        ),
        retrieved_at=_dec_datetime(
            _dec_required_key(data, "retrieved_at", path), f"{path}.retrieved_at"
        ),
        source_authority=_dec_enum(
            SourceAuthority,
            _dec_required_key(data, "source_authority", path),
            f"{path}.source_authority",
        ),
        raw_reference=_dec_optional_str(
            _dec_required_key(data, "raw_reference", path), f"{path}.raw_reference"
        ),
    )


def _dec_comparable_candidate_assessment(
    data: dict[str, object], path: str,
) -> ComparableCandidateAssessment:
    _check_no_extra_keys(
        data,
        {"target_identity", "observation", "normalized_part_number", "disposition"},
        path,
    )
    return ComparableCandidateAssessment(
        target_identity=_dec_product_identity(
            _dec_mapping(
                _dec_required_key(data, "target_identity", path),
                f"{path}.target_identity",
            ),
            f"{path}.target_identity",
        ),
        observation=_dec_comparable_candidate_observation(
            _dec_mapping(
                _dec_required_key(data, "observation", path),
                f"{path}.observation",
            ),
            f"{path}.observation",
        ),
        normalized_part_number=_dec_str(
            _dec_required_key(data, "normalized_part_number", path),
            f"{path}.normalized_part_number",
        ),
        disposition=_dec_enum(
            CandidateDisposition,
            _dec_required_key(data, "disposition", path),
            f"{path}.disposition",
        ),
    )


def _dec_comparable_candidate(
    data: dict[str, object], path: str,
) -> ComparableCandidate:
    _check_no_extra_keys(
        data, {"manufacturer_part_number", "normalized_part_number", "evidence"},
        path,
    )
    evidence_raw = _dec_list(
        _dec_required_key(data, "evidence", path), f"{path}.evidence"
    )
    evidence = tuple(
        _dec_comparable_candidate_assessment(
            _dec_mapping(item, f"{path}.evidence[{i}]"),
            f"{path}.evidence[{i}]",
        )
        for i, item in enumerate(evidence_raw)
    )
    return ComparableCandidate(
        manufacturer_part_number=_dec_str(
            _dec_required_key(data, "manufacturer_part_number", path),
            f"{path}.manufacturer_part_number",
        ),
        normalized_part_number=_dec_str(
            _dec_required_key(data, "normalized_part_number", path),
            f"{path}.normalized_part_number",
        ),
        evidence=evidence,
    )


def _dec_product_enrichment_audit(
    data: dict[str, object], path: str,
) -> ProductEnrichmentAudit:
    _check_no_extra_keys(
        data,
        {"target_identity", "authority_audit", "datasheet_audit",
         "specification_set"},
        path,
    )
    authority_raw = _dec_list(
        _dec_required_key(data, "authority_audit", path), f"{path}.authority_audit"
    )
    authority_audit = tuple(
        _dec_authority_attempt_result(
            _dec_mapping(item, f"{path}.authority_audit[{i}]"),
            f"{path}.authority_audit[{i}]",
        )
        for i, item in enumerate(authority_raw)
    )
    datasheet_raw = _dec_list(
        _dec_required_key(data, "datasheet_audit", path), f"{path}.datasheet_audit"
    )
    datasheet_audit = tuple(
        _dec_datasheet_attempt_result(
            _dec_mapping(item, f"{path}.datasheet_audit[{i}]"),
            f"{path}.datasheet_audit[{i}]",
        )
        for i, item in enumerate(datasheet_raw)
    )
    spec_set_raw = _dec_required_key(data, "specification_set", path)
    specification_set = (
        _dec_product_specification_set(
            _dec_mapping(spec_set_raw, f"{path}.specification_set"),
            f"{path}.specification_set",
        )
        if spec_set_raw is not None
        else None
    )
    return ProductEnrichmentAudit(
        target_identity=_dec_product_identity(
            _dec_mapping(
                _dec_required_key(data, "target_identity", path),
                f"{path}.target_identity",
            ),
            f"{path}.target_identity",
        ),
        authority_audit=authority_audit,
        datasheet_audit=datasheet_audit,
        specification_set=specification_set,
    )


def _dec_evidence_source_reference(
    data: dict[str, object], path: str,
) -> EvidenceSourceReference:
    _check_no_extra_keys(data, {"source_name", "source_url", "layer"}, path)
    return EvidenceSourceReference(
        source_name=_dec_str(
            _dec_required_key(data, "source_name", path), f"{path}.source_name"
        ),
        source_url=_dec_str(
            _dec_required_key(data, "source_url", path), f"{path}.source_url"
        ),
        layer=_dec_enum(
            EvidenceLayer,
            _dec_required_key(data, "layer", path),
            f"{path}.layer",
        ),
    )


def _dec_field_assessment_result(
    data: dict[str, object], path: str,
) -> FieldAssessmentResult:
    _check_no_extra_keys(
        data,
        {"field_name", "target_value", "candidate_value",
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
    return FieldAssessmentResult(
        field_name=_dec_str(
            _dec_required_key(data, "field_name", path), f"{path}.field_name"
        ),
        target_value=_dec_optional_str(
            _dec_required_key(data, "target_value", path), f"{path}.target_value"
        ),
        candidate_value=_dec_optional_str(
            _dec_required_key(data, "candidate_value", path),
            f"{path}.candidate_value",
        ),
        target_evidence=target_evidence,
        candidate_evidence=candidate_evidence,
    )


def _dec_comparable_candidate_result(
    data: dict[str, object], path: str,
) -> ComparableCandidateResult:
    _check_no_extra_keys(
        data, {"candidate", "enrichment_audit", "field_assessments"}, path
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
        candidate=_dec_comparable_candidate(
            _dec_mapping(
                _dec_required_key(data, "candidate", path),
                f"{path}.candidate",
            ),
            f"{path}.candidate",
        ),
        enrichment_audit=_dec_product_enrichment_audit(
            _dec_mapping(
                _dec_required_key(data, "enrichment_audit", path),
                f"{path}.enrichment_audit",
            ),
            f"{path}.enrichment_audit",
        ),
        field_assessments=field_assessments,
    )


# ---------------------------------------------------------------------------
# Decode — V1
# ---------------------------------------------------------------------------


def _decode_v1_payload(payload: dict[str, object]) -> ComparableResearchResult:
    """Decode a V1 payload into a validated ComparableResearchResult."""
    _check_no_extra_keys(
        payload,
        {"kind", "target_mpn", "target_manufacturer", "target_enrichment_audit",
         "authority_audit", "candidates", "candidate_enrichment_audits"},
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
    candidate_audits_raw = _dec_list(
        _dec_required_key(payload, "candidate_enrichment_audits", "top-level"),
        "candidate_enrichment_audits",
    )
    candidate_enrichment_audits = tuple(
        _dec_product_enrichment_audit(
            _dec_mapping(item, f"candidate_enrichment_audits[{i}]"),
            f"candidate_enrichment_audits[{i}]",
        )
        for i, item in enumerate(candidate_audits_raw)
    )

    return ComparableResearchResult(
        kind=kind,
        target_mpn=target_mpn,
        target_manufacturer=target_manufacturer,
        target_enrichment_audit=target_enrichment_audit,
        authority_audit=authority_audit,
        candidates=candidates,
        candidate_enrichment_audits=candidate_enrichment_audits,
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
