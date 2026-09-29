"""Production promotion-regression harness for semantic PRIMARY candidates
(PRODUCT-INTEL.SEMANTIC.PROMOTION-REGRESSION).

What this is
------------
A SEPARATE, evaluation-only regression facility for the question:

    "If a formally qualified challenger were considered for the production
     PRIMARY seat, can we test it against production-shaped
     semantic/execution authority boundaries WITHOUT changing the
     production route?"

It is deliberately distinct from semantic QUALIFICATION
(``product_intelligence.evaluation.semantic.runner`` + the frozen 64-case
``evaluation/semantic_corpus/cases.json``). Qualification measures a model
against the frozen benchmark. Promotion regression measures a model against
the PRODUCTION AUTHORITY BOUNDARIES using a small production-shaped corpus
(``evaluation/semantic_promotion_regression/cases.json``):

    deterministic matching (real ``assess_listing_identity``)
            |
            v
    semantic eligibility (frozen FU3B states, via the public pure
    research predicate ``is_human_review_eligistic_assessment`` plus the
    frozen usable-evidence title gate)
            |
            v
    semantic model (ONE injected transport attempt per eligible case,
    prompt v1.1 built by the shared contract, strict contract parser)
            |
            v
    semantic decision (MATCH / NO_MATCH / UNCERTAIN or bounded failure)
            |
            v
    execution disposition (MATCH -> AI_ASSISTED_MATCH only;
    NO_MATCH / UNCERTAIN -> UNDECIDED, no authority)

Why the harness cannot use the production ``SemanticRuntime``
-------------------------------------------------------------
The frozen production runtime is mechanically pinned to
``amax/nemotron-3-super`` primary / ``vllm-262k/Qwen3.6-27B-262K`` fallback:
``validate_runtime_config`` rejects any other route, and
``SemanticRuntimeResult`` self-validates ``requested_primary_*`` against the
pinned constants. A challenger such as ``amax/qwen3.8-27b`` therefore cannot
even be named in a production result object. This harness constructs its OWN
explicitly identified transport/model configuration (evaluation-only
authorization, see ``PROMOTION_REGRESSION_AUTHORIZED_MODELS``) and records
its own bounded result objects. The production route is not touched.

Authoritative production objects that the harness REUSES (never copies):

* ``research.matching.assess_listing_identity`` — real deterministic matching.
* ``research.matching.is_human_review_eligible_assessment`` — the public
  pure predicate that mirrors the frozen FU3B semantic-eligible states
  (a test locks this mirror against the execution-layer predicate).
* ``semantic.contract.build_prompt`` / ``parse_raw_output`` /
  ``validate_response`` / ``SEMANTIC_PROMPT_VERSION`` — prompt v1.1 and the
  strict response contract, the same objects production uses.
* ``semantic.transport`` — the neutral transport (same classes and the same
  ``get_openai_transport_for_provider`` the production runtime resolves
  lazily); the frozen transport error vocabulary.
* ``semantic.runtime._TRANSPORT_ERROR_TO_STATUS`` +
  ``SemanticAttemptStatus`` — the frozen status mapping, reused so the
  harness's single-attempt interpretation cannot diverge from the production
  primary attempt (a test locks the equivalence over the full outcome
  matrix).

What this harness is NOT
------------------------
* Not a production runtime. Production must never import this module.
* Not a qualification benchmark. It does not load, score against, or
  modify the frozen 64-case qualification corpus.
* Not a fallback chain. Each model is tested in the PRIMARY seat with
  exactly one transport attempt per eligible case. Production fallback
  semantics (execution failure only, never semantic disagreement) remain
  frozen and are covered by the production runtime's own tests. No retry
  behavior exists: an invalid first response is recorded as invalid.
* Not a winner selector. The comparison surfaces per-case decisions,
  disagreements, and objective gate facts. It never scores models against
  each other and never declares a winner; promotion remains a
  human-reviewed decision.

Import purity
-------------
This module imports only stdlib plus ``product_intelligence.domain``,
``product_intelligence.research`` (pure, Django-free), and
``product_intelligence.semantic`` (pure contract + neutral transport).
It does NOT import ``product_intelligence.execution``, ``runs``, ``web``,
``providers``, or Django, so it stays importable in a clean interpreter —
locked by a test.
"""

from __future__ import annotations

import hashlib
import json
import math
import os
import subprocess
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from product_intelligence.domain import ResearchRequest
from product_intelligence.domain.enums import (
    EvidenceDecision,
    IdentityMatchType,
)
from product_intelligence.research.listings import (
    ExtractionMethod,
    ListingObservation,
)
from product_intelligence.research.matching import (
    EvidenceSource,
    IdentityRejectionReason,
    ListingIdentityAssessment,
    assess_listing_identity,
    is_human_review_eligible_assessment,
)
from product_intelligence.research.normalization import (
    NormalizedAvailability,
    NormalizedCondition,
    NormalizedListingObservation,
)
from product_intelligence.semantic.contract import (
    SEMANTIC_PROMPT_VERSION,
    ConfidenceLevel,
    RawOutputParseError,
    SemanticDecision,
    SemanticMatchResponse,
    build_prompt,
    parse_raw_output,
    validate_response,
)
# The frozen status mapping and attempt vocabulary are REUSED, not forked:
# the harness's single-attempt interpretation must classify outcomes exactly
# the way the production primary attempt does. ``SemanticAttemptStatus`` is a
# public export of ``product_intelligence.semantic``; the mapping table is a
# module-level constant of the frozen runtime (imported read-only).
from product_intelligence.semantic.runtime import (
    _TRANSPORT_ERROR_TO_STATUS,
    SemanticAttemptStatus,
)
from product_intelligence.semantic.transport import (
    RUN_FATAL_ERROR_TYPES,
    SemanticModelTransport,
    TransportFailure,
    TransportResult,
    get_openai_transport_for_provider,
)


# ---------------------------------------------------------------------------
# Bounded harness vocabulary
# ---------------------------------------------------------------------------

PROMOTION_REGRESSION_BENCHMARK_KIND = "semantic_promotion_regression"
PROMOTION_REGRESSION_SCHEMA_VERSION = "1.0"
PROMOTION_REGRESSION_RUNNER_VERSION = "1.0"

# Frozen generation settings, identical to the production qualified route.
# temperature is the exact float 0.0 (mirrors the production pin: only a
# Python float serializes to the qualified JSON body).
PROMOTION_REGRESSION_TEMPERATURE = 0.0
PROMOTION_REGRESSION_MAX_TOKENS = 32768
DEFAULT_REQUEST_TIMEOUT_SECONDS = 300.0

DEFAULT_RUNS_DIRECTORY = Path("semantic_promotion_regression_runs")

# Category codes A..J from the phase specification, with fixed names.
PROMOTION_REGRESSION_CATEGORIES: dict[str, str] = {
    "A": "deterministic_accepted",
    "B": "mpn_conflict",
    "C": "title_text_semantic_eligible",
    "D": "sku_field_semantic_eligible",
    "E": "partial_mpn_semantic_eligible",
    "F": "no_usable_evidence",
    "G": "accessory_compatibility_trap",
    "H": "identity_attribute_conflict",
    "I": "normalized_identity_trailing_description",
    "J": "decision_mapping",
}

# Expected-decision vocabulary for the semantic tier (contract values).
_SEMANTIC_DECISION_VALUES = frozenset(
    {d.value for d in SemanticDecision}
)

# Authority-outcome vocabulary (bounded, model-agnostic).
AUTHORITY_OUTCOME_DETERMINISTIC_ACCEPTED = "DETERMINISTIC_ACCEPTED"
AUTHORITY_OUTCOME_DETERMINISTIC_REJECTED_MPN_CONFLICT = (
    "DETERMINISTIC_REJECTED_MPN_CONFLICT"
)
AUTHORITY_OUTCOME_DETERMINISTIC_REJECTED_NO_SEMANTIC = (
    "DETERMINISTIC_REJECTED_NO_SEMANTIC"
)
AUTHORITY_OUTCOME_AI_ASSISTED_MATCH_ONLY = "AI_ASSISTED_MATCH_ONLY"
AUTHORITY_OUTCOME_NO_SEMANTIC_AUTHORITY = "NO_SEMANTIC_AUTHORITY"

# Run statuses (mirrors the qualification runner vocabulary).
RUN_STATUS_COMPLETED = "COMPLETED"
RUN_STATUS_FAILED_CONFIGURATION = "FAILED_CONFIGURATION"
RUN_STATUS_FAILED_PROVIDER = "FAILED_PROVIDER"

# Run-fatal transport error types that abort the run (frozen transport
# vocabulary, shared with the qualification runner).
_RUN_FATAL_CONFIGURATION = frozenset(
    {
        "AUTHENTICATION_FAILED",
        "MODEL_NOT_FOUND",
        "MODEL_IDENTITY_MISMATCH",
        "UNSUPPORTED_PARAMETER",
        "INVALID_REQUEST_CONFIGURATION",
    }
)
_RUN_FATAL_PROVIDER = frozenset({"RATE_LIMITED", "PROVIDER_UNAVAILABLE"})


class PromotionRegressionError(ValueError):
    """Base error for the promotion-regression harness."""


class PromotionRegressionCorpusError(PromotionRegressionError):
    """Raised when the promotion-regression corpus is invalid."""


class PromotionRegressionCaseError(PromotionRegressionError):
    """Raised when a case's declared state is not realized by the frozen
    deterministic authority chain. A case that does not reproduce its own
    declared production shape is defective and the run fails closed."""


class PromotionRegressionModelAuthorizationError(PromotionRegressionError):
    """Raised when a model is not explicitly authorized for this harness."""


class PromotionRegressionComparisonError(PromotionRegressionError):
    """Raised when two runs cannot be compared (bounded error code)."""


def _make_filesystem_safe(name: str) -> str:
    """Convert provider/model to a filesystem-safe slug (same rule as the
    qualification runner)."""
    import re

    original = name
    unsafe_chars = set('/\\:|"<>?*')
    safe = name
    for char in unsafe_chars:
        safe = safe.replace(char, "_")
    safe = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f]", "_", safe)
    safe = safe.rstrip(". ")
    if safe != original:
        hash_suffix = hashlib.sha256(original.encode("utf-8")).hexdigest()[:8]
        safe = f"{safe}--{hash_suffix}"
    return safe


def _validate_path_safety(target: Path, root: Path) -> bool:
    """Verify target is truly inside root (no escape via ..)."""
    try:
        target_resolved = target.resolve()
        root_resolved = root.resolve()
        return target_resolved.is_relative_to(root_resolved)
    except (ValueError, OSError):
        return False


def _validate_request_timeout(value: Any) -> None:
    """Reject non-finite, non-positive, boolean, or non-numeric timeouts."""
    if isinstance(value, bool):
        raise PromotionRegressionError(
            "request_timeout_seconds must not be boolean, "
            f"got {type(value).__name__}"
        )
    if not isinstance(value, (int, float)):
        raise PromotionRegressionError(
            "request_timeout_seconds must be numeric, "
            f"got {type(value).__name__}"
        )
    if not math.isfinite(value):
        raise PromotionRegressionError(
            f"request_timeout_seconds must be finite, got {value}"
        )
    if value <= 0:
        raise PromotionRegressionError(
            f"request_timeout_seconds must be > 0, got {value}"
        )


