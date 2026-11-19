# SEMANTIC-V2-PERFORMANCE-DESIGN-01 — Performance Evidence of Record

**Status:** DESIGN-ONLY companion to `docs/SEMANTIC_V2_PERFORMANCE_DESIGN_01.md`
(**revision FU2, updated in place; the FU1 notes below remain**).
Sanitized re-review of the LOCAL-UAT-PERF-01 latency evidence. No
production code, prompt, route, output limit, fallback policy, authority,
test, or persistence semantics are changed by this document. FU1
additions of record: the [D] lease-consequence note in §3, the input-
persistence pointer in §5, and the new §8 (V2 input persistence coverage,
source-verified at the base for the design's B1/B2/B4/B5 corrections).
FU2 additions of record: the §3 [D] overlapping-execution note (design
C2), and the new §8.14 (runtime failure semantics — persistable vs.
unpersistable, source-verified for design C1) + §8.15 (the one-at-a-time
Scheduler service rate and queue — derived, for design C3). The design's
fixed 30-minute lease is superseded there by the configured-timeout lease
formula `L(T) = 2T + M_EVAL + M_LEASE` (see §3, §8, design §4.2 FU1 B2).

**Sanitization record.** This document contains no API keys, no provider base
URLs, no environment variable values, no raw provider payloads, and no raw
model output text. The UAT database is referenced by role only (the local
UAT SQLite database queried strictly read-only; its path of record is in the
LOCAL-UAT-PERF-01 run report and is deliberately not reproduced here). Route
identifiers (`amax` / `qwen3.8-27b`, `vllm-262k` / `Qwen3.6-27B-262K`) are the
frozen V2 contract data already committed in
`product_intelligence/semantic/runtime_v2.py`. The single evaluated candidate
is a public retail listing (servertechsupply.com) identified to bind the
ledger row.

**Classification discipline.** Every figure below is labeled exactly one of:

- **[M] measured** — read directly from a preserved artifact or the UAT
  database in this session, or recomputed from raw preserved data.
- **[D] derived** — arithmetic over measured quantities (stated).
- **[H] hypothesis** — not established by any preserved measurement; stated
  as such, with what would be required to test it.
- **[U] unobservable** — not recorded by design or not available; no value
  is claimed.

The untracked analysis document
`docs/LOCAL_UAT_PERF_01_SEMANTIC_V2_LATENCY_ANALYSIS.md` was re-verified
figure-by-figure against these sources; its validated content is incorporated
below with the corrections of §7. That untracked document is preserved
unchanged.

---

## 1. The UAT execution evidence (resolves the PRIMARY-vs-fallback question)

Source: the local UAT SQLite database, queried read-only
(`file:...?mode=ro`). Tables of record: `runs_researchrun`,
`runs_semanticdecisionrecord` (the semantic decision ledger; one JSON
envelope payload per (run, assessment_index) + a separate canonical digest
column), `runs_executionevidencerecord`, `runs_researchsupplementsnapshot`,
`runs_researchfxsnapshot`.

### 1.1 ResearchRun `bd992103-4f83-4264-9a06-571b454530e5` (stored UUID:
hyphen-less `bd9921034f8342649a06571b454530e5`)

| Item | Value | Class |
| --- | --- | --- |
| Run window | `2026-11-18 23:38:00.576396` → `23:39:46.264252` UTC | [M] `runs_researchrun.created_at` / `finished_at` |
| Run duration | **105.688 s** | [D] subtraction |
| V2-eligible candidates | exactly 1 (assessment_index 0; substate U2_SKU_ONLY; source: the servertechsupply.com listing) | [M] ledger `binding.assessment_index` + `case.deterministic_identity_context.substate` |
| V2 model attempts | **exactly 1**: role `PRIMARY`, attempt_number 1, provider `amax`, model `qwen3.8-27b`, outcome `OK` | [M] ledger `execution.attempts` (one element) |
| PRIMARY provider/model | `amax` / `qwen3.8-27b` | [M] ledger `execution.actual_provider` / `actual_model` |
| FALLBACK used | **No** — `execution.fallback_used = false`, `fallback_reason = null`, `error_type = null`; no second attempt entry exists | [M] ledger `execution` |
| Evaluation started | `2026-11-18T23:38:17.397051Z` | [M] ledger `execution.evaluation_started_at` |
| Evaluation finished | `2026-11-18T23:39:42.124653Z` | [M] ledger `execution.evaluation_finished_at` |
| Evaluation window | **84.727602 s** | [D] subtraction |
| Share of run | **80.17 %** | [D] 84.727602 / 105.687856 |
| Final V2 outcome | `evaluation_state = EVALUATED`, decision `UNCERTAIN`, confidence `MEDIUM`, reason `UNCERTAIN_MISSING_CRITICAL_ATTRIBUTES` | [M] ledger `evaluation` |
| Record contract | `("V2", "2.0", 1, 1, "SEMANTIC_AUTHORITY_V2_S2A_FU2")`, prompt 2.0 | [M] ledger `contract` |
| Ledger row persisted at | `23:39:46.262684` — 1.6 ms before run finish | [M] `runs_semanticdecisionrecord.created_at` vs run `finished_at` (confirms persistence inside the atomic publication) |

