# Product Intelligence — Current Status

## Current state

**PRODUCT-INTEL.PILOT-UX — Semantic qualification APPROVED/FROZEN;
FU3A Production Semantic Runtime Contract APPROVED/FROZEN;
FU3B Semantic Execution Integration APPROVED/FROZEN;
HUMAN-REVIEW Human Review for AI-Assisted Matches APPROVED/FROZEN.**

Semantic qualification is APPROVED AND FROZEN:
- Semantic qualification corpus, prompt v1.1, evaluator mathematics,
  qualification thresholds, expected decisions, and safety gates approved
- Prompt v1.1 FULL SHA256: f50e5584659f953ce73a97ccc8bc1ff487fbeeb37e2e0a72e52210613aeab1ff
- Corpus SHA256: 3c21d6fcd4eefa5cc383792abfd9308bd5c03315834c8ffdffd0f6a2b3619ca1

**Two models passed the formal FULL qualification gates.** They are the
qualified production route:

| Role | Provider | Model |
| --- | --- | --- |
| PRIMARY | `amax` | `nemotron-3-super` |
| FALLBACK | `vllm-262k` | `Qwen3.6-27B-262K` |

Generation settings are fixed at `temperature=0.0`, `max_tokens=32768`.

FU3A — Production Semantic Runtime Contract — **APPROVED / FROZEN**
(corrective history: FU3A2B/C/D/E/F; FU3A2F was the final corrective pass —
ChatGPT's review of the final FU3A2F `runtime.py` and `test_runtime.py`
approved the contract):

FU3B — Semantic execution integration — **APPROVED / FROZEN**
(corrective history: FU3B was the execution-wiring pass; MiniMax M2.7 Thinking
independently reviewed the final FU3B implementation and found no production-code
or safety-contract blocker; ChatGPT performed the final approval/freeze review):
- `product_intelligence/semantic/contract.py` is the single source of truth for
  prompt v1.1, the decision vocabulary, the response schema, and the strict
  parser/validator. The evaluation harness re-exports those same objects;
  production does not depend on `evaluation.semantic.*`.
- `product_intelligence/semantic/transport.py` is the single source of truth
  for the transport implementation (HTTP call, error classification,
  `SemanticModelTransport`/`OpenAISemanticTransport`/`FakeSemanticModelTransport`);
  `evaluation/semantic/transport.py` re-exports it rather than keeping a copy.
- `product_intelligence/semantic/runtime.py` pins the qualified route
  (validation rejects any other provider/model/temperature/max_tokens before a
  transport call — temperature is checked by exact type, `type(x) is float`,
  so `0`/`False` are rejected even though numerically equal to `0.0`), falls
  back on an EXPLICIT allowlist of execution failures, requires exact
  provider-reported model identity, records per-attempt provenance, and never
  converts a programming exception into a fallback.
- The fallback allowlist and error taxonomy are complete over every code the
  canonical transport can return (`INVALID_PROVIDER_RESPONSE` is fallback
  eligible like `MALFORMED_JSON`/`SCHEMA_INVALID`; `CASE_REJECTED` is a known,
  non-fallback-eligible code — neither is lost into `UNKNOWN_ERROR`).
- `SemanticRuntimeResult` fully self-validates: every typed field is checked
  by exact type (not merely truthy-equal), and a failure's `error_type` is
  mechanically bound to what its attempts actually recorded.
- Importing `product_intelligence.semantic` pulls in no evaluation module, no
  Django, and no network client. The live transport is resolved lazily.

**The frozen semantic runtime is wired into execution** behind the semantic integration boundary for explicitly eligible candidates. The frozen runtime exists
and is tested offline; it is called from the research pipeline through `evaluate_semantic_matches` — that
wiring was FU3B, now implemented and approved.

AI_ASSISTED_MATCH remains outside existing 4A aggregation.

A semantic MATCH is represented by:
    original ListingIdentityAssessment.decision == REJECTED
    +
    AiAssistedMatchResult.disposition == AI_ASSISTED_MATCH

