"""Shared helpers for the Q3-A-FU1 direct-model qualification tests.

Every direct capture built here is an explicit TEST FIXTURE (declared
in the artifact's provenance): it is not a model response and is never
treated as one. The helpers exercise the strict DIRECT_MODEL_
QUALIFICATION capture contract against the committed corpus.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from tests.evaluation.semantic_v2._q3a_helpers import (
    default_response_for,
    make_response,
)
from product_intelligence.evaluation.semantic_v2.capture import (
    FALLBACK_ROUTE,
    PRIMARY_ROUTE,
)
from product_intelligence.evaluation.semantic_v2.direct_capture import (
    DIRECT_CAPTURE_MODE,
    DIRECT_CAPTURE_SCHEMA_VERSION,
)

#: The frozen semantic contract / prompt identity (the same literals the
#: Q3-A helper writes; drift-pinned against the research exports by the
#: Q3-A binding tests).
SEMANTIC_CONTRACT = "V2"
PROMPT_VERSION = "2.0"


def write_direct_capture(
    path: Path,
    corpus: Any,
    *,
    target: tuple[str, str] | None = None,
    decisions: dict[str, str] | None = None,
    failures: dict[str, str] | None = None,
    missing: tuple[str, ...] = (),
    invalid: dict[str, str] | None = None,
    raw_overrides: dict[str, str] | None = None,
    capture_run_id: str = "Q3A-FU1-TEST-FIXTURE",
    captured_at: str = "2026-10-08T12:00:00Z",
    captured_by: str = "Q3-A-FU1 test fixture (not a model response)",
    notes: str = "Q3-A-FU1 test fixture: declared responses, not model output",
) -> Path:
    """Write one strict DIRECT_MODEL_QUALIFICATION capture document.

    The capture targets exactly ONE pinned provider/model (``target``;
    default: the frozen primary route) and records that model's own
    execution of every eligible semantic case - no primary-before-
    fallback requirement, no fallback attempt, no production routing.

    ``decisions`` maps case_id -> decision (deliberate-error fixtures);
    ``failures`` maps case_id -> bounded execution status (the record
    carries no raw output); ``missing`` is a tuple of case ids to omit
    from the capture (they surface as NOT_CAPTURED); ``invalid`` maps
    case_id -> raw string that fails the production parser;
    ``raw_overrides`` maps case_id -> exact raw response.
    """
    target = target or PRIMARY_ROUTE
    decisions = decisions or {}
    failures = failures or {}
    invalid = invalid or {}
    raw_overrides = raw_overrides or {}
    missing_ids = set(missing)
    records: list[dict[str, Any]] = []
    for case in sorted(corpus.cases, key=lambda c: c.case_id):
        if case.case_class == "CONTRACT_NEGATIVE":
            continue
        if case.case_id in missing_ids:
            continue
        if case.case_id in failures:
            records.append(
                {
                    "case_id": case.case_id,
                    "execution_status": failures[case.case_id],
                    "raw_output": None,
                }
            )
            continue
        if case.case_id in invalid:
            raw = invalid[case.case_id]
        elif case.case_id in raw_overrides:
            raw = raw_overrides[case.case_id]
        else:
            decision = decisions.get(case.case_id, case.expected["decision"])
            raw = (
                default_response_for(case)
                if decision == case.expected["decision"]
                else make_response(decision)
            )
        records.append(
            {
                "case_id": case.case_id,
                "execution_status": "OK",
                "raw_output": raw,
            }
        )
    doc = {
        "capture_mode": DIRECT_CAPTURE_MODE,
        "direct_capture_schema_version": DIRECT_CAPTURE_SCHEMA_VERSION,
        "target_provider": target[0],
        "target_model": target[1],
        "corpus_id": corpus.corpus_id,
        "corpus_version": corpus.corpus_version,
        "corpus_digest": corpus.corpus_digest,
        "semantic_contract": SEMANTIC_CONTRACT,
        "prompt_version": PROMPT_VERSION,
        "capture_run_id": capture_run_id,
        "captured_at": captured_at,
        "captured_by": captured_by,
        "notes": notes,
        "records": records,
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(doc, indent=1, sort_keys=True), encoding="utf-8"
    )
    return path


def direct_decide_for(
    corpus: Any,
    capture: Any,
    policy: Any,
    route: tuple[str, str] | None = None,
) -> tuple[Any, dict[str, Any], str, tuple[str, ...]]:
    """The full direct-model pipeline for one capture (evaluate ->
    gates -> thresholds -> decide), mirroring the Q3-A helper for the
    production-route view."""
    from product_intelligence.evaluation.semantic_v2.evaluator import (
        evaluate_direct_for_model,
    )
    from product_intelligence.evaluation.semantic_v2.gates import (
        decide,
        evaluate_safety_gates,
    )
    from product_intelligence.evaluation.semantic_v2.policy import (
        evaluate_thresholds,
        policy_applies_to,
    )

    route = route or (capture.target_provider, capture.target_model)
    result = evaluate_direct_for_model(corpus, capture, *route)
    gates = evaluate_safety_gates(result)
    threshold_evaluation = (
        evaluate_thresholds(policy, result.metrics)
        if policy is not None
        and policy_applies_to(policy, corpus.corpus_id, corpus.corpus_version)
        else None
    )
    decision, rationale = decide(result, gates, policy, threshold_evaluation)
    return result, gates, decision, rationale
