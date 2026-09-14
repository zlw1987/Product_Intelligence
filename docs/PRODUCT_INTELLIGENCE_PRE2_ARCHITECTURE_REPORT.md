# PRODUCT-INTEL.7C-PRE2 Architecture Investigation Report

**Comparable Research Child Execution & Persistence Architecture Closure**

---

## 1. Executive Verdict: GO for PRE2 Architecture Closure

The investigation finds that a dedicated child-execution model (Option B) is the
only architecture that satisfies all constraints without weakening any frozen
contract. The required additive surface is narrow, follows existing patterns,
and can be proven safe against the old 6C-only 7B executor.

No frozen file needs modification. No stop conditions are triggered.

---

## 2. Current ResearchRun Lifecycle Map

**File:** `product_intelligence/runs/models.py` (lines 1-821)
**File:** `product_intelligence/runs/execution_claims.py` (full file)
**File:** `product_intelligence/domain/enums.py` (ResearchRunState, lines ~90-105)

### 2.1 Exact ResearchRun Model Fields

| Field | Type | Mutable | Notes |
|-------|------|---------|-------|
| `id` | `UUIDField(primary_key=True, default=uuid.uuid4)` | Immutable | UUID v4, app-assigned |
| `manufacturer_part_number` | `TextField(blank=True)` | Immutable after creation | From ResearchRequest |
| `description` | `TextField(blank=True)` | Immutable after creation | From ResearchRequest |
| `state` | `CharField(max_length=32, choices=STATE_CHOICES)` | Via `transition_to()` only | Edited=False |
| `created_at` | `DateTimeField(default=timezone.now)` | Immutable | Edited=False |
| `started_at` | `DateTimeField(null=True)` | Set on RUNNING transition | Edited=False |
| `finished_at` | `DateTimeField(null=True)` | Set on terminal transition | Edited=False |

### 2.2 Status Vocabulary

Defined in `domain/enums.py` `ResearchRunState`:
```
CREATED -> RUNNING -> {COMPLETED, PARTIALLY_COMPLETED, FAILED}
```

Terminal states: `{COMPLETED, PARTIALLY_COMPLETED, FAILED}`

### 2.3 ALLOWED_TRANSITIONS

```python
CREATED:   {RUNNING}
RUNNING:   {COMPLETED, PARTIALLY_COMPLETED, FAILED}
COMPLETED:   {}
PARTIALLY_COMPLETED: {}
FAILED:        {}
```

Terminal states are **truly terminal** — empty successor sets. No reopen, no
resume, no retry-in-place.

### 2.4 How a Run Is Created

`ResearchRunManager.create_from_request(request: ResearchRequest)`:
- Takes a `ResearchRequest` (canonical domain object)
- Stores `manufacturer_part_number` and `description` exactly as the request produced them
- Creates the row with `state=CREATED`
- `save()` enforces initial state must be CREATED

### 2.5 How a Run Is Claimed

`claim_execution(run_id)` in `runs/execution_claims.py`:
- **Compare-and-set** via `QuerySet.update()` with WHERE clause
- WHERE: `id=target_id AND state=CREATED AND started_at IS NULL AND finished_at IS NULL`
- SET: `state=RUNNING, started_at=now()`
- Checks `rows_affected`; if 0, diagnoses the reason (not found, already claimed, terminal)
- **No `select_for_update`**, no row locking, no version field
- Portable across SQLite/PostgreSQL/MySQL

### 2.6 Concurrency Protection

**Claim uses:** database-level compare-and-set (single UPDATE with WHERE).
- No `transaction.atomic`
- No `select_for_update`
- No version field
- No ownership token

This is explicit in the code comments:
> "The atomicity is achieved through a single UPDATE statement with a WHERE
> clause that checks the current state. This is portable across databases
> (SQLite, PostgreSQL, and MySQL)."

### 2.7 Duplicate Execution Prevention

The compare-and-set claim guarantees at most one successful claim per run.
A second caller gets `ClaimExecutionFailed(reason="already_claimed")`.

### 2.8 Crash After Claim

If execution crashes after claim, the run stays in `RUNNING` state. There is
currently no stale-RUNNING recovery mechanism. The run's `started_at` is set
but `finished_at` is NULL — the lifecycle shape constraint allows this (it
defines RUNNING as `started_at NOT NULL, finished_at NULL`).

### 2.9 Existing Retry/Recovery Semantics

`retry_run(old_run: ResearchRun) -> ResearchRun`:
- Only works on terminal runs
- Creates a **NEW** ResearchRun from the old run's `to_research_request()`
- Old run is **never** reset or modified
- No snapshot or evidence is copied

### 2.10 Status Transition Validation

`transition_to(target_state)` in `ResearchRun`:
- Checks `ALLOWED_TRANSITIONS[current]` — raises `InvalidResearchRunTransition`
- Sets timestamps mechanically (started_at on RUNNING, finished_at on terminal)
- `save(update_fields=...)` only — never raw state assignment
- `save()` guard: `_persisted_state` tracks last-known DB state; if `state`
  changed without going through `transition_to()`, raises `UnsupportedResearchRunStateChange`
- `LIFECYCLE_SHAPE` check constraint at DB level validates structural
  consistency regardless of how the row was written

### 2.11 Where Results Are Stored

- `PriceIntelligenceSnapshot`: OneToOne to ResearchRun (price result)
- `ExecutionEvidenceRecord`: ForeignKey to ResearchRun (per-attempt evidence)
- `AiAssistedReviewCandidate`: ForeignKey to ResearchRun (semantic review)
- Nothing is stored directly on ResearchRun beyond state/timestamps/inputs

### 2.12 Input Immutability

`manufacturer_part_number` and `description` have no `editable=False`, but the
design treats them as immutable — they are set at creation from the canonical
`ResearchRequest` and never changed by any lifecycle operation. The
`to_research_request()` method rebuilds the same request from stored fields.

### 2.13 Can Completed Runs Receive Additional Artifacts?

**Yes.** The current architecture already supports this:
- `PriceIntelligenceSnapshot` is a OneToOne to ResearchRun — created after
  execution completes, not during
- `AiAssistedReviewCandidate` is ForeignKey — created at final publication
  time alongside the snapshot
- A completed run can have review candidates added to it
- Terminal state transitions are truly terminal, but child records can be
  added to a terminal parent

### 2.14 Existing Child-Model Patterns

Three child patterns already exist:

1. **OneToOne result snapshot** — `PriceIntelligenceSnapshot`
   - `run = OneToOneField(ResearchRun, primary_key=True, on_delete=CASCADE)`
   - One per run, at most
   - Versioned JSON payload

2. **ForeignKey evidence records** — `ExecutionEvidenceRecord`
   - `run = ForeignKey(ResearchRun, on_delete=CASCADE)`
   - Many per run, ordered by `attempt_number`
   - Unique constraint on `(run, attempt_number)`

3. **ForeignKey child execution** — `AiAssistedReviewCandidate`
   - `run = ForeignKey(ResearchRun, on_delete=CASCADE)`
   - Many per run
   - UUID primary key
   - Independent lifecycle state (`review_state`)
   - Immutable semantic provenance + mutable state
   - Check constraint on state/timestamp consistency

---

## 3. Current Web -> Execution Boundary Map

**File:** `product_intelligence/web/views.py` (full file)
**File:** `product_intelligence/web/urls.py` (full file)
**File:** `product_intelligence/web/presentation.py` (full file)

### 3.1 Current Web Imports from Execution

```python
from product_intelligence.execution import ExecutionError, execute_research_run
```

### 3.2 Current Web Imports from Runs

