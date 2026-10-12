# Product Intelligence — Q3-B5-P1 Independent Contract and Qualification Integrity Audit

**Session:** PRODUCT-INTEL.Q3-B5-P1-AUDIT (independent, fresh; no prior chat context)
**Mode:** AUDIT ONLY — no production code, test, corpus, report, policy, or
threshold change was made by this audit; no live capture; no deployment.
**Audited commit (starting SHA):** `a383c610f0274a1fda34aa56fb17c279af0df70e`
(`PRODUCT-INTEL.SEMANTIC-AUTHORITY-V2-Q3-B5-P1: prompt 2.1 versioned implementation`)
**Parent commit:** `e53d28c54840d296457dc586105cd3d1d545d394` (Q3-B4-FU2 endpoint)
**Baseline collection at the audited SHA:** **7142** (independently re-verified:
per-file sum over 175 files; parent `e53d28c` independently re-verified at
**7034** over 171 files via a temporary linked worktree, removed after use).
**Frozen contracts of record:**
- Approved design: `docs/PRODUCT_INTEL_SEMANTIC_V2_PROMPT_2_1_DESIGN_Q3B3_FU2.md`
  (Revision 2; sections 4/5/6/8/9, T1–T5, Q1–Q10).
- Authority-boundary decision: `docs/PRODUCT_INTEL_SEMANTIC_V2_Q3B4_AUTHORITY_
  BOUNDARY_DECISION.md` (§6.2 AD-Q3B4-5 binding correction, §9 phase plan row P1).
- Frozen prompt 2.0: `product_intelligence/semantic/contract_v2.py`
  (digest `c0cc98bdd6d357e81d4692218f18d354351fc2833267b3062b7cd74b18445a84`,
  **recomputed this audit: exact match**).
- Frozen S2-A authority module: `product_intelligence/research/
  semantic_authority_v2.py` (file-hash pinned by the pre-existing FU3 test
  `tests/research/test_semantic_authority_v2_fu3.py::TestOldTokenInvariance::
  test_the_frozen_s2a_module_is_byte_unchanged`; passed in this audit's full run).
- DRAFT policy: `evaluation/semantic_v2_qualification/policy/
  qualification_policy_draft_1.json` (byte-unchanged by the P1 commit; verified
  against the parent).

**Method note.** Every implementation-report claim below was treated as a claim,
not evidence. Each was re-derived from source (file/line references) and, where
executable, by independent out-of-suite execution in this session (corpus
comparison scripts, forged-artifact rejections, full-suite run). "Source-proven"
means the audit executed the production code path directly this session;
"test-proven" means the behavior is pinned by a committed test that passed in
this audit's runs but the audit did not separately re-execute the exact path.

---

## 1. Exact SHA and file inventory

Audited tree: `a383c610f0274a1fda34aa56fb17c279af0df70e` on `main`; worktree
clean except the pre-existing `tmp_collection.txt` (line-ending-only) tracked
modification and pre-existing untracked session/evidence artifacts, all
preserved and untouched by this audit.

The P1 commit changes **24 files, +13337 / −75 lines** (commit `--stat`,
independently reproduced). SHA-256 prefixes (first 16 hex) and byte sizes at
the audited SHA:

| SHA-256 (16) | bytes | file |
| --- | --- | --- |
| a26a4c8948920546 | 11415 | `evaluation/semantic_v2_qualification/README.md` (modified) |
| 6f5254c8772ea345 | 190978 | `evaluation/semantic_v2_qualification/corpus_2_1.json` (new) |
| f37956e45b3d873e | 16123 | `evaluation/semantic_v2_qualification/manifest_2_1.json` (new) |
| 7cf2519789f4bfae | 44570 | `evaluation/semantic_v2_qualification/reports/q3b5_baseline_2_1/no-capture_amax_qwen3.8-27b__report.json` (new) |
| 9c1d3b383f4f367d | 3507 | `.../q3b5_baseline_2_1/no-capture_amax_qwen3.8-27b__report.md` (new) |
| bfd63d3c83ce5567 | 44581 | `.../q3b5_baseline_2_1/no-capture_vllm-262k_Qwen3.6-27B-262K__report.json` (new) |
| b176e03879731e35 | 3518 | `.../q3b5_baseline_2_1/no-capture_vllm-262k_Qwen3.6-27B-262K__report.md` (new) |
| d7b2ae6bfac69b07 | 5387 | `product_intelligence/evaluation/semantic_v2/__init__.py` (modified) |
| 4da8b79a33ffc863 | 19159 | `product_intelligence/evaluation/semantic_v2/capture.py` (modified) |
| 0102c4ccc98034d6 | 18785 | `product_intelligence/evaluation/semantic_v2/cli.py` (modified) |
| 876edbe832288965 | 47350 | `product_intelligence/evaluation/semantic_v2/corpus.py` (modified) |
| 58b790879efb13f1 | 16235 | `product_intelligence/evaluation/semantic_v2/direct_capture.py` (modified) |
| cdb60166cf71d3f3 | 110621 | `product_intelligence/evaluation/semantic_v2/fixtures.py` (modified) |
| 113c7b53605b4a85 | 12188 | `product_intelligence/evaluation/semantic_v2/gates.py` (modified) |
| 77e7943dcf38da68 | 52401 | `product_intelligence/evaluation/semantic_v2/live_capture.py` (modified) |
| cad62e4234f7478a | 28029 | `product_intelligence/evaluation/semantic_v2/report.py` (modified) |
| ac0b2c3773222c96 | 6272 | `product_intelligence/semantic/__init__.py` (modified) |
| dc86899f233eb97b | 40486 | `product_intelligence/semantic/contract_v2_1.py` (new) |
| 011d8550b55a6011 | 6061 | `tests/evaluation/semantic_v2/_q3a_fu1_helpers.py` (modified, additive) |
| 617f349598d70466 | 10681 | `tests/evaluation/semantic_v2/_q3a_helpers.py` (modified, additive) |
| ad278dfcf39958a2 | 34935 | `tests/evaluation/semantic_v2/test_q3b5_p1_adversarial.py` (new) |
| 3af57f60b323c7ee | 25261 | `tests/evaluation/semantic_v2/test_q3b5_p1_binding_replay.py` (new) |
| 9e9111d28378c9d2 | 22107 | `tests/evaluation/semantic_v2/test_q3b5_p1_corpus_2_1.py` (new) |
| ec29a8ecd29f049a | 32224 | `tests/semantic/test_contract_v2_1.py` (new) |

**Not changed by the P1 commit (verified against the parent diff):**
`product_intelligence/semantic/contract_v2.py` (frozen 2.0),
`product_intelligence/research/*` (including `semantic_authority_v2.py`,
`semantic_authority_fu3.py`, `semantic_decision_v2.py`,
`semantic_decision_codec.py`, `semantic_decision_replay.py`),
`evaluation/semantic_v2_qualification/corpus_v1.json`, `manifest_v1.json`,
`policy/qualification_policy_draft_1.json`, `reports/q3a_baseline/*`
(the 2.0 no-capture baselines are byte-identical to the parent), the evaluator
(`evaluation/semantic_v2/evaluator.py`), and all of `runs/`, `web/`,
`execution/`, `providers/`, `domain/`.

**Live-capture evidence of record (unchanged, hash-verified this audit):**
`semantic_v2_live_captures/q3b-20261009T010312Z-amax__direct__amax_
qwen3.8-27b.json` = `d94f1ed8ec4d254aa2a80e4ff58bd0bc55eb8c3744ad22f53f0b602ae9084d9f`
(38,945 bytes) and `...__manifest.json` = `46f818bb02cc5838ab29aea9eb9d819108fa89c2f5a17349bb91e89544b99b79`
(20,293 bytes). No live model call or capture was performed in P1 and none was
performed in this audit.

---

## 2. Diff and test preservation

### 2.1 Production diff review (all 13 changed/new production files)

Every changed production hunk was read in full against the parent (see §4 for
the path-by-path trace). Summary of what the diff does and what it does not:

* `semantic/contract_v2_1.py` (new, 391 lines): separately versioned 2.1
  contract owner — `SEMANTIC_PROMPT_VERSION_V2_1 = "2.1"` (line 102),
  `V2_1_CONTRACT_BINDING` composed from the research package's frozen exports
  (lines 111–117; **no literal token strings in this source**),
  `SYSTEM_PROMPT_V2_1` (line 129), `render_v2_1_user_prompt` (line 258,
  fail-closed on 2.0 renderer drift), `SemanticPromptV2_1` construction guards
  (lines 292–327: foreign version or foreign system-prompt body rejected),
  `build_semantic_prompt_v2_1` (line 329), and five import-time
  self-consistency checks (lines 353–390).
* `evaluation/semantic_v2/corpus.py`: `BINDING_CORPUS_VERSIONS`
  (line 131: 2.0 binding ↔ 1.0.0, 2.1 binding ↔ 1.1.0) and
  `KNOWN_PRODUCTION_BINDINGS` (line 139, exactly those two); the loader
  (lines ~1205–1226) now refuses unknown bindings and any
  version/binding disagreement; a REAL_MARKET docstring clarification (no
  behavior change).
* `evaluation/semantic_v2/capture.py`: re-exports the 2.1 pins from the
  semantic owner (line 114, no literal copy); the PRODUCTION_ROUTE loader
  stays 2.0-only (`load_capture` line 431: `prompt_version != "2.0"` refused);
  `verify_capture_against_corpus` gains the prompt-axis cross-check
  (line 491).
* `evaluation/semantic_v2/direct_capture.py`: `DIRECT_KNOWN_PROMPT_VERSIONS`
  (line 91: `{2.0, 2.1}`); loader accepts exactly those (line ~301);
  `verify_direct_capture_against_corpus` gains the prompt-axis cross-check
  (line 388).
* `evaluation/semantic_v2/live_capture.py`: the runner selects the prompt
  builder from the corpus's bound prompt axis (lines 526–556: 2.0 axis →
  frozen 2.0 builder; 2.1 axis → 2.1 builder; any other axis → fail-closed
  `LiveCaptureConfigError`); the document pins `self._prompt_version`
  (line 908) and the manifest records the REAL system-prompt digest of the
  bound version (lines 967–969); manifest key set unchanged; CLI printout
  names the bound prompt version (line ~1197). No prompt-version flag exists
  on the CLI (verified: no such `add_argument` in `live_capture.py` or
  `cli.py` — the corpus file is the only selector).