There is no AI_ASSISTED_MATCH ListingIdentityAssessment.

Existing 4A sees the original deterministic REJECTED assessment and
excludes it as IDENTITY_NOT_ACCEPTED.

Only EvidenceDecision.ACCEPTED automatically enters 4A Machine Price.

## Project facts (already delivered outside repo)

- FoxPro launcher: **Manually integrated outside this repository — delivered,
  not pending.** The client code is maintained in the existing Visual FoxPro
  sales-order application. The server-side GET prefill contract is implemented
  and localhost UAT passed.
- 4C-B-FU corrective: Exact structural duplicate ListingObservation
  deduplication implemented in `execution/orchestration._deduplicate_exact_observations`.

## FU3B — Semantic execution integration

**APPROVED / FROZEN**

FU3B wires the frozen FU3A semantic runtime into real research execution:

- Deterministic matching remains first authority; deterministic `ACCEPTED` bypasses semantic
- Explicit `MPN_MISMATCH` bypasses semantic
- Semantic eligible:
  - `NO_EXPLICIT_MPN_EVIDENCE + TITLE_TEXT`
  - `NO_EXPLICIT_MPN_EVIDENCE + SKU_FIELD`
  - `PARTIAL_MPN_ONLY`
- Not semantic-enabled in FU3B:
  - `NO_EXPLICIT_MPN_EVIDENCE + NONE`
  - description-only / `UNDECIDED`
- Bounded semantic failure leaves run usable
- Programming/config exceptions propagate to existing catastrophic boundary
- AI-assisted matches retained in `ExecutionResult.ai_assisted_matches`
- `ai_assisted_match_count` is derived
- `AiAssistedMatchResult` mechanically binds provenance
- `SEMANTIC` execution evidence uses bounded controlled detail codes
- Migration 0005 is choices-only metadata
- `AI_ASSISTED_MATCH` remains entirely outside 4A
- `PriceIntelligenceSnapshot` remains deterministic-only

## Phase ownership

| Phase | Description | Status |
| --- | --- | --- |
| 4C-A | Execution ownership/lifecycle/evidence primitives | Implemented (frozen) |
| 4C-B | Backend research execution | Implemented (frozen) |
| 4C-B-FU | Exact duplicate deduplication | Implemented (frozen) |
| 4C-C | Web execution/retry integration | Implemented (frozen) |
| 5A | Structured external API | Not implemented |
| 5B | FoxPro launcher | Server-side implemented; client integrated outside repo, UAT passed |
| PILOT-UX | Pilot UX polish + semantic qualification | **FROZEN** |
| HUMAN-REVIEW | Human review for AI-assisted semantic matches | Implemented (frozen)
| 6A | Product Specification Framework | Implemented (review pending)
| SAP | SAP launcher integration | Future |


## Implementation snapshot

