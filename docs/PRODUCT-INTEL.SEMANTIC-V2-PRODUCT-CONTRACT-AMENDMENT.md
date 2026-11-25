# PRODUCT-INTEL.SEMANTIC-V2 — Product-Contract & Architecture-Impact Amendment

> **Document role.** This is a bounded **contract amendment** for ChatGPT
> product / architecture review. It is **design only**: no implementation,
> no test changes, no corpus labels, no schema change in this artifact
> (two additive, default-preserving migrations are prescribed for their
> gated implementation phases — §4.3 / §4.9 — and are not written by
> this amendment), no qualification promotion,
> no V2 pricing-authority activation, and no change to the existing security
> or integrity constraints. The artifact restates the corrective product
> direction, audits it against the actual frozen architecture and extraction
> capabilities, defines the contract delta, names measurable success criteria,
> and lists the minimum viable changes (MVC) with their phase dependencies.
>
> **FU1 review status.** ChatGPT FU1 review of commit
> `4c2388937ba00882ca9d72250d347004bfaef808` returned
> **CHANGES REQUESTED — DESIGN ONLY**. This document corrected in place
> (F1–F8) without creating a replacement. It did not advance any
> implementation, qualification, or authority flag.
>
> **FU2 review status.** ChatGPT FU2 review of commit
> `f164730ba20117e76a76b0eb4a1a6b06088ec089` returned
> **CHANGES REQUESTED — DESIGN ONLY**. This document corrects in place
> (C1–C7, plus the mandatory end-to-end proof specifications) without
> creating a replacement. It does not advance any implementation,
> qualification, or authority flag, and does not activate V2 authority:
> the versioned run-level review policy of record (§4.9) remains
> `V1_FIRST`, and the frozen V2 authority flags remain `False`.
>
> **FU2 correction index.** C1 — U4 source-state analysis fixed against the
> actual `derive_identity_state_v2` (NONE + usable title already derives
> `U4_NO_MPN` and is V2-execution-eligible; execution eligibility /
> available evidence / human-review eligibility separated; impossible
> `NONE AND (TITLE_TEXT OR SKU_FIELD)` condition removed; no new U4
> substate). C2 — executable versioned V2 review-admission boundary whose
> inputs include the persisted, verified V2 ledger evidence; the
> assessment-only V1 predicate is frozen and carries no V2 authority.
> C3 — ledger/adapter coexistence resolved against the actual four-adapter
> registry, the `(run, assessment_index)` unique binding, and the
> append-only write path: the advisory classification is stored on the
> review candidate (smallest representation), never in a new ledger row or
> by rewriting a V2-PERF row. C4 — separate price authority for variants:
> the actual confirmation / replay / reviewed-price paths are traced and an
> explicit testable data + projection boundary is specified. C5 — smallest
> versioned run-level review policy for V2-primary migration (not
> activated). C6 — suspected vs verified variant discovery separated;
> the actual complete `ALWAYS_HARD_CONFLICT_CLASSES` set documented;
> the frozen-contract redesign for otherwise-excluded MPN mismatches is
> named as a separate gated phase (SV2-G). C7 — evidence acquisition and
> the actual MVP against the real `ListingObservation` published fields;
> unknown sales units stay unknown.
>
> Frozen-phrase reference. Where this document uses a phrase that already
> has a binding definition in `CLAUDE.md`, `docs/PRODUCT_INTELLIGENCE_PLAN.md`,
> or `docs/PRODUCT_INTELLIGENCE_STATUS.md`, the binding definition
> controls; this document does not redefine it.

---

## 0. Status of this artifact (gate)

| Property | Value |
| --- | --- |
| Phase | Pre-design — product-contract amendment for ChatGPT review (FU1 corrections F1–F8 and FU2 corrections C1–C7 applied in place) |
| Implementation | **None.** No code, no test, no migration, no corpus label, no authority flag, no schema, no pricing wiring, no prompt, no model call, no seal artifact, no qualification. |
| Dependents | None. This amendment does not modify `CLAUDE.md`, `PRODUCT_INTELLIGENCE_STATUS.md`, or `PRODUCT_INTELLIGENCE_PLAN.md`. Status / PLAN update happens only under a later approved implementation phase. |
| Authority state of record (carried over, unchanged) | `V2_AUTHORITY_QUALIFIED = False`, `V2_PERF_AUTHORITY_QUALIFIED = False`, FU2 Option B **NOT YET APPROVED**, FU4 Bundle authority program state **UNAPPROVED / NOT EXECUTED**, C2 corpus state **DRAFT ACCEPTED / FINAL HOLD**, v1.0.0 seal **FINAL-HOLD**. |
| Deployment security | F-2 ambient `PI_VENDOR_PRICE_ALLOWED_CIDRS` HOLD **OPEN** — untouched; the CIDR zero-knowledge requirement remains limited to its actual protected commercial-data boundary (4D-C-SEC `vendor_price_access_allowed` over `REMOTE_ADDR`) and is NOT extended to non-commercial surfaces by this amendment (F8). |
| FU1 review verdict | CHANGES REQUESTED — DESIGN ONLY. F1–F8 corrections applied in this document. |
| FU2 review verdict | CHANGES REQUESTED — DESIGN ONLY (reviewed commit `f164730ba20117e76a76b0eb4a1a6b06088ec089`). C1–C7 corrections + the mandatory end-to-end proof specifications applied in this document. |
| Product requirement of record | Semantic V2 must eventually replace V1 as the **primary review engine** — not merely supplement V1 for otherwise-ineligible candidates — while increasing access to genuinely comparable products and preserving hard safety exclusions and price-result integrity. The versioned run-level review policy (§4.9) is the migration mechanism; this amendment designs it but does **not** activate it. |

---

## 1. Authoritative product goal (re-statement, scope-bounded)

Semantic V2 is intended to **replace** Semantic V1 as the primary
intelligent matching and review engine for Product Intelligence.

The business problem it must solve is **insufficient usable comparable
samples**, driven by overly restrictive identity filtering and review
eligibility, with three named real customer scenarios:

| # | Scenario | Deterministic 3C behavior today | Semantic V2's potential role |
| --- | --- | --- | --- |
| 1 | Requested MPN appears in listing **title** but no explicit structured MPN field exists. | `REJECTED` + `NO_EXPLICIT_MPN_EVIDENCE` + `TITLE_TEXT`. Today: **V2-execution-eligible** (`U1_TITLE_MPN`; `is_v2_semantic_eligible` = True) and human-review-eligible (FU3B clause). | Evaluate as an **advisory** same-product / variant candidate; surface as a review candidate. Never auto-accept. |
| 2 | Candidate MPN is **missing**, but product description and independently supported specifications are strongly consistent with the requested product. | `REJECTED` + `NO_EXPLICIT_MPN_EVIDENCE` + `NONE`. Today: **V2-execution-eligible via the EXISTING `U4_NO_MPN` substate** when the listing carries a usable product title (`derive_identity_state_v2` routes `NONE` + usable title to `U4_NO_MPN`, primary signal `NO_RELATION`; no new substate — C1), but **NOT human-review-eligible** (the FU3B clause excludes `NONE`) and the available bounded evidence is thin (live builder: brand + raw title + commercial facts only; no structured product-dimension fact, no specification text). | A versioned V2 review-admission boundary (§4.2) + grounded evidence acquisition (SV2-A, §4.11) are required. Advisory only. |
| 3 | Candidate MPN differs by a **suffix** that may represent color, cosmetic appearance, or another non-critical variation. | `REJECTED` + `MPN_MISMATCH` + explicit MPN source. Today: V2-execution-eligible **only in the bounded near-miss shapes** — NM-1 (strict prefix over the frozen normalized keys, i.e. a pure suffix addition) and NM-2 (same length, one substituted character) derive `U5_NEAR_MISS_MPN`; any other shape derives `C1_INCOMPATIBLE_EXPLICIT_MPN` (`DETERMINISTIC_CONFLICT`) and is **not V2-execution-eligible** under the frozen S2-A mapping — an explicit frozen-contract redesign is required for those shapes (SV2-G, §4.6). Some suffix cases also surface as `PARTIAL` (`REJECTED` + `PARTIAL_MPN_ONLY`, today V2-execution-eligible via `U3_PARTIAL_BOUNDARY` and human-review-eligible). | Treat as a **V2-advisory VARIANT candidate** discovered from the persisted V2 evaluation (suspected — no pre-existing attestation required, C6); a verified attestation upgrades the label (SV2-C). **Never** treat arbitrary MPN suffix similarity as proof of equivalence. **Never** auto-accept. Suspected vs verified evidence statuses are separated (§4.6). |
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
  none of which are open or approved today). V2 becomes the **primary
  review engine** only through the versioned run-level review policy
  (§4.9) after that qualification and an explicit approval — this
  amendment designs the policy but keeps it at `V1_FIRST`.
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
  the same-product Reviewed Price bucket may gain HUMAN_CONFIRMED rows
  only through the frozen `aggregate_reviewed_listing_prices` (V1
  same-product confirmations) or the versioned `reviewed-price/2`
  boundary (§4.7, V2 same-product confirmations — identical frozen
  arithmetic); V2 **variant-class** confirmations are NOT a path into
  any 4A bucket, reviewed bucket, or Machine Price — see C4 / §4.7).
* A V2 MATCH never becomes `EvidenceDecision.ACCEPTED`
  (CLAUDE.md / PLAN §16.3 / `runs/ai_assisted_review.py` are explicit:
  "Confirming a candidate NEVER changes EvidenceDecision to ACCEPTED").
* A V2 MATCH never causes a deterministic-identity-eligible listing to
  become ineligible (V2 can only ADMIT additional human-review candidates,
  not strip currently-eligible ones).

The amendment therefore proposes **advisory, evidence-grounded** V2
expansion — and, through the versioned run-level review policy (§4.9),
V2's eventual replacement of V1 as the **primary review engine** —
never V2 replacement of the deterministic identity authority.

---

## 3. Audit of current extraction and evidence capabilities (the real main flow) — FU1/FU2-corrected

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
| `NONE` | No candidate identifier was found | REJECTED + NO_EXPLICIT_MPN_EVIDENCE | **V2-execution-eligible when the listing carries a usable product title**: the actual `derive_identity_state_v2` (`research/semantic_authority_v2.py`) maps `NONE` + usable title to `U4_NO_MPN` (primary signal `NO_RELATION`; `is_v2_semantic_eligible` = True — U4 is the explicit "no-MPN usable-title recall" entry point of the frozen S2-A contract). `NONE` without a usable title derives `E2_NO_CANDIDATE_EVIDENCE` (unevaluable, not V2-execution-eligible). **NOT human-review-eligible** (the FU3B clause excludes `NONE`). Live builder: brand (when published) + raw title text only — no product-dimension facts (C1 / §4.1) |
| Product description / specification text | Not carried by 3C; not read by `assess_listing_identity`; "Any future description/category/comparable semantic interpretation belongs to a later explicitly approved phase" (PLAN §16.3). 6A / 6B / 6C framework contracts exist; **6A is not implemented**; 6B implements the Enterprise SSD category schema (frozen); 6C implements deterministic structured extraction. The main flow today does **not** carry a description or specification payload into semantic V2. | n/a (description not read) | `SPECIFICATION_TEXT` is **RESERVED**; `REVIEWED_PRODUCT_CONTEXT` is **RESERVED**; `CandidateProductEvidenceV2.raw_specification_text` is explicit `None` from the live builder — the actual MVP that changes this is SV2-A (§4.11) |

**C1 correction of record (FU2).** The FU1 text of this table claimed that
"`EvidenceSource.NONE` itself does NOT route to `U4_NO_MPN`" and that U4
is "admitted only when a primary signal exists (TITLE_MPN_TOKEN or
SKU_EQUALS_REQUESTED)". Both statements are wrong against the actual
implementation: `TITLE_MPN_TOKEN` is the `U1_TITLE_MPN` primary signal and
`SKU_EQUALS_TARGET` / `SKU_NOT_TARGET` are the `U2_SKU_ONLY` primary
signals; the `U4_NO_MPN` primary signals are `NO_RELATION` (the `NONE`
source) and `EMPTY_MPN_FIELD` (an explicit MPN field with no
part-number content after the frozen wrapper cleanup). A `NONE` source
with a usable product title **already derives `U4_NO_MPN` and is
V2-execution-eligible today**; no new U4 substate is introduced by this
amendment. The three layers the FU1 text collapsed are separated here and
used throughout §4:

| Layer | Actual source of truth | `NONE` + usable title today | `NONE` without usable title today |
| --- | --- | --- | --- |
| **V2 execution eligibility** (may the V2 runtime evaluate this candidate?) | `is_v2_semantic_eligible` (`research/semantic_v2.py`) over `derive_identity_state_v2` (`research/semantic_authority_v2.py`): `DETERMINISTIC_UNCERTAIN` (U1–U5) only | **Eligible** (`U4_NO_MPN`) | Not eligible (`E2_NO_CANDIDATE_EVIDENCE`) |
| **Available bounded evidence** (what the model can actually see) | `build_candidate_product_evidence_v2` + `build_candidate_commercial_evidence_v2` (`research/semantic_v2.py`) as recorded in the persisted V2 case | brand (when published) + `raw_title_text` (RAW) + published commercial facts; sales-unit channel always `UNAVAILABLE`; no product-dimension fact, no specification text | same, minus a usable title (the frozen V1 usability gate) |
| **Human-review eligibility** (may a review candidate be created?) | `is_human_review_eligible_assessment` (`research/matching.py`) — the frozen FU3B triple | **NOT eligible** (FU3B excludes `NONE`) — the versioned V2 admission boundary (§4.2) is the new path; the V1 predicate is unchanged | not eligible (also not V2-executed) |

**Implication for the direction's four scenarios (FU1 F1 + F5, FU2 C1-corrected):**

1. **Title-MPN (scenario 1).** Identifier signal = `TITLE_TEXT`; V2
   semantic product-evidence signal = the bounded title text carried as
   `raw_title_text` (RAW observation text, not a structured fact).
   S2-A substate = `U1_TITLE_MPN`. Existing V2 eligibility and human
   review eligibility **preserved** (FU3B clause).
2. **Missing-MPN with description + spec consistency (scenario 2).**
   Identifier signal = `NONE`. V2 execution eligibility: **already exists**
   — `NONE` + usable title derives `U4_NO_MPN` and passes
   `is_v2_semantic_eligible` (C1; no new substate, no new execution
   route). V2 semantic product-evidence signal today: **the live builder
   emits no structured product-dimension fact for this case**
   (`raw_title_text` is present when the title is; `PUBLISHED_STRUCTURED_FIELD`
   carries only brand; `SPECIFICATION_TEXT` and `REVIEWED_PRODUCT_CONTEXT`
   are RESERVED; `raw_specification_text = None`). What is missing, and
   what §4.11 (SV2-A) supplies, is (a) the **bounded evidence
   acquisition** that lets the persisted V2 case carry grounded
   specification evidence, and (b) the **versioned V2 review-admission
   boundary** (§4.2) that may create a review candidate from the
   persisted V2 outcome — the frozen assessment-only V1 predicate
   `is_human_review_eligible_assessment` is NOT extended and remains
   False for `NONE` (FU1 F1, corrected: the impossibility was the FU1
   admission clause, not the V2 execution route). **Until SV2-A is
   approved and live, a `NONE`-source candidate is V2-executed (ledger
   evidence preserved) but same-product review admission does not fire**
   because the grounded-evidence bar (§4.1) is not met — an explicit,
   explainable state, never a silent route.
3. **Cosmetic suffix variant (scenario 3).** Identifier signal mismatch →
   `MPN_MISMATCH` + explicit MPN source. S2-A substate today: the bounded
   near-miss shapes only — NM-1 (strict prefix over the frozen normalized
   keys, i.e. a pure suffix addition) and NM-2 (same length, exactly one
   substituted character) derive `U5_NEAR_MISS_MPN` (V2-execution-
   eligible); any other shape derives `C1_INCOMPATIBLE_EXPLICIT_MPN`
   (`DETERMINISTIC_CONFLICT`, not V2-execution-eligible) — those shapes
   are the "otherwise-excluded MPN mismatches" that require the explicit
   frozen-contract redesign SV2-G (§4.6), not a silent route through
   `is_v2_semantic_eligible`. Suspected-variant discovery is keyed on the
   persisted V2 evaluation (a recorded `MATCH` carrying a REVIEWABLE
   conflict class and no ALWAYS_HARD class — §4.6); it does **not**
   require a pre-existing attestation record (C6) and does not depend on
   edit-distance or character-similarity heuristics.
4. **Genuinely different product (scenario 4).** No new admission. The
   frozen conflict precedence and the `ALWAYS_HARD_CONFLICT_CLASSES`
   precedence (the actual complete ten-member set — `MPN_IDENTITY`,
   `PRODUCT_FAMILY`, `GENERATION`, `CAPACITY`, `INTERFACE`,
   `FORM_FACTOR`, `PRODUCT_ROLE`, `ACCESSORY_RELATION`,
   `PACKAGING_QUANTITY`, `BUNDLE` — §4.6) are preserved (F4 / §4.4).

### 3.2 What the FU3A / FU3B semantic runtime already carries

