"""The offline Q3-A qualification command surface.

Usage (all commands are OFFLINE - no network, no model calls):

    python -m product_intelligence.evaluation.semantic_v2.cli corpus-build \
        --out-dir evaluation/semantic_v2_qualification
    python -m product_intelligence.evaluation.semantic_v2.cli corpus-digest \
        --corpus evaluation/semantic_v2_qualification/corpus_v1.json
    python -m product_intelligence.evaluation.semantic_v2.cli corpus-manifest \
        --corpus <corpus.json> --out <manifest.json>
    python -m product_intelligence.evaluation.semantic_v2.cli evaluate \
        --corpus <corpus.json> \
        [--capture <capture.json>]... \
        --policy <policy.json> \
        --out-dir <dir> \
        --generated-utc 2026-10-08T00:00:00Z
    python -m product_intelligence.evaluation.semantic_v2.cli verify-report \
        --report <report.json> --corpus <corpus.json>

``evaluate`` with no ``--capture`` produces the explicit no-capture
baseline for BOTH pinned route candidates (every eligible case is
NOT_CAPTURED; the decision is POLICY_PENDING - never a pass). With
captures, one run is projected onto BOTH models (the primary view and
the fallback view): one report per provider/model, qualified
INDEPENDENTLY - a primary-model PASS never qualifies the fallback.

The CLI consumes the package modules; it imports no production
research/semantic surface directly (least privilege - the frozen
chain is executed only inside the allowlisted modules).
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


def _write_json(path: Path, document: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(document, indent=1, sort_keys=True, ensure_ascii=True)
        + "\n",
        encoding="utf-8",
    )


def _cmd_corpus_build(args: argparse.Namespace) -> int:
    from product_intelligence.evaluation.semantic_v2.corpus import (
        build_manifest_document,
    )
    from product_intelligence.evaluation.semantic_v2.fixtures import (
        build_corpus_document,
    )

    out_dir = Path(args.out_dir)
    corpus_doc = build_corpus_document()
    _write_json(out_dir / "corpus_v1.json", corpus_doc)
    manifest = build_manifest_document(corpus_doc)
    _write_json(out_dir / "manifest_v1.json", manifest)
    print(f"corpus digest: {corpus_doc['corpus_digest']}")
    print(f"manifest digest: {manifest['manifest_digest']}")
    print(f"cases: {len(corpus_doc['cases'])}")
    return 0


def _cmd_corpus_digest(args: argparse.Namespace) -> int:
    from product_intelligence.evaluation.semantic_v2.corpus import (
        load_corpus,
    )

    corpus = load_corpus(args.corpus)
    print(corpus.corpus_digest)
    return 0


def _cmd_corpus_manifest(args: argparse.Namespace) -> int:
    from product_intelligence.evaluation.semantic_v2.corpus import (
        build_manifest_document,
        load_corpus,
    )

    corpus = load_corpus(args.corpus)
    manifest = build_manifest_document(corpus.document)
    _write_json(Path(args.out), manifest)
    print(f"manifest digest: {manifest['manifest_digest']}")
    return 0


def _evaluate_capture_views(
    corpus,
    capture,
    policy,
    generated_utc: str,
    out_dir: Path,
) -> tuple[str, str]:
    from product_intelligence.evaluation.semantic_v2.capture import (
        FALLBACK_ROUTE,
        PRIMARY_ROUTE,
    )
    from product_intelligence.evaluation.semantic_v2.evaluator import (
        QualificationContractError,
        evaluate_for_model,
    )
    from product_intelligence.evaluation.semantic_v2.gates import (
        decide,
        evaluate_safety_gates,
    )
    from product_intelligence.evaluation.semantic_v2.policy import (
        evaluate_thresholds,
        policy_applies_to,
    )
    from product_intelligence.evaluation.semantic_v2.report import (
        build_report,
        render_markdown,
    )

    decisions = []
    for route in (PRIMARY_ROUTE, FALLBACK_ROUTE):
        stem = (
            f"{capture.capture_run_id or 'capture'}__"
            f"{route[0]}_{route[1]}"
        ).replace("/", "_").replace(" ", "_")
        try:
            result = evaluate_for_model(corpus, capture, *route)
        except QualificationContractError as exc:
            # The evaluation is VOID: still emit an explicit fail-closed
            # report so the mismatch stays visible, never silent.
            report = {
                "report_schema_version": 1,
                "report_kind": "SEMANTIC_V2_QUALIFICATION_OFFLINE",
                "generated_utc": generated_utc,
                "corpus": {
                    "corpus_id": corpus.corpus_id,
                    "corpus_version": corpus.corpus_version,
                    "corpus_digest": corpus.corpus_digest,
                },
                "model": {
                    "provider": route[0],
                    "model": route[1],
                    "route_role": "PRIMARY" if route == PRIMARY_ROUTE else "FALLBACK",
                },
                "decision": "FAIL_CLOSED",
                "decision_rationale": [f"VOID_EVALUATION:{exc}"],
                "cases": [],
                "metrics": {},
                "safety_gates": {},
                "policy": None,
                "authority": {"granted": False},
            }
            _write_json(out_dir / f"{stem}__report.json", report)
            print(f"{stem}: FAIL_CLOSED (void evaluation)")
            decisions.append("FAIL_CLOSED")
            continue

        gates = evaluate_safety_gates(result)
        threshold_evaluation = None
        if policy is not None and policy_applies_to(
            policy, corpus.corpus_id, corpus.corpus_version
        ):
            threshold_evaluation = evaluate_thresholds(
                policy, result.metrics
            )
        decision, rationale = decide(
            result, gates, policy, threshold_evaluation
        )
        report = build_report(
            result=result,
            gates=gates,
            policy=policy,
            threshold_evaluation=threshold_evaluation,
            decision=decision,
            rationale=rationale,
            corpus=corpus,
            generated_utc=generated_utc,
        )
        json_path = out_dir / f"{stem}__report.json"
        md_path = out_dir / f"{stem}__report.md"
        _write_json(json_path, report)
        md_path.write_text(render_markdown(report), encoding="utf-8")
        print(f"{stem}: {decision} ({', '.join(rationale)})")
        decisions.append(decision)
    return decisions[0], decisions[1]


def _baseline_one(
    corpus, provider: str, model: str, policy, generated_utc: str, out_dir: Path
) -> str:
    from product_intelligence.evaluation.semantic_v2.evaluator import (
        evaluate_no_capture,
    )
    from product_intelligence.evaluation.semantic_v2.gates import (
        decide,
        evaluate_safety_gates,
    )
    from product_intelligence.evaluation.semantic_v2.policy import (
        evaluate_thresholds,
        policy_applies_to,
    )
    from product_intelligence.evaluation.semantic_v2.report import (
        build_report,
        render_markdown,
    )

    result = evaluate_no_capture(corpus, provider, model)
    gates = evaluate_safety_gates(result)
    threshold_evaluation = None
    if policy is not None and policy_applies_to(
        policy, corpus.corpus_id, corpus.corpus_version
    ):
        threshold_evaluation = evaluate_thresholds(policy, result.metrics)
    decision, rationale = decide(result, gates, policy, threshold_evaluation)
    report = build_report(
        result=result,
        gates=gates,
        policy=policy,
        threshold_evaluation=threshold_evaluation,
        decision=decision,
        rationale=rationale,
        corpus=corpus,
        generated_utc=generated_utc,
    )
    stem = f"no-capture_{provider}_{model}".replace("/", "_")
    json_path = out_dir / f"{stem}__report.json"
    md_path = out_dir / f"{stem}__report.md"
    _write_json(json_path, report)
    md_path.write_text(render_markdown(report), encoding="utf-8")
    print(f"{stem}: {decision} ({', '.join(rationale)})")
    return decision


def _cmd_evaluate(args: argparse.Namespace) -> int:
    from product_intelligence.evaluation.semantic_v2.capture import (
        FALLBACK_ROUTE,
        PRIMARY_ROUTE,
        load_capture,
    )
    from product_intelligence.evaluation.semantic_v2.corpus import (
        load_corpus,
    )
    from product_intelligence.evaluation.semantic_v2.policy import (
        load_policy,
    )

    corpus = load_corpus(args.corpus)
    policy = load_policy(args.policy) if args.policy else None
    out_dir = Path(args.out_dir)
    if args.capture:
        for capture_path in args.capture:
            capture = load_capture(capture_path)
            _evaluate_capture_views(corpus, capture, policy, args.generated_utc, out_dir)
        return 0
    # Explicit no-capture baseline for both pinned route candidates:
    # qualification is impossible offline without captured responses,
    # and the baseline says exactly that (fail closed, never a pass).
    _baseline_one(
        corpus, PRIMARY_ROUTE[0], PRIMARY_ROUTE[1],
        policy, args.generated_utc, out_dir,
    )
    _baseline_one(
        corpus, FALLBACK_ROUTE[0], FALLBACK_ROUTE[1],
        policy, args.generated_utc, out_dir,
    )
    return 0


def _cmd_verify_report(args: argparse.Namespace) -> int:
    import json as _json

    from product_intelligence.evaluation.semantic_v2.corpus import (
        load_corpus,
    )
    from product_intelligence.evaluation.semantic_v2.report import (
        ReportError,
        verify_report,
    )

    report = _json.loads(Path(args.report).read_text(encoding="utf-8"))
    corpus = load_corpus(args.corpus)
    try:
        verify_report(report, corpus)
    except ReportError as exc:
        print(f"REPORT VERIFICATION FAILED: {exc}", file=sys.stderr)
        return 1
    print("report verifies against the presented corpus")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python -m product_intelligence.evaluation.semantic_v2.cli",
        description="Q3-A offline Semantic V2 qualification (no network, no AI)",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    p_build = sub.add_parser("corpus-build", help="regenerate the corpus + manifest from the auditable source")
    p_build.add_argument("--out-dir", required=True)
    p_build.set_defaults(func=_cmd_corpus_build)

    p_digest = sub.add_parser("corpus-digest", help="print the verified corpus digest")
    p_digest.add_argument("--corpus", required=True)
    p_digest.set_defaults(func=_cmd_corpus_digest)

    p_manifest = sub.add_parser("corpus-manifest", help="write the reproducible manifest")
    p_manifest.add_argument("--corpus", required=True)
    p_manifest.add_argument("--out", required=True)
    p_manifest.set_defaults(func=_cmd_corpus_manifest)

    p_eval = sub.add_parser("evaluate", help="offline evaluation + reports")
    p_eval.add_argument("--corpus", required=True)
    p_eval.add_argument("--capture", action="append", default=None)
    p_eval.add_argument("--policy", default=None)
    p_eval.add_argument("--out-dir", required=True)
    p_eval.add_argument("--generated-utc", required=True)
    p_eval.set_defaults(func=_cmd_evaluate)

    p_verify = sub.add_parser("verify-report", help="verify a historical report against a corpus")
    p_verify.add_argument("--report", required=True)
    p_verify.add_argument("--corpus", required=True)
    p_verify.set_defaults(func=_cmd_verify_report)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        return args.func(args)
    except Exception as exc:  # bounded CLI surface: one clear failure
        print(f"error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
