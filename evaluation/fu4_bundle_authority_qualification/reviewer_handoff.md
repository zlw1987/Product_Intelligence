# C2 Reviewer / Tester Handoff (FU4 Bundle Authority Qualification v1.0.0)

**To:** the genuinely distinct independent label reviewer (design
section 8.1) and the independent tester (design section 8.1 / 7.6).
**From:** the corpus author of record (`PRODUCT-INTEL.Q3C-C2.CORPUS-
AUTHOR`, the single authoring pass of 2026-10-15T23:22:50Z).
**Status:** the authoring pass is complete; the independent review has
NOT occurred. Nothing in the committed family is a review record.

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
3. **Adjudicate the C2-F findings** (challenge log section 4): for
   each held case, either (a) ratify the held label + the named
   resolution (design revision / schema correction), or (b) record a
   different higher-authority reading and move the label under
   section 4.6 item 5 governance.
4. **Tester scope (section 3 below):** re-derive at least 20% of the
   population including ALL adversarial D rows (37/96 = 38.5% >= 20%),
   inspect every G1-adjacent false-PROVEN path (the A rows + D1/D5/D7
   shapes), verify the missing-evidence rows stay UNPROVEN (the
   `attestation_missing` tagged population - M10), and review every
   changed / deleted test at acceptance (the node-level collection
   diff, the 0/0/0 skip invariant, the flake-allowlist non-expansion).
5. **Do NOT** use the FU4 implementation, the R1 record adapter, or
   any model as the expected-label oracle (section 4.6 item 2). The
   implementation may be READ as the frozen contract of record (it is
   the C0-pinned surface the labels cite); its OUTPUT may not be read
   as the answer.
6. **Do NOT** seal before every non-held case carries your re-
   derivation record (section 5 below is the exact seal procedure).

## 1. The population (where to look)

* The case documents: `product_intelligence/evaluation/bundle_authority/
  fixtures.py` - `CASES` (96 draft case documents, the exact 16-key
  shape minus `case_digest`; every label in the DRAFT state).
* The author pass + findings: `evaluation/fu4_bundle_authority_qualification/
  challenge_log.md` (section 3 table: per-case grounding citation +
  author re-derivation; section 4: the C2-F findings; section 6: the
  agreements / disagreements / corrections log).
* The C2 governance suite (the mechanical gates you are completing):
  `tests/evaluation/bundle_authority/test_q3c_c2_label_governance.py`.
* The matrix of record: `docs/PRODUCT_INTEL_Q3C_FU4_BUNDLE_AUTHORITY_
  QUALIFICATION_DESIGN.md` sections 5.1-5.6 (the rows) + 4.4-4.6
  (the case document + label contract) + 8 (this workflow).

## 2. Per-case review worklist (the 86 non-held cases)

For each case ID below: open the case in `fixtures.py`, read the
`label.grounding_citation`, re-derive the `expected` block from the
cited rows over the sealed `source` / `derivation_inputs` /
`recorded_case` documents, compare to the recorded expectation, and
record your verdict (AGREE / CHALLENGE + resolution) under your
identity + instant. The mechanical pre-checks (the loader over your
review-filled copy - section 5) must pass for every case you sign.

The 86 review-ready case IDs (all 48 matrix rows at their minimums;
the row is named per case):

FA4-PROV-001 (A1) | FA4-PROV-003 (A2) | FA4-PROV-004 (A2) | FA4-PROV-005
(A3) | FA4-PROV-006 (A4) | FA4-PROV-007 (A5) | FA4-PROV-008 (A5) |
FA4-PROV-009 (A6) | FA4-PROV-010 (A7) | FA4-PROV-011 (A7) | FA4-PROV-012
(A8) | FA4-PROV-013 (A8) | FA4-DELE-004 (A-DELE) | FA4-UNPR-001 (B1) |
FA4-UNPR-002 (B1) | FA4-UNPR-003 (B2) | FA4-UNPR-004 (B2) | FA4-UNPR-005
(B3) | FA4-UNPR-006 (B4) | FA4-UNPR-007 (B5) | FA4-UNPR-008 (B5) |
FA4-UNPR-009 (B5) | FA4-UNPR-010 (B6) | FA4-UNPR-016 (B6) | FA4-UNPR-013
(B7) | FA4-UNPR-014 (B7) | FA4-UNPR-015 (B8) | FA4-UNPR-026 (B8) |
FA4-UNPR-017 (B9) | FA4-UNPR-018 (B9) | FA4-UNPR-019 (B10) | FA4-UNPR-020
(B10) | FA4-UNPR-021 (B10) | FA4-UNPR-022 (B11) | FA4-UNPR-023 (B12) |
FA4-DELE-005 (B-DELE) | FA4-DELE-006 (B-DELE) | FA4-UNPR-024 (B6/B-only) |
FA4-UNPR-025 (B5/B-only) | FA4-CONTR-001 (C1) | FA4-CONTR-002 (C1) |
FA4-CONTR-003 (C2) | FA4-CONTR-004 (C2b) | FA4-CONTR-005 (C3) |
FA4-CONTR-006 (C3) | FA4-CONTR-007 (C4) | FA4-CONTR-008 (C4) |
FA4-CONTR-009 (C4) | FA4-CONTR-010 (C5) | FA4-CONTR-012 (C7) |
FA4-CONTR-013 (C7) | FA4-ADV-001 (D1) | FA4-ADV-002 (D1) | FA4-ADV-003
(D1) | FA4-ADV-004 (D2) | FA4-ADV-005 (D3) | FA4-ADV-007 (D3) |
FA4-ADV-008 (D4) | FA4-ADV-009 (D4) | FA4-ADV-010 (D5) | FA4-ADV-011
(D5) | FA4-ADV-012 (D6) | FA4-ADV-013 (D6) | FA4-ADV-014 (D7) |
FA4-ADV-015 (D7) | FA4-ADV-016 (D8) | FA4-ADV-017 (D8) | FA4-ADV-018
(D9) | FA4-ADV-019 (D9) | FA4-ADV-020 (D10) | FA4-ADV-021 (D10) |
FA4-ADV-022 (D11) | FA4-ADV-024 (D12) | FA4-ADV-025 (D13) | FA4-ADV-026
(D13) | FA4-ADV-027 (D14) | FA4-ADV-028 (D14) | FA4-ADV-029 (D14) |
FA4-ADV-030 (D15) | FA4-ADV-031 (D15) | FA4-ADV-032 (D16) | FA4-ADV-033
(D16) | FA4-ADV-035 (D17) | FA4-ADV-036 (D17) | FA4-ADV-037 (D18) |
FA4-DELE-007 (B-DELE/B-only)

