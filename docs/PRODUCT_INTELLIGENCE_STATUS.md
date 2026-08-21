# Product Intelligence — Current Status

## Completed phase

**PRODUCT-INTEL.4B — Price Intelligence web report** (2026-08-20).

Implementation complete; freeze validation pending.

The durable report at `/research/<uuid>` now reads an optional
`PriceIntelligenceSnapshot` and renders the full price intelligence
result: buckets, contributing evidence, and excluded listings.
It starts nothing, transitions nothing, and writes no timestamp.
A corrupt payload or request-provenance mismatch shows the snapshot
as unavailable — it never renders partially-decoded data as verified.

### What is connected

* The codec round-trips `PriceAggregationResult` through versioned opaque
  JSON in `PriceIntelligenceSnapshot`.
* The report view decodes, validates provenance, and presents the result.
* The decoder fails closed: corrupt payloads, unknown schema versions,
  and provenance mismatches all show the snapshot as unavailable.
* External text from listing observations is HTML-escaped.
* The report is read-only: multiple GET requests change no state.

### What is NOT connected

* **Research execution does not exist.** A submitted run stays `CREATED`.
  Nothing runs automatically, nothing is queued.
* **No orchestration layer.** Phases 3A–4A produce a result manually; no
  code connects search → fetch → extract → normalize → match → aggregate.
  That is phase 4C (`execution/`).
* **No LLM.** The LLM boundary exists as documentation only (§14).
* **No launcher integration.** FoxPro/SAP/ERP launchers are not built.

### Next phase

**PRODUCT-INTEL.4C — Research orchestration.**

Create the `execution/` application layer that coordinates one `ResearchRun`
through provider I/O and the deterministic research primitives of phases 2A–4A.
**Do not start until 4B freeze validation is green.**

## Implementation snapshot

| Component | Package | Status |
| --- | --- | --- |
| Domain contracts + vocabularies | `domain/` | Implemented |
| Evaluation corpus + loader | `evaluation/` | Implemented |
| Persisted run lifecycle | `runs/` | Implemented (ResearchRun) |
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
| Research orchestration | `execution/` | **Not started (4C)** |
| LLM boundary | docs only | Planned |
| FoxPro/SAP launcher | — | Planned (5A/5B) |

## Validation baseline

* 4B implementation is present.
* Pi-session focused/non-subprocess validation is green.
* Pi full-session: 1433 passed, 7 failed (across 6 subprocess-boundary test
  functions), 39 subtests passed.
* Pi full-session subprocess-boundary failures remain.
* Independent ordinary-terminal freeze validation is pending.
* `python manage.py check` — 0 issues
* `python manage.py makemigrations --check --dry-run` — no changes detected
* Architecture guard tests enforce layer boundaries