```python
from product_intelligence.runs import ClaimExecutionFailed, retry_run
from product_intelligence.runs import (
    CandidateNotFoundError, CrossRunReviewError, InvalidCandidateError,
    ReviewConflictError, RunNotReviewableError,
    confirm_candidate, reject_candidate, undo_review,
)
from product_intelligence.runs.models import (
    AiAssistedReviewCandidate, PriceIntelligenceSnapshot, ResearchRun,
)
```

### 3.3 Current Web Imports from Research

```python
from product_intelligence.research.aggregation import PriceAggregationResult
from product_intelligence.research.aggregation import aggregate_reviewed_listing_prices
from product_intelligence.research.price_result_codec import (
    PriceResultCodecError, decode_price_aggregation_result,
)
```

### 3.4 Current Web Imports from Domain

None directly (all through other layers).

### 3.5 Current Web Imports from Providers

None directly.

### 3.6 Web Boundary Summary

| Import source | What web imports |
|---------------|-----------------|
| `execution` | `execute_research_run`, `ExecutionError` |
| `runs` | `ClaimExecutionFailed`, `retry_run`, review primitives + errors |
| `runs.models` | `ResearchRun`, `PriceIntelligenceSnapshot`, `AiAssistedReviewCandidate` |
| `research` | `PriceAggregationResult`, `price_result_codec`, `aggregate_reviewed_listing_prices` |
| `web.presentation` | `build_report_presentation`, `_check_candidate_binding` |
| `providers` | **Nothing** |
| `domain` | **Nothing** |

### 3.7 Web Execution Invocation Pattern

In `research_new()` POST:
1. Create `ResearchRun` from form
2. Call `execute_research_run(str(run.id))` **synchronously**
3. Catch `ClaimExecutionFailed`, `ExecutionError`, generic `Exception`
4. Redirect to report

In `research_detail()` GET:
1. Load `ResearchRun`
2. Load `PriceIntelligenceSnapshot` (if exists)
3. Decode via `decode_price_aggregation_result()`
4. Build presentation via `build_report_presentation()`
5. Load `AiAssistedReviewCandidate` records
6. Render

**Key invariant:** Web does NOT perform research, scoring, or authority
establishment. Web triggers execution and reads stored results.

### 3.8 Existing Routes

```
GET  /research/new                          -> research_new (form display)
POST /research/new                          -> research_new (create + execute)
GET  /research/<uuid>                       -> research_detail (report)
POST /research/<uuid>/retry                 -> research_retry (new run + execute)
POST /research/<uuid>/review/<uuid>         -> research_review (human review action)
```

---

## 4. Existing Persistence/Codec Patterns

### 4.1 Versioned JSON Snapshots

`PriceIntelligenceSnapshot` (runs/models.py):
- `schema_version: PositiveSmallIntegerField` (check: >= 1)
- `payload: JSONField`
- OneToOne to ResearchRun (PK = run UUID)
- `created_at: DateTimeField`
- Codec in `research/price_result_codec.py` (not in runs)
- Strict decode: unknown version, missing keys, extra keys, wrong types all raise `PriceResultCodecError`
- Codec is pure: no Django, no network, no execution, no web imports

### 4.2 Child Records with Lifecycle

`AiAssistedReviewCandidate` (runs/models.py):
- UUID PK (not the run UUID)
- ForeignKey to ResearchRun
- `review_state` with transitions (UNREVIEWED <-> CONFIRMED/REJECTED)
- Immutable semantic provenance fields (set at creation, `editable=False`)
- Check constraint: UNREVIEWED requires `reviewed_at` NULL; CONFIRMED/REJECTED requires `reviewed_at` NOT NULL
- Unique constraint: `(run, assessment_index)`
- State transitions handled in `runs/ai_assisted_review.py`

### 4.3 Execution Evidence Records

`ExecutionEvidenceRecord` (runs/models.py):
- Auto-increment PK
- ForeignKey to ResearchRun
- `attempt_number` (unique per run, >= 1)
- `stage`, `outcome`, `candidate_url`, `detail_code`
- Check constraints on URL format, attempt_number >= 1
- Indexed on `(run, attempt_number)`, `(run, stage)`, `(run, outcome)`
- Ordered by `(run, attempt_number)`

### 4.4 Existing Claim/Retry State

`execution_claims.py` uses compare-and-set UPDATE pattern:
- Single UPDATE with WHERE clause
- Checks rows_affected
- Diagnoses failure reason from current state

### 4.5 Schema Versioning

`PriceIntelligenceSnapshot.schema_version` with check constraint `>= 1`.
Codec accepts only `PRICE_RESULT_SCHEMA_VERSION` (currently 1).
Unknown version raises `PriceResultCodecError` — no best-effort migration.

---

## 5. Options Considered

### Option A: Extend ResearchRun with Comparable Fields/Status

**Verdict: REJECTED**

- **Compatibility:** Would require modifying ResearchRun model (frozen). Adding
  new terminal states violates existing transition table. Adding non-terminal
  states after COMPLETED requires breaking the "truly terminal" invariant.
- **Lifecycle isolation:** Impossible — comparable failure semantics would
  pollute parent ResearchRun state space.
- **Claim safety:** Would need a second claim mechanism on the same model,
  introducing dual-concurrency concerns.
- **Retry behavior:** Would conflict with existing retry semantics (retry
  creates new ResearchRun).
- **Persistence clarity:** Comparable result would be a field on the same
  table as price intelligence, violating the separation already established.
- **Migration impact:** Requires migration to frozen model.
- **Risk of semantic leakage:** High — comparable lifecycle bleeds into parent.

### Option B: Dedicated Child Model Related to ResearchRun

**Verdict: RECOMMENDED**

- **Compatibility:** Fully compatible. Existing child patterns (OneToOne
  snapshot, ForeignKey evidence, ForeignKey review) prove this works.
  Parent ResearchRun is never touched.
- **Lifecycle isolation:** Complete. Child has its own state machine,
  claim mechanism, and retry semantics.
- **Claim safety:** Compare-and-set on child's own state field.
- **Retry behavior:** New child record on retry (matches `retry_run` pattern).
- **Idempotency:** Unique constraint on `(parent_run)` for first-child
  creation; subsequent retries create new child records.
- **Persistence clarity:** Follows `PriceIntelligenceSnapshot` and
  `AiAssistedReviewCandidate` patterns exactly.
- **Migration impact:** Only new model, no changes to existing models.
- **Web-layer impact:** Web adds one new route and reads one new child model.
- **Risk of semantic leakage:** Zero — child is fully isolated.
- **Compatibility with frozen phases:** All frozen phases remain untouched.

### Option C: Persist Only a Result Snapshot Without Lifecycle Model

**Verdict: REJECTED**

- **Lifecycle isolation:** Impossible — no lifecycle model means no durable
  claim state, no RUNNING indication, no retry tracking.
- **Claim safety:** Cannot prevent duplicate execution without a durable
  state-bearing record.
- **Retry behavior:** No way to track whether comparable research has been
  attempted for a given parent.
- **Compatibility:** Contradicts the explicit requirement for "durable
  claim/running state."

### Option D: Reuse an Existing Generic Child-Execution/Job Model

**Verdict: REJECTED**

- No generic child-job model exists. `ExecutionEvidenceRecord` is per-attempt
  evidence for a single run, not an independent child execution.
- `AiAssistedReviewCandidate` has a lifecycle but it is specific to human
  review semantics (UNREVIEWED/CONFIRMED/REJECTED), not execution
  lifecycle (PENDING/RUNNING/COMPLETED/FAILED).