# ---------------------------------------------------------------------------
# Evaluation-only model authorization
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class PromotionRegressionModelSpec:
    """Explicitly identified transport/model configuration for ONE harness
    run.

    This is evaluation-only authorization: it names which provider/model the
    harness may test in the PRIMARY seat. It does NOT configure the production
    ``SemanticRuntime`` (which remains pinned and rejects any other route)
    and does NOT add any model to the production fallback chain.
    """

    provider: str
    model: str
    role: str  # "production_primary" | "challenger"

    def __post_init__(self) -> None:
        if not isinstance(self.provider, str) or not self.provider:
            raise ValueError("provider must be a non-empty string")
        if not isinstance(self.model, str) or not self.model:
            raise ValueError("model must be a non-empty string")
        if self.role not in ("production_primary", "challenger"):
            raise ValueError(
                f"role must be 'production_primary' or 'challenger', "
                f"got {self.role!r}"
            )

    @property
    def provider_model_id(self) -> str:
        return f"{self.provider}/{self.model}"


# The ONLY models this harness may run. The production primary is the
# baseline; formally qualified challengers are added here by explicit,
# reviewed decision (never by the production route).
PROMOTION_REGRESSION_AUTHORIZED_MODELS: tuple[PromotionRegressionModelSpec, ...] = (
    PromotionRegressionModelSpec(
        provider="amax", model="nemotron-3-super", role="production_primary"
    ),
    PromotionRegressionModelSpec(
        provider="amax", model="qwen3.8-27b", role="challenger"
    ),
)


def get_authorized_model_spec(provider: str, model: str) -> PromotionRegressionModelSpec:
    """Return the authorized spec for provider/model, or fail closed.

    Unknown models are rejected: the harness has no open-ended model
    configuration surface.
    """
    for spec in PROMOTION_REGRESSION_AUTHORIZED_MODELS:
        if spec.provider == provider and spec.model == model:
            return spec
    raise PromotionRegressionModelAuthorizationError(
        f"Model {provider}/{model} is not authorized for promotion "
        "regression evaluation. Authorized models: "
        + ", ".join(s.provider_model_id for s in PROMOTION_REGRESSION_AUTHORIZED_MODELS)
    )


# ---------------------------------------------------------------------------
# Corpus contract
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class PromotionRegressionExpectedDeterministic:
    """The deterministic state a case must realize under the frozen
    authority chain. Validated against the real production enums."""

    decision: str
    rejection_reason: str | None
    evidence_source: str
    match_type: str


@dataclass(frozen=True)
class PromotionRegressionCase:
    """One production-shaped promotion-regression case."""

    case_id: str
    category: str
    category_name: str
    title: str
    target_mpn: str
    target_description: str
    candidate_product_title: str | None
    candidate_mpn_field: str | None
    candidate_sku: str | None
    candidate_brand: str | None
    candidate_condition: str | None
    expected_deterministic: PromotionRegressionExpectedDeterministic
    expected_semantic_call: bool
    expected_semantic_decision: str | None
    match_is_unsafe: bool
    critical_reason: str
    provenance: str


@dataclass(frozen=True)
class PromotionRegressionCorpus:
    """The promotion-regression corpus (separate from the frozen
    qualification corpus)."""

    corpus_version: int
    cases: tuple[PromotionRegressionCase, ...]

    def __len__(self) -> int:
        return len(self.cases)

    def get_case(self, case_id: str) -> PromotionRegressionCase:
        for case in self.cases:
            if case.case_id == case_id:
                return case
        raise KeyError(f"Case not found: {case_id}")


def _default_corpus_path() -> Path:
    path = (
        Path(__file__).parent
        / ".."
        / ".."
        / ".."
        / "evaluation"
        / "semantic_promotion_regression"
        / "cases.json"
    )
    path = path.resolve()
    if not path.exists():
        path = Path("evaluation") / "semantic_promotion_regression" / "cases.json"
    return path


def _validate_expected_deterministic(
    data: Any, case_id: str
) -> PromotionRegressionExpectedDeterministic:
    if not isinstance(data, dict):
        raise PromotionRegressionCorpusError(
            f"Case {case_id}: expected_deterministic must be an object"
        )
    decision = data.get("decision")
    if decision not in (e.value for e in EvidenceDecision):
        raise PromotionRegressionCorpusError(
            f"Case {case_id}: expected_deterministic.decision must be a valid "
            f"EvidenceDecision value, got {decision!r}"
        )
    rejection_reason = data.get("rejection_reason")
    if rejection_reason is not None:
        if rejection_reason not in (r.value for r in IdentityRejectionReason):
            raise PromotionRegressionCorpusError(
                f"Case {case_id}: expected_deterministic.rejection_reason must "
                f"be a valid IdentityRejectionReason value or null, got "
                f"{rejection_reason!r}"
            )
    evidence_source = data.get("evidence_source")
    if evidence_source not in (s.value for s in EvidenceSource):
        raise PromotionRegressionCorpusError(
            f"Case {case_id}: expected_deterministic.evidence_source must be "
            f"a valid EvidenceSource value, got {evidence_source!r}"
        )
    match_type = data.get("match_type")
    if match_type not in (m.value for m in IdentityMatchType):
        raise PromotionRegressionCorpusError(
            f"Case {case_id}: expected_deterministic.match_type must be a "
            f"valid IdentityMatchType value, got {match_type!r}"
        )
    # Internal consistency of the declared state (mirrors the frozen 3C
    # invariants at the vocabulary level):
    if decision == EvidenceDecision.ACCEPTED.value:
        if rejection_reason is not None:
            raise PromotionRegressionCorpusError(
                f"Case {case_id}: ACCEPTED may not carry a rejection_reason"
            )
        if evidence_source not in (
            EvidenceSource.EXPLICIT_MPN_FIELD.value,
            EvidenceSource.VISIBLE_LABELED_MPN_FIELD.value,
        ):
            raise PromotionRegressionCorpusError(
                f"Case {case_id}: ACCEPTED requires an explicit MPN field "
                f"evidence source, got {evidence_source!r}"
            )
        if match_type not in (
            IdentityMatchType.EXACT.value,
            IdentityMatchType.NORMALIZED_EXACT.value,
        ):
            raise PromotionRegressionCorpusError(
                f"Case {case_id}: ACCEPTED requires EXACT or "
                f"NORMALIZED_EXACT, got {match_type!r}"
            )
    else:
        if rejection_reason is None:
            raise PromotionRegressionCorpusError(
                f"Case {case_id}: a non-ACCEPTED deterministic state must "
                "carry a rejection_reason"
            )
        if match_type is not None and match_type == IdentityMatchType.EXACT.value:
            raise PromotionRegressionCorpusError(
                f"Case {case_id}: a rejected state may not claim EXACT"
            )
    return PromotionRegressionExpectedDeterministic(
        decision=decision,
        rejection_reason=rejection_reason,
        evidence_source=evidence_source,
        match_type=match_type,
    )


def _validate_case(case_data: Any, index: int, seen_ids: set[str]) -> PromotionRegressionCase:
    if not isinstance(case_data, dict):
        raise PromotionRegressionCorpusError(
            f"Case at index {index} must be a JSON object"
        )

    case_id = case_data.get("case_id")
    if not isinstance(case_id, str) or not case_id:
        raise PromotionRegressionCorpusError(
            f"Case at index {index}: case_id must be a non-empty string"
        )
    if not case_id.startswith("SPR-"):
        raise PromotionRegressionCorpusError(
            f"Case {case_id}: promotion-regression case IDs must use the "
            "SPR- prefix (the SMQ- prefix belongs to the frozen "
            "qualification corpus)"
        )
    if case_id in seen_ids:
        raise PromotionRegressionCorpusError(f"Duplicate case_id: {case_id}")
    seen_ids.add(case_id)

    category = case_data.get("category")
    if category not in PROMOTION_REGRESSION_CATEGORIES:
        raise PromotionRegressionCorpusError(
            f"Case {case_id}: category must be one of "
            f"{sorted(PROMOTION_REGRESSION_CATEGORIES)}, got {category!r}"
        )
    category_name = case_data.get("category_name")
    if category_name != PROMOTION_REGRESSION_CATEGORIES[category]:
        raise PromotionRegressionCorpusError(
            f"Case {case_id}: category_name {category_name!r} does not match "
            f"category {category!r} (expected "
            f"{PROMOTION_REGRESSION_CATEGORIES[category]!r})"
        )

    title = case_data.get("title")
    if not isinstance(title, str) or not title.strip():
        raise PromotionRegressionCorpusError(
            f"Case {case_id}: title must be a non-empty string"
        )

    target = case_data.get("target")
    if not isinstance(target, dict):
        raise PromotionRegressionCorpusError(
            f"Case {case_id}: target must be an object"
        )
    target_mpn = target.get("manufacturer_part_number")
    if not isinstance(target_mpn, str) or not target_mpn.strip():
        raise PromotionRegressionCorpusError(
            f"Case {case_id}: target.manufacturer_part_number must be a "
            "non-empty string"
        )
    target_description = target.get("description")
    if not isinstance(target_description, str) or not target_description.strip():
        raise PromotionRegressionCorpusError(
            f"Case {case_id}: target.description must be a non-empty string"
        )

    candidate = case_data.get("candidate")
    if not isinstance(candidate, dict):
        raise PromotionRegressionCorpusError(
            f"Case {case_id}: candidate must be an object"
        )

    def _optional_text(field: str) -> str | None:
        value = candidate.get(field)
        if value is None:
            return None
        if not isinstance(value, str) or not value.strip():
            raise PromotionRegressionCorpusError(
                f"Case {case_id}: candidate.{field} must be a non-empty "
                f"string or null, got {value!r}"
            )
        return value

    expected_deterministic = _validate_expected_deterministic(
        case_data.get("expected_deterministic"), case_id
    )

    expected_semantic_call = case_data.get("expected_semantic_call")
    if not isinstance(expected_semantic_call, bool):
        raise PromotionRegressionCorpusError(
            f"Case {case_id}: expected_semantic_call must be a boolean"
        )

    expected_semantic_decision = case_data.get("expected_semantic_decision")
    if expected_semantic_decision is None:
        if expected_semantic_call:
            raise PromotionRegressionCorpusError(
                f"Case {case_id}: a semantic call is expected, so "
                "expected_semantic_decision must be MATCH, NO_MATCH, or "
                "UNCERTAIN (not null)"
            )
    else:
        if expected_semantic_decision not in _SEMANTIC_DECISION_VALUES:
            raise PromotionRegressionCorpusError(
                f"Case {case_id}: expected_semantic_decision must be MATCH, "
                f"NO_MATCH, UNCERTAIN, or null, got "
                f"{expected_semantic_decision!r}"
            )
        if not expected_semantic_call:
            raise PromotionRegressionCorpusError(
                f"Case {case_id}: expected_semantic_decision is set but no "
                "semantic call is expected; a model decision cannot exist "
                "without a call"
            )

    match_is_unsafe = case_data.get("match_is_unsafe")
    if not isinstance(match_is_unsafe, bool):
        raise PromotionRegressionCorpusError(
            f"Case {case_id}: match_is_unsafe must be a boolean"
        )
    if match_is_unsafe and not expected_semantic_call:
        raise PromotionRegressionCorpusError(
            f"Case {case_id}: match_is_unsafe requires an expected semantic "
            "call; cases where no model may be consulted are protected by "
            "the no-override gate instead"
        )

    critical_reason = case_data.get("critical_reason")
    if not isinstance(critical_reason, str) or not critical_reason.strip():
        raise PromotionRegressionCorpusError(
            f"Case {case_id}: critical_reason must be a non-empty string"
        )

    provenance = case_data.get("provenance")
    if provenance not in ("synthetic", "project_uat"):
        raise PromotionRegressionCorpusError(
            f"Case {case_id}: provenance must be 'synthetic' or "
            f"'project_uat', got {provenance!r}"
        )

    return PromotionRegressionCase(
        case_id=case_id,
        category=category,
        category_name=category_name,
        title=title,
        target_mpn=target_mpn,
        target_description=target_description,
        candidate_product_title=_optional_text("product_title"),
        candidate_mpn_field=_optional_text("manufacturer_part_number_text"),
        candidate_sku=_optional_text("sku_text"),
        candidate_brand=_optional_text("brand_text"),
        candidate_condition=_optional_text("condition_text"),
        expected_deterministic=expected_deterministic,
        expected_semantic_call=expected_semantic_call,
        expected_semantic_decision=expected_semantic_decision,
        match_is_unsafe=match_is_unsafe,
        critical_reason=critical_reason,
        provenance=provenance,
    )


