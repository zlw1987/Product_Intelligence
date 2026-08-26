# Semantic Benchmark Runner

## Overview

The semantic benchmark runner provides offline evaluation infrastructure for semantic model qualification. No live model integration is required for this phase - all tests use fake transports and recorded responses.

## Usage

```bash
# List available models
python -m product_intelligence.evaluation.semantic.cli list-models

# Run full qualification (amax/minimax-m2.7)
python -m product_intelligence.evaluation.semantic.cli run --provider amax --model minimax-m2.7

# Run smoke test (amax/gpt-oss-20b)
python -m product_intelligence.evaluation.semantic.cli run --provider amax --model gpt-oss-20b --mode smoke

# Compare runs
python -m product_intelligence.evaluation.semantic.cli compare run1/manifest.json run2/manifest.json
```

## Model Catalog Authorization

### FULL Qualification Models

These models may run FULL qualification:
- `vllm-262k/Qwen3.6-27B-262K` (PRIMARY_CANDIDATE)
- `amax/minimax-m2.7` (PRIMARY_CANDIDATE)
- `amax/minimax-m2.7-thinking` (PRIMARY_CANDIDATE)
- `amax/nemotron-3-super` (PRIMARY_CANDIDATE)
- `amax/google/gemma-4-26B-A4B-it` (PRIMARY_CANDIDATE)
- `amax/mistral-small-4` (PRIMARY_CANDIDATE)
- `amax/mistral-small-24b-instruct-2501` (LIGHTWEIGHT_GENERAL)
- `amax/qwen3-coder-next` (PRIMARY_CANDIDATE)

### SMOKE Test Models

These models may run only SMOKE (5 cases):
- `amax/gpt-oss-20b` (SMOKE_TEST)

### SKIP Models

These models cannot be benchmarked:
- `amax/kokoro-tts` (SKIP_NON_GENERATIVE)
- `amax/e5-mistral-7b-instruct-embed` (SKIP_NON_GENERATIVE)
- `amax/qwen3-embedding-8b` (SKIP_NON_GENERATIVE)

### Authorization Rules

| Model Type | FULL | SMOKE |
|------------|------|-------|
| PRIMARY_CANDIDATE | ✅ | ❌ |
| LIGHTWEIGHT_GENERAL | ✅ | ❌ |
| SMOKE_TEST | ❌ | ✅ |
| SKIP_NON_GENERATIVE | ❌ | ❌ |

**Unknown models are rejected** - the runner fails closed rather than falling back to allow any model.

## FULL vs SMOKE Semantics

### FULL Qualification

- Runs all 64 cases from the corpus
- Subject to hard gates:
  - `zero_false_match_on_authority_conflicts`
  - `zero_false_match_on_accessory_safety_set`
  - `primary_valid_output_rate_sufficient` (>= 99%)
  - `primary_match_precision_sufficient` (>= 98%)
  - `primary_overall_accuracy_target` (>= 90%)
- Comparable on FULL leaderboard

### SMOKE Qualification (RUNTIME SMOKE SCREEN)

- Runs exactly 5 cases (SMQ-0001, SMQ-0002, SMQ-0004, SMQ-0005, SMQ-0032)
- **NOT a full semantic qualification**
- Full qualification hard gates are **N/A** for smoke runs
- **Cannot enter FULL leaderboard**
- Valid output rate = valid attempted outputs / 5

## Safe Artifact Storage

### No Raw Exception Content

Transport failures use normalized error codes only:

| Code | Meaning |
|------|---------|
| `TIMEOUT` | Request timed out |
| `DNS_ERROR` | DNS resolution failed |
| `TLS_ERROR` | TLS/SSL error |
| `CONNECTION_ERROR` | Connection failed |
| `HTTP_ERROR` | HTTP error (status in http_status) |
| `INVALID_PROVIDER_RESPONSE` | Malformed provider response |
| `RESPONSE_DECODE_ERROR` | JSON decode failed |

Raw exception messages, API keys, URLs, and credentials are **never** persisted.

### Raw Output Preservation

The provider's decoded message content string is preserved **exactly as received**, including:
- Leading/trailing whitespace
- Markdown code fences
- Prose around JSON

The strict parser may reject such output as invalid, but the raw output is preserved in artifacts unchanged.

### Redirect Handling

HTTP redirects (3xx responses) are **not followed**. The benchmark fails closed on redirect rather than forwarding credentials to an unintended destination.

### Zero Retries

There are no automatic retries. Permanent configuration failures (unsupported parameters, auth failures) abort the run immediately rather than retrying with modified parameters.

## Artifact Directory

Run artifacts are stored in `semantic_benchmark_runs/` by default:

```
semantic_benchmark_runs/
  20250101T120000__amax_minimax-m2.7/
    manifest.json
    responses.jsonl
    evaluation.json
    summary.md
  20250101T130000__amax_gpt-oss-20b/
    manifest.json
    responses.jsonl
    evaluation.json
    summary.md
```

For model IDs with slashes (e.g., `google/gemma-4-26B-A4B-it`), the slash is sanitized to underscore with a hash suffix for collision resistance: `amax_google_gemma-4-26B-A4B-it--a1b2c3d4`.

The `semantic_benchmark_runs/` directory is gitignored - benchmark artifacts never become source changes.

## Provider Environment Variables

| Variable | Description |
|----------|-------------|
| `PI_SEMANTIC_AMAX_BASE_URL` | amax API base URL (required for amax runs) |
| `PI_SEMANTIC_AMAX_API_KEY` | amax API key (optional) |
| `PI_SEMANTIC_VLLM_262K_BASE_URL` | vLLM base URL (required for vllm-262k runs) |
| `PI_SEMANTIC_VLLM_262K_API_KEY` | vLLM API key (optional) |

## FULL Leaderboard Compatibility Rules

FULL runs are comparable only when ALL of these match:
- `benchmark_kind` = "semantic_model_qualification"
- `schema_version` (compatible)
- `case_selection` = "FULL"
- `case_count` (same number of cases)
- `corpus_version`
- `corpus_sha256` (exact corpus content match)
- `prompt_version`
- `prompt_sha256` (exact prompt content match)

SMOKE runs **never** enter the FULL leaderboard.

Unknown/missing/corrupt provenance fails closed - no automatic winner selection.

## Corpus Hash Definition

The corpus SHA256 is computed from the complete raw corpus JSON content (canonical JSON with deterministic sorting), not a projection that might omit fields.

## Prompt Hash Definition

The prompt SHA256 includes the exact prompts used:

```json
[
  {
    "case_id": "SMQ-0001",
    "system_prompt": "<exact system prompt>",
    "user_prompt": "<exact user prompt>"
  },
  ...
]
```

For FULL runs, all 64 cases are included. For SMOKE runs, exactly 5 cases are included.

## No Network Calls

All tests are offline. The runner uses `FakeSemanticModelTransport` for testing and does not make any live network calls.