**Question: does the 84.73 s window represent one attempt or multiple?**
One attempt. The ledger records one entry per transport attempt actually
made (the persisted `SemanticDecisionAttempt` keeps role/provider/model/
outcome per attempt; `_attempts_from_result` in
`execution/semantic_decision_v2_execution.py` maps the in-memory attempt
sequence one-to-one). Exactly one entry exists, it is `PRIMARY`, and
`fallback_used` is `false`. The 84.727602 s window is therefore the single
primary `amax`/`qwen3.8-27b` round trip, not a primary+fallback sum. [M]+[D]

**Reconciliation of the contradictory previous statements.**
The LOCAL-UAT-PERF-01 run report stated decisively "1 call, single attempt
(PRIMARY), OK, no fallback used". The untracked analysis document instead
left both hypotheses open ("If it was the amax primary (attempts=1) … If it
was a two-attempt case (primary execution failure + fallback on the B300
vLLM) …"). Both documents were read before the ledger of the UAT database
was re-queried in this session. The ledger (above) **confirms the run
report and refutes the two-attempt hypothesis for this run**: there was no
primary execution failure (attempt outcome `OK`, `error_type` null), no
fallback attempt was made, and the actual provider is the primary. The
analysis document's own escape clause applies — it stated the ledger's
`fallback_used`, attempt count, and `actual_provider` "distinguish these two
hypotheses"; they now have. [M]

**Unrecoverable for this run (by design, not by accident):**

- Completion-token count of the 84.73 s call: [U] — the production runtime
  carries no usage field (`SemanticRuntimeResultV2` has no token fields;
  `TransportResult.token_usage` is in-memory only and dropped when the
  persisted record is built).
- Per-attempt latency split inside the persisted record: [U] — with one
  attempt the window equals the attempt, so this is moot for this run; with
  more than one attempt the persisted record would not split them (only
  `SemanticAttempt.latency_ms` holds it in memory).
- Provider-internal queue / prefill / decode split, TTFT: [U] — the
  transport is non-streaming (no `stream` anywhere in
  `product_intelligence/semantic/transport.py`); a single wall-clock
  `latency_ms` per attempt is all the client observes.
  **None of queue delay, hidden reasoning length, or GPU contention is
  asserted as the cause of the 84.73 s; they remain [H] hypotheses** until
  per-attempt latency + token usage are persisted (design Option A1 /
  Phase 0).

### 1.2 Sibling run `37826c4f6cf542d183dbeab8d833d26c` (same UAT window)

| Item | Value | Class |
| --- | --- | --- |
| Run window | `23:16:08.204798` → `23:19:59.164744` UTC = **230.960 s** | [M]/[D] |
| V2-eligible candidates | 5 (assessment indices 0, 1, 3, 4, 6) | [M] ledger |
| V2 attempts | each record: exactly 1, `PRIMARY` `amax`/`qwen3.8-27b` `OK`, `fallback_used = false` | [M] ledger (all five rows) |
| Per-evaluation windows | 31.113769 / 36.993613 / 50.254236 / 29.583017 / 50.137606 s | [M] ledger |
| V2 total | **198.082241 s** (85.77 % of the run) | [D] |
| Serial discipline | each `evaluation_started_at` = previous `evaluation_finished_at` + 0.3–0.4 ms | [M] (the V2 loop evaluates candidates one after another) |
| Outcomes | NO_MATCH/HIGH (`NO_MATCH_CAPACITY`), NO_MATCH/MEDIUM (`NO_MATCH_PRODUCT_FAMILY`), UNCERTAIN/MEDIUM (`UNCERTAIN_IDENTIFIER_RELATION`), UNCERTAIN/MEDIUM (`UNCERTAIN_MISSING_CRITICAL_ATTRIBUTES`), UNCERTAIN/MEDIUM (`UNCERTAIN_MISSING_CRITICAL_ATTRIBUTES`) | [M] |

### 1.3 Stage evidence for run `bd992103` (re-verified from
`runs_executionevidencerecord`, 23 rows)

