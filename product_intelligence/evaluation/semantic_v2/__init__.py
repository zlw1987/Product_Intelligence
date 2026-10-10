"""The Q3-A Semantic V2 offline qualification system.

Independent, deterministic, offline qualification infrastructure for
the exact frozen Semantic V2 contract:

* the versioned, independently labeled qualification corpus
  (``fixtures`` = the auditable source; ``corpus`` = the strict
  loader / decoder / digest / manifest surface);
* the captured-response artifact contract (``capture``) and the
  independent DIRECT_MODEL_QUALIFICATION capture schema
  (``direct_capture``);
* the offline evaluator using the REAL production V2 parser and the
  REAL frozen V2 input contract (``evaluator``);
* the mandatory safety gates and the fail-closed decision
  (``gates``); the DRAFT qualification policy (``policy``);
* the reproducible offline report (``report``);
* the offline command surface (``cli``).

Nothing in this package calls a model or touches the network during
offline replay; it grants no authority (the report records the
V2_AUTHORITY_QUALIFIED marker as-is and the decision vocabulary
contains no authority grant).
"""

from product_intelligence.evaluation.semantic_v2.canonical import (
    UTC_INSTANT_PATTERN,
    assert_json_native,
    canonical_sha256,
    canonically_encode,
)
from product_intelligence.evaluation.semantic_v2.corpus import (
    AMBIGUOUS_CASE_CLASS,
    AUTHORITATIVE_CASE_CLASS,
    BINDING_CORPUS_VERSIONS,
    CONTRACT_NEGATIVE_CASE_CLASS,
    CORPUS_SCHEMA_VERSION,
    CorpusBundle,
    CorpusCase,
    CorpusError,
    CorpusIntegrityError,
    CorpusInputRejectionError,
    CorpusSchemaError,
    KNOWN_PRODUCTION_BINDINGS,
    build_manifest_document,
    decode_match_case,
    load_corpus,
    reject_class_for,
    verify_manifest,
)
from product_intelligence.evaluation.semantic_v2.capture import (
    CAPTURE_MODE,
    CAPTURE_SCHEMA_VERSION,
    CaptureDocument,
    CaptureError,
    CaptureIntegrityError,
    CaptureRecord,
    FALLBACK_ELIGIBLE_STATUSES,
    CAPTURE_STATUS_TO_FALLBACK_REASON,
    PROMPT_VERSION_V2_1,
    V2_1_CONTRACT_BINDING,
    load_capture,
    verify_capture_against_corpus,
)
from product_intelligence.evaluation.semantic_v2.direct_capture import (
    DIRECT_CAPTURE_MODE,
    DIRECT_CAPTURE_SCHEMA_VERSION,
    DIRECT_EXECUTION_STATUSES,
    DIRECT_KNOWN_PROMPT_VERSIONS,
    DirectCaptureDocument,
    DirectCaptureError,
    DirectCaptureIntegrityError,
    DirectCaptureRecord,
    load_direct_capture,
    verify_direct_capture_against_corpus,
)
from product_intelligence.evaluation.semantic_v2.evaluator import (
    OUTCOME_STATES,
    SEVERITIES,
    VERDICTS,
    CaseOutcome,
    EvaluationResult,
    QualificationContractError,
    classify_raw_response,
    compute_metrics,
    evaluate_direct_for_model,
    evaluate_no_capture,
    evaluate_offline,
)
from product_intelligence.evaluation.semantic_v2.gates import (
    DECISIONS,
    HARD_SAFETY_GATES,
    GateResult,
    decide,
    evaluate_safety_gates,
)
from product_intelligence.evaluation.semantic_v2.policy import (
    POLICY_SCHEMA_VERSION,
    THRESHOLD_NAMES,
    PolicyDocument,
    PolicyError,
    evaluate_thresholds,
    load_policy,
    policy_applies_to,
)
from product_intelligence.evaluation.semantic_v2.report import (
    DIRECT_REPORT_KIND,
    PRODUCTION_REPORT_KIND,
    REPORT_SCHEMA_VERSION,
    ReportError,
    build_direct_report,
    build_report,
    render_markdown,
    verify_direct_report,
    verify_report,
)

__all__ = [
    "AMBIGUOUS_CASE_CLASS",
    "AUTHORITATIVE_CASE_CLASS",
    "BINDING_CORPUS_VERSIONS",
    "CONTRACT_NEGATIVE_CASE_CLASS",
    "CORPUS_SCHEMA_VERSION",
    "CAPTURE_SCHEMA_VERSION",
    "CAPTURE_MODE",
    "DIRECT_CAPTURE_MODE",
    "DIRECT_CAPTURE_SCHEMA_VERSION",
    "DIRECT_EXECUTION_STATUSES",
    "DIRECT_KNOWN_PROMPT_VERSIONS",
    "DIRECT_REPORT_KIND",
    "KNOWN_PRODUCTION_BINDINGS",
    "PRODUCTION_REPORT_KIND",
    "PROMPT_VERSION_V2_1",
    "POLICY_SCHEMA_VERSION",
    "REPORT_SCHEMA_VERSION",
    "UTC_INSTANT_PATTERN",
    "V2_1_CONTRACT_BINDING",
    "CaptureDocument",
    "CaptureError",
    "CaptureIntegrityError",
    "CaptureRecord",
    "CAPTURE_STATUS_TO_FALLBACK_REASON",
    "DirectCaptureDocument",
    "DirectCaptureError",
    "DirectCaptureIntegrityError",
    "DirectCaptureRecord",
    "FALLBACK_ELIGIBLE_STATUSES",
    "CaseOutcome",
    "CorpusBundle",
    "CorpusCase",
    "CorpusError",
    "CorpusIntegrityError",
    "CorpusInputRejectionError",
    "CorpusSchemaError",
    "DECISIONS",
    "EvaluationResult",
    "GateResult",
    "HARD_SAFETY_GATES",
    "OUTCOME_STATES",
    "PolicyDocument",
    "PolicyError",
    "QualificationContractError",
    "ReportError",
    "SEVERITIES",
    "THRESHOLD_NAMES",
    "VERDICTS",
    "assert_json_native",
    "build_manifest_document",
    "build_direct_report",
    "build_report",
    "canonical_sha256",
    "canonically_encode",
    "classify_raw_response",
    "compute_metrics",
    "decode_match_case",
    "decide",
    "evaluate_direct_for_model",
    "evaluate_no_capture",
    "evaluate_offline",
    "evaluate_safety_gates",
    "evaluate_thresholds",
    "load_capture",
    "load_corpus",
    "load_direct_capture",
    "load_policy",
    "policy_applies_to",
    "render_markdown",
    "reject_class_for",
    "verify_capture_against_corpus",
    "verify_direct_capture_against_corpus",
    "verify_direct_report",
    "verify_manifest",
    "verify_report",
]