### Option E: Other

**Verdict: No other repo-backed architecture found.** The three child
patterns identified above cover all existing persistence conventions.

---

## 6. Recommended Child-Execution Architecture

**Option B: Dedicated child model.**

### 6.1 Proposed Model

New model `ComparableResearchResult` in `product_intelligence/runs/models.py`:

```python
class ComparableResearchResult(models.Model):
    """One durable comparable-research execution for a ResearchRun.

    PRODUCT-INTEL.7C-PRE2.

    Each record represents one comparable-research execution attempt for a
    parent ResearchRun. The child has its own lifecycle state machine, claim
    mechanism, and versioned JSON payload. Parent ResearchRun state is never
    affected by child execution outcomes.

    Multiple child records per parent are legitimate: a failed child can be
    retried by creating a new child record. The old failed record remains
    as durable history.
    """
```

### 6.2 Why ForeignKey, Not OneToOne

- **OneToOne** (`PriceIntelligenceSnapshot` pattern) implies at most one
  record. A comparable execution that fails and is retried would need either:
  (a) mutation of the existing record (losing failure history), or
  (b) violation of the OneToOne constraint.
- **ForeignKey** (`AiAssistedReviewCandidate` pattern) allows multiple
  records. Retry creates a new record. Old records persist as history.
- The idempotency guarantee ("only one active comparable execution per
  parent at a time") is enforced by the claim mechanism (compare-and-set on
  child state), not by the FK cardinality.
- The `related_name` would be `comparable_research_results` (plural).

### 6.3 Ordering

Children would be ordered by `created_at` (ascending), so the most recent
attempt is last. The web report would show the latest COMPLETED or FAILED
child, with historical attempts available.

### 6.4 Which Child to Display

The web report would query for the latest child:
```python
latest_child = parent.comparable_research_results.latest("created_at")
```

If multiple COMPLETED children exist (e.g., retry after a previous failure),
the latest one is shown. If the latest is RUNNING, a "research in progress"
indicator is shown.

---

## 7. Exact Proposed Child Lifecycle/State Machine

### 7.1 State Vocabulary

Defined in a new enum (not in `ResearchRunState` — child owns its own vocabulary):

```python
class ComparableResearchState(str, Enum):
    PENDING = "PENDING"
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
```

### 7.2 Transitions

```python
PENDING:   {RUNNING}
RUNNING:   {COMPLETED, FAILED}
COMPLETED:   {}
FAILED:        {}
```

Terminal states are truly terminal (empty successors), matching the parent
pattern. Retry creates a **new** child record in PENDING state.

### 7.3 Lifecycle Shape Constraint

```python
LIFECYCLE_SHAPE = (
    models.Q(state=PENDING.value, started_at__isnull=True, finished_at__isnull=True)
    | models.Q(state=RUNNING.value, started_at__isnull=False, finished_at__isnull=True)
    | models.Q(state__in=[COMPLETED.value, FAILED.value],
               started_at__isnull=False, finished_at__isnull=False)
)
```

### 7.4 Timestamp Fields

| State | `created_at` | `started_at` | `finished_at` |
|-------|-------------|-------------|--------------|
| PENDING | set | NULL | NULL |
| RUNNING | set | set | NULL |
| COMPLETED | set | set | set |
| FAILED | set | set | set |

---

## 8. Parent/Child Relationship and Idempotency Contract

### 8.1 Relationship

- **ForeignKey** from `ComparableResearchResult` to `ResearchRun`
- `on_delete=CASCADE` (deleting parent deletes all children)
- `related_name='comparable_research_results'`

### 8.2 Multiplicity

- One or more children per parent (multiple retries create new children)
- At most one child in PENDING or RUNNING at any time (enforced by claim)
- Parent ResearchRun must be in a terminal state before comparable research
  is triggered (guarantees price research completed independently)

### 8.3 Idempotency

Triggering comparable research for a parent that already has:
- A COMPLETED child: **no-op** (return existing child, no new work)
- A RUNNING child: **no-op** (return existing child, no new work)
- A FAILED child with no other active child: **create new PENDING child**
- A PENDING child: **no-op** (return existing child)

This is implemented by checking `parent.comparable_research_results` before
creating a new record.

### 8.4 Parent Status Isolation

**Critical invariant:** Comparable research execution (success or failure)
must NEVER alter the parent ResearchRun's state. The parent is already in a
terminal state. Writing to the parent would violate the frozen transition
table and the "truly terminal" invariant.

### 8.5 Parent Failure and Comparable Execution

If the parent ResearchRun is FAILED, comparable research may still be
triggered (the comparable research is a separate concern). If the parent
is COMPLETED or PARTIALLY_COMPLETED, comparable research is the normal path.

### 8.6 Deleting/Rerunning Parent

- Deleting parent: CASCADE deletes all children
- Rerunning parent: `retry_run()` creates a new parent ResearchRun. The
  new parent has NO children. Comparable research must be re-triggered
  for the new parent.

### 8.7 Concurrency

Two concurrent requests triggering comparable research for the same parent:
1. Both check for existing active child — both see none
2. Both attempt to create a PENDING child — database handles this (no unique
   constraint on just `parent_run`)
3. Both attempt to claim one of the PENDING children — compare-and-set ensures
   only one succeeds
4. The loser gets `ClaimExecutionFailed`

To prevent step 2 race, the trigger function should use a transaction that
checks-for-then-creates atomically. The compare-and-set claim provides the
hard guarantee.

---

## 9. Claim/Retry/Crash-Recovery Contract

### 9.1 Initial Trigger

POST endpoint or programmatic API creates a PENDING child record. If a
non-terminal child already exists (PENDING or RUNNING), returns the existing
child without creating a duplicate.

### 9.2 Atomic Claim

Compare-and-set UPDATE on the child's state field:
```python
rows = ComparableResearchResult.objects.filter(
    id=child_id,
    state=PENDING.value,
    started_at__isnull=True,
    finished_at__isnull=True,
).update(state=RUNNING.value, started_at=now())
```

If `rows == 0`, claim failed (diagnose: not found, already running, terminal).

### 9.3 Already-Running Behavior

Trigger returns the existing RUNNING child. No new work starts.

### 9.4 Already-Completed Behavior

Trigger returns the existing COMPLETED child. No new work starts.

### 9.5 Failed Child Retry

Retry creates a **new** PENDING child record (not mutating the old one).
The old FAILED child remains as durable history.

### 9.6 Crash After Claim

Child stays in RUNNING state. No automatic recovery exists (matching the
parent ResearchRun behavior). A stale-RUNNING recovery mechanism could be
added in a future phase but is not required for 7C-PRE2.

### 9.7 Duplicate Concurrent Triggers

Both create PENDING children (race on step 2 above). Both attempt claim —
only one succeeds (compare-and-set guarantee). The other gets
`ClaimExecutionFailed`. The orphan PENDING child can be manually cleaned up
or left as dead record (no semantic harm — it will never execute).

**Mitigation:** The trigger function should atomically check-and-create
within a transaction to minimize the race window.

### 9.8 Stale RUNNING Recovery

Not required for 7C-PRE2. If needed in a future phase, a new child record
can be created and the old RUNNING child left as abandoned history.

### 9.9 Maximum Attempt Semantics

No maximum attempts. Each retry creates a new child record. This matches
the parent's `retry_run()` semantics.

### 9.10 Retry Overwrites Previous Failure Detail

No overwriting. Each attempt is a new record with its own payload and
timestamps. All attempts remain inspectable.

---

## 10. Semantic Abstention vs Execution Failure Contract

