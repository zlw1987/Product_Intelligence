# LOCAL-SEMANTIC-V2-PERF-PHASE1-DIAG — Semantic V2 latency diagnosis

**Status:** DIAGNOSTIC ONLY. No production, test, prompt, route,
temperature, max_tokens, timeout, or fallback change. No live
model/provider calls, no new ResearchRuns, no database writes, no
network. UAT SQLite database queried strictly read-only
(`file:...?mode=ro` + `PRAGMA query_only=ON`).
**Branch/HEAD:** `feature/vendor-refresh-web` @
`01e937af19789d0a74bb1265acdab1d7dad1ebb5` (Phase 0 + UAT-FU1
endpoint, APPROVED and committed). All pre-existing untracked files
preserved.
**Naming note:** this task's "Phase 1" is a diagnostic milestone of the
PERF program. The design of record
(`docs/SEMANTIC_V2_PERFORMANCE_DESIGN_01.md`, FU2 revision) numbers its
own implementation steps Phase 0–3 (Phase 1 = debt lifecycle, no timing
change; Phase 2 = decouple). Both are referenced below explicitly.
Classification: **[M]** measured from a preserved artifact, **[D]**
derived arithmetic over measured quantities, **[H]** hypothesis,
**[U]** unobservable — stated, never fabricated.

## Architecture approval state (provenance of record)

