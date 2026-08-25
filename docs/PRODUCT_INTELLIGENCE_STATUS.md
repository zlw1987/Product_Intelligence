# Product Intelligence — Current Status

## Completed phase

**PRODUCT-INTEL.4C-B — Research Execution Orchestration** (frozen).

Implementation complete. This phase is now frozen and must not be modified
unless explicitly required by a corrective follow-up.

## Next delivery priority

**PRODUCT-INTEL.4C-C — Web Execution/Retry Integration** (corrective review).

Web layer wiring is implemented but pending final review. The web layer
synchronously triggers research execution via the public `execute_research_run`
API. POST creates a run, executes synchronously, and redirects to the report.
Execution failures transition the run to FAILED. Retry button creates a new
run and re-executes.

**PRODUCT-INTEL.5B — FoxPro Launcher** (pending manual insertion + UAT).

Server-side GET prefill contract is implemented. The FoxPro client code
will be written manually outside this repository by the project lead.

**Customer Pilot v0.1: NOT YET DELIVERED.**

Remaining gates:
- 4C-C final review
- FoxPro manual integration (outside this repo)
- One explicit live smoke test

## Phase ownership

| Phase | Description | Status |
| --- | --- | --- |
| 4C-A | Execution ownership/lifecycle/evidence primitives | Implemented (frozen) |
| 4C-B | Backend research execution | Implemented (frozen) |
| 4C-C | Web execution/retry integration | **Implementation candidate** |
| 5A | Structured external API | Not implemented |
| 5B | FoxPro launcher | Server-side implemented; client pending |
| SAP | SAP launcher integration | Future |

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
| Standalone web shell | `web/` | Implemented |
| Part-number comparison | `research/identity` | Implemented |
| Search provider boundary | `providers/search.py` | Implemented |
| Serper adapter | `providers/serper.py` | Implemented |
| Page fetch + extraction | `providers/http_page.py` + `research/listings.py` | Implemented |
| Listing normalization | `research/normalization.py` | Implemented |
| MPN matching + rejection | `research/matching.py` | Implemented |
| Price aggregation | `research/aggregation.py` | Implemented |
| Versioned codec | `research/price_result_codec.py` | Implemented |
| Price report presentation | `web/presentation.py` | Implemented |
| Research orchestration | `execution/` | **Implemented (frozen)** |
| Web execution wiring | `web/` | **4C-C implementation candidate** |
| Structured API | — | 5A (not implemented) |
| SAP launcher | — | Future |

## Web layer architecture

The web layer may import only the public execution API:

```
web  ->  product_intelligence.execution  (execute_research_run, ExecutionError)
web  ->  product_intelligence.runs  (ClaimExecutionFailed, retry_run, ResearchRun)
```

The web layer MUST NOT import:
- `product_intelligence.execution.orchestration` (or any execution submodule)
- `product_intelligence.execution` (bare module import)
- `product_intelligence.providers` (or any provider submodule)
- `product_intelligence.runs.execution_claims` (internal)

## FoxPro ownership

FoxPro source code is NOT maintained in this repository. This repository
owns only the launcher-facing HTTP intake contract:

```
GET /research/new?mpn=<encoded>&description=<encoded>
```

The project lead maintains the FoxPro client code manually in the existing
Visual FoxPro sales-order application.

## Validation results

Run:

```bash
python -m pytest tests/web -q
python -m pytest tests/execution -q
python manage.py check
python manage.py makemigrations --check --dry-run
```

Full suite and architecture guard results will be reported after corrective
pass completes.

## Known issues / debt

- 4C-B-FU corrective: exact structural duplicate ListingObservation deduplication — IMPLEMENTED. Real UAT defect: a page publishing five identical Product/Offer nodes caused AGGREGATE FAILED with ValueError from 4A's `_refuse_duplicate_assessments`. Fix: deduplicate exact structural duplicates at extraction boundary before normalization/matching, in `execution/orchestration._deduplicate_exact_observations`. 4A is unchanged.
- 4C-C corrective review pending
- FoxPro client integration pending (maintained outside repo)
- Customer Pilot v0.1 delivery pending final review + smoke test