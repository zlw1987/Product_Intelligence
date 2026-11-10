# PRODUCT-INTEL.VREF-R1-DESIGN-FU1 — Vendor Refresh R1 Execution & Operator Safety Architecture (revised)

**Design-Only Revision for ChatGPT Final Architecture Review**

- **Task type:** DESIGN ONLY (VREF-R1-DESIGN-FU1). No implementation. No
  source, test, migration, settings, or deployment changes were made by
  this revision. One file exists and is modified by this revision: this
  document (on branch `feature/vendor-refresh-r1-design`, on top of the
  candidate commit `a18f1ccc4d0475c575742ca55a45d15c936fccf9`).
- **Review baseline (candidate under review):** `a18f1ccc4d0475c575742ca55a45d15c936fccf9`
  ("docs: propose vendor refresh R1 execution safety architecture").
  Verdict of record: **R1 design NOT FROZEN. R1 implementation NOT
  AUTHORIZED.**
- **Frozen R0 implementation baseline (work base for this design):**
  `3983db4b57e9b960d5bf6841042c93a14687fdd0`
  (branch `feature/vendor-refresh-r0`, tip commit
  "PRODUCT-INTEL.VREF-R0-FU1-GATE: authorized test-contract correction
  (Task C)").
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
  [VERIFIED in the candidate session by `--collect-only` at cde2a80].
- **Frozen R0 test collection:** 6,082 nodes / 149 files [VERIFIED in the
  candidate session by `--collect-only` at 3983db4; the +123-node delta is
  fully accounted in §1.5].
- **Reviewer / approval gate:** ChatGPT (independent architecture
  reviewer). The pushed document is NOT an approved design and does NOT
  authorize implementation.

**FU1 revision history (this document vs candidate `a18f1cc`):**

| Finding | Defect in candidate | Correction (sections) |
|---|---|---|
| F1 — P0 double claim | §3.4 claimed the child inside the command's serialized trigger+claim transaction; §10.2 made `execute_vendor_refresh` claim the same child again ("re-assert defensively"), which the frozen R0 CAS (PENDING→RUNNING only) must reject — the normal success path was self-contradictory | §3.2, §3.3, §3.4, §5, §10.2, §10.3, §12 (rows 1–2, 19), §14, §15 |
| F2 — adapter construction timing | §3.2 guaranteed zero adapter construction on losing/preflight-rejected paths; §10.1/§10.2 wired the runtime to construct `InternalVendorAdapter()` eagerly before any check ran | §3.2, §10.1, §10.2, §10.3, §12 (rows 2–4, 13), §14 (O9) |
| F3 — recovery evidence gate | `--evidence {reboot\|process-scan\|operator-stop}` was a user-typed token presented as if it established "sufficient trusted external evidence"; no collection procedure, no linkage, no retention, no HOLD semantics; E-REBOOT/E-SCAN/E-KILL and the 60 s tolerance were not re-evaluated | §3.1 (full rewrite), §4, §7 (W12), §8, §10.1, §12 (row 8), §14 (O1/O8, R1-4 BLOCKED), §15 |
| F4 — recovery safety-test contract | Token-free R1 names (`manual_terminalize…`) were chosen so the R0 recovery-symbol guard stays literally green — guard evasion by naming | §3.1, §10.1, §11 (rows 1–3, staged in-place evolution with strict R1 allowlist), §12 (rows 8–9), §13, §14 (O2), §15 |
| F5 — invariant accuracy | "exactly one lookup per successfully claimed child" conflated the structural at-most bound with the success-path fact and over-claimed for preflight refusals | §3.2 (LB-1/LB-2/LB-3), §4.2 (I4), §5, §9, §10.3, §12 (rows 1, 3, 4, 18) |

- **Every statement is marked:**
  - **[VERIFIED]** — read directly from the frozen SHAs (candidate-session
    verifications retained; this FU1 session's added verifications are in
    §1.7 and Appendix A.2), with file/line references; or established by a
    controlled probe recorded in Appendix A.
  - **[PROPOSED]** — a design decision in this document, requiring ChatGPT
    approval before any implementation.
  - **[OPEN]** — genuinely unresolved; requires a decision at this gate.
  - **[BLOCKED]** — specified, but implementation gated on an unmet
    precondition (used only for R1-4 / M1, §3.1/§14/§15).

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
| `execution/comparable_runtime.py` | whole file (48) | The thin default-provider adapter: the ONLY place in the web/command stack that constructs concrete provider classes; delegates once to the frozen execution function. **Construction is EAGER** (both fetchers are instantiated in the function body before the delegation call) — the precedent the candidate R1 design mirrored in §10.2. FU1 note: the R1 execution surface does NOT mirror the eager construction; §3.2/§10.1 (O9) replace it with a zero-arg factory supplied by the runtime and invoked only after ownership and preflight checks. |
| `web/views.py` — `research_comparables` | L1032–1094 | The existing precedent for trigger-then-synchronous-execution of a PENDING child by the SAME invocation (POST, CSRF, bounded redirects). R1's command surface is analogous but host-side, and R1 adds the §3.3 ownership constraint that this web path does not have (documented in §3.3 as the contrast case). |
| `runs/management/commands/` | dir listing | Contains exactly `__init__.py` and `pilot_check.py` at 3983db4. **No `vendor_refresh*` command exists** (frozen R0 boundary, pinned by R0 tests §11). |
| Layer/AST guards | `tests/domain/test_domain_boundaries.py` (CALLER_TOKENS L59 = foxpro/fox pro/vfp/sap/erp; VENDOR_TOKENS L63–74 = tavily/serpapi/serper/google/bing/openai/anthropic/claude/gemini/langchain; `test_the_execution_layer_imports_no_web` L192–212), `tests/providers/test_provider_boundaries.py` (INNER_ROOTS L98–104 = domain/research/runs/web/evaluation; `test_nothing_is_wired_to_the_search_boundary_yet` L222–246; provider file-list pin L294–321; model inventory L250–258), `tests/web/test_web_boundaries.py` (INNER_ROOTS L34–39 = domain/research/runs/evaluation; `test_the_inner_layers_do_not_import_the_web_layer` L226–236; `ALLOWED_EXECUTION_IMPORTS` L102–109), `tests/runs/test_research_run_boundaries.py` (per-file CALLER/VENDOR token scans over RUNS_ROOT L273–290 — RUNS_ROOT rglob includes `management/commands/` and `migrations/`; token scans are over FULL FILE TEXT, docstrings included) | The per-file guards that every NEW R1 file will automatically be collected by (§1.5 explains the node deltas; §11/§13 state the content constraints the new files must satisfy). No guard pins "runs must not import execution" — see §10.1/§14-O4. |

### 1.4 Frozen DESIGN2 contract points that R1 must honor [VERIFIED at a87ff1b]

- §3.3 final R0 state-transition table (rows 1–9; rows 3–4 the ONLY legal
  RUNNING→terminal transitions in R0; row 9 forbids recovery-based
  terminalization in R0) and the F2 "what the CAS guarantees" paragraph
  (atomic single-winner terminalization, NOT issuer identity).
- §3.4 (proposed R1 execution mechanism — DESIGN2's own step 1 was a
  claim-first `execute_vendor_refresh`; DESIGN2 §12.2 M2/M4 kept the R1
  enforcement MECHANISM open at this design gate, so §3.2/§10.2 of THIS
  document answers it with separated claim/execute — §14 contradiction
  check (e)).
- §3.5 (R1 runtime placement — "the only place in the web/command stack
  touching the concrete provider class"; the construction TIMING shown
  there is illustrative and is refined by §3.2/O9 of this document —
  §14 contradiction check (d)).
- §3.6 "Future R1 operational recovery gate (specified now; NOT R0
  scope)": manual interruption only on sufficient trusted external
  evidence that the prior process is terminated; wall-clock alone
  insufficient; atomic conditional transition; reserved
  `EXECUTION_INTERRUPTED` = "execution interrupted; the external Vendor
  request outcome is explicitly UNKNOWN"; the R1 gate transition is its own
  separately approved primitive — the ONLY sanctioned writer of the
  reserved reason; "No overlapping outbound request may be justified
  merely by reclaiming a database slot"; no lease/scheduler/supervisor
  invented.
- §4.2 (Option A management command, `--operator` self-reported
  provenance, host-access authorization, deployment prerequisite: host
  permissions + operational audit review before R1 deploys), §4.5
  (self-reported provenance NOT authentication; no claim that trustworthy
  OS audit evidence exists until the host permissions + operational audit
  review verifies it), §4.6 (trigger-vs-execution provenance option 1:
  "the R1 command claims and executes only the child its own trigger
  created in the same logical invocation; a pre-existing PENDING child is
  reported with a bounded message (identified by its `created_at` and
  recorded `operator`) and left untouched"; no new model field without
  approved justification), §5.1 (within one attempt: **at most one**
  `InternalVendorAdapter.lookup()`; zero calls if the attempt crashes
  before the call or the base URL is unconfigured), §5.2 (R1 repeat
  safeguard: evaluated BEFORE persistence and BEFORE any Vendor API
  request; refusal leaves NO new PENDING child; `--force-repeat`;
  concurrent invocations "reviewed separately at R1" — that review is
  §3.4 of THIS document), §11 (R1 scope: `execution/vendor_refresh.py`,
  `execution/vendor_refresh_runtime.py`, shared 4D-B helper extraction
  per D10, `runs/management/commands/vendor_refresh.py`, recovery gate,
  provenance mechanism, trusted ownership, tests §10.3(2)(3)(4)(5);
  "Done when: a production-equivalent command invocation produces exactly
  one Vendor API call, one durable append-only row, zero changes to the
  original run's persisted artifacts"), §12.1 confirmed decisions D1–D10,
  §12.2 open mechanisms M1–M4 (this document answers M1–M4; M1 is
  answered with a BLOCKED implementation gate, §3.1).

### 1.5 Verified test baselines (this session) [VERIFIED]

- Collection at cde2a80: **148 files / 5,959 nodes** (reproduces the
  historical production baseline).
- Collection at 3983db4: **149 files / 6,082 nodes** (reproduces the
  frozen R0 collection).
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
- R0 claims suite green at 3983db4 (candidate worktree): **115 passed, 5
  subtests passed, 0 failed** (0.90 s). Re-verified for this revision:
  **115 passed, 5 subtests passed, 0 failed, 0 skipped** (§1.7).
- Frozen 4D-B + codec suites green at 3983db4 (candidate worktree):
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

### 1.7 FU1 revision verifications (this session, at 3983db4) [VERIFIED]

Additional direct reads performed for this revision (no file modified):

| Fact | Reference | Why it matters |
|---|---|---|
| `claim_vendor_refresh(child_id)` (no `at=` parameter) is ONE conditional UPDATE `WHERE id=… AND state=PENDING AND active_slot=1 AND started_at IS NULL` → `state=RUNNING, started_at=now`; 0 rows → re-read → `VendorRefreshClaimError` (absent or not-PENDING, bounded detail); winner returns the re-read object | `runs/vendor_refresh_claims.py` L327–377 | The claim admits PENDING only. A second claim on an already-RUNNING child MUST fail — this is the mechanism that made the candidate's double-claim (F1) a P0 contradiction. |
| `complete_vendor_refresh` / `fail_vendor_refresh` (`*, at=None`) validate bounded preconditions BEFORE one conditional UPDATE `WHERE state=RUNNING AND active_slot=1 AND finished_at IS NULL`; 0 rows → bounded error, zero mutation; reserved reason rejected before any UPDATE | L381–489 / L518–611 | Terminal CAS single-winner; the row-10 recovery CAS has the identical shape. |
| `trigger_vendor_refresh` wraps its INSERT in its OWN `transaction.atomic()` (savepoint when nested) and returns concept-1 active child / created object / race winner with NO discriminator | L134–319, esp. L283–319 | Nested inside the command's serialized txn the trigger INSERT is a savepoint (W1 rollback is total). |
| `InternalVendorAdapter.__init__` (L1609–1615) **does not read configuration** ("Initialize without reading configuration. Configuration is validated lazily on first lookup"); `_ensure_configured` (L1617–1629) reads `PI_VENDOR_LOOKUP_BASE_URL` and is the FIRST statement of `lookup()` (L1631+); a malformed non-blank base URL raises `ValueError` before any `Request`/`opener.open`; transport failures return `FAILED` responses, programming errors propagate | `providers/internal_vendor.py` | F2: construction is a side-effect-free allocation; the first configuration touch is inside `lookup()`. The zero-construction/zero-lookup branch table (§3.2) is stated against exactly this behavior. |
| `comparable_runtime.execute_comparable_research_with_default_providers` constructs both fetchers EAGERLY in the function body before delegating (function-level imports) | `execution/comparable_runtime.py` (48 lines) | The precedent the candidate mirrored; FU1 records the deliberate deviation (O9). |
| R0 guard nodes: `test_service_module_exposes_exactly_four_primitives` (L1378), `test_module_defines_no_recovery_functions` (L1407, AST over `vendor_refresh_claims.py` ONLY), `test_public_api_has_no_vendor_refresh_recovery_symbols` (L1435, token scan over vendor symbols in `runs.__all__`), `test_no_vendor_refresh_management_command_exists` (L1446, glob `vendor_refresh*` in `runs/management/commands`), `test_no_vendor_refresh_execution_module_exists` (L1457, glob `vendor_refresh*.py` in `execution/`); `_FORBIDDEN_SURFACE_TOKENS` = (reclaim, reset, retry, recover, recovery, force, stale, reassign, resurrect, interrupt) (L1359–1370) | `tests/runs/test_vendor_refresh_claims.py` | F4: the exact R0 guard bodies the in-place evolution (§11) must preserve intent over. |
| R0 failure-reason rejection nodes (ALL preserved by F4): `test_unknown_failure_reason_rejected` (L458, storage CHECK), `test_rejects_unknown_reason_before_mutation` (L1191), `test_rejects_reserved_execution_interrupted_on_valid_running_row` (L1203), `test_reserved_rejection_issues_no_db_statement` (L1227), `test_reserved_reason_still_representable_in_database` (L1260), `test_all_non_reserved_reasons_accepted` (L1160), `test_r0_legal_reasons_are_exactly_the_five_non_reserved` (L1170), fail-reason type battery (L2071–2125), complete version-agreement battery (L974–1107) | same file | F4: "preserve all R0 failure-reason rejection tests" — listed exhaustively; none is modified in R1. |
| `CALLER_TOKENS` / `VENDOR_TOKENS` guard lists (L59–74) and that the runs per-file token scans read FULL FILE TEXT | `tests/domain/test_domain_boundaries.py` | The recovery module's content (PowerShell reference strings, docstrings) must avoid these tokens; verified the proposed content does. |
| `runs/errors.py` class shape: reason constants + `__init__(child_id, detail, *, reason=None)` pattern | `runs/errors.py` L141–234 | The two appended R1 error classes mirror it. |
| `pilot_check.py` command precedent: bounded safe stdout, `sys.exit(0/1)`, no mutation | `runs/management/commands/pilot_check.py` | The §8.3 stdout/exit contract mirrors it. |
| DESIGN2 §3.4 (L686–754), §3.5 (L755–767), §4.5 (L950–976), §4.6 (L977–1019), §5.1 (L1022–1043), §5.2 (L1044–1069), §11 (L1607–1738), §12.1–12.2 (L1739–1785), §13 (L1786–1840) | `a87ff1b:docs/VENDOR_ONLY_REFRESH_DESIGN.md` | The frozen bar the M1–M4 answers must meet; M2/M4 mechanisms explicitly open at this gate (§12.2). |
| R0 claims suite re-run at 3983db4 for this revision | `python -m pytest tests/runs/test_vendor_refresh_claims.py` | **115 passed, 5 subtests passed, 0 failed, 0 skipped** (baseline re-confirmation). |

---

## 2. Precise R1 scope and exclusions

### 2.1 In scope (R1, per frozen DESIGN2 §11, detailed here) [PROPOSED]

1. **M1** — the operational recovery gate for stuck RUNNING children:
   machine-collected evidence, the attestation boundary, operator
   procedure, one separately-gated R1 terminalization primitive + its
   command, `EXECUTION_INTERRUPTED` semantics. **[BLOCKED at R1-4 pending
   O8 — §3.1/§14/§15; the requirement is not weakened.]**
2. **M2** — trusted execution ownership enforced in the execution path
   (single-invocation claim→execute→terminalize; no owner token; no schema
   change; claim and execution are SEPARATED contracts, §3.2).
3. **M3** — trigger-vs-execution provenance: execution constrained to the
   creating invocation (DESIGN2 §4.6 option 1); honest handling of
   pre-existing PENDING children (never silently executed).
4. **M4** — the five-minute repeat safeguard made atomic under the actual
   SQLite deployment (serialized short write transaction; `--force-repeat`).
5. **§10 provider boundary** — `execution/vendor_refresh.py`,
   `execution/vendor_refresh_runtime.py`, the management command, the
   D10 shared 4D-B binding/encoding helper extraction, the single
   authoritative call graph (§10.2), expected behaviors (malformed
   payloads, provider programming exceptions, database failures, lost
   terminalization races).
6. **§11 test-contract evolution plan (staged, in-place, allowlist-based),
   the §12 R1 regression matrix, and the §16 final-checks compliance
   map.**

### 2.2 Out of scope (exclusions — none of these change in R1) [PROPOSED]

- No R0 source change: `runs/vendor_refresh_claims.py`,
  `runs/models.py`, `runs/errors.py` (additive-only exception in §13 —
  TWO NEW error classes appended; the four R0 primitives and their
  signatures are untouched), migration 0012, and every R0 test node
  except the explicitly enumerated staged in-place evolutions in §11
  (each requires ChatGPT approval at the named implementation gate).
- No schema change: no new model, no new field, no new migration. The R1
  recovery transition stores the already-admitted reserved value
  (`EXECUTION_INTERRUPTED`) in the existing `failure_reason` column
  (verified: R0 CHECK `vendor_refresh_valid_failure_reason` admits it;
  R0 test `test_reserved_reason_still_representable_in_database` pins it).
- No new model field, no new failure reason, no new trigger source, no
  new state: the R1 surfaces use exactly the frozen R0 vocabularies.
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

### 3.1 M1 — RUNNING operational recovery gate **[BLOCKED at R1-4 pending
O8 — §14]**

**Frozen rules being implemented** [VERIFIED DESIGN2 §3.3 row 9, §3.6,
§12.1 D3(b), F1; the frozen bar is NOT weakened by this revision]: a
RUNNING child MUST NOT be reclaimed merely because its timestamp is old;
the 10 s Vendor socket timeout is a per-operation socket timeout, not an
absolute deadline; recovery requires **sufficient trusted external
evidence that the prior execution process is terminated**; the transition
is a single atomic conditional write; the external Vendor outcome is
preserved as explicitly UNKNOWN; the reserved `EXECUTION_INTERRUPTED` is
written ONLY by this separately approved R1 primitive — never via the R0
`fail_vendor_refresh`, which rejects it with zero row mutation (R0
behavior, untouched, re-pinned by §12).

**The evidence problem (F3).** A token typed by an operator on a command
line is an **attestation, not proof**: it cannot by itself establish that
the original process has terminated, it can be false, and the database
cannot distinguish a truthful from an untruthful one. The candidate
design presented `--evidence {reboot|process-scan|operator-stop}` as if
the token established the frozen bar; it did not. This revision therefore
separates, and specifies, three fact classes:

