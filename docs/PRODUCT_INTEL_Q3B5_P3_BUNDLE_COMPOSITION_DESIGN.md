# Product Intelligence — Q3-B5-P3: Versioned Bundle Composition Authority Design (S2-A-FU4)

**Mode: DESIGN ONLY — no implementation in this phase.** No code, no test,
no capture, no deployment, no migration, no model call, no authority
promotion. The only artifact of this phase is this document, committed
design-only on the starting SHA below.

**Starting SHA:** `1ec0e34f96af29cbbd8785e4be23e9f109b94412`
(Q3-B5-P2-FU1 endpoint — the packaging-ambiguity and bundle-identity
correction; baseline collection 7268, re-verified this session: HEAD is
`1ec0e34`, full-suite state per the Q3-B5-P2-FU1 STATUS section).

## Relationship to the prior design documents

This document is the design of record for the separately versioned
**bundle-composition authority amendment** that the Q3-B5-P2-FU1 STATUS
section's *FU3 interaction review* proposed (the "exact versioned contract
amendment required to represent the distinction (PROPOSED, NOT
implemented — separately approval-gated)"). It executes the roadmap
discipline of the approved Q3-B4 decision
(`docs/PRODUCT_INTEL_SEMANTIC_V2_Q3B4_AUTHORITY_BOUNDARY_DECISION.md`):
Task B Option D (the combined firewall), §5.4(2) (changes requiring NEW
VERSIONED CONTRACTS, each separately approval-gated), §6.1 (the S2-A-FU3
amendment pattern), §6.2 (the 2.1 binding decision / AD-Q3B4-5), §6.5
(replay compatibility), §9 (the bounded phase plan), and the per-binding
replay discipline that Q3-B5-P1 (Prompt 2.1) and Q3-B5-P2 (extraction)
have been executing against.

Lineage, one entry each:

| Phase | Document / record | Relation to this design |
| --- | --- | --- |
| Q3-B4 decision | `docs/PRODUCT_INTEL_SEMANTIC_V2_Q3B4_AUTHORITY_BOUNDARY_DECISION.md` | Approved architecture of record (Option D firewall; AD-Q3B4-1..7 ratified) |
| Q3-B3-FU2 (rev 2) | `docs/PRODUCT_INTEL_SEMANTIC_V2_PROMPT_2_1_DESIGN_Q3B3_FU2.md` | Approved Prompt 2.1 design; the SU axis (SU-EQ / SU-X / SU-AMB / SU-UNK / SU-ENT) and the P1–P6 sales-unit outcome table the model side of this contract speaks to |
| Q3-B4-FU1 / FU2 | STATUS sections (frozen) | The separately versioned FU3 authority contract (`SEMANTIC_AUTHORITY_V2_S2A_FU3`) and its Q3-B4-FU2 correction — BYTE-FROZEN input to this design |
| Q3-B5-P1 | STATUS section (approved / frozen) | Prompt 2.1 implementation; the 2.1 binding `("V2","2.1",1,1,"SEMANTIC_AUTHORITY_V2_S2A_FU3")`; corpus 1.1.0; harness pin extensions |
| Q3-B5-P2 / P2-FU1 | STATUS sections (implemented / corrected; P2 pending final review) | The extraction layer (schema v1) and its bundle-identity correction (count-only bundles are ambiguous, never established); the FU3 interaction review that PROPOSED this amendment |

What this document deliberately is NOT:

* **Not an implementation.** No module, no test, no binding registration, no
  corpus artifact is created or changed by this phase. The future
  implementation phase (its own, separately approval-gated) builds against
  this specification.
* **Not an amendment of any frozen contract.** The frozen S2-A module
  (token `SEMANTIC_AUTHORITY_V2_S2A_FU2`), the frozen FU3 module (token
  `SEMANTIC_AUTHORITY_V2_S2A_FU3`), the frozen S2-C-FU1 channel
  (`CandidateSalesUnitEvidenceV2`), the Prompt 2.0 / 2.1 contracts, the
  corpus (1.0.0 / 1.1.0), the DRAFT policy, the qualification gates, and
  the replay registries are all specified here only as UNCHANGED inputs
  and byte-pinned invariants.
* **Not a qualification or promotion decision.** `V2_AUTHORITY_QUALIFIED`
  stays False in both pinned locations; nothing in this design activates
  V2 authority, connects any derivation to pricing, or changes any tier
  reachable from a live path (no live path references the proposed token
  yet — the same isolation property the FU1 / FU2 / P1 / P2 phases all
  carried).

## Scope box (safety requirements, restated as design invariants)

1. **No model-generated composition authority.** Every composition fact in
   this contract is (a) a verbatim published text span with span-bound
   provenance (candidate side: the frozen extractor's recorded cues, or the
   frozen recorded channel), or (b) a supplied, reviewed, or
   request-description record with a bounded non-model provenance class
   (target side). No member of either provenance vocabulary is a model
   claim; no LLM output enters the derivation; the derivation is pure,
   deterministic, and replayable.
2. **No inference from matching MPN alone.** Composition comparison is
   over the published clause text (or the versioned materiality grammar's
   parse of it). A part number occurring inside a clause is an item token
   like any other: it is never matched, normalized against the target
   MPN, or given identity weight. MPN similarity inside compositions is
   out of grammar (an entry containing a full identifier string simply
   parses as item text or fails to parse — never as identity evidence).
3. **No automatic pricing eligibility from missing or partial
   sales-unit evidence.** A missing / partial / self-contradicted
   composition derives UNPROVEN (never PROVEN_EQUIVALENT), and the
   restrict-only ceilings (`CEILING_SALES_UNIT_NOT_PROVEN` /
   `CEILING_SALES_UNIT_CONTRADICTED`, frozen FU3 vocabulary, unchanged)
   keep any would-be automatic tier at `NEEDS_REVIEW`. PROVEN_EQUIVALENT
   under this token changes no consumer behavior until the separately
   gated W1 wiring + guard + qualification all exist; `V2_AUTHORITY_
   QUALIFIED` stays False.
4. **No changes to frozen contracts, corpus labels, thresholds, or
   qualification policy.** The corpus reseal this design specifies
   (§7.3) is binding-ONLY (every per-case document byte-identical;
   `label_revisions` empty) and is executed by the separately gated
   registration step, never by the contract phase.
5. **No live integration, deployment, or model capture** in any phase
   this document authorizes.

---

## Decision table (binding design decisions)

Binding design decisions. Each is ratified by this document; each has a
source citation (§1) or an explicit tradeoff record (§11).