### 10.1 Execution Lifecycle State vs Semantic Result

The child's `state` field represents **execution lifecycle**, not semantic
outcome. A successful execution that produces "no authority match" is
`COMPLETED`, not `FAILED`.

### 10.2 Semantic Abstention Classification

| Scenario | Execution State | Semantic Outcome |
|----------|----------------|-----------------|
| Authority context ESTABLISHED, candidates found, scored | COMPLETED | Full comparable result |
| Authority context NO_AUTHORITY_MATCH (e.g., Samsung, unknown MPN) | COMPLETED | Abstention result |
| Authority context AMBIGUOUS_AUTHORITY_MATCH | COMPLETED | Abstention result |
| Authority context NO_REQUESTED_MPN | COMPLETED | Abstention result |
| 7A candidate discovery: no candidates found | COMPLETED | Empty comparable result |
| Page fetch failed (transient network error) | FAILED | N/A |
| Programming exception (invariant violation) | FAILED | N/A |
| Persistence failure | FAILED | N/A |

### 10.3 Why Not NOT_APPLICABLE as Execution State

`NOT_APPLICABLE` would conflate semantic outcome with execution lifecycle.
PRE1 explicitly established that `NO_AUTHORITY_MATCH` does NOT prove:
- unsupported manufacturer
- unsupported category
- not an enterprise SSD
- permanently not applicable

A `NO_AUTHORITY_MATCH` today might become `ESTABLISHED` tomorrow when a new
authority policy is reviewed and added. The execution was successful — it
just produced a bounded abstention.

### 10.4 Where Semantic Outcome Lives

The semantic outcome (ESTABLISHED, NO_AUTHORITY_MATCH, etc.) is encoded in
the child's JSON `payload`, not in the `state` field. The payload contains
the full execution result including authority acquisition outcomes.

---

## 11. Exact Post-6D Orchestration Chain

### 11.1 The Semantic Chain

```
ResearchRun (parent, COMPLETED)
    |
    v
PRE1: acquire_comparable_research_authority_context(request, page_fetcher)
    -> ComparableResearchAuthorityAcquisitionResult
    |
    If ESTABLISHED:
    |
    v
6C target: research_enterprise_ssd_specifications(
    product_identity=context.target_identity,
    sources=(context.specification_source,),
    page_fetcher=page_fetcher,
) -> SpecificationEvidenceResult (target 6C)
    |
    v
7A: discover_enterprise_ssd_comparable_candidates(
    target_identity=context.target_identity,
    target_specification_set=<target 6C spec set>,
    sources=(context.comparable_source,),
    page_fetcher=page_fetcher,
) -> ComparableCandidateDiscoveryResult
    |
    v
6D target: enrich_enterprise_ssd_specifications(
    product_identity=context.target_identity,
    discovery_result=<7A result>,
    source_outcome=<7A EXTRACTED outcome>,
    page_fetcher=page_fetcher,
    document_fetcher=document_fetcher,
) -> SpecificationEnrichmentResult (target 6D)
    |
    v
Compose target: compose_6c_6d_specifications(
    product_identity=context.target_identity,
    frozen_6c_spec_set=<target 6C spec set>,
    enrichment_result=<target 6D result>,
) -> ProductSpecificationSet (target 6C+6D)
    |
    v
For each candidate in 7A result:
    6C candidate: research_enterprise_ssd_specifications(
        product_identity=<candidate identity via 7B bridge>,
        sources=<7A EXTRACTED sources>,
        page_fetcher=page_fetcher,
    ) -> SpecificationEvidenceResult (candidate 6C)
    |
    v
    6D candidate: enrich_enterprise_ssd_specifications(
        product_identity=<candidate identity>,
        discovery_result=<7A result>,
        source_outcome=<7A EXTRACTED outcome>,
        page_fetcher=page_fetcher,
        document_fetcher=document_fetcher,
    ) -> SpecificationEnrichmentResult (candidate 6D)
    |
    v
    Compose candidate: compose_6c_6d_specifications(...)
    -> ProductSpecificationSet (candidate 6C+6D)
    |
    v
    Profile: ComparableCandidateSpecificationProfile(
        candidate=<7A candidate>,
        candidate_identity=<candidate identity>,
        specification_set=<candidate 6C+6D spec set>,
    )
    |
    v
7B pure: score_enterprise_ssd_candidate_similarity(
    target_specification_set=<target 6C+6D spec set>,
    candidate_profile=<candidate profile>,
) -> EnterpriseSsdCandidateSimilarity
    |
    v
Final result: ComparableResearchExecutionResult (NEW)
    -> encode via codec
    -> persist in ComparableResearchResult.payload
```

### 11.2 New Orchestration Primitive

A new function in `execution/` (not modifying frozen 7B):

```python
def execute_comparable_research(
    run_id: str,
    *,
    page_fetcher: PageFetcher | None = None,
    document_fetcher: DocumentFetcher | None = None,
) -> ComparableResearchExecutionResult:
    """Execute the full comparable research pipeline for a parent ResearchRun.

    Pipeline: PRE1 -> 6C target -> 7A -> 6D target -> compose target ->
              per-candidate: 6C -> 6D -> compose -> 7B pure scoring
    """
```

This function does NOT call `research_and_score_enterprise_ssd_candidates()`
(the old 6C-only 7B executor). It calls the same low-level primitives
(6C extraction, 6D enrichment, compose, 7B pure scoring) but in the
correct post-6D order.

---

## 12. Old 6C-Only 7B Leakage Analysis

### 12.1 Frozen 7B Functions

**File:** `product_intelligence/research/enterprise_ssd_similarity.py` (pure, frozen 7B)

| Symbol | Safe for reuse? | Reason |
|--------|----------------|--------|
| `establish_candidate_product_identity(candidate)` | **YES** | Pure bridge. Takes any `ComparableCandidate` from 7A, produces `ProductIdentity`. No scoring. No 6C dependency. |
| `ComparableCandidateSpecificationProfile` | **YES** | Dataclass. Binds candidate + identity + any `ProductSpecificationSet`. No scoring logic. Accepts spec set from any source. |
| `score_enterprise_ssd_candidate_similarity(target_spec_set, candidate_profile)` | **YES** | Pure scoring function. Takes any `ProductSpecificationSet` and `ComparableCandidateSpecificationProfile`. No I/O, no extraction, no 6C dependency. |
| `ComparisonState` enum | **YES** | Pure vocabulary. |
| `SpecificationSimilarityFieldAssessment` | **YES** | Pure dataclass. |
| `EnterpriseSsdCandidateSimilarity` | **YES** | Pure dataclass. |
| `_compute_field_similarity()` | **YES** | Internal pure computation. |

**All pure 7B research-layer symbols are safe for reuse.** They are
schema-aware but source-agnostic: they score any `ProductSpecificationSet`
regardless of whether it came from 6C-only, 6D-only, or 6C+6D composition.

### 12.2 Frozen 7B Execution-Layer Functions

**File:** `product_intelligence/execution/comparable_similarity.py` (7B execution, frozen)

| Symbol | Safe for reuse? | Reason |
|--------|----------------|--------|
| `ComparableSimilaritySourceOutcome` | **NO** | Tied to 7A discovery source outcomes. The post-6D path may have additional sources (datasheets) not in the 7A discovery result. |
| `ComparableSimilaritySourceOutcomeState` | **NO** | Same as above. |
| `EnterpriseSsdSimilarityResult` | **NO** | Contains `discovery_result` (the old 7A object) and validates evidence against 7A/7B source outcomes. The post-6D path has additional evidence sources (6D datasheets) that this result type cannot audit. |
| `research_and_score_enterprise_ssd_candidates(discovery_result, page_fetcher)` | **NO** | This is the high-level 7B executor. It performs its own 6C extraction from 7A sources, then scores. It does NOT perform 6D enrichment. Using it would leak 6C-only results. |