| Component | Package | Status |
| --- | --- | --- |
| Domain contracts + vocabularies | `domain/` | Implemented |
| Evaluation corpus + loader | `evaluation/` | Implemented |
| Semantic match corpus + evaluator | `evaluation/semantic/` | **Implemented (frozen)** |
| Semantic match prompt template v1.1 | `evaluation/semantic/prompt.py` | **Implemented (frozen)** |
| Semantic match export/import | `evaluation/semantic/` | **Implemented** |
| Semantic match transport | `evaluation/semantic/transport.py` | **Implemented** |
| Semantic match model catalog | `evaluation/semantic/model_catalog.py` | **Implemented** |
| Semantic match benchmark runner | `evaluation/semantic/runner.py` | **Implemented** |
| Semantic match CLI | `evaluation/semantic/cli.py` | **Implemented** |
| Semantic match comparison | `evaluation/semantic/comparison.py` | **Implemented** |
| Semantic match tests | `tests/evaluation/semantic/` | **Implemented (frozen)** |
| Semantic neutral contract (canonical) | `semantic/contract.py` | **Implemented (frozen, FU3A)** |
| Semantic neutral transport (canonical) | `semantic/transport.py` | **Implemented (frozen, FU3A)** |
| Semantic production runtime | `semantic/runtime.py` | **Implemented (frozen, FU3A)** |
| Semantic runtime tests | `tests/semantic/test_runtime.py` | **Implemented** |
| Semantic transport tests | `tests/semantic/test_transport.py` | **Implemented** |
| Semantic runtime boundaries | `tests/semantic/test_runtime_boundaries.py` | **Implemented** |
| Semantic contract sharing proof | `tests/semantic/test_contract_sharing.py` | **Implemented** |
| Semantic execution integration | `execution/semantic_integration.py` | **Implemented (frozen, FU3B)** |
| EvidenceDecision.AI_ASSISTED_MATCH | `domain/enums.py` | **Reserved (frozen semantic identity disposition, FU3A)** |
| Persisted run lifecycle | `runs/` | Implemented (ResearchRun) |
| Execution evidence model | `runs/` | Implemented (ExecutionEvidenceRecord) |
| Execution claim service | `runs/` | Implemented (claim_execution) |
| Execution completion service | `runs/` | Implemented (complete_execution) |
| Retry service | `runs/` | Implemented (retry_run) |
| Price intelligence snapshot | `runs/` | Implemented (PriceIntelligenceSnapshot) |
| Standalone web shell | `web/` | Implemented |
| Part-number comparison | `research/identity` | Implemented |
| Search provider boundary | `providers/search.py` | Implemented |
| Serper adapter | `providers/serper.py` | Implemented |
| Page fetch + extraction | `providers/http_page.py` + `research/listings.py` | Implemented |
| Listing normalization | `research/normalization.py` | Implemented |
| MPN matching + rejection | `research/matching.py` | Implemented |
| Price aggregation (frozen) | `research/aggregation.py` | **Implemented (frozen)** |
| Versioned codec | `research/price_result_codec.py` | Implemented |
| Price report presentation | `web/presentation.py` | Implemented |
| Research orchestration | `execution/` | **Implemented (frozen)** |
| Web execution wiring | `web/` | **Implemented (frozen)** |
| Structured API | — | 5A (not implemented) |
| FoxPro launcher | — | Server-side implemented; client integrated outside repo, UAT passed |
| SAP launcher | — | Future |
| Human review candidate model | `runs/` (AiAssistedReviewCandidate) | **Implemented (frozen, HUMAN-REVIEW)**
| Human review service | `runs/ai_assisted_review.py` | **Implemented (frozen, HUMAN-REVIEW)**
| Reviewed price aggregation | `research/aggregation.py` (aggregate_reviewed_listing_prices) | **Implemented (frozen, HUMAN-REVIEW)**
| Human review web view + URLs | `web/views.py` + `web/urls.py` | **Implemented (frozen, HUMAN-REVIEW)**
| Human review candidate presentation | `web/presentation.py` | **Implemented (frozen, HUMAN-REVIEW)**
| Product Specification Framework (6A) | `research/specifications.py` | **Implemented (6A)**

## Research orchestration

Base 4C orchestration contract: **frozen**
FU3B semantic execution extension: **APPROVED / FROZEN**

Implementation snapshot:

- Research orchestration: Base 4C frozen; FU3B semantic extension frozen
- Semantic execution integration: Implemented / APPROVED / FROZEN

## Web layer architecture

The web layer may import only the public execution API and the approved read-side research symbols:

```
web  ->  product_intelligence.execution  (execute_research_run, ExecutionError)
web  ->  product_intelligence.runs  (ClaimExecutionFailed, retry_run, ResearchRun,
         confirm_candidate, reject_candidate, undo_review, review errors)
web  ->  product_intelligence.research.price_result_codec
         (PriceResultCodecError, decode_price_aggregation_result)
web  ->  product_intelligence.research.aggregation
         (PriceAggregationResult, aggregate_reviewed_listing_prices)
web  ->  product_intelligence.research.matching
         (ListingIdentityAssessment, is_human_review_eligible_assessment)
web  ->  product_intelligence.runs.models
         (ResearchRun, PriceIntelligenceSnapshot, AiAssistedReviewCandidate)
```