- **Class M — machine-collected and machine-verified by the recovery
  command, at command time, on the deployment host.** The command itself
  collects the evidence (no operator transcription of the decisive
  facts): the row facts (child id, parent, state, `started_at`,
  `created_at`, recorded operator), the host name, and — for the
  process-scan and operator-stop classes — a live process-table scan with
  the §3.1 predicate evaluated IN CODE; for the reboot class — the host
  boot time with the ordering check evaluated IN CODE. Any collection
  failure (subprocess error, timeout, unparseable output) is fail-closed:
  HOLD, zero mutation.
- **Class A — human-attested, irreducible, never machine-provable in
  R1.** That the deployment host is the ONLY host on which the execution
  command could have run (single-host inventory completeness); for
  operator-stop, that the earlier stop act targeted the original
  execution; and, in all classes, the ultimate substance — that the
  original process is terminated — which the Class M facts establish for
  the current host at command time and the attestation extends to the
  whole inventory. The command cannot verify a Class A fact; it requires
  the operator to assert it EXPLICITLY (the `--attest-host-inventory`
  flag; refusal without it) and records it.
- **Class H — host-auditable AFTER THE FACT under the O8 operational
  audit regime.** The command line in the host command log (child id,
  `--operator`, `--evidence`, the attestation flag), the bounded stdout
  (evidence summary + record path + record SHA-256 digest), and the
  retained evidence record (§3.1 retention). The O8 review (frozen
  DESIGN2 §4.5 deployment prerequisite) is what makes Class A
  attestations cross-checkable — and hence what makes the evidence
  "trusted" in the frozen sense. **Until O8 is completed and recorded,
  the gate cannot meet the frozen bar; that is the reason R1-4 is
  BLOCKED (§14), not a reason to weaken the requirement.**