`product_intelligence/research/semantic_v2.py` defines bounded candidate
observation facts with provenance (`CandidateEvidenceSourceV2`) and a
frozen S2-A derived state vocabulary. The semantic runtime already
admits the five uncertain substates (`U1_TITLE_MPN`, `U2_SKU_ONLY`,
`U3_PARTIAL_BOUNDARY`, `U4_NO_MPN`, `U5_NEAR_MISS_MPN`) via
`is_v2_semantic_eligible`. What is missing differs by scenario: for
scenario 2 the **V2 execution admission already exists** (U4 is an
explicit S2-A entry point) — what is missing is the bounded observation
surface the model can draw on (SV2-A / §4.11) and the versioned
review-admission boundary (C2 / §4.2); for scenario 3 the in-shape
near-miss candidates (U5) are already V2-execution-eligible — what is
missing is suspected-variant classification from the persisted
evaluation (C6 / §4.6), the attestation table for the VERIFIED tier
(SV2-C), and — for the out-of-shape `MPN_MISMATCH` candidates the frozen
S2-A mapping keeps at `C1_INCOMPATIBLE_EXPLICIT_MPN` — an explicit
frozen-contract redesign (SV2-G / §4.6).

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
  keyed on `(run, assessment_index)`, unique per binding, append-only
  through the single service write path (`persist_semantic_decision`
  never overwrites; the `payload_digest` column anchors every read).
  The codec (`research/semantic_decision_codec.py`) registers FOUR
  contract adapters (V1, V2, V2-FU4, V2-PERF) and dispatches on the
  full recorded five-axis contract binding (singleton-claim, fail
  closed). The live V2 path writes the V2-PERF record
  (`SemanticDecisionRecordV2Perf`, binding
  `(V2, 2.0, 1, 2, SEMANTIC_AUTHORITY_V2_S2A_FU2)`) for every
  V2-executed candidate — ALL outcomes (MATCH / NO_MATCH / UNCERTAIN /
  RUNTIME_FAILURE), each row recording the full V2 case (the persisted
  V2 input) and response. The frozen `schema_version=1` envelope and
  every existing payload shape are preserved; **no new adapter is
  registered and no row is modified or rewritten by this amendment** —
  the FU1 "new `v2_advisory` section under a new contract adapter"
  design is infeasible against the unique binding + append-only
  write path and is withdrawn (C3 / §4.3). The advisory
  classification lives on the review candidate instead (§4.3).
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
V2 review path is conditioned on the persisted, verified V2 ledger
evidence and the FU3A / FU3B bounded observation contract, and is
**never** a path to `EvidenceDecision.ACCEPTED`. None of the clauses
below activate pricing authority or new authority; the ONLY schema
deltas the clauses prescribe are the two recorded additive migrations
— one nullable `v2_review_admission` JSONField on
`AiAssistedReviewCandidate` (§4.3, C3) and one `review_engine_policy`
choices column on `ResearchRun` defaulting to `V1_FIRST` (§4.9, C5) —
each additive, default-preserving, and gated to its implementation
phase.

### 4.1 SV2-C1 — V2 advisory classification (the FU2-corrected admission contract)

**Three-signal admission contract (FU1 F1, re-anchored by FU2 C1).**

The admission contract operates on **three separated signals**:

| Signal | Source of truth | Vocabulary |
| --- | --- | --- |
| **Identifier signal** | `_find_evidence()` in `research/matching.py` | `EvidenceSource ∈ {EXPLICIT_MPN_FIELD, VISIBLE_LABELED_MPN_FIELD, SKU_FIELD, TITLE_TEXT, NONE}` (frozen) |
| **V2 semantic product-evidence signal** | FU3A bounded observation set (`CandidateProductEvidenceV2` from `research/semantic_v2.py`) as **recorded in the persisted V2 case** | `CandidateEvidenceSourceV2 ∈ {PUBLISHED_STRUCTURED_FIELD, LISTING_TITLE (RESERVED), SPECIFICATION_TEXT (RESERVED), REVIEWED_PRODUCT_CONTEXT (RESERVED)}` (frozen) |
| **S2-A derived state** | `derive_identity_state_v2` in `research/semantic_authority_v2.py` | `IdentityStateV2.DETERMINISTIC_UNCERTAIN` with `UncertainSubstateV2 ∈ {U1_TITLE_MPN, U2_SKU_ONLY, U3_PARTIAL_BOUNDARY, U4_NO_MPN, U5_NEAR_MISS_MPN}` (frozen) |

**Three-layer separation (FU2 C1, correction of record).** The FU1 text
repeatedly collapsed "V2-eligible", "evidence available", and
"human-review-eligible" into one condition, and mis-stated the `NONE`
source-state analysis. Against the actual implementation
(`derive_identity_state_v2`, `research/semantic_authority_v2.py`):

* **V2 execution eligibility** — `is_v2_semantic_eligible` (true iff the
  derived state is `DETERMINISTIC_UNCERTAIN`). A `NONE` source with a
  usable product title **already derives `U4_NO_MPN`** (primary signal
  `NO_RELATION`) and is V2-execution-eligible **today**; `NONE` without a
  usable title derives `E2_NO_CANDIDATE_EVIDENCE` (not eligible); an
  explicit MPN field with no part-number content derives `U4_NO_MPN` with
  primary signal `EMPTY_MPN_FIELD`. **No new U4 substate is introduced** —
  the FU1 condition "`NONE` AND a primary signal present (TITLE_TEXT OR
  SKU_FIELD)" was impossible (the identifier signal is a single value;
  `TITLE_TEXT` / `SKU_FIELD` are the U1 / U2 sources, not U4 primary
  signals) and is removed.
* **Available bounded evidence** — what the live builder actually records
  in the V2 case: brand (`PUBLISHED_STRUCTURED_FIELD`) when published,
  `raw_title_text` (RAW), the published commercial facts, and the
  sales-unit channel (always `UNAVAILABLE` from the main flow). No
  product-dimension fact beyond brand and no specification text are
  published by the live builder today; execution eligibility does not
  depend on that, but same-product review admission does (§4.1 grounded
  bar).
* **Human-review eligibility** — the frozen assessment-only V1 predicate
  `is_human_review_eligible_assessment` (`research/matching.py`), which
  returns True for exactly the FU3B triple (`TITLE_TEXT`, `SKU_FIELD`,
  `PARTIAL_MPN_ONLY`) and **remains frozen and unchanged** (C2). The new
  versioned V2 admission boundary (§4.2) is a separate predicate with
  separate inputs; it does not extend the V1 predicate and the V1
  predicate does not carry implicit V2 authority.

**Advisory classification (FU2 C3/C6 correction).** The FU1 five-class /
four-outcome table is superseded. There is **no new model output
vocabulary** (frozen `V2SemanticDecision` = `MATCH / NO_MATCH /
UNCERTAIN` only; frozen prompt 2.0 unchanged). The advisory
classification is a **deterministic derivation over the persisted, verified
V2 ledger record** (`SemanticDecisionRecordV2Perf`, decoded through
`load_semantic_decision` — digest-verified, codec-verified), the
re-derived S2-A state, and the variant-attestation guard: two orthogonal
axes, persisted together on the review candidate (§4.3):

* **Admission provenance** — the S2-A uncertain substate the candidate
  was V2-executed under: `U1_TITLE_MPN`, `U2_SKU_ONLY`,
  `U3_PARTIAL_BOUNDARY`, `U4_NO_MPN`, `U5_NEAR_MISS_MPN` (frozen
  vocabulary; display + audit only; carries no authority).
* **Advisory class** — the authority class the classification assigns:
  * `V2_ADVISORY_SAME_PRODUCT` — recorded `MATCH`, no ALWAYS_HARD and no
    REVIEWABLE conflict class recorded (the model asserts same product
    with no material recorded conflict); **plus the grounded-evidence bar
    for `U4_NO_MPN` provenance**: the persisted V2 case must carry at
    least one `PUBLISHED_STRUCTURED_FIELD` product-dimension fact beyond
    `brand` (e.g. capacity, interface, generation) or a
    `REVIEWED_PRODUCT_CONTEXT` candidate-side context —
    description-only / title-only similarity is never sufficient. The
    live builder emits no such fact today, so `U4_NO_MPN`
    same-product admission **does not fire until SV2-A is approved**
    (explicit, explainable — the ledger record is preserved either way).
    `U5_NEAR_MISS_MPN` same-product admission is permitted (a frozen
    S2-A design intent: near-miss MATCHes are human-reviewable; the NM-2
    automatic-authority ceiling is preserved — it caps automatic tiers,
    which V2 has none).
  * `V2_ADVISORY_VARIANT_SUSPECTED` — recorded `MATCH` carrying at least
    one REVIEWABLE conflict class (`REVISION_OR_SUFFIX`, `BRAND`,
    `OTHER_MATERIAL_CONFLICT`) and no ALWAYS_HARD class. **Discovered
    from the persisted evaluation itself — no pre-existing attested-
    variant record is required** (C6). Not identity; not a 4A bucket
    member; reviewable; on confirmation it becomes a separately labeled
    comparable offer (§4.7).
  * `V2_ADVISORY_VARIANT_VERIFIED` — as suspected, plus a bound persisted
    attested-variant row from `VariantSimilarityTableV2` (SV2-C) present
    **at classification time**. If attestation arrives later, the
    candidate conservatively stays SUSPECTED (the classification field
    is immutable; no row rewriting).
* **`V2_NOT_ADMITTED`** (no review candidate created) — with a bounded
  recorded reason: `NO_LEDGER_RECORD` (never V2-executed — verified /
  conflict / unevaluable state), `LEDGER_PENDING` (V2 execution not yet
  complete — Option B lifecycle, §4.9), `RECORDED_NO_MATCH`,
  `RECORDED_UNCERTAIN`, `RECORDED_RUNTIME_FAILURE`,
  `GROUNDED_EVIDENCE_BAR_NOT_MET` (`U4_NO_MPN` same-product without a
  grounded fact), `HARD_CONFLICT_POLICY` (recorded ALWAYS_HARD class —
  defense in depth; the frozen response coherence rule makes a recorded
  `MATCH`/`UNCERTAIN` with an ALWAYS_HARD class unconstructible, §4.4).
  **The FU1 `ADVISORY_NO_FIRE` "no-record outcome" is removed**: the V2
  evaluation always persists its ledger record for every V2-executed
  candidate (all outcomes, C3); "no review candidate" is an admission
  result, never the absence of semantic execution evidence.

**Hard guards (frozen, FU2 C3/C4/C6 enforced):**

* The recorded V2 response is coherence-checked at the frozen
  `SemanticMatchResponseV2` constructor (`_validate_v2_response_coherence`,
  `research/semantic_v2.py`): a `MATCH` or `UNCERTAIN` response carrying
  any ALWAYS_HARD conflict class is **refused at construction** — "a hard
  conflict is a structured NO_MATCH and can never be overridden or hidden
  by the semantic output". The admission derivation re-checks this
  fail-closed over the persisted record (tamper defense).
* The actual complete `ALWAYS_HARD_CONFLICT_CLASSES` set (frozen, S2-A —
  `research/semantic_authority_v2.py`): `MPN_IDENTITY`,
  `PRODUCT_FAMILY`, `GENERATION`, `CAPACITY`, `INTERFACE`,
  `FORM_FACTOR`, `PRODUCT_ROLE`, `ACCESSORY_RELATION`,
  `PACKAGING_QUANTITY`, `BUNDLE` (exactly ten members). The REVIEWABLE
  set: `REVISION_OR_SUFFIX`, `BRAND`, `OTHER_MATERIAL_CONFLICT`. The
  PRICE_DIMENSION_ONLY set: `CONDITION`. **`SALES_UNIT` is NOT a
  ConflictClass member** — sales-unit protection rides the frozen
  `CandidateSalesUnitEvidenceV2` channel discipline plus the
  `BUNDLE` / `PACKAGING_QUANTITY` classes; the FU1 text's
  "`CAPACITY, INTERFACE, GENERATION, SALES_UNIT, BUNDLE, FAMILY`" list
  was wrong (it named a non-existent class and omitted six real members)
  and is corrected throughout this document (C6).
* The classification never promotes identity: the assessment's
  `EvidenceDecision` is never changed; a `V2_ADVISORY_SAME_PRODUCT`
  confirmation is a HUMAN_CONFIRMED **overlay** only (frozen
  HUMAN-REVIEW semantics).
* No V2 execution runs against an `ACCEPTED` listing (the derived state
  is `DETERMINISTIC_VERIFIED`, not an entry point).
* The grounded bar, the conflict-class rules, and the attestation rules
  are deterministic functions of persisted, verified artifacts; no
  admission decision may read live evidence or unpersisted model state.

### 4.2 SV2-C2 — Human-review candidate admission (the versioned V2 admission boundary, FU2 C2 corrected)

**Actual signature audit (FU1 F3, re-verified for FU2).**

* `is_human_review_eligible_assessment(assessment: ListingIdentityAssessment) -> bool`
  — `research/matching.py:762-806`. Inputs: a single
  `ListingIdentityAssessment` only. Accesses exactly
  `assessment.decision`, `assessment.rejection_reason`,
  `assessment.candidate_evidence_source`. Returns True only for the
  three FU3B clauses (`PARTIAL_MPN_ONLY`; `NO_EXPLICIT_MPN_EVIDENCE` +
  `TITLE_TEXT`; `NO_EXPLICIT_MPN_EVIDENCE` + `SKU_FIELD`). It **cannot**
  read V2 outcomes, attestation records, or any semantic evidence —
  that is a property of its frozen signature, not an accident.
* `is_review_candidate_binding_valid(candidate, assessment) -> bool`
  — `research/matching.py:804-866`. Checks the 6 provenance fields
  (`source_url`, `target_mpn`, `candidate_title`, `candidate_mpn_field`,
  `candidate_sku`, `evidence_source`) and **re-checks
  `is_human_review_eligible_assessment(assessment)` as its first rule**.
  Fail-closed. Consequence (C2): any candidate whose assessment is not
  in the FU3B triple — including every `NONE`-source and every
  `MPN_MISMATCH`-source candidate — fails this binding primitive, so the
  V1 pipeline (creation, confirmation, replay) cannot carry V2-admitted
  candidates at all.
* `runs/ai_assisted_review.py` entry points (actual names):
  `confirm_candidate`, `reject_candidate`, `undo_review`,
  `remove_candidate_from_working_quote`. The state machine
  (`UNREVIEWED → CONFIRMED / REJECTED → UNREVIEWED`), the conditional-
  update concurrency protection, and `_validate_assessment_mapping`
  (runs-layer snapshot existence check) are frozen.
* `AiAssistedReviewCandidate` field inventory — `runs/models.py:622-849`.
  Immutable provenance fields: `source_url`, `target_mpn`,
  `target_description`, `candidate_title`, `candidate_mpn_field`,
  `candidate_sku`, `candidate_specs`, `evidence_source`,
  `semantic_confidence`, `semantic_reason_code`,
  `semantic_matched_attributes`, `semantic_conflicting_attributes`,
  `actual_provider`, `actual_model`, `prompt_version`. Mutable state:
  `review_state ∈ {UNREVIEWED, CONFIRMED, REJECTED}` (+ `reviewed_at`
  consistency CHECK constraint). Identity: UUID primary key;
  `assessment_index` with
  `UniqueConstraint(fields=['run', 'assessment_index'],
  name='ai_assisted_review_unique_candidate_per_run_assessment')`.

**The FU1 design is withdrawn (C2 correction of record).** The FU1 text
specified that the new V2 admission be "an additive predicate that
operates **only** on the inputs already available to
`is_human_review_eligible_assessment`" while simultaneously requiring
that the `NONE`-source clause read "the FU3A bounded observation set"
and the variant clause read "`VariantSimilarityTableV2`". Those inputs
are not available to an assessment-only predicate; the design was not
executable. Extending the V1 predicate in any way would also give the
old assessment-only predicate implicit V2 authority, and — because
`is_review_candidate_binding_valid` re-checks it — would corrupt the
V1 binding/replay semantics the predicate guards. The corrected design:

**New versioned V2 admission boundary (explicit, executable).**

* **Contract identifier**: `v2-review-admission/1` (a versioned string
  constant; any future change is a new version, never an in-place
  edit). Declared in `research/` (pure, stdlib + research imports only);
  the runs layer invokes it; the web layer never calls it directly
  (layer boundaries preserved).
* **Classification function** (pure, deterministic, fail-closed):
  `derive_v2_advisory_classification(assessment, ledger_record,
  variant_attestation) -> V2AdvisoryClassification`, where
  `ledger_record: SemanticDecisionRecordV2Perf | None` is the **persisted,
  verified V2 evidence** — the decoded `SemanticDecisionRecord` row for
  `(run, assessment_index)` loaded through
  `execution/semantic_decision_persistence.py::load_semantic_decision`
  (whole-artifact digest verification + strict codec dispatch), or
  explicit `None` when no row exists; and `variant_attestation:
  VariantSimilarityEntry | None` is the bound SV2-C attestation row or
  explicit `None`. The function re-derives the S2-A state via
  `derive_identity_state_v2`, verifies it agrees with the ledger record's
  own recorded context (a mismatch = caller/tamper defect, fail closed),
  and applies exactly the §4.1 classification rules (recorded decision +
  recorded conflict classes + substate + grounded bar + attestation)
  to produce the admission provenance, the advisory class, the bounded
  reason when not admitted, and the recorded sales-unit channel state
  from the persisted V2 case.
* **Admission predicate**: `is_v2_review_admissible(...) -> bool` =
  (classification.advisory_class ∈ {`V2_ADVISORY_SAME_PRODUCT`,
  `V2_ADVISORY_VARIANT_SUSPECTED`, `V2_ADVISORY_VARIANT_VERIFIED`}).
  A candidate is created **only** when this returns True over the
  persisted, verified inputs. No in-memory-only evidence is admissible:
  if the ledger row is not persisted, there is no admission.
* **V1 predicate frozen**: `is_human_review_eligible_assessment` and
  `is_review_candidate_binding_valid` are **byte-identical**; they
  remain the sole authority for V1 (FU3B) candidates and for the
  same-product guards inside the frozen reviewed-price / projection
  helpers. The V2 boundary is a separate function with separate inputs
  and a separate binding primitive:
  `is_v2_review_candidate_binding_valid(candidate, assessment,
  ledger_record)` — verifies (a) the same 6 provenance-field binding as
  the V1 primitive (reused structurally, unchanged), (b) the assessment
  re-derives to the candidate's recorded admission provenance substate,
  (c) the ledger record's universal binding
  `(run, assessment_index, source_url)` agrees, (d) the persisted
  candidate classification **equals** the classification re-derived from
  the persisted, verified inputs (drift or tamper ⇒ fail closed), and
  (e) for `V2_ADVISORY_VARIANT_VERIFIED` the bound attestation row still
  exists and still binds. It does **not** call
  `is_human_review_eligible_assessment` (the V2-admitted assessments are
  precisely the ones it excludes) — the two binding primitives are
  disjoint by construction and dispatched on the candidate's persisted
  class (§4.3), never on a shared mutable flag.
