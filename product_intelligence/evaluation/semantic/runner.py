"""Benchmark runner for semantic model qualification (PRODUCT-INTEL.SEMANTIC.BENCHMARK).

This module implements the runner that executes semantic model qualification
batches against the frozen corpus.

No live model integration is required for this phase.
All tests use fake transports / recorded responses.
"""

from __future__ import annotations

import hashlib
import json
import os
import subprocess
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from product_intelligence.evaluation.semantic.evaluator import (
    evaluate_responses,
)
from product_intelligence.evaluation.semantic.loader import (
    SemanticCorpus,
    load_corpus,
)
from product_intelligence.evaluation.semantic.prompt import (
    SemanticPrompt,
    build_prompt,
    export_corpus_to_jsonl,
    import_results_from_jsonl,
)
from product_intelligence.evaluation.semantic.transport import (
    FakeSemanticModelTransport,
    OpenAISemanticTransport,
    SemanticModelTransport,
    TransportFailure,
    TransportResult,
    get_openai_transport_for_provider,
)
from product_intelligence.evaluation.semantic.vocabulary import (
    SemanticDecision,
)
from product_intelligence.evaluation.semantic.model_catalog import (
    FULL_QUALIFICATION_MODELS,
    GPT_OSS_SMOKE_CASE_IDS,
    QualificationModel,
    is_smoke_model,
    is_full_qualification_model,
    can_run_full,
    can_run_smoke,
    is_known_model,
    is_skip_model,
    get_model_by_provider_model,
    get_full_qualification_models,
    get_smoke_only_models,
    get_skip_models,
)


# ---------------------------------------------------------------------------
# Filesystem-safe naming
# ---------------------------------------------------------------------------


def _make_filesystem_safe(name: str) -> str:
    r"""Convert a provider/model string to a filesystem-safe slug.

    Replaces ALL Windows-invalid characters (/\:|"?*<>), control characters,
    and trailing dots/spaces with safe alternatives. For provider/model IDs,
    this means "provider/model" becomes "provider_model".

    When sanitization changes the identity, adds a short hash suffix for
    collision resistance.

    Args:
        name: Provider/model string (e.g., "someprovider/model-name")

    Returns:
        Filesystem-safe string (e.g., "someprovider_model-name--a1b2c3d4")
    """
    import re

    original = name

    # Replace path separators and other unsafe chars with underscore
    unsafe_chars = set('/\\:|"<>?*')
    safe = name
    for char in unsafe_chars:
        safe = safe.replace(char, "_")

    # Remove any control characters (ASCII < 32 except tab, newline, CR)
    safe = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f]", "_", safe)

    # Remove trailing dots and spaces (Windows special behavior)
    safe = safe.rstrip(". ")

    # If sanitization changed the name, add a hash suffix for collision resistance
    changed = safe != original
    if changed:
        hash_suffix = hashlib.sha256(original.encode("utf-8")).hexdigest()[:8]
        safe = f"{safe}--{hash_suffix}"

    return safe


def _validate_path_safety(target: Path, root: Path) -> bool:
    """Verify target is truly inside root (no escape via ..)."""
    try:
        target_resolved = target.resolve()
        root_resolved = root.resolve()
        # Ensure target is under root
        return target_resolved.is_relative_to(root_resolved)
    except (ValueError, OSError):
        return False


# Runner version for artifact versioning
RUNNER_VERSION = "1.0"
SCHEMA_VERSION = "1.0"


