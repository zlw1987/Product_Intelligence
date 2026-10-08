"""The reproducible offline qualification report (Q3-A).

The report binds to the EXACT identity of everything it evaluates:

* the corpus (id / version / digest) — historical results stay
  associated with their corpus even if the corpus is later revised
  (a revised corpus is a different digest; ``verify_report`` then
  fails against the old report);
* the frozen production contract (semantic contract V2, prompt 2.0,
  input/output schema 1, authority contract SEMANTIC_AUTHORITY_V2_S2A_FU2);
* the frozen system prompt (by digest of the REAL prompt text — the
  harness renders with ``build_semantic_prompt_v2``, it never carries
  a copy);
* the runtime configuration identity (pinned routes, temperature,
  max_tokens, the V2_AUTHORITY_QUALIFIED marker);
* the capture artifact (run id, instant, model).

``generated_utc`` is the only non-deterministic field; the report
digest is computed over everything else, so re-running the same
offline evaluation reproduces the same report digest.

The report grants NO authority: the V2 qualification marker is
recorded as-is (False in S2-C) and the report's decision vocabulary
contains no authority grant.
"""

from __future__ import annotations

from typing import Any, Final

from product_intelligence.research import (
    FALLBACK_MODEL_V2,
    FALLBACK_PROVIDER_V2,
    PRIMARY_MODEL_V2,
    PRIMARY_PROVIDER_V2,
    PROMPT_VERSION_V2,
    SEMANTIC_CONTRACT_VERSION_V2,
    SEMANTIC_INPUT_SCHEMA_VERSION_V2,
    SEMANTIC_OUTPUT_SCHEMA_VERSION_V2,
    AUTHORITY_CONTRACT_VERSION_V2,
    V2_AUTHORITY_QUALIFIED,
)
from product_intelligence.semantic.contract_v2 import (
    SEMANTIC_PROMPT_VERSION_V2,
    SYSTEM_PROMPT_V2,
)
from product_intelligence.semantic.runtime_v2 import (
    SEMANTIC_MAX_TOKENS_V2,
    SEMANTIC_TEMPERATURE_V2,
)
from product_intelligence.evaluation.semantic_v2.canonical import (
    assert_json_native,
    canonical_sha256,
)
from product_intelligence.evaluation.semantic_v2.capture import (
    CAPTURE_MODE,
    CAPTURE_SCHEMA_VERSION,
)
from product_intelligence.evaluation.semantic_v2.corpus import (
    CONTRACT_NEGATIVE_CASE_CLASS,
    CorpusBundle,
)
from product_intelligence.evaluation.semantic_v2.direct_capture import (
    DIRECT_CAPTURE_MODE,
    DIRECT_CAPTURE_SCHEMA_VERSION,
    DirectCaptureDocument,
)
from product_intelligence.evaluation.semantic_v2.evaluator import (
    EvaluationResult,
)
from product_intelligence.evaluation.semantic_v2.gates import (
    GateResult,
)
from product_intelligence.evaluation.semantic_v2.policy import (
    PolicyDocument,
)

__all__ = [
    "DIRECT_REPORT_KIND",
    "PRODUCTION_REPORT_KIND",
    "REPORT_SCHEMA_VERSION",
    "build_direct_report",
    "build_report",
    "render_markdown",
    "verify_direct_report",
    "verify_report",
    "ReportError",
]

REPORT_SCHEMA_VERSION: Final[int] = 1

#: The two report kinds (one per capture mode; the two are never
#: reinterpreted across modes - each verifier refuses the other kind).
PRODUCTION_REPORT_KIND: Final[str] = "SEMANTIC_V2_QUALIFICATION_OFFLINE"
DIRECT_REPORT_KIND: Final[str] = (
    "SEMANTIC_V2_DIRECT_MODEL_QUALIFICATION_OFFLINE"
)


class ReportError(Exception):
    """Bounded report failure (verification)."""


