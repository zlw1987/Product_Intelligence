# PRODUCT-INTEL.VREF-R1-DESIGN — Vendor Refresh R1 Execution & Operator Safety Architecture

**Design-Only Proposal for ChatGPT Independent Architecture Review**

- **Task type:** DESIGN ONLY (VREF-R1-DESIGN-GATE). No implementation. No
  source, test, migration, settings, or deployment changes were made by this
  design. One new document exists: this file.
- **Frozen R0 implementation baseline (work base for this design):**
  `3983db4b57e9b960d5bf6841042c93a14687fdd0`
  (branch `feature/vendor-refresh-r0`, tip commit
  "PRODUCT-INTEL.VREF-R0-FU1-GATE: authorized test-contract correction
  (Task C)"). This design was investigated in a dedicated isolated worktree
  `C:/dev/Product_Intelligence_vref_r1_design` on new branch
  `feature/vendor-refresh-r1-design` created at exactly that SHA.
- **Frozen design contract (read via Git object access, not merged or
  cherry-picked):**
  `a87ff1b5665f76e96b0c2628459e8975df3d4095:docs/VENDOR_ONLY_REFRESH_DESIGN.md`
  — "PRODUCT-INTEL.VENDOR-REFRESH-DESIGN2 — Vendor-only Refresh",
  DESIGN2-FU3, 1,897 lines.
- **R0 state:** APPROVED / FROZEN. R0's completed decisions and R0 source
  are not reopened by this document. R0 is exactly: persistence
  (migration 0012), the `VendorRefreshExecution` model, the four lifecycle
  CAS primitives, bounded errors, public exports, and offline tests. R0 has
  no management command, no provider call, no endpoint, no template.
- **Production branch baseline:** `cde2a802c54372da088a7d1876f450cbf9bd7c69`
  (branch `pilot-vendor-status-ux-a`). This is an ancestor of the R0 base
  [VERIFIED: `git log` chain cde2a80 → 1f5cdd8 → ad7d68b → 3983db4].
- **Historical production test baseline:** 5,959 nodes / 148 files
  [VERIFIED in this session by `--collect-only` at cde2a80].
- **Frozen R0 test collection:** 6,082 nodes / 149 files [VERIFIED in this
  session by `--collect-only` at 3983db4; the +123-node delta is fully
  accounted in §1.5].
- **Reviewer / approval gate:** ChatGPT (independent architecture
  reviewer). The pushed document is NOT an approved design and does NOT
  authorize implementation.
- **Every statement is marked:**
  - **[VERIFIED]** — read directly from the frozen SHAs in this session
    (worktree at 3983db4, `git show` object access for DESIGN2), with
    file/line references; or established by a controlled probe recorded in
    Appendix A.
  - **[PROPOSED]** — a design decision in this document, requiring ChatGPT
    approval before any implementation.
  - **[OPEN]** — genuinely unresolved; requires a decision at this gate.

---

## 1. Source and frozen-contract inventory

### 1.1 Branch topology and isolation [VERIFIED]

- Development `main` (inspected at `a87ff1b5665f76e96b0c2628459e8975df3d4095`,
  the DESIGN2-FU3 commit) carries the divergent Semantic V2 line and an
  independently numbered migration `0012` for `SemanticDecisionRecord`.
  This design does **not** merge, cherry-pick, or rebase `main`. [VERIFIED:
  `git log` on both lines; DESIGN2 §1.3 records the same divergence and the
  D9 option (a) decision that the implementation base is the production
  line.]
- `docs/PRODUCT_INTELLIGENCE_STATUS.md` and
  `docs/PRODUCT_INTELLIGENCE_PLAN.md` at the R0 base 3983db4 are the
  pilot-line documents (3,996 / 6,627 lines). They do not contain a VREF
  section: the three R0 commits (`1f5cdd8`, `ad7d68b`, `3983db4`) modified
  only `product_intelligence/runs/**` and `tests/**` [VERIFIED:
  `git show --stat` of each R0 commit]. This is consistent with DESIGN2
  §1.3's observation that the pilot-branch phases are not canonically
  recorded in the STATUS/PLAN documents; the frozen DESIGN2 contract and
  the R0 source at 3983db4 are therefore the authoritative baseline
  record for this design. Recorded here as an observation, not a
  conflict: no frozen contract is contradicted.
- `CLAUDE.md` is byte-identical between a87ff1b and 3983db4 [VERIFIED:
  `git diff --stat` shows no CLAUDE.md delta]. Its durable rules (frozen
  phase semantics, test preservation, layer boundaries, no destructive
  git, commit/push only when asked) bind this design.

### 1.2 Frozen R0 source (investigated at 3983db4) [VERIFIED]

| File | Lines | What was verified |
|---|---|---|
| `product_intelligence/runs/vendor_refresh_claims.py` | 611 | Exactly four public primitives: `trigger_vendor_refresh` (L134), `claim_vendor_refresh` (L327), `complete_vendor_refresh` (L381), `fail_vendor_refresh` (L518). Operator bound 1..128 enforced in the service (L109–118, L158–190); trigger eligibility (parent exists / COMPLETED / has `PriceIntelligenceSnapshot` / non-empty MPN; original supplement snapshot absence is legal); concept-1 active-child dedup returns the existing child; concept-2 post-terminal new child; INSERT race → savepoint rollback → winner lookup; claim/complete/fail are single conditional UPDATEs with bounded loser errors. `fail_vendor_refresh` REJECTS the reserved `EXECUTION_INTERRUPTED` before any UPDATE (L560). `complete_vendor_refresh` validates only the bounded V1 schema-version agreement at dict level before the UPDATE (L425 ff.). **The trigger return contract: `VendorRefreshExecution` in every case — an existing active child (L283–284), the created object (L318–319), or the race winner (L309–311). It carries NO created-versus-existing discriminator.** |
| `product_intelligence/runs/models.py` (L1602–2022) | 2022 | `VendorRefreshState` (L1607), `VendorRefreshFailureReason` (L1648, incl. reserved `EXECUTION_INTERRUPTED` and `R0_LEGAL = ALL - {EXECUTION_INTERRUPTED}`), `VendorRefreshTriggerSource` (L1700, `MANAGEMENT_COMMAND` only), `VendorRefreshExecution` (L1718): UUID PK, FK `parent_run` CASCADE `related_name="+"`, `requested_mpn` (verbatim capture), `active_slot` 1/NULL sentinel, `operator` (self-reported trigger initiator), lifecycle timestamps, `result_schema_version`/`result_payload` (NULL until COMPLETED), `failure_reason`. Docstring states the four lifecycle CHECK shapes and the C6 immutability accuracy (editable=False is not a write barrier). |
| `product_intelligence/runs/errors.py` (L141–234) | 234 | `VendorRefreshError` base + `VendorRefreshTriggerError` (parent_not_found / parent_not_completed / no_snapshot / no_mpn / invalid_operator / invalid_trigger_source), `VendorRefreshClaimError`, `VendorRefreshCompletionError` (invalid_schema_version / invalid_payload), `VendorRefreshFailureError` (reserved_execution_interrupted / invalid_failure_reason). All bounded, content-free on untrusted input. |
| `product_intelligence/runs/migrations/0012_vendor_refresh_execution.py` | 38 | `CreateModel VendorRefreshExecution` only; parent 0011; CHECK constraints incl. `vendor_refresh_valid_failure_reason` which **admits** `EXECUTION_INTERRUPTED` (the reserved value is storage-legal — the R1 transition needs no schema change); `UNIQUE(parent_run, active_slot)` as `vendor_refresh_one_active_per_parent`; history index `(parent_run, created_at, id)`. No data migration. No other table touched. |
| `product_intelligence/runs/__init__.py` | — | Lazy `__getattr__` export maps; `_VENDOR_REFRESH_EXPORTS` frozenset (L119) = exactly the four primitives + five error classes; model/vocabulary exports in `_MODEL_EXPORTS`. |
| `product_intelligence/runs/execution_claims.py` | — | The 4C-A compare-and-set precedent. NOTE: its module docstring (L40) says "SQLite supports row-level locking through SELECT FOR UPDATE" while the implementation comments (L200–206) correctly state "SQLite does NOT support SELECT FOR UPDATE - this pattern works everywhere" and uses a single conditional UPDATE. The `select_for_update`-is-a-no-op statement is also in `product_intelligence/runs/ai_assisted_review.py` L254 and `product_intelligence/execution/fx_observation_cache.py` L46. **This design never claims row-level locking on SQLite; the CAS + the file write-lock mechanisms below are the actual primitives.** |
| `product_intelligence/runs/comparable_execution_claims.py` | 379 | The 7C-A four-primitive precedent: `trigger_comparable_research` (L61, idempotent incl. COMPLETED-child return), `claim_comparable_research` (L187), `complete_comparable_research` (L242), `fail_comparable_research` (L312). |
| `tests/runs/test_vendor_refresh_claims.py` | 2,134 | 115 nodes (see §1.5/§11). Key classes: `TestNoRecoverySurface` (L1373–1508) incl. `_FORBIDDEN_SURFACE_TOKENS` (L1359–1370: reclaim, reset, retry, recover, recovery, force, stale, reassign, resurrect, interrupt); reserved-reason rejection + zero-mutation + no-DB-statement proofs (L1203–1283); `test_reserved_reason_still_representable_in_database` (L1260) proving the storage constraint admits the reserved value; `_row_snapshot` (L176) all-field re-read pattern. |
| `config/settings.py` (L97–110) | — | SQLite via `django.db.backends.sqlite3`, `NAME` from `PI_SQLITE_PATH` (absolute path, outside the checkout per runbook), **no `OPTIONS`** — hence no journal-mode, no busy-timeout override: default rollback journal and the Python `sqlite3` default 5.0 s busy timeout apply [VERIFIED + probes, Appendix A]. |
| `docs/INTERNAL_PILOT_DEPLOYMENT.md` + `scripts/run_internal_pilot.cmd` | — | Windows host; Waitress WSGI (`python -m waitress ... config.wsgi:application`, default thread configuration — no explicit `--threads`); `manage.py` commands are the standard operational interface (`pilot_check` preflight); DB backup = file copy with the application stopped; runbook requires CMD access for migrations/ops. Single deployment host is the documented posture. |

### 1.3 Frozen production code the R1 execution builds on [VERIFIED]

| File / symbol | Reference | Contract verified |
|---|---|---|
| `providers/internal_vendor.py` — `InternalVendorAdapter.lookup` | L1631–1720+ | At most ONE network call per lookup; GET only; 10 s socket timeout (`_VENDOR_TIMEOUT`, L107) — a per-operation socket timeout, NOT an absolute wall-clock deadline; 1 MiB body bound (L108); no redirects (30x refused); `ProxyHandler({})` (no ambient proxy); no cookies/Authorization; base URL deployment-owned via `PI_VENDOR_LOOKUP_BASE_URL` (lazy `_ensure_configured`, raises `ValueError` on malformed config); URL built by `_build_lookup_url` (L271: `{base}?partno=<urlencoded MPN>`); bounded transport failures RETURN `CommercialSourceResponse(status=FAILED, retrieved_at=None)` — they do not raise; programming errors propagate. |
| `providers/commercial.py` — `CommercialLookupQuery` | L141–160 | `__post_init__` rejects non-str, **strips surrounding whitespace** (interior untouched), rejects empty. `InternalVendorAdapter.lookup` transmits `query.mpn` — the stripped form. This is why the R1 fail-closed normalization check exists (frozen DESIGN2 §3.4 step 4). |
| `research/identity.py` — `compare_part_numbers` (frozen 2A) | L268–308 | EXACT / NORMALIZED_EXACT / UNKNOWN only; no PARTIAL/CONFLICT; structural-character-first abstention; TypeError only on non-str/None args. |
| `research/commercial_supplement_codec.py` (frozen V1 codec) | L262 (`_SCHEMA_VERSION_V1 = 1`), L382 (`encode_research_supplement_result`), L433 (`decode_research_supplement_result`) | Strict required keys, reject extra keys, Decimal-as-string, tz-aware UTC datetimes, `vendor_mpn_match_type` EXACT/NORMALIZED_EXACT only, `brand_new_basis` exactly `VENDOR_API_POLICY`, bounded `detail` vocabulary. Fail-closed both directions. |
| `execution/orchestration.py` — `_try_vendor_commercial_lookup` | L1124–1257 | The 4D-B policy: config check (env, `.strip()`, absent → return None = no call, no row); ONE `InternalVendorAdapter()` + `lookup`; per-candidate frozen 2A binding (EXACT/NORMALIZED_EXACT → `SupplementSourceObservation` with `brand_new=True, brand_new_basis="VENDOR_API_POLICY"`; else `SupplementSourceIssue(MPN_MISMATCH, "vendor_mpn_mismatch")`); provider issues copied bounded (detail=None); final status mapping (transport FAILED → `"FAILED"`, `retrieved_at=None`; else `response.status.value` + `response.retrieved_at`); codec encode; `SupplementCodecError` propagates (programming defect). Invoked at L594 (post-aggregation, pre-publication), outside the atomic final publication (L575+). |
| `execution/comparable_research.py` — `execute_comparable_research` | L732–805 | The existing execution-function pattern: claim FIRST (L766), then pipeline, then complete; bounded failure → `_terminate_failed` + `ComparableResearchExecutionError`; unexpected → best-effort `fail_comparable_research(INTERNAL_ERROR)` + propagate. `ComparableResearchExecutionError` defined at L116 (execution layer, exported from `execution/__init__`). |
| `execution/comparable_runtime.py` | whole file (48) | The thin default-provider adapter: the ONLY place in the web/command stack that constructs concrete provider classes; delegates once to the frozen execution function. |
| `web/views.py` — `research_comparables` | L1032–1094 | The existing precedent for trigger-then-synchronous-execution of a PENDING child by the SAME invocation (POST, CSRF, bounded redirects). R1's command surface is analogous but host-side, and R1 adds the §3.3 ownership constraint that this web path does not have (documented in §3.3 as the contrast case). |
| `runs/management/commands/` | dir listing | Contains exactly `__init__.py` and `pilot_check.py` at 3983db4. **No `vendor_refresh*` command exists** (frozen R0 boundary, pinned by R0 tests §11). |
| Layer/AST guards | `tests/domain/test_domain_boundaries.py` (CALLER_TOKENS L59, VENDOR_TOKENS L63–73; `test_the_execution_layer_imports_no_web` L192–212), `tests/providers/test_provider_boundaries.py` (INNER_ROOTS L98–104 = domain/research/runs/web/evaluation; `test_nothing_is_wired_to_the_search_boundary_yet` L222–246; provider file-list pin L294–321; model inventory L250–258), `tests/web/test_web_boundaries.py` (INNER_ROOTS L34–39 = domain/research/runs/evaluation; `test_the_inner_layers_do_not_import_the_web_layer` L226–236; `ALLOWED_EXECUTION_IMPORTS` L102–109), `tests/runs/test_research_run_boundaries.py` (per-file CALLER/VENDOR token scans over RUNS_ROOT L273–290 — RUNS_ROOT rglob includes `management/commands/` and `migrations/`) | The per-file guards that every NEW R1 file will automatically be collected by (§1.5 explains the node deltas; §11/§13 state the content constraints the new files must satisfy). No guard pins "runs must not import execution" — see §10.1/§14-O4. |

### 1.4 Frozen DESIGN2 contract points that R1 must honor [VERIFIED at a87ff1b]

- §3.3 final R0 state-transition table (rows 1–9; rows 3–4 the ONLY legal
  RUNNING→terminal transitions in R0; row 9 forbids recovery-based
  terminalization in R0) and the F2 "what the CAS guarantees" paragraph
  (atomic single-winner terminalization, NOT issuer identity).
- §3.6 "Future R1 operational recovery gate (specified now; NOT R0
  scope)": manual interruption only on sufficient trusted external
  evidence that the prior process is terminated; wall-clock alone
  insufficient; atomic conditional transition; reserved
  `EXECUTION_INTERRUPTED` = "execution interrupted; the external Vendor
  request outcome is explicitly UNKNOWN"; the R1 gate transition is its own
  separately approved primitive — the ONLY sanctioned writer of the
  reserved reason; no lease/scheduler/supervisor invented.