def load_promotion_regression_corpus(
    path: str | Path | None = None,
) -> PromotionRegressionCorpus:
    """Load and strictly validate the promotion-regression corpus.

    Fails closed on any structural defect: unknown categories, duplicate or
    mis-prefixed IDs, inconsistent call/decision declarations, or a corpus
    that does not cover every category A..J and all three expected semantic
    decisions among called cases.

    This corpus is SEPARATE from the frozen 64-case qualification corpus;
    loading it never touches ``evaluation/semantic_corpus/cases.json``.
    """
    if path is None:
        path = _default_corpus_path()
    path = Path(path)
    if not path.exists():
        raise PromotionRegressionCorpusError(
            f"Promotion-regression corpus file not found: {path}"
        )
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except json.JSONDecodeError as e:
        raise PromotionRegressionCorpusError(
            f"Invalid JSON in promotion-regression corpus: {e}"
        )

    if not isinstance(data, dict):
        raise PromotionRegressionCorpusError(
            "Promotion-regression corpus must be a JSON object"
        )
    if data.get("benchmark_kind") != PROMOTION_REGRESSION_BENCHMARK_KIND:
        raise PromotionRegressionCorpusError(
            "benchmark_kind must be "
            f"{PROMOTION_REGRESSION_BENCHMARK_KIND!r}, got "
            f"{data.get('benchmark_kind')!r}"
        )
    corpus_version = data.get("corpus_version")
    if not isinstance(corpus_version, int) or isinstance(corpus_version, bool) or corpus_version < 1:
        raise PromotionRegressionCorpusError(
            f"Invalid corpus_version: {corpus_version!r}"
        )
    cases_data = data.get("cases")
    if not isinstance(cases_data, list) or not cases_data:
        raise PromotionRegressionCorpusError(
            "cases must be a non-empty JSON array"
        )

    seen_ids: set[str] = set()
    cases: list[PromotionRegressionCase] = []
    for idx, case_data in enumerate(cases_data):
        case = _validate_case(case_data, idx, seen_ids)
        cases.append(case)

    # Corpus-wide coverage guards: the phase requires every category A..J
    # and all three expected semantic decisions among called cases.
    categories_present = {c.category for c in cases}
    missing_categories = set(PROMOTION_REGRESSION_CATEGORIES) - categories_present
    if missing_categories:
        raise PromotionRegressionCorpusError(
            "corpus does not cover every required category; missing: "
            + ", ".join(sorted(missing_categories))
        )
    decisions_present = {
        c.expected_semantic_decision
        for c in cases
        if c.expected_semantic_call
    }
    if decisions_present != _SEMANTIC_DECISION_VALUES:
        raise PromotionRegressionCorpusError(
            "corpus must contain called cases expecting each of MATCH, "
            f"NO_MATCH, and UNCERTAIN; got {sorted(d for d in decisions_present if d)}"
        )

    return PromotionRegressionCorpus(
        corpus_version=corpus_version, cases=tuple(cases)
    )


# ---------------------------------------------------------------------------
# Production-shaped case realization
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class PromotionRegressionCaseInputs:
    """The real production input objects one case realizes."""

    request: ResearchRequest
    observation: ListingObservation
    normalized: NormalizedListingObservation


def build_case_inputs(case: PromotionRegressionCase) -> PromotionRegressionCaseInputs:
    """Build the real ``ResearchRequest`` / ``ListingObservation`` /
    ``NormalizedListingObservation`` for one case.

    The observation fields are exactly the fields the frozen integration
    would read; the source URL is synthetic data that is never fetched.
    """
    request = ResearchRequest(case.target_mpn, case.target_description)
    observation = ListingObservation(
        source_url=f"https://example.com/promotion-regression/{case.case_id}",
        extraction_method=ExtractionMethod.JSON_LD,
        product_title=case.candidate_product_title,
        manufacturer_part_number_text=case.candidate_mpn_field,
        sku_text=case.candidate_sku,
        brand_text=case.candidate_brand,
        condition_text=case.candidate_condition,
    )
    normalized = NormalizedListingObservation(
        observation=observation,
        price_amount=None,
        currency_code=None,
        availability=NormalizedAvailability.UNKNOWN,
        condition=NormalizedCondition.UNKNOWN,
        seller_name=None,
        normalization_issues=(),
    )
    return PromotionRegressionCaseInputs(
        request=request, observation=observation, normalized=normalized
    )


def assess_case(case: PromotionRegressionCase) -> ListingIdentityAssessment:
    """Run the REAL deterministic matcher for one case and verify the
    case's declared deterministic state.

    If the frozen authority chain does not realize the declared state, the
    case is defective and the run fails closed — a promotion-regression case
    whose production shape is wrong measures nothing.
    """
    inputs = build_case_inputs(case)
    assessment = assess_listing_identity(inputs.request, inputs.normalized)
    expected = case.expected_deterministic
    observed = (
        assessment.decision.value,
        assessment.rejection_reason.value
        if assessment.rejection_reason is not None
        else None,
        assessment.candidate_evidence_source.value,
        assessment.match_type.value,
    )
    declared = (
        expected.decision,
        expected.rejection_reason,
        expected.evidence_source,
        expected.match_type,
    )
    if observed != declared:
        raise PromotionRegressionCaseError(
            f"Case {case.case_id}: the frozen deterministic authority chain "
            f"realized {observed}, but the case declares {declared}. The "
            "case definition is defective; the run fails closed."
        )
    return assessment


def semantic_call_is_expected(assessment: ListingIdentityAssessment) -> bool:
    """The harness's eligibility decision, built ONLY from frozen
    production objects:

    * ``is_human_review_eligible_assessment`` — the public pure research
      predicate that mirrors the frozen FU3B semantic-eligible states
      (a test locks this mirror against the execution-layer
      ``_is_semantic_eligible``);
    * the frozen usable-evidence gate: the candidate must publish a product
      title (the execution integration's ``_has_usable_evidence``).
    """
    if not is_human_review_eligible_assessment(assessment):
        return False
    observation = assessment.normalized_listing.observation
    if not observation.product_title:
        return False
    return True


def _build_case_specs(observation: ListingObservation) -> str | None:
    """Mirror of the frozen integration's candidate-specs builder
    (Brand / MPN / SKU / Condition, ' | '-joined, None when empty).
    A test locks this against the execution-layer original."""
    parts: list[str] = []
    if observation.brand_text:
        parts.append(f"Brand: {observation.brand_text}")
    if observation.manufacturer_part_number_text:
        parts.append(f"MPN: {observation.manufacturer_part_number_text}")
    if observation.sku_text:
        parts.append(f"SKU: {observation.sku_text}")
    if observation.condition_text:
        parts.append(f"Condition: {observation.condition_text}")
    if not parts:
        return None
    return " | ".join(parts)


def _build_case_prompt(
    case: PromotionRegressionCase,
    assessment: ListingIdentityAssessment,
) -> Any:
    """Build the prompt v1.1 for one called case through the shared
    contract, with fields derived exactly like the frozen integration."""
    request = build_case_inputs(case).request
    observation = assessment.normalized_listing.observation
    return build_prompt(
        case_id=case.case_id,
        target_mpn=assessment.requested_part_number,
        target_description=request.description,
        candidate_title=observation.product_title or "",
        candidate_mpn_field=(
            observation.manufacturer_part_number_text
            if observation.manufacturer_part_number_text
            else None
        ),
        candidate_sku=observation.sku_text if observation.sku_text else None,
        candidate_specs=_build_case_specs(observation),
        evidence_source=assessment.candidate_evidence_source.value,
    )


# ---------------------------------------------------------------------------
# Single-attempt interpretation (mirrors the production primary attempt)
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class PromotionRegressionInterpretation:
    """Bounded outcome of one transport attempt for one case.

    The classification order and vocabulary are exactly the production
    primary attempt's: transport failure -> frozen status mapping; then
    exact provider-reported model identity; then non-empty raw output; then
    the strict contract parser; then the strict schema validator. There is no
    retry, no second model, and no reinterpretation: an invalid first
    response is recorded as invalid.
    """

    status: SemanticAttemptStatus
    response: SemanticMatchResponse | None
    raw_output: str | None
    provider_reported_model: str | None
    model_identity_proven: bool | None
    latency_ms: float | None
    transport_error_type: str | None


