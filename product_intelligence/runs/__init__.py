"""Persistent research-run lifecycle (PRODUCT-INTEL.1A).

This is the application/persistence layer for a research attempt. It is the
only place in the project that owns a durable `ResearchRun` record.

Why it is its own layer:

* `domain/` is stdlib-only contracts; a Django model there would break that
  boundary and the guard test that enforces it;
* `research/` is the caller-independent engine and must stay free of
  persistence concerns, so it can be reasoned about and tested without a
  database;
* `web/` is transport and presentation, and must not own the lifecycle — a run
  outlives the request that created it and is not tied to any caller.

The dependency direction runs one way: this package imports `domain`, never the
reverse.

Scope note: 1A persists the request and its lifecycle state. It performs no
research. There is no search, no LLM, no evidence store, no view, no URL, and
no background processing.
"""

from __future__ import annotations

from product_intelligence.runs.errors import (
    InvalidInitialResearchRunState,
    InvalidResearchRunTransition,
    ResearchRunLifecycleError,
    UnsupportedResearchRunStateChange,
)

__all__ = [
    "ALLOWED_TRANSITIONS",
    "ClaimExecutionFailed",
    "claim_execution",
    "complete_execution",
    "ExecutionDetailCode",
    "ExecutionEvidenceRecord",
    "ExecutionOutcome",
    "ExecutionStage",
    "InvalidInitialResearchRunState",
    "InvalidResearchRunTransition",
    "confirm_candidate",
    "reject_candidate",
    "undo_review",
    "CrossRunReviewError",
    "CandidateNotFoundError",
    "RunNotReviewableError",
    "ReviewConflictError",
    "retry_run",
    "ResearchRun",
    "ResearchRunLifecycleError",
    "TERMINAL_STATES",
    "UnsupportedResearchRunStateChange",
]

_MODEL_EXPORTS = frozenset({"ALLOWED_TRANSITIONS", "ResearchRun", "TERMINAL_STATES", "PriceIntelligenceSnapshot", "ExecutionEvidenceRecord", "AiAssistedReviewCandidate"})

# Evidence enums and primitives are pure Python (no Django import), so they can
# be exposed directly from this package without lazy loading.
_REVIEW_EXPORTS = frozenset({"confirm_candidate", "reject_candidate", "undo_review"})
_REVIEW_ERROR_EXPORTS = frozenset({"CrossRunReviewError", "CandidateNotFoundError", "RunNotReviewableError", "ReviewError", "ReviewConflictError", "InvalidCandidateError"})

_EVIDENCE_EXPORTS = frozenset({
    "ClaimExecutionFailed",
    "claim_execution",
    "complete_execution",
    "ExecutionDetailCode",
    "ExecutionOutcome",
    "ExecutionStage",
    "retry_run",
})


def __getattr__(name: str) -> object:
    """Expose the model, evidence enum, or execution primitive lazily.

    Importing this package must not require the Django app registry to be
    ready, so ``models`` is imported on first attribute access rather than at
    package import time. The error types and execution primitives have no such
    constraint and are imported directly. Evidence enums are also available
    from the runs.models package.
    """
    if name in _EVIDENCE_EXPORTS:
        # Check each name individually to find the right source
        if name == "ExecutionDetailCode":
            from product_intelligence.domain import ExecutionDetailCode
            return ExecutionDetailCode
        elif name == "ExecutionOutcome":
            from product_intelligence.domain import ExecutionOutcome
            return ExecutionOutcome
        elif name == "ExecutionStage":
            from product_intelligence.domain import ExecutionStage
            return ExecutionStage
        elif name == "ClaimExecutionFailed":
            from product_intelligence.runs import execution_claims
            return getattr(execution_claims, name)
        elif name == "complete_execution":
            from product_intelligence.runs import execution_claims
            return getattr(execution_claims, name)
        elif name == "retry_run":
            from product_intelligence.runs import execution_claims
            return getattr(execution_claims, name)
        elif name == "claim_execution":
            from product_intelligence.runs import execution_claims
            return getattr(execution_claims, name)
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")

    # Review service exports (HUMAN-REVIEW)
    if name in _REVIEW_EXPORTS:
        from product_intelligence.runs import ai_assisted_review
        return getattr(ai_assisted_review, name)

    # Review error exports (HUMAN-REVIEW)
    if name in _REVIEW_ERROR_EXPORTS:
        from product_intelligence.runs import ai_assisted_review
        return getattr(ai_assisted_review, name)

    if name in _MODEL_EXPORTS:
        # Import from runs.models (the main models.py file)
        from product_intelligence.runs import models

        return getattr(models, name)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
