# Product Intelligence — Q3-C-D1: FU4 Bundle Authority Qualification Design

**Mode: DESIGN ONLY — no implementation in this phase.** No code, no test,
no corpus artifact, no label, no capture, no deployment, no migration, no
model call, no authority promotion, no pricing wiring. The only artifacts
of this phase are this document and the authorized STATUS / PLAN additions
recording its existence and its unapproved state.

**Starting SHA:** `3bf6eb294df3ca83b93665158297f97abf3fba4b`
(Q3-B5-P5-R2-FU1 endpoint — the six-module integrity contract
restoration; baseline collection **7574, re-verified this session** by a
full `pytest --collect-only` over the working tree at this SHA).

**Scope.** This document designs the first independent qualification
program for FU4 Bundle composition authority — the separately versioned,
independently labeled qualification corpus, the two-track evaluation
methodology (deterministic authority / model-assisted evidence
acquisition), the acceptance policy, the independent review workflow, and
the bounded phase plan that a later, separately approved implementation
would execute. It exists to close the explicit gap recorded by
Q3-B5-P5-R2 (STATUS "Unresolved qualification gaps (explicit)", item 1):
"Corpus 1.2.0 is a binding-registration and semantic-compatibility
corpus; it does not independently qualify the FU4 Bundle composition
authority" (stated in the 1.2.0 manifest inside the manifest digest).

**The mission, restated.** The approved R1/R2 infrastructure supports FU4
deterministic Bundle authority derivation, versioned FU4 decision
records, strict codec and zero-live replay, offline FU4 binding
registration, and corpus 1.2.0 semantic compatibility evaluation. None of
that qualifies FU4 Bundle authority. This design specifies a qualification
program capable of detecting **false authority promotion** — in
particular a false `PROVEN_EQUIVALENT` (the dangerous direction) and a
false `CONTRADICTED` (the over-restrictive direction) — against
independently labeled cases, under five explicitly separated axes:

1. **Semantic product identity** — the model's / deterministic
   identity question (decision, confidence, substate, conflict classes).
2. **Bundle composition equivalence** — the FU4 unit axis
   (`PROVEN_EQUIVALENT` / `UNPROVEN` / `CONTRADICTED`) over the published
   composition clauses, their completeness attestations, and the quantity
   axis.
3. **Sales-unit quantity equivalence** — the determined quantity-axis
   state (`CONSISTENT` / `BOTH_UNPUBLISHED` / `ATTESTED_NOT_MATERIAL` /
   `CONTRADICTED` / `UNDETERMINED`).
4. **Authority tier eligibility** — the derived tier under a scripted
   identity context (`MACHINE_VERIFIED` / `AI_ASSISTED_COMPARABLE` /
   `NEEDS_REVIEW` / `HUMAN_CONFIRMED` / `HARD_CONFLICT` /
   `EXCLUDED_LOW_CONFIDENCE`) with the restrict-only ceilings.
5. **Pricing eligibility** — the consequence axis: whether the derived
   tier is in `PRICING_ELIGIBLE_TIERS`, and (recorded, never exercised)
   that NO pricing consumer exists that could read any FU4 state.

**The headline invariant (I-1).** A correct semantic MATCH must never be
treated as sufficient proof of Bundle equivalence or pricing
comparability. Under the frozen FU4 contract, the unit derivation's
inputs are signature-pinned to the recorded channel + evidence records +
quantity attestation; the scripted semantic evaluation (decision,
confidence, conflict classes, matched attributes) is NEVER a unit input.
The corpus makes this a labeled, measured property: matrix rows B10 /
D13 / D11 carry scripted MATCH contexts over unproven or contradicted
bundle evidence, and the evaluator additionally runs a perturbation
invariance check (I-4, §6.3).

**Relationship to the prior documents.**

| Document | Role here |
| --- | --- |
| `docs/PRODUCT_INTEL_Q3B5_P3_BUNDLE_COMPOSITION_DESIGN.md` (Q3-B5-P3, CORRECTED — Blocker A / B + Revision records 2 / 3) | The approved FU4 contract design of record. Its decision table (D1–D20), the U0–U21 rows, the §5.1 ten-case matrix, the §3.8 attestation records, the §3.7 materiality grammar, and the §9 adversarial matrix are the CONTRACT SEMANTICS the qualification labels are grounded in (cited row-by-row, never re-derived from the implementation). |
| `docs/PRODUCT_INTEL_Q3B5_P5_FU4_BINDING_REPLAY_QUALIFICATION_DESIGN.md` (Q3-B5-P5) | The approved registration design executed by R1 / R2 (+ FU1 corrections). Its DEC-5 (separate metric surfaces), §5.4.2 (deterministic FU4 authority correctness surface), §7 (firewall obligations), §9 (adversarial conventions), and O-2 / O-3 / O-4 (future corpus case addition, live execution, capture) are binding inputs. THIS DESIGN IS THE O-2 / "Bundle-specific qualification cases" lineage that R2's STATUS record names as the missing separately approved phase. |
| `docs/PRODUCT_INTEL_SEMANTIC_V2_Q3B4_AUTHORITY_BOUNDARY_DECISION.md` (Q3-B4) | The approved firewall decision: the §4.1 invariant (a fully qualified semantic MATCH must never auto-price on an unproven or contradicted commercial sales unit), the W1 atomic consumer guard, and AD-Q3B4-6 (the Q3-C conditioning — the qualification decision is conditioned on the firewall disposition). This program is the Q3-C qualification lineage for the FU4 successor binding. |
| `docs/PRODUCT_INTEL_SEMANTIC_V2_PROMPT_2_1_DESIGN_Q3B3_FU2.md` (rev 2) | The approved Prompt 2.1 design; the COMMERCIAL SALES-UNIT RULES and the P1–P6 sales-unit outcome table are the MODEL-SIDE contract Track B measures against (binding-agnostic for the model — the authority token never enters the prompt). |
| `docs/PRODUCT_INTEL_Q3B5_P1_INDEPENDENT_AUDIT.md` | The P1 audit precedent: finding F-4 (the DRAFT policy is scoped to corpus 1.0.0 — a policy-governance step is owed by any later qualification lineage) is inherited by this program as the policy contract of §7.1 / §7.7: a policy-gated tier decision requires an APPROVED policy applicable to THIS family's corpus identity, and no existing policy is copied, modified, or extended here. |
| `docs/PRODUCT_INTELLIGENCE_STATUS.md` / `docs/PRODUCT_INTELLIGENCE_PLAN.md` | Phase state (R1 / R1-FU1 / R2 / R2-FU1 all PENDING INDEPENDENT REVIEW at the starting SHA) and the decision log (through §26.40 / AD-082). The documented STATUS/PLAN catch-up applies: this design's row is §26.41; the implementation phases get their own rows at completion. |

**What this document deliberately is NOT.**

* Not an implementation. No module, test, corpus artifact, label, or
  registry entry is created or changed by this phase.
* Not a qualification or promotion decision. No status below
  `RESEARCH_ONLY` is claimed, recommended as achievable now, or implied.
  The program's final state at completion of all its phases remains
  `POLICY_PENDING` until an independently reviewed policy is explicitly
  approved (§7.7) — that is, at every phase endpoint before P1 (P1 is
  the approving phase; Q1, the first phase after it, is the first phase
  whose computed state may exceed POLICY_PENDING), and
  `PRODUCTION_AUTHORITY_QUALIFIED` is outside the
  report's decision space entirely (§7.5).
* Not an amendment of any frozen contract. The FU4 module, the FU2 / FU3
  modules, the extraction module, the S2-C channel, the R1 record / codec
  / replay surface, the Prompt 2.0 / 2.1 contracts, the corpus
  1.0.0 / 1.1.0 / 1.2.0 artifacts, the DRAFT policy, the eight semantic
  gates, and the live runtime are all specified here only as UNCHANGED
  inputs.
* Not a re-labeling of corpus 1.2.0. The new corpus is a SEPARATE
  family with its own identity, versioning, seal, and loader (§4.1).
  Corpus 1.2.0 stays exactly as sealed (digest `582b35bb…`), binding-only
  under the FU4 tuple, semantic-compatibility-scoped per its own
  manifest statement.

---

## Revision record (Q3-C-D1-FU1 — adjudication-driven design revision,
this document, revised in place)

**Revised at:** `df91e4908dc538b6cad5ea7a218f32100e441ecd`
(the Q3-C-C2 endpoint — the committed v1.0.0 DRAFT population (96
cases) + the reviewer handoff; baseline collection **8043, re-verified
this session**).

The independent C2-F1 adjudication of the ten HELD C2 cases (challenge
log §4; reviewer handoff §4) found design / schema conflicts between
the approved Q3-C-D1 matrix and (a) the frozen P3 / P5 contracts, (b)
the C1 family loader, and (c) the recorded-source ground. This revision
resolves each adjudicated finding in place. Design-only: no production
code, no corpus fixture, no expected label, no test, no qualification
policy, and no seal moves in this revision; the corrections it names
are the scope of the bounded C1-FU3 + C2 corrective implementation
(§9.11 — PROPOSED, NOT authorized by this revision; separately
approval-gated). Every proposed correction was independently verified
against the cited evidence at the starting SHA (the adjudication
report is NOT treated as authority over the frozen contracts — where
the adjudication and a frozen contract met, the frozen contract
governed, as recorded per finding below).

**Adjudicated findings and corrections of record**:

| Finding | Cases | Correction (location) | Higher-authority contract |
| --- | --- | --- | --- |
| C2-F1 | FA4-DELE-001..003 | §4.4: the Bundle-specific quantity / composition coherence checks apply ONLY to Bundle-channel cases; the non-Bundle delegated FU3 PROVEN expectations retain the frozen P3 D11 audit-field semantics (the six Bundle-axis fields EXACTLY null) — the byte-identical delegation (P3 D9) is preserved; the A-DELE row states the null semantics (verified at the revision: the frozen non-Bundle audit fields are exactly None; the unscoped C1 check refused the design-grounded label) | P3 D9 / D11 (frozen) |
| C2-F2a | FA4-ADV-006 | §5.4 D3-ii: the content-identical-channel substitution stage is CORPUS_INTEGRITY — the mismatch (the record's embedded original ≠ the case's recorded extraction evidence) is observable ONLY by the family loader; the frozen P5 R-5 channel-granularity bound prevents the derivation presentation gate from detecting it (over content-identical channels the channel-content binding holds and all four frozen gate steps pass — verified at the revision: the labeled PRESENTATION_GATE expectation is incoherent because the case-document observation fired, and the self-consistent payload twin decodes AND replays cleanly, so the (ii) variant is surface DERIVATION, no record twin); the separate D3-i PRESENTATION_GATE case is preserved | P5 R-5 / risk R-C1-10 (frozen); P3 Revision record 3 (frozen) |
| C2-F2b | FA4-ADV-034 | §5.4 D16-iii: the FU3-token derivation-surface contract-misuse refusal is an EXECUTION-level observation point (the frozen FU3 function is invoked under the frozen FU3 token — over the sealed documents, which are sound FU4 documents, no constructor / codec / case-document observation fires; verified at the revision). It is NOT a sealable v1.0.0 corpus case at any refusal stage: the v1.0.0 D16 corpus minimum is recorded as 2 (the explicit phase-boundary correction of Q3-C-D1-FU1), and the third obligation is preserved as a MANDATORY E1 adversarial-execution assertion (§5 stage semantics (v); §9.6). The frozen FU3 / FU4 token boundary is NOT weakened | P3 §5.4 per-binding dispatch + D9 (frozen); P5 §4.2a codec registry (frozen) |
| C2-F3 | FA4-PROV-002 | §5.1 A1: the current recorded fixture sources do NOT publish the required complete Bundle composition (§2.5 verified — zero bundle occurrences in the page fixtures; the recorded 0034-shape context carries the clause WITHOUT the versioned completeness marker, and its title cannot form the family's identity context — verified at the revision: past the identity-context defect, the span-grounding refusal over the recorded target clause is the second boundary). The A1 recorded PROVEN-shape variant is adjudicated C3-deferred: v1.0.0 A1 minimum 1 (the SYNTHETIC case); the RECORDED_FIXTURE variant is an additive 1.1.0 obligation authored over the C3-acquired recorded source. The requirement for independently evidenced publisher completeness (P3 D19) is preserved — recorded evidence is never replaced with invented text | P3 D19 (frozen); design §2.5 / §7.6 (the C3 gate) |
| C2-F5 | FA4-ADV-023 | §5.4 D11-ii: the recorded identifier-family evidence (the one-character-different Micron 7500 catalog part numbers) is separated from the by-construction Bundle composition evidence. The hybrid variant (RECORDED_FIXTURE over the recorded identifier context + the ungrounded composition clauses) CANNOT be represented truthfully by the existing schema (the span-grounding provenance rule + the row's required U1 EXACT identity context — the recorded context is U4_NO_MPN, no candidate identifier; both boundaries verified at the revision). The re-authored case is SYNTHETIC (the truthful evidence classification) with the EXACT U1 EXACT identity context of the row (U1_TITLE_MPN, equal non-empty normalized part numbers, TITLE_MPN_TOKEN, NOT_REQUIRED — W8); the Micron recorded catalog is documented as the row's identifier-shape context only and is NOT claimed to publish Bundle compositions. The D11 material-contradiction authority contract (P3 U17) and its 2-case adversarial coverage are retained | P3 U17 (frozen); design §4.3 / §4.4 grounding rules; design §2.5 |
| C2-F6 | FA4-UNPR-011/012, FA4-CONTR-011 | §4.4: the allowed state — candidate composition record null, candidate basis NONE, recorded extraction result present, presented channel EXACTLY the frozen P2 mapping of that result, expected authority independently derived from the frozen contract (U0 UNPROVEN over the canonical UNAVAILABLE mapping); the new loader-visible case-document-integrity refusal when the recorded result and the presented channel do not match. The existing EXTRACTION_RESULT_V1 / RECORDED_CHANNEL / NONE negative contracts are preserved. W7: FA4-CONTR-011 must accurately instantiate its cue state — the frozen P2 over the current sealed text is AMBIGUOUS_CUE (verified at the revision: the established pack-of-3 structured cue + the ambiguous count-only "bundle of 2" title cue), NOT the rationale's claimed CONTRADICTED_CUES; the re-authored case carries the genuine frozen CONTRADICTED_CUES instantiation (verified at the revision: the title's established bundle-with-contents clause vs the structured pack-of-N field ⇒ CONTRADICTED_CUES, the mapped channel the canonical UNAVAILABLE) or describes the exact cue state of the instantiation it carries | frozen P2 cue table + lossy mapping (frozen); P3 U0 / D8 (frozen) |
| C1 identity-context defect | FA4-ADV-023, FA4-PROV-002 (any U4_NO_MPN case) | §4.4: the loader's identity-assessment decode allows the EMPTY normalized candidate part number exactly where the frozen V2 constructor permits it — the U4_NO_MPN substate ("no candidate identifier exists"), symmetrically the empty normalized requested part number where the frozen constructor permits (E1_NO_TARGET_MPN). Verified at the revision: the frozen `IdentityStateAssessmentV2` accepts the empty string (type check only), the C1 loader refused it (the first boundary over both held recorded-context cases); the frozen constructor + the round-trip projection remain the final arbiter; no other identity constraint is weakened; the frozen constructor is NOT modified | frozen `IdentityStateAssessmentV2` (S2-A, byte-pinned) |
| W1–W9 | (governance) | W1: the E1 adversarial re-execution asserts the exact bounded refusal reason (the named observation over the loader-observation stages) — §6.1 / §9.6. W2: the qualification-ready gate enforces EVERY §5.6 composition floor on the ACTUAL seal population — §8.2 / §9.4. W3: held-set changes are explicitly adjudicated and monotonic (pinned by the C2 suite; release only via the recorded adjudication + the verified correction) — §8.2. W4: the missing-review rejection reason is pinned — §8.2. W5: preserved as a documented maintenance issue — no immediate code change is warranted at this endpoint; no threshold or contract move; carried to the owning phase's maintenance scope. W6: the bounded vocabulary is projected over the seal population — §5.6 / §8.2. W7: FA4-CONTR-011 cue-state accuracy — §5.3 C6. W8: FA4-ADV-023 identity-context correction (the exact U1 EXACT shape) — §5.4 D11. W9: the DERIVED expected-axis / sealed-evidence coherence checks use frozen contract data only — never implementation output (the §4.6 implementation-output prohibition extends to the loader's coherence checks; structurally pinned by the C1 import scan + the sentinel no-execution probe) — §4.4 / §4.6 | design §4.6 (binding); CLAUDE.md evaluation-truth rule |

**Register of corrected locations** (pre-revision → corrected):

| Location | Correction |
| --- | --- |
| §4.4 (coherence bullet) | the PROVEN coherence check scoped to Bundle-channel cases; the non-Bundle PROVEN expectation carries the exactly-null Bundle-axis fields (P3 D11); the identity decode allows the empty normalized part numbers where the frozen constructor permits (U4_NO_MPN / E1_NO_TARGET_MPN); the allowed NONE-basis recorded-extraction-result state + the new case-document-integrity refusal; the W9 coherence-separation statement |
| §4.6 item 2 | the implementation-output prohibition extends to the loader's coherence pre-checks (W9 — the item (d) loader-coherence separation) |
| §5 (stage semantics) | item (v) added: the execution-level contract-misuse observation point (D16-iii → the E1 mandatory assertion) |
| §5.1 A1 | the RECORDED_FIXTURE-shape variant is C3-deferred (v1.0.0 minimum 1; the additive 1.1.0 obligation) |
| §5.1 A-DELE | the non-Bundle audit-field null semantics stated on the row (P3 D11) |
| §5.1 Category A minimum | 17 → 16 at v1.0.0 (the A1 correction — recorded destination) |
| §5.2 B6 | (ii) / (iii) carry the allowed recorded-extraction-result state (C2-F6) |
| §5.3 C6 | the cue-state accuracy requirement (W7) |
| §5.4 D3 | (ii) stage CORPUS_INTEGRITY + the R-5 bound + surface DERIVATION; (i) remains PRESENTATION_GATE |
| §5.4 D11 | (ii) the truthful SYNTHETIC re-authoring + the exact U1 EXACT identity context; the recorded identifier family is context, not composition evidence |
| §5.4 D16 | v1.0.0 minimum 3 → 2 (the explicit phase-boundary correction); (iii) the mandatory E1 assertion |
| §5.4 Category D minimum | 37 → 36 at v1.0.0 (the D16 correction — recorded destination) |
| §5.6 | the revised v1.0.0 accounting (90 Track A floor; the 94-case seal population; the RECORDED_FIXTURE enumeration; the additive 1.1.0 obligations; the W6 seal-population projection) |
| §6.1 | the W1 exact refusal-reason assertions; the D16-iii execution-level row under M13 / G6; the non-Bundle axis-audit null semantics under M15 |
| §7.6 | the diversity floors reference the corrected §5.6 + the W6 seal-population projection |
| §8.2 | the W3 held-set adjudication + monotonicity (item 6); the qualification-ready gate contract (item 7 — the W2 / W4 / W6 floors + the pinned reasons) |
| §9.4 | the corrected acceptance (the floors on the seal population; the pinned gate reasons) |
| §9.6 | the mandatory D16-iii adversarial-execution assertion; the W1 exact-reason assertions |
| §9.11 (new) | the proposed bounded C1-FU3 + C2 corrective implementation scope (NOT authorized) |
| §10 R-C1-10 | the D3-ii reading corrected to the adjudicated CORPUS_INTEGRITY observation point |
| §11 O-10 (new) | the two v1.0.0 row-minimum phase-boundary corrections recorded as adjudicated (not open) |

**What this revision deliberately does NOT do.** No acceptance
threshold is silently changed: the two v1.0.0 row-minimum movements
(A1 2→1; D16 3→2) are the explicit phase-boundary corrections of
record, each with its destination (the C3 / additive 1.1.0 obligation;
the E1 mandatory adversarial-execution assertion), its rationale, its
governing frozen contract (P3 D19; P3 §5.4 / D9), and its later
acceptance gate (the C3 acceptance + the 1.1.0 re-seal verification;
the §9.6 E1 acceptance). No frozen contract (P3 / P5 / P2 / FU3 / FU4 /
R1) is modified. The pre-revision 92-case floor is NOT re-stated: it is
re-derived (16 + 25 + 13 + 36 = 90) over the corrected row set, and the
corrected 94-case v1.0.0 seal population (91 Track A) meets it. The
DRAFT population's labels are NOT bent: the ten HELD cases are resolved
by the design / schema corrections named here + the recorded pre-seal
case corrections of the C2 corrective phase (the D3-ii re-label, the
D11-ii re-authoring, the B6-ii / B6-iii / C6 re-authorings — under the
§4.6 item 5 governance, recorded in the challenge log; the two
population removals — D16-iii, the A1 recorded variant — under the
phase-boundary corrections of record).

**Q3-C-D1-FU2 consistency correction (corrected in place, this
document).** A full audit of the Q3-C-D1-FU1 revised accounting
found three residual references to the pre-revision `92`-case Track A
floor stated as OPERATIVE (not labeled historical): (1) the §7.6
"Why a small synthetic corpus cannot qualify a model" bullet —
`the 92-case floor` → `the 90-case floor`; (2) the same bullet —
`The 92-case v1.0.0 floor` → `The 90-case v1.0.0 floor`; (3) the
§9.4 scope line — `≥92 Track A / ≥21 Track B minimums` → `≥90 Track
A / ≥21 Track B minimums` (the §9.4 acceptance (1) already referenced
the corrected (Q3-C-D1-FU1) row minimums over the seal population; the
scope line now agrees with it). No adjudication, threshold,
population, obligation, or acceptance criterion was re-derived or
moved by Q3-C-D1-FU2: the operative accounting is exactly the
Q3-C-D1-FU1 revised v1.0.0 accounting of record (Track A floor
16 + 25 + 13 + 36 = 90 over the 48 matrix rows; the 94-case seal
population = 91 Track A (≥ 90) + 3 B-only; Track B 24 (≥ 21) =
21 A_B-shared (≥ 18) + 3 B-only; 88 SYNTHETIC (93.6% ≥ 80%) + 6
RECORDED_FIXTURE (≥ 5) + 0 REAL_MARKET; 5 categories (≥ 4); the
bounded vocabulary projected over the actual seal population — W6).
The labeled pre-revision references (the revision record's
`pre-revision 92`, `17 + 25 + 13 + 37 = 92`, `A1 2→1`, `D16 3→2`,
`17 → 16`, `37 → 36`; the §5.1 / §5.4 row and category minimum
notes; the §5.6 pre-revision accounting) remain as historical
record.

## Revision record (Q3-C-D1-FU3 — the F-R6 architecture
adjudication, this document, revised in place)

**Revised at:** `b85261924bc4827636ae3c3f54b01c7674d697b4`
(the Q3-C-C1-FU3 + C2 corrective endpoint of record; the C2-R1-FU1
pre-seal corrections are the six uncommitted working-tree files of
the session start, preserved byte-for-byte by this revision;
baseline collection **8082**, of record in the independent
Q3-C-C2-T1 tester ledger over this endpoint).

The independent Q3-C-C2-T1 adversarial tester record (the F-R6
BLOCKER — `tmp_q3c_c2t1_fr6_investigation.md` + the tester ledger)
demonstrated, by exact read-only reproduction, a three-way
inconsistency inside the authoritative design: the approved D6(i)
row's stage attribution (CONSTRUCTION) × the design's own E1
execution clauses (the W1 exact-reason adjudication of Q3-C-D1-
FU1, §6.1, §9.6) × the actual observation point over the sealed
FA4-ADV-012 documents. This revision records the independent
frozen-contract determination (re-verified this session, read-only)
and ADJUDICATES the F-R6 finding. Design-only: no production code,
no corpus fixture, no expected label, no test, no qualification
policy, and no seal moves in this revision; the corrections it
names are the scope of the bounded C1-FU4 + C2-FU2 corrective
implementation (§9.12 — PROPOSED, NOT authorized by this revision;
separately approval-gated).

**The independent frozen-contract determination (of record).** Over
the sealed FA4-ADV-012 documents:

* **The extraction result and its examined input are individually
  valid under the frozen constructors.** Every sealed document
  decodes through the REAL frozen constructors with zero
  constructor errors (the v2 case, the channel, the v3 candidate
  record — its anchors equal the embedded result's own digests; the
  embedded result's self-digests + cue spans verify over its own
  recorded field text — the ALTERED title '…1x CPU'), and the
  frozen presentation gate's four steps (P3 Revision record 3) ALL
  pass (the presented channel is exactly the frozen P2 mapping of
  the embedded result; the recomputed composition equals the
  complete record).
* **The inconsistency exists BETWEEN the case's separately sealed
  documents.** The case's recorded extraction input document (the
  sealed source's projection — the title '…1x SSD') is NOT the
  input the embedded result's `input_digest` binds: the recorded
  input document's canonical digest `a8cdc4d0…` ≠ the result's
  `input_digest` `660fdb47…` (plain-hash verified). The defect is
  a relationship between two documents that live in the CASE.
* **The frozen derivation cannot independently observe that cross-
  document mismatch.** No frozen constructor, codec, gate step,
  derivation signature, or replay path EVER receives the case's
  sealed `source` block or the case's recorded extraction input
  document: the P2 result's `input_digest` is a stored binding the
  frozen code never recomputes against an external document (the
  frozen extractor computes it only over its own
  `ListingObservation` at production time); the v3 record's anchor
  checks are equalities WITHIN the record + embedded result; the
  R1 payload's exact key set carries no such field. Over the
  reconstructed self-consistent typed inputs the frozen derivation
  COMPLETES (U15: UNPROVEN / NEEDS_REVIEW / BOTH_UNPUBLISHED /
  ESTABLISHED / T-AGREE / CEILING_SALES_UNIT_NOT_PROVEN) — the
  defect is invisible to it, not missed by it.
* **The family loader's `SOURCE_EXTRACTION_INPUT_DIGEST` check
  (`corpus.py`) is the first and only non-corroborative
  observation point** (corroborated by the GATE-layer cue / clause
  span-grounding observations). It is a family-owned CROSS-DOCUMENT
  integrity check (the case's recorded extraction input document vs
  the embedded result's `input_digest` binding), classified at the
  CONSTRUCTOR layer as a "mirror" of the construction-level
  binding. A family-loader observation labeled at the CONSTRUCTOR
  layer is NOT an exception emitted by a frozen constructor (the
  five validation surfaces, §5): the frozen constructor is silent
  over this shape, and the W1 clause's construction-stage
  mechanism ("the frozen constructor / codec's bounded error") has
  nothing to assert against.
* **Therefore the D6(i) defect is exactly the stage-semantics (iv)
  class** — "the family loader only (the case document's own
  internal inconsistencies — §4.4 — never presented to the
  implementation)" — the same structural family the C2-F2a
  adjudication (Q3-C-D1-FU1) resolved to CORPUS_INTEGRITY for the
  D3-ii row. No frozen contract (P2 / P3 / P5 / FU4 / R1) requires
  or supports the CONSTRUCTION attribution over this shape; the
  only passages naming it are the design row itself (this
  document), the family loader's mirror classification (a
  family-owned byte), and the C1 suite's pin over that mirror (a
  test byte) — all three movable under this revision's
  governance, none frozen.

**The adjudication (Option B — the stage re-attribution per the
C2-F2a precedent).** The D6(i) row's expected refusal stage is
**CORPUS_INTEGRITY** with **error_type null** (the existing stage-
error vocabulary: the loader's own stage names no implementation
error class), the EXACT named case-document observation
`SOURCE_EXTRACTION_INPUT_DIGEST` being the W1 refusal reason. The
expected outcome **REFUSED stands** (no unit, authority tier,
pricing eligibility, or replay approval is produced for the
invalid case — G4 / M7 are satisfied at the loader observation
point, BEFORE any derivation input exists). Option A (the
execution-semantics clarification keeping the CONSTRUCTION label +
the derivation completion a documented non-observation) was
considered and REJECTED: it would require a D6-i-specific
exception inside W1's stage-keyed exact-reason clause (the clause
as written keys the named case-document observation to
CORPUS_INTEGRITY only and the frozen bounded error to
CONSTRUCTION only — the latter does not exist over this shape),
would leave the row in direct conflict with the design's own
stage semantics (iv), and would perpetuate the D6 row's internal
asymmetry ((i) a loader-mirrored "construction" stage vs (ii)
CORPUS_INTEGRITY for the same loader-observable, never-presented-
to-the-implementation structural family). The construction-stage
requirement is NOT re-interpreted for the unrelated cases: every
row whose named defect IS a frozen-constructor / codec bounded
error (D4 / D8 / D14 / D15 / D17-i + the record-surface twins)
keeps CONSTRUCTION / CODEC_DECODE with the frozen bounded reason
(W1 unchanged for those shapes).

**The F-R2 documentary finding (verified this session).** The two
D11 grounding citations (FA4-ADV-022 / FA4-ADV-023) name the
Micron catalog by PATH only (`tests/fixtures/pages/micron_7500_
part_catalog.json`) while the adjudication record claims "cited by
path + digest" (the D11 row; the C2-F5 prose). The catalog's
working-tree digest at this endpoint is
`160d4fe97a5df5249e8f6404f6b005c0515fab4def1b4668fdaf87c727600743`
(24,060 bytes; recomputed this session — agreeing with the
independent T1 recomputation). The catalog publishes identifiers
only (zero `bundle` occurrences — the C2-F5 statement re-verified
true). The smallest required citation correction — adding the
VERIFIED digest to the two grounding citations (a class-A
annotation correction under §4.6 item 5; the catalog itself is
unchanged; no unverified digest is inserted) — is recorded in the
§9.12 scope. F-R3 / F-R4 / F-R5 / F-R7 / F-R8 stand as the
recorded downstream obligations with their recorded destinations
(unchanged by this revision).

**Register of corrected locations** (pre-revision → corrected):