# ---------------------------------------------------------------------------
# Benchmark run configuration
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class BenchmarkRunConfig:
    """Configuration for one benchmark run."""

    provider: str
    model: str
    case_selection: str  # "FULL" or "SMOKE"
    transport: SemanticModelTransport
    temperature: float = 0.0
    max_tokens: int = 1024
    output_dir: str | Path | None = None

    def __post_init__(self) -> None:
        """Validate configuration against catalog authorization."""
        if self.case_selection not in ("FULL", "SMOKE"):
            raise ValueError(f"Invalid case_selection: {self.case_selection}")

        # Fail closed on unknown models
        if not is_known_model(self.provider, self.model):
            raise ValueError(
                f"Unknown model: {self.provider}/{self.model}. "
                f"Model must be in the catalog to run."
            )

        # Reject SKIP models entirely
        if is_skip_model(self.provider, self.model):
            raise ValueError(
                f"Model {self.provider}/{self.model} is a SKIP model "
                f"and cannot be benchmarked."
            )

        # SMOKE selection: only SMOKE_TEST models may run smoke
        if self.case_selection == "SMOKE":
            if not can_run_smoke(self.provider, self.model):
                raise ValueError(
                    f"Model {self.provider}/{self.model} is not eligible for smoke runs. "
                    f"Only SMOKE_TEST models may run smoke. "
                    f"For full qualification models, use case_selection=FULL."
                )

        # FULL selection: only FULL models may run full
        if self.case_selection == "FULL":
            if not can_run_full(self.provider, self.model):
                raise ValueError(
                    f"Model {self.provider}/{self.model} is not eligible for full runs. "
                    f"Only full qualification models may run FULL. "
                    f"For smoke-only models, use case_selection=SMOKE."
                )


# ---------------------------------------------------------------------------
# Run result
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class RunResult:
    """Complete result of a benchmark run."""

    config: BenchmarkRunConfig
    corpus: SemanticCorpus
    responses: dict[str, dict[str, Any]]
    evaluation_result: Any  # EvaluationResult from evaluator
    manifest: dict[str, Any]
    run_timestamp: datetime


# ---------------------------------------------------------------------------
# Manifest schema
# ---------------------------------------------------------------------------


def _compute_sha256(data: str) -> str:
    """Compute SHA256 hash of string data."""
    return hashlib.sha256(data.encode("utf-8")).hexdigest()


def _compute_corpus_sha256(corpus: SemanticCorpus) -> str:
    """Compute SHA256 hash of the actual corpus source file.

    Reads the canonical corpus source file (cases.json), parses it,
    canonicalizes with deterministic JSON serialization, and hashes
    the UTF-8 bytes.

    FAIL CLOSED: If the corpus source file cannot be read, parsed, or
    canonicalized, this function raises an exception BEFORE any model
    call. There is no fallback projection.

    Args:
        corpus: The semantic corpus (used only for validation)

    Returns:
        SHA256 hex digest of the canonical corpus source JSON

    Raises:
        FileNotFoundError: If corpus source file is missing
        ValueError: If corpus source file is invalid JSON
    """
    # Load the raw corpus file content directly to ensure we're hashing
    # exactly what was used as the benchmark source
    corpus_path = Path(__file__).parent / ".." / ".." / ".." / "evaluation" / "semantic_corpus" / "cases.json"
    corpus_path = corpus_path.resolve()

    if not corpus_path.exists():
        raise FileNotFoundError(
            f"Corpus source file not found: {corpus_path}. "
            "Cannot compute corpus hash for benchmark run."
        )

    with open(corpus_path, "r", encoding="utf-8") as f:
        raw_content = f.read()

    # Canonical JSON with deterministic sorting - fail if invalid
    data = json.loads(raw_content)
    canonical = json.dumps(data, sort_keys=True, ensure_ascii=False)

    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def _compute_prompt_sha256(cases: tuple, config: BenchmarkRunConfig) -> str:
    """Compute SHA256 hash of the actual prompts used in this run.

    Hashes the exact prompts (system + user) for each case in run order.
    This is the ground truth for prompt content verification.

    Args:
        cases: Tuple of cases that were used in this run
        config: The run configuration

    Returns:
        SHA256 hex digest of the canonical prompt JSON
    """
    prompt_entries = []
    for case in cases:
        prompt = build_prompt(
            case_id=case.case_id,
            target_mpn=case.target.manufacturer_part_number,
            target_description=case.target.description,
            candidate_title=case.candidate.product_title or "",
            candidate_mpn_field=case.candidate.manufacturer_part_number_text,
            candidate_sku=case.candidate.sku_text,
            candidate_specs=case.candidate.description_or_specs,
            evidence_source=case.candidate_evidence_source,
        )
        prompt_entries.append({
            "case_id": case.case_id,
            "system_prompt": prompt.system_prompt,
            "user_prompt": prompt.user_prompt,
        })

    canonical = json.dumps(prompt_entries, sort_keys=True, ensure_ascii=False)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def _build_manifest(
    config: BenchmarkRunConfig,
    corpus: SemanticCorpus,
    case_ids: tuple[str, ...],
    prompt_version: str,
    corpus_sha256: str,
    prompt_sha256: str,
    start_time: datetime,
    finish_time: datetime,
    run_status: str = "COMPLETED",
    qualification_eligible: bool | None = None,
    qualification_gates_applicable: bool | None = None,
) -> dict[str, Any]:
    """Build manifest dictionary.
    
    Args:
        config: Benchmark run configuration
        corpus: Loaded semantic corpus
        case_ids: Ordered tuple of case IDs that were attempted
        prompt_version: Prompt version string
        corpus_sha256: SHA256 of corpus source
        prompt_sha256: SHA256 of prompts
        start_time: Run start timestamp
        finish_time: Run finish timestamp
        run_status: Run completion status (COMPLETED, FAILED_CONFIGURATION, FAILED_PROVIDER)
        qualification_eligible: Whether run is eligible for qualification
        qualification_gates_applicable: Whether hard gates apply to this run
    
    Returns:
        Manifest dictionary ready for JSON serialization
    """
    # Compute defaults based on case_selection if not provided
    if qualification_eligible is None:
        qualification_eligible = config.case_selection == "FULL"
    if qualification_gates_applicable is None:
        qualification_gates_applicable = config.case_selection == "FULL"
    git_head = None
    try:
        result = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        if result.returncode == 0:
            git_head = result.stdout.strip()
    except Exception:
        pass  # Silently ignore if git not available

    # Look up model from catalog
    model_obj = get_model_by_provider_model(config.provider, config.model)
    role = model_obj.role.value if model_obj else "unknown"

    return {
        "benchmark_kind": "semantic_model_qualification",
        "schema_version": SCHEMA_VERSION,
        "runner_version": RUNNER_VERSION,
        "corpus_version": corpus.corpus_version,
        "corpus_sha256": corpus_sha256,
        "prompt_version": prompt_version,
        "prompt_sha256": prompt_sha256,
        "provider": config.provider,
        "model": config.model,
        "role": role,
        # Explicit requested model provenance
        "requested_provider": config.provider,
        "requested_model": config.model,
        "generation_parameters": {
            "temperature": config.temperature,
            "max_tokens": config.max_tokens,
        },
        "case_selection": config.case_selection,
        # Case IDs: use ordered tuple, NOT sorted
        "case_ids": list(case_ids),  # JSON doesn't support tuple, convert to list
        "case_count": len(case_ids),
        "start_timestamp": start_time.isoformat(),
        "finish_timestamp": finish_time.isoformat(),
        "git_head": git_head,
        "transport_type": type(config.transport).__name__,
        # Run status and qualification
        "run_status": run_status,
        "qualification_eligible": qualification_eligible,
        "qualification_gates_applicable": qualification_gates_applicable,
    }