* `evaluation/semantic_v2/gates.py`: `zero_contract_version_mismatch`
  (lines 170–171) now passes for either known production binding; the
  detail text is byte-identical in the 2.0 context and carries the 2.1
  binding identity in the 2.1 context (the only allowed delta per design §9.1;
  the 2.0-context byte identity is pinned by test against the committed 2.0
  baseline reports and passed in this audit's runs). Gate names/order and
  fail-closed semantics unchanged (8/8 names re-pinned by test).
* `evaluation/semantic_v2/report.py`: `_contract_section(binding)`
  (line 117) is version-aware — 2.0 context byte-identical to pre-2.1, 2.1
  context carries prompt 2.1 + FU3 token + the REAL 2.1 system-prompt digest
  (`_system_prompt_digest_v2_1`, line 177); unknown binding → `ReportError`
  (line 138). `_verify_report_binding` (line ~379) now checks the report's
  binding against the **presented corpus's** binding instead of the
  hard-coded 2.0 tuple. The `policy` section renders `null` when the policy is
  not applicable to the corpus identity (lines 303–308, 498–503) — a
  previously unreachable crash path per the commit message; the 2.0 output is
  unchanged (the DRAFT policy applies to 1.0.0).
* `evaluation/semantic_v2/fixtures.py`: `CORPUS_VERSION_2_1 = "1.1.0"`
  (line 123) and `build_corpus_2_1_document()` (line 2936): derives the 1.1.0
  document from the sealed 1.0.0 document moving exactly
  `corpus_version`, `semantic_contract_binding`, and the recomputed
  `corpus_digest`; `label_revisions` stays empty.
* `evaluation/semantic_v2/cli.py`: `corpus-build` additionally regenerates
  `corpus_2_1.json` + `manifest_2_1.json`; all other commands unchanged in
  behavior (version-agnostic; the corpus file selects).
* `evaluation/semantic_v2/__init__.py`, `semantic/__init__.py`: additive
  re-exports of the new pins (no removals).

**Frozen-artifact invariance (independently verified):**
- `contract_v2.py` byte-identical to the parent; 2.0 digest reproduces
  (`c0cc98bd…a84`).
- `research/` tree untouched by the commit; the FU3 file-hash pin on
  `semantic_authority_v2.py` passes (full run).
- DRAFT policy, `corpus_v1.json`, `manifest_v1.json`, `reports/q3a_baseline/*`
  byte-identical to the parent.
- `python manage.py check`: "System check identified no issues (0 silenced)";
  `makemigrations --check --dry-run`: "No changes detected" (re-run this audit).

### 2.2 Test preservation

* **Node-level comparison (independent collection at both SHAs):**
  parent `e53d28c` = **7034** nodes / 171 files; audited SHA = **7142** nodes /
  175 files. Exact node-ID set difference: **0 nodes present in the parent and
  absent at the audited SHA** (no deletion, rename, skip, xfail, deselect, or
  ignore); **exactly 108 nodes added**, all in the four new files; **no
  existing test file changed its node count** (no auto-expanded parameterized
  scan — the only new production file sits in `semantic/`, which no per-file
  boundary scan parameterizes over, consistent with the commit message).
* **Per-file new nodes (collected):** `test_contract_v2_1.py` 49,
  `test_q3b5_p1_corpus_2_1.py` 20, `test_q3b5_p1_binding_replay.py` 20,
  `test_q3b5_p1_adversarial.py` 19. (The commit message attributes 49/21/19/19
  — the total 108 is right, the two per-file attributions are off by one; see
  finding F-2.)
* **The two modified test helpers are strictly additive vs the parent:**
  - `_q3a_helpers.py`: +8 lines, three new path constants
    (`CORPUS_2_1_PATH`, `MANIFEST_2_1_PATH`, `BASELINE_2_1_REPORT_DIR`); no
    existing line changed.
  - `_q3a_fu1_helpers.py`: one new optional keyword `prompt_version`
    (default `None` → the corpus binding's prompt axis, which for the committed
    1.0.0 corpus is `"2.0"` — byte-identical to the pre-2.1 helper's
    `PROMPT_VERSION = "2.0"` literal); no existing assertion or signature
    changed.
* **New-test quality (read in full):** all four files are offline
  (scripted recording transport doubles with prompt guards; one
  socket-blocked pipeline test). No test relaxes a pre-existing contract; the
  adversarial file asserts the pre-registered 2.1 expectations (CRITICAL
  false MATCH on 0018/0022/0032; the 0037 flip; alias zero-authority;
  sales-unit-blindness property) and never asserts a model call was made.

---

## 3. Prompt 2.1 fidelity (design Rev-2 §9.2 vs implemented `SYSTEM_PROMPT_V2_1`)

Method: the §9.2 draft code block was extracted from the design document, its
reviewer annotations stripped (header markers, inline `[2.1 NEW]`/`[2.1
CHANGED …]` markers, the whole-line CL-9 note — all explicitly "not prompt
text"), and the result compared line by line against the implemented
`SYSTEM_PROMPT_V2_1` (108 lines each).

**Result: 107 of 108 lines are byte-identical after annotation stripping. The
single substantive deviation is the disclosed RESPONSE FORMAT wording
difference:**

| Line | Design Rev-2 draft | Implementation (= frozen 2.0, = Revisions 0 and 1) |
| --- | --- | --- |
| RESPONSE FORMAT, sentence 1 | "There is no chain-of-thought field **and there is no** hidden-reasoning field: …" | "There is no chain-of-thought field **and no** hidden-reasoning field: …" |

The draft marks that section `[2.0 unchanged, with one [2.1 NEW] addition
preserved from revisions 0/1]`, and the frozen 2.0 text (as do Revision 0 and
Revision 1 drafts, verified by grep across the three prior design documents)
reads "and no hidden-reasoning field". The implementation therefore follows
the frozen 2.0 wording and the draft's own marker; the Rev-2 draft's code
block contains an unmarked internal inconsistency (its marker says
"2.0 unchanged" while the sentence was re-worded). The implementation's
choice is the only one consistent with the marker, with design §9.5
("Everything else in the Revision 1 draft is preserved byte-for-byte"), and
with the parser-facing output contract (the sentence is instructional, not
schema). **No silent correction was made to the design or acceptance
criteria; the discrepancy is recorded here for the reviewer.** (Finding F-1.)

**Everything else, verified line by line:**

* The one authorized addition: final line
  "MATCH_AUTHORIZED_IDENTIFIER_RELATION may be used only when the CONTEXT
  PROVENANCE section explicitly lists MANUFACTURER_RELATION_AUTHORITY." —
  present; the RESPONSE FORMAT section is otherwise byte-identical to 2.0
  (12 → 13 lines).
* Identifier-resolution rules: ESTABLISHED-only-by list; U2N "not a conflict,
  not a ground, contributes no resolution … at DESCRIPTION resolution"; U3
  family-membership-only ("a family prefix can be shared by more than one
  part", "never a NO_MATCH on the prefix alone"); U4 description resolution
  ("the same description can be published by different products, and the
  supplied evidence does not show that it is not here"); U5 blocks the
  distinctive-alignment test, authority-only establishment at part-number
  resolution, unproven-different → UNCERTAIN, "do not assert MPN_IDENTITY on
  an unproven difference" — all byte-identical to the draft.
* New sections present and byte-identical to the draft: IDENTITY RESOLUTION
  (three resolutions; asserts-nothing-beyond; exact identity owned by the
  deterministic layer and human confirmation; no resolution upgrades),
  DISTINCTIVE-ALIGNMENT TEST (pinning; strictly-coarser example; supplied-
  evidence bound; "Alignment is NOT uniqueness"), READING THE DETERMINISTIC
  IDENTITY CONTEXT (requirement line = downstream authority-tier policy,
  corrected trust reading), MISSING-CRITICAL ATTRIBUTES RULES (three-part,
  re-anchored to grounding at any resolution; G1 gaps not decision-critical;
  BRAND/REVISION_OR_SUFFIX/CONDITION never named), INTERNAL CONTRADICTION
  RULE (unpinned in both directions; never NO_MATCH on the contradiction
  alone), COMMERCIAL SALES-UNIT RULES (WHAT A MATCH ASSERTS, PRECISELY with
  the price-comparability non-assertion; ABSOLUTE RULE with the raw-cue
  evidence base; MISSING SALES UNIT NON-CRITICAL and CRITICAL/SU-ENT).
* Sales-unit uncertainty: UNAVAILABLE = recorded absence, never "single
  unit", never named missing-critical under the non-critical condition; only
  the U5 entanglement (SU-ENT) blocks MATCH with UNCERTAIN naming
  PACKAGING_QUANTITY/BUNDLE — as designed.
* Contradictions and missing-critical behavior: as designed (approved
  decision 7; the three-part rule).
* CL-9: no confidence-guidance wording — the confidence surface is the 2.0
  format line plus the one absolute-rule no-override sentence (pinned by
  test; confirmed by the line-by-line comparison).
* No reviewer annotations remain in the prompt text (pinned by test).
* **User template (design §9.4):** `render_v2_1_user_prompt` applies exactly
  the two approved annotation lines (section-C header + the
  relationship-requirement line) over the frozen 2.0 rendering, and fails
  closed if either 2.0 anchor does not occur exactly once. **Independently
  verified this audit for ALL 43 eligible cases of BOTH corpus versions: the
  rendered diff is exactly those two lines per case; every other rendered
  line is byte-identical to 2.0.** The 2.0 renderer emits each anchor exactly
  once structurally (`contract_v2.py` lines ~389, ~420).
* 2.0 coexistence: `contract_v2.py` untouched; 2.0 prompts remain
  deterministically reconstructable (test-pinned per case); the 2.1 builder
  constructs only 2.1 and rejects a foreign version or foreign system-prompt
  body at construction (lines 292–327).
* Binding: `V2_1_CONTRACT_BINDING = ("V2", "2.1", 1, 1,
  "SEMANTIC_AUTHORITY_V2_S2A_FU3")` — composed from frozen exports
  (drift-pinned by test). This deviates from the design §9.1 text
  (`("V2","2.1",1,1,"SEMANTIC_AUTHORITY_V2_S2A_FU2")`) **exactly as the
  approved Q3-B4 decision §6.2 (AD-Q3B4-5) corrects it**: FU3 was registered
  (Q3-B4-FU1/FU2, precedes P1), so the first 2.1 production binding carries
  the separately versioned FU3 token; the design's all other content stands.
  Recorded as an authorized, disclosed deviation — not a defect.
* 2.1 system-prompt digest (recorded evidence):
  `e2949e7544d26228ac6f5555ae8ebd28019076e1de88ace25e79a5d942d818fc`
  (recomputed this audit; matches the committed 2.1 baseline reports'
  `contract.system_prompt_digest`).

---

## 4. Corpus integrity (independent comparison of 1.0.0 vs 1.1.0)

Method: both committed JSON documents were parsed and compared field by field
in this session (independent of the project's tests), and every digest was
recomputed with the project's canonical serialization (sorted keys, compact,
ASCII).

| Property | Result |
| --- | --- |
| Case count | 56 in both (43 semantic: 36 AUTHORITATIVE + 7 AMBIGUOUS; 13 CONTRACT_NEGATIVE) |
| Case ID sets | Identical (same 56 IDs, same order) |
| Per-case documents (all fields: `input_payload`, `expected`, `label`, `category`, `case_class`, `evidence_kind`, `input_shape`, `challenge_tags`, `substate`, `primary_signal`) | **Byte-identical for all 56 cases** (zero differences) |
| Per-case `case_digest` | Identical for all 56 cases; every digest recomputed and verified against its case content in both files |
| `label_revisions` | `[]` in both (no label revision) |
| `corpus_id` / `corpus_label` / `corpus_schema_version` / `created_utc` | Identical |
| `corpus_version` | `1.0.0` → `1.1.0` (authorized move) |
| `semantic_contract_binding` | `["V2","2.0",1,1,"SEMANTIC_AUTHORITY_V2_S2A_FU2"]` → `["V2","2.1",1,1,"SEMANTIC_AUTHORITY_V2_S2A_FU3"]` (authorized move, per AD-Q3B4-5) |
| `corpus_digest` | `2c37ba088c317d8cefc6ad0dd7e0d73cfd085f6474ef43eb6953e3cf0170b549` (1.0.0 — **unchanged, matches the frozen record of every prior phase**) → `14396eae884841e20063cb4da0d4424ce8f05ff8745f2c787fc395d250ea8dcd` (1.1.0 — recomputed and verified over the re-sealed state, which excludes exactly `label_revisions` and `corpus_digest`) |
| Top-level delta | **Exactly** `{corpus_version, semantic_contract_binding, corpus_digest}` — the design §9.1 binding-only re-seal |
| Manifests | `manifest_v1.json` and `manifest_2_1.json` each reproduce byte-identically from their corpus document via `build_manifest_document` (verified this session); per-case manifest entries carry the identical case digests |
| Anti-manipulation on the re-seal | Verified this session: an unsealed label edit on 1.1.0 is rejected at load (`case_digest does not verify`); a schema-valid expected-pole swap on an AMBIGUOUS case is likewise digest-rejected; both 1.0.0 and 1.1.0 load cleanly against their own bindings |

**No unexplained case-level difference exists. The re-seal is exactly the
binding-only re-seal the approved design specifies (Q5 / decision 8).**

---

## 5. Cross-version authority isolation (path trace)

Each required property, with the source that enforces it (line references at
the audited SHA) and how it was verified:

| Property | Enforcement (source) | Verification |
| --- | --- | --- |
| 2.0 cannot be interpreted as 2.1 | 2.0 builder pins version `"2.0"` and the frozen body (`contract_v2.py` `SemanticPromptV2.__post_init__`); corpus 1.0.0 loads only under the 2.0 binding (`corpus.py` line 1221); the 2.1 runner selection maps the 2.0 axis to the frozen 2.0 builder only (`live_capture.py` lines 526–537) | Source + this audit's execution: the runner over the 1.0.0 corpus renders byte-frozen 2.0 for 43/43 cases (test-proven) and both corpora load with their own axes (source-proven) |
| 2.1 cannot be interpreted as 2.0 | `SemanticPromptV2_1` rejects a foreign version **and a foreign (2.0) system-prompt body** (`contract_v2_1.py` lines 292–327); the frozen V2 persistence adapter pins `prompt_version == "2.0"` + the FU2 token and has `supported_bindings == (V2_CONTRACT_BINDING,)` (`semantic_decision_v2.py` line 642; `SEMANTIC_V2_ADAPTER`); the replay registry `SUPPORTED_CONTRACT_BINDINGS` = V1 + 2.0 bindings only, unknown bindings refused (`semantic_decision_replay.py` line 130); a 2.1/FU3-bound V2-shaped payload is refused by the codec (`decode_semantic_decision_record` strict contract check) | Source + this audit's execution of the codec refusal path via the committed test (test-proven) and registry inspection (source-proven) |
| Unknown versions fail closed | Corpus: unknown binding refused, unknown corpus version under a known binding refused, unknown prompt axis (`"2.2"`, `"9.9"`) refused at direct-capture load, version/binding disagreement refused in both directions (`corpus.py` lines 1214–1226; `direct_capture.py` line ~301); report: unknown binding → `ReportError` (`report.py` line 138); prompt builders: foreign version/body rejected | **Source-proven — this audit executed all six forged-corpus variants and all forged-prompt-version variants directly; every one was rejected** (see §6 matrix) |
| Capture metadata cannot silently select a different prompt or authority token | The capture document carries no authority token at all (keys: `semantic_contract`, `prompt_version`, corpus id/version/digest, … — `direct_capture.py` `_DOCUMENT_KEYS` lines 146–163); the prompt axis is cross-checked against the bound corpus's binding prompt axis in both modes (`capture.py` line 491, `direct_capture.py` line 388); the authority token travels only inside the corpus binding, sealed by the corpus digest; the live runner derives the prompt from the corpus axis and records the REAL system-prompt digest in the manifest (`live_capture.py` lines 908, 967–969); no CLI flag can override the prompt version | Source + this audit's execution: a 2.0 capture presented against 1.1.0 (both untampered and with the corpus identity fields moved to 1.1.0) is refused; a 2.1 capture against 1.0.0 likewise; the PRODUCTION_ROUTE loader refuses a 2.1-named capture at load |
| Report verification checks the correct prompt digest and binding | `_verify_report_binding` checks corpus digest + corpus version + `semantic_contract_binding == presented corpus's binding` + per-case expected/acceptable snapshots + the sealed report digest (which covers `contract.system_prompt_digest` and `contract.semantic_contract_binding`) (`report.py` lines ~365–420); the 2.1 baseline reports bind prompt 2.1 + FU3 token + the REAL 2.1 digest `e2949e75…` | **Source-proven — this audit executed**: 2.0 report vs 1.0.0 corpus VERIFIED; 2.1 vs 1.1.0 VERIFIED; both cross-version combinations REJECTED (corpus digest); forged FU2 token in a 2.1 report REJECTED (binding mismatch); forged prompt axis REJECTED; zeroed `system_prompt_digest` REJECTED (report digest tamper); flipped `authority.granted` REJECTED (report digest tamper) |
| No report can grant pricing authority | `authority.granted` is hard-coded `False` and sealed in the report digest (`report.py` `_authority_section` lines 244–253); `v2_authority_qualified` mirrors the module marker (False); the 2.1 no-capture report text names no tier (pinned by test: no `AI_ASSISTED_COMPARABLE`/`MACHINE_VERIFIED`/`HUMAN_CONFIRMED` in the report JSON) | Source-proven (section + digest behavior executed this audit) + test-proven (no tier names) |
| FU3 remains unreachable from live pricing | `research/semantic_authority_fu3.py` is contract-only: a repository-wide import scan shows the FU3 derivation symbols (`derive_authority_tier_fu3`, `derive_identity_resolution_bound`, `derive_sales_unit_authority`, `AuthorityDecisionV2FU3`, …) referenced ONLY by `research/__init__.py` (re-export) and the research tests; no module in `runs/`, `web/`, `execution/`, `providers/`, `semantic/runtime_v2.py`, `semantic_decision_v2.py`, or `research/semantic_v2.py` imports them; the live runtime pins prompt 2.0 (`runtime_v2.py` line 519); the production codec/replay registry does not contain the 2.1/FU3 binding | Source-proven (import scan + pin inspection this audit) + test-proven (codec refusal, registry exactness) |
| V2_AUTHORITY_QUALIFIED remains False | `semantic_decision_v2.py` line 227 and `runtime_v2.py` line 97: `V2_AUTHORITY_QUALIFIED: Final[bool] = False` (both files untouched by the P1 commit) | Source-proven |
| Sales-unit-blindness of the frozen derivation (documented property, design T2) | Pinned by `tests/evaluation/semantic_v2/test_q3b5_p1_binding_replay.py::TestSalesUnitBlindnessDocumentedProperty`: the old token has no sales-unit input (passing one raises), U1+MATCH+HIGH+STRONG+clean derives the pricing-eligible `AI_ASSISTED_COMPARABLE` under the frozen token (the R14 exposure), while the separately versioned FU3 derivation caps SU-UNK at `NEEDS_REVIEW` via `CEILING_SALES_UNIT_NOT_PROVEN` and stands SU-EQ; `UNAVAILABLE` never derives `PROVEN_EQUIVALENT`; the unit derivation's inputs are typed and model-claim-free (signature-pinned) | Test-proven (passed in this audit's runs); consistent with the Q3-B3-FU2 §3.3/§3.5 design determination |

---

## 6. Adversarial matrix (independently devised negative cases)

For each mandated shape: what the audit constructed, what the actual code did,
and the evidence class. "Source-proven (executed)" = this audit drove the
production path directly in-session; "test-proven" = committed test passed in
this audit's runs; "prompt-semantics" = model-side behavior that no offline
code can structurally enforce (by design; the parser is input-blind).

| # | Adversarial case | Constructed by the audit | Actual code behavior | Evidence class |
| --- | --- | --- | --- | --- |
| 1 | Forged prompt version | Direct capture `prompt_version` = `"2.2"`, `"9.9"`; PRODUCTION_ROUTE capture `prompt_version` = `"2.1"` | All three rejected: `"2.2"`/`"9.9"` at `load_direct_capture` (`DirectCaptureIntegrityError`: not one of the known V2 prompt versions); the 2.1-named production-route capture at `load_capture` (`CaptureIntegrityError`: not the frozen `"2.0"`) | Source-proven (executed) + test-proven |
| 2 | Mismatched corpus and capture binding | (a) 2.0 capture vs 1.1.0 corpus; (b) 2.1 capture vs 1.0.0 corpus; (c) the cross-axis tamper: capture's corpus id/version/digest moved to the other corpus while its prompt axis stays | All rejected: (a)/(b) at corpus identity (`different corpus`) or the axis cross-check (`prompt axis … does not match the bound corpus's contract binding prompt axis`); (c) at the axis cross-check in both modes; the evaluator level fails closed (`QualificationContractError`) before scoring | Source-proven (executed) + test-proven |
| 3 | Forged authority token | Corpus binding with 2.1 prompt axis + the frozen FU2 token; report contract section with the FU2 token substituted into a 2.1 report | Corpus rejected at load (`not one of the known production bindings`); report rejected at verification (`report contract binding mismatch`); a capture document cannot name an authority token at all (no such key in `_DOCUMENT_KEYS`) — the token reaches captures only via the digest-sealed corpus binding, so there is no forge surface in the capture metadata | Source-proven (executed) |
| 4 | Altered prompt digest | 2.1 report `contract.system_prompt_digest` zeroed; 2.0 report `authority.granted` flipped to `True` | Both rejected: `report digest does not verify (tampered)` (the digest seals the contract and authority sections); the legitimate 2.1 digest `e2949e75…` was independently recomputed from `SYSTEM_PROMPT_V2_1` and matches the committed report | Source-proven (executed) |
| 5 | Changed case labels | (a) unsealed expected-decision edit on 1.1.0 (schema-invalid variant); (b) schema-valid expected-pole swap on AMBIGUOUS case `V2Q-DIMM-U2N-THIN-0009` (UNCERTAIN→MATCH, in-set); (c) committed 1.0.0 vs 1.1.0 label comparison | (a) rejected at load (bounded schema rule); (b) rejected at load (`case_digest does not verify (the case was mutated after sealing)`); (c) 56/56 case documents byte-identical, `label_revisions` empty in both | Source-proven (executed) |
| 6 | Unknown corpus version | `corpus_version` = `"1.0.0"` under the 2.1 binding; `"1.1.0"` under the 2.0 binding; `"1.2.0"` under the 2.1 binding | All rejected at load: the sealed version/binding correspondence (`corpus.py` lines 1220–1226) fails closed in every combination | Source-proven (executed) |
| 7 | Conflicting packaging evidence | Self-contradictory packaging (title "single unit" vs spec "tray of 20") and published-incompatible packaging with a MATCH response | Model-side: the internal-contradiction rule (U-4-style UNCERTAIN; never NO_MATCH on the contradiction alone) is prompt semantics — stated, not structurally enforced (design R5; the parser is input-blind). Code-side: a MATCH on a published-incompatible case (0032) scores `FALSE_MATCH`/`CRITICAL`, fails the packaging + ALWAYS_HARD gates, and the decision is `NOT_QUALIFIED`; the safe NO_MATCH scores `CORRECT` with all gates green | Prompt-semantics + test-proven (harness detection) |
| 8 | Missing commercial-unit quantity | The SU-ENT shapes (0018/0022, channel UNAVAILABLE, no cue) with a MATCH response; the silent multi-pack (A9: G1 exact-identifier MATCH, channel UNAVAILABLE) | 0018/0022 MATCH → `FALSE_MATCH`/`CRITICAL`, counted in `sales_unit_safety_false_match_count`, near-miss metric, decision `NOT_QUALIFIED`-direction; A9 MATCH scores `CORRECT` against the label (the contract's own row M-1) while `derive_sales_unit_authority` returns `UNPROVEN` (never `PROVEN_EQUIVALENT`) and the separately versioned FU3 derivation caps the tier at `NEEDS_REVIEW` (not pricing-eligible) — the firewall the design mandates | Test-proven (harness + FU3 derivation) + prompt-semantics (the UNCERTAIN naming on 0018/0022) |
| 9 | Generic descriptions that appear equivalent | MATCH on the generic-overlap shapes (0015 "NVMe SSD" vs requested "3.84TB U.3 NVMe data center SSD"; 0043; 0009 strictly-coarser) and the in-set MATCH pole (0043 AMBIGUOUS) | 0015 MATCH → `FALSE_MATCH`/`HIGH`, `false_match_count` 1, decision stays `POLICY_PENDING` (never `QUALIFIED` — the DRAFT policy is inapplicable to 1.1.0 and unapproved); UNCERTAIN on 0015/0043/0009 → `CORRECT`; 0043 MATCH → `DEFENSIBLE` (in-set, no severity) | Test-proven (harness detection) + prompt-semantics (the U-1 rule) |
| 10 | Different MPN with matching attributes | U5 complete-different-number shapes: 0018/0022 (customer-retrieval alias, full attribute alignment) with MATCH; 0020 (labeled `MANUFACTURER_RELATION_AUTHORITY`) with the licensed reason code; unauthorized `MATCH_AUTHORIZED_IDENTIFIER_RELATION` on 0018 | 0018/0022 MATCH → `CRITICAL` false MATCH (sales-unit-safety metric = 2); the recorded context derives resolution bound `NONE` for the alias shape and `PART_NUMBER` for the authority-resolved 0020; the unauthorized reason code is flagged (`UNAUTHORIZED_AUTHORITY_CLAIM` + `CUSTOMER_ALIAS_PROMOTION` notes) and fails both promotion gates; 0020 with the licensed code scores `CORRECT` with no flag | Test-proven (harness + FU3 bound) + prompt-semantics (the U5 blocking rule) |
| 11 | Historical replay under the wrong binding | (a) committed 2.0 no-capture baseline reports vs the 1.1.0 corpus; (b) committed 2.1 baselines vs the 1.0.0 corpus; (c) 2.1-bound V2-shaped payload into the production codec; (d) identical scripted responses scored under both corpus versions | (a)/(b) rejected by `verify_report`/`verify_direct_report` (corpus digest / binding mismatch — cross-version replay refusal both directions); (c) rejected (`SemanticDecisionCodecError`; the registry knows exactly the V1 + 2.0 bindings); (d) per-case verdicts identical across versions while record identities (binding, corpus digest) differ — scoring is binding-agnostic, identity is not | Source-proven (a/b/c executed) + test-proven (d) |

**No constructed negative case was accepted by the production code.** Every
forge surface examined (corpus document, capture document, manifest fields,
report contract/authority sections, codec payload) fails closed, and the
model-side semantic cases are detected at qualification by the scoring and
gate machinery exactly as the design pre-registers (with the stated
prompt-semantics caveat that the parser is input-blind — a documented,
carried-forward limitation, not a P1 regression).

---

## 7. Test evidence (this audit, exact)

Environment: Windows; CPython **3.14.7** (`C:\Users\LEVIN-Z\AppData\Local\
Python\pythoncore-3.14-64\python.exe`); `pytest 9.1.1`; project
`requires-python = ">=3.12"`. (The interpreter is above the declared floor and
is the same environment class recorded by prior phases — finding F-5.)

* **Collection at the audited SHA:** 7142 nodes / 175 files (matches the
  briefing baseline). **Collection at the parent** (temporary linked worktree,
  removed after use): 7034 / 171. Delta: +108 nodes in 4 new files; 0 nodes
  removed/renamed; 0 existing-file count changes. The 108 exact new node IDs
  are Appendix A.
* **The four new test files:** `108 passed, 0 failed` (4.72 s) —
  `tests/semantic/test_contract_v2_1.py` (49),
  `tests/evaluation/semantic_v2/test_q3b5_p1_corpus_2_1.py` (20),
  `tests/evaluation/semantic_v2/test_q3b5_p1_binding_replay.py` (20),
  `tests/evaluation/semantic_v2/test_q3b5_p1_adversarial.py` (19).
* **Focused suites** `tests/evaluation/semantic_v2/` + `tests/semantic/`:
  **780 passed, 0 failed** (13.06 s).
* **Full suite** (`python -m pytest`): **7142 collected; 7131 passed,
  11 failed; 39 subtests passed; 0 skipped / 0 xfailed / 0 deselected**
  (430.51 s). The 11 failures are EXACTLY the members of the documented
  load-sensitive clean-interpreter subprocess-guard flake class (the fixed
  eleven-node allowlist from the Q3-A-FU1 / Q3-B records), and every one
  carries the identical signature — `OSError: [WinError 6] The handle is
  invalid` at `subprocess.py:1431` (`_winapi.DuplicateHandle` inside
  `Popen.__init__ → _get_handles → _make_inheritable`), raised **before any
  project code runs**; zero assertion failures, zero collection errors:

  1. `tests/domain/test_domain_boundaries.py::test_domain_imports_without_django_network_or_llm_dependencies`
  2. `tests/evaluation/test_evaluation_boundaries.py::test_loading_the_corpus_imports_no_framework_or_provider`
  3. `tests/providers/test_provider_boundaries.py::test_importing_the_provider_boundary_pulls_in_no_third_party_dependency`
  4. `tests/providers/test_provider_boundaries.py::test_importing_the_page_boundary_pulls_in_no_third_party_dependency`
  5. `tests/providers/test_provider_boundaries.py::test_http_pdf_imports_no_third_party_dependency`
  6. `tests/research/test_enterprise_ssd_boundaries.py::test_importing_enterprise_ssd_pulls_in_no_third_party`
  7. `tests/research/test_enterprise_ssd_boundaries.py::test_importing_enterprise_ssd_does_not_load_django`
  8. `tests/research/test_listing_normalization_boundaries.py::test_importing_the_research_core_still_pulls_in_no_third_party_dependency`
  9. `tests/research/test_research_identity_boundaries.py::test_importing_the_research_core_pulls_in_no_third_party_dependency`
  10. `tests/research/test_specification_boundaries.py::test_importing_specifications_pulls_in_no_third_party_dependency`
  11. `tests/runs/test_research_run_boundaries.py::test_the_domain_still_imports_without_django_present`

* **Isolated one-node-per-process re-runs of the 11 (preserved, not hidden
  behind a summary):** 9/11 re-passed on the first isolated attempt;
  `test_importing_enterprise_ssd_pulls_in_no_third_party` re-passed on the
  second attempt; `test_importing_the_provider_boundary_pulls_in_no_third_
  party_dependency` flaked once more in isolation with the **identical**
  `WinError 6` Popen signature and re-passed on the third attempt (sustained
  handle pressure from the back-to-back full runs). **11/11 ultimately
  re-passed; no non-flake node failed anywhere in this audit.**
* **Django:** `manage.py check` → "System check identified no issues
  (0 silenced)"; `manage.py makemigrations --check --dry-run` → "No changes
  detected".
* `git diff --check e53d28c..a383c61` → clean.
* No test, allowlist, or threshold was modified by this audit.

---

## 8. Findings, severity-ranked

| ID | Severity | Finding |
| --- | --- | --- |
| F-1 | LOW (documentation; no implementation correction) | The Q3-B3-FU2 Rev-2 draft's RESPONSE FORMAT code block re-words one frozen 2.0 sentence ("…and **there is no** hidden-reasoning field") although the section is marked `[2.0 unchanged, with one [2.1 NEW] addition]`; Revisions 0/1 and the frozen 2.0 text all read "…and **no** hidden-reasoning field". The implementation follows the frozen 2.0 wording (the only choice consistent with the marker and design §9.5). The deviation exists in the design document's code block, not in the shipped prompt. Per the audit mandate the design and acceptance criteria were **not** corrected; this is recorded for the reviewer. No parser, schema, or behavior impact. |
| F-2 | LOW (reporting accuracy) | The P1 commit message attributes the 108 new nodes as 49/21/19/19 across the four files; the actually collected node IDs are 49 (`test_contract_v2_1.py`) / 20 (`test_q3b5_p1_corpus_2_1.py`) / 20 (`test_q3b5_p1_binding_replay.py`) / 19 (`test_q3b5_p1_adversarial.py`). The total is correct; two per-file attributions are off by one. Appendix A is the authoritative node list. |
| F-3 | LOW (documentation lag; process) | `docs/PRODUCT_INTELLIGENCE_STATUS.md` was not updated by Q3-B3-FU2, Q3-B4, Q3-B4-FU1, Q3-B4-FU2, or Q3-B5-P1: its "Current state" header still points at Q3-B-FU1 (IMPLEMENTED / PENDING FINAL REVIEW) and no section exists for the Q3-Bx design/decision/implementation phases. `docs/PRODUCT_INTELLIGENCE_PLAN.md` is likewise silent on them. The committed design documents and commit messages are complete and self-contained, but the document-ownership rule (STATUS updated at every phase completion) has not been applied since Q3-B-FU1. Recommend the approval record (or the next phase) update STATUS; no contract content is affected. |
| F-4 | INFO (governance for Q3-C) | The DRAFT policy is scoped to corpus 1.0.0 (`applicability.corpus_version = "1.0.0"`, byte-unchanged as designed), so 2.1/1.1.0 evaluations render `policy: null` and can only decide `POLICY_PENDING` ("no approved applicable policy") — even a DRAFT approved as-is would not apply to the 1.1.0 re-seal. Q3-C must therefore include a policy-governance step for the 1.1.0 corpus identity (and, per the Q3-B4 decision §9, be conditioned on the P4 disposition). Consistent with the approved design; stated so it is not missed at Q3-C. |
| F-5 | INFO (environment) | Validation ran under CPython 3.14.7 (declared `requires-python >= 3.12`; supported baseline 3.12). Same environment class as all prior phase validations; the full suite is green apart from the documented flake class. No action for P1. |
| F-6 | INFO (carried property, not a regression) | Report verification seals (and tamper-detects) the report's own `system_prompt_digest` but does not recompute it from the real prompt text of the bound version; the builder always records the real digest. This property existed identically for 2.0 reports before P1. Cross-version reinterpretation and tampering are still refused (binding + corpus-digest + report-digest checks, all source-proven in §5/§6). |

**No blocker-severity finding. No finding requires a bounded correction to the
P1 implementation.** F-1 is a design-document internal inconsistency that the
implementation correctly did not follow; F-2/F-3 are reporting/documentation
items; F-4–F-6 are informational.

---

## 9. Replay and binding analysis (consolidated)

* **Two corpora, two bindings, no reinterpretation.** 1.0.0 ↔
  `("V2","2.0",1,1,"SEMANTIC_AUTHORITY_V2_S2A_FU2")`; 1.1.0 ↔
  `("V2","2.1",1,1,"SEMANTIC_AUTHORITY_V2_S2A_FU3")`. The loader enforces the
  exact version↔binding seal and refuses every other combination (executed).
* **Captures are bound to the corpus that sealed them.** Both capture modes
  cross-check the prompt axis against the corpus binding; the production-route
  mode is 2.0-only at load (it mirrors the live runtime, which executes the
  frozen 2.0 builder); the direct mode accepts exactly {2.0, 2.1} and then
  enforces the axis. The authority token is not a capture field; it reaches
  artifacts only through the digest-sealed corpus binding.
* **Reports verify against the presented corpus's binding** (not a hard-coded
  tuple): a 2.0 report fails on the 1.1.0 corpus and vice versa (executed);
  forged tokens/axes/digests/authority flags all fail (executed).
* **Production persistence and replay know exactly the V1 and 2.0 bindings.**
  The 2.1/FU3 binding is qualification-record identity only: no registered
  adapter owns it, the codec refuses a 2.1-bound payload, the live runtime
  pins 2.0, and the FU3 derivation module is referenced by no live path.
* **Scoring is binding-agnostic; identity is not.** Identical responses score
  identically under 1.0.0 and 1.1.0 (labels/payloads are byte-identical),
  while the record/report identities (binding, corpus digest, prompt digest)
  differ and cross-verify — the re-seal moved the binding, not the truth.
* **Authority posture unchanged:** `V2_AUTHORITY_QUALIFIED = False` at both
  pinned locations; reports grant nothing; the DRAFT policy is unapproved and
  inapplicable to 1.1.0 (F-4); no tier name appears in any 2.1 report.

---

## 10. Recommendation

**PASS** — the Q3-B5-P1 implementation is faithful to the frozen contracts and
the approved Q3-B3-FU2 (revision 2) design, with the two disclosed and
authorized deviations accounted for:

1. The authority axis of the 2.1 binding is the separately versioned FU3
   token (the Q3-B4 decision §6.2 / AD-Q3B4-5 correction of the design §9.1
   text) — correct, because FU3 preceded the 2.1 registration.
2. The RESPONSE FORMAT sentence is the frozen 2.0 wording — correct, because
   the draft marks that section `[2.0 unchanged]` (the Rev-2 code block's
   re-wording is the inconsistency; finding F-1).

All blocker-class audit checks pass: test preservation is exact (0 removed /
0 renamed / +108); the corpus re-seal is binding-only with 56/56 byte-identical
case documents and independently verified digests; every cross-version,
forged-binding, forged-token, and tampered-report negative case fails closed
in the actual code (source-proven where executed); the prompt is line-faithful
to the approved draft; the live runtime, persistence codec, replay registry,
and authority posture are untouched; and the full suite is green apart from
the documented, signature-identical, isolated-re-passed flake class.

**Required bounded corrections: none for the P1 implementation.** Recommended
(non-blocking) items: record the STATUS/PLAN documentation catch-up (F-3) with
the approval decision; carry F-4 into the Q3-C scope statement; optionally
annotate the historical design document's RESPONSE FORMAT inconsistency (F-1)
in the review record — without rewriting frozen or historical documents.

Live 2.1 requalification captures (both pinned models, including the deferred
fallback) remain Q3-C's scope per the approved phase plan; none were
performed in P1 or in this audit.

---

## Appendix A — The 108 new test nodes (exact, collected at the audited SHA)
  1. `tests/evaluation/semantic_v2/test_q3b5_p1_adversarial.py::TestAmbiguousPackagingCues::test_a_match_on_published_incompatible_packaging_is_critical`
  2. `tests/evaluation/semantic_v2/test_q3b5_p1_adversarial.py::TestAmbiguousPackagingCues::test_the_safe_definite_answer_on_the_absolute_rule_case`
  3. `tests/evaluation/semantic_v2/test_q3b5_p1_adversarial.py::TestGenericDescriptions::test_a_match_on_generic_overlap_is_detected_not_authoritative`
  4. `tests/evaluation/semantic_v2/test_q3b5_p1_adversarial.py::TestGenericDescriptions::test_the_in_set_match_pole_stays_defensible`
  5. `tests/evaluation/semantic_v2/test_q3b5_p1_adversarial.py::TestGenericDescriptions::test_the_uncertain_answer_on_generic_overlap_scores_correct`
  6. `tests/evaluation/semantic_v2/test_q3b5_p1_adversarial.py::TestInternalContradictions::test_the_2_0_false_no_match_shape_is_detected`
  7. `tests/evaluation/semantic_v2/test_q3b5_p1_adversarial.py::TestInternalContradictions::test_uncertain_naming_the_contradicted_dimension_scores_correct`
  8. `tests/evaluation/semantic_v2/test_q3b5_p1_adversarial.py::TestNearMissIdentifiers::test_a_match_on_the_alias_sales_unit_safety_case_is_critical`
  9. `tests/evaluation/semantic_v2/test_q3b5_p1_adversarial.py::TestNearMissIdentifiers::test_the_authority_resolved_near_miss_scores_correct`
 10. `tests/evaluation/semantic_v2/test_q3b5_p1_adversarial.py::TestNearMissIdentifiers::test_the_customer_retrieval_alias_confers_zero_authority`
 11. `tests/evaluation/semantic_v2/test_q3b5_p1_adversarial.py::TestOldVersionReplayIsolation::test_identical_responses_score_identically_on_both_versions`
 12. `tests/evaluation/semantic_v2/test_q3b5_p1_adversarial.py::TestOldVersionReplayIsolation::test_the_offline_2_1_pipeline_makes_no_network_call`
 13. `tests/evaluation/semantic_v2/test_q3b5_p1_adversarial.py::TestRunner2_1PromptFidelity::test_a_completed_2_1_run_evaluates_to_complete_no_authority`
 14. `tests/evaluation/semantic_v2/test_q3b5_p1_adversarial.py::TestRunner2_1PromptFidelity::test_contract_negatives_are_never_rendered_sent_or_recorded`
 15. `tests/evaluation/semantic_v2/test_q3b5_p1_adversarial.py::TestRunner2_1PromptFidelity::test_the_document_and_manifest_pin_the_2_1_identity`
 16. `tests/evaluation/semantic_v2/test_q3b5_p1_adversarial.py::TestRunner2_1PromptFidelity::test_the_runner_on_the_1_0_0_corpus_stays_byte_frozen_2_0`
 17. `tests/evaluation/semantic_v2/test_q3b5_p1_adversarial.py::TestRunner2_1PromptFidelity::test_the_runner_renders_the_byte_exact_2_1_prompt`
 18. `tests/evaluation/semantic_v2/test_q3b5_p1_adversarial.py::TestSilentMultiPack::test_a_silent_multi_pack_match_scores_correct_and_grants_nothing`
 19. `tests/evaluation/semantic_v2/test_q3b5_p1_adversarial.py::TestSilentMultiPack::test_the_recorded_absence_never_derives_proven_equivalent`
 20. `tests/evaluation/semantic_v2/test_q3b5_p1_binding_replay.py::TestBindingDriftPins::test_the_2_1_binding_is_drift_pinned`
 21. `tests/evaluation/semantic_v2/test_q3b5_p1_binding_replay.py::TestBindingDriftPins::test_the_frozen_2_0_binding_is_unchanged`
 22. `tests/evaluation/semantic_v2/test_q3b5_p1_binding_replay.py::TestCrossVersionCaptureRefusal::test_a_2_0_direct_capture_refused_against_the_1_1_0_corpus`
 23. `tests/evaluation/semantic_v2/test_q3b5_p1_binding_replay.py::TestCrossVersionCaptureRefusal::test_a_2_0_production_capture_refused_against_the_1_1_0_corpus`
 24. `tests/evaluation/semantic_v2/test_q3b5_p1_binding_replay.py::TestCrossVersionCaptureRefusal::test_a_2_1_direct_capture_loads_and_verifies_on_its_corpus`
 25. `tests/evaluation/semantic_v2/test_q3b5_p1_binding_replay.py::TestCrossVersionCaptureRefusal::test_a_2_1_direct_capture_refused_against_the_1_0_0_corpus`
 26. `tests/evaluation/semantic_v2/test_q3b5_p1_binding_replay.py::TestCrossVersionCaptureRefusal::test_an_unknown_prompt_axis_fails_closed_at_load`
 27. `tests/evaluation/semantic_v2/test_q3b5_p1_binding_replay.py::TestCrossVersionCaptureRefusal::test_the_production_route_loader_stays_2_0_only`
 28. `tests/evaluation/semantic_v2/test_q3b5_p1_binding_replay.py::TestCrossVersionCorpusRefusal::test_1_0_0_under_the_2_1_binding_fails_closed`
 29. `tests/evaluation/semantic_v2/test_q3b5_p1_binding_replay.py::TestCrossVersionCorpusRefusal::test_1_1_0_under_the_2_0_binding_fails_closed`
 30. `tests/evaluation/semantic_v2/test_q3b5_p1_binding_replay.py::TestCrossVersionCorpusRefusal::test_2_1_prompt_axis_with_the_frozen_token_fails_closed`
 31. `tests/evaluation/semantic_v2/test_q3b5_p1_binding_replay.py::TestCrossVersionCorpusRefusal::test_an_unknown_future_binding_fails_closed`
 32. `tests/evaluation/semantic_v2/test_q3b5_p1_binding_replay.py::TestCrossVersionReportRefusal::test_the_committed_2_0_baseline_refused_on_the_1_1_0_corpus`
 33. `tests/evaluation/semantic_v2/test_q3b5_p1_binding_replay.py::TestCrossVersionReportRefusal::test_the_committed_2_1_baseline_refused_on_the_1_0_0_corpus`
 34. `tests/evaluation/semantic_v2/test_q3b5_p1_binding_replay.py::TestProductionAdapterUnchanged::test_an_fu3_bound_payload_is_refused_by_the_production_codec`
 35. `tests/evaluation/semantic_v2/test_q3b5_p1_binding_replay.py::TestProductionAdapterUnchanged::test_the_codec_registry_still_knows_exactly_the_v1_and_2_0_bindings`
 36. `tests/evaluation/semantic_v2/test_q3b5_p1_binding_replay.py::TestProductionAdapterUnchanged::test_the_live_v2_record_type_still_pins_the_frozen_binding`
 37. `tests/evaluation/semantic_v2/test_q3b5_p1_binding_replay.py::TestSalesUnitBlindnessDocumentedProperty::test_the_frozen_derivation_is_structurally_sales_unit_blind`
 38. `tests/evaluation/semantic_v2/test_q3b5_p1_binding_replay.py::TestSalesUnitBlindnessDocumentedProperty::test_the_model_response_never_feeds_the_unit_authority`
 39. `tests/evaluation/semantic_v2/test_q3b5_p1_binding_replay.py::TestSalesUnitBlindnessDocumentedProperty::test_unavailable_never_derives_proven_equivalent`
 40. `tests/evaluation/semantic_v2/test_q3b5_p1_corpus_2_1.py::TestAntiManipulationOnReSeal::test_a_2_1_report_stays_bound_to_1_1_0`
 41. `tests/evaluation/semantic_v2/test_q3b5_p1_corpus_2_1.py::TestAntiManipulationOnReSeal::test_a_historical_2_0_report_stays_bound_to_1_0_0`
 42. `tests/evaluation/semantic_v2/test_q3b5_p1_corpus_2_1.py::TestAntiManipulationOnReSeal::test_a_sealed_label_change_on_1_1_0_changes_the_digest`
 43. `tests/evaluation/semantic_v2/test_q3b5_p1_corpus_2_1.py::TestAntiManipulationOnReSeal::test_an_unsealed_label_edit_on_1_1_0_is_rejected_on_load`
 44. `tests/evaluation/semantic_v2/test_q3b5_p1_corpus_2_1.py::TestBindingOnlyInvariance::test_all_56_case_digests_are_byte_identical`
 45. `tests/evaluation/semantic_v2/test_q3b5_p1_corpus_2_1.py::TestBindingOnlyInvariance::test_both_versions_load_against_their_own_bindings`
 46. `tests/evaluation/semantic_v2/test_q3b5_p1_corpus_2_1.py::TestBindingOnlyInvariance::test_every_case_document_is_zero_diff`
 47. `tests/evaluation/semantic_v2/test_q3b5_p1_corpus_2_1.py::TestBindingOnlyInvariance::test_only_the_authorized_metadata_moves`
 48. `tests/evaluation/semantic_v2/test_q3b5_p1_corpus_2_1.py::TestBindingOnlyInvariance::test_the_known_bindings_map_is_exact`
 49. `tests/evaluation/semantic_v2/test_q3b5_p1_corpus_2_1.py::TestCommittedReSeal::test_regeneration_from_the_source_is_byte_identical`
 50. `tests/evaluation/semantic_v2/test_q3b5_p1_corpus_2_1.py::TestCommittedReSeal::test_the_1_0_0_corpus_is_unchanged`
 51. `tests/evaluation/semantic_v2/test_q3b5_p1_corpus_2_1.py::TestCommittedReSeal::test_the_committed_1_1_0_corpus_loads`
 52. `tests/evaluation/semantic_v2/test_q3b5_p1_corpus_2_1.py::TestCommittedReSeal::test_the_manifest_is_reproducible`
 53. `tests/evaluation/semantic_v2/test_q3b5_p1_corpus_2_1.py::TestHarnessInvariance::test_the_2_0_context_gate_output_is_byte_identical`
 54. `tests/evaluation/semantic_v2/test_q3b5_p1_corpus_2_1.py::TestHarnessInvariance::test_the_2_1_baseline_contract_section_binds_the_2_1_identity`
 55. `tests/evaluation/semantic_v2/test_q3b5_p1_corpus_2_1.py::TestHarnessInvariance::test_the_2_1_context_gate_output`
 56. `tests/evaluation/semantic_v2/test_q3b5_p1_corpus_2_1.py::TestHarnessInvariance::test_the_draft_policy_artifact_is_byte_unchanged`
 57. `tests/evaluation/semantic_v2/test_q3b5_p1_corpus_2_1.py::TestHarnessInvariance::test_the_eight_gate_names_and_order_are_unchanged`
 58. `tests/evaluation/semantic_v2/test_q3b5_p1_corpus_2_1.py::TestHarnessInvariance::test_the_no_capture_2_1_baseline_is_reproducible_and_committed`
 59. `tests/evaluation/semantic_v2/test_q3b5_p1_corpus_2_1.py::TestHarnessInvariance::test_the_thirteen_contract_negative_rejections_are_identical`
 60. `tests/semantic/test_contract_v2_1.py::TestFrozen2_0Regression::test_the_2_1_text_is_separately_versioned`
 61. `tests/semantic/test_contract_v2_1.py::TestFrozen2_0Regression::test_the_real_frozen_2_0_system_prompt_digest_reproduces`
 62. `tests/semantic/test_contract_v2_1.py::TestNewClausePins::test_identifier_relationship_established_only_by`
 63. `tests/semantic/test_contract_v2_1.py::TestNewClausePins::test_no_chain_of_thought_surface`
 64. `tests/semantic/test_contract_v2_1.py::TestNewClausePins::test_sales_unit_unavailable_never_means_proven_equal`
 65. `tests/semantic/test_contract_v2_1.py::TestNewClausePins::test_the_absolute_rule_with_the_raw_cue_evidence_base`
 66. `tests/semantic/test_contract_v2_1.py::TestNewClausePins::test_the_authorized_relation_reason_code_tie`
 67. `tests/semantic/test_contract_v2_1.py::TestNewClausePins::test_the_condition_clarifying_sentence`
 68. `tests/semantic/test_contract_v2_1.py::TestNewClausePins::test_the_decision_rules_match_grounding_at_resolution`
 69. `tests/semantic/test_contract_v2_1.py::TestNewClausePins::test_the_distinctive_alignment_test`
 70. `tests/semantic/test_contract_v2_1.py::TestNewClausePins::test_the_identity_resolution_section`
 71. `tests/semantic/test_contract_v2_1.py::TestNewClausePins::test_the_internal_contradiction_rule`
 72. `tests/semantic/test_contract_v2_1.py::TestNewClausePins::test_the_no_match_never_on_exclusions`
 73. `tests/semantic/test_contract_v2_1.py::TestNewClausePins::test_the_requirement_line_trust_reading`
 74. `tests/semantic/test_contract_v2_1.py::TestNewClausePins::test_the_response_schema_is_the_frozen_seven_keys`
 75. `tests/semantic/test_contract_v2_1.py::TestNewClausePins::test_the_su_ent_critical_condition`
 76. `tests/semantic/test_contract_v2_1.py::TestNewClausePins::test_the_three_part_missing_critical_rule`
 77. `tests/semantic/test_contract_v2_1.py::TestNewClausePins::test_the_two_question_instruction_with_resolution_and_non_assertions`
 78. `tests/semantic/test_contract_v2_1.py::TestNewClausePins::test_u2n_contributes_no_resolution`
 79. `tests/semantic/test_contract_v2_1.py::TestNewClausePins::test_u3_partial_prefix_family_membership_limitations`
 80. `tests/semantic/test_contract_v2_1.py::TestNewClausePins::test_u4_generic_vs_distinctive_description`
 81. `tests/semantic/test_contract_v2_1.py::TestNewClausePins::test_u5_blocks_distinctive_alignment_and_authority_only`
 82. `tests/semantic/test_contract_v2_1.py::TestNewClausePins::test_what_a_match_asserts_precisely`
 83. `tests/semantic/test_contract_v2_1.py::TestNoConfidenceGuidance::test_confidence_lines_are_the_2_0_set_plus_exactly_one`
 84. `tests/semantic/test_contract_v2_1.py::TestNoConfidenceGuidance::test_no_confidence_mapping_instructions`
 85. `tests/semantic/test_contract_v2_1.py::TestNoDraftAnnotations::test_no_reviewer_markers_remain_in_the_prompt_text`
 86. `tests/semantic/test_contract_v2_1.py::TestPreserved2_0Sections::test_the_conflict_classes_section_gains_the_condition_sentence`
 87. `tests/semantic/test_contract_v2_1.py::TestPreserved2_0Sections::test_the_context_provenance_section_gains_two_appended_sentences`
 88. `tests/semantic/test_contract_v2_1.py::TestPreserved2_0Sections::test_the_determine_section_keeps_its_last_three_lines`
 89. `tests/semantic/test_contract_v2_1.py::TestPreserved2_0Sections::test_the_evidence_classes_section_differs_only_by_the_raw_cue_sentence`
 90. `tests/semantic/test_contract_v2_1.py::TestPreserved2_0Sections::test_the_new_sections_are_present`
 91. `tests/semantic/test_contract_v2_1.py::TestPreserved2_0Sections::test_the_not_asked_section_is_byte_identical`
 92. `tests/semantic/test_contract_v2_1.py::TestPreserved2_0Sections::test_the_product_evidence_section_is_byte_identical`
 93. `tests/semantic/test_contract_v2_1.py::TestPreserved2_0Sections::test_the_replaced_2_0_sections_are_gone`
 94. `tests/semantic/test_contract_v2_1.py::TestPreserved2_0Sections::test_the_response_format_section_gains_exactly_one_line`
 95. `tests/semantic/test_contract_v2_1.py::TestPreserved2_0Sections::test_the_task_section_is_byte_identical`
 96. `tests/semantic/test_contract_v2_1.py::TestUserTemplateDiff::test_the_builder_is_deterministic`
 97. `tests/semantic/test_contract_v2_1.py::TestUserTemplateDiff::test_the_rendered_diff_is_exactly_two_lines[different-sku]`
 98. `tests/semantic/test_contract_v2_1.py::TestUserTemplateDiff::test_the_rendered_diff_is_exactly_two_lines[near-miss-mpn]`
 99. `tests/semantic/test_contract_v2_1.py::TestUserTemplateDiff::test_the_rendered_diff_is_exactly_two_lines[provenances]`
100. `tests/semantic/test_contract_v2_1.py::TestUserTemplateDiff::test_the_rendered_diff_is_exactly_two_lines[title-mpn]`
101. `tests/semantic/test_contract_v2_1.py::TestUserTemplateDiff::test_the_rendering_is_deterministic`
102. `tests/semantic/test_contract_v2_1.py::TestVersionAndBinding::test_a_foreign_system_prompt_body_cannot_be_constructed`
103. `tests/semantic/test_contract_v2_1.py::TestVersionAndBinding::test_a_foreign_version_cannot_be_constructed`
104. `tests/semantic/test_contract_v2_1.py::TestVersionAndBinding::test_the_2_0_builder_stays_byte_frozen_per_case`
105. `tests/semantic/test_contract_v2_1.py::TestVersionAndBinding::test_the_2_1_binding_moves_only_prompt_and_authority_axes`
106. `tests/semantic/test_contract_v2_1.py::TestVersionAndBinding::test_the_2_1_builder_constructs_only_2_1`
107. `tests/semantic/test_contract_v2_1.py::TestVersionAndBinding::test_the_exact_prompt_version_is_pinned`
108. `tests/semantic/test_contract_v2_1.py::TestVersionAndBinding::test_the_frozen_2_0_axis_is_unchanged`

## Appendix B — Audit execution record and preservation statement

**Executed in this session (read-only + evidence collection only):**

* Per-file and node-level collection at the audited SHA and at the parent
  (parent via a temporary linked worktree at `e53d28c`, created with
  `git worktree add --detach`, removed with `git worktree remove` after use;
  the main worktree was never restored, reset, checked out, stashed, or
  cleaned).
* Independent corpus comparison scripts (case-by-case field diff, digest
  recomputation, manifest reproducibility) over `corpus_v1.json` and
  `corpus_2_1.json`.
* Direct execution of the forged-artifact rejections (six corpus variants,
  five capture variants, six report variants) against the production
  loaders/verifiers.
* The 43/43 user-template rendered-diff verification over both corpus
  versions.
* Prompt line-by-line comparison of the implemented `SYSTEM_PROMPT_V2_1`
  against the design Rev-2 §9.2 draft (annotations stripped) and against the
  frozen `SYSTEM_PROMPT_V2`; digest recomputation for both.
* Targeted suites (108 new nodes; 780 focused nodes) and the full suite
  (7142 nodes) with exact failure nodes and signatures preserved; isolated
  one-node-per-process re-runs of the 11 flaked nodes (11/11 re-passed;
  two required a second/third attempt under sustained load, with the
  identical `OSError [WinError 6]` Popen signature each time).
* `python manage.py check`, `python manage.py makemigrations --check
  --dry-run`, `git diff --check e53d28c..a383c61`.
* SHA-256 verification of the preserved live-capture evidence of record
  (document `d94f1ed8…`, manifest `46f818bb…`).

**Changed by this audit:** nothing in production code, tests, corpus,
reports, policy, or thresholds; no live capture; no deployment. The only
artifact created for commit is this document. Session scratch files created
during evidence collection were removed from the worktree before committing.

**Preservation of unrelated worktree artifacts:** the pre-existing tracked
modification `tmp_collection.txt` (line endings only), the seven historical
benchmark artifacts, the untracked design documents (Revisions 0/1 and the
integrated copy), the live-capture evidence, and all pre-existing `tmp_*`
session logs are byte-untouched. The second linked worktree
(`C:/dev/Product_Intelligence_recall_fix`, branch `pilot-ux-recall-fix-a`)
was not accessed or modified.
