# FU4 Bundle Authority Qualification Corpus Family

**Corpus identity:** `PI-FU4-BUNDLE-AUTHORITY-QUALIFICATION` (first
version `1.0.0`, schema 1, sealed under the registered FU4 binding
`("V2", "2.1", 1, 1, "SEMANTIC_AUTHORITY_V2_S2A_FU4")`).

This is the **independently labeled qualification corpus** for the FU4
Bundle composition authority — the benchmark against which the frozen
implementation (`product_intelligence/research/semantic_authority_fu4.py`
+ the R1 record / codec / replay surface) is later measured (Track A,
the deterministic evaluator, E1) and the published-evidence axis on
which the pinned models are scored for review assistance only (Track B,
E2). It is the O-2 / "Bundle-specific qualification cases" lineage that
the R2 record named as the missing separately approved phase.

## What this family is

* A SEPARATE corpus family: its own loader / seal / manifest / policy /
  report (`product_intelligence/evaluation/bundle_authority/`). The
  semantic family (`PI-SEMANTIC-V2-QUALIFICATION` 1.0.0–1.2.0) is NOT
  extended, NOT modified, and NOT reinterpreted; its artifacts are
  byte-pinned by the C1 / C2 suites.
* A two-track qualification: **Track A** (the frozen FU4 derivation +
  constructors + the registered R1 codec / replay executed offline over
  the sealed corpus; metrics M1–M15; gates G1–G8) and **Track B**
  (the pinned models under the frozen Prompt 2.1 scored on published-
  evidence fidelity; gates MB-1..MB-3). Track B NEVER feeds Track A and
  NEVER constructs an attestation (gate MB-3).
* An independently labeled ground truth: every case carries the
  governing design row + citation, the source evidence + provenance,
  the expected authority outcome (unit / quantity axis / composition
  states / tier / pricing consequence / refusal stage), the explicit
  rationale, the author identity + instant, and (at the sealed
  endpoint) the distinct reviewer identity + instant (design sections
  4.4 / 4.6 / 8.2). The labels are grounded in the approved contract
  semantics (P3 design, Q3-B4 firewall decision, the Q3-C-D1 matrix) —
  NEVER in the implementation output or a model response.

## What this family is NOT

* Not a semantic-model corpus: it labels the DETERMINISTIC AUTHORITY
  axis (and, for the model-facing subset, the PUBLISHED-EVIDENCE axis
  for Track B scoring) — never the semantic decision axis.
* Not a production evidence store: real-market archives are cited,
  never re-fetched by the evaluator (zero-live); v1.0.0 carries ZERO
  REAL_MARKET cases (C3's separately gated acquisition).
* Not an authority: nothing here grants pricing eligibility, tier
  promotion, or production activation. The family report's computable
  state is at most `QUALIFIED_FOR_REVIEW_ASSISTANCE` under an APPROVED
  family policy; at this endpoint it is `UNAPPROVED / NOT EXECUTED`
  (the corpus is not sealed, no case is independently qualified, and
  the family policy is DRAFT).

## State of record (the C2 draft endpoint)

The declared population in
`product_intelligence/evaluation/bundle_authority/fixtures.py` is the
complete design section 5 matrix (all 48 rows at their minimums; 93
Track A cases) + 3 Track B-only model controls (96 cases): 88
SYNTHETIC + 8 RECORDED_FIXTURE, five product categories, every bounded
vocabulary member the contract admits for a bundle comparison.

**The corpus is NOT sealed.** Every label is in the explicit DRAFT
state (`reviewer: null`, `review_status: "DRAFT"`); the family loader
refuses that state by design (`REVIEW_STATUS_VALUES = {"REVIEWED"}`),
so no loadable corpus can be produced from the draft population and NO
`corpus_v1.json` / `manifest_v1.json` is committed. This directory
carries the DRAFT governance artifacts only:

* `policy/qualification_policy_draft_1.json` — the family DRAFT policy
  (the design section 7.2 threshold vocabulary; DRAFT status;
  `approved: false`).
* `challenge_log.md` — the author's independent derivation pass over
  every case (grounding citations, the contract re-reading probes, the
  ten C2-F findings where the authored document is HELD), the
  agreement / disagreement record, and the seal gate status.
* `reviewer_handoff.md` — the precise, per-case worklist for the
  genuinely distinct independent label reviewer + independent tester
  (design section 8): what to re-derive from which citation, the
  findings to adjudicate, and the exact seal procedure when review
  completes.

**The independent review is the missing gate.** The corpus author
(C2, the recorded author identity) has NOT impersonated a reviewer; no
reviewer identity, timestamp, or signature exists in this population.
Per the C2 directive: the draft + this handoff are delivered without a
falsely sealed corpus. The seal (and with it the qualification claim)
completes only when the two-identity review of design section 8.2 is
genuinely staffed and recorded.

## Layout (design section 4.2)

```
evaluation/fu4_bundle_authority_qualification/
  README.md                     this file
  policy/qualification_policy_draft_1.json   family DRAFT policy
  challenge_log.md              the label-governance record (author pass)
  reviewer_handoff.md           the independent review worklist + seal procedure
  corpus_v1.json                ABSENT at the draft endpoint (the seal)
  manifest_v1.json              ABSENT at the draft endpoint (the seal)
  sources/<case_id>/            C3 real-market archives (ABSENT - zero REAL_MARKET cases)
  reports/q3c_e1_baseline/      E1 committed Track A baseline (ABSENT - E1 not run)
  reports/q3c_e2_baseline/      E2 committed no-capture baselines (ABSENT - E2 not run)
```

## Validation entry points

* `python -m pytest tests/evaluation/bundle_authority/` — the C1
  integrity suite (250 nodes) + the C2 label-governance suite.
* The C2 suite pins: the matrix coverage + population minimums, the
  draft state (the loader refuses the draft; no seal artifact exists),
  the authoring import prohibition, the anti-derivation label scan,
  the design-citation grounding, the challenge-log completeness, the
  held-case set (the C2-F findings), the historical corpus / module
  preservation, the DRAFT-only policy state, and the adversarial gate
  demonstrations (forged review metadata, missing review, missing
  matrix rows, stale digests, modified expected labels cannot silently
  pass the qualification gate).