### 12.3 Why `research_and_score_enterprise_ssd_candidates()` Must Not Be Called

This function (the old 6C-only 7B executor):
1. Takes a `ComparableCandidateDiscoveryResult` from 7A
2. Fetches 7A EXTRACTED sources
3. Extracts candidate specs via 6C from those sources only
4. Builds `ComparableCandidateSpecificationProfile` with 6C-only spec sets
5. Scores via pure 7B

Steps 3-4 use **only 6C evidence** (from 7A support catalog sources). They
**do not** call 6D datasheet enrichment. The resulting `ProductSpecificationSet`
would be the same 6C-only set the frozen 7B was designed for.

If the new orchestration called this function, the comparable result would
be 6C-only — exactly the leakage we must prevent.

### 12.4 Candidate Profile Reuse

`ComparableCandidateSpecificationProfile` is safe to reuse because it accepts
any `ProductSpecificationSet`. The new orchestration builds the spec set
from 6C+6D composition and passes it in. The profile dataclass itself
does not know or care about the source of the spec set.

### 12.5 How Tests Prove No Leakage

1. **Unit tests** for the new orchestration function verify that
   `research_and_score_enterprise_ssd_candidates()` is never called (mock or
   import boundary check).
2. **Integration tests** verify that the persisted payload contains
   datasheet evidence (6D provenance) that the old 6C-only path could not
   produce.
3. **Boundary tests** verify the new orchestration module does not import
   the old 7B high-level executor.

---

## 13. Proposed Execution Result Contract

### 13.1 New Execution Result Type

```python
@dataclass(frozen=True)
class ComparableResearchExecutionResult:
    """Complete comparable research execution result.

    Produced by the new post-6D orchestration pipeline. Encodes:
    - Target identity and authority outcome
    - Per-candidate composed specification and similarity results
    - Field-level comparison details
    - Source/provenance references
    """

    # Authority outcome
    authority_status: AuthorityAcquisitionStatus  # from PRE1

    # Target
    target_mpn: str
    target_manufacturer: str | None

    # Candidates (ordered by MPN alphabetical, NOT similarity-descending)
    candidates: tuple["ComparableCandidateResult", ...]
```

```python
@dataclass(frozen=True)
class ComparableCandidateResult:
    """One candidate's comparable research result."""

    candidate_mpn: str
    candidate_normalized_mpn: str

    # Similarity scores (from pure 7B)
    scored_field_count: int
    evidence_coverage: Decimal  # scored / total definitions
    observed_similarity: Decimal | None
    evidence_weighted_similarity: Decimal | None

    # Per-field assessments
    field_assessments: tuple["FieldAssessmentResult", ...]
```

```python
@dataclass(frozen=True)
class FieldAssessmentResult:
    """One specification field's comparison result."""

    definition_key: str  # e.g., "capacity", "interface", "form_factor"
    comparison_state: str  # SCORED, TARGET_NOT_VERIFIED, etc.
    target_value: str | None  # human-readable target value (or None)
    candidate_value: str | None  # human-readable candidate value (or None)
    target_resolution_state: str  # VERIFIED, UNKNOWN, etc.
    candidate_resolution_state: str  # VERIFIED, UNKNOWN, etc.
    field_similarity: Decimal | None  # only when SCORED
```

### 13.2 What Is NOT Stored

- Raw `ComparableCandidateDiscoveryResult` object (not JSON-serializable,
  contains object-identity bindings)
- Raw `ComparableCandidateSourceOutcome` objects (same)
- Raw `FetchedPage` objects
- Raw exception text
- Provider-specific details

### 13.3 Candidate Ordering

**Default order: MPN alphabetical** (not similarity-descending).
This is the presentation-layer default. The execution result stores candidates
in MPN order. The web layer must NOT reorder by score.

---

## 14. Proposed Persisted/Read-Model Contract

### 14.1 Persisted Schema (JSON payload structure)

```json
{
    "schema_version": 1,
    "authority_status": "ESTABLISHED",
    "target_mpn": "ZF40206_G006",
    "target_manufacturer": "Seagate",
    "candidates": [
        {
            "candidate_mpn": "ZF40206-G004",
            "candidate_normalized_mpn": "zf40206g004",
            "scored_field_count": 10,
            "evidence_coverage": "0.8333333333333333333333333333",
            "observed_similarity": "0.9000000000000000000000000000",
            "evidence_weighted_similarity": "0.7500000000000000000000000000",
            "field_assessments": [
                {
                    "definition_key": "capacity",
                    "comparison_state": "SCORED",
                    "target_value": "3.84 TB",
                    "candidate_value": "1.92 TB",
                    "target_resolution_state": "VERIFIED",
                    "candidate_resolution_state": "VERIFIED",
                    "field_similarity": "0.5"
                }
            ]
        }
    ]
}
```

### 14.2 What Web Reads

After decoding:
- `authority_status`: shows whether comparable research was authoritative
- `target_mpn` + `target_manufacturer`: identifies the target
- `candidates[]`: array of comparable products, each with:
  - MPN, normalized MPN
  - Scored field count, coverage
  - Per-field comparisons (similarities, differences, unverified fields)

Web does NOT re-score, re-compute, or re-authorize.

---

## 15. Proposed Codec Ownership/Versioning

### 15.1 Codec Location

New codec in `product_intelligence/research/comparable_result_codec.py`:
- **Why research/:** Follows the `price_result_codec.py` pattern exactly.
  Codec is research-layer serialization, not persistence logic.
- **Purity:** No Django, no network, no execution, no web imports.

### 15.2 Codec API

```python
COMPARABLE_RESULT_SCHEMA_VERSION = 1

class ComparableResultCodecError(ValueError):
    """Raised when a persisted comparable payload cannot be decoded."""

def encode_comparable_result(result: ComparableResearchExecutionResult) -> dict:
    """Encode to versioned JSON-serializable dict."""

def decode_comparable_result(payload: object, *, schema_version: int) -> ComparableResearchExecutionResult:
    """Decode from persisted JSON payload. Strict, fail-closed."""
```

### 15.3 Import Direction

```
execution -> research (codec, domain, research contracts)
runs -> research (codec for encoding during persistence)
web -> research (codec for decoding during presentation)
```

This is the **exact same pattern** as `price_result_codec.py`:
- Execution encodes
- Runs stores the JSON
- Web decodes and presents
- Neither runs nor web imports execution internals

### 15.4 Versioning

- `schema_version` starts at 1
- Unknown version raises `ComparableResultCodecError`
- No best-effort migration
- Check constraint: `schema_version >= 1`

### 15.5 Corrupt/Unknown Payload

Web catches `ComparableResultCodecError` and shows a neutral "comparable
result unavailable" notice (same pattern as price snapshot decode failure).

---

## 16. Proposed Database Schema

### 16.1 Model Definition