* **Candidate creation (producer)**: a runs-owned admission service
  (extension of the `runs/ai_assisted_review.py` review-write ownership
  — CLAUDE.md: "Runs-owned services own review writes"), invoked inside
  the existing atomic publication block of
  `execution/orchestration.py` **after** `persist_semantic_decision_records_v2`
  (ordering contract: snapshot → V1 candidates → V2 ledger rows → V2
  candidates), for runs whose versioned review policy (§4.9) admits V2
  candidate creation. It persists the classification in the additive
  immutable `v2_review_admission` field (§4.3), written exactly once at
  creation, `editable=False`.
* **Confirmation (actual entry point `confirm_candidate`)**: for a
  candidate with non-null `v2_review_admission`, the confirm path gains
  one versioned re-verification step inside the existing transaction:
  the ledger row is loaded (runs owns `SemanticDecisionRecord`), its
  digest is verified, the payload is strictly decoded, and the
  pure research-layer verifier (contract `v2-review-admission/1`; takes
  the candidate structurally, the assessment, and the decoded ledger
  record — no Django, no I/O) re-derives the classification and requires
  agreement with the persisted field before the UNREVIEWED → CONFIRMED
  transition (mismatch ⇒ bounded `InvalidCandidateError`, fail closed).
  **Layering note (of record)**: the re-verification composes the
  runs-owned row load (digest + strict decode) with the pure
  research-layer verifier. The default implementation site is the
  existing web review-POST validation (PLAN §26.11.2 — the 8-step
  boundary that already runs before `confirm_candidate`, and which
  already holds the symbol-level research read-side allowlist enforced
  by `tests/web/test_web_boundaries.py`; the verifier symbol joins that
  recorded allowlist as a standard re-pin). An alternative site (the
  runs service itself) would require ONE narrow additive `runs/` →
  pure-`research/` import and its own boundary re-pin; both sites are
  design-equivalent for this contract — the fail-closed guard must
  exist at exactly ONE site, chosen by the implementation phase and
  pinned by its boundary tests. No `runs/` → `execution/` import is
  introduced either way. For a
  candidate with null `v2_review_admission` (V1), the confirm path is
  **byte-identical to today**. `reject_candidate`, `undo_review`, and
  `remove_candidate_from_working_quote` apply to V2 candidates through
  the same state machine unchanged (no new transitions).
* **Replay integration**: the persisted `PriceIntelligenceSnapshot`
  remains the assessment source of truth; the replay boundaries
  (`replay_compact_quote_projection`, `replay_public_compact_quote_projection`)
  read the run's own snapshot with zero live I/O and zero caller-supplied
  index; their confirmed-index derivation partitions candidates by the
  persisted class and dispatches on the binding primitive (§4.7). A V1
  candidate replays through the **unchanged** `is_review_candidate_binding_valid`;
  a V2 candidate through `is_v2_review_candidate_binding_valid` (which
  re-verifies the ledger row — persisted, verified evidence at replay
  time, no live I/O). Historical V1 runs (policy `V1_FIRST`, null class
  field) replay **byte-identical**.
* **Idempotency / coexistence**: the existing
  `(run, assessment_index)` unique constraint remains the single source
  of truth — at most one review candidate per index, ever. Which
  pipeline may create it is decided by the run's versioned review policy
  (§4.9), not by predicate evaluation order at creation time.

**Hard guards (frozen, FU2 C2 + C5):**

* The V1 predicate and V1 binding primitive are never extended; a V2
  outcome, attestation record, or semantic evidence is never readable
  from them.
* No review candidate is created from an unpersisted V2 outcome; no
  admission decision is made from in-memory-only evidence.
* A candidate's persisted advisory class is immutable after creation;
  any later change of the underlying persisted evidence is detected at
  the next confirm/replay as a re-derivation mismatch (fail closed —
  never silently re-admitted, never silently dropped).
* NON-admitted outcomes (`NO_MATCH`, `UNCERTAIN`, `RUNTIME_FAILURE`,
  grounded-bar failure, hard-conflict policy) create no candidate and
  can never be confirmed under any path; their ledger evidence is
  preserved and reviewable through the ledger surface (§4.9 pending /
  failed states).
* The existing HUMAN_CONFIRMED / Reviewed Price arithmetic is unchanged
  in all respects for V1 candidates (F4); V2 same-product candidates
  enter reviewed price only through the versioned boundary of §4.7.

### 4.3 SV2-C2.5 — Where the advisory classification lives (ledger / adapter coexistence, FU2 C3 corrected)

**The actual ledger architecture (re-verified for FU2).**

* **Four registered contract adapters** — `research/semantic_decision_codec.py::_REGISTERED_SEMANTIC_CONTRACT_ADAPTERS` names exactly four, in registration order: `SEMANTIC_V1_ADAPTER` (`research/semantic_decision_v1.py`), `SEMANTIC_V2_ADAPTER` (`research/semantic_decision_v2.py`), `SEMANTIC_V2_FU4_ADAPTER` (`research/semantic_decision_v2_fu4.py`), and `SEMANTIC_V2_PERF_ADAPTER` (`research/semantic_decision_v2_perf.py`).
* **Dispatch is on the FULL RECORDED five-axis contract binding**
  `(semantic_contract_version, prompt_version, input_schema_version,
  output_schema_version, authority_contract_version)`, claimed by
  **exactly one** adapter (zero claiming ⇒ refused; more than one ⇒
  registry defect, refused — never first-match, never failover).
* The live V2 path persists **one row per V2-executed candidate**:
  `build_semantic_decision_records_v2` / `persist_semantic_decision_records_v2`
  (`execution/semantic_decision_v2_execution.py`) write a
  `SemanticDecisionRecordV2Perf` record claiming the binding
  `(V2, 2.0, 1, 2, SEMANTIC_AUTHORITY_V2_S2A_FU2)` — the recorded
  output schema 2 (the per-attempt instrumentation successor). This is
  the existing **V2-PERF ledger row**. Its payload records, in full:
  the recorded V2 case (the complete persisted V2 input), the
  evaluation state (`EVALUATED` with the frozen `MATCH / NO_MATCH /
  UNCERTAIN` decision, or `RUNTIME_FAILURE` with the bounded error
  class), confidence, reason code, conflict classes, matched /
  conflicting / missing attributes, the bounded attempts, and the
  derived authority audit snapshot.
* **One record per `(run, assessment_index)`; append-only.** The row
  carries the unique `(run, assessment_index)` binding; the single
  service write path `persist_semantic_decision`
  (`execution/semantic_decision_persistence.py`) **never overwrites** —
  a second persist for the same binding fails closed
  (`SemanticDecisionAlreadyRecordedError`); the separate
  `payload_digest` column (canonical SHA-256) anchors every read, so any
  out-of-band rewrite is detected and fails closed on the next load.
* **Every V2 semantic evaluation outcome is preserved**: NO_MATCH,
  UNCERTAIN, and RUNTIME_FAILURE are all ledgered exactly like MATCH —
  the ledger is the execution / provenance record; a review candidate
  is a separate workflow artifact.

**The FU1 design is infeasible and is withdrawn (C3 correction of
record).** FU1 proposed a **new registered contract adapter** whose
payload carried an "additive top-level `v2_advisory` section" of the
existing `SemanticDecisionRecord` envelope. Against the actual ledger
that cannot work:

1. The `(run, assessment_index)` slot of every V2-executed candidate is
   **already occupied** by the V2-PERF row — a second row at the same
   binding is refused by the unique constraint and the append-only
   write path. A separate row at the same binding cannot exist.
2. Embedding the advisory section into the V2-PERF row would require
   **modifying or rewriting an existing V2-PERF ledger row** —
   forbidden by this review, by the append-only write contract, and by
   the digest anchor (a rewritten payload fails every subsequent read).
3. A new adapter claiming the **same** five-axis binding as
   `SEMANTIC_V2_PERF_ADAPTER` is a contract-registry defect (two
   claiming adapters ⇒ decode refused for BOTH the new and the
   historical rows — it would destroy replay of existing V2-PERF
   evidence). A new adapter claiming a **different** binding has no row
   to decode: the historical rows keep their recorded binding.

**The corrected storage contract (smallest viable representation).**

The new advisory classification is **not** stored in the semantic
ledger at all. It is stored **on the review candidate** — the artifact
that IS the review authority — as one additive, immutable, versioned
field. Concretely:

* **Storage**: a single additive `JSONField` column on
  `AiAssistedReviewCandidate` — `v2_review_admission` (null for every
  V1 candidate and for every historical row) — plus ONE additive
  migration (a nullable column with default null; no other table,
  constraint, or column touched; every existing row stays legal). This
  is the smallest representation that is testable at the data level:
  no new model, no new ledger row, no new codec adapter, no ledger
  schema change, no rewrite of any `SemanticDecisionRecord` payload.
  The FU1 "no new model fields" position and its
  `semantic_reason_code` free-text tag are withdrawn: a free-text tag
  is not a testable data or projection boundary (C4).
* **Shape (contract `v2-review-admission/1`)**: the persisted
  classification — contract version; admission provenance (the S2-A
  substate, e.g. `U4_NO_MPN`); advisory class (`V2_ADVISORY_SAME_PRODUCT`
  / `V2_ADVISORY_VARIANT_SUSPECTED` / `V2_ADVISORY_VARIANT_VERIFIED`);
  the ledger reference (row UUID + the recorded five-axis binding);
  the recorded decision / confidence / conflict classes; the
  grounded-bar result (for `U4_NO_MPN` same-product); the bound
  attestation row UUID (verified tier) or null; the recorded sales-unit
  channel state from the persisted V2 case (`UNAVAILABLE` or `OBSERVED`
  + bounded kind / quantity).
* **Contract binding**: the field binds the candidate to the
  persisted, verified ledger row (run + assessment index + row UUID +
  five-axis binding) and to the S2-A substate. It is an **identity-
  claim-free** record: it references evidence; it asserts no
  deterministic identity and no price fact.
* **Producer**: the runs-owned admission service (§4.2), inside the
  atomic publication block, **after** `persist_semantic_decision_records_v2`
  — so the field always references an already-persisted, digest-
  anchored row; the classification is derived from the decoded row,
  never from in-memory evaluation state.
* **Replay selection**: the confirmed-index derivation sites
  (live report, vendor-authorized replay, public replay — §4.7) select
  candidates **by the persisted class in this field** and verify it
  through `is_v2_review_candidate_binding_valid` (which re-loads the
  ledger row and re-derives the classification). V1 candidates (null
  field) are selected by the unchanged V1 primitives. The ledger row
  itself is selected by the existing universal codec dispatch — the
  advisory field changes nothing about how ledger rows decode.
* **Evidence preservation / absence semantics (binding)**:
  * The V2-PERF ledger row is the **semantic execution evidence** for
    every V2-executed candidate, whatever the outcome (MATCH /
    NO_MATCH / UNCERTAIN / RUNTIME_FAILURE) and whatever the admission
    result. It is never modified, never rewritten, never replaced by
    any advisory artifact.
  * **An absent positive review candidate must never be interpreted as
    absent semantic execution evidence.** The interpretation rule is
    fixed: no ledger row ⇒ the candidate was never V2-executed (its
    derived state is verified / conflict / unevaluable) or its
    execution is still pending under the §4.9 policy (an explicit
    "pending" state, not an absence); ledger row present, candidate
    absent ⇒ V2-executed and not admitted (the bounded reason is
    re-derivable from the persisted row at any time). Both states are
    distinct, both are displayable, neither is "no evidence".
  * No `ADVISORY_NO_FIRE` / `INSUFFICIENT_EVIDENCE` counters or flags
    are persisted anywhere (F7 anti-metric preserved): non-admission is
    a derived, explainable state, not a stored outcome.
* **Frozen surfaces unchanged**: prompt 2.0, `V2SemanticDecision`,
  `SemanticDecision` (V1), the four-adapter registry, the envelope
  `schema_version=1`, the V2-PERF payload shape, the ledger model, the
  persistence service — all byte-identical. Any future actual
  model-output semantics still require separate qualification and
  version approval under SV2-D; this amendment proposes none.

### 4.4 SV2-C4 — V2 advisory never overrides safety (the conflict precedence)

The frozen precedence `HARD_CONFLICT > HUMAN_CONFIRMED > AI authority`
is preserved verbatim. Concretely:

* Any `EvidenceDecision.ACCEPTED` listing is **out of V2's advisory
  reach** (derived state `DETERMINISTIC_VERIFIED` — not an entry point);
  V2 cannot downgrade, upgrade, or reclassify any deterministic result.