The web layer MUST NOT import:
- `product_intelligence.execution.orchestration` (or any execution submodule)
- `product_intelligence.execution` (bare module import)
- `product_intelligence.providers` (or any provider submodule)
- `product_intelligence.runs.execution_claims` (internal)
- `product_intelligence.research.identity` (research decision primitive)
- Any unapproved symbol from approved research modules

Web writes review state through the runs-owned review service
(`runs/ai_assisted_review.py`). Web may perform approved read-side
composition and binding validation as enforced by boundary tests.
Web must not bypass providers, must not own execution internals,
and must not carry research semantics.

## FoxPro ownership

FoxPro source code is NOT maintained in this repository. This repository
owns only the launcher-facing HTTP intake contract:

```
GET /research/new?mpn=<encoded>&description=<encoded>
```

The project lead maintains the FoxPro client code manually in the existing
Visual FoxPro sales-order application.

## Human Review authority model

HUMAN-REVIEW is IMPLEMENTED / APPROVED / FROZEN.

Required authority layers:

1. Deterministic identity
   ListingIdentityAssessment.decision == ACCEPTED
   remains the only automatic existing-4A identity authority.

2. Semantic match
   original ListingIdentityAssessment.decision == REJECTED
   +
   AiAssistedMatchResult.disposition == AI_ASSISTED_MATCH

   Snapshot assessment itself is never AI_ASSISTED_MATCH.

3. Human review overlay
   run-scoped AiAssistedReviewCandidate
   states:
       UNREVIEWED
       CONFIRMED
       REJECTED
   actions:
       Confirm
       Reject
       Undo

   Human confirmation never mutates snapshot assessment.

4. Machine Price
   deterministic ACCEPTED only.

5. Reviewed Price
   deterministic ACCEPTED
   +
   human-CONFIRMED semantic-eligible listings.

   Preserve origin:
       DETERMINISTIC
       HUMAN_CONFIRMED

6. Human confirmation changes identity authority only.
   Existing deterministic non-identity price eligibility remains:
       Decimal price
       comparable currency
       known condition

7. Candidate binding fails closed:
   exact run/snapshot assessment + provenance must match before mutation.

8. Candidate creation is run-scoped and participates in final publication.

9. No reviewer identity/authentication/audit identity was introduced.


## Eligibility boundary

Eligible original deterministic assessments ONLY:

    REJECTED
    + NO_EXPLICIT_MPN_EVIDENCE
    + TITLE_TEXT

    REJECTED
    + NO_EXPLICIT_MPN_EVIDENCE
    + SKU_FIELD

    REJECTED
    + PARTIAL_MPN_ONLY

Not eligible:

    ACCEPTED
    UNDECIDED
    MPN_MISMATCH
    NO_EXPLICIT_MPN_EVIDENCE + NONE
    any other non-semantic-eligible state


## Validation results

### HISTORICAL FU3A2F FREEZE SNAPSHOT

| Metric | Count |
| --- | --- |
| Collected | 2158 |
| Passed | 2151 |
| Failed | 7 |
| (+ 39 subtests) | — |

### HISTORICAL FU3B FINAL REVIEW SNAPSHOT

| Metric | Count |
| --- | --- |
| Collected | 2212 |
| Passed | 2206 |
| Failed | 6 |

The six failures were exactly:

- `tests/evaluation/test_evaluation_boundaries.py::test_loading_the_corpus_imports_no_framework_or_provider`
- `tests/providers/test_provider_boundaries.py::test_importing_the_provider_boundary_pulls_in_no_third_party_dependency`
- `tests/providers/test_provider_boundaries.py::test_importing_the_page_boundary_pulls_in_no_third_party_dependency`
- `tests/research/test_listing_normalization_boundaries.py::test_importing_the_research_core_still_pulls_in_no_third_party_dependency`
- `tests/research/test_research_identity_boundaries.py::test_importing_the_research_core_pulls_in_no_third_party_dependency`
- `tests/runs/test_research_run_boundaries.py::test_the_domain_still_imports_without_django_present`

