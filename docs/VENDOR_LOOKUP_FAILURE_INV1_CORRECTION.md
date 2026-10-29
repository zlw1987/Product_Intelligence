# PERF-SEM-INV1-FU1 — Production Baseline Correction Report

**Investigation type:** Corrective investigation (read-only). No implementation.
**Production baseline SHA:** `cde2a802c54372da088a7d1876f450cbf9bd7c69` (2026-10-26 15:53:55 -0700)
**Divergent main branch SHA (NOT production):** `916296af8d23f780aca63702e3302458ba7f8ffd`

---

## 1. Correct Production-Baseline SHA and Inspected Blob Identities

### 1.1 Deployed baseline confirmed

The production runtime is pinned at:

```
cde2a802c54372da088a7d1876f450cbf9bd7c69  (2026-10-26 15:53:55 -0700)
```

This is the last committed SHA before the V2 semantic authority branch
diverged. It does NOT contain any V2 semantic code.

### 1.2 Files that exist at production but NOT on divergent main (none)

All production V1 files also exist on the divergent branch. The divergence
is purely additive: V2 files are added on top of V1.

### 1.3 Files on divergent main that do NOT exist at production SHA

Confirmed via `git show cde2a80:<path>` returning exit code 128:

| File | Exists at production SHA? |
|------|--------------------------|
| `product_intelligence/semantic/runtime_v2.py` | **NO** |
| `product_intelligence/execution/semantic_decision_v2_execution.py` | **NO** |
| `product_intelligence/execution/semantic_decision_persistence.py` | **NO** |
| `product_intelligence/semantic/contract_v2.py` | **NO** |
| `product_intelligence/semantic/contract_v2_1.py` | **NO** |

These V2 files represent a separate semantic architecture (S2-C, Q3-B/C
lineage) that was developed on `main` but is NOT deployed.

### 1.4 V1 semantic architecture at production SHA (confirmed via `git show`)

| File | Role |
|------|------|
| `product_intelligence/semantic/__init__.py` | Package exports |
| `product_intelligence/semantic/contract.py` | Prompt v1.1, decision vocabulary, response schema, parser/validator |
| `product_intelligence/semantic/runtime.py` | Production runtime with Primary/Fallback routing, per-attempt provenance, `SemanticRuntimeResult` |
| `product_intelligence/semantic/transport.py` | Neutral transport: `OpenAISemanticTransport` (urllib), `FakeSemanticModelTransport`, `TransportResult`/`TransportFailure` |
| `product_intelligence/execution/semantic_integration.py` | Wires V1 runtime into orchestration; eligibility predicate; evidence writes |

### 1.5 Pinned V1 route constants (from `runtime.py` at production SHA)

```python
PRIMARY_PROVIDER = "amax"
PRIMARY_MODEL = "qwen3.8-27b"
FALLBACK_PROVIDER = "vllm-262k"
FALLBACK_MODEL = "Qwen3.6-27B-262K"
SEMANTIC_TEMPERATURE = 0.0
SEMANTIC_MAX_TOKENS = 32768
DEFAULT_REQUEST_TIMEOUT_SECONDS = 300.0
```

---

## 2. Exact V1 Execution Path

The production V1 execution pipeline for a Micron research run, as traced
through `product_intelligence/execution/orchestration.py` at the deployed SHA:

### 2.1 Pipeline sequence