def _contract_section() -> dict[str, Any]:
    return {
        "semantic_contract_version": SEMANTIC_CONTRACT_VERSION_V2,
        "prompt_version": PROMPT_VERSION_V2,
        "input_schema_version": SEMANTIC_INPUT_SCHEMA_VERSION_V2,
        "output_schema_version": SEMANTIC_OUTPUT_SCHEMA_VERSION_V2,
        "authority_contract_version": AUTHORITY_CONTRACT_VERSION_V2,
        "semantic_contract_binding": [
            SEMANTIC_CONTRACT_VERSION_V2,
            PROMPT_VERSION_V2,
            SEMANTIC_INPUT_SCHEMA_VERSION_V2,
            SEMANTIC_OUTPUT_SCHEMA_VERSION_V2,
            AUTHORITY_CONTRACT_VERSION_V2,
        ],
        "system_prompt_digest": _system_prompt_digest(),
        "runtime_config_identity": {
            "primary": {
                "provider": PRIMARY_PROVIDER_V2,
                "model": PRIMARY_MODEL_V2,
            },
            "fallback": {
                "provider": FALLBACK_PROVIDER_V2,
                "model": FALLBACK_MODEL_V2,
            },
            "temperature": repr(SEMANTIC_TEMPERATURE_V2),
            "max_tokens": SEMANTIC_MAX_TOKENS_V2,
            "v2_authority_qualified": V2_AUTHORITY_QUALIFIED,
        },
    }


def _system_prompt_digest() -> str:
    """The digest of the REAL frozen system prompt text."""
    if SEMANTIC_PROMPT_VERSION_V2 != PROMPT_VERSION_V2:
        # Drift between the prompt module and the adapter mirror: the
        # report refuses to bind to an inconsistent contract.
        raise ReportError(
            "the frozen prompt version drifted from the adapter mirror; "
            "the report cannot bind to the contract"
        )
    return canonical_sha256({"text": SYSTEM_PROMPT_V2})


def _corpus_input_digest(corpus: CorpusBundle) -> str:
    """The digest over the exact semantic case inputs (case id + the
    sealed case digest covers the payload)."""
    entries = [
        {"case_id": case.case_id, "case_digest": case.case_digest}
        for case in sorted(
            corpus.semantic_cases, key=lambda c: c.case_id
        )
    ]
    return canonical_sha256(entries)


def _corpus_section(corpus: CorpusBundle, counts: dict[str, Any]) -> dict[str, Any]:
    return {
        "corpus_id": corpus.corpus_id,
        "corpus_version": corpus.corpus_version,
        "corpus_schema_version": 1,
        "corpus_digest": corpus.corpus_digest,
        "total_cases": counts["total_cases"],
        "authoritative_cases": counts["authoritative_cases"],
        "ambiguous_cases": counts["ambiguous_cases"],
        "contract_negative_cases": counts["contract_negative_cases"],
        "corpus_input_digest": _corpus_input_digest(corpus),
    }


def _policy_section(
    policy: PolicyDocument | None,
    threshold_evaluation: dict[str, Any] | None,
) -> dict[str, Any] | None:
    return (
        {
            "policy_id": policy.policy_id,
            "policy_version": policy.policy_version,
            "status": policy.status,
            "approved": policy.approved,
            "approved_by": policy.approved_by,
            "approved_utc": policy.approved_utc,
            "thresholds": {
                k: f"{v:.6f}" for k, v in policy.thresholds.items()
            },
            "threshold_evaluation": threshold_evaluation,
            "note": (
                "DRAFT proposal - not a finalized production "
                "acceptance threshold; qualification requires an "
                "approved policy"
                if policy.status == "DRAFT"
                else "approved qualification policy"
            ),
        }
        if policy is not None
        else None
    )


def _authority_section() -> dict[str, Any]:
    return {
        "granted": False,
        "v2_authority_qualified": V2_AUTHORITY_QUALIFIED,
        "note": (
            "this report is evaluation evidence only; it grants no "
            "pricing authority, no tier promotion, and no human-"
            "review behavior change"
        ),
    }


def _report_digest_fields(
    report: dict[str, Any],
) -> dict[str, Any]:
    return {k: v for k, v in report.items() if k not in ("generated_utc",)}


