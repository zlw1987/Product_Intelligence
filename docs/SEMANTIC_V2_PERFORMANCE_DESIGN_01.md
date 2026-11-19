# SEMANTIC-V2-PERFORMANCE-DESIGN-01 — Reducing user-visible ResearchRun latency from synchronous Semantic V2 evaluation

**Status:** DESIGN-ONLY architecture decision document. PENDING CHATGPT
ARCHITECTURE REVIEW. No production code, test, migration, prompt, route, or
deployment is changed by this document. ChatGPT remains the final
architecture approval gate.

**Base:** `feature/vendor-refresh-web` @ `33e7f42e8c1800f902aafbdfb74f63e7907eb384`
(full-suite baseline collection: **8,669 nodes / 199 files**, measured at
the base in this session with `python -m pytest --collect-only -q`).

**Companion evidence document:** `docs/SEMANTIC_V2_PERFORMANCE_EVIDENCE_01.md`
(sanitized; every figure classified [M]easured / [D]erived / [H]ypothesis /
[U]nobservable, with provenance). This document cites it as **EVIDENCE**;
the untracked `docs/LOCAL_UAT_PERF_01_SEMANTIC_V2_LATENCY_ANALYSIS.md` is
preserved unchanged and was validated/corrected per EVIDENCE §7.

---

## 1. Problem statement (evidence-bound)

The standalone web intake (`web/views.py::research_new` POST) calls
`execute_research_run` **synchronously inside the browser request**.
Orchestration step 4b runs every Semantic V2 evaluation **before** the
run's atomic publication. V2 output is evidence-only
(`V2_AUTHORITY_QUALIFIED is False`; no authority code path reads a V2
record) — the user waits for it without any effect on Machine Price,
Reviewed Price, matching decisions, or review state.

Measured in the local UAT (EVIDENCE §1):

| Run | Total window | V2 share | V2 shape |
| --- | --- | --- | --- |
| `bd992103` (1 V2-eligible candidate) | 105.688 s | **84.728 s = 80.17 %** | single PRIMARY `amax`/`qwen3.8-27b` attempt, no fallback, outcome `UNCERTAIN` |
| `37826c4f` (5 V2-eligible candidates) | 230.960 s | **198.082 s = 85.77 %** | 5 serial single-PRIMARY attempts, no fallback |

The PRIMARY-vs-fallback ambiguity in the previous reports is **resolved
against the UAT ledger**: exactly one attempt per record, all
`fallback_used = false`, `actual_provider = amax` (EVIDENCE §1.1–1.2).

Driver analysis (EVIDENCE §4): on the same endpoint, V2 prompt 2.0 p50
completion is 6.75× V1 prompt 1.1 p50 (2,475 vs 366.5 tokens) at equal
implied decode rate (≈115 vs ≈112 tok/s) — output deliberation length, not
client work, dominates. Queue delay, TTFT, and token counts for the UAT
calls themselves are [U]nobservable today because the production runtime
drops per-attempt latency and provider usage when building the persisted
record.

## 2. Decision question

How to remove the measured ~80 % V2 share from **user-visible** ResearchRun
latency without changing the frozen prompt (2.0, digest `c0cc98bd…`), route
identities, temperature (0.0), output limit (32,768), fallback policy
(execution-failure-only, ≤1 primary + ≤1 fallback), semantic authority
(evidence-only), or the deterministic price authority — and without
violating CLAUDE.md's infrastructure bar (no Celery/Redis/brokers without a
demonstrated-need phase).

## 3. Option A — Keep synchronous V2

Low-risk improvements that do **not** change the frozen V2 contract or the
synchronous timing.

### A1. Instrumentation (persist per-attempt latency + provider usage)

Persist, in the V2 ledger, per-attempt `latency_ms` (already held in
memory as `SemanticAttempt.latency_ms`) and provider-reported
`token_usage` (prompt/completion; already held as
`TransportResult.token_usage`), plus `finish_reason`. No raw provider
body, no CoT text — the bounded-vocabulary/no-raw-output discipline of the
V2 record is preserved.

- **Contract surface:** this is an additive, versioned extension of the V2
  persistence adapter (or an additive envelope section), following the
  S2-B-FU1 precedent that new contract versions reuse the row by
  registering a versioned adapter — old records replay byte-identically
  under the old binding; the extension is a separately approval-gated
  contract amendment, **not** a silent field addition to the frozen 2.0
  record.