```
1.  execute_research_run(run_id)
    └── claim_execution(run)              # CREATED → RUNNING
    └── _execute_claimed_run()
        ├── Step 1: _try_direct_acquisition()
        │   └── (4D-A) Preferred-source direct acquisition
        │       For Micron: direct vendor pages fetched first
        │
        ├── Step 2: _has_valid_4a_buckets()
        │   └── If direct evidence insufficient → fallback_required = True
        │
        ├── Step 3: Fallback search (if required)
        │   ├── 4D-D: acquire_micron_alias_eligibility()
        │   │   └── ONE reviewed Micron catalog authority fetch
        │   │   └── Persist alias snapshot
        │   ├── build_search_query() / build_alias_expanded_search_query()
        │   ├── search_provider.search(query)     # Serper, ONE paid call
        │   └── Per-result: _process_candidate_url()
        │       ├── page_fetcher.fetch(url)        # FETCH
        │       ├── extract_listing_observations() # EXTRACT
        │       ├── normalize_listings()           # NORMALIZE
        │       └── assess_listing_identity()      # MATCH (deterministic)
        │
        ├── Step 4: Semantic integration
        │   └── evaluate_semantic_matches(request, semantic_input, evidence_writer)
        │       For each semantic-eligible candidate:
        │         ├── _is_semantic_eligible(assessment)
        │         │   REJECTED + (NO_EXPLICIT_MPN_EVIDENCE with TITLE_TEXT/SKU_FIELD
        │         │                 OR PARTIAL_MPN_ONLY) → eligible
        │         ├── _has_usable_evidence(assessment)
        │         │   product_title must be present
        │         ├── runtime.evaluate(case_id, ...)
        │         │   ├── PRIMARY attempt (amax/qwen3.8-27b)
        │         │   │   └── If OK: return 1-attempt result
        │         │   │   └── If fallback-eligible error: → FALLBACK
        │         │   ├── FALLBACK attempt (vllm-262k/Qwen3.6-27B-262K)
        │         │   │   └── If OK: return 2-attempt result
        │         │   │   └── If failed: return 2-attempt failure
        │         │   └── If non-fallback-eligible error: return 1-attempt failure
        │         ├── evidence_writer.append_execution_attempt()
        │         │   SEMANTIC/SUCCESS/SEMANTIC_MATCH|NO_MATCH|UNCERTAIN
        │         │   SEMANTIC/FAILED/SEMANTIC_UNAVAILABLE
        │         └── If MATCH: append AiAssistedMatchResult
        │
        ├── Step 5: aggregate_prices()
        │   └── 4A aggregation over ALL assessments (semantic not in buckets)
        │
        ├── ATOMIC FINAL PUBLICATION (transaction):
        │   ├── PriceIntelligenceSnapshot.objects.create()
        │   ├── _create_review_candidates()        # For AI-assisted MATCHes only
        │   ├── ResearchSupplementSnapshot (4D-B, if vendor attempted)
        │   ├── ResearchFxSnapshot (4D-C-A, if FX obtained)
        │   └── complete_execution(COMPLETED)
        │
        └── Vendor lookup + FX (between aggregation and atomic publication):
            ├── _try_vendor_commercial_lookup()     # 4D-B, ONE network call, 10s timeout
            └── _try_fetch_fx_rates()               # 4D-C-A, ONE FX call (or cache)
```

### 2.2 Critical V1 semantic semantics

- **One `SemanticRuntimeResult` per eligible candidate.** Not one per attempt.
- **Each result carries `attempts: tuple[SemanticAttempt, ...]`** with exactly
  1 or 2 members (Primary only, or Primary + Fallback).
- **Fallback triggers ONLY on execution failure** of the Primary attempt,
  specifically when the failure code is in `PRIMARY_FALLBACK_ELIGIBLE_ERRORS`
  (15 codes: TIMEOUT, DNS_ERROR, TLS_ERROR, CONNECTION_ERROR, RATE_LIMITED,
  HTTP_ERROR, PROVIDER_UNAVAILABLE, AUTHENTICATION_FAILED, MODEL_NOT_FOUND,
  EMPTY_RESPONSE, MALFORMED_JSON, SCHEMA_INVALID, MODEL_IDENTITY_MISMATCH,
  INVALID_RESPONSE).
- **A valid Primary response (MATCH/NO_MATCH/UNCERTAIN) is FINAL** — exactly
  one call, zero fallback calls. Low confidence or conservative reason code
  never triggers fallback.
- **Non-fallback-eligible errors** (5 codes: INVALID_REQUEST_CONFIGURATION,
  UNSUPPORTED_PARAMETER, PROVIDER_NOT_CONFIGURED, UNKNOWN_ERROR, CASE_REJECTED)
  fail closed after one attempt.

### 2.3 Vendor lookup position

The Vendor commercial lookup (`_try_vendor_commercial_lookup`) executes
**AFTER** semantic integration and aggregation, but **BEFORE** atomic final
publication. It is supplemental only — its failure does NOT prevent the run
from completing. A `TimeoutError` from the Vendor API (10-second bounded
timeout) is caught by `InternalVendorAdapter.lookup()` and encoded as a
`FAILED` supplemental result, NOT as a run failure.