| Stage | Window (UTC) | Elapsed | Evidence | Class |
| --- | --- | --- | --- | --- |
| Claim (created → RUNNING) | 00.576 → 00.592 | 0.015 s | 1 | [M] |
| Micron catalog authority (4D-D) | 00.592 → 01.190 | 0.60 s | 1 fetch, `NO_AUTHORITY_MATCH` | [M] |
| Serper paid search | 01.190 → 02.374 | 1.18 s | exactly 1 `SEARCH`/`OK` call | [M] |
| Candidate fetch/extract/normalize/match | 02.374 → 07.217 | 4.84 s | 10 fetches: 4 `OK` + 6 `NETWORK_ERROR` (remote fast-fails 0.16–0.27 s); 1 empty extract (`NO_LISTING_OBSERVATIONS`); 2 `ACCEPTED` + 1 `NO_MPN_IN_OBSERVATION` | [M] |
| Semantic V1 (amax `qwen3.8-27b`, prompt 1.1) | 07.217 → 17.384 | 10.17 s | 1 call → `SEMANTIC_MATCH`, 1 UNREVIEWED review candidate | [M] |
| Aggregate | 17.384 → 17.391 | 0.007 s | 2 price buckets, AMBIGUOUS | [M] |
| **Semantic V2 (prompt 2.0)** | **17.397 → 42.125** | **84.73 s** | **1 call, 1 attempt, primary, `UNCERTAIN`** | [M] |
| Vendor API lookup (4D-B) | 42.125 → 45.000 (1-s resolution) | ≈2.9–3.4 s | 1 call, PARTIAL, 3 sources `NOT_FOUND`, 0 observations | [M] (instant) / [D] (bounds) |
| ECB FX (8A) | → 46.252 (1-s resolution) | ≈0.5–1.3 s | 1 call, acquisition LIVE (cold cross-run store — first FX on this DB) | [M] (instant) / [D] (bounds) |
| Atomic publication | → 46.264 | ≈0.01 s | snapshot + review candidate + V2 ledger row + supplement + FX rows | [M] |

Vendor/FX windows are bounded to 1-second precision by the persisted
`retrieved_at` fields; every other stage is measured at millisecond
precision from persisted evidence. The separate vendor-refresh child
(23:40:11 → 23:40:13) is a different operation and is not charged to this
run.

**Unmeasured inside each semantic round trip:** the client-network vs
model-server split and the server-side queue/prefill/decode phases — [U]
(non-streaming transport, §1.1).

---

## 2. Provenance of the prompt/completion token counts and latency
distributions

### 2.1 Q3-B live capture (the only preserved V2 token/latency population)

Artifact: `semantic_v2_live_captures/q3b-20261009T010312Z-amax__direct__
amax_qwen3.8-27b__manifest.json` (per-case `latency_ms`, `token_usage`,
`finish_reason`, `attempts`) + the capture document (`records[].raw_output`
— the visible JSON only) + `q3b2-primary-recall-diagnosis.md`. All values
below recomputed in this session from those files.

- Population: 43 of 56 corpus cases (the eligible ones); amax `qwen3.8-27b`;
  prompt 2.0; manifest `generation_parameters` records
  `max_tokens: 32768`, `temperature: "0.0"`, and `transport_parameters`
  records `request_timeout_seconds: 300.0`.
- Latency: min **7.630 s**, p50 **21.559 s**, p90 **45.798 s**
  (nearest-rank), max **120.499 s**. Sum of per-case latencies **1227.1 s**
  vs manifest wall time **1227.145 s** (`started_at` 01:03:12.810Z →
  `finished_at` 01:23:39.956Z) — the equality is the measured proof of
  sequential execution. [M]
- Prompt tokens (server-reported `usage`): 2,638 – 3,073 (p50 2,674). [M]
- Completion tokens (server-reported `usage`): 603 – 9,248 (p50 2,475,
  mean 3,052.4). [M]
- Visible JSON (`raw_output`): 277 – 1,189 chars (p50 680). [M]
- `finish_reason`: `stop` on all 43; `attempts = 1` on all 43; no retries.
  [M]
- Provenance note on "max_concurrency: 1": the Q3-B manifest predates the
  additive `max_concurrency` field (added by Q3-B-FU1, runner
  `live_capture.py`); the sequential execution is established by (a) the
  runner's default `LIVE_DEFAULT_CONCURRENCY = 1` and (b) the measured
  wall == Σ latencies above. [M]+[D]

**The gap between completion tokens and visible JSON (p50 2,475 tokens vs
680 visible chars) is [M] as a difference; its attribution to hidden model
reasoning is [H]** — the V2 output contract has no chain-of-thought field
(`SemanticMatchResponseV2`: "no prose field exists"), so the extra tokens
are not visible output, but the client cannot see what the provider
generated internally (non-streaming). The frozen 2.0 system prompt (9,632
chars; REAL system-prompt digest `c0cc98bd…`, verified in this session via
`canonical_sha256({"text": SYSTEM_PROMPT_V2})`) requires per-attribute
dimension+detail observations and a sales-unit analysis — a materially more
deliberative output shape than V1. [M] (contract text) + [H] (mechanism)

### 2.2 V1 benchmark (same amax model, prompt 1.1) — the control

Artifact: `semantic_benchmark_runs/20260928T231936__amax_qwen3.8-27b--
048e146e/` (`responses.jsonl` 64 rows + manifest). Recomputed here.

- Latency: min 2.086 s, p50 3.275 s, max 20.416 s. [M]
- Prompt tokens: 1,314 – 1,380 (p50 1,348). [M]
- Completion tokens: 225 – 2,378 (p50 366.5, mean 448.2). [M]
- Visible JSON: 238 – 614 chars (p50 390). [M]
- Implied decode rate p50: 366.5 / 3.275 ≈ **111.9 tok/s**. [D]