- **Expected gain:** 0 s directly. Measurable value: it makes every later
  decision evidence-based (attribute any window to route/attempt/tokens;
  detect fallback usage; bound provider-side variance) and it is a
  **prerequisite** for Option B's eventual-completion acceptance
  criteria.
- **Required change set:** additive codec/adapter version, additive
  migration only if a column is used (the versioned-payload design
  requires none), re-pin events for the touched semantic-family digest
  suites (recorded, per the Q3-B5 precedent), replacement tests that
  preserve/strengthen the old-record replay pins.

### A2. In-step concurrency of independent candidates

Parallelize the serial step-4b loop (bounded pool, e.g. 2–4 in flight;
per-case contract untouched: same route, same prompt, same ≤1 primary +
≤1 fallback, same output schema).

- **Expected gain (measured shapes):** 0 s for N=1 (the observed UAT run
  stays ≈106 s). For N=5 (the sibling run): 198.08 s → ≈max(draw) ≈
  50.3 s (the measured max of the five windows), i.e. run ≈83 s
  (32.88 s non-V2 remainder + 50.25 s; −64 %). For N=3 homogeneous: ≈85
  s instead of ≈255 s.
- **Risks (measured where possible):** `RATE_LIMITED` is
  fallback-eligible — contention on the shared amax endpoint converts one
  failure into a second call (doubled cost/latency for that candidate);
  the provider concurrency policy is unknown ([H]); Waitress' default
  thread budget (4) is shared with other browser traffic — bounded at
  pilot scale, but it must be pinned by tests; the qualification-capture
  sequential discipline is a property of the *runner*, not of the
  production loop, so no capture contract moves.
- **Gate:** adopt only if the post-A1 ledger shows runs routinely carry
  ≥2 V2-eligible candidates (the UAT population: 1 and 5 — one of two).

### A3. B300/vLLM server tuning (out-of-repo)

Affects fallback-route calls only. The UAT runs used **no fallback**
(ledger, EVIDENCE §1), so A3 contributes 0 s to the observed population.
Whether any configuration (vs model or shared load) limits the fallback
route is unanswerable without vLLM server metrics ([H], EVIDENCE §4).
Kept as an out-of-repo follow-up, not part of this decision.

### Option A verdict

A1 is low-risk and necessary (evidence gate). A2 is conditional and helps
only multi-candidate runs. **A alone cannot remove the measured 80.17 %
from the observed single-candidate run** — the user still waits ≈85 s for
evidence that changes no price. The pilot runbook ("may take 1–2 minutes")
remains the norm, and the norm worsens with candidate count (231 s at N=5).

## 4. Option B — Nonblocking supplementary V2 (recommended target)

The run publishes its authoritative results **without** V2; V2 evaluation
becomes durable, owned, recoverable **supplementary** work whose records
land in the same append-only ledger through the same S2-B service. V2
stays evidence-only in content AND in timing.

Design principles: (1) every mechanism reuses an in-repo precedent
(vendor-refresh child execution, `claim_execution`, the S2-B ledger, the
management-command surface); (2) no browser-request thread is treated as a
durable worker; (3) "no ledger row" is no longer ambiguous — a debt row
makes the state explicit; (4) the original publication is byte-identical in
all pre-existing rows.

### 4.1 Durable V2 lifecycle states (requirement 1)

New additive model (runs layer, the only package with Django models),
one row per V2-eligible (run, assessment_index) — the same stable binding
the ledger and review candidates use:

```
state (bounded vocabulary, CHECK-constrained):
  PENDING      created in the run's atomic publication transaction;
               never evaluated yet
  EVALUATING   claimed by one sweep invocation; lease recorded
  COMPLETED    terminal: exactly one V2 evaluation outcome was persisted
               to the ledger (EVALUATED or RUNTIME_FAILURE — "ALL
               outcomes persist" is preserved)
  FAILED       terminal: the debt mechanism gave up WITHOUT a persistable
               outcome (bounded reason class only; never fabricates a
               RUNTIME_FAILURE ledger row for a non-semantic error)
```

Row fields (bounded; no raw payloads, no provider text): `run_id`,
`assessment_index`, `state`, `source_url` (binding, mirroring the ledger),
`claim_owner` (bounded invocation id) + `claim_lease_expires_at`,
`evaluations_attempted` (int), `retry_eligible_at` (backoff gate, NULL
when immediately eligible), `last_error_class` (bounded vocabulary, only
for non-persistable debt-level failures: `RETRY_EXHAUSTED`,
`EXECUTOR_ERROR`, `PROVIDER_NOT_CONFIGURED` — semantic runtime failures
are persistable ledger outcomes, not debt errors),
`created_at` / `state_changed_at` / `finished_at`.

