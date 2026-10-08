# Semantic V2 Qualification Corpus (Q3-A)

The independent, deterministic, offline qualification corpus for the
exact frozen Semantic V2 contract
(`("V2", "2.0", 1, 1, "SEMANTIC_AUTHORITY_V2_S2A_FU2")`).

Established by **PRODUCT-INTEL.SEMANTIC-AUTHORITY-V2-Q3-A**.

## What this is (and is not)

* A **versioned benchmark corpus**: cases with frozen V2 input payloads
  and INDEPENDENTLY established expected semantic decisions, conflict
  classes, and missing-critical attributes;
* A **digest-sealed artifact**: `corpus_v1.json` carries
  `corpus_digest` (SHA-256 over the canonical state view) and per-case
  `case_digest`. Any label mutation changes the digest; historical
  reports remain bound to their original corpus digest and fail
  verification against a mutated corpus;
* **NOT** a model evaluation (Q3-A runs no live model qualification),
  **NOT** production authority (the V2 route stays
  `V2_AUTHORITY_QUALIFIED = False`), and **NOT** real-market accuracy
  evidence beyond what is cited per label.

## Layout

```text
evaluation/semantic_v2_qualification/
  corpus_v1.json                          the sealed corpus (56 cases)
  manifest_v1.json                        reproducible per-case manifest
  policy/qualification_policy_draft_1.json  DRAFT thresholds (not approved)
  README.md                               this file
```

The auditable SOURCE of the corpus is
`product_intelligence/evaluation/semantic_v2/fixtures.py` (declarative
case definitions that run the EXACT frozen chain: `ResearchRequest ->
ListingObservation -> normalize_listing_observation ->
assess_listing_identity -> derive_identity_state_v2 ->
build_semantic_match_case_v2`). Regenerating from the source must
reproduce `corpus_v1.json` byte-for-byte (proven by test); the sealed
JSON is the artifact the harness measures.

## Case taxonomy

* **case_class**
  * `AUTHORITATIVE` — independently supported label, used for hard
    qualification metrics and safety gates;
  * `AMBIGUOUS` — legitimately disputed or insufficiently supported
    label; carries an `acceptable_decisions` set (>= 2). Visible in
    reports; excluded from hard accuracy; never silently forced to
    MATCH or NO_MATCH;
  * `CONTRACT_NEGATIVE` — invalid state / schema violation /
    authority-boundary attack; the expected outcome is rejection by
    the frozen V2 input contract (bounded `rejection_class`),
    evaluated separately from semantic accuracy. A model response for
    such a case is a schema-bypass attack (hard safety gate).
* **evidence_kind**
  * `SYNTHETIC` — by-construction scenario (clearly synthetic MPNs and
    listings). Tests known contracts; NEVER real-market accuracy
    evidence;
  * `RECORDED_FIXTURE` — grounded in a recorded in-repository source
    (the recorded 4D-D Micron 7500 part-catalog fixture; the recorded
    project-UAT V1 semantic corpus `evaluation/semantic_corpus/`);
  * `REAL_MARKET` — reserved; corpus 1.0.0 ships no real-market cases
    (the loader rejects them: a real-market label requires an
    independently retrieved market source, which Q3-A does not
    fabricate).
* **input_shape**
  * `LIVE_SHAPE` — exactly what the live main-flow builders emit today
    (brand as the only structured product fact; packaging channel
    UNAVAILABLE; no specification text);
  * `CONTRACT_SURFACE` — exercises the full frozen input surface the
    live path does not emit yet (observed packaging / sales unit,
    raw specification text). Built through the same real
    `SemanticMatchCaseV2` constructor; no approximation.

## Ground-truth governance (binding)

Every case carries: stable case id, category, frozen input payload,
deterministic substate / primary signal, expected decision (and the
acceptable set for ambiguous cases), expected conflict classes,
expected missing-critical dimensions, expected reason code (advisory),
the commercial-sales-unit-safety flag, label source kind
(`CONTRACT_GROUNDED` / `PRODUCT_KNOWLEDGE_GROUNDED` /
`REVIEWED_SOURCE_GROUNDED`), explicit source citation, the independent
evidence supporting the label, reviewer identity + status, ambiguity
classification, and the case digest.

