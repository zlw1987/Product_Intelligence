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
> **FU1 review status.** ChatGPT FU1 review of commit
> `4c2388937ba00882ca9d72250d347004bfaef808` returned
> **CHANGES REQUESTED — DESIGN ONLY**. This document corrects in place
> (F1–F8) without creating a replacement. It does not advance any
> implementation, qualification, or authority flag.
>
> Frozen-phrase reference. Where this document uses a phrase that already
> has a binding definition in `CLAUDE.md`, `docs/PRODUCT_INTELLIGENCE_PLAN.md`,
> or `docs/PRODUCT_INTELLIGENCE_STATUS.md`, the binding definition
> controls; this document does not redefine it.

---

## 0. Status of this artifact (gate)

| Property | Value |
| --- | --- |
| Phase | Pre-design — product-contract amendment for ChatGPT review (FU1 corrections applied in place) |
| Implementation | **None.** No code, no test, no migration, no corpus label, no authority flag, no schema, no pricing wiring, no prompt, no model call, no seal artifact, no qualification. |
| Dependents | None. This amendment does not modify `CLAUDE.md`, `PRODUCT_INTELLIGENCE_STATUS.md`, or `PRODUCT_INTELLIGENCE_PLAN.md`. Status / PLAN update happens only under a later approved implementation phase. |
| Authority state of record (carried over, unchanged) | `V2_AUTHORITY_QUALIFIED = False`, `V2_PERF_AUTHORITY_QUALIFIED = False`, FU2 Option B **NOT YET APPROVED**, FU4 Bundle authority program state **UNAPPROVED / NOT EXECUTED**, C2 corpus state **DRAFT ACCEPTED / FINAL HOLD**, v1.0.0 seal **FINAL-HOLD**. |
| Deployment security | F-2 ambient `PI_VENDOR_PRICE_ALLOWED_CIDRS` HOLD **OPEN** — untouched; the CIDR zero-knowledge requirement remains limited to its actual protected commercial-data boundary (4D-C-SEC `vendor_price_access_allowed` over `REMOTE_ADDR`) and is NOT extended to non-commercial surfaces by this amendment (F8). |
| FU1 review verdict | CHANGES REQUESTED — DESIGN ONLY. F1–F8 corrections applied in this document. |

---

## 1. Authoritative product goal (re-statement, scope-bounded)

Semantic V2 is intended to **replace** Semantic V1 as the primary
intelligent matching and review engine for Product Intelligence.

The business problem it must solve is **insufficient usable comparable
samples**, driven by overly restrictive identity filtering and review
eligibility, with three named real customer scenarios:

| # | Scenario | Deterministic 3C behavior today | Semantic V2's potential role |
| --- | --- | --- | --- |
| 1 | Requested MPN appears in listing **title** but no explicit structured MPN field exists. | `REJECTED` + `NO_EXPLICIT_MPN_EVIDENCE` + `TITLE_TEXT`. Today, **V2-eligible** (U1_TITLE_MPN uncertain substate) and human-review-eligible. | Evaluate as an **advisory** MATCH / VARIANT / NON_MATCH candidate; surface as a review candidate. Never auto-accept. |
| 2 | Candidate MPN is **missing**, but product description and independently supported specifications are strongly consistent with the requested product. | `REJECTED` + `NO_EXPLICIT_MPN_EVIDENCE` + `NONE`. Today, **NOT V2-eligible** and NOT human-review-eligible. | A new V2-eligibility substate is required; admissible evidence is sourced from the FU3A semantic runtime's bounded observation contract (NOT from arbitrary main-flow fields — see §3.4 and F1). Advisory only. |
| 3 | Candidate MPN differs by a **suffix** that may represent color, cosmetic appearance, or another non-critical variation. | Most cases: `REJECTED` + `MPN_MISMATCH` (today, NOT V2-eligible). Some: `PARTIAL` (`REJECTED` + `PARTIAL_MPN_ONLY`, today V2-eligible and human-review-eligible). | Treat as a **V2-advisory VARIANT candidate** when supported by independent evidence (manufacturer or auditable attestation). **Never** treat arbitrary MPN suffix similarity as proof of equivalence. **Never** auto-accept. Two distinct evidence statuses are separated (see F6 / §4.6). |
| 4 | A genuinely different product / accessory / bundle / capacity / interface / generation / sales unit must still be handled safely. | `REJECTED` + `MPN_MISMATCH` or `PARTIAL_MPN_ONLY`, or `REJECTED` + bundle/capacity conflict (frozen Bundle-axis). | The frozen conflict precedence `HARD_CONFLICT > HUMAN_CONFIRMED > AI authority` is **preserved**. V2 advisory cannot override a hard safety conflict and cannot silently alter Machine Price. |

**Direction the amendment confirms (unchanged):**

* Broader V2 candidate evaluation (subject to §3 audit and §4 contract).
* Evidence-grounded matching and variant classification.
* V2-backed human review candidates (V2 advisory proposes; human confirms).
* User-confirmed inclusion in Reviewed Price and comparison workflows
  (already the frozen HUMAN-REVIEW path: `runs/ai_assisted_review.py`,
  `aggregate_reviewed_listing_prices`, the Compact-Quote HUMAN_CONFIRMED
  overlay — preserved unchanged). The new path **adds** sources of
  HUMAN_CONFIRMED, never modifies how a HUMAN_CONFIRMED row is treated
  (see §4.2 / F3).
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
  no such path; the V2 advisory VARIANT outcome is NOT a path into any
  4A bucket — see F4 / §4.4).
* A V2 MATCH never becomes `EvidenceDecision.ACCEPTED`
  (CLAUDE.md / PLAN §16.3 / `runs/ai_assisted_review.py` are explicit:
  "Confirming a candidate NEVER changes EvidenceDecision to ACCEPTED").
* A V2 MATCH never causes a deterministic-identity-eligible listing to
  become ineligible (V2 can only ADMIT additional human-review candidates,
  not strip currently-eligible ones).

The amendment therefore proposes **advisory, evidence-grounded** V2
expansion, not V2 replacement of deterministic identity.

---

## 3. Audit of current extraction and evidence capabilities (the real main flow) — FU1-corrected

The direction document explicitly directs: *"Do not assume descriptions
or structured specification fields exist in the current main-flow input.
Audit the real extraction and evidence capabilities before designing
matching authority."*

This audit is binding for the amendment. FU1 corrections F1 and F5
require three explicit separations:

1. **Identifier signal** (the deterministic `EvidenceSource` vocabulary
   in `research/matching.py`: `EXPLICIT_MPN_FIELD`,
   `VISIBLE_LABELED_MPN_FIELD`, `SKU_FIELD`, `TITLE_TEXT`, `NONE`).
2. **V2 semantic product-evidence signal** (the bounded
   `CandidateEvidenceSourceV2` vocabulary in `research/semantic_v2.py`:
   `PUBLISHED_STRUCTURED_FIELD`, `LISTING_TITLE` (RESERVED),
   `SPECIFICATION_TEXT` (RESERVED), `REVIEWED_PRODUCT_CONTEXT`
   (RESERVED)).
3. **S2-A derived state** (the frozen `IdentityStateV2` /
   `UncertainSubstateV2` vocabulary, computed via
   `derive_identity_state_v2`, including the five uncertain substates
   U1_TITLE_MPN / U2_SKU_ONLY / U3_PARTIAL_BOUNDARY / U4_NO_MPN /
   U5_NEAR_MISS_MPN).

The FU1-corrected admission contract (§4.1) operates on these three
signals **separately**, never combining them as if they were one
vocabulary.

### 3.1 What the main flow actually carries into the 3C matching step

Source of truth: `product_intelligence/research/listings.py`,
`NormalizationIssue`, the `NormalizedListingObservation` / `ListingObservation`
contract, and `research/matching.py::_find_evidence`.

| Evidence source (deterministic) | Main-flow field | Today in 3C | Today in semantic V2 evidence collection |
| --- | --- | --- | --- |
| `EXPLICIT_MPN_FIELD` | `manufacturer_part_number_text` from structured JSON-LD / meta | ACCEPTED path on EXACT / NORMALIZED_EXACT | `PUBLISHED_STRUCTURED_FIELD` (candidate brand only — the live `build_candidate_product_evidence_v2` populates only `brand` from this source; every other product dimension stays explicit None) |
| `VISIBLE_LABELED_MPN_FIELD` | Bounded visible labeled MPN enrichment (`JSON_LD_WITH_VISIBLE_MPN`, `META_WITH_VISIBLE_MPN`) | ACCEPTED path on EXACT / NORMALIZED_EXACT | `PUBLISHED_STRUCTURED_FIELD` (same scope) |
| `SKU_FIELD` | `sku_text` | REJECTED + NO_EXPLICIT_MPN_EVIDENCE (recorded) | U2_SKU_ONLY substate; **no SKU-derived fact emitted** — `CandidateEvidenceSourceV2` has no SKU member; SKU is an identifier field, not a product-evidence source |
| `TITLE_TEXT` | `product_title` (token-substring match only) | REJECTED + NO_EXPLICIT_MPN_EVIDENCE (recorded) | U1_TITLE_MPN substate; today the live main-flow builder emits **no** title-derived fact — `LISTING_TITLE` is **RESERVED**; the raw title text is carried as `CandidateProductEvidenceV2.raw_title_text` (RAW observation text, labeled as such) but a token in it is NOT a structured fact |
| `NONE` | No candidate identifier was found | REJECTED + NO_EXPLICIT_MPN_EVIDENCE | Today NOT V2-eligible for human review; the S2-A substate U4_NO_MPN is admitted only when a primary signal exists (TITLE_MPN_TOKEN or SKU_EQUALS_REQUESTED) — `EvidenceSource.NONE` itself does NOT route to U4_NO_MPN under the current `assess_listing_identity` builder (FU1 F1: this is the impossibility the original admission predicate collapsed; the corrected predicate is in §4.1) |
| Product description / specification text | Not carried by 3C; not read by `assess_listing_identity`; "Any future description/category/comparable semantic interpretation belongs to a later explicitly approved phase" (PLAN §16.3). 6A / 6B / 6C framework contracts exist; **6A is not implemented**; 6B implements the Enterprise SSD category schema (frozen); 6C implements deterministic structured extraction. The main flow today does **not** carry a description or specification payload into semantic V2. | n/a (description not read) | `SPECIFICATION_TEXT` is **RESERVED**; `REVIEWED_PRODUCT_CONTEXT` is **RESERVED**; `CandidateProductEvidenceV2.raw_specification_text` is explicit `None` from the live builder |