`PENDING` and `EVALUATING` are the only non-terminal states; a debt is
terminal exactly when a ledger row exists (→ `COMPLETED`) or the bounded
give-up fires (→ `FAILED`).

### 4.2 Execution ownership and concurrency control (requirement 2)

- **Only a sweep invocation executes debt.** The web request never
  evaluates V2 after the cutover (no in-request thread, no deferred
  callable, no "fire and forget").
- **Claim:** an atomic conditional write (state `PENDING` — or
  `EVALUATING` with an EXPIRED lease — → `EVALUATING`, new owner + new
  lease) inside one transaction; at most one winner
  (precedent: the vendor-refresh serialized claim, M4 A3 zero-row write
  lock; SQLite single-writer semantics).
- **Lease:** bounded constant ≥ 2×(qualified timeout 300 s) + margin,
  e.g. 30 min — one evaluation is at most primary(300 s) + fallback(300 s)
  + bookkeeping, so a 30-min lease can only expire when the owner is dead
  or wedged.
- **Per-evaluation discipline (unchanged):** exactly one
  `runtime.evaluate(case)` per evaluation; ≤1 primary + ≤1 fallback per
  the frozen allowlist; runtime constructed per sweep invocation (lazy,
  zero debt → zero construction).
- **Two sweeps never evaluate one debt simultaneously** (single-winner
  claim); the same debt is never evaluated twice unless a crash lost the
  outcome AND the ledger shows no row (the reconciliation below decides
  from durable state, never from memory).

### 4.3 Atomicity of original ResearchRun publication (requirement 3)

The publication transaction keeps creating, **together or not at all**:
snapshot, V1 review candidates, vendor supplement, FX, terminal
transition — AND (new) the debt rows for every V2-eligible assessment.
The V2 **ledger rows leave the transaction** (that is the one frozen
surface being redesigned — §4.12 item 1). Consequences:

- No work is ever lost: a run that reaches COMPLETED atomically owns its
  complete debt set (creation is in the same transaction as the terminal
  state — there is no "run published, debt not written" window).
- The published rows are byte-identical to today for every pre-existing
  artifact (the V2 ledger row simply arrives later, through the same
  service).
- A debt row is never created by any surface other than the publication
  transaction (single-writer, source-pinned).

### 4.4 Durable tracking of pending V2 work (requirement 4)

The debt table IS the tracking surface. Queries of record:
pending = `state IN (PENDING, EVALUATING-with-live-lease)`; backlog =
count of `state = PENDING`. The sweep processes a bounded batch
(default 1, serial within one invocation — the per-invocation wall is at
most one evaluation ≈ ≤600 s, so batch 1 keeps a single Task Scheduler
slot clean; batch > 1 is a later tuning decision, not an architecture
one). No in-memory queue, no broker, no second database.

### 4.5 Recovery after process crash / server restart (requirement 5)

| Failure point | Durable state after | Recovery |
| --- | --- | --- |
| Crash between run publication and first sweep | debt `PENDING` | next sweep (or startup sweep) claims it |
| Sweep killed mid-`evaluate` | debt `EVALUATING`, no ledger row | lease expires (≤30 min) → next sweep re-claims → **reconcile**: ledger row absent → evaluate once |
| Crash after ledger persist, before debt terminalization | debt `EVALUATING`, ledger row PRESENT | re-claim → **reconcile**: ledger row present → debt `COMPLETED` WITHOUT re-evaluation (the existing append-only guard would otherwise raise `SemanticDecisionAlreadyRecordedError`) |
| Server down for hours/days | debts `PENDING`/stale `EVALUATING` | **startup sweep** (hooked into the existing `run_internal_pilot.cmd` before Waitress starts) + scheduled sweeps |
| Sweep host misconfigured (no provider env) | runtime construction fails bounded | debt `FAILED` / `PROVIDER_NOT_CONFIGURED` (explicit; never silent PENDING forever, never a fabricated ledger row) |

Reconciliation is always from durable state (ledger row present or not);
no outcome is ever inferred from a dead process's memory. This is the
project's first supplementary-write recovery surface — the
`EXECUTION_INTERRUPTED` reserved-writer precedent sets the bar: the
recovery path may ONLY move debt rows and append ledger rows through the
existing single service; it never touches run state, snapshot, prices, or
review candidates.