### 2.3 B300 vLLM fallback route (V1 prompt, different model)

Artifacts: `semantic_benchmark_runs/20260827T171159__vllm-262k_Qwen3.6-
27B-262K--41458c0a/` (prompt 1.1) and `20260826T014727__vllm-262k_Qwen3.6-
27B-262K--41458c0a/` (prompt 1.0). Recomputed here.

- 2026-08-27: p50 completion 1,288 tokens / p50 latency 30.238 s →
  **42.6 tok/s** [M]+[D]
- 2026-08-26: p50 completion 1,076 tokens / p50 latency 22.792 s →
  **47.2 tok/s** [M]+[D]

This is a throughput observation across different models (Qwen3.6-27B-262K
vs qwen3.8-27b), not a defect finding.

### 2.4 Rendered prompt sizes (this tree)

| Prompt | System chars | User chars (Q3-B 43 eligible cases) | Class |
| --- | --- | --- | --- |
| V1 1.1 (`semantic/contract.py`) | 4,136 | n/a here | [M] |
| V2 2.0 (`semantic/contract_v2.py`, digest `c0cc98bd…`) | 9,632 | 2,153 – 3,346 (p50 2,219) — rendered in this session through the frozen `build_semantic_prompt_v2` over the corpus-decoded cases | [M] |
| V2 2.1 (`semantic/contract_v2_1.py`, qualification-harness only; **not** imported by the live runtime) | 27,789 | n/a | [M] |

### 2.5 The 84.73 s call in the measured V2 population (derived only)

- The 84.728 s window sits inside the measured V2 latency range
  (7.6 – 120.5 s), in its upper third. [D]
- If the p50 decode rate (≈114.8 tok/s = 2,475 / 21.559) applied to this
  call, it implies ≈ 9,700 completion tokens — slightly ABOVE the observed
  capture maximum (9,248). This is an extrapolation from the p50 rate, not
  a measurement; the true value is [U] (§1.1). It does show the call is
  consistent with a very long deliberative output, but **no token count,
  queue time, TTFT, or GPU-contention figure for the UAT call is claimed**.
  [H]

---

## 3. Frozen-contract inventory (what the performance work must not move)

All [M] from the current tree at base `33e7f42`:

- V2 route: PRIMARY `amax`/`qwen3.8-27b`, FALLBACK `vllm-262k`/
  `Qwen3.6-27B-262K` (`runtime_v2.py`, drift-pinned to the frozen FU3A
  route).
- `SEMANTIC_TEMPERATURE_V2 = 0.0`, `SEMANTIC_MAX_TOKENS_V2 = 32768`;
  `validate_runtime_config_v2` rejects any deviation before any transport
  is built.
- Prompt 2.0, digest `c0cc98bdd6d3…` (verified §2.4).
- Fallback on EXECUTION FAILURE ONLY (frozen allowlist shared with V1);
  a valid primary response is final; no voting/consensus/low-confidence
  fallback. At most one primary + one fallback call per candidate.
- Request timeout: env-configurable, default **300.0 s**, hard ceiling
  **3,600.0 s** (`DEFAULT_REQUEST_TIMEOUT_SECONDS` /
  `MAX_REQUEST_TIMEOUT_SECONDS` in `semantic/runtime.py`, shared by the
  V1 and V2 runtimes via `PI_SEMANTIC_REQUEST_TIMEOUT_SECONDS`);
  `validate_runtime_config` / `validate_runtime_config_v2` reject any
  non-finite, non-positive, or > ceiling value before any transport is
  built; the qualified capture manifest pins 300.0 s. The UAT call
  (84.73 s) did not approach the ceiling. [M]
  **Consequence (FU1 B2, [D]):** one V2 evaluation is at most
  `2·T + bookkeeping` (one primary + one fallback attempt, each bounded
  by the configured T), so the design-01 fixed 30-minute lease (1800 s)
  is safe only for `T ≤ 750 s`; the design now uses the formula
  `L(T) = 2T + M_EVAL + M_LEASE` (900 s at the qualified default T =
  300 s; 7500 s at the ceiling T = 3600 s) with the grant recorded on
  the debt row + ownership generation + atomic fence (design §4.2).
  **Consequence 2 (FU2 C2, [D]):** the single-winner claim bounds
  *ownership and publication*, not *execution*: under an expired lease,
  a still-running wedged owner and a successor may execute the same
  debt's transport calls simultaneously (duplicated execution, bounded
  by the 3-attempt policy); only ONE fenced ledger publication succeeds
  (the all-or-nothing fenced completion — design §4.2). The reconcile-
  only startup pass claims nothing (design §4.10 FU2 C2).
- `V2_AUTHORITY_QUALIFIED is False` (drift-pinned in the adapter and by
  architecture tests).