| Location | Correction |
| --- | --- |
| §5 (stage semantics) | item (iv) states the cross-document case bindings (the D6-i / D3-ii / D6-ii / C2-F6 shapes + their named observations); the five validation surfaces paragraph added (the frozen-constructor / frozen-codec / family-loader cross-document / frozen-derivation / replay distinction) |
| §5.4 D6 | (i) stage CONSTRUCTION → CORPUS_INTEGRITY (error_type null; the named observation `SOURCE_EXTRACTION_INPUT_DIGEST` — the family-loader cross-document observation point, the C2-F2a precedent); (ii) unchanged; the row's shape / evidence / kind / surface (BOTH) / minimum (2) unchanged |
| §5.6 | the refusal-stage projection names the D6-i case under CORPUS_INTEGRITY (D6-i / D6-ii / D3-ii) |
| §6.1 | the execution order: the loader-observation cases run the authorized family-loader integrity path FIRST (as corrected by the Q3-C-D1-FU3-FU1 contract correction: the strict load is Contract A — it ACCEPTS the correctly labeled sealed-raw case after verifying the stage against its internally collected observations; the REAL observation is the family-owned read-only observation interface — Contract B — which must return the exact named observation at the exact layer, and a record with no corpus-surface observation is the explicit bypass-to-G4 failure); a successful FU4 derivation never counts as satisfying a refused case; the W1 example list corrected + extended (the named observations by shape) and the construction / codec clause restricted to the shapes over which the frozen constructor / codec actually refuses |
| §9.6 | acceptance (2): the D rows labeled at the loader-observation stage LOAD through the strict path (Contract A — the label-coherence verification; a correctly labeled case is accepted, not refused) and re-feed the family-owned observation interface as their REAL observation (Contract B — the exact named observation at the exact layer); the explicit bypass-to-G4 rule (a record with no corpus-surface observation is scored NOT refused — G4 failure, regardless of the strict load's acceptance); the nine mandatory adversarial tests of the Q3-C-D1-FU3-FU1 contract correction; the frozen derivation's completion over the reconstructed self-consistent typed inputs is the documented non-observation (never a refusal, never `BYPASSED_INTEGRITY`, never a satisfaction) |
| §9.12 (new) | the proposed bounded C1-FU4 + C2-FU2 corrective implementation scope (F-R6 + F-R2; NOT authorized) |
| §10 R-C1-10 | the D6-i shape recorded as the same loader-only observation-point family (CORPUS_INTEGRITY) |

**What this revision deliberately does NOT do.** No frozen
contract (P2 / P3 / P5 / FU4 / R1) is modified — the frozen
layers' silence over the D6-i shape is the evidence of the
adjudication, not a defect to be fixed. No matrix population floor
moves: the D6 row minimum stays 2, the category D minimum stays
36, the Track A floor stays 90 over the 48 rows, the Track B
floor stays 21, and the 94-case v1.0.0 seal population stands (the
D6-i correction is a stage re-attribution + error_type
nullification of one pre-seal case label under §4.6 item 5
governance — the outcome REFUSED, the replay NOT_APPLICABLE, and
every other expected field are preserved). No implementation, no
label, no fixture byte, no test byte, no pin, no corpus artifact
moves in THIS revision (the named corrections are the §9.12 scope,
separately approval-gated). No seal, no signoff, no reviewer
field. The F-R6 BLOCKER is discharged by this recorded
adjudication: the design's E1 execution clauses, the D6(i) row,
and the observation point now agree.

**Q3-C-D1-FU3-FU1 contract correction (corrected in place, this
document).** The Q3-C-D1-FU3 E1 language as first revised
described the loader-observation rows' E1 mechanism as "the
strict family load must REFUSE the case, and the W1 exact-reason
assertion requires the EXACT named case-document observation(s)".
A read-only verification of the actual family loader (this
session, over the base HEAD) found that description incorrect
over a CORRECTLY labeled sealed-raw case, in two respects:
(1) the strict load ACCEPTS such a case — the stage-coherence
rule passing IS the acceptance: the loader collects its
observations internally, verifies the labeled refusal stage
against them, and returns the case to the corpus (it refuses
only the incoherent label, a DERIVED case carrying a defect, or
a failed digest — the existing C1 sealed-raw tests and the
94-case C2 loader pass are the pins of this contract); and
(2) the public load surface (`decode_corpus_case_document` →
`FamilyCorpusCase`) carries NO observation record (the
observations live in a private structure; the package exports
no observation API) — the W1 exact-reason assertion cannot
read the named observation off the strict load's output. This
correction separates the TWO contracts over the ONE family
logic (the §5 five validation surfaces, §6.1, §9.6, §9.12):
**Contract A — corpus ingestion** (unchanged — the strict load
verifies seal + label governance + stage coherence and accepts
/ refuses the case into the corpus; a negative case loading
successfully does NOT mean the underlying evidence is valid);
**Contract B — E1 negative-case execution** (the evaluator
obtains the observation record ONLY from the narrow, read-only,
family-owned observation interface — the actual
`_run_family_checks()` logic in collection mode, the loader's
own checks reused, NO duplicated mock of the security rules — a
bounded `check / layer / reason` record in deterministic firing
order + the inverse-scoping `observation_stages` mapping
computed from the record + the sealed surface, NEVER from the
label; the interface does not verify the seal and never
invokes the derivation / the replay / any model). The §6.1
failure taxonomy over the record: the required named
observation absent while the labeled stage stays coherent (a
different check fired — the wrong reason) — a W1 FAILURE; the
required named observation at a layer whose `observation_stages`
excludes the labeled stage (the wrong-stage
observation) — the M6 DEFECT, G4 standing on the record's
non-emptiness (a refusal at ANY stage satisfies the hard
gate); the record carrying no corpus-surface observation
(empty, corroborative-only, or never obtained — the check
disabled or bypassed, the record manufactured from the label)
— the EXPLICIT BYPASS-TO-G4 FAILURE (the row scored NOT
refused; `BYPASSED_INTEGRITY`), regardless of the strict
load's acceptance and regardless of any derivation outcome — a
successful FU4 derivation, including a completed `UNPROVEN`,
never satisfies, suppresses, or fills the record (a
`PROVEN_EQUIVALENT` completion over a refused-expected case
fires G1 independently). The nine mandatory E1 adversarial
tests (§9.6) pin this boundary; the §9.12 scope gains the
interface (file (1b)) + its C1 pins (file (2) node (e)).
Option B, the D6-i CORPUS_INTEGRITY / null attribution, the
exact `SOURCE_EXTRACTION_INPUT_DIGEST` observation, the F-R2
documentary correction, all 94 cases and matrix floors, all
frozen safety and pricing invariants, and all deferred C3 /
E1 obligations are UNCHANGED by this note; no adjudication,
threshold, floor, or acceptance criterion was re-derived
beyond the E1 observation mechanism this note corrects.

---

# 1. Executive decision

**Decision.** Approve, for review, a separately versioned FU4 Bundle
Authority Qualification program with:

1. **A new corpus family** (`PI-FU4-BUNDLE-AUTHORITY-QUALIFICATION`,
   proposed identity — O-1), first version `1.0.0`, sealed under the
   registered FU4 binding `("V2", "2.1", 1, 1,
   "SEMANTIC_AUTHORITY_V2_S2A_FU4")`, whose cases label the DETERMINISTIC
   AUTHORITY axis (and, for the model-facing subset, the PUBLISHED-EVIDENCE
   axis for Track B scoring) — never the semantic-model decision axis.
   The corpus is authored by an independent labeling workflow
   (two-distinct-identity review, implementation-output prohibition,
   §4.6 / §8) and is the benchmark later phases are measured against
   (CLAUDE.md evaluation-truth rules apply verbatim).
2. **Two distinct qualification tracks** (§6):
   * **Track A — deterministic authority.** The frozen FU4 derivation,
     the frozen constructors, and the registered R1 codec / replay are
     executed offline over the corpus's recorded evidence and compared
     with the independent labels. This track qualifies the CONTRACT +
     RECORD machinery. It requires no model and no capture; its committed
     baseline is a FULL deterministic evaluation (the semantic harness's
     no-capture NOT_CAPTURED stub is inapplicable — there is no model
     dependency to be missing).
   * **Track B — model-assisted evidence acquisition.** The pinned
     models, under the frozen Prompt 2.1, are presented the recorded
     published content and scored on whether they EXTRACT AND PRESENT the
     published bundle facts (constituents, published quantity, published
     completeness statements, ambiguity) faithfully, without inventing
     facts. Track B qualifies the MODEL for review assistance ONLY. It
     never feeds the FU4 derivation, never overrides Track A, and cannot
     produce authority evidence: a model-reported completeness statement
     is not a publisher attestation (gate MB-3, §7.4).
3. **A six-state decision ladder** (§7.5): `FAIL_CLOSED` >
   `NOT_QUALIFIED` > `POLICY_PENDING` > `RESEARCH_ONLY` >
   `QUALIFICATION_CANDIDATE` > `QUALIFIED_FOR_REVIEW_ASSISTANCE`, with
   `PRODUCTION_AUTHORITY_QUALIFIED` reserved for the separately gated W1
   phase and never computable by the report. The state of record at this
   design's completion is **UNAPPROVED / NOT EXECUTED**; after execution,
   the state can only move under an APPROVED policy of this family.
4. **Eight hard safety gates** (G1–G8, §7.3), each a zero-tolerance
   condition with an exact denominator, including zero false
   `PROVEN_EQUIVALENT` on independently labeled negative cases, zero
   pricing-eligibility leakage, zero evidence-integrity bypass, zero
   cross-listing substitution, zero historical-binding confusion, and
   full replay agreement for accepted records.
5. **A ten-phase bounded roadmap** (§9): D1 (this design) → C0 (the
   recorded pin-gap correction, forced by finding CF-2) → C1 (corpus
   schema + integrity validator) → C2 (independently labeled cases,
   v1.0.0 seal) → C3 (real-market bundle evidence acquisition — the
   statistical-coverage gate for tiers above RESEARCH_ONLY) → E1
   (deterministic evaluator + adversarial tests) → E2 (model evidence
   acquisition evaluation) → P1 (independent policy review) → Q1
   (qualification execution) → W1 (separate production wiring approval,
   only if qualified). No phase may redefine its acceptance criteria
   because the implementation failed (CLAUDE.md: the benchmark working
   is not a defect to be fixed in the benchmark).
6. **An explicit trust-boundary model** (§3): five epistemic layers
   (internal structural integrity / provenance consistency / independent
   source authenticity / completeness of published evidence / truth of
   the underlying commercial claim), with the exact set of conclusions
   the system may safely reach from recorded evidence alone, and the set
   that requires independent source verification or human review. A
   valid digest alone does NOT establish source authenticity; a
   publisher's completeness claim does NOT establish physical
   completeness; the system claims neither.

**Recorded findings that shape the design (details §2.6):**

* **CF-1** — The task matrix places "conflicting secondary extraction
  cues" under CONTRADICTED; the frozen approved contract derives
  UNPROVEN for candidate self-contradiction (P3 D8 / U12; R1 matrix row
  8). The design keeps the frozen semantics and places the row under the
  UNPROVEN category with the conflict documented. No contract change.
* **CF-2** — The FU4 module and the R1 record adapter are NOT
  content-pinned by any test literal at the starting SHA (verified:
  neither working-tree digest appears in `tests/` or `docs/`). The
  program qualifies an implementation whose identity is not file-pinned.
  A bounded correction phase (C0) is required BEFORE Track A execution,
  following the R1-FU1 / R2-FU1 precedent exactly.
* **CF-3** — "Valid duplicate constituent quantities": under the frozen
  materiality grammar (P3 §3.7 — a multiset of `(quantity, item)` pairs,
  no merging of repeated item tokens), two sides publishing
  `1x RAM + 1x RAM + 1x CPU` vs `2x RAM + 1x CPU` are
  T-DIFF-MATERIAL ⇒ CONTRADICTED (both ESTABLISHED), while byte-identical
  duplicate phrasings are T-AGREE ⇒ PROVEN-eligible. The matrix carries
  both shapes under their frozen-contract outcomes, with the grammar
  behavior recorded as a future T5 version decision (O-4).
* **CF-4** — "Asymmetric published quantity" splits, under the frozen
  contract, into UNPROVEN (no attestation — U18) and PROVEN-eligible
  (verified quantity attestation on the missing side —
  ATTESTED_NOT_MATERIAL). The matrix carries both arms.
* **CF-5** — "Semantic NO_MATCH with apparently equivalent Bundle
  composition": the unit axis is decision-independent under the frozen
  contract; where the composition IS attested-equivalent, the unit
  derives PROVEN even under a NO_MATCH scripted context, while the tier
  remains non-automatic (the frozen S2-A derivation grants no automatic
  tier on a NO_MATCH). The matrix labels the axes separately, making the
  independence an explicitly measured property rather than an assumption.

**Authority of this document.** DESIGN ONLY. It specifies, it does not
authorize execution. Every phase in §9 starts only after (a) the
pending independent reviews of the lineage it builds on (Q3-B5-P4-FU2,
R1, R1-FU1, R2, R2-FU1) are ratified, and (b) ChatGPT's independent
review of THIS document explicitly approves the phase's bounded scope.
ChatGPT remains the final architecture and approval gate.

---

# 2. Current-state source inventory

Every entry below was re-verified at the starting SHA
`3bf6eb294df3ca83b93665158297f97abf3fba4b` this session. File digests are
SHA-256 of the WORKING-TREE bytes (the house pin convention — see the
autocrlf note in §2.7). The baseline collection was re-verified:
**7574** (`pytest --collect-only`; per-file sum).

## 2.1 The FU4 contract of qualification (research layer)

* `product_intelligence/research/semantic_authority_fu4.py` (working-tree
  digest `0a0fb3d7760208b03ca54b7e12e35e8fa9bed81e0e09898252b4cecb2cf81
  bc4`; committed blob at HEAD `482a637477dd24dfbb1051f714ab087b96061f80
  c8617ce8adb421a4edb5c09f`, 167,523 bytes LF / working tree 171,137
  bytes CRLF — §2.7) — **the contract this program qualifies.**
  `AUTHORITY_CONTRACT_VERSION_V2_FU4 = "SEMANTIC_AUTHORITY_V2_S2A_FU4"`
  (line 285); `KNOWN_AUTHORITY_CONTRACT_TOKENS_FU4 = {FU2, FU3, FU4}`
  (line 300); `BUNDLE_COMPOSITION_EVIDENCE_VERSION_FU4 = 3` (line 326);
  the five-way `BundleCompositionStateV2FU4` (line 361); the attestation
  records `CompositionCompletenessAttestationV2FU4` (line 562) /
  `QuantityCompletenessAttestationV2FU4` (line 693) with
  `canonical()` / `verify()`; the candidate record
  `CandidateBundleCompositionEvidenceV2FU4` (line 814 — the v3 embedded
  original-result field; constructor as validator, line 914 ff.); the
  target record `TargetSalesUnitEvidenceV2FU4` (line 1245); the versioned
  clause machinery — `extract_published_bundle_clause` (line 1542), the
  `_INCOMPLETE_MARKERS` / `_COMPLETENESS_MARKERS` lists (lines 1577 /
  1604), `classify_clause_closure` (line 1692), the materiality grammar
  (`_full_parse_clause`, line 1873; `_textual_relation`, line 1901); the
  construction entry points `candidate_composition_from_extraction`
  (line 2093) / `candidate_composition_from_channel` (line 2318); the
  decision record `AuthorityDecisionV2FU4` (line 2415 — the FU3 field
  set + the six bundle-axis audit fields, constructor invariants at
  line 2447); the presentation gate `_verify_candidate_composition`
  (line 2590 — the v3 four-step original-result chain) and
  `_verify_target_evidence` (line 2787); the unit derivation
  `derive_sales_unit_authority_fu4` (line 2815 — the U0–U21 table) and
  case-level `derive_sales_unit_authority_fu4_case` (line 2900); the
  tier derivation `derive_authority_tier_fu4` (line 3231 — frozen S2-A
  derivation + bound + unit + the two restrict-only ceilings); the
  superset dispatch `derive_authority_tier_for_contract_fu4` (line 3347
  — FU2 / FU3 arms delegate byte-identically).
* `product_intelligence/research/semantic_authority_fu3.py` (digest
  `4ea529452e50a62b63778c97e37856f5660a0c5426654d7918725b3d59e24c0f`,
  56,426 bytes, pinned in the FU4 suite A1 table) — the frozen firewall:
  `SalesUnitAuthorityV2` (line 445), `TargetSalesUnitEvidenceV2` (line
  549 — the frozen three-field target record the FU4 record succeeds),
  `sales_unit_authority_from_channel` (line 600), the two restrict-only
  ceilings, `derive_authority_tier_for_contract` (line 1085).
* `product_intelligence/research/semantic_authority_v2.py` (digest
  `78301d308e0a5e748c2a22cd8785c673b7c2230b54cc60f4714ee2da6b74d8a5`,
  125,215 bytes CRLF working tree, pinned) — the frozen S2-A contract:
  `AuthorityTier` vocabulary, the 27-entry tier matrix,
  `PRICING_ELIGIBLE_TIERS = {MACHINE_VERIFIED, AI_ASSISTED_COMPARABLE,
  HUMAN_CONFIRMED}` with the import self-check that `NEEDS_REVIEW` is
  never pricing-eligible, `IdentityStateAssessmentV2` (line 643 — the
  scripted-context record Track A cases carry), `SemanticEvaluationV2`
  (line 1872 — the bounded scripted evaluation document).
* `product_intelligence/research/sales_unit_extraction.py` (digest
  `0dd6016503292a926d86f3dbafa97e59a713a4386df2a648882e4942cc6737b6`,
  65,724 bytes, pinned) — the frozen P2 extraction (schema v1):
  `SalesUnitExtractionResult` (line 544) with `canonical()` /
  `verify_integrity()` (line 793 — both digests + cue-span containment),
  the cue table `_CUE_MASTER` (line 309 — bundle forms: count-only ⇒
  `AMBIGUOUS_CUE` / `BUNDLE_WITHOUT_CONTENTS`; marker forms ⇒
  established BUNDLE cue with the span over the published contents
  clause), `extract_sales_unit_evidence` (line 1260),
  `sales_unit_channel_from_extraction` (line 1349 — the frozen lossy
  mapping: `OBSERVED_UNAMBIGUOUS` ⇒ channel over the primary established
  cue's published text; every other state ⇒ canonical `UNAVAILABLE`).
  This is the EVIDENCE-ACQUISITION layer the corpus's extraction evidence
  documents are recorded through (its recorded output is evidence, not a
  label — §4.6).
* `product_intelligence/research/semantic_v2.py` (digest
  `d573d8086bc51db1653f99cebe42aa476ff954fc9d582f8f014ec2d4a97e7d7d`,
  pinned) — the frozen S2-C input contract: `SemanticMatchCaseV2` (line
  913 — the recorded V2 input; the channel lives at
  `candidate_commercial.sales_unit`), `CandidateSalesUnitEvidenceV2`
  (line 448 — the five-field channel whose `canonical()` document is the
  `channel_content_digest` bound), `SemanticMatchResponseV2` (the strict
  7-key output: decision / confidence / reason_code / matched_attributes
  / conflicting_attributes / missing_critical_attributes /
  conflict_classes), `SemanticAttributeDimensionV2` (bounded dimensions
  incl. `BUNDLE` / `PACKAGING_QUANTITY`), `SalesUnitKindV2`
  (SINGLE_UNIT / PACK_QUANTITY / TRAY_OR_FACTORY_PACK / BUNDLE).

## 2.2 The R1 record / codec / replay surface (registered at R1)

* `product_intelligence/research/semantic_decision_v2_fu4.py` (working-
  tree digest `c1037a5a987ee7a1674de0d9736ec9670ef13737e092a857b643ea70
  548d1224`) — **the R1 adapter, the record-surface target of Track A.**
  `V2_FU4_CONTRACT_BINDING = ("V2","2.1",1,1,"SEMANTIC_AUTHORITY_V2_S2A_
  FU4")` (line 296); `V2_FU4_AUTHORITY_QUALIFIED = False` (line 323 —
  registration is NOT qualification, pinned False by the R1 suite); the
  typed record `SemanticDecisionRecordV2FU4` (line 531 — the V2 field
  set + the FULL `AuthorityDecisionV2FU4` derived audit surface + the
  version-owned `authority` section: the v3 candidate record WITH the
  embedded original result, the target evidence under the explicit
  `absent / frozen_fu3 / fu4_v3` discriminator, the quantity attestation
 ); the strict payload codec (`_decode_v2_fu4_payload`, line 2213 — exact
  key sets, field-by-field evidence decode through the FU4 constructors,
  round-trip document identity); the zero-live replay
  (`_replay_v2_fu4_record`, line 2694 — the presentation gate re-run via
  the derivation + re-derivation + full derived-agreement proof); the
  registered instance `SEMANTIC_V2_FU4_ADAPTER` (line 2958).
* `product_intelligence/research/semantic_decision_codec.py` (digest
  `c0cef216d72e528ba8b17daa7adbb941f9ac328b42f02eb8dc4f00fdaa68bd3d`,
  content-pinned at the R1 endpoint by R1-FU1) — the universal codec
  with the DEC-9 claim-based disambiguation; the registry is exactly
  `(SEMANTIC_V1_ADAPTER, SEMANTIC_V2_ADAPTER, SEMANTIC_V2_FU4_ADAPTER)`
  (line 158 ff.); `supported_contract_bindings()` = exactly
  `(V1, 2.0/FU2, 2.1/FU4)`.
* `product_intelligence/research/semantic_decision_replay.py` (digest
  `481f58aecf08893f0aab683a620bf25a41960e529f40ae197be06be1e272f803`,
  pinned) — the universal zero-live replay gate; byte-unchanged by R1 /
  R2; `SUPPORTED_CONTRACT_BINDINGS` derived from the codec registry.
* `product_intelligence/research/semantic_decision_record.py` (digest
  `40517aedb5fbcb3e6ad9eac117308f67bd12979ac9691a81c635c75129d0f4fd`) —
  the envelope foundation (`canonical_sha256`, the bounded error
  vocabulary, the adapter extension point).
* `product_intelligence/research/semantic_decision_v2.py` (digest
  `9176380cc67090b1b799e7f9ad1640e5f2858ea1b9680897ff3cb7ad5f4cffeb`,
  pinned) — the frozen V2 adapter / record type (pins 2.0/FU2);
  `V2_AUTHORITY_QUALIFIED = False` (pinned location 1).

## 2.3 The live runtime and prompt contracts (byte-frozen; the Track B
prompt axis)

* `product_intelligence/semantic/contract_v2.py` (digest
  `d1a69692f57ece6bab8362e77c7067a9642f214d2b115403c1638fe537aa7492`,
  pinned) — frozen Prompt 2.0 (system-text digest `c0cc98bd…`).
* `product_intelligence/semantic/contract_v2_1.py` (digest
  `d9e564ef1824b55e31a2096082feff2e5d7d7df42154b4845785f4d846617ea4`,
  R2-endpoint content-pinned) — Prompt 2.1 owner:
  `V2_1_CONTRACT_BINDING` (2.1/FU3, byte-unchanged) +
  `V2_1_FU4_CONTRACT_BINDING` (the registered FU4 successor binding,
  DEC-6); `SYSTEM_PROMPT_V2_1` (system-text digest `e2949e75…18fc`); the
  COMMERCIAL SALES-UNIT RULES the model side of Track B speaks to.
* `product_intelligence/semantic/runtime_v2.py` (digest
  `e0791384a218409a1e390e304cfc6da1d0e002b404955722b94d557b8c02cc36`,
  pinned) — the live V2 runtime: pinned route (PRIMARY `amax` /
  `qwen3.8-27b`, FALLBACK `vllm-262k` / `Qwen3.6-27B-262K`);
  `V2_AUTHORITY_QUALIFIED = False` (pinned location 2); executes the
  frozen 2.0 builder. **No live 2.1 / FU4 execution path exists; this
  program creates none** (W1 is the separate gate).

## 2.4 The semantic qualification harness (byte-pinned; the pattern
source, NOT the extension target)

* `product_intelligence/evaluation/semantic_v2/corpus.py` (digest
  `4c0851a82b2f0863a16938c419e49938c86c1494aefbbde03684e496ee4fb4e4`,
  R2-endpoint pinned) — strict corpus loading: `CORPUS_SCHEMA_VERSION =
  1`; `BINDING_CORPUS_VERSIONS` = exactly the three production seals
  (2.0/FU2→1.0.0, 2.1/FU3→1.1.0, 2.1/FU4→1.2.0); the exact corpus-
  document key set; per-case strict decode with the REAL
  `SemanticMatchCaseV2` constructor as arbiter (`decode_match_case`,
  line 574 — the public entry the new family reuses read-only); per-case
  and whole-corpus digest verification; the `label_revisions` A–D
  reason-class rules; `build_manifest_document` / `verify_manifest`.
* `product_intelligence/evaluation/semantic_v2/fixtures.py` (digest
  `ac8777dc27cdf879415645a04468690366d5d92f515c67fe7f794482cb0c783f`,
  R2-endpoint pinned) — the auditable corpus-source pattern: declarative
  case definitions running the exact frozen chain; regeneration must
  reproduce the committed artifact byte-for-byte.
* `product_intelligence/evaluation/semantic_v2/gates.py` (digest
  `a441ada2a275983f15ddb39f770c4163a42c4f95255c99f7565ea6d83c582e3f`,
  R2-endpoint pinned) — the eight mandatory hard gates + the `decide`
  ladder (`FAIL_CLOSED > NOT_QUALIFIED > POLICY_PENDING >
  INCOMPLETE_COVERAGE > THRESHOLD_INDETERMINATE > BELOW_THRESHOLD >
  QUALIFIED`) — the pattern for §7.
* `product_intelligence/evaluation/semantic_v2/report.py` (digest
  `45626ae166cf6ba0e4818357dc65363bf837503153a78764b518a7294f6a8619`,
  R2-endpoint pinned) — the report contract: the `contract` section
  (real system-prompt digest of the bound version), the `authority`
  section (`granted: false` + the evaluation-evidence-only note),
  `verify_report` / `verify_direct_report`.
* `product_intelligence/evaluation/semantic_v2/policy.py` (digest
  `af951180594a4e10cba64db22be114e4bd4b03bb204179c689bef20617e387f4`,
  pinned) — the policy artifact contract: the DRAFT / APPROVED status
  discipline (`approved_by` + `approved_utc` required for APPROVED),
  `policy_applies_to` (corpus_id + corpus_version), `evaluate_thresholds`
  (insufficient denominator ⇒ `met: null`, never satisfied by default).
