"""Offline comparison utility for semantic benchmark runs (PRODUCT-INTEL.SEMANTIC.BENCHMARK).

This module provides utilities for comparing multiple completed benchmark runs
and generating a leaderboard-style comparison table.

No live model integration is required for this phase.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from product_intelligence.evaluation.semantic.loader import load_corpus


# ---------------------------------------------------------------------------
# Error codes for comparison failures (bounded vocabulary)
# ---------------------------------------------------------------------------

PROVENANCE_ERROR_CODES = frozenset([
    "MISSING_REQUIRED_FIELD",
    "RUN_INCOMPLETE",
    "RUN_STATUS_FAILED_CONFIGURATION",
    "RUN_STATUS_FAILED_PROVIDER",
    "CASE_SELECTION_MISMATCH",
    "QUALIFICATION_GATES_NOT_APPLICABLE",
    "CORPUS_VERSION_MISMATCH",
    "CORPUS_SHA256_MISMATCH",
    "PROMPT_VERSION_MISMATCH",
    "PROMPT_SHA256_MISMATCH",
    "CASE_COUNT_MISMATCH",
    "CASE_ID_ORDER_MISMATCH",
    "CASE_ID_SET_MISMATCH",
    "MISSING_CORPUS_HASH",
    "MISSING_PROMPT_HASH",
    "SCHEMA_VERSION_INCOMPATIBLE",
    "BENCHMARK_KIND_MISMATCH",
    "SMOKE_CANNOT_ENTER_FULL_LEADERBOARD",
    "RUN_NOT_COMPLETED",
    "REQUEST_TIMEOUT_MISMATCH",
    "MISSING_REQUEST_TIMEOUT_PROVENANCE",
    "MISSING_GENERATION_PROVENANCE",
    "TEMPERATURE_MISMATCH",
    "MAX_TOKENS_MISMATCH",
])


@dataclass(frozen=True)
class ProvenanceCheckResult:
    """Result of a single provenance check."""

    passed: bool
    error_code: str | None = None
    detail: str | None = None


@dataclass(frozen=True)
class RunComparison:
    """Comparison data for one benchmark run."""

    provider: str
    model: str
    role: str
    case_selection: str
    case_count: int
    run_status: str  # COMPLETED, FAILED_CONFIGURATION, FAILED_PROVIDER
    qualification_eligible: bool
    qualification_gates_applicable: bool
    gates_passed: bool
    valid_output_rate: float
    match_precision: float
    match_recall: float
    accuracy: float
    false_match_count: int
    safety_cost: int
    median_latency: float | None = None
    manifest_path: str | None = None

    # Full provenance fields (for comparison)
    benchmark_kind: str | None = None
    schema_version: str | None = None
    corpus_version: int | None = None
    corpus_sha256: str | None = None
    prompt_version: str | None = None
    prompt_sha256: str | None = None
    case_ids: tuple[str, ...] = field(default_factory=tuple)
    error_codes: tuple[str, ...] = field(default_factory=tuple)  # Why not qualified
    # Transport parameters (for runtime policy comparison)
    request_timeout_seconds: float | None = None
    # Generation parameters (for quality consistency)
    temperature: float | None = None
    max_tokens: int | None = None


# ---------------------------------------------------------------------------
# Manifest loader
# ---------------------------------------------------------------------------


def load_run_manifest(path: str | Path) -> dict[str, Any]:
    """Load a benchmark run manifest.

    Args:
        path: Path to manifest.json

    Returns:
        Manifest dictionary

    Raises:
        FileNotFoundError: If the file is not found
        ValueError: If the manifest is invalid
    """
    path = Path(path)

    if not path.exists():
        raise FileNotFoundError(f"Manifest not found: {path}")

    with open(path, "r", encoding="utf-8") as f:
        manifest = json.load(f)

    # Validate required fields
    required = [
        "benchmark_kind", "schema_version", "runner_version",
        "corpus_version", "corpus_sha256", "prompt_version",
        "prompt_sha256", "provider", "model", "case_selection",
        "case_count",
    ]

    for field_name in required:
        if field_name not in manifest:
            raise ValueError(f"Manifest missing required field: {field_name}")

    return manifest


def _load_manifest_or_raise(item: dict[str, Any] | str | Path | RunComparison) -> dict[str, Any]:
    """Load manifest from path or return dict directly."""
    if isinstance(item, dict):
        return item
    elif isinstance(item, (str, Path)):
        return load_run_manifest(item)
    else:
        raise TypeError(f"Expected dict, str, or Path, got {type(item).__name__}")


def _compute_gates_passed(gates_data: dict[str, Any]) -> bool:
    """Compute overall gates_passed from frozen evaluator gate mapping.

    The frozen evaluator stores individual gate booleans. Overall gates_passed
    is True only when ALL individual gates are True.

    Args:
        gates_data: Dict from evaluation.json gates_passed field

    Returns:
        True if all gates passed, False otherwise or if gates_data is empty
    """
    if not gates_data:
        return False

    # All individual gate values must be True for overall to pass
    return all(bool(v) for v in gates_data.values())


# ---------------------------------------------------------------------------
# Canonical FULL corpus
# ---------------------------------------------------------------------------


def _get_canonical_full_case_ids() -> tuple[str, ...]:
    """Get the canonical FULL corpus ordered case IDs.

    Returns:
        Tuple of case IDs in canonical FULL corpus order
    """
    corpus = load_corpus()
    return tuple(c.case_id for c in corpus.cases)


# ---------------------------------------------------------------------------
# Run comparison data
# ---------------------------------------------------------------------------


def load_run_comparison(manifest_path: str | Path) -> RunComparison:
    """Load comparison data from a single run manifest.

    Args:
        manifest_path: Path to manifest.json

    Returns:
        RunComparison instance

    Raises:
        FileNotFoundError: If the file is not found
        ValueError: If required evaluation data is missing
    """
    manifest = load_run_manifest(manifest_path)
    manifest_dir = Path(manifest_path).parent
    evaluation_path = manifest_dir / "evaluation.json"

    evaluation_data: dict[str, Any] = {}
    if evaluation_path.exists():
        with open(evaluation_path, "r", encoding="utf-8") as f:
            evaluation_data = json.load(f)

    # Extract case_ids as tuple (manifest stores list)
    case_ids_raw = manifest.get("case_ids", [])
    case_ids = tuple(case_ids_raw) if case_ids_raw else tuple()

    # Extract request_timeout_seconds from transport_parameters
    request_timeout_seconds = None
    transport_params = manifest.get("transport_parameters", {})
    if transport_params:
        request_timeout_seconds = transport_params.get("request_timeout_seconds")

    # Extract generation parameters (temperature and max_tokens)
    temperature = None
    max_tokens = None
    generation_params = manifest.get("generation_parameters", {})
    if generation_params:
        temperature = generation_params.get("temperature")
        max_tokens = generation_params.get("max_tokens")

    # Extract run_status and related fields (default to COMPLETED if absent)
    run_status = manifest.get("run_status", "COMPLETED")
    qualification_eligible = manifest.get("qualification_eligible", False)
    qualification_gates_applicable = manifest.get("qualification_gates_applicable", True)

    return RunComparison(
        provider=manifest["provider"],
        model=manifest["model"],
        role=manifest.get("role", "unknown"),
        case_selection=manifest["case_selection"],
        case_count=manifest["case_count"],
        run_status=run_status,
        qualification_eligible=qualification_eligible,
        qualification_gates_applicable=qualification_gates_applicable,
        # Compute gates_passed from frozen gate mapping
        # The evaluator stores individual gate booleans in gates_passed dict
        # overall = all individual gate values must be True
        gates_passed=_compute_gates_passed(evaluation_data.get("gates_passed", {})),
        valid_output_rate=evaluation_data.get("valid_output_rate", 0.0),
        match_precision=evaluation_data.get("match_precision", 0.0),
        match_recall=evaluation_data.get("match_recall", 0.0),
        accuracy=evaluation_data.get("decision_accuracy", 0.0),
        false_match_count=evaluation_data.get("false_match_count", 0),
        safety_cost=evaluation_data.get("safety_cost", 0),
        median_latency=None,  # Not available in current schema
        manifest_path=str(manifest_path),
        # Provenance fields
        benchmark_kind=manifest.get("benchmark_kind"),
        schema_version=manifest.get("schema_version"),
        corpus_version=manifest.get("corpus_version"),
        corpus_sha256=manifest.get("corpus_sha256"),
        prompt_version=manifest.get("prompt_version"),
        prompt_sha256=manifest.get("prompt_sha256"),
        case_ids=case_ids,
        # Transport parameters
        request_timeout_seconds=request_timeout_seconds,
        # Generation parameters
        temperature=temperature,
        max_tokens=max_tokens,
    )


# ---------------------------------------------------------------------------
# Provenance validation
# ---------------------------------------------------------------------------


def _check_run_qualified_for_full_leaderboard(
    comp: RunComparison,
) -> ProvenanceCheckResult:
    """Check if a run is qualified for the FULL leaderboard.

    A run may enter the FULL leaderboard only if ALL of the following hold:
    - run_status == COMPLETED
    - qualification_eligible == true
    - qualification_gates_applicable == true
    - benchmark_kind matches (semantic_model_qualification)
    - schema_version is compatible
    - case_selection == FULL
    - case_count == 64 (or whatever the FULL corpus size is)
    - ordered case_ids match exactly the canonical corpus IDs
    - corpus_version matches
    - corpus_sha256 matches
    - prompt_version matches
    - prompt_sha256 matches

    Returns:
        ProvenanceCheckResult with passed=True if qualified, or
        ProvenanceCheckResult with passed=False and error_code describing failure.
    """
    # Check run_status
    if comp.run_status != "COMPLETED":
        return ProvenanceCheckResult(
            passed=False,
            error_code="RUN_NOT_COMPLETED",
            detail=f"run_status={comp.run_status}, expected COMPLETED",
        )

    # Check qualification_eligible
    if not comp.qualification_eligible:
        return ProvenanceCheckResult(
            passed=False,
            error_code="RUN_INCOMPLETE",
            detail=f"qualification_eligible={comp.qualification_eligible}, expected True",
        )

    # Check qualification_gates_applicable (FULL runs must have gates applicable)
    if not comp.qualification_gates_applicable:
        return ProvenanceCheckResult(
            passed=False,
            error_code="QUALIFICATION_GATES_NOT_APPLICABLE",
            detail="qualification_gates_applicable=False, expected True for FULL leaderboard",
        )

    # Check benchmark_kind
    if comp.benchmark_kind != "semantic_model_qualification":
        return ProvenanceCheckResult(
            passed=False,
            error_code="BENCHMARK_KIND_MISMATCH",
            detail=f"benchmark_kind={comp.benchmark_kind}, expected semantic_model_qualification",
        )

    # Check case_selection
    if comp.case_selection != "FULL":
        return ProvenanceCheckResult(
            passed=False,
            error_code="SMOKE_CANNOT_ENTER_FULL_LEADERBOARD",
            detail=f"case_selection={comp.case_selection}, expected FULL for leaderboard",
        )

    # Check required provenance fields for FULL leaderboard
    # Timeout must be present
    if comp.request_timeout_seconds is None:
        return ProvenanceCheckResult(
            passed=False,
            error_code="MISSING_REQUEST_TIMEOUT_PROVENANCE",
            detail="request_timeout_seconds is required for FULL leaderboard",
        )

    # Generation parameters must be present
    if comp.temperature is None:
        return ProvenanceCheckResult(
            passed=False,
            error_code="MISSING_GENERATION_PROVENANCE",
            detail="temperature is required for FULL leaderboard",
        )
    if comp.max_tokens is None:
        return ProvenanceCheckResult(
            passed=False,
            error_code="MISSING_GENERATION_PROVENANCE",
            detail="max_tokens is required for FULL leaderboard",
        )

    # Check canonical FULL corpus eligibility
    canonical_full_case_ids = _get_canonical_full_case_ids()

    # 1. case_count must equal len(canonical_full_case_ids)
    if comp.case_count != len(canonical_full_case_ids):
        return ProvenanceCheckResult(
            passed=False,
            error_code="CASE_COUNT_MISMATCH",
            detail=f"case_count={comp.case_count}, expected {len(canonical_full_case_ids)} for FULL corpus",
        )

    # 2. case_ids must contain exactly the canonical IDs
    comp_case_ids_set = set(comp.case_ids) if comp.case_ids else set()
    canonical_set = set(canonical_full_case_ids)
    if comp_case_ids_set != canonical_set:
        return ProvenanceCheckResult(
            passed=False,
            error_code="CASE_ID_SET_MISMATCH",
            detail=f"case_ids set mismatch: run has {len(comp_case_ids_set)} IDs, canonical corpus has {len(canonical_set)} IDs",
        )

    # 3. case_ids must be in the exact canonical order
    comp_case_ids_tuple = tuple(comp.case_ids) if comp.case_ids else tuple()
    if comp_case_ids_tuple != canonical_full_case_ids:
        return ProvenanceCheckResult(
            passed=False,
            error_code="CASE_ID_ORDER_MISMATCH",
            detail="case_ids order differs from canonical corpus order",
        )

    return ProvenanceCheckResult(passed=True)


def _check_provenance_alignment(
    reference: RunComparison,
    candidate: RunComparison,
) -> list[ProvenanceCheckResult]:
    """Check that candidate's provenance aligns with reference.

    Returns a list of ProvenanceCheckResults, one per check.
    All checks must pass for runs to be comparable.
    """
    results: list[ProvenanceCheckResult] = []

    # Schema version check (compatible if same major version)
    ref_schema = reference.schema_version or ""
    cand_schema = candidate.schema_version or ""
    if ref_schema != cand_schema:
        # Check major version compatibility
        ref_major = ref_schema.split(".")[0] if ref_schema else ""
        cand_major = cand_schema.split(".")[0] if cand_schema else ""
        if ref_major != cand_major:
            results.append(ProvenanceCheckResult(
                passed=False,
                error_code="SCHEMA_VERSION_INCOMPATIBLE",
                detail=f"schema_version {ref_schema} vs {cand_schema}",
            ))

    # Corpus version check
    if reference.corpus_version != candidate.corpus_version:
        results.append(ProvenanceCheckResult(
            passed=False,
            error_code="CORPUS_VERSION_MISMATCH",
            detail=f"corpus_version {reference.corpus_version} vs {candidate.corpus_version}",
        ))

    # Corpus SHA256 check
    if reference.corpus_sha256 != candidate.corpus_sha256:
        results.append(ProvenanceCheckResult(
            passed=False,
            error_code="CORPUS_SHA256_MISMATCH",
            detail=f"corpus_sha256 mismatch",
        ))

    # Prompt version check
    if reference.prompt_version != candidate.prompt_version:
        results.append(ProvenanceCheckResult(
            passed=False,
            error_code="PROMPT_VERSION_MISMATCH",
            detail=f"prompt_version {reference.prompt_version} vs {candidate.prompt_version}",
        ))

    # Prompt SHA256 check
    if reference.prompt_sha256 != candidate.prompt_sha256:
        results.append(ProvenanceCheckResult(
            passed=False,
            error_code="PROMPT_SHA256_MISMATCH",
            detail=f"prompt_sha256 mismatch",
        ))

    # Request timeout check (must match for comparable FULL runs)
    # If one has timeout and the other doesn't, they are incompatible
    # If both have timeouts, they must match exactly
    ref_timeout = reference.request_timeout_seconds
    cand_timeout = candidate.request_timeout_seconds

    # Both None means incompatible (missing provenance)
    if ref_timeout is None and cand_timeout is None:
        results.append(ProvenanceCheckResult(
            passed=False,
            error_code="MISSING_REQUEST_TIMEOUT_PROVENANCE",
            detail="both runs are missing request_timeout_seconds",
        ))
    elif ref_timeout is not None and cand_timeout is None:
        results.append(ProvenanceCheckResult(
            passed=False,
            error_code="MISSING_REQUEST_TIMEOUT_PROVENANCE",
            detail="reference has timeout provenance but candidate is missing",
        ))
    elif ref_timeout is None and cand_timeout is not None:
        results.append(ProvenanceCheckResult(
            passed=False,
            error_code="MISSING_REQUEST_TIMEOUT_PROVENANCE",
            detail="candidate has timeout provenance but reference is missing",
        ))
    elif ref_timeout is not None and cand_timeout is not None:
        # Both have timeout - they must match exactly
        if ref_timeout != cand_timeout:
            results.append(ProvenanceCheckResult(
                passed=False,
                error_code="REQUEST_TIMEOUT_MISMATCH",
                detail=f"request_timeout_seconds {ref_timeout} vs {cand_timeout}",
            ))

    # Generation parameters check (must match for comparable FULL runs)
    ref_temp = reference.temperature
    cand_temp = candidate.temperature
    ref_max_tokens = reference.max_tokens
    cand_max_tokens = candidate.max_tokens

    # Temperature check
    if ref_temp is None or cand_temp is None:
        results.append(ProvenanceCheckResult(
            passed=False,
            error_code="MISSING_GENERATION_PROVENANCE",
            detail=f"temperature missing (reference: {ref_temp}, candidate: {cand_temp})",
        ))
    elif ref_temp != cand_temp:
        results.append(ProvenanceCheckResult(
            passed=False,
            error_code="TEMPERATURE_MISMATCH",
            detail=f"temperature {ref_temp} vs {cand_temp}",
        ))

    # max_tokens check
    if ref_max_tokens is None or cand_max_tokens is None:
        results.append(ProvenanceCheckResult(
            passed=False,
            error_code="MISSING_GENERATION_PROVENANCE",
            detail=f"max_tokens missing (reference: {ref_max_tokens}, candidate: {cand_max_tokens})",
        ))
    elif ref_max_tokens != cand_max_tokens:
        results.append(ProvenanceCheckResult(
            passed=False,
            error_code="MAX_TOKENS_MISMATCH",
            detail=f"max_tokens {ref_max_tokens} vs {cand_max_tokens}",
        ))

    # Case count check
    if reference.case_count != candidate.case_count:
        results.append(ProvenanceCheckResult(
            passed=False,
            error_code="CASE_COUNT_MISMATCH",
            detail=f"case_count {reference.case_count} vs {candidate.case_count}",
        ))

    # Case IDs - exact ordered comparison
    if reference.case_ids != candidate.case_ids:
        # Check if it's just ordering or actual set difference
        ref_set = set(reference.case_ids)
        cand_set = set(candidate.case_ids)
        if ref_set != cand_set:
            results.append(ProvenanceCheckResult(
                passed=False,
                error_code="CASE_ID_SET_MISMATCH",
                detail=f"case_id sets differ: ref has {len(ref_set)}, cand has {len(cand_set)}",
            ))
        else:
            results.append(ProvenanceCheckResult(
                passed=False,
                error_code="CASE_ID_ORDER_MISMATCH",
                detail="case_ids order differs (same elements, different sequence)",
            ))

    # Check for missing hashes
    if not candidate.corpus_sha256:
        results.append(ProvenanceCheckResult(
            passed=False,
            error_code="MISSING_CORPUS_HASH",
            detail="corpus_sha256 is missing or empty",
        ))

    if not candidate.prompt_sha256:
        results.append(ProvenanceCheckResult(
            passed=False,
            error_code="MISSING_PROMPT_HASH",
            detail="prompt_sha256 is missing or empty",
        ))

    return results


# ---------------------------------------------------------------------------
# Comparison utility
# ---------------------------------------------------------------------------


def compare_benchmark_runs(
    manifests: list[dict[str, Any]] | list[str | Path] | list[RunComparison],
) -> list[dict[str, Any]]:
    """Compare multiple benchmark FULL runs.

    FULL runs are comparable only when ALL required benchmark provenance agrees:
    - run_status == COMPLETED
    - qualification_eligible == true
    - qualification_gates_applicable == true
    - benchmark_kind (must be semantic_model_qualification)
    - compatible schema version
    - case_selection == FULL (smoke cannot enter FULL leaderboard)
    - case_count (same number of cases)
    - exact case ID selection/order
    - corpus_version
    - corpus_sha256
    - prompt_version
    - prompt_sha256
    - request_timeout_seconds (must match exactly)
    - temperature (must match exactly)
    - max_tokens (must match exactly)

    SMOKE runs are NEVER comparable with FULL runs.

    Unknown/missing/corrupt provenance: fail closed.
    Do not automatically select a winner.

    Args:
        manifests: List of manifest dicts, paths, or RunComparison instances

    Returns:
        List of comparison dicts sorted by safety-first ordering

    Raises:
        ValueError: If manifests have incompatible provenance or are not FULL runs
    """
    comparisons: list[RunComparison] = []

    # Normalize inputs to RunComparison
    for item in manifests:
        if isinstance(item, RunComparison):
            comparisons.append(item)
        elif isinstance(item, (str, Path)):
            comparisons.append(load_run_comparison(item))
        elif isinstance(item, dict):
            # Dict input is no longer supported - must use paths or RunComparison
            raise TypeError(
                "Dict input is not supported. "
                "Use a manifest path (str or Path) or a RunComparison instance."
            )

    if not comparisons:
        return []

    # Validate each run is qualified for FULL leaderboard
    for i, comp in enumerate(comparisons):
        qualifier_check = _check_run_qualified_for_full_leaderboard(comp)
        if not qualifier_check.passed:
            raise ValueError(
                f"Run {i+1} ({comp.provider}/{comp.model}) cannot enter FULL leaderboard: "
                f"{qualifier_check.error_code} - {qualifier_check.detail}"
            )

    # Validate provenance compatibility for ALL runs (pairwise against first)
    if len(comparisons) > 1:
        reference = comparisons[0]
        for i, comp in enumerate(comparisons[1:], start=2):
            alignment_results = _check_provenance_alignment(reference, comp)
            failures = [r for r in alignment_results if not r.passed]
            if failures:
                failure_details = "; ".join(
                    f"{r.error_code}: {r.detail}" for r in failures
                )
                raise ValueError(
                    f"Cannot compare run {i} ({comp.provider}/{comp.model}) with run 1 "
                    f"({reference.provider}/{reference.model}): {failure_details}"
                )

    # Build result list
    results: list[dict[str, Any]] = []
    for comp in comparisons:
        results.append({
            "provider": comp.provider,
            "model": comp.model,
            "role": comp.role,
            "case_selection": comp.case_selection,
            "case_count": comp.case_count,
            "qualification_eligible": comp.qualification_eligible,
            "gates_passed": comp.gates_passed,
            "valid_output_rate": comp.valid_output_rate,
            "match_precision": comp.match_precision,
            "match_recall": comp.match_recall,
            "accuracy": comp.accuracy,
            "false_match_count": comp.false_match_count,
            "safety_cost": comp.safety_cost,
            "median_latency": comp.median_latency,
            "manifest_path": comp.manifest_path,
        })

    # Sort by safety-first ordering
    results.sort(
        key=lambda x: (
            not x["gates_passed"],
            x["false_match_count"],
            -x["match_precision"],
            -x["match_recall"],
            -x["accuracy"],
            x.get("median_latency", float("inf")),
        )
    )

    return results


def generate_leaderboard(
    comparisons: list[dict[str, Any]],
    max_entries: int = 20,
) -> str:
    """Generate a human-readable leaderboard.

    Args:
        comparisons: List of comparison dicts from compare_benchmark_runs
        max_entries: Maximum entries to show

    Returns:
        Markdown-formatted leaderboard
    """
    lines = [
        "# Semantic Model Qualification Leaderboard",
        "",
        "Sorted by: safety-first ordering",
        "  1. Hard gates passed",
        "  2. False MATCH count (ascending)",
        "  3. MATCH precision (descending)",
        "  4. MATCH recall (descending)",
        "  5. Accuracy (descending)",
        "  6. Latency (ascending, as tie-break)",
        "",
        "| Provider | Model | Qual | Gates | Valid % | MATCH % | Recall % | Acc % | False | Safety |",
        "|----------|-------|-------|-------|---------|---------|----------|-------|-------|--------|",
    ]

    for item in comparisons[:max_entries]:
        qual = "YES" if item.get("qualification_eligible", False) else "NO"
        gates = "PASS" if item["gates_passed"] else "FAIL"
        line = (
            f"| {item['provider']} | {item['model']} | {qual} | {gates} | "
            f"{item['valid_output_rate']*100:.1f}% | "
            f"{item['match_precision']*100:.1f}% | "
            f"{item['match_recall']*100:.1f}% | "
            f"{item['accuracy']*100:.1f}% | "
            f"{item['false_match_count']} | "
            f"{item['safety_cost']} |"
        )
        lines.append(line)

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Verification utilities
# ---------------------------------------------------------------------------


def verify_run_compatibility(
    manifest1: dict[str, Any],
    manifest2: dict[str, Any],
) -> bool:
    """Verify two runs are compatible for comparison.

    Uses the full provenance check machinery.
    """
    # Extract timeout from transport_parameters for both manifests
    timeout1 = None
    transport_params1 = manifest1.get("transport_parameters", {})
    if transport_params1:
        timeout1 = transport_params1.get("request_timeout_seconds")

    timeout2 = None
    transport_params2 = manifest2.get("transport_parameters", {})
    if transport_params2:
        timeout2 = transport_params2.get("request_timeout_seconds")

    # Extract generation parameters
    temp1 = None
    max_tokens1 = None
    gen_params1 = manifest1.get("generation_parameters", {})
    if gen_params1:
        temp1 = gen_params1.get("temperature")
        max_tokens1 = gen_params1.get("max_tokens")

    temp2 = None
    max_tokens2 = None
    gen_params2 = manifest2.get("generation_parameters", {})
    if gen_params2:
        temp2 = gen_params2.get("temperature")
        max_tokens2 = gen_params2.get("max_tokens")

    comp1 = RunComparison(
        provider=manifest1.get("provider", ""),
        model=manifest1.get("model", ""),
        role=manifest1.get("role", "unknown"),
        case_selection=manifest1.get("case_selection", "UNKNOWN"),
        case_count=manifest1.get("case_count", 0),
        run_status=manifest1.get("run_status", "COMPLETED"),
        qualification_eligible=manifest1.get("qualification_eligible", False),
        qualification_gates_applicable=manifest1.get("qualification_gates_applicable", True),
        gates_passed=False,
        valid_output_rate=0.0,
        match_precision=0.0,
        match_recall=0.0,
        accuracy=0.0,
        false_match_count=0,
        safety_cost=0,
        benchmark_kind=manifest1.get("benchmark_kind"),
        schema_version=manifest1.get("schema_version"),
        corpus_version=manifest1.get("corpus_version"),
        corpus_sha256=manifest1.get("corpus_sha256"),
        prompt_version=manifest1.get("prompt_version"),
        prompt_sha256=manifest1.get("prompt_sha256"),
        case_ids=tuple(manifest1.get("case_ids", [])),
        request_timeout_seconds=timeout1,
        temperature=temp1,
        max_tokens=max_tokens1,
    )

    comp2 = RunComparison(
        provider=manifest2.get("provider", ""),
        model=manifest2.get("model", ""),
        role=manifest2.get("role", "unknown"),
        case_selection=manifest2.get("case_selection", "UNKNOWN"),
        case_count=manifest2.get("case_count", 0),
        run_status=manifest2.get("run_status", "COMPLETED"),
        qualification_eligible=manifest2.get("qualification_eligible", False),
        qualification_gates_applicable=manifest2.get("qualification_gates_applicable", True),
        gates_passed=False,
        valid_output_rate=0.0,
        match_precision=0.0,
        match_recall=0.0,
        accuracy=0.0,
        false_match_count=0,
        safety_cost=0,
        benchmark_kind=manifest2.get("benchmark_kind"),
        schema_version=manifest2.get("schema_version"),
        corpus_version=manifest2.get("corpus_version"),
        corpus_sha256=manifest2.get("corpus_sha256"),
        prompt_version=manifest2.get("prompt_version"),
        prompt_sha256=manifest2.get("prompt_sha256"),
        case_ids=tuple(manifest2.get("case_ids", [])),
        request_timeout_seconds=timeout2,
        temperature=temp2,
        max_tokens=max_tokens2,
    )

    # Check leaderboard qualification
    if not _check_run_qualified_for_full_leaderboard(comp1).passed:
        return False
    if not _check_run_qualified_for_full_leaderboard(comp2).passed:
        return False

    # Check provenance alignment
    alignment_results = _check_provenance_alignment(comp1, comp2)
    return all(r.passed for r in alignment_results)


def filter_compatible_runs(
    manifests: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Filter to only runs with compatible provenance.

    Args:
        manifests: List of manifest dicts

    Returns:
        List of compatible manifests
    """
    if not manifests:
        return []

    compatible = [manifests[0]]

    for manifest in manifests[1:]:
        if verify_run_compatibility(compatible[-1], manifest):
            compatible.append(manifest)

    return compatible