- S2-C: every V2-eligible candidate is evaluated (no usable-title gate);
  ALL outcomes persist; the records persist in the atomic publication
  block ONLY; V2 outcomes are not in 4A input, not in review-candidate
  input, not in snapshot payload, not in any public summary; no V2
  human-review candidates; no change to current UI authority presentation
  before Qualification V3.
- Ledger: append-only via the single S2-B persistence service; unique
  (run, assessment_index); whole-artifact digest anchor verified on every
  read; absence of a record means "legacy semantic provenance unavailable"
  — NOT NO_MATCH, NOT NOT_EVALUATED, NOT an AI failure.
- Orchestration: step 4b runs V2 serially, after aggregation, before the
  atomic publication; `web/views.py::research_new` POST calls
  `execute_research_run` synchronously inside the browser request.

The observed 84.73 s / 198.08 s figures are therefore the frozen contract's
normal, in-contract behavior (one primary call per eligible candidate,
serial), not a misconfiguration. [M]+[D]

---

## 4. Why the calls take this long — established vs not

Established (measured, §2): output length dominates. On the same amax
endpoint/model class, V2 (prompt 2.0) p50 completion is 6.75× V1 (prompt
1.1) p50 (2,475 vs 366.5 tokens) and p50 latency is 6.58× (21.56 s vs
3.28 s), at statistically equal implied decode rates (114.8 vs 111.9
tok/s). Prompt size doubled (2,674 vs 1,348 p50 tokens) and contributes at
most a small prefill delta (heuristic bound ~1–2 s; [D] not separately
measured — the transport does not split prefill/decode). The UAT window
(84.73 s) is within the measured V2 tail.

Not established ([H]/[U] — no cause is asserted without measurement):

- Provider-side queue delay for the UAT call: [U]
- Time-to-first-token: [U]
- Whether the 84.73 s call emitted ~9,700 completion tokens: [U]
  (derived extrapolation, §2.5)
- B300/vLLM configuration or shared-GPU load effects: the fallback route
  decode is measured ≈2.6× slower per token than the amax primary
  (42.6 vs 111.9–114.8 tok/s, §2.2–2.3), but whether any *configuration*
  causes it is unanswerable from this repository; vLLM server metrics
  (running/waiting requests, KV-cache, per-request queue time) were never
  captured. [H]
- The B300 host also runs the Codex implementer profiles
  (`tools/codex/README.md`: `qwen-local` = the same model ID
  `Qwen3.6-27B-262K` as the fallback route); shared-workload contention is
  plausible and unmeasured. [H]
- The Q3-B2 diagnosis (session 2026-07-14, capture dated 2026-10-09)
  recorded that `PI_SEMANTIC_VLLM_262K_*` was ABSENT on the capture host
  (fallback fail-closed by design). Whether it is configured on the UAT
  host is in the UAT server environment, not this repository. [M] (of the
  diagnosis) / [U] (of the UAT host).

**Corollary:** no tuning decision (route, server, prompt) is evidence-
based until per-attempt latency + provider token usage are persisted in the
production ledger (Phase 0 of the design document).

---

## 5. The blocking-path mechanics (source-confirmed at base `33e7f42`)

1. `web/views.py::research_new` POST → `execute_research_run(run.id)`
   synchronously in the browser request; redirect after return. [M]
2. `execution/orchestration.py` step 4b → `evaluate_semantic_matches_v2`
   (serial per-candidate loop; lazy runtime construction — zero
   V2-eligible candidates → zero transport calls) →
   `build_semantic_decision_records_v2`. [M]
3. Atomic publication block (`transaction.atomic()`): snapshot → V1 review
   candidates → `persist_semantic_decision_records_v2` (all V2 outcomes,
   append-only) → vendor supplement → FX → terminal transition. [M]
4. `semantic/runtime_v2.py::evaluate` → one primary attempt; fallback only
   for frozen-allowlist execution failures; per-attempt `latency_ms` and
   `token_usage` exist in memory only (`SemanticAttempt`,
   `TransportResult`) and are dropped when the persisted
   `SemanticDecisionAttempt` is built (role/provider/model/outcome only).
   [M]

Measured consequence (UAT): the browser request waits for all of 1–3
including every V2 call — 84.73 s (1 candidate) or 198.08 s (5 candidates)
of the 105.688 s / 230.960 s run windows. [M]+[D]

**Input-persistence coverage of the blocking path (FU1 B1, [M]+[D]):**
of the synchronous V2 case's inputs, exactly one value is held only in
memory — the per-assessment search-batch membership (which assessments
originated from the alias-expanded paid-search batch vs. 4D-A direct
acquisition); everything else (request identity, the full ordered
assessment array, the alias acquisition, the case_id index) is persisted
or purely derivable from persisted rows. The minimal bounded immutable
data the design now persists per debt at publication is the recorded
`context_provenance` field (design §4.13). Full coverage table: §8.

---

## 6. Source index (evidence of record)

- UAT SQLite database (local; read-only; path of record in the
  LOCAL-UAT-PERF-01 run report): `runs_researchrun` (8 runs),
  `runs_semanticdecisionrecord` (6 rows: 1 for `bd992103`, 5 for
  `37826c4f`), `runs_executionevidencerecord` (23 rows for `bd992103`),
  `runs_researchsupplementsnapshot`, `runs_researchfxsnapshot`.