```python
class ComparableResearchResult(models.Model):
    """One durable comparable-research execution for a ResearchRun.

    PRODUCT-INTEL.7C-PRE2.
    """

    # --- Identity ---
    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
    )

    # --- Parent relationship ---
    parent_run = models.ForeignKey(
        "ResearchRun",
        on_delete=models.CASCADE,
        related_name="comparable_research_results",
        help_text="The research run this comparable result belongs to.",
    )

    # --- Lifecycle state ---
    state = models.CharField(
        max_length=16,
        choices=STATE_CHOICES,  # PENDING, RUNNING, COMPLETED, FAILED
        default=ComparableResearchState.PENDING.value,
        editable=False,
    )

    # --- Timestamps ---
    created_at = models.DateTimeField(
        default=timezone.now,
        editable=False,
    )
    started_at = models.DateTimeField(
        null=True,
        blank=True,
        editable=False,
    )
    finished_at = models.DateTimeField(
        null=True,
        blank=True,
        editable=False,
    )

    # --- Result payload ---
    schema_version = models.PositiveSmallIntegerField(
        help_text="Codec version that produced the payload.",
    )
    payload = models.JSONField(
        help_text="Versioned codec-encoded ComparableResearchExecutionResult.",
    )

    class Meta:
        constraints = [
            models.CheckConstraint(
                condition=LIFECYCLE_SHAPE,
                name="comparable_research_state_matches_timestamps",
            ),
            models.CheckConstraint(
                condition=models.Q(schema_version__gte=1),
                name="comparable_research_schema_version_gte_1",
            ),
        ]
        indexes = [
            models.Index(fields=["parent_run", "state"]),
            models.Index(fields=["parent_run", "created_at"]),
        ]
        ordering = ["parent_run", "created_at"]
```

### 16.2 Field Specifications

| Field | Type | Null | Default | Mutable | Written by | Read by |
|-------|------|------|---------|---------|-----------|---------|
| `id` | UUIDField | No | uuid.uuid4 | No | DB/framework | All |
| `parent_run` | ForeignKey | No | — | No | Trigger | All |
| `state` | CharField(16) | No | PENDING | Via transitions | Claim/complete | All |
| `created_at` | DateTimeField | No | now() | No | Framework | All |
| `started_at` | DateTimeField | Yes | NULL | On claim | Claim | All |
| `finished_at` | DateTimeField | Yes | NULL | On terminal | Complete | All |
| `schema_version` | PositiveSmallInt | No | — | No | Encoder | Codec |
| `payload` | JSONField | No | — | No | Encoder | Codec |

### 16.3 Constraints

- **Check: lifecycle shape** — same pattern as ResearchRun
- **Check: schema_version >= 1** — same pattern as PriceIntelligenceSnapshot
- **Index: (parent_run, state)** — fast lookup for active child check
- **Index: (parent_run, created_at)** — fast lookup for latest child

### 16.4 Relationships

- `parent_run.on_delete = CASCADE` — deleting parent deletes all children
- `parent_run.related_name = 'comparable_research_results'` — plural, many-to-one
- No unique constraint on `(parent_run)` — allows retries (multiple children)

---

## 17. Proposed Web Trigger Boundary

### 17.1 Route Shape

```python
# New route:
path("research/<uuid:run_id>/comparable", views.research_comparable, name="research-comparable")
```

### 17.2 HTTP Method

POST only (`@require_POST`). Comparable research is a write operation
(creates child records, runs execution).

### 17.3 Trigger Logic

```python
@require_POST
def research_comparable(request: HttpRequest, run_id: uuid.UUID) -> HttpResponse:
    """Trigger comparable research for a completed ResearchRun.

    POST-only. Idempotent: if a non-terminal comparable result already exists,
    returns the existing result without creating a new execution.

    If the parent run is not in a terminal state, redirect to detail without action.
    """
    run = get_object_or_404(ResearchRun, pk=run_id)

    # Must be terminal (price research done)
    if not run.is_terminal:
        return redirect("research-detail", run_id=run_id)

    # Check for existing active child
    existing = run.comparable_research_results.filter(
        state__in=[PENDING.value, RUNNING.value]
    ).first()
    if existing:
        return redirect("research-detail", run_id=run_id)

    # Check for existing completed child (idempotent no-op)
    completed = run.comparable_research_results.filter(
        state=COMPLETED.value
    ).latest("created_at")
    if completed:
        return redirect("research-detail", run_id=run_id)

    # Create new PENDING child
    child = ComparableResearchResult.objects.create(
        parent_run=run,
        state=ComparableResearchState.PENDING.value,
    )

    # Execute synchronously (matches current web execution pattern)
    try:
        execute_comparable_research(str(run.id), child_id=str(child.id))
    except ClaimExecutionFailed:
        # Claim failed (concurrent trigger) — existing child has the result
        pass
    except ExecutionError:
        # Execution failed — child is in FAILED state
        pass
    except Exception:
        logger.exception("Unexpected error during comparable research")
        # Child may be in RUNNING state (crash) — manual recovery needed

    return redirect("research-detail", run_id=run_id)
```

### 17.4 Idempotent Behavior

- Already has COMPLETED child: no-op, redirect
- Already has RUNNING child: no-op, redirect
- Already has PENDING child: no-op, redirect
- Has only FAILED children: create new PENDING, execute
- No children: create new PENDING, execute

### 17.5 What Web Must NOT Do

- Perform comparable semantic work in a GET request
- Run scoring inside template/view rendering
- Construct authority descriptors
- Inject manufacturer/category/source authority
- Mutate frozen main execution semantics

---

## 18. Proposed Web Presentation Input Contract

### 18.1 What 7C Web Receives After Decoding

From the decoded `ComparableResearchExecutionResult`:

| Field | Purpose | UI Treatment |
|-------|---------|-------------|
| `authority_status` | Whether research was authoritative | "Comparable products from authoritative source" or "Comparable research: no authority match" |
| `target_mpn` | Target product identifier | Header/label |
| `target_manufacturer` | Target manufacturer | Header/label |
| `candidates[]` | Array of comparable products | Table/list |
| `candidate_mpn` | Candidate MPN | Column header |
| `scored_field_count` | Number of comparable fields | Metadata |
| `evidence_coverage` | Coverage ratio | Metadata |
| `field_assessments[]` | Per-field details | Expandable detail |
| `comparison_state` | SCORED / NOT_VERIFIED | Visual distinction |
| `target_value` | Target field value | Column |
| `candidate_value` | Candidate field value | Column |
| `field_similarity` | Per-field similarity (0-1) | **Not shown as rank/score** |

### 18.2 What Must NOT Be Implied

- "equivalent" — different field values mean different products
- "interchangeable" — no compatibility certification
- "recommended replacement" — no recommendation
- "best alternative" — no ranking
- Score ordering — candidates displayed MPN-alphabetical

### 18.3 Score Presentation

If score is shown (e.g., in field detail), it must be contextualized:
- "X of Y fields comparable" (coverage)
- "Of comparable fields, Z matched" (similarities)
- "N fields differed" (differences)
- "M fields unverified" (gaps)

**Score is never the primary sort key.** Differences are as prominent as
similarities. Unverified fields are clearly marked.

### 18.4 Unverified Fields

Fields with `TARGET_NOT_VERIFIED`, `CANDIDATE_NOT_VERIFIED`, or
`BOTH_NOT_VERIFIED` are shown with a distinct visual treatment (e.g.,
grayed-out, "unverified" label). They are NOT treated as mismatches.

---

## 19. Proposed Import Graph

### 19.1 New Allowed Imports

