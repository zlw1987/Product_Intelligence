# Product Intelligence — Semantic Authority V2: Q3-B4 Authority Boundary Decision

**Session:** PRODUCT-INTEL.SEMANTIC-AUTHORITY-V2-Q3-B4 — Semantic MATCH Authority Boundary Decision
**Mode:** CONTRACT DESIGN ONLY (architecture-analysis / decision document). No implementation, no runtime change, no test modification, no corpus change, no model capture, no deployment, no authority promotion.
**Starting SHA:** `3e6d326d3f7d36ef377a0f9f78899ca68b6e3aa6` (Q3-B3-FU2 endpoint; confirmed `git rev-parse HEAD` this session)
**Test collection baseline at starting SHA:** **6928** (re-verified this session: per-file collection sum over 170 files = 6928, `tmp_q3b4_collect.txt`; identical to the recorded Q3-B-FU1 / Q3-B3 / Q3-B3-FU1 / Q3-B3-FU2 baselines)

**Role split (preserved):** the operator (this session) produces the bounded
architecture analysis; **ChatGPT remains the architecture reviewer and final
approval gate.** This document is a decision PROPOSAL with explicit approval
questions. It does not claim architecture approval and does not authorize any
implementation.

## Relationship to the prior design documents

| Document | Role | State |
| --- | --- | --- |
| `docs/PRODUCT_INTEL_SEMANTIC_V2_PROMPT_2_1_DESIGN.md` | Q3-B3 (revision 0) Prompt 2.1 design | Untracked, byte-unchanged (SHA-256 `bb3aa9dc3b8e195db19589914cd07a646483c451f82a9f7a1d65e1f4aaf730dd`, re-verified this session) |
| `docs/PRODUCT_INTEL_SEMANTIC_V2_PROMPT_2_1_DESIGN_Q3B3_ORIGINAL.md` | Byte-identical copy of revision 0 | Untracked, byte-unchanged (verified identical this session) |
| `docs/PRODUCT_INTEL_SEMANTIC_V2_PROMPT_2_1_DESIGN_Q3B3_FU1_REVISION_1.md` | Revision 1 (Q3-B3-FU1) | Untracked, byte-unchanged (SHA-256 `1c21c86c34fe06441f7c74ceded4fdb4e689a50181cabbc6883b1e8657dc3db0`, re-verified this session) |
| `docs/PRODUCT_INTEL_SEMANTIC_V2_PROMPT_2_1_DESIGN_Q3B3_FU2.md` | **Revision 2 (Q3-B3-FU2)** — the current Prompt 2.1 design of record; the committed starting-SHA document this decision builds on | Tracked at the starting SHA (SHA-256 `0ba54848f5a862646e8c241391e7d826ed0b61e423abc4c7cb261799b3ebc879`, re-verified this session) |
| this document | **Q3-B4:** the authority-boundary decision resolving the two remaining Prompt 2.1 blockers (Task A: executable MATCH semantics; Task B: sales-unit pricing firewall), with the target architecture, contract-amendment requirements, adversarial acceptance matrix, phases, and approval questions | Deliverable of this phase; committed and pushed (this document only) |

Q3-B3-FU2 already: (a) corrected the identity-sufficiency semantics (six
evidence classes; three resolutions; "alignment is not uniqueness"), (b)
proved the frozen tier derivation **structurally sales-unit-blind** (§3.3 of
that document), (c) classified the current safeguards as **state, not
contract** (§3.4), (d) exposed the future qualified-state silent-multi-pack
pricing path (§3.5 / R14), and (e) specified P4 as a **separately
approval-gated proposal** with three candidate forms (P4-a / P4-b / P4-c).
Q3-B4 is the decision on P4 and on the identity-resolution boundary: it
selects among the options, pins the exact conflicts with the frozen criteria,
and defines the smallest coherent target architecture. It changes **no** Q3-B3
semantics; where it supersedes Q3-B3's open P4 question, it says so explicitly.

## Evidence of record (independently re-verified this session)

| Artifact | Identity |
| --- | --- |
| Frozen prompt 2.0 | `product_intelligence/semantic/contract_v2.py`, `SEMANTIC_PROMPT_VERSION_V2 = "2.0"`; REAL system-prompt digest **`c0cc98bdd6d357e81d4692218f18d354351fc2833267b3062b7cd74b18445a84`** — recomputed this session as `canonical_sha256({"text": SYSTEM_PROMPT_V2})`; exact match |
| Frozen contract binding | `("V2", "2.0", 1, 1, "SEMANTIC_AUTHORITY_V2_S2A_FU2")` — re-read from `corpus_v1.json` `semantic_contract_binding` and from `research/semantic_decision_v2.py` (`V2_CONTRACT_BINDING`) this session |
| Qualification corpus | `evaluation/semantic_v2_qualification/corpus_v1.json`, v1.0.0, digest **`2c37ba088c317d8cefc6ad0dd7e0d73cfd085f6474ef43eb6953e3cf0170b549`**, 56 cases (43 semantic: 36 UNAMBIGUOUS + 7 CONTESTABLE; 13 CONTRACT_NEGATIVE), `label_revisions` empty — re-read and re-counted this session |
| Expected-MATCH set (11) | `V2Q-SSD-U1-MATCH-0001`, `V2Q-SSD-SEO-MATCH-0038`, `V2Q-SSD-U1-PRODCTX-0041`, `V2Q-SSD-U2E-MATCH-0006`, `V2Q-SSD-U5NM2-RELAUTH-0020`, `V2Q-SSD-U2N-MATCH-0008`, `V2Q-SSD-U3-MATCH-0010`, `V2Q-SSD-U4-COND-0017`, `V2Q-DIMM-U4-MATCH-0014`, `V2Q-DIMM-COND-0039`, `V2Q-SSD-SAME-ALTWORDING-0035` — extracted from the corpus this session |
| Ambiguous (CONTESTABLE) set (7) | `V2Q-SSD-U1-THIN-0005`, `V2Q-DIMM-U2N-THIN-0009`, `V2Q-SSD-U4-AMBIG-0013`, `V2Q-SSD-U5NM2-NOAUTH-0021`, `V2Q-SSD-U5NM2-PRODCONTEXT-0023`, `V2Q-SSD-BRAND-CONTESTED-0040`, `V2Q-SSD-UNPROVEN-FORM-0043` — extracted from the corpus this session |
| Sales-unit channel states in the corpus | 40 × `UNAVAILABLE` + 3 × `OBSERVED` (`V2Q-SSD-SU-TRAY-0032` tray, `V2Q-SSD-SU-MULTI-0033` pack of 4, `V2Q-GPU-SU-BUNDLE-0034` bundle — all expected NO_MATCH) — counted from `input_payload.candidate.commercial.sales_unit` this session |
| `commercial_sales_unit_safety` flags (5) | `V2Q-SSD-U5NM1-MICRON-0018`, `V2Q-SSD-U5NM1-ALIAS-0022`, `V2Q-SSD-SU-TRAY-0032`, `V2Q-SSD-SU-MULTI-0033`, `V2Q-GPU-SU-BUNDLE-0034` — extracted this session |
| DRAFT qualification policy | `evaluation/semantic_v2_qualification/policy/qualification_policy_draft_1.json`: `approved: false`, `status: DRAFT`; thresholds match precision ≥ 0.99, recall ≥ 0.90, valid response rate ≥ 0.99, eligible coverage ≥ 1.00 — re-read this session |
| Eight hard safety gates | `product_intelligence/evaluation/semantic_v2/gates.py` `HARD_SAFETY_GATES` (line 66): `zero_false_match_on_always_hard_conflicts`, `zero_false_match_on_packaging_quantity_conflicts`, `zero_false_match_on_accessory_product_role_conflicts`, `zero_schema_bypass_acceptance`, `zero_unauthorized_authority_promotion`, `zero_customer_alias_authority_promotion`, `zero_contract_version_mismatch`, `zero_missing_required_evaluation_silent_pass` — re-read this session |
| Primary live capture (evidence of record, unchanged) | `semantic_v2_live_captures/q3b-20261009T010312Z-amax__direct__amax_qwen3.8-27b.json` + manifest + `reports/…__report.json` (report digest `40340ce47d36d3b33b0dcf2a8dcce722abf0a34a399876ed174b6f558866f906`) — untracked session evidence, untouched this session (presence verified) |
| Recorded 4D-D catalog fixture | `tests/fixtures/pages/micron_7500_part_catalog.json` (2026-09-22) — **re-read this session:** three distinct 7500 4TB (3840GB) U.3 parts share the prefix `MTFDKCC3T8TGP` and the part name "7500 4TB U.3 SSD": `MTFDKCC3T8TGP-1BK1DABYY` (6800 MB/s read, Production), `MTFDKCC3T8TGP-1BK1JABYY` (7000 MB/s read, Contact Sales), `MTFDKCC3T8TGP-1BK1DFCYY` (Contact Sales); all with `Module Box Qty: 20`. Independently re-verified (grep over the fixture) |
| Q3-B2 diagnosis | `semantic_v2_live_captures/q3b2-primary-recall-diagnosis.md` / `.json` — untracked session evidence, untouched |
| `V2_AUTHORITY_QUALIFIED` | `False` in both `research/semantic_decision_v2.py:227` and `semantic/runtime_v2.py:97` — re-verified this session |

---

# 1. Current architecture and verified source references

## 1.1 The identity/authority chain (as frozen and as verified this session)

```
                 DETERMINISTIC (sole identity owner)
 3A observation -> 3B normalization -> 3C ListingIdentityAssessment
        |
        +-- ACCEPTED (EXACT / NORMALIZED_EXACT) ----------> MACHINE_PRICE (4A, deterministic only)
        +-- REJECTED + semantic-eligible (V1: NO_EXPLICIT_MPN_EVIDENCE+TITLE_TEXT/SKU_FIELD,
            PARTIAL_MPN_ONLY)  -> V1 semantic (prompt 1.1, frozen FU3A) -> MATCH ->
            AiAssistedReviewCandidate (HUMAN-REVIEW) -> human CONFIRMED ->
            REVIEWED_PRICE (4A reviewed: deterministic ACCEPTED + human-CONFIRMED indices,
            origin DETERMINISTIC / HUMAN_CONFIRMED)
        +-- DETERMINISTIC_UNCERTAIN (V2 overlay: U1/U2/U3/U4/U5) -> V2 semantic (prompt 2.0,
            frozen S2-C/S2-C-FU1; PERSIST-ONLY: V2_AUTHORITY_QUALIFIED=False) ->
            SemanticDecisionRecordV2 (S2-B envelope, binding
            ("V2","2.0",1,1,"SEMANTIC_AUTHORITY_V2_S2A_FU2")) with DERIVED AUDIT SNAPSHOTS:
            product_evidence_quality, relationship_authority, authority_tier, fired_rules
            (no authority code path reads a V2 record today)
```

Verified source references (line numbers at the starting SHA):