- Previous reports: LOCAL-UAT-PERF-01 run report (per-stage table —
  re-verified row-for-row in this session, §1.3); the untracked
  `docs/LOCAL_UAT_PERF_01_SEMANTIC_V2_LATENCY_ANALYSIS.md` (validated and
  corrected per §7).
- Q3-B capture: `semantic_v2_live_captures/q3b-20261009T010312Z-amax__
  direct__amax_qwen3.8-27b__manifest.json` + `…json` +
  `q3b2-primary-recall-diagnosis.md`.
- V1 control: `semantic_benchmark_runs/20260928T231936__amax_qwen3.8-27b--
  048e146e/`.
- Fallback route: `semantic_benchmark_runs/20260827T171159__vllm-262k_
  Qwen3.6-27B-262K--41458c0a/`, `…/20260826T014727__…/`.
- Source: `product_intelligence/{semantic/{runtime_v2,runtime,transport,
  contract,contract_v2,contract_v2_1}.py, execution/{orchestration,
  semantic_decision_v2_execution, semantic_decision_persistence}.py,
  research/semantic_decision_v2.py, runs/models.py, web/views.py,
  evaluation/semantic_v2/{live_capture,report}.py}`;
  `docs/INTERNAL_PILOT_DEPLOYMENT.md` (Waitress launcher; "may take
  1-2 minutes"); `tools/codex/README.md` (B300 profiles).
  FU1 additions (source-verified at the base for design §4.13/§8): 
  `research/price_result_codec.py` (`_enc_assessment` — the full 
  assessment persistence), `research/aggregation.py` 
  (`aggregate_listing_prices` — the input-tuple order pass-through), 
  `research/micron_alias_codec.py` (`encode/decode_micron_alias_
  snapshot` — the alias round-trip), `research/semantic_v2.py` 
  (`build_semantic_match_case_v2` — the frozen case builder), 
  `scripts/run_internal_pilot.cmd` (the launcher surface), 
  `web/views.py` (the ALLOWED/DENIED access branches), 
  `providers/preferred_source_config.py` (`is_directmacro_enabled` —
  the direct-acquisition gate).

## 7. Corrections to the untracked analysis document (of record)

The untracked document is preserved unchanged. Its figures were re-verified
in this session; the following items are corrected or clarified in the
incorporated version above:

1. **§2 table header "V1 (benchmark 2026-09-28, prompt 1.0)"** — the cited
   benchmark's manifest records `prompt_version: 1.1` (as the document's
   own §1.2 states). The 1.0 label is a misstatement.
2. **"43 cases at `max_concurrency: 1`"** — the Q3-B manifest does not
   record a `max_concurrency` field (added later by Q3-B-FU1). Sequential
   execution is established by the runner default
   (`LIVE_DEFAULT_CONCURRENCY = 1`) and the measured wall-time ==
   Σ per-case latency equality (1,227.145 s vs 1,227.1 s).
3. **"within one step of the observed maximum (9,248)"** for the implied
   ≈9.6k tokens — the implied value (≈9,700 at the p50 rate) slightly
   EXCEEDS the observed maximum; it is an extrapolation, and the true
   token count of the UAT call is unrecorded.
4. **PRIMARY-vs-fallback question** — resolved against the UAT ledger:
   single PRIMARY attempt, no fallback (§1.1).
5. **"fallback-route decode is ≈2.5× slower per token"** — the recomputed
   ratio is ≈2.6× (42.6 tok/s vs 111.9–114.8 tok/s); corrected above.
6. Everything else (distributions, prompt sizes, frozen-contract values,
   stage table, decode rates) reproduced exactly.

---

## 8. V2 input reconstruction coverage (FU1 B1 — source-verified at
the base)

The design's §4.13 proof (reconstructing the exact synchronous
`SemanticMatchCaseV2` from persisted data) rests on the following
source-confirmed facts at the base. All [M] (read directly from the
committed tree at the base) unless marked [D]. This section is the
persistent-input inventory of record for the B1 correction (8.1–8.12)
and the B5 access boundary (8.13); 8.14–8.15 are the FU2 C1/C3
grounding. (The tree is code-identical across `33e7f42` → `0df5830` →
`9b2103c` — the design-01 and FU1 commits are documentation-only.)

