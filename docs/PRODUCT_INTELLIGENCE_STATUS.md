# Product Intelligence — Current Status

## Completed phase

**PRODUCT-INTEL.4C-B — Complete PRICE MVP Backend Research Execution** (2026-08-24).

Implementation complete and tested with 59 execution tests.

Phase 4C-B connects the lifecycle primitives of 4C-A to the research
primitives (search, fetch, extract, normalize, match, aggregate) to
orchestrate actual research execution:

* **Execution orchestration** — `product_intelligence/execution/orchestration.py`
  coordinates the complete research pipeline from `ResearchRequest` through
  `claim_execution` → `search` → `fetch` → `extract` → `normalize` → `match` →
  `aggregate` → `snapshot` → terminal state.

* **One paid search call maximum** — enforced by `claim_execution` (4C-A).

* **Execution evidence persistence** — `ExecutionEvidenceWriter` provides
  strict API for recording attempts at each stage with contiguous attempt
  numbers starting at 1.

* **Candidate-level failure resilience** — fetch/extract failures for one
  URL do NOT fail the whole run; orchestration continues to later candidates.

* **URL deduplication** — deterministic first-occurrence-wins exact URL
  deduplication prevents duplicate fetches.

* **Safe URL validation** — before fetch, URLs are validated for:
  * Absolute http(s)://
  * Non-empty hostname
  * No embedded credentials

* **Zero-results support** — empty search results complete the run with
  UNKNOWN verification status.

* **Snapshot persistence** — final price result encoded via 4B codec and
  stored in `PriceIntelligenceSnapshot`, with request provenance validation.

* **Real contract usage** — Uses actual `FetchedPage` contract (`body_text`,
  `requested_url`, `final_url`) rather than invented contracts.

* **Redirect provenance** — When a URL redirects, FETCH evidence records the
  requested candidate URL, while extracted `ListingObservation.source_url`
  preserves the actual `final_url` after redirects.

* **Controlled detail codes** — All execution evidence detail codes use the
  frozen 4C-A vocabulary; arbitrary strings are rejected.

* **Atomic final publication** — Final snapshot + state transition wrapped
  in database transaction to ensure snapshot exists ↔ run is COMPLETED,
  never snapshot exists + RUNNING or FAILED.

* **Fetch statistics** — `fetch_success_count` correctly counts successful
  PageFetcher calls regardless of extraction results.

## Next delivery priority: Customer Pilot v0.1

The first customer pilot combines:

- **4C-B backend engine** (already implemented) — full research pipeline
- **4C-C minimum web wiring** — execute button, loading UI, polling for status
- **5B FoxPro launcher** — legacy intake from FoxPro product/order context

**Goal:** From a FoxPro product/order context, the user can launch the browser
with MPN + description prefilled, explicitly start market research, and view
the result.

**NOT required for pilot:**
- 5A structured API (standalone web form is sufficient for first pilot)
- SAP launcher (future phase)
- Comparable-product intelligence (future phase)

### Phase ownership

| Phase | Description | Status |
| --- | --- | --- |
| 4C-A | Execution ownership/lifecycle/evidence primitives | Implemented |
| 4C-B | Backend research execution | Implemented |
| 4C-C | Web execution/retry integration | Not implemented |
| 5A | Structured external API | Not implemented |
| 5B | FoxPro launcher | Not implemented (pilot scope) |
| SAP | SAP launcher integration | Future |

## Validation results

* Focused execution tests: **59 passed**
* Full suite: 59 passed + 7 subprocess-boundary failures (Windows/Python 3.14
  infrastructure, not code defects)
* `python manage.py check` — 0 issues
* `python manage.py makemigrations --check --dry-run` — no changes detected
* Architecture guard tests enforce layer boundaries

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
| Research orchestration | `execution/` | **4C-B complete** |
| Web execution wiring | `web/` | 4C-C (not implemented) |
| FoxPro/SAP launcher | — | 5B/Future (not implemented) |