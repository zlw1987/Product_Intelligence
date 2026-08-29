"""Production semantic runtime package (PRODUCT-INTEL.SEMANTIC).

The production semantic runtime and the neutral semantic contract and
transport that both production and the evaluation harness share.

``product_intelligence.semantic.contract`` is the SINGLE SOURCE OF TRUTH for
prompt v1.1, the decision vocabulary, the response schema, and the strict
parser/validator. ``product_intelligence.semantic.transport`` is the SINGLE
SOURCE OF TRUTH for the transport abstraction (``SemanticModelTransport``,
``FakeSemanticModelTransport``, ``OpenAISemanticTransport``,
``TransportResult``, ``TransportFailure``,
``get_openai_transport_for_provider``). The evaluation harness re-exports both;
it keeps no second copy of either.

Import purity (enforced by ``tests/semantic/test_runtime_boundaries.py``):
importing this package must not import the evaluation harness, Django, or any
network client (``requests``, ``urllib``, ``urllib3``, ``httpx``, ``aiohttp``).
The live transport (``semantic.transport``, itself neutral) is resolved
lazily, only when a live transport is actually constructed.

Dependency direction::

    semantic.runtime  <-  semantic.contract   (neutral: prompt, parser, vocabulary)
    semantic.runtime  ->  semantic.transport  (lazily; neutral, not evaluation)

No production semantic source imports ``product_intelligence.evaluation`` at
all. This runtime is the ONLY way production calls a semantic model. Callers
never touch transport details directly.
"""

from product_intelligence.semantic.contract import (
    SEMANTIC_PROMPT_VERSION,
    ConfidenceLevel,
    RawOutputParseError,
    SemanticDecision,
    SemanticMatchResponse,
    SemanticPrompt,
    build_prompt,
    parse_raw_output,
    validate_response,
)
from product_intelligence.semantic.runtime import (
    FALLBACK_MODEL,
    FALLBACK_PROVIDER,
    PRIMARY_FALLBACK_ELIGIBLE_ERRORS,
    PRIMARY_MODEL,
    PRIMARY_NON_FALLBACK_ERRORS,
    PRIMARY_PROVIDER,
    SEMANTIC_MAX_TOKENS,
    SEMANTIC_TEMPERATURE,
    SemanticAttempt,
    SemanticAttemptStatus,
    SemanticRuntime,
    SemanticRuntimeConfig,
    SemanticRuntimeConfigError,
    SemanticRuntimeErrorType,
    SemanticRuntimeFallbackReason,
    SemanticRuntimeResult,
    get_default_runtime,
    reset_default_runtime,
    validate_runtime_config,
)

__all__ = [
    # Neutral contract (canonical)
    "SEMANTIC_PROMPT_VERSION",
    "ConfidenceLevel",
    "RawOutputParseError",
    "SemanticDecision",
    "SemanticMatchResponse",
    "SemanticPrompt",
    "build_prompt",
    "parse_raw_output",
    "validate_response",
    # Pinned qualified route
    "PRIMARY_PROVIDER",
    "PRIMARY_MODEL",
    "FALLBACK_PROVIDER",
    "FALLBACK_MODEL",
    "SEMANTIC_TEMPERATURE",
    "SEMANTIC_MAX_TOKENS",
    "PRIMARY_FALLBACK_ELIGIBLE_ERRORS",
    "PRIMARY_NON_FALLBACK_ERRORS",
    # Runtime
    "SemanticRuntime",
    "SemanticRuntimeConfig",
    "SemanticRuntimeConfigError",
    "SemanticRuntimeResult",
    "SemanticRuntimeErrorType",
    "SemanticRuntimeFallbackReason",
    "SemanticAttempt",
    "SemanticAttemptStatus",
    "validate_runtime_config",
    "get_default_runtime",
    "reset_default_runtime",
]
