"""Strict loading, decoding, and integrity verification of the Q3-A
Semantic V2 qualification corpus.

The corpus is the independently labeled benchmark the offline
qualification harness measures the frozen Semantic V2 contract against.
Everything here is FAIL CLOSED:

* the document schema is exact (missing AND extra keys rejected);
* every bounded vocabulary is checked against the frozen contract
  enums (unknown values rejected);
* the per-case digest and the whole-corpus digest are verified on load
  (silent label mutation after evaluation is detectable);
* reconstructing a case runs the REAL frozen ``SemanticMatchCaseV2``
  constructor — a contract-negative payload is rejected by the
  contract itself, and the rejection is classified against the bounded
  rejection vocabulary.

This module imports the frozen research contract (authorized by the
Q3-A exact-allowlist exception in
``tests/research/test_research_identity_boundaries.py``).
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Final

from product_intelligence.research import (
    ALWAYS_HARD_CONFLICT_CLASSES,
    ConflictClass,
    ContextProvenance,
    IdentityRelationshipSignal,
    IdentityStateAssessmentV2,
    IdentityStateV2,
    ProductEvidenceDimension,
    ProductEvidenceFactV2,
    ProductEvidenceProfileV2,
    RelationshipRequirement,
    UncertainSubstateV2,
    V2_CONTRACT_BINDING,
    derive_product_evidence_quality,
    substate_relationship_requirement,
)
from product_intelligence.research import (
    CandidateProductEvidenceSource,
    ConflictSubstateV2,
    UnevaluableSubstateV2,
    VerifiedSubstateV2,
)
from product_intelligence.evaluation.semantic_v2.canonical import (
    UTC_INSTANT_PATTERN,
    assert_json_native,
    canonical_sha256,
)
from product_intelligence.evaluation.semantic_v2.fixtures import (
    AMBIGUITY_CLASSES,
    CATEGORIES,
    CANDIDATE_FACT_SOURCES,
    CASE_CLASSES,
    CHALLENGE_TAGS,
    CONFLICT_CLASSES,
    CORPUS_ID,
    DECISIONS,
    EVIDENCE_KINDS,
    FORBIDDEN_EVIDENCE_TOKENS,
    INPUT_SHAPES,
    LABEL_SOURCE_KINDS,
    MISSING_DIMENSIONS,
    PRODUCT_FACT_DIMENSIONS,
    REJECTION_CLASSES,
    REVIEWER_STATUSES,
    SALES_UNIT_KINDS,
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
    SemanticMatchCaseV2,
    TargetEvidenceV2,
    TargetIdentifierRelationKindV2,
)

__all__ = [
    "AMBIGUOUS_CASE_CLASS",
    "AUTHORITATIVE_CASE_CLASS",
    "CONTRACT_NEGATIVE_CASE_CLASS",
    "CORPUS_SCHEMA_VERSION",
    "CorpusCase",
    "CorpusBundle",
    "CorpusError",
    "CorpusIntegrityError",
    "CorpusInputRejectionError",
    "CorpusSchemaError",
    "REJECTION_CLASSES",
    "build_manifest_document",
    "decode_match_case",
    "load_corpus",
    "reject_class_for",
    "verify_manifest",
]

CORPUS_SCHEMA_VERSION: Final[int] = 1
"""Corpus schema version 1. Any other value fails closed (unknown
corpus versions are never best-effort interpreted)."""

AUTHORITATIVE_CASE_CLASS: Final[str] = "AUTHORITATIVE"
AMBIGUOUS_CASE_CLASS: Final[str] = "AMBIGUOUS"
CONTRACT_NEGATIVE_CASE_CLASS: Final[str] = "CONTRACT_NEGATIVE"


class CorpusError(Exception):
    """Bounded corpus failure (document level)."""


class CorpusSchemaError(CorpusError):
    """The corpus document violates the strict corpus schema."""


class CorpusIntegrityError(CorpusError):
    """The corpus digests do not verify (mutation / version mismatch)."""


class CorpusInputRejectionError(Exception):
    """A case input payload is rejected by the frozen V2 input contract.

    ``rejection_class`` is a bounded vocabulary member; ``detail`` is
    the deterministic stage that fired. Contract-negative corpus cases
    are EXPECTED to raise this (the harness verifies the expected
    class); any other case raising it is a corpus defect (FAIL_CLOSED).
    """

    def __init__(self, rejection_class: str, detail: str) -> None:
        if rejection_class not in REJECTION_CLASSES:
            raise ValueError(
                f"rejection_class must be one of {sorted(REJECTION_CLASSES)}, "
                f"got {rejection_class!r}"
            )
        super().__init__(f"[{rejection_class}] {detail}")
        self.rejection_class = rejection_class
        self.detail = detail


_CASE_ID_PATTERN = re.compile(r"^V2Q-[A-Z0-9][A-Z0-9-]*$")
_SHA256_PATTERN = re.compile(r"^[0-9a-f]{64}$")

_STATE_VALUES: Final[frozenset[str]] = frozenset(
    s.value for s in IdentityStateV2
)
_SUBSTATE_VALUES: Final[dict[str, Any]] = {
    **{m.value: m for m in VerifiedSubstateV2},
    **{m.value: m for m in UncertainSubstateV2},
    **{m.value: m for m in ConflictSubstateV2},
    **{m.value: m for m in UnevaluableSubstateV2},
}
_SIGNAL_VALUES: Final[frozenset[str]] = frozenset(
    s.value for s in IdentityRelationshipSignal
)
_REQUIREMENT_VALUES: Final[frozenset[str]] = frozenset(
    r.value for r in RelationshipRequirement
)
_PROVENANCE_VALUES: Final[frozenset[str]] = frozenset(
    p.value for p in ContextProvenance
)
_CONFLICT_VALUES: Final[frozenset[str]] = frozenset(
    c.value for c in ConflictClass
)
_DIMENSION_VALUES: Final[frozenset[str]] = frozenset(
    d.value for d in ProductEvidenceDimension
)
_AUTH_SOURCE_VALUES: Final[frozenset[str]] = frozenset(
    s.value for s in CandidateProductEvidenceSource
)


def _reject(
    rejection_class: str, detail: str, *, path: str | None = None
) -> CorpusInputRejectionError:
    location = f" ({path})" if path else ""
    return CorpusInputRejectionError(rejection_class, detail + location)


def _dec_str(value: Any, path: str) -> str:
    if not isinstance(value, str) or not value:
        raise _reject(
            "INVALID_INPUT_SCHEMA",
            f"expected a non-empty str, got {type(value).__name__}",
            path=path,
        )
    return value


def _dec_optional_str(value: Any, path: str) -> str | None:
    if value is None:
        return None
    return _dec_str(value, path)


def _dec_str_enum(value: Any, allowed: frozenset[str], path: str) -> str:
    if not isinstance(value, str) or value not in allowed:
        raise _reject(
            "INVALID_INPUT_SCHEMA",
            f"expected one of {sorted(allowed)}, got {value!r}",
            path=path,
        )
    return value


def _dec_exact_keys(value: Any, keys: set[str], path: str) -> None:
    if not isinstance(value, dict):
        raise _reject(
            "INVALID_INPUT_SCHEMA",
            f"expected an object, got {type(value).__name__}",
            path=path,
        )
    missing = keys - set(value.keys())
    if missing:
        raise _reject(
            "INVALID_INPUT_SCHEMA",
            f"missing required keys: {sorted(missing)}",
            path=path,
        )
    unknown = set(value.keys()) - keys
    if unknown:
        raise _reject(
            "INVALID_INPUT_SCHEMA",
            f"unknown keys: {sorted(unknown)}",
            path=path,
        )


def _dec_utc_instant(value: Any, path: str) -> str:
    if (
        not isinstance(value, str)
        or not UTC_INSTANT_PATTERN.match(value)
    ):
        raise _reject(
            "INVALID_INPUT_SCHEMA",
            f"expected an ISO-8601 UTC instant, got {value!r}",
            path=path,
        )
    try:
        parsed = datetime.fromisoformat(value[:-1] + "+00:00")
    except ValueError:
        raise _reject(
            "INVALID_INPUT_SCHEMA",
            f"invalid ISO-8601 UTC instant {value!r}",
            path=path,
        ) from None
    if parsed.utcoffset() is None:
        raise _reject(
            "INVALID_INPUT_SCHEMA",
            f"non-UTC instant {value!r}",
            path=path,
        )
    return value


def _dec_sha256(value: Any, path: str) -> str:
    if not isinstance(value, str) or not _SHA256_PATTERN.match(value):
        raise _reject(
            "INVALID_INPUT_SCHEMA",
            f"expected a 64-hex SHA-256 digest, got {value!r}",
            path=path,
        )
    return value


# ---------------------------------------------------------------------------
# Typed case-payload decode (stages mirror the frozen constructor order)
# ---------------------------------------------------------------------------


def _dec_target(payload: dict[str, Any]) -> TargetEvidenceV2:
    target = payload["target"]
    path = "target"
    _dec_exact_keys(
        target,
        {"mpn", "description_raw_text", "reviewed_context"},
        path,
    )
    reviewed_raw = target["reviewed_context"]
    reviewed = None
    if reviewed_raw is not None:
        rpath = f"{path}.reviewed_context"
        _dec_exact_keys(
            reviewed_raw,
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
            },
            rpath,
        )
        relation_kind = _dec_str_enum(
            reviewed_raw["relation_kind"],
            frozenset(k.value for k in TargetIdentifierRelationKindV2),
            f"{rpath}.relation_kind",
        )
        family = reviewed_raw["relation_family_part_numbers"]
        if (
            not isinstance(family, list)
            or not family
            or any(not isinstance(f, str) or not f for f in family)
            or len(set(family)) != len(family)
        ):
            raise _reject(
                "INVALID_INPUT_SCHEMA",
                "relation_family_part_numbers must be a non-empty "
                "unique list of non-empty strings",
                path=f"{rpath}.relation_family_part_numbers",
            )
        _dec_utc_instant(reviewed_raw["retrieved_at"], f"{rpath}.retrieved_at")
        _dec_sha256(
            reviewed_raw["evidence_body_sha256"],
            f"{rpath}.evidence_body_sha256",
        )
        for key in (
            "manufacturer",
            "category",
            "matched_base_part_number",
            "source_name",
            "source_url",
        ):
            _dec_str(reviewed_raw[key], f"{rpath}.{key}")
        reviewed = ReviewedTargetContextV2(
            manufacturer=reviewed_raw["manufacturer"],
            category=reviewed_raw["category"],
            matched_base_part_number=reviewed_raw["matched_base_part_number"],
            relation_kind=TargetIdentifierRelationKindV2(relation_kind),
            relation_family_part_numbers=tuple(family),
            source_name=reviewed_raw["source_name"],
            source_url=reviewed_raw["source_url"],
            retrieved_at=reviewed_raw["retrieved_at"],
            evidence_body_sha256=reviewed_raw["evidence_body_sha256"],
        )
    return TargetEvidenceV2(
        mpn=_dec_str(target["mpn"], f"{path}.mpn"),
        description_raw_text=_dec_optional_str(
            target["description_raw_text"], f"{path}.description_raw_text"
        ),
        reviewed_context=reviewed,
    )


def _dec_fact(
    value: Any, path: str
) -> CandidateObservationFactV2 | None:
    if value is None:
        return None
    _dec_exact_keys(value, {"value", "source"}, path)
    source = _dec_str_enum(
        value["source"], CANDIDATE_FACT_SOURCES, f"{path}.source"
    )
    return CandidateObservationFactV2(
        value=_dec_str(value["value"], f"{path}.value"),
        source=CandidateEvidenceSourceV2(source),
    )


def _dec_product(payload: dict[str, Any]) -> CandidateProductEvidenceV2:
    product = payload["candidate"]["product"]
    path = "candidate.product"
    keys = set(PRODUCT_FACT_DIMENSIONS) | {
        "raw_title_text",
        "raw_specification_text",
    }
    _dec_exact_keys(product, keys, path)
    return CandidateProductEvidenceV2(
        **{
            dim: _dec_fact(product[dim], f"{path}.{dim}")
            for dim in PRODUCT_FACT_DIMENSIONS
        },
        raw_title_text=_dec_optional_str(
            product["raw_title_text"], f"{path}.raw_title_text"
        ),
        raw_specification_text=_dec_optional_str(
            product["raw_specification_text"],
            f"{path}.raw_specification_text",
        ),
    )


def _dec_sales_unit(value: Any) -> CandidateSalesUnitEvidenceV2:
    path = "candidate.commercial.sales_unit"
    _dec_exact_keys(
        value,
        {"state", "kind", "quantity", "raw_detail", "source"},
        path,
    )
    state = _dec_str_enum(
        value["state"],
        frozenset(s.value for s in PackagingEvidenceStateV2),
        f"{path}.state",
    )
    kind_raw = value["kind"]
    kind = None
    if kind_raw is not None:
        kind = SalesUnitKindV2(
            _dec_str_enum(kind_raw, SALES_UNIT_KINDS, f"{path}.kind")
        )
    quantity = value["quantity"]
    if quantity is not None and (
        type(quantity) is not int or quantity < 1
    ):
        raise _reject(
            "INVALID_INPUT_SCHEMA",
            f"quantity must be a positive int, got {quantity!r}",
            path=f"{path}.quantity",
        )
    source_raw = value["source"]
    source = None
    if source_raw is not None:
        source = CandidateEvidenceSourceV2(
            _dec_str_enum(
                source_raw, CANDIDATE_FACT_SOURCES, f"{path}.source"
            )
        )
    detail = _dec_optional_str(value["raw_detail"], f"{path}.raw_detail")
    try:
        return CandidateSalesUnitEvidenceV2(
            state=PackagingEvidenceStateV2(state),
            kind=kind,
            quantity=quantity,
            raw_detail=detail,
            source=source,
        )
    except (ValueError, TypeError) as exc:
        raise _reject(
            "INVALID_INPUT_SCHEMA", f"sales unit cross-state: {exc}"
        ) from exc


def _dec_commercial(payload: dict[str, Any]) -> CandidateCommercialEvidenceV2:
    commercial = payload["candidate"]["commercial"]
    path = "candidate.commercial"
    _dec_exact_keys(
        commercial,
        {
            "condition",
            "price",
            "currency",
            "availability",
            "seller",
            "offer_url",
            "sales_unit",
        },
        path,
    )
    return CandidateCommercialEvidenceV2(
        condition=_dec_fact(commercial["condition"], f"{path}.condition"),
        price=_dec_fact(commercial["price"], f"{path}.price"),
        currency=_dec_fact(commercial["currency"], f"{path}.currency"),
        availability=_dec_fact(
            commercial["availability"], f"{path}.availability"
        ),
        seller=_dec_fact(commercial["seller"], f"{path}.seller"),
        offer_url=_dec_optional_str(commercial["offer_url"], f"{path}.offer_url"),
        sales_unit=_dec_sales_unit(commercial["sales_unit"]),
    )


def _dec_profile(payload: dict[str, Any]) -> ProductEvidenceProfileV2:
    profile_raw = payload["product_evidence"]
    path = "product_evidence"
    _dec_exact_keys(
        profile_raw,
        {"has_usable_product_title", "matched_facts"},
        path,
    )
    usable = profile_raw["has_usable_product_title"]
    if type(usable) is not bool:
        raise _reject(
            "INVALID_INPUT_SCHEMA",
            f"has_usable_product_title must be a bool, got {usable!r}",
            path=f"{path}.has_usable_product_title",
        )
    facts_raw = profile_raw["matched_facts"]
    if not isinstance(facts_raw, list):
        raise _reject(
            "INVALID_INPUT_SCHEMA",
            "matched_facts must be a list",
            path=f"{path}.matched_facts",
        )
    facts: set[ProductEvidenceFactV2] = set()
    for i, fact in enumerate(facts_raw):
        fpath = f"{path}.matched_facts[{i}]"
        _dec_exact_keys(fact, {"dimension", "sources"}, fpath)
        dimension = _dec_str_enum(
            fact["dimension"], _DIMENSION_VALUES, f"{fpath}.dimension"
        )
        sources_raw = fact["sources"]
        if (
            not isinstance(sources_raw, list)
            or not sources_raw
            or any(
                not isinstance(s, str) or s not in _AUTH_SOURCE_VALUES
                for s in sources_raw
            )
            or len(set(sources_raw)) != len(sources_raw)
        ):
            raise _reject(
                "INVALID_INPUT_SCHEMA",
                "sources must be a non-empty unique list drawn from "
                f"{sorted(_AUTH_SOURCE_VALUES)}",
                path=f"{fpath}.sources",
            )
        facts.add(
            ProductEvidenceFactV2(
                ProductEvidenceDimension(dimension),
                frozenset(CandidateProductEvidenceSource(s) for s in sources_raw),
            )
        )
    try:
        return ProductEvidenceProfileV2(
            has_usable_product_title=usable,
            matched_facts=frozenset(facts),
        )
    except (ValueError, TypeError) as exc:
        raise _reject(
            "INVALID_INPUT_SCHEMA", f"product evidence cross-state: {exc}"
        ) from exc


def decode_match_case(payload: dict[str, Any]) -> SemanticMatchCaseV2:
    """Reconstruct the real frozen ``SemanticMatchCaseV2`` from one
    corpus input payload.

    Raises ``CorpusInputRejectionError`` with a bounded rejection class
    when the payload is outside the frozen V2 input contract. The REAL
    case constructor is the final arbiter (no approximation); the stage
    probes only NAME the rejection class.
    """
    assert isinstance(payload, dict)
    _dec_exact_keys(
        payload,
        {
            "case_id",
            "target",
            "candidate",
            "deterministic_identity_context",
            "context_provenance",
            "product_evidence",
        },
        "input_payload",
    )

    # -- stage 1: strict shape / bounded enums (schema axis) -------------
    target = _dec_target(payload)
    candidate_path = "candidate"
    cand = payload["candidate"]
    _dec_exact_keys(
        cand,
        {"source_url", "mpn_field", "sku", "evidence_source", "product",
         "commercial"},
        candidate_path,
    )
    product = _dec_product(payload)
    commercial = _dec_commercial(payload)
    dic = payload["deterministic_identity_context"]
    _dec_exact_keys(
        dic,
        {
            "identity_state",
            "substate",
            "primary_relationship_signal",
            "relationship_signals",
            "normalized_requested_part_number",
            "normalized_candidate_part_number",
            "relationship_requirement",
        },
        "deterministic_identity_context",
    )
    state_value = _dec_str_enum(
        dic["identity_state"], _STATE_VALUES,
        "deterministic_identity_context.identity_state",
    )
    substate_value = dic["substate"]
    if (
        not isinstance(substate_value, str)
        or substate_value not in _SUBSTATE_VALUES
    ):
        raise _reject(
            "INVALID_INPUT_SCHEMA",
            f"unknown substate {substate_value!r}",
            path="deterministic_identity_context.substate",
        )
    primary_value = _dec_str_enum(
        dic["primary_relationship_signal"], _SIGNAL_VALUES,
        "deterministic_identity_context.primary_relationship_signal",
    )
    signals_raw = dic["relationship_signals"]
    if (
        not isinstance(signals_raw, list)
        or not signals_raw
        or any(
            not isinstance(s, str) or s not in _SIGNAL_VALUES
            for s in signals_raw
        )
        or len(set(signals_raw)) != len(signals_raw)
    ):
        raise _reject(
            "INVALID_INPUT_SCHEMA",
            "relationship_signals must be a non-empty unique list of "
            f"bounded signals",
            path="deterministic_identity_context.relationship_signals",
        )
    requirement_value = _dec_str_enum(
        dic["relationship_requirement"], _REQUIREMENT_VALUES,
        "deterministic_identity_context.relationship_requirement",
    )
    req_key = _dec_str_or_empty(
        dic["normalized_requested_part_number"],
        "deterministic_identity_context.normalized_requested_part_number",
    )
    cand_key = _dec_str_or_empty(
        dic["normalized_candidate_part_number"],
        "deterministic_identity_context.normalized_candidate_part_number",
    )
    provenances_raw = payload["context_provenance"]
    if (
        not isinstance(provenances_raw, list)
        or any(
            not isinstance(p, str) or p not in _PROVENANCE_VALUES
            for p in provenances_raw
        )
        or len(set(provenances_raw)) != len(provenances_raw)
    ):
        raise _reject(
            "INVALID_INPUT_SCHEMA",
            "context_provenance must be a unique list of bounded "
            "provenance classes",
            path="context_provenance",
        )
    profile = _dec_profile(payload)

    # -- stage 2: deterministic context legitimacy (frozen S2-A) --------
    state = IdentityStateV2(state_value)
    substate = _SUBSTATE_VALUES[substate_value]
    signals = frozenset(IdentityRelationshipSignal(s) for s in signals_raw)
    try:
        context = IdentityStateAssessmentV2(
            state=state,
            substate=substate,
            relationship_signals=signals,
            normalized_requested_part_number=req_key,
            normalized_candidate_part_number=cand_key,
        )
    except ValueError as exc:
        raise _reject(
            "FOREIGN_DETERMINISTIC_CONTEXT", str(exc)
        ) from exc

    # -- stage 3: the V2 input admits only semantic entry points --------
    if state is not IdentityStateV2.DETERMINISTIC_UNCERTAIN:
        raise _reject(
            "NON_UNCERTAIN_STATE",
            f"state {state_value} is outside the V2 semantic entry "
            "point (DETERMINISTIC_UNCERTAIN only)",
        )
    if primary_value != context.primary_relationship_signal.value:
        raise _reject(
            "FOREIGN_DETERMINISTIC_CONTEXT",
            "primary_relationship_signal disagrees with the recorded "
            "signals",
        )

    # -- stage 4: the frozen requirement table --------------------------
    expected_requirement = substate_relationship_requirement(
        substate, context.primary_relationship_signal
    )
    if requirement_value != expected_requirement.value:
        raise _reject(
            "FOREIGN_DETERMINISTIC_CONTEXT",
            f"relationship_requirement {requirement_value!r} disagrees "
            f"with the frozen table ({expected_requirement.value!r})",
        )

    # -- stage 5: state/evidence consistency (frozen) -------------------
    if (
        substate is UncertainSubstateV2.U4_NO_MPN
        and not profile.has_usable_product_title
    ):
        raise _reject(
            "FOREIGN_DETERMINISTIC_CONTEXT",
            "U4_NO_MPN requires a usable product title; the payload "
            "contradicts the state",
        )
    provenances = frozenset(
        ContextProvenance(p) for p in provenances_raw
    )
    try:
        derive_product_evidence_quality(profile, provenances)
    except ValueError as exc:
        raise _reject("UNSUPPORTED_EVIDENCE", str(exc)) from exc

    # -- stage 6: the REAL frozen constructor is the arbiter ------------
    try:
        return SemanticMatchCaseV2(
            case_id=_dec_str(payload["case_id"], "case_id"),
            target=target,
            candidate_source_url=_dec_str(
                cand["source_url"], "candidate.source_url"
            ),
            candidate_mpn_field=_dec_optional_str(
                cand["mpn_field"], "candidate.mpn_field"
            ),
            candidate_sku=_dec_optional_str(
                cand["sku"], "candidate.sku"
            ),
            candidate_evidence_source=_dec_str(
                cand["evidence_source"], "candidate.evidence_source"
            ),
            candidate_product=product,
            candidate_commercial=commercial,
            identity_state=context.state,
            substate=context.substate,
            primary_relationship_signal=context.primary_relationship_signal,
            relationship_signals=context.relationship_signals,
            normalized_requested_part_number=(
                context.normalized_requested_part_number
            ),
            normalized_candidate_part_number=(
                context.normalized_candidate_part_number
            ),
            relationship_requirement=expected_requirement,
            context_provenances=provenances,
            product_evidence=profile,
        )
    except CorpusInputRejectionError:
        raise
    except (ValueError, TypeError) as exc:
        # Backstop: every stage above already probed the constructor's
        # semantic checks; an unexpected failure is classified by the
        # probe order (deterministic).
        raise _reject("INVALID_INPUT_SCHEMA", f"constructor: {exc}") from exc


def _dec_str_or_empty(value: Any, path: str) -> str:
    if not isinstance(value, str):
        raise _reject(
            "INVALID_INPUT_SCHEMA",
            f"expected a str (possibly empty), got {type(value).__name__}",
            path=path,
        )
    return value


def reject_class_for(payload: dict[str, Any]) -> str | None:
    """The bounded rejection class of one payload, or None when the
    payload reconstructs a legitimate V2 input case."""
    try:
        decode_match_case(payload)
    except CorpusInputRejectionError as exc:
        return exc.rejection_class
    return None


# ---------------------------------------------------------------------------
# Corpus document loading
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class CorpusCase:
    """One decoded, digest-verified corpus case."""

    case_id: str
    category: str
    case_class: str
    evidence_kind: str
    input_shape: str
    challenge_tags: tuple[str, ...]
    substate: str
    primary_signal: str
    input_payload: dict[str, Any]
    expected: dict[str, Any]
    label: dict[str, Any]
    case_digest: str

    @property
    def is_semantic(self) -> bool:
        return self.case_class != CONTRACT_NEGATIVE_CASE_CLASS

    @property
    def is_authoritative(self) -> bool:
        return self.case_class == AUTHORITATIVE_CASE_CLASS

    @property
    def is_ambiguous(self) -> bool:
        return self.case_class == AMBIGUOUS_CASE_CLASS

    @property
    def expected_decision(self) -> str | None:
        return self.expected.get("decision")

    @property
    def acceptable_decisions(self) -> tuple[str, ...] | None:
        value = self.expected.get("acceptable_decisions")
        return tuple(value) if value is not None else None

    @property
    def expected_conflict_classes(self) -> frozenset[str]:
        return frozenset(self.expected.get("conflict_classes", ()))

    @property
    def expected_hard_conflict_classes(self) -> frozenset[str]:
        hard = {c.value for c in ALWAYS_HARD_CONFLICT_CLASSES}
        return self.expected_conflict_classes & hard

    def build_semantic_case(self) -> SemanticMatchCaseV2:
        """Reconstruct the real frozen V2 input case for this payload.

        Raises ``CorpusInputRejectionError`` (bounded class) when the
        payload is contract-negative or otherwise outside the frozen
        input contract."""
        return decode_match_case(self.input_payload)


@dataclass(frozen=True)
class CorpusBundle:
    """The verified corpus: document + decoded cases + identity."""

    document: dict[str, Any]
    cases: tuple[CorpusCase, ...]
    corpus_id: str
    corpus_version: str
    corpus_digest: str
    semantic_contract_binding: tuple[str, str, int, int, str]

    def case(self, case_id: str) -> CorpusCase:
        for case in self.cases:
            if case.case_id == case_id:
                return case
        raise KeyError(case_id)

    @property
    def semantic_cases(self) -> tuple[CorpusCase, ...]:
        return tuple(c for c in self.cases if c.is_semantic)

    @property
    def contract_negative_cases(self) -> tuple[CorpusCase, ...]:
        return tuple(
            c for c in self.cases if not c.is_semantic
        )


def _doc_exact_keys(value: Any, keys: set[str], path: str) -> None:
    """Document-level exact-key check (raises CorpusSchemaError; the
    payload-level ``_dec_exact_keys`` raises the bounded input
    rejection instead)."""
    if not isinstance(value, dict):
        raise CorpusSchemaError(
            f"{path}: expected an object, got {type(value).__name__}"
        )
    missing = keys - set(value.keys())
    if missing:
        raise CorpusSchemaError(
            f"{path}: missing required keys {sorted(missing)}"
        )
    unknown = set(value.keys()) - keys
    if unknown:
        raise CorpusSchemaError(
            f"{path}: unknown keys {sorted(unknown)}"
        )


def _doc_str(value: Any, path: str) -> str:
    if not isinstance(value, str) or not value:
        raise CorpusSchemaError(
            f"{path}: expected a non-empty str, got {value!r}"
        )
    return value


def _doc_str_enum(value: Any, allowed: frozenset[str], path: str) -> str:
    if not isinstance(value, str) or value not in allowed:
        raise CorpusSchemaError(
            f"{path}: expected one of {sorted(allowed)}, got {value!r}"
        )
    return value


def _doc_utc_instant(value: Any, path: str) -> str:
    if not isinstance(value, str) or not UTC_INSTANT_PATTERN.match(value):
        raise CorpusSchemaError(
            f"{path}: expected an ISO-8601 UTC instant, got {value!r}"
        )
    try:
        datetime.fromisoformat(value[:-1] + "+00:00")
    except ValueError:
        raise CorpusSchemaError(
            f"{path}: invalid ISO-8601 UTC instant {value!r}"
        ) from None
    return value


def _check_label_fields(case_id: str, label: dict[str, Any]) -> None:
    _doc_exact_keys(
        label,
        {
            "source_kind",
            "source",
            "evidence",
            "reviewer",
            "reviewer_status",
            "ambiguity",
        },
        f"case {case_id}: label",
    )
    _doc_str_enum(
        label["source_kind"], LABEL_SOURCE_KINDS, f"case {case_id}: label.source_kind"
    )
    _doc_str(label["source"], f"case {case_id}: label.source")
    _doc_str(label["evidence"], f"case {case_id}: label.evidence")
    _doc_str(label["reviewer"], f"case {case_id}: label.reviewer")
    _doc_str_enum(
        label["reviewer_status"],
        REVIEWER_STATUSES,
        f"case {case_id}: label.reviewer_status",
    )
    _doc_str_enum(
        label["ambiguity"], AMBIGUITY_CLASSES, f"case {case_id}: label.ambiguity"
    )
    # Mechanical ground-truth independence guard: label text must not
    # name candidate model output or a candidate model.
    for field_name in ("source", "evidence"):
        text = str(label[field_name]).lower()
        for token in FORBIDDEN_EVIDENCE_TOKENS:
            if token in text:
                raise CorpusSchemaError(
                    f"case {case_id}: label.{field_name} names "
                    f"{token!r}; ground truth must be independent of any "
                    "model output"
                )
    # A REAL_MARKET label must cite a retrieved market source.
    if label["source_kind"] == "REVIEWED_SOURCE_GROUNDED" and (
        "recorded" not in str(label["source"]).lower()
        and "uat" not in str(label["source"]).lower()
        and "fixture" not in str(label["source"]).lower()
        and "catalog" not in str(label["source"]).lower()
    ):
        raise CorpusSchemaError(
            f"case {case_id}: a REVIEWED_SOURCE_GROUNDED label must cite "
            "a recorded source (fixture / UAT / catalog)"
        )


def _check_expected(case_id: str, expected: dict[str, Any]) -> None:
    _doc_exact_keys(
        expected,
        {
            "disposition",
            "rejection_class",
            "decision",
            "acceptable_decisions",
            "conflict_classes",
            "missing_dimensions",
            "expected_reason_code",
            "commercial_sales_unit_safety",
        },
        f"case {case_id}: expected",
    )
    disposition = expected["disposition"]
    if disposition not in {"SEMANTIC_EVALUATION", "INPUT_REJECTED"}:
        raise CorpusSchemaError(
            f"case {case_id}: unknown disposition {disposition!r}"
        )
    if disposition == "INPUT_REJECTED":
        if expected["decision"] is not None:
            raise CorpusSchemaError(
                f"case {case_id}: an INPUT_REJECTED expectation carries "
                "no semantic decision"
            )
        _doc_str_enum(
            expected["rejection_class"],
            REJECTION_CLASSES,
            f"case {case_id}: expected.rejection_class",
        )
    else:
        if expected["rejection_class"] is not None:
            raise CorpusSchemaError(
                f"case {case_id}: a SEMANTIC_EVALUATION expectation "
                "carries no rejection class"
            )
        _doc_str_enum(
            expected["decision"], DECISIONS, f"case {case_id}: expected.decision"
        )
        acceptable = expected["acceptable_decisions"]
        if (
            not isinstance(acceptable, list)
            or not acceptable
            or any(d not in DECISIONS for d in acceptable)
            or expected["decision"] not in acceptable
        ):
            raise CorpusSchemaError(
                f"case {case_id}: acceptable_decisions must be a "
                "non-empty bounded list containing the expected decision"
            )
        for cc in expected["conflict_classes"]:
            if cc not in CONFLICT_CLASSES:
                raise CorpusSchemaError(
                    f"case {case_id}: unknown conflict class {cc!r}"
                )
        for dim in expected["missing_dimensions"]:
            if dim not in MISSING_DIMENSIONS:
                raise CorpusSchemaError(
                    f"case {case_id}: unknown missing dimension {dim!r}"
                )
        if expected["expected_reason_code"] is not None and (
            not isinstance(expected["expected_reason_code"], str)
            or not expected["expected_reason_code"]
        ):
            raise CorpusSchemaError(
                f"case {case_id}: expected_reason_code must be a str"
            )
    if type(expected["commercial_sales_unit_safety"]) is not bool:
        raise CorpusSchemaError(
            f"case {case_id}: commercial_sales_unit_safety must be a bool"
        )


def _decode_case(raw: dict[str, Any], index: int) -> CorpusCase:
    case_id = raw.get("case_id", f"<index {index}>")
    _doc_exact_keys(
        raw,
        {
            "case_id",
            "category",
            "case_class",
            "evidence_kind",
            "input_shape",
            "challenge_tags",
            "substate",
            "primary_signal",
            "input_payload",
            "expected",
            "label",
            "case_digest",
        },
        f"case {case_id}",
    )
    if not isinstance(raw["case_id"], str) or not _CASE_ID_PATTERN.match(
        raw["case_id"]
    ):
        raise CorpusSchemaError(
            f"case {case_id}: case_id must match {_CASE_ID_PATTERN.pattern}"
        )
    _doc_str_enum(raw["category"], CATEGORIES, f"case {case_id}: category")
    _doc_str_enum(
        raw["case_class"], CASE_CLASSES, f"case {case_id}: case_class"
    )
    _doc_str_enum(
        raw["evidence_kind"], EVIDENCE_KINDS, f"case {case_id}: evidence_kind"
    )
    _doc_str_enum(
        raw["input_shape"], INPUT_SHAPES, f"case {case_id}: input_shape"
    )
    tags = raw["challenge_tags"]
    if (
        not isinstance(tags, list)
        or not all(isinstance(t, str) and t in CHALLENGE_TAGS for t in tags)
        or len(set(tags)) != len(tags)
        or tags != sorted(tags)
    ):
        raise CorpusSchemaError(
            f"case {case_id}: challenge_tags must be a sorted unique "
            "list of bounded tags"
        )
    _doc_str(raw["substate"], f"case {case_id}: substate")
    _doc_str(raw["primary_signal"], f"case {case_id}: primary_signal")
    payload = raw["input_payload"]
    if not isinstance(payload, dict):
        raise CorpusSchemaError(
            f"case {case_id}: input_payload must be an object"
        )
    assert_json_native(payload, f"case {case_id}: input_payload")
    _check_expected(case_id, raw["expected"])
    _check_label_fields(case_id, raw["label"])
    _dec_sha256(raw["case_digest"], f"case {case_id}: case_digest")
    state_view = {k: v for k, v in raw.items() if k != "case_digest"}
    if canonical_sha256(state_view) != raw["case_digest"]:
        raise CorpusIntegrityError(
            f"case {case_id}: case_digest does not verify (the case was "
            "mutated after sealing)"
        )
    # A REAL_MARKET evidence kind is reserved for independently
    # retrieved market sources; corpus 1.0.0 ships none.
    if raw["evidence_kind"] == "REAL_MARKET":
        raise CorpusSchemaError(
            f"case {case_id}: evidence_kind REAL_MARKET requires an "
            "independently retrieved market source with URL and "
            "retrieval instant; corpus 1.0.0 ships no real-market cases"
        )
    return CorpusCase(
        case_id=raw["case_id"],
        category=raw["category"],
        case_class=raw["case_class"],
        evidence_kind=raw["evidence_kind"],
        input_shape=raw["input_shape"],
        challenge_tags=tuple(tags),
        substate=raw["substate"],
        primary_signal=raw["primary_signal"],
        input_payload=payload,
        expected=raw["expected"],
        label=raw["label"],
        case_digest=raw["case_digest"],
    )


def load_corpus(path: str | Path) -> CorpusBundle:
    """Load + strictly verify one corpus document.

    Raises ``CorpusSchemaError`` (unknown version / bad shape),
    ``CorpusIntegrityError`` (digest mismatch), or ``CorpusError``
    (unrecoverable document problem). A corpus whose declared
    ``semantic_contract_binding`` differs from the frozen production
    binding raises ``CorpusIntegrityError``: the harness only qualifies
    the exact frozen contract, never a lookalike.
    """
    file = Path(path)
    if not file.is_file():
        raise CorpusError(f"corpus file not found: {file}")
    try:
        document = json.loads(file.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise CorpusSchemaError(f"corpus is not valid JSON: {exc}") from exc

    _doc_exact_keys(
        document,
        {
            "corpus_id",
            "corpus_schema_version",
            "corpus_version",
            "corpus_label",
            "created_utc",
            "semantic_contract_binding",
            "cases",
            "label_revisions",
            "corpus_digest",
        },
        "corpus document",
    )
    if document["corpus_schema_version"] != CORPUS_SCHEMA_VERSION:
        raise CorpusSchemaError(
            f"unknown corpus schema version "
            f"{document['corpus_schema_version']!r}; only "
            f"{CORPUS_SCHEMA_VERSION} is supported (fail closed)"
        )
    if document["corpus_id"] != CORPUS_ID:
        raise CorpusSchemaError(
            f"corpus_id {document['corpus_id']!r} is not the Q3-A "
            f"qualification corpus {CORPUS_ID!r}"
        )
    _doc_str(document["corpus_version"], "corpus document: corpus_version")
    _doc_str(document["corpus_label"], "corpus document: corpus_label")
    _doc_utc_instant(document["created_utc"], "corpus document: created_utc")

    binding = document["semantic_contract_binding"]
    if (
        not isinstance(binding, list)
        or tuple(binding) != tuple(V2_CONTRACT_BINDING)
    ):
        raise CorpusIntegrityError(
            f"corpus semantic_contract_binding {binding!r} differs from "
            f"the frozen production binding {list(V2_CONTRACT_BINDING)!r}; "
            "the harness only qualifies the exact frozen contract"
        )

    raw_cases = document["cases"]
    if not isinstance(raw_cases, list) or not raw_cases:
        raise CorpusSchemaError("corpus must carry a non-empty case list")
    cases = tuple(_decode_case(raw, i) for i, raw in enumerate(raw_cases))
    seen: set[str] = set()
    for case in cases:
        if case.case_id in seen:
            raise CorpusSchemaError(
                f"duplicate case id {case.case_id!r}; case ids must be "
                "unique (fail closed)"
            )
        seen.add(case.case_id)

    revisions = document["label_revisions"]
    if not isinstance(revisions, list):
        raise CorpusSchemaError("label_revisions must be a list")
    _check_label_revisions(revisions, seen)

    state = {
        k: v
        for k, v in document.items()
        if k not in ("label_revisions", "corpus_digest")
    }
    if canonical_sha256(state) != document["corpus_digest"]:
        raise CorpusIntegrityError(
            "corpus_digest does not verify (the corpus state was mutated "
            "after sealing)"
        )

    return CorpusBundle(
        document=document,
        cases=cases,
        corpus_id=document["corpus_id"],
        corpus_version=document["corpus_version"],
        corpus_digest=document["corpus_digest"],
        semantic_contract_binding=tuple(binding),  # type: ignore[arg-type]
    )


def _check_label_revisions(
    revisions: list[Any], case_ids: set[str]
) -> None:
    seen_revisions: set[int] = set()
    for i, revision in enumerate(revisions):
        rpath = f"label_revisions[{i}]"
        _doc_exact_keys(
            revision,
            {
                "revision",
                "case_id",
                "utc",
                "reason_class",
                "statement",
                "digest_before",
                "digest_after",
            },
            rpath,
        )
        number = revision["revision"]
        if type(number) is not int or number < 1:
            raise CorpusSchemaError(f"{rpath}.revision must be a positive int")
        if number in seen_revisions:
            raise CorpusSchemaError(f"{rpath}.revision is not unique")
        seen_revisions.add(number)
        if revision["case_id"] not in case_ids:
            raise CorpusSchemaError(
                f"{rpath}.case_id {revision['case_id']!r} is not a corpus case"
            )
        _doc_utc_instant(revision["utc"], f"{rpath}.utc")
        if revision["reason_class"] not in {"A", "B", "C", "D"}:
            raise CorpusSchemaError(
                f"{rpath}.reason_class must be A (old expectation was "
                "factually wrong), B (authoritative source changed), C "
                "(case definition was ambiguous), or D (product behaviour "
                "requirement intentionally changed)"
            )
        _dec_str(revision["statement"], f"{rpath}.statement")
        _dec_sha256(revision["digest_before"], f"{rpath}.digest_before")
        _dec_sha256(revision["digest_after"], f"{rpath}.digest_after")
    expected_numbers = set(range(1, len(revisions) + 1))
    if seen_revisions != expected_numbers:
        raise CorpusSchemaError(
            "label_revisions must be numbered 1..N without gaps"
        )


# ---------------------------------------------------------------------------
# Manifest
# ---------------------------------------------------------------------------


def build_manifest_document(document: dict[str, Any]) -> dict[str, Any]:
    """The reproducible manifest for one verified corpus document."""
    cases = [
        {
            "case_id": case["case_id"],
            "case_class": case["case_class"],
            "category": case["category"],
            "substate": case["substate"],
            "primary_signal": case["primary_signal"],
            "case_digest": case["case_digest"],
        }
        for case in document["cases"]
    ]
    state = {
        "manifest_schema_version": 1,
        "corpus_id": document["corpus_id"],
        "corpus_version": document["corpus_version"],
        "semantic_contract_binding": list(document["semantic_contract_binding"]),
        "corpus_digest": document["corpus_digest"],
        "case_count": len(cases),
        "cases": cases,
    }
    state["manifest_digest"] = canonical_sha256(state)
    return state


def verify_manifest(
    corpus: CorpusBundle, manifest: dict[str, Any]
) -> None:
    """Verify a manifest against one corpus (fail closed)."""
    expected = build_manifest_document(corpus.document)
    if manifest != expected:
        raise CorpusIntegrityError(
            "manifest does not match the corpus document (regenerate the "
            "manifest from the exact corpus or restore the corpus)"
        )