---

## 3. Revised Timestamp and Candidate-Count Analysis

### 3.1 Micron production run timeline (from task statement)

| Event | Timestamp (UTC) |
|-------|-----------------|
| Run started | 21:42:57.901942 |
| First persisted SEMANTIC result | ~21:43:52 |
| Last persisted SEMANTIC result | ~21:48:45 |
| Vendor TimeoutError (after last semantic) | after ~21:48:45 |
| Run finished | 21:48:55.935429 |
| Total duration | 5 min 58 sec (358 seconds) |

### 3.2 Time to first semantic evaluation

From run start (21:42:57) to first semantic record (~21:43:52):
**approximately 55 seconds.**

This period covers: claim execution, direct acquisition (4D-A), fallback
search determination, Micron alias eligibility acquisition (catalog fetch),
Serper search call, URL processing (fetch/extract/normalize/match) for
enough URLs to produce the first semantic-eligible candidate.

### 3.3 Semantic evaluation window

From first to last persisted SEMANTIC record:
**approximately 4 minutes 53 seconds (293 seconds).**

Ten persisted SEMANTIC execution records were produced. Each record
corresponds to ONE call to `evaluate()` in the V1 runtime.

### 3.4 Candidate count correction

**The production run evaluated exactly 10 semantic-eligible candidates.**

Each candidate produces exactly ONE `ExecutionEvidenceRecord` at the
SEMANTIC stage. The record carries `stage=SEMANTIC`, `outcome=SUCCESS` or
`FAILED`, and a detail code. It does NOT record the number of underlying
provider attempts.

**One V1 candidate evaluation may involve one or two provider attempts:**

- If Primary succeeds: 1 attempt, 1 SEMANTIC record (SUCCESS)
- If Primary fails with fallback-eligible error, Fallback succeeds:
  2 attempts, 1 SEMANTIC record (SUCCESS)
- If Primary fails with fallback-eligible error, Fallback fails:
  2 attempts, 1 SEMANTIC record (FAILED)
- If Primary fails with non-fallback-eligible error:
  1 attempt, 1 SEMANTIC record (FAILED)

**The previous INV1 report's candidate count was correct in recording
10 SEMANTIC execution records. However, it may have conflated 10 records
with "10 model calls" when some candidates may have triggered 2 provider
attempts (Primary + Fallback), yielding up to 20 actual model calls across
the 10 candidates.**

The 21 stderr `CONNECTION_ERROR` warnings for "Primary" across multiple
case IDs cannot be definitively attributed to this Micron run without
examining the run UUID in the log. The count of 21 exceeds 10, suggesting
either: (a) CONNECTION_ERROR warnings from other concurrent runs, or (b)
repeated connection retries at the urllib level that each produce a warning
for what the runtime sees as a single failed attempt.

### 3.5 Defensible timing bounds per candidate

**CONFIRMED FACT:** The V1 runtime measures per-attempt latency with
`time.perf_counter()` in `SemanticRuntime._attempt()`. This latency is
stored in `SemanticAttempt.latency_ms` and serialized in
`SemanticRuntimeResult.to_dict()`.

**CONFIRMED FACT:** This per-attempt latency is **NOT persisted** to any
database table. The `ExecutionEvidenceRecord` has no latency field. The
`AiAssistedReviewCandidate` model has no latency field. The
`PriceIntelligenceSnapshot` payload (encoded via the versioned codec)
does not include semantic per-attempt latency.

**KNOWN:** The only persisted timing for semantic evaluation is the
`created_at` timestamp on `ExecutionEvidenceRecord`, which records when
the evidence was persisted to the database — not when the evaluation
started or ended, and not per-attempt latency.

### 3.6 Per-candidate timing analysis (bounds from persisted timestamps)

With 10 SEMANTIC records spanning ~293 seconds:
- Average interval between records: ~29.3 seconds
- This represents the elapsed time from one candidate's evidence write to
  the next candidate's evidence write, not a per-candidate model inference time
- A candidate that hit Fallback would consume TWO model calls (each up to
  300 seconds on the request timeout)

