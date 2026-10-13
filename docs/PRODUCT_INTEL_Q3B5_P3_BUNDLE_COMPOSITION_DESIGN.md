# Product Intelligence — Q3-B5-P3: Versioned Bundle Composition Authority Design (S2-A-FU4)

**Mode: DESIGN ONLY — no implementation in this phase.** No code, no test,
no capture, no deployment, no migration, no model call, no authority
promotion. The only artifact of this phase is this document, committed
design-only on the starting SHA below.

**Starting SHA:** `1ec0e34f96af29cbbd8785e4be23e9f109b94412`
(Q3-B5-P2-FU1 endpoint — the packaging-ambiguity and bundle-identity
correction; baseline collection 7268, re-verified this session: HEAD is
`1ec0e34`, full-suite state per the Q3-B5-P2-FU1 STATUS section).

## Revision record (FU4 correction — this document, revised in place)

**Revised at:** `68ac4e4988ea35f805eb524afec6e1cd1b9fa2fe`
(this document as originally committed, design-only, at the Q3-B5-P3
design endpoint).

The independent review of the Q3-B5-P3 candidate identified two
architecture blockers in the bundle-composition design. This revision
corrects both in place. The original design rationale is preserved
wherever it remains valid; every correction is recorded explicitly, at
the corrected location and in the register below. Design-only: no
implementation exists for the pre-revision or the corrected design,
and nothing frozen moves.

**Blocker A — quantity completeness.** The pre-revision D6 / U16 count
rule treated a quantity published on one side and absent on the other
as passable ("equal, or at least one side publishes none — no
inference, D17"): a missing quantity was silently treated as
immaterial, and the derivation could return PROVEN_EQUIVALENT while
one side's published count was never checked. Correction: a bounded,
independently supported **quantity-completeness determination** is now
a recorded axis of every bundle comparison (D6, D17, D20, §3.8, §5
U16–U18, §5.1 cases 1–3, §9 C10). Exactly one side publishes a count
⇒ the axis is `UNDETERMINED` ⇒ UNPROVEN, unless a verified
`QuantityCompletenessAttestationV2FU4` (bounded non-materiality reason,
frozen non-model attestation class, digest-verified) stands on the
missing side. No quantity is inferred from bundle item counts, MPN,
price, model output, or absence. Neither-side-publishes is a
determined, recorded state (`BOTH_UNPUBLISHED`), not a silence.

**Blocker B — composition completeness.** The pre-revision D4 / D5 /
§3.5 treated a non-empty, syntactically closed published clause as
`ESTABLISHED`, and byte-identical text (or equal parsed multisets) as
sufficient for the PROVEN conjunction: syntactic validity was
conflated with commercial completeness, so two pages publishing the
same INCOMPLETE enumeration could derive PROVEN_EQUIVALENT.
Correction: the state vocabulary now distinguishes **syntactically
valid text** (`SYNTACTICALLY_VALID` — what the pre-revision
`ESTABLISHED` denoted, demoted), **partially enumerated contents**
(`PARTIAL`), **independently attested complete composition**
(`ESTABLISHED`, redefined — a syntactically valid clause PLUS a
bounded, independently supported
`CompositionCompletenessAttestationV2FU4`: the subject's own published
explicit completeness statement, or a target-side reviewed composition
attestation), **complete but materially different composition** (a
comparison OUTCOME — two `ESTABLISHED` clauses with a materially
established difference ⇒ CONTRADICTED, U17 — not a state), and
**unknown completeness** (syntactically valid, no attestation). Byte-
identity and multiset equality establish TEXTUAL AGREEMENT only —
never completeness (D4, D5, D6, D16, D19, §3.5, §3.6, §3.7, §4, §5
U15–U21, §5.1 cases 4–7 and 9, §9 C11). If completeness cannot be
independently established on a side, FU4 derives UNPROVEN for that
pair. The pre-revision T2 residual (two identically truncated pages
could derive PROVEN over the truncated statement, byte-identity
being "sufficient") is closed by the attestation requirement (T2 as
corrected).

**Register of corrected locations** (pre-revision → corrected):

| Location | Correction |
| --- | --- |
| Scope box 1 / 3 | Attestation facts admitted as the same recorded, non-model, bounded class (determination text audit-only); completeness-unknown composition and asymmetric unattested quantity added to the UNPROVEN arms |
| D4 | State vocabulary split: `SYNTACTICALLY_VALID` added; `ESTABLISHED` redefined as attested-complete |
| D5 | Closure refusals now bar `SYNTACTICALLY_VALID` and `ESTABLISHED` alike; a completeness marker can never rescue an unclosed clause; incompleteness markers dominate |
| D6 | PROVEN conjunction restructured as three recorded axes (form / composition-with-completeness / quantity); byte-identity + multiset equality demoted to textual agreement |
| D11 | Decision record gains bounded bundle-axis audit fields (quantity-axis state, composition states, attestation digests) |
| D16 | Textual agreement explicitly never establishes completeness |
| D17 | No-silent-immateriality rule + explicit no-inference lists (item counts / MPN / price / model output / absence; closure / identity / repetition / absence for completeness) |
| D19 (new) | Composition-completeness attestation: the exact evidence for `ESTABLISHED` |
| D20 (new) | Quantity-completeness attestation: the exact evidence lifting an asymmetric gap |
| §2 | Safety-direction audit re-stated for the corrected design (FU4 corrected is strictly more restrictive than FU4 pre-revision; no FU3-capped tier exposure is lifted) |
| §3.1 / §3.2 / §3.3 | Derivation signature gains the quantity attestation; evidence records gain the attestation fields; constructor coherence updated |
| §3.4 / §3.5 | Clause extraction tightened (whole-text count-only match; count-prefixed marker form); §3.5 split into textual closure (a) + completeness-marker detection (b, versioned list) |
| §3.6 / §3.7 | Three epistemic tiers; materiality grammar scoped to textual agreement / material difference only; worked examples re-stated with the attestation context |
| §3.8 (new) | The two attestation records + bounded vocabularies + the quantity-axis states |
| §4 | Table re-stated over the corrected states (completeness column added; the pre-revision "completely established" row split into unknown / attested) |
| §5 | U-table restructured (U0–U14 preserved; U15–U21 corrected); attestation preconditions; §5.1 mandated decision matrix (ten cases); §5.2 byte-identity sufficiency corrected (was §5.1); tier / dispatch renumbered (§5.3 / §5.4, was §5.2 / §5.3) |
| §6 | Construction entry points and the schema delivery list updated; the identical-repetition rule corrected (consistency ≠ completeness) |
| §7.3 step 4 | The FU4-bound record carries the attestations' canonical documents |
| §9 | B9 / B10 (attestation constructors), C10 / C11 / C12 (quantity and completeness comparison rows), C1 / C5 corrected, F4 (attestation trust boundary) |
| §11 | T2 / T3 corrected; T9 (marker vocabulary) and T10 (quantity-attestation epistemology) recorded |
| §12 | Acceptance vocabularies updated |

## Revision record 2 (Q3-B5-P4-FU1 — implementation correction, this
document revised in place)

**Revised at:** the Q3-B5-P4-FU1 correction endpoint (this amendment is
the smallest versioned change the independent GitHub source review of
the Q3-B5-P4 implementation requires; nothing in the corrected design
moves — the amendment is to the IMPLEMENTED evidence schema, which the
T5 / T9 discipline versions explicitly for this purpose).

The independent review of the Q3-B5-P4 implementation found two safety
defects in the candidate-side presentation gate (`_verify_candidate_`-
`composition` + the two candidate evidence constructors + the
derivation entry points):