* Ground truth is NEVER derived from the candidate model's output:
  the loader mechanically rejects label text naming model output or a
  candidate model, and the corpus build never reads any capture file;
* A synthetic scenario is labeled synthetic; its label is established
  by construction + the frozen contract, not by pretending to be a
  real market listing;
* Changing an expected label requires: (1) a `label_revisions` entry
  with the bounded reason class (A: old expectation factually wrong;
  B: authoritative source changed; C: case definition was ambiguous;
  D: product behaviour requirement intentionally changed), (2) a new
  corpus digest, (3) a reviewer identity; the historical report
  against the old digest remains bound to it and fails verification
  against the new corpus.

## The motivating Micron case

Target `MTFDKCC3T8TGP-1BK1DABYYR` vs candidate
`MTFDKCC3T8TGP-1BK1DABYY` (case `V2Q-SSD-U5NM1-MICRON-0018`):

* the candidate's published MPN is the exact recorded-catalog part
  ("7500 4TB U.3 SSD");
* the requested form differs by a truncated final "R" (bounded
  NEAR_MISS_TRUNCATION, U5);
* the R/T family relation is a CUSTOMER-DEFINED retrieval rule — no
  manufacturer document states what the final R suffix denotes (the
  recorded 4D-D rule says so explicitly);
* therefore physical-product family membership is grounded while
  commercial sales-unit comparability is UNPROVEN;
* the independent expected decision is **UNCERTAIN** with
  `PACKAGING_QUANTITY` named missing — the pair is NOT labeled
  equivalent merely because it shares a base identifier; a false
  MATCH is the commercial-safety error (severity CRITICAL via the
  case's `commercial_sales_unit_safety` flag).

## Commands (offline)

```cmd
python -m product_intelligence.evaluation.semantic_v2.cli corpus-build --out-dir evaluation/semantic_v2_qualification
python -m product_intelligence.evaluation.semantic_v2.cli corpus-digest --corpus evaluation/semantic_v2_qualification/corpus_v1.json
python -m product_intelligence.evaluation.semantic_v2.cli corpus-manifest --corpus evaluation/semantic_v2_qualification/corpus_v1.json --out evaluation/semantic_v2_qualification/manifest_v1.json
python -m product_intelligence.evaluation.semantic_v2.cli evaluate --corpus evaluation/semantic_v2_qualification/corpus_v1.json --policy evaluation/semantic_v2_qualification/policy/qualification_policy_draft_1.json --out-dir <reports dir> --generated-utc <ISO-8601Z>
python -m product_intelligence.evaluation.semantic_v2.cli evaluate --corpus <corpus> --policy <policy> --capture <capture.json> --out-dir <dir> --generated-utc <ISO-8601Z>
python -m product_intelligence.evaluation.semantic_v2.cli verify-report --report <report.json> --corpus <corpus>
```

`evaluate` without `--capture` produces the explicit no-capture
baseline for both pinned route candidates (every eligible case
`NOT_CAPTURED`; decision `INCOMPLETE_COVERAGE` / `POLICY_PENDING` —
never a pass). With captures, one report per provider/model: the
primary and the fallback are qualified INDEPENDENTLY (a
primary-model PASS never qualifies the fallback).

## Capture artifact contract (for the later live phase)

The offline harness evaluates PREVIOUSLY CAPTURED model responses.
The strict format (schema version 1) is defined in
`product_intelligence/evaluation/semantic_v2/capture.py`: one document
per pinned model, bound to the exact corpus digest, bounded
per-attempt provenance mirroring the frozen runtime (fallback on
execution failure only; raw output only for OK attempts). Q3-A ships
no captures (no live V2 responses exist yet) — test fixtures exercise
the format in the suite.