**WITHOUT per-attempt persistence, the following remain estimates:**

- Whether all 10 candidates hit Primary successfully (minimum time)
- Whether some Primary calls failed and triggered Fallback (longer time)
- How many distinct model invocations occurred (10–20 range)

### 3.7 Safe candidate-to-run correlation

**Without exposing raw source URLs**, candidate IDs from the V1 runtime
(`candidate-{url_hash}-{index}`) use an 8-character SHA-256 prefix of the
source URL. These are not persisted but could be reconstructed from the
`ExecutionEvidenceRecord.candidate_url` stored for each SEMANTIC record.

A safe correlation method:

1. Read the `ExecutionEvidenceRecord` rows for the Micron run's UUID
2. Extract `candidate_url` values for SEMANTIC-stage records
3. Compute `hashlib.sha256(url).hexdigest()[:8]` for each URL
4. The resulting hash prefix can be matched against `case_id` values in
   stderr logs without exposing the full URL

This preserves URL opacity while enabling correlation of stderr
`CONNECTION_ERROR` warnings to specific persisted evidence records.

---

## 4. Connection-Error Attribution: Proven vs Unknown

### 4.1 What `CONNECTION_ERROR` means in V1 transport

From `transport.py` at production SHA, `CONNECTION_ERROR` is produced in
these exact code paths:

```python
# In OpenAISemanticTransport.complete():
except urllib.error.URLError as e:
    reason = e.reason
    if isinstance(reason, TimeoutError):
        error_type = "TIMEOUT"          # NOT CONNECTION_ERROR
    elif isinstance(reason, OSError):
        error_type = "CONNECTION_ERROR" # DNS resolution failure,
    else:                               #  connection refused, reset
        error_type = "CONNECTION_ERROR"

except (OSError, UnicodeDecodeError):
    error_type = "CONNECTION_ERROR"     # Connection reset mid-read,
                                        # or non-UTF-8 response body
```

**Precise classification:** `CONNECTION_ERROR` in V1 transport means the
underlying `urllib` raised either:
- `urllib.error.URLError` with an `OSError` reason (DNS failure, connection
  refused, connection reset, network unreachable)
- A bare `OSError` (connection reset during response body read)
- `UnicodeDecodeError` (response body is not valid UTF-8 — misclassified
  as CONNECTION_ERROR, but still a transport-layer failure)

### 4.2 Conditions triggering Fallback

`CONNECTION_ERROR` is in `PRIMARY_FALLBACK_ELIGIBLE_ERRORS` (15-member
frozenset). When the Primary attempt returns `CONNECTION_ERROR`:

1. `SemanticRuntime.evaluate()` checks eligibility: `primary_attempt.status.value
   in PRIMARY_FALLBACK_ELIGIBLE_ERRORS` → True for CONNECTION_ERROR
2. `fallback_reason = _STATUS_TO_FALLBACK_REASON[primary_attempt.status]`
   → `SemanticRuntimeFallbackReason.CONNECTION_ERROR`
3. The Fallback transport is called exactly once
4. If Fallback succeeds: 2-attempt SUCCESS result
5. If Fallback fails: 2-attempt FAILURE result with the Fallback's error type

### 4.3 Distinguishing root causes of CONNECTION_ERROR

The current V1 transport does NOT distinguish between:
- DNS resolution failure (NXDOMAIN, SERVFAIL, timeout)
- Connection refused (remote port closed)
- Connection reset (TCP RST mid-stream)
- Network unreachable (no route to host)
- Proxy-related failure
- TLS handshake failure (mapped to `TLS_ERROR` separately)
- Response body decode failure (`UnicodeDecodeError` → CONNECTION_ERROR)

**Evidence that would distinguish them:**

| Cause | Evidence needed |
|-------|----------------|
| DNS failure | `str(e.reason)` would contain "Name or service not known" or the specific errno |
| Connection refused | `str(e.reason)` would contain "Connection refused" (errno 111 on Linux, 10061 on Windows) |
| Proxy issue | The transport uses `build_opener(NoRedirectHandler)` — NO proxy handler is installed, so ambient proxy env vars are ignored for the semantic transport. BUT: the Vendor API adapter explicitly uses `ProxyHandler({})`. Neither semantic transport uses a proxy. |
| Server-side | HTTP error codes (4xx/5xx) would be caught as `HTTPError` → classified by `_classify_http_error()`, NOT as CONNECTION_ERROR |
| Malformed response | 200 OK response that is not valid UTF-8 → caught as `UnicodeDecodeError` → CONNECTION_ERROR (misclassification) |

