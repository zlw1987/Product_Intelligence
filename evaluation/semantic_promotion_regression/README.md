# Semantic PRIMARY Promotion-Regression Corpus

**SEPARATE from the frozen semantic QUALIFICATION corpus**
(`evaluation/semantic_corpus/cases.json`, 64 cases, version 2, SHA256
`3c21d6fcd4eefa5cc383792abfd9308bd5c03315834c8ffdffd0f6a2b3619ca1`).

Two different questions, two different facilities:

| | Qualification (frozen) | Promotion regression (this corpus) |
| --- | --- | --- |
| Question | Does the model pass the frozen 64-case benchmark? | If a formally qualified challenger were considered for the production PRIMARY seat, does it respect the production semantic/execution authority boundaries? |
| Cases | Model-level expected decisions only | Production-shaped: real deterministic state + real FU3B eligibility + expected decision |
| Matcher | Not involved (declared evidence sources) | Real `assess_listing_identity` runs for every case |
| Transport | Qualification runner (FULL/SMOKE) | Harness single-attempt PRIMARY-seat loop |
| Verdict | Qualification gates (leaderboard) | Promotion gate facts + human-review list; **no winner** |

Passing FULL qualification (as `amax/qwen3.8-27b` did) does NOT change the
production route. This corpus measures the OTHER risk: a qualified challenger
expanding positive authority in production-shaped situations the qualification
corpus does not exercise (deterministic ACCEPTED, explicit MPN conflict,
no usable evidence, accessory traps, attribute conflicts, disposition
mapping).

## Status at corpus v1

- 22 cases, categories A..J (each category present by loader enforcement)
- 16 semantic-called cases (MATCH x5, NO_MATCH x6, UNCERTAIN x5)
- 6 no-call cases (deterministic ACCEPTED x2, MPN_MISMATCH x2, no usable
  evidence x2)
- All cases are `synthetic` provenance; product identities are generic and
  deliberately do NOT copy the frozen SMQ-0053 / SMQ-0062 error cases
  (category I encodes the same GENERIC contract — normalized exact identity
  plus trailing description — with different identities and wording)

## Case schema

```json
{
  "case_id": "SPR-0005",
  "category": "C",
  "category_name": "title_text_semantic_eligible",
  "title": "...",
  "target": { "manufacturer_part_number": "...", "description": "..." },
  "candidate": {
    "product_title": "...",
    "manufacturer_part_number_text": null,
    "sku_text": null,
    "brand_text": "...",
    "condition_text": "new"
  },
  "expected_deterministic": {
    "decision": "REJECTED",
    "rejection_reason": "NO_EXPLICIT_MPN_EVIDENCE",
    "evidence_source": "TITLE_TEXT",
    "match_type": "UNKNOWN"
  },
  "expected_semantic_call": true,
  "expected_semantic_decision": "MATCH",
  "match_is_unsafe": false,
  "critical_reason": "...",
  "provenance": "synthetic"
}
```

- `expected_deterministic` is verified against the REAL frozen authority
  chain at run time; a case whose production shape does not reproduce fails
  the run closed (a defective case measures nothing).
- `expected_semantic_call` must equal the frozen FU3B eligibility states +
  the usable-evidence (title) gate; the harness verifies this too.
- `expected_semantic_decision` is a GENERIC product-identity contract (prompt
  v1.1 decision precedence), never a model-specific patch. It is used only to
  compute model-quality facts (false match, unsafe match) and the mandatory
  human-review list — it does not gate the production architecture.
- `match_is_unsafe`: a model MATCH on this case is an unsafe positive-authority
  expansion (accessory/compatibility traps, hard identity-attribute conflicts).
  This is a corpus-declared fact; the harness contains no per-case-ID logic.

## Categories (phase requirement A..J)

- **A** `deterministic_accepted` — deterministic ACCEPTED; semantic must NOT be
  consulted; deterministic result remains authoritative.
- **B** `mpn_conflict` — authoritative explicit MPN_MISMATCH; semantic must
  NOT overturn it; the candidate can never become AI_ASSISTED_MATCH.
- **C** `title_text_semantic_eligible` — no explicit MPN; usable TITLE_TEXT.
- **D** `sku_field_semantic_eligible` — no authoritative explicit MPN; usable
  SKU_FIELD.
- **E** `partial_mpn_semantic_eligible` — PARTIAL_MPN_ONLY; result stays
  AI-assisted only.
- **F** `no_usable_evidence` — semantic must NOT be called (source NONE, or
  eligible state but no product title).
- **G** `accessory_compatibility_trap` — accessory / compatible-with /
  replacement / multipack relationships; the promotion risk is a challenger
  MATCH where the safe decision is NO_MATCH or UNCERTAIN.
- **H** `identity_attribute_conflict` — concrete capacity / form-factor /
  interface conflicts.
- **I** `normalized_identity_trailing_description` — generic normalization and
  descriptive-title-wording vs actual identity contract (NOT copies of
  SMQ-0053/SMQ-0062).
- **J** `decision_mapping` — verifies the MATCH / NO_MATCH / UNCERTAIN
  production disposition semantics are all exercised by the corpus.

## Rules

- Changing a case's `expected_deterministic` or `expected_semantic_call` is a
  change to the production-shaped boundary under test: it requires a reviewed
  phase decision, not a benchmark convenience.
- Changing an `expected_semantic_decision` requires the same standard as the
  qualification corpus: (A) the old expectation was factually wrong,
  (B) the authoritative source changed, (C) the case definition was
  ambiguous, or (D) the product behaviour requirement intentionally changed.
  "The challenger failed this case" is NOT a valid reason.
- This file is versioned; the harness fingerprints it (corpus SHA256) into
  every run manifest, and comparisons fail closed on mismatch.
