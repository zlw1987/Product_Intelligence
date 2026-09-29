"""CLI for semantic PRIMARY promotion-regression evaluation
(PRODUCT-INTEL.SEMANTIC.PROMOTION-REGRESSION).

EVALUATION-ONLY. This CLI never touches the production SemanticRuntime,
never changes the production route, and never declares a model winner.

Usage examples:
    # List the promotion-regression corpus
    python -m product_intelligence.evaluation.semantic.promotion_regression_cli list-cases

    # Live run: production primary baseline (amax/nemotron-3-super)
    python -m product_intelligence.evaluation.semantic.promotion_regression_cli run --provider amax --model nemotron-3-super

    # Live run: challenger (amax/qwen3.8-27b)
    python -m product_intelligence.evaluation.semantic.promotion_regression_cli run --provider amax --model qwen3.8-27b

    # Compare two completed run directories (primary baseline, challenger)
    python -m product_intelligence.evaluation.semantic.promotion_regression_cli compare <primary_run_dir> <challenger_run_dir>

Exit codes:
    0 - success (run: promotion gate PASS; compare: comparison produced and
        both promotion gates PASS)
    1 - operational error (bad arguments, missing configuration, corrupt
        artifacts)
    2 - promotion gate FAIL (run) or provenance-incompatible / gate FAIL
        (compare)

Live runs require the provider environment configuration
(PI_SEMANTIC_AMAX_BASE_URL / PI_SEMANTIC_AMAX_API_KEY), exactly as the
production runtime and the qualification CLI use it. No environment
variable of the harness exists to select a model in production: the model
is a CLI argument validated against the harness's explicit authorization
list.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from product_intelligence.evaluation.semantic.promotion_regression import (
    PROMOTION_REGRESSION_AUTHORIZED_MODELS,
    PromotionRegressionComparisonError,
    PromotionRegressionCorpusError,
    PromotionRegressionError,
    PromotionRegressionModelAuthorizationError,
    build_live_transport,
    compare_promotion_regression_runs,
    get_authorized_model_spec,
    load_promotion_regression_corpus,
    load_run,
    run_promotion_regression,
    save_comparison,
    save_run,
)


def _print_gate_summary(run) -> None:
    for gate in run.gates:
        status = "PASS" if gate.passed else "FAIL"
        line = f"  {gate.name}: {status}"
        if gate.detail:
            line += f" - {gate.detail}"
        print(line)


def _cmd_list_cases(args: argparse.Namespace) -> int:
    try:
        corpus = (
            load_promotion_regression_corpus(args.corpus)
            if args.corpus
            else load_promotion_regression_corpus()
        )
    except PromotionRegressionCorpusError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    print(f"Promotion-regression corpus v{corpus.corpus_version} "
          f"({len(corpus.cases)} cases)")
    for case in corpus.cases:
        call = "call" if case.expected_semantic_call else "no-call"
        expected = case.expected_semantic_decision or "-"
        unsafe = " UNSAFE-MATCH" if case.match_is_unsafe else ""
        print(
            f"  {case.case_id} [{case.category} {case.category_name}] "
            f"{call} expected={expected}{unsafe}"
        )
    return 0


def _cmd_run(args: argparse.Namespace) -> int:
    try:
        spec = get_authorized_model_spec(args.provider, args.model)
    except PromotionRegressionModelAuthorizationError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1

    try:
        corpus = (
            load_promotion_regression_corpus(args.corpus)
            if args.corpus
            else None
        )
        transport = build_live_transport(
            spec, request_timeout_seconds=args.request_timeout_seconds
        )
    except PromotionRegressionError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1

    run = run_promotion_regression(
        spec,
        transport,
        corpus=corpus,
        request_timeout_seconds=args.request_timeout_seconds,
    )
    run_dir = save_run(run, output_dir=args.output_dir)

    print(f"Run saved to: {run_dir}")
    print(f"Run status: {run.run_status}")
    print("Promotion gate facts:")
    _print_gate_summary(run)
    print(f"Promotion gate: {'PASS' if run.promotion_gate_passed else 'FAIL'}")
    print(
        "NOTE: this is evaluation evidence only. The production route is "
        "unchanged; no winner is declared by this run."
    )
    return 0 if run.promotion_gate_passed else 2


def _cmd_compare(args: argparse.Namespace) -> int:
    try:
        primary = load_run(Path(args.primary_run_dir))
        challenger = load_run(Path(args.challenger_run_dir))
    except (PromotionRegressionComparisonError, PromotionRegressionError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1

    try:
        comparison = compare_promotion_regression_runs(primary, challenger)
    except PromotionRegressionComparisonError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    comp_dir = save_comparison(comparison, output_dir=args.output_dir)
    print(f"Comparison saved to: {comp_dir}")
    print(
        f"Primary: {primary.spec.provider_model_id} "
        f"(promotion gate {'PASS' if primary.promotion_gate_passed else 'FAIL'})"
    )
    print(
        f"Challenger: {challenger.spec.provider_model_id} "
        f"(promotion gate {'PASS' if challenger.promotion_gate_passed else 'FAIL'})"
    )
    print(
        f"Model disagreements: {comparison.aggregates['model_disagreement_count']} | "
        f"positive authority expansion (challenger MATCH vs primary "
        f"NO_MATCH/UNCERTAIN): "
        f"{comparison.aggregates['positive_authority_expansion_count']} | "
        f"conservative challenger regression (primary MATCH vs challenger "
        f"NO_MATCH/UNCERTAIN): "
        f"{comparison.aggregates['conservative_challenger_regression_count']} | "
        f"human review required: {comparison.aggregates['human_review_required_count']}"
    )
    if comparison.human_review_case_ids:
        print("Mandatory human-review cases:")
        for cid in comparison.human_review_case_ids:
            print(f"  - {cid}")
    print(
        "NOTE: no winner is declared. Promotion remains a human-reviewed "
        "decision; the production route is unchanged."
    )
    both_pass = (
        primary.promotion_gate_passed and challenger.promotion_gate_passed
    )
    return 0 if both_pass else 2


def create_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="promotion_regression_cli",
        description=(
            "Evaluation-only promotion-regression harness for semantic "
            "PRIMARY candidates. Never changes the production route; never "
            "declares a winner."
        ),
    )
    sub = parser.add_subparsers(dest="command", required=True)

    list_p = sub.add_parser(
        "list-cases", help="List the promotion-regression corpus"
    )
    list_p.add_argument("--corpus", default=None, help="Corpus path override")
    list_p.set_defaults(func=_cmd_list_cases)

    run_p = sub.add_parser(
        "run",
        help="Live run of one authorized model against the regression corpus",
    )
    run_p.add_argument(
        "--provider",
        required=True,
        help=(
            "Provider (authorized: "
            + ", ".join(s.provider for s in PROMOTION_REGRESSION_AUTHORIZED_MODELS)
            + ")"
        ),
    )
    run_p.add_argument(
        "--model",
        required=True,
        help=(
            "Model (authorized: "
            + ", ".join(s.model for s in PROMOTION_REGRESSION_AUTHORIZED_MODELS)
            + ")"
        ),
    )
    run_p.add_argument(
        "--request-timeout-seconds",
        type=float,
        default=300.0,
        help="Transport request timeout (default: 300.0)",
    )
    run_p.add_argument(
        "--output-dir",
        default=None,
        help="Artifact output directory (default: semantic_promotion_regression_runs/)",
    )
    run_p.add_argument("--corpus", default=None, help="Corpus path override")
    run_p.set_defaults(func=_cmd_run)

    compare_p = sub.add_parser(
        "compare",
        help="Compare two completed run directories (primary, challenger)",
    )
    compare_p.add_argument("primary_run_dir")
    compare_p.add_argument("challenger_run_dir")
    compare_p.add_argument(
        "--output-dir",
        default=None,
        help="Artifact output directory (default: semantic_promotion_regression_runs/)",
    )
    compare_p.set_defaults(func=_cmd_compare)

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = create_parser()
    args = parser.parse_args(argv)
    try:
        return args.func(args)
    except PromotionRegressionError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    except json.JSONDecodeError as exc:
        print(f"error: corrupt JSON artifact: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