### 6A IMPLEMENTATION SNAPSHOT (CURRENT)

| Metric | Count |
| --- | --- |
| Collected | 2539 |
| Passed | 2531 |
| Failed | 8 |
| Unexpected failures | 0 |

The eight failures are the established environment-specific
subprocess-boundary flake allowlist on this Windows / Python 3.14 workstation
(all boundary/import-guard tests):

1. `tests/domain/test_domain_boundaries.py::test_domain_imports_without_django_network_or_llm_dependencies`
2. `tests/evaluation/test_evaluation_boundaries.py::test_loading_the_corpus_imports_no_framework_or_provider`
3. `tests/providers/test_provider_boundaries.py::test_importing_the_provider_boundary_pulls_in_no_third_party_dependency`
4. `tests/providers/test_provider_boundaries.py::test_importing_the_page_boundary_pulls_in_no_third_party_dependency`
5. `tests/research/test_listing_normalization_boundaries.py::test_importing_the_research_core_still_pulls_in_no_third_party_dependency`
6. `tests/research/test_research_identity_boundaries.py::test_importing_the_research_core_pulls_in_no_third_party_dependency`
7. `tests/research/test_specification_boundaries.py::test_importing_specifications_pulls_in_no_third_party_dependency`
8. `tests/runs/test_research_run_boundaries.py::test_the_domain_still_imports_without_django_present`

Observed failure signature:

    subprocess.Popen
    -> _winapi.DuplicateHandle
    -> OSError: [WinError 6/50] The handle is invalid / The request is not supported

These are environment-specific subprocess-boundary limitations on this Windows /
Python 3.14 workstation, not application defects. No node outside the fixed
eight-node allowlist fails. No test is skipped, xfailed, or weakened.

## Next delivery priority

**HUMAN-REVIEW**: IMPLEMENTED / APPROVED / FROZEN

**5A**: PLANNED / NOT IMPLEMENTED / non-blocking

**5B**: Server-side implemented; client integrated outside repo; localhost UAT passed

**6A**: IMPLEMENTED / REVIEW PENDING —
         Product Specification Framework (framework only, no extraction)
         Corrective pass: evidence-derived constructor enforcement,
         deep immutability (MappingProxyType), schema/definition key
         consistency. Awaiting project-lead approval before freeze.

**6B**: NEXT DELIVERY PRIORITY —
         First Category-Specific Specification Schema;
         Enterprise SSD / storage is preferred first-category direction;
         final choice during 6A/6B review

**6C**: follows 6B;
         Specification Evidence Extraction & Resolution;
         acquires evidence, extracts raw observations, preserves provenance,
         normalizes via 6B schema, invokes 6A resolution;
         no LLM preselected

**7A/7B/7C**: follow 6A/6B/6C

## Semantic qualification harness

**APPROVED / FROZEN**

The semantic qualification corpus, prompt v1.1, evaluator mathematics,
qualification thresholds, expected decisions, and safety gates are APPROVED AND FROZEN.

- Prompt v1.1 SHA256: f50e5584659f953ce73a97ccc8bc1ff487fbeeb37e2e0a72e52210613aeab1ff
- Corpus SHA256: 3c21d6fcd4eefa5cc383792abfd9308bd5c03315834c8ffdffd0f6a2b3619ca1

Do NOT modify:
- evaluation/semantic_corpus/cases.json truth labels or case contents
- SEMANTIC_PROMPT_VERSION = "1.1"
- semantic system/user prompt semantics
- semantic evaluator formulas
- qualification gates
- production research/matching.py
- production aggregation (4A FROZEN)
- production execution authority (frozen 4C/FU3B execution semantics preserved;
  future explicitly approved phases may extend)

Since FU3A2 the frozen prompt text, decision vocabulary, response schema and
strict parser/validator physically live in
`product_intelligence/semantic/contract.py`. `evaluation/semantic/prompt.py`,
`vocabulary.py` and `evaluator.py` re-export those same objects. The freeze
applies to the behaviour wherever it lives; the extraction was proved
behaviour-preserving by the two SHA256 fingerprints above.