### 4.6 Retry boundaries and idempotency (requirement 6)

- **Inside one evaluation:** frozen — ≤1 primary + ≤1 fallback; no
  semantic-error retries (a valid response is final; a schema-invalid one
  is not retried — same as today).
- **Debt level (new bounded policy, defaults subject to approval):** at
  most 3 evaluation attempts per debt (a debt-level attempt = one
  `runtime.evaluate` call, which itself may spend ≤1 primary + ≤1
  fallback per the frozen allowlist); schedule: immediately, then
  `retry_eligible_at` ≈ +5 min, then ≈ +30 min (sweep-interval driven —
  no timers inside a process; a sweep invocation claims only debts whose
  `retry_eligible_at` is past); after the 3rd attempt without a
  persistable outcome → `FAILED` / `RETRY_EXHAUSTED`. A `RUNTIME_FAILURE`
  ledger row is a TERMINAL evaluation outcome, not a retry trigger — the
  debt goes `COMPLETED` for it (the outcome is recorded; re-rolling the
  model would fabricate a second record the append-only ledger refuses).
- **Idempotency assets (existing, reused):** (run, assessment_index)
  uniqueness + append-only service guard (double persist fails closed);
  single-winner claim (double sweep does nothing); reconcile-before-
  evaluate (crash recovery never re-evaluates a persisted outcome).

### 4.7 Zero eligible vs pending vs completed vs failed (requirement 7)

The four states are distinguishable from durable rows alone:

| Debt rows for the run | Ledger rows | Meaning (the only meaning) |
| --- | --- | --- |
| none | none | **zero V2-eligible candidates** (evaluated population empty — lazy runtime construction made zero calls, as today) |
| `PENDING` / `EVALUATING` | none | **evaluation pending** |
| any | EVALUATED (any decision) | **evaluation completed** |
| any | RUNTIME_FAILURE | **evaluation completed with a bounded runtime-failure outcome** (fail-closed record; never NO_MATCH) |
| `FAILED` | none | **evaluation failed at the debt level** (bounded reason; no outcome recorded) |

The report page presents exactly this distinction with a bounded status
line (§4.8) — so "no ledger row" can no longer be misread as "evaluated,
not eligible". Pre-cutover runs (no debt rows) keep the frozen legacy
absence meaning (EVIDENCE §3) — the new interpretation applies only where
a debt row exists. **This redefinition of absence is a frozen-contract
change requiring explicit approval** (§4.12 item 2).

### 4.8 Safe V2 evidence publication and replay (requirement 8)

- **Publication:** unchanged service path — the sweep calls
  `persist_semantic_decision_records_v2`-equivalent (the same
  `persist_semantic_decision` per record) inside its own transaction
  (ledger row + debt terminalization together or not at all). Digest
  anchor, uniqueness, append-only: unchanged.
- **Replay:** unchanged contract — `replay_semantic_decision_record`
  still requires the persisted row + the snapshot's assessment binding;
  for a `FAILED` debt (no row) an explicit replay fails closed exactly as
  absence does today (`SemanticDecisionRecordNotFoundError`).
- **Presentation:** a bounded status line in the report's semantic
  evidence area: one of (a) no V2 evaluation was required (zero
  eligible), (b) pending, (c) completed (decision shown as advisory
  evidence, authority-neutral wording), (d) completed with runtime
  failure (bounded class only), (e) failed (bounded reason only). Wording
  is fixed vocabulary; no client-supplied flag can alter it; DENIED and
  non-COMPLETED pages render nothing new (byte-identity preserved).
  **Adding this line is a change to the report presentation that S2-C
  froze ("no change to current UI authority presentation" before
  Qualification V3) — explicit approval required** (§4.12 item 3). It presents
  evidence-availability state, not authority — but the surface is frozen
  regardless, and the approval gate is the S2-C MUST-NOT list itself.

### 4.9 No new authority (requirement 9)

Unchanged and re-pinned: `V2_AUTHORITY_QUALIFIED is False`; V2 outcomes
are not in 4A input, not in review-candidate input, not in the snapshot
payload, not in any public price summary; no V2 human-review candidates;
Machine Price / Reviewed Price / deterministic matching are untouched by
the debt, the sweep, or the status line. The S2-C authority-firewall test
suite passes **unmodified** (its pins are content-based, not timing-based
— verified: `TestAuthorityFirewall` asserts what V2 can and cannot feed,
not when evaluation happens).

