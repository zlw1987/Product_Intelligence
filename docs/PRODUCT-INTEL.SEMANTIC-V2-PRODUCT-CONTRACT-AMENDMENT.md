# PRODUCT-INTEL.SEMANTIC-V2 — Product-Contract & Architecture-Impact Amendment

> **Document role.** This is a bounded **contract amendment** for ChatGPT
> product / architecture review. It is **design only**: no implementation,
> no test changes, no corpus labels, no schema, no qualification promotion,
> no V2 pricing-authority activation, and no change to the existing security
> or integrity constraints. The artifact restates the corrective product
> direction, audits it against the actual frozen architecture and extraction
> capabilities, defines the contract delta, names measurable success criteria,
> and lists the minimum viable changes (MVC) with their phase dependencies.
>
> Frozen-phrase reference. Where this document uses a phrase that already
> has a binding definition in `CLAUDE.md`, `docs/PRODUCT_INTELLIGENCE_PLAN.md`,
> or `docs/PRODUCT_INTELLIGENCE_STATUS.md`, the binding definition
> controls; this document does not redefine it.

---

## 0. Status of this artifact (gate)

| Property | Value |
| --- | --- |
| Phase | Pre-design — product-contract amendment for ChatGPT review |
| Implementation | **None.** No code, no test, no migration, no corpus label, no authority flag, no schema, no pricing wiring, no prompt, no model call, no seal artifact, no qualification. |
| Dependents | None. This amendment does not modify `CLAUDE.md`, `PRODUCT_INTELLIGENCE_STATUS.md`, or `PRODUCT_INTELLIGENCE_PLAN.md`. Status / PLAN update happens only under a later approved implementation phase. |
| Authority state of record (carried over, unchanged) | `V2_AUTHORITY_QUALIFIED = False`, `V2_PERF_AUTHORITY_QUALIFIED = False`, FU2 Option B **NOT YET APPROVED**, FU4 Bundle authority program state **UNAPPROVED / NOT EXECUTED**, C2 corpus state **DRAFT ACCEPTED / FINAL HOLD**, v1.0.0 seal **FINAL-HOLD**. |
| Deployment security | F-2 ambient `PI_VENDOR_PRICE_ALLOWED_CIDRS` HOLD **OPEN** — untouched. |

---

## 1. Authoritative product goal (re-statement, scope-bounded)

Semantic V2 is intended to **replace** Semantic V1 as the primary
intelligent matching and review engine for Product Intelligence.

The business problem it must solve is **insufficient usable comparable
samples**, driven by overly restrictive identity filtering and review
eligibility, with four named real customer scenarios:

| # | Scenario | Deterministic 3C behavior today | Semantic V2's potential role |
| --- | --- | --- | --- |
| 1 | Requested MPN appears in listing **title** but no explicit structured MPN field exists. | `REJECTED` + `NO_EXPLICIT_MPN_EVIDENCE` + `TITLE_TEXT`. Today, **V2-eligible** (U1_TITLE_MPN uncertain substate) and human-review-eligible. | Evaluate as an **advisory** MATCH / VARIANT / NON_MATCH candidate; surface as a review candidate. Never auto-accept. |
| 2 | Candidate MPN is **missing**, but product description and independently supported specifications are strongly consistent with the requested product. | `REJECTED` + `NO_EXPLICIT_MPN_EVIDENCE` + `NONE`. Today, **NOT V2-eligible** and NOT human-review-eligible. | A new V2-eligibility substate is required; admissible evidence is sourced from the FU3A semantic runtime's bounded evidence collection (not from arbitrary main-flow fields). Advisory only. |
| 3 | Candidate MPN differs by a **suffix** that may represent color, cosmetic appearance, or another non-critical variation. | Most cases: `REJECTED` + `MPN_MISMATCH` (today, NOT V2-eligible). Some: `PARTIAL` (`REJECTED` + `PARTIAL_MPN_ONLY`, today V2-eligible and human-review-eligible). | Treat as a **V2-advisory VARIANT candidate** when supported by independent evidence (FU3A semantic runtime's bounded collection). **Never** treat arbitrary MPN suffix similarity as proof of equivalence. **Never** auto-accept. |
| 4 | A genuinely different product / accessory / bundle / capacity / interface / generation / sales unit must still be handled safely. | `REJECTED` + `MPN_MISMATCH` or `PARTIAL_MPN_ONLY`, or `REJECTED` + bundle/capacity conflict (frozen Bundle-axis). | The frozen conflict precedence `HARD_CONFLICT > HUMAN_CONFIRMED > AI authority` is **preserved**. V2 advisory cannot override a hard safety conflict and cannot silently alter Machine Price. |

**Direction the amendment confirms:**

* Broader V2 candidate evaluation (subject to §3 audit and §4 contract).
* Evidence-grounded matching and variant classification.
* V2-backed human review candidates (V2 advisory proposes; human confirms).
* User-confirmed inclusion in Reviewed Price and comparison workflows
  (already the frozen HUMAN-REVIEW path: `runs/ai_assisted_review.py`,
  `aggregate_reviewed_listing_prices`, the Compact-Quote HUMAN_CONFIRMED
  overlay — preserved unchanged).
* **Qualified** automatic inclusion **only** after independent approval
  (the existing FU4 / C3 / E1 / E2 / P1 / Q1 / W1 qualification gates,
  none of which are open or approved today).
* Historical V1 compatibility, replay, and test preservation (every frozen
  test remains byte-pinned; V1 codec, V1 snapshot decoder, V1 replay
  boundary — preserved unchanged).

---

## 2. Architectural requirement (identity vs business-valid comparability)

The amendment draws a single sharp line that is **already binding** and is
only restated here for product-clarity:

> **Exact product identity** is established exclusively by the frozen
> deterministic authority (2A comparator + 3C matching + frozen
> constructor invariants — `compare_part_numbers` returning `EXACT` or
> `NORMALIZED_EXACT` over an explicit MPN field or the bounded visible
> labeled MPN field, per `ListingIdentityAssessment.__post_init__`).
> Deterministic authority is automatic, exact, and never overridable by
> V2.
>
> **Business-valid price comparability** is a different question. It is
> established by an independent, evidence-grounded chain — frozen
> conflict precedence `HARD_CONFLICT > HUMAN_CONFIRMED > AI authority`
> (PLAN §26.21 / §26.22 / §26.26 / §26.27) and frozen 4A / 4B /
> HUMAN-REVIEW bucket arithmetic — and **V2 MATCH is advisory on this
> chain, never authoritative**.

Therefore:

* A V2 MATCH never automatically overrides a hard safety conflict
  (HARD_CONFLICT supersession is preserved; the S2-A matrix and the
  `ALWAYS_HARD_CONFLICT_CLASSES` are preserved).
* A V2 MATCH never silently alters Machine Price
  (`PriceIntelligenceSnapshot` is the frozen authoritative artifact;
  HUMAN-REVIEW's `aggregate_reviewed_listing_prices` is the only path
  that may add HUMAN_CONFIRMED rows to a Reviewed Price bucket; V2 has
  no such path).
* A V2 MATCH never becomes `EvidenceDecision.ACCEPTED`
  (CLAUDE.md / PLAN §16.3 / `runs/ai_assisted_review.py` are explicit:
  "Confirming a candidate NEVER changes EvidenceDecision to ACCEPTED").
* A V2 MATCH never causes a deterministic-identity-eligible listing to
  become ineligible (V2 can only ADMIT additional human-review candidates,
  not strip currently-eligible ones).

The amendment therefore proposes **advisory, evidence-grounded** V2
expansion, not V2 replacement of deterministic identity.

---

## 3. Audit of current extraction and evidence capabilities (the real main flow)

The direction document explicitly directs: *"Do not assume descriptions
or structured specification fields exist in the current main-flow input.
Audit the real extraction and evidence capabilities before designing
matching authority."*

This audit is binding for the amendment.

### 3.1 What the main flow actually carries into the 3C matching step

Source of truth: `product_intelligence/research/listings.py`,
`NormalizationIssue`, the `NormalizedListingObservation` / `ListingObservation`
contract, and `research/matching.py::_find_evidence`.

| Evidence source | Main-flow field | Today in 3C | Today in semantic V2 evidence collection |
| --- | --- | --- | --- |
| `EXPLICIT_MPN_FIELD` | `manufacturer_part_number_text` from structured JSON-LD / meta | ACCEPTED path on EXACT / NORMALIZED_EXACT | `PUBLISHED_STRUCTURED_FIELD` |
| `VISIBLE_LABELED_MPN_FIELD` | Bounded visible labeled MPN enrichment (`JSON_LD_WITH_VISIBLE_MPN`, `META_WITH_VISIBLE_MPN`) | ACCEPTED path on EXACT / NORMALIZED_EXACT | `PUBLISHED_STRUCTURED_FIELD` |
| `SKU_FIELD` | `sku_text` | REJECTED + NO_EXPLICIT_MPN_EVIDENCE (recorded) | U2_SKU_ONLY substate (today model-side observation; main flow builder emits no SKU-derived fact — `CandidateEvidenceSourceV2` has no SKU member) |
| `TITLE_TEXT` | `product_title` (token-substring match only) | REJECTED + NO_EXPLICIT_MPN_EVIDENCE (recorded) | U1_TITLE_MPN substate; today the live main-flow builder emits **no** title-derived fact — `LISTING_TITLE` is **RESERVED** in `CandidateEvidenceSourceV2` |
| `NONE` | No candidate identifier was found | REJECTED + NO_EXPLICIT_MPN_EVIDENCE | NOT V2-eligible today; U4_NO_MPN substate is admitted only when a primary signal exists (TITLE_MPN_TOKEN or SKU_EQUALS_REQUESTED) |
| Product description / specification text | Not carried by 3C; not read by `assess_listing_identity`; "Any future description/category/comparable semantic interpretation belongs to a later explicitly approved phase" (PLAN §16.3). 6A / 6B / 6C framework contracts exist; **6A is not implemented**; 6B implements the Enterprise SSD category schema (frozen); 6C implements deterministic structured extraction. The main flow today does **not** carry a description or specification payload into semantic V2. | n/a (description not read) | `SPECIFICATION_TEXT` is **RESERVED**; `REVIEWED_PRODUCT_CONTEXT` is **RESERVED** |

**Implication for the direction's four scenarios:**

1. **Title-MPN (scenario 1).** The main flow already carries the title token
   and routes this case to U1_TITLE_MPN. Today the V2 advisory path exists
   (FU3A semantic runtime); what changes is the **evidence-collection
   payload** — the FU3A prompt / bounded observation set needs to surface
   sufficient title + listing text to support an advisory MATCH / NON_MATCH.
2. **Missing-MPN with description + spec consistency (scenario 2).** The
   main flow does **not** carry description or specification text into V2
   evidence collection today. For V2 to admit these cases at all, the FU3A
   bounded evidence collection must be the source — the V2 model observes
   a bounded structured set, not arbitrary text. This is an SV2-A
   contract delta in §4, not an architectural re-design.
3. **Cosmetic suffix variant (scenario 3).** The main flow already handles
   PARTIAL boundary (`U3_PARTIAL_BOUNDARY`) via 3C's narrow prefix rule.
   For *non-boundary* suffix variants (e.g. `MTFDKCC1T9TGP-1BK1DABYY` vs
   `MTFDKCC1T9TGP-1BK1DABYYR`), the deterministic answer is MPN_MISMATCH
   and **not** V2-eligible today. Admitting them requires a new substate
   (V5_VARIANT_SIMILARITY or similar) — see §4. **Arbitrary** MPN suffix
   similarity is **not** identity evidence; this admission is conditioned on
   independent evidence (manufacturer documentation or operator attestation),
   never on edit-distance or character-similarity heuristics.
4. **Genuinely different product (scenario 4).** No new admission. The
   frozen conflict precedence and the `ALWAYS_HARD_CONFLICT_CLASSES`
   precedence (`CAPACITY`, `INTERFACE`, `GENERATION`, `SALES_UNIT`,
   `BUNDLE`, `FAMILY`) are preserved.

### 3.2 What the FU3A / FU3B semantic runtime already carries

`product_intelligence/research/semantic_v2.py` defines bounded candidate
observation facts with provenance (`CandidateEvidenceSourceV2`) and a
frozen S2-A derived state vocabulary. The semantic runtime already
admits the five uncertain substates (`U1_TITLE_MPN`, `U2_SKU_ONLY`,
`U3_PARTIAL_BOUNDARY`, `U4_NO_MPN`, `U5_NEAR_MISS_MPN`). What is missing
for scenarios 2 and 3 is **not the admission** (U4_NO_MPN is admitted
when a primary signal exists) — it is the **bounded observation surface**
the model can draw on. The amendment proposes this be addressed in §4
as SV2-A.

### 3.3 What frozen phases forbid the amendment from changing

| Frozen phase | Cannot be changed by this amendment | Source |
| --- | --- | --- |
| 2A / 2A-FU1 deterministic comparator | The normalization profile; EXACT/NORMALIZED_EXACT/UNKNOWN outcome; "no fuzzy matching, edit distance, similarity score, embedding, or model call". | PLAN §12.1, §12.3; `research/identity.py`. |
| 3C matching | The four-decision vocabulary; the `ACCEPTED`-requires-`EXPLICIT_MPN_FIELD` or `VISIBLE_LABELED_MPN_FIELD` rule; PARTIAL classification; the "no description semantics" rule. | PLAN §16.3; `research/matching.py`. |
| 4A aggregation | The bucket vocabulary; the inclusion/exclusion rules; Machine Price derivation. | PLAN §16.4; `research/aggregation.py`. |
| 4B snapshot | `PriceIntelligenceSnapshot` immutability; the V1 codec (`decode_price_aggregation_result`); the read-only GET. | PLAN §16.5; `research/price_result_codec.py`. |
| FU3A / FU3B semantic runtime | The S2-A derived state vocabulary; the conflict precedence `HARD_CONFLICT > HUMAN_CONFIRMED > AI authority`; the `ALWAYS_HARD_CONFLICT_CLASSES`; the bounded observation fact provenance; the advisory nature of any V2 MATCH. | PLAN §26.21–§26.27; STATUS (FU3A/FU3B). |
| HUMAN-REVIEW | The review-state machine (`UNREVIEWED → CONFIRMED / REJECTED → UNREVIEWED`); the candidate-to-assessment binding primitive (`is_review_candidate_binding_valid`); the rule that CONFIRMED is the **only** path to HUMAN_CONFIRMED and the rule that CONFIRMED never becomes `ACCEPTED`; the persisted snapshot authority at both replay boundaries (`replay_compact_quote_projection`, `replay_public_compact_quote_projection` — no caller-supplied index, no caller-supplied `PriceAggregationResult`). | PLAN §26.11 / §26.12; STATUS (HUMAN-REVIEW); `runs/ai_assisted_review.py`. |
| 4D / Compact Quote / Vendor | The Vendor Commercial Price Access Gate (4D-C-SEC); the FX cache contract (8A); the vendor paragraph envelope (FU3); the production-wire fidelity (FU1). | PLAN §26.9–§26.15. |
| Architecture guard tests | Layer boundaries (`web/` read-side research allowlist; `runs/` is the only Django model layer; provider / execution internals / `research/identity` import discipline); stdlib-only domain; no vendor names in business logic. | CLAUDE.md; `tests/web/test_web_boundaries.py`; architecture-guard test files. |

---

## 4. Bounded product contract amendments (the contract delta)

Each amendment is a **contract clause** (a documented rule change). It is
**advisory by default**: every clause that grants new admission to the
V2 advisory path is conditioned on the FU3A / FU3B bounded observation
contract and is **never** a path to `EvidenceDecision.ACCEPTED`. None of
the clauses below activate pricing authority, schema changes, or new
authority.

### 4.1 SV2-C1 — V2 advisory candidate classes (the new admission contract)

**New bounded V2 advisory candidate classes (advisory only, frozen):**

| Class | Triggering frozen state | Required V2 outcome | Admissible evidence |
| --- | --- | --- | --- |
| `V2_ADVISORY_TITLE_MPN` | REJECTED + TITLE_TEXT + NO_EXPLICIT_MPN_EVIDENCE; U1_TITLE_MPN | MATCH / VARIANT / NON_MATCH | Bounded title-token + listing-text observations (FU3A) |
| `V2_ADVISORY_SKU_FIELD` | REJECTED + SKU_FIELD + NO_EXPLICIT_MPN_EVIDENCE; U2_SKU_ONLY | MATCH / VARIANT / NON_MATCH | Bounded SKU + listing-text observations (FU3A) |
| `V2_ADVISORY_PARTIAL_BOUNDARY` | REJECTED + PARTIAL_MPN_ONLY; U3_PARTIAL_BOUNDARY | MATCH / VARIANT / NON_MATCH | Already bounded; preserved |
| `V2_ADVISORY_NO_MPN` | REJECTED + NO_EXPLICIT_MPN_EVIDENCE + NONE + a **primary signal present** (title token OR SKU equality) — the existing U4_NO_MPN substate | MATCH / VARIANT / NON_MATCH | Bounded observation set sourced from FU3A runtime (NOT from arbitrary main-flow text) |
| `V2_ADVISORY_VARIANT_SIMILARITY` | REJECTED + MPN_MISMATCH over an **independently attested variant relationship** (manufacturer documentation OR operator attestation; never edit-distance OR suffix-character heuristics) | VARIANT only (never MATCH) | Bounded observation set with the attested variant table (a frozen `VariantSimilarityTableV2` populated only from documented manufacturer or operator attestation; absent attestation → class does not fire) |

**Outcome vocabulary (the new V2 advisory return values, frozen):**

* `MATCH` — V2 advisory believes the candidate refers to the same product
  with **independent** evidence (FU3A bounded observation; never edit-distance).
* `VARIANT` — V2 advisory believes the candidate refers to a known
  non-identity product variant (color, cosmetic, packaging, sales unit
  variant). **`VARIANT` is never `MATCH`** — it is a distinct outcome
  and never enters the price bucket as identity.
* `NON_MATCH` — V2 advisory believes the candidate is not the requested
  product (the safe default).
* `INSUFFICIENT_EVIDENCE` — V2 advisory cannot reach a defensible conclusion
  on the bounded observation set; the candidate is not created.

**Hard guards (frozen):**

* A V2 outcome of `MATCH` over a `V2_ADVISORY_VARIANT_SIMILARITY` admission
  is **forbidden at the constructor** — the class admits `VARIANT` only.
* A V2 outcome of `MATCH` over `V2_ADVISORY_NO_MPN` is permitted only when
  the FU3A bounded observation includes **at least one independently
  attested product specification match** (e.g. capacity, interface,
  generation) — the `VariantSimilarityTableV2` rule for NON-identity
  variants is preserved; **never** over a description-only similarity.
* A V2 outcome cannot name `MATCH` over a hard conflict class
  (`CAPACITY`, `INTERFACE`, `GENERATION`, `SALES_UNIT`, `BUNDLE`,
  `FAMILY`). The conflict precedence is preserved.
* A V2 outcome cannot name `MATCH` over `EvidenceDecision.ACCEPTED` —
  no V2 evaluation runs against an already-accepted listing.

### 4.2 SV2-C2 — Human-review candidate admission (the review-boundary contract)

**New review-eligibility predicate (frozen, replaces the existing
`is_human_review_eligible_assessment` set membership via additive clauses):**

* The existing three predicates are **preserved** (TITLE_TEXT +
  NO_EXPLICIT_MPN_EVIDENCE; SKU_FIELD + NO_EXPLICIT_MPN_EVIDENCE;
  PARTIAL_MPN_ONLY).
* **Additive predicates** (new):
  * `V2_ADVISORY_VARIANT_SIMILARITY` (any V2 outcome) — review-eligible,
    but with an explicit "VARIANT — NOT identity" tag carried into the
    presentation. **CONFIRMED does not promote to `ACCEPTED`;** it
    promotes only to a `HUMAN_CONFIRMED_VARIANT` overlay that is
    **excluded** from the identity bucket and **excluded** from
    Machine Price arithmetic (4A bucket arithmetic is unchanged).
  * `V2_ADVISORY_NO_MPN` + V2 outcome `MATCH` (only when the
    independently-attested-specification guard in §4.1 holds) —
    review-eligible, CONFIRMED promotes to the standard HUMAN_CONFIRMED
    Compact-Quote overlay (the existing `aggregate_reviewed_listing_prices`
    path), without altering Machine Price.
  * `V2_ADVISORY_TITLE_MPN` + V2 outcome `MATCH`; `V2_ADVISORY_SKU_FIELD`
    + V2 outcome `MATCH`; `V2_ADVISORY_PARTIAL_BOUNDARY` + V2 outcome
    `MATCH` — review-eligible with the standard HUMAN_CONFIRMED overlay
    semantics, provided the FU3A bounded observation set is non-empty
    and the outcome is not an `INSUFFICIENT_EVIDENCE`.

**Hard guards (frozen):**

* A `VARIANT` confirmation is **never** an `ACCEPTED` and is **never**
  in a 4A price bucket; it is recorded as a labeled overlay only.
* The existing HUMAN_CONFIRMED / REVIEWED_PRICE arithmetic
  (`aggregate_reviewed_listing_prices`) is **unchanged**: HUMAN_CONFIRMED
  rows enter the reviewed bucket only when they pass the frozen
  eligibility and binding checks. The new clauses only **add** sources
  of HUMAN_CONFIRMED, never modify how a HUMAN_CONFIRMED row is treated.
* The persisted snapshot authority remains at both replay boundaries
  (no caller-supplied index; no caller-supplied `PriceAggregationResult`).

### 4.3 SV2-C3 — VariantSimilarityTableV2 (the attested-variant contract)

A frozen, append-only table of attested product-variant relationships,
populated exclusively from documented manufacturer sources or explicit
operator attestation; **never** from edit-distance, suffix-similarity,
character-similarity, embedding, or model inference.

* Read-side usage: only as a guard clause ("did the FU3A runtime's bounded
  observation set reference an attested variant?"); **never** as a
  similarity oracle.
* Write-side usage: append-only; every entry carries provenance
  (manufacturer URL + retrieval instant OR operator attestation +
  attestation instant + operator identity).
* Empty / absent: the `V2_ADVISORY_VARIANT_SIMILARITY` admission class
  does not fire; nothing else changes.

### 4.4 SV2-C4 — V2 advisory never overrides safety (the conflict precedence)

The frozen precedence `HARD_CONFLICT > HUMAN_CONFIRMED > AI authority`
is preserved verbatim. Concretely:

* Any `EvidenceDecision.ACCEPTED` listing carrying a frozen hard conflict
  class (`CAPACITY`, `INTERFACE`, `GENERATION`, `SALES_UNIT`,
  `BUNDLE`, `FAMILY`) is **out of V2's advisory reach** — V2 cannot
  downgrade, upgrade, or reclassify the conflict.
* A V2 outcome of `MATCH` over a hard-conflict-class detection in the
  FU3A bounded observation set is **forbidden at the constructor**
  (`SemanticMatchResponseV2`'s post-init invariant).
* The `V2_PERF_AUTHORITY_QUALIFIED = False` / `V2_AUTHORITY_QUALIFIED = False`
  state of record remains unchanged by this amendment. Qualification
  promotion happens only under the FU4 Bundle authority program
  (currently UNAPPROVED / NOT EXECUTED).

### 4.5 SV2-C5 — Evidence-grounded matching (the audit chain)

Every V2 advisory MATCH / VARIANT / NON_MATCH outcome carries:

* The bounded observation set (each fact tagged with
  `CandidateEvidenceSourceV2` provenance).
* The frozen derived state (S2-A) at admission.
* The hard-conflict-class check result.
* A `semantic_match_id` and `v2_decision_id` for replay / replay-boundary
  tracing (using the existing
  `AiAssistedMatchResult.original_assessment` shape; the new classes are
  represented through additive provenance tags, never a new model).
* A pointer to the persisted `ResearchRun` and the in-scope assessment
  index (the existing binding primitive
  `is_review_candidate_binding_valid` is the single source of truth for
  provenance binding — preserved).

### 4.6 SV2-C6 — Working Quote / Reviewed Price integration

The Working Quote policy and Reviewed Price arithmetic are unchanged:

* `aggregate_reviewed_listing_prices` continues to consume the persisted
  CONFIRMED review state.
* The new admission clauses in §4.2 **add** sources of HUMAN_CONFIRMED
  rows; they do not change how a CONFIRMED row is treated once persisted.
* The `PriceIntelligenceSnapshot` (Machine Price) is **never** mutated
  by the V2 advisory path or by the new admission clauses.

### 4.7 SV2-C7 — V1 retirement / historical compatibility (the boundary)

V1 retirement is **out of scope** for this amendment. The amendment:

* Preserves the V1 deterministic authority (2A / 3C / 4A / 4B / HUMAN-REVIEW
  / replay / FU3B live predicate) byte-identically.
* Preserves the V1 codec, the V1 snapshot decoder, the V1 replay
  boundaries, and every frozen test.
* Preserves the V1 historical price-result integrity (`schema_version`
  versioning; the FU2 public-replay correction).
* Defines V1 retirement as a separate phase with its own architectural
  gate (analogous to the existing FU4 / C3 / E1 / E2 / P1 / Q1 / W1
  gating).

### 4.8 SV2-C8 — Nonblocking V2 lifecycle (alignment with Option B)

V2 advisory work is **advisory supplementary work**. Where the FU2
Option B design (NONBLOCKING supplementary V2) is the future approved
direction, this amendment's V2 advisory candidate creation is
**compatible** with Option B but does **not** presuppose it:

* V2 advisory runs on **already-published** `ResearchSupplementSnapshot`
  data; it never blocks the main-flow publication.
* V2 advisory ledger records are **append-only**, with the same
  provenance and replay-boundary guarantees as the existing
  `AiAssistedMatchResult` shape.
* If Option B is approved in its own gate, the FU2 lifecycle (durable
  states, recovery, retry, idempotency) applies to the V2 advisory
  ledger records without further contract change.
* If Option B is rejected, the V2 advisory ledger records continue to
  be created on the existing synchronous supplementary path (the
  current FU3B integration), bounded by the existing A1 latency /
  per-attempt instrumentation.

### 4.9 SV2-C9 — Qualification V3 and pricing-authority gating

The amendment does **not** open the qualification gate. Specifically:

* No V2 advisory outcome is promoted to `EvidenceDecision.ACCEPTED`.
* No V2 advisory outcome alters Machine Price.
* No V2 advisory outcome is automatically included in Reviewed Price.
* No V2 advisory outcome is automatically included in Working Quote.
* No V2 advisory candidate is admitted into a 4A price bucket.
* No V2 advisory result affects the `V2_AUTHORITY_QUALIFIED` /
  `V2_PERF_AUTHORITY_QUALIFIED` flags — both remain `False` under this
  amendment.
* The FU4 Bundle authority program (currently UNAPPROVED / NOT
  EXECUTED; C2 state of record DRAFT ACCEPTED / FINAL HOLD; v1.0.0
  seal FINAL-HOLD) is **not** advanced by this amendment.

---

## 5. Measurable success criteria (the "not just more semantic calls" bar)

The direction document is explicit: *"The goal is not simply making
more semantic calls or reducing latency."* The amendment therefore
fixes **measurable** success criteria, each traced to an existing
benchmark or artifact (no new benchmark, no moving the goal posts).

### 5.1 Recall of legitimately reviewable comparison candidates

| Metric | Baseline (today, post-FU3B) | Target | Source of truth |
| --- | --- | --- | --- |
| Reviewed Price bucket count per run (median across the recorded 6D-reference benchmark of representative requests) | (TBD at design-frozen endpoint; current value is whatever the FU3B live path returns) | ≥ +20% relative increase, with **zero** false inclusion (see §5.2) | `aggregate_reviewed_listing_prices` output on the existing 7B / 7C benchmark cases; no new benchmark |
| Coverage of TITLE_TEXT / SKU_FIELD admission | Currently 100% (every such REJECTED is review-eligible) | Preserved 100%; no regression | `is_human_review_eligible_assessment` |
| Coverage of NO_MPN admission with primary signal | Currently 0% (NOT V2-eligible; not review-eligible) | New review-eligible class when the FU3A bounded observation includes an independently-attested specification match | New predicate (SV2-C2) |
| Coverage of variant-similarity cases (independent attestation) | Currently 0% | New review-eligible class `V2_ADVISORY_VARIANT_SIMILARITY` with the attested-variant guard | New predicate (SV2-C2) + `VariantSimilarityTableV2` |

### 5.2 False inclusion of materially incompatible products

| Metric | Baseline | Target | Source of truth |
| --- | --- | --- | --- |
| `HARD_CONFLICT` listings (CAPACITY / INTERFACE / GENERATION / SALES_UNIT / BUNDLE / FAMILY) ever promoted to HUMAN_CONFIRMED | 0 (frozen precedence) | **0** — preserved exactly | `aggregate_reviewed_listing_prices` + the existing precedence node |
| Listings with frozen PARTIAL boundary (`PARTIAL_MPN_ONLY`) auto-promoted to `ACCEPTED` by V2 | 0 (frozen) | **0** — preserved exactly | `ListingIdentityAssessment.__post_init__` |
| Listings with documented manufacturer bundle / capacity / interface conflict ever presented as `MATCH` by V2 | 0 (frozen conflict precedence) | **0** — preserved exactly | S2-A derived state vocabulary |
| UNKNOWN-condition / zero-observation / corrupted-payload rows promoted to HUMAN_CONFIRMED | 0 (frozen HUMAN-REVIEW tests) | **0** — preserved exactly | frozen HUMAN-REVIEW tests |

### 5.3 Coverage of missing-MPN, title-MPN, and cosmetic-variant cases

| Metric | Baseline | Target | Source of truth |
| --- | --- | --- | --- |
| Title-MPN review-eligibility with V2 advisory backing | Review-eligible (U1_TITLE_MPN already admitted) | Preserved; add evidence-grounded backing via FU3A bounded observation | FU3A runtime; SV2-C1 |
| SKU-only review-eligibility with V2 advisory backing | Review-eligible (U2_SKU_ONLY already admitted) | Preserved; add evidence-grounded backing | FU3A runtime; SV2-C1 |
| Missing-MPN review-eligibility with V2 advisory backing | NOT review-eligible (NONE) | Review-eligible when FU3A bounded observation includes an independently-attested spec match | SV2-C1; SV2-C2 |
| Cosmetic-variant review-eligibility | NOT review-eligible (MPN_MISMATCH) | Review-eligible as `V2_ADVISORY_VARIANT_SIMILARITY` **only** with attested-variant backing | SV2-C1; SV2-C3 |

### 5.4 User-confirmed inclusion in Reviewed Price / Working Quote

| Metric | Baseline | Target | Source of truth |
| --- | --- | --- | --- |
| Idempotent confirm / reject / undo | Preserved (frozen HUMAN-REVIEW) | Preserved | `runs/ai_assisted_review.py` |
| 8-step review-POST fail-closed validation | Preserved | Preserved | PLAN §26.11.2 |
| Persisted snapshot authority at both replay boundaries | Preserved (FU2 correction) | Preserved | PLAN §26.12 |
| Working Quote removal action (CONFIRMED → REJECTED) | Preserved | Preserved | `runs/ai_assisted_review.py::remove_candidate_from_working_quote` |

### 5.5 Provenance, replay, and versioned price-result integrity

| Metric | Baseline | Target | Source of truth |
| --- | --- | --- | --- |
| `schema_version` versioning of `PriceIntelligenceSnapshot` | Preserved | Preserved | V1 codec; FU2 replay correction |
| Replay-boundary binding primitive (`is_review_candidate_binding_valid`) | Single source of truth | Preserved; new admission clauses reuse | PLAN §26.11.2; `research/matching.py` |
| Cross-run / cross-snapshot / cross-attempt replay safety | Preserved (FU2 cross-run test) | Preserved | PLAN §26.12 |
| Semantic-match-id + v2-decision-id replay tracing | n/a (advisory today) | Append-only; provenance-bound; not a new authority | SV2-C5 |

### 5.6 Runtime latency and supplementary evidence readiness

| Metric | Baseline (post-Phase 0 A1 instrumentation) | Target | Source of truth |
| --- | --- | --- | --- |
| Per-attempt V2 latency | Persisted (Phase 0 A1 instrumentation, APPROVED) | No regression requirement; Option B is the future async path | `LOCAL_SEMANTIC_V2_PERF_PHASE1_DIAG.md` |
| Token usage per attempt | Persisted | No regression requirement | A1 instrumentation |
| `INSUFFICIENT_EVIDENCE` rate (avoid waste) | n/a | A bounded rate (target: ≥ 5% of V2-eligible admissions surface as `INSUFFICIENT_EVIDENCE` when the FU3A observation set is too thin) | SV2-C1 outcome vocabulary |
| Per-run V2 call count | Recorded | No new global minimum; per-attempt ledger continues | A1 instrumentation |

**Anti-metric (the "not just more calls" bar):** the amendment does **not**
count "more semantic calls" or "lower median latency" as success. The
success metrics are recall coverage (§5.1, §5.3), zero false inclusion
(§5.2), and provenance/replay integrity (§5.5).

---

## 6. Design-scope impact (per surface)

The amendment is assessed against each surface named by the direction
document.

### 6.1 Frozen V2 eligibility and conflict boundaries

* V2 eligibility predicate (`is_v2_semantic_eligible`) is **extended**
  via additive substate admissions (§4.1) — not replaced.
* The frozen S2-A derived state vocabulary and conflict precedence are
  **preserved verbatim**.
* The `ALWAYS_HARD_CONFLICT_CLASSES` is **preserved verbatim**.
* The `SemanticMatchResponseV2.__post_init__` invariant is **strengthened**
  to forbid `MATCH` over `V2_ADVISORY_VARIANT_SIMILARITY` and `MATCH`
  over a hard-conflict-class observation.

### 6.2 Main-flow candidate description / specification evidence

* The main-flow builder continues **not** to carry description or
  specification text into 3C matching (PLAN §16.3 "no description
  semantics" rule is preserved).
* The FU3A semantic runtime's bounded evidence collection is the
  **only** source of additional evidence for V2 advisory — the
  amendment defines the contract (§4.5), not a new main-flow field.
* The 6A / 6B / 6C framework contracts are **unchanged**: 6A remains
  not implemented; 6B (Enterprise SSD) remains frozen and approved;
  6C remains frozen. The amendment does not advance 6A.
* The `CandidateEvidenceSourceV2` `LISTING_TITLE` / `SPECIFICATION_TEXT`
  / `REVIEWED_PRODUCT_CONTEXT` RESERVED members remain RESERVED in the
  main flow; only the FU3A runtime may populate them.

### 6.3 V2 review candidate creation

* `AiAssistedReviewCandidate` model field inventory is **re-pinned
  unchanged** (per STATUS HUMAN-REVIEW record).
* New `V2_ADVISORY_*` classes are represented as **provenance tags** on
  the existing `original_assessment` shape — no new model fields, no
  new migration.
* The `runs/ai_assisted_review.py` write path is **unchanged** in its
  state machine; only the **admission predicate** is extended.

### 6.4 Human confirmation eligibility

* `is_human_review_eligible_assessment` is **extended** by additive
  clauses (§4.2). The existing three predicates are preserved.
* The 8-step review-POST validation is **preserved** in strength
  (PLAN §26.11.2).
* The persisted snapshot authority at both replay boundaries is
  **preserved** (PLAN §26.12).

### 6.5 Reviewed Price and Working Quote integration

* `aggregate_reviewed_listing_prices` is **unchanged** — the existing
  HUMAN_CONFIRMED arithmetic is preserved; the new clauses **add**
  sources of HUMAN_CONFIRMED rows.
* Working Quote policy is **unchanged** — `remove_candidate_from_working_quote`
  and the V0/V1/V2 ordering remain as recorded.
* `PriceIntelligenceSnapshot` (Machine Price) is **never** mutated by
  the new clauses.

### 6.6 V1 retirement / historical compatibility

* V1 retirement is **out of scope** (SV2-C7).
* Historical V1 compatibility is **preserved**: V1 codec, V1 snapshot
  decoder, V1 replay boundaries, every frozen test.

### 6.7 Nonblocking V2 lifecycle / delayed price readiness

* The amendment is **compatible** with FU2 Option B but does not
  presuppose it (SV2-C8).
* The existing A1 instrumentation continues to record per-attempt
  V2 latency / token usage.
* `INSUFFICIENT_EVIDENCE` is the explicit outcome for cases where the
  FU3A bounded observation set is too thin to defend a conclusion — a
  documented rate (target ≥ 5% of eligible admissions) is the
  measurement of "supplementary evidence readiness".

### 6.8 Qualification V3 and pricing-authority gates

* The amendment does **not** open the qualification gate (SV2-C9).
* The FU4 Bundle authority program remains UNAPPROVED / NOT EXECUTED;
  C2 remains DRAFT ACCEPTED / FINAL HOLD; v1.0.0 seal remains
  FINAL-HOLD.
* The C1 / C2 governance batches continue to gate any future
  implementation that would advance the qualification program.

---

## 7. Minimum viable changes (MVC) and phase dependencies

Each MVC is a **bounded phase** with its own gate; **none** is approved
by this amendment. The amendment only enumerates the MVC list and the
dependencies.

### Phase SV2-A — V2 evidence-grounded observation contract (FU3A / FU3B delta)

**Scope (proposed):**
* `research/semantic_v2.py`: additive `V2_ADVISORY_*` candidate classes
  and the `MATCH / VARIANT / NON_MATCH / INSUFFICIENT_EVIDENCE`
  outcome vocabulary (SV2-C1).
* `research/semantic_v2.py`: constructor invariants enforcing the
  variant-class guard and the hard-conflict-class guard (SV2-C4).
* `research/semantic_v2.py`: evidence provenance for `LISTING_TITLE` /
  `SPECIFICATION_TEXT` / `REVIEWED_PRODUCT_CONTEXT` when sourced from
  FU3A bounded observation (not from arbitrary main-flow text).
* `research/identity.py`: **unchanged** (frozen).
* `research/matching.py`: **unchanged** (frozen).

**Gate (proposed):** ChatGPT independent review over the actual source
diff + the test evidence (pin suites byte-verify the frozen surface).

### Phase SV2-B — Human-review candidate admission extension

**Scope (proposed):**
* `research/matching.py::is_human_review_eligible_assessment`:
  additive clauses for `V2_ADVISORY_NO_MPN` + `MATCH`,
  `V2_ADVISORY_VARIANT_SIMILARITY` + any outcome, and the existing
  three predicates preserved.
* `runs/ai_assisted_review.py`: **unchanged** in the state machine.
* `runs/models.py::AiAssistedReviewCandidate`: **unchanged** in field
  inventory (re-pinned).
* `web/presentation.py` / `web/views.py`: additive provenance tags
  only — no new model fields, no new routes.

**Gate (proposed):** ChatGPT independent review.

### Phase SV2-C — VariantSimilarityTableV2 (attested-variant guard)

**Scope (proposed):**
* A new `runs/models.py::VariantSimilarityEntry` model (append-only;
  provenance-bound; no similarity oracle).
* A bounded `runs/variant_similarity.py` service: read-side (guard
  clause only) + write-side (operator-attestation entry).
* Empty/absent → `V2_ADVISORY_VARIANT_SIMILARITY` does not fire.

**Gate (proposed):** ChatGPT independent review; an additive migration
(`make migrations --check --dry-run` must report "No changes detected"
after the additive migration is committed).

### Phase SV2-D — Qualification V3 (governance, NOT implementation)

**Scope (proposed):**
* The C1 / C2 governance batches continue to gate any V2 advisory
  case moving to FU4 / C3 / E1 / E2 / P1 / Q1 / W1.
* The amendment does **not** open any of these gates.

**Gate:** the existing FU4 / C2 / v1.0.0 seal procedure (PLAN §26.34 /
§26.44 / §26.45 / §26.46; STATUS C2 entry).

### Phase SV2-E — V1 retirement (separate, gated)

**Scope (proposed):**
* A future phase that retires V1 only after the V2 advisory path is
  qualified under SV2-D AND the FU2 Option B gate (if approved) is
  closed.

**Gate:** explicit V1-retirement design of record with its own
independent review; preserves V1 historical replay and V1 test
preservation byte-identically.

### Phase SV2-F — Working Quote / Reviewed Price presentation extension

**Scope (proposed):**
* `web/templates/web/research_detail.html`: provenance tags for the
  new admission classes (display only; no arithmetic change).
* `web/presentation.py`: additive presentation helpers — no change
  to `aggregate_reviewed_listing_prices` arithmetic.

**Gate:** ChatGPT independent review.

### Phase dependency diagram

```
SV2-A  ──►  SV2-B  ──►  SV2-F
   │            │
   │            └────► (FU2 Option B gate, independent)
   │
   └────────────►  SV2-C
                     │
                     └────────►  SV2-D (qualification V3)
                                       │
                                       └────────►  SV2-E (V1 retirement)
```

**Hard dependency:** SV2-B depends on SV2-A (the new admission classes
need the outcome vocabulary); SV2-F depends on SV2-B (the presentation
tags need the admission predicates). SV2-C is parallel to SV2-A.
SV2-D and SV2-E are gated on the FU4 / FU2 / C2 governance and the
existing qualification program state, **not** on this amendment.

---

## 8. Explicit non-scope / safety boundaries (the "do not" list)

These boundaries are **binding** for any implementation that descends
from this amendment. Each is traceable to a frozen rule.

1. **Do not weaken or delete any existing test.** `tests/` collection
   baseline is preserved; every frozen pin suite continues to byte-verify
   the frozen surface; the documented 11-node Windows subprocess flake
   allowlist is not expanded by this amendment (CLAUDE.md).
2. **Do not activate V2 pricing authority.** `V2_AUTHORITY_QUALIFIED`
   and `V2_PERF_AUTHORITY_QUALIFIED` remain `False`; no Machine Price
   mutation; no automatic promotion to Reviewed Price; no automatic
   promotion to `ACCEPTED`; no promotion into a 4A price bucket.
3. **Do not treat arbitrary MPN suffix similarity as proof of
   equivalence.** The `VariantSimilarityTableV2` admits only documented
   manufacturer sources or explicit operator attestation (SV2-C3). 2A-FU1's
   withdrawn "delete every non-alphanumeric" lesson is preserved.
4. **Do not override the frozen conflict precedence
   `HARD_CONFLICT > HUMAN_CONFIRMED > AI authority`.** S2-A and
   `SemanticMatchResponseV2.__post_init__` enforce this.
5. **Do not assume description / specification text exists in the main
   flow.** Only the FU3A bounded observation set is admissible for the
   new V2 advisory evidence.
6. **Do not change the deterministic authority.** 2A / 3C / 4A / 4B
   contracts, constructors, and post-init invariants are byte-identical.
7. **Do not advance the qualification gate.** FU4 Bundle authority
   program state remains UNAPPROVED / NOT EXECUTED; C2 remains DRAFT
   ACCEPTED / FINAL HOLD; v1.0.0 seal remains FINAL-HOLD.
8. **Do not modify the V1 codec, the V1 snapshot decoder, or the V1
   replay boundaries.** No caller-supplied index; no caller-supplied
   `PriceAggregationResult`; no schema_version bump.
9. **Do not add a generic LLMProvider interface.** A generic
   `LLMProvider` is planned (PLAN §14B) but **not yet implemented**;
   the existing FU3A / FU3B semantic runtime uses its own transport
   module, not a generic interface (CLAUDE.md / PLAN §14B).
10. **Do not change the security and integrity constraints.** DENIED
    pages and non-COMPLETED pages remain total zero-knowledge (F4 / F5);
    the corporate REMOTE_ADDR/CIDR gate (4D-C-SEC) is unchanged;
    FX / Micron / commercial-supplement denied branches are unchanged;
    F-2 deployment security HOLD remains OPEN.
11. **Do not advance the FU2 Option B gate.** Option B remains the
    **preferred** architectural candidate but is NOT YET APPROVED;
    this amendment is compatible with Option B but does not presuppose
    it.
12. **Do not commit, push, deploy, or change external infrastructure
    unless the user explicitly asks.** (CLAUDE.md; this amendment is
    design only.)
13. **Do not use `git restore` / `git reset` / `git checkout` / `git
    stash` / `git clean` unless explicitly authorized.** (AGENTS.md.)

---

## 9. Open questions / decision gates (for the reviewer)

These are the questions whose resolution gates any future implementation
that descends from this amendment. Each question is small, on-topic, and
non-blocking on the amendment itself.

1. **SV2-A.1** — Should the `V2_ADVISORY_NO_MPN` admission class require
   the FU3A bounded observation to include **at least one**
   independently-attested specification match, or **at least two**
   (defense in depth)?
2. **SV2-A.2** — Is `INSUFFICIENT_EVIDENCE` a single global outcome
   flag, or a per-observation-set failure mode (i.e. a structured
   reason code, not a string)?
3. **SV2-B.1** — Should a `VARIANT` confirmation be eligible for a
   "labeled variant" presentation block in the report (visible to the
   user), or only recorded silently in the audit ledger? This is a
   presentation question; the arithmetic is unchanged either way.
4. **SV2-C.1** — Who is the operator identity for the attestation
   write-path? The existing `web/vendor_refresh_presentation.py`
   pattern uses a self-reported provenance (`operator="web"`); the
   `VariantSimilarityTableV2` may need the same bounded pattern OR an
   explicit identity (analogous to 8C). This is a future-phase
   decision; this amendment does not decide.
5. **SV2-D.1** — When (if ever) the FU4 Bundle authority program
   advances, does the `V2_ADVISORY_VARIANT_SIMILARITY` class need its
   own qualification corpus, or does it inherit the FU4 corpus? This is
   a future-qualification question; this amendment does not decide.
6. **SV2-E.1** — What is the cutover rule for V1 retirement (per-run,
   per-deployment, per-corpus-version)? This is a future-retirement
   question; this amendment does not decide.
7. **SV2-F.1** — Does the presentation need a "V2 advisory candidate
   pending review" block distinct from the existing human-review
   candidates? The existing presentation already carries review-state
   tags; the answer may be "no new block, additive provenance tags
   only".

---

## 10. References (frozen phases, STATUS, PLAN)

| Reference | Why it is cited |
| --- | --- |
| `CLAUDE.md` | The durable AI operating contract. Every frozen phase table entry is sourced here. |
| `docs/PRODUCT_INTELLIGENCE_PLAN.md` §12.1 / §12.3 | The 2A / 2A-FU1 deterministic comparator contract; "no fuzzy matching, edit distance, similarity score, embedding, or model call" rule. |
| `docs/PRODUCT_INTELLIGENCE_PLAN.md` §16.3 | The 3C matching contract; "no description semantics" rule; PARTIAL classification. |
| `docs/PRODUCT_INTELLIGENCE_PLAN.md` §16.4 | The 4A aggregation contract. |
| `docs/PRODUCT_INTELLIGENCE_PLAN.md` §16.5 | The 4B snapshot contract; `PriceIntelligenceSnapshot` immutability. |
| `docs/PRODUCT_INTELLIGENCE_PLAN.md` §26.11 / §26.12 | The HUMAN-REVIEW / replay-boundary corrections (FU1 / FU2); persisted snapshot authority. |
| `docs/PRODUCT_INTELLIGENCE_PLAN.md` §26.21–§26.27 | The Semantic V2 S2-A / S2-B / S2-C contracts and FU1 corrections. |
| `docs/PRODUCT_INTELLIGENCE_PLAN.md` §22.0 / §22.1 / §22.2 | The 6A / 6B / 6C framework contracts (6A not implemented; 6B frozen; 6C frozen). |
| `docs/PRODUCT_INTELLIGENCE_STATUS.md` | The current state of record (FU3A APPROVED; FU3B approved; FU2 Option B NOT YET APPROVED; F-2 deployment security HOLD OPEN; FU4 UNAPPROVED / NOT EXECUTED; C2 DRAFT ACCEPTED / FINAL HOLD). |
| `docs/SEMANTIC_V2_PERFORMANCE_DESIGN_01.md` | The Option B nonblocking supplementary V2 design (preferred architecture of record; FU2 NOT YET APPROVED). |
| `docs/LOCAL_SEMANTIC_V2_PERF_PHASE1_DIAG.md` | The Phase 0 / Phase 1 V2 performance diagnostic (APPROVED with documented evidence limitations; A1 instrumentation). |
| `product_intelligence/research/identity.py` | The frozen 2A comparator. |
| `product_intelligence/research/matching.py` | The frozen 3C matching + the existing `is_human_review_eligible_assessment` predicate. |
| `product_intelligence/research/semantic_v2.py` | The FU3A semantic V2 vocabulary + `is_v2_semantic_eligible` predicate. |
| `product_intelligence/research/aggregation.py` | The frozen 4A aggregation + `aggregate_reviewed_listing_prices`. |
| `product_intelligence/research/price_result_codec.py` | The V1 codec + `decode_price_aggregation_result`. |
| `product_intelligence/runs/ai_assisted_review.py` | The HUMAN-REVIEW write path. |
| `product_intelligence/runs/models.py` | The `AiAssistedReviewCandidate` model + the frozen field inventory. |
| `product_intelligence/execution/compact_quote_replay.py` | The replay-boundary authority (`replay_compact_quote_projection`, `replay_public_compact_quote_projection`, `derive_human_confirmed_assessment_indices`). |
| `tests/web/test_web_boundaries.py` | The web-layer import allowlist enforcement. |
| `tests/runs/test_vendor_refresh_*` (and the other frozen pin suites) | The frozen pin suites that byte-verify the frozen surface. |

---

## 11. Closing gate statement

This amendment is **design only**. It proposes a bounded contract
delta (§4), measurable success criteria (§5), and minimum viable
changes (§7). It does **not** implement code, **does not** change
tests, **does not** weaken any frozen contract, **does not** activate
V2 pricing authority, and **does not** change the qualification
program state.

The next step is ChatGPT independent review over this document. The
document is small, on-topic, and traceable to the frozen architecture.
Any implementation that descends from this amendment is itself a
bounded phase with its own design of record, its own migration /
corpus / schema discipline, its own test-preservation record, and its
own independent review — **none of which is approved by this
amendment**.
