# FU4 Bundle Authority Qualification - Label Challenge Log (C2)

**Corpus family:** `PI-FU4-BUNDLE-AUTHORITY-QUALIFICATION` v1.0.0 (draft
endpoint). **Record of:** the label-governance workflow of design
sections 4.6 / 8.2 over the declared population of record in
`product_intelligence/evaluation/bundle_authority/fixtures.py`
(94 cases - the corrected v1.0.0 DRAFT population: the C2
endpoint's 96 DRAFT cases minus FA4-ADV-034 (the E1-only
obligation) and FA4-PROV-002 (the C3 / 1.1.0 obligation), with
the seven released cases corrected in place under the recorded
adjudication - section 6 rows 12-19).

## 1. The independent-review gate status (record of record)

**The corpus is NOT independently reviewed. The independent reviewer
and the independent tester are NOT staffed at this endpoint.** The
author of record completed the authoring pass below (section 3) and
delivers this log + the precise reviewer handoff
(`reviewer_handoff.md`). No reviewer identity, timestamp, signature, or
approval is recorded anywhere in this family: the author has not
impersonated an independent reviewer (design section 8.1), and the
family loader mechanically refuses the DRAFT state, so no sealed
corpus exists. Per the C2 directive, this is the honest
authoring-evidence + handoff delivery - NOT a claim of C2 completion
and NOT a claim that any case is independently qualified.

The mechanical seal gate is closed and demonstrated by the C2
governance suite (`tests/evaluation/bundle_authority/
test_q3c_c2_label_governance.py`): a forged `REVIEWED` flip with any
reviewer identity, a missing review, a missing matrix row, a stale
digest, or a modified expected label cannot pass the qualification-
ready gate silently. Recorded caveat of record (task discipline): a
matching digest authenticates the BYTES of the record, not the
humanity or independence of its authorship - the digest is the seal,
handoff's job, and the gate never claims to verify it.

**Correction record of record (the Q3-C-C1-FU3 + C2 corrective
implementation; this is NOT a review).** The ten HELD findings of
section 4 were adjudicated case-by-case by the independent C2-F1
adjudication of record (the Q3-C-D1-FU1 design revision, the
revision record of
`docs/PRODUCT_INTEL_Q3C_FU4_BUNDLE_AUTHORITY_QUALIFICATION_
DESIGN.md`, endpoint SHA `34ca5edf056c68c1719ed470e832e9f956626c19`,
2026-10-16T02:44:50Z; ratified at the Q3-C-D1-FU2 design gate,
endpoint SHA `4f53538f34c588c6f2b5e66a237f40acae2b5995`,
2026-10-16T17:36:55Z) and executed under the bounded C1-FU3 + C2
corrective implementation (design section 9.11, authorized at the
Q3-C-D1-FU2 endpoint): the C1 family loader corrections (the
section 4.4 PROVEN coherence scoping, the identity-context empty-
part-number decode, the allowed NONE-basis recorded-extraction-
result state + the named `CASEDOC_RECORDED_RESULT_CHANNEL_MAPPING`
refusal, the W9 coherence-separation statement) and the pre-seal
case corrections (the D3-ii re-label; the D11-ii SYNTHETIC re-
authoring; the B6-ii / B6-iii / C6 genuine recorded-extraction-
result re-authorings; the removal of FA4-ADV-034 + FA4-PROV-002
with their obligation destinations). The adjudication is the
release authority (the W3 monotonic held-set rule): every release
and removal below names the adjudicated correction. The
INDEPENDENT REVIEW HAS STILL NOT OCCURRED - every label remains
DRAFT (reviewer null), the reviewer column below remains
PENDING, and no reviewer identity, timestamp, signature, or
approval is recorded anywhere in this family.

## 2. Authoring methodology (the label independence contract,
section 4.6)

1. **Grounding class per case** (bounded): `DESIGN_TABLE_GROUNDED`
   (synthetic contract-coverage rows - the expected outcome follows
   from the cited approved-design rows), `REVIEWED_SOURCE_GROUNDED`
   (recorded-fixture rows - the expected outcome follows from the
   recorded source content + the cited row), `ADVERSARIAL_CONSTRUCTION`
   (D / defect rows - the expected refusal follows from the cited
   defect shape + the failure-stage analysis).
2. **Implementation-output prohibition (observed):** no expected value
   was derived from the FU4 derivation, the R1 record adapter, or any
   model. The authoring tooling (untracked, never committed) imports
   the frozen constructors / codec / P2 extractor exclusively to
   RECORD evidence documents (the constructor-is-validator discipline -
   the documents are inputs, the labels are not). The committed
   `fixtures.py` imports NO research module at all (stronger than the
   section 4.6(a) allowlist); the C2 suite import-scans it.
3. **Contract re-reading probes (documented; never label sources):** to
   ground the rows the design leaves "recorded per case" / "per the
   frozen derivation", the author re-read the FROZEN CONTRACT (design +
   code of record) and recorded the readings below. A probe output was
   consulted ONLY to confirm the contract's stated behavior for a cited
   row; where a probe and a cited design row disagreed, the design row
   governed and the disagreement was recorded (none occurred for the
   authored expectations - the disagreements found are the C2-F
   findings between the design matrix / stage semantics and the C1
   loader, section 4).
   * The standard scripted context (MATCH + HIGH + clean + the U1
     title-MPN identity substate) yields base tier
     `AI_ASSISTED_COMPARABLE` under the frozen S2-A matrix (P3 section
     5.3; Q3-B4 section 4.1) - the design matrix's stated
     "the tier stands" / "NEEDS_REVIEW + ceiling" consequences.
   * NO_MATCH scripted contexts yield base tier
     `EXCLUDED_LOW_CONFIDENCE` (the frozen S2-A matrix's NO_MATCH
     rows) - the D12 row's "recorded per case" tier (CF-5 / I-2).
   * The non-bundle arms (U1 / U3 / U8) derive PROVEN with the bundle-
     axis audit fields EXACTLY None (P3 D11) - the A-DELE row's
     "recorded per case" axes (and the C2-F1 conflict, section 4).
   * The count-only corpus-shaped channel is admitted by the frozen
     S2-C channel (P3 section 4 row 2) and derives U10 UNPROVEN - the
     B1 row.
   * The versioned completeness-marker list (`complete list`, `all
     items listed`, `everything included`, `all included`, `full
     contents`, `nothing else included`) is the ONLY published-
     attestation detector (P3 section 3.5b / T9) - the B11 / D9 rows.
   * SYNTACTICALLY_VALID / PARTIAL target records carry NO
     completeness attestation (the frozen constructor rule) - the B2 /
     B3 / B7 shapes.
   * The R1 record sections: `input_digest` over {binding, contract,
     case}, `output_digest` over {evaluation, execution, authority,
     derived}; the replay re-derives over the record's OWN authority +
     case channel and requires field-for-field agreement with the
     stored derived section (P5 section 4.2a; R1 matrix) - the A8 /
     D1-ii / D3-iii / D17-ii shapes.
4. **Temporal separation (observed):** this corpus is sealed (at the
   sealed endpoint) BEFORE the evaluator (E1) exists; the C2 suite
   pins that no evaluator surface exists in the family package.

## 3. The author pass - per case (the re-derivation record)

The table below is the author's independent derivation pass: each
expected outcome was re-derived from the cited design row over the
sealed recorded evidence (the rationale column is the derivation
statement). The author identity + instant are the recorded authorship
of the pass. **Every row's reviewer is PENDING - no independent
re-derivation has occurred; the column is deliberately empty, not
filled.**


## 4. The C2-F findings (the HELD cases - disagreement record)

The author found TEN cases where a valid approved case (per the design
matrix + frozen contract) conflicts with the C1 family loader or with
the recorded-source ground. Per the C2 directive these rows are
NOT bent, weakened, or omitted: the authored document carries the
design-grounded expectation, the conflict is recorded here + in the
case rationale, and the row is HELD for the design revision / schema
correction it names. The C2 suite pins the held set exactly and
demonstrates the loader behavior on each (at the corrected
endpoint the held set is EMPTY - the resolutions of record are
appended at the end of this section, and the C2 suite pins the
released / removed state under the W3 monotonic held-set rule).

* **C2-F1 (A-DELE U1 / U3 / U8 - FA4-DELE-001..003).** The design row
  expects the frozen FU3 PROVEN rows (non-bundle delegation, P3 D9 /
  D11: the bundle-axis audit fields are EXACTLY None for non-bundle
  channels). The C1 loader's PROVEN coherence pre-check (design
  section 4.4, as implemented) requires a satisfied bundle quantity
  axis + ESTABLISHED composition states for ANY PROVEN expectation -
  incompatible with the frozen non-bundle recording. The loader
  refuses the design-grounded label (LABEL_GOVERNANCE, confirmed by
  the suite). Resolution owner: a design revision (scope the
  section 4.4 coherence rule to bundle-channel cases) or a C1 schema
  correction - NEVER a bent label (recording BOTH_UNPUBLISHED /
  ESTABLISHED over a non-bundle channel would misstate the frozen
  contract and mislabel the E1 axis-audit comparison).
* **C2-F2a (D3-ii - FA4-ADV-006).** Content-IDENTICAL channels with
  DIFFERENT embedded original results: the design row names
  PRESENTATION_GATE (detected at the v3 embedding level), but the
  observable defect over the sealed documents is the embedded-vs-
  recorded-result mismatch - a case-document-integrity observation
  (CORPUS_INTEGRITY), because the channel-level gate steps cannot fire
  over content-identical channels (the documented frozen bound, P5
  R-5 / risk R-C1-10). The label carries the design row's stage; the
  CORPUS_INTEGRITY reading is recorded for the reviewer's
  adjudication.
* **C2-F2b (D16-iii - FA4-ADV-034).** The FU3-token derivation
  presentation (composition / attestation inputs under the historical
  token) is an EXECUTION-level contract-misuse refusal (P3 section
  5.4: the FU4 superset dispatch's FU3 arm delegates to the frozen
  function, which refuses). Over the sealed corpus documents (sound
  FU4 documents) NO constructor / codec / case-document observation
  fires, so the labeled CONSTRUCTION stage is incoherent per the
  family's stage rule. The row is instantiated at the DERIVATION
  surface with the design label; the E1 adversarial re-execution is
  the observation point the design names.
