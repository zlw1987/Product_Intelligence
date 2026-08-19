# Product Intelligence — Current Status

Volatile current-state document. Updated on ordinary phase completion.
For the full architectural rationale and phase specifications, see
[PRODUCT_INTELLIGENCE_PLAN.md](PRODUCT_INTELLIGENCE_PLAN.md).

## Current completed phase

**PRODUCT-INTEL.4A — Price aggregation.**

## Next planned phase

**PRODUCT-INTEL.4B — Price Intelligence web report.** Do not start it unless
asked.

## Implemented primitives (through 4A)

- **0A / 0A-FU1** — Architecture, domain contracts, and contract-level corrections.
- **0B** — Evaluation corpus (19 cases: 5 real, 14 synthetic), schema, validation, loader.
- **1A / 1A-FU1** — Persisted `ResearchRun` lifecycle with state machine, timestamps,
  and DB check constraint.
- **1B** — Standalone web shell: form at `/research/new`, report at `/research/<uuid>`,
  creates a `CREATED` run, executes nothing.
- **2A / 2A-FU1** — Deterministic part-number comparison (`identity.py`):
  `EXACT`, `NORMALIZED_EXACT`, `UNKNOWN`. Structure-preserving normalization.
- **2B** — Search-provider boundary (`search.py`): `SearchQuery`, `SearchResult`,
  `SearchResponse`, `SearchProvider` protocol, one exception. Stdlib contracts only.
- **2C** — Serper adapter (`serper.py`): first real `SearchProvider`, ordinary Google
  Search, offline fixture-based tests. Not wired into anything.
- **3A** — Page fetch boundary (`page.py`, `http_page.py`): bounded, safe, stdlib.
  Raw listing extraction (`listings.py`, `extraction.py`): JSON-LD + meta, all text,
  five recorded real-page fixtures.
- **3B** — Listing normalization (`normalization.py`): price to `Decimal` or abstain,
  currency, availability, condition, seller. No identity decision, no aggregate.
- **3C** — MPN matching and rejection (`matching.py`): explicit MPN field acceptance,
  SKU/title rejection, `PARTIAL` refused, `mpn:` wrapper cleanup.
- **4A** — Price aggregation (`aggregation.py`): eligibility with precedence,
  currency+condition buckets, computed statistics, derived confidence.

## Not yet connected

- No end-to-end research execution.
- No orchestration (query generation, candidate URL selection, pipeline invocation).
- No automatic `ResearchRun` execution — a submitted run stays `CREATED`.
- No web price intelligence presentation — the report shell is empty.
- No global market-price selection or cross-bucket policy.
- No comparable-product system.
- No runtime LLM integration.
- No structured intake API (5A).
- No FoxPro launcher integration (5B).
- No SAP integration.

## Current validation baseline

As frozen for 4A: **1305 passed, 39 subtests passed** from the ordinary
repository test run.
