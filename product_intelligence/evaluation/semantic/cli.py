"""CLI for semantic model qualification (PRODUCT-INTEL.SEMANTIC.BENCHMARK).

This module provides a clean evaluation-only CLI for running semantic model
qualification benchmarks.

Usage examples:
    # List available models
    python -m product_intelligence.evaluation.semantic.cli list-models

    # Run one full qualification model
    python -m product_intelligence.evaluation.semantic.cli run --provider amax --model minimax-m2.7

    # Run GPT-OSS smoke selection
    python -m product_intelligence.evaluation.semantic.cli run --provider amax --model gpt-oss-20b --mode smoke

    # Evaluate existing recorded response artifact without network
    python -m product_intelligence.evaluation.semantic.cli evaluate --responses /path/to/responses.jsonl

    # Compare completed full runs
    python -m product_intelligence.evaluation.semantic.cli compare /path/to/run1/manifest.json /path/to/run2/manifest.json
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from product_intelligence.evaluation.semantic.model_catalog import (
    ALL_MODELS,
    FULL_QUALIFICATION_MODELS,
    GPT_OSS_SMOKE_CASE_IDS,
    QualificationModel,
    is_known_model,
    is_skip_model,
    can_run_full,
    can_run_smoke,
    get_model_by_provider_model,
    is_smoke_model,
    ModelRole,
)
from product_intelligence.evaluation.semantic.runner import (
    SemanticBenchmarkRunner,
    run_benchmark,
)
from product_intelligence.evaluation.semantic.transport import (
    FakeSemanticModelTransport,
    get_openai_transport_for_provider,
)
from product_intelligence.evaluation.semantic.loader import (
    load_corpus,
)
from product_intelligence.evaluation.semantic.evaluator import (
    parse_raw_output,
    RawOutputParseError,
)
from product_intelligence.evaluation.semantic.comparison import (
    compare_benchmark_runs,
)


def list_models() -> None:
    """List available models."""
    print("Available semantic qualification models:")
    print()

    print("FULL QUALIFICATION MODELS:")
    for model in FULL_QUALIFICATION_MODELS:
        status = "generative" if model.is_generative else "non-generative"
        print(f"  {model.provider}/{model.model} (role: {model.role}, {status})")

    print()
    print("SMOKE-ONLY MODELS:")
    for model in [
        m for m in ALL_MODELS if m.role.value == "smoke_test"
    ]:
        print(f"  {model.provider}/{model.model} (role: {model.role})")

    print()
    print("SKIP MODELS (not benchmarked):")
    for model in [
        m for m in ALL_MODELS if m.role.value == "skip_non_generative"
    ]:
        print(f"  {model.provider}/{model.model} (role: {model.role})")


def run_command(args: argparse.Namespace) -> int:
    """Execute run command with catalog authorization enforcement."""
    # Validate mode
    if args.mode not in ("full", "smoke"):
        print(f"Error: Invalid mode '{args.mode}'. Must be 'full' or 'smoke'")
        return 1

    case_selection = "FULL" if args.mode == "full" else "SMOKE"

    # Fail closed on unknown models
    if not is_known_model(args.provider, args.model):
        print(
            f"Error: Unknown model: {args.provider}/{args.model}. "
            f"Model must be in the catalog to run.",
            file=sys.stderr
        )
        return 1

    # Reject SKIP models entirely
    if is_skip_model(args.provider, args.model):
        print(
            f"Error: Model {args.provider}/{args.model} is a SKIP model "
            f"and cannot be benchmarked.",
            file=sys.stderr
        )
        return 1

    # Authorization check: FULL models may only run FULL, SMOKE models only SMOKE
    if case_selection == "FULL":
        if not can_run_full(args.provider, args.model):
            model_obj = get_model_by_provider_model(args.provider, args.model)
            role_str = model_obj.role.value if model_obj else "unknown"
            print(
                f"Error: Model {args.provider}/{args.model} (role: {role_str}) "
                f"is not eligible for full runs. Only FULL qualification models "
                f"may run with case_selection=FULL.",
                file=sys.stderr
            )
            return 1
    else:  # SMOKE
        if not can_run_smoke(args.provider, args.model):
            model_obj = get_model_by_provider_model(args.provider, args.model)
            role_str = model_obj.role.value if model_obj else "unknown"
            print(
                f"Error: Model {args.provider}/{args.model} (role: {role_str}) "
                f"is not eligible for smoke runs. Only SMOKE_TEST models "
                f"may run with case_selection=SMOKE. "
                f"For full qualification models, use --mode full.",
                file=sys.stderr
            )
            return 1

    # Show smoke case info
    if args.mode == "smoke":
        print(f"Running RUNTIME SMOKE SCREEN (NOT A FULL SEMANTIC QUALIFICATION)")
        print(f"with {len(GPT_OSS_SMOKE_CASE_IDS)} cases:")
        for case_id in sorted(GPT_OSS_SMOKE_CASE_IDS):
            print(f"  - {case_id}")
        print()

    try:
        result = run_benchmark(
            provider=args.provider,
            model=args.model,
            case_selection=case_selection,
            output_dir=args.output_dir,
            temperature=args.temperature,
            max_tokens=args.max_tokens,
            request_timeout_seconds=args.request_timeout_seconds,
        )

        print()
        print("Run complete!")
        print(f"  Output directory: {result.config.output_dir}")
        print()

        # For SMOKE runs, show smoke-appropriate output
        if case_selection == "SMOKE":
            print("RUNTIME SMOKE SCREEN - NOT A FULL QUALIFICATION")
            print()
            print("SMOKE metrics (5 cases only):")
            er = result.evaluation_result
            print(f"  Valid output rate: {er.valid_output_rate:.2%}")
            print()
            print("Note: Full qualification hard gates are N/A for smoke runs.")
            print()
        else:
            print("Key metrics:")
            er = result.evaluation_result
            print(f"  Valid output rate: {er.valid_output_rate:.2%}")
            print(f"  Decision accuracy: {er.decision_accuracy:.2%}")
            print(f"  MATCH precision: {er.match_precision:.2%}")
            print(f"  MATCH recall: {er.match_recall:.2%}")
            print(f"  False MATCH count: {er.false_match_count}")
            print(f"  Safety cost: {er.safety_cost}")
            print()
            print("Hard gates:")
            for gate, passed in er.gates_passed.items():
                status = "PASS" if passed else "FAIL"
                print(f"  {gate}: {status}")

        return 0

    except ValueError as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1
    except Exception as e:
        print(f"Error: {type(e).__name__}: {e}", file=sys.stderr)
        return 1


def evaluate_command(args: argparse.Namespace) -> int:
    """Execute evaluate command - evaluate existing recorded responses."""
    try:
        # Load corpus
        corpus = load_corpus()

        # Load responses from JSONL
        with open(args.responses, "r", encoding="utf-8") as f:
            lines = f.readlines()

        responses: dict[str, dict[str, str]] = {}
        for line in lines:
            line = line.strip()
            if not line:
                continue
            record = json.loads(line)
            if "case_id" not in record or "raw_output" not in record:
                continue
            responses[record["case_id"]] = record

        # Parse raw outputs
        parsed_responses: dict[str, dict[str, Any]] = {}
        for case_id, record in responses.items():
            raw_output = record.get("raw_output")
            if raw_output is None:
                continue
            try:
                parsed_output = parse_raw_output(raw_output)
                parsed_responses[case_id] = parsed_output
            except RawOutputParseError as e:
                print(f"Warning: Failed to parse response for {case_id}: {e}")

        # Evaluate
        runner = SemanticBenchmarkRunner()
        evaluation_result = runner._evaluator(corpus, parsed_responses)

        # Report
        print("Evaluation results:")
        print(f"  Valid output rate: {evaluation_result.valid_output_rate:.2%}")
        print(f"  Decision accuracy: {evaluation_result.decision_accuracy:.2%}")
        print(f"  MATCH precision: {evaluation_result.match_precision:.2%}")
        print(f"  MATCH recall: {evaluation_result.match_recall:.2%}")
        print(f"  False MATCH count: {evaluation_result.false_match_count}")
        print(f"  Safety cost: {evaluation_result.safety_cost}")

        return 0

    except FileNotFoundError:
        print(f"Error: Responses file not found: {args.responses}", file=sys.stderr)
        return 1
    except Exception as e:
        print(f"Error: {type(e).__name__}: {e}", file=sys.stderr)
        return 1


def compare_command(args: argparse.Namespace) -> int:
    """Execute compare command - compare two or more benchmark runs."""
    if len(args.manifests) < 2:
        print("Error: At least two manifest paths required", file=sys.stderr)
        return 1

    try:
        # Pass paths directly to compare_benchmark_runs - it handles path loading internally
        comparison = compare_benchmark_runs(args.manifests)

        print("Comparison Results:")
        print()

        # Header
        print(
            f"{'Provider/Model':<25} {'Gates':<6} {'Valid':<8} "
            f"{'MATCH':<8} {'Recall':<8} {'Acc':<6} {'False':<6}"
        )
        print("-" * 75)

        # Sort by safety-first ordering
        sorted_results = sorted(
            comparison,
            key=lambda x: (
                not x["gates_passed"],
                x["false_match_count"],
                -x["match_precision"],
                -x["match_recall"],
                -x["accuracy"],
                x.get("median_latency", float("inf")),
            ),
        )

        for result in sorted_results:
            gates_str = "PASS" if result["gates_passed"] else "FAIL"
            print(
                f"{result['provider']}/{result['model']:<17} {gates_str:<6} "
                f"{result['valid_output_rate']*100:.1f}% {result['match_precision']*100:.1f}% "
                f"{result['match_recall']*100:.1f}% {result['accuracy']*100:.1f}% "
                f"{result['false_match_count']:<6}"
            )

        return 0

    except Exception as e:
        print(f"Error: {type(e).__name__}: {e}", file=sys.stderr)
        return 1


def create_parser() -> argparse.ArgumentParser:
    """Create CLI argument parser."""
    parser = argparse.ArgumentParser(
        prog="semantic-benchmark",
        description="Semantic model qualification benchmark runner",
    )

    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # List models
    list_parser = subparsers.add_parser(
        "list-models", help="List available qualification models"
    )

    # Run command
    run_parser = subparsers.add_parser(
        "run", help="Run one benchmark"
    )
    run_parser.add_argument(
        "--provider", "-p", required=True,
        help="Provider name (e.g., 'amax', 'vllm-262k')"
    )
    run_parser.add_argument(
        "--model", "-m", required=True,
        help="Model name"
    )
    run_parser.add_argument(
        "--mode", "-d", default="full",
        choices=["full", "smoke"],
        help="Case selection mode (default: full)"
    )
    run_parser.add_argument(
        "--output-dir", "-o",
        help="Output directory for artifacts"
    )
    run_parser.add_argument(
        "--temperature", "-t", type=float, default=0.0,
        help="Temperature setting (default: 0.0)"
    )
    run_parser.add_argument(
        "--max-tokens", type=int, default=1024,
        help="Maximum completion tokens (default: 1024)"
    )
    run_parser.add_argument(
        "--request-timeout-seconds", type=float, default=300.0,
        help="Request timeout in seconds (default: 300.0)"
    )

    # Evaluate command
    eval_parser = subparsers.add_parser(
        "evaluate", help="Evaluate existing recorded responses"
    )
    eval_parser.add_argument(
        "--responses", "-r", required=True,
        help="Path to responses JSONL file"
    )

    # Compare command
    compare_parser = subparsers.add_parser(
        "compare", help="Compare multiple benchmark runs"
    )
    compare_parser.add_argument(
        "manifests", nargs="+",
        help="Paths to manifest.json files to compare"
    )

    return parser


def main(argv: list[str] | None = None) -> int:
    """Main entry point."""
    parser = create_parser()
    args = parser.parse_args(argv)

    if args.command is None:
        parser.print_help()
        return 1

    if args.command == "list-models":
        list_models()
        return 0

    elif args.command == "run":
        return run_command(args)

    elif args.command == "evaluate":
        return evaluate_command(args)

    elif args.command == "compare":
        return compare_command(args)

    else:
        parser.print_help()
        return 1


if __name__ == "__main__":
    sys.exit(main())