# ---------------------------------------------------------------------------
# Runner implementation
# ---------------------------------------------------------------------------


class SemanticBenchmarkRunner:
    """Runner for semantic model qualification benchmarks."""

    def __init__(
        self,
        *,
        transport: SemanticModelTransport | None = None,
        evaluator: Callable = evaluate_responses,
    ):
        """Initialize runner.

        Args:
            transport: Transport instance (uses fake if None for testing)
            evaluator: Evaluator function (default: evaluate_responses)
        """
        self._transport = transport
        self._evaluator = evaluator
        self._corpus = load_corpus()

    def _get_transport(self) -> SemanticModelTransport:
        """Get transport instance."""
        if self._transport is not None:
            return self._transport
        # For fake transport, pass case_ids for testing with non-heuristic extraction
        fake_transport = FakeSemanticModelTransport()
        if isinstance(self._transport, FakeSemanticModelTransport) and hasattr(self._transport, '_case_ids'):
            # Preserve case_ids if the transport has them set
            pass
        return FakeSemanticModelTransport()

    def run(
        self,
        config: BenchmarkRunConfig,
    ) -> RunResult:
        """Execute one benchmark run.

        Args:
            config: Benchmark run configuration

        Returns:
            RunResult with all artifacts
        """
        start_time = datetime.now(timezone.utc)

        # Select cases - now returns tuple, not frozenset
        case_ids = self._select_case_ids(config.case_selection)
        cases = tuple(c for c in self._corpus.cases if c.case_id in case_ids)

        # Build prompts
        prompts = []
        for case in cases:
            prompt = build_prompt(
                case_id=case.case_id,
                target_mpn=case.target.manufacturer_part_number,
                target_description=case.target.description,
                candidate_title=case.candidate.product_title or "",
                candidate_mpn_field=case.candidate.manufacturer_part_number_text,
                candidate_sku=case.candidate.sku_text,
                candidate_specs=case.candidate.description_or_specs,
                evidence_source=case.candidate_evidence_source,
            )
            prompts.append((case, prompt))

        # Execute requests with fatal abort handling
        responses: dict[str, dict[str, Any]] = {}
        run_status = "COMPLETED"
        qualification_eligible = config.case_selection == "FULL"
        qualification_gates_applicable = config.case_selection == "FULL"
        requested_model = config.model  # Track requested model for mismatch check
        provider_reported_model: str | None = None
        
        for case, prompt in prompts:
            result = self._execute_single_request(
                prompt=prompt,
                model=config.model,
                temperature=config.temperature,
                max_tokens=config.max_tokens,
                transport=self._get_transport(),
            )

            if isinstance(result, TransportResult):
                # Track provider-reported model from first successful response
                if provider_reported_model is None and result.provider_reported_model is not None:
                    provider_reported_model = result.provider_reported_model
                
                # Check for model mismatch if provider reported different model
                if provider_reported_model is not None and provider_reported_model != requested_model:
                    # MODEL_IDENTITY_MISMATCH - abort immediately
                    error_type = "MODEL_IDENTITY_MISMATCH"
                    responses[case.case_id] = {
                        "case_id": case.case_id,
                        "raw_output": None,
                        "latency_ms": None,
                        "provider_status": None,
                        "provider_id": None,
                        "model_id": None,
                        "token_usage": None,
                        "valid_output": False,
                        "error": {
                            "error_type": error_type,
                            "transport_status": None,
                            "http_status": None,
                        },
                    }
                    run_status = "FAILED_CONFIGURATION"
                    qualification_eligible = False
                    qualification_gates_applicable = False
                    break
                
                responses[case.case_id] = {
                    "case_id": case.case_id,
                    "raw_output": result.raw_output,
                    "latency_ms": result.latency_ms,
                    "provider_status": result.provider_status,
                    "provider_id": result.provider_id,
                    "model_id": result.model_id,
                    "provider_reported_model": result.provider_reported_model,
                    "requested_provider": config.provider,
                    "requested_model": config.model,
                    "token_usage": result.token_usage,
                    # Determine valid_output based on strict parser validity
                    # We must parse to determine if output is valid
                    "valid_output": True,  # Will be updated below
                    "error": None,
                }
                
                # Check if raw_output passes the strict parser
                from product_intelligence.evaluation.semantic.evaluator import (
                    parse_raw_output,
                    RawOutputParseError,
                )
                try:
                    parse_raw_output(result.raw_output)
                    # Output is valid
                except RawOutputParseError:
                    # Output doesn't parse - mark as invalid
                    responses[case.case_id]["valid_output"] = False
            elif isinstance(result, TransportFailure):
                # Record the failed case
                responses[case.case_id] = {
                    "case_id": case.case_id,
                    "raw_output": None,
                    "latency_ms": None,
                    "provider_status": result.transport_status,
                    "provider_id": None,
                    "model_id": None,
                    "provider_reported_model": None,
                    "requested_provider": config.provider,
                    "requested_model": config.model,
                    "token_usage": None,
                    "valid_output": False,
                    "error": {
                        "error_type": result.error_type,
                        "transport_status": result.transport_status,
                        "http_status": result.http_status,
                    },
                }
                
                # Check if this is a RUN-FATAL error
                from product_intelligence.evaluation.semantic.transport import RUN_FATAL_ERROR_TYPES
                
                if result.error_type in RUN_FATAL_ERROR_TYPES:
                    # Abort the run immediately
                    if result.error_type in ("AUTHENTICATION_FAILED", "MODEL_NOT_FOUND", 
                                             "MODEL_IDENTITY_MISMATCH", "UNSUPPORTED_PARAMETER",
                                             "INVALID_REQUEST_CONFIGURATION"):
                        run_status = "FAILED_CONFIGURATION"
                    else:  # RATE_LIMITED, PROVIDER_UNAVAILABLE
                        run_status = "FAILED_PROVIDER"
                    
                    qualification_eligible = False
                    qualification_gates_applicable = False
                    
                    # Stop processing further cases
                    break

        # Import responses (parses and validates raw outputs)
        parsed_responses = self._parse_responses(
            responses,
            case_ids,
        )

        # Evaluate
        evaluation_result = self._evaluator(self._corpus, parsed_responses)

        # Compute hashes using actual content
        corpus_sha256 = _compute_corpus_sha256(self._corpus)
        prompt_sha256 = _compute_prompt_sha256(cases, config)

        # Build manifest
        finish_time = datetime.now(timezone.utc)
        manifest = _build_manifest(
            config=config,
            corpus=self._corpus,
            case_ids=case_ids,
            prompt_version="1.0",
            corpus_sha256=corpus_sha256,
            prompt_sha256=prompt_sha256,
            start_time=start_time,
            finish_time=finish_time,
            run_status=run_status,
            qualification_eligible=qualification_eligible,
            qualification_gates_applicable=qualification_gates_applicable,
        )

        return RunResult(
            config=config,
            corpus=self._corpus,
            responses=responses,
            evaluation_result=evaluation_result,
            manifest=manifest,
            run_timestamp=start_time,
        )

    def _select_case_ids(self, case_selection: str) -> tuple[str, ...]:
        """Select case IDs based on selection mode.
        
        Returns a tuple (ordered, deterministic) rather than frozenset.
        """
        if case_selection == "FULL":
            # Use corpus order (tuple order from loader)
            return tuple(c.case_id for c in self._corpus.cases)
        elif case_selection == "SMOKE":
            # Use explicit smoke case order
            return GPT_OSS_SMOKE_CASE_IDS
        else:
            raise ValueError(f"Invalid case_selection: {case_selection}")

    def _execute_single_request(
        self,
        prompt: SemanticPrompt,
        model: str,
        temperature: float,
        max_tokens: int,
        transport: SemanticModelTransport,
    ) -> TransportResult | TransportFailure:
        """Execute a single request."""
        return transport.complete(
            system_prompt=prompt.system_prompt,
            user_prompt=prompt.user_prompt,
            model=model,
            temperature=temperature,
            max_tokens=max_tokens,
        )

    def _parse_responses(
        self,
        responses: dict[str, dict[str, Any]],
        case_ids: frozenset[str],
    ) -> dict[str, dict[str, Any]]:
        """Parse responses for evaluation.

        Filters out transport failures for evaluation but keeps them
        in the raw responses.
        """
        from product_intelligence.evaluation.semantic.evaluator import (
            parse_raw_output,
            RawOutputParseError,
        )

        parsed: dict[str, dict[str, Any]] = {}
        for case_id, record in responses.items():
            if not record.get("valid_output", False):
                continue  # Skip transport failures
            raw_output = record.get("raw_output")
            if raw_output is None:
                continue
            try:
                parsed_output = parse_raw_output(raw_output)
                parsed[case_id] = parsed_output
            except RawOutputParseError:
                # Invalid output format - skip for evaluation
                continue

        return parsed

    def save_run(
        self,
        run_result: RunResult,
        output_dir: str | Path | None = None,
    ) -> Path:
        """Save run artifacts to directory.

        Creates:
        - manifest.json
        - responses.jsonl
        - evaluation.json
        - summary.md

        Args:
            run_result: Result from benchmark run
            output_dir: Output directory (optional, uses config default)

        Returns:
            Path to output directory

        Raises:
            ValueError: If path would escape the output directory
        """
        if output_dir is None:
            output_dir = run_result.config.output_dir

        if output_dir is None:
            # Default to semantic_benchmark_runs/ under project root
            output_dir = Path("semantic_benchmark_runs")

        # Create run directory with filesystem-safe naming
        output_dir = Path(output_dir).resolve()
        provider_model_safe = _make_filesystem_safe(f"{run_result.config.provider}/{run_result.config.model}")
        run_dir = output_dir / f"{run_result.run_timestamp.strftime('%Y%m%dT%H%M%S')}__{provider_model_safe}"

        # Validate path safety - run_dir must be inside output_dir
        if not _validate_path_safety(run_dir, output_dir):
            raise ValueError(
                f"Run directory {run_dir} would escape output directory {output_dir}"
            )

        run_dir.mkdir(parents=True, exist_ok=True)

        # Save manifest
        manifest_path = run_dir / "manifest.json"
        with open(manifest_path, "w", encoding="utf-8") as f:
            json.dump(run_result.manifest, f, indent=2)

        # Save responses as JSONL
        responses_path = run_dir / "responses.jsonl"
        with open(responses_path, "w", encoding="utf-8") as f:
            for case_id, record in run_result.responses.items():
                f.write(json.dumps(record, ensure_ascii=False) + "\n")

        # Save evaluation results
        evaluation_path = run_dir / "evaluation.json"
        # For SMOKE, compute evaluation from actual responses; for FULL use evaluator
        if run_result.config.case_selection == "SMOKE":
            evaluation_data = self._build_smoke_evaluation(run_result)
        else:
            evaluation_data = self._evaluation_to_dict(run_result.evaluation_result, run_result.config.case_selection)
        with open(evaluation_path, "w", encoding="utf-8") as f:
            json.dump(evaluation_data, f, indent=2)

        # Generate and save summary
        summary_path = run_dir / "summary.md"
        summary = self._generate_summary(run_result)
        with open(summary_path, "w", encoding="utf-8") as f:
            f.write(summary)

        return run_dir

    def _build_smoke_evaluation(self, run_result: RunResult) -> dict[str, Any]:
        """Build SMOKE-specific evaluation artifact.
        
        SMOKE is NOT a 64-case qualification. It's a 5-case runtime screen.
        Evaluation is computed directly from attempted cases, not from
        the frozen full-corpus evaluator.
        
        Args:
            run_result: Result from benchmark run
            
        Returns:
            SMOKE-specific evaluation dictionary
        """
        case_ids = run_result.manifest["case_ids"]
        attempted_case_count = len(case_ids)
        
        # Count valid responses among attempted cases
        valid_response_count = 0
        for case_id in case_ids:
            record = run_result.responses.get(case_id, {})
            if record.get("valid_output", False):
                valid_response_count += 1
        
        invalid_response_count = attempted_case_count - valid_response_count
        valid_output_rate = valid_response_count / attempted_case_count if attempted_case_count > 0 else 0.0
        
        return {
            "case_selection": "SMOKE",
            "attempted_case_count": attempted_case_count,
            "valid_response_count": valid_response_count,
            "invalid_response_count": invalid_response_count,
            "valid_output_rate": valid_output_rate,
            "qualification_eligible": False,
            "qualification_gates_applicable": False,
            "hard_gates": None,
        }

    def _evaluation_to_dict(self, evaluation_result: Any, case_selection: str) -> dict[str, Any]:
        """Convert evaluation result to dictionary.
        
        For SMOKE runs, hard_gates is null since qualification gates don't apply.
        For FULL runs, normal evaluation metrics/gates are included.
        
        Args:
            evaluation_result: Evaluation result from evaluator
            case_selection: 'FULL' or 'SMOKE'
            
        Returns:
            Dictionary for evaluation.json
        """
        result = {
            "total_corpus_cases": evaluation_result.total_corpus_cases,
            "valid_response_count": evaluation_result.valid_response_count,
            "invalid_or_missing_count": evaluation_result.invalid_or_missing_count,
            "valid_output_rate": evaluation_result.valid_output_rate,
            "decision_accuracy": evaluation_result.decision_accuracy,
            "match_precision": evaluation_result.match_precision,
            "match_recall": evaluation_result.match_recall,
            "false_match_count": evaluation_result.false_match_count,
            "false_match_rate": evaluation_result.false_match_rate,
            "safety_cost": evaluation_result.safety_cost,
            "authority_safety_probes_passed": evaluation_result.authority_safety_probes_passed,
        }
        
        # Only include gates for FULL runs; SMOKE has no hard gates applicable
        if case_selection == "FULL":
            result["gates_passed"] = evaluation_result.gates_passed
        else:
            result["hard_gates"] = None
            
        return result

    def _generate_summary(self, run_result: RunResult) -> str:
        """Generate human-readable summary."""
        config = run_result.config
        er = run_result.evaluation_result
        case_selection = config.case_selection
        
        lines = [
            f"# Semantic Model Qualification Summary",
            f"",
            f"Provider: {config.provider}",
            f"Model: {config.model}",
            f"Role: {run_result.manifest.get('role', 'unknown')}",
            f"Prompt version: 1.0",
            f"Corpus version: {run_result.corpus.corpus_version}",
            f"Cases attempted: {len(run_result.manifest['case_ids'])}",
            f"Valid output rate: {er.valid_output_rate:.2%}",
            f"",
            f"## PRIMARY METRICS",
            f"",
            f"**Accuracy**: {er.decision_accuracy:.2%}",
            f"**MATCH precision**: {er.match_precision:.2%}",
            f"**MATCH recall**: {er.match_recall:.2%}",
            f"**False MATCH count**: {er.false_match_count}",
            f"**False MATCH rate**: {er.false_match_rate:.2%}",
            f"**Safety cost**: {er.safety_cost}",
            f"",
        ]
        
        # SMOKE runs don't have hard gates applicable
        if case_selection == "SMOKE":
            lines.extend([
                f"## RUNTIME SMOKE SCREEN",
                f"",
                f"NOT A FULL SEMANTIC QUALIFICATION",
                f"",
                f"Hard gates: N/A — FULL qualification only",
                f"",
                f"Smoke valid-output rate:",
                f"valid strict outputs / attempted smoke cases ({len(run_result.manifest['case_ids'])})",
                f"",
            ])
        else:
            lines.extend([
                f"## HARD GATES",
                f"",
            ])
            
            for gate, passed in er.gates_passed.items():
                status = "PASS" if passed else "FAIL"
                lines.append(f"- **{gate}**: {status}")
        
        lines.extend([
            f"",
            f"## CONFUSION MATRIX",
            f"",
            f"```\n",
            f"                   | Predicted MATCH | Predicted NO_MATCH | Predicted UNCERTAIN",
            f"---------------------------------------------------------------------------",
            f"Actual MATCH       | {er.confusion_matrix.M_M:15d} | {er.confusion_matrix.M_N:18d} | {er.confusion_matrix.M_U:19d}",
            f"Actual NO_MATCH    | {er.confusion_matrix.N_M:15d} | {er.confusion_matrix.N_N:18d} | {er.confusion_matrix.N_U:19d}",
            f"Actual UNCERTAIN   | {er.confusion_matrix.U_M:15d} | {er.confusion_matrix.U_N:18d} | {er.confusion_matrix.U_U:19d}",
            f"```",
            f"",
            f"## INCORRECT CASES",
            f"",
        ])
        
        # Group incorrect cases by error type
        incorrect = self._collect_incorrect_cases(run_result)
        
        for error_type, cases in incorrect.items():
            if cases:
                lines.append(f"### {error_type}")
                lines.append("")
                for case_id, expected, actual in cases:
                    lines.append(f"- **{case_id}**: expected={expected}, actual={actual}")
                lines.append("")
        
        return "\n".join(lines)

    def _collect_incorrect_cases(
        self,
        run_result: RunResult,
    ) -> dict[str, list[tuple[str, str, str]]]:
        """Collect incorrect cases grouped by error type."""
        # This would use the confusion matrix to identify incorrect predictions
        # For now, return empty structure
        return {}


def run_benchmark(
    provider: str,
    model: str,
    case_selection: str = "FULL",
    output_dir: str | Path | None = None,
    temperature: float = 0.0,
    max_tokens: int = 1024,
    *,
    transport: SemanticModelTransport | None = None,
) -> RunResult:
    """Convenience function to run one benchmark.

    Args:
        provider: Provider name (e.g., 'amax', 'vllm-262k')
        model: Model name
        case_selection: 'FULL' or 'SMOKE'
        output_dir: Output directory (optional)
        temperature: Temperature setting (default: 0.0)
        max_tokens: Max tokens (default: 1024)
        transport: Custom transport (optional)

    Returns:
        RunResult with all artifacts
    """
    config = BenchmarkRunConfig(
        provider=provider,
        model=model,
        case_selection=case_selection,
        transport=transport or get_openai_transport_for_provider(provider),
        temperature=temperature,
        max_tokens=max_tokens,
        output_dir=output_dir,
    )

    runner = SemanticBenchmarkRunner()
    result = runner.run(config)

    if output_dir is None:
        runner.save_run(result)
    else:
        runner.save_run(result, output_dir=output_dir)

    return result