- §4.2 (Option A management command, `--operator` self-reported
  provenance, host-access authorization, deployment prerequisite: host
  permissions + operational audit review before R1 deploys), §4.6
  (trigger-vs-execution provenance options 1/2; no new model field without
  approved justification), §5.2 (R1 repeat safeguard: evaluated BEFORE
  persistence and BEFORE any Vendor API request; refusal leaves NO new
  PENDING child; `--force-repeat`; concurrent invocations "reviewed
  separately at R1" — that review is §3.4 of THIS document), §11 (R1 scope:
  `execution/vendor_refresh.py`, `execution/vendor_refresh_runtime.py`,
  shared 4D-B helper extraction per D10, `runs/management/commands/
  vendor_refresh.py`, recovery gate, provenance mechanism, trusted
  ownership, tests §10.3(2)(3)(4)(5)), §12.1 confirmed decisions D1–D10,
  §12.2 open mechanisms M1–M4 (this document answers M1–M4).

### 1.5 Verified test baselines (this session) [VERIFIED]

- Collection at cde2a80: **148 files / 5,959 nodes** (reproduces the
  historical production baseline).
- Collection at 3983db4: **149 files / 6,082 nodes** (reproduces the frozen
  R0 collection).
- The +123-node R0 delta, exactly:
  - `tests/runs/test_vendor_refresh_claims.py`: NEW, 115 nodes.
  - `tests/runs/test_research_run_boundaries.py` 92→96 (+4): the two
    per-file token-scan guards picked up the two new `runs/` files
    (`vendor_refresh_claims.py`, `migrations/0012_vendor_refresh_execution.py`).
  - `tests/providers/test_provider_boundaries.py` 147→149 (+2) and
    `tests/web/test_web_boundaries.py` 165→167 (+2): the two
    INNER_ROOTS per-file import guards picked up the same two new `runs/`
    files.
  - Reproducible via `python -m pytest --collect-only` per-file diff.
- R0 claims suite green at 3983db4 (this worktree): **115 passed, 5
  subtests passed, 0 failed** (0.90 s).
- Frozen 4D-B + codec suites green at 3983db4 (this worktree):
  `tests/execution/test_4d_b_vendor_commercial.py` (19) +
  `tests/execution/test_4d_b_vendor_section_integration.py` (19) +
  `tests/research/test_commercial_supplement_codec.py` (46) = **84 passed,
  0 failed** (4.41 s). These are the behavior-identity reference for the
  D10 helper extraction (§10).

### 1.6 Verified SQLite/deployment facts (probes, Appendix A) [VERIFIED]

Deployment database = file-based SQLite, default rollback journal (no WAL),
no Django `OPTIONS` (no journal/busy overrides); effective busy timeout =
Python `sqlite3` default 5.0 s. Probe results:

1. A zero-row write statement executed inside a transaction acquires
   SQLite's RESERVED (write) lock immediately (~0.4 ms).
2. A second independent connection attempting any write blocks until the
   first commits, then proceeds against the fresh committed state.
3. A new reader proceeds normally while a writer holds the RESERVED lock
   (rollback journal: SHARED is not blocked by RESERVED).
4. A writer's commit succeeds while another connection holds a short read
   transaction (within the busy timeout).
5. A process killed while holding the write lock: the OS releases the lock
   on process death; the uncommitted transaction (including an uncommitted
   INSERT) is rolled back by journal recovery; a fresh connection writes
   immediately; the killed transaction's mutations are absent.
6. Lock contention beyond the busy timeout surfaces as
   `sqlite3.OperationalError: database is locked` (bounded, recognizable).
7. The same behavior holds end-to-end through the Django ORM on the
   deployment configuration: `VendorRefreshExecution.objects.filter(
   parent_run_id=<P>, active_slot=2).update(active_slot=2)` inside
   `transaction.atomic()` updates **0 rows** (the CHECK constraint makes
   `active_slot=2` unmatchable) while the second Django connection's
   identical statement blocks ~760 ms until the first commits, then reads
   the fresh state; the row is byte-identical afterwards.

No probe modified any repository file; probe databases were temporary and
deleted.

---

## 2. Precise R1 scope and exclusions

### 2.1 In scope (R1, per frozen DESIGN2 §11, detailed here) [PROPOSED]

1. **M1** — the operational recovery gate for stuck RUNNING children:
   evidence criteria, operator procedure, one separately-gated R1
   terminalization primitive + its command, `EXECUTION_INTERRUPTED`
   semantics.
2. **M2** — trusted execution ownership enforced in the execution path
   (single-invocation claim→execute→terminalize; no owner token; no schema
   change).
3. **M3** — trigger-vs-execution provenance: execution constrained to the
   creating invocation (DESIGN2 §4.6 option 1); honest handling of
   pre-existing PENDING children.
4. **M4** — the five-minute repeat safeguard made atomic under the actual
   SQLite deployment (serialized short write transaction; `--force-repeat`).
5. **§7 provider boundary** — `execution/vendor_refresh.py`,
   `execution/vendor_refresh_runtime.py`, the management command, the
   D10 shared 4D-B binding/encoding helper extraction, exact call sequence,
   expected behaviors (malformed payloads, provider programming exceptions,
   database failures, lost terminalization races).
6. **§8 test-contract evolution plan** and the **§9 R1 regression matrix**.

### 2.2 Out of scope (exclusions — none of these change in R1) [PROPOSED]

- No R0 source change: `runs/vendor_refresh_claims.py`,
  `runs/models.py`, `runs/errors.py` (additive-only exception in §13 — a
  NEW error class appended; the four R0 primitives and their signatures are
  untouched), migration 0012, and every R0 test node except the
  explicitly enumerated evolutions in §11 (each requires ChatGPT approval
  at the implementation gate).
- No schema change: no new model, no new field, no new migration. The R1
  recovery transition stores the already-admitted reserved value
  (`EXECUTION_INTERRUPTED`) in the existing `failure_reason` column
  (verified: R0 CHECK `vendor_refresh_valid_failure_reason` admits it;
  R0 test `test_reserved_reason_still_representable_in_database` pins it).
- No R2 surface: no `execution/vendor_refresh_history.py`, no
  `web/vendor_refresh_presentation.py`, no view/template changes, no
  `ALLOWED_EXECUTION_IMPORTS` web-allowlist change.
- No R3 surface: no Web POST trigger, no request idempotency identity
  (concept 3), no Django authentication, no session, no user model, no
  CSRF surface, no new URL.
- No FX activity: no `providers.fx` import, no `FxObservationStore`
  read/write, no `ResearchFxSnapshot` touch, zero FX network calls, no
  historical FX reuse (confirmed D2(a) governs display in R2; R1 persists
  no FX field).
- No search/page/semantic/comparable/micron-alias activity from the
  refresh path (frozen DESIGN2 §6.1 table; enforced by new AST/sentinel
  guards §12).
- No parent mutation: `ResearchRun` state, `PriceIntelligenceSnapshot`,
  original `ResearchSupplementSnapshot`, `ResearchFxSnapshot`,
  `ResearchMicronAliasSnapshot`, `ExecutionEvidenceRecord`,
  `AiAssistedReviewCandidate`, `ComparableResearchExecution` — all
  byte-identical before/after any R1 operation (frozen DESIGN2 §9
  invariant).
- No lease, scheduler, background worker, queue, or automated reclaim of
  any kind (frozen D3(b)).
- No merge of development `main`; no deployment; no database migration
  execution against production; no destructive git operation.

---

## 3. M1–M4: alternatives and recommended decisions

### 3.1 M1 — RUNNING operational recovery gate

**Frozen rules being implemented** [VERIFIED DESIGN2 §3.3 row 9, §3.6,
§12.1 D3(b), F1]: a RUNNING child MUST NOT be reclaimed merely because its
timestamp is old; the 10 s Vendor socket timeout is a per-operation socket
timeout, not an absolute deadline; recovery requires sufficient trusted
external evidence that the prior execution process is terminated; the
transition is a single atomic conditional write; the external Vendor
outcome is preserved as explicitly UNKNOWN; the reserved
`EXECUTION_INTERRUPTED` is written ONLY by this separately approved R1
primitive — never via the R0 `fail_vendor_refresh`, which rejects it with
zero row mutation (R0 behavior, untouched, re-pinned by §12).

**What provenance the row already carries** [VERIFIED]: `id`,
`parent_run`, `requested_mpn`, `state`, `active_slot`,
`trigger_source`, `operator` (self-reported trigger initiator),
`created_at`, `started_at`, `finished_at`. **It does not carry a PID, host
name, or command line.** Any evidence design must live with that.

**The execution process that can still act on a RUNNING child**
[PROPOSED, derived]: under M2/M3 (§3.2/§3.3), the ONLY code path that can
issue `complete`/`fail` for a child is the single invocation that won its
claim — which, on the R1 command path, is also the invocation that INSERTed
it (combined transaction, §3.4). That invocation is a standalone
`python manage.py vendor_refresh <parent-run-uuid> --operator <string>`
process on the deployment host (no web trigger, no worker — §2.2). The
command line therefore carries the parent run UUID; at the moment of
recovery the target child is the parent's UNIQUE active child
(`UNIQUE(parent_run, active_slot)`), so the parent UUID in the command line
pins the process to the exact child. The process necessarily started
BEFORE `created_at` (it created the row) and claimed at `started_at`
(combined transaction: `created_at ≈ started_at`, same commit).

**Trustworthy termination evidence — exact criteria** [PROPOSED]. Recovery
is permitted only when the operator establishes, on the deployment host,
exactly one of the following, with the observation recorded (bounded
stdout of the recovery command + the host operational audit):

- **E-REBOOT** — the host booted at a time ≥ the child's `started_at`
  (observable via system uptime or the boot event). A reboot terminates
  every user process unconditionally; the execution process cannot be
  alive. Sufficient by itself.
- **E-SCAN** — a complete process-table scan of the deployment host
  (e.g. `wmic process get ProcessId,CreationDate,CommandLine` or
  `Get-CimInstance Win32_Process`) shows **no running process** whose
  command line matches the execution signature
  `manage.py vendor_refresh <parent-run-uuid>` (any `--operator` value)
  AND whose creation time is ≤ `started_at` + tolerance (tolerance
  PROPOSED 60 s [OPEN-O1]). Rationale: a live process created after
  `started_at` + tolerance cannot be the original claim winner (the claim
  CAS already committed at `started_at`; a later command invocation over
  the same parent sees the active child, reports in-progress, and makes
  zero calls — it structurally cannot terminalize this child, §3.2/§3.3),
  so it does not disqualify recovery. A live process created at or before
  `started_at` + tolerance with the matching signature ⇒ the original
  execution MAY be alive ⇒ **recovery DENIED** (conservative direction:
  denial only ever delays, never risks a double call).
- **E-KILL** — the operator explicitly stopped the matching execution
  (closed its command window, or `taskkill /PID` on a process matching the
  signature), then re-verified E-SCAN. The operator's stop act plus the
  re-scan is the termination proof.

**How the evidence links to the exact child and originating process**
[PROPOSED]: the link is (parent run UUID in the command line) + (the child
is the parent's unique active child at check time) + (process creation
time ≤ `started_at` + tolerance). The recovery command's bounded stdout
records: child id, parent run, `started_at`, recorded `operator`, the
evidence class token, the check time, and the outcome.

**Evidence that is INSUFFICIENT (enumerated)** [PROPOSED]:

1. Wall-clock age of `started_at` alone (frozen rule; the process may be
   alive mid-call or mid-write at any age).
2. A PID alone, at any time (Windows PIDs are reused; a bare PID match
   proves nothing about the process — the signature + creation-time pair
   is the predicate; PID reuse can at worst create a conservative
   FALSE-DENIAL, never a false recovery, because a reused PID running the
   matching signature created before `started_at`+tolerance is
   indistinguishable from the original and is treated as "may be alive").
3. Absence of a process on ONE host when the operator cannot attest the
   complete host inventory where the command could have run (single-host
   deployment is the runbook posture [VERIFIED]; if multi-host operation
   is ever introduced, E-SCAN must cover every candidate host or the
   result is HOLD).
4. Stale or unverified log lines ("the command printed an exit message"):
   DESIGN2 §4.5 makes no claim that trustworthy OS audit evidence exists;
   until the R1 host permissions + operational audit review verifies the
   command-logging posture, logs are corroborative only, never
   sufficient.
5. "The vendor didn't answer / the call must have timed out" — the
   external outcome is UNKNOWN by definition; the adapter's 10 s timeout
   bounds the socket operation, not the attempt, and a completed request
   with a lost response is precisely the case this gate exists for.
6. A matching process observed but whose signature cannot be fully read
   (e.g. wrapped launch that hides arguments) — indeterminate ⇒ HOLD.

**Authorized operator procedure** [PROPOSED]:

1. Run the normal command:
   `python manage.py vendor_refresh <parent-run-uuid> --operator <id>`.
   It reports the active child (id, state, recorded operator,
   `created_at`/`started_at`) and exits with zero calls (in-progress
   path, §3.4).
2. Establish E-REBOOT, E-SCAN, or E-KILL per the criteria above, on the
   deployment host, with host administrator privileges (required for a
   complete process-table read across sessions).
3. If evidence is established: run
   `python manage.py vendor_refresh_manual_terminalization <child-uuid>
   --operator <id> --evidence {reboot|process-scan|operator-stop}`.
   (Command/file names PROPOSED; the `--evidence` token makes the
   attestation explicit in the command line and stdout, so the host
   operational audit carries it; the vocabulary is bounded and pinned by
   tests §12.)
4. If evidence CANNOT be established (host unreachable, scan
   indeterminate, inventory not attestable): **HOLD** — do nothing to the
   database. The child stays RUNNING and occupies the active slot (safe
   direction: it can never cause a double Vendor call; it only blocks new
   refreshes for that parent). The HOLD is recorded in the operational
   audit (who, when, which evidence was missing) and may be re-attempted.
   This design does not invent evidence where it cannot be established.

**The exact R1-only conditional terminalization transition** [PROPOSED]:

One new runs-layer primitive in a NEW module
`product_intelligence/runs/vendor_refresh_manual_terminalization.py`
(name PROPOSED, token-free w.r.t. `_FORBIDDEN_SURFACE_TOKENS` so the R0
public-API guard stays literally green — §11), function
`manual_terminalize_vendor_refresh_execution(child_id, *, at=None)`:

```
UPDATE runs_vendorrefreshexecution
   SET state='FAILED', active_slot=NULL,
       finished_at=<at or now>, failure_reason='EXECUTION_INTERRUPTED'
 WHERE id=<child_id> AND state='RUNNING' AND active_slot=1
   AND finished_at IS NULL
```

- Single conditional UPDATE in its own transaction (same CAS idiom as the
  R0 primitives).
- **1 row affected** → transition committed. The row stores
  `EXECUTION_INTERRUPTED` with the frozen semantics: "execution was
  interrupted; the external Vendor request outcome is explicitly UNKNOWN"
  — the prior request may have been sent and may have completed; the row
  must never be read as "the lookup failed" nor as success. Identity
  fields (`id`, `parent_run`, `requested_mpn`, `operator`,
  `trigger_source`, `created_at`, `started_at`) are UNTOUCHED; only
  `state`, `active_slot`, `finished_at`, `failure_reason` change
  (invariant I9, §4).
- **0 rows affected** → re-read the row, then (bounded, zero mutation):
  - COMPLETED → the original execution completed (or another terminal
    write won the race): report the actual terminal shape; NO
    interruption is recorded over a real result.
  - FAILED (any reason) → same: report the actual reason.
  - PENDING → bounded error: the gate applies to RUNNING only (a PENDING
    row is the separate orphan case, §3.3).
  - absent → bounded error (parent-deleted cascade or bad id).
- No retry of the transition; the lost race is reported, not re-attempted.
- New bounded error class `VendorRefreshManualTerminalizationError`
  (appended to `runs/errors.py`; additive only) with reasons
  `already_terminal` / `pending_row` / `not_found`.

**R0 compatibility** [PROPOSED, pinned by §12]: `fail_vendor_refresh`
still rejects `EXECUTION_INTERRUPTED` before any UPDATE (R0 code
untouched; R0 tests untouched and re-run green); the R1 primitive is the
ONLY sanctioned writer of the reserved value; the R1 primitive lives in a
separate module, so the R0 AST pin
(`test_module_defines_no_recovery_functions`, which scans
`vendor_refresh_claims.py` only) and the four-primitive `__all__` pin
remain literally true.

**No resumption or reuse** [PROPOSED]: a recovered child is terminal
FAILED — `claim_vendor_refresh` rejects terminal rows (R0 CAS
precondition `state=PENDING`), the R1 command never claims a child it did
not create (§3.3), and a later refresh of the parent is a NEW child row
(concept 2) with its own single call. The recovered row can never be
resumed or reused for a second Vendor call — structurally.

**Alternatives considered and rejected** [PROPOSED]:

- *Command-side process scan built into the recovery command* (the command
  itself runs `wmic`/`tasklist` and auto-verifies): rejected for R1 —
  OS-specific subprocess coupling in a Django management command, a new
  failure mode, and it would convert an operator attestation into code
  that DESIGN2 §4.5 says must not claim trustworthiness without the
  verified audit posture. The operator scan + `--evidence` token is the
  minimal honest mechanism. (May be revisited after the operational audit
  review.)
- *A schema field for evidence (e.g. `recovery_evidence` text)*: rejected
  — no schema change in R1 (§2.2); the row's reserved reason + timestamps
  plus the bounded stdout/audit carry the evidence; DESIGN2 F1 designed
  the storage to admit the transition without any schema change.
- *Extending the R0 `fail_vendor_refresh` with a reserved-reason escape
  hatch (e.g. a `recovery=True` keyword)*: rejected — it would modify R0
  service code and weaken the F1 zero-mutation rejection pin; the separate
  primitive keeps the R0 surface exactly four.

### 3.2 M2 — Trusted execution ownership

**Question set (task §4), answered against the real deployment threat
model** [PROPOSED unless marked]:

- *Who may invoke the execution function?*
  `execute_vendor_refresh(child_id, *, vendor_adapter=None)` is invoked
  in production ONLY by the R1 management command, via
  `execute_vendor_refresh_with_default_providers(child_id)`
  (`execution/vendor_refresh_runtime.py` — the thin adapter, mirroring
  `comparable_runtime.py` [VERIFIED precedent]). There is no web trigger
  (R3 deferred, 8C-gated), no worker, no queue, no scheduler (§2.2), and
  no retry path. Tests invoke it with injected counting fakes.
- *Can the command accept an arbitrary existing child ID?* No. The
  normal command's positional argument is the PARENT run UUID
  (`vendor_refresh <run-uuid> --operator <identity> [--force-repeat]`);
  the child is derived internally by the trigger inside the serialized
  transaction (§3.4). No child id is ever operator-supplied on the normal
  surface, so the command cannot be pointed at an arbitrary child. (The
  recovery command accepts a child id — but its ONLY capability is the
  M1 RUNNING→EXECUTION_INTERRUPTED transition; it never claims, executes,
  or calls any provider.)
- *What prevents a losing claimant from calling the adapter?* The claim
  CAS is the FIRST action of `execute_vendor_refresh` (the frozen pattern
  of `execute_comparable_research` L766 and `execute_research_run`: paid
  work only after claim). A loser raises `VendorRefreshClaimError` before
  the adapter is constructed or called; the adapter is constructed lazily
  after the config/normalization checks, all post-claim. Sentinel tests
  (§12) prove zero construction AND zero call on every losing path.
- *What prevents accidental complete/fail from another execution path?*
  Three layers: (1) structural — complete/fail are called only from the
  claim winner's own call stack (single outer boundary, mirroring 4C-B's
  "ONE singular post-claim catastrophic-failure boundary" and 7C-B);
  (2) the R0 terminal CAS — after one terminal write commits, any other
  complete/fail affects 0 rows and raises with zero mutation (frozen,
  R0-pinned); (3) the command surface never terminalizes a child it did
  not create+claim (§3.3).
- *What does the mechanism actually guarantee against concurrent
  cooperating workers?* For ANY number of concurrent invocations that go
  through the R0 claim primitive on one child: at most one claim winner
  (CAS); the adapter is reachable only after claim success in the winner's
  stack; at most one terminal write (CAS). Hence: **exactly one
  `InternalVendorAdapter.lookup()` per successfully claimed child, zero
  calls for every loser and for every terminal child, ever** — and the
  complete/fail that records the outcome is issued by the same invocation
  that won the claim, unless that invocation died (in which case NOTHING
  is terminalized until the M1 gate, which writes the reserved reason, not
  a result).
- *What does it NOT guarantee against arbitrary privileged Python/DB
  writers?* Nothing, and it is not claimed to: a process with host access
  can call `fail_vendor_refresh(child, INTERNAL_ERROR)` on a RUNNING row
  (the schema does not authenticate the issuer — frozen F2), call the R1
  recovery primitive without the operator evidence steps (the evidence
  gate is procedural, outside the database), or issue raw SQL. This is
  the same threat class as any server-side capability, and DESIGN2 §4.2
  explicitly scopes the threat model to external/subnet actors and human
  operator error on a controlled host. A claim-owner token (schema change:
  a random column written by claim, matched by complete/fail) would
  authenticate ISSUERS to each other but would stop no privileged writer
  (they can read/copy the token or bypass the services) — it is
  unjustified complexity for the real threat model. [PROPOSED: NO owner
  token, NO schema change. Revisit ONLY if a future phase introduces a
  second legitimate execution surface (worker/queue) — none does in
  R1–R2.]
- *STOP check (task §4):* the proposed mechanism DOES guarantee the
  required behavior under the real deployment threat model (single
  Windows host; command-only mutation surface; cooperating operators;
  crashes). No architecture decision request is triggered. [PROPOSED]

### 3.3 M3 — Trigger vs executor provenance and orphaned PENDING

**The actual trigger contract** [VERIFIED, task warning honored]:
`trigger_vendor_refresh` returns a `VendorRefreshExecution` in ALL cases
— existing active child (concept 1), the created object, or the INSERT
race winner — with NO created-versus-existing discriminator in the return
value or on the row. Ownership cannot be read off the return value alone.
Under the §3.4 serialized transaction, ownership IS established by the
pre-INSERT snapshot taken under the database write lock (any competing
writer — command or programmatic — must hold the same lock to INSERT, so
it is serialized behind the snapshot). Details in §3.4.

**Option A — only the invocation that creates the child may claim and
execute it** [PROPOSED — RECOMMENDED]:

- Mechanism (no schema change): the normal command, inside its serialized
  transaction: snapshot active children → cooldown decision → (if
  allowed) `trigger_vendor_refresh` → if the returned child was NOT in the
  snapshot (proof: this invocation's INSERT created it) →
  `claim_vendor_refresh` on it → COMMIT. If the snapshot already contained
  an active child (PENDING or RUNNING), the command REPORTS it (id,
  state, recorded operator, `created_at`/`started_at`) and exits — no
  claim, no execution, no INSERT, zero network calls.
- Post-commit, the invocation executes exactly one Vendor lookup for its
  own RUNNING child and alone proceeds to complete/fail through its own
  call stack (M2).
- **Process crash before INSERT:** nothing committed (the combined
  transaction rolls back; the lock statement is a zero-row no-op —
  verified §1.6/Appendix A). No orphan.
- **Crash after INSERT but before claim:** IMPOSSIBLE on the R1 command
  path — INSERT and claim commit atomically in the one transaction. A
  PENDING row on the command path never reaches durability on its own.
- **Crash after claim (i.e. after the combined commit) but before the
  Vendor call:** RUNNING orphan, ZERO external requests. Resolved by M1
  (uniform `EXECUTION_INTERRUPTED`; the row semantics are
  "outcome UNKNOWN" even though this window made no request — the row
  cannot encode which crash window applies, and the conservative uniform
  semantics is the honest one; display must not assert either direction).
- **Crash during the Vendor call:** RUNNING orphan, ≤1 request in flight,
  outcome unknown. M1.
- **Crash after the Vendor response but before complete:** RUNNING orphan,
  request completed externally, result lost. M1. A later refresh (new
  child, after recovery) is a new timestamped evidence point; nothing is
  rewritten.
- **Existing PENDING encountered by another operator:** reported (id,
  state, recorded operator, `created_at`), left untouched, no new row,
  zero calls. This is the honest, safe response to the orphan-PENDING
  case.
- **What the stored `operator` truthfully means under Option A:** the
  self-reported TRIGGER initiator (frozen meaning) — AND, on the command
  path, also the executor, because only the creating invocation claims and
  executes. The field therefore never lies about trigger provenance and,
  for command-created rows, coincides with execution provenance. No row
  exists on the command path whose executor differs from its recorded
  operator.
- **How the later executor is identified, if applicable:** there is no
  later executor on the command path. If a PENDING row exists (created
  only by a non-command surface — programmatic trigger, future R3), no R1
  invocation executes it; its eventual executor, if any, must come from a
  separately approved mechanism (future gate; the R3 web surface must
  bring 8C identity + its own provenance handling per frozen DESIGN2
  §12.2 M6).
- **Orphaned PENDING (non-command trigger; creator died before any claim):**
  possible ONLY via a non-command `trigger_vendor_refresh` call. It made
  ZERO Vendor calls and carries NO unknown external outcome (frozen
  DESIGN2 §4.6 option 1 consequence). It occupies the active slot, so it
  blocks new refreshes for that parent — the safe direction. R1
  treatment: **reported on every subsequent command invocation; never
  claimed, executed, or terminalized by R1.** Its resolution is [OPEN-O3]:
  (i) leave as a permanent reported HOLD (no schema change; the operator
  audit records it; the parent's refresh stays blocked until a future
  approved gate), (ii) a future gate approves a narrow "abandon orphan
  PENDING" procedure (claim PENDING→RUNNING via the R0 primitive, then
  fail with a NEWLY reserved reason — which requires a vocabulary + CHECK
  change, i.e. a schema change, hence its own approval), or (iii) the R3
  identity/provenance mechanism makes later execution truthful. R1
  implements none of these; Option A + report-only is the R1 behavior.

**Option B — a later invocation may execute an existing PENDING child
with separately truthful execution provenance** [PROPOSED — analyzed, NOT
recommended]:

- The comparable-research web view is the existing precedent for this
  shape (trigger-then-synchronous-execute, same request; a later request
  over a PENDING child would execute it too) [VERIFIED
  `web/views.py` L1032–1094].