## Model qualification runner

**IMPLEMENTED**

Semantic qualification harness infrastructure is implemented:

* transport.py - Abstract transport interface + OpenAI-compatible HTTP
* model_catalog.py - Explicit model catalog (8 primary + 1 smoke + 3 skip)
* runner.py - Benchmark runner with durable artifacts
* cli.py - CLI for list-models, run, evaluate, compare
* comparison.py - Offline comparison utility

All tests use fake transports / recorded responses. No live network calls.

**Two models have passed the formal FULL qualification gates**:
`amax/nemotron-3-super` (primary) and `vllm-262k/Qwen3.6-27B-262K` (fallback).
They are the pinned production route.

## FU3A — Production Semantic Runtime Contract

**APPROVED / FROZEN.** (Corrective history: FU3A2B, FU3A2C, FU3A2D, FU3A2E,
FU3A2F — labels for the corrective path to this freeze, not separate durable
phases. FU3A2F was the final corrective pass; ChatGPT's independent review of
the final FU3A2F `runtime.py` and `test_runtime.py` approved the contract.)

Both `semantic/contract.py` and `EvidenceDecision.AI_ASSISTED_MATCH` are now
frozen as part of this approval.

### Single source of truth

`product_intelligence/semantic/contract.py` is the canonical implementation of:

* Prompt v1.1 (`SEMANTIC_PROMPT_VERSION`, `SYSTEM_PROMPT`,
  `USER_PROMPT_TEMPLATE`, `SemanticPrompt`, `build_prompt`)
* `SemanticDecision`, `ConfidenceLevel`, `SemanticMatchResponse`
* `parse_raw_output`, `validate_response`, `RawOutputParseError`

`evaluation/semantic/prompt.py`, `vocabulary.py` and `evaluator.py` re-export
those objects. Sharing is proved by object identity, not by an import
statement (`tests/semantic/test_contract_sharing.py`). Production does not
import `product_intelligence.evaluation.semantic.*`.

`product_intelligence/semantic/transport.py` is likewise the canonical
transport implementation (HTTP call, error classification, all three
transport classes); `evaluation/semantic/transport.py` re-exports it rather
than keeping a second copy — proved by object identity in
`tests/semantic/test_contract_sharing.py`, same as the contract.

### Import boundary

Importing `product_intelligence.semantic` loads no
`product_intelligence.evaluation.*` module, no Django, and no network client
(`requests`, `urllib`, `urllib3`, `httpx`, `aiohttp`). `evaluation.semantic.transport`
is NOT whitelisted: the live transport is imported lazily inside transport
construction. Enforced by `tests/semantic/test_runtime_boundaries.py`, which
inspects real post-import `sys.modules` state from a clean module state — and
(FU3A2D) also restores each evicted module's *parent-package attribute*, not
only its `sys.modules` entry, so a test that reimports
`product_intelligence.semantic` cannot leave `product_intelligence.semantic`
(attribute access) and `sys.modules["product_intelligence.semantic"]`
pointing at two different objects for the rest of the test session.

### Pinned qualified route

| Setting | Value |
| --- | --- |
| Primary | `amax` / `nemotron-3-super` |
| Fallback | `vllm-262k` / `Qwen3.6-27B-262K` |
| temperature | `0.0` (exact float — `type(x) is float`, so `0`/`False` are rejected) |
| max_tokens | `32768` |

`SemanticRuntimeConfig` keeps these fields for compatibility, but
`validate_runtime_config` rejects any deviation before a transport is built or
called — by exact type where numeric equality alone would be insufficient
(`0`/`False` are numerically `== 0.0` but are not the qualified float). Only
`request_timeout_seconds` is configurable, and an unreadable or non-finite
environment value (`PI_SEMANTIC_REQUEST_TIMEOUT_SECONDS=abc`/`nan`/`inf`) fails
closed rather than silently defaulting.

### Fallback policy

