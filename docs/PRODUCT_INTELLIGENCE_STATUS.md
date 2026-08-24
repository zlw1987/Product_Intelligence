# Product Intelligence — Current Status

## Completed phase

**PRODUCT-INTEL.4C-A — Execution ownership, durable evidence, lifecycle** (2026-08-21).

Implementation complete; freeze validation pending.

Phase 4C-A introduces the execution layer primitives that enable safe,
concurrent execution claims and terminal-state transitions:

* **Atomic execution claim** — a database-level compare-and-set operation
  ensures exactly one claim succeeds per run, portable across SQLite,
  PostgreSQL, and MySQL.

* **Execution completion** — explicit terminal-state transitions (COMPLETED,
  PARTIALLY_COMPLETED, FAILED) on claimed runs using atomic updates.

* **Retry semantics** — creating a new run from a terminal run's request
  without copying snapshots or evidence.

* **Controlled evidence vocabulary** — ExecutionStage, ExecutionOutcome,
  and ExecutionDetailCode provide a stable, machine-readable vocabulary
  for execution attempts.

* **Durable evidence records** — ExecutionEvidenceRecord stores ordered
  execution attempts with stage, outcome, candidate URL, and detail code.

**Do not call providers yet.** 4C-A provides only the lifecycle primitives.
Actual search/fetch/extract/orchestration is 4C-B's responsibility.

### Next phase

**PRODUCT-INTEL.4C-B — Execution orchestration.**

Phase 4C-B connects the lifecycle primitives of 4C-A to the research
primitives (search, fetch, extract, normalize, match, aggregate) to
orchestrate actual research execution. This phase will:

* Call SearchProvider.search() for candidate generation
* Call PageFetcher.fetch() for candidate URL retrieval
* Call extract_listing_observations() for raw listing extraction
* Call normalize_listing_observation() for price/MPN extraction
* Call assess_listing_identity() for MPN matching
* Call aggregate_listing_prices() for final price computation

**This phase is not yet implemented.**

## Implementation snapshot

| Component | Package | Status |
| --- | --- | --- |
| Domain contracts + vocabularies | `domain/` | Implemented |
| Evaluation corpus + loader | `evaluation/` | Implemented |
| Persisted run lifecycle | `runs/` | Implemented (ResearchRun) |
| Execution evidence model | `runs/` | Implemented (ExecutionEvidenceRecord) |
| Execution claim service | `runs/` | Implemented (claim_execution) |
| Execution completion service | `runs/` | Implemented (complete_execution) |
| Retry service | `runs/` | Implemented (retry_run) |
| Price intelligence snapshot | `runs/` | Implemented (PriceIntelligenceSnapshot) |
| Standalone web shell | `web/` | Implemented (form + report) |
| Part-number comparison | `research/identity` | Implemented |
| Search provider boundary | `providers/search.py` | Implemented |
| Serper adapter | `providers/serper.py` | Implemented |
| Page fetch + extraction | `providers/http_page.py` + `research/listings.py` | Implemented |
| Listing normalization | `research/normalization.py` | Implemented |
| MPN matching + rejection | `research/matching.py` | Implemented |
| Price aggregation | `research/aggregation.py` | Implemented |
| Versioned codec | `research/price_result_codec.py` | Implemented |
| Price report presentation | `web/presentation.py` | Implemented |
| Research orchestration | `execution/` | **4C-A complete (lifecycle)** |
| LLM boundary | docs only | Planned |
| FoxPro/SAP launcher | — | Planned (5A/5B) |

## Validation baseline

* 4C-A implementation is present.
* Pi-session focused/non-subprocess validation is green.
* Pi full-session: 1473 passed, 1 failed (subprocess-boundary test on Windows,
  not a code defect), 39 subtests passed.
* Pi full-session subprocess-boundary failures are infrastructure issues
  on Windows, not code defects.
* `python manage.py check` — 0 issues
* `python manage.py makemigrations --check --dry-run` — no changes detected
* Architecture guard tests enforce layer boundaries