### 4.10 Windows production deployment (requirement 10)

Current pilot: one Waitress process via `scripts\run_internal_pilot.cmd`
(preflight + `python -m waitress …`), SQLite at `PI_SQLITE_PATH`.

- **Chosen: management command + Windows Task Scheduler.** A new command
  (`semantic_v2_debt_sweep`) claims + executes one debt per invocation,
  exits; a scheduled task runs it every ≈60 s. Task Scheduler is
  OS-standard on the pilot host — it is NOT a broker, queue service, or
  new dependency class; the command is idempotent and single-winner by
  the DB claim, so double-firing is harmless. This is the same surface
  class as the existing `vendor_refresh` management command (in-repo
  precedent, no new infrastructure).
- **Startup sweep** in the launcher script (one invocation before
  Waitress starts) covers downtime without a timer.
- **A separate long-running worker process is NOT justified at pilot
  scale:** it would add a second supervised process (failure mode: a dead
  worker with no supervisor), and CLAUDE.md requires a demonstrated-need
  phase for new infrastructure classes. The measurable gap vs a worker is
  the sweep interval (≤60 s) + startup latency — acceptable for
  evidence-only work whose single evaluation is ≤≈600 s anyway. It is
  re-opened ONLY if the eventual-completion SLO (§5.2) fails UAT with the
  scheduler in place.
- **A thread launched inside the Django request is explicitly not a
  durable worker** (no supervision, dies with the worker, no crash
  recovery, Waitress thread budget) — the design does not use one.
- A browser-request thread, an in-process timer, or "execute after the
  redirect" are all rejected: none survives a crash/restart, and all
  would silently lose or double debt.

### 4.11 Migration and rollback strategy (requirement 11)

- **Migration:** one additive migration (new debt table + CHECK
  constraints + (run_id, assessment_index) UNIQUE). No data migration, no
  column change to any existing table, every existing row stays legal
  (precedent: migration 0014).
- **Cutover:** the behavior switch (synchronous → debt+sweep) is a single
  orchestration change gated behind the same code; deployment order:
  migrate → deploy code → register scheduled task → (optionally) run
  startup sweep. No dual-mode flag in production code (no bypass
  surface); mode is the deployed version.
- **Rollback:** (1) stop the scheduled task; (2) run the sweep until the
  pending backlog is ZERO (measurable: count query — the drain gate);
  (3) revert code to the previous version. After the drain gate, every
  published run has its ledger rows or bounded `FAILED` debts, so
  rolled-back (synchronous) code reads a world with no ambiguous
  absences. **The drain gate is the rollback safety device; rolling back
  with a non-empty PENDING backlog is prohibited** (those runs' absence
  would be misread under the old semantics).
- **Forward re-entry:** if a rollback later rolls forward, PENDING debts
  from the reverted window do not exist (drained), so no reconciliation
  is needed.

### 4.12 Frozen tests and safety contracts (requirement 12)

**Preserved unmodified (content-based pins that Option B does not break):**

- S2-C authority firewall suite (`TestAuthorityFirewall`,
  `TestNoMachinePriceContamination` — V2 never feeds 4A / review /
  snapshot / summary / Machine Price / Reviewed Price).
- `V2_AUTHORITY_QUALIFIED is False` drift pins (runtime + adapter).
- Frozen runtime config pins (route identities, temperature 0.0 exact-
  type, max_tokens 32,768, timeout validation, prompt 2.0 digest
  `c0cc98bd…`).
- Ledger service pins: append-only guard, digest anchor, uniqueness,
  replay binding/verification (the sweep uses these unchanged).
- V1 (FU3B) pins, vendor-refresh suite (incl. the 8 file-backed
  concurrency nodes), web boundary DENIED zero-knowledge nodes.
- The motivating-case record pins (stored decision/confidence/reason,
  derived snapshots) — records stay shape-identical.

**Re-pinned or redesigned — each requires EXPLICIT approval (this is the
frozen-contract delta of Option B):**

1. **S2-C §9 timing surface:** "the records persist in the atomic
   publication block ONLY" → re-decided as "the debt is created in the
   atomic publication block; the records persist in the debt-completion
   transaction through the unchanged service". Affected pins:
   `tests/research/test_semantic_v2_boundaries.py::test_the_orchestration_
   v2_wiring_is_persist_only` (source-level: `persist_semantic_decision_
   records_v2` in `orchestration.py`), the persistence-behavior nodes in
   `tests/execution/test_semantic_decision_v2_execution.py`
   (`TestV2OutcomesPersist`, `test_every_eligible_candidate_gets_a_
   record`), and the full-run pins in `tests/execution/test_semantic_v2_
   motivating_case.py`. Replacement tests preserve the safety property
   (ALL outcomes recorded, never overwritten, never feeding authority)
   and ADD the timing-decoupling contracts (debt created in the
   publication transaction; ledger row or bounded FAILED in every
   terminal shape).