| Fact | Source |
| --- | --- |
| V1 response = exactly **6** keys (decision, confidence, reason_code, matched_attributes, conflicting_attributes, missing_critical_attributes) | `product_intelligence/semantic/contract.py` (required_keys set, ~line 324) |
| V2 response = exactly **7** strict keys (the V1 six + `conflict_classes`); missing AND extra keys rejected | `product_intelligence/research/semantic_v2.py:1762` `_V2_RESPONSE_KEYS`; `parse_semantic_response_v2` (line 1779) |
| V2 response coherence rules (NO_MATCH always conflict-grounded; MATCH/UNCERTAIN never carry ALWAYS_HARD) | `research/semantic_v2.py` `_validate_v2_response_coherence` / `SemanticMatchResponseV2.__post_init__` (~line 1967) |
| V2 input = 17 top-level fields, five sections; required `CandidateSalesUnitEvidenceV2` channel (UNAVAILABLE / OBSERVED; kinds SINGLE_UNIT / PACK_QUANTITY / TRAY_OR_FACTORY_PACK / BUNDLE; fail-closed cross-states) | `research/semantic_v2.py` `CandidateSalesUnitEvidenceV2` (line 448), `SALES_UNIT_EVIDENCE_UNAVAILABLE` (line 553), `SemanticMatchCaseV2` (~line 920) |
| **Live sales-unit channel is ALWAYS UNAVAILABLE** (the extractor publishes no packaging field; nothing inferred) | `research/semantic_v2.py:903` inside `build_candidate_commercial_evidence_v2` (line 871) |
| Live authority-side product evidence grounds **zero** matched facts (`matched_facts=frozenset()` → dimension A ≤ LIMITED) | `research/semantic_v2.py:1334` `build_v2_product_evidence_profile` documented limitation; `execution/semantic_decision_v2_execution.py:376` |
| STRONG bar = usable title + ≥ 2 matched facts spanning ≥ 2 distinct hard product dimensions; source vocabulary exactly {LISTING_PRODUCT_TITLE, REVIEWED_PRODUCT_CONTEXT} (no model-claim member) | `research/semantic_authority_v2.py` `STRONG_PRODUCT_EVIDENCE_MIN_MATCHED_FACTS` / `…_DIMENSIONS` (2/2), `derive_product_evidence_quality` (line 1721), `CandidateProductEvidenceSource` (line 1608) |
| Authority-side dimension vocabulary is six hard product dimensions; **packaging/price/condition deliberately excluded** | `research/semantic_authority_v2.py:1586` `ProductEvidenceDimension` (docstring: "Deliberately excluded: price / packaging / condition dimensions") |
| Tier matrix = 27 (decision × confidence × product-evidence-quality) entries; **only MATCH+HIGH+STRONG reaches AI_ASSISTED_COMPARABLE** pre-ceiling | `research/semantic_authority_v2.py:2081` `SEMANTIC_OUTCOME_TIER_MATRIX` (full table re-extracted this session, §1.3 below) |
| Requirement table = 14 entries; U1 NOT_REQUIRED; U2E NOT_APPLICABLE; U2N / U3 / U5-NM-1 / U5-NM-2 REVIEWED_RELATION_AUTHORITY_REQUIRED; U4 NOT_APPLICABLE | `research/semantic_authority_v2.py` `SUBSTATE_RELATIONSHIP_REQUIREMENTS` (re-extracted this session) |
| `derive_authority_tier` inputs: `IdentityStateAssessmentV2` (state, substate, relationship_signals, normalized keys — **no sales unit**), `SemanticEvaluationV2` (**evaluation_state, decision, confidence, conflict_classes only** — no attribute lists), `context_provenances`, `product_evidence` (title + 6-dimension facts — no packaging), `human_review` (CONFIRMED/REJECTED — no unit fact) | `research/semantic_authority_v2.py:643` (assessment), `:1872` (evaluation), `:1678` (profile), `:2305` (human state), `:2412` (derivation) |
| `COMPATIBILITY_WORDING` is a **deterministic overlay signal** (frozen 4-token vocabulary {compatible, replacement, interchangeable, drop-in}; word-boundary title match) recorded in any state whose title matches — but **no derivation consumes it** | `research/semantic_authority_v2.py:540` `COMPATIBILITY_WORDING_VOCABULARY`, signal added ~line 821 ("in any state" per the frozen derivation docstring); absent from `derive_authority_tier` (verified by full read of lines 2412–2620) |
| Ceilings (restrict only, never lift): reviewable conflict on MATCH; NM-2 without relationship authority; state-specific requirement unanswered (`CEILING_IDENTIFIER_RELATIONSHIP_NOT_ESTABLISHED`); then HARD_CONFLICT supersession; then human overlay with precedence **HARD_CONFLICT > HUMAN_CONFIRMED > AI** | `research/semantic_authority_v2.py:2412` `derive_authority_tier` (verified this session) |
| `PRICING_ELIGIBLE_TIERS = {MACHINE_VERIFIED, AI_ASSISTED_COMPARABLE, HUMAN_CONFIRMED}`; import-time invariants: MARKET_EVIDENCE = PRICING_ELIGIBLE ∪ {NEEDS_REVIEW}; **NEEDS_REVIEW never pricing-eligible** | `research/semantic_authority_v2.py:2709`, invariants at lines 2727–2735 |
| V2 execution: evaluation input for the tier is exactly (decision, confidence, conflict_classes) — "the reason code and attribute lists are recorded alongside but are **not matrix inputs**" | `execution/semantic_decision_v2_execution.py:407` `_evaluation_from_result`; tier derived at line 492 in `build_semantic_decision_records_v2` (line 462) with NO human overlay |
| S2-C boundary (binding): V2 outcomes NOT in 4A input, NOT in review-candidate input, NOT in any public summary; "V2_AUTHORITY_QUALIFIED is False and **no authority code path reads a V2 record**" | `execution/semantic_decision_v2_execution.py` module docstring (lines 13–19) |
| V2 record binding + replay: exact-binding gate; **re-derivation under the frozen S2-A module with exact agreement** of (requirement, quality, relationship authority, tier, fired rules); "a future authority contract version is explicitly refused (never silently reinterpreted)" | `research/semantic_decision_v2.py` `AUTHORITY_CONTRACT_VERSION_V2` (line 192), `V2_CONTRACT_BINDING` (~line 200), `_replay_v2_record` (line 2175) |
| V1 records bind the **same** authority token and re-derive through the same `derive_authority_tier` (line 2249) — an in-place change of that function's semantics would break V1 replay too | `research/semantic_decision_v1.py:163` `AUTHORITY_CONTRACT_VERSION`, `:175` `V1_CONTRACT_BINDING` |
| Envelope/adapter architecture: persistence envelope version ≠ semantic contract ≠ prompt ≠ input schema ≠ output schema ≠ route; explicit adapter registry; "One entry. A future binding is a future adapter — never an implicit reinterpretation of this one" | `research/semantic_decision_record.py` / `semantic_decision_codec.py` (S2-B-FU1; STATUS §S2-B-FU1) |
| Machine Price = deterministic ACCEPTED only; 4A exclusions IDENTITY_NOT_ACCEPTED / NO_NUMERIC_PRICE / NO_COMPARABLE_CURRENCY / UNKNOWN_CONDITION; **no unit-price inference** ("quantity / pack-size normalization and unit-price calculation remain deferred pending actual listing evidence and a separately approved responsibility") | `research/aggregation.py` `aggregate_listing_prices` (line 718); PLAN §16.4 "4A What stays out" |
| Reviewed Price = deterministic ACCEPTED + human-CONFIRMED semantic-eligible listings; confirmation overrides **ONLY the identity-authority gate**; origin preserved (DETERMINISTIC / HUMAN_CONFIRMED) | `research/aggregation.py:1389` `aggregate_reviewed_listing_prices`; STATUS "Human Review authority model" (frozen HUMAN-REVIEW) |
| V1 review eligibility (frozen FU3B): REJECTED + NO_EXPLICIT_MPN_EVIDENCE + (TITLE_TEXT \| SKU_FIELD), REJECTED + PARTIAL_MPN_ONLY; not ACCEPTED / UNDECIDED / MPN_MISMATCH | `research/matching.py:762` `is_human_review_eligible_assessment`; STATUS "Eligibility boundary" |
| Human review workflow: run-scoped `AiAssistedReviewCandidate`, CONFIRM/REJECT/UNDO, fail-closed candidate binding, no reviewer identity | `runs/ai_assisted_review.py` (frozen HUMAN-REVIEW) |
| Frozen 2.0 decision standard (verbatim): "MATCH: the candidate is very likely the same commercially comparable product on the supplied evidence."; "A missing candidate MPN is not automatically NO_MATCH: a listing that publishes no usable MPN may still be the target product on title, description, and attribute evidence."; "Exact MPN equality is strong evidence but is not the only evidence of commercial equivalence."; UNPROVEN-sales-unit rule: "if the comparison otherwise supports MATCH and the sales unit is critical to commercial comparability, report PACKAGING_QUANTITY (and/or BUNDLE) in missing_critical_attributes and return UNCERTAIN …" | `semantic/contract_v2.py` `SYSTEM_PROMPT_V2` (digest-pinned; re-read this session) |

## 1.2 The frozen V2 response — and the "six-field" question (Task A input fact)

The task refers to "the existing six-field semantic response." Verified fact:

* The **V1** semantic response is exactly **six** keys (decision, confidence,
  reason_code, matched_attributes, conflicting_attributes,
  missing_critical_attributes) — `semantic/contract.py`.
* The **V2** semantic response (the contract Prompt 2.1 extends) is exactly
  **seven** strict keys — the V1 six plus `conflict_classes` —
  `research/semantic_v2.py:1762` `_V2_RESPONSE_KEYS`; the parser rejects
  missing and extra keys; the frozen dataclass `SemanticMatchResponseV2`
  carries exactly those seven fields.
