# Product Intelligence — Current Status

## Current state

**PRODUCT-INTEL.PILOT-UX — Corrective review in progress.**

This phase is under corrective review. The previous implementation contained
correctness defects in the semantic evaluator and corpus. A corrective pass
is addressing:

1. **Evaluator mathematics fixed**: DecisionMetrics.accuracy no longer
   double-counts TN values. Perfect prediction yields accuracy = 1.0.
2. **Invalid/missing output handling**: Missing responses are NOT counted as
   NO_MATCH predictions. They reduce valid_output_rate but don't affect
   confusion matrix or accuracy.
3. **Safety cost semantics corrected**: False MATCH now correctly increases
   safety_cost (cost = 10), not decreases it.
4. **Per-class metrics implemented**: All SemanticCaseClass values now have
   proper metrics, not just TITLE_EXACT_MPN.
5. **Corpus corrected**:
   - SMQ-0001 now uses TITLE_TEXT evidence (not EXPLICIT_MPN_FIELD)
   - SMQ-0004 is now the explicit conflict safety case with EXPLICIT_MPN_FIELD
   - SMQ-0200-0203 filler cases removed
   - New MATCH cases added to meet distribution requirements
6. **Raw-output strict parser implemented**: Parses raw model output with
   strict rules (no prose, no markdown fences, no arrays).
7. **Versioned prompt template implemented**: Shared, model-independent prompt
   with SEMANTIC_PROMPT_VERSION = "1.0".
8. **Export/import workflow implemented**: corpus_to_jsonl and
   import_results_from_jsonl functions.

**No production LLM matcher exists.** Semantic qualification harness is
a candidate, but no model has been evaluated yet.

## Project facts (already delivered outside repo)

- FoxPro launcher: Manually integrated outside repository. Client code
  maintained in the existing Visual FoxPro sales-order application.
  Server-side GET prefill contract is implemented. Localhost UAT passed.
- 4C-B-FU corrective: Exact structural duplicate ListingObservation
  deduplication implemented in `execution/orchestration._deduplicate_exact_observations`.

## Next delivery priority

**PRODUCT-INTEL.PILOT-UX — Corrective review completion.**

After corrective pass is reviewed:
- Semantic qualification harness validated
- Human checkbox selection design recorded for future implementation

**PRODUCT-INTEL.5B — FoxPro Launcher** (client pending outside repo).

## Phase ownership

| Phase | Description | Status |
| --- | --- | --- |
| 4C-A | Execution ownership/lifecycle/evidence primitives | Implemented (frozen) |
| 4C-B | Backend research execution | Implemented (frozen) |
| 4C-B-FU | Exact duplicate deduplication | Implemented (frozen) |
| 4C-C | Web execution/retry integration | **Implemented (frozen)** |
| 5A | Structured external API | Not implemented |
| 5B | FoxPro launcher | Server-side implemented; client pending |
| PILOT-UX | Pilot UX polish + semantic qualification | **Corrective review** |
| SAP | SAP launcher integration | Future |

## Implementation snapshot

| Component | Package | Status |
| --- | --- | --- |
| Domain contracts + vocabularies | `domain/` | Implemented |
| Evaluation corpus + loader | `evaluation/` | Implemented |
| Semantic match corpus + evaluator | `evaluation/semantic/` | **Implemented** |
| Semantic match prompt template | `evaluation/semantic/prompt.py` | **Implemented** |
| Semantic match export/import | `evaluation/semantic/` | **Implemented** |
| Semantic match transport | `evaluation/semantic/transport.py` | **Implemented** |
| Semantic match model catalog | `evaluation/semantic/model_catalog.py` | **Implemented** |
| Semantic match benchmark runner | `evaluation/semantic/runner.py` | **Implemented** |
| Semantic match CLI | `evaluation/semantic/cli.py` | **Implemented** |
| Semantic match comparison | `evaluation/semantic/comparison.py` | **Implemented** |
| Semantic match tests | `tests/evaluation/semantic/` | **Implemented** |
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
| Web execution wiring | `web/` | **Implemented (frozen)** |
| Structured API | — | 5A (not implemented) |
| FoxPro launcher | — | Server-side implemented; client pending |
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
python -m pytest tests/evaluation/semantic -q
python manage.py check
python manage.py makemigrations --check --dry-run
```

Note: Two subprocess-based tests in `tests/research/` fail on Windows with
Python 3.14 due to a known `os.duplicatehandle` issue. This is a platform/version
problem, not a code defect.

## Next delivery priority

**PRODUCT-INTEL.PILOT-UX — Corrective review completion.**

After corrective pass:
- Human checkbox selection design recorded for future implementation after
  semantic qualification harness is trustworthy

**PRODUCT-INTEL.5B — FoxPro Launcher** (client pending outside repo).

## Semantic qualification harness

**APPROVED / FROZEN**

The semantic qualification corpus, prompt v1.0, evaluator mathematics,
qualification thresholds, expected decisions, and safety gates are now
APPROVED AND FROZEN.

Do NOT modify:
- evaluation/semantic_corpus/cases.json truth labels or case contents
- SEMANTIC_PROMPT_VERSION = "1.0"
- semantic system/user prompt semantics
- semantic evaluator formulas
- qualification gates
- production research/matching.py
- production aggregation
- production execution

## Model qualification runner

**IMPLEMENTATION CANDIDATE**

Semantic qualification harness infrastructure is now implemented:

* transport.py - Abstract transport interface + OpenAI-compatible HTTP
* model_catalog.py - Explicit model catalog (8 primary + 1 smoke + 3 skip)
* runner.py - Benchmark runner with durable artifacts
* cli.py - CLI for list-models, run, evaluate, compare
* comparison.py - Offline comparison utility

All tests use fake transports / recorded responses. No live network calls.

No model results yet. No production semantic matcher selected.

## Known issues / debt

- Semantic match qualification: harness candidate implemented; no model results yet
- Human checkbox selection for user-curated summary: design recorded for future
  implementation after semantic qualification harness is trustworthy