2. **Absence semantics (S2-B/FU1):** "no record = legacy provenance
   unavailable" gains the debt-aware reading (§4.7) for post-cutover runs
   — an explicit, versioned redefinition; pre-cutover runs keep the
   legacy meaning unchanged (their absence shape is pinned and must
   still render identically).
3. **Report presentation (S2-C MUST-NOT):** the bounded status line
   (§4.8) — approval required against "no change to current UI authority
   presentation before Qualification V3". The approval scope is stated
   precisely: evidence-availability status only; no decision is shown
   with authority weight; DENIED/non-COMPLETED pages byte-identical.
4. **Frozen nine-file digest pin** (`tests/execution/test_vendor_refresh_
   network_boundary.py`): `orchestration.py` and `runs/models.py` are
   protected files that Option B changes → two **recorded re-pin events**
   (precedent: MAIN-MERGE-FU1 re-pin for S2-B/C; VENDOR-REFRESH-WEB
   re-pin for the additive `WEB_UI` member), each as its own approved
   phase, the other seven files byte-identical.
5. **Web boundary allowlist** (`tests/web/test_web_boundaries.py`): the
   status line needs a runs-owned read symbol (debt state for the run) →
   the narrow runs public-API addition, allowed by explicit allowlist
   extension (precedent: the vendor-refresh public names +1/+2 recorded
   evolutions).
6. **New surfaces get new tests, not weakened old ones:** debt claim
   single-winner (file-backed concurrency, 8-node class precedent),
   lease expiry + reconciliation (no re-evaluation of persisted
   outcomes), startup sweep, drain-gate rollback, status-line
   byte-identity over DENIED pages, no-provider-config classification.
   CLAUDE.md: replacement tests must preserve or strengthen the original
   contract; zero pre-existing node deleted/renamed/skipped/xfailed/
   deselected/weakened.

**What Option B does NOT touch (no approval needed):** the V2 input
contract (23-field case), the prompt, the output schema (strict 6-key
JSON), the eligibility predicate, the authority derivation (FU2/FU3
tokens), the ledger row schema (until the A1 instrumentation version is
itself approved), the V1 path, 4A/4B/4C, HUMAN-REVIEW, vendor refresh,
FX, the FoxPro/SAP intake boundary, DENIED zero-knowledge.

## 5. Acceptance criteria (measurable)

Baseline of record: this branch, 8,669 nodes / 199 files; UAT shapes
§1. "UAT run" = one fresh local UAT execution of the same MPN
(`XP15360SE70005`) under the pilot environment.

1. **Main research response latency.** A UAT run with ≥1 V2-eligible
   candidate reaches COMPLETED (report reachable) with **zero V2
   evaluation time inside the run window**: `run.finished_at −
   run.created_at` ≤ 30 s for the N=1 shape (measured non-V2 remainder:
   20.96 s) and ≤ 45 s for the N=5 shape (measured remainder: 32.88 s);
   browser-observed POST→report ≤ the same bound + 5 s. Cross-check:
   the run's evidence timeline contains no SEMANTIC/V2 stage between
   claim and publication.
2. **V2 eventual completion.** ≥ 99 % of published runs with ≥1 debt row
   reach a terminal debt state within 15 min of run completion (p95 over
   a 2-week UAT population); terminal state is `COMPLETED` (ledger row
   present) or `FAILED` (bounded reason) — never stuck `PENDING`/
   `EVALUATING` past lease+2 sweep intervals; per-evaluation wall ≤
   660 s (2×300 s + margin) or the debt is `FAILED`.
3. **No lost or duplicated evidence.** Invariant queries return zero
   violations: (a) every V2-eligible assessment of every post-cutover
   COMPLETED run has exactly one of {ledger row, `FAILED` debt};
   (b) the (run, assessment_index) ledger uniqueness holds (constraint +
   service guard — a forced double persist fails closed); (c)
   pre-cutover ledger rows are byte-identical (digest-verified replay
   sample ≥ 6 rows, incl. both UAT runs); (d) no debt was ever evaluated
   twice with a persisted outcome (reconcile-before-evaluate pinned by
   file-backed concurrency test + production audit query).
