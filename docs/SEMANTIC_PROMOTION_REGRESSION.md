# Semantic PRIMARY Promotion-Regression Harness

**Phase:** PRODUCT-INTEL.SEMANTIC-QWEN38-PROMOTION-REGRESSION-A1
**Status:** IMPLEMENTED / APPROVED / FROZEN (independent review;
frozen at `b26b50e4a5ea1ae6be7fae4e8d680a6d3a880331`). This facility's
frozen evidence was the input to the separately reviewed B1 production
PRIMARY promotion (PRODUCT-INTEL.SEMANTIC-QWEN38-PRODUCTION-PROMOTION-B1,
PLAN §26.17), after which `amax/qwen3.8-27b` IS the production primary.
At A1 itself, no promotion was decided.

## What this is

A separate, explicit, **evaluation-only** promotion-regression facility for
semantic PRIMARY candidates. It answers:

> If a formally qualified challenger were considered for the production
> PRIMARY role, can we test it against production-shaped
> semantic/execution authority boundaries **without changing the
> production route**?

It is NOT:

* authorization to promote `amax/qwen3.8-27b` into production;
* a change to semantic policy, prompt, parser, or route;
* an attempt to improve any model's qualification score;
* a winner selector.

## Qualification vs promotion regression (separate concepts)

| | Qualification | Promotion regression |
| --- | --- | --- |
| Corpus | `evaluation/semantic_corpus/cases.json` (64 cases, frozen, SHA256 `3c21d6fc…`) | `evaluation/semantic_promotion_regression/cases.json` (22 cases, v1) |
| Runner | `product_intelligence/evaluation/semantic/runner.py` | `product_intelligence/evaluation/semantic/promotion_regression.py` |
| Question | Does the model pass the frozen benchmark? | Does the model respect the production authority boundaries in production-shaped cases? |
| Verdict | Qualification gates + leaderboard | Objective promotion-gate facts + mandatory human-review list. **No winner.** |

**`qwen3.8-27b` passing FULL qualification does not itself change
production.** At A1 the production route remained pinned:

```
PRIMARY   amax / nemotron-3-super      (historical, pre-B1)
FALLBACK  vllm-262k / Qwen3.6-27B-262K
temperature 0.0, max_tokens 32768
```

The regression comparison is EVIDENCE for a later human-reviewed promotion
decision. That decision was taken separately: the B1 phase (PLAN §26.17)
promoted `amax/qwen3.8-27b` to production PRIMARY, based on the frozen
FULL qualification, the A1 live promotion regression (22 processed /
16 semantic-called cases, both models passing all six objective gates),
and human review of the two surfaced disagreements (SPR-0009, SPR-0020 —
both closed as no promotion blocker). The production FALLBACK is
UNCHANGED (`vllm-262k/Qwen3.6-27B-262K`); Nemotron remains a
qualified/reference model but is NOT the production fallback (it shares
provider `amax` with the primary, and the fallback exists for
provider-level execution redundancy).

## Architecture under test (preserved, not bypassed)

```
deterministic matching      real assess_listing_identity (frozen 2A/3C)
        |
        v
semantic eligibility        frozen FU3B states (public research predicate
                            is_human_review_eligible_assessment) + title gate
        |
        v
semantic model              ONE injected transport attempt per eligible case,
                            prompt v1.1 (shared contract), strict contract
                            parser, exact model-identity proof
        |
        v
semantic decision           MATCH / NO_MATCH / UNCERTAIN or bounded failure
        |
        v
execution disposition       MATCH -> AI_ASSISTED_MATCH (AI-assisted evidence
                            only); NO_MATCH / UNCERTAIN -> UNDECIDED, no
                            authority. The deterministic assessment is never
                            mutated.
```

The harness reuses the production objects (prompt builder, strict parser,
eligibility predicate, transport factory, frozen status mapping); a test
suite locks every reuse against the frozen originals. Production never
imports the harness (enforced by a source scan).

The one authorized evaluation->research dependency: the harness
(`product_intelligence/evaluation/semantic/promotion_regression.py`)
imports the REAL deterministic identity chain
(`research.matching.assess_listing_identity` and the public eligibility
predicate) under an architecture-reviewer authorized EXACT one-file
allowlist in
`tests/research/test_research_identity_boundaries.py` (`PROMOTION_REGRESSION_RESEARCH_EXCEPTION`):
`product_intelligence/evaluation/semantic/promotion_regression.py`.
(Reviewer history: authorized and exacted as a two-file allowlist in
A1-FU1; tightened to least privilege in A1-FU2.)
`promotion_regression_cli.py` receives NO exception because it does
not directly depend on research — it consumes the harness module. No
other evaluation module — including the CLI and any future
`promotion_regression_*` file — may import `product_intelligence.research`
without a NEW explicit reviewer decision.

## Production authority invariants protected by the harness

1. Deterministic ACCEPTED is never sent to semantic evaluation.
2. Explicit authoritative MPN conflict cannot be overturned by semantic
   (no model call exists to overturn it).