**Blocker 1 — cross-listing composition evidence substitution.** The
gate checked the record's source class and published quantity against
the presented channel, but did not establish that the composition
evidence belongs to the EXACT presented candidate publication: a
record built from listing A's channel / extraction result was accepted
over listing B's channel whenever source class, bundle form, and
quantity agreed (a self-verifying digest is not proof of cross-record
association). Correction — the smallest versioned amendment (the frozen
S2-C-FU1 channel cannot carry the back-reference — it is byte-frozen —
but the FU4 evidence schema is versioned for exactly this): the
**versioned bundle-composition evidence schema moves to v2**
(`BUNDLE_COMPOSITION_EVIDENCE_VERSION_FU4 = 2`; v1 records are
un-constructible — an unknown / superseded schema version is never
silently reinterpreted). The candidate record gains ONE field:
`channel_content_digest` — SHA-256 over the frozen channel's canonical
document (state / kind / quantity / raw_detail / source) of the EXACT
channel content the record was constructed from (RECORDED_CHANNEL
basis: the passed channel; EXTRACTION_RESULT_V1 basis: the frozen P2
mapping `sales_unit_channel_from_extraction(result)` of the verified
result — the verifiable relationship extraction result → mapped
channel → record). The derivation's presentation gate re-verifies the
association at derivation time: (a) the presented channel's canonical
content digest must equal the record's (composition evidence
originating from another listing is refused even when source class,
bundle form, and quantity are identical); (b) a RECORDED_CHANNEL
record must be EXACTLY the construction of the presented channel (the
record is a pure function of that channel — a hand-forged record
claiming a clause / state / attestation the presented publication never
made is refused); (c) an EXTRACTION_RESULT_V1 record's primary clause
must be the determined form of the presented channel's published
`raw_detail` (the continuation attestation text may sit beyond
`raw_detail` — AUDIT-ONLY, never compared). Missing provenance is never
invented or reconstructed: the digest is computed at construction over
the exact input; the gate verifies the recorded association. Full
published provenance and integrity evidence are preserved (source /
quantity / digest checks, the attestation verifications, and the
record's own `evidence_digest` all stand; the new field is inside it).

**Blocker 2 — integer identity comparison.** The gate compared the
record's published `channel_quantity` against the channel's `quantity`
with object identity (`is not`): two separately deserialized (or
otherwise separately constructed) equal quantities greater than 256 are
distinct `int` objects, so a valid same-publication record was refused
and only small-int interning masked the defect. Correction: exact
value equality (`!=`). Audit of the related identity comparisons:
every remaining `is` / `is not` in the module is an enum single-
identity check (correct — enum members are singletons) or a strict
`type(x) is int` bound check; no other integer value uses identity
comparison (the quantity axis already compared by value, `==`).

**Register of corrected locations (design → implemented v2):**

| Location | Correction |
| --- | --- |
| §3 (schema intro) / §6 item 3 | Evidence schema versioned to 2 (`BUNDLE_COMPOSITION_EVIDENCE_VERSION_FU4 = 2`); v1 records un-constructible |
| §3.2 | Candidate record gains `channel_content_digest` (the exact channel-content binding, inside `evidence_digest`); constructor rules: computed by the two validated constructors over the exact input (never a caller-invented value), 64-hex bounded |
| §5 (derivation preconditions) | The presentation gate re-verifies the association at derivation time (a / b / c above); quantity compared by exact value |
| §9 (test matrix) | B11 class added: the mandated adversarial rows (identical source + quantity / different raw_detail; listing-A record over listing-B; separately deserialized quantities > 256; equal quantity / different composition; tampered channel provenance; tampered extraction association; valid same-listing; count-only UNPROVEN; FU3 replay unchanged; the MATCH / HIGH / STRONG ceiling unchanged; constructor-time + derivation-time enforcement) |

The frozen FU2 / FU3 / S2-C / P2-extraction / Prompt 2.0 / 2.1 inputs
are byte-unchanged by the amendment; the FU3 / FU2 dispatch arms
delegate to the frozen derivations exactly as before (the historical
replays are untouched — the binding is an FU4-contract property); the
registration step remains separately gated (the v2 records are not
registered anywhere).

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
   deterministic, and replayable. **Corrected (Blocker A / B):** the
   completeness and quantity non-materiality ATTESTATIONS are composition /
   quantity facts of exactly these two classes — (a) the subject side's own
   published explicit statement, verbatim and recorded (the versioned marker
   detection, §3.5b), or (b) a reviewed / request-description record with a
   bounded non-model class — and their recorded determination text is
   AUDIT-ONLY: never read by the derivation (the bounded basis / reason
   fields drive behavior; §3.8, §9-F4).
2. **No inference from matching MPN alone.** Composition comparison is
   over the published clause text (or the versioned materiality grammar's
   parse of it). A part number occurring inside a clause is an item token
   like any other: it is never matched, normalized against the target
   MPN, or given identity weight. MPN similarity inside compositions is
   out of grammar (an entry containing a full identifier string simply
   parses as item text or fails to parse — never as identity evidence).
3. **No automatic pricing eligibility from missing, partial,
   completeness-unknown, or quantity-undetermined sales-unit evidence.** A
   missing / partial / self-contradicted / completeness-unknown composition
   derives UNPROVEN (never PROVEN_EQUIVALENT), an asymmetric unattested
   quantity derives UNPROVEN (D20), and the
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
| **D4** | Composition publication states (CORRECTED — Blocker B) | The bounded vocabulary is `SYNTACTICALLY_VALID` (a non-empty, closed, verbatim published contents clause with no explicit incompleteness marker — a TEXTUAL property only; the commercial completeness of the enumeration is unknown: this is what the pre-revision design's `ESTABLISHED` denoted, demoted), `ESTABLISHED` (REDEFINED: `SYNTACTICALLY_VALID` PLUS a bounded, independently supported completeness attestation — `CompositionCompletenessAttestationV2FU4`, D19 / §3.8 — establishing that the published clause is the bundle's complete commercial composition), `PARTIAL` (partially enumerated contents: published but explicitly incomplete or not closed — an incompleteness marker, an unclosed paren, a dangling trailing separator), `ABSENT` (no contents clause: bare / count-only bundle, empty marker clause), plus the candidate-side-only relation `CONTRADICTED_PUBLISHED` (two or more published clauses that differ textually — every side recorded with its own textual state, none adopted). A non-empty, syntactically closed clause is NOT automatically a complete commercial composition: syntactic closure is the floor of `SYNTACTICALLY_VALID`, never of `ESTABLISHED`. |
| **D5** | Empty / truncated markers never establish (CORRECTED) | `bundle:` (nothing after), `bundle ()`, `bundle (…` (no closing paren), and a clause ending on a dangling separator / incomplete quantity token are NEVER `SYNTACTICALLY_VALID` or `ESTABLISHED` (they are `ABSENT` or `PARTIAL`), so they can never contribute to PROVEN_EQUIVALENT on either side. A completeness marker can never rescue an unclosed clause: the marker detection (§3.5b) runs only over a textually valid clause, and an incompleteness marker always dominates (a clause containing `etc.` is PARTIAL with no attestation, even with a trailing `complete list`). |
| **D6** | The PROVEN conjunction (CORRECTED — Blockers A / B) | FU4 derives `PROVEN_EQUIVALENT` for a bundle ONLY when ALL hold: (1) FORM axis — matching BUNDLE form on both sides; (2) COMPOSITION axis — composition `ESTABLISHED` on BOTH sides (each side with its OWN verified completeness attestation, D19 — a `SYNTACTICALLY_VALID` clause, however identical, is completeness-unknown and can never prove), and the clauses TEXTUALLY AGREE (byte-identical, OR equal multisets under the versioned full-parse materiality grammar, §3.7 — textual agreement only, never completeness); (3) QUANTITY axis — SATISFIED: both sides publish a count ⇒ the counts are equal (`CONSISTENT`), OR neither side publishes one (`BOTH_UNPUBLISHED` — a determined, recorded state, not a silence), OR a material quantity is published on one side and absent on the other with a verified non-materiality attestation standing on the MISSING side (`ATTESTED_NOT_MATERIAL`, D20); (4) both sides carry bounded non-model provenance; (5) the records are integrity-verified. Missing, partial, or completeness-unknown composition on either side ⇒ UNPROVEN. An asymmetric unattested quantity ⇒ UNPROVEN. A published incompatibility independently established on either axis — a count difference over textually-agreed clauses, or a materially established difference between two `ESTABLISHED` clauses — ⇒ CONTRADICTED. |
| **D7** | CONTRADICTED only on materially established difference | Byte-different `ESTABLISHED` clauses derive `CONTRADICTED` ONLY when the versioned bounded item grammar fully parses BOTH clauses and the (normalized quantity, normalized item) multisets differ. Any parse failure ⇒ UNPROVEN (a textual difference that the deterministic grammar cannot establish as material is never declared a contradiction — the safe direction: UNPROVEN caps the tier, CONTRADICTED additionally marks published incompatibility). |
| **D8** | Candidate self-contradiction fails closed to UNPROVEN | Two published candidate-side clauses that differ (title vs structured field, or two title clauses) ⇒ `CONTRADICTED_PUBLISHED` on the evidence ⇒ the derivation returns UNPROVEN for EVERY target shape (never PROVEN, and never CONTRADICTED — mirroring the P2 contradiction → recorded-absence → UNPROVEN discipline and the 2.1 INTERNAL CONTRADICTION RULE: an internally contradictory dimension is unpinned in both directions, not adopted as a conflict against the target). Every side stays recorded with full provenance in the result / evidence for audit. |
| **D9** | Non-bundle arms unchanged | For `SINGLE_UNIT`, `PACK_QUANTITY`, and `TRAY_OR_FACTORY_PACK` the FU4 unit derivation is BYTE-IDENTICAL in behavior to the frozen FU3 derivation (delegated where possible; proven equivalent by test over the full FU3 shape suite, §9-A2). Only the BUNDLE arm changes, and the changes are exactly D6 / D7 / D8 / D19 / D20. |
| **D10** | No new audit rule | FU4 introduces no new `AuthorityRule` member. The two frozen FU3 restrict-only ceilings cover every FU4 unit state (`UNPROVEN` ⇒ `CEILING_SALES_UNIT_NOT_PROVEN`; `CONTRADICTED` ⇒ `CEILING_SALES_UNIT_CONTRADICTED`). The FU4 rule vocabulary mirrors the FU3 set exactly (import-self-checked, the FU3 pattern over the FU2 set). |
| **D11** | State vocabulary reused; decision record versioned (CORRECTED — audit surface) | The three-state `SalesUnitAuthorityV2` enum (frozen FU3) is REUSED — the states are vocabulary; the semantics live in the derivation under the token. The decision record is a NEW separately versioned `AuthorityDecisionV2FU4` with the FU3 record's field set and the same construction invariants, PLUS bounded bundle-axis audit fields (for BUNDLE channels: the quantity-axis state (`BundleQuantityAxisStateV2FU4`), the candidate / target composition states, the completeness-attestation digests, the quantity-attestation digest; for non-bundle channels: exactly None) — the determinations are RECORDED, never silent (D19 / D20). An FU4 decision is type-distinguishable from a FU3 decision at replay; the FU3 firewall invariants are unchanged. |
| **D12** | Prompt 2.1 needs no new version; a NEW binding is required | The 2.1 prompt TEXT is unchanged (no 2.2): its sales-unit instructions are model-level and assert nothing FU4 contradicts (§7.4). But a record governed by FU4 must carry FU4 on its authority axis — the existing 2.1 binding `("V2","2.1",1,1,FU3)` is NOT reused for changed authority semantics. The FU4 production binding is `("V2","2.1",1,1,"SEMANTIC_AUTHORITY_V2_S2A_FU4")` — a successor 2.1 binding moving ONLY the authority axis. The downstream token alone is necessary but not sufficient: the token identifies the derivation, the binding identifies the RECORD CONTRACT (§7.4 answers task item 7 explicitly). |
| **D13** | Binding registration is separately gated | The contract-only FU4 phase registers NOTHING in the production / qualification registries (codec, replay, corpus, harness pins, report sections stay exactly as §1.6). The registration step (semantic-layer binding constant + harness pins + corpus 1.2.0 binding-only reseal + codec adapter + replay extension + offline no-capture baseline reports) is its own approval-gated phase, specified in §7.3 and executable only after the FU4 contract phase is reviewed and approved. |
| **D14** | Corpus reseal is binding-only | When registered, the FU4 binding seals a NEW corpus version `1.2.0`: 56/56 per-case documents byte-identical to 1.1.0, `label_revisions` empty, exactly `{corpus_version, semantic_contract_binding, corpus_digest}` moved (the P1 1.1.0 re-seal precedent). No label change; the committed 1.0.0 / 1.1.0 artifacts stay byte-frozen under their own bindings. |
| **D15** | No wiring, no promotion, no eligibility | The FU4 module is unreachable from every live path (the P2 AST-pin / FU3 lexical-guard discipline). `V2_AUTHORITY_QUALIFIED` stays False in both pinned locations. No V2 pricing consumer reads FU4 states (none exists; W1's guard predicate is unchanged and orthogonal). |
| **D16** | Textual agreement only; normalization is grammar-internal (CORRECTED — Blocker B) | Clause equality's primary path is byte-identity over the verbatim clause (after the bounded marker strip, §3.4–3.5b); the materiality grammar's normalization (casefold + internal-whitespace collapse of item tokens, integer quantities) applies ONLY inside the secondary full-parse multiset path and the materiality test — never to the primary comparison, never beyond the documented grammar. The equality rule establishes TEXTUAL AGREEMENT between two clauses only. It NEVER establishes that either clause is a complete commercial composition — that is the completeness attestation's function (D19), a separate axis: byte-identical text and parsed multiset equality may establish textual agreement, but not completeness by themselves. |
| **D17** | No cross-field inference; no silent immateriality (CORRECTED — Blocker A) | (a) A published bundle count is never parsed into the composition, and the composition is never parsed into the count: count-vs-entry-count agreement is neither required nor checked (the quantity axis compares PUBLISHED counts side-to-side only). (b) A MISSING QUANTITY IS NEVER SILENTLY IMMATERIAL: exactly one side publishing a material count leaves the quantity axis `UNDETERMINED` ⇒ UNPROVEN, unless a bounded, independently supported non-materiality attestation stands on the missing side (D20) — the pre-revision design's pass-arm "at least one side publishes none — no inference" is REMOVED. (c) No quantity is inferred from a bundle item count (the clause's parsed entries), an MPN, a price, a model output, or an absence. (d) No completeness is inferred from syntactic closure, byte-identity, multiset equality, same-page repetition, a model output, or an absence (D19). The clause, the count, and their attestations are separate recorded facts. |
| **D18** | Frozen target records are composition-ABSENT under FU4 | The FU4 unit derivation also accepts the FROZEN `TargetSalesUnitEvidenceV2` (so one call site can serve both tokens): under the FU4 token a frozen target record is read exactly as its fields state — form + count, composition ABSENT (the field does not exist; no implicit upgrade). This keeps FU4 total over recorded inputs while guaranteeing a FU3-shaped record can never manufacture a composition fact. |
| **D19** | Composition completeness attestation (NEW — Blocker B) | A composition is `ESTABLISHED` ONLY with a recorded `CompositionCompletenessAttestationV2FU4` (§3.8): bound to the exact clause (the clause digest), carrying a BOUNDED basis — the subject side's own published explicit completeness statement (the versioned `_COMPLETENESS_MARKERS` list, detected deterministically from the recorded text, §3.5b), or, TARGET-SIDE ONLY, a recorded review composition attestation (the review process's determination, trusted as recorded, T3) — carrying the subject side's frozen non-model provenance class, the verbatim attestation text (AUDIT-ONLY: never read by the derivation), and a self-verifying digest. No other evidence — syntactic closure, byte-identity, multiset equality, same-page repetition, a model output, an MPN, a price, an absence — establishes completeness. If completeness cannot be independently established on a side, FU4 derives UNPROVEN for that pair. |
| **D20** | Quantity completeness attestation (NEW — Blocker A) | The bundle quantity axis is a DETERMINED, RECORDED state in every comparison (`CONSISTENT` / `BOTH_UNPUBLISHED` / `ATTESTED_NOT_MATERIAL` / `CONTRADICTED` / `UNDETERMINED`, §3.8). A material quantity published on one side and absent on the other is `UNDETERMINED` ⇒ UNPROVEN, UNLESS a recorded `QuantityCompletenessAttestationV2FU4` stands on the MISSING side: bounded subject side, bounded non-materiality reason (the versioned vocabulary), a frozen non-model attestation class (the review process is the contract's sole quantity-attestation authority — a page never self-attests its own silence, T10), the verbatim recorded determination (AUDIT-ONLY), a self-verifying digest. The attestation never supplies a quantity VALUE (a reviewed value enters through the record's quantity field, the frozen mechanism). Neither-side-published is `BOTH_UNPUBLISHED` — determined and recorded, not a silence. |

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
required for any record to be governed by FU4 (§7.4). The correction
recorded in the revision record at the top of this document further
refines (b) in two recorded places: "byte-identical" establishes TEXTUAL
AGREEMENT only — PROVEN additionally requires a completeness
attestation on BOTH sides (D19) and a determined quantity axis (D20);
and the quantity axis itself is a recorded determination in every
comparison, never a silent pass-arm (the pre-revision U16 defect,
Blocker A).

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
inputs, CORRECTED design): FU4 differs from FU3 only where (a) FU3
said PROVEN on a count-only or composition-unestablished bundle shape
(FU4: UNPROVEN — restricts); (b) FU3 said PROVEN or UNPROVEN over two
bundles whose published statements are textually agreed with a count
difference, or materially different with completeness attested on both
sides (FU4: CONTRADICTED — restricts, and the decision-level absolute
rule already owns the model-side shape); or (c) FU3 said UNPROVEN over
two textually-agreed clauses, quantity axis satisfied, with a
completeness attestation on BOTH sides (FU4: PROVEN — the intended
capability, requiring the full corrected D6 conjunction, which no
count-only, partial, completeness-unknown, or quantity-undetermined
shape satisfies). FU4 (corrected) is strictly MORE restrictive than
FU4 (pre-revision) and lifts no tier exposure FU3 capped: every shape
the pre-revision design admitted as PROVEN on an unattested clause or
on an unattested asymmetric quantity is UNPROVEN under the corrected
design (U15 / U18), and CONTRADICTED / UNPROVEN cap identically
(NEEDS_REVIEW) on every shape where FU3 and the corrected FU4 diverge
in informativeness. No shape that the corrected FU4 admits as PROVEN
is a count-only, partial, completeness-unknown, or quantity-
undetermined shape (D5 / D6 / D19 / D20), so the Q3-B5-P2-FU1
bundle-identity invariant ("a published count is not the complete
identity of a bundle") holds at the derivation level under the FU4
token — now on BOTH axes (the count axis per D17 / D20, the
composition axis per D19).

---

# 3. The bounded composition evidence schema (exact proposal)

All names below are the proposed contract surface (module
`research/semantic_authority_fu4.py`, research layer, stdlib-only,
import-self-checked, no mutable global state — the FU3 / P2 discipline).
The schema is **version 2 of the FU4 composition evidence**
(`BUNDLE_COMPOSITION_EVIDENCE_VERSION_FU4 = 2` — version 1 plus the
Q3-B5-P4-FU1 `channel_content_digest` channel-content binding on the
candidate record; see Revision record 2); any future change to a
grammar or state is a new version of this record, never a silent edit.

## 3.1 Placement: derivation inputs, not case fields (D2)

The FU4 unit derivation's inputs are:

```
derive_sales_unit_authority_fu4(
    channel: CandidateSalesUnitEvidenceV2,                      # frozen
    candidate_composition: CandidateBundleCompositionEvidenceV2FU4 | None,  # NEW
    target_evidence: TargetSalesUnitEvidenceV2FU4                # NEW
                    | TargetSalesUnitEvidenceV2 | None,          # frozen (D18)
    quantity_attestation: QuantityCompletenessAttestationV2FU4  # NEW (D20)
                        | None = None,
) -> SalesUnitAuthorityV2
```

* `channel` — the frozen recorded channel, byte-unchanged type.
* `candidate_composition` — the NEW bounded candidate-side record
  (§3.2). `None` is legitimate and means "no composition evidence
  presented" — for a BUNDLE channel that is composition ABSENT
  (UNPROVEN); for a non-BUNDLE channel it is contract misuse (fail
  closed, D9). The record's embedded completeness attestation (§3.8)
  re-verifies with it.
* `target_evidence` — the NEW versioned target record (§3.3), or the
  FROZEN FU3 record (read as composition-ABSENT, D18), or `None`
  (the default single unit — unchanged). The FU4 record's embedded
  completeness attestation (§3.8) re-verifies with it.
* `quantity_attestation` — CORRECTED (Blocker A, D20): the NEW
  bounded, review-constructed non-materiality attestation, presented
  ONLY over an asymmetric quantity axis (exactly one side publishes a
  count) and ONLY with its subject side the actually-missing side;
  digest-verified before any axis uses it. `None` is the normal case;
  both-sides-published and both-unpublished axes are determined
  without it, and presenting it there is contract misuse.

Replay reconstructs the derivation exactly because every input is a
recorded, digest-verified value (§8): the channel is inside the case
(input schema 1, unchanged); the two records (with their embedded
completeness attestations) and the quantity attestation (when
present) are recorded in the FU4-bound record's own evaluation
section (§7.3, the Q3-B4 §6.1 item 5 "derived snapshots … replay re-
derives and proves agreement" precedent).

## 3.2 Candidate-side record

```python
class BundleCompositionStateV2FU4(str, Enum):
    """CORRECTED (Blocker B): the pre-revision member set conflated
    syntactic closure with commercial completeness. The pre-revision
    `ESTABLISHED` (a non-empty, closed, marker-free clause) is
    DEMOTED to `SYNTACTICALLY_VALID`; `ESTABLISHED` is REDEFINED as
    the attested-complete state. `PARTIAL` / `ABSENT` /
    `CONTRADICTED_PUBLISHED` keep their pre-revision meaning (stated
    now over textual validity)."""

    SYNTACTICALLY_VALID = "SYNTACTICALLY_VALID"
    """A non-empty, closed, verbatim published contents clause with no
    explicit incompleteness marker (the textual closure grammar of
    §3.5a). A TEXTUAL property only: the statement is a complete
    published sentence, not necessarily a complete ENUMERATION of what
    the bundle contains — the commercial completeness of the
    composition is UNKNOWN. This state can never by itself contribute
    to PROVEN_EQUIVALENT, on either side (D19; §5 U15). (This is what
    the pre-revision design's `ESTABLISHED` denoted.)"""

    ESTABLISHED = "ESTABLISHED"
    """REDEFINED (Blocker B): SYNTACTICALLY_VALID PLUS a bounded,
    independently supported completeness attestation
    (`CompositionCompletenessAttestationV2FU4`, §3.8) establishing
    that the published clause is the bundle's COMPLETE commercial
    composition — the subject's own published explicit completeness
    statement (the versioned marker, §3.5b) or, target-side only, a
    recorded review composition attestation. Only this state may
    enter the PROVEN conjunction (D6). The attestation is trusted as
    recorded (the T3 / T3' boundary); physical truth remains the
    publisher's claim or the reviewer's determination (the same
    epistemic status as every recorded fact in this system:
    equivalence is AS PUBLISHED, and AS ATTESTED complete)."""

    PARTIAL = "PARTIAL"
    """Partially enumerated contents: the publication is explicitly
    incomplete or not closed: an incompleteness marker inside the
    clause (§3.5a list), an unclosed paren-form, or a dangling
    trailing separator / incomplete quantity token. The clause text is
    recorded for audit; it can never contribute to
    SYNTACTICALLY_VALID, ESTABLISHED, or PROVEN_EQUIVALENT, and a
    completeness marker can never rescue it (D5)."""

    ABSENT = "ABSENT"
    """No contents clause is published: a bare bundle word, a count-only
    bundle phrase ("bundle of N" / "N-unit bundle"), or an empty marker
    clause ("bundle:" / "bundle ()"). The count, when published, stays
    verbatim in the source text and is never bound to a quantity (the
    P2-FU1 rule, preserved)."""

    CONTRADICTED_PUBLISHED = "CONTRADICTED_PUBLISHED"
    """Candidate-side ONLY: two or more published contents clauses
    (across the examined fields, e.g. title vs structured field) that
    differ textually (byte comparison over the §3.4-3.5b clause form).
    EVERY clause is recorded with its full provenance AND its own
    textual state (and its own published attestation, if the marker
    was present); NONE is adopted. The derivation returns UNPROVEN
    for every target shape (D8) — a self-contradiction is not a
    contradiction against the target, and neither side may be
    presented as THE composition."""


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
    completeness_attestation: CompositionCompletenessAttestationV2FU4 | None
    """CORRECTED (Blocker B): the attestation that makes state
    ESTABLISHED. Present EXACTLY when state is ESTABLISHED (subject
    side = CANDIDATE; the basis is necessarily
    PUBLISHED_COMPLETENESS_STATEMENT — a candidate-side record cannot
    carry a review basis, §3.8); None for every other state (a
    SYNTACTICALLY_VALID clause is completeness-unknown — the attested
    and unattested shapes are type-distinguishable, never conflated).
    Embedded in the record's digest."""
    composition_clause: str | None
    """The verbatim published contents clause (§3.4–3.5b: marker-
    stripped, completeness-marker-stripped when attested) — present
    when SYNTACTICALLY_VALID or ESTABLISHED or PARTIAL or
    CONTRADICTED_PUBLISHED (the primary clause); None when ABSENT.
    Original case and spacing (byte comparison is over exactly this
    text)."""
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
    channel_content_digest: str
    """VERSION 2 (Q3-B5-P4-FU1): the binding to the EXACT channel
    content the record was constructed from — SHA-256 over the frozen
    channel's canonical document (state / kind / quantity / raw_detail
    / source). RECORDED_CHANNEL basis: the passed channel; EXTRACTION_RESULT_V1 basis: the frozen P2 mapping of the verified result
    (`sales_unit_channel_from_extraction` — the verifiable
    relationship extraction result → mapped channel → record).
    Computed by the validated constructors over the exact input
    (never a caller-invented value); inside `evidence_digest`; the
    derivation's presentation gate re-verifies it against the
    presented channel (cross-listing substitution refused)."""
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
* state/coherence (CORRECTED): `ABSENT` ⇒ `composition_clause is
  None`, `completeness_attestation is None`, `additional_clauses ==
  ()`; `SYNTACTICALLY_VALID` / `PARTIAL` ⇒ exactly one clause
  (non-empty for SYNTACTICALLY_VALID), `completeness_attestation is
  None`, `additional_clauses == ()`; `ESTABLISHED` ⇒ exactly one
  clause, non-empty, `completeness_attestation` present and coherent
  (subject CANDIDATE; basis PUBLISHED_COMPLETENESS_STATEMENT; source =
  the record's source; `clause_digest` over exactly the record's
  clause; digest verified — §3.8), `additional_clauses == ()`;
  `CONTRADICTED_PUBLISHED` ⇒ `composition_clause` is the primary
  clause and `additional_clauses` is non-empty and every clause
  differs from every other (byte comparison over the §3.4–3.5b clause
  form);
* SYNTACTICALLY_VALID clauses must pass the §3.5a textual closure
  checks (an empty / truncated clause is un-constructible as
  SYNTACTICALLY_VALID or ESTABLISHED — D5 at the type level);
* `EXTRACTION_RESULT_V1` ⇒ both extraction digests present and
  well-formed; `RECORDED_CHANNEL` ⇒ both None;
* `channel_content_digest` (VERSION 2) is a well-formed 64-hex digest,
  computed by the constructor over the exact channel content the record
  is built from (RECORDED_CHANNEL: the passed channel; EXTRACTION:
  the frozen P2 mapping of the verified result) — never a caller-
  invented value; the presentation gate re-verifies it against the
  presented channel (Revision record 2, Blocker 1);
* `channel_quantity` obeys the frozen channel's bundle quantity rules
  (positive int or None; never inferred);
* `evidence_digest` re-verifies at construction and on every presented
  record (a tampered record — including a tampered embedded
  attestation — produces no derivation input —
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
    (the same §3.5 grammar, corrected; the target side has no
    CONTRADICTED_PUBLISHED — one reviewed attestation is one record; a
    self-contradictory source is a review-governance failure, not a
    contract state, §11-T7). Non-BUNDLE forms carry exactly
    (None, None, None): composition is a bundle-only fact."""
    completeness_attestation: CompositionCompletenessAttestationV2FU4 | None
    """CORRECTED (Blocker B): present EXACTLY when composition_state is
    ESTABLISHED (subject side = TARGET; basis PUBLISHED_COMPLETENESS_
    STATEMENT — the target's own source published the statement, the
    review records it — or REVIEWED_COMPOSITION_ATTESTATION — the
    review's determination over the clause); None for
    SYNTACTICALLY_VALID / PARTIAL / ABSENT (a SYNTACTICALLY_VALID
    target clause is completeness-unknown and can never prove, §5
    U15). Embedded in the record's digest."""
    evidence_digest: str
```

Constructor rules: the frozen FU3 rules verbatim (form / source
vocabulary; PACK_QUANTITY requires the positive count; SINGLE_UNIT
forbids it; the provenance classes are the two frozen non-model
members) + `schema_version == 1` + the bundle composition coherence
(BUNDLE ⇒ state ∈ {SYNTACTICALLY_VALID, ESTABLISHED, PARTIAL, ABSENT},
and the clause matches the state exactly as on the candidate side;
ESTABLISHED ⇒ the attestation present and coherent (subject TARGET;
clause_digest over exactly the clause; source in the target classes;
digest verified); SYNTACTICALLY_VALID / PARTIAL ⇒ the attestation
None; non-BUNDLE ⇒ all three composition fields None) + digest self-
verification.

**Provenance semantics (recorded, not re-verified by the derivation):**
the target source label is the bounded class of where the attestation
came from. Independence of the two sides (that the target clause was
not copied from the candidate page) is the REVIEW process's
attestation at record creation — the same epistemic boundary the frozen
target record already carries for its count (a reviewed "pack of 4" is
trusted as reviewed, not re-derived). CORRECTED (Blocker B): the same
boundary now extends to the completeness ATTESTATION itself — that the
target's ESTABLISHED state rests on genuine independent verification
rather than on a copy of the candidate's publication is the review
process's attestation at record creation (T3 / T3': a copied,
unverified attestation is a review-governance failure — the record must
not have been created — not a contract state; the deterministically
detectable slice — basis / source-class coherence, clause_digest
binding — is enforced, §3.8). The derivation records both source
labels AND both attestations in the decision's audit surface; a red
flag (both sides labeled from the same request description, or a
target attestation whose recorded anchor names the candidate source)
is visible to the reviewer, never silently laundered by the derivation
(§11-T3).

## 3.4 The bounded clause extraction (marker strip — CORRECTED)

One versioned function, `extract_published_bundle_clause(text) ->
(clause, was_paren_form)` (stdlib only; the text is always a verbatim
published span — an established cue text or a recorded channel
`raw_detail`):

1. **Count-only bundle phrase** (WHOLE-TEXT match — corrected: the
   pre-revision step did not state the match bound, and a text with
   contents after a count, e.g. `"bundle of 2: 2x RAM + 1x CPU"`,
   falls through to the marker forms, not to ABSENT): the trimmed text
   matches `bundle` / `bundle of N` / `N-unit bundle` / `N unit
   bundle` in FULL (N canonical 1..99999 — case-insensitive on the
   packaging word only, N verbatim-checked): → `clause = None`
   (composition ABSENT; the count is never bound, P2-FU1 / D17).
2. **Marker form** (word `bundle` + optional whitespace + `:` or `(`;
   INCLUDING the count-prefixed variants `bundle of N` + marker and
   `N-unit bundle` + marker, in which the published count N is IGNORED
   by the clause extraction — it stays the channel / target's quantity
   fact, never re-bound into the clause, D17a): strip the marker
   prefix; for the paren form, strip the ENCLOSING closing paren when
   present (the cue span includes it); `clause` = the residue
   (original case / spacing preserved).
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

## 3.5 Closure / completeness classification (D5 / D19 — CORRECTED)

CORRECTED (Blocker B): the pre-revision single step ("ESTABLISHED
otherwise") conflated textual closure with commercial completeness.
It is now two versioned steps over the §3.4 clause:

**Step (a) — textual closure classification**
`classify_clause_closure(clause, was_paren_form) -> ABSENT | PARTIAL |
SYNTACTICALLY_VALID` (empty clause ⇒ ABSENT immediately):

* **PARTIAL** when any holds:
  * the clause contains an explicit incompleteness marker from the
    bounded versioned list `_INCOMPLETE_MARKERS = ("etc.", "etc",
    "…", "...", "and more", "+ more", "and so on", "among others",
    "and other")` — corrected precision: a single-word member matches
    as a complete whitespace-delimited token anywhere in the clause; a
    multi-word member matches as a maximal whitespace-delimited run;
    the ellipsis character (`…`) or the dot-triplet token (`...`)
    matches anywhere;
  * the paren form's enclosure is not closed (the published span ends
    without the closing paren — the clause is truncated at the field
    boundary);
  * the clause ends on a dangling separator (`+`, `,`, `&`, `;`, or
    whitespace after one of them), or on an incomplete quantity token
    (a trailing `N x` / `Nx` with no item following) — positive
    evidence the published statement continues beyond the examined
    text.
* **SYNTACTICALLY_VALID** otherwise (non-empty, closed, no marker).
  Textually a complete published statement; the ENUMERATION's
  completeness is unknown (D4). This is what the pre-revision design
  classified as ESTABLISHED — demoted, not deleted.
* (ABSENT is reached only via the empty clause / count-only path.)

The colon-form clause that runs to the field end (the title simply ends
after the clause) is CLOSED (SYNTACTICALLY_VALID if otherwise clean):
the examined field is the complete published field; there is no
deterministic signal of continuation. The residual risk (a page-level
truncation invisible to the field) is recorded in §11-T2 — corrected:
it can no longer reach PROVEN, because step (b) and D19 require an
attestation the truncation would have to survive.

**Step (b) — completeness-marker detection** (runs ONLY over a
SYNTACTICALLY_VALID clause — an incompleteness marker always dominates:
a clause containing `etc.` is PARTIAL with no attestation, even with a
trailing `complete list`, D5):

A clause C carries a PUBLISHED completeness statement iff C = P + D + M
with: M (casefolded) a member of the versioned list
`_COMPLETENESS_MARKERS = ("complete list", "all items listed",
"everything included", "all included", "full contents", "nothing else
included")`, matched as a maximal whitespace-delimited run; D a bounded
delimiter from the versioned set {whitespace-prefixed `+` / `,` / `&`
/ `;` / "and", whitespace-prefixed em-dash / en-dash, whitespace-
prefixed `(`}; P non-empty. When it does: the marker segment D+M is
STRIPPED (the residual P is the clause — re-checked for non-emptiness;
a marker-only clause is ABSENT), and a
`CompositionCompletenessAttestationV2FU4` is CONSTRUCTED with basis
`PUBLISHED_COMPLETENESS_STATEMENT`, attestation_text = the verbatim
recorded D+M segment, subject side = the evidence's side, source = the
clause's recorded source, clause_digest over P.

For the EXTRACTION_RESULT_V1 basis there is one additional recorded
location: the frozen cue engine's COLON-form span stops at the first
comma / semicolon / closing paren (§1.4), so a title
`"bundle: 2x RAM + 1x CPU, complete list"` records the cue
`"bundle: 2x RAM + 1x CPU"` and leaves the marker segment in the
RECORDED `raw_field_value` immediately after the cue span. Step (b)
therefore also checks, for a colon-form established cue, the recorded
field text following the cue span: it must begin, after any
whitespace, with a bounded delimiter D + a marker member M (no other
text between the span end and D); the verbatim recorded segment is the
attestation_text. The PAREN form needs no such continuation (its span
includes the closure, so the marker sits inside the clause). No other
text location is read; the check is over recorded, span-verified,
digest-bound fields only.

Both marker lists and the delimiter set are VERSIONED contract
constants of the FU4 module (`BUNDLE_COMPOSITION_EVIDENCE_VERSION_FU4`
covers them; any change is a new version — the T5 discipline,
§11-T9).

## 3.6 What "complete" is and is not (CORRECTED — three epistemic
tiers)