- For the row to be truthfully readable, the executor's identity must be
  recorded on the row → a NEW model field (e.g. claim-executor) → a schema
  change. The task bar ("do not create a new model field without proving
  why the existing schema and bounded operational audit cannot meet the
  requirement") is NOT met: on the single-host command surface, Option A
  makes creator==executor for every executed row, so the existing
  `operator` field plus the bounded stdout plus the host operational
  audit (mandatory R1 deployment prerequisite, frozen DESIGN2 §4.5)
  already carry truthful execution provenance for everything R1 can
  execute. A field would encode information the row never needs to be
  true, for a surface (later-executor) that Option A removes.
- Alternatively, Option B with stdout-only executor provenance (no field):
  the record is not bound to the row, is lost if the operator does not
  redirect stdout, and cannot be read by the R2 history display — a
  weaker truthfulness story with none of Option A's simplicity.
- Trade accepted by NOT choosing B: orphaned PENDING (non-command
  surface only, zero external outcome) is a reported HOLD in R1 instead of
  an executable row.

**Decision [PROPOSED]: Option A.** It matches frozen DESIGN2 §4.6 option
1, needs no schema change, makes the `operator` field simultaneously
trigger- and execution-truthful on the command path, and confines the
orphan case to the non-command surface where it is inert (zero calls).

### 3.4 M4 — Five-minute repeat safeguard under SQLite concurrency

**Frozen business rule** [VERIFIED DESIGN2 §5.2/D6(b)]: a new explicit
post-terminal refresh within five minutes of the latest terminal attempt
requires `--force-repeat`; the safeguard runs BEFORE a new child is
persisted and BEFORE any Vendor API call; a refusal creates zero children
and makes zero network calls; `UNIQUE(parent_run, active_slot)` + the
claim CAS remain intact; no general rate limiter is invented; concurrent
invocations are "reviewed separately at R1" — reviewed here.

**Verified deployment facts** [VERIFIED §1.6]: file SQLite, default
rollback journal (no WAL), no Django `OPTIONS`, busy timeout = Python
`sqlite3` default 5.0 s; `select_for_update()` is a no-op on SQLite
(repository's own statement, `runs/ai_assisted_review.py` L254); a
zero-row write statement inside a transaction acquires the RESERVED lock
and serializes all other writers behind it; readers are not blocked; a
killed lock holder releases the lock and rolls back.

**Alternatives** [PROPOSED]:

- *A1 — display-based check only (check, then trigger outside any shared
  lock):* two invocations can both pass the check before either persists
  (frozen DESIGN2 §13 names this exact race). Rejected as the sole
  mechanism.
- *A2 — a dedicated cooldown row/table or new model field (e.g.
  `last_terminal_at` on the parent, or a guard table):* schema change for
  an operator-safety check on a single-host command surface; the existing
  rows already carry the full terminal history; rejected (§2.2 no-schema
  rule).
- *A3 — advisory write-lock transaction (RECOMMENDED):* wrap the
  authoritative decision + INSERT + claim in ONE short
  `transaction.atomic()` whose FIRST statement is a zero-row write on
  `runs_vendorrefreshexecution` —
  `VendorRefreshExecution.objects.filter(parent_run_id=<P>,
  active_slot=2).update(active_slot=2)` — which the CHECK constraint
  (`active_slot ∈ {1, NULL}`) guarantees can match zero rows, so it
  mutates NOTHING, while SQLite semantics grant the executing transaction
  the file RESERVED lock. Every other writer on the database file (any R1
  command, any programmatic trigger/claim/complete/fail, any Waitress
  write) serializes behind it. The transaction then: reads the
  authoritative state (active children; latest terminal child's
  `finished_at`), makes the safeguard decision, and — only if allowed —
  calls `trigger_vendor_refresh` (INSERT) and `claim_vendor_refresh`
  (PENDING→RUNNING) in the same transaction. COMMIT precedes the Vendor
  HTTP call. No network, no sleeps, no I/O of any kind inside — the
  transaction is milliseconds [PROPOSED; lock behavior VERIFIED §1.6].
- *A4 — `BEGIN IMMEDIATE` via raw SQL:* achieves the same lock but
  bypasses Django's transaction management (Django does not expose the
  transaction mode through `transaction.atomic()`; raw `BEGIN` inside
  Django is fragile and unaudited). Rejected in favor of A3, which is
  pure ORM.

**Recommended: A3.** Exact command flow [PROPOSED]:

```
python manage.py vendor_refresh <parent-run-uuid> --operator <id> [--force-repeat]

 0. Argument validation (run UUID parse — bounded 404-style refusal;
    --operator mandatory, 1..128 verbatim; --force-repeat boolean).
    Zero DB access.
 1. Informational display read (outside any write transaction): active
    child + latest terminal child for the parent; print bounded state
    lines. (May be stale by the time of step 2 — the decision below is
    authoritative, this is human information only.)
 2. with transaction.atomic():                       # SHORT write txn
      a. LOCK: VendorRefreshExecution.objects
             .filter(parent_run_id=P, active_slot=2)
             .update(active_slot=2)   # zero-row; takes RESERVED lock
      b. Read active children for P (fresh, under lock).
         If any: exit txn -> report IN PROGRESS (state, id, operator,
         created_at/started_at); NO INSERT; NO claim; NO call; exit 0.
      c. Read latest terminal child for P (fresh, under lock):
         max(finished_at), tie-break id DESC.
         If it exists AND (now - finished_at) < 300s AND NOT --force-repeat:
             exit txn -> report COOLDOWN REFUSAL (child id, finished_at,
             age); NO INSERT; NO call; exit 0.
      d. child = trigger_vendor_refresh(P, operator=op)
         (INSERT PENDING; the UNIQUE constraint remains the hard invariant
         for any writer that does not take the lock)
      e. created = (child was not present in the step-b snapshot)   #
         ownership proof under the lock (§3.3)
      f. if created: claim_vendor_refresh(child.id)  # PENDING->RUNNING,
                                                      # same transaction
    COMMIT -> the child is durably RUNNING (command path: no PENDING is
    ever committed alone), BEFORE any network activity.
 3. Post-commit execution (NO open transaction):
      load parent; re-check parent COMPLETED (defensive) and
      child.requested_mpn == parent.manufacturer_part_number
      (else fail MPN_BINDING_VIOLATION, zero calls);
      env check PI_VENDOR_LOOKUP_BASE_URL absent/blank
      (else fail VENDOR_LOOKUP_CONFIG_MISSING, zero calls);
      query = CommercialLookupQuery(mpn=child.requested_mpn);
      if query.mpn != child.requested_mpn:
          fail MPN_QUERY_NORMALIZATION_MISMATCH, ZERO calls (frozen C7);
      adapter = injected-or-lazy InternalVendorAdapter();
      response = adapter.lookup(query)        # THE single network call;
                                              # outside any transaction
      encoded = bind_and_encode_vendor_lookup(child.requested_mpn,
                                              response)   # shared D10 helper
      complete_vendor_refresh(child.id, 1, encoded)
   (any bounded post-claim defect -> fail_vendor_refresh(bounded reason);
    see §10 expected behaviors)
```

**Ownership proof under the lock** [PROPOSED, derived from verified
semantics]: while the command holds the RESERVED lock, no other writer can
commit an INSERT/UPDATE on the file. Therefore: if snapshot (b) shows no
active child and the trigger's INSERT (d) succeeds, THIS invocation
created the row — deterministic, no clock, no return-value ambiguity (the
frozen trigger contract carries no ownership flag, §3.3). If snapshot (b)
shows an active child, the command reports and exits — it never claims a
child it did not create (Option A). The INSERT's own IntegrityError race
path (R0) remains as defense in depth for writers that skip the lock
(programmatic triggers): such a writer's INSERT serializes behind the
lock statement too (an INSERT is a write), so in practice the race path
is unreachable from the command; the R0 behavior is simply preserved.

**Combined trigger+claim transaction — the task's specific question**
[PROPOSED]: YES, trigger and claim are safely combined in one short
database transaction committed BEFORE the external Vendor request:

- Both are single statements (INSERT; conditional UPDATE); no network, no
  locks of any kind other than the file write lock; total duration is
  milliseconds.
- The committed shapes are all legal R0 lifecycle shapes: the transaction
  either commits nothing or commits a RUNNING child (PENDING is an
  intermediate state inside the transaction, never durable on the command
  path). The R0 primitives are called unmodified; the composition is in
  the command.
- It AVOIDS creation of orphaned PENDING rows for normal R1 command
  invocations: crash before commit ⇒ no row (verified rollback §1.6);
  crash after commit ⇒ RUNNING (resolved by M1). Orphaned PENDING remains
  possible only via non-command triggers (§3.3).
- It does NOT weaken anything frozen: `UNIQUE(parent_run, active_slot)`
  still bounds any writer; the claim CAS still guarantees single-winner
  even for a child created outside the lock; DESIGN2 §3.6's crash table
  remains valid (the "claim" row's crash consequence is now unreachable on
  the command path — a strict improvement, not a contradiction).

**Cooldown definition** [PROPOSED]: window = 300 seconds; reference = the
latest terminal child's `finished_at` for this parent (max, tie-break
`id` DESC — deterministic, no `now()` dependence in the ordering);
comparison is STRICT: `now - finished_at < 300s` ⇒ refusal without
`--force-repeat`; `>= 300s` ⇒ allowed. `now` = `timezone.now()` sampled
inside the transaction (single host, single clock). `--force-repeat`
bypasses the cooldown refusal ONLY — it does not bypass the in-progress
report (an active child still blocks a new child) and it records
nothing on the row (no field exists; the bounded stdout and host audit
carry it — [OPEN-O5] whether a row-level force record is ever wanted;
that would be a schema change and is NOT proposed).

**Precise guarantee** [PROPOSED]: the safeguard is ATOMIC with respect to
every writer that takes the file write lock — in particular, no two R1
command invocations can both pass the cooldown check and both create a
child, and no invocation can create a child while a terminal attempt it
would have seen is mid-commit; a refusal commits nothing and calls
nothing. It is NOT a server-enforced rate limit: a writer that does not
take the lock statement (a bare programmatic `trigger_vendor_refresh`
call, a future R3 web surface, raw SQL) is not subject to the five-minute
window; the hard invariants (`UNIQUE(parent_run, active_slot)`: at most
one active child per parent; claim CAS: at most one claim and therefore
at most one Vendor call per child) still bound every writer. This is
stated exactly, per frozen D6: an operator-safety check on the command
surface, clearly distinct from a rate limit.

**Residual risks (enumerated, not hidden)** [PROPOSED]:
(a) a >5 s lock holder surfaces as bounded `OperationalError: database
is locked` on the waiting command (zero mutation, non-zero exit, manual
re-run) instead of a delayed success — practically unreachable (command
transactions hold no I/O; Waitress write transactions are short) but
real; (b) host clock regression can shorten or lengthen the observed
window for subsequent invocations — acceptable for an operator-safety
check on a single host, noted; (c) non-command writers bypass the window
(by design — D6(c) defers real rate limiting to R3/8C).

---

## 4. State transitions and lifecycle invariants

### 4.1 R1 state-transition table [PROPOSED]

Rows 1–9 are the FROZEN R0 table (DESIGN2 §3.3) reproduced unchanged.
Row 10 is the single R1 addition. No state, no reason, no column, and no
constraint changes.

| # | Transition | Primitive (module) | CAS precondition (WHERE of the single UPDATE) | Effect | Phase |
|---|---|---|---|---|---|
| 1 | (no row) → PENDING | `trigger_vendor_refresh` (runs/vendor_refresh_claims.py L134) | parent eligible + no active child (`UNIQUE(parent_run, active_slot)`) | INSERT PENDING, active_slot=1, verbatim `requested_mpn`, `operator`, `trigger_source`, `created_at` | R0 frozen |
| 2 | PENDING → RUNNING | `claim_vendor_refresh` (L327) | state=PENDING, active_slot=1, started_at IS NULL | state=RUNNING, started_at set | R0 frozen |
| 3 | RUNNING → COMPLETED | `complete_vendor_refresh` (L381) | state=RUNNING, active_slot=1, finished_at IS NULL (+ bounded V1 version agreement pre-check) | state=COMPLETED, active_slot=NULL, finished_at, result_schema_version=1, result_payload — ONE UPDATE | R0 frozen |
| 4 | RUNNING → FAILED | `fail_vendor_refresh` (L518) | state=RUNNING, active_slot=1, finished_at IS NULL (+ bounded reason pre-check, reserved value REJECTED) | state=FAILED, active_slot=NULL, finished_at, failure_reason ∈ R0_LEGAL — ONE UPDATE | R0 frozen |
| 5 | PENDING → terminal (skip RUNNING) | — | — | — | FORBIDDEN (R0 row 5) |
| 6 | RUNNING → PENDING | — | — | — | FORBIDDEN (R0 row 6) |
| 7 | RUNNING → RUNNING (reassignment) | — | — | — | FORBIDDEN (R0 row 7) |
| 8 | COMPLETED/FAILED → any | — | — | — | FORBIDDEN (R0 row 8) |
| 9 | RUNNING → terminal by recovery (stale reclaim / threshold / auto-retry / operator-forced interruption via the R0 fail service) | — | — | — | FORBIDDEN (R0 row 9; F1) |
| 10 | RUNNING → FAILED (`EXECUTION_INTERRUPTED`) | `manual_terminalize_vendor_refresh_execution` (NEW runs/vendor_refresh_manual_terminalization.py) — operator-gated, evidence per §3.1 | state=RUNNING, active_slot=1, finished_at IS NULL | state=FAILED, active_slot=NULL, finished_at set, failure_reason=EXECUTION_INTERRUPTED — ONE UPDATE; identity fields untouched; external Vendor outcome remains explicitly UNKNOWN | **R1 ONLY** — the sole sanctioned writer of the reserved reason |

Row 10 is a row-4-shaped transition with the reserved reason, issued by a
separate primitive, under a separate command, with a separate operator
evidence precondition. It is not a modification of row 4, not an exception
to row 9 (row 9 forbids recovery-based terminalization IN R0 and
threshold/reclaim-based terminalization in any phase — row 10 is
manual, evidence-gated, non-threshold, and frozen-DESIGN2-sanctioned as
the "separately approved future R1 recovery transition"), and it is the
only additional legal RUNNING→terminal path in R1.

### 4.2 Lifecycle invariants [PROPOSED]

- **I1** — At most one active (PENDING/RUNNING) child per parent run.
  [Frozen R0; `UNIQUE(parent_run, active_slot)`; holds for ANY writer.]
- **I2** — At most one claim winner per child. [Frozen R0; row-2 CAS.]
- **I3** — At most one terminal write per child; a duplicate or
  cross-terminal attempt affects 0 rows, raises bounded, mutates
  nothing. [Frozen R0; rows 3–4 CAS + row-10 CAS.]
- **I4** — At most one `InternalVendorAdapter.lookup()` per child, ever;
  the call site is reachable only after a successful claim in the
  claim winner's own call stack; losers, ineligible triggers, and
  config-missing/normalization-mismatch cases make zero calls. [R1
  application-level structure + frozen adapter one-call policy.]
- **I5** — On the R1 command path, a child is first durably observed in
  the RUNNING shape (combined trigger+claim transaction); a PENDING row
  committed alone can only come from a non-command trigger. [R1, §3.4.]
- **I6** — On the R1 command path, the executor of a child is the
  invocation that created it; the row's `operator` is therefore both the
  self-reported trigger initiator and (for command-created rows) the
  executor. [R1, §3.3 Option A.]
- **I7** — The parent `ResearchRun` and every original persisted artifact
  (`PriceIntelligenceSnapshot`, original `ResearchSupplementSnapshot`,
  `ResearchFxSnapshot`, `ResearchMicronAliasSnapshot`,
  `ExecutionEvidenceRecord`s, `AiAssistedReviewCandidate`s,
  `ComparableResearchExecution`s) are byte-identical before and after any
  R1 operation. [Frozen DESIGN2 §9 invariant; extended to R1.]
- **I8** — An `EXECUTION_INTERRUPTED` row means: execution interrupted;
  external Vendor outcome explicitly UNKNOWN. It is never displayed or
  interpreted as a failed lookup, and never as success; it carries no
  payload (FAILED shape: result fields NULL). [R1 + frozen F1 semantics.]
- **I9** — The row-10 transition writes exactly `state`, `active_slot`,
  `finished_at`, `failure_reason` on the target RUNNING row; no other
  field of any row is modified; prior refresh rows and all parent
  artifacts are untouched. [R1.]
- **I10** — No network call occurs inside any database transaction. [R1;
  the Vendor call is strictly post-commit (§3.4 step 3).]
- **I11** — No R1 surface reclaims, resets, retries, reassigns, or
  resurrects any child; no `--reclaim-stale`-style flag exists; the only
  repeat affordance is `--force-repeat` (cooldown bypass, creates a NEW
  child only when allowed). [R1; frozen D3(b)/D6.]
- **I12** — The runs-layer public API contains exactly the four R0
  vendor-refresh primitives plus the ONE R1 recovery primitive (and their
  bounded errors); the `vendor_refresh_claims.py` module surface stays
  exactly four functions. [R1, pinned by §12.]

---

## 5. Trigger / claim / execute ownership sequence

The complete R1 normal-path sequence with ownership annotations
[PROPOSED]:

```
INVOCATION = one `python manage.py vendor_refresh <P> --operator <op> [--force-repeat]`
process on the deployment host (authorization: Windows host access,
frozen DESIGN2 §4.2; `op`: self-reported provenance, verbatim).

[S0] parse/validate args                          (no DB, no network)
[S1] informational display read                    (read-only; may be stale)
[S2] BEGIN short write transaction
     [L]  zero-row lock statement                  (acquires RESERVED lock; 0 mutations)
     [R1'] active-children snapshot under lock
     [D1] active child present?  -> IN PROGRESS report, ABORT (no INSERT)
     [R2'] latest-terminal read under lock
     [D2] within 300 s and not --force-repeat? -> COOLDOWN REFUSAL, ABORT (no INSERT)
     [T]  trigger_vendor_refresh(P, operator=op)   (INSERT PENDING; savepoint race path preserved)
     [O]  ownership: returned child not in [R1'] -> THIS invocation created it
     [C]  claim_vendor_refresh(child.id)           (PENDING->RUNNING, same txn)
[S3] COMMIT                                        (row durably RUNNING; before ANY network)
[S4] load parent; re-check COMPLETED + requested_mpn == parent MPN
     (violation -> fail MPN_BINDING_VIOLATION, 0 calls)
[S5] env PI_VENDOR_LOOKUP_BASE_URL check
     (absent/blank -> fail VENDOR_LOOKUP_CONFIG_MISSING, 0 calls)
[S6] query = CommercialLookupQuery(mpn=child.requested_mpn)
     query.mpn != child.requested_mpn -> fail MPN_QUERY_NORMALIZATION_MISMATCH, 0 calls
[S7] adapter = injected or lazy InternalVendorAdapter()
     response = adapter.lookup(query)              (THE single network call; no open txn)
[S8] encoded = bind_and_encode_vendor_lookup(child.requested_mpn, response)  (D10 helper)
[S9] complete_vendor_refresh(child.id, 1, encoded) (single UPDATE)
     -> bounded stdout: COMPLETED (lookup_status=...); exit 0

POST-CLAIM FAILURE PATH (S4..S9 defect):
     bounded reason r in {MPN_BINDING_VIOLATION, VENDOR_LOOKUP_CONFIG_MISSING,
                          MPN_QUERY_NORMALIZATION_MISMATCH, RESULT_ENCODING_FAILED,
                          INTERNAL_ERROR}
     -> fail_vendor_refresh(child.id, r)  (single UPDATE)
     -> raise VendorRefreshExecutionError (bounded)
     -> command stdout: FAILED (reason=r); exit 0 (bounded outcome)
     -> if the fail itself cannot persist (DB error): propagate; stdout:
        "terminalization NOT recorded; child remains RUNNING; recovery gate
        reference"; non-zero exit. Child stays RUNNING (I3/I9 intact).

RECOVERY PATH (separate gated command, §3.1):
     operator evidence (E-REBOOT | E-SCAN | E-KILL) established OUTSIDE the DB
     -> vendor_refresh_manual_terminalization <child> --operator <op> --evidence <class>
     -> single CAS UPDATE (row 10) -> bounded stdout -> exit 0
     (a later refresh of P is a NEW child [T..S9]; the recovered child is
     never resumed or reused for a second Vendor call — I4/I9/I11.)
```

Ownership summary: exactly ONE invocation can execute one child (the
creator, under I5/I6); the claim CAS makes that true even for races the
lock does not serialize (defense in depth); complete/fail are issued only
by that invocation's stack; the only other legal terminalizer is the
evidence-gated recovery primitive, which writes the reserved reason and
never a result.

---

## 6. Transaction boundaries

| Unit | Contents (statements) | Network? | Max duration class | Failure behavior |
|---|---|---|---|---|
| Command serialized txn (S2–S3) | lock stmt (0-row UPDATE); active-children SELECT; latest-terminal SELECT; INSERT (trigger, own savepoint); claim UPDATE | NO | milliseconds | any error before COMMIT → full rollback → zero mutation (verified §1.6); `OperationalError: database is locked` at the lock stmt if contention > busy timeout (5 s) → bounded, non-zero exit, zero mutation |
| Config/binding/normalization checks (S4–S6) | parent SELECT; env read; in-memory string compare | NO | trivial | → bounded fail UPDATE (below) |
| Vendor call (S7) | ONE GET (frozen adapter policy: 10 s socket timeout, 1 MiB bound, no retries) | YES — outside every transaction | ≤ ~10 s + scheduling | transport failure → bounded FAILED RESPONSE (not exception) → normal completion with lookup_status=FAILED |
| Binding/encode (S8) | in-memory | NO | trivial | codec error → RESULT_ENCODING_FAILED fail path |
| complete (S9) | single UPDATE | NO | trivial | 0 rows → bounded error, zero mutation; DB error → propagate, child stays RUNNING |
| fail (any) | single UPDATE | NO | trivial | same as complete |
| Recovery CAS (row 10) | single UPDATE | NO | trivial | 0 rows → re-read → bounded report (actual terminal shape), zero mutation |

No statement of any R1 path holds a transaction open across S7. [PROPOSED
invariant I10; mirrors frozen 4C-B "call the provider outside
transactions" and DESIGN2 §3.6.]

---

## 7. Crash and recovery decision matrix

Legend: `W` = window; `row` = durable child shape after the event;
`API` = Vendor calls made by that attempt; `resolution` = who/what
legally acts next. All windows assume the R1 command path (combined
txn); non-command trigger windows noted where different.

| W | Event | Row after | API | Parent/original artifacts | Resolution |
|---|---|---|---|---|---|
| W1 | crash inside serialized txn (lock stmt / INSERT / claim), before COMMIT | NO ROW (rollback) | 0 | untouched (I7) | nothing to do; next invocation is normal |
| W2 | crash after COMMIT (S3), before S4 (config/binding checks) | RUNNING | 0 | untouched | M1 gate (evidence) → row 10 → new attempt later. (Uniform UNKNOWN semantics, §3.3.) |
| W3 | crash during S4–S6 checks (post-claim, pre-call; checks would have failed) | RUNNING (if crash before the fail UPDATE commits) | 0 | untouched | M1 gate as W2. (If the fail UPDATE committed first: FAILED bounded reason; no crash state.) |
| W4 | crash during the Vendor call (S7) | RUNNING | ≤1 in flight, outcome unknown | untouched | M1 gate (evidence) → row 10. External outcome stays UNKNOWN; a later NEW attempt is new evidence, never a rewrite. |
| W5 | crash after response received, before encode/complete (S8/S9) | RUNNING | 1 completed externally, result lost | untouched | M1 gate as W4. |
| W6 | crash during the complete UPDATE commit | COMPLETED (durable) if commit won, else RUNNING (rollback) | 1 | untouched | COMPLETED: done. RUNNING: M1 gate. |
| W7 | crash during the fail UPDATE commit | FAILED if commit won, else RUNNING | ≤1 | untouched | FAILED: done. RUNNING: M1 gate. |
| W8 | DB failure during S9/S-fail (not a crash) | RUNNING (UPDATE did not commit) | 1 | untouched | command prints "terminalization NOT recorded"; M1 gate later. (Frozen DESIGN2 §9 row 8 shape.) |
| W9 | crash of the RECOVERY command during its CAS | FAILED(row 10) if commit won, else RUNNING | (original attempt's) unknown | untouched | re-run recovery after fresh evidence, or original-execution completion wins the race (row 10 reports it, no mutation). |
| W10 | (non-command trigger only) crash after PENDING INSERT, before any claim | PENDING | 0 | untouched | reported IN PROGRESS/PENDING by every command; never executed/terminalized by R1; resolution [OPEN-O3]. Safe: zero external outcome. |
| W11 | recovery race: original process completes (row 3) concurrently with recovery CAS (row 10) | exactly one terminal write; the other affects 0 rows | 1 | untouched | loser re-reads and reports the ACTUAL terminal shape; interruption is never recorded over a real result (I3). |

Invariants across all windows: I1–I12 hold; a crashed attempt can never
produce a second Vendor call (I4); no window rewrites any historical row
(I7/I9); a RUNNING row always blocks new attempts for its parent (safe
direction) until row 3, row 4, or evidence-gated row 10 terminalizes it.

---

## 8. Operator authorization and provenance

### 8.1 Authorization (frozen DESIGN2 §4, restated for R1) [PROPOSED]

- The mutation authorization boundary for BOTH R1 commands is controlled
  **Windows host access** on the deployment host (account,
  executable/deployment access, database-file ACLs, runbook operational
  controls) — the same boundary frozen for the `migrate` / `pilot_check`
  operations [VERIFIED runbook]. No Django authentication, no session, no
  user model, no new URL, no new POST surface (8C remains the formal
  authentication phase; R3 web trigger stays deferred).
- **Deployment prerequisite (frozen, blocking for DEPLOYMENT only):**
  the explicit host permissions and operational audit review (host/CMD
  account inventory, command-logging posture, database file + directory
  ACLs, runbook controls) must be completed and recorded before R1
  deploys. [OPEN-O8 tracks it.]
- `--operator` (mandatory, 1..128, verbatim, content-free errors) is
  **self-reported provenance, NOT authentication** (frozen D4(b)). Shared
  administrative accounts reduce attribution; `--operator` mitigates,
  never solves. No OS environment value (`USERNAME` etc.) is trusted or
  recorded (frozen: no OS-context column).
- The recovery command additionally carries the bounded `--evidence`
  token (§3.1) so the operator's termination attestation class appears
  in the command line and the bounded stdout for the host audit.

### 8.2 What the stored row truthfully says (R1) [PROPOSED]

- `operator` = self-reported identity of the actor who TRIGGERED the
  refresh (frozen meaning, unchanged). On the R1 command path, I6 makes
  that actor also the executor for every EXECUTED child; the field is
  simultaneously trigger-truthful and execution-truthful there.
- `trigger_source` = `MANAGEMENT_COMMAND` for both R1 commands' children
  (the vocabulary member is unchanged; the recovery command does not
  create children).
- `started_at` = claim instant (= creation instant on the command path,
  same commit).
- `finished_at` + `failure_reason=EXECUTION_INTERRUPTED` = evidence-gated
  manual terminalization; semantics frozen (I8): outcome UNKNOWN.
- Execution-provenance beyond the row (evidence class, check time,
  invocations) lives in the bounded stdout and the host operational
  audit — NOT in the schema (frozen no-new-field default; §3.3).

### 8.3 Bounded stdout contract (both commands) [PROPOSED]

Always bounded; no secrets; no raw exception text; no raw private Vendor
response content; no base URL. Per-child lines carry: child id, parent
run id, state, recorded operator, relevant timestamps, bounded reason /
lookup_status vocabulary values, and the command's own outcome class
(CREATED+EXECUTED / IN PROGRESS / COOLDOWN REFUSAL / CLAIM LOST /
COMPLETED / FAILED / TERMINALIZATION NOT RECORDED / DATABASE BUSY /
ALREADY TERMINAL / HOLD). The MPN (bound identity) is displayed — it is
already public on the report page and stored on the row. Exit codes:
0 for bounded outcomes (success, in-progress, cooldown refusal, claim
lost, already-terminal); non-zero for ineligibility (bad UUID, missing
operator, parent ineligible) and unexpected errors (DB busy/locked,
programming error, terminalization-not-recorded). This mirrors the frozen
DESIGN2 §10.3(5) exit-code contract and the `pilot_check` precedent.

---

## 9. SQLite race / interleaving analysis (task §6 cases)

All cases analyzed against the §3.4 flow (serialized txn A3) and the
VERIFIED semantics of §1.6. "Cmd" = an R1 command invocation.

1. **Two simultaneous invocations, no child exists.**
   Cmd-A acquires the RESERVED lock at its zero-row statement; Cmd-B
   blocks there (busy-wait ≤ 5 s). A: snapshot empty → no cooldown
   blocker → INSERT+claim → COMMIT (child RUNNING). B: lock released,
   B's statement runs (0 rows), B's fresh snapshot sees A's RUNNING
   child → IN PROGRESS report → no INSERT → zero calls.
   **Result: exactly one child, at most one Vendor call. Closed.**
2. **Second invocation while the first is PENDING.**
   On the command path a PENDING row is never committed alone (I5) — a
   PENDING child seen by a second Cmd came from a non-command trigger.
   Second Cmd: snapshot under lock sees the active (PENDING) child →
   IN PROGRESS report (identifies id, recorded operator, created_at) →
   no claim, no execution, no INSERT, zero calls. Option A: the orphan
   is never silently executed (§3.3). **Closed (honest report).**
3. **Second invocation while the first is RUNNING.**
   Same as case 2: snapshot under lock sees the active RUNNING child →
   IN PROGRESS report → zero calls. The RUNNING row keeps occupying the
   slot (frozen rule). **Closed.**
4. **First attempt completes between the second invocation's cooldown
   check and its attempt to insert.**
   The second's check and INSERT are in ONE serialized transaction: no
   writer can commit "between" them. Sub-cases: (a) at the second's
   in-lock snapshot the first's child is still RUNNING → active child →
   IN PROGRESS, no INSERT at all; (b) the first's complete committed
   before the second acquired the lock → the second's fresh read sees
   the new terminal child within 300 s → COOLDOWN REFUSAL (without
   `--force-repeat`) → no INSERT; (c) the first's complete commits after
   the second's commit → the second's decision was made against a fully
   committed state (first was RUNNING/absent-terminal then) → the second
   legitimately created a new child; the later first-completion cannot
   retroactively invalidate it (different rows; append-only). **Closed —
   the decision always reads the latest committed state.**
5. **Two invocations both observe terminal history outside the cooldown
   window.**
   Both pass the cooldown, but only ONE can INSERT: Cmd-A commits its
   child (RUNNING) under the lock; Cmd-B blocks, then sees the active
   child → IN PROGRESS → no second INSERT. **Result: exactly one new
   child. The 5-minute rule governs post-terminal spacing; the
   active-slot invariant governs duplication — both hold. Closed.**
6. **`--force-repeat` competing with a non-forced invocation.**
   Serialized: whichever holds the lock first decides. If force goes
   first: it INSERTs+claims (cooldown bypassed in ITS fresh read); the
   non-forced then sees the active child → IN PROGRESS (it never reaches
   a cooldown decision about a child it did not create). If non-forced
   goes first while a terminal <300 s exists: it REFUSES (no INSERT);
   force then passes its own fresh read (bypass) → INSERTs. **At most
   one new child per pair; the force flag is honored exactly once and
   never "eaten" by the race. Closed.**
7. **SQLite busy/locked error while acquiring the serialization
   mechanism.**
   If the lock holder exceeds the 5.0 s busy timeout (VERIFIED P5:
   `OperationalError: database is locked`), the waiting command: its
   transaction never committed → **zero mutation** (the lock statement
   changed 0 rows by construction) → bounded "DATABASE BUSY — no state
   changed — re-run" → non-zero exit → NO automatic retry (frozen
   no-retry stance; a manual re-run is a new explicit invocation). A
   >5 s holder is practically unreachable on this deployment (command
   txns are milliseconds with no I/O; the only other writers are short
   Waitress web transactions and manual operations) — noted as residual
   (a), §3.4. **Bounded. Closed.**
8. **A new terminal child appearing during the decision.**
   The decision reads under the write lock: a terminal child can only
   become visible "during" the decision if it committed BEFORE the
   decision's transaction acquired the lock (→ it IS in the fresh read —
   the decision accounts for it) or AFTER this transaction commits (→
   this decision was correct against the committed state at decision
   time; the later terminalization of a DIFFERENT child cannot retroact
   on it, and the later child's own 5-minute consequence is evaluated by
   the NEXT invocation). A non-command writer terminalizing some RUNNING
   child during the wait is equally ordered by the lock. **Closed — no
   stale-decision window exists for writers that take the file lock;
   non-locking writers are bounded by I1–I4 (residual (c), §3.4).**