**Implication for the direction's four scenarios (FU1 F1 + F5 corrected):**

1. **Title-MPN (scenario 1).** Identifier signal = `TITLE_TEXT`; V2
   semantic product-evidence signal = the bounded title text carried as
   `raw_title_text` (RAW observation text, not a structured fact).
   S2-A substate = `U1_TITLE_MPN`. Existing V2 eligibility and human
   review eligibility **preserved** (FU3B clause).
2. **Missing-MPN with description + spec consistency (scenario 2).**
   Identifier signal = `NONE`. V2 semantic product-evidence signal
   today: **the live builder emits no observation fact for this case**
   (`raw_title_text` may still be present, but `PUBLISHED_STRUCTURED_FIELD`
   has no candidate-side facts beyond brand; `SPECIFICATION_TEXT` and
   `REVIEWED_PRODUCT_CONTEXT` are RESERVED). For V2 to admit these cases
   at all, the FU3A bounded observation contract (SV2-A / §7) must
   define the bounded acquisition surface that the live builder currently
   does not produce. **Until SV2-A is approved and live, this scenario
   has no admissible evidence and the NO_MPN admission does not fire**
   (FU1 F1: no silent route from `NONE` to V2 advisory via
   `is_human_review_eligible_assessment`).
3. **Cosmetic suffix variant (scenario 3).** Identifier signal
   mismatch → `MPN_MISMATCH`. S2-A substate today: NOT V2-eligible
   under `is_v2_semantic_eligible` (the FU3A predicate only admits
   `DETERMINISTIC_UNCERTAIN`; `MPN_MISMATCH` is not uncertain). The
   corrected variant-similarity admission (FU1 F6 / §4.6) is a NEW
   separate predicate keyed on the attested-variant guard and the
   bounded FU3A observation set; it does not silently route through the
   existing `is_v2_semantic_eligible` and does not depend on
   edit-distance or character-similarity heuristics.
4. **Genuinely different product (scenario 4).** No new admission. The
   frozen conflict precedence and the `ALWAYS_HARD_CONFLICT_CLASSES`
   precedence (`CAPACITY`, `INTERFACE`, `GENERATION`, `SALES_UNIT`,
   `BUNDLE`, `FAMILY`) are preserved (F4 / §4.4).

### 3.2 What the FU3A / FU3B semantic runtime already carries

`product_intelligence/research/semantic_v2.py` defines bounded candidate
observation facts with provenance (`CandidateEvidenceSourceV2`) and a
frozen S2-A derived state vocabulary. The semantic runtime already
admits the five uncertain substates (`U1_TITLE_MPN`, `U2_SKU_ONLY`,
`U3_PARTIAL_BOUNDARY`, `U4_NO_MPN`, `U5_NEAR_MISS_MPN`) via
`is_v2_semantic_eligible`. What is missing for scenarios 2 and 3 is
**not the admission** (the predicate covers `DETERMINISTIC_UNCERTAIN`)
— it is the **bounded observation surface** the model can draw on,
and — for scenario 3 — a NEW attestation guard. The amendment proposes
both be addressed in §7 as SV2-A (observation contract) and SV2-C
(`VariantSimilarityTableV2`).

### 3.3 What frozen phases forbid the amendment from changing

| Frozen phase | Cannot be changed by this amendment | Source |
| --- | --- | --- |
| 2A / 2A-FU1 deterministic comparator | The normalization profile; EXACT/NORMALIZED_EXACT/UNKNOWN outcome; "no fuzzy matching, edit distance, similarity score, embedding, or model call". | PLAN §12.1, §12.3; `research/identity.py`. |
| 3C matching | The four-decision vocabulary; the `ACCEPTED`-requires-`EXPLICIT_MPN_FIELD` or `VISIBLE_LABELED_MPN_FIELD` rule; PARTIAL classification; the "no description semantics" rule; the `_find_evidence` evidence-source vocabulary. | PLAN §16.3; `research/matching.py`. |
| 4A aggregation | The bucket vocabulary; the inclusion/exclusion rules; Machine Price derivation; `aggregate_reviewed_listing_prices`. | PLAN §16.4; `research/aggregation.py`. |
| 4B snapshot | `PriceIntelligenceSnapshot` immutability; the V1 codec (`decode_price_aggregation_result`); the read-only GET. | PLAN §16.5; `research/price_result_codec.py`. |
| FU3A / FU3B semantic runtime | The S2-A derived state vocabulary (`IdentityStateV2` / `UncertainSubstateV2`); the S2-C decision vocabulary (`V2SemanticDecision` in `research/semantic_authority_v2.py` — `MATCH / NO_MATCH / UNCERTAIN` only); the `SemanticDecision` vocabulary (`semantic/contract.py` — `MATCH / NO_MATCH / UNCERTAIN` only); the conflict precedence `HARD_CONFLICT > HUMAN_CONFIRMED > AI authority`; the `ALWAYS_HARD_CONFLICT_CLASSES`; the bounded observation fact provenance; the advisory nature of any V2 MATCH. | PLAN §26.21–§26.27; STATUS (FU3A/FU3B); `research/semantic_v2.py`; `research/semantic_authority_v2.py`; `semantic/contract.py`. |
| HUMAN-REVIEW | The review-state machine (`UNREVIEWED → CONFIRMED / REJECTED → UNREVIEWED`); the candidate-to-assessment binding primitive (`is_review_candidate_binding_valid`); the rule that CONFIRMED is the **only** path to HUMAN_CONFIRMED and the rule that CONFIRMED never becomes `ACCEPTED`; the persisted snapshot authority at both replay boundaries (`replay_compact_quote_projection`, `replay_public_compact_quote_projection` — no caller-supplied index, no caller-supplied `PriceAggregationResult`). | PLAN §26.11 / §26.12; STATUS (HUMAN-REVIEW); `runs/ai_assisted_review.py`. |
| 4D / Compact Quote / Vendor | The Vendor Commercial Price Access Gate (4D-C-SEC); the FX cache contract (8A); the vendor paragraph envelope (FU3); the production-wire fidelity (FU1); F-2 ambient `PI_VENDOR_PRICE_ALLOWED_CIDRS` HOLD OPEN. | PLAN §26.9–§26.15. |
| SemanticDecisionRecord schema | The single registered envelope format version (`schema_version=1`) of the persisted payload; the codec (`research/semantic_decision_codec.py`); the existing unique binding `(run, assessment_index)`. New contract adapter versions register through the codec, never through model changes (F2 / §4.3). | `runs/models.py::SemanticDecisionRecord`; `research/semantic_decision_codec.py`. |
| Architecture guard tests | Layer boundaries (`web/` read-side research allowlist; `runs/` is the only Django model layer; provider / execution internals / `research/identity` import discipline); stdlib-only domain; no vendor names in business logic. | CLAUDE.md; `tests/web/test_web_boundaries.py`; architecture-guard test files. |

### 3.4 FU1 F5: Persisted-data and evidence-acquisition architecture (the source of truth)

The FU1 review surfaces a critical correction. This subsection records
the actual persisted-data and evidence-acquisition architecture that
the amendment must respect:

* **`PriceIntelligenceSnapshot`** (`runs/models.py`) is the **canonical
  source of listing identity assessments**. It holds the run's full
  ordered assessment tuple (codec-decoded via
  `decode_price_aggregation_result`). Any V2 advisory reconstruction
  starts here.
* **`ResearchSupplementSnapshot`** (`runs/models.py`) is **Vendor API
  commercial data** (4D-B). It is **NOT** the canonical source of
  listing identity assessments. The amendment does not route any V2
  advisory admission through it.
* **`ResearchFxSnapshot`** is **FX-rate evidence** (4D-C-A, display-
  supplemental only). Not a V2 advisory source.
* **`AiAssistedMatchResult.original_assessment`** is the immutable
  deterministic assessment wrapped by the FU3B V1 path. It is the
  assessment a V2 advisory record references — never its source of
  truth (the snapshot is).
* **`SemanticDecisionRecord`** (`runs/models.py`) is the semantic
  execution / provenance ledger: an opaque versioned JSON payload
  keyed on `(run, assessment_index)` with one registered contract
  adapter today (S2-C). New advisory contract adapters register
  through `research/semantic_decision_codec.py` — never by changing
  the model. The frozen `schema_version=1` envelope and the frozen
  S2-C payload shape are preserved; the new advisory is an additive
  `v2_advisory` section under a new registered contract adapter
  (F2 / §4.3).
* **Per-debt provenance** under the FU2 Option B direction (NONBLOCKING
  supplementary V2) is the future approved shape for asynchronous
  durable state, recovery, and retry. SV2-C8 ensures the V2 advisory
  records are compatible with Option B without presupposing it.
* **`CandidateProductEvidenceV2`** (`research/semantic_v2.py`) is the
  bounded extraction contract. The live main-flow builder
  (`build_candidate_product_evidence_v2`) emits:
  * `brand` only from `PUBLISHED_STRUCTURED_FIELD` (when the page
    publishes brand); every other product dimension is explicit None;
  * `raw_title_text` from the published title (RAW observation text,
    labeled);
  * `raw_specification_text = None` (the main flow carries no
    specification text; the remaining JSON-LD material stays in the
    opaque `raw_reference`, which no business rule may parse — AD-040).
* **`CandidateCommercialEvidenceV2`** carries the bounded commercial
  observation evidence with the explicit `sales_unit` channel always
  present (`UNAVAILABLE` or `OBSERVED`). NEVER identity evidence.
* **Bounded acquisition contract**: the V2 advisory observation
  surface is the existing `CandidateProductEvidenceV2` + the existing
  FU3A bounded observation set. SV2-A (if approved) defines the
  future additive bounded acquisition shape that lets the live
  builder populate the `PUBLISHED_STRUCTURED_FIELD` product dimensions
  beyond `brand` (e.g. capacity, interface, generation) and the
  `REVIEWED_PRODUCT_CONTEXT` candidate-side context where the main
  flow carries one. Until SV2-A is approved, the live builder's
  bounded surface is what the amendment documents.
* **Opaque `raw_reference` discipline (AD-040)** is preserved: the
  amendment **never** parses opaque raw_reference as structured
  authority and **never** fabricates structured facts from model
  output (F5).

---

## 4. Bounded product contract amendments (the contract delta)

