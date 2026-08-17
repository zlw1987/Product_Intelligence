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
    "InvalidInitialResearchRunState",
    "InvalidResearchRunTransition",
    "ResearchRun",
    "ResearchRunLifecycleError",
    "TERMINAL_STATES",
    "UnsupportedResearchRunStateChange",
]

_MODEL_EXPORTS = frozenset({"ALLOWED_TRANSITIONS", "ResearchRun", "TERMINAL_STATES"})


def __getattr__(name: str) -> object:
    """Expose the model lazily.

    Importing this package must not require the Django app registry to be
    ready, so ``models`` is imported on first attribute access rather than at
    package import time. The error types have no such constraint and are
    imported directly.
    """
    if name in _MODEL_EXPORTS:
        from product_intelligence.runs import models

        return getattr(models, name)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
