# Product Intelligence — Semantic Authority V2: Prompt 2.1 Contract Design (Q3-B3)

**Session:** PRODUCT-INTEL.SEMANTIC-AUTHORITY-V2-Q3-B3 — Semantic V2 Prompt 2.1 Contract Design Review
**Starting SHA:** `12f5bed109470af483aab135434ff1ca5071a141` (Q3-B-FU1 endpoint)
**Test baseline at starting SHA:** 6928 collected (re-verified this session: per-file collection sum = 6928)
**Mode:** DESIGN-ONLY. No implementation, no live capture, no deployment, no authority promotion, no commit.

**Evidence of record (independently re-verified this session):**

| Artifact | Identity |
| --- | --- |
| Frozen prompt 2.0 | `product_intelligence/semantic/contract_v2.py`, `SEMANTIC_PROMPT_VERSION_V2 = "2.0"`; REAL system-prompt digest `c0cc98bdd6d357e81d4692218f18d354351fc2833267b3062b7cd74b18445a84` (`canonical_sha256({"text": SYSTEM_PROMPT_V2})`, recomputed and matched) |
| Frozen contract binding | `("V2", "2.0", 1, 1, "SEMANTIC_AUTHORITY_V2_S2A_FU2")` (`research/semantic_decision_v2.py`, drift-pinned) |
| Corpus | `evaluation/semantic_v2_qualification/corpus_v1.json`, v1.0.0, digest `2c37ba088c317d8cefc6ad0dd7e0d73cfd085f6474ef43eb6953e3cf0170b549` (56 cases: 36 AUTHORITATIVE + 7 AMBIGUOUS + 13 CONTRACT_NEGATIVE) |
| Primary live capture | `semantic_v2_live_captures/q3b-20261009T010312Z-amax__direct__amax_qwen3.8-27b.json`, SHA-256 `d94f1ed8ec4d254aa2a80e4ff58bd0bc55eb8c3744ad22f53f0b602ae9084d9f` (38,945 bytes; re-hashed, matched); manifest `46f818bb...b79` (20,293 bytes) |
| Official offline report | `reports/q3b-20261009T010312Z-amax__direct__amax_qwen3.8-27b__report.json`, report digest `40340ce47d36d3b33b0dcf2a8dcce722abf0a34a399876ed174b6f558866f906` |
| Q3-B2 diagnosis | `semantic_v2_live_captures/q3b2-primary-recall-diagnosis.md` / `.json` (untracked session artifacts; derived from the preserved capture through the frozen parser; cross-checked against the official report, 11/11 agreement) |
| Fallback capture | does not exist (endpoint unconfigured; runner failed closed; Q3-B2 §6) |

**Observed primary result (unchanged, per the official report):** 43/43 status OK and parser-valid; 22 NO_MATCH / 21 UNCERTAIN / 0 MATCH; 24 CORRECT / 7 DEFENSIBLE / 11 ABSTAIN_ON_DEFINITE (all 11 expected-MATCH cases) / 1 FALSE_NO_MATCH (`V2Q-SSD-CONTRA-0037`, severity REVIEW); MATCH precision UNAVAILABLE (denominator 0); MATCH recall 0/11 = 0.0; NO_MATCH accuracy 20/20; all eight safety gates PASS; decision POLICY_PENDING (DRAFT policy).

This document designs a safe, explicitly versioned **Prompt 2.1** contract that resolves the observed zero-MATCH recall without weakening any Semantic V2 identity, packaging, sales-unit, or relationship-authority protection. It contains the full proposed 2.1 wording as a versioned draft (not an in-place edit), the decision matrix, the relationship-authority semantics, the eleven-case behavioral analysis, the adversarial regression test plan, the production-input limitations, the recommendation, and the explicit unresolved risks and approval questions.

---

## 1. Scope and non-scope

**In scope (design only):**

1. Independent inspection of the frozen S2-A / S2-B(-FU1) / S2-C(-FU1) sources and Prompt 2.0, and of the preserved capture evidence for all 11 expected-MATCH cases and the safety-relevant negative/uncertain cases.
2. The exact Prompt 2.0 ambiguities, with source references.
3. The sales-unit blocking rule: exactly when missing sales-unit information must block MATCH and when it may remain unresolved without proving a contradiction.
4. The proposed Prompt 2.1 system prompt and user-prompt template as a versioned draft, with a change table against 2.0.
5. The relationship-authority semantics and the four-way separation of identity decision, relationship authority, ProductEvidenceQuality, and pricing eligibility.
6. The eleven-case expected-behavior analysis under 2.1, plus the full 43-case + 13 negative-case regression expectation.
7. The adversarial regression test plan for the implementation and requalification phases.
8. The production-input limitations and the prompt-only vs extraction-first vs combined recommendation.
9. Explicit unresolved risks and approval questions.

**Out of scope (prohibited by the task):**

- No implementation (no source, test, corpus, threshold, or policy change in this session).
- No live model calls, no capture, no deployment, no qualification approval, no authority promotion.
- No commit (documentation-only deliverable left untracked in the worktree).
- No relabeling of the frozen corpus: the 56 case labels are the benchmark; "the new implementation failed this case" is not a reason to move them.
- No changes to the DRAFT qualification policy, the eight safety gates, the S2-A authority contract, the output schema, the reason-code vocabulary, or the input schema.

## 2. Independent inspection of the frozen sources

### 2.1 S2-A — `product_intelligence/research/semantic_authority_v2.py` (frozen authority contract)

Independently inspected (not taken from STATUS/PLAN at face value):

- **Conflict taxonomy and severity sets** (lines 986–1120): 14 `ConflictClass` values. `ALWAYS_HARD_CONFLICT_CLASSES` = {MPN_IDENTITY, PRODUCT_FAMILY, GENERATION, CAPACITY, INTERFACE, FORM_FACTOR, PRODUCT_ROLE, ACCESSORY_RELATION, PACKAGING_QUANTITY, BUNDLE}; `REVIEWABLE` = {REVISION_OR_SUFFIX, BRAND, OTHER_MATERIAL_CONFLICT}; `PRICE_DIMENSION_ONLY` = {CONDITION}. This is the source of the **absolute rule**: published incompatible packaging quantities (PACKAGING_QUANTITY) and different sales units / bundles (BUNDLE) are ALWAYS_HARD.
- **`SEMANTIC_OUTCOME_TIER_MATRIX`** (lines 2081–2168): all 27 (decision × confidence × product-evidence-quality) entries. The highest tier reachable from ANY semantic outcome is `AI_ASSISTED_COMPARABLE` (MATCH + HIGH + STRONG only). Every NO_MATCH → `EXCLUDED_LOW_CONFIDENCE`. UNCERTAIN rows → NEEDS_REVIEW or EXCLUDED. This is the **evidence-quality ceiling** and the identity-vs-authority separation in one table.
- **Ceilings (restrict only, never lift)** in `derive_authority_tier` (lines 2412–2620): (i) MATCH with any REVIEWABLE conflict → NEEDS_REVIEW (`CEILING_REVIEWABLE_CONFLICT`); (ii) U5 + near-miss-substitution active **without** relationship authority → NEEDS_REVIEW (`CEILING_NEAR_MISS_SUBSTITUTION_WITHOUT_RELATION_AUTHORITY` — the **NM-2 ceiling**, Product-lead amendment 1; explicitly does NOT fire when `MANUFACTURER_RELATION_AUTHORITY` is present, since `has_relationship_authority` returns True); (iii) state/substate requirement `REVIEWED_RELATION_AUTHORITY_REQUIRED` with dimension B not ESTABLISHED → NEEDS_REVIEW (`CEILING_IDENTIFIER_RELATIONSHIP_NOT_ESTABLISHED`). Precedence inside the AI path: hard-conflict supersession is applied **last** (`HARD_CONFLICT_SUPERSEDES`): any ALWAYS_HARD conflict class in the response forces tier `HARD_CONFLICT`.
- **`SUBSTATE_RELATIONSHIP_REQUIREMENTS`** (lines 1415–1503): U1_TITLE_MPN → NOT_REQUIRED; U2 + SKU_EQUALS_TARGET → NOT_APPLICABLE; U2 + SKU_NOT_TARGET, U3_PARTIAL_BOUNDARY, U5 + NEAR_MISS_TRUNCATION, U5 + NEAR_MISS_SUBSTITUTION → REVIEWED_RELATION_AUTHORITY_REQUIRED; U4_NO_MPN (both signals) → NOT_APPLICABLE; verified/C1/E1/E2 → NOT_APPLICABLE. `substate_relationship_requirement` (lines 1503–1556) documents the exact use: "the tier is capped at NEEDS_REVIEW (fired rule CEILING_IDENTIFIER_RELATIONSHIP_NOT_ESTABLISHED) when — and only when — the requirement is REVIEWED_RELATION_AUTHORITY_REQUIRED and dimension B is not ESTABLISHED." **The requirement is tier policy; it is not a model-decision input.**
- **`derive_relationship_authority`** (lines 1283–1350): U4 → NOT_APPLICABLE regardless of provenance; DETERMINISTIC_UNCERTAIN → ESTABLISHED **only** with a provenance carrying `ESTABLISH_IDENTIFIER_RELATIONSHIP` (today exactly `MANUFACTURER_RELATION_AUTHORITY`); `CUSTOMER_RETRIEVAL_RELATION` **never** establishes (capability `RETRIEVAL_RECALL_ONLY` only — **customer retrieval zero authority**).
- **`derive_product_evidence_quality`** (lines 1721–1793): STRONG requires a usable product title plus ≥2 bounded matched facts spanning ≥2 distinct hard product dimensions, each grounded in `LISTING_PRODUCT_TITLE` or `REVIEWED_PRODUCT_CONTEXT`; the candidate-source vocabulary has **no model-claim member** (the model cannot self-promote authority); a title alone is LIMITED, never STRONG.
- **Provenance capability table** (lines 1124–1220): the three distinct classes and their disjoint capabilities, including "CUSTOMER_RETRIEVAL_RELATION ... MUST NEVER, by itself: establish identity; ... be described to the model as manufacturer-established equivalence."

### 2.2 S2-B / S2-B-FU1 — persistence envelope and V2 adapter (frozen)

- `research/semantic_decision_record.py` / `semantic_decision_codec.py` / `semantic_decision_replay.py`: the universal envelope is contract-agnostic; interpretation dispatches on the RECORDED (envelope schema version, semantic contract version) pair through the registered adapters; `SUPPORTED_CONTRACT_BINDINGS` is exactly the union of the registered adapters' supported bindings; unknown bindings are refused explicitly.
- `research/semantic_decision_v2.py` (S2-C): `V2_CONTRACT_BINDING = ("V2", "2.0", 1, 1, "SEMANTIC_AUTHORITY_V2_S2A_FU2")`; `supported_bindings=(V2_CONTRACT_BINDING,)` (line 2359); the zero-live replay "knows exactly one safe envelope ... and REFUSES explicitly any other (unknown or future) binding"; PLAN §26.26(7)/§26.27 states verbatim: *"a future V2-lineage binding (e.g. prompt 2.1) is refused explicitly — never reinterpreted under the current contract."* **The frozen design already anticipates 2.1 as a separate registered binding.**
- The S2-C-FU1 versioning precedent (PLAN §26.27(1)): 2.0 was amended in place **only because** S2-C was pre-freeze, unshipped, and no V2 record existed. That condition no longer holds for 2.0 (S2-A/S2-B/S2-C/S2-C-FU1 are APPROVED / FROZEN per the Q3-A/Q3-B operator briefings; 2.0 is sealed into the corpus digest, the capture schema pin, the adapter, and the replay gate). **2.1 must therefore be a new explicit version — a versioned draft, never an in-place edit of 2.0.**

### 2.3 S2-C / S2-C-FU1 — input/output contract and Prompt 2.0 (frozen)

- `research/semantic_v2.py` (2,131 lines): `SemanticMatchCaseV2` (17 required top-level fields, five sections A–E, no silent defaults); `CandidateSalesUnitEvidenceV2` with the explicit channel (`UNAVAILABLE` — all value fields None — or `OBSERVED` with bounded `SalesUnitKindV2` SINGLE_UNIT / PACK_QUANTITY / TRAY_OR_FACTORY_PACK / BUNDLE, published raw detail, provenance, and bounded positive quantity where the kind carries one); the output contract (decision / confidence / 17 reason codes / 12 bounded dimensions / structured conflicts); `REASON_CODE_RULES` coherence (a NO_MATCH is always conflict-grounded; MATCH/UNCERTAIN may never carry an ALWAYS_HARD class — enforced at construction in `_validate_v2_response_coherence`, lines 1913–1966: "a hard conflict is a structured NO_MATCH and can never be overridden or hidden by the semantic output").
- **The live builders (the structural amplifier, independently confirmed):** `build_candidate_commercial_evidence_v2` (lines 871–912) hard-wires `sales_unit=SALES_UNIT_EVIDENCE_UNAVAILABLE` — "the main-flow extractor publishes no packaging field, and no packaging value is inferred from price, availability, or any other commercial fact." `build_candidate_product_evidence_v2` (lines 829–870) fills **only** the published brand field; every other product dimension is explicit None; the title is RAW observation text; no specification text is carried (it stays in the opaque `raw_reference`, which no business rule may parse, per AD-040 as recorded in PLAN §26.27(2)). `build_v2_product_evidence_profile` is unchanged from S2-A, and the live path passes `matched_facts=frozenset()` (documented limitation: the main flow grounds no bounded identity-dimension equality, so live candidates are at most LIMITED).
- `semantic/contract_v2.py` (the Prompt 2.0 owner): `SYSTEM_PROMPT_V2` (the full frozen system prompt; digest `c0cc98bd...` recomputed and matched); `render_v2_user_prompt` (the five-section deterministic rendering; the relationship requirement renders at line 435 under the header *"DETERMINISTIC IDENTITY CONTEXT (frozen deterministic layer output; you cannot override it)"*); the frozen provenance labels (CUSTOMER_RETRIEVAL_RELATION = retrieval-only, zero identity authority; MANUFACTURER_RELATION_AUTHORITY = stronger, labeled manufacturer relationship authority; MANUFACTURER_PRODUCT_CONTEXT = grounding only); the sales-unit UNAVAILABLE rendering (line 244: *"absence is NOT proof of equal sales unit (do not infer a single unit)"*).
- `semantic/runtime_v2.py`: the V2 pinned route, temperature 0.0 / max_tokens 32768, fallback on execution failure only, `V2_AUTHORITY_QUALIFIED = False`.