9. **Abrupt process termination while the short transaction holds
   database locks.**
   VERIFIED (P4): process death releases the file locks at the OS level;
   the uncommitted transaction (lock stmt + any INSERT/claim) is rolled
   back by journal recovery on the next connection; no partial row; the
   zero-row lock statement mutated nothing. A terminated Cmd-1 leaves
   either NO row (crash before commit) or a RUNNING row (crash after
   commit) — exactly W1/W2 of §7. A second invocation proceeds without
   waiting (lock is free). **Closed; no wedge, no corruption.**

Additional interleavings (not in the mandated list, analyzed for
completeness):

- **A. Cmd + programmatic trigger racing (no lock-taker on the programmatic
  side):** the programmatic INSERT is a write — it serializes behind the
  Cmd's RESERVED lock; after the Cmd commits (child RUNNING), the
  programmatic trigger's own pre-check finds the active child (concept 1
  return) or its INSERT hits `UNIQUE` → winner returned. At most one
  active child (I1). **Bounded.**
- **B. Two programmatic `execute_vendor_refresh(child)` calls on the same
  PENDING child (non-command surface):** claim CAS → one winner, one
  call; loser bounded, zero calls (I2/I4). **Bounded (M2 guarantee).**
- **C. Waitress web write (e.g. a research POST atomic publication)
  concurrent with a Cmd:** both are ordinary writers; they serialize on
  the file lock; the Cmd's txn is milliseconds; the web txn is the
  existing short atomic publication; each may hit the 5 s busy bound in
  the pathological case (bounded error on both sides, rollback, retry by
  the user/operator). No R1-specific risk beyond existing deployment
  behavior. **Bounded.**
- **D. Backup runbook (`copy db.sqlite3` with app stopped) concurrent
  with a Cmd:** the runbook requires the application stopped for backups;
  a Cmd running against a copied/stopped database is operator error —
  out of mechanism scope; noted for the operational audit review (O8).

**Aggregate guarantee (restated):** on the R1 command surface, the
serialized transaction makes the safeguard decision, child creation, and
claim acquisition atomic with respect to all file-lock-taking writers;
the frozen hard invariants (I1–I4) bound every writer including
non-locking ones; refusals and reports commit nothing and call nothing.

---

## 10. Provider boundary and helper extraction map

### 10.1 Module map [PROPOSED]

