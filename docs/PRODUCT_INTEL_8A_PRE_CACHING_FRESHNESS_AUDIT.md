# PRODUCT-INTEL.8A-PRE — Caching & Freshness Architecture Audit

**Status:** DELIVERED (read-only / design-first audit). This document records the
caching/freshness architecture investigation. It authorizes NO implementation,
approves NO TTL values, and changes NO production code, test, model, migration,
or frozen contract.

**Authoritative starting SHA:** `55d1879a03da3dc6163a28c9524b5ef0396b76b3`
**Audit basis:** actual production code at that SHA (all citations below), plus
`CLAUDE.md`, `docs/PRODUCT_INTELLIGENCE_PLAN.md` (§13–§18, §22, §26, decision log),
`docs/PRODUCT_INTELLIGENCE_STATUS.md`.

---

## 0. Governance / read-only evidence

- `git rev-parse HEAD` → `55d1879a03da3dc6163a28c9524b5ef0396b76b3` (matches the
  authoritative starting SHA).
- `git diff --stat` → **empty** (zero tracked-file changes).
- `git diff --name-status` → **empty**.
- `git status --short` → only **pre-existing untracked** evaluation artifacts
  (present before the audit began): `b2_b3_full.txt`, `b2_b3_full_junit.xml`,
  `nemotron_full_evaluation.json`, `nemotron_full_manifest.json`,
  `nemotron_full_responses.jsonl`, `qwen38_run1_responses.jsonl`,
  `qwen38_run2_responses.jsonl`, plus this audit document
  (`docs/PRODUCT_INTEL_8A_PRE_CACHING_FRESHNESS_AUDIT.md`, newly written,
  untracked, **not committed**).
- Production files changed: **NONE**.
- Tests changed/deleted/renamed/skipped/xfail/deselected: **NONE** (zero test
  edits; no markers added or removed).
- Migration / model / schema changed: **NONE** (`python manage.py makemigrations
  --check --dry-run` reports "No changes detected" at this SHA).
- Frozen authority invariants requiring modification: **NONE** (this audit only
  reads them; the proposed next slice in §8 touches no frozen contract).
- Implementation diff for the audit: **ZERO**, as required.

### Baseline test evidence (at the authoritative SHA, before and after the audit)

Full suite: `python -m pytest` → **5633 collected; 5623 passed; 10 failed;
0 errors; 0 skipped; 0 xfailed; 0 xpassed; 0 deselected** (progress reached
100% in both full runs; the final summary line was truncated by the known
Windows console/pipe behavior, so counts were derived from the progress
characters: 5633).