(That is the 86 non-held cases + the three C2-F6 lighter-shape cases
FA4-UNPR-011 / FA4-UNPR-012 / FA4-CONTR-011, which LOAD but are held
on the evidence gap - 88 signable; the seven C2-F loader-held cases
seal only after the section 4 adjudication + the named correction.)

## 3. Tester minimum (design section 7.6 + the C2 directive)

Re-derive, independently of the reviewer pass: (a) ALL 37 adversarial
D cases (FA4-ADV-001..037 - including the held FA4-ADV-006 / 023 / 034,
for whose findings you record the tester's reading); (b) the false-
PROVEN-adjacent shapes (FA4-PROV-001..013, FA4-ADV-001..003, FA4-
ADV-010..011, FA4-ADV-014..015, FA4-ADV-035..036); (c) the
`attestation_missing` tagged population (FA4-UNPR-003..006, FA4-
UNPR-013..014, FA4-UNPR-022, FA4-ADV-037); (d) the
`historical_binding_confusion` tagged population (FA4-UNPR-001, FA4-
ADV-032..034); (e) the `cross_listing_substitution` tagged population
(FA4-ADV-004..005, FA4-ADV-007, FA4-ADV-010, FA4-ADV-012). Together
this is >= 20% of the 96-case population with all D rows included.
Record: case IDs, your governing citations, your independently
derived labels, disagreements + resolutions (challenge log section 6,
under your identity).

## 4. The C2-F adjudications (per the challenge log, section 4)

For each finding, the decision you record:

* **C2-F1** (FA4-DELE-001, FA4-DELE-002, FA4-DELE-003 - the
  non-bundle PROVEN rows): ratify
  the hold + name the correction (design section 4.4 coherence-rule
  scoping to bundle-channel cases, or the C1 schema correction), or
  record a higher-authority reading that makes the row sealable at
  v1.0.0.
* **C2-F2a** (FA4-ADV-006): choose the stage - the design row's
  PRESENTATION_GATE (with the documented bound) or the observable
  CORPUS_INTEGRITY - and record the reading.
* **C2-F2b** (FA4-ADV-034): ratify the E1-observation-point reading
  or record a different one.
* **C2-F3** (FA4-PROV-002): ratify the hold (no recorded bundle +
  marker source at v1.0.0) - the row seals under C3 or a design
  revision.
* **C2-F5** (FA4-ADV-023): same class - the recorded catalog grounds
  the exact-identifier shape, not the attested clauses.
* **C2-F6** (FA4-UNPR-011, FA4-UNPR-012, FA4-CONTR-011): ratify the
  lighter-shape
  authoring + the evidence-gap record, or name the schema correction
  that would seal the recorded extraction result with a DERIVED
  outcome.

## 5. The seal procedure (exactly, when the review is complete)

1. In `fixtures.py`, for every case you signed: set
   `label.reviewer` = your recorded identity, `label.reviewer_utc` =
   your recorded instant, `label.review_status` = `"REVIEWED"`. For
   each held case: apply the adjudicated correction (label move under
   section 4.6 item 5 with the A-D reason class + `label_revisions`,
   or the row stays out of the sealed population with the recorded
   finding).
2. Record every challenge / agreement / correction in
   `challenge_log.md` section 6 under your identity + instant
   (agreements included - the log is complete or it is not the audit
   surface).
3. Re-run the authoring dry-run (every non-held case must load under
   the family loader with your review fields; the C2 suite's
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