Fallback uses an EXPLICIT allowlist (`PRIMARY_FALLBACK_ELIGIBLE_ERRORS`), never
"anything outside a deny set", so an unrecognised error code cannot silently
buy a second paid model call. Both lookup tables the runtime and
`SemanticRuntimeResult` index (`_PRIMARY_STATUS_TO_ERROR_TYPE`,
`_FALLBACK_STATUS_TO_ERROR_TYPE`) are complete over every non-OK status, and
every code the canonical transport's `ALL_ERROR_TYPES` can return has an
intentional mapping — proved by
`tests/semantic/test_runtime.py::TestEveryCanonicalTransportCodeHasAnIntentionalMapping`.

Eligible: `TIMEOUT`, `DNS_ERROR`, `TLS_ERROR`, `CONNECTION_ERROR`,
`RATE_LIMITED`, `HTTP_ERROR`, `PROVIDER_UNAVAILABLE`, `AUTHENTICATION_FAILED`,
`MODEL_NOT_FOUND`, `EMPTY_RESPONSE`, `MALFORMED_JSON`, `SCHEMA_INVALID`,
`MODEL_IDENTITY_MISMATCH`, `INVALID_RESPONSE` (FU3A2D: a malformed HTTP-200
provider envelope is an execution/output-contract failure of the same kind as
`MALFORMED_JSON`/`SCHEMA_INVALID`, and now buys one fallback attempt the same
way they do).

Not eligible: `INVALID_REQUEST_CONFIGURATION`, `UNSUPPORTED_PARAMETER`,
`PROVIDER_NOT_CONFIGURED`, `CASE_REJECTED` (FU3A2D: a content-policy rejection
of the case's own content — retrying the identical content against a
different model would not help — kept as its own known bounded status,
distinct from `UNKNOWN_ERROR`), an invalid `SemanticRuntimeConfig`, any
genuinely unrecognised error code, and programming exceptions.

A valid primary decision (`MATCH`, `NO_MATCH`, `UNCERTAIN`) is FINAL: exactly
one primary call, zero fallback calls.

### Model identity

Exact provider-reported model identity is mandatory. A primary that reports the
wrong model, or reports no model at all, falls back exactly once. A fallback
that reports the wrong model or no model is a final semantic failure — there is
no third provider.

### Provenance and safety

`SemanticRuntimeResult` carries the requested primary route, a tuple of frozen
`SemanticAttempt` records (provider, model, bounded status, latency), the
fallback flag and reason, and the bounded final error type. On ANY final
failure `actual_provider` and `actual_model` are `None`. No raw response, no
provider body, no exception text, no API key, and no chain-of-thought is
retained. Programming exceptions propagate rather than becoming a fallback.

`SemanticRuntimeResult` is fully self-validating (FU3A2D): every typed field
(`decision`, `confidence`, `error_type`, `fallback_reason`, `fallback_used`,
and the three attribute tuples) is checked by exact type, not merely accepted
and left to fail later inside `to_dict()`. A failure's `error_type` is
mechanically bound to what its attempts actually recorded — a one-attempt
failure's `error_type` must equal `_PRIMARY_STATUS_TO_ERROR_TYPE[first.status]`,
a two-attempt failure's must equal
`_FALLBACK_STATUS_TO_ERROR_TYPE[second.status]` — so a result cannot claim,
say, `PRIMARY_MODEL_NOT_FOUND` for an attempt that actually timed out.

### Relationship to 4A

The original deterministic assessment remains REJECTED.
The parallel AiAssistedMatchResult carries disposition AI_ASSISTED_MATCH.
Existing 4A sees the REJECTED assessment and excludes it as
IDENTITY_NOT_ACCEPTED.


## Known issues / debt

- FU3A Production Semantic Runtime Contract: APPROVED / FROZEN
- FU3B Semantic Execution Integration: APPROVED / FROZEN
- This Windows / Python 3.14 workstation has a fixed eight-node subprocess-boundary
  flake allowlist. These nodes may fail independently between runs with
  OSError: [WinError 6/50] from subprocess.run(..., capture_output=True).
  No node outside the fixed eight-node allowlist fails.
  Environment limitation, not a product defect.
