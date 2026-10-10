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

PRODUCT-INTEL.SEMANTIC-AUTHORITY-V2-S2-C added the FINAL Semantic V2
contract surface alongside the frozen V1 contract (V1 is unchanged):

* ``semantic.contract_v2`` — the final Prompt V2 (``2.0``): the frozen
  system prompt (commercial semantic equivalence task; the explicit
  NOT-asked-to rules; the identifier / provenance / sales-unit / conflict-
  class rules), the deterministic user-prompt renderer over the exact
  ``SemanticMatchCaseV2`` input, and ``build_semantic_prompt_v2``;
* ``semantic.runtime_v2`` — the V2 runtime on the V2 pinned route (the
  currently frozen qualified route identities, carried as V2 contract
  data): primary once, fallback on EXECUTION FAILURE only, model identity
  verification, strict structured V2 output parsing, bounded provenance,
  and the explicit ``V2_AUTHORITY_QUALIFIED = False`` qualification-
  boundary marker (the V2 route is NOT qualified for the new contract;
  Qualification V3 comes after S2-C).
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
from product_intelligence.semantic.contract_v2 import (
    SEMANTIC_PROMPT_VERSION_V2,
    SYSTEM_PROMPT_V2,
    SemanticPromptV2,
    build_semantic_prompt_v2,
    render_v2_user_prompt,
)
from product_intelligence.semantic.contract_v2_1 import (
    SEMANTIC_PROMPT_VERSION_V2_1,
    SYSTEM_PROMPT_V2_1,
    SemanticPromptV2_1,
    V2_1_CONTRACT_BINDING,
    build_semantic_prompt_v2_1,
    render_v2_1_user_prompt,
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
from product_intelligence.semantic.runtime_v2 import (
    FALLBACK_MODEL_V2,
    FALLBACK_PROVIDER_V2,
    PRIMARY_MODEL_V2,
    PRIMARY_PROVIDER_V2,
    SEMANTIC_MAX_TOKENS_V2,
    SEMANTIC_TEMPERATURE_V2,
    V2_AUTHORITY_QUALIFIED,
    SemanticRuntimeConfigV2,
    SemanticRuntimeResultV2,
    SemanticRuntimeV2,
    get_default_runtime_v2,
    reset_default_runtime_v2,
    validate_runtime_config_v2,
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
    # Final Semantic V2 contract (S2-C): Prompt V2 + V2 runtime on the V2
    # pinned route (currently frozen qualified route identities; NOT
    # qualified for the new contract — V2_AUTHORITY_QUALIFIED is False).
    "SEMANTIC_PROMPT_VERSION_V2",
    "SYSTEM_PROMPT_V2",
    "SemanticPromptV2",
    "build_semantic_prompt_v2",
    "render_v2_user_prompt",
    # Separately versioned Prompt 2.1 (Q3-B5-P1; the approved Q3-B3-FU2
    # design, revision 2). The frozen 2.0 surface above is byte-untouched;
    # the 2.1 binding carries the separately versioned FU3 authority
    # token (Q3-B4 AD-Q3B4-5) and is qualification-record identity only -
    # the live runtime and the live V2 persistence adapter remain pinned
    # to the frozen 2.0 binding.
    "SEMANTIC_PROMPT_VERSION_V2_1",
    "SYSTEM_PROMPT_V2_1",
    "SemanticPromptV2_1",
    "V2_1_CONTRACT_BINDING",
    "build_semantic_prompt_v2_1",
    "render_v2_1_user_prompt",
    "PRIMARY_PROVIDER_V2",
    "PRIMARY_MODEL_V2",
    "FALLBACK_PROVIDER_V2",
    "FALLBACK_MODEL_V2",
    "SEMANTIC_TEMPERATURE_V2",
    "SEMANTIC_MAX_TOKENS_V2",
    "V2_AUTHORITY_QUALIFIED",
    "SemanticRuntimeV2",
    "SemanticRuntimeConfigV2",
    "SemanticRuntimeResultV2",
    "validate_runtime_config_v2",
    "get_default_runtime_v2",
    "reset_default_runtime_v2",
]
