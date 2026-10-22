# C2 Reviewer / Tester Handoff (FU4 Bundle Authority Qualification v1.0.0)

**To:** the genuinely distinct independent label reviewer (design
section 8.1) and the independent tester (design section 8.1 / 7.6).
**From:** the corpus author of record (`PRODUCT-INTEL.Q3C-C2.CORPUS-
AUTHOR`, the single authoring pass of 2026-10-15T23:22:50Z).
**Status:** the authoring pass is complete (and the corrected
population of record is in place under the recorded Q3-C-D1-FU1
adjudication + the bounded C1-FU3 + C2 corrective implementation -
design section 9.11); the independent review has NOT occurred.
Nothing in the committed family is a review record.

## 0. What you are being asked to do (and not do)

1. **Re-derive the expected outcome of every case independently** from
   the case's `label.grounding_citation` + the sealed source evidence
   (design section 8.2 step 2) - re-reading the cited P3 / Q3-B4 /
   Q3-C-D1 / R1 rows, NOT the author's rationale as authority.
2. **Challenge the label** where your re-derivation differs; record
   the challenge + resolution in `challenge_log.md` (section 6) under
   your own identity + instant (design section 8.2 step 4).
   Disagreement resolves by citation to the higher-authority row -
   the frozen contract wins over both readings (section 8.2 step 3);
   a genuine contract conflict is a FINDING, never a split-the-
   difference label.
3. **Verify the recorded C2-F adjudications** (challenge log
   sections 4 / 6): the ten HELD findings were adjudicated case-by-
   case by the independent C2-F1 adjudication of record (the Q3-C-D1-
   FU1 revision record, endpoint SHA `34ca5edf056c68c1719ed470e832e9f956626c19`;
   ratified at the Q3-C-D1-FU2 design gate, endpoint SHA
   `4f53538f34c588c6f2b5e66a237f40acae2b5995`) and executed under the
   bounded C1-FU3 + C2 corrective implementation (design section
   9.11). For each of the eight corrected rows (section 4 below) you
   verify that the correction is the faithful reading of the cited
   frozen contract; where your independent reading differs, record a
   CHALLENGE + resolution under section 4.6 item 5 governance (the
   frozen contract wins over both readings - a genuine contract
   conflict is a FINDING, never a split-the-difference label).
4. **Tester scope (section 3 below):** re-derive at least 20% of the
   population including ALL adversarial D rows (36/94 = 38.3% >=
   20%; the removed FA4-ADV-034 third D16 obligation is the MANDATORY
   E1 adversarial-execution assertion - design section 9.6, NOT a
   corpus re-derivation), inspect every G1-adjacent false-PROVEN path
   (the A rows + D1/D5/D7 shapes), verify the missing-evidence rows
   stay UNPROVEN (the `attestation_missing` tagged population - M10),
   and review every changed / deleted test at acceptance (the node-
   level collection diff, the 0/0/0 skip invariant, the flake-
   allowlist non-expansion).
5. **Do NOT** use the FU4 implementation, the R1 record adapter, or
   any model as the expected-label oracle (section 4.6 item 2). The
   implementation may be READ as the frozen contract of record (it is
   the C0-pinned surface the labels cite); its OUTPUT may not be read
   as the answer.
6. **Do NOT** seal before every case (all 94) carries your re-
   derivation record (section 5 below is the exact seal procedure).

## 1. The population (where to look)

* The case documents: `product_intelligence/evaluation/bundle_authority/
  fixtures.py` - `CASES` (94 draft case documents - the corrected
  v1.0.0 DRAFT population of record: the C2 endpoint's 96 cases minus
  the removed FA4-ADV-034 (E1-only) and FA4-PROV-002 (C3 / 1.1.0),
  with the eight corrected rows in place; the exact 16-key shape
  minus `case_digest`; every label in the DRAFT state).
* The author pass + findings: `evaluation/fu4_bundle_authority_qualification/
  challenge_log.md` (section 3 table: per-case grounding citation +
  author re-derivation; section 4: the C2-F findings; section 6: the
  agreements / disagreements / corrections log).
* The C2 governance suite (the mechanical gates you are completing):
  `tests/evaluation/bundle_authority/test_q3c_c2_label_governance.py`.
