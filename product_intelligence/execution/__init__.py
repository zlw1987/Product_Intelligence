"""Research execution orchestration (PRODUCT-INTEL.4C-B).

This package coordinates the deterministic pipeline:

    ResearchRequest  ->  claim_execution  ->  search  ->  fetch  ->  extract
                                         ->  normalize  ->  match  ->  aggregate
                                         ->  snapshot  ->  terminal state

Key constraints:
* Maximum ONE paid search call per ResearchRun (enforced by claim_execution)
* Candidate-level fetch/extract failures do NOT fail the whole run
* Deterministic primitives only - no LLM, no guessing
* Evidence-first: every conclusion traces to preserved evidence

Dependency direction:
    domain
        independent

    research
        deterministic / Django-independent

    providers
        external I/O adapters/contracts

    runs
        lifecycle and persistence

    execution  <-  domain, research, providers, runs
        orchestration

    web
        presentation/composition only

Execution must NOT import web. Research must NOT import runs/providers.
"""

from __future__ import annotations

from product_intelligence.execution.orchestration import (
    execute_research_run,
    ExecutionResult,
    ExecutionError,
)

__all__ = [
    "execute_research_run",
    "ExecutionResult",
    "ExecutionError",
]