def build_report(
    result: EvaluationResult,
    gates: dict[str, GateResult],
    policy: PolicyDocument | None,
    threshold_evaluation: dict[str, Any] | None,
    decision: str,
    rationale: tuple[str, ...],
    corpus: CorpusBundle,
    generated_utc: str,
) -> dict[str, Any]:
    """Assemble the machine-readable report (deterministic apart from
    ``generated_utc``)."""
    counts = result.metrics["counts"]
    report: dict[str, Any] = {
        "report_schema_version": REPORT_SCHEMA_VERSION,
        "report_kind": PRODUCTION_REPORT_KIND,
        "generated_utc": generated_utc,
        "corpus": _corpus_section(corpus, counts),
        "contract": _contract_section(),
        "model": {
            "provider": result.provider,
            "model": result.model,
            "route_role": result.route_role,
        },
        "capture": (
            {
                "capture_mode": CAPTURE_MODE,
                "capture_schema_version": CAPTURE_SCHEMA_VERSION,
                "capture_run_id": result.capture_run_id,
                "captured_at": result.captured_at,
                "captured_by": result.captured_by,
                "notes": result.capture_notes,
            }
            if result.capture_run_id is not None
            else None
        ),
        "cases": [outcome.to_report_dict() for outcome in result.outcomes],
        "metrics": result.metrics,
        "safety_gates": {
            name: gates[name].to_report_dict() for name in gates
        },
        "policy": _policy_section(policy, threshold_evaluation),
        "decision": decision,
        "decision_rationale": list(rationale),
        "authority": _authority_section(),
    }
    assert_json_native(report, "report")
    report["report_digest"] = canonical_sha256(
        _report_digest_fields(report)
    )
    return report


def verify_report(
    report: dict[str, Any], corpus: CorpusBundle
) -> None:
    """Verify one historical PRODUCTION_ROUTE report against one corpus.

    Fails closed (``ReportError``) when the report is not a
    production-route qualification report (cross-mode kind is refused),
    when it was produced against a different corpus digest / contract
    binding, or when any per-case expected-decision snapshot no longer
    matches the corpus (a label revision since the report was
    produced). This is what keeps historical results associated with
    their original identity and makes silent label mutation after
    evaluation detectable.
    """
    if report.get("report_schema_version") != REPORT_SCHEMA_VERSION:
        raise ReportError("unknown report schema version")
    if report.get("report_kind") != PRODUCTION_REPORT_KIND:
        raise ReportError(
            "report kind is not the production-route qualification "
            "report; cross-mode interpretation is refused (fail closed)"
        )
    _verify_report_binding(report, corpus)


def verify_direct_report(
    report: dict[str, Any], corpus: CorpusBundle
) -> None:
    """Verify one historical DIRECT_MODEL_QUALIFICATION report against
    one corpus (the direct-mode counterpart of ``verify_report``;
    refuses the other mode's reports).
    """
    if report.get("report_schema_version") != REPORT_SCHEMA_VERSION:
        raise ReportError("unknown report schema version")
    if report.get("report_kind") != DIRECT_REPORT_KIND:
        raise ReportError(
            "report kind is not the direct-model qualification report; "
            "cross-mode interpretation is refused (fail closed)"
        )
    if report.get("capture_mode") != DIRECT_CAPTURE_MODE:
        raise ReportError("report capture mode mismatch")
    _verify_report_binding(report, corpus)


def _verify_report_binding(
    report: dict[str, Any], corpus: CorpusBundle
) -> None:
    """The shared corpus / contract / per-case / digest binding checks
    (mode-neutral; the public verifiers enforce the kind first)."""
    bound_corpus = report.get("corpus", {})
    if bound_corpus.get("corpus_digest") != corpus.corpus_digest:
        raise ReportError(
            "report is bound to corpus digest "
            f"{bound_corpus.get('corpus_digest')!r}; the presented corpus "
            f"is {corpus.corpus_digest!r} (the corpus changed after this "
            "report was produced - the historical result stays with its "
            "original corpus)"
        )
    if bound_corpus.get("corpus_version") != corpus.corpus_version:
        raise ReportError("report corpus version mismatch")
    contract = report.get("contract", {})
    if contract.get("semantic_contract_binding") != [
        "V2",
        "2.0",
        1,
        1,
        "SEMANTIC_AUTHORITY_V2_S2A_FU2",
    ]:
        raise ReportError("report contract binding mismatch")
    # Per-case label snapshot: every case in the report must still carry
    # the same expected decision / acceptable set in the corpus.
    by_id = {case.case_id: case for case in corpus.cases}
    for entry in report.get("cases", ()):
        case = by_id.get(entry.get("case_id"))
        if case is None:
            raise ReportError(
                f"report case {entry.get('case_id')!r} is not in the "
                "presented corpus"
            )
        if entry.get("expected_decision") != case.expected.get("decision"):
            raise ReportError(
                f"report case {entry['case_id']} expected decision "
                f"{entry.get('expected_decision')!r} no longer matches "
                f"the corpus label {case.expected.get('decision')!r}"
            )
        acceptable = entry.get("acceptable_decisions")
        corpus_acceptable = case.expected.get("acceptable_decisions")
        if acceptable != corpus_acceptable:
            raise ReportError(
                f"report case {entry['case_id']} acceptable decisions "
                "no longer match the corpus label"
            )
    digested = {
        k: v
        for k, v in report.items()
        if k not in ("generated_utc", "report_digest")
    }
    if canonical_sha256(digested) != report.get("report_digest"):
        raise ReportError("report digest does not verify (tampered)")


