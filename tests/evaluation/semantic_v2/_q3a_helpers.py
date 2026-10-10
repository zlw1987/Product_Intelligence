"""Shared helpers for the Q3-A qualification test suite.

Every capture built here is an explicit TEST FIXTURE (declared in the
artifact's provenance): it is not a model response and is never treated
as one. The helpers exercise the strict capture contract against the
committed corpus.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[3]
CORPUS_DIR = REPO_ROOT / "evaluation" / "semantic_v2_qualification"
CORPUS_PATH = CORPUS_DIR / "corpus_v1.json"
MANIFEST_PATH = CORPUS_DIR / "manifest_v1.json"
# Q3-B5-P1: the corpus 1.1.0 binding-only re-seal (the separately
# versioned 2.1 binding) and its reproducible manifest; both versions
# coexist, 1.0.0 stays bound to the 2.0 binding for historical evidence.
CORPUS_2_1_PATH = CORPUS_DIR / "corpus_2_1.json"
MANIFEST_2_1_PATH = CORPUS_DIR / "manifest_2_1.json"
POLICY_PATH = (
    CORPUS_DIR / "policy" / "qualification_policy_draft_1.json"
)
BASELINE_REPORT_DIR = CORPUS_DIR / "reports" / "q3a_baseline"
# The 2.1 no-capture baseline reports (both pinned route candidates),
# committed alongside the re-seal; reproducible byte-for-byte by test.
BASELINE_2_1_REPORT_DIR = CORPUS_DIR / "reports" / "q3b5_baseline_2_1"

from product_intelligence.evaluation.semantic_v2.capture import (  # noqa: E402
    FALLBACK_ROUTE,
    PRIMARY_ROUTE,
)
from product_intelligence.evaluation.semantic_v2.corpus import (  # noqa: E402
    CorpusBundle,
    load_corpus,
)

#: Bounded conflicting-attribute dimension for one conflict class when
#: the class is not itself a bounded attribute dimension.
_CONFLICT_ATTR_DIMENSION = {
    "OTHER_MATERIAL_CONFLICT": "PRODUCT_FAMILY",
    "MPN_IDENTITY": "REVISION_OR_SUFFIX",
}

_NAME_CODE = {
    "MPN_IDENTITY": "NO_MATCH_MPN_IDENTITY",
    "PRODUCT_FAMILY": "NO_MATCH_PRODUCT_FAMILY",
    "GENERATION": "NO_MATCH_GENERATION",
    "CAPACITY": "NO_MATCH_CAPACITY",
    "INTERFACE": "NO_MATCH_INTERFACE",
    "FORM_FACTOR": "NO_MATCH_FORM_FACTOR",
    "PRODUCT_ROLE": "NO_MATCH_PRODUCT_ROLE",
    "ACCESSORY_RELATION": "NO_MATCH_ACCESSORY",
    "PACKAGING_QUANTITY": "NO_MATCH_PACKAGING",
    "BUNDLE": "NO_MATCH_BUNDLE",
}


def load_corpus_bundle() -> CorpusBundle:
    return load_corpus(CORPUS_PATH)


def make_response(
    decision: str,
    *,
    confidence: str = "HIGH",
    reason_code: str | None = None,
    matched: tuple[tuple[str, str], ...] = (),
    conflicting: tuple[tuple[str, str], ...] = (),
    missing: tuple[str, ...] = (),
    conflict_classes: tuple[str, ...] = (),
) -> str:
    """One raw V2 response string (the bounded six-key JSON object)."""
    if reason_code is None:
        if decision == "MATCH":
            reason_code = "MATCH_EXACT_PRODUCT_CONTEXT"
        elif decision == "NO_MATCH":
            if len(conflict_classes) >= 2:
                reason_code = "NO_MATCH_MULTIPLE_CONFLICTS"
            elif conflict_classes:
                reason_code = _NAME_CODE.get(
                    conflict_classes[0], "NO_MATCH_OTHER"
                )
            else:
                reason_code = "NO_MATCH_OTHER"
                conflict_classes = ("OTHER_MATERIAL_CONFLICT",)
        else:
            reason_code = (
                "UNCERTAIN_MISSING_CRITICAL_ATTRIBUTES"
                if missing
                else "UNCERTAIN_IDENTIFIER_RELATION"
            )
    return json.dumps(
        {
            "decision": decision,
            "confidence": confidence,
            "reason_code": reason_code,
            "matched_attributes": [
                {"dimension": d, "detail": t} for d, t in matched
            ],
            "conflicting_attributes": [
                {
                    "dimension": _CONFLICT_ATTR_DIMENSION.get(d, d),
                    "detail": t,
                }
                for d, t in conflicting
            ],
            "missing_critical_attributes": list(missing),
            "conflict_classes": list(conflict_classes),
        }
    )


def default_response_for(case: Any) -> str:
    """The label-consistent response for one corpus case (test fixture
    semantics: what a fully correct model would return on this label)."""
    expected = case.expected
    decision = expected["decision"]
    if decision == "MATCH":
        reason = "MATCH_EXACT_PRODUCT_CONTEXT"
        if case.case_id == "V2Q-SSD-U5NM2-RELAUTH-0020":
            reason = "MATCH_AUTHORIZED_IDENTIFIER_RELATION"
        return make_response(
            "MATCH",
            reason_code=reason,
            matched=(("PRODUCT_FAMILY", "aligned"),),
        )
    if decision == "NO_MATCH":
        classes = tuple(sorted(expected["conflict_classes"]))
        return make_response(
            "NO_MATCH",
            conflicting=tuple((c, "observed") for c in classes),
            conflict_classes=classes,
        )
    return make_response(
        "UNCERTAIN",
        missing=tuple(expected["missing_dimensions"]),
    )


def write_capture(
    path: Path,
    corpus: CorpusBundle,
    decisions: dict[str, str] | None = None,
    execution: str = "primary_ok",
    attempts_overrides: dict[str, list[dict[str, Any]]] | None = None,
    include_all: bool = True,
    capture_run_id: str = "Q3A-TEST-FIXTURE",
    captured_at: str = "2026-10-08T12:00:00Z",
    provenance_note: str = (
        "Q3-A test fixture: declared responses, not model output"
    ),
) -> Path:
    """Write one strict capture document for the committed corpus.

    A capture records ONE RUN of the frozen pinned route; the model
    under qualification is projected from the run, never named in the
    header. ``execution`` shapes the attempts:

    * ``primary_ok`` (default): every record is a single PRIMARY OK
      attempt (the primary answered; the fallback was never invoked);
    * ``fallback``: every record is a PRIMARY execution failure + a
      FALLBACK OK attempt (the fallback answered).

    ``decisions`` maps case_id -> decision (overrides the label's
    expected decision for deliberate-error fixtures, on the ACCEPTED
    attempt of the chosen execution shape);
    ``attempts_overrides`` maps case_id -> exact attempt list (for
    runtime-failure / mixed fixtures).
    """
    if execution not in {"primary_ok", "fallback"}:
        raise ValueError(f"unknown execution shape {execution!r}")
    decisions = decisions or {}
    attempts_overrides = attempts_overrides or {}
    records: list[dict[str, Any]] = []
    for case in sorted(corpus.cases, key=lambda c: c.case_id):
        if case.case_class == "CONTRACT_NEGATIVE":
            continue
        if case.case_id in attempts_overrides:
            attempts = attempts_overrides[case.case_id]
        else:
            if case.case_id not in decisions and not include_all:
                continue
            decision = decisions.get(
                case.case_id, case.expected["decision"]
            )
            raw = (
                default_response_for(case)
                if decision == case.expected["decision"]
                else make_response(decision)
            )
            if execution == "primary_ok":
                attempts = [
                    {
                        "role": "PRIMARY",
                        "provider": PRIMARY_ROUTE[0],
                        "model": PRIMARY_ROUTE[1],
                        "status": "OK",
                        "raw_output": raw,
                    }
                ]
            else:
                attempts = [
                    {
                        "role": "PRIMARY",
                        "provider": PRIMARY_ROUTE[0],
                        "model": PRIMARY_ROUTE[1],
                        "status": "TIMEOUT",
                        "raw_output": None,
                    },
                    {
                        "role": "FALLBACK",
                        "provider": FALLBACK_ROUTE[0],
                        "model": FALLBACK_ROUTE[1],
                        "status": "OK",
                        "raw_output": raw,
                    },
                ]
        records.append(
            {
                "case_id": case.case_id,
                "attempts": attempts,
                "fallback_used": len(attempts) == 2,
                "fallback_reason": (
                    _fallback_reason_for(attempts) if len(attempts) == 2 else None
                ),
            }
        )
    doc = {
        "capture_schema_version": 1,
        "corpus_id": corpus.corpus_id,
        "corpus_version": corpus.corpus_version,
        "corpus_digest": corpus.corpus_digest,
        "semantic_contract": "V2",
        "prompt_version": "2.0",
        "capture_run_id": capture_run_id,
        "captured_at": captured_at,
        "captured_by": "Q3-A test fixture (not a model response)",
        "notes": provenance_note,
        "records": records,
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(doc, indent=1, sort_keys=True), encoding="utf-8")
    return path


def _fallback_reason_for(attempts: list[dict[str, Any]]) -> str:
    from product_intelligence.evaluation.semantic_v2.capture import (
        CAPTURE_STATUS_TO_FALLBACK_REASON,
    )

    return CAPTURE_STATUS_TO_FALLBACK_REASON[attempts[0]["status"]]


def write_approved_policy(
    tmp_path: Path,
    corpus: CorpusBundle,
    thresholds: dict[str, float] | None = None,
) -> Path:
    """A TEST-SCOPE approved policy (proves the decision mechanism; it
    is NOT a production acceptance threshold - the shipped policy
    artifact stays DRAFT)."""
    thresholds = thresholds or {
        "match_precision_min": 0.9,
        "match_recall_min": 0.8,
        "valid_structured_response_rate_min": 0.9,
        "eligible_coverage_min": 1.0,
    }
    doc = {
        "policy_schema_version": 1,
        "policy_id": "PI-SEMANTIC-V2-QUALIFICATION-POLICY",
        "policy_version": "test-approved-1",
        "status": "APPROVED",
        "approval": {
            "approved": True,
            "approved_by": "Q3-A TEST APPROVER (test scope only)",
            "approved_utc": "2026-10-08T00:00:00Z",
        },
        "applicability": {
            "corpus_id": corpus.corpus_id,
            "corpus_version": corpus.corpus_version,
        },
        "thresholds": thresholds,
        "rationale": "test-scope approved policy for decision-mechanism tests",
    }
    path = tmp_path / "test_policy.json"
    path.write_text(json.dumps(doc, indent=1, sort_keys=True), encoding="utf-8")
    return path


def primary_route() -> tuple[str, str]:
    return PRIMARY_ROUTE


def fallback_route() -> tuple[str, str]:
    return FALLBACK_ROUTE