| Module (path) | Content | Import allowlist (pinned by new AST guards, §12) |
|---|---|---|
| `product_intelligence/execution/vendor_refresh.py` (NEW) | `execute_vendor_refresh(child_id, *, vendor_adapter=None) -> VendorRefreshExecution`; `VendorRefreshExecutionError` (bounded, execution-layer, mirrors `ComparableResearchExecutionError` L116); single outer post-claim boundary (bounded defect → `fail_vendor_refresh(reason)` + raise; DB-unrecordable fail → propagate + row stays RUNNING) | `product_intelligence.runs` public symbols (claim/complete/fail triggers + bounded errors + model/vocabularies); `product_intelligence.execution.vendor_commercial_binding` (the D10 helper); `product_intelligence.providers.commercial` (`CommercialLookupQuery`, `LookupStatus`); `os` (env read of `PI_VENDOR_LOOKUP_BASE_URL`); stdlib. Function-level lazy import of `InternalVendorAdapter` (default construction, mirroring 4D-B orchestration's lazy adapter import) — `providers.internal_vendor` allowed ONLY for the adapter class. NO web, NO research.identity direct (2A happens inside the helper), NO fx, NO semantic, NO comparable, NO search, NO page fetch. |
| `product_intelligence/execution/vendor_refresh_runtime.py` (NEW) | `execute_vendor_refresh_with_default_providers(child_id)` — thin adapter constructing `InternalVendorAdapter()` and delegating ONCE (mirrors `comparable_runtime.py`) | `product_intelligence.execution.vendor_refresh`; `product_intelligence.providers.internal_vendor` (adapter class only). |
| `product_intelligence/execution/vendor_commercial_binding.py` (NEW — D10 helper) | `bind_and_encode_vendor_lookup(requested_mpn: str, response) -> dict` — the moved 4D-B binding/encoding policy: per-candidate frozen 2A `compare_part_numbers` (EXACT/NORMALIZED_EXACT → `SupplementSourceObservation(brand_new=True, brand_new_basis="VENDOR_API_POLICY")`; else `SupplementSourceIssue(MPN_MISMATCH, "vendor_mpn_mismatch")`); provider issues copied bounded (detail=None); final status mapping (transport FAILED → `"FAILED"` + `retrieved_at=None`; else `response.status.value` + `response.retrieved_at`); `ResearchSupplementResult` construction + `encode_research_supplement_result`; `SupplementCodecError` propagates | `product_intelligence.research.identity` (`compare_part_numbers`); `product_intelligence.research.commercial_supplement_codec` (dataclasses + encoder); `product_intelligence.providers.commercial` (`LookupStatus`); stdlib. Pure function: no DB, no env, no network. |
| `product_intelligence/execution/orchestration.py` (MODIFIED — behavior-identical) | `_try_vendor_commercial_lookup` (L1124–1257) keeps: config check, query build, ONE adapter call; the step-6/7 binding+encode block is REPLACED by a call to `bind_and_encode_vendor_lookup(request.manufacturer_part_number, response)`. No other orchestration line changes. | existing + `product_intelligence.execution.vendor_commercial_binding` |
| `product_intelligence/execution/__init__.py` (MODIFIED) | exports `execute_vendor_refresh`, `execute_vendor_refresh_with_default_providers`, `VendorRefreshExecutionError` (exact set pinned by a new adversarial node; the web allowlist `ALLOWED_EXECUTION_IMPORTS` is UNCHANGED in R1 — web imports none of these) | — |
| `product_intelligence/runs/vendor_refresh_manual_terminalization.py` (NEW — M1) | `manual_terminalize_vendor_refresh_execution(child_id, *, at=None)` — the row-10 CAS + bounded 0-row re-read reporting | `django.db`/`timezone`; `product_intelligence.runs.models` (model + vocabularies); `product_intelligence.runs.errors`; stdlib. NO providers, NO research, NO web, NO execution. |
| `product_intelligence/runs/errors.py` (MODIFIED — additive) | appends `VendorRefreshManualTerminalizationError` (reasons `already_terminal` / `pending_row` / `not_found`) under the existing VREF section; no existing class/signature changes | — |
| `product_intelligence/runs/__init__.py` (MODIFIED — additive) | `_VENDOR_REFRESH_R1_EXPORTS` frozenset + `__all__` entries + lazy `__getattr__` branch for the recovery primitive and its error (token-free names keep the R0 public-API guard literally green — §11 row 5) | — |
| `product_intelligence/runs/management/commands/vendor_refresh.py` (NEW) | the normal command: args, informational display, serialized txn (§3.4), post-commit execution via the runtime adapter, bounded stdout, exit codes (§8.3) | `django.core.management`; `product_intelligence.runs` public (trigger/claim + errors + model for display); `product_intelligence.execution` public (`execute_vendor_refresh_with_default_providers`, `VendorRefreshExecutionError`); stdlib (`os`, `uuid`, `datetime`). NO providers import (the per-file INNER_ROOTS guard will scan this file — §11 row 9), NO web import. |
| `product_intelligence/runs/management/commands/vendor_refresh_manual_terminalization.py` (NEW) | the recovery command: args incl. bounded `--evidence {reboot,process-scan,operator-stop}`, invokes the recovery primitive, bounded stdout/exit | same discipline as above minus the execution import; NO providers, NO web. |

Layer-direction note [PROPOSED, flagged]: the management commands live in
`runs/management/commands/` per frozen DESIGN2 §3.5 placement, and they
import the `execution` public API — an outer-surface (operational
entry-point) import direction, analogous to `web` importing `execution`.
No existing guard pins "runs services must not import execution"
[VERIFIED: no such test; no runs source file currently imports execution].
R1 ADDS a guard pinning the exact permitted form: no module in
`runs/` EXCEPT `runs/management/commands/*` may import
`product_intelligence.execution` (§12). [OPEN-O4 approves the carve-out +
guard.]

### 10.2 Exact call sequence (normal path) [PROPOSED]

```
Command.handle
 └─ runtime.execute_vendor_refresh_with_default_providers(child.id)   # only if [O] created
     └─ vendor_refresh.execute_vendor_refresh(child.id,
              vendor_adapter=InternalVendorAdapter())
         ├─ runs.claim_vendor_refresh(child.id)          # R0 primitive (loser → VendorRefreshClaimError, no adapter)
         ├─ parent load + COMPLETED re-check + requested_mpn == parent MPN
         ├─ env PI_VENDOR_LOOKUP_BASE_URL check
         ├─ CommercialLookupQuery(mpn=child.requested_mpn) + exact-equality check
         ├─ adapter.lookup(query)                        # THE single network call
         ├─ vendor_commercial_binding.bind_and_encode_vendor_lookup(child.requested_mpn, response)
         └─ runs.complete_vendor_refresh(child.id, 1, encoded)
         # single outer boundary: bounded defect → runs.fail_vendor_refresh(child.id, reason) → raise
```

(The claim for the command path already happened inside the serialized
txn, §3.4 [C]; `execute_vendor_refresh` re-asserts it defensively: a
child that is not PENDING at that point is a race/programming anomaly →
bounded claim error, zero adapter calls. This keeps the execution
function self-contained and safe if ever called on a non-fresh child —
the comparable precedent's shape.)

### 10.3 Expected behaviors (task §7) [PROPOSED]

- **Malformed wire payload** (non-JSON / non-UTF-8 / malformed section /
  oversized / unrecognized contract): the frozen adapter RETURNS a
  bounded `CommercialSourceResponse(status=FAILED or PARTIAL-with-issues)`
  — it does not raise (VERIFIED adapter contract). The refresh completes
  the child as **COMPLETED** with `lookup_status=FAILED` (or PARTIAL) —
  an executed lookup with a failed/partial RESULT, exactly the 4D-B
  semantics (frozen case E). No execution-machinery failure; no
  `INTERNAL_ERROR`.
- **Provider programming exception** (adapter raises — e.g. `ValueError`
  from `_ensure_configured` on a malformed (non-blank) base URL, or an
  internal bug): single outer boundary → `fail_vendor_refresh(
  INTERNAL_ERROR)` → `VendorRefreshExecutionError`. Distinct from
  transport FAILED (which is a RESULT). Note the config split:
  ABSENT/BLANK base URL → bounded `VENDOR_LOOKUP_CONFIG_MISSING` (pre-
  adapter, 0 calls); MALFORMED non-blank base URL → the adapter's
  `_ensure_configured` raises `ValueError` at the START of `lookup()`,
  before any HTTP request is built — so this path also makes ZERO
  requests → `INTERNAL_ERROR` after the adapter surfaces it (the bounded
  reason does not overclaim; display stays vocabulary-bound).
- **Database failure** (locked/IO during the serialized txn): full
  rollback, bounded "DATABASE BUSY/ERROR — no state changed", non-zero
  exit (W1). During complete/fail (W8): child stays RUNNING, bounded
  "terminalization NOT recorded" stdout, non-zero exit, M1 gate is the
  only later path.
- **Lost terminalization race** (row 3 vs row 10, or row 3 vs row 4):
  the CAS admits exactly one terminal write (I3); the loser re-reads and
  reports the actual terminal shape with zero mutation (W11); recovery
  never records an interruption over a real result.
- **Frozen contracts preserved**: exactly one `lookup()` per claimed
  attempt; zero calls for losers/ineligible/config-missing/
  normalization-mismatch; the EXACT captured canonical MPN is the query
  binding (`query.mpn == child.requested_mpn` enforced, fail-closed,
  never silently altered); provider transport FAILED is a COMPLETED
  result, not a machinery failure; MPN binding / source mapping /
  availability / zero-price semantics unchanged (same helper, same
  frozen codec V1, same `VENDOR_API_POLICY` basis); full codec encoding
  happens BEFORE the complete CAS (and the R0 complete service still
  validates the bounded V1 agreement pre-UPDATE); no FX lookup, no
  provider search, no semantic matching, no comparable execution, no
  price-authority promotion; ResearchRun + all original artifacts
  unchanged (I7); no network inside a DB txn (I10); bounded stdout
  without secrets or raw private Vendor responses (§8.3); no new Web
  POST or Django authentication (§2.2).

---

## 11. Existing test-contract evolution plan (task §8)

**Preservation baseline** [VERIFIED §1.5]: 5,959 production nodes (cde2a80)
and 6,082 frozen R0 nodes (3983db4). R1 must preserve all 6,082 except the
nodes below whose literal R0-only assertions are intentionally
phase-specific; every replacement must preserve or strengthen the original
safety invariant; at the implementation gate ChatGPT approves each
correction explicitly. No deletion, rename-to-avoid-collection, skip,
xfail, or weakening anywhere; all other changes are additions.

The R0 nodes are in `tests/runs/test_vendor_refresh_claims.py` (115
nodes). Exactly TWO nodes collide with R1's mandated surface; ONE more is
conditionally affected by naming.

| # | Original node (line at 3983db4) | Original meaning | Why the literal R0-only assertion must evolve in R1 | Replacement / strengthened assertion (PROPOSED) | How the original safety invariant is preserved | New adversarial R1 regression coverage |
|---|---|---|---|---|---|---|
| 1 | `TestNoRecoverySurface::test_no_vendor_refresh_management_command_exists` (L1446) | "R0 ships no command surface: no `vendor_refresh*` file in `runs/management/commands`" | Frozen DESIGN2 §3.5/§11 place the `vendor_refresh` command and (this design §3.1) the separately gated recovery command in R1 — the literal absence is FALSE by design once R1 lands | In-place evolution (same class, same name family may be re-purposed — proposed: same node name, new body): assert the EXACT R1 command surface — the set of `vendor_refresh*` files in `runs/management/commands` == `{vendor_refresh.py, vendor_refresh_manual_terminalization.py}` (exact membership; any other file fails); parse the normal command's argument parser: exactly 1 positional (parent run UUID) and exactly the flags `--operator` (required) and `--force-repeat` (optional) — NO child-id positional, NO `--reclaim-stale` or any token-bearing flag (reclaim/reset/retry/recover/stale/resurrect/reassign), NO undocumented flag; parse the recovery command's parser: exactly 1 positional (child UUID) + `--operator` (required) + `--evidence` (required, choices `{reboot, process-scan, operator-stop}`) and nothing else | The original invariant ("no unapproved execution/recovery surface") becomes a STRICTER exact-membership pin: R1 may add only the two approved command files with only the approved arguments — a hidden fifth flag or a third file fails closed. The absence property is subsumed by exact membership | New nodes in `tests/runs/test_vendor_refresh_command.py`: unknown/forbidden flag → parser error with zero DB statements (ORM spy, mirroring R0's `test_reserved_rejection_issues_no_db_statement` pattern); help output contains no forbidden surface tokens; invocation over an ineligible parent (not COMPLETED / no MPN / missing) → bounded refusal, zero children, zero adapter construction (sentinel), zero network; exit-code matrix per §8.3 |
| 2 | `TestNoRecoverySurface::test_no_vendor_refresh_execution_module_exists` (L1457) | "R0 ships no execution/runtime surface: no `vendor_refresh*.py` in `execution/`, nothing network-capable added" | Frozen DESIGN2 §11 R1 scope creates `execution/vendor_refresh.py` + `execution/vendor_refresh_runtime.py` (plus the D10 helper `execution/vendor_commercial_binding.py`, deliberately NOT `vendor_refresh`-prefixed) | In-place evolution: assert the EXACT R1 execution vendor surface — `vendor_refresh*.py` in `execution/` == `{vendor_refresh.py, vendor_refresh_runtime.py}`; the complete new-module set for the refresh feature in `execution/` == `{vendor_refresh.py, vendor_refresh_runtime.py, vendor_commercial_binding.py}`; exactly the runtime module imports `providers.internal_vendor` at MODULE level (the core's function-level lazy default construction is the only other adapter touchpoint, pinned by the AST allowlist); `vendor_commercial_binding.py` is pure (no DB/env/network imports) | The original invariant ("no network-capable surface before approval") becomes the STRICTER pin "the network-capable surface is exactly the approved set, and the concrete-adapter touchpoint is singular and located" | New nodes in `tests/execution/test_vendor_refresh_network_boundary.py` (frozen DESIGN2 §10.3(3) allowlist, extended to the helper): AST import allowlists per §10.1 table (no SearchProvider/PageFetcher/serper/http_page/semantic/comparable/providers.fx/FxObservationStore in any R1 module; runs files import no providers); sentinel "no-execution" probes: armed adapter double raises if constructed or called on any losing/ineligible/config-missing/normalization-mismatch path; exactly-one-call probe on the winning path |
| 3 (conditional) | `TestNoRecoverySurface::test_public_api_has_no_vendor_refresh_recovery_symbols` (L1435) | "No `runs.__all__` vendor symbol carries a forbidden surface token (reclaim/reset/retry/recover/recovery/force/stale/reassign/resurrect/interrupt)" | R1 MUST export its recovery primitive + error through the `runs` public API (command uses the public surface). With the PROPOSED token-free names (`manual_terminalize_vendor_refresh_execution`, `VendorRefreshManualTerminalizationError`) the node stays LITERALLY GREEN — no evolution needed | **If** the reviewer mandates a token-bearing name (OPEN-O2), evolve in place to: the vendor-symbols set of `runs.__all__` == {R0 four primitives + R0 five error classes + R1 primitive + R1 error class} (exact membership) AND the forbidden-token scan applied to all vendor symbols EXCEPT the explicitly approved R1 pair | The original invariant ("no recovery symbol in the public API") is preserved as "no UNAPPROVED recovery symbol": exact membership pins the approved one, the scan keeps catching any other (stale/reclaim/reset/...) drift | New node: importing the R1 recovery symbol from `product_intelligence.runs` works; importing any token-bearing recovery name (e.g. `recover_vendor_refresh`) raises AttributeError (surface is exactly the pinned set) |

**Nodes verified to stay UNCHANGED and green in R1** (explicitly checked
against the proposed R1 surface — no hidden collisions):

- `test_service_module_exposes_exactly_four_primitives` (L1378) and
  `test_module_defines_no_recovery_functions` (L1407): both scan
  `vendor_refresh_claims.py` ONLY. The R1 recovery primitive lives in a
  SEPARATE module (§3.1), so the R0 module surface remains exactly four —
  the tests stay literally true. [Design consequence of the separate
  module, PROPOSED.]
- `test_no_implicit_retry_after_failure` (L1465),
  `test_stuck_running_cannot_be_forced_terminal` (L1483): bodies assert
  R0-path behavior (trigger/claim over terminal/RUNNING rows) — all
  remain true; the stuck-RUNNING node's docstring ("absent-in-R0")
  stays accurate (no R0 path terminalizes it; the R1 gate is a separate
  surface the node never calls).
- Reserved-reason trio: `test_rejects_reserved_execution_interrupted_
  on_valid_running_row` (L1203), `test_reserved_rejection_issues_no_db_
  statement` (L1227), `test_reserved_reason_still_representable_in_
  database` (L1260): R0 `fail_vendor_refresh` is unmodified; all three
  stay green; they are the F1 pins the R1 primitive must coexist with.
- All shape/eligibility/idempotency/claim/complete/fail/terminalization/
  cascade/operator/trigger-source nodes (remaining ~100): R0 source and
  semantics unmodified → green.
- `tests/web/test_web_boundaries.py` (167 nodes at 3983db4): R1 adds no
  web surface and no web-visible execution imports → UNCHANGED (the
  frozen §10.3(10) allowlist extension belongs to R2).
- Model-inventory guards (`test_the_provider_layer_adds_no_model_and_no_
  migration`, `test_the_web_layer_defines_no_model`,
  `test_the_evaluation_corpus_is_not_persisted`,
  `test_the_identity_primitive_adds_no_model_and_no_migration`): R1 adds
  no model/migration → UNCHANGED.
- `test_only_the_expected_adapter_modules_exist` (providers file list):
  R1 adds no providers file → UNCHANGED.
- Frozen 4D-B suites (19+19), codec (46), internal vendor (165),
  vendor section (127), vendor authority (14), replay/firewall suites:
  UNCHANGED and green — they are the behavior-identity reference for the
  D10 extraction (§12 row 17).

**Automatic ADDITIONS (additions-only rule satisfied)** [VERIFIED
mechanism, §1.5]: each NEW `runs/` file is picked up by four per-file
parameterized guards — `test_research_run_boundaries.py::test_the_
persistence_layer_names_no_calling_system` and `::test_the_
persistence_layer_names_no_external_vendor` (RUNS_ROOT rglob incl.
management/commands/ and migrations/), `test_provider_boundaries.py::
test_nothing_is_wired_to_the_search_boundary_yet` (INNER_ROOTS incl.
runs: no `product_intelligence.providers` import), `test_web_boundaries.
py::test_the_inner_layers_do_not_import_the_web_layer` (INNER_ROOTS
incl. runs: no web import). Three new runs files (recovery module + two
commands) ⇒ +12 parameterized nodes, all of which must PASS: the new
files therefore carry no caller/vendor tokens (no "serper"/"google"/...
in help text) and import no providers/web — content constraints stated in
§10.1. New execution files (3) are scanned by `test_the_execution_layer_
imports_no_web` (single loop, no node delta) and by the new R1 AST
guards. Net R1 collection: 6,082 − 0 removed − 0 renamed + (2 evolved in
place, same count) + (new nodes, §12) → additions only.

---

## 12. Complete new regression matrix (task §9)

**Classification legend** — D = deterministic sequential (single
connection, in-memory suite DB, pinned clocks via the primitives' `at=`
parameters or patched `timezone.now`); M = mocked race-path (monkeypatched primitives/sentinels force interleavings that are impractical
to time); C = GENUINE independent-connection/process concurrency against
a FILE-based SQLite (threads with separate Django connections and/or
subprocesses; invariant assertions only — never timing). Per the task's
explicit bar: concurrency is proven ONLY by C nodes; sequential CAS tests
are labeled D and never claimed as concurrency proof.

**Concurrency test infrastructure [PROPOSED, OPEN-O6]**: the suite's
default test DB is in-memory SQLite on ONE persistent connection
[VERIFIED `tests/conftest.py`]; a fresh connection to an in-memory
database sees an EMPTY database, so multi-connection tests cannot run
there (verified property). The C nodes use a local fixture (NEW, inside
the R1 suites — NO conftest change, NO production change): a temporary
file SQLite per test, migrated, with per-thread Django connection
management (each worker thread opens its own connection; closed after).
Subprocess C nodes run a small stdlib-only snippet against the same file
DB (the probe technique of Appendix A). C nodes assert INVARIANTS
(exact call counts, row shapes, byte-identity, at-most-one-new-child)
over a FIXED number of rounds (5 rounds × 4 workers) — stable,
deterministic in assertion, non-flaky by construction.

| # | Scenario (task §9 item) | Nodes (suite) | Class |
|---|---|---|---|
| 1 | Exactly one API call for one winner | D: claim→execute with counting fake → exactly 1 `lookup`; C: 4 concurrent command invocations (file DB, counting fake with a short in-lookup sleep) → exactly 1 call total, 1 RUNNING-then-terminal child | D+C |
| 2 | Loser makes zero calls | D: pre-claimed child → execute → `VendorRefreshClaimError`, sentinel proves zero adapter construction AND zero call; D: pre-terminal child → same; C: losers of the row-1 race → zero construction (per-worker sentinels) | D+C |
| 3 | No call with missing Vendor configuration | D: env cleared → child FAILED `VENDOR_LOOKUP_CONFIG_MISSING`, 0 calls, payload fields NULL, reason exact; D: blank (whitespace) base URL → same; D: malformed non-blank base URL → adapter `ValueError` → FAILED `INTERNAL_ERROR` (documented split, §10.3) | D |
| 4 | No call when `CommercialLookupQuery` changes captured MPN | D: child row with surrounding-whitespace `requested_mpn` (fixture-level; trigger verbatim-capture already R0-pinned) → execute → FAILED `MPN_QUERY_NORMALIZATION_MISMATCH`, ZERO calls, `requested_mpn` byte-identical after (never rewritten); M: same with patched adapter sentinel | D+M |
| 5 | Frozen 2A and 4D-B policy equivalence | D: for a fixed response corpus (SUCCESS/PARTIAL/FAILED/mixed-candidate shapes incl. one-char MPN mismatch, missing explicit MPN, zero-price, OUT_OF_STOCK, UNKNOWN availability): `bind_and_encode_vendor_lookup(mpn, response)` output BYTE-EQUAL to the pre-extraction orchestration path's encoded payload (golden dicts captured from the frozen 4D-B fixtures); D: full frozen 4D-B + codec + provider suites green (19+19+46+165+127+14) | D |
| 6 | Normal COMPLETED / bounded FAILED / transport-FAILED-result distinction | D: (a) SUCCESS response → COMPLETED, `lookup_status=SUCCESS`, observations bound (EXACT/NORMALIZED_EXACT, `VENDOR_API_POLICY`); (b) PARTIAL → COMPLETED `PARTIAL` with usable observations + bounded issues; (c) transport FAILED response → **COMPLETED** `lookup_status=FAILED`, `retrieved_at=None`, zero observations — child state NOT FAILED; (d) codec `SupplementCodecError` → FAILED `RESULT_ENCODING_FAILED`; (c) vs (d) asserted as distinct rows/states | D |
| 7 | Crash windows and stuck RUNNING behavior | D/M: W2–W9 of §7 — patched raise/stop between steps (after claim; during call; after response; during complete; during fail): row shape, call count, byte-identity asserted per window; D: stuck RUNNING (claim committed, no CAS issued) → trigger returns it, claim rejects, zero calls (R0 node retained); M: recovery gate over a stuck RUNNING → row 10 exactly once (see #9); M: recovery vs complete race (row 11) → single terminal write, loser reports actual shape, zero mutation | D+M |
| 8 | Manual recovery denied without trustworthy evidence | D: recovery command without `--evidence` → parser error, ZERO DB statements (ORM spy); D: invalid evidence token → parser error; D: primitive over PENDING row → `pending_row` bounded error, row snapshot byte-identical; D: over COMPLETED/FAILED row → `already_terminal` bounded error + actual-shape report, zero mutation; D: R0 `fail_vendor_refresh` over the same RUNNING row with the reserved reason → still rejected with zero mutation (F1 re-pin) | D |
| 9 | Reserved failure reason written only by approved R1 recovery primitive | D: primitive writes row-10 shape successfully (CHECK-admitted, R0-pinned); D: AST scan — the ONLY module that references `EXECUTION_INTERRUPTED` as a WRITE value (in an update/terminalization call) is `runs/vendor_refresh_manual_terminalization.py` (model vocabulary + migration + R0 service's rejection check are pinned read/definition references); M: concurrent recovery + original complete (two threads, file DB) → exactly one terminal write (I3); C: 4-worker recovery race over one RUNNING row → one writer wins, three bounded `already_terminal`, row byte-stable | D+M+C |
| 10 | Existing PENDING and truthful operator provenance | D: programmatic trigger creates PENDING (non-command fixture); command invocation → stdout reports child id + recorded operator + created_at; row count unchanged; child still PENDING; zero adapter construction; `operator` field byte-identical (I6/§3.3 Option A pin); D: full command lifecycle on a fresh parent → row `operator` == the `--operator` value verbatim AND that invocation was the executor (single-invocation proof via the counting fake owned by the same process) | D |
| 11 | Five-minute safeguard, `--force-repeat`, simultaneous commands | D (pinned clock): latest terminal at age 299.9 s → refusal, 0 children, 0 calls; age 300.1 s → allowed; `--force-repeat` at 299.9 s → allowed (new child, never a rewrite); force over ACTIVE child → IN PROGRESS (force does not bypass in-progress); refusal stdout carries the blocking child id + finished_at + age; D: tie-break — two terminal children with identical `finished_at` → `id` DESC deterministic latest; C: interleavings 1/4/5/6 of §9 (4 workers, file DB): invariants = at most ONE new child per round, refusals commit nothing, force honored exactly once | D+C |
| 12 | Real SQLite transaction/locking behavior | C: (a) lock-statement serialization — worker A holds the txn (sleep after zero-row stmt), worker B's identical stmt blocks then reads A's committed state (Appendix A.7 pattern, in-test); (b) bounded busy error — raw connection holds an exclusive write lock > 5 s (pathological holder), command surfaces DATABASE BUSY, non-zero exit, ZERO mutation (row snapshot before/after); (c) kill — subprocess holds txn with uncommitted INSERT, killed → fresh connection writes immediately, INSERT rolled back, lock-statement zero-mutation confirmed (Appendix A.5 pattern); (d) reader non-blocking — concurrent SELECT proceeds while a command txn holds the lock (web GET not wedged) | C |
| 13 | Failure persistence and zero-mutation guarantees | D: every bounded failure path (#3–#6, #8) asserts the all-fields row snapshot pattern (R0 `_row_snapshot`) unchanged except the intended fields; D: parent + ALL original artifacts byte-identical after every R1 operation (reusing R0's lifecycle byte-identity test pattern extended with the R1 execution) | D |
| 14 | Parent and all original artifacts byte-identical | D: full R1 normal path (COMPLETED) + full R1 failure paths + recovery path vs. pre-state of `ResearchRun`, `PriceIntelligenceSnapshot`, original `ResearchSupplementSnapshot` (payload bytes + created_at), `ResearchFxSnapshot`, `ResearchMicronAliasSnapshot`, `ExecutionEvidenceRecord`s, `AiAssistedReviewCandidate`s, `ComparableResearchExecution`s | D |
| 15 | Zero FX and zero unapproved provider calls | D: sentinel instrumentation — `FxObservationStore` query spy (0 reads, 0 writes), `EcbFxProvider` construction sentinel (never), `SerperSearchProvider` never imported (AST + runtime), `HttpPageFetcher`/`HttpPdfFetcher` never constructed, semantic runtime never imported, `trigger_comparable_research` never called, `claim_execution`/`complete_execution` (ResearchRun-level) never called; D: network-boundary AST allowlists per §10.1 (all 8 new/modified R1 files) + sentinel one-allowed-call probe (frozen DESIGN2 §10.3(3) shape) | D |
| 16 | No new browser mutation surface | D: URLconf route set byte-equal to the frozen R0/production set (no new route); D: `web/views.py` + `web/urls.py` + `web/commercial_access.py` unchanged (hash pin vs 3983db4 blobs); D: no new POST handler, no CSRF surface, no template change (web file-set diff == ∅); D: full web-boundary suite (167) green unchanged | D |
| 17 | No regression from 4D-B helper extraction | D: frozen 4D-B/codec/provider/authority suites green (counts per §11); D: golden-dict equivalence (#5); D: orchestration behavior invariants — config-absent → no call/no snapshot; description-only → no call; success → one call + snapshot (frozen cases A–J re-run); M: helper called from both call sites with identical policy inputs → identical outputs (drift canary) | D+M |
| 18 | All previously frozen safety and authority boundaries | D: FULL suite — 6,082 frozen R0 nodes (2 evolved in place per §11, ChatGPT-approved at the gate) + all new R1 nodes → 0 removed / 0 renamed; `python manage.py check` clean; `python manage.py makemigrations --check --dry-run` → "No changes detected" (no R1 schema change); `git diff --check` clean; node-level collection diff vs 6,082 = additions only | D |

Command-suite summary (`tests/runs/test_vendor_refresh_command.py`,
frozen DESIGN2 §10.3(5) scope + this design's additions): run-uuid parse
(bounded 404-style), operator mandatory/verbatim/bounded, recorded
provenance exact (`trigger_source=MANAGEMENT_COMMAND`), bounded stdout
(no secrets, no base URL, no raw vendor content, no raw exception text),
exit-code matrix, no reclaim flag (evolution row 1), in-progress report,
safeguard ordering + refusal zero-persistence (row 11), Option-A
provenance pin (row 10), DATABASE BUSY path (row 12b). Recovery-suite
(`tests/runs/test_vendor_refresh_recovery.py`): rows 8–9 above + the
evidence-token vocabulary pin + stdout audit-line shape pin.

---

## 13. Expected production file changes for future R1 implementation

Exact file-level delta (future work — NOT performed by this design).
Base branch: `feature/vendor-refresh-r0` tip 3983db4 (production line per
frozen D9); no merge of development main.

| File | Change | Content (from §10.1) |
|---|---|---|
| `product_intelligence/execution/vendor_commercial_binding.py` | NEW | D10 shared helper `bind_and_encode_vendor_lookup` (moved verbatim policy from `_try_vendor_commercial_lookup` steps 6–7) |
| `product_intelligence/execution/orchestration.py` | MODIFY | `_try_vendor_commercial_lookup` L1124–1257: replace the inline binding/encode block with the helper call; behavior-identical (pinned by rows 5/17 of §12); no other line changes |
| `product_intelligence/execution/vendor_refresh.py` | NEW | `execute_vendor_refresh` + `VendorRefreshExecutionError` (§10.2/§10.3) |
| `product_intelligence/execution/vendor_refresh_runtime.py` | NEW | `execute_vendor_refresh_with_default_providers` (thin adapter) |
| `product_intelligence/execution/__init__.py` | MODIFY (additive) | export exactly `execute_vendor_refresh`, `execute_vendor_refresh_with_default_providers`, `VendorRefreshExecutionError` (adversarial exact-set pin, §12 row 18 context) |
| `product_intelligence/runs/vendor_refresh_manual_terminalization.py` | NEW | the M1 row-10 CAS primitive + bounded 0-row re-read reporting |
| `product_intelligence/runs/errors.py` | MODIFY (additive) | append `VendorRefreshManualTerminalizationError` (3 reasons); existing classes untouched |
| `product_intelligence/runs/__init__.py` | MODIFY (additive) | `_VENDOR_REFRESH_R1_EXPORTS` + `__all__` + lazy `__getattr__` branch (token-free names, §11 row 3) |
| `product_intelligence/runs/management/commands/vendor_refresh.py` | NEW | normal command (§3.4 flow, §8.3 stdout/exit contract) |
| `product_intelligence/runs/management/commands/vendor_refresh_manual_terminalization.py` | NEW | recovery command (evidence token, audit stdout) |
| `tests/execution/test_vendor_refresh_execution.py` | NEW | §12 rows 1–6, 13–15, 17 (D/M nodes) |
| `tests/execution/test_vendor_refresh_network_boundary.py` | NEW | §12 rows 2, 15 (AST allowlists + sentinels) |
| `tests/runs/test_vendor_refresh_command.py` | NEW | §12 rows 10, 11 (command D nodes) + §11 row 1 new nodes |
| `tests/runs/test_vendor_refresh_recovery.py` | NEW | §12 rows 7–9 |
| `tests/runs/test_vendor_refresh_concurrency.py` | NEW | §12 rows 1, 9, 11, 12 (C nodes + file-DB fixture, §12 infra) |
| `tests/runs/test_vendor_refresh_claims.py` | MODIFY (2 in-place evolutions ONLY) | §11 rows 1–2 (ChatGPT-approved at the gate); row 3 conditional on O2 naming |

Explicitly NOT changed: `runs/vendor_refresh_claims.py`,
`runs/models.py`, `runs/migrations/**` (no migration in R1),
`providers/**`, `research/**`, `web/**`, `domain/**`, `config/**`,
`scripts/**`, every other test file. [PROPOSED; enforced by §12 rows 16
and 18.]

---

## 14. Explicit remaining approval decisions and blockers

**Decisions requested from ChatGPT at this design gate:**

- **O1 — M1 evidence tolerances.** Confirm the 60 s creation-time
  tolerance in the E-SCAN predicate (`started_at` + 60 s) and the three
  evidence classes (E-REBOOT / E-SCAN / E-KILL) with the `--evidence`
  token vocabulary `{reboot, process-scan, operator-stop}`.
- **O2 — R1 recovery surface naming.** Confirm the token-free names
  (`runs/vendor_refresh_manual_terminalization.py`,
  `manual_terminalize_vendor_refresh_execution`,
  `VendorRefreshManualTerminalizationError`, command
  `vendor_refresh_manual_terminalization`) that keep the R0 public-API
  guard (§11 row 3) LITERALLY green; or mandate token-bearing names and
  approve the §11 row 3 conditional evolution.
- **O3 — Orphaned PENDING resolution policy.** Confirm R1 behavior =
  report-only HOLD (never claimed/executed/terminalized by R1); the three
  future-resolution options remain out of scope for R1 (ii requires a
  schema change; iii belongs to R3/8C).
- **O4 — Command-layer runs→execution import carve-out.** Confirm the
  outer-surface direction (management commands import the execution
  public API, mirroring web) together with the NEW guard pinning that no
  other `runs/` module imports `execution`.
- **O5 — `--force-repeat` record location.** Confirm: no row-level force
  record in R1 (stdout + host audit only; a row-level record would be a
  schema change and is not proposed).
- **O6 — Concurrency test infrastructure.** Confirm the file-based
  SQLite local fixture approach (temporary file DB per C test, per-thread
  connections, subprocess snippets; NO conftest change, NO production
  change) as the means to make C nodes genuine.
- **O7 — Cooldown boundary semantics.** Confirm: strict `< 300 s`
  refusal, `finished_at` reference of the latest terminal child
  (max, tie-break `id` DESC), single host clock via `timezone.now()`
  sampled inside the serialized transaction.
- **O8 — Deployment prerequisite (BLOCKER for deployment, not for
  implementation).** The frozen DESIGN2 §4.5 host permissions +
  operational audit review (host/CMD account inventory, command-logging
  posture, database file + directory ACLs, runbook controls — incl. the
  backup-while-app-stopped discipline vs command invocations, §9 case D)
  must be completed and recorded BEFORE R1 deploys. The M1 E-SCAN
  credibility also rests on this review (administrator process-table
  visibility).

**Contradiction check against frozen DESIGN2/R0 [PROPOSED assessment]:**
No frozen contract is contradicted. Two deliberate refinements of OPEN
design space are flagged for approval rather than claimed as settled:
(a) the combined trigger+claim transaction (§3.4) refines DESIGN2 §3.6's
phase-by-phase crash table for the COMMAND path only — R0 primitives,
durable shapes, and all frozen invariants are unchanged (crash
consequences strictly improve: the PENDING-orphan window becomes
unreachable on the command path); (b) the advisory zero-row write-lock
statement (§3.4 A3) is the concrete mechanism for M4, which frozen
DESIGN2 §13 explicitly assigned to "R1 review" ("Concurrent invocations
… reviewed separately at R1"). Both are inside confirmed decisions D3/D6
and do not reopen any frozen commercial, semantic, FX, replay, or
pricing-authority contract.

**Unresolved risks carried forward (honest inventory):**

1. Privileged-writer residual (M2): host-level code/SQL can bypass all
   service-level guarantees — accepted per the frozen threat model
   (DESIGN2 §4.2), stated, not hidden.
2. Orphaned PENDING via non-command triggers blocks the parent's refresh
   until a future approved gate (O3) — inert (zero external outcome),
   reported on every invocation.
3. Cooldown window is wall-clock on one host; clock regression affects
   the OBSERVED window only (operator-safety check, not a rate limit).
4. Busy-timeout bound (5 s): a pathological lock holder yields a bounded
   "database busy" refusal (zero mutation) — retry is manual.
5. E-SCAN predication assumes the canonical launch form
   (`python manage.py vendor_refresh <uuid> --operator …`); wrapped or
   renamed launches that hide the command line force HOLD (conservative).
6. R2 display of `EXECUTION_INTERRUPTED` rows must carry the I8 UNKNOWN
   wording (assigned to R2, frozen vocabulary boundary).
7. The 6,082-node R0 collection and all suite-green claims above were
   verified in a design worktree at 3983db4 with Python 3.14.7 / Django
   5.2.17 / pytest 9.1.1; the implementation gate re-verifies per the
   frozen validation gates.

---

## 15. Implementation sequencing into bounded R1 substeps

Each substep ends with a ChatGPT independent review of the actual diff +
test evidence before the next begins; no substep expands into the next;
all substeps branch from 3983db4 on the production line (frozen D9); no
substep touches development main.

- **R1-1 — D10 shared helper extraction (pure refactor).**
  `execution/vendor_commercial_binding.py` + the `_try_vendor_commercial_
  lookup` delegation + the golden-dict equivalence nodes (§12 row 5/17) +
  the helper AST/purity guards. Gate criteria: frozen 4D-B/codec/
  provider/authority suites green UNCHANGED; full suite = 6,082 + additions
  only; `makemigrations --check` clean.
- **R1-2 — Execution core (no command yet).**
  `execution/vendor_refresh.py` + `execution/vendor_refresh_runtime.py` +
  execution `__init__` additive exports + network-boundary suite (§12
  rows 1–6, 13–15, 17 D/M nodes). Gate criteria: one-call/loser-zero-
  call/config-missing/normalization-mismatch/transport-FAILED-result
  distinction pinned; no surface callable from web exists.
- **R1-3 — Normal command + M4 safeguard + M3 Option A.**
  `runs/management/commands/vendor_refresh.py` + serialized txn + command
  suite (§12 rows 10, 11, 16; §11 row 1 evolution APPROVED at this gate)
  + C-node infrastructure (O6) + concurrency suite (§12 rows 1, 9(partial),
  11, 12 C nodes). Gate criteria: interleaving invariants hold under
  genuine independent connections; the two evolved R0 nodes are the ONLY
  R0-node modifications, explicitly approved node-by-node.
- **R1-4 — M1 recovery gate (separately gated surface).**
  `runs/vendor_refresh_manual_terminalization.py` + additive error +
  `runs/__init__` additive exports + `runs/management/commands/
  vendor_refresh_manual_terminalization.py` + recovery suite (§12 rows 7,
  8, 9; §11 row 3 conditional evolution only if O2 so decides). Gate
  criteria: reserved reason writable ONLY by this primitive (AST pin);
  R0 F1 pins green unchanged; row 10 single-winner race proven under C.
- **R1-5 — Final R1 gate.**
  Full suite (6,082 frozen + all R1 additions; 0 removed / 0 renamed),
  `manage.py check`, `makemigrations --check --dry-run`, `git diff
  --check`, node-level collection diff report, file-delta audit vs §13,
  and the O8 prerequisite status (blocks DEPLOYMENT until recorded;
  implementation may land without it, deployment may not).

The pushed document is a proposal only. It authorizes nothing until each
substep is separately reviewed and approved.

---

## Appendix A — Verification commands and probe transcripts (this session)

All reads: worktree `C:/dev/Product_Intelligence_vref_r1_design` at
3983db4 (`feature/vendor-refresh-r1-design`, created for this design via
`git worktree add … 3983db4b57e9b960d5bf6841042c93a14687fdd0`); DESIGN2
via `git show a87ff1b5665f76e96b0c2628459e8975df3d4095:docs/
VENDOR_ONLY_REFRESH_DESIGN.md`. No destructive git operation was used;
no source/test/migration/settings file was modified (only this document
is new; temporary probe files were created and deleted).

```
git cat-file -t 3983db4…  /  cde2a80… /  a87ff1b…     # all "commit"
git log --oneline 3983db4… -4                          # R0 chain over cde2a80
git show --stat 1f5cdd8 / ad7d68b / 3983db4            # R0 file deltas
git diff a87ff1b 3983db4 -- CLAUDE.md docs/…           # doc-line divergence
python -m pytest --collect-only -q                     # at cde2a80: 148 files / 5959 nodes
python -m pytest --collect-only -q                     # at 3983db4: 149 files / 6082 nodes
node-level diff (per-file counts)                      # +123 delta, §1.5
python -m pytest tests/runs/test_vendor_refresh_claims.py
                                                       # 115 passed, 5 subtests, 0 failed
python -m pytest tests/execution/test_4d_b_vendor_commercial.py
                 tests/execution/test_4d_b_vendor_section_integration.py
                 tests/research/test_commercial_supplement_codec.py
                                                       # 84 passed, 0 failed
```

SQLite probes (temporary file databases, deleted afterwards; deployment
configuration: rollback journal, no WAL, no Django OPTIONS):

- A.1 zero-row UPDATE inside a txn acquires the RESERVED lock (~0.4 ms).
- A.2 a second independent connection's write blocks ~760 ms behind the
  holder, then proceeds on the fresh committed state.
- A.3 a new reader proceeds while the RESERVED lock is held.
- A.4 a commit succeeds while a short SHARED read is held (busy-wait
  within timeout).
- A.5 process kill while holding the write lock: lock released at the OS
  level; uncommitted INSERT rolled back; zero mutations from the
  zero-row lock statement; fresh writes succeed immediately.
- A.6 contention beyond the busy timeout → `OperationalError: database
  is locked` (bounded).
- A.7 end-to-end through the Django ORM at 3983db4:
  `VendorRefreshExecution.objects.filter(parent_run_id=<P>,
  active_slot=2).update(active_slot=2)` inside `transaction.atomic()`
  → 0 rows updated; second thread's identical statement blocked ~762 ms;
  post-commit row byte-identical (`PENDING`, `active_slot=1`).

Django version behavior check: `QuerySet.none().update()` issues NO SQL
(empty-query short-circuit) — therefore the zero-MATCH filter (not
`.none()`) is the correct lock-statement form [VERIFIED].

---

**Final status: `VREF-R1 DESIGN COMPLETE — PENDING CHATGPT ARCHITECTURE
REVIEW`**