def build_direct_report(
    result: EvaluationResult,
    gates: dict[str, GateResult],
    policy: PolicyDocument | None,
    threshold_evaluation: dict[str, Any] | None,
    decision: str,
    rationale: tuple[str, ...],
    corpus: CorpusBundle,
    direct_capture: DirectCaptureDocument,
    generated_utc: str,
) -> dict[str, Any]:
    """Assemble the machine-readable DIRECT_MODEL_QUALIFICATION report
    (deterministic apart from ``generated_utc``). The mode, the capture
    schema version, the single target model identity, and the direct
    coverage facts are identified explicitly; the report is never
    combined with a production-route report.
    """
    if result.capture_mode != DIRECT_CAPTURE_MODE:
        raise ReportError(
            "build_direct_report requires a direct-model evaluation "
            "result; production-route results are reported by "
            "build_report (the two modes are never combined)"
        )
    counts = result.metrics["counts"]
    semantic_outcomes = [
        o for o in result.outcomes
        if o.case_class != CONTRACT_NEGATIVE_CASE_CLASS
    ]
    coverage = {
        "eligible_semantic_cases": counts["eligible_semantic_cases"],
        "evaluated_cases": counts["evaluated_cases"],
        "not_captured": counts["not_captured"],
        "runtime_failure": counts["runtime_failure_count"],
        "capture_integrity_failure": counts["capture_integrity_failures"],
        "complete": (
            counts["evaluated_cases"] == counts["eligible_semantic_cases"]
        ),
        "missing_case_ids": sorted(
            o.case_id for o in semantic_outcomes if o.state == "NOT_CAPTURED"
        ),
        "runtime_failure_case_ids": sorted(
            o.case_id
            for o in semantic_outcomes
            if o.state == "RUNTIME_FAILURE"
        ),
        "invalid_response_case_ids": sorted(
            o.case_id
            for o in semantic_outcomes
            if o.state == "CAPTURE_INTEGRITY_FAILURE"
        ),
    }
    report: dict[str, Any] = {
        "report_schema_version": REPORT_SCHEMA_VERSION,
        "report_kind": DIRECT_REPORT_KIND,
        "capture_mode": DIRECT_CAPTURE_MODE,
        "capture_schema_version": DIRECT_CAPTURE_SCHEMA_VERSION,
        "generated_utc": generated_utc,
        "corpus": _corpus_section(corpus, counts),
        "contract": _contract_section(),
        "model": {
            "provider": result.provider,
            "model": result.model,
            "route_role": result.route_role,
            "target_provider": direct_capture.target_provider,
            "target_model": direct_capture.target_model,
        },
        "capture": {
            "capture_mode": DIRECT_CAPTURE_MODE,
            "capture_schema_version": direct_capture.direct_capture_schema_version,
            "capture_run_id": direct_capture.capture_run_id,
            "captured_at": direct_capture.captured_at,
            "captured_by": direct_capture.captured_by,
            "notes": direct_capture.notes,
        },
        "coverage": coverage,
        "cases": [outcome.to_report_dict() for outcome in result.outcomes],
        "metrics": result.metrics,
        "safety_gates": {
            name: gates[name].to_report_dict() for name in gates
        },
        "policy": _policy_section(policy, threshold_evaluation),
        "decision": decision,
        "decision_rationale": list(rationale),
        "authority": _authority_section(),
    }
    assert_json_native(report, "report")
    report["report_digest"] = canonical_sha256(
        _report_digest_fields(report)
    )
    return report