def interpret_transport_outcome(
    outcome: TransportResult | TransportFailure,
    requested_model: str,
) -> PromotionRegressionInterpretation:
    if isinstance(outcome, TransportFailure):
        status = _TRANSPORT_ERROR_TO_STATUS.get(
            outcome.error_type, SemanticAttemptStatus.UNKNOWN_ERROR
        )
        return PromotionRegressionInterpretation(
            status=status,
            response=None,
            raw_output=None,
            provider_reported_model=None,
            model_identity_proven=None,
            latency_ms=None,
            transport_error_type=outcome.error_type,
        )

    reported = outcome.provider_reported_model
    if reported is None or reported != requested_model:
        # Exact provider-reported model identity is mandatory (production
        # invariant): a provider that reports a different model, or no model,
        # has not proven it ran the requested model.
        return PromotionRegressionInterpretation(
            status=SemanticAttemptStatus.MODEL_IDENTITY_MISMATCH,
            response=None,
            raw_output=outcome.raw_output if isinstance(outcome.raw_output, str) else None,
            provider_reported_model=reported,
            model_identity_proven=False,
            latency_ms=outcome.latency_ms,
            transport_error_type=None,
        )

    raw_output = outcome.raw_output
    if not isinstance(raw_output, str) or not raw_output.strip():
        return PromotionRegressionInterpretation(
            status=SemanticAttemptStatus.EMPTY_RESPONSE,
            response=None,
            raw_output=raw_output if isinstance(raw_output, str) else None,
            provider_reported_model=reported,
            model_identity_proven=True,
            latency_ms=outcome.latency_ms,
            transport_error_type=None,
        )

    try:
        parsed = parse_raw_output(raw_output)
    except RawOutputParseError:
        return PromotionRegressionInterpretation(
            status=SemanticAttemptStatus.MALFORMED_JSON,
            response=None,
            raw_output=raw_output,
            provider_reported_model=reported,
            model_identity_proven=True,
            latency_ms=outcome.latency_ms,
            transport_error_type=None,
        )

    try:
        validated = validate_response(parsed)
    except (TypeError, ValueError):
        return PromotionRegressionInterpretation(
            status=SemanticAttemptStatus.SCHEMA_INVALID,
            response=None,
            raw_output=raw_output,
            provider_reported_model=reported,
            model_identity_proven=True,
            latency_ms=outcome.latency_ms,
            transport_error_type=None,
        )

    return PromotionRegressionInterpretation(
        status=SemanticAttemptStatus.OK,
        response=validated,
        raw_output=raw_output,
        provider_reported_model=reported,
        model_identity_proven=True,
        latency_ms=outcome.latency_ms,
        transport_error_type=None,
    )


# ---------------------------------------------------------------------------
# Disposition and authority outcomes
# ---------------------------------------------------------------------------


def map_semantic_disposition(
    decision: SemanticDecision | None,
) -> EvidenceDecision | None:
    """Map a semantic decision to its execution disposition, exactly the
    frozen production mapping:

    * MATCH -> AI_ASSISTED_MATCH (AI-assisted evidence only; NEVER
      deterministic ACCEPTED, and never a mutation of the original
      assessment);
    * NO_MATCH / UNCERTAIN -> UNDECIDED (no authority created);
    * no decision (invalid output) -> None (no disposition at all).
    """
    if decision is None:
        return None
    if decision is SemanticDecision.MATCH:
        return EvidenceDecision.AI_ASSISTED_MATCH
    return EvidenceDecision.UNDECIDED


def expected_authority_outcome(case: PromotionRegressionCase) -> str:
    """The model-agnostic authority outcome the case declares."""
    if not case.expected_semantic_call:
        if case.expected_deterministic.decision == EvidenceDecision.ACCEPTED.value:
            return AUTHORITY_OUTCOME_DETERMINISTIC_ACCEPTED
        if (
            case.expected_deterministic.rejection_reason
            == IdentityRejectionReason.MPN_MISMATCH.value
        ):
            return AUTHORITY_OUTCOME_DETERMINISTIC_REJECTED_MPN_CONFLICT
        return AUTHORITY_OUTCOME_DETERMINISTIC_REJECTED_NO_SEMANTIC
    if case.expected_semantic_decision == SemanticDecision.MATCH.value:
        return AUTHORITY_OUTCOME_AI_ASSISTED_MATCH_ONLY
    return AUTHORITY_OUTCOME_NO_SEMANTIC_AUTHORITY


def observed_authority_outcome(
    assessment: ListingIdentityAssessment,
    interpretation: PromotionRegressionInterpretation | None,
) -> str:
    """The authority outcome actually observed for one case.

    When no semantic call was made, the deterministic state is the entire
    authority story. When a call was made, the disposition mapping is the
    only authority that may exist on top of the (unchanged) deterministic
    state.
    """
    if interpretation is None:
        if assessment.decision is EvidenceDecision.ACCEPTED:
            return AUTHORITY_OUTCOME_DETERMINISTIC_ACCEPTED
        if assessment.rejection_reason is IdentityRejectionReason.MPN_MISMATCH:
            return AUTHORITY_OUTCOME_DETERMINISTIC_REJECTED_MPN_CONFLICT
        return AUTHORITY_OUTCOME_DETERMINISTIC_REJECTED_NO_SEMANTIC
    decision = (
        interpretation.response.decision
        if interpretation.response is not None
        else None
    )
    disposition = map_semantic_disposition(decision)
    if disposition is EvidenceDecision.AI_ASSISTED_MATCH:
        return AUTHORITY_OUTCOME_AI_ASSISTED_MATCH_ONLY
    return AUTHORITY_OUTCOME_NO_SEMANTIC_AUTHORITY