4. **Crash/restart recovery.** File-backed scripted tests (SQLite, two
   processes): (a) kill between publication and sweep → restart →
   startup sweep completes all debts; (b) kill mid-evaluation → after
   lease expiry → next sweep reclaims, final state exactly one ledger
   row OR `FAILED`, zero duplicates; (c) kill between ledger persist and
   debt terminalization → reconcile closes the debt `COMPLETED` with
   ZERO additional model calls (call-count spy = 1).
5. **Zero change to deterministic price authority.** The S2-C
   authority-firewall + no-machine-price-contamination suites pass
   **unmodified**; a UAT run's `PriceIntelligenceSnapshot` payload is
   byte-identical to the same-evidence synchronous-mode run (recorded
   pair); 4A input remains `total_assessments` (source pin preserved);
   Machine Price / Reviewed Price / review queue values equal the
   deterministic-only derivation.
6. **DENIED access and commercial-data boundaries.** All armed
   vendor-refresh DENIED zero-knowledge nodes pass unmodified; NEW armed
   nodes: a DENIED page contains no debt-status byte and queries no debt
   row; a non-COMPLETED page renders no status line; the debt table
   carries no provider payload, no raw model text, no credential, no
   base URL (adversarial construction test: a runtime result containing
   such text cannot be written through the debt path).
7. **Test collection preservation and safety regression.** Full-suite
   collection ≥ 8,669 nodes with node-level diff showing **zero**
   deleted/renamed/skipped/xfailed/deselected (only additions and the
   explicitly approved in-place re-pins of §4.12, each name- and
   contract-preserving); the frozen nine-file digest pin passes with the
   two recorded re-pins and seven byte-identical files; the 8
   vendor-refresh concurrency nodes pass; full-suite result equals the
   baseline modulo the documented pre-existing workstation failure class
   (the 32-node CRLF raw-byte digest + preview-fixtures class), node-for-
   node identical.

## 6. Recommendation and trade-offs

**Recommended: Option B (nonblocking supplementary V2), implemented in
the bounded phases below, with Option A1 instrumentation as Phase 0.**

Why not A alone: A removes 0 s from the observed single-candidate run
(the measured 80.17 % stays user-visible) and at most ~64 % from the
five-candidate run, while adding provider-contention exposure (A2) for a
bounded gain. The pilot's observed runs are 106 s / 231 s — both already
at or past the runbook's stated upper bound, and both scale linearly with
V2-eligible candidates.

Why B is safe here specifically:

- V2 content is authority-neutral today by freeze (`V2_AUTHORITY_
  QUALIFIED is False`, firewall-pinned); B changes only the TIMING of
  that evidence, with the state distinction made explicit instead of
  implicit — moving "unknown" into an explicit durable state, which is
  the project's own epistemic rule (unknown beats fabricated certainty).
- Every mechanism has an in-repo precedent with a frozen test suite
  (child execution rows, serialized claim, cooldown-class bounded
  policy, management command, startup script, additive migration).
- The idempotency asset already exists (append-only guard + uniqueness),
  so the highest-risk class (duplicate evidence) is guarded by the
  current contract, not by new logic.
- The rollback path has a measurable safety gate (drain-to-zero).

Accepted costs (the honest trade-off):

- One additive migration + one new table + one new command + one
  scheduled task + one launcher-script line (deployment surface grows
  by exactly these; no broker/queue/worker process).
- Five frozen surfaces require explicit redesign approval (§4.12): the
  S2-C §9 timing pin, the S2-B absence semantics (versioned extension),
  the S2-C report-presentation MUST-NOT (status line), two digest re-
  pins, one web-allowlist extension. **Without that approval, Option B
  may not start** — this document is the approval request.
- A small new failure class (debt stuck/FAILED) that the status line
  makes visible to the user instead of hidden inside run latency.
- Qualification V3 (the pending Q3-C program, corpus seal at FINAL-HOLD
  per STATUS) must later re-decide the presentation of V2 evidence under
  authority; B's status line is scoped to availability state only, so
  the V3 presentation decision remains clean.

**Interim position if Option B is rejected:** land Phase 0 (A1
instrumentation) immediately — it is necessary either way — and hold
A2 pending ledger evidence that N≥2 candidates are the common shape;
accept that single-candidate runs remain ≈106 s user-visible.