### 2.4 Q3-A … Q3-B-FU1 — qualification harness, corpus, capture (frozen as reviewed)

- `evaluation/semantic_v2/corpus.py`: strict loader; the corpus document's `semantic_contract_binding` must equal the frozen production binding `V2_CONTRACT_BINDING` (lines 1173–1180) — **a 2.1 requalification requires a corpus re-seal to the 2.1 binding (Section 8.1), not a label change.** Per-case `case_digest` is computed over the per-case state only (line 1095–1098) — the top-level binding is **not** part of any per-case digest, so a binding-only re-seal leaves all 56 `case_digest`s byte-identical, which is a mechanical proof of label invariance. The `corpus_digest` covers the document minus `label_revisions` and itself (lines 1205–1207), so it does change with the binding.
- `evaluation/semantic_v2/gates.py`: the eight mandatory hard safety gates (`HARD_SAFETY_GATES`, lines 56–65) and the fail-closed decision precedence (NOT_QUALIFIED > POLICY_PENDING > INCOMPLETE_COVERAGE > BELOW_THRESHOLD / THRESHOLD_INDETERMINATE > QUALIFIED). The input-aware authority cross-check (gate 5) flags `MATCH_AUTHORIZED_IDENTIFIER_RELATION` responses whose input did not label `MANUFACTURER_RELATION_AUTHORITY` (`UNAUTHORIZED_AUTHORITY_CLAIM`, plus `CUSTOMER_ALIAS_PROMOTION` when a customer-retrieval relation is present) — `evaluator.py` lines 321–326.
- `evaluation/semantic_v2/policy/qualification_policy_draft_1.json` (data dir `evaluation/semantic_v2_qualification/policy/`): DRAFT-1, `approved: false`, thresholds match_precision ≥ 0.99, match_recall ≥ 0.90, valid_structured_response_rate ≥ 0.99, eligible_coverage ≥ 1.00.
- `evaluation/semantic_v2/direct_capture.py`: schema v1; `prompt_version` must equal `PROMPT_VERSION_V2` ("2.0") (line 289) — the capture/runner pin the 2.1 phase must extend.
- **The preserved primary capture** was re-parsed this session through the frozen production parser composition (`parse_semantic_response_v2` + `validate_semantic_response_v2`) for all 43 cases; every response is schema-valid; the per-case states/verdicts agree with the official report (the Q3-B2 diagnosis's 11/11 cross-check is confirmed). The 13 CONTRACT_NEGATIVE cases were never rendered or sent (input-level rejections: INVALID_INPUT_SCHEMA / NON_UNCERTAIN_STATE / FOREIGN_DETERMINISTIC_CONTEXT / UNSUPPORTED_EVIDENCE) and are prompt-independent.

## 3. Exact Prompt 2.0 ambiguities (with source references)

Each ambiguity below was independently confirmed against `contract_v2.py` and against the preserved capture behavior. None is a ground-truth conflict (Section 4); together they fully explain the 11/11 abstention profile and the single false NO_MATCH.

### A. The sales-unit criticality trigger is undefined (dominant; all 11 abstentions)

`contract_v2.py` line 140 (SYSTEM_PROMPT_V2, "PHYSICAL PRODUCT vs COMMERCIAL SALES UNIT", final bullet):

> "When the candidate's sales-unit / packaging channel is UNAVAILABLE, sales-unit equivalence is UNPROVEN: if the comparison otherwise supports MATCH **and the sales unit is critical to commercial comparability**, report PACKAGING_QUANTITY (and/or BUNDLE) in missing_critical_attributes and return UNCERTAIN with UNCERTAIN_MISSING_CRITICAL_ATTRIBUTES rather than guessing packaging equivalence."

- "critical to commercial comparability" occurs **exactly once** in the system prompt and is **never defined** (grep-verified). The rest of the prompt heavily weights sales-unit safety (line 116: "absence of packaging evidence is NOT proof of equal sales unit and is never read as 'single unit'"; line 151: "A false MATCH is materially worse than UNCERTAIN"; the entire PHYSICAL PRODUCT vs COMMERCIAL SALES UNIT section, lines 136–140, built around the sales-unit distinction).
- Both readings are textually defensible: (R1) UNAVAILABLE ⇒ the unit question is open ⇒ abstain; (R2) an unpublished packaging field on a standard single-unit retail listing is not decision-critical ⇒ match when everything else aligns. The primary model applied R1 uniformly: **11/11** expected-MATCH responses list PACKAGING_QUANTITY (and in 3 cases also BUNDLE) in `missing_critical_attributes` with reason `UNCERTAIN_MISSING_CRITICAL_ATTRIBUTES`. The corpus labels assume R2.
- **Structural amplifier (independently confirmed in the frozen builders, `semantic_v2.py` lines 871–912):** the live main flow publishes no packaging field, so **every** live V2 candidate carries `sales_unit.state = UNAVAILABLE`. Under reading R1, live MATCH recall is ~0 by construction — the corpus result is not a corpus artifact.
- The Q3-B2 recommendation's proposed criterion ("critical ... or the product class is commonly multi-pack") is **rejected by this design** (Section 6): product classes here (enterprise SSD, server memory) are precisely the classes that exist in multi-pack/tray forms; a class-based factor would re-block the 11 cases in live and is not an evidence-based test. Criticality must be decided from the supplied evidence only.

### B. The rendered "Relationship requirement" field has no decision semantics (3 of 11 stated reasons)

- `render_v2_user_prompt` (line 435) renders `- Relationship requirement: {value}` under the header *"DETERMINISTIC IDENTITY CONTEXT (frozen deterministic layer output; you cannot override it)"*.
- The tokens `REVIEWED_RELATION_AUTHORITY_REQUIRED`, `NOT_REQUIRED`, `NOT_APPLICABLE`, and `Relationship requirement` occur **zero times** in `SYSTEM_PROMPT_V2` (grep-verified this session) — the model receives a constraint-looking line it has no rule for, under a header that says "you cannot override it."
- The frozen S2-A use of the requirement is **tier policy only** (`substate_relationship_requirement` docstring, lines 1503–1556; `derive_authority_tier` rule `CEILING_IDENTIFIER_RELATIONSHIP_NOT_ESTABLISHED`): it caps the derived authority tier at NEEDS_REVIEW; it does not gate the model's equivalence decision. The frozen S2-A amendment 1 even states that "AI may still return MATCH/HIGH" for NM-2 — the model output is permitted; only the automatic tier is capped.
- Observed: `V2Q-SSD-U2N-MATCH-0008` and `V2Q-SSD-SAME-ALTWORDING-0035` answered `UNCERTAIN / UNCERTAIN_IDENTIFIER_RELATION` (requirement = REVIEWED_RELATION_AUTHORITY_REQUIRED; no relation authority in input) although the identifier question is resolvable on the supplied evidence (a different retailer SKU is not proof of a different product — a rule the 2.0 prompt itself states); `V2Q-SSD-U3-MATCH-0010` answered `UNCERTAIN / UNCERTAIN_IDENTIFIER_RELATION` the same way.

### C. Near-miss / partial equivalence has no stated criterion (U3 vs U5)

- Line 126: "Near-miss identifiers (truncated, or exactly one character substituted) are NOT automatically equivalent: a one-character difference in an MPN can mean a different revision, generation, or product. Report the observed relationship and whether it establishes equivalence." — *"whether it establishes equivalence"* is undefined.
- The corpus requires four different outcomes on near-miss-shaped inputs, distinguishable only by (i) partial-published-identifier vs complete-different-part-number and (ii) the relationship authority present:
  - `V2Q-SSD-U3-MATCH-0010` (U3: candidate published MPN is a **partial** consistent prefix of the requested MPN; full attribute alignment) → expected **MATCH**;
  - `V2Q-SSD-U5NM1-MICRON-0018` and `V2Q-SSD-U5NM1-ALIAS-0022` (U5/NM-1: candidate published MPN is a **complete** different part number; customer-retrieval-only relation; the near-miss suffix is the customer-defined R/T variant whose commercial meaning is unproven; sales-unit-safety flag) → expected **UNCERTAIN** with PACKAGING_QUANTITY missing (a false MATCH is CRITICAL);
  - `V2Q-SSD-U5NM2-NOAUTH-0021` and `V2Q-SSD-U5NM2-PRODCONTEXT-0023` (U5/NM-2: complete different part number; no relationship authority / product context only) → acceptable **{NO_MATCH, UNCERTAIN}**, MATCH not defensible;
  - `V2Q-SSD-U5NM2-RELAUTH-0020` (U5/NM-2 with labeled `MANUFACTURER_RELATION_AUTHORITY` establishing the 01/02 relation) → expected **MATCH** with reason `MATCH_AUTHORIZED_IDENTIFIER_RELATION`.
- Prompt 2.0 gives the model no rule that separates these four shapes; the model answered UNCERTAIN to all of them (safe, but 0020 is a definite abstention and 0010 likewise).

### D. "Critical attribute" is undefined for `missing_critical_attributes` (over-demanding / under-crediting)

- The NEVER-MANUFACTURE rule says "if a **critical attribute** is absent from ALL supplied evidence, name it in missing_critical_attributes" — "critical" is never defined, and the 12-dimension list does not mark which are decision-critical.
- Observed over-demanding (dimensions named missing that are not decision-critical and/or unpublished on the target side itself): `V2Q-SSD-U4-COND-0017` (BRAND, GENERATION, REVISION_OR_SUFFIX — none published by the target; the decision turns on nothing they could resolve), `V2Q-DIMM-COND-0039` (FORM_FACTOR — unpublished by the target; candidate publishes MRDIMM uncontradicted), `V2Q-DIMM-U4-MATCH-0014` and `V2Q-SSD-U2E-MATCH-0006` (BUNDLE with no bundle signal anywhere), and the universal PACKAGING_QUANTITY (ambiguity A). Observed under-crediting: `V2Q-SSD-SAME-ALTWORDING-0035` listed PRODUCT_FAMILY as missing although "Solid State Drive" is published in the candidate title and "SSD" in the requested description (model-side, RC-4).

### E. Internally contradictory listings have no stated handling (the single false NO_MATCH)

- `V2Q-SSD-CONTRA-0037` (U4): the candidate title states 3.84TB while its specification text states 7.68TB. The label: "Neither value can be taken as the product's capacity on the supplied evidence, so no conflict class can be established ... asserting CAPACITY either way would be manufacturing." Expected **UNCERTAIN**.
- Prompt 2.0 says a NO_MATCH "must be grounded in the structured conflict classes" and that a hard conflict forces NO_MATCH — but it never states that an **internally contradictory** dimension is unresolvable in either direction (it is missing evidence on that dimension, not negative evidence against the target). The model picked one published side (title vs spec) and answered NO_MATCH / CAPACITY — the corpus's only FALSE_NO_MATCH (severity REVIEW, conservative direction).

### F. Raw-text packaging cues are not tied to the sales-unit rule (live absolute-rule grounding)

- The COMMERCIAL / PACKAGING EVIDENCE class (line 116) describes "the sales-unit / packaging channel" — the structured channel. The PHYSICAL vs COMMERCIAL SALES UNIT rules (lines 136–140) speak of the channel state (OBSERVED/UNAVAILABLE). Nothing states that a packaging cue published in RAW observation text (title "pack of 4", "(tray)", "2x", "bundle", "kit") is packaging evidence.
- Because the live channel is ALWAYS UNAVAILABLE (Section 2.3), the absolute rule (published incompatible packaging → NO_MATCH / HARD_CONFLICT) would in production rest on the model's implicit raw-text reading. The corpus packaging cases (`V2Q-SSD-SU-MULTI-0033`, `V2Q-SSD-SU-TRAY-0032`, `V2Q-GPU-SU-BUNDLE-0034`) all use the structured OBSERVED channel — the live shape is untested by the corpus. 2.1 must make the raw-cue reading explicit (Section 6.1), preserving the absolute rule for the live input reality.

## 4. The eleven expected-MATCH cases — review against the preserved capture

All eleven inputs were re-parsed this session through the frozen parser; the responses below are verbatim from the preserved capture (decisions/summary; full raw outputs in the capture document). "Contract permits MATCH?" is assessed against the frozen S2-A/S2-C rules (decision-level; tier ceilings are downstream and never bar the model output itself).

| # | Case (substate / signal) | Supplied evidence for the expected MATCH | Actual primary response (2.0) | Requirement (frozen table) | Contract permits MATCH? | Corpus vs frozen contract |
|---|---|---|---|---|---|---|
| 1 | `V2Q-SSD-U1-MATCH-0001` (U1 / TITLE_MPN) | Exact requested MPN in title with identity wording; 960GB M.2 22110 NVMe Gen4 PM9A3 Samsung all aligned; no conflict published. REVIEWED_SOURCE_GROUNDED (project UAT SMQ-0001). | UNCERTAIN / MEDIUM / UNCERTAIN_MISSING_CRITICAL_ATTRIBUTES; missing [PACKAGING_QUANTITY]; 7 dimensions credited; no conflicts | NOT_REQUIRED | **Yes.** No ALWAYS_HARD barrier; U1 not relation-gated; the only open question is the undefined sales-unit criticality (A). | **Consistent.** The U1 state exists for exactly this resolution; the label encodes reading R2 of the undefined trigger. |
| 2 | `V2Q-SSD-SEO-MATCH-0038` (U1 / TITLE_MPN) | Exact MPN token + aligned capacity/FF/interface; SEO tokens ("best price", "hot deal") carry no product evidence. CONTRACT_GROUNDED. | UNCERTAIN / MEDIUM / UNCERTAIN_MISSING_CRITICAL_ATTRIBUTES; missing [PACKAGING_QUANTITY]; 5 dimensions credited | NOT_REQUIRED | **Yes.** As #1. | **Consistent.** |
| 3 | `V2Q-SSD-U1-PRODCTX-0041` (U1 / TITLE_MPN) | Exact title MPN + aligned attributes + `MANUFACTURER_PRODUCT_CONTEXT` (STRONG authority profile by construction: 2 title-grounded hard facts). Label: context "is not needed for the decision." | UNCERTAIN / MEDIUM / UNCERTAIN_MISSING_CRITICAL_ATTRIBUTES; missing [PACKAGING_QUANTITY, BUNDLE]; 4 dimensions credited | NOT_REQUIRED | **Yes.** As #1; product context adds grounding only (frozen rule). | **Consistent.** Purest isolation of clause A as the sole blocker. |
| 4 | `V2Q-SSD-U2E-MATCH-0006` (U2 / SKU_EQUALS_TARGET) | Published SKU frozen-2A identical to the target MPN (identifier relation deterministically established); capacity/FF aligned; no conflict. | UNCERTAIN / MEDIUM / UNCERTAIN_MISSING_CRITICAL_ATTRIBUTES; missing [PACKAGING_QUANTITY, BUNDLE]; 4 dimensions credited | NOT_APPLICABLE | **Yes.** No identifier question exists at all; the frozen table itself is NOT_APPLICABLE. | **Consistent.** |
| 5 | `V2Q-SSD-U2N-MATCH-0008` (U2 / SKU_NOT_TARGET) | Different retailer SKU (explicitly "not by itself proof of a different product" — 2.0's own rule); 5 title dimensions aligned. | UNCERTAIN / LOW / **UNCERTAIN_IDENTIFIER_RELATION**; missing [PACKAGING_QUANTITY] | REVIEWED_RELATION_AUTHORITY_REQUIRED | **Yes.** The requirement caps the *derived tier* (NEEDS_REVIEW), not the model decision; MATCH is schema-valid and S2-A-amendment-1-permitted. | **Consistent.** The model read the unexplained requirement line as an unresolved identifier relation (B). |
| 6 | `V2Q-SSD-SAME-ALTWORDING-0035` (U2 / SKU_NOT_TARGET) | Same product in different legitimate wording ("3.84 Terabytes", "U.3 2.5in", "Enterprise NVMe Solid State Drive"); different retailer SKU; no conflict. | UNCERTAIN / LOW / **UNCERTAIN_IDENTIFIER_RELATION**; missing [BRAND, PRODUCT_FAMILY, PACKAGING_QUANTITY] — PRODUCT_FAMILY listed missing although published in the raw title (under-crediting, RC-4) | REVIEWED_RELATION_AUTHORITY_REQUIRED | **Yes.** As #5. | **Consistent.** Model-side crediting error (RC-4) + contributing B/A. |
| 7 | `V2Q-SSD-U3-MATCH-0010` (U3 / PARTIAL_BOUNDARY) | Candidate published MPN `MTFDKCC3T8TGP` is a consistent prefix (partial) of the requested `MTFDKCC3T8TGP-1BK1DABYY`; brand Micron + 7500/4TB/U.3/NVMe/SSD all aligned. REVIEWED_SOURCE_GROUNDED (recorded 4D-D catalog fixture). | UNCERTAIN / LOW / **UNCERTAIN_IDENTIFIER_RELATION**; REVISION_OR_SUFFIX reported as conflicting attribute + class; missing [PACKAGING_QUANTITY] | REVIEWED_RELATION_AUTHORITY_REQUIRED | **Yes.** A partial published identifier is not a different product number; no criterion is stated (C), and the label's catalog grounding is not carried by any frozen input channel (RC-3). | **Consistent with a nuance, not a conflict.** The expected MATCH is independently defensible on the supplied evidence (prefix consistency + full alignment) under the criterion defined in Section 6.2 (P3) and Section 7.2 (U3); the non-transmittable grounding is recorded, not relied upon. |
| 8 | `V2Q-SSD-U4-COND-0017` (U4 / NO_RELATION) | No candidate MPN (U4 by construction); all published identity attributes align; only difference is condition (Refurbished vs new) — CONDITION is PRICE_DIMENSION_ONLY. | UNCERTAIN / LOW / UNCERTAIN_MISSING_CRITICAL_ATTRIBUTES; CONDITION reported; missing [BRAND, GENERATION, REVISION_OR_SUFFIX, PACKAGING_QUANTITY] — over-demanding (D) | NOT_APPLICABLE | **Yes.** 2.0: a missing candidate MPN "is not automatically NO_MATCH ... may still be the target product on title, description, and attribute evidence." | **Consistent.** |
| 9 | `V2Q-DIMM-U4-MATCH-0014` (U4 / NO_RELATION) | Title publishes the full aligned attribute set (96GB DDR5-6400 MRDIMM server memory); no conflict. | UNCERTAIN / LOW / UNCERTAIN_MISSING_CRITICAL_ATTRIBUTES; missing [PACKAGING_QUANTITY, BUNDLE] — BUNDLE with no bundle signal (D/A) | NOT_APPLICABLE | **Yes.** As #8. | **Consistent.** |
| 10 | `V2Q-DIMM-COND-0039` (U2 / SKU_NOT_TARGET) | All identity attributes align by construction; only difference is condition (Open box vs new) — PRICE_DIMENSION_ONLY. Target description publishes no form factor; candidate publishes MRDIMM uncontradicted. | UNCERTAIN / MEDIUM / UNCERTAIN_MISSING_CRITICAL_ATTRIBUTES; CONDITION reported; missing [PACKAGING_QUANTITY, FORM_FACTOR] | REVIEWED_RELATION_AUTHORITY_REQUIRED (not the stated blocker) | **Yes.** As #5. | **Consistent.** |
| 11 | `V2Q-SSD-U5NM2-RELAUTH-0020` (U5 / NEAR_MISS_SUBSTITUTION) | Labeled `MANUFACTURER_RELATION_AUTHORITY` establishes the 01/02 relation by construction; all attributes aligned; the bounded vocabulary includes `MATCH_AUTHORIZED_IDENTIFIER_RELATION` for exactly this shape. | UNCERTAIN / MEDIUM / UNCERTAIN_MISSING_CRITICAL_ATTRIBUTES; the near-miss correctly credited as "relation authority present, not treated as material conflict"; missing [PACKAGING_QUANTITY] — the sales-unit clause is the *only* stated blocker (cleanest proof of A) | REVIEWED_RELATION_AUTHORITY_REQUIRED — **satisfied** by the labeled authority | **Yes.** Relation ESTABLISHED, so neither the requirement ceiling nor the NM-2 ceiling fires; S2-A amendment 1 explicitly permits the MATCH/HIGH output. | **Consistent.** |

**Findings (task item 7):**

- **No genuine frozen-contract conflict exists in any of the 11 labels.** Every expected decision is schema-satisfiable under the frozen V2 output contract; no label contradicts an explicit frozen clause; all 11 identity contexts match the frozen `SUBSTATE_RELATIONSHIP_REQUIREMENTS` table exactly. **No STOP condition is triggered.**
- The eleven labels each encode **one defensible reading (R2)** of prompt 2.0's undefined trigger(s) A–D; the primary model produced the other defensible reading (R1) plus the unexplained-requirement reading (B). This is a property of prompt 2.0 as frozen, not of the ground truth.
- The only label whose independent grounding is **not transmittable** through the frozen input is #7 (`V2Q-SSD-U3-MATCH-0010`, RC-3: the recorded-catalog prefix fact; the production 4D-D context would be a CUSTOMER_RETRIEVAL_ALIAS with zero identity authority, and this corpus case carries no reviewed target context). The expected MATCH nevertheless stands on the supplied evidence alone under the criterion defined in Section 7.2 (U3 consistent-partial semantics), so the corpus remains consistent with the frozen contract. This is recorded as a finding, and per the evaluation-truth rule the label is **not** altered and no alteration is recommended.
- Per the Q3-B2 classification, independently confirmed: 10 × FROZEN_PROMPT_AMBIGUITY (primary cause) + 1 × MODEL_EXCESSIVE_ABSTENTION (primary cause, #6, with contributing ambiguity); zero cases classified CORPUS_CONTRACT_CONFLICT / EVALUATION_SCORING_DEFECT / INDETERMINATE.


## 5. Missing evidence vs negative evidence (the core semantic distinction)

The frozen contract, the corpus labels, and the 2.1 design all rest on one distinction that prompt 2.0 never states:

**Missing evidence** — a channel is UNAVAILABLE, a dimension is unpublished on one or both sides, or an identifier relation is unproven. Missing evidence **establishes nothing in either direction**: it is not proof of equivalence and not proof of difference. Consequences:

1. Missing evidence **never licenses NO_MATCH**. A NO_MATCH is always grounded in *published* negative evidence (frozen `REASON_CODE_RULES`: every NO_MATCH reason requires a non-empty structured conflict set; "NO_MATCH is always conflict-grounded").
2. Missing evidence licenses **UNCERTAIN only when decision-critical** — i.e., only when the equivalence decision actually turns on the missing dimension (defined operationally in Section 6.2 cells P3/P4 and Section 7.4). A missing dimension that the decision does not turn on must not be named in `missing_critical_attributes` and must not force abstention. This is what fixes the 11 universal PACKAGING_QUANTITY abstentions (ambiguity A) and the over-demanding in #8/#9/#10 (ambiguity D).
3. Missing evidence is never read as a value: "do not infer a single unit" (frozen, line 116/244) is preserved verbatim. Unproven is not equal, and not different.

**Negative evidence** — a *published* observation that establishes the candidate is a different product or is not pricing-comparable as the same sales unit: a published hard-identity dimension contradicting the target (different capacity, generation, interface, form factor, family, role); a published accessory/kit product role instead of the requested product; published incompatible packaging (a pack of N, tray/factory pack, or bundle against a single-unit target — the absolute rule); a complete different published part number whose relation is not established (U5). Negative evidence licenses **NO_MATCH** (hard classes) or abstention (reviewable classes where inspection could resolve, e.g. BRAND).

**Internally contradictory evidence** — the supplied evidence conflicts with *itself* on a dimension (title 3.84TB vs spec 7.68TB). This is **missing evidence for that dimension in both directions**, not negative evidence against the target: no published side may be adopted as the product's value, so the dimension cannot be established as a conflict and cannot be established as alignment. Consequence: UNCERTAIN, naming the dimension (ambiguity E; the #0037 fix). This is distinct from a published candidate value contradicting a published target value, which **is** negative evidence.

**Observed 2.0 errors, mapped:**

| Error class | Cases | Conflation |
| --- | --- | --- |
| Universal sales-unit abstention (11/11) | all 11 expected-MATCH | missing evidence (UNAVAILABLE channel) treated as decision-blocking (A) |
| Requirement-line abstention (3 stated) | #5, #6, #7 | a downstream tier-policy field treated as a model-decision constraint (B) |
| Over-demanding dimensions | #8 (BRAND/GENERATION/REVISION_OR_SUFFIX), #10 (FORM_FACTOR), #9/#4 (BUNDLE) | "unpublished" treated as "critical" (D) |
| Under-crediting | #6 (PRODUCT_FAMILY) | published raw evidence treated as absent (D, model-side) |
| False NO_MATCH | `V2Q-SSD-CONTRA-0037` | internal contradiction treated as negative evidence against the target (E) |

## 6. The sales-unit rule: exactly when missing packaging must block MATCH

### 6.1 The absolute rule (preserved and strengthened)

> **Published incompatible packaging is a hard conflict.** When the candidate's packaging evidence — in the structured sales-unit channel **or** published in raw observation text (listing title, specification text) — is incompatible with the target's commercial unit, the decision is **NO_MATCH** with the structured conflict classes PACKAGING_QUANTITY and/or BUNDLE (ACCESSORY_RELATION / PRODUCT_ROLE where the published product is an accessory rather than the requested product). This is the frozen S2-A ALWAYS_HARD semantics, enforced at the output boundary (MATCH/UNCERTAIN may never carry an ALWAYS_HARD class) and at the authority tier (HARD_CONFLICT supersession). No semantic output, provenance, or confidence can override it.

Strengthening vs 2.0: 2.0 states the rule against the structured channel; 2.1 extends its evidence base to raw observation text (ambiguity F) — required because the live channel is ALWAYS UNAVAILABLE (Section 2.3). No weakening: every 2.0 trigger remains a trigger; the raw-cue branch only adds triggers of the same kind.

**Target's commercial unit:** the input carries no target-side packaging channel; the target's commercial unit is **the single unit of the requested part**, unless the supplied target-side evidence (the requested description's raw text, or a reviewed target context) explicitly establishes a different form (e.g., "pack of 4", "tray", "bundle"). This default is a contract-level semantic choice (approval question Q1) and matches every corpus case (the single-unit targets in 0032/0033/0034 state it explicitly; the 11 MATCH targets are standard single-part requests).

**Ambiguous cues:** where a raw cue could be packaging or something else and its contents are unclear (e.g., "kit" without contents), the cue is *unproven* packaging evidence, not established conflict: the safe output is UNCERTAIN naming PACKAGING_QUANTITY / BUNDLE (never MATCH, never NO_MATCH on the cue alone). Clear cues ("pack of 4", "tray of 20", "bundle: X + Y") are established conflict: NO_MATCH.

### 6.2 Decision matrix — packaging state × evidence

| Cell | Packaging evidence state | Trigger conditions | Decision | Reason code | Conflict classes | Downstream tier effect (frozen S2-A, unchanged) |
| --- | --- | --- | --- | --- | --- | --- |
| **P1 — known / equal** | OBSERVED (structured or raw cue) | Candidate's published sales unit equals the target's commercial unit (both single-unit; or target-side supplied evidence establishes the same multi-unit form) | No packaging barrier; decided by the identifier/product rules (Section 7) | per outcome | none (packaging) | none |
| **P2 — known / different** | OBSERVED (structured or raw cue) | Candidate's published sales unit is incompatible with the target's commercial unit (single-unit target vs pack of N / tray / factory pack / bundle; accessory role instead of the product) | **NO_MATCH (absolute rule)** | NO_MATCH_PACKAGING / NO_MATCH_BUNDLE / NO_MATCH_ACCESSORY (role) | PACKAGING_QUANTITY and/or BUNDLE; ACCESSORY_RELATION and/or PRODUCT_ROLE for accessory role | HARD_CONFLICT supersession; not confirmable by human; parser forbids MATCH/UNCERTAIN carrying these classes |
| **P3 — unavailable, non-critical** | UNAVAILABLE; **no** packaging cue anywhere in the supplied evidence (structured or raw) | The identifier relation is established per Section 7 (exact identifier, SKU-equal, consistent partial, no-identifier-with-full-alignment, or labeled manufacturer relation authority), and no other decision-critical dimension is missing | **MATCH is not blocked by the sales unit.** The unit remains UNPROVEN (never read as "single unit"); PACKAGING_QUANTITY / BUNDLE must NOT be named in missing_critical_attributes solely because the channel is UNAVAILABLE | MATCH_* | none | Per the 27-entry matrix + ceilings (evidence quality, requirement, NM-2) — the sales unit adds no ceiling |
| **P4 — unavailable, critical (entangled)** | UNAVAILABLE; no raw cue | The candidate publishes a **complete part number different from the requested one** (U5_NEAR_MISS_MPN — truncation or one-character substitution) and the relation is **not established** (no MANUFACTURER_RELATION_AUTHORITY; a customer-retrieval relation or no relation at all), and everything else supplied aligns: the identifier difference itself is what may carry the sales-unit / packaging / revision question (the Micron R/T shape) | **UNCERTAIN — MATCH blocked.** The commercial question cannot be separated from the identifier question; guessing equivalence is forbidden | UNCERTAIN_MISSING_CRITICAL_ATTRIBUTES (or UNCERTAIN_IDENTIFIER_RELATION) | none (the near-miss difference may be reported as a REVISION_OR_SUFFIX conflicting attribute, reviewable; never an ALWAYS_HARD class) | NEEDS_REVIEW (UNCERTAIN rows) — the CRITICAL sales-unit-safety cases (0018/0022) must never flip to MATCH |
| **P5 — internally contradictory** | Structured and/or raw evidence contradicts **itself** on the packaging (or any identity) dimension | e.g., title "pack of 4" vs spec "single unit"; title 3.84TB vs spec 7.68TB | **UNCERTAIN** — the dimension is unresolvable in either direction; not a conflict against the target; never NO_MATCH on the contradiction alone | UNCERTAIN_MISSING_CRITICAL_ATTRIBUTES | none | NEEDS_REVIEW / EXCLUDED per UNCERTAIN rows |
| **P6 — ambiguous cue** | UNAVAILABLE structured; raw cue present but unclear (unclear contents / unclear whether packaging or accessory) | the cue could change pricing comparability but its meaning is not established | **UNCERTAIN** naming PACKAGING_QUANTITY and/or BUNDLE (or ACCESSORY_RELATION where the product role is the unclear part) | UNCERTAIN_MISSING_CRITICAL_ATTRIBUTES | none | as P5 |

**The blocking answer (task item 3), in one sentence:** missing sales-unit information **must** block MATCH only in cell P4 — when the unresolved identifier difference is itself the potential carrier of the sales-unit/packaging/revision question (complete different part number, no manufacturer relationship authority); in every other cell it may remain UNPROVEN without proving a contradiction, and in cell P2 the *published* incompatibility is negative evidence that forces NO_MATCH regardless of what is missing elsewhere.

### 6.3 Why this preserves every frozen protection

- **Absolute rule (task item 4):** P2 is the 2.0 rule with an enlarged (not reduced) evidence base; the parser coherence rule and the HARD_CONFLICT supersession are untouched.
- **NM-2 ceiling (task item 5):** untouched — it is tier policy in `derive_authority_tier`; 2.1 does not reference it as a decision rule. Note the deliberate distinction: the NM-2 *ceiling* (authority tier, S2-A) applies even when `MANUFACTURER_RELATION_AUTHORITY` is present **if** the near-miss substitution is active and no relationship authority clears it — with authority present the ceiling does not fire, and the model **may** MATCH (0020). 2.1's decision rule and S2-A's tier rule stay on their separate axes.
- **Customer retrieval zero authority (task item 5):** P4 treats a customer-retrieval relation as *not establishing* the identifier relation (and as making the family-variant question concrete); it confers no equivalence, no authority, and is never described as manufacturer-stated. The harness's input-aware alias cross-check (gate 6) is untouched.
- **Evidence-quality ceilings (task item 5):** untouched — dimension A is derived only from the authority-side profile (no model-claim source); the live path stays at most LIMITED, so live MATCH is at most NEEDS_REVIEW regardless of prompt wording.
- **Corpus safety cases:** P2 covers 0032/0033/0034 (OBSERVED different), P4 covers 0018/0022 (UNAVAILABLE entangled), P5 covers 0037 (internal contradiction), the accessory/compatibility NO_MATCHs (0031/0002/0007/0042) are product-role negative evidence under the preserved 2.0 accessory rule, and 0021/0023 (U5 unresolved, acceptable {NO_MATCH, UNCERTAIN}) fall under P4's "not MATCH" bar with the NO_MATCH/UNCERTAIN choice left to the model's reading of whether the substitution is published-different or unproven.

## 7. Identifier decision semantics and relationship-authority semantics

### 7.1 The four-way separation (task item 6)

| Axis | Question | Owner | Input | Constrains | Touched by 2.1 |
| --- | --- | --- | --- | --- | --- |
| **Identity decision** | Is the candidate the same commercially comparable product, on the supplied evidence? | The model (advisory; never sole authority for exact identity) | The five input sections | The recorded decision + structured conflicts; downstream tier via the matrix | **Yes — this is the only axis 2.1 redesigns** (the decision criterion), and it explains the requirement line to the model |
| **Relationship authority** (dimension B) | Does a reviewed authoritative source establish the identifier relationship? | Frozen S2-A (`derive_relationship_authority` + `SUBSTATE_RELATIONSHIP_REQUIREMENTS`) | Deterministic state + context provenance only (customer retrieval never qualifies) | The automatic tier: REVIEWED_RELATION_AUTHORITY_REQUIRED entries cap AI_ASSISTED_COMPARABLE at NEEDS_REVIEW when dimension B is not ESTABLISHED | **No** — S2-A byte-untouched; 2.1 only tells the model the rendered line is this axis, not its own input |
| **ProductEvidenceQuality** (dimension A) | How strongly is the candidate's product evidence grounded? | Frozen S2-A (`derive_product_evidence_quality`) | Authority-side profile only (no model-claim source member exists) | The tier matrix row (MATCH+HIGH needs STRONG for AI_ASSISTED_COMPARABLE) | **No** — the model observes section E and may never create/upgrade it (preserved rule) |
| **Pricing eligibility** | May this candidate enter pricing output? | Frozen S2-A tiers + 4A aggregation + the qualification marker | The derived tier (`PRICING_ELIGIBLE_TIERS` = MACHINE_VERIFIED + AI_ASSISTED_COMPARABLE + HUMAN_CONFIRMED) and `V2_AUTHORITY_QUALIFIED` (False) | Which listings may be priced / compared in output | **No** — V2 is persist-only and unqualified; 2.1 changes no pricing behavior in any scenario |

The 2.0 failure mode was a **merge of axis 1 and axis 2**: the model treated the axis-2 requirement line as an axis-1 blocker (ambiguity B). 2.1's explicit separation statement (Section 8.2, "READING THE DETERMINISTIC IDENTITY CONTEXT") is the correction; it changes no S2-A data.

### 7.2 Identifier relationship decision semantics (new prompt section, per frozen substate)

The deterministic layer has already classified the identifier shape (state/substate/signals are established facts — the model does not re-litigate them). The prompt states, per substate, what the shape means for the **equivalence decision**:

| Substate / signal | Identifier fact (established) | Decision semantics in 2.1 |
| --- | --- | --- |
| U1_TITLE_MPN | Exact requested MPN token in the title | Identifier **established** unless the wording context is compatibility/reference/SEO (preserved 2.0 rule: inspect the wording). Established + aligned published hard dimensions + no blocking sales unit → MATCH. |
| U2_SKU_ONLY / SKU_EQUALS_TARGET | Published SKU frozen-2A identical to the target | Identifier **established** (the deterministic comparator is the authority). → MATCH on the product rules. |
| U2_SKU_ONLY / SKU_NOT_TARGET | Published SKU different from the target | A different SKU is **not proof of a different product** (preserved 2.0 rule). The identifier question is decided on the product evidence: all target-published hard identity dimensions aligned or uncontradicted on the candidate → MATCH is available. (The requirement line for this shape is tier policy, Section 7.3.) |
| U3_PARTIAL_BOUNDARY | Candidate published MPN is a **partial** (consistent truncation/prefix) of the requested MPN | The candidate published a **partial form of the requested identifier, not a different product number**; a consistent partial is **not** a conflicting revision. Decide on the product evidence: full alignment of all target-published hard dimensions → MATCH; decision-critical hard dimension unpublished on the candidate → UNCERTAIN naming it; published contradiction → NO_MATCH. Confidence guidance: a partial identifier supports at most MEDIUM. |
| U4_NO_MPN | No usable candidate identifier | No identifier question exists (frozen: the requirement is NOT_APPLICABLE — there is nothing to establish). Decide on the product evidence: full alignment of all target-published hard dimensions → MATCH; a decision-critical hard dimension published on the target and absent from the candidate → UNCERTAIN naming it; contradiction → NO_MATCH. (Preserved 2.0 rule: a missing candidate MPN is not automatically NO_MATCH.) |
| U5_NEAR_MISS_MPN (NM-1 truncation / NM-2 substitution) | Candidate published MPN is a **complete** part number different from the requested one (bounded near-miss shape) | A different complete part number is **never automatically equivalent**. Equivalence is established **only** by `MANUFACTURER_RELATION_AUTHORITY` explicitly establishing the relationship (or manufacturer-stated evidence resolving the difference as not material). A customer-retrieval relation and a manufacturer product context **never** establish it. Established → MATCH available (reason `MATCH_AUTHORIZED_IDENTIFIER_RELATION`; do not report the resolved near-miss difference as a conflicting revision). Not established → **not MATCH**: the pair is either NO_MATCH (where the model judges the published difference establishes a different product) or UNCERTAIN (where it does not); in the aligned-attributes shape, the sales unit is critical per cell P4 (the difference may itself carry the sales-unit/packaging/revision question), so the safe definite output is UNCERTAIN naming PACKAGING_QUANTITY and/or the identifier gap. |

### 7.3 The "Relationship requirement" line (ambiguity B fix)

The 2.1 prompt states, and the 2.1 user template annotates the rendered line:

> The "Relationship requirement" line in the DETERMINISTIC IDENTITY CONTEXT is **downstream authority-tier policy**: it records whether the candidate's derived pricing-authority tier requires a reviewed relationship source to be ESTABLISHED. It is **not** your decision input. It neither blocks nor permits a MATCH: a candidate for which the requirement is REVIEWED_RELATION_AUTHORITY_REQUIRED can be a MATCH on the supplied evidence (the requirement then caps the derived tier, which you cannot see), and a candidate for which it is NOT_APPLICABLE/NOT_REQUIRED can be a NO_MATCH or UNCERTAIN for evidence reasons. Decide commercial equivalence solely per the IDENTIFIER RELATIONSHIP RULES, the COMMERCIAL SALES-UNIT RULES, and the DECISION RULES.

This is a faithful restatement of the frozen S2-A semantics (`substate_relationship_requirement` docstring: the tier "is capped at NEEDS_REVIEW ... when — and only when — ... the requirement is REVIEWED_RELATION_AUTHORITY_REQUIRED and dimension B is not ESTABLISHED"; S2-A amendment 1: "AI may still return MATCH/HIGH; a human may confirm later; it simply cannot auto-price").

### 7.4 Decision-critical missing attributes (ambiguity D fix)

2.1 defines "critical" operationally: a dimension belongs in `missing_critical_attributes` **only if** all three hold —

1. it is a hard identity dimension (PRODUCT_FAMILY, GENERATION, CAPACITY, INTERFACE, FORM_FACTOR, PRODUCT_ROLE, ACCESSORY_RELATION, PACKAGING_QUANTITY, BUNDLE) or the identifier relationship itself (U5 unresolved);
2. it is **not established and not contradicted** by any supplied evidence on either side — in particular, a value published on the candidate side and not contradicted is *not* missing, and a value published on neither side is not decision-critical unless the decision turns on it;
3. the equivalence decision **depends on it**: no established identifier relationship exists (per Section 7.2) and not all target-published hard identity dimensions are aligned or uncontradicted on the candidate side.

And the credit-all-first rule: "Credit ALL supplied evidence on both sides (structured and raw observation text) before naming anything missing." This removes the #8/#9/#10 over-demanding, the #6 under-crediting pattern, and (with cell P3) the universal PACKAGING_QUANTITY abstention, while keeping the genuine thin cases correct (0015 "NVMe SSD" → UNCERTAIN naming capacity/FF/family; 0012 → UNCERTAIN naming CAPACITY/FORM_FACTOR; 0009 → UNCERTAIN naming INTERFACE — all still within expected/acceptable sets).

### 7.5 Preserved verbatim (no semantic change)

- Customer retrieval = retrieval hint only, zero identity authority, never manufacturer equivalence (and the rendered provenance labels, unchanged).
- MANUFACTURER_PRODUCT_CONTEXT = grounding only, does not establish the identifier relationship.
- "A false MATCH is materially worse than UNCERTAIN" (kept; it now coexists with the defined non-criticality of the UNAVAILABLE sales unit — the asymmetry is about *guessing*, not about *abstaining on every open question*).
- Condition = price dimension only, never identity (kept; may be reported as a CONDITION conflicting attribute on a MATCH; caps nothing downstream — preserved).
- The six-key response schema, the 17 reason codes, the 12 dimensions, the conflict-class vocabulary (kept byte-identical; the output contract is version 1 under 2.1).
- No chain-of-thought surface (kept).
- The reason-code tie (new explicit statement, matching the existing harness cross-check): `MATCH_AUTHORIZED_IDENTIFIER_RELATION` may be used **only when** the CONTEXT PROVENANCE section explicitly lists `MANUFACTURER_RELATION_AUTHORITY`.

## 8. Proposed Prompt 2.1 (versioned draft)

### 8.1 Versioning, binding, and artifacts (implementation-phase constraints, design-level)

- **New version constant** `SEMANTIC_PROMPT_VERSION_V2_1 = "2.1"` (a new module surface; the frozen `SEMANTIC_PROMPT_VERSION_V2 = "2.0"` and `SYSTEM_PROMPT_V2` remain byte-untouched — the 2.0 digest `c0cc98bd...` must keep reproducing as a regression pin). The 2.1 builder (`build_semantic_prompt_v2_1`) constructs only 2.1 prompts; a 2.0 prompt for any case remains deterministically reconstructable from the recorded input (frozen property, preserved).
- **New contract binding** `("V2", "2.1", 1, 1, "SEMANTIC_AUTHORITY_V2_S2A_FU2")`: only the prompt-version axis moves. Semantic contract V2, input schema v1, output schema v1, and the authority contract (`SEMANTIC_AUTHORITY_V2_S2A_FU2`) are unchanged. This is exactly the "V2-lineage binding (e.g. prompt 2.1)" the frozen S2-B/S2-C design anticipated: it must be **registered as its own adapter binding** (new `SemanticDecisionRecordV2_1` family or an explicitly separate supported binding — implementation decision), with replay refusing cross-version reinterpretation in both directions (2.0 records under 2.1, 2.1 records under 2.0). No V2 production record exists anywhere, so no live reinterpretation risk.
- **Corpus re-seal (labels unchanged):** a new corpus document `corpus_2_1.json` at version **1.1.0**, `semantic_contract_binding` = the 2.1 binding, **all 56 per-case `case_digest`s byte-identical to 1.0.0** (mechanical proof that every label, expected decision, conflict class, missing dimension, flag, and input payload is unchanged), `label_revisions` empty (a binding re-point is not a label change; no A/B/C/D class is triggered), and a new `corpus_digest` (the binding is part of the corpus-level state). Both corpus versions remain loadable: 1.0.0 stays bound to the 2.0 production binding for historical 2.0 evidence; 1.1.0 serves 2.1 requalification. The corpus loader's binding gate (`corpus.py:1173–1180`) accepts the 2.1 production binding for 1.1.0.
- **Harness/capture pins:** the direct-capture `prompt_version` pin (`direct_capture.py:289`), the runner's frozen-builder reuse, the manifest's system-prompt digest field, and the report's contract section are extended to the 2.1 binding in the implementation phase. The eight gates keep their exact names/details (gate 6 pins the 2.1 production binding in the 2.1 context). The DRAFT policy artifact is **byte-unchanged** (0.99 / 0.90 / 0.99 / 1.00, `approved: false`); 2.1 requalification decisions remain POLICY_PENDING until the policy is explicitly approved (a Q3-C matter, unchanged).
- **What this means for authority:** 2.1 is a *contract version under qualification*. `V2_AUTHORITY_QUALIFIED` stays False; no 2.1 prompt may be used in production execution, no 2.1 record may carry pricing authority, and no 2.1 capture may grant any tier — identical to the 2.0 posture during Q3.

### 8.2 SYSTEM PROMPT 2.1 — full draft text

The complete proposed system prompt follows. Sections marked **[2.0 unchanged]** carry over verbatim (byte-identical substring pins are part of the test plan). New/changed sections are marked **[2.1 NEW]** or **[2.1 CHANGED]**.

```text
You are a product commercial-equivalence evaluation assistant.

TASK
Your task is to determine the COMMERCIAL SEMANTIC EQUIVALENCE of a TARGET product and a CANDIDATE listing: does the candidate listing represent the same commercially comparable product as the target, and with what confidence?

You are given a structured input with five sections: TARGET, CANDIDATE LISTING, DETERMINISTIC IDENTITY CONTEXT, CONTEXT PROVENANCE, and PRODUCT EVIDENCE. Use ONLY the evidence supplied in those sections. Do not rely on unstated specifications, catalog knowledge, or outside product knowledge. Every value in the input is labeled with its evidence class (STRUCTURED FACT with a source label, RAW OBSERVATION TEXT, COMMERCIAL / PACKAGING EVIDENCE, REVIEWED TARGET CONTEXT, or AUTHORITY-SIDE PRODUCT EVIDENCE); read every value in its class.

WHAT YOU ARE NOT ASKED TO DO   [2.0 unchanged]
- Do not estimate, infer, or compare prices. Price and package observations are supplied as commercial context only and are NEVER identity evidence.
- Do not decide or override deterministic identity status. The deterministic layer has already established the DETERMINISTIC IDENTITY CONTEXT; you cannot make a candidate "machine verified", and you cannot override a deterministic hard conflict.
- Do not infer manufacturer authority. Do not turn customer retrieval relations, aliases, or compatibility/SEO wording into manufacturer equivalence or identity authority.
- Do not decide final market aggregation or any pricing outcome.

WHAT YOU SHOULD DETERMINE
- Whether the candidate represents the same commercially comparable product as the target (MATCH), is a different product (NO_MATCH), or whether the supplied evidence is insufficient (UNCERTAIN).
- Which bounded attributes match, which conflict, and which critical attributes are missing.
- Whether material conflicts exist, classified using the structured conflict classes below (never free text).
- Whether uncertainty remains, and what would resolve it.
- Whether the supplied identifier evidence establishes that the candidate is the requested product (IDENTIFIER RELATIONSHIP RULES).

EVIDENCE CLASSES (how to read the input)
- STRUCTURED FACT: [2.0 unchanged]
- RAW OBSERVATION TEXT: [2.0 unchanged]
- COMMERCIAL / PACKAGING EVIDENCE: price, currency, availability, seller, condition, offer, and the sales-unit / packaging channel. Commercial evidence is NEVER identity evidence. The sales-unit channel is EXPLICIT: "UNAVAILABLE" means the listing published no packaging / sales-unit field. Absence of packaging evidence is NOT proof of equal sales unit and is never read as "single unit"; do not infer a packaging value from price or from any other commercial fact. [2.1 NEW] A packaging cue published in raw observation text (listing title or specification text) — for example "pack of N", "N x", "tray", "factory pack", "multi-pack", "bundle" — is ALSO packaging evidence: read it under the COMMERCIAL SALES-UNIT RULES exactly as if it were published in the structured channel.
- REVIEWED TARGET CONTEXT: [2.0 unchanged]
- AUTHORITY-SIDE PRODUCT EVIDENCE: [2.0 unchanged]
- NEVER MANUFACTURE A MISSING FACT: [2.0 unchanged]

IDENTIFIER RELATIONSHIP RULES   [2.1 NEW; replaces and extends "IDENTIFIER EVIDENCE RULES"]
- The DETERMINISTIC IDENTITY CONTEXT has already established the identifier shape (state, substate, signals, normalized keys). Do not re-litigate the shape; apply the rule for the substate it records.
- Exact MPN equality (published MPN field, or the exact requested MPN token in the title with identity wording) is strong evidence and ESTABLISHES the identifier relationship, but it is not the only evidence of commercial equivalence: the product evidence still decides the outcome.
- A missing candidate MPN is not automatically NO_MATCH: a listing that publishes no usable MPN may still be the target product on title, description, and attribute evidence. No identifier question exists for such a listing; decide on the product evidence.
- A target MPN appearing in the listing title may be product identity OR compatibility / reference / SEO wording (for example "compatible with", "replacement for", "drop-in"). Inspect the wording context before treating title MPN text as identity evidence.
- SKU evidence must be interpreted carefully: a SKU equal to the target ESTABLISHES the identifier relationship (the deterministic layer records it); a different SKU is not by itself proof of a different product — decide on the product evidence.
- A published candidate MPN that is a consistent truncation / prefix of the requested MPN (substate U3_PARTIAL_BOUNDARY) is a PARTIAL FORM of the requested identifier, not a different product number and not a conflicting revision. Decide commercial equivalence on the product evidence: a decision-critical hard identity dimension that is published on the target and absent from the candidate supports UNCERTAIN naming that dimension; a published contradiction supports NO_MATCH.
- A published candidate MPN that is a COMPLETE part number different from the requested one in a bounded near-miss shape (substate U5_NEAR_MISS_MPN: truncation, or exactly one character substituted) is a DIFFERENT PUBLISHED PART NUMBER and is NOT automatically equivalent. Equivalence for such a pair is established ONLY by MANUFACTURER_RELATION_AUTHORITY explicitly establishing the relationship (or manufacturer-stated evidence resolving the difference as not material). A customer-retrieval relation and a manufacturer product context never establish it. When the relationship is not established, the pair is not a MATCH on identifier evidence alone; decide NO_MATCH or UNCERTAIN on whether the published difference establishes a different product, and apply the COMMERCIAL SALES-UNIT RULES (the difference itself may carry the sales-unit / packaging / revision question).

READING THE DETERMINISTIC IDENTITY CONTEXT   [2.1 NEW]
- The identifier facts in this section are established by the frozen deterministic layer; do not re-litigate them.
- The "Relationship requirement" line is DOWNSTREAM AUTHORITY-TIER POLICY: it records whether the candidate's derived pricing-authority tier requires a reviewed relationship source to be established. It is NOT your decision input. It neither blocks nor permits a MATCH: a MATCH on the supplied evidence is possible even where the requirement is REVIEWED_RELATION_AUTHORITY_REQUIRED (the requirement then caps a derived tier you cannot see), and a NO_MATCH or UNCERTAIN is required where the evidence does not support equivalence even though the requirement is NOT_REQUIRED or NOT_APPLICABLE. Decide solely per the IDENTIFIER RELATIONSHIP RULES, the COMMERCIAL SALES-UNIT RULES, the MISSING-CRITICAL ATTRIBUTES RULES, and the DECISION RULES.

CONTEXT PROVENANCE RULES   [2.1 CHANGED: all 2.0 text retained verbatim; the first two bullets each gain one appended sentence (customer-retrieval never establishes a relation between two different published part numbers; a labeled-authority-resolved near-miss is not reported as a conflicting revision)]
- CUSTOMER_RETRIEVAL_RELATION, when present, is a RETRIEVAL HINT ONLY: it explains how the candidate was found. It is NOT manufacturer equivalence, it is NOT identity authority, and it confers no product authority. Use it as a retrieval hint only. Where the only relationship between two different published part numbers is a customer-retrieval relation, the identifier relationship is NOT established.
- MANUFACTURER_RELATION_AUTHORITY, when explicitly present, is stronger evidence: a reviewed authoritative source explicitly establishes the relevant identifier relationship. Use it as labeled manufacturer relationship authority, not as a guess. When it establishes a near-miss relationship, do not report that resolved difference as a conflicting revision.
- MANUFACTURER_PRODUCT_CONTEXT, when present, is reviewed product grounding about the base product; it strengthens product evidence but does not establish the identifier relationship.

PRODUCT EVIDENCE RULES   [2.0 unchanged]

COMMERCIAL SALES-UNIT RULES   [2.1 CHANGED; replaces "PHYSICAL PRODUCT vs COMMERCIAL SALES UNIT"]
- Distinguish PHYSICAL-PRODUCT equivalence from COMMERCIAL SALES-UNIT / PACKAGING equivalence. The same underlying physical product sold with a different pack quantity, sales unit, bundle, or as an accessory (tray, caddy, enclosure) is NOT pricing-comparable as the same sales unit.
- The target's commercial unit is the single unit of the requested part, unless the supplied target-side evidence (the requested description, or a reviewed target context) explicitly establishes a different form.
- ABSOLUTE RULE — PUBLISHED INCOMPATIBLE PACKAGING IS A HARD CONFLICT: if the candidate's packaging evidence — in the structured sales-unit channel or published in raw observation text — is incompatible with the target's commercial unit (for example: target a single unit, candidate a pack of 4, a tray of 20, or a bundle), the decision is NO_MATCH with the PACKAGING_QUANTITY and/or BUNDLE conflict class. "Same physical drive" never implies "same comparable price unit". No confidence, provenance, or attribute alignment overrides this rule.
- An accessory (tray, caddy, enclosure, heatsink, adapter, cable, standalone kit) instead of the actual requested product is a material ACCESSORY_RELATION / PRODUCT_ROLE conflict (NO_MATCH). A raw-text cue that is unclear whether it denotes packaging of the requested product or an accessory supports UNCERTAIN naming the dimension, never MATCH and never NO_MATCH on the cue alone.
- MISSING SALES UNIT, NON-CRITICAL: when the sales-unit / packaging channel is UNAVAILABLE and no packaging cue appears anywhere in the supplied evidence, sales-unit equivalence is UNPROVEN but is NOT critical to commercial comparability. Do not report PACKAGING_QUANTITY or BUNDLE in missing_critical_attributes solely because the channel is UNAVAILABLE; do not read UNAVAILABLE as "single unit". The sales-unit gap does not block a MATCH that the identifier relationship and product evidence otherwise support.
- MISSING SALES UNIT, CRITICAL (MATCH BLOCKED): the missing sales unit IS critical — and must block MATCH with UNCERTAIN, reporting PACKAGING_QUANTITY and/or BUNDLE in missing_critical_attributes — when the identifier relationship is not established and the difference between the published identifiers is itself what may carry the sales-unit / packaging / revision question: a candidate that publishes a COMPLETE part number different from the requested one (substate U5_NEAR_MISS_MPN) with no manufacturer relationship authority (a customer-retrieval relation only, or no relationship at all), where the near-miss difference (a missing suffix, a substituted character) could denote a packaging, sales-unit, or revision variant and no manufacturer-stated evidence resolves it. In that case the commercial question cannot be separated from the identifier question, and guessing packaging or product equivalence is forbidden.

CONFLICT CLASSES (structured; use exactly these values)   [2.0 unchanged]
- ALWAYS HARD (different product / pricing-incomparable identity): MPN_IDENTITY, PRODUCT_FAMILY, GENERATION, CAPACITY, INTERFACE, FORM_FACTOR, PRODUCT_ROLE, ACCESSORY_RELATION, PACKAGING_QUANTITY, BUNDLE.
- REVIEWABLE (material but resolvable by inspection): REVISION_OR_SUFFIX, BRAND, OTHER_MATERIAL_CONFLICT.
- PRICE DIMENSION ONLY (never an identity conflict): CONDITION.
A NO_MATCH decision must be grounded in the structured conflict classes. If the supplied evidence shows a hard conflict, the decision is NO_MATCH with the corresponding conflict class; your reason code must never contradict your structured conflict set.

MISSING-CRITICAL ATTRIBUTES RULES   [2.1 NEW]
- Name a dimension in missing_critical_attributes ONLY when it is decision-critical: (1) it is a hard identity dimension (PRODUCT_FAMILY, GENERATION, CAPACITY, INTERFACE, FORM_FACTOR, PRODUCT_ROLE, ACCESSORY_RELATION, PACKAGING_QUANTITY, BUNDLE) or the identifier relationship itself; (2) it is not established and not contradicted by any supplied evidence on either side — a value published on the candidate side and not contradicted is NOT missing, and a value published on neither side is not decision-critical unless the decision turns on it; (3) the equivalence decision actually depends on it — no identifier relationship is established per the IDENTIFIER RELATIONSHIP RULES, and not all target-published hard identity dimensions are aligned or uncontradicted on the candidate side.
- Credit ALL supplied evidence on both sides (structured facts and raw observation text) BEFORE naming anything missing.
- Do not name PACKAGING_QUANTITY / BUNDLE under the non-critical condition of the COMMERCIAL SALES-UNIT RULES.

INTERNAL CONTRADICTION RULE   [2.1 NEW]
- If the supplied evidence contradicts ITSELF on a dimension (for example, the title states one capacity and the specification text states another, or one published field states a packaging and another contradicts it), that dimension is unresolvable in either direction on the supplied evidence. It is not a conflict against the target: do not pick one published side as the product's value, do not assert the corresponding conflict class, and do not return NO_MATCH on an internally contradictory dimension alone. Return UNCERTAIN and name the dimension in missing_critical_attributes.

DECISION RULES   [2.1 CHANGED]
- MATCH: the identifier relationship is established per the IDENTIFIER RELATIONSHIP RULES (exact identifier; SKU equal to the target; a consistent partial form of the requested identifier; no identifier question with the product evidence deciding; or a near-miss resolved by labeled MANUFACTURER_RELATION_AUTHORITY); no published hard conflict exists (CONFLICT CLASSES); the sales unit does not block per the COMMERCIAL SALES-UNIT RULES; and every target-published hard identity dimension is aligned or uncontradicted on the candidate side.
- NO_MATCH: the candidate is a different product or is not pricing-comparable as the same sales unit, grounded in the published structured conflict classes (including the absolute packaging rule). Never return NO_MATCH on missing evidence alone, on an internally contradictory dimension alone, or on a customer-retrieval relation.
- UNCERTAIN: the evidence is insufficient or ambiguous — a decision-critical dimension is missing, the identifier relationship is not established, a dimension is internally contradictory, or the sales unit is critical per the COMMERCIAL SALES-UNIT RULES. If evidence is insufficient, output UNCERTAIN rather than guessing. A false MATCH is materially worse than UNCERTAIN.
- Confidence reflects the strength of the supplied identifier and attribute evidence, not your certainty: an exact published identifier with all target-published hard dimensions aligned supports at most HIGH; a different retailer SKU, a consistent partial identifier, or a no-identifier attribute match supports at most MEDIUM; never report HIGH where a decision-critical dimension is missing.

RESPONSE FORMAT   [2.0 unchanged, with one addition]
Return exactly one JSON object with exactly these keys and no others. No prose before or after. No Markdown or code fences. There is no chain-of-thought field and no hidden-reasoning field: reason_code and the structured attribute lists are the entire explanation surface.
{
  "decision": "MATCH" or "NO_MATCH" or "UNCERTAIN",
  "confidence": "HIGH" or "MEDIUM" or "LOW",
  "reason_code": one of: MATCH_EXACT_PRODUCT_CONTEXT, MATCH_DESCRIPTION_AND_ATTRIBUTES, MATCH_AUTHORIZED_IDENTIFIER_RELATION, UNCERTAIN_MISSING_CRITICAL_ATTRIBUTES, UNCERTAIN_IDENTIFIER_RELATION, NO_MATCH_MPN_IDENTITY, NO_MATCH_PRODUCT_FAMILY, NO_MATCH_GENERATION, NO_MATCH_CAPACITY, NO_MATCH_INTERFACE, NO_MATCH_FORM_FACTOR, NO_MATCH_PRODUCT_ROLE, NO_MATCH_ACCESSORY, NO_MATCH_PACKAGING, NO_MATCH_BUNDLE, NO_MATCH_MULTIPLE_CONFLICTS, NO_MATCH_OTHER,
  "matched_attributes": [{"dimension": <dimension>, "detail": <short observed text>}],
  "conflicting_attributes": [{"dimension": <dimension>, "detail": <short observed text>}],
  "missing_critical_attributes": [<dimension>, ...],
  "conflict_classes": [<conflict class value>, ...]
}
The bounded attribute dimensions are: PRODUCT_FAMILY, GENERATION, CAPACITY, INTERFACE, FORM_FACTOR, PRODUCT_ROLE, ACCESSORY_RELATION, PACKAGING_QUANTITY, BUNDLE, BRAND, REVISION_OR_SUFFIX, CONDITION.
[2.1 NEW] MATCH_AUTHORIZED_IDENTIFIER_RELATION may be used only when the CONTEXT PROVENANCE section explicitly lists MANUFACTURER_RELATION_AUTHORITY.
```

### 8.3 User-prompt template changes (exactly two lines)

1. Section C header:
   - 2.0: `DETERMINISTIC IDENTITY CONTEXT (frozen deterministic layer output; you cannot override it):`
   - 2.1: `DETERMINISTIC IDENTITY CONTEXT (frozen deterministic layer output; the identifier facts are established; the relationship requirement line is downstream authority-tier policy, not your decision input):`
2. The requirement line:
   - 2.0: `- Relationship requirement: {value}`
   - 2.1: `- Relationship requirement (downstream authority-tier policy, not your decision input): {value}`

All other rendered lines (sections A, B, D, E; every fact/absence/sales-unit/provenance line) are byte-identical to the 2.0 rendering for the same recorded input. The test plan pins the diff to exactly these two lines per case.

### 8.4 What stays byte-identical under 2.1

- The output contract: six keys, 17 reason codes, 12 dimensions, conflict-class vocabulary, coherence rules, parser.
- The input contract: 17 top-level fields, evidence classes, sales-unit channel states/kinds, provenance classes, the rendered fact/source/relation labels.
- S2-A: taxonomy, severity sets, the 27-entry matrix, ceilings, the requirement table, NM-2 ceiling, customer-retrieval zero authority, evidence-quality derivation, tier vocabulary, badges.
- The frozen 2.0 prompt text, builder, and digest (regression-pinned — 2.0 remains the contract of the preserved capture and any 2.0-bound corpus/reports).
- The DRAFT policy, the eight gates (names/details), the capture schema v1 shape, the route pins, temperature/max_tokens.


## 9. Eleven-case expected behavioral analysis under Prompt 2.1

Pre-registered expectations for the requalification capture (these are design expectations for review, not harness assertions — the harness scores against the frozen 1.1.0 labels, which are unchanged). "Downstream tier (live)" uses the frozen S2-A derivation over the case's recorded inputs (live authority-side profile where applicable).

| # | Case | 2.0 actual | 2.1 expected decision | 2.1 expected reason (advisory) | Confidence guidance | Missing (expected) | Downstream tier note (frozen rules, unchanged) |
|---|---|---|---|---|---|---|---|
| 1 | `V2Q-SSD-U1-MATCH-0001` | UNCERTAIN (PACKAGING_QUANTITY) | **MATCH** | MATCH_EXACT_PRODUCT_CONTEXT | HIGH (exact title MPN + all hard dims aligned) | none (P3 non-critical) | U1 NOT_REQUIRED → no requirement ceiling; live profile LIMITED → at most NEEDS_REVIEW; no pricing |
| 2 | `V2Q-SSD-SEO-MATCH-0038` | UNCERTAIN (PACKAGING_QUANTITY) | **MATCH** | MATCH_DESCRIPTION_AND_ATTRIBUTES | MEDIUM–HIGH | none | as #1; SEO tokens ignored (preserved rule) |
| 3 | `V2Q-SSD-U1-PRODCTX-0041` | UNCERTAIN (PACKAGING_QUANTITY, BUNDLE) | **MATCH** | MATCH_EXACT_PRODUCT_CONTEXT | HIGH | none (no bundle signal → BUNDLE over-demand removed) | product context grounds STRONG by construction → MATCH+HIGH+STRONG = AI_ASSISTED_COMPARABLE candidate; still no production authority (V2 unqualified) |
| 4 | `V2Q-SSD-U2E-MATCH-0006` | UNCERTAIN (PACKAGING_QUANTITY, BUNDLE) | **MATCH** | MATCH_DESCRIPTION_AND_ATTRIBUTES | MEDIUM–HIGH | none | SKU-equal → requirement NOT_APPLICABLE; no ceiling |
| 5 | `V2Q-SSD-U2N-MATCH-0008` | UNCERTAIN (identifier relation) | **MATCH** | MATCH_DESCRIPTION_AND_ATTRIBUTES | MEDIUM (different retailer SKU) | none | requirement REVIEWED_RELATION_AUTHORITY_REQUIRED → **tier ceiling NEEDS_REVIEW fires downstream** (the case 2.1 explicitly separates: MATCH decision, capped tier) |
| 6 | `V2Q-SSD-SAME-ALTWORDING-0035` | UNCERTAIN (identifier relation; PRODUCT_FAMILY under-credited) | **MATCH** | MATCH_DESCRIPTION_AND_ATTRIBUTES | MEDIUM | none (credit-all-first: family from raw title) | requirement ceiling NEEDS_REVIEW downstream |
| 7 | `V2Q-SSD-U3-MATCH-0010` | UNCERTAIN (identifier relation; REVISION_OR_SUFFIX conflict reported) | **MATCH** | MATCH_DESCRIPTION_AND_ATTRIBUTES | MEDIUM (partial identifier — capped by guidance) | none (consistent partial is not a conflicting revision; no decision-critical dim missing) | requirement ceiling NEEDS_REVIEW downstream; RC-3 grounding gap noted (label stands on supplied evidence under 7.2-U3) |
| 8 | `V2Q-SSD-U4-COND-0017` | UNCERTAIN (BRAND/GENERATION/REVISION_OR_SUFFIX/PACKAGING_QUANTITY) | **MATCH** | MATCH_DESCRIPTION_AND_ATTRIBUTES | MEDIUM (no identifier) | none (target-unpublished dims not decision-critical; condition is price-only, may be reported as CONDITION conflicting attribute) | U4 NOT_APPLICABLE; no ceiling from requirement |
| 9 | `V2Q-DIMM-U4-MATCH-0014` | UNCERTAIN (PACKAGING_QUANTITY, BUNDLE) | **MATCH** | MATCH_DESCRIPTION_AND_ATTRIBUTES | MEDIUM–HIGH (full attribute set) | none | as #8 |
| 10 | `V2Q-DIMM-COND-0039` | UNCERTAIN (PACKAGING_QUANTITY, FORM_FACTOR) | **MATCH** | MATCH_DESCRIPTION_AND_ATTRIBUTES | MEDIUM | none (FF published on candidate, uncontradicted → not missing) | requirement ceiling NEEDS_REVIEW downstream |
| 11 | `V2Q-SSD-U5NM2-RELAUTH-0020` | UNCERTAIN (PACKAGING_QUANTITY) | **MATCH** | **MATCH_AUTHORIZED_IDENTIFIER_RELATION** (the provenance is present — the only case where this code is licenseable) | MEDIUM–HIGH | none (near-miss resolved by labeled authority; not reported as conflicting revision) | NM-2 ceiling does NOT fire (authority present); requirement satisfied; profile LIMITED in the recorded input → NEEDS_REVIEW (would be AI_ASSISTED_COMPARABLE at HIGH+STRONG) |

**Recall arithmetic if 2.1 behaves as expected:** MATCH recall 11/11 = 1.00 (≥ 0.90 DRAFT floor met on the corpus); false MATCH 0; the 20 expected-NO_MATCH, the 5 expected-UNCERTAIN authoritative, and the 7 AMBIGUOUS cases unchanged in expectation (Section 10, T6); the single REVIEW false NO_MATCH (`V2Q-SSD-CONTRA-0037`) expected to flip to UNCERTAIN (its label already says UNCERTAIN — no label change needed or permitted).

## 10. Adversarial regression test plan

The plan is organized so that every frozen protection has a named regression. Items T1–T5 are deterministic (implementation-phase test suites, no model); T6–T8 require the requalification capture (post-approval, bounded live runner, both pinned models).

### T1. Prompt 2.1 contract unit tests (new `tests/semantic/test_contract_v2_1.py`, mirroring `test_contract_v2.py`)

- Version pin: `SEMANTIC_PROMPT_VERSION_V2_1 == "2.1"`; the 2.1 builder constructs only 2.1; rejects any other version argument.
- **2.0 freeze regression (no in-place edit):** `SYSTEM_PROMPT_V2` byte-identical (digest `c0cc98bd...` reproduces); `build_semantic_prompt_v2` output for every corpus case byte-identical to the recorded 2.0 prompts (recomputed from the frozen builder over the 1.0.0 corpus — historical reconstructability preserved).
- New-clause presence pins (exact substrings, one test per clause): the absolute rule with the raw-cue evidence base; target-commercial-unit default; P3 non-critical (do-not-block + do-not-infer + do-not-name); P4 critical (complete-different-part-number, no manufacturer authority, customer-retrieval-only, suffix/substituted-character, "cannot be separated"); per-substate identifier rules (U1/U2 both signals/U3 partial-not-conflicting-revision/U4 no-question/U5 complete-different-never-automatic + authority-only establishment); the two appended CONTEXT PROVENANCE sentences (customer-retrieval never establishes between different published part numbers; resolved near-miss not reported as a conflicting revision); the added WHAT YOU SHOULD DETERMINE bullet (identifier relationship); the requirement-line meaning (both directions: neither blocks nor permits); credit-all-first; decision-critical three-part definition; internal-contradiction rule (no side picked; never NO_MATCH alone); the MATCH/NO_MATCH/UNCERTAIN decision rules; confidence guidance; `MATCH_AUTHORIZED_IDENTIFIER_RELATION` ⟺ `MANUFACTURER_RELATION_AUTHORITY` tie.
- Preserved-clause presence pins: every [2.0 unchanged] section's key sentences (task framing, all four NOT-asked rules, evidence classes, the never-infer rule, customer-retrieval zero authority, product-context grounding-only, accessory rule, conflict classes, "A false MATCH is materially worse than UNCERTAIN", no chain-of-thought).
- User template: rendered diff vs 2.0 for every corpus case is **exactly the two annotated lines** (header + requirement line); all other lines byte-identical.
- Determinism: same input → same 2.1 prompt (twice-call stability), as frozen.

### T2. Binding / adapter / replay (research boundaries)

- The 2.1 binding constant `("V2", "2.1", 1, 1, "SEMANTIC_AUTHORITY_V2_S2A_FU2")` is defined and drift-pinned to the adapter registration.
- Cross-version refusal both directions: a 2.1 record replayed under the 2.0 gate → explicit refusal (never reinterpreted); a 2.0 record under the 2.1 gate → explicit refusal. Unknown bindings still refused. `SUPPORTED_CONTRACT_BINDINGS` = registry union (now including 2.1) — completeness-checked.
- The 2.0 no-capture baseline reports (both pinned candidates) remain **byte-identical** (committed artifact regression).
- S2-A module freeze: no source change (file hash pin or existing boundary tests) — the authority contract, matrix, ceilings, requirement table, and NM-2 rule are byte-untouched; the V2 authority derivation over a synthetic 2.1-shaped evaluation still yields the frozen tiers (e.g., 0020-shape: MATCH+HIGH+STRONG with authority present and NM-2 active → AI_ASSISTED_COMPARABLE; MATCH+MEDIUM+STRONG same shape → NEEDS_REVIEW; 0018-shape: a MATCH output with no relationship authority that would otherwise reach AI_ASSISTED_COMPARABLE → requirement ceiling NEEDS_REVIEW — proving the tier side independently of the prompt).

### T3. Corpus 1.1.0 re-seal integrity (evaluation)

- All 56 `case_digest`s byte-identical between `corpus_v1.json` (1.0.0) and the 2.1 corpus (1.1.0) — the mechanical proof of zero label change.
- Per-case zero-diff assertion over `expected` (decision, acceptable_decisions, conflict_classes, missing_dimensions, expected_reason_code, commercial_sales_unit_safety, disposition, rejection_class) and over `input_payload`, `label`, `substate`, `primary_signal`, `case_class`, `category`, `challenge_tags`, `evidence_kind`, `input_shape`.
- Top-level: `corpus_version` = 1.1.0; `semantic_contract_binding` = the 2.1 production binding; `label_revisions` = [] (a binding re-point is not a label revision); `corpus_digest` recomputed and sealed; loader accepts 1.1.0 against the 2.1 binding and still accepts 1.0.0 against the 2.0 binding (both coexist; no migration of the historical corpus).
- Anti-manipulation property preserved: any per-case mutation in 1.1.0 fails the case-digest check exactly as in 1.0.0.

### T4. Harness invariance (evaluation)

- The eight gates: names and details byte-identical (gate 6 pins the 2.1 production binding in the 2.1 context — the only allowed delta); gate logic unchanged (proved by re-running the gate suite over a synthetic result set).
- DRAFT policy artifact byte-identical: thresholds 0.99 / 0.90 / 0.99 / 1.00, `approved: false`; decision precedence unchanged (POLICY_PENDING reachable, QUALIFIED not); a perfect 2.1 capture stays POLICY_PENDING until policy approval.
- Severity mapping unchanged (CRITICAL false MATCH on ALWAYS_HARD/sales-unit-safety; HIGH other false MATCH; MEDIUM false NO_MATCH on expected MATCH; REVIEW abstention-on-definite; model confidence never overrides the label).
- No-capture 2.1 baseline report reproducible (43/43 NOT_CAPTURED, POLICY_PENDING), mirroring the committed 2.0 baselines.
- The 13 CONTRACT_NEGATIVE cases: identical rejection classes under 1.1.0 (loader-level, prompt-independent) — 13/13 INPUT_REJECTED as before.

### T5. Capture infrastructure (bounded live runner)

- The runner executes all 43 eligible cases per model; the 13 contract-negative cases are never rendered/sent/recorded (preserved proof); fixed retry policy, envelope, model pinning, credential discipline, manifest shape — all unchanged except the prompt-version pin (2.1) and the system-prompt digest (new, recorded).
- The two pinned models are captured independently (primary `amax/qwen3.8-27b`, fallback `vllm-262k/Qwen3.6-27B-262K`); the fallback capture that was blocked in Q3-B/Q3-B2 (endpoint unconfigured) must be completed in the requalification window; a second model showing the same profile confirms the fix is contract-driven, not model-specific (Q3-B2 recommendation 4).

### T6. Pre-registered per-case expectations (43 semantic cases)

Expected decisions for the 2.1 capture, derived in Section 9 (11 cases) and here for the rest (labels unchanged; "Δ" = behavior change vs the 2.0 capture):

- **20 expected-NO_MATCH (all must stay NO_MATCH; gate 1/2/3 territory):** 0002 (accessory/compat, ACCESSORY+ROLE), 0003 (SEO ref + CAPACITY), 0004 (crossref + GENERATION), 0007 (SKU collision + accessory role), 0011 (U3 + CAPACITY conflict — the published 8TB decides, identifier shape irrelevant), 0016 (cross-category ROLE), 0019 (U5 + CAPACITY/GENERATION published conflicts), 0024/0025/0026/0027/0028/0029/0030 (attribute conflicts), 0031 (caddy), 0032 (tray OBSERVED — absolute rule), 0033 (pack of 4 OBSERVED — absolute rule), 0034 (bundle OBSERVED — absolute rule), 0036 (multi-conflict), 0042 (bracket/cable kit). The 2.0 model got 20/20; the 2.1 risk direction is false MATCH, watched by gates 1–3.
- **5 expected-UNCERTAIN authoritative:** 0012 (U3 prefix + CAPACITY/FORM_FACTOR unpublished → UNCERTAIN naming them; PACKAGING_QUANTITY no longer expected named under the P3 non-critical rule), 0015 (U4 "NVMe SSD" thin → UNCERTAIN), 0018 (Micron: **P4 critical → UNCERTAIN naming PACKAGING_QUANTITY; the CRITICAL sales-unit-safety guard — a MATCH here fails gate 2 with CRITICAL severity**), 0022 (alias: same as 0018, P4), 0037 (internal contradiction: **Δ expected flip from NO_MATCH to UNCERTAIN** — the label already says UNCERTAIN).
- **7 AMBIGUOUS (must land inside acceptable sets):** 0005 {MATCH, UNCERTAIN} (U1 bare token: default UNCERTAIN naming the unpublished target-published hard dims; MATCH defensible on the exact identifier), 0009 {MATCH, UNCERTAIN} (default: UNCERTAIN naming INTERFACE), 0013 {UNCERTAIN, MATCH} (default under 2.1: all target dims aligned → MATCH permitted; the recorded-catalog three-way ambiguity is not transmitted (RC-3-class) — both poles defensible on supplied evidence), 0021 {NO_MATCH, UNCERTAIN} (default: UNCERTAIN — U5 not established; MATCH excluded by 7.2), 0023 {NO_MATCH, UNCERTAIN} (same; product context does not establish the relation), 0040 {NO_MATCH, UNCERTAIN} (published different brand = reviewable material difference; MATCH excluded by the decision rules' "no published hard conflict" + brand handling), 0043 {MATCH, UNCERTAIN} (U4 form factor unproven: default UNCERTAIN naming FORM_FACTOR; MATCH inside the acceptable set). An OUTSIDE_DEFENSIBLE result (severity HIGH if MATCH) is a requalification watch failure, not a gate failure.
- **Valid structured response rate:** 43/43 required (the 2.1 schema is the frozen v1 output — parser unchanged).
- **Input-aware cross-checks (gates 5/6):** any `MATCH_AUTHORIZED_IDENTIFIER_RELATION` response without `MANUFACTURER_RELATION_AUTHORITY` in the input → UNAUTHORIZED_AUTHORITY_CLAIM (only 0020 licenses the code); any MATCH on 0018/0022 → CUSTOMER_ALIAS_PROMOTION-relevant CRITICAL failure.

### T7. Model-side watch items (from Q3-B2, carried forward)

- #6 (`0035`): PRODUCT_FAMILY must be credited from the raw title (under-crediting error). If it recurs, it is model-side (RC-4) — no further prompt change in 2.1; record for the next bounded correction if persistent.
- #8 (`0017`) / #10 (`0039`): no target-unpublished dimensions in `missing_critical_attributes` (over-demanding).
- `0020`: the near-miss difference must not be reported as a conflicting revision when the labeled authority resolves it.
- `0037`: the internal-contradiction rule compliance (flip to UNCERTAIN).

### T8. Future probes (recorded; NOT added to the 1.1.0 seal)

The following live shapes are **not represented in the frozen corpus** (its packaging negatives use the structured OBSERVED channel; the live channel is always UNAVAILABLE). They are recorded as design probes for a future reviewer-labeled corpus extension (a later phase with its own label governance), not as requalification assertions:

- Silent multi-pack: a 4-pack with NO packaging cue in the structured channel or raw text (channel UNAVAILABLE, title clean) → 2.1 permits MATCH (cell P3). **Documented residual risk** (Section 13, R1).
- Raw-cue pack/tray/bundle: "pack of 4" / "(tray)" / "+ 2x Power Cable" in the title only → 2.1 expects NO_MATCH (P2 via the raw-cue evidence base).
- Ambiguous "kit": unclear contents → 2.1 expects UNCERTAIN (P6).
- Customer-alias near-miss with a raw tray cue in the candidate title → NO_MATCH (published conflict beats the unresolved relation; the absolute rule).
- One-character substitution with manufacturer-stated non-materiality evidence (not constructible today — no provenance class carries "manufacturer-stated non-material revision note") → out of the bounded input contract; stays UNCERTAIN/NO_MATCH by the U5 rule.

## 11. Production-input limitations

These are frozen properties of the live S2-C-FU1 input pipeline (independently confirmed in Section 2.3) and bound what any prompt — 2.0 or 2.1 — can see in production:

1. **The sales-unit channel is ALWAYS UNAVAILABLE live.** `build_candidate_commercial_evidence_v2` hard-wires `SALES_UNIT_EVIDENCE_UNAVAILABLE`; the 3A extractor publishes no packaging field and no packaging value is inferred from price or any other commercial fact. The OBSERVED states (SINGLE_UNIT / PACK_QUANTITY / TRAY_OR_FACTORY_PACK / BUNDLE) are representable and codec-tested but unreachable from the live main flow today. **Consequence:** the absolute rule (P2) operates live solely through raw-observation-text cues (model judgment) until extraction publishes the field — the main residual safety gap of a prompt-only fix (R1/R2).
2. **Structured product facts are brand-only.** Every other product dimension is explicit None; the title is RAW observation text (no token is parsed into a structured fact); no specification text is carried (it remains in the opaque `raw_reference`, unparsable per AD-040). **Consequence:** all live equivalence reasoning rides on raw title text + the requested description — the same evidence base the corpus models.
3. **Reviewed target context exists only in the 4D-D shape.** The only wired reviewed target context is the Micron 7500 customer-retrieval alias (CUSTOMER_RETRIEVAL_ALIAS; the box quantity is deliberately NOT carried into the main flow and must not be claimed as candidate packaging evidence). **Consequence:** cell P4 (the Micron guard) is live-reachable exactly in the alias-expanded search batch — the motivating shape.
4. **The authority-side profile is at most LIMITED live.** The live path passes `matched_facts=frozenset()` (documented S2-C limitation: the main flow grounds no bounded identity-dimension equality). **Consequence (independent of the prompt):** even a correct 2.1 MATCH/HIGH is at most NEEDS_REVIEW in production — no automatic pricing eligibility. Recall at the identity-decision level is the only axis 2.1 moves; pricing eligibility remains blocked by the evidence-quality ceiling until the grounding infrastructure lands (P3).
5. **The corpus is a faithful model of the live input on these axes.** All 11 expected-MATCH cases carry brand-only / no-packaging / raw-title inputs, and the negative packaging cases explicitly note "(CONTRACT_SURFACE: the live extractor publishes no packaging field today; the frozen channel represents this observation)." The 2.1 design is therefore tested on the corpus against the live input reality for everything except raw-cue packaging (T8), which is untestable on the frozen corpus by construction.
6. **No V2 production record exists.** V2 is persist-only and unqualified (`V2_AUTHORITY_QUALIFIED = False`); the 2.1 contract version has no live reinterpretation surface.

## 12. Recommendation — combined phased approach (prompt 2.1 first; extraction independent follow-up)

**Prompt 2.1 alone is sufficient to resolve the observed zero-MATCH recall on the qualification corpus, and it is the necessary first step; structured packaging extraction is a complementary live-safety hardening that must not gate it, and extraction-first alone is insufficient.**

Reasoning:

1. **Prompt-only is sufficient for the corpus (and for the live decision shape).** All 11 abstentions are prompt-contract ambiguities (A–F), not input deficiencies: every one of the 11 cases is decidable on its supplied evidence under the criteria defined in Sections 6–7 (verified case-by-case in Section 9). The live input shape is the same (Section 11.5). If a qualified model under 2.1 still abstains on the 11, that is model-side (watch items T7), not contract-side.
2. **Extraction-first is insufficient.** The 11 corpus listing pages publish no packaging field at all (by construction; the negative packaging cases are the only ones with OBSERVED channels, and they are the NO_MATCH cases). A perfect extractor still leaves `sales_unit = UNAVAILABLE` on all 11 — the zero-recall persists. The Q3-B2 fallback-model confirmation (still blocked on endpoint configuration) would independently confirm the prompt-contract (vs model-specific) cause, but it cannot substitute for the contract fix.
3. **Extraction (P2) is needed for live safety, independently.** The absolute rule's live grounding is raw-cue model judgment (Section 11.1). A bounded 3A/3B phase that publishes the OBSERVED channel **only where the page actually publishes packaging** (approved extraction mechanisms; no opaque `raw_reference` parsing beyond the approved pattern; no inference from price) makes P2 deterministic-evidence-grounded live and shrinks R1/R2. It changes no prompt, no label, no authority rule; the 2.1 prompt already handles OBSERVED inputs correctly (the corpus negative cases prove it).
4. **Grounding (P3) is a separate track.** The authority-side matched-fact infrastructure (the documented S2-C limitation) determines whether live 2.1 MATCHes can ever reach AI_ASSISTED_COMPARABLE; it is orthogonal to the prompt contract and to packaging extraction.

Phasing (each phase a bounded, reviewed, separately-approvable deliverable):

- **P1 — Prompt 2.1 contract phase (implements this design):** 2.1 prompt + builder + version constant; 2.1 binding + adapter registration (cross-version refusal both directions); corpus 1.1.0 re-seal (labels byte-identical, proven by case digests); harness/capture/report pin extensions; T1–T5 test suites; then the bounded requalification captures (primary + fallback, independent) and T6–T7 evaluation. Exit criteria: eight gates pass on both models; recall ≥ 0.90 and precision ≥ 0.99 on the DRAFT policy's arithmetic (decision remains POLICY_PENDING until policy approval — unchanged); zero false MATCH; 0018/0022 remain UNCERTAIN.
- **P2 — Packaging extraction (independent; may start after P1 approval, not before requalification evidence exists):** bounded 3A/3B OBSERVED-channel publication; its own corpus extension (the T8 probes become reviewer-labeled cases, a later corpus version with its own digest and label governance); no prompt change required (2.1 already covers OBSERVED).
- **P3 — Authority-side grounding (separate track):** matched-fact infrastructure so live profiles can reach STRONG; no prompt change.
- **Q3-C — Policy approval and qualification decision:** unchanged in scope; it approves the DRAFT policy (or a revised one) and makes the qualification decision against the 2.1 evidence. Prompt 2.1 does not preempt it.

## 13. Unresolved risks (explicit)

- **R1 — Silent multi-pack / silent tray (no cue anywhere).** Under 2.1 cell P3, a listing that sells a 4-pack but publishes no packaging signal in the structured channel or raw text is MATCH-able. This is the direct cost of fixing the 11 false abstentions: the same evidence gap that blocked them also hides a silent multi-pack. Mitigations, all already in the frozen contract: (i) the identity decision is advisory — the live tier for such a MATCH is at most NEEDS_REVIEW (LIMITED profile, Section 11.4) and no V2 authority is qualified, so it cannot enter pricing automatically; (ii) the DRAFT precision floor (0.99) and the eight gates bound qualification; (iii) P2 extraction removes the gap at the source for pages that do publish packaging. **Not mitigable by prompt alone** — accepted as residual, monitored in live audits.
- **R2 — Raw-cue detection reliability.** P2/P6 ride on a 27B-class model reading packaging cues in raw title text. A missed cue = R1 exposure; a false cue (marketing "kit"/"bundle" wording on a single-unit product) = false NO_MATCH (safe direction, REVIEW-severity at most, and the P6 ambiguous-cue rule pushes unclear wording to UNCERTAIN rather than NO_MATCH). P2 removes the dependency.
- **R3 — `V2Q-SSD-U3-MATCH-0010` grounding gap (RC-3).** The label's recorded-catalog grounding is not carried by any frozen input channel. The 2.1 U3 rule makes the expected MATCH stand on supplied evidence (consistent prefix + full alignment), but if the recorded catalog were later found to treat that prefix as a distinct family, the label would require a class-B (source-changed) revision — a future governance event, not a current conflict.
- **R4 — Fallback model behavior unconfirmed.** The fallback capture is still absent (endpoint unconfigured in Q3-B/Q3-B2). The 2.1 design is model-agnostic (contract wording, not model-specific tuning), but the second-model confirmation that the fix is contract-driven is pending (T5 requires both captures).
- **R5 — `V2Q-SSD-CONTRA-0037` flip depends on compliance.** If the model still picks a side of an internal contradiction, the output remains a REVIEW-severity false NO_MATCH (safe direction; not a gate failure). The 2.1 internal-contradiction rule is stated, not structurally enforced (the parser cannot see the input).
- **R6 — Confidence is not scored and is now guided.** The new confidence guidance (Section 8.2) can shift tier outcomes at the boundary (e.g., 0041 HIGH+STRONG → AI_ASSISTED_COMPARABLE vs MEDIUM → NEEDS_REVIEW). Bounded: the guidance only ever lowers confidence relative to over-claiming, the live profile caps at LIMITED regardless, and V2 carries no production authority while unqualified. Recorded so the approval review can reject the guidance if deemed scope creep.
- **R7 — Corpus 1.1.0 re-seal changes the corpus digest.** Any historical 2.0 report/capture remains bound to 1.0.0 and fails closed against 1.1.0 (and vice versa) — by design (no reinterpretation), but operations must keep both corpus files and both binding contexts distinct.
- **R8 — The "default single commercial unit of the requested part" (Section 6.1) is a contract-level semantic choice.** It matches all 56 corpus cases and the product's MPN-based request model, but it is new prompt semantics; it is an explicit approval question (Q1) precisely because a target that is itself a multi-unit part (a pack MPN) is decided by its supplied target-side evidence, not by the default.
- **R9 — No live recapture was or is performed in this session.** Everything above is a design prediction against the preserved 2.0 capture and the frozen contract; the 2.1 expectations (Sections 9–10) are pre-registered, not observed.

## 14. Approval questions

The bounded implementation phase (P1) may start only on explicit answers to:

1. **Q1 (sales-unit rule):** Approve the cell P1–P6 decision matrix (Section 6.2) as the 2.1 contract semantics — specifically: (a) the default target commercial unit = single unit of the requested part unless target-side supplied evidence establishes otherwise; (b) missing sales unit blocks MATCH **only** in cell P4 (complete different part number, no manufacturer relationship authority, aligned otherwise — the Micron shape); (c) UNAVAILABLE with no cue is never read as "single unit" and never named missing-critical; (d) raw-text packaging cues are packaging evidence for the absolute rule.
2. **Q2 (identifier semantics):** Approve the per-substate identifier decision rules (Section 7.2) — specifically: U3 consistent partial = not a different product number and not a conflicting revision; U5 complete different part number = never equivalent without `MANUFACTURER_RELATION_AUTHORITY` (customer retrieval and product context never establish); U2 different SKU = not proof of a different product.
3. **Q3 (requirement line):** Approve stating to the model that the rendered "Relationship requirement" is downstream authority-tier policy that neither blocks nor permits its decision (Section 7.3) — a prompt-level explanation of an unchanged S2-A rule, with the two-line user-template annotation.
4. **Q4 (missing-critical + contradiction):** Approve the decision-critical three-part definition and credit-all-first rule (Section 7.4) and the internal-contradiction → UNCERTAIN rule (Section 8.2), with the pre-registered `V2Q-SSD-CONTRA-0037` flip.
5. **Q5 (corpus re-seal):** Approve corpus 1.1.0 as a binding-only re-seal of the identical 56 labels (per-case digests byte-identical, `label_revisions` empty, new corpus digest, both versions coexisting) as the 2.1 requalification target.
6. **Q6 (versioning):** Approve the 2.1 binding `("V2", "2.1", 1, 1, "SEMANTIC_AUTHORITY_V2_S2A_FU2")`, the separate adapter registration with cross-version replay refusal, and the byte-freeze of all 2.0 artifacts (prompt text, digest, corpus 1.0.0, baseline reports).
7. **Q7 (phasing):** Approve the combined phased recommendation (Section 12): P1 prompt 2.1 + requalification (primary **and** fallback captures) first; P2 packaging extraction as an independent follow-up (not a precondition); P3 grounding as a separate track; Q3-C policy approval and qualification decision unchanged in scope and sequence (decision stays POLICY_PENDING until the policy is approved).
8. **Q8 (confidence guidance):** Approve or reject the confidence guidance sentence in Section 8.2 (R6) — rejectable without affecting any other 2.1 clause.

## 15. Preservation and boundary statement

- **This session changed nothing in the repository source, tests, corpus, policy, or thresholds.** All inspection was read-only; all capture analysis re-parsed the preserved document through the frozen production parser without modification. The frozen 2.0 prompt digest (`c0cc98bd...`), corpus 1.0.0 digest (`2c37ba08...`), capture document (`d94f1ed8...`) and manifest (`46f818bb...`), and official report digest (`40340ce4...`) were independently recomputed/verified and are unchanged.
- **No live model call, no capture, no deployment, no qualification approval, no authority promotion, no commit.** The deliverable (this document) is left untracked in the worktree with all pre-existing worktree evidence (the seven historical benchmark artifacts, the pre-existing `tmp_collection.txt` modification, the live-capture directory contents, the Q3-B2 diagnosis artifacts) preserved.
- **New untracked session artifacts:** this design document; `tmp_q3b3_collect.txt` (per-file collection count proving the 6928 baseline at the starting SHA); `tmp_q3b3_full.txt` (full-suite regression run over the unmodified tree); `tmp_q3b3_iso1.txt` / `tmp_q3b3_iso2.txt` / `tmp_q3b3_iso3.txt` / `tmp_q3b3_iso_r1..r3.txt` (isolation retries of the two flaked subprocess-guard nodes).
- **Regression baseline (executed this session over the unmodified tree at the starting SHA):** full suite: **6928 executed; 6926 passed; 2 failed** — both failures are the documented load-sensitive clean-interpreter subprocess guard flake class (`OSError: [WinError 6]` at `Popen -> _get_handles -> _make_inheritable -> _winapi.DuplicateHandle`, before any project code runs; zero assertion failures, zero collection errors): `tests/domain/test_domain_boundaries.py::test_domain_imports_without_django_network_or_llm_dependencies` and `tests/evaluation/test_evaluation_boundaries.py::test_loading_the_corpus_imports_no_framework_or_provider` — the same two nodes as the Q3-B full-suite record. Both re-passed on isolated one-node-per-process retry (node 1: 1/1; node 2: 3/3 after two flaked attempts). Skipped / xfailed / deselected: **0 / 0 / 0**. The known flake allowlist was NOT expanded; no non-flake node failed.
- **Ground-truth rule compliance:** no expected decision, conflict label, flag, or threshold was moved to suit any observed or predicted model behavior; the only "changes" this design proposes are to the prompt contract (a new version), a binding re-seal of identical labels, and harness pin extensions — each an approval-gated, separately reviewable deliverable.