All 10 failures are inside the documented, fixed **Windows/Python-3.14
subprocess-boundary flake allowlist** (STATUS "Known issues / debt": "This
Windows / Python 3.14 workstation has a fixed eleven-node subprocess-boundary
flake allowlist ... No node outside the fixed eleven-node allowlist fails").
Observed signature in every failure:
`OSError: [WinError 6] The handle is invalid` at
`subprocess.py:1431` (`_winapi.DuplicateHandle`). The union of failing nodes
across the two full runs is exactly 11 clean-interpreter import-boundary nodes
(e.g. `tests/domain/test_domain_boundaries.py::test_domain_imports_without_django_network_or_llm_dependencies`,
`tests/providers/test_provider_boundaries.py::{test_importing_the_provider_boundary_pulls_in_no_third_party_dependency,
test_importing_the_page_boundary_pulls_in_no_third_party_dependency,
test_http_pdf_imports_no_third_party_dependency}`,
`tests/research/test_*_boundaries.py::{...no_third_party...}` nodes,
`tests/runs/test_research_run_boundaries.py::test_the_domain_still_imports_without_django_present`,
`tests/evaluation/test_evaluation_boundaries.py::test_loading_the_corpus_imports_no_framework_or_provider`).
In this session the flake class was sustained (isolation retry reproduced the
same signature), consistent with its documented "may fail independently between
runs" nature. **No node outside the allowlist fails.**
`python manage.py check` → "System check identified no issues (0 silenced)".

---

## 1. Current-state execution / data-flow map

### 1.1 Topology (verified in code)

```
GET  /research/new        web.views.research_new        form only; ZERO live work
POST /research/new        web.views.research_new
     -> ResearchRun.objects.create_from_request(ResearchRequest)   [CREATED]
     -> execution.orchestration.execute_research_run(run_id)
           1. ResearchRun.objects.get + run.to_research_request()
           2. runs.execution_claims.claim_execution(run)
              (atomic compare-and-set CREATED->RUNNING; the paid-call
               protection: "at most one execution claim may succeed")
           3. _execute_claimed_run(...):
              a. 4D-A direct: providers.preferred_source_config.is_directmacro_enabled()
                 -> providers.directmacro.DirectMacroLocator.locate()   [NO network]
                 -> per target: _process_candidate_url(...)
              b. fallback decision: _has_valid_4a_buckets()  (pure research
                 primitive aggregate_listing_prices; >=1 bucket => skip Serper)
              c. 4D-D alias: execution.micron_alias_authority.acquire_micron_alias_eligibility()
                 [ONE JSON catalog fetch] -> _persist_alias_snapshot()
                 (ResearchMicronAliasSnapshot, body SHA-256, BEFORE paid search)
              d. providers.serper.SerperSearchProvider.from_environment().search(query)
                 [ONE paid call, lazy construction] -> per result:
                 _process_candidate_url(...)
              e. _process_candidate_url (both direct + search URLs):
                 CandidateDeduplicator (in-run exact-URL dedup)
                 -> PageFetchRequest(url)  (URL contract validation)
                 -> providers.http_page.HttpPageFetcher.fetch()  [NETWORK]
                 -> research.extraction.extract_listing_observations(body_text, final_url)
                 -> _deduplicate_exact_observations (exact value-equality, per page)
                 -> execution.normalization.normalize_listings  (pure)
                 -> execution.matching.assess_identity  (pure 2A/3C)
              f. execution.semantic_integration.evaluate_semantic_matches:
                 per eligible candidate -> semantic.runtime.SemanticRuntime.evaluate()
                 [1-2 provider calls; PRIMARY amax/qwen3.8-27b, FALLBACK
                  vllm-262k/Qwen3.6-27B-262K; temperature 0.0; max_tokens 32768;
                  prompt v1.1] -> _validate_provenance (mechanical binding)
              g. execution.aggregation.aggregate_prices  (frozen 4A)
           4. _encode_aggregation_result (research.price_result_codec v1)
           5. 4D-B: _try_vendor_commercial_lookup
                 providers.internal_vendor.InternalVendorAdapter.lookup()
                 [ONE network call; env PI_VENDOR_LOOKUP_BASE_URL]
                 -> frozen 2A binding (compare_part_numbers)
                 -> research.commercial_supplement_codec encode
           6. 4D-C-A: _try_fetch_fx_rates
                 providers.fx.EcbFxProvider.fetch_rates()
                 [ONE call iff non-USD currency in public buckets OR usable
                  vendor observations] -> research.fx_codec encode
           7. ATOMIC FINAL PUBLICATION (transaction):
              PriceIntelligenceSnapshot + AiAssistedReviewCandidate rows
              + ResearchSupplementSnapshot (opt) + ResearchFxSnapshot (opt)
              + complete_execution(RUNNING->COMPLETED)
     -> redirect /research/<uuid>

GET  /research/<uuid>     web.views.research_detail     STRICTLY READ-ONLY:
     decodes persisted PriceIntelligenceSnapshot (request-provenance check
     decoded.request == run.to_research_request()), review candidates,
     replay_compact_quote_projection / replay_public_compact_quote_projection
     (zero live Search/Page/Vendor/ECB/Semantic/network work),
     ResearchMicronAliasSnapshot (display only), ComparableResearchExecution
     child (decode only). NO provider calls. NO writes.

POST /research/<uuid>/retry        new run via runs.retry_run (NO evidence or
     snapshot copied; re-executes live) -> execute_research_run(new)
POST /research/<uuid>              web.views.research_review (8-step fail-closed
     binding validation; HARD_CONFLICT confirm blocked; runs-owned writes)
POST /research/<uuid>/comparables  web.views.research_comparables
     -> runs.comparable_execution_claims.trigger_comparable_research
        (IDEMPOTENT: returns existing ACTIVE or COMPLETED child)
     -> if PENDING: execution.comparable_runtime.execute_comparable_research_with_default_providers
        -> claim (PENDING->RUNNING) -> PRE1 authority fetch [ONE page]
        -> target 6C extraction + 7A discovery (from HELD document)
        -> 6C per candidate from HELD support docs (one-fetch-per-source)
        -> ONE 6D batch enrichment (one-fetch-per-datasheet, PDF [NETWORK])
        -> 6C+6D composition, 7B scoring, projection, codec v1
        -> complete (RUNNING->COMPLETED, result_payload persisted)
```

### 1.2 What is persisted, and how it is keyed

All eight models are in `product_intelligence/runs/models.py`; **every artifact
is keyed to one ResearchRun UUID** (OneToOneField primary key for snapshots;
ForeignKey for logs/children/candidates) and is written once at publication
(immutable afterward, except `AiAssistedReviewCandidate.review_state` which is
human-owned mutable state):

| Model | Key | Carries |
| --- | --- | --- |
| `ResearchRun` | run UUID | request (MPN+description), lifecycle state, timestamps |
| `ExecutionEvidenceRecord` | run + attempt_number (unique per run) | stage/outcome/candidate_url/detail_code — an ordered per-run attempt LOG |
| `PriceIntelligenceSnapshot` | run UUID (pk) | codec v1 opaque JSON of `PriceAggregationResult` (AD-050) |
| `AiAssistedReviewCandidate` | run + assessment_index | immutable semantic provenance + mutable review_state |
| `ComparableResearchExecution` | child UUID, parent_run FK | lifecycle + codec v1 `ComparableResearchResult` |
| `ResearchSupplementSnapshot` | run UUID (pk) | vendor commercial codec v1 (supplemental authority only) |
| `ResearchFxSnapshot` | run UUID (pk) | FX codec v1 (display-supplemental only) |
| `ResearchMicronAliasSnapshot` | run UUID (pk) | alias audit; body SHA-256, never the body |

**Raw bodies are never persisted anywhere** (verified: no `body_text` /
`body_bytes` references in `runs/` or `web/views.py`): page HTML, Serper JSON
(raw_response_reference), vendor body ("The raw Vendor body is never logged,
persisted ..." — `providers/internal_vendor.py` docstring and STATUS FU3/FU4),
ECB XML, PDF bytes, Micron catalog body, semantic model raw output (only
bounded parsed fields; `SemanticRuntimeResult.to_dict()` "Contains no raw
response, no provider body, no exception text, no API key, and no
chain-of-thought"). Serper raw references are dropped after orchestration
(`execution/orchestration.py` uses only `search_response.results` and
`len(...)`).

### 1.3 Existing replay / reuse mechanisms (NOT caches — do not conflate)

1. **Historical report replay** — `web.views.research_detail` +
   `execution/compact_quote_replay.py` (`replay_compact_quote_projection`,
   `derive_human_confirmed_assessment_indices`) +
   `execution/compact_quote_public_replay.py` (`replay_public_compact_quote_projection`,
   FU2: loads its OWN run's `PriceIntelligenceSnapshot`, decodes, verifies
   request provenance; never reads `ResearchSupplementSnapshot` on the denied
   branch). Run-scoped, zero live I/O, immutable.
2. **Idempotent comparable trigger** — `runs/comparable_execution_claims.py::trigger_comparable_research`
   returns the existing ACTIVE or COMPLETED child for the same parent run
   (same-run-scoped reuse, lifecycle semantics, not freshness semantics).
3. **In-run URL dedup** — `execution/deduplication.py::CandidateDeduplicator`
   (exact stripped-URL string, in-memory, dies with the run).
4. **In-page exact-observation dedup** — `orchestration._deduplicate_exact_observations`
   (frozen dataclass value equality, first-occurrence wins, per page).
5. **In-run one-fetch-per-source / one-fetch-per-datasheet** —
   `execution/specification_enrichment.py` (batch: "deduplicated PDF fetch
   (one per unique URL)", `fetched_support_pages` dict),
   `execution/comparable_research.py` (held documents),
   `execution/comparable_discovery.py` (per approved source).
6. **Claim-based duplicate paid-call protection** — `runs/execution_claims.py::claim_execution`
   (PLAN §18.1: "As of 4C-B, duplicate paid-call protection IS IMPLEMENTED.
   ... A new ResearchRun created for retry cannot share evidence or snapshot
   with any prior run.")
7. **Evaluation-only replay** — `semantic/transport.py::FakeSemanticModelTransport`,
   recorded page fixtures (`tests/fixtures/pages/*.html`), evaluation
   `responses.jsonl` export/import (`evaluation/semantic/runner.py`). Not
   production paths.
8. **Process-wide runtime singleton** — `semantic/runtime.py::get_default_runtime`
   (caches the *runtime object*, never any response).
9. **Retry** — `runs/execution_claims.py::retry_run`: "No old snapshot is
   copied. No old execution evidence is copied." Cross-run evidence sharing is
   explicitly FORBIDDEN today.

**Consequence:** there is currently **no cross-run reuse of any live
artifact**. Every `POST /research/new` re-executes the full live pipeline for
a brand-new run. The only "cached" thing is per-run immutable persistence,
which is replay, not caching.

---

## 2. Cacheability / freshness inventory

Classification keys: **producer / consumer / persistence / key inputs /
authority / provenance / change class / cross-run safety / hazards / existing
freshness signals / audit persistence needs.**

Change classes used (no TTLs chosen):
- **IMM** immutable / content-addressable
- **RUN** session/run-local (in-memory, dies with the run)
- **MKT** short-lived market observation (wall-clock age changes meaning)
- **PROV** provider-dependent (meaning depends on provider generation/state)
- **CAT** product/catalog metadata (content identity > age)
- **FXD** exchange-rate observation (identity = observation_date)
- **SEM** semantic decision tied to frozen inputs/config (content identity,
  with provider-side model-drift hazard)
- **HUM** human-reviewed state (never cacheable as evidence)

### 2.1 Public search/provider results (Serper) — MKT + PROV, PAID

- Producer: `providers/serper.py::SerperSearchProvider.search`
  (`DEFAULT_ENDPOINT` fixed; `PROVIDER_ID = "serper"`; `retrieved_at` set by
  adapter clock).
- Consumer: `execution/orchestration.py::_execute_claimed_run` step 3 ONLY
  (candidate URLs feed `_process_candidate_url`; result count feeds
  `ExecutionResult` + `ExecutionEvidenceRecord` SEARCH stage).
- Persistence: **none** — `SearchResponse.raw_response_reference` and
  `SearchResult.raw_reference` are dropped; only FETCH-stage evidence records
  survive.
- Key inputs: exact query text (deterministic `execution/search_query.py::build_search_query`
  / `build_alias_expanded_search_query`) + provider identity (endpoint,
  PROVIDER_ID) + alias relation when ESTABLISHED.
- Authority: **discovery only** — a search result is not a listing; identity
  and price authority are re-derived live from fetched pages (3C/4A).
- Cross-run reuse: semantically UNSAFE without re-executing the whole
  fetch→extract→normalize→match chain on fresh pages, because the downstream
  evidence is time-sensitive; and the run-scoped evidence model
  (`ExecutionEvidenceRecord` per run, AD-050/AD-052) has no place for
  another run's search generation.
- Stale-data risk: high (index state, ranking, availability of listed URLs).
  Poisoning risk: medium (query-keyed; provider output is untrusted text).
- Boundary bypass risk: low IF results are re-piped through the full
  candidate pipeline; HIGH if a cache returned already-fetched/extracted
  artifacts (would skip `PageFetchRequest`/SSRF re-validation and fresh
  identity assessment).
- Existing freshness signals: `retrieved_at` (in-memory only); SEARCH
  evidence stage/outcome per run.
- Audit persistence if cached: query text, provider_id, endpoint identity,
  response content hash, retrieved_at, per-result raw_reference (today
  dropped — a raw cache would be the FIRST persistence of Serper raw material,
  a new evidence surface).

### 2.2 Page fetch results — MKT (prices) / CAT (support pages) / PROV

- Producer: `providers/http_page.py::HttpPageFetcher.fetch`
  (`FETCHER_ID = "stdlib-http"`; bounds: 10 s/hop, 3 redirects, 5 MiB, HTML by
  default or the reviewed JSON config; every redirect hop revalidated for
  public-routability).
- Consumer: `_process_candidate_url` (main pipeline); `_try_direct_acquisition`
  targets; 6C/7A/7C-B support/catalog pages; 4D-D Micron catalog
  (JSON-configured fetcher).
- Persistence: **none** — `FetchedPage.body_text` is dropped after extraction;
  extracted `ListingObservation`s (with `source_url` = final_url,
  `raw_reference` node text) survive inside `PriceIntelligenceSnapshot`.
- Key inputs: `requested_url` + `final_url` + redirect_count + media-type
  config (HTML vs JSON) + fetcher bounds identity.
- Authority: raw untrusted content (§19) — every downstream decision is
  re-derived live.
- Change class: price pages = MKT (short); manufacturer support/catalog/datasheet
  pages = CAT (longer; content-identity); Micron catalog = CAT + already
  content-hashed (body SHA-256 persisted in the alias snapshot).
- Cross-run reuse: SAFE-IF-RAW: a cached `FetchedPage` re-entering the full
  extract→normalize→match→aggregate chain preserves every validation boundary
  (extraction, normalization, 2A/3C identity, 4A, semantic eligibility) — the
  cache would only substitute the network hop. UNSAFE if keyed on
  `requested_url` alone: redirects mean content identity is the FINAL URL
  (the fetcher's own docstring: "A redirect is evidence"), and the documented
  DNS rebinding gap means host-content binding must be re-proven.
- Stale-data risk: high for price pages; low for datasheets.
- Poisoning risk: a URL-keyed raw cache stores untrusted content; key must
  bind final_url + content hash + fetcher media-type config; a poisoned entry
  would replay attacker text through extraction (extraction is
  fail-closed/bounded, but trust model assumes fresh retrieval).
- Boundary bypass: a raw cache hit must still produce a full `FetchedPage`
  contract (status, content_type, byte count, final_url) so extraction and
  evidence records are unchanged; it must NOT skip `PageFetchRequest`
  validation or the FETCH-stage evidence record.
- Existing freshness signals: `FetchedPage.retrieved_at` (in-memory),
  `final_url`, `body_byte_count`, `redirect_count`. **Gap:** per-observation
  `retrieved_at` is NOT persisted — `research/listings.py::ListingObservation`
  has no time field and `price_result_codec._enc_listing_observation` omits it;
  the report shows only `run.created_at` / `snapshot_created_at`
  ("Price result snapshot stored at", template L756-758). This is a pre-existing
  §18 freshness-display gap ("A report must show how old its evidence is").
- Audit persistence if cached: final_url, requested_url, redirect_count,
  content hash, body byte count, content_type, media-type config id,
  original retrieved_at, cache_served_at, key-composition version.

### 2.3 Internal vendor observations — MKT (shortest), SENSITIVE, ACCESS-GATED

- Producer: `providers/internal_vendor.py::InternalVendorAdapter.lookup`
  (env `PI_VENDOR_LOOKUP_BASE_URL`; one network call; no redirect; raw body
  never logged/persisted; allowlist mappers strip SessionId/BuyerAccountId/
  SystemId; strict bounded literal parser).
- Consumer: `orchestration._try_vendor_commercial_lookup` → frozen 2A binding
  (`compare_part_numbers`; only EXACT/NORMALIZED_EXACT) →
  `commercial_supplement_codec` → `ResearchSupplementSnapshot` (per run) →
  Compact Quote vendor rows (ALLOWED branch only, 4D-C-SEC
  `web/commercial_access.py::vendor_price_access_allowed`, REMOTE_ADDR CIDR
  gate, fail-closed DENY).
- Persistence: normalized bound observations per run (supplemental authority
  only — never enters 4A Machine Price, Reviewed Price, identity, semantic,
  or comparable scoring).
- Key inputs: canonical MPN + provider base-URL identity (config).
- Change class: MKT shortest — availability and customer price are the most
  time-sensitive data in the system (the FU4 production incident is exactly
  this: upstream commercial data mutated between observations).
- Cross-run reuse: UNSAFE initially — (a) vendor data is access-gated at
  PRESENTATION per-request; a shared store readable from the public/denied
  replay branch would be a data leak (the denied branch is hard-wired to
  NEVER read `ResearchSupplementSnapshot` — FU2); (b) supplemental authority
  is run-scoped; (c) sensitivity (commercial pricing) is the reason 4D-B
  triggered the §19 security gate.
- Stale-data risk: critical (stock/price). Poisoning: medium (internal API,
  allowlist parsing is fail-closed). Authority-escalation risk: HIGH — cached
  vendor observations must never become canonical public-market evidence.
- Existing freshness signals: `VendorCommercialResult.retrieved_at` persisted
  per run; per-observation availability/price/quantity.
- Verdict: **do not cache initially** (§5).

### 2.4 FX / public currency observations — FXD (content identity = observation_date)

- Producer: `providers/fx.py::EcbFxProvider.fetch_rates`
  (`_ECB_STATISTICS_URL` daily eurofxref XML; bounded 10 s / 512 KiB;
  Decimal-exact parse; NaN/negative rejected).
- Consumer: `orchestration._try_fetch_fx_rates` (one call per run iff
  `_get_required_fx_currencies` non-empty: public 4A buckets + usable vendor
  observations, non-USD) → `research/fx_codec.py::encode_fx_observation` →
  `ResearchFxSnapshot` (per run) → Compact Quote "USD Equivalent" (display
  only; original amount/currency stays authoritative).
- Persistence: `provider_id`, `observation_date`, `base_currency`, rate
  entries, `retrieved_at` — full provenance per run.
- Key inputs: `provider_id` + `observation_date` + `base_currency` + requested
  currency set (or full-day document content hash).
- Authority: **display-supplemental only**; failure is NONFATAL (run
  completes; "USD Equivalent ... Unavailable"); never feeds Machine/Reviewed
  Price, identity, semantic, or vendor authority.
- Change class: FXD — the ECB publishes DAILY official rates; the persisted
  `observation_date` IS the freshness identity (PLAN roadmap: "ECB FX rates
  (tied to persisted official observation date)"). Wall-clock age of the
  *fetch* is irrelevant once the *observation date* is known.
- Cross-run reuse: SAFE — same (provider_id, observation_date, document
  content) ⇒ same rates, by construction of the source; no authority, no
  sensitivity, no human review, no paid metering; single call site
  (`_try_fetch_fx_rates`); contract shape `FxObservationSet` already carries
  all provenance a cache-hit audit needs.
- Stale-data risk: LOW (rates for a given observation_date are immutable
  official records); the only hazard is serving a *different day's* document
  as today's — prevented by keying on observation_date and comparing the
  document content hash.
- Poisoning risk: LOW (public official endpoint, TLS-verified — FU1
  documented the secure trust chain; no insecure bypass exists).
- Existing freshness signals: `observation_date` + `retrieved_at` persisted.
  Display gap: the report does not currently render the FX observation date
  (no `observation_date` in `research_detail.html`; only the converted value
  appears) — minor, fixable at 8A without touching frozen contracts.
- Verdict: **best first candidate** (§6 Q1, §8).

### 2.5 Semantic-model calls/results — SEM (frozen inputs/config) + provider drift hazard

- Producer: `semantic/runtime.py::SemanticRuntime.evaluate` via
  `execution/semantic_integration.py::evaluate_semantic_matches` (one call per
  eligible candidate; `_is_semantic_eligible` + `_has_usable_evidence`
  gates; lazy `get_default_runtime()`).
- Pinned route (frozen, B1/AD-063): `PRIMARY_PROVIDER="amax"`,
  `PRIMARY_MODEL="qwen3.8-27b"`, `FALLBACK_PROVIDER="vllm-262k"`,
  `FALLBACK_MODEL="Qwen3.6-27B-262K"`, `SEMANTIC_TEMPERATURE=0.0` (exact
  float), `SEMANTIC_MAX_TOKENS=32768`, `SEMANTIC_PROMPT_VERSION="1.1"`
  (`semantic/contract.py:34`); `validate_runtime_config` rejects any other
  value; fallback ONLY on the explicit execution-failure allowlist.
- Consumer: `AiAssistedMatchResult` (MATCH only) → `AI_ASSISTED_MATCH`
  disposition → `AiAssistedReviewCandidate` persistence (bounded provenance:
  target/candidate fields, evidence_source, confidence, reason code,
  matched/conflicting attributes, actual_provider, actual_model,
  prompt_version) → human review → Reviewed Price / Compact Quote rows
  (identity authority only).
- Persistence: **raw model output is never persisted**; only bounded parsed
  fields for MATCH candidates. Non-MATCH/failed calls leave only SEMANTIC
  stage evidence records (outcome + detail code + candidate_url).
- Key inputs (a semantically valid key): full prompt content (v1.1 template +
  case_id + target_mpn + target_description + candidate_title +
  candidate_mpn_field + candidate_sku + candidate_specs + evidence_source) +
  pinned route seats + temperature + max_tokens + provider-reported actual
  model identity.
- Authority: ADVISORY only — `AI_ASSISTED_MATCH` stays outside canonical 4A;
  deterministic assessments in the snapshot are never mutated; HARD_CONFLICT
  candidates cannot be confirmed (working-quote policy).
- Change class: SEM — for IDENTICAL frozen inputs the *intended* decision is
  identity-stable, BUT the production invariant is **per-response model
  identity proof** (`runtime._interpret`: `provider_reported_model != model`
  → `MODEL_IDENTITY_MISMATCH`). A provider serving the same model NAME with
  updated weights over time means "same key, different behavior" is possible
  — the system's own answer to that is: re-ask, and prove identity per
  response.
- Cross-run reuse: UNSAFE initially. A cached `SemanticRuntimeResult` reused
  in another run would (a) skip the live model-identity proof, (b) require
  re-validation through `_validate_provenance` (the result's fields must
  mechanically equal the new run's observation fields — true only for
  byte-identical candidate evidence), (c) risk converting "advisory for THIS
  run's evidence" into "advisory for any similar evidence", and (d) interact
  with human review state that is run-scoped and human-owned.
- Boundary bypass risk: HIGH if the cache sits at the transport (would
  fabricate attempt history — `SemanticRuntimeResult` self-validation
  mechanically rejects impossible attempt/routing histories, a good backstop,
  but a transport-level cache would still suppress the per-response identity
  proof); LOWER if it sits at `evaluate()` and re-runs full validation —
  but even then the model-drift hazard remains.
- Existing freshness signals: none temporal (by design) — identity signals
  (prompt version, model, config, evidence fields) are the freshness.
- Verdict: **do not cache initially**; if ever needed, cache at
  `SemanticRuntime.evaluate()` level with the FULL key above plus
  provider-reported identity, and re-run `_validate_provenance` and
  eligibility on every hit. Never cache failures as decisions
  (failure = bounded error, no authority; `error_type` results carry no
  provenance).

### 2.6 Product specification / support-page evidence (6C / 7A sources) — CAT

- Producer: `execution/specification_evidence.py::research_enterprise_ssd_specifications`
  (explicit `SpecificationEvidenceSource` descriptors: policy-as-code
  `source_name`/`source_url`/`source_authority`, never hostname-inferred) via
  `HttpPageFetcher`; `execution/comparable_discovery.py`
  (`ComparableCandidateSource` approved catalog sources, AUTHORITATIVE
  required).
- Consumer: 6B normalization + 6A resolution (VERIFIED only for
  AUTHORITATIVE support); 7A candidate discovery; 7B scoring (VERIFIED-only).
- Persistence: **none standalone** (6C/7A are no-persistence phases); in
  production they flow through `ComparableResearchExecution.result_payload`
  (per parent run, codec v1, with per-attempt `final_url` + `retrieved_at`).
- Key inputs: `policy_id` / source descriptor identity + `source_url` +
  final_url + content + bound ProductIdentity (for 6C).
- Authority: specification authority (AUTHORITATIVE/SECONDARY explicit) —
  feeds comparable presentation, NOT market price, NOT 4A, NOT identity
  authority for the requested product.
- Change class: CAT — manufacturer support/catalog pages change rarely;
  content identity (page body hash) matters more than wall-clock age.
- Cross-run reuse: plausibly SAFE at the RAW level (re-run extraction/
  resolution per use), subject to the same final_url/content-hash keying as
  §2.2; the 7C-B pipeline already holds documents per-run and dedups
  fetches per source.
- Stale-data risk: LOW-MED (catalogs gain/lose models; spec values rarely
  mutate for a published product). Poisoning: as §2.2 (untrusted content,
  but extraction is structurally bounded: `var supportSpecsData =
  JSON.parse('...')` only; host-escape refused by PRE1 authority check).
- Existing freshness signals: per-attempt `final_url`/`retrieved_at`
  persisted inside comparable results; PRE1 authority origin-bound check.
- Verdict: second-wave raw-cache candidate (free, non-sensitive, no market
  authority), after FX.

### 2.7 Datasheet/PDF fetches and parsed specification evidence (6D) — CAT, IMM per content hash

- Producer: `providers/http_pdf.py::HttpPdfFetcher` (stdlib urllib; 10 MiB
  bound; no redirect following beyond 3; `FetchedDocument.body_bytes`).
- Consumer: `execution/specification_enrichment.py`
  (`enrich_enterprise_ssd_specifications_batch`: deduplicated PDF fetch —
  one per unique URL; `pdfplumber` table extraction;
  `research/enterprise_ssd_datasheet.py` MPN→table→column→row binding; six-
  field allowlist; 6B normalization; 6A resolution).
- Persistence: **PDF bytes never persisted**; parsed observations +
  `DatasheetAttemptResult` provenance (source_name, source_url, final_url,
  retrieved_at, observation_count) inside `ComparableResearchExecution`
  result.
- Key inputs: datasheet URL (derived from approved support record,
  `derive_datasheet_source_from_discovery` — 7A-grounded) + content hash.
- Authority: AUTHORITATIVE specification evidence only (SECONDARY rejected).
- Change class: CAT / IMM — a published datasheet PDF for a given URL is
  content-stable; the real Seagate fixture is even SHA256-locked
  (STATUS 6D: `b449dc48...`, 201,997 bytes). **Content hash is the natural
  key; age is irrelevant once identity is fixed.** The Micron alias snapshot
  (`research/micron_alias_codec.py`: `body_sha256` persisted, body not) is
  the system's existing content-addressing precedent.
- Cross-run reuse: SAFE-IF-RAW (re-run table interpretation per use); the
  heaviest single network artifact (10 MiB, 8-page PDF) — best
  cost/benefit of the raw classes.
- Stale-data risk: LOW (datasheets are versioned documents; a URL that
  changes content is a NEW document identity). Poisoning: LOW-MED (same
  untrusted-content discipline; the 6D parser is strictly bounded — three
  exact model-row forms, six exact spec-row patterns, whole-PDF MPN
  uniqueness).
- Existing freshness signals: `retrieved_at` + `final_url` per datasheet
  attempt; PDF content hash (not yet persisted — would be added by a cache).
- Verdict: strong second-wave raw-cache candidate alongside 2.6.

### 2.8 Comparable-product discovery / research (7A-7C) — CAT + MKT mix, per-run persisted

- Producer: `execution/comparable_research.py::execute_comparable_research`
  (authority fetch + held-document re-extraction + 6D batch) via
  `execute_comparable_research_with_default_providers` (7C-C).
- Consumer: `ComparableResearchExecution.result_payload` → web decode +
  parent binding validation (`views._validate_comparable_result_parent_binding`)
  → display-only presentation.
- Persistence: per parent run, codec v1, full audit chain (authority attempt,
  datasheet attempts, evidence source references, per-field assessments) —
  the result is IMMUTABLE history, already "cached" for its own run.
- Key inputs: parent run's canonical request + PRE1 policy identity +
  source/datasheet content identities.
- Authority: comparable/display only — never feeds price or requested-
  product identity authority.
- Change class: mixed — candidate catalog = CAT; candidate spec values = CAT;
  discovery SET = PROV (catalog content).
- Cross-run reuse: the trigger is already idempotent per parent; a cross-run
  comparable cache would need the full key stack (policy + sources +
  datasheets content hashes) — feasible but NOT needed for the first wave
  because the expensive parts (support pages, PDFs) are exactly the 2.6/2.7
  raw artifacts: cache THOSE, and re-composition is cheap pure work.
- Verdict: do not cache the COMPOSITE result cross-run initially; cache the
  raw inputs (§2.6/§2.7) and let 7C-B re-derive.

### 2.9 Existing persisted ResearchRun / evidence / snapshot records — IMM (historical)

- All eight models (§1.2). Immutable per run by construction (publication
  transaction; `save()` lifecycle guards; `editable=False`; FU2 run-scoped
  authority). They are **historical evidence, not a cache**: a report GET
  replays them with zero live work and they are NEVER refreshed (PLAN:
  "historical reports (immutable replay, NEVER refreshed merely by GET)").
- A cache must not write into them and must not be readable from them:
  cross-run reads of another run's snapshot as "current evidence" was the
  exact FU2 review blocker (same-request cross-run price substitution).

### 2.10 Human-reviewed state (AiAssistedReviewCandidate) — HUM, never cacheable

- Mutable `review_state` is human-owned, run-scoped, and the ONLY source of
  `HUMAN_CONFIRMED` authority (with the 8-step fail-closed POST validation and
  `derive_human_confirmed_assessment_indices` proving each confirmed index
  from persisted state). A cache returning CONFIRMED state, or a cached
  semantic MATCH presented as reviewable in another run, would fabricate
  human confirmation — prohibited outright.

---

## 3. Authority and provenance hazards (cache-specific)

1. **Authority escalation by prior acceptance.** Today every authority
   conclusion is re-derived live per run (2A/3C identity, 4A aggregation,
   semantic eligibility+provenance, working-quote policy, human binding).
   A cache that persists a CONCLUSION (accepted listing, MATCH, confirmed
   candidate, vendor observation) and replays it in another run would convert
   "derived for this run's evidence at this time" into "inherited" — the
   frozen models have no such inheritance and every FU1/FU2 correction moved
   authority back to the run's OWN persisted artifacts. Hard rule: **a cache
   may only substitute a network hop; it may never substitute a decision.**
2. **Run-scoped evidence authority (FU2 precedent).**
   `replay_public_compact_quote_projection` was blocked for trusting a
   caller-supplied same-request `PriceAggregationResult` (identical source
   URL/title/MPN/SKU, different price, another run). Any cross-run derived-
   result reuse needs the equivalent binding: result must be proven to belong
   to THIS run's request AND this run's exact input content — or it must
   never carry authority.
3. **Vendor supplemental → canonical public market.** `ResearchSupplementSnapshot`
   authority is sealed at three places: 4A input (vendor never enters
   `aggregate_prices`), the denied replay branch (never reads the supplement),
   and 4D-C-SEC (per-request REMOTE_ADDR visibility). A shared vendor cache
   readable outside the allowed branch or feeding bucket membership breaks
   the §19 gate and the supplemental boundary.
4. **Semantic provenance is mechanically bound per run.**
   `_validate_provenance` requires the semantic result's target/candidate
   fields to equal THIS run's observation fields byte-for-byte;
   `SemanticRuntimeResult` self-validation rejects impossible attempt/routing
   histories and any non-pinned route/prompt. A transport-level response
   cache would suppress the per-response `provider_reported_model` identity
   proof (the system's only defense against a provider quietly changing what
   "qwen3.8-27b" means) and could present a stale attempt history as live.
5. **HARD_CONFLICT and human confirmation fabrication.** Working-quote policy
   blocks confirm on explicit hard identity conflict; review POST is 8-step
   fail-closed. Any path that caches/returns review state or confirmed
   indices across runs mints `HUMAN_CONFIRMED` authority without a human.
6. **AI_ASSISTED_MATCH stays outside 4A.** Snapshot assessments are never
   `AI_ASSISTED_MATCH`; reviewed aggregation is a separate contract
   (`aggregate_reviewed_listing_prices`). A derived-result cache that mixes
   deterministic and advisory rows, or a semantic cache that feeds bucket
   membership, would silently promote advisory to canonical.
7. **Redirect/SSRF surface on raw caches.** The fetcher revalidates EVERY
   hop and documents a DNS rebinding gap. Caching by `requested_url` with
   final content (or by host) would freeze a redirect chain or a rebinding
   outcome. Key must bind `final_url` + content hash + fetcher media-type
   config; safety decisions (`BLOCKED`/`SAFE_URL_REFUSED`) must NEVER be
   cached (they are policy evaluations, re-run live per request).
8. **Sensitive-data persistence surface.** Vendor raw bodies and
   SessionId/BuyerAccountId/SystemId are today guaranteed NOT persisted
   (allowlist mappers; "raw Vendor body is never ... persisted"). A raw
   vendor cache would create a new sensitive-data store — the exact exposure
   that 4D-B's security gate exists to contain. FX/search/page/PDF raw data
   are non-sensitive; vendor is not.
9. **Access-gated presentation vs cached artifacts.** Compact Quote vendor
   rows are visible per-request (CIDR gate). Caching rendered report HTML
   (E-class) would let a DENIED viewer receive an ALLOWED rendering from
   cache. Presentation must remain per-request composition over persisted +
   (future) cache artifacts.
10. **Provenance loss.** The system's evidence-first rule (CLAUDE.md) requires
    source, URL, retrieval time, raw reference, normalized value, decision,
    reason, confidence for every reported fact. A cache hit that does not
    persist `original_retrieved_at` + `content_hash` + `cache_served_at` +
    `key_composition_version` + source identity silently degrades this —
    "stale data presented as current is a correctness bug" (PLAN §18).
11. **Paid-call protection confusion (PLAN §18.1).** `claim_execution` already
    solves in-run duplicate paid calls. A cross-run search cache is a
    DIFFERENT problem (general caching) with provider-generation hazards
    (`PROV`); conflating the two is the exact error §18.1 records.
12. **Per-observation retrieval time gap.** `ListingObservation`
    (persisted in the price snapshot) carries NO `retrieved_at`; only
    `run.created_at`/`snapshot.created_at` are shown. Any freshness policy
    (cache or otherwise) must first be able to STATE evidence age per
    artifact; today the main price pipeline cannot, for individual listings.

---

## 4. Recommended cache boundaries (A–E separated)

**A. Raw external evidence caching — APPROVE AS A CLASS (two waves).**
- Store: NEW dedicated persistence (not Django's `CACHES`, not an existing
  model); codec in `research/` (pure key/hash/payload contracts), model in
  `runs/` (only model-owning package), lookup + I/O in `execution/`
  (orchestration owns pipeline sequencing), adapters UNCHANGED.
- Contract: lookup returns the EXISTING artifact shape (`FetchedPage`,
  `FetchedDocument`, later `SearchResponse`/`FxObservationSet`) so the full
  downstream chain re-executes; every hit is recorded in
  `ExecutionEvidenceRecord` with a new bounded CACHE_HIT detail code +
  original provenance (never silently skipped stages).
- Key discipline: final-URL + content hash + fetcher capability identity
  (media types) for pages/PDFs; provider_id + observation_date + content
  hash for FX; provider + endpoint identity + exact query for search
  (deferred); policy_id + source_url + content hash for catalog/support.
- Sensitive classes (vendor) EXCLUDED from this store by design.
- Invalidation: content-identity (hash) is the primary signal; wall-clock
  only for MKT classes (future); forced refresh = bypass for the current run
  (§18 user rule); safety decisions never cached.
- Wave 1: FX (§2.4). Wave 2: datasheet PDF + manufacturer catalog/support
  pages (§2.6/§2.7). Wave 3 (decision needed): search results (§2.1).

**B. Normalized/interpreted evidence caching — DO NOT BUILD.**
- Normalization/matching/identity/semantic-eligibility are cheap pure work
  and ARE the authority boundaries; re-running them per use is what keeps
  cache hits from bypassing validation. Per-run persisted normalized
  artifacts already exist (snapshots) — those are history, not a cache.

**C. Derived research-result caching — DO NOT BUILD cross-run (wave 1-2).**
- `PriceAggregationResult` / `ComparableResearchResult` / supplement / alias
  are run-authority artifacts; cross-run reuse was a review-blocked defect
  (FU2). Re-derivation from cached RAW inputs (A) is the safe alternative:
  pure research work is milliseconds; the network is the cost.

**D. Semantic-model response caching — DO NOT BUILD (any wave until a
separate decision).**
- Highest authority hazard (§3.4), provider model-drift hazard, and the
  pinned-route self-validation makes a hit a first-class trust event. If
  ever revisited: cache at `SemanticRuntime.evaluate()` (never transport),
  key = full prompt content hash + pinned seats + temperature/max_tokens +
  provider-reported actual identity + exact case fields; every hit re-runs
  `_is_semantic_eligible`, `_has_usable_evidence`, `_validate_provenance`,
  and result self-validation; failures are never cached; advisory-only
  authority unchanged; human review untouched.

**E. Presentation/report caching — DO NOT BUILD.**
- GET is already a zero-live replay of persisted artifacts (the correct
  "cache"); rendering HTML is cheap; and rendered output is per-request
  access-gated (4D-C-SEC) — caching it leaks. The only presentation-level
  improvement in scope is DISPLAYING evidence age (closing §18/§3.12).

**Ownership (import/layer boundaries verified):**
- `research/` stdlib-only guard (`tests/research/test_research_identity_boundaries.py::test_the_research_core_imports_only_stdlib_and_the_domain`):
  cache KEY/HASH/CONTRACT logic (pure) may live here.
- `providers/` must stay vendor/network-only (`tests/providers/test_provider_boundaries.py`): NO cache inside adapters — freshness policy is core, not vendor (PLAN §18: "Cache policy belongs to the core, keyed on the canonical request").
- `execution/` imports domain/research/providers/runs: owns the LOOKUP
  placement around provider calls, after claim and after request/URL
  validation.
- `runs/` is the only Django-model package: owns any new cache model.
- `web/` symbol allowlists (`tests/web/test_web_boundaries.py`): no new
  execution/research surface for web; cache is invisible to presentation
  except displayed age labels.

---

## 5. Explicit "do not cache yet" list

1. **Human review state** (`AiAssistedReviewCandidate.review_state`,
   confirmed-index derivations) — human-owned; fabrication = authority
   escalation. NEVER.
2. **Vendor commercial observations and raw vendor bodies** — sensitive,
   access-gated (4D-C-SEC), shortest freshness, supplemental authority
   sealed at three boundaries.
3. **Semantic model responses (any level)** — model-identity proof,
   pinned-route validation, advisory authority, per-run provenance binding.
4. **Public market page content/prices in the live identity path (wave 1)** —
   MKT freshness + authority-critical; the identity pipeline must stay
   re-derived from fresh evidence until the raw-cache audit (A) is proven for
   CAT classes.
5. **Serper raw search responses (wave 1)** — paid + provider-generation +
   §18.1 problem-class separation; revisit only as an explicit paid-call
   decision with its own key discipline.
6. **Cross-run derived results** (`PriceAggregationResult`,
   `ComparableResearchResult`, supplement, alias, FX-as-authority) — run-
   scoped authority (FU2 precedent).
7. **Safety/policy decisions** (`BLOCKED`, `SAFE_URL_REFUSED`, destination
   refusals, 4D-C-SEC allow/deny, semantic eligibility failures) — live
   evaluations only.
8. **Negative caches of failures** (fetch failures, zero-results, provider
   errors, FX failures, vendor FAILED status) — deferred class (§6 Q9);
   today FX failure is non-fatal by design and vendor state is mutable.
9. **Rendered report HTML / presentation projections** — per-request access
   gating; GET is already zero-live.
10. **`ExecutionEvidenceRecord` content as reusable input** — it is an
    ordered per-run audit log, not an artifact store.

---

## 6. Answers to the required architecture questions

**Q1. Safest first caching layer, and why?**
The **ECB FX observation layer** (§2.4). It is the only artifact that is
simultaneously: (a) display-supplemental authority (never enters 4A,
identity, semantic, vendor, or review paths — `orchestration._try_fetch_fx_rates`
docstring: "FX evidence remains DISPLAY-SUPPLEMENTAL"; failure is NONFATAL);
(b) content-identity keyed by an immutable source fact (`observation_date` —
PLAN: "ECB FX rates (tied to persisted official observation date)");
(c) non-sensitive public official data over verified TLS (FU1 trust-chain
correction); (d) already fully provenance-persisted per run
(`provider_id`, `observation_date`, `base_currency`, rates, `retrieved_at`);
(e) single call site, single artifact shape (`FxObservationSet`); (f) no
interaction with human review, access gates, or paid metering; (g) no
frozen-contract change (codec v1 unchanged; lookup sits inside existing
execution flow). Runner-up: datasheet PDF / catalog pages (CAT, free,
heaviest network cost) as wave 2.

**Q2. What must NOT be cached initially?**
§5 items 1-7, 9, 10 — in priority order: human review state; vendor
observations; semantic responses; cross-run derived results; safety
decisions; rendered presentation; search results (deferred to an explicit
paid-call decision); negative caching.

**Q3. Raw fetch caching vs derived-result reuse — separate stores/contracts?**
**Yes, separate — in fact, only raw (A) is built; derived (C) is not built at
all in the first waves.** Different identity semantics (URL/content vs
request+pipeline), different authority exposure (raw re-derives decisions;
derived carries them), different freshness classes, different sensitivity
rules, and different invalidation signals. One store would create a single
key namespace where a raw hit and a derived hit look alike — the FU2 blocker
shows exactly how cross-run derived substitution fails.

**Q4. Key dimensions per class?**
- FX: `provider_id` + `observation_date` + `base_currency` + full-document
  content hash (+ requested-currency subset derivable without re-fetch).
- Page (CAT wave): `final_url` + content hash + fetcher media-type config id
  + `fetcher_id` (+ requested_url/redirect_count as provenance, not key).
- Page (MKT, future): same + wall-clock bound (TTL decision deferred) +
  explicit not-for-authority flag.
- PDF: `final_url` + content hash + document fetcher identity.
- Search (future): provider_id + endpoint identity + exact query text +
  response content hash; NEVER provider-agnostic.
- Semantic (future, if ever): full prompt v1.1 content hash + pinned
  (primary, fallback) seat identities + temperature + max_tokens +
  provider-reported actual model + case field tuple.
- MPN: vendor keys would need canonical MPN + provider config identity —
  but vendor is excluded.
- Locale/currency: FX base_currency + codes are ISO-validated at contract
  construction; no other locale dimension exists in production today.

**Q5. Where must cache lookup occur so it cannot bypass authority checks?**
Inside `execution/`, at the provider-call boundary, AFTER: run claim
(`claim_execution`), request/URL contract validation (`PageFetchRequest`,
`CommercialLookupQuery`, search query build), and the stage's eligibility
decision (e.g., non-USD currency discovery). The hit returns the ORIGINAL
artifact contract shape so that ALL downstream validation re-executes:
extraction → normalization → 2A/3C identity → 4A → semantic eligibility +
`_validate_provenance` → codec → publication. The lookup must write an
`ExecutionEvidenceRecord` for the stage (CACHE_HIT detail code + original
provenance) rather than omitting the stage. NEVER in `web/` (presentation
must not know), NEVER inside provider adapters (vendor-owned freshness is
forbidden, §18), NEVER in `research/` (pure; contract only).

**Q6. Which existing models/tables must NOT be overloaded as a cache?**
ALL of them, specifically:
- `PriceIntelligenceSnapshot` (AD-050 run-identity design; frozen price
  authority artifact; primary key = run UUID).
- `ExecutionEvidenceRecord` (ordered per-run attempt log; unique
  (run, attempt_number); a cache hit logged as an attempt corrupts historical
  run audits; a cache keyed by it is circular).
- `ResearchSupplementSnapshot` / `ResearchFxSnapshot` /
  `ResearchMicronAliasSnapshot` (run-scoped authority; FU2 precedent:
  cross-run reads of these are an authority defect; also OneToOne — no
  cross-run key exists).
- `AiAssistedReviewCandidate` (human-owned state; immutable provenance
  fields; (run, assessment_index) binding).
- `ComparableResearchExecution` (lifecycle + active_slot invariants; reuse
  is trigger idempotency, a different semantics).
- `ResearchRun` (lifecycle; retry explicitly copies nothing).
- Django's built-in `CACHES` framework: not configured (`config/settings.py`
  has no `CACHES`; docstring: "adds no authentication, caching, or background
  processing") and would couple cache policy to the transport layer.

**Q7. New persistence model, or can an existing contract safely support it?**
**A new persistence model + new codec contract is required** (design only —
NOT implemented here). No existing contract can safely support a cross-run
cache: all current stores are (i) run-identity-keyed (OneToOne/parent-FK),
(ii) publication-immutable, (iii) authority-scoped to their run, and (iv)
schema-versioned to exactly one supported version with fail-closed decode.
A cache needs cross-run content/version keys, bounded retention/invalidation,
hit/miss provenance, sensitivity classes, and its own schema versioning —
none of which fit without overloading one of the §6 models. Proposed shape
(for reviewer approval only): pure key/hash/payload contracts in `research/`
(codec), one new model in `runs/` (e.g., a generic
`CacheObservation`-style store with `key_composition_version`,
`schema_version`, content hash, original provenance, class label,
sensitivity flag), lookup/record logic in `execution/`. No provider or web
change.

**Q8. Observability to distinguish LIVE / CACHE_HIT / REPLAY / persisted
historical evidence?**
- Four disjoint source labels, persisted per artifact use:
  **LIVE** (network call this run: existing `retrieved_at` + stage SUCCESS),
  **CACHE_HIT** (served from store this run: original `retrieved_at` +
  content hash + `cache_served_at` + store schema/key versions),
  **REPLAY** (zero-live read of THIS run's persisted artifacts: the existing
  report-GET / compact-quote-replay behavior),
  **HISTORICAL** (read of another run's artifacts: must NEVER happen —
  any code path that could do so is a defect; FU2 is the proof).
- `ExecutionEvidenceRecord` gains bounded CACHE_HIT detail codes (new enum
  values — additive) so run audits show exactly which stages were live.
- Report display (closes §18 + §3.12): per-artifact-class age — listings
  (requires persisting per-observation `retrieved_at`: codec/schema decision),
  vendor `retrieved_at` (already persisted), FX `observation_date` (already
  persisted; add display), comparable/alias `retrieved_at` (already
  persisted). "Stale data presented as current is a correctness bug" → the
  report renders labels, never silently reuses.
- Store-level: hit/miss counts by class, key-composition version, invalidation
  events, retention bounds — operational, not user-facing.
- Evaluation/test replay (`FakeSemanticModelTransport`, fixtures) stays in
  the evaluation domain only and is labeled REPLAY in tests, never in
  production evidence.

**Q9. Failure / negative caching?**
**Deferred — not part of any initial wave.** If later approved: (a) separate
bounded class with its own key/composition version; (b) strictly SHORTER
freshness than the positive class; (c) same provenance discipline
(original failure time + detail code); (d) NEVER for safety/policy decisions
(destination refusals, access-gate denials, eligibility failures); (e) NEVER
for semantic failures (a failure carries `error_type` and NO provenance/
authority — caching it as "unavailable" would freeze a transient provider
state into a decision); (f) NEVER for vendor `FAILED`/`NOT_FOUND` (mutable
upstream commercial state — the FU4 incident shows vendor state flips
between observations); (g) forced refresh always bypasses.

**Q10. Smallest safe implementation slice after this audit?**
**8A-FX: ECB FX observation reuse** — see §8. It is the smallest slice that
exercises the whole future architecture (new store + codec + execution-
boundary lookup + evidence labeling + report age display) against the
lowest-hazard artifact, changes zero frozen contracts, and is independently
valuable (one fewer daily ECB call per non-USD run after the first).

---

## 7. Open architecture decisions requiring reviewer approval

1. **Store ownership and shape** — new model in `runs/` + codec in
   `research/` + lookup in `execution/` (§6 Q7); exact table/key fields,
   retention bound, and sensitivity-class mechanism need a reviewed spec.
2. **Wave ordering** — FX first, then CAT raw (datasheet PDF, support/
   catalog pages), then (separately) a paid-call decision for Serper raw
   results. Reviewer must confirm the FX-first rationale and that CAT raw
   caching is in 8A scope at all (vs 8A = FX only).
3. **MKT-class policy** — whether 8A ever includes public price page
   caching (wall-clock freshness, per-listing `retrieved_at` persistence,
   codec v2 for `ListingObservation`), or whether MKT stays live-only with
   age displayed. This is a frozen-4A/4B-adjacent decision (snapshot schema
   version bump) and must be explicit.
4. **Per-observation `retrieved_at` in the price snapshot** — additive codec
   schema change (v2) needed for §18 "report shows how old its evidence is"
   on listings; touches a frozen artifact's codec (versioned, fail-closed —
   but still a 4B-contract decision).
5. **Evidence-vocabulary extension** — new `ExecutionDetailCode` values for
   CACHE_HIT (additive enum change in `domain/evidence.py`, a frozen-phase
   file; needs explicit authorization and re-proof of existing stage/
   outcome/detail combination validation).
6. **Forced-refresh semantics** — §18 requires "A user must be able to force
   a refresh." Candidate semantics: (a) new run always bypasses cache for
   its own live stages (retry already does full live execution), (b) an
   explicit refresh flag on intake. Needs a decision; (a) alone may satisfy
   §18 because every research operation is a new run — but that conflates
   "new run" with "refresh" and must be stated.
7. **Negative caching** — approve/defer per §6 Q9.
8. **Semantic response caching** — approve/defer per §4-D (default: defer).
9. **Vendor raw caching** — confirm permanent exclusion (sensitivity) or
   scope a sealed, access-gated variant (default: exclude).
10. **Observability surface** — report age-label design (which classes show
    age, wording, and whether FX observation date display is in scope) and
    store hit/miss operational reporting (pilot_check-style command vs none).

---

## 8. Proposed smallest next implementation slice (NOT implemented)

**PRODUCT-INTEL.8A-FX — ECB FX observation reuse (design sketch only).**

Goal: after the first non-USD run of a given ECB observation date, subsequent
runs reuse the persisted official rate set for THAT date — one fewer live
ECB call — with full provenance and zero authority change.

1. **Pure contracts** (`research/`): an FX-cache codec defining
   `key = f("v1", provider_id, observation_date, base_currency,
   document_content_sha256)` and a payload = the existing
   `encode_fx_observation` V1 dict (reused, not forked) + cache provenance
   (original `retrieved_at`, document hash, key composition version).
2. **Store** (`runs/`): ONE new model (e.g., `FxObservationStore`): unique
   key, payload JSON, `schema_version`, `created_at`, `last_used_at` (or no
   mutable field — reviewer decision), retention bounded by observation_date
   (old dates are eligible for cleanup; cleanup policy is a separate
   decision).
3. **Lookup** (`execution/orchestration.py::_try_fetch_fx_rates`): BEFORE
   `fx_provider.fetch_rates`, check the store for the date-today expectation:
   - fetch-on-miss is UNCHANGED; on success, persist the observation set.
   - on hit, the hit is used only if its `observation_date` equals the
     date the LIVE document would be expected to carry today — i.e., the
     slice may ship WITHOUT a date-assertion by simply always fetching on
     day change (first fetch of the day writes; later same-day runs read) —
     the exact miss/hit boundary is the one open item in this sketch.
   - hit returns the identical `FxObservationSet` shape; `_get_required_fx_
     currencies`, encoding, and `ResearchFxSnapshot` publication are
     UNCHANGED (the run's own FX snapshot is still written — per-run history
     is untouched).
4. **Evidence**: new bounded CACHE_HIT detail code on the FX stage record
   (additive `domain/evidence.py` enum — requires approval per §7.5) carrying
   original `observation_date`/`retrieved_at`; LIVE path unchanged.
5. **Display**: report shows FX observation date + "reused" label (closes
   the FX half of §18 age display without any price-codec change).
6. **Forced refresh**: a brand-new run on a new observation date always
   fetches live; same-day reuse is the only "cached" behavior (stated
   explicitly to satisfy §7.6 candidate (a)).

**Explicitly untouched:** 4A/4B price contracts, ListingObservation codec,
vendor path and 4D-C-SEC, semantic runtime/route/prompt, human review,
comparable pipeline, all existing models (new model is additive — migration
required and reported at implementation), Serper, page/PDF fetching.
**Test posture (planned, not written):** codec round-trip; store key
uniqueness; hit/miss matrix (date change, provider change, hash change);
per-run snapshot still written on hits; LIVE vs CACHE_HIT evidence records;
zero authority leakage (FX still display-only); fail-closed on corrupt store
rows (FxCodecError path unchanged); boundary guards (research stdlib-only,
runs-only-models, execution import rules, web allowlists) re-proven.

---

## 9. Consolidated source evidence

| Conclusion | Evidence (path :: symbol) |
| --- | --- |
| POST /research/new always creates a NEW run and executes live; GET form-only | `product_intelligence/web/views.py :: research_new` |
| Report GET is strictly read-only, zero live work | `product_intelligence/web/views.py :: research_detail`; `product_intelligence/execution/compact_quote_replay.py :: replay_compact_quote_projection` (docstring: "ZERO live provider/network/semantic work"); `product_intelligence/execution/compact_quote_public_replay.py :: replay_public_compact_quote_projection` |
| One paid search per run; claim = paid-call protection | `product_intelligence/runs/execution_claims.py :: claim_execution` (docstring: "at most one execution claim may succeed"); `product_intelligence/execution/orchestration.py :: _execute_claimed_run` step 3 (lazy `SerperSearchProvider.from_environment()`) |
| Retry copies no evidence/snapshot | `product_intelligence/runs/execution_claims.py :: retry_run` ("No old snapshot is copied. No old execution evidence is copied.") |
| Serper raw material dropped (not persisted) | `product_intelligence/providers/serper.py :: _map_serper_payload` (`raw_response_reference`), `search()`; `product_intelligence/execution/orchestration.py :: _execute_claimed_run` (only `search_response.results` / `len` used) |
| Page fetch bounds, per-hop revalidation, fetcher identity | `product_intelligence/providers/http_page.py :: HttpPageFetcher.fetch`, `_assert_destination_is_public`, `FETCHER_ID`, `JSON_ACCEPTED_MEDIA_TYPES` |
| Page body not persisted; per-observation time gap | `product_intelligence/research/listings.py :: ListingObservation` (no time field); `product_intelligence/research/price_result_codec.py :: _enc_listing_observation` (no `retrieved_at`); `product_intelligence/web/templates/web/research_detail.html` L756-758 ("snapshot stored at") |
| Direct location is network-free | `product_intelligence/providers/directmacro.py :: DirectMacroLocator.locate`; `product_intelligence/providers/preferred_source_config.py :: is_directmacro_enabled` |
| Micron catalog: one fetch, body hashed, persisted pre-search, display-only | `product_intelligence/execution/orchestration.py :: _persist_alias_snapshot`; `product_intelligence/research/micron_alias_codec.py :: encode_micron_alias_snapshot` (`body_sha256`); `product_intelligence/execution/micron_alias_authority.py :: acquire_micron_alias_eligibility` |
| Vendor: one call, raw body never persisted, 2A binding, supplemental only | `product_intelligence/providers/internal_vendor.py :: InternalVendorAdapter.lookup` (docstring + FAILED mapping); `product_intelligence/execution/orchestration.py :: _try_vendor_commercial_lookup` (compare_part_numbers; "Vendor commercial evidence MUST NOT affect ...") |
| 4D-C-SEC per-request REMOTE_ADDR gate, fail-closed | `product_intelligence/web/commercial_access.py :: vendor_price_access_allowed`; `config/settings.py :: PI_VENDOR_PRICE_ALLOWED_CIDRS` |
| FX: one call iff non-USD, non-fatal, display-only, observation_date persisted | `product_intelligence/execution/orchestration.py :: _try_fetch_fx_rates`, `_get_required_fx_currencies`; `product_intelligence/providers/fx.py :: EcbFxProvider.fetch_rates`, `_parse_ecb_xml`; `product_intelligence/research/fx_codec.py :: encode_fx_observation` |
| Semantic route pinned + validated; one call per eligible candidate; provenance mechanically bound | `product_intelligence/semantic/runtime.py :: PRIMARY_PROVIDER/PRIMARY_MODEL/FALLBACK_PROVIDER/FALLBACK_MODEL/SEMANTIC_TEMPERATURE/SEMANTIC_MAX_TOKENS`, `validate_runtime_config`, `SemanticRuntimeResult.__post_init__`, `SemanticRuntime.evaluate/_interpret` (MODEL_IDENTITY_MISMATCH), `get_default_runtime`; `product_intelligence/semantic/contract.py :: SEMANTIC_PROMPT_VERSION = "1.1"`; `product_intelligence/execution/semantic_integration.py :: evaluate_semantic_matches`, `_is_semantic_eligible`, `_has_usable_evidence`, `_validate_provenance`, `AiAssistedMatchResult.__post_init__` |
| Semantic raw output never persisted; bounded MATCH provenance only | `product_intelligence/semantic/runtime.py :: SemanticRuntimeResult.to_dict` ("no raw response, no provider body ..."); `product_intelligence/execution/orchestration.py :: _create_review_candidates` |
| In-run URL dedup; in-page exact dedup | `product_intelligence/execution/deduplication.py :: CandidateDeduplicator`; `product_intelligence/execution/orchestration.py :: _deduplicate_exact_observations` |
| Comparable trigger idempotent (ACTIVE/COMPLETED child reused); one-fetch-per-source / per-datasheet within run | `product_intelligence/runs/comparable_execution_claims.py :: trigger_comparable_research`; `product_intelligence/execution/specification_enrichment.py` (batch dedup, `fetched_support_pages`); `product_intelligence/execution/comparable_research.py` (held documents); `product_intelligence/execution/comparable_discovery.py :: discover_enterprise_ssd_comparable_candidates` |
| Approved sources = policy-as-code (identity inputs for CAT caching) | `product_intelligence/execution/comparable_research_authority.py :: _AuthorityPolicy` ("reviewed production configuration-as-code"); `product_intelligence/execution/specification_evidence.py :: SpecificationEvidenceSource` |
| All persisted artifacts run-keyed, publication-immutable, codec-versioned | `product_intelligence/runs/models.py :: PriceIntelligenceSnapshot / ExecutionEvidenceRecord / AiAssistedReviewCandidate / ComparableResearchExecution / ResearchSupplementSnapshot / ResearchFxSnapshot / ResearchMicronAliasSnapshot` (OneToOne run pk; `editable=False`; schema_version checks) |
| Atomic publication (snapshot + candidates + supplement + FX + COMPLETED) | `product_intelligence/execution/orchestration.py :: execute_research_run` (transaction block) |
| No cache framework configured anywhere | `config/settings.py` (no `CACHES`; docstring "adds no ... caching"); zero `django.core.cache` / `lru_cache` / Redis references in `product_intelligence/` |
| Human confirmation: run-scoped, 8-step fail-closed, HARD_CONFLICT blocked, derived from persisted state only | `product_intelligence/web/views.py :: research_review` (steps C-1..C-8); `product_intelligence/execution/compact_quote_replay.py :: derive_human_confirmed_assessment_indices`; `product_intelligence/research/working_quote_policy.py` (HARD_CONFLICT) |
| FU2: cross-run same-request substitution was a BLOCKED defect (run-scoped authority) | `docs/PRODUCT_INTELLIGENCE_PLAN.md :: AD-062`; `product_intelligence/execution/compact_quote_public_replay.py` |
| Caching direction + §18 rules (core-owned policy, forced refresh, age display) + §18.1 paid-call separation | `docs/PRODUCT_INTELLIGENCE_PLAN.md :: §18, §18.1, roadmap "NEXT — PRODUCT-INTEL.8A-PRE" entry` |
| 8A-PRE scope (distinguish: market short, vendor short, FX date-bound, spec longer, comparable medium, deterministic not auto-equivalent, forced refresh, historical immutable) | `docs/PRODUCT_INTELLIGENCE_PLAN.md :: roadmap 8A-PRE block`; `docs/PRODUCT_INTELLIGENCE_STATUS.md :: "Next delivery priority"` |
| Layer boundaries constraining cache ownership | `tests/web/test_web_boundaries.py :: ALLOWED_RESEARCH_IMPORTS/ALLOWED_EXECUTION_IMPORTS`; `tests/research/test_research_identity_boundaries.py :: test_the_research_core_imports_only_stdlib_and_the_domain`; `tests/providers/test_provider_boundaries.py`; `product_intelligence/execution/__init__.py` (docstring dependency direction) |
| Windows/Py3.14 subprocess flake allowlist (baseline failures) | `docs/PRODUCT_INTELLIGENCE_STATUS.md :: "Known issues / debt"` (11-node allowlist; WinError 6/50) |
| B1 frozen route identity | `docs/PRODUCT_INTELLIGENCE_STATUS.md :: B1 section`; `docs/PRODUCT_INTELLIGENCE_PLAN.md :: AD-063` |

## 10. Conflicts and notes

- **No material conflict** found between repository code, tests, STATUS,
  CLAUDE, and PLAN regarding architecture, phase state, or capability at the
  audited SHA.
- Non-conflict notes:
  - STATUS lists PROD-FIX1-FU1..FU4-FU1 as "PENDING FINAL REVIEW" (post-
    deployment corrections on top of deployed PILOT-RELEASE-2); PLAN records
    the same state (AD-061..AD-062, §26.11-26.15). Consistent.
  - The deployed production runtime SHA (`065320180c17b89c7460164326a0c9f49e01fe3b`)
    predates the audited SHA (`55d1879a03da3dc6163a28c9524b5ef0396b76b3`); the
    audit documents the audited HEAD as required. The caching/freshness
    architecture conclusions above hold for the deployed runtime as well
    (no cache layer exists in either).
  - Baseline full-suite run shows 10/5633 failures, all within the documented
    11-node environmental flake allowlist (WinError 6 subprocess class);
    isolated retry reproduced the same signature (sustained in this session),
    matching STATUS's "may fail independently between runs" description.
    No node outside the allowlist fails.

**Audit complete. No implementation performed. STOP.**