# ---------------------------------------------------------------------------
# Case records and run results
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class PromotionRegressionCaseRecord:
    """Everything one model did (and did not do) on one case.

    Bounded provenance only: no raw exception text, no API key, no
    chain-of-thought. The raw model output IS preserved (evaluation
    artifact, exactly as received), mirroring the qualification runner.
    """

    case_id: str
    category: str
    category_name: str
    case_title: str
    critical_reason: str
    provenance: str
    target_mpn: str
    target_description: str
    candidate_title: str | None
    candidate_mpn_field: str | None
    candidate_sku: str | None
    candidate_brand: str | None
    # Real deterministic state (frozen authority chain).
    deterministic_decision: str
    deterministic_rejection_reason: str | None
    deterministic_evidence_source: str
    deterministic_match_type: str
    # Semantic tier.
    expected_semantic_call: bool
    semantic_call_made: bool
    call_conformance: bool
    transport_status: str | None
    transport_error_type: str | None
    provider_reported_model: str | None
    model_identity_proven: bool | None
    valid_response: bool
    decision: str | None
    confidence: str | None
    reason_code: str | None
    matched_attributes: tuple[str, ...]
    conflicting_attributes: tuple[str, ...]
    missing_critical_attributes: tuple[str, ...]
    raw_output: str | None
    latency_ms: float | None
    disposition: str | None
    # Authority outcomes.
    expected_authority_outcome: str
    observed_authority_outcome: str
    authority_outcome_match: bool
    # Model-quality facts (corpus expectation vs observed decision).
    expected_semantic_decision: str | None
    decision_matches_expected: bool | None
    match_is_unsafe: bool
    unsafe_match: bool
    false_match: bool

    def to_dict(self) -> dict[str, Any]:
        return {
            "case_id": self.case_id,
            "category": self.category,
            "category_name": self.category_name,
            "case_title": self.case_title,
            "critical_reason": self.critical_reason,
            "provenance": self.provenance,
            "target_mpn": self.target_mpn,
            "target_description": self.target_description,
            "candidate_title": self.candidate_title,
            "candidate_mpn_field": self.candidate_mpn_field,
            "candidate_sku": self.candidate_sku,
            "candidate_brand": self.candidate_brand,
            "deterministic": {
                "decision": self.deterministic_decision,
                "rejection_reason": self.deterministic_rejection_reason,
                "evidence_source": self.deterministic_evidence_source,
                "match_type": self.deterministic_match_type,
            },
            "expected_semantic_call": self.expected_semantic_call,
            "semantic_call_made": self.semantic_call_made,
            "call_conformance": self.call_conformance,
            "transport": {
                "status": self.transport_status,
                "error_type": self.transport_error_type,
                "provider_reported_model": self.provider_reported_model,
                "model_identity_proven": self.model_identity_proven,
                "latency_ms": self.latency_ms,
            },
            "response": {
                "valid": self.valid_response,
                "decision": self.decision,
                "confidence": self.confidence,
                "reason_code": self.reason_code,
                "matched_attributes": list(self.matched_attributes),
                "conflicting_attributes": list(self.conflicting_attributes),
                "missing_critical_attributes": list(
                    self.missing_critical_attributes
                ),
            },
            "raw_output": self.raw_output,
            "disposition": self.disposition,
            "expected_authority_outcome": self.expected_authority_outcome,
            "observed_authority_outcome": self.observed_authority_outcome,
            "authority_outcome_match": self.authority_outcome_match,
            "expected_semantic_decision": self.expected_semantic_decision,
            "decision_matches_expected": self.decision_matches_expected,
            "match_is_unsafe": self.match_is_unsafe,
            "unsafe_match": self.unsafe_match,
            "false_match": self.false_match,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "PromotionRegressionCaseRecord":
        deterministic = data["deterministic"]
        transport = data["transport"]
        response = data["response"]
        return cls(
            case_id=data["case_id"],
            category=data["category"],
            category_name=data["category_name"],
            case_title=data["case_title"],
            critical_reason=data["critical_reason"],
            provenance=data["provenance"],
            target_mpn=data["target_mpn"],
            target_description=data["target_description"],
            candidate_title=data["candidate_title"],
            candidate_mpn_field=data["candidate_mpn_field"],
            candidate_sku=data["candidate_sku"],
            candidate_brand=data["candidate_brand"],
            deterministic_decision=deterministic["decision"],
            deterministic_rejection_reason=deterministic["rejection_reason"],
            deterministic_evidence_source=deterministic["evidence_source"],
            deterministic_match_type=deterministic["match_type"],
            expected_semantic_call=data["expected_semantic_call"],
            semantic_call_made=data["semantic_call_made"],
            call_conformance=data["call_conformance"],
            transport_status=transport["status"],
            transport_error_type=transport["error_type"],
            provider_reported_model=transport["provider_reported_model"],
            model_identity_proven=transport["model_identity_proven"],
            valid_response=response["valid"],
            decision=response["decision"],
            confidence=response["confidence"],
            reason_code=response["reason_code"],
            matched_attributes=tuple(response["matched_attributes"]),
            conflicting_attributes=tuple(response["conflicting_attributes"]),
            missing_critical_attributes=tuple(response["missing_critical_attributes"]),
            raw_output=data["raw_output"],
            latency_ms=transport["latency_ms"],
            disposition=data["disposition"],
            expected_authority_outcome=data["expected_authority_outcome"],
            observed_authority_outcome=data["observed_authority_outcome"],
            authority_outcome_match=data["authority_outcome_match"],
            expected_semantic_decision=data["expected_semantic_decision"],
            decision_matches_expected=data["decision_matches_expected"],
            match_is_unsafe=data["match_is_unsafe"],
            unsafe_match=data["unsafe_match"],
            false_match=data["false_match"],
        )


@dataclass(frozen=True)
class PromotionRegressionGate:
    """One objective promotion-gate fact (no weighting, no winner)."""

    name: str
    passed: bool
    detail: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {"name": self.name, "passed": self.passed, "detail": self.detail}


@dataclass(frozen=True)
class PromotionRegressionRunResult:
    """Complete result of one promotion-regression run (one model)."""

    spec: PromotionRegressionModelSpec
    corpus: PromotionRegressionCorpus
    records: tuple[PromotionRegressionCaseRecord, ...]
    manifest: dict[str, Any]
    gates: tuple[PromotionRegressionGate, ...]
    run_timestamp: datetime

    @property
    def run_status(self) -> str:
        return self.manifest["run_status"]

    @property
    def promotion_gate_passed(self) -> bool:
        return all(g.passed for g in self.gates)


# ---------------------------------------------------------------------------
# Corpus / prompt provenance hashes (same canonical form as qualification)
# ---------------------------------------------------------------------------


def _compute_corpus_sha256(corpus_path: Path | None = None) -> str:
    """SHA256 of the canonical JSON content of the corpus source file.

    Same canonical form as the qualification runner (sort_keys,
    ensure_ascii=False) so the two facilities cannot drift in how they
    fingerprint a corpus.
    """
    if corpus_path is None:
        corpus_path = _default_corpus_path()
    corpus_path = Path(corpus_path)
    if not corpus_path.exists():
        raise PromotionRegressionCorpusError(
            f"Corpus source file not found: {corpus_path}"
        )
    with open(corpus_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    canonical = json.dumps(data, sort_keys=True, ensure_ascii=False)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def _compute_prompt_sha256(
    prompt_entries: list[dict[str, str]],
) -> str:
    """SHA256 over the exact prompts used, in called-case order."""
    canonical = json.dumps(prompt_entries, sort_keys=True, ensure_ascii=False)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def _get_git_head() -> str | None:
    try:
        result = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        if result.returncode == 0:
            return result.stdout.strip()
    except Exception:
        pass
    return None


# ---------------------------------------------------------------------------
# Runner
# ---------------------------------------------------------------------------


def _run_fatal_status_for(
    interpretation: PromotionRegressionInterpretation,
) -> str | None:
    """Map an interpretation to a run-fatal status, if one."""
    if interpretation.status is SemanticAttemptStatus.MODEL_IDENTITY_MISMATCH:
        return RUN_STATUS_FAILED_CONFIGURATION
    if (
        interpretation.transport_error_type is not None
        and interpretation.transport_error_type in _RUN_FATAL_CONFIGURATION
    ):
        return RUN_STATUS_FAILED_CONFIGURATION
    if (
        interpretation.transport_error_type is not None
        and interpretation.transport_error_type in _RUN_FATAL_PROVIDER
    ):
        return RUN_STATUS_FAILED_PROVIDER
    return None


def _make_case_record(
    case: PromotionRegressionCase,
    assessment: ListingIdentityAssessment,
    interpretation: PromotionRegressionInterpretation | None,
) -> PromotionRegressionCaseRecord:
    call_made = interpretation is not None
    conforming = call_made == case.expected_semantic_call

    decision_value: str | None = None
    confidence_value: str | None = None
    reason_code: str | None = None
    matched: tuple[str, ...] = ()
    conflicting: tuple[str, ...] = ()
    missing: tuple[str, ...] = ()
    valid = False
    if call_made and interpretation.response is not None:
        valid = interpretation.status is SemanticAttemptStatus.OK
        decision_value = interpretation.response.decision.value
        confidence_value = interpretation.response.confidence.value
        reason_code = interpretation.response.reason_code
        matched = interpretation.response.matched_attributes
        conflicting = interpretation.response.conflicting_attributes
        missing = interpretation.response.missing_critical_attributes

    disposition = map_semantic_disposition(interpretation.response.decision) if (
        call_made and valid
    ) else None

    observed_authority = observed_authority_outcome(assessment, interpretation)
    expected_authority = expected_authority_outcome(case)

    decision_matches_expected: bool | None = None
    if call_made and valid and case.expected_semantic_decision is not None:
        decision_matches_expected = (
            decision_value == case.expected_semantic_decision
        )

    unsafe_match = bool(valid and decision_value == SemanticDecision.MATCH.value and case.match_is_unsafe)
    false_match = bool(
        valid
        and decision_value == SemanticDecision.MATCH.value
        and case.expected_semantic_decision is not None
        and case.expected_semantic_decision != SemanticDecision.MATCH.value
    )

    return PromotionRegressionCaseRecord(
        case_id=case.case_id,
        category=case.category,
        category_name=case.category_name,
        case_title=case.title,
        critical_reason=case.critical_reason,
        provenance=case.provenance,
        target_mpn=case.target_mpn,
        target_description=case.target_description,
        candidate_title=case.candidate_product_title,
        candidate_mpn_field=case.candidate_mpn_field,
        candidate_sku=case.candidate_sku,
        candidate_brand=case.candidate_brand,
        deterministic_decision=assessment.decision.value,
        deterministic_rejection_reason=(
            assessment.rejection_reason.value
            if assessment.rejection_reason is not None
            else None
        ),
        deterministic_evidence_source=assessment.candidate_evidence_source.value,
        deterministic_match_type=assessment.match_type.value,
        expected_semantic_call=case.expected_semantic_call,
        semantic_call_made=call_made,
        call_conformance=conforming,
        transport_status=interpretation.status.value if call_made else None,
        transport_error_type=interpretation.transport_error_type if call_made else None,
        provider_reported_model=interpretation.provider_reported_model if call_made else None,
        model_identity_proven=interpretation.model_identity_proven if call_made else None,
        valid_response=valid,
        decision=decision_value,
        confidence=confidence_value,
        reason_code=reason_code,
        matched_attributes=matched,
        conflicting_attributes=conflicting,
        missing_critical_attributes=missing,
        raw_output=interpretation.raw_output if call_made else None,
        latency_ms=interpretation.latency_ms if call_made else None,
        disposition=disposition.value if disposition is not None else None,
        expected_authority_outcome=expected_authority,
        observed_authority_outcome=observed_authority,
        authority_outcome_match=observed_authority == expected_authority,
        expected_semantic_decision=case.expected_semantic_decision,
        decision_matches_expected=decision_matches_expected,
        match_is_unsafe=case.match_is_unsafe,
        unsafe_match=unsafe_match,
        false_match=false_match,
    )


def run_promotion_regression(
    spec: PromotionRegressionModelSpec,
    transport: SemanticModelTransport,
    *,
    corpus: PromotionRegressionCorpus | None = None,
    request_timeout_seconds: float = DEFAULT_REQUEST_TIMEOUT_SECONDS,
) -> PromotionRegressionRunResult:
    """Run one promotion-regression evaluation for one authorized model.

    For every corpus case, in corpus order:

    1. realize the case as real production inputs;
    2. run the REAL deterministic matcher and verify the case's declared
       deterministic state (fail closed on a defective case);
    3. apply the frozen eligibility rules; a case where no semantic call is
       expected never touches the transport;
    4. for eligible cases, make EXACTLY ONE transport attempt with prompt
       v1.1 (temperature 0.0 float, max_tokens 32768) and interpret the
       outcome with the frozen production classification;
    5. map the decision to its production disposition and record bounded
       provenance.

    A run-fatal transport error (frozen vocabulary) aborts the run after
    recording the failed case, mirroring the qualification runner; there is
    no retry and no second model — this harness tests the PRIMARY seat.
    """
    _validate_request_timeout(request_timeout_seconds)
    if spec not in PROMOTION_REGRESSION_AUTHORIZED_MODELS:
        raise PromotionRegressionModelAuthorizationError(
            f"Model {spec.provider_model_id} is not authorized for "
            "promotion-regression evaluation"
        )
    if corpus is None:
        corpus = load_promotion_regression_corpus()

    start_time = datetime.now(timezone.utc)
    records: list[PromotionRegressionCaseRecord] = []
    prompt_entries: list[dict[str, str]] = []
    run_status = RUN_STATUS_COMPLETED
    aborted = False

    for case in corpus.cases:
        assessment = assess_case(case)
        eligible = semantic_call_is_expected(assessment)
        if eligible != case.expected_semantic_call:
            raise PromotionRegressionCaseError(
                f"Case {case.case_id}: the frozen eligibility rules say "
                f"semantic call {'expected' if eligible else 'not expected'}, "
                f"but the case declares "
                f"{'expected' if case.expected_semantic_call else 'not expected'}. "
                "The case definition is defective; the run fails closed."
            )

        interpretation: PromotionRegressionInterpretation | None = None
        if eligible:
            prompt = _build_case_prompt(case, assessment)
            prompt_entries.append(
                {
                    "case_id": case.case_id,
                    "system_prompt": prompt.system_prompt,
                    "user_prompt": prompt.user_prompt,
                }
            )
            outcome = transport.complete(
                system_prompt=prompt.system_prompt,
                user_prompt=prompt.user_prompt,
                model=spec.model,
                temperature=PROMOTION_REGRESSION_TEMPERATURE,
                max_tokens=PROMOTION_REGRESSION_MAX_TOKENS,
            )
            interpretation = interpret_transport_outcome(outcome, spec.model)

        records.append(_make_case_record(case, assessment, interpretation))

        fatal_status = (
            _run_fatal_status_for(interpretation) if interpretation else None
        )
        if fatal_status is not None:
            run_status = fatal_status
            aborted = True
            break

    finish_time = datetime.now(timezone.utc)

    processed_case_ids = tuple(r.case_id for r in records)
    called_case_ids = tuple(r.case_id for r in records if r.semantic_call_made)

    manifest = {
        "benchmark_kind": PROMOTION_REGRESSION_BENCHMARK_KIND,
        "schema_version": PROMOTION_REGRESSION_SCHEMA_VERSION,
        "runner_version": PROMOTION_REGRESSION_RUNNER_VERSION,
        "corpus_version": corpus.corpus_version,
        "corpus_sha256": _compute_corpus_sha256(),
        "prompt_version": SEMANTIC_PROMPT_VERSION,
        "prompt_sha256": _compute_prompt_sha256(prompt_entries),
        "provider": spec.provider,
        "model": spec.model,
        "role": spec.role,
        "requested_provider": spec.provider,
        "requested_model": spec.model,
        "generation_parameters": {
            "temperature": PROMOTION_REGRESSION_TEMPERATURE,
            "max_tokens": PROMOTION_REGRESSION_MAX_TOKENS,
        },
        "transport_parameters": {
            "request_timeout_seconds": request_timeout_seconds,
        },
        "transport_type": type(transport).__name__,
        "case_ids": [c.case_id for c in corpus.cases],
        "case_count": len(corpus.cases),
        "called_case_ids": list(called_case_ids),
        "called_case_count": len(called_case_ids),
        "processed_case_ids": list(processed_case_ids),
        "processed_case_count": len(processed_case_ids),
        "start_timestamp": start_time.isoformat(),
        "finish_timestamp": finish_time.isoformat(),
        "git_head": _get_git_head(),
        "run_status": run_status,
        "no_winner_declared": True,
    }

    # Gates are computed over the records + manifest; the gate summary is
    # then sealed into the manifest itself so a saved run carries both the
    # facts and the verdict, and load_run can re-verify them.
    provisional = PromotionRegressionRunResult(
        spec=spec,
        corpus=corpus,
        records=tuple(records),
        manifest=dict(manifest),
        gates=(),
        run_timestamp=start_time,
    )
    gates = compute_promotion_gates(provisional)
    manifest["gates"] = {g.name: g.passed for g in gates}
    manifest["promotion_gate_passed"] = all(g.passed for g in gates)
    return PromotionRegressionRunResult(
        spec=spec,
        corpus=corpus,
        records=tuple(records),
        manifest=manifest,
        gates=gates,
        run_timestamp=start_time,
    )


# ---------------------------------------------------------------------------
# Promotion gates (objective facts; no weighting, no winner)
# ---------------------------------------------------------------------------


def compute_promotion_gates(
    run: PromotionRegressionRunResult,
) -> tuple[PromotionRegressionGate, ...]:
    """Compute the objective promotion-gate facts for one run.

    These are the A1 gate definitions. The harness does NOT pick a winner
    and does NOT score models against each other; it reports whether the
    production authority invariants held for THIS model in the PRIMARY seat.

    Gates:
    * deterministic_states_verified — every processed case realized its
      declared deterministic state (enforced by the run; recorded here).
    * no_semantic_override_of_deterministic_authority — the transport was
      called exactly on the frozen-eligible cases: no call where none is
      expected (deterministic ACCEPTED / MPN conflict / no usable evidence)
      and no missed call where one is expected.
    * all_semantic_calls_valid — every called case produced a strict-valid
      response with proven model identity (no malformed JSON, no schema
      violation, no empty response, no identity mismatch, no transport
      failure).
    * no_unsafe_match — no MATCH on a case where a MATCH is an unsafe
      positive-authority expansion (accessory/compatibility traps, hard
      identity-attribute conflicts).
    * ai_assisted_authority_boundary — every MATCH carried exactly the
      AI_ASSISTED_MATCH disposition (never deterministic ACCEPTED); every
      NO_MATCH/UNCERTAIN carried no authority; the deterministic decision
      was unchanged for every case.
    * provenance_integrity — the run completed, the manifest fingerprints
      match the corpus and prompt v1.1, the frozen generation settings were
      used, and every accepted response proved exact model identity.
    """
    records = run.records
    manifest = run.manifest
    gates: list[PromotionRegressionGate] = []

    # 1. deterministic states verified (true by construction; a mismatch
    #    aborts the run with PromotionRegressionCaseError).
    gates.append(
        PromotionRegressionGate(
            name="deterministic_states_verified",
            passed=True,
            detail=(
                f"{len(records)} processed case(s) realized their declared "
                "deterministic state under the frozen authority chain"
            ),
        )
    )

    # 2. no semantic override of deterministic authority.
    offenders = [
        r.case_id
        for r in records
        if not r.call_conformance
    ]
    gates.append(
        PromotionRegressionGate(
            name="no_semantic_override_of_deterministic_authority",
            passed=not offenders,
            detail=(
                None
                if not offenders
                else "semantic call made or missed on: " + ", ".join(offenders)
            ),
        )
    )

    # 3. every called case produced a strict-valid, identity-proven response.
    invalid = [
        (r.case_id, r.transport_status)
        for r in records
        if r.semantic_call_made and (
            not r.valid_response or r.model_identity_proven is not True
        )
    ]
    not_processed = (
        [c.case_id for c in run.corpus.cases]
        if manifest.get("run_status") != RUN_STATUS_COMPLETED
        else []
    )
    processed_ids = {r.case_id for r in records}
    missing = [c for c in not_processed if c not in processed_ids]
    gates.append(
        PromotionRegressionGate(
            name="all_semantic_calls_valid",
            passed=not invalid and not missing,
            detail=(
                None
                if not invalid and not missing
                else (
                    ("invalid/non-proven responses: "
                     + ", ".join(f"{cid}({status})" for cid, status in invalid)
                     + "; ") if invalid else ""
                )
                + (
                    f"run did not process every case (status "
                    f"{manifest.get('run_status')}); unprocessed: "
                    + ", ".join(missing)
                    if missing
                    else ""
                )
            )
            or None,
        )
    )

    # 4. no unsafe MATCH.
    unsafe = [r.case_id for r in records if r.unsafe_match]
    gates.append(
        PromotionRegressionGate(
            name="no_unsafe_match",
            passed=not unsafe,
            detail=(
                None
                if not unsafe
                else "MATCH on unsafe case(s): " + ", ".join(unsafe)
            ),
        )
    )

    # 5. AI-assisted authority boundary.
    violations: list[str] = []
    for r in records:
        if r.semantic_call_made and r.valid_response:
            if r.decision == SemanticDecision.MATCH.value:
                if r.disposition != EvidenceDecision.AI_ASSISTED_MATCH.value:
                    violations.append(
                        f"{r.case_id}: MATCH without AI_ASSISTED_MATCH "
                        f"disposition (got {r.disposition!r})"
                    )
            else:
                if r.disposition not in (
                    None,
                    EvidenceDecision.UNDECIDED.value,
                ):
                    violations.append(
                        f"{r.case_id}: {r.decision} produced authority "
                        f"disposition {r.disposition!r}"
                    )
        # The deterministic decision is the frozen pre-semantic state: a
        # semantic result may never rewrite it.
        expected = next(
            c for c in run.corpus.cases if c.case_id == r.case_id
        ).expected_deterministic
        if (
            r.deterministic_decision != expected.decision
            or r.deterministic_rejection_reason != expected.rejection_reason
            or r.deterministic_evidence_source != expected.evidence_source
            or r.deterministic_match_type != expected.match_type
        ):
            violations.append(
                f"{r.case_id}: deterministic state changed after the run"
            )
    gates.append(
        PromotionRegressionGate(
            name="ai_assisted_authority_boundary",
            passed=not violations,
            detail=None if not violations else "; ".join(violations),
        )
    )

    # 6. provenance integrity.
    problems: list[str] = []
    if manifest.get("prompt_version") != SEMANTIC_PROMPT_VERSION:
        problems.append(
            f"prompt_version {manifest.get('prompt_version')!r} is not the "
            f"frozen {SEMANTIC_PROMPT_VERSION!r}"
        )
    generation = manifest.get("generation_parameters", {})
    if type(generation.get("temperature")) is not float or generation.get(
        "temperature"
    ) != PROMOTION_REGRESSION_TEMPERATURE:
        problems.append(
            "generation temperature deviates from the frozen 0.0 float"
        )
    if (
        isinstance(generation.get("max_tokens"), bool)
        or not isinstance(generation.get("max_tokens"), int)
        or generation.get("max_tokens") != PROMOTION_REGRESSION_MAX_TOKENS
    ):
        problems.append(
            "generation max_tokens deviates from the frozen 32768"
        )
    if manifest.get("run_status") != RUN_STATUS_COMPLETED:
        problems.append(
            f"run_status {manifest.get('run_status')!r}; only a completed "
            "run has full provenance"
        )
    try:
        recomputed_corpus_sha = _compute_corpus_sha256()
        if manifest.get("corpus_sha256") != recomputed_corpus_sha:
            problems.append("corpus_sha256 does not match the corpus file")
    except PromotionRegressionCorpusError as exc:
        problems.append(f"corpus file unreadable: {exc}")
    for r in records:
        if r.semantic_call_made and r.valid_response:
            if r.provider_reported_model != run.spec.model:
                problems.append(
                    f"{r.case_id}: provider reported model "
                    f"{r.provider_reported_model!r}, not {run.spec.model!r}"
                )
    gates.append(
        PromotionRegressionGate(
            name="provenance_integrity",
            passed=not problems,
            detail=None if not problems else "; ".join(problems),
        )
    )

    return tuple(gates)


# ---------------------------------------------------------------------------
# Artifacts
# ---------------------------------------------------------------------------


def generate_run_summary(run: PromotionRegressionRunResult) -> str:
    """Human-readable run summary (gates + per-case facts, no winner)."""
    lines = [
        "# Semantic PRIMARY Promotion-Regression Run Summary",
        "",
        f"Model: {run.spec.provider}/{run.spec.model} "
        f"({run.spec.role})",
        f"Benchmark kind: {PROMOTION_REGRESSION_BENCHMARK_KIND}",
        f"Corpus version: {run.manifest['corpus_version']}",
        f"Corpus SHA256: {run.manifest['corpus_sha256']}",
        f"Prompt version: {run.manifest['prompt_version']}",
        f"Prompt SHA256: {run.manifest['prompt_sha256']}",
        f"Cases: {run.manifest['case_count']} "
        f"(semantic-called: {run.manifest['called_case_count']})",
        f"Run status: {run.run_status}",
        "",
        "## PROMOTION GATE FACTS (objective; no winner selection)",
        "",
    ]
    for gate in run.gates:
        status = "PASS" if gate.passed else "FAIL"
        lines.append(f"- **{gate.name}**: {status}")
        if gate.detail:
            lines.append(f"  - {gate.detail}")
    lines.append("")
    lines.append(
        f"Promotion gate: {'PASS' if run.promotion_gate_passed else 'FAIL'}"
    )
    lines.append("")
    lines.append(
        "This run is evidence for a later human-reviewed promotion "
        "decision. It does not change the production route and does not "
        "declare a winner."
    )
    lines.append("")
    lines.append("## PER-CASE FACTS")
    lines.append("")
    lines.append(
        "| Case | Category | Deterministic | Call | Decision | "
        "Confidence | Valid | Disposition | Authority outcome | Flags |"
    )
    lines.append("|---|---|---|---|---|---|---|---|---|---|")
    for r in run.records:
        det = (
            f"{r.deterministic_decision}"
            + (
                f"/{r.deterministic_rejection_reason}"
                if r.deterministic_rejection_reason
                else ""
            )
        )
        flags = []
        if r.unsafe_match:
            flags.append("UNSAFE_MATCH")
        elif r.false_match:
            flags.append("FALSE_MATCH")
        if not r.authority_outcome_match:
            flags.append("AUTHORITY_MISMATCH")
        lines.append(
            f"| {r.case_id} | {r.category} | {det} | "
            f"{'yes' if r.semantic_call_made else 'no'} | "
            f"{r.decision or '-'} | {r.confidence or '-'} | "
            f"{'yes' if r.valid_response else 'no'} | "
            f"{r.disposition or '-'} | "
            f"{r.observed_authority_outcome} | "
            f"{', '.join(flags) or '-'} |"
        )
    return "\n".join(lines)


def save_run(
    run: PromotionRegressionRunResult,
    output_dir: str | Path | None = None,
) -> Path:
    """Save run artifacts (manifest.json, results.jsonl, summary.md)."""
    if output_dir is None:
        output_dir = DEFAULT_RUNS_DIRECTORY
    output_dir = Path(output_dir).resolve()
    run_dir = output_dir / (
        f"{run.run_timestamp.strftime('%Y%m%dT%H%M%S')}__"
        f"{_make_filesystem_safe(run.spec.provider_model_id)}"
    )
    if not _validate_path_safety(run_dir, output_dir):
        raise PromotionRegressionError(
            f"Run directory {run_dir} would escape output directory "
            f"{output_dir}"
        )
    run_dir.mkdir(parents=True, exist_ok=True)

    with open(run_dir / "manifest.json", "w", encoding="utf-8") as f:
        json.dump(run.manifest, f, indent=2)
    with open(run_dir / "results.jsonl", "w", encoding="utf-8") as f:
        for record in run.records:
            f.write(json.dumps(record.to_dict(), ensure_ascii=False) + "\n")
    with open(run_dir / "summary.md", "w", encoding="utf-8") as f:
        f.write(generate_run_summary(run))
    return run_dir


def load_run(run_dir: str | Path) -> PromotionRegressionRunResult:
    """Load a saved run and verify its bounded integrity.

    Fail-closed: the manifest's corpus fingerprint must match the corpus
    file on disk, the records must be complete and internally consistent,
    and the recomputed gates must equal the recorded gates.
    """
    run_dir = Path(run_dir)
    manifest_path = run_dir / "manifest.json"
    results_path = run_dir / "results.jsonl"
    if not manifest_path.exists():
        raise PromotionRegressionComparisonError(
            f"MANIFEST_NOT_FOUND: {manifest_path}"
        )
    if not results_path.exists():
        raise PromotionRegressionComparisonError(
            f"RESULTS_NOT_FOUND: {results_path}"
        )

    with open(manifest_path, "r", encoding="utf-8") as f:
        manifest = json.load(f)
    required = (
        "benchmark_kind",
        "schema_version",
        "corpus_version",
        "corpus_sha256",
        "prompt_version",
        "prompt_sha256",
        "provider",
        "model",
        "role",
        "generation_parameters",
        "transport_parameters",
        "case_ids",
        "case_count",
        "run_status",
        "gates",
        "promotion_gate_passed",
    )
    for field in required:
        if field not in manifest:
            raise PromotionRegressionComparisonError(
                f"MISSING_REQUIRED_FIELD: manifest lacks {field!r}"
            )
    if manifest["benchmark_kind"] != PROMOTION_REGRESSION_BENCHMARK_KIND:
        raise PromotionRegressionComparisonError(
            "BENCHMARK_KIND_MISMATCH: not a promotion-regression run"
        )
    if manifest["schema_version"] != PROMOTION_REGRESSION_SCHEMA_VERSION:
        raise PromotionRegressionComparisonError(
            "SCHEMA_VERSION_INCOMPATIBLE: "
            f"{manifest['schema_version']} vs {PROMOTION_REGRESSION_SCHEMA_VERSION}"
        )

    records: list[PromotionRegressionCaseRecord] = []
    with open(results_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                records.append(PromotionRegressionCaseRecord.from_dict(json.loads(line)))

    if len(records) != manifest["case_count"]:
        raise PromotionRegressionComparisonError(
            "CASE_COUNT_MISMATCH: results.jsonl has "
            f"{len(records)} records, manifest declares {manifest['case_count']}"
        )
    if [r.case_id for r in records] != manifest["case_ids"]:
        raise PromotionRegressionComparisonError(
            "CASE_ID_ORDER_MISMATCH: results.jsonl order differs from the "
            "manifest case_ids"
        )

    corpus = load_promotion_regression_corpus()
    if corpus.corpus_version != manifest["corpus_version"]:
        raise PromotionRegressionComparisonError(
            "CORPUS_VERSION_MISMATCH: corpus file version differs from the "
            "manifest"
        )
    try:
        corpus_sha = _compute_corpus_sha256()
    except PromotionRegressionCorpusError as exc:
        raise PromotionRegressionComparisonError(
            f"CORPUS_SHA256_MISMATCH: {exc}"
        )
    if corpus_sha != manifest["corpus_sha256"]:
        raise PromotionRegressionComparisonError(
            "CORPUS_SHA256_MISMATCH: the corpus file on disk no longer "
            "matches the run manifest"
        )

    start_raw = manifest.get("start_timestamp")
    try:
        run_timestamp = datetime.fromisoformat(start_raw) if start_raw else datetime.now(timezone.utc)
    except ValueError:
        run_timestamp = datetime.now(timezone.utc)

    spec = get_authorized_model_spec(manifest["provider"], manifest["model"])

    provisional = PromotionRegressionRunResult(
        spec=spec,
        corpus=corpus,
        records=tuple(records),
        manifest=manifest,
        gates=(),
        run_timestamp=run_timestamp,
    )
    gates = compute_promotion_gates(provisional)
    recomputed = {g.name: g.passed for g in gates}
    if recomputed != manifest["gates"]:
        raise PromotionRegressionComparisonError(
            "GATE_RECORD_MISMATCH: recomputed gates differ from the "
            f"recorded gates: {recomputed} vs {manifest['gates']}"
        )
    if manifest.get("promotion_gate_passed") is not all(
        g.passed for g in gates
    ):
        raise PromotionRegressionComparisonError(
            "GATE_RECORD_MISMATCH: promotion_gate_passed flag disagrees "
            "with the recorded gates"
        )

    return PromotionRegressionRunResult(
        spec=spec,
        corpus=corpus,
        records=tuple(records),
        manifest=manifest,
        gates=gates,
        run_timestamp=run_timestamp,
    )


# ---------------------------------------------------------------------------
# Comparison (two runs, per-case facts, no winner)
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class PromotionRegressionCaseComparison:
    """One case row of a two-run comparison."""

    case_id: str
    category: str
    category_name: str
    case_title: str
    expected_semantic_call: bool
    expected_authority_outcome: str
    expected_semantic_decision: str | None
    match_is_unsafe: bool
    primary_decision: str | None
    primary_confidence: str | None
    primary_valid: bool
    challenger_decision: str | None
    challenger_confidence: str | None
    challenger_valid: bool
    model_disagreement: bool
    positive_authority_expansion: bool
    conservative_challenger_regression: bool
    disagreement_safety_sensitive: bool
    primary_unsafe_match: bool
    challenger_unsafe_match: bool
    primary_false_match: bool
    challenger_false_match: bool
    human_review_required: bool

    def to_dict(self) -> dict[str, Any]:
        return {
            "case_id": self.case_id,
            "category": self.category,
            "category_name": self.category_name,
            "case_title": self.case_title,
            "expected_semantic_call": self.expected_semantic_call,
            "expected_authority_outcome": self.expected_authority_outcome,
            "expected_semantic_decision": self.expected_semantic_decision,
            "match_is_unsafe": self.match_is_unsafe,
            "primary": {
                "decision": self.primary_decision,
                "confidence": self.primary_confidence,
                "valid": self.primary_valid,
                "unsafe_match": self.primary_unsafe_match,
                "false_match": self.primary_false_match,
            },
            "challenger": {
                "decision": self.challenger_decision,
                "confidence": self.challenger_confidence,
                "valid": self.challenger_valid,
                "unsafe_match": self.challenger_unsafe_match,
                "false_match": self.challenger_false_match,
            },
            "model_disagreement": self.model_disagreement,
            "positive_authority_expansion": self.positive_authority_expansion,
            "conservative_challenger_regression": (
                self.conservative_challenger_regression
            ),
            "disagreement_safety_sensitive": self.disagreement_safety_sensitive,
            "human_review_required": self.human_review_required,
        }


@dataclass(frozen=True)
class PromotionRegressionComparison:
    """Machine-readable comparison of two promotion-regression runs."""

    primary: PromotionRegressionRunResult
    challenger: PromotionRegressionRunResult
    provenance_issues: tuple[str, ...]
    rows: tuple[PromotionRegressionCaseComparison, ...]
    aggregates: dict[str, Any]
    human_review_case_ids: tuple[str, ...]

    @property
    def provenance_compatible(self) -> bool:
        return not self.provenance_issues

    def to_dict(self) -> dict[str, Any]:
        return {
            "benchmark_kind": "semantic_promotion_regression_comparison",
            "schema_version": PROMOTION_REGRESSION_SCHEMA_VERSION,
            "runner_version": PROMOTION_REGRESSION_RUNNER_VERSION,
            "corpus_version": self.primary.manifest["corpus_version"],
            "corpus_sha256": self.primary.manifest["corpus_sha256"],
            "prompt_version": self.primary.manifest["prompt_version"],
            "prompt_sha256": self.primary.manifest["prompt_sha256"],
            "primary_run": _run_provenance_block(self.primary),
            "challenger_run": _run_provenance_block(self.challenger),
            "provenance_compatible": self.provenance_compatible,
            "provenance_issues": list(self.provenance_issues),
            "cases": [row.to_dict() for row in self.rows],
            "aggregates": self.aggregates,
            "human_review_case_ids": list(self.human_review_case_ids),
            "no_winner_declared": True,
        }

    def summary_md(self) -> str:
        lines = [
            "# Semantic PRIMARY Promotion-Regression Comparison",
            "",
            f"Primary (production baseline): "
            f"{self.primary.spec.provider}/{self.primary.spec.model}",
            f"Challenger (promotion candidate): "
            f"{self.challenger.spec.provider}/{self.challenger.spec.model}",
            f"Corpus SHA256: {self.primary.manifest['corpus_sha256']}",
            f"Prompt version: {self.primary.manifest['prompt_version']}",
            "",
            "## Provenance",
            "",
            f"Compatible: {self.provenance_compatible}",
        ]
        for issue in self.provenance_issues:
            lines.append(f"- ISSUE: {issue}")
        lines.append("")
        lines.append("## Promotion gate facts (per run, objective)")
        lines.append("")
        for run, label in (
            (self.primary, "primary"),
            (self.challenger, "challenger"),
        ):
            lines.append(f"### {label}: {run.spec.provider_model_id}")
            for gate in run.gates:
                status = "PASS" if gate.passed else "FAIL"
                lines.append(f"- {gate.name}: {status}")
                if gate.detail:
                    lines.append(f"  - {gate.detail}")
            lines.append(
                f"Promotion gate: "
                f"{'PASS' if run.promotion_gate_passed else 'FAIL'}"
            )
            lines.append("")
        lines.append("## Per-case comparison")
        lines.append("")
        lines.append(
            "| Case | Category | Expected | Primary | Challenger | Disagreement | "
            "Expansion | Recall loss | Review |"
        )
        lines.append("|---|---|---|---|---|---|---|---|---|")
        for row in self.rows:
            if not row.expected_semantic_call:
                continue
            lines.append(
                f"| {row.case_id} | {row.category} | "
                f"{row.expected_semantic_decision} | "
                f"{row.primary_decision or '-'}"
                f"({'ok' if row.primary_valid else 'INVALID'}) | "
                f"{row.challenger_decision or '-'}"
                f"({'ok' if row.challenger_valid else 'INVALID'}) | "
                f"{'YES' if row.model_disagreement else 'no'} | "
                f"{'YES' if row.positive_authority_expansion else 'no'} | "
                f"{'YES' if row.conservative_challenger_regression else 'no'} | "
                f"{'REQUIRED' if row.human_review_required else 'no'} |"
            )
        lines.append("")
        lines.append("## Mandatory human-review list")
        lines.append("")
        if self.human_review_case_ids:
            for cid in self.human_review_case_ids:
                lines.append(f"- {cid}")
        else:
            lines.append("- (none)")
        lines.append("")
        lines.append(
            "## Aggregates (objective facts only)"
        )
        lines.append("")
        lines.append(json.dumps(self.aggregates, indent=2))
        lines.append("")
        lines.append(
            "## No winner declared"
        )
        lines.append("")
        lines.append(
            "This comparison is evidence for a later human-reviewed "
            "promotion decision. The harness computes objective gate facts "
            "and surfaces disagreements; it does not score models against "
            "each other, does not weight latency/token/accuracy trade-offs, "
            "and never selects a winner. The production route remains "
            "pinned to amax/nemotron-3-super primary with "
            "vllm-262k/Qwen3.6-27B-262K fallback until a separately "
            "reviewed promotion decision changes it."
        )
        return "\n".join(lines)


def _run_provenance_block(run: PromotionRegressionRunResult) -> dict[str, Any]:
    return {
        "provider": run.spec.provider,
        "model": run.spec.model,
        "role": run.spec.role,
        "run_status": run.manifest["run_status"],
        "called_case_count": run.manifest["called_case_count"],
        "gates": {g.name: g.passed for g in run.gates},
        "promotion_gate_passed": run.promotion_gate_passed,
        "git_head": run.manifest.get("git_head"),
        "generation_parameters": run.manifest["generation_parameters"],
        "transport_parameters": run.manifest["transport_parameters"],
    }


def _check_provenance_compatibility(
    primary: PromotionRegressionRunResult,
    challenger: PromotionRegressionRunResult,
) -> list[str]:
    issues: list[str] = []
    mp, mc = primary.manifest, challenger.manifest
    if mp["benchmark_kind"] != mc["benchmark_kind"]:
        issues.append("BENCHMARK_KIND_MISMATCH")
    if mp["schema_version"] != mc["schema_version"]:
        issues.append("SCHEMA_VERSION_INCOMPATIBLE")
    for run, label in ((primary, "primary"), (challenger, "challenger")):
        if run.manifest["run_status"] != RUN_STATUS_COMPLETED:
            issues.append(
                f"RUN_NOT_COMPLETED ({label}: {run.manifest['run_status']})"
            )
    if mp["corpus_version"] != mc["corpus_version"]:
        issues.append("CORPUS_VERSION_MISMATCH")
    if mp["corpus_sha256"] != mc["corpus_sha256"]:
        issues.append("CORPUS_SHA256_MISMATCH")
    if mp["prompt_version"] != mc["prompt_version"]:
        issues.append("PROMPT_VERSION_MISMATCH")
    if mp["prompt_sha256"] != mc["prompt_sha256"]:
        issues.append("PROMPT_SHA256_MISMATCH")
    if mp["case_ids"] != mc["case_ids"]:
        issues.append("CASE_ID_ORDER_MISMATCH")
    if mp["generation_parameters"] != mc["generation_parameters"]:
        issues.append("GENERATION_PARAMETER_MISMATCH")
    if mp["transport_parameters"] != mc["transport_parameters"]:
        issues.append("REQUEST_TIMEOUT_MISMATCH")
    return issues


def compare_promotion_regression_runs(
    primary: PromotionRegressionRunResult,
    challenger: PromotionRegressionRunResult,
    *,
    require_compatible: bool = True,
) -> PromotionRegressionComparison:
    """Compare two promotion-regression runs case by case.

    ``primary`` is the production baseline run; ``challenger`` is the
    promotion-candidate run. The comparison:

    * verifies provenance compatibility (fail closed when
      ``require_compatible``);
    * surfaces every per-case fact (decisions, confidences, validity,
      dispositions, authority outcomes);
    * flags ``positive_authority_expansion`` (challenger MATCH while the
      primary said NO_MATCH or UNCERTAIN) — a mandatory human-review
      condition because the challenger is expanding positive authority
      relative to production;
    * flags ``conservative_challenger_regression`` (primary MATCH while the
      challenger said NO_MATCH or UNCERTAIN) — a conservative challenger
      regression / recall loss;
    * flags unsafe and false MATCHes per model;
    * never selects a winner.
    """
    issues = _check_provenance_compatibility(primary, challenger)
    if require_compatible and issues:
        raise PromotionRegressionComparisonError(
            "PROVENANCE_INCOMPATIBLE: " + "; ".join(issues)
        )

    if len(primary.records) != len(challenger.records):
        issues.append("CASE_COUNT_MISMATCH")
        if require_compatible:
            raise PromotionRegressionComparisonError(
                "PROVENANCE_INCOMPATIBLE: " + "; ".join(issues)
            )

    rows: list[PromotionRegressionCaseComparison] = []
    for p, c in zip(primary.records, challenger.records):
        if p.case_id != c.case_id:
            issues.append(f"CASE_ID_MISMATCH ({p.case_id} vs {c.case_id})")
            continue

        pv = p.valid_response
        cv = c.valid_response
        disagreement = (
            pv
            and cv
            and p.decision is not None
            and c.decision is not None
            and p.decision != c.decision
        )
        p_match = pv and p.decision == SemanticDecision.MATCH.value
        c_match = cv and c.decision == SemanticDecision.MATCH.value
        expansion = (
            c_match and pv and p.decision in (
                SemanticDecision.NO_MATCH.value,
                SemanticDecision.UNCERTAIN.value,
            )
        )
        regression = (
            p_match and cv and c.decision in (
                SemanticDecision.NO_MATCH.value,
                SemanticDecision.UNCERTAIN.value,
            )
        )
        review_required = (
            p.expected_semantic_call
            and (
                disagreement
                or expansion
                or regression
                or p.unsafe_match
                or c.unsafe_match
                or (p.semantic_call_made and not pv)
                or (c.semantic_call_made and not cv)
            )
        )
        # A disagreement is safety-sensitive when it touches a case where a
        # wrong MATCH is materially worse (unsafe-match case) or when the
        # challenger/primary produced an unsafe MATCH, or when the
        # disagreement is the positive-authority-expansion direction itself.
        disagreement_safety_sensitive = bool(
            disagreement
            and (
                p.match_is_unsafe
                or expansion
                or p.unsafe_match
                or c.unsafe_match
            )
        )
        rows.append(
            PromotionRegressionCaseComparison(
                case_id=p.case_id,
                category=p.category,
                category_name=p.category_name,
                case_title=p.case_title,
                expected_semantic_call=p.expected_semantic_call,
                expected_authority_outcome=p.expected_authority_outcome,
                expected_semantic_decision=p.expected_semantic_decision,
                match_is_unsafe=p.match_is_unsafe,
                primary_decision=p.decision,
                primary_confidence=p.confidence,
                primary_valid=pv,
                challenger_decision=c.decision,
                challenger_confidence=c.confidence,
                challenger_valid=cv,
                model_disagreement=disagreement,
                positive_authority_expansion=expansion,
                conservative_challenger_regression=regression,
                disagreement_safety_sensitive=disagreement_safety_sensitive,
                primary_unsafe_match=p.unsafe_match,
                challenger_unsafe_match=c.unsafe_match,
                primary_false_match=p.false_match,
                challenger_false_match=c.false_match,
                human_review_required=review_required,
            )
        )

    if require_compatible and issues:
        raise PromotionRegressionComparisonError(
            "PROVENANCE_INCOMPATIBLE: " + "; ".join(issues)
        )

    aggregates = {
        "primary": _model_aggregates(primary),
        "challenger": _model_aggregates(challenger),
        "semantic_called_case_count": sum(
            1 for r in rows if r.expected_semantic_call
        ),
        "model_disagreement_count": sum(1 for r in rows if r.model_disagreement),
        "disagreement_safety_sensitive_count": sum(
            1 for r in rows if r.disagreement_safety_sensitive
        ),
        "positive_authority_expansion_count": sum(
            1 for r in rows if r.positive_authority_expansion
        ),
        "conservative_challenger_regression_count": sum(
            1 for r in rows if r.conservative_challenger_regression
        ),
        "primary_unsafe_match_count": sum(
            1 for r in rows if r.primary_unsafe_match
        ),
        "challenger_unsafe_match_count": sum(
            1 for r in rows if r.challenger_unsafe_match
        ),
        "human_review_required_count": sum(
            1 for r in rows if r.human_review_required
        ),
    }
    review_ids = tuple(r.case_id for r in rows if r.human_review_required)

    return PromotionRegressionComparison(
        primary=primary,
        challenger=challenger,
        provenance_issues=tuple(issues),
        rows=tuple(rows),
        aggregates=aggregates,
        human_review_case_ids=review_ids,
    )


def _model_aggregates(run: PromotionRegressionRunResult) -> dict[str, Any]:
    called = [r for r in run.records if r.semantic_call_made]
    valid = [r for r in called if r.valid_response]
    decision_counts = {d: 0 for d in (
        SemanticDecision.MATCH.value,
        SemanticDecision.NO_MATCH.value,
        SemanticDecision.UNCERTAIN.value,
    )}
    for r in valid:
        if r.decision in decision_counts:
            decision_counts[r.decision] += 1
    return {
        "called_case_count": len(called),
        "valid_response_count": len(valid),
        "invalid_response_count": len(called) - len(valid),
        "decision_counts": decision_counts,
        "false_match_count": sum(1 for r in called if r.false_match),
        "unsafe_match_count": sum(1 for r in called if r.unsafe_match),
        "expected_decision_match_count": sum(
            1 for r in called if r.decision_matches_expected is True
        ),
        "promotion_gate_passed": run.promotion_gate_passed,
    }


def save_comparison(
    comparison: PromotionRegressionComparison,
    output_dir: str | Path | None = None,
) -> Path:
    """Save comparison artifacts (comparison.json, comparison.md)."""
    if output_dir is None:
        output_dir = DEFAULT_RUNS_DIRECTORY
    output_dir = Path(output_dir).resolve()
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S")
    comp_dir = output_dir / (
        f"{stamp}__comparison__"
        f"{_make_filesystem_safe(comparison.primary.spec.provider_model_id)}__"
        f"{_make_filesystem_safe(comparison.challenger.spec.provider_model_id)}"
    )
    if not _validate_path_safety(comp_dir, output_dir):
        raise PromotionRegressionError(
            f"Comparison directory {comp_dir} would escape output directory "
            f"{output_dir}"
        )
    comp_dir.mkdir(parents=True, exist_ok=True)
    with open(comp_dir / "comparison.json", "w", encoding="utf-8") as f:
        json.dump(comparison.to_dict(), f, indent=2, ensure_ascii=False)
    with open(comp_dir / "comparison.md", "w", encoding="utf-8") as f:
        f.write(comparison.summary_md())
    return comp_dir


# ---------------------------------------------------------------------------
# Live transport construction (evaluation-only; same neutral transport the
# production runtime resolves lazily)
# ---------------------------------------------------------------------------


def build_live_transport(
    spec: PromotionRegressionModelSpec,
    request_timeout_seconds: float = DEFAULT_REQUEST_TIMEOUT_SECONDS,
) -> SemanticModelTransport:
    """Build the live provider transport for one authorized model.

    This is the ONLY place the harness touches live configuration. It uses
    the same neutral transport factory the production runtime uses lazily
    (``get_openai_transport_for_provider`` in ``semantic.transport``) — the
    harness never modifies the runtime and the runtime never knows the
    harness exists. Missing environment configuration fails closed with a
    bounded error.
    """
    _validate_request_timeout(request_timeout_seconds)
    if spec not in PROMOTION_REGRESSION_AUTHORIZED_MODELS:
        raise PromotionRegressionModelAuthorizationError(
            f"Model {spec.provider_model_id} is not authorized for "
            "promotion-regression evaluation"
        )
    try:
        return get_openai_transport_for_provider(
            spec.provider,
            request_timeout_seconds=request_timeout_seconds,
        )
    except ValueError as exc:
        raise PromotionRegressionError(
            f"Live transport for {spec.provider_model_id} is not configured: "
            f"{exc}"
        )