**KEY FINDING:** The V1 semantic transport does NOT install a proxy handler.
It uses the bare `urllib.request.build_opener(NoRedirectHandler)`. Ambient
`HTTP_PROXY`/`HTTPS_PROXY` environment variables are NOT used by this transport.
This means proxy configuration issues would NOT affect the semantic transport
unless the underlying network stack itself is configured to route through a
proxy (system-level, not Python-level).

### 4.4 urllib request timeout behavior

The V1 transport applies timeout via:

```python
opener.open(req, timeout=self._request_timeout_seconds)
```

**This is a per-socket operation timeout, NOT a guaranteed whole-request
deadline.** Python's `urllib.request.urlopen()` with `timeout`:

- Sets the timeout on the initial socket connect
- Sets the timeout on each `recv()` call
- Does NOT impose a wall-clock deadline on the entire request

For a streaming response (e.g., the model generates tokens over 280 seconds
with each chunk arriving within the timeout window), the total request can
exceed `request_timeout_seconds`. The default is 300 seconds, so in practice
a 280-second inference would complete within a single socket timeout window.

However, a request that stalls for more than 300 seconds between any two
data receptions will raise `TimeoutError`.

### 4.5 Per-attempt latency fields in memory

The V1 runtime records per-attempt timing:

```python
@dataclass(frozen=True)
class SemanticAttempt:
    provider: str
    model: str
    status: SemanticAttemptStatus
    latency_ms: float  # ← measured with time.perf_counter()
```

Each `SemanticRuntimeResult.attempts` tuple contains 1 or 2 `SemanticAttempt`
objects, each with its own `latency_ms`. The `SemanticRuntimeResult.to_dict()`
serializes these:

```python
def to_dict(self) -> dict[str, Any]:
    return {
        ...
        "attempts": [a.to_dict() for a in self.attempts],
        ...
    }
```

Where `SemanticAttempt.to_dict()` returns:
```python
{"provider": ..., "model": ..., "status": ..., "latency_ms": ...}
```

### 4.6 Which fields are currently persisted

| Field | In memory? | Persisted? | Where? |
|-------|-----------|------------|--------|
| `SemanticAttempt.provider` | Yes | **NO** | — |
| `SemanticAttempt.model` | Yes | **NO** | — |
| `SemanticAttempt.status` | Yes | **NO** | — |
| `SemanticAttempt.latency_ms` | Yes | **NO** | — |
| Per-candidate success/failure | Yes | Yes | `ExecutionEvidenceRecord` (outcome + detail_code) |
| Per-candidate candidate_url | Yes | Yes | `ExecutionEvidenceRecord.candidate_url` |
| Per-candidate persistence time | — | Yes | `ExecutionEvidenceRecord.created_at` |
| Semantic decision (MATCH/NO_MATCH/UNCERTAIN) | Yes | Indirectly | `ExecutionEvidenceRecord.detail_code` (only for successful evals) |
| For MATCH: confidence, reason, attributes, provider, model | Yes | Yes | `AiAssistedReviewCandidate` (only for MATCH outcomes) |
| For non-MATCH or failure: full result dict | Yes | **NO** | — |

**CRITICAL GAP:** The complete `SemanticRuntimeResult` (including all
per-attempt provenance and latency) is available in memory during execution
but is **never persisted** for non-MATCH outcomes. For MATCH outcomes, only
a subset of fields is persisted in `AiAssistedReviewCandidate`, and
per-attempt latency is **not** among them.

---

## 5. Corrected Windows CMD Diagnostics

### 5.1 Environment: CMD only, WinSW service, Waitress 8080

The deployment is:
- **Shell:** Windows CMD (not PowerShell, not bash)
- **Service:** WinSW `ProductIntelligencePilot`
- **Web server:** Waitress on port 8080
- **Python venv:** `C:\Product_Intelligence\.venv`
- **Production data:** Outside Git checkout