* The matrix of record: `docs/PRODUCT_INTEL_Q3C_FU4_BUNDLE_AUTHORITY_
  QUALIFICATION_DESIGN.md` sections 5.1-5.6 (the rows) + 4.4-4.6
  (the case document + label contract) + 8 (this workflow).

## 2. Per-case review worklist (the 94 corrected-population cases)

For each case ID below: open the case in `fixtures.py`, read the
`label.grounding_citation`, re-derive the `expected` block from the
cited rows over the sealed `source` / `derivation_inputs` /
`recorded_case` documents, compare to the recorded expectation, and
record your verdict (AGREE / CHALLENGE + resolution) under your
identity + instant. The mechanical pre-checks (the loader over your
review-filled copy - section 5) must pass for every case you sign.

The 86 review-ready case IDs (all 48 matrix rows at their minimums;
the row is named per case):

FA4-PROV-001 (A1) | FA4-PROV-003 (A2) | FA4-PROV-004 (A2)
FA4-PROV-005 (A3) | FA4-PROV-006 (A4) | FA4-PROV-007 (A5)
FA4-PROV-008 (A5) | FA4-PROV-009 (A6) | FA4-PROV-010 (A7)
FA4-PROV-011 (A7) | FA4-PROV-012 (A8) | FA4-PROV-013 (A8)
FA4-DELE-001 (A-DELE) [CORRECTED-VERIFY]
FA4-DELE-002 (A-DELE) [CORRECTED-VERIFY]
FA4-DELE-003 (A-DELE) [CORRECTED-VERIFY] | FA4-DELE-004 (A-DELE)
FA4-UNPR-001 (B1) | FA4-UNPR-002 (B1) | FA4-UNPR-003 (B2)
FA4-UNPR-004 (B2) | FA4-UNPR-005 (B3) | FA4-UNPR-006 (B4)
FA4-UNPR-007 (B5) | FA4-UNPR-008 (B5) | FA4-UNPR-009 (B5)
FA4-UNPR-025 (B5) | FA4-UNPR-010 (B6)
FA4-UNPR-011 (B6) [CORRECTED-VERIFY]
FA4-UNPR-012 (B6) [CORRECTED-VERIFY] | FA4-UNPR-016 (B6)
FA4-UNPR-024 (B6) | FA4-UNPR-013 (B7) | FA4-UNPR-014 (B7)
FA4-UNPR-015 (B8) | FA4-UNPR-026 (B8) | FA4-UNPR-017 (B9)
FA4-UNPR-018 (B9) | FA4-UNPR-019 (B10) | FA4-UNPR-020 (B10)
FA4-UNPR-021 (B10) | FA4-UNPR-022 (B11) | FA4-UNPR-023 (B12)
FA4-DELE-005 (B-DELE) | FA4-DELE-006 (B-DELE)
FA4-DELE-007 (B-DELE) | FA4-CONTR-001 (C1) | FA4-CONTR-002 (C1)
FA4-CONTR-003 (C2) | FA4-CONTR-004 (C2b) | FA4-CONTR-005 (C3)
FA4-CONTR-006 (C3) | FA4-CONTR-007 (C4) | FA4-CONTR-008 (C4)
FA4-CONTR-009 (C4) | FA4-CONTR-010 (C5)
FA4-CONTR-011 (C6) [CORRECTED-VERIFY] | FA4-CONTR-012 (C7)
FA4-CONTR-013 (C7) | FA4-ADV-001 (D1) | FA4-ADV-002 (D1)
FA4-ADV-003 (D1) | FA4-ADV-004 (D2) | FA4-ADV-005 (D3)
FA4-ADV-006 (D3) [CORRECTED-VERIFY] | FA4-ADV-007 (D3)
FA4-ADV-008 (D4) | FA4-ADV-009 (D4) | FA4-ADV-010 (D5)
FA4-ADV-011 (D5) | FA4-ADV-012 (D6) [CORRECTED-VERIFY] | FA4-ADV-013 (D6)
FA4-ADV-014 (D7) | FA4-ADV-015 (D7) | FA4-ADV-016 (D8)
FA4-ADV-017 (D8) | FA4-ADV-018 (D9) | FA4-ADV-019 (D9)
FA4-ADV-020 (D10) | FA4-ADV-021 (D10) | FA4-ADV-022 (D11) [CORRECTED-VERIFY]
FA4-ADV-023 (D11) [CORRECTED-VERIFY] | FA4-ADV-024 (D12)
FA4-ADV-025 (D13) | FA4-ADV-026 (D13) | FA4-ADV-027 (D14)
FA4-ADV-028 (D14) | FA4-ADV-029 (D14) | FA4-ADV-030 (D15)
FA4-ADV-031 (D15) | FA4-ADV-032 (D16) | FA4-ADV-033 (D16)
FA4-ADV-035 (D17) | FA4-ADV-036 (D17) | FA4-ADV-037 (D18)