3. Semantic evaluation occurs only for candidates already eligible under
   the frozen semantic eligibility rules.
4. Semantic MATCH remains AI_ASSISTED_MATCH — never deterministic ACCEPTED.
5. Semantic NO_MATCH / UNCERTAIN create no AI-assisted MATCH authority.
6. Semantic output does not alter deterministic matching records.
7. AI-assisted evidence stays outside canonical 4A aggregation (re-proven
   per MATCH record against the frozen `aggregate_listing_prices`).
8. Semantic output fabricates no human confirmation (no review state, no
   HUMAN_CONFIRMED in any artifact).
9. Semantic output does not bypass HARD_CONFLICT (frozen domain
   working-quote policy re-proven for identity-critical conflicts).
10. Semantic output does not create Reviewed Price authority by itself.
11. Production fallback semantics remain execution-failure-only, never
    semantic disagreement (frozen runtime re-proven; the non-pinned
    production model — since B1 the demoted former primary
    amax/nemotron-3-super — is rejected by the frozen
    `validate_runtime_config` in either seat and cannot even be named as
    the requested primary in a `SemanticRuntimeResult`).
12. No caller-configurable model override was introduced into the frozen
    production `SemanticRuntime`; the harness builds its own
    evaluation-only transport configuration.

## Promotion gates (objective facts, no winner)

A run's promotion gate FAILS if any of these occur:

* invalid output that violates the required model response contract
  (malformed JSON, schema violation, empty response, model-identity
  mismatch, or any transport-level failure on a called case);
* false MATCH on an explicit authority-conflict case (structurally: any
  semantic call on a no-call case is a gate failure —
  `no_semantic_override_of_deterministic_authority`);
* false MATCH on an accessory/compatibility/identity-conflict hard negative
  (corpus-declared `match_is_unsafe` cases — `no_unsafe_match`);
* any attempt to semantically override deterministic authority (missed or
  extra transport calls);
* any leakage of an AI-assisted result into deterministic/canonical
  authority (`ai_assisted_authority_boundary`);
* provenance incompatibility/corruption (`provenance_integrity` +
  load-time verification).

Model disagreements outside the hard safety cases are surfaced for human
review, not auto-failed:

* **positive authority expansion** — challenger MATCH while the production
  primary said NO_MATCH or UNCERTAIN: a MANDATORY human-review condition
  (the challenger is expanding positive authority relative to production);
* **conservative challenger regression** — primary MATCH while the
  challenger said NO_MATCH or UNCERTAIN: a recall-loss flag for review.

## Usage (HUMAN-executed live commands)

Live runs require the amax provider environment
(`PI_SEMANTIC_AMAX_BASE_URL` / `PI_SEMANTIC_AMAX_API_KEY`), exactly as the
production runtime and the qualification CLI use it. No harness-specific
environment variable selects a production model: the model is a CLI
argument validated against the explicit authorization list.

```bash
# 0. (optional) list the regression corpus
python -m product_intelligence.evaluation.semantic.promotion_regression_cli list-cases

# 1. current production-primary run (since B1)
python -m product_intelligence.evaluation.semantic.promotion_regression_cli run --provider amax --model qwen3.8-27b

# 2. reference baseline run (demoted former primary; still an authorized harness spec)
python -m product_intelligence.evaluation.semantic.promotion_regression_cli run --provider amax --model nemotron-3-super

# 3. compare the two run directories (print the paths shown by steps 1-2)
python -m product_intelligence.evaluation.semantic.promotion_regression_cli compare <primary_run_dir> <challenger_run_dir>
```

Exit codes: `0` gate PASS / comparison produced with both gates PASS;
`2` promotion gate FAIL or provenance-incompatible comparison; `1`
operational error.

Artifacts (gitignored, under `semantic_promotion_regression_runs/`):

```
<ts>__amax_nemotron-3-super--<hash>/   manifest.json, results.jsonl, summary.md
<ts>__amax_qwen3.8-27b--<hash>/        manifest.json, results.jsonl, summary.md
<ts>__comparison__…__…/                comparison.json, comparison.md
```

`comparison.json` is machine-readable with per-case rows (case ID, category,
expected authority outcome, both decisions, confidences, validity,
disagreement flags, unsafe/false MATCH flags, reason codes, bounded
provenance) and carries `"no_winner_declared": true`.

## What a live run does NOT do

* does not change the production route or any production constant;
* does not add any model as a production fallback (the production
  fallback remains the frozen `vllm-262k/Qwen3.6-27B-262K`; since B1 the
  production primary is `amax/qwen3.8-27b`, and neither is selectable
  through the harness);
* does not retry invalid outputs (the first response is the recorded
  response);
* does not fall back between models (each model is tested in the PRIMARY
  seat with exactly one attempt per eligible case — production fallback
  semantics remain frozen and are the production runtime's contract, not
  the harness's);
* does not declare a winner.