Each amendment is a **contract clause** (a documented rule change). It is
**advisory by default**: every clause that grants new admission to the
V2 advisory path is conditioned on the FU3A / FU3B bounded observation
contract and is **never** a path to `EvidenceDecision.ACCEPTED`. None of
the clauses below activate pricing authority, schema changes, or new
authority.

### 4.1 SV2-C1 — V2 advisory candidate classes (the FU1-corrected admission contract)

**Three-signal admission contract (FU1 F1 correction).**

The FU1 review identified that the original admission predicate
collapsed identifier signals and semantic product-evidence signals into
a single condition. The corrected contract operates on **three
separated signals**:

| Signal | Source of truth | Vocabulary |
| --- | --- | --- |
| **Identifier signal** | `_find_evidence()` in `research/matching.py` | `EvidenceSource ∈ {EXPLICIT_MPN_FIELD, VISIBLE_LABELED_MPN_FIELD, SKU_FIELD, TITLE_TEXT, NONE}` (frozen) |
| **V2 semantic product-evidence signal** | FU3A bounded observation set (`CandidateProductEvidenceV2` from `research/semantic_v2.py`) | `CandidateEvidenceSourceV2 ∈ {PUBLISHED_STRUCTURED_FIELD, LISTING_TITLE (RESERVED), SPECIFICATION_TEXT (RESERVED), REVIEWED_PRODUCT_CONTEXT (RESERVED)}` (frozen) |
| **S2-A derived state** | `derive_identity_state_v2` in `research/semantic_v2.py` | `IdentityStateV2.DETERMINISTIC_UNCERTAIN` with `UncertainSubstateV2 ∈ {U1_TITLE_MPN, U2_SKU_ONLY, U3_PARTIAL_BOUNDARY, U4_NO_MPN, U5_NEAR_MISS_MPN}` (frozen) |

The new admission contract is the **conjunction** of conditions on these
three signals. The frozen 3C comparator and the S2-A state constructors
are **unchanged** (FU1 F1: no silent change). The new predicate is
**additive** at the boundary; it does not replace `_find_evidence` or
`derive_identity_state_v2`.

**New bounded V2 advisory candidate classes (advisory only, frozen):**

| Class | Identifier signal | V2 semantic product-evidence signal | S2-A substate | Required V2 outcome |
| --- | --- | --- | --- | --- |
| `V2_ADVISORY_TITLE_MPN` | `TITLE_TEXT` | bounded title-text observation present (`raw_title_text` non-None) | `U1_TITLE_MPN` | MATCH / VARIANT / NON_MATCH |
| `V2_ADVISORY_SKU_FIELD` | `SKU_FIELD` | bounded SKU identifier present + bounded title-text observation present | `U2_SKU_ONLY` | MATCH / VARIANT / NON_MATCH |
| `V2_ADVISORY_PARTIAL_BOUNDARY` | `EXPLICIT_MPN_FIELD` (PARTIAL outcome) | bounded structured observation present (brand or capacity/interface/generation from PUBLISHED_STRUCTURED_FIELD) | `U3_PARTIAL_BOUNDARY` | MATCH / VARIANT / NON_MATCH |
| `V2_ADVISORY_NO_MPN` (FU1 F1 corrected) | `NONE` AND a primary signal present (TITLE_TEXT OR SKU_FIELD); the existing U4_NO_MPN substate | bounded FU3A observation set must contain **at least one** `PUBLISHED_STRUCTURED_FIELD` product-dimension fact beyond `brand` (e.g. capacity, interface, generation) OR a `REVIEWED_PRODUCT_CONTEXT` candidate-side context — the live builder emits no such fact today, so this class **does not fire** until SV2-A is approved (FU1 F1: no silent route from `NONE`) | `U4_NO_MPN` | MATCH / VARIANT / NON_MATCH |
| `V2_ADVISORY_VARIANT_SIMILARITY` (FU1 F6 corrected) | `EXPLICIT_MPN_FIELD` with MPN_MISMATCH | attested-variant guard from `VariantSimilarityTableV2` (§4.6) — **never** edit-distance; **never** character-similarity heuristics | not in `DETERMINISTIC_UNCERTAIN` (separate predicate) | VARIANT only (never MATCH) |

**Outcome vocabulary (the new V2 advisory return values, FU1 F2 corrected):**

The frozen `V2SemanticDecision` (`research/semantic_authority_v2.py`:
`MATCH / NO_MATCH / UNCERTAIN` only) and the frozen `SemanticDecision`
(`semantic/contract.py`: same) are **unchanged**. The new V2 advisory
**does not** add members to either vocabulary (FU1 F2). Instead, the
new V2 advisory record carries an **additive `v2_advisory` section**
under a **new registered contract adapter** of the existing
`SemanticDecisionRecord` envelope (see §4.3). The `v2_advisory` section
records:

* `class` — one of the five `V2_ADVISORY_*` class strings.
* `outcome` — one of four bounded advisory outcomes:
  * `MATCH` — V2 advisory believes the candidate refers to the same
    product with **independent** evidence (FU3A bounded observation;
    never edit-distance).
  * `VARIANT` — V2 advisory believes the candidate refers to a known
    non-identity product variant (color, cosmetic, packaging, sales
    unit variant). **`VARIANT` is never `MATCH`** — it is a distinct
    outcome and never enters the price bucket as identity.
  * `NON_MATCH` — V2 advisory believes the candidate is not the
    requested product (the safe default).
  * `ADVISORY_NO_FIRE` — the bounded FU3A observation set was
    insufficient to reach a defensible conclusion; the candidate is
    **not created** (FU1 F2 + F1: this is a no-record outcome, not a
    stored `INSUFFICIENT_EVIDENCE` flag — see §4.3 and F7 anti-metric).
* `evidence_facts` — the bounded observation set (each fact tagged
  with `CandidateEvidenceSourceV2` provenance).
* `provenance` — the bounded S2-A derived state at admission.
* `hard_conflict_check` — the bounded `ALWAYS_HARD_CONFLICT_CLASSES`
  check result.

**Hard guards (frozen, FU1 F2/F4 enforced):**

* An `outcome` of `MATCH` over a `V2_ADVISORY_VARIANT_SIMILARITY`
  class is **forbidden at the constructor** (FU1 F4 + F6: a
  variant-class candidate must record `VARIANT`; `MATCH` is rejected).
* An `outcome` of `MATCH` over `V2_ADVISORY_NO_MPN` is permitted **only**
  when the FU3A bounded observation includes **at least one
  independently-attested product specification match** (e.g.
  `PUBLISHED_STRUCTURED_FIELD` capacity / interface / generation) —
  description-only similarity is never sufficient (F1 + F5).
* An `outcome` of `MATCH` or `VARIANT` over a hard-conflict class
  (`CAPACITY`, `INTERFACE`, `GENERATION`, `SALES_UNIT`, `BUNDLE`,
  `FAMILY`) is **forbidden at the constructor**. The conflict
  precedence is preserved.
* An `outcome` cannot name `MATCH` over `EvidenceDecision.ACCEPTED` —
  no V2 evaluation runs against an already-accepted listing.
* `ADVISORY_NO_FIRE` is a **no-record outcome**: no `SemanticDecisionRecord`
  is created, no review candidate is created, no audit row is created.
  The candidate simply does not exist (FU1 F1: no silent acceptance via
  absence).

### 4.2 SV2-C2 — Human-review candidate admission (the review-boundary contract, FU1 F3 corrected)

**Actual signature audit (FU1 F3 requirement).**

* `is_human_review_eligible_assessment(assessment: ListingIdentityAssessment) -> bool`
  — `research/matching.py:762-806`. Inputs: a single
  `ListingIdentityAssessment`. Decision and evidence-source access:
  `assessment.decision`, `assessment.rejection_reason`,
  `assessment.candidate_evidence_source`. Returns True only for the
  three FU3B clauses today.
* `AiAssistedReviewCandidate` field inventory — `runs/models.py:622-849`.
  Immutable provenance fields: `source_url`, `target_mpn`,
  `target_description`, `candidate_title`, `candidate_mpn_field`,
  `candidate_sku`, `candidate_specs`, `evidence_source`,
  `semantic_confidence`, `semantic_reason_code`,
  `semantic_matched_attributes`, `semantic_conflicting_attributes`,
  `actual_provider`, `actual_model`, `prompt_version`. Mutable state:
  `review_state ∈ {UNREVIEWED, CONFIRMED, REJECTED}`. Identity:
  UUID primary key; `assessment_index` is a `PositiveSmallIntegerField`
  with `UniqueConstraint(fields=['run', 'assessment_index'])`.
* `is_review_candidate_binding_valid(candidate, assessment) -> bool`
  — `research/matching.py:804-866`. Checks the 6 binding fields:
  `source_url`, `target_mpn`, `candidate_title`, `candidate_mpn_field`,
  `candidate_sku`, `evidence_source`. Re-checks
  `is_human_review_eligible_assessment(assessment)`. Fail-closed.

**The corrected new admission contract (FU1 F3 — minimal additive):**

The new V2 advisory admission is implemented as an **additive predicate**
that operates **only** on the inputs already available to
`is_human_review_eligible_assessment` (i.e.
`decision`, `rejection_reason`, `candidate_evidence_source`). It does
**not** introduce a new assessment field; it does **not** mutate the
existing signature; it does **not** depend on evidence unavailable to
those functions.

The additive clauses (each keyed on the existing triple, evaluated
after the FU3B predicate returns False):

* `V2_ADVISORY_NO_MPN` admission (scenario 2): the candidate has
  `decision=REJECTED`, `rejection_reason=NO_EXPLICIT_MPN_EVIDENCE`,
  `candidate_evidence_source=NONE`, AND the FU3A bounded observation
  set records **at least one** `PUBLISHED_STRUCTURED_FIELD` product
  dimension beyond `brand` OR a `REVIEWED_PRODUCT_CONTEXT` candidate
  context — guarded at the predicate by the `VariantSimilarityTableV2`
  read-side check (§4.6) keyed on the bounded observation. **Today the
  live builder emits no such fact, so the clause does not fire** (F1).
* `V2_ADVISORY_VARIANT_SIMILARITY` admission (scenario 3): the
  candidate has `decision=REJECTED`,
  `rejection_reason=MPN_MISMATCH`, AND the bounded observation
  references an attested variant relationship in
  `VariantSimilarityTableV2` (manufacturer URL + retrieval instant OR
  operator attestation; never edit-distance; never character-similarity
  heuristics). The clause does **not** require
  `is_v2_semantic_eligible` to return True — it is a separate predicate
  keyed on the attested-variant guard (F6).

