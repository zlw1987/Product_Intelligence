# PRODUCT-INTEL.VENDOR-REFRESH-DESIGN2 — Vendor-only Refresh

**Production Baseline Architecture Contract (Design Only)**

- **Task type:** DESIGN ONLY. No implementation, no code/test/migration/settings
  changes were made by this design.
- **Authoritative baseline:** deployed production SHA
  `cde2a802c54372da088a7d1876f450cbf9bd7c69`
  (branch `pilot-vendor-status-ux-a`, commit
  "PRODUCT-INTEL.PILOT-VENDOR-STATUS-UX-A: Vendor API Status notice in Quote &
  Market Summary + evidence-only exclusion investigation").
- **Development `main` SHA inspected for divergence only:**
  `916296af8d23f780aca63702e3302458ba7f8ffd`.
- **Reviewer / approval gate:** ChatGPT (project lead, independent architecture
  reviewer).
- **Revision:** DESIGN2-FU2 — final contract consistency corrections
  (DESIGN2-FU1 reviewed: direction accepted; architecture NOT FROZEN, R0
  NOT AUTHORIZED): (1) RUNNING terminalization semantics corrected — the
  four lifecycle primitives are trigger (INSERT PENDING), claim
  (PENDING→RUNNING), complete (RUNNING→COMPLETED with atomic result
  publication), and fail (RUNNING→FAILED with a bounded failure reason);
  complete/fail are REQUIRED and remain the ONLY legal RUNNING→terminal
  transitions; what R0 forbids is EXTRA recovery-based terminalization of
  an allegedly stale or interrupted RUNNING execution without trusted proof
  that the original execution has stopped (stale reclaim, threshold-
  triggered forced failure, RUNNING→PENDING reset, automatic retry,
  operator-forced interruption/recovery, reassignment of an existing
  RUNNING attempt); the final R0 state-transition table is §3.3; (2) phase
  ownership corrected — the `vendor_refresh` management command and the
  default-provider runtime belong to R1, NOT R0; R0 has exactly
  persistence, model + migration, lifecycle claims, bounded errors and
  exports, offline tests (no management command, provider call, HTTP
  endpoint, template, or deployment); (3) D1 and D7 are CONFIRMED
  decisions (§12.1) — the original Quote & Market Summary, original vendor
  rows, and existing PILOT-VENDOR-STATUS-UX-A status notice remain
  unchanged; the optional pointer-line modification is NOT approved for R2
  and is removed from the approved R0–R2 scope; the R2 history section
  renders only for ALLOWED connections with at least one refresh record;
  (4) `operator` clarified as the self-reported TRIGGER initiator, not
  necessarily the person or process that eventually executes a PENDING
  child (§3.1/§3.3/§4.6), with the R1 provenance requirement; (5) R1 repeat
  safeguard ordering corrected — the safeguard is evaluated before a new
  refresh attempt is persisted, so a cooldown refusal leaves no newly
  created PENDING child. This is a DESIGN document correction only: R0 is
  NOT approved, NOT frozen, and NOT implemented by this revision.
  - Prior revision: DESIGN2-FU1 — bounded architecture-gate corrections
    C1–C9 applied per the ChatGPT independent architecture review of
    DESIGN2 (stale reclaim REJECTED; idempotency semantics split into three
    distinct concepts; refresh-success / usable-quotation / IN_STOCK-
    quotation vocabulary; operator identity as self-reported provenance,
    not authentication; R1 repeat-operation safeguard; stored-row
    immutability accuracy; query-normalization fail-closed check;
    replay/display byte-identity scope; additional regression coverage).
- **Final status:** `DESIGN2-FU2 CORRECTIONS APPLIED — PENDING CHATGPT FINAL ARCHITECTURE GATE`

Every statement below is marked either:

- **[VERIFIED]** — read directly from the production SHA source via non-
  destructive Git inspection (`git show`, `git ls-tree`, and a detached
  read-only worktree at the production SHA for test execution), with file and
  line/blob references; or
- **[PROPOSED]** — a design decision in this document, requiring ChatGPT
  approval before any implementation.

No destructive Git operation (`restore` / `reset` / `checkout` / `stash` /
`clean`) was used. The current working tree was left untouched (one pre-
existing modification `tmp_collection.txt` and pre-existing untracked files
were observed and preserved).

---

## 1. Verified production source references

### 1.1 Baseline verification method [VERIFIED]

1. `git cat-file -t cde2a802…` → `commit`; `git log --oneline -5 cde2a802…`
   confirms the production SHA is the tip of branch
   `pilot-vendor-status-ux-a` (also present on
   `remotes/origin/pilot-vendor-status-ux-a`).
2. Source files were read at the production SHA with
   `git show cde2a802…:<path>` (blob IDs below).
3. A detached, read-only temporary worktree was created at the production SHA
   (`git worktree add --detach <tmp> cde2a802…`) **solely to execute the
   production test baseline** (§1.4). It shares no state with the working
   tree and was created after all source reads.

### 1.2 File references at production SHA cde2a802 [VERIFIED]

| File | Blob (git ls-tree) | Role verified at production |
|---|---|---|
| `product_intelligence/runs/models.py` | `b6a1378bd53a02c8367852cbcb67ea8b25e91b27` | All persisted run records: `ResearchRun` (L120), `PriceIntelligenceSnapshot` (L402), `ExecutionEvidenceRecord` (L488), `AiAssistedReviewCandidate` (L622), `ComparableResearchState` (L845), `ComparableResearchFailureReason` (L878), `ComparableResearchExecution` (L927), `ResearchSupplementSnapshot` (L1133), `ResearchFxSnapshot` (L1210), `ResearchMicronAliasSnapshot` (L1325), `FxObservationStore` (L1414). Run state vocabulary + `ALLOWED_TRANSITIONS` (L50): CREATED→RUNNING→{COMPLETED, PARTIALLY_COMPLETED, FAILED}, terminal is terminal. |
| `product_intelligence/execution/orchestration.py` | `3fa9d95338e04f06b2a22fa1770d7305ced3cb80` | Pipeline entry `execute_research_run` (L461); `_execute_claimed_run` (L178); vendor lookup step `_try_vendor_commercial_lookup` (L1124); FX step `_try_fetch_fx_rates` (L1355) + `_get_required_fx_currencies` (L1258); "ATOMIC FINAL PUBLICATION" block (L575); `_terminalize_run` (L774). |
| `product_intelligence/execution/compact_quote_replay.py` | `f61c4e2e89be2aa253b371adc08effb9cdfeef2c` | ALLOWED-branch historical replay `replay_compact_quote_projection`; reads + decodes `PriceIntelligenceSnapshot`, `ResearchFxSnapshot`, `ResearchSupplementSnapshot` (sole decoder of the vendor artifact); exposes `supplemental_result` on the replay result for display-only status presentation (PILOT-VENDOR-STATUS-UX-A). |
| `product_intelligence/execution/compact_quote_public_replay.py` | `2fcca0c1e4a306fe289bf2184d627a102dbdc703` | DENIED-branch public-only replay `replay_public_compact_quote_projection`; FU2 authority ownership: loads and decodes the run's own `PriceIntelligenceSnapshot` + `ResearchFxSnapshot`; binding contract "NEVER reads `ResearchSupplementSnapshot`, never imports or calls the commercial supplement codec". |
| `product_intelligence/providers/internal_vendor.py` | `e3da8ea7709322608d1d0e1aeb1ea1665dcdf451` | `InternalVendorAdapter.lookup` (L1631). Bounded policy (module docstring + code): at most ONE network call per lookup; no retries/fanout/redirects (30x refused); no ambient proxy (`ProxyHandler({})`); no cookies/Authorization; GET only; 10 s timeout (`_VENDOR_TIMEOUT`, L107); 1 MiB body bound (`_VENDOR_MAX_BODY`, L108); deployment-owned base URL `PI_VENDOR_LOOKUP_BASE_URL` (no request-controlled endpoint); URL-encoded canonical MPN; allowlist field mapping for Ingram / CDW / Synnex EU; sensitive metadata (SessionId, BuyerAccountId, SystemId, …) stripped by construction; bounded `CommercialSourceResponse(status, retrieved_at, candidates, issues)` with `LookupStatus` SUCCESS/PARTIAL/FAILED and `SourceOutcome` USABLE/NOT_FOUND/MALFORMED_SECTION/MISSING_EXPLICIT_MPN/MPN_MISMATCH. |
| `product_intelligence/providers/commercial.py` | `c1c5fd425fd4376b5edc026faf89611ff40474e8` | Provider-neutral commercial boundary; `CommercialLookupQuery` (non-empty MPN; `__post_init__` **strips surrounding whitespace** from the MPN — interior untouched — and `InternalVendorAdapter.lookup` builds the request URL from the stripped `query.mpn`, so the transmitted MPN is the stripped form), `CommercialSourceCandidate` (Decimal price, finite nonnegative; currency; availability; price basis; quantity; note kind), `CommercialSourceIssue`, `CommercialSourceProvider` protocol. Explicitly "not authority", "not evidence storage". |
| `product_intelligence/research/commercial_supplement_codec.py` | `c83ae62bfd05ea1f08653d8b9b459fff544a2e74` | Frozen V1 codec (`_SCHEMA_VERSION_V1 = 1`): `encode_research_supplement_result` / `decode_research_supplement_result`; strict required keys, reject extra keys, Decimal-as-string, timezone-aware UTC `retrieved_at`, `vendor_mpn_match_type` EXACT/NORMALIZED_EXACT only, `brand_new_basis` exactly `VENDOR_API_POLICY`, bounded `detail` vocabulary (`None` / `"vendor_mpn_mismatch"`). Fail-closed on any violation. |
| `product_intelligence/web/views.py` | `d2678c1147dbd227f9297380620bded721e31cfa` | `research_new` (intake GET/POST, L256), `research_detail` (report GET, L345; server-side security branch before any vendor artifact access; ALLOWED → authorized replay + vendor status notice, DENIED → public replay, no vendor fact in context; FX freshness display block L677+), `research_retry` (POST, L832 — creates a NEW run; old run untouched), `research_review` (POST + CSRF, L873 — 8-step fail-closed binding validation), `research_comparables` (POST, L1031 — idempotent `trigger_comparable_research` then synchronous execution of a PENDING child; the existing precedent for operator-triggered child execution on a COMPLETED run). |
| `product_intelligence/web/urls.py` | `d2a9b0c74baff814a761d12a4e19cb74818563af` | Routes: `/healthz`, `/research/new`, `/research/<uuid>`, `/research/<uuid>/retry`, `/research/<uuid>/review/<uuid>`, `/research/<uuid>/comparables`. **No refresh endpoint exists at production.** |
| `product_intelligence/web/commercial_access.py` | `e58aaab6b99b54d3a2d5f30cd6fa48ea40ee543a` | `vendor_price_access_allowed`: fail-closed CIDR gate over `PI_VENDOR_PRICE_ALLOWED_CIDRS`; `REMOTE_ADDR` only (no forwarded headers); strict canonical CIDR parsing; absent/blank/malformed → DENY. Visibility policy only — "No identity authority, pricing authority, or research logic changes". |
| `product_intelligence/web/vendor_status_presentation.py` | `eced80442d7e439e387fdef49ec32b5b862f5d47` | Display-only, ALLOWED-only "Vendor API status" notice (states `not-recorded` / `failed` / `completed-no-quote` / `partial` / `completed`); no DB reads, no decode, no network, no prices; fails closed on unrecognized shapes. |
| `product_intelligence/runs/execution_claims.py` | `c2777c8fc55814d4e2a79229d974125a7e3a6950` | `claim_execution` / `complete_execution` / `retry_run`: database-level compare-and-set single-UPDATE pattern (portable, incl. SQLite); retry = NEW run from the old request; old run never reset. |
| `product_intelligence/runs/comparable_execution_claims.py` | `d76780102811bcd316595a92da7c56bf5e1d0d6f` | `trigger_comparable_research` (L61; idempotent; `UNIQUE(parent_run, active_slot)` race → savepoint rollback → winner lookup → unrelated `IntegrityError` re-raised), `claim_comparable_research` (L187), `complete_comparable_research` (L242; single UPDATE writes state + payload + finished atomically), `fail_comparable_research` (L312). |
| `config/settings.py` | `cfd5bcc7cd06a675d545f448fbdb86c1109b22e9` | Middleware: Security, Common, **CSRF** (`CsrfViewMiddleware`), Clickjacking — with the explicit comment that the pilot "needs no session framework, no user model, and no authentication — none of which this phase introduces". `PI_VENDOR_PRICE_ALLOWED_CIDRS` setting (L128). SQLite via `PI_SQLITE_PATH`. |
| `product_intelligence/runs/migrations/` | — | 0001–0011 at production; latest is `0011_researchfxsnapshot_acquisition_fxobservationstore`. `0008_research_supplement_snapshot.py` shows the OneToOne supplement-snapshot convention. |
| `product_intelligence/execution/__init__.py` | — | Public execution API: `execute_research_run`, `ExecutionError`, comparable trigger/execution symbols, `replay_compact_quote_projection`, `replay_public_compact_quote_projection`. |
| `tests/web/test_web_boundaries.py` | — | AST-enforced web import allowlist; `ALLOWED_EXECUTION_IMPORTS` = exactly {`execute_research_run`, `ExecutionError`, `ComparableResearchExecutionError`, `execute_comparable_research_with_default_providers`, `replay_compact_quote_projection`, `replay_public_compact_quote_projection`}; providers forbidden to web; research only via symbol allowlist. |

### 1.3 Production vs development-main divergence [VERIFIED]

The development `main` (916296a) is **not** the production baseline:

- `main` carries the entire semantic-authority V2 / Q3 work line
  (`SemanticDecisionRecord` model +221 lines in `runs/models.py`,
  `execution/orchestration.py` +87 lines, `product_intelligence/semantic/
  contract_v2*.py`, `execution/semantic_decision_*` files, corpus
  governance artifacts). None of that exists at the production SHA.
- **The PILOT-VENDOR-STATUS-UX-A surface exists at production and NOT on
  main:** `product_intelligence/web/vendor_status_presentation.py` and
  `tests/web/test_vendor_status_ux_a.py` were added in commit cde2a80 and are
  absent from main's tree (`git show cde2a80:…` succeeds; the files do not
  exist at main HEAD). `web/views.py` and `execution/compact_quote_replay.py`
  at production carry the corresponding +39/+21 lines (status notice wiring
  and the replay's `supplemental_result` field) that main lacks.
- The untracked dev-worktree investigation
  `docs/VENDOR_LOOKUP_FAILURE_INV1_REPORT.md` (run
  `82565637-…`/`MTFDKCC3T8TGP-1BK1DABYYR`) documents the production incident
  that motivates this design: the run's persisted vendor result was
  `FAILED` with zero observations (transient transport failure class), while a
  later manual Vendor API call returned valid pricing evidence from all three
  sources. This is the business case for an operator-controlled, vendor-only,
  append-on-the-side refresh.
- `docs/PRODUCT_INTELLIGENCE_STATUS.md` / `PRODUCT_INTELLIGENCE_PLAN.md` on
  main track the semantic V2 line; they do not canonically record the
  `pilot-vendor-status-ux-a` branch phases. This design therefore treats the
  production SHA itself as the sole authoritative record of the baseline.

**Consequence:** all design references below are to the production SHA. An
implementation of this design must start from the production branch
(`pilot-vendor-status-ux-a`), not from `main`. [VERIFIED constraint;
PROPOSED starting branch for the implementation — see §12.2 D9.]

### 1.4 Verified production test baseline (recorded this session) [VERIFIED]

Executed in the detached worktree at cde2a802 using the project venv
(Python 3.14.7, Django 5.2.17, pytest 9.1.1), in-memory SQLite test DB
(`tests/conftest.py`):

- Collection: **148 test files, 5959 nodes** (agent-reported historical
  baseline, subject to independent verification before any implementation;
  per-file counts recorded; e.g. `tests/providers/test_internal_vendor.py`: 165,
  `tests/providers/test_vendor_section_response.py`: 127,
  `tests/web/test_commercial_access.py`: 104,
  `tests/web/test_web_boundaries.py`: 165,
  `tests/execution/test_4d_b_vendor_commercial.py`: 19,
  `tests/research/test_commercial_supplement_codec.py`: 46,
  `tests/web/test_vendor_status_ux_a.py`: 25,
  `tests/execution/test_compact_quote_public_replay.py`: 21,
  `tests/runs/test_comparable_execution_claims.py`: 33,
  `tests/execution/test_public_replay_persisted_authority.py`: 15).
- Full suite, one run: **5959 passed, 39 subtests passed, 0 failed, 0 errors,
  0 skipped, in 415.25 s** (exit 0).
- `python manage.py check`: "System check identified no issues (0 silenced)".
- `python manage.py makemigrations --check --dry-run`: "No changes detected".

This is the recorded pre-implementation collection baseline required by §9 of
the task. Any future implementation must produce a node-level collection diff
against 5959 with **0 removed / 0 renamed** nodes (additions only), and must
preserve this suite green. The known Windows/3.14 subprocess-boundary flake
class (documented in STATUS for the dev line) did not occur in this run; if it
occurs in a future implementation run, the documented isolation-rerun rule of
the project applies and the allowlist is never expanded silently.

---

## 2. Current execution/data graph (production)

### 2.1 Research execution pipeline [VERIFIED]

```
POST /research/new (views.research_new)
  -> ResearchRun(CREATED)                       (runs/models.py L120)
  -> execute_research_run(run_id)               (execution/orchestration.py L461)
       -> claim_execution: CAS CREATED->RUNNING (runs/execution_claims.py;
          single UPDATE; at most one winner; paid work only after claim)
       -> _execute_claimed_run (L178):
            [4D-A] direct acquisition (zero paid search when sufficient)
            [4D-D] Micron alias eligibility (only when fallback required)
            [fallback] ONE SerperSearchProvider call (lazy construction)
            per candidate: fetch -> extract -> normalize -> match
            [semantic] evaluate_semantic_matches (advisory only)
            aggregate_prices (frozen 4A)
       -> _try_vendor_commercial_lookup (L1124)          # 4D-B
            only when request.manufacturer_part_number is non-empty
            only when PI_VENDOR_LOOKUP_BASE_URL is set (else: no call, no row)
            ONE InternalVendorAdapter.lookup()            (frozen bounded policy)
            frozen 2A compare_part_numbers binding per candidate:
              EXACT/NORMALIZED_EXACT -> SupplementSourceObservation
                (brand_new=True, brand_new_basis="VENDOR_API_POLICY")
              otherwise -> SupplementSourceIssue(MPN_MISMATCH,
                detail="vendor_mpn_mismatch")
            provider issues copied (bounded outcome, no raw detail)
            encode_research_supplement_result (frozen codec V1)
       -> _try_fetch_fx_rates (L1355)                     # 4D-C-A + 8A-FX-A1
            currencies from public 4A buckets + USABLE vendor observations
            USD-only -> zero ECB calls
            canonical path: cross-run FxObservationStore freshness contract
            (CACHE_HIT or ONE live fetch); injected provider bypasses cache
            FX failure is NONFATAL
       -> ATOMIC FINAL PUBLICATION (transaction.atomic, L575):
            PriceIntelligenceSnapshot.create (schema_version=1)
            _create_review_candidates (AiAssistedReviewCandidate rows)
            ResearchSupplementSnapshot.create  (iff lookup attempted)
            ResearchFxSnapshot.create          (iff FX obtained;
                                               acquisition LIVE|CACHE_HIT)
            complete_execution: CAS RUNNING->COMPLETED
       -> ANY exception after claim: _terminalize_run (RUNNING->FAILED),
          ExecutionError raised; already-terminal runs are never changed
```

### 2.2 Historical report read path (GET /research/<uuid>) [VERIFIED]

```
views.research_detail (L345):
  load run + PriceIntelligenceSnapshot; decode; request-provenance check
  (decoded.request == run.to_research_request()) — fail-closed on mismatch
  vendor_commercial_access_allowed = vendor_price_access_allowed(request)
  (CIDR gate decided BEFORE any vendor artifact is read)

  ALLOWED branch:
     replay_compact_quote_projection(run_id)
        = decode PriceIntelligenceSnapshot + ResearchFxSnapshot
          + ResearchSupplementSnapshot (SOLE decoder of the vendor artifact)
        -> CompactQuoteProjection (vendor rows first, then human-confirmed,
           AI-unreviewed, public, quote-only)
        -> replay.supplemental_result exposed for the display-only
           Vendor API status notice (web/vendor_status_presentation.py)
  DENIED branch:
     replay_public_compact_quote_projection(run=run)
        = decode the run's own PriceIntelligenceSnapshot + ResearchFxSnapshot
        -> vendor-free projection; NEVER reads ResearchSupplementSnapshot,
           NEVER imports the commercial supplement codec
  Template context carries no vendor fact for DENIED connections.
  Zero live provider/network/semantic work on GET (frozen replay invariant).
```

### 2.3 Snapshot authority map [VERIFIED]

| Persisted artifact | Model | Authority (frozen) |
|---|---|---|
| Machine Price / public buckets | `PriceIntelligenceSnapshot` (OneToOne, PK=run) | Sole source of frozen 4A machine price, public rows, report statistics. Never written by vendor/FX/refresh paths. |
| Vendor commercial evidence | `ResearchSupplementSnapshot` (OneToOne, PK=run) | Supplemental display evidence only. Does NOT modify `PriceIntelligenceSnapshot`; never enters Machine Price, Reviewed Price, deterministic identity authority, semantic authority, or comparable scoring (PLAN §26.3, `providers/commercial.py` contract). Absent iff the lookup was not attempted. |
| FX evidence | `ResearchFxSnapshot` (OneToOne, PK=run; `acquisition` LIVE/CACHE_HIT) | DISPLAY-SUPPLEMENTAL only; original source amount+currency remain authoritative. Absent iff no FX evidence obtained. |
| Human review | `AiAssistedReviewCandidate` (FK run) | Run-scoped CONFIRMED/REJECTED overlay; identity authority only; never mutates the price snapshot. |
| Comparables | `ComparableResearchExecution` (FK parent_run, `active_slot` unique) | Separate child lifecycle; `UNIQUE(parent_run, active_slot)` enforces at most one active child; CAS trigger/claim/complete/fail. |
| Cross-run FX content | `FxObservationStore` | Acquisition content store; written only by successful canonical live acquisition; never read on historical GET. |

### 2.4 Existing concurrency/idempotency precedents [VERIFIED]

- `claim_execution` / `complete_execution`: compare-and-set single-UPDATE
  (portable on SQLite); loser gets a bounded `ClaimExecutionFailed` with an
  explicit reason; no second paid call is possible after a failed claim.
- `trigger_comparable_research`: idempotent trigger — returns an existing
  active child, else an existing COMPLETED child, else creates a PENDING
  child; `UNIQUE(parent_run, active_slot)` is the hard invariant against
  concurrent double creation; on `IntegrityError`, the failing savepoint
  rolls back and the winner is looked up outside the failed scope; unrelated
  `IntegrityError` propagates.
- `research_comparables` view: POST (CSRF-protected) trigger + synchronous
  execution of the PENDING child; RUNNING/COMPLETED children are not
  re-executed; claim races are bounded.
- `research_retry`: retry = NEW run; the old failed run is immutable history.

There is **no** existing mechanism to re-acquire any supplemental evidence
for a terminal run: no refresh command, no refresh endpoint, no refresh
model. [VERIFIED: absence]

### 2.5 The vendor failure shape this feature addresses [VERIFIED]

`InternalVendorAdapter.lookup()` returns `CommercialSourceResponse(
status=FAILED, retrieved_at=None, candidates=(), issues=())` for bounded
transport failure classes (timeout, connection error, HTTP error incl.
refused 30x, oversized body, non-UTF-8, unrecognized contract). The
orchestration encodes that as a supplement payload with `lookup_status=
"FAILED"`, zero observations, zero issues — the exact shape of the
documented production incident (VENDOR_LOOKUP_FAILURE_INV1). The original
row is durable history; nothing in production can later re-attempt the
vendor lookup for that run without creating a whole new ResearchRun
(`research_retry`), which is explicitly forbidden by the business
requirement.

---

## 3. Proposed data model and lifecycle

### 3.1 New model: `VendorRefreshExecution` [PROPOSED]

Lives in `product_intelligence/runs/models.py` (the only package with Django
models — layer rule). Structurally modeled on `ComparableResearchExecution`
(7C-A), which is the existing production precedent for a parent-run-scoped,
append-only, active-slot-guarded child execution. The model is storage, not
interpretation: the payload schema is owned by the codec (below), exactly as
with all other snapshot models.

```python
class VendorRefreshState:
    PENDING = "PENDING"; RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"; FAILED = "FAILED"

class VendorRefreshFailureReason:
    VENDOR_LOOKUP_CONFIG_MISSING     = "VENDOR_LOOKUP_CONFIG_MISSING"
    MPN_BINDING_VIOLATION            = "MPN_BINDING_VIOLATION"
    MPN_QUERY_NORMALIZATION_MISMATCH = "MPN_QUERY_NORMALIZATION_MISMATCH"
    RESULT_ENCODING_FAILED           = "RESULT_ENCODING_FAILED"
    EXECUTION_INTERRUPTED            = "EXECUTION_INTERRUPTED"
    INTERNAL_ERROR                   = "INTERNAL_ERROR"

class VendorRefreshTriggerSource:
    MANAGEMENT_COMMAND = "MANAGEMENT_COMMAND"   # only V1 member
```

Failure-reason semantics notes (DESIGN2-FU1 C1/C7):

- `MPN_QUERY_NORMALIZATION_MISMATCH`: the frozen `CommercialLookupQuery`
  would transmit an MPN different from the immutable captured binding
  (surrounding-whitespace stripping, §1.2); the attempt fails closed
  BEFORE any network call (§3.4 step 4). The requested binding is never
  silently altered.
- `EXECUTION_INTERRUPTED`: reserved for the future R1 operational recovery
  gate (§3.6). **No R0 code path writes it.** Its semantics are "the
  execution was interrupted; the external Vendor request outcome is
  explicitly UNKNOWN" — it must never be read as "the lookup failed".
- `MPN_BINDING_VIOLATION`: the execution-time re-check found
  `child.requested_mpn != parent.manufacturer_part_number` — an
  application-level invariant (§3.4 step 2); no single-row CHECK can
  express it (C6).

Fields:

| Field | Type / constraint | Meaning |
|---|---|---|
| `id` | UUID PK, app-generated, `editable=False` | Refresh execution identity. |
| `parent_run` | FK `ResearchRun`, `CASCADE`, `related_name="+"` | The already-COMPLETED ResearchRun whose original canonical MPN is refreshed. No reverse accessor (mirrors 7C-A). |
| `requested_mpn` | `TextField`, `editable=False`, CHECK non-empty | **Immutable requested canonical MPN binding.** Set at trigger time to `parent_run.manufacturer_part_number` verbatim. Re-verified against the parent at execution time; a mismatch is `MPN_BINDING_VIOLATION` (fail-closed), never a silent rewrite. |
| `state` | CharField, choices PENDING/RUNNING/COMPLETED/FAILED, `editable=False` | Controlled execution state. |
| `active_slot` | PositiveSmallIntegerField, null, `editable=False` | 1 iff PENDING/RUNNING else NULL (7C-A sentinel). |
| `trigger_source` | CharField, CHECK in {MANAGEMENT_COMMAND} for V1, `editable=False` | Explicit provenance of who/what class of actor triggered the refresh. Bounded vocabulary, extensible by a later approved phase. |
| `operator` | CharField(128), CHECK non-empty, `editable=False` | Recorded identity string of the self-reported actor who **TRIGGERED** the refresh (the INSERT of the PENDING row; see §4.2/§4.5/§4.6). Set once at trigger time; never modified by claim, complete, or fail. It is NOT by itself an attestation of who eventually claims and executes a PENDING child — trigger and claim are distinct primitives (§3.3), and R1 must prevent that gap from silently producing an inaccurate execution-provenance claim (§4.6). Free text, bounded length; never a secret; recorded as provided. |
| `created_at` | DateTimeField, `editable=False` | Trigger/creation instant. |
| `started_at` | DateTimeField, null, `editable=False` | Claim instant (PENDING→RUNNING). |
| `finished_at` | DateTimeField, null, `editable=False` | Terminal instant. |
| `result_schema_version` | PositiveSmallIntegerField, null, `editable=False` | Codec version of `result_payload`; NULL until COMPLETED; V1 = 1 (the frozen supplement codec version). |
| `result_payload` | JSONField, null, `editable=False` | Codec-validated vendor supplemental payload (frozen `commercial_supplement_codec` V1 — §3.2). NULL until COMPLETED. |
| `failure_reason` | CharField(64), null, `editable=False` | Bounded vocabulary value; NULL except when FAILED. |

Constraints (CHECK on the stored row, so they hold for any writer):

1. `active_slot` ∈ {1, NULL}.
2. `UNIQUE(parent_run, active_slot)` → **at most one active (PENDING/RUNNING)
   refresh per parent run** (the hard concurrency invariant).
3. Lifecycle shape (exactly one of):
   - PENDING: `active_slot=1`, `started_at=NULL`, `finished_at=NULL`,
     `result_*`=NULL, `failure_reason=NULL`;
   - RUNNING: `active_slot=1`, `started_at!=NULL`, `finished_at=NULL`,
     result fields NULL, `failure_reason=NULL`;
   - COMPLETED: `active_slot=NULL`, both start/finish set,
     `result_schema_version>=1`, `result_payload!=NULL`,
     `failure_reason=NULL`;
   - FAILED: `active_slot=NULL`, both start/finish set,
     `result_*`=NULL, `failure_reason` in the bounded vocabulary.
4. `requested_mpn` non-empty; `operator` non-empty; `trigger_source` in the
   vocabulary.
5. Index `(parent_run, created_at, id)` for deterministic history reads
   (ordering + identical-timestamp tie-breaker, §8.3).

Append-only semantics (application-level):

- In application code, rows are written only through the four CAS lifecycle
  paths (trigger-insert / claim / complete / fail). There is **no** service
  that writes a COMPLETED or FAILED row in place, and **no** UPDATE path
  anywhere in the design touches `ResearchSupplementSnapshot`,
  `PriceIntelligenceSnapshot`, `ResearchFxSnapshot`,
  `ResearchMicronAliasSnapshot`, `ComparableResearchExecution`,
  `ExecutionEvidenceRecord`, `AiAssistedReviewCandidate`, or `ResearchRun`
  for a refreshed run.
- A later successful refresh does not supersede, reinterpret, or erase an
  earlier FAILED refresh or the original FAILED supplemental snapshot: each
  attempt is a distinct durable row. "Reinterpreting a prior failed vendor
  lookup as successful" is unrepresentable — the original row's payload is
  byte-frozen history.
- Deleting the parent `ResearchRun` cascades to all refresh rows (same as
  7C-A).

**Immutability accuracy — what the constraints do and do not guarantee
(corrected per DESIGN2-FU1 C6):**

- `editable=False` is Django model/ORM metadata (form and admin behavior);
  it does **not** prevent arbitrary ORM `QuerySet.update()` calls or raw SQL.
  No field flag in this model is claimed to be a write barrier, and no test
  may assert that `editable=False` itself rejects arbitrary writes.
- The DB CHECK/UNIQUE constraints enforce **valid stored shapes** (the
  lifecycle shapes above; `active_slot` ∈ {1, NULL}) and **at most one
  active child per parent run** — for any writer that goes through the
  database.
- The CAS services in `runs/vendor_refresh_claims.py` enforce the
  **permitted application state transitions** (single conditional UPDATE;
  a transition whose preconditions do not match affects zero rows and
  raises a bounded error).
- Neither CHECK constraints nor `editable=False` **prove a row was never
  modified** after commit. The durability claim is therefore stated exactly:
  no application write path exists other than the four CAS primitives, the
  stored shapes are database-enforced, and the tests pin both. Rows are
  durable application history, not tamper-proof records.
- Parent/child canonical MPN equality is validated by **application
  services** (the trigger-time copy + the execution-time re-check, §3.4
  steps 1–2), not by any proposed single-row CHECK constraint (a single-row
  CHECK cannot reference the parent row).
- Frozen codec validity of `result_payload` is validated by the appropriate
  **producer** (the frozen `encode_research_supplement_result` before the
  complete CAS) and **reader** (the frozen
  `decode_research_supplement_result` in history replay, failing closed),
  not merely by the JSONField NOT NULL constraint or the
  `result_schema_version >= 1` CHECK. The complete service additionally
  verifies that the stored `result_schema_version` agrees with the payload's
  codec schema version (frozen V1 = 1; §3.4 step 8; DESIGN2-FU1 C7).

### 3.2 Payload codec: reuse the frozen V1 supplement codec [PROPOSED]

`result_payload` is encoded with the **existing, unmodified**
`research/commercial_supplement_codec.py` V1 codec
(`encode_research_supplement_result` / `decode_research_supplement_result`)
over the same frozen dataclasses
(`ResearchSupplementResult` / `VendorCommercialResult` /
`SupplementSourceObservation` / `SupplementSourceIssue`).

Rationale (all verified against the frozen codec):

- The business object of a refresh is exactly "one vendor lookup result":
  `lookup_status` SUCCESS/PARTIAL/FAILED, `retrieved_at`, identity-bound
  observations (EXACT/NORMALIZED_EXACT, `brand_new` VENDOR_API_POLICY), and
  bounded source issues. The codec already validates every one of these
  fail-closed, including Decimal exactness and the controlled `detail`
  vocabulary.
- A second codec version for identical content would create a second schema
  to keep honest and would blur "one canonical MPN lookup result" semantics.
- The codec is research-layer (Django-free, provider-free) and already on the
  web boundary allowlist for error-type imports; reuse changes no layer rule.

The refresh-specific provenance (parent run, MPN binding, operator, trigger
source, lifecycle timestamps) lives in the **model columns**, not the payload,
so a decoded payload can never be mistaken for a different run's evidence and
the payload stays byte-comparable with the original supplemental payload
schema. `result_schema_version` = 1.

**No changes** are proposed to the frozen codec, the FX codec, or any replay
codec. [PROPOSED invariant; matches task constraint "Do not silently modify
frozen FX codec or replay semantics."]

### 3.3 Lifecycle service: `runs/vendor_refresh_claims.py` [PROPOSED]

Runs-layer CAS primitives, structurally identical to
`comparable_execution_claims.py` (verified precedent):

- `trigger_vendor_refresh(run_id, *, operator, trigger_source=MANAGEMENT_COMMAND)
  -> VendorRefreshExecution`
  Eligibility (fail-closed, bounded reasons):
  1. parent exists (`PARENT_NOT_FOUND`);
  2. parent state is **COMPLETED** (`PARENT_NOT_COMPLETED`) — PARTIALLY_
     COMPLETED / FAILED / RUNNING / CREATED are not eligible (task: "already
     COMPLETED"; aligns with 7C-A);
  3. parent has a `PriceIntelligenceSnapshot` (`NO_SNAPSHOT`) — defensive
     invariant check mirroring 7C-A (a constructed COMPLETED row always has
     one; a row without one is anomalous and refused);
  4. `parent_run.manufacturer_part_number` is non-empty (`NO_MPN`) — a
     description-only run has no canonical MPN to refresh;
  5. the original `ResearchSupplementSnapshot` **may be absent** (run created
     before vendor config, or no-MPN-at-intake edge): absence is NOT an
     eligibility error — the refresh history then simply shows "original:
     not recorded" (§8.4). [PROPOSED — safe behavior per task §4.]

  Idempotency semantics — three distinct concepts (DESIGN2-FU1 C2):

  1. **Active-child deduplication (PENDING/RUNNING).** A trigger while an
     active child exists returns the existing active child; it creates
     nothing and executes nothing. Together with the CAS single-claim (at
     most one claim winner, at most one Vendor call per attempt), this is
     the ONLY duplicate suppression R0 guarantees.
  2. **Intentional post-terminal refresh (new child).** A new explicit
     operator invocation after all children are terminal creates a NEW
     PENDING child — a new attempt and a new timestamped evidence point;
     no prior child is rewritten (history stays append-only).
  3. **Retransmission of the SAME logical request (no new child).** A
     duplicate of one logical trigger operation (e.g., a client retry after
     a timeout when the original request's outcome is unknown) must not
     create a new child. R0 does NOT implement this: with no stable request
     idempotency identity, a post-terminal re-invocation is indistinguishable
     from concept 2 and is treated as concept 2. **R3 (the future web
     surface) MUST use an explicit, stable request idempotency identity or
     an equivalently proven protocol**; looking up the latest terminal child
     is NOT sufficient to distinguish a retransmission from an intentional
     post-terminal refresh. The R3 mechanism is NOT added to R0.

  Provenance note (DESIGN2-FU2): the trigger records its self-reported
  `operator` at INSERT time — the TRIGGER initiator (§3.1), not necessarily
  the actor of a later invocation that claims and executes the PENDING
  child (R1). Returning an existing active child (concept 1) neither
  transfers nor re-attests that field; R1 must prevent an inaccurate
  execution-provenance claim (§4.6).

  Trigger behavior (R0):
  - existing active child (PENDING/RUNNING) → return it, create nothing,
    execute nothing (concept 1);
  - existing terminal children → do NOT block a new explicit invocation:
    create a new PENDING child (concept 2 — refreshing again later is the
    feature; history stays append-only);
  - creation race → `UNIQUE(parent_run, active_slot)` fires for the loser;
    the failing savepoint rolls back; the winner is looked up outside the
    failed scope; an unrelated `IntegrityError` re-raises (7C-A pattern).

- `claim_vendor_refresh(child_id) -> VendorRefreshExecution`
  CAS `PENDING + active_slot=1 + started_at NULL → RUNNING` (single UPDATE);
  at most one winner; the winner is the only execution that may subsequently
  issue complete/fail for this row (§3.3 state-transition table, §4.6);
  claim does not modify `operator` (the recorded trigger initiator, §3.1);
  loser gets `VendorRefreshClaimError`.

- `complete_vendor_refresh(child_id, result_schema_version, result_payload, *,
  at=None)`
  CAS `RUNNING + active_slot=1 + finished_at NULL → COMPLETED` writing
  `state, active_slot=NULL, finished_at, result_schema_version,
  result_payload` in ONE UPDATE. No committed state exists in which a
  COMPLETED child lacks its payload.

- `fail_vendor_refresh(child_id, failure_reason, *, at=None)`
  CAS `RUNNING + active_slot=1 + finished_at NULL → FAILED` writing
  `state, active_slot=NULL, finished_at, failure_reason` in ONE UPDATE;
  `failure_reason` validated against the bounded vocabulary.

**Final R0 state-transition table (binding, DESIGN2-FU2).** The four
primitives above are the COMPLETE set of legal row transitions in R0.
Complete and fail are REQUIRED, normal, and legal: they are how a claim
winner terminates its own attempt. What R0 forbids is EXTRA, recovery-based
terminalization (the rejected proposal below and the "No recovery-based
terminalization in R0" rule that follows it).

| # | Transition | Primitive | CAS precondition (WHERE clause of the single UPDATE) | Effect | Legal in R0 |
|---|---|---|---|---|---|
| 1 | (no row) → PENDING | trigger | parent eligible (§3.3) AND no active child (`UNIQUE(parent_run, active_slot)`) | INSERT: state=PENDING, active_slot=1, requested_mpn / operator / trigger_source / created_at set | Yes |
| 2 | PENDING → RUNNING | claim | state=PENDING, active_slot=1, started_at IS NULL | state=RUNNING, started_at set | Yes — at most one winner |
| 3 | RUNNING → COMPLETED | complete | state=RUNNING, active_slot=1, finished_at IS NULL | state=COMPLETED, active_slot=NULL, finished_at, result_schema_version, result_payload in ONE UPDATE (atomic result publication) | Yes — at most one winner |
| 4 | RUNNING → FAILED | fail | state=RUNNING, active_slot=1, finished_at IS NULL | state=FAILED, active_slot=NULL, finished_at, failure_reason (bounded vocabulary) in ONE UPDATE | Yes — at most one winner |
| 5 | PENDING → COMPLETED/FAILED (skipping RUNNING) | — | — | — | NO — no primitive terminalizes a PENDING row directly |
| 6 | RUNNING → PENDING (reset / stale reclaim) | — | — | — | NO — forbidden in R0 |
| 7 | RUNNING → RUNNING (reassignment to another execution) | — | — | — | NO — forbidden in R0 |
| 8 | COMPLETED/FAILED → any state | — | — | — | NO — terminal is terminal |
| 9 | RUNNING → terminal by recovery (stale reclaim, threshold-triggered forced failure, operator-forced interruption) | — | — | — | NO in R0 — forbidden; the ONLY RUNNING→terminal transitions are rows 3–4, issued by the claim winner's own execution. The R1 operational recovery gate (§3.6) is a future, separately-reviewed mechanism — NOT an R0 primitive. |

No test may assert that row 3 (RUNNING→COMPLETED) or row 4 (RUNNING→FAILED)
is prohibited; the required R0 regression contract is §10.3(1).

- **(REJECTED — DESIGN2-FU1 C1.)** The earlier draft proposed an optional
  `reclaim_stale_running_vendor_refresh` primitive (CAS `RUNNING +
  active_slot=1 + finished_at NULL + started_at < (now - STALE_THRESHOLD) →
  FAILED(EXECUTION_INTERRUPTED)` with a 60-second threshold, D3 option (a)).
  That proposal is REJECTED and removed from this design: a 10-second
  urllib socket timeout is a per-operation socket timeout, **not** a
  10-second absolute wall-clock deadline on the attempt (the call, the DB
  transactions, binding, encoding, and process scheduling all add time),
  and a RUNNING process may still be alive — mid-call or mid-write — long
  after any fixed threshold. Reclaiming the slot on wall-clock age alone
  would let a second attempt start while the first may still issue its
  Vendor request: an overlapping outbound request justified merely by
  reclaiming a database slot.

**No recovery-based terminalization in R0 (binding; DESIGN2-FU1 C1,
clarified per DESIGN2-FU2).** R0 implements exactly four primitives
(trigger / claim / complete / fail), and complete/fail ARE the only legal
RUNNING→terminal transitions (state-transition table above). What is
forbidden in R0 is EXTRA recovery-based terminalization of an allegedly
stale or interrupted RUNNING execution, without trusted proof that the
original execution has stopped:

- NO reclaim primitive; NO `--reclaim-stale` flag;
- NO threshold-triggered forced failure;
- NO automatic retry;
- NO RUNNING→PENDING reset;
- NO operator-forced interruption/recovery primitive;
- NO reassignment of an existing RUNNING attempt to another execution;
- a RUNNING child continues to occupy its active slot, so no second attempt
  (and thus no second Vendor request) can start for the same parent while
  it exists;
- one execution identity per attempt is preserved (an attempt is its row).

The future **R1 operational recovery gate** is specified in §3.6: manual
interruption only on sufficient trusted external evidence that the prior
execution process is terminated (a wall-clock threshold alone is
insufficient); any terminalization via an atomic conditional transition;
the external Vendor outcome preserved as explicitly unknown; no overlapping
outbound request justified by slot reclaim. This design invents no
distributed lease, scheduler, or process supervisor.

All four primitives are exported through the `product_intelligence.runs`
public API (extend the lazy `__getattr__` export maps; no model leaks into
web beyond public symbols).

### 3.4 Execution orchestration: `execution/vendor_refresh.py` [PROPOSED]

```
execute_vendor_refresh(child_id, *, vendor_adapter=None)
  1. child = claim_vendor_refresh(child_id)          # CAS; losers no-op
  2. parent = load parent_run
     re-check: parent COMPLETED (defensive; else fail INTERNAL_ERROR)
     re-check: child.requested_mpn == parent.manufacturer_part_number
               (else fail MPN_BINDING_VIOLATION)
  3. if PI_VENDOR_LOOKUP_BASE_URL absent/blank:
         fail VENDOR_LOOKUP_CONFIG_MISSING            # bounded, no call made
     (mirrors 4D-B: configuration absence is a no-attempt state)
  4. query = CommercialLookupQuery(mpn=child.requested_mpn)
     VERIFY query.mpn == child.requested_mpn (exact string equality;
     DESIGN2-FU1 C7): the frozen query type strips surrounding whitespace
     (§1.2), so a captured binding carrying any surrounding whitespace would
     be transmitted in a different, normalized form. On ANY mismatch: fail
     MPN_QUERY_NORMALIZATION_MISMATCH with ZERO network calls — fail closed,
     never silently alter the requested binding.
  5. adapter = vendor_adapter or InternalVendorAdapter()
     response = adapter.lookup(query)
        # THE single network call of this attempt (frozen adapter policy:
        # one GET, 10 s, 1 MiB, no retries, no redirects, no proxy,
        # allowlist mapping, sensitive metadata stripped)
  6. frozen 2A binding, identical policy to _try_vendor_commercial_lookup:
     for candidate: compare_part_numbers(child.requested_mpn,
                                         candidate.explicit_candidate_mpn)
       EXACT / NORMALIZED_EXACT -> SupplementSourceObservation
         (brand_new=True, brand_new_basis="VENDOR_API_POLICY")
       else -> SupplementSourceIssue(MPN_MISMATCH, "vendor_mpn_mismatch")
     provider issues copied (bounded outcome, detail=None)
  7. final_status = "FAILED" (transport failure) else response.status.value;
     retrieved_at from response
     encoded = encode_research_supplement_result(...)   # frozen codec V1
  8. complete_vendor_refresh(child_id, 1, encoded)
     # the complete service verifies, BEFORE the CAS write, that the stored
     # result_schema_version agrees with the payload's codec schema version
     # (frozen V1 = 1; DESIGN2-FU1 C7); a disagreement is a programming
     # error (bounded; no row is written)

  BOUNDARY (single outer catch, after claim):
  - SupplementCodecError / adapter programming error / invariant violation
    -> fail_vendor_refresh(bounded reason) then raise
       VendorRefreshExecutionError
  - fail persistence itself impossible (DB down) -> propagate; child remains
    RUNNING, occupying its active slot; R0 provides NO in-band reclaim,
    reset, or recovery-based terminalization for it — the only
    RUNNING->terminal transitions are the complete/fail CAS primitives
    (§3.3), which this stopped claim winner will not issue; resolution is
    the future R1 operational recovery gate (§3.6)
```

Notes:

- A **vendor transport failure is a bounded vendor RESULT, not an execution
  failure**: the child completes COMPLETED with payload `lookup_status=
  FAILED` (exactly the 4D-B semantics, verified in
  `tests/execution/test_4d_b_vendor_commercial.py` case E). `state=FAILED`
  is reserved for refresh-machinery defects (§9 matrix).
- Step 6/7 duplicate the 4D-B binding/encoding policy, not its code path:
  the implementation should extract the shared binding+encoding helper from
  `_try_vendor_commercial_lookup` into one private function used by both the
  original lookup and the refresh (single policy, two call sites). This is a
  refactoring of an orchestration private, behavior-identical, covered by the
  existing 4D-B suites; it must not change any observable 4D-B behavior.
  [PROPOSED — flagged for review as the one touch to 4D-B-adjacent code.]
- The adapter is injectable for deterministic tests (the frozen test
  precedent: all existing vendor tests are zero-network via mocks).

### 3.5 Default-provider runtime + command surface [PROPOSED — R1 phase scope, §11]

Phase ownership (DESIGN2-FU2): both artifacts below are R1. R0 ships no
management command, no default-provider runtime, and no provider call of any
kind (§11).

- `execution/vendor_refresh_runtime.py`
  `execute_vendor_refresh_with_default_providers(child_id)` — thin adapter
  constructing `InternalVendorAdapter()` only, mirroring
  `comparable_runtime.py` (the only place in the web/command stack touching
  the concrete provider class).
- `runs/management/commands/vendor_refresh.py` — `vendor_refresh` (see §4).

### 3.6 Transaction boundaries and crash/recovery semantics [PROPOSED]

| Phase | Durable effect | Transaction | Crash window consequence |
|---|---|---|---|
| Trigger | PENDING row inserted (`active_slot=1`) | single INSERT (own implicit tx; savepoint on the uniqueness race) | Crash after commit: row persists; next trigger returns it; next command invocation claims+executes it. **Zero** API calls were made (call happens only post-claim). |
| Claim | CAS PENDING→RUNNING, `started_at` set | single UPDATE | Crash: row RUNNING, still occupying the active slot. The claim winner was the only party that may call the API. R0 has NO in-band recovery or recovery-based terminalization (§3.3): the row stays RUNNING until the future R1 operational recovery gate (below) resolves it on trusted external evidence; no new attempt for this parent while it is RUNNING. |
| Vendor call | — (network, OUTSIDE any DB transaction, mirroring 4C "call the search provider (outside transaction)") | none | Crash mid-call: at most one HTTP request was sent; the row is RUNNING with no payload. Never COMPLETED, never re-read as success; the external outcome stays explicitly unknown. |
| Complete | CAS RUNNING→COMPLETED writing payload+version+`finished_at` | single UPDATE | Crash before: row stays RUNNING, occupying the active slot (§3.3; no R0 reclaim). Crash after: durable history. A COMPLETED row without payload is structurally impossible (constraint 3). |
| Fail | CAS RUNNING→FAILED writing reason+`finished_at` | single UPDATE | Crash before: row RUNNING, occupying the active slot (§3.3; no R0 reclaim). |

Recovery rule (corrected per DESIGN2-FU1 C1; clarified per DESIGN2-FU2):
**there is no automatic AND no in-band recovery of RUNNING rows in R0 — no
reclaim, no threshold-triggered forced failure, no RUNNING→PENDING reset,
no automatic retry, no operator-forced interruption, no reassignment.**
The ONLY RUNNING→terminal transitions in R0 are the complete and fail CAS
primitives (§3.3 table), which may be issued only by the execution that won
the claim. A RUNNING row is therefore either (a) a live in-flight refresh —
its claim winner may still issue complete/fail normally (reported as
in-progress by the next trigger, never re-executed) — or (b) an interrupted
attempt whose claim winner is dead or unknown: it will not issue complete/
fail, and NO R0 recovery path substitutes for it. In case (b) the row is
neither forcibly terminalized, reclaimed, nor reset; it continues to occupy
its active slot, so "one attempt = one row" holds and no recovery path can
start a double network call. A 10-second urllib socket timeout is a
per-operation socket timeout, **not** an absolute wall-clock deadline: a
RUNNING process may still be alive after the threshold, so no age-based rule
may treat the row as dead.

**Future R1 operational recovery gate (specified now; NOT R0 scope):**
manual interruption of a RUNNING row is permissible **only** when sufficient
trusted external evidence proves the prior execution process is terminated
(e.g., verified host process/deployment evidence). A wall-clock threshold
alone is insufficient. Any terminalization must use an **atomic conditional
transition** (one CAS UPDATE matching the full RUNNING precondition; the
row then records `EXECUTION_INTERRUPTED` with the semantics "execution
interrupted; the external Vendor request outcome is explicitly UNKNOWN" —
the prior request may have been sent and may have completed; the
terminalization must NOT imply that it failed or never happened). No
overlapping outbound request may be justified merely by reclaiming a
database slot. This design invents no distributed lease, scheduler, or
process supervisor; the gate is an operational procedure plus one atomic
transition, detailed at R1 review.

---

## 4. Authorization architecture

### 4.1 Verified current state [VERIFIED]

- The pilot has **no application authentication, no sessions, no user
  model** (`config/settings.py` middleware comment; PLAN §19:
  "Authentication and authorization are DEFERRED … 8C remains the formal
  production-hardening/authentication phase").
- The only vendor-related control is the **display** gate
  `vendor_price_access_allowed` (CIDR over `REMOTE_ADDR`, fail-closed) —
  explicitly "presentation visibility policy", not identity, not mutation
  authority (module docstring; PLAN §26.6).
- All existing POST mutations (intake submit, retry, review, comparables
  trigger) are CSRF-protected but reachable by **anyone who can reach the
  server**. PLAN §19 records the project-lead decision for the pilot:
  "people who can reach the internal pilot server are currently considered
  authorized for this pilot" — an acceptable statement for *reading* public
  reports; the task correctly states it is **not** acceptable for a
  *privileged mutation* that spends Vendor API traffic and writes durable
  commercial evidence rows.
- The production deployment is a Windows host running Waitress with
  `manage.py` commands as the standard operational interface
  (`docs/INTERNAL_PILOT_DEPLOYMENT.md`: migrations, `pilot_check`, launcher
  `.cmd` scripts).

### 4.2 Option A — explicitly invoked, operator-restricted Windows CMD
management command [PROPOSED]

R1 surface (the `vendor_refresh` management command belongs to R1, not R0 —
§11; R0 has no command surface at all. NO `--reclaim-stale` — reclaim is
rejected, §3.3; the only repeat flag is the R1 repeat safeguard
`--force-repeat`, §5.2/D6):

`python manage.py vendor_refresh <run-uuid> --operator <identity>`

- **Authorization boundary:** real mutation authorization for this command
  comes from controlled **Windows account access** on the deployment host
  (plus executable/deployment access, database-file ACLs, and the
  operational controls of the pilot runbook) — the OS account of the person
  (or script) executing the command. Host access is a strictly stronger
  boundary than subnet reachability: the runbook already requires CMD
  access for `migrate` / `pilot_check`.
- **`--operator` is self-reported provenance, NOT authentication
  (DESIGN2-FU1 C4):** it is mandatory and recorded verbatim on the row as
  the invoking actor's self-declared identity, layered ON TOP of host
  access; anyone with host access can supply any string, so the field must
  never be described as identity proof. `USERNAME` (or any other OS
  environment data) is NOT trusted identity proof; if such a value is ever
  recorded (D4 option (a)), it is a labeled untrusted OS-context
  correlation aid only. Shared administrative accounts reduce actor
  attribution — `--operator` mitigates but does not solve this. This design
  makes NO claim that trustworthy OS audit evidence (e.g., Windows event
  logs) exists; that claim requires production verification. **R1
  deployment prerequisite:** an explicit host permissions and operational
  audit review (who has host/CMD access, how command invocations are
  logged, how the database file and its directory are ACL-controlled) must
  be completed and recorded before R1 deploys. No Django authentication,
  user model, or session is built in this task (8C remains the formal
  authentication phase).
- **No new network attack surface:** no URL, no form, no CSRF token, no
  client that can discover or replay the action. "Knowledge of the run UUID"
  alone is useless without host access.
- **Auditability:** each attempt is a durable row (operator, trigger_source,
  timestamps, result) plus the command's bounded stdout (which the operator
  can redirect); nothing is silent.
- **Secrets:** no new secrets. `PI_VENDOR_LOOKUP_BASE_URL` already lives in
  the server environment; the command runs in that environment. No
  credentials in the command line (UUID + operator name only — operator name
  is identity, not a secret).
- **Bounded blast radius:** at most one in-flight refresh per run; at most
  one Vendor API call per claim; no phase of R0–R1 introduces a general
  rate limiter (DESIGN2-FU1 C5; R0 has no command surface at all). The R1
  command displays the existing active state and the most recent terminal
  attempt before a new invocation, so an operator can see whether a
  re-trigger is redundant. The R1 minimal CMD repeat safeguard (DESIGN2-FU1
  C5; ordering corrected per DESIGN2-FU2; §5.2): if a terminal attempt
  occurred within the preceding 5 minutes, an explicit `--force-repeat` is
  required to authorize another attempt; the safeguard is evaluated BEFORE a
  new refresh attempt is persisted (before the trigger INSERT) and BEFORE
  any new Vendor API request — a cooldown refusal leaves NO newly created
  PENDING child behind; any repeated attempt is a NEW child, never a rewrite
  of a prior child; concurrent invocations are reviewed separately at R1.
  This is an operator-safety check on the command surface — clearly distinct
  from a server-enforced comprehensive rate limit, which requires identity
  and remains out of scope (D6).

Weaknesses (honest): not reachable from the browser (acceptable in phase 1);
OS-account identity is coarse when admin accounts are shared (mitigated —
never solved — by the mandatory self-reported `--operator` provenance, §4.5);
a compromised host can invoke the command (true of any server-side
capability — the threat model is external/subnet actors, and this removes
them from the mutation surface entirely).

### 4.3 Option B — authenticated Web POST action [PROPOSED analysis]

A `POST /research/<uuid>/vendor-refresh` route would be CSRF-protected, but
with no authentication system its effective authorization is
"REMOTE_ADDR ∈ allowed CIDR + CSRF token" — i.e., **every pilot user on the
trusted subnet** becomes an operator of a privileged mutation: they can
spend Vendor API traffic at will (each trigger = up to one external call),
write durable commercial-evidence rows, and force refresh history growth.
CSRF does not help (there is no session to forge; any same-origin page —
including the app's own report pages — can post). UUID knowledge + subnet
presence is exactly the combination the task forbids as authorization.

Making Option B *safe* requires an authenticated operator identity (login,
session, role) — that is the 8C scope the project has explicitly deferred.
Building a one-endpoint credential system now would be a mini-authentication
design without the rest of the identity substrate, contradicting the
frozen §19 sequencing.

### 4.4 Recommendation [PROPOSED]

**Phase 1: Option A.** The trigger surface is the management command on the
server host. Mutation authorization is the controlled Windows host access
itself (account, executable, deployment, database ACLs, operational
controls); `--operator` adds mandatory self-reported provenance on the row —
it is not authentication (§4.5). The web layer gets **read-only**
refresh-history presentation, gated by the *existing* display gate (ALLOWED
branch only; DENIED learns nothing, §8). The CIDR gate keeps its exact
frozen meaning (visibility of vendor prices) and is **not** repurposed as
mutation authorization.

**Phase 2 (deferred, 8C-gated): Option B** as a browser convenience once an
authenticated operator role exists; the command remains available. Phase 2
is out of scope for this design's first implementation and is listed only as
the future boundary.

### 4.5 Operator identity and authorization boundaries [PROPOSED — corrected per DESIGN2-FU1 C4]

- `--operator` is **self-reported provenance**, NOT authentication: a
  mandatory, verbatim-recorded attestation by the invoking actor, useful
  for audit correlation, but forgeable by anyone who already holds the
  authorization boundary (host access).
- `USERNAME` and other OS environment data are **not trusted identity
  proof**; at most they may be recorded as a labeled, untrusted OS-context
  field (D4) for correlation.
- Real mutation authorization comes from **controlled Windows account
  access**, executable/deployment access, database ACLs, and the
  operational controls of the pilot runbook — not from any field stored on
  the row.
- **Shared administrative accounts reduce actor attribution**; the
  mandatory `--operator` field mitigates this for command invocations but
  cannot make a shared account individually attributable.
- This design makes **no claim that trustworthy OS audit evidence exists**
  (e.g., Windows Security/Event logs capturing the invoking account and
  command line); such a claim requires production verification.
- **R1 deployment requires an explicit host permissions and operational
  audit review** (host/CMD account inventory, command-logging posture,
  database file + directory ACLs, runbook controls), completed and recorded
  before R1 deploys.
- **No Django authentication** (no user model, session, or login) is built
  in this task; 8C remains the formal production-hardening/authentication
  phase.

### 4.6 Trigger vs execution provenance (DESIGN2-FU2) [PROPOSED — binding
for R1 review]

- The `operator` field stores the self-reported identity of the actor who
  **TRIGGERED** the refresh (the INSERT of the PENDING row; §3.1). It is set
  once at trigger time and is never modified by claim, complete, or fail.
- Trigger and claim are distinct primitives (§3.3). R0 never claims or
  executes a PENDING child (R0 has no execution path at all), so in R0 the
  recorded operator is always the trigger initiator and no execution-
  provenance gap can arise. In R1, a PENDING child created by one invocation
  may, in principle, be claimed and executed by a later one (the production
  comparables precedent, §2.4, does exactly this in its web view).
- **R1 requirement:** an existing PENDING child must not be silently
  executed in a way that produces the inaccurate claim that its recorded
  (original trigger) operator executed the Vendor lookup. R1 must choose one
  of:
  1. **Constrain which invocation may execute it:** the R1 command claims
     and executes only the child its own trigger created in the same logical
     invocation; a pre-existing PENDING child is reported with a bounded
     message (identified by its `created_at` and recorded `operator`) and
     left untouched. Consequence: a PENDING child whose creating invocation
     died between INSERT and claim is not executed by any later invocation;
     it occupies the active slot and is reported on subsequent triggers.
     Its resolution is an R1 review item: it has made ZERO API calls, so
     unlike a stuck RUNNING row it carries no unknown external outcome; the
     §3.6 R1 recovery gate covers RUNNING rows only and is not extended to
     PENDING rows here without approval.
  2. **Record/obtain truthful execution provenance through an explicitly
     approved mechanism:** e.g., the R1 command's bounded stdout/audit
     record names the executing invocation and its self-reported operator
     (an operational, non-model mechanism), or a later design-gate approval
     adds a claim-executor field.
- **No new model field is introduced by this revision.** The R0 schema
  freeze is unchanged: `operator` + `trigger_source` + the lifecycle
  timestamps remain the complete R0 provenance surface. If R1 option 2
  requires a model field, it must be proposed with an explicit justification
  that the existing schema cannot satisfy the requirement, and approved at
  the R1 design gate before any schema change.
- Acceptance coverage: the R1 command suite (§10.3(5)) pins the chosen
  mechanism; no R0 test is affected (R0 never executes a PENDING child).

---

## 5. Concurrency and idempotency contract

### 5.1 Definition: one refresh attempt [PROPOSED]

**One refresh attempt is exactly one `VendorRefreshExecution` row**, created
by one trigger, moved PENDING→RUNNING by at most one claim, and terminated
by at most one complete-or-fail. Within one attempt:

- **at most one** `InternalVendorAdapter.lookup()` network call (only the
  claim winner reaches the call site; the adapter's own frozen policy bounds
  that call to a single GET with no retries);
- zero calls if the attempt crashes before the call, or if the vendor base
  URL is unconfigured (fail `VENDOR_LOOKUP_CONFIG_MISSING`);
- the attempt's outcome is durably recorded in the row (COMPLETED + payload,
  or FAILED + bounded reason — the only two terminal states, each reached
  by its single-winner CAS — or RUNNING-interrupted: occupying its active
  slot, with NO in-band reclaim, reset, retry, or recovery-based
  terminalization in R0, §3.3/§3.6).

An attempt is never "retried" into another attempt: a new attempt is a new
row, created only by a new explicit trigger (concept 2, §3.3). There is no
implicit retry path anywhere in R0 — not in the command, not in the claims
services, not in any recovery rule.

### 5.2 Safeguard matrix [PROPOSED]

| Threat | Mechanism | Durable evidence |
|---|---|---|
| Double-click / duplicate trigger (two invocations, same run) | `trigger` is idempotent on active children; `UNIQUE(parent_run, active_slot)` makes the second insert fail; loser returns the winner row; loser never claims, never calls | one row; the second invocation prints "already in progress / already created" |
| Concurrent refreshes, same run, different hosts/operators | same uniqueness invariant + CAS claim: at most one claim winner; the second claimer gets `VendorRefreshClaimError` and performs **no** network work | one RUNNING then one terminal row |
| Repeated requests after an HTTP timeout (phase-2 web surface) | R3 requirement (DESIGN2-FU1 C2): a retransmission of the SAME logical request must not create a new child. Active-child deduplication (concept 1) covers only PENDING/RUNNING; once the child is terminal, "find the latest terminal child and do nothing new" is INSUFFICIENT — it cannot distinguish a retransmission from an intentional post-terminal refresh (concept 2). R3 therefore requires an explicit, stable request idempotency identity (or an equivalently proven protocol). R0/R1 do not implement concept 3: every command invocation is an explicit operator action, and post-terminal invocations are concept 2 (new child), guarded in R1 by the repeat safeguard below | rows are the truth; R3 deduplication is identity-keyed, not latest-row lookup |
| Process crash mid-execution (DESIGN2-FU1 C1: 60-s wall-clock reclaim REJECTED) | RUNNING row persists, occupying its active slot; NO auto-recovery and NO in-band reclaim/reset/retry or recovery-based terminalization in R0 (the only RUNNING→terminal transitions are the claim winner's complete/fail CAS, §3.3 — a crashed process will not issue them); the next trigger reports in-progress and makes zero API calls; a stuck row blocks new refreshes for that parent until resolved. Resolution is the future **R1 operational recovery gate** (§3.6): manual interruption only on sufficient trusted external evidence that the prior process is terminated (a wall-clock threshold alone is insufficient), via an atomic conditional transition recording `EXECUTION_INTERRUPTED` with the external Vendor outcome preserved as explicitly unknown; only then may a NEW distinct attempt be triggered | the interrupted attempt stays visible; it is never read as success; its external Vendor outcome is never assumed to have failed |
| Excessive Vendor API traffic | bounded stack: (1) one active child per run; (2) one call per claim; (3) frozen adapter policy (one GET, 10 s, no retries/fanout); (4) no automatic re-trigger anywhere in the design; (5) post-terminal re-refresh requires a new explicit operator trigger (concept 2); (6) no command surface exists in R0; the R1 command output shows active state + last refresh instant; NO general rate limiter in R0 or R1 (DESIGN2-FU1 C5); (7) R1 minimal CMD safeguard: the safeguard is evaluated BEFORE a new refresh attempt is persisted (before the trigger INSERT) and BEFORE any new Vendor API request — the command displays the existing active state and the most recent terminal attempt; if a terminal attempt occurred within the preceding 5 minutes, an explicit `--force-repeat` is required, and a cooldown refusal leaves NO newly created PENDING child behind; any repeated attempt is a NEW child, never a rewrite; concurrent invocations are reviewed separately at R1 (the hard invariant is still UNIQUE(parent_run, active_slot) + CAS). This is an operator-safety check on the command surface, clearly distinct from a server-enforced comprehensive rate limit (which needs identity; out of scope — D6) | each call is attributable to exactly one row and one operator |
| Ambiguous retries (did the crashed attempt reach the API?) | the design never claims knowledge it lacks: a crashed RUNNING row is not terminalized by any R0 recovery path — its claim winner is dead and cannot issue the complete/fail CAS, and R0 provides no substitute (§3.3/§3.6) — so it is neither failed-lookup nor success; the external outcome stays explicitly unknown until (and unless) the R1 recovery gate resolves the row; the later attempt (after R1 resolution) is a new timestamped evidence point, and no overlapping outbound request is ever justified by reclaiming a database slot. The original snapshot and all prior rows remain unmodified | history is monotone; no state implies "unknown call = success" or "unknown call = failure" |

### 5.3 Vendor adapter policy preservation [PROPOSED]

`InternalVendorAdapter` is used **unmodified**: the bounded network-call
policy (one call, GET-only, 10 s timeout, 1 MiB cap, no redirect following,
no ambient proxy, no cookies/auth headers, allowlist mapping, sensitive
metadata stripping) carries over by construction. **No automatic retry
policy is invented** at any layer (adapter, execution, command, future web).
A failed lookup is a failed lookup; the next lookup is a new explicit
attempt (concept 2). In R0 there is no reclaim of RUNNING rows and no
implicit retry path of any kind: an interrupted attempt stays RUNNING,
occupying its slot, until the future R1 operational recovery gate (§3.6)
resolves it on trusted external evidence.

---

## 6. Vendor-only network boundary

### 6.1 The single allowed egress [PROPOSED]

A vendor refresh execution performs exactly one class of network activity:
`InternalVendorAdapter.lookup(CommercialLookupQuery(mpn=<bound MPN>))` against
the deployment-configured `PI_VENDOR_LOOKUP_BASE_URL` (§2.5 frozen policy).
Nothing else is reachable from the refresh code path:

| Forbidden in a refresh | Enforcement |
|---|---|
| Serper / any SearchProvider call | the refresh execution imports only the commercial adapter + frozen 2A comparator + frozen codec; no `SearchProvider` import exists in its module (guard test, AST scan) |
| Public product page fetch (PageFetcher/HttpPageFetcher) | same; no fetcher construction anywhere in the path |
| Semantic Primary/Fallback (LLM) | no semantic import; eligibility is pure deterministic 2A, as in 4D-B |
| Comparable-product discovery | no comparable module import; no child of `ComparableResearchExecution` is created or touched |
| ECB FX retrieval (any provider call, live or cache-write) | no `providers.fx` import, no `FxObservationStore` read or write; §7 |
| Micron alias authority fetch | no alias module import |
| Any other outbound I/O | execution module dependency scan in the guard tests (new, §10) |

The parent ResearchRun is **not re-executed** and its state is not touched:
no `claim_execution`, no `transition_to`, no `ExecutionEvidenceRecord`
writes — the original run's evidence section stays byte-identical, so the
historical report (including its audit trail) is reproducible exactly as
before.

### 6.2 Exact MPN binding [PROPOSED]

- The refreshed MPN is **the parent run's `manufacturer_part_number`
  verbatim** — captured immutably into `requested_mpn` at trigger time,
  re-verified at execution time (application-level check, §3.4 step 2). No
  operator-supplied MPN is accepted (the command takes only the run UUID +
  operator identity): a refresh can never look up a different part number
  under a run's identity.
- **Query-normalization fail-closed check (DESIGN2-FU1 C7):** the frozen
  `CommercialLookupQuery` strips surrounding whitespace (§1.2). The refresh
  execution verifies that the constructed query MPN **exactly equals** the
  immutable captured canonical MPN BEFORE any network call; any unexpected
  normalization fails the attempt closed (`MPN_QUERY_NORMALIZATION_MISMATCH`,
  zero Vendor calls) — the requested binding is never silently altered. The
  frozen 2A binding and codec behavior are preserved unchanged.
- Candidates returned by the vendor are re-bound with the frozen
  `compare_part_numbers` exactly as in 4D-B: EXACT / NORMALIZED_EXACT become
  identity-bound observations (with `brand_new` VENDOR_API_POLICY policy);
  anything else is recorded as a bounded `MPN_MISMATCH` issue — never a row.
- One-character differences, missing explicit vendor MPN, and malformed
  sections behave exactly as the frozen vocabulary dictates (the codec
  rejects anything outside it on encode/decode).

### 6.3 No authority promotion [PROPOSED]

Refreshed observations are supplemental display evidence, full stop. They
do not enter `PriceIntelligenceSnapshot`, Machine Price, Reviewed Price,
2A/semantic identity authority, comparable scoring, or any statistic of the
original run. This is the same frozen authority contract as 4D-B
(`providers/commercial.py` module contract; PLAN §26.3), asserted structurally
in new guard tests (§10) mirroring `tests/providers/test_vendor_authority.py`.

---

## 7. FX and price freshness policy

### 7.1 Immutability and zero FX activity [PROPOSED]

- `ResearchFxSnapshot` for the parent run is **never read or written** by the
  refresh execution, and `FxObservationStore` is never touched (no read, no
  write, no re-proof). The refresh makes **zero FX network calls** — no ECB
  retrieval, live or cached — without separate explicit approval (task
  constraint; the 8A freshness contract is untouched).
- The frozen FX codec, the FX math, and the replay FX semantics are
  unmodified. The original report's "ECB reference date / rates retrieved /
  FX acquisition" lines keep rendering from the original snapshot exactly as
  today.
- **No historical FX reuse (DESIGN2-FU1 C8):** the refresh never applies the
  original run's FX rates — or any other historical rates — to refreshed
  quotes. D2 option (b) (labeled display arithmetic over the frozen original
  snapshot) remains a SEPARATE future decision requiring explicit approval;
  it is NOT part of R0–R2.

### 7.2 Why the refreshed EUR quote gets no naive USD conversion

The original FX snapshot carries an `observation_date` from the original run.
Rendering a refreshed quote's "USD Equivalent" computed from that old rate
would present a **fresh price as if it had a newly acquired conversion** —
precisely the misleading appearance the task forbids. The preferred initial
behavior is therefore: **suppress USD-equivalent conversion for refreshed
rows; present native currency only**, with an explicit bounded note that no
FX was acquired for this refresh (open decision D2 offers the labeled-reuse
variant for a later approval).

### 7.3 Presentation rules for the refresh history (ALLOWED view) [PROPOSED]

All "latest" wording in §7.3/§8.3 uses the four-concept projection
vocabulary defined in §8.3 (DESIGN2-FU1 C3). A refresh row is historical
evidence **as of its `retrieved_at`**; no display may describe an older
refresh's quotation as necessarily current.

| Case | Display |
|---|---|
| Native-currency vendor price (e.g. `4740.18 EUR`) | Rendered in the published currency, exact Decimal formatting identical to the existing `_format_price` convention; column "Price". |
| USD native price | Rendered as-is (`$X USD`); no conversion involved. |
| USD Equivalent column for a refreshed non-USD row (phase 1) | **"Not converted — no FX acquired for this refresh"** (bounded literal). Never a number. |
| Historical FX reference date | The original report's FX line is unchanged and refers only to the original rows. Refresh rows carry no FX date; the panel header states "no FX evidence is associated with refreshes". |
| Out-of-stock / zero-price / UNKNOWN-availability observations (`OUT_OF_STOCK` incl. zero price where the source publishes one; `UNKNOWN` availability) | Rendered with the frozen inventory mapping ("Out of Stock" / "Unknown"); a zero published price keeps the existing "verify price" verification-note behavior of the frozen display layer — refresh reuses display mapping, never invents availability. These observations retain their original evidence semantics and are NEVER mislabeled as available-to-purchase positive-price quotations (DESIGN2-FU1 C3). |
| Partial success (`lookup_status=PARTIAL`) | Per-source lines: usable observations as rows; bounded issues with their frozen labels (not found / section unreadable / no explicit MPN / MPN mismatch). Status line "Partially completed". A PARTIAL lookup MAY contain valid quotation observations and is NOT excluded from usable commercial evidence solely because it is PARTIAL (concepts 3/4, §8.3). |
| Failure (`lookup_status=FAILED`) | "Lookup failed — no vendor quote obtained" + bounded per-source issues if any were persisted + "the specific cause was not recorded" when the payload carries none (mirroring the frozen status-notice contract — the codec persists no free-text cause). A COMPLETED child with `lookup_status=FAILED` is an executed Vendor lookup with a FAILED result — NOT a successful quotation (DESIGN2-FU1 C3). |
| Successful lookup, zero bound observations (`lookup_status=SUCCESS`, no observations) | "Completed — no usable vendor quote" + bounded issue lines. This is a SUCCESS *lookup* (concept 2, §8.3), NOT a quotation (concept 3); it is displayed as an executed lookup with no quote. |
| Original vs refreshed comparison | The panel shows, for the same bound MPN: the **original** lookup status with its original `retrieved_at` (decoded from the frozen original snapshot — read-only) beside each **refreshed** attempt's status and `retrieved_at`. Distinct visual treatment: original rows carry no suffix; refreshed rows carry a "Refreshed <timestamp>" label and a refresh-id link fragment. Stale (original) and fresh (refreshed) are never merged, averaged, or deduplicated. |
| No original supplement snapshot | Original line reads "Not recorded for this run" (frozen `not-recorded` semantics); refresh rows render normally. The refresh panel is the first vendor evidence for that run — and it is labeled as refresh evidence, never backdated into the original's place. |

### 7.4 No fabricated conversions, ever [PROPOSED]

A refreshed row's USD-equivalent value may appear only under an explicitly
approved variant (D2) with dual-date labeling (quote date + FX observation
date) computed from the **original frozen snapshot** — or never. The refresh
execution itself persists no FX field (the codec V1 payload has none), so a
misleading conversion is unrepresentable at the data level.

---

## 8. Historical replay and visibility

### 8.1 Original report replay: unchanged [PROPOSED invariant]

- `replay_compact_quote_projection` (ALLOWED) and
  `replay_public_compact_quote_projection` (DENIED) are **not modified**: the
  Quote & Market Summary, vendor rows, status notice, FX line, market
  statistics, and the full evidence/audit sections of the original report
  remain exactly the reproducible projection of the original persisted
  artifacts. A refresh never alters any of them.
- **Byte-identity scope (DESIGN2-FU1 C8):** the ORIGINAL persisted snapshots
  and the ORIGINAL replay projections are unchanged — the replay projections
  (and every original report section) are byte-identical with or without
  refresh rows. R2 adds a SEPARATE projection (the refresh history section);
  the complete report HTML for an ALLOWED connection WITH refresh rows is
  NOT promised byte-identical to the pre-R2 page — the difference is exactly
  the additive section. DENIED pages and no-history ALLOWED pages remain
  byte-identical to today.
- The original `ResearchSupplementSnapshot` OneToOne row is never updated,
  replaced, or deleted by refresh code (task constraint; enforced by
  behavior tests: original payload bytes + `created_at` identical before and
  after refreshes, §10).

### 8.2 Public-only replay firewall, extended [PROPOSED]

The DENIED branch's zero-knowledge contract is extended to the new model:

- `compact_quote_public_replay.py` continues to never read
  `ResearchSupplementSnapshot` **and** never reads
  `VendorRefreshExecution` rows (no import, no query — enforced by the
  existing armed-fail-fast test pattern in
  `tests/web/test_vendor_status_ux_a.py` / `tests/execution/
  test_compact_quote_public_replay.py`, mirrored for the new model).
- The refresh-history presentation is built **only** in the view's ALLOWED
  branch, after `vendor_price_access_allowed` returns True; the DENIED
  template context contains no refresh fact of any kind — not existence,
  not count, not status, not operator, not price, **not error** (DESIGN2-FU1
  C8; D8 recommendation: total zero-knowledge, same standard as the original
  snapshot).
- The public replay import/query firewall and its armed fail-fast test
  requirement are preserved unchanged (DESIGN2-FU1 C8): the DENIED path must
  not query `VendorRefreshExecution` at all, and the guard tests must fail
  fast if any such import or query appears.
- No second read/decode of vendor artifacts happens: the refresh-history
  read-side module is the sole decoder of refresh payloads (same "replay
  boundary is the sole decoder" convention as PILOT-VENDOR-STATUS-UX-A).

### 8.3 Refresh history view / projection [PROPOSED]

- New read-side: `execution/vendor_refresh_history.py`
  `replay_vendor_refresh_history(run_id) -> VendorRefreshHistoryReplayResult`
  (zero live work: loads the run's refresh rows ordered newest-first, decodes
  COMPLETED payloads via the frozen codec, returns bounded presentation
  inputs; malformed persisted payload → the affected row is rendered
  fail-closed as "recorded but unreadable", the rest of the report is
  unaffected — display-only degradation, never a numeric fabrication).
- New pure display module: `web/vendor_refresh_presentation.py` (DB-free,
  decode-free, provider-free — same discipline as
  `web/vendor_status_presentation.py`).
- Template: a new section **"Vendor refresh history"** on the report page,
  rendered only for ALLOWED connections with at least one refresh record
  (confirmed D7 rule, §12.1; the "always show 'none yet'" alternative is
  NOT approved). The DENIED page and the no-history ALLOWED page stay
  byte-identical to today; the with-history ALLOWED page gains exactly the
  additive section — §8.1.
- Row display: state, operator, trigger source, created/started/finished
  timestamps, bound MPN (displayed to prove the binding), lookup status,
  per-source observation lines (price/currency/availability/brand-new/
  note), bounded issue lines, and the §7.3 FX treatment.
- **Projection vocabulary — four distinct concepts (DESIGN2-FU1 C3; binding
  for all display wording and tests):**
  1. **Latest execution** — the most recently created
     `VendorRefreshExecution` row, in ANY state (PENDING/RUNNING/COMPLETED/
     FAILED).
  2. **Latest SUCCESS lookup** — the most recent COMPLETED child whose
     decoded `lookup_status` is SUCCESS, **even when it has zero bound
     observations**. A SUCCESS lookup is a Vendor lookup that executed
     normally; it is not by itself a quotation.
  3. **Latest usable quotation evidence** — the most recent COMPLETED child
     with `lookup_status` SUCCESS **or PARTIAL** and at least one correctly
     identity-bound usable quotation observation. A PARTIAL lookup MAY
     contain valid quotation observations and is NOT excluded from usable
     commercial evidence solely because it is PARTIAL.
  4. **Latest IN_STOCK quotation** — the most recent eligible child (per
     concept 3) containing an IN_STOCK observation with a positive price.
  - Boundary rules: a COMPLETED child with `lookup_status=FAILED` is an
    executed Vendor lookup with a FAILED result — NOT a successful
    quotation; it contributes nothing to concepts 2–4. OUT_OF_STOCK,
    UNKNOWN availability, and zero-price observations retain their original
    evidence semantics and are never mislabeled as available-to-purchase
    positive-price quotations. A historical quotation is evidence as of its
    `retrieved_at`; it is NOT necessarily current, and no display may
    describe an older refresh's quote as current without its timestamp.
  - Deterministic ordering: history rows and all "latest" projections are
    ordered by `created_at` DESC with a **tie-breaker on `id` DESC for
    identical timestamps** (a stable total order; projections never depend
    on database iteration order or on `now()`).
  - A later FAILED or interrupted attempt never removes the visibility of an
    earlier successful one (append-only history; every derived projection is
    a pure projection over all rows, so erasure is unrepresentable).
- **Confirmed D1 rule (DESIGN2-FU2; §12.1):** the original Quote & Market
  Summary, the original vendor rows, and the existing PILOT-VENDOR-STATUS-UX-
  A status notice remain UNCHANGED. R2 adds an independent Vendor Refresh
  History section only; the refresh panel is the distinguished, labeled,
  timestamped historical vendor-evidence surface (the original report
  sections stay reproducible; the full page gains only the additive refresh
  section, §8.1). The previously proposed optional pointer-line modification
  to the original status notice ("a later operator-initiated vendor refresh
  recorded results — see Vendor refresh history") is **NOT approved for R2**
  and is removed from the approved R0–R2 implementation scope.

### 8.4 Safe behavior without an original vendor snapshot [PROPOSED]

Covered by trigger eligibility (§3.3: absence is not an error) and display
(§7.3 "Not recorded for this run"). No special execution path: the refresh
is a normal single-call lookup for the bound MPN.

### 8.5 No new price authority [PROPOSED]

Nothing in the refresh history is consumed by any aggregation, matching,
review, comparable, or replay authority path. No refresh result may
influence Machine Price, Reviewed Price, semantic authority, comparables,
or the original quote statistics (DESIGN2-FU1 C8). The only consumers are
the two display modules above. Guard tests assert that no execution/research
authority module imports the refresh read-side result type (structural
separation, mirroring `test_vendor_authority.py`).

---

## 9. Failure and crash-recovery matrix

Legend: `child` = the `VendorRefreshExecution` row; `API` = Vendor API
network calls made by that attempt.

| # | Failure / event | Where | Child state after | API | Parent run / original snapshots | Recovery |
|---|---|---|---|---|---|---|
| 1 | Parent not found / not COMPLETED / no price snapshot / empty MPN | trigger | no row | 0 | untouched | bounded trigger error; operator sees reason |
| 2 | `PI_VENDOR_LOOKUP_BASE_URL` absent | execution step 3 | FAILED `VENDOR_LOOKUP_CONFIG_MISSING` | 0 | untouched | reconfigure env; new explicit attempt |
| 3 | Concurrent trigger race | trigger insert | one row (winner); loser returns winner | ≤1 total | untouched | loser no-ops |
| 4 | Concurrent claim race | claim CAS | one RUNNING (winner); loser error | ≤1 total | untouched | loser no-ops |
| 5 | Vendor transport failure (timeout/connection/HTTP/oversize/non-UTF8/unrecognized contract) | adapter | **COMPLETED**, payload `lookup_status=FAILED` (obs/issues per bounded response) | 1 | untouched | history shows the failed lookup; new explicit attempt allowed |
| 6 | Vendor PARTIAL / SUCCESS with zero usable observations | adapter+binding | COMPLETED with the bounded shape; MPN mismatches recorded as issues | 1 | untouched | display-only; no reinterpretation |
| 7 | Codec/contract defect (programming error) | encode/bind | FAILED `RESULT_ENCODING_FAILED` / `MPN_BINDING_VIOLATION` | ≤1 | untouched | fix defect; new explicit attempt |
| 8 | DB failure during complete/fail UPDATE | CAS step | stays RUNNING (the update did not commit), occupying the active slot | 1 | untouched | DB restored; R0 provides NO in-band reclaim/reset or recovery-based terminalization for the stuck row (§3.3) — the complete/fail CAS belongs to the (stopped) claim winner and is not re-issued by any R0 mechanism; resolution only via the future R1 operational recovery gate (§3.6): trusted external evidence of process termination, atomic conditional transition, external outcome preserved as explicitly unknown; no new attempt until then |
| 9 | Process crash between claim and API call | — | RUNNING, 0 calls made, occupying the active slot | 0 | untouched | as #8 |
| 10 | Process crash mid API call / after response, before complete | — | RUNNING, occupying the active slot | 1 (unverifiable) | untouched | as #8; the row is **not** terminalized by any R0 recovery path — its claim winner crashed and cannot issue the complete/fail CAS, and R0 provides no substitute (§3.3/§3.6) — so it is neither failed-lookup nor success; the external Vendor outcome stays explicitly unknown; the later attempt (after R1 recovery-gate resolution) is a new timestamped evidence point |
| 11 | Crash after complete committed | — | COMPLETED durable | 1 | untouched | none needed; history is the record |
| 12 | Re-trigger while active child exists | trigger | existing child returned | 0 new | untouched | operator told "in progress (since T)" |
| 13 | Re-trigger after terminal child | trigger | NEW PENDING child (distinct attempt; concept 2, §3.3 — an intentional post-terminal refresh, guarded in R1 by the repeat safeguard, §5.2) | ≤1 for the new attempt | untouched | append-only history grows; the four-concept projections (§8.3) are recomputed over all rows; a later FAILED lookup never erases an earlier usable quotation |
| 14 | Parent run deleted | FK cascade | rows deleted with the run (same as 7C-A; durable customer DB is the operator's domain) | — | — | n/a |
| 15 | Refresh row payload corrupted post-commit (impossible via code; tamper scenario) | display decode | row stays COMPLETED | 0 | untouched | display renders that row fail-closed as "recorded but unreadable"; original report unaffected; no numeric fabrication |

Invariant across all rows: **the parent ResearchRun row, its
`PriceIntelligenceSnapshot`, its `ResearchSupplementSnapshot`, its
`ResearchFxSnapshot`, its `ResearchMicronAliasSnapshot` (if any), its
`ExecutionEvidenceRecord`s, its `AiAssistedReviewCandidate`s, and all its
`ComparableResearchExecution` records are byte-identical before and after
any refresh** (DESIGN2-FU1 C9). A failed or interrupted refresh never
erases, amends, or reinterprets a prior successful refresh or the original
result.

---

## 10. Required migrations and regression tests

### 10.1 Migration [PROPOSED]

- New migration on the production branch:
  `product_intelligence/runs/migrations/0012_vendor_refresh_execution.py`
  (production's latest is 0011; note dev-main independently owns a 0012 for
  `SemanticDecisionRecord` — the branches must not be merged without a
  renumbering decision; the implementation base is the production branch,
  D9).
- Contents: `CreateModel VendorRefreshExecution` + the five constraint
  groups of §3.1 (CHECKs + UNIQUE + index). No data migration; no change to
  any existing table. Post-implementation gates:
  `python manage.py makemigrations --check --dry-run` → "No changes
  detected"; `python manage.py check` → clean.

### 10.2 Test-preservation invariant (binding)

Never delete, rename, skip, xfail, deselect, ignore, or weaken an existing
test; never change expected results to match implementation. Before the first
implementation commit: re-record the production-baseline node-level
collection (5959 nodes / 148 files, §1.4 — agent-reported historical
baseline, subject to independent verification) and the full-suite result,
and diff node-by-node after (additions only). The existing semantic-runtime,
execution-integration, vendor-authority, and security suites are preserved
as-is:

- `tests/providers/test_internal_vendor.py` (165),
  `tests/providers/test_vendor_section_response.py` (127),
  `tests/providers/test_commercial_provider.py` (46),
  `tests/providers/test_vendor_authority.py` (14)
- `tests/execution/test_4d_b_vendor_commercial.py` (19),
  `tests/execution/test_4d_b_vendor_section_integration.py` (19)
- `tests/research/test_commercial_supplement_codec.py` (46)
- `tests/research/test_historical_replay.py` (7),
  `tests/research/test_historical_replay_blocker1_fu3.py` (5)
- `tests/execution/test_compact_quote_public_replay.py` (21),
  `tests/execution/test_public_replay_persisted_authority.py` (15),
  `tests/execution/test_human_confirmed_replay_authority.py` (24)
- FX: `tests/execution/test_fx_*` (9+24+11+10+43+2),
  `tests/research/test_fx_*` (43+30+29), `tests/providers/test_fx_*`
  (54+9+24), `tests/runs/test_fx_observation_store.py` (16),
  `tests/web/test_fx_evidence_presentation.py` (7)
- Security: `tests/web/test_commercial_access.py` (104),
  `tests/web/test_vendor_status_ux_a.py` (25),
  `tests/web/test_web_boundaries.py` (165)
- Claims/concurrency precedents: `tests/runs/test_execution_claims.py` (16),
  `tests/runs/test_comparable_execution_claims.py` (33)

### 10.3 New required test suites [PROPOSED]

1. **`tests/runs/test_vendor_refresh_claims.py`** (R0) — model shape
   constraints (all four lifecycle shapes accepted; every invalid shape
   rejected, incl. COMPLETED-without-payload, RUNNING-with-result,
   terminal-with-active_slot); trigger eligibility (each bounded reason);
   idempotency (active child returned, no second row — concept 1; a new
   explicit trigger after terminal creates a NEW child — concept 2; §3.3);
   MPN binding copied verbatim; race: `IntegrityError` path returns the
   winner; unrelated `IntegrityError` propagates; CAS claim/complete/fail
   single-winner semantics; parent-delete cascade.
   **Final R0 state-transition regression contract (DESIGN2-FU2; pins the
   §3.3 state-transition table):** (i) a legitimate claim→complete succeeds
   and atomically publishes the payload; (ii) a legitimate claim→fail
   succeeds with a bounded reason; (iii) each terminal transition (complete,
   fail) is single-winner CAS — two concurrent terminalizations of the same
   child: exactly one succeeds; (iv) an attempted duplicate or losing-race
   terminalization (complete-after-complete, fail-after-complete,
   complete-after-fail) fails with a bounded error and NO mutation (state,
   timestamps, active_slot, result fields, and failure_reason all
   unchanged); (v) the claims service surface is EXACTLY the four
   primitives — no reclaim, no RUNNING→PENDING reset, no threshold-triggered
   forced failure, no automatic retry, no operator-forced interrupt/recovery,
   no reassignment of an existing RUNNING attempt (import/AST-pinned,
   mirroring §10.3(4)); (vi) a stuck RUNNING row (claim committed, no
   complete/fail issued) **cannot be forcibly terminated through any R0
   recovery path** — no such path exists to invoke, and trigger/claim over
   it have no terminalization effect; (vii) a subsequent trigger over a
   RUNNING child returns the existing child without creating another row.
   **No test in this suite (or anywhere else) may assert that
   RUNNING→COMPLETED or RUNNING→FAILED is prohibited; the asserted contract
   is the opposite — complete/fail are the ONLY legal RUNNING→terminal
   transitions and must succeed when their CAS preconditions hold.** **Database structural constraints
   versus application immutability guarantees (DESIGN2-FU1 C6):** the
   CHECK/UNIQUE shapes are enforced by the database for direct inserts
   (invalid shape → rejected), while a direct ORM `.update()` / raw SQL CAN
   move a row outside the CAS path — the test documents that the lifecycle
   guarantee is application-level (the four CAS primitives are the only
   application write path) and makes NO claim that `editable=False` itself
   rejects arbitrary writes. The earlier draft's test claim that
   "`editable=False` fields reject writes" is REMOVED from this
   specification (design correction only; no existing repository test is
   altered).
2. **`tests/execution/test_vendor_refresh_execution.py`** — zero-network
   (injected fake adapter counting calls): exactly ONE `lookup` call per
   claimed attempt, zero for losers/config-missing; MPN query equals the
   bound MPN exactly (byte-level); **`CommercialLookupQuery`
   normalization/binding mismatch** — a captured MPN with surrounding
   whitespace (the frozen query type strips it, §1.2) → child FAILED
   `MPN_QUERY_NORMALIZATION_MISMATCH` with ZERO network calls (fail closed;
   the requested binding is never silently altered); 2A binding (EXACT /
   NORMALIZED_EXACT / one-char mismatch / missing explicit MPN) produces the
   frozen observation/issue shapes; vendor FAILED → child COMPLETED with
   `lookup_status=FAILED` payload (an executed lookup with a failed result —
   NOT a successful quotation); **SUCCESS lookup with zero bound
   observations** (concept 2, not concept 3); **PARTIAL lookup with valid
   bound observations** (counts for concepts 3/4 — PARTIAL is not excluded
   from usable commercial evidence); **FAILED lookup after an earlier
   successful quotation** (the earlier quotation remains the latest usable);
   **zero-price and OUT_OF_STOCK observations** retain their original
   evidence semantics (never a positive-price purchaseable quote); codec
   encoding through the frozen encoder (payload decodes with
   `decode_research_supplement_result`); **stored `result_schema_version`
   agrees with the payload's codec schema version** (a mismatch is rejected
   at complete; a corrupted/mismatched stored payload fails closed at read);
   programming-error → child FAILED bounded reason; parent run + **ALL
   original artifacts** byte-identical before/after —
   `PriceIntelligenceSnapshot`, `ResearchSupplementSnapshot`,
   `ResearchFxSnapshot`, `ExecutionEvidenceRecord`,
   `AiAssistedReviewCandidate`, `ResearchMicronAliasSnapshot`, and
   `ComparableResearchExecution` records (append-only, no mutation — the
   central regression); no `ExecutionEvidenceRecord` writes; no run state
   transition.
3. **`tests/execution/test_vendor_refresh_network_boundary.py`** — AST scan
   of the new execution modules: imports are confined to
   {runs public claims, `providers.commercial` (query/response contracts),
   `providers.internal_vendor` (adapter class only), `research.identity`
   (2A), `research.commercial_supplement_codec` (codec), stdlib}; no
   `SearchProvider`, `PageFetcher`, `serper`, `http_page`, `semantic`,
   `comparable`, `providers.fx`, `fx_observation_cache`, `FxObservationStore`
   imports; sentinel "no-execution" probes: with an armed adapter double that
   raises if the network boundary is exceeded, the full refresh path makes
   exactly the one allowed call (mirrors the existing sentinel-probe
   convention in the semantic suites).
4. **Concurrency/failure/idempotency + recovery-based-terminalization
   absence** (R0 nodes within suites 1–2; command-surface nodes in the R1
   suite 5; DESIGN2-FU1 C1/C3/C9, DESIGN2-FU2): double-trigger → one row,
   one call; double-claim → one winner; in-progress report; crash simulation
   (claim committed, then the claim winner stops issuing CAS — no complete/
   fail; the R1 execution suite additionally kills before the API call /
   before complete) → RUNNING, 0/1 calls, no success implied, **row stays
   RUNNING occupying the active slot**; **recovery-based terminalization is
   absent from R0 and no implicit retry path exists** — the claims service
   surface exposes exactly four primitives (no reclaim API, no RUNNING→
   PENDING reset API, no threshold-triggered forced-failure API, no
   operator-forced interrupt/recovery API, no RUNNING reassignment API, no
   `--reclaim-stale` flag); a subsequent trigger over the RUNNING child
   returns the same row and makes ZERO additional API calls; **no R0
   recovery path moves RUNNING→terminal — the only RUNNING→terminal
   transitions are the complete and fail CAS primitives issued by the claim
   winner (§3.3 table), and no test asserts that RUNNING→COMPLETED or
   RUNNING→FAILED is prohibited (§10.3(1))**; repeated trigger after terminal
   → new distinct rows, history monotone; **most recent attempt versus most recent usable
   quote** (a later RUNNING/FAILED latest execution does not change the
   latest SUCCESS lookup / latest usable quotation / latest IN_STOCK
   quotation projections); **deterministic history ordering with identical
   timestamps** (tie-breaker `id` DESC; stable total order). The earlier
   draft's tests expecting the rejected 60-second reclaim mechanism are
   REMOVED from this specification (design correction only; no existing
   repository test is altered).
5. **`tests/runs/test_vendor_refresh_command.py`** (management command —
   **R1 suite**; the command belongs to R1, not R0 — DESIGN2-FU2) —
   run-uuid parsing (404-bounded), operator mandatory (missing → refused,
   nothing recorded; the recorded value is the self-reported TRIGGER
   initiator's provenance, not authentication and not an execution-
   provenance attestation — §4.5/§4.6), recorded provenance exact
   (`trigger_source=MANAGEMENT_COMMAND`, operator verbatim), bounded stdout
   (no secrets, no raw exception text), exit codes (0 bounded outcomes /
   non-zero ineligibility & unexpected), **no reclaim/`--reclaim-stale`
   flag in the R1 command surface** (absent from parser and help;
   re-invocation over a RUNNING child reports in-progress and leaves it
   untouched), no network when trigger is ineligible. **R1 repeat safeguard
   (DESIGN2-FU1 C5; ordering corrected per DESIGN2-FU2):** the safeguard is
   evaluated BEFORE a new refresh attempt is persisted (before the trigger
   INSERT) and BEFORE any Vendor API request — the command displays the
   existing active state and the most recent terminal attempt; a terminal
   attempt within the preceding 5 minutes → refused without explicit
   `--force-repeat`, and a refused invocation persists NO PENDING child
   (row count unchanged); with `--force-repeat` → a NEW child is created
   (never a rewrite of a prior child); the adapter double counts zero calls
   when refused. **Trigger-vs-execution operator provenance (DESIGN2-FU2;
   §4.6):** the suite pins the R1-approved mechanism — an existing PENDING
   child is never executed in a way that silently claims its recorded
   (original trigger) operator performed the Vendor lookup.
6. **`tests/web/test_vendor_refresh_presentation.py`** — ALLOWED display:
   every §7.3 case (native EUR/USD rows; "Not converted — no FX acquired for
   this refresh" literal for non-USD — no historical FX reuse, §7.1;
   out-of-stock + zero-price + UNKNOWN availability retaining their original
   semantics; PARTIAL with valid bound observations shown as usable evidence;
   failed with and without bounded issues; SUCCESS with zero bound
   observations shown as an executed lookup, not a quotation;
   original-not-recorded; original-vs-refreshed dual listing with distinct
   labels and timestamps; **most recent attempt vs most recent usable
   quote** — a latest RUNNING/FAILED execution never displayed as the
   current quote; **identical-timestamp ordering deterministic**); DENIED
   zero-knowledge: no refresh fact in context/HTML — no existence, count,
   status, operator, price, **or error** (armed fail-fast on any
   `VendorRefreshExecution` query from the DENIED path); original report
   sections byte-identical with/without refresh rows; the full ALLOWED page
   with rows differs by exactly the additive section (§8.1); no price
   authority leakage (refresh prices appear nowhere in the Machine Price /
   Reviewed Price / market statistics / original quote statistics regions).
7. **Replay firewall** — `tests/execution/` new nodes: the public replay
   module never imports or queries the refresh model (AST + armed fail-fast,
   mirroring the existing supplement-firewall tests); the authorized replay
   **projection** (and every original report section) is byte-identical with
   refresh rows present vs absent (original report reproducibility); no
   whole-page byte identity is asserted for the ALLOWED page when the
   additive refresh section renders (§8.1, DESIGN2-FU1 C8).
8. **FX isolation** — a run whose refresh returns a fresh EUR price: no
   `ResearchFxSnapshot` write, no `FxObservationStore` read/write (instrument
   both), no `EcbFxProvider` construction (sentinel), original FX line
   unchanged; the refreshed row carries no USD number.
9. **No promotion** (structural, mirroring `test_vendor_authority.py`) —
   refresh observations are not importable by aggregation/matching/semantic/
   comparable authority modules; a refreshed run's decoded
   `PriceIntelligenceSnapshot` and review candidates are identical.
10. **`tests/web/test_web_boundaries.py`** — the ONE authorized change:
    extend `ALLOWED_EXECUTION_IMPORTS` with the new public execution symbols
    the view uses (refresh-history replay entry point + its bounded error
    type) and nothing else; the existing 165-node guard suite is preserved
    verbatim and the extension is adversarially pinned (a new node asserting
    the exact post-change allowlist, so a future drift fails closed).
    [PROPOSED — explicitly a gated, recorded allowlist extension, not a
    weakening: every pre-existing expectation remains.]

### 10.4 Validation gates per phase [PROPOSED]

`python -m pytest` (full suite, one run, reported exactly per project
convention), `python manage.py check`,
`python manage.py makemigrations --check --dry-run`,
`git diff --check`; node-level collection diff vs 5959 baseline (additions
only).

---

## 11. Proposed bounded implementation phases

Each phase ends in ChatGPT independent review of the actual diff + test
evidence before the next begins. No phase may expand into the next.

**Phase R0 — persistence + lifecycle claims (no network, no surfaces; NO
recovery-based terminalization).**
R0 has EXACTLY: persistence (migration 0012), the `VendorRefreshExecution`
model, the lifecycle claims, bounded errors and public exports, and offline
tests. No management command, no provider call, no HTTP endpoint, no
template, and no deployment in R0 (the `vendor_refresh` command and the
default-provider runtime are R1 — §3.5/§4.2/§11).
- Migration 0012 (production branch); `VendorRefreshExecution` model +
  state/reason/source vocabularies; `runs/vendor_refresh_claims.py`
  (trigger/claim/complete/fail — EXACTLY four primitives per the §3.3
  state-transition table: INSERT PENDING; PENDING→RUNNING; RUNNING→
  COMPLETED with atomic result publication; RUNNING→FAILED with a bounded
  failure reason. The latter two are the ONLY legal RUNNING→terminal
  transitions and are REQUIRED. Prohibited in R0: stale reclaim, threshold-
  triggered forced failure, RUNNING→PENDING reset, automatic retry,
  operator-forced interruption/recovery, reassignment of an existing RUNNING
  attempt — §3.3/§3.6); `runs` public exports.
- Tests: §10.3(1) + the R0 portion of the §10.3(4) absence nodes (four-
  primitive service surface; legitimate claim→complete and claim→fail
  succeed; each terminal transition is single-winner CAS; an attempted
  duplicate terminalization fails without mutation; no reclaim or
  interrupt-recovery primitive exists in R0; a stuck RUNNING row cannot be
  forcibly terminated through any R0 recovery path; a subsequent trigger
  over a RUNNING child returns the existing child without creating another).
- Done when: full suite green; `makemigrations --check` clean; claims
  concurrency tests prove the uniqueness invariant; no code path yet can
  make a network call; no command, endpoint, template, or deployment
  exists yet.

**Phase R1 — vendor-only execution + operator command.**
- `execution/vendor_refresh.py` (incl. the §3.4 step-4 query-normalization
  fail-closed check) + `execution/vendor_refresh_runtime.py`; shared 4D-B
  binding/encoding helper extraction (behavior-identical, pinned by the
  existing 4D-B suites); `runs/management/commands/vendor_refresh.py`.
- **Minimal CMD repeat safeguard (DESIGN2-FU1 C5; ordering corrected per
  DESIGN2-FU2):** the safeguard is evaluated BEFORE a new refresh attempt
  is persisted (before the trigger INSERT) and BEFORE any new Vendor API
  request — the command displays the existing active state and the most
  recent terminal attempt; if a terminal attempt occurred within the
  preceding 5 minutes, an explicit `--force-repeat` is required, and a
  cooldown refusal leaves NO newly created PENDING child behind; any
  repeated attempt is a NEW child, never a rewrite. This is an operator-
  safety check, clearly distinct from a server-enforced comprehensive rate
  limit. Concurrent invocations (both passing the display check before
  either persists) are reviewed separately at R1; the hard invariant
  remains UNIQUE(parent_run, active_slot) + CAS. Detailed implementation
  and race handling remain subject to R1 review.
- **Trigger-vs-execution operator provenance (DESIGN2-FU2; §4.6):** the
  recorded `operator` is the self-reported TRIGGER initiator, not
  necessarily the actor whose invocation eventually claims and executes a
  PENDING child. The R1 implementation must ensure an existing PENDING child
  is never silently executed in a way that claims its original operator
  performed the Vendor lookup — either execution is constrained to the
  creating invocation (a pre-existing PENDING child is reported, not
  executed) or truthful execution provenance is recorded/obtained through an
  explicitly approved mechanism. No new model field is added without an
  approved justification that the existing schema cannot satisfy the
  requirement. The choice is made at R1 review; §10.3(5) pins it.
- **Operational recovery gate for stuck RUNNING rows (§3.6, specified at
  R1):** manual interruption only on sufficient trusted external evidence
  that the prior execution process is terminated (a wall-clock threshold
  alone is insufficient); atomic conditional transition; external Vendor
  outcome preserved as explicitly unknown; no overlapping outbound request
  justified by slot reclaim.
- **Deployment prerequisite (DESIGN2-FU1 C4):** an explicit host
  permissions and operational audit review (host/CMD accounts, command
  logging, database ACLs, runbook controls) completed and recorded before
  R1 deploys; no Django authentication is built.
- Tests: §10.3(2)(3)(4)(5) (incl. the safeguard-ordering and
  trigger-vs-execution provenance nodes) + the no-mutation
  regression (parent + ALL original artifacts byte-identical, §9
  invariant).
- Done when: a production-equivalent command invocation produces exactly
  one Vendor API call, one durable append-only row, zero changes to the
  original run's persisted artifacts; network-boundary AST + sentinel tests
  green; the safeguard and recovery gate behave per §5.2/§3.6.

**Phase R2 — read-only refresh history display (ALLOWED only).**
- `execution/vendor_refresh_history.py` (replay entry point; deterministic
  ordering per §8.3), `web/vendor_refresh_presentation.py`, view extension
  in the ALLOWED branch, template section (additive; §8.1 byte-identity
  scope), web-boundaries allowlist extension + adversarial pin.
- Tests: §10.3(6)(7)(8)(9)(10).
- Done when: DENIED connections learn nothing (armed fail-fast — no
  existence/count/status/operator/price/error), the original replay
  projection and every original report section are byte-identical
  with/without refresh rows (the full ALLOWED page may differ only by the
  additive section), FX suppression literals hold (no historical FX reuse),
  and the four-concept projections (§8.3) are proven erasure-proof,
  deterministic (incl. identical-timestamp tie-breaks), and PARTIAL-inclusive
  over mixed histories.

**Phase R3 (deferred; NOT part of the first implementation) — Web POST
trigger.**
- Gated on 8C authenticated operator identity + a bounded cooldown policy
  (D6) + a separate security review of the mutation surface.
- **Idempotency requirement (DESIGN2-FU1 C2, concept 3):** R3 MUST use an
  explicit, stable request idempotency identity (or an equivalently proven
  protocol) so that a retransmission of the SAME logical request creates no
  new child; looking up the latest terminal child is NOT sufficient. The
  mechanism is not added to R0.
- The command remains the canonical operator surface regardless.

---

## 12. Decisions

### 12.1 Confirmed decisions (DESIGN2-FU2)

| # | Decision | Confirmed rule |
|---|---|---|
| D1 | Display status of refreshed quotations in the original report. (Vocabulary reminder: a SUCCESS lookup with zero observations — concept 2 — is NOT a quotation; a FAILED lookup is an executed lookup with a failed result, NOT a successful quotation.) | **CONFIRMED** — the original Quote & Market Summary, the original vendor rows, and the existing PILOT-VENDOR-STATUS-UX-A status notice remain UNCHANGED. R2 adds an independent Vendor Refresh History section (the distinguished, labeled, timestamped historical-evidence surface). The main table and status notice remain projections of the original snapshot (the original report sections stay reproducible; the full page gains only the additive section, §8.1); a historical refresh quotation is evidence as of its `retrieved_at`, NOT necessarily current. The previously proposed optional pointer-line modification to the original status notice is **NOT approved for R2** and is removed from the approved R0–R2 implementation scope. The earlier draft option (b) — the latest usable quotation replaces the vendor rows in the main table — is NOT approved. |
| D7 | Refresh history display location. | **CONFIRMED (option (a))** — an additive section on the same report page (ALLOWED branch). The approved R2 rule: **only ALLOWED connections with at least one refresh record render the separate history section.** The DENIED page and the no-history ALLOWED page remain byte-identical to today; the with-history ALLOWED page gains exactly the additive section (§8.1 — no whole-page byte identity promised there). One durable report URL; no new route enumeration surface. This is a confirmed decision, NOT an open one. |

### 12.2 Open decisions requiring ChatGPT approval

| # | Decision | Options | Design recommendation |
|---|---|---|---|
| D2 | USD-equivalent for refreshed non-USD quotes. | (a) Phase 1: suppress (native currency only; bounded "Not converted — no FX acquired for this refresh" literal). (b) Compute from the original frozen `ResearchFxSnapshot` with mandatory dual-date labeling (quote date + FX observation date) — i.e., historical FX reuse for display. | **(a)** — zero FX activity, NO historical FX reuse, no misleading freshness; (b) is display-arithmetic over frozen evidence and remains a SEPARATE future decision requiring explicit approval — NOT part of R0–R2 (§7.1). |
| D3 | Stuck-RUNNING handling: recovery-based terminalization surface and recovery gate (DESIGN2-FU1 C1, clarified per DESIGN2-FU2). | (a) [REJECTED] `--reclaim-stale` flag, threshold 60 s — a 10-second urllib socket timeout is a per-operation socket timeout, NOT an absolute wall-clock deadline; a RUNNING process may still be alive after the threshold, so wall-clock-age reclaim could justify an overlapping outbound Vendor request. (b) No recovery-based terminalization in R0: complete/fail remain the ONLY legal RUNNING→terminal transitions (the claim winner's single-winner CAS, §3.3 table); a RUNNING child continues to occupy its active slot (RUNNING never reset to PENDING; one execution identity per attempt); no stale reclaim, no threshold-triggered forced failure, no automatic retry, no operator-forced interruption, no reassignment; resolution of a stuck RUNNING row only via the future R1 operational recovery gate (§3.6): manual interruption solely on sufficient trusted external evidence that the prior process is terminated (wall-clock alone insufficient), atomic conditional transition, external Vendor outcome preserved as explicitly unknown, no overlapping request justified by slot reclaim. (c) A different wall-clock threshold. | **(b)** — (a) and (c) are rejected for the same reason. No distributed lease, scheduler, or process supervisor is invented. The normal complete/fail CAS is unaffected by this decision (it is the required terminalization of a live attempt). A stuck row blocking new refreshes is the safe direction: it can never cause a double Vendor call. |
| D4 | Operator provenance convention (DESIGN2-FU1 C4). `operator` records the self-reported TRIGGER initiator, not necessarily the executor of a PENDING child (§4.6 — that requirement is handled by the R1 constraint/mechanism choice, NOT by this field). | (a) Mandatory `--operator <identity>` (self-reported provenance, NOT authentication); also record the OS `USERNAME` environment value in a second column explicitly labeled untrusted OS context (correlation aid only — `USERNAME` is NOT trusted identity proof; this option adds one bounded column, acceptable only if approved, since the existing schema has no OS-context field, and it never serves as an execution-provenance record). (b) `--operator` only. (c) OS account only, no recorded provenance field. | **(b)** — the minimum; (a) is acceptable only with the untrusted-context labeling and never as an identity claim; (c) is rejected (no actor provenance on the row). Real mutation authorization is the controlled Windows host access itself (account, executable/deployment access, database ACLs, operational controls); shared administrative accounts reduce actor attribution. Regardless of the choice, R1 deployment requires the explicit host permissions and operational audit review (§4.5); no Django authentication is built in this task. No secrets in any field. |
| D5 | Eligibility: COMPLETED parents only, or also PARTIALLY_COMPLETED? | (a) COMPLETED only (task wording; 7C-A alignment). (b) Include PARTIALLY_COMPLETED. | **(a)** — the business requirement names COMPLETED runs; PARTIALLY_COMPLETED runs have incomplete price evidence and their refresh semantics are a separate question. |
| D6 | Any bound on repeated post-terminal refreshes? (DESIGN2-FU1 C5; ordering corrected per DESIGN2-FU2) | (a) R0: none — no command surface exists in R0 at all; no general rate limiter is invented for R0 (or R1); each attempt is explicit, audited, one-call. (b) R1 minimal CMD safeguard: the safeguard is evaluated BEFORE a new refresh attempt is persisted (before the trigger INSERT) and BEFORE any new Vendor API request — the command displays the existing active state and the most recent terminal attempt; a terminal attempt within the preceding 5 minutes requires explicit `--force-repeat`, and a cooldown refusal leaves NO newly created PENDING child behind; any repeated attempt is a NEW child, never a rewrite; concurrent invocations are reviewed separately at R1 (the hard invariant is still UNIQUE(parent_run, active_slot) + CAS). This is an operator-safety check on the command surface — clearly distinct from a server-enforced comprehensive rate limit. (c) Server-enforced comprehensive rate limiting (requires identity; R3/8C scope). | **(a)** for R0; **(b)** for R1 (detailed implementation and race handling subject to R1 review); **(c)** deferred to R3. |
| D8 | What may DENIED connections learn? | (a) Total zero-knowledge (no existence/count/status/operator/price/**error**; no `VendorRefreshExecution` query at all). (b) Existence + status only, no prices. | **(a)** — same standard as the original supplemental snapshot; the refresh panel contains operator identity and error state, which must not leak; the public replay import/query firewall + armed fail-fast are preserved (§8.2). |
| D9 | Implementation base branch. | (a) `pilot-vendor-status-ux-a` (the production line). (b) `main`. | **(a)** — the feature is defined over the production architecture (incl. the vendor-status UX surface main lacks); merging main's semantic-V2 line is a separate, later decision. |
| D10 | Shared 4D-B binding/encoding helper extraction (one behavior-identical refactor of an orchestration private, covered by the frozen 4D-B suites). | (a) Approve the extraction. (b) Keep the refresh self-contained with a duplicated policy (two copies of the 2A binding + brand-new policy). | **(a)** — one policy, two call sites; duplication is a drift hazard the project's own guard culture rejects. |

---

## 13. Remaining risks (phase assignments, DESIGN2-FU2)

**Assigned to R1 (reviewed at the R1 design gate):**
- Trigger-vs-execution operator provenance (§4.6): the choice between
  constraining execution to the creating invocation and recording/obtaining
  truthful execution provenance through an explicitly approved mechanism;
  the orphaned-PENDING edge (creating invocation died between INSERT and
  claim — zero API calls, no unknown external outcome, slot blocked) has no
  R0/R1 resolution primitive until that choice is approved.
- Repeat-safeguard concurrency: two invocations can both pass the display-
  based safeguard before either persists; the safeguard is a coarse operator
  check — the hard invariant remains UNIQUE(parent_run, active_slot) + CAS.
- Operational recovery gate procedure (§3.6): what constitutes sufficient
  trusted external evidence of process termination is an operational
  procedure; no automation, lease, scheduler, or supervisor is invented.
- Host permissions + operational audit review prerequisite (DESIGN2-FU1 C4)
  must be completed and recorded before R1 deploys.
- Shared 4D-B binding/encoding helper extraction (D10) — behavior-identity
  over the frozen 4D-B suites.

**Assigned to R2:**
- Additive-section rendering must not leak any refresh fact to DENIED
  connections (armed fail-fast, §8.2); byte-identity scope of the
  with-history ALLOWED page (§8.1).
- Deterministic four-concept projections over mixed histories (identical-
  timestamp tie-breaks, PARTIAL inclusion, erasure-proof, §8.3).
- D2 (USD-equivalent for refreshed non-USD quotes) remains OPEN: R2 must
  not implement option (b) — historical FX reuse for display — without
  separate explicit approval.
- web-boundaries allowlist extension (§10.3(10)) — gated, recorded,
  adversarially pinned.

**Assigned to R3 (deferred; NOT part of the first implementation):**
- 8C authenticated operator identity + bounded cooldown policy (D6(c)) + a
  separate security review of the Web POST mutation surface.
- Request idempotency identity (concept 3, §3.3/§5.2): a retransmission of
  the SAME logical request must create no new child; latest-terminal-child
  lookup is insufficient.

**Cross-phase gates:**
- The 5,959-node production baseline (§1.4) is agent-reported and MUST be
  independently verified before any implementation; the node-level
  collection diff against it (0 removed / 0 renamed) is an implementation
  gate.
- Branch renumbering decision if the production line and dev-main are ever
  merged (D9/§10.1).

---

## Appendix A — Verification commands used (this session) [VERIFIED]

```
git cat-file -t cde2a802c54372da088a7d1876f450cbf9bd7c69            # commit
git log --oneline -5 cde2a802…                                      # branch tip
git branch -a --contains cde2a802…                                  # pilot-vendor-status-ux-a
git ls-tree -r --name-only cde2a802… | grep product_intelligence/   # tree
git show cde2a802…:<path>                                           # all source reads
git ls-tree cde2a802… -- <paths>                                    # blob IDs (§1.2)
git diff cde2a802… HEAD -- <paths>                                  # divergence (§1.3)
git worktree add --detach <tmp> cde2a802…                           # read-only baseline run
python -m pytest                                                    # 5959 passed, 39 subtests, 415.25 s
python -m pytest --collect-only -q                                  # 148 files / 5959 nodes
python manage.py check                                              # no issues
python manage.py makemigrations --check --dry-run                   # No changes detected
```

The temporary worktree contains no local modifications and no database file;
test execution used the in-memory SQLite test DB per `tests/conftest.py`.

## Appendix B — Task-constraint compliance map

| Task constraint | Where addressed |
|---|---|
| No new full ResearchRun / no pipeline rerun | §3.3 (eligibility on existing run), §6.1 (no claim_execution, no stages), §9 row 1 |
| No Serper / public pages / Semantic / comparables | §6.1 table + §10.3(3) AST/sentinel tests |
| No MPN/description change | §3.1 (parent row untouched), §6.2 (MPN read verbatim), §9 invariant |
| No Machine/Reviewed Price change | §6.3, §10.3(9), §9 invariant |
| No vendor→deterministic matching promotion | §6.3, §10.3(9) |
| No modification of historical PriceIntelligenceSnapshot / ResearchSupplementSnapshot | §3.1 append-only, §8.1, §10.3(2) byte-identity regression |
| No alteration of historical human-review decisions | §9 invariant (candidates untouched) |
| No reinterpretation of prior failed lookups as successful | §3.1, §8.3 (four-concept projections), §9 rows 5/10 |
| No ECB FX retrieval without separate approval | §7.1 (zero FX activity), §10.3(8) |
| OneToOne supplement model unchanged; no UPDATE/replacement shortcut | §3.1, §8.1, §10.1 (migration is additive only) |
| Transaction boundaries + crash/recovery documented | §3.6, §9 |
| Concurrency/idempotency incl. definition of one attempt | §5 |
| Vendor adapter bounded policy preserved; no invented retry | §5.3, §3.4 |
| CIDR gate ≠ mutation authorization; A vs B compared; safe first boundary | §4 |
| FX snapshot immutable; presentation rules incl. stale/refreshed distinction | §7 |
| Historical replay reproducible; separate refresh projection; public replay firewall; failed refresh never erases success | §8 |
| Required test list + test-preservation invariant + recorded baseline | §1.4, §10 |
| Design doc only; no code/test/migration/settings changes; no commit/push | this document (new untracked file); working tree otherwise untouched |
| Stale reclaim REJECTED; no recovery-based terminalization in R0 — complete/fail remain the ONLY legal RUNNING→terminal transitions (single-winner CAS issued by the claim winner; legitimate claim→complete and claim→fail succeed; duplicate terminalization fails without mutation; no test asserts RUNNING→COMPLETED or RUNNING→FAILED is prohibited); no stale reclaim, no threshold-triggered forced failure, no RUNNING→PENDING reset, no automatic retry, no operator-forced interrupt/recovery, no RUNNING reassignment; RUNNING occupies its slot; one execution identity per attempt; R1 operational recovery gate (trusted external evidence, atomic conditional transition, unknown external outcome, no overlap justified by slot reclaim); no lease/scheduler/supervisor invented | §3.3 (state-transition table), §3.4, §3.6, §5.1–5.3, §9 rows 8–10, §10.3(1)(4)(5), §11 (R0/R1), §12.2 D3 |
| The `vendor_refresh` management command + the default-provider runtime belong to R1, NOT R0; R0 has exactly persistence, model + migration, lifecycle claims, bounded errors and exports, offline tests; no management command, provider call, HTTP endpoint, template, or deployment in R0 | §3.5, §4.2, §10.3(4)(5), §11 (R0/R1) |
| D1 confirmed: original Quote & Market Summary + original vendor rows + existing PILOT-VENDOR-STATUS-UX-A status notice unchanged; R2 adds an independent Vendor Refresh History section; the optional status-notice pointer line is NOT approved for R2 (removed from the approved R0–R2 scope). D7 confirmed: only ALLOWED connections with at least one refresh record render the separate history section (a confirmed decision, NOT open) | §8.3, §12.1 |
| `operator` = self-reported TRIGGER initiator, not necessarily the executor of a PENDING child; R1 must constrain which invocation may execute it or record/obtain truthful execution provenance through an explicitly approved mechanism; no new model field without an approved justification that the existing schema cannot satisfy the requirement | §3.1, §3.3, §4.6, §10.3(5), §11 (R1), §12.2 D4 |
| Idempotency: three distinct concepts (active-child dedup / intentional post-terminal new child / same-request retransmission); R0 guarantees only concept 1 + CAS single-claim; R3 requires explicit stable request idempotency identity (latest-terminal-child lookup insufficient); R3 mechanism NOT added to R0 | §3.3, §5.2, §11 (R3) |
| Four-concept quotation vocabulary (latest execution / latest SUCCESS lookup incl. zero observations / latest usable quotation incl. PARTIAL / latest IN_STOCK positive-price); FAILED ≠ successful quotation; OUT_OF_STOCK/UNKNOWN/zero-price never mislabeled as purchaseable quotes; no "necessarily current" wording; deterministic ordering + identical-timestamp tie-breaker (`id` DESC); frozen codec unchanged | §7.3, §8.3, §9 row 13, §10.3(2)(4)(6), §11 (R2), §12.1 D1 |
| `--operator` self-reported provenance of the TRIGGER initiator, NOT authentication and NOT necessarily execution provenance (`USERNAME` not trusted identity proof; authorization = controlled Windows account access + executable/deployment access + database ACLs + operational controls; shared admin accounts reduce attribution; no unverified OS audit claims; R1 host permissions + operational audit review prerequisite; no Django authentication; trigger-vs-execution gap handled per §4.6) | §3.1, §3.3, §4.2, §4.4, §4.5, §4.6, §11 (R1), §12.2 D4 |
| No command surface in R0; no general rate limiter in R0 or R1; R1 minimal CMD safeguard (display active state + most recent terminal attempt; 5-minute `--force-repeat` gate; the safeguard is evaluated BEFORE a new refresh attempt is persisted and BEFORE any new Vendor API request — a cooldown refusal leaves NO newly created PENDING child; NEW child only, never a rewrite; concurrent invocations reviewed separately at R1); operator-safety check ≠ server-enforced rate limit | §3.5, §4.2, §5.2, §10.3(5), §11 (R0/R1), §12.2 D6 |
| `editable=False` is NOT a write barrier (ORM `.update()`/raw SQL bypass it); CHECK/UNIQUE enforce stored shapes + at most one active child; CAS services enforce permitted transitions; no "row never modified" proof; parent/child MPN equality and frozen codec validity are application-level validations; removed test claim that `editable=False` rejects arbitrary writes | §3.1, §10.3(1) |
| `CommercialLookupQuery` strips surrounding whitespace (verified §1.2); constructed query MPN must exactly equal the immutable captured canonical MPN or fail closed (`MPN_QUERY_NORMALIZATION_MISMATCH`, zero network calls); stored `result_schema_version` agrees with payload codec schema version; invalid payloads rejected by producer or fail closed on read; frozen 2A binding + codec preserved | §1.2, §3.1, §3.4, §6.2, §10.3(2) |
| Original persisted snapshots + original replay projections unchanged; R2 separate additive projection; NO whole-page byte-identity promise for the with-history ALLOWED page (DENIED + no-history pages byte-identical); DENIED zero-knowledge incl. errors + no `VendorRefreshExecution` query; public replay firewall + armed fail-fast preserved; no influence on Machine Price / Reviewed Price / semantic authority / comparables / original quote statistics; no FX retrieval, no FX cache writes, no historical FX reuse | §7.1, §7.4, §8.1, §8.2, §8.5, §10.3(6)(7)(8), §11 (R2), §12.1 D7, §12.2 D2/D8 |
| 5,959-node historical baseline (agent-reported; MUST be independently verified before any implementation — gate preserved); C9 regression coverage (SUCCESS-zero-observations; PARTIAL-with-valid-observations; FAILED-after-success; zero-price/OUT_OF_STOCK; most recent attempt vs most recent usable quote; identical-timestamp ordering; query normalization mismatch; schema-version mismatch; DB structural constraints vs application immutability; recovery-based terminalization absent from R0 + no implicit retry path + legitimate claim→complete/claim→fail succeed (single-winner terminal CAS; duplicate terminalization fails without mutation; a stuck RUNNING row cannot be forcibly terminated via any R0 recovery path; a trigger over RUNNING returns the existing child); original alias snapshot / comparables / review / execution evidence untouched); no existing test deleted, renamed, skipped, xfailed, deselected, ignored, weakened, or replaced | §1.4, §10.2, §10.3(1), §9 invariant, §13 |