| # | Fact (source of record) | Class |
| --- | --- | --- |
| 8.1 | The synchronous case builder chain is `evaluate_semantic_matches_v2(request, total_assessments, context_provenances_by_assessment, reviewed_target_context)` → per eligible assessment: `derive_identity_state_v2(assessment)` → `build_v2_product_evidence_profile(observation, provenances, matched_facts=frozenset())` → `build_semantic_match_case_v2(case_id=_v2_candidate_case_id(assessment, idx), request, assessment, context, product_evidence, provenances, reviewed_target_context)`. Every function is pure over its arguments; the builder re-runs and verifies the deterministic derivation (a foreign context fails closed). (`execution/semantic_decision_v2_execution.py`, `research/semantic_v2.py`) | [M] |
| 8.2 | The case_id scheme is `candidate-{sha256(source_url)[:8]}-{idx}` where `idx` is the enumeration position in `total_assessments` (the FULL ordered list, not just the eligible subset). (`execution/semantic_decision_v2_execution.py::_v2_candidate_case_id`, the `enumerate(assessments)` loop) | [M] |
| 8.3 | The request identity (MPN + description) is persisted on the run row and rebuilt by `run.to_research_request()`; the case builder refuses an assessment whose `requested_part_number` != the request MPN. (`runs/models.py::ResearchRun.to_research_request`, `research/semantic_v2.py`) | [M] |
| 8.4 | The full assessment array (every `ListingIdentityAssessment`, incl. the complete `normalized_listing.observation` — source URL, title, MPN field, SKU, brand, price/currency/availability/condition/seller text, offer URL, raw reference; the match type; the decision) is persisted in order in `PriceIntelligenceSnapshot.payload["assessments"]` by the frozen price codec; the decode round-trip is frozen and digest-anchored. (`research/price_result_codec.py::_enc_assessment` / `decode_price_aggregation_result`, `execution/orchestration.py::_encode_aggregation_result`) | [M] |
| 8.5 | The published payload order IS the evaluation order: `aggregate_listing_prices` passes the input tuple through to `PriceAggregationResult.assessments` unchanged (same objects, same order; `build_semantic_decision_records_v2` indexes against that same tuple). Therefore the ledger `assessment_index` and the case_id `idx` both equal the array position. (`research/aggregation.py::aggregate_listing_prices`, `execution/semantic_decision_v2_execution.py::build_semantic_decision_records_v2`) | [M]+[D] |
| 8.6 | The 4D-D alias acquisition (ESTABLISHED or bounded non-established) is persisted pre-search as `ResearchMicronAliasSnapshot` (bounded provenance: URLs, retrieved_at, body SHA-256, status, policy — never the catalog body) whenever a non-empty-MPN run's direct evidence was insufficient. Present ⇔ the alias fetch ran; `ESTABLISHED` ⇔ the search query was the alias-expanded form. (`execution/orchestration.py::_persist_alias_snapshot`, `research/micron_alias_codec.py::encode_micron_alias_snapshot`) | [M] |
| 8.7 | `decode_micron_alias_snapshot` round-trips the persisted payload to the self-validating `MicronAliasEligibilityResult` (strict key set, fail-closed); `reviewed_target_context_from_alias_result` is pure over that result (non-ESTABLISHED → explicit None; ESTABLISHED missing a reviewed field → fails closed). So the reviewed manufacturer target context is reconstructable from the persisted snapshot alone. (`research/micron_alias_codec.py`, `execution/semantic_decision_v2_execution.py`) | [M]+[D] |
| 8.8 | **The one input currently held only in memory:** the per-assessment search-batch membership (which assessments originated from the alias-expanded paid-search batch vs. 4D-A direct acquisition). The live path assigns `CUSTOMER_RETRIEVAL_RELATION` provenance exactly to `search_batch_assessments` when `alias_expanded`; but the snapshot payload records no direct/search boundary, the alias snapshot references no assessments, and the execution-evidence rows carry per-URL FETCH facts without batch membership. In a mixed run (direct enabled + direct-insufficient + alias ESTABLISHED) the membership is reconstructable from no durable row. (`execution/orchestration.py` step 3–4b: `search_batch_assessments`, `alias_expanded`, `v2_provenances_by_assessment`) | [M] |
| 8.9 | For the observed UAT population the gap is latent: direct acquisition is disabled on the UAT host (the launcher environment sets no `PI_PREFERRED_DOMAINS`; `is_directmacro_enabled()` is False), so every published assessment came from the single search batch. (`scripts/run_internal_pilot.cmd`, `providers/preferred_source_config.py::is_directmacro_enabled`) | [M]+[D] |
| 8.10 | **The minimal bounded immutable data that must be persisted at publication (the B1 correction):** exactly one field — the debt row's `context_provenance` (the bounded `ContextProvenance` vocabulary list for that assessment; ∅ or `[CUSTOMER_RETRIEVAL_RELATION]` in the live path), set in the atomic publication transaction from the in-memory membership and immutable thereafter. With it, every case input is persisted or purely derived (8.1–8.7); without it, 8.8 is unrecoverable. The rejected run-level `direct_assessment_count` alternative is recorded in design §4.13. | [D] (design decision, grounded in 8.1–8.9) |
| 8.11 | The no-refetch rule: reconstruction reads only the run row, the snapshot payload, the alias snapshot, and the debt row. The catalog body (SHA-256 only, 8.6) and the candidate page (fully persisted observation, 8.4) are never re-fetched; no provider/search/FX/vendor call is made. | [D] |
| 8.12 | The mandatory deterministic equivalence anchor for the ESTABLISHED Micron alias scenario is the existing motivating-run shape (`tests/execution/test_semantic_v2_motivating_case.py::TestNoMachinePriceContamination` — reviewed 4D-D catalog ESTABLISHED, alias-expanded search, the U5/NM-1 near-miss candidate carrying `CUSTOMER_RETRIEVAL_RELATION` + the reviewed target context). The reconstruction must equal the case that shape records. | [M] |
| 8.13 | **The existing web access boundary (FU1 B5):** `web/views.py::research_detail` renders the standard report (the public market evidence, the V1 review-candidate presentation, the assessment table) for every connection that holds the run UUID — the pilot report-reachability model (the report UUID is never access control; full authentication is deferred to 8C). The 4D-C-SEC CIDR gate (`vendor_price_access_allowed` over `REMOTE_ADDR` / `PI_VENDOR_PRICE_ALLOWED_CIDRS`, fail-closed) scopes ONLY the vendor commercial regions: the compact-quote vendor rows, the Vendor API status notice, the vendor supplement replay, and the vendor refresh section — the DENIED branch takes the public-only replay and never reads the vendor artifacts (total zero-knowledge, the frozen D8 standard). The V2 work-status line is therefore standard report content (never CIDR-gated); the design-01 "DENIED pages render nothing new" wording is corrected accordingly (design §4.8). (`web/views.py::research_detail`, `web/commercial_access.py::vendor_price_access_allowed`) | [M] |
| 8.14 **(FU2 C1)** | **Runtime failure semantics — persistable vs. unpersistable (source-verified):** (a) a missing provider env does NOT fail runtime construction — `SemanticRuntimeV2._build_transport` catches the adapter's `ValueError` and returns a `None` transport (bounded warning); (b) `_attempt` over a `None` transport returns a NORMALIZED attempt (`status = PROVIDER_NOT_CONFIGURED`, `latency_ms = 0.0`) — not an exception; (c) `PROVIDER_NOT_CONFIGURED` is NOT in `PRIMARY_FALLBACK_ELIGIBLE_ERRORS` (the frozen V1/V2 shared allowlist) → `evaluate` fails closed after one attempt and `_failure` returns a VALID `SemanticRuntimeResultV2` (`response = None`, `error_type = PROVIDER_NOT_CONFIGURED`, one `PRIMARY` attempt, `fallback_used = false`); (d) `build_semantic_decision_records_v2` maps every `response = None` result to `evaluation_state = RUNTIME_FAILURE` with the bounded `SemanticFailureClass` (`PROVIDER_NOT_CONFIGURED` is a legal member) — a valid, PERSISTABLE ledger record. A provider-unconfigured evaluation is therefore a persistable semantic runtime failure → the debt terminalizes `COMPLETED` (design situation #5), NEVER a debt-level `FAILED` state. (e) UNPERSISTABLE failures: a construction/validation exception (invalid `PI_SEMANTIC_REQUEST_TIMEOUT_SECONDS` → `SemanticRuntimeConfigError`), a programming exception propagated by the transport (the runtime contract: never swallowed), or a fenced-completion commit failure (the result exists in memory; no row; the debt is not terminalized; the retry policy applies) → bounded debt-level `FAILED` (`EXECUTOR_ERROR` / `RETRY_EXHAUSTED`); a `RUNTIME_FAILURE` row is never fabricated for a non-semantic error. (`semantic/runtime_v2.py` `_build_transport`/`_attempt`/`evaluate`/`_failure`/`validate_runtime_config_v2`; `semantic/runtime.py` `PRIMARY_FALLBACK_ELIGIBLE_ERRORS`; `execution/semantic_decision_v2_execution.py` `_evaluation_from_result`/`build_semantic_decision_records_v2`; `research/semantic_decision_v2.py` `SemanticFailureClass`) | [M] |
| 8.15 **(FU2 C3)** | **Scheduler one-at-a-time service rate and queue (derived):** with the design's parameters I = 60 s, O = 60 s, W(T = 300) = 660 s, the worst-case *service period* is `S = I + O + W = 780 s` per debt served; a 720 s (O + W) invocation overlaps ~12 of the 60 s triggers, skipped by the "do not start a new instance" policy — no OS-level queue (the queue is the debt table, FIFO). A debt claimed at position k (1-indexed, simultaneous publication) is bounded worst-case by k·S: k = 1 → **13 min** (inside the retained 15-minute target); k = 5 → **65 min** — the UAT N=5 shape (run `37826c4f`, 5 simultaneous debts, §1.2) exceeds the 15-minute target structurally for positions ≥ 2. The worst-case one-at-a-time service rate is `1/S ≈ 4.6 debts/h`; the measured per-evaluation windows (§1.2: 29.6–50.3 s; §2.1: p50 21.6 s, max 120.5 s) bound the practical service time the load gate (design §5.2 G1–G3) measures over the UAT population. | [D] (derived from the measured §1.2/§2.1 windows + the design's PROPOSED I/O/W parameters — not yet approved) |