* **C2-F3 (A1-ii - FA4-PROV-002).** The RECORDED_FIXTURE-shape variant
  requires the candidate's PUBLISHED marker + attested clause span-
  grounded in committed recorded source; verified: no committed
  recorded source publishes bundle contents with a versioned
  completeness marker (design section 2.5) - the recorded 0034-shape
  context carries the clause WITHOUT the marker, and its title
  (additionally) cannot form the family's recorded identity context
  (no candidate MPN token). Authored over the closest recorded ground
  (the 0034 context + the recorded product page) with the row's
  expectation; HELD for the design revision / the C3 recorded-market
  bundle page.
* **C2-F5 (D11-ii - FA4-ADV-023).** The exact-identifier family
  variant grounds the one-character-different part numbers in the
  recorded Micron 7500 catalog (the committed fixture), but the
  recorded catalog publishes part numbers / specifications - no
  bundle contents - so the attested-CONTRADICTED expectation's
  clauses cannot be span-grounded without manufacturing recorded
  content; the catalog part-number titles additionally do not yield
  the family's non-empty normalized candidate part number under the
  one-character-different request (the exact-identifier separation IS
  the point). HELD.
* **C2-F6 (B6-ii / B6-iii / C6 - FA4-UNPR-011 / 012,
  FA4-CONTR-011).** The row's REQUIRED evidence is the RECORDED
  extraction result (AMBIGUOUS_CUE / CONTRADICTED_CUES over the
  ambiguous / conflicting fields). The family's basis-coherence rule
  cannot carry a recorded result without a candidate composition
  record (any basis value over (no record + recorded result) fires a
  case-document-mirror observation, which a DERIVED case may not
  carry), so the full row is unsealable at v1.0.0. Authored with the
  documented lighter shape (the canonical recorded-absence channel +
  the sealed published text, no extraction evidence) - the U0
  expectation is re-derivable over it; the evidence gap is recorded,
  not papered over. (C6 is the CF-1 documented conflict row - the
  frozen P2-to-FU4 chain records UNPROVEN over the recorded absence;
  the task matrix's CONTRADICTED placement is overridden by the
  frozen contract, O-3.)

**Resolutions of record (the independent C2-F1 adjudication -**
the Q3-C-D1-FU1 revision record, endpoint SHA `34ca5edf056c68c1719ed470e832e9f956626c19`,
2026-10-16T02:44:50Z; ratified at the Q3-C-D1-FU2 design gate, endpoint
SHA `4f53538f34c588c6f2b5e66a237f40acae2b5995`, 2026-10-16T17:36:55Z; executed under
the bounded C1-FU3 + C2 corrective implementation, design section 9.11).**
Each resolution names the higher-authority (frozen-contract)
citation that governed over both authors' readings (section 8.2
step 3) + the verified correction that makes the row sealable.
The adjudication report was NOT treated as authority over the
frozen contracts - where the adjudication and a frozen contract
met, the frozen contract governed.

* **C2-F1 (FA4-DELE-001..003) - RESOLVED / RELEASED.** The design
  section 4.4 coherence rule is scoped to Bundle-channel cases;
  the non-Bundle delegated FU3 PROVEN expectations retain the
  frozen P3 D11 audit-field semantics (the Bundle-axis fields
  EXACTLY null) - the byte-identical delegation (P3 D9) is
  preserved. The C1-FU3 loader correction implements it (a
  non-Bundle PROVEN carrying a non-null Bundle axis is refused
  with the named misstated-delegation reason). The three cases
  LOAD under the corrected loader with their design-grounded
  labels BYTE-UNCHANGED (never a bent label).
* **C2-F2a (FA4-ADV-006) - RESOLVED / RELEASED.** The stage is
  CORPUS_INTEGRITY (the mismatch - the record's embedded
  original != the case's recorded extraction evidence - is
  observable ONLY by the family loader; over content-identical
  channels the channel-content binding + all four frozen
  presentation-gate steps pass - the P5 R-5 bound; risk R-C1-10).
  The surface is DERIVATION (the self-consistent payload twin
  decodes and replays cleanly - the (ii) variant is surface
  DERIVATION, no record twin). The case is re-labeled
  CORPUS_INTEGRITY / error_type null / surface DERIVATION / replay
  NOT_APPLICABLE and the record twin is removed; it LOADS under
  the corrected loader. The separate D3-i PRESENTATION_GATE case
  (FA4-ADV-005) is preserved.
* **C2-F2b (FA4-ADV-034) - RESOLVED / REMOVED.** The FU3-token
  contract-misuse refusal is an EXECUTION-level observation point
  only (over the sealed documents - sound FU4 documents - no
  constructor / codec / case-document observation fires); it is
  NOT a sealable v1.0.0 corpus case at any refusal stage. The
  case is REMOVED from the v1.0.0 declared population (the case
  ID is retired; the v1.0.0 D16 corpus minimum is recorded as 2
  - the explicit phase-boundary correction of Q3-C-D1-FU1); the
  obligation is PRESERVED as the MANDATORY E1 adversarial-
  execution assertion (P3 section 5.4 / D9; design section 9.6;
  the M13 / G6 coverage note of the E1 baseline report); the
  frozen FU3 / FU4 token boundary is NOT weakened.
* **C2-F3 (FA4-PROV-002) - RESOLVED / REMOVED.** No committed
  recorded source publishes the required complete Bundle
  composition (design section 2.5 verified; past the identity-
  context defect, the span-grounding refusal is the second
  boundary). The A1 recorded PROVEN-shape variant is
  C3-deferred: the v1.0.0 A1 minimum is 1 (the SYNTHETIC case
  FA4-PROV-001); the RECORDED_FIXTURE variant is an additive
  1.1.0 obligation over the C3-acquired recorded source (P3 D19
  independently evidenced publisher completeness preserved -
  recorded evidence is never replaced with invented text; the
  section 7.6 distinctness requirements; the 1.1.0 re-seal
  verification). The case is REMOVED from the v1.0.0 declared
  population (the case ID is retired; the v1.0.0 A1 corpus
  minimum is recorded as 1 - the explicit phase-boundary
  correction of Q3-C-D1-FU1).
* **C2-F5 (FA4-ADV-023) - RESOLVED / RELEASED (re-authored).**
  The recorded identifier-family evidence (the one-character-
  different Micron 7500 catalog part numbers) is separated from
  the by-construction Bundle composition evidence: the hybrid
  variant CANNOT be represented truthfully by the existing schema
  (the span-grounding provenance rule + the row's required U1
  EXACT identity context - the recorded context is U4_NO_MPN, no
  candidate identifier; both boundaries verified at the
  revision). The case is re-authored SYNTHETIC with the row's
  EXACT U1 EXACT identity context (U1_TITLE_MPN, equal non-empty
  normalized part numbers, TITLE_MPN_TOKEN, NOT_REQUIRED - W8)
  instantiated by-construction over the recorded identifier
  family's own part-number shape; the Micron recorded catalog is
  documented as the row's identifier-shape CONTEXT (cited by path
  + digest) and is NOT claimed to publish Bundle compositions; a
  truthful RECORDED_FIXTURE D11 instantiation is the C3 / 1.1.0
  additive obligation (IF AND ONLY IF the recorded source
  publishes both the U1 EXACT identity context's recorded form and
  the attested composition clauses). The D11 material-
  contradiction authority contract (P3 U17) + its 2-case
  adversarial coverage are retained. The re-authored case LOADS
  under the corrected loader.
* **C2-F6 (FA4-UNPR-011 / FA4-UNPR-012 / FA4-CONTR-011) -
  RESOLVED / RELEASED (re-authored).** The allowed state of
  design section 4.4: candidate composition record null,
  candidate basis NONE, the recorded extraction result present,
  the presented channel EXACTLY the frozen P2 mapping of that
  result (the canonical UNAVAILABLE over AMBIGUOUS_CUE /
  CONTRADICTED_CUES), the expected authority independently
  derived from the frozen contract (U0 UNPROVEN over the
  canonical UNAVAILABLE mapping - P3 U0 / D8). The C1-FU3 loader
  correction admits the state + adds the named case-document-
  integrity refusal `CASEDOC_RECORDED_RESULT_CHANNEL_MAPPING`
  over the recorded-result / presented-channel mismatch; the
  existing EXTRACTION_RESULT_V1 / RECORDED_CHANNEL / NONE
  negative contracts are preserved. W7: FA4-CONTR-011's pre-
  correction sealed text was an AMBIGUOUS_CUE shape (the
  established pack-of-3 structured cue + the ambiguous count-only
  'bundle of 2' title cue) whose rationale claimed the
  CONTRADICTED_CUES state it did not carry - the re-authored case
  carries the GENUINE frozen CONTRADICTED_CUES instantiation (the
  title's established bundle-with-contents clause vs the
  structured pack-of-N field - verified over the frozen P2 cue
  table at the correction); the expectation (U0 UNPROVEN) is
  unchanged. All three cases carry the genuine frozen P2 results
  over their sealed texts and LOAD under the corrected loader.
* **C1 identity-context defect (G) - RESOLVED (loader
  correction).** The loader's identity decode allows the EMPTY
  normalized part numbers exactly where the frozen
  `IdentityStateAssessmentV2` constructor permits them (the
  U4_NO_MPN substate - 'no candidate identifier exists' - the
  normalized candidate part number is the empty string;
  symmetrically the E1_NO_TARGET_MPN substate - the normalized
  requested part number). The frozen constructor (type check
  only) + the round-trip projection remain the final arbiter; no
  other identity constraint is weakened; the frozen constructor
  is NOT modified. This was the first boundary over both held
  recorded-context cases (FA4-ADV-023 / FA4-PROV-002); over
  FA4-PROV-002 the span-grounding refusal was the second
  boundary (recorded under C2-F3 above).


## 5. Adversarial (D) rows - authorship record of record