### 5.2 Safe read-only CMD commands

**Check service status:**
```cmd
sc query ProductIntelligencePilot
```

**Check if Waitress is listening on 8080:**
```cmd
netstat -an | findstr "8080"
```

**Read WinSW service log (last 50 lines):**
```cmd
type "C:\Product_Intelligence\win-sw\ProductIntelligencePilot-service.log" | more +^-50
```
Or more precisely:
```cmd
powershell -Command "Get-Content 'C:\Product_Intelligence\win-sw\ProductIntelligencePilot-service.log' -Tail 50"
```
Note: This is PowerShell invoked from CMD for tailing; pure CMD alternative:
```cmd
type "C:\Product_Intelligence\win-sw\ProductIntelligencePilot-service.log"
```
(manually scroll to end)

**Check semantic transport connectivity (Primary — amax):**
```cmd
ping -n 1 -w 5 api.amax.ai
```
Or DNS resolution:
```cmd
nslookup api.amax.ai
```

**Check Fallback endpoint reachability:**
```cmd
ping -n 1 -w 5 <vllm-262k-host>
```
(The actual hostname is in `PI_SEMANTIC_VLLM_262K_BASE_URL`)

**Read environment variables inherited by CMD shell:**
```cmd
set PI_SEMANTIC
set PI_VENDOR
```
**CRITICAL:** These show values in the interactive CMD environment, which
may differ from what the WinSW service process inherits. WinSW services
typically inherit the system environment at service start time, not the
current interactive session.

**Read WinSW service configuration for environment:**
```cmd
type "C:\Product_Intelligence\win-sw\ProductIntelligencePilot.xml"
```
The `<environment>` section in the XML file shows what variables the service
process receives.

**Test semantic Primary connectivity from the production venv:**
```cmd
C:\Product_Intelligence\.venv\Scripts\python -c "import urllib.request; r = urllib.request.urlopen('https://api.amax.ai/v1/models', timeout=10); print(r.status)"
```

**Check Vendor API connectivity:**
```cmd
C:\Product_Intelligence\.venv\Scripts\python -c "import os; print(os.environ.get('PI_VENDOR_LOOKUP_BASE_URL', 'NOT SET'))"
```

**Check for ambient proxy settings (system-level):**
```cmd
set HTTP_PROXY
set HTTPS_PROXY
set http_proxy
set https_proxy
```

**Check DNS resolution for semantic endpoints:**
```cmd
nslookup <primary-hostname>
nslookup <fallback-hostname>
```

**Read Django settings for database connectivity:**
```cmd
C:\Product_Intelligence\.venv\Scripts\python -c "import django; django.setup(); from django.conf import settings; print(settings.DATABASES['default']['HOST'])"
```

### 5.3 What NOT to do

- **Do not** use `/dev/null` (Unix-only)
- **Do not** use `pilot_check --json` (does not exist)
- **Do not** use `grep`, `awk`, `head`, `tail` (not available in CMD)
- **Do not** use `curl` (not standard on Windows; use `python -c` with urllib instead)
- **Do not** print full values of `PI_SEMANTIC_AMAX_API_KEY`, `PI_SEMANTIC_VLLM_262K_API_KEY`, or any `*_BASE_URL` that contains authentication tokens
- **Do not** restart services or modify configuration
- **Do not** issue chat completions to any provider

### 5.4 CMD vs WinSW environment distinction

| Source | Shows |
|--------|-------|
| `set PI_*` in CMD | Interactive session environment (may differ from service) |
| WinSW `.xml` `<environment>` | Variables injected into the service process at startup |
| Windows System Environment (System Properties → Environment Variables) | Baseline for all services |
| User Environment Variables | Not inherited by services running as LocalSystem or NetworkService |

**A `CONNECTION_ERROR` in the semantic transport that works from CMD but
not from the service would indicate a service environment difference** —
most commonly: missing proxy configuration, different network interface,
or firewall rules applied to the service account.

---

## 6. Recommended Minimal Corrective Implementation

### 6.1 The evidence gap

The current V1 runtime produces rich per-attempt provenance in memory
(`SemanticRuntimeResult` with `attempts: tuple[SemanticAttempt, ...]`) but
persists only a thin `stage/outcome/detail_code` record for each candidate.
This means:

- Per-attempt latency is lost after execution
- Primary vs Fallback routing history is partially lost (only for MATCH outcomes)
- Non-MATCH successful results (NO_MATCH, UNCERTAIN) leave only the evidence record
- Failed results leave only the evidence record (no per-attempt detail)

### 6.2 What a correction must preserve

Before recommending any persistence change, the existing contracts were
inspected:

**V1 Result and model contracts:**
- `SemanticRuntimeResult` is a frozen dataclass with `to_dict()` serialization
- `AiAssistedReviewCandidate` model has 20 fields (12 immutable provenance,
  1 mutable review state, 2 FK/identity)
- `ExecutionEvidenceRecord` has 7 fields (run FK, attempt_number, stage,
  outcome, candidate_url, detail_code, created_at)
- `PriceIntelligenceSnapshot` carries the encoded aggregation result only

**Existing execution evidence storage:**
- `ExecutionEvidenceRecord` has no JSON blob for arbitrary per-stage data
- Adding one would require a migration and a new field
- The `detail_code` field is a fixed 64-character CharField from a
  controlled vocabulary

**Schema and codec compatibility:**
- `PriceIntelligenceSnapshot` uses versioned codec (schema_version field)
- Backward-compatible append is the approved pattern (FU3A/FU3B precedent)

**Frozen semantic runtime safety:**
- `SemanticRuntime`, `SemanticRuntimeConfig`, `SemanticRuntimeResult`,
  `SemanticAttempt` are all frozen dataclasses
- The runtime's `evaluate()` method returns `SemanticRuntimeResult`
- `semantic_integration.py` calls `evaluate()` and writes evidence records
- Modifying the runtime's return type would break the integration contract

### 6.3 Proposed minimal approach (NOT implemented — design only)

**Option A: Add per-candidate provenance to `ExecutionEvidenceRecord`**

Add one optional JSON field to `ExecutionEvidenceRecord`:

```python
# New field on ExecutionEvidenceRecord
semantic_provenance = models.JSONField(
    blank=True,
    null=True,
    default=None,
    help_text='V1 semantic per-attempt provenance (only for SEMANTIC stage).',
)
```

The `semantic_provenance` would carry the `SemanticRuntimeResult.to_dict()`
output for SEMANTIC-stage records only. Other stages leave it `null`.

**Backward compatibility analysis:**
- Existing non-null `detail_code` records remain valid (the new field is
  `null` for historical records)
- The `detail_code` vocabulary is unchanged
- Replay: a reader must tolerate `semantic_provenance` being `null`
  for historical records
- Migration: additive-only (new nullable JSONField), no data migration
  needed for existing rows

**Changes required:**
1. Migration: add `semantic_provenance` JSONField (nullable)
2. `evidence_writer.py`: accept optional `semantic_provenance` parameter
3. `semantic_integration.py`: pass `semantic_result.to_dict()` when writing
   SEMANTIC evidence records
4. Reader: tolerate `null` for historical replay

**Impact:** +1 database field, +1 migration, +2 source file changes,
backward-compatible append-only provenance.

**Option B: Extend `AiAssistedReviewCandidate` for all outcomes**

Currently `AiAssistedReviewCandidate` exists only for MATCH outcomes.
Creating a record for ALL semantic evaluation outcomes (MATCH, NO_MATCH,
UNCERTAIN, FAILED) would persist per-attempt provenance for all candidates.

**Problem:** This model is named and designed for human review of MATCH
outcomes. Extending it to all outcomes would change its semantics and
require a rename or significant redesign.

**Not recommended without a separate design phase.**

### 6.4 Recommendation

**Option A is the minimal, backward-compatible approach.** It:

- Preserves the existing `ExecutionEvidenceRecord` structure
- Adds provenance as an additive optional field
- Maintains append-only semantics (historical records remain valid)
- Does not modify frozen runtime contracts
- Does not change codec versions or replay behavior
- Can be implemented in a separate phase without touching V1 runtime logic

**Implementation would be Phase: PERF-SEM-INV1-FU1-CORRECTIVE** (separate
from this investigation).

---

## 7. Statements Retracted from Original INV1 Report