```
execution (new comparable orchestration module)
    -> domain (ResearchRequest, ProductIdentity, enums)
    -> research (codec, specifications, comparable_candidates, enterprise_ssd, identity)
    -> execution.specification_evidence (6C primitives)
    -> execution.specification_enrichment (6D primitives)
    -> execution.comparable_discovery (7A primitives)
    -> execution.comparable_research_authority (PRE1 primitives)
    -> research.enterprise_ssd_similarity (7B pure scoring, bridge)
    -> providers.page (PageFetcher protocol)
    -> providers.document (DocumentFetcher protocol)
    -> runs.models (ComparableResearchResult model)
    -> runs.execution_claims (complete_execution primitive — reused for child)

runs (models, __init__)
    -> research.comparable_result_codec (encoding during persistence)

web (views, presentation)
    -> runs.models (ComparableResearchResult model)
    -> research.comparable_result_codec (decoding during presentation)
    -> execution (new trigger API: execute_comparable_research, if needed)
```

### 19.2 Boundary Tests Affected

**Existing test:** `tests/domain/test_domain_boundaries.py::test_the_execution_layer_imports_no_web`
- **Status:** No change needed. The new execution module does not import web.

**Additive test needed:** New boundary test verifying:
1. `research/comparable_result_codec.py` is pure (no Django, no execution, no web)
2. New execution orchestration module does not import `execution.comparable_similarity`
   (the old 6C-only 7B executor)
3. Web does not import execution internals beyond the trigger API

### 19.3 Forbidden Imports

| Layer | Must NOT import | Reason |
|-------|----------------|--------|
| `research/comparable_result_codec.py` | Django, execution, web, providers, runs | Codec purity |
| `web/` | execution internals (scoring, discovery, authority) | Web boundary |
| New orchestration | `execution.comparable_similarity.research_and_score_enterprise_ssd_candidates` | Old 6C-only leakage |

---

## 20. Additive Test Plan

### A. Model/Persistence Invariants (runs)
- Child creates in PENDING with correct timestamps
- Child lifecycle shape constraint rejects invalid state/timestamp combos
- Child state transitions follow allowed table
- Child save() guard prevents raw state assignment
- CASCADE delete: deleting parent deletes children
- schema_version check constraint

### B. Claim Concurrency (execution)
- Two concurrent claims: only one succeeds
- Claim on RUNNING child fails
- Claim on COMPLETED child fails
- Claim on non-existent child fails
- Compare-and-set atomicity (rows_affected == 1)

### C. Duplicate Trigger Idempotency (web/execution)
- Trigger on parent with COMPLETED child: no new child created
- Trigger on parent with RUNNING child: no new child created
- Trigger on parent with PENDING child: no new child created
- Trigger on parent with only FAILED children: new child created
- Trigger on non-terminal parent: no action

### D. Failed Retry (execution)
- Failed child retry creates new PENDING child
- Old FAILED child remains in database
- New child can be claimed and executed independently

### E. Completed Child Re-Trigger (execution)
- Completed child re-trigger is no-op
- No new child created, no re-execution

### F. Parent Status Isolation (execution)
- Child COMPLETED does not change parent state
- Child FAILED does not change parent state
- Parent remains in its original terminal state

### G. Semantic Abstention Persistence (execution)
- NO_AUTHORITY_MATCH produces COMPLETED child with abstention payload
- AMBIGUOUS_AUTHORITY_MATCH produces COMPLETED child with abstention payload
- NO_REQUESTED_MPN produces COMPLETED child with abstention payload
- Payload contains correct authority_status

### H. Transient Fetch Failure Semantics (execution)
- Page fetch failure produces FAILED child (not abstention)
- Child state is FAILED, not COMPLETED
- Fetch failure details in payload (bounded, not raw exception)

### I. Codec Round-Trip (research)
- Encode then decode produces equal result
- Decimal values preserved as strings
- Enum values round-trip correctly
- All candidate field assessments preserved

### J. Corrupt/Unknown Codec Version (research)
- Unknown schema_version raises ComparableResultCodecError
- Corrupt payload raises ComparableResultCodecError
- Extra keys in payload rejected
- Missing keys in payload rejected

### K. Web Read-Side Import Boundary (web)
- Web decodes payload without importing execution internals
- Web does not construct authority descriptors
- Web does not call scoring functions
- Web does not call discovery functions

### L. Web Does Not Score/Research (web)
- research_detail GET does not trigger execution
- Template rendering does not call scoring
- Template rendering does not call discovery

### M. No Ranking Policy (web)
- Candidates displayed MPN-alphabetical
- No reordering by similarity score in presentation layer
- Score not used as sort key

### N. Differences as Prominent as Similarities (web)
- Field assessments with differences shown with equal visual weight
- Not collapsed or hidden

### O. Unverified Fields Preserved (web/codec)
- Unverified fields encoded in payload
- Unverified fields decoded correctly
- Unverified fields shown in presentation

### P. Exact Frozen-Chain Integration (execution)
- PRE1 authority context acquisition
- 6C target specification extraction
- 7A candidate discovery
- 6D target enrichment
- compose 6C+6D target
- Per-candidate: 6C -> 6D -> compose
- 7B pure scoring per candidate
- Authority abstention paths

### Q. No Fallback to Old 6C-Only 7B Executor (execution)
- New orchestration does NOT call `research_and_score_enterprise_ssd_candidates()`
- Mock test: if old executor is called, test fails
- Import boundary: new orchestration does not import old executor module

### R. No Test Deletion/Skip/Xfail/Deselect (meta)
- No existing tests deleted
- No existing tests skipped
- No existing tests xfailed
- No existing tests deselected

### Test Categories

| Category | Tests |
|----------|-------|
| Pure research/unit | G, I, J, O (codec, abstention), P (chain verification), Q |
| Execution | B, D, E, F, G, H, P, Q |
| Runs/persistence | A, C |
| Web | C, K, L, M, N, O |
| Boundary/integration | K, L, Q |

---

## 21. Exact Production Files Likely to Be Added/Modified

### New Files (all additive, no frozen file modified)

1. **`product_intelligence/runs/models.py`** — ADD `ComparableResearchResult` model class
   (append to existing file, do not modify existing classes)

2. **`product_intelligence/runs/migrations/0007_comparable_research_result.py`** — New migration

3. **`product_intelligence/runs/comparable_execution_claims.py`** — NEW file
   Child claim/complete/retry primitives (mirrors `execution_claims.py` pattern for child)

4. **`product_intelligence/research/comparable_result_codec.py`** — NEW file
   Codec for ComparableResearchExecutionResult (follows `price_result_codec.py` pattern)

5. **`product_intelligence/execution/comparable_research_orchestration.py`** — NEW file
   New post-6D orchestration: PRE1 -> 6C -> 7A -> 6D -> compose -> 7B pure

6. **`product_intelligence/domain/enums.py`** — ADD `ComparableResearchState` enum
   (append to existing file, do not modify existing enums)

7. **`product_intelligence/web/views.py`** — ADD `research_comparable()` view function
   (append, do not modify existing views)

8. **`product_intelligence/web/urls.py`** — ADD comparable route
   (append to urlpatterns, do not modify existing routes)

9. **`product_intelligence/web/presentation.py`** — ADD comparable presentation builders
   (append, do not modify existing presentation functions)

### Modified `__init__.py` Files (additive exports only)

10. **`product_intelligence/runs/__init__.py`** — ADD comparable child exports
    (append to __all__, add __getattr__ branches)

11. **`product_intelligence/research/__init__.py`** — ADD codec exports
    (append to __all__)

### No Modified Frozen Files

The following files must NOT be modified:
- `product_intelligence/execution/comparable_similarity.py` (frozen 7B execution)
- `product_intelligence/research/enterprise_ssd_similarity.py` (frozen 7B pure)
- `product_intelligence/execution/comparable_discovery.py` (frozen 7A)
- `product_intelligence/execution/specification_evidence.py` (frozen 6C)
- `product_intelligence/execution/specification_enrichment.py` (frozen 6D)
- `product_intelligence/execution/comparable_research_authority.py` (frozen PRE1)
- `product_intelligence/runs/execution_claims.py` (frozen parent claims)
- `product_intelligence/domain/enums.py` — `ResearchRunState` enum (frozen)
- `product_intelligence/runs/models.py` — existing model classes (frozen)