The D rows (36 cases at the corrected endpoint - the C2 endpoint
37 minus the removed FA4-ADV-034, whose third D16 obligation is the
MANDATORY E1 adversarial-execution assertion) are
ADVERSARIAL_CONSTRUCTION: each defect shape was constructed from the
cited adversarial matrix (P4-FU1 / P4-FU2 / R1 / R2 / the Revision
records 2 / 3) and its failure stage from the cited failure-point
analysis. Per design section 7.6 the adversarial
rows require the INDEPENDENT TESTER's authorship or review signature -
**not yet obtained**: the tester record is PENDING (section 1). The
author's construction notes per D case are in the table's rationale
column; the tester re-derivation worklist (ALL D rows, per the C2
directive's 20% + all-adversarial minimum) is in
`reviewer_handoff.md` section 3.

## 6. Agreements / disagreements / corrections log

| # | case(s) | event | record |
| --- | --- | --- | --- |
| 1 | all 96 | author pass completed | section 3 table (re-derivation from the cited rows) |
| 2 | FA4-DELE-001..003 | disagreement: design row vs C1 loader coherence rule | C2-F1 - HELD, not bent |
| 3 | FA4-ADV-006 | disagreement: design stage vs observable stage | C2-F2a - HELD, both readings recorded |
| 4 | FA4-ADV-034 | disagreement: execution-level defect vs sealed-document observability | C2-F2b - HELD, E1 observation point recorded |
| 5 | FA4-PROV-002 | disagreement: recorded ground vs row's marker requirement | C2-F3 - HELD |
| 6 | FA4-ADV-023 | disagreement: recorded ground vs clause grounding | C2-F5 - HELD |
| 7 | FA4-UNPR-011/012, FA4-CONTR-011 | disagreement: required recorded result vs basis-coherence rule | C2-F6 - HELD, lighter shape authored + gap recorded |
| 8 | FA4-ADV-035 (D17-i) | correction of author's first reading: the design row names CONSTRUCTION; the stage-semantics (iii) rule + the loader's codec-observation layer key the record-surface constructor incoherence to CODEC_DECODE | labeled CODEC_DECODE, both readings recorded for the reviewer |
| 9 | FA4-ADV-012/013 (D6) | correction of author's first reading: the row names BOTH; the defects are corpus-level (outside the record authority section) and cannot be carried by the record-level twin | instantiated at DERIVATION, deviation recorded in the rationales |
| 10 | FA4-CONTR-008/009 (C4-ii/iii) | authoring correction: the explicit-form targets (frozen FU3 records) were first presented with basis NONE over a present candidate record (a mirror observation); corrected to the RECORDED_CHANNEL basis per the frozen construction | no label change; document correction only |
| 11 | - | reviewer entries | PENDING - the independent review has not occurred |
| 12 | all 10 HELD cases | ADJUDICATION of record: the independent C2-F1 adjudication resolves each finding case-by-case (the Q3-C-D1-FU1 revision record, endpoint SHA `34ca5edf056c68c1719ed470e832e9f956626c19`, 2026-10-16T02:44:50Z; ratified at the Q3-C-D1-FU2 design gate, endpoint SHA `4f53538f34c588c6f2b5e66a237f40acae2b5995`, 2026-10-16T17:36:55Z) - the frozen-contract citations govern over both authors' readings (section 8.2 step 3); the adjudication report is NOT treated as authority over the frozen contracts | the six RESOLUTION records in section 4 (each naming the higher-authority contract + the verified correction) |
| 13 | FA4-DELE-001..003 | RELEASED (W3 monotonic held-set rule) under the named correction: the C1-FU3 PROVEN-coherence scoping (the Bundle-specific checks apply only to Bundle-channel cases; the non-Bundle PROVEN expectation carries the frozen P3 D11 exactly-null Bundle-axis fields) | the cases load under the corrected loader with their design-grounded labels BYTE-UNCHANGED (no label bent) - verified case-by-case |
| 14 | FA4-ADV-006 | RELEASED under the named correction: the D3-ii re-label to the adjudicated CORPUS_INTEGRITY observation point (stage CORPUS_INTEGRITY, error_type null; surface BOTH -> DERIVATION; replay REPLAY_REFUSED -> NOT_APPLICABLE; the self-consistent record twin removed - it decodes and replays cleanly, so the (ii) variant is surface DERIVATION, no record twin) | the re-labeled case loads under the corrected loader - verified; the rationale records the adjudication + the R-5 bound |
| 15 | FA4-ADV-023 | RELEASED under the named correction: the D11-ii SYNTHETIC re-authoring (RECORDED_FIXTURE -> SYNTHETIC - the truthful evidence classification; the row's exact U1 EXACT identity context - U1_TITLE_MPN, equal non-empty normalized part numbers, TITLE_MPN_TOKEN, NOT_REQUIRED - W8; the by-construction attested compositions; the recorded Micron identifier family documented as the row's identifier-shape context, cited by path + digest, NOT claimed to publish Bundle compositions) | the re-authored case loads under the corrected loader - verified; the D11 2-case adversarial coverage is retained with FA4-ADV-022 |
| 16 | FA4-UNPR-011, FA4-UNPR-012 | RELEASED under the named correction: the C1-FU3 allowed NONE-basis recorded-extraction-result state (the recorded results are the GENUINE frozen P2 instantiations over the sealed texts - AMBIGUOUS_CUE BUNDLE_WITHOUT_CONTENTS count-only / bare-bundle shapes; the presented channel exactly the frozen P2 mapping - the canonical UNAVAILABLE; the U0 expectation independently derived from the frozen P2-to-FU4 chain) | the re-authored cases load under the corrected loader - verified; the expectations are unchanged |
| 17 | FA4-CONTR-011 | RELEASED under the named correction (C2-F6 + W7 cue-state accuracy): the GENUINE CONTRADICTED_CUES instantiation (the sealed candidate text corrected so that the title's established bundle-with-contents clause vs the structured pack-of-N field is what the recorded result carries - verified over the frozen P2 cue table; the presented channel exactly the frozen P2 mapping - the canonical UNAVAILABLE; the U0 expectation unchanged, independently derived) | the re-authored case loads under the corrected loader - verified |
| 18 | FA4-ADV-034 | REMOVED from the v1.0.0 declared population under the recorded adjudication (the W3 release direction that moves population accounting): the D16-iii FU3-token contract-misuse refusal is an EXECUTION-level observation point only - over the sealed documents no constructor / codec / case-document observation fires, so no C2 refusal stage is coherent; the v1.0.0 D16 corpus minimum is recorded as 2 (the explicit phase-boundary correction of Q3-C-D1-FU1) | the MANDATORY E1 adversarial-execution assertion (design section 9.6; the M13 / G6 coverage note of the E1 baseline report); the frozen FU3 / FU4 token boundary is NOT weakened |
| 19 | FA4-PROV-002 | REMOVED from the v1.0.0 declared population under the recorded adjudication: no committed recorded source publishes the required complete Bundle composition (design section 2.5 verified; the span-grounding refusal is the second boundary past the identity-context defect) | the C3 real-market acquisition + the additive 1.1.0 re-seal (P3 D19 independently evidenced publisher completeness preserved; the section 7.6 distinctness requirements; the 1.1.0 re-seal verification); the v1.0.0 A1 corpus minimum is recorded as 1 (the explicit phase-boundary correction of Q3-C-D1-FU1) |

| case_id | matrix_row | expected (outcome / unit / tier / stage) | grounding citation | author re-derivation (from the cited rows) | author | reviewer | status |
| --- | --- | --- | --- | --- | --- | --- | --- |
| FA4-ADV-001 | D1 | REFUSED / - / - / PRESENTATION_GATE/PRES... | Q3-C-D1 matrix row D1; P4-FU2 Revision record (the false-PROVEN defect shape: a self-consistent ESTABLISHED record ove... | Forged completeness attestation (i): a self-consistent ESTABLISHED RECORDED_CHANNEL record (all record digests valid -... | PRODUCT-INTEL.Q3C-C2.CORPUS-AUTHOR | PENDING | AUTHORED - review pending |
| FA4-ADV-002 | D1 | REFUSED / - / - / REPLAY_AGREEMENT/REPLA... | Q3-C-D1 matrix row D1; P4-FU2 Revision record (the false-PROVEN defect shape: a self-consistent ESTABLISHED record ove... | Forged completeness attestation (ii): the RECORD-surface payload over the (i) evidence - the authority section carries... | PRODUCT-INTEL.Q3C-C2.CORPUS-AUTHOR | PENDING | AUTHORED - review pending |
| FA4-ADV-003 | D1 | NON_CONSTRUCTIBLE / - / - / CODEC_DECODE... | Q3-C-D1 matrix row D1; P4-FU2 Revision record (the false-PROVEN defect shape: a self-consistent ESTABLISHED record ove... | Forged completeness attestation (iii): the variant whose stored derived section claims AI_ASSISTED_COMPARABLE + UNPROV... | PRODUCT-INTEL.Q3C-C2.CORPUS-AUTHOR | PENDING | AUTHORED - review pending |
| FA4-ADV-004 | D2 | REFUSED / - / - / PRESENTATION_GATE/PRES... | Q3-C-D1 matrix row D2; P3 section 5 preconditions (the RECORDED_CHANNEL record must be exactly the construction of the... | Self-consistent but ungrounded evidence: a hand-forged RECORDED_CHANNEL record (all digests recomputed - the exact con... | PRODUCT-INTEL.Q3C-C2.CORPUS-AUTHOR | PENDING | AUTHORED - review pending |
| FA4-ADV-005 | D3 | REFUSED / - / - / PRESENTATION_GATE/PRES... | Q3-C-D1 matrix row D3; P3 Revision record 3 (the v3 four-step original-result chain; the channel_content_digest bindin... | Cross-listing evidence substitution (i): listing A's EXTRACTION record (the embedded original result A, same source cl... | PRODUCT-INTEL.Q3C-C2.CORPUS-AUTHOR | PENDING | AUTHORED - review pending |
| FA4-ADV-006 | D3 | REFUSED / - / - / CORPUS_INTEGRITY/None | Q3-C-D1 matrix row D3 (ii) as adjudicated by the Q3-C-D1-FU1 / C2-F2a revision record; P3 Revision record 3 (the v3 four-step original-result chain; the channel_content_digest binding); P5 R-5 (the frozen channel-granularity bound: over content-identical channels the channel-content binding + all four presentation-gate steps pass); Q3-C-D1 section 5 stage semantics (iv) (the CORPUS_INTEGRITY loader-only observation point) | Cross-listing substitution (ii) - the adjudicated CORPUS_INTEGRITY observation point: content-IDENTICAL channels (the P5 R-5 bound) with DIFFERENT embedded original results - the record embeds listing A's original while the case's recorded extraction evidence is listing B's own original; the observable defect is the case-document-integrity observation only the family loader sees (the presentation gate CANNOT detect the substitution); the pre-adjudication PRESENTATION_GATE label + the self-consistent record twin are removed (the twin decodes and replays cleanly - surface DERIVATION, no record twin); the separate D3-i PRESENTATION_GATE case (FA4-ADV-005) is preserved | PRODUCT-INTEL.Q3C-C2.CORPUS-AUTHOR | PENDING | CORRECTED (C2-F2a released) - review pending |
| FA4-ADV-007 | D3 | REFUSED / - / - / REPLAY_AGREEMENT/REPLA... | Q3-C-D1 matrix row D3; P3 Revision record 3 (the v3 four-step original-result chain; the channel_content_digest bindin... | Cross-listing substitution (iii): the RECORD-surface payload's authority section swapped from another record over the ... | PRODUCT-INTEL.Q3C-C2.CORPUS-AUTHOR | PENDING | AUTHORED - review pending |
| FA4-ADV-008 | D4 | REFUSED / - / - / CONSTRUCTION/CONSTRUCT... | Q3-C-D1 matrix row D4; P3 Revision record 3 (the embedded result's own integrity + the anchor-vs-embedding equality ar... | Modified original extraction evidence (i): the embedded result's cue text is tampered and the result's digests are rec... | PRODUCT-INTEL.Q3C-C2.CORPUS-AUTHOR | PENDING | AUTHORED - review pending |
| FA4-ADV-009 | D4 | REFUSED / - / - / CONSTRUCTION/CONSTRUCT... | Q3-C-D1 matrix row D4; P3 Revision record 3 (the embedded result's own integrity + the anchor-vs-embedding equality ar... | Modified original extraction evidence (ii): the embedded result's raw_field_value is tampered (the cue-span containmen... | PRODUCT-INTEL.Q3C-C2.CORPUS-AUTHOR | PENDING | AUTHORED - review pending |
| FA4-ADV-010 | D5 | REFUSED / - / - / PRESENTATION_GATE/PRES... | Q3-C-D1 matrix row D5; P3 Revision record 3 gate steps 3-4 (the frozen P2 mapping equality; the recomputed-composition... | Recomputed forged digests (i): a fully self-consistent EXTRACTION record (embedded original A, anchors A, digests A) w... | PRODUCT-INTEL.Q3C-C2.CORPUS-AUTHOR | PENDING | AUTHORED - review pending |
| FA4-ADV-011 | D5 | REFUSED / - / - / PRESENTATION_GATE/PRES... | Q3-C-D1 matrix row D5; P3 Revision record 3 gate steps 3-4 (the frozen P2 mapping equality; the recomputed-composition... | Recomputed forged digests (ii): the embedded original maps correctly (the frozen P2 mapping equals the presented chann... | PRODUCT-INTEL.Q3C-C2.CORPUS-AUTHOR | PENDING | AUTHORED - review pending |
| FA4-ADV-012 | D6 | REFUSED / - / - / CONSTRUCTION/CONSTRUCT... | Q3-C-D1 matrix row D6; P3 Revision record 3 (the embedded result binds the exact examined input - the input digest / c... | Source-content mismatch (i): the recorded extraction input document (the sealed source text's projection) is NOT the i... | PRODUCT-INTEL.Q3C-C2.CORPUS-AUTHOR | PENDING | AUTHORED - review pending |
| FA4-ADV-013 | D6 | REFUSED / - / - / CORPUS_INTEGRITY/None | Q3-C-D1 matrix row D6; P3 Revision record 3 (the embedded result binds the exact examined input - the input digest / c... | Source-content mismatch (ii): the case's derivation channel (listing B's) differs from the recorded case's channel (li... | PRODUCT-INTEL.Q3C-C2.CORPUS-AUTHOR | PENDING | AUTHORED - review pending |
| FA4-ADV-014 | D7 | DERIVED / UNPROVEN / NEEDS_REVIEW / - | Q3-C-D1 matrix row D7; P3 section 11 T2 residual (truncation can never reach PROVEN without a surviving attestation: t... | Truncated source content (i): the colon-form title cut at max length MID-CLAUSE (no marker survives, no partial form):... | PRODUCT-INTEL.Q3C-C2.CORPUS-AUTHOR | PENDING | AUTHORED - review pending |
| FA4-ADV-015 | D7 | REFUSED / - / - / CONSTRUCTION/CONSTRUCT... | Q3-C-D1 matrix row D7; P3 section 11 T2 residual (truncation can never reach PROVEN without a surviving attestation: t... | Truncated source content (ii): the RECORDED-FIXTURE variant - the sealed candidate block cites the recorded OEMPCWorld... | PRODUCT-INTEL.Q3C-C2.CORPUS-AUTHOR | PENDING | AUTHORED - review pending |
| FA4-ADV-016 | D8 | DERIVED / CONTRADICTED / NEEDS_REVIEW / ... | Q3-C-D1 matrix row D8; P3 U17 (manufacturer-anchored attested composition vs materially different attested reseller co... | Conflicting manufacturer versus reseller claims (i): the target review attestation is anchored to the MANUFACTURER-pub... | PRODUCT-INTEL.Q3C-C2.CORPUS-AUTHOR | PENDING | AUTHORED - review pending |
| FA4-ADV-017 | D8 | DERIVED / UNPROVEN / NEEDS_REVIEW / - | Q3-C-D1 matrix row D8; P3 U17 (manufacturer-anchored attested composition vs materially different attested reseller co... | Conflicting manufacturer versus reseller claims (ii): the same shape with the candidate UNattested (closed clause, no ... | PRODUCT-INTEL.Q3C-C2.CORPUS-AUTHOR | PENDING | AUTHORED - review pending |
| FA4-ADV-018 | D9 | DERIVED / UNPROVEN / NEEDS_REVIEW / - | Q3-C-D1 matrix row D9; P3 section 3.5b (only the versioned marker list is a completeness statement - the pseudo-comple... | Prompt injection in listing text (i): the sealed source records the full injected text (the publication's truth); the ... | PRODUCT-INTEL.Q3C-C2.CORPUS-AUTHOR | PENDING | AUTHORED - review pending |
| FA4-ADV-019 | D9 | DERIVED / UNPROVEN / NEEDS_REVIEW / - | Q3-C-D1 matrix row D9; P3 section 3.5b (only the versioned marker list is a completeness statement - the pseudo-comple... | Prompt injection in listing text (ii): the sealed source records the full injected text (the publication's truth); the... | PRODUCT-INTEL.Q3C-C2.CORPUS-AUTHOR | PENDING | AUTHORED - review pending |
| FA4-ADV-020 | D10 | DERIVED / UNPROVEN / NEEDS_REVIEW / - | Q3-C-D1 matrix row D10; P3 section 5 'never an input, never inferred' (the scripted evaluation's attribute detail is n... | Constituent claims without published support published support (i): the scripted evaluation detail names a constituent... | PRODUCT-INTEL.Q3C-C2.CORPUS-AUTHOR | PENDING | AUTHORED - review pending |
| FA4-ADV-021 | D10 | DERIVED / UNPROVEN / NEEDS_REVIEW / - | Q3-C-D1 matrix row D10; P3 section 5 'never an input, never inferred' (the scripted evaluation's attribute detail is n... | Constituent claims without published support published support (ii): the scripted evaluation detail names a constituen... | PRODUCT-INTEL.Q3C-C2.CORPUS-AUTHOR | PENDING | AUTHORED - review pending |
| FA4-ADV-022 | D11 | DERIVED / CONTRADICTED / NEEDS_REVIEW / ... | Q3-C-D1 matrix row D11; invariant I-1 (exact identity never implies unit equivalence - Q3-C-D1 section 3.1); P3 U17 (t... | Exact-MPN match but Bundle composition mismatch (i): the recorded U1 title-MPN identity context (the requested MPN is ... | PRODUCT-INTEL.Q3C-C2.CORPUS-AUTHOR | PENDING | AUTHORED - review pending |
| FA4-ADV-023 | D11 | DERIVED / CONTRADICTED / NEEDS_REVIEW / - | Q3-C-D1 matrix row D11 (ii) as adjudicated by the Q3-C-D1-FU1 / C2-F5 / W8 revision record; invariant I-1 (exact identity never implies unit equivalence - Q3-C-D1 section 3.1); P3 U17 (two attested materially different compositions); the recorded Micron 7500 identifier family (tests/fixtures/pages/micron_7500_part_catalog.json - the one-character-different part numbers) is the row's documented identifier-shape CONTEXT only (the catalog publishes part numbers / specifications, NOT Bundle compositions - verified Q3-C-D1 section 2.5) | Exact-MPN match but Bundle composition mismatch (ii) - the adjudicated SYNTHETIC re-authoring: the row's exact U1 EXACT identity context (U1_TITLE_MPN, equal non-empty normalized part numbers, TITLE_MPN_TOKEN, NOT_REQUIRED) instantiated by-construction over the recorded identifier family's own part-number shape; the pre-correction RECORDED_FIXTURE hybrid CANNOT be represented truthfully by the existing schema (the span-grounding provenance rule + the U4_NO_MPN recorded context is not the row's shape - W8); by-construction attested compositions (candidate '2x SSD + 1x RAM' vs target '2x SSD + 1x GPU' - materially different) => U17 CONTRADICTED + CEILING_SALES_UNIT_CONTRADICTED, pricing non-eligible; the truthful RECORDED_FIXTURE D11 instantiation is the C3 / 1.1.0 additive obligation | PRODUCT-INTEL.Q3C-C2.CORPUS-AUTHOR | PENDING | CORRECTED (C2-F5 released) - review pending |
| FA4-ADV-024 | D12 | DERIVED / PROVEN_EQUIVALENT / EXCLUDED_L... | Q3-C-D1 matrix row D12; invariant I-2 / CF-5 (the unit axis is decision-independent: an attested-equivalent compositio... | Semantic NO_MATCH with apparently equivalent Bundle composition (CF-5 / I-2): scripted NO_MATCH+HIGH with an independe... | PRODUCT-INTEL.Q3C-C2.CORPUS-AUTHOR | PENDING | AUTHORED - review pending |
| FA4-ADV-025 | D13 | DERIVED / UNPROVEN / NEEDS_REVIEW / - | Q3-C-D1 matrix row D13; invariant I-1 (high-confidence MATCH never substitutes for the missing authority evidence); P3... | AI high-confidence MATCH despite missing authority evidence (i): MATCH+HIGH+STRONG over a channel UNAVAILABLE (no bund... | PRODUCT-INTEL.Q3C-C2.CORPUS-AUTHOR | PENDING | AUTHORED - review pending |
| FA4-ADV-026 | D13 | DERIVED / UNPROVEN / NEEDS_REVIEW / - | Q3-C-D1 matrix row D13; invariant I-1 (high-confidence MATCH never substitutes for the missing authority evidence); P3... | AI high-confidence MATCH despite missing authority evidence (ii): MATCH+HIGH+STRONG over a bundle channel with NO comp... | PRODUCT-INTEL.Q3C-C2.CORPUS-AUTHOR | PENDING | AUTHORED - review pending |
| FA4-ADV-027 | D14 | REFUSED / - / - / CONSTRUCTION/CONSTRUCT... | Q3-C-D1 matrix row D14; P3 section 3.8 (the candidate-side completeness claim with a REVIEWED basis is un-constructibl... | Attestation laundering (i): the candidate-side record carries a REVIEWED_COMPOSITION_ATTESTATION basis - a review atte... | PRODUCT-INTEL.Q3C-C2.CORPUS-AUTHOR | PENDING | AUTHORED - review pending |
| FA4-ADV-028 | D14 | REFUSED / - / - / CONSTRUCTION/CONSTRUCT... | Q3-C-D1 matrix row D14; P3 section 3.8 (the candidate-side completeness claim with a REVIEWED basis is un-constructibl... | Attestation laundering (ii): the target attestation carries a CANDIDATE source class (PUBLISHED_STRUCTURED_FIELD - out... | PRODUCT-INTEL.Q3C-C2.CORPUS-AUTHOR | PENDING | AUTHORED - review pending |
| FA4-ADV-029 | D14 | REFUSED / - / - / CONSTRUCTION/CONSTRUCT... | Q3-C-D1 matrix row D14; P3 section 3.8 (the candidate-side completeness claim with a REVIEWED basis is un-constructibl... | Attestation laundering (iii): the completeness attestation's clause_digest binds a DIFFERENT clause (the digest over '... | PRODUCT-INTEL.Q3C-C2.CORPUS-AUTHOR | PENDING | AUTHORED - review pending |
| FA4-ADV-030 | D15 | REFUSED / - / - / CONSTRUCTION/CONSTRUCT... | Q3-C-D1 matrix row D15; P3 section 3.8 + section 5 preconditions (the quantity attestation's subject must be the actua... | Quantity-attestation abuse (i): the quantity attestation's subject_side (CANDIDATE) is not the actually-missing side (... | PRODUCT-INTEL.Q3C-C2.CORPUS-AUTHOR | PENDING | AUTHORED - review pending |
| FA4-ADV-031 | D15 | REFUSED / - / - / CONSTRUCTION/CONSTRUCT... | Q3-C-D1 matrix row D15; P3 section 3.8 + section 5 preconditions (the quantity attestation's subject must be the actua... | Quantity-attestation abuse (ii): the attestation is presented over a NON-asymmetric published axis (both sides publish... | PRODUCT-INTEL.Q3C-C2.CORPUS-AUTHOR | PENDING | AUTHORED - review pending |
| FA4-ADV-032 | D16 | REFUSED / - / - / CODEC_DECODE/CODEC | Q3-C-D1 matrix row D16; P5 section 4.2a + the codec registry (the production codec claims exactly the V1 / 2.0-FU2 / 2... | Historical binding confusion (i): the forged mixed-axis payload (V2, 2.0, 1, 1, FU4 - the input digest re-sealed over ... | PRODUCT-INTEL.Q3C-C2.CORPUS-AUTHOR | PENDING | AUTHORED - review pending |
| FA4-ADV-033 | D16 | REFUSED / - / - / CODEC_DECODE/CODEC | Q3-C-D1 matrix row D16; P5 section 4.2a + the codec registry (the production codec claims exactly the V1 / 2.0-FU2 / 2... | Historical binding confusion (ii): a 2.1/FU3-bound payload presented to the production codec (the input digest re-seal... | PRODUCT-INTEL.Q3C-C2.CORPUS-AUTHOR | PENDING | AUTHORED - review pending |
| FA4-ADV-035 | D17 | NON_CONSTRUCTIBLE / - / - / CODEC_DECODE... | Q3-C-D1 matrix row D17; P3 section 5.3 + the decision record's construction invariants (the firewall: AI_ASSISTED with... | Replay-conformance tamper (i): the stored derived section claims AI_ASSISTED_COMPARABLE + UNPROVEN (the section digest... | PRODUCT-INTEL.Q3C-C2.CORPUS-AUTHOR | PENDING | AUTHORED - review pending |
| FA4-ADV-036 | D17 | REFUSED / - / - / REPLAY_AGREEMENT/REPLA... | Q3-C-D1 matrix row D17; P3 section 5.3 + the decision record's construction invariants (the firewall: AI_ASSISTED with... | Replay-conformance tamper (ii): the stored derived section is self-consistent with its own digests (the PROVEN snapsho... | PRODUCT-INTEL.Q3C-C2.CORPUS-AUTHOR | PENDING | AUTHORED - review pending |
| FA4-ADV-037 | D18 | DERIVED / UNPROVEN / NEEDS_REVIEW / - | Q3-C-D1 matrix row D18; gate MB-3 (a completeness attestation recorded by a model is never treated as publisher eviden... | A completeness assertion recorded by a model being treated as publisher evidence - the structural row: the scripted ev... | PRODUCT-INTEL.Q3C-C2.CORPUS-AUTHOR | PENDING | AUTHORED - review pending |
| FA4-CONTR-001 | C1 | DERIVED / CONTRADICTED / NEEDS_REVIEW / ... | Q3-C-D1 matrix row C1; P3 U17 (both ESTABLISHED, multisets differ - T-DIFF-MATERIAL); P3 section 3.7 (material differe... | Different constituent identity: both sides ESTABLISHED and fully parseable; the multisets differ on an item ('2x RAM +... | PRODUCT-INTEL.Q3C-C2.CORPUS-AUTHOR | PENDING | AUTHORED - review pending |
| FA4-CONTR-002 | C1 | DERIVED / CONTRADICTED / NEEDS_REVIEW / ... | Q3-C-D1 matrix row C1; P3 U17 (both ESTABLISHED, multisets differ - T-DIFF-MATERIAL); P3 section 3.7 (material differe... | Different constituent identity: both sides ESTABLISHED and fully parseable; the multisets differ on an item ('2x RAM +... | PRODUCT-INTEL.Q3C-C2.CORPUS-AUTHOR | PENDING | AUTHORED - review pending |
| FA4-CONTR-003 | C2 | DERIVED / CONTRADICTED / NEEDS_REVIEW / ... | Q3-C-D1 matrix row C2; P3 U17 / section 3.7 (shared-item quantity difference) | Different constituent multiplicity: both sides ESTABLISHED; the shared item's quantity differs ('2x RAM' vs '3x RAM') ... | PRODUCT-INTEL.Q3C-C2.CORPUS-AUTHOR | PENDING | AUTHORED - review pending |
| FA4-CONTR-004 | C2b | DERIVED / CONTRADICTED / NEEDS_REVIEW / ... | Q3-C-D1 matrix row C2b (CF-3): the frozen versioned grammar does NOT merge repeated item tokens (P3 section 3.7 multis... | CF-3 frozen duplicate-constituent multiset semantics: the candidate publishes the repeated-token form '1x RAM + 1x RAM... | PRODUCT-INTEL.Q3C-C2.CORPUS-AUTHOR | PENDING | AUTHORED - review pending |
| FA4-CONTR-005 | C3 | DERIVED / CONTRADICTED / NEEDS_REVIEW / ... | Q3-C-D1 matrix row C3; P3 U16 (a count difference over textually-agreed clauses is a published incompatibility that co... | Published quantity contradiction (i): both sides publish DIFFERENT counts (2 vs 3) over textually AGREED attested clau... | PRODUCT-INTEL.Q3C-C2.CORPUS-AUTHOR | PENDING | AUTHORED - review pending |
| FA4-CONTR-006 | C3 | DERIVED / CONTRADICTED / NEEDS_REVIEW / ... | Q3-C-D1 matrix row C3; P3 U16 (a count difference over textually-agreed clauses is a published incompatibility that co... | Published quantity contradiction (ii): both sides publish DIFFERENT counts (2 vs 3) over textually AGREED clauses with... | PRODUCT-INTEL.Q3C-C2.CORPUS-AUTHOR | PENDING | AUTHORED - review pending |
| FA4-CONTR-007 | C4 | DERIVED / CONTRADICTED / NEEDS_REVIEW / ... | Q3-C-D1 matrix row C4; P3 U9 (the form rule fires before any composition is read, even an ESTABLISHED candidate compos... | Different sales-unit form (i): the bundle candidate (the recorded 0034-shape form-axis context - the recorded OEMPCWor... | PRODUCT-INTEL.Q3C-C2.CORPUS-AUTHOR | PENDING | AUTHORED - review pending |
| FA4-CONTR-008 | C4 | DERIVED / CONTRADICTED / NEEDS_REVIEW / ... | Q3-C-D1 matrix row C4; P3 U9 (the form rule fires before any composition is read, even an ESTABLISHED candidate compos... | Different sales-unit form (ii): the bundle candidate (attested ESTABLISHED composition presented) vs an explicit PACK ... | PRODUCT-INTEL.Q3C-C2.CORPUS-AUTHOR | PENDING | AUTHORED - review pending |
| FA4-CONTR-009 | C4 | DERIVED / CONTRADICTED / NEEDS_REVIEW / ... | Q3-C-D1 matrix row C4; P3 U9 (the form rule fires before any composition is read, even an ESTABLISHED candidate compos... | Different sales-unit form (iii): the bundle candidate (attested ESTABLISHED composition - the form-over-composition ro... | PRODUCT-INTEL.Q3C-C2.CORPUS-AUTHOR | PENDING | AUTHORED - review pending |
| FA4-CONTR-010 | C5 | DERIVED / CONTRADICTED / NEEDS_REVIEW / ... | Q3-C-D1 matrix row C5; P3 U17 (the UNDETERMINED quantity gap is recorded, does not shield the contradiction); P3 ten-c... | Complete but non-equivalent composition with an asymmetric quantity gap: both sides ESTABLISHED, materially different ... | PRODUCT-INTEL.Q3C-C2.CORPUS-AUTHOR | PENDING | AUTHORED - review pending |
| FA4-CONTR-011 | C6 | DERIVED / UNPROVEN / NEEDS_REVIEW / - | Q3-C-D1 matrix row C6 (CF-1 documented) as adjudicated by the Q3-C-D1-FU1 / C2-F6 / W7 revision record: the frozen P2 rule - a kind or quantity conflict across fields records absence (CONTRADICTED_CUES => the canonical UNAVAILABLE channel) => U0 UNPROVEN under the frozen P2-to-FU4 chain (P3 U0 / D8); recorded against the task matrix's CONTRADICTED placement, which the frozen contract (P3 D8 / U12; R1 matrix row 8) overrides (O-3) | CF-1 documented conflict row - the GENUINE CONTRADICTED_CUES instantiation (the W7 cue-state accuracy correction): the sealed candidate text publishes two ESTABLISHED incompatible cues across fields (the title's established bundle-with-contents clause 'bundle: 2x RAM + 1x CPU' vs the structured pack-of-N field 'pack of 3' - verified over the frozen P2 cue table); the case carries the allowed recorded-extraction-result state (record null, basis NONE, the presented channel exactly the frozen P2 mapping - the canonical UNAVAILABLE); the U0 expectation is independently derived from the frozen P2-to-FU4 chain over the recorded absence; the pre-correction sealed text was an AMBIGUOUS_CUE shape whose rationale claimed the state it did not carry (the label defect the W7 adjudication names) - the expectation is unchanged, the evidence now carries the state the row requires | PRODUCT-INTEL.Q3C-C2.CORPUS-AUTHOR | PENDING | CORRECTED (C2-F6 / W7 released) - review pending |
| FA4-CONTR-012 | C7 | REFUSED / - / - / CONSTRUCTION/CONSTRUCT... | Q3-C-D1 matrix row C7; P3 section 3.8 (a completeness attestation is usable ONLY over a SYNTACTICALLY_VALID clause - P... | Published evidence contradicting an asserted completeness attestation (i): the sealed record claims ESTABLISHED + a PU... | PRODUCT-INTEL.Q3C-C2.CORPUS-AUTHOR | PENDING | AUTHORED - review pending |
| FA4-CONTR-013 | C7 | REFUSED / - / - / PRESENTATION_GATE/PRES... | Q3-C-D1 matrix row C7; P3 section 3.8 (a completeness attestation is usable ONLY over a SYNTACTICALLY_VALID clause - P... | Published evidence contradicting an asserted completeness attestation (ii): a RECORDED_CHANNEL record claiming ESTABLI... | PRODUCT-INTEL.Q3C-C2.CORPUS-AUTHOR | PENDING | AUTHORED - review pending |
| FA4-DELE-001 | A-DELE | DERIVED / PROVEN_EQUIVALENT / AI_ASSISTED_COMPARABLE / - | Q3-C-D1 matrix row A-DELE; P3 section 5 U0-U8 (the frozen FU3 rows, delegation byte-identity D9); P3 D18 (frozen target records read composition-ABSENT); P3 D11 (non-bundle audit fields exactly None) | Non-bundle delegation preservation at corpus scale: pack of 4 vs the same-count frozen FU3 target record derives the frozen FU3 row U3 PROVEN_EQUIVALENT under the FU4 token (D9 - the non-bundle arms are byte-identical to the frozen FU3 derivation); the expected Bundle-axis fields are EXACTLY null on the expected axes (the frozen P3 D11 non-bundle audit-field semantics) - released by the recorded C2-F1 adjudication (the C1-FU3 PROVEN-coherence scoping; the label is the design-grounded shape, NOT bent) | PRODUCT-INTEL.Q3C-C2.CORPUS-AUTHOR | PENDING | CORRECTED (C2-F1 released) - review pending |
| FA4-DELE-002 | A-DELE | DERIVED / PROVEN_EQUIVALENT / AI_ASSISTED_COMPARABLE / - | Q3-C-D1 matrix row A-DELE; P3 section 5 U0-U8 (the frozen FU3 rows, delegation byte-identity D9); P3 D18 (frozen target records read composition-ABSENT); P3 D11 (non-bundle audit fields exactly None) | Non-bundle delegation preservation at corpus scale: tray of 25 vs the same-count frozen FU3 target record derives the frozen FU3 row U8 PROVEN_EQUIVALENT under the FU4 token (D9 - the non-bundle arms are byte-identical to the frozen FU3 derivation); the expected Bundle-axis fields are EXACTLY null on the expected axes (the frozen P3 D11 non-bundle audit-field semantics) - released by the recorded C2-F1 adjudication (the C1-FU3 PROVEN-coherence scoping; the label is the design-grounded shape, NOT bent) | PRODUCT-INTEL.Q3C-C2.CORPUS-AUTHOR | PENDING | CORRECTED (C2-F1 released) - review pending |
| FA4-DELE-003 | A-DELE | DERIVED / PROVEN_EQUIVALENT / AI_ASSISTED_COMPARABLE / - | Q3-C-D1 matrix row A-DELE; P3 section 5 U0-U8 (the frozen FU3 rows, delegation byte-identity D9); P3 D18 (frozen target records read composition-ABSENT); P3 D11 (non-bundle audit fields exactly None) | Non-bundle delegation preservation at corpus scale: single unit vs the default single-unit target derives the frozen FU3 row U1 PROVEN_EQUIVALENT under the FU4 token (D9 - the non-bundle arms are byte-identical to the frozen FU3 derivation); the expected Bundle-axis fields are EXACTLY null on the expected axes (the frozen P3 D11 non-bundle audit-field semantics) - released by the recorded C2-F1 adjudication (the C1-FU3 PROVEN-coherence scoping; the label is the design-grounded shape, NOT bent) | PRODUCT-INTEL.Q3C-C2.CORPUS-AUTHOR | PENDING | CORRECTED (C2-F1 released) - review pending |
| FA4-DELE-004 | A-DELE | DERIVED / UNPROVEN / NEEDS_REVIEW / - | Q3-C-D1 matrix row A-DELE; P3 section 5 U0-U8 (the frozen FU3 rows, delegation byte-identity D9); P3 D18 (frozen targe... | Non-bundle absence row at corpus scale over the recorded Samsung PM9A3 page (the committed fixture cited by path + dig... | PRODUCT-INTEL.Q3C-C2.CORPUS-AUTHOR | PENDING | AUTHORED - review pending |
| FA4-DELE-005 | B-DELE | DERIVED / UNPROVEN / NEEDS_REVIEW / - | Q3-C-D1 matrix row B-DELE; P3 U0 (recorded absence is UNPROVEN for every target, FU3-identical); P3 section 5.3 | UNAVAILABLE channel vs the default single-unit target (U0 recorded at corpus scale) over the recorded DirectMacro BCM9... | PRODUCT-INTEL.Q3C-C2.CORPUS-AUTHOR | PENDING | AUTHORED - review pending |
| FA4-DELE-006 | B-DELE | DERIVED / UNPROVEN / NEEDS_REVIEW / - | Q3-C-D1 matrix row B-DELE; P3 U0 (recorded absence is UNPROVEN for every target, FU3-identical); P3 section 5.3 | UNAVAILABLE channel vs the STRONGEST target shape (an attested ESTABLISHED bundle record): the recorded absence admits... | PRODUCT-INTEL.Q3C-C2.CORPUS-AUTHOR | PENDING | AUTHORED - review pending |
| FA4-DELE-007 | B-DELE | DERIVED / UNPROVEN / NEEDS_REVIEW / - | Q3-C-D1 matrix row TB-6 (the Track B population over the B-DELE row); the frozen 2.1 COMMERCIAL SALES-UNIT RULES (reco... | The TB-6 / TB-8 model control over the recorded Samsung PM9A3 page (the committed fixture cited by path + digest): the... | PRODUCT-INTEL.Q3C-C2.CORPUS-AUTHOR | PENDING | AUTHORED - review pending |
| FA4-PROV-001 | A1 | DERIVED / PROVEN_EQUIVALENT / AI_ASSISTE... | Q3-C-D1 matrix row A1; P3 section 5 U19 / ten-case matrix case 4; P3 section 3.8 (independent attestations); Q3-B4 sec... | Both configurations are independently complete: the candidate's PUBLISHED marker is detected from the recorded text ('... | PRODUCT-INTEL.Q3C-C2.CORPUS-AUTHOR | PENDING | AUTHORED - review pending |
| FA4-PROV-003 | A2 | DERIVED / PROVEN_EQUIVALENT / AI_ASSISTE... | Q3-C-D1 matrix row A2; P3 section 5 U20 / section 3.7 (multiset secondary path); P3 section 3.8; P3 section 5.3 (tier ... | Different wording with an equivalent constituent multiset under the versioned grammar (candidate '2x RAM + 1x CPU' vs ... | PRODUCT-INTEL.Q3C-C2.CORPUS-AUTHOR | PENDING | AUTHORED - review pending |
| FA4-PROV-004 | A2 | DERIVED / PROVEN_EQUIVALENT / AI_ASSISTE... | Q3-C-D1 matrix row A2; P3 section 5 U20 / section 3.7 (multiset secondary path); P3 section 3.8; P3 section 5.3 (tier ... | Different wording with an equivalent constituent multiset under the versioned grammar (candidate '2x RAM + 1x CPU' vs ... | PRODUCT-INTEL.Q3C-C2.CORPUS-AUTHOR | PENDING | AUTHORED - review pending |
| FA4-PROV-005 | A3 | DERIVED / PROVEN_EQUIVALENT / AI_ASSISTE... | Q3-C-D1 matrix row A3; P3 section 5 U20 / section 3.7 (order immaterial); P3 section 3.8; P3 section 5.3 | Different ordering only ('2x RAM + 1x CPU' vs '1x CPU + 2x RAM'): the versioned grammar treats order as immaterial (T-... | PRODUCT-INTEL.Q3C-C2.CORPUS-AUTHOR | PENDING | AUTHORED - review pending |
| FA4-PROV-006 | A4 | DERIVED / PROVEN_EQUIVALENT / AI_ASSISTE... | Q3-C-D1 matrix row A4; P3 section 5 U19 (byte-identity primary path); CF-3 frozen multiset semantics (no merging of re... | Valid duplicate constituent quantities published BYTE-IDENTICALLY on both sides ('1x RAM + 1x RAM + 1x CPU', both atte... | PRODUCT-INTEL.Q3C-C2.CORPUS-AUTHOR | PENDING | AUTHORED - review pending |
| FA4-PROV-007 | A5 | DERIVED / PROVEN_EQUIVALENT / AI_ASSISTE... | Q3-C-D1 matrix row A5; P3 section 5 U19 / U20 + section 3.8 quantity axis CONSISTENT (D20); P3 section 5.3 | Quantity-axis consistency row 1: both sides publish the EQUAL count 3 over attested byte-identical clauses => Q=CONSIS... | PRODUCT-INTEL.Q3C-C2.CORPUS-AUTHOR | PENDING | AUTHORED - review pending |
| FA4-PROV-008 | A5 | DERIVED / PROVEN_EQUIVALENT / AI_ASSISTE... | Q3-C-D1 matrix row A5; P3 section 5 U19 / U20 + section 3.8 quantity axis CONSISTENT (D20); P3 section 5.3 | Quantity-axis consistency row 2: both sides publish the EQUAL count 2 over multiset-phrasing attested clauses ('2x RAM... | PRODUCT-INTEL.Q3C-C2.CORPUS-AUTHOR | PENDING | AUTHORED - review pending |
| FA4-PROV-009 | A6 | DERIVED / PROVEN_EQUIVALENT / AI_ASSISTE... | Q3-C-D1 matrix row A6; P3 section 5 ten-case matrix case 2 (ATTESTED_NOT_MATERIAL arm) / U19; P3 section 3.8 QuantityC... | Asymmetric published quantity (the candidate publishes 3; the target is silent) with the verified review-constructed Q... | PRODUCT-INTEL.Q3C-C2.CORPUS-AUTHOR | PENDING | AUTHORED - review pending |
| FA4-PROV-010 | A7 | DERIVED / PROVEN_EQUIVALENT / AI_ASSISTE... | Q3-C-D1 matrix row A7; P3 section 3.8 CompletenessBasisV2FU4 (both bounded bases, each side's own source); P3 ten-case... | Independence shape (i): the target's attestation is the target's OWN published statement (PUBLISHED basis, recorded by... | PRODUCT-INTEL.Q3C-C2.CORPUS-AUTHOR | PENDING | AUTHORED - review pending |
| FA4-PROV-011 | A7 | DERIVED / PROVEN_EQUIVALENT / AI_ASSISTE... | Q3-C-D1 matrix row A7; P3 section 3.8 CompletenessBasisV2FU4 (both bounded bases, each side's own source); P3 ten-case... | Independence shape (ii): the target's attestation is the REVIEWED determination anchored to the manufacturer-published... | PRODUCT-INTEL.Q3C-C2.CORPUS-AUTHOR | PENDING | AUTHORED - review pending |
| FA4-PROV-012 | A8 | DERIVED / PROVEN_EQUIVALENT / AI_ASSISTE... | Q3-C-D1 matrix row A8; P5 section 4.2a record contract + section 9.1 row 1 (the positive control: the recorded snapsho... | RECORD-surface positive control: the complete R1 payload over the A1/A5 shape - the recorded derived section is the sn... | PRODUCT-INTEL.Q3C-C2.CORPUS-AUTHOR | PENDING | AUTHORED - review pending |
| FA4-PROV-013 | A8 | DERIVED / PROVEN_EQUIVALENT / AI_ASSISTE... | Q3-C-D1 matrix row A8; P5 section 4.2a record contract + section 9.1 row 1 (the positive control: the recorded snapsho... | RECORD-surface positive control: the complete R1 payload over the A1/A5 shape - the recorded derived section is the sn... | PRODUCT-INTEL.Q3C-C2.CORPUS-AUTHOR | PENDING | AUTHORED - review pending |
| FA4-UNPR-001 | B1 | DERIVED / UNPROVEN / NEEDS_REVIEW / - | Q3-C-D1 matrix row B1; P3 section 4 row 2 (count-only: corpus-shaped channel admitted, composition ABSENT) + U10; P3 t... | Count-only bundle: the corpus-shaped channel (OBSERVED BUNDLE quantity 3, raw_detail the count phrase - the admitted h... | PRODUCT-INTEL.Q3C-C2.CORPUS-AUTHOR | PENDING | AUTHORED - review pending |
| FA4-UNPR-002 | B1 | DERIVED / UNPROVEN / NEEDS_REVIEW / - | Q3-C-D1 matrix row B1; P3 section 4 row 2 (count-only: corpus-shaped channel admitted, composition ABSENT) + U10; P3 t... | RECORDED_FIXTURE variant: the candidate's sealed block cites the recorded OEMPCWorld PM9A3 page (the product's recorde... | PRODUCT-INTEL.Q3C-C2.CORPUS-AUTHOR | PENDING | AUTHORED - review pending |
| FA4-UNPR-003 | B2 | DERIVED / UNPROVEN / NEEDS_REVIEW / - | Q3-C-D1 matrix row B2; P3 U15 (Blocker B: textual agreement is not completeness); P3 section 3.8 (no attestation stand... | Missing completeness attestation on EITHER side (both clauses SYNTACTICALLY_VALID, byte-identical; neither side publis... | PRODUCT-INTEL.Q3C-C2.CORPUS-AUTHOR | PENDING | AUTHORED - review pending |
| FA4-UNPR-004 | B2 | DERIVED / UNPROVEN / NEEDS_REVIEW / - | Q3-C-D1 matrix row B2; P3 U15 (Blocker B: textual agreement is not completeness); P3 section 3.8 (no attestation stand... | Missing completeness attestation on EITHER side (both clauses SYNTACTICALLY_VALID, byte-identical; both sides publish ... | PRODUCT-INTEL.Q3C-C2.CORPUS-AUTHOR | PENDING | AUTHORED - review pending |
| FA4-UNPR-005 | B3 | DERIVED / UNPROVEN / NEEDS_REVIEW / - | Q3-C-D1 matrix row B3; P3 U15 (one side completeness-unknown never proves); P3 section 5.3 | Candidate complete (attested ESTABLISHED over the published marker), target incomplete (closed clause, no attestation ... | PRODUCT-INTEL.Q3C-C2.CORPUS-AUTHOR | PENDING | AUTHORED - review pending |
| FA4-UNPR-006 | B4 | DERIVED / UNPROVEN / NEEDS_REVIEW / - | Q3-C-D1 matrix row B4; P3 U15 (roles reversed); P3 section 5.3 | Target complete (attested ESTABLISHED, REVIEWED basis), candidate incomplete (closed clause, no published statement - ... | PRODUCT-INTEL.Q3C-C2.CORPUS-AUTHOR | PENDING | AUTHORED - review pending |
| FA4-UNPR-007 | B5 | DERIVED / UNPROVEN / NEEDS_REVIEW / - | Q3-C-D1 matrix row B5; P3 U11 / U14 (partial never proves and never contradicts by its own incompleteness); P3 section... | Partial constituent list: the candidate clause 'bundle: 2x RAM etc.' is PARTIAL (incompleteness marker / unclosed pare... | PRODUCT-INTEL.Q3C-C2.CORPUS-AUTHOR | PENDING | AUTHORED - review pending |
| FA4-UNPR-008 | B5 | DERIVED / UNPROVEN / NEEDS_REVIEW / - | Q3-C-D1 matrix row B5; P3 U11 / U14 (partial never proves and never contradicts by its own incompleteness); P3 section... | Partial constituent list: the candidate clause 'bundle (2x RAM + 1x C' is PARTIAL (incompleteness marker / unclosed pa... | PRODUCT-INTEL.Q3C-C2.CORPUS-AUTHOR | PENDING | AUTHORED - review pending |
| FA4-UNPR-009 | B5 | DERIVED / UNPROVEN / NEEDS_REVIEW / - | Q3-C-D1 matrix row B5; P3 U11 / U14 (partial never proves and never contradicts by its own incompleteness); P3 section... | Partial constituent list: the candidate clause 'bundle: 2x RAM +' is PARTIAL (incompleteness marker / unclosed paren /... | PRODUCT-INTEL.Q3C-C2.CORPUS-AUTHOR | PENDING | AUTHORED - review pending |
| FA4-UNPR-010 | B6 | DERIVED / UNPROVEN / NEEDS_REVIEW / - | Q3-C-D1 matrix row B6; P3 U12 / D8 (candidate self-contradiction fails closed to UNPROVEN - the CF-1 documented row: t... | Candidate self-contradiction (CF-1 documented row): the title's clause and the structured field's clause differ => the... | PRODUCT-INTEL.Q3C-C2.CORPUS-AUTHOR | PENDING | AUTHORED - review pending |
| FA4-UNPR-011 | B6 | DERIVED / UNPROVEN / NEEDS_REVIEW / - | Q3-C-D1 matrix row B6; P3 U12 / D8 (candidate self-contradiction fails closed to UNPROVEN - the CF-1 documented row: the frozen contract governs over the task matrix's CONTRADICTED placement); Q3-C-D1 section 4.4 (the allowed recorded-extraction-result state - the C2-F6 / Q3-C-D1-FU1 adjudication); P3 U0 / D8 (the frozen P2-to-FU4 chain over the recorded absence); P3 section 5.3 | (ii) extraction AMBIGUOUS_CUE (the count-only phrase 'bundle of 3' - the frozen P2 cue table records the BUNDLE_WITHOUT_CONTENTS ambiguous cue: a published count is never the complete identity of a bundle): the case carries the allowed recorded-extraction-result state - the candidate composition record is null, the candidate basis is NONE, the recorded extraction result is the GENUINE frozen P2 instantiation over the sealed candidate text (the committed examined-input document + the sealed self-verifying result), and the presented channel is EXACTLY the frozen P2 lossy mapping of that result (the canonical UNAVAILABLE over AMBIGUOUS_CUE); the expected U0 UNPROVEN is independently derived from the frozen P2-to-FU4 chain over the recorded absence - released by the recorded C2-F6 adjudication (the C1-FU3 loader correction) + the W7 cue-state accuracy (the evidence now carries the state the row requires) | PRODUCT-INTEL.Q3C-C2.CORPUS-AUTHOR | PENDING | CORRECTED (C2-F6 released) - review pending |
| FA4-UNPR-012 | B6 | DERIVED / UNPROVEN / NEEDS_REVIEW / - | Q3-C-D1 matrix row B6; P3 U12 / D8 (candidate self-contradiction fails closed to UNPROVEN - the CF-1 documented row: the frozen contract governs over the task matrix's CONTRADICTED placement); Q3-C-D1 section 4.4 (the allowed recorded-extraction-result state - the C2-F6 / Q3-C-D1-FU1 adjudication); P3 U0 / D8 (the frozen P2-to-FU4 chain over the recorded absence); P3 section 5.3 | (iii) extraction AMBIGUOUS_CUE (the bare word 'bundle' - the frozen P2 cue table records the BUNDLE_WITHOUT_CONTENTS ambiguous cue: a bare bundle word is never an established unit): the case carries the allowed recorded-extraction-result state - the candidate composition record is null, the candidate basis is NONE, the recorded extraction result is the GENUINE frozen P2 instantiation over the sealed candidate text (the committed examined-input document + the sealed self-verifying result), and the presented channel is EXACTLY the frozen P2 lossy mapping of that result (the canonical UNAVAILABLE over AMBIGUOUS_CUE); the expected U0 UNPROVEN is independently derived from the frozen P2-to-FU4 chain over the recorded absence - released by the recorded C2-F6 adjudication (the C1-FU3 loader correction) + the W7 cue-state accuracy (the evidence now carries the state the row requires) | PRODUCT-INTEL.Q3C-C2.CORPUS-AUTHOR | PENDING | CORRECTED (C2-F6 released) - review pending |
| FA4-UNPR-013 | B7 | DERIVED / UNPROVEN / NEEDS_REVIEW / - | Q3-C-D1 matrix row B7; P3 U18 (Blocker A: the asymmetric unattested quantity is UNDETERMINED, never silently immateria... | Missing published quantity (Blocker A defect row, role direction 1): the candidate publishes count 3 over the attested... | PRODUCT-INTEL.Q3C-C2.CORPUS-AUTHOR | PENDING | AUTHORED - review pending |
| FA4-UNPR-014 | B7 | DERIVED / UNPROVEN / NEEDS_REVIEW / - | Q3-C-D1 matrix row B7; P3 U18 (Blocker A: the asymmetric unattested quantity is UNDETERMINED, never silently immateria... | Missing published quantity (role direction 2): the target publishes count 3, the candidate is silent, NO quantity atte... | PRODUCT-INTEL.Q3C-C2.CORPUS-AUTHOR | PENDING | AUTHORED - review pending |
| FA4-UNPR-015 | B8 | REFUSED / - / - / CONSTRUCTION/CONSTRUCT... | Q3-C-D1 matrix row B8; P3 section 3.2 / 3.8 (the bounded source vocabulary per side: a composition-surface source outs... | Insufficient provenance (i): the sealed candidate record carries source 'SPECIFICATION_TEXT' - a frozen enum member NO... | PRODUCT-INTEL.Q3C-C2.CORPUS-AUTHOR | PENDING | AUTHORED - review pending |
| FA4-UNPR-016 | B6 | DERIVED / UNPROVEN / NEEDS_REVIEW / - | Q3-C-D1 matrix row B6; P3 U12 / D8 (candidate self-contradiction fails closed to UNPROVEN - the CF-1 documented row: t... | Second conflicting-fields variant (the TB-5 pair): title '2x SSD + 1x cable' vs structured '2x RAM + 1x CPU' => CONTRA... | PRODUCT-INTEL.Q3C-C2.CORPUS-AUTHOR | PENDING | AUTHORED - review pending |
| FA4-UNPR-017 | B9 | REFUSED / - / - / CONSTRUCTION/CONSTRUCT... | Q3-C-D1 matrix row B9; P3 Revision record 3 (the v3 embedded original is mandatory for the EXTRACTION basis; its own i... | Unverifiable original extraction evidence (i): the EXTRACTION-basis record's embedded original result is MISSING (the ... | PRODUCT-INTEL.Q3C-C2.CORPUS-AUTHOR | PENDING | AUTHORED - review pending |
| FA4-UNPR-018 | B9 | REFUSED / - / - / CONSTRUCTION/CONSTRUCT... | Q3-C-D1 matrix row B9; P3 Revision record 3 (the v3 embedded original is mandatory for the EXTRACTION basis; its own i... | Unverifiable original extraction evidence (ii): the embedded result's cue text is tampered OUT-OF-BAND and the result'... | PRODUCT-INTEL.Q3C-C2.CORPUS-AUTHOR | PENDING | AUTHORED - review pending |
| FA4-UNPR-019 | B10 | DERIVED / UNPROVEN / NEEDS_REVIEW / - | Q3-C-D1 matrix row B10; invariant I-1 (a correct semantic MATCH is never sufficient proof of bundle equivalence - Q3-C... | I-1 headline row (i): scripted MATCH+HIGH+STRONG+clean over unattested equal clauses (the B2 shape): the semantic deci... | PRODUCT-INTEL.Q3C-C2.CORPUS-AUTHOR | PENDING | AUTHORED - review pending |
| FA4-UNPR-020 | B10 | DERIVED / UNPROVEN / NEEDS_REVIEW / - | Q3-C-D1 matrix row B10; invariant I-1 (a correct semantic MATCH is never sufficient proof of bundle equivalence - Q3-C... | I-1 headline row (ii): scripted MATCH+HIGH+STRONG+clean over a count-only bundle (the B1 shape): equal counts without ... | PRODUCT-INTEL.Q3C-C2.CORPUS-AUTHOR | PENDING | AUTHORED - review pending |
| FA4-UNPR-021 | B10 | DERIVED / UNPROVEN / NEEDS_REVIEW / - | Q3-C-D1 matrix row B10; invariant I-1 (a correct semantic MATCH is never sufficient proof of bundle equivalence - Q3-C... | I-1 headline row (iii): scripted MATCH+HIGH+STRONG+clean over a channel UNAVAILABLE with the model's BUNDLE claim reco... | PRODUCT-INTEL.Q3C-C2.CORPUS-AUTHOR | PENDING | AUTHORED - review pending |
| FA4-UNPR-022 | B11 | DERIVED / UNPROVEN / NEEDS_REVIEW / - | Q3-C-D1 matrix row B11; P3 section 3.5b + T9 (only the versioned marker list detects completeness; unlisted phrasing s... | Unlisted completeness phrasing: the closed clause ends 'as listed' - a localized phrasing NOT in the versioned complet... | PRODUCT-INTEL.Q3C-C2.CORPUS-AUTHOR | PENDING | AUTHORED - review pending |
| FA4-UNPR-023 | B12 | DERIVED / UNPROVEN / NEEDS_REVIEW / - | Q3-C-D1 matrix row B12; P3 section 5 'never an input, never inferred' (no composition is inferred from a model claim);... | Constituent claims recorded in the scripted evaluation detail only: the scripted evaluation detail names constituents ... | PRODUCT-INTEL.Q3C-C2.CORPUS-AUTHOR | PENDING | AUTHORED - review pending |
| FA4-UNPR-024 | B6 | DERIVED / UNPROVEN / NEEDS_REVIEW / - | Q3-C-D1 matrix row TB-3 (the Track B population over the B6 row); the frozen 2.1 COMMERCIAL SALES-UNIT RULES (count-on... | The TB-3 model control over the B6 row's bare-bundle shape: the sealed published text carries only the word 'bundle'; ... | PRODUCT-INTEL.Q3C-C2.CORPUS-AUTHOR | PENDING | AUTHORED - review pending |
| FA4-UNPR-025 | B5 | DERIVED / UNPROVEN / NEEDS_REVIEW / - | Q3-C-D1 matrix row TB-4 (the Track B population over the B5 row); the frozen 2.1 COMMERCIAL SALES-UNIT RULES (partial ... | The TB-4 model control over the B5 row's dangling marker variant: the candidate clause is PARTIAL (dangling separator ... | PRODUCT-INTEL.Q3C-C2.CORPUS-AUTHOR | PENDING | AUTHORED - review pending |
| FA4-UNPR-026 | B8 | REFUSED / - / - / CONSTRUCTION/CONSTRUCT... | Q3-C-D1 matrix row B8; P3 section 3.2 / 3.8 (the bounded source vocabulary per side: a composition-surface source outs... | Insufficient provenance (ii): the sealed target record carries source 'PUBLISHED_STRUCTURED_FIELD' - a CANDIDATE-side ... | PRODUCT-INTEL.Q3C-C2.CORPUS-AUTHOR | PENDING | AUTHORED - review pending |

## 7. The reviewer / tester work

The complete, per-case worklist for the independent label reviewer and
the independent tester is in `reviewer_handoff.md`. Nothing in this
log is a review; every status above is the AUTHOR's record only.