# ---------------------------------------------------------------------------
# Human-readable rendering
# ---------------------------------------------------------------------------


def render_markdown(report: dict[str, Any]) -> str:
    """The human-readable report (deterministic over the same content).
    Production-route and direct-model reports are rendered with their
    explicit mode identification; the production text is unchanged.
    """
    is_direct = report.get("capture_mode") == DIRECT_CAPTURE_MODE
    lines: list[str] = []
    if is_direct:
        lines.append(
            "# Semantic V2 Direct-Model Qualification Report "
            "(Q3-A-FU1 offline)"
        )
    else:
        lines.append("# Semantic V2 Qualification Report (Q3-A offline)")
    lines.append("")
    model = report["model"]
    lines.append(
        f"- **Model under qualification:** `{model['provider']}/"
        f"{model['model']}` (route role: {model['route_role']})"
    )
    if is_direct:
        lines.append(
            f"- **Capture mode:** `{report['capture_mode']}` "
            f"(schema v{report['capture_schema_version']}) - "
            "independent direct-model capture; no production routing, "
            "no fallback projection, no production execution authority"
        )
    corpus = report["corpus"]
    lines.append(
        f"- **Corpus:** `{corpus['corpus_id']}` v{corpus['corpus_version']} "
        f"(digest `{corpus['corpus_digest']}`)"
    )
    contract = report["contract"]
    lines.append(
        "- **Frozen contract:** semantic "
        f"`{contract['semantic_contract_version']}`, prompt "
        f"`{contract['prompt_version']}`, input schema "
        f"`{contract['input_schema_version']}`, output schema "
        f"`{contract['output_schema_version']}`, authority "
        f"`{contract['authority_contract_version']}`; system prompt "
        f"digest `{contract['system_prompt_digest']}`"
    )
    lines.append(
        f"- **Decision:** `{report['decision']}` — "
        + ", ".join(report["decision_rationale"])
    )
    lines.append("")
    lines.append("## Safety gates (mandatory, fail-closed)")
    lines.append("")
    lines.append("| Gate | Passed | Failing cases |")
    lines.append("| --- | --- | --- |")
    for name, gate in report["safety_gates"].items():
        lines.append(
            f"| {name} | {'PASS' if gate['passed'] else '**FAIL**'} "
            f"| {', '.join(gate['failing_case_ids']) or '-'} |"
        )
    lines.append("")
    lines.append("## Metrics")
    lines.append("")
    m = report["metrics"]
    c = m["counts"]
    if is_direct:
        cov = report["coverage"]
        lines.append(
            f"- Coverage (direct-model denominator): "
            f"{cov['evaluated_cases']}/{cov['eligible_semantic_cases']} "
            f"evaluated; not captured {cov['not_captured']}; runtime "
            f"failures {cov['runtime_failure']}; invalid responses "
            f"{cov['capture_integrity_failure']}; complete: "
            f"{cov['complete']}"
        )
        if cov["missing_case_ids"]:
            lines.append(
                "  - missing: " + ", ".join(cov["missing_case_ids"])
            )
        if cov["runtime_failure_case_ids"]:
            lines.append(
                "  - runtime failures: "
                + ", ".join(cov["runtime_failure_case_ids"])
            )
        if cov["invalid_response_case_ids"]:
            lines.append(
                "  - invalid responses: "
                + ", ".join(cov["invalid_response_case_ids"])
            )
    lines.append(
        f"- Total cases: {c['total_cases']} "
        f"(authoritative {c['authoritative_cases']}, "
        f"ambiguous {c['ambiguous_cases']}, "
        f"contract-negative {c['contract_negative_cases']})"
    )
    lines.append(
        f"- Evaluated: {c['evaluated_cases']}; not captured: "
        f"{c['not_captured']}; runtime failures: "
        f"{c['runtime_failure_count']} "
        f"({c['runtime_failures_by_status'] or 'none'}); capture "
        f"integrity failures: {c['capture_integrity_failures']}; "
        f"contract violations: {c['contract_violations']}"
    )

    def fmt(entry: dict[str, Any], label: str) -> str:
        if entry["status"] == "unavailable":
            return f"- {label}: **unavailable** (denominator 0)"
        return f"- {label}: {entry['value']} ({entry['numerator']}/{entry['denominator']})"

    lines.append(fmt(m["valid_structured_response_rate"], "Valid structured response rate"))
    lines.append(fmt(m["match_precision"], "MATCH precision (authoritative)"))
    lines.append(fmt(m["match_recall"], "MATCH recall (authoritative)"))
    lines.append(fmt(m["no_match_accuracy"], "NO_MATCH accuracy (authoritative)"))
    lines.append(fmt(m["uncertain_rate"], "UNCERTAIN rate (authoritative)"))
    lines.append(f"- False MATCH: {m['false_match_count']}")
    if m["false_match_examples"]:
        lines.append("  - " + "; ".join(
            f"{e['case_id']} (expected {e['expected']}, severity {e['severity']})"
            for e in m["false_match_examples"]
        ))
    lines.append(f"- False NO_MATCH: {m['false_no_match_count']}")
    lines.append(
        f"- HARD_CONFLICT false MATCH: {m['hard_conflict_false_match_count']}"
    )
    lines.append(
        f"- Packaging/bundle false MATCH: {m['packaging_false_match_count']}"
    )
    lines.append(
        f"- Accessory/product-role false MATCH: {m['accessory_false_match_count']}"
    )
    lines.append(
        f"- Near-miss false MATCH: {m['near_miss_false_match_count']}"
    )
    lines.append(
        f"- Sales-unit-safety false MATCH: {m['sales_unit_safety_false_match_count']}"
    )
    lines.append(
        f"- Severity counts: {m['severity_counts']} "
        f"(model confidence never overrides the independent label)"
    )
    amb = m["ambiguous"]
    lines.append(
        f"- Ambiguous cases (visible, excluded from hard accuracy): "
        f"{amb['defensible']} defensible / {amb['outside_defensible']} "
        "outside the defensible set of "
        f"{c['ambiguous_cases']} total"
    )
    lines.append("")
    lines.append("### Performance by substate")
    lines.append("")
    lines.append("| Substate | Total | Evaluated | Correct | False MATCH | False NO_MATCH | Runtime failure | Not captured | Not invoked |")
    lines.append("| --- | --- | --- | --- | --- | --- | --- | --- | --- |")
    for substate, row in sorted(m["by_substate"].items()):
        lines.append(
            f"| {substate} | {row['total']} | {row['evaluated']} "
            f"| {row['correct']} | {row['false_match']} "
            f"| {row['false_no_match']} | {row['runtime_failure']} "
            f"| {row['not_captured']} | {row['not_invoked']} |"
        )
    lines.append("")
    lines.append("### Performance by category")
    lines.append("")
    lines.append("| Category | Total | Evaluated | Correct | False MATCH | False NO_MATCH | Runtime failure | Not captured | Not invoked |")
    lines.append("| --- | --- | --- | --- | --- | --- | --- | --- | --- |")
    for category, row in sorted(m["by_category"].items()):
        lines.append(
            f"| {category} | {row['total']} | {row['evaluated']} "
            f"| {row['correct']} | {row['false_match']} "
            f"| {row['false_no_match']} | {row['runtime_failure']} "
            f"| {row['not_captured']} | {row['not_invoked']} |"
        )
    lines.append("")
    if report["policy"] is not None:
        p = report["policy"]
        lines.append("## Qualification policy")
        lines.append("")
        lines.append(f"- Policy: `{p['policy_id']}` v{p['policy_version']} — **{p['status']}**")
        lines.append(f"- {p['note']}")
        for name, entry in p["threshold_evaluation"].items():
            value = "unavailable" if entry["value"] is None else entry["value"]
            met = {True: "met", False: "NOT met", None: "indeterminate"}[entry["met"]]
            lines.append(f"- {name}: bound >= {entry['bound']}, value {value} — {met}")
        lines.append("")
    lines.append("## Authority")
    lines.append("")
    authority = report["authority"]
    lines.append(
        f"- Authority granted: **{authority['granted']}**; "
        f"V2_AUTHORITY_QUALIFIED marker: {authority['v2_authority_qualified']}"
    )
    lines.append(f"- {authority['note']}")
    lines.append("")
    lines.append(
        f"- Report digest: `{report['report_digest']}` "
        f"(generated {report['generated_utc']})"
    )
    return "\n".join(lines) + "\n"