* `product_intelligence/evaluation/semantic_v2/evaluator.py` (digest
  `e56fc6778243d24f160fcc947415287f13b9f97fcf66f379d6f967d7230b8ae2`),
  `capture.py` (`4da8b79a…`), `direct_capture.py` (`58b79087…`),
  `cli.py` (`e4853546…`) — the offline evaluation / capture / CLI
  patterns (the direct-capture document schema, the route pinning, the
  corpus binding of a capture by id / version / digest + prompt axis —
  the pattern Track B's capture loader follows, §6.4).

## 2.5 The corpus artifacts of record and the committed baselines

| Artifact | State at the starting SHA |
| --- | --- |
| `evaluation/semantic_v2_qualification/corpus_v1.json` + `manifest_v1.json` | 1.0.0, 56 cases, sealed under 2.0/FU2, corpus digest `2c37ba08…`; byte-pinned (A1 `CORPUS_ARTIFACT_PINS`). |
| `evaluation/semantic_v2_qualification/corpus_2_1.json` + `manifest_2_1.json` | 1.1.0, 56 cases, sealed under 2.1/FU3, corpus digest `14396eae…`; byte-pinned. |
| `evaluation/semantic_v2_qualification/corpus_2_1_fu4.json` + `manifest_2_1_fu4.json` | 1.2.0, 56 cases, sealed under 2.1/FU4, corpus digest `582b35bbee93959eaa5a598fa579cd99229e550e37f3c6cd970f7774ed9d1b91`, manifest digest `972ba35428d1dfc0a4b07d2027d9186577cf398a3ba4dc96dc61865b9843d8d7`. The manifest's `statement` key says verbatim: "Corpus 1.2.0 is a binding-registration and semantic-compatibility corpus. It does not independently qualify FU4 Bundle composition authority." — **the gap this program fills.** |
| `evaluation/semantic_v2_qualification/policy/qualification_policy_draft_1.json` | DRAFT (`approved: false`), applicable to corpus **1.0.0 only**; file digest `6bc30d37…`, byte-pinned. |
| `evaluation/semantic_v2_qualification/reports/{q3a_baseline, q3b5_baseline_2_1, q3b5_p5_baseline_1_2_0}/` | the committed no-capture baselines (2.0 / 2.1 / FU4 lineages; all `POLICY_PENDING`, `granted: false`). |
| `tests/fixtures/pages/*.html|json` | the recorded real retail pages (Samsung / OEMPCWorld / EXXACTCorp / DirectMacro / Micron 7500 catalog) — the in-repository RECORDED_FIXTURE ground. **None publishes bundle contents** (verified: zero `bundle` occurrences in the page fixtures); the recorded P2 extraction over them is the recorded absence. |
| Q3-B capture evidence (untracked, gitignore-protected) | the real primary capture `q3b-20261009T010312Z-amax` (43/43 OK; 0 MATCH) — the precedent for Track B's controlled-capture discipline; NOT part of any corpus. |

The three semantic-corpus sales-unit cases (0032 / 0033 / 0034) are all
conflict shapes against the DEFAULT single-unit target; the committed
corpus contains NO attested-composition case — the FU4 PROVEN path
(U19 / U20) is exercised today only at the research / record level
(217 + 38 + 35 test nodes), never by an independently labeled corpus
case. That asymmetry is the precise qualification gap.

## 2.6 The test suites of record (node counts at the starting SHA)

| Suite | Nodes | Role for this program |
| --- | --- | --- |
| `tests/research/test_semantic_authority_v2_fu4.py` | 217 | The FU4 contract suite (A1 pins, A2 delegation identity, A4 registries / reachability, A7 two-token coexistence, B1–B12 evidence schema, C1–C12 comparison rules, D1–D3 tier / overlay, E1–E2 contract-phase registries, F1–F4 never-infer). The behavioral evidence the contract implements its design; NOT the qualification (its labels are the implementation's own pins). |
| `tests/research/test_semantic_decision_v2_fu4.py` (R1) | 38 | The record / codec / replay layer: the §9.1 P5 matrix (B1–B9 rows: the PROVEN / UNPROVEN / CONTRADICTED paths over constructed records, forged attestations, tampered embedded results, cross-listing substitution, wrong bindings, the exhaustive restrict-only sweep, zero-live). |
| `tests/evaluation/semantic_v2/test_q3b5_p5_fu4_registration.py` (R2) | 35 | The qualification-layer registration: the 1.2.0 seal, the harness registry, the baselines, the firewall rows, the R2-endpoint module pins. |
| `tests/research/test_semantic_authority_v2_fu3.py` | 98 | Frozen firewall suite (byte-pinned). |
| `tests/research/test_sales_unit_extraction.py` + `…_recorded_pages.py` | 111 + 7 | Frozen P2 extraction suites (byte-pinned). |
| `tests/evaluation/semantic_v2/test_q3b5_p1_*` + `test_q3a_*` | 20 + 20 + 19 + (Q3-A suites) | The binding / replay / corpus-2.1 / adversarial / harness suites. |
| codec / replay / record / V2 / boundaries suites | 55 / 31 / 47 / 61 / 50 / 32 | The universal envelope suites. |
| **Full collection** | **7574** | re-verified this session; skipped / xfailed / deselected 0 / 0 / 0 at the R2-FU1 endpoint record. |

## 2.7 Findings of record (design-time inspection results)

* **CF-2 (pin gap — forces phase C0).** No test literal pins the content
  of `semantic_authority_fu4.py` (working-tree digest `0a0fb3d7…` /
  committed blob `482a6374…`) or of
  `semantic_decision_v2_fu4.py` (`c1037a5a…`) anywhere in `tests/` or
  `docs/` (verified by exhaustive grep for both digests). The FU4 suite's
  A1 `FROZEN_MODULE_PINS` table (11 rows) pins the frozen INPUTS; the R1
  suite pins the codec at its R1 endpoint; the R2 suite pins the six
  R2-owned modules — but the two files that ARE the qualified surface
  carry no file-content pin. The same gap class R1-FU1 (the codec) and
  R2-FU1 (the six R2 modules) closed by their recorded corrections.
  Consequence: qualification results over an unpinned implementation
  identity are only as strong as the pin; C0 restores the contract
  before any Track A execution (§9.2).
* **The autocrlf checkout-state note.** The repository is checked out
  with `core.autocrlf=true` + `* text=auto`. Some working-tree files are
  CRLF expansions of their committed LF blobs (e.g.
  `semantic_authority_v2.py`: committed `04c7be7a…` / working tree
  `78301d30…` — the pin literal is the WORKING-TREE digest, and
  `git diff` normalizes, so the expansion is invisible to git status).
  The house pin convention is: pin literal = SHA-256 of the working-tree
  bytes at the pinning phase's starting SHA, with the working tree
  verified `git diff`-clean against that SHA. C0 follows the convention
  and, for robustness, records BOTH the committed-blob digest (LF) and
  the working-tree digest (machine state) in the pin's comment, asserting
  the working-tree value per the house convention (§10 risk R-C1-2).
* **The lineage review state.** At the starting SHA, Q3-B5-P4-FU2 (the
  FU4 module's final correction), R1, R1-FU1, R2, and R2-FU1 are all
  PENDING INDEPENDENT REVIEW (STATUS current state). This design builds
  on that lineage; its execution phases are gated on the ratification of
  these reviews (§9 stop conditions) — the same sequencing discipline as
  P5 design B-1.
* **No conflict between the frozen implementation and the approved
  designs** was found at the source level for the surfaces this program
  qualifies: the FU4 module implements the corrected P3 design (U0–U21,
  D6 / D19 / D20 conjunctions, the v3 presentation gate) as specified;
  the R1 adapter implements the P5 §4.2 record contract as specified;
  the digests of the frozen inputs match their recorded pins. The two
  conflicts that DO exist are between the TASK MATRIX and the frozen
  contract (CF-1, CF-3) — resolved in favor of the frozen contract with
  documentation, never by redefining the implementation.

---

# 3. Explicit authority and trust boundaries

## 3.1 The five-axis separation (the mission's required distinction)

The qualification program measures five questions that the system
answers with five different kinds of evidence, and it must never conflate
them:

| Axis | Question | Answered by | NEVER answered by |
| --- | --- | --- | --- |
| 1. Semantic product identity | "Is the candidate the same product as requested, at what resolution?" | the deterministic 3C identity assessment + the (scripted, in Track A / model-produced, in Track B) semantic evaluation | bundle composition facts; pricing facts |
| 2. Bundle composition equivalence | "Are the candidate's and target's commercial bundle compositions proven equivalent / contradicted / unproven, as published and as attested?" | the FU4 unit derivation over the recorded channel + evidence records + quantity attestation (the v3 presentation gate) | the semantic decision (MATCH or NO_MATCH); the model's attribute detail; MPN identity; price |
| 3. Sales-unit quantity equivalence | "Is the published bundle quantity axis consistent, both-unpublished, attested-not-material, contradicted, or undetermined?" | the determined `BundleQuantityAxisStateV2FU4` recorded on every bundle comparison | inference from item counts, MPN, price, absence, model output (D17 / D20) |
| 4. Authority tier eligibility | "What workflow tier does the scripted context + the unit state derive under FU4?" | the frozen S2-A derivation + the restrict-only ceilings | any axis 1–3 fact outside the signature-pinned inputs; human overlays (explicit, outside the derivation input in Track A) |
| 5. Pricing eligibility | "Can the derived tier enter a price statistic?" | `tier ∈ PRICING_ELIGIBLE_TIERS` AND the absence of any pricing consumer reading FU4 states (W1 pending) | a PROVEN unit alone (the W1 guard does not exist yet); a MATCH alone; an attestation alone |

**I-1 (the headline invariant, restated as a measured property).** Axis 1
is never sufficient for axes 2–5: a correct semantic MATCH over a
bundle candidate with unattested / missing / partial composition derives
UNPROVEN (axis 2), caps the automatic tier at NEEDS_REVIEW (axis 4), and
leaves pricing non-eligible (axis 5). Matrix rows B10 / D13 / D11 are
the labeled instances; the evaluator's perturbation check (I-4) proves
the signature-level independence over the whole corpus.

**I-2 (decision independence of the unit axis).** Axis 2 is never
sufficient for axis 1, and axis 1's outcome does not feed axis 2: an
attested-equivalent composition under a NO_MATCH scripted context still
derives PROVEN on the unit axis (row D12, CF-5) — recorded so that a
future consumer cannot read "NO_MATCH" as "the bundle was disproven" or
"PROVEN" as "the products match."

**I-3 (the provenance firewall).** No member of either evidence
provenance vocabulary is a model claim (P3 scope box 1): candidate-side
composition facts come from the frozen extractor's recorded cues or the
recorded channel; target-side facts from the two frozen non-model
attestation classes; attestations from the subject's own published
statement or the review process. The corpus encodes this as a loader
invariant: a case whose evidence documents name a model source is
rejected at seal time (§4.4).

**I-4 (structural model-independence of the derivation).** The unit
derivation's inputs are signature-pinned (channel + candidate
composition record + target evidence + quantity attestation); the
evaluator verifies over every Track A case that perturbing the scripted
evaluation (decision / confidence / conflict classes / matched
attributes) leaves the unit + quantity-axis + composition-state outputs
unchanged. Any violation is a `NOT_QUALIFIED` gate failure (G2 family)
— not a label correction.

## 3.2 The five-layer evidence authenticity boundary

The program distinguishes, and the report states per conclusion, which
layer of evidence each conclusion rests on:

| Layer | Name | What it is | What the system can verify from recorded evidence | What it CANNOT establish |
| --- | --- | --- | --- | --- |
| L1 | Internal structural integrity | the document's own digests / canonical round-trip / constructor invariants | "this document is exactly the bytes its digest covers; it has not been modified since sealing" (re-computed digests, cue-span containment, round-trip identity) | that the content was ever published anywhere |
| L2 | Provenance consistency | the cross-record association chain (channel_content_digest binding; extraction anchor equality; the frozen P2 mapping equality; the recomposed-against-record equality; subject-side / basis / source-class coherence; the route pins) | "this composition record is EXACTLY the construction over this presented channel / embedded original" — within the frozen channel-granularity bound (P5 R-5: two content-identical publications are indistinguishable at channel level) | which physical listing / page the channel came from when the channel content alone does not distinguish them |
| L3 | Independent source authenticity | that the recorded text was actually published at the cited URL by the cited seller / manufacturer at the recorded retrieval instant | ONLY the recording act's own integrity: the archived raw content file's digest + the retrieval metadata (URL, retrieved_utc, raw reference) + the human / operator attestation that the archive was captured from the cited source at the cited time | the truth of the retrieval attestation (a forged archive is L1-valid and L2-consistent and still false); the continued existence or current state of the source |
| L4 | Completeness of published evidence | that the attested clause enumerates the bundle's COMPLETE commercial composition, AS PUBLISHED | the attestation record's L1 / L2 integrity + the bounded basis (the subject's own published statement detected from recorded text, or the review's recorded determination) | physical completeness — a publisher's "complete list" statement is a PUBLISHED claim (L3-attested, L4-as-published), not a verified fact |
| L5 | Truth of the underlying commercial claim | that the physical bundle contains what the publication says | NEVER. The system claims nothing at L5. | — |

**The safe-conclusions statement (binding for the report and for any
future consumer):**

* From recorded evidence alone (L1 + L2, with the L3 recording act
  attested by a human at capture time), the system may safely conclude:
  (a) the unit state the derivation returns (PROVEN_EQUIVALENT = "the
  candidate is published as sold in the same commercial unit as the
  target, each side's completeness independently attested, as recorded";
  UNPROVEN = "the recorded evidence does not establish equivalence — the
  safe abstention"; CONTRADICTED = "the recorded publications state
  incompatibility"); (b) the evidence-integrity refusals (a presented
  record that is not the exact construction over its presented channel /
  original is refused — substitution / forgery DETECTED at the recorded
  level); (c) the tier consequence under the scripted context, with the
  ceilings.
* Requiring independent source verification or human review: (a) any L3
  claim beyond the archive's own integrity (the source actually said
  this — verified by a reviewer against an independent retrieval, not
  against the archive); (b) any target-side REVIEWED attestation's
  independence (that the review verified against the target's own
  source rather than copying the candidate's publication — the T3 / T3'
  boundary: a copied unverified attestation is a review-governance
  failure the contract cannot detect; the audit surface records both
  attestations for the reviewer); (c) any quantity attestation's
  correctness (a mistaken non-materiality determination produces a
  PROVEN over a real unit difference — the T10 boundary: the failure is
  the record's, not the derivation's); (d) any L5 conclusion (physical
  contents) — reserved to human verification, never the system's.
* Explicitly NOT claimed, and NOT to be invented: cryptographic trust in
  the source (no signature / certificate / notarization capability
  exists in this repository — the digest chain proves consistency with
  the recorded archive, not authorship); timestamp trust beyond the
  recorded `retrieved_utc` field; or any verification of a URL's current
  content. The design refuses to add any such capability implicitly:
  if a future tier needs it, it is its own separately approved
  capability with its own evidence, not a reinterpretation of this
  program's results.

## 3.3 The authority boundaries (what this program may and may not touch)

* **Read-only over the qualified surface.** Track A imports the frozen
  derivation / constructors / codec / replay entry points and the
  frozen S2-C / P2 types. It never modifies them; their identity is
  established by the C0 pins + the existing A1 / R1 / R2 pins, and the
  E1 acceptance re-verifies all pins pass.
* **No production wiring.** The program creates no live execution path,
  no pricing consumer, no runtime reference to FU4 states, no
  `V2_AUTHORITY_QUALIFIED` / `V2_FU4_AUTHORITY_QUALIFIED` flip. The
  existing reachability guards (no live module references the FU4
  contract / record surface) are re-run unchanged and must pass at every
  phase's acceptance.
* **No semantic-harness extension.** The `evaluation/semantic_v2/*`
  modules are R2-endpoint content-pinned; the new family is a NEW
  package (§4.1) that reuses patterns and the frozen research public API,
  never the pinned harness files. The eight semantic gates, the DRAFT
  policy, and the three semantic corpus seals are untouched by any phase
  of this program.
* **No prompt change.** Track B runs the frozen Prompt 2.1 (system-text
  digest `e2949e75…18fc`). No 2.2, no annotation, no bundle-specific
  prompt text is proposed by this design; the model's bundle duties are
  exactly the 2.1 COMMERCIAL SALES-UNIT RULES.
* **The label independence boundary.** Expected outcomes are
  implementation-independent by construction (§4.6): authored from the
  recorded source content + the approved design tables (cited) + human
  review; sealed before the evaluator exists (C2 precedes E1); and
  mechanically checked (anti-derivation import scan + provenance field).
  The implementation is measured against the labels, never the reverse.

---

# 4. Proposed corpus schema

## 4.1 The new corpus family (DEC-C1-1)

A NEW corpus family, separate identity, separate versioning, separate
seal — corpus 1.2.0 is not modified, extended, or reinterpreted:

* `corpus_id`: `PI-FU4-BUNDLE-AUTHORITY-QUALIFICATION` (proposed — O-1).
* First version: `1.0.0`. Versioning discipline (family-owned, mirrors
  the semantic family's): the corpus document is sealed per version;
  case additions that change no existing per-case document = next minor
  (1.1.0); any label / case-document change = new version WITH
  `label_revisions` entries under the A–D reason classes (the
  semantic-family rule, adopted verbatim); a binding-only re-seal under
  a successor authority token (e.g. a future FU5) = new minor with
  exactly `{corpus_version, semantic_contract_binding, corpus_digest}`
  moved. The loader enforces the version↔binding seal exactly as
  `semantic_v2/corpus.py` does: `BINDING_AUTHORITY_CORPUS_VERSIONS =
  {FU4 binding → "1.0.0"}` (family-owned registry; the semantic
  family's `BINDING_CORPUS_VERSIONS` is NOT extended).
* `corpus_schema_version`: 1 (family schema — the case document shape of
  §4.4 is version 1; any change is a new schema version, never a silent
  edit).
* `corpus_label` (proposed): `fu4-bundle-authority-qualification-v1`.
* Created-utc: set at the C2 seal (the first sealing instant of the
  family — not backdated to the semantic family's creation).
* Statement (inside the manifest digest, the 1.2.0-manifest precedent):
  "Corpus 1.0.0 (family
  PI-FU4-BUNDLE-AUTHORITY-QUALIFICATION) is the independently labeled
  FU4 Bundle composition authority qualification corpus. It is not the
  semantic model qualification corpus (family PI-SEMANTIC-V2-
  QUALIFICATION, versions 1.0.0–1.2.0); it does not label semantic
  decisions; and it does not by itself qualify any model for production
  authority — the decision ladder of the family report governs."

## 4.2 Versioning, storage, and integrity architecture (DEC-C1-2 / C1-10)

* **Storage layout** (proposed — O-1):

```
evaluation/fu4_bundle_authority_qualification/          NEW directory
  corpus_v1.json                the sealed family corpus 1.0.0
  manifest_v1.json              the per-case manifest (schema 1, statement + lineage keys)
  policy/qualification_policy_draft_1.json   family DRAFT policy (C2/P1 artifact)
  reports/q3c_e1_baseline/      committed Track A baseline reports (E1)
  reports/q3c_e2_baseline/      committed Track B no-capture baselines (E2)
  sources/                      recorded source content for RECORDED_FIXTURE / REAL_MARKET cases
    <case_id>/raw_content.{html|json}   byte-archived published content
    <case_id>/retrieval_attestation.json  url, retrieved_utc, raw reference, attestor identity
tests/evaluation/bundle_authority/                  NEW test directory
  test_q3c_c1_corpus_integrity.py
  test_q3c_c2_label_governance.py
  test_q3c_e1_track_a.py
  test_q3c_e2_track_b.py
product_intelligence/evaluation/bundle_authority/    NEW evaluation package
  __init__.py  corpus.py  fixtures.py  capture.py  evaluator.py
  gates.py  policy.py  report.py  cli.py
```

  The semantic family's `README.md` is NOT touched; the new directory
  carries its own README (C2 deliverable) stating what the family is and
  is not.
* **Digests.** Canonical form = sorted keys, compact separators, ASCII,
  no floats (the house `canonical_sha256` discipline). Per-case digest =
  SHA-256 over the case document minus `case_digest` (the semantic
  family's per-case rule). Corpus digest = SHA-256 over the canonical
  corpus state view (all per-case digests + version + binding + id +
  schema + created + label revisions). Manifest = schema 1 (the
  semantic family's manifest shape + the `statement` / `lineage`
  additive keys the R2 seal introduced; `lineage.derived_from_*` = null
  for the family's first version).
* **Artifact integrity checks (C1 validator + E1 acceptance).**
  (a) the sealed corpus loads only under the exact FU4 binding (the
  family seal registry); (b) every per-case digest re-verifies; (c) the
  corpus digest re-verifies; (d) the manifest verifies against the
  corpus; (e) regeneration from `fixtures.py` reproduces the committed
  artifact byte-for-byte (the P1 property, family version); (f) the
  evidence documents inside cases (channel, composition records,
  attestations, extraction results) decode through the REAL frozen
  constructors (constructor-is-validator; a case carrying an
  un-constructible evidence document is a corpus-integrity failure at
  load — `FAIL_CLOSED`); (g) for RECORD-surface cases, the embedded
  payload document decodes through the REAL universal codec
  (`decode_semantic_decision_record`) at load time — a corpus whose
  record cases do not decode is void.
* **Source evidence storage.** SYNTHETIC cases: the published content is
  the by-construction text inside the case document (no external file;
  the case IS the ground truth of its own construction). RECORDED_
  FIXTURE cases: the in-repository recorded page / catalog fixture is
  cited by path + file digest in the case's `source` block (the fixture
  file itself stays where it is — no duplication). REAL_MARKET cases:
  the archived raw content + retrieval attestation live under
  `sources/<case_id>/`, cited by path + digest in the case document
  (C3 deliverable; the archive is committed so the case is reproducible
  offline). The loader re-verifies every cited file digest at load.
* **Deterministic reproduction.** The entire Track A baseline is
  reproducible offline from the committed corpus + the C0-pinned
  implementation identity: `cli evaluate-a --corpus <sealed> --out-dir
  <dir> --generated-utc <T>` must reproduce the committed baseline
  byte-for-byte at the pinned SHA (the P1 regeneration property, family
  version; pinned by E1 test). Track B reproduction is over the
  committed capture documents (the model is not re-invoked — captures
  are evidence, the evaluator is pure).

## 4.3 The five-case classification (evidence kind × track × surface)

* `evidence_kind` (bounded, the semantic family's vocabulary adopted):
  `SYNTHETIC` (by-construction scenario; tests deterministic contracts;
  NEVER real-market accuracy evidence — stated per case and per report);
  `RECORDED_FIXTURE` (grounded in a recorded in-repository source: the
  `tests/fixtures/pages/*` pages, the Micron 7500 catalog, or a committed
  `sources/` archive with its retrieval attestation); `REAL_MARKET`
  (independently retrieved market listing, archived with retrieval
  attestation; the label additionally requires the independent source
  verification of §3.2-L3 by a reviewer — C3 gate).
* `track` (bounded): `A` (deterministic only), `B` (model-facing only),
  `A_B` (both — the shared recorded V2 case document serves Track A's
  scripted context AND Track B's model input).
* `surface` (bounded, Track A only): `DERIVATION` (the unit / tier
  derivation over recorded inputs), `RECORD` (the R1 payload decode +
  replay), `BOTH` (the derivation row plus its record-level twin —
  required for every matrix row that asserts a replay property).

## 4.4 The per-case document (schema 1, exact key set)

```
{
  "case_id":           "FA4-<CAT>-<NNN>"      (^FA4-[A-Z]{4}-[0-9]{3}$;
                                               CAT ∈ {PROV, UNPR, CONTR, ADV, DELE})
  "case_category":     <non-empty str>        (product category, free text —
                                               the semantic family's convention)
  "matrix_row":        "A1" | "A2" | ... | "D18"   (the §5 design-matrix row this
                                               case instantiates; traceability)
  "challenge_tags":    [ <bounded str>, ... ]  (e.g. "forged_attestation",
                                               "cross_listing_substitution",
                                               "semantic_match_unproven_bundle")
  "evidence_kind":     "SYNTHETIC" | "RECORDED_FIXTURE" | "REAL_MARKET"
  "track":             "A" | "B" | "A_B"
  "surface":           "DERIVATION" | "RECORD" | "BOTH"     (track A / A_B only)
  "source": {
     "target":  { "title_text": <str|null>, "structured_fields": {<str>:<str>},
                  "source_url": <str|null>, "retrieved_utc": <str|null>,
                  "raw_reference": <str|null>, "archive": <path|null>,
                  "archive_digest": <sha256|null>,
                  "recording_attestation": <str|null> }   # SYNTHETIC: url null,
                                                          # attestation "by-construction"
     "candidate": { same shape }
  }
  "recorded_case":     { "v2_case_document": <the EXACT SemanticMatchCaseV2
                          input document; decodes through the frozen
                          decode_match_case / constructor — the model-facing
                          input for track B, the channel owner for track A> }
  "derivation_inputs": {
     "channel":                  <the 5-field channel document; the loader
                                  enforces channel == recorded_case's channel>
     "candidate_composition":    <the v3 canonical document | null>
     "candidate_basis":          "EXTRACTION_RESULT_V1" | "RECORDED_CHANNEL" | "NONE"
     "extraction_evidence":      { "input_document": <canonical examined-input
                                     document | null>,
                                   "result_document": <SalesUnitExtractionResult
                                     canonical document (schema 1) | null> } | null
     "target_evidence":          { "schema": "absent" | "frozen_fu3" | "fu4_v3",
                                   "document": <canonical document | null> }
     "quantity_attestation":     <canonical document | null>
  }
  "scripted_context":   { "identity_assessment": <document>,
                          "evaluation":        <document (SemanticEvaluationV2
                                               shape — the SCRIPTED model
                                               outcome for the tier axis)>,
                          "context_provenances": [<bounded member>, ...],
                          "product_evidence":    <document | null>,
                          "human_review":        null }   # overlays are OUT of
                                                          # Track A (replay precedent)
  "published_quantity": { "candidate": <int|null>, "target": <int|null>,
                          "citation": <str> }
  "completeness_attestation_source": {
     "candidate": { "state": "PUBLISHED_STATEMENT" | "ABSENT",
                    "verbatim": <str|null>, "location": <str|null> },
     "target":    { "state": "PUBLISHED_STATEMENT" | "REVIEWED_DETERMINATION" | "ABSENT",
                    "verbatim": <str|null>, "anchor": <str|null> } }
  "expected": {
     "outcome":  "DERIVED" | "REFUSED" | "NON_CONSTRUCTIBLE",
     "unit":     "PROVEN_EQUIVALENT" | "UNPROVEN" | "CONTRADICTED" | null,
     "quantity_axis": "CONSISTENT" | "BOTH_UNPUBLISHED" | "ATTESTED_NOT_MATERIAL"
                      | "CONTRADICTED" | "UNDETERMINED" | null,
     "candidate_composition_state": <state | null>,
     "target_composition_state":    <state | null>,
     "textual_relation": "T-AGREE" | "T-DIFF-MATERIAL" | "T-DIFF-UNESTABLISHED" | null,
     "tier":          <tier | null>,
     "expected_ceiling": "CEILING_SALES_UNIT_NOT_PROVEN"
                         | "CEILING_SALES_UNIT_CONTRADICTED" | null,
     "pricing_eligible": <bool | null>,   # tier-level consequence; null when
                                          # outcome != DERIVED
     "replay":        "REPLAY_PASS" | "REPLAY_REFUSED" | "NOT_APPLICABLE",
     "refusal":       { "stage": "CONSTRUCTION" | "CODEC_DECODE" | "PRESENTATION_GATE"
                         | "REPLAY_AGREEMENT" | "CORPUS_INTEGRITY",
                        "error_type": <bounded str | null> } | null,
     "semantic_identity_note": <str | null>   # for A_B cases: the independent
                                              # semantic-axis statement (context
                                              # only — never an authority input)
  }
  "label": {
     "labeling_provenance": "DESIGN_TABLE_GROUNDED" | "REVIEWED_SOURCE_GROUNDED"
                            | "ADVERSARIAL_CONSTRUCTION",
     "grounding_citation":  <str>,    # e.g. "P3 design §5 U19; §5.1 case 4" /
                                      # "P4-FU2 Revision record 3, blocker shape"
     "author":      <identity str>, "author_utc": <utc str>,
     "reviewer":    <identity str>, "reviewer_utc": <utc str>,
     "review_status": "REVIEWED",
     "independence_attestation": <str>,  # the fixed statement, per case:
     "rationale":   <str>                # explicit prose, per case
  }
  "case_digest": <sha256 over the case document minus this field>
}
```

* The loader enforces the exact key set (missing AND extra keys refused —
  the family's strict-decode discipline), the bounded vocabularies, the
  `case_id` pattern + uniqueness, `label.author != label.reviewer`,
  `review_status == "REVIEWED"`, and — for `outcome == "DERIVED"` — the
  internal coherence of the expected axes. The Bundle-specific
  coherence checks are SCOPED to Bundle-channel cases (the adjudicated
  correction of record, C2-F1 / Q3-C-D1-FU1): `unit ==
  PROVEN_EQUIVALENT` requires `quantity_axis ∈ {CONSISTENT,
  BOTH_UNPUBLISHED, ATTESTED_NOT_MATERIAL}` and both composition states
  ESTABLISHED ONLY when the case's presented channel is the BUNDLE form
  (the Bundle-comparison shape — the frozen P3 D6 conjunction). For
  non-Bundle channels (SINGLE_UNIT / PACK_QUANTITY / TRAY_OR_FACTORY_
  PACK) the delegated FU3 expectations retain their FROZEN P3 D11
  audit-field semantics: the six Bundle-axis fields (quantity-axis
  state, candidate / target composition states, the three attestation
  digests — and the textual-relation axis) are EXACTLY null on the
  expected axes; a non-Bundle PROVEN expectation carrying a non-null
  Bundle axis is incoherent (it would misstate the frozen delegation
  and mislabel the E1 axis-audit comparison). The byte-identical
  delegation requirement (P3 D9) is preserved: the non-Bundle arm
  derives exactly the frozen FU3 unit, and the family labels that unit
  with the null Bundle-axis audit surface. `pricing_eligible == true`
  requires `tier ∈ {MACHINE_VERIFIED, AI_ASSISTED_COMPARABLE,
  HUMAN_CONFIRMED}` and `unit == PROVEN_EQUIVALENT` (the `human_review`
  overlay arm is vacuous in family schema v1 — `human_review` is null
  by the exact key set). The label itself is checked for obvious
  incoherence BEFORE the implementation is ever run; an incoherent
  label is a corpus-integrity failure, never a test failure.
* The identity-assessment decode (the `scripted_context.identity_
  assessment` document) enforces the FROZEN `IdentityStateAssessmentV2`
  constructor as the final arbiter (the state / substate family
  consistency, exactly one primary identifier-relationship signal over
  the frozen per-substate signal table, the round-trip projection
  identity — every constraint byte-frozen, none weakened). The
  adjudicated correction of record (the C1 identity-context defect /
  Q3-C-D1-FU1): the normalized part-number fields are decoded as
  strings that may be EMPTY exactly where the frozen constructor
  permits — the U4_NO_MPN substate ("no candidate identifier exists" —
  the normalized candidate part number is the empty string) and,
  symmetrically, the E1_NO_TARGET_MPN substate (the normalized
  requested part number). A loader rule that refused the empty
  normalized part number would reject recorded identity contexts the
  frozen S2-A contract produces (the no-MPN recorded-page shapes);
  the correction permits the empty string, keeps the frozen
  constructor + the projection as arbiter, and changes no other
  identity constraint. The frozen constructor is NOT modified.
* The allowed recorded-extraction-result state (the adjudicated
  correction of record, C2-F6 / Q3-C-D1-FU1). A case MAY carry: the
  candidate composition record NULL + the candidate basis `NONE` + a
  PRESENT recorded extraction result (`derivation_inputs.
  extraction_evidence.result_document`), with the presented channel
  EXACTLY the frozen P2 mapping of that result (`sales_unit_
  channel_from_extraction` — the frozen lossy map: OBSERVED_
  UNAMBIGUOUS ⇒ the channel over the primary established cue's
  published text; every other state ⇒ the canonical UNAVAILABLE) and
  the expected authority INDEPENDENTLY derived from the frozen
  contract (for the AMBIGUOUS_CUE / BUNDLE_WITHOUT_CONTENTS /
  CONTRADICTED_CUES recorded states: the canonical UNAVAILABLE channel
  ⇒ U0 UNPROVEN — the frozen P2-to-FU4 chain, P3 U0 / D8). This is the
  row shape of B6-ii / B6-iii / C6: the row's REQUIRED evidence IS the
  recorded extraction result, and the recorded absence is the frozen
  mapping of it. The loader enforces a NEW case-document-integrity
  refusal over this state: when a recorded extraction result is
  present, the presented channel must equal the frozen P2 mapping of
  that result — a mismatch (the recorded result was not the result the
  presented channel was mapped from) is a `CORPUS_INTEGRITY`
  observation (the cross-listing / wrong-result shape at the case-
  document layer — the loader is the only surface that sees both
  documents). The existing negative contracts are PRESERVED:
  `EXTRACTION_RESULT_V1` requires the candidate composition record +
  the recorded extraction evidence with the record's embedded original
  equal to the recorded result; `RECORDED_CHANNEL` carries no
  extraction evidence; `NONE` carries no candidate composition record.
  Recording the result over the case's published text uses the FROZEN
  P2 extractor (evidence acquisition — §4.6 item 3); the expected
  outcome is still grounded per items 1–2.
* The coherence pre-checks of this section use FROZEN CONTRACT DATA
  ONLY (the bounded vocabularies drift-pinned to the frozen research
  exports, the frozen `PRICING_ELIGIBLE_TIERS` set, the frozen
  ceiling-to-unit keying, the frozen constructors as validators) — the
  loader NEVER invokes the FU4 derivation, the R1 replay, or any model
  to compute, fill, or check an expected axis (the W9 adjudication of
  record; the §4.6 implementation-output prohibition extends to the
  loader's own coherence checks — structurally pinned by the C1 import
  scan + the sentinel no-execution probe).
* `expected.refusal.stage` is the INDEPENDENT expectation (which layer
  the defect must be caught at, per the approved design's failure-point
  analysis — P3 §9 / P5 §9 / the Revision records); a refusal at the
  WRONG stage is a recorded defect (metric M6, §6.2), and a refusal at
  ANY stage still satisfies the hard gate G4 (no bypass).

## 4.5 The manifest (schema 1)

`manifest_schema_version: 1`; `corpus_id`; `corpus_version`;
`semantic_contract_binding` (the FU4 five-tuple); `corpus_digest`;
`case_count`; `cases` (per-case: `case_id`, `case_digest`,
`evidence_kind`, `track`, `matrix_row`); `statement` (the §4.1 family
statement); `lineage` (`derived_from_corpus_version: null`,
`derived_from_corpus_digest: null` — the family's first version);
`manifest_digest` (over the manifest minus this field). The per-case
projection keeps the manifest auditable without re-opening the corpus
document (the semantic family's manifest convention).

## 4.6 The label independence contract (binding, DEC-C1-11)

1. **Grounding classes (bounded).** Every label names exactly one
   `labeling_provenance`:
   * `DESIGN_TABLE_GROUNDED` — the expected outcome follows from the
     approved contract semantics as published in the design of record
     (P3 §5 U-rows, §5.1 ten-case matrix, §3.7 worked examples, the
     attestation rules; Q3-B4 §4.1 / §5.3 for the tier / ceiling
     consequences; the frozen S2-A tier matrix for the scripted-context
     tier). The `grounding_citation` names the exact row(s). This class
     covers the synthetic contract-coverage rows.
   * `REVIEWED_SOURCE_GROUNDED` — the expected outcome follows from the
     recorded source content + a cited independent determination (a
     recorded fixture's history, a real-market retrieval verified by a
     reviewer against an independent source). The `grounding_citation`
     names the archive / fixture + the determination.
   * `ADVERSARIAL_CONSTRUCTION` — the expected REFUSAL / NON_
     CONSTRUCTIBLE outcome follows from a recorded defect shape (the
     P4-FU1 / P4-FU2 / R1 / R2 adversarial matrices, cited) + reviewer
     judgment of the failure stage.
2. **The implementation-output prohibition.** Labels are NEVER derived
   from the FU4 implementation output or from any model response.
   Mechanically enforced three ways: (a) `fixtures.py` (the case
   authoring source) and the C2 authoring scripts are import-scanned —
   they may import the frozen P2 extraction module (evidence
   ACQUISITION — recording the extraction result IS recording evidence)
   and the frozen S2-C / domain types (case construction), but NOT
   `semantic_authority_fu4`, `semantic_decision_v2_fu4`,
   `semantic_authority_v2`, or `semantic_authority_fu3` (the label-
   determining derivations) — a guard test fails the suite on violation;
   (b) the `independence_attestation` field carries the fixed statement
   ("this expected outcome was established from the recorded source
   content and the cited approved-design rows without executing or
   reading the output of the FU4 derivation, the R1 record adapter, or
   any model") and the loader rejects any label text that names model
   output as a source (the semantic family's mechanical anti-derivation
   rule, adopted); (c) temporal separation — the corpus is SEALED (C2
   endpoint, digest of record) before the evaluator (E1) is written;
   the E1 acceptance re-verifies the sealed digest is unchanged;
   (d) the loader-coherence separation (the W9 adjudication of Q3-C-
   D1-FU1): the expected-axis coherence pre-checks of §4.4 use only
   the frozen contract data (the bounded vocabularies, the frozen
   pricing-eligible tier set, the frozen ceiling-to-unit keying, the
   frozen constructors as validators) and never invoke the derivation
   / the replay / any model — a coherence check that computed an
   expected value from implementation output would be a label-
   derivation violation, not a structural check (the C1 import scan +
   the sentinel no-execution probe pin this structurally).
3. **The extraction-evidence nuance (recorded, not a loophole).**
   Recording the `SalesUnitExtractionResult` over a case's published
   text uses the FROZEN P2 extractor — that is evidence acquisition
   (the result is the recorded input of the v3 embedding, exactly as the
   production chain would produce it), not label determination. The
   EXPECTED OUTCOME (unit / axis / tier / refusal stage) is still
   grounded per items 1–2 without reading the FU4 derivation. A case
   whose extraction evidence cannot be produced by the frozen extractor
   over its recorded source text (e.g. a hand-forged result for an
   adversarial row) is labeled `ADVERSARIAL_CONSTRUCTION` and its
   expected outcome is the REFUSAL — the forgery is the point.
4. **Two-reviewer rule.** `label.author` and `label.reviewer` are
   distinct recorded identities (the loader enforces inequality); the
   reviewer's duty is to re-derive the expected outcome INDEPENDENTLY
   from the citation + the source content (for `DESIGN_TABLE_GROUNDED`:
   from the design rows, not from the author's case text), and to
   challenge the label (the §8 workflow). For `REAL_MARKET` cases the
   reviewer must additionally perform (or attest to) the independent
   source verification of §3.2-L3 by a person other than the archive's
   attestor.
5. **Label change governance.** Any post-seal label change follows the
   semantic family's A–D reason classes under a new corpus version +
   `label_revisions` entry (numbered, digest-anchored, reviewer-
   identity-required). "The implementation failed this case" is NOT a
   valid reason (CLAUDE.md evaluation-truth rule, verbatim).

## 4.7 What the corpus deliberately is not

* Not a semantic-model corpus: it carries no expected semantic decision
  labels for the hard-gate arithmetic of the semantic family (the
  `semantic_identity_note` is context documentation for A_B cases, and
  Track B's own labels are PUBLISHED-EVIDENCE annotations — the
  independently labeled set of published constituents / quantity /
  completeness statement / ambiguity — never "the model should answer X
  because the implementation derives Y").
* Not a production evidence store: the case evidence is qualification
  evidence (recorded, sealed, cited); real-market archives are cited,
  never re-fetched by the evaluator (zero-live).
* Not a prompt: nothing in the corpus enters the model prompt except,
  for Track B, the rendered recorded case (the frozen 2.1 user
  rendering over the real case document).

---

# 5. Complete qualification case matrix

Conventions. Every row names: the required shape, the EXPECTED authority
(five axes where applicable), the EXPECTED failure stage (for REFUSED /
NON_CONSTRUCTIBLE rows), the required evidence (which recorded documents
must exist), the evidence kind, the surface, and the minimum case count
in v1.0.0. "Q" = the quantity-axis state; "T" = the textual-relation
axis; "states" = the candidate / target composition states. The expected
outcomes below are the SPECIFICATION of record (grounded in the cited
approved-design rows) that C2's independent labels must instantiate; a
C2 label that disagrees with its cited row is a label-defect event
(§4.6 item 4), never a silent re-label. DELE = the delegation /
preservation rows (non-bundle arms + historical coexistence — the
"nothing moved" proof at corpus scale).

**Stage semantics per surface (C2 labeler guidance — the observation
point of the refusal is part of the label; grounded in the R1 matrix's
recorded failure points).** The same defect is observed at different
stages depending on the surface the sealed document is presented
through:

* (i) **Digest-breaking tamper** (any field edited, the covering digest
  NOT recomputed): `CONSTRUCTION` on the DERIVATION surface (the frozen
  constructor re-verifies the digest); `CODEC_DECODE` on the RECORD
  surface (the payload decode re-verifies the record digests + the
  round-trip document identity — the R1 row-8 variants all refuse at
  decode).
* (ii) **Self-consistent forgery** (all digests recomputed; the
  association / grounding is false — the P4-FU2 false-PROVEN shape):
  `PRESENTATION_GATE` on the DERIVATION surface (the gate re-proves the
  association at derivation time); `REPLAY_AGREEMENT` on the RECORD
  surface (the decode ACCEPTS the self-consistent shape — the record's
  own digests verify and the round-trip holds; the replay's re-derivation
  refuses at the gate and the derived-agreement proof surfaces it as a
  replay error — the R1 row-9 control / forgery pair).
* (iii) **Constructor-level incoherence** (a basis / subject-side /
  clause-binding / vocabulary defect, an unpermitted source member, a
  missing embedded result): `CONSTRUCTION` on the DERIVATION surface;
  `CODEC_DECODE` on the RECORD surface (the decode runs the same
  constructors — the bounded error class is the codec's).
* (iv) **`CORPUS_INTEGRITY`** — the family loader only (the case
  document's own internal inconsistencies — §4.4 — never
  presented to the implementation). This includes the CROSS-DOCUMENT
  bindings between separately sealed case fields that no frozen
  constructor / codec / derivation input receives (the named
  loader observation is the W1 exact refusal reason): the recorded
  extraction input document vs the embedded result's `input_digest`
  binding (the D6-i shape — the Q3-C-D1-FU3 / F-R6 re-attribution,
  `SOURCE_EXTRACTION_INPUT_DIGEST`); the record's embedded original
  vs the case's recorded extraction evidence (the D3-ii shape —
  C2-F2a, `CASEDOC_EMBEDDED_RESULT_EQUALITY`); the derivation
  channel vs the recorded case's channel (the D6-ii shape —
  `CASEDOC_CHANNEL_EQUALITY`); the recorded extraction result vs the
  presented channel (the C2-F6 allowed-state mismatch —
  `CASEDOC_RECORDED_RESULT_CHANNEL_MAPPING`).
* (v) **Execution-level contract misuse** (the defect exists only
  when a frozen function is INVOKED with the misused inputs — the
  D16-iii shape: composition / attestation inputs presented to the
  frozen FU3 token's derivation, which has no composition axis; the
  FU4 superset dispatch's FU3 arm delegates to the frozen function,
  which refuses — P3 §5.4 / D9): the sealed documents are SOUND (no
  constructor / codec / case-document observation can fire over them
  — verified at the Q3-C-D1-FU1 revision over the family loader), so
  the shape is NOT a sealable v1.0.0 corpus case at any refusal stage;
  its observation point is the E1 adversarial re-execution, where the
  MANDATORY assertion feeds the documented shape through the REAL
  frozen entry point and requires the contract-misuse refusal (the
  §9.6 acceptance; the D16 row's third obligation — the v1.0.0 D16
  corpus minimum is 2, the explicit phase-boundary correction of Q3-C-
  D1-FU1; the frozen FU3 / FU4 token boundary is NOT weakened).

**The five validation surfaces (the Q3-C-D1-FU3 / F-R6
adjudication — the explicit distinction).** A labeled refusal
stage names exactly ONE observation surface, and the surfaces are
NOT interchangeable:

1. **Frozen-constructor validation** — the REAL frozen
   constructors over the presented evidence documents (design
   §4.2(f); the constructor is the validator). The `CONSTRUCTION`
   stage is observable only where a frozen constructor ACTUALLY
   refuses the presented document with its bounded error (the
   stage-error vocabulary's `CONSTRUCTOR` class). A family-loader
   check that MIRRORS a construction-level binding at corpus level
   is a family observation, not a frozen-constructor exception: the
   frozen constructors never receive the case's sealed `source`
   block or the case's recorded extraction input document, and
   their silence over a sealed shape is a documented non-
   observation, never a construction-stage refusal.
2. **Frozen-codec validation** — the REAL universal codec over the
   RECORD-surface payload (design §4.2(g); the `CODEC_DECODE`
   stage, the `CODEC` class). The payload's exact key set carries
   no case-document field (no sealed `source` block, no recorded
   extraction input document) — a cross-document case binding is
   not a codec-observable shape.
3. **Family-loader cross-document integrity validation** — the
   family's own checks over the case document's separately sealed
   fields (design §4.4; the `CORPUS_INTEGRITY` stage, error_type
   null by the stage-error vocabulary). The loader is the ONLY
   surface that sees both sides of a cross-document binding; its
   named observations are the exact refusal reasons of this stage
   (the W1 adjudication). The loader NEVER invokes the derivation
   / the replay / any model (W9). The SAME checks serve TWO
   distinct consumers, and the distinction is binding (the
   Q3-C-D1-FU3-FU1 two-contract correction): **Contract A —
   corpus ingestion** — the strict load runs the checks in
   collection mode over a sealed-raw case, verifies the labeled
   stage against the collected observations (the stage-coherence
   rule), and ACCEPTS the correctly labeled case into the corpus
   (the refusal of an incoherent label is the loader's label-
   governance act — it is not the observation record, and a
   negative case loading successfully does not mean the
   underlying evidence is valid); **Contract B — E1
   observation** — the evaluator reads the observation record
   ONLY from the family-owned read-only observation interface
   (the §6.1 execution: the same actual checks in collection
   mode — a bounded name / layer / reason record + the inverse-
   scoping stage mapping — NEVER from the label, NEVER from the
   strict load's acceptance).
4. **Frozen-derivation execution** — the REAL entry point
   `derive_authority_tier_fu4` (the `PRESENTATION_GATE` stage for
   the gate's bounded errors; the derivation's own contract-misuse
   refusals — stage semantics (v)). A derivation COMPLETING over a
   refused-expected case's reconstructed self-consistent typed
   inputs is a documented non-observation for the loader-observation
   shapes (the defect is never presented to the implementation): it
   is neither a refusal at any stage nor a `BYPASSED_INTEGRITY` —
   and it is NEVER counted as satisfying a refused case (the §6.1
   two-contract execution order: the family-owned observation
   interface — Contract B — is the loader-observation shapes'
   real observation over the sealed document; the strict load —
   Contract A — is the label-coherence verification, not the
   observation).
5. **Replay agreement** — the REAL codec decode + the frozen
   `replay_semantic_decision` over the RECORD surface (the
   `REPLAY_AGREEMENT` stage, the `REPLAY` class).

The pre-revision D6(i) attribution (CONSTRUCTION) conflated
surface 3 with surface 1 (a family-loader observation classified
at the CONSTRUCTOR layer was read as the frozen constructor's
bounded error); the Q3-C-D1-FU3 adjudication re-attributes it to
surface 3 per the C2-F2a precedent.

A refusal at the WRONG stage is a recorded defect (M6, quality metric);
a refusal at ANY stage satisfies the hard gate (G4 — no bypass); a NO
refusal is the fatal class (G1 / G4).

## 5.1 Category A — expected `PROVEN_EQUIVALENT`

| Row | Shape (recorded evidence) | Expected authority (unit / Q / states / T) | Expected tier consequence (scripted MATCH+HIGH+STRONG+U1 context unless noted) | Required evidence | Kind | Surface | Min cases |
| --- | --- | --- | --- | --- | --- | --- | --- |
| A1 | Both configurations independently complete (candidate: PUBLISHED marker detected from recorded text; target: REVIEWED determination over the target's own source), byte-identical closed clause, neither side publishes a count | PROVEN / BOTH_UNPUBLISHED / ESTABLISHED,ESTABLISHED / T-AGREE | tier stands (AI_ASSISTED_COMPARABLE); pricing_eligible=true (tier level); W1-PENDING recorded | candidate record (v3, RECORDED_CHANNEL or EXTRACTION basis), target FU4 record (REVIEWED attestation), channel, recorded source texts | SYNTHETIC (×1 — the v1.0.0 instantiation) + RECORDED_FIXTURE-shape variant (×1) — **the recorded variant is C3-deferred (Q3-C-D1-FU1 / C2-F3): no committed recorded source publishes the required complete Bundle composition (verified §2.5); it is an additive 1.1.0 obligation over the C3-acquired recorded source, the independently evidenced publisher completeness of P3 D19 preserved — recorded evidence is never replaced with invented text** | BOTH | 1 at v1.0.0 (2 incl. the C3-deferred recorded variant) |
| A2 | Same as A1 but DIFFERENT WORDING with equivalent constituent multiset under the versioned grammar (order + quantity phrasing: `2x RAM + 1x CPU` vs `CPU, 2 RAM`) | PROVEN / BOTH_UNPUBLISHED / ESTABLISHED,ESTABLISHED / T-AGREE (secondary path) | as A1 | as A1 (both clauses fully parseable) | SYNTHETIC | BOTH | 2 |
| A3 | Different ordering only (`2x RAM + 1x CPU` vs `1x CPU + 2x RAM`) | PROVEN / BOTH_UNPUBLISHED / ESTABLISHED,ESTABLISHED / T-AGREE (secondary) | as A1 | as A1 | SYNTHETIC | BOTH | 1 |
| A4 | Valid duplicate constituent quantities — repeated item tokens published IDENTICALLY on both sides (`1x RAM + 1x RAM + 1x CPU` byte-identical, both attested) | PROVEN / BOTH_UNPUBLISHED / ESTABLISHED,ESTABLISHED / T-AGREE (byte-identity primary path) | as A1 | as A1 | SYNTHETIC | BOTH | 1 |
| A5 | Quantity-axis consistency — both sides publish the EQUAL count over attested agreed clauses (Q=CONSISTENT); one row byte-identical, one row multiset-phrasing | PROVEN / CONSISTENT / ESTABLISHED,ESTABLISHED / T-AGREE | as A1 | channel with quantity, target record with quantity, both attestations | SYNTHETIC | BOTH | 2 |
| A6 | Asymmetric published quantity + verified `QuantityCompletenessAttestationV2FU4` standing on the MISSING side (review-constructed, bounded reason, subject = missing side) | PROVEN / ATTESTED_NOT_MATERIAL / ESTABLISHED,ESTABLISHED / T-AGREE | as A1 | the quantity attestation document (the ONLY case family where a quantity attestation is admissible), both completeness attestations | SYNTHETIC | BOTH | 1 |
| A7 | Reviewed target evidence versus published candidate evidence — the standard independence shape in both attestation-basis directions: (i) target attestation = the target's OWN published statement (PUBLISHED basis, recorded by the review); (ii) target attestation = REVIEWED determination anchored to a manufacturer-published specification | PROVEN / per Q / ESTABLISHED,ESTABLISHED / T-AGREE | as A1 | target FU4 record (both basis variants), candidate PUBLISHED-basis record, anchor text | SYNTHETIC | BOTH | 2 |
| A8 | RECORD-surface positive control — a full R1 payload over an A1 shape (the derived section records PROVEN + the standing tier) | PROVEN (unit) / REPLAY_PASS | replay re-derives and agrees field-for-field (the full FU4 audit surface) | the complete payload document (case + evaluation + execution + derived + authority + integrity), the pinned route execution section | SYNTHETIC | RECORD | 2 |
| A-DELE | Non-bundle delegation preservation at corpus scale — pack-of-equal-counts (U3 PROVEN), tray equal counts (U8 PROVEN), single unit (U1 PROVEN), channel UNAVAILABLE (U0 UNPROVEN) under the FU4 token — the frozen FU3 delegation is byte-identical | per the frozen FU3 rows (recorded per case) — **the expected Bundle-axis fields are EXACTLY null (quantity axis, composition states, textual relation, the attestation digests): the frozen P3 D11 non-bundle audit-field semantics; the §4.4 coherence check is scoped to Bundle-channel cases (Q3-C-D1-FU1 / C2-F1)** | per the frozen derivation | the frozen FU3 target record (D18 composition-ABSENT reading) or None; no composition evidence | RECORDED_FIXTURE (the Micron recorded pages ground the non-bundle absence rows) + SYNTHETIC | DERIVATION | 4 |

**Category A minimum: 16 cases at v1.0.0** (pre-revision 17 — the A1
recorded-variant deferral is the explicit phase-boundary correction of
Q3-C-D1-FU1 / C2-F3; destination: the C3 real-market acquisition + the
additive 1.1.0 re-seal; governing contract: P3 D19 + the design §7.6
real-market minimums; later acceptance gate: the C3 acceptance + the
1.1.0 re-seal verification). Every A row additionally carries the
recorded negative twin where the frozen contract provides one (e.g. A4's
twin — non-identical duplicate phrasing — is C2-row, CF-3).

## 5.2 Category B — expected `UNPROVEN`

| Row | Shape | Expected authority | Expected tier consequence (scripted MATCH+HIGH+STRONG+U1 unless noted) | Required evidence | Kind | Surface | Min cases |
| --- | --- | --- | --- | --- | --- | --- | --- |
| B1 | Count-only bundle description — corpus-shaped channel OBSERVED BUNDLE quantity N, raw_detail the count-only phrase (`bundle of N`), candidate composition ABSENT — vs a target bundle of the SAME count (frozen record) | UNPROVEN / (axis recorded) / ABSENT candidate | NEEDS_REVIEW + CEILING_SALES_UNIT_NOT_PROVEN; pricing_eligible=false. Coexistence note (recorded, not an FU4 expectation): the SAME input under the FU3 token derives PROVEN (the A7 two-token pin at corpus scale) | the channel document; the frozen target record; no composition record | SYNTHETIC + RECORDED_FIXTURE variant | BOTH | 2 |
| B2 | Missing completeness attestation — byte-identical closed clauses, NO attestation on EITHER side (both SYNTACTICALLY_VALID); one row Q=BOTH_UNPUBLISHED, one row Q=CONSISTENT | UNPROVEN / (recorded) / SYNTACTICALLY_VALID,SYNTACTICALLY_VALID / T-AGREE | NEEDS_REVIEW + CEILING (the Blocker B headline: textual agreement ≠ completeness) | the unattested records (both sides) | SYNTHETIC | BOTH | 2 |
| B3 | Candidate complete (attested), target incomplete (SYNTACTICALLY_VALID, unattested) | UNPROVEN / ESTABLISHED,Synt | NEEDS_REVIEW + CEILING | candidate ESTABLISHED record; target FU4 record (unattested state) | SYNTHETIC | BOTH | 1 |
| B4 | Target complete (attested), candidate incomplete — the reverse of B3 | UNPROVEN / Synt,ESTABLISHED | NEEDS_REVIEW + CEILING | as B3, roles reversed | SYNTHETIC | BOTH | 1 |
| B5 | Partial constituent list — candidate PARTIAL (incompleteness marker `etc.` / unclosed paren / dangling separator) vs any target; target PARTIAL vs candidate ESTABLISHED | UNPROVEN / PARTIAL side | NEEDS_REVIEW + CEILING | the PARTIAL records (three marker variants) | SYNTHETIC | BOTH | 3 |
| B6 | Ambiguous extraction — (i) candidate CONTRADICTED_PUBLISHED (title vs structured clauses differ) vs an ESTABLISHED target whose clause equals one side → **UNPROVEN** (D8 / U12 — the CF-1 documented row: the task's CONTRADICTED placement is overridden by the frozen contract, see §2.7); (ii) extraction AMBIGUOUS_CUE → channel UNAVAILABLE → U0; (iii) bare `bundle` → U0 | UNPROVEN / CONTRADICTED_PUBLISHED (i) | NEEDS_REVIEW + CEILING (i); UNPROVEN (ii, iii) | the EXTRACTION-basis record (i) with both clauses + their per-clause states; the recorded extraction results (ii, iii) — **the allowed state of §4.4 (Q3-C-D1-FU1 / C2-F6): candidate composition record null, basis NONE, the recorded result present, the presented channel exactly the frozen P2 mapping of the result (the canonical UNAVAILABLE over AMBIGUOUS_CUE), the U0 expectation independently derived from the frozen contract; the loader's case-document-integrity refusal over a recorded-result / presented-channel mismatch** | SYNTHETIC | BOTH | 3 |
| B7 | Missing published quantity — asymmetric gap, NO attestation, both configurations attested + textually agreed (the Blocker A defect row, both role directions: candidate publishes, target silent; target publishes, candidate silent) | UNPROVEN / UNDETERMINED / ESTABLISHED,ESTABLISHED / T-AGREE | NEEDS_REVIEW + CEILING | the channel / target quantity fields; NO quantity attestation | SYNTHETIC | BOTH | 2 |
| B8 | Insufficient provenance — (i) a candidate record whose `source` is a frozen enum member NOT permitted on the composition surface (e.g. `SPECIFICATION_TEXT` / `REVIEWED_PRODUCT_CONTEXT`) or a string outside the vocabulary; (ii) a target record with a foreign source class | outcome NON_CONSTRUCTIBLE, refusal stage CONSTRUCTION | no derivation input; no tier | the invalid documents (sealed raw) | SYNTHETIC | DERIVATION | 2 |
| B9 | Unverifiable original extraction evidence — (i) an EXTRACTION-basis record with the embedded result MISSING (un-constructible); (ii) an embedded result whose cue span / digest integrity FAILS (out-of-band tamper, refused at construction / presentation) | NON_CONSTRUCTIBLE (i) / REFUSED stage CONSTRUCTION or PRESENTATION_GATE (ii) | no unit derived | the invalid documents | SYNTHETIC | BOTH | 2 |
| B10 | Semantic MATCH with unproven bundle composition — scripted MATCH+HIGH+STRONG+clean+U1 over (i) unattested equal clauses; (ii) count-only bundle; (iii) channel UNAVAILABLE with a model BUNDLE claim in matched_attributes | UNPROVEN in all three / (recorded) | NEEDS_REVIEW + CEILING_SALES_UNIT_NOT_PROVEN; pricing_eligible=false — **the I-1 headline rows** | the scripted evaluation document (with the BUNDLE attribute detail, to be ignored), the evidence per sub-row | SYNTHETIC | BOTH | 3 |
| B11 | Unlisted completeness phrasing — a closed clause ending `as listed` / a localized phrasing NOT in the versioned `_COMPLETENESS_MARKERS` (T9 safe direction) vs an attested equal target | UNPROVEN / Synt,ESTABLISHED | NEEDS_REVIEW + CEILING | the unattested candidate record | SYNTHETIC | DERIVATION | 1 |
| B12 | Model-generated constituent claims only — the scripted evaluation detail names constituents; the recorded published text names none (channel UNAVAILABLE or ABSENT composition) | UNPROVEN (per the recorded evidence ONLY) | NEEDS_REVIEW + CEILING | the scripted evaluation; the recorded absence | SYNTHETIC | BOTH | 1 |
| B-DELE | UNAVAILABLE channel vs every target shape (default single unit, pack, tray, bundle) — U0 recorded at corpus scale | UNPROVEN | per the frozen delegation | the canonical UNAVAILABLE channel | RECORDED_FIXTURE (the recorded pages' extraction-absence rows) + SYNTHETIC | DERIVATION | 2 |

**Category B minimum: 25 cases.**

## 5.3 Category C — expected `CONTRADICTED`

| Row | Shape | Expected authority | Expected tier consequence | Required evidence | Kind | Surface | Min cases |
| --- | --- | --- | --- | --- | --- | --- | --- |
| C1 | Different constituent identity — both ESTABLISHED, fully parseable, multisets differ on an item (`2x RAM + 1x CPU` vs `2x RAM + 1x SSD`); one row Q=BOTH_UNPUBLISHED, one row Q=CONSISTENT | CONTRADICTED / ESTABLISHED,ESTABLISHED / T-DIFF-MATERIAL | NEEDS_REVIEW + CEILING_SALES_UNIT_CONTRADICTED; pricing_eligible=false | both attested records | SYNTHETIC | BOTH | 2 |
| C2 | Different constituent multiplicity — both ESTABLISHED, shared item quantity differs (`2x RAM + 1x CPU` vs `3x RAM + 1x CPU`) | CONTRADICTED / T-DIFF-MATERIAL | as C1 | as C1 | SYNTHETIC | BOTH | 1 |
| C2b | (CF-3) Non-identical duplicate phrasing over the same commercial content — candidate `1x RAM + 1x RAM + 1x CPU` (attested) vs target `2x RAM + 1x CPU` (attested): the frozen grammar does NOT merge repeated tokens ⇒ T-DIFF-MATERIAL ⇒ CONTRADICTED (recorded as the frozen-grammar outcome; the commercial-ambiguity note + the future T5 decision are in O-4) | CONTRADICTED / T-DIFF-MATERIAL | as C1 | as C1 | SYNTHETIC | DERIVATION | 1 |
| C3 | Published quantity contradiction — both sides publish DIFFERENT counts: (i) over textually-agreed attested clauses (U16); (ii) over textually-agreed clauses with ONE side unattested (U16 — the count difference is not gated by completeness) | CONTRADICTED / CONTRADICTED (quantity axis) | NEEDS_REVIEW + CEILING (both rows) | the quantity fields; the records per sub-row | SYNTHETIC | BOTH | 2 |
| C4 | Different sales-unit form — bundle candidate vs (i) the default single-unit target (U9; the corpus-0034 shape, RECORDED_FIXTURE-able); (ii) an explicit PACK target; (iii) an explicit TRAY target — the form rule fires BEFORE any composition is read (even an ESTABLISHED candidate composition) | CONTRADICTED / form axis | NEEDS_REVIEW + CEILING; the scripted NO_MATCH context variant recorded (the absolute-rule model side) | the channel; the target records (frozen FU3 shape for (i)–(iii)); for the form-over-composition row: an ESTABLISHED candidate record | RECORDED_FIXTURE + SYNTHETIC | BOTH | 3 |
| C5 | Complete but non-equivalent composition with an asymmetric quantity gap — both ESTABLISHED, materially different clauses, Q=UNDETERMINED (the gap is recorded, does NOT shield the contradiction) | CONTRADICTED / UNDETERMINED / T-DIFF-MATERIAL | NEEDS_REVIEW + CEILING | as C1 + the asymmetric quantities | SYNTHETIC | DERIVATION | 1 |
| C6 | (CF-1, documented) Conflicting secondary extraction cues — a GENUINE `CONTRADICTED_CUES` extraction (kind or quantity conflict across fields ⇒ recorded absence) vs a bundle target | UNPROVEN (U0 over the recorded absence) — the frozen P2 → FU4 chain; recorded against the task's CONTRADICTED placement | NEEDS_REVIEW + CEILING | the recorded extraction result — **accurately instantiated (Q3-C-D1-FU1 / W7): the sealed candidate text must publish the cues the recorded result carries; the genuine `CONTRADICTED_CUES` shape is two ESTABLISHED incompatible cues across fields (verified over the frozen P2 at the revision: the title's established bundle-with-contents clause vs the structured pack-of-N field ⇒ `CONTRADICTED_CUES`, the mapped channel the canonical UNAVAILABLE) — or the case describes the EXACT cue state of the instantiation it carries (a rationale that claims a state the recorded result does not carry is a label defect, §4.6 item 4); the expected authority is independently derived from the frozen P2 → FU4 chain (U0 over the recorded absence)** | SYNTHETIC | DERIVATION | 1 |
| C7 | Published evidence contradicting an asserted completeness attestation — (i) a clause containing an incompleteness marker + a claimed completeness statement (PARTIAL dominates, D5: the attestation is un-constructible over PARTIAL); (ii) a RECORDED_CHANNEL record claiming ESTABLISHED + a PUBLISHED attestation over a marker-free raw_detail (not the exact construction — refused at the gate) | NON_CONSTRUCTIBLE (i) / REFUSED stage PRESENTATION_GATE (ii) | no PROVEN reachable | the invalid / forged documents | SYNTHETIC | BOTH | 2 |

**Category C minimum: 13 cases** (10 CONTRADICTED-expected rows: C1 /
C2 / C2b / C3 / C4 / C5; plus the CF-1 documented-conflict row C6 —
labeled UNPROVEN per the frozen contract — and the published-evidence-
contradicts-attestation row C7 — labeled NON_CONSTRUCTIBLE / REFUSED —
both counted under category C for matrix completeness but carrying
non-CONTRADICTED expectations).

## 5.4 Category D — adversarial authority cases

Every D row's expected outcome is either REFUSED / NON_CONSTRUCTIBLE at
the NAMED stage (the independence expectation of §4.4), or a specific
derived authority that proves the firewall held. The stage expectation
is grounded in the cited design's failure-point analysis (P3 §9 / P5 §9
/ the Revision records 2 / 3); a refusal at a different stage is a
recorded defect (M6), a refusal at ANY stage satisfies G4, a NO refusal
fails G1 / G4 fatally.

| Row | Attack shape | Expected authority / refusal | Stage (expected) | Required evidence | Kind | Surface | Min cases |
| --- | --- | --- | --- | --- | --- | --- | --- |
| D1 | Forged completeness attestation — (i) a self-consistent ESTABLISHED RECORDED_CHANNEL record over a marker-free publication (the P4-FU2 false-PROVEN defect shape, re-exercised at corpus scale); (ii) a RECORD-surface payload over the (i) evidence whose derived section claims PROVEN + the standing tier (the self-consistent forged snapshot — decode accepts, the replay's re-derivation refuses); (iii) the variant whose derived section claims AI_ASSISTED_COMPARABLE + UNPROVEN (the firewall invariant — un-constructible) | (i) REFUSED — no unit from the forged record; (ii) REPLAY_REFUSED; (iii) NON_CONSTRUCTIBLE | PRESENTATION_GATE (i); REPLAY_AGREEMENT (ii); CONSTRUCTION / CODEC_DECODE (iii, per surface) | the forged documents (digests valid, grounding absent); the tampered payloads | SYNTHETIC | BOTH | 3 |
| D2 | Self-consistent but ungrounded evidence — a hand-forged RECORDED_CHANNEL record (all digests recomputed) whose clause the presented channel's raw_detail never published | REFUSED | PRESENTATION_GATE (the exact-construction check) | the forged record + the real channel | SYNTHETIC | DERIVATION | 1 |
| D3 | Cross-listing evidence substitution — (i) listing A's EXTRACTION record over listing B's channel (same source class / form / quantity, different raw_detail — the P4-FU1 Blocker 1 shape); (ii) content-IDENTICAL channels with DIFFERENT embedded original results (the frozen-channel-granularity bound, P5 R-5 — **the mismatch is observable ONLY by the family loader: the case's recorded extraction evidence ≠ the record's embedded original, a case-document-integrity observation; the derivation presentation gate CANNOT detect it — over content-identical channels the channel-content binding holds and all four frozen gate steps (the embedded result's own integrity; the anchor equality; the frozen P2 mapping equality; the recomputed-composition equality) pass, because the frozen channel cannot express which physical listing it came from (P5 R-5 — the documented bound, risk R-C1-10); verified at the Q3-C-D1-FU1 revision: the labeled PRESENTATION_GATE expectation is incoherent (a case-document observation fires), the CORPUS_INTEGRITY label is coherent, and the self-consistent payload twin DECODES and REPLAYS cleanly — so the (ii) variant is surface DERIVATION (no record twin; the record surface cannot carry the case-document observation)**); (iii) RECORD-surface: the payload's authority section swapped from another record over the same case | REFUSED in all three | **PRESENTATION_GATE (i — the channel_content_digest + the four-step chain); CORPUS_INTEGRITY (ii — the loader-only observation point, Q3-C-D1-FU1 / C2-F2a; the separate D3-i PRESENTATION_GATE case is preserved); REPLAY_AGREEMENT (iii)** | both listings' recorded evidence; the forged association | SYNTHETIC | BOTH (row) — (ii) DERIVATION | 3 |
| D4 | Modified original extraction evidence — (i) embedded result's cue text tampered, the result's digests recomputed, the record's anchors left UNchanged (the anchor-vs-embedding equality — the constructor's own check, the gate's step 2); (ii) embedded result's raw_field_value tampered (the cue-span containment breaks — the embedded result's OWN `verify_integrity`) | REFUSED in both | CONSTRUCTION (i, ii — the constructor re-verifies the embedding + the anchors; on the RECORD surface the same incoherence is observed as CODEC_DECODE, per the stage semantics) | the tampered documents | SYNTHETIC | BOTH | 2 |
| D5 | Recomputed forged digests — fully self-consistent forgeries: (i) an embedded original whose FROZEN P2 mapping ≠ the presented channel (wrong-result forgery); (ii) an embedded original that maps correctly but whose RECOMPUTED composition ≠ the presented record (an extra clause the publication never published) | REFUSED in both | PRESENTATION_GATE (steps 3 and 4) | the forged results + records | SYNTHETIC | BOTH | 2 |
| D6 | Source-content mismatch — (i) the recorded extraction input document is NOT the input the embedded result's `input_digest` binds (the examined input was altered after extraction — the case seals the genuine source, the separately sealed result binds the altered one; the frozen constructor / codec / derivation NEVER receive the case's recorded input document — the Q3-C-D1-FU3 / F-R6 adjudication); (ii) the case's `derivation_inputs.channel` ≠ the `recorded_case`'s channel (corpus-internal inconsistency) | (i) REFUSED — the cross-document source / extraction binding is a case-internal inconsistency observable ONLY by the family loader (the named observation `SOURCE_EXTRACTION_INPUT_DIGEST`; the sealed record + embedded result are self-consistent over the altered input — every frozen layer passes, the derivation completes, and the defect is never presented to the implementation); (ii) REFUSED at CORPUS_INTEGRITY (the loader's named observation `CASEDOC_CHANNEL_EQUALITY`) | CORPUS_INTEGRITY (i — the Q3-C-D1-FU3 / F-R6 re-attribution from the pre-revision CONSTRUCTION, per the C2-F2a precedent; error_type null by the stage-error vocabulary); CORPUS_INTEGRITY (ii) | the mismatched documents; the sealed source block | SYNTHETIC | BOTH | 2 |
| D7 | Truncated source content — (i) a colon-form title cut at max length MID-CLAUSE (no marker survives): the clause is SYNTACTICALLY_VALID, completeness UNKNOWN ⇒ derived outcome UNPROVEN (the T2 residual boundary: truncation can never reach PROVEN without a surviving attestation); (ii) an embedded result truncated after sealing (digest not recomputed) | (i) UNPROVEN (derived); (ii) REFUSED | — (i); CONSTRUCTION (ii) | the recorded truncated text; the tampered result | SYNTHETIC + RECORDED_FIXTURE variant | BOTH | 2 |
| D8 | Conflicting manufacturer versus reseller claims — (i) target review attestation anchored to the MANUFACTURER-published composition vs a materially different RESSELLER-published (attested) candidate composition; (ii) the same with the candidate UNattested | (i) CONTRADICTED (U17) + CEILING; (ii) UNPROVEN (U15 — the safe direction) | — | both attestations (the anchor texts recorded), both clauses | SYNTHETIC (real-market instance reserved for C3) | BOTH | 2 |
| D9 | Prompt injection in listing text — the title / structured field carries an instruction injection + a pseudo-completeness phrasing outside the versioned marker list: (i) Track A — the deterministic extraction does not interpret the injection (state per the recorded cue table; no attestation exists); expected unit per the recorded evidence (UNPROVEN); (ii) Track B — the model must not report a completeness assertion or adopt the injected instruction (scored as a mis-grounding / injection-susceptibility event) | (i) UNPROVEN (derived); (ii) per Track B labels | — | the recorded injection text; the Track B annotation | SYNTHETIC | A_B | 2 |
| D10 | Model-generated constituent claims without published support — scripted evaluation BUNDLE detail names a constituent the publication never listed: (i) Track A — the derivation ignores the claim (signature pin; unit per the recorded evidence); (ii) Track B — hallucination event (scored) | (i) per the recorded evidence (UNPROVEN / CONTRADICTED as labeled); (ii) per Track B | — | the scripted evaluation; the published text | SYNTHETIC | A_B | 2 |
| D11 | Exact-MPN match but Bundle composition mismatch — **the row's required identity context is the EXACT U1 EXACT shape: substate U1_TITLE_MPN (identity_state DETERMINISTIC_UNCERTAIN), the normalized candidate part number EQUAL and NON-EMPTY against the normalized requested part number, primary signal TITLE_MPN_TOKEN, relationship requirement NOT_REQUIRED (Q3-C-D1-FU1 / W8 — the identity context the material-contradiction contract measures against; a no-identifier context such as U4_NO_MPN is NOT this row's shape)** + scripted MATCH+HIGH+STRONG+clean; candidate attested composition materially different from the target's attested composition | CONTRADICTED / T-DIFF-MATERIAL → NEEDS_REVIEW + CEILING_SALES_UNIT_CONTRADICTED; pricing_eligible=false — **the "exact identity never implies unit equivalence" row** | — | the exact-MPN case (both variants by-construction over the U1 EXACT context); both attested records | **SYNTHETIC (×2 — the v1.0.0 population, Q3-C-D1-FU1 / C2-F5): the recorded identifier-family evidence (the one-character-different Micron 7500 catalog part numbers, the committed fixture cited by path + digest) is the row's documented identifier-shape CONTEXT only — the recorded catalog publishes part numbers / specifications, NOT Bundle compositions (verified §2.5), so the RECORDED_FIXTURE hybrid variant (the recorded identifier context + the by-construction composition axis) CANNOT be represented truthfully by the existing schema (the span-grounding provenance rule + the row's U1 EXACT identity context — the recorded context is U4_NO_MPN, no candidate identifier; verified at the revision). The re-authored (ii) variant is SYNTHETIC with the by-construction attested compositions over the U1 EXACT context; the D11 material-contradiction authority contract (P3 U17) and its 2-case adversarial coverage are retained; a truthful RECORDED_FIXTURE D11 instantiation is a C3 / 1.1.0 additive obligation (only over a recorded source that publishes both the U1 EXACT identity context's recorded form and the attested composition clauses)** | BOTH | 2 |
| D12 | Semantic NO_MATCH with apparently equivalent Bundle composition — scripted NO_MATCH (an independent ALWAYS_HARD conflict, e.g. capacity) + attested-EQUIVALENT composition on both sides | unit PROVEN (axis independence, CF-5) / tier non-automatic per the frozen S2-A derivation over a NO_MATCH context (recorded per case); the semantic decision is NOT upgraded and the unit is NOT downgraded | — | the scripted NO_MATCH evaluation; both attested records | SYNTHETIC | BOTH | 1 |
| D13 | AI high-confidence MATCH despite missing authority evidence — MATCH+HIGH+STRONG over (i) channel UNAVAILABLE (no bundle evidence at all); (ii) a bundle channel with NO composition record presented | UNPROVEN → NEEDS_REVIEW + CEILING (both rows) | — | the scripted evaluation; the recorded absence | SYNTHETIC | BOTH | 2 |
| D14 | Attestation laundering — (i) a candidate-side record carrying a REVIEWED_COMPOSITION_ATTESTATION basis (a review attests the target side, never the candidate listing); (ii) a target attestation with a CANDIDATE source class; (iii) a completeness attestation whose clause_digest binds a DIFFERENT clause | NON_CONSTRUCTIBLE / REFUSED in all three | CONSTRUCTION | the invalid attestation documents | SYNTHETIC | DERIVATION | 3 |
| D15 | Quantity-attestation abuse — (i) `subject_side` ≠ the actually-missing side (integrity error, no derivation); (ii) presentation over a non-asymmetric axis (both publish / both absent — contract misuse, ValueError) | REFUSED in both | CONSTRUCTION / PRESENTATION (i); CONSTRUCTION (ii) | the invalid attestation documents | SYNTHETIC | DERIVATION | 2 |
| D16 | Historical binding confusion — (i) a forged mixed-axis payload `(V2, 2.0, 1, 1, FU4)` (no adapter claims it); (ii) a 2.1/FU3-bound payload presented to the production codec (harness-only binding — still refused, the P1 invariant at corpus scale); (iii) a derivation-surface presentation of composition / attestation inputs under the FROZEN FU3 token (contract misuse — the FU3 contract has no composition axis; the FU4 dispatch's FU3 arm delegates to the frozen function, which refuses) — **(iii) is the EXECUTION-level observation point only (Q3-C-D1-FU1 / C2-F2b): over the sealed documents (sound FU4 documents) no constructor / codec / case-document observation fires (verified at the revision), so (iii) is NOT a sealable v1.0.0 corpus case at any refusal stage; the FU3 contract-misuse assertion is MANDATORY in the E1 adversarial re-execution (the stage semantics (v), §9.6) — the frozen FU3 / FU4 token boundary is NOT weakened** | REFUSED in all three (i, ii in the corpus; iii at the E1 execution) | CODEC_DECODE (i, ii); **E1 adversarial-execution assertion (iii — the frozen entry point's contract-misuse refusal, the P3 §5.4 / D9 delegation boundary)** | the forged payloads (i, ii); the FU3-token derivation shape (iii, E1) | SYNTHETIC | RECORD (i, ii); (iii) E1-only | **2 at v1.0.0** (pre-revision 3 — the explicit phase-boundary correction of Q3-C-D1-FU1; the third obligation's destination is the E1 acceptance §9.6(2)) |
| D17 | Replay-agreement tamper — (i) a stored derived section claiming AI_ASSISTED_COMPARABLE + UNPROVEN (the firewall invariant — un-constructible); (ii) a stored derived section that is self-consistent with its own digests but DISAGREES with the re-derivation over the recorded evidence (the forged-snapshot shape) | NON_CONSTRUCTIBLE (i); REPLAY_REFUSED (ii) | CONSTRUCTION (i); REPLAY_AGREEMENT (ii) | the tampered payloads | SYNTHETIC | RECORD | 2 |
| D18 | Model-generated completeness attestation treated as publisher evidence — the structural row: a scripted evaluation asserting completeness + the corpus case carrying NO attestation record: Track A derives exactly as if the assertion were absent (UNPROVEN over an unattested clause); the family gate MB-3 proves no model output document ever enters the derivation input (evaluator scan). The Track B side scores the assertion as mis-grounded (no published statement). | UNPROVEN (derived); MB-3 gate | — | the scripted evaluation; the unattested records | SYNTHETIC | A_B | 1 |

**Category D minimum: 36 cases at v1.0.0** (pre-revision 37 — the
D16-iii deferral to the E1 mandatory adversarial-execution assertion is
the explicit phase-boundary correction of Q3-C-D1-FU1 / C2-F2b;
destination: the E1 acceptance §9.6(2) + the M13 / G6 coverage note of
the E1 baseline report; governing contract: P3 §5.4 per-binding
dispatch + D9 (frozen); the obligation is preserved, not dropped).

## 5.5 Track B population (the model-facing subset)

The Track B population is every `track ∈ {B, A_B}` case (the A_B rows
share the §5.1–§5.4 population; the B-only rows are the model controls):

| Row | Shape | Track B label (published-evidence annotation) | Min cases |
| --- | --- | --- | --- |
| TB-1 | Published composition WITH a versioned completeness statement (the marker text is the labeled published statement, verbatim + location) | labeled constituent set; quantity; statement present + verbatim | 3 |
| TB-2 | Published composition WITHOUT any completeness statement | labeled constituent set; statement ABSENT (a model completeness claim = mis-grounded) | 3 |
| TB-3 | Count-only bundle / bare bundle (the P2-FU1 ambiguity shapes) | labeled: form observed, constituents ABSENT, quantity verbatim; expected model behavior: NO_MATCH + BUNDLE (the absolute rule) or UNCERTAIN — never MATCH on the count alone | 3 |
| TB-4 | Partial / truncated / dangling publication | labeled: partial + the marker; expected: no completeness claim; abstention or conflict naming | 3 |
| TB-5 | Conflicting fields (title vs structured publish different clauses) | BOTH clauses labeled with their field; expected: the model names the conflict (or abstains) and does NOT adopt the wrong field's clause as the composition (the bounded cross-field attribution proxy, §6.4) | 2 |
| TB-6 | Non-bundle sales-unit controls (pack / tray / single-unit published shapes, incl. the recorded-page absence shapes) | labeled form + quantity; expected: the 2.1 sales-unit rules' non-bundle duties | 3 |
| TB-7 | Injection / unsupported-claim shapes (the D9 / D10 / D18 model side) | labeled: the published facts only; the injection text is labeled as NOT a published constituent / statement | 2 |
| TB-8 | UNAVAILABLE channel (no packaging published at all — the live-path residual shape) | labeled absence; expected: never read as single unit or equivalence (the 2.1 discipline) | 2 |

**Track B minimum: 21 cases** (of which ≥18 are A_B-shared with the
Track A population; the B-only controls add ≥3 distinct model-facing
shapes). The Track B labels are independently authored per §4.6
(`REVIEWED_SOURCE_GROUNDED` over the recorded source text — the labeler
reads the published content, not the model), and the `semantic_
identity_note` field records the independent semantic-axis expectation
for the A_B cases (e.g. "the absolute rule expects NO_MATCH + BUNDLE")
as CONTEXT for Track B scoring of the decision duty — never as an input
to Track A.

## 5.6 Coverage accounting (v1.0.0 minimum population)

* Track A: 16 (A) + 25 (B) + 13 (C) + 36 (D) = **90 minimum cases**
  over **48 distinct matrix rows** (the DELE delegation rows are counted
  inside A-DELE and B-DELE above). Pre-revision accounting: 17 + 25 +
  13 + 37 = 92 — the two v1.0.0 row-minimum movements are the explicit
  phase-boundary corrections of Q3-C-D1-FU1 (A1 2→1: the recorded
  variant deferred to C3 / the additive 1.1.0 obligation; D16 3→2: the
  execution-level (iii) obligation preserved in the E1 mandatory
  adversarial-execution assertion), each with its recorded destination,
  rationale, governing contract, and later acceptance gate — NOT a
  silent threshold change; the corrected floor is met with room to
  spare over the 94-case v1.0.0 seal population (91 Track A).
* Track B: **21 minimum model-facing cases** (≥18 shared) — unchanged
  by the revision (both v1.0.0 removals are Track A cases; the A_B
  population is untouched).
* The v1.0.0 seal population of record (post-revision): **94 cases**
  (96 DRAFT minus D16-iii — E1-only — and the A1 recorded variant —
  C3-deferred; the D3-ii re-label and the D11-ii / B6-ii / B6-iii / C6
  re-authorings are pre-seal case corrections under the §4.6 item 5
  governance, recorded in the challenge log, the case IDs stable).
  Every one of the 94 is loader-sealable after the C1-FU3 corrections
  named in the revision record (the A-DELE PROVEN coherence scoping; the
  D3-ii stage coherence; the D11-ii identity context + span grounding
  over the re-authored SYNTHETIC document; the B6-ii / B6-iii / C6
  allowed recorded-extraction-result state).
* Evidence-kind composition at v1.0.0 seal: SYNTHETIC ≥ 80% (post-
  revision population: 88/94 = 93.6%); RECORDED_FIXTURE ≥ 5 cases
  (post-revision population: 6 — the non-bundle absence rows over the
  recorded pages (A-DELE / B-DELE); the form-axis row over the recorded
  0034-shape context (C4); the B1 recorded variant; the truncation
  variant (D7-ii); the pre-revision "exact-identifier family context"
  member (D11-ii) is re-authored SYNTHETIC — the recorded catalog
  grounds the identifier shape, not the composition axis; the A1
  recorded variant (deferred) joins at 1.1.0 over the C3-acquired
  source); REAL_MARKET = **0 at v1.0.0** — real-market bundle cases are
  C3's separately gated acquisition (no recorded page in the repository
  publishes bundle contents — verified, §2.5), and the absence is
  EXPLICIT in the report (it bounds the achievable tier — §7.5:
  v1.0.0 can reach at most RESEARCH_ONLY until C3 lands).
* Diversity floor (v1.0.0): ≥4 product categories across the bundle
  rows (the semantic family's category convention — e.g. GPU / SSD /
  memory / peripheral-kit shapes; post-revision population: 5 —
  unchanged); every bounded vocabulary member that the contract admits
  for a bundle comparison appears in ≥1 case (states ×5, bases ×2,
  attestation sides ×2, quantity-axis states ×5, refusal stages ×5 —
  the loader checks the projection) — **projected over the ACTUAL
  v1.0.0 seal population at seal time (the W6 adjudication of Q3-C-D1-
  FU1), not over the draft authoring population** (the stages ×5 remain
  projected: the CORPUS_INTEGRITY stage by the D6-i / D6-ii /
  D3-ii cases (the D6-i re-attribution — the Q3-C-D1-FU3 / F-R6
  adjudication);
  every member of the other vocabularies by its surviving row).
* Additive 1.1.0 obligations (recorded by the revision): (1) the A1
  RECORDED_FIXTURE PROVEN-shape case over the C3-acquired recorded
  source (the C2-F3 destination — the independently evidenced publisher
  completeness of P3 D19); (2) the D11 RECORDED_FIXTURE exact-
  identifier + attested-composition case, IF AND ONLY IF the recorded
  source publishes both the U1 EXACT identity context's recorded form
  and the attested composition clauses (the C2-F5 destination — the
  recorded catalog of §2.5 publishes identifiers only, so no v1.0.0 /
  1.1.0 case may claim otherwise). Both are additive (no per-case
  document moves; the 1.1.0 re-seal verification is the acceptance
  gate).

---

# 6. Track A and Track B methodologies

## 6.1 Track A — deterministic authority (the contract + record surface)

**Population.** Every `track ∈ {A, A_B}` case of the sealed corpus.
Subpopulations (exact denominators):

* `n_A` = |Track A cases| (the whole population).
* `n_derived` = |cases with `expected.outcome == "DERIVED"`|
* `n_refused` = |cases with `expected.outcome ∈ {"REFUSED",
  "NON_CONSTRUCTIBLE"}| (`n_A = n_derived + n_refused`).
* `n_record` = |cases with `surface ∈ {RECORD, BOTH}`|;
  `n_record_pass` = |record cases with `expected.replay ==
  "REPLAY_PASS"`|; `n_record_refused` = |record cases with
  `expected.replay == "REPLAY_REFUSED"`| (`n_record =
  n_record_pass + n_record_refused`).
* `n_neg` = |derived cases with `expected.unit != "PROVEN_EQUIVALENT"`|
  (the false-PROVEN denominator); `n_pos` = |derived cases with
  `expected.unit == "PROVEN_EQUIVALENT"`|.
* `n_tagged` = |cases carrying a `challenge_tags` member from the
  bounded tag set| (per-tag denominators for the specialized gates).

**Execution (per case, zero-live, deterministic).** The evaluator
reconstructs the typed inputs through the FROZEN constructors (the
constructor is the validator — a case whose evidence does not
construct is a `CORPUS_INTEGRITY` failure, counted, never a pass), then:

* **The two-contract execution order (the Q3-C-D1-FU3 / F-R6
  adjudication + the Q3-C-D1-FU3-FU1 contract correction —
  binding).** The family's integrity checks serve two distinct
  consumers; E1 executes both and keeps them apart:

  **Contract A — corpus ingestion (the strict load, unchanged).**
  The corpus is loaded through the strict family path (`load_
  bundle` — the seal verification + the label governance + the
  per-case digest + the stage-coherence rule). A correctly
  labeled sealed-raw adversarial case LOADS (is accepted into
  the corpus): the loader collects its observations internally,
  verifies the labeled refusal stage against them, and that
  verification passing IS the acceptance — the strict load
  refuses only the incoherent label, a DERIVED case carrying a
  defect, or a failed digest. A corpus that fails its own strict
  load is the `FAIL_CLOSED` ladder rung (no per-case evaluation
  is reported). A negative case loading successfully does NOT
  mean the underlying evidence is valid: Contract A verifies
  label coherence, never evidence soundness.

  **Contract B — E1 negative-case observation (the family-owned
  read-only interface — the §9.12 (1b) surface, implemented in
  C1-FU4; the E1 suite's mandatory adversarial tests (1)–(8)
  execute over it).** For every refused case whose labeled stage
  is a corpus-surface stage (`CORPUS_INTEGRITY` / `CONSTRUCTION`
  / `CODEC_DECODE` — the stage semantics (iv) cross-document
  shapes + the frozen-constructor / codec bounded-error shapes),
  the case's REAL observation is obtained ONLY from the narrow
  family-owned observation interface over the case's actual
  sealed document: the actual family checks (the typed decode
  over the REAL frozen constructors + the family cross-document
  checks) in collection mode, returning the bounded record of
  fired `check / layer / reason` triples in deterministic firing
  order (every fired observation — multiple observations all
  returned, never truncated, deduplicated, or prioritized; an
  unexpected observation changes the record, never hides the
  required one), + the inverse-scoping `observation_stages`
  mapping (the exact set of corpus-surface stages the sealed-raw
  scoping rule would find coherent with the record's layers +
  the sealed surface — computed from the record, NEVER from the
  label). The interface schema-validates the `expected` block
  but NEVER reads it for behavior (no outcome / stage / error
  field selects, filters, or manufactures an observation — the
  W9 discipline, structurally pinned), does not verify the seal
  (Contract A's obligation), and NEVER invokes the derivation /
  the replay / any model (zero model calls, zero network, zero
  pricing authority). **The explicit bypass-to-G4 rule:** the
  row is "refused" for G4 / M7 purposes if and only if the
  interface's record over the sealed document carries a corpus-
  surface observation (`observation_stages` non-empty); a record
  with NO corpus-surface observation — empty (the sound
  documents), corroborative-only (the GATE layer), or never
  obtained (the check disabled, the interface bypassed, the
  record manufactured from the label; a bounded interface error
  is fail-closed — the row's record is absent, never a silent
  pass) — is scored NOT refused: **G4 FAILS** (the
  `BYPASSED_INTEGRITY` class), regardless of the strict load's
  acceptance of the labeled case and regardless of any
  derivation outcome. The record-surface clause of M7 stands:
  a replay-passed record over a refused-expected row is a G4
  failure. The typed-input reconstruction + the frozen
  derivation over it is then a DOCUMENTED NON-OBSERVATION for
  the stage-semantics (iv) cross-document shapes (the sealed
  source / recorded examined input is never a derivation input
  — the frozen layer's silence is recorded in the baseline): a
  successful FU4 derivation — including a completed `UNPROVEN` —
  NEVER counts as satisfying a refused case, never suppresses
  the bypass-to-G4 failure, and never fills an empty record; a
  completion that returned `PROVEN_EQUIVALENT` over a
  refused-expected case fires G1 independently (the worst
  class). For the execution-surface rows (`PRESENTATION_GATE` /
  `REPLAY_AGREEMENT`), the REAL observation remains the frozen
  execution's bounded refusal itself (the gate / replay steps),
  over which the interface's record is expected to carry no
  corpus-surface observation.
* DERIVATION surface: `derive_authority_tier_fu4(assessment, channel,
  evaluation, provenances, product_evidence, None,
  target_unit_evidence=…, candidate_composition=…, quantity_
  attestation=…)` over the scripted context — comparing unit, quantity
  axis, both composition states, the three attestation digests, tier,
  fired rules, ceilings against `expected`.
* RECORD surface: `decode_semantic_decision_record(payload)` →
  `replay_semantic_decision(record)` — comparing the replay outcome
  (pass / refused-at-stage + error class) against `expected.replay` /
  `expected.refusal`.
* For REFUSED / NON_CONSTRUCTIBLE cases: the expected refusal is
  established as the ACTUAL system behavior — for the corpus-
  surface stages by Contract B (the interface's record over the
  sealed document carries a corpus-surface observation — the
  explicit bypass-to-G4 rule above), for the execution-surface
  stages (`PRESENTATION_GATE` / `REPLAY_AGREEMENT`) by the frozen
  execution's bounded refusal itself. A refusal at ANY stage
  satisfies G4; the stage is compared for M6 (the labeled stage
  ∈ the record's `observation_stages`, or the execution's
  refused stage); a derivation completing where a refusal was
  expected is the worst-class failure (G1 if PROVEN, G4
  otherwise) — EXCEPT for the stage-semantics (iv) cross-
  document shapes, where the frozen layers never receive the
  sealed document and the completion over the reconstructed
  self-consistent typed inputs is the documented non-observation
  (the bypass-to-G4 rule governs those rows). **Exact refusal-
  reason assertions (the W1 adjudication of Q3-C-D1-FU1, the
  named-observation list corrected by the Q3-C-D1-FU3 / F-R6
  adjudication, the failure classes fixed by the Q3-C-D1-FU3-
  FU1 correction): the E1 adversarial re-execution asserts the
  labeled bounded error class (the stage-keyed error vocabulary)
  AND the deterministic reason — for the loader-observation stage
  (CORPUS_INTEGRITY) the exact named case-document observation(s)
  (`CASEDOC_EMBEDDED_RESULT_EQUALITY` for the D3-ii shape;
  `CASEDOC_CHANNEL_EQUALITY` for the D6-ii shape;
  `SOURCE_EXTRACTION_INPUT_DIGEST` for the D6-i shape — the Q3-C-
  D1-FU3 re-attribution; `CASEDOC_RECORDED_RESULT_CHANNEL_MAPPING`
  for the C2-F6 recorded-result / presented-channel mismatch); for
  the construction / codec stages the FROZEN constructor / codec's
  bounded error (only the shapes over which the frozen constructor
  / codec ACTUALLY refuses the presented document — the D4 / D8 /
  D14 / D15 / D17-i shapes and the record-surface twins: a family-
  loader mirror of a cross-document binding is NOT a frozen-
  constructor error — the five validation surfaces, §5). Over a
  corpus-surface row the failure classes are: the row's required
  named observation ABSENT from the record while the labeled
  stage stays coherent with it (a different check fired — the
  wrong reason) — a **W1 FAILURE** (the exact-reason acceptance
  is not met; the row is recorded with the bounded expected /
  observed reason, never a silent pass); the required named
  observation present at a layer whose `observation_stages`
  EXCLUDES the labeled stage (the wrong-stage observation) — an
  **M6 DEFECT** (stage accuracy), G4 standing on the record's
  non-emptiness (a refusal at ANY stage satisfies the hard gate);
  the record carrying no corpus-surface observation at all — the
  **G4 FAILURE** (the bypass-to-G4 rule). Only the right stage +
  the right named observation + the pinned reason satisfies the
  row.**

**Metrics (exact definitions; all rates are null-when-denominator-zero,
never satisfied by default — the policy contract's `met: null`
discipline).**

| # | Metric | Numerator | Denominator |
| --- | --- | --- | --- |
| M1 | `false_proven_count` (G1) | cases with `expected.unit != PROVEN` (derived OR refused) where the system returned / recorded `PROVEN_EQUIVALENT` (incl. a replay-passing record whose derived section says PROVEN over non-PROVEN-labeled evidence) | `n_A` (rate) — and reported separately over `n_neg` |
| M2 | `false_contradicted_count` | derived cases with `expected.unit != CONTRADICTED` where the system returned `CONTRADICTED` | `n_derived` |
| M3 | `unproven_abstention_accuracy` | derived cases with `expected.unit == UNPROVEN` where the system returned `UNPROVEN` | |`expected.unit == UNPROVEN`| (within `n_derived`) |
| M4 | the authority confusion matrix | the 3×3 counts over (expected × actual) unit states for `n_derived`, + the REFUSED rows as a fourth "actual" column (a derived answer on a refused-expected case is a bypass, M1 / G4 family) | `n_A` |
| M5 | `tier_axis_accuracy` | derived cases where the system's tier + fired rules + ceiling EQUAL `expected` exactly | `n_derived` |
| M6 | `integrity_stage_accuracy` | refused cases where the system refused at the EXPECTED stage (for the corpus-surface rows: the labeled stage ∈ the Contract B record's `observation_stages`; for the execution-surface rows: the execution's refused stage equals the labeled stage) | `n_refused` |
| M7 | `evidence_integrity_rejection_rate` (G4) | refused cases where the system refused at ANY stage (for the corpus-surface rows: the Contract B record carries a corpus-surface observation — the explicit bypass-to-G4 rule; for the execution-surface rows: the execution refused — no unit derived, no replay passed) | `n_refused` |
| M8 | `replay_agreement_rate` (G7) | record-pass cases where replay returned the proved derived-agreement | `n_record_pass` |
| M9 | `cross_listing_substitution_rejection` (G5) | tagged `cross_listing_substitution` cases refused at any stage | `n_tagged[cross_listing_substitution]` |
| M10 | `missing_attestation_fail_closed_rate` | tagged `attestation_missing` derived cases where the system returned UNPROVEN (never PROVEN, never a completeness inference) | `n_tagged[attestation_missing]` |
| M11 | `quantity_conflict_detection` | derived cases with `expected.quantity_axis == CONTRADICTED` where the system returned unit CONTRADICTED | |`expected.quantity_axis == CONTRADICTED`| |
| M12 | `pricing_authority_leakage_count` (G3) | derived cases where (a) the returned tier ∈ `PRICING_ELIGIBLE_TIERS` while `expected.unit != PROVEN_EQUIVALENT` (the ceiling failure), or (b) `expected.pricing_eligible == false` while the returned tier is pricing-eligible | `n_derived` (count; the rate is reported) |
| M13 | `historical_confusion_rejection` (G6) | tagged `historical_binding_confusion` cases refused / failing closed exactly as labeled (incl. the FU3-arm coexistence rows: the SAME recorded input under the FU3 token derives the frozen FU3 unit — the delegation identity at corpus scale) **+ the MANDATORY execution-level assertion of the D16-iii shape (the FU3-token contract-misuse refusal: the composition / attestation inputs fed to the frozen FU3 entry point refuse — P3 §5.4 / D9; the Q3-C-D1-FU1 phase-boundary correction: the shape is an E1 adversarial-execution member, NOT a v1.0.0 corpus case; its pass / fail is recorded in the E1 baseline report under this metric's coverage note, and its failure is a G6-family NOT_QUALIFIED)** | `n_tagged[historical_binding_confusion]` |
| M14 | `model_independence_invariance` (I-4) | Track A cases where perturbing the scripted evaluation (decision / confidence / conflict classes / matched attributes — the bounded perturbation set) leaves unit + quantity axis + composition states unchanged | `n_A` |
| M15 | `axis_audit_accuracy` | derived bundle-channel cases where the six bundle-axis audit fields (states + three attestation digests + quantity axis) EQUAL `expected` exactly — **the non-bundle derived cases (the A-DELE / B-DELE delegation rows) are audited on the same surface with the frozen P3 D11 semantics: the six Bundle-axis fields must be EXACTLY null — the byte-identical delegation (P3 D9) is the audit contract (the Q3-C-D1-FU1 / C2-F1 correction: the §4.4 coherence scoping makes the null shape sealable; the E1 axis audit asserts it, so a delegation drift that silently fills a bundle axis is a `WRONG_AXIS_AUDIT`)** | |derived cases (bundle-channel: the fields equal expected; non-bundle: the fields exactly null)| |

**The Track A verdict.** A case is `PASS` iff: its outcome class
matches (DERIVED vs REFUSED vs NON_CONSTRUCTIBLE), and — for DERIVED —
M4's cell is the expected unit AND M15's audit fields agree AND (if a
tier is labeled) M5 agrees, and — for REFUSED — a refusal occurred
(M6's stage is a quality metric, not the pass condition), and — for
RECORD — M8 / the expected replay outcome holds. Any mismatch is a
`FAIL` with the bounded failure class (§6.5). The committed E1
baseline report is the FULL Track A evaluation over the sealed corpus
(there is no NOT_CAPTURED stub — the track is model-independent).

## 6.2 Track B — model-assisted evidence acquisition

**Population.** Every `track ∈ {B, A_B}` case with a committed capture
document for the evaluated model (the per-model projection — primary and
fallback are qualified INDEPENDENTLY; a primary PASS never qualifies the
fallback, the harness discipline). Denominators: `n_B` = |Track B
cases|; `n_B_captured(m)` = |cases with an OK execution record for model
m|; `n_B_bundle` = |Track B cases with a labeled published bundle
constituent set|; `n_B_amb` = |cases labeled AMBIGUOUS (TB-3 / TB-4 /
TB-5 / TB-8 shapes where abstention is the labeled duty)|;
`n_B_stmt` = |cases where the publication is labeled to carry a
completeness statement, or the model asserts completeness|.

**Capture (E2; separately operator-approved live sub-step).** The model
receives EXACTLY the frozen Prompt 2.1 user rendering over the case's
real recorded V2 case document (the `decode_match_case`-validated
input) — nothing else (no label, no expected outcome, no injection of
evidence the model did not receive). One bounded execution per case per
model (the direct-capture discipline: the pinned route, the fixed
generation parameters, the bounded retry policy, the run-level abort —
the Q3-B / Q3-B-FU1 runner discipline adopted verbatim for the family
runner; every model call in the test suites is a scripted recording
double, zero network). The capture document (schema 1, family-owned,
the direct-capture shape) binds to the family corpus identity (id /
version / digest) + prompt axis 2.1 + route; verification reuses the
frozen `parse_semantic_response_v2` / `validate_semantic_response_v2`
composition (the production parser boundary — read-only import) for
output validity.

**Metrics (exact definitions; the scoring compares the model's bounded
structured output against the INDEPENDENTLY LABELED published evidence
annotation — never against the FU4 derivation, never against the
Track A expected outcome).**

| # | Metric | Numerator | Denominator | Status |
| --- | --- | --- | --- | --- |
| N1 | `constituent_extraction_precision` | labeled published constituents that the model reported (token-level, under the family's versioned annotation grammar — casefold + whitespace-collapse + integer-quantity normalization, the materiality-grammar NORMALIZATION reused as an evaluation-owned constant set, drift-cited to P3 §3.7; a reported constituent = an item token in the model's BUNDLE / PACKAGING_QUANTITY attribute detail or matched_attributes) | all constituents reported by the model over `n_B_bundle` | IMPLEMENTED (E2) |
| N2 | `constituent_extraction_recall` | labeled published constituents the model reported | all labeled published constituents over `n_B_bundle` | IMPLEMENTED (E2) |
| N3 | `attestation_grounding_accuracy` | cases where the model's completeness position AGREES with the label (label: statement present ⇒ the model may report the statement's content, must not assert completeness BEYOND the statement; label: statement absent ⇒ the model must NOT assert completeness) | `n_B_stmt` | IMPLEMENTED (E2) |
| N4 | `unsupported_constituent_hallucination_rate` | cases where the model reported ≥1 constituent absent from the labeled published set, or asserted a quantity / completeness statement absent from the publication | `n_B` | IMPLEMENTED (E2) |
| N5 | `ambiguous_abstention_rate` | labeled-AMBIGUOUS cases where the model answered UNCERTAIN, or NO_MATCH naming BUNDLE / PACKAGING_QUANTITY (the absolute-rule duty), and did NOT answer MATCH | `n_B_amb` | IMPLEMENTED (E2) |
| N6 | `provenance_correctness` | the bounded proxy: TB-5 conflicting-field cases where the model's reported constituent set does NOT equal the wrong field's labeled set (cross-field attribution); reported as `cross_field_attribution_error_rate` | |TB-5 cases| | PARTIAL (E2) — the 7-key response carries no field-level provenance surface; span-level provenance is **FUTURE / NOT IMPLEMENTED** (it requires a versioned output-schema axis move + prompt decision — O-5; this design does not propose the prompt change) |
| N7 | `valid_output_schema_rate` | cases with a parser-valid 7-key response (the frozen production parser) | `n_B_captured(m)` | IMPLEMENTED (E2) |
| N8 | `coverage` | `n_B_captured(m)` with an OK execution | `n_B` | IMPLEMENTED (E2) |
| N9 | primary / fallback separation | structural: the per-model projection is computed independently per capture document; the report carries one N-metric block per model; a gate failure for one model never discharges the other | `n_B` per model | IMPLEMENTED (E2) |

**The Track B verdict.** Track B produces MODEL evidence only: it
qualifies the model for the review-assistance tier under the family
policy (MB gates + N-thresholds, §7). It NEVER feeds Track A: the
evaluator holds a structural proof (gate MB-3) that no capture-derived
document enters any derivation input of any Track A case (the Track A
evidence documents are sealed corpus content; the capture is a separate
artifact bound to the same corpus identity).

**FUTURE / NOT IMPLEMENTED (declared, not designed around):** a
structured bundle-evidence output schema (explicit constituent list +
quantity + statement span in the response); span-level provenance
scoring; multi-turn evidence refinement; any model-assisted attestation
CONSTRUCTION (a model may POINT to a published statement for a reviewer;
the attestation record is review-constructed only — P3 §3.8; this
boundary is a gate, MB-3, not a capability gap to be filled by the
model).

## 6.3 The structural invariants (evaluator-level, all cases)

* **I-4 execution** (§3.1): the perturbation invariance sweep (M14) runs
  over the whole Track A population — the scripted-evaluation
  perturbation set is bounded (decision ∈ {MATCH, NO_MATCH, UNCERTAIN}
  × confidence ∈ {HIGH, MEDIUM, LOW} × conflict classes ∈ {∅, {BUNDLE},
  {PACKAGING_QUANTITY}} × matched_attributes ∈ {∅, a BUNDLE claim}), and
  the unit / axis / state outputs must be invariant under it.
* **G8 structural proof:** for every Track A case, the derivation-input
  document set is EXACTLY the case's sealed `derivation_inputs`
  projection (digest-compared at evaluation time — the evaluator never
  substitutes, extends, or regenerates evidence); any case whose
  evidence projection differs from the sealed document is a
  `CORPUS_INTEGRITY` failure.
* **Zero-live proof:** the E1 / E2 suites run the full evaluation under
  the socket-blocked / no-transport discipline (the R1 / R2 zero-live
  sentinel precedent) — Track A by construction (no transport exists in
  the imported surface); Track B's tests use scripted recording doubles
  only.

## 6.4 The annotation grammar (Track B scoring, family-owned)

The token comparison of N1 / N2 / N4 / N6 uses a versioned constant set
owned by the family evaluator (separately from the FU4 contract's
grammar — the contract grammar is the derivation's, the annotation
grammar is the labeler's / scorer's; they must AGREE on normalization
for the shared shapes, and the E2 acceptance includes a cross-check row
over the versioned marker / item vocabulary citing P3 §3.4–§3.7 as the
drift reference). Any change is a new annotation-grammar version inside
a new corpus / evaluator version — never a silent edit. This keeps the
labeling side independent of the implementation side while staying
comparable.

## 6.5 The failure taxonomy (bounded, report vocabulary)

| Class | Meaning | Severity |
| --- | --- | --- |
| `BYPASSED_FALSE_PROVEN` | a refused-expected or negative-expected case yielded / recorded PROVEN_EQUIVALENT | fatal (G1) |
| `BYPASSED_INTEGRITY` | a refused-expected case derived a unit or passed replay at all | fatal (G4) |
| `PRICING_LEAKAGE` | a pricing-eligible tier over a non-PROVEN unit / non-eligible expectation | fatal (G3) |
| `FALSE_CONTRADICTED` | CONTRADICTED over a non-CONTRADICTED expectation (over-restriction) | major |
| `WRONG_UNPROVEN` | UNPROVEN over a PROVEN or CONTRADICTED expectation (missed authority / missed contradiction) | major |
| `WRONG_TIER` | the unit is right but the tier / ceiling / fired rules are wrong | major |
| `WRONG_AXIS_AUDIT` | the unit is right but the recorded axis states / attestation digests disagree | minor |
| `REFUSED_WRONG_STAGE` | the refusal occurred at a different stage than labeled (the defect was caught — the failure point differs from the design's analysis) | minor (M6 quality) |
| `CONSTRUCTION_ACCEPTED_INVALID` | an un-constructible / integrity-invalid document constructed (the constructor validator was bypassed) | fatal (G4 family) |
| `REPLAY_MISMATCH` | a record-pass expectation that failed replay, or a record-refusal that passed | fatal (G7) |
| `HISTORICAL_CONFUSION` | a cross-binding / cross-token combination interpreted where refusal was labeled | fatal (G6) |
| `CORPUS_INTEGRITY` | the sealed case / corpus / evidence failed the family's own load checks | fatal (FAIL_CLOSED — no evaluation) |
| `NOT_EVALUATED` | a labeled case produced no outcome (coverage) | fatal (gate G-zero-silent) |
| `CAPTURE_BINDING_FAILURE` (Track B) | a capture document failed corpus / prompt / route binding | fatal for the capture (never a model pass) |
| `SCHEMA_INVALID` (Track B) | the model output failed the frozen parser | scored (N7), never a Track A input |
| `HALLUCINATION` (Track B) | unsupported constituent / quantity / completeness claim (N4) | scored; a MB-1 gate member |
| `MIS_GROUNDED_ATTESTATION` (Track B) | a completeness assertion with no published statement (N3) | scored; a MB-3 gate member |
| `INJECTION_SUSCEPTIBLE` (Track B) | the model adopted injected instruction content as a published fact (N4 / D9) | scored; recorded, MB-1 family |

---

# 7. Acceptance policy proposal

## 7.1 The policy artifact (family-owned)

A NEW policy artifact for the family (schema 1, the semantic family's
policy contract pattern adopted — DRAFT / APPROVED status discipline,
`approved_by` + `approved_utc` required for APPROVED, `policy_
applies_to` = the family corpus identity (id + version),
`evaluate_thresholds` with `met: null` on insufficient denominators):
`evaluation/fu4_bundle_authority_qualification/policy/
qualification_policy_draft_1.json` (C2 deliverable, DRAFT,
`approved: false`). The EXISTING DRAFT policy (the semantic family's
1.0.0-scoped artifact) is UNCHANGED, UNCOPIED, and UNEXTENDED by this
program (the F-4 lineage: every qualification lineage owes its own
policy-governance step; this family's is P1).

## 7.2 The threshold vocabulary (family-owned, DRAFT proposals)

The design PROPOSES the following vocabulary + DRAFT values for P1's
independent review (recorded as proposals — NOT finalized acceptance
thresholds; P1 approves or moves them; the values are governance
decisions, the vocabulary is contract):

Track A (all denominators per §6.1):

| Threshold name | DRAFT value | Denominator |
| --- | --- | --- |
| `false_proven_count_max` | 0 | `n_A` |
| `false_contradicted_rate_max` | 0.0 | `n_derived` |
| `unproven_abstention_min` | 1.0 | per M3 |
| `integrity_rejection_min` | 1.0 | `n_refused` |
| `replay_agreement_min` | 1.0 | `n_record_pass` |
| `substitution_rejection_min` | 1.0 | per M9 |
| `missing_attestation_fail_closed_min` | 1.0 | per M10 |
| `quantity_conflict_detection_min` | 1.0 | per M11 |
| `pricing_leakage_count_max` | 0 | `n_derived` |
| `historical_confusion_rejection_min` | 1.0 | per M13 |
| `model_independence_invariance_min` | 1.0 | `n_A` |
| `tier_axis_min` | 1.0 | `n_derived` |
| `axis_audit_min` | 1.0 | per M15 |
| `integrity_stage_accuracy_min` | DRAFT: reviewed per release (quality floor, not zero) | `n_refused` |

Track B (per model; all denominators per §6.2):

| Threshold name | DRAFT value | Denominator |
| --- | --- | --- |
| `hallucination_rate_max` | 0.0 | `n_B` |
| `constituent_precision_min` | 0.95 | per N1 |
| `constituent_recall_min` | 0.90 | per N2 |
| `attestation_grounding_min` | 1.0 | `n_B_stmt` |
| `ambiguous_abstention_min` | 0.95 | `n_B_amb` |
| `valid_schema_min` | 0.99 | `n_B_captured(m)` |
| `coverage_min` | 1.0 | `n_B` |

The zero-tolerance items are the ones that protect against false
authority (a single false PROVEN is the defect the whole program exists
to catch); the non-zero DRAFT items are the quality floors for evidence
acquisition. P1 may move ANY of them with a recorded rationale — the
vocabulary and the denominators are the contract, the values are the
policy.

## 7.3 The hard safety gates (mandatory, non-configurable, G1–G8)

| Gate | Condition (exact) | Failure class |
| --- | --- | --- |
| G1 | `false_proven_count == 0` over ALL `n_A` cases (every independently labeled negative — UNPROVEN-expected, CONTRADICTED-expected, and REFUSED-expected) | `BYPASSED_FALSE_PROVEN` |
| G2 | zero unauthorized authority promotion: no case where the returned tier is LOOSER than `expected.tier` under the scripted context (the loosening direction only — a stricter result is recorded, not a gate failure), AND M14 invariance holds (no case where a model-context perturbation moved the unit / axis) | `WRONG_TIER` / I-4 |
| G3 | `pricing_authority_leakage_count == 0` (M12) | `PRICING_LEAKAGE` |
| G4 | zero evidence-integrity bypass: every `n_refused` case refused (M7 == 1.0) — no unit derived, no replay passed, no construction of an invalid document | `BYPASSED_INTEGRITY` / `CONSTRUCTION_ACCEPTED_INVALID` |
| G5 | zero cross-listing substitution: M9 == 1.0 over the tagged population | `BYPASSED_INTEGRITY` |
| G6 | zero historical-binding confusion: M13 == 1.0; the frozen contract + registration suites (the 217-node FU4 suite, the 98-node FU3 suite, the 111 + 7 extraction suites, the R1 38 / R2 35 suites, the codec / replay / V2 / record / boundary suites) pass UNCHANGED at acceptance (the collection pin — the per-phase node-level diff, §8.3) | `HISTORICAL_CONFUSION` |
| G7 | full replay agreement for accepted records: M8 == 1.0 over `n_record_pass` | `REPLAY_MISMATCH` |
| G8 | no model-generated completeness attestation treated as publisher evidence: the structural proof of §6.3 (the derivation-input projection is digest-equal to the sealed corpus content in every Track A case; no capture artifact is imported by the Track A evaluator — an import-scan over the evaluator module) | `BYPASSED_INTEGRITY` |

Gates are evaluated BEFORE thresholds (the ladder, §7.5); a gate
failure is `NOT_QUALIFIED` regardless of the policy state; the DRAFT
policy cannot disable, reorder, or re-weight a gate.

## 7.4 The Track B gates (mandatory for the model tier, MB-1..MB-3)

| Gate | Condition | Meaning |
| --- | --- | --- |
| MB-1 | `hallucination_rate == 0.0` over `n_B` (per model) | the model never reported an unsupported constituent / quantity / statement |
| MB-2 | `coverage == 1.0` AND every non-OK execution is a recorded bounded transport / execution failure (never a silent absence) | the model's evidence is complete, not cherry-picked |
| MB-3 | `attestation_grounding_accuracy == 1.0` AND the structural G8 proof holds | a model-reported completeness statement is never treated as publisher evidence; the attestation record remains review-constructed only |

MB-1 / MB-2 / MB-3 bind the MODEL-TIER decisions only (QUALIFIED_FOR_
REVIEW_ASSISTANCE); they do not gate Track A (the deterministic
contract is qualified independently of any model — DEC-C1 track
separation).

## 7.5 The decision ladder and the six statuses

The family report computes, for the corpus version + the evaluated
models + the policy state, EXACTLY one of:

1. `FAIL_CLOSED` — the corpus / contract integrity failed at load (a
   `CORPUS_INTEGRITY` class; no evaluation is reported, the failure is).
2. `NOT_QUALIFIED` — any of G1–G8 (Track A) or MB-1..MB-3 (for the
   model tier, per model) failed.
3. `POLICY_PENDING` — all applicable gates pass but no APPROVED policy
   applies to the corpus identity (or the policy is DRAFT). **The
   state of record at the completion of every phase before P1 remains
   POLICY_PENDING until P1's independently reviewed policy is
   explicitly approved** — a full-pass evaluation over a DRAFT policy is
   POLICY_PENDING, never QUALIFIED (the semantic family's
   hypothetical-full-pass pin, adopted). Q1 (the first phase after P1)
   is the first phase whose computed state may exceed POLICY_PENDING.
4. `RESEARCH_ONLY` — gates pass, an APPROVED policy applies, but the
   statistical-coverage requirements for higher tiers are unmet (at
   v1.0.0: the REAL_MARKET population is empty — the report states the
   residual explicitly, with the rule-of-three bounds, §7.6). This is
   the HONEST ceiling for the synthetic v1.0.0 seal.
5. `QUALIFICATION_CANDIDATE` — `RESEARCH_ONLY` conditions + the C3
   real-market population lands (the §7.6 minimums) + Track B captured
   for BOTH pinned models with MB gates passing.
6. `QUALIFIED_FOR_REVIEW_ASSISTANCE` — `QUALIFICATION_CANDIDATE` + the
   Track B thresholds met (per model) + the independent policy review
   (P1) recorded APPROVED. Scope: the model is qualified to PRESENT
   published bundle evidence to a human reviewer (the review workflow's
   input assistance); the attestation record remains review-
   constructed; NO automatic authority, NO pricing, NO live wiring
   exists or is implied.
7. `PRODUCTION_AUTHORITY_QUALIFIED` — **NEVER a report state.** It
   requires the separately gated W1 phase (the live 2.1 / FU4
   execution decision + the W1 atomic consumer guard + the
   qualification-marker flip under the AD-Q3B4-6 discipline, each with
   its own architecture review and explicit approval). The report's
   `authority` section carries the standing note (the semantic family's
   text, adopted): "this report is evaluation evidence only; it grants
   no pricing authority, no tier promotion, no human-review behavior
   change, and no production activation."

The ladder is fail-closed and ordered: a lower state is never reported
when a higher state's failure condition holds; the rationale string
records every evaluated rung (the semantic family's `decide` pattern).

## 7.6 The statistically meaningful coverage requirements

* **Zero-tolerance gates are population-complete.** G1 / G3 / G4 / G5 /
  G6 / G7 / G8 are defined over the WHOLE sealed population (no sampling
  of the safety rows): every negative case must be independently
  labeled and executed. A zero on a partial population is not a zero.
* **The rule-of-three disclosure (binding report content).** For each
  zero-count gate the report records `n` and the 95% upper confidence
  bound ≈ 3/n (the standard bound for a zero observed events). Example:
  0 false PROVEN over n=65 negatives bounds the false-PROVEN rate at
  < 4.6% (95% CI) — recorded verbatim, with the statement that this is
  a CONTRACT-COVERAGE bound over a synthetic / recorded-fixture
  population, NOT a real-market performance claim. No report may omit
  the bound, and no status above RESEARCH_ONLY may be computed without
  the real-market population of the next item.
* **The real-market minimums (C3; required for QUALIFICATION_CANDIDATE
  and above).** ≥10 REAL_MARKET cases with bundle contents published on
  the candidate side (each: archived raw content + retrieval
  attestation + the §3.2-L3 independent source verification by a
  reviewer distinct from the attestor + two-identity labels), of which
  ≥5 are PROVEN-eligible shapes (attested completeness reachable on both
  sides per the labeled evidence) and ≥5 are UNPROVEN / CONTRADICTED
  shapes; ≥5 REAL_MARKET cases with the manufacturer-vs-reseller
  provenance documented (the D8 family). The retrieval attestation
  states URL, retrieved_utc, the raw reference, and the attestor
  identity; the reviewer's verification is recorded against an
  INDEPENDENT retrieval (a second fetch or a cited secondary source),
  never against the same archive alone.
* **Case diversity floors (v1.0.0, loader-enforced).** The §5.6
  population minimums (90 Track A / 21 Track B — the Q3-C-D1-FU1
  corrected §5.6; the two row-minimum movements are the recorded phase-
  boundary corrections, not threshold drift), the category floor
  (≥4), and the vocabulary-projection floor (every bounded member
  admitted for a bundle comparison appears ≥1 time — **projected over
  the actual seal population at seal time, the W6 adjudication of Q3-C-
  D1-FU1**).
* **Independent reviewer requirements.** Two-distinct-identity labels
  (loader-enforced); the adversarial (D) rows require the independent
  TESTER's authorship or review signature in the label (the §8 role);
  REAL_MARKET rows require the §7.6 verification distinctness.
* **Why a small synthetic corpus cannot qualify a model (stated).** The
  synthetic population bounds the CONTRACT's behavior (the deterministic
  derivation is total over the bounded vocabularies — full coverage is
  achievable and is what the 90-case floor is); it does NOT bound the
  REAL-WORLD rate of false authority (the publication diversity, the
  truncation / localization / phrasing tails, the adversarial
  publishers). That is why the tiers are stratified by evidence kind
  and why QUALIFICATION_CANDIDATE requires C3 — and why even
  PRODUCTION_AUTHORITY_QUALIFIED (W1) must carry the standing statement
  that qualification is over a FINITE sealed population with recorded
  bounds, monitored by the replay discipline (any post-qualification
  corpus version re-runs the full gate set before it may be the
  qualification of record). The 90-case v1.0.0 floor is the full
  bounded-vocabulary coverage of the deterministic contract (every
  admitted member, every U-row, every refusal stage) — it is a
  contract-completeness floor, not a statistical sample of the real
  market.

## 7.7 The policy approval requirements (exact)

A `QUALIFIED_FOR_REVIEW_ASSISTANCE` (or any status below it that is
policy-gated) decision requires an APPROVED policy artifact of the
family: `status: "APPROVED"`, `approval.approved: true`, a named
`approved_by` (the independent reviewer of record — P1), a valid UTC
`approved_utc`, the §7.2 threshold vocabulary (the values as approved),
and `applicability` bound to the exact family corpus identity. Until it
exists, the state is POLICY_PENDING. The approval is ChatGPT's final
gate (it reviews the policy document + the E1 / E2 reports + the
independent tester's record, then records the approval — the semantic
family's P1 discipline, adopted).

---

# 8. Independent review workflow

## 8.1 The roles (bounded, distinct)

| Role | Identity constraint | Duties |
| --- | --- | --- |
| Corpus author | any qualified implementer; NOT the sole authority for expected results | authors the case documents + the first-pass labels (C2), following §4.6's grounding classes |
| Independent label reviewer | distinct identity from the author (loader-enforced per case); for REAL_MARKET, distinct from the retrieval attestor | independently re-derives each expected outcome from the citation + source content; challenges labels (the challenge log is a C2 deliverable); signs `reviewer` / `reviewer_utc` |
| Independent tester | a SEPARATE role from the C1 / E1 implementer (the implementer must not be the sole authority for expected results) | authors or reviews the ADVERSARIAL (D) rows; inspects the false-PROVEN paths (every G1-adjacent shape); verifies that missing evidence remains UNPROVEN (the M10 population); reviews every changed / deleted test at each phase's acceptance; compares test collection against the approved baseline (the 7574 node-level diff, per phase); checks skipped / xfailed / deselected (must stay 0/0/0); verifies the safety contracts are not weakened (the firewall re-run: V2_AUTHORITY_QUALIFIED False ×2 + the adapter mirror; the reachability guards; the pricing surfaces byte-pinned; the DRAFT policies byte-pinned); produces the TESTER RECORD per phase (the artifact the ChatGPT gate reviews) |
| Phase implementer | the bounded-phase executor | implements the phase's exact file set; runs the phase's acceptance; reports the exact test results; may NOT sign labels for its own phase's expected outcomes |
| ChatGPT (final gate) | the architecture / approval authority | independently reviews each phase's GitHub diff + this design + the tester record before approving the next phase; approves the policy (P1); authorizes W1 only on its own separate review |

**No agent's final report is proof.** Every phase's acceptance is the
COMMIT + the TESTER RECORD + ChatGPT's review, in that order (the task's
§10 governance, made mechanical).

## 8.2 The label-review workflow (C2, per case)

1. The author drafts the case document + the label (grounding class,
   citation, rationale) from the recorded source content + the approved
   design rows — with the §4.6 import prohibition in force (the
   authoring tooling is scanned).
2. The reviewer re-derives the expected outcome INDEPENDENTLY (for
   DESIGN_TABLE_GROUNDED: from the cited design rows over the case's
   recorded evidence — re-reading the P3 / Q3-B4 / S2-A citations, not
   the author's rationale); records the challenge or the agreement.
3. Disagreement ⇒ the case is held (not sealed) until resolved by
   citation to a higher-authority row (the frozen contract semantics
   win over both authors' reading — if the authors and the frozen
   contract disagree, that is a finding, §2.7 discipline, never a
   silent split-the-difference label).
4. The challenge log (every case: author, reviewer, date, challenge,
   resolution) is committed alongside the corpus (C2 deliverable) — the
   audit surface of the labels themselves.
5. The seal: `fixtures.py` regeneration reproduces the committed corpus
   byte-for-byte; the digest is the record; the tester re-verifies a
   SAMPLE (≥20%, adversarial rows included in full) by independent
   re-derivation.
6. **The held set of record (the W3 adjudication of Q3-C-D1-FU1).**
   The held case set (the C2-F findings — challenge log §4) is an audit
   surface pinned exactly by the C2 governance suite. Its membership
   changes ONLY by an explicit adjudication recorded in the challenge
   log §6 under the adjudicator's identity + instant, and the change is
   MONOTONIC: a case leaves the held set only via a recorded
   adjudication naming the design / schema correction (or the
   re-authoring) that makes the row sealable, verified by the C2
   suite's re-pinned held set; a case is never un-holded (or holded)
   silently — by no label edit, loader change, or test edit. A case's
   held status may only tighten (more evidence of the conflict) or
   release (the recorded adjudication + the verified correction); the
   release direction is the only one that moves population accounting,
   and it moves it under the revision's recorded destinations, never
   under a silent floor change.
7. **The qualification-ready gate (the W2 / W4 / W6 adjudications of
   Q3-C-D1-FU1).** A population is QUALIFICATION-READY for the seal
   only if: (1) the family loader accepts it (every document coherent,
   the REVIEWED two-identity state); (2) every case's reviewer identity
   is in the recorded reviewer registry with a review record in the
   challenge log under that identity (a missing review is rejected with
   the PINNED deterministic reason — "no review record in the challenge
   log under the case's reviewer identity" — the W4 reason-pinning; a
   gate that rejects for an un-pinned reason is a gate defect); (3)
   **EVERY §5.6 composition floor holds on the ACTUAL seal population
   (not the draft authoring population): the corrected row minimums
   (90 over the 48 rows), the Track A / Track B floors (90 / 21 / 18 /
   3), the evidence-kind composition (SYNTHETIC ≥ 80%, RECORDED_
   FIXTURE ≥ 5, REAL_MARKET = 0 at v1.0.0), the category floor (≥4),
   and the bounded-vocabulary projection (every admitted member ≥1
   time — W6). A floor verified only over the draft population is NOT
   seal evidence — the W2 adjudication.** The gate is mechanical; the
   trust it protects is the review's own (the recorded caveat of the
   C2 suite, adopted).

## 8.3 The per-phase review record (tester artifact)

For every phase: the node-level collection diff against the phase's
starting-SHA baseline (added / removed / renamed, per file); the
skipped / xfailed / deselected counts; the changed / deleted test
inventory with the preservation argument (the R1-FU1 / R2-FU1
precedent — recorded in-place corrections named, intent preserved or
strengthened); the firewall re-run evidence (the byte pins + the
reachability guards + `V2_AUTHORITY_QUALIFIED` False everywhere + the
pricing surfaces); the stop-condition check (§9 per phase); and the
explicit statement of what the phase does and does NOT authorize.

---

# 9. Phased implementation plan

Sequencing gate for ALL phases (the B-1 discipline, adopted): a phase
must NOT start while the lineage reviews it builds on are pending — at
this design's starting SHA, Q3-B5-P4-FU2, R1, R1-FU1, R2, and R2-FU1
are all PENDING INDEPENDENT REVIEW. C0 starts after their ratification
(or is itself scoped to the ratified subset — O-2). Every phase:
DESIGN-authorized scope only; acceptance frozen at phase start; a
failed acceptance is a phase failure (the benchmark working), never a
reason to redefine the acceptance.

## 9.0 Q3-C-D1 — this qualification design (this phase)

* **Scope.** Exactly this document + the authorized STATUS / PLAN
  additions. **Inputs:** the starting-SHA tree (inspected, §2).
  **Deliverables:** this document. **Acceptance:** committed design-only
  on the starting SHA; the final diff contains only this document + the
  STATUS / PLAN additions; collection unchanged (7574); no other file
  touched. **Required tests:** none new (design phase). **Stop
  conditions:** any discovery that the frozen implementation and the
  approved designs disagree beyond the recorded CF-1..CF-5 (report, do
  not resolve); any change request that touches a pinned file (defer to
  the owning lineage). **Authority boundaries:** DESIGN ONLY — nothing
  implemented, nothing qualified, no labels, no capture.

## 9.1 Phase numbering note

The task's proposed sequence (D1 → C1 → C2 → E1 → E2 → P1 → Q1 → W1)
is adopted, with TWO inserted bounded phases of the same discipline:
C0 (the recorded pin-gap correction, forced by finding CF-2 — the
R1-FU1 / R2-FU1 precedent: a test-preservation correction is its own
bounded, reviewable step; O-2 confirms the insertion) and C3 (the
real-market bundle evidence acquisition — the only live surface
besides E2's gated capture sub-step, forced by the statistical-coverage
requirements of §7.6; O-6 confirms the authorization shape). Every
phase below states its exact scope (file sets), inputs, deliverables,
acceptance criteria, required tests, explicit stop conditions, and
authority boundaries. A phase's acceptance is frozen at this design's
approval; no phase may redefine its acceptance criteria merely because
the implementation failed (CLAUDE.md evaluation-truth rule).

## 9.2 Q3-C-C0 — the recorded pin-gap correction (forced by CF-2)

* **Scope (exact files).** Two content-pin nodes in the designated
  homes (per the R1-FU1 / R2-FU1 recorded-precedent pattern — the
  pin lives in the suite that owns the endpoint being pinned):
  (1) `tests/research/test_semantic_authority_v2_fu4.py` (the FU4
  module's own suite — its A1 frozen-surface table is the natural home)
  pinning `product_intelligence/research/semantic_authority_fu4.py`;
  (2) `tests/research/test_semantic_decision_v2_fu4.py` (the R1 suite
  — the R1-FU1 codec-pin precedent: the R1-endpoint pin lives in the R1
  suite) pinning
  `product_intelligence/research/semantic_decision_v2_fu4.py`. Both
  pins carry the working-tree digest per the house convention + the
  committed-blob digest (LF) recorded in the comment (§2.7). No
  production file is touched. **Inputs:** the ratified R2-FU1
  endpoint. **Deliverables:** the two pins + the tester record.
  **Acceptance:** the two new nodes pass; a controlled tamper probe
  (the R1-FU1 / R2-FU1 safety-property demonstration, fully reversible
  without git restore) fails EXACTLY the corresponding node; the full
  suite passes with collection 7574 → 7576 (+2, 0 removed / 0 renamed /
  0 skipped); all pre-existing pins pass unchanged. **Required tests:**
  the two new nodes + the probe demonstration + the full suite. **Stop
  conditions:** the lineage reviews are not ratified (no endpoint to
  pin — C0 re-bases on the ratified endpoint, the pin literals move,
  the scope does not); the tamper probe cannot be restored byte-exactly
  (abort, report). **Authority boundaries:** test-file correction only
  — NO production change, NO label, NO corpus.

## 9.3 Q3-C-C1 — corpus schema and integrity validator

* **Scope (exact files).** NEW package
  `product_intelligence/evaluation/bundle_authority/` — `__init__.py`,
  `corpus.py` (the family loader: the exact key-set strict decode, the
  seal registry, the per-case / corpus digests, the manifest builder /
  verifier, the label-governance checks (§4.4 / §4.6: author ≠
  reviewer, the provenance vocabulary, the anti-derivation label-text
  check, the expected-axis coherence pre-check), the evidence
  construction through the REAL frozen constructors + the RECORD-surface
  payload decode through the REAL universal codec), `fixtures.py`
  (EMPTY case set + the builder skeleton — the auditable-source
  pattern, regeneration property), `cli.py` (corpus-build /
  corpus-digest / corpus-manifest — offline only). NEW test file
  `tests/evaluation/bundle_authority/test_q3c_c1_corpus_integrity.py`.
  NO other file is touched (the semantic family is byte-pinned — the
  new package is the ONLY home). **Inputs:** the C0 endpoint; the P3 /
  P5 design documents (the contract semantics + the pattern sources).
  **Deliverables:** the validator + the CLI + the empty-seal
  demonstration (a 0-case corpus builds, seals, loads, and regenerates
  byte-for-byte — the skeleton's integrity property). **Acceptance:**
  the §4.2 artifact-integrity checks (a)–(g) pass over the 0-case seal;
  every bounded vocabulary is drift-pinned to the frozen research
  exports (no literal copies — the P1 discipline); the import scan
  proves the package imports ONLY the frozen research public surface +
  the domain / research types (no semantic_v2 harness module, no
  execution / runs / web / providers); collection non-decreasing
  (7576 → 7576 + C1 nodes); 0 / 0 / 0 skips; `manage.py check` +
  `makemigrations --check --dry-run` clean. **Required tests:** the C1
  suite (strict decode refusals: missing / extra keys, unknown enums,
  incoherent labels, wrong seal, tampered per-case / corpus digests,
  cross-version / cross-binding refusal, the constructor-as-validator
  rows, the regeneration property). **Stop conditions:** the frozen
  constructors / codec refuse a case shape the design requires (a
  contract gap — report, do not work around by bypassing the
  constructors); the import boundary cannot be met without touching a
  pinned file (report — the design's §4.1 assumption is false).
  **Authority boundaries:** schema + validator only — NO cases, NO
  labels, NO evaluator, NO model call.

## 9.4 Q3-C-C2 — independently labeled bundle cases (the v1.0.0 seal)

* **Scope (exact files).** `fixtures.py` populated with the §5 matrix
  (≥90 Track A / ≥21 Track B minimums, the §5.6 diversity floors); the
  sealed `corpus_v1.json` + `manifest_v1.json`; the `sources/` archives
  for the RECORDED_FIXTURE citations (the in-repo fixtures cited by
  path + digest — no new archive files beyond the cited ones); the
  challenge log; `policy/qualification_policy_draft_1.json` (DRAFT,
  §7.2 proposals); the family README; NEW test file
  `tests/evaluation/bundle_authority/test_q3c_c2_label_governance.py`.
  **Inputs:** the C1 validator; the §5 matrix (this design); the
  two-identity review workflow (§8.2); the C0 pins. **Deliverables:**
  the sealed v1.0.0 corpus + manifest + DRAFT policy + challenge log +
  README. **Acceptance:** (1) every §5.1–§5.5 row is instantiated ≥ its
  **corrected (Q3-C-D1-FU1) minimum over the seal population**, and
  **EVERY §5.6 composition floor (evidence-kind composition, category
  diversity, bounded-vocabulary projection — the W2 / W6 adjudications)
  is enforced on the ACTUAL seal population by the qualification-ready
  gate** (the loader-enforced projection; the draft-population check
  alone is not seal evidence); (2) the §4.6 independence
  contract holds mechanically (the import scan over fixtures.py + the
  authoring tooling; the author ≠ reviewer per case; the provenance
  fields + independence attestation per case; the seal precedes the
  evaluator — E1 does not exist yet); (3) the tester's sample
  re-derivation (≥20%, all D rows) agrees with the sealed labels
  (disagreements are findings — the labels or the design citation move
  under §4.6 item 5 governance, never silently); (4) regeneration
  reproduces the committed artifacts byte-for-byte; (5) all C0 / C1
  pins + the full pre-existing suite pass (collection 7576 → 7576 + C2
  nodes; 0 / 0 / 0 skips); (6) **the gate reasons are pinned (the W1 /
  W4 adjudications of Q3-C-D1-FU1): the qualification-ready gate's
  refusal reasons are a bounded deterministic vocabulary, and the C2
  governance suite asserts the exact reason over the adversarial gate
  demonstrations (the forged-review, the missing-review, the missing-
  matrix-row shapes).** **Required tests:** the C2 suite (matrix
  coverage projection, label governance, the coherence pre-checks, the
  seal integrity, the regeneration). **Stop conditions:** any row of §5
  cannot be labeled independently (the citation fails — the row is
  reported as a design defect, the matrix is corrected under a NEW
  design revision, not the labels bent); the two-identity review cannot
  be staffed (the phase holds — a self-reviewed corpus is not a
  qualification corpus). **Authority boundaries:** labels + seal only —
  NO evaluator, NO execution against the implementation for label
  purposes, NO capture, NO policy approval.

## 9.5 Q3-C-C3 — real-market bundle evidence acquisition (the tier gate)

* **Scope.** A BOUNDED, operator-approved live sub-step (the Q3-B
  controlled-capture discipline, adapted): retrieval of real bundle
  listings (the §7.6 minimums), archiving under `sources/<case_id>/`
  (raw content + retrieval attestation), authoring the REAL_MARKET case
  documents + labels through the §8.2 workflow (the reviewer's
  INDEPENDENT source verification per §3.2-L3 / §7.6), and a family
  corpus minor re-seal (1.1.0 — additive cases, no per-case document
  moves, `label_revisions` empty) OR a new-version seal if 1.0.0 cases
  require correction (under the A–D rule). NEW / amended files: the
  family `sources/` tree, `fixtures.py` (the REAL_MARKET cases), the
  re-sealed corpus + manifest, the family README (the population
  statement). **Inputs:** the sealed v1.0.0 (C2); the operator's
  explicit retrieval authorization (the network access is the live
  surface — bounded, logged, operator-gated; the C1–C2 phases remain
  zero-live). **Deliverables:** the REAL_MARKET population (≥15 cases
  per §7.6) + the re-seal + the verification record. **Acceptance:**
  the §7.6 minimums met with the distinctness requirements (reviewer ≠
  attestor; independent verification recorded); the re-seal verifies
  (field-by-field, the 1.0.0 per-case documents byte-identical where
  additive); the full suite passes (collection non-decreasing).
  **Required tests:** the C2 governance suite extended over the
  REAL_MARKET rows (the archive digest re-verification, the attestation
  shape, the independence record). **Stop conditions:** the retrieval
  environment is unavailable (the phase holds — the tier ceiling stays
  RESEARCH_ONLY, recorded); a REAL_MARKET case cannot be independently
  verified (the case is dropped to the SYNTHETIC/RECORDED population
  or the phase holds — never labeled from a single archive).
  **Authority boundaries:** evidence acquisition + label addition only
  — NO evaluator change, NO policy approval, NO capture of models.

## 9.6 Q3-C-E1 — deterministic evaluator and adversarial tests (Track A)

* **Scope (exact files).** The family `evaluator.py` (the §6.1
  execution + metrics M1–M15, the perturbation sweep, the zero-live
  discipline), `gates.py` (G1–G8 + the zero-silent gate: every labeled
  case has exactly one outcome), `report.py` (the §7.5 ladder + the
  report contract — the family `contract` section records the C0-pinned
  implementation identity: the FU4 module + R1 adapter + codec + replay
  digests, the corpus identity, the starting SHA; the `authority`
  section's standing note; the rule-of-three disclosure §7.6),
  `policy.py` (the family policy loader — the §7.2 vocabulary), the
  family `cli.py` (evaluate-a + verify-report); the committed baseline
  `reports/q3c_e1_baseline/` (the FULL Track A evaluation over the
  sealed corpus — per §6.1 there is no NOT_CAPTURED stub); NEW test file
  `tests/evaluation/bundle_authority/test_q3c_e1_track_a.py`.
  **Inputs:** the sealed corpus (C2 / C3); the C0 pins; the frozen
  research public surface (read-only); the family-owned
  observation interface + the `observation_stages` mapping (the
  C1-FU4 artifact, §9.12 (1b) — the SOLE source of Contract B
  records). **Deliverables:** the evaluator + gates + report + the
  committed baseline + the E1 suite.
  **Acceptance:** (1) the baseline reproduces byte-for-byte from the
  sealed corpus + the pinned implementation (the regeneration
  property); (2) the E1 suite passes — including the ADVERSARIAL
  re-execution: every D row's sealed invalid document is re-fed
  through the REAL entry points and the labeled refusal class / stage /
  **exact bounded reason (the named observation over the loader-
  observation stages — the W1 adjudication of Q3-C-D1-FU1, the
  execution order of the Q3-C-D1-FU3 / F-R6 adjudication, the
  two-contract correction of the Q3-C-D1-FU3-FU1 note)** is what
  occurs (the gate arithmetic over the actual system, not over the
  evaluator's model of it). For the D rows labeled at the loader-
  observation stage (CORPUS_INTEGRITY — incl. the D6-i shape /
  FA4-ADV-012, whose exact named observation is
  `SOURCE_EXTRACTION_INPUT_DIGEST` at the `CASE_DOCUMENT` layer),
  the REAL entry point is the two-contract order of §6.1: the
  case LOADS through the strict path (Contract A — the label-
  coherence verification; a correctly labeled case is accepted
  into the corpus, not refused by it), and its REAL observation
  is the family-owned observation interface's record over the
  sealed document (Contract B — the exact named observation at
  the exact layer, the labeled stage within `observation_stages`;
  a record with no corpus-surface observation is scored NOT
  refused — the explicit bypass-to-G4 rule: G4 fails,
  `BYPASSED_INTEGRITY`, regardless of the strict load's
  acceptance), and the frozen derivation COMPLETING over the
  reconstructed self-consistent typed inputs is the documented
  non-observation recorded in the baseline — NEVER counted as
  satisfying the refusal, never scored `BYPASSED_INTEGRITY`,
  never suppressing a G4 failure (the defect is never presented
  to the implementation — stage semantics (iv)); **PLUS the
  MANDATORY D16-iii execution-
  level assertion (the Q3-C-D1-FU1 / C2-F2b phase-boundary
  correction): the composition / attestation inputs are fed to the
  frozen FU3 token's derivation entry point and the frozen contract-
  misuse refusal is what occurs — the P3 §5.4 / D9 delegation boundary
  verified at execution, recorded in the E1 baseline report under the
  M13 / G6 coverage note; an E1 pass here without the recorded
  assertion is an E1 acceptance failure**; (3) the pre-existing full suite passes
  unchanged (the collection pin against the phase's starting SHA; 0 /
  0 / 0 skips; the firewall re-run — the tester record); (4) the report
  verifies (`verify_report` re-binds corpus + implementation identity
  + per-case outcomes); (5) the decision is computed and recorded
  (at the E1 endpoint the family policy is DRAFT — P1 has not run — so
  the ladder state over a passing-gate baseline is POLICY_PENDING,
  never higher; the report states the rule-of-three
  bounds). **Required tests:** the E1 suite (the metric definitions
  pinned over constructed outcome tables; the gate ladder over
  constructed metric states — a constructed false-PROVEN outcome must
  flip G1 and land NOT_QUALIFIED; the constructed full-pass + DRAFT
  policy must land POLICY_PENDING, never QUALIFIED — the semantic
  family's hypothetical-full-pass pin, adopted; the perturbation sweep
  over the sealed population; the zero-live sentinel). **Mandatory
  adversarial tests (the Q3-C-D1-FU3-FU1 two-contract E1 boundary —
  each proves a real system behavior; none compares a label to
  itself):** (1) the valid FA4-ADV-012 negative case (CORPUS_
  INTEGRITY / error_type null — the corrected label) LOADS into
  the corpus through the strict path (Contract A — the existing
  label-governance contract preserved: the loader accepts the
  correctly labeled sealed-raw case after verifying the stage
  against its internally collected observations); (2) the family-
  owned observation interface over FA4-ADV-012's sealed document
  INDEPENDENTLY detects `SOURCE_EXTRACTION_INPUT_DIGEST` (the
  actual check fired — not the label); (3) the observation's
  exact layer (`CASE_DOCUMENT` — the C1-FU4 reclassification) +
  the `observation_stages` mapping (`CORPUS_INTEGRITY`) match the
  authoritative design; (4) disabling or bypassing the integrity
  check (the record carrying no corpus-surface observation) flips
  G4 to FAIL over the same case (the explicit bypass-to-G4
  rule); (5) a successful `UNPROVEN` derivation over the
  reconstructed self-consistent typed inputs does NOT suppress
  the G4 failure of (4) (the documented non-observation never
  fills an empty record); (6) a record whose fired check is NOT
  the row's required named observation (the wrong reason, the
  labeled stage still coherent with the record) fails W1
  (recorded with the bounded expected / observed reason; G4
  standing on the record's non-emptiness); (7) the required named
  observation present at the WRONG stage (the `observation_stages`
  set excluding the labeled stage) is recorded as an M6
  defect with G4 standing (a refusal at ANY stage satisfies the
  hard gate); (8) the expected label alone cannot create an
  actual observation — the interface over a SOUND document
  returns the EMPTY record (the labeled named observation is
  absent; the row scores NOT refused — G4), and the evaluator's
  import scan + sentinel prove the record is computed from the
  sealed evidence documents only, never from `expected`; (9)
  every pre-existing constructor / codec / presentation-gate /
  replay refusal test retains its contract unchanged (the
  collection pin over the phase's starting SHA; the D4 / D8 / D14
  / D15 / D17-i shapes + the record-surface twins + the full
  sealed-raw scoping family byte-verified — no test deleted,
  renamed, skipped, xfailed, deselected, or weakened). **Stop
  conditions:** the evaluator cannot be written without importing a
  forbidden surface (the §3.3 boundary is false — report); the sealed
  corpus fails its own load (C2 defect — C2 correction under the
  governance rule, then re-run — the E1 acceptance is never relaxed);
  the Contract B record cannot be obtained without a duplicated mock
  of the family's security rules or a label-derived record (the
  §9.12 (1b) interface boundary is false — report; the E1
  acceptance is never relaxed by manufacturing observations).
  **Authority boundaries:** evaluation + report only — NO production
  wiring, NO marker flip, NO policy approval, NO capture, NO label
  change.

## 9.7 Q3-C-E2 — model evidence acquisition evaluation (Track B)

* **Scope (exact files).** The family `capture.py` (the Track B capture
  document schema 1 — the direct-capture pattern: the family corpus
  binding, the prompt axis 2.1, the pinned route, the per-record
  `case_id / execution_status / raw_output`), the family runner
  (the Q3-B / Q3-B-FU1 discipline: bounded errors — no raw exception
  disclosure; the strict dispatch-stop; the fixed retry policy; the
  lazy approved transport import; the credential / secret sentinel
  tests; the runner-managed gitignore-protected artifact directory —
  captures are NEVER committed alongside the labels), `evaluator.py`
  extended (the §6.2 N-metrics + the annotation grammar §6.4 + the
  MB gates), the committed no-capture baseline `reports/
  q3c_e2_baseline/` (per model: coverage 0 — the explicit no-capture
  state, the semantic family's baseline convention), NEW test file
  `tests/evaluation/bundle_authority/test_q3c_e2_track_b.py` (every
  model call a scripted recording double; the full pipeline under a
  blocked socket). **Inputs:** the E1 endpoint; the frozen Prompt 2.1
  (read-only — the system-text digest `e2949e75…18fc` is the contract
  identity in the report); the operator's explicit authorization for
  the LIVE capture sub-step (separately approved within E2 — the
  offline implementation + the double-based tests are the phase
  deliverable; the live execution is its gated sub-step, per model,
  per the Q3-B precedent). **Deliverables:** the capture + runner +
  Track B evaluation + the no-capture baselines + the E2 suite (+ the
  live capture documents, when the sub-step is approved and executed).
  **Acceptance:** (1) the double-based pipeline passes (the constructed
  capture over the sealed corpus evaluates; the MB gates flip correctly
  over constructed hallucination / mis-grounding outcomes; the
  primary / fallback separation is structural); (2) the capture
  binding refuses every cross-version / cross-corpus / wrong-route /
  contract-negative combination (the semantic family's adversarial
  capture matrix, family version); (3) the G8 structural proof passes
  (no capture artifact is importable by the Track A evaluator — the
  import scan); (4) the full pre-existing suite passes unchanged
  (collection pin; 0 / 0 / 0 skips; the firewall re-run); (5) if the
  live sub-step is executed: the capture documents verify against the
  sealed corpus; the per-model Track B block lands in the report; the
  decision recomputes under the ladder (the model tier cannot exceed
  POLICY_PENDING without the approved policy — §7.7). **Required
  tests:** the E2 suite (≥ the Q3-B 80-node runner discipline adapted:
  model pinning, prompt fidelity over the REAL frozen builder, the
  transport boundary, no credential leakage, the bounded retry, the
  abort, the no-label-read-on-retry proof, the offline replay fidelity,
  no authority promotion, no pricing contamination, no network in the
  unit tests). **Stop conditions:** the live endpoint is unavailable
  (the sub-step defers — the phase endpoint is the offline
  implementation + the no-capture baselines, recorded as such); the
  frozen parser / prompt cannot serve the Track B input shape
  (report — no prompt change is authorized by this design).
  **Authority boundaries:** model evidence only — NO Track A input from
  Track B, NO attestation construction, NO policy approval, NO live
  production path.

## 9.8 Q3-C-P1 — independent policy review

* **Scope.** The DRAFT family policy (C2) + the E1 / E2 reports + the
  tester records → the APPROVED policy (or the recorded rejection with
  the corrections). Reviewer: the independent tester + ChatGPT (the
  final gate). **Inputs:** the E1 / E2 endpoints. **Deliverables:**
  `policy/qualification_policy_<version>.json` (APPROVED — named
  `approved_by`, `approved_utc`, the §7.2 values as approved) + the
  review record (every threshold: the rationale, the population it
  binds, the denominator check). **Acceptance:** the policy loads
  under the family contract; `policy_applies_to` the sealed corpus
  identity; the hypothetical-full-pass recomputation lands per the
  ladder (the approved policy + passing gates + unmet coverage ⇒
  RESEARCH_ONLY; met coverage ⇒ the next rung); the full suite passes
  (collection pin). **Required tests:** the policy-contract nodes
  (APPROVED shape validation, the applicability, the DRAFT-artifact
  byte-preservation — the C2 DRAFT stays committed and unchanged
  alongside the APPROVED version). **Stop conditions:** the review
  finds a threshold whose denominator is unsatisfiable over the sealed
  population (the threshold is corrected in the policy review — the
  corpus / implementation are NOT corrected to fit the threshold); the
  tester record is incomplete (the review holds). **Authority
  boundaries:** policy governance only — NO code, NO corpus, NO capture.

## 9.9 Q3-C-Q1 — qualification execution

* **Scope.** The full program run over the sealed corpus (the C3
  population if landed): the Track A evaluation + the Track B
  evaluation (per model, over the committed captures) + the policy
  decision → the qualification report of record (the family's
  `reports/q3c_q1/`), the tester record, and the STATUS / PLAN update
  recording the computed state. **Inputs:** the P1 endpoint.
  **Deliverables:** the report of record + the state recording.
  **Acceptance:** the report verifies; the state is exactly the ladder
  outcome (at most QUALIFIED_FOR_REVIEW_ASSISTANCE — the report can
  compute no higher, §7.5); the full suite passes (collection pin; the
  firewall re-run — the qualification does NOT flip
  `V2_AUTHORITY_QUALIFIED` / `V2_FU4_AUTHORITY_QUALIFIED`, does NOT
  wire a consumer, does NOT move the live runtime). **Required tests:**
  the verify-report nodes + the state-recording pin (the committed
  report's decision string is what the ladder computes — a
  re-execution over the sealed inputs must reproduce it). **Stop
  conditions:** any gate failure (the state is NOT_QUALIFIED —
  recorded; the corrections are NEW phases under NEW governance, never
  acceptance redefinition); the corpus has moved (a post-seal label
  event — the qualification is over the NEW version, re-run).
  **Authority boundaries:** execution + recording only.

## 9.10 Q3-C-W1 — separate production wiring approval (only if qualified)

* **Scope.** OUT OF THIS DESIGN'S AUTHORIZATION. Recorded for
  completeness: the live 2.1 / FU4 execution decision (the P5 O-3
  lineage), the W1 atomic consumer guard (PROVEN_EQUIVALENT or a
  recorded human CONFIRMED or excluded with a recorded reason — the
  predicate unchanged, it reads `SalesUnitAuthorityV2`), the
  qualification-marker flip under the AD-Q3B4-6 discipline, and the
  PRODUCTION_AUTHORITY_QUALIFIED governance state. Each requires its
  own architecture review + explicit approval, on a QUALIFIED_FOR_
  REVIEW_ASSISTANCE (or higher, as governed) state of record. **This
  design neither schedules nor pre-approves W1.**

## 9.11 Q3-C-C1-FU3 + the C2 corrective implementation — the proposed
bounded scope (Q3-C-D1-FU1; PROPOSED, NOT authorized)

The revision record names the corrections the HELD-case adjudications
require. Their implementation is a bounded corrective phase (the C1-
FU2 precedent: a validator / test / pre-seal-case correction is its own
recorded step) proposed here for ChatGPT's separate approval — this
design neither schedules nor pre-approves it.

* **Scope (exact files).** (1) `product_intelligence/evaluation/
  bundle_authority/corpus.py` — the C1-FU3 validator corrections:
  (a) the §4.4 PROVEN coherence scoping (the Bundle-specific quantity
  / composition checks apply only to Bundle-channel cases; the non-
  Bundle PROVEN expectation requires the exactly-null Bundle-axis
  fields — P3 D11; C2-F1); (b) the identity-assessment decode over the
  empty normalized part numbers where the frozen constructor permits
  (U4_NO_MPN / E1_NO_TARGET_MPN; the frozen constructor + the round-
  trip projection remain the arbiter; the C1 identity-context defect);
  (c) the allowed NONE-basis recorded-extraction-result state + the
  new case-document-integrity refusal over the recorded-result /
  presented-channel mismatch (the frozen P2 mapping; C2-F6; the
  existing EXTRACTION_RESULT_V1 / RECORDED_CHANNEL / NONE negative
  contracts preserved); (d) the W9 coherence-separation statement in
  the module contract (the checks use frozen contract data only —
  already structural, now named). (2) `tests/evaluation/
  bundle_authority/test_q3c_c1_corpus_integrity.py` — the recorded in-
  place corrections (the precedent: the C2 endpoint's five-node
  correction; intent preserved or strengthened; no rename / skip /
  xfail / deselect) + the NEW correction nodes: the non-Bundle PROVEN
  over the exactly-null Bundle-axis fields loads (every non-Bundle
  form); the non-Bundle PROVEN over a non-null Bundle axis is refused
  (the misstated delegation); the U4_NO_MPN / E1_NO_TARGET_MPN
  identity contexts decode (the empty part number the frozen
  constructor accepts); the allowed recorded-result state loads over
  the matching frozen P2 mapping and is refused (CORPUS_INTEGRITY, the
  exact named observation) over the mismatching one; the W1 exact-
  reason assertions over the stage-coherence rejections. (3)
  `product_intelligence/evaluation/bundle_authority/fixtures.py` — the
  pre-seal case corrections under the §4.6 item 5 governance (recorded
  in the challenge log §6, the case IDs stable): the D3-ii re-label
  (PRESENTATION_GATE → CORPUS_INTEGRITY; surface BOTH → DERIVATION; the
  payload twin removed — the self-consistent record decodes and replays
  cleanly, the observation is the loader's); the D11-ii re-authoring
  (RECORDED_FIXTURE → SYNTHETIC; the exact U1 EXACT identity context —
  U1_TITLE_MPN, equal non-empty normalized part numbers, TITLE_MPN_
  TOKEN, NOT_REQUIRED; the by-construction attested compositions; the
  recorded Micron identifier family documented as the row's context,
  NOT claimed to publish bundle contents); the B6-ii / B6-iii / C6
  re-authoring over the allowed recorded-extraction-result state (the
  recorded results are the genuine frozen P2 instantiations over the
  sealed texts — C6's verified CONTRADICTED_CUES shape: the title's
  established bundle-with-contents clause vs the structured pack-of-N
  field; B6-ii / B6-iii's verified AMBIGUOUS_CUE count-only / bare-
  bundle shapes; the W7 cue-state accuracy); the D16-iii case removed
  from the declared population (the E1-only obligation — §9.6); the A1
  recorded-variant case removed from the v1.0.0 declared population
  (the C3 / 1.1.0 additive obligation — §5.6). The re-recorded
  fixtures source-digest pin (the pin's own stated contract). (4)
  `tests/evaluation/bundle_authority/test_q3c_c2_label_governance.py`
  — the recorded in-place corrections (the precedent: the C2 endpoint's
  five-node correction) + the NEW nodes: the revised ROW_MINIMUMS (A1
  1; D16 2; the 90 sum) and the revised held set (the W3 monotonic
  adjudication — the release of the seven loader-held cases under the
  named corrections, recorded); the §5.6 floors enforced over the seal
  population in the qualification-ready gate (W2 / W6); the pinned
  gate refusal reasons (W1 / W4); the vocabulary projection over the
  94-case population; the revised review-readiness dry-run (the 94-
  case loader-pass expectation under the corrected loader). (5)
  `evaluation/fu4_bundle_authority_qualification/challenge_log.md` +
  `reviewer_handoff.md` — the adjudication record under the reviewer /
  adjudicator identity + instant (the challenge log §6 entries; the
  handoff's held-case worklist updated to the corrected rows; the re-
  recorded artifact pins under the governance rule). (6) The STATUS /
  PLAN records. **No other file.** The frozen research surface (the
  C0-pinned modules), the semantic family artifacts, and the DRAFT
  policy are byte-pinned inputs.
* **Deliverables.** The corrected validator + tests; the corrected 94-
  case DRAFT population (still DRAFT — the seal completes only under
  the genuine two-identity review per the handoff, now over the
  corrected rows); the recorded adjudication + held-set release (W3);
  the re-pinned governance artifacts.
* **Acceptance.** (1) the 94-case corrected population loads under the
  corrected family loader with the test-local reviewer fill (the dry-
  run, case-by-case); (2) the seven loader-held releases are verified
  case-by-case (the exact corrected behavior over each); (3) the §5.6
  floors hold over the seal population (90 Track A / 21 Track B / 18
  shared / 3 B-only; 88 SYNTHETIC ≥ 80% / 6 RECORDED_FIXTURE ≥ 5 / 0
  REAL_MARKET; 5 categories ≥ 4; every bounded member projected);
  (4) the C1-FU2 provenance binding + every C1 correction node stands
  (0 removed / 0 renamed outside the recorded in-place corrections; 0
  / 0 / 0 skips); (5) the qualification-ready gate enforces the floors
  + the pinned reasons over the forged / missing / dropped adversarial
  demonstrations (W1 / W2 / W4 / W6); (6) the D16-iii + the A1-
  recorded obligations are recorded in the E1 scope (§9.6) + the C3 /
  1.1.0 scope (§5.6) — the destinations are named, the obligations are
  preserved; (7) `manage.py check` + `makemigrations --check --dry-
  run` clean; the collection pin against the phase's starting SHA (the
  8043 baseline + the new nodes; 0 removed / 0 renamed outside the
  recorded corrections).
* **Stop conditions.** Any correction that would weaken a frozen
  contract (the P3 D9 / D11 delegation; the P5 R-5 bound; the P2
  mapping; the FU3 / FU4 token boundary) is a conflict — report, do
  not resolve; a truthful evidence classification that the schema
  cannot express (the C2-F5 class) — the case stays SYNTHETIC or moves
  to C3, never a provenance weakening; any floor the corrected
  population cannot meet — the arithmetic conflict is reported, the
  threshold is never silently moved.
* **Authority boundaries.** Validator + test + pre-seal case
  corrections + the governance records ONLY — NO seal (the two-
  identity review is still outstanding), NO evaluator, NO policy,
  NO capture, NO model call, NO production wiring.

## 9.12 Q3-C-C1-FU4 + the C2-FU2 corrective implementation (F-R6
+ F-R2) — the proposed bounded scope (Q3-C-D1-FU3 + the Q3-C-D1-
FU3-FU1 contract correction; PROPOSED, NOT authorized)

The Q3-C-D1-FU3 revision record re-attributes the D6(i) row to
CORPUS_INTEGRITY (the family-loader cross-document observation
point — the C2-F2a precedent) and verifies the F-R2 documentary
citation gap; the Q3-C-D1-FU3-FU1 contract correction fixes the
E1 two-contract observation boundary over it (§6.1 / §9.6). The
implementation is a bounded corrective phase of the §9.11 class
(a validator / test / pre-seal-case correction is its own
recorded step) proposed here for ChatGPT's separate approval —
this design neither schedules nor pre-approves it.

* **Scope (exact files).** (1) `product_intelligence/evaluation/
  bundle_authority/corpus.py` — the C1-FU4 validator correction:
  the `SOURCE_EXTRACTION_INPUT_DIGEST` observation (the D6-i cross-
  document binding — the case's recorded extraction input document
  vs the embedded result's `input_digest`) is re-classified from
  the CONSTRUCTOR layer to the CASE_DOCUMENT layer (the family-
  loader cross-document integrity validation — stage semantics
  (iv); the five validation surfaces). The check's logic is
  UNCHANGED (the same comparison, the same bounded reason text);
  the reclassification makes the EXISTING stage-coherence rule
  reject the pre-revision CONSTRUCTION label over the D6-i shape
  (a case-document observation fired) and require CORPUS_INTEGRITY
  with the named observation. The reclassification changes ONLY
  which label is coherent over the D6-i shape: the strict load's
  Contract A behavior is otherwise unchanged (a correctly labeled
  sealed-raw case still LOADS — the acceptance after the stage-
  coherence verification — and the incoherent label is still
  refused). The module docstring's sealed-raw defect scope states
  the D6-i binding under CORPUS_INTEGRITY. (1b) the SAME file
  gains the NARROW family-owned observation interface (the
  Q3-C-D1-FU3-FU1 Contract B surface; the §6.1 two-contract
  execution order): the public bounded record type (the fired
  `check / layer / reason` triple — the closed check family, the
  five bounded layers) + `observe_corpus_case_integrity(case_
  document)` — the strict structural decode (a malformed case
  document is a bounded schema error — fail-closed, a structural
  failure is never an observation) + the typed decode over the
  REAL frozen constructors + the family cross-document checks,
  ALL in the loader's own observation-collection mode (the
  ACTUAL `_run_family_checks()` logic reused — NO duplicated mock
  of the security rules), returning every fired observation in
  deterministic firing order (multiple observations: all, never
  truncated / deduplicated / prioritized; an unexpected
  observation changes the record, never hides the required one);
  the `expected` block is schema-validated but NEVER read for
  behavior (the outcome does not select strictness; no label
  field selects, filters, or manufactures an observation — the
  W9 discipline); + the pure `observation_stages(record,
  surface)` mapping — the exact INVERSE of the sealed-raw
  scoping rule's corpus-surface acceptance set, computed from
  the record's layers + the sealed surface, NEVER from the label
  (`CORPUS_INTEGRITY` ∈ the set iff a `CASE_DOCUMENT` or
  `CASE_DOCUMENT_MIRROR` observation fired; `CONSTRUCTION` ∈ the
  set iff a `CONSTRUCTOR` / `CODEC` / `CASE_DOCUMENT_MIRROR`
  observation fired and no `CASE_DOCUMENT` observation fired;
  `CODEC_DECODE` ∈ the set iff a `CODEC` observation fired, no
  `CASE_DOCUMENT` observation fired, and the sealed surface ∈
  {RECORD, BOTH}; the GATE-layer corroborative observations never
  determine a stage; the empty set — no corpus-surface
  observation — is the bypass-to-G4 shape). The interface does
  NOT verify the per-case / corpus digest or the manifest (the
  seal is Contract A's obligation) and NEVER invokes the
  derivation / the replay / any model (zero model calls, zero
  network, zero pricing authority — the W9 import scan + the
  sentinel no-execution probe extended to the new surface). NO
  frozen research module is touched — the frozen layers' silence
  over this shape is the evidence, not the defect. (2)
  `tests/evaluation/bundle_authority/test_q3c_c1_corpus_integrity.
  py` — the recorded in-place correction (the precedent: the C2
  endpoint's five-node correction + the C1-FU3 in-place
  corrections; intent preserved or strengthened; no rename / skip /
  xfail / deselect): `test_extraction_input_digest_mismatch_
  sealed_raw` re-pins the D6-i sealed-raw shape at the ADJUDICATED
  observation point (stage CORPUS_INTEGRITY, error_type null, the
  exact named observation `SOURCE_EXTRACTION_INPUT_DIGEST` at the
  CASE_DOCUMENT layer) — the pre-revision CONSTRUCTION
  expectation is the recorded pre-adjudication reading, replaced in
  place with the correction named; NEW correction nodes: (a) the
  exact loader observation over the D6-i shape (the named check
  fires at the CASE_DOCUMENT layer with the bounded reason; the
  corroborative GATE-layer span-grounding observations are
  recorded, never the reason); (b) the stage + bounded reason
  (CORPUS_INTEGRITY / error_type null — the stage-error
  vocabulary holds); (c) the NEGATIVE node: the CONSTRUCTION label
  over the D6-i shape is REFUSED by the stage-coherence rule when
  ONLY the cross-document mismatch exists (the frozen constructor
  is silent — no constructor / codec observation fires; the case-
  document observation does — the incoherent-label refusal with its
  pinned reason); (d) every frozen-constructor / codec /
  presentation-gate / replay refusal test stands UNCHANGED (the D4
  / D8 / D14 / D15 / D17-i shapes, the record-surface twins, the
  full sealed-raw scoping family — the construction-stage
  requirement is NOT re-interpreted for the unrelated cases);
  (e) the Contract B interface pins (the Q3-C-D1-FU3-FU1
  observation boundary — the E1 suite's mandatory adversarial
  tests (1)–(8) execute over this surface at E1): the interface
  over the corrected D6-i sealed document returns the record
  carrying `SOURCE_EXTRACTION_INPUT_DIGEST` at the `CASE_DOCUMENT`
  layer with the pinned bounded reason (the GATE-layer
  corroborative observations present, never the reason) +
  `observation_stages` = {CORPUS_INTEGRITY}; the interface over a
  SOUND sealed document returns the EMPTY record (the label
  cannot create an observation); the interface with the
  designated check disabled returns the corroborative-only
  record + the EMPTY stage set (the G4-failure shape); a
  MALFORMED case document raises the bounded schema error (fail-
  closed — not an observation); the same evidence documents under
  a different `expected` label return the IDENTICAL record
  (outcome-independence — the label never selects behavior); the
  interface does not verify the digest (a wrong `case_digest`
  value still yields the record — the seal is Contract A's
  obligation, pinned separately); the W9 import scan + the
  sentinel no-execution probe cover the new surface (the
  interface never invokes the derivation / the replay / any
  model).
  (3) `product_intelligence/evaluation/bundle_authority/fixtures.
  py` — the pre-seal case corrections under the §4.6 item 5
  governance (recorded in the challenge log §6 under the
  adjudicator identity + instant; the case IDs stable; the class-A
  reason of record — the old stage expectation was factually wrong
  over the frozen contract: no frozen constructor / codec bounded
  error exists over the D6-i sealed shape, the observation point is
  the family loader's named cross-document check): FA4-ADV-012 —
  `expected.refusal.stage` CONSTRUCTION → CORPUS_INTEGRITY +
  `expected.refusal.error_type` CONSTRUCTOR → null (PRESERVED,
  byte-unchanged: `expected.outcome` REFUSED, `expected.replay`
  NOT_APPLICABLE, every other expected field, the surface
  DERIVATION, the track A, the matrix row D6, every sealed
  evidence document, the label author / provenance; the grounding
  citation + rationale state the F-R6 adjudication); F-R2 (the
  documentary citation correction — the two D11 grounding
  citations, FA4-ADV-022 / FA4-ADV-023, name the Micron catalog by
  path only while the adjudication record claims "path + digest"):
  the VERIFIED catalog digest `160d4fe97a5df5249e8f6404f6b005c0515-
  fab4def1b4668fdaf87c727600743` (recomputed over the working-tree
  bytes of `tests/fixtures/pages/micron_7500_part_catalog.json` —
  24,060 bytes; the catalog file itself is UNCHANGED; the zero-
  `bundle` statement re-verified; no unverified digest is inserted)
  is added to the two grounding citations (a class-A annotation
  correction — no expected field moves). The re-recorded fixtures
  source-digest pin (the pin's own stated contract). (4)
  `tests/evaluation/bundle_authority/test_q3c_c2_label_governance.
  py` — the recorded in-place corrections (the fixtures / challenge-
  log / handoff digest re-pins under the governance rule; the row-
  projection + held-set expectations stand — the D6 row minimum
  stays 2, the 90 sum stays 90, the 94-case population stands) +
  the NEW nodes: the FA4-ADV-012 corrected-label pin (CORPUS_
  INTEGRITY / null / REFUSED / NOT_APPLICABLE — mutation-verified:
  the pre-correction CONSTRUCTION / CONSTRUCTOR value trips it); the
  F-R2 citation-digest pin (both D11 grounding citations carry the
  verified catalog digest; the pre-correction path-only value trips
  it). (5) `evaluation/fu4_bundle_authority_qualification/
  challenge_log.md` + `reviewer_handoff.md` — the adjudication
  record under the reviewer / adjudicator identity + instant (the
  challenge log §6 entry naming the design correction + the F-R6
  resolution: the D6-i stage re-attribution per the Q3-C-D1-FU3
  revision record; the F-R2 citation correction; the handoff's
  worklist updated — FA4-ADV-012 / FA4-ADV-022 / FA4-ADV-023
  flagged for the independent reviewer's re-verification over the
  corrected rows; the re-recorded artifact pins). (6) The STATUS /
  PLAN records. **No other file.** The frozen research surface (the
  C0-pinned modules), the semantic family artifacts, and the DRAFT
  policy are byte-pinned inputs.
* **Deliverables.** The corrected validator + the family-owned
  observation interface (the Contract B surface, (1b)) + tests;
  the corrected 94-case DRAFT population (FA4-ADV-012 re-labeled;
  the two D11 citations completed; still DRAFT — the seal
  completes only under the genuine two-identity review per the
  handoff, now over the corrected rows); the recorded F-R6 +
  F-R2 resolutions; the re-pinned governance artifacts.
* **Acceptance.** (1) the 94-case corrected population loads under
  the corrected family loader with the test-local reviewer fill (the
  dry run, case-by-case) — FA4-ADV-012 at CORPUS_INTEGRITY with the
  exact named observation; (2) the negative node holds: the
  CONSTRUCTION label over the D6-i shape is refused when ONLY the
  cross-document mismatch exists; (3) the §5.6 floors hold
  UNCHANGED over the seal population (90 Track A / 21 Track B / 18
  shared / 3 B-only; 88 SYNTHETIC ≥ 80% / 6 RECORDED_FIXTURE ≥ 5 /
  0 REAL_MARKET; 5 categories ≥ 4; the refusal-stage vocabulary ×5
  projected — CORPUS_INTEGRITY by the D6-i / D6-ii / D3-ii cases;
  every other member by its surviving row); (4) every frozen-
  constructor / codec / presentation-gate / replay refusal test
  stands (0 removed / 0 renamed outside the recorded in-place
  corrections; 0 / 0 / 0 skips — the 8082-node baseline preserved
  or strengthened); (5) the F-R2 citations carry the verified
  digest (both D11 cases; the catalog file byte-unchanged); (6) the
  E1 contract is ready: the §6.1 two-contract execution order
  makes the future E1 evaluator unable to bypass the family
  integrity observation for the loader-observation rows (Contract
  A: the corpus strict-loads first — a correctly labeled sealed-
  raw case LOADS, the label-coherence verification, not the
  observation; Contract B: the family-owned observation interface
  over the sealed document must return the exact named
  observation at the exact layer with the labeled stage within
  `observation_stages` — a record with no corpus-surface
  observation is the explicit bypass-to-G4 failure; a successful
  FU4 derivation — incl. a completed UNPROVEN — never counts as
  satisfying a refused case; the baseline records the interface
  record + the documented non-observation); (7)
  `manage.py check` + `makemigrations --check --dry-run` clean; the
  collection pin against the phase's starting SHA (the 8082
  baseline + the new nodes; 0 removed / 0 renamed outside the
  recorded corrections).
* **Stop conditions.** Any correction that would touch a frozen
  research byte (the P2 extraction, the P3 / FU4 constructor /
  gate, the R1 codec / replay) is a conflict — report, do not
  resolve (the F-R6 adjudication moves NO frozen contract — the
  frozen layers' silence is the evidence, not the defect); any
  correction that would re-interpret the construction-stage
  requirement for the unrelated rows (D4 / D8 / D14 / D15 / D17-i)
  is a conflict — the W1 frozen-bounded-error clause stands for
  them verbatim; any floor the corrected population cannot meet —
  the arithmetic conflict is reported, the threshold is never
  silently moved.
* **Authority boundaries.** Validator + test + pre-seal case
  corrections + the governance records ONLY — NO seal (the two-
  identity review is still outstanding), NO evaluator, NO policy,
  NO capture, NO model call, NO production wiring, NO frozen-
  contract change.

---

# 10. Risk register

| # | Risk | Likelihood / impact | Mitigation of record |
| --- | --- | --- | --- |
| R-C1-1 | The pin gap (CF-2) is discovered too late — Track A executes over an unpinned implementation identity | medium / high | C0 is a HARD sequencing gate before E1 (a phase stop condition, §9.6); the E1 report's `contract` section records the C0-pinned identity — a report without the pins is a `FAIL_CLOSED` artifact |
| R-C1-2 | The autocrlf checkout-state fragility of content pins (the pin literal is the working-tree byte digest; a different checkout state breaks the pin on another machine) | medium / medium | the house convention is recorded (§2.7) and the C0 pins carry BOTH digests (committed blob LF + working tree) in the pin comment; the pin asserts the working-tree value per the convention; a checkout-state change is a recorded re-pin event (the R1-FU1 / R2-FU1 pattern), never a silent one |
| R-C1-3 | Label independence failure — the authoring tooling silently imports a label-determining module | low / fatal | the §4.6 three-way mechanical enforcement (import scan over fixtures.py + the authoring scripts; the provenance field + the fixed independence attestation; the temporal seal-before-evaluator ordering); the tester's sample re-derivation at C2; a detected violation voids the seal (new version, recorded) |
| R-C1-4 | The matrix expected values encode the design, not the implementation — an implementation defect surfaces as a "label problem" | medium / high | the evaluation-truth rule is adopted verbatim (§4.6 item 5): "the implementation failed this case" is not a label-change reason; the C2 stop condition routes any author-vs-contract disagreement to a FINDING (the §2.7 discipline); the E1 adversarial re-execution (§9.6) proves the gates over the ACTUAL system, so a defect cannot hide behind the evaluator's model |
| R-C1-5 | False statistical confidence — a small synthetic corpus read as real-market performance | medium / high | the tier stratification by evidence kind (§7.5); the mandatory rule-of-three disclosure with the explicit "contract-coverage bound, not a real-market claim" statement (§7.6); C3 as the gate for QUALIFICATION_CANDIDATE and above; the standing note that qualification is over a finite sealed population |
| R-C1-6 | Track B free-form detail scoring brittleness — the model's bounded structured output (dimension + free-form detail) is an imperfect evidence channel; the token comparison under the annotation grammar can mis-score legitimate phrasings | medium / medium | the annotation grammar is versioned + cross-checked against the contract grammar's normalization (§6.4); the TB-5 bounded proxy is labeled PARTIAL with span-level provenance declared FUTURE (N6, O-5); the QUALIFIED_FOR_REVIEW_ASSISTANCE scope is REVIEW ASSISTANCE — the human reviewer sees the model's report AND the published source; a mis-scored metric bounds the tier, it does not create authority |
| R-C1-7 | Harness coupling — a "helpful" extension of the byte-pinned `semantic_v2` modules for the family | medium / high | the R2-endpoint content pins make the coupling a suite failure, not a design choice; the §3.3 boundary (the new package is the only home) is an acceptance item at C1 (the import scan) and at every later phase |
| R-C1-8 | Lineage sequencing — this program builds on PENDING reviews (P4-FU2 / R1 / R1-FU1 / R2 / R2-FU1); a ratification correction moves the freeze point | medium / medium | the C0 gate re-bases on the ratified endpoint (the pin literals move, the scope does not — §9.2); the design is version-tolerant by construction (the family seals bind the C0-pinned identity, not a moving target); no phase starts on an unratified lineage (the §9 sequencing gate) |
| R-C1-9 | The duplicate-constituent semantics (CF-3) — the frozen grammar's non-merging behavior may be commercially surprising (`1x RAM + 1x RAM` vs `2x RAM` ⇒ CONTRADICTED over attested clauses) | low / medium | the row is labeled per the frozen contract (C2b) with the commercial-ambiguity note; O-4 records the future T5 grammar decision (a new version, recorded examples, re-pinned tests — never a silent edit); until then the safe direction holds (CONTRADICTED caps at NEEDS_REVIEW — no false PROVEN, no false price) |
| R-C1-10 | The frozen channel-granularity bound (P5 R-5) — content-identical publications are indistinguishable at the channel level; the v3 embedding closes the dangerous direction but the bound remains | low / low (documented) | D3-ii exercises the bound at the ADJUDICATED observation point (Q3-C-D1-FU1 / C2-F2a): the case is CORPUS_INTEGRITY — the mismatch (the record's embedded original ≠ the case's recorded extraction evidence) is observable only by the family loader, because over content-identical channels the channel-content binding + all four presentation-gate steps pass (verified over the sealed documents at the revision: the self-consistent payload twin decodes and replays cleanly). The D6-i shape (the recorded extraction input ≠ the embedded result's `input_digest` binding — the Q3-C-D1-FU3 / F-R6 adjudication) is the same observation-point family: every frozen layer is silent over the sealed documents (the record + result are self-consistent over the altered input; the derivation completes), and the family loader's named observation `SOURCE_EXTRACTION_INPUT_DIGEST` is the first and only non-corroborative observation point — CORPUS_INTEGRITY); the bound is stated in the report's contract section (it is a property of the frozen S2-C channel, byte-pinned); a channel version move is a new input-schema axis + new binding — separately gated, out of this program |
| R-C1-11 | Real-market retrieval (C3) — network access in a zero-live program lineage; a retrieval that silently substitutes content | medium / high | C3 is the ONLY live surface and is operator-approved per retrieval batch; the archive is committed + digest-sealed BEFORE labeling; the independent verification (a second retrieval or a cited secondary source, §7.6) is the anti-substitution control; the retrieval attestation names the attestor, and the reviewer is distinct |
| R-C1-12 | The Windows subprocess flake class (the fixed eleven-node allowlist) — full-suite runs under handle pressure | known / low | the documented multi-attempt isolated re-pass discipline (the R2-FU1 record); the allowlist is NOT expanded by any phase; the flake class is itemized separately in every acceptance report |

---

# 11. Unresolved decisions requiring approval

Each is a governance decision, NOT a precondition of this design's
internal coherence; each is owned by the named phase / gate.

* **O-1 — Naming.** The family identity (`PI-FU4-BUNDLE-AUTHORITY-
  QUALIFICATION`), the package / directory / file names, the case-ID
  pattern (`FA4-<CAT>-<NNN>`), the report directory names, and the
  policy artifact name are PROPOSALS of record (the P5 O-1 discipline).
  C1 finalizes them; a rename is documentation-level (the contracts are
  the digest-sealed documents + the pinned constants, not the names).
* **O-2 — The C0 micro-phase.** Whether the pin-gap correction (CF-2)
  runs as its own recorded phase (recommended — the R1-FU1 / R2-FU1
  precedent: a test-preservation correction is its own bounded,
  reviewable step) or is folded into C1's preflight. Decision owner:
  the lineage ratification review (ChatGPT), at the C0 gate.
* **O-3 — The CF-1 disposition.** The task matrix's "conflicting
  secondary extraction cues" under CONTRADICTED vs the frozen contract's
  UNPROVEN (D8 / U12). This design keeps the frozen semantics and
  documents the conflict (C6 / B6-i rows labeled UNPROVEN). Approval
  requested: ratify the documentation (no contract change) — or, if the
  review intends a contract change, that is a NEW separately versioned
  amendment (new token or new evidence-schema version, the T5
  discipline), NOT a qualification-label change.
* **O-4 — The CF-3 disposition (duplicate constituent multiplicity).**
  Ratify the frozen grammar's non-merging behavior as the v1.0.0 label
  basis (recommended — the safe direction: CONTRADICTED caps, never a
  false PROVEN), with the commercial-ambiguity note recorded as a
  candidate FUTURE grammar-version decision (new version + recorded
  examples + re-pinned tests, the T5 / T9 discipline).
* **O-5 — The Track B structured-output question.** Whether
  QUALIFIED_FOR_REVIEW_ASSISTANCE (and any future tier) requires a
  versioned structured bundle-evidence output schema (an output-schema
  axis move + a prompt decision — a phantom 2.2 is refused by the 2.1
  module's own import check; a real 2.2 is its own separately gated
  design) or whether the frozen 7-key output + the bounded annotation-
  grammar scoring (this design's v1) suffices for the review-assistance
  scope (recommended for v1 — the reviewer sees the source; the metric
  bounds the tier, it does not create authority; span-level provenance
  stays FUTURE / NOT IMPLEMENTED either way until O-5 decides).
* **O-6 — The C3 retrieval authorization.** The operator approval of
  the bounded live retrieval sub-step (the sources, the batch size, the
  environment) — the Q3-B precedent (a controlled capture is
  operator-briefed, not self-authorized). Until C3 is approved and
  executed, the tier ceiling is RESEARCH_ONLY (recorded, not blocked).
* **O-7 — The DRAFT threshold values.** The §7.2 proposals are DRAFT
  governance content; P1 approves / moves them with recorded rationale.
  The design deliberately neither proposes final values as binding nor
  copies the semantic family's DRAFT (the F-4 lineage: this family
  owes its own policy).
* **O-8 — The committed baseline convention.** This design commits the
  FULL Track A evaluation as the family baseline (there is no model
  dependency — the semantic family's NOT_CAPTURED stub convention is
  inapplicable and would misstate the track). Approval requested: the
  convention as stated in §6.1 / §9.6.
* **O-9 — The Q3-C lineage identity.** Whether this program is the
  "Q3-C" lineage of the Q3-B4 roadmap (the AD-Q3B4-6 conditioning —
  "the qualification decision is conditioned on the firewall
  disposition") or a separately named successor. This design treats it
  as the FU4-successor branch of the Q3-C qualification lineage (the
  semantic-model Q3-C over corpus 1.1.0 / 1.2.0 is a SEPARATE open
  question in that lineage — the two share no labels, no policy, no
  report, and no gate; the firewall conditioning binds both). Naming /
  scope confirmation requested at the lineage ratification.
* **O-10 — The Q3-C-D1-FU1 phase-boundary corrections (adjudicated,
  NOT open).** The revision record of Q3-C-D1-FU1 resolves the ten
  HELD C2 cases (C2-F1 / C2-F2a / C2-F2b / C2-F3 / C2-F5 / C2-F6 + the
  C1 identity-context defect + W1–W9). The two v1.0.0 row-minimum
  movements (A1 2→1; D16 3→2) are the explicit phase-boundary
  corrections of record — each with its destination (the C3 / additive
  1.1.0 obligation; the E1 mandatory adversarial-execution assertion),
  its rationale, its governing frozen contract (P3 D19; P3 §5.4 / D9),
  and its later acceptance gate. They are NOT unresolved decisions:
  ChatGPT's review of the Q3-C-D1-FU1 revision ratifies or corrects
  them at the design gate (the normal revision review), after which
  the bounded C1-FU3 + C2 corrective implementation (§9.11) executes
  the named corrections under its own separate approval.

---

# 12. Exact implementation authorization boundaries

**This design (Q3-C-D1) authorizes, at its completion:**

1. The existence of the qualification program as specified — the corpus
   family, the two tracks, the metrics, the gates, the ladder, the
   phases — as a REVIEWABLE DESIGN OF RECORD.
2. Nothing else. No implementation phase starts on this document alone:
   each requires (a) the ratification of the pending lineage reviews
   (P4-FU2 / R1 / R1-FU1 / R2 / R2-FU1), (b) ChatGPT's explicit approval
   of that phase's bounded scope against this design, and (c) the
   phase's own frozen acceptance (which this design fixes NOW — §9 —
   and which NO later phase may redefine because the implementation
   failed).

**The hard boundaries (every phase, restated):**

* **No production authority wiring.** No live 2.1 / FU4 execution path,
  no pricing consumer, no W1 guard, no `V2_AUTHORITY_QUALIFIED` /
  `V2_FU4_AUTHORITY_QUALIFIED` flip, no runtime reference to any FU4
  state. The existing reachability / firewall guards are re-run, never
  relaxed.
* **No modification of the qualified surface or the pinned harness.**
  The C0 pins, the A1 / R1 / R2 pin tables, the semantic family
  modules (byte-pinned), the DRAFT policies (both families), the corpus
  1.0.0 / 1.1.0 / 1.2.0 seals, the live runtime, and the prompt texts
  are frozen inputs of every phase. The ONLY new code homes are the
  family package, the family test directory, and the family artifact
  directory.
* **No prompt change.** Track B runs the frozen Prompt 2.1 (digest
  `e2949e75…18fc`). A structured-output capability is O-5's decision,
  not this design's.
* **No labels from the implementation or the model.** §4.6 is binding
  from C2 onward; the seal-before-evaluator ordering is a stop
  condition, not a convention.
* **No capture outside the gated sub-steps.** C1 / C2 / E1 / P1 / Q1
  are zero-live. C3's retrieval and E2's model capture are the ONLY
  live surfaces, each separately operator-approved, each bounded and
  archived, each with its stop conditions.
* **No database change.** The family is file-artifact + pure
  evaluation; `makemigrations --check --dry-run` must report "No
  changes detected" at every phase's acceptance (no model is touched —
  the R1 / R2 discipline).
* **No test deletion / weakening.** The collection accounting (node-
  level diff, 0 removed / 0 renamed except recorded re-pins under the
  house precedent), the 0 / 0 / 0 skipped / xfailed / deselected
  invariant, and the flake-allowlist non-expansion are acceptance items
  of every phase.
* **No qualification claim below the ladder.** No phase report, STATUS
  entry, or plan row may state that FU4 bundle authority is qualified,
  production-approved, or pricing-eligible; the maximum computable
  report state is QUALIFIED_FOR_REVIEW_ASSISTANCE (§7.5), and
  PRODUCTION_AUTHORITY_QUALIFIED is W1's separately gated governance
  state.

**What this phase (D1) does not do (invariance list).**

* No code, no tests, no corpus artifacts, no labels, no captures, no
  model calls, no deployment, no migration, no policy change, no
  authority promotion, no pricing wiring.
* No modification of corpus 1.2.0 (or any semantic-family artifact); no
  extension of the `semantic_v2` harness (byte-pinned); no change to the
  FU4 module, the R1 adapter, the codec, the replay, the prompts, the
  live runtime, or the DRAFT policies.
* No Qwen self-audit (the independent review of this document and the
  underlying source is ChatGPT's, per the task).
* The unrelated worktree artifacts (the pre-existing `tmp_collection.txt`
  modification; the untracked session / benchmark files) are preserved;
  the commit stages only this document + the authorized STATUS / PLAN
  additions.

**Successful D1 means the qualification design is ready for review. It
does not mean FU4 authority is qualified or production-approved.**

---

# 13. Source-to-design traceability

| Design section | Grounded in (source of record) |
| --- | --- |
| §1 (mission / invariants / CF findings) | P3 design D6 / D8 / D17 / D19 / D20 / §2 safety-direction audit / §5 U-table; Q3-B4 §4.1 / AD-Q3B4-6; P5 DEC-5 / §5.4.2; STATUS R2 "Unresolved qualification gaps"; this session's source inspection (§2) |
| §2 (inventory) | the files + digests + node counts as verified at the starting SHA (this session); STATUS / PLAN R1 / R1-FU1 / R2 / R2-FU1 records; the P5 design §1 (the pre-registration inventory, re-verified where it overlaps) |
| §3 (authority / trust boundaries) | P3 §3.6 (the three epistemic tiers) / §3.3 (provenance semantics) / T3 / T3' / T10; P5 R-5 (the channel-granularity bound) / §7 (the firewall obligations); the frozen `PRICING_ELIGIBLE_TIERS` + import self-checks (`semantic_authority_v2.py`); the W1 guard (Q3-B4 §6.2); the L3 recording convention (the 3A / P2 recorded-page precedent, `tests/fixtures/pages/`) |
| §4 (corpus schema) | the semantic family's corpus contract (`corpus.py` / `fixtures.py` / the README ground-truth governance — the exact-key strict decode, the per-case / corpus digest discipline, the label A–D rule, the evidence-kind vocabulary, the manifest statement / lineage keys from the R2 1.2.0 seal); the FU4 evidence schema v3 (`semantic_authority_fu4.py` §3.2–§3.8 of P3); the R1 payload contract (P5 §4.2a) |
| §5 (matrix) | P3 §5 (U0–U21) / §5.1 (the ten mandated cases) / §3.7 (worked examples) / §9 (the B / C / D adversarial rows); P5 §9.1–§9.2 (the R1 / R2 adversarial matrices — the refusal stages); the Revision records 2 / 3 (the D3 / D4 / D5 defect shapes); the frozen FU3 rows (U0–U9 delegation — `semantic_authority_fu3.py`); the corpus-0034 shape (the committed 1.2.0 case document) |
| §6 (methodology) | P5 DEC-5 (the separate metric surfaces) / §5.4.2 (the deterministic correctness surface); the semantic family's evaluator / gates / policy / report / capture contracts (the denominator discipline, the `met: null` rule, the eight-gate pattern, the decision ladder, the direct-capture schema, the Q3-B / Q3-B-FU1 runner discipline); the 2.1 COMMERCIAL SALES-UNIT RULES (`contract_v2_1.py` — the Track B model duties); the 7-key response (`semantic_v2.py`) |
| §7 (acceptance policy) | the task's §7 gate list (adopted with exact denominators); the rule-of-three (standard zero-event confidence bound — recorded as report content, not as a capability); the P1 audit F-4 (the policy-scoping debt lineage); the semantic family's hypothetical-full-pass POLICY_PENDING pin (the R2 suite row 21 family) |
| §8 (review workflow) | the task's §10 (the independent tester duties — adopted verbatim as the role table); the R1-FU1 / R2-FU1 tester-record precedent (the tamper probe, the node-level accounting); the CLAUDE.md test-preservation contract |
| §9 (phases) | the task's §9 (the proposed sequence — adopted with C0 + C3 inserted under O-2 / O-6); the P5 §10 (the R1 / R2 bounded-phase pattern — exact file sets, frozen inputs, acceptance, stop conditions); the Q3-B precedent (the controlled live sub-step discipline) |
| §10 (risks) | this session's findings (CF-2 / the autocrlf state); the P5 §12.1 risk register (R-4 / R-5 / R-6 adopted at family scale); the R2-FU1 record (the flake class) |
| §11 (unresolved decisions) | the task's §7 (the tier vocabulary — the O-9 lineage question); P5 O-2 / O-3 / O-4 (the future-corpus / live-execution / capture decisions — the O-5 / O-6 successors at family scale); the 2.1 module's phantom-version import check (the O-5 constraint) |
| §12 (authorization boundaries) | the task's §12 hard restrictions (adopted as the standing per-phase boundaries); the P5 §13 invariance pattern |

---

# 14. Sources (complete list cited above)

* `CLAUDE.md` — the operating contract (frozen-phase semantics; test
  preservation; evaluation-truth rules; deterministic ownership;
  unknown-beats-fabricated-certainty; document ownership).
* `docs/PRODUCT_INTELLIGENCE_STATUS.md` — the R2-FU1 / R2 / R1-FU1 /
  R1 / P4-FU2 / P4-FU1 / P4 / P2-FU1 / P2 / P1 / Q3-B4-FU2 / Q3-B4 /
  Q3-B / Q3-A lineage records (the review states, the digests, the
  collection accounting, the R2 "Unresolved qualification gaps
  (explicit)" item 1 — the gap this program fills).
* `docs/PRODUCT_INTELLIGENCE_PLAN.md` — §26.28–§26.40 (the Q3-A / Q3-B /
  Q3-B3 / Q3-B4 / Q3-B5 records) + AD-072..AD-082 (the decision log
  through the starting SHA).
* `docs/PRODUCT_INTEL_Q3B5_P3_BUNDLE_COMPOSITION_DESIGN.md` — the
  approved corrected FU4 contract design (D1–D20, T1–T10, §1–§14, the
  Revision records 2 / 3) — read in full this session.
* `docs/PRODUCT_INTEL_Q3B5_P5_FU4_BINDING_REPLAY_QUALIFICATION_
  DESIGN.md` — the approved registration design (DEC-1..DEC-11, §1–§14,
  the R1 / R2 scopes, the adversarial matrices, the firewall
  obligations) — read in full this session.
* `docs/PRODUCT_INTEL_SEMANTIC_V2_Q3B4_AUTHORITY_BOUNDARY_DECISION.md` —
  the firewall decision of record (§4.1 invariant; the W1 guard;
  AD-Q3B4-6 conditioning; §6.1–§6.5 amendment / replay discipline).
* `docs/PRODUCT_INTEL_SEMANTIC_V2_PROMPT_2_1_DESIGN_Q3B3_FU2.md` — the
  approved Prompt 2.1 design (the SU axis; the P1–P6 table; the
  COMMERCIAL SALES-UNIT RULES content of record).
* `docs/PRODUCT_INTEL_Q3B5_P1_INDEPENDENT_AUDIT.md` — the P1 audit
  (F-3 the documentation lag; F-4 the policy-scoping debt — both
  inherited by this program).
* `product_intelligence/research/semantic_authority_fu4.py` — the
  qualified contract (this session: the full symbol inventory + the
  derivation / dispatch / gate / attestation surfaces; digests per §2.1
  / §2.7).
* `product_intelligence/research/semantic_authority_fu3.py` /
  `semantic_authority_v2.py` / `sales_unit_extraction.py` /
  `semantic_v2.py` — the frozen firewall / tier / extraction / input
  contracts (the delegation rows, the pricing constants, the P2 cue
  table + mapping, the 7-key response — digests per §2.1).
* `product_intelligence/research/semantic_decision_v2_fu4.py` /
  `semantic_decision_codec.py` / `semantic_decision_replay.py` /
  `semantic_decision_record.py` / `semantic_decision_v2.py` — the R1
  record surface + the universal envelope (the registry, the claim-
  based dispatch, the replay gate, the typed record + strict payload
  codec — digests per §2.2).
* `product_intelligence/semantic/contract_v2.py` /
  `contract_v2_1.py` / `runtime_v2.py` — the frozen prompt contracts +
  the live runtime (the 2.1 system text + digest, the binding
  constants, the pinned route, the qualification markers — digests per
  §2.3).
* `product_intelligence/evaluation/semantic_v2/{corpus,fixtures,gates,
  report,policy,evaluator,capture,direct_capture,cli}.py` — the
  semantic harness (the pattern source, byte-pinned — digests per §2.4;
  `decode_match_case` the public case-decode entry the family reuses
  read-only).
* `evaluation/semantic_v2_qualification/{corpus_v1.json, corpus_2_1.
  json, corpus_2_1_fu4.json, manifest_*.json, README.md,
  policy/qualification_policy_draft_1.json, reports/}` — the committed
  corpus / policy / baseline artifacts of the semantic family (the
  1.2.0 manifest statement — the gap of record; the case-document shape
  the family's Track B overlay mirrors).
* `tests/fixtures/pages/*` — the recorded real retail pages + the
  Micron 7500 catalog (the RECORDED_FIXTURE ground; the verified
  bundle-absence state, §2.5).
* `tests/research/test_semantic_authority_v2_fu4.py` (217 nodes — the
  A1 pin tables inspected, the CF-2 gap verified) /
  `test_semantic_decision_v2_fu4.py` (38 — the R1 matrix) /
  `tests/evaluation/semantic_v2/test_q3b5_p5_fu4_registration.py` (35 —
  the R2 matrix + the R2-endpoint pins) / the FU3 (98) + extraction
  (111 + 7) + codec / replay / V2 / record / boundaries suites — the
  behavioral evidence of record (node counts per §2.6).

---

*End of design. Q3-C-D1 deliverable of record. The design is UNAPPROVED
until ChatGPT's independent review of this document and its source
references completes. No implementation is authorized by this document
alone (§12).*