CORRECTED (Blocker B): the pre-revision paragraph defined
`ESTABLISHED` as "the page published a closed, non-empty contents
statement, and it does not say the statement is incomplete" — i.e. it
treated syntactic closure + the absence of an incompleteness marker as
completeness. That is insufficient: a closed, marker-free clause may
enumerate only part of the bundle's contents without any syntactic
trace of the omission. The corrected design separates three tiers:

1. **Textual validity** (`SYNTACTICALLY_VALID`) — the page published a
   closed, non-empty contents statement that does not say it is
   incomplete. A property of the TEXT, deterministically classified
   (§3.5a). Necessary for ESTABLISHED, never sufficient.
2. **Attested completeness** (`ESTABLISHED`) — tier 1 PLUS a recorded,
   bounded, independently supported attestation that the clause is the
   bundle's complete commercial composition (D19 / §3.8: the subject's
   own published explicit statement, or a target-side review
   determination). This is the exact evidence the corrected design
   requires; no substitute (closure, byte-identity, multiset equality,
   same-page repetition) is admitted.
3. **Physical truth** — NEVER claimed by this contract. The
   completeness of the enumeration as a matter of physical fact is the
   publisher's claim (tier 2a) or the reviewer's attested
   determination (tier 2b), recorded with provenance, on the same
   epistemic footing as every other recorded fact (the frozen
   `PROVEN_EQUIVALENT` semantics: "the candidate is published as sold
   in the same commercial unit as the target"). Equivalence is
   established AS PUBLISHED and AS ATTESTED — by two independently
   recorded publications agreeing under the bounded grammar, each
   side's completeness independently established — never by a model,
   never by catalog knowledge, never by MPN matching inside the
   clauses.

## 3.7 The versioned materiality grammar (D6 / D7 / D16 — CORRECTED
scope)

