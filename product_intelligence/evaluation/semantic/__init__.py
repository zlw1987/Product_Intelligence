"""Semantic match qualification infrastructure (PRODUCT-INTEL.SEMANTIC).

This package provides offline evaluation infrastructure for semantic
model qualification. No live model integration is required for this phase.

Submodules:
    vocabulary     - Semantic decision vocabulary
    loader         - Corpus loader
    prompt         - Versioned prompt template
    evaluator      - Metrics computation
    transport      - Model transport layer (fake and HTTP)
    model_catalog  - Model catalog
    runner         - Benchmark runner
    cli            - CLI interface
    comparison     - Offline comparison utility
"""

from product_intelligence.evaluation.semantic.vocabulary import (
    SemanticDecision,
    ConfidenceLevel,
    SemanticMatchResponse,
    SemanticCaseClass,
)
from product_intelligence.evaluation.semantic.loader import (
    SemanticCorpus,
    SemanticMatchCase,
    SemanticMatchTarget,
    SemanticMatchCandidate,
    load_corpus,
    validate_response,
)
from product_intelligence.evaluation.semantic.prompt import (
    build_prompt,
    export_corpus_to_jsonl,
    import_results_from_jsonl,
)
from product_intelligence.evaluation.semantic.evaluator import (
    evaluate_responses,
    parse_raw_output,
    RawOutputParseError,
)
from product_intelligence.evaluation.semantic.transport import (
    SemanticModelTransport,
    FakeSemanticModelTransport,
    OpenAISemanticTransport,
    TransportResult,
    TransportFailure,
    get_openai_transport_for_provider,
)
from product_intelligence.evaluation.semantic.model_catalog import (
    QualificationModel,
    FULL_QUALIFICATION_MODELS,
    SMOKE_ONLY_MODELS,
    SKIP_MODELS,
    ALL_MODELS,
    GPT_OSS_SMOKE_CASE_IDS,
    get_model_by_provider_model,
    is_smoke_model,
)
from product_intelligence.evaluation.semantic.runner import (
    SemanticBenchmarkRunner,
    BenchmarkRunConfig,
    RunResult,
    run_benchmark,
)
from product_intelligence.evaluation.semantic.comparison import (
    load_run_manifest,
    RunComparison,
    compare_benchmark_runs,
    generate_leaderboard,
    verify_run_compatibility,
    filter_compatible_runs,
)

__all__ = [
    # Vocabulary
    "SemanticDecision",
    "ConfidenceLevel",
    "SemanticMatchResponse",
    "SemanticCaseClass",
    # Loader
    "SemanticCorpus",
    "SemanticMatchCase",
    "SemanticMatchTarget",
    "SemanticMatchCandidate",
    "load_corpus",
    "validate_response",
    # Prompt
    "build_prompt",
    "export_corpus_to_jsonl",
    "import_results_from_jsonl",
    # Evaluator
    "evaluate_responses",
    "parse_raw_output",
    "RawOutputParseError",
    # Transport
    "SemanticModelTransport",
    "FakeSemanticModelTransport",
    "OpenAISemanticTransport",
    "TransportResult",
    "TransportFailure",
    "get_openai_transport_for_provider",
    # Model catalog
    "QualificationModel",
    "FULL_QUALIFICATION_MODELS",
    "SMOKE_ONLY_MODELS",
    "SKIP_MODELS",
    "ALL_MODELS",
    "GPT_OSS_SMOKE_CASE_IDS",
    "get_model_by_provider_model",
    "is_smoke_model",
    # Runner
    "SemanticBenchmarkRunner",
    "BenchmarkRunConfig",
    "RunResult",
    "run_benchmark",
    # Comparison
    "load_run_manifest",
    "RunComparison",
    "compare_benchmark_runs",
    "generate_leaderboard",
    "verify_run_compatibility",
    "filter_compatible_runs",
]