(All 94 cases are review-ready at the corrected endpoint: the seven loader-held cases are released under the recorded adjudication - three by the C1-FU3 validator correction with byte-unchanged labels, one by the D3-ii re-label + record-twin removal, one by the D11-ii SYNTHETIC re-authoring, and two removed from the declared population with their obligation destinations - and the three C2-F6 evidence-gap cases now carry the GENUINE recorded extraction results (the allowed NONE-basis recorded-result state); the ten corrected rows are flagged CORRECTED-VERIFY above - the eight of the recorded adjudication + FA4-ADV-012 / FA4-ADV-022 of the F-R6 / F-R2 pre-seal corrections (FA4-ADV-023's flag is shared with its C2-F5 correction).)
## 3. Tester minimum (design section 7.6 + the C2 directive)

Re-derive, independently of the reviewer pass: (a) ALL 36 adversarial
D cases (FA4-ADV-001..037 minus the removed FA4-ADV-034 - the D16-iii
third obligation is the MANDATORY E1 adversarial-execution assertion,
design section 9.6, not a corpus re-derivation; for the corrected
FA4-ADV-006 / 023 you verify the corrections under section 4); (b) the false-
PROVEN-adjacent shapes (FA4-PROV-001..013, FA4-ADV-001..003, FA4-
ADV-010..011, FA4-ADV-014..015, FA4-ADV-035..036); (c) the
`attestation_missing` tagged population (FA4-UNPR-003..006, FA4-
UNPR-013..014, FA4-UNPR-022, FA4-ADV-037); (d) the
`historical_binding_confusion` tagged population (FA4-UNPR-001, FA4-
ADV-032, FA4-ADV-033); (e) the `cross_listing_substitution` tagged population
(FA4-ADV-004..005, FA4-ADV-007, FA4-ADV-010, FA4-ADV-012). Together
this is >= 20% of the 94-case population with all D rows included (the
removed FA4-ADV-034 obligation moves to the E1 mandatory adversarial-
execution assertion - design section 9.6).
Record: case IDs, your governing citations, your independently
derived labels, disagreements + resolutions (challenge log section 6,
under your identity).

## 4. The C2-F findings - the recorded adjudications + your
verification worklist (challenge log sections 4 / 6)

The ten findings were ADJUDICATED (independent C2-F1 adjudication of
record - the Q3-C-D1-FU1 revision record, endpoint SHA
`34ca5edf056c68c1719ed470e832e9f956626c19`, 2026-10-16T02:44:50Z;
ratified at the Q3-C-D1-FU2 design gate, endpoint SHA
`4f53538f34c588c6f2b5e66a237f40acae2b5995`, 2026-10-16T17:36:55Z) and
EXECUTED under the bounded C1-FU3 + C2 corrective implementation
(design section 9.11). Your work per finding - verify the correction
is the faithful reading of the cited frozen contract (re-reading the
citation, not the correction's prose); a disagreement is a CHALLENGE
under section 4.6 item 5 governance (the frozen contract wins over
both readings):

* **C2-F1** (FA4-DELE-001, FA4-DELE-002, FA4-DELE-003 - the non-
  bundle PROVEN rows): adjudicated - the design section 4.4
  coherence rule is scoped to Bundle-channel cases (the C1-FU3
  loader correction); the non-Bundle PROVEN expectations retain the
  frozen P3 D11 exactly-null Bundle-axis semantics; the byte-
  identical delegation (P3 D9) is preserved. VERIFY: the three
  labels are the frozen non-bundle shapes (byte-unchanged by the
  correction) and the cases load under the corrected loader.
* **C2-F2a** (FA4-ADV-006): adjudicated - the D3-ii stage is
  CORPUS_INTEGRITY (the record's embedded original != the case's
  recorded extraction evidence is observable ONLY by the family
  loader; the P5 R-5 channel-granularity bound prevents the
  presentation gate from detecting the substitution) and the surface
  is DERIVATION (the self-consistent record twin decodes and replays
  cleanly - no record twin). VERIFY: the re-labeled case
  (CORPUS_INTEGRITY / error_type null / DERIVATION / NOT_APPLICABLE,
  no payload) is coherent over the sealed documents; the separate
  D3-i PRESENTATION_GATE case (FA4-ADV-005) is preserved.
* **C2-F2b** (FA4-ADV-034): adjudicated - the FU3-token contract-
  misuse refusal is an EXECUTION-level observation point only (over
  the sealed sound FU4 documents no constructor / codec / case-
  document observation fires); REMOVED from the v1.0.0 declared
  population (case ID retired; v1.0.0 D16 minimum recorded as 2 -
  the explicit phase-boundary correction). VERIFY: the removal +
  the MANDATORY E1 adversarial-execution assertion destination
  (design section 9.6; the M13 / G6 coverage note) are recorded;
  the frozen FU3 / FU4 token boundary is NOT weakened.
* **C2-F3** (FA4-PROV-002): adjudicated - no committed recorded
  source publishes the required complete Bundle composition
  (design section 2.5; the span-grounding refusal is the second
  boundary past the identity-context defect); REMOVED from the
  v1.0.0 declared population (case ID retired; v1.0.0 A1 minimum
  recorded as 1 - the explicit phase-boundary correction). VERIFY:
  the removal + the C3 / additive 1.1.0 obligation destination
  (P3 D19 independently evidenced publisher completeness preserved)
  are recorded.
* **C2-F5** (FA4-ADV-023): adjudicated - the recorded identifier-
  family evidence (the one-character-different Micron 7500 part
  numbers) is separated from the by-construction Bundle composition
  evidence; the hybrid variant cannot be represented truthfully by
  the existing schema (the span-grounding provenance rule + the
  row's U1 EXACT identity context - the recorded context is
  U4_NO_MPN); re-authored SYNTHETIC with the row's exact U1 EXACT
  identity context (U1_TITLE_MPN, equal non-empty normalized part
  numbers, TITLE_MPN_TOKEN, NOT_REQUIRED - W8). VERIFY: the
  re-authored case carries by-construction attested compositions
  over the U1 EXACT context (materially different clauses), the
  Micron catalog is documented as identifier-shape CONTEXT only
  (cited by path + digest - NOT claimed to publish Bundle
  compositions), and the D11 2-case adversarial coverage is
  retained (FA4-ADV-022 + FA4-ADV-023).
* **C2-F6** (FA4-UNPR-011, FA4-UNPR-012, FA4-CONTR-011): adjudicated
  - the allowed state (candidate composition record null, basis
  NONE, the recorded extraction result present, the presented
  channel EXACTLY the frozen P2 mapping of that result, the
  expected authority independently derived from the frozen
  contract); the C1-FU3 loader correction admits the state + the
  named `CASEDOC_RECORDED_RESULT_CHANNEL_MAPPING` refusal; W7 -
  FA4-CONTR-011's sealed text is corrected so that the recorded
  result carries the genuine CONTRADICTED_CUES state (the title's
  established bundle-with-contents clause vs the structured
  pack-of-N field). VERIFY: each case's recorded result is the
  genuine frozen P2 instantiation over its sealed text (the cue
  table + the lossy mapping), the presented channel is exactly the
  frozen mapping (the canonical UNAVAILABLE), and the expectations
  are the unchanged U0 UNPROVEN frozen-chain readings.

## 4.1 The pre-seal corrections of record (Q3-C-C2-R1-FU1) - your
re-verification worklist

The independent C2-R1 label review of record (reviewer identity
`Q3-C-C2-R1.INDEPENDENT-LABEL-REVIEWER`; the untracked session
review ledger over HEAD
`b85261924bc4827636ae3c3f54b01c7674d697b4`) resolved 92 of the 94
cases AGREE (9 with recorded non-label notes) and opened THREE
pre-seal blockers. They were corrected pre-seal under the section
4.6 item 5 governance (class A where the expectation was
factually wrong over the frozen contract; no URL invented; the
frozen derivation / grammar NOT changed to match the authored
labels) by the corrective implementer of record (PRODUCT-INTEL.
Q3C-C2-R1-FU1.CORRECTIVE-IMPLEMENTER, correction instant
2026-10-17T00:35:42Z), and each correction is pinned by a NEW
regression node in the C2 governance suite (the pre-correction
value fails the pin). **The corrections remain OPEN for your
re-verification: they are the corrective implementer's record
only, and the challenges / finding are NOT marked independently
resolved on the reviewer's behalf.** Your work per correction -
verify the correction is the faithful reading of the cited frozen
contract (re-reading the citation over the sealed bytes, not the
correction's prose) and record your verdict under section 4.6
item 5 governance in challenge log section 6 under your identity
+ instant:

* **CH-1 (MAJOR - FA4-ADV-024 / D12).** Corrected: expected.tier
  EXCLUDED_LOW_CONFIDENCE -> HARD_CONFLICT (all other expected
  fields preserved). VERIFY over the sealed scripted context +
  the frozen S2-A contract data: the matrix base over NO_MATCH +
  HIGH + STRONG is EXCLUDED_LOW_CONFIDENCE; the scripted conflict
  class CAPACITY is a frozen ALWAYS_HARD_CONFLICT_CLASSES member;
  the frozen hard-conflict supersession (always last inside the AI
  path) sets HARD_CONFLICT (fired rule HARD_CONFLICT_SUPERSEDES -
  the case's own sealed payload derived section records exactly
  that). Where your independent reading differs, record a
  CHALLENGE + resolution (the frozen contract wins over both
  readings).
* **CH-2 (LOW - FA4-UNPR-022 / B11).** Corrected: expected.
  textual_relation T-DIFF-UNESTABLISHED -> T-DIFF-MATERIAL + the
  rationale sentence (the UNPROVEN unit + its governing missing-
  completeness rationale preserved). VERIFY over the sealed clause
  bytes + the frozen P3 versioned grammar: the candidate clause
  '2x RAM + 1x CPU, as listed' FULLY parses ('as listed' is a
  valid item token - the same class as the worked-example 'power
  cables'), as does the target clause '2x RAM + 1x CPU', the
  canonical multisets DIFFER ((2,'ram'),(1,'cpu'),(1,'as listed')
  vs (2,'ram'),(1,'cpu')) - the frozen axis over two fully-parsed
  clauses is T-DIFF-MATERIAL; and the unit stays UNPROVEN (U15 -
  the candidate is completeness-unknown; a material difference
  never contradicts over a completeness-unknown clause - the D7
  safe direction). If the frozen grammar does NOT support that
  parse, record the contract conflict - do not force the
  corrected label.
* **F-R1 (MEDIUM - FA4-DELE-005 / B-DELE, provenance).**
  Corrected: source_url
  https://www.directd.com/product/BCM957608-P2200GQF00 ->
  https://directmacro.com/catalogsearch/result/?q=BCM957608-
  P2200GQF00 at the three sealed locations (source.candidate /
  source.target / the recorded V2 case's candidate) - no label
  field moved. VERIFY over the committed recording evidence: the
  cited archive's own 4D-PRE evidence line records exactly the
  corrected URL; the original 4D-A acquisition record pins the
  DirectMacro locator target for the MPN as that URL (and forbids
  a fabricated product slug); the declared archive digest verifies
  over the committed file; the C1 provenance-binding invariant
  (recorded V2 case <-> sealed candidate block, exact equality)
  stands; and the pre-correction URL is unsupported by any
  archive or 3A / 4D-A recording (it appeared only in an
  unvalidated P2 test constant). If no trustworthy URL can be
  established from the recording evidence, record the unresolved
  provenance gap - do not accept an invented URL.

The review's remaining non-label findings (F-R3 / F-R4 / F-R5 /
F-R7 / F-R8, as recorded in the untracked ledger) stand for the
seal gate / E1 / this tester worklist unchanged (they are handed
to the independent tester as additional re-derivation targets, with
all 36 D rows in tester scope by definition); F-R2 was corrected
pre-seal at the Q3-C-C1-FU4 + C2-FU2 endpoint (section 4.2 below -
your re-verification is required). The reviewer column of the
challenge log for the three corrected rows remains PENDING until
your re-verification is recorded.

## 4.2 The F-R6 + F-R2 corrections of record (Q3-C-C1-FU4 +
C2-FU2) - your re-verification worklist

The F-R6 BLOCKER of the independent Q3-C-C2-T1 adversarial tester
record of record (the untracked
`tmp_q3c_c2t1_fr6_investigation.md` + the tester ledger, over HEAD
`b85261924bc4827636ae3c3f54b01c7674d697b4`) was ADJUDICATED by the
approved Q3-C-D1-FU3 design revision of record (the revision
record of `docs/PRODUCT_INTEL_Q3C_FU4_BUNDLE_AUTHORITY_QUALIFICATION_`
`DESIGN.md`: Option B - the D6-i stage re-attribution per the
C2-F2a precedent; the F-R2 documentary finding verified at the
revision) + the Q3-C-D1-FU3-FU1 two-contract correction (Contract
A: the strict load ACCEPTS the correctly labeled sealed-raw case
after verifying the stage against its internally collected
observations; Contract B: the family-owned read-only observation
interface returns the exact named observation at the exact layer;
a record with no corpus-surface observation is the explicit
bypass-to-G4 failure). The corrections were executed pre-seal
under the section 4.6 item 5 governance by the corrective
implementer of record (PRODUCT-INTEL.Q3C-C1-FU4.CORRECTIVE-
IMPLEMENTER, correction instant 2026-10-20T02:00:02Z, the bounded
C1-FU4 + C2-FU2 corrective implementation of design section 9.12),
and each correction is pinned by a NEW regression node in the C2
governance suite (the pre-correction value fails the pin). **The
corrections remain OPEN for your re-verification: they are the
corrective implementer's record only, and the finding is NOT
marked independently resolved on the reviewer's behalf.** Your
work per correction - verify the correction is the faithful
reading of the cited design adjudication over the sealed bytes
(re-reading the citation, not the correction's prose) and record
your verdict under section 4.6 item 5 governance in challenge log
section 6 (rows 23 / 24) under your identity + instant:

* **F-R6 (BLOCKER - FA4-ADV-012 / D6-i).** Corrected:
  expected.refusal.stage CONSTRUCTION -> CORPUS_INTEGRITY +
  expected.refusal.error_type CONSTRUCTOR -> null (PRESERVED,
  byte-unchanged: expected.outcome REFUSED, expected.replay
  NOT_APPLICABLE, every other expected field, the case ID, matrix
  row D6, track A, the DERIVATION surface, every sealed evidence
  document, the label author, reviewer null, review_status DRAFT).
  VERIFY over the sealed FA4-ADV-012 documents + the approved
  Q3-C-D1-FU3 revision record: (1) every sealed document decodes
  through the REAL frozen constructors with zero constructor
  errors (the v2 case, the channel, the v3 candidate record - its
  anchors equal the embedded result's own digests; the embedded
  result's self-digests + cue spans verify over its own recorded
  field text - the ALTERED title); the frozen presentation gate's
  four steps ALL pass; (2) the inconsistency is BETWEEN the case's
  separately sealed documents (the recorded extraction input
  document's canonical digest != the result's input_digest -
  plain-hash verifyable over the sealed bytes); (3) no frozen
  constructor / codec / gate step / derivation signature / replay
  path EVER receives the case's recorded input document (the P2
  result's input_digest is a stored binding the frozen code never
  recomputes against an external document; the frozen derivation
  COMPLETES over the reconstructed self-consistent typed inputs -
  the documented non-observation, never a satisfaction); (4)
  therefore the family loader's named cross-document observation
  SOURCE_EXTRACTION_INPUT_DIGEST (the corrected family loader's
  CASE_DOCUMENT-layer observation - the Contract B interface
  `observe_corpus_case_integrity` returns it at that layer with
  the bounded reason, and `observation_stages` over the record +
  the sealed surface is {CORPUS_INTEGRITY}) is the first and only
  non-corroborative observation point - the stage-semantics (iv)
  class, the C2-F2a precedent; (5) the existing stage-coherence
  rule now ACCEPTS the CORPUS_INTEGRITY / null label (Contract A -
  the case LOADS under the review fill) and REJECTS the obsolete
  CONSTRUCTION / CONSTRUCTOR attribution (the pinned incoherent-
  label reason). Where your independent reading differs, record a
  CHALLENGE + resolution (the frozen contract wins over both
  readings - the F-R6 adjudication moves NO frozen contract: the
  frozen layers' silence over this shape is the evidence, not the
  defect).
* **F-R2 (documentary - FA4-ADV-022 / FA4-ADV-023 / D11).**
  Corrected: the two D11 grounding citations now carry the
  VERIFIED catalog digest
  `160d4fe97a5df5249e8f6404f6b005c0515fab4def1b4668fdaf87c727600743`
  (the pre-correction citations named
  tests/fixtures/pages/micron_7500_part_catalog.json by path only
  while the adjudication record claims "cited by path + digest")
  - a class-A annotation correction: NO expected field moves, NO
  evidence-classification move (both cases stay DERIVED /
  CONTRADICTED / NEEDS_REVIEW over their sealed documents; the
  catalog is identifier-shape CONTEXT only). VERIFY: recompute the
  SHA-256 over the current working-tree bytes of
  tests/fixtures/pages/micron_7500_part_catalog.json (24,060
  bytes) and confirm it equals the cited digest (the NEW C2 node
  recomputes it at test time - a catalog move or a path-only
  citation trips the pin); confirm the catalog publishes
  identifiers only (zero `bundle` occurrences - the C2-F5
  statement); confirm the catalog file is otherwise UNCHANGED.
  FA4-ADV-023 joins its existing C2-F5 re-verification (its [COR-
  RECTED-VERIFY] flag is shared with both corrections).

The reviewer column of the challenge log for the three corrected
rows (FA4-ADV-012 / FA4-ADV-022 / FA4-ADV-023) remains PENDING
until your re-verification is recorded under your identity +
instant.

## 5. The seal procedure (exactly, when the review is complete)

1. In `fixtures.py`, for every case you signed: set
   `label.reviewer` = your recorded identity, `label.reviewer_utc` =
   your recorded instant, `label.review_status` = `"REVIEWED"`. The
   eight corrected rows (section 4) are verified in place - the
   corrections are pre-seal population corrections of record (no
   seal-time label move is required); the two removed cases
   (FA4-ADV-034 / FA4-PROV-002) stay OUT of the sealed population
   with their recorded obligation destinations (the MANDATORY E1
   adversarial-execution assertion; the C3 / 1.1.0 additive
   obligation).
2. Record every challenge / agreement / correction in
   `challenge_log.md` section 6 under your identity + instant
   (agreements included - the log is complete or it is not the audit
   surface).
3. Re-run the authoring dry-run (every case - all 94 - must load
   under the family loader with your review fields; the C2 suite's
   review-ready node does exactly this).
4. Seal: `corpus_v1.json` + `manifest_v1.json` =
   `build_corpus_document(<the sealing instant of record>, CASES)` +
   `build_manifest_document` in the canonical serialization, committed
   to `evaluation/fu4_bundle_authority_qualification/`; the per-case /
   corpus / manifest digests are the record. The committed
   `fixtures.py` must regenerate the seal byte-for-byte (the C2 suite
   pins this at the sealed endpoint).
5. Record the seal (STATUS + this directory's README state section)
   as the C2 endpoint - the first endpoint at which a qualification
   claim may be computed (and even then: at most POLICY_PENDING over
   the DRAFT family policy, the section 7.5 ladder).

## 6. What this handoff is NOT

Not a review. Not an approval. Not a claim that any case is
independently qualified. The author's pass is recorded in the
challenge log; YOUR pass does not exist yet - that is precisely the
gate this handoff unlocks.
