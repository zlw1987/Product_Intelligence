# SEMANTIC-V2-PERFORMANCE-DESIGN-01 — Reducing user-visible ResearchRun latency from synchronous Semantic V2 evaluation

**Status:** DESIGN-ONLY architecture decision document. **Revision FU2
(this document, updated in place — no new report created).** ChatGPT
review of record: **Option B remains the preferred architecture; the FU1
design is NOT yet approved for implementation; five final corrections
(C1–C5) are now incorporated in place below**
(each marked (FU2) at its location; the (FU1) marks remain). No
production code, test, migration, prompt, route, or deployment is changed
by this document. ChatGPT remains the final architecture approval gate for
the corrected design; **no implementation phase may start until the
corrected design (incl. the §4.12 frozen-contract delta, items 1–9, as
corrected by FU2) is explicitly approved.**

**Base:** `feature/vendor-refresh-web` @ `9b2103c5549cb158a928feb217cf3cf71aaceb57`
(FU1 commit; full-suite baseline collection **8,669 nodes / 199 files**,
measured at `33e7f42` with `python -m pytest --collect-only -q`,
unchanged by the documentation-only design commits `0df5830` (design-01)
and `9b2103c` (FU1)).

**Revision record (FU1, of record).** This revision corrects, in place,
the five architecture issues of the ChatGPT independent review of the
design-01 commit. Approved direction of record: Option B (durable
nonblocking supplementary V2); Windows Task Scheduler (not a new broker
or long-running worker); one debt per sweep invocation initially; separate
bounded implementation phases (§7); a versioned instrumentation adapter if
needed (Phase 0); **no prompt, route, model, temperature, token-limit, or
fallback-policy change**.
- **B1 — Exact V2 input reconstruction:** §4.1 (new debt field
  `context_provenance`), §4.3 (the publication transaction now also
  persists the per-debt recorded provenance and the run-level marker),
  NEW §4.13 (the reconstruction proof: input-by-input coverage, the one
  input currently held only in memory, the minimal bounded immutable data
  persisted at publication, the no-refetch rule, and the mandatory
  deterministic equivalence test matrix including the ESTABLISHED Micron
  alias scenario), §5.8 (acceptance).
- **B2 — Lease fencing and actual timeout bounds:** §4.2 (the fixed 30-
  minute lease is **withdrawn** — the runtime supports a configurable
  request timeout up to the validated 3600 s ceiling, so the lease is now
  the formula `L(T) = 2T + M_EVAL + M_LEASE` computed and **recorded** at
  claim time; new ownership generation + atomic fencing validation; only
  the current claim owner may append the ledger result and terminalize
  the debt), §4.1 (new debt fields `claim_generation`,
  `claim_lease_seconds`), §4.6 (retry bound parametric in T), §5.9
  (acceptance: the mandatory tests for an expired but still-running
  owner, a new claimant, and a late result from the old owner).
- **B3 — Explicit coverage and rollback semantics:** §4.1 (new run-level
  durable coverage marker `v2_publication_contract`), §4.7 (the six
  distinguishable situations, determined from durable rows alone), §4.11
  (the corrected rollback: exact preconditions RP1–RP5 — a zero-PENDING
  backlog is **not sufficient** while `FAILED` debts without ledger rows
  remain; the bounded pre-rollback drain; the recorded-exception path),
  §4.12 item 9 (the bounded `FAILED → COMPLETED` drain transition),
  §5.10 (acceptance).
- **B4 — Scheduler, retry and SLO consistency:** §4.10 (bounded Task
  Scheduler invocation: one debt, controlled overlapping-instance policy
  "do not start a new instance", scheduler kill bound `L(T) + 2·O`;
  the startup step is now a **reconcile-only** pass, ≤ 30 s, zero model
  calls, fail-open for Waitress — a potentially long V2 sweep never runs
  synchronously before Waitress startup), §5.2 (the rewritten SLO: successful evidence completion separated from terminal `FAILED`; measurable
  healthy-path and crash-recovery bounds consistent with lease and
  retries), §5.11 (acceptance).
- **B5 — Presentation and authority:** §4.8 (before Qualification V3 the
  presentation is **bounded V2 work-status only** — pending / completed /
  unavailable (legacy absence) / failed — with NO model decisions,
  confidence, or semantic conclusions; the design-01 "(c) completed
  (decision shown as advisory evidence)" wording is **withdrawn**; the
  existing web access boundary is stated explicitly and the Vendor Price
  CIDR authorization is **never conflated** with semantic evidence
  access), §4.12 items 3 and 5 (revised approval scope), §5.6
  (corrected armed nodes).