CORRECTED (Blocker B): the grammar is used ONLY for the TEXTUAL-
AGREEMENT axis (the secondary multiset path) and the MATERIAL-
DIFFERENCE test (D7) — and explicitly NEVER for completeness (D19) or
quantity (D17 / D20). A versioned constant set of the FU4 module
(import-self-checked immutable):

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

Worked examples (pinned as tests; CORRECTED — the attestation context
is stated, because the grammar alone no longer decides PROVEN):

| Candidate clause | Target clause | Textual axis | FU4 result (quantity axis permitting) |
| --- | --- | --- | --- |
| `2x RAM + 1x CPU` | `2x RAM + 1x CPU` | byte-identical (T-AGREE) | TEXTUAL AGREEMENT only — UNPROVEN without a completeness attestation on both sides (U15); with attestations on both sides + quantity axis satisfied: PROVEN (U19) |
| `2x RAM + 1x CPU` | `1x CPU + 2x RAM` | both full, multisets equal (T-AGREE, secondary path) | as above — PROVEN (U20) when both sides ESTABLISHED |
| `2x RAM + 1x CPU` | `2x RAM + 1x SSD` | both full, multisets differ (T-DIFF-MATERIAL) | CONTRADICTED when BOTH sides ESTABLISHED (U17); UNPROVEN when either side's completeness is unknown (U15 — a material difference without both-side completeness is never a contradiction) |
| `2x RAM + 1x CPU` | `2x DDR5-6400 RAM + 1x CPU` | full/full, items differ (T-DIFF-MATERIAL) | as above |
| `2x RAM + 1x CPU` | `2x RAM + a mystery gizmo` | both fully parseable (multi-word item tokens are in grammar), multisets differ (T-DIFF-MATERIAL) | as above |
| `2x RAM + 1x CPU (revised)` | `2x RAM + 1x CPU` | the parenthesized qualifier is residual on one side — NOT fully parseable (T-DIFF-UNESTABLISHED) | UNPROVEN (never CONTRADICTED on unparseable text — U21 / D7) |
| `GPU + power cables + bracket kit` (0034 shape) | same clause | byte-identical (T-AGREE) | textual agreement; the committed 0034 text carries no completeness marker ⇒ SYNTACTICALLY_VALID ⇒ UNPROVEN without attestations (U15); a corpus-shaped raw_detail WITH a recorded marker (e.g. `"… bracket kit, complete list"`) ⇒ ESTABLISHED via the PUBLISHED basis, then U19 |
| `2x RAM etc.` | `2x RAM` | candidate PARTIAL (incompleteness marker, §3.5a) | UNPROVEN (never PROVEN, and never CONTRADICTED by its own incompleteness — U11 / U14, §9-C1) |
| `2x RAM + 1x CPU, complete list` | `2x RAM + 1x CPU` | marker stripped (§3.5b), then byte-identical (T-AGREE); candidate ESTABLISHED (PUBLISHED basis) | PROVEN (U19) when the target side is also ESTABLISHED; the marker segment is the recorded attestation text, never an item token |

## 3.8 The attestation records (NEW — Blocker A / B)

The bounded vocabulary of evidence that completeness and quantity
non-materiality may rest on. All names below are the proposed contract
surface of the FU4 module; the integrity error type is the corrected-
scope `BundleCompositionEvidenceIntegrityError` (it now covers the
evidence records AND both attestation records).

```python
class EvidenceSideV2FU4(str, Enum):
    CANDIDATE = "CANDIDATE"
    TARGET = "TARGET"


class CompletenessBasisV2FU4(str, Enum):
    PUBLISHED_COMPLETENESS_STATEMENT = "PUBLISHED_COMPLETENESS_STATEMENT"
    """The subject side's OWN recorded publication contains an explicit
    bounded completeness statement tied to the clause: detected
    deterministically from recorded text by §3.5b (the versioned
    _COMPLETENESS_MARKERS list; the verbatim marker segment IS the
    recorded attestation text), or, target-side, recorded by the
    review as the statement the target's own source published.
    Candidate- or target-side (each side's own source)."""

    REVIEWED_COMPOSITION_ATTESTATION = "REVIEWED_COMPOSITION_ATTESTATION"
    """A recorded review determination that the subject's published
    clause is the bundle's complete commercial composition (TARGET-
    SIDE ONLY — the review process is the contract's attestation
    authority for the target side; the attestation text records the
    review's anchor, e.g. the manufacturer-published bundle
    specification the clause was verified against). The derivation
    trusts the record as reviewed (the T3 / T3' epistemic boundary);
    a copied, unverified attestation is a review-governance failure —
    the record must not have been created — not a contract state."""


@dataclass(frozen=True)
class CompositionCompletenessAttestationV2FU4:
    schema_version: int          # = 1
    subject_side: EvidenceSideV2FU4
    basis: CompletenessBasisV2FU4
    source: <the subject side's frozen non-model class>
    """CANDIDATE subject ⇒ exactly LISTING_TITLE /
    PUBLISHED_STRUCTURED_FIELD (the frozen channel vocabulary
    members); TARGET subject ⇒ exactly REVIEWED_TARGET_CONTEXT /
    REQUEST_DESCRIPTION (the frozen target vocabulary). A
    basis/source-class mismatch is un-constructible; a candidate-side
    record with basis REVIEWED_COMPOSITION_ATTESTATION is
    un-constructible (a review attests the target side, not the
    candidate listing's own completeness)."""
    clause_digest: str
    """SHA-256 of the attested clause (the §3.4–3.5b clause form,
    original case / spacing) — binds the attestation to the EXACT
    clause; an attestation presented for a different clause is an
    integrity error."""
    attestation_text: str
    """The verbatim recorded statement / determination (non-empty;
    AUDIT-ONLY — never read by the derivation, §9-F4)."""
    attestation_digest: str
    """SHA-256 over the canonical record minus this field."""


class QuantityNonMaterialityReasonV2FU4(str, Enum):
    SUBJECT_SOURCE_STRUCTURALLY_WITHOUT_BUNDLE_COUNTS = \
        "SUBJECT_SOURCE_STRUCTURALLY_WITHOUT_BUNDLE_COUNTS"
    """The subject side's source structurally publishes no bundle
    quantities for this offer shape; the published composition clause
    is the source's complete statement of the commercial unit, so the
    missing quantity is not a material difference between the two
    publications (the review's recorded determination, e.g. the
    requested part's listing family never publishes bundle counts)."""
    PUBLISHED_COUNT_NOT_UNIT_MULTIPLICITY = \
        "PUBLISHED_COUNT_NOT_UNIT_MULTIPLICITY"
    """The OTHER side's published count does not denote the commercial
    unit's multiplicity (the review's recorded determination, e.g. a
    promotional multi-set count), so the subject side's silence on it
    is not a material unit difference."""


@dataclass(frozen=True)
class QuantityCompletenessAttestationV2FU4:
    schema_version: int          # = 1
    subject_side: EvidenceSideV2FU4
    """The side where the quantity is MISSING — the derivation enforces
    the match: an attestation whose subject is not the actually-missing
    side is an integrity error (no derivation); an attestation over a
    non-asymmetric axis (both publish / both absent) is contract
    misuse (ValueError)."""
    reason: QuantityNonMaterialityReasonV2FU4
    source: TargetSalesUnitEvidenceSourceV2
    """Exactly the two frozen non-model attestation classes
    (REVIEWED_TARGET_CONTEXT / REQUEST_DESCRIPTION) — the review
    process is the contract's SOLE quantity-attestation authority for
    EITHER subject side (a page never self-attests the non-materiality
    of its own silence; the candidate-side gap is attested by the
    review record with subject_side = CANDIDATE, T10)."""
    attestation_text: str
    """The verbatim recorded determination (non-empty; AUDIT-ONLY)."""
    attestation_digest: str
    """SHA-256 over the canonical record minus this field."""


class BundleQuantityAxisStateV2FU4(str, Enum):
    """The DETERMINED quantity-axis outcome of a bundle comparison
    (recorded on the decision's audit surface in EVERY case — D20: the
    determination is never silent)."""
    CONSISTENT = "CONSISTENT"
    """Both sides publish a count; the counts are equal. SATISFIED."""
    BOTH_UNPUBLISHED = "BOTH_UNPUBLISHED"
    """Neither side publishes a count. SATISFIED — a determined,
    recorded state (no published quantity exists on either side for
    the other side's silence to mask), NOT a silence."""
    ATTESTED_NOT_MATERIAL = "ATTESTED_NOT_MATERIAL"
    """Exactly one side publishes; a verified
    QuantityCompletenessAttestationV2FU4 stands on the missing side.
    SATISFIED (D20)."""
    CONTRADICTED = "CONTRADICTED"
    """Both sides publish; the counts differ. The quantity axis
    independently establishes published incompatibility (unit
    CONTRADICTED — §5 U16)."""
    UNDETERMINED = "UNDETERMINED"
    """Exactly one side publishes; no verified attestation stands on
    the missing side. Blocks PROVEN (unit UNPROVEN — §5 U18) unless
    another axis independently establishes a contradiction (U17)."""
```