| # | Decision | Statement |
| --- | --- | --- |
| **D1** | New token, new module | The amendment is the separately versioned authority contract token `SEMANTIC_AUTHORITY_V2_S2A_FU4`, owned by a NEW research module (proposed name `product_intelligence/research/semantic_authority_fu4.py`). The FU2 module (`research/semantic_authority_v2.py`), the FU3 module (`research/semantic_authority_fu3.py`), the extraction module (`research/sales_unit_extraction.py`), the S2-C channel module (`research/semantic_v2.py`), and the 2.0 / 2.1 contract modules are BYTE-FROZEN inputs (file-level SHA-256 pins, the FU3-test precedent at `tests/research/test_semantic_authority_v2_fu3.py` line 144 ff.). |
| **D2** | No input-schema change | The recorded V2 input (`SemanticMatchCaseV2`; input-schema axis "1") is unchanged. The composition facts are DERIVATION-INPUT records (the FU3 `TargetSalesUnitEvidenceV2` precedent — an explicit, bounded record passed to the derivation, not a case field). The FU4 production binding therefore keeps input schema 1 and output schema 1 (§7.1). |
| **D3** | Candidate-side evidence, two bounded bases | The candidate composition record is constructed only (a) from a verified `SalesUnitExtractionResult` (schema v1) — the `EXTRACTION_RESULT_V1` basis, digest-bound, reading the result's FULL cue list (so self-contradictory published contents are detectable, §6 item 4) — or (b) from a recorded OBSERVED BUNDLE channel alone — the `RECORDED_CHANNEL` basis (corpus-shaped / supplied channels), which sees exactly one clause. The basis is recorded in the evidence. When an extraction result is available, the integration MUST use basis (a) (the channel basis is the single-clause view, §11-T6). |
| **D4** | Composition publication states | The bounded vocabulary is `ESTABLISHED` (a non-empty, closed, verbatim published contents clause with no explicit incompleteness marker), `PARTIAL` (contents published but explicitly incomplete or not closed: an incompleteness marker, an unclosed paren, a dangling trailing separator), `ABSENT` (no contents clause: bare / count-only bundle, empty marker clause), plus the candidate-side-only relation `CONTRADICTED_PUBLISHED` (two or more established/partial published clauses that differ — every side recorded, none adopted). |
| **D5** | Empty / truncated markers never establish | `bundle:` (nothing after), `bundle ()`, `bundle (…` (no closing paren), and a clause ending on a dangling separator / incomplete quantity token are NEVER `ESTABLISHED` (they are `ABSENT` or `PARTIAL`), so they can never contribute to PROVEN_EQUIVALENT on either side. |
| **D6** | The PROVEN conjunction | FU4 derives `PROVEN_EQUIVALENT` for a bundle ONLY when ALL hold: matching BUNDLE form on both sides; composition `ESTABLISHED` on BOTH sides; the clauses equal under the bounded equality rule (byte-identical, OR equal multisets under the versioned full-parse materiality grammar, §3.7); the count rule holds (both sides publish a count ⇒ the counts are equal); both sides carry bounded non-model provenance; and the records are integrity-verified. Missing or partial composition on either side ⇒ UNPROVEN. |
| **D7** | CONTRADICTED only on materially established difference | Byte-different `ESTABLISHED` clauses derive `CONTRADICTED` ONLY when the versioned bounded item grammar fully parses BOTH clauses and the (normalized quantity, normalized item) multisets differ. Any parse failure ⇒ UNPROVEN (a textual difference that the deterministic grammar cannot establish as material is never declared a contradiction — the safe direction: UNPROVEN caps the tier, CONTRADICTED additionally marks published incompatibility). |
| **D8** | Candidate self-contradiction fails closed to UNPROVEN | Two published candidate-side clauses that differ (title vs structured field, or two title clauses) ⇒ `CONTRADICTED_PUBLISHED` on the evidence ⇒ the derivation returns UNPROVEN for EVERY target shape (never PROVEN, and never CONTRADICTED — mirroring the P2 contradiction → recorded-absence → UNPROVEN discipline and the 2.1 INTERNAL CONTRADICTION RULE: an internally contradictory dimension is unpinned in both directions, not adopted as a conflict against the target). Every side stays recorded with full provenance in the result / evidence for audit. |
| **D9** | Non-bundle arms unchanged | For `SINGLE_UNIT`, `PACK_QUANTITY`, and `TRAY_OR_FACTORY_PACK` the FU4 unit derivation is BYTE-IDENTICAL in behavior to the frozen FU3 derivation (delegated where possible; proven equivalent by test over the full FU3 shape suite, §9-A2). Only the BUNDLE arm changes, and the changes are exactly D6 / D7 / D8. |
| **D10** | No new audit rule | FU4 introduces no new `AuthorityRule` member. The two frozen FU3 restrict-only ceilings cover every FU4 unit state (`UNPROVEN` ⇒ `CEILING_SALES_UNIT_NOT_PROVEN`; `CONTRADICTED` ⇒ `CEILING_SALES_UNIT_CONTRADICTED`). The FU4 rule vocabulary mirrors the FU3 set exactly (import-self-checked, the FU3 pattern over the FU2 set). |
| **D11** | State vocabulary reused; decision record versioned | The three-state `SalesUnitAuthorityV2` enum (frozen FU3) is REUSED — the states are vocabulary; the semantics live in the derivation under the token. The decision record is a NEW separately versioned `AuthorityDecisionV2FU4` with the same field set and the same construction invariants as the FU3 record, so an FU4 decision is type-distinguishable from a FU3 decision at replay. |
| **D12** | Prompt 2.1 needs no new version; a NEW binding is required | The 2.1 prompt TEXT is unchanged (no 2.2): its sales-unit instructions are model-level and assert nothing FU4 contradicts (§7.4). But a record governed by FU4 must carry FU4 on its authority axis — the existing 2.1 binding `("V2","2.1",1,1,FU3)` is NOT reused for changed authority semantics. The FU4 production binding is `("V2","2.1",1,1,"SEMANTIC_AUTHORITY_V2_S2A_FU4")` — a successor 2.1 binding moving ONLY the authority axis. The downstream token alone is necessary but not sufficient: the token identifies the derivation, the binding identifies the RECORD CONTRACT (§7.4 answers task item 7 explicitly). |
| **D13** | Binding registration is separately gated | The contract-only FU4 phase registers NOTHING in the production / qualification registries (codec, replay, corpus, harness pins, report sections stay exactly as §1.6). The registration step (semantic-layer binding constant + harness pins + corpus 1.2.0 binding-only reseal + codec adapter + replay extension + offline no-capture baseline reports) is its own approval-gated phase, specified in §7.3 and executable only after the FU4 contract phase is reviewed and approved. |
| **D14** | Corpus reseal is binding-only | When registered, the FU4 binding seals a NEW corpus version `1.2.0`: 56/56 per-case documents byte-identical to 1.1.0, `label_revisions` empty, exactly `{corpus_version, semantic_contract_binding, corpus_digest}` moved (the P1 1.1.0 re-seal precedent). No label change; the committed 1.0.0 / 1.1.0 artifacts stay byte-frozen under their own bindings. |
| **D15** | No wiring, no promotion, no eligibility | The FU4 module is unreachable from every live path (the P2 AST-pin / FU3 lexical-guard discipline). `V2_AUTHORITY_QUALIFIED` stays False in both pinned locations. No V2 pricing consumer reads FU4 states (none exists; W1's guard predicate is unchanged and orthogonal). |
| **D16** | Verbatim comparison is primary; normalization is grammar-internal | Clause equality's primary path is byte-identity over the verbatim clause (after the bounded marker strip, §3.4). The materiality grammar's normalization (casefold + internal-whitespace collapse of item tokens, integer quantities) applies ONLY inside the secondary full-parse multiset path and the materiality test — never to the primary comparison, never beyond the documented grammar. |
| **D17** | No cross-field inference | A published bundle count is never parsed into the composition, and the composition is never parsed into the count: count-vs-entry-count agreement is neither required nor checked (D6's count rule compares published counts side-to-side only). The clause and the count are independent published facts. |
| **D18** | Frozen target records are composition-ABSENT under FU4 | The FU4 unit derivation also accepts the FROZEN `TargetSalesUnitEvidenceV2` (so one call site can serve both tokens): under the FU4 token a frozen target record is read exactly as its fields state — form + count, composition ABSENT (the field does not exist; no implicit upgrade). This keeps FU4 total over recorded inputs while guaranteeing a FU3-shaped record can never manufacture a composition fact. |

---

# 1. Evidence of record (source-level, re-verified this session)

Every citation below is file:line at the starting SHA and is the basis for
the corresponding design section. (All paths relative to the repository
root.)

## 1.1 The frozen S2-C-FU1 candidate channel

`product_intelligence/research/semantic_v2.py`

* `SalesUnitKindV2` (line 410): `SINGLE_UNIT` / `PACK_QUANTITY` /
  `TRAY_OR_FACTORY_PACK` / `BUNDLE`.
* `PackagingEvidenceStateV2` (line 430): `UNAVAILABLE` / `OBSERVED` — the
  frozen channel has EXACTLY two states; it has no ambiguous, no
  contradicted, and no composition state.
* `CandidateSalesUnitEvidenceV2` (line 448): fields `state`, `kind`,
  `quantity`, `raw_detail`, `source`. Constructor rules: `UNAVAILABLE`
  carries nothing; `OBSERVED` requires kind + non-empty `raw_detail` +
  explicit `source`; `PACK_QUANTITY` requires the bounded positive
  quantity; `SINGLE_UNIT` forbids it; tray / bundle quantity optional.
* `SALES_UNIT_EVIDENCE_UNAVAILABLE` (line 553): the single canonical
  recorded absence.
* `CandidateCommercialEvidenceV2` (line 565): the section-B commercial
  evidence; `sales_unit` is always present with an explicit state.
* `SemanticMatchCaseV2` (line 913): the recorded V2 input; the channel
  lives at `case.candidate_commercial.sales_unit`. **The case (input
  schema axis "1") is the recorded input; derivation-side records
  (e.g. the FU3 target evidence) are NOT case fields** — the precedent
  this design follows (§3.1, §7.1).

**The channel's composition visibility is free-text-only:** `raw_detail`
is "the observed value as published" (the frozen docstring) — for an
extraction-derived BUNDLE channel it is the primary established cue's
verbatim text (e.g. `"bundle: 2x RAM + 1x CPU"`), and for a
corpus-supplied channel it is the structured value (e.g. case
`V2Q-GPU-SU-BUNDLE-0034`, corpus 1.1.0: `raw_detail = "GPU + power
cables + bracket kit"`, `quantity = null`, `source =
PUBLISHED_STRUCTURED_FIELD`). Nothing in the channel bounds,
classifies, or verifies the composition: the derivation never reads
`raw_detail` at all (§1.3). That is the structural gap.

## 1.2 The frozen FU3 target-side record

`product_intelligence/research/semantic_authority_fu3.py`

* `TargetSalesUnitFormV2` (line 494): mirrors the channel kinds exactly
  (import-self-checked at module bottom).
* `TargetSalesUnitEvidenceSourceV2` (line 523): exactly
  `REVIEWED_TARGET_CONTEXT` / `REQUEST_DESCRIPTION` — "No member is a
  model claim … Absence of a record is the default single unit — an
  explicit None, never a guess."
* `TargetSalesUnitEvidenceV2` (line 549): `form`, `quantity`, `source`.
  **No composition field exists** — the target side of a bundle
  comparison can publish a form and a count, but never a contents clause.
  This is the other half of the structural gap.
* `SalesUnitAuthorityV2` (line 445): `PROVEN_EQUIVALENT` / `UNPROVEN` /
  `CONTRADICTED` — the three-state authority vocabulary (bounded at
  import).

## 1.3 The frozen FU3 derivation (the exact rule set FU4 succeeds)

Same module:

* `sales_unit_authority_from_channel` (line 600) — the recorded-channel
  derivation. The BUNDLE / TRAY arm (the Q3-B4-FU2 corrected contract):
  * target form mismatch (incl. the default single unit) →
    `CONTRADICTED`;
  * matching form, count missing on EITHER side → `UNPROVEN`;
  * matching form, counts unequal → `CONTRADICTED`;
  * matching form, equal published counts → `PROVEN_EQUIVALENT`.
  **The derivation reads exactly `state`, `kind`, `quantity`, and the
  target record — never `raw_detail`, never any composition fact.**
* `derive_sales_unit_authority` (line 724): the case-level entry point.
* `AuthorityRuleV2FU3` (line 753): the frozen rule vocabulary = the
  frozen S2-A rules + EXACTLY two restrict-only rules
  (`CEILING_SALES_UNIT_NOT_PROVEN`, `CEILING_SALES_UNIT_CONTRADICTED`),
  import-self-checked.
* `AuthorityDecisionV2FU3` (line 816): the FU3 decision record;
  construction enforces the firewall invariants (AI_ASSISTED with an
  UNPROVEN or CONTRADICTED unit is un-constructible; each ceiling rule
  only with its unit state on `NEEDS_REVIEW`).
* `derive_authority_tier_fu3` (line 958): the frozen S2-A-FU2 derivation
  (called, never re-implemented) + bound + unit + the two ceilings.
* `derive_authority_tier_for_contract` (line 1085): per-binding dispatch
  over `KNOWN_AUTHORITY_CONTRACT_TOKENS` (line 179) = exactly
  `{FU2, FU3}`; the FU2 arm refuses sales-unit inputs (contract misuse);
  the FU3 arm requires the channel; unknown tokens fail closed.
* `AUTHORITY_CONTRACT_VERSION_V2_FU3` (line 159):
  `"SEMANTIC_AUTHORITY_V2_S2A_FU3"`.

**Consequence (verified against the Q3-B5-P2-FU1 tests):** under the FU3
token, a corpus-shaped BUNDLE channel with an equal published count
against a target BUNDLE of the same count derives `PROVEN_EQUIVALENT`
(§1.3's last row) — the derivation cannot see that neither side
published a composition. The Q3-B5-P2-FU1 extraction correction removed
this shape from EXTRACTOR-PRODUCED channels (count-only bundles are
`AMBIGUOUS_CUE` → recorded absence), but the FU3 derivation itself
remains count-based for bundles because the frozen channel cannot carry
a composition fact. The FU3 interaction review (below) is the proposal
of record for fixing the derivation behind a NEW token.

## 1.4 The extraction result (schema v1)

`product_intelligence/research/sales_unit_extraction.py`

* `SALES_UNIT_EXTRACTION_SCHEMA_VERSION = 1` (line 147).
* `SalesUnitExtractionState` (line 150): `NO_PACKAGING_PUBLISHED` /
  `OBSERVED_UNAMBIGUOUS` / `AMBIGUOUS_CUE` / `CONTRADICTED_CUES`
  (bounded at import).
* `SalesUnitCueReason` (line 227) — incl. `BUNDLE_WITHOUT_CONTENTS`
  (line 236): "a bare `bundle` word, or a bundle with a published count
  but no contents … A published count alone is not the complete identity
  of a bundle (the bundle's commercial unit is its composition, never
  just its count — two bundles with equal counts and different contents
  are not commercially equivalent; Q3-B5-P2-FU1)."
* `_CUE_MASTER` (line 309): the frozen cue table. Bundle forms:
  * `"N-unit bundle"` / `"bundle of N"` → **ambiguous**
    (`BUNDLE_WITHOUT_CONTENTS`); the count stays verbatim in the cue
    text and is never bound to a quantity;
  * `"bundle:"` / `"bundle ("` (`bundle_mark`) → **established** BUNDLE,
    quantity `None`, and the cue span EXTENDS over the published
    contents clause (for `(` up to the closing paren or the field end;
    for `:` up to the next comma / semicolon / closing paren or the
    field end) — so an established bundle cue's `cue_text` is the
    verbatim published phrase including its contents clause;
  * bare `"bundle"` → ambiguous (`BUNDLE_WITHOUT_CONTENTS`).
* `SalesUnitCueV1` (line 404): one recorded cue with full provenance —
  `field` (exactly `PRODUCT_TITLE` / `STRUCTURED_PACKAGING_FIELD`),
  `source` (exactly the frozen `LISTING_TITLE` /
  `PUBLISHED_STRUCTURED_FIELD` members; the other two vocabulary members
  are rejected — no member is a model claim), `raw_field_value`,
  `cue_text` verified as the verbatim substring `raw_field_value[
  cue_start:cue_end]`, `kind`, `quantity`, `disposition`, `reason`.
* `SalesUnitExtractionResult` (line 544): the versioned, immutable,
  self-verifying result — `state`, all `cues`, identifier set-aside
  notes, `established_kind` / `established_quantity`, `input_digest`
  (SHA-256 over the canonical examined-input document; the opaque
  `raw_reference` deliberately excluded), `result_digest` (SHA-256 over
  the canonical result minus the digest). The constructor is the
  validator (incl. the Q3-B5-P2-FU1 subsumption rule,
  `_is_subsumed_by_established`, line 1133: a same-kind ambiguous cue is
  admitted only when its span is contained in an established cue's span
  in the same field).
* **State-resolution boundary relevant to this design** (`_resolve_
  state`, line 1158): two established BUNDLE cues with different
  contents (e.g. title `"bundle: 2x RAM + 1x CPU"` + structured
  `"Bundle (2x SSD + cable)"`) resolve to `OBSERVED_UNAMBIGUOUS` — the
  resolution compares kind + published quantity, and for bundles both
  quantities are `None`. The channel mapping presents ONLY the primary
  cue (structured first, else first title span); the second clause
  survives in the result for audit but is invisible to the channel.
  **The extraction layer therefore does not, and per its frozen scope
  need not, police contents agreement** — the contents relation is an
  authority-level fact, which is exactly why the composition evidence
  record (§3.2) reads the RESULT's full cue list, not the channel.
* `verify_integrity` (line 793): the anti-forgery gate (digest + cue
  span re-verification; `SalesUnitExtractionIntegrityError` on any
  mismatch).
* `extract_sales_unit_evidence` (line 1260) /
  `sales_unit_channel_from_extraction` (line 1349) /
  `extract_and_map_sales_unit_evidence` (line 1406): the entry points;
  every non-`OBSERVED_UNAMBIGUOUS` state maps to the canonical
  `UNAVAILABLE` channel (fail closed).

## 1.5 The Prompt 2.1 binding (what the model side already commits to)

* `product_intelligence/semantic/contract_v2_1.py`:
  * `SEMANTIC_PROMPT_VERSION_V2_1 = "2.1"` (line 102);
  * `V2_1_CONTRACT_BINDING = ("V2", "2.1", 1, 1,
    "SEMANTIC_AUTHORITY_V2_S2A_FU3")` (line 111) — composed from the
    frozen research exports, no literal token in source; the import
    self-check at module bottom pins that the 2.1 binding moves ONLY the
    prompt axis and the authority-contract axis;
  * `SYSTEM_PROMPT_V2_1` (line 129) — the approved 2.1 text; its
    COMMERCIAL SALES-UNIT RULES (line 193 ff.) instruct the model to:
    treat a raw packaging cue as packaging evidence; apply the absolute
    rule (published incompatible packaging → NO_MATCH +
    PACKAGING_QUANTITY / BUNDLE); read an ambiguous cue (incl. a bundle
    cue of unclear wording — the 2.1 design's SU-AMB / P6 shape) as
    UNCERTAIN, never MATCH or NO_MATCH on the cue alone; and never read
    `UNAVAILABLE` as a single unit or as equivalence. **The prompt never
    names the authority token, never describes the derivation's bundle
    rule, and asserts no property that FU4 contradicts** (§7.4).
  * the real 2.1 system-prompt digest
    `e2949e7544d26228ac6f5555ae8ebd28019076e1de88ace25e79a5d942d818fc`
    (recorded in the Q3-B5-P1 STATUS section).
* `product_intelligence/research/semantic_decision_v2.py`:
  * `V2_CONTRACT_BINDING = ("V2","2.0",1,1,"SEMANTIC_AUTHORITY_V2_S2A_
    FU2")` (line 203); `AUTHORITY_CONTRACT_VERSION_V2` (line 191);
  * the live V2 record type pins `authority_contract_version ==
    "SEMANTIC_AUTHORITY_V2_S2A_FU2"` at construction (line 669 ff.) —
    **no production record can carry the FU3 token today, and none can
    carry FU4 after this design**;
  * `V2_AUTHORITY_QUALIFIED = False` (line 227) — one of the two pinned
    locations (the other: `product_intelligence/semantic/runtime_v2.py`
    line 97).

## 1.6 The qualification / replay registries (exactly as frozen)

* **Persistence codec registry** —
  `product_intelligence/research/semantic_decision_codec.py`:
  `_REGISTERED_SEMANTIC_CONTRACT_ADAPTERS` (line 138) names exactly two
  adapters (V1 + V2); `supported_contract_bindings()` (line 192) is the
  union of their `supported_bindings` — the V2 adapter supports EXACTLY
  the frozen 2.0/FU2 binding (`semantic_decision_v2.py` line 2211:
  `if binding not in (V2_CONTRACT_BINDING,):`). A FU3- or FU4-bound
  payload is refused by the production codec (pinned by
  `tests/evaluation/semantic_v2/test_q3b5_p1_binding_replay.py`,
  `test_the_codec_registry_still_knows_exactly_the_v1_and_2_0_bindings`
  and `test_an_fu3_bound_payload_is_refused_by_the_production_codec`).
* **Replay registry** —
  `product_intelligence/research/semantic_decision_replay.py`:
  `SUPPORTED_CONTRACT_BINDINGS` (= `supported_contract_bindings()`, line
  74 ff.); `replay_semantic_decision` (line 107) dispatches by the
  record's EXPLICITLY RECORDED binding; unknown / future bindings fail
  closed.
* **Corpus / harness binding registry** —
  `product_intelligence/evaluation/semantic_v2/corpus.py`:
  `BINDING_CORPUS_VERSIONS` (line 131) seals exactly
  `{("V2","2.0",1,1,FU2) → "1.0.0", ("V2","2.1",1,1,FU3) → "1.1.0"}`
  (the version constants live in `fixtures.py` lines 111 / 123);
  `KNOWN_PRODUCTION_BINDINGS` (line 139) = the key set.
* **Harness pins** — `gates.py` (`zero_contract_version_mismatch` pins
  the known production bindings, drift-pinned to the research export and
  the semantic layer's 2.1 owner), `report.py` (line 128 ff.: the
  contract-identity section accepts exactly the two known production
  bindings; unknown bindings fail closed), `capture.py` (the 2.1
  direct-capture axis pins; the PRODUCTION_ROUTE loader stays 2.0-only),
  `direct_capture.py`, `cli.py`.
* **Corpus artifacts of record** —
  `evaluation/semantic_v2_qualification/corpus_2_1.json` +
  `manifest_2_1.json`: 56 cases, `corpus_version "1.1.0"`,
  `semantic_contract_binding = ["V2","2.1",1,1,
  "SEMANTIC_AUTHORITY_V2_S2A_FU3"]`, digest
  `14396eae884841e20063cb4da0d4424ce8f05ff8745f2c787fc395d250ea8dcd`,
  `label_revisions` empty; the 1.0.0 artifacts bound to the 2.0/FU2
  binding are byte-frozen.

## 1.7 The proposal of record

The Q3-B5-P2-FU1 STATUS section ("FU3 interaction review (the mandated
STOP check)") records the exact amendment this document designs:

> a NEW separately versioned authority token
> `SEMANTIC_AUTHORITY_V2_S2A_FU4` (per-binding discipline; the frozen
> FU2 / FU3 tokens, records, and replays byte- and behavior-unchanged)
> with (1) a versioned successor of the S2-C-FU1 recorded channel
> gaining a bounded `composition` fact …, (2) the target-side evidence
> record gaining the same bounded `composition` field, and (3) the FU4
> BUNDLE rule: matching BUNDLE form → PROVEN_EQUIVALENT only with
> composition published on BOTH sides and byte-identical verbatim
> contents clauses (and equal published counts where both sides publish
> one); composition present but differing → CONTRADICTED; composition
> missing on either side → UNPROVEN.

**This design refines that proposal in three recorded places** (each a
Decision-table entry): (a) the composition fact is a versioned
evidence RECORD supplied to the derivation, not a widened channel field
inside the recorded V2 input — preserving the frozen channel byte-for-
byte and the input-schema axis at 1 (the FU3 target-evidence precedent,
§1.2); (b) "byte-identical" is necessary but NOT sufficient, and
"present but differing → CONTRADICTED" is narrowed to "materially
established difference → CONTRADICTED, otherwise UNPROVEN" per the
task's comparison rules and the no-model / no-fuzzy-match constraints;
(c) the prompt-2.1 question is answered explicitly: no new prompt
version, but a NEW production binding (not merely a downstream token) is
required for any record to be governed by FU4 (§7.4).

---

# 2. The exact gap this contract closes

1. **The derivation is composition-blind for bundles.** The frozen FU3
   BUNDLE rule (§1.3) equates matching form + equal published counts.
   Composition — the bundle's commercial identity per the Q3-B5-P2-FU1
   correction — is invisible to it: it can derive `PROVEN_EQUIVALENT`
   over two bundles that publish equal counts and different contents
   (corpus-shaped channels), and it can derive only `UNPROVEN` over two
   bundles that publish byte-identical, complete, independently recorded
   contents (the safe-but-blind direction). The frozen channel cannot
   carry the fact (§1.1), and the frozen target record cannot either
   (§1.2).
2. **The extraction layer already distinguishes the states but cannot
   express them at the authority boundary.** Schema v1 records, with
   full provenance, the bundle form (an established BUNDLE cue), the
   published count (ambiguous, never bound), the contents clause
   (verbatim, span-bound, inside the established cue text), the missing
   contents (`BUNDLE_WITHOUT_CONTENTS`), and the self-contradiction
   (two established clauses — visible only in the result, not the
   channel, §1.4). What is missing is a versioned authority-level
   EVIDENCE RECORD that carries those states with provenance into a
   derivation, and a derivation that consumes them.
3. **Why a new token and not an amendment.** The FU3 contract is frozen
   (Q3-B4-FU2 approved; the Q3-B5-P2-FU1 phase deliberately left it
   byte-unchanged and recorded the amendment as separately
   approval-gated). Per-binding replay (§6.5 of the Q3-B4 decision;
   D1 / D9) requires that historical FU3-bound records keep deriving
   exactly as they did — including FU3's count-based bundle PROVEN shape
   for records that genuinely carry only counts. Changed authority
   semantics therefore live behind `SEMANTIC_AUTHORITY_V2_S2A_FU4`;
   nothing under FU2 / FU3 moves.

**Safety-direction audit of the FU3 → FU4 delta** (over identical
inputs): FU4 differs from FU3 only where (a) FU3 said PROVEN on a
count-only or composition-unestablished bundle shape (FU4: UNPROVEN —
restricts); (b) FU3 said PROVEN or UNPROVEN over two ESTABLISHED
clauses with a materially established difference (FU4: CONTRADICTED —
restricts, and the decision-level absolute rule already owns the
model-side shape); or (c) FU3 said UNPROVEN over two ESTABLISHED,
equal, sufficiently-provenanced clauses (FU4: PROVEN — the intended
capability, requiring the full D6 conjunction, which no count-only or
partial shape satisfies). No shape that FU4 admits as PROVEN is a
count-only or incomplete-composition shape (D5 / D6 / D7), so the
Q3-B5-P2-FU1 bundle-identity invariant ("a published count is not the
complete identity of a bundle") holds at the derivation level under the
FU4 token.

---

# 3. The bounded composition evidence schema (exact proposal)

All names below are the proposed contract surface (module
`research/semantic_authority_fu4.py`, research layer, stdlib-only,
import-self-checked, no mutable global state — the FU3 / P2 discipline).
The schema is **version 1 of the FU4 composition evidence**
(`BUNDLE_COMPOSITION_EVIDENCE_VERSION_FU4 = 1`); any future change to a
grammar or state is a new version of this record, never a silent edit.

## 3.1 Placement: derivation inputs, not case fields (D2)

The FU4 unit derivation's inputs are:

```
derive_sales_unit_authority_fu4(
    channel: CandidateSalesUnitEvidenceV2,                      # frozen
    candidate_composition: CandidateBundleCompositionEvidenceV2FU4 | None,  # NEW
    target_evidence: TargetSalesUnitEvidenceV2FU4                # NEW
                    | TargetSalesUnitEvidenceV2 | None,          # frozen (D18)
) -> SalesUnitAuthorityV2
```

* `channel` — the frozen recorded channel, byte-unchanged type.
* `candidate_composition` — the NEW bounded candidate-side record
  (§3.2). `None` is legitimate and means "no composition evidence
  presented" — for a BUNDLE channel that is composition ABSENT
  (UNPROVEN); for a non-BUNDLE channel it is contract misuse (fail
  closed, D9).
* `target_evidence` — the NEW versioned target record (§3.3), or the
  FROZEN FU3 record (read as composition-ABSENT, D18), or `None`
  (the default single unit — unchanged).

Replay reconstructs the derivation exactly because every input is a
recorded, digest-verified value (§8): the channel is inside the case
(input schema 1, unchanged); the two records are recorded in the
FU4-bound record's own evaluation section (§7.3, the Q3-B4 §6.1 item 5
"derived snapshots … replay re-derives and proves agreement"
precedent).

## 3.2 Candidate-side record

```python
class BundleCompositionStateV2FU4(str, Enum):
    ESTABLISHED = "ESTABLISHED"
    """A non-empty, closed, verbatim published contents clause with no
    explicit incompleteness marker (the bounded grammar of §3.4-3.6).
    The clause is the publisher's published statement of what the bundle
    contains — recorded, not verified against the physical contents
    (the same epistemic status as every recorded fact in this system:
    equivalence is AS PUBLISHED)."""

    PARTIAL = "PARTIAL"
    """Contents were published but the publication is explicitly
    incomplete or not closed: an incompleteness marker inside the clause
    (§3.6 list), an unclosed paren-form, or a dangling trailing
    separator / incomplete quantity token. The clause text is recorded
    for audit; it can never contribute to PROVEN_EQUIVALENT."""

    ABSENT = "ABSENT"
    """No contents clause is published: a bare bundle word, a count-only
    bundle phrase ("bundle of N" / "N-unit bundle"), or an empty marker
    clause ("bundle:" / "bundle ()"). The count, when published, stays
    verbatim in the source text and is never bound to a quantity (the
    P2-FU1 rule, preserved)."""

    CONTRADICTED_PUBLISHED = "CONTRADICTED_PUBLISHED"
    """Candidate-side ONLY: two or more published contents clauses
    (across the examined fields, e.g. title vs structured field) that
    differ. EVERY clause is recorded with its full provenance; NONE is
    adopted. The derivation returns UNPROVEN for every target shape
    (D8) — a self-contradiction is not a contradiction against the
    target, and neither side may be presented as THE composition."""


class CandidateCompositionEvidenceBasisV2FU4(str, Enum):
    EXTRACTION_RESULT_V1 = "EXTRACTION_RESULT_V1"
    """Built from a verified sales_unit_extraction schema-v1 result
    (the result's full cue list is read; the record is digest-bound to
    it). Detects CONTRADICTED_PUBLISHED (D3 / D8)."""

    RECORDED_CHANNEL = "RECORDED_CHANNEL"
    """Built from a recorded OBSERVED BUNDLE channel alone (corpus-
    shaped / supplied channels; the single-clause view, §3.4)."""


@dataclass(frozen=True)
class CandidateBundleCompositionEvidenceV2FU4:
    schema_version: int                        # = 1 (bounded)
    basis: CandidateCompositionEvidenceBasisV2FU4
    state: BundleCompositionStateV2FU4
    composition_clause: str | None
    """The verbatim published contents clause (marker-stripped per §3.4)
    — present when ESTABLISHED or PARTIAL or CONTRADICTED_PUBLISHED
    (the primary clause); None when ABSENT. Original case and spacing
    (byte comparison is over exactly this text)."""
    additional_clauses: tuple[str, ...]
    """CONTRADICTED_PUBLISHED only: the OTHER published clauses, each
    verbatim, in canonical order (extraction field order, then span
    order). Empty for every other state (a non-contradicted record
    cannot carry them)."""
    source: CandidateEvidenceSourceV2
    """The frozen channel's recorded provenance source (exactly
    LISTING_TITLE / PUBLISHED_STRUCTURED_FIELD for extractor-derived
    evidence; the channel's source for RECORDED_CHANNEL basis). No
    member is a model claim; any other value is un-constructible."""
    channel_quantity: int | None
    """The frozen channel's published bundle quantity, mirrored verbatim
    (None for extractor-derived bundles — the P2-FU1 rule; the count is
    never salvaged from the composition, D17)."""
    extraction_result_digest: str | None
    """EXTRACTION_RESULT_V1 basis: the verified result's result_digest
    (64-hex; the audit anchor). None for RECORDED_CHANNEL basis."""
    extraction_input_digest: str | None
    """EXTRACTION_RESULT_V1 basis: the result's input_digest (the exact
    examined input). None otherwise."""
    evidence_digest: str
    """SHA-256 over the canonical record minus this field (self-
    verification anchor, the P2 result / FU2 record discipline)."""
```

Constructor (fail closed, the P2 result-constructor pattern):

* `schema_version == 1` exactly (unknown versions are never
  reinterpreted);
* `basis` / `state` / `source` are the exact vocabulary members;
* `source` must be one of the two non-model frozen members (a cue from
  any other provenance is un-constructible — the forged / model-claim
  defense, §1.4);
* state/coherence: `ABSENT` ⇒ `composition_clause is None` and
  `additional_clauses == ()`; `ESTABLISHED` / `PARTIAL` ⇒ exactly one
  clause, non-empty, and `additional_clauses == ()`;
  `CONTRADICTED_PUBLISHED` ⇒ `composition_clause` is the primary clause
  and `additional_clauses` is non-empty and every clause differs from
  every other (byte comparison);
* `ESTABLISHED` clauses must pass the §3.5 closure checks (an empty /
  truncated clause is un-constructible as ESTABLISHED — D5 at the
  type level);
* `EXTRACTION_RESULT_V1` ⇒ both extraction digests present and
  well-formed; `RECORDED_CHANNEL` ⇒ both None;
* `channel_quantity` obeys the frozen channel's bundle quantity rules
  (positive int or None; never inferred);
* `evidence_digest` re-verifies at construction and on every presented
  record (a tampered record produces no derivation input —
  `BundleCompositionEvidenceIntegrityError`).

## 3.3 Target-side record

```python
@dataclass(frozen=True)
class TargetSalesUnitEvidenceV2FU4:
    """The versioned successor of the frozen FU3 target-side record:
    the same form / quantity / source fields with the same constructor
    rules (mirrored from the frozen record, import-self-checked), plus
    the bounded composition fields for the BUNDLE form."""

    schema_version: int          # = 1
    form: TargetSalesUnitFormV2                     # frozen vocabulary
    quantity: int | None                            # frozen rules
    source: TargetSalesUnitEvidenceSourceV2         # frozen vocabulary
    composition_clause: str | None
    """The verbatim published contents clause of the requested part's
    bundle, exactly as published in the source the review attests
    (reviewed target context or requested description). None = the
    source published no contents (composition ABSENT — the frozen
    record's shape, D18)."""
    composition_state: BundleCompositionStateV2FU4 | None
    """None unless form is BUNDLE. For a BUNDLE form the field is
    REQUIRED and is the bounded classification of composition_clause
    (the same §3.5 grammar; the target side has no
    CONTRADICTED_PUBLISHED — one reviewed attestation is one record; a
    self-contradictory source is a review-governance failure, not a
    contract state, §11-T7). Non-BUNDLE forms carry exactly
    (None, None): composition is a bundle-only fact."""
    evidence_digest: str
```

Constructor rules: the frozen FU3 rules verbatim (form / source
vocabulary; PACK_QUANTITY requires the positive count; SINGLE_UNIT
forbids it; the provenance classes are the two frozen non-model
members) + `schema_version == 1` + the bundle composition coherence
(BUNDLE ⇒ state ∈ {ESTABLISHED, PARTIAL, ABSENT}, and the clause
matches the state exactly as on the candidate side; ESTABLISHED ⇒
clause passes §3.5; non-BUNDLE ⇒ both None) + digest self-verification.

**Provenance semantics (recorded, not re-verified by the derivation):**
the target source label is the bounded class of where the attestation
came from. Independence of the two sides (that the target clause was
not copied from the candidate page) is the REVIEW process's
attestation at record creation — the same epistemic boundary the frozen
target record already carries for its count (a reviewed "pack of 4" is
trusted as reviewed, not re-derived). The derivation records both
source labels in the decision's audit surface; a red flag (both sides
labeled from the same request description) is visible to the reviewer,
never silently laundered by the derivation (§11-T3).

## 3.4 The bounded clause extraction (marker strip)

One versioned function, `extract_published_bundle_clause(text) ->
(clause, was_paren_form)` (stdlib only; the text is always a verbatim
published span — an established cue text or a recorded channel
`raw_detail`):

1. **Count-only bundle phrase** (grammar mirroring the frozen cue
   table's bundle forms: `bundle`, `bundle of N`, `N-unit bundle`,
   `N unit bundle`, with N canonical 1..99999 — case-insensitive on the
   packaging word only, N verbatim-checked): → `clause = None`
   (composition ABSENT; the count is never bound, P2-FU1 / D17).
2. **Marker form** (word `bundle` + optional whitespace + `:` or `(`):
   strip the marker; for the paren form, strip the ENCLOSING closing
   paren when present (the cue span includes it); `clause` = the
   residue (original case / spacing preserved).
3. **No marker, not count-only** (the corpus-shape: the structured
   field's value IS the contents, e.g. `"GPU + power cables + bracket
   kit"`): `clause` = the whole text.

The extraction basis gets the clause directly from the established cue
span (the cue engine's own extension rule, §1.4 — the inverse is
exactly step 2); the channel basis applies the three steps to
`raw_detail`. The steps are deterministic and total; an input matching
none is treated as step 3 (the text is the published clause) — a
recorded channel `raw_detail` is by contract "the observed value as
published."

## 3.5 Closure / completeness classification (D5)

`classify_clause(clause, was_paren_form) -> BundleCompositionStateV2FU4`
over the marker-stripped clause (empty clause ⇒ ABSENT immediately):

* **PARTIAL** when any holds:
  * the clause contains an explicit incompleteness marker from the
    bounded versioned list `_INCOMPLETE_MARKERS = ("etc.", "etc",
    "…", "...", "and more", "+ more", "and so on", "among others",
    "and other")` (matched case-insensitively as a complete
    whitespace-delimited token, or the ellipsis character anywhere);
  * the paren form's enclosure is not closed (the published span ends
    without the closing paren — the clause is truncated at the field
    boundary);
  * the clause ends on a dangling separator (`+`, `,`, `&`, `;`, or
    whitespace after one of them), or on an incomplete quantity token
    (a trailing `N x` / `Nx` with no item following) — positive
    evidence the published statement continues beyond the examined
    text.
* **ESTABLISHED** otherwise (non-empty, closed, no marker).
* (ABSENT is reached only via the empty clause / count-only path.)

The colon-form clause that runs to the field end (the title simply ends
after the clause) is CLOSED (ESTABLISHED if otherwise clean): the
examined field is the complete published field; there is no
deterministic signal of continuation. The residual risk (a page-level
truncation invisible to the field) is recorded in §11-T2.

## 3.6 What "complete" is and is not

`ESTABLISHED` means: **the page published a closed, non-empty contents
statement, and it does not say the statement is incomplete.** It does
NOT mean "the bundle physically contains exactly these items" — that
is the publisher's claim, recorded with provenance, on the same
epistemic footing as every other recorded fact (the frozen
`PROVEN_EQUIVALENT` semantics: "the candidate is published as sold in
the same commercial unit as the target"). Equivalence is established
AS PUBLISHED, by two independently recorded publications agreeing under
the bounded grammar — never by a model, never by catalog knowledge,
never by MPN matching inside the clauses.

## 3.7 The versioned materiality grammar (D6 / D7 / D16)

Used ONLY for the secondary equality path and the material-difference
test; a versioned constant set of the FU4 module (import-self-checked
immutable):

* **Separators** (split the clause into entries): `+`, `,`, `&`, and
  ` and ` (case-insensitive).
* **Entry grammar**: an optional quantity — a canonical integer
  1..99999 (no leading zero) followed by an optional `x` / `×` (any
  case) and optional whitespace — then a non-empty item token
  (alphanumerics with internal single spaces / `.` / `-` / `_`).
* **Normalization** (inside the grammar only, D16): item tokens are
  casefolded, leading/trailing whitespace stripped, internal whitespace
  collapsed to single spaces; quantities are integers (absent ⇒ 1).
* **Full parse**: the trimmed clause decomposes EXACTLY into entries
  joined by separators, with no residual. Any residual (parenthesized
  qualifiers, trailing punctuation not a separator, unknown tokens) ⇒
  NOT fully parseable.
* **Multiset**: the sorted tuple of `(quantity, item)` pairs.
* **Equality (secondary path)**: both clauses fully parse and the
  multisets are equal (order / formatting differences are immaterial).
* **Material difference**: both clauses fully parse and the multisets
  differ (a different number of items, or a different quantity on a
  shared item, or a different item). A clause pair where either side
  fails to fully parse is NEVER a material difference (UNPROVEN, D7).

Worked examples (pinned as tests):

| Candidate clause | Target clause | Parse | FU4 result |
| --- | --- | --- | --- |
| `2x RAM + 1x CPU` | `2x RAM + 1x CPU` | byte-identical | PROVEN (count rule permitting) |
| `2x RAM + 1x CPU` | `1x CPU + 2x RAM` | both full, multisets equal | PROVEN (secondary path) |
| `2x RAM + 1x CPU` | `2x RAM + 1x SSD` | both full, multisets differ | CONTRADICTED |
| `2x RAM + 1x CPU` | `2x DDR5-6400 RAM + 1x CPU` | full/full, items differ | CONTRADICTED |
| `2x RAM + 1x CPU` | `2x RAM + a mystery gizmo` | both fully parseable (multi-word item tokens are in grammar), multisets differ | CONTRADICTED |
| `2x RAM + 1x CPU (revised)` | `2x RAM + 1x CPU` | the parenthesized qualifier is residual on one side — NOT fully parseable | UNPROVEN (never CONTRADICTED on unparseable text) |
| `GPU + power cables + bracket kit` (0034 shape) | same clause | byte-identical | PROVEN (count rule permitting) |
| `2x RAM etc.` | `2x RAM` | candidate PARTIAL (incompleteness marker) | UNPROVEN (never PROVEN, §9-C1) |

---

# 4. The six-way distinction (task item 3)

Every published bundle shape, deterministically classified by the
extraction layer (unchanged) + the FU4 evidence record (new):

| Observed shape (published text) | Extraction result (v1, FROZEN behavior) | Mapped channel (FROZEN behavior) | FU4 composition state (NEW) | Derivation consequence |
| --- | --- | --- | --- | --- |
| **Bundle form observed, no contents, no count** — `"bundle"` (bare) | `AMBIGUOUS_CUE` / `BUNDLE_WITHOUT_CONTENTS` | `UNAVAILABLE` | — (no record; channel absent) | UNPROVEN, every target |
| **Bundle quantity observed, no contents** — `"bundle of 3"`, `"3-unit bundle"` | Extraction-derived: `AMBIGUOUS_CUE` / `BUNDLE_WITHOUT_CONTENTS` (count verbatim, never bound). Corpus-shaped: the frozen channel ADMIITS an OBSERVED BUNDLE with `quantity=3` and count-only `raw_detail` (e.g. `"bundle of 3"`) — a hand- or corpus-supplied channel the extractor never produces | Extraction-derived ⇒ `UNAVAILABLE`. Corpus-shaped ⇒ `OBSERVED` / BUNDLE / qty 3 / raw_detail = the count-only phrase | ABSENT (basis `RECORDED_CHANNEL`, step 1 of §3.4) for the corpus-shaped channel; no record (channel absent) for the extraction-derived one | UNPROVEN vs every target, INCLUDING a target bundle of the same count (D6 — "equal counts without composition → UNPROVEN") |
| **Bundle contents partially described** — `"bundle: 2x RAM etc."`, `"bundle (2x RAM + 1x CPU"` (unclosed), `"bundle: 2x RAM + "` (dangling) | `OBSERVED_UNAMBIGUOUS` (established BUNDLE cue; the span is the published clause) | `OBSERVED` / BUNDLE / qty None / raw_detail = the published phrase | PARTIAL (clause recorded for audit) | UNPROVEN vs every target — partial never proves (D5 / D6), and never contradicts by its own incompleteness |
| **Bundle contents completely established** — `"bundle: 2x RAM + 1x CPU"`, `"bundle (2x RAM + 1x CPU)"` | `OBSERVED_UNAMBIGUOUS` | `OBSERVED` / BUNDLE / qty None / raw_detail = the published phrase | ESTABLISHED (verbatim clause, provenance, digest-bound) | The D6 conjunction applies (PROVEN only against a target side that is ALSO ESTABLISHED and equal; CONTRADICTED only on a materially established difference; UNPROVEN otherwise) |
| **Contents absent or ambiguous (empty markers)** — `"bundle:"`, `"bundle ()"`, `"bundle: "` | `OBSERVED_UNAMBIGUOUS` (the cue engine's established marker shape; the clause residue is empty) | `OBSERVED` / BUNDLE / qty None / raw_detail = the empty-marker phrase | ABSENT (empty clause, §3.5) | UNPROVEN vs every target — an empty marker never establishes complete composition (task item 4, final row) |
| **Contradictory published contents** — title `"bundle: 2x RAM + 1x CPU"` + structured `"Bundle (2x SSD + cable)"` | `OBSERVED_UNAMBIGUOUS` (kind + quantity consistent; the contents relation is NOT the extractor's scope, §1.4) | `OBSERVED` (primary clause only — the channel cannot express the second) | CONTRADICTED_PUBLISHED (both clauses recorded with provenance; basis `EXTRACTION_RESULT_V1`) | UNPROVEN vs every target (D8 — fail closed; the recorded absence of a single adoptable composition) |

Two shapes outside the table, for completeness:

* **Bundle form vs non-bundle target** (default single unit, pack, or
  tray): CONTRADICTED at the FORM level before any composition is read
  (D9 — the FU3 form rule, unchanged). A bundle is never pricing-
  comparable to a single unit "even when the contents name the
  requested part."
* **Two title clauses / two structured clauses** (multiple offers are
  out of scope — one observation = one offer, frozen): within one
  examined field, the cue engine's ordered alternatives never emit
  overlapping pairs; two disjoint established bundle clauses in one
  field are possible published text and are handled by the same
  CONTRADICTED_PUBLISHED rule (the evidence reads the result's full cue
  list, D3).

---

# 5. The FU4 comparison rules (task item 4) — exact derivation

`derive_sales_unit_authority_fu4(channel, candidate_composition,
target_evidence)` — pure, deterministic, zero-live, replayable;
`TypeError` / `ValueError` on foreign or contract-misuse inputs; the
unit returned is the frozen `SalesUnitAuthorityV2` (D11).

**Preconditions (fail closed):**

* `channel` is the frozen type; `channel.state == UNAVAILABLE` ⇒
  return `UNPROVEN` for every target — identical to FU3, and a
  `candidate_composition` presented over an UNAVAILABLE channel is
  contract misuse (ValueError: the recorded absence admits no
  composition evidence).
* `candidate_composition` (when present) re-verifies its
  `evidence_digest` and, on the extraction basis, its binding to the
  presented channel (the record's `source` and `channel_quantity` must
  agree with the channel's `source` and `quantity` — a record cannot
  claim provenance the channel never recorded; integrity error
  otherwise).
* `target_evidence` is None, or the frozen type (D18), or the FU4 type
  (digest re-verified); a frozen record is read as composition-ABSENT.

**The decision table** (target form = the explicit target evidence's
form, or the default SINGLE_UNIT):

| # | Candidate channel | Target | FU4 unit | Rule |
| --- | --- | --- | --- | --- |
| U0 | `UNAVAILABLE` | any | **UNPROVEN** | Recorded absence (FU3-identical) |
| U1 | `OBSERVED SINGLE_UNIT` | SINGLE_UNIT (default or explicit) | **PROVEN_EQUIVALENT** | FU3-identical |
| U2 | `OBSERVED SINGLE_UNIT` | PACK / TRAY / BUNDLE | **CONTRADICTED** | FU3-identical |
| U3 | `OBSERVED PACK_QUANTITY n` | PACK_QUANTITY n (same published count) | **PROVEN_EQUIVALENT** | FU3-identical |
| U4 | `OBSERVED PACK_QUANTITY n` | any other form or count | **CONTRADICTED** | FU3-identical |
| U5 | `OBSERVED TRAY_OR_FACTORY_PACK` | non-tray form (default single unit included) | **CONTRADICTED** | FU3-identical |
| U6 | `OBSERVED TRAY_OR_FACTORY_PACK` | tray; count missing either side | **UNPROVEN** | FU3-identical (count material for trays) |
| U7 | `OBSERVED TRAY_OR_FACTORY_PACK` | tray; counts unequal | **CONTRADICTED** | FU3-identical |
| U8 | `OBSERVED TRAY_OR_FACTORY_PACK` | tray; counts equal | **PROVEN_EQUIVALENT** | FU3-identical |
| U9 | `OBSERVED BUNDLE` | non-bundle form (default single unit included) | **CONTRADICTED** | Form rule before composition (D9) — identical to FU3 |
| U10 | `OBSERVED BUNDLE` | BUNDLE; candidate composition ABSENT (no record, count-only channel, empty marker) | **UNPROVEN** | D6 / §4 row 2 — **equal counts without composition → UNPROVEN** (the FU4 restriction over FU3's count-based PROVEN) |
| U11 | `OBSERVED BUNDLE` | BUNDLE; candidate composition PARTIAL (incomplete / unclosed / dangling) | **UNPROVEN** | D5 / D6 — partial never proves, never contradicts by its own incompleteness |
| U12 | `OBSERVED BUNDLE` | BUNDLE; candidate composition CONTRADICTED_PUBLISHED | **UNPROVEN** | D8 — fail closed; every side recorded |
| U13 | `OBSERVED BUNDLE` | BUNDLE; target composition ABSENT (frozen target record, or FU4 record with None clause) | **UNPROVEN** | D6 — composition missing on the target side |
| U14 | `OBSERVED BUNDLE` | BUNDLE; target composition PARTIAL | **UNPROVEN** | D6 |
| U15 | `OBSERVED BUNDLE` | BUNDLE; both ESTABLISHED; count rule violated (both publish, counts differ) | **CONTRADICTED** | D6 count rule — published incompatible units |
| U16 | `OBSERVED BUNDLE` | BUNDLE; both ESTABLISHED; count rule holds (equal, or at least one side publishes none — no inference, D17); clauses byte-identical | **PROVEN_EQUIVALENT** | D6 — equal complete compositions, both provenances bounded (the intended capability) |
| U17 | `OBSERVED BUNDLE` | BUNDLE; same as U16, clauses byte-different, both fully parse, multisets equal | **PROVEN_EQUIVALENT** | D6 secondary path (order / formatting only) |
| U18 | `OBSERVED BUNDLE` | BUNDLE; same as U16, clauses byte-different, both fully parse, multisets differ | **CONTRADICTED** | D7 — materially established difference |
| U19 | `OBSERVED BUNDLE` | BUNDLE; same as U16, clauses byte-different, at least one side NOT fully parseable | **UNPROVEN** | D7 — the difference is textual but not materially established; no semantic / fuzzy comparison exists in this contract |

**Never an input, never inferred (FU3 list, preserved verbatim):** model
confidence, model matched / conflicting / missing-critical attributes
(a model claim of "bundle contents matched" is not independent
verification), product-title similarity beyond the recorded verbatim
clause, price, availability, or any other commercial fact; no quantity
is inferred from a missing value; no composition is inferred from a
count, a channel absence, an MPN, or a model output.

**The task's six mandated rows, mapped:** "Missing or partial
composition → UNPROVEN" = U10 / U11 / U13 / U14; "Different verified
compositions → CONTRADICTED only when the difference is materially
established" = U18 (yes) / U19 (no — UNPROVEN); "Equal counts without
composition → UNPROVEN" = U10; "Equal complete compositions with
sufficient provenance → potentially PROVEN_EQUIVALENT" = U16 / U17
("potentially" is the D6 conjunction: equality alone is not the rule —
§5.1); "Conflicting title and structured fields → fail closed" =
§4 row 6 / U12 (and, at the channel level, the frozen P2 rule: kind or
quantity conflict across the fields ⇒ `CONTRADICTED_CUES` ⇒ recorded
absence ⇒ UNPROVEN, unchanged); "Empty `bundle:` / `bundle ()` /
truncated content must never establish complete composition" = §4 row 5
/ U10 / U11 (D5 at the type level: such clauses are
un-constructible as ESTABLISHED).

## 5.1 Is byte-identity sufficient? (task item 5) — no, and here is why

Byte-identical published clauses are **necessary but not sufficient**
for PROVEN_EQUIVALENT. Identical text can still be:

1. **Incomplete** — `"bundle: 2x RAM etc."` on both sides is
   byte-identical and PARTIAL (incompleteness marker): the pages
   published the same INCOMPLETE statement; equivalence is unproven
   (U11 / U14). D5 refuses the ESTABLISHED classification at the type
   level, so the derivation cannot reach U16 on such text at all.
2. **Truncated** — `"bundle (2x RAM + 1x C"` on both sides (identical
   field-level truncation): byte-identical, PARTIAL (unclosed paren),
   UNPROVEN. The §11-T2 residual (an invisible page-level truncation of
   a colon-form clause that runs to the field end) is the one identical-
   text case the field cannot detect; it is recorded as an accepted
   epistemic boundary (§11-T2), bounded by the same independence
   requirement that bounds every recorded fact.
3. **Ambiguous in meaning** — the deterministic contract has no
   semantic layer: a clause is ESTABLISHED when it is a closed,
   non-empty, marker-free published statement; whether that statement
   is TRUE of the physical bundle is the publisher's claim (and the
   review process's attestation on the target side), exactly the
   epistemic status of every other recorded fact in this system
   (the frozen PROVEN semantics: "published as sold in the same
   commercial unit").
4. **Under-insufficient provenance** — U16 / U17 additionally require
   the bounded non-model source on both sides (the record constructors
   refuse any other value) and the D18 rule (a frozen target record can
   only ever be ABSENT — identity of text with a count-only target
   record is impossible because the record carries no clause).

Conversely, byte-identity is **not required**: U17 admits an equal,
fully parsed multiset (order / formatting differences) under the
versioned grammar — a strictly bounded relaxation, with the grammar's
residuals failing closed to UNPROVEN (U19).

**Sufficient provenance, stated:** candidate side — the clause is a
verbatim span of a published field with the frozen source label
(`LISTING_TITLE` / `PUBLISHED_STRUCTURED_FIELD`), digest-bound to the
verified extraction result (basis a) or to the recorded channel (basis
b); target side — the clause is verbatim published text supplied under
one of the two frozen attestation classes (`REVIEWED_TARGET_CONTEXT` /
`REQUEST_DESCRIPTION`). That conjunction is what U16 / U17 call
"sufficient"; it is provenance of PUBLICATION, not of PHYSICAL TRUTH
(§3.6), and it is the strongest the deterministic contract can express.

## 5.2 Tier derivation (unchanged machinery, new unit input)

`derive_authority_tier_fu4(assessment_v2, sales_unit_channel,
evaluation, context_provenances, product_evidence, human_review, *,
target_unit_evidence, candidate_composition)` = the frozen S2-A-FU2
derivation (called, never re-implemented) + the FU3
`IdentityResolutionBoundV2` (delegated — byte-identical) + the FU4 unit
derivation (above) + the SAME two restrict-only ceilings on the
automatic tier (`UNPROVEN` ⇒ `CEILING_SALES_UNIT_NOT_PROVEN`;
`CONTRADICTED` ⇒ `CEILING_SALES_UNIT_CONTRADICTED`; `PROVEN_
EQUIVALENT` ⇒ the automatic tier stands). Result: a NEW
`AuthorityDecisionV2FU4` (D11) with the FU3 record's field set and
construction invariants (AI_ASSISTED with an UNPROVEN / CONTRADICTED
unit is un-constructible; each ceiling rule only with its unit state on
`NEEDS_REVIEW`; `frozen_fired_rules` projection onto the frozen
vocabulary). Human overlay precedence (HARD_CONFLICT > HUMAN_CONFIRMED
> AI) unchanged: a human may confirm a firewall-capped bundle candidate
— the explicit, auditable path is preserved.

## 5.3 Per-binding dispatch (the FU4 superset)

`derive_authority_tier_for_contract_fu4(token, …)`:

* `SEMANTIC_AUTHORITY_V2_S2A_FU2` ⇒ the frozen `derive_authority_tier`
  (delegated; sales-unit inputs are contract misuse — the frozen rule,
  preserved);
* `SEMANTIC_AUTHORITY_V2_S2A_FU3` ⇒ the frozen `derive_authority_tier_
  fu3` (delegated byte-identically; composition inputs are contract
  misuse under FU3 — the FU3 contract has no composition axis, and
  silently dropping or interpreting them would be a re-interpretation);
* `SEMANTIC_AUTHORITY_V2_S2A_FU4` ⇒ `derive_authority_tier_fu4` (the
  channel REQUIRED, as under FU3);
* anything else ⇒ `UnknownAuthorityContractTokenError` (reused from the
  frozen FU3 module — the exception is vocabulary, importing it changes
  nothing); non-string ⇒ `TypeError`.
* `KNOWN_AUTHORITY_CONTRACT_TOKENS_FU4 = {FU2, FU3, FU4}` (the FU4
  module's own constant; the frozen FU3 constant stays exactly
  `{FU2, FU3}`, byte-frozen).

The delegation identity (FU4-dispatch arm ⇒ frozen function, same
inputs ⇒ same output, same exceptions) is a PINNED test property
(§9-A2 / A7): the historical tokens replay identically under the FU4
code, which is the per-binding discipline made mechanical.

---

# 6. The smallest versioned FU4 authority contract (task item 6)

The future implementation phase (CONTRACT-ONLY, the FU1 / FU2 / P1 /
P2 precedent: no wiring, no deployment, production behavior identical to
its starting SHA because no live path references the token) delivers
EXACTLY:

1. **New module** `product_intelligence/research/semantic_authority_
   fu4.py` (name proposed; research layer; stdlib + the research
   package's public surface + the frozen FU3 / FU2 / S2-C / extraction
   modules; no Django, no I/O, no clock, no network, no LLM, no mutable
   global state, no vendor names; import-self-checked, the FU3 pattern).
2. **The token** `AUTHORITY_CONTRACT_VERSION_V2_FU4 =
   "SEMANTIC_AUTHORITY_V2_S2A_FU4"` (a new string; distinct from FU2 /
   FU3 by import check) and `KNOWN_AUTHORITY_CONTRACT_TOKENS_FU4`.
3. **The evidence schema** (§3): `BundleCompositionStateV2FU4`,
   `CandidateCompositionEvidenceBasisV2FU4`,
   `CandidateBundleCompositionEvidenceV2FU4`,
   `TargetSalesUnitEvidenceV2FU4`, the clause extraction (§3.4), the
   closure classification (§3.5), the materiality grammar (§3.7), and
   the integrity error type (`BundleCompositionEvidenceIntegrityError`).
   `BUNDLE_COMPOSITION_EVIDENCE_VERSION_FU4 = 1`.
4. **The construction entry points** (fail closed):
   `candidate_composition_from_extraction(result) ->
   CandidateBundleCompositionEvidenceV2FU4 | None` — re-verifies the
   presented result FIRST (`verify_integrity`), returns None for every
   non-OBSERVED_UNAMBIGUOUS state and for a non-BUNDLE established kind,
   and for an OBSERVED BUNDLE result reads the result's FULL established
   BUNDLE cue list (primary = the channel mapping's primary cue rule:
   structured first, else first title span order): one clause ⇒
   classified (§3.5); ≥2 differing clauses ⇒ CONTRADICTED_PUBLISHED
   (every clause recorded); identical repeated clauses ⇒ ESTABLISHED
   (consistent repetition, the count-rule precedent).
   `candidate_composition_from_channel(channel) ->
   CandidateBundleCompositionEvidenceV2FU4` — the `RECORDED_CHANNEL`
   basis, §3.4 steps 1–3 over the channel's `raw_detail` (OBSERVED
   BUNDLE only; anything else is contract misuse).
5. **The unit derivation** `derive_sales_unit_authority_fu4` (§5) and
   the case-level `derive_sales_unit_authority_fu4_case(case_v2, …)`
   (the frozen case-type entry point, mirroring `derive_sales_unit_
   authority`).
6. **The tier derivation** `derive_authority_tier_fu4` + the decision
   record `AuthorityDecisionV2FU4` + the mirrored rule vocabulary
   `AuthorityRuleV2FU4` (import-self-checked EQUAL to the FU3 set — D10).
7. **The dispatch** `derive_authority_tier_for_contract_fu4` (§5.3) and
   `is_known_authority_contract_token_fu4`.
8. **The research package export surface** — strictly additive
   (`research/__init__.py` gains the FU4 symbols; the FU3 / P2 export
   blocks are untouched).
9. **A NEW test file** `tests/research/test_semantic_authority_v2_fu4.
   py` implementing the §9 matrix (plus the existing P2 / P2-FU1
   (two files) and FU3 test files re-run UNCHANGED as the preservation
   proof).

**Deliberately NOT in the contract phase** (each is the separately
gated registration step or a later phase): no binding constant, no
harness pin change, no corpus artifact, no codec adapter, no replay-
registry change, no record-type change, no persistence, no pricing
wiring, no deployment, no capture, no migration.

---

# 7. Binding, replay, and qualification changes (task items 6 / 7)

## 7.1 The binding tuple — and why the input-schema axis does NOT move

The FU4 production binding is:

```
("V2", "2.1", 1, 1, "SEMANTIC_AUTHORITY_V2_S2A_FU4")
```

Axis by axis: semantic contract V2 (unchanged), prompt 2.1 (UNCHANGED
TEXT — no new prompt version, §7.4), input schema 1 (UNCHANGED — D2:
the composition facts are derivation-input records, not case fields;
the recorded V2 input is byte-identical in shape), output schema 1
(unchanged — the 7-key response stays 7 keys under all bindings, the
Q3-B4 §5.6 invariance), authority contract = the new FU4 token.

The binding constant is composed from the frozen exports (the P1
discipline: no literal token in source; drift-pinned by test) and is
owned by the semantic layer at registration (a research module cannot
import the semantic layer — dependency direction). Proposed owner: the
Prompt 2.1 contract module's registry surface, extended by the
registration phase (the FU3 binding lives in `contract_v2_1.py` line
111; the FU4 successor is added alongside, the existing constant
byte-unchanged).

## 7.2 The contract phase changes NO registry

At the FU4 contract phase endpoint: the production codec knows exactly
the V1 + 2.0/FU2 bindings (unchanged); `SUPPORTED_CONTRACT_BINDINGS`
(replay) is unchanged; `BINDING_CORPUS_VERSIONS` /
`KNOWN_PRODUCTION_BINDINGS` (harness) are unchanged (exactly the two
production bindings); the gates / report / capture / direct-capture /
cli pins are unchanged; the live record type still pins the FU2 token;
no record can carry the FU4 token (the same isolation property that
made FU1 / FU2 / P1 / P2 deployable without behavior change). An FU4-
bound payload is refused by the production codec — pinned by test,
mirroring `test_an_fu3_bound_payload_is_refused_by_the_production_codec`
(§9-A4).

## 7.3 The separately gated registration step (specified, not executed here)

When — and only when — an explicit versioned compatibility decision
approves FU4-bound production records (the same gate shape the P2
"smallest separately gated integration" proposal uses), the
registration step delivers EXACTLY:

1. **The semantic-layer binding constant** (§7.1) with the P1-style
   import self-checks (axis composition; the 2.1/FU3 binding byte-
   unchanged alongside).
2. **The corpus 1.2.0 binding-only re-seal** (D14): NEW artifacts
   `corpus_2_1_fu4.json` + `manifest_2_1_fu4.json` (names proposed):
   56/56 per-case documents byte-identical to 1.1.0, `label_revisions`
   empty, exactly `{corpus_version, semantic_contract_binding,
   corpus_digest}` moved; a new `CORPUS_VERSION_2_1_FU4 = "1.2.0"`
   constant; the 1.0.0 / 1.1.0 artifacts and digests re-pinned by test.
3. **The harness registry extension** (corpus.py):
   `BINDING_CORPUS_VERSIONS` gains the third entry
   `(("V2","2.1",1,1,FU4) → "1.2.0")`; `KNOWN_PRODUCTION_BINDINGS`
   becomes exactly the three production bindings; gates / report /
   capture / direct-capture / cli accept the three, fail closed on
   every cross-binding combination (a 2.1/FU3 capture against the 1.2.0
   corpus is refused and vice versa; a 2.0 prompt axis under the FU4
   binding is refused; an unknown fifth-tuple is refused).
4. **The codec + replay extension**: a new registered contract adapter
   for the FU4 binding (the `SemanticDecisionRecord` model docstring's
   stated extension point: "A future semantic contract … reuses this
   row by registering a new contract adapter; no model change, no new
   migration, no data rewrite"); the FU4-bound record carries, inside
   its payload's evaluation section: the FU4 decision record
   (`AuthorityDecisionV2FU4`), the two evidence records' canonical
   documents (digests included), and the bound + unit + tier + fired-
   rules derived snapshots — replay re-derives under
   `derive_authority_tier_for_contract_fu4` and proves exact agreement
   (the Q3-B4 §6.1 item-5 discipline, as executed for FU3).
5. **The offline no-capture baseline reports** for the FU4 binding over
   both pinned candidates (the P1 arithmetic: the committed baselines
   are no-capture; the FU4 versions derive the same recorded inputs
   through the FU4 dispatch — for the current corpus shapes every
   bundle case is either UNPROVEN-restricted or form-CONTRADICTED, so
   the baselines' gate arithmetic is binding-agnostic by construction
   (the Q3-B4 §6.2 "qualification arithmetic is binding-agnostic"
   property)).
6. **The Q3-C interaction**: qualification remains conditioned on the
   firewall disposition (AD-Q3B4-6, unchanged); a future qualified
   state under the FU4 binding inherits the same ceilings; W1's guard
   predicate is unchanged (it reads `SalesUnitAuthorityV2`, whose
   vocabulary is unchanged — the FU4 token only changes WHEN each state
   is derived for bundles).

**Migration-free** throughout: no Django model change
(`makemigrations --check --dry-run` stays "No changes detected"); the
envelope is opaque and versioned; old rows decode under their own
binding; no data rewrite (§10).

## 7.4 Prompt 2.1: new binding, no new prompt version (task item 7 — the explicit determination)

**Question:** does Prompt 2.1 require a NEW binding, or is a separate
DOWNSTREAM authority token sufficient?

**Determination: both statements are true at their respective levels,
and the design requires the new binding — the token alone is
insufficient for records.**

* **No new prompt version.** The 2.1 system prompt is model-level
  instruction text; it names no authority token and describes no
  derivation. Its COMMERCIAL SALES-UNIT RULES commit the model to:
  absolute rule on published incompatible packaging (NO_MATCH +
  PACKAGING_QUANTITY / BUNDLE), UNCERTAIN on ambiguous cues (incl.
  bundles of unclear wording — the P6 shape), never reading
  UNAVAILABLE as single unit or equivalence, and asserting nothing
  about price comparability unless "published packaging evidence
  establishes the same commercial unit." FU4 changes none of the
  model's duties: the model still sees the same recorded input (input
  schema 1, D2), still emits the same 7-key response (output schema 1),
  and still applies the same decision rules. A 2.2 version would be a
  phantom version (the 2.1 module's own import check refuses a version
  bump without a text change) — and no text change is needed. The
  prompt's line "published packaging evidence establishes the same
  commercial unit (report it in matched_attributes where it does)"
  remains exactly correct under FU4: two established, equal,
  provenanced compositions ARE published evidence establishing the same
  commercial unit, and the model's MATCH-side reporting is unaffected
  by which token the authority layer later derives under.
* **A downstream token alone is NOT sufficient for record identity.**
  The per-binding discipline (Q3-B4 §6.5: "the recorded authority token
  selects the derivation … a future binding is a future adapter — never
  an implicit reinterpretation of this one"; Q3-B4 §6.1 item 5: a bound
  record carries the derived snapshots OF ITS TOKEN) means: a record's
  authority axis must name the contract under which its derived
  snapshots were produced. Reusing the existing 2.1 binding
  `("V2","2.1",1,1,FU3)` for FU4-governed records would (i) let a
  FU4-derived snapshot be replayed as a FU3 derivation (wrong
  re-interpretation — the FU3 arm cannot see composition inputs,
  §5.3), or (ii) force the FU3 dispatch to accept composition inputs
  (an amendment of a frozen module — forbidden). The task's own rule
  applies: **do not silently reuse an existing binding for changed
  authority semantics.** Therefore the FU4 successor binding
  `("V2","2.1",1,1,"SEMANTIC_AUTHORITY_V2_S2A_FU4")` is REQUIRED for
  any record governed by FU4, and is a separately gated registration
  step (§7.3) — the token is the derivation identity, the binding is
  the record / corpus / harness identity; both move together, and
  neither moves in the contract phase.
* **Coexistence.** The 2.1/FU3 binding, its corpus 1.1.0, its captures,
  its baseline reports, and its qualification lineage (Q3-C) remain
  fully valid and byte-frozen; the 2.1/FU4 binding is a SUCCESSOR
  lineage, sealed under its own corpus version, qualifying only
  artifacts it itself produced. Cross-lineage combinations fail closed
  (the registry extensions of §7.3 step 3).

## 7.5 The Q3-B4 roadmap position

FU4 is the bounded contract phase that the Q3-B5-P2-FU1 interaction
review reserved ("separately approval-gated"). It does not reorder the
approved roadmap: the Q3-B4 P3 (authority-side grounding) ordering
constraint (iii) is unaffected (FU4 is downstream of the firewall, like
FU3); P2 remains independent (iv) and remains the extraction basis of
this contract (D3); Q3-C remains conditioned on the FU3 disposition
(AD-Q3B4-6) — the FU4 registration is its own later decision and, being
strictly more restrictive for bundles than FU3 (§2 safety-direction
audit), cannot widen any exposure the Q3-B4 decision already bounded;
W1 ships its atomic guard regardless (ordering constraint (i)).

---

# 8. Replay preservation plan (every frozen token and historical record)

**Byte-frozen at the FU4 contract phase (file-level SHA-256 pins, the
FU3-test precedent `tests/research/test_semantic_authority_v2_fu3.py`
line 144 ff. — the digests are computed at the implementation phase's
starting SHA and pinned in the new test file):**

| Frozen input | Why it must not move |
| --- | --- |
| `research/semantic_authority_v2.py` (FU2 token) | The frozen S2-A contract; old records' replay |
| `research/semantic_authority_fu3.py` (FU3 token) | The separately versioned firewall; Q3-B4-FU2 approved; the P2-FU1 STOP-check left it deliberately unchanged |
| `research/sales_unit_extraction.py` (schema v1) | P2 / P2-FU1 (pending final review); the candidate-side evidence basis; its state resolution is NOT the place to police contents (D3 / §1.4) |
| `research/semantic_v2.py` (S2-C-FU1 channel + case) | The frozen recorded input (input schema 1); D2 keeps the axis at 1 |
| `research/semantic_decision_v2.py` + `research/semantic_decision_codec.py` + `research/semantic_decision_replay.py` | The production record / codec / replay registries (§1.6); D13 / §7.2 |
| `semantic/contract_v2.py`, `semantic/contract_v2_1.py`, `semantic/runtime_v2.py` | The frozen 2.0 / 2.1 prompts (digests of record) and the runtime pins |
| `evaluation/semantic_v2/*` (gates, corpus, report, capture, direct-capture, cli, policy) | The qualification registry + the DRAFT policy (byte-unchanged) |
| `evaluation/semantic_v2_qualification/corpus_v1.json` + `corpus_2_1.json` + both manifests | The corpus of record (1.0.0 / 1.1.0 digests re-pinned) |
| `V2_AUTHORITY_QUALIFIED = False` (both pinned locations) | No promotion |

**Behavior-frozen (suite-level):**

* The full FU3 suite (98 nodes, `tests/research/test_semantic_authority_
  v2_fu3.py`) passes UNCHANGED, including every old-token invariance
  pin and the Q3-B4-FU2 correction nodes.
* The full P2 / P2-FU1 extraction suites (111 nodes,
  `tests/research/test_sales_unit_extraction.py`; 7 nodes, `tests/
  research/test_sales_unit_extraction_recorded_pages.py`) pass
  UNCHANGED.
* The P1 binding-replay suite (`tests/evaluation/semantic_v2/
  test_q3b5_p1_binding_replay.py`) passes UNCHANGED (the two known
  production bindings, the codec refusal of FU3 payloads, the corpus
  seal pins).
* The frozen 2.0 / 1.0.0 and 2.1 / 1.1.0 replay lineages produce
  byte-identical derivations (the per-binding dispatch is untouched at
  the contract phase; the FU4 dispatch's FU2 / FU3 arms delegate to the
  frozen functions — delegation identity pinned, §9-A2 / A7).

**Historical records:** every persisted record (V1, 2.0/FU2) decodes
and replays under its own registered binding exactly as before; no
record is re-derived under FU4; no artifact is re-sealed, relabeled, or
rewritten. The ONE deliberately coexisting semantic difference (same
recorded inputs, different TOKEN ⇒ different bundle states, e.g. a
corpus-shaped count-only BUNDLE pair: FU3 ⇒ PROVEN, FU4 ⇒ UNPROVEN) is
pinned as a two-token test row (§9-A7) so it is documented behavior
of per-binding replay, never silent drift.

---

# 9. Mandatory adversarial test matrix (task item 8)

Conventions (the Q3-B4 §8 matrix / FU3 / P2 precedent): every case is an
OFFLINE recorded-input construction (synthetic `ListingObservation` +
the frozen extractor chain, or a directly constructed frozen channel /
result / record), with scripted evaluation doubles; NO live call, NO
model capture, NO network. Assertions split: (i) extraction state +
cue shape (frozen, unchanged), (ii) composition evidence record (state,
clause, provenance, digest), (iii) FU4 unit state, (iv) FU3 unit state
under the SAME inputs (the coexistence pin), (v) tier under
MATCH + HIGH + STRONG + clean over the FU4 dispatch (the Q3-B4 §4.1
invariant), (vi) the expected ceiling rule / rejection. Rows:

**A — Preservation (the frozen side of the ledger)**

* **A1.** File-digest pins: FU2, FU3, P2 extraction, S2-C channel, 2.0
  contract, 2.1 contract, runtime_v2, codec, replay, harness modules —
  all byte-identical to the phase's starting SHA; the two corpus
  artifacts' digests re-pinned; the DRAFT policy byte-unchanged.
* **A2.** Delegation identity: over a fixed parameterized input set
  (the FU3 suite's shapes), `derive_authority_tier_for_contract_fu4`'s
  FU2 arm ≡ `derive_authority_tier`, and its FU3 arm ≡
  `derive_authority_tier_fu3` (same decision fields, same fired rules,
  same exceptions); unknown token ⇒ `UnknownAuthorityContractTokenError`;
  non-string ⇒ `TypeError`.
* **A3.** The full 98-node FU3 suite (`tests/research/test_semantic_
  authority_v2_fu3.py`) and the full P2 / P2-FU1 extraction suites
  (111 nodes in `tests/research/test_sales_unit_extraction.py` + 7 in
  `tests/research/test_sales_unit_extraction_recorded_pages.py`) pass
  UNCHANGED (no rename / skip / xfail / weaken — the CLAUDE.md test-
  preservation contract).
* **A4.** The production codec registry still knows exactly the V1 +
  2.0/FU2 bindings; an FU4-bound payload (hand-constructed) is refused
  by the production codec and the replay registry (mirrors the FU3
  refusal pin); the live record type still pins the FU2 token;
  `V2_AUTHORITY_QUALIFIED` False in both pinned locations; no live
  module imports the FU4 module (AST / lexical scan, the P2 / FU3
  reachability guard).
* **A5.** `manage.py check` clean; `makemigrations --check --dry-run`
  "No changes detected" (no model change — the component is pure
  research layer + tests).
* **A6.** Collection non-decreasing; node-level diff: 0 removed / 0
  renamed; the addition is exactly the new test file's nodes (+ the
  auto-expanded parameterized boundary scans the new research file
  triggers: research-core per-file x4, domain +1, providers +1, runs
  +1, web +1 — the P2 precedent, +8 for a new research file).
* **A7.** The two-token coexistence pin: the SAME recorded inputs
  (a corpus-shaped channel OBSERVED BUNDLE, `quantity=3`,
  `raw_detail="bundle of 3"`, vs the frozen target record BUNDLE
  `quantity=3`) derive `PROVEN_EQUIVALENT` through the FU4 dispatch's
  FU3 arm (the frozen count-based behavior, preserved) and
  `UNPROVEN` through its FU4 arm (D6 / §4 row 2) — coexisting results
  under coexisting tokens, pinned as documented per-binding behavior,
  never as drift (the §8 coexistence statement, test-able).

**B — The composition evidence schema (construction-level)**

* **B1.** The six-way distinction (§4) over published text: bare
  `"bundle"`; `"bundle of 3"` / `"3-unit bundle"`; `"bundle: 2x RAM
  etc."`; `"bundle (2x RAM + 1x CPU"`; `"bundle: 2x RAM + 1x CPU"` /
  `"bundle (2x RAM + 1x CPU)"`; title `"bundle: 2x RAM + 1x CPU"` +
  structured `"Bundle (2x SSD + cable)"` — each yields exactly the
  recorded extraction state (frozen) AND exactly the recorded FU4
  evidence state (ABSENT / PARTIAL / ESTABLISHED /
  CONTRADICTED_PUBLISHED), with the clause text verbatim and the
  provenance (field + source + span / basis + digest) intact.
* **B2.** Empty markers never establish: `"bundle:"` (title-final),
  `"bundle ()"`, `"bundle: "`, `"bundle ("` (unclosed, title-final) —
  all ABSENT or PARTIAL; the ESTABLISHED constructor REFUSES such a
  clause (un-constructible, D5 at the type level).
* **B3.** Count-only never bound: over `"bundle of 3"`, the evidence
  (via a corpus-shaped channel with quantity 3) is ABSENT with
  `channel_quantity = 3` mirrored verbatim; no derivation input
  carries a composition clause; the count is never salvaged into the
  clause.
* **B4.** Provenance refusal: a record whose `source` is any
  non-extractor frozen member (SPECIFICATION_TEXT /
  REVIEWED_PRODUCT_CONTEXT) or whose target `source` is any non-frozen
  value is un-constructible; a model-claim basis cannot exist in the
  vocabulary (the enum is bounded to the two non-model members per
  side).
* **B5.** Integrity: a tampered evidence record (clause edited, digest
  not recomputed; basis / digest mismatch; a `RECORDED_CHANNEL` record
  claiming extraction digests; `CONTRADICTED_PUBLISHED` with
  `additional_clauses == ()`; a clause set where "additional" equals
  primary) is refused — construction and presentation
  (`evidence_digest` re-verification at the derivation) —
  `BundleCompositionEvidenceIntegrityError`; a tampered / forged
  extraction result (the P2 gate) produces no evidence record.
* **B6.** Determinism: equal inputs ⇒ byte-equal records (canonical
  document + digest); the canonical order of `additional_clauses`
  (field order, then span order) is pinned.
* **B7.** The frozen target record under FU4 (D18): accepted as
  composition-ABSENT for a BUNDLE form (UNPROVEN vs a composition-
  verified candidate); non-BUNDLE forms with composition fields are
  un-constructible.
* **B8.** Clause-grammar edges (pinned verbatim): `"2x RAM + 1x CPU"`
  vs `"1x CPU + 2x RAM"` (multiset-equal ⇒ U17); vs `"2x RAM + 1x SSD"`
  (multiset-differ ⇒ U18); vs `"2x RAM + 1x CPU (revised)"` (residual
  ⇒ U19 UNPROVEN); `"GPU + power cables + bracket kit"` (the 0034
  shape, fully parseable); a quantity edge (`"04x RAM"` non-canonical
  ⇒ not fully parseable ⇒ U19); a trailing `"2x"` (dangling
  incomplete token ⇒ PARTIAL, never ESTABLISHED).

**C — The comparison rules (task item 4, one row per mandated rule)**

* **C1.** Missing or partial composition ⇒ UNPROVEN: every pair in
  {candidate ABSENT × target any; candidate PARTIAL × target ESTABLISHED
  (byte-identical text); candidate ESTABLISHED × target ABSENT (frozen
  record — the "contents known on only one side" regression, now
  preserved under FU4); candidate ESTABLISHED × target PARTIAL} over
  EVERY target shape (default single unit, explicit bundle ± count).
* **C2.** Equal counts without composition ⇒ UNPROVEN: corpus-shaped
  channel BUNDLE quantity 3 (raw_detail `"bundle of 3"`) vs target
  BUNDLE quantity 3 (frozen record) — FU4 UNPROVEN while the SAME
  inputs derive FU3 PROVEN_EQUIVALENT (the coexistence pin, A7's
  shape); and vs target BUNDLE no count — both tokens UNPROVEN.
* **C3.** Materially established difference ⇒ CONTRADICTED: U18 over
  MATCH + HIGH + STRONG + clean ⇒ tier NEEDS_REVIEW with
  `CEILING_SALES_UNIT_CONTRADICTED` fired; the Q3-B4 §4.1 invariant: NEVER
  `AI_ASSISTED_COMPARABLE`; the hand-constructed `AuthorityDecisionV2
  FU4` with that tier + unit is un-constructible (the constructor
  invariant).
* **C4.** Unestablished difference ⇒ UNPROVEN (U19, B8 residual rows) —
  never CONTRADICTED; the tier cap is `CEILING_SALES_UNIT_NOT_PROVEN`.
* **C5.** Equal complete compositions with sufficient provenance ⇒
  PROVEN_EQUIVALENT (U16 / U17): the tier STANDS under MATCH + HIGH +
  STRONG (no ceiling fired) — the positive row proving FU4 can
  represent verified-composition equivalence the frozen channel cannot
  (the Q3-B5-P2-FU1 regression 8 shape, now lifted off UNPROVEN by the
  new evidence, still gated by qualification); the same row with the
  count rule violated (both publish, counts differ) ⇒ CONTRADICTED (U15).
* **C6.** Conflicting title and structured fields ⇒ fail closed (U12 /
  D8): extraction `OBSERVED_UNAMBIGUOUS` with two differing established
  clauses ⇒ evidence CONTRADICTED_PUBLISHED ⇒ UNPROVEN for every
  target; both clauses recorded (audit); the kind / quantity-conflict
  shape (frozen P2: `CONTRADICTED_CUES` ⇒ recorded absence ⇒ UNPROVEN)
  is re-pinned unchanged.
* **C7.** Form before contents: an ESTABLISHED composition against a
  default single-unit target / pack / tray ⇒ CONTRADICTED (U9) — the
  composition is never read to "explain away" a form mismatch.
* **C8.** MPN-in-clause non-inference: clauses differing only in an
  embedded part number (e.g. `"1x SSD M.2 9A0…" vs "1x SSD M.2 9B0…"`)
  ⇒ multiset-differ ⇒ CONTRADICTED (the items differ — no identity
  weight given); clauses where the identifier makes the entry
  unparseable ⇒ U19 UNPROVEN; in NO row is the target MPN or the
  candidate MPN an input to the comparison (signature-pinned).
* **C9.** Model-output non-inference: a scripted evaluation whose
  `matched_attributes` claims BUNDLE / PACKAGING_QUANTITY agreement
  changes NOTHING under the FU4 dispatch (the unit derivation's inputs
  are signature-pinned: channel + evidence records only); the
  `AuthorityRule` trail never gains a model-sourced rule.

**D — Tier, overlay, and the Q3-B4 §4.1 invariant**

* **D1.** The exact Q3-B4 §4.1 composition (MATCH + HIGH + STRONG + clean +
  U1 exact-identifier) over: silent multi-bundle (no cue) ⇒ UNPROVEN
  ⇒ NEEDS_REVIEW (`CEILING_SALES_UNIT_NOT_PROVEN`); count-only pair
  (C2) ⇒ UNPROVEN ⇒ NEEDS_REVIEW; material difference (C3) ⇒
  CONTRADICTED ⇒ NEEDS_REVIEW (`CEILING_SALES_UNIT_CONTRADICTED`);
  verified equal (C5) ⇒ PROVEN ⇒ `AI_ASSISTED_COMPARABLE` STAYS (the
  firewall's own design: a proven unit leaves the automatic tier
  standing — pricing eligibility still requires the separately gated
  W1 guard + qualification; `V2_AUTHORITY_QUALIFIED` False).
* **D2.** Human overlay preserved: a firewall-capped bundle candidate
  (UNPROVEN or CONTRADICTED) confirmed by a recorded
  `HumanReviewStateV2` CONFIRM derives `HUMAN_CONFIRMED` under the FU4
  dispatch (precedence HARD_CONFLICT > HUMAN_CONFIRMED > AI unchanged;
  a model-reported ALWAYS_HARD BUNDLE conflict still supersedes the
  overlay — the frozen rule, unchanged).
* **D3.** The ceiling rules never lift, never touch
  `MACHINE_VERIFIED`, never fire outside the automatic tier (the FU3
  invariants re-proven over the FU4 decision type).

**E — Binding / replay / qualification (contract phase + specified registration)**

* **E1.** Contract phase: the registries are exactly as §1.6 (A4); the
  two committed corpus artifacts' digests re-pinned; the committed 2.1
  no-capture baselines are refused on any non-1.1.0 corpus (unchanged
  P1 pins).
* **E2.** Registration step (specified; executed by its own phase): the
  1.2.0 re-seal verified field-by-field with independently recomputed
  digests (56/56 per-case documents byte-identical to 1.1.0;
  `label_revisions` empty; exactly `{corpus_version, semantic_contract_
  binding, corpus_digest}` moved); the harness accepts exactly three
  production bindings; every cross-binding combination (2.1/FU3
  capture × 1.2.0 corpus; 2.1/FU4 capture × 1.1.0 corpus; 2.0 prompt
  axis × FU4 binding; forged fifth-tuple variants; whitespace / case
  token variants) fails closed; the offline FU4 no-capture baselines
  seal under the FU4 binding.
* **E3.** Replay: an FU4-bound record (hand-constructed per §7.3 step 4)
  replays through the FU4 adapter with exact derived-agreement
  (bound + unit + tier + fired rules re-derived and byte-equal); the
  same recorded case under its FU3 binding replays under FU3 with the
  FU3 result (no cross-derivation); an unknown token in a record
  payload fails closed.

**F — False-positive resistance (the never-infer list, FU4 edition)**

* **F1.** No composition is derived from: price, availability,
  condition, seller, offer URL, the raw reference (never read), the
  identifier fields (set-aside only), the model output, absence, a
  matching MPN, one listing, or one price (each pinned by a negative
  construction, the P2 matrix pattern).
* **F2.** Specification quantities inside a clause are item text, not
  counts: `"1x 960GB SSD + 1x fan"` parses as entries `(1,"960gb ssd"),
  (1,"fan")` — no parsed quantity or item is ever promoted to the
  bundle's channel / target quantity (D17: the quantity is only what
  the frozen channel or target record publishes); and a clause with an
  out-of-grammar residual (e.g. `"1x 960GB SSD + 1x fan (tray)"` —
  parentheses are not in the item-token character class) is NOT fully
  parseable ⇒ U19 UNPROVEN, never CONTRADICTED from a half-understood
  clause.
* **F3.** Multi-offer independence (frozen): two observations with
  different bundle clauses extract independently (distinct input
  digests); no cross-contamination into any evidence record.

---

# 10. Migration-free compatibility strategy

1. **No persistence change, contract phase:** the FU4 component is pure
   research layer + tests (no model, no migration, no codec
   registration) — the P2 / FU1 / FU2 isolation property;
   `makemigrations --check --dry-run` stays clean.
2. **The extension point is already stated by the storage contract:**
   `runs/models.py` `SemanticDecisionRecord` (line 845 ff.) — "the
   artifact is a versioned contract … A future semantic contract …
   reuses this row by registering a new contract adapter; no model
   change, no new migration, no data rewrite is required by the mere
   existence of a new semantic contract version. Unknown or future
   semantic contracts stored here are durably identifiable but fail
   closed on interpretation." The FU4 binding's record adapter
   (§7.3 step 4) is exactly this path.
3. **Binding coexistence, not migration:** every artifact keeps its own
   sealed binding (2.0/FU2 ↔ 1.0.0, 2.1/FU3 ↔ 1.1.0, 2.1/FU4 ↔ 1.2.0);
   no historical corpus, capture, baseline report, or persisted record
   is re-sealed, rewritten, or re-derived; the old registries remain
   true (the harness registry GAINS an entry at registration; nothing
   is removed or re-pointed).
4. **Replay is per-binding forever:** the recorded token selects the
   derivation (§5.3); the FU4 dispatch delegates FU2 / FU3 to the
   frozen functions (identity pinned, A2); the old replay path
   (`SUPPORTED_CONTRACT_BINDINGS` pre-registration) is byte-unchanged
   and keeps refusing FU4 payloads (A4).
5. **Corpus governance is additive:** 1.2.0 is a NEW sealed artifact;
   1.0.0 / 1.1.0 digests are re-pinned by test (A1 / E2); labels are
   untouched (the Q3-B4 §5.4(3) property: the firewall family changes
   no label — the corpus labels decisions / conflicts / missing
   dimensions, never tiers or compositions).
6. **Rollback is a non-event:** the contract phase adds one module +
   one test file + the research export block; deleting neither affects
   any live path (A4); at registration, the harness / codec changes are
   additive registry entries behind their own pins — no data path is
   rewired.

---

# 11. Unresolved tradeoffs (recorded for the approval decision)

* **T1 — The secondary equality path (U17).** Byte-identity (U16) is
  the primary, trust-minimal path; the full-parse multiset path
  (U17) admits order / formatting differences. Tradeoff: it widens the
  PROVEN population by exactly the shapes where a deterministic grammar
  proves the published item multisets equal; every grammar gap fails
  to UNPROVEN (U19), never to CONTRADICTED. Rejected alternative:
  byte-identity ONLY (simpler contract; genuinely equal published
  compositions differing in item order would stay UNPROVEN
  indefinitely). Rejection path: if approval prefers the narrower
  contract, U17 is deleted (one table row + B8's equal-multiset rows)
  without touching any other decision — the grammar constants stay
  versioned for the materiality test.
* **T2 — Field-end closure for colon-form clauses.** A colon-form clause
  running to the end of the examined field is treated as closed
  (ESTABLISHED if otherwise clean). Residual risk: an invisible page-
  level truncation (the title cut at max length mid-clause) is
  undetectable from the field; two identically truncated pages could
  then derive PROVEN over the truncated statement. Rejected
  alternative: require a positive terminator (comma / semicolon /
  paren) — strictly safer but fails the common real-title shape
  (`"…SSD bundle: 2x RAM + 1x CPU"`) and keeps it UNPROVEN forever.
  The risk is bounded by §5.1(2)'s independence requirement (both
  sides must publish the same statement) and by the review attestation
  on the target side; it is recorded here, not papered over. The
  dangling-separator / incomplete-token rule (§3.5) is the deterministic
  slice of the risk that IS detectable, and is enforced.
* **T3 — Target provenance independence.** The derivation cannot verify
  that the target clause was not copied from the candidate page (text
  independence is not a deterministic contract fact). The contract
  records both source labels in the decision's audit surface (visible
  to the reviewer) and relies on the REVIEW process's attestation at
  record creation — the same epistemic boundary the frozen target
  record carries for its count. Rejected alternative: a fuzzy text-
  similarity independence check in contract code (an inference surface,
  brittle, and a violation of the deterministic-ownership rule).
* **T4 — Count-vs-clause cross-check.** A published bundle count is
  never compared against the clause's parsed entry count (D17).
  Rejected: requiring agreement (it would manufacture a new
  contradiction state from a cross-field inference the frozen
  contracts never permit, and it would fail the common shape where the
  count is published and the clause lists component items whose count
  the grammar cannot total reliably). Recorded as a candidate for a
  FUTURE reviewed attestation field, not this contract.
* **T5 — Grammar evolution.** Any change to the clause grammar, the
  incompleteness-marker list, or the item-entry grammar changes
  derivation results: it is a NEW authority token (or a NEW evidence
  schema version within a new token), never a silent edit of the FU4
  v1 constants (the extraction schema's own discipline, §1.4,
  mirrored).
* **T6 — The `RECORDED_CHANNEL` basis is a single-clause view.** A
  channel alone cannot detect two published clauses (the channel maps
  only the primary cue, §1.4). The contract therefore pins (D3) that
  an integration with an available extraction result MUST use
  `EXTRACTION_RESULT_V1`; the channel basis exists for corpus-shaped /
  supplied channels where no result is in evidence. Residual: a
  hand-supplied channel basis over a page that actually published two
  clauses is under-evidenced — its state can only be ESTABLISHED /
  PARTIAL / ABSENT, and the derivation cannot know better. Accepted
  (the corpus channels are single-value structured fields by
  construction); recorded.
* **T7 — No target-side `CONTRADICTED_PUBLISHED`.** One reviewed
  attestation is one record; a self-contradictory target source is a
  review-governance failure (the record must not be created), not a
  contract state. Rejected alternative: a target-side contradiction
  vocabulary (it would need two target records per candidate — a
  case-shape change, violating D2's minimality).
* **T8 — Dispatch placement.** The FU4 module owns the SUPERSET
  dispatch (FU2 / FU3 / FU4) and the frozen FU3 dispatch is byte-
  unchanged (it cannot grow — it is frozen). Consumers that need all
  three tokens use the FU4 dispatch; consumers frozen at FU3 keep the
  FU3 entry point. A future top-level merger (one dispatch knowing all
  tokens) is its own separately versioned step; until then, both
  dispatches coexist and agree by delegation (A2).

---

# 12. Implementation acceptance criteria (for the future contract phase)

The implementation phase is approved, and its endpoint is accepted,
ONLY when ALL hold:

1. **Design fidelity.** The module implements this document exactly:
   the token, the evidence schema (§3) including every constructor
   rule, the derivation table (§5) including every fail-closed arm,
   the dispatch (§5.3), and the import self-checks (vocabulary
   bounds: the four composition states; the two bases; the rule set
   EQUAL to the FU3 set; the token distinct from FU2 / FU3; the
   evidence schema version 1; no mutable global state).
2. **Frozen pins.** Every file digest in §8 is byte-identical to the
   phase's starting SHA (the pin test computes the digests from the
   starting-SHA tree — not from the phase's own edits); the full 98-
   node FU3 suite and the full 111-node extraction suite pass
   UNCHANGED; the P1 binding-replay suite passes unchanged; the two
   corpus artifacts' digests re-pin.
3. **Adversarial matrix.** The complete §9 matrix (A1–A7, B1–B8,
   C1–C9, D1–D3, E1, F1–F3) is implemented as NEW test nodes in the
   NEW test file and passes; no existing test is deleted, renamed,
   skipped, xfailed, deselected, ignored, or weakened; the Windows
   subprocess flake allowlist is NOT expanded.
4. **Isolation.** No live module (semantic runtime / execution / runs /
   web / providers) imports the FU4 module (AST + lexical scan); the
   production codec registry is unchanged (V1 + 2.0/FU2 only); an
   FU4-bound payload is refused (A4); `V2_AUTHORITY_QUALIFIED` is
   False in both pinned locations; the research export surface is
   strictly additive.
5. **Determinism.** Equal inputs produce byte-equal evidence records
   and byte-equal decisions (B6); the derivation is pure (no clock, no
   I/O, no network, no LLM — import-self-checked, the P2 pattern).
6. **Validation.** Full suite: collection non-decreasing (A6);
   pass/fail reported with exact counts and the flake class
   separately itemized (the Q3-B5-P2-FU1 reporting discipline);
   `python manage.py check` no issues; `python manage.py
   makemigrations --check --dry-run` "No changes detected."
7. **No registration.** The phase does NOT register the binding,
   re-seal any corpus, extend any harness pin, add any codec adapter,
   or change any replay registry (§7.2 / D13) — each is its own
   separately gated step with its own acceptance criteria (E2 / E3).
8. **No live work.** No model call, no capture, no deployment, no
   migration, no corpus label change, no threshold / policy change.

---

# 13. What this phase does not do (invariance list)

* No code, no tests, no artifacts other than this document (committed
  design-only, append-only, on main).
* No implementation of FU4 (task: "Do not implement FU4 in this
  phase").
* No change to the frozen FU2 / FU3 / S2-C / 2.0 / 2.1 contracts, the
  extraction schema v1, the corpus (1.0.0 / 1.1.0), the DRAFT policy,
  the eight gates, the replay / codec registries, or the live runtime.
* No binding registration, no corpus reseal, no capture, no
  qualification decision, no authority promotion, no pricing wiring,
  no deployment, no migration, no model call.
* No Qwen self-audit (the independent review of this document and the
  underlying source is ChatGPT's, per the task).
* Unrelated worktree artifacts (the untracked session / benchmark
  files, the pre-existing `tmp_collection.txt` modification) are
  preserved; the commit stages only this document.

---

# 14. Sources (complete list cited above)

* `CLAUDE.md` — the operating contract (frozen-phase semantics; test
  preservation; deterministic ownership; unknown-beats-fabricated-
  certainty).
* `docs/PRODUCT_INTELLIGENCE_STATUS.md` — Q3-B5-P2-FU1 (the FU3
  interaction review / proposal of record; the four corrected test
  nodes; the 17-node regression matrix), Q3-B5-P2, Q3-B5-P1, Q3-B4-
  FU2, Q3-B4-FU1, Q3-B4, Q3-B3-FU2 sections.
* `docs/PRODUCT_INTEL_SEMANTIC_V2_Q3B4_AUTHORITY_BOUNDARY_DECISION.md`
  — §4.1 (the invariant), §4.7 (the FU3 derivation specification),
  §5.4–5.6 (change buckets; ordering constraints; invariance list),
  §6.1–6.5 (the amendment pattern; the 2.1 binding decision; the W1
  guard; replay compatibility), §8 (the adversarial matrix
  conventions), §9 (the phase plan).
* `docs/PRODUCT_INTEL_SEMANTIC_V2_PROMPT_2_1_DESIGN_Q3B3_FU2.md` — the
  SU axis, the P1–P6 sales-unit outcome table (the P6 bundle shape),
  the six-way separation, the absolute rule.
* `product_intelligence/research/semantic_v2.py` — lines 410, 430,
  448, 553, 565, 913 (§1.1).
* `product_intelligence/research/semantic_authority_fu3.py` — lines
  159, 179, 445, 494, 523, 549, 600, 724, 753, 816, 958, 1085 (§1.2,
  §1.3).
* `product_intelligence/research/sales_unit_extraction.py` — lines
  147, 150, 227, 236, 309, 404, 544, 793, 1133, 1158, 1260, 1349,
  1406 (§1.4).
* `product_intelligence/semantic/contract_v2_1.py` — lines 102, 111,
  129, 193 ff., 258, 329 (§1.5, §7.4).
* `product_intelligence/research/semantic_decision_v2.py` — lines 168,
  177, 182, 186, 191, 203, 227, 669 ff., 2211 (§1.5, §1.6).
* `product_intelligence/semantic/runtime_v2.py` — line 97 (the second
  `V2_AUTHORITY_QUALIFIED` pin).
* `product_intelligence/research/semantic_decision_codec.py` — lines
  138, 192 (§1.6).
* `product_intelligence/research/semantic_decision_replay.py` — lines
  74 ff., 107 (§1.6).
* `product_intelligence/evaluation/semantic_v2/{corpus,gates,report,
  capture,direct_capture,cli,fixtures}.py` — the binding registries
  and pins (fixtures.py lines 111, 123; corpus.py lines 131, 139;
  report.py lines 128 ff.; capture.py lines 86 ff.) (§1.6).
* `product_intelligence/runs/models.py` — `SemanticDecisionRecord`
  (line 845 ff.) (§10 item 2).
* `evaluation/semantic_v2_qualification/{corpus_2_1.json,manifest_2_
  _1.json}` — the 1.1.0 seal (56 cases; the `V2Q-GPU-SU-BUNDLE-0034`
  channel shape) (§1.1, §1.6).
* `tests/research/test_semantic_authority_v2_fu3.py` (98 nodes; the
  file-digest pin pattern, line 144 ff.), `tests/research/test_sales_
  unit_extraction.py` (111 nodes; the four P2-FU1-corrected nodes and
  the 17-node regression matrix), `tests/evaluation/semantic_v2/
  test_q3b5_p1_binding_replay.py` (the binding / codec refusal pins)
  (§1.6, §8).