---

## 22. Exact Frozen Files That MUST Remain Untouched

### Frozen Phase Implementations

| File | Phase | Why frozen |
|------|-------|-----------|
| `execution/orchestration.py` | 4C-B | Main execution pipeline |
| `execution/comparable_similarity.py` | 7B | 6C-only high-level executor |
| `research/enterprise_ssd_similarity.py` | 7B | Pure scoring primitives |
| `execution/comparable_discovery.py` | 7A | Candidate discovery |
| `execution/specification_evidence.py` | 6C | Specification extraction |
| `execution/specification_enrichment.py` | 6D | Datasheet enrichment |
| `execution/comparable_research_authority.py` | PRE1 | Authority context |
| `research/price_result_codec.py` | 4B | Price result codec |
| `research/enterprise_ssd.py` | 6B | Enterprise SSD schema |
| `research/enterprise_ssd_extraction.py` | 6C | Extraction primitives |
| `research/specifications.py` | 6A | Specification framework |
| `research/comparable_candidates.py` | 7A | Candidate contracts |
| `domain/enums.py` | 0A | ResearchRunState vocabulary |
| `domain/models.py` | 0A | ProductIdentity, ResearchRequest |

### Frozen Persistence Contracts

| File | Phase | Why frozen |
|------|-------|-----------|
| `runs/models.py` (existing classes) | 1A/4B/4C | ResearchRun, PriceIntelligenceSnapshot, ExecutionEvidenceRecord, AiAssistedReviewCandidate |
| `runs/execution_claims.py` | 4C-A | Parent claim semantics |
| `runs/errors.py` | 1A | Parent lifecycle errors |

### Frozen Web Contracts

| File | Phase | Why frozen |
|------|-------|-----------|
| `web/views.py` (existing functions) | 1B/4B/4C | research_new, research_detail, research_retry, research_review |
| `web/urls.py` (existing routes) | 1B | Existing URL patterns |
| `web/presentation.py` (existing functions) | 4B | Price report presentation |

### Frozen Boundary Tests

| File | Purpose | Why frozen |
|------|---------|-----------|
| `tests/domain/test_domain_boundaries.py` | Import purity guards | Existing boundary invariants |

---

## 23. Open Questions / Blockers

### 23.1 No Blockers Identified

All architecture decisions are derivable from the existing codebase. No stop
conditions are triggered:

- Safe child lifecycle does NOT weaken existing ResearchRun semantics
- Post-6D scoring does NOT require modifying frozen 7B
- Candidate profile reuse does NOT leak old 6C-only scores
- Web does NOT need to own authority/research semantics
- Durable claim/retry mechanism can be added without changing frozen contracts
- Persisted semantics CAN be decoded without importing execution internals
- NOT_APPLICABLE does NOT require manufacturer/category guessing
- Implementation does NOT require changing existing expected results

### 23.2 Open Questions (for 7C implementation, not PRE2)

1. **Stale RUNNING recovery:** Should a future phase add automatic
   detection/recovery of stuck RUNNING child records? (Not required for 7C.)

2. **Permission model:** Should comparable research trigger require the same
   caller/ownership checks as the main research execution? (Currently no
   auth exists — matches parent.)

3. **Multiple retries:** Should there be a maximum number of child retry
   records per parent? (Current design: no maximum, matches parent pattern.)

4. **Display of historical children:** Should the web report show all child
   attempts or only the latest? (Recommendation: latest by default, history
   available via expanded view.)

---

## 24. Git Status Before/After

### Before Investigation
```
$ git status --short
(clean — no output)
```

### After Investigation
```
$ git status --short
(clean — no output)
```

No files were modified. This was a read-only investigation.

---

## 25. Collection/Test Evidence Gathered

### Files Inspected (read-only)

**Core architecture:**
- `product_intelligence/runs/models.py` — ResearchRun, PriceIntelligenceSnapshot,
  ExecutionEvidenceRecord, AiAssistedReviewCandidate
- `product_intelligence/runs/execution_claims.py` — claim_execution, complete_execution, retry_run
- `product_intelligence/runs/errors.py` — lifecycle error types
- `product_intelligence/runs/__init__.py` — export map
- `product_intelligence/domain/enums.py` — ResearchRunState, other vocabularies
- `product_intelligence/domain/models.py` — ProductIdentity, ResearchRequest
- `product_intelligence/execution/__init__.py` — export map
- `product_intelligence/execution/orchestration.py` — execute_research_run
- `product_intelligence/execution/comparable_discovery.py` — 7A pipeline
- `product_intelligence/execution/comparable_similarity.py` — 7B execution pipeline
- `product_intelligence/execution/comparable_research_authority.py` — PRE1 authority
- `product_intelligence/execution/specification_evidence.py` — 6C pipeline
- `product_intelligence/execution/specification_enrichment.py` — 6D pipeline
- `product_intelligence/research/__init__.py` — export map
- `product_intelligence/research/price_result_codec.py` — price result codec
- `product_intelligence/research/enterprise_ssd_similarity.py` — 7B pure scoring
- `product_intelligence/research/specifications.py` — 6A framework
- `product_intelligence/research/comparable_candidates.py` — 7A contracts
- `product_intelligence/research/enterprise_ssd.py` — 6B schema
- `product_intelligence/web/views.py` — all views
- `product_intelligence/web/urls.py` — all routes
- `product_intelligence/web/presentation.py` — presentation helpers
- `tests/domain/test_domain_boundaries.py` — boundary guard tests

**Migration inventory:**
- `runs/migrations/0001_initial.py` through `0006_add_ai_assisted_review_candidate.py`

### Test Baseline (PRE1 committed)

- PRE1-specific tests: 87
- Full collection: 3440
- Observed clean: 3440 passed
- Observed flaky: 3429 passed, 11 known Windows/Python 3.14 subprocess failures
- 0 unexpected failures, 0 skipped, 0 xfailed, 0 deselected

---

## 26. Recommendation: GO to Bounded Implementation

**Verdict: GO**

All 26 investigation sections are complete. The recommended architecture is:

1. **New child model** `ComparableResearchResult` in `runs/models.py`
   (ForeignKey to ResearchRun, own lifecycle, versioned JSON payload)

2. **New codec** in `research/comparable_result_codec.py`
   (follows price_result_codec.py pattern exactly)

3. **New orchestration** in `execution/comparable_research_orchestration.py`
   (POST-6D chain: PRE1 -> 6C -> 7A -> 6D -> compose -> 7B pure)
   Does NOT call the old 6C-only `research_and_score_enterprise_ssd_candidates()`

4. **New child claim primitives** in `runs/comparable_execution_claims.py`
   (mirrors parent execution_claims.py pattern)

5. **New web trigger** `research_comparable` POST route
   (idempotent, synchronous, matches existing web execution pattern)

6. **New web presentation** for comparable results
   (MPN-alphabetical ordering, no ranking, differences prominent)

**Zero frozen files modified.** All additive. All following existing patterns.

The 6C-only 7B leakage risk is mitigated by:
- New orchestration does NOT import or call `research_and_score_enterprise_ssd_candidates()`
- Pure 7B scoring functions are source-agnostic and safe to reuse
- Boundary tests verify import direction
- Payload contains 6D evidence provenance

No stop conditions triggered. PRE2 architecture closure is complete.
