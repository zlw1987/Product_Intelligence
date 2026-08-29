"""Semantic model transport layer (PRODUCT-INTEL.SEMANTIC.BENCHMARK).

This module provides transport abstractions for calling semantic model
providers via OpenAI-compatible chat completions API.

Single source of truth (FU3A2B)
--------------------------------
The transport implementation is NOT defined here. It lives in
``product_intelligence.semantic.transport``, the neutral production module,
and this file re-exports the exact same objects so the evaluation harness and
production share one implementation rather than two copies that could drift.

The public API of this module (every name below) is unchanged: existing
imports of ``product_intelligence.evaluation.semantic.transport`` continue to
work exactly as before.

No live model integration is required for this phase.
All tests use fake transports.
"""

from __future__ import annotations

# Canonical implementation - re-exported, never re-implemented.
from product_intelligence.semantic.transport import (
    ALL_ERROR_TYPES,
    CASE_LOCAL_ERROR_TYPES,
    NETWORK_ERROR_TYPES,
    RESPONSE_ERROR_TYPES,
    RUN_FATAL_ERROR_TYPES,
    FakeSemanticModelTransport,
    OpenAISemanticTransport,
    SemanticModelTransport,
    TransportFailure,
    TransportResult,
    _classify_http_error,
    _HTTPResponse,
    get_openai_transport_for_provider,
)

__all__ = [
    "RUN_FATAL_ERROR_TYPES",
    "CASE_LOCAL_ERROR_TYPES",
    "NETWORK_ERROR_TYPES",
    "RESPONSE_ERROR_TYPES",
    "ALL_ERROR_TYPES",
    "TransportResult",
    "TransportFailure",
    "SemanticModelTransport",
    "FakeSemanticModelTransport",
    "OpenAISemanticTransport",
    "get_openai_transport_for_provider",
]