The three existing FU3B clauses are **preserved** (TITLE_TEXT,
SKU_FIELD, PARTIAL_MPN_ONLY). The new clauses are **additive**.

**Idempotency, provenance binding, confirmation, replay:**

* **Idempotency key**: the existing `(run, assessment_index)`
  `UniqueConstraint` on `AiAssistedReviewCandidate`. FU1 F3
  requirement: "prevent duplicate or contradictory review candidates
  when V1 and V2 overlap." The unique constraint is the single source
  of truth. The V2 advisory admission predicate is evaluated AFTER the
  FU3B predicate — if FU3B returns True, the V2 clause is **not**
  applied (the V1 review candidate is the only one created at that
  index). For NO_MPN (which is NOT FU3B-eligible), the V2 clause is
  the sole path; the unique constraint applies identically.
* **Provenance binding**: `is_review_candidate_binding_valid` is the
  single source of truth, unchanged signature. The new V2 advisory
  candidate carries the same 6 binding fields as V1 candidates.
* **Confirmation state**: the existing `review_state ∈ {UNREVIEWED,
  CONFIRMED, REJECTED}` machine, the existing
  `confirm_review_candidate` / `reject_review_candidate` /
  `undo_review_candidate` / `remove_candidate_from_working_quote`
  entry points, and the existing `TERMINAL_REVIEW_STATES` set. The new
  V2 advisory candidate flows through the same state machine.
* **Replay integration**: the run's persisted
  `PriceIntelligenceSnapshot` is the source of truth; the
  `SemanticDecisionRecord` envelope carries the new
  `v2_advisory` contract section (§4.3) without altering the frozen
  S2-C payload; the replay boundaries (`replay_compact_quote_projection`,
  `replay_public_compact_quote_projection`) read the run's own snapshot
  with zero live I/O and zero caller-supplied index.
* **Historical V1 path preservation**: V1 codec, V1 snapshot decoder,
  V1 replay boundaries, every frozen V1 test, and every FU3B test —
  all byte-identical, all preserved.

**Hard guards (frozen, FU1 F3 + F4):**

* A V2 advisory candidate is **never** created at an index where a
  FU3B V1 review candidate is created at the same (run,
  assessment_index) (the unique constraint enforces it; the evaluation
  order enforces it).
* A V2 advisory `VARIANT` outcome is **never** confirmed unless the
  candidate's recorded `v2_advisory.outcome == "VARIANT"` (F4
  correction: the original "any V2 outcome" clause is rejected).
  `NON_MATCH`, `ADVISORY_NO_FIRE`, and `RUNTIME_FAILURE` are
  **disallowed** at the confirm path (F4: `confirm_review_candidate`
  enforces outcome=match-or-variant; runtime failures are not
  confirmable).
* The existing HUMAN_CONFIRMED / REVIEWED_PRICE arithmetic
  (`aggregate_reviewed_listing_prices`) is **unchanged** (F4): the new
  clauses only **add** sources of HUMAN_CONFIRMED, never modify how a
  HUMAN_CONFIRMED row is treated.

### 4.3 SV2-C2.5 — Versioned advisory classification boundary (FU1 F2 correction)

The FU1 review is explicit: do not add `VARIANT` or
`INSUFFICIENT_EVIDENCE` directly to frozen prompt 2.0,
`V2SemanticDecision`, or the existing ledger schema. The amendment
complies as follows:

* **Frozen prompt 2.0**: unchanged. No new member is added. The new
  advisory outcome vocabulary is **not** rendered by the frozen
  prompt.
* **Frozen `V2SemanticDecision`** (`research/semantic_authority_v2.py`:
  `MATCH / NO_MATCH / UNCERTAIN`): unchanged.
* **Frozen `SemanticDecision`** (`semantic/contract.py`: `MATCH /
  NO_MATCH / UNCERTAIN`): unchanged.
* **Frozen `SemanticDecisionRecord` schema** (`runs/models.py`: opaque
  JSON payload, `schema_version=1` envelope, codec
  `research/semantic_decision_codec.py`): unchanged. The unique
  binding `(run, assessment_index)` is unchanged.
* **New advisory classification boundary**: the new V2 advisory lives
  under a **new registered contract adapter** of the existing
  `SemanticDecisionRecord` envelope. The new adapter registers
  through `research/semantic_decision_codec.py` — a pure code-path
  addition, never a model change. The new adapter's payload contains
  a single additive top-level `v2_advisory` section with the
  `class / outcome / evidence_facts / provenance /
  hard_conflict_check` fields defined in §4.1. **The frozen S2-C
  payload fields are unchanged**: the new section is a sibling, not
  a replacement. **Historical records decode identically**: the new
  adapter is opt-in at the codec dispatch boundary; existing rows
  decode under the existing S2-C adapter.
* **Candidate class storage**: the `class` is derived from the
  `(decision, rejection_reason, candidate_evidence_source, FU3A
  observation shape)` tuple at admission time and recorded in the
  `v2_advisory.class` field. It is **not** stored as a column on
  `AiAssistedReviewCandidate` (FU1 F3: no new model fields); the
  existing `semantic_reason_code` carries an optional bounded
  advisory-class tag (`V2_ADVISORY_TITLE_MPN` etc.) for display
  provenance only.
* **Decision storage**: the `outcome` is recorded in
  `v2_advisory.outcome`. The frozen S2-C payload's `decision` field
  remains a frozen `V2SemanticDecision` value; the new advisory
  outcome does **not** replace it.
* **Evidence storage**: the `evidence_facts` are recorded as a
  structured list of `CandidateObservationFactV2` values with their
  `CandidateEvidenceSourceV2` provenance. The frozen S2-C payload's
  `product_evidence` field remains the authority-side profile
  (`ProductEvidenceProfileV2`); the new `evidence_facts` are
  model-observation evidence (separate vocabulary, separate role).
* **Provenance storage**: the `provenance` carries the bounded S2-A
  derived state snapshot at admission
  (`IdentityStateV2` + `UncertainSubstateV2` +
  `IdentityRelationshipSignal` set).
* **Replay identity**: the existing `SemanticDecisionRecord` row
  primary key (UUID) and the `(run, assessment_index)` binding are
  unchanged. The new contract adapter adds a `contract` field value
  distinct from `S2-C`; the codec dispatches on the recorded contract
  string. Existing rows continue to decode under `S2-C`; new rows
  decode under the new adapter; both decode fail-closed for any
  unknown contract string.

**Any actual new model-output semantics (FU1 F2)** — meaning any new
member of the prompt-rendered vocabulary or any change to the model
output JSON shape — require a **separate qualification and version
approval** under SV2-D (§7). This amendment does not propose any.

### 4.4 SV2-C4 — V2 advisory never overrides safety (the conflict precedence)

The frozen precedence `HARD_CONFLICT > HUMAN_CONFIRMED > AI authority`
is preserved verbatim. Concretely:

* Any `EvidenceDecision.ACCEPTED` listing carrying a frozen hard conflict
  class (`CAPACITY`, `INTERFACE`, `GENERATION`, `SALES_UNIT`,
  `BUNDLE`, `FAMILY`) is **out of V2's advisory reach** — V2 cannot
  downgrade, upgrade, or reclassify the conflict.