Based on the production baseline correction, the following statements from
the original PERF-SEM-INV1 report are retracted or corrected:

### 7.1 Retracted: V2 semantic runtime was part of the production analysis

The original report may have referenced or assumed the existence of:
- `runtime_v2.py` (Semantic V2 runtime, S2-C)
- `semantic_decision_v2_execution.py` (V2 live execution wiring)
- V2 authority qualification concepts (`V2_AUTHORITY_QUALIFIED`)
- V2 per-candidate persistence (`SemanticDecisionRecordV2`)

**Correction:** None of these files exist at the deployed production SHA.
The production baseline uses V1 semantic runtime exclusively. Any V2
behavior described in the original report does not apply to the Micron
production run.

### 7.2 Retracted: Each inference took exactly 30 seconds

The original report may have assumed a fixed 30-second inference time.

**Correction:** No inference time was measured or persisted. The V1 runtime
measures per-attempt latency with `time.perf_counter()` in memory, but this
data is not persisted. The only timing evidence is the `created_at` timestamps
on `ExecutionEvidenceRecord` rows, which record persistence time, not
evaluation time. Any per-inference timing claim is an unsupported estimate.

### 7.3 Retracted: Every Primary attempt failed (CONNECTION_ERROR)

The original report may have assumed that all 10 candidates failed Primary
and retried Fallback, based on stderr warnings.

**Correction:** The 21 `CONNECTION_ERROR` warnings in stderr are not
definitively attributed to this run. They may span multiple concurrent runs.
Without per-attempt persistence, it is unknown how many of the 10 candidates
used Primary-only, Primary+Fallback, or Primary-only-failed paths. The
`CONNECTION_ERROR` count of 21 exceeds the candidate count of 10, suggesting
additional sources of warnings.

### 7.4 Retracted: Every CONNECTION_ERROR completed immediately

The original report may have assumed that connection errors returned
instantly, contributing no meaningful latency.

**Correction:** `CONNECTION_ERROR` in the V1 transport covers: DNS failure,
connection refused, connection reset, network unreachable, and response body
decode failure. DNS failure and connection refused may take up to the full
socket timeout (300 seconds) before returning. The urllib `timeout` parameter
is a per-socket timeout, not an immediate failure. Without per-attempt
latency persistence, the actual duration of failed attempts is unknown.

### 7.5 Retracted: V2 `SemanticDecisionAttempt` extension proposal

The original report proposed extending V2 `SemanticDecisionAttempt` for
timing evidence.

**Correction:** V2 `SemanticDecisionAttempt` does not exist at the production
SHA. The correction proposal in Section 6.3 above targets V1
`ExecutionEvidenceRecord` instead.

---

## 8. Worktree Status and Evidence of Zero Modifications

### 8.1 Worktree state (read at investigation time)

```
Current HEAD: 916296a (divergent main branch, NOT production baseline)
Modified: tmp_collection.txt (pre-existing, unrelated)
Untracked: V2 design docs, evaluation artifacts, INV1 report, test file
```

### 8.2 Files inspected (read-only, via `git show`)

All production baseline inspection used `git show cde2a80:<path>`. No files
were modified, no branches were switched, no git operations were performed
on the worktree beyond read-only inspection.

### 8.3 No changes made

- No source or test file modifications
- No database writes or migrations
- No service restarts or configuration changes
- No git restore/reset/checkout/stash/clean
- No commits or pushes
- All existing artifacts preserved

---

## Final State

**INVESTIGATION CORRECTED / PENDING CHATGPT REVIEW**

This report corrects the production baseline identification error in the
original PERF-SEM-INV1 report. The deployed baseline is V1-only (no V2
semantic runtime). The V1 execution path, candidate count, timing bounds,
connection error taxonomy, transport analysis, and Windows diagnostics have
been reconstructed from the actual production code at the deployed SHA.

The previous report's V2-specific claims are retracted. The corrected
analysis identifies a material evidence gap (per-attempt latency not
persisted) and proposes a minimal backward-compatible correction (Option A:
additive JSON field on `ExecutionEvidenceRecord`) for a separate
implementation phase.

This investigation makes NO implementation changes. It does NOT declare
APPROVED, FIXED, or FROZEN.