## 7. Bounded reviewable phases (future implementation; each is its own
approval gate with ChatGPT review of the actual diff + test evidence)

**Phase 0 — Instrumentation (A1).** Versioned additive extension of the
V2 persistence adapter recording per-attempt `latency_ms`, provider
`token_usage` (prompt/completion), and `finish_reason`; old records
replay byte-identically; no timing/behavior change (synchronous V2
stays). Exit: one UAT run whose 84-class window is attributed to route +
attempt + tokens from the production ledger alone.

**Phase 1 — Debt lifecycle + explicit states (no timing change).**
Additive migration (debt table, CHECK + UNIQUE); debt rows created in
the run's atomic publication transaction; synchronous evaluation still
terminalizes the debt in the same transaction (so every run is
`COMPLETED`-debt — the pending/failed machinery exists but is not yet
exercised by timing); the bounded status line renders (zero-eligible /
completed / completed-runtime-failure / failed / pending-vocabulary
complete, pending always transient); §4.12 items 1–3, 5 approved and
re-pinned in this phase. Exit: full regression + UAT shows identical run
windows (± network variance) and the four-state presentation is pinned.

**Phase 2 — Decouple (the latency change).** Orchestration step 4b stops
evaluating; sweep command (claim/lease/reconcile/bounded retries); Task
Scheduler registration + startup sweep in the launcher; §4.12 item 4
re-pins (recorded events). Exit: acceptance criteria §5.1–5.4 measured on
fresh UAT runs (N=1 and a constructed N≥2 shape), crash-recovery
file-backed suite green, drain-gate rollback drill executed and recorded.

**Phase 3 — Hardening + decision inputs.** Two-week UAT population
metrics against §5.2 (eventual completion p95); the A2 concurrency
decision (adopt/hold) from the real ledger distribution; fallback-route
health check (A3) informed by first persisted per-attempt data;
re-open worker-vs-scheduler ONLY on §5.2 failure. Exit: the performance
evidence-of-record v2 replaces this one; no contract change.

Each phase: no test deleted/renamed/skipped/xfailed/weakened; recorded
re-pins only where §4.12 approves them; `manage.py check` 0 issues;
`makemigrations --check --dry-run` clean post-migration; full-suite
node-level diff of record.

## 8. Unresolved architectural decisions (for the approval gate)

1. **Debt retry policy defaults** (3 attempts; ≈5 min / ≈30 min; 30-min
   lease) — proposed bounded values, not yet approved.
2. **Task Scheduler vs separate worker** — this design recommends the
   scheduler (no new supervised process); the re-open trigger is a
   measured §5.2 failure.
3. **The report status line's exact wording and placement** — an S2-C
   MUST-NOT surface; requires the explicit redesign approval of §4.12.3
   (scope: availability state only, advisory-neutral wording).
4. **Phase 1/Phase 2 split vs merged approval** — the split keeps each
   diff reviewable (schema+presentation, then timing); a merged phase
   would ship the change in one approval. Recommended: split.
5. **Instrumentation versioning shape (Phase 0)** — versioned successor
   adapter (new output schema version) vs additive envelope section;
   both reuse the row without migration; the adapter-registry precedent
   favors the versioned adapter.
6. **No-provider-config classification** — debt `FAILED` /
   `PROVIDER_NOT_CONFIGURED` at evaluation time (proposed) vs staying
   `PENDING` until configured (rejected: silent backlog). Needs
   confirmation as it changes misconfigured-environment behavior from
   "run terminates" (synchronous mode: runtime construction error →
   catastrophic boundary) to "run completes, debt fails bounded".
7. **Sweep batch size** — default 1 debt/invocation (proposed; keeps a
   single scheduled slot ≈ ≤600 s); batch >1 is a tuning decision
   deferred to Phase 3.

## 9. Strict-boundary compliance (this task)

Documentation only: two files created (`docs/SEMANTIC_V2_PERFORMANCE_
DESIGN_01.md`, `docs/SEMANTIC_V2_PERFORMANCE_EVIDENCE_01.md`). No
production code modified; no migration created; no test modified/deleted/
skipped/weakened; no frozen prompt/model/route/output-limit change; no
benchmark or acceptance-criteria rebaseline; no destructive git command;
the existing untracked evidence (incl.
`docs/LOCAL_UAT_PERF_01_SEMANTIC_V2_LATENCY_ANALYSIS.md`) preserved
byte-identical; UAT database opened read-only only (`file:...?mode=ro`);
nothing merged or deployed.