**Revision record (FU2, of record).** This revision corrects, in place,
the five final issues of the ChatGPT independent review of the FU1 design
(base `9b2103c`). No new report. No code, migration, test, prompt, route,
or authority change.
- **C1 — Preserve runtime failure semantics:** source-verified
  (`semantic/runtime_v2.py::_attempt`/`evaluate`/`_failure`; EVIDENCE
  §8.14): a missing provider env does NOT fail construction and is NOT a
  debt error — it is a valid, persistable `RUNTIME_FAILURE` outcome
  (bounded error class `PROVIDER_NOT_CONFIGURED`; one zero-latency
  attempt, no fallback — outside the frozen allowlist) → the debt
  terminalizes **COMPLETED** (situation #5). §4.1 (`PROVIDER_NOT_
  CONFIGURED` removed from `last_error_class`; the two debt-level classes
  defined precisely), §4.5 (the exact distinction between a persistable
  semantic runtime failure and an unpersistable execution/persistence
  failure; corrected recovery-table rows), §4.6 (retry is triggered by
  unpersistable failures only), §4.7 (situation #5 note), §4.12 item 6,
  §4.14 I-B4.5, §5.11 (a disabled Scheduler leaves work PENDING — it does
  not execute or fail work), §8 item 6 (resolved).
- **C2 — Reconcile-only must not capture execution ownership:** the
  startup reconcile-only pass terminalizes row-PRESENT debts via the
  fence over the RECORDED owner+generation only — no claim, no new
  lease, no execution; row-absent debts are left untouched (an
  unclaimed stale lease is immediately claimable by the next scheduled
  sweep). §4.2 (ownership and fencing defined precisely; the claim "two
  sweeps never evaluate one debt simultaneously" corrected — under an
  expired lease, duplicate transport execution MAY happen, but only one
  fenced ledger publication can succeed), §4.5, §4.10, §4.14 (I-B2.1/
  I-B2.6 sharpened; new I-B2.7), §5.4/§5.11.
- **C3 — Account for Scheduler backlog:** §4.4 (FIFO claim order makes
  the queue position well-defined; batch size is the capacity lever),
  §4.10 (the single one-at-a-time instance is a capacity choice, gated),
  §5.2 (queue-aware SLO recalculation: the healthy path is unchanged at
  queue position 1 — 780 s ≤ the retained 15-minute target; residence
  bound `B(k, r) ≤ r·k·(I + O + W(T)) + (r − 1)·(B1 + B2)`; skipped
  overlapping triggers, repeated attempts, and sustained arrival rates
  accounted for; the measurable load gate G1–G3 decides single Scheduler
  instance vs. separate capacity decision — the 15-minute target is NOT
  lowered), §7 Phase 3, §4.14 (new I-B4.6).
- **C4 — Correct rollback safety:** normal rollback requires RP1–RP5,
  including no unresolved FAILED debt — no waiver. §4.1 (`drain_
  attempted_at` withdrawn), §4.6 (FAILED is terminal in this design),
  §4.11 (the signed-exception document is withdrawn — it does not
  restore old-code understanding of a missing V2 record; an emergency
  degraded rollback is NOT contract-preserving and is never presented
  as such), §4.12 item 9 (the `FAILED → COMPLETED` drain transition
  withdrawn, replaced by terminal-state preservation; any separate
  recovery operation is explicitly designed and approved on its own),
  §4.14 (I-B3.5 replaced), §5.10, §6, §7 Phase 2, §8 item 8 (resolved).
- **C5 — Correct phase ownership of frozen test changes:** Phase 1
  remains synchronous — the original S2-C ledger-publication timing
  tests are preserved UNCHANGED there (debt rows and ledger records
  persist together in the publication transaction, so the original
  timing contract still holds). Phase 2 owns the approved timing-
  contract redesign (§4.12 item 1), together with replacement tests
  preserving or strengthening every original safety invariant. §4.12
  item 1, §4.14 (I-B1.1 attribution split), §5.7, §7.

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
`context_provenance` **(FU1 B1)** — the recorded bounded
`ContextProvenance` vocabulary set for this assessment at publication
(∅ or exactly `[CUSTOMER_RETRIEVAL_RELATION]` in the live path;
CHECK-constrained to the frozen vocabulary; immutable after creation) —
the per-assessment alias-expanded search-batch provenance that the
§4.13 reconstruction reads; it is the minimal bounded immutable data the
B1 analysis identifies as currently held only in memory,
`claim_owner` (bounded invocation id) + `claim_generation` **(FU1 B2)**
— the monotonically increasing ownership counter, exactly +1 per
successful claim (the fencing token) + `claim_lease_expires_at` +
`claim_lease_seconds` **(FU1 B2)** — the lease actually granted, recorded
so expiry and fencing are self-describing (never dependent on two
processes sharing an environment value; the formula is in §4.2),
`evaluations_attempted` (int), `retry_eligible_at` (backoff gate, NULL
when immediately eligible), `last_error_class` **(FU2 C1)** (bounded
vocabulary; UNPERSISTABLE debt-level failures only: `RETRY_EXHAUSTED` —
the §4.6 3-attempt policy spent without a persistable outcome;
`EXECUTOR_ERROR` — no bounded runtime result ever existed (a
construction/validation exception, or a programming exception that is
never swallowed). `PROVIDER_NOT_CONFIGURED` is **removed** from this
vocabulary: a missing provider env is a persistable semantic runtime
failure — a `RUNTIME_FAILURE` ledger outcome that terminalizes the debt
**COMPLETED** (situation #5), never a debt state; §4.5 defines the exact
distinction),
`created_at` / `state_changed_at` / `finished_at`.
**(FU2 C4)** the FU1 B3 `drain_attempted_at` field is **withdrawn** (it
existed only for the `FAILED → COMPLETED` drain transition, now
withdrawn — §4.12 item 9 revised): `FAILED` is terminal in this design;
no surface may move a terminal debt.

**Run-level coverage marker (FU1 B3).** The additive publication also
sets `ResearchRun.v2_publication_contract` — a bounded CHECK-constrained
vocabulary `SYNCHRONOUS_V2` / `DEBT_V2` — in the same atomic transaction,
before the terminal transition: `SYNCHRONOUS_V2` for every run published
by the legacy synchronous code (all pre-existing rows take this value by
migration default — they predate the cutover by definition) and
`DEBT_V2` for every run published by the debt code. This durable
run-level coverage/version marker makes the six situations of §4.7
distinguishable from durable rows alone — in particular a post-cutover
zero-eligible run from a legacy run with unavailable V2 provenance (both
have no debt row and no ledger row; only the marker separates them).
No run is ever terminal without its marker.

`PENDING` and `EVALUATING` are the only non-terminal states; a debt is
terminal exactly when a ledger row exists (→ `COMPLETED`) or the bounded
give-up fires (→ `FAILED`).

### 4.2 Execution ownership and concurrency control (requirement 2)

- **Only a sweep invocation executes debt.** The web request never
  evaluates V2 after the cutover (no in-request thread, no deferred
  callable, no "fire and forget").
- **Claim:** an atomic conditional write (state `PENDING` — or
  `EVALUATING` with an EXPIRED lease **and no ledger row** — →
  `EVALUATING`, new owner + new lease) inside one transaction; at most one
  winner (precedent: the vendor-refresh serialized claim, M4 A3 zero-row
  write lock; SQLite single-writer semantics). **(FU2 C2)** only an
  invocation that WILL execute the debt may claim; a reconcile-only
  invocation never claims (§4.10).
- **Lease (FU1 B2 — corrected):** the request timeout T is
  **configurable** (`PI_SEMANTIC_REQUEST_TIMEOUT_SECONDS`; qualified
  default **300.0 s**, validated hard ceiling **3600.0 s** — EVIDENCE
  §3), so a fixed 30-minute lease is safe only for T ≤ 750 s and is
  **withdrawn**. The lease is a function of the configured timeout,
  computed at claim time from the same validated configuration the
  runtime uses: `L(T) = 2·T + M_EVAL + M_LEASE` with `M_EVAL = 60 s`
  (evaluation bookkeeping margin) and `M_LEASE = 240 s` (reclaim
  margin). One evaluation is at most `W(T) = 2·T + M_EVAL` (primary(T)
  + fallback(T) + bookkeeping), so `L(T) ≥ W(T) + M_LEASE`: at the
  qualified default `W = 660 s`, `L = 900 s` (15 min); at the ceiling
  `W = 7260 s`, `L = 7500 s`. The granted lease is recorded on the debt
  row (`claim_lease_expires_at` + `claim_lease_seconds`), so a lease can
  expire only when its owner is dead or wedged — for any legal T.
- **Ownership generation and atomic fencing (FU1 B2 — new).** Each
  successful claim increments `claim_generation` by exactly one (inside
  the same CAS transaction as the claim) — the fencing token. **Only
  the current claim owner may append the ledger result and terminalize
  the debt:** the completion is ONE transaction — (1) append the ledger
  record through the unchanged S2-B service (append-only guard + (run,
  assessment_index) uniqueness), then (2) the fenced conditional update
  `… WHERE id=? AND state='EVALUATING' AND claim_owner=? AND
  claim_generation=? AND claim_lease_expires_at > now` → the terminal
  state, requiring exactly one affected row, then COMMIT; any fence
  failure ROLLBACKs the whole transaction — **including the ledger
  append** — and records a bounded "stale completion" log event (no row
  change, no state change). Ordering rationale (of record): the append
  precedes the fenced terminalization inside the transaction, so a fence
  failure discards both atomically — a terminalized debt without its row
  (a coverage violation) is impossible, while a row without a terminal
  debt (if ever observed out of band) is self-healing by reconcile (row
  present → `COMPLETED`, no re-evaluation). The reconcile terminalization
  of a row-present debt (from a sweep invocation OR the reconcile-only
  startup pass) is a separate fenced update conditioned on the
  **recorded** owner + generation — no lease term, no claim, no
  generation change: it consumes the recorded ownership without creating
  new ownership (FU2 C2 — the precise definition follows). A late
  completion from a superseded owner therefore persists nothing; the
  ledger's append-only guard + uniqueness remain the defense-in-depth
  backstop.
- **Per-evaluation discipline (unchanged):** exactly one
  `runtime.evaluate(case)` per evaluation; ≤1 primary + ≤1 fallback per
  the frozen allowlist; runtime constructed per sweep invocation (lazy,
  zero debt → zero construction).
- **Ownership and fencing (FU2 C2 — precise definition).**
  (1) *Ownership* is established ONLY by a claim — the CAS above
  (PENDING → EVALUATING, or EVALUATING with an expired lease and no
  ledger row → EVALUATING) that sets a new `claim_owner`,
  `claim_generation` + 1, and a new lease; only invocations that will
  execute the debt may claim, and a reconcile-only invocation never
  claims. (2) *Ownership* is the pair (`claim_owner`,
  `claim_generation`); the lease bounds only how long the ownership may
  block re-claim — it does not make the owner right, and an expired
  lease does not cancel an in-flight execution. (3) *Execution* is
  permitted while the owner holds the claim at claim time; its transport
  calls continue under their own bounded wall (`W(T)`) — an execution
  that outlives its lease expiry is not a protocol violation. (4)
  *Publication* is legal only for the current owner + generation with a
  live lease: the fenced completion transaction (append + terminalize,
  all-or-nothing) is the ONLY write path that creates a ledger row.
  (5) *Reconcile terminalization* (ledger row present → `COMPLETED`)
  is legal from ANY invocation (sweep or reconcile-only) as a fenced
  update over the recorded owner + generation — no lease term, no claim:
  it consumes recorded ownership and creates none.
- **Consequence — execution may overlap; publication cannot (FU2 C2 —
  corrected).** The FU1 wording "Two sweeps never evaluate one debt
  simultaneously" is **withdrawn**: single-winner claim means at most one
  winner per claim event (one live lease at a time); it does NOT exclude
  concurrent evaluation. Under an expired lease while the original owner
  is still executing (wedged, not dead), the successor's claim is legal,
  and both may run transport calls on the same debt simultaneously —
  duplicate transport execution is an accepted bounded cost (at most one
  extra evaluation per expiry event, inside the §4.6 3-attempt budget).
  What the fence guarantees is publication: **only one fenced ledger
  publication can succeed** — the loser's append is atomically rolled
  back (no row, no state change), with the (run, assessment_index)
  uniqueness + append-only guard as backstop. Duplicate execution can
  happen; duplicate persisted outcomes cannot. The same debt is never
  evaluated twice WITH A PERSISTED OUTCOME unless a crash lost the
  outcome AND the ledger shows no row (reconciliation decides from
  durable state, never from memory) — and a lost-but-late outcome is
  *discarded by the fence*, not double-persisted: the superseded owner's
  completion transaction rolls back (no row, no state change), and the
  successor re-evaluates at most once from the ledger's durable absence.

### 4.3 Atomicity of original ResearchRun publication (requirement 3)

The publication transaction keeps creating, **together or not at all**:
snapshot, V1 review candidates, vendor supplement, FX, terminal
transition — AND (new) the debt rows for every V2-eligible assessment,
each carrying the recorded `context_provenance` of its assessment **(FU1
B1 — the minimal bounded immutable data of §4.13)** — AND (new) the
run-level `v2_publication_contract = DEBT_V2` marker **(FU1 B3)**, set
before the terminal transition in the same transaction. The V2
**ledger rows leave the transaction** (that is the one frozen
surface being redesigned — §4.12 item 1). Consequences:

- No work is ever lost: a run that reaches COMPLETED atomically owns its
  complete debt set (creation is in the same transaction as the terminal
  state — there is no "run published, debt not written" window).
- The published rows are byte-identical to today for every pre-existing
  artifact (the V2 ledger row simply arrives later, through the same
  service).
- A debt row is never created by any surface other than the publication
  transaction (single-writer, source-pinned).
- **(FU1 B1)** a debt row's `context_provenance` is set at creation from
  the in-memory search-batch membership and is immutable thereafter —
  the reconstruction (§4.13) never re-derives it from run topology.
- **(FU1 B3)** no run is terminal without its marker; marker + debt set
  + ledger rows together make every coverage situation (§4.7)
  determinable from durable rows alone.

### 4.4 Durable tracking of pending V2 work (requirement 4)

The debt table IS the tracking surface. Queries of record:
pending = `state IN (PENDING, EVALUATING-with-live-lease)`; backlog =
count of `state = PENDING`. The sweep processes a bounded batch
(default 1, serial within one invocation — the per-invocation wall is at
most one evaluation, `W(T)` = 660 s at the qualified default, so batch 1
keeps a single Task Scheduler slot clean; batch > 1 is a later tuning
decision, not an architecture one). No in-memory queue, no broker, no
second database.
**(FU2 C3 — queue order and position).** The sweep claims exactly one
debt per invocation: the *oldest* claim-eligible debt (`created_at ASC,
id ASC` — FIFO), so the queue position `k` (1-indexed over the
non-terminal debts at claim time) is well-defined for the §5.2 residence
bound. The debt table IS the queue (the Task Scheduler's overlap policy
skips, it does not queue — §4.10); the batch size is the capacity lever
the §5.2 load gate acts on (a separate capacity decision, not a default
change here).

### 4.5 Recovery after process crash / server restart (requirement 5)

| Failure point | Durable state after | Recovery |
| --- | --- | --- |
| Crash between run publication and first sweep | debt `PENDING` | next sweep claims it (the reconcile-only startup pass claims nothing — FU2 C2) |
| Sweep killed mid-`evaluate` | debt `EVALUATING`, no ledger row | lease expires (≤ `L(T)` — 15 min at the qualified default; §4.2 FU1 B2) → next sweep **reconciles** (no row) → claims (new `claim_generation`) → evaluates once |
| Crash after ledger persist, before debt terminalization | debt `EVALUATING`, ledger row PRESENT | **reconcile terminalization** (no re-evaluation, no claim): the fenced update over the recorded owner+generation moves the debt `COMPLETED` (any re-execution would otherwise raise `SemanticDecisionAlreadyRecordedError` via the append-only guard; the fence — §4.2 FU2 C2 — makes the crashed owner's own late completion impossible). Under the all-or-nothing fenced completion this shape is not reachable in-protocol (append and terminalization commit together); it is defended against as an out-of-band observation |
| Server down for hours/days | debts `PENDING`/stale `EVALUATING` | **the reconcile-only startup pass** (bounded ≤ 30 s, zero model calls, fail-open for Waitress startup — terminalizes row-present debts ONLY, claims nothing — §4.10 FU2 C2) + the scheduled sweeps (which run while the web server is down — Task Scheduler is independent of Waitress) |
| Sweep host misconfigured (provider env missing) **(FU2 C1)** | **not** a construction failure: the runtime is built with a `None` transport; `_attempt` returns the normalized `PROVIDER_NOT_CONFIGURED` attempt (zero latency, no fallback — outside the frozen allowlist); `evaluate` returns a valid `RUNTIME_FAILURE` result | the persistable semantic runtime failure → ledger row (`RUNTIME_FAILURE`, bounded error class `PROVIDER_NOT_CONFIGURED`) + debt `COMPLETED` (situation #5) — **never** reclassified as a debt-level `FAILED` state |
| Runtime construction fails (invalid configured timeout → `SemanticRuntimeConfigError`), or the executor raises an unexpected exception (a programming defect — never swallowed) **(FU2 C1)** | no bounded runtime result exists | debt `FAILED` / `EXECUTOR_ERROR` (explicit; a `RUNTIME_FAILURE` row is never fabricated for a non-semantic error; never silent PENDING forever) |
| Fenced completion transaction cannot commit (persistence error) **(FU2 C1)** | a runtime result exists in memory; no row (append + terminalization roll back atomically) | the debt stays `EVALUATING` under the recorded owner; after lease expiry the successor re-claims and re-evaluates (counts against the §4.6 3-attempt budget); budget spent without a persistable outcome → `FAILED` / `RETRY_EXHAUSTED` |

Reconciliation is always from durable state (ledger row present or not)
and **never claims** (row-absent debts are left to the executing sweep —
FU2 C2); no outcome is ever inferred from a dead process's memory. This
is the project's first supplementary-write recovery surface — the
`EXECUTION_INTERRUPTED` reserved-writer precedent sets the bar: the
recovery path may ONLY move debt rows and append ledger rows through the
existing single service; it never touches run state, snapshot, prices, or
review candidates.

**The exact distinction (FU2 C1 — source-verified; EVIDENCE §8.14).**
*Persistable semantic runtime failure* = `runtime.evaluate(case)`
returned a bounded `SemanticRuntimeResultV2` with `response=None` + a
bounded `error_type` — any normalized attempt status, including
`PROVIDER_NOT_CONFIGURED` (a missing provider env is a call-time
normalization in `_attempt`, not an exception; `_failure` builds the
result). The record builder maps every such result to
`evaluation_state = RUNTIME_FAILURE` (S2-B "ALL outcomes persist"), so a
persistable outcome is **always** persisted through the unchanged service
and terminalizes the debt **COMPLETED** (situation #5). The debt runner
must NOT reclassify it — silently or explicitly — as a debt-level
`FAILED` state. *Unpersistable execution/persistence failure* = no
bounded runtime result exists (a construction/validation exception, e.g.
an invalid `PI_SEMANTIC_REQUEST_TIMEOUT_SECONDS`; an unexpected
programming exception propagated from the transport — the runtime
contract: never swallowed), or the fenced completion transaction could
not commit (a persistence error — the result exists in memory but no row
was persisted; the debt is not terminalized, and the retry policy
applies). These can NEVER become a `RUNTIME_FAILURE` row (a row must be
built from an actual bounded result — fabricating a row for a
non-semantic error would corrupt the evidence contract); the bounded
give-up terminalizes the debt **FAILED** with `last_error_class` ∈
{`RETRY_EXHAUSTED`, `EXECUTOR_ERROR`} (situation #6).

### 4.6 Retry boundaries and idempotency (requirement 6)

- **Inside one evaluation:** frozen — ≤1 primary + ≤1 fallback; no
  semantic-error retries (a valid response is final; a schema-invalid one
  is not retried — same as today).
- **Debt level (new bounded policy, defaults subject to approval):** at
  most 3 evaluation attempts per debt (a debt-level attempt = one
  `runtime.evaluate` call, which itself may spend ≤1 primary + ≤1
  fallback per the frozen allowlist); schedule: immediately, then
  `retry_eligible_at` ≈ +5 min (B1), then ≈ +30 min (B2) (sweep-interval
  driven — no timers inside a process; a sweep invocation claims only
  debts whose `retry_eligible_at` is past); after the 3rd attempt without
  a persistable outcome → `FAILED` / `RETRY_EXHAUSTED`. A
  `RUNTIME_FAILURE` ledger row is a TERMINAL evaluation outcome, not a
  retry trigger — the debt goes `COMPLETED` for it (the outcome is
  recorded; re-rolling the model would fabricate a second record the
  append-only ledger refuses) **(FU2 C1: every persistable runtime
  failure — including `PROVIDER_NOT_CONFIGURED` — is a terminal
  evaluation outcome of this kind; ONLY unpersistable failures (§4.5)
  trigger the retry policy)**. **(FU1 B4):** the backoff values are
  measured against the parametric bound of §5.2 — the worst-case
  non-terminal residence `L(T) + 3·(I + O) + 3·W(T) + B1 + B2` stays
  below the no-stuck audit bound for the configured T (at the qualified
  default: 900 + 360 + 1980 + 2100 = 5340 s ≈ 89 min; see §5.2 INV-1).
  **(FU2 C4 — the FU1 B3 drain is withdrawn):** a `FAILED` debt is
  **terminal** in this design — no surface (sweep, reconcile,
  reconcile-only pass, rollback gate) may move it; the bounded
  pre-rollback drain and the `FAILED → COMPLETED` transition it required
  are withdrawn (terminal-state history is not rewritten for rollback
  convenience — §4.11, §4.12 item 9 revised). A separate recovery
  operation for `FAILED` debts, if ever required, is explicitly designed
  and approved on its own before any implementation.
- **Idempotency assets (existing, reused):** (run, assessment_index)
  uniqueness + append-only service guard (double persist fails closed);
  single-winner claim (double sweep does nothing); reconcile-before-
  evaluate (crash recovery never re-evaluates a persisted outcome).

### 4.7 Coverage: the six distinguishable situations (requirement 7;
FU1 B3 — corrected)

Design-01's five-row table could not distinguish "legacy run with
unavailable V2 provenance" from "new run with zero eligible candidates"
(both: no debt row, no ledger row). **(FU1 B3)** the durable run-level
marker `v2_publication_contract` (§4.1) makes **six** situations
distinguishable from durable rows alone:

| # | Run marker | Debt rows | Ledger row | Meaning (the only meaning) |
| --- | --- | --- | --- | --- |
| 1 | `SYNCHRONOUS_V2` | — (none can exist) | none | **legacy run, V2 provenance unavailable** — the frozen S2-B legacy absence semantics, unchanged: "legacy semantic provenance unavailable" — never NO_MATCH, never NOT_EVALUATED, never an AI failure |
| 2 | `DEBT_V2` | none | none | **new run, zero V2-eligible candidates** (evaluated population empty — lazy runtime construction made zero calls, as today) — explicit, and distinguished from #1 by the marker |
| 3 | `DEBT_V2` | `PENDING` / `EVALUATING` (live or stale lease) | none yet | **evaluation pending** |
| 4 | `DEBT_V2` | `COMPLETED` | EVALUATED (any decision) | **completed evaluation** (an outcome is recorded; the outcome itself is NOT presented before Qualification V3 — §4.8 FU1 B5) |
| 5 | `DEBT_V2` | `COMPLETED` | RUNTIME_FAILURE | **recorded runtime failure** — a fail-closed outcome is recorded (distinct from #4: the row exists, a semantic outcome does not); never NO_MATCH. **(FU2 C1)** the row's bounded error class includes `PROVIDER_NOT_CONFIGURED` (a missing provider env is a persistable runtime failure — this situation, never #6) |
| 6 | `DEBT_V2` | `FAILED` | none | **debt-level failure** — the debt mechanism gave up WITHOUT a persistable outcome (bounded reason class); distinct from #5 (no row at all) |

The per-run situation is the deterministic combination over the run's
debts (a run with ≥1 debt row: pending while any debt is non-terminal;
otherwise the debt shapes above, per assessment). The report page
presents exactly the bounded work-status mapping of §4.8 — so "no
ledger row" can no longer be misread as "evaluated, not eligible", and
"no debt row" can no longer be read, for a `DEBT_V2` run, as anything
but "zero eligible". Pre-cutover (`SYNCHRONOUS_V2`) runs keep the frozen
legacy absence meaning **byte-identically** (the report renders no new
line for them — §4.8). **This marker-gated, versioned redefinition of
absence is a frozen-contract change requiring explicit approval**
(§4.12 item 2, revised). Invariant query of record (durable rows only):
every `DEBT_V2` run's every V2-eligible assessment — recomputed with the
frozen `is_v2_semantic_eligible` over the snapshot's persisted
assessments (a pure function) — has exactly one debt row, and each debt
row is in exactly one of situations #3–#6; a marker/debt/eligibility
disagreement is a data-integrity failure that fails closed (bounded
command output; no presentation).

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
- **Presentation (FU1 B5 — corrected):** a bounded status line in the
  report's semantic evidence area, **work-status only**: one of
  (a) not required (zero eligible candidates), (b) pending, (c)
  completed, (d) completed — runtime failure recorded (bounded class;
  no semantic outcome was produced), (e) failed (bounded reason class).
  **Before Qualification V3 the line presents NO model decision, NO
  confidence, NO reason code, NO matched/conflicting attribute, NO
  provider/model identity, and NO semantic conclusion of any kind** —
  the design-01 wording "(c) completed (decision shown as advisory
  evidence, authority-neutral wording)" is **withdrawn**: the line says
  only that the supplementary evaluation finished (and, for (d)/(e),
  in which bounded work-status shape). The display module reads only the
  run marker + the debt row state — **never the ledger record content**
  (the §4.12 item 5 allowlist addition is scoped accordingly) — so the
  presentation cannot leak a semantic conclusion by construction. Wording
  is fixed server-derived vocabulary; no client-supplied flag can alter
  it (the vendor-refresh F1 forged-flag precedent); `SYNCHRONOUS_V2`
  (legacy) runs and non-COMPLETED runs render nothing new (byte-identity
  preserved — for legacy runs, the absence of the line IS the frozen
  legacy presentation; B5's "unavailable" maps to that frozen absence,
  not to a new line).
- **Web access boundary (FU1 B5 — stated explicitly; never conflated).**
  The existing boundary of record (EVIDENCE §8.13): (1) the pilot
  report model — anyone who can reach the server and holds the run UUID
  can open the report (the report UUID is never access control; full
  authentication is deferred to 8C); (2) the 4D-C-SEC corporate
  **Vendor Price** CIDR gate (`vendor_price_access_allowed` over
  `REMOTE_ADDR` / `PI_VENDOR_PRICE_ALLOWED_CIDRS`, fail-closed)
  authorizes **vendor commercial data ONLY** — the compact-quote vendor
  rows, the Vendor API status notice, the vendor supplement replay, and
  the vendor refresh section/action — a DENIED connection takes the
  public-only replay and the vendor regions stay total zero-knowledge
  (the frozen D8 standard). The V2 status line is **standard report
  content** (the same surface class as the V1 review-candidate
  presentation, the assessment table, and the Machine Price summary): it
  is **NOT vendor commercial data; it is NOT gated by the Vendor Price
  CIDR policy; the CIDR authorization is never applied to semantic
  evidence access** — the line renders identically for ALLOWED and
  DENIED connections (COMPLETED `DEBT_V2` runs). The design-01 wording
  "DENIED and non-COMPLETED pages render nothing new (byte-identity
  preserved)" is **corrected**: the zero-knowledge / byte-identity
  requirement applies to the **vendor regions** (their armed nodes pass
  unmodified), while the standard report region gains the bounded line
  for every connection class under the existing report-reachability
  model.
  **Adding this line is a change to the report presentation that S2-C
  froze ("no change to current UI authority presentation" before
  Qualification V3) — explicit approval required** (§4.12 item 3,
  revised scope). It presents work-status only, not authority — but the
  surface is frozen regardless, and the approval gate is the S2-C
  MUST-NOT list itself.

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

- **Chosen: management command + Windows Task Scheduler (FU1 B4 —
  bounded invocation, controlled overlap).** A new command
  (`semantic_v2_debt_sweep`) claims + executes **one debt per
  invocation** (the approved initial value; batch >1 is a Phase-3
  tuning decision, not an architecture one), exits; a scheduled task
  runs it every 60 s (I = 60 s). Task Scheduler is OS-standard on the
  pilot host — it is NOT a broker, queue service, or new dependency
  class; the command is idempotent and single-winner by the DB claim,
  so an overlapping manual + scheduled firing cannot double-claim (one
  live lease at a time; an expired-lease overlap is bounded by the fence
  — §4.2 FU2 C2).
  This is the same surface class as the existing `vendor_refresh`
  management command (in-repo precedent, no new infrastructure). The
  task registration carries two controlled bounds (pinned by test,
  §5.11): **overlap policy "Do not start a new instance"** (a trigger
  firing while the previous invocation is still running is skipped —
  no queue, no pile-up; the invocation wall is bounded by `W(T) + O`
  ≈ 720 s at the qualified default, so a skip costs at most one
  interval) and **"Stop task if it runs longer than" = `L(T) + 2·O`**
  (≈ 1020 s at the default) — a wedged invocation is killed by the
  scheduler itself, leaving a stale `EVALUATING` debt that the
  lease/fence/reconcile path recovers (the crash-recovery bound of
  §5.2 applies). The transport's own request timeout (≤ T per attempt)
  makes exceeding `W(T) + O` structurally impossible except for
  process-level wedges (DB lock, host stall) — the kill bound covers
  exactly that class. **(FU2 C3)** one debt per invocation, one at a
  time, is a *capacity choice* validated by the §5.2 queue-aware SLO +
  load gate, not an architecture constant: the UAT N=5 shape (run
  `37826c4f`, 5 simultaneous debts) structurally exceeds the 15-minute
  target for queue positions ≥ 2 (worst case 65 min — §5.2). The gate
  decides, from measured UAT data, whether the pilot may run a single
  Scheduler instance or requires a separate capacity decision (batch
  >1, a second scheduled task, or a worker process — each its own
  approval gate); the 15-minute per-debt target is retained as an
  acceptance target and is NOT lowered to fit the proposed Scheduler.
- **Reconcile-only startup pass (FU1 B4 corrected; FU2 C2 — must not
  capture execution ownership).** A potentially long evaluation (≤
  `W(T) + O` ≈ 12 min at the qualified default) must **never run
  synchronously before Waitress startup**: the launcher's pre-Waitress
  step is a bounded **reconcile-only** pass (`semantic_v2_debt_sweep
  --reconcile-only`) that performs ONLY safe, bounded reconciliation
  from durable state: ledger row present → fenced reconcile
  terminalization to `COMPLETED` WITHOUT re-evaluation, over the
  RECORDED owner+generation (no claim, no new owner/generation/lease —
  §4.2 FU2 C2); **ledger row absent → the debt is left UNTOUCHED — no
  claim**: a reconcile-only pass must not establish a new execution
  lease on a debt it will not process (the FU1 wording "row absent →
  leave claimed for the scheduler's next evaluation" is **withdrawn** —
  a claimed row-absent debt would block re-evaluation until the new
  lease expired, up to `L(T)` = 15 min after every restart, while an
  unclaimed stale lease is immediately claimable by the next scheduled
  sweep), hard wall bound **30 s**, **zero model calls, zero
  provider-environment requirement, zero network** — it cannot wedge on
  supplementary work. The pass is **fail-open for the application**:
  Waitress starts regardless of the pass's outcome (a bounded log line
  on failure) — and fail-closed for evidence: no debt is ever lost or
  re-evaluated. All evaluation work belongs to the scheduled task, which
  runs **independently of Waitress state** (Task Scheduler is a separate
  OS subsystem — sweeps proceed across web-server restarts, and web
  availability is never held by supplementary work). Downtime recovery:
  a debt whose owner died with the host is reclaimed within `L(T) + I`
  of its lease expiry (the scheduler runs while the web server is down);
  the startup reconcile pass additionally terminalizes row-present debts
  immediately after restart (without claiming them — FU2 C2), so recovery
  of a PERSISTED outcome never waits for a lease.
- **A separate long-running worker process is NOT justified at pilot
  scale:** it would add a second supervised process (failure mode: a dead
  worker with no supervisor), and CLAUDE.md requires a demonstrated-need
  phase for new infrastructure classes. The measurable gap vs a worker is
  the sweep interval (≤60 s) + startup latency — acceptable for
  evidence-only work whose single evaluation is ≤ `W(T)` anyway. It is
  re-opened ONLY if the eventual-completion SLO (§5.2 SLO-1) fails UAT
  with the scheduler in place.
- **A thread launched inside the Django request is explicitly not a
  durable worker** (no supervision, dies with the worker, no crash
  recovery, Waitress thread budget) — the design does not use one.
- A browser-request thread, an in-process timer, or "execute after the
  redirect" are all rejected: none survives a crash/restart, and all
  would silently lose or double debt.

### 4.11 Migration and rollback strategy (requirement 11)

- **Migration:** one additive migration: (a) the new debt table (CHECK
  constraints over the bounded vocabularies — incl. `context_provenance`
  and the state set — + (run_id, assessment_index) UNIQUE + the lease/
  generation fields **(FU2 C4: the FU1 B3 drain field is withdrawn)**);
  (b) the additive `v2_publication_contract`
  column on the existing run table (bounded CHECK vocabulary;
  **migration default `SYNCHRONOUS_V2` makes every pre-existing row the
  legacy marker by definition** — no row-by-row data migration, no
  semantic rewrite, every existing row stays legal; precedent: migration
  0014). The design-01 "no column change to any existing table" is
  superseded by this single additive marker column (FU1 B3 — §4.12 item
  7).
- **Cutover:** the behavior switch (synchronous → debt+sweep) is a single
  orchestration change gated behind the same code; deployment order:
  migrate → deploy code → register scheduled task (with the bounded
  overlap + kill parameters — §4.10) → add the reconcile-only startup
  pass to the launcher (≤ 30 s, zero model calls, fail-open — FU1 B4).
  No dual-mode flag in production code (no bypass surface); mode is the
  deployed version.
- **Rollback (FU1 B3 — corrected: the zero-PENDING drain gate is
  necessary but NOT sufficient).** The design-01 gate allowed a rollback
  with `FAILED` debts (no ledger row) in place; under the old code
  those runs' reports would present the frozen legacy absence
  interpretation ("legacy semantic provenance unavailable") for runs
  that are **not** legacy — a truthfulness defect (the F5 class). The
  debt table and the marker column are additive and **stay applied**
  through the rollback (code reverts, the migration does not — the
  0014 discipline; every row stays legal and the old code ignores the
  additive surface), so the failure record remains auditable. **Exact
  rollback preconditions** (each verifiable by a bounded count /
  invariant query; the sweep command's rollback-gate query prints them):
  - **RP1** the scheduled task is disabled AND the startup reconcile
    pass is removed from the launcher (both cutover deployment steps,
    reversed).
  - **RP2** zero debts in `PENDING` (the design-01 drain gate, kept).
  - **RP3** zero debts in `EVALUATING` — live or stale: the sweep must
    first reconcile stale-lease claims (row present → `COMPLETED`;
    row absent → expired-lease re-claim + evaluate to terminal), so no
    in-flight ownership survives the rollback.
  - **RP4** zero debts in `FAILED` — see the no-waiver rule below.
  - **RP5** the coverage invariant holds for every run: every
    `DEBT_V2` run's every V2-eligible assessment has exactly one of {a
    `COMPLETED` debt + its ledger row, or no debt row (situation #2 —
    zero eligible)}; every `SYNCHRONOUS_V2` run has no debt row and its
    report renders byte-identically (the legacy presentation, for every
    connection class).
  **RP4 not met: the rollback is BLOCKED — no waiver (FU2 C4).** The
  FU1 B3 **pre-rollback drain is withdrawn**: it existed only to convert
  `FAILED` debts to `COMPLETED` via a new bounded `FAILED → COMPLETED`
  transition — i.e. to rewrite terminal-state history for rollback
  convenience; terminal states are preserved in this design (§4.6,
  §4.12 item 9 revised). The FU1 B3 **recorded-exception path is also
  withdrawn**: a signed exception document does **NOT** restore the old
  code's understanding of a missing V2 record — the old code renders
  the frozen legacy-absence interpretation for a run without a V2 record
  regardless of any document, and nothing at runtime consults the
  document; waiving RP4 would therefore deploy a truthfulness defect
  (the F5 class) as a known state of the product. An **emergency
  degraded rollback** (code reverted with `FAILED` debts outstanding)
  is **NOT contract-preserving** and is never presented as satisfying
  RP1–RP5: if it is ever executed, it is an explicitly declared, logged
  degraded operation enumerating the affected runs, with the defect
  accepted as an emergency cost — it is not part of this design's
  rollback path. A **separate recovery operation** for `FAILED` debts
  (re-attempt, re-terminalize, any state movement) is **out of scope**:
  it must be explicitly designed and approved on its own before any
  implementation; it is not introduced here for rollback convenience.
  Draining RP2/RP3 before the rollback check is done by the normal
  scheduled sweeps (one at a time; the §5.2 queue bound applies) — the
  gate is checked only after the backlog is terminal.
- **Forward re-entry:** after a clean rollback (RP1–RP5), no post-
  cutover debt is non-terminal and no `FAILED` debt remains (RP4);
  a later roll-forward creates debt rows only for NEW runs, so no
  reconciliation of the reverted window is needed.

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
   transaction through the unchanged service". **(FU2 C5 — phase
   ownership):** this item — the approved timing-contract redesign AND
   its replacement tests — belongs to **Phase 2**, the phase where the
   evaluation actually leaves the publication transaction. **Phase 1
   remains synchronous** (debt rows and ledger records persist together
   in the atomic publication block), so the ORIGINAL S2-C
   ledger-publication timing tests are **preserved unmodified** in Phase
   1 — they keep holding. Phase 2 executes this re-pin with replacement
   tests that preserve or strengthen every original safety invariant.
   Affected pins:
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
2. **Absence semantics (S2-B/FU1) — revised (FU1 B3):** "no record =
   legacy provenance unavailable" gains the debt-aware reading **gated
   by the run-level `v2_publication_contract` marker** (§4.7, the six
   situations) — an explicit, versioned redefinition where the marker
   IS the version: `SYNCHRONOUS_V2` runs keep the legacy meaning
   byte-identically (pinned: the legacy absence shape still renders
   identically, and the new line never renders for them, for any
   connection class); `DEBT_V2` runs read the six-situation table. The
   design-01 ambiguity (a zero-eligible post-cutover run vs. a legacy
   run — both "no debt row, no ledger row") is resolved by the marker,
   and the presentation vocabulary is work-status only (§4.8, FU1 B5).
   The legacy interpretation itself (never NO_MATCH, never
   NOT_EVALUATED, never an AI failure) is unchanged.
3. **Report presentation (S2-C MUST-NOT) — revised (FU1 B5):** the
   bounded **work-status-only** status line (§4.8) — approval required
   against "no change to current UI authority presentation before
   Qualification V3". The approval scope is stated precisely: (a) the
   line presents ONLY the bounded work status (not required / pending /
   completed / completed-runtime-failure / failed) — no model decision,
   no confidence, no reason code, no attribute, no provider/model
   identity, no semantic conclusion (the design-01 "decision shown as
   advisory evidence" scope is withdrawn); (b) the line is standard
   report content under the pilot report-reachability model — it is NOT
   vendor commercial data and is NOT subject to the 4D-C-SEC Vendor
   Price CIDR gate (stated explicitly so the two authorizations are
   never conflated); (c) `SYNCHRONOUS_V2` (legacy) runs and non-
   COMPLETED runs render byte-identically to today for every connection
   class; (d) the vendor regions (compact quote, status notice, refresh
   section) remain byte-identical zero-knowledge for DENIED connections
   — the existing armed vendor-refresh DENIED nodes pass unmodified.
4. **Frozen nine-file digest pin** (`tests/execution/test_vendor_refresh_
   network_boundary.py`): `orchestration.py` and `runs/models.py` are
   protected files that Option B changes → two **recorded re-pin events**
   (precedent: MAIN-MERGE-FU1 re-pin for S2-B/C; VENDOR-REFRESH-WEB
   re-pin for the additive `WEB_UI` member), each as its own approved
   phase, the other seven files byte-identical.
5. **Web boundary allowlist** (`tests/web/test_web_boundaries.py`) —
   revised (FU1 B5): the status line needs exactly one runs-owned read
   symbol (the debt-state + marker projection for the run) → the narrow
   runs public-API addition, allowed by explicit allowlist extension
   (precedent: the vendor-refresh public names +1/+2 recorded
   evolutions). The allowlist is scoped so the web layer can read the
   debt state and the run marker but **no ledger record symbol** — the
   presentation cannot load V2 record content (work-status only, by
   construction; §4.8).
6. **New surfaces get new tests, not weakened old ones:** debt claim
   single-winner (file-backed concurrency, 8-node class precedent),
   lease expiry + reconciliation (no re-evaluation of persisted
   outcomes), **the FU1 B2 fencing triad (expired-but-still-running
   owner; new claimant over a live lease; late result from the old
   owner — §5.9)**, **the FU1 B1 reconstruction-equivalence suite
   (incl. the ESTABLISHED Micron alias scenario — §5.8)**, the
   reconcile-only startup pass bound (no long sweep before Waitress;
   **no claiming — FU2 C2** — §5.11), the corrected RP1–RP5 rollback
   gate (**no drain, no waiver — FU2 C4**) + the terminal-state
   preservation pin (§5.10), the six-situation coverage determinations
   (§5.10), the work-status-only presentation pins (vendor-region zero-
   knowledge preserved; the line renders for ALLOWED and DENIED CIDR
   connections alike over `DEBT_V2` COMPLETED runs — §5.6), **provider-
   unconfigured classification (FU2 C1 — resolved by the runtime's
   actual semantics, §4.5: a persistable `RUNTIME_FAILURE` →
   `COMPLETED`, never a debt-level `FAILED`)**, and **the queue-aware
   residence bound + load gate (FU2 C3 — §5.2)**. CLAUDE.md: replacement
   tests must preserve or strengthen the original contract; zero
   pre-existing node deleted/renamed/skipped/xfailed/deselected/
   weakened.
7. **Run-level coverage marker (FU1 B3 — new approval item):** the
   additive `ResearchRun.v2_publication_contract` column (bounded CHECK
   vocabulary `SYNCHRONOUS_V2` / `DEBT_V2`; the migration default
   `SYNCHRONOUS_V2` makes every pre-existing row the legacy marker by
   definition) — covered by the §4.12 item 4 `runs/models.py` recorded
   re-pin (the same re-pin event covers the debt table + the marker
   column; no second re-pin).
8. **Per-debt recorded context provenance (FU1 B1 — new approval
   item):** the debt row's immutable `context_provenance` field (CHECK-
   constrained to the frozen `ContextProvenance` vocabulary; ∅ or
   `[CUSTOMER_RETRIEVAL_RELATION]` in the live path), set in the
   publication transaction — the minimal bounded immutable data that
   makes the V2 input reconstructable from persisted data (§4.13).
9. **Terminal-state preservation (FU2 C4 — revised; the FU1 B3
   `FAILED → COMPLETED` drain transition is **withdrawn**):**
   `COMPLETED` and `FAILED` are terminal in this design — no surface
   (sweep, reconcile, reconcile-only pass, rollback gate, or any flag)
   may move a terminal debt, and the state-transition matrix is pinned
   by test (source + behavior). A separate recovery operation for
   `FAILED` debts is out of scope and requires its own explicit design +
   approval before any implementation; it is not introduced for
   rollback convenience.

**What Option B does NOT touch (no approval needed):** the V2 input
contract (23-field case), the prompt, the output schema (strict 6-key
JSON), the eligibility predicate, the authority derivation (FU2/FU3
tokens), the ledger row schema (until the A1 instrumentation version is
itself approved), the V1 path, 4A/4B/4C, HUMAN-REVIEW, vendor refresh,
FX, the FoxPro/SAP intake boundary, the vendor-region DENIED zero-
knowledge (FU1 B5: preserved — the CIDR gate and its armed nodes are
untouched; only the design-01 mis-scoping of the status line against
them is corrected).

### 4.13 Exact V2 input reconstruction from persisted data (FU1 B1 —
new)

The sweep must evaluate each debt with **exactly the same
`SemanticMatchCaseV2` the synchronous path would have constructed** —
same 23 fields, same case_id, same provenance, same reviewed target
context — from persisted data alone. This section is the proof of
record.

**Reconstruction proof (input by input).** The frozen synchronous
builder chain (EVIDENCE §5) is: `evaluate_semantic_matches_v2(request,
total_assessments, context_provenances_by_assessment=…, reviewed_
target_context=…)` → per eligible assessment: `derive_identity_state_
v2(assessment)` (pure) → `build_v2_product_evidence_profile(
observation, provenances, matched_facts=frozenset())` (pure; the
frozen S2-C safe builder — matched_facts = ∅ is a live-path constant of
record) → `build_semantic_match_case_v2(case_id=_v2_candidate_case_id(
assessment, idx), request, assessment, context, product_evidence,
provenances, reviewed_target_context)` (pure; the builder itself re-runs
and verifies the deterministic derivation — a foreign context cannot be
injected). Every input is reconstructable iff every value the live path
feeds it is persisted or purely derivable from persisted data:

| Case input | Live-path source | Persisted source for reconstruction | Class |
| --- | --- | --- | --- |
| `request` (MPN + description) | `run.to_research_request()` | the `runs_researchrun` row (persisted at intake; EVIDENCE §8.3) | [M] |
| `assessment` (the frozen 3C dataclass incl. `normalized_listing.observation`: source URL, title, MPN field, SKU, brand, price/currency/availability/condition/seller text, offer URL, raw reference; the match type; the decision) | `total_assessments[k]` | `PriceIntelligenceSnapshot.payload["assessments"][k]` — the frozen codec persists the full assessment array, every field, in order (EVIDENCE §8.4); the decode round-trip is frozen and digest-anchored | [M] |
| assessment **order** — the `idx` of `enumerate`, which feeds BOTH the case_id and the ledger `assessment_index` | `total_assessments` order | the payload array order — `aggregate_listing_prices` passes the input tuple through to `PriceAggregationResult.assessments` unchanged (same objects, same order; source-confirmed), so the published array order IS the evaluation order | [M]+[D] |
| deterministic identity context | `derive_identity_state_v2(assessment)` | re-run at reconstruction (pure, deterministic; the case builder re-runs it and fails closed on any disagreement) | [D] |
| candidate section (source URL, MPN field, SKU, evidence source) + structured product/commercial evidence | the bounded S2-C-FU1 builders over the observation | re-run at reconstruction (pure over the persisted observation) | [D] |
| `context_provenances` | `{CUSTOMER_RETRIEVAL_RELATION}` iff (a) the paid search used the ESTABLISHED alias-expanded query AND (b) this assessment originated from that search batch; else ∅ | **(a)** derivable: `ResearchMicronAliasSnapshot` (persisted pre-search; present ⇔ the alias fetch ran; status `ESTABLISHED` ⇔ the search query was alias-expanded — EVIDENCE §8.6–8.7) — **(b) read from the debt row's recorded `context_provenance` field** (persisted in the publication transaction — §4.1, §4.3). The reconstruction never re-derives (b) from run topology | [M] |
| `reviewed_target_context` | `reviewed_target_context_from_alias_result(alias_result)` iff ESTABLISHED; else explicit None | re-run over `decode_micron_alias_snapshot(payload)` (the codec round-trips to the self-validating result; the helper is pure and fails closed on a missing reviewed field); no alias snapshot row ⇔ no alias fetch ran (direct-sufficient or empty-MPN run) ⇔ explicit None | [M]+[D] |
| `case_id` | `candidate-{sha256(source_url)[:8]}-{idx}` | re-computed from the persisted source URL + the array position (both rows above) | [D] |

**The one input currently held only in memory (identified, FU1 B1):**
the per-assessment **search-batch membership** — which assessments
originate from the alias-expanded paid-search batch vs. 4D-A direct
acquisition. In a **mixed** run (direct acquisition enabled AND the
direct evidence insufficient AND the alias ESTABLISHED), the
`search_batch_assessments` list exists only inside the orchestrating
process: the snapshot payload records no direct/search boundary, the
alias snapshot references no assessments, and the execution evidence
rows carry per-URL FETCH facts without batch membership (EVIDENCE §8.8;
the observed UAT population is trivial for this input — §8.9, direct
acquisition disabled on the UAT host). The zero-search-results edge is covered by the same field: an
ESTABLISHED alias with an empty search batch assigns provenance to no
assessment (direct assessments stay ∅) — the per-debt field records the
fact, not a topology guess.

**Minimal bounded immutable data to persist at publication (FU1 B1):**
exactly one field — the debt row's `context_provenance` (the bounded
`ContextProvenance` vocabulary list for that assessment; ∅ or
`[CUSTOMER_RETRIEVAL_RELATION]` in the live path), set in the atomic
publication transaction from the live in-memory membership and immutable
thereafter (editable=False). It is minimal (no run-topology
reconstruction, no URL list, no payload), bounded (CHECK-constrained
vocabulary — no free text, no provider data), and sufficient (every
other case input is persisted or purely derived, per the table).
Rejected alternative (of record): a run-level `direct_assessment_count`
would also determine the boundary under the orchestration's "direct
before search" ordering — but it persists a count the case never reads,
reconstructed through an implicit ordering invariant; the per-debt
field persists the fact itself.

**No refetch or reinterpretation of live external data (FU1 B1).**
Reconstruction reads only local persisted rows (the run, the snapshot
payload, the alias snapshot, the debt row). The reviewed catalog body is
never re-fetched (the alias snapshot carries the body SHA-256, not the
body); the candidate page is never re-fetched (the observation is fully
persisted); no provider, search, FX, or vendor call is made; the
reconstruction is a pure function over durable rows (socket-blocked
sentinel test, §5.8). A future reviewed source is out of scope: until
one exists, `reviewed_target_context` has exactly the 4D-D shape above
(the frozen S2-C live-path limitation, unchanged).

**Mandatory deterministic equivalence tests (FU1 B1; acceptance §5.8).**
For each scenario: execute the real synchronous pipeline (fakes for the
transport only; a capturing runtime records the exact
`SemanticMatchCaseV2` objects the live path built), publish the run
(atomically — debts + marker), then run the reconstruction over the
persisted rows and assert **exact case equality** (frozen dataclass
equality, plus byte-equality of the frozen codec's case-section
encoding). Scenarios (the matrix of record):
1. **The ESTABLISHED Micron alias scenario** — the existing motivating
   run shape (`tests/execution/test_semantic_v2_motivating_case.py::
   TestNoMachinePriceContamination` — reviewed 4D-D catalog
   ESTABLISHED, alias-expanded search, the U5/NM-1 near-miss candidate
   carrying `CUSTOMER_RETRIEVAL_RELATION` + the reviewed target
   context): reconstructed case == recorded case, including case_id, the
   provenance set, and the full section-A reviewed-context block.
2. Non-ESTABLISHED alias (the UAT `bd992103` shape: `NO_AUTHORITY_
   MATCH` snapshot; provenance ∅; reviewed context explicit None).
3. No alias fetch (direct-sufficient run; no snapshot row; ∅/None).
4. **Synthetic mixed run** (direct acquisition + alias-expanded
   search): direct-assessment debts carry ∅, search-batch debts carry
   `CUSTOMER_RETRIEVAL_RELATION`, per debt; reconstruction == recorded
   per assessment. This scenario is the negative proof of the
   `context_provenance` field: a reconstruction that re-derived (b) from
   run topology has no durable input for it.
5. Zero-eligible run: no debt rows; reconstruction not invoked; the
   coverage determination = situation #2.
Additionally pinned: reconstruction fails closed on a foreign run
request (MPN/description mismatch vs. the snapshot payload — the replay-
binding precedent), on a marker/debt/eligibility disagreement (the §4.7
invariant query), and performs zero live work (sentinel).

### 4.14 Corrected architectural invariant → enforcing test (FU1, as
corrected by FU2 — the exact mapping of record)

Existing nodes are cited by their actual names; new nodes are
specified by file + planned node name (they are acceptance
specifications of §5; none may be deleted, renamed, skipped, xfailed,
deselected, or weakened to obtain green — CLAUDE.md). "Unmodified"
means the node passes without change.

| # | Corrected invariant (FU1) | Enforcing test(s) |
| --- | --- | --- |
| I-B1.1 | The debt rows (+ marker + `context_provenance`) are created in the run's atomic publication transaction — together or not at all | NEW (Phase 1) `tests/execution/test_semantic_v2_debt_publication.py::TestDebtPublicationAtomicity::test_debt_rows_and_marker_created_in_publication_transaction` + `::test_publication_failure_creates_no_debt_and_no_marker`; the ORIGINAL S2-C ledger-publication timing pins — incl. `tests/research/test_semantic_v2_boundaries.py::test_the_orchestration_v2_wiring_is_persist_only` and `tests/execution/test_semantic_decision_v2_execution.py::TestV2OutcomesPersist::test_every_eligible_candidate_gets_a_record` — are **preserved unmodified in Phase 1** (synchronous: records and debt rows persist together in the publication block, so the original timing contract still holds) and are re-pinned in **Phase 2** with the §4.12 item 1 replacement tests (contracts preserved/strengthened — FU2 C5) |
| I-B1.2 | The sweep reconstructs the exact synchronous V2 case from persisted data (the §4.13 proof), including the ESTABLISHED Micron alias scenario | NEW `tests/execution/test_semantic_v2_debt_reconstruction.py::TestReconstructionEquivalence::test_established_alias_motivating_case_reconstruction_equals_recorded` (over the existing motivating-run shape) + `::test_non_established_alias_reconstruction` + `::test_no_alias_fetch_reconstruction` + `::test_mixed_direct_and_alias_search_run_per_debt_provenance` + `::test_zero_eligible_run_no_reconstruction` |
| I-B1.3 | The per-assessment search-batch provenance is persisted at publication and is the reconstruction's sole source for it (no topology re-derivation) | NEW `::TestReconstructionEquivalence::test_mixed_direct_and_alias_search_run_per_debt_provenance` (above) + `tests/runs/test_semantic_v2_debt_model.py::TestDebtFieldVocabulary::test_context_provenance_check_constraint_and_immutability` |
| I-B1.4 | Reconstruction performs zero live work (no network, no provider environment, no re-fetch of the catalog or the candidate page) | NEW `::TestReconstructionEquivalence::test_reconstruction_performs_no_live_work` (socket-blocked + provider-env-removed sentinel; the S2-B zero-live precedent) |
| I-B1.5 | Reconstruction binds to the run (foreign request / marker–debt–eligibility disagreement fails closed) | NEW `::TestReconstructionEquivalence::test_reconstruction_refuses_foreign_run_request` + `tests/runs/test_semantic_v2_debt_coverage.py::TestCoverageInvariant::test_marker_debt_eligibility_disagreement_fails_closed`; existing replay run-binding nodes UNMODIFIED (`tests/execution/test_semantic_decision_v2_execution.py::TestV2ReplayThroughService::*`) |
| I-B2.1 | Single-winner claim: at most one invocation wins a **claim event** (one live lease at a time); the losers of that claim write zero rows and start no evaluation (concurrent execution under an EXPIRED lease is a different shape — I-B2.7, FU2 C2) | NEW `tests/runs/test_semantic_v2_debt_claim.py::TestClaimSingleWinner::test_concurrent_claims_exactly_one_winner` (file-backed, two processes; the 8-node vendor-refresh concurrency precedent) + `::test_loser_writes_no_row_and_evaluates_nothing` |
| I-B2.2 | An expired-but-still-running owner's late result persists nothing (no ledger row, no state change); the successor re-evaluates at most once | NEW `tests/runs/test_semantic_v2_debt_fencing.py::TestLeaseFencing::test_expired_still_running_owner_late_completion_discarded` (file-backed, pinned clock; call-count spy: the discarded attempt + exactly one committed row) |
| I-B2.3 | A new claimant cannot claim or complete over a live lease | NEW `::TestLeaseFencing::test_live_lease_refuses_second_claimant` + `::test_second_claimant_late_completion_fails_fence` |
| I-B2.4 | Only the current owner + generation + live lease may append the ledger result AND terminalize the debt (the fenced completion transaction is all-or-nothing) | NEW `::TestFencedTerminalization::test_wrong_owner_refused` + `::test_wrong_generation_refused` + `::test_expired_lease_refused` + `::test_fence_failure_rolls_back_ledger_append` (no row after rollback — the coverage audit query verifies) |
| I-B2.5 | The lease covers the worst case for every legal configured timeout: `L(T) = 2T + M_EVAL + M_LEASE` at T ∈ {300, 3600} (the design-01 fixed 30-min lease is withdrawn) | NEW `tests/execution/test_semantic_v2_debt_lease.py::TestLeaseBounds::test_lease_formula_over_configured_timeouts` + `::test_lease_recorded_on_debt_row` (fencing reads the recorded grant, never the environment); existing runtime-config timeout-validation pins UNMODIFIED (`tests/semantic/` config nodes) |
| I-B2.6 | A reconcile never re-evaluates a persisted outcome (row present → `COMPLETED`, zero additional model calls) **and never claims** (the fenced terminalization is over the RECORDED owner+generation; owner/generation/lease unchanged — FU2 C2) | NEW `::TestFencedTerminalization::test_reconcile_closes_debt_without_reevaluation` (call-count spy = 1; owner/generation/lease byte-unchanged); acceptance §5.4(c) |
| I-B2.7 **(FU2 C2)** | The reconcile-only startup pass captures no execution ownership: a row-ABSENT stale debt is left untouched after the pass (state/owner/generation/lease unchanged — the next scheduled sweep claims it immediately, no `L(T)` block); a row-PRESENT debt is terminalized by the fence over the recorded owner+generation. Duplicate evaluation under an expired lease (wedged owner still executing + successor) MAY happen, but exactly ONE fenced publication commits | NEW `tests/runs/test_semantic_v2_debt_fencing.py::TestReconcileOnly::test_startup_pass_leaves_row_absent_debt_unclaimed` + `::test_startup_pass_terminalizes_row_present_debt_without_claim` + `::TestLeaseFencing::test_overlapping_evaluations_under_expired_lease_single_fenced_publication` (file-backed, pinned clock; call-count spy: 2 evaluations, exactly 1 committed row, the late completion rolled back) |
| I-B3.1 | The six coverage situations are distinguishable from durable rows alone (marker + debts + ledger) | NEW `tests/runs/test_semantic_v2_debt_coverage.py::TestCoverageSituations::test_six_situations_distinguishable_from_durable_rows` (parameterized over the six shapes) |
| I-B3.2 | Legacy (`SYNCHRONOUS_V2`) absence semantics unchanged: no new line, report byte-identical, the frozen S2-B absence interpretation preserved | existing S2-B absence nodes UNMODIFIED (`tests/execution/test_semantic_decision_persistence.py` load-None semantics) + NEW `::TestCoverageSituations::test_legacy_run_report_byte_identical_no_status_line` |
| I-B3.3 | A zero-eligible post-cutover run is distinguished from a legacy run (the design-01 ambiguity closed) | NEW `::TestCoverageSituations::test_zero_eligible_debt_run_distinct_from_legacy_run` |
| I-B3.4 | Rollback preconditions RP1–RP5; a zero-PENDING backlog alone is NOT sufficient (a remaining `FAILED` debt blocks) | NEW `tests/runs/test_semantic_v2_debt_rollback.py::TestRollbackPreconditions::test_rollback_blocked_on_failed_debt` + `::test_rollback_gate_queries_print_rp1_rp5` + `::test_rollback_allowed_at_full_terminal_with_rows` |
| I-B3.5 **(FU2 C4 — revised; the FU1 B3 drain nodes are withdrawn)** | Terminal-state preservation: no surface moves a `FAILED` (or `COMPLETED`) debt — claim, sweep, reconcile, and rollback-gate invocations all refuse; the state-transition matrix has no `FAILED → COMPLETED` writer; a separate recovery operation is out of scope (no node in this design exercises one) | NEW `tests/runs/test_semantic_v2_debt_terminal.py::TestTerminalStates::test_failed_debt_refuses_any_reclaim` + `::test_completion_path_refuses_failed_debt` + `::test_state_transition_matrix_has_no_terminal_writer` (source pin over the debt model/service + behavior pins) |
| I-B4.1 | The healthy-path bound is consistent with the SLO: `I + O + W(T) ≤ 900 s` at T = 300 (parametric in T) | NEW `tests/runs/test_semantic_v2_debt_slo.py::TestBoundConsistency::test_healthy_path_bound_under_slo_window` + the §5.2 SLO-1 measurement (UAT) |
| I-B4.2 | The crash-recovery bound `L(T) + I + O + W(T)` is met (a killed owner recovers to terminal with exactly one row or `FAILED`) | NEW `tests/runs/test_semantic_v2_debt_crash.py::TestCrashRecovery::test_killed_owner_recovers_within_bound` (file-backed kill; scaled-down world; the production-scale number recorded from the formula) + acceptance §5.4 |
| I-B4.3 | The scheduler: one debt per invocation; the overlap policy skips (no pile-up); the kill bound `L(T) + 2O` leaves no wedge unrecoverable | NEW `tests/runs/test_semantic_v2_debt_sweep_command.py::TestSweepInvocation::test_one_debt_per_invocation` + `::test_double_invocation_cannot_double_evaluate` (the claim single-winner) + `tests/scripts/test_semantic_v2_scheduler_registration.py::test_task_registration_overlap_and_kill_bounds` (the bounded registration parameters pinned) |
| I-B4.4 | No long V2 sweep runs synchronously before Waitress startup; the startup pass is reconcile-only, ≤ 30 s, zero model calls, fail-open for the application, **and claims nothing (FU2 C2 — the no-claim behavior is pinned by I-B2.7)** | NEW `tests/scripts/test_pilot_launcher_startup_pass.py::test_launcher_runs_reconcile_only_pass_bounded` (source pin over `scripts\run_internal_pilot.cmd`: the `--reconcile-only` flag, the 30 s bound, no bare sweep) + `::test_startup_pass_failure_does_not_block_waitress` (simulated pass timeout → the server line still executes) |
| I-B4.5 **(FU2 C1 — shapes corrected)** | Supplementary unhealthiness never degrades the main path: the report renders, the price authority is untouched, the debt state is visible — **in the correct shapes**: task disabled → debt `PENDING` (it does not execute or fail work); provider env missing → debt `COMPLETED` with a persistable `RUNTIME_FAILURE` row (situation #5, presentation shape (d)); executor/construction failure → debt `FAILED` / `EXECUTOR_ERROR` (situation #6, shape (e)) | NEW `tests/web/test_semantic_v2_status_presentation.py::TestSupplementaryUnhealthy::test_report_renders_200_with_task_disabled_pending_debt` (kept) + `::test_report_renders_200_with_provider_unconfigured_runtime_failure_completed_debt` (replaces the FU1 `…_provider_down_failed_debt` node — a provider-unconfigured evaluation is persistable, not a debt failure) + `::test_report_renders_200_with_executor_error_failed_debt` (the FAILED-debt presentation shape, from an unpersistable class); existing S2-C authority-firewall suites UNMODIFIED (`tests/execution/test_semantic_decision_v2_execution.py::TestAuthorityFirewall::*`, `tests/execution/test_semantic_v2_motivating_case.py::TestNoMachinePriceContamination`) |
| I-B4.6 **(FU2 C3)** | Queue-aware residence bound and load gate: a debt claimed at position `k` (FIFO — §4.4) with `r` attempts is terminal within `B(k, r) ≤ r·k·(I + O + W(T)) + (r − 1)·(B1 + B2)` (worst case; the 15-minute target holds at k = 1, r = 1 — 780 s); the load gate (G1 max concurrent backlog, G2 sustained arrival vs. the one-at-a-time service rate, G3 measured service/residence times) is a durable query of record | NEW `tests/runs/test_semantic_v2_debt_slo.py::TestQueueResidence::test_residence_bound_fifo_positions` (file-backed, pinned clock, N simultaneous debts; the Task Scheduler overlap skip is simulated) + `::test_load_gate_queries_print_g1_g2_g3` |
| I-B5.1 | Before Qualification V3 the presentation is work-status only: no model decision, confidence, reason code, attribute, provider/model, or semantic conclusion renders (the design-01 "decision shown" scope withdrawn) | NEW `tests/web/test_semantic_v2_status_presentation.py::TestWorkStatusOnly::test_completed_line_shows_no_decision_or_confidence_or_reason` (parameterized over the five work-status shapes; "must-never-render" absence pins over the decision/confidence/reason vocabulary — the F5 precedent) + `::test_display_module_reads_no_ledger_symbol` (web-boundary allowlist, §4.12 item 5) |
| I-B5.2 | The status line is standard report content: it renders for a COMPLETED `DEBT_V2` run on both CIDR-ALLOWED and CIDR-DENIED connections with identical bytes; the Vendor Price CIDR gate is never applied to semantic evidence access; the vendor regions stay zero-knowledge for DENIED | NEW `::TestAccessBoundary::test_status_line_renders_identically_for_denied_cidr_connection`; existing armed vendor-refresh DENIED zero-knowledge nodes UNMODIFIED (`tests/web/test_vendor_refresh_web.py` DENIED suite + the FU1/FU2 DENIED nodes) |
| I-B5.3 | `SYNCHRONOUS_V2` runs and non-COMPLETED runs render the line nowhere (byte-identity for every connection class) | NEW `::TestAccessBoundary::test_legacy_run_renders_no_line_any_connection` + `::test_non_completed_run_renders_no_line_any_connection` |
| I-B5.4 | A client-supplied flag cannot alter the line (server-derived bounded vocabulary only) | NEW `::TestWorkStatusOnly::test_forged_query_flag_cannot_alter_status_line` (the vendor-refresh F1 forged-flag precedent) |
| I-B5.5 | The deterministic price authority and the human-review authority contracts are untouched (no contract redesign beyond the §4.12 approved items) | existing suites UNMODIFIED: `TestAuthorityFirewall`, `TestNoMachinePriceContamination`, the V1 review-candidate nodes, the `V2_AUTHORITY_QUALIFIED is False` drift pins, the frozen nine-file digest pin (with the two recorded re-pins — §4.12 item 4) |

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
   claim and publication. (The publication transaction additionally
   writes the marker + the debt rows — local SQLite DML, bounded in
   milliseconds; the bound is unchanged.)
2. **V2 eventual completion — separate metrics (FU1 B4 corrected; FU2
   C3 queue-aware).** Successful evidence completion is measured **separately** from
   terminal `FAILED` states (the design-01 lumped them). Parametric
   bounds of record (I = 60 s sweep interval; O = 60 s invocation
   overhead; M_EVAL = 60 s; M_LEASE = 240 s; T = the configured and
   validated request timeout, **pinned to the qualified default 300 s
   for UAT measurement**): per-evaluation wall `W(T) = 2T + M_EVAL`
   (660 s at the default); lease `L(T) = W(T) + M_LEASE` (900 s at the
   default).
   - **SLO-1 (evidence terminalization; FU2 C3 — queue-aware
     recalculation):** ≥ 99 % of debts reach `COMPLETED` (a ledger row
     present — EVALUATED **or** RUNTIME_FAILURE; the bounded outcome the
     evaluation produced) within **15 min** of run completion (p95 over
     a 2-week UAT population) — **the 15-minute completion target is
     RETAINED as an acceptance target and is NOT lowered to fit the
     proposed Scheduler**. Queue-aware recalculation for multiple debts
     sharing the one-at-a-time Scheduler: a *service period* is
     `S = I + O + W(T) = 780 s` worst case per debt served. A debt
     claimed at queue position `k` (FIFO — §4.4) with `r` attempts
     (`r ≤ 3`, §4.6) is bounded by `B(k, r) ≤ r·k·S + (r − 1)·(B1 + B2)`:
     k = 1, r = 1 → **780 s = 13 min** (the healthy path is UNCHANGED —
     `I + O + W(T) = 60 + 60 + 660 = 780 s ≤ 900 s` at the default, a
     non-crashed debt completes inside the SLO window with 120 s of
     headroom, as before); k = 2, r = 1 → 1560 s (26 min); **k = 5,
     r = 1 → 3900 s (65 min) — the UAT N=5 shape (run `37826c4f`, 5
     simultaneous debts) exceeds the 15-minute target structurally for
     positions ≥ 2**; k = 1, r = 3 → 6540 s (109 min). Skipped
     overlapping triggers are accounted for: each 720 s (O + W)
     invocation overlaps ~12 of the 60 s triggers, skipped by the
     "do not start a new instance" policy — no OS-level queue (the queue
     is the debt table) and no cost beyond the S period per debt.
     **Measurable load gate (of record) — determines whether the pilot
     may use a single Scheduler instance or requires a separate
     capacity decision:** over the UAT population, a single
     one-at-a-time Scheduler instance is valid only if ALL three hold:
     **G1** the maximum concurrent debt backlog at any instant is 1 (no
     debt is ever claimed at position ≥ 2 — the 15-minute target's
     regime); **G2** the sustained debt arrival rate (debt publications
     per 24-h window, maximum window) is ≤ the one-at-a-time service
     rate `1/S ≈ 4.6 debts/h` (worst case; the G3 measured service
     times give the practical rate); **G3** the measured per-debt
     service times p50/p95 (claim → terminal) are recorded and the p95
     residence at position 1 is ≤ 15 min. Any violation (G1 ≥ 2 — e.g.
     a multi-debt run — G2 > rate, or G3 p95 > 15 min) → a separate
     capacity decision (batch >1 per invocation, a second scheduled
     task, or a worker process — each its own approval gate; §4.10) —
     with the 15-minute per-debt target retained unchanged.
   - **SLO-2 (bounded-failure rate, tracked separately):** the debt-
     level `FAILED` fraction (bounded reason; no ledger row) over the
     same window is reported as its own metric — it is NOT counted as
     evidence completion; > 1 % is a Phase-3 review trigger (a
     misconfiguration or provider-health signal, visible via the work-
     status line). **(FU2 C1)** the `FAILED` fraction counts
     UNPERSISTABLE failures only — a provider-unconfigured evaluation is
     `COMPLETED` / `RUNTIME_FAILURE` (situation #5), not `FAILED`.
   - **INV-1 (no stuck debt, hard invariant):** zero debts in
     `PENDING`/`EVALUATING` past the worst-case non-terminal residence
     `L(T) + 3·(I + O) + 3·W(T) + B1 + B2` (5340 s ≈ 89 min at the
     default; B1 = 5 min, B2 = 30 min) — an audit query of record; a
     violation fails acceptance.
   - **Crash-recovery bound (measurable):** a killed evaluation owner
     recovers to a terminal shape within `L(T) + I + O + W(T)` (1680 s
     = 28 min at the default) — measured by the file-backed kill test in
     a scaled-down world with the formula pinned; the production-scale
     number is recorded, not approximated.
   - **Per-evaluation wall:** ≤ `W(T)` for the configured T (the
     transport's own request timeout bounds each attempt; a timeout is a
     bounded execution failure, fallback-eligible per the frozen
     allowlist), so a debt whose evaluation exceeds `W(T)` is
     structurally impossible; a process-level wedge is covered by the
     scheduler kill bound (§4.10) + the lease (FU1 B2).
3. **No lost or duplicated evidence.** Invariant queries return zero
   violations: (a) every V2-eligible assessment of every post-cutover
   (`DEBT_V2`) COMPLETED run older than the SLO-1 window (15 min at the
   qualified default) has exactly one of {a `COMPLETED` debt + its
   ledger row, a `FAILED` debt}; (b) the (run, assessment_index) ledger
   uniqueness holds (constraint +
   service guard — a forced double persist fails closed); (c)
   pre-cutover ledger rows are byte-identical (digest-verified replay
   sample ≥ 6 rows, incl. both UAT runs); (d) no debt was ever evaluated
   twice with a persisted outcome (reconcile-before-evaluate pinned by
   file-backed concurrency test + production audit query) — and (FU1
   B2) a superseded owner's late completion never produced a row or a
   state change (the stale-completion audit: every ledger row's debt is
   `COMPLETED` under the generation that appended it; zero fenced-away
   orphans).
4. **Crash/restart recovery.** File-backed scripted tests (SQLite, two
   processes): (a) kill between publication and sweep → restart →
   **the reconcile-only startup pass terminalizes row-present debts
   immediately (without claiming them — FU2 C2) and leaves row-absent
   debts untouched, and the scheduled sweep (≤ I) completes the rest** —
   all debts terminal within the crash-recovery bound (no long startup
   sweep — FU1 B4); (b) kill mid-evaluation → after lease expiry → next
   sweep reclaims (new `claim_generation`), final state exactly one
   ledger row OR `FAILED`, zero duplicates; (c) kill between ledger
   persist and debt terminalization → reconcile closes the debt
   `COMPLETED` with ZERO additional model calls (call-count spy = 1);
   (d) **(FU1 B2)** the fencing triad — an expired-but-still-running
   owner (its late completion persists nothing: no row, no state change;
   the successor re-evaluates at most once; exactly one row), a new
   claimant over a live lease (zero rows, zero evaluations), and a late
   result from a superseded owner after the successor committed (fence
   fails; rollback; exactly one row remains — the audit query verifies).
5. **Zero change to deterministic price authority.** The S2-C
   authority-firewall + no-machine-price-contamination suites pass
   **unmodified**; a UAT run's `PriceIntelligenceSnapshot` payload is
   byte-identical to the same-evidence synchronous-mode run (recorded
   pair); 4A input remains `total_assessments` (source pin preserved);
   Machine Price / Reviewed Price / review queue values equal the
   deterministic-only derivation.
6. **Access and commercial-data boundaries (FU1 B5 — corrected).** The
   Vendor Price CIDR authorization and semantic evidence access are
   separate existing boundaries, stated as such: all armed vendor-
   refresh DENIED zero-knowledge nodes pass **unmodified** (the vendor
   regions — compact quote, status notice, refresh section — remain
   total zero-knowledge for DENIED connections); NEW armed nodes:
   (a) the work-status line renders for a COMPLETED `DEBT_V2` run on
   both CIDR-ALLOWED and CIDR-DENIED connections with identical bytes
   (standard report content — NOT vendor commercial data — the CIDR
   gate is never applied to it); (b) the vendor regions remain byte-
   identical for DENIED connections with the line present; (c)
   `SYNCHRONOUS_V2` runs and non-COMPLETED runs render no line on any
   connection class (byte-identity to today); (d) a forged query flag
   cannot alter the line; (e) the debt table carries no provider
   payload, no raw model text, no credential, no base URL, no search-
   result list (adversarial construction test: a runtime result or a
   search response containing such text cannot be written through the
   debt path; the debt's `context_provenance` is vocabulary-only).
7. **Test collection preservation and safety regression.** Full-suite
   collection ≥ 8,669 nodes with node-level diff showing **zero**
   deleted/renamed/skipped/xfailed/deselected (only additions and the
   explicitly approved in-place re-pins of §4.12, each name- and
   contract-preserving); **(FU2 C5)** in-place re-pins are phase-
   attributed: Phase 1 re-pins only §4.12 items 2–3, 5–9, and the
   ORIGINAL S2-C ledger-publication timing tests (§4.12 item 1's
   affected pins) pass **unmodified** in Phase 1 (synchronous); the item
   1 timing-contract redesign + replacement tests land in Phase 2;
   the frozen nine-file digest pin passes with the
   two recorded re-pins and seven byte-identical files; the 8
   vendor-refresh concurrency nodes pass; full-suite result equals the
   baseline modulo the documented pre-existing workstation failure class
   (the 32-node CRLF raw-byte digest + preview-fixtures class), node-for-
   node identical.
8. **V2 input reconstruction (FU1 B1).** The §4.13 deterministic
   equivalence matrix passes: for each of the five scenarios (the
   ESTABLISHED Micron alias motivating case; non-ESTABLISHED alias; no
   alias fetch; the synthetic mixed direct + alias-search run; the zero-
   eligible run) the reconstructed `SemanticMatchCaseV2` equals the
   synchronous path's recorded case exactly (frozen dataclass equality +
   codec case-section byte equality); the reconstruction performs zero
   live work (socket-blocked sentinel, provider environment removed);
   the per-debt `context_provenance` field is present on every debt row
   created in the UAT population (100 % coverage query); the mixed-run
   scenario proves the field is necessary (a reconstruction without it
   cannot determine the search-batch membership from durable rows).
9. **Lease fencing (FU1 B2).** The §4.14 fencing suite passes (I-B2.1
   – I-B2.6): single-winner claim; the expired-but-still-running
   owner's late result persists nothing (no row, no state change — the
   coverage audit query verifies); a new claimant over a live lease
   writes zero rows and evaluates nothing; a superseded owner's late
   result fails the fence and rolls back (exactly one row remains);
   the lease formula `L(T) = 2T + M_EVAL + M_LEASE` holds at T ∈ {300,
   3600} with the grant recorded on the debt row (fencing never reads
   the environment); a reconcile never re-evaluates a persisted outcome
   (call-count spy = 1).
10. **Coverage and rollback (FU1 B3; FU2 C4).** The six-situation
    determination is a pure function of durable rows (the parameterized
    coverage test); the legacy (`SYNCHRONOUS_V2`) report is byte-
    identical (no line, for every connection class); the rollback drill
    executes RP1–RP5 verbatim (the gate queries print each precondition
    with its count); a constructed remaining-`FAILED`-debt shape
    **BLOCKS** the rollback (the design-01 zero-PENDING-alone gate is
    pinned as insufficient; **no drain, no waiver** — the FU1 B3 pre-
    rollback drain and recorded-exception path are withdrawn: a signed
    document does not restore old-code understanding of a missing V2
    record); a `FAILED` debt is terminal — no surface moves it (the
    state-transition-matrix pin passes); an emergency degraded rollback,
    if ever executed, is explicitly logged as NOT contract-preserving
    (no acceptance node asserts contract preservation over it).
11. **Scheduler and launcher bounds (FU1 B4; FU2 C1/C2/C3).** The task
    registration pins the overlap policy (do-not-start-new-instance) and
    the kill bound `L(T) + 2O`; the launcher runs the reconcile-only
    pass (source pin: the `--reconcile-only` flag, the 30 s bound, zero
    model calls; **no claiming — a row-absent debt is left untouched
    and a row-present debt is terminalized over the recorded
    owner+generation — FU2 C2**) and starts Waitress regardless of the
    pass outcome (simulated pass timeout → the server line executes);
    one debt per sweep invocation (a backlog of N claims exactly N over
    N invocations, FIFO); **the supplementary-unhealthiness shapes
    (FU2 C1 — corrected; the main path is unaffected in every shape —
    application availability preserved while supplementary execution is
    unhealthy):** (a) scheduled task disabled (provider environment
    normal): a fresh UAT run completes with its report reachable (≤ the
    §5.1 bound) and its debt remains `PENDING` — **a disabled Scheduler
    leaves work pending; it does not execute or fail work** (the debt
    is claimable when the task is re-enabled); (b) task enabled, provider
    environment removed: the debt is `COMPLETED` with a persistable
    `RUNTIME_FAILURE` ledger row (bounded error class
    `PROVIDER_NOT_CONFIGURED`; one zero-latency attempt, no fallback —
    outside the frozen allowlist; situation #5, presentation shape (d))
    — **never** `FAILED` / `PROVIDER_NOT_CONFIGURED`; (c) task enabled,
    runtime construction failure (invalid configured timeout) or
    executor programming exception: the debt is `FAILED` /
    `EXECUTOR_ERROR` (situation #6, shape (e)). The §5.2 load gate
    (G1–G3) is measured over the UAT population and printed by the
    sweep command's bounded output (FU2 C3).

## 6. Recommendation and trade-offs

**Recommended: Option B (nonblocking supplementary V2), implemented in
the bounded phases below, with Option A1 instrumentation as Phase 0.**
**ChatGPT review of record (FU1): accepted as the preferred direction;
implementation ON HOLD pending the B1–B5 corrections, now incorporated
in place in this revision.**

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
- The rollback path has a measurable safety gate: the corrected
  **RP1–RP5 preconditions** (FU1 B3 — the design-01 drain-to-zero gate
  was necessary but not sufficient: a remaining `FAILED` debt without a
  ledger row would misread as legacy absence under the old code;
  **FU2 C4** — a remaining `FAILED` debt BLOCKS the rollback with no
  drain and no waiver: a signed-exception document does not restore
  old-code understanding of a missing V2 record, an emergency degraded
  rollback is NOT contract-preserving and is never presented as such,
  and terminal states are preserved — any separate recovery operation
  is explicitly designed and approved on its own; §4.11).

Accepted costs (the honest trade-off):

- One additive migration + one new table + one new command + one
  scheduled task + one launcher-script line (deployment surface grows
  by exactly these; no broker/queue/worker process).
- **Nine** frozen surfaces require explicit redesign approval (§4.12
  items 1–9; FU1 added the coverage marker and the per-debt recorded
  provenance to the design-01 five; **FU2 C5** attributes item 1 — the
  timing-contract redesign + replacement tests — to Phase 2, so Phase 1
  preserves the original S2-C timing tests unmodified, and **FU2 C4**
  replaces the bounded drain transition with terminal-state
  preservation):
  the S2-C §9 timing pin, the S2-B absence semantics (now marker-gated
  and work-status-only), the S2-C report-presentation MUST-NOT (bounded
  work-status line — no decision presentation before Qualification V3),
  two digest re-pins, one web-allowlist extension (scoped to the debt-
  state read — no ledger symbol). **Without that approval, Option B may
  not start** — this document (as corrected by FU1) is the approval
  request.
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
`token_usage` (prompt/completion), and `finish_reason`; **a versioned
instrumentation adapter if needed** (the approved direction; the adapter-
registry precedent — §8 item 5); old records replay byte-identically; no
timing/behavior change (synchronous V2 stays). Exit: one UAT run whose
84-class window is attributed to route + attempt + tokens from the
production ledger alone.

**Phase 1 — Debt lifecycle + explicit states (no timing change).**
Additive migration (debt table incl. `context_provenance` + the lease/
generation fields — the FU1 B3 drain field is withdrawn, FU2 C4 — CHECK +
UNIQUE; **the run-level
`v2_publication_contract` marker column** — FU1 B1/B2/B3); debt rows
created in the run's atomic publication transaction (with the marker and
the per-debt recorded provenance); synchronous evaluation still
terminalizes the debt in the same transaction (so every run is
`COMPLETED`-debt — the pending/failed machinery exists but is not yet
exercised by timing); the bounded **work-status-only** status line renders
(not required / pending / completed / completed-runtime-failure / failed —
NO decision / confidence / reason before Qualification V3 — FU1 B5);
**the §4.13 reconstruction-equivalence suite lands here** (it needs only
the persisted debt + marker, not the sweep); the six-situation coverage
determination is pinned; §4.12 items 2–3, 5–9 approved and re-pinned in
this phase; **the original S2-C ledger-publication timing tests (§4.12
item 1's affected pins) are preserved UNCHANGED in this phase — Phase 1
remains synchronous (debt rows and ledger records persist together in
the atomic publication block, so the original timing contract still
holds); the item 1 timing-contract redesign + replacement tests belong
to Phase 2 (FU2 C5)**. Exit: full regression + UAT shows identical run
windows (±
network variance), the work-status-only presentation is pinned, the
reconstruction matrix (incl. the ESTABLISHED Micron alias + the synthetic
mixed run) is green, and the six situations are determined from durable
rows alone.

**Phase 2 — Decouple (the latency change).** Orchestration step 4b stops
evaluating; sweep command (single-winner claim / **the `L(T)` lease with
ownership generation + atomic fenced terminalization** / reconcile —
**never claims; terminalizes row-present debts over the recorded
owner+generation — FU2 C2** / bounded retries — FU1 B2); **§4.12 item 1
re-pins HERE — the approved timing-contract redesign (debt created in
the publication transaction; ledger records persist in the debt-
completion transaction), with replacement tests preserving or
strengthening every original safety invariant of the S2-C timing pins
(FU2 C5)**; **the reconcile-only startup pass in the
launcher (≤ 30 s, zero model calls, fail-open, no claiming — FU2 C2) +
the bounded Task
Scheduler registration (overlap policy "do not start a new instance",
kill bound `L(T) + 2O`) — FU1 B4; NO long sweep before Waitress
startup**; §4.12 item 4 re-pins (recorded events). Exit: acceptance
criteria §5.1, §5.4 (incl. the fencing triad + the reconcile-only no-
claim pin — FU2 C2), §5.9, §5.10, §5.11 measured
on fresh UAT runs (N=1 and a constructed N≥2 shape), crash-recovery file-
backed suite green, and **the corrected RP1–RP5 rollback drill (incl.
a constructed remaining-`FAILED`-debt shape that BLOCKS the rollback —
FU2 C4) executed and
recorded**.

**Phase 3 — Hardening + decision inputs.** Two-week UAT population
metrics against **the separated §5.2 metrics (SLO-1 evidence
terminalization p95; SLO-2 bounded-failure rate reported separately;
INV-1 no-stuck audit; the crash-recovery bound — FU1 B4) AND the §5.2
load gate G1–G3 (FU2 C3 — the decision of record for single Scheduler
instance vs. separate capacity decision)**; the A2
concurrency decision (adopt/hold) from the real ledger distribution;
fallback-route health check (A3) informed by first persisted per-attempt
data; **the configured-timeout governance check (T pinned to the
qualified default 300 s for the SLO; the lease formula re-verified if T
ever moves — FU1 B2)**; re-open worker-vs-scheduler ONLY on SLO-1
failure. Exit: the performance evidence-of-record v2 replaces this one;
no contract change.

Each phase: no test deleted/renamed/skipped/xfailed/weakened; recorded
re-pins only where §4.12 approves them; the phase's §4.14 invariants are
the entry gate (their tests must exist and pass before the phase is
reviewed); `manage.py check` 0 issues; `makemigrations --check --dry-run`
clean post-migration; full-suite node-level diff of record.

## 8. Unresolved architectural decisions (for the approval gate)

1. **Debt policy defaults** (3 attempts; ≈5 min / ≈30 min backoffs; the
   lease is now the **formula** `L(T) = 2T + M_EVAL + M_LEASE` with
   proposed `M_EVAL = 60 s`, `M_LEASE = 240 s`; I = 60 s; O = 60 s —
   FU1 B2/B4) — proposed bounded values, not yet approved. The design-01
   fixed 30-min lease is withdrawn (safe only for T ≤ 750 s; the runtime
   supports a configurable timeout to the 3600 s ceiling).
2. **Task Scheduler vs separate worker** — this design recommends the
   scheduler (no new supervised process); the re-open trigger is a
   measured **SLO-1** (§5.2) failure.
3. **The report status line's exact wording and placement** — an S2-C
   MUST-NOT surface; requires the explicit redesign approval of §4.12.3
   (FU1 B5 scope: **bounded work-status only** — no decision, no
   confidence, no semantic conclusion before Qualification V3; standard
   report content, never CIDR-gated).
4. **Phase 1/Phase 2 split vs merged approval** — the split keeps each
   diff reviewable (schema+presentation, then timing); a merged phase
   would ship the change in one approval. Recommended: split.
5. **Instrumentation versioning shape (Phase 0)** — versioned successor
   adapter (new output schema version) vs additive envelope section;
   both reuse the row without migration; the adapter-registry precedent
   favors the versioned adapter.
6. **Provider-unconfigured classification (FU2 C1 — RESOLVED by the
   runtime's actual semantics; no longer open).** A missing provider env
   is a **persistable** semantic runtime failure (a `RUNTIME_FAILURE`
   ledger row, bounded error class `PROVIDER_NOT_CONFIGURED`; one zero-
   latency attempt, no fallback — outside the frozen allowlist; §4.5,
   EVIDENCE §8.14) → the debt is `COMPLETED` at evaluation time
   (situation #5). **Unpersistable** failures (construction/validation
   exception on an invalid configured timeout; programming exception —
   never swallowed; retry exhaustion) → the debt is `FAILED` with
   `last_error_class` ∈ {`EXECUTOR_ERROR`, `RETRY_EXHAUSTED`}. The
   behavior change from synchronous mode stands: the run completes and
   the debt terminalizes (for the provider-unconfigured case,
   `COMPLETED` / `RUNTIME_FAILURE` — never the rejected silent-PENDING
   alternative, and never a fabricated debt-level `FAILED`).
7. **Sweep batch size** — default 1 debt/invocation (proposed; keeps a
   single scheduled invocation ≤ `W(T) + O` ≈ 720 s at the default);
   batch >1 is a tuning decision deferred to Phase 3.
8. **(FU2 C4 — RESOLVED; the FU1 B3 open decision is closed)** the
   stricter policy governs: **no terminal debt ever leaves its terminal
   state** in this design — no `FAILED → COMPLETED` transition, no pre-
   rollback drain (both withdrawn: a signed-exception document does not
   restore old-code understanding of a missing V2 record, and terminal-
   state history is not rewritten for rollback convenience); a remaining
   `FAILED` debt blocks the rollback with NO drain option and NO waiver.
   A separate recovery operation for `FAILED` debts, if required, is
   explicitly designed and approved on its own (out of scope here).
9. **(FU1 B1 — new) the per-debt `context_provenance` field** — the
   minimal bounded immutable data of §4.13 (proposed) vs. the rejected
   run-level `direct_assessment_count` alternative (recorded in §4.13).

## 9. Strict-boundary compliance (this task)

Documentation only. Design-01 (the base commit): two files created
(`docs/SEMANTIC_V2_PERFORMANCE_DESIGN_01.md`, `docs/SEMANTIC_V2_
PERFORMANCE_EVIDENCE_01.md`). FU1: the **same two files updated in
place — no new report created**. FU2 (this revision): the **same two
files updated in place — no new report created**; every correction is
marked (FU2) at its location (design: the revision record, §4.1–§4.14,
§5, §6, §7, §8, §9; evidence: the header, the §3 [D] note, the new
§8.14–8.15).
In both: no production code modified; no migration created; no test
modified/deleted/skipped/weakened (the new test nodes above are
acceptance specifications, not changes); no frozen prompt/model/route/
temperature/token-limit/fallback-policy change; no benchmark rebaseline
(the acceptance criteria are corrected, not rebased — the UAT shapes of
§1 remain the measurement baseline); no destructive git command; the
existing untracked evidence (incl.
`docs/LOCAL_UAT_PERF_01_SEMANTIC_V2_LATENCY_ANALYSIS.md` and the `tmp_*`
session artifacts) preserved byte-identical; the UAT database opened
read-only only (`file:...?mode=ro`); nothing merged or deployed.
**Every existing test and every frozen authority contract is preserved;
the only contract redesigns are the explicitly identified §4.12 items
(1–9), each requiring ChatGPT approval before implementation; no
implementation may begin until that approval is granted (the
implementation is ON HOLD per the FU1 review of record).**