* An `outcome` of `MATCH` or `VARIANT` over a hard-conflict-class
  detection in the FU3A bounded observation set is **forbidden at the
  constructor** (the new contract adapter's post-init invariant).
* The `V2_PERF_AUTHORITY_QUALIFIED = False` / `V2_AUTHORITY_QUALIFIED = False`
  state of record remains unchanged by this amendment. Qualification
  promotion happens only under the FU4 Bundle authority program
  (currently UNAPPROVED / NOT EXECUTED).

### 4.5 SV2-C5 — Evidence-grounded matching (the audit chain)

Every V2 advisory MATCH / VARIANT / NON_MATCH outcome carries:

* The bounded observation set (each fact tagged with
  `CandidateEvidenceSourceV2` provenance), stored in the
  `v2_advisory.evidence_facts` field of the new contract adapter
  payload (§4.3).
* The frozen derived state (S2-A) at admission, stored in
  `v2_advisory.provenance`.
* The hard-conflict-class check result, stored in
  `v2_advisory.hard_conflict_check`.
* The existing `SemanticDecisionRecord` row identity (UUID + (run,
  assessment_index) binding) for replay / replay-boundary tracing —
  unchanged.

### 4.6 SV2-C6 — Suspected-variant vs Verified-variant evidence status (FU1 F6 correction)

The FU1 review requires two distinct evidence statuses for variant
admission:

| Status | Admission class | Evidence | Presentation | Authority |
| --- | --- | --- | --- | --- |
| **Suspected variant** | `V2_ADVISORY_VARIANT_SIMILARITY` | bounded FU3A observation set: at least one bounded dimension matches the requested target's `PRODUCT_FAMILY` / `GENERATION` / `CAPACITY` / `INTERFACE` from `CandidateProductEvidenceV2` | labeled as `Suspected variant — pending review`; reviewable; not in any 4A bucket | NOT identity; NOT a 4A bucket member |
| **Verified variant** | `V2_ADVISORY_VARIANT_SIMILARITY` + verified attestation | `VariantSimilarityTableV2` entry with documented manufacturer URL + retrieval instant **OR** independently auditable attestation (never edit-distance; never character-similarity; never suffix-only heuristics; never self-reported operator string treated as manufacturer authority) | labeled as `Verified variant`; reviewable; presented as a **separate comparable offer** (§4.7) | NOT identity; NOT a 4A bucket member; a separate bounded presentation block |

**Hard guards (frozen, FU1 F6):**

* **No edit-distance authority**: a candidate is **never** admitted as
  `V2_ADVISORY_VARIANT_SIMILARITY` based on MPN string similarity,
  character overlap, or suffix-only heuristics. The
  `VariantSimilarityTableV2` is the sole authority; it is append-only
  and populated only from documented manufacturer sources or explicit
  operator attestation.
* **No self-reported operator authority**: the operator-attestation
  write-path records a self-reported operator string (the same bounded
  pattern as `vendor_refresh_presentation.py::operator="web"`) — this
  is **provenance**, not authentication, and **never** manufacturer
  authority. The presentation distinguishes self-reported
  provenance from reviewed manufacturer authority (the future 8C
  hardening remains the authentication path).
* **Working Quote hard-conflict rules** (`ALWAYS_HARD_CONFLICT_CLASSES`:
  `CAPACITY`, `INTERFACE`, `GENERATION`, `SALES_UNIT`, `BUNDLE`,
  `FAMILY`) are **preserved** (F6): real capacity, interface,
  generation, accessory, bundle, and sales-unit protections are not
  weakened. A variant candidate with a hard-conflict observation is
  rejected at the constructor.
* **`V2_ADVISORY_VARIANT_SIMILARITY` requires outcome=VARIANT**: a
  variant-class candidate with outcome `MATCH` is rejected at the
  constructor (F4). `NON_MATCH`, `ADVISORY_NO_FIRE`, and
  `RUNTIME_FAILURE` cannot become a variant confirmation.

### 4.7 SV2-C7 — Working Quote / Reviewed Price / comparable-variant integration (FU1 F4 corrected)

The FU1 review requires the distinction between **same-product Reviewed
Price aggregation** and **explicitly labeled comparable-variant offer
comparison**. The amendment specifies both paths:

* **Same-product Reviewed Price aggregation** (unchanged):
  `aggregate_reviewed_listing_prices` consumes the persisted
  `CONFIRMED` review state. HUMAN_CONFIRMED rows enter the reviewed
  bucket only when they pass the frozen eligibility and binding
  checks. The new V2 advisory admission predicates (§4.2) **add**
  sources of HUMAN_CONFIRMED rows; they do not change how a
  HUMAN_CONFIRMED row is treated once persisted.
* **Explicitly labeled comparable-variant offer comparison** (NEW, FU1
  F4): a confirmed `VARIANT` outcome produces a bounded
  `V2_VARIANT_CONFIRMED_OFFER` row — **not** in the reviewed bucket,
  **not** in the Machine Price bucket, **not** in any 4A bucket. It
  lives in a separate bounded presentation block on the research
  detail page (SV2-F), with:
  * the variant label (e.g. `Verified variant — color X`,
    `Verified variant — packaging Y`, `Suspected variant — capacity
    compatible`);
  * the price, currency, units, and variant-specific sales-unit
    field (the existing `CandidateCommercialEvidenceV2.sales_unit`
    channel);
  * the bounded source URL, retrieval instant, and provenance;
  * the bounded conflict check result (capacity / interface /
    generation / sales-unit).
* **Full user path** (FU1 F4): V2 assessment (`v2_advisory.outcome`)
  → reviewable candidate (`AiAssistedReviewCandidate`) → user
  confirmation (`review_state=CONFIRMED`) → visible comparable offer
  (`V2_VARIANT_CONFIRMED_OFFER` row + bounded presentation block) with
  correct price / units / variant label. The user can REJECT or UNDO
  via the existing state machine.
* **Identity-bucket contamination prevention** (FU1 F4): a confirmed
  variant is **never** in the identity bucket
  (`EvidenceDecision.ACCEPTED` → Machine Price); it is **never** in
  the `aggregate_reviewed_listing_prices` reviewed bucket; it is
  **never** in any `PriceIntelligenceSnapshot` 4A bucket. It is a
  separate bounded artifact, presented separately.
* **`NON_MATCH` / `RUNTIME_FAILURE` review-state shortcut prohibition**
  (FU1 F4): `confirm_review_candidate` enforces that a confirmation
  is only valid when the candidate's recorded `v2_advisory.outcome`
  is `MATCH` or `VARIANT`. `NON_MATCH`, `ADVISORY_NO_FIRE`, and
  `RUNTIME_FAILURE` cannot be promoted to a confirmation under any
  path. The existing FU3B V1 confirm path is unchanged.
* **Hard safety conflicts and sales-unit controls** (FU1 F4 preserved):
  the frozen `ALWAYS_HARD_CONFLICT_CLASSES` precedence and the frozen
  `CandidateSalesUnitEvidenceV2` channel state discipline are
  preserved; a candidate with a hard-conflict observation is rejected
  at the constructor (§4.4) regardless of outcome.

### 4.8 SV2-C8 — V1 retirement / historical compatibility (the boundary)

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

### 4.9 SV2-C9 — Nonblocking V2 lifecycle (alignment with Option B, FU1 F8 corrected)

V2 advisory work is **advisory supplementary work**. Where the FU2
Option B design (NONBLOCKING supplementary V2) is the future approved
direction, this amendment's V2 advisory candidate creation is
**compatible** with Option B but does **not** presuppose it:

* V2 advisory runs on **already-published** `PriceIntelligenceSnapshot`
  data; it never blocks the main-flow publication.
* V2 advisory ledger records are **append-only**, with the same
  provenance and replay-boundary guarantees as the existing
  `SemanticDecisionRecord` shape.
* If Option B is approved in its own gate, the FU2 lifecycle (durable
  states, recovery, retry, idempotency) applies to the V2 advisory
  ledger records without further contract change.
* If Option B is rejected, the V2 advisory ledger records continue to
  be created on the existing synchronous supplementary path (the
  current FU3B integration), bounded by the existing A1 latency /
  per-attempt instrumentation.
* **Delayed V2 evidence readiness** (FU1 F8): when the FU3A bounded
  observation set is insufficient to defend an outcome (today: any
  `V2_ADVISORY_NO_MPN` candidate, since the live builder emits no
  product-dimension fact beyond `brand`), the candidate is **not**
  created (`ADVISORY_NO_FIRE` is a no-record outcome, §4.1). No
  `INSUFFICIENT_EVIDENCE` counter is recorded; the absence is the
  signal.

### 4.10 SV2-C10 — Qualification V3 and pricing-authority gating (unchanged)

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

## 4.11 End-to-end acceptance matrix (FU1 mandatory validation)

The FU1 review requires an explicit end-to-end acceptance matrix
covering eight scenarios. The matrix below is the FU1-corrected matrix
that any implementation phase descending from this amendment must
satisfy. The matrix uses the actual frozen source as authority; every
cell references the exact contract path.

| # | Scenario | Identifier signal | S2-A substate | Expected admission | Expected outcome | Expected presentation | Hard guard | Source of truth |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | **Title-MPN** (scenario 1) | `TITLE_TEXT` | `U1_TITLE_MPN` | FU3B V1 review-eligible; V2 advisory `V2_ADVISORY_TITLE_MPN` | MATCH / VARIANT / NON_MATCH | bounded display with `V2_ADVISORY_TITLE_MPN` provenance tag | confirmed = HUMAN_CONFIRMED overlay (unchanged) | `is_human_review_eligible_assessment`; FU3B tests |
| 2 | **Missing-MPN with strong product evidence** (scenario 2) | `NONE` + primary signal | `U4_NO_MPN` | **V2 advisory `V2_ADVISORY_NO_MPN` only when FU3A bounded observation contains ≥1 `PUBLISHED_STRUCTURED_FIELD` dimension beyond `brand` OR `REVIEWED_PRODUCT_CONTEXT`; today does not fire** | MATCH / VARIANT / NON_MATCH | bounded display with `V2_ADVISORY_NO_MPN` provenance tag | confirmed = HUMAN_CONFIRMED overlay; description-only similarity NEVER sufficient | `is_human_review_eligible_assessment` (additive clause); SV2-A; FU1 F1 |
| 3 | **Cosmetic suffix variant** (scenario 3) | `EXPLICIT_MPN_FIELD` with MPN_MISMATCH | not in `DETERMINISTIC_UNCERTAIN` | V2 advisory `V2_ADVISORY_VARIANT_SIMILARITY` ONLY with `VariantSimilarityTableV2` attestation | VARIANT only | separate bounded `V2_VARIANT_CONFIRMED_OFFER` block with variant label + sales-unit | confirmed variant is NEVER in identity / Machine Price / 4A bucket; confirmed variant ≠ silently promoted identity | `VariantSimilarityTableV2` (SV2-C); FU1 F4 + F6 |
| 4 | **Materially incompatible capacity/interface/generation** | `EXPLICIT_MPN_FIELD` with MPN_MISMATCH + capacity/interface/generation conflict | `DETERMINISTIC_CONFLICT` (out of V2 reach) | **NO admission** | n/a | not reviewable; not in any 4A bucket; `HARD_CONFLICT` supersession preserved | `ALWAYS_HARD_CONFLICT_CLASSES` precedence; FU1 F4 | S2-A derived state; `is_human_review_eligible_assessment` returns False |
| 5 | **Accessory / bundle / multipack / sales-unit mismatch** | `EXPLICIT_MPN_FIELD` with PARTIAL_MPN_ONLY + bundle/quantity conflict | `DETERMINISTIC_CONFLICT` (out of V2 reach) | **NO admission** | n/a | not reviewable; not in any 4A bucket; bundle / sales-unit precedence preserved | `ALWAYS_HARD_CONFLICT_CLASSES`; `CandidateSalesUnitEvidenceV2` channel discipline | S2-A derived state; `CandidateCommercialEvidenceV2` |
| 6 | **Model NON_MATCH** | any | any | review candidate exists ONLY if FU3B predicate already admits it; otherwise no candidate | NON_MATCH | no review action; no confirmation; `confirm_review_candidate` rejects NON_MATCH confirmation | FU1 F4: NON_MATCH is NEVER promoted to a confirmation | `confirm_review_candidate`; FU3B tests |
| 7 | **Model UNCERTAIN / ADVISORY_NO_FIRE** | any | any | no candidate created | ADVISORY_NO_FIRE | no review action; no record (FU1 F1: no silent acceptance via absence) | UNCERTAIN / ADVISORY_NO_FIRE NEVER becomes a record-bearing outcome | new contract adapter (§4.3); FU1 F1 + F2 |
| 8 | **Historical V1 review-candidate replay** | any V1 FU3B-eligible | any V1 FU3B | V1 review candidate record unchanged; V2 advisory `v2_advisory` section is an additive sibling under the new contract adapter | n/a | V1 review candidate + V2 advisory section (if any) replay identically from `SemanticDecisionRecord`; FU1 F3 replay integration | frozen V1 codec, V1 snapshot decoder, V1 replay boundaries, every frozen V1 test byte-identical | `SemanticDecisionRecord` codec; `replay_compact_quote_projection`; `replay_public_compact_quote_projection`; FU3B tests |
| 9 | **Concurrent / duplicate V1 and V2 candidate admission at the same (run, assessment_index)** | any | any | FU3B predicate is evaluated FIRST; if it admits, V2 clause is **not** applied; if it does not admit, V2 clause is evaluated. The `UniqueConstraint(fields=['run', 'assessment_index'])` enforces single-candidate. | n/a | exactly one `AiAssistedReviewCandidate` row at the index; FU1 F3 contradiction prevention | `is_human_review_eligible_assessment` evaluation order; unique constraint | `AiAssistedReviewCandidate.UniqueConstraint`; FU1 F3 |

**Validation discipline:**

* Use actual committed source as the authority for signatures, model
  fields, enums, and frozen tests.
* Never delete, rename, skip, xfail, deselect, or weaken existing
  tests.
* Do not alter acceptance criteria to fit current implementation.

---

## 5. Measurable success criteria (FU1 F7 corrected)

The FU1 review identifies two misleading metrics in the original
amendment: the unsupported automatic +20% bucket-count target and the
perverse `INSUFFICIENT_EVIDENCE` ≥ 5% target. The amendment replaces
both with a measurable, falsifiable, hold-out-validated metric set.
**No baseline number is fabricated**; every metric is grounded in an
existing benchmark or frozen artifact, and every metric is measured
**post-approval** against independently labeled cases.

### 5.1 Recall against independently labeled legitimately reviewable cases

| Metric | Source of truth | Measurement | Anti-metric (forbidden) |
| --- | --- | --- | --- |
| **Recall of legitimately reviewable comparison candidates** (independently labeled on a held-out test set; the existing frozen test suite already provides negative cases) | `aggregate_reviewed_listing_prices` output + the held-out label set | % of labeled reviewable candidates that surface as `AiAssistedReviewCandidate` after the FU3B + V2 advisory admission pipeline | NOT measured by currency / condition bucket count alone (FU1 F7); NOT measured by call count |

### 5.2 False inclusion against hard-negative cases

| Metric | Source of truth | Measurement | Hard guard |
| --- | --- | --- | --- |
| **False inclusion** of materially incompatible products into `HUMAN_CONFIRMED` or `V2_VARIANT_CONFIRMED_OFFER` | frozen `ALWAYS_HARD_CONFLICT_CLASSES` test cases + the held-out negative set | count of `HARD_CONFLICT` listings ever promoted to `HUMAN_CONFIRMED` + count of `V2_VARIANT_CONFIRMED_OFFER` rows whose hard-conflict check returned non-empty | MUST remain 0 (frozen precedence) |
| False inclusion of NON_MATCH / ADVISORY_NO_FIRE / RUNTIME_FAILURE into any confirmation | FU3B confirm path + V2 advisory confirm path | count of confirmations whose recorded outcome ≠ {MATCH, VARIANT} | MUST remain 0 (FU1 F4) |

### 5.3 Human-confirmed comparable offer count

| Metric | Source of truth | Measurement |
| --- | --- | --- |
| **Human-confirmed comparable offer count** (after human action) | `AiAssistedReviewCandidate` rows where `review_state=CONFIRMED`, partitioned by `evidence_source` and `v2_advisory.class` (when present) | total count + per-class breakdown |

### 5.4 Inclusion in the actual intended comparison output

| Metric | Source of truth | Measurement |
| --- | --- | --- |
| **Inclusion in the actual intended comparison output** (reviewable AND confirmed AND visible in comparison output) | the rendered comparison output (working quote, reviewed bucket, or `V2_VARIANT_CONFIRMED_OFFER` block) | count of candidates that are reviewable, confirmed, and visible; % of total reviewable candidates that reach visibility |

### 5.5 Variant labeling and unit-comparability accuracy

| Metric | Source of truth | Measurement |
| --- | --- | --- |
| **Variant labeling accuracy** | `V2_VARIANT_CONFIRMED_OFFER` rows | % of confirmed-variant rows whose variant label agrees with the held-out label (Suspected vs Verified; cosmetic vs capacity; etc.) |
| **Unit-comparability accuracy** | `CandidateSalesUnitEvidenceV2` channel | % of confirmed rows whose sales-unit channel state agrees with the held-out label; % of confirmed rows whose `kind` / `quantity` / `raw_detail` agree |

### 5.6 V1 vs V2 outcomes on the same evaluation population

| Metric | Source of truth | Measurement |
| --- | --- | --- |
| **V1 vs V2 outcomes on the same evaluation population** (same held-out cases run through FU3B-only and FU3B+V2 advisory) | the held-out set run through both pipelines | coverage delta, false-inclusion delta, agreement rate, class-level agreement (U1 / U2 / U3 / U4 / U5) |

### 5.7 Replay integrity (carried over from the original §5.5)

| Metric | Source of truth | Target |
| --- | --- | --- |
| `schema_version` versioning of `PriceIntelligenceSnapshot` | V1 codec; FU2 replay correction | Preserved |
| Replay-boundary binding primitive (`is_review_candidate_binding_valid`) | `research/matching.py` | Preserved; new admission clauses reuse |
| Cross-run / cross-snapshot / cross-attempt replay safety | PLAN §26.12 | Preserved |
| `SemanticDecisionRecord` contract adapter dispatch (existing S2-C + new V2 advisory adapter) | `research/semantic_decision_codec.py` | new adapter opt-in; existing S2-C rows decode identically |

### 5.8 Anti-metric (the "not just more calls" bar, FU1 F7)

The amendment does **not** count the following as success:

* "More semantic calls" or "lower median latency" as a primary metric.
* Currency / condition bucket-count delta as a recall proxy.
* An automatic +20% bucket target.
* An `INSUFFICIENT_EVIDENCE` ≥ 5% target (this metric was perverse:
  FU1 F7 removes it entirely; `ADVISORY_NO_FIRE` is a no-record
  outcome, not a counter).
* Fabricated baseline numbers (every metric is grounded in an
  existing frozen test or held-out labeled set).

---

## 6. Design-scope impact (per surface) — FU1-corrected

The amendment is assessed against each surface named by the direction
document.

### 6.1 Frozen V2 eligibility and conflict boundaries

* The V2 eligibility predicate `is_v2_semantic_eligible`
  (`research/semantic_v2.py`) is **unchanged**. The new V2 advisory
  admission predicates (§4.2) are separate additive predicates that
  operate on the existing inputs; they do not replace
  `is_v2_semantic_eligible` and do not modify its signature.
* The frozen S2-A derived state vocabulary and conflict precedence are
  **preserved verbatim**.
* The `ALWAYS_HARD_CONFLICT_CLASSES` is **preserved verbatim**.
* The `SemanticMatchResponseV2.__post_init__` invariant is preserved
  (FU1 F2: no `VARIANT` or `INSUFFICIENT_EVIDENCE` added to the frozen
  vocabulary).

### 6.2 Main-flow candidate description / specification evidence (FU1 F5 corrected)

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
  main flow; only the FU3A runtime may populate them. The live main-
  flow builder (`build_candidate_product_evidence_v2`) emits only
  `brand` from `PUBLISHED_STRUCTURED_FIELD` and `raw_title_text` from
  the published title; every other product dimension is explicit None.
* **`raw_reference` opaque discipline (AD-040)**: the amendment
  **never** parses opaque `raw_reference` as structured authority and
  **never** fabricates structured facts from model output (F5).

### 6.3 V2 review candidate creation (FU1 F3 corrected)

* `AiAssistedReviewCandidate` model field inventory is **re-pinned
  unchanged** (per STATUS HUMAN-REVIEW record).
* New `V2_ADVISORY_*` classes are represented as bounded provenance
  tags on the existing `semantic_reason_code` field — no new model
  fields, no new migration. The detailed class / outcome / evidence
  fields live inside the new `SemanticDecisionRecord` contract adapter
  payload (§4.3).
* The `runs/ai_assisted_review.py` write path is **unchanged** in its
  state machine; only the **admission predicate** is extended.
* The single `(run, assessment_index)` UNIQUE constraint enforces
  duplicate / contradiction prevention (FU1 F3).

### 6.4 Human confirmation eligibility (FU1 F3 + F4 corrected)

* `is_human_review_eligible_assessment` is **extended** by additive
  clauses (§4.2). The existing three predicates are preserved.
* `confirm_review_candidate` is **extended** by an outcome check
  (`v2_advisory.outcome ∈ {MATCH, VARIANT}`) for V2 advisory candidates
  (F4). The existing FU3B confirm path is unchanged.
* The 8-step review-POST validation is **preserved** in strength
  (PLAN §26.11.2).
* The persisted snapshot authority at both replay boundaries is
  **preserved** (PLAN §26.12).

### 6.5 Reviewed Price and Working Quote integration (FU1 F4 corrected)

* `aggregate_reviewed_listing_prices` is **unchanged** — the existing
  HUMAN_CONFIRMED arithmetic is preserved; the new clauses **add**
  sources of HUMAN_CONFIRMED rows.
* `V2_VARIANT_CONFIRMED_OFFER` rows are **never** in the reviewed
  bucket, **never** in any 4A bucket, **never** in Machine Price.
  They live in a separate bounded presentation block (SV2-F).
* Working Quote policy is **unchanged** — `remove_candidate_from_working_quote`
  and the V0/V1/V2 ordering remain as recorded.
* `PriceIntelligenceSnapshot` (Machine Price) is **never** mutated by
  the new clauses.

### 6.6 V1 retirement / historical compatibility

* V1 retirement is **out of scope** (SV2-C8).
* Historical V1 compatibility is **preserved**: V1 codec, V1 snapshot
  decoder, V1 replay boundaries, every frozen test.

### 6.7 Nonblocking V2 lifecycle / delayed V2 evidence readiness (FU1 F8 corrected)

* The amendment is **compatible** with FU2 Option B but does not
  presuppose it (SV2-C9).
* The existing A1 instrumentation continues to record per-attempt
  V2 latency / token usage.
* `ADVISORY_NO_FIRE` is the bounded no-record outcome for cases where
  the FU3A bounded observation set is too thin to defend a conclusion
  (§4.1, §4.3). It is not a counter; it is the absence of a record.

### 6.8 Qualification V3 and pricing-authority gates

* The amendment does **not** open the qualification gate (SV2-C10).
* The FU4 Bundle authority program remains UNAPPROVED / NOT EXECUTED;
  C2 remains DRAFT ACCEPTED / FINAL HOLD; v1.0.0 seal remains
  FINAL-HOLD.
* The C1 / C2 governance batches continue to gate any future
  implementation that would advance the qualification program.

---

## 7. Minimum viable changes (MVC) and phase dependencies — FU1 F8 corrected

Each MVC is a **bounded phase** with its own gate; **none** is approved
by this amendment. The amendment only enumerates the MVC list and the
dependencies. FU1 F8 requires each phase to have a genuinely
implementable input and output contract.

### Phase SV2-A — V2 evidence-grounded observation contract (FU3A / FU3B delta)

**Input contract (genuinely implementable):**
* The existing `CandidateProductEvidenceV2` shape
  (`research/semantic_v2.py`).
* The existing FU3A bounded observation surface (currently:
  `brand` from `PUBLISHED_STRUCTURED_FIELD`; `raw_title_text` from the
  published title; `raw_specification_text=None`).
* The existing `CandidateCommercialEvidenceV2` shape (commercial
  observation evidence with explicit `sales_unit` channel).

**Output contract (genuinely implementable):**
* An additive bounded acquisition shape that, IF AND ONLY IF a
  reviewed source is available, populates the
  `PUBLISHED_STRUCTURED_FIELD` product dimensions beyond `brand`
  (capacity, interface, generation) and the `REVIEWED_PRODUCT_CONTEXT`
  candidate-side context. **The output is a contract definition, not
  a populated payload**: the amendment documents the bounded shape;
  no live payload is fabricated.
* Live-builder output is unchanged (still `brand` only +
  `raw_title_text`) until a reviewed source is wired under a future
  approved phase.

**Scope:**
* `research/semantic_v2.py`: additive bounded observation shape
  documentation; no new members in `CandidateEvidenceSourceV2`; no
  changes to the frozen vocabulary.
* `research/identity.py`: **unchanged** (frozen).
* `research/matching.py`: **unchanged** (frozen).

**Gate (proposed):** ChatGPT independent review over the actual source
diff + the test evidence (pin suites byte-verify the frozen surface).

### Phase SV2-B — Human-review candidate admission extension

**Input contract:**
* The existing `(decision, rejection_reason, candidate_evidence_source)`
  triple from `assessment: ListingIdentityAssessment`.
* The existing `SemanticDecisionRecord` contract adapter dispatch.
* The new `VariantSimilarityTableV2` read-side guard (SV2-C).

**Output contract:**
* An extended `is_human_review_eligible_assessment` (additive clauses).
* An extended `confirm_review_candidate` outcome check.
* Zero new `AiAssistedReviewCandidate` fields.
* Zero new `SemanticDecisionRecord` columns.

**Scope:**
* `research/matching.py::is_human_review_eligible_assessment`:
  additive clauses for `V2_ADVISORY_NO_MPN` + bounded observation
  guard, `V2_ADVISORY_VARIANT_SIMILARITY` + attested-variant guard,
  and the existing three FU3B predicates preserved.
* `runs/ai_assisted_review.py::confirm_review_candidate`: outcome
  check (`v2_advisory.outcome ∈ {MATCH, VARIANT}`) for V2 advisory
  candidates. State machine otherwise unchanged.
* `runs/models.py::AiAssistedReviewCandidate`: **unchanged** in field
  inventory (re-pinned).
* `web/presentation.py` / `web/views.py`: additive provenance tags
  only — no new model fields, no new routes.

**Gate (proposed):** ChatGPT independent review; frozen pin suites
re-verify; FU3B V1 path and V1 tests remain byte-identical.

### Phase SV2-C — VariantSimilarityTableV2 (attested-variant guard, FU1 F6)

**Input contract:**
* Documented manufacturer sources (manufacturer URL + retrieval
  instant + content SHA-256).
* Explicit operator attestation (bounded self-reported provenance
  pattern, NOT authentication, NOT manufacturer authority).
* **NEVER** edit-distance, suffix-character heuristics, character
  similarity, embedding similarity, or model-inferred similarity.

**Output contract:**
* Append-only `runs.VariantSimilarityEntry` rows with provenance.
* Read-side guard clause for `V2_ADVISORY_VARIANT_SIMILARITY`
  admission (§4.6).
* Empty / absent → `V2_ADVISORY_VARIANT_SIMILARITY` does not fire.

**Scope:**
* A new `runs/models.py::VariantSimilarityEntry` model (append-only;
  provenance-bound; no similarity oracle).
* A bounded `runs/variant_similarity.py` service: read-side (guard
  clause only) + write-side (operator-attestation entry).
* Empty/absent → `V2_ADVISORY_VARIANT_SIMILARITY` does not fire.

**Gate (proposed):** ChatGPT independent review; an additive migration
(`make migrations --check --dry-run` must report "No changes detected"
after the additive migration is committed).

### Phase SV2-D — Qualification V3 (governance, NOT implementation)

**Input contract:** the FU4 / C2 / v1.0.0 governance state.

**Output contract:** governance-level decisions only; no code or
schema changes.

**Scope:**
* The C1 / C2 governance batches continue to gate any V2 advisory
  case moving to FU4 / C3 / E1 / E2 / P1 / Q1 / W1.
* The amendment does **not** open any of these gates.

**Gate:** the existing FU4 / C2 / v1.0.0 seal procedure (PLAN §26.34 /
§26.44 / §26.45 / §26.46; STATUS C2 entry).

### Phase SV2-E — V1 retirement (separate, gated)

**Input contract:** SV2-D qualification closure AND (if approved) FU2
Option B closure.

**Output contract:** a future V1-retirement design of record with
its own independent review.

**Scope:** out of scope for this amendment; documented as a separate
gated phase.

**Gate:** explicit V1-retirement design of record with its own
independent review; preserves V1 historical replay and V1 test
preservation byte-identically.

### Phase SV2-F — Working Quote / Reviewed Price / comparable-variant presentation extension

**Input contract:**
* Existing `AiAssistedReviewCandidate` rows (unchanged field inventory).
* New `V2_VARIANT_CONFIRMED_OFFER` bounded presentation block.
* Existing `web/presentation.py` presentation helpers.

**Output contract:**
* Additive provenance tags on existing presentation blocks.
* New bounded presentation block for `V2_VARIANT_CONFIRMED_OFFER`
  rows (separate from reviewed bucket and Machine Price bucket).
* No change to `aggregate_reviewed_listing_prices` arithmetic.

**Scope:**
* `web/templates/web/research_detail.html`: additive presentation
  blocks (existing reviewed bucket unchanged + new variant block).
* `web/presentation.py`: additive presentation helpers — no change
  to `aggregate_reviewed_listing_prices` arithmetic.

**Gate:** ChatGPT independent review.

### Corrected phase dependency map (FU1 F8)

```
SV2-A  ──►  SV2-B  ──►  SV2-F
   │            │           │
   │            └────► (FU2 Option B gate, independent)
   │
   └────────────►  SV2-C  ──► (SV2-B reads SV2-C attested-variant guard)
                     │
                     └────────►  SV2-D (qualification V3)
                                       │
                                       └────────►  SV2-E (V1 retirement)
```

**Hard dependencies:**

* SV2-B depends on **SV2-A** (the bounded observation contract
  defines what `V2_ADVISORY_NO_MPN` admission guards on) AND on
  **SV2-C** (the attested-variant guard is required for
  `V2_ADVISORY_VARIANT_SIMILARITY` admission).
* SV2-F depends on SV2-B (the presentation tags need the admission
  predicates).
* SV2-D is gated on the FU4 / FU2 / C2 governance and the existing
  qualification program state, **not** on this amendment.
* SV2-E is gated on SV2-D qualification closure AND (if Option B is
  approved) FU2 Option B closure.

**Compatibility statements (FU1 F8):**

* **Nonblocking Option B compatibility**: V2 advisory records are
  append-only; the FU2 lifecycle (durable states, recovery, retry,
  idempotency) applies without contract change.
* **Delayed V2 evidence readiness**: `ADVISORY_NO_FIRE` is a
  no-record outcome; no row is created when evidence is insufficient.
* **V1 retirement**: remains a separate gated phase (SV2-E).
* **Vendor Price CIDR zero-knowledge**: limited to its actual
  protected commercial-data boundary (4D-C-SEC
  `vendor_price_access_allowed` over `REMOTE_ADDR`); F-2 HOLD
  preserved; not extended to non-commercial surfaces.
* **F-2 HOLD, frozen test preservation, unqualified V2 authority
  flags**: all preserved.

---

## 8. Explicit non-scope / safety boundaries (the "do not" list) — FU1 F8 updated

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
   manufacturer sources or explicit operator attestation (SV2-C6 / §4.6).
   2A-FU1's withdrawn "delete every non-alphanumeric" lesson is preserved.
   **Edit-distance authority is forbidden**; **character-similarity
   authority is forbidden**; **self-reported operator strings are
   provenance, not authentication, not manufacturer authority** (FU1 F6).
4. **Do not override the frozen conflict precedence
   `HARD_CONFLICT > HUMAN_CONFIRMED > AI authority`.** S2-A and
   `SemanticMatchResponseV2.__post_init__` enforce this.
5. **Do not assume description / specification text exists in the main
   flow.** Only the FU3A bounded observation set is admissible for the
   new V2 advisory evidence. The live builder
   (`build_candidate_product_evidence_v2`) emits only `brand` from
   `PUBLISHED_STRUCTURED_FIELD` and `raw_title_text` from the published
   title; `raw_specification_text=None` (FU1 F5).
6. **Do not change the deterministic authority.** 2A / 3C / 4A / 4B
   contracts, constructors, and post-init invariants are byte-identical.
7. **Do not advance the qualification gate.** FU4 Bundle authority
   program state remains UNAPPROVED / NOT EXECUTED; C2 remains DRAFT
   ACCEPTED / FINAL HOLD; v1.0.0 seal remains FINAL-HOLD.
8. **Do not modify the V1 codec, the V1 snapshot decoder, or the V1
   replay boundaries.** No caller-supplied index; no caller-supplied
   `PriceAggregationResult`; no schema_version bump. The frozen
   `SemanticDecisionRecord` envelope `schema_version=1` is preserved;
   new advisory contract adapters register through
   `research/semantic_decision_codec.py` (FU1 F2).
9. **Do not add a generic LLMProvider interface.** A generic
   `LLMProvider` is planned (PLAN §14B) but **not yet implemented**;
   the existing FU3A / FU3B semantic runtime uses its own transport
   module, not a generic interface (CLAUDE.md / PLAN §14B).
10. **Do not change the security and integrity constraints.** DENIED
    pages and non-COMPLETED pages remain total zero-knowledge (F4 / F5);
    the corporate REMOTE_ADDR/CIDR gate (4D-C-SEC) is **unchanged and
    limited to its actual protected commercial-data boundary** (F8);
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
14. **Do not parse opaque `raw_reference` as structured authority**
    (AD-040, FU1 F5). The remaining JSON-LD material stays opaque; no
    business rule may parse it; no model output may fabricate
    structured facts from it.
15. **Do not promote NON_MATCH / ADVISORY_NO_FIRE / RUNTIME_FAILURE
    outcomes to a confirmation** (FU1 F4). The
    `confirm_review_candidate` outcome check is the single guard.

---

## 9. Open questions / decision gates (for the reviewer)

These are the questions whose resolution gates any future implementation
that descends from this amendment. Each question is small, on-topic, and
non-blocking on the amendment itself. FU1 corrections resolve the
previously-misframed questions; the open list below is the FU1-narrowed
set.

1. **SV2-A.1** — Should the `V2_ADVISORY_NO_MPN` admission class require
   the FU3A bounded observation to include **at least one**
   independently-attested specification match, or **at least two**
   (defense in depth)? FU1 F1 narrows the question to the count
   threshold; the FU1-corrected default is "at least one" (single
   independently-attested match) pending review.
2. **SV2-A.2** — The FU1 F2 contract makes `ADVISORY_NO_FIRE` a
   no-record outcome. Question: should the codec dispatch record a
   bounded counter for `ADVISORY_NO_FIRE` (e.g. as an
   instrumentation-only field under the new contract adapter)? The
   FU1 F7 anti-metric rejects the +5% target; the question is
   whether to record the count at all for instrumentation purposes.
3. **SV2-B.1** — Should a `VARIANT` confirmation be eligible for a
   "labeled variant" presentation block in the report (visible to the
   user), or only recorded silently in the audit ledger? FU1 F4
   defaults to a labeled, visible bounded block (SV2-C7 / SV2-F); the
   question is the exact label vocabulary.
4. **SV2-C.1** — Who is the operator identity for the attestation
   write-path? The existing `web/vendor_refresh_presentation.py`
   pattern uses a self-reported provenance (`operator="web"`); the
   `VariantSimilarityTableV2` may need the same bounded pattern OR an
   explicit identity (analogous to 8C). This is a future-phase
   decision; this amendment does not decide. FU1 F6 explicitly
   records that self-reported operator strings are provenance, NOT
   authentication, NOT manufacturer authority.
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
| `docs/PRODUCT_INTELLIGENCE_PLAN.md` §16.3 | The 3C matching contract; "no description semantics" rule; PARTIAL classification; the `_find_evidence` evidence-source vocabulary. |
| `docs/PRODUCT_INTELLIGENCE_PLAN.md` §16.4 | The 4A aggregation contract. |
| `docs/PRODUCT_INTELLIGENCE_PLAN.md` §16.5 | The 4B snapshot contract; `PriceIntelligenceSnapshot` immutability. |
| `docs/PRODUCT_INTELLIGENCE_PLAN.md` §26.11 / §26.12 | The HUMAN-REVIEW / replay-boundary corrections (FU1 / FU2); persisted snapshot authority. |
| `docs/PRODUCT_INTELLIGENCE_PLAN.md` §26.21–§26.27 | The Semantic V2 S2-A / S2-B / S2-C contracts and FU1 corrections. |
| `docs/PRODUCT_INTELLIGENCE_PLAN.md` §22.0 / §22.1 / §22.2 | The 6A / 6B / 6C framework contracts (6A not implemented; 6B frozen; 6C frozen). |
| `docs/PRODUCT_INTELLIGENCE_STATUS.md` | The current state of record (FU3A APPROVED; FU3B approved; FU2 Option B NOT YET APPROVED; F-2 deployment security HOLD OPEN; FU4 UNAPPROVED / NOT EXECUTED; C2 DRAFT ACCEPTED / FINAL HOLD). |
| `docs/SEMANTIC_V2_PERFORMANCE_DESIGN_01.md` | The Option B nonblocking supplementary V2 design (preferred architecture of record; FU2 NOT YET APPROVED). |
| `docs/LOCAL_SEMANTIC_V2_PERF_PHASE1_DIAG.md` | The Phase 0 / Phase 1 V2 performance diagnostic (APPROVED with documented evidence limitations; A1 instrumentation). |
| `product_intelligence/research/identity.py` | The frozen 2A comparator. |
| `product_intelligence/research/matching.py` | The frozen 3C matching; `EvidenceSource`; `IdentityRejectionReason`; `is_human_review_eligible_assessment`; `is_review_candidate_binding_valid`. |
| `product_intelligence/research/semantic_v2.py` | The FU3A semantic V2 vocabulary; `CandidateEvidenceSourceV2` (with `LISTING_TITLE` / `SPECIFICATION_TEXT` / `REVIEWED_PRODUCT_CONTEXT` RESERVED members); `CandidateProductEvidenceV2`; `CandidateCommercialEvidenceV2`; `SalesUnitKindV2`; `is_v2_semantic_eligible`. |
| `product_intelligence/research/semantic_authority_v2.py` | The frozen `V2SemanticDecision` vocabulary (`MATCH / NO_MATCH / UNCERTAIN`). |
| `product_intelligence/semantic/contract.py` | The frozen `SemanticDecision` vocabulary (`MATCH / NO_MATCH / UNCERTAIN`). |
| `product_intelligence/research/semantic_decision_codec.py` | The `SemanticDecisionRecord` codec; contract adapter dispatch. |
| `product_intelligence/research/aggregation.py` | The frozen 4A aggregation + `aggregate_reviewed_listing_prices`. |
| `product_intelligence/research/price_result_codec.py` | The V1 codec + `decode_price_aggregation_result`. |
| `product_intelligence/execution/semantic_integration.py` | `AiAssistedMatchResult`; `SemanticRuntimeResult`; FU3B V1 admission path. |
| `product_intelligence/runs/ai_assisted_review.py` | The HUMAN-REVIEW write path; the review-state machine. |
| `product_intelligence/runs/models.py` | `PriceIntelligenceSnapshot`; `ResearchSupplementSnapshot` (4D-B, Vendor API commercial data); `ResearchFxSnapshot`; `AiAssistedReviewCandidate` (with the field inventory and the `(run, assessment_index)` UNIQUE constraint); `SemanticDecisionRecord` (opaque versioned JSON payload, `schema_version=1` envelope). |
| `product_intelligence/execution/compact_quote_replay.py` | The replay-boundary authority (`replay_compact_quote_projection`, `replay_public_compact_quote_projection`, `derive_human_confirmed_assessment_indices`). |
| `tests/web/test_web_boundaries.py` | The web-layer import allowlist enforcement. |
| `tests/runs/test_vendor_refresh_*` (and the other frozen pin suites) | The frozen pin suites that byte-verify the frozen surface. |

---

## 11. Closing gate statement (FU1 status)

This amendment is **design only**. It proposes a bounded contract
delta (§4), an explicit end-to-end acceptance matrix (§4.11),
measurable success criteria (§5), and minimum viable changes (§7).
It does **not** implement code, **does not** change tests, **does
not** weaken any frozen contract, **does not** activate V2 pricing
authority, and **does not** change the qualification program state.

FU1 review verdict: **CHANGES REQUESTED — DESIGN ONLY**. F1–F8
corrections are applied in place in this document:

* F1 — admission predicate now separates identifier signals
  (`EvidenceSource`), V2 semantic product-evidence signals
  (`CandidateEvidenceSourceV2`), and S2-A derived state; the
  `V2_ADVISORY_NO_MPN` clause does not silently route from
  `EvidenceSource.NONE` (it requires the FU3A bounded observation
  guard; today the live builder emits no such fact, so the clause
  does not fire until SV2-A).
* F2 — `VARIANT` and `INSUFFICIENT_EVIDENCE` are NOT added to the
  frozen `V2SemanticDecision`, `SemanticDecision`, or frozen prompt
  2.0; the new advisory lives under a new registered contract
  adapter of the existing `SemanticDecisionRecord` envelope as an
  additive `v2_advisory` section; historical records decode
  identically.
* F3 — new admission predicates are additive and operate only on
  inputs already available to `is_human_review_eligible_assessment`;
  idempotency is the existing `(run, assessment_index)` UNIQUE
  constraint; provenance binding is
  `is_review_candidate_binding_valid`; confirmation state is
  `review_state`; replay is the existing replay-boundary authority;
  V1 path and tests byte-identical.
* F4 — same-product Reviewed Price aggregation is unchanged;
  variant confirmation produces a bounded
  `V2_VARIANT_CONFIRMED_OFFER` row in a separate bounded presentation
  block; NON_MATCH / ADVISORY_NO_FIRE / RUNTIME_FAILURE cannot be
  confirmed; hard safety conflicts and sales-unit controls
  preserved.
* F5 — `PriceIntelligenceSnapshot` is the canonical listing identity
  assessment source; `ResearchSupplementSnapshot` is Vendor API
  commercial data (not identity source); the FU3A runtime does NOT
  independently fetch description/spec text; bounded extraction is
  the existing `CandidateProductEvidenceV2`; `raw_reference` opaque
  discipline (AD-040) preserved.
* F6 — Suspected-variant and Verified-variant evidence statuses
  separated; no edit-distance authority; no character-similarity
  authority; self-reported operator strings are provenance, not
  authentication, not manufacturer authority; Working Quote hard-
  conflict rules preserved.
* F7 — bucket-count target and `INSUFFICIENT_EVIDENCE` ≥ 5% target
  removed; success metrics replaced with recall against labeled
  cases, false inclusion, human-confirmed comparable offer count,
  inclusion in intended comparison output, variant labeling /
  unit-comparability accuracy, and V1 vs V2 outcomes on the same
  evaluation population; no fabricated baselines.
* F8 — each phase SV2-A through SV2-F has a genuinely implementable
  input / output contract; phase dependency map corrected;
  compatibility with Option B and delayed V2 evidence readiness
  clarified; V1 retirement remains a separate gated phase; Vendor
  Price CIDR zero-knowledge limited to its actual protected
  commercial-data boundary; F-2 HOLD, frozen test preservation, and
  unqualified V2 authority flags preserved.

**Status: SEMANTIC-V2-PRODUCT-CONTRACT-FU1 — PENDING CHATGPT REVIEW.**

The next step is ChatGPT independent review over this corrected
document. Any implementation that descends from this amendment is
itself a bounded phase with its own design of record, its own
migration / corpus / schema discipline, its own test-preservation
record, and its own independent review — **none of which is approved
by this amendment**.
