"""Model catalog for semantic qualification (PRODUCT-INTEL.SEMANTIC.BENCHMARK).

This module defines the explicit model catalog for semantic model
qualification benchmarks.

No live model integration is required for this phase.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class ModelRole(str, Enum):
    """Role of a model in qualification."""

    PRIMARY_CANDIDATE = "primary_candidate"
    """Primary semantic candidate for full qualification."""

    LIGHTWEIGHT_GENERAL = "lightweight_general"
    """Lightweight/general candidate for comparison."""

    SMOKE_TEST = "smoke_test"
    """Runtime/reliability smoke candidate (limited cases only)."""

    SKIP_NON_GENERATIVE = "skip_non_generative"
    """Non-generative models (TTS, embeddings) - not benchmarked."""

    SMOKE_ONLY = "smoke_only"
    """Smoke-only model (not for full leaderboard)."""


@dataclass(frozen=True)
class QualificationModel:
    """Model entry in the qualification catalog."""

    provider: str
    model: str
    role: ModelRole

    @property
    def provider_model_id(self) -> str:
        """Return provider/model ID for transport."""
        return f"{self.provider}/{self.model}"

    @property
    def is_generative(self) -> bool:
        """Return True if this model is eligible for generative qualification."""
        return self.role not in (
            ModelRole.SKIP_NON_GENERATIVE,
            ModelRole.SMOKE_ONLY,
        )

    @property
    def is_smoke_candidate(self) -> bool:
        """Return True if this model is eligible for smoke-only runs."""
        return self.role in (ModelRole.SMOKE_TEST, ModelRole.SMOKE_ONLY)

    @property
    def is_primary_candidate(self) -> bool:
        """Return True if this model is a primary semantic candidate."""
        return self.role in (
            ModelRole.PRIMARY_CANDIDATE,
            ModelRole.LIGHTWEIGHT_GENERAL,
        )


# ---------------------------------------------------------------------------
# Full qualification models (8 models)
# ---------------------------------------------------------------------------

FULL_QUALIFICATION_MODELS = (
    QualificationModel(
        provider="vllm-262k",
        model="Qwen3.6-27B-262K",
        role=ModelRole.PRIMARY_CANDIDATE,
    ),
    QualificationModel(
        provider="amax",
        model="minimax-m2.7",
        role=ModelRole.PRIMARY_CANDIDATE,
    ),
    QualificationModel(
        provider="amax",
        model="minimax-m2.7-thinking",
        role=ModelRole.PRIMARY_CANDIDATE,
    ),
    QualificationModel(
        provider="amax",
        model="nemotron-3-super",
        role=ModelRole.PRIMARY_CANDIDATE,
    ),
    QualificationModel(
        provider="amax",
        model="google/gemma-4-26B-A4B-it",
        role=ModelRole.PRIMARY_CANDIDATE,
    ),
    QualificationModel(
        provider="amax",
        model="mistral-small-4",
        role=ModelRole.PRIMARY_CANDIDATE,
    ),
    QualificationModel(
        provider="amax",
        model="mistral-small-24b-instruct-2501",
        role=ModelRole.LIGHTWEIGHT_GENERAL,
    ),
    QualificationModel(
        provider="amax",
        model="qwen3-coder-next",
        role=ModelRole.PRIMARY_CANDIDATE,
    ),
)


# ---------------------------------------------------------------------------
# Smoke-only models (1 model)
# ---------------------------------------------------------------------------

SMOKE_ONLY_MODELS = (
    QualificationModel(
        provider="amax",
        model="gpt-oss-20b",
        role=ModelRole.SMOKE_TEST,
    ),
)


# ---------------------------------------------------------------------------
# Skip models (non-generative)
# ---------------------------------------------------------------------------

SKIP_MODELS = (
    QualificationModel(
        provider="amax",
        model="kokoro-tts",
        role=ModelRole.SKIP_NON_GENERATIVE,
    ),
    QualificationModel(
        provider="amax",
        model="e5-mistral-7b-instruct-embed",
        role=ModelRole.SKIP_NON_GENERATIVE,
    ),
    QualificationModel(
        provider="amax",
        model="qwen3-embedding-8b",
        role=ModelRole.SKIP_NON_GENERATIVE,
    ),
)


# ---------------------------------------------------------------------------
# All models for catalog purposes
# ---------------------------------------------------------------------------

ALL_MODELS = FULL_QUALIFICATION_MODELS + SMOKE_ONLY_MODELS + SKIP_MODELS


# ---------------------------------------------------------------------------
# GPT-OSS smoke case IDs
# ---------------------------------------------------------------------------

GPT_OSS_SMOKE_CASE_IDS = (
    "SMQ-0001",
    "SMQ-0002",
    "SMQ-0004",
    "SMQ-0005",
    "SMQ-0032",
)


# ---------------------------------------------------------------------------
# Helper functions
# ---------------------------------------------------------------------------


def get_model_by_provider_model(provider: str, model: str) -> QualificationModel | None:
    """Get model entry by provider and exact model name.

    Args:
        provider: Provider name
        model: Exact model name

    Returns:
        QualificationModel if found, None otherwise
    """
    for m in ALL_MODELS:
        if m.provider == provider and m.model == model:
            return m
    return None


def get_full_qualification_models() -> tuple[QualificationModel, ...]:
    """Return all models eligible for full qualification.

    These are PRIMARY_CANDIDATE and LIGHTWEIGHT_GENERAL models only.
    SMOKE_TEST models are NOT eligible for full runs.
    """
    return tuple(
        m for m in ALL_MODELS
        if m.role in (ModelRole.PRIMARY_CANDIDATE, ModelRole.LIGHTWEIGHT_GENERAL)
    )


def get_smoke_test_models() -> tuple[QualificationModel, ...]:
    """Return all models eligible for smoke runs (SMOKE_TEST role)."""
    return tuple(m for m in ALL_MODELS if m.role == ModelRole.SMOKE_TEST)


def get_smoke_only_models() -> tuple[QualificationModel, ...]:
    """Return models that should only run in smoke mode."""
    return SMOKE_ONLY_MODELS


def get_skip_models() -> tuple[QualificationModel, ...]:
    """Return models that should not be benchmarked."""
    return SKIP_MODELS


def is_smoke_model(provider: str, model: str) -> bool:
    """Check if a model is eligible for smoke runs.

    Returns True if the model has SMOKE_TEST role.
    Returns False for FULL qualification models (they must run FULL).
    Returns False for SKIP models (they cannot run at all).
    """
    model_obj = get_model_by_provider_model(provider, model)
    if model_obj is None:
        return False
    return model_obj.role == ModelRole.SMOKE_TEST


def is_full_qualification_model(provider: str, model: str) -> bool:
    """Check if a model is eligible for FULL qualification runs.

    Returns True only for PRIMARY_CANDIDATE or LIGHTWEIGHT_GENERAL roles.
    """
    model_obj = get_model_by_provider_model(provider, model)
    if model_obj is None:
        return False
    return model_obj.role in (ModelRole.PRIMARY_CANDIDATE, ModelRole.LIGHTWEIGHT_GENERAL)


def can_run_full(provider: str, model: str) -> bool:
    """Check if a model may run FULL qualification.

    Returns True only for known FULL models. Unknown models return False.
    """
    return is_full_qualification_model(provider, model)


def can_run_smoke(provider: str, model: str) -> bool:
    """Check if a model may run SMOKE qualification.

    Returns True only for known SMOKE_TEST models.
    Unknown models return False (fail closed).
    SKIP models return False.
    """
    model_obj = get_model_by_provider_model(provider, model)
    if model_obj is None:
        return False
    return model_obj.role == ModelRole.SMOKE_TEST


def is_known_model(provider: str, model: str) -> bool:
    """Check if a model is in the catalog (known model)."""
    return get_model_by_provider_model(provider, model) is not None


def is_skip_model(provider: str, model: str) -> bool:
    """Check if a model should not be benchmarked (SKIP_NON_GENERATIVE)."""
    model_obj = get_model_by_provider_model(provider, model)
    if model_obj is None:
        return False
    return model_obj.role == ModelRole.SKIP_NON_GENERATIVE