* A recorded V2 `MATCH` or `UNCERTAIN` response carrying any member of
  the actual complete `ALWAYS_HARD_CONFLICT_CLASSES` set (ten members —
  `MPN_IDENTITY`, `PRODUCT_FAMILY`, `GENERATION`, `CAPACITY`,
  `INTERFACE`, `FORM_FACTOR`, `PRODUCT_ROLE`, `ACCESSORY_RELATION`,
  `PACKAGING_QUANTITY`, `BUNDLE`; see §4.1 hard guards) is
  **unconstructible at the frozen response constructor**
  (`_validate_v2_response_coherence`, `research/semantic_v2.py`: "a hard
  conflict is a structured NO_MATCH and can never be overridden or
  hidden by the semantic output"). The admission derivation re-checks
  the rule fail-closed over the persisted record (`HARD_CONFLICT_POLICY`
  — defense in depth against a tampered ledger row).
* The material hardware / accessory / bundle / packaging protections
  (`CAPACITY`, `INTERFACE`, `FORM_FACTOR`, `PRODUCT_ROLE`,
  `ACCESSORY_RELATION`, `PACKAGING_QUANTITY`, `BUNDLE`,
  `PRODUCT_FAMILY`, `GENERATION`, `MPN_IDENTITY`) are therefore NEVER
  silently overridable by V2, by human confirmation, or by this
  amendment's classification — a hard conflict is a structured
  NO_MATCH, and NO_MATCH admits nothing (§4.1).
* The `V2_PERF_AUTHORITY_QUALIFIED = False` / `V2_AUTHORITY_QUALIFIED = False`
  state of record remains unchanged by this amendment, and the
  versioned review policy of record remains `V1_FIRST` (§4.9).
  Qualification promotion happens only under the FU4 Bundle authority
  program (currently UNAPPROVED / NOT EXECUTED).

### 4.5 SV2-C5 — Evidence-grounded matching (the audit chain)

Every V2-executed candidate's evidence is persisted and auditable;
every ADMITTED candidate's classification is bound to that evidence:

* **The persisted V2 case** (recorded in the V2-PERF ledger row
  payload, digest-anchored): the complete V2 input — target MPN /
  description (RAW), candidate identifier fields, the bounded product
  observation facts (each tagged `CandidateEvidenceSourceV2`), the raw
  title / specification text, the bounded commercial facts, the
  sales-unit channel state, the recorded S2-A context, and the context
  provenance classes.
* **The persisted V2 response** (same row): the recorded decision /
  confidence / reason code / conflict classes / matched / conflicting /
  missing attributes — the model's full structured output.
* **The persisted classification** (on the review candidate, when
  admitted — §4.3): contract version, admission provenance (S2-A
  substate), advisory class, the ledger reference (row UUID + five-axis
  binding), the recorded decision / conflict classes, the grounded-bar
  result, the attestation reference, the sales-unit channel state.
* **The ledger row identity** (UUID + `(run, assessment_index)` +
  source-URL binding) for replay / replay-boundary tracing — unchanged.

The audit chain is therefore: candidate row → classification field →
ledger row (digest-verified) → recorded case + response → persisted
snapshot assessment. Every hop is a persisted, verifiable reference; no
hop requires live re-fetching or model re-execution.

### 4.6 SV2-C6 — Suspected-variant vs verified-variant discovery (FU2 C6 corrected)

**Discovery does not require pre-existing attestation (C6).** The FU1
table keyed the ENTIRE `V2_ADVISORY_VARIANT_SIMILARITY` class on the
attested-variant guard, which made a suspected variant undiscoverable
unless an attestation record already existed — discovery then became
attestation lookup, not evidence evaluation. The corrected design has
two evidence statuses with different requirements:

| Status | Advisory class | Required persisted evidence at classification | Presentation | Authority |
| --- | --- | --- | --- | --- |
| **Suspected variant** | `V2_ADVISORY_VARIANT_SUSPECTED` | the persisted V2 ledger row records a `MATCH` carrying ≥ 1 REVIEWABLE conflict class (`REVISION_OR_SUFFIX`, `BRAND`, `OTHER_MATERIAL_CONFLICT`) and NO ALWAYS_HARD class; the S2-A state re-derives to the recorded substate. **No pre-existing attested-variant record is required.** | labeled `Suspected variant — <dimension> — pending verification`; reviewable | NOT identity; NOT a 4A bucket member; on confirmation: separate labeled comparable offer ONLY (§4.7) |
| **Verified variant** | `V2_ADVISORY_VARIANT_VERIFIED` | as suspected, PLUS a bound persisted `VariantSimilarityTableV2` row (documented manufacturer URL + retrieval instant **OR** independently auditable attestation; never edit-distance; never character-similarity; never suffix-only heuristics; a self-reported operator string is provenance, not authentication, not manufacturer authority) present **at classification time** | labeled `Verified variant — <dimension>`; reviewable; separate labeled comparable offer (§4.7) | NOT identity; NOT a 4A bucket member; the attestation row is bound in the persisted classification |

Attestation arriving AFTER classification does not rewrite the
immutable classification: the candidate conservatively stays
`SUSPECTED` (no row rewriting, C3). A new candidate classified later
picks up the attestation automatically.

**Reviewability is defined separately from identity and price
authority (C6).**

* **Reviewability** — the right to exist as an `AiAssistedReviewCandidate`
  row a human can inspect, confirm, reject, or undo. Governed solely
  by the versioned admission boundary (§4.2) over persisted, verified
  evidence.
* **Identity authority** — the deterministic 3C decision (never
  changed by V2) plus the human HUMAN_CONFIRMED **same-product**
  overlay. A variant candidate carries ZERO identity authority at every
  state: confirming it never alters the assessment, never creates
  `ACCEPTED`, and never creates a same-product HUMAN_CONFIRMED index
  (§4.7).
* **Price authority** — the frozen 4A buckets (deterministic only),
  the same-product Reviewed Price (deterministic + confirmed
  same-product overlay), and — separately — the labeled comparable-
  variant offer block, which is **display evidence only**: it is never
  aggregated (no median / min / max over variants, no bucket counts,
  no Machine Price, no Reviewed Price).

**The actual complete conflict-class sets (C6, correction of record).**
Frozen in `research/semantic_authority_v2.py` (S2-A):

* `ALWAYS_HARD_CONFLICT_CLASSES` (exactly ten members):
  `MPN_IDENTITY`, `PRODUCT_FAMILY`, `GENERATION`, `CAPACITY`,
  `INTERFACE`, `FORM_FACTOR`, `PRODUCT_ROLE`, `ACCESSORY_RELATION`,
  `PACKAGING_QUANTITY`, `BUNDLE`.
* `REVIEWABLE_CONFLICT_CLASSES` (three members): `REVISION_OR_SUFFIX`,
  `BRAND`, `OTHER_MATERIAL_CONFLICT`.
* `PRICE_DIMENSION_ONLY_CONFLICT_CLASSES` (one member): `CONDITION`.

The FU1 text's six-name list ("`CAPACITY`, `INTERFACE`, `GENERATION`,
`SALES_UNIT`, `BUNDLE`, `FAMILY`") is wrong on the record: `SALES_UNIT`
is not a `ConflictClass` member (sales-unit protection rides the
`CandidateSalesUnitEvidenceV2` channel discipline plus `BUNDLE` /
`PACKAGING_QUANTITY`), `FAMILY` is abbreviated from `PRODUCT_FAMILY`,
and six real ALWAYS_HARD members were omitted. All occurrences in this
document are corrected to the actual sets. **Material hardware,
accessory, bundle, and packaging incompatibility can never be silently
overridden**: a recorded `MATCH`/`UNCERTAIN` carrying any ALWAYS_HARD
class is unconstructible at the frozen response constructor
(§4.4), and the admission derivation re-rejects it fail-closed over the
persisted record.

**Otherwise-excluded MPN mismatches — the explicit frozen-contract
redesign (SV2-G).** Under the frozen S2-A mapping,
`REJECTED + MPN_MISMATCH` + explicit MPN source derives `U5_NEAR_MISS_MPN`
**only** in the two bounded near-miss shapes over the frozen normalized
keys — NM-1 (strict prefix; a pure suffix addition on the requested
MPN) and NM-2 (same length, exactly one substituted character) — and
derives `C1_INCOMPATIBLE_EXPLICIT_MPN` (`DETERMINISTIC_CONFLICT`, not
V2-execution-eligible, no ledger row, no review surface) for every
other shape. Cosmetic-suffix variants whose suffix difference falls
outside NM-1 / NM-2 (e.g. multi-token suffixes, reordered tokens) are
therefore **excluded from V2 evaluation entirely today** — no
suspected-variant discovery is possible for them under the frozen
contract, and this amendment does not and cannot route them in via the
admission boundary (the boundary consumes persisted ledger evidence;
there is none). The explicit redesign required, named **SV2-G** (a
separate gated phase, §7):

* an additive frozen S2-A contract change admitting a bounded, named
  additional suffix/revision shape set to V2 execution (either as an
  extended U5 shape set or a new uncertain substate — the
  representation is SV2-G's design decision; this amendment prescribes
  only that it be an explicit, reviewed change to the frozen mapping,
  never an implicit route through `is_v2_semantic_eligible` or the
  admission boundary);
* hard guards carried into SV2-G: the redesign never admits a recorded
  ALWAYS_HARD conflict (response coherence + admission rules), never
  promotes identity (no `ACCEPTED`, no same-product overlay without the
  §4.2 admission + human confirmation chain), never weakens NM-1/NM-2
  or the C1 default (out-of-shape candidates remain C1 until SV2-G is
  approved and the mapping re-pinned), and requires its own
  qualification corpus coverage before any authority change.
* Until SV2-G is approved: those candidates remain
  `C1_INCOMPATIBLE_EXPLICIT_MPN` — an explicit, documented, explainable
  exclusion (displayable as "not semantically evaluated: incompatible
  MPN shape"), never a silent loss.

**Hard guards (frozen, FU2 C6):**

* **No edit-distance authority, no identity promotion**: variant
  classification is derived only from the persisted V2 evaluation +
  persisted attestation; MPN string similarity, character overlap,
  suffix-only heuristics, and edit distance are never an admission or
  classification input. The 2A "no fuzzy matching, edit distance,
  similarity score, embedding, or model call" rule is untouched.
* **Suspected ≠ verified in authority as well as label**: a confirmed
  SUSPECTED variant produces a comparable offer labeled suspected — it
  never acquires verified-tier presentation, and neither tier ever
  acquires identity or same-product price authority.
* **No self-reported operator authority**: unchanged from FU1 (the
  attestation write-path records a self-reported operator string —
  provenance, not authentication, not manufacturer authority; 8C
  remains the future authentication path).

### 4.7 SV2-C7 — Separate price authority for variants (FU2 C4 corrected)

**The actual confirmation / replay / aggregation paths (traced).**
There are exactly three sites at which a persisted CONFIRMED review
candidate becomes price authority, and all three collapse the candidate
into a **bare `frozenset[int]` of assessment indices** before the price
arithmetic:

1. **Live report (Reviewed Price)** — `web/views.py` (research detail
   view): `_validate_confirmed_candidates(confirmed_candidates,
   assessments, logger)` collects `candidate.assessment_index` for every
   confirmed candidate whose `binding_valid` and whose
   `working_quote_disposition == "CONFIRMED"` (the disposition comes
   from `research/working_quote_policy.py::classify_ai_match_for_working_quote` —
   review state + semantic confidence + strong-SKU + conflicting
   attributes; it reads NO admission class). The bare index set is
   passed to `research/aggregation.py::aggregate_reviewed_listing_prices(
   request, assessments, confirmed_assessment_indices)`, whose guard
   `_validate_confirmed_indices` accepts an index iff the assessment
   passes the frozen assessment-only `is_human_review_eligible_assessment`
   (the FU3B triple), and whose `ReviewedPriceEntry` / exclusion
   invariants repeat the same guard; every accepted index then receives
   `ReviewedListingOrigin.HUMAN_CONFIRMED` and enters the frozen
   same-product bucket arithmetic (`(currency, condition)` keys,
   Decimal prices, low / median / high, market range at count ≥ 3,
   verification status).
2. **Vendor-authorized replay** —
   `execution/compact_quote_replay.py::replay_compact_quote_projection`:
   `derive_human_confirmed_assessment_indices(run, assessments)` iterates
   the run's CONFIRMED candidates; for each it requires the V1 binding
   primitive `is_review_candidate_binding_valid` (which re-checks the
   FU3B triple on the assessment) and
   `classify_ai_match_for_working_quote(...) is CONFIRMED`, then returns
   the bare index set; `research/compact_quote.py::project_human_confirmed_rows
   (price_result, indices, fx_snapshot)` projects the "Human Confirmed"
   quote rows (it re-guards each index on
   `is_human_review_eligible_assessment`).
3. **Public replay** —
   `execution/compact_quote_public_replay.py::replay_public_compact_quote_projection`
   uses the SAME shared `derive_human_confirmed_assessment_indices` +
   `project_human_confirmed_rows` (vendor-free branch).

**Why a confirmed comparable VARIANT can be misread as a same-product
HUMAN_CONFIRMED index (the C4 demonstration).** The bare integer
carries no authority class. Every existing guard is assessment-level
(FU3B triple) or policy-level (hard-conflict disposition) — none of
them can see WHY the candidate exists or what class its persisted V2
evidence assigns. A V2 variant candidate whose assessment IS in the
FU3B triple (worst case: a `TITLE_TEXT` / `U1_TITLE_MPN` listing, or a
`SKU_FIELD` / `U2_SKU_ONLY` listing, whose V2 evaluation recorded a
`MATCH` + a REVIEWABLE class) can pass ALL existing guards once
confirmed: V1 binding valid (the 6 provenance fields are the same
assessment's facts), FU3B-eligible assessment, and the frozen
`classify_working_quote_policy` disposition CONFIRMED whenever the
persisted `semantic_conflicting_attributes` do not match the policy's
hard-identity term list (e.g. an `OTHER_MATERIAL_CONFLICT`-grounded
variant, or an unfilled field). Its price then enters (a) the same-
product Reviewed Price bucket as `HUMAN_CONFIRMED`, and (b) the
"Human Confirmed" compact-quote row in BOTH replays — as if the variant
were the same product. The frozen policy's term matching (it does
cover the common `REVISION_OR_SUFFIX` / `BRAND` / `CAPACITY` /
`INTERFACE` dimension names) is a **secondary defense-in-depth layer
only** — it is term-based, incomplete over the REVIEWABLE vocabulary,
and reads no admission class; it is NOT the boundary. Producer
discipline (SV2-B): the V2 candidate producer records the
persisted V2 response's conflicting dimensions into the existing
`semantic_conflicting_attributes` field so that this frozen layer
continues to apply to V2 candidates (it cannot, by itself, carry the
variant boundary). A presentation label cannot prevent the primary
defect: the row's authority type (`HUMAN_CONFIRMED` origin /
human-confirmed quote row) IS the data.

**The explicit, testable boundary (data + projection, not
presentation).**

* **Data boundary**: the persisted immutable `v2_review_admission`
  classification on the candidate (§4.3) is the SINGLE authority-class
  record. A V1 candidate (field null) is same-product by construction
  (frozen FU3B semantics — unchanged). A V2 candidate is same-product
  iff its persisted class is `V2_ADVISORY_SAME_PRODUCT`; it is variant
  iff its persisted class is `V2_ADVISORY_VARIANT_SUSPECTED` /
  `V2_ADVISORY_VARIANT_VERIFIED`. The class is re-verified from the
  persisted ledger row at confirm and at every replay (drift ⇒ fail
  closed) — it cannot be minted, edited, or presented-away.
* **Projection boundary**: every confirmed-index derivation site
  PARTITIONS the run's confirmed candidates by persisted class BEFORE
  collecting indices. The same-product partition feeds the reviewed-
  price and human-confirmed-quote paths; the variant partition feeds
  ONLY the separate labeled comparable-offer projection. An index is in
  at most one partition (one candidate row, one class, one state).
  Concretely: a versioned derivation
  `derive_v2_same_product_confirmed_indices(run, assessments)` replaces
  the shared derivation for `V2_PRIMARY` runs (dispatched by the
  run's persisted policy, §4.9); it admits an index iff the candidate's
  persisted class is `V2_ADVISORY_SAME_PRODUCT` AND
  `is_v2_review_candidate_binding_valid` (ledger re-verified) AND the
  hard-conflict policy disposition is CONFIRMED. For `V1_FIRST` runs the
  frozen `derive_human_confirmed_assessment_indices` is used
  byte-identically (its V1 candidates have null class fields).
* **Same-product Reviewed Price arithmetic stays unchanged.** For a
  same-product index set whose assessments all pass the frozen FU3B
  triple (all `U1` / `U2` / `U3` provenance — the case every
  `V1_FIRST` run and every in-FU3B-triple `V2_PRIMARY` confirmation
  falls in), the frozen `aggregate_reviewed_listing_prices` and
  `project_human_confirmed_rows` are used unchanged. For same-product
  confirmations at assessments OUTSIDE the FU3B triple (`U4_NO_MPN`,
  `U5_NEAR_MISS_MPN` — the new access this amendment exists to give),
  a **versioned reviewed-price boundary** (contract `reviewed-price/2`)
  and a **versioned human-confirmed projection** (contract
  `compact-quote/2`) run the IDENTICAL frozen bucket arithmetic
  (same `(currency, condition)` keys, same Decimal price handling, same
  low / median / high, same market-range-at-≥3 rule, same exclusions,
  same verification status, same "Human Confirmed" row shape) over the
  class-proven index set. **Equivalence property (test-enforced)**: for
  any index set on which the frozen v1 guard passes, the `reviewed-price/2`
  / `compact-quote/2` outputs are byte-identical to the frozen v1
  outputs. The v1 functions themselves are never modified; the v1
  guard's rejection of non-FU3B-eligible indices remains a fail-closed
  pin (a v2-authorized index must never be routed through the v1
  function).
* **The comparable-variant offer (separate, labeled, never aggregated)**:
  a confirmed variant candidate produces a bounded variant-offer row —
  **not** in the reviewed bucket, **not** in any 4A bucket, **not** in
  Machine Price, **not** a human-confirmed quote row. It is projected by
  its own versioned projection (SV2-F) into a separate bounded block on
  the research detail page and in both replays, carrying:
  * the variant label and tier (`Verified variant — <dimension>` /
    `Suspected variant — <dimension> — pending verification`);
  * the published price, currency, and availability exactly as persisted
    in the snapshot (never recomputed, never unit-normalized);
  * the explicit sales-unit state from the persisted V2 case: channel
    `UNAVAILABLE` ⇒ `Sales unit unknown — not normalized` (an unknown
    unit is never treated as a single unit and no per-unit price is
    derived — C7); channel `OBSERVED` ⇒ the recorded bounded kind /
    quantity;
  * the bounded source URL, retrieval instant, provenance, and the
    recorded conflict-class check result;
  * the attestation reference for the verified tier.
* **Full user path**: V2 evaluation (persisted ledger row) →
  classification (persisted on the candidate at creation) → human
  action (`confirm_candidate` / `reject_candidate` / `undo_review` /
  `remove_candidate_from_working_quote` — the existing state machine)
  → same-product partition (reviewed price / human-confirmed quote row)
  OR variant partition (labeled comparable offer) — never both.
* **NON-admitted outcome shortcut prohibition**: `NO_MATCH`,
  `UNCERTAIN`, `RUNTIME_FAILURE`, and grounded-bar failures create no
  candidate and can never be confirmed under any path; the confirm
  path's ledger re-verification is the single guard against a forged
  or drifted candidate asserting a class its evidence does not support.
* **Hard safety conflicts and sales-unit controls**: the actual
  complete `ALWAYS_HARD_CONFLICT_CLASSES` set (§4.6) and the frozen
  `CandidateSalesUnitEvidenceV2` channel discipline are preserved;
  material hardware / accessory / bundle / packaging incompatibility is
  never silently overridden (§4.4).

### 4.8 SV2-C8 — V1 retirement / historical compatibility (the boundary)

V1 retirement is **out of scope** for this amendment. The amendment:

* Preserves the V1 deterministic authority (2A / 3C / 4A / 4B / HUMAN-REVIEW
  / replay / FU3B live predicate) byte-identically.
* Preserves the V1 codec, the V1 snapshot decoder, the V1 replay
  boundaries, and every frozen test.
* Preserves the V1 historical price-result integrity (`schema_version`
  versioning; the FU2 public-replay correction).
* Defines the V1 → V2 **primary-engine migration** as the versioned
  run-level review policy of §4.9 (smallest viable design) and keeps V1
  RETIREMENT (stopping the V1 engine from running at all, removing V1
  surfaces) as a separate later phase with its own architectural gate
  (analogous to the existing FU4 / C3 / E1 / E2 / P1 / Q1 / W1 gating).

### 4.9 SV2-C9 — V2-primary migration behavior (the versioned run-level review policy, FU2 C5 corrected)

**Problem of record (C5).** The current selection is V1-first: review
candidates are created exclusively by the V1 pipeline
(`execution/semantic_integration.py::evaluate_semantic_matches` over the
frozen FU3B `_is_semantic_eligible` + `_has_usable_evidence`, published
by `execution/orchestration.py::_create_review_candidates`), and V2 is
execution-evidence only (every V2-executed candidate gets a ledger row;
**no V2 review candidate is created** — the orchestration firewall:
"no V2 human-review candidate is created; persist V2 result only").
That selection is incompatible with the product requirement that V2
**replace** V1 as the primary review engine. The FU1 text's
"evaluation order" coexistence rule (V1 predicate first, V2 clause
after) would permanently keep V1 the primary engine. The corrected
design is the **smallest versioned run-level review policy**:

* **Policy vocabulary (frozen)**: `V1_FIRST` and `V2_PRIMARY`.
* **Recording (smallest viable)**: one additive immutable column on
  `ResearchRun` — `review_engine_policy` (bounded choices,
  **default `V1_FIRST`**), set at run creation from the frozen code
  constant `CURRENT_REVIEW_POLICY_VERSION` (value today: `V1_FIRST`).
  One additive migration; historical rows carry the default ⇒ their
  behavior is unchanged without any data rewrite. The constant is
  advanced **only** under the qualification + approval gate below —
  never by this amendment, never by a code change alone.
* **V1_FIRST (every historical run, and every new run until approval)**:
  byte-identical to today — V1 pipeline creates the review candidates;
  V2 executes and persists ledger rows (evidence only, zero V2
  candidates); the frozen v1 reviewed-price / replay boundaries apply;
  the `v2_review_admission` field is null on every candidate of such a
  run; the derivation sites never reach the v2 partition code (a v1
  candidate has no class to partition) — historical replay stays
  byte-identical (proof scenario 6, §4.12).
* **V2_PRIMARY (new runs only, after qualification + explicit approval)**:
  V2 is the primary review engine. The V2 evaluation (unchanged
  execution + ledger) is the source of the review candidates; the
  versioned admission boundary (§4.2) is the SOLE candidate producer;
  V1 candidate creation is suppressed for the run; the V1 semantic
  evaluation is suppressed (the V2 engine replaces it — no dual engine
  minting authority); same-product authority flows through the
  versioned `reviewed-price/2` / `compact-quote/2` boundaries (§4.7);
  variants flow through the separate labeled offer projection (§4.7);
  the frozen v1 boundaries remain available and unchanged for v1-
  shaped index sets (equivalence proven, §4.7).
* **Coexistence invariant (no duplicate or contradictory active review
  authority)**: (a) one review candidate per `(run, assessment_index)`
  (the existing unique constraint — unchanged); (b) one policy per run
  (the persisted column) decides which pipeline may produce candidates;
  (c) the persisted advisory class partitions every confirmed candidate
  into exactly one of same-product / variant (§4.7); (d) a V2 ledger
  row on a `V1_FIRST` run carries zero review authority (no candidate
  references it as authority — it is evidence); a V1 candidate on a
  `V2_PRIMARY` run cannot exist (suppressed producer). V1 and V2
  results therefore never assert two authorities for one assessment, in
  live reports or in either replay.
* **Pending / failed V2 — no unsafe fallback, no unexplained loss**:
  under `V2_PRIMARY`, a V2-execution-eligible candidate whose ledger row
  is not yet persisted (Option B nonblocking lifecycle, when approved)
  or whose recorded outcome is `RUNTIME_FAILURE` / `UNCERTAIN` /
  `NO_MATCH` / grounded-bar-not-met receives **no review candidate** —
  and the review surface displays the bounded, explainable state
  (`Semantic evaluation pending` / `Semantic evaluation failed — not
  reviewable` / `V2 matched — same-product confirmation requires
  grounded specification evidence, not published` etc., with the ledger
  reference where a row exists). There is **no fallback to V1
  candidate creation** (the superseded engine's authority must not
  reappear silently), and there is no silent loss: every such state is
  derived from persisted evidence and is displayable. When the Option B
  lifecycle completes a pending evaluation, the admission boundary
  re-runs idempotently over the persisted row (the unique constraint
  guards against a duplicate candidate).
* **Option B alignment (FU1 F8 preserved)**: V2 work remains
  supplementary with respect to main-flow publication (it runs on
  already-published snapshot data; ledger records are append-only);
  if Option B is approved in its own gate, its durable states /
  recovery / retry / idempotency apply to the V2 ledger records and to
  the pending-state display rule above without further contract
  change; if Option B is rejected, the synchronous path persists the
  ledger rows at publication and no `LEDGER_PENDING` state ever occurs
  (admission runs in the same atomic block).
* **NOT activated by this amendment**: `CURRENT_REVIEW_POLICY_VERSION`
  remains `V1_FIRST`; the advancement gate is SV2-D qualification
  closure (FU4 Bundle authority program: C2 corpus state DRAFT ACCEPTED
  / FINAL HOLD; v1.0.0 seal FINAL-HOLD) PLUS an explicit independent
  approval of the V2-primary cutover — a separate record this
  amendment does not create. The frozen `V2_AUTHORITY_QUALIFIED` /
  `V2_PERF_AUTHORITY_QUALIFIED` flags remain `False` regardless.

### 4.10 SV2-C10 — Qualification V3 and pricing-authority gating (policy-gated; FU2 C5 aligned)

The amendment does **not** open the qualification gate. Specifically:

* No V2 advisory outcome is promoted to `EvidenceDecision.ACCEPTED`.
* No V2 advisory outcome alters Machine Price.
* No V2 advisory outcome is automatically included in Reviewed Price.
* No V2 advisory outcome is automatically included in Working Quote.
* No V2 advisory candidate is admitted into a 4A price bucket.
* No V2 advisory result affects the `V2_AUTHORITY_QUALIFIED` /
  `V2_PERF_AUTHORITY_QUALIFIED` flags — both remain `False` under this
  amendment.
* **The versioned review policy (§4.9) remains at `V1_FIRST`** under
  this amendment; V2-primary behavior is specified, gated, and
  test-specified (proof scenarios, §4.12) but NOT activated.
* The FU4 Bundle authority program (currently UNAPPROVED / NOT
  EXECUTED; C2 state of record DRAFT ACCEPTED / FINAL HOLD; v1.0.0
  seal FINAL-HOLD) is **not** advanced by this amendment.

---

## 4.11 Evidence acquisition and the actual MVP (FU2 C7 corrected)

**"A contract shape alone is not a delivered data source."** The FU1
text named the `CandidateProductEvidenceV2` contract shape (nine product
dimensions, each a bounded fact or explicit None) as if the shape were
the source. It is not: the live main-flow builder
(`build_candidate_product_evidence_v2`) populates **only** `brand` from
`PUBLISHED_STRUCTURED_FIELD` (when the page publishes a brand),
`raw_title_text` (the published title, RAW), and
`raw_specification_text = None`; the commercial builder
(`build_candidate_commercial_evidence_v2`) populates condition / price /
currency / availability / seller / offer URL and the sales-unit channel
**always** `SALES_UNIT_EVIDENCE_UNAVAILABLE`. Everything else is explicit
absent. The actual MVP is therefore specified against what the main flow
really publishes and persists:

* **What the page publishes today (safe to extract — named fields of
  `ListingObservation`, `research/listings.py`)**: `product_title`,
  `manufacturer_part_number_text`, `sku_text`, `brand_text`,
  `price_text`, `currency_text`, `availability_text`, `condition_text`,
  `seller_text`, `offer_url_text`, plus the opaque `raw_reference` (which
  preserves the GTIN, category, description, and price-valid-until
  material — **AD-040: no business rule may parse it**; it is a human /
  test reference, not a structured source). The only product-dimension
  fact the live builder derives from these today is `brand`.
* **How it is already persisted (two durable, digest-anchored copies)**:
  (a) in the `PriceIntelligenceSnapshot` payload — the assessments carry
  the normalized listings / observations, decoded by
  `decode_price_aggregation_result`, and re-proved by the replay binding
  checks; (b) in the V2-PERF ledger row — the recorded V2 case contains
  the exact persisted V2 input (brand fact, raw title, commercial facts,
  sales-unit channel state, S2-A context, provenance classes).
* **How the V2 input is reconstructed without live re-fetching or opaque-
  reference authority**: `load_semantic_decision` (digest verification +
  strict codec dispatch) returns the recorded case — the exact input the
  model saw; `replay_semantic_decision_record` additionally re-derives
  the request identity and the snapshot assessment binding against the
  persisted run evidence, with zero live I/O. No reconstruction path
  reads `raw_reference`, re-fetches the page, or re-runs the model.
* **The actual MVP for grounded NO_MPN evidence (scenario 2; phase
  SV2-A)** — an additive, explicitly reviewed 3A extractor contract
  change, the SMALLEST that can deliver a grounded fact:
  1. a new named RAW field on `ListingObservation` carrying the
     page-published description / specification text (extracted under an
     explicit frozen rule over the fetched document — extraction, NOT
     parsing of the opaque `raw_reference` by business logic), mapped to
     `CandidateProductEvidenceV2.raw_specification_text` (RAW
     observation text; a token in it is not a structured fact);
  2. deterministic bounded extraction of product-dimension facts
     (`capacity`, `interface`, `generation`, …) from published structured
     positions (e.g. JSON-LD product properties) under a reviewed
     extraction rule — category-schema-driven where the frozen 6B
     Enterprise SSD schema applies — each recorded as a
     `PUBLISHED_STRUCTURED_FIELD` fact with its bounded dimension;
  3. persistence of both through the existing channels (named observation
     fields in the snapshot payload; recorded case in the ledger row) —
     NO new model, NO new ledger row, NO new codec adapter;
  4. the reconstruction proof: a replay test that reconstructs the V2
     input from persisted artifacts only (no network, no `raw_reference`
     parse) and digests it equal to the recorded case.
  Until SV2-A is approved and live, the grounded bar (§4.1) is not met
  for `U4_NO_MPN` same-product admission — V2 execution still happens,
  the ledger evidence is still preserved, and the review surface shows
  the explicit "grounded evidence not published" state (§4.9).
* **Sales units (C7 discipline)**: the main-flow channel is always
  `UNAVAILABLE`; unknown sales units are treated as **unknown** — a
  variant offer renders the published price with
  `Sales unit unknown — not normalized` and makes NO unit-normalized /
  per-unit price; no unit-normalized price is ever fabricated; a
  unit-comparability statement requires both sides `OBSERVED` with
  bounded kinds. Same-product Reviewed Price arithmetic is unchanged
  (it never consumed sales-unit normalization anyway — C4).

## 4.12 Mandatory end-to-end proof specifications (FU2 required)

The FU2 review requires concrete positive AND negative acceptance tests
for eight end-to-end scenarios. Any implementation phase descending from
this amendment must deliver, for each scenario: the actual source
function(s), the new versioned contract(s), the expected persisted
artifact(s), and the enforcing test node(s). These tests run in the
qualification-approved world (a `V2_PRIMARY` run created with the policy
field set by the advanced constant in the test world, or pure-boundary
invocations with explicit policy arguments); they do NOT activate the
policy in production (`CURRENT_REVIEW_POLICY_VERSION` stays `V1_FIRST`,
§4.9).

**P1 — Title-only MPN → V2 review → confirmed same-product comparison.**

* Source functions: `derive_identity_state_v2` (⇒ `U1_TITLE_MPN`);
  `is_v2_semantic_eligible` (True); `evaluate_semantic_matches_v2` /
  `build_semantic_decision_records_v2` / `persist_semantic_decision_records_v2`;
  `derive_v2_advisory_classification` (contract `v2-review-admission/1`);
  the runs-owned candidate producer (§4.2); `confirm_candidate`
  (ledger re-verification extension); `aggregate_reviewed_listing_prices`
  (v1 — the `U1` assessment passes the frozen FU3B guard, so the frozen
  function is used as-is); `derive_human_confirmed_assessment_indices` /
  `derive_v2_same_product_confirmed_indices` + `project_human_confirmed_rows`.
* Versioned contracts: `v2-review-admission/1`; candidate field shape v1;
  run policy `V2_PRIMARY`.
* Persisted artifacts: the V2-PERF ledger row (recorded `MATCH`, no
  REVIEWABLE/ALWAYS_HARD class, recorded case); the candidate row
  (class `V2_ADVISORY_SAME_PRODUCT`, provenance `U1_TITLE_MPN`, ledger
  reference) UNREVIEWED → CONFIRMED.
* Enforcing tests: POSITIVE — confirm ⇒ the listing enters the same-
  product Reviewed Price bucket (frozen arithmetic: bucket keys, median,
  HUMAN_CONFIRMED origin) and both replays show the "Human Confirmed"
  row at that index; the assessment's `EvidenceDecision` remains
  `REJECTED` (overlay only). NEGATIVE — (a) recorded `NO_MATCH` /
  `UNCERTAIN` / `RUNTIME_FAILURE` at the same shape ⇒ no candidate, no
  reviewed change, no quote row (ledger row preserved — proof scenario P5, §4.12); (b) recorded
  `MATCH` + `REVISION_OR_SUFFIX` ⇒ class `V2_ADVISORY_VARIANT_SUSPECTED`,
  and confirming it produces ONLY the labeled variant offer — the
  reviewed bucket and both replays' human-confirmed rows are byte-
  identical with/without it (proof scenario P8, §4.12).

**P2 — Missing MPN with grounded specifications → V2 review → confirmed
comparison.**

* Source functions: `derive_identity_state_v2` (⇒ `U4_NO_MPN`, primary
  `NO_RELATION`, from `NONE` + usable title — C1: no new substate);
  `is_v2_semantic_eligible` (True — U4 is the explicit entry point);
  the SV2-A extractor (description field + bounded dimension fact, live
  in the test world); the same V2 execution / persistence chain;
  `derive_v2_advisory_classification` (grounded bar met ⇒
  `V2_ADVISORY_SAME_PRODUCT`); `confirm_candidate`; the versioned
  `reviewed-price/2` boundary (the `U4` assessment is OUTSIDE the FU3B
  triple — the frozen v1 function must never receive this index); the
  `compact-quote/2` projection.
* Versioned contracts: `v2-review-admission/1`; `reviewed-price/2`;
  `compact-quote/2`; the SV2-A extraction contract; policy `V2_PRIMARY`.
* Persisted artifacts: the ledger row (recorded case carrying ≥ 1
  `PUBLISHED_STRUCTURED_FIELD` product-dimension fact beyond brand, or a
  `REVIEWED_PRODUCT_CONTEXT`; recorded `MATCH`); the candidate row
  (class `V2_ADVISORY_SAME_PRODUCT`, provenance `U4_NO_MPN`).
* Enforcing tests: POSITIVE — confirm ⇒ the `reviewed-price/2` boundary
  includes the listing as HUMAN_CONFIRMED (identical frozen arithmetic —
  equivalence node: the same listing shape at an in-FU3B-triple index
  yields byte-identical v1 vs v2 outputs); both replays show the row
  via `compact-quote/2`. NEGATIVE — (a) recorded `MATCH` with NO grounded
  fact (description-only / title-only evidence; SV2-A field absent) ⇒
  `V2_NOT_ADMITTED` reason `GROUNDED_EVIDENCE_BAR_NOT_MET`, no candidate,
  ledger preserved, explicit display state (§4.9); (b) pin: routing the
  `U4` index through the frozen v1 `aggregate_reviewed_listing_prices`
  raises (its guard is unchanged) — the v2 boundary is the only path;
  (c) `NONE` without a usable title ⇒ `E2_NO_CANDIDATE_EVIDENCE` ⇒ no V2
  execution at all ⇒ no ledger row ⇒ state "never V2-executed" (distinct
  from (a)).

**P3 — Cosmetic suffix variant → suspected / verified distinction →
separately labeled comparable offer.**

* Source functions: `derive_identity_state_v2` (suffix addition = NM-1
  strict prefix over the frozen normalized keys ⇒ `U5_NEAR_MISS_MPN` —
  in-shape today; out-of-shape suffixes ⇒ `C1_INCOMPATIBLE_EXPLICIT_MPN`
  ⇒ not V2-executed unless SV2-G is approved — §4.6); V2 execution /
  persistence; `derive_v2_advisory_classification` (recorded `MATCH` +
  `REVISION_OR_SUFFIX`, no ALWAYS_HARD ⇒ `V2_ADVISORY_VARIANT_SUSPECTED`
  **without any pre-existing attestation record** — C6; attestation row
  present at classification ⇒ `V2_ADVISORY_VARIANT_VERIFIED`);
  `confirm_candidate`; the variant-offer projection (SV2-F).
* Versioned contracts: `v2-review-admission/1`; the SV2-C attestation
  guard; the variant-offer projection contract; policy `V2_PRIMARY`.
* Persisted artifacts: the ledger row (recorded `MATCH` +
  `REVISION_OR_SUFFIX`); the candidate row (SUSPECTED or VERIFIED class,
  provenance `U5_NEAR_MISS_MPN`, attestation reference where verified).
* Enforcing tests: POSITIVE — (a) a candidate is created with NO
  attestation row (discovery requires no pre-existing record) and is
  labeled `Suspected variant — <dimension> — pending verification`;
  (b) with a bound attestation row present at creation ⇒ labeled
  `Verified variant — <dimension>`; (c) confirm ⇒ the separately labeled
  comparable offer renders (price / currency as published, explicit
  sales-unit state, provenance, conflict check) in the review UI and in
  both replays' variant blocks. NEGATIVE — (a) attestation arriving
  later does not rewrite the immutable classification (stays SUSPECTED);
  (b) the confirmed variant is NEVER identity: the assessment remains
  `REJECTED`, no `ACCEPTED` anywhere, no same-product index (proof scenario P8, §4.12);
  (c) out-of-shape suffix (C1) ⇒ no V2 execution, no candidate, explicit
  "incompatible MPN shape" state — no silent loss and no edit-distance
  routing (the frozen comparator is untouched).

**P4 — Genuine MPN, capacity, interface, accessory, bundle, or unit
conflict → cannot contaminate same-product pricing.**

* Source functions: `_validate_v2_response_coherence` (frozen:
  `MATCH`/`UNCERTAIN` + any ALWAYS_HARD class ⇒ unconstructible — "a
  hard conflict is a structured NO_MATCH"); `derive_v2_advisory_classification`
  (recorded `NO_MATCH` + hard class ⇒ `V2_NOT_ADMITTED`; tampered
  `MATCH` + hard class persisted out-of-band ⇒ re-derivation re-rejects
  with `HARD_CONFLICT_POLICY`); the frozen 3C / 4A deterministic path for
  deterministically-detected conflicts (unchanged);
  `CandidateSalesUnitEvidenceV2` channel discipline for unit
  incompatibility (expressed via `BUNDLE` / `PACKAGING_QUANTITY` classes
  + the sales-unit channel — there is no `SALES_UNIT` ConflictClass).
* Versioned contracts: `v2-review-admission/1` rejection rules; the
  frozen S2-A taxonomy (actual complete sets, §4.6).
* Persisted artifacts: the ledger row (recorded `NO_MATCH` with the
  hard class, or `C1` ⇒ no row); NO candidate row.
* Enforcing tests: POSITIVE (safety, per-class sweep over ALL TEN
  actual `ALWAYS_HARD_CONFLICT_CLASSES` members) — each ⇒ no candidate,
  reviewed bucket byte-identical with/without, no quote row, no variant
  offer. NEGATIVE (leak) — (a) forged candidate row (class
  `V2_ADVISORY_SAME_PRODUCT`) over a `NO_MATCH`-hard-class ledger record
  ⇒ `confirm_candidate` fails closed (re-derivation mismatch) and both
  replays exclude the index; (b) sales-unit mismatch: variant offer
  shows the published price with the explicit unit state and NO unit-
  normalized number; (c) deterministic hard conflicts (bundle / capacity
  detected by 3C) remain out of V2 reach — the V2 ledger (if any) cannot
  reclassify them.

**P5 — V2 UNCERTAIN / NO_MATCH / runtime failure → preserved semantic
evidence, no unauthorized positive confirmation.**

* Source functions: `build_semantic_decision_records_v2` (`EVALUATED` +
  decision `UNCERTAIN`/`NO_MATCH`, or `RUNTIME_FAILURE` + bounded error
  class); `persist_semantic_decision` (append-only, digest anchor);
  `load_semantic_decision` / `replay_semantic_decision_record`
  (verification + zero-live replay); `derive_v2_advisory_classification`
  (⇒ `V2_NOT_ADMITTED` with the bounded reason);
  `confirm_candidate` (no candidate exists; a forged one fails closed).
* Versioned contracts: none new for the ledger (the V2-PERF record shape
  is frozen); `v2-review-admission/1` for the non-admission reasons.
* Persisted artifacts: the ledger row in EVERY case (all outcomes
  preserved, C3); NO candidate row.
* Enforcing tests: POSITIVE — each of `UNCERTAIN`, `NO_MATCH`,
  `RUNTIME_FAILURE` ⇒ the row decodes and replays with the outcome
  preserved (decision / error class / attempts / recorded case intact);
  the review surface shows the bounded "not admitted — <reason>" state
  with the ledger reference; candidate absence is displayed as
  "V2-executed, not admitted", NEVER as "no semantic evidence" (C3
  interpretation rule). NEGATIVE — forged candidate (class
  `V2_ADVISORY_SAME_PRODUCT`) over such a record ⇒ confirm fails closed;
  replay derives no index; reviewed bucket unchanged; the V1 confirm
  path over a genuine V1 candidate is byte-identical (no cross-impact).

**P6 — V1 historical replay → byte-identical.**

* Source functions: `replay_compact_quote_projection`,
  `replay_public_compact_quote_projection`,
  `derive_human_confirmed_assessment_indices`,
  `project_human_confirmed_rows`, `aggregate_reviewed_listing_prices`,
  `_validate_confirmed_candidates` (live report),
  `decode_price_aggregation_result`, the four-adapter codec dispatch
  (V1 / V2 / V2-FU4 / V2-PERF rows all decode under their ORIGINAL
  adapters), `is_review_candidate_binding_valid` (unchanged V1
  primitive).
* Versioned contracts: none apply — the run's persisted policy is
  `V1_FIRST` (the default on historical rows), every candidate's
  `v2_review_admission` field is null, and the v2 partition / boundary
  code is unreachable for null-class candidates.
* Persisted artifacts: the unchanged historical rows (snapshot, ledger,
  candidates).
* Enforcing tests: POSITIVE — a V1_FIRST run fixture (V1 candidates +
  V2-PERF evidence rows): the full vendor replay, the full public
  replay, and the live reported Reviewed Price output are byte-identical
  (digest-pinned) before/after all new code is present; the V2-PERF rows
  decode under `SEMANTIC_V2_PERF_ADAPTER` exactly as before (no new
  adapter claims their binding). NEGATIVE — mutation pin: making ANY v1
  derivation site consult the new boundary / class field changes the
  output ⇒ the byte-identity pin fails (enforces unreachability);
  rewriting any V2-PERF row payload ⇒ digest failure on load (append-
  only enforcement, C3).

**P7 — V1/V2 coexisting output → one valid review authority per
assessment.**

* Source functions: the unique constraint
  `ai_assisted_review_unique_candidate_per_run_assessment`; the run
  policy dispatch (§4.9: `V1_FIRST` ⇒ V1 producer only; `V2_PRIMARY` ⇒
  V2 producer only); the class partition (§4.7: same-product XOR
  variant per candidate); `derive_human_confirmed_assessment_indices`
  (v1) / `derive_v2_same_product_confirmed_indices` (v2) + the variant
  projection.
* Versioned contracts: the policy vocabulary; the partition rule;
  `v2-review-admission/1`.
* Persisted artifacts: exactly one candidate row per admitted index (or
  none); the V2-PERF ledger row at every V2-executed index.
* Enforcing tests: POSITIVE — a `V2_PRIMARY` run with admitted candidates
  at several indices: exactly one candidate row per index; each derived
  index appears in EXACTLY ONE partition (same-product set XOR variant
  set) in the live report, the vendor replay, and the public replay —
  the three surfaces agree. NEGATIVE — (a) forced double creation (V1 +
  V2 producer racing at the same index) ⇒ `IntegrityError` on the unique
  constraint, surfaced as a bounded publication failure — never two
  rows; (b) a `V1_FIRST` run's V2-PERF ledger row (evidence only) cannot
  mint authority: no candidate references it, no derivation consumes it
  as authority (pin: the v1 derivation over such a run returns only the
  V1 candidates' indices); (c) tampered class field (DB-level edit of
  `v2_review_admission`) ⇒ confirm and both replays re-derive from the
  ledger and fail closed (the persisted field is a cache of a
  verifiable derivation, never an independent authority).

**P8 — Variant confirmation → no Reviewed Price index leakage in either
public or vendor-authorized replay.**

* Source functions: `derive_human_confirmed_assessment_indices` (frozen
  v1 — unchanged, and unreachable for v2-class candidates by dispatch);
  `derive_v2_same_product_confirmed_indices` (v2 — admits only
  `V2_ADVISORY_SAME_PRODUCT`); the variant partition + the variant-offer
  projection; `replay_public_compact_quote_projection` +
  `replay_compact_quote_projection`; `aggregate_reviewed_listing_prices`
  / the `reviewed-price/2` boundary; `project_human_confirmed_rows` /
  the `compact-quote/2` projection.
* Versioned contracts: `v2-review-admission/1` (class); the partition
  rule (§4.7); `compact-quote/2` + the variant-offer projection.
* Persisted artifacts: the CONFIRMED variant candidate (worst case
  fixture: at a FU3B-ELIGIBLE `TITLE_TEXT` index, so every legacy guard
  would pass); the ledger row (recorded `MATCH` + REVIEWABLE class);
  the variant-offer display state.
* Enforcing tests: POSITIVE — both replays: NO "Human Confirmed" row at
  that index; the variant offer block IS present (labeled, published
  price, explicit unit state, provenance); the live reported Reviewed
  Price bucket is byte-identical with/without the confirmation; the
  same-product partition excludes the index in ALL THREE surfaces
  (live report, vendor replay, public replay — one derivation, one
  partition). NEGATIVE — (a) the partition is enforced at the single
  derivation site: a test that the variant class can never enter the
  same-product index set (property: same-product set ∩ variant set = ∅
  and both ∪ = the confirmed-candidate set); (b) cross-run forgery: a
  variant candidate row copied to another run ⇒ the run-scoped query +
  binding checks fail closed (no index minted); (c) undo / reject of
  the variant ⇒ the offer disappears from both replays (state machine
  unchanged), still no same-product trace.

**Validation discipline:**

* Use actual committed source as the authority for signatures, model
  fields, enums, and frozen tests.
* Never delete, rename, skip, xfail, deselect, or weaken existing
  tests.
* Do not alter acceptance criteria to fit current implementation.
* Every proof scenario above is a CONTRACT specification: the named
  new functions / fields / boundaries do not exist yet and are delivered
  only by the gated phases of §7.

---

## 5. Measurable success criteria (FU1 F7 corrected; FU2 C3/C4/C6-aligned)

The FU1 review identified two misleading metrics in the original
amendment: the unsupported automatic +20% bucket-count target and the
perverse `INSUFFICIENT_EVIDENCE` ≥ 5% target. The amendment replaces
both with a measurable, falsifiable, hold-out-validated metric set.
**No baseline number is fabricated**; every metric is grounded in an
existing benchmark or frozen artifact, and every metric is measured
**post-approval** against independently labeled cases. (FU2: the metric
terminology now follows the persisted advisory class in the
`v2_review_admission` field and the separate variant-offer block, not
the withdrawn FU1 `v2_advisory` ledger section / `V2_VARIANT_CONFIRMED_OFFER`
row names.)

### 5.1 Recall against independently labeled legitimately reviewable cases

| Metric | Source of truth | Measurement | Anti-metric (forbidden) |
| --- | --- | --- | --- |
| **Recall of legitimately reviewable comparison candidates** (independently labeled on a held-out test set; the existing frozen test suite already provides negative cases) | reviewed-price output (frozen `aggregate_reviewed_listing_prices` for v1 shapes; `reviewed-price/2` for v2 shapes) + the held-out label set | % of labeled reviewable candidates that surface as `AiAssistedReviewCandidate` (V1 pipeline under `V1_FIRST`; the versioned V2 admission boundary under `V2_PRIMARY`) | NOT measured by currency / condition bucket count alone (FU1 F7); NOT measured by call count |

### 5.2 False inclusion against hard-negative cases

| Metric | Source of truth | Measurement | Hard guard |
| --- | --- | --- | --- |
| **False inclusion** of materially incompatible products into same-product `HUMAN_CONFIRMED` or into the labeled variant-offer block | the frozen `ALWAYS_HARD_CONFLICT_CLASSES` (the actual ten-member set, §4.6) test cases + the held-out negative set | count of ALWAYS_HARD-listings ever promoted to same-product `HUMAN_CONFIRMED` + count of variant-offer rows whose persisted classification carries an ALWAYS_HARD class | MUST remain 0 (frozen response coherence + admission re-check, §4.4) |
| False inclusion of non-admitted outcomes (recorded `NO_MATCH` / `UNCERTAIN` / `RUNTIME_FAILURE`, grounded-bar failures, pending) into any confirmation | the confirm path's ledger re-verification + the admission derivation | count of CONFIRMED candidates whose persisted class is not `V2_ADVISORY_SAME_PRODUCT` / `V2_ADVISORY_VARIANT_SUSPECTED` / `V2_ADVISORY_VARIANT_VERIFIED` (or whose re-derived class disagrees) | MUST remain 0 (C2 / C3) |
| **Variant leakage into same-product pricing** (the C4 boundary) | the partition rule at the three derivation sites (live report, vendor replay, public replay) | count of confirmed variant-class indices present in any same-product index set (reviewed bucket keys, human-confirmed quote rows) | MUST remain 0 (proof scenario P8) |

### 5.3 Human-confirmed comparable offer count

| Metric | Source of truth | Measurement |
| --- | --- | --- |
| **Human-confirmed comparable offer count** (after human action) | `AiAssistedReviewCandidate` rows where `review_state=CONFIRMED`, partitioned by `evidence_source` and the persisted advisory class (the `v2_review_admission` field; null ⇒ V1 same-product) | total count + per-class breakdown |

### 5.4 Inclusion in the actual intended comparison output

| Metric | Source of truth | Measurement |
| --- | --- | --- |
| **Inclusion in the actual intended comparison output** (reviewable AND confirmed AND visible in comparison output) | the rendered comparison output (working quote, reviewed bucket, or the labeled variant-offer block) | count of candidates that are reviewable, confirmed, and visible; % of total reviewable candidates that reach visibility |

### 5.5 Variant labeling and unit-comparability accuracy

| Metric | Source of truth | Measurement |
| --- | --- | --- |
| **Variant labeling accuracy** | confirmed variant-class candidates + the variant-offer block | % of confirmed-variant rows whose variant label agrees with the held-out label (Suspected vs Verified; the recorded REVIEWABLE dimension) |
| **Unit-comparability accuracy** | `CandidateSalesUnitEvidenceV2` channel (as persisted in the V2 case) | % of confirmed variant rows whose sales-unit channel state agrees with the held-out label; % of confirmed rows whose `kind` / `quantity` agree (OBSERVED only); count of unit-normalized prices fabricated over `UNAVAILABLE` channels — MUST remain 0 (C7) |

### 5.6 V1 vs V2 outcomes on the same evaluation population

| Metric | Source of truth | Measurement |
| --- | --- | --- |
| **V1 vs V2 outcomes on the same evaluation population** (same held-out cases run through the FU3B V1 pipeline and the V2 admission boundary) | the held-out set run through both pipelines | coverage delta, false-inclusion delta, agreement rate, provenance-level agreement (U1 / U2 / U3 / U4 / U5) |

### 5.7 Replay integrity and boundary equivalence (carried over from the original §5.5; FU2 C3/C4)

| Metric | Source of truth | Target |
| --- | --- | --- |
| `schema_version` versioning of `PriceIntelligenceSnapshot` | V1 codec; FU2 replay correction | Preserved |
| V1 replay-boundary binding primitive (`is_review_candidate_binding_valid`) | `research/matching.py` | Preserved byte-identical; V1 candidates only; the V2 binding primitive is separate (§4.2) |
| Cross-run / cross-snapshot / cross-attempt replay safety | PLAN §26.12 | Preserved |
| `SemanticDecisionRecord` four-adapter registry + five-axis dispatch | `research/semantic_decision_codec.py` | **Unchanged** — no new adapter registered by this amendment; all four adapters' bindings decode identically (C3) |
| V2-PERF ledger row immutability | `persist_semantic_decision` (append-only) + the digest anchor | zero rows modified / rewritten; tamper ⇒ fail-closed on load (C3) |
| Versioned boundary equivalence (C4) | `reviewed-price/2` vs `aggregate_reviewed_listing_prices`; `compact-quote/2` vs `project_human_confirmed_rows` | byte-identical outputs for any index set on which the frozen v1 guard passes (proof scenarios P2 / P6) |

### 5.8 Anti-metric (the "not just more calls" bar, FU1 F7)

The amendment does **not** count the following as success:

* "More semantic calls" or "lower median latency" as a primary metric.
* Currency / condition bucket-count delta as a recall proxy.
* An automatic +20% bucket target.
* An `INSUFFICIENT_EVIDENCE` ≥ 5% target (this metric was perverse:
  FU1 F7 removed it; FU2 C3 removes the `ADVISORY_NO_FIRE` no-record
  concept entirely — the V2 evaluation ALWAYS persists its ledger row
  for every V2-executed candidate, and non-admission is a derived,
  explainable state, not a stored outcome and not a counter).
* Fabricated baseline numbers (every metric is grounded in an
  existing frozen test or held-out labeled set).
* Treating "no review candidate" as "no semantic execution evidence"
  (C3 interpretation rule — a display or metric that conflates the two
  is a defect, not a result).

---

## 6. Design-scope impact (per surface) — FU1-corrected, FU2 C1–C7-aligned

The amendment is assessed against each surface named by the direction
document.

### 6.1 Frozen V2 eligibility and conflict boundaries

* The V2 execution-eligibility predicate `is_v2_semantic_eligible`
  (`research/semantic_v2.py`) is **unchanged**. The versioned V2 review-
  admission boundary (§4.2) is a separate predicate with separate
  inputs (persisted ledger evidence + attestation); it does not replace
  `is_v2_semantic_eligible` and does not modify its signature. (C1: the
  two answer different questions — "may the runtime evaluate this?" vs
  "may a review candidate be created from the persisted evaluation?".)
* The frozen S2-A derived state vocabulary (`derive_identity_state_v2`,
  `research/semantic_authority_v2.py`) and conflict precedence are
  **preserved verbatim** — including the actual mapping
  `NONE` + usable title ⇒ `U4_NO_MPN` (C1 correction of record).
* The actual complete `ALWAYS_HARD_CONFLICT_CLASSES` set (ten members —
  §4.6) and the REVIEWABLE / PRICE_DIMENSION_ONLY sets are **preserved
  verbatim**.
* The `SemanticMatchResponseV2` coherence invariant is preserved (no
  `VARIANT` or `INSUFFICIENT_EVIDENCE` added to the frozen model
  vocabulary — the variant classification is DERIVED over the persisted
  record, C3/C6).
* The ONLY sanctioned frozen-contract change touching this surface is
  the separately gated SV2-G redesign of the out-of-shape
  `MPN_MISMATCH` ⇒ `C1` mapping (§4.6) — not part of this amendment's
  implementation scope, and it fails closed to the frozen mapping until
  approved.

### 6.2 Main-flow candidate description / specification evidence (FU1 F5, FU2 C7 corrected)

* The main-flow builder continues **not** to carry description or
  specification text into 3C matching (PLAN §16.3 "no description
  semantics" rule is preserved).
* The actual MVP for grounded NO_MPN evidence is the additive 3A
  extractor contract of §4.11 (SV2-A): a new named RAW description
  field + deterministic bounded extraction of product-dimension facts
  under a reviewed rule, persisted through the existing channels
  (snapshot payload + recorded V2 case). A contract shape alone is not
  a delivered data source; the phase's deliverable is the published +
  persisted field, with the reconstruction proof (persisted-artifacts-
  only replay of the V2 input).
* The 6A / 6B / 6C framework contracts are **unchanged**: 6A remains
  not implemented; 6B (Enterprise SSD) remains frozen and approved;
  6C remains frozen. The amendment does not advance 6A. SV2-A's
  bounded dimension extraction MAY reuse the frozen 6B schema where it
  applies (category-driven), without changing 6B.
* The `CandidateEvidenceSourceV2` `LISTING_TITLE` / `SPECIFICATION_TEXT`
  / `REVIEWED_PRODUCT_CONTEXT` RESERVED members remain RESERVED in the
  main flow until SV2-A is approved; the live main-flow builder emits
  only `brand` from `PUBLISHED_STRUCTURED_FIELD` and `raw_title_text`
  from the published title; every other product dimension is explicit
  None. The recorded V2 case (persisted in the ledger row) is the
  authoritative reconstructed input — no live re-fetching.
* **`raw_reference` opaque discipline (AD-040)**: the amendment
  **never** parses opaque `raw_reference` as structured authority and
  **never** fabricates structured facts from model output (F5, C7).
* **Sales units**: unknown stays unknown — the main-flow channel is
  always `UNAVAILABLE`; no unit-normalized price is ever fabricated
  (C7).

### 6.3 V2 review candidate creation (FU1 F3, FU2 C2/C3 corrected)

* `AiAssistedReviewCandidate` field inventory: the existing fields are
  **re-pinned unchanged**, with ONE additive exception — the immutable
  versioned `v2_review_admission` JSONField (null for V1 candidates and
  for every historical row; one additive migration; `editable=False`).
  The FU1 "no new model fields" position is withdrawn: the persisted,
  testable authority-class record is the C4 data boundary, and a free-
  text `semantic_reason_code` tag is not a boundary.
* The `runs/ai_assisted_review.py` review-write ownership is **extended
  by the versioned admission service** (§4.2): same state machine, same
  conditional-update concurrency, same unique constraint; the producer
  runs inside the atomic publication block AFTER the V2 ledger
  persistence (ordering contract).
* The single `(run, assessment_index)` UNIQUE constraint remains the
  duplicate / contradiction prevention mechanism (C5 coexistence
  invariant, with the run policy deciding the producer).

### 6.4 Human confirmation eligibility (FU1 F3 + F4, FU2 C2 corrected)

* `is_human_review_eligible_assessment` is **NOT extended** — it stays
  byte-identical as the V1 (FU3B) admission and same-product guard
  (C2: the assessment-only predicate carries no implicit V2 authority).
* The V1 binding primitive `is_review_candidate_binding_valid` is
  **NOT extended** — V2 candidates use the separate
  `is_v2_review_candidate_binding_valid` (§4.2), dispatched on the
  persisted class; historical V1 replay is byte-identical.
* `confirm_candidate` (the actual entry point; the FU1 text's
  `confirm_review_candidate` name is corrected) gains ONE versioned
  branch: for non-null `v2_review_admission` rows it re-loads the
  ledger row (digest + strict decode) and re-derives the classification
  before the transition; null-class (V1) rows take the existing path
  byte-identically. `reject_candidate`, `undo_review`, and
  `remove_candidate_from_working_quote` are unchanged in behavior.
* The 8-step review-POST validation is **preserved** in strength
  (PLAN §26.11.2). The persisted snapshot authority at both replay
  boundaries is **preserved** (PLAN §26.12).

### 6.5 Reviewed Price and Working Quote integration (FU1 F4, FU2 C4 corrected)

* `aggregate_reviewed_listing_prices` is **unchanged** — including its
  frozen FU3B-eligibility guard, which stays a fail-closed pin; v2-
  authorized non-FU3B-eligible indices must never be routed through it
  (P2 negative test).
* The versioned `reviewed-price/2` boundary runs the IDENTICAL frozen
  arithmetic over the class-proven same-product index set and is
  proven byte-equivalent to v1 on v1-guard-passing inputs (C4).
* The frozen `derive_human_confirmed_assessment_indices` is
  **unchanged** for `V1_FIRST` runs; `V2_PRIMARY` runs use the versioned
  same-product derivation + the variant partition (§4.7) — one index in
  at most one partition; no confirmed variant index can enter a human-
  confirmed quote row or a reviewed bucket in either replay (P8).
* The variant-offer block is **never** in the reviewed bucket, **never**
  in any 4A bucket, **never** in Machine Price; it is display evidence
  only (no aggregation over variants).
* Working Quote policy is **unchanged** — `remove_candidate_from_working_quote`
  and the V0/V1/V2 disposition ordering remain as recorded; under
  `V2_PRIMARY`, v2 UNREVIEWED candidates are display-only (no working-
  quote auto-include — automatic inclusion remains qualification
  territory, §4.10).
* `PriceIntelligenceSnapshot` (Machine Price) is **never** mutated by
  the new clauses.

### 6.6 V1 → V2 primary migration / historical compatibility (FU2 C5 corrected)

* The versioned run-level review policy (§4.9) is the migration
  mechanism: `ResearchRun.review_engine_policy` (additive column,
  default `V1_FIRST`) + the frozen code constant
  `CURRENT_REVIEW_POLICY_VERSION` (today `V1_FIRST`).
* V1 RETIREMENT (removing V1 surfaces) is **out of scope** and remains
  a separate later gated phase; V2-PRIMARY ADOPTION is designed, gated,
  and test-specified but **NOT activated** by this amendment.
* Historical V1 compatibility is **preserved**: V1 codec, V1 snapshot
  decoder, V1 replay boundaries, every frozen test — byte-identical
  (P6).

### 6.7 Nonblocking V2 lifecycle / pending-and-failed review states (FU1 F8, FU2 C5 corrected)

* The amendment is **compatible** with FU2 Option B but does not
  presuppose it (§4.9).
* The existing A1 instrumentation continues to record per-attempt V2
  latency / token usage (the V2-PERF record — unchanged).
* The FU1 `ADVISORY_NO_FIRE` no-record concept is **withdrawn** (C3):
  every V2-executed candidate has a persisted ledger row; the bounded
  non-admission reasons (§4.1) and the pending / failed display states
  (§4.9) are derived, explainable, and ledger-referenced — no silent
  loss, no unsafe fallback to V1 candidate creation.

### 6.8 Qualification V3 and pricing-authority gates

* The amendment does **not** open the qualification gate (§4.10).
* The FU4 Bundle authority program remains UNAPPROVED / NOT EXECUTED;
  C2 remains DRAFT ACCEPTED / FINAL HOLD; v1.0.0 seal remains
  FINAL-HOLD.
* The C1 / C2 governance batches continue to gate any future
  implementation that would advance the qualification program — and, per
  §4.9, any advancement of `CURRENT_REVIEW_POLICY_VERSION` to
  `V2_PRIMARY`.

---

## 7. Minimum viable changes (MVC) and phase dependencies — FU2 C-corrected

Each MVC is a **bounded phase** with its own gate; **none** is approved
by this amendment. The amendment only enumerates the MVC list and the
dependencies. Each phase has a genuinely implementable input and output
contract. (FU2: the phase list is re-anchored on C1–C7 — SV2-A becomes
the evidence-acquisition MVP, SV2-B becomes the versioned V2 review-
authority boundary (admission + classification storage + versioned
reviewed / replay boundaries), SV2-C serves the VERIFIED tier only,
SV2-E becomes the V2-primary policy adoption, and SV2-G is added for
the otherwise-excluded MPN mismatches.)

### Phase SV2-A — Evidence acquisition and the actual MVP (FU2 C7)

**Input contract (genuinely implementable):**
* The actual `ListingObservation` published fields (`research/listings.py`)
  and the actual live V2 builders (`build_candidate_product_evidence_v2`,
  `build_candidate_commercial_evidence_v2`) — the delivered data source
  of record (§4.11).
* The frozen `CandidateProductEvidenceV2` / `CandidateCommercialEvidenceV2`
  shapes (no new members in `CandidateEvidenceSourceV2`).

**Output contract (genuinely implementable):**
* ONE additive 3A extractor contract: a new named RAW field on
  `ListingObservation` carrying the page-published description /
  specification text (mapped to `raw_specification_text`), PLUS
  deterministic bounded extraction of product-dimension facts from
  published structured positions under a reviewed extraction rule
  (category-schema-driven where the frozen 6B schema applies), each
  recorded as a `PUBLISHED_STRUCTURED_FIELD` fact.
* Persistence through the EXISTING channels only: named observation
  fields in the `PriceIntelligenceSnapshot` payload; the recorded V2
  case in the V2-PERF ledger row. NO new model, NO new ledger row, NO
  new codec adapter.
* The reconstruction proof: the V2 input reconstructed from persisted
  artifacts ONLY (no network, no `raw_reference` parse) digests equal
  to the recorded case (§4.11, P2 infrastructure).
* The delivered artifact is PUBLISHED + PERSISTED evidence — a contract
  shape alone is not acceptance.

**Scope:** `research/listings.py` (additive named field + extractor
  rule); the 3A extraction module; the V2 builder mapping; codec
  re-pins where the snapshot payload shape changes. `research/identity.py`,
`research/matching.py` frozen predicates: **unchanged**.

**Gate (proposed):** ChatGPT independent review over the actual source
diff + the test evidence (frozen pin suites re-verify; AD-040
`raw_reference` discipline pinned).

### Phase SV2-B — The versioned V2 review-authority boundary (FU2 C2 / C3 / C4)

**Input contract:**
* The frozen assessment triple (read-only) via `ListingIdentityAssessment`.
* The persisted, verified V2 ledger row: `load_semantic_decision`
  (digest verification + strict codec dispatch over the four-adapter
  registry) — or the explicit absent / pending state (§4.9).
* The SV2-C attestation guard read-side (for the VERIFIED tier).
* The run's persisted `review_engine_policy` (§4.9, SV2-E delivers the
  column; SV2-B consumes it and is testable with explicit values before
  the column exists).

**Output contract:**
* `derive_v2_advisory_classification` + `is_v2_review_admissible` +
  `is_v2_review_candidate_binding_valid` (contract `v2-review-admission/1`,
  §4.2) — pure research functions over persisted inputs.
* ONE additive immutable `v2_review_admission` JSONField on
  `AiAssistedReviewCandidate` (null for V1 / historical rows) + ONE
  additive migration; the runs-owned admission producer inside the
  atomic publication block (after V2 ledger persistence); the
  `confirm_candidate` versioned re-verification branch (§4.2 / §4.3).
* The partition rule + the versioned derivations / boundaries at ALL
  THREE confirmed-index sites (live report, vendor replay, public
  replay): `derive_v2_same_product_confirmed_indices`, the
  `reviewed-price/2` aggregation boundary, the `compact-quote/2`
  projection, and the variant partition feeding the SV2-F offer
  projection — with the byte-equivalence proofs over v1-guard-passing
  inputs (§4.7, P2 / P6 / P8).
* **Zero** changes to: `is_human_review_eligible_assessment`,
  `is_review_candidate_binding_valid`, `aggregate_reviewed_listing_prices`,
  `project_human_confirmed_rows`, `derive_human_confirmed_assessment_indices`,
  the four-adapter registry, the ledger model / codec / service.

**Gate (proposed):** ChatGPT independent review; frozen pin suites
re-verify; the P2 / P6 / P7 / P8 proof nodes pass; V1 paths and tests
remain byte-identical.

### Phase SV2-C — VariantSimilarityTableV2 (attested-variant guard, VERIFIED tier only, FU2 C6)

**Input contract:**
* Documented manufacturer sources (manufacturer URL + retrieval
  instant + content SHA-256).
* Explicit operator attestation (bounded self-reported provenance
  pattern, NOT authentication, NOT manufacturer authority).
* **NEVER** edit-distance, suffix-character heuristics, character
  similarity, embedding similarity, or model-inferred similarity.

**Output contract:**
* Append-only `runs.VariantSimilarityEntry` rows with provenance, bound
  to the (requested MPN, candidate MPN) pair.
* The read-side guard consumed by `derive_v2_advisory_classification`
  for the VERIFIED tier (§4.6). **Suspected-variant discovery does NOT
  consume this table** (C6) — an empty table changes nothing about
  suspected admission; it only withholds the VERIFIED label.

**Scope:** a new `runs/models.py::VariantSimilarityEntry` model
(append-only; provenance-bound; no similarity oracle); a bounded
`runs/variant_similarity.py` service (read-side guard + write-side
operator-attestation entry).

**Gate (proposed):** ChatGPT independent review; an additive migration
(`makemigrations --check --dry-run` reports "No changes detected" after
the additive migration is committed).

### Phase SV2-D — Qualification V3 (governance, NOT implementation)

**Input contract:** the FU4 / C2 / v1.0.0 governance state.

**Output contract:** governance-level decisions only; no code or
schema changes.

**Scope:**
* The C1 / C2 governance batches continue to gate any V2 advisory case
  moving to FU4 / C3 / E1 / E2 / P1 / Q1 / W1 — and, per §4.9, any
  advancement of `CURRENT_REVIEW_POLICY_VERSION` to `V2_PRIMARY`.
* The amendment does **not** open any of these gates.

**Gate:** the existing FU4 / C2 / v1.0.0 seal procedure (PLAN §26.34 /
§26.44 / §26.45 / §26.46; STATUS C2 entry).

### Phase SV2-E — V2-primary policy adoption (versioned run-level policy; FU2 C5)

**Input contract:** SV2-D qualification closure AND an explicit
independent approval of the V2-primary cutover (a separate record) AND
(if approved) FU2 Option B closure for the pending-state lifecycle.

**Output contract:**
* The additive `ResearchRun.review_engine_policy` column (default
  `V1_FIRST`) + the frozen code constant
  `CURRENT_REVIEW_POLICY_VERSION` advanced to `V2_PRIMARY` by the
  approval; the producer dispatch (V1 candidate creation suppressed for
  new `V2_PRIMARY` runs; V2 admission boundary becomes the sole
  candidate producer); the pending / failed review-surface states
  (§4.9) wired to the SV2-F presentation.
* V1 RETIREMENT (removing V1 surfaces, stopping V1 evaluation on
  retired-deployment timelines) remains a SEPARATE later gated phase
  with its own design of record — this phase changes which engine is
  primary for NEW runs, not what code exists.

**Scope:** `runs/models.py` (one additive column + migration);
`execution/orchestration.py` (producer dispatch under the persisted
  policy); no change to any frozen boundary (equivalence proofs carry
  the historical guarantee).

**Gate:** explicit cutover approval of record; P6 byte-identity re-
verified over the historical corpus after the constant advances.

### Phase SV2-F — Presentation: labeled variant offers + pending / failed states (FU2 C4 / C5)

**Input contract:**
* Existing `AiAssistedReviewCandidate` rows (including the persisted
  `v2_review_admission` classification).
* The variant partition from SV2-B (confirmed variant-class candidates).
* The non-admission / pending / failed states from SV2-B / SV2-E.
* Existing `web/presentation.py` presentation helpers.

**Output contract:**
* The separately labeled comparable-offer block (suspected / verified
  tier label, published price / currency, explicit sales-unit state,
  provenance, conflict-check result, attestation reference) in the
  review UI and in BOTH replays' projections — display evidence only,
  never aggregated.
* The bounded "not admitted — <reason>" / "semantic evaluation pending" /
  "semantic evaluation failed" review-surface states with ledger
  references (candidate absence is never rendered as "no semantic
  evidence", C3).
* Additive provenance tags on existing blocks (admission provenance
  substate; V1 vs V2 admission) — no change to existing block content.
* NO change to `aggregate_reviewed_listing_prices` arithmetic, the
  reviewed-bucket presentation, or Machine Price.

**Scope:** `web/templates/web/research_detail.html` (additive blocks);
`web/presentation.py` (additive helpers); the replay result types gain
the additive variant-offer / state projections (additive fields, frozen
fields unchanged).

**Gate:** ChatGPT independent review.

### Phase SV2-G — Frozen-contract redesign for otherwise-excluded MPN mismatches (FU2 C6)

**Input contract:** the frozen S2-A mapping (`derive_identity_state_v2`:
out-of-shape explicit `MPN_MISMATCH` ⇒ `C1_INCOMPATIBLE_EXPLICIT_MPN` ⇒
not V2-execution-eligible) and the identified suffix/revision shapes the
product wants to make discoverable (§4.6).

**Output contract:**
* An EXPLICIT, reviewed change to the frozen S2-A mapping admitting a
  bounded, named additional shape set to V2 execution (extended U5
  shape set or a new uncertain substate — SV2-G's design decision),
  with the re-pinned derivation tests, the qualification-corpus
  coverage for the new shape set, and the hard guards carried verbatim:
  never admit a recorded ALWAYS_HARD conflict; never promote identity;
  never weaken NM-1 / NM-2 or the C1 default (out-of-shape candidates
  remain C1 until the mapping is re-pinned); suspected-variant
  classification only (§4.6).
* Until SV2-G is approved: out-of-shape mismatches remain
  `C1_INCOMPATIBLE_EXPLICIT_MPN` with the explicit displayable state —
  no silent loss, no implicit routing.

**Scope:** `research/semantic_authority_v2.py` (frozen mapping — a
recorded frozen-contract amendment with its own decision log entry),
`research/semantic_v2.py` (eligibility docstring / pins), re-pinned
S2-A tests, corpus additions under the evaluation governance rules
(A / B / C / D — never "the implementation failed the case").

**Gate:** a SEPARATE independent review as a frozen-contract change
(this amendment names and guards it; it does not approve it).

### Phase dependency map (FU2 corrected)

```
SV2-A  ──►  SV2-B  ──►  SV2-F
   │            │           ▲
   │            │           │
   │            ├──► SV2-C ─┤ (SV2-B reads the VERIFIED-tier guard)
   │            │
   │            └──► SV2-E ─┘ (policy column + cutover; needs SV2-B)
   │
   └──────────────► SV2-G (independent frozen-contract track)
                         │
SV2-D (qualification V3) ┴──► gates SV2-E (cutover) + SV2-G activation
```

**Hard dependencies:**

* SV2-B depends on **SV2-A** (the grounded-evidence bar for `U4_NO_MPN`
  same-product admission guards on the SV2-A-delivered published +
  persisted facts; before SV2-A the bar simply is not met — execution
  and ledger evidence still happen, C1) and on **SV2-C** (the VERIFIED
  tier; before SV2-C only the SUSPECTED tier is classified — discovery
  is unaffected, C6).
* SV2-F depends on SV2-B (the offer / state projections need the
  partition and the persisted classification).
* SV2-E depends on SV2-B (the V2_PRIMARY dispatch needs the boundaries)
  and on SV2-D + the explicit cutover approval (governance).
* SV2-G is independent of SV2-A / B / F (it changes the frozen mapping;
  its activation still requires SV2-D governance) but its benefit
  (variant discovery for out-of-shape suffixes) is consumed through
  SV2-B's classification.

**Compatibility statements (FU2):**

* **Nonblocking Option B compatibility**: V2 ledger records remain
  append-only; the Option B lifecycle (durable states, recovery, retry,
  idempotency) applies to the pending-state display rule and the
  idempotent admission re-run without further contract change (§4.9).
* **Delayed / failed V2 evidence**: every V2-executed candidate has a
  persisted ledger row; non-admission is a derived, explainable state
  with a bounded reason — never a silent loss, never an unsafe fallback
  to V1 candidate creation (C3 / C5).
* **V1 retirement**: remains a separate gated phase after SV2-E (the
  policy adoption changes which engine is primary; it does not retire
  V1 code).
* **Vendor Price CIDR zero-knowledge**: limited to its actual protected
  commercial-data boundary (4D-C-SEC `vendor_price_access_allowed` over
  `REMOTE_ADDR`); F-2 HOLD preserved; not extended to non-commercial
  surfaces.
* **F-2 HOLD, frozen test preservation, unqualified V2 authority flags,
  and `CURRENT_REVIEW_POLICY_VERSION = V1_FIRST`**: all preserved.

---

## 8. Explicit non-scope / safety boundaries (the "do not" list) — FU1 F8 / FU2 C-corrected

These boundaries are **binding** for any implementation that descends
from this amendment. Each is traceable to a frozen rule.

1. **Do not weaken or delete any existing test.** `tests/` collection
   baseline is preserved; every frozen pin suite continues to byte-verify
   the frozen surface; the documented 11-node Windows subprocess flake
   allowlist is not expanded by this amendment (CLAUDE.md).
2. **Do not activate V2 pricing authority or V2-primary policy.**
   `V2_AUTHORITY_QUALIFIED` and `V2_PERF_AUTHORITY_QUALIFIED` remain
   `False`; `CURRENT_REVIEW_POLICY_VERSION` remains `V1_FIRST` (§4.9);
   no Machine Price mutation; no automatic promotion to Reviewed Price;
   no automatic promotion to `ACCEPTED`; no promotion into a 4A price
   bucket; no working-quote auto-include of V2 UNREVIEWED candidates.
3. **Do not treat arbitrary MPN suffix similarity as proof of
   equivalence.** Variant classification is derived from the persisted
   V2 evaluation (recorded REVIEWABLE conflict class, no ALWAYS_HARD
   class); the `VariantSimilarityTableV2` attestation serves the
   VERIFIED tier only and admits only documented manufacturer sources
   or explicit operator attestation (SV2-C / §4.6). 2A-FU1's withdrawn
   "delete every non-alphanumeric" lesson is preserved. **Edit-distance
   authority is forbidden**; **character-similarity authority is
   forbidden**; **self-reported operator strings are provenance, not
   authentication, not manufacturer authority** (FU1 F6 / FU2 C6).
4. **Do not override the frozen conflict precedence
   `HARD_CONFLICT > HUMAN_CONFIRMED > AI authority`.** S2-A and the
   frozen response coherence rule (`_validate_v2_response_coherence`:
   `MATCH`/`UNCERTAIN` + any ALWAYS_HARD class is unconstructible — "a
   hard conflict is a structured NO_MATCH") enforce this; the admission
   derivation re-checks it fail-closed over the persisted record. The
   actual complete `ALWAYS_HARD_CONFLICT_CLASSES` set (ten members —
   §4.6) is the reference, never the FU1 six-name list.
5. **Do not assume description / specification text exists in the main
   flow.** The live builder (`build_candidate_product_evidence_v2`) emits
   only `brand` from `PUBLISHED_STRUCTURED_FIELD` and `raw_title_text`
   from the published title; `raw_specification_text=None`; the
   sales-unit channel is always `UNAVAILABLE` (FU1 F5 / FU2 C7). The
   actual MVP that delivers grounded NO_MPN evidence is the additive 3A
   extractor contract of SV2-A (§4.11) — until it is live, the
   grounded-evidence bar is not met and `U4_NO_MPN` same-product
   admission does not fire (an explicit, explainable state).
6. **Do not change the deterministic authority.** 2A / 3C / 4A / 4B
   contracts, constructors, and post-init invariants are byte-identical
   (the ONLY sanctioned frozen-contract change on this surface is the
   separately gated SV2-G S2-A mapping redesign, §4.6).
7. **Do not advance the qualification gate.** FU4 Bundle authority
   program state remains UNAPPROVED / NOT EXECUTED; C2 remains DRAFT
   ACCEPTED / FINAL HOLD; v1.0.0 seal remains FINAL-HOLD.
8. **Do not modify the V1 codec, the V1 snapshot decoder, or the V1
   replay boundaries.** No caller-supplied index; no caller-supplied
   `PriceAggregationResult`; no schema_version bump. The frozen
   `SemanticDecisionRecord` envelope `schema_version=1` is preserved;
   **the four-adapter registry is unchanged — no new ledger adapter is
   registered by this amendment** (C3: the FU1 "new contract adapter
   with a `v2_advisory` section" design is infeasible and withdrawn); the
   V2-PERF record shape is unchanged.
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
    structured facts from it. SV2-A extracts from the fetched document
    under an explicit reviewed extractor rule — that is extraction, not
    opaque-reference parsing.
15. **Do not promote non-admitted outcomes to a confirmation.**
    `NO_MATCH`, `UNCERTAIN`, `RUNTIME_FAILURE`, grounded-bar failures,
    and hard-conflict-policy rejections create no candidate and can
    never be confirmed under any path; the `confirm_candidate` ledger
    re-verification + classification re-derivation (for non-null
    `v2_review_admission` rows) is the single guard, and the frozen V1
    confirm path (null-class rows) is byte-identical (FU1 F4 / FU2 C2).
16. **Do not modify or rewrite any existing `SemanticDecisionRecord`
    row — in particular any V2-PERF ledger row** (C3). The ledger is
    append-only through the single service write path
    (`persist_semantic_decision` never overwrites; a second persist for
    the same `(run, assessment_index)` fails closed); the
    `payload_digest` anchor detects out-of-band rewrites and fails every
    subsequent read closed. The advisory classification lives on the
    review candidate (§4.3), never in the ledger.
17. **Do not interpret an absent positive review candidate as absent
    semantic execution evidence** (C3). Every V2-executed candidate has
    a persisted ledger row (all outcomes); the fixed interpretation
    rule is: no ledger row ⇒ never V2-executed (or pending under the
    §4.9 policy); ledger row present + candidate absent ⇒ V2-executed,
    not admitted (bounded re-derivable reason). Displays, metrics, and
    tests must keep the two states distinct.
18. **Do not fabricate unit-normalized prices** (C7). Unknown sales
    units stay unknown: the `UNAVAILABLE` channel renders
    "Sales unit unknown — not normalized"; no per-unit number is
    derived; unit-comparability claims require both sides `OBSERVED`
    with bounded kinds. Same-product Reviewed Price arithmetic is
    unchanged.
19. **Do not extend the assessment-only V1 predicates** (C2).
    `is_human_review_eligible_assessment` and
    `is_review_candidate_binding_valid` stay byte-identical and carry no
    implicit V2 authority; V2 admission and binding run only through
    the versioned boundary (§4.2) over persisted, verified evidence.

---

## 9. Open questions / decision gates (for the reviewer)

These are the questions whose resolution gates any future implementation
that descends from this amendment. Each question is small, on-topic, and
non-blocking on the amendment itself. FU2 corrections resolve or
re-frame the previously-open questions; the open list below is the
FU2-narrowed set.

1. **SV2-A.1** — Should the `U4_NO_MPN` same-product grounded bar
   require **at least one** published product-dimension fact beyond
   brand, or **at least two** (defense in depth)? The FU2 default is
   "at least one" (a single independently published structured fact,
   or a `REVIEWED_PRODUCT_CONTEXT` candidate-side context), pending
   review. (Re-framed from FU1: the bar applies to the persisted V2
   case's recorded facts, not to an in-memory observation set.)
2. **SV2-A.3** — The FU1 `ADVISORY_NO_FIRE` counter question is
   RESOLVED and closed (C3): the V2 evaluation always persists its
   ledger row; non-admission is a derived state; no counter is
   persisted. No further decision is open here.
3. **SV2-B.1** — The variant-offer label vocabulary: the exact
   `<dimension>` rendering (e.g. `Verified variant — revision/suffix` vs
   `Verified variant — color X`) and whether the SUSPECTED label must
   carry the "pending verification" suffix in every surface (review UI,
   both replays). The FU2 default: the recorded REVIEWABLE conflict
   class name + the tier word; the suffix is mandatory for SUSPECTED.
4. **SV2-B.2** — Representation of the versioned `reviewed-price/2` /
   `compact-quote/2` boundaries: separate functions reusing the frozen
   arithmetic helpers (the FU2 default) vs a shared core with a versioned
   authorization parameter. The equivalence property (§4.7) is the same
   either way; this is an implementation-shape question for SV2-B.
5. **SV2-C.1** — Who is the operator identity for the attestation
   write-path? The existing `web/vendor_refresh_presentation.py` pattern
   uses a self-reported provenance (`operator="web"`); the
   `VariantSimilarityTableV2` may need the same bounded pattern OR an
   explicit identity (analogous to 8C). This is a future-phase decision;
   this amendment does not decide. FU1 F6 / FU2 C6 explicitly record
   that self-reported operator strings are provenance, NOT
   authentication, NOT manufacturer authority — and the attestation
   serves the VERIFIED tier only (suspected discovery does not consume
   it).
6. **SV2-D.1** — When (if ever) the FU4 Bundle authority program
   advances, do the variant classes (`V2_ADVISORY_VARIANT_SUSPECTED` /
   `V2_ADVISORY_VARIANT_VERIFIED`) need their own qualification corpus,
   or do they inherit the FU4 corpus? This is a future-qualification
   question; this amendment does not decide.
7. **SV2-E.1** — RESOLVED in shape, open in activation: the cutover is
   the versioned run-level policy (§4.9) — per-run, recorded at creation,
   advanced only by `CURRENT_REVIEW_POLICY_VERSION` under qualification
   + explicit approval. The remaining open question is the activation
   decision itself (governance), not the mechanism.
8. **SV2-G.1** — Which out-of-shape `MPN_MISMATCH` suffix/revision
   shapes enter the SV2-G bounded shape set (the frozen S2-A mapping
   redesign)? Candidates: multi-token suffix additions, reordered
   tokens, hyphen/case variants beyond the frozen normalization. The
   shape set must be bounded and named (never generic similarity),
   re-pinned with the derivation tests, and covered by the qualification
   corpus before activation. This amendment does not decide the set.
9. **SV2-F.1** — Does the presentation need a "V2 candidate pending /
   not admitted" block distinct from the existing human-review
   candidates? The FU2 default is YES for `V2_PRIMARY` runs (the §4.9
   explainable states must be visible to prevent "unexplained loss");
   for `V1_FIRST` runs the V2 evidence remains ledger-only with the
   existing presentation unchanged.

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
| `product_intelligence/research/semantic_authority_v2.py` | The frozen S2-A contract: `derive_identity_state_v2` (the actual `NONE` + usable-title ⇒ `U4_NO_MPN` mapping, C1); the S2-A state / substate / relationship-signal vocabularies; the actual complete conflict taxonomy (`ALWAYS_HARD_CONFLICT_CLASSES` — ten members — / `REVIEWABLE_CONFLICT_CLASSES` / `PRICE_DIMENSION_ONLY_CONFLICT_CLASSES`, C6); the bounded near-miss shapes (NM-1 / NM-2); the context provenance classes; the frozen `V2SemanticDecision` vocabulary (`MATCH / NO_MATCH / UNCERTAIN`, line 1835). |
| `product_intelligence/semantic/contract.py` | The frozen V1 `SemanticDecision` vocabulary (`MATCH / NO_MATCH / UNCERTAIN`). |
| `product_intelligence/research/semantic_decision_codec.py` | The `SemanticDecisionRecord` universal codec; the FOUR registered contract adapters (`SEMANTIC_V1_ADAPTER`, `SEMANTIC_V2_ADAPTER`, `SEMANTIC_V2_FU4_ADAPTER`, `SEMANTIC_V2_PERF_ADAPTER`); five-axis binding dispatch with singleton-claim fail-closed semantics (C3). |
| `product_intelligence/research/semantic_decision_v2_perf.py` | The V2-PERF record (`SemanticDecisionRecordV2Perf`) and its claimed binding `(V2, 2.0, 1, 2, SEMANTIC_AUTHORITY_V2_S2A_FU2)` — the existing V2-PERF ledger row this amendment must never modify or rewrite (C3). |
| `product_intelligence/research/aggregation.py` | The frozen 4A aggregation + `aggregate_reviewed_listing_prices` (incl. the frozen FU3B-eligibility guard `_validate_confirmed_indices` and the `ReviewedPriceEntry` origin invariants — the C4 same-product boundary). |
| `product_intelligence/research/price_result_codec.py` | The V1 codec + `decode_price_aggregation_result`. |
| `product_intelligence/research/compact_quote.py` | `project_human_confirmed_rows` / `project_ai_assisted_unreviewed_rows` (frozen v1 projections; the C4 "Human Confirmed" row surface). |
| `product_intelligence/research/working_quote_policy.py` | `classify_ai_match_for_working_quote` (the Working Quote disposition policy consumed by the derivation sites). |
| `product_intelligence/research/listings.py` | `ListingObservation` — the actual page-published named fields + the opaque `raw_reference` (AD-040) — the C7 evidence-acquisition source of record. |
| `product_intelligence/execution/semantic_integration.py` | `AiAssistedMatchResult`; `SemanticRuntimeResult`; the FU3B V1 admission path (`_is_semantic_eligible`, `_has_usable_evidence`, `evaluate_semantic_matches`). |
| `product_intelligence/execution/semantic_decision_v2_execution.py` | The V2 execution + record construction (`evaluate_semantic_matches_v2`, `build_semantic_decision_records_v2`, `persist_semantic_decision_records_v2`) — the ledger producer for every V2 outcome (C3). |
| `product_intelligence/execution/semantic_decision_persistence.py` | `persist_semantic_decision` (append-only; `SemanticDecisionAlreadyRecordedError`), `load_semantic_decision` (digest verification + strict decode — the "persisted, verified V2 evidence" input of C2), `replay_semantic_decision_record` (zero-live replay + binding proof — the C7 reconstruction path). |
| `product_intelligence/execution/orchestration.py` | The atomic publication block (snapshot → V1 candidates → V2 ledger rows → run terminalization) and the V1/V2 firewall comments — the SV2-B / SV2-E producer-dispatch site. |
| `product_intelligence/runs/ai_assisted_review.py` | The HUMAN-REVIEW write path; the review-state machine; the actual entry points `confirm_candidate` / `reject_candidate` / `undo_review` / `remove_candidate_from_working_quote` (C2 confirm extension site). |
| `product_intelligence/runs/models.py` | `PriceIntelligenceSnapshot`; `ResearchSupplementSnapshot` (4D-B, Vendor API commercial data); `ResearchFxSnapshot`; `AiAssistedReviewCandidate` (with the field inventory and the `(run, assessment_index)` UNIQUE constraint — the C3 classification-storage site, one additive versioned field); `SemanticDecisionRecord` (opaque versioned JSON payload, `schema_version=1` envelope, `(run, assessment_index)` unique binding, `payload_digest` anchor). |
| `product_intelligence/web/views.py` | The live report path: `_validate_confirmed_candidates` (the third confirmed-index derivation site — C4), the 4D-C ALLOWED / DENIED replay dispatch. |
| `product_intelligence/execution/compact_quote_replay.py` | The vendor-authorized replay boundary (`replay_compact_quote_projection`, `derive_human_confirmed_assessment_indices` — the shared C4 derivation). |
| `product_intelligence/execution/compact_quote_public_replay.py` | The public (DENIED-branch) replay boundary (`replay_public_compact_quote_projection` — consumes the shared C4 derivation; never reads vendor artifacts). |
| `tests/web/test_web_boundaries.py` | The web-layer import allowlist enforcement. |
| `tests/runs/test_vendor_refresh_*` (and the other frozen pin suites) | The frozen pin suites that byte-verify the frozen surface. |

---

## 11. Closing gate statement (FU2 status)

This amendment is **design only**. It proposes a bounded contract
delta (§4), mandatory end-to-end proof specifications (§4.12),
measurable success criteria (§5), and minimum viable changes (§7).
It does **not** implement code, **does not** change tests, **does
not** weaken any frozen contract, **does not** activate V2 pricing
authority, **does not** activate V2-primary policy (`CURRENT_REVIEW_
POLICY_VERSION` remains `V1_FIRST`), and **does not** change the
qualification program state.

FU1 review verdict: **CHANGES REQUESTED — DESIGN ONLY** (commit
`4c2388937ba00882ca9d72250d347004bfaef808`). F1–F8 corrections were
applied in place in this document.

FU2 review verdict: **CHANGES REQUESTED — DESIGN ONLY** (commit
`f164730ba20117e76a76b0eb4a1a6b06088ec089`). C1–C7 corrections and the
mandatory end-to-end proof specifications are applied in place in this
document:

* C1 — the U4 source-state analysis is corrected against the actual
  `derive_identity_state_v2` (`research/semantic_authority_v2.py`):
  a `NONE` source with a usable product title **already derives
  `U4_NO_MPN` and is V2-execution-eligible today**; the impossible
  `NONE AND (TITLE_TEXT OR SKU_FIELD)` condition is removed; V2
  execution eligibility, available bounded evidence, and human-review
  eligibility are three separately defined layers (§3.1, §4.1); no new
  U4 substate is introduced.
* C2 — review admission is made executable: an explicit versioned V2
  admission boundary (`v2-review-admission/1`) whose inputs include
  the persisted, verified V2 ledger evidence (loaded through
  `load_semantic_decision`) and the attestation guard; the
  assessment-only `is_human_review_eligible_assessment` and its binding
  primitive stay byte-identical and carry no implicit V2 authority;
  historical V1 replay is preserved (§4.2).
* C3 — ledger / adapter coexistence is resolved against the actual
  four-adapter registry, the `(run, assessment_index)` unique binding,
  and the append-only write path: the FU1 "new ledger adapter with a
  `v2_advisory` section" design is infeasible (slot occupied; rewrite
  forbidden; binding collision) and withdrawn; the advisory
  classification is stored on the review candidate as one additive
  immutable versioned field (smallest representation); every V2
  outcome including UNCERTAIN and RUNTIME_FAILURE remains preserved in
  the ledger; an absent positive candidate is never interpreted as
  absent semantic execution evidence (§4.3).
* C4 — separate price authority for variants: the actual live-report,
  vendor-replay, and public-replay confirmation paths and
  `aggregate_reviewed_listing_prices` are traced; the mechanism by
  which a confirmed comparable VARIANT could be misread as a same-
  product HUMAN_CONFIRMED index (the bare `frozenset[int]` carries no
  authority class) is demonstrated; the boundary is the persisted
  versioned classification + the partition rule at all three
  derivation sites + the versioned `reviewed-price/2` /
  `compact-quote/2` boundaries with byte-equivalence proofs; same-
  product Reviewed Price arithmetic is unchanged (§4.7).
* C5 — V2-primary migration behavior: the smallest versioned run-level
  review policy (`V1_FIRST` / `V2_PRIMARY`, recorded on
  `ResearchRun`, advanced only by qualification + explicit approval)
  with historical runs unchanged, single-producer coexistence, and
  explicit pending / failed states (no unsafe fallback, no unexplained
  loss); V2 authority is NOT activated in this task (§4.9).
* C6 — suspected and verified variant discovery are separated (no
  pre-existing attestation record is required to discover a suspected
  variant); reviewability is defined separately from identity and
  price authority; no edit-distance-based identity promotion; the
  actual complete `ALWAYS_HARD_CONFLICT_CLASSES` set (ten members) and
  the REVIEWABLE / PRICE_DIMENSION_ONLY sets are documented, and the
  FU1 six-name list (incl. the non-existent `SALES_UNIT` class) is
  corrected; the explicit frozen-contract redesign for otherwise-
  excluded MPN mismatches is named SV2-G (§4.6).
* C7 — evidence acquisition and the actual MVP: the actual page-
  published named fields (`ListingObservation`) are specified as the
  delivered data source; the persisted reconstruction path (recorded
  V2 case in the digest-anchored ledger row; zero live re-fetching; no
  opaque-`raw_reference` authority) is documented; the SV2-A additive
  3A extractor contract is the smallest safe path to grounded NO_MPN
  evidence; unknown sales units stay unknown and no unit-normalized
  price is ever fabricated (§4.11).

**Status: SEMANTIC-V2-PRODUCT-CONTRACT-FU2 — PENDING CHATGPT REVIEW.**

The next step is ChatGPT independent review over this corrected
document. Any implementation that descends from this amendment is
itself a bounded phase with its own design of record, its own
migration / corpus / schema discipline, its own test-preservation
record, and its own independent review — **none of which is approved
by this amendment**.