**What the candidate's alternative (command-side auto-scan) rejected —
re-evaluated (F3).** The candidate rejected a command-side scan for R1
(OS-specific subprocess coupling; "it would convert an operator
attestation into code that DESIGN2 §4.5 says must not claim
trustworthiness without the verified audit posture"). FU1 re-evaluation:
the rejection's second premise no longer holds as stated — DESIGN2 §4.5
does not forbid code from COLLECTING evidence; it forbids CLAIMING
trustworthiness before the audit review verifies the host posture. A
command-side scan claims less than the candidate's operator-transcribed
token: the decisive facts (table contents at command time, boot time,
predicate evaluation) are machine-collected and machine-evaluated, the
operator's role shrinks to (a) the explicit inventory attestation and
(b) the prior stop act for operator-stop. The subprocess coupling is real
but bounded: it is quarantined to the recovery module behind a scanner
seam (the only host-I/O surface in R1, AST-pinned, §10.1), read-only,
fixed 60 s timeout, fail-closed on ANY error (collection failed ⇒ HOLD,
zero mutation). **[PROPOSED: the command-side machine scan is the R1
collection mechanism; the candidate's operator-scan + typed-token design
is superseded.]**

**The evidence predicate (machine-evaluated) [PROPOSED].**

- **Signature:** the normal command's canonical launch form
  `python manage.py vendor_refresh <parent-run-uuid> --operator <id>
  [--force-repeat]` — the command line therefore contains the substring
  `vendor_refresh <parent-run-uuid>` (parent uuid rendered lowercase).
  The recovery command's own line (`vendor_refresh_recovery <child-uuid>
  …`) contains a DIFFERENT substring and never matches the predicate — a
  recovery invocation cannot evidence itself into denial. A later normal
  command over the same parent (e.g. an operator re-check) matches the
  signature but its creation time is AFTER `started_at + tolerance`, so it
  is outside the predicate window and — per §3.3/§3.4 — structurally
  harmless (it sees the active child, reports in-progress, makes zero
  calls). The predicate is: **a process row with CommandLine containing
  `vendor_refresh <parent-run-uuid>` (case-insensitive) AND
  CreationDate ≤ `started_at` + 60 s.**
- **E-SCAN (process-scan):** the predicate evaluates to EMPTY over the
  live table ⇒ machine-established absence of the original (or any
  original-window) execution on this host at command time.
- **E-KILL (operator-stop):** the operator previously stopped the
  matching execution; the command then runs the SAME live scan; a clean
  result machine-establishes the post-stop table state. The stop ACT
  itself remains Class A (attested by the operator; cross-checked by the
  O8 command log) — but the dangerous substance (is anything
  original-window still alive?) is machine-checked at command time.
- **E-REBOOT (reboot):** the command reads the host boot time and
  machine-checks `boot_time ≥ started_at`. A boot after the claim
  terminated every user process unconditionally; this is the strongest
  class and requires no process-table predicate.

**The 60 s tolerance — re-evaluated (F3) [PROPOSED, O1 confirms].** The
original execution process necessarily exists BEFORE it wrote the row:
true process start < `created_at` ≤ `started_at` (trigger INSERT and claim
commit in the same transaction on the same host clock; claim sets
`started_at`). OS process-creation timestamps carry second-level (at
best) granularity, and wrapper launches (`cmd /c …`, shortcut forms) add
small margins. Hence a live original ALWAYS presents
`CreationDate ≤ started_at + ~1 s`. Any process presenting
`started_at < CreationDate ≤ started_at + 60 s` is PROVABLY not the
original (it started after the claim committed) and is structurally
harmless (§3.3: it sees the active child, reports in-progress, zero
calls) — so counting it in the predicate band can only ADD denials.
Conversely, a tolerance of 0 would risk a FALSE RECOVERY only if a live
original's recorded creation time were more than the granularity margin
later than `started_at` — within ~1–2 s. **T = 60 s is therefore
conservative in the safe direction (denial-only) with ~60× margin over
the worst expected timestamp error; any T ≥ ~2 s is safe, and larger T
never risks a double call, only a delayed (correct) denial. T = 60 s is
retained.** [OPEN-O1 confirms T and the canonical reference command
forms.]

**Limit of the machine predicate (stated, not hidden) [PROPOSED]:** the
scan proves absence of a process whose CommandLine CONTAINS the
signature. A launch form that HIDES the arguments (renamed wrapper with
no visible command line, certain service hosts) makes the original
invisible to the scan — indeterminate, NOT clean. The runbook (O8)
therefore pins the canonical launch form as the ONLY documented way to
start a refresh, and the operator's duty is: if the original invocation
was not started in the canonical form, the scan is indeterminate ⇒ **HOLD
(do not run the recovery command)**. The evidence record preserves the
signature substring, the window end, and the matching rows (expected
empty) so the O8 audit can re-verify the predicate against the retained
raw scan output.

**Evidence record (retained artifact, command-written) [PROPOSED, O1
confirms the shape].** After the scan, BEFORE the CAS, the command writes
a bounded JSON record (schema v1, exact key set, strict writer) to the
deployment evidence directory (deployment-owned env
`PI_VENDOR_RECOVERY_EVIDENCE_DIR`; absent/unwritable ⇒ bounded refusal,
zero mutation — the record is the durable evidence anchor, so an
unavailable store is a HOLD, not a skip). Keys (all classes):
`schema_version` (=1), `evidence_class` (`reboot` | `process-scan` |
`operator-stop`), `child_id`, `parent_run_id`, `host_name`,
`captured_at_utc` (tz-aware, the scan instant), `operator` (the
`--operator` value), `host_inventory_attested` (true — the explicit Class
A attestation), `signature_substring` (`vendor_refresh <parent>`),
`window_end_utc` (`started_at + 60 s`), `tolerance_seconds` (60),
`scan_command` (the canonical reference form for the class), `scan_total`
(process count), `scan_matching_rows` (the predicate-matching rows: pid,
creation date, bounded command line — expected empty when recovery
proceeds), `boot_time_utc` (reboot class only), `outcome` (`recovered` |
`evidence_present` | `reboot_order_violated` | `collection_failed` |
`race_lost_terminal` — no record exists for `EVIDENCE_STORE_UNAVAILABLE`,
a stdout-only refusal, because the store is the unavailable thing).
The review-required linkage is explicit: child ID (`child_id`), parent
UUID (`parent_run_id`), originating process (the `signature_substring` +
`window_end_utc` predicate identity, with `scan_matching_rows`
recording any process that hits it), host (`host_name`, machine-checked
equal to the running host), execution time (`captured_at_utc`, the scan
instant, against the row's `created_at`/`started_at`).
The stdout audit line carries the record path + SHA-256 digest, so the
retained file is digest-anchored. **Retention:** the record file is the
durable evidence (runbook O8 defines the retention location/duration);
stdout is the digest anchor; no evidence value is stored in the database
(no schema change, §2.2). The record is written for REFUSED attempts
too (outcomes `evidence_present` / `collection_failed`) — denials are
audited like actions.

**Operator procedure (authorized; every step explicit) [PROPOSED]:**

1. Run the normal command: `python manage.py vendor_refresh
   <parent-run-uuid> --operator <id>`. It reports the active child (id,
   state, recorded operator, `created_at`/`started_at`) and exits with
   zero calls (in-progress path, §3.4).
2. Determine the class: did the host reboot since `started_at` (E-REBOOT);
   did the operator stop the execution (E-KILL); otherwise a clean live
   scan (E-SCAN). For E-KILL the stop is performed as a host act with the
   canonical command line visible (O8 runbook), BEFORE step 3.
3. Establish the Class A inventory fact: the operator is on the
   deployment host and can attest (single-host posture) that no other
   host/session could run the execution command. **If not — HOLD (step
   5b); the attestation flag must never be asserted dishonestly; O8's
   command-log cross-check exists to catch exactly that.**
4. Run the recovery command (canonical form): `python manage.py
   vendor_refresh_recovery <child-uuid> --operator <id> --evidence
   {reboot|process-scan|operator-stop} --attest-host-inventory`. The
   command: reads the row (read-only); collects Class M evidence at
   command time (scanner seam, 60 s timeout, fail-closed); evaluates the
   predicate IN CODE; writes the evidence record; performs the row-10 CAS.
   Refusals (predicate non-empty ⇒ EVIDENCE_PRESENT; collection failure
   ⇒ EVIDENCE_COLLECTION_FAILED; boot ordering violated ⇒
   REBOOT_ORDER_VIOLATED; evidence store absent/unwritable ⇒
   EVIDENCE_STORE_UNAVAILABLE; row not RUNNING ⇒ ALREADY_TERMINAL /
   PENDING_ROW / NOT_FOUND) are bounded, zero-mutation (CAS not reached
   or 0-row), non-zero exit, and recorded.
5. Outcomes: (a) **RECOVERED** — row durably FAILED
   (`EXECUTION_INTERRUPTED`, I8 semantics: outcome UNKNOWN); a later
   refresh of the parent is a NEW child (concept 2) with its own single
   call; (b) **HOLD** — any refusal: do nothing else to the database;
   the child stays RUNNING and occupies the active slot (safe direction:
   it can never cause a double Vendor call; it only blocks new refreshes
   for that parent); record WHO, WHEN, and WHICH evidence was missing in
   the operational audit; re-attempt is allowed (each attempt is
   re-collected at command time — no stale evidence is reused).

**Explicit HOLD rule [PROPOSED]:** the default is HOLD. Recovery proceeds
only when Class M collection SUCCEEDS, the predicate is EMPTY (or boot
ordering holds), the attestation flag is present, the row is RUNNING, and
the evidence store is writable. Every other combination — host
unreachable, CIM failure, timeout, unparseable row, indeterminate
signature (non-canonical original launch), inventory not attestable,
missing `--attest-host-inventory`, unavailable evidence store — is a
bounded refusal with zero mutation. Wall-clock age is NEVER an input: no
threshold of `started_at` age alone (or plus age) can trigger or justify
recovery (frozen rule, re-pinned by §12).

**Protection against premature recovery allowing overlapping Vendor
requests (F3) [PROPOSED, analysis]:** the danger of a premature
recovery is NOT double terminalization — the row-10 CAS vs the original's
complete/fail admits exactly one terminal write (W11, frozen CAS
property). The danger is an OVERLAPPING OUTBOUND REQUEST: the original
process still alive mid-lookup gets its child terminalized underneath it
(its later complete/fail loses the CAS and reports, W11), while a NEW
normal command invocation — now unblocked because the slot is free —
creates child 2 and issues lookup 2 on the same MPN CONCURRENTLY with
the original's in-flight lookup 1. **No database mechanism can prevent
this** (child 2 is a fresh, legitimate concept-2 row once child 1 is
terminal); the ONLY protection is the evidence gate itself — the Class M
predicate (machine, at command time) plus the Class A inventory
attestation (auditable under O8). This is exactly the frozen §3.6 rule
that "no overlapping outbound request may be justified merely by
reclaiming a database slot." Residual: a FALSE attestation (operator
erroneous or malicious under a shared admin account) is detectable by
the O8 cross-check (command log vs record vs retained raw scan), not
preventable in software — stated, not hidden. **While R1-4 is BLOCKED,
the danger is unreachable from the R1 surface: no R1 writer of
`EXECUTION_INTERRUPTED` exists until the gate unblocks (W12, §7).**

**The R1-only conditional terminalization transition [PROPOSED]
(specified; implementation BLOCKED at R1-4).** One new runs-layer
primitive in a NEW module
`product_intelligence/runs/vendor_refresh_recovery.py` (honest name —
F4: the surface carries its true "recovery" function; the R0 guard is
evolved in place with a strict allowlist, §11 row 3; the candidate's
token-free naming is rejected as guard evasion), function
`recover_vendor_refresh_execution(child_id, *, at=None)`:

```
UPDATE runs_vendorrefreshexecution
   SET state='FAILED', active_slot=NULL,
       finished_at=<at or now>, failure_reason='EXECUTION_INTERRUPTED'
 WHERE id=<child_id> AND state='RUNNING' AND active_slot=1
   AND finished_at IS NULL
```

- Single conditional UPDATE in its own transaction (same CAS idiom as the
  R0 primitives; verified shape §1.7).
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
    interruption is recorded over a real result (W11).
  - FAILED (any reason) → same: report the actual reason.
  - PENDING → bounded error: the gate applies to RUNNING only (a PENDING
    row is the separate orphan case, §3.3 — never terminalized by M1).
  - absent → bounded error (parent-deleted cascade or bad id).
- No retry of the transition; the lost race is reported, not re-attempted.
- Zero network, zero adapter construction, zero lookup — in every branch.
- New bounded error classes (appended to `runs/errors.py`; additive
  only), mirroring the R0 class shape: `VendorRefreshRecoveryError`
  (reasons `already_terminal` / `pending_row` / `not_found`) and
  `VendorRefreshRecoveryEvidenceError` (bounded evidence-refusal
  reasons: `collection_failed` / `scan_timeout` / `scan_unparseable` /
  `evidence_store_unavailable` / `predicate_present` /
  `reboot_order_violated` — content-free; `scan_timeout` /
  `scan_unparseable` map to `collection_failed` for bounded stdout).

**R0 compatibility [PROPOSED, pinned by §11/§12]:** `fail_vendor_refresh`
still rejects `EXECUTION_INTERRUPTED` before any UPDATE (R0 code
untouched; ALL R0 failure-reason rejection tests preserved verbatim —
§1.7 list; re-run green at every gate); the R1 primitive is the ONLY
sanctioned writer of the reserved value (AST-pinned, §12 row 9); the R1
primitive lives in a separate module, so the R0 AST pin
(`test_module_defines_no_recovery_functions`, which scans
`vendor_refresh_claims.py` only) and the four-primitive `__all__` pin
remain literally true.

**No resumption or reuse [PROPOSED]:** a recovered child is terminal
FAILED — `claim_vendor_refresh` rejects terminal rows (R0 CAS
precondition `state=PENDING`), the R1 command never claims a child it did
not create (§3.3), the post-claim executor refuses non-RUNNING rows
(§3.2 state re-assert), and a later refresh of the parent is a NEW child
row (concept 2) with its own single call. The recovered row can never be
resumed or reused for a second Vendor call — structurally.

**R1-4 gate state: BLOCKED [PROPOSED; the frozen requirement is not
weakened].** The recovery surface (primitive + evidence machinery +
command + its suite) is FULLY SPECIFIED here for approval, but its
implementation is BLOCKED at substep R1-4, separately from R1-1…R1-3,
pending BOTH: (i) the O8 host permissions + operational audit review
completed and recorded (frozen DESIGN2 §4.5 deployment prerequisite — now
explicitly ALSO the R1-4 unblock condition: the attestation regime, the
canonical launch form, the evidence retention location/duration, and
administrator process-table visibility must be verified before the first
possible use), and (ii) this gate's approval of the §3.1 mechanism
(evidence classes, predicate, T = 60 s, record shape, HOLD rule). While
BLOCKED: no R1 code writes `EXECUTION_INTERRUPTED`; a stuck RUNNING row
is a permanent reported HOLD (every normal command invocation reports it;
§7 W2–W5 resolution column); R1-1…R1-3 and R1-5 proceed normally. The
block is a DEFERRAL of the only surface that could write the reserved
reason until the frozen evidence bar is operationally satisfiable — not
a relaxation of the bar.

**Alternatives considered and rejected [PROPOSED]:**

- *Operator-transcribed scan + typed `--evidence` token (the candidate
  design):* rejected per F3 — transcription moves the decisive facts out
  of machine control (a scan read yesterday, or for another child, can be
  replayed as token truth); the token was presented as evidence it was
  not. Superseded by the command-side machine scan + explicit attestation
  flag + retained record above.
- *A schema field for evidence (e.g. `recovery_evidence` text):* rejected
  — no schema change in R1 (§2.2); the row's reserved reason + timestamps
  plus the retained record file + stdout digest + host command log carry
  the evidence (DESIGN2 F1 designed the storage to admit the transition
  without any schema change).
- *Extending the R0 `fail_vendor_refresh` with a reserved-reason escape
  hatch (e.g. a `recovery=True` keyword):* rejected — it would modify R0
  service code and weaken the F1 zero-mutation rejection pin; the separate
  primitive keeps the R0 surface exactly four.
- *Deferring the recovery design itself (no specification until O8):*
  rejected — DESIGN2 §3.6 requires the gate to be specified at R1 review;
  specifying now and gating implementation on O8 is the honest split
  (the specification is reviewable; the capability is withheld).

### 3.2 M2 — Trusted execution ownership (separated claim / post-claim
execution)

**The entrypoint contract (F1).** Claim ownership and post-claim
execution are SEPARATED contracts with exactly ONE claim site in R1:

- **The claim.** `runs.claim_vendor_refresh(child_id)` (R0, frozen) is
  invoked exactly ONCE per normal command invocation — at step [f] inside
  the command's serialized trigger+claim transaction (§3.4), on the child
  the command's own trigger just INSERTed. Loser invocations (snapshot
  exit, §3.4 [D1]) make ZERO claim attempts. The claim is the single
  ownership fact: its CAS (PENDING→RUNNING, verified §1.7) admits at most
  one winner per child for ANY writer.
- **The post-claim execution.**
  `execution.vendor_refresh.execute_claimed_vendor_refresh(child_id, *,
  vendor_adapter=None, vendor_adapter_factory=None)` — the single R1
  execution body. It NEVER claims: it does not call
  `claim_vendor_refresh`, does not reference it (AST-pinned, §12 row 19),
  and performs no PENDING→RUNNING transition. It re-asserts the row's
  state READ-ONLY (RUNNING + active_slot=1 + finished_at NULL; else
  bounded `VendorRefreshExecutionError`, zero adapter construction, zero
  lookup) — a state check that is NOT a claim and from which NO ownership
  is inferred. It then runs preflight S4–S6, constructs the adapter from
  the supplied factory (S7, §3.2 adapter contract), performs the single
  lookup, binds/encodes, and terminalizes (S8–S9).
- **No bypass by catching a failed claim.** No R1 module catches
  `VendorRefreshClaimError` (or any claim/terminal CAS error) to infer
  ownership or to proceed to execution. A claim failure is always
  terminal for the invocation that hit it: on the command path a claim
  raise inside the serialized transaction rolls back the whole
  transaction (W1 — no row, zero calls; structurally unreachable because
  the claim targets the command's own fresh INSERT, but fail-closed
  nonetheless); elsewhere it propagates bounded. The candidate's
  "execute re-claims defensively and the command's earlier claim makes
  that re-claim fail" path is DELETED: a re-claim on an already-RUNNING
  child must fail under the frozen R0 CAS (PENDING only, verified
  §1.7), so the candidate's normal success path was self-contradictory.
  AST pin + adversarial node: §12 row 19.
- **Exactly one claim per normal command invocation.** Success path:
  exactly one (step [f]). Every other path: zero (ineligible, IN PROGRESS,
  COOLDOWN REFUSAL, anomaly, DB busy). Pinned by the runtime claim-count
  spy (§12 rows 1/19) and by the single claim call site (§10.2).

**The explicit function signatures (single authoritative set; §10.2 is
the call graph):**

```python
# product_intelligence/execution/vendor_refresh.py (NEW; R1-2)
def execute_claimed_vendor_refresh(
    child_id: uuid.UUID | str,
    *,
    vendor_adapter: "InternalVendorAdapter | None" = None,
    vendor_adapter_factory: "Callable[[], InternalVendorAdapter] | None" = None,
) -> VendorRefreshExecution: ...

class VendorRefreshExecutionError(Exception):
    """Bounded execution-layer failure. Persisted-reason vocabulary is
    exactly the R0_LEGAL set (mpn_binding_violation /
    vendor_lookup_config_missing / mpn_query_normalization_mismatch /
    result_encoding_failed / internal_error); non-persisted reasons:
    state_not_running / state_not_found / adapter_argument_conflict /
    terminalization_not_recorded. Content-free messages."""

# product_intelligence/execution/vendor_refresh_runtime.py (NEW; R1-2)
def execute_claimed_vendor_refresh_with_default_providers(
    child_id: uuid.UUID | str,
) -> VendorRefreshExecution: ...
# Supplies the concrete InternalVendorAdapter CLASS as the
# vendor_adapter_factory (function-level import — the only R1 module
# that imports providers.internal_vendor, DESIGN2 §3.5 placement) and
# delegates once. Constructs nothing itself.

# product_intelligence/runs/vendor_refresh_recovery.py (NEW; R1-4 [BLOCKED])
def recover_vendor_refresh_execution(
    child_id: uuid.UUID | str, *, at: datetime | None = None,
) -> VendorRefreshExecution: ...  # row-10 CAS, §3.1; zero network ever

# product_intelligence/execution/vendor_commercial_binding.py (NEW; R1-1)
def bind_and_encode_vendor_lookup(requested_mpn: str, response) -> dict: ...
# The D10 helper (moved 4D-B binding/encode policy). Pure: no DB, no env,
# no network, no adapter import.
```

**Authority boundary of the public post-claim executor (F1).**
`execute_claimed_vendor_refresh` is PUBLIC (exported from
`product_intelligence.execution`) and therefore callable by anyone with
host access. Its authority boundary, stated exactly:

- **Documented contract:** the caller MUST be the invocation that won
  the child's claim CAS (the claim win held in the caller's own call
  stack, same process). The function verifies what it CAN verify — the
  row is RUNNING (state re-assert, fail-closed, zero calls otherwise) —
  and cannot verify issuer identity, because the frozen R0 schema carries
  no owner token (R0 F2: the CAS guarantees atomic single-winner
  terminalization, NOT issuer identity; verified §1.2/DESIGN2 §3.3).
- **It cannot silently violate M3 (trigger-vs-execution provenance).**
  M3-sensitive shape = executing a child a non-creating invocation did
  not claim. The executor cannot claim, so it cannot execute a PENDING
  orphan (state re-assert refuses PENDING — bounded, zero calls): the
  §3.3 Option-A orphan case is machine-guarded, not merely procedural.
  The residual shape — a direct call on a RUNNING crash-orphan by a
  NON-owner — would make a second lookup; it is (a) never reachable from
  the R1 command surface (losers report at the snapshot and never reach
  the executor; the command calls the executor exactly once on its own
  child), and (b) the same privileged-writer class as calling the R0
  complete/fail CAS directly or issuing raw SQL — explicitly OUTSIDE the
  frozen threat model (DESIGN2 §4.2 scopes to external/subnet actors and
  operator error on a controlled host) and NOT claimed to be prevented
  (below).
- **The single R1 caller** of the executor is the normal command, post-
  commit, on the child it created+claimed (§10.2). A future R3 web
  surface may not call the executor without bringing its own claim +
  provenance mechanism (R3/8C gate, frozen DESIGN2 §12.2 M6).

**What the mechanism guarantees — and what it does not (F5 precision).**
The lookup-count contract, stated exactly (LB):

- **LB-1 (at most).** AT MOST ONE `InternalVendorAdapter.lookup()`
  invocation per child, and AT MOST ONE Vendor HTTP request per child.
  Bound: the R0 claim CAS (at most one claim winner per child, any
  writer) + the R0 terminal CAS (at most one terminal write) + the R1
  surface structure (exactly one executor call site; the command calls
  it at most once per invocation, only on its own child; losers never
  reach it; the executor never claims) + the frozen adapter policy (one
  GET per `lookup()`, no retries).
- **LB-2 (exactly, success path).** EXACTLY ONE `lookup()` invocation
  (and, modulo a transport failure returning a bounded FAILED response
  after that single request, exactly one HTTP request) ONLY WHEN the
  invocation created+claimed the child, the claim committed, ALL
  preflight checks (S4–S6) passed, and execution reached S7. This is the
  frozen DESIGN2 §11 "Done when" property ("a production-equivalent
  command invocation produces exactly one Vendor API call").
- **LB-3 (zero).** ZERO adapter constructions, ZERO `lookup()`
  invocations, ZERO HTTP requests for: command losers (IN PROGRESS /
  COOLDOWN REFUSAL / ineligibility / anomaly / DB-busy), executor state-
  re-assert refusals (PENDING / terminal / absent row), MPN-binding
  violations, missing/blank Vendor config, normalization mismatches,
  and the recovery command (every branch, §3.1).
  (The post-preflight branches where the factory IS invoked are
  classified exactly in the §3.2 table / §10.3: a failed
  construction; a `lookup()` that raises at its first statement before
  any HTTP request; a transport failure as a bounded RESULT; and a
  post-lookup encode failure.)

For ANY number of concurrent invocations that go through the R0 claim
primitive on one child: at most one claim winner (CAS); the executor is
reachable only in the winner's own post-claim stack on the command
surface; at most one terminal write (CAS). **The candidate's sentence
"exactly one lookup per successfully claimed child, zero calls for every
loser and every terminal child, ever" is REPLACED by LB-1/LB-2/LB-3 —
"ever" is not claimed against arbitrary privileged writers.**

**What it does NOT guarantee against arbitrary privileged Python/DB
writers [PROPOSED — unchanged from candidate, restated over the new
contract]:** nothing, and it is not claimed: a process with host access
can call `fail_vendor_refresh(child, INTERNAL_ERROR)` on a RUNNING row
(the schema does not authenticate the issuer — frozen F2), call the R1
recovery primitive with a false `--attest-host-inventory` (the attestation
is Class A; O8 cross-checks it after the fact), call the public executor
on a RUNNING child it did not claim (second lookup — the residual above),
or issue raw SQL. This is the same threat class as any server-side
capability, and DESIGN2 §4.2 explicitly scopes the threat model to
external/subnet actors and human operator error on a controlled host. A
claim-owner token (schema change: a random column written by claim,
matched by complete/fail) would authenticate ISSUERS to each other but
would stop no privileged writer (they can read/copy the token or bypass
the services); DESIGN2 §12.2 M2 offers that mechanism as the
approval-gated alternative — **this design does NOT invoke that
approval**: no owner token, no schema change; the enforced surface
guarantee (LB + single claim site + post-claim-only executor) covers the
frozen threat model. [Revisit ONLY if a future phase introduces a second
legitimate execution surface (worker/queue/web) — R3/8C gate; none does
in R1–R2.]

**The adapter construction contract (F2).** Construction is separated
from claim and from preflight and happens exactly once, at S7, strictly
AFTER the claim committed and AFTER all preflight checks passed:

- The core takes the adapter as EITHER a pre-constructed instance
  (`vendor_adapter` — test doubles only in R1) OR a zero-arg factory
  (`vendor_adapter_factory` — the production command path); exactly one
  of the two (neither or both ⇒ bounded `adapter_argument_conflict`,
  zero calls). The core has NO silent default construction and NO import
  of `providers.internal_vendor` in any form (AST-pinned, §11 row 2 /
  §12 row 15).
- The runtime (`execute_claimed_vendor_refresh_with_default_providers`)
  supplies the concrete class itself as the factory (function-level
  import — the only R1 module importing `providers.internal_vendor`;
  DESIGN2 §3.5 placement preserved: the runtime remains the only
  component in the web/command stack that touches the concrete provider
  class). It constructs NOTHING itself.
- **Deviation from the mirrored precedent, recorded (O9):**
  `comparable_runtime.py` constructs its fetchers EAGERLY (verified
  §1.7); DESIGN2 §3.5 showed the R1 runtime the same way ("constructing
  `InternalVendorAdapter()`"). The comparable path has no preflight check
  that carries a zero-construction guarantee, so eager construction was
  harmless there. R1's M2 guarantee IS "zero adapter construction on
  every losing and preflight-rejected branch" (LB-3), which eager
  construction violates. The lazy-factory form preserves DESIGN2 §3.5's
  frozen PLACEMENT and single-construction properties while moving the
  construction TIMING to after ownership + preflight — the reviewer-
  preferred option. [PROPOSED refinement — O9 confirms.]
- Verified substrate [VERIFIED §1.7]: `InternalVendorAdapter.__init__`
  reads no configuration (side-effect-free allocation); the first
  configuration touch is `_ensure_configured()` as the first statement of
  `lookup()` — hence "zero construction" (no object) is strictly
  stronger than "zero configuration read", and both hold on every LB-3
  branch by the factory placement.

**Exact zero-construction / zero-lookup table per failure branch [PROPOSED,
pinned by §12 rows 2–4/13]:**

| Branch (point of exit) | Factory invoked | Adapter object | `lookup()` calls | HTTP requests | Terminal write |
|---|---|---|---|---|---|
| S0 argument invalid (bad UUID / missing operator) | no | none | 0 | 0 | none (no DB) |
| S2 trigger ineligibility (parent not found/not COMPLETED/no snapshot/no MPN) — rollback | no | none | 0 | 0 | none (rollback) |
| S2 [D1] IN PROGRESS (active child, PENDING or RUNNING) | no | none | 0 | 0 | none |
| S2 [D2] COOLDOWN REFUSAL | no | none | 0 | 0 | none |
| S2 [O] anomaly (trigger returned a non-created child) | no | none | 0 | 0 | none (no claim attempted) |
| S2 DB busy/locked (contention > 5 s) | no | none | 0 | 0 | none (rollback) |
| Executor state re-assert refusal (row PENDING / terminal / absent) | no | none | 0 | 0 | none |
| S4 MPN binding violation | no | none | 0 | 0 | fail (R0_LEGAL reason) |
| S5 base URL absent/blank | no | none | 0 | 0 | fail (R0_LEGAL reason) |
| S6 normalization mismatch | no | none | 0 | 0 | fail (R0_LEGAL reason) |
| S7 factory raises (construction fails) | yes — fails | none | 0 | 0 | fail (R0_LEGAL reason) |
| S7 base URL malformed non-blank (factory OK; `lookup()` raises `ValueError` in `_ensure_configured`, first statement, before any `Request`/`opener.open`) | yes | one | 1 (raises before socket) | **0** | fail (R0_LEGAL reason) |
| S7 reached, response returned (SUCCESS / PARTIAL / transport FAILED) | yes | one | 1 | 1 (transport failure = the single request that failed) | complete |
| S8 encode failure | yes | one | 1 | 1 | fail (RESULT_ENCODING_FAILED) |
| Recovery command (every branch, §3.1) | no (no factory exists there) | none | 0 | 0 | row-10 CAS only |

Sentinel discipline: tests inject a COUNTING factory (records invocation,
returns a fake adapter that raises/records on `lookup`) and, where an
instance is injected, the instance itself is armed — §12 rows 2–4/13.

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
execute it [PROPOSED — RECOMMENDED; FU1: claim and execution are
separated contracts, §3.2]:**

- Mechanism (no schema change): the normal command, inside its serialized
  transaction: snapshot active children → cooldown decision → (if
  allowed) `trigger_vendor_refresh` → if the returned child was NOT in
  the snapshot (proof: this invocation's INSERT created it) →
  `claim_vendor_refresh` on it (THE one and only claim of the
  invocation) → COMMIT. If the snapshot already contained an active child
  (PENDING or RUNNING), the command REPORTS it (id, state, recorded
  operator, `created_at`/`started_at`) and exits — no claim, no
  execution, no INSERT, zero network calls. Post-commit, the SAME
  invocation calls the post-claim executor exactly once for its own
  RUNNING child (the executor never claims — §3.2) and alone proceeds to
  complete/fail through its own call stack.
- **Existing PENDING is never silently executed by the normal command**
  (frozen DESIGN2 §4.6 option 1, restated as a hard R1 rule): a PENDING
  active child is reported (id, state, recorded operator, `created_at`)
  and left untouched — no claim, no executor call, zero calls. It is
  additionally MACHINE-GUARDED: even a direct call of the post-claim
  executor on a PENDING row is refused (state re-assert, bounded, zero
  calls — §3.2), so no R1 surface can execute an orphan PENDING child,
  by procedure or by code.
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
  While R1-4 is BLOCKED (§3.1), this orphan is a permanent reported HOLD
  (safe: it blocks only its parent's refresh; zero overlapping requests
  are possible because no R1 surface can terminalize it).
- **Crash during the Vendor call:** RUNNING orphan, ≤1 request in flight,
  outcome unknown. M1 (or HOLD while blocked).
- **Crash after the Vendor response but before complete:** RUNNING orphan,
  request completed externally, result lost. M1 (or HOLD while blocked).
  A later refresh (new child, after recovery) is a new timestamped
  evidence point; nothing is rewritten.
- **What the stored `operator` truthfully means under Option A:** the
  self-reported TRIGGER initiator (frozen meaning) — AND, on the command
  path, also the executor, because only the creating invocation claims
  and only that same invocation calls the post-claim executor. The field
  therefore never lies about trigger provenance and, for command-created
  rows, coincides with execution provenance. No row exists on the command
  path whose executor differs from its recorded operator.
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
  claimed, executed, or terminalized by R1** (machine-guarded: the
  executor refuses PENDING, §3.2; M1 applies to RUNNING only, §3.1). Its
  resolution is [OPEN-O3]: (i) leave as a permanent reported HOLD (no
  schema change; the operator audit records it; the parent's refresh
  stays blocked until a future approved gate), (ii) a future gate
  approves a narrow "abandon orphan PENDING" procedure (claim
  PENDING→RUNNING via the R0 primitive, then fail with a NEWLY reserved
  reason — which requires a vocabulary + CHECK change, i.e. a schema
  change, hence its own approval), or (iii) the R3 identity/provenance
  mechanism makes later execution truthful. R1 implements none of these;
  Option A + report-only is the R1 behavior.

**Option B — a later invocation may execute an existing PENDING child
with separately truthful execution provenance [PROPOSED — analyzed, NOT
recommended]:**

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
- Option B with stdout-only executor provenance (no field): the record is
  not bound to the row, is lost if the operator does not redirect stdout,
  and cannot be read by the R2 history display — a weaker truthfulness
  story with none of Option A's simplicity.
- Trade accepted by NOT choosing B: orphaned PENDING (non-command
  surface only, zero external outcome) is a reported HOLD in R1 instead of
  an executable row.

**Decision [PROPOSED]: Option A.** It matches frozen DESIGN2 §4.6 option
1, needs no schema change, makes the `operator` field simultaneously
trigger- and execution-truthful on the command path, and confines the
orphan case to the non-command surface where it is inert (zero calls,
machine-guarded).

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

**Recommended: A3.** Exact command flow [PROPOSED] (the §10.2 call graph
is the authoritative form; this is the state-level summary):

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
         If any (PENDING or RUNNING): exit txn -> report IN PROGRESS
         (state, id, operator, created_at/started_at); NO INSERT;
         NO claim; NO executor call; zero network; exit 0.
         (A PENDING child is NEVER claimed or executed by the command —
         M3/§4.6 option 1, hard rule §3.3.)
      c. Read latest terminal child for P (fresh, under lock):
         max(finished_at), tie-break id DESC.
         If it exists AND (now - finished_at) < 300s AND NOT --force-repeat:
             exit txn -> report COOLDOWN REFUSAL (child id, finished_at,
             age); NO INSERT; NO claim; zero network; exit 0.
      d. child = trigger_vendor_refresh(P, operator=op)
         (INSERT PENDING; the UNIQUE constraint remains the hard invariant
         for any writer that does not take the lock)
      e. created = (child.id was not present in the step-b snapshot)   #
         ownership proof under the lock (§3.3)
      f. if created: claim_vendor_refresh(child.id)   # PENDING->RUNNING,
                                                      # same transaction —
                                                      # THE one and only
                                                      # claim of this
                                                      # invocation
         else: IN PROGRESS anomaly report; exit txn;
         NO claim; NO executor call; zero network; exit 0 (fail-closed:
         unreachable under the lock, §3.4 ownership proof)
    COMMIT -> the child is durably RUNNING (command path: no PENDING is
    ever committed alone), BEFORE any network activity.
 3. Post-commit execution (NO open transaction; §10.2 call graph):
      execute_claimed_vendor_refresh_with_default_providers(child.id)
        -> state re-assert (row RUNNING; else bounded, zero calls)
        -> S4 parent load; COMPLETED re-check (defensive) and
           child.requested_mpn == parent.manufacturer_part_number
           (else fail MPN_BINDING_VIOLATION, zero calls)
        -> S5 env check PI_VENDOR_LOOKUP_BASE_URL absent/blank
           (else fail VENDOR_LOOKUP_CONFIG_MISSING, zero calls)
        -> S6 query = CommercialLookupQuery(mpn=child.requested_mpn);
           if query.mpn != child.requested_mpn:
               fail MPN_QUERY_NORMALIZATION_MISMATCH, ZERO calls
               (frozen C7; the captured binding is never rewritten)
        -> S7 adapter = vendor_adapter_factory()   # FIRST construction
           response = adapter.lookup(query)        # THE single lookup
           (outside any transaction; §3.2 zero-construction table)
        -> S8 encoded = bind_and_encode_vendor_lookup(child.requested_mpn,
                                                   response)   # D10 helper
        -> S9 complete_vendor_refresh(child.id, 1, encoded)
   (any bounded post-claim defect -> fail_vendor_refresh(bounded R0_LEGAL
   reason); single outer boundary, §10.2/§10.3)
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
- It is the ONLY claim on the R1 command surface (F1): the post-claim
  executor never re-claims (§3.2); there is no second claim attempt on
  the success path or any other path — the candidate's §10.2 "defensive
  re-assert" re-claim is deleted (it would always fail under the frozen
  PENDING-only CAS).
- It AVOIDS creation of orphaned PENDING rows for normal R1 command
  invocations: crash before commit ⇒ no row (verified rollback §1.6);
  crash after commit ⇒ RUNNING (resolved by M1 or reported HOLD while
  R1-4 is blocked). Orphaned PENDING remains possible only via
  non-command triggers (§3.3).
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

**Precise guarantee (F5-precise) [PROPOSED]:** the safeguard is ATOMIC
with respect to every writer that takes the file write lock — in
particular, no two R1 command invocations can both pass the cooldown
check and both create a child, and no invocation can create a child while
a terminal attempt it would have seen is mid-commit; a refusal commits
nothing and calls nothing (LB-3). Per-invocation claim count: exactly one
on the success path, zero on every other path (§3.2). Lookup count per
child: LB-1/LB-2/LB-3 (§3.2). It is NOT a server-enforced rate limit: a
writer that does not take the lock statement (a bare programmatic
`trigger_vendor_refresh` call, a future R3 web surface, raw SQL) is not
subject to the five-minute window; the hard invariants
(`UNIQUE(parent_run, active_slot)`: at most one active child per parent;
claim CAS: at most one claim winner per child; terminal CAS: at most one
terminal write per child) still bound every writer. This is stated
exactly, per frozen D6: an operator-safety check on the command surface,
clearly distinct from a rate limit.

**Residual risks (enumerated, not hidden) [PROPOSED]:**
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
| 7 | RUNNING → RUNNING (reassignment) | — | — | FORBIDDEN (R0 row 7) |
| 8 | COMPLETED/FAILED → any | — | — | FORBIDDEN (R0 row 8) |
| 9 | RUNNING → terminal by recovery (stale reclaim / threshold / auto-retry / operator-forced interruption via the R0 fail service) | — | — | FORBIDDEN (R0 row 9; F1) |
| 10 | RUNNING → FAILED (`EXECUTION_INTERRUPTED`) | `recover_vendor_refresh_execution` (NEW runs/vendor_refresh_recovery.py) — operator-gated; machine-collected evidence + explicit inventory attestation per §3.1; **implementation BLOCKED at R1-4 pending O8** | state=RUNNING, active_slot=1, finished_at IS NULL | state=FAILED, active_slot=NULL, finished_at set, failure_reason=EXECUTION_INTERRUPTED — ONE UPDATE; identity fields untouched; external Vendor outcome remains explicitly UNKNOWN | **R1 ONLY** — the sole sanctioned writer of the reserved reason |

Row 10 is a row-4-shaped transition with the reserved reason, issued by a
separate primitive, under a separate command, with a separate operator
evidence precondition (§3.1). It is not a modification of row 4, not an
exception to row 9 (row 9 forbids recovery-based terminalization IN R0
and threshold/reclaim-based terminalization in any phase — row 10 is
manual, evidence-gated, non-threshold, and frozen-DESIGN2-sanctioned as
the "separately approved future R1 recovery transition"), and it is the
only additional legal RUNNING→terminal path in R1. While R1-4 is
BLOCKED, row 10 has NO implementing surface: the reserved value remains
rejected by the R0 fail primitive and unwritable by any R1 code.

### 4.2 Lifecycle invariants [PROPOSED]

- **I1** — At most one active (PENDING/RUNNING) child per parent run.
  [Frozen R0; `UNIQUE(parent_run, active_slot)`; holds for ANY writer.]
- **I2** — At most one claim winner per child. [Frozen R0; row-2 CAS.]
- **I3** — At most one terminal write per child; a duplicate or
  cross-terminal attempt affects 0 rows, raises bounded, mutates
  nothing. [Frozen R0; rows 3–4 CAS + row-10 CAS.]
- **I4 (F5-precise)** — AT MOST ONE `InternalVendorAdapter.lookup()`
  invocation per child, and at most one Vendor HTTP request per child
  (LB-1). EXACTLY ONE only when the claim was won by the executing
  invocation, all preflight checks succeeded, and execution reached the
  lookup (LB-2). ZERO adapter constructions and ZERO lookups for claim
  losers, ineligibility, cooldown refusal, config-missing,
  normalization-mismatch, state-re-assert refusals, and every recovery-
  command branch (LB-3, §3.2 table). The at-most bound is a surface
  guarantee of the R1 command surface plus the frozen adapter one-call
  policy; it is NOT claimed against arbitrary privileged writers
  (§3.2). [R1 structure + frozen adapter policy; replaces the candidate's
  "exactly one per successfully claimed child … ever" formulation.]
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
  the Vendor call is strictly post-commit (§3.4 step 3 / §10.2 S7).]
- **I11** — No R1 surface reclaims, resets, retries, reassigns, or
  resurrects any child; no `--reclaim-stale`-style flag exists; the only
  repeat affordance is `--force-repeat` (cooldown bypass, creates a NEW
  child only when allowed); recovery (row 10) is manual, evidence-gated,
  non-repeating (the recovered row is terminal; a new refresh is a new
  child). [R1; frozen D3(b)/D6.]
- **I12** — The runs-layer public API contains exactly the four R0
  vendor-refresh primitives plus (when R1-4 unblocks) the ONE R1 recovery
  primitive and its two bounded error classes (§3.1/§11 row 3 stage 2);
  the `vendor_refresh_claims.py` module surface stays exactly four
  functions. While R1-4 is BLOCKED the public surface is exactly the R0
  one (pinned at the R1-1…R1-3 gates by §11 row 3 stage 1). [R1, pinned
  by §11/§12.]
- **I13 (F2)** — The adapter factory is invoked at most once per
  child, and never before the claim commit, and never on any preflight-
  refusal branch; the construction point is S7 exclusively. The
  `execution/vendor_refresh.py` module imports no provider class in any
  form; `execution/vendor_refresh_runtime.py` is the only R1 module
  importing `providers.internal_vendor`. [R1; §3.2 adapter contract,
  §10.1 AST pins.]

---

## 5. Trigger / claim / execute ownership sequence

The complete R1 normal-path sequence with ownership annotations
[PROPOSED] — §10.2 is the AUTHORITATIVE function-level call graph; this
is its invocation-level projection:

```
INVOCATION = one `python manage.py vendor_refresh <P> --operator <op> [--force-repeat]`
process on the deployment host (authorization: Windows host access,
frozen DESIGN2 §4.2; `op`: self-reported provenance, verbatim).

[S0] parse/validate args                          (no DB, no network)
[S1] informational display read                    (read-only; may be stale)
[S2] BEGIN short write transaction
     [L]  zero-row lock statement                  (acquires RESERVED lock; 0 mutations)
     [R1'] active-children snapshot under lock
     [D1] active child present (PENDING or RUNNING)?
          -> IN PROGRESS report, ABORT (no INSERT; NO claim; zero network)
          (a PENDING child is NEVER claimed/executed by the command — M3)
     [R2'] latest-terminal read under lock
     [D2] within 300 s and not --force-repeat?
          -> COOLDOWN REFUSAL, ABORT (no INSERT; NO claim; zero network)
     [T]  trigger_vendor_refresh(P, operator=op)   (INSERT PENDING; savepoint race path preserved)
     [O]  ownership: returned child.id not in [R1'] -> THIS invocation created it
          (else: anomaly report, ABORT — NO claim; zero network; fail-closed)
     [C]  claim_vendor_refresh(child.id)           (PENDING->RUNNING, same txn)
          THE one and only claim of this invocation. A raise here
          (structurally unreachable) rolls back the whole txn: no row,
          zero calls, bounded non-zero exit. It is NEVER caught to
          continue.
[S3] COMMIT                                        (row durably RUNNING; before ANY network)
[S4'] execution.execute_claimed_vendor_refresh_with_default_providers(child.id)
      (the post-claim executor — it NEVER claims; §10.2 graph)
     [A]  state re-assert: row RUNNING (read-only; else bounded, zero calls)
     [S4] parent load; COMPLETED re-check; requested_mpn == parent MPN
          (violation -> fail MPN_BINDING_VIOLATION, zero construction, zero calls)
     [S5] env PI_VENDOR_LOOKUP_BASE_URL non-blank
          (absent/blank -> fail VENDOR_LOOKUP_CONFIG_MISSING, zero construction, zero calls)
     [S6] query = CommercialLookupQuery(mpn=child.requested_mpn);
          query.mpn != child.requested_mpn -> fail MPN_QUERY_NORMALIZATION_MISMATCH,
          zero construction, zero calls
     [S7] adapter = vendor_adapter_factory()       (FIRST construction; counting-fake
          in tests) ; response = adapter.lookup(query)   (THE single lookup; no open txn)
     [S8] encoded = bind_and_encode_vendor_lookup(child.requested_mpn, response)  (D10 helper)
     [S9] complete_vendor_refresh(child.id, 1, encoded) (single UPDATE)
          -> bounded stdout: COMPLETED (lookup_status=...); exit 0

POST-CLAIM FAILURE PATH (A/S4..S9 defect):
     bounded R0_LEGAL reason r in {MPN_BINDING_VIOLATION, VENDOR_LOOKUP_CONFIG_MISSING,
                                   MPN_QUERY_NORMALIZATION_MISMATCH, RESULT_ENCODING_FAILED,
                                   INTERNAL_ERROR}
     -> fail_vendor_refresh(child.id, r)  (single UPDATE)
     -> raise VendorRefreshExecutionError (bounded)
     -> command stdout: FAILED (reason=r); exit 0 (bounded outcome)
     -> if the complete lost a terminalization race or the fail itself
        cannot persist (DB error): propagate; stdout:
        "terminalization NOT recorded; child remains RUNNING; recovery gate
        reference (R1-4, blocked until O8)"; non-zero exit. Child stays
        RUNNING (I3/I9 intact).

RECOVERY PATH (separate gated command, §3.1; implementation BLOCKED at R1-4):
     operator Class A attestation (single-host inventory) explicit
     -> vendor_refresh_recovery <child-uuid> --operator <op>
          --evidence {reboot|process-scan|operator-stop} --attest-host-inventory
     -> machine-collected evidence at command time (scanner seam; fail-closed)
     -> predicate evaluated in code (non-empty => EVIDENCE_PRESENT refusal, zero mutation)
     -> evidence record written (durable; digest in stdout)
     -> single CAS UPDATE (row 10) -> bounded stdout -> exit
     (a later refresh of P is a NEW child [T..S9]; the recovered child is
     never resumed or reused for a second Vendor call — I4/I9/I11.)
```

Ownership summary (F1): exactly ONE invocation can execute one child —
the creator, under I5/I6; its claim is the invocation's ONE claim (step
[C], inside the serialized transaction); the post-claim executor never
claims and is reachable only in that invocation's own post-commit stack
on the command surface; the claim CAS makes single-ownership true even
for races the lock does not serialize (defense in depth); complete/fail
are issued only by that invocation's stack; losers (snapshot exit) make
zero claim attempts and zero lookups; no R1 module catches a claim
failure to proceed; the only other legal terminalizer is the
evidence-gated recovery primitive (BLOCKED at R1-4), which writes the
reserved reason and never a result, and never a lookup.

---

## 6. Transaction boundaries

| Unit | Contents (statements) | Network? | Adapter construction? | Max duration class | Failure behavior |
|---|---|---|---|---|---|
| Command serialized txn (S2–S3) | lock stmt (0-row UPDATE); active-children SELECT; latest-terminal SELECT; INSERT (trigger, own savepoint); claim UPDATE (the only claim) | NO | none | milliseconds | any error before COMMIT → full rollback → zero mutation (verified §1.6); `OperationalError: database is locked` at the lock stmt if contention > busy timeout (5 s) → bounded, non-zero exit, zero mutation |
| Post-commit state re-assert (A) | child SELECT | NO | none | trivial | row not RUNNING → bounded error, zero construction, zero calls, no mutation |
| Config/binding/normalization checks (S4–S6) | parent SELECT; env read; in-memory string compare | NO | none | trivial | → bounded fail UPDATE (below) |
| Vendor call (S7) | factory invocation (FIRST construction) + ONE GET (frozen adapter policy: 10 s socket timeout, 1 MiB bound, no retries) | YES — outside every transaction | exactly once | ≤ ~10 s + scheduling | transport failure → bounded FAILED RESPONSE (not exception) → normal completion with lookup_status=FAILED; `ValueError` in `_ensure_configured` (malformed non-blank URL) → raises before any HTTP request (0 requests) → INTERNAL_ERROR fail path; factory raising → no object → INTERNAL_ERROR fail path |
| Binding/encode (S8) | in-memory | NO | none | trivial | codec error → RESULT_ENCODING_FAILED fail path |
| complete (S9) | single UPDATE | NO | none | trivial | 0 rows → bounded error, zero mutation; DB error → propagate, child stays RUNNING |
| fail (any) | single UPDATE | NO | none | trivial | same as complete |
| Recovery CAS (row 10; BLOCKED at R1-4) | single UPDATE | NO | none (no factory exists in the recovery path) | trivial | 0 rows → re-read → bounded report (actual terminal shape), zero mutation |

No statement of any R1 path holds a transaction open across S7; the
adapter factory is never invoked inside a transaction. [PROPOSED
invariants I10/I13; mirrors frozen 4C-B "call the provider outside
transactions" and DESIGN2 §3.6.]

---

## 7. Crash and recovery decision matrix

Legend: `W` = window; `row` = durable child shape after the event;
`API` = Vendor lookups made by that attempt (LB-precise: ≤1 per child,
§3.2); `resolution` = who/what legally acts next. All windows assume the
R1 command path (combined txn); non-command trigger windows noted where
different.

| W | Event | Row after | API | Parent/original artifacts | Resolution |
|---|---|---|---|---|---|
| W1 | crash inside serialized txn (lock stmt / INSERT / claim), before COMMIT | NO ROW (rollback) | 0 | untouched (I7) | nothing to do; next invocation is normal |
| W2 | crash after COMMIT (S3), before A (state re-assert) | RUNNING | 0 | untouched | recovery gate (R1-4; BLOCKED pending O8 — while blocked: permanent reported HOLD, §3.1) → row 10 → new attempt later. (Uniform UNKNOWN semantics, §3.3.) |
| W3 | crash during A–S6 checks (post-claim, pre-call; checks would have failed) | RUNNING (if crash before the fail UPDATE commits) | 0 | untouched | recovery gate as W2. (If the fail UPDATE committed first: FAILED bounded reason; no crash state.) |
| W4 | crash during the Vendor call (S7) | RUNNING | ≤1 in flight, outcome unknown | untouched | recovery gate as W2. External outcome stays UNKNOWN; a later NEW attempt is new evidence, never a rewrite. |
| W5 | crash after response received, before encode/complete (S8/S9) | RUNNING | 1 (LB-2 reached the lookup) | untouched | recovery gate as W2. |
| W6 | crash during the complete UPDATE commit | COMPLETED (durable) if commit won, else RUNNING (rollback) | 1 | untouched | COMPLETED: done. RUNNING: recovery gate. |
| W7 | crash during the fail UPDATE commit | FAILED if commit won, else RUNNING | ≤1 | untouched | FAILED: done. RUNNING: recovery gate. |
| W8 | DB failure during S9/S-fail (not a crash) | RUNNING (UPDATE did not commit) | 1 | untouched | command prints "terminalization NOT recorded"; recovery gate later (HOLD while blocked). (Frozen DESIGN2 §9 row 8 shape.) |
| W9 | crash of the RECOVERY command (post-unblock) mid-flow | FAILED(row 10) if the CAS commit won, else RUNNING | (original attempt's) unknown | untouched | record reflects the outcome (or the collection-failure refusal); re-run after fresh evidence (evidence is re-collected at command time — never reused); or original-execution completion wins the race (W11). |
| W10 | (non-command trigger only) crash after PENDING INSERT, before any claim | PENDING | 0 | untouched | reported IN PROGRESS by every command; never claimed/executed by R1 (M3 hard rule + executor state re-assert refuses PENDING); resolution [OPEN-O3]. Safe: zero external outcome. |
| W11 | recovery race: original process completes (row 3) concurrently with recovery CAS (row 10) | exactly one terminal write; the other affects 0 rows | 1 | untouched | loser re-reads and reports the ACTUAL terminal shape; interruption is never recorded over a real result (I3). NOTE: W11 prevents double TERMINALIZATION — it does NOT prevent an overlapping second LOOKUP when the original was still alive (that is W12; only the evidence gate addresses it). |
| W12 | premature recovery: row 10 commits while the original process is STILL ALIVE (false/erred evidence) | FAILED(row 10) | original ≤1 in flight + a NEW child may then be triggered | untouched | the original's later complete/fail loses the CAS and reports (W11 shape); a subsequent normal command creates child 2 and issues lookup 2 CONCURRENTLY with the original's in-flight lookup 1 — an overlapping Vendor request. NO database mechanism prevents this (child 2 is a fresh legitimate row once child 1 is terminal); the ONLY protection is the §3.1 evidence gate (machine predicate at command time + explicit inventory attestation + O8 after-the-fact cross-check). Unreachable from the R1 surface while R1-4 is BLOCKED (no row-10 writer exists). This is why the gate is blocked rather than shipped on an attestation token alone. |

Invariants across all windows: I1–I13 hold; a crashed attempt can never
produce a second Vendor call (I4/LB-1); no window rewrites any historical
row (I7/I9); a RUNNING row always blocks new attempts for its parent (safe
direction) until row 3, row 4, or evidence-gated row 10 terminalizes it
(row 10 unavailable while R1-4 is BLOCKED — the block is the safe
direction: it delays resolution, never risks overlap).

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
- **Deployment prerequisite (frozen, blocking for DEPLOYMENT of R1-1…R1-3;
  ADDITIONALLY the R1-4 unblock condition — §3.1/§14):** the explicit
  host permissions and operational audit review (host/CMD account
  inventory, command-logging posture, database file + directory ACLs,
  runbook controls) must be completed and recorded. For R1-4 the review
  additionally verifies: administrator process-table visibility (the
  scanner seam's premise), the CANONICAL launch form as the only
  documented way to start a refresh (the §3.1 predicate's soundness
  premise), and the evidence retention location/duration for recovery
  records. [OPEN-O8 tracks it.]
- `--operator` (mandatory, 1..128, verbatim, content-free errors) is
  **self-reported provenance, NOT authentication** (frozen D4(b)). Shared
  administrative accounts reduce attribution; `--operator` mitigates,
  never solves. No OS environment value (`USERNAME` etc.) is trusted or
  recorded (frozen: no OS-context column).
- The recovery command additionally carries `--evidence
  {reboot|process-scan|operator-stop}` (the attested class, machine-
  cross-checked against the collected evidence, §3.1) and the REQUIRED
  `--attest-host-inventory` flag (the explicit Class A attestation — the
  command refuses without it; asserting it dishonestly is the O8
  command-log cross-check's job to catch). The recovery command's
  machine-collected evidence, evidence record path, and record SHA-256
  digest appear in its bounded stdout for the host audit.

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
  manual terminalization (recovery command, post-unblock); semantics
  frozen (I8): outcome UNKNOWN. The evidence itself is NOT in the row —
  it is in the retained evidence record (digest-anchored by the stdout
  line) + the host command log (Class H, §3.1).
- Execution-provenance beyond the row (evidence class, scan instant,
  invocations) lives in the bounded stdout, the retained record, and the
  host operational audit — NOT in the schema (frozen no-new-field
  default; §3.3).

### 8.3 Bounded stdout contract (both commands) [PROPOSED]

Always bounded; no secrets; no raw exception text; no raw private Vendor
response content; no base URL; no full process-table dump (the record
carries only the predicate-matching rows — expected empty — plus the
total count). Per-child lines carry: child id, parent run id, state,
recorded operator, relevant timestamps, bounded reason / lookup_status
vocabulary values, and the command's own outcome class. Exit codes:
0 for bounded outcomes (success, in-progress, cooldown refusal, already-
terminal, recovery RECOVERED); non-zero for ineligibility (bad UUID,
missing operator, parent ineligible) and every recovery REFUSAL
(evidence present, collection failed, store unavailable, pending row,
not found — a refusal alerts the operator that the row remains RUNNING
and needs follow-up) and unexpected errors (DB busy/locked, programming
error, terminalization-not-recorded). This mirrors the frozen DESIGN2
§10.3(5) exit-code contract and the `pilot_check` precedent.

Normal command outcome classes: CREATED_EXECUTED / IN_PROGRESS (incl.
the [O] anomaly, labeled) / COOLDOWN_REFUSAL / COMPLETED / FAILED /
TERMINALIZATION_NOT_RECORDED / DATABASE_BUSY / INELIGIBLE.
Recovery command outcome classes (post-unblock; §3.1): RECOVERED_
EXECUTION_INTERRUPTED / EVIDENCE_PRESENT / REBOOT_ORDER_VIOLATED /
EVIDENCE_COLLECTION_FAILED / EVIDENCE_STORE_UNAVAILABLE /
ALREADY_TERMINAL (actual shape reported) / PENDING_ROW / NOT_FOUND. The RECOVERED and refusal lines carry: child
id, parent id, evidence class, host name, scan instant, predicate
result, record path, record SHA-256 digest, `--operator`.

---

## 9. SQLite race / interleaving analysis (task §6 cases)

All cases analyzed against the §3.4 flow (serialized txn A3) and the
VERIFIED semantics of §1.6. "Cmd" = an R1 command invocation. Lookup
counts are LB-precise (§3.2).

1. **Two simultaneous invocations, no child exists.**
   Cmd-A acquires the RESERVED lock at its zero-row statement; Cmd-B
   blocks there (busy-wait ≤ 5 s). A: snapshot empty → no cooldown
   blocker → INSERT+claim (its ONE claim) → COMMIT (child RUNNING) →
   executor → exactly one lookup (LB-2) → COMPLETED. B: lock released,
   B's statement runs (0 rows), B's fresh snapshot sees A's RUNNING
   child (or, if A already terminalized, the terminal history feeds the
   cooldown decision) → IN PROGRESS report (or COOLDOWN REFUSAL) → no
   claim attempt → zero lookups (LB-3, sentinel-proven).
   **Result: exactly one child; exactly one lookup total (the winner
   reached the lookup); zero claims and zero lookups for the loser.
   Closed.**
2. **Second invocation while the first is PENDING.**
   On the command path a PENDING row is never committed alone (I5) — a
   PENDING child seen by a second Cmd came from a non-command trigger.
   Second Cmd: snapshot under lock sees the active (PENDING) child →
   IN PROGRESS report (identifies id, recorded operator, created_at) →
   no claim, no execution, no INSERT, zero lookups. **An existing PENDING
   is never silently executed by the normal command** (M3 hard rule,
   §3.3; machine-guarded by the executor's PENDING refusal). Option A:
   the orphan is a reported HOLD. **Closed (honest report).**
3. **Second invocation while the first is RUNNING.**
   Same as case 2: snapshot under lock sees the active RUNNING child →
   IN PROGRESS report → zero claims, zero lookups. The RUNNING row keeps
   occupying the slot (frozen rule). **Closed.**
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
   retroactively invalidate it (different rows; append-only).
   **Closed — the decision always reads the latest committed state.**
5. **Two invocations both observe terminal history outside the cooldown
   window.**
   Both pass the cooldown, but only ONE can INSERT: Cmd-A commits its
   child (RUNNING) under the lock; Cmd-B blocks, then sees the active
   child → IN PROGRESS → no second INSERT. **Result: exactly one new
   child; exactly one lookup (the winner, LB-2); the 5-minute rule
   governs post-terminal spacing; the active-slot invariant governs
   duplication — both hold. Closed.**
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
   changed 0 rows by construction) → zero claims, zero lookups →
   bounded "DATABASE BUSY — no state changed — re-run" → non-zero exit →
   NO automatic retry (frozen no-retry stance; a manual re-run is a new
   explicit invocation). A >5 s holder is practically unreachable on this
   deployment (command txns are milliseconds with no I/O; the only other
   writers are short Waitress web transactions and manual operations) —
   noted as residual (a), §3.4. **Bounded. Closed.**
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
   waiting (lock is free) and reports IN PROGRESS over the RUNNING row
   (zero claims, zero lookups). **Closed; no wedge, no corruption.**

Additional interleavings (not in the mandated list, analyzed for
completeness):

- **A. Cmd + programmatic trigger racing (no lock-taker on the programmatic
  side):** the programmatic INSERT is a write — it serializes behind the
  Cmd's RESERVED lock; after the Cmd commits (child RUNNING), the
  programmatic trigger's own pre-check finds the active child (concept 1
  return) or its INSERT hits `UNIQUE` → winner returned. At most one
  active child (I1). **Bounded.**
- **B. Two non-R1-surface sequences (programmatic claim + post-claim
  executor) on the same PENDING child:** the claim CAS admits exactly one
  winner; the loser's claim raises `VendorRefreshClaimError` — a
  failure that is NEVER caught to proceed (F1 no-bypass rule; §12 row
  19) — so the loser never reaches the executor: one lookup total
  (LB-1/LB-2 for the winner; LB-3 for the loser). (The R1 command
  surface has no such path at all — its claim is inside its own
  transaction; this case bounds hypothetical/future non-command users.)
  **Bounded.**
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

**Aggregate guarantee (restated, F5-precise):** on the R1 command
surface, the serialized transaction makes the safeguard decision, child
creation, and claim acquisition atomic with respect to all file-lock-
taking writers; per invocation the claim count is exactly one (success)
or zero (every other path); per child the lookup count obeys
LB-1/LB-2/LB-3 (§3.2); refusals and reports commit nothing, claim
nothing, and call nothing. The frozen hard invariants (I1–I3) bound
every writer including non-locking ones.

---

## 10. Provider boundary and helper extraction map

### 10.1 Module map [PROPOSED]

| Module (path) | Content | Import allowlist (pinned by new AST guards, §12) |
|---|---|---|
| `product_intelligence/execution/vendor_refresh.py` (NEW; R1-2) | `execute_claimed_vendor_refresh(child_id, *, vendor_adapter=None, vendor_adapter_factory=None) -> VendorRefreshExecution` — the POST-CLAIM execution body (§3.2 contract: state re-assert; S4–S6 preflight; S7 factory+lookup; S8 encode; S9 complete; single outer boundary — bounded defect → `fail_vendor_refresh(R0_LEGAL reason)` + raise `VendorRefreshExecutionError`; DB-unrecordable fail → propagate + row stays RUNNING). `VendorRefreshExecutionError` (bounded, execution-layer, mirrors `ComparableResearchExecutionError` L116). **NO claim: the module does not reference `claim_vendor_refresh` in any form (AST-pinned, §12 row 19) and catches no claim/terminal CAS error for control flow.** | `product_intelligence.runs` PUBLIC symbols only (complete/fail + bounded errors + model for the state re-assert); `product_intelligence.execution.vendor_commercial_binding` (the D10 helper); `product_intelligence.providers.commercial` (`CommercialLookupQuery`, `LookupStatus` — the network-free contract types, as the frozen 4D-B orchestration does); `os` (env read of `PI_VENDOR_LOOKUP_BASE_URL`); stdlib. **NO import of `providers.internal_vendor` in any form** (I13/AST); the adapter arrives ONLY as a parameter (instance or zero-arg factory). NO web, NO research.identity direct (2A happens inside the helper), NO fx, NO semantic, NO comparable, NO search, NO page fetch. |
| `product_intelligence/execution/vendor_refresh_runtime.py` (NEW; R1-2) | `execute_claimed_vendor_refresh_with_default_providers(child_id)` — thin command-stack entry: supplies the concrete `InternalVendorAdapter` CLASS as the `vendor_adapter_factory` (function-level import — the ONLY R1 module importing `providers.internal_vendor`; DESIGN2 §3.5 placement preserved) and delegates ONCE. **Constructs nothing itself** (O9: deliberate deviation from `comparable_runtime.py`'s eager construction — §3.2). | `product_intelligence.execution.vendor_refresh`; `product_intelligence.providers.internal_vendor` (adapter class only, function-level). |
| `product_intelligence/execution/vendor_commercial_binding.py` (NEW; R1-1 — D10 helper) | `bind_and_encode_vendor_lookup(requested_mpn: str, response) -> dict` — the moved 4D-B binding/encoding policy: per-candidate frozen 2A `compare_part_numbers` (EXACT/NORMALIZED_EXACT → `SupplementSourceObservation(brand_new=True, brand_new_basis="VENDOR_API_POLICY")`; else `SupplementSourceIssue(MPN_MISMATCH, "vendor_mpn_mismatch")`); provider issues copied bounded (detail=None); final status mapping (transport FAILED → `"FAILED"` + `retrieved_at=None`; else `response.status.value` + `response.retrieved_at`); `ResearchSupplementResult` construction + `encode_research_supplement_result`; `SupplementCodecError` propagates | `product_intelligence.research.identity` (`compare_part_numbers`); `product_intelligence.research.commercial_supplement_codec` (dataclasses + encoder); `product_intelligence.providers.commercial` (`LookupStatus`); stdlib. Pure function: no DB, no env, no network, no adapter import. |
| `product_intelligence/execution/orchestration.py` (MODIFIED — behavior-identical; R1-1) | `_try_vendor_commercial_lookup` (L1124–1257) keeps: config check, query build, ONE adapter call; the step-6/7 binding+encode block is REPLACED by a call to `bind_and_encode_vendor_lookup(request.manufacturer_part_number, response)`. No other orchestration line changes. | existing + `product_intelligence.execution.vendor_commercial_binding` |
| `product_intelligence/execution/__init__.py` (MODIFIED; R1-2) | exports exactly `execute_claimed_vendor_refresh`, `execute_claimed_vendor_refresh_with_default_providers`, `VendorRefreshExecutionError` (exact set pinned by a new adversarial node; the web allowlist `ALLOWED_EXECUTION_IMPORTS` is UNCHANGED in R1 — web imports none of these) | — |
| `product_intelligence/runs/vendor_refresh_recovery.py` (NEW; R1-4 **[BLOCKED pending O8]**) | `recover_vendor_refresh_execution(child_id, *, at=None)` — the row-10 CAS + bounded 0-row re-read reporting (§3.1); the evidence machinery: `scan_process_table` / `read_boot_time` (the scanner seam — production: single bounded read-only PowerShell/CIM invocations, 60 s timeout, fail-closed), `evaluate_scan_predicate` (PURE predicate over recorded rows: signature substring + creation window; §3.1), `build_evidence_record` / `write_evidence_record` (schema v1, §3.1; digest returned). Module docstring carries the pinned attestation-limit statement (F3: the software verifies structure/collection, NEVER proves termination — §12 row 8). Honest naming (F4): the module and primitive carry their true recovery function; the R0 guard is evolved in place with the strict allowlist (§11 row 3), NOT evaded by token-free names. | `django.db`/`timezone`; `product_intelligence.runs.models` (model + vocabularies); `product_intelligence.runs.errors`; stdlib (`subprocess`, `json`, `uuid`, `datetime`, `pathlib`, `socket`, `hashlib`). NO providers, NO research, NO web, NO execution. The PowerShell reference command forms (O1) are the only host-specific content; verified token-free w.r.t. the runs CALLER/VENDOR token scans (§1.3/§1.7). |
| `product_intelligence/runs/errors.py` (MODIFIED — additive; R1-4) | appends `VendorRefreshRecoveryError` (reasons `already_terminal` / `pending_row` / `not_found`) and `VendorRefreshRecoveryEvidenceError` (bounded evidence-refusal reasons, §3.1) under the existing VREF section; no existing class/signature changes | — |
| `product_intelligence/runs/__init__.py` (MODIFIED — additive; R1-4) | `_VENDOR_REFRESH_R1_EXPORTS` frozenset + `__all__` entries + lazy `__getattr__` branch for EXACTLY: `recover_vendor_refresh_execution`, `VendorRefreshRecoveryError`, `VendorRefreshRecoveryEvidenceError` (the strict R1 allowlist, §11 row 3 stage 2; token-bearing names are the point — F4) | — |
| `product_intelligence/runs/management/commands/vendor_refresh.py` (NEW; R1-3) | the normal command: args (1 positional PARENT run UUID; `--operator` required; `--force-repeat` optional — NO child-id positional, NO other flags), informational display, serialized txn (§3.4) — the ONLY claim call site in R1 — post-commit execution via the runtime entry, bounded stdout, exit codes (§8.3) | `django.core.management`; `product_intelligence.runs` public (trigger/claim + errors + model for display); `product_intelligence.execution` public (`execute_claimed_vendor_refresh_with_default_providers`, `VendorRefreshExecutionError`); stdlib (`os`, `uuid`, `datetime`). NO providers import (the per-file INNER_ROOTS guard will scan this file — §11), NO web import. |
| `product_intelligence/runs/management/commands/vendor_refresh_recovery.py` (NEW; R1-4 **[BLOCKED pending O8]**) | the recovery command: args (1 positional CHILD UUID; `--operator` required; `--evidence` required, choices `{reboot, process-scan, operator-stop}`; `--attest-host-inventory` required; nothing else), read-only row pre-check, machine evidence collection at command time (scanner seam), predicate evaluation, evidence record write (deployment-owned env `PI_VENDOR_RECOVERY_EVIDENCE_DIR` — absent/unwritable ⇒ bounded refusal, zero mutation), the row-10 CAS, bounded stdout incl. record path + SHA-256 digest (§8.3), exit codes. Zero adapter, zero lookup, in every branch. | same discipline as the normal command minus the execution import; additionally `product_intelligence.runs.vendor_refresh_recovery` (in-package evidence machinery), `os` (env dir), `socket` (host name). NO providers, NO web, NO execution. |

Layer-direction note [PROPOSED, flagged]: the management commands live in
`runs/management/commands/` per frozen DESIGN2 §3.5 placement, and the
NORMAL command imports the `execution` public API — an outer-surface
(operational entry-point) import direction, analogous to `web` importing
`execution`. No existing guard pins "runs services must not import
execution" [VERIFIED: no such test; no runs source file currently
imports execution]. R1 ADDS a guard pinning the exact permitted form: no
module in `runs/` EXCEPT `runs/management/commands/vendor_refresh.py`
may import `product_intelligence.execution` (the recovery command
imports no execution surface at all — §12 row 15). [OPEN-O4 approves the
carve-out + guard.]

### 10.2 THE single authoritative call graph [PROPOSED] (F1)

This section is the ONE authoritative command-to-execution call graph for
R1. §5 is its invocation-level projection; no other graph, sequence, or
"defensive re-claim" exists anywhere in the design. Signatures are as in
§3.2.

```
NORMAL COMMAND  (runs/management/commands/vendor_refresh.py)
handle(parent_run_uuid: str, *, operator: str, force_repeat: bool)
 │  [S0] parse/validate (uuid parse; operator 1..128)            — no DB, no network
 │  [S1] informational display read (read-only, may be stale)
 │  [S2] with transaction.atomic():                              — SHORT write txn
 │        [L]  VendorRefreshExecution.objects.filter(
 │                 parent_run_id=P, active_slot=2).update(active_slot=2)
 │             # zero-row; acquires the file RESERVED lock; mutates NOTHING
 │        [b]  active_children = parent's active children (fresh, under lock)
 │        [D1] active_children non-empty (PENDING or RUNNING)
 │             → bounded IN PROGRESS report → EXIT 0
 │             # NO trigger, NO claim, NO executor, zero network (LB-3)
 │        [c]  latest_terminal = max(finished_at), tie-break id DESC (fresh)
 │        [D2] latest_terminal within 300 s and not force_repeat
 │             → bounded COOLDOWN REFUSAL report → EXIT 0
 │             # NO trigger, NO claim, NO executor, zero network (LB-3)
 │        [d]  child = runs.trigger_vendor_refresh(P, operator=operator)
 │             # R0 primitive; INSERT (own savepoint); eligibility re-checked
 │        [O]  if child.id in {a.id for a in active_children}:
 │             → bounded IN PROGRESS (anomaly) report → EXIT 0
 │             # NO claim, NO executor, zero network (fail-closed;
 │               unreachable under the lock — §3.4 ownership proof)
 │        [f]  runs.claim_vendor_refresh(child.id)
 │             # R0 primitive — THE ONE AND ONLY CLAIM of this invocation
 │             # (exactly one on success; zero on every other path)
 │             # a raise here (structurally unreachable) propagates OUT of
 │             # the atomic block → total rollback → no row, zero calls,
 │             # bounded non-zero exit. It is NEVER caught to continue.
 │  [S3] COMMIT                                                   — child durably RUNNING;
 │                                                                    NO network yet (I10)
 │  [S4'] execution.execute_claimed_vendor_refresh_with_default_providers(child.id)
 └────────┬──────────────────────────────────────────────────────  (public execution API)
         ▼
RUNTIME  (execution/vendor_refresh_runtime.py)
execute_claimed_vendor_refresh_with_default_providers(child_id)
 │  function-level import of InternalVendorAdapter (the ONLY R1 module
 │  that imports the concrete provider class — DESIGN2 §3.5 placement)
 └─▶ execution.vendor_refresh.execute_claimed_vendor_refresh(
         child_id, vendor_adapter_factory=InternalVendorAdapter)
         # constructs NOTHING itself; passes the class as the factory

EXECUTION CORE  (execution/vendor_refresh.py)
execute_claimed_vendor_refresh(child_id, *, vendor_adapter=None,
                               vendor_adapter_factory=None)
 │  precondition (documented authority, §3.2): the caller is the
 │  invocation that won the claim CAS for child_id
 │  argument discipline: exactly one of vendor_adapter /
 │  vendor_adapter_factory (neither/both → adapter_argument_conflict,
 │  zero calls)
 │  [A]  state re-assert (READ-ONLY): row exists, state=RUNNING,
 │       active_slot=1, finished_at IS NULL
 │       else → VendorRefreshExecutionError(state_not_found /
 │       state_not_running) — zero construction, zero lookup, NO claim,
 │       NO terminal write (a PENDING orphan is machine-refused here — M3)
 │  # THIS FUNCTION NEVER CALLS claim_vendor_refresh (AST-pinned, row 19);
 │  # no R1 module catches a claim/terminal CAS error to proceed
 │  [S4] parent = load parent_run
 │       parent COMPLETED re-check (defensive)
 │       child.requested_mpn == parent.manufacturer_part_number
 │       else → fail MPN_BINDING_VIOLATION → raise
 │  [S5] os.environ PI_VENDOR_LOOKUP_BASE_URL present and non-blank
 │       else → fail VENDOR_LOOKUP_CONFIG_MISSING → raise
 │  [S6] query = CommercialLookupQuery(mpn=child.requested_mpn)
 │       query.mpn == child.requested_mpn (exact string equality; C7)
 │       else → fail MPN_QUERY_NORMALIZATION_MISMATCH → raise
 │  [S7] adapter = vendor_adapter_factory()      # FIRST and ONLY construction (I13)
 │       response = adapter.lookup(query)        # THE single lookup (LB-1/LB-2)
 │       # outside any transaction (I10)
 │  [S8] encoded = vendor_commercial_binding.bind_and_encode_vendor_lookup(
 │            child.requested_mpn, response)     # D10 helper; pure
 │       # SupplementCodecError → fail RESULT_ENCODING_FAILED → raise
 │  [S9] runs.complete_vendor_refresh(child.id, 1, encoded)
 │       # 0-row terminalization race / DB error →
 │       #   VendorRefreshExecutionError(terminalization_not_recorded),
 │       #   row stays RUNNING, no mutation
 └─────── SINGLE OUTER BOUNDARY (post-claim): any bounded defect
         maps to ONE R0_LEGAL fail reason + fail_vendor_refresh +
         raise VendorRefreshExecutionError; if the fail itself cannot
         persist → propagate (row stays RUNNING; command prints
         TERMINALIZATION_NOT_RECORDED, non-zero exit)

RECOVERY COMMAND  (runs/management/commands/vendor_refresh_recovery.py)
handle(child_uuid: str, *, operator: str, evidence: str,
       attest_host_inventory: bool)
 │  [S0'] parse/validate (uuid; operator; --evidence ∈
 │        {reboot, process-scan, operator-stop}; --attest-host-inventory
 │        REQUIRED — absent ⇒ parser error, zero DB)
 │  [S1'] row read (read-only): absent → NOT_FOUND; PENDING → PENDING_ROW
 │        (M3: the gate is RUNNING-only, never terminalizes orphans);
 │        terminal → ALREADY_TERMINAL (actual shape reported); zero writes
 │  [S2'] machine evidence collection AT COMMAND TIME (scanner seam):
 │        reboot → read_boot_time(); boot < started_at → REBOOT_ORDER_VIOLATED
 │        refusal. process-scan / operator-stop → scan_process_table()
 │        (60 s timeout; ANY failure → EVIDENCE_COLLECTION_FAILED,
 │        fail-closed, zero mutation); evaluate_scan_predicate(rows,
 │        parent_run_id, started_at, tolerance_seconds=60) non-empty →
 │        EVIDENCE_PRESENT refusal (the original may be alive —
 │        recovery DENIED; denial only ever delays, §3.1)
 │  [S3'] evidence record written (schema v1, §3.1) to
 │        PI_VENDOR_RECOVERY_EVIDENCE_DIR (absent/unwritable →
 │        EVIDENCE_STORE_UNAVAILABLE, zero mutation; the record carries
 │        the collection outcome incl. refusals — denials are audited)
 │  [S4'] runs.vendor_refresh_recovery.recover_vendor_refresh_execution(child.id)
 │        # row-10 CAS (single conditional UPDATE; the ONLY R1 writer of
 │        # EXECUTION_INTERRUPTED — AST-pinned, §12 row 9)
 │        # 0 rows → re-read → ALREADY_TERMINAL (actual shape), zero mutation
 └─────── bounded stdout: outcome class + child/parent ids + evidence
         class + host + scan instant + record path + record SHA-256
         digest + operator (§8.3). ZERO adapter, ZERO lookup, EVERY branch.
```

**Graph properties (pinned by §12):** (1) exactly one claim call site in
R1 — the normal command's [f]; (2) the execution core and runtime never
claim; (3) no R1 module catches a claim/terminal CAS error for control
flow (a CAS failure is always terminal for the invocation that hit it);
(4) the network call site is unique — core [S7], strictly post-commit
and post-preflight; (5) the recovery path shares NO node with the
execution path (no factory, no lookup, no execution import); (6) every
exit path is LB-classified (§3.2 table).

### 10.3 Expected behaviors (task §7) [PROPOSED]

- **Malformed wire payload** (non-JSON / non-UTF-8 / malformed section /
  oversized / unrecognized contract): the frozen adapter RETURNS a
  bounded `CommercialSourceResponse(status=FAILED or PARTIAL-with-issues)`
  — it does not raise (VERIFIED adapter contract). The refresh completes
  the child as **COMPLETED** with `lookup_status=FAILED` (or PARTIAL) —
  an executed lookup with a failed/partial RESULT, exactly the 4D-B
  semantics (frozen case E). LB-class: factory 1, `lookup()` 1, HTTP
  request 1 (the failed one), complete. No execution-machinery failure;
  no `INTERNAL_ERROR`.
- **Provider programming exception** (adapter raises — e.g. `ValueError`
  from `_ensure_configured` on a malformed (non-blank) base URL, or an
  internal bug): single outer boundary → `fail_vendor_refresh(
  INTERNAL_ERROR)` → `VendorRefreshExecutionError`. Distinct from
  transport FAILED (which is a RESULT). Note the config split, exactly
  LB-classified: ABSENT/BLANK base URL → bounded
  `VENDOR_LOOKUP_CONFIG_MISSING` (pre-adapter, factory 0, `lookup()` 0,
  HTTP 0); MALFORMED non-blank base URL → S5 passes (non-blank), the
  factory IS invoked (1 construction — verified side-effect-free, §1.7),
  `lookup()` raises `ValueError` at its FIRST statement
  (`_ensure_configured`) before any `Request`/`opener.open` →
  `lookup()` 1 (raised), **HTTP requests 0** → `INTERNAL_ERROR` after
  the adapter surfaces it (the bounded reason does not overclaim; display
  stays vocabulary-bound); FACTORY ITSELF RAISING (construction failure)
  → factory 1 (failed), no object, `lookup()` 0, HTTP 0 →
  `INTERNAL_ERROR`.
- **Database failure** (locked/IO during the serialized txn): full
  rollback, zero claims, zero lookups, bounded "DATABASE BUSY/ERROR — no
  state changed", non-zero exit (W1). During complete/fail (W8): child
  stays RUNNING, bounded "terminalization NOT recorded" stdout, non-zero
  exit, recovery gate (R1-4) is the only later path (HOLD while blocked).
- **Lost terminalization race** (row 3 vs row 10, or row 3 vs row 4):
  the CAS admits exactly one terminal write (I3); the loser re-reads and
  reports the actual terminal shape with zero mutation (W11); recovery
  never records an interruption over a real result. NOTE (W12): a lost
  race prevents double TERMINALIZATION only — it cannot prevent an
  overlapping second LOOKUP issued by a still-alive original; that is the
  evidence gate's job (§3.1), not a CAS property.
- **Frozen contracts preserved (LB-precise, F5):** AT MOST ONE
  `lookup()` per child and AT MOST ONE Vendor HTTP request per child
  (LB-1); EXACTLY ONE `lookup()` (and one HTTP request, modulo a
  transport failure that returns a bounded FAILED response after that
  single request) ONLY when claim ownership + all preflight checks
  succeed and execution reaches the lookup (LB-2); ZERO adapter
  constructions and ZERO `lookup()` calls for claim losers,
  ineligible triggers, cooldown refusal, config-missing,
  normalization-mismatch, state-
  re-assert refusals, and every recovery-command branch (LB-3, §3.2
  table). The EXACT captured canonical MPN is the query binding
  (`query.mpn == child.requested_mpn` enforced, fail-closed, never
  silently altered); provider transport FAILED is a COMPLETED result,
  not a machinery failure; MPN binding / source mapping / availability /
  zero-price semantics unchanged (same helper, same frozen codec V1,
  same `VENDOR_API_POLICY` basis); full codec encoding happens BEFORE
  the complete CAS (and the R0 complete service still validates the
  bounded V1 agreement pre-UPDATE); no FX lookup, no provider search, no
  semantic matching, no comparable execution, no price-authority
  promotion; ResearchRun + all original artifacts unchanged (I7); no
  network inside a DB txn (I10); no adapter construction before the
  claim commit or on any preflight-refusal branch (I13); bounded stdout
  without secrets or raw private Vendor responses (§8.3); no new Web POST
  or Django authentication (§2.2).

---

## 11. Existing test-contract evolution plan (task §8)

**Preservation baseline** [VERIFIED §1.5/§1.7]: 5,959 production nodes
(cde2a80) and 6,082 frozen R0 nodes (3983db4). R1 must preserve ALL
6,082 except the nodes below whose literal R0-only assertions are
intentionally phase-specific; every replacement preserves or strengthens
the original safety invariant; at the named implementation gate ChatGPT
approves each stage explicitly. **No deletion, no rename (node
collection identity is preserved at every stage), no skip, no xfail, no
deselection, no weakening anywhere; all other changes are additions.**
**No test modification is made by THIS design task** — the evolutions
below are PROPOSED staged bodies for the implementation gates; the
candidate's token-free-naming strategy (F4) is rejected: R1 surfaces
carry their true names, and the guard that would have been evaded is
evolved in place under a strict allowlist instead.

The R0 nodes are in `tests/runs/test_vendor_refresh_claims.py` (115
nodes). THREE nodes in `TestNoRecoverySurface` collide with R1's
mandated surface; each evolves IN PLACE (same node ID; docstring
corrected; body staged per substep so it is green at every gate).

| # | Original node (line at 3983db4) | Original meaning | Evolved body — staged (PROPOSED) | Original safety intent preserved | New adversarial R1 regression coverage |
|---|---|---|---|---|---|
| 1 | `TestNoRecoverySurface::test_no_vendor_refresh_management_command_exists` (L1446) | "R0 ships no command surface: no `vendor_refresh*` file in `runs/management/commands`" | **Stage A (approved at the R1-3 gate):** assert the EXACT set of `vendor_refresh*` files in `runs/management/commands` == `{vendor_refresh.py}` (exact membership — the recovery command does NOT exist yet, R1-4 BLOCKED; any other file fails); parse the normal command's argument parser: exactly 1 positional (PARENT run UUID) and exactly the flags `--operator` (required) and `--force-repeat` (optional) — NO child-id positional, NO `--evidence*`, NO `--attest*`, NO `--reclaim-stale` or any token-bearing flag (reclaim/reset/retry/recover/recovery/force/stale/reassign/resurrect/interrupt), NO undocumented flag; help text token-free. **Stage B (approved at the R1-4 gate, post-unblock ONLY):** set == `{vendor_refresh.py, vendor_refresh_recovery.py}` + Stage A pins + the recovery command's parser: exactly 1 positional (CHILD UUID) + `--operator` (required) + `--evidence` (required, choices exactly `{reboot, process-scan, operator-stop}`) + `--attest-host-inventory` (required) and nothing else | The original invariant ("no unapproved execution/recovery surface") becomes a STRICTER exact-membership pin at every stage: R1 may add only the approved command files with only the approved arguments — a hidden fifth flag, a third file, or a premature recovery file fails closed. The absence property is subsumed by exact membership | New nodes in `tests/runs/test_vendor_refresh_command.py`: unknown/forbidden flag → parser error with zero DB statements (ORM spy, mirroring R0's `test_reserved_rejection_issues_no_db_statement` pattern); child-id positional on the normal command → parser error; invocation over an ineligible parent (not COMPLETED / no MPN / missing) → bounded refusal, zero children, zero factory invocations (counting fake), zero lookups; exit-code matrix per §8.3. At Stage B additionally: recovery parser pins + §12 row 8 suite |
| 2 | `TestNoRecoverySurface::test_no_vendor_refresh_execution_module_exists` (L1457) | "R0 ships no execution/runtime surface: no `vendor_refresh*.py` in `execution/`, nothing network-capable added" | **Stage A (approved at the R1-2 gate):** assert the EXACT R1 execution vendor surface — `vendor_refresh*.py` in `execution/` == `{vendor_refresh.py, vendor_refresh_runtime.py}`; the complete new-module set for the refresh feature in `execution/` == `{vendor_commercial_binding.py, vendor_refresh.py, vendor_refresh_runtime.py}` (the helper is deliberately NOT `vendor_refresh`-prefixed); **`execution/vendor_refresh_runtime.py` is the ONLY R1 module importing `providers.internal_vendor`** (function-level, as factory source); **`execution/vendor_refresh.py` imports NO provider class in any form** (AST — I13, the F2 core of the zero-construction contract); `vendor_commercial_binding.py` is pure (no DB/env/network/adapter imports); `vendor_refresh.py` references NO `claim` symbol in any form (AST — F1 no-double-claim). (The R1-1 gate lands ONLY `vendor_commercial_binding.py`, which the `vendor_refresh*.py` glob does not match — the R0 node stays literally green through R1-1; no stage is needed there.) | The original invariant ("no network-capable surface before approval") becomes the STRICTER pin "the network-capable surface is exactly the approved set, the concrete-adapter touchpoint is singular and located, and the execution core cannot claim or import the adapter" | New nodes in `tests/execution/test_vendor_refresh_network_boundary.py` (frozen DESIGN2 §10.3(3) allowlist, extended to the helper): AST import allowlists per §10.1 table (no SearchProvider/PageFetcher/serper/http_page/semantic/comparable/providers.fx/FxObservationStore in any R1 module; runs files import no providers/web; only `runs/management/commands/vendor_refresh.py` imports execution — O4); counting-factory sentinels: zero construction AND zero `lookup()` on every losing/ineligible/config-missing/normalization-mismatch/state-refusal path; exactly-one-construction + exactly-one-`lookup()` on the winning path |
| 3 | `TestNoRecoverySurface::test_public_api_has_no_vendor_refresh_recovery_symbols` (L1435) | "No `runs.__all__` vendor symbol carries a forbidden surface token (reclaim/reset/retry/recover/recovery/force/stale/reassign/resurrect/interrupt)" | **Stage 1 (approved at the R1-3 gate; the R1-1/R1-2 gates keep the LITERAL R0 body — no runs exports are added before R1-4):** the vendor-symbols set of `runs.__all__` == EXACTLY the R0 nine (`trigger_vendor_refresh`, `claim_vendor_refresh`, `complete_vendor_refresh`, `fail_vendor_refresh`, `VendorRefreshError`, `VendorRefreshTriggerError`, `VendorRefreshClaimError`, `VendorRefreshCompletionError`, `VendorRefreshFailureError`) AND the R0 forbidden-token scan over them (strengthened: exact membership subsumes the token scan). **Stage 2 (approved at the R1-4 gate, post-unblock ONLY):** the vendor-symbols set == EXACTLY the R0 nine PLUS the strict R1 allowlist `{recover_vendor_refresh_execution, VendorRefreshRecoveryError, VendorRefreshRecoveryEvidenceError}` AND the R0 forbidden-token scan applied to ALL vendor symbols EXCEPT the allowlisted R1 set. **Naming (F4):** the R1 symbols carry their true token-bearing function (`recover…/…Recovery…`) by design — the candidate's token-free `manual_terminalize…` names are rejected as guard evasion; the guard's original intent ("no UNAPPROVED recovery surface in the public API") is what both stages enforce, with the approved surface pinned by exact membership instead of hidden by naming. The node ID is unchanged at every stage (collection identity preserved); the docstring is corrected to state the stage's exact meaning | "No recovery symbol in the public API" → "no UNAPPROVED recovery symbol": exact membership pins the approved one (and its absence pre-unblock), the token scan keeps catching any other (stale/reclaim/reset/… or a second recovery pair) drift | New nodes in `tests/runs/test_vendor_refresh_recovery.py` (post-unblock): importing the three allowlisted symbols from `product_intelligence.runs` works; importing ANY other token-bearing recovery name (e.g. `recover_vendor_refresh`, `force_recover_vendor_refresh_execution`, `VendorRefreshRecovery` — the allowlist minus suffix, the allowlist plus a token) raises AttributeError; a test-local mutation adding a fourth vendor symbol (token-bearing or not) fails the exact-membership assertion (the allowlist is strict, not open-ended) |

**Nodes verified to stay UNCHANGED and green in R1** (explicitly checked
against the proposed R1 surface — no hidden collisions):

- `test_service_module_exposes_exactly_four_primitives` (L1378) and
  `test_module_defines_no_recovery_functions` (L1407): both scan
  `vendor_refresh_claims.py` ONLY. The R1 recovery surface lives in a
  SEPARATE module (§3.1), so the R0 module surface remains exactly four —
  the tests stay literally true at every stage. [Design consequence of
  the separate module, PROPOSED.]
- `test_no_implicit_retry_after_failure` (L1465),
  `test_stuck_running_cannot_be_forced_terminal` (L1483): bodies assert
  R0-path behavior (trigger/claim over terminal/RUNNING rows) — all
  remain true; the stuck-RUNNING node's docstring ("absent-in-R0")
  stays accurate (no R0 path terminalizes it; the R1 gate is a separate
  surface the node never calls — and while R1-4 is BLOCKED, no R1 path
  exists at all).
- **ALL R0 failure-reason rejection tests (F4: preserved verbatim,
  re-run green at every gate):** `test_unknown_failure_reason_rejected`
  (L458), `test_rejects_unknown_reason_before_mutation` (L1191),
  `test_rejects_reserved_execution_interrupted_on_valid_running_row`
  (L1203), `test_reserved_rejection_issues_no_db_statement` (L1227),
  `test_reserved_reason_still_representable_in_database` (L1260),
  `test_all_non_reserved_reasons_accepted` (L1160),
  `test_r0_legal_reasons_are_exactly_the_five_non_reserved` (L1170), the
  fail-reason type battery (L2071–2125), the complete version-agreement
  battery (L974–1107). R0 `fail_vendor_refresh` is unmodified; these are
  the F1 pins the R1 primitive must coexist with.
- All shape/eligibility/idempotency/claim/complete/fail/terminalization/
  cascade/operator/trigger-source nodes (remaining ~100): R0 source and
  semantics unmodified → green.
- `tests/web/test_web_boundaries.py` (167 nodes at 3983db4): R1 adds no
  web surface and no web-visible execution imports → UNCHANGED (the
  frozen §10.3(10) allowlist extension belongs to R2).
- Model-inventory guards (`test_the_provider_layer_adds_no_model_and_no_
  migration`, `test_the_web_layer_defines_no_model`,
  `test_the_evaluation_corpus_is_not_
  persisted`, `test_the_identity_primitive_adds_no_model_and_no_migration`): R1 adds
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
management/commands/ and migrations/; FULL FILE TEXT scanned — the
recovery module's PowerShell reference strings and docstrings are
verified token-free, §1.7), `test_provider_boundaries.py::
test_nothing_is_wired_to_the_search_boundary_yet` (INNER_ROOTS incl.
runs: no `product_intelligence.providers` import), `test_web_boundaries.
py::test_the_inner_layers_do_not_import_the_web_layer` (INNER_ROOTS
incl. runs: no web import). Three new runs files (recovery module + two
commands, the recovery module landing at R1-4) ⇒ +12 parameterized
nodes overall (+4 at the R1-3 gate — the normal command file; +8 at the
R1-4 gate — the recovery module + the recovery command; recounted at
each gate), all of which must PASS: the new files therefore
carry no caller/vendor tokens (no "serper"/"google"/… in help text) and
import no providers/web — content constraints stated in §10.1. New
execution files (3) are scanned by `test_the_execution_layer_imports_no_
web` (single loop, no node delta) and by the new R1 AST guards. Net R1
collection: 6,082 − 0 removed − 0 renamed + (3 evolved in place across
stages, same node count) + (new nodes, §12) → additions only.

---

## 12. Complete new regression matrix (task §9)

**Classification legend** — D = deterministic sequential (single
connection, in-memory suite DB, pinned clocks via the primitives' `at=`
parameters (complete/fail/recover) or patched `timezone.now` — NOTE:
`claim_vendor_refresh` has NO `at=` parameter (verified §1.7); claim
instants are pinned by patching `timezone.now` in the claims module);
M = mocked race-path (monkeypatched primitives/sentinels force
interleavings that are impractical to time); C = GENUINE independent-
connection/process concurrency against a FILE-based SQLite (threads with
separate Django connections and/or subprocesses; invariant assertions
only — never timing). Per the task's explicit bar: concurrency is proven
ONLY by C nodes; sequential CAS tests are labeled D and never claimed as
concurrency proof.

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
(exact call counts, claim counts, row shapes, byte-identity,
at-most-one-new-child) over a FIXED number of rounds (5 rounds × 4
workers) — stable, deterministic in assertion, non-flaky by
construction.

| # | Scenario (task §9 item) | Nodes (suite) | Class |
|---|---|---|---|
| 1 | One complete successful command invocation; exactly one lookup for the winner; at most one per child | D (END-TO-END, the F1 demonstration): fresh COMPLETED parent → `Command.handle()` over the real command class (no monkeypatching of the flow) with a counting factory + canned adapter fake: asserts EXACTLY — 1 trigger INSERT, 1 claim UPDATE (ORM spy over the command module's `claim_vendor_refresh` binding), 1 factory invocation, 1 `lookup()` call, 1 complete UPDATE; child COMPLETED with payload (`lookup_status=SUCCESS`, observations bound); parent + all original artifacts byte-identical (I7); bounded stdout (COMPLETED class); exit 0. D (claim count): same node asserts the spy saw NO second claim on any re-entry. C: 4 concurrent full command invocations (file DB, counting factory with a short in-lookup sleep) → exactly 1 lookup total, exactly 1 claim UPDATE total, 1 RUNNING-then-terminal child, 3 IN PROGRESS reports, per-worker sentinels show 0 factory invocations + 0 `lookup()` for each loser | D+C |
| 2 | Loser makes zero calls (LB-3) | D: pre-claimed child → `execute_claimed_vendor_refresh` directly (post-claim, valid) → exactly 1 lookup (authority: the test IS the claim owner); D: PENDING child → executor → `state_not_running` bounded, ZERO factory invocations (counting fake), ZERO `lookup()`, row byte-identical (M3 machine guard); D: terminal child → same; D: absent child → `state_not_found`; C: losers of row 1's race → zero construction + zero `lookup()` (per-worker counting factories); M: R0-primitive-level double claim (two threads, same PENDING child) → one winner, the loser's `VendorRefreshClaimError` is propagated by a test-local sequence that mimics a non-R1 caller and is NEVER caught to proceed (§9 case B) | D+C+M |
| 3 | No call with missing/malformed Vendor configuration (LB-precise) | D: env cleared → child FAILED `VENDOR_LOOKUP_CONFIG_MISSING`, factory 0, `lookup()` 0, HTTP 0, payload fields NULL, reason exact; D: blank (whitespace) base URL → same; D: malformed non-blank base URL → factory 1 (object constructed — side-effect-free, §1.7), `lookup()` 1 (raises in `_ensure_configured`), **HTTP 0** (socket opener spy), FAILED `INTERNAL_ERROR`; D: factory itself raising → factory 1 (failed), no object, `lookup()` 0, HTTP 0, FAILED `INTERNAL_ERROR` (the §10.3 split, each branch separately pinned) | D |
| 4 | No call when `CommercialLookupQuery` changes captured MPN | D: child row with surrounding-whitespace `requested_mpn` (fixture-level; trigger verbatim-capture already R0-pinned) → executor → FAILED `MPN_QUERY_NORMALIZATION_MISMATCH`, factory 0, `lookup()` 0, `requested_mpn` byte-identical after (never rewritten); M: same with a counting factory | D+M |
| 5 | Frozen 2A and 4D-B policy equivalence | D: for a fixed response corpus (SUCCESS/PARTIAL/FAILED/mixed-candidate shapes incl. one-char MPN mismatch, missing explicit MPN, zero-price, OUT_OF_STOCK, UNKNOWN availability): `bind_and_encode_vendor_lookup(mpn, response)` output BYTE-EQUAL to the pre-extraction orchestration path's encoded payload (golden dicts captured from the frozen 4D-B fixtures); D: full frozen 4D-B + codec + provider suites green (19+19+46+165+127+14) | D |
| 6 | Normal COMPLETED / bounded FAILED / transport-FAILED-result distinction | D: (a) SUCCESS response → COMPLETED, `lookup_status=SUCCESS`, observations bound (EXACT/NORMALIZED_EXACT, `VENDOR_API_POLICY`); (b) PARTIAL → COMPLETED `PARTIAL` with usable observations + bounded issues; (c) transport FAILED response → **COMPLETED** `lookup_status=FAILED`, `retrieved_at=None`, zero observations — child state NOT FAILED; (d) codec `SupplementCodecError` → FAILED `RESULT_ENCODING_FAILED` (factory 1, `lookup()` 1, HTTP 1); (c) vs (d) asserted as distinct rows/states | D |
| 7 | Crash windows and stuck RUNNING behavior | D/M: W2–W9 of §7 — patched raise/stop between steps (after claim; during call; after response; during complete; during fail): row shape, call count (LB-precise), byte-identity asserted per window; D: stuck RUNNING (claim committed, no CAS issued) → trigger returns it, claim rejects, command reports IN PROGRESS (factory 0, `lookup()` 0), executor-on-stuck-row only via documented authority (not by the command) (R0 node retained); M: recovery gate over a stuck RUNNING (post-unblock suite) → row 10 exactly once; M: recovery vs complete race (W11) → single terminal write, loser reports actual shape, zero mutation; M: W12 shape (post-unblock) → premature row-10 over a still-"alive" original (test-local second executor simulating the original) → the overlap is DEMONSTRATED as the evidence gate's responsibility: the CAS alone did not prevent the second lookup — the node's docstring states the gate (not the DB) is the protection, pinned against false claims | D+M |
| 8 | Recovery gate: evidence machinery (post-unblock suite; R1-4) | D: recovery command without `--attest-host-inventory` → parser error, ZERO DB statements (ORM spy); D: unknown flag (including a superseded operator-supplied record flag such as `--evidence-record` — the record is command-written) → parser error, zero DB statements; D: each Class M refusal — scan non-empty (predicate hit at `started_at + 30 s`) → EVIDENCE_PRESENT, row byte-identical, record written with outcome `evidence_present`; boot time < `started_at` → REBOOT_ORDER_VIOLATED, row byte-identical, record written with outcome `reboot_order_violated`; scanner raising / timing out / unparseable → EVIDENCE_COLLECTION_FAILED (fail-closed), zero mutation, record written with outcome `collection_failed`; evidence dir absent/unwritable → EVIDENCE_STORE_UNAVAILABLE (stdout-only refusal — no record possible); D: row-shape refusals — PENDING row → PENDING_ROW (the gate never touches orphans, M3); COMPLETED/FAILED row → ALREADY_TERMINAL + actual-shape report, zero mutation; absent → NOT_FOUND; D: CAS winner shape — row 10 exactly (I9 identity fields byte-identical; `failure_reason=EXECUTION_INTERRUPTED`; CHECK-admitted); D: R0 `fail_vendor_refresh` over the same RUNNING row with the reserved reason → still rejected with zero mutation (F1 re-pin); D (the F3 no-false-claim pin): the recovery module + recovery command docstrings carry the pinned attestation-limit statement (the software collects/verifies structure, never proves termination; Class A is attested; O8 cross-checks) — a meta-node asserting the statement's presence so a future edit cannot silently re-claim proof; D: evidence record shape — exact key set per class, digest in stdout, refusal records written too | D |
| 9 | Reserved failure reason written only by the approved R1 recovery primitive (post-unblock) | D: primitive writes row-10 shape successfully (CHECK-admitted, R0-pinned); D: AST scan — the ONLY module that references `EXECUTION_INTERRUPTED` as a WRITE value (in an update/terminalization call) is `runs/vendor_refresh_recovery.py` (model vocabulary + migration + R0 service's rejection check are pinned read/definition references); D: the primitive issues NO network and constructs NO adapter (sentinel); M: concurrent recovery + original complete (two threads, file DB) → exactly one terminal write (I3); C: 4-worker recovery race over one RUNNING row → one writer wins, three bounded `already_terminal`, row byte-stable | D+M+C |
| 10 | Existing PENDING never silently executed; truthful operator provenance (M3) | D: programmatic trigger creates PENDING (non-command fixture); command invocation → stdout reports child id + state PENDING + recorded operator + created_at; row count unchanged; child still PENDING; factory 0; `lookup()` 0; `operator` field byte-identical (I6/§3.3 Option A pin); D: DIRECT executor call on the orphan PENDING row → `state_not_running` bounded, factory 0, `lookup()` 0, row byte-identical (the machine guard behind the procedural rule); D: full command lifecycle on a fresh parent → row `operator` == the `--operator` value verbatim AND that invocation was the executor (single-invocation proof via the counting factory owned by the same process) | D |
| 11 | Five-minute safeguard, `--force-repeat`, simultaneous commands | D (pinned clock): latest terminal at age 299.9 s → refusal, 0 children, 0 claims, 0 lookups; age 300.1 s → allowed; `--force-repeat` at 299.9 s → allowed (new child, never a rewrite); force over ACTIVE child → IN PROGRESS (force does not bypass in-progress; no claim, no lookup); refusal stdout carries the blocking child id + finished_at + age; D: tie-break — two terminal children with identical `finished_at` → `id` DESC deterministic latest; C: interleavings 1/4/5/6 of §9 (4 workers, file DB): invariants = at most ONE new child per round, exactly ONE claim UPDATE per round total, refusals commit nothing, force honored exactly once | D+C |
| 12 | Real SQLite transaction/locking behavior | C: (a) lock-statement serialization — worker A holds the txn (sleep after zero-row stmt), worker B's identical stmt blocks then reads A's committed state (Appendix A.7 pattern, in-test); (b) bounded busy error — raw connection holds an exclusive write lock > 5 s (pathological holder), command surfaces DATABASE BUSY, non-zero exit, ZERO mutation (row snapshot before/after); (c) kill — subprocess holds txn with uncommitted INSERT, killed → fresh connection writes immediately, INSERT rolled back, lock-statement zero-mutation confirmed (Appendix A.5 pattern); (d) reader non-blocking — concurrent SELECT proceeds while a command txn holds the lock (web GET not wedged) | C |
| 13 | Failure persistence and zero-mutation guarantees; LB-3 construction zeros | D: every bounded failure path (#3–#6, #8) asserts the all-fields row snapshot pattern (R0 `_row_snapshot`) unchanged except the intended fields AND the counting-factory invocation count == 0 on every LB-3 branch (§3.2 table, branch by branch); D: parent + ALL original artifacts byte-identical after every R1 operation (reusing R0's lifecycle byte-identity test pattern extended with the R1 execution) | D |
| 14 | Parent and all original artifacts byte-identical | D: full R1 normal path (COMPLETED) + full R1 failure paths + (post-unblock) recovery path vs. pre-state of `ResearchRun`, `PriceIntelligenceSnapshot`, original `ResearchSupplementSnapshot` (payload bytes + created_at), `ResearchFxSnapshot`, `ResearchMicronAliasSnapshot`, `ExecutionEvidenceRecord`s, `AiAssistedReviewCandidate`s, `ComparableResearchExecution`s | D |
| 15 | Zero FX and zero unapproved provider calls; import allowlists | D: sentinel instrumentation — `FxObservationStore` query spy (0 reads, 0 writes), `EcbFxProvider` construction sentinel (never), `SerperSearchProvider` never imported (AST + runtime), `HttpPageFetcher`/`HttpPdfFetcher` never constructed, semantic runtime never imported, `trigger_comparable_research` never called, `claim_execution`/`complete_execution` (ResearchRun-level) never called; D: network-boundary AST allowlists per §10.1 (all 8 new/modified R1 files) + the I13 pins (runtime is the ONLY `providers.internal_vendor` importer; the core is provider-class-free; only `runs/management/commands/vendor_refresh.py` imports execution — O4) + the counting-factory one-allowed-call probe (frozen DESIGN2 §10.3(3) shape) | D |
| 16 | No new browser mutation surface | D: URLconf route set byte-equal to the frozen R0/production set (no new route); D: `web/views.py` + `web/urls.py` + `web/commercial_access.py` unchanged (hash pin vs 3983db4 blobs); D: no new POST handler, no CSRF surface, no template change (web file-set diff == ∅); D: full web-boundary suite (167) green unchanged | D |
| 17 | No regression from 4D-B helper extraction | D: frozen 4D-B/codec/provider/authority suites green (counts per §11); D: golden-dict equivalence (#5); D: orchestration behavior invariants — config-absent → no call/no snapshot; description-only → no call; success → one call + snapshot (frozen cases A–J re-run); M: helper called from both call sites with identical policy inputs → identical outputs (drift canary) | D+M |
| 18 | All previously frozen safety and authority boundaries | D: FULL suite — 6,082 frozen R0 nodes (the §11 staged in-place evolutions applied AT THEIR GATES ONLY: rows 1–2 stage A at R1-2/R1-3; row 3 stage 1 at R1-3; row 3 stage 2 + rows 1–2 stage B at R1-4 post-unblock — ChatGPT approves each stage at its gate) + all new R1 nodes → 0 removed / 0 renamed; `python manage.py check` clean; `python manage.py makemigrations --check --dry-run` → "No changes detected" (no R1 schema change); `git diff --check` clean; node-level collection diff vs 6,082 = additions only (recounted per gate); at the R1-1…R1-3 gates the recovery surface does not exist — row 3 stage 1 pins exactly that | D |
| 19 | NO DOUBLE CLAIM; single authoritative call graph (F1) | D: AST — the ONLY R1 module referencing `claim_vendor_refresh` is `runs/management/commands/vendor_refresh.py`, at EXACTLY ONE call site (inside the serialized txn); `execution/vendor_refresh.py` and `execution/vendor_refresh_runtime.py` contain NO reference to any claim symbol in any form (import, call, name string); D: AST — NO R1 module has an `except` handler naming `VendorRefreshClaimError` (or any runs CAS error) as a caught type used for control-flow continuation (a raise may be re-raised/wrapped at the outer boundary — the pattern is pinned by the two allowed exception types: `VendorRefreshExecutionError` wrapping, `SystemExit`/`OperationalError` bounded handling); M: monkeypatch the command module's `claim_vendor_refresh` binding to RAISE (simulating the structurally-unreachable in-txn claim failure) → the transaction rolls back (no row), factory 0, `lookup()` 0, bounded non-zero exit, and the raise is NOT caught to proceed (the executor is never entered); D: full successful invocation (row 1) re-asserted here — claim UPDATE count == 1 (no duplicate claim anywhere in the lifetime); C: row 1's 4-worker race → claim UPDATE count == 1 total (the loser made zero claim attempts — it exited at the snapshot) | D+M+C |

Command-suite summary (`tests/runs/test_vendor_refresh_command.py`,
frozen DESIGN2 §10.3(5) scope + this design's additions): run-uuid parse
(bounded 404-style), operator mandatory/verbatim/bounded, recorded
provenance exact (`trigger_source=MANAGEMENT_COMMAND`), bounded stdout
(no secrets, no base URL, no raw vendor content, no raw exception text),
exit-code matrix, no reclaim/child-id/`--evidence*` flag on the normal
command (evolution row 1 stage A), in-progress report, safeguard ordering
+ refusal zero-persistence/zero-claim (row 11), Option-A provenance pin +
PENDING-never-executed (row 10), DATABASE BUSY path (row 12b),
end-to-end success (row 1). Recovery-suite
(`tests/runs/test_vendor_refresh_recovery.py`, post-unblock): rows 7
(recovery parts), 8–9 + the evidence-record shape pins + the attestation-
limit docstring pin (row 8) + the allowlist drift nodes (row 3 stage 2
context).

---

## 13. Expected production file changes for future R1 implementation

Exact file-level delta (future work — NOT performed by this design).
Base branch: `feature/vendor-refresh-r0` tip 3983db4 (production line per
frozen D9); no merge of development main.

| File | Change | Substep | Content (from §10.1) |
|---|---|---|---|
| `product_intelligence/execution/vendor_commercial_binding.py` | NEW | R1-1 | D10 shared helper `bind_and_encode_vendor_lookup` (moved verbatim policy from `_try_vendor_commercial_lookup` steps 6–7); pure |
| `product_intelligence/execution/orchestration.py` | MODIFY | R1-1 | `_try_vendor_commercial_lookup` L1124–1257: replace the inline binding/encode block with the helper call; behavior-identical (pinned by rows 5/17 of §12); no other line changes |
| `product_intelligence/execution/vendor_refresh.py` | NEW | R1-2 | `execute_claimed_vendor_refresh` (POST-CLAIM-only contract, §3.2/§10.2: state re-assert; S4–S6 preflight; S7 factory+lookup; S8 encode; S9 complete; single outer boundary; NO claim reference in any form) + `VendorRefreshExecutionError`; provider-class-free (I13) |
| `product_intelligence/execution/vendor_refresh_runtime.py` | NEW | R1-2 | `execute_claimed_vendor_refresh_with_default_providers` (supplies the `InternalVendorAdapter` class as the zero-arg factory; the ONLY `providers.internal_vendor` importer in R1; constructs nothing itself — O9) |
| `product_intelligence/execution/__init__.py` | MODIFY (additive) | R1-2 | export exactly `execute_claimed_vendor_refresh`, `execute_claimed_vendor_refresh_with_default_providers`, `VendorRefreshExecutionError` (adversarial exact-set pin, §12 row 18 context) |
| `product_intelligence/runs/management/commands/vendor_refresh.py` | NEW | R1-3 | normal command (§3.4 flow — the ONLY claim call site —, §10.2 graph, §8.3 stdout/exit contract) |
| `tests/execution/test_vendor_refresh_execution.py` | NEW | R1-2/R1-3 | §12 rows 1–6, 13–15, 17, 19 (D/M nodes) |
| `tests/execution/test_vendor_refresh_network_boundary.py` | NEW | R1-2 | §12 rows 2, 15 (AST allowlists + counting-factory sentinels) |
| `tests/runs/test_vendor_refresh_command.py` | NEW | R1-3 | §12 rows 10, 11, 1 (command D/C nodes) + §11 row 1 stage A new nodes |
| `tests/runs/test_vendor_refresh_concurrency.py` | NEW | R1-3 | §12 rows 1, 11, 12, 19 (C nodes + file-DB fixture, §12 infra) |
| `tests/runs/test_vendor_refresh_claims.py` | MODIFY (in-place staged evolutions ONLY) | R1-3 (rows 1–2 stage A, row 3 stage 1); R1-4 (rows 1–2 stage B, row 3 stage 2) | §11 rows 1–3 (ChatGPT-approved per stage at the named gate); node IDs unchanged at every stage |
| `product_intelligence/runs/vendor_refresh_recovery.py` | NEW | R1-4 **[BLOCKED pending O8]** | the M1 surface: `recover_vendor_refresh_execution` (row-10 CAS + bounded 0-row re-read reporting) + the evidence machinery (scanner seam `scan_process_table`/`read_boot_time`, pure `evaluate_scan_predicate`, `build_evidence_record`/`write_evidence_record`); honest token-bearing names (F4); module docstring carries the pinned attestation-limit statement |
| `product_intelligence/runs/errors.py` | MODIFY (additive) | R1-4 **[BLOCKED]** | append `VendorRefreshRecoveryError` (3 reasons) + `VendorRefreshRecoveryEvidenceError` (bounded evidence-refusal reasons); existing classes untouched |
| `product_intelligence/runs/__init__.py` | MODIFY (additive) | R1-4 **[BLOCKED]** | `_VENDOR_REFRESH_R1_EXPORTS` + `__all__` + lazy `__getattr__` branch for EXACTLY the three allowlisted symbols (§11 row 3 stage 2) |
| `product_intelligence/runs/management/commands/vendor_refresh_recovery.py` | NEW | R1-4 **[BLOCKED]** | recovery command (§3.1 flow: required `--evidence` + `--attest-host-inventory`; machine evidence collection at command time; evidence record to `PI_VENDOR_RECOVERY_EVIDENCE_DIR`; row-10 CAS; §8.3 stdout incl. record digest) |
| `tests/runs/test_vendor_refresh_recovery.py` | NEW | R1-4 **[BLOCKED]** | §12 rows 7 (recovery parts), 8, 9 + the row 3 stage 2 allowlist drift nodes |

Explicitly NOT changed: `runs/vendor_refresh_claims.py`,
`runs/models.py`, `runs/migrations/**` (no migration in R1),
`providers/**`, `research/**`, `web/**`, `domain/**`, `config/**` (the
evidence dir is a deployment-owned env read by the recovery command, in
the `PI_*` env pattern of `PI_SQLITE_PATH`/`PI_VENDOR_LOOKUP_BASE_URL` —
no settings.py change), `scripts/**` (the canonical launch form is a
RUNBOOK document, O8 — not a script), every other test file.
[PROPOSED; enforced by §12 rows 16 and 18.]

---

## 14. Explicit remaining approval decisions and blockers

**R1-4 (the M1 recovery surface) is BLOCKED [PROPOSED — the frozen
requirement is not weakened]:** the recovery command + primitive +
evidence machinery are fully specified here for approval, but their
implementation is blocked, separately from R1-1…R1-3 and R1-5, pending
BOTH: (i) O8 completed and recorded — including, for R1-4, verified
administrator process-table visibility, the canonical launch form pinned
in the runbook, and the evidence retention location/duration (the frozen
DESIGN2 §4.5 deployment prerequisite, now explicitly ALSO the R1-4
unblock condition: the Class A attestation regime must exist before the
first possible use of the row-10 writer); and (ii) this gate's approval
of the §3.1 mechanism (evidence classes, predicate, T = 60 s, record
shape, HOLD rule, scanner seam). While BLOCKED: no R1 code writes
`EXECUTION_INTERRUPTED` (the reserved value stays R0-rejected and
unwritable by any R1 surface); stuck RUNNING rows are permanent reported
HOLDS (safe direction — §7); §11 row 3 stage 1 pins the absence. The
block defers the ONLY surface that could write the reserved reason until
the frozen "sufficient trusted external evidence" bar (DESIGN2 §3.6) is
operationally satisfiable — it does not lower the bar; an attestation
token alone (the candidate design) was held insufficient by review (F3)
and is NOT shipped.

**Decisions requested from ChatGPT at this design gate:**

- **O1 — M1 evidence parameters and forms [re-evaluated per F3].**
  Confirm: the three evidence classes (reboot / process-scan /
  operator-stop); the machine predicate (signature substring
  `vendor_refresh <parent-run-uuid>`, case-insensitive; creation window
  `≤ started_at + 60 s`); **T = 60 s retained** (re-evaluation: denial-
  only parameter; any T ≥ ~2 s safe; 60 s ≈ 60× the worst timestamp-
  granularity/wrapper margin — §3.1); the scanner timeout 60 s; the
  canonical PowerShell/CIM reference command forms (process table, boot
  time); the evidence record schema v1 (exact key set per class); the
  deployment-owned env `PI_VENDOR_RECOVERY_EVIDENCE_DIR`; the explicit
  `--attest-host-inventory` requirement (the irreducible Class A fact,
  asserted, never defaulted).
- **O2 — R1 recovery surface naming and guard evolution [REPLACED per
  F4; no longer a fork].** The candidate's token-free
  (`manual_terminalize…`) naming is REJECTED as guard evasion. Confirm:
  the honest token-bearing names (`runs/vendor_refresh_recovery.py`,
  `recover_vendor_refresh_execution`, `VendorRefreshRecoveryError`,
  `VendorRefreshRecoveryEvidenceError`, command `vendor_refresh_recovery`)
  TOGETHER with the staged in-place evolution of
  `test_public_api_has_no_vendor_refresh_recovery_symbols` (§11 row 3 —
  strict allowlist, node ID preserved, all R0 failure-reason rejection
  tests untouched) and the adversarial allowlist-drift nodes (§12 row 3
  context).
- **O3 — Orphaned PENDING resolution policy.** Confirm R1 behavior =
  report-only HOLD (never claimed/executed/terminalized by R1 — now
  machine-guarded by the executor's PENDING refusal, §3.2); the three
  future-resolution options remain out of scope for R1 (ii requires a
  schema change; iii belongs to R3/8C).
- **O4 — Command-layer runs→execution import carve-out.** Confirm the
  outer-surface direction (the normal command imports the execution
  public API, mirroring web; the recovery command imports NO execution
  surface) together with the NEW guard pinning that no other `runs/`
  module imports `product_intelligence.execution` (§10.1/§12 row 15).
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
- **O8 — Deployment prerequisite [PROMOTED: blocks R1 deployment AND is
  the R1-4 unblock condition].** The frozen DESIGN2 §4.5 host
  permissions + operational audit review (host/CMD account inventory,
  command-logging posture, database file + directory ACLs, runbook
  controls — incl. the backup-while-app-stopped discipline vs command
  invocations, §9 case D) must be completed and recorded BEFORE R1
  deploys. For R1-4 it additionally verifies: administrator process-
  table visibility (the scanner seam's premise), the CANONICAL launch
  form (the §3.1 predicate's soundness premise — non-canonical original
  launches force HOLD), and the evidence retention location/duration for
  recovery records (the Class H cross-check target for Class A
  attestations).
- **O9 — Adapter construction timing (F2).** Confirm the lazy-factory
  mechanism: the runtime supplies the `InternalVendorAdapter` class as
  the zero-arg factory; the core (provider-class-free, I13) invokes it
  exactly once at S7, after the claim commit and all preflight checks;
  the exact zero-construction/zero-lookup branch table (§3.2) is the
  pinned contract. This is a REFINEMENT of DESIGN2 §3.5's illustrative
  eager construction (placement + single-construction properties
  preserved; timing moved) — flagged because DESIGN2 §3.5 showed the
  runtime "constructing `InternalVendorAdapter()`"; the comparable-
  runtime precedent (verified eager, §1.7) is the shape deliberately NOT
  mirrored, with the justification in §3.2.

**Contradiction check against frozen DESIGN2/R0 [PROPOSED
assessment]:** No frozen contract is contradicted. Deliberate refinements
of OPEN design space, flagged for approval rather than claimed as
settled:

(a) the combined trigger+claim transaction (§3.4) refines DESIGN2
§3.6's phase-by-phase crash table for the COMMAND path only — R0
primitives, durable shapes, and all frozen invariants are unchanged
(crash consequences strictly improve: the PENDING-orphan window becomes
unreachable on the command path);
(b) the advisory zero-row write-lock statement (§3.4 A3) is the concrete
mechanism for M4, which frozen DESIGN2 §13 explicitly assigned to "R1
review" ("Concurrent invocations … reviewed separately at R1");
(c) the M1 implementation block (§3.1/§14) is a DEFERRAL, not a
weakening: DESIGN2 §3.6's trusted-evidence bar is restated unchanged and
the only surface that writes the reserved reason is withheld until the
bar is operationally satisfiable (O8); DESIGN2 §3.6's "detailed at R1
review" is honored by the full mechanism specification in §3.1;
(d) the adapter construction timing (§3.2/O9) refines DESIGN2 §3.5's
illustrative runtime shape inside the M2 mechanism that DESIGN2 §12.2
left open at this gate — the frozen PLACEMENT decision (the runtime as
the only concrete-provider touchpoint in the command stack) and the
single-construction property are preserved;
(e) the separated claim/post-claim entrypoint (§3.2/§10.2) answers
DESIGN2 §12.2 M2 (trusted execution ownership enforcement) and §3.4's
proposed claim-first step 1 — which DESIGN2 left as an open R1
MECHANISM (M2/M4), not a frozen implementation: the ownership and
boundary INTENT of §3.4 (paid work only after claim; single outer
post-claim boundary; loser zero-work) is preserved, and the double-claim
the candidate inherited from a literal reading of §3.4 step 1 is removed.
The D10 helper extraction is unchanged. Both refinements are inside
confirmed decisions D3/D6 and do not reopen any frozen commercial,
semantic, FX, replay, or pricing-authority contract.

**Unresolved risks carried forward (honest inventory):**

1. Privileged-writer residual (M2): host-level code/SQL can bypass all
   service-level guarantees — including a direct post-claim executor call
   on a RUNNING child it did not claim (second lookup, the §3.2
   residual) — accepted per the frozen threat model (DESIGN2 §4.2),
   stated, not hidden.
2. Orphaned PENDING via non-command triggers blocks the parent's refresh
   until a future approved gate (O3) — inert (zero external outcome),
   reported on every invocation, machine-refused by the executor.
3. Cooldown window is wall-clock on one host; clock regression affects
   the OBSERVED window only (operator-safety check, not a rate limit).
4. Busy-timeout bound (5 s): a pathological lock holder yields a bounded
   "database busy" refusal (zero mutation) — retry is manual.
5. The §3.1 predicate assumes the canonical launch form; wrapped or
   renamed launches that hide the command line force HOLD (conservative,
   operator duty + O8 runbook pin).
6. R1-4 BLOCKED: stuck RUNNING rows have NO R1 resolution path until O8
   unblocks the gate — they remain permanent reported HOLDS (safe
   direction: no overlap possible, only that parent's refresh is
   blocked).
7. R2 display of `EXECUTION_INTERRUPTED` rows must carry the I8 UNKNOWN
   wording (assigned to R2, frozen vocabulary boundary).
8. The 6,082-node R0 collection and all suite-green claims above were
   verified in the design worktree at 3983db4 with Python 3.14.7 /
   Django 5.2.17 / pytest 9.1.1; the implementation gate re-verifies per
   the frozen validation gates.

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
  provider/authority suites green UNCHANGED; full suite = 6,082 +
  additions only; `makemigrations --check` clean. (The R0 surface
  absence nodes stay literally green: the helper file does not match the
  `vendor_refresh*` globs, §11 row 2.)
- **R1-2 — Execution core (no command yet).**
  `execution/vendor_refresh.py` (POST-CLAIM-only
  `execute_claimed_vendor_refresh` + `VendorRefreshExecutionError`;
  provider-class-free, I13) + `execution/vendor_refresh_runtime.py`
  (factory-supplying entry; the only `providers.internal_vendor`
  importer, O9) + execution `__init__` additive exports + network-
  boundary suite (§12 rows 2–4, 13–15, 17, 19 D/M nodes). Gate criteria:
  one-call/loser-zero-call/config-missing/normalization-mismatch/
  transport-FAILED-result distinction pinned (LB-precise, §3.2 table);
  no claim reference in the execution core (AST, row 19); no surface
  callable from web exists; §11 row 2 stage A approved at this gate.
- **R1-3 — Normal command + M4 safeguard + M3 Option A.**
  `runs/management/commands/vendor_refresh.py` + serialized txn (the
  ONLY claim call site) + command suite (§12 rows 1, 10, 11, 16, 19;
  §11 row 1 stage A + row 3 stage 1 APPROVED at this gate) + C-node
  infrastructure (O6) + concurrency suite (§12 rows 1, 11, 12, 19 C
  nodes). Gate criteria: interleaving invariants hold under genuine
  independent connections (one child, one claim, one lookup total,
  losers zero); the end-to-end success node (row 1) green; the evolved
  R0 nodes at this gate are EXACTLY rows 1–2 stage A + row 3 stage 1
  (node IDs unchanged), explicitly approved node-by-node; the recovery
  surface does not exist (row 3 stage 1 pins it).
- **R1-4 — M1 recovery gate (separately gated surface) [BLOCKED —
  unblock conditions: O8 completed and recorded (incl. the R1-4
  additions, §14) + this gate's approval of the §3.1 mechanism + O1/O2
  confirmation].** When unblocked: `runs/vendor_refresh_recovery.py`
  (honest names, F4: primitive + scanner seam + pure predicate +
  evidence record machinery; attestation-limit docstring) + additive
  errors (2 classes) + `runs/__init__` additive exports (EXACTLY the
  three allowlisted symbols) + `runs/management/commands/
  vendor_refresh_recovery.py` + recovery suite (§12 rows 7 recovery
  parts, 8, 9; §11 rows 1–2 stage B + row 3 stage 2 APPROVED at this
  gate — the staged allowlist evolution, node IDs unchanged). Gate
  criteria: reserved reason writable ONLY by this primitive (AST pin);
  R0 F1 pins + ALL R0 failure-reason rejection tests green unchanged;
  row 10 single-winner race proven under C; every Class M refusal
  zero-mutation (ORM spy + row snapshot); the no-false-claim docstring
  pin (row 8) green; no premature unblock: O8 record attached to the
  gate review.
- **R1-5 — Final R1 gate (over R1-1…R1-3; R1-4 state recorded).**
  Full suite (6,082 frozen + all R1-1…R1-3 additions; 0 removed /
  0 renamed), `manage.py check`, `makemigrations --check --dry-run`,
  `git diff --check`, node-level collection diff report, file-delta
  audit vs §13, the R1-4 BLOCKED status + O8 prerequisite status
  recorded (blocks R1-4 implementation and R1 DEPLOYMENT until recorded;
  R1-1…R1-3 implementation may land without O8 — deployment of ANY R1
  surface may not).

The pushed document is a proposal only. It authorizes nothing until
each substep is separately reviewed and approved.

---

## 16. FU1 required-final-checks compliance map

| Required final check | Where satisfied |
|---|---|
| One authoritative command-to-execution call graph | §10.2 (the single graph; §5 its projection; §12 row 19 pins its properties) |
| No double claim | §3.2 (one claim site), §3.4 step [f], §10.2 [f] + graph property (1)/(2), §12 rows 1/19 (runtime claim-count == 1; AST single call site; in-txn claim-raise rollback node) |
| No network inside DB transactions | §3.4 (COMMIT precedes S7), §6 table, I10, §12 row 12 |
| No invented ownership guarantee in R0 | §3.2 (R0 F2 restated: CAS = single-winner terminalization, NOT issuer identity; no owner token — the M2 approval-gated alternative explicitly NOT invoked), §14 (e) |
| No unchecked recovery portrayed as trusted evidence | §3.1 (Class M/A/H split; machine collection at command time; explicit attestation flag; HOLD rule; O8 as the trust regime; the no-false-claim docstring pin §12 row 8), R1-4 BLOCKED |
| No hidden recovery capability escaping test guards | §11 (staged exact-membership pins at every gate — the recovery surface is pinned ABSENT pre-unblock by row 3 stage 1 and row 1 stage A; token-bearing honest names; allowlist drift nodes), §12 rows 8–9 |
| M4 SQLite transaction strategy remains explicit and independently testable | §3.4 A3 (zero-row lock statement, verified §1.6), §6, §12 rows 11/12 (C nodes, file DB, O6) |
| Frozen DESIGN2 decisions and R0 behavior unchanged | §2.2, §4.1 (rows 1–9 reproduced), §11 (all R0 failure-reason rejection tests preserved), §14 contradiction check (a)–(e), §13 (R0 files explicitly not changed) |
| All conflicting cross-references reconciled | §3.2↔§10.2 (claim/execute separation — the F1 contradiction deleted), §3.2↔§10.1 (F2 factory wiring matches the zero-construction table), §3.1↔§4.1 row 10↔§7 W11/W12↔§15 R1-4 (BLOCKED status consistent everywhere), §5↔§10.2 (projection vs authoritative graph), F5 LB wording uniform in §3.2/§4.2 I4/§5/§7/§9/§10.3/§12 |

---

## Appendix A — Verification commands and probe transcripts (candidate session)

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

### Appendix A.2 — FU1 revision verifications (this session)

Direct reads at 3983db4 (worktree `C:/dev/Product_Intelligence_vref_r1_
design`; no file modified; §1.7 records the facts):

```
git -C … show 3983db4:product_intelligence/runs/vendor_refresh_claims.py
    # claim L327-377 (single conditional UPDATE, PENDING-only, no at=);
    # complete L381-489 / fail L518-611 (pre-checks then single UPDATE);
    # trigger L134-319 (own savepoint; concept 1/2; no discriminator)
git show 3983db4:product_intelligence/providers/internal_vendor.py
    # __init__ L1609-1615 (no config read); _ensure_configured L1617-1629
    # (first statement of lookup L1631+); _validate_base_url L215-268
git show 3983db4:tests/runs/test_vendor_refresh_claims.py
    # TestNoRecoverySurface L1373-1508; _FORBIDDEN_SURFACE_TOKENS
    # L1359-1370; failure-reason rejection nodes L458/974-1107/1160-1260/
    # 2071-2125
git show 3983db4:product_intelligence/execution/comparable_runtime.py
    # eager fetcher construction (the precedent deliberately not mirrored)
git show 3983db4:tests/domain/test_domain_boundaries.py
    # CALLER_TOKENS L59; VENDOR_TOKENS L63-74; full-file-text scans
git show a87ff1b:docs/VENDOR_ONLY_REFRESH_DESIGN.md
    # §3.4 L686-754; §3.5 L755-767; §4.5 L950-976; §4.6 L977-1019;
    # §5.1 L1022-1043; §5.2 L1044-1069; §11 L1607-1738; §12 L1739-1785;
    # §13 L1786-1840
python -m pytest tests/runs/test_vendor_refresh_claims.py
    # re-run this session: 115 passed, 5 subtests passed, 0 failed,
    # 0 skipped (baseline re-confirmation)
```

---

**Final status: `VREF-R1-DESIGN-FU1 REVISED — PENDING CHATGPT FINAL
ARCHITECTURE REVIEW` (R1 design NOT FROZEN; R1 implementation NOT
AUTHORIZED; R1-4 BLOCKED pending O8)**