**Constructor rules (fail closed, both records):** vocabulary bounds
(the members above, exact); `schema_version == 1`; `source` in the
subject side's frozen non-model class (basis/source coherence for the
completeness record); `attestation_text` non-empty; digests 64-hex and
self-verified at construction and on every presentation (a tampered
attestation produces no derivation input —
`BundleCompositionEvidenceIntegrityError`); the completeness
attestation is usable ONLY over a `SYNTACTICALLY_VALID` clause (a
PARTIAL / ABSENT clause cannot be attested — §3.5b runs only over
textual validity, and the record constructors enforce state/coherence).

**Review-constructed, not derived:** neither attestation is ever
produced by the derivation or by a fuzzy / similarity computation. The
completeness attestation is machine-constructed ONLY from the recorded
marker detection (§3.5b — deterministic, bounded, over recorded text)
or review-constructed (target side); the quantity attestation is
review-constructed ONLY (there is no machine path: non-materiality is
a determination, not a text pattern).

---

# 4. The six-way distinction (task item 3 — CORRECTED: Blocker B's
five-way classification over the published shapes, plus the quantity
axis row)

Every published bundle shape, deterministically classified by the
extraction layer (unchanged) + the FU4 evidence record (corrected —
the completeness column distinguishes what the pre-revision design
conflated):