* Option B (nonblocking supplementary V2) is the **preferred
  architectural candidate**, per the ChatGPT FU1 design review of
  record (commit `9b2103c`; reaffirmed by the FU2 revision commit
  `55ab0ee`, whose message states: "Option B remains the preferred
  architecture; the FU1 design is NOT yet approved for implementation").
* The committed FU2 revision of
  `docs/SEMANTIC_V2_PERFORMANCE_DESIGN_01.md` explicitly states that
  the corrected design — including the §4.12 items 1–9
  frozen-contract delta — **requires final explicit approval before
  implementation**. An architecture-direction approval (Option B
  preferred) is **not** an implementation approval.
* **No later explicit approval record exists in the repository**
  (verified in this session: the design file's git history is
  `0df5830` (design-01) → `9b2103c` (FU1, B1–B5 corrections) →
  `55ab0ee` (FU2, C1–C5 corrections); the later commits
  `447fb58`/`24857f6`/`0db104d`/`01e937af` concern the Phase 0 (A1)
  implementation and its UAT-FU1 approval only — their references to
  the "approved … direction" (Option B direction; the versioned-
  adapter direction) are the architecture-DIRECTION acceptance of
  record, and none of them approves the corrected FU2 design for
  implementation). Approval is not assumed from a previous design
  document.
* **Detailed FU2 implementation approval remains PENDING** (ChatGPT is
  the final architecture approval gate; the architecture decision is
  made separately from this diagnostic).
* **Phase 0 (A1 instrumentation) is APPROVED and completed** (commits
  `447fb58`–`01e937af`; ChatGPT review APPROVED at `01e937af`).
* The design's **Phase 1 debt-lifecycle implementation must not begin**
  without the explicit architecture approval gate.

---

## 1. Evidence base (existing evidence only)

| # | Artifact | Content |
| --- | --- | --- |
| E1 | UAT ledger `runs_semanticdecisionrecord` (7 rows; local UAT SQLite, read-only) | 105.69 s run `bd992103` (1 candidate, pre-Phase-0 contract), 230.96 s run `37826c4f` (5 candidates, pre-Phase-0, anonymous MPN), 61.58 s run `7bc925de` (1 candidate, MPN `XP15360SE70005`, **the only Phase-0-instrumented row in the local UAT ledger — not a deployed-production record**) |
| E2 | UAT ledger `runs_executionevidencerecord` (stage rows for the three COMPLETED runs) | stage windows (search / fetch / extract / normalize / match / V1 / aggregate) |
| E3 | `docs/LOCAL_UAT_PERF_01_SEMANTIC_V2_LATENCY_ANALYSIS.md` | original 105.688 s UAT analysis (untracked, preserved) |
| E4 | `docs/LOCAL_UAT_PERF_02_SEMANTIC_V2_PERF_PHASE0_UAT.md` | Phase 0 UAT report: 61.580279 s run, PERF row telemetry, findings F-1/F-2 |
| E5 | `SEMANTIC_V2_PERF_PHASE0_UAT_FU1_REVIEW.zip` (untracked package) | UAT-FU1 final report + 21-check read-only verification (UAT item 5 resolved) + full-suite evidence; ChatGPT review **APPROVED** (commit `01e937af`) |
| E6 | `docs/SEMANTIC_V2_PERFORMANCE_EVIDENCE_01.md` (FU2) | classified evidence of record; design companion |
| E7 | `semantic_v2_live_captures/q3b-20261009T010312Z-amax__direct__amax_qwen3.8-27b__manifest.json` | Q3-B qualification capture: 43 cases, amax `qwen3.8-27b`, prompt 2.0, `max_tokens` 32,768, temperature 0.0, 300 s timeout, sequential (wall 1,227.145 s == Σ per-case latency 1,227.149 s [M]). Captured by a separate qualification/evaluation workflow — **the Q3-B capture workflow does NOT write to the application's runtime ledger** (it writes only to `semantic_v2_live_captures/`); no application-ledger integration is demonstrated in this repository. |
| E8 | `semantic_benchmark_runs/20260928T231936__amax_qwen3.8-27b--048e146e/` | V1 control: same amax model, prompt 1.1, 64 cases |
| E9 | `semantic_benchmark_runs/2026082{6,7}T…vllm-262k_Qwen3.6-27B-262K…/` | fallback-route throughput (different model, prompt 1.1) |

Q3-B / V1 / fallback figures below were **recomputed in this session**
from E7/E8/E9 and match EVIDENCE §2. The Pearson correlation is
recomputed from a sanitized 43-row CSV extracted from E7 (preserved
under the stable documentation filename
`docs/LOCAL_SEMANTIC_V2_PERF_PHASE1_DIAG_CORRELATION_43.csv`;
`case_index,completion_tokens,latency_ms`; case identifiers are
replaced with a 1..43 integer index; no model outputs, prompts,
secrets, or customer data are present; numeric pairs byte-identical
to the reviewed evidence package).

## 2. Measured latency decomposition

| Run (ledger window) | N (V2-eligible) | Total | V1 semantic | **V2 (share)** | Non-V2 remainder | V2 attempts / fallback |
| --- | --- | --- | --- | --- | --- | --- |
| `bd992103` 2026-11-18 | 1 | **105.687856 s** | 10.17 s (1 call) | **84.727602 s (80.17 %)** | 20.960254 s | 1 PRIMARY `amax`/`qwen3.8-27b`; none [M] |
| `37826c4f` 2026-11-18 | 5 | **230.960 s** | ≈15.7 s (3 calls) | **198.082241 s (85.77 %)** — 5 serial windows 29.58–50.25 s | 32.877 s | 1 PRIMARY each; none [M] |
| `7bc925de` 2026-11-19 (PERF) | 1 | **61.580279 s** | 9.99 s (1 call) | **41.936347 s (68.10 %)** — `latency_ms` 41,936 persisted (agreement 0.347 ms) | 19.643932 s | 1 PRIMARY; none; `finish_reason` `stop` [M] |

Non-V2 remainder (search, fetch/extract, match, V1, vendor lookup, FX,
publication) is 19.6–32.9 s across the three runs [D]. Every V2 call in
the observed population is a single primary attempt on the qualified
route; `fallback_used = false` throughout; the 300 s ceiling was never
approached (max observed 84.73 s) [M]. **Timeout/fallback overhead is
0 s in the observed runs** — and the fallback route was not even
configured on the UAT host (`PI_SEMANTIC_VLLM_262K_*` absent [M]), so
no fallback data exists for this population.

## 3. Tokens and throughput

| Population (route / model / prompt) | n | Prompt tokens | Completion tokens | Latency (s) | Implied decode |
| --- | --- | --- | --- | --- | --- |
| **Q3-B V2 qualification capture** (amax `qwen3.8-27b`, 2.0) [M] | 43 | 2,638–3,073 (p50 2,674) | 603–9,248 (p50 2,475, mean 3,052) | 7.630–120.499 (p50 21.559, p90 45.798) | ratio of median completion tokens to median end-to-end latency: p50 2,475 / 21.559 s ≈ 114.8; overall mean 3,052 / population-mean 28.538 s ≈ 107.0 (arithmetic ratios — not measured decode throughput) |
| **V1 control** (same amax model, 1.1) [M] | 64 | 1,314–1,380 (p50 1,348) | 225–2,378 (p50 366.5) | 2.086–20.416 (p50 3.275) | ratio of median completion tokens to median end-to-end latency: p50 366.5 / 3.275 s ≈ 111.9 (arithmetic ratio — not measured decode throughput) |
| Fallback vLLM (Qwen3.6-27B-262K, 1.1) [M] | 64 / 43 | — | p50 1,288 / 1,076 | p50 30.238 / 22.792 | ratios of median completion tokens to median end-to-end latency: 1,288 / 30.238 ≈ 42.6; 1,076 / 22.792 ≈ 47.2 (arithmetic ratios — not measured decode throughput) |
| **The one Phase-0-instrumented UAT call** (E1, `7bc925de`, MPN `XP15360SE70005`; **not** a deployed-production record) [M] | 1 | **2,789** | **4,170** | **41.936** (41,936 ms) | ratio of median completion tokens to median end-to-end latency: completion 4,170 / 41.936 s ≈ 99.4 (tokens/s, by arithmetic — not a measured decode rate) [D] |

Derived positioning of the UAT calls inside the Q3-B qualification
population [**D**]: the 41.94 s / 4,170-token Phase-0-instrumented
UAT call sits at the 81st / 74th percentile respectively — above
median, not tail. The 84.73 s baseline window sits at the **97.7th
percentile** and, at the population's arithmetic completion-to-
latency ratios, implies ≈9,000–9,700 completion tokens — consistent
with (but not proof of) an upper-tail output; its true token count
is **[U]** (persisted pre-instrumentation, unrecoverable).
Across the Q3-B population, Pearson **r(completion tokens, latency) =
0.9599 (n=43)** [D]. **Source provenance and reproduction
methodology:** recomputed in this session from the E7 capture
manifest alone — per-case server-reported `token_usage.completion_tokens`
vs per-case `latency_ms`/1000 over the 43 `final_status = OK` cases;
Pearson product-moment correlation = 0.959875 (≈0.9599), re-derived
in this review from the sanitized CSV (`docs/LOCAL_SEMANTIC_V2_PERF_PHASE1_DIAG_CORRELATION_43.csv`,
43 rows, `case_index,completion_tokens,latency_ms`; case identifiers
replaced with a 1..43 integer index; no model outputs, prompts,
secrets, or customer data). The same population statistics
(p50/mean/p90) are recorded in EVIDENCE §2.1. The correlation is a
within-population statistical association; it is **not proof of any
particular provider-side latency mechanism** (decode, queue, or
prefill) — the per-call phase split is [U] (§4, H2). The Pearson
value was reported by Qwen in the FU1 review and is re-derived here
from the sanitized CSV as direct arithmetic on the documented
`latency_ms` and `token_usage.completion_tokens` pairs.
Visible JSON for V2 is only 277–1,189 chars (p50 680) vs 603–9,248
completion tokens [M] — the gap is measured; its attribution to
hidden model reasoning is **[H]** (the contract has no chain-of-
thought field; the client cannot see it).

## 4. Most likely causes — observations vs hypotheses

**Established (observed/derived):**
1. **The user waits for V2 synchronously and V2 is 68–86 % of the run
   window** in every completed UAT run, and it waits for **evidence-only
   output** (`V2_AUTHORITY_QUALIFIED` / `V2_PERF_AUTHORITY_QUALIFIED`
   are `False`; no authority consumer reads a V2 record) [M].
2. **Per-call duration is strongly associated with output-token volume
   within the measured populations, consistent with (but not proof of)
   output generation being the dominant per-call cost.** The arithmetic
   ratios of median completion tokens to median end-to-end latency for
   V1 and V2 on the same endpoint/model are similar (≈111.9 vs ≈114.8
   tokens-per-second ratios [D — §3 table]; V2 p50 completion is 6.75×
   and p50 latency is 6.58× [M]+[D]); these are ratios of medians over
   a per-case wall-clock total — they are NOT measured decode rates
   (queue/TTFT/decode split is [U], H2; no statistical equality test
   has been performed and none is claimed). r(completion tokens,
   latency) = 0.9599 (n=43) within the V2 capture population [D —
   §3 provenance, re-derived in this review from the sanitized CSV].
   The correlation alone does not establish a particular provider-side
   mechanism; it is a within-population statistical association.
   **No upper bound on prefill contribution is established** by the
   available telemetry (transport is non-streaming; per-call phase
   split is [U]).
3. **V2 duration is high-variance on the provider side**: the same MPN
   / candidate class produced 84.727602 s (2026-11-18) and 41.936347 s
   (2026-11-19) on two independent local UAT runs [M] — a V2 window
   difference of **42.791255 s**. These two runs are NOT a controlled
   before/after (Phase 0 is instrumentation-only, 1.5 days apart).
   The earlier call has **no measured completion-token count** (pre-
   Phase-0 contract, unrecoverable [U]). **Causal attribution of the
   42.791255 s difference is NOT established by the available
   telemetry.** Output-length variation is a plausible explanation,
   but provider-side queueing, throughput variation, and other
   effects (TTFT, network path, fallback invocation, prompt-token
   variation) remain unmeasured for that call. The label is **[H]**,
   not [D]: the per-call phase split is [U] and no value is claimed.
4. **Timeout and fallback overhead are not material**: zero fallback
   usage, zero near-ceiling calls in the whole observed population
   [M].

**Hypotheses (not established):**
- **H1 — hidden reasoning is the mechanism behind the 6.75× token
  growth** [H]: the visible/total gap is measured; what the provider
  generated internally is not. Testable only by provider-side
  visibility (streaming/TTFT) or a re-qualified prompt — both outside
  this phase.
- **H2 — tail calls include provider queue/prefill/decode
  degradation** [H]/[U]: the non-streaming transport records one
  wall-clock total per attempt; queue, TTFT, and the queue/prefill/
  decode split are **unobservable from this repository**, and no value
  is claimed.
- **H3 — B300/vLLM configuration bottleneck** [H]: affects the
  fallback route only, which never executed in the observed population
  (and is unconfigured on the UAT host). The only measured fallback
  effect is ≈2.6× slower per-token decode, across a *different model*
  — a throughput observation, not a defect finding. Unanswerable
  without vLLM server metrics.

**What cannot be determined without TTFT / queue / prefill / decode
breakdowns:** the per-call phase split; whether the 84.73 s call was a
long output at normal rate or a shorter output at degraded rate (or a
queued call); any provider-side queue attribution.

**Sample sufficiency: the current samples are NOT sufficient for a
production performance decision.** The local UAT ledger carries
exactly **one** Phase-0-instrumented call (n=1) — **not** a deployed-
production record; the application's runtime ledger has no Phase-0
PERF rows beyond that local UAT run. The Q3-B qualification capture
(n=43) is genuinely comparable in route/model/prompt/config but is a
qualification-corpus population, not production traffic, and its
capture workflow does NOT write to the application's runtime ledger.
The candidate-count distribution rests on three completed local UAT
runs (N = 1 for MPN `XP15360SE70005`, N = 1 for the same MPN on the
PERF row, N = 5 for one anonymous MPN). What the evidence IS
sufficient for: the causal direction of the user-visible cost (the
synchronous, evidence-only V2 wait is the dominant share of every
observed run window [M]); the derived finding that output-token volume
is the dominant per-call cost within the measured Q3-B qualification
population (V2 completions 6.75× larger than V1 with similar
arithmetic completion-to-latency ratios; per-call phase split
remaining [U]); and the decision that no frozen-contract parameter
(prompt, max_tokens, temperature, timeout, fallback) may be changed
inside this program to remove the wait.

## 5. Ranked optimization candidates (≤3)

| Rank | Candidate | Expected benefit (evidence) | Complexity | Model-decision semantics / operational & evidence-integrity risk | Versioned contract / qualification | Minimum experiment |
| --- | --- | --- | --- | --- | --- | --- |
| **1** | **Option B — nonblocking supplementary V2** per the FU2 design of record (`docs/SEMANTIC_V2_PERFORMANCE_DESIGN_01.md`) — **preferred architectural candidate; detailed FU2 implementation approval PENDING** — starting with its Phase 1 (debt lifecycle, **no timing change**) | Removes the measured V2 share from the user-visible window (conditional on the pending FU2 approval and the design's Phase 2 validation): 105.7 s → ≈21 s, 61.6 s → ≈19.6 s (N=1); 231.0 s → ≈33 s (N=5). Evidence: §2 measured shares + evidence-only authority [M] | High (debt table + run marker + sweep + Task Scheduler + launcher pass + §4.12 items 1–9 re-pins) — fully designed; direction accepted as the preferred candidate; **detailed FU2 implementation approval pending** (Architecture approval state, above); split into reviewable phases | **Model decision semantics UNCHANGED** (same per-case route/prompt/output schema/fallback/records; content unchanged, only publication timing moves; authority stays `False`, firewall pins unmodified) — no decision-accuracy change. **New operational and evidence-integrity risks introduced by asynchronous execution:** atomic publication of debt rows + run marker, debt completion and fenced terminalization, ownership fencing (claim generation/lease), crash/failure recovery, historical input reconstruction (design §4.13), the six coverage situations (§4.7), work-status presentation boundaries (§4.8, S2-C MUST-NOT delta), and rollback preconditions RP1–RP5 (§4.11). The design **requires validation** of all of these (acceptance §5, invariants §4.14, per-phase ChatGPT gates); the design alone does **not** eliminate them — the new process-safety class (stuck/`FAILED` debts, coverage situations, work-status presentation) is bounded and made visible by the design, not yet proven | Yes — §4.12 items 1–9 each require explicit approval; per-phase ChatGPT gate | The design's own Phase 1 exit: full regression + UAT with **identical** run windows (± network variance), six-situation states determined from durable rows, §4.13 reconstruction matrix green — a controlled mechanism-safety experiment; benefit then proven by design Phase 2 UAT (N=1 run ≤ 30 s). Observed UAT timing supports Option B's potential reduction in user-visible waiting, but the product value, operational complexity, and deployment SLO remain subject to separate approval and validation (independent of the conditional approval of this diagnostic); its implementation remains subject to the pending FU2 approval. |
| **2** | **A2 — in-step concurrency of independent V2 candidates** (bounded pool; per-case contract untouched) | N≥2 runs only. **Theoretical full-parallel estimate, not a projection**: N=5 shape 198.08 s → a parallel block no less than ≈50.3 s (the measured max of the five serial windows), run 231.0 s → ≈83 s (−64 %) — attainable only if all five candidates execute truly concurrently with zero contention; actual speedup depends on measured endpoint throughput, provider concurrency policy/contention, and rate limits (`RATE_LIMITED` is fallback-eligible). N=1: **0 s** [M] (one call cannot be parallelized) | Medium (parallelize the serial step-4b loop; Waitress thread budget; provider rate-limit exposure) | **Model decision semantics unchanged** (per-case route/prompt/records identical). Operational risk: `RATE_LIMITED` is fallback-eligible — contention can double calls/cost per candidate; provider concurrency policy unknown [H] | No per-case contract change; the orchestration call-sequence/timing test pins (S2-C surface) must be re-pinned with contract-preserving replacements | **Gating evidence first**: representative candidate-count distribution from production operational data (class 3 in §7, NOT produced by the proposed controlled UAT). The local UAT ledger shows N=1 in 2 of 3 completed runs — insufficient to know if N≥2 is "routine" anywhere |
| **3** | **Per-call output-length control** (thinking budget, prompt 2.x, max_tokens, route) — **deferred; excluded by the frozen contract for this program** | Potentially the largest per-call lever: p50 completion 2,475 vs V1 366.5 tokens; r = 0.9599 (§3, with provenance). The V1/V2 arithmetic ratios of median completion to median end-to-end latency are similar (§3, table); no measured decode throughput or statistical equality is claimed | Low code / **very high qualification** (prompt digest, runtime-config identity, full Q3-B-class re-capture, re-qualification against the sealed corpus) | **High** — the deliberative output shape is what produces the per-attribute analysis; shortening it may shift the decision distribution and invalidates the qualification binding; note the designed successor prompt 2.1 is *larger* (27,789-char system), not smaller | Yes — a separate re-qualification phase, not latency work | None now. Revisit only if representative production evidence (class 3 in §7) shows a completion-token tail (e.g., repeatedly >8,000) |

Practical-over-architectural note: under the frozen contracts there is
no small in-request lever that removes the measured 68–86 % from the
N=1 shape — one synchronous model call of provider-determined length
remains (the single Phase-0-instrumented local UAT call, at 41.94 s,
is the only available observation of the N=1 shape with measured
tokens and `finish_reason`). Candidate 1 is architectural but is the only candidate that
addresses the observed runs; its design surface is accepted in
direction (Option B = preferred architectural candidate) but its
detailed FU2 implementation approval (§4.12 items 1–9) **remains
pending**, and the design splits the work into a timing-neutral first
phase.

## 6. Product-level decision question (recorded — NOT answered here)

Before the product commits to the multi-phase nonblocking debt
architecture (design Option B: Phase 1 debt lifecycle → Phase 2
decouple → Phase 3 hardening), the following product question must be
decided explicitly. This diagnostic records it; it does not answer it,
and it designs nothing.

* **A. Retain supplementary V2 on every ResearchRun and move it to a
  durable background lifecycle** (the design's Option B). Product
  implication: every completed run eventually carries V2 evidence in
  the append-only ledger (the frozen "ALL outcomes persist" property
  extended across time), the report shows the design's bounded
  work-status line, and the measured 68–86 % user-visible V2 wait is
  removed from normal interactive runs (§2). Cost: the new operational
  and evidence-integrity surface of asynchronous execution (the F2
  risk class in §5, rank 1) and a new user-visible failure class
  (stuck/`FAILED` debts), at unchanged per-run provider cost.
* **B. Defer supplementary V2 for normal interactive ResearchRuns and
  invoke it only through an explicitly approved evaluation/research
  workflow** (the surface class of the existing qualification
  capture/management-command runs, e.g. the Q3-B qualification
  capture workflow). Product implication: normal interactive runs
  stop waiting for V2 immediately — the measured 68–86 % is removed
  with no debt table, no scheduler, no launcher pass, no rollback
  surface, and no §4.12 items 1–9 delta — and the V2 evidence ledger
  is populated only by explicit workflow invocations; per-run V2
  evidence is no longer a product property of normal runs. **Note
  (precise terminology):** the existing Q3-B qualification capture
  workflow writes to `semantic_v2_live_captures/`, NOT to the
  application's runtime ledger (EVIDENCE §1); an integration that
  writes captured V2 outcomes into the application's production
  ledger is NOT demonstrated in this repository, and Option B
  (product) does not assume or require it.

**Option B (product) is a proposed product simplification, NOT an
authorized contract change.** Existing frozen-contract implications
(brief): the current frozen semantics (FU3A/FU3B, S2-C) evaluate every
V2-eligible candidate synchronously inside each run and persist ALL
outcomes in the atomic publication block (S2-C §9 timing pin;
`test_every_eligible_candidate_gets_a_record`). Deferring V2 for
normal runs would require explicit approval of that orchestration
change — the step-4b wiring and the "all eligible candidates get a
record" contract, re-scoped to workflow invocations — and the frozen
absence semantics must not drift: a run without V2 records must
continue to mean "legacy semantic provenance unavailable" (never
NO_MATCH, never NOT_EVALUATED, never an AI failure), and the S2-C
MUST-NOT presentation rule (no change to current UI authority
presentation before Qualification V3) is preserved (no new status line
for normal runs). Either option leaves the eligibility predicate,
prompt 2.0 (digest `c0cc98bd…`), route identities, temperature 0.0,
max_tokens 32,768, the fallback policy, and the authority firewall
unchanged.

**What is required:** a **user/product decision** — not an
architecture-gate decision — on whether per-run supplementary V2
evidence on every ResearchRun is a product requirement (e.g., for
pilot reporting completeness or Qualification V3 readiness) or whether
on-demand V2 through explicitly approved workflows suffices. The
measured evidence in this diagnostic (n=1 Phase-0-instrumented local
UAT run — **not** a deployed-production record; the user-visible cost
is paid on every normal run) quantifies the cost of
retaining A synchronously but does not resolve that product question.
ChatGPT's separate architecture decision (approve/reject the corrected
FU2 design) is conditioned on this product question. No new feature
flag, alternate lifecycle, or scheduling system is proposed or designed
here.

## 7. Recommended next experiment (proposed — NOT executed in this
phase; NOT authorized by this diagnostic)

**A controlled repeat-run UAT under the existing Phase 0
instrumentation, with zero code/config change** (the design's interim
position; it separates three classes of evidence the current samples
leave open and explicitly does NOT conflate them).

* **Population:** 5–8 ResearchRuns on the same UAT host/environment of
  record (including the task-mandated `127.0.0.1/32` CIDR override):
  3 repeats of MPN `XP15360SE70005` (the N=1 shape) + 2–3 runs of two
  other MPNs (to sample V2-eligible candidate counts), spaced over a
  few days to capture provider-side variance. **Actual V2 eligibility
  and call counts must be measured, not assumed.** Historical N=1
  observations for MPN `XP15360SE70005` do not establish a future lower
  bound on V2 call counts for new runs of that MPN, and the candidate
  counts of the proposed "two other MPNs" are not documented in E1
  (only MPN `XP15360SE70005` at N=1 and one anonymous MPN at N=5
  appear; the prior "≈3–6 V2 calls" estimate was not supported by
  available data and is removed). The recorded candidate counts are
  historical facts, not guarantees; future runs' V2-eligible
  candidate counts and corresponding V2 call counts must be measured
  from the actual ledger.
* **Reads:** local UAT PERF ledger only (per-attempt `latency_ms`,
  `prompt_tokens`, `completion_tokens`, `finish_reason`,
  `fallback_used`) + run windows + execution-evidence stage rows. No
  new telemetry, no provider-side instrumentation, no streaming.
* **Scope of what it can establish — three evidence classes, kept
  separate (the FU1 review's concern):**
  1. **Controlled UAT latency variability.** Provider-side
     latency variability on a single MPN / single candidate shape,
     measured under zero code/config change. Establishes the
     variance band for the N=1 case (and, for any other MPN actually
     selected, the N=k case).
  2. **Scenario coverage for N=1 and N≥2.** Whether any specific
     candidate count shape (N=1, N≥2) can be observed in the UAT
     environment of record. Depends on the chosen MPNs producing the
     intended candidate-count shapes — which is a purposive selection
     property, not a frequency observation.
  3. **Actual production candidate-count frequency and arrival
     rates.** NOT established by a purposively selected set of
     5–8 UAT runs. Production frequency/arrival-rate evidence
     requires representative operational data (e.g., a real
     production-ledger distribution) over a duration that captures
     the natural arrival distribution. Whether multi-candidate runs
     are rare or routine in production is **not inferable** from the
     proposed UAT; it is not stated in this diagnostic.
* **Decision rules of record (conditional on authorization; each rule
  references the evidence class it consumes):**
  (a) **Latency variability evidence (class 1):** if the 3 N=1
      repeats show a p50 within the ≈20–45 s band of the Q3-B
      qualification population, the provider-side latency variance
      statement for the N=1 shape is reinforced [M]. **Per-run
      latency (`latency_ms`) and per-call prompt / completion-token
      counts are recorded individually** — N=1 observations do not
      establish a population correlation, and a comparable Pearson r
      is NOT a criterion for three repeats; no optimization decision
      follows from this class alone.
  (b) **Scenario coverage evidence (class 2):** if any chosen MPN
      produces N≥2 V2-eligible candidates in the UAT, the N≥2
      candidate shape becomes directly observable in the UAT
      environment (the design Phase 3 concurrency decision can then
      use those measured windows); if no chosen MPN produces N≥2,
      that absence is recorded — it is a coverage observation, NOT
      evidence that N≥2 is rare or routine in production.
  (c) **Production frequency evidence (class 3):** NOT produced by
      this experiment. Option B (design Phase 1) is the only
      optimization that addresses the N=1 shape (the only shape with
      a documented local UAT PERF row); its design surface is
      accepted in direction (Option B = preferred architectural
      candidate) but its detailed FU2 implementation approval (§4.12
      items 1–9) remains pending. A2 (concurrency) and the
      completion-token tail question (calls > 8,000 tokens) are
      deferred to future phases gated on representative production
      evidence, not on this controlled UAT.

The experiment's output would directly feed the design Phase 2
acceptance bound (N=1 run ≤ 30 s [M] non-V2 remainder 19.6 s) and the
SLO validation (design §5.2). **No additional live runs are
authorized by this diagnostic**; the experiment remains proposed only,
for a future explicitly authorized phase.

## 8. Limitations

1. n=1 Phase-0-instrumented local UAT run (`7bc925de`, MPN
   `XP15360SE70005`); the 84.73 s call's token count is [U]
   (unrecoverable; pre-Phase-0 contract).
2. Queue / prefill / decode split and TTFT are [U] (non-streaming
   transport); per-call phase attribution is impossible for all
   existing calls, including the new PERF one.
3. The two single-candidate UAT runs are independent observations, not
   a controlled before/after; no latency claim is made for the
   instrumentation itself.
4. Q3-B is a qualification-corpus population: comparable for
   throughput/distribution, not for exact production durations.
5. Fallback-route figures are a different model (throughput
   observation only); the fallback never executed in the observed
   population.
6. Structural exposure, unobserved: with the 300 s qualified ceiling,
   one pathological synchronous V2 evaluation could occupy the
   user-visible window for up to ≈2T + bookkeeping in the worst case
   (design [D] bound) — the Option B risk this program exists to
   remove.
7. The V1 semantic stage (≈10 s per run) is a second synchronous model
   wait inside the non-V2 remainder; out of scope here, relevant to the
   acceptance bound.
8. The N=5 parallel-concurrency figure (§5, rank 2) is a theoretical
   full-parallel estimate (measured max serial window as the floor),
   not a projection: actual concurrent throughput, provider
   contention, and rate limits are unmeasured for this route.

## 9. Safety and authority invariants (this phase)

* No production/test/prompt/config change; `git diff --check` clean;
  only this report + a minimal STATUS.md entry are written.
* Semantic V2 authority **unchanged and unqualified**:
  `V2_AUTHORITY_QUALIFIED = False` and
  `V2_PERF_AUTHORITY_QUALIFIED = False`, evidence-only, no authority
  consumer reads a V2 record (drift-pinned; verified in tree at HEAD).
* **F-2 deployment security HOLD remains OPEN** (ambient all-address
  `PI_VENDOR_PRICE_ALLOWED_CIDRS` = `0.0.0.0/0,::/0`; must not be left
  as the UAT/pilot host default) — outside this diagnostic.
* UAT database read-only (whole-DB hash unchanged); no live model
  calls; no network; no Oracle/PeopleSoft; no destructive git command.

## 10. Evidence references

E1–E9 (§1) plus: `product_intelligence/semantic/runtime_v2.py`
(frozen route/temperature/max_tokens/timeout,
`V2_AUTHORITY_QUALIFIED = False`), `product_intelligence/execution/
orchestration.py` (serial step-4b, synchronous in-request),
`product_intelligence/research/semantic_decision_v2_perf.py` (PERF
record contract: per-attempt `latency_ms`/tokens/`finish_reason`,
`V2_PERF_AUTHORITY_QUALIFIED = False`),
`docs/SEMANTIC_V2_PERFORMANCE_DESIGN_01.md` (Option B, FU2 —
preferred architectural candidate, implementation approval pending;
§4.12, §5, §7), `docs/SEMANTIC_V2_PERFORMANCE_EVIDENCE_01.md` (§1,
§2, §4).

Sanitized numeric evidence supporting the §3 Pearson r = 0.959875
(43 pairs from E7): `docs/LOCAL_SEMANTIC_V2_PERF_PHASE1_DIAG_CORRELATION_43.csv`
(`case_index,completion_tokens,latency_ms`, 43 rows; case identifiers
replaced with a 1..43 integer index; no model outputs, no prompts,
no secrets, no customer data; stable documentation filename,
preserved byte-identical from this review).