* The stale "six" persists in two documents: the `contract_v2.py` module
  docstring ("exactly the six bounded keys") and Q3-B3-FU2 §9.5 ("Output
  contract: 6 keys") — both contradict their own enforced 7-key shape. This
  is a documentation inconsistency only (DEFECT-3, §2); it has no
  behavioral effect and is recorded here so the six/seven distinction is
  never re-litigated.

**All Task A analysis below applies to the frozen 7-key V2 response.**

## 1.3 The 27-entry tier matrix and the 14-entry requirement table (re-extracted this session)

```
MATCH HIGH STRONG   -> AI_ASSISTED_COMPARABLE          (the only pricing-eligible semantic row)
MATCH HIGH LIMITED  -> NEEDS_REVIEW                    MATCH HIGH WEAK   -> NEEDS_REVIEW
MATCH MEDIUM *      -> NEEDS_REVIEW (x3)               MATCH LOW *       -> EXCLUDED_LOW_CONFIDENCE (x3)
NO_MATCH *          -> EXCLUDED_LOW_CONFIDENCE (x9)
UNCERTAIN HIGH STRONG/LIMITED -> NEEDS_REVIEW          UNCERTAIN HIGH WEAK -> EXCLUDED_LOW_CONFIDENCE
UNCERTAIN MEDIUM STRONG/LIMITED -> NEEDS_REVIEW        UNCERTAIN MEDIUM/LOW WEAK -> EXCLUDED_LOW_CONFIDENCE
UNCERTAIN LOW STRONG/LIMITED -> EXCLUDED_LOW_CONFIDENCE

Requirement (substate, primary signal) -> value:
V_EXACT/EXACT, V_NORMALIZED_EXACT/NORMALIZED_EXACT -> NOT_APPLICABLE
U1_TITLE_MPN/TITLE_MPN_TOKEN -> NOT_REQUIRED
U2_SKU_ONLY/SKU_EQUALS_TARGET -> NOT_APPLICABLE
U2_SKU_ONLY/SKU_NOT_TARGET -> REVIEWED_RELATION_AUTHORITY_REQUIRED
U3_PARTIAL_BOUNDARY/PARTIAL_BOUNDARY -> REVIEWED_RELATION_AUTHORITY_REQUIRED
U4_NO_MPN/NO_RELATION, U4_NO_MPN/EMPTY_MPN_FIELD -> NOT_APPLICABLE
U5_NEAR_MISS_MPN/NEAR_MISS_TRUNCATION, U5_NEAR_MISS_MPN/NEAR_MISS_SUBSTITUTION -> REVIEWED_RELATION_AUTHORITY_REQUIRED
C1/…, E1/…, E2/… -> NOT_APPLICABLE
```

Current production consequence (verified): every live V2 MATCH derives at
most NEEDS_REVIEW (dimension A ≤ LIMITED because `matched_facts=frozenset()`),
and no V2 tier is consumed by any pricing or presentation path
(`V2_AUTHORITY_QUALIFIED = False`; persist-only). Machine Price and Reviewed
Price are computed exclusively by the frozen deterministic + human-confirmed
paths (§1.1).

## 1.4 Qualification state (record, unchanged)

Corpus v1.0.0 (digest `2c37ba08…0b549`); primary live capture
`q3b-20261009T010312Z-amax` (43/43 parser-valid; 22 NO_MATCH / 21 UNCERTAIN /
0 MATCH; 11 ABSTAIN_ON_DEFINITE on the expected-MATCH set; MATCH recall 0/11;
all eight gates PASS; POLICY_PENDING under the DRAFT policy); fallback capture
deferred (endpoint unconfigured); Q3-B is REVIEWED / NOT APPROVED / NOT
FROZEN with its two runner defects corrected in Q3-B-FU1 (PENDING FINAL
REVIEW). The Prompt 2.1 design (Q3-B3-FU2, revision 2) is committed at the
starting SHA and awaits ChatGPT approval of its Q1–Q10. None of this is
changed by this document.

---

# 2. Exact architectural defect statements

## DEFECT-1 — Semantic MATCH carries no enforceable identity-resolution distinction (Task A blocker)

The frozen V2 response contract (7 strict keys, `research/semantic_v2.py:1762`)
represents **all** identity resolutions under the single decision value
`MATCH`, with **no field recording at which resolution the MATCH is
grounded**:

1. Exact part-number identity (U1 title MPN with identity wording; U2
   SKU-equals-target; 0001/0006/0038/0041 shapes),
2. Reviewed manufacturer-authorized equivalence (U5 near-miss +
   `MANUFACTURER_RELATION_AUTHORITY`; 0020 shape),
3. Family-level similarity (U3 consistent prefix + alignment; 0010 shape),
4. Description-level similarity (U4 no-MPN / U2 different-retailer-SKU +
   alignment; 0008/0014/0017/0035/0039 shapes),

all produce the same decision value. The `reason_code` is a weak advisory
discriminator (`MATCH_EXACT_PRODUCT_CONTEXT` / `MATCH_DESCRIPTION_AND_
ATTRIBUTES` / `MATCH_AUTHORIZED_IDENTIFIER_RELATION`) but it is **not an
input to the authority derivation** (`execution/semantic_decision_v2_
execution.py:407`: "the reason code and attribute lists are recorded
alongside but are not matrix inputs"), and the parser enforces only
reason/conflict coherence — never reason/substate coherence at the runtime
boundary (the provenance cross-check for `MATCH_AUTHORIZED_IDENTIFIER_
RELATION` exists in the QUALIFICATION evaluator only, not in the runtime).

The frozen authority derivation is keyed on the deterministic
substate/requirement table, not on the evidence's actual resolution:
`derive_authority_tier` (`research/semantic_authority_v2.py:2412`) consumes
`(decision, confidence, conflict_classes)` from the model plus
`(substate, primary signal, provenances, product-evidence profile)`. Two
consequences, both source-verified:

* **Within-substate distinctions have no downstream expression.** U1 with
  identity wording (part-number ground) and U1 with compatibility wording
  (description ground — the deterministic `COMPATIBILITY_WORDING` overlay
  signal is *recorded* in the assessment whenever the frozen listing title
  matches the bounded 4-token vocabulary, in any state —
  `semantic_authority_v2.py:540/821` — but *consumed by no derivation*)
  derive identical tiers. U4 full-alignment
  (description ground) and U4 generic-overlap MATCH (a 2.1 contract
  violation — no resolution grounded) derive identical tiers, because the
  model's `missing_critical_attributes` / `conflicting_attributes` are not
  derivation inputs.
* **The distinction is not recorded, replayable, or consumer-visible.** No
  persisted field states which resolution a given MATCH rests on; consumers
  (UI, review workflow, future pricing wiring) must re-guess it from the
  substate.

The fifth case — **unresolved product variants** — is *represented* safely
only as `UNCERTAIN` (the contract's answer, rows U-2/U-3 in the Q3-B3-FU2
design); the schema is **permissive** and will not reject a `MATCH` on
unresolved-variant evidence (0018-shape MATCH is schema-valid; it is caught
at qualification by the `commercial_sales_unit_safety` severity rule and by
the U5 requirement ceiling, not at the runtime boundary).

## DEFECT-2 — The frozen tier derivation is structurally sales-unit-blind; the future qualified state admits `MATCH + UNKNOWN_SALES_UNIT → pricing-eligible comparable` (Task B blocker)

Source-verified (re-proven this session on top of Q3-B3-FU2 §3.3):

1. The recorded sales-unit channel (`CandidateSalesUnitEvidenceV2`, required
   in every V2 input; live always UNAVAILABLE — `research/semantic_v2.py:903`)
   is **consumed by no authority symbol**: it is absent from
   `IdentityStateAssessmentV2`, `SemanticEvaluationV2`,
   `ProductEvidenceProfileV2` (whose dimension vocabulary *deliberately
   excludes* packaging — `semantic_authority_v2.py:1586`), the provenance
   classes, and `HumanReviewStateV2`.
2. A SU-EQ MATCH (packaging reported in `matched_attributes`) and a SU-UNK
   MATCH (packaging absent from all three lists) with identical decision,
   confidence, product-evidence quality, conflict classes, substate, and
   provenances derive **identical tiers and identical pricing eligibility**
   (`PRICING_ELIGIBLE_TIERS`, `semantic_authority_v2.py:2709`).
3. Packaging reaches the derivation **only negatively**: an ALWAYS_HARD
   `PACKAGING_QUANTITY`/`BUNDLE` class on a NO_MATCH → `HARD_CONFLICT`
   supersession → EXCLUDED.
4. **Exposure in the future qualified state** (once `V2_AUTHORITY_QUALIFIED
   = True` and dimension A can reach STRONG): a **silent multi-pack** — a
   4-pack/tray sold with no packaging signal anywhere — with a grounded
   identifier (including G1 exact part-number) and, for U2N/U3/U5 shapes, a
   reviewed relationship authority, derives `AI_ASSISTED_COMPARABLE` —
   pricing-eligible — **indistinguishable from a proven single unit**. No
   prompt wording, qualification gate, or matrix row can prevent this within
   the `SEMANTIC_AUTHORITY_V2_S2A_FU2` contract.
5. Today's protections are **state safeguards, not contract safeguards**:
   live dimension A ≤ LIMITED (caps every live MATCH at NEEDS_REVIEW) and
   `V2_AUTHORITY_QUALIFIED = False` (persist-only). Both can change — P3
   grounding + Q3-C qualification — **without touching the prompt, the
   matrix, the gates, or the corpus**. The frozen contract that would then
   govern pricing eligibility has no sales-unit input at all.

The frozen 4A contract adds no backstop on the semantic path: 4A performs
**no unit-price inference** (PLAN §16.4: "quantity / pack-size
normalization and unit-price calculation remain deferred pending actual
listing evidence and a separately approved responsibility") — an
unverified-unit price enters the statistic as-is once the identity gate is
passed.

## DEFECT-3 — Stale "six bounded keys" documentation (minor, recorded)

`semantic/contract_v2.py`'s module docstring and Q3-B3-FU2 §9.5 state "six
bounded keys" for the V2 output; the parser enforces seven. No behavioral
effect. Correction belongs to the implementation phase that next touches
those texts (documentation-only), not to this decision.

---

# 3. Task A — Executable MATCH semantics: option analysis

## 3.1 Can the existing response safely represent the five resolutions?

**Representation: yes, with a caveat; enforceability: no.**

* Resolutions 1–4 are representable as `decision = MATCH` + bounded reason
  code + attribute lists; the schema does not force a single identity
  semantics (that is the defect, not a validation failure).
* Resolution 5 (unresolved variants) is representable — and is the
  contract's *required* representation — as `UNCERTAIN`
  (`missing_critical_attributes = [PACKAGING_QUANTITY]` under SU-ENT; the
  named-dimension form otherwise).
* **Caveat:** the schema is permissive about *misuse*: a `MATCH` on
  unresolved-variant evidence (0018 shape) and a `MATCH` on generic overlap
  (0015/0043 shape answered MATCH) are both schema-valid. Enforcement of the
  corrected semantics lives at three existing layers — the prompt (2.1
  design, model-level), the qualification gates (corpus-level, incl. the
  CRITICAL sales-unit-safety severity), and the substate requirement
  ceilings (tier-level) — none of which is a *typed downstream distinction*
  a pricing consumer can rely on. That is the gap this task must close.

## 3.2 Option A — Keep MATCH a single advisory decision; enforce resolution-aware restrictions outside the model, with no new field

Meaning: the 7-key response is untouched; the Prompt 2.1 resolution language
(Q3-B3-FU2 §9.2, Q9) states the semantics at model level; the frozen
substate-requirement ceilings remain the only downstream enforcement; the
DEFECT-2 exposure is left to the separate Task B firewall.

| Dimension | Assessment |
| --- | --- |
| Frozen S2-A/S2-B/S2-C compatibility | Full — zero contract change; 2.0 and 2.1 replay byte-identical; corpus untouched |
| 11 expected-MATCH cases | Decision expectations unchanged (all remain MATCH defaults under 2.1); tiers unchanged from the Q3-B3-FU2 §3.5 future-state table |
| 7 ambiguous cases | Unchanged (0005/0009/0013/0043 keep both poles in-set; 0021/0023/0040 unchanged) |
| Corpus-contract conflicts | None |
| False-MATCH exposure | Model-level only (qualification-gated). Runtime boundary unchanged: the within-substate distinctions (U1 identity-vs-compatibility wording; U4 full-alignment vs generic-overlap MATCH) remain unenforceable and unrecorded; a contract-violating U4 MATCH on generic overlap would auto-price at `AI_ASSISTED` in the future state (subject only to the Task B firewall) |
| Required schema changes | None |
| Replay compatibility | Unchanged |
| Downstream pricing safety | No change to DEFECT-2 (R14 persists); the Task B guard must carry 100% of the pricing safety, and the tier/summary presentation will still show `AI_ASSISTED_COMPARABLE` for unproven-unit MATCHes (see §4.6, Option A weakness) |
| Migration requirements | None |
| Test/qualification implications | Additive only: the sales-unit-blindness pin (Q3-B3-FU2 T2) becomes a recorded documented property; qualification (2.1 + Q3-C) proceeds exactly as designed |

**Verdict:** Option A is the zero-cost baseline and is *necessary* (the
prompt language and the qualification gates are part of the recommendation),
but alone it does **not** create the enforceable downstream distinction the
task requires: restrictions "outside the model" that change tier behavior
are, by definition, authority-contract changes (Option B's mechanism).
Option A without B leaves DEFECT-1 open at the consumer boundary.

## 3.3 Option B — An independently derived identity-resolution (evidence-authority) field at a separately versioned contract boundary

Meaning: a **new versioned authority contract** — `SEMANTIC_AUTHORITY_V2_
S2A_FU3` (new token on the frozen binding's authority axis; the S2-B-FU1
architecture explicitly reserves "a future binding is a future adapter") —
adds, **purely and deterministically**:

1. **`IdentityResolutionBoundV2`** ∈ {`PART_NUMBER`, `FAMILY_DESCRIPTION`,
   `DESCRIPTION`, `NONE`}, derived from the *recorded input only*
   (substate + relationship signals — including the already-recorded
   `COMPATIBILITY_WORDING` overlay — + context provenances). The model's
   output never sets it; it is the **maximum resolution the recorded
   evidence can support** for an equivalence MATCH. Exact table in §5.2.
2. **`SalesUnitAuthorityV2`** ∈ {`PROVEN_EQUIVALENT`, `UNPROVEN`,
   `CONTRADICTED`}, derived from the *recorded* sales-unit channel +
   target-side unit evidence (specification in §4.7) — the Task B input.
3. A **restrict-only ceiling** `CEILING_SALES_UNIT_NOT_PROVEN` on the
   *automatic* tier (Task B, §4.3).
4. Both values recorded as **derived audit snapshots** in the V2 record
   under the FU3 binding (replay re-derives and proves agreement — the
   existing S2-B replay discipline extended per binding).

The frozen `SEMANTIC_AUTHORITY_V2_S2A_FU2` derivation is **byte-unchanged**
(the module gains new functions/token; old token's semantics and its tests
are untouched — see §6.5 for the replay-dispatch requirement).

| Dimension | Assessment |
| --- | --- |
| Frozen S2-A/S2-B/S2-C compatibility | S2-B: native fit (versioned binding axis; per-binding adapter dispatch). S2-C: **no input or output schema change** — the derivation consumes only already-recorded data. S2-A: **amended by a new version** (post-freeze; approval-gated). The exact conflict with AD-066 is identified in §3.6 (not silently resolved) |
| 11 expected-MATCH cases | Decision level: unchanged (all remain MATCH; labels untouched). Field level: each case's record gains its bound — PART_NUMBER (0001/0006/0020/0038/0041), FAMILY_DESCRIPTION (0010), DESCRIPTION (0008/0014/0017/0035/0039). Tier level (future qualified state): all 11 have sales_unit UNAVAILABLE → UNPROVEN → automatic tier capped at NEEDS_REVIEW under FU3 (vs `AI_ASSISTED` under S2A_FU2 for the U1/U2E/U4 shapes) — a tier-level change the corpus does **not** label (labels are decisions, not tiers) |
| 7 ambiguous cases | Decision level: unchanged (all acceptable sets still contain the 2.1 defaults). Field level: 0005 PART_NUMBER; 0009/0013/0043 DESCRIPTION; 0021/0023/0040 NONE (a MATCH on a NONE bound is exactly the contract violation the labels already exclude from their sets) |
| Corpus-contract conflicts | **None.** No label asserts a tier or a resolution; no label is moved. The only conflict is with the S2-A **acceptance text** (AD-066), identified in §3.6 |
| False-MATCH exposure | Decision level unchanged (qualification-gated). Pricing level: a contract-violating generic-overlap U4 MATCH can no longer auto-price while the unit is unproven (ceiling) — the exposure narrows to human-confirmed judgment, which is the frozen boundary |
| Required schema changes | None (input v1 / output v1 / envelope v1 unchanged; new derived fields exist only in the payload of FU3-bound records) |
| Replay compatibility | Per-binding dispatch: V1 records and 2.0 V2 records (both bound to S2A_FU2) replay under the unchanged old derivation — byte-identical; FU3-bound records replay under the new derivation; cross-binding reinterpretation refused (existing discipline) |
| Downstream pricing safety | DEFECT-2 closed at the derivation level (the tier itself can no longer be pricing-eligible with an unproven unit); DEFECT-1 closed as a typed, replayable, consumer-visible distinction |
| Migration requirements | **None** — the record is an opaque codec payload; the runs model, migration 0012, and the service are untouched |
| Test/qualification implications | New FU3 contract test suite (derivation tables; restrict-only proof; per-binding replay; old-token invariance pins). The eight gates and the DRAFT policy are unchanged (they measure the model, not the tier). Qualification of 2.1 proceeds as designed; the firewall is orthogonal to the recall/precision arithmetic |

**Verdict:** Option B is the only option that makes the distinction
*enforceable downstream* while preserving deterministic identity ownership.
Its cost is a post-freeze, versioned, approval-gated authority-contract
amendment with one exact acceptance-text conflict to ratify (§3.6).

## 3.4 Option C — Restrict MATCH to specific-product-identity evidence; classify weaker matches as UNCERTAIN

Meaning: a prompt/contract change permitting MATCH only on part-number
grounds (G1 exact identifier; G2-auth reviewed relation); family+description
(U3) and description (U4/U2N) alignment → UNCERTAIN.

| Dimension | Assessment |
| --- | --- |
| Frozen S2-A/S2-B/S2-C compatibility | S2-B/S2-C mechanically compatible (same decision vocabulary). **S2-A: direct conflict** — AD-066 (PLAN §26.22) required behavior 1: "U4_NO_MPN + semantic MATCH + HIGH confidence + strong approved product evidence + no HARD conflict + no REVIEWABLE conflict => AI_ASSISTED_COMPARABLE is PERMITTED" and behavior 2: "U4 does NOT require MANUFACTURER_RELATION_AUTHORITY." The entire S2-A-FU1 correction exists "to stop re-conservatizing exactly the no-identifier description match" (STATUS S2-A-FU1). Option C makes U4/MATCH a non-outcome, nullifying the frozen correction |
| 11 expected-MATCH cases | **6 of 11 become unsupported**: 0008/0035/0039 (U2N description ground), 0010 (U3 family+description ground), 0014/0017 (U4 description ground) expect MATCH; the Option C contract default for all six is UNCERTAIN → 6 ABSTAIN_ON_DEFINITE (severity REVIEW) on requalification; MATCH recall falls to 5/11 = **0.4545 < the DRAFT recall floor 0.90** → `BELOW_THRESHOLD`: qualification cannot pass on the frozen corpus |
| 7 ambiguous cases | 0005 (U1, {MATCH, UNCERTAIN}) — PART_NUMBER bound, MATCH stays in-set (no change); 0009 (U2N, {MATCH, UNCERTAIN}) and 0043 (U4, {MATCH, UNCERTAIN}) — contract default UNCERTAIN (in-set; the MATCH pole dies); 0013 (U4, {UNCERTAIN, MATCH}) — contract default UNCERTAIN now matches the *expected* pole (in-set; the MATCH pole dies); 0021/0023/0040 — unchanged. Three poles "improve" only by destroying the six authoritative MATCH labels |
| Corpus-contract conflicts | **Six CORPUS_CONTRACT_CONFLICT cases** (0008/0010/0014/0017/0035/0039) — precisely the boundary condition (i) Q3-B3-FU2 §7.5 pre-registered as the reading that WOULD conflict. Resolution would require class-A/D label governance ("the product behaviour requirement intentionally changed") — a far heavier lift than B, and it moves evaluation truth to suit an implementation policy, which CLAUDE.md forbids absent an explicit product decision the task does not make |
| False-MATCH exposure | Decision level: reduced (fewer MATCHes). **But DEFECT-2 is NOT closed**: a G1 exact-identifier MATCH on a silent multi-pack (A9) is still part-number-grounded and still pricing-eligible in the future state. Option C fixes the weakest identity claim and leaves the strongest one's unit question open |
| Required schema changes | None (vocabulary unchanged) — the change is prompt semantics + label governance |
| Replay compatibility | 2.0 records stay byte-replayable, but the meaning of a stored description-ground MATCH (e.g., a future 0013-pole MATCH) shifts under the new contract — the silent reinterpretation the house rules forbid |
| Downstream pricing safety | Partial, misdirected (see false-MATCH row) |
| Migration requirements | None |
| Test/qualification implications | Requalification infeasible under the frozen corpus + DRAFT policy; the frozen 2.0 prompt text is itself contradicted ("a listing that publishes no usable MPN may still be the target product on title, description, and attribute evidence") |

**Verdict: REJECTED** — it conflicts with frozen acceptance criteria on four
independent surfaces (AD-066 required behaviors; the frozen 2.0 decision
standard; six corpus labels; the DRAFT recall floor), and it does not close
the actual pricing defect for the strongest-identity shape. Per the task, the
conflicts are identified here, not resolved by moving the criteria.

## 3.5 Task A comparison summary

| | A (status quo + prompt) | B (derived field, versioned boundary) | C (MATCH = part-number only) |
| --- | --- | --- | --- |
| Enforceable downstream resolution distinction | **No** (substate ceilings only) | **Yes** (typed, replayed, consumer-visible) | Partial (decision-level), pricing defect survives |
| Frozen-contract conflict | None | One, identified (§3.6), versioned + ratified | Four, unresolvable without relabeling |
| 11 / 7 case impact | None | Field + future-tier only; decisions untouched | 6 labels unsupported; 3 poles die |
| Migration | None | None | None (but governance events) |
| Replay | Unchanged | Per-binding, old records byte-identical | Silent semantic shift on old records |
| Smallest coherent | Yes (but incomplete) | **Yes (complete)** | No (over-correction + under-fix) |

## 3.6 The exact frozen-criteria conflict Option B carries (stated, not resolved)

Under `SEMANTIC_AUTHORITY_V2_S2A_FU3`, the S2-A-FU1/FU2 auto-authority
behaviors become **conditional on sales-unit authority**:

* AD-066 required behavior 1 (PLAN §26.22): "U4 + MATCH/HIGH + STRONG + no
  HARD + no REVIEWABLE => AI_ASSISTED_COMPARABLE is PERMITTED" — under FU3
  this reads "…is PERMITTED **when `SalesUnitAuthorityV2` is
  `PROVEN_EQUIVALENT`**; otherwise the automatic tier is capped at
  NEEDS_REVIEW (`CEILING_SALES_UNIT_NOT_PROVEN`)." The U4 relationship
  requirement (NOT_APPLICABLE) is **not** changed.
* The same conditioning applies to the U1 (NOT_REQUIRED) and U2E
  (NOT_APPLICABLE) auto-authority behaviors pinned by the frozen S2-A-FU2
  test nodes (`TestU1AutoAuthorityWithoutRelationRequirement`, the U2E
  auto-tier node, `TestU4AutoAuthority`).
* Those frozen nodes remain **valid and untouched under the old binding**
  (the S2A_FU2 derivation is byte-unchanged); FU3 ships its own node set.
  No frozen test is modified, weakened, or re-pointed.

This is the **only** acceptance-criteria conflict in the recommendation. It
is a post-freeze amendment to the S2-A line and requires the explicit
approval AD-Q3B4-4 (§10).

---

# 4. Task B — Sales-unit pricing firewall: option analysis

## 4.1 The invariant

The target architecture must prevent, **structurally** (not by current state):

```
MATCH + UNKNOWN_SALES_UNIT  →  pricing-eligible comparable
```

even when **all four** of the following hold simultaneously:

1. `V2_AUTHORITY_QUALIFIED = True` (route qualified under an approved policy),
2. ProductEvidenceQuality = STRONG (P3 grounding live),
3. the model reports HIGH confidence,
4. a manufacturer relationship has been reviewed (requirement satisfied;
   NM-2 ceiling cleared).

Human-confirmed overrides must **remain** explicit and auditable. The current
qualification flag (`False`) and the current LIMITED evidence quality are
**not** permanent safety controls and may not be cited as the contract.

## 4.2 Option A — Fail-closed pricing-consumer guard (Q3-B3-FU2 P4-b)

A new rule at the **consumer boundary** (the first V2 pricing-eligibility
wiring, which does not exist today): a V2-derived candidate enters a price
statistic only if `tier ∈ PRICING_ELIGIBLE_TIERS` **and**
`SalesUnitAuthorityV2 == PROVEN_EQUIVALENT` **or** the candidate carries a
recorded human CONFIRMED overlay; otherwise it is excluded with a recorded
reason. S2-A stays byte-frozen.

* **Invariant check:** PASSES — the guard fails closed on UNPROVEN at the
  pricing boundary regardless of tier, qualification, quality, confidence,
  or relationship authority.
* **Strengths:** no frozen-contract amendment; protects even S2A_FU2-bound
  records; deterministic input (the recorded channel).
* **Weaknesses (source-level):** (i) the tier — and therefore the frozen
  summary wording "Pricing-eligible comparable listings: N" (amendment 3,
  tier-driven) and the `AI_ASSISTED_COMPARABLE` badge — still presents an
  unproven-unit MATCH as pricing-eligible while the statistic silently
  excludes it: a presentation/arithmetic divergence inside the frozen
  wording contract; (ii) safety by **consumer convention** — every future
  pricing consumer must implement the guard; a consumer that forgets it
  re-opens the defect; (iii) DEFECT-1's resolution distinction is still not
  recorded.

## 4.3 Option B — Sales-unit authority input + restrict-only ceiling in the derivation (Q3-B3-FU2 P4-a)

A versioned S2-A amendment (FU3) adds `SalesUnitAuthorityV2` (§4.7) as a
derivation input and a **restrict-only ceiling** `CEILING_SALES_UNIT_
NOT_PROVEN`: an automatic `AI_ASSISTED_COMPARABLE` is capped at
`NEEDS_REVIEW` when the unit is UNPROVEN — mirroring the frozen
`CEILING_NEAR_MISS_SUBSTITUTION_WITHOUT_RELATION_AUTHORITY` pattern
("the AI may still return MATCH/HIGH; it simply cannot auto-price").

* **Invariant check:** PASSES — in the fully-qualified future state, the
  derivation itself can no longer output a pricing-eligible automatic tier
  with an unproven unit, under any (quality, confidence, relationship,
  substate) combination. The frozen import-time invariant
  "NEEDS_REVIEW must never count as pricing-eligible"
  (`semantic_authority_v2.py:2732`) then does the rest; tier, badge, summary
  wording, and statistic all agree (the candidate counts under *market
  evidence*, never under *pricing-eligible*).
* **Scope limits (deliberate, matching the frozen pattern):** the ceiling
  fires **only** on the automatic AI tier. It does not fire on
  `MACHINE_VERIFIED` (the deterministic path never consults the semantic
  layer — 4A behavior byte-unchanged), on `HARD_CONFLICT` (precedence
  already excludes), or against the `HUMAN_CONFIRMED` overlay (precedence
  HARD_CONFLICT > HUMAN_CONFIRMED > AI is unchanged; a human may confirm a
  ceiling-capped candidate — explicit, run-scoped, persisted, auditable).
  A **published** incompatible unit is `CONTRADICTED`, not `UNPROVEN`: the
  absolute rule (N-1) decides NO_MATCH at the decision level and
  `HARD_CONFLICT` supersession excludes it from human confirmation — the
  frozen semantics, unchanged.
* **Strengths:** one structural fix at one place; presentation and
  arithmetic cannot diverge; replayable per binding.
* **Weaknesses:** post-freeze amendment (approval-gated; the §3.6 conflict
  must be ratified); if FU3 slips, the invariant has no derivation-level
  protection until it lands.

## 4.4 Option C — Packaging extraction (P2) followed by independently validated sales-unit comparison

The extractor publishes the packaging field; the OBSERVED channel fills with
bounded provenance (kind + quantity + raw detail + source — the contract
already represents it); the frozen absolute rule then catches published
incompatible units at the decision level (NO_MATCH), and proven
`SINGLE_UNIT` observations close the unit question (SU-EQ) where pages
publish packaging.

* **Invariant check:** **FAILS alone** — by definition, a *silent*
  multi-pack publishes nothing: the channel stays UNAVAILABLE → UNPROVEN →
  the fully-qualified MATCH still auto-prices. P2 shrinks the UNPROVEN
  population (possibly to a small residual on the live page population); it
  cannot guarantee the invariant.
* **Status:** a load-bearing **mitigation** (Q3-B3-FU2 §11: "P2 is now
  load-bearing for future pricing safety"), not the firewall.

## 4.5 Option D — Combined: derivation ceiling (B) + mandatory consumer guard (A) + extraction (C)

* **Invariant check:** PASSES with **two independent structural layers**
  (derivation-level and consumer-level) plus a population-shrinking layer:
  1. FU3 ceiling: the automatic tier is not pricing-eligible while UNPROVEN
     (tier, badge, summary, statistic agree);
  2. Consumer guard: the first V2 pricing wiring excludes any candidate
     without `PROVEN_EQUIVALENT` or a recorded human CONFIRMED overlay —
     fail-closed, recorded reason; this layer also protects S2A_FU2-bound
     2.1 records if FU3 lands after P1, and defends against future
     consumer-side regressions;
  3. P2 extraction: converts OBSERVED packaging into decision-level
     absolute-rule NO_MATCHes (published incompatible) or `PROVEN_
     EQUIVALENT` (published single unit) — the unproven residual is
     monitored in live audits (R1/R14 watch items).
* **Human-confirmed override:** preserved exactly at the frozen boundary —
  the overlay is explicit (run-scoped candidate state), persisted (ledger +
  review-candidate rows), auditable (confirm/reject/undo actions), and the
  *only* path by which an unproven-unit semantic candidate reaches a price
  statistic. The reviewer sees the listing page and the recorded
  sales-unit state; the firewall does not remove the human's judgment, it
  removes the machine's silent assumption.

## 4.6 Task B comparison summary

| Invariant conditions (qualified + STRONG + HIGH + reviewed relation) | A (guard) | B (ceiling) | C (extraction) | D (combined) |
| --- | --- | --- | --- | --- |
| Silent multi-pack, G1 exact identifier (A9) | Blocked at consumer; tier still displays AI_ASSISTED (summary/statistic divergence) | **Blocked at derivation; consistent presentation** | Not blocked (channel UNAVAILABLE) | **Blocked twice; consistent presentation** |
| Silent multi-pack, U4 description ground | Blocked at consumer | Blocked at derivation | Not blocked | Blocked twice |
| Reviewed-relation U3/U5 with unproven unit | Blocked at consumer | Blocked at derivation | Not blocked | Blocked twice |
| Published incompatible unit (0032/0033/0034) | n/a — decision-level NO_MATCH (frozen) | n/a — HARD_CONFLICT (frozen) | Catches earlier (OBSERVED) | Frozen behavior + earlier catch |
| Human-confirmed override | Preserved (guard admits overlay) | Preserved (ceiling is automatic-tier-only) | Preserved | Preserved |
| Current production behavior change | None (no V2 consumer exists) | None (old token unchanged; live tier already ≤ NEEDS_REVIEW) | Extraction-phase scope, separate | None |

**Selection: Option D.** Option B alone would satisfy the invariant, but the
consumer guard is the *atomic precondition* for the (future) first V2 pricing
wiring regardless of FU3 timing, and it is what makes the invariant hold for
S2A_FU2-bound records in the interim; Option C alone fails the invariant;
Option A alone leaves the presentation/arithmetic divergence and
consumer-convention fragility. D is the smallest architecture that satisfies
the invariant structurally and consistently.

## 4.7 `SalesUnitAuthorityV2` — exact bounded derivation (FU3 specification)

Pure function over the **recorded** V2 input (zero-live, replayable):

* Target commercial unit: the single unit of the requested part, **unless**
  target-side supplied evidence (the requested description, or a reviewed
  target context) explicitly establishes a different form (the frozen 2.1
  default — Q3-B3-FU2 Q1(a)/R8).
* Channel `UNAVAILABLE` → **`UNPROVEN`** (never `PROVEN_EQUIVALENT`; absence
  is a recorded absence — frozen S2-C-FU1 semantics).
* Channel `OBSERVED SINGLE_UNIT` → **`PROVEN_EQUIVALENT`** against the
  default single-unit target (or CONTRADICTED if the target-side evidence
  establishes a pack/tray/bundle).
* Channel `OBSERVED PACK_QUANTITY n` → **`PROVEN_EQUIVALENT`** iff
  target-side evidence establishes the same pack `n`; otherwise
  **`CONTRADICTED`**.
* Channel `OBSERVED TRAY_OR_FACTORY_PACK` / `BUNDLE` → **`CONTRADICTED`**
  against the default single-unit target (PROVEN_EQUIVALENT only with
  matching target-side established kind + quantity).
* `CONTRADICTED` ⇒ the frozen absolute rule applies at the decision level
  (NO_MATCH + PACKAGING_QUANTITY/BUNDLE; HARD_CONFLICT supersession in the
  tier; not human-confirmable — all frozen semantics, unchanged).
* `UNPROVEN` ⇒ the restrict-only ceiling fires on the automatic tier.
* **Never** an input: model confidence, model `matched_attributes`
  (a model claim of "packaging matched" is not independent verification),
  price, availability, or any other commercial fact (frozen never-infer
  rule).
* Derivation source: the published structured field with provenance
  (`CandidateEvidenceSourceV2`) — i.e., the same evidence class the prompt
  labels; raw-text cues remain model-interpreted at the decision level
  (R2), which is why the guard/ceiling treat only the OBSERVED channel as
  independent verification.

## 4.8 Why the current state is not the safety contract (recorded)

`matched_facts=frozenset()` (live ≤ LIMITED) and `V2_AUTHORITY_QUALIFIED =
False` are **state** (AD-071 documented limitation; S2-C boundary). P3
(grounding) and Q3-C (qualification) each change one of them **without
touching the prompt, the matrix, the gates, or the corpus**. The invariant
of §4.1 is therefore a *contract* requirement of the target architecture —
satisfied by D's derivation ceiling + consumer guard — and may not be
argued from today's state in any approval rationale.

---

# 5. Recommended target architecture (Task C)

## 5.1 Overview

```
MODEL LEVEL      Prompt 2.1 (Q3-B3-FU2 design, Q1–Q10 gated): states the
                 resolution of every ground; MATCH asserts nothing beyond it;
                 price-comparability non-assertion; absolute rule; SU-ENT
                 blocks. (Output schema FROZEN at 7 keys.)
                  │  recorded 7-key response
AUTHORITY LEVEL  S2-A-FU3 (new versioned token; approval-gated):
                 ├─ IdentityResolutionBoundV2 (deterministic, input-only)   [Task A: Option B]
                 ├─ SalesUnitAuthorityV2 (deterministic, recorded channel)  [Task B: Option D.2]
                 ├─ CEILING_SALES_UNIT_NOT_PROVEN (restrict-only, auto tier)[Task B: Option D.1]
                 └─ S2A_FU2 derivation BYTE-UNCHANGED (old token replays)
                  │  derived snapshots in the V2 record (per-binding replay)
QUALIFICATION    Q3-C: 2.1 captures (both pinned models), eight gates,
LEVEL            DRAFT→approved policy, recall/precision floors. The firewall
                 is orthogonal to model qualification (it measures tiers, not
                 the model).
PRICING LEVEL    First V2 pricing wiring (future phase W1): MANDATORY
                 fail-closed consumer guard — PROVEN_EQUIVALENT or recorded
                 HUMAN_CONFIRMED overlay or excluded (recorded reason).
                 Atomic with the wiring; no gap.
OBSERVABILITY    P2: packaging extraction fills the OBSERVED channel over
LEVEL            time (decision-level absolute rule + PROVEN_EQUIVALENT),
                 shrinking the UNPROVEN population; silent residual → live
                 audit watch (R1/R14).
```

Deterministic identity ownership is preserved at every level: the two new
derivation fields are pure functions of **recorded input** (deterministic
substate/signals/provenances; published channel with source label). The model
never sets them, never self-reports resolution, and its claims are checked
against the bounds (qualification severity; watch items), not trusted.

## 5.2 Task A selection — Option B (with Option A's discipline)

MATCH remains a **single advisory decision** (A's discipline; the 2.1 prompt
states the resolution; the LLM is never the sole authority for exact
identity — CLAUDE.md frozen rule). The enforceable downstream distinction is
the **independently derived `IdentityResolutionBoundV2`** at the **S2-A-FU3
versioned boundary** (B's mechanism). Option C is rejected with the exact
conflicts of §3.4.

Exact derivation table (recorded input only; `COMPAT` = the deterministic
`COMPATIBILITY_WORDING` overlay signal):

| Deterministic context | Bound |
| --- | --- |
| DETERMINISTIC_VERIFIED (V_EXACT / V_NORMALIZED_EXACT) | `PART_NUMBER` (no AI involved) |
| U1 + not COMPAT | `PART_NUMBER` (exact title MPN in identity wording) |
| U1 + COMPAT | `DESCRIPTION` (the title token is not an identifier ground; the decision rests on product evidence) |
| U2 + SKU_EQUALS_TARGET | `PART_NUMBER` (frozen-2A deterministic fact) |
| U2 + SKU_NOT_TARGET | `DESCRIPTION` (the SKU is neither conflict nor ground) |
| U3_PARTIAL_BOUNDARY | `FAMILY_DESCRIPTION` (the prefix is never the complete number it truncates) |
| U4_NO_MPN (both signals) | `DESCRIPTION` (no identifier question exists) |
| U5 + MANUFACTURER_RELATION_AUTHORITY present | `PART_NUMBER` (for the specifically related part — the labeled authority is the ground) |
| U5 + no manufacturer relation authority (incl. customer-retrieval-only) | `NONE` (a MATCH on this bound is the CRITICAL false-MATCH shape 0018/0022) |
| DETERMINISTIC_CONFLICT / UNEVALUABLE | `NONE` (no semantic entry) |

Completeness note: the `COMPATIBILITY_WORDING` overlay is recorded in any
state whose title matches the 4-token vocabulary (frozen derivation), but it
is only *effective* on the bound in U1 (the one state whose bound is
otherwise `PART_NUMBER`): in U2/U3/U4 the bound is already below
part-number level, and in U5 it is fixed by the presence or absence of
`MANUFACTURER_RELATION_AUTHORITY`. The derivation table above is complete
over the full substate × primary-signal vocabulary (fail-closed lookup,
import-self-checked — §6.1).

Consumers may then rely on: **tier + bound + unit authority**, all recorded,
all replay-verified. The within-substate gaps of DEFECT-1 (U1 wording; U4
alignment compliance) become *visible* (bound + recorded missing/conflicting
lists) and, for the pricing path, *consequence-free* while the unit is
UNPROVEN (ceiling). A U4 generic-overlap MATCH that the model should not
have made remains a qualification/watch matter (R11/R13) — its pricing
consequence is already blocked by the unit ceiling in every live shape
(today's channel is always UNAVAILABLE).

## 5.3 Task B selection — Option D

Per §4: the FU3 derivation ceiling (primary structural layer) + the
mandatory fail-closed consumer guard at the first V2 pricing wiring
(atomic precondition; protects S2A_FU2-bound interim records) + P2
packaging extraction (independent observability phase). Human-confirmed
overrides remain the explicit, persisted, auditable exception (§4.7/§4.3).
Nothing about the deterministic Machine Price path, the V1 Reviewed Price
path, or 4A is touched (Task C item 7).

## 5.4 The four change buckets (Task C deliverable split)

### (1) Changes possible WITHOUT amending frozen contracts

* **Documentation/decision record only:** this document; the DEFECT-2
  sales-unit-blindness property pinned as a *documented property* in the 2.1
  test plan (Q3-B3-FU2 T2 — additive new test, no behavior change); the
  DEFECT-3 docstring correction in whatever phase next touches
  `contract_v2.py`.
* **Prompt 2.1 itself** is a *new versioned contract* (2.0 stays byte-frozen;
  the binding's prompt axis moves; the S2-C-FU1 versioning discipline: a
  version bump of an unshipped-line contract is not an amendment of the
  frozen 2.0) — approved via the Q3-B3-FU2 Q1–Q10, which this document does
  not answer.
* **The consumer guard rule** at the (not-yet-existing) first V2 pricing
  boundary: no frozen contract defines that boundary today (V2 is
  persist-only; the S2-C MUST-NOT list says the wiring comes later), so the
  guard is a new bounded rule of the future wiring phase — specified here,
  approval-gated with the wiring. It is deliberately written so it holds
  *even if* S2-A-FU3 is delayed.

### (2) Changes requiring NEW VERSIONED CONTRACTS (each separately approval-gated)

* **S2-A-FU3 authority contract** (new token `SEMANTIC_AUTHORITY_V2_S2A_
  FU3`): the `IdentityResolutionBoundV2` derivation + derived snapshot;
  the `SalesUnitAuthorityV2` derivation + derived snapshot; the
  `CEILING_SALES_UNIT_NOT_PROVEN` restrict-only automatic-tier ceiling;
  per-binding replay dispatch; the old-token invariance pins. Ratification
  of the exact AD-066 conditioning conflict (§3.6) is required
  (AD-Q3B4-4).
* **The 2.1 production binding decision** (AD-Q3B4-5): register 2.1 under
  `("V2","2.1",1,1,"SEMANTIC_AUTHORITY_V2_S2A_FU3")` if FU3 is approved
  first (recommended), or under `("V2","2.1",1,1,"SEMANTIC_AUTHORITY_V2_
  S2A_FU2")` per the Q3-B3-FU2 design if FU3 slips — with the consumer
  guard then carrying the invariant alone until FU3 lands.
* **The W1 wiring-phase contract** (future): the pricing-eligibility
  predicate with the atomic guard (§4.2), the recorded exclusion reason
  vocabulary, and the summary-wording agreement (tier-driven wording stays
  frozen; the guard operates on the statistic).

### (3) Changes requiring NEW CORPUS GOVERNANCE

* **None required by either blocker.** The firewall and the resolution
  bound change no label: the corpus labels decisions/conflicts/missing
  dimensions (never tiers or resolutions); all 56 labels remain supportable
  (§7). `label_revisions` stays empty; corpus 1.0.0 stays bound to the 2.0
  binding; the planned 1.1.0 binding-only re-seal (Q3-B3-FU2 Q5, all 56
  per-case digests byte-identical) is unaffected by this decision.
* **Future (P2's own governance, separate phase):** reviewer-labeled
  OBSERVED-packaging cases (raw-cue A5 variants; OBSERVED single-unit A4
  variants) enter a later corpus version with its own digest and label
  governance. The **silent-multi-pack shape remains unlabelable by
  construction** (the payload cannot contain the cue that would make it
  distinguishable — Q3-B3-FU2 A3/A9); it stays a live-audit watch item +
  the structural firewall, never a corpus label.

### (4) Changes requiring QUALIFICATION AND DEPLOYMENT APPROVAL

* **Q3-C:** DRAFT→approved policy decision; 2.1 captures on **both** pinned
  models (the deferred fallback capture completes in this window); the eight
  gates; the recall/precision floors. Conditioned on the FU3 disposition
  (AD-Q3B4-6).
* **Authority promotion:** `V2_AUTHORITY_QUALIFIED = True` — only after Q3-C
  passes and (for any FU3-bound production records) FU3 is frozen.
* **W1 + deployment:** the first V2 pricing wiring ships the guard
  atomically; deployment is an explicit, separate approval (the S2-C
  MUST-NOT-deploy discipline continues until an explicitly reviewed
  deployment phase).

## 5.5 Ordering constraints (binding on the phase plan, §9)

* **(i)** The consumer guard ships **atomically** with the first V2 pricing
  consumer — no window in which a V2-derived tier is pricing-readable without
  the unit check.
* **(ii)** Q3-C's qualification decision is **conditioned on the FU3
  disposition** (Q3-B3-FU2 §15 item 4, ratified here as AD-Q3B4-6).
* **(iii)** **P3 (grounding) is the switch that activates the exposure
  table.** If P3's production effect lands before FU3's ceiling + the guard,
  the R14 exposure is live. Therefore P3's production effect is conditioned
  on FU3 (or at minimum the guard) being in force.
* **(iv)** P2 is independent and may land at any time; it strictly shrinks
  the UNPROVEN population and adds decision-level catches.

## 5.6 What the recommendation does NOT do (invariance list)

* No in-place modification of the frozen S2A_FU2 derivation, its tables, its
  token, or its tests (per-binding dispatch instead — §6.5).
* No change to the 2.0 prompt, its digest, corpus 1.0.0, or the committed
  no-capture baseline reports.
* No change to the V1 path (eligibility, prompt 1.1, review candidates,
  confirm/reject/undo, Reviewed Price arithmetic, origins).
* No change to 4A Machine Price (deterministic only; no unit-price
  inference — the frozen deferral stands).
* No corpus label change; no threshold/policy change (DRAFT stays DRAFT);
  no migration; no deployment; no authority promotion; no model call.
* No model self-reporting of resolution or unit equivalence (deterministic
  ownership).
* No widening of the semantic response schema (7 keys stay 7 keys under all
  bindings).

---

# 6. Contract amendment requirements

## 6.1 S2-A-FU3 (the versioned authority-contract amendment)

Bounded CONTRACT-ONLY phase (S2-A precedent: no wiring, no deployment;
production behavior identical to the starting SHA because no live path
references the new token yet). Requirements:

1. New token `SEMANTIC_AUTHORITY_V2_S2A_FU3`; the S2A_FU2 module surface
   (tables, functions, token, semantics) is **byte- and behavior-unchanged**
   (file-level invariance pin for the frozen token's derivation; the old
   tests pass untouched).
2. `IdentityResolutionBoundV2` + `derive_identity_resolution_bound(
   assessment_v2)` — the §5.2 table, fail-closed lookup (unknown
   combinations never gain a bound), import-self-checked completeness over
   the substate/signal vocabulary, immutable data (S2-A-FU1 blocker-2
   pattern).
3. `SalesUnitAuthorityV2` + `derive_sales_unit_authority(case_v2)` — the
   §4.7 specification, fail-closed, over the recorded channel + target-side
   unit evidence only.
4. The FU3 tier derivation = the frozen S2A_FU2 derivation **plus** the
   restrict-only ceiling `CEILING_SALES_UNIT_NOT_PROVEN` (fires only on
   `AI_ASSISTED_COMPARABLE` + `UNPROVEN`; never lifts; interaction with the
   existing ceilings is by the frozen "restrict only, never lift" order;
   HARD_CONFLICT supersession stays last; the human overlay precedence is
   unchanged and applies above the AI path as with the NM-2 ceiling).
5. Derived snapshots: FU3-bound V2 records carry the bound + unit authority
   + the FU3 tier + fired rules; replay re-derives and proves agreement
   (existing discipline).
6. Tests: new FU3 node set (derivation tables incl. every U-row and the U5
   authority/no-authority split; the restrict-only proof incl. "ceiling
   cannot be bypassed by STRONG + HIGH + reviewed relation + qualified
   route" — the §4.1 invariant as a unit test; per-binding replay; old-token
   invariance; immutability; no-model-claim inputs — a model
   `matched_attributes` packaging claim changes nothing).
7. **Ratification of the §3.6 AD-066 conditioning conflict** (AD-Q3B4-4) is
   the approval entry; the FU1-era "corrected in place" test pattern does
   NOT apply (post-freeze: the old nodes stand under the old token).

## 6.2 The 2.1 binding decision

Per §5.4(2)/AD-Q3B4-5. If FU3 precedes the 2.1 registration, the first 2.1
production binding is `("V2","2.1",1,1,"SEMANTIC_AUTHORITY_V2_S2A_FU3")`;
the Q3-B3-FU2 design's binding text (§9.1) is corrected by that decision
(design-level note; the design's all other content stands). The 2.1
capture/qualification harness pins the binding it is given — the firewall is
tier-level, and the harness scores decisions, so qualification arithmetic is
binding-agnostic.

## 6.3 The W1 consumer-guard contract (future wiring phase)

Pricing-eligibility predicate for V2-derived candidates (statistic level):

```
eligible ⇔ tier ∈ PRICING_ELIGIBLE_TIERS
          ∧ ( SalesUnitAuthorityV2 == PROVEN_EQUIVALENT
              ∨ recorded human CONFIRMED overlay for this candidate )
otherwise excluded with the recorded reason (e.g. SALES_UNIT_NOT_PROVEN)
```

* Applies to **V2 semantic-derived eligibility only** — never to the
  deterministic MACHINE_VERIFIED path (frozen 4A) and never to the V1
  human-confirmed Reviewed Price path (frozen HUMAN-REVIEW), both
  byte-unchanged.
* The guard is a precondition of the wiring phase's own acceptance: the
  phase may not deploy a V2 pricing consumer without it (task item:
  "mandatory").
* Presentation: the candidate remains market evidence (NEEDS_REVIEW counts
  under "Market evidence found: N" per the frozen summary wording); it
  never appears in "Pricing-eligible comparable listings: N" unless the
  predicate holds.

## 6.4 Amendments explicitly NOT made

* No change to `PRICING_ELIGIBLE_TIERS` (the frozen set stands; the ceiling
  moves tiers out of it by landing on NEEDS_REVIEW).
* No change to the requirement table, the matrix, the NM-2 ceiling, the
  conflict taxonomy, the badges, or the attention order.
* No change to the capture schema (v1 direct; v1 production-route), the
  eight gates, or the DRAFT policy.
* No change to the deterministic 3C/2A comparator or the 4D-D firewall.

## 6.5 Replay compatibility (design requirement)

* V1 records (binding `("V1","1.1",1,1,"SEMANTIC_AUTHORITY_V2_S2A_FU2")`)
  and 2.0 V2 records (binding `("V2","2.0",1,1,"SEMANTIC_AUTHORITY_V2_S2A_
  FU2")`) replay under the **unchanged** derivation — byte-identical
  agreement proofs, no re-interpretation.
* FU3-bound records replay under the FU3 derivation (bound + unit authority +
  FU3 tier + fired rules agreement).
* The adapter/codec dispatch extends the S2-B-FU1 registry discipline:
  the recorded authority token selects the derivation; an unknown token
  fails closed. (Module placement — extension of `semantic_authority_v2.py`
  vs a new `semantic_authority_v3.py` module — is an implementation-phase
  detail constrained only by: old-token invariance, per-binding dispatch,
  and the research-layer boundary rules.)
* Historical qualification evidence (Q3-B capture + reports bound to 2.0 /
  corpus 1.0.0) is untouched — the harness does not consume tiers.

---

# 7. Corpus impact and conflicts

## 7.1 No label change; the 11 expected-MATCH cases under the target architecture

Decisions: unchanged (the 2.1 defaults stand; Q3-B3-FU2 §7 audit: 11/11
SUPPORTABLE at the stated resolutions). The target architecture adds two
recorded facts per case and one future-tier effect:

| Case | Substate | Resolution bound (FU3) | Unit authority (all 11: UNAVAILABLE) | Future auto-tier S2A_FU2 | Future auto-tier S2A_FU3 |
| --- | --- | --- | --- | --- | --- |
| 0001 | U1 (identity wording) | PART_NUMBER | UNPROVEN | AI_ASSISTED | NEEDS_REVIEW (unit ceiling) |
| 0038 | U1 (SEO tokens — not in the 4-token COMPAT vocabulary) | PART_NUMBER | UNPROVEN | AI_ASSISTED | NEEDS_REVIEW |
| 0041 | U1 + product context | PART_NUMBER | UNPROVEN | AI_ASSISTED | NEEDS_REVIEW |
| 0006 | U2E | PART_NUMBER | UNPROVEN | AI_ASSISTED | NEEDS_REVIEW |
| 0020 | U5 NM-2 + relation authority | PART_NUMBER (specifically related part) | UNPROVEN | AI_ASSISTED | NEEDS_REVIEW |
| 0010 | U3 | FAMILY_DESCRIPTION | UNPROVEN | NEEDS_REVIEW (requirement ceiling) | NEEDS_REVIEW (requirement + unit ceilings) |
| 0008 | U2N | DESCRIPTION | UNPROVEN | NEEDS_REVIEW (requirement ceiling) | NEEDS_REVIEW (requirement + unit ceilings) |
| 0035 | U2N | DESCRIPTION | UNPROVEN | NEEDS_REVIEW (requirement ceiling) | NEEDS_REVIEW |
| 0039 | U2N | DESCRIPTION | UNPROVEN | NEEDS_REVIEW (requirement ceiling) | NEEDS_REVIEW |
| 0014 | U4 | DESCRIPTION | UNPROVEN | AI_ASSISTED | NEEDS_REVIEW (unit ceiling) |
| 0017 | U4 | DESCRIPTION | UNPROVEN | AI_ASSISTED | NEEDS_REVIEW (unit ceiling) |

(Today, under both tokens, every live V2 MATCH is at most NEEDS_REVIEW —
dimension A ≤ LIMITED; the table's tier columns describe the **future
qualified state**, where the firewall's effect is defined.)

## 7.2 The 7 ambiguous (CONTESTABLE) cases

| Case | Substate | 2.1 default (in-set) | Resolution bound (FU3) | Note |
| --- | --- | --- | --- | --- |
| 0005 | U1 bare token | MATCH (Δ vs 2.0) | PART_NUMBER | UNCERTAIN stays DEFENSIBLE (R13) |
| 0009 | U2N thin | UNCERTAIN (INTERFACE unpinned) | DESCRIPTION | MATCH pole DEFENSIBLE by label; a MATCH would carry the unit ceiling in the future state |
| 0013 | U4 sibling family | MATCH (Δ; expected pole UNCERTAIN is the safer, in-set one) | DESCRIPTION | The recorded three-sibling fact stays label-side (RC-3/R15); both poles in-set; no payload-internal rule separates it from 0014 (Q3-B3-FU2 §7.4) |
| 0021 | U5 NM-2 no relation | UNCERTAIN (revision-shaped) | NONE | MATCH is outside the label set and the contract (U-3) |
| 0023 | U5 NM-2 product context only | UNCERTAIN | NONE | Product context never establishes (approved decision 5) |
| 0040 | U4 published different brand | NO_MATCH (reviewable, never MATCH) | DESCRIPTION (bound; N-3 decides) | The bound records what the input *could* support; the published conflict decides |
| 0043 | U4 form unproven | UNCERTAIN (FORM_FACTOR unpinned) | DESCRIPTION | MATCH pole DEFENSIBLE by label |

## 7.3 Conflicts identified

* **Corpus-contract conflicts: NONE.** No label asserts a tier, a
  resolution, or a unit equivalence; no label is moved; `label_revisions`
  stays empty; the 1.1.0 binding-only re-seal design is unaffected.
* **The single acceptance-text conflict:** §3.6 (AD-066 U4/U1/U2E
  auto-authority becomes conditional on unit authority under the FU3
  token). It is a property of the S2-A **authority contract**, not of the
  corpus, and it is ratified by approval (AD-Q3B4-4), never by silent
  change.
* **Option C's six-label conflicts** (§3.4) are recorded as the reason C is
  not recommended — they do not arise under the recommendation.

---

# 8. Adversarial acceptance matrix (Task D — DESIGN ONLY; nothing implemented in this phase)

Test-design conventions: every case is a **recorded-input construction**
through the frozen chain (request → observation → 3B → 3C → S2-A
assessment → V2 input builder), with the model response scripted (test
double) — no live call; assertions split into (i) expected 2.1 semantic
decision, (ii) expected `IdentityResolutionBoundV2`, (iii) expected tier
under the S2A_FU2 derivation (future-qualified state: dimension A = STRONG
profile supplied), (iv) expected tier under the S2A_FU3 derivation, (v)
expected pricing eligibility under the target W1 predicate, (vi) the
expected blocking/rejection reason. Rows 1–11 are the task-mandated shapes;
"future-qualified" means conditions §4.1 (1)+(2)+(3) (+ (4) where stated).

| # | Scenario (shape) | Expected decision (2.1) | Identity resolution bound | Tier — S2A_FU2 (future-qualified) | Tier — S2A_FU3 | Pricing-eligible (target W1) | Blocking / rejection reason |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | **Exact MPN, silent multi-pack** (A9; U1 identity wording; channel UNAVAILABLE; no cue; STRONG profile) | MATCH (M-1 — the identifier is grounded; nothing published to the contrary) | PART_NUMBER | **AI_ASSISTED** (the R14 exposure under S2A_FU2) | **NEEDS_REVIEW** | **No** | S2A_FU3: `CEILING_SALES_UNIT_NOT_PROVEN` (unit UNPROVEN; absence is never single-unit). W1 guard: `SALES_UNIT_NOT_PROVEN` (belt-and-braces for S2A_FU2-bound records). Human path: explicit CONFIRM overlay remains the only admission (row 10) |
| 2 | **Description-identical products, different full MPNs** (A8(iii); U5 complete sibling number, e.g. `…JABYY` vs requested `…DABYY`; no authority; full alignment; channel UNAVAILABLE) | UNCERTAIN (U-2, naming PACKAGING_QUANTITY — the unproven difference may carry the unit/variant question; NO_MATCH pole where the evidence resolves the difference to a product difference, N-3) | NONE (no manufacturer relation authority) | NEEDS_REVIEW (requirement ceiling: U5, B not ESTABLISHED) | NEEDS_REVIEW (requirement + unit ceilings) | No | Identifier relation not established; the recorded-catalog sibling fact is label-side, never transmitted (R15). A MATCH here on a flagged case = CRITICAL false MATCH (`sales_unit_safety_false_match_count`) — the gate the corpus exists to catch |
| 3 | **Partial-prefix sibling variants** (A2(i)/0010 shape; U3 prefix shared by three recorded siblings; full alignment; no authority) | MATCH (M-3 — family+description ground; (U3-a)(U3-b)(U3-c) hold on the payload) | FAMILY_DESCRIPTION (the prefix is never the complete number) | NEEDS_REVIEW (U3 requirement ceiling — the variant tail is open) | NEEDS_REVIEW (requirement + unit ceilings) | No | `CEILING_IDENTIFIER_RELATIONSHIP_NOT_ESTABLISHED` (frozen; the open variant question) — and, future-qualified under S2A_FU2 *with* a reviewed relation added, the unit ceiling still holds the tier (row 6 proves the interaction) |
| 4 | **Different retailer SKU, matching specifications** (0008 shape; U2N; full alignment) | MATCH (M-4 — description ground; the SKU is neither conflict nor ground) | DESCRIPTION | NEEDS_REVIEW (U2N requirement ceiling) | NEEDS_REVIEW (requirement + unit ceilings) | No | `CEILING_IDENTIFIER_RELATIONSHIP_NOT_ESTABLISHED` — a published identifier-like claim that is not the target is not trusted for automatic pricing (frozen S2-A-FU2 policy, preserved) |
| 5 | **U4 no-MPN generic description** (0015/0043 shape; request conveys CAPACITY + FORM_FACTOR; candidate pins neither) | UNCERTAIN (U-1, naming the unpinned request-conveyed dimension(s) — alignment fails; no resolution grounded) | DESCRIPTION (bound only; no ground claimed) | NEEDS_REVIEW (UNCERTAIN + actionable) | NEEDS_REVIEW | No | Missing decision-critical request-conveyed dimensions (`missing_critical_attributes` names them); a MATCH on this shape is a 2.1 contract violation (qualification severity; watch item) and, future-qualified, carries the unit ceiling regardless |
| 6 | **Manufacturer-authorized near-miss with unknown packaging** (0020 + UNPROVEN unit; U5 NM-2 + `MANUFACTURER_RELATION_AUTHORITY`; channel UNAVAILABLE) | MATCH (M-2 — G2-auth; the resolved difference is not a conflict; reason `MATCH_AUTHORIZED_IDENTIFIER_RELATION`) | PART_NUMBER (for the specifically related part — the labeled authority is the ground) | **AI_ASSISTED** (NM-2 ceiling cleared by authority; requirement satisfied — the §4.1 condition (4) holds) | **NEEDS_REVIEW** | **No** | `CEILING_SALES_UNIT_NOT_PROVEN` — **identifier authority does not establish commercial-unit equivalence** (the core Task B invariant case: qualified + STRONG + HIGH + reviewed relation, still not auto-priced). Unit proven (OBSERVED SINGLE_UNIT) → PROVEN_EQUIVALENT → AI_ASSISTED stands |
| 7 | **Customer-retrieval alias without manufacturer authority** (0018/0022 shape; U5 NM-1 + `CUSTOMER_RETRIEVAL_RELATION`; R/T suffix; channel UNAVAILABLE; safety flag) | UNCERTAIN (U-2, naming PACKAGING_QUANTITY — the alias makes the variant question concrete while conferring zero equivalence authority) | NONE | NEEDS_REVIEW (requirement ceiling; customer retrieval is never ESTABLISHED) | NEEDS_REVIEW (requirement + unit ceilings) | No | Customer retrieval = retrieval hint only (frozen; approved decision 4). A MATCH = CRITICAL false MATCH (0018/0022 are the corpus's sales-unit-safety guards; gate `zero_false_match_on_packaging_quantity_conflicts` + the safety metric) |
| 8 | **Published incompatible packaging** (0032/0033/0034 shape; OBSERVED tray of 20 / pack of 4 / bundle; any identifier shape) | NO_MATCH (N-1 absolute rule — `PACKAGING_QUANTITY` / `BUNDLE`; no confidence, provenance, or alignment overrides) | (bound recorded; decision negative — no equivalence claimed) | HARD_CONFLICT (supersedes, last) | HARD_CONFLICT | **Never** — not even by human confirmation (frozen: a hard conflict cannot be confirmed or changed) | The absolute rule: "same physical drive" never implies "same comparable price unit." Under P2 this shape arrives OBSERVED from the extractor; today the corpus supplies it via the structured channel |
| 9 | **Conflicting title and specification evidence** (0037 shape; title 3.84TB vs spec 7.68TB; request conveys CAPACITY) | UNCERTAIN (U-5 — the dimension is unpinned in both directions; neither side adopted; the conflict class is never asserted; never NO_MATCH on the contradiction alone) | DESCRIPTION (bound only; no ground claimed) | NEEDS_REVIEW (UNCERTAIN + actionable) | NEEDS_REVIEW | No | Internal contradiction = missing evidence in both directions (approved decision 7). The 2.0-era false NO_MATCH on this shape is the defect the 2.1 rule removes (pre-registered Δ; R5 watch) |
| 10 | **Human-reviewed unit equivalence** (row 1's shape after a human CONFIRM on the recorded candidate; overlay persisted; no hard conflict) | (model record unchanged: MATCH, PART_NUMBER bound) | PART_NUMBER | (S2A_FU2: AI_ASSISTED → overlay HUMAN_CONFIRMED; S2A_FU3: NEEDS_REVIEW → overlay HUMAN_CONFIRMED — precedence HARD_CONFLICT > HUMAN_CONFIRMED > AI unchanged) | **HUMAN_CONFIRMED** (the ceiling is automatic-tier-only; the overlay applies above it, exactly as with the NM-2 ceiling) | **Yes — via the explicit human path** (W1 predicate: recorded CONFIRMED overlay admits; origin preserved as in the frozen 4A-reviewed semantics) | No rejection — this row pins that the firewall preserves the explicit, auditable override: run-scoped candidate state, confirm/reject/undo actions, persisted, origin-tagged. The reviewer's judgment that the silent listing is a single unit is a human decision, recorded as such — never a machine inference |
| 11 | **Future STRONG + HIGH + qualified V2 state** (the §4.1 composition; two sub-rows) | (a) U1 exact-identifier silent multi-pack → MATCH; (b) U4 full-alignment (0014 shape) → MATCH | (a) PART_NUMBER; (b) DESCRIPTION | Both: **AI_ASSISTED** under S2A_FU2 — the R14 exposure live (the test asserts this to pin the pre-fix state) | Both: **NEEDS_REVIEW** under S2A_FU3 | Both: **No** (W1 guard: `SALES_UNIT_NOT_PROVEN`) | (a)+(b) prove the firewall is resolution-independent: the *strongest* identity ground (exact part number) receives the *same* unit treatment as the weakest (description) — the unit question is orthogonal to the identity question. This is the acceptance row for Task B's invariant; a regression that admits either sub-row is a hard failure of the W1 predicate and of the FU3 ceiling |

Design notes: rows 1/6/11 assert **both** token behaviors (pre-fix and
post-fix) so the test suite documents the defect and the fix in one matrix;
rows 2/7/8 pin the frozen false-MATCH gates (the corpus's existing
`commercial_sales_unit_safety` severity); row 10 pins the override
preservation (Task B requirement); every row's decision expectation is the
Q3-B3-FU2 corrected-contract default (no label implication — none of these
shapes is a frozen corpus case except by construction of the row).

---

# 9. Proposed bounded implementation phases

Each phase is bounded, reviewed, separately approvable, and MUST NOT deploy
until its own reviewed deployment approval. No phase in this plan implements
anything in this session.

| Phase | Scope (one paragraph) | Gate / exit criteria | Depends on |
| --- | --- | --- | --- |
| **FU3** — `SEMANTIC-AUTHORITY-V2-S2-A-FU3` | CONTRACT-ONLY: the §6.1 amendment (bound + unit-authority derivations; restrict-only ceiling; per-binding replay; old-token invariance; tests). No wiring, no deployment — production behavior identical to the starting SHA (no live path references the token) | Independent review + approval (incl. AD-Q3B4-4 ratification); full suite green; collection non-decreasing | AD-Q3B4-2/-3/-4 |
| **P1** — Prompt 2.1 implementation | The approved Q3-B3-FU2 design (T1–T5): 2.1 builder + binding + corpus 1.1.0 binding-only re-seal + harness pin extensions; **no recapture** (captures are Q3-C's) | Q1–Q10 approved by ChatGPT (this document's decision does not answer them); 2.0 artifacts byte-frozen (regression pins) | AD-Q3B4-5 (binding choice); independent of FU3 (binding-agnostic arithmetic, §6.2) |
| **P2** — Packaging extraction | The extractor publishes the bounded packaging field with source provenance; the OBSERVED channel fills on live pages; absolute-rule catches at the decision level; corpus extension (governed, later corpus version) | Independent review + approval; the never-infer rule preserved (UNAVAILABLE stays the honest state where nothing is published); the silent residual recorded (R1/R14 watch) | None (independent; may land any time) |
| **P3** — Authority-side grounding | Deterministic/reviewed `matched_facts` infrastructure making dimension A STRONG reachable on the live path (the AD-071 limitation closed by its own approved design) | **Ordering constraint (iii): its production effect is conditioned on FU3 (or at minimum the W1 guard) being in force** | FU3 (or guard) |
| **Q3-C** — Qualification decision | Policy approval (DRAFT → approved, or an amended policy through its own governance); 2.1 captures on BOTH pinned models (incl. the deferred fallback); eight gates; floors | **Ordering constraint (ii): conditioned on the FU3 disposition** (AD-Q3B4-6); decision vocabulary unchanged (POLICY_PENDING until then) | P1; P2 (recommended, for coverage of OBSERVED shapes — not mandatory for the decision) |
| **W1** — First V2 pricing wiring + deployment | The V2-derived pricing-eligibility consumer with the **atomic fail-closed guard** (§6.3), summary-wording agreement, recorded exclusion reasons; the authority promotion (`V2_AUTHORITY_QUALIFIED`) is part of this phase's deployment decision, never a separate flip | **Ordering constraint (i): guard atomic with the consumer; no V2 pricing consumer ships without it**; explicit deployment approval; the current Machine Price / Reviewed Price bytes-identical regression | Q3-C; FU3 (or, at minimum, the guard carrying the invariant for S2A_FU2-bound records) |

Sequencing note: the minimal safe order is **FU3 → (P1 ∥ P2 ∥ P3-gated) →
Q3-C → W1**; P1 may precede FU3 (binding decision AD-Q3B4-5 covers both),
but P3's production effect and W1 may not outrun the firewall.

---

# 10. Explicit approval decisions required from ChatGPT

This document requests **decisions, not implementation authorization**.
Each is bounded and independent; any may be deferred without invalidating
the others except where stated. (The Q3-B3-FU2 design's own Q1–Q10 remain
separately pending and are NOT answered by this document.)

1. **AD-Q3B4-1 — Defect record.** Approve DEFECT-1 (no enforceable
   identity-resolution distinction in the MATCH response/derivation),
   DEFECT-2 (structural sales-unit blindness of the frozen derivation; the
   §4.1 future-state exposure), and DEFECT-3 (stale six-key documentation)
   as the architecture record of the Q3-B4 decision.
2. **AD-Q3B4-2 — Task A option selection.** Approve **Option B** (the
   independently derived `IdentityResolutionBoundV2` at the separately
   versioned S2-A-FU3 boundary, with Option A's single-advisory-MATCH
   discipline) and **reject Option C** with the recorded conflicts (§3.4:
   AD-066 behaviors 1–2; the frozen 2.0 decision standard; six corpus
   labels; the DRAFT recall floor 0.90 vs 0.4545).
3. **AD-Q3B4-3 — Task B option selection.** Approve **Option D** (the
   combined firewall: FU3 restrict-only derivation ceiling + mandatory
   atomic fail-closed consumer guard at the first V2 pricing wiring + P2
   extraction as the independent observability phase), including the
   restrict-only scope (automatic tier only; the human overlay is the
   explicit auditable exception; the deterministic MACHINE_VERIFIED path and
   the V1 Reviewed Price path are untouched) and the §4.1 invariant as the
   acceptance test (row 11 of §8).
4. **AD-Q3B4-4 — Ratification of the exact AD-066 conflict.** Approve that,
   under the NEW token `SEMANTIC_AUTHORITY_V2_S2A_FU3` only, the S2-A-FU1/
   FU2 auto-authority behaviors (U4 / U1 / U2E: MATCH + HIGH + STRONG +
   clean ⇒ AI_ASSISTED) become **conditional on
   `SalesUnitAuthorityV2 == PROVEN_EQUIVALENT`** (capped at NEEDS_REVIEW by
   `CEILING_SALES_UNIT_NOT_PROVEN` when UNPROVEN), while the old token's
   semantics, records, tests, and replays are byte- and behavior-unchanged.
   This is the post-freeze amendment; the §3.6 statement is the conflict,
   and this approval is its ratification — not a silent change.
5. **AD-Q3B4-5 — Binding/ordering decision.** Approve the recommended order:
   FU3 before the 2.1 production binding is registered (first 2.1 records
   carry `("V2","2.1",1,1,"SEMANTIC_AUTHORITY_V2_S2A_FU3")`); if FU3 slips,
   2.1 registers under S2A_FU2 per the Q3-B3-FU2 design and the consumer
   guard alone carries the invariant until FU3 lands.
6. **AD-Q3B4-6 — Q3-C conditioning.** Approve that the Q3-C qualification
   decision (policy approval + captures + gates) is **conditioned on the
   FU3 disposition** (approved and frozen, or explicitly deferred in
   writing with the guard precondition for W1 standing) — ratifying
   Q3-B3-FU2 §15 item 4 / Q7.
7. **AD-Q3B4-7 — Phase plan.** Approve the bounded phase plan (§9) with the
   ordering constraints (i)–(iv), including: no deployment from FU3; P3's
   production effect gated on the firewall; W1's guard atomic with its
   consumer; and that **no implementation of any phase begins before
   ChatGPT's independent review of this pushed document**.

---

# 11. GO / NO-GO assessment

**GO — for the recommended target architecture, approval-gated at every
step.** Rationale:

1. **Both blockers are real, source-verified, and precisely bounded**
   (DEFECT-1 §2; DEFECT-2 §2) — not hypotheticals: the live channel is
   always UNAVAILABLE (`semantic_v2.py:903`), the derivation has no unit
   input (verified over all five derivation inputs), the only
   pricing-eligible semantic row is MATCH+HIGH+STRONG, and the current
   protections are state (P3 + Q3-C remove them without touching the
   contract).
2. **The recommendation is the smallest coherent architecture** that
   preserves every frozen invariant (§5.6 list), makes the resolution
   distinction typed/replayed/consumer-visible (Option B, Task A), and
   structurally prevents `MATCH + UNKNOWN_SALES_UNIT → pricing-eligible
   comparable` in the fully-qualified future (Option D, Task B) — with
   deterministic ownership (input-only derivations), no schema change, no
   migration, no corpus change, and the human override preserved as the
   explicit auditable exception.
3. **The one acceptance-criteria conflict is identified exactly and is
   version-isolated** (§3.6, AD-Q3B4-4): old-token semantics, records,
   tests, and replays are unchanged; the conflict lives only under the new
   token, which no live path references until W1.
4. **No NO-GO condition is currently triggered:** no corpus-contract
   conflict (Option C's six are recorded as the reason for rejection); no
   state drift (HEAD = starting SHA; collection 6928; digests re-verified);
   no safety-boundary violation in the recommendation.

**Explicit NO-GO (prohibited without the listed approvals):**

* Implementing Prompt 2.1 before Q3-B3-FU2 Q1–Q10 approval (including Q9
  resolution semantics and Q10 limitation record).
* Any in-place modification of the frozen S2A_FU2 derivation/tables/tests.
* Registering the 2.1 binding under S2A_FU3 without AD-Q3B4-4 + AD-Q3B4-5.
* Shipping ANY V2 pricing consumer without the atomic fail-closed guard
  (ordering constraint (i)) — this holds even if AD-Q3B4-4 is deferred.
* Any corpus label change "for the firewall" (none is required; §7).
* Flipping `V2_AUTHORITY_QUALIFIED` before Q3-C + (for FU3-bound records)
  FU3 freeze.
* Letting P3's production effect outrun the firewall (ordering constraint
  (iii)).

**This recommendation is not architecture approval.** It is the bounded
decision document of a contract-design session. ChatGPT's independent
review of the pushed commit precedes any implementation authorization; no
deployment, authority promotion, model capture, or implementation occurs in
this phase or as a consequence of it.

---

# 12. Session evidence and preservation statement

**Git / worktree evidence (recorded before work):**

* HEAD at start: `3e6d326d3f7d36ef377a0f9f78899ca68b6e3aa6` (the Q3-B3-FU2
  commit — the expected starting SHA).
* Pre-existing worktree state (preserved, untouched): 1 tracked modification
  (`tmp_collection.txt` — line-ending only, pre-existing since before
  Q3-B3); 24 untracked files (the Q3-B3 revision design documents, the
  historical benchmark artifacts, the Q3-B live-capture evidence, the
  Q3-B2 diagnosis, and session `tmp_*` logs) — all byte-unchanged by this
  session (the three Q3-B3 design documents' SHA-256 values re-verified
  against the Q3-B3-FU2 header: `bb3aa9dc…` rev0, `bb3aa9dc…` rev0 copy,
  `1c21c86c…` rev1).
* Test collection baseline: **6928** (re-verified this session, 170 files,
  `tmp_q3b4_collect.txt`).
* Digests recomputed this session: system prompt `c0cc98bd…a84` (exact
  match); corpus v1.0.0 `2c37ba08…b549` (exact match); binding
  `("V2","2.0",1,1,"SEMANTIC_AUTHORITY_V2_S2A_FU2")`; `label_revisions`
  empty; `V2_AUTHORITY_QUALIFIED = False` in both pinned locations.

**Test evidence (what was / was not executed):** This phase is
**documentation-only** — no production source, test, corpus, policy, or
threshold file was modified (verified: the commit stages exactly one new
document; `git status` otherwise unchanged). Per the task's testing
requirement, full-suite execution is optional for documentation-only work:
**collection was re-run and verified (6928 = expected baseline); no test
node was executed** (no source change occurred, so no regression could be
introduced or detected by execution, and the house-recorded flake class of
clean-interpreter subprocess guards would add no signal). `python
manage.py check` / `makemigrations --check --dry-run` were not re-run: no
model, migration, or Django surface is touched by a new markdown document
(the starting SHA's recorded validation covers the unchanged source). No
test was deleted, renamed, skipped, xfailed, deselected, ignored, or
weakened; the flake allowlist was not expanded.

**Preservation:** No live model call; no capture performed or modified; no
deployment; no authority promotion; no corpus change; no implementation.
The Q3-B live capture and its manifest remain the evidence of record,
untouched.

**Commit scope (this phase):** exactly one ordinary append-only commit
staging **only** `docs/PRODUCT_INTEL_SEMANTIC_V2_Q3B4_AUTHORITY_BOUNDARY_
DECISION.md` (this document), pushed normally to the authorized branch
`main`. Not staged: the pre-existing tracked modification (`tmp_collection_
txt`), the new session collection log (`tmp_q3b4_collect.txt` — untracked
session evidence, consistent with the `tmp_*` convention), and every other
pre-existing untracked artifact. No force push; no `git restore` / `reset`
/ `checkout` / `stash` / `clean` / `commit --amend` / `rebase`.

**Phase-state note (unchanged by this document):** Q3-B remains REVIEWED /
NOT APPROVED / NOT FROZEN (defects corrected in Q3-B-FU1); Q3-B-FU1 remains
IMPLEMENTED / PENDING FINAL REVIEW; the Q3-B3-FU2 Prompt 2.1 design remains
pending Q1–Q10; this document adds the Q3-B4 decision proposal on top,
pending AD-Q3B4-1…7.