| Observed shape (published text) | Extraction result (v1, FROZEN behavior) | Mapped channel (FROZEN behavior) | FU4 composition state (CORRECTED) | FU4 completeness (CORRECTED) | Derivation consequence |
| --- | --- | --- | --- | --- | --- |
| **Bundle form observed, no contents, no count** — `"bundle"` (bare) | `AMBIGUOUS_CUE` / `BUNDLE_WITHOUT_CONTENTS` | `UNAVAILABLE` | — (no record; channel absent) | — | UNPROVEN, every target |
| **Bundle quantity observed, no contents** — `"bundle of 3"`, `"3-unit bundle"` | Extraction-derived: `AMBIGUOUS_CUE` / `BUNDLE_WITHOUT_CONTENTS` (count verbatim, never bound). Corpus-shaped: the frozen channel ADMIITS an OBSERVED BUNDLE with `quantity=3` and count-only `raw_detail` (e.g. `"bundle of 3"`) — a hand- or corpus-supplied channel the extractor never produces | Extraction-derived ⇒ `UNAVAILABLE`. Corpus-shaped ⇒ `OBSERVED` / BUNDLE / qty 3 / raw_detail = the count-only phrase | ABSENT (basis `RECORDED_CHANNEL`, §3.4 step 1) for the corpus-shaped channel; no record (channel absent) for the extraction-derived one | — (no clause to attest) | UNPROVEN vs every target, INCLUDING a target bundle of the same count (U10 — a published count is not the complete identity of a bundle) |
| **Bundle contents partially described** — `"bundle: 2x RAM etc."`, `"bundle (2x RAM + 1x CPU"` (unclosed), `"bundle: 2x RAM + "` (dangling) | `OBSERVED_UNAMBIGUOUS` (established BUNDLE cue; the span is the published clause) | `OBSERVED` / BUNDLE / qty None / raw_detail = the published phrase | PARTIAL (partially enumerated contents; the clause recorded for audit) | — (a PARTIAL clause can never be attested — §3.5b runs only over textually valid clauses; an `etc.` clause is PARTIAL even with a trailing `complete list`, D5) | UNPROVEN vs every target — partial never proves (U11 / U14) and never contradicts by its own incompleteness |
| **Bundle contents closed, no completeness statement** — `"bundle: 2x RAM + 1x CPU"` | `OBSERVED_UNAMBIGUOUS` | `OBSERVED` / BUNDLE / qty None / raw_detail = the published phrase | SYNTACTICALLY_VALID (the verbatim clause, provenance, digest-bound) | UNKNOWN — no attestation (**CORRECTED**: the pre-revision design classified this row `ESTABLISHED` from syntactic closure alone — Blocker B) | UNPROVEN vs every target — a textually valid clause is not a complete composition (U15), even against a byte-identical, quantity-satisfied target clause |
| **Bundle contents closed + published completeness statement** — `"bundle: 2x RAM + 1x CPU, complete list"`, `"bundle (2x RAM + 1x CPU) (all items listed)"` | `OBSERVED_UNAMBIGUOUS` (the established cue's recorded span / field text carries the marker segment, §3.5b) | `OBSERVED` / BUNDLE / qty None / raw_detail = the published phrase | SYNTACTICALLY_VALID clause (marker stripped, §3.5b) | ATTESTED — `PUBLISHED_COMPLETENESS_STATEMENT` (the verbatim marker segment recorded) ⇒ state ESTABLISHED | The corrected D6 conjunction applies (PROVEN only against a target side that is ALSO ESTABLISHED and textually equal with the quantity axis satisfied — U19 / U20; CONTRADICTED per U16 / U17; UNPROVEN otherwise) |
| **Bundle contents closed + reviewed completeness attestation (target side)** — the requested part's source clause `"2x RAM + 1x CPU"`, the review's recorded verification against the manufacturer-published bundle specification | — (the target side has no extraction layer — the review supplies the record) | — | SYNTACTICALLY_VALID clause | ATTESTED — `REVIEWED_COMPOSITION_ATTESTATION` (the determination + anchor recorded) ⇒ state ESTABLISHED | The target side of the corrected D6 conjunction (the independence boundary: T3 / T3'; case 9) |
| **Contents absent or ambiguous (empty markers)** — `"bundle:"`, `"bundle ()"`, `"bundle: "` | `OBSERVED_UNAMBIGUOUS` (the cue engine's established marker shape; the clause residue is empty) | `OBSERVED` / BUNDLE / qty None / raw_detail = the empty-marker phrase | ABSENT (empty clause, §3.5a) | — | UNPROVEN vs every target — an empty marker never establishes syntactic validity, completeness, or PROVEN (U10) |
| **Contradictory published contents** — title `"bundle: 2x RAM + 1x CPU"` + structured `"Bundle (2x SSD + cable)"` | `OBSERVED_UNAMBIGUOUS` (kind + quantity consistent; the contents relation is NOT the extractor's scope, §1.4) | `OBSERVED` (primary clause only — the channel cannot express the second) | CONTRADICTED_PUBLISHED (both clauses recorded with provenance AND their own textual states; each with its own published attestation if the marker was present; basis `EXTRACTION_RESULT_V1`) | per-clause (recorded, none adopted) | UNPROVEN vs every target (U12 / D8 — fail closed; a self-contradiction is unpinned in both directions, not adopted as a conflict against the target) |
| **Asymmetric published quantity (CORRECTED row — Blocker A)** — the candidate channel quantity 2 with clause `"2x RAM + 1x CPU"` (corpus-shaped `raw_detail` `"bundle of 2: 2x RAM + 1x CPU"`), the target the same clause with quantity None (or the reverse roles) | per shape (the extraction-derived candidate always carries quantity None — the P2-FU1 rule — so the asymmetric shape over an extraction-derived candidate is the review-supplied target quantity) | per shape | per shape (each side's own) | per shape | UNPROVEN (U18 — the quantity axis is UNDETERMINED: the missing quantity is NOT silently immaterial) unless a verified `QuantityCompletenessAttestationV2FU4` stands on the missing side (⇒ the axis is ATTESTED_NOT_MATERIAL, and the pair derives per the composition / textual axes — U19 when both sides are ESTABLISHED and agreed); both-sides-published differing counts ⇒ CONTRADICTED (U16) |

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
target_evidence, quantity_attestation)` — pure, deterministic, zero-
live, replayable; `TypeError` / `ValueError` on foreign or contract-
misuse inputs; the unit returned is the frozen `SalesUnitAuthorityV2`
(D11).

**Preconditions (fail closed):**

* `channel` is the frozen type; `channel.state == UNAVAILABLE` ⇒
  return `UNPROVEN` for every target — identical to FU3, and a
  `candidate_composition` presented over an UNAVAILABLE channel is
  contract misuse (ValueError: the recorded absence admits no
  composition evidence).
* `candidate_composition` (when present) re-verifies its
  `evidence_digest` — including its embedded completeness attestation
  (§3.8: digest, subject CANDIDATE, basis PUBLISHED_COMPLETENESS_
  STATEMENT, source = the record's source, clause_digest over exactly
  the record's clause) — and, on the extraction basis, its binding to
  the presented channel (the record's `source` and `channel_quantity`
  must agree with the channel's `source` and `quantity` — a record
  cannot claim provenance the channel never recorded; integrity error
  otherwise).
* `target_evidence` is None, or the frozen type (D18), or the FU4 type
  (digest re-verified — including its embedded completeness
  attestation, subject TARGET); a frozen record is read as
  composition-ABSENT.
* CORRECTED (Blocker A): `quantity_attestation` (when present) is
  digest-verified before any axis uses it; it is admissible ONLY over
  an asymmetric quantity axis (exactly one side publishes a count) and
  ONLY with `subject_side` = the actually-missing side — a subject
  mismatch is an integrity error (no derivation); presentation over a
  both-published or both-unpublished axis is contract misuse
  (ValueError).

**The decision table (CORRECTED — the bundle rows U15–U21 are
restructured over the three recorded axes: form, composition-with-
completeness, quantity; U0–U14 preserve their pre-revision meaning)**
(target form = the explicit target evidence's form, or the default
SINGLE_UNIT):

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
| U15 | `OBSERVED BUNDLE` | BUNDLE; both sides textually valid (SYNTACTICALLY_VALID or ESTABLISHED); at least one side's completeness UNKNOWN (no verified attestation); no independently established axis contradiction (i.e., not U16 / U17) | **UNPROVEN** | Blocker B (NEW) — byte-identity / multiset equality establishes TEXTUAL AGREEMENT, not completeness (D19); a material difference without both-side completeness is never a contradiction (D7's safe direction) |
| U16 | `OBSERVED BUNDLE` | BUNDLE; both sides textually valid; clauses TEXTUALLY AGREE (byte-identical or multiset-equal); quantity axis CONTRADICTED (both sides publish, counts differ) | **CONTRADICTED** | D20 — a count difference over the same stated composition is a published incompatibility that completeness does not gate (was pre-revision U15, broadened: no longer requires both sides ESTABLISHED) |
| U17 | `OBSERVED BUNDLE` | BUNDLE; both ESTABLISHED; clauses byte-different, both fully parse, multisets differ (T-DIFF-MATERIAL) — quantity axis state recorded (an UNDETERMINED gap is logged, does not shield the contradiction) | **CONTRADICTED** | D7 — complete but materially different composition (was pre-revision U18, completeness redefined) |
| U18 | `OBSERVED BUNDLE` | BUNDLE; both ESTABLISHED; quantity axis UNDETERMINED (one side publishes, none attested); clauses not independently materially different (T-AGREE or T-DIFF-UNESTABLISHED) | **UNPROVEN** | Blocker A (NEW) — a missing quantity is NOT silently immaterial (D20); the pre-revision U16 pass-arm "at least one side publishes none — no inference" is REMOVED |
| U19 | `OBSERVED BUNDLE` | BUNDLE; both ESTABLISHED (each with its own verified attestation); quantity axis SATISFIED (CONSISTENT / BOTH_UNPUBLISHED / ATTESTED_NOT_MATERIAL); clauses byte-identical | **PROVEN_EQUIVALENT** | D6 — the corrected intended capability: textually agreed compositions, each side independently attested complete, quantity axis determined (was pre-revision U16, now completeness- and quantity-gated) |
| U20 | `OBSERVED BUNDLE` | BUNDLE; same as U19, clauses byte-different, both fully parse, multisets equal | **PROVEN_EQUIVALENT** | D6 secondary path (T1 preserved, now over attested-complete compositions) (was pre-revision U17) |
| U21 | `OBSERVED BUNDLE` | BUNDLE; same as U19, clauses byte-different, at least one side NOT fully parseable | **UNPROVEN** | D7 — the difference is textual but not materially established; no semantic / fuzzy comparison exists in this contract (was pre-revision U19) |

**The axis structure (CORRECTED).** The table reads in order — form
(U9), candidate composition (U10–U12), target composition (U13–U14),
then the two comparison axes over the two textually-valid clauses:
the QUANTITY axis (`BundleQuantityAxisStateV2FU4`, §3.8) and the
TEXTUAL-AGREEMENT axis (T-AGREE / T-DIFF-MATERIAL / T-DIFF-
UNESTABLISHED, §3.7). The combination rule: the unit is **
CONTRADICTED** iff the form axis mismatches (U9), or the quantity axis
is CONTRADICTED over textually-agreed clauses (U16), or the
composition axis is T-DIFF-MATERIAL with both sides ESTABLISHED (U17);
the unit is **PROVEN_EQUIVALENT** iff all axes are satisfied (U19 /
U20); every other combination is **UNPROVEN** (U0 / U10–U15 / U18 /
U21). Every axis determination is recorded on the decision's audit
surface (D11) — the comparison is total over recorded inputs, and no
axis is ever silent.

**Never an input, never inferred (FU3 list, preserved + CORRECTED
extension):** model confidence, model matched / conflicting / missing-
critical attributes (a model claim of "bundle contents matched" OR of
"the composition is complete" is not independent verification — only
the §3.8 attestation records are), product-title similarity beyond the
recorded verbatim clause, price, availability, or any other commercial
fact; no quantity is inferred from a bundle item count (the clause's
parsed entries), a missing value, an MPN, a price, a model output, or
an absence (D17c); no composition is inferred from a count, a channel
absence, an MPN, or a model output; no completeness is inferred from
syntactic closure, byte-identity, multiset equality, same-page
repetition, or an absence (D17d / D19); the attestation's recorded
text is never an input (the bounded fields drive behavior; §9-F4).

**The task's six mandated rows, mapped (CORRECTED row numbers):**
"Missing or partial composition → UNPROVEN" = U10 / U11 / U13 / U14,
plus completeness-unknown composition = U15 (Blocker B: "missing"
now includes "closed but unattested"); "Different verified
compositions → CONTRADICTED only when the difference is materially
established" = U17 (yes — both sides ESTABLISHED) / U21 (no —
UNPROVEN) / U15 (no — a material difference without both-side
completeness is UNPROVEN, the safe direction); "Equal counts without
composition → UNPROVEN" = U10; "Equal complete compositions with
sufficient provenance → potentially PROVEN_EQUIVALENT" = U19 / U20
("potentially" is the corrected D6 conjunction: attested completeness
+ textual agreement + the determined quantity axis — §5.2); "
Conflicting title and structured fields → fail closed" = §4 row 8 /
U12 (and, at the channel level, the frozen P2 rule: kind or quantity
conflict across the fields ⇒ `CONTRADICTED_CUES` ⇒ recorded absence ⇒
UNPROVEN, unchanged); "Empty `bundle:` / `bundle ()` / truncated
content must never establish complete composition" = §4 row 7 / U10 /
U11 (D5 at the type level: such clauses are un-constructible as
SYNTACTICALLY_VALID, let alone ESTABLISHED).

## 5.1 The mandated revision decision matrix (ten cases — NEW)

The ten mandated cases, each with the exact input shape and the exact
corrected derivation (the axes of §5: the form axis, the composition
axis, the textual-agreement axis T, the quantity axis Q). "Clause C"
abbreviates a closed, marker-free contents clause; "attested (side)"
means the side carries a verified completeness attestation (§3.8)
over its clause; the quantity-axis states per §3.8.

1. **Equal bundle text, both quantities absent.** The candidate
   publishes C (quantity None); the target publishes C (quantity
   None). Q = BOTH_UNPUBLISHED — a determined, recorded state, not a
   silence. Neither side attested (both SYNTACTICALLY_VALID):
   **UNPROVEN** (U15 — textual agreement without completeness is not
   equivalence). Both sides attested (both ESTABLISHED):
   **PROVEN_EQUIVALENT** (U19 — case 4's shape). Never CONTRADICTED
   (no published difference on any axis).
2. **Equal bundle text, quantity present on one side only.** The
   candidate publishes C with quantity 2; the target publishes C with
   quantity None (the reverse roles are symmetric). Q = UNDETERMINED.
   Both sides attested: **UNPROVEN** (U18 — the Blocker A row: the
   pre-revision design derived PROVEN here on "at least one side
   publishes none"; that arm is removed). With a verified
   `QuantityCompletenessAttestationV2FU4` on the missing side (subject
   = the missing side, a bounded reason, a frozen non-model source):
   Q = ATTESTED_NOT_MATERIAL ⇒ **PROVEN_EQUIVALENT** (U19). An
   attestation with the wrong subject side ⇒
   `BundleCompositionEvidenceIntegrityError` (no derivation);
   an attestation over a non-asymmetric axis ⇒ ValueError (contract
   misuse). Without attested completeness on both sides: **UNPROVEN**
   (U15 — the completeness gap stands; the quantity gap is recorded).
3. **Equal bundle text, different published quantities.** The
   candidate publishes C with quantity 2; the target publishes C with
   quantity 3. Q = CONTRADICTED + T = T-AGREE ⇒ **CONTRADICTED**
   (U16) — regardless of the completeness attestation state (a count
   difference over the same stated composition is a published
   incompatibility that completeness does not gate); the completeness
   states are recorded on the audit surface.
4. **Equal bundle text, complete independent attestations.** Both
   sides ESTABLISHED via independent attestations — the candidate's
   own published statement (the PUBLISHED basis, detected from the
   recorded text) and the target's reviewed attestation (the REVIEWED
   basis; the independence boundary is case 9 / T3') — T = T-AGREE
   (byte-identical, or multiset-equal under the grammar), Q satisfied
   (any of CONSISTENT / BOTH_UNPUBLISHED / ATTESTED_NOT_MATERIAL) ⇒
   **PROVEN_EQUIVALENT** (U19 / U20) — the intended capability of the
   corrected design.
5. **Equal but incomplete published descriptions.** Either clause is
   PARTIAL (incompleteness marker / unclosed paren / dangling
   separator): **UNPROVEN** (U11 / U14) — a partial description never
   proves and never contradicts by its own incompleteness, even
   against an ESTABLISHED, differently-attested other side. A clause
   that is syntactically valid but incomplete in fact (the page
   omitted items without saying so — no marker, no unclosed form):
   SYNTACTICALLY_VALID, completeness UNKNOWN ⇒ **UNPROVEN** (U15) —
   the Blocker B point: the incompleteness is invisible to the
   syntax; only a recorded attestation can establish completeness;
   without it, UNPROVEN.
6. **Different descriptions with independently complete
   compositions.** Both sides ESTABLISHED (independent attestations);
   the clauses byte-differ; both fully parse; the multisets differ
   (T = T-DIFF-MATERIAL) ⇒ **CONTRADICTED** (U17 — the "complete but
   materially different composition" outcome; the Q state is
   recorded, and Q = UNDETERMINED does not shield it). The same but
   one side not fully parseable ⇒ **UNPROVEN** (U21 — the difference
   is not materially established, D7's safe direction). The same but
   at least one side's completeness unknown ⇒ **UNPROVEN** (U15 — a
   material difference requires completeness on BOTH sides; one-sided
   completeness never contradicts).
7. **Equal parsed multisets with incomplete source evidence.** Both
   clauses fully parse and the multisets are equal (T = T-AGREE via
   the secondary path; byte-different) but at least one side lacks a
   verified completeness attestation (SYNTACTICALLY_VALID), or its
   attestation is integrity-failed or bound to a different clause ⇒
   **UNPROVEN** (U15) — multiset equality establishes textual
   agreement, never completeness (D16 corrected). With both sides
   attested this is case 4 (U20 — PROVEN).
8. **Contradictory candidate publications.** The title's clause C1 ≠
   the structured clause C2 ⇒ the evidence is CONTRADICTED_PUBLISHED
   (both clauses recorded with their own textual states and their own
   published attestations, if any) ⇒ **UNPROVEN for every target
   shape** (U12 / D8) — including a target whose clause equals C1 or
   C2 and is itself ESTABLISHED: a self-contradiction is unpinned in
   both directions (the 2.1 INTERNAL CONTRADICTION RULE, preserved).
9. **Candidate source copied into target evidence without
   independent verification.** The target FU4 record's clause is
   byte-identical to the candidate's clause and the target carries a
   REVIEWED_COMPOSITION_ATTESTATION. The derivation cannot detect the
   copy (T3 / T3' — text independence is not a deterministic contract
   fact; the same boundary the frozen target record carries for its
   count). The contract's pins: (a) the attestation's subject-side /
   basis / source-class coherence (a target-side review attestation
   over the target's own clause — constructible, trusted as
   recorded); (b) the audit surface records both attestations (basis,
   source, text, digest) — the reviewer's inspection surface; (c) a
   copied, unverified attestation is a review-governance failure:
   the record must not have been created (T3'); (d) the detectable
   launderings are unconstructible / integrity-refused (B9 / B10):
   a candidate-side completeness claim with a REVIEWED basis, a
   target-side attestation with a candidate source class, an
   attestation over a different clause (the clause_digest mismatch).
   Behavior over the constructible shape: the pair derives per the
   axes (PROVEN reachable when the attestations stand as recorded) —
   the contract adds no fuzzy independence check (the rejected
   alternative, preserved from T3).
10. **Historical FU3 bundle behavior preserved under its original
    binding.** The corpus-shaped channel OBSERVED BUNDLE quantity 3
    raw_detail "bundle of 3" (count-only) vs. the frozen target
    record BUNDLE quantity 3: under the FU3 arm of the dispatch (the
    record's binding `("V2","2.1",1,1,FU3)`) ⇒ **PROVEN_
    EQUIVALENT** — the frozen count-based behavior, byte-unchanged
    (the A7 coexistence pin, preserved). Under the FU4 arm (the same
    recorded input, the FU4 token) ⇒ candidate composition ABSENT ⇒
    **UNPROVEN** (U10) — the corrected design's restriction (the
    safety-direction audit's delta (a)). The same recorded input,
    coexisting results under coexisting tokens — per-binding replay,
    documented, never drift.

## 5.2 Is byte-identity sufficient? (task item 5) — no, and here is
why (CORRECTED)

Byte-identical published clauses are **necessary but not sufficient**
for PROVEN_EQUIVALENT. Identical text can still be:

1. **Incomplete** — `"bundle: 2x RAM etc."` on both sides is
   byte-identical and PARTIAL (incompleteness marker): the pages
   published the same INCOMPLETE statement; equivalence is unproven
   (U11 / U14). D5 refuses the SYNTACTICALLY_VALID classification at
   the type level, so the derivation cannot reach U19 on such text at
   all.
2. **Truncated** — `"bundle (2x RAM + 1x C"` on both sides (identical
   field-level truncation): byte-identical, PARTIAL (unclosed paren),
   UNPROVEN. The invisible colon-form variant (a title cut at max
   length mid-clause, no marker) is SYNTACTICALLY_VALID — textually
   identical, completeness UNKNOWN — and CORRECTED: it can no longer
   derive PROVEN without a completeness attestation on both sides;
   the residual is recorded in §11-T2 (corrected), bounded by the
   attestation the truncation would have to survive.
3. **Not a complete composition** — the principal CORRECTED case
   (Blocker B): a closed, marker-free clause may enumerate only part
   of the bundle's contents without any syntactic trace of the
   omission. Two pages publishing the same partial enumeration are
   byte-identical and both SYNTACTICALLY_VALID — the derivation
   returns UNPROVEN (U15), because byte-identity establishes textual
   agreement, never completeness. Only the recorded attestation
   (§3.8) establishes ESTABLISHED.
4. **A quantity gap** — CORRECTED (Blocker A): byte-identical clauses
   with a count published on one side only do NOT derive PROVEN; the
   quantity axis is UNDETERMINED ⇒ UNPROVEN (U18) unless the missing
   side carries a verified non-materiality attestation (D20).
5. **Under-insufficient provenance** — U19 / U20 additionally require
   the bounded non-model source on both sides (the record
   constructors refuse any other value) AND the attestation
   coherence (D19 / §3.8) AND the D18 rule (a frozen target record
   can only ever be ABSENT — identity of text with a count-only
   target record is impossible because the record carries no clause).

Conversely, byte-identity is **not required**: U20 admits an equal,
fully parsed multiset (order / formatting differences) under the
versioned grammar — a strictly bounded relaxation of TEXTUAL
AGREEMENT, with the grammar's residuals failing closed to UNPROVEN
(U21).

**Sufficient evidence, stated (CORRECTED):** candidate side — the
clause is a verbatim span of a published field with the frozen source
label (`LISTING_TITLE` / `PUBLISHED_STRUCTURED_FIELD`), digest-bound
to the verified extraction result (basis a) or to the recorded
channel (basis b), PLUS the candidate's own completeness
attestation (a published statement detected from recorded text,
§3.5b); target side — the clause is verbatim published text supplied
under one of the two frozen attestation classes
(`REVIEWED_TARGET_CONTEXT` / `REQUEST_DESCRIPTION`), PLUS the
target's completeness attestation (the review's determination, or the
target source's published statement); and the quantity axis is
DETERMINED (D20). That conjunction is what U19 / U20 call
"sufficient"; it is provenance of PUBLICATION + recorded ATTESTATION
of COMPLETENESS + a determined QUANTITY AXIS — not provenance of
PHYSICAL TRUTH (§3.6), and it is the strongest the deterministic
contract can express.

## 5.3 Tier derivation (unchanged machinery, corrected inputs)

`derive_authority_tier_fu4(assessment_v2, sales_unit_channel,
evaluation, context_provenances, product_evidence, human_review, *,
target_unit_evidence, candidate_composition, quantity_attestation=None)`
= the frozen S2-A-FU2 derivation (called, never re-implemented) + the
FU3 `IdentityResolutionBoundV2` (delegated — byte-identical) + the FU4
unit derivation (above) + the SAME two restrict-only ceilings on the
automatic tier (`UNPROVEN` ⇒ `CEILING_SALES_UNIT_NOT_PROVEN`;
`CONTRADICTED` ⇒ `CEILING_SALES_UNIT_CONTRADICTED`; `PROVEN_
EQUIVALENT` ⇒ the automatic tier stands). Result: a NEW
`AuthorityDecisionV2FU4` (D11 corrected) with the FU3 record's field
set PLUS the bounded bundle-axis audit fields (the quantity-axis
state, the composition states, the attestation digests — None for
non-bundle channels) and the same construction invariants (AI_
ASSISTED with an UNPROVEN / CONTRADICTED unit is un-constructible; each
ceiling rule only with its unit state on `NEEDS_REVIEW`; `frozen_
fired_rules` projection onto the frozen vocabulary). Human overlay
precedence (HARD_CONFLICT > HUMAN_CONFIRMED > AI) unchanged: a human
may confirm a firewall-capped bundle candidate — the explicit,
auditable path is preserved.

## 5.4 Per-binding dispatch (the FU4 superset)

`derive_authority_tier_for_contract_fu4(token, …)`:

* `SEMANTIC_AUTHORITY_V2_S2A_FU2` ⇒ the frozen `derive_authority_tier`
  (delegated; sales-unit inputs are contract misuse — the frozen rule,
  preserved);
* `SEMANTIC_AUTHORITY_V2_S2A_FU3` ⇒ the frozen `derive_authority_tier_
  fu3` (delegated byte-identically; composition / attestation inputs
  are contract misuse under FU3 — the FU3 contract has no composition
  axis, and
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
3. **The evidence schema** (§3, CORRECTED): `BundleCompositionState
   V2FU4` (five members: SYNTACTICALLY_VALID / ESTABLISHED / PARTIAL /
   ABSENT / CONTRADICTED_PUBLISHED), `EvidenceSideV2FU4`,
   `CompletenessBasisV2FU4`, `CompositionCompletenessAttestationV2FU4`,
   `QuantityNonMaterialityReasonV2FU4`,
   `QuantityCompletenessAttestationV2FU4`, `BundleQuantityAxisStateV2
   FU4`, `CandidateCompositionEvidenceBasisV2FU4`,
   `CandidateBundleCompositionEvidenceV2FU4`,
   `TargetSalesUnitEvidenceV2FU4`, the clause extraction (§3.4), the
   textual closure classification + completeness-marker detection
   (§3.5a / §3.5b), the versioned `_COMPLETENESS_MARKERS` list + the
   bounded marker-delimiter set, the materiality grammar (§3.7), and
   the integrity error type (`BundleCompositionEvidenceIntegrityError`,
   corrected scope: the evidence records AND both attestation
   records). `BUNDLE_COMPOSITION_EVIDENCE_VERSION_FU4 = 2` (the Q3-
   B5-P4-FU1 amendment: version 1 + the candidate record's
   `channel_content_digest` binding, §3.2 / Revision record 2) covers
   the marker lists (the T5 / T9 discipline).
4. **The construction entry points** (fail closed, CORRECTED):
   `candidate_composition_from_extraction(result) ->
   CandidateBundleCompositionEvidenceV2FU4 | None` — re-verifies the
   presented result FIRST (`verify_integrity`), returns None for every
   non-OBSERVED_UNAMBIGUOUS state and for a non-BUNDLE established kind,
   and for an OBSERVED BUNDLE result reads the result's FULL established
   BUNDLE cue list (primary = the channel mapping's primary cue rule:
   structured first, else first title span order): each established
   cue's clause extracted (§3.4) and closure-classified (§3.5a), the
   completeness marker detected over each textually valid clause
   (§3.5b, incl. the recorded field-text continuation for colon-form
   cues) ⇒ the PUBLISHED_COMPLETENESS_STATEMENT attestation when
   present; one textually differing clause pair ⇒
   CONTRADICTED_PUBLISHED (every clause recorded with its own textual
   state and its own published attestation, if any); identical repeated
   clauses (byte-identical after marker strip) ⇒ one clause —
   CORRECTED: the pre-revision design read consistent repetition as
   ESTABLISHED support ("the count-rule precedent"); repetition is
   textual agreement with itself, NOT completeness (Blocker B) — the
   repeated clause is SYNTACTICALLY_VALID unless a published marker
   attests it (the recorded cues are the audit trail).
   `candidate_composition_from_channel(channel) ->
   CandidateBundleCompositionEvidenceV2FU4` — the `RECORDED_CHANNEL`
   basis, §3.4 steps 1–3 + §3.5a / §3.5b over the channel's
   `raw_detail` (OBSERVED BUNDLE only; anything else is contract
   misuse; a corpus-shaped raw_detail carrying a recorded marker, e.g.
   `"… bracket kit, complete list"`, attests via the PUBLISHED basis —
   pinned in §9-B1). VERSION 2 (Revision record 2): BOTH constructors
   bind the record's `channel_content_digest` to the exact channel
   content the record is constructed from (the passed channel / the
   frozen P2 mapping of the verified result), and the derivation's
   presentation gate re-verifies the association at derivation time
   (a digest match over the presented channel's canonical content, the
   exact-construction requirement over the RECORDED_CHANNEL basis, the
   primary-clause requirement over the EXTRACTION_RESULT_V1 basis;
   the published quantity compared by exact value, never object
   identity).
   The TARGET-side record (and its embedded completeness attestation)
   and the QUANTITY attestation are REVIEW-CONSTRUCTED only — the
   validated dataclass constructors are the sole creation paths (there
   is no machine derivation of either: §3.8 "Review-constructed, not
   derived").
5. **The unit derivation** `derive_sales_unit_authority_fu4(channel,
   candidate_composition, target_evidence, quantity_attestation)` (§5)
   and the case-level `derive_sales_unit_authority_fu4_case(case_v2,
   candidate_composition, target_evidence, quantity_attestation=None)`
   (the frozen case-type entry point, mirroring `derive_sales_unit_
   authority`).
6. **The tier derivation** `derive_authority_tier_fu4` (the quantity
   attestation parameter included) + the decision record
   `AuthorityDecisionV2FU4` (the FU3 field set + the bounded bundle-
   axis audit fields, D11 corrected) + the mirrored rule vocabulary
   `AuthorityRuleV2FU4` (import-self-checked EQUAL to the FU3 set —
   D10).
7. **The dispatch** `derive_authority_tier_for_contract_fu4` (§5.4) and
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
   (`AuthorityDecisionV2FU4`, audit fields included), the two evidence
   records' canonical documents (digests included — the embedded
   completeness attestations WITHIN their records' digests), the
   quantity-completeness attestation's canonical document (when
   present), and the bound + unit + tier + fired-
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
  §5.4), or (ii) force the FU3 dispatch to accept composition inputs
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
clause, completeness attestation + its bounded fields and digest, the
quantity attestation's bounded fields and digest where presented,
provenance), (iii) FU4 unit state + the recorded axis determinations
(quantity-axis state, D11), (iv) FU3 unit state
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

* **B1.** The five-way distinction + the marker rows (§4) over
  published text: bare `"bundle"`; `"bundle of 3"` / `"3-unit bundle"`;
  `"bundle: 2x RAM etc."`; `"bundle (2x RAM + 1x CPU"`; `"bundle:
  2x RAM + 1x CPU"` / `"bundle (2x RAM + 1x CPU)"` (closed, no marker
  ⇒ SYNTACTICALLY_VALID, NO attestation — the corrected demotion);
  `"bundle: 2x RAM + 1x CPU, complete list"` (colon form; the marker
  segment sits in the recorded field text after the cue span ⇒ clause
  `"2x RAM + 1x CPU"` + the PUBLISHED_COMPLETENESS_STATEMENT
  attestation, verbatim segment recorded ⇒ ESTABLISHED); `"bundle (2x
  RAM + 1x CPU, all items listed)"` (paren form; the marker inside the
  clause ⇒ stripped ⇒ ESTABLISHED); `"bundle: 2x RAM etc., complete
  list"` (incompleteness DOMINATES ⇒ PARTIAL, NO attestation, D5);
  title `"bundle: 2x RAM + 1x CPU"` + structured `"Bundle (2x SSD +
  cable)"` (⇒ CONTRADICTED_PUBLISHED, both clauses with their own
  textual states) — each yields exactly the recorded extraction state
  (frozen) AND exactly the recorded FU4 evidence state (ABSENT /
  PARTIAL / SYNTACTICALLY_VALID / ESTABLISHED /
  CONTRADICTED_PUBLISHED) with the attestation (or its absence) exact,
  the clause text verbatim, and the provenance (field + source + span
  / basis + digest) intact.
* **B2.** Empty markers never establish: `"bundle:"` (title-final),
  `"bundle ()"`, `"bundle: "`, `"bundle ("` (unclosed, title-final) —
  all ABSENT or PARTIAL; the SYNTACTICALLY_VALID and ESTABLISHED
  constructors REFUSE such a clause (un-constructible, D5 at the type
  level).
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
* **B8.** Clause-grammar edges (pinned verbatim; the attestation
  context stated — the grammar decides the TEXTUAL axis only):
  `"2x RAM + 1x CPU"` vs `"1x CPU + 2x RAM"` (multiset-equal ⇒ T-AGREE:
  U20 when both sides ESTABLISHED, U15 when either side unattested);
  vs `"2x RAM + 1x SSD"` (multiset-differ ⇒ T-DIFF-MATERIAL: U17 when
  both sides ESTABLISHED, U15 when either side unattested); vs `"2x
  RAM + 1x CPU (revised)"` (residual ⇒ T-DIFF-UNESTABLISHED: U21 when
  both ESTABLISHED, U15 otherwise); `"GPU + power cables + bracket
  kit"` (the 0034 shape, fully parseable — and NO completeness marker
  in the committed corpus text ⇒ SYNTACTICALLY_VALID ⇒ U15 without an
  attestation); a quantity edge (`"04x RAM"` non-canonical ⇒ not fully
  parseable ⇒ T-DIFF-UNESTABLISHED); a trailing `"2x"` (dangling
  incomplete token ⇒ PARTIAL, never SYNTACTICALLY_VALID, let alone
  ESTABLISHED).
* **B9.** The composition-completeness attestation (constructor-level,
  NEW — Blocker B): a marker detected from recorded text is the only
  candidate-side basis (a candidate-side record with a
  REVIEWED_COMPOSITION_ATTESTATION basis is un-constructible); the
  subject-side / source-class coherence (CANDIDATE subject ⇒
  LISTING_TITLE / PUBLISHED_STRUCTURED_FIELD; TARGET subject ⇒ the
  frozen target classes); the clause_digest binding (an attestation
  over a different clause is un-constructible / an integrity error at
  presentation); a PUBLISHED-basis attestation_text is exactly the
  verbatim marker segment; a tampered attestation (text edited, digest
  not recomputed) is refused; an attestation over a PARTIAL / ABSENT
  clause is un-constructible (detection runs only over textual
  validity); a target-side record with state ESTABLISHED and no
  coherent attestation (or state SYNTACTICALLY_VALID with one) is
  un-constructible (state/coherence, §3.3).
* **B10.** The quantity-completeness attestation (constructor-level,
  NEW — Blocker A): the vocabulary bounds (the two reasons; the frozen
  non-model source classes); the subject-side / source coherence;
  `attestation_text` non-empty; a tampered attestation refused (digest
  self-verification + re-verification at presentation —
  `BundleCompositionEvidenceIntegrityError`, no derivation input);
  at the derivation: an attestation with `subject_side` ≠ the actually-
  missing side ⇒ integrity error; an attestation over a non-asymmetric
  axis (both publish / both absent) ⇒ ValueError (contract misuse);
  the attestation never supplies a quantity VALUE (there is no value
  field — a reviewed value enters through the record's quantity field,
  the frozen mechanism).

**C — The comparison rules (task item 4, one row per mandated rule)**

* **C1.** Missing, partial, or completeness-unknown composition ⇒
  UNPROVEN: every pair in {candidate ABSENT × target any; candidate
  PARTIAL × target any; candidate SYNTACTICALLY_VALID (no attestation)
  × target any ESTABLISHED / SYNTACTICALLY_VALID; target ABSENT ×
  candidate any (frozen record — the "contents known on only one
  side" regression, now preserved under FU4); target PARTIAL ×
  candidate any; target SYNTACTICALLY_VALID × candidate ESTABLISHED}
  over EVERY target shape (default single unit, explicit bundle ±
  count) — a completeness-unknown clause never proves (U15) and never
  contradicts (a material difference requires both-side ESTABLISHED —
  U17's gate).
* **C2.** Equal counts without composition ⇒ UNPROVEN: corpus-shaped
  channel BUNDLE quantity 3 (raw_detail `"bundle of 3"`) vs target
  BUNDLE quantity 3 (frozen record) — FU4 UNPROVEN while the SAME
  inputs derive FU3 PROVEN_EQUIVALENT (the coexistence pin, A7's
  shape); and vs target BUNDLE no count — both tokens UNPROVEN.
* **C3.** Materially established difference ⇒ CONTRADICTED: U17 over
  MATCH + HIGH + STRONG + clean ⇒ tier NEEDS_REVIEW with
  `CEILING_SALES_UNIT_CONTRADICTED` fired; the Q3-B4 §4.1 invariant: NEVER
  `AI_ASSISTED_COMPARABLE`; the hand-constructed `AuthorityDecisionV2
  FU4` with that tier + unit is un-constructible (the constructor
  invariant). The same text with one side UNATTESTED (SYNTACTICALLY_
  VALID) ⇒ U15 UNPROVEN (the safe direction — a material difference
  without both-side completeness is never a contradiction).
* **C4.** Unestablished difference ⇒ UNPROVEN (U21 / U15, B8 residual
  rows) — never CONTRADICTED; the tier cap is
  `CEILING_SALES_UNIT_NOT_PROVEN`.
* **C5.** Equal complete compositions with sufficient provenance ⇒
  PROVEN_EQUIVALENT (U19 / U20, CORRECTED): BOTH sides ESTABLISHED via
  independent attestations (candidate: the PUBLISHED marker detected
  from the recorded text; target: the REVIEWED attestation), clauses
  byte-identical (U19) or multiset-equal (U20), quantity axis
  satisfied (BOTH_UNPUBLISHED / CONSISTENT / ATTESTED_NOT_MATERIAL): the
  tier STANDS under MATCH + HIGH + STRONG (no ceiling fired) — the
  positive row proving the corrected design can represent
  attested-composition equivalence the frozen channel cannot (the Q3-
  B5-P2-FU1 regression 8 shape, now lifted off UNPROVEN by the
  attestations, still gated by qualification); the same row with the
  count rule violated (both publish, counts differ) ⇒ CONTRADICTED
  (U16); the same row with ONE side unattested ⇒ UNPROVEN (U15 — the
  Blocker B negative twin of the positive row).
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
  embedded part number (e.g. `"1x SSD M.2 9A0…"` vs `"1x SSD M.2
  9B0…"`) ⇒ multiset-differ ⇒ CONTRADICTED when both sides ESTABLISHED
  (U17 — the items differ, no identity weight given); the same with
  one side unattested ⇒ UNPROVEN (U15); clauses where the identifier
  makes the entry unparseable ⇒ U21 / U15 UNPROVEN; in NO row is the
  target MPN or the candidate MPN an input to the comparison (signature-
  pinned).
* **C9.** Model-output non-inference: a scripted evaluation whose
  `matched_attributes` claims BUNDLE / PACKAGING_QUANTITY agreement OR
  "the compositions are complete" changes NOTHING under the FU4
  dispatch (the unit derivation's inputs are signature-pinned:
  channel + evidence records + the quantity attestation's bounded
  fields only); the `AuthorityRule` trail never gains a model-sourced
  rule.
* **C10.** The quantity-completeness axis (NEW — Blocker A, one row per
  axis state over textually-agreed, both-ESTABLISHED clauses): Q =
  CONSISTENT (both publish, equal) ⇒ PROVEN (U19); Q =
  BOTH_UNPUBLISHED (neither publishes) ⇒ PROVEN (U19 — the determined,
  recorded state, not a silence); Q = CONTRADICTED (both publish,
  differ) ⇒ CONTRADICTED (U16) — even when one side's completeness is
  unknown (the count difference over the same stated composition is not
  gated by completeness); Q = UNDETERMINED (asymmetric, no attestation)
  ⇒ UNPROVEN (U18 — the Blocker A defect row: byte-identical clauses,
  both sides attested complete, candidate quantity 2, target quantity
  None; pinned as the shape the pre-revision design derived PROVEN
  over); Q = ATTESTED_NOT_MATERIAL (asymmetric + a verified attestation
  on the missing side) ⇒ PROVEN (U19); the no-inference pins (D17c):
  a clause's parsed entry count is never compared against the published
  count (the 3-entry clause with published quantity 3 derives purely
  from the published values; the derivation never receives the parsed
  multiset for quantity purposes — signature-pinned); no quantity is
  derived from absence / MPN / price / model output (the FU3 list,
  preserved + extended).
* **C11.** The completeness axis (NEW — Blocker B rows): byte-identical
  clauses, NO attestation on either side, both quantities absent ⇒
  UNPROVEN (U15 — decision-matrix case 1); byte-identical + one side
  attested ⇒ UNPROVEN (U15 — case 7's shape over byte-identity);
  multiset-equal (byte-different) + incomplete source evidence (one
  side unattested) ⇒ UNPROVEN (U15 — case 7); both attested + material
  difference ⇒ CONTRADICTED (U17 — case 6); one attested + material
  difference ⇒ UNPROVEN (U15 — the safe direction); the same-page
  repeated clause (title + structured, byte-identical, no marker) ⇒
  SYNTACTICALLY_VALID, NO attestation (the §6 identical-repetition
  correction — consistency is textual agreement with itself) ⇒
  UNPROVEN against a byte-identical target clause (repetition ≠
  completeness).
* **C12.** The copied attestation (NEW — decision-matrix case 9): the
  constructible shape (a target review attestation over a clause byte-
  identical to the candidate's) derives per the axes as recorded — the
  contract performs no copy detection (T3' pinned: the derivation's
  inputs are signature-pinned; no similarity / provenance-of-text
  computation exists in the module — import-scanned); the detectable
  launderings are unconstructible / integrity-refused (B9 / B10 rows:
  a candidate-side REVIEWED-basis record, a target-side attestation
  with a candidate source class, a clause_digest mismatch, a
  subject-side mismatch); the decision's audit surface records both
  attestations (basis + source + text + digest — the reviewer's
  inspection surface, pinned).

**D — Tier, overlay, and the Q3-B4 §4.1 invariant**

* **D1.** The exact Q3-B4 §4.1 composition (MATCH + HIGH + STRONG + clean +
  U1 exact-identifier) over: silent multi-bundle (no cue) ⇒ UNPROVEN
  ⇒ NEEDS_REVIEW (`CEILING_SALES_UNIT_NOT_PROVEN`); count-only pair
  (C2) ⇒ UNPROVEN ⇒ NEEDS_REVIEW; equal unattested text (C11 case 1
  row) ⇒ UNPROVEN ⇒ NEEDS_REVIEW (Blocker B — the pre-revision design
  derived PROVEN here); asymmetric unattested quantity over attested
  equal text (C10 Q = UNDETERMINED row) ⇒ UNPROVEN ⇒ NEEDS_REVIEW
  (Blocker A); material difference over two attested compositions (C3)
  ⇒ CONTRADICTED ⇒ NEEDS_REVIEW (`CEILING_SALES_UNIT_CONTRADICTED`);
  attested equal, quantity axis satisfied (C5) ⇒ PROVEN ⇒
  `AI_ASSISTED_COMPARABLE` STAYS (the firewall's own design: a proven
  unit leaves the automatic tier standing — pricing eligibility still
  requires the separately gated W1 guard + qualification;
  `V2_AUTHORITY_QUALIFIED` False).
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
  parseable ⇒ U21 / U15 UNPROVEN, never CONTRADICTED from a half-
  understood clause.
* **F3.** Multi-offer independence (frozen): two observations with
  different bundle clauses extract independently (distinct input
  digests); no cross-contamination into any evidence record.
* **F4.** The attestation trust boundary (NEW — Blocker A / B): the
  derivation reads EXACTLY the attestation's bounded fields (basis /
  reason, source, subject_side, clause_digest, attestation_digest) —
  `attestation_text` is NEVER read (the recorded determination is the
  reviewer's audit anchor, not a derivation input; a derivation that
  parsed it would be a new inference surface — import-scanned); a
  presented attestation is digest-verified before any axis uses it (a
  tamper ⇒ `BundleCompositionEvidenceIntegrityError`, no unit
  derived); an attestation is never adopted for the wrong side / wrong
  axis (B10 pins); no attestation is ever CONSTRUCTED by the
  derivation itself (the completeness attestation only from the
  §3.5b recorded marker detection or the review; the quantity
  attestation only from the review — §3.8 "Review-constructed, not
  derived").

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
   derivation (§5.4); the FU4 dispatch delegates FU2 / FU3 to the
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

* **T1 — The secondary equality path (U20).** Byte-identity (U19) is
  the primary, trust-minimal path; the full-parse multiset path
  (U20) admits order / formatting differences. Tradeoff: it widens the
  PROVEN population by exactly the shapes where a deterministic grammar
  proves the published item multisets equal; every grammar gap fails
  to UNPROVEN (U21, or U15 where a side is unattested), never to
  CONTRADICTED. Rejected alternative: byte-identity ONLY (simpler
  contract; genuinely equal published compositions differing in item
  order would stay UNPROVEN indefinitely). Rejection path: if approval
  prefers the narrower contract, U20 is deleted (one table row + B8's
  equal-multiset rows) without touching any other decision — the
  grammar constants stay versioned for the materiality test.
* **T2 — Field-end closure for colon-form clauses (CORRECTED).** A
  colon-form clause running to the end of the examined field is
  treated as textually closed (SYNTACTICALLY_VALID if otherwise clean
  — the §3.5a rule preserved). The pre-revision residual (an invisible
  page-level truncation: the title cut at max length mid-clause,
  undetectable from the field; two identically truncated pages could
  then derive PROVEN over the truncated statement, byte-identity being
  "sufficient") is CLOSED by Blocker B: PROVEN now requires a
  completeness attestation on BOTH sides, and an attestation over an
  identically truncated clause would be a double governance failure —
  a cut in the middle of the item list leaves no marker for the
  PUBLISHED basis and no honest anchor for the REVIEWED basis, so the
  clause stays SYNTACTICALLY_VALID ⇒ UNPROVEN. The residual recorded
  here, corrected, is the narrow case where the truncation falls
  AFTER a published completeness marker survives in the text (e.g.
  the title cut at max length after "…, complete list") — the marker
  is the page's own statement, trusted as recorded (the T3 boundary),
  and the review's attestation must survive the same scrutiny on the
  target side. Rejected alternative (unchanged): require a positive
  terminator (comma / semicolon / paren) — its cost is now LOWER, not
  higher: a terminator-less clause is merely UNPROVEN-eligible, never
  PROVEN-eligible, so the field-end rule exists only to keep the
  common real-title shape (`"…SSD bundle: 2x RAM + 1x CPU"`) out of
  PARTIAL and attestation-eligible. The dangling-separator /
  incomplete-token rule (§3.5a) is the deterministic slice of the
  risk that IS detectable, and is enforced.
* **T3 — Target provenance independence (CORRECTED — extended to the
  attestations).** The derivation cannot verify that the target clause
  was not copied from the candidate page — and, corrected, it cannot
  verify that the target's completeness ATTESTATION was not created by
  copying the candidate's publication rather than by independent
  verification (a copied attestation: the review reads the candidate
  listing and records its clause, and its "verified" completeness, as
  the target composition). Both are text-independence questions, not
  deterministic contract facts. The contract records both source
  labels AND both attestations (basis + source + text + digest) in the
  decision's audit surface (visible to the reviewer) and relies on the
  REVIEW process's attestation at record creation — the same
  epistemic boundary the frozen target record carries for its count.
  A copied, unverified attestation is a review-governance failure:
  the record must not have been created (T3') — not a contract state,
  and no contract rule may be tuned to "detect" it. The
  deterministically detectable slice is enforced at construction /
  presentation (B9 / B10): basis / source-class coherence,
  clause_digest binding, subject-side match — laundering across the
  side / basis boundary is un-constructible. Rejected alternative
  (unchanged): a fuzzy text-similarity independence check in contract
  code (an inference surface, brittle, and a violation of the
  deterministic-ownership rule).
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
  clauses is under-evidenced — its state can only be
  SYNTACTICALLY_VALID / ESTABLISHED / PARTIAL / ABSENT, and the
  derivation cannot know better. Accepted
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
* **T9 — The completeness-marker vocabulary (NEW — Blocker B).**
  `_COMPLETENESS_MARKERS` (six members) and the bounded marker-
  delimiter set (§3.5b) are VERSIONED contract constants: any
  addition / removal / rewording changes which recorded texts attest
  completeness — a derivation-result change — so it is a new evidence-
  schema version or a new token (the T5 discipline, applied to the
  new lists). Recorded concern: the list is English-shaped and
  conservative; pages phrasing completeness differently ("as listed",
  "full bundle contents", localized phrasings) leave the clause
  SYNTACTICALLY_VALID ⇒ UNPROVEN — the safe direction (an unlisted
  phrasing is an unattested clause, never a false attestation). A
  future version may grow the list only with recorded examples and
  re-pinned tests (B1's marker rows).
* **T10 — The quantity non-materiality attestation's epistemology
  (NEW — Blocker A).** The review process is the contract's SOLE
  quantity-attestation authority (the frozen non-model classes; §3.8).
  A page does not self-attest the non-materiality of its own silence —
  a published statement about one's own omission is a publisher claim
  about its own gap, not independent support — so the candidate-side
  gap is attested by the review record with `subject_side =
  CANDIDATE`, and the target-side gap by the review record with
  `subject_side = TARGET`. The attestation is trusted as recorded (the
  T3 boundary); the two bounded reasons are the only behavior-driving
  content, the recorded determination text is the audit anchor (F4).
  Recorded concern: a mistaken attestation (the missing count WAS
  material) produces a PROVEN over a real unit difference — the same
  exposure class as a mistaken reviewed target count (the frozen
  record's existing boundary, now extended to the gap-determination);
  the failure is the record's, not the derivation's. No cheaper
  deterministic substitute exists: the count-vs-entry-count check is
  forbidden (D17a / T4), and absence is never evidence.

---

# 12. Implementation acceptance criteria (for the future contract phase)

The implementation phase is approved, and its endpoint is accepted,
ONLY when ALL hold:

1. **Design fidelity.** The module implements this document exactly:
   the token, the evidence schema (§3) including every constructor
   rule, the derivation table (§5) including every fail-closed arm,
   the dispatch (§5.4), and the import self-checks (vocabulary
   bounds CORRECTED: the five composition states; the two evidence
   sides; the two completeness bases; the two quantity non-materiality
   reasons; the five quantity-axis states; the candidate-basis pair;
   the versioned `_COMPLETENESS_MARKERS` list (six members) + the
   marker-delimiter set; the rule set EQUAL to the FU3 set; the token
   distinct from FU2 / FU3; the evidence schema version 2 (the Q3-B5-
   P4-FU1 amendment: version 1 + the candidate record's
   `channel_content_digest` binding — Revision record 2); no mutable
   global state).
2. **Frozen pins.** Every file digest in §8 is byte-identical to the
   phase's starting SHA (the pin test computes the digests from the
   starting-SHA tree — not from the phase's own edits); the full 98-
   node FU3 suite and the full 111-node extraction suite pass
   UNCHANGED; the P1 binding-replay suite passes unchanged; the two
   corpus artifacts' digests re-pin.
3. **Adversarial matrix.** The complete §9 matrix (A1–A7, B1–B10,
   C1–C12, D1–D3, E1–E3, F1–F4) is implemented as NEW test nodes in
   the NEW test file and passes; no existing test is deleted, renamed,
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
