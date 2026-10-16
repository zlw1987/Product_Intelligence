# Product Intelligence — Current Status



## Current state


**PRODUCT-INTEL.SEMANTIC-AUTHORITY-V2-Q3-C-C2 (Independently Labeled
Bundle Cases — the v1.0.0 DRAFT population + reviewer handoff)

— DRAFT ENDPOINT / INDEPENDENT REVIEW PENDING (the seal is NOT
authorized at this endpoint; see the gate status below)**

Bounded corpus-authoring phase on the authoritative starting SHA
`840f7c5d69e5f36bc8c82624d5bbe8079a438470` (the Q3-C-C1-FU2 endpoint;
baseline collection **7843, re-verified this session**), executing
design §9.4 of
`docs/PRODUCT_INTEL_Q3C_FU4_BUNDLE_AUTHORITY_QUALIFICATION_DESIGN.md`
(the C2 scope explicitly approved by the task directive). Bounded
scope ONLY: the populated family case-authoring source, the family
DRAFT governance artifacts (README / policy DRAFT / challenge log /
reviewer handoff), the C2 label-governance test suite, and the STATUS
/ PLAN records — **NO sealed corpus, NO qualification, NO evaluator,
NO capture, NO model call, NO policy approval, NO authority promotion,
NO pricing wiring, NO deployment, NO migration**
(`makemigrations --check --dry-run`: No changes detected;
`manage.py check`: 0 issues).

**The independent-review gate status (of record).** The task's
independent-review gate (task §5 / §11; design §8.2) could NOT be
staffed: no genuinely distinct independent label reviewer or
independent tester exists for this session; the corpus author did not
impersonate an independent reviewer; no reviewer identity, timestamp,
signature, or approval was invented. Per the task directive the phase
therefore delivers the **authoring evidence + the precise reviewer
handoff WITHOUT a falsely sealed corpus**: every label is in the
explicit DRAFT state (`reviewer: null`, `review_status: "DRAFT"`), the
family loader refuses that state by design (`REVIEW_STATUS_VALUES =
{"REVIEWED"}` — verified: the draft population fails
`verify_corpus_document` and the CLI `corpus-build` fails closed with
no artifact written), **NO `corpus_v1.json` / `manifest_v1.json` is
committed**, and **NO C2 completion is claimed**. The FU4 Bundle
authority program state of record remains UNAPPROVED / NOT EXECUTED.
The seal completes only when the two-identity review of design §8.2 is
genuinely staffed and recorded — `reviewer_handoff.md` names the
exact per-case work, the tester minimum (≥20% incl. ALL 37
adversarial D rows), the C2-F adjudications, and the byte-exact seal
procedure. ChatGPT independently reviews the committed draft, labels,
handoff, and tests before the seal (task final line).

**The declared population (design §5, complete — 96 DRAFT cases in
`product_intelligence/evaluation/bundle_authority/fixtures.py`).** All
48 matrix rows at their design minimums (93 Track A cases — floor 92)
+ 3 Track B-only model controls; Track B population 24 (21 A_B-shared
+ 3 B-only — floors 21 / 18 / 3); 88 SYNTHETIC (91.7% — floor 80%) +
8 RECORDED_FIXTURE (floor 5) + **ZERO REAL_MARKET** (v1.0.0 — C3's
separately gated acquisition); five product categories (memory_kit /
micron_ddr5 / nvme_ssd / workstation_gpu / networking_module — floor
4); every bounded vocabulary member the contract admits for a bundle
comparison projected (composition states ×5, quantity-axis states ×5,
refusal stages ×5, candidate bases incl. NONE, attestation sides +
states); positive / negative / ambiguous / contradictory /
missing-evidence / quantity / provenance / injection /
historical-binding / replay-refusal shapes all instantiated. The
CF-1..CF-5 interpretations of record are preserved, including the
frozen duplicate-constituent multiset semantics (A4: identical
duplicate phrasing is PROVEN-eligible via byte-identity; C2b: the
non-identical phrasing is T-DIFF-MATERIAL ⇒ CONTRADICTED over attested
clauses — the frozen grammar does not merge repeated tokens).

**Label independence (design §4.6 — observed, mechanically pinned).**
Every `expected` block, grounding citation, and rationale is a PURE
LITERAL grounded in the cited approved-design rows (P3 U-table /
ten-case matrix / §3.7 grammar / §3.8 attestation rules; Q3-B4 §4.1;
the Q3-C-D1 matrix rows; the frozen S2-A tier matrix; the R1 stage
semantics). **No FU4 derivation, R1 record-adapter, or model output
was read as an answer key.** The committed `fixtures.py` imports NO
research module (stronger than the §4.6(a) allowlist — the C2 suite
import-scans it); the evidence documents (channels, v3 composition
records, attestations, P2 extraction results, the R1 payloads) are
sealed JSON literals recorded through the frozen constructors / codec
at authoring time (constructor-is-validator; the untracked authoring
pass + its contract re-reading probes are recorded in the challenge
log and are NOT committed). The C1-FU2 F-9/F-10 prohibition is
honored: the C1 suite's `_expected_from_decision` / `_payload_record`
helpers were NOT reused as expected-label sources (only the document
assembly chain); the fixed independence attestation statement is
carried by every label; the anti-derivation token scan is re-asserted
case-by-case by the C2 suite.

**The C2-F findings — ten HELD cases (NOT bent, NOT omitted; pinned
exactly by the C2 suite).** Contract conflicts between valid approved
cases and the C1 loader / recorded-source ground, recorded
case-by-case in the challenge log + each case's rationale:
**C2-F1** (A-DELE U1/U3/U8 — FA4-DELE-001..003): the design row
expects the frozen FU3 PROVEN delegation with the bundle-axis audit
fields EXACTLY None (P3 D11 for non-bundle channels); the C1 loader's
PROVEN coherence pre-check (design §4.4 as implemented) requires a
satisfied bundle quantity axis + ESTABLISHED states for ANY PROVEN
expectation — incompatible; the loader refuses the design-grounded
label (verified). Resolution owner: a design revision (scope the §4.4
rule to bundle-channel cases) or the C1 schema correction — never a
bent label. **C2-F2a** (D3-ii — FA4-ADV-006): the design row names
PRESENTATION_GATE for content-identical channels with different
embedded originals, but the observable defect over the sealed
documents is the embedded-vs-recorded-result mismatch (a
case-document-integrity observation — CORPUS_INTEGRITY), because the
channel-level gate steps cannot fire over content-identical channels
(the documented P5 R-5 bound / risk R-C1-10); both readings recorded
for the reviewer's adjudication. **C2-F2b** (D16-iii — FA4-ADV-034):
the FU3-token derivation presentation is an EXECUTION-level
contract-misuse refusal (P3 §5.4); over sound sealed FU4 documents no
constructor / codec / case-document observation fires, so the labeled
CONSTRUCTION stage is incoherent per the family's stage rule — the E1
adversarial re-execution is the observation point the design names.
**C2-F3** (A1-ii — FA4-PROV-002): no committed recorded source
publishes bundle contents with a versioned completeness marker (design
§2.5 verified) — the recorded 0034-shape context carries the clause
WITHOUT the marker and its title cannot form the family's identity
context (no candidate MPN token); the row's RECORDED_FIXTURE variant
is unsealable at v1.0.0. **C2-F5** (D11-ii — FA4-ADV-023): the
recorded Micron 7500 catalog grounds the exact-identifier family shape
(the one-character-different part numbers) but publishes no bundle
contents, so the attested-CONTRADICTED expectation's clauses cannot be
span-grounded without manufacturing recorded content. **C2-F6**
(B6-ii/iii + C6 — FA4-UNPR-011/012, FA4-CONTR-011): the row's
REQUIRED recorded extraction result (AMBIGUOUS_CUE / CONTRADICTED_
CUES) cannot be sealed with a DERIVED outcome — the family's
basis-coherence rule fires a case-document-mirror observation for any
basis over (no candidate record + recorded result); authored with the
documented lighter shape (the canonical recorded-absence channel + the
sealed published text) — the U0 expectation is re-derivable over it,
the evidence gap is recorded, not papered over (C6 is the CF-1
documented-conflict row: the frozen P2→FU4 chain records UNPROVEN
over the recorded absence; the task matrix's CONTRADICTED placement is
overridden by the frozen contract, O-3). **Review readiness (the C2
suite's case-by-case dry-run over the REAL family loader, with a
test-local reviewer fill — a decoder fixture, never a committed
review claim): 89 of 96 cases LOAD with the two-identity review
fields filled (the 86 non-held + the 3 C2-F6 lighter shapes); the 7
loader-held cases fail for the recorded reason; the seal is thus
mechanically achievable the moment the genuine review is recorded.**

**Deliverables (design §9.4 file set, draft-state).** (1)
`fixtures.py` populated (the DRAFT population — byte-pinned by the C2
suite's source-digest node: any modified expected label / forged
reviewer field / stale digest moves the pin). (2)
`evaluation/fu4_bundle_authority_qualification/`: `README.md` (the
family statement + the draft state of record);
`policy/qualification_policy_draft_1.json` (**DRAFT status only** —
the design §7.2 threshold vocabulary with the DRAFT values,
`approved: false`; the existing semantic-family DRAFT policy is
UNCHANGED, UNCOPIED, UNEXTENDED — the F-4 lineage); `challenge_log.md`
(the author pass per case — grounding citation + re-derivation
statement; the C2-F findings; the agreements / disagreements /
corrections log incl. the D17-i stage-reading correction (CONSTRUCTION
→ the stage-semantics (iii) CODEC_DECODE reading, both recorded) and
the D6 surface deviation (BOTH → DERIVATION for the corpus-level
defects, recorded); every reviewer cell PENDING);
`reviewer_handoff.md` (the precise per-case worklist — all 96 case
IDs; the tester minimum; the C2-F adjudications; the exact seal
procedure). (3) `corpus_v1.json` / `manifest_v1.json`: **ABSENT by
design at this endpoint** (the seal gate — pinned by both the C1
corrected node and the C2 suite). (4) `sources/`: ABSENT (zero
REAL_MARKET cases). (5) NEW
`tests/evaluation/bundle_authority/test_q3c_c2_label_governance.py`
(**200 nodes**). (6) **Recorded in-place corrections of FIVE C1
nodes** whose phase-state pins the C2 endpoint legitimately moves
(house precedent R2-FU1 / C1-FU2; intent preserved or strengthened;
no rename / skip / xfail / deselect / weakening):
`test_zero_case_corpus_builds_seals_loads_and_regenerates` (the 0-case
builder property over the EXPLICIT empty case set — the declared set
is now the 96-case DRAFT population); `test_cli_corpus_build_writes_
the_seal` (STRENGTHENED: the CLI corpus-build over the DRAFT
population must FAIL CLOSED with the bounded error naming the
unreviewed label state, and must write NO artifacts — a seal command
that wrote over an unreviewed population would be a false seal);
`test_cli_corpus_digest_and_manifest_verify` +
`test_cli_corpus_digest_refuses_tampered_seal` (the round trip over
the explicit 0-case seal — the CLI build path is fail-closed at this
endpoint); `test_no_corpus_artifact_is_committed_at_c1` (TIGHTENED:
the family directory may now exist with the non-seal governance
artifacts, and the SEALED corpus / manifest must be ABSENT — pinning
"no false seal").

**Tests / validation (exact).** 200 NEW C2 nodes: matrix coverage +
the 48 row minimums (parameterized), the track A/B populations +
overlap (93 / 24 / 21 / 3), the evidence-kind composition (88 / 8 / 0;
91.7% / floor 80% / 5 / 0), the category floor (5 / floor 4), the
bounded-vocabulary projection (states ×5, axes ×5, stages ×5, bases,
attestation sides + states), the gate-denominator tag populations, the
draft state (every label DRAFT + reviewer null + the recorded author
identity / instant), the seal-gate closure (no seal artifact; the
loader refuses the draft population; the CLI fails closed), the
case-by-case review-readiness dry-run (89 loader-passes parameterized
+ the 7 loader-holds pinned exactly + the 3 evidence-holds pinned),
the label governance (the fixed attestation; the anti-derivation scan
case-by-case; the grounding-citation source rule; the provenance-row
coherence; the A_B note rule; the author≠reviewer gate over a forged
self-review; the missing-review refusal), the challenge-log + handoff
completeness (every case ID; every finding; the reviewer column all
PENDING; the tester scope incl. all 37 D rows), the integrity pins
(the fixtures source digest; a modified expected label moves the case
digest; the tampered sealed case fails the loader at the case digest;
the byte-stable corpus build; the missing-matrix-row gate; the forged-
review-metadata gate — including the recorded caveat that the LOADER
accepts a forged two-identity state, which is exactly why the
qualification gate adds the recorded-registry + review-record checks,
and why a matching digest never authenticates a human review), the
authoring import prohibition (no research module in `fixtures.py`;
the import set is exactly the family + stdlib allowlist; no forbidden
module name in the source; the family package surface is pinned to the
C1 file set — no evaluator surface exists), the historical
preservation (the five semantic-family artifacts by file digest + the
1.2.0 seal by its inner digests; the C1 family package files
corpus.py / cli.py / __init__.py byte-frozen; the C0-pinned FU4 module
+ R1 adapter content identity; the four family governance artifacts
byte-pinned), and the DRAFT-only policy state (status / approval /
applicability / the §7.2 vocabulary + zero-tolerance invariants; the
semantic-family DRAFT policy unchanged). The C1 suite keeps **250
nodes** (the five recorded corrections in place — no node deleted /
renamed / skipped / xfailed / deselected). **Targeted batch: C1 250 +
C2 200 + C0 2 + FU4 217 + R1 38 + R2 35 = 742 passed, 0 failed, exit
0.** **Boundary guards (research / web / providers / evaluation): 595
passed, exit 0.** **Full suite over the 8043 collection — four
recorded attempts** (the documented load-sensitive clean-interpreter
subprocess guard flake class — every failure at `subprocess.Popen` /
`subprocess._get_handles` BEFORE any project code runs; zero assertion
failures; the fixed eleven-node allowlist UNCHANGED): run 2 (evidence
`tmp_c2_full_junit.xml`) — 1 failed
(`tests/domain/test_domain_boundaries.py::test_domain_imports_without_
django_network_or_llm_dependencies` — a fixed allowlist member;
re-passed isolated); run 3 (evidence `tmp_c2_full_run3.txt`) — 2
failed (the same allowlist member + `tests/evaluation/
test_evaluation_boundaries.py::test_loading_the_corpus_imports_no_
framework_or_provider` — the documented WinError-6 pair; re-passed
isolated); run 4 (evidence `tmp_c2_full_run4.txt`) — exit 0, 8043
executed (the environment dropped the terminal summary line in this
capture — the junit-less run); **run 5 (evidence `tmp_c2_full_run5.
txt` + `tmp_c2_full_junit2.xml`) — FULL GREEN: 8043 executed (8082
junit test cases incl. the 39 subtests), 0 failed, 0 errors, 0
skipped, PYTEST_EXIT=0**. An isolated retry does not convert a failed
full-suite run into a full green result: the recorded full-green
result is run 5. **Collection delta (against the re-verified 7843
baseline): 7843 -> 8043 (+200, all in the NEW C2 suite; 0 removed / 0
renamed; no other file changed its node count).** `python manage.py
check`: System check identified no issues (0 silenced). `python
manage.py makemigrations --check --dry-run`: No changes detected.

**Invariance (this phase).** No frozen authority implementation
change (the C0-pinned `semantic_authority_fu4.py` +
`semantic_decision_v2_fu4.py` content-verified by the C2 suite; the
C1-pinned family package files corpus.py / cli.py / __init__.py
byte-frozen); no production integration; no model capture or model
call (zero-live by construction — the authoring probes read the
frozen contract's stated behavior for cited rows, never the
implementation's output as an answer key); no live network retrieval;
no real-market case acquisition; no Track A or B evaluation (the
evaluator does not exist — the family package surface is pinned to
the C1 file set); no policy approval (the family policy is DRAFT
only); no qualification marker change; no pricing change; no database
migration; no C3/E1/E2/P1/Q1/W1 work. The historical semantic corpus
/ manifests / DRAFT policy are byte-pinned by both suites. The
unrelated worktree artifacts are preserved. **C2 grants NO
qualification at this endpoint**: the corpus is NOT sealed, no Bundle
authority case is independently qualified, and the state of record
remains UNAPPROVED / NOT EXECUTED.

**Next.** The genuine two-identity independent review per
`reviewer_handoff.md` (the independent label reviewer re-derives every
case from the citations; the independent tester re-derives ≥20% incl.
ALL 37 D rows; the C2-F findings are adjudicated). ChatGPT
independently reviews the actual GitHub diff, corpus, labels,
reviewer record, and tests before approving C2. The seal (the v1.0.0
`corpus_v1.json` + `manifest_v1.json` from the reviewed
`fixtures.py`, byte-for-byte) is a C2-completion step under that
review — or a recorded correction phase if the review finds a label
defect. Do not start C3 or E1.

**PRODUCT-INTEL.SEMANTIC-AUTHORITY-V2-Q3-C-C1-FU2 (Provenance Binding
& Integrity Hardening)

— IMPLEMENTED / PENDING CHATGPT INDEPENDENT REVIEW**

Bounded CORRECTIVE implementation on the authoritative starting SHA
`36ae43e9d268a45d7ea7df1b42125944ca3cbafb` (the Q3-C-C1 endpoint;
baseline collection **7793, re-verified this session**), correcting
the confirmed C1 security / integrity gaps identified by the C1-FU1
investigation (findings F-1..F-10, decision record AD-085 / PLAN
§26.43). Corrective scope ONLY: the family corpus validator, its
integrity tests, minimal necessary fixtures, and the STATUS / PLAN
records — NO qualification cases, NO labels, NO evaluator, NO
capture, NO model call, NO policy, NO authority promotion, NO
pricing wiring, NO deployment, NO migration (`makemigrations --check
--dry-run`: No changes detected; `manage.py check`: 0 issues).

**F-1 — the mandatory provenance binding.** The family cross-document
validator now binds the recorded V2 case document
(`recorded_case.v2_case_document`) to the corresponding sealed source
blocks, field by field, over the ACTUAL canonical document keys (no
cross-name equivalence assumed): candidate raw title <-> sealed
title_text (exact codepoint equality or explicit joint absence, all
evidence kinds); candidate source URL <-> sealed source_url (exact
equality; RECORDED_FIXTURE / REAL_MARKET only — for SYNTHETIC the
sealed block carries no URL and no authoritative counterpart exists:
documented limitation, no manufactured comparison); candidate MPN
field / SKU / offer URL / raw specification text <-> the name-exact
sealed structured_fields keys (key present -> recorded non-null +
exactly equal; key absent -> recorded null — the recorded case never
carries text the sealed source never published); target MPN / target
raw description <-> the name-exact sealed target structured_fields
keys ONLY when the block records them (the caller-published request
anchor has no counterpart otherwise — documented limitation).
Eight deterministic, named observations at the case-document-
integrity layer: `CASEDOC_CANDIDATE_TITLE` / `_SOURCE_URL` /
`_SPEC_TEXT` / `_MPN_FIELD` / `_SKU` / `_OFFER_URL`,
`CASEDOC_TARGET_MPN` / `_DESCRIPTION`. A mismatch is rejected for a
sound DERIVED case; REFUSED / NON_CONSTRUCTIBLE cases remain under
the existing sealed-raw stage-coherence contract (the mismatch is
CORPUS_INTEGRITY-grounding and incoherent under PRESENTATION_GATE /
REPLAY_AGREEMENT / CONSTRUCTION labels — the CASE_DOCUMENT vs
presentation-gate distinction preserved). The binding proves INTERNAL
provenance consistency (L1/L2) only — not source authenticity (L3),
no trust promotion.

**F-2 + archive filesystem safety.** A REAL_MARKET archive must cite
its OWN case's `sources/<case_id>/` directory (decode-level, the
approved per-case layout). At load, every cited archive is RESOLVED
(symlinks followed) and must stay inside the resolved repository
root — archive reads cannot escape the authorized source root
through symlink traversal; REAL_MARKET archives must additionally
resolve inside their own case's sources directory (case A's archive
reference must not resolve to case B's source directory). Missing
paths keep the established bounded "missing archive" error; path-
resolution errors are bounded; the declared-digest verification is
unchanged (run over the resolved file); error reporting names the
case, side, cited path, and resolved path (deterministic).

**F-3 / F-4 — duplicate cleanup.** The duplicate `_SOURCE_BLOCK_KEYS`
definition (family validator) and the duplicated PLAN §26.42
paragraph removed; the surviving definition / wording preserved
verbatim; no functional change (the C1 suite + targeted batch pass
unmodified except the two minimal fixture corrections below).

**F-5 — bounded errors.** A corpus file that is not at least three
path components below its repository root is now the established
bounded corpus error (DIGEST_INTEGRITY stage), never an unhandled
`IndexError`; path-resolution failures are bounded the same way.

**F-6 / F-7 — committed regression coverage.** Valid (1 / 2) and
invalid label revisions (unknown case id; reason class unknown / null
/ lowercase); nonsequential revision numbers (gap at start / gap in
middle / duplicate); revision tamper over a stale manifest (the
corpus loads under its own recomputed digest; the stale manifest's
corpus_digest check fails); duplicate JSON keys (a hidden last-wins
duplicate breaks the canonical byte contract); NaN and Infinity
(the strict decode refuses the float value); mixed line endings
(rejected); the valid EXACT CRLF expansion (loads — the documented
autocrlf state); noncanonical manifest bytes (rejected); Unicode
codepoint distinctions (raw UTF-8 bytes rejected at file level; a
visually identical Cyrillic codepoint in the recorded title rejected
at the binding level). All rows exercise the actual public
loader / validator entry points.

**F-8 — the execution boundary.** Committed rows document the
existing behavior: sound documents labeled REFUSED@PRESENTATION_GATE
(and REFUSED@REPLAY_AGREEMENT) load WITHOUT the decoder invoking the
frozen authority derivation / replay (monkeypatched sentinel probe
over every label-determining entry point). Stage coherence over sound
documents proves ONLY that the sealed shapes are self-consistent
below the construction layer; it does NOT prove the actual authority
outcome — actual derivation / replay correctness remains an E1
responsibility.

**F-9 / F-10 — the trust boundary.** The distinction between a valid
schema, internally consistent sealed data, authentic published
evidence, independent human review, and physical product truth is
maintained; no automatic trust promotion; no qualification cases
created. WARNING OF RECORD: the test-local expected values derived
from FU4 output (the C1 suite's `_expected_from_decision` /
`_payload_record` helpers and every helper that reads a frozen FU4 /
R1 output) are SYNTHETIC DECODER FIXTURES ONLY — they are NOT
independently labeled expected outcomes, and C2 authoring and
labeling tools MUST NOT reuse those helpers (or their outputs) as
independent expected-label sources; the C2 label is established under
the design §4.6 / 8.2 two-identity workflow from the recorded source
content + the approved design rows.

**Minimal necessary fixture corrections (of record; the permitted
fixture scope).** (1) The recorded-fixture helper's candidate block
now cites the case's OWN source URL — the name-authoritative
counterpart the F-1 binding requires (it previously cited a
different recorded page on the candidate side). (2) `_extraction_case`
now builds the recorded V2 case from the SAME extended-title
observation its sealed candidate block records — it previously sealed
a block title the recorded case never carried, a mismatch the F-1
binding correctly rejects. No test expectation was weakened; both
fixtures are now strictly more coherent with the sealed documents.

**Tests.** 50 NEW nodes in `tests/evaluation/bundle_authority/
test_q3c_c1_corpus_integrity.py` (the C1 suite is now 250):
TestProvenanceBinding (21 — the substitution / nullable-field /
structured-mapping / target-anchor / codepoint rows over re-sealed
corpora + the three sealed-raw stage-coherence rows),
TestArchiveAssociationAndSafety (11 — the per-case layout, the
path-shape refusals incl. `..` / absolute / Windows drive /
backslash, the bounded shallow path, the symlink escape outside the
root, the symlink cross-case association), TestLabelRevision
Regression (10), TestLoaderByteContractRegression (7),
TestExecutionBoundaryRefusals (2). No test deleted, renamed, skipped,
xfailed, deselected, ignored, or weakened; the fixed eleven-node
Windows flake allowlist UNCHANGED.

**Validation (exact).** Focused C1 suite: **250 passed, 0 failed**.
Targeted batch (boundary guards + 217-node FU4 + 38-node R1 +
35-node R2 registration + 2-node C0 pins): all passed, exit 0 (one
allowlist member flaked under load with the documented signature and
re-passed isolated). Full semantic batch (623 nodes): all passed,
exit 0. Full suite over the 7843 collection, SIX recorded runs (the
documented load-sensitive clean-interpreter subprocess guard flake
class — every failure at `subprocess.Popen` / `subprocess.
_get_handles` BEFORE any project code runs; zero assertion failures;
the fixed eleven-node allowlist UNCHANGED): run 1 — 7841 passed, 2
failed (two allowlist members, re-passed isolated); run 2 — 7833
passed, 10 failed (allowlist members, re-passed isolated); run 3 —
7832 passed, 11 failed — the SAME 11 fixed-allowlist nodes exactly
(node-level list in `tmp_fu2_run3_failed.txt`; signatures: 9x
`OSError [WinError 50] The request is not supported` at
`subprocess._get_handles` + 2x `OSError [WinError 6] The handle is
invalid` at `subprocess.Popen` — the load-correlated OS-error-code
variant of the documented class, confirmed against the allowlist and
re-passing isolated, NOT an unfamiliar failure); run 4 — 7832
passed, 11 failed — the SAME 11 nodes, same signature mix;
run 5 — 7841 passed, 2 failed (two allowlist members); run 6 (evidence
`tmp_fu2_full_run6.txt`) — **7843 collected, 7843 passed, 0 failed,
exit 0** (the recorded full-green result), 0 skipped / 0 xfailed / 0
deselected. An isolated retry does not convert a failed full-suite
run into a full green result: the recorded full-green result is run
6. Collection delta (against the re-verified 7793 baseline): 7793 ->
7843 (**+50**, all in the C1 suite; **0 removed / 0 renamed**; no
other file changed its node count). `python manage.py check`: System
check identified no issues (0 silenced). `python manage.py
makemigrations --check --dry-run`: No changes detected.

**Invariance (this phase).** No frozen research code, no semantic
authority behavior, no pricing behavior, no corpus or manifest, no
qualification policy, no prompt text, no authority flag, no database
schema changed: `git diff` against the starting SHA is confined to
`product_intelligence/evaluation/bundle_authority/corpus.py`,
`tests/evaluation/bundle_authority/test_q3c_c1_corpus_integrity.py`,
and the STATUS / PLAN records. No qualification label was created or
revised. No model capture occurred (zero-live by construction). C1-
FU2 grants NO qualification: the FU4 Bundle authority program state
of record remains UNAPPROVED / NOT EXECUTED — the corpus is NOT
sealed, no Bundle authority case is independently qualified, and C2
(the independently labeled v1.0.0 seal) starts only under its own
explicit approval (design §9.4) with the two-identity workflow
staffed. The unrelated worktree artifacts are preserved.

**Next.** ChatGPT's independent review of the committed C1-FU2 GitHub
diff decides whether C1 can be frozen. C2 is NOT started.


**PRODUCT-INTEL.SEMANTIC-AUTHORITY-V2-Q3-C-C1 (FU4 Bundle Authority
Qualification — Corpus Schema & Integrity Validator)

— IMPLEMENTED / PENDING CHATGPT INDEPENDENT REVIEW**

Bounded implementation on the authoritative starting SHA
`36d4e8b9716e18295abfcb8e5d8167ad320bd6df` (the Q3-C-C0 endpoint;
baseline collection **7576**, re-verified this session), executing
design §9.3 of
`docs/PRODUCT_INTEL_Q3C_FU4_BUNDLE_AUTHORITY_QUALIFICATION_DESIGN.md`
(the C1 scope explicitly approved by the task directive). Schema +
validator only: **NO qualification cases, NO labels, NO evaluator, NO
capture, NO model call, NO policy, NO authority promotion, NO pricing
wiring, NO deployment, NO migration** (`makemigrations --check
--dry-run`: No changes detected; `manage.py check`: 0 issues).

**What C1 implements (of record).** The strictly offline FU4 Bundle
authority qualification corpus family — the schema, the strict
decoder, the manifest integrity validator, the builder skeleton, and
the offline CLI. The family is a SEPARATE corpus identity (`PI-FU4-
BUNDLE-AUTHORITY-QUALIFICATION`, first version `1.0.0`, schema 1),
sealed under the registered FU4 binding
tuple(`V2_FU4_CONTRACT_BINDING`) — the semantic family
(`PI-SEMANTIC-V2-QUALIFICATION` 1.0.0–1.2.0) is NOT extended and NOT
touched. The sealed corpus loads ONLY under the exact family seal
registry (cross-family / cross-binding / cross-version refusal).

**The exact files (design §9.3 scope).**

* NEW `product_intelligence/evaluation/bundle_authority/__init__.py`
  (family marker; research-independent).
* NEW `product_intelligence/evaluation/bundle_authority/corpus.py`
  (the family loader: exact-key-set strict decode of the §4.4
  per-case document + the corpus document; the seal registry; the
  per-case / corpus / manifest digests; the manifest builder /
  verifier; the §4.4 / §4.6 label-governance checks — author ≠
  reviewer, `REVIEWED` status, the fixed independence attestation,
  the anti-derivation label-text scan, the expected-axis coherence
  pre-checks; the evidence construction through the REAL frozen
  constructors with canonical round-trip identity (constructor-is-
  validator); the RECORD-surface payload decode through the REAL
  universal codec; the stable canonical serialization check; the
  declared source-file digest re-verification).
* NEW `product_intelligence/evaluation/bundle_authority/fixtures.py`
  (the auditable case-authoring source: the EMPTY declared case set +
  the corpus-document builder skeleton; research-independent at C1).
* NEW `product_intelligence/evaluation/bundle_authority/cli.py`
  (`corpus-build` / `corpus-digest` / `corpus-manifest` — offline
  only; explicit `--created-utc`, no clock read).
* NEW `tests/evaluation/bundle_authority/` (`__init__.py` +
  `test_q3c_c1_corpus_integrity.py`, 200 nodes — the focused C1
  adversarial suite; minimal synthetic fixtures only, test-local,
  never a qualification seal).
* AMENDED IN PLACE (strictly additive, recorded decision — see
  "Boundary-guard decision of record" below):
  `tests/research/test_research_identity_boundaries.py` (+103/-4:
  the `BUNDLE_AUTHORITY_QUALIFICATION_RESEARCH_EXCEPTION` exact-
  allowlist entry for `bundle_authority/corpus.py` only, the union
  update, the new `test_bundle_authority_exception_is_an_exact_
  allowlist` node, the docstring record).
* NO other file touched: the byte-pinned semantic_v2 harness, the
  three committed semantic corpus seals + manifests + the DRAFT
  policy, the R1 / R2 / C0 pin tables, the FU4 module, the R1
  adapter, the prompts, the live runtime, the pricing surfaces — all
  byte-identical to the starting SHA (`git diff` over
  `product_intelligence/` + `evaluation/` + `tests/evaluation/
  semantic_v2/` empty against the starting SHA; the C1 suite
  re-pins the five A1-pinned semantic artifacts by file digest and
  the 1.2.0 seal by its inner document digests).

**Supported integrity guarantees (what a matching digest proves).**
Internal structural integrity only (design §3.2 L1): the document is
exactly the bytes its digests cover (per-case digest over the case
document minus `case_digest`; corpus digest over the full state view
including label revisions — case reordering without re-sealing is
detected; manifest digest over the manifest minus `manifest_digest`),
in the stable canonical serialization (sorted keys / indent 1 / ASCII
/ trailing newline; the documented autocrlf working-tree expansion is
the only tolerated byte variant), under the exact family identity /
version / binding seal, with every bounded vocabulary drift-pinned to
the frozen research exports, every evidence document decoded through
the REAL frozen constructors (canonical round-trip identity), the
RECORD-surface payload decoded through the REAL universal codec, the
label governance enforced (§4.6: two distinct identities, `REVIEWED`,
the fixed independence attestation, the anti-derivation scan, the
expected-axis coherence pre-checks), and every cited source archive
re-verified against its declared digest. **Explicit authenticity
limitations (never claimed):** a valid digest does NOT establish that
the publisher actually made a claim (L3 — only the recording act's own
integrity is verifiable), does NOT establish that a published
completeness statement is physically complete (L4 — it remains a
published claim), and does NOT establish that a physical bundle
contains the listed components (L5 — reserved to human verification).
No cryptographic source-authentication capability exists or is
invented by C1.

**Sealed-raw defect scoping (the documented rule).** Cases labeled
`REFUSED` / `NON_CONSTRUCTIBLE` carry the sealed invalid documents of
the adversarial matrix. The loader runs the real constructors / codec
/ family checks over every evidence document WITHOUT executing the
derivation, classifies each observation by layer, and requires the
labeled refusal stage to be coherent with what is observable:
`CORPUS_INTEGRITY` requires a case-document-integrity observation;
`CONSTRUCTION` / `CODEC_DECODE` require a constructor- / codec-level
observation (a label naming a construction-stage defect over fully
sound documents is an incoherent label — a corpus-integrity failure,
never a test failure); `PRESENTATION_GATE` / `REPLAY_AGREEMENT`
require the documents to be exactly the self-consistent shapes (no
constructor- / codec- / case-document-integrity observation may fire).
A sound (`DERIVED`) case must carry zero observations of any layer.

**Boundary-guard decision of record (the one file outside §9.3's
literal list).** The frozen architecture guard
(`tests/research/test_research_identity_boundaries.py`) requires a
recorded, strictly-additive in-place allowlist extension for any new
evaluation→research importer (its own documented mechanism;
precedents A1-FU2 / Q3-A / Q3-A-FU1; the file is NOT content-pinned —
verified by digest grep over `tests/` + `docs/`). C1 extends it for
EXACTLY `bundle_authority/corpus.py` (the family loader requires the
real frozen constructors / codec / drift-pinned research public
surface — design §9.3's own import-scan acceptance); every other
family module stays research-independent (pinned by the C1 suite),
and the C1 import-scan suite additionally locks the exact research
symbol allowlist of `corpus.py` + the label-determining import
prohibition (no `derive_*` authority derivation, no replay, no
construction entry point, no semantic_v2 harness module, no execution
/ runs / web / providers / Django). This decision is recorded here and
in PLAN §26.42 / AD-084 for the independent reviewer; if the review
disagrees, the bounded correction is this single test file.

**Interpretations of record (design-internal, not conflicts with the
frozen implementation).** (1) D1 §2.4 names the harness
`decode_match_case` as the "public entry the new family reuses
read-only" while §9.3's mechanically verifiable import-scan acceptance
forbids semantic_v2 harness imports; resolved by §4.4's own
"decode_match_case **/ constructor**" wording + §3.3 ("reuses
patterns and the frozen research public API, never the pinned harness
files"): the family implements the strict V2 case-document decode
in-package with the REAL frozen `SemanticMatchCaseV2` constructor as
final arbiter + canonical round-trip identity. (2) §4.2(f)/(g) over
sealed-raw defect documents (matrix rows B8/B9/D14/D15/D16 are
documents the constructors / codec MUST refuse) is scoped by the
stage-coherence rule above — the loader verifies the sealed documents
are consistent with the labeled observation point without executing
the derivation. (3) The family finalizes the design's O-1 items:
`challenge_tags` = the five tags the design names; the refusal
`error_type` bounded set = {CONSTRUCTOR, CODEC, PRESENTATION, REPLAY}
per stage; `surface` = explicit null for track-B cases; the corpus
digest covers `label_revisions` (per §4.2's state view — the semantic
family's exclusion of `label_revisions` is NOT adopted); `track A_B`
cases carry the `semantic_identity_note`.

**Tests.** 200 NEW nodes in `tests/evaluation/bundle_authority/
test_q3c_c1_corpus_integrity.py` (the focused C1 adversarial suite):
the structural-integrity matrix (missing / extra keys, wrong types,
invalid enums, case-id grammar, duplicate ids, cross-family /
cross-binding / cross-version / schema-version seal refusal, track /
surface coherence); the digest-integrity matrix (sealed-byte case /
label / reviewer / source tamper, corpus-digest / manifest tamper
class incl. statement / lineage / case-count / projection / binding,
case reordering, non-canonical serialization); the provenance-
integrity matrix (candidate-evidence-on-target and the reverse,
cross-listing substitution sealed-raw + sound-label refusal, missing
original extraction, extraction input-digest mismatch, missing
completeness attestation, model claim disguised as publisher
evidence, forged reviewer association, quantity-attestation side /
axis misuse); the sealed-raw stage-coherence rows (B8 / D14 /
D15-i / D15-ii / D16 / D6-ii shapes load under their labels; the
incoherent-label shapes are refused — CONSTRUCTION over sound
documents, CORPUS_INTEGRITY without a defect, PRESENTATION_GATE over
a constructor defect, CODEC_DECODE over the derivation surface);
the label-governance rows (two identities, `REVIEWED`, fixed
attestation, anti-derivation token scan, the expected-axis coherence
pre-checks incl. no-implicit-PROVEN / no-pricing-default / ceiling-
keying / note-track rules); the authority-separation proofs (the
exact research symbol allowlist, the forbidden label-determining
surface scan, the monkeypatched no-execution probe, least-privilege
research-independence of the non-loader family modules); the
vocabulary drift pins (family sets == frozen exports, incl. the
evidence-kind equality against the semantic family's set); the
source-archive digest consistency (verify / substituted file /
missing file / the per-evidence-kind source-block rules); the
historical-preservation pins (the five A1-pinned semantic artifacts
by file digest + the 1.2.0 seal by its inner document digests);
and the empty-seal demonstration (the 0-case corpus builds, seals,
loads, and regenerates byte-for-byte; the CLI round trip).
1 NEW guard node in the amended boundary file
(`test_bundle_authority_exception_is_an_exact_allowlist`). No test
deleted, renamed, skipped, xfailed, deselected, ignored, or
weakened; the fixed eleven-node Windows flake allowlist UNCHANGED.

**Validation (exact).** Focused C1 suite: **200 passed, 0 failed**
(3.78s). Targeted batch (boundary guards + the 217-node FU4 contract
suite + the 38-node R1 suite + the 35-node R2 registration suite +
the 2-node C0 pin suite): **all passed, exit 0**. Full semantic batch
(`tests/evaluation/semantic_v2/` + the authority-boundary + codec /
replay / record suites): **all passed, exit 0**. Full suite, three
recorded runs against the 7793 collection (the documented load-
sensitive clean-interpreter subprocess guard flake class — every
failure `OSError [WinError 6] DuplicateHandle` at `subprocess.Popen`
BEFORE any project code runs; zero assertion failures; the fixed
eleven-node allowlist UNCHANGED): run 1 (evidence `tmp_c1_full_
run1.txt`) — **7793 collected, 7793 passed, 0 failed, exit 0**, 0
skipped / 0 xfailed / 0 deselected; run 2 (evidence `tmp_c1_full_
run2.txt`) — 7791 passed, 2 failed (the `test_domain_boundaries::
test_domain_imports_without_django_network_or_llm_dependencies` +
`test_evaluation_boundaries::test_loading_the_corpus_imports_no_
framework_or_provider` allowlist members; both re-passed on isolated
retry); run 3 (evidence `tmp_c1_full_run3.txt`) — 7782 passed,
11 failed — the SAME 11 fixed-allowlist nodes exactly (node-level
list in `tmp_c1_run3_failed.txt`), all re-passing on isolated
retry. An isolated retry does not convert a failed full-suite run
into a full green result: the recorded full-green full-suite result
is run 1. Collection delta (against the re-verified 7576 baseline):
7576 -> 7793 (**+217** = 200 new C1 suite nodes + 1 new boundary
guard node + 16 auto-expanded per-file boundary scans [4 new family
production files × (evaluation vendor + evaluation stdlib + provider
no-wiring + web no-import) — the documented auto-expansion class;
**0 removed / 0 renamed**; per-file: `test_q3c_c1_corpus_integrity`
0 -> 200, `test_research_identity_boundaries` 161 -> 162,
`test_evaluation_boundaries` 64 -> 72, `test_provider_boundaries`
170 -> 174, `test_web_boundaries` 183 -> 187 — no other file changed
its node count). `python manage.py check`: System check identified no
issues (0 silenced). `python manage.py makemigrations --check
--dry-run`: No changes detected.

**Invariance (this phase).** No production Python code outside the
NEW family package, no historical test, no corpus or manifest,
no qualification policy, no prompt text, no authority flag, no
pricing behavior, no database schema changed: `git diff` over
`product_intelligence/` (minus the new family package),
`evaluation/`, and `tests/evaluation/semantic_v2/` is empty against
the starting SHA; the C1 suite's historical-preservation pins pass.
No qualification label was created or revised (the 200-suite
fixtures are synthetic decoder fixtures assembled in the test
module, never a corpus artifact). No model capture occurred (no
transport, no provider, no capture runner; zero-live by
construction). C1 grants NO qualification: the FU4 Bundle authority
program state of record remains UNAPPROVED / NOT EXECUTED — the
qualification corpus is NOT sealed, no Bundle authority case is
independently qualified, and the next phase (C2 — the independently
labeled v1.0.0 seal) starts only under its own explicit approval
(design §9.4). The unrelated worktree artifacts (the pre-existing
`tmp_collection.txt` modification; the untracked session / benchmark
files; the preserved C0 evidence) are preserved.

**Next.** ChatGPT's independent review of the C1 GitHub diff + tests
+ this record (the delivery report's invariance evidence). C2 is NOT
started — it requires its own explicit approval (design §9.4) and
the two-identity review workflow staffed (§8.2).


**PRODUCT-INTEL.SEMANTIC-AUTHORITY-V2-Q3-C-C0 (FU4 Implementation
Integrity Pins — the CF-2 Pin-Gap Correction)

— IMPLEMENTED / PENDING INDEPENDENT REVIEW**

Bounded TEST-ONLY correction on the authoritative starting SHA
`a3134739fdf2531f295744e832099f17f06acfbd` (the Q3-C-D1 design
endpoint; baseline collection **7574**, re-verified this session),
executing design §9.2 of
`docs/PRODUCT_INTEL_Q3C_FU4_BUNDLE_AUTHORITY_QUALIFICATION_DESIGN.md`
(the C0 scope explicitly approved by the task directive): it closes the
CF-2 pin gap — at the starting SHA the two frozen FU4 authority
modules — the deterministic authority derivation
(`product_intelligence/research/semantic_authority_fu4.py`) and the R1
record / codec / replay adapter
(`product_intelligence/research/semantic_decision_v2_fu4.py`) — carried
NO file-content pin in any test literal or document record (the
qualified surface was unpinned — the same gap class R1-FU1 and R2-FU1
closed for the codec and the six R2-owned modules). Test-file
correction only: NO production code change, NO corpus / manifest
change, NO qualification-policy change, NO authority-flag flip, NO
pricing behavior change, NO migration (`makemigrations --check
--dry-run`: No changes detected), NO Windows flake allowlist change.

**The recorded implementation correction (of record).** A first
implementation variant of this phase verified the committed identity
at pytest run time through git subprocess + pure-Python loose-object
parsing (`zlib` over `.git/objects`). That variant was REJECTED
before approval: under sustained Windows handle pressure the git
subprocess itself flakes — the preserved untracked evidence
`c0_full_run2.txt` records both of its nodes failing alongside the
fixed eleven-node allowlist set (13 failed) — so the content-integrity
contract was at risk of becoming a flake-class member. The corrected
implementation (recorded by this entry) is **SUBPROCESS-FREE**: the
nodes use `pathlib` (file bytes) + `hashlib` (SHA-256) only; the module
has NO `subprocess` import, NO git invocation, and NO object-store
access. Git commands were used EXCLUSIVELY during the setup /
documentation pass to record the fixed audit metadata below; normal
pytest execution never touches git.

**The pins (one new file, two nodes, every literal fixed).**
`tests/research/test_q3c_c0_fu4_implementation_pins.py` — the
designated C0 pin home (a separate small test module per the task
directive; NOT added to the FU4 A1 suite) — pins the two modules
against LITERALS recorded at the starting SHA:

* `semantic_authority_fu4.py` — blob OID
  `7c1b1c4f8e88b8951e9362087aeb6b40f7aaf8bd`; committed content
  167,523 bytes (pure LF, 3,614 lines), SHA-256
  `482a637477dd24dfbb1051f714ab087b96061f80c8617ce8adb421a4edb5c09f`;
  exact CRLF expansion 171,137 bytes, SHA-256
  `0a0fb3d7760208b03ca54b7e12e35e8fa9bed81e0e09898252b4cecb2cf81bc4`
  (the recording machine's checkout state).
* `semantic_decision_v2_fu4.py` — blob OID
  `8a4c62c8d360a489740e244f312be1e35ed52fa8`; committed content
  123,142 bytes (pure LF, 3,030 lines), SHA-256
  `c1037a5a987ee7a1674de0d9736ec9670ef13737e092a857b643ea70548d1224`
  (the recording machine's checkout state — byte-identical to the
  committed blob); exact CRLF expansion 126,172 bytes, SHA-256
  `f6f0eecf98a544bd70adb1b47203f149b2ee8710a6d19b8e6947d5f681755967`.

Setup-time derivation procedure of record (executed once, documented
in the module docstring, NEVER executed at pytest run time): blob OID
via `git rev-parse a3134739...:<path>`; size via `git cat-file -s
<OID>`; committed SHA-256 via `git cat-file blob <OID> | sha256sum`
(the stored blob bytes — NO clean / smudge filter applied); the CRLF
expansion digest via the deterministic expansion of the committed bytes
(every `\n` -> `\r\n`). Both production files verified
`git diff`-clean against the starting SHA at preflight, and the
production tree is byte-identical between the R2-FU1 endpoint
`3bf6eb29...` and this SHA (`git diff --stat` over
`product_intelligence/` + `tests/`: empty). (Verified of record: the
D1 STATUS entry above writes the R2-FU1 endpoint SHA with a
transposition — `3bf6e3294df3...` — an object that does not exist in
the repository; the design document's
`3bf6eb294df3ca83b93665158297f97abf3fba4b` is the real endpoint,
verified by `git cat-file -e`. The D1 entry's transposed SHA was
corrected to that real endpoint at C0 delivery; no other D1 content
changed.)

**CRLF / LF portability (the explicit, bounded normalization policy —
of record).** The repository is checked out with `core.autocrlf=true`
+ `* text=auto`, so a committed pure-LF blob may legitimately appear
in the working tree as its exact CRLF expansion. The policy is bounded
to EXACTLY ONE transformation: `content := raw.replace(b"\r\n",
b"\n")` — the exact inverse of the autocrlf expansion — applied ONLY
to derive assertion A. NO arbitrary content normalization: no
whitespace trimming, no encoding conversion, no lone-CR handling, no
trailing-newline logic, no content rewriting; any byte difference
other than line-ending state survives the transformation and changes
the digest. NO dynamically generated expected digests: every expected
value is a fixed literal in the module (the committed SHA-256 + size,
and the two documented checkout-state raw digests), recorded at setup
and never derived from the file under test at run time.

**What each node asserts (two separate identities, neither conflated,
neither weakened).** A. **CONTENT IDENTITY** (portable across the two
documented checkout states): the working-tree bytes after the bounded
CRLF->LF transformation must be byte-identical to the committed
approved content — size AND SHA-256 against the fixed literals. This
is the pin of the task-directive's exact approved content: a content
change to either module fails its own node in ANY documented checkout
state. B. **WORKING-TREE STATE** (the house pin convention, design
§2.7 / R-C1-2): the RAW working-tree bytes (NO transformation) must
hash to exactly one of the two recorded checkout-state literals (the
pure-LF committed form or the exact CRLF expansion). A mixed
line-ending state, a lone-CR residue, or any other byte change is NOT
a documented state: it fails loudly — a recorded re-pin event, never a
silent one. A legitimate checkout-state change (a fresh clone under a
different autocrlf configuration) moves the raw digest to the OTHER
recorded literal and keeps passing — the intended portability.

**Tests.** 2 NEW nodes (one per module):
`tests/research/test_q3c_c0_fu4_implementation_pins.py::TestQ3CC0FU4
ImplementationIntegrityPins::test_pinned_module_implementation_
identity_is_unchanged[semantic_authority_fu4]` and
`…[semantic_decision_v2_fu4]`. No other test change.

**Validation.** Independent single-node runs (first, per the task
directive): node 1 — 1 passed, exit 0 (1.42s); node 2 — 1 passed,
exit 0 (0.55s); neither exhibits subprocess latency (evidence
`c0_fix_single_node1.txt` / `c0_fix_single_node2.txt`). Safety
property demonstrated (the design §9.2 acceptance; the R1-FU1 /
R2-FU1 precedent — controlled and fully reversible): for EACH module,
the original bytes + SHA-256 were recorded; a harmless byte-level
tamper was appended (`b"\n# probe\n"` — never committed); EXACTLY that
file's node FAILED (assertion A — the recorded content-size mismatch
naming the blob OID + starting SHA; the other module's node kept
passing in the same invocation); the exact original bytes were
restored by direct byte write-back (NO git restore / reset / checkout
/ stash / clean); the restored digest was verified byte-identical to
the original and `git diff --quiet` clean against the starting SHA
(evidence `c0_fix_probe_node1.txt` / `c0_fix_probe_node2.txt` /
`c0_fix_post_probe.txt` — both nodes green again after restoration).
Targeted FU4 / R1 / R2 regression batch (`test_semantic_authority_
v2_fu4` 217 + `test_semantic_decision_v2_fu4` 38 +
`test_q3b5_p5_fu4_registration` 35 + `test_q3b5_p1_binding_replay`
20 + `test_q3b5_p1_corpus_2_1` 20 + the new C0 file 2): **332 passed,
0 failed** (evidence `c0_fix_targeted.txt`). Full suite: **7576
collected — 7576 passed, 0 failed, exit 0** (evidence
`c0_fix_full_run1.txt`; zero FAILED lines; 39 subtests passed).
**Allowlist comparison (task directive item 9):** zero full-suite
failures — an exact (empty) subset of the original fixed eleven-node
Windows flake allowlist; the two new integrity nodes are subprocess-
free (no `subprocess` import, no git invocation, no object-store
access) and are NOT added to the allowlist, which is UNCHANGED.
Collection delta (against the re-verified 7574 baseline): 7574 ->
7576 (**+2** = the two new C0 nodes; **0 removed / 0 renamed / 0
added** elsewhere; per-file: `test_q3c_c0_fu4_implementation_pins`
0 -> 2 — no other file changed its node count). Skipped / xfailed /
deselected: **0 / 0 / 0**. `python manage.py check`: System check
identified no issues (0 silenced). `python manage.py makemigrations
--check --dry-run`: No changes detected.

**Invariance (this phase).** No production Python code, historical
test, corpus or manifest, qualification policy, prompt text, authority
flag, pricing behavior, or database schema changed: `git diff` over
`product_intelligence/` is empty against the starting SHA (the only
file touched this phase is the NEW untracked test file; the two probe
tampers were restored byte-identical and verified by digest + git
diff before the targeted and full runs). C0 grants NO qualification:
pinning the implementation identity does not make the FU4 authority
qualified, production-approved, or pricing-eligible — the program's
qualification state of record remains UNAPPROVED / NOT EXECUTED.

**Endpoint of record (corrected at C1 delivery).** The C0 endpoint WAS
committed and pushed: ordinary append-only commit
`36d4e8b9716e18295abfcb8e5d8167ad320bd6df` on `main` (parent
`a3134739fdf2531f295744e832099f17f06acfbd`, the D1 design endpoint;
`origin/main` verified at that SHA at the C1 starting point). The
stale "No commit, no push" wording of this entry (written before the
deliverable landed) is corrected by this sentence only — no other C0
content changed, and C0's approval scope is NOT expanded (C0 remains
the bounded TEST-ONLY CF-2 pin correction; it granted and still grants
NO qualification). The unrelated worktree artifacts (the pre-existing
`tmp_collection.txt` modification; the untracked session / benchmark
files; the preserved untracked `c0_full_run1.txt` /
`c0_full_run2.txt` evidence of the rejected first variant) are
preserved.

**Next.** Independent review of the C0 correction (the GitHub diff).
C1 (the corpus schema + integrity validator) is NOT authorized — it
starts only under its own explicit approval (design §9.3).


**PRODUCT-INTEL.SEMANTIC-AUTHORITY-V2-Q3-C-D1 (FU4 Bundle Authority
Qualification Design)

— DESIGN ONLY / UNAPPROVED (this design exists; it authorizes nothing;
ChatGPT independently reviews the GitHub document and source references
before authorizing any implementation phase)**

Bounded DESIGN-ONLY phase on the authoritative starting SHA
`3bf6eb294df3ca83b93665158297f97abf3fba4b` (the Q3-B5-P5-R2-FU1
endpoint; baseline collection **7574, re-verified this session** by a
full `pytest --collect-only` over the working tree at this SHA). This is
the first independent qualification program designed for FU4 Bundle
composition authority — the explicitly recorded gap of Q3-B5-P5-R2
("Corpus 1.2.0 is a binding-registration and semantic-compatibility
corpus; it does not independently qualify the FU4 Bundle composition
authority" — stated in the 1.2.0 manifest inside the manifest digest).
The sole deliverable is
`docs/PRODUCT_INTEL_Q3C_FU4_BUNDLE_AUTHORITY_QUALIFICATION_DESIGN.md`
(design-only, append-only, on the starting SHA). NO implementation, NO
corpus artifact, NO label, NO evaluator, NO capture, NO model call, NO
policy, NO authority promotion, NO pricing wiring, NO deployment, NO
migration. The final diff contains only the new design document + the
authorized STATUS / PLAN additions (this entry + the PLAN §26.41 row).

**What the design specifies (of record; all UNAPPROVED).** (1) A NEW,
separately versioned, independently labeled qualification corpus family
(`PI-FU4-BUNDLE-AUTHORITY-QUALIFICATION`, proposed identity — O-1;
first version 1.0.0; its own loader / seal / manifest / policy / report —
NOT an extension of the byte-pinned `evaluation/semantic_v2` harness and
NOT a modification of corpus 1.2.0), whose per-case documents carry the
task-mandated fields (stable case ID, category, target + candidate
evidence, the original published source content, evidence provenance,
the extraction evidence + digest, the bundle composition evidence, the
completeness-attestation source, the published quantity information, the
independently expected authority outcome, the reviewer identity +
review status, the explicit rationale, the case digest). (2) A five-axis
separation (semantic product identity / bundle composition equivalence /
sales-unit quantity equivalence / authority tier eligibility / pricing
eligibility) with the headline invariant I-1: a correct semantic MATCH
must never be treated as sufficient proof of Bundle equivalence or
pricing comparability (labeled rows B10 / D13 / D11 + the evaluator's
perturbation-invariance check I-4). (3) A five-layer evidence-authenticity
boundary (internal structural integrity / provenance consistency /
independent source authenticity / completeness of published evidence /
truth of the underlying commercial claim) with the exact safe-conclusions
statement — a valid digest alone does NOT establish source authenticity;
a publisher's completeness claim does NOT establish physical
completeness; the system claims neither; no cryptographic trust or
verification capability is invented beyond what the repository
implements. (4) A complete qualification case matrix (category A
PROVEN_EQUIVALENT, B UNPROVEN, C CONTRADICTED, D adversarial authority
cases — each row with the expected authority, the expected failure
stage, the required evidence, the evidence kind, the surface, and the
minimum case count; v1.0.0 floor 92 Track A / 21 Track B; the
independent tester authors or reviews the D rows). (5) Two distinct
qualification tracks: Track A (deterministic authority — the frozen FU4
derivation + constructors + the registered R1 codec / replay executed
offline over the sealed corpus, metrics M1–M15 with exact denominators,
including the false-PROVEN count over the whole population, the
confusion matrix, the replay agreement, the substitution / missing-
attestation / quantity-conflict detections, and the pricing-leakage
count) and Track B (model-assisted evidence acquisition — the pinned
models under the frozen Prompt 2.1 scored on published-constituent
extraction precision / recall, attestation-grounding accuracy,
unsupported-constituent hallucination, ambiguous-evidence abstention,
provenance correctness (PARTIAL — span-level is FUTURE / NOT
IMPLEMENTED, O-5), valid output schema rate, coverage, and primary /
fallback separation; Track B NEVER feeds Track A and NEVER constructs an
attestation — gate MB-3). (6) An acceptance policy: eight mandatory
hard safety gates (G1 zero false PROVEN_EQUIVALENT on independently
labeled negative cases; G2 zero unauthorized authority promotion;
G3 zero pricing-eligibility leakage; G4 zero evidence-integrity bypass;
G5 zero cross-listing substitution; G6 zero historical-binding
confusion; G7 full replay agreement for accepted records; G8 no model-
generated completeness attestation treated as publisher evidence), three
Track B model-tier gates (MB-1..MB-3), the family DRAFT threshold
vocabulary (O-7 — proposals, NOT finalized values; the existing DRAFT
policy is untouched and uncopied), the six-state decision ladder
(FAIL_CLOSED > NOT_QUALIFIED > POLICY_PENDING > RESEARCH_ONLY >
QUALIFICATION_CANDIDATE > QUALIFIED_FOR_REVIEW_ASSISTANCE, with
PRODUCTION_AUTHORITY_QUALIFIED reserved for the separately gated W1 and
NEVER computable by the report), the statistically meaningful coverage
requirements (population-complete zero-tolerance gates; the mandatory
rule-of-three disclosure with the explicit contract-coverage-not-
real-market statement; the real-market minimums as the gate for tiers
above RESEARCH_ONLY; the diversity + two-identity + reviewer-distinctness
floors). (7) An independent review workflow (corpus author /
independent label reviewer / independent tester / phase implementer /
ChatGPT final gate — the implementer is never the sole authority for
expected results; no agent's final report is proof). (8) A bounded
ten-phase roadmap (D1 this design + C0 the recorded pin-gap correction
forced by finding CF-2; C1 the corpus schema + integrity validator;
C2 the independently labeled v1.0.0 seal; C3 the real-market bundle
evidence acquisition — the only live surface besides E2's gated capture
sub-step; E1 the deterministic evaluator + adversarial tests; E2 the model
evidence acquisition evaluation; P1 the independent policy review; Q1
the qualification execution; W1 the separate production wiring approval,
only if qualified) — each with the exact scope, inputs, deliverables,
acceptance criteria, required tests, explicit stop conditions, and
authority boundaries; no phase may redefine its acceptance criteria
because the implementation failed. (9) The source-to-design
traceability table and the exact implementation authorization boundaries
(the design authorizes nothing beyond its own existence; every phase
requires the pending lineage reviews to be ratified + ChatGPT's
explicit phase approval).

**Findings of record (design-time inspection, verified at the starting
SHA).** CF-1: the task matrix's placement of "conflicting secondary extraction
cues" under CONTRADICTED conflicts with the frozen approved contract
(P3 D8 / U12; R1 matrix row 8) which derives UNPROVEN for candidate
self-contradiction — the design keeps the frozen semantics, documents
the conflict, and requests ratification of the documentation (O-3); NO
contract change. CF-2 (forces phase C0): the FU4 module
(`semantic_authority_fu4.py` — working-tree digest `0a0fb3d7…` /
committed blob `482a6374…`) and the R1 record adapter
(`semantic_decision_v2_fu4.py` — `c1037a5a…`) are NOT content-pinned by
any test literal or document record at the starting SHA (the qualified
surface is unpinned — the same gap class R1-FU1 and R2-FU1 closed for
the codec and the six R2-owned modules); C0 restores the contract
following the recorded precedent. CF-3: under the frozen materiality
grammar (P3 §3.7 — a multiset of (quantity, item) pairs, no merging),
"valid duplicate constituent quantities" is PROVEN-eligible only when
published byte-identically on both sides; the non-identical phrasing
(`1x RAM + 1x RAM + 1x CPU` vs `2x RAM + 1x CPU`) is T-DIFF-MATERIAL ⇒
CONTRADICTED over attested clauses — both shapes are labeled per the
frozen contract (O-4 records the future grammar-version decision). CF-4:
"asymmetric published quantity" splits under the frozen contract into
UNPROVEN (U18, no attestation) and PROVEN-eligible (ATTESTED_NOT_
MATERIAL, verified quantity attestation on the missing side). CF-5:
"semantic NO_MATCH with apparently equivalent Bundle composition" — the
unit axis is decision-independent; where the composition IS
attested-equivalent the unit derives PROVEN even under a NO_MATCH
context while the tier stays non-automatic (row D12).

**Invariance (this phase).** No production Python code, test, corpus or
manifest, qualification policy, prompt text, live runtime, pricing rule,
authority flag, or database schema changed. No model capture occurred
(no transport, no provider, no capture runner — the design is the only
artifact). No qualification labels were created or revised. No
qualification is claimed: the program's state of record at this design's
completion is UNAPPROVED / NOT EXECUTED, and after full execution the
computable state can only move under an APPROVED family policy (the
ladder's POLICY_PENDING floor). No test deleted, renamed, skipped,
xfailed, deselected, or weakened; the collection baseline remains
**7574** (re-verified; no new test nodes — design only). The unrelated
worktree artifacts (the pre-existing `tmp_collection.txt` modification;
the untracked session / benchmark files) are preserved. No
restore / reset / checkout / stash / clean / amend / rebase / force-push
used.

**Next.** ChatGPT's independent review of the GitHub design document +
its source references is the approval gate. The first implementable
phase is Q3-C-C0 (the CF-2 pin correction), which starts only after the
pending lineage reviews (Q3-B5-P4-FU2, R1, R1-FU1, R2, R2-FU1) are
ratified and the C0 scope is explicitly approved (design §9.2 / O-2).
A successful D1 means the qualification design is ready for review — it
does NOT mean FU4 authority is qualified or production-approved.


**PRODUCT-INTEL.SEMANTIC-AUTHORITY-V2-Q3-B5-P5-R2-FU1 (Semantic
Authority V2 — Six Module Integrity Contract Restoration, R2
test-preservation correction)

— IMPLEMENTED / PENDING INDEPENDENT REVIEW**

Bounded TEST-PRESERVATION CORRECTION on the authoritative starting
SHA `202a3efa386c45b137b2f407510fe91a594f5e55` (the R2 endpoint;
baseline collection 7568, re-verified this session), restoring the
six SHA-256 file-content integrity contracts that R2's A1 re-pin
removed from the FU4 frozen-module test table (`tests/research/
test_semantic_authority_v2_fu4.py`, `FROZEN_MODULE_PINS`, 17 -> 11
rows). This is a test-file correction only: NO production code
change, NO corpus reseal, NO manifest change, NO qualification-
policy change, NO live wiring, NO pricing change, NO deployment, NO
migration (`makemigrations --check --dry-run`: No changes detected),
NO Windows flake allowlist change.

**The gap (R2's removal left the six modules unpinned at the file
level).** R2's recorded claim — "the six R2-owned files' post-R2
state is pinned by the new R2 suite" — was NOT implemented as file-
content pins. Verified before changing anything (the FU1 pre-change
audit): no node anywhere in the tree reads the bytes of any of the
six modules and compares its SHA-256 against a literal (all six
post-R2 digests grepped across `tests/` + `docs/`: zero hits). The
R2 suite's `_file_digest` helper is used only for the qualification
artifacts (the committed corpus / manifest JSON files) and never
for the modules; the R2-suite nodes that reference the six modules
are behavioral (registry / seal / gate / report / CLI-regeneration
assertions), not content-based. Any post-R2 edit to any of the six
files therefore passed the full 7568-node suite silently.

**The old A1 pins vs the R2 implementation endpoint.** The six
pre-R2 literals (at R2's starting SHA `ac75f47`, now obsolete):
`contract_v2_1.py` `dc86899f…`, `fixtures.py` `cdb60166…`,
`corpus.py` `876edbe8…`, `gates.py` `113c7b53…`, `report.py`
`cad62e42…`, `cli.py` `0102c4cc…`. R2 explicitly amended these six
modules on purpose to register the new FU4 offline binding (design
§10.2: the `V2_1_FU4_CONTRACT_BINDING` constant + import
self-checks; `CORPUS_VERSION_2_1_FU4` + the 1.2.0 document builder
+ the manifest statement / lineage keys; the third
`BINDING_CORPUS_VERSIONS` entry; the `zero_contract_version_
mismatch` third-binding detail branch; the `_contract_section`
third-binding branch; the corpus-build 1.2.0 generation), so the
pre-R2 literals no longer describe the current content. **They
were NOT restored as current expectations** — restoring them would
fail by design (the same category as the pre-R1 codec literal in
R1-FU1). The six expected digests changed for exactly this reason:
R2's registration amendment moved each module from its `ac75f47`
content to its `202a3efa` endpoint content.

**The correction (one new class, six literal digests, no dynamic
computation).** `tests/evaluation/semantic_v2/
test_q3b5_p5_fu4_registration.py` — the R2 suite, the recorded home
of the R2-endpoint pins for the R2-owned files (the same category
as the R1-FU1 codec pin in the R1 suite; pinning here makes the
recorded R2 claim true and leaves the FU4 A1 suite file
UNMODIFIED) — gains: the `R2_ENDPOINT_MODULE_PINS` table with six
explicit literal SHA-256 expected digests (each computed from the
actual committed file content at the starting SHA `202a3efa` — the
working tree verified byte-identical for all six at FU1 start:
`git diff` clean); the NEW `TestR2EndpointModulePins` class with
one parameterized node; and one bullet in the file docstring. The
node reads the real file bytes (`_file_digest` =
`hashlib.sha256(...).hexdigest()` over the file's bytes) and
compares against the corresponding literal. The expected digest is
recorded, never derived from the file under test at run time. The
six fixed expected digests (the R2-endpoint content):

* `product_intelligence/semantic/contract_v2_1.py` —
  `d9e564ef1824b55e31a2096082feff2e5d7d7df42154b4845785f4d846617ea4`
* `product_intelligence/evaluation/semantic_v2/corpus.py` —
  `4c0851a82b2f0863a16938c419e49938c86c1494aefbbde03684e496ee4fb4e4`
* `product_intelligence/evaluation/semantic_v2/cli.py` —
  `e4853546e879eaf1b1edb69002b7f07aece15f5199e7d4979ae662eb84d9c645`
* `product_intelligence/evaluation/semantic_v2/fixtures.py` —
  `ac8777dc27cdf879415645a04468690366d5d92f515c67fe7f794482cb0c783f`
* `product_intelligence/evaluation/semantic_v2/gates.py` —
  `a441ada2a275983f15ddb39f770c4163a42c4f95255c99f7565ea6d83c582e3f`
* `product_intelligence/evaluation/semantic_v2/report.py` —
  `45626ae166cf6ba0e4818357dc65363bf837503153a78764b518a7294f6a8619`

**What stands (no weakening, nothing removed).** (1) The existing
ELEVEN frozen-input pins in the FU4 A1 suite are untouched (the
suite file is unmodified by FU1; the A1 table, CORPUS_
ARTIFACT_PINS, SUITE_FILE_PINS, and the FU3 line-exact pin all
stand). (2) The R1-FU1 codec integrity pin (`c0cef216…`) is
untouched. (3) All 29 pre-existing R2-suite nodes are unmodified —
the correction is purely additive to the R2 suite (29 -> 35
nodes). (4) All existing R2 behavior / corpus / manifest /
qualification / firewall tests pass unmodified (re-run below). (5)
The six pre-R2 literals are documented as obsolete in the
`R2_ENDPOINT_MODULE_PINS` comment and are not restored as current
expectations.

**Safety property demonstrated (adversarial verification,
controlled and fully reversible).** For each of the six files: the
original bytes + SHA-256 were recorded; a harmless temporary
content mutation was appended (`b"\n# probe\n"` — a byte-level
tamper, never committed); EXACTLY that file's integrity node FAILED
(recorded `AssertionError: {file} differs from its R2-endpoint
content (commit 202a3efa, digest …); the module was explicitly
amended by R2 to register the FU4 offline binding - a further
change requires an explicit, recorded re-pin`); the exact original
bytes were restored (direct byte write-back — NO git restore /
reset / checkout / stash / clean); and the restored digest was
verified equal to the original literal before any suite run below.
All unrelated worktree evidence preserved.

**Tests.** 6 NEW nodes (the R2 suite's `TestR2EndpointModulePins`,
one parameterized row per file): `test_r2_amended_module_is_
content_pinned_at_the_r2_endpoint[product_intelligence/evaluation/
semantic_v2/cli.py-e4853546e879eaf1b1edb69002b7f07aece15f5199e7d4
979ae662eb84d9c645]`, `[…corpus.py-4c0851a82b2f0863a16938c419e499
38c86c1494aefbbde03684e496ee4fb4e4]`, `[…fixtures.py-ac8777dc27c
df879415645a04468690366d5d92f515c67fe7f794482cb0c783f]`, `[…gates
.py-a441ada2a275983f15ddb39f770c4163a42c4f95255c99f7565ea6d83c58
2e3f]`, `[…report.py-45626ae166cf6ba0e4818357dc65363bf837503153a
78764b518a7294f6a8619]`, `[product_intelligence/semantic/contract_
v2_1.py-d9e564ef1824b55e31a2096082feff2e5d7d7df42154b4845785f4d8
46617ea4]`. No other test change.

**Validation.** R2 suite alone: 35 passed, 0 failed (29 + 6 new).
Targeted R1 / R2 + preservation batch (`test_q3b5_p5_fu4_
registration` 35 + `test_semantic_authority_v2_fu4` 217 +
`test_semantic_decision_v2_fu4` 38 + `test_q3b5_p1_binding_replay`
20 + `test_q3b5_p1_corpus_2_1` 20): 330 passed, 0 failed. Targeted
historical corpus / codec / replay / boundary batch (the full
`tests/evaluation/semantic_v2/` directory 398 + codec 55 + replay
31 + record 47 + V2 61 + decision-boundaries 50 + semantic_v2-
boundaries 32 + FU3 98 + extraction 111 + 7): 890 passed, 0
failed. Boundary batch (the same 824-node set as the R2 record:
research identity 161 + evaluation 64 + domain 59 + providers 170
+ web 183 + runs 105 + semantic_v2 boundaries 32 + decision
boundaries 50): 821 passed on the batch run + 3 fixed-allowlist
members (every one `OSError: [WinError 6] The handle is invalid`
at `subprocess.Popen -> _winapi.DuplicateHandle` BEFORE any
project code runs; zero assertion failures) each re-passed
isolated one-node-per-process — no non-flake failure. Full suite
(run 1): 7574 collected — 7563 passed, 11 failed — the 11 failures
are EXACTLY the fixed eleven-node load-sensitive clean-interpreter
subprocess guard flake allowlist (every one `OSError: [WinError 6]
The handle is invalid` at `subprocess.Popen -> _winapi.
DuplicateHandle` before any project code runs; zero assertion
failures), each re-passed isolated one-node-per-process (7 on the
first spaced pass, 4 on spaced retry — the documented multi-
attempt behavior under sustained handle pressure after a full run).
Full suite (run 2, over the final tree with documentation): 7574
collected — 7563 passed, 11 failed — the SAME 11 fixed-allowlist
nodes, every one failing at the same
recorded point (`subprocess.Popen -> _get_handles -> _winapi.
DuplicateHandle` before any project code runs; zero assertion
failures) with a VARIANT OS error code under the machine's
sustained handle pressure (9× `OSError: [WinError 50] The request
is not supported` + 2× `OSError: [WinError 6] The handle is
invalid` — the same flake class at the same line, a surface
variant; the node-identity allowlist is NOT expanded and no new
node joined it); all 11 re-passed isolated one-node-per-process
(7 on the first spaced pass, 4 on spaced retries). Full suite
(run 3 — DEFINITIVE, over the final tree with documentation):
**7574 collected — 7574 passed, 0 failed, exit 0** (zero
collection errors; the machine's handle pressure cleared between
run 2 and run 3). Across all three full runs and every targeted
run: no non-flake node failed, and no node outside the fixed
allowlist failed anywhere. Collection accounting
(node-level diff against the 7568-node R2 baseline collected over
the same working tree before the correction): 7568 -> 7574 (+6 =
6 new parameterized rows; **0 removed / 0 renamed / 0 added**);
per-file: `test_q3b5_p5_fu4_registration` 29 -> 35 — no other file
changed its node count. Skipped / xfailed / deselected: **0 / 0 /
0**. `python manage.py check`: System check identified no issues
(0 silenced). `python manage.py makemigrations --check --dry-run`:
No changes detected.

**Production firewall (evidence).** The six production files are
byte-identical to the R2 endpoint (each pinned by the new nodes;
the transient probe bytes were restored and verified by digest
before the suite runs). No qualification flag flipped (`V2_
AUTHORITY_QUALIFIED` remains False in both pinned locations + the
FU4 adapter's mirror — re-run above); no corpus / manifest change
(historical artifact pins + the 1.2.0 digest pins pass); no policy
change (the DRAFT is byte-identical and still 1.0.0-scoped); no
live wiring; no pricing change; no migration; no deployment
performed.

R2 (below) is ON HOLD pending this correction's independent review;
ChatGPT inspects the GitHub correction before approving R2.


**PRODUCT-INTEL.SEMANTIC-AUTHORITY-V2-Q3-B5-P5-R2 (Semantic
Authority V2 — FU4 Offline Qualification Harness Integration)

— IMPLEMENTED / ON HOLD PENDING TEST-PRESERVATION CORRECTION (Q3-
B5-P5-R2-FU1: the R2 A1 re-pin excluded the six R2-owned modules
from the frozen-input table, and the recorded claim that the new
R2 suite pins their post-R2 state was not implemented as file-
content pins; corrected in Q3-B5-P5-R2-FU1, recorded above) /
PENDING INDEPENDENT REVIEW (ChatGPT inspects the GitHub correction
before approving R2)**

Bounded QUALIFICATION-LAYER phase (sub-phase R2 of the separately
gated FU4 registration step; the R1 record / replay layer is
committed at `60f548d` and its test-preservation correction at
`ac75f47`) on the authoritative starting SHA `ac75f474f2515760a7eb99
13807b075f6cf50d1a` (the R1-FU1 endpoint; baseline collection 7545,
re-verified this session). Executes the CONDITIONALLY APPROVED
Q3-B5-P5 design (`docs/PRODUCT_INTEL_Q3B5_P5_FU4_BINDING_REPLAY_
QUALIFICATION_DESIGN.md`, section 10.2). This phase makes the
approved FU4 authority binding a RECOGNIZED, digest-sealed,
independently identifiable member of the versioned offline Semantic
V2 qualification harness. **It does NOT qualify FU4 for
production:** the FU4 binding begins POLICY_PENDING /
AUTHORITY_NOT_QUALIFIED, with no production eligibility and no
automatic pricing eligibility. NO live execution, NO capture, NO
model call, NO pricing, NO deployment, NO migration
(`makemigrations --check --dry-run`: No changes detected), NO policy
creation / approval, NO corpus LABEL change (binding-only re-seal),
NO threshold change.

**The exact FU4 binding (registered).**
`("V2", "2.1", 1, 1, "SEMANTIC_AUTHORITY_V2_S2A_FU4")` — owned by
the semantic layer as `V2_1_FU4_CONTRACT_BINDING` in
`product_intelligence/semantic/contract_v2_1.py` (DEC-6; composed
from the frozen exports — no literal token in source; import-
self-checked to move ONLY the authority axis relative to the
existing 2.1/FU3 binding; the FU3 binding constant byte-unchanged).
The R1 research record adapter's mirror (`V2_FU4_CONTRACT_BINDING`)
is drift-pinned against this owner by test.

**The four known bindings, distinguished exactly.** V1 (codec /
replay only — never a harness seal, unchanged); 2.0/FU2 (codec +
replay + harness 1.0.0, unchanged); 2.1/FU3 (harness 1.1.0 only —
codec / replay-refused, unchanged); 2.1/FU4 (codec + replay from
R1 + harness 1.2.0 from R2). Unknown or mixed-axis bindings fail
closed at every surface (seal registry, loader, gates, report,
capture loaders) — no fallback to a nearby binding, no silent
historical-record migration.

**Corpus 1.2.0 (binding-only re-seal; lineage from 1.1.0).** NEW
committed artifacts:
`evaluation/semantic_v2_qualification/corpus_2_1_fu4.json` (file
digest `7475334a009b5b63dbeabf15bc11ced077862acb66472df7997f22becf
e8ce3e`; **corpus digest `582b35bbee93959eaa5a598fa579cd99229e550e
37f3c6cd970f7774ed9d1b91`**) and
`evaluation/semantic_v2_qualification/manifest_2_1_fu4.json` (file
digest `faa2febdc7611ed2593257920b2c6348608fab6cd09de0b2bfa862405
c00ab58`; **manifest digest `972ba35428d1dfc0a4b07d2027d9186577cf
398a3ba4dc96dc61865b9843d8d7`**). Derived from the sealed 1.1.0
document by moving EXACTLY `{corpus_version -> 1.2.0,
semantic_contract_binding -> the FU4 tuple, corpus_digest ->
recomputed}`; 56/56 per-case documents (original case IDs, source /
target evidence, expected semantic labels, ambiguity
classifications, negative controls, per-case meaning, sealed per-
case digests) BYTE-IDENTICAL to 1.1.0 (and to 1.0.0); `label_
revisions` empty; `corpus_id` / `corpus_label` / `created_utc` /
`corpus_schema_version` unchanged (the P1 1.1.0 precedent executed
verbatim, design section 5.1 / DEC-3). Regenerating from the
auditable source (`cli corpus-build`, extended with the 1.2.0
generation) reproduces BOTH committed artifacts byte-for-byte, and
the committed 1.0.0 / 1.1.0 artifacts + manifests remain byte-
identical. The 1.2.0 manifest carries EXACTLY two additive top-
level keys inside the manifest digest (manifest schema stays 1; the
committed 1.0.0 / 1.1.0 manifests do not gain the keys): `statement`
= the required explicit record ("Corpus 1.2.0 is a binding-
registration and semantic-compatibility corpus. It does not
independently qualify FU4 Bundle composition authority.") and
`lineage` = `{derived_from_corpus_version: 1.1.0,
derived_from_corpus_digest: 14396eae…8dcd}` (the explicit 1.1.0
lineage).

**Harness integration (the exact R2 file set, design section
10.2).** MODIFIED `semantic/contract_v2_1.py` (the FU4 binding
constant + import self-checks — additive; the existing constant
byte-unchanged); MODIFIED `evaluation/semantic_v2/fixtures.py`
(`CORPUS_VERSION_2_1_FU4 = "1.2.0"` +
`build_corpus_2_1_fu4_document()` + the manifest statement /
lineage keys + the recorded `CORPUS_2_1_CORPUS_DIGEST` lineage
anchor); MODIFIED `evaluation/semantic_v2/corpus.py` (the third
`BINDING_CORPUS_VERSIONS` entry — `KNOWN_PRODUCTION_BINDINGS`
becomes EXACTLY the three production bindings, drift-pinned, no
literal copies; the mirrored manifest builder); MODIFIED
`evaluation/semantic_v2/gates.py` (the
`zero_contract_version_mismatch` detail-text branch for the third
binding — the eight gate names / order / fail-closed semantics
unchanged; the 2.0 and 2.1/FU3 detail texts stay BYTE-IDENTICAL,
proven against the committed historical baselines); MODIFIED
`evaluation/semantic_v2/report.py` (the `_contract_section` third-
binding branch — the report schema UNCHANGED; the 1.2.0 contract
section records the FU4 binding + the REAL 2.1 system-prompt digest
`e2949e75…18fc` + the runtime config identity with
`v2_authority_qualified: false`); MODIFIED
`evaluation/semantic_v2/cli.py` (the corpus-build 1.2.0
generation). VERIFIED BYTE-UNCHANGED: `capture.py`,
`direct_capture.py`, `policy.py`, `evaluator.py` (the prompt-axis
capture mechanism and the metric surface are binding-count-agnostic
— the registration changes no capture / evaluation / policy
behavior), the R1 codec / replay / adapter modules (the R1-FU1
codec endpoint pin `c0cef216…` passes — the codec is byte-identical),
`runtime_v2.py`, the frozen FU2 / FU3 / FU4 research modules, the
Prompt 2.0 / 2.1 texts, and the committed 1.0.0 / 1.1.0 artifacts +
DRAFT policy (all A1 pins pass).

**Committed 1.2.0 no-capture baselines (both pinned candidates).**
NEW `evaluation/semantic_v2_qualification/reports/
q3b5_p5_baseline_1_2_0/` — four report files (`no-capture_amax_
qwen3.8-27b__report.{json,md}`, `no-capture_vllm-262k_Qwen3.6-
27B-262K__report.{json,md}`; generated-utc `2026-10-08T00:00:00Z`,
the committed-baseline convention): 43/43 eligible NOT_CAPTURED,
13/13 contract-negative rejected as expected, all eight gates pass
(the 1.2.0 gate detail names prompt 2.1 + the FU4 authority axis),
decision **POLICY_PENDING** (no applicable APPROVED policy — the
DRAFT is 1.0.0-scoped and unapproved, unchanged), `policy: null`,
authority `granted: false` + `v2_authority_qualified: false` + the
evaluation-evidence-only note. The report schema is unchanged;
`verify_report` binds each 1.2.0 report to the 1.2.0 corpus and
refuses the 1.0.0 / 1.1.0 corpora (and the historical baselines
refuse the 1.2.0 corpus — the cross-lineage matrix, both
directions).

**Qualification status (the firewall).** `V2_AUTHORITY_
QUALIFIED` remains False in both pinned locations + the FU4
adapter's mirror; `V2_FU4_AUTHORITY_QUALIFIED` exists only as the
FU4 module's explicit marker, pinned False (registration is NOT a
qualification); no production eligibility, no automatic pricing
eligibility; the pricing-eligible tier set is unchanged and
`NEEDS_REVIEW` remains non-pricing-eligible; no live module
(semantic / execution / runs / web / providers) references the FU4
qualification harness (the new R2 reachability node, AST +
lexical) or the FU4 record surface (the R1 guard stands);
`runtime_v2.py` byte-identical (the live runtime stays on the
frozen 2.0 / FU2 record). Corpus 1.2.0 is NOT evidence of
production readiness: a future separately approved phase must
establish the Bundle-specific FU4 authority qualification cases +
an APPROVED 1.2.0-scoped policy (the design section 5.6 governance
step) + the live 2.1/FU4 execution decision (design O-3 / O-4)
before any qualification claim.

**Authority isolation (the separate metric surfaces, DEC-5).** The
semantic-model performance surface (the harness: labels, metrics,
gates) and the deterministic FU4 authority surface (the R1
research derivation + zero-live replay) are kept explicitly
separate: over EVERY committed 1.2.0 case the FU4 no-capture
arithmetic derives CONTRADICTED for the three sales-unit cases
(0032 / 0033 / 0034 — the form axis over the default single-unit
target) and UNPROVEN for the 40 UNAVAILABLE-channel cases (frozen
delegation) — NO case derives PROVEN and no case lifts a ceiling;
the corpus semantic label (NO_MATCH) is never an input to the unit
derivation (signature-pinned; the identical channel derives the
identical unit under a MATCH evaluation); a count-only bundle
cannot gain automatic comparable authority (UNPROVEN + the cap,
while the SAME input preserves the historical FU3 PROVEN — three-
token coexistence); a missing completeness attestation can never
become PROVEN (SYNTACTICALLY_VALID holds the cap, even over an
independently attested-equal target); a tampered embedded
extraction result (self-consistently re-digested forgery) is
refused at the FU4 record decode — no unit is derived from it, no
replay passes; Bundle PROVEN / UNPROVEN / CONTRADICTED states are
governed by the R1 replay over the recorded evidence (re-exercised
through the universal entry points in the R2 suite).

**Tests.** 29 NEW nodes in the NEW file
`tests/evaluation/semantic_v2/test_q3b5_p5_fu4_registration.py`
(the mandated matrix over the REAL public harness interfaces + the
REAL R1 record / replay entry points — never only internal
helpers): the exact four-binding registry / seal distinction; FU4
-> 1.2.0 only; the historical mappings unchanged; the 56/56 case-
ID + label invariance; the 1.2.0 digest / manifest integrity
(statement + lineage + byte-for-byte regeneration); wrong digest /
wrong binding / unknown token / cross-version substitution
rejections; the FU4 no-capture evaluation + committed-baseline
reproduction; invalid 2.1 output failing closed (the zero-
schema-bypass gate — NOT_QUALIFIED, never a pass); primary /
fallback provenance independence; wrong provider / model refusal;
historical baselines interpretable + cross-lineage refusal; zero-
live socket-blocked no-capture / replay / historical V2 replay;
qualification cannot set authority flags (the hypothetical full
pass stays POLICY_PENDING with the DRAFT policy); the authority-
isolation rows above; `V2_AUTHORITY_QUALIFIED` False everywhere; no
live runtime harness reference; frozen FU2 / FU3 replay behavior
unchanged (byte-identical V2 round trip + the 2.1/FU3 codec
refusal standing); historical report semantics; the eight gate
names / order / semantics (the 2.0 detail byte-identical to the
committed baseline).

**Recorded test-file corrections (the P1 / P2-FU1 / Q3-B4-FU2 /
Q3-B5-P4-FU1 / FU2 / R1 precedent — in place, documented, names
preserved, intent preserved or strengthened; no test deleted,
renamed, skipped, xfailed, deselected, ignored, or weakened beyond
the one recorded re-pin below; the design's section 1.7 inventory
is extended by TWO mechanical discoveries of the same category, as
the task anticipated).** (1) `tests/research/test_semantic_authority_
v2_fu4.py`: the A1 `FROZEN_MODULE_PINS` table re-pins at R2's
starting SHA EXCLUDING the six R2-owned files (contract_v2_1.py /
corpus.py / fixtures.py / gates.py / report.py / cli.py) — 17 ->
11 parameterized rows (the recorded consequence of design
section 10.2, the same category as R1's codec row; the six
R2-owned files' post-R2 state is pinned by the new R2 suite
instead); the A4 harness-registry node re-pins from the two-
binding state to EXACTLY the three-binding seal registry (2.0/FU2
-> 1.0.0, 2.1/FU3 -> 1.1.0, 2.1/FU4 -> 1.2.0; the 1.2.0 artifacts +
fixtures constant now exist — name preserved, intent
strengthened); the E1 registry node's harness portion re-pins to
the three-binding state (the codec / replay union + the committed
2.1/FU3 constant stand); the E1 "committed 2.1 binding is still
the FU3 one" node re-pins its second assertion (the module now
owns the DISTINCT FU4 successor constant composed from the
exports — the FU3 binding is byte-unchanged; the pre-R2 "no FU4
value in the module" pin encoded the pre-registration state); the
E2 node re-pins to the completed registration (the seal registry
carries exactly the 2.1/FU4 -> 1.2.0 entry; the contract phase
itself registered nothing — the name "no binding registration
happened in the CONTRACT phase" stays true). (2)
`tests/evaluation/semantic_v2/test_q3b5_p1_binding_replay.py`: the
2.1 drift-pin node's `KNOWN_PRODUCTION_BINDINGS` assertion moves
from the exact two-binding set to the exact three-binding set (the
FU4 binding is the only addition; the 2.1/FU3 / 2.0/FU2 drift pins
stand). (3) `tests/evaluation/semantic_v2/test_q3b5_p1_corpus_2_1.
py` — MECHANICAL DISCOVERY BEYOND THE DESIGN'S SECTION 1.7
INVENTORY (the design verified four suites at design time and
missed this node; the task's "do not assume the inventory is
exhaustive"): `test_the_known_bindings_map_is_exact` moves from
the two-entry `BINDING_CORPUS_VERSIONS` / two-set
`KNOWN_PRODUCTION_BINDINGS` pins to the exact three-entry /
three-set state (the two historical entries byte-unchanged). (4)
`tests/research/test_semantic_decision_v2_fu4.py` — MECHANICAL
DISCOVERY OF THE SAME CATEGORY (this suite is R1's own; it pins
the pre-R2 harness state in the qualification-marker node): the
marker pins stand; the trailing harness assertion moves from
"exactly two bindings, no 1.2.0 artifact" to the exact three-
entry seal registry + the fixtures constant / committed artifacts.
Every correction preserves the original assertion's purpose and
pins a strictly more exact registry state. The R1-FU1 codec
SHA-256 content pin (`c0cef216…`) is PRESERVED and passes (the
codec is byte-identical).

**Validation.** New R2 suite alone: 29 passed, 0 failed. Focused
registration batch (the 217-node FU4 contract suite + the 38-
node R1 suite + the 98-node FU3 suite + the 111 + 7 extraction
suites + codec 55 / replay 31 / decision-boundaries 50 / V2 61 /
record 47 + the P1 binding-replay 20 + P1 corpus-2.1 20 + the
49-node 2.1 contract suite): all passed, 0 failed. Focused
evaluation/semantic_v2 directory: 392 passed, 0 failed. Focused
boundary suites (research identity / evaluation / domain /
providers / web / runs / semantic_v2 boundaries / decision
boundaries): 824 passed, 0 failed. Full suite (run 1, over the
working tree): **7568 collected — 7557 passed, 11 failed** — the
11 failures are EXACTLY the fixed eleven-node load-sensitive clean-
interpreter subprocess guard flake allowlist (every one `OSError:
[WinError 6] The handle is invalid` at `subprocess.Popen ->
_winapi.DuplicateHandle` BEFORE any project code runs; zero
assertion failures), each re-passed isolated one-node-per-process
(10 on the first spaced pass, the 11th on spaced retry — the
documented multi-attempt behavior under sustained handle pressure
after a full run); no non-flake node failed. Full suite (run 2 - DEFINITIVE, over the final tree with documentation): **7568 collected - 7558 passed, 10 failed** - the 10 failures are EXACTLY a subset of the same fixed eleven-node allowlist (every one the recorded `OSError: [WinError 6]` at `subprocess.Popen -> _winapi.DuplicateHandle` before any project code runs; zero assertion failures); all 10 re-passed isolated one-node-per-process (6 on the first spaced pass, 4 on spaced retry); no non-flake node failed in either run. Collection
accounting (node-level diff against the starting SHA, verified
over an independent linked worktree at `ac75f47`, removed after
use): 7545 -> 7568 (+23 net = +29 new-file nodes - 6 the recorded
A1 re-pin rows — the only removals; **0 other nodes removed / 0
renamed**); per-file: `test_semantic_authority_v2_fu4` 223 ->
217 (the six rows), `test_q3b5_p5_fu4_registration` 0 -> 29 — no
other file changed its node count. Skipped / xfailed /
deselected: **0 / 0 / 0**. `python manage.py check`: System check
identified no issues (0 silenced). `python manage.py
makemigrations --check --dry-run`: No changes detected (no model
change — the registration is semantic / evaluation layer + tests +
documents + corpus artifacts).

**Historical compatibility (evidence).** The committed 1.0.0 /
1.1.0 corpus + manifest file digests equal the recorded literals
(`ffb407b3…` / `caa5d76f…` / `6f5254c8…` / `f37956e4…`) and their
corpus digests stand (`2c37ba08…` / `14396eae…`); `cli
corpus-build` reproduces all four historical artifacts byte-for-
byte; the committed 1.0.0 / 1.1.0 no-capture baselines verify
against their corpora and refuse the 1.2.0 corpus; the 2.0-
context gate output is byte-identical to the committed 1.0.0
baseline; the 2.1/FU3 gate detail text is byte-unchanged; the
frozen FU2 / FU3 derivation + replay behavior is unchanged (the
R1 suite + the R2 historical-preservation rows); the DRAFT policy
is byte-identical (`6bc30d37…`) and still 1.0.0-scoped.

**Production firewall (evidence).** `V2_AUTHORITY_QUALIFIED` is
False in both pinned locations + the FU4 adapter's mirror (the
1.2.0 baselines record it False in both the contract and the
authority sections); the live record type still pins the 2.0 /
FU2 binding; `runtime_v2.py` byte-identical (the frozen 2.0
prompt axis); no live module references the FU4 qualification
harness (the new R2 reachability node) or the FU4 record surface
(the R1 guard stands over the new constant — the constant name is
`V2_1_FU4_CONTRACT_BINDING`, lexically distinct from the guard's
markers); the pricing-eligible tier set is unchanged (`NEEDS_
REVIEW` never pricing-eligible — import self-check); no prompt
2.0 / 2.1 text change (the 2.1 digest `e2949e75…` stands); no
Machine Price / Reviewed Price / pricing-eligibility change; no
database migration; no deployment; the FU3 DRAFT policy was NOT
copied into FU4 (no policy artifact for 1.2.0 exists — every
1.2.0 decision is POLICY_PENDING until the separately gated
policy step).

**Unresolved qualification gaps (explicit).** (1) Bundle-specific
FU4 authority qualification cases + acceptance criteria (the
committed corpus carries NO attested-composition case — the FU4
PROVEN path is exercised at the research / record level only; a
future separately approved corpus step + the 1.2.0-scoped
APPROVED policy, design section 5.6 / O-2); (2) the live 2.1/FU4
execution decision + the W1 atomic consumer guard (design O-3 —
ships with the FIRST pricing consumer); (3) the model capture over
1.2.0 (design O-4 — a separately gated live step after the policy
governance); (4) R1 + R1-FU1 remain pending independent review
(this R2 builds on their committed endpoint; ChatGPT reviews the
GitHub diff).

No deployment performed. A successful R2 is **infrastructure-
ready, not authority-qualified and not production-approved**.

**PRODUCT-INTEL.SEMANTIC-AUTHORITY-V2-Q3-B5-P5-R1-FU1 (Semantic
Authority V2 — Codec Integrity Test Contract Restoration, R1 test-
preservation correction)

— IMPLEMENTED / PENDING INDEPENDENT REVIEW**

Bounded TEST-PRESERVATION CORRECTION on the authoritative starting
SHA `60f548d404b39ac801f4c1963505ca36c160fea8` (the R1 endpoint;
baseline collection 7544, re-verified this session), restoring the
codec file-content integrity contract that the R1 node removal left
open. This is a test-file correction only: NO production
implementation change, NO R2, NO corpus / qualification / runtime /
pricing / deployment change, NO migration (`makemigrations --check
--dry-run`: No changes detected), NO Windows flake allowlist change.

**The gap (R1's removal left the codec unpinned at the file level).**
R1 removed the one parameterized A1 row
`test_frozen_module_is_byte_identical_to_the_starting_sha[product_\nintelligence/research/semantic_decision_codec.py-ef31ef38…]`
from `tests/research/test_semantic_authority_v2_fu4.py` (recorded at
design §1.7 / §10.1: the codec is no longer a frozen input of R1 —
it is the one production module R1 amended). The R1 record and the
removed row's own comment state that the codec's R1-endpoint
integrity "is pinned by the new R1 suite instead" — that claim was
NOT implemented. Verified before changing anything (the FU1
pre-change audit, item 7): no node in
`tests/research/test_semantic_decision_v2_fu4.py` — or anywhere else
in the tree — reads the codec file's bytes or compares its SHA-256
against a literal; the R1-suite nodes that reference the codec are
registry-identity assertions (`TestA1RegistrationState.
test_the_codec_registry_is_exactly_the_three_registered_bindings` —
the three-binding union, registration order, first-match pair
lookup) and a reachability-guard `allowed_paths` entry (`TestA1
RegistrationState.test_no_live_module_references_the_fu4_record_\nsurface`, line-level) — behavioral, not content-based. The R1-
endpoint digest `c0cef216…` appeared in no test or document; the
pre-R1 frozen digest `ef31ef38…` appears only in design §1.1 and in
the R1 STATUS record. The replacement R1 tests verify codec
behavior and registry identity but do not establish the same
file-content integrity contract: any post-R1 edit to
`semantic_decision_codec.py` passed the full 7544-node suite
silently.

**The correction (one new node, literal digest, no dynamic
computation).** `tests/research/test_semantic_decision_v2_fu4.py`
(`TestA1RegistrationState`, class A1 of the R1 suite — the recorded
home of the R1-endpoint pins for the R1-owned files) gains exactly
one node: `test_the_amended_codec_is_content_pinned_at_the_r1_\nendpoint`, plus the two module constants it uses (`CODEC_PATH`,
`CODEC_R1_ENDPOINT_DIGEST`) and one bullet in the file's docstring
(A1 section description). The node reads the actual codec file
(`product_intelligence/research/semantic_decision_codec.py`),
calculates its SHA-256, and compares against the LITERAL expected
digest `c0cef216d72e528ba8b17daa7adbb941f9ac328b42f02eb8dc4f00fdaa68\nbd3d` — the codec's content as committed at the starting SHA
`60f548d` (verified byte-identical to the working tree at FU1 start:
`git diff` clean on the file). The expected digest is recorded,
never computed from the file under test. **Why the expected digest
differs from the pre-R1 frozen digest** (recorded in the node's
docstring and the constant's comment): `ef31ef38ca5159c01cbfab9056a\ne20365c1dd58a8c6fb33b8f45f9f80a03b769` pinned the codec at R1's
starting SHA `de3dd95` (design §1.1) — the pre-amendment content.
R1 amended the codec (the DEC-9 claim-based disambiguation of the
decode dispatch — the claiming set on the full recorded five-axis
binding must be exactly one — plus the registry's third entry, the
FU4 adapter), so its R1-endpoint content is different by design;
`c0cef216…` is the SHA-256 of that exact committed endpoint. The
pin therefore moves from "frozen input at `de3dd95`" to "R1-endpoint
content at `60f548d`" — same safety property (any edit fails the
suite; a change requires an explicit, recorded re-pin), new
endpoint, recorded reason.

**What stands (no weakening, nothing removed).** (1) The original
A1 test's historical pins are preserved for ALL still-frozen files:
`FROZEN_MODULE_PINS` 18 → 17 rows — the AST-parsed diff between the
`de3dd95` and working-tree tables shows the codec row as the ONLY
removal, zero additions, zero value changes; `CORPUS_ARTIFACT_PINS`
(5) and `SUITE_FILE_PINS` (2) are byte-identical. The FU4 suite
file `tests/research/test_semantic_authority_v2_fu4.py` is
UNMODIFIED by FU1. (2) No existing registry, replay, authority, or
boundary assertion was touched — the R1 suite's 37 prior nodes, the
55-node codec suite, the 31-node replay suite, the boundary suites,
and the P1 binding-replay suite are all unedited and re-run below.
(3) The removed pre-R1 pin is NOT re-added to the frozen-input
table (it would fail by design — the codec is amended at R1);
its contract is replaced at the correct endpoint, as the task
mandates.

**Tests.** 1 NEW node (above). No other test change.

**Validation.** New node alone: 1 passed, 0 failed. R1 suite:
38 passed, 0 failed (37 + 1 new). Targeted preservation / codec /
replay / boundary runs: `test_semantic_authority_v2_fu4` 223 +
`test_semantic_decision_codec` 55 + `test_semantic_decision_replay`
31 + `test_semantic_decision_boundaries` 50 + `test_semantic_v2_\nboundaries` 32 + `test_semantic_decision_v2` 61 + `test_semantic_\ndecision_record` 47 + `test_q3b5_p1_binding_replay` 20 — 519
passed, 0 failed. **Safety property demonstrated**: a one-line
append to the codec file (a valid `# probe` comment — byte-level
tamper, never committed) made the new node FAIL with the recorded
message (`AssertionError: semantic_decision_codec.py differs from
its R1-endpoint content (commit 60f548d, digest c0cef216…); … a
change requires an explicit, recorded re-pin`); the file was
restored and verified byte-identical (SHA-256 `c0cef216…`, `git
diff` clean) before any suite run below. Full suite: 7545
collected — 7545 passed, 0 failed, exit 0 (zero collection errors).
Collection accounting (node-level diff against the 7544-node R1
baseline, collected before and after over the same working tree):
7544 → 7545; **added: exactly 1** — `tests/research/
test_semantic_decision_v2_fu4.py::TestA1RegistrationState::test_\nthe_amended_codec_is_content_pinned_at_the_r1_endpoint`; **removed:
0; renamed: 0**; no other file changed its node count. Skipped /
xfailed / deselected: **0 / 0 / 0**. No flake-class member failed;
the Windows flake allowlist is UNCHANGED (not expanded). `python
manage.py check`: System check identified no issues (0 silenced).
`python manage.py makemigrations --check --dry-run`: No changes
detected.

**Production runtime unchanged (evidence).** The only production-
file bytes touched during FU1 were the codec's, transiently, for
the safety-property probe — restored byte-identical and verified by
digest + `git diff` before the targeted and full runs. The codec
itself is the R1-endpoint content `c0cef216…` (unmodified by FU1);
the new node pins exactly that. `V2_AUTHORITY_QUALIFIED` remains
False in both pinned locations + the FU4 adapter's mirror; the
registry / replay unions, the 2.1/FU3 harness-only refusal, the
reachability firewall, and the historical V1 / V2 behavior
preservation proofs all stand (re-run above). No deployment
performed.

R1 (below) is ON HOLD pending this correction's independent review;
ChatGPT inspects the GitHub correction before approving R1.


**PRODUCT-INTEL.SEMANTIC-AUTHORITY-V2-Q3-B5-P5-R1 (Semantic Authority V2 —

FU4 Versioned Record, Codec and Replay Integration, the R1 record /
replay layer of the separately gated FU4 registration step)

— IMPLEMENTED / ON HOLD PENDING TEST-PRESERVATION CORRECTION (Q3-
B5-P5-R1-FU1: the R1 A1 codec-pin removal left the codec without a
file-content pin despite the recorded claim that the R1 suite pins
it; corrected in Q3-B5-P5-R1-FU1, recorded above) / PENDING
INDEPENDENT REVIEW (ChatGPT inspects the GitHub correction before
approving R1)**

Bounded RECORD/REPLAY-LAYER phase on the authoritative starting SHA
`de3dd950cd5386ffa03806984cb5f0c7a05340eb` (the Q3-B5-P5 design
endpoint; baseline collection 7500, re-verified this session),
executing the CONDITIONALLY APPROVED Q3-B5-P5 design
(`docs/PRODUCT_INTEL_Q3B5_P5_FU4_BINDING_REPLAY_QUALIFICATION_DESIGN.
md`, design §10.1 — sub-phase R1 of the separately gated registration
step, with ChatGPT's review amendments: the codec dispatch amendment
is claim-based disambiguation on the recorded five-axis binding — zero
claims fail closed, multiple claims fail closed, no adapter-failover
decoding, historical exact-binding checks intact). R1 makes FU4-bound
records PERSISTABLE, DECODEABLE, and REPLAYABLE through the universal
semantic-decision envelope, without changing historical FU2/FU3
interpretation and without enabling production authority. NO R2 (no
corpus 1.2.0, no harness extension, no semantic-layer binding
constant, no no-capture baselines), NO qualification, NO capture, NO
live execution, NO pricing, NO deployment, NO model call, NO migration
(`makemigrations --check --dry-run`: No changes detected). The frozen
inputs — the FU4 module, the FU2 / FU3 modules, the extraction module,
`semantic_v2.py`, the V1 / V2 adapters + record types, the envelope
foundation, the REPLAY module (digest `481f58ae…` byte-unchanged),
`contract_v2.py` / `contract_v2_1.py` / `runtime_v2.py`, the entire
harness, the corpus artifacts (1.0.0 / 1.1.0), the DRAFT policy — are
byte-unchanged (the FU4 A1 re-pin passes; `V2_AUTHORITY_QUALIFIED`
stays False in both pinned locations + the FU4 adapter's own mirror;
the live record type still pins the FU2 token; the production codec
still refuses the 2.1/FU3 harness-only binding; no live module
references the FU4 record surface — AST + lexical scan).

**The delivered component.** NEW
`product_intelligence/research/semantic_decision_v2_fu4.py` (research
layer; stdlib + the research package's public surface + the frozen
research contract modules; no Django, no I/O, no clock, no network,
no LLM, no mutable global state — import-self-checked and test-
scanned): the THIRD registered adapter at the codec's explicit
extension point, owning (1) the FU4 contract identity
`V2_FU4_CONTRACT_BINDING = ("V2","2.1",1,1,
"SEMANTIC_AUTHORITY_V2_S2A_FU4")` — composed from the frozen exports,
no literal token in source (the semantic-layer owner constant is the
R2 deliverable; the research mirror is drift-pinned by test against
the 2.1 prompt owner and the research exports — the P1 discipline),
moving ONLY the authority axis relative to the existing 2.1/FU3
binding; (2) the pinned route mirror (identical values to the V2
adapter — drift-pinned to the runtime); (3) the explicit
`V2_FU4_AUTHORITY_QUALIFIED = False` marker (the registration is NOT
a qualification); (4) the versioned evidence-schema pins (bundle-
composition evidence 3; extraction 1 — a superseded or unknown
document is undecodable); (5) the NEW typed record
`SemanticDecisionRecordV2FU4` — the V2 record's field set (universal
binding; the EXACT recorded V2 case — input schema 1, byte-identical
shape; the EXACT V2 evaluation / execution sections — output schema
1) with the FU4 exact-binding pin (a record bound to any other tuple
is un-constructible — FIND-2 / DEC-7), the V2 evaluation / execution
coherence rules (identical; the same route pin; the same attempt
discipline), the FU4 `derived` section values (the FULL
`AuthorityDecisionV2FU4` audit surface: tier, fired rules — the FU4
rule vocabulary —, product-evidence quality, relationship authority,
identity-resolution bound, sales-unit authority, + the six bundle-
axis audit fields — exactly None for non-bundle channels; the stored
section must be a VALID `AuthorityDecisionV2FU4` — the constructor
invariants run at record construction, so an AI_ASSISTED_COMPARABLE +
UNPROVEN / CONTRADICTED exposure is un-constructible, hence
undecodable), the NEW version-owned `authority` evidence fields
(`candidate_composition` — the v3 record, digest-bound, the
EXTRACTION_RESULT_V1 basis carrying the EXACT original
`SalesUnitExtractionResult` WITHIN its `evidence_digest`;
`target_evidence` — the explicit bounded `absent / frozen_fu3 /
fu4_v3` shape discriminator (DEC-8) — null = the default single unit,
"frozen_fu3" = the frozen FU3 record's three fields as recorded (read
as composition-ABSENT under FU4 — D18), "fu4_v3" = the versioned FU4
target record; `quantity_attestation` — the v3 review-constructed
attestation or null), and the self-verifying section digests
(`input_digest` = canonical over {binding, contract, case} — the
contract section carries the FU4 binding, so an FU4 input digest is
distinct from a same-case FU2 / FU3 input digest by exactly the
recorded authority axis — the binding is recorded INSIDE the input
digest: no historical record is upgradable to FU4; `output_digest` =
canonical over {evaluation, execution, authority, derived}); (6) the
strict FU4 payload codec (top-level `{schema_version, binding,
contract, case, evaluation, execution, derived, authority,
integrity}`; the case / evaluation / execution sections reuse the V2
adapter's strict decoders — byte-identical shapes; the evidence
documents decode field-by-field against their EXACT canonical key
sets (missing AND extra keys refused; unknown enums refused) into
TYPED records through the FU4 constructors (the constructor is the
validator — the schema pins, the state/coherence matrix, the basis /
extraction-digest coherence, the embedded-original integrity, and the
digest re-verification all fail closed), with the round-trip document
identity — the stored document must equal the reconstructed record's
encoding: no two documents, one record); (7) the FU4 pure zero-live
replay (reconstruction + the v3 presentation gate run BY THE
DERIVATION ITSELF — no private-gate re-implementation: the channel-
content-digest binding, the RECORDED_CHANNEL exact-construction
check, the four-step original-result chain — plus the FU4
re-derivation and the full derived-agreement proof over EVERY field
of the FU4 audit surface — any disagreement is a
`SemanticDecisionReplayError` naming the field; the human overlay is
NOT replayed, exactly as under the V2 replay); (8) the registered
instance `SEMANTIC_V2_FU4_ADAPTER` (envelope schema 1, semantic
contract "V2", `supported_bindings = (V2_FU4_CONTRACT_BINDING,)`,
record type = the FU4 record) — appended to the codec registry AFTER
the V2 adapter (registration order V1, V2, V2-FU4 preserved).

MODIFIED `semantic_decision_codec.py` — the ONE required versioned
amendment (FIND-1 / DEC-9, the design's §8.2): decode dispatch moves
from first-match-on-(envelope schema version, semantic contract
version) to CLAIM-BASED disambiguation on the FULL recorded five-axis
binding: the claiming set (registered adapters whose envelope version
matches and whose `supported_bindings` contain the recorded binding)
must be EXACTLY one; ZERO claims (unknown / future / cross-binding /
structurally malformed contract section — e.g. 2.1/FU3, 2.0/FU4,
misspelled / case / whitespace token variants) is refused with the
historical bounded "no registered contract adapter interprets this
payload" error; MORE THAN ONE claim (a registry inconsistency —
unreachable by construction: the bindings are disjoint) is refused
with a distinct bounded contract-registry-defect error. The universal
envelope framing, the no-float discipline, the single-adapter pair
lookup (first-match semantics KEPT — it is an introspection helper;
registration order keeps (1, "V2") resolving to the V2 adapter), and
the registry / encode / digest surfaces are otherwise unchanged.
Behavior-preserving by construction: for every payload that decodes
today (V1 or 2.0/FU2, well-formed or malformed) the claiming set is a
singleton — the same adapter is selected and the same error class is
raised (concrete proof: the R1 suite's byte-identical historical
round trips + the unchanged malformed-payload matrix). The rejected
alternative (an adapter-failover loop — decode-error masking,
non-deterministic failure stage) is NOT implemented. MODIFIED
`research/__init__.py` — the strictly additive FU4 adapter export
block (the FU3 / FU2 / V1 / V2 export blocks untouched). The replay
module is BYTE-UNCHANGED: its five-tuple gate + per-binding selection
already implement the post-amendment semantics — the derived union
picks up the third binding automatically; the persistence service and
the runs model need no change (they call the universal entry points
only).

**Tests.** 37 NEW nodes in the NEW file
`tests/research/test_semantic_decision_v2_fu4.py` implement the
mandated §9.1 integration matrix (rows 1–16) over the REAL codec /
replay entry points (never only direct FU4 research functions): (1)
FU2 / FU3 / FU4 binding coexistence — the codec / replay union is
exactly (V1, 2.0/FU2, 2.1/FU4), a forged fourth binding refused, the
2.1/FU3 harness-only binding still refused, the three-token
derivation coexistence (the SAME count-only inputs: PROVEN through
the FU3 arm, UNPROVEN through the FU4 arm, the FU2 arm refusing a
unit input as contract misuse); (2) unknown / future / misspelled /
case / whitespace authority tokens refused at the claim gate; (3)
unknown evidence schema (future 4) + superseded v2-shaped documents
refused; (4) the FU4 PROVEN_EQUIVALENT path over independently
attested complete compositions (candidate PUBLISHED statement +
target REVIEW attestation) through every satisfied quantity-axis
state (CONSISTENT / BOTH_UNPUBLISHED / ATTESTED_NOT_MATERIAL) — full
encode → decode → re-encode byte-identical → zero-live replay, the
audit fields RECORDED (never silent); (5) FU4 UNPROVEN over missing
evidence (count-only, composition ABSENT — over the frozen FU3
same-form target) and over incomplete evidence (SYNTACTICALLY_VALID —
completeness-unknown, no attestation) — the cap tier held, never the
automatic comparable; (6) FU4 CONTRADICTED over materially different
established compositions (U17) + the form axis over the default
single-unit target (U9, the corpus 0034 shape); (7) the count-only
bundle remains UNPROVEN under FU4 (the P2-FU1 rule survives
registration) while the SAME input preserves the historical FU3
behavior; (8) EXTRACTION_RESULT_V1 with the complete embedded
original result — the full document (schema_version 1, both digests,
every cue with its full provenance) inside the payload, round-
tripped, the genuine association replaying to PROVEN; (9) conflicting
secondary extraction cues — the genuine CONTRADICTED_PUBLISHED record
replays UNPROVEN; a self-consistent forged swapped-cue document is
accepted at decode (its own digests verify — the B12 pin) and
REFUSED at replay (the re-composition over the embedded original
differs); a state-incoherent dropped-cue document is refused at
decode; (10) missing embedded extraction result (un-constructible —
decode refuses both directions: EXTRACTION with null embedding;
RECORDED_CHANNEL with a non-null embedding); tampered embedded result
(cue field / stored result_digest / cue span — all refused); (11) the
wrong extraction result with the identical primary clause — the Q3-
B5-P4-FU2 false-PROVEN shape at record level: the self-consistent
forged EST document embedding the marker-FREE original decodes (the
digest alone proves nothing) and REPLAYS REFUSED (no unit derived
from it); the marker-free genuine record derives UNPROVEN; (12)
forged completeness attestation (digest/content mismatch — decode
refused) and forged quantity attestation (tampered digest — decode
refused; self-consistent wrong-subject-side attestation — decode
accepts, replay refuses); (13) wrong target-evidence discriminator
(unknown value — codec error naming the bounded set; extra key on the
frozen_fu3 document; non-reconstructing fu4_v3 document — all
refused; the valid frozen_fu3 document round-trips under its explicit
shape); (14) altered stored derived decision (the un-constructible
exposure — AI_ASSISTED_COMPARABLE + UNPROVEN with the ceiling
removed — refused at decode even with the section digest recomputed;
a constructible disagreement — altered quantity-axis state,
recomputed digest — decodes and is refused at replay NAMING the
field; a stale section digest — refused at decode); (15) payload
digest mismatch (stored input / output digests; the whole-artifact
anchor moves with any tamper); (16) the disambiguation gate itself
(the double-claim registry defect — injected by substitution —
refused with the registry-defect error, never first-match, for BOTH
the FU4 and the historical V2 bindings); plus historical V1 / V2
byte-identical encode/decode/replay over five fixtures (the DEC-9
behavior-preservation proof, concrete), the unchanged malformed-
payload matrix (unknown enum, stale digest, cross-contract names,
extra keys, float, unknown contract, the 2.1/FU3 refusal), zero-live
sentinels (armed fail-fast on the live runtime / transport / urlopen
surfaces over the FU4 AND historical payloads), and the exhaustive
restrict-only sweep over the FU4 decision type (no automatic
comparable tier for UNPROVEN / CONTRADICTED sales units — the
exposure un-constructible at the decision AND record level; the
ceilings fire only with their unit state on NEEDS_REVIEW; the
registered records hold NEEDS_REVIEW, never pricing-eligible). Every
case is an OFFLINE recorded-input construction — no live call, no
model capture, no network.

**Recorded test-file corrections (the P1 / P2-FU1 / Q3-B4-FU2 / Q3-
B5-P4-FU1 / FU2 precedent — in place, documented, names preserved,
intent preserved or strengthened; no test deleted, renamed, skipped,
xfail, deselected, ignored, or weakened — with the ONE recorded node
removal below).** (1) `test_semantic_authority_v2_fu4.py` A1: the
frozen-input pin table re-pins at R1's starting SHA EXCLUDING the
R1-owned codec (design §1.7) — the one parameterized pin row
(`test_frozen_module_is_byte_identical_to_the_starting_sha[product_
intelligence/research/semantic_decision_codec.py-ef31ef38…]`) is
REMOVED: the codec is no longer a frozen input (it is the amended
module of R1); its R1-endpoint integrity is pinned by the new R1
suite instead — 224 → 223 nodes, the only collection decrease in the
phase. The A3 FU3-suite pin extends from one recorded allow-line to
TWO (the FU3 reachability guard's `allowed_paths` recognizes the FU4
record adapter — the successor module must reference the FU3 frozen
target record + vocabulary by name to carry the derived audit
surface; the guard's stated safety property — "no production module
OUTSIDE the research contract surface references it" — is unchanged;
the pin proves the FU3 suite file equals its starting-SHA content
plus exactly those two recorded lines — no other byte). The A4 codec-
registry node re-pins `supported_contract_bindings()` from (V1,
2.0/FU2) to (V1, 2.0/FU2, 2.1/FU4) with the authority axes exactly
{FU2, FU4} and the 2.1/FU3 binding STILL absent. The A4 FU4-replay-
refusal node moves from "the gate refuses a FU4-bound payload" (pre-
registration) to "a raw FU4-bound object passes the gate and is
refused at the FU4 adapter's type gate (TypeError — only the FU4
record type decodes), while the V2 record type still cannot be re-
bound" (name + anti-reinterpretation intent preserved, strengthened).
The A4 qualification-marker node gains the FU4 adapter's mirror
(`V2_FU4_AUTHORITY_QUALIFIED is False`). The A4 reachability guard's
allowed surface gains the R1-owned adapter module (the design's "the
new adapter module joins the allowed research surface" — the live /
pricing / runtime exclusions stand). The E1 registry node re-pins the
union to exactly three (the harness registries, the committed 2.1
binding, and the marker assertions stand unchanged — the harness
extension is R2). The E2 node's docstring records the R1-registered /
R2-unregistered split (its harness-level assertions — no FU4 in the
seal registry, no 1.2.0 artifact, no fixtures constant — are
UNCHANGED and still hold). (2) `test_semantic_authority_v2_fu3.py`:
the reachability guard's `allowed_paths` set gains exactly one entry
— `research/semantic_decision_v2_fu4.py` — a single recorded line,
the same category as the Q3-B5-P4 FU4 allow-line (pinned line-exactly
by the updated A3 node above). (3) `test_q3b5_p1_binding_replay.py`:
the codec-registry node re-pins from "the 2.1/FU3 binding is NOT in
the union and 2.0/FU2 IS" to the EXACT three-binding union (V1,
2.0/FU2, 2.1/FU4) with 2.1/FU3 STILL absent (name preserved; strictly
more exact state); the FU3-payload-refusal node STAYS TRUE (still
refused, same error class) with its docstring recording the moved
failure point — the codec's binding-disambiguation gate (zero claims)
instead of the V2 adapter's strict check. (4) `test_semantic_
decision_codec.py`: `test_registry_lookup_is_explicit_and_fail_closed`
— the expected `supported_contract_bindings()` tuple gains the third
entry (V2, 2.1, 1, 1, FU4); the single-adapter pair lookups stand
(registration order keeps (1, "V2") → the V2 adapter); the FU4
adapter's binding pin is added. (5) `test_semantic_decision_replay.
py`: the exact-tuple node gains the third entry; the length pin moves
2 → 3; the future-bound-payload node's docstring records the moved
failure point (the zero-claim gate; error class unchanged). (6)
`test_semantic_decision_boundaries.py` (a mechanical discovery — the
design's §1.7 "verified by inspection" inventory enumerated four
suites and missed this node): `test_registry_is_the_explicit_version_
adapter_extension_point` — the registry length pin moves 2 → 3 with
`registry[2] is SEMANTIC_V2_FU4_ADAPTER` and the FU4 adapter's
identity pinned exactly (envelope 1, semantic contract V2, the one
FU4 binding; the envelope-version agreement extended to the third
adapter) — the same category as the §1.7 recorded corrections,
documented here.

**Validation.** Focused new file: 36 passed, 0 failed. Focused
preservation: the 223-node FU4 suite + the 98-node FU3 suite + the
111 + 7-node extraction suites — 439 passed, 0 failed (the A1 re-pin
passes — every still-frozen input byte-identical to the starting SHA
minus the R1-owned codec / export surface). Focused decision / replay
/ V2 / boundaries / P1 / persistence suites: 429 passed, 0 failed
(codec 55, replay 31, V2 61, record 47, decision-boundaries 50,
semantic_v2-boundaries 32, P1 binding-replay 20, persistence 33 — the
persistence service works unchanged through the amended codec: the
cross-contract reinterpretation refusals and the unregistered-
contract storage/interpretation distinction stand). Full suite (run
1): 7544 collected — 7544 passed, 0 failed, exit 0 (zero collection
errors). Full suite (run 2 — back-to-back, over the exact same code):
9 nodes failed — every one the documented load-sensitive clean-
interpreter subprocess guard flake class (`OSError: [WinError 6] The
handle is invalid` at `subprocess.Popen -> _winapi.DuplicateHandle`
BEFORE any project code runs; zero assertion failures) — the
documented multi-attempt behavior under sustained handle pressure
after back-to-back full runs (Q3-B5-P2-FU1): all 9 re-passed isolated
one-node-per-process (6 on the first spaced attempt, the remaining 3
on spaced retry); no non-flake node failed in either run. Collection
accounting (node-level diff against the starting SHA, verified over an
independent linked worktree at `de3dd95`, removed after use):
7500 → 7544 (+44 = +37 new-file nodes + 8 auto-expanded parameterized
boundary scans for the new research file [research-core per-file x4,
domain +1, providers +1, runs +1, web +1] − 1 the recorded A1 codec-
pin row — the only removal; **0 other nodes removed / 0 renamed**;
per-file: `test_domain_boundaries` 58→59, `test_provider_boundaries`
169→170, `test_research_identity_boundaries` 157→161, `test_semantic_
authority_v2_fu4` 224→223, `test_semantic_decision_v2_fu4` 0→37,
`test_research_run_boundaries` 104→105, `test_web_boundaries` 182→183
— no other file changed its node count). Skipped / xfailed /
deselected: **0 / 0 / 0**. `python manage.py check`: System check
identified no issues (0 silenced). `python manage.py
makemigrations --check --dry-run`: No changes detected (no model
change — the registration is pure research layer + tests + documents
at R1).

**Production runtime and pricing remain unchanged (evidence).** The
frozen files are digest-pinned by the re-pinned A1 nodes (FU2 / FU3 /
P2 extraction / S2-C / decision / REPLAY / 2.0 / 2.1 / runtime /
harness modules, the corpus artifacts, the DRAFT policy — byte-
identical to the starting SHA; the replay module's digest is
unchanged — it needed NO change: its five-tuple gate + per-binding
selection already implement the post-amendment semantics); the
production codec registry now knows exactly the V1 + 2.0/FU2 +
2.1/FU4 bindings (the 2.1/FU3 harness-only binding is still refused);
the live record type still pins the FU2 token (a V2 record re-bound to
FU4 is un-constructible); `V2_AUTHORITY_QUALIFIED` is False in both
pinned locations + the FU4 adapter's mirror; no live module
(semantic / execution / runs / web / providers) references the FU4
record surface (AST + lexical scan — the R1 suite's A1 nodes, and the
FU4 suite's extended A4 reachability guard); the pricing-eligible tier
set is unchanged and the cap tier (NEEDS_REVIEW) remains non-pricing-
eligible (the exhaustive restrict-only sweep over the FU4 decision
type + the record-level constructor invariants); the historical V1 /
V2 payloads decode / replay / re-encode byte-identically (the R1
suite's A2 rows — the DEC-9 behavior-preservation proof, concrete).
Nothing in R1 activates V2 authority, connects any derivation to
pricing, or wires a live path: the separately gated R2 (the semantic-
layer binding constant, the corpus 1.2.0 binding-only re-seal, the
harness registry extension, the no-capture baselines) remains
unexecuted; qualification under the FU4 binding is a separate
governance event with its own marker flip + consumer guard (AD-Q3B4-
6 / W1).

No deployment performed.




**PRODUCT-INTEL.SEMANTIC-AUTHORITY-V2-Q3-B5-P4-FU2 (Semantic Authority V2 —

Extraction Evidence Association Closure, S2-A-FU4 correction)

— IMPLEMENTED / PENDING INDEPENDENT REVIEW**

Bounded SAFETY-CORRECTION phase on the authoritative starting SHA
`7791a65405094f5ddb30d5d5b1d904f05affe1bb` (the Q3-B5-P4-FU1
correction endpoint; baseline collection 7487, re-verified this
session), closing the remaining EXTRACTION_RESULT_V1 evidence-
association gap identified by ChatGPT's independent GitHub source
review of Q3-B5-P4-FU1. This is a bounded correction, not a new
feature phase. CONTRACT CORRECTION ONLY: NO live integration, NO V2
authority activation, NO pricing change, NO corpus label change, NO
benchmark capture, NO deployment, NO model call, NO migration
(`makemigrations --check --dry-run`: no changes detected). The frozen
inputs — the FU2 / FU3 modules, the S2-C-FU1 channel,
`sales_unit_extraction.py` (schema v1), the Prompt 2.0 / 2.1
contracts, the codec / replay / harness registries — are byte-
unchanged (the A1 digest pins pass; the only production file touched
is the FU4-owned pending-review module `research/
semantic_authority_fu4.py`, plus its test file and the two design /
status documents). `V2_AUTHORITY_QUALIFIED` stays False in both
pinned locations; the production codec still refuses an FU4-bound
payload; the FU3 / FU2 dispatch arms delegate to the frozen
derivations byte-identically (the A2 delegation-identity pins pass
unchanged).

**The gap — the channel content binds the projection, not the result.**
The version-2 `channel_content_digest` correctly binds the MAPPED
CHANNEL, but the frozen S2-C channel is a LOSSY projection of the
extraction result: it carries only the primary established cue's
published text (`raw_detail`), never the full result's additional
cues, its contradiction state, or the continuation completeness
marker that may sit in the recorded field text BEYOND `raw_detail`
(the frozen cue engine's colon-form span stops at the first comma /
semicolon / closing paren). The version-2 gate therefore verified
only the record's primary clause against the presented channel's
`raw_detail` (primary-clause-only validation): a self-consistent,
hand-forged EXTRACTION-basis record could carry an ESTABLISHED
composition (a completeness attestation the presented publication
never made) or a CONTRADICTED_PUBLISHED state with additional
clauses (cue facts the presented publication never published)
whenever its primary clause and the channel content agreed — its
`extraction_result_digest` / `extraction_input_digest` were
unverified self-claims. Demonstrated over the starting-SHA v2 code:
the gate derived PROVEN_EQUIVALENT for a marker-free publication
presented with a forged self-consistent EST record over an
attested-equal target (false PROVEN; the restrict-only ceiling never
fired).

**The correction — the smallest versioned amendment (the design's T5
/ T9 discipline: any change is a new version, never a silent edit;
the frozen S2-C channel is byte-frozen and cannot carry the back-
reference, so the association is expressed on the FU4 record's side,
as in FU1; the derivation / dispatch / case-level SIGNATURES are
UNCHANGED — no new derivation input: the association travels with
the record, pinned by the unchanged C8 / F1 signature nodes):** the
versioned bundle-composition evidence schema moves to **v3**
(`BUNDLE_COMPOSITION_EVIDENCE_VERSION_FU4 = 3`; v2 records are
un-constructible — a superseded schema version is never silently
reinterpreted). The EXTRACTION_RESULT_V1 candidate record gains ONE
field, `extraction_result` — the EXACT original
`SalesUnitExtractionResult` (frozen schema v1) it was constructed
from: the bounded proof carrying ALL authority-relevant extraction
facts (every recorded cue with its full provenance — field / source
/ verbatim field text / span / kind / disposition / reason — the
result's state, its established unit, and both of its self-verifying
digests), embedded inside the record's `evidence_digest` (a tampered
embedding breaks the record's own verification). The RECORDED_
CHANNEL record carries exactly None. The constructor is the
validator (fail closed): an EXTRACTION record whose original result
is missing is un-constructible; the stored anchors must equal the
embedded result's own digests (a forged anchor is an integrity
error); the embedded result must pass its OWN integrity
verification; it must be OBSERVED BUNDLE; `channel_quantity` must be
its `established_quantity`. The derivation's presentation gate re-
proves the association INDEPENDENTLY at derivation time over the
embedded original — **never a fallback to primary-clause-only
validation**, and **no self-consistent, caller-reconstructed digest
in place of trusted recorded evidence provenance**: (1) the embedded
result's OWN integrity (BOTH stored digests recomputed — a tampered
or altered original is refused); (2) the record's stored extraction
digest anchors equal the embedded result's digests; (3) the FROZEN
P2 mapping `sales_unit_channel_from_extraction` of that exact result
EQUALS the presented channel (full channel equality — a wrong
extraction result, whose mapping is not the presented publication, is
refused); (4) the candidate composition RECOMPUTED from that exact
result equals the COMPLETE presented record — state, clauses,
attestations, and provenance (a hand-forged or altered record is
refused even when self-consistent). **The RECORDED_CHANNEL
validation is INTACT** (the exact-construction + channel-content-
binding checks stand; the source / quantity / provenance checks and
the attestation verifications all stand; the version-2
`channel_content_digest` binding is preserved inside the record).
Full published provenance is preserved — the new field is inside the
record's digest; missing provenance is never invented or
reconstructed.

**Documented bound (the frozen channel's granularity).** The channel
association is proven over the channel CONTENT (state / kind /
quantity / raw_detail / source): two distinct publications whose
recorded channels are content-identical (differing only beyond the
primary cue's span — e.g. a continuation marker, or a secondary cue)
are indistinguishable at the frozen channel level (the S2-C channel
cannot carry the input identity, and the frozen channel is not
modified). Over that bound, every authority-relevant fact of the
record is proven to be exactly the fact of its embedded, self-
consistent original result; the dangerous direction (a record
claiming facts its embedded original does not support — a forged
attestation, a swapped / dropped secondary cue) is closed. The bound
is pinned by the B12 rows.

**Recorded test-file corrections (the P2-FU1 / Q3-B4-FU2 / FU1
precedent — in place, documented, names preserved, intent preserved;
no test deleted, renamed, skipped, xfailed, deselected, ignored, or
weakened).** (1) The schema-version pin (A2
`test_the_fu4_token_is_separately_versioned`) moves 2 → 3 and the
unknown-version node (B9
`test_a_unknown_schema_version_is_unconstructible`) moves its unknown
value 3 → 4 — the mechanical consequence of the versioned amendment
(the same category as the FU1 / Q3-B4-FU2 pin updates). (2) The two
direct positional record constructions (B4
`test_candidate_record_refuses_non_extractor_sources`, B5
`test_construction_reverifies_the_digest`) gain the one new field
(None — the RECORDED_CHANNEL basis). (3) The record helper
`_make_candidate_record` gains the `extraction_result` mirror
parameter (default None; inside the mirrored canonical document).
(4) **The B11 hand-forged EXTRACTION record row is aligned to the
corrected binding** (`test_a_handforged_extraction_record_cannot_
claim_a_foreign_clause`): a v3 hand-forged EXTRACTION record must
embed a real self-consistent result, so the fixture now embeds the
actual result whose FROZEN P2 mapping equals the presented channel
(the strongest possible forgery — every version-2 check passes,
including its own digests and anchors), while still claiming a clause
/ state the embedded original never determined; the name, the
asserted refusal, and the intent are preserved — the refusal now
fires at the v3 re-composition check ("not the exact construction")
instead of the superseded primary-clause check. Every other node
keeps its name, its asserted unit / tier / rule expectations, and its
intent — all 211 baseline nodes pass unchanged over the v3 schema.

**Tests.** 13 NEW nodes in the NEW class
`TestB12ExtractionResultAssociationFU2` (in
`tests/research/test_semantic_authority_v2_fu4.py`) implement the
mandated adversarial matrix over the corrected gate: the extraction
record embeds the exact original result (anchor + proof inside the
evidence digest; an out-of-band field tamper of the embedding breaks
the record's own verification); identical primary clause but
different secondary cues (the genuine CONTRADICTED_PUBLISHED record
stands over its own mapped channel — UNPROVEN over every bundle
target, the form rule over non-bundle — a forged swapped secondary
cue over listing B's content-identical channel is refused, a forged
dropped-cue record is refused, and the frozen-channel content bound
is pinned: a GENUINE record from one content-identical publication
stands over the other's channel and still fails closed); conflicting
title / structured clauses (the genuine record stands over its own
mapped channel — the channel presents only the primary clause, the
title clause is the embedded original's additional cue — a forged
dropped-side record and a forged side-swapped record are both
refused); continuation completeness marker present vs absent (the
genuine EST record stands over its own mapped channel — PROVEN over
the attested-equal target — a forged self-consistent EST record
embedding the marker-FREE original, claiming an attestation the
publication never made, is REFUSED — the version-2 gate derived
PROVEN_EQUIVALENT over exactly this shape, the false-PROVEN defect —
and the marker-free record derives UNPROVEN); missing extraction
result (un-constructible at the type level; an out-of-band removal of
the embedding is refused at the gate); wrong extraction result with a
matching mapped channel (the strongest wrong-result forgery —
claiming ESTABLISHED + attestation, or claiming an additional clause
the embedded original never published — refused at the re-composition
over the exact result); wrong extraction result with a mismatched
mapping (a self-consistent record whose embedded original maps to a
different channel, its content digest forged to the presented
channel's — the explicit frozen-P2-mapping check fires); tampered
extraction result (a stored result_digest tamper NOT covered by the
embedding's canonical — the record's own evidence digest still
verifies — is caught by the gate's own re-verification of the
embedded original's integrity; a field tamper is caught by the
record's own digest; the constructor refuses a tampered result);
forged extraction digest (a self-consistent record whose stored
anchors do not match the embedded original's own digests is un-
constructible — a forged anchor is an integrity error; the gate-side
out-of-band anchor tamper stands refused); valid same-result replay
(the byte-equal re-extraction constructs the byte-equal record; the
association stands over the mapped channel and over a separately
constructed content-equal channel — full equality by value; the
same presentation re-derives the same unit); superseded-v2 un-
constructibility (a v2 record — no embedded original — is un-
constructible); the RECORDED_CHANNEL validation intact (the exact-
construction refusal stands; a RECORDED record carries no embedding;
the basis coherence is un-constructible); and FU2 / FU3 unchanged +
the FU4 tier ceilings unchanged over v3 (the historical dispatch
arms still refuse a v3 composition input as contract misuse — the
delegation identity pins stand — attested-equal stands at
AI_ASSISTED_COMPARABLE, the unattested twin is capped at
NEEDS_REVIEW with CEILING_SALES_UNIT_NOT_PROVEN). Every case is an
OFFLINE recorded-input construction — no live call, no model
capture, no network.

**Validation.** Focused new file: 224 passed, 0 failed (211 baseline
+ 13 new). Focused preservation: the 98-node FU3 suite + the 111 +
7-node P2 / P2-FU1 extraction suites — 216 passed, 0 failed (the A1
frozen-file pins pass — every frozen input byte-identical to the
starting SHA). Focused `tests/research/`: 3296 nodes — 3293 passed,
3 failed; the 3 failures are EXACTLY the documented load-sensitive
clean-interpreter subprocess guard flake class (every one
`OSError: [WinError 6]` at `subprocess.Popen` BEFORE any project code
runs; zero assertion failures), all re-passed isolated one-node-per-
process. Focused `tests/semantic/` + `tests/evaluation/`: 1336
nodes — 1336 passed, 0 failed. Full suite (run 1): 7500 collected —
7489 passed, 11 failed — the 11 failures are EXACTLY the fixed
eleven-node load-sensitive clean-interpreter subprocess guard flake
allowlist (every one `OSError: [WinError 6]` ×2 / `[WinError 50]` ×9
at `subprocess.Popen -> _winapi.DuplicateHandle` BEFORE any project
code runs; zero assertion failures), all 11 re-passed isolated
one-node-per-process on the first attempt. Full suite (run 2):
7500 collected — 7498 passed, 2 failed — both the same flake class
(`OSError: [WinError 6]` at Popen; zero assertion failures), both
re-passed isolated on the first attempt. Full suite (run 3 — FINAL,
over the exact committed code): 7500 collected — 7489 passed, 11
failed — again EXACTLY the same fixed eleven-node flake allowlist
(`OSError: [WinError 50]` ×9 / `[WinError 6]` ×2 at Popen; zero
assertion failures), all 11 re-passed isolated one-node-per-process
on the first attempt; no non-flake node failed in any run (the flake
class is the documented multi-attempt behavior under sustained handle
pressure after back-to-back full runs — Q3-B5-P2-FU1). Collection
accounting:
7487 → 7500 (+13 — the B12 class; node-level diff against the
starting SHA: **0 nodes removed / 0 renamed** — the only changed
file is the FU4 test file, 211 → 224). Skipped / xfailed /
deselected: **0 / 0 / 0**. `python manage.py check`: System check
identified no issues (0 silenced). `python manage.py
makemigrations --check --dry-run`: No changes detected (no model
change — the correction is pure research layer + tests + documents).

**Production runtime and pricing remain unchanged (evidence).** The
frozen files are digest-pinned by the unchanged A1 nodes (FU2 / FU3
/ P2 extraction / S2-C / decision / codec / replay / 2.0 / 2.1 /
runtime / harness modules, the corpus artifacts, the DRAFT policy —
byte-identical to the starting SHA); the production codec registry
still knows exactly the V1 + 2.0/FU2 bindings and refuses an FU4-
bound payload; the replay registry is the same union; the harness
knows exactly the two production bindings and no corpus 1.2.0
artifact exists; the live record type still pins the FU2 token;
`V2_AUTHORITY_QUALIFIED` is False in both pinned locations; no live
module references the FU4 surface (the unchanged A4 AST + lexical
scan passes); the pricing-eligible tier set is unchanged and the
cap tier remains non-pricing-eligible; the derivation / dispatch /
case-level signatures are unchanged (the C8 / F1 signature pins
pass). Nothing in the phase registers, re-seals, activates, or
wires; the separately gated FU4 registration step (design §7.3)
remains unexecuted — it will register the v3 schema, not the
superseded v1 / v2.

No deployment performed.


**PRODUCT-INTEL.SEMANTIC-AUTHORITY-V2-Q3-B5-P4-FU1 (Semantic Authority V2 —

Candidate Evidence Binding Integrity, S2-A-FU4 correction)

— IMPLEMENTED / CORRECTED BY Q3-B5-P4-FU2 (EXTRACTION EVIDENCE
ASSOCIATION CLOSURE) / PENDING FINAL REVIEW (the independent GitHub
source review identified the remaining EXTRACTION_RESULT_V1 evidence-
association gap — the channel-content digest binds the mapped channel
but does not prove the full extraction result's additional cues,
contradiction state, or continuation completeness marker; corrected
in Q3-B5-P4-FU2, recorded above)**

Bounded SAFETY-CORRECTION phase on the authoritative starting SHA
`7deb22e7261dad0f086645084dd311608059e48b` (the Q3-B5-P4 contract-
only endpoint; baseline collection 7474, re-verified this session),
correcting the two defects found by the independent GitHub source
review of Q3-B5-P4. This is a bounded correction, not a new feature
phase. CONTRACT CORRECTION ONLY: NO live integration, NO V2 authority
activation, NO pricing change, NO corpus label change, NO benchmark
capture, NO deployment, NO model call, NO migration
(`makemigrations --check --dry-run`: no changes detected). The frozen
inputs — the FU2 / FU3 modules, the S2-C-FU1 channel,
`sales_unit_extraction.py` (schema v1), the Prompt 2.0 / 2.1
contracts, the codec / replay / harness registries — are byte-
unchanged (the A1 digest pins pass; the only production file touched
is the FU4-owned pending-review module `research/
semantic_authority_fu4.py`, plus its test file and the two design /
status documents). `V2_AUTHORITY_QUALIFIED` stays False in both
pinned locations; the production codec still refuses an FU4-bound
payload; the FU3 / FU2 dispatch arms delegate to the frozen
derivations byte-identically (the A2 delegation-identity pins pass
unchanged).

**Blocker 1 — cross-listing composition evidence substitution.** The
FU4 presentation gate (`_verify_candidate_composition`) checked the
candidate record's source class and published quantity against the
presented channel, but did not establish that the composition evidence
belongs to the EXACT presented candidate publication: a record built
from listing A's channel / extraction result was accepted over
listing B's channel whenever source class, bundle form, and quantity
agreed (a self-verifying digest is not proof of cross-record
association). Corrected by the **smallest versioned amendment to the
FU4 evidence schema — v2** (the design's T5 / T9 discipline: any
change is a new version, never a silent edit; the frozen S2-C-FU1
channel cannot carry the back-reference — it is byte-frozen — but the
FU4 schema is versioned for exactly this, and the association it
cannot express on its side is expressed on the FU4 record's side):
the candidate record gains ONE field, `channel_content_digest` —
SHA-256 over the frozen channel's canonical document (state / kind /
quantity / raw_detail / source) of the EXACT channel content the
record was constructed from (RECORDED_CHANNEL basis: the passed
channel; EXTRACTION_RESULT_V1 basis: the frozen P2 mapping
`sales_unit_channel_from_extraction(result)` of the verified result —
the verifiable relationship extraction result → mapped channel →
record). `BUNDLE_COMPOSITION_EVIDENCE_VERSION_FU4` moves 1 → 2; v1
records are un-constructible (a superseded schema version is never
silently reinterpreted). The presentation gate re-verifies the
association at DERIVATION TIME (the unit, case-level, and tier
derivations all route through it): (a) the presented channel's
canonical content digest must equal the record's — composition
evidence originating from another listing is refused even when source
class, bundle form, and quantity are identical; (b) a RECORDED_
CHANNEL record must be EXACTLY the construction of the presented
channel (the record is a pure function of that channel — a
hand-forged, self-verifying record claiming a clause / state /
attestation the presented publication never made is refused);
(c) an EXTRACTION_RESULT_V1 record's primary clause must be the
determined form of the presented channel's published `raw_detail`
(the continuation attestation text may sit beyond `raw_detail` —
AUDIT-ONLY, never compared). Full published provenance and integrity
evidence are preserved (the source / quantity / digest checks and the
attestation verifications all stand; the new field is inside the
record's `evidence_digest`). Missing provenance is never invented or
reconstructed: the digest is computed at construction over the exact
input, and the gate verifies the recorded association rather than
re-deriving it.

**Blocker 2 — integer identity comparison.** The gate compared the
record's published `channel_quantity` against the channel's
`quantity` with object identity (`is not`): two separately
deserialized (or otherwise separately constructed) equal quantities
greater than 256 are distinct `int` objects, so a valid same-
publication record was refused (only small-int interning masked the
defect). Corrected to exact value equality (`!=`). Audit of the
related identity comparisons: every remaining `is` / `is not` in the
FU4 module is an enum single-identity check (correct — enum members
are singletons) or a strict `type(x) is int` bound check; no other
integer value uses identity comparison (the quantity axis already
compared by value, `==`). The frozen modules were audited too: their
quantity comparisons are None checks / `type(...) is int` bounds /
value `==` — no defect of this class exists outside the FU4 module
(nor is anything frozen touched).

**Recorded test-file corrections (the P2-FU1 / Q3-B4-FU2 precedent —
in place, documented, names preserved, intent preserved; no test
deleted, renamed, skipped, xfailed, deselected, ignored, or
weakened).** (1) The schema-version pin (A2
`test_the_fu4_token_is_separately_versioned`) moves 1 → 2 and the
unknown-version node (B9
`test_a_unknown_schema_version_is_unconstructible`) moves its unknown
value 2 → 3 — the mechanical consequence of the versioned amendment
(the same category as the Q3-B4-FU2 pin update). (2) The two direct
positional record constructions (B4
`test_candidate_record_refuses_non_extractor_sources`, B5
`test_construction_reverifies_the_digest`) gain the one new field.
(3) The record helpers bind to the canonical channel their
presentation targets: `_make_candidate_record` defaults
`channel_content_digest` to the digest of the OBSERVED BUNDLE channel
with the record's source / quantity / corpus-shaped raw_detail, and
`_candidate_established` now CONSTRUCTS (not hand-builds) over its
marker-carrying channel (`_candidate_established_channel` — NEW
helper; the published completeness statement is part of the
presented publication's raw_detail). (4) **The fixture CONSTRUCTIONS
of the affected derivation call-sites are aligned to the corrected
binding** (the recorded defect, demonstrated): they previously
presented a record built from / claiming an ESTABLISHED (marker-
carrying) publication OVER a marker-free channel — i.e. the very
cross-listing substitution the review found (notably
`test_attested_equal_with_an_asymmetric_quantity_gap_proves_with_the_`-
`attestation`, `test_the_constructible_copied_shape_derives_per_the_`-
`axes`, `test_the_attestation_text_is_never_read_by_the_derivation`,
and the B1 / B6 / B7 / B8 / B10 / C1 / C3–C12 / D1 / F4 rows, each
now presenting the record's OWN channel). Every such node keeps its
name, its asserted unit / tier / rule expectations, and its intent —
the record and the channel it is presented over are now the SAME
publication (for the EXTRACTION-basis rows, the record's own mapped
channel: B1 `test_a_truncated_copublication...`, C6
`test_conflicting_published_contents...`).

**Tests.** 13 NEW nodes in the NEW class
`TestB11ChannelContentBindingFU1` (in
`tests/research/test_semantic_authority_v2_fu4.py`) implement the
mandated adversarial matrix over the corrected gate: identical
source + quantity / different raw_detail (RECORDED_CHANNEL basis —
refused; over its own listing — stands); listing-A EXTRACTION record
over listing-B's mapped channel (identical source class / bundle form
/ quantity — refused); two separately deserialized channels with
equal quantity 300 > 256 (distinct `int` objects — the premise is
pinned — derive per value equality, no spurious refusal, both the
SV/ABSENT UNPROVEN row and the ESTABLISHED/PROVEN row); equal
quantity but different composition (material ⇒ CONTRADICTED both
ESTABLISHED; one side unattested ⇒ UNPROVEN); tampered channel
provenance (refused — the pre-existing source-check node stands
unchanged); tampered extraction-result association (out-of-band
`extraction_result_digest` tamper refused by the record's own
evidence digest at the gate; a foreign result's record over this
mapped channel refused by the mapped-channel association); valid same-
listing channel + composition (both bases derive per the axes — no
spurious refusal); count-only bundle remains UNPROVEN (the P2-FU1
rule survives the binding); the historical FU3 replay is unchanged
(the frozen count-based derivation still derives PROVEN over the same
inputs — the coexistence pin, A7, stands); the FU4 MATCH / HIGH /
STRONG ceiling is unchanged (attested-equal stands at AI_ASSISTED_
COMPARABLE; the unattested twin is capped at NEEDS_REVIEW with
CEILING_SALES_UNIT_NOT_PROVEN); constructor-time integrity
enforcement (a malformed `channel_content_digest` is un-
constructible; an out-of-band tamper of the binding is refused at
the gate); and the two forgery rows the digest alone cannot close
(a self-verifying hand-forged RECORDED_CHANNEL record claiming an
ESTABLISHED composition a count-only publication never made —
refused by the exact-construction requirement; a hand-forged
EXTRACTION-basis record with fabricated self-verifying extraction
digests claiming a clause the presented raw_detail never determines
— refused by the primary-clause requirement). Every case is an
OFFLINE recorded-input construction — no live call, no model capture,
no network.

**Validation.** Focused new file: 211 passed, 0 failed (198 baseline
+ 13 new). Focused preservation: the 98-node FU3 suite + the 111 +
7-node P2 / P2-FU1 extraction suites — 216 passed, 0 failed (the A1
frozen-file pins pass — every frozen input byte-identical to the
starting SHA). Focused `tests/research/`: 3283 nodes — 3278 passed,
5 failed; the 5 failures are EXACTLY the documented load-sensitive
clean-interpreter subprocess guard flake class (every one
`OSError: [WinError 6]` at `subprocess.Popen` BEFORE any project code
runs; zero assertion failures), all re-passed isolated one-node-per-
process on the first attempt. Focused `tests/semantic/` +
`tests/evaluation/`: 1379 nodes — 1335 passed, 1 failed — the single
failure is the same flake class (`tests/evaluation/
test_evaluation_boundaries.py::test_loading_the_corpus_imports_no_`-
`framework_or_provider`), re-passed isolated on the first attempt.
Full suite (first run over the committed code): 7487 collected —
7486 passed, 1 failed — the single failure the same subprocess flake
class (`tests/domain/test_domain_boundaries.py::test_domain_imports_`
`without_django_network_or_llm_dependencies`, `OSError [WinError 6]`
at Popen, zero assertion failures), re-passed isolated on the first
attempt. Full suite (FINAL run): **7487 collected; 7487 passed, 0
failed** — no flake-class member failed in the final run; zero
collection errors. Collection accounting: 7474 → 7487 (+13 — the B11
class; node-level diff against the starting SHA: **0 nodes removed /
0 renamed** — the only changed file is the FU4 test file, 198 → 211).
Skipped / xfailed / deselected: **0 / 0 / 0**. `python manage.py
check`: System check identified no issues (0 silenced). `python
manage.py makemigrations --check --dry-run`: No changes detected (no
model change — the correction is pure research layer + tests +
documents).

**Production runtime and pricing remain unchanged (evidence).** The
frozen files are digest-pinned by the unchanged A1 nodes (FU2 / FU3 /
P2 extraction / S2-C / decision / codec / replay / 2.0 / 2.1 /
runtime / harness modules, the corpus artifacts, the DRAFT policy —
byte-identical to the starting SHA); the production codec registry
still knows exactly the V1 + 2.0/FU2 bindings and refuses an FU4-
bound payload; the replay registry is the same union; the harness
knows exactly the two production bindings and no corpus 1.2.0
artifact exists; the live record type still pins the FU2 token;
`V2_AUTHORITY_QUALIFIED` is False in both pinned locations; no live
module references the FU4 surface (the unchanged A4 AST + lexical
scan passes); the pricing-eligible tier set is unchanged and the
cap tier remains non-pricing-eligible. Nothing in the phase
registers, re-seals, activates, or wires; the separately gated FU4
registration step (design §7.3) remains unexecuted — it will
register the v2 schema, not the superseded v1.

No deployment performed.


**PRODUCT-INTEL.SEMANTIC-AUTHORITY-V2-Q3-B5-P4 (Semantic Authority V2 —

Versioned Bundle Composition Authority Contract, S2-A-FU4)

— IMPLEMENTED / CORRECTED BY Q3-B5-P4-FU1 (CANDIDATE EVIDENCE BINDING
INTEGRITY) / PENDING FINAL REVIEW (the independent GitHub source
review identified two safety defects — cross-listing composition
evidence substitution over the presented channel, and an integer
identity comparison of published quantities; both corrected in
Q3-B5-P4-FU1, recorded above)**

Bounded CONTRACT-ONLY phase on the authoritative starting SHA
`bc12c4a36e4dd4bef85a958b6e7406ca1c87361f` (the Q3-B5-P3-FU1 design
endpoint; baseline collection 7268, re-verified this session). It
implements the approved, CORRECTED Q3-B5-P3 bundle-composition authority
design (`docs/PRODUCT_INTEL_Q3B5_P3_BUNDLE_COMPOSITION_DESIGN.md` —
Blocker A quantity completeness, Blocker B composition completeness) as
an isolated, deterministic, versioned research contract: the separately
versioned authority token `SEMANTIC_AUTHORITY_V2_S2A_FU4` and, behind
that token ONLY, the versioned bundle-composition evidence schema (v1),
the corrected D6 conjunction (composition ESTABLISHED on both sides via
independent attestations + textual agreement + a determined quantity
axis), the FU4 decision record with the bounded bundle-axis audit
fields, and the FU4 superset dispatch. NO implementation of the
pre-revision (superseded) rules. CONTRACT ONLY: NO live integration, NO
binding registration (codec / replay / harness registries byte-
unchanged — an FU4-bound payload is refused by the production codec and
replay registry, pinned), NO corpus 1.2.0 (no artifact exists; the
harness knows exactly the two production bindings), NO V2 authority
activation (`V2_AUTHORITY_QUALIFIED` False in both pinned locations), NO
pricing change (the cap tier stays non-pricing-eligible; the aggregation
surface owns no FU4 symbol), NO corpus label change, NO benchmark
capture, NO deployment, NO model call, NO migration
(`makemigrations --check --dry-run`: no changes detected).

**The delivered component.** NEW
`product_intelligence/research/semantic_authority_fu4.py` (research
layer; stdlib + the research package's public surface + the frozen FU3 /
FU2 / S2-C / extraction modules; no Django, no I/O, no clock, no
network, no LLM, no mutable global state — import-self-checked):

* The token `AUTHORITY_CONTRACT_VERSION_V2_FU4` +
  `KNOWN_AUTHORITY_CONTRACT_TOKENS_FU4` (= exactly {FU2, FU3, FU4}; the
  frozen FU3 constant stays exactly {FU2, FU3});
  `BUNDLE_COMPOSITION_EVIDENCE_VERSION_FU4 = 1`.
* The CORRECTED five-way composition-state vocabulary
  (`SYNTACTICALLY_VALID` / `ESTABLISHED` / `PARTIAL` / `ABSENT` /
  `CONTRADICTED_PUBLISHED`) — syntactic closure demoted to a textual
  property; `ESTABLISHED` redefined as attested-complete (D4 / D19).
* The two attestation records (self-verifying digests):
  `CompositionCompletenessAttestationV2FU4` (bounded subject side /
  basis / source-class coherence; a candidate-side record cannot carry
  a REVIEWED basis; a candidate source class cannot attest a target and
  vice versa; `clause_digest` binds the EXACT clause; the attestation
  text is AUDIT-ONLY — never read by the derivation) and
  `QuantityCompletenessAttestationV2FU4` (the review process is the
  contract's SOLE quantity-attestation authority for EITHER subject
  side; bounded non-materiality reasons; no value field — the
  attestation never supplies a quantity VALUE). Neither is ever produced
  by the derivation (no fuzzy / similarity computation exists in the
  module — import-scanned).
* The candidate-side record
  (`CandidateBundleCompositionEvidenceV2FU4`, basis
  EXTRACTION_RESULT_V1 / RECORDED_CHANNEL, digest-bound to the verified
  extraction result or the recorded channel, with the embedded
  completeness attestation within its digest) and the target-side
  versioned record (`TargetSalesUnitEvidenceV2FU4` — the frozen FU3
  record's fields with the same constructor rules plus the bounded
  bundle composition fields; the FROZEN target record is read as
  composition-ABSENT under FU4, D18, no implicit upgrade). Both
  constructors are fail-closed validators (state/coherence matrix; D5 at
  the type level: empty / truncated / incomplete clauses are
  un-constructible as SYNTACTICALLY_VALID, let alone ESTABLISHED);
  presentation re-verifies the digests
  (`BundleCompositionEvidenceIntegrityError` on any tamper).
* The versioned clause extraction (whole-text count-only match; marker
  forms incl. the count-prefixed variants — the count is never re-bound
  into the clause, D17a), the textual-closure classification +
  completeness-marker detection (the versioned `_COMPLETENESS_MARKERS`
  six-member list + bounded delimiter set, the versioned
  `_INCOMPLETE_MARKERS` list; an incompleteness marker always dominates
  — D5; the EXTRACTION-basis colon-form continuation over the recorded
  field text), and the versioned materiality grammar (separators
  `+` / `,` / `&` / ` and `; canonical-quantity entries; grammar-
  internal normalization; full parse / multiset / material difference —
  textual agreement and material difference ONLY, never completeness,
  never quantity, D16 / D17).
* The unit derivation `derive_sales_unit_authority_fu4` + the case-level
  `derive_sales_unit_authority_fu4_case`: the CORRECTED decision table
  U0–U21 (form before composition; missing / partial /
  completeness-unknown composition ⇒ UNPROVEN; the quantity axis a
  DETERMINED, RECORDED state in every bundle comparison — CONSISTENT /
  BOTH_UNPUBLISHED / ATTESTED_NOT_MATERIAL / CONTRADICTED /
  UNDETERMINED — an asymmetric unattested gap is never silently
  immaterial, D20; PROVEN only over the full corrected D6 conjunction;
  the pre-revision U16 pass-arm "at least one side publishes none — no
  inference" is REMOVED). The non-bundle arms (SINGLE_UNIT /
  PACK_QUANTITY / TRAY_OR_FACTORY_PACK) delegate to the frozen FU3
  derivation (byte-identical — D9).
* The tier derivation `derive_authority_tier_fu4` + the decision record
  `AuthorityDecisionV2FU4` (the FU3 field set + the same construction
  invariants — AI_ASSISTED with an UNPROVEN / CONTRADICTED unit is
  un-constructible — PLUS the bounded bundle-axis audit fields: the
  quantity-axis state, the candidate / target composition states, the
  completeness-attestation digests, the quantity-attestation digest;
  exactly None for non-bundle channels — the determinations are
  RECORDED, never silent) + the mirrored rule vocabulary
  `AuthorityRuleV2FU4` (import-self-checked EQUAL to the FU3 set —
  D10: no new audit rule) + the SAME two restrict-only ceilings
  (UNPROVEN ⇒ CEILING_SALES_UNIT_NOT_PROVEN; CONTRADICTED ⇒
  CEILING_SALES_UNIT_CONTRADICTED; PROVEN ⇒ the automatic tier stands).
* The FU4 superset dispatch `derive_authority_tier_for_contract_fu4`
  (§5.4 / T8): the FU2 / FU3 arms delegate to the UNCHANGED frozen
  derivations (delegation identity pinned — same inputs ⇒ same outputs
  / same exceptions; composition / attestation inputs under either
  historical token are contract misuse, fail closed); the FU4 arm runs
  the FU4 derivation (the channel REQUIRED); unknown tokens fail closed
  (`UnknownAuthorityContractTokenError`, reused from the frozen FU3
  module); non-string ⇒ TypeError.

The research export surface is strictly additive
(`research/__init__.py` gains the FU4 import block + `__all__` entries;
the FU3 / P2 export blocks are untouched).

**Recorded conflict (the one existing-test edit).** The approved design
mandates the FU4 module inside `research/` (D1) which imports the FU3
module and reuses its frozen vocabulary (D9 delegation, D10 mirrored
rule set, D11 reused `SalesUnitAuthorityV2` / bound fields, §5.4 /
T8) — so the FU3 lexical markers are structurally unavoidable inside
the FU4 module, while the frozen FU3 reachability guard
(`tests/research/test_semantic_authority_v2_fu3.py`,
`TestReachabilityIsolation::test_no_live_module_references_the_fu3_
contract`) scans every research-layer module outside its allowlist.
Design §8's statement that the 98-node FU3 suite passes "UNCHANGED" is
therefore mechanically unsatisfiable without recognizing the
successor module the design itself mandates. RESOLVED with the minimal
non-weakening change: the guard's `allowed_paths` set gains exactly one
entry — `research/semantic_authority_fu4.py` — a single-line edit,
pinned LINE-EXACTLY by the new test file's A3 node
(`test_the_fu3_suite_is_unchanged_except_the_recorded_allowline` proves
the working FU3 suite file equals its starting-SHA content plus exactly
that one line — no other byte). The guard's stated safety property ("no
production module OUTSIDE the research contract surface references
it") is preserved: the FU4 successor contract module IS research
contract surface (the same category as `research/__init__.py`, already
allowed), and the new test file's own reachability guard re-pins that
no live / persistence / pricing / presentation module references the
FU4 surface. Every other assertion of the guard, and the guard's
marker set, are byte-unchanged. All 98 FU3 nodes pass.

**Tests.** 197 NEW nodes in the NEW file
`tests/research/test_semantic_authority_v2_fu4.py` implement the
design's full §9 adversarial matrix: A1 file-digest pins (every frozen
input of §8 — FU2 / FU3 / P2 extraction / S2-C / decision / codec /
replay / 2.0 / 2.1 / runtime / harness modules, the two corpus
artifact pairs, the DRAFT policy — byte-identical to the starting SHA)
+ A2 token / vocabulary bounds + delegation identity (the FU2 / FU3
dispatch arms ≡ the frozen derivations over the fixed parameterized
input set, same exceptions; unknown / non-string tokens fail closed) +
A3 suite preservation (the extraction suite files digest-pinned
UNCHANGED; the FU3 suite file pinned as starting-SHA + the one recorded
allow-line) + A4 the production codec / replay registries unchanged,
an FU4-bound payload refused (mirroring the FU3 refusal pin), the live
record type still pins the FU2 token, `V2_AUTHORITY_QUALIFIED` False in
both pinned locations, no live module references the FU4 contract (AST
+ lexical scan), the FU4 module is research-pure with no similarity /
fuzzy surface, no vendor / caller names, no pricing activation + A7 the
two-token coexistence pin (the SAME count-only bundle inputs derive
PROVEN_EQUIVALENT through the FU3 arm and UNPROVEN through the FU4 arm
— documented per-binding behavior, never drift). B1–B10 the
construction-level matrix: the five-way distinction + marker rows over
published text through the REAL frozen extractor chain (incl. the
EXTRACTION-basis colon-form continuation; a marker in a non-primary
field is not adopted — consistency ≠ completeness); empty / truncated
markers never establish (D5 at the type level); count-only never bound;
provenance refusal (no member is a model claim); integrity (tampered /
forged records refused at construction AND at the presentation gate —
the channel binding: a record cannot claim provenance the channel never
recorded); determinism (equal inputs ⇒ byte-equal records; the
canonical order of additional_clauses); the frozen target record under
FU4 (D18); the clause-grammar edges (the grammar decides the textual
axis only; `04x RAM` non-canonical ⇒ not fully parseable; the 0034
shape unattested ⇒ UNPROVEN, attested ⇒ PROVEN); the completeness-
attestation constructor (Blocker B: candidate-side REVIEWED basis
un-constructible; subject-side / source-class coherence; clause_digest
binding; the verbatim marker segment as attestation text; state /
coherence) and the quantity-attestation constructor (Blocker A:
vocabulary bounds; the sole authority; wrong subject side ⇒ integrity
error; non-asymmetric axis ⇒ contract misuse; no value field). C1–C12
the comparison rules: missing / partial / completeness-unknown ⇒
UNPROVEN over every target shape (Blocker B); equal counts without
composition ⇒ UNPROVEN (FU4) while FU3 PROVEN; materially established
difference ⇒ CONTRADICTED (both sides ESTABLISHED; the Q3-B4 §4.1
invariant + the constructor invariant); unestablished difference ⇒
UNPROVEN; equal complete compositions with sufficient provenance ⇒
PROVEN (U19 / U20 over all three satisfied quantity-axis states); form
before contents; MPN-in-clause non-inference; model-output
non-inference (signature-pinned); the quantity-completeness axis (every
axis state, incl. the Blocker A defect row: byte-identical attested
clauses with candidate quantity 2 / target None ⇒ UNPROVEN, was the
pre-revision PROVEN shape; the parsed entry count is never compared
against the published count); the completeness axis (Blocker B rows
incl. one-sided attestation never proves / never contradicts);
the copied attestation (the constructible shape derives per the axes —
no copy detection, T3'; the detectable launderings are unconstructible
/ integrity-refused; the audit surface records both attestations).
D1–D3 tier / overlay: the exact Q3-B4 §4.1 composition (MATCH + HIGH +
STRONG + clean + U1) over every corrected bundle shape (silent multi-
bundle, count-only, equal unattested text, asymmetric unattested
quantity, material difference, attested equal — the automatic-tier
ceiling invariants); the human overlay preserved (a firewall-capped
bundle candidate confirmed derives HUMAN_CONFIRMED; a model-reported
ALWAYS_HARD BUNDLE conflict still supersedes); the ceilings never lift,
never touch MACHINE_VERIFIED, never fire outside the automatic tier,
and the unproven / contradicted exposures are un-constructible (the FU3
invariants re-proven over the FU4 decision type, which is
type-distinguishable from the FU3 decision). E1–E3 the contract-phase
registries exactly as frozen; the registration step specified, not
executed (no FU4 entry anywhere; no corpus 1.2.0 artifact); replay
refusal of an FU4-bound payload + an unknown token in a record payload
fails closed. F1–F4 the never-infer list (no composition derived from
price / availability / condition / seller / offer URL / the raw
reference / the identifier fields / the model output / absence;
specification quantities inside a clause are item text, never promoted
to the bundle's quantity; multi-offer independence; the attestation
trust boundary: the derivation reads exactly the bounded fields — two
records differing only in attestation text derive identically — a
tampered attestation is digest-verified before any axis uses it, and no
attestation is ever constructed by the derivation). Every case is an
OFFLINE recorded-input construction with scripted evaluation doubles —
no live call, no model capture, no network. No existing test is
deleted, renamed, skipped, xfailed, deselected, ignored, or weakened
(except the one recorded FU3 guard allow-line above); the Windows
subprocess flake allowlist is NOT expanded.

**Validation.** Focused new file: 197 passed, 0 failed. Focused
preservation: the 98-node FU3 suite + the 111 + 7-node P2 / P2-FU1
extraction suites + the P1 binding-replay suite all pass (re-run
unchanged apart from the recorded FU3 allow-line). Focused
`tests/semantic/` + `tests/evaluation/`: 1335 passed, 1 failed — the
single failure is a member of the documented load-sensitive clean-
interpreter subprocess guard flake class (`OSError: [WinError 6]` at
`subprocess.Popen -> _winapi.DuplicateHandle` BEFORE any project code
runs; zero assertion failures), re-passed isolated on the first
attempt. Focused `tests/research/`: 3265 passed, 5 failed — the 5
failures are the same subprocess flake class (all re-passed isolated
one-node-per-process on the first attempt). Full suite (final): 7473
collected; **7473 passed, 0 failed** — no flake class member failed in
the final run; zero collection errors. Collection accounting: 7268 →
7473 (+205 = 197 new-file nodes + 8 auto-expanded parameterized
boundary scans the new research file triggers: research-core per-file
x4, domain +1, providers +1, runs +1, web +1 — the P2 precedent). Node-
level diff against the starting SHA: **0 nodes removed / 0 renamed**;
the addition is exactly the new test file + the boundary-scan
expansion. Skipped / xfailed / deselected: **0 / 0 / 0**. `python
manage.py check`: System check identified no issues (0 silenced). `python
manage.py makemigrations --check --dry-run`: No changes detected (no
model change — the component is pure research layer + tests).

**Production runtime and pricing remain unchanged (evidence).** The
frozen files are digest-pinned by the new A1 nodes (FU2 / FU3 / P2
extraction / S2-C / decision / codec / replay / 2.0 / 2.1 / runtime /
harness modules, the corpus artifacts, the DRAFT policy — all byte-
identical to the starting SHA); the production codec registry still
knows exactly the V1 + 2.0/FU2 bindings and refuses an FU4-bound
payload; the replay registry is the same union; the harness knows
exactly the two production bindings (2.0/FU2 ↔ 1.0.0, 2.1/FU3 ↔
1.1.0) and no corpus 1.2.0 artifact exists; the live record type still
pins the FU2 token at construction; `V2_AUTHORITY_QUALIFIED` is False
in both pinned locations; no live module (semantic / execution / runs /
web / providers) imports or lexically names the FU4 surface (AST +
lexical scan); the pricing-eligible tier set is unchanged and the cap
tier (NEEDS_REVIEW) remains non-pricing-eligible while the aggregation
/ matching surfaces own no FU4 symbol; the live V2 execution still
derives under the frozen 2.0/FU2 token. Nothing in the phase registers,
re-seals, activates, or wires.

No deployment performed. Q3-B5-P4 does NOT activate V2 authority, does
NOT connect V2 to pricing aggregation, and does NOT change any frozen
contract, the corpus, the DRAFT policy, or the live runtime: it
implements the separately versioned bundle-composition authority behind
its own token, isolated exactly as the design specifies. The
registration step (semantic-layer binding constant, corpus 1.2.0
binding-only reseal, harness registry extension, codec + replay
extension, offline no-capture baselines) remains its own separately
approval-gated phase (design §7.3), NOT executed here.


**PRODUCT-INTEL.SEMANTIC-AUTHORITY-V2-Q3-B5-P2-FU1 (Semantic Authority V2 —


Packaging Ambiguity and Bundle Identity Correction)

— IMPLEMENTED / PENDING INDEPENDENT REVIEW**

Bounded CONTRACT-CORRECTION phase on the reviewed Q3-B5-P2 candidate
(starting SHA `aa7401fc32c268316891ddaa7230b79f9c6f3e45`; baseline
collection 7251, re-verified this session), correcting the two safety
defects identified by the independent GitHub source review of
Q3-B5-P2. This is a bounded correction, not a new feature phase.
CONTRACT CORRECTION ONLY: NO live integration, NO V2 authority
activation, NO pricing change, NO corpus label change, NO benchmark
capture, NO deployment, NO model call, NO migration. The frozen FU3
module (`research/semantic_authority_fu3.py`), the frozen S2-C-FU1
channel (`research/semantic_v2.py`), the frozen 2.0 / 2.1 contracts,
and the live runtime are byte- and behavior-unchanged (the FU3 file-
level pins and the frozen-module digest pin pass; the only production
file touched is the P2-owned pending-review module `research/
sales_unit_extraction.py`). `V2_AUTHORITY_QUALIFIED` stays False in
both pinned locations; both committed corpus digests stay pinned by
the unchanged tests.

**Blocker 1 — ambiguous cues silently subsumed.** The reviewed
`_resolve_state` (and the result constructor's OBSERVED branch) could
accept an established claim while ignoring an ambiguous cue of the
SAME kind (e.g. "4-Pack (pack)" or "Tray of 10, tray of 10.5" ->
OBSERVED_UNAMBIGUOUS) — i.e. it treated matching packaging kinds as
proof that the ambiguous cue describes the same commercial unit.
Corrected (the P2-owned extraction contract only): an INDEPENDENTLY
unresolved ambiguous cue — of ANY kind, including the established
kind — now prevents OBSERVED_UNAMBIGUOUS (state AMBIGUOUS_CUE; every
cue preserved with its full provenance; the mapped channel is the
fail-closed recorded absence -> FU3 UNPROVEN for every target shape).
A genuine duplicate / subsumed cue is admitted ONLY when its
relationship is deterministically proven by the EXACT PUBLISHED SPANS
— the documented subsumption rule: same examined field, the ambiguous
cue's `[start, end)` span contained in an established cue's published
span, same kind (a fragment of the same published phrase, never a
second occurrence). The rule is applied IDENTICALLY by state
resolution (`_resolve_state` via the shared
`_is_subsumed_by_established`) and by the result constructor (a hand-
built OBSERVED result with an unproven ambiguous cue is un-
constructible; the scan engine's ordered alternatives never emit an
overlapping pair, so no extracted result depends on the subsumption
path). Unknown quantities stay fail-closed (a count is never bound to
an ambiguous cue).

**Blocker 2 — bundle contents and equivalence.** The reviewed cue
table established "bundle of N" / "N-unit bundle" as BUNDLE units
carrying the published count, so a count-only bundle mapped to an
OBSERVED channel that the frozen FU3 derivation treats as
PROVEN_EQUIVALENT against a target-side bundle of the same count — a
published count alone was accepted as the complete identity of a
bundle. Corrected: the extraction layer now distinguishes OBSERVED
BUNDLE FORM/COUNT from VERIFIED BUNDLE COMPOSITION. "bundle of N" /
"N-unit bundle" is ambiguous (BUNDLE_WITHOUT_CONTENTS; the count stays
verbatim in the cue text and is never bound to a quantity) -> the
mapped channel is the recorded absence -> FU3 UNPROVEN for EVERY
target shape, including a target-side bundle of the same count.
"bundle: contents" / "bundle (contents)" remains established (the
published composition verbatim in the cue span, quantity None — the
count is never salvaged from the composition).

**FU3 interaction review (the mandated STOP check).** The frozen
S2-C-FU1 channel carries no composition fact (its `raw_detail` free
text is not read by the derivation), and the frozen FU3 BUNDLE rule
equates matching form + equal published counts — so the frozen
channel / FU3 contract CANNOT represent verified-composition
equivalence: two identical, independently verified compositions
derive UNPROVEN (conservative, safe), and no count-only bundle can
ever derive PROVEN. The exact versioned contract amendment required
to represent the distinction (PROPOSED, NOT implemented — separately
approval-gated; the frozen FU3 implementation and acceptance criteria
are unchanged): a NEW separately versioned authority token
`SEMANTIC_AUTHORITY_V2_S2A_FU4` (per-binding discipline; the frozen
FU2 / FU3 tokens, records, and replays byte- and behavior-unchanged)
with (1) a versioned successor of the S2-C-FU1 recorded channel
gaining a bounded `composition` fact (the verbatim published contents
clause; required for an established count-bearing BUNDLE shape, absent
for a count-only one), (2) the target-side evidence record gaining the
same bounded `composition` field, and (3) the FU4 BUNDLE rule:
matching BUNDLE form -> PROVEN_EQUIVALENT only with composition
published on BOTH sides and byte-identical verbatim contents clauses
(and equal published counts where both sides publish one); composition
present but differing -> CONTRADICTED; composition missing on either
side -> UNPROVEN. Until that amendment is approved and separately
versioned, bundle equivalence under the frozen contract stays fail-
closed UNPROVEN.

**Tests.** The four existing nodes that asserted the reviewed
defective contract were corrected in place (documented; names
preserved — the Q3-B4-FU2 precedent): `test_bundle_with_established_
contents_and_quantity` ("bundle of 3 drives" now AMB /
BUNDLE_WITHOUT_CONTENTS / no bound quantity / UNAVAILABLE channel,
was OBS qty 3), `test_n_unit_bundle_phrases_are_observed` ("3-Unit
Bundle" now AMB / UNAVAILABLE, was OBS qty 3),
`test_same_kind_ambiguous_cue_is_subsumed_by_the_established_claim`
("4-Pack (pack)" now AMB / UNAVAILABLE, was OBS qty 4), and
`test_extracted_tray_and_bundle_forms` (the bundle-of-3 assertions now
UNAVAILABLE / UNPROVEN for every target shape, was OBSERVED / PROVEN
against a target-side bundle of 3). 17 NEW nodes (16 in the NEW class
`TestQ3B5P2FU1PackagingAmbiguityAndBundleIdentity` + 1 new
parametrize member `count-only-bundle` on the existing never-proven
node) cover the mandated regression matrix: (1) pack of 4 +
unresolved pack -> AMB, UNPROVEN for every target; (2) pack of 4 +
pack of 8 -> CONTRADICTED, every side preserved, UNPROVEN; (3) exact
duplicate pack-of-4 cues -> OBSERVED, PROVEN vs a target-side pack of
4, CONTRADICTED vs a different count; (4) structured packaging
conflicting with title (reverse roles over the existing node) ->
CONTRADICTED, fail-closed recorded absence; (5) bundle of 3 without
contents -> AMB, count never bound, UNPROVEN for every target;
(6) two bundles with equal counts but different contents -> never
PROVEN (count-only -> recorded absence; composition-verified ->
UNPROVEN; default single-unit target -> CONTRADICTED); (7) bundle
contents known on only one side -> UNPROVEN (the frozen target record
carries no composition field); (8) two identical, independently
verified bundle compositions -> both OBSERVED in the extraction layer
(composition verbatim, quantity None, distinct input bindings) but
UNPROVEN under the frozen FU3 contract (the channel carries no
composition fact — the reported amendment, not an implementation);
(9) tray quantity missing on one side -> UNPROVEN (equal published
counts PROVEN, unequal CONTRADICTED); (10) previously valid single-
unit and explicit pack-of-N cases (the unchanged recognition suite);
(11) frozen Prompt 2.0 replay (the unchanged old-token / corpus /
binding pins); (12) FU3 pricing ceiling with MATCH / HIGH / STRONG
over the corrected bundle shapes (count-only -> NEEDS_REVIEW via
CEILING_SALES_UNIT_NOT_PROVEN; composition-verified vs the default
target -> NEEDS_REVIEW via CEILING_SALES_UNIT_CONTRADICTED). The
constructor-level subsumption rule is pinned directly (hand-built
OBSERVED results: independent same-kind ambiguous cue rejected;
exact-span-proven subsumed cue admitted; non-contained span /
different field / different kind rejected). No test deleted, renamed,
skipped, xfailed, deselected, ignored, or weakened; no existing test
file other than the two P2-owned files touched; the Windows
subprocess flake allowlist NOT expanded.

**Validation.** Collection 7251 -> 7268 (+17, all in
`tests/research/test_sales_unit_extraction.py`, 94 -> 111 nodes; the
recorded-pages file unchanged at 7). Focused P2 files: 118 passed, 0
failed. Focused `tests/research/`: 3068 passed, 0 failed (incl. the
98-node frozen FU3 suite and its pins). Full suite: 7268 collected;
7257 passed, 11 failed — the 11 failures are EXACTLY the fixed
eleven-node load-sensitive clean-interpreter subprocess guard flake
allowlist (every one `OSError [WinError 6 x2 / WinError 50 x9]` at
`subprocess.Popen -> _winapi.DuplicateHandle` BEFORE any project code
runs; zero assertion failures). Isolated one-node-per-process re-runs:
9/11 re-passed on the first attempt; the remaining 2 re-passed on
spaced retry (the same multi-attempt behavior the Q3-B5-P1 audit and
the Q3-B5-P2 validation recorded under sustained handle pressure after
back-to-back full runs). No non-flake node failed anywhere. `python
manage.py check`: no issues (0 silenced); `python manage.py
makemigrations --check --dry-run`: no changes detected.

No deployment performed. Q3-B5-P2-FU1 does NOT activate V2 authority,
does NOT connect V2 to pricing aggregation, and does NOT change the
frozen FU3 contract, the frozen live-UNAVAILABLE contract, or the
corpus: it corrects the pending-review P2 extraction layer so that
the separately gated integration inherits the corrected fail-closed
semantics.


**PRODUCT-INTEL.SEMANTIC-AUTHORITY-V2-Q3-B5-P2 (Semantic Authority V2 —

Bounded Sales-Unit Evidence Extraction)

— IMPLEMENTED / CORRECTED BY Q3-B5-P2-FU1 (SAFETY DEFECTS) / PENDING
FINAL REVIEW (the independent GitHub source review identified two
safety defects — ambiguous same-kind cues silently subsumed, and a
bundle count accepted as the complete bundle identity; both corrected
in Q3-B5-P2-FU1, recorded above)**

Bounded EXTRACTION-LAYER phase on the authoritative starting SHA
`4033f21385a70b9e138e86b8ddf27e69de914595` (Q3-B5-P1-AUDIT endpoint;
collection baseline 7142, independently re-verified this session). This is
the Q3-B4 decision's roadmap row **P2** ("packaging extraction": the
extractor publishes the bounded packaging field with source provenance; the
OBSERVED channel fills on live pages; the absolute rule catches published
incompatible units at the decision level) — implemented HERE as the **pure
extraction and validation layer only**: no live input construction change,
no live integration activation, no V2 authority activation, no connection
to pricing aggregation, no corpus label change, no deployment, no model
call. The independently approved Q3-B4-FU2 (the separately versioned
firewall contract) and Q3-B5-P1 (prompt 2.1) are the contracts of record
(sections below; the documentation catch-up for the Q3-B3-FU2 design and
the Q3-B4 decision / FU1 / FU2 / P1 lineage — audit finding F-3 — is
recorded with this update).

**The bounded extraction component (NEW
`product_intelligence/research/sales_unit_extraction.py`, exported through
the research package surface).** A pure, deterministic, research-layer
module (stdlib + the frozen 3A observation contract + the frozen S2-C-FU1
channel / provenance vocabulary; no Django, no I/O, no clock, no network,
no LLM, no mutable global state — import-self-checked): the versioned,
immutable, self-verifying `SalesUnitExtractionResult` (**extraction schema
v1**) distinguishes, with explicit provenance for every cue, the four
bounded states — `OBSERVED_UNAMBIGUOUS` / `CONTRADICTED_CUES` /
`AMBIGUOUS_CUE` / `NO_PACKAGING_PUBLISHED`. Input is ONE
`ListingObservation` (one offer) plus, when a source publishes one, the
explicit page-published structured packaging field value (plain text as
published) — the ONLY fields the extractor may read. The identifier fields
(MPN / SKU) are examined ONLY to record that a packaging-like token in them
was set aside (never packaging evidence); the opaque `raw_reference` is
never read or parsed (AD-040); no price / availability / condition /
seller / description text and no model output is an input (the examined-
field vocabulary has exactly two members, neither a model claim).

**The frozen cue table (schema v1; false-positive resistance).** A bounded,
test-pinned phrase table requiring an explicit packaging word: single retail
unit ("single unit" / "single-unit" / "1 unit" / "1-unit"), pack of N
("pack of N" / "N-pack" / "N pack"), tray / factory pack ("tray" / "tray
of N" / "N-unit tray" / "factory pack" / "factory pack of N" / "N-unit
factory pack" / "oem pack" / "oem pack of N" / "N-unit oem pack" / "oem
tray" / "oem tray of N" / "N-unit oem tray"), bundle ("bundle of N" /
"N-unit bundle" / "bundle: contents" / "bundle (contents)"). Specification
quantities are NOT sales quantities: `4 TB` capacity, `2U` / `1U` chassis
height, `Dual-Port`, `8-channel`, `PCIe 4.0 x4`, `1 DWPD`, and product
revision numbers carry no packaging word and never match. A count must be
canonical (1..99999, no leading zero, no decimal); a count attached to a
capacity unit ("pack of 4TB" / "pack of 4TiB") is a specification quantity
(`CAPACITY_ATTACHED_QUANTITY`); a bare `pack` word is `PACK_WITHOUT_COUNT`;
a bare `bundle` is `BUNDLE_WITHOUT_CONTENTS` (the approved 2.1 design's P6
shape: unclear wording is unproven evidence, never an established
conflict); a structured field without packaging vocabulary is
`NO_PACKAGING_VOCABULARY`. Unbounded words (`kit`, `case`, `multipack`,
`Packard`, `Packing`, glued `4pack`) are not cues at all.

**State resolution (fail-closed).** No established cue ->
`NO_PACKAGING_PUBLISHED` (the recorded absence — the only state a silent
multi-pack can have) or `AMBIGUOUS_CUE`. Established cues of >1 kind, or of
one kind with >1 published quantity (incl. title vs structured field) ->
`CONTRADICTED_CUES` (EVERY side recorded with its full provenance).
Otherwise one established claim: `OBSERVED_UNAMBIGUOUS`, UNLESS an
unclassifiable cue of a different kind (or a vocabulary-less structured
field) is present, which blocks the claim -> `AMBIGUOUS_CUE`. A same-kind
ambiguous cue (e.g. "4-Pack (pack)") is subsumed and still recorded. The
constructor is the validator: every state / cue / established-unit
inconsistency (incl. a cue text its field never published, a foreign /
model-claim provenance source, a non-canonical digest, an unknown schema
version) fails closed.

**The provenance contract.** Each cue records: the examined field
(`PRODUCT_TITLE` / `STRUCTURED_PACKAGING_FIELD`), the bounded provenance
source (exactly the frozen `CandidateEvidenceSourceV2` members
`LISTING_TITLE` / `PUBLISHED_STRUCTURED_FIELD` — no member is a model
claim; the other two vocabulary members are rejected at construction), the
full field value as published, the verbatim cue text with its span
(verified as an exact substring), the kind, the published quantity where
the phrase carries one (never salvaged from an ambiguous phrase), the
disposition, and the bounded reason for ambiguous cues. The result is bound
to the exact examined input by an `input_digest` (SHA-256 over the
canonical document of the named 3A fields — `raw_reference` deliberately
excluded; two observations identical in every named field are the same
extraction input) and self-verifies by a `result_digest` (SHA-256 over the
canonical result minus the digest). Deterministic: equal inputs produce
byte-equal results.

**The fail-closed mapping onto the frozen channel (no contract change).**
`sales_unit_channel_from_extraction` re-verifies the presented result's
integrity FIRST (a hand-forged or tampered result produces no channel —
`SalesUnitExtractionIntegrityError`), then maps: `OBSERVED_UNAMBIGUOUS` ->
the frozen channel's `OBSERVED` state (established kind; published quantity
where the phrase carries one; the PRIMARY established cue's exact published
text as `raw_detail` — the structured-field cue when one is established,
else the first title cue in span order; that cue's recorded source; the
channel's own constructor re-validates). EVERY other state -> the canonical
`UNAVAILABLE`: the frozen channel has no ambiguous or contradicted state,
and recording either side of a contradiction as `OBSERVED` would present
one published claim as THE recorded unit (an unsafe workaround the schema
refuses). The full cue record stays in the versioned result for audit; the
FU3 derivation over the mapped channel then yields UNPROVEN (never
PROVEN_EQUIVALENT, never CONTRADICTED) for absence / ambiguity /
contradiction. A future versioned input schema may add explicit channel
conflict states — a separately approval-gated decision, NOT made here.

**Bounded scope (what this phase deliberately does NOT do).** The frozen
live input construction (S2-C-FU1) is byte- and behavior-unchanged:
`build_candidate_commercial_evidence_v2` still hard-wires the explicit
`UNAVAILABLE` state (test-pinned, incl. over a title with a loud cue), and
`build_semantic_match_case_v2` still records it — the frozen
live-UNAVAILABLE contract is NOT silently replaced. No live module
(semantic / execution / runs / web / providers) references the extractor
(AST-pinned); the separately versioned firewall derivation module remains
unreachable from live wiring (the FU3 lexical guard passes unchanged). No
persistence (no model, no migration, no codec registration — the result's
own future storage is its own versioned decision); no corpus label change
(both corpus digests re-pinned); no threshold / policy change; no V2
authority activation (`V2_AUTHORITY_QUALIFIED` stays False in both pinned
locations); no Machine Price / Reviewed Price change; no deployment; no
live capture.

**The smallest separately gated integration (PROPOSED, not activated).**
If and when an explicit versioned compatibility decision approves it, the
smallest integration is: a versioned successor of the live commercial
evidence builder (the frozen 2.0 builder stays as-is for 2.0-bound records)
that calls `extract_and_map_sales_unit_evidence(observation)` and records
the mapped channel in the recorded V2 input — everything else in the case
remains the frozen builder's. The offline gated shape is proven here
(`dataclasses.replace` of ONLY the channel over a real frozen-chain case;
FU3 case-level derivation reads exactly that channel). Activation requires
that decision; none was made in this phase.

**Tests.** 101 NEW nodes in TWO NEW files, all offline (no network, no
model call): `tests/research/test_sales_unit_extraction.py` (94) and
`tests/research/test_sales_unit_extraction_recorded_pages.py` (7, over the
REAL recorded listing fixtures through the real 3A extractor — the
samsung / oempcworld / exxactcorp / directmacro pages publish no packaging
evidence: capacity, chassis height, lane / channel counts, and
"Dual-Port" are specification quantities, never sales quantities; the
newegg / fusionww pages publish no observations and none is fabricated).
The mandated adversarial matrix is covered in full: silent multi-pack with
exact MPN (recorded absence -> UNPROVEN; old token's replay unchanged
AI_ASSISTED vs the firewall's NEEDS_REVIEW cap — the §4.1 row 1 invariant
over the extractor's channel); explicit pack-of-four (observed, CONTRADICTED
vs the default single-unit target, PROVEN against a target-side pack of the
same count); capacity mistaken for quantity (4 TB / 3.84TB / 960GB; plus
"pack of 4TB" / "pack of 4TiB" / "pack of 3.84" / "pack of 04" /
"pack of 100000" / "014-pack" -> ambiguous, never established); tray with
unknown quantity (observed TRAY, quantity None, never invented —
CONTRADICTED vs single target, UNPROVEN vs a tray target lacking the
count); bundle with unknown contents (bare "bundle" -> ambiguous;
"bundle: 2x RAM + 1x CPU" -> observed BUNDLE with the published contents
verbatim in the cue); conflicting title and structured packaging (both
sides recorded with provenance; the channel is the fail-closed UNAVAILABLE,
never either side); product revision number mistaken for quantity (no cue);
seller SKU with a quantity-like token ("4PACK-SSD-001" / "2-BUNDLE-001" /
"FACTORY-PACK-9" -> recorded set-aside, never evidence); multiple offers
with different units (one observation = one offer; independent results,
distinct input digests, no cross-contamination); manufacturer vs retailer
packaging (the tray / factory-pack forms are distinct kinds; a published
"4-Pack / Tray of 10" is CONTRADICTED — different unit claims; consistent
repetition "Tray of 10 / Factory Pack of 10" is observed); missing
packaging (the recorded absence, never SINGLE_UNIT); forged or
model-generated packaging evidence (no input member is a model claim —
signature-pinned; a cue cannot carry a foreign / non-extractor provenance
source; a cue cannot claim text its field never published; the
`raw_reference` is never read and never bound to the digest; a tampered /
hand-forged result fails self-verification and produces no channel;
inconsistent forged results are un-constructible); historical Prompt 2.0
replay (the frozen live builder still records UNAVAILABLE over a loud
title; the old token's derivation has no sales-unit input — passing one is
contract misuse; both committed corpus artifacts and the frozen 2.0 /
1.0.0 + 2.1 / 1.1.0 bindings re-pinned by digest); and the FU3
PROVEN / UNPROVEN / CONTRADICTED interaction (every mapped channel through
`sales_unit_authority_from_channel` and the tier derivation over
MATCH + HIGH + STRONG, incl. the case-level recorded-input shape). Both
false-positive resistance (no cue -> no channel value; never inferred from
absence / MPN / price / image / raw reference / identifier fields / model
claims) and preservation of valid observations (every unambiguous published
cue -> the exact OBSERVED channel with its provenance) are demonstrated.
No test deleted, renamed, skipped, xfailed, deselected, ignored, or
weakened; no existing test file changed; the Windows subprocess flake
allowlist NOT expanded.

**Validation (this session; candidate pass — final approval remains with
independent review).**

* Collection baseline at `4033f21`: **7142**; final: **7251** (+109 = 101
  new-file nodes + 8 auto-expanded parameterized boundary scans for the new
  research file [research-core per-file x4, domain +1, providers +1, runs
  +1, web +1]). Node-level diff against the starting SHA (independent
  linked worktree, removed after use): **0 nodes removed / renamed;**
  exactly the 109 additions above; no existing test file changed its node
  count.
* Focused new tests: **101 passed, 0 failed**.
* Focused `tests/research/`: **all passed** apart from the documented
  load-sensitive clean-interpreter subprocess guard flake class (see full
  suite; every one re-passed isolated).
* Focused `tests/semantic/` + `tests/evaluation/semantic_v2/` (frozen
  replay): **780 passed, 0 failed**.
* Focused `tests/execution/`: **858 passed, 0 failed**.
* Focused `tests/domain/` + `tests/providers/` + `tests/runs/` +
  `tests/web/`: all passed apart from the same flake class (re-passed
  isolated, spaced).
* Full suite (final, over the committed code): **7251 collected; 7240
  passed, 11 failed** — the 11 failures are EXACTLY the members of the
  documented load-sensitive clean-interpreter subprocess guard flake class
  (the fixed eleven-node allowlist; every one `OSError: [WinError 6] The
  handle is invalid` at `subprocess.py:1431` (`_winapi.DuplicateHandle`
  inside `Popen.__init__ → _get_handles → _make_inheritable`) BEFORE any
  project code runs; zero assertion failures, zero collection errors).
  Isolated one-node-per-process re-runs: over the first full run 8/11
  re-passed on the first attempt, the remaining 3 re-passed on spaced
  retry; over the FINAL full run (after the last cue-table refinement)
  ALL 11/11 re-passed on the first spaced isolated attempt (sustained
  handle pressure from the back-to-back full runs — the same multi-
  attempt behavior the Q3-B5-P1 audit recorded). No non-flake node
  failed anywhere. The known flake allowlist was NOT expanded.
* Skipped / xfailed / deselected: **0 / 0 / 0**.
* `python manage.py check`: System check identified no issues (0 silenced).
  `python manage.py makemigrations --check --dry-run`: No changes detected
  (no model change; the component is pure research layer).
* Worktree preservation: the pre-existing `tmp_collection.txt`
  modification and ALL untracked session / evidence artifacts (the seven
  historical benchmark artifacts, the three untracked Prompt 2.1 design
  lineage documents, the tmp_* collection files) are untouched; the commit
  stages only the phase files. The temporary linked worktree used for the
  node-level diff was removed after use; the unrelated
  `Product_Intelligence_recall_fix` worktree is preserved.

No deployment performed. Q3-B5-P2 does NOT activate V2 authority, does
NOT connect V2 to pricing aggregation, and does NOT change the frozen
live-UNAVAILABLE contract: the extractor is the independently sourced,
deterministic observability layer of the approved Option D firewall; its
integration into the recorded input construction is the separately gated
proposal above.


**PRODUCT-INTEL.SEMANTIC-AUTHORITY-V2-Q3-B5-P1 (Semantic Authority V2 —
Prompt 2.1 Versioned Implementation)

— IMPLEMENTED / APPROVED / FROZEN (independently approved; the independent
audit `docs/PRODUCT_INTEL_Q3B5_P1_INDEPENDENT_AUDIT.md` recorded at commit
`4033f21` is a PASS with no required corrections; the documentation
catch-up finding F-3 of that audit is addressed by this update)**

Bounded PROMPT-2.1-CONTRACT phase on the authoritative starting SHA
`e53d28c54840d296457dc586105cd3d1d545d394` (Q3-B4-FU2 endpoint; baseline
collection 7034). Implements the approved Q3-B3-FU2 design (Revision 2):
NEW `product_intelligence/semantic/contract_v2_1.py` (separately versioned
owner: `SEMANTIC_PROMPT_VERSION_V2_1 = "2.1"`, the real 2.1
system-prompt digest `e2949e7544d26228ac6f5555ae8ebd28019076e1de88ace25e
79a5d942d818fc`, the 2.1 user-prompt renderer over the frozen 2.0
rendering + the two approved annotation lines, fail-closed on 2.0 drift);
the 2.1 production binding registered as
`("V2", "2.1", 1, 1, "SEMANTIC_AUTHORITY_V2_S2A_FU3")` — the separately
versioned FU3 authority token per the Q3-B4 decision §6.2 /
AD-Q3B4-5 (the approved correction of the design's §9.1 text); the
corpus **1.1.0 binding-only re-seal** (`corpus_2_1.json` +
`manifest_2_1.json`: 56/56 per-case documents byte-identical to 1.0.0,
`label_revisions` empty, exactly `{corpus_version, semantic_contract_
binding, corpus_digest}` moved; digest `14396eae884841e20063cb4da0d4424c
e8f05ff8745f2c787fc395d250ea8dcd`); the harness pin extensions (corpus /
capture / direct_capture / live_capture / gates / report / cli accept
exactly the two known production bindings; the PRODUCTION_ROUTE loader
stays 2.0-only; unknown / cross-version / forged axes fail closed); the
committed 2.1 no-capture baseline reports for both pinned candidates.
NO recapture, NO deployment, NO authority promotion, NO corpus label
change; the frozen 2.0 contract (`contract_v2.py`, digest
`c0cc98bdd6d357e81d4692218f18d354351fc2833267b3062b7cd74b18445a84`),
corpus 1.0.0, the DRAFT policy, the FU3 module, and
`V2_AUTHORITY_QUALIFIED = False` (both pinned locations) are
byte-unchanged (independently verified by the audit). Tests: 108 NEW
nodes in four new files (`tests/semantic/test_contract_v2_1.py` 49,
`tests/evaluation/semantic_v2/test_q3b5_p1_corpus_2_1.py` 20,
`test_q3b5_p1_binding_replay.py` 20, `test_q3b5_p1_adversarial.py` 19).
Collection 7034 -> 7142 (+108; no auto-expanded scan — the only new
production file sits in `semantic/`, which no per-file research boundary
scan parameterizes over). The independent audit (commit `4033f21`,
document-only): PASS; test preservation exact (0 removed / 0 renamed /
+108); the re-seal verified field-by-field with independently recomputed
digests; every forged-binding / forged-token / cross-version / tampered-
report negative case executed against the actual code and refused; the
prompt verified line-faithful to the approved design (one disclosed,
authorized deviation accounted for — the RESPONSE FORMAT sentence keeps
the frozen 2.0 wording, the design's own marker; finding F-1, no impact);
findings F-4 (the DRAFT policy is scoped to corpus 1.0.0, so 2.1 /
1.1.0 evaluations can only decide POLICY_PENDING until Q3-C's policy-
governance step) and F-6 (the report seals but does not recompute the
system-prompt digest — a carried pre-P1 property) recorded for Q3-C. The
Q3-B5-P2 operator briefing and this update record the approval.


**PRODUCT-INTEL.SEMANTIC-AUTHORITY-V2-Q3-B4-FU2 (Semantic Authority V2 —
Sales-Unit Authority Firewall Correction)

— IMPLEMENTED / APPROVED / FROZEN (independently approved; the approval is
recorded by the Q3-B5-P1 and Q3-B5-P2 operator briefings and by this
update; the Q3-B5-P1 binding and the Q3-B5-P2 extraction layer execute
exactly against the corrected contract)**

Bounded CONTRACT-CORRECTION phase on the reviewed Q3-B4-FU1 candidate
(starting SHA `d70b137c4a95a5044fc421768ee8eab4bbb2325c`; baseline
collection 7021), correcting the two independent review defects of the
FU1 candidate. The frozen S2-A module (token
`SEMANTIC_AUTHORITY_V2_S2A_FU2`) is byte-unchanged (file-level digest pin
passes); the old token's derivation, records, tests, and replays are
unchanged; `V2_AUTHORITY_QUALIFIED` stays False in both pinned locations;
the corpus digest is unchanged; no deployment. **Blocker 1 — complete-
unit equivalence:** the reviewed candidate returned PROVEN_EQUIVALENT for
matching TRAY_OR_FACTORY_PACK / BUNDLE forms with the material quantity
unknown on one or both sides. Corrected contract (the separately versioned
`SEMANTIC_AUTHORITY_V2_S2A_FU3` derivation only): SINGLE_UNIT proves
against the default / explicit single-unit target (CONTRADICTED against
an established pack / tray / bundle target); PACK_QUANTITY proves only
with the same published count on both sides; matching TRAY / BUNDLE form
alone NEVER establishes equivalence — equal published counts on BOTH
sides PROVEN_EQUIVALENT, unequal published counts CONTRADICTED, the count
missing on EITHER side UNPROVEN; UNAVAILABLE -> UNPROVEN for every target
shape. **Blocker 2 — CONTRADICTED fails closed independently of the
model:** a recorded, independently derived sales-unit contradiction could
yield the automatic pricing-eligible tier whenever the model returned
MATCH (even MATCH + HIGH + STRONG + clean, empty conflict classes).
Corrected by the new separately versioned restrict-only rule
`AuthorityRuleV2FU3.CEILING_SALES_UNIT_CONTRADICTED`: a would-be
AI_ASSISTED_COMPARABLE with a CONTRADICTED unit is capped at NEEDS_REVIEW
(the invariant `CONTRADICTED -> never AI_ASSISTED_COMPARABLE` is also
enforced at `AuthorityDecisionV2FU3` construction; the rule never lifts,
never touches MACHINE_VERIFIED, never fabricates a model conflict class,
and is mutually exclusive with the UNPROVEN-only ceiling; the frozen human-
overlay precedence HARD_CONFLICT > HUMAN_CONFIRMED > AI is unchanged).
Tests: 13 NEW mandated adversarial nodes in
`tests/research/test_semantic_authority_v2_fu3.py` (seven of them failing
against the pre-correction module — defect demonstrated); existing nodes
corrected ONLY where they asserted the reviewed defective contract
(documented in the commit); one test renamed with its pin updated to the
corrected contract (the briefing-authorized vocabulary extension from one
to exactly two restrict-only rules). Collection 7021 -> 7034 (+13). Full
suite at the FU2 endpoint: 7034 collected, 7034 passed (the two preceding
runs each showed 2 failures of the documented subprocess flake class,
every one re-passed isolated; allowlist not expanded).


**PRODUCT-INTEL.SEMANTIC-AUTHORITY-V2-Q3-B4-FU1 (Semantic Authority V2 —
Contract Firewall Foundation)

— IMPLEMENTED / APPROVED (AS CORRECTED BY Q3-B4-FU2) / FROZEN (reviewed
with two independent blockers, both corrected in Q3-B4-FU2, recorded
above; this phase is the foundation of record for the separately
versioned firewall contract)**

Bounded CONTRACT-ONLY phase on the Q3-B4 decision (starting SHA
`4b2ed6c5ef368dd75b8ae2f86fc1e1ae58c21550`; baseline collection 6928):
NEW `product_intelligence/research/semantic_authority_fu3.py` — the
separately versioned authority contract token
`SEMANTIC_AUTHORITY_V2_S2A_FU3` behind which live ONLY: (1)
`IdentityResolutionBoundV2` (PART_NUMBER / FAMILY_DESCRIPTION /
DESCRIPTION / NONE) — the frozen 14-row bound table over the recorded
deterministic state + reviewed provenances (the model never sets it);
(2) `SalesUnitAuthorityV2` (PROVEN_EQUIVALENT / UNPROVEN /
CONTRADICTED) — the recorded-channel derivation (default single-unit
target; explicit target-side evidence with bounded provenance; fail-
closed UNPROVEN default); (3) the restrict-only
`CEILING_SALES_UNIT_NOT_PROVEN` rule on the automatic tier; (4) per-
binding dispatch (`derive_authority_tier_for_contract`: the old token
replays through the UNCHANGED frozen derivation; unknown tokens fail
closed). The frozen S2-A module is byte- and behavior-unchanged; nothing
live references the new token (import-scanned); no production record can
carry it; `V2_AUTHORITY_QUALIFIED` stays False. Tests: 85 NEW nodes in
`tests/research/test_semantic_authority_v2_fu3.py` (+ the research
package export surface, strictly additive). Collection 6928 -> 7021
(+93 = 85 new-file nodes + 8 auto-expanded boundary scans).


**PRODUCT-INTEL.SEMANTIC-AUTHORITY-V2-Q3-B4 (Semantic Authority V2 —
Semantic MATCH Authority Boundary Decision)

— APPROVED (decision document of record;
`docs/PRODUCT_INTEL_SEMANTIC_V2_Q3B4_AUTHORITY_BOUNDARY_DECISION.md`,
committed design-only on the Q3-B3-FU2 endpoint, baseline collection
6928; its six decisions AD-Q3B4-1..6 are ratified — the defect record,
Task A Option B (the independently derived
`IdentityResolutionBoundV2` at the separately versioned S2-A-FU3
boundary), Task B Option D (the combined firewall: FU3 restrict-only
derivation ceiling + mandatory atomic fail-closed consumer guard at the
first V2 pricing wiring + P2 extraction as the independent observability
phase), the AD-066 ratification, the 2.1 binding ordering (FU3 token),
and the Q3-C conditioning — by the subsequent separately approved
phases that execute exactly per them: Q3-B4-FU1 / Q3-B4-FU2 (the FU3
contract) and Q3-B5-P1 (the 2.1 binding under the FU3 token, verified by
the independent audit))**

The decision document resolves the two remaining Prompt 2.1 blockers as a
bounded decision proposal: Task A (executable MATCH semantics — the
frozen derivation consumes only decision / confidence / conflict classes,
so the within-MATCH identity resolutions are unenforceable downstream;
Option C rejected with its recorded conflicts) and Task B (the structural
sales-unit blindness of the frozen derivation — the §4.1 invariant: a
fully qualified semantic MATCH must never auto-price on an unproven or
contradicted commercial sales unit), with the exact bounded derivation
tables, the adversarial acceptance matrix (rows 1-11), the phase plan
(FU3 / P1 / P2 / P3 / Q3-C / W1), and the explicit ordering constraints
(consumer guard atomic with the first V2 pricing wiring; Q3-C conditioned
on the FU3 disposition; P3's production effect conditioned on the
firewall; P2 independent). This phase is CONTRACT DESIGN ONLY: no code,
no test, no capture, no deployment.


**PRODUCT-INTEL.SEMANTIC-AUTHORITY-V2-Q3-B3-FU2 (Semantic Authority V2 —
Prompt 2.1 Design: Identity Sufficiency and Sales-Unit Safety Correction)

— APPROVED (design document of record;
`docs/PRODUCT_INTEL_SEMANTIC_V2_PROMPT_2_1_DESIGN_Q3B3_FU2.md`, Revision
2, committed design-only on the Q3-B-FU1 endpoint, baseline collection
6928; approved by the Q3-B4 decision's lineage and implemented exactly by
Q3-B5-P1 — the independent P1 audit verified the implemented prompt line-
faithful against this revision and names it the approved design; the
earlier revisions (original + FU1 revision 1) remain untracked session
documents, not part of the committed record)**

Bounded DESIGN-CORRECTION-ONLY follow-up on the Prompt 2.1 design
(revision 1). Blocker A — product identity vs specification alignment:
the six evidence classes and the IDENTITY RESOLUTION vocabulary
(part-number / family+description / description) become explicit contract
language; a G2/G3 MATCH asserts equivalence at the stated resolution and
never part-number identity or unique product identification (alignment is
not uniqueness); the eleven-case audit shows 11/11 expected-MATCH labels
SUPPORTABLE at the stated resolution (zero corpus-contract conflicts; no
label moved). Blocker B — sales-unit unknown and future authority: the
six-way separation (physical identity / sales-unit equivalence / price
comparability / semantic decision / derived tier / actual pricing
eligibility); the sales-unit outcome table P1-P6 (known / equal; known /
different -> the absolute rule NO_MATCH; unavailable non-critical;
unavailable critical / entangled U5 -> UNCERTAIN, MATCH blocked;
ambiguous raw cue -> UNCERTAIN naming PACKAGING_QUANTITY / BUNDLE, never
MATCH or NO_MATCH on the cue alone); the UNPROVEN sales-unit
non-criticality rule; the raw-cue evidence base for the absolute rule
(required because the live channel is ALWAYS UNAVAILABLE — the recorded
R1 / R2 residual); and the explicit note that extraction (P2) is the
independent observability phase that grounds P2 / P6 deterministically.
NO implementation, NO live capture, NO deployment, NO authority
promotion, NO corpus label change, NO model call. The Q3-B4 decision
recorded the two remaining blockers this revision resolves (Task A /
Task B) as decision proposals.


**PRODUCT-INTEL.SEMANTIC-AUTHORITY-V2-Q3-B-FU1 (Semantic Authority V2 —

Live Capture Security and Abort-Safety Correction)

— IMPLEMENTED / PENDING FINAL REVIEW**

Bounded LIVE-RUNNER corrective follow-up on the reviewed Q3-B
candidate (AD-074; canonical spec §26.31), on the authoritative
starting SHA `eee688e15085dafa7788eb17ac87ceec9732894f` (Q3-B
endpoint; baseline collection 6912). Q3-B is recorded as REVIEWED /
NOT APPROVED / NOT FROZEN: its review identified two independent
defects in the live capture RUNNER, both corrected in this phase.
This is a CODE-CORRECTION AND TEST-VALIDATION phase: NO live
recapture was performed (the existing real primary capture and its
manifest are preserved byte-for-byte and remain the evidence of
record), NO deployment, and NO frozen production artifact changed:
prompt 2.0, input / output schema, reason codes, eligibility,
authority matrix, persistence adapter, runtime route, corpus labels,
and the DRAFT policy are byte-untouched; the corpus digest is
unchanged (`2c37ba088c317d8cefc6ad0dd7e0d73cfd085f6474ef43eb6953e3cf0170b549`);
the REAL frozen system prompt digest is unchanged
(`c0cc98bdd6d357e81d4692218f18d354351fc2833267b3062b7cd74b18445a84`);
`V2_AUTHORITY_QUALIFIED = False` is unchanged; no migration; the
frozen direct-capture schema v1 is unchanged (the capture document
the runner writes is the same strict schema; the runner manifest
sidecar - evidence only, never read by the evaluator - gains exactly
one additive top-level key, `dispatch_states`). No production
pricing authority; no new credentials or transport paths; the Q3-A
evaluation->research exact allowlist remains EXACTLY THE SAME SIX
FILES (the runner stays research-independent with its single lazy
transport import).

**Blocker 1 — unsafe exception disclosure (root cause +
correction).** Root cause: the CLI's `main()` caught arbitrary
`Exception` and printed its raw string (`error: {exc}`) - unexpected
exception text may contain provider URLs, request details,
credentials, or other sensitive information; additionally,
`_interpret_outcome()` embedded the transport-provided `error_type`
value into raised exceptions for out-of-vocabulary transport
evidence (an unrecognized string code, or a non-string
classification), and bounded configuration errors echoed
operator-supplied values (rejected provider/model, run_id) and the
transport factory echoed the unknown-provider name while retaining
the raw cause chain. Correction (all in
`product_intelligence/evaluation/semantic_v2/live_capture.py`):

* `main()` now handles the approved bounded error types explicitly -
  `LiveCaptureConfigError` / `LiveCaptureError` / `CorpusError` /
  `DirectCaptureError` -> their bounded messages, exit 2; a bounded
  run-level abort still exits 1 with the evidence preserved; success
  / dry run exits 0. ANY other exception -> the fixed, non-sensitive
  `UNEXPECTED_RUNNER_FAILURE` message (module constant; raw text /
  type / traceback are never printed), exit 3.
* Unexpected exceptions are never converted into a successful or
  retryable capture outcome: they propagate out of the run
  unconverted (same identity, no bounded status) and no capture
document is written.
* Out-of-vocabulary transport evidence no longer raises with the
  value embedded: it is a bounded run-level ABORT recorded ONLY as
  the new `LIVE_UNRECOGNIZED_TRANSPORT_CODE` marker - deliberately
  outside the four frozen policy buckets (which stay exactly the
  frozen vocabulary), manifest-only (no document record - the frozen
  schema cannot represent it), the transport value never echoed,
  and never retried. This also means the attempted evidence is no
  longer silently omitted: such an abort writes the manifest
  (bounded code; attempted + unattempted cases named).
* Bounded config / transport errors no longer echo
  operator-supplied values (only the frozen pinned identities,
  validated numerics, and type names are named); `TypeError` from
  config validation becomes a bounded `LiveCaptureConfigError`; the
  transport-factory conversion retains no exception chain
  (`from None` was already in place and is preserved).
* A ghost `__all__` entry (`LiveCaptureAbortError` - named but never
defined, found during the exception-path audit) was removed.

**Blocker 2 — concurrency and run-level abort (root cause +
correction).** Root cause: the concurrent runner submitted ALL
eligible cases to the `ThreadPoolExecutor` before consuming any
result, so an authentication / model-identity failure could be
detected only after other requests had already started; the
documented run-level abort boundary ("no further case is sent") was
not enforced for already-queued work, and the evidence could not
distinguish cancelled from never-attempted cases. Correction: a
strict dispatch-stop bounded dispatcher (a simple bounded loop -
correctness deliberately preferred over parallel speed):

* at most `max_concurrency` cases in flight at any time (the bound
  is preserved);
* a new case is dispatched ONLY while no abort has been observed:
  once an abort-class failure is recorded (the frozen abort
  vocabulary, or the out-of-vocabulary marker), no further case is
  submitted;
* submitted-but-not-started work is CANCELLED at the abort: it is
  never called and no model response is ever fabricated for it;
* already in-flight work runs to completion and its REAL outcome is
  preserved verbatim (executions, manifest attempt evidence, and -
  when in-vocabulary - the capture document record);
* the manifest distinguishes, for EVERY eligible case, the new
  additive `dispatch_states` key: `completed` (an outcome was
  preserved) / `cancelled` (submitted, not started, no model call)
  / `never_attempted` (never dispatched, no model call); in-flight
  cases are always collected before the manifest is written, so no
  uncollected state survives into the evidence;
* sequential mode is unchanged in behavior: an observed abort stops
  the very next dispatch (sequential work is never submitted before
  it starts, so `cancelled` cannot occur there).

**Evidence integrity (preserved).** The primary's real capture
(`q3b-20261009T010312Z-amax`) and its manifest are untouched,
hash-verified in this session:
`d94f1ed8ec4d254aa2a80e4ff58bd0bc55eb8c3744ad22f53f0b602ae9084d9f`
(document, 38945 bytes) and
`46f818bb02cc5838ab29aea9eb9d819108fa89c2f5a17349bb91e89544b99b79`
(manifest, 20293 bytes). The primary's observed result stands
unchanged: 43/43 valid responses; 0 false MATCH; 0 MATCH
predictions; MATCH recall 0/11; qualification policy DRAFT; no model
qualified. The fallback has not been captured. No ground-truth
labels, thresholds, prompts, or expected decisions were changed to
improve these results. NO live qualification rerun was performed
during FU1.

**Tests.** 16 NEW nodes in NEW
`tests/evaluation/semantic_v2/test_q3b_fu1_live_capture_safety.py`
(every model call is a scripted, recording test double; no live
network call anywhere): adversarial exception redaction (an
unexpected exception message carrying a synthetic API key, bearer
token, URL with credentials, and request secret never reaches
stdout/stderr - the CLI emits exactly the fixed non-sensitive
message, exit 3, no artifact; an unexpected transport exception
propagates unconverted with identical identity, one call, no
artifact; an out-of-vocabulary code with a secret payload and a
non-string classification both abort with the bounded marker - not
retried, no echo, manifest-only; bounded config errors do not echo
operator input, incl. the transport-factory path with no retained
cause chain; the CLI bounded paths keep exit 2 with bounded
messages - unpinned route, missing corpus, artifact collision);
strict dispatch-stop on REAL worker threads (barrier + event
synchronization, no timing-dependent sleeps: the abort case returns
while the other dispatched case is still in flight; the in-flight
outcome is preserved verbatim; nothing beyond the boundary is
dispatched - any further call fails loudly; the concurrency bound
holds; the tail is distinguished in the manifest; the capture
replays fail-closed, never QUALIFIED); deterministic cancellation /
preservation via a driven bounded-executor stand-in (REAL
`concurrent.futures.Future` objects and the production `wait` /
`cancel` semantics; tasks start and finish only when the test says
so): a submitted-but-not-started case is cancelled - never called,
never fabricated, distinguished from the `never_attempted` tail,
with the dispatcher proven to submit EXACTLY the first batch
(strict dispatch-stop); an already-running case is collected with
its real outcome while the abort is observed; an out-of-vocabulary
code stops the concurrent dispatch the same way; a sequential abort
marks the tail `never_attempted`; a completed concurrent run marks
all 43 `completed`; the manifest shape is pinned exactly (the Q3-B
key set + the single new key; the per-case attempt-evidence key set
unchanged; the dispatch vocabulary bounded to the three states).
The two previously modified Q3-A guards were REVIEWED and their
original assertions remain intact: `test_the_harness_modules_name_`
`no_ai_surface` (pins `live_capture.py` as the ONE module that may
reference the live transport surface) and
`test_the_direct_modules_import_no_production_execution_surface`
(pins its transport reference as exactly ONE lazy function-level
import of the approved factory) - both pass unchanged against the
corrected runner. No test deleted, renamed, skipped, xfailed,
deselected, ignored, or weakened; no file decreased; the Windows
subprocess flake allowlist NOT expanded. Collection 6912 -> 6928
(+16 = new-file nodes; no auto-expanded parameterized scans - no new
production file).

**Validation (this session, candidate pass - final approval remains
with independent review).**

* Collection baseline at `eee688e`: **6912**; final: **6928** (+16
  new-file nodes; no scan auto-expansion - no new production file).
* Focused Q3-A + FU1 + Q3-B + FU1 (`tests/evaluation/semantic_v2/`):
  **304 passed, 0 failed** (288 pre-existing + 16 new).
* Focused boundary suites (evaluation / research identity /
  providers / web / domain): **609 passed, 0 failed** (the
  clean-interpreter subprocess guards all passed in this run).
* Full suite (final, over the corrected code): **6928 collected;
  6928 passed, 0 failed** - zero failures, zero collection errors,
  and zero occurrences of the documented load-sensitive
  clean-interpreter subprocess guard flake class in the final run
  (nothing required isolation retry); the known flake allowlist was
  NOT expanded.
* Skipped / xfailed / deselected: **0 / 0 / 0** (full run: 6928
  passed, no other outcomes).
* `python manage.py check` / `makemigrations --check --dry-run`:
  run in this session - no issues, no model change (the correction is
  evaluation infrastructure only; recorded in the commit message).
* Worktree preservation: the seven historical benchmark artifacts,
  the pre-existing `tmp_collection.txt` modification, and the
  existing untracked live capture evidence are untouched (the commit
  stages only the phase files).

No deployment performed. Q3-B-FU1 does NOT claim qualification or
approval: Q3-B remains NOT APPROVED / NOT FROZEN pending review of
this correction, the qualification policy remains DRAFT,
`V2_AUTHORITY_QUALIFIED` remains False, the primary's live capture
remains the evidence of record (unchanged), the fallback's live
capture remains deferred, and NO live recapture was performed in
this phase.


**PRODUCT-INTEL.SEMANTIC-AUTHORITY-V2-Q3-B (Semantic Authority V2 —
Controlled Live Direct-Model Capture)

— REVIEWED / NOT APPROVED / NOT FROZEN (the two review blockers are
corrected in Q3-B-FU1; the phase awaits review of the corrected
candidate)**

Bounded LIVE-QUALIFICATION-EVIDENCE phase on the authoritative starting
SHA `517ef25c7ce83bba364234dda46270b147c0c053` (Q3-A-FU1 endpoint;
baseline collection 6828). Q3-A and Q3-A-FU1 are recorded as
APPROVED / FROZEN per the Q3-B operator briefing (the sections below
are flipped accordingly), so the frozen DIRECT_MODEL_QUALIFICATION
capture schema and the independent offline evaluator / report path
(AD-073) are the contract this phase executes against. **This phase
collects evidence. It does NOT grant qualification or pricing
authority.** NO frozen production artifact changed: prompt 2.0, input
/ output schema, reason codes, eligibility, authority matrix,
persistence adapter, runtime route, corpus labels, and the DRAFT
policy are byte-untouched; the corpus digest is unchanged
(`2c37ba088c317d8cefc6ad0dd7e0d73cfd085f6474ef43eb6953e3cf0170b549`);
the REAL frozen system prompt is
`c0cc98bdd6d357e81d4692218f18d354351fc2833267b3062b7cd74b18445a84`;
`V2_AUTHORITY_QUALIFIED = False` is unchanged; the decision stays
POLICY_PENDING under the DRAFT policy; no Machine Price, Reviewed
Price, or human-review authority change; no migration; no deployment.

**The bounded live capture runner (NEW
`product_intelligence/evaluation/semantic_v2/live_capture.py`).** A
benchmark-only live entry point, separate from production
orchestration. It reuses, never recreates: (a) the frozen production
V2 prompt builder (`semantic.contract_v2.build_semantic_prompt_v2`)
over the REAL typed corpus case (`CorpusCase.build_semantic_case`) -
every sent prompt is byte-exact frozen-builder output (proven by test
against the recorded calls); (b) the approved Q3-A-FU1
DIRECT_MODEL_QUALIFICATION capture schema (unchanged v1) - the written
document self-verifies through `load_direct_capture` /
`verify_direct_capture_against_corpus` after every run; (c) the frozen
production V2 parser composition (`evaluator.classify_raw_response` =
`parse_semantic_response_v2` + `validate_semantic_response_v2`,
identity-first, the production runtime boundary discipline); (d) the
approved provider transport / configuration mechanism
(`semantic.transport.get_openai_transport_for_provider`, env
`PI_SEMANTIC_<PROVIDER>_BASE_URL` / `_API_KEY`), imported LAZILY inside
transport construction only - module import loads no network client;
no `os.environ` read anywhere in the runner. It is RESEARCH-
INDEPENDENT (frozen route / contract pins re-imported from the
allowlisted `capture.py` / `direct_capture.py`), so the Q3-A
evaluation->research exact-allowlist remains EXACTLY THE SAME SIX
FILES. No production orchestration is imported or invoked (AST +
module-state proven: no execution / runs / web / providers / framework
surface); no general-purpose autonomous agent; the frozen Semantic V2
runtime is unmodified.

**Frozen model pinning (one run = one pinned model).** Each run
targets EXACTLY ONE frozen identity: primary `amax / qwen3.8-27b` or
fallback `vllm-262k / Qwen3.6-27B-262K` (unknown / mixed / whitespace
identities fail closed before any call). The two models are captured
INDEPENDENTLY - no primary-before-fallback routing, no simulated
primary failure, no response transfer between identities. Generation
parameters are the frozen pins (temperature exact float 0.0,
max_tokens 32768 - not caller-configurable, drift-pinned to
production). Bounded envelope: request timeout default 300.0 s, hard
bound 3600.0 s (mirrors of the frozen runtime bounds, drift-pinned);
concurrency default 1 (sequential, corpus order), hard bound 4;
records stay in corpus order under concurrency; artifacts are
append-only (existing paths are never overwritten); run id is
validated (bounded grammar) and distinct per capture.

**The FIXED retry policy (fixed before collection; no retry decision
ever reads the label).** (1) RETRYABLE - no model output, transient
transport condition, identical request, at most max_attempts=3 total
(bounded 1..3): TIMEOUT / DNS_ERROR / TLS_ERROR / CONNECTION_ERROR /
RATE_LIMITED / PROVIDER_UNAVAILABLE. (2) FINAL after exactly one call
(never retried, never cherry-picked; the single real output is
preserved verbatim): OK / HTTP_ERROR / EMPTY_RESPONSE / MALFORMED_JSON
/ SCHEMA_INVALID / INVALID_RESPONSE / MODEL_IDENTITY_MISMATCH. (3)
RUN-LEVEL ABORT after recording the attempted case (no further case
sent; unattempted cases named): AUTHENTICATION_FAILED / MODEL_NOT_
FOUND / INVALID_REQUEST_CONFIGURATION / UNSUPPORTED_PARAMETER /
unrecognized transport code (out-of-vocabulary evidence goes to the
manifest only - no document record that the frozen schema could not
represent). (4) CASE-LOCAL: CASE_REJECTED (content-policy rejection of
the case's own content) - run continues, manifest-documented, no
document record, replays NOT_CAPTURED (a coverage shortfall, never a
pass). A semantic disagreement with the ground truth is NEVER a retry
reason (proven by test: a schema-valid but label-wrong answer is final
after exactly one call and is scored as-is).

**Capture discipline (no fabrication, no silent skips).** ALL 43
eligible semantic cases are attempted per run; the 13
CONTRACT_NEGATIVE cases are never rendered into a prompt, never sent,
never recorded (proven by test). Every attempted case preserves: case
id, exact model identity (bound to the document and each record's
interpretation), frozen prompt/input identity (per-case prompt digest
+ REAL system-prompt digest in the manifest), bounded execution
status, raw response iff OK, run id + timestamps, and failure
classification. No expected label is modified from any model
response; a missing or incomplete capture never becomes a pass.

**Credentials / safety.** No key, base URL, Authorization header, or
credential value is hardcoded, printed, or written to any artifact
(sentinel-value proven by test; the manifest records key PRESENCE as a
bare bool). An unconfigured provider fails closed BEFORE any network
call (bounded error naming no secret; no artifact). Capture artifacts
are stored separately from the corpus labels in
`semantic_v2_live_captures/` (gitignore-protected, never committed
alongside labels): the strict capture document + the runner manifest
sidecar (evidence only - the offline evaluator never reads it).

**CLI.** NEW
`python -m product_intelligence.evaluation.semantic_v2.live_capture
capture` (--provider/--model validated against the frozen pins;
--corpus; --run-id/--captured-by/--notes; --max-attempts 1..3;
--max-concurrency 1..4; --request-timeout bounded; --out-dir;
--dry-run = full offline preflight with no transport, no call, no
artifact). The offline `cli.py` (including `evaluate-direct`) is
unchanged in behavior.

**LIVE EXECUTION (this session, per the operator briefing).**

* **Primary `amax/qwen3.8-27b` - CAPTURED (real responses).** Run
  `q3b-20261009T010312Z-amax`, started 2026-10-09T01:03:12.810455Z,
  finished 2026-10-09T01:23:39.955919Z (~20.5 min), git HEAD
  `517ef25c` (the starting SHA - the runner code captured is exactly
  the code under review), transport `OpenAISemanticTransport` (the
  approved canonical transport; api key present in the server
  environment, recorded only as a bool), timeout 300.0 s, concurrency
  1, max_attempts 3, temperature 0.0, max_tokens 32768. Result:
  **43/43 eligible cases attempted, 0 not attempted, 43/43 status OK,
  0 runtime failures, 0 retries used** (no transient transport
  condition occurred; the fixed policy was armed but never needed),
  latency min/avg/max 7.6 s / 28.5 s / 120.5 s. The document loads
  and verifies through the UNCHANGED frozen loader against the frozen
  corpus.
* **Fallback `vllm-262k/Qwen3.6-27B-262K` - NOT CAPTURED (endpoint
  unavailable in this environment).** `PI_SEMANTIC_VLLM_262K_BASE_URL`
  / `_API_KEY` are not set; the runner failed closed at preflight with
  the bounded PROVIDER_NOT_CONFIGURED classification (exit 2: "no
  live call was made and no artifact was written"). Per the operator
  briefing, the bounded runner + tests are complete and this session
  STOPS before claiming live qualification results for the fallback;
  its live capture is deferred to a session where the endpoint is
  configured.

**OFFLINE REPLAY (approved evaluator, unchanged path).** The primary
capture was replayed through `evaluate-direct` (report kind
SEMANTIC_V2_DIRECT_MODEL_QUALIFICATION_OFFLINE; report digest
`40340ce47d36d3b33b0dcf2a8dcce722abf0a34a399876ed174b6f558866f906`),
bound to corpus digest `2c37ba08...0b549`, the REAL system-prompt
digest `c0cc98bdd6d3...`, contract `("V2","2.0",1,1,
"SEMANTIC_AUTHORITY_V2_S2A_FU2")`, provider/model
`amax/qwen3.8-27b`, capture run `q3b-20261009T010312Z-amax`,
evaluation timestamp 2026-10-09T01:25:12Z. Result for
**amax/qwen3.8-27b**:

* **Coverage:** 43/43 eligible evaluated; 0 not-captured; 0 runtime
  failures; 0 invalid/capture-integrity failures; 0 contract
  violations; completeness flag TRUE. Valid structured response rate
  43/43 = 1.0.
* **Decisions made:** 22 NO_MATCH, 21 UNCERTAIN, **0 MATCH**.
* **Verdicts:** 24 CORRECT, 7 DEFENSIBLE (all 7 ambiguous cases
  answered within their acceptable sets; 0 outside defensible),
  11 ABSTAIN_ON_DEFINITE (every one of the 11 expected-MATCH cases),
  1 FALSE_NO_MATCH (`V2Q-SSD-CONTRA-0037`: expected UNCERTAIN, model
  NO_MATCH - severity REVIEW).
* **MATCH precision:** UNAVAILABLE (denominator 0 - the model made no
  MATCH prediction; reported unavailable, never 100%). **MATCH
  recall:** 0/11 = 0.0. **NO_MATCH accuracy:** 20/20 = 1.0.
* **Safety gates: ALL EIGHT PASS.** False-MATCH count 0
  (HARD_CONFLICT 0, packaging 0, accessory/product-role 0, near-miss
  0, sales-unit-safety 0). Severity counts: CRITICAL 0, HIGH 0,
  MEDIUM 0, REVIEW 12. The motivating Micron case
  (`V2Q-SSD-U5NM1-MICRON-0018`, expected UNCERTAIN +
  commercial_sales_unit_safety) answered UNCERTAIN / LOW /
  UNCERTAIN_IDENTIFIER_RELATION with REVISION_OR_SUFFIX - verdict
  CORRECT.
* **Per-substate:** U1 5/8 correct, U2 4/8, U3 2/3, U4 15/18 (the
  single false NO_MATCH), U5 5/6. **Per-category:** enterprise_ssd
  22/32 correct (incl. the one REVIEW false NO_MATCH), server_memory
  2/4, processor 2/2, network_adapter 3/3, workstation_gpu 2/2.
* **Decision: POLICY_PENDING** (coverage complete; the qualification
  policy is DRAFT / not approved - the decision vocabulary grants no
  QUALIFIED result; authority section `granted: false`,
  `v2_authority_qualified: false`).
* **Honest reading of the evidence (no qualification claimed):** the
  captured model is SAFE on this corpus (zero false MATCH, all eight
  hard gates pass, the critical sales-unit-safety Micron case is
  handled correctly) but is OVERLY CONSERVATIVE: it made no MATCH
  decision at all (recall 0.0 vs the DRAFT-proposed recall floor of
  0.90). If the DRAFT policy were approved as written, this capture
  would fall BELOW_THRESHOLD on match recall; as shipped (DRAFT), the
  decision is POLICY_PENDING. No labels, thresholds, or policy were
  moved to suit the result.

**Tests.** 80 NEW nodes in NEW
`tests/evaluation/semantic_v2/test_q3b_live_capture.py` (every model
call is a scripted, recording test double; the full pipeline re-proven
under a blocked socket): exact model pinning; frozen prompt fidelity;
transport boundary; no credential leakage; timeout handling; bounded
retry; no semantic-error retries; no best-of-N selection; no
contract-negative model calls; complete eligible-case traversal;
failure preservation; independent model capture; capture schema
validation; offline replay fidelity; no production execution imports;
no authority promotion; no pricing contamination; no network calls
during ordinary unit tests; bounded concurrency. The Q3-A / Q3-A-FU1
guards are STRENGTHENED in place (strictly additive): the offline
names-no-AI-surface guard now pins `live_capture.py` as the ONE module
that may reference the live transport surface (load-bearing
asserted); the direct-model AST guard pins its transport reference as
exactly ONE lazy function-level import of the approved factory (no
module-level transport import; the production runtime module still
forbidden). No test deleted, renamed, skipped, xfailed, deselected,
ignored, or weakened; no file decreased; the Windows subprocess flake
allowlist NOT expanded. Collection 6828 -> 6912 (+84 = 80 new-file
nodes + 4 auto-expanded parameterized scans for `live_capture.py`
[vendor-token +1, stdlib-imports +1, web inner-layer +1, providers
INNER_ROOTS +1]; no file decreased).

**Validation (this session, candidate pass - final approval remains
with independent review).**

* Collection baseline at `517ef25`: **6828**; final: **6912** (+84 as
  accounted above).
* Focused Q3-A + FU1 + Q3-B (`tests/evaluation/semantic_v2/`):
  **288 passed, 0 failed** (208 Q3-A/FU1 + 80 Q3-B).
* Focused research identity boundaries + semantic: all passed apart
  from the recorded load-sensitive clean-interpreter subprocess guard
  flake class (re-passed on isolated retry).
* Full suite (final, over the committed code): **6912 collected;
  6910 passed, 2 failed** - both failures are the documented load-
  sensitive clean-interpreter subprocess guard class (fail at Popen
  with `OSError [WinError 6/50]` BEFORE any project code runs; zero
  assertion failures, zero collection errors) and both re-passed on
  isolated one-node-per-process retry (2/2, exit 0): `test_domain_
  boundaries::test_domain_imports_without_django_network_or_llm_
  dependencies`, `test_evaluation_boundaries::test_loading_the_corpus_
  imports_no_framework_or_provider`. (An earlier full run over the
  same code, while the live capture was still finishing, showed 11
  failures - the complete fixed eleven-node allowlist of the same
  class, every one re-passed on isolated retry 11/11.) The known
  flake allowlist was NOT expanded; no non-flake node failed.
* Skipped / xfailed / deselected: **0 / 0 / 0**.
* `python manage.py check`: System check identified no issues (0
  silenced). `python manage.py makemigrations --check --dry-run`: No
  changes detected (no model change; the runner + artifacts are
  evaluation infrastructure only).
* `git diff --check`: clean.
* Worktree preservation: the seven historical benchmark artifacts
  (`b2_b3_full.txt`, `b2_b3_full_junit.xml`, `nemotron_full_
  evaluation.json`, `nemotron_full_manifest.json`, `nemotron_full_
  responses.jsonl`, `qwen38_run1_responses.jsonl`, `qwen38_run2_
  responses.jsonl`) and the pre-existing `tmp_collection.txt`
  line-ending modification are untouched (the commit stages only the
  phase files). The new live-capture directory is
  gitignore-protected; live artifacts remain untracked session
  evidence (the historical convention).

No deployment performed. Q3-B does NOT claim qualification or
approval: the qualification policy remains DRAFT,
`V2_AUTHORITY_QUALIFIED` remains False, the primary's live capture is
evidence recorded in the report above, the fallback's live capture is
deferred (endpoint not configured in this session), and the
qualification decision (Q3-C) is explicitly out of scope.


**PRODUCT-INTEL.SEMANTIC-AUTHORITY-V2-Q3-A-FU1 (Semantic Authority V2 —

Independent Model Qualification Capture)

— IMPLEMENTED / APPROVED / FROZEN (approval recorded at the start of
Q3-B per the operator briefing)**



Bounded CAPTURE-ARCHITECTURE corrective follow-up on the reviewed
Q3-A candidate (canonical spec: the Q3-A-FU1 operator briefing;
decision record: AD-073), on the authoritative starting SHA
`8435864e7517c17843a7406a79de4c819a6ef2fa` (Q3-A endpoint; baseline
collection 6748). Q3-A is recorded as REVIEWED / NOT APPROVED / NOT
FROZEN: review found one blocking architecture defect - the Q3-A
capture contract is ONE production run of the frozen pinned route
(primary attempt; fallback on eligible primary execution failure
only), so a normal run finalizes every case on the primary's success
and the fallback view of that run is all NOT_INVOKED: a single
production-route capture structurally cannot provide full
qualification coverage for BOTH models independently. FU1 corrects
the capture architecture without touching the frozen Semantic V2
production contract: it introduces two explicitly distinct, versioned
capture modes, and a dedicated independent evaluator / report path
for the benchmark-only mode. **No live model calls were executed in
FU1** (offline infrastructure only; the controlled capture runner is
Q3-B). **No frozen production artifact changed**: prompt 2.0, input /
output schema, reason codes, eligibility, authority matrix,
persistence adapter, runtime route, and production fallback behavior
are byte-untouched; the corpus digest is unchanged
(`2c37ba08...0b549`); the DRAFT policy is unchanged; `V2_AUTHORITY_
QUALIFIED = False` is unchanged; no Machine Price, Reviewed Price, or
human-review authority change; no migration; no deployment.


**The two capture modes (explicitly distinct typed schemas).**

* **Mode A — PRODUCTION_ROUTE** (the existing `capture.py` schema v1,
  unchanged and still readable): one capture = one run of the frozen
  pinned route; primary first; fallback only after an eligible
  primary EXECUTION failure with the frozen reason mapping; a
  successful primary finalizes the route; a fallback response never
  qualifies the primary and vice versa; uninvoked fallback cases stay
  NOT_INVOKED; the report now explicitly identifies the capture mode
  (the capture section carries `capture_mode: PRODUCTION_ROUTE` +
  `capture_schema_version: 1`) - additive identity fields only; no
  historical committed artifact is affected (the committed baselines
  are the no-capture state with a null capture section).
* **Mode B — DIRECT_MODEL_QUALIFICATION** (NEW `direct_capture.py`,
  its own `direct_capture_schema_version: 1`): a benchmark-only
  capture targeting EXACTLY ONE pinned provider/model
  (`amax / qwen3.8-27b` or `vllm-262k / Qwen3.6-27B-262K` - no other
  identity may enter the frozen V2 qualification; wrong / unknown /
  mixed provider-model pairs fail closed); every eligible semantic
  case is that model's own single bounded execution (one
  `execution_status` from OK + the frozen runtime's execution-failure
  vocabulary; `raw_output` present iff OK); NO primary-before-
  fallback requirement, NO fallback attempt, NO artificial primary
  failures, NO production routing, NO production execution or
  pricing authority; the model identity is bound to the document AND
  to every record's interpretation; the capture preserves the exact
  frozen corpus identity (id / version / digest), semantic contract
  V2, prompt 2.0, and a distinct run id + provenance per capture;
  duplicate case IDs, unknown case IDs, contract-negative records
  (schema-bypass attack), and corpus / prompt / contract mismatches
  all fail closed. Missing eligible cases are NOT a load error: they
  surface as NOT_CAPTURED at evaluation (coverage shortfall, never a
  pass).


**Backward compatibility (no cross-mode interpretation).** The two
modes are SEPARATE typed documents, not one ambiguous structure: a
PRODUCTION_ROUTE document is refused by the direct loader (explicit
cross-mode error), a direct document is refused by the production
loader (exact-key-set failure), a hybrid with both key sets is refused
by both, and the evaluators and report verifiers each refuse the
other mode's artifacts (typed cross-mode guards; production-route
captures are never reinterpreted as direct-model captures and vice
versa). Old production-route captures remain readable by the
unchanged production loader; nothing is migrated.


**The independent direct-model evaluator (NEW path in
`evaluator.py`).** `evaluate_direct_for_model` verifies (1) exact
provider/model identity of the requested model against the frozen
pinned routes, (2) the capture's bound target == the requested model
(responses never transfer between identities), (3) corpus id /
version / digest, (4) semantic contract V2 + prompt 2.0, (5) every
case ID (duplicates rejected at load; unknown / contract-negative
records rejected at corpus verification), and fails closed
(`QualificationContractError`) on any mismatch. It then scores each
case on that model's own execution: OK + parser-valid -> EVALUATED;
bounded execution failure -> RUNTIME_FAILURE (preserved separately,
never a semantic decision); no record -> NOT_CAPTURED; OK but the raw
output does not survive the FROZEN production V2 parser ->
CAPTURE_INTEGRITY_FAILURE (never substituted with the expected
answer). It reuses the production parser composition UNCHANGED
(`classify_raw_response` = `parse_semantic_response_v2` +
`validate_semantic_response_v2`), the same label-driven scoring,
severity, and metric surface - no approximation, no NOT_INVOKED
state, and no production orchestration import (mechanically
verified). Metrics, the eight mandatory safety gates, and the
fail-closed decision (FAIL_CLOSED / NOT_QUALIFIED / POLICY_PENDING /
INCOMPLETE_COVERAGE / THRESHOLD_INDETERMINATE / BELOW_THRESHOLD /
QUALIFIED) are computed independently per model in each mode; the
coverage denominators of the two modes are never mixed (a full
direct fallback capture is 43 evaluated / 0 NOT_INVOKED while the
same model's production-route view of a primary-answered run stays 0
evaluated / 43 NOT_INVOKED - both coexist, proven by test). A
complete direct-model qualification requires every one of the 43
eligible semantic cases to have an accepted, parser-valid response;
primary and fallback must each satisfy this independently.


**Reporting (explicit mode identity).** NEW `build_direct_report` /
`verify_direct_report` (separate report kind
`SEMANTIC_V2_DIRECT_MODEL_QUALIFICATION_OFFLINE`): the report
explicitly identifies the capture mode, the capture schema version,
provider/model (bound target), corpus id / version / digest, the
frozen contract binding + real system-prompt digest, the capture run
id + provenance, the evaluation timestamp, and the direct coverage
facts (eligible / evaluated / not-captured / runtime-failure /
invalid-response counts WITH case ids, completeness flag), plus the
per-substate and per-category performance, false-MATCH case ids, the
eight hard safety-gate results, the qualification policy status
(DRAFT), and the decision. Each mode's verifier REFUSES the other
mode's reports (cross-mode kind check - fail closed). Production-
route `build_report` output is unchanged in content and the committed
no-capture baseline reports (both pinned candidates) are
BYTE-IDENTICAL to what the unchanged pipeline reproduces (JSON and
Markdown, proven by test).


**Offline-only boundary.** FU1 implements capture formats + offline
evaluation infrastructure. It runs NO real model calls, adds NO live
transport execution, and changes NO production runtime routing; the
controlled capture runner is Q3-B (after independent FU1 approval).
The socket-blocked pipeline test and the AST import scan cover the
direct path.


**Architecture boundary (preserved, strengthened).** NEW
`direct_capture.py` is RESEARCH-INDEPENDENT (it re-imports the
frozen route / contract pins from the allowlisted `capture.py`, the
house least-privilege pattern), so the Q3-A evaluation->research
exact allowlist remains EXACTLY THE SAME SIX FILES - no new exception
was necessary and none was added; no broad prefix-based exception
was introduced. The Q3-A mechanism test
`test_qualification_v2_exception_is_an_exact_allowlist` is
STRENGTHENED in place (strictly additive: `direct_capture.py` is
added to the pinned non-allowlisted set and must exist and remain
research-independent).


**Ground truth and safety (unchanged).** The corpus is untouched:
56 cases (43 semantic: 36 AUTHORITATIVE + 7 AMBIGUOUS; 13
CONTRACT_NEGATIVE); the motivating Micron case
(`MTFDKCC3T8TGP-1BK1DABYYR` vs `MTFDKCC3T8TGP-1BK1DABYY`,
`V2Q-SSD-U5NM1-MICRON-0018`) still expects UNCERTAIN with
PACKAGING_QUANTITY missing and the commercial sales-unit-safety flag
(a direct MATCH on it is a CRITICAL false MATCH in both modes -
proven); synthetic / recorded-fixture / real-market provenance stays
separate (REAL_MARKET still loader-rejected); no expected decision or
conflict label changed. The eight mandatory safety gates are
unchanged and work identically in both modes (gate-for-gate
equality proven, including the input-aware authority-promotion
cross-check); the policy remains DRAFT, so no QUALIFIED result can
be produced (full correct captures stay POLICY_PENDING under the
shipped policy); `V2_AUTHORITY_QUALIFIED` remains False; no Machine
Price, Reviewed Price, or human-review authority change.


**CLI.** NEW `evaluate-direct` command (one report per pinned model
per direct capture; void evaluations emit an explicit FAIL_CLOSED
direct-kind report); the existing `evaluate` command (production-
route mode, including the no-capture baseline) is unchanged in
behavior.


**Tests.** 76 NEW nodes across four files
(`tests/evaluation/semantic_v2/`): `test_q3a_fu1_direct_capture.py`
(35), `test_q3a_fu1_direct_evaluation.py` (19),
`test_q3a_fu1_qualification.py` (12), `test_q3a_fu1_reports.py` (10)
+ the shared `_q3a_fu1_helpers.py` fixture writer (declared test
fixtures, not model output) - covering all 32 mandated properties:
production-route captures still readable / fallback never after
primary success / fallback execution-failure-only; independent
direct primary + fallback captures with no fake primary failure;
cross-mode decode + evaluation fail closed; wrong / unknown /
mixed provider-model fail closed; duplicate / unknown case IDs;
contract-negative responses; corpus digest / prompt / contract
mismatches; missing / runtime-failure / invalid responses cannot
PASS; primary qualification does not qualify the fallback and vice
versa; independent denominators (NOT_INVOKED production-only);
production parser reused without approximation (case-for-case
outcome equality across modes); false-MATCH gates identical in both
modes; synthetic labels stay synthetic; the Micron case unchanged;
no production execution imports (AST + module-state proof);
no network / model calls (socket-blocked); historical baseline
reports byte-identical; policy remains DRAFT; `V2_AUTHORITY_
QUALIFIED` remains False; no pricing / review authority tokens. No
test deleted, renamed, skipped, xfailed, deselected, ignored, or
weakened; the one existing test touched is the strictly-additive
mechanism-test strengthening above; the Windows subprocess flake
allowlist NOT expanded. Collection 6748 -> 6828 (+80 = 76 new-file
nodes + 4 auto-expanded parameterized scans for `direct_capture.py`
[vendor-token +1, stdlib-imports +1, no-outer-layer +1, providers
INNER_ROOTS +1]; no file decreased).


**Validation (this session, candidate pass — final approval remains
with independent review).**


* Collection baseline at `8435864`: **6748**; final: **6828** (+80 as
  accounted above).
* Focused Q3-A + FU1 (`tests/evaluation/semantic_v2/`): **208
  passed, 0 failed** (132 Q3-A + 76 FU1).
* Focused boundaries (`tests/evaluation/test_evaluation_boundaries.py`
  + `tests/research/test_research_identity_boundaries.py`): all
  passed apart from the recorded load-sensitive clean-interpreter
  subprocess guard flake class (see full suite).
* Focused S2-A / S2-B / S2-C + FU1 (authority contract, V2 contract,
  input evidence, V1/V2 record, codec, replay, boundaries, adapter,
  prompt, runtime): **all passed, 0 failed** (613 nodes).
* Focused semantic runtime / V2 execution wiring / motivating case /
  semantic integration / persistence / runs: all passed apart from
  the same subprocess guard flake class (re-passed on isolated
  retry).
* Focused 2A / 3C / 4A / human review: **all passed, 0 failed**.
* Full suite: **6828 collected; 6817 passed, 11 failed** - all 11
  failures are the documented load-sensitive clean-interpreter
  subprocess guard class (fail at `Popen -> _get_handles ->
  _make_inheritable -> _winapi.DuplicateHandle -> OSError`
  [WinError 6 x2, WinError 50 x9] BEFORE any project code runs; zero
  assertion failures, zero collection errors): `test_domain_
  boundaries::test_domain_imports_without_django_network_or_llm_
  dependencies`, `test_evaluation_boundaries::test_loading_the_corpus_
  imports_no_framework_or_provider`, `test_provider_boundaries::
  test_http_pdf_imports_no_third_party_dependency` / `test_importing_
  the_page_boundary_pulls_in_no_third_party_dependency` / `test_
  importing_the_provider_boundary_pulls_in_no_third_party_dependency`,
  `test_enterprise_ssd_boundaries::test_importing_enterprise_ssd_
  does_not_load_django` / `test_importing_enterprise_ssd_pulls_in_no_
  third_party`, `test_listing_normalization_boundaries::test_
  importing_the_research_core_still_pulls_in_no_third_party_
  dependency`, `test_research_identity_boundaries::test_importing_the_
  research_core_pulls_in_no_third_party_dependency`, `test_
  specification_boundaries::test_importing_specifications_pulls_in_no_
  third_party_dependency`, `test_research_run_boundaries::test_the_
  domain_still_imports_without_django_present`. Every one re-passed
  on isolated one-node-per-process retry (11/11, exit 0). The known
  flake allowlist was NOT expanded; no non-flake node failed.
* Skipped / xfailed / deselected: **0 / 0 / 0** (full run: 6817
  passed + 11 flaked, no other outcomes).
* `python manage.py check`: System check identified no issues (0
  silenced). `python manage.py makemigrations --check --dry-run`: No
  changes detected (no model change; capture formats are evaluation
  infrastructure only). `python manage.py migrate --plan`: unchanged
  (final entry `runs.0012_semantic_decision_record`).
* `git diff --check`: clean.


No deployment performed; FU1 does not claim approval or
qualification: Q3-A remains NOT APPROVED / NOT FROZEN pending review
of this correction, the qualification policy remains DRAFT, `V2_
AUTHORITY_QUALIFIED` remains False, and live capture is Q3-B.



**PRODUCT-INTEL.SEMANTIC-AUTHORITY-V2-Q3-A (Semantic Authority V2 —

Qualification V3: Independent Corpus, Harness and Offline Qualification)

— IMPLEMENTED / APPROVED / FROZEN (reviewed; the capture-architecture
defect corrected by Q3-A-FU1; approval recorded at the start of Q3-B
per the operator briefing)**



Bounded QUALIFICATION-INFRASTRUCTURE phase on the authoritative starting

SHA `cf51a23e31d175cc9e6759d12f97171769db87e5` (S2-C-FU1 endpoint,

now APPROVED / FROZEN per the operator briefing; baseline collection

6575). Canonical spec: PLAN §26.28; decision record: AD-072. Q3-A

builds the independent, deterministic, OFFLINE qualification system for

the exact frozen Semantic V2 contract: a versioned, independently

labeled corpus, a reproducible offline evaluation harness that uses the

REAL frozen V2 input / prompt / parser (no recreation), separate

semantic-accuracy and safety metrics, explicit false-MATCH detection

with deterministic severity, contract / version / provenance

verification, a fail-closed qualification decision, and a reproducible

offline report bound to the exact corpus digest. **No live model

qualification was executed in Q3-A** (no V2 responses exist yet; the

harness evaluates previously captured responses, and the committed

baseline reports are the explicit no-capture state). **No frozen

production artifact changed**: the Semantic V2 prompt, input schema,

output schema, reason codes, eligibility, authority matrix, persistence

adapter, and runtime route are byte-untouched; `V2_AUTHORITY_QUALIFIED

= False` is unchanged; no deployment.



**Approval record (state transition).** The operator briefing for Q3-A

declares "S2-C APPROVED / FROZEN". The committed STATUS at the starting

SHA still carried S2-C / S2-C-FU1 as PENDING FINAL REVIEW (the approval

had not yet been recorded in-repo). Following the project's established

transition pattern (S2-A-FU2's approval was recorded by the S2-B

commit), this commit records the approval: the S2-C and S2-C-FU1

sections below are flipped to APPROVED / FROZEN, and the frozen

Semantic V2 contract that Qualification V3 qualifies against is the

corrected S2-C-FU1 contract with binding exactly

`("V2", "2.0", 1, 1, "SEMANTIC_AUTHORITY_V2_S2A_FU2")` and prompt

`2.0` (the pre-freeze 2.0 text, never shipped).



**The corpus (versioned, digest-sealed, independently labeled).** NEW

`evaluation/semantic_v2_qualification/` (data, outside the Python

package): `corpus_v1.json` — 56 cases (43 semantic: 36 AUTHORITATIVE +

7 AMBIGUOUS; 13 CONTRACT_NEGATIVE) across 5 product categories

(enterprise_ssd 45, server_memory 4, processor 2, network_adapter 3,

workstation_gpu 2); covers all seven frozen S2-A uncertain

state/substate combinations (U1, U2 both signals, U3, U4, U5 NM-1,

U5 NM-2) and every mandated adversarial shape (exact product in

different legitimate wording; title-MPN only; compatibility/reference

wording; different generation/capacity/interface/form factor;

accessory vs product; standalone vs bundle; single vs multi-pack;

tray vs retail; missing candidate MPN; different SKU for the same

product; SKU accidentally matching the requested MPN; one-character

MPN difference; truncated MPN; different brand; condition-only

difference; missing critical specs; customer retrieval alias;

manufacturer product context without relation authority; explicit

reviewed relation authority; contradictory listing evidence;

misleading SEO; insufficient evidence). The motivating Micron case

(target `MTFDKCC3T8TGP-1BK1DABYYR` vs candidate

`MTFDKCC3T8TGP-1BK1DABYY`) is present

(`V2Q-SSD-U5NM1-MICRON-0018`, RECORDED_FIXTURE): the truncated form is

the exact recorded-catalog part ("7500 4TB U.3 SSD"), the R/T family

relation is the recorded CUSTOMER-DEFINED 4D-D rule (no manufacturer

document states what R denotes), so physical-product family membership

is grounded while commercial sales-unit comparability is UNPROVEN —

the independent expected decision is **UNCERTAIN** with

PACKAGING_QUANTITY missing, flagged `commercial_sales_unit_safety`

(a false MATCH is CRITICAL). The pair is NOT labeled equivalent merely

because it shares a base identifier. Ground truth: every case carries

source kind (CONTRACT_GROUNDED / PRODUCT_KNOWLEDGE_GROUNDED /

REVIEWED_SOURCE_GROUNDED), explicit source citation, the independent

evidence, reviewer identity + status, and ambiguity classification;

the loader mechanically rejects label text naming model output or a

candidate model; synthetic cases are labeled SYNTHETIC and never

real-market evidence; `REAL_MARKET` is reserved (corpus 1.0.0 ships

none — the loader rejects it); the recorded-fixture cases cite the

recorded 4D-D Micron 7500 catalog (body digest

`160d4fe9...00743`) and the recorded project-UAT V1 semantic corpus.



**Corpus integrity (frozen, digest-bound).** Canonical serialization

(sorted keys, compact, ASCII, no floats) + SHA-256: per-case

`case_digest` and whole-state `corpus_digest` (v1.0.0: corpus

`2c37ba08...0b549`, manifest `aa870660...2e9`). The auditable source is

`product_intelligence/evaluation/semantic_v2/fixtures.py` (declarative

cases that run the EXACT frozen chain: request -> observation -> 3B

normalization -> 3C assessment -> S2-A derivation -> S2-C input

builder / real `SemanticMatchCaseV2` constructor); a self-check fails

generation if a fixture lands in a different deterministic state than

declared; regeneration must reproduce the committed corpus

byte-for-byte (proven by test). A label change must change the digest

and create a bounded `label_revisions` entry (reason class A/B/C/D —

"the new implementation failed this case" is not a valid class);

reports verify against the corpus digest and per-case label snapshots,

so a historical report stays bound to its original corpus and fails

against a mutated one. Reproducible `manifest_v1.json` per case.



**Offline harness (NEW `product_intelligence/evaluation/semantic_v2/`).**

* `fixtures.py` — corpus source (frozen chain); * `corpus.py` — strict

loader / typed case reconstruction / bounded rejection classes

(NON_UNCERTAIN_STATE / INVALID_INPUT_SCHEMA /

FOREIGN_DETERMINISTIC_CONTEXT / UNSUPPORTED_EVIDENCE) / digest /

manifest; * `capture.py` — the captured-response artifact contract for

the later live phase (schema v1; binds to the exact corpus digest, the

frozen prompt `2.0`, the semantic contract `V2`; attempts mirror the

frozen runtime discipline — PRIMARY first, fallback on execution

failure only with the frozen reason mapping, raw output only for OK

attempts; a record for a contract-negative case is a schema-bypass

attack); a capture records ONE RUN and is projected per model; *

`evaluator.py` — deterministic zero-network zero-AI evaluation using

the PRODUCTION V2 parser (`parse_semantic_response_v2` +

`validate_semantic_response_v2`; no recreation) and the REAL

`SemanticMatchCaseV2` constructor: per-case states EVALUATED /

NOT_CAPTURED / NOT_INVOKED / RUNTIME_FAILURE /

CAPTURE_INTEGRITY_FAILURE / CONTRACT_REJECTED_OK / CONTRACT_VIOLATION;

the primary and fallback are qualified INDEPENDENTLY (a primary view

counts a fallback-answered case as its own execution failure; a

fallback view counts a primary-answered case as not invoked — a

primary PASS never qualifies the fallback); an invalid captured

response is a bounded failure, never substituted with the expected

answer; model confidence never overrides the label (severity comes

from the label's conflict classes / flags: CRITICAL = false MATCH on

an independently established ALWAYS_HARD conflict or commercial

sales-unit safety; HIGH = other false MATCH; MEDIUM = false NO_MATCH

on expected MATCH; REVIEW = abstention on definite / outside the

ambiguous defensible set); * `gates.py` — the eight MANDATORY hard

safety gates (zero false MATCH on ALWAYS_HARD / packaging / accessory

conflicts; zero schema-bypass acceptance; zero unauthorized authority

promotion; zero customer-alias promotion; zero contract-version

mismatch; zero missing-required-evaluation-silent-pass) + the

fail-closed decision (NOT_QUALIFIED > POLICY_PENDING >

INCOMPLETE_COVERAGE > BELOW_THRESHOLD / THRESHOLD_INDETERMINATE >

QUALIFIED); * `policy.py` + `policy/qualification_policy_draft_1.json`

— the DRAFT threshold proposal (match precision >= 0.99, recall >=

0.90, valid response rate >= 0.99, eligible coverage >= 1.0) marked

DRAFT / unapproved: NOT finalized production thresholds; without an

approved policy the decision is POLICY_PENDING, never QUALIFIED; *

`report.py` — the reproducible offline report (machine JSON + human

Markdown) bound to the exact corpus digest, the frozen contract

binding, the REAL system prompt by digest, the runtime configuration

identity (pinned routes, temperature 0.0, max_tokens 32768, the

`V2_AUTHORITY_QUALIFIED` marker), and the capture provenance; the

report grants no authority and no decision token grants one; *

`cli.py` — offline commands (corpus-build / corpus-digest /

corpus-manifest / evaluate / verify-report), no network, no AI.

Committed baseline: `reports/q3a_baseline/` — the explicit no-capture

reports for BOTH pinned route candidates (43/43 eligible NOT_CAPTURED,

13/13 contract-negative rejected as expected, all gates pass,

decision POLICY_PENDING; reproducible byte-for-byte by test).



**Architecture boundary (explicit, documented).** The Q3-A harness must

use the real frozen research/semantic surface, so the A1-FU2

evaluation->research exact-allowlist mechanism is extended by EXACTLY

SIX named files (`corpus.py`, `fixtures.py`, `capture.py`,

`evaluator.py`, `gates.py`, `report.py` — `canonical.py`, `policy.py`,

`cli.py`, `__init__.py` stay research-independent). The A1-FU2 entry

remains exactly one file; the mechanism tests are preserved and a new

exact-allowlist mechanism test locks the Q3-A set (no prefix/glob/

regex). Recorded in the test docstrings, PLAN §26.28 item 9, and

AD-072.



**Tests.** New: 132 nodes across 5 files (`tests/evaluation/

semantic_v2/`): corpus schema validation; independent label provenance

(incl. the mechanical model-output-naming rejection and the

corpus-never-reads-captures proof); synthetic vs real evidence

classification; corpus digest stability + regeneration byte-identity;

label mutation changes digest (incl. the sealed-revision path);

duplicate case id; unknown corpus version; unknown semantic contract;

prompt version mismatch; production prompt fidelity (real digest, no

prompt copy in the harness); production parser fidelity (sentinel-proof

that the classifier composes the real parser); valid MATCH /

NO_MATCH / UNCERTAIN evaluation; invalid JSON; unknown response field;

unknown conflict class; incoherent reason/conflict pair; missing model

response; runtime failure (incl. both model views of a failed

fallback); false-MATCH detection (hard-conflict / packaging / accessory

/ near-miss / sales-unit-safety, with case-id examples); ambiguous

exclusion from hard accuracy; zero-denominator metrics reported

unavailable (never 100%); independent primary/fallback qualification

(a primary PASS on one run leaves the fallback INCOMPLETE — no data

crossing); incomplete coverage cannot PASS; policy-pending cannot

PASS; safety failure cannot be masked by high aggregate accuracy; no

network in offline replay (socket blocked); no AI calls in offline

replay (transport never imported, runtime construction refused);

no authority promotion (marker False, report grants nothing, alias

promotion flagged, no pricing/review surface imported); historical

results retain exact corpus/contract identity (reproducible digest,

verify-against-corpus, mutation detection, capture cannot follow a

corpus revision, committed baselines verify). Anti-manipulation:

changing expectations to fit model output is detectable (digest change

+ historical report stops verifying + capture cannot follow the

revision) and an unsealed label edit is rejected on load.

Corrected in place (requirement correction, safety preserved):

`test_only_promotion_regression_may_wire_research` (the count pin now

spans both exact allowlists; the A1-FU2 one-file pin is preserved;

the no-heavy-imports property applies to all excepted files); the

`test_no_outer_layer...` docstring (Q3-A extension recorded). No test

deleted/renamed/skipped/xfail/deselected/ignored; no file decreased;

the known Windows/Python-3.14 subprocess flake allowlist NOT expanded.

Collection 6575 -> 6748 (+173 = 132 new-file nodes + 40 auto-expanded

parameterized scans for the 10 new evaluation files [vendor-token +10,

stdlib-imports +10, no-outer-layer +10, providers INNER_ROOTS +10] + 1

new exact-allowlist mechanism node; no file decreased).



**Validation (this session, candidate pass — final approval remains

with independent review).**



* Collection baseline at `cf51a23`: **6575**; final: **6748** (+173 as

  accounted above).

* Focused Q3-A (`tests/evaluation/semantic_v2/`): **132 passed, 0

  failed**.

* Focused boundaries (`tests/evaluation/test_evaluation_boundaries.py`

  + `tests/research/test_research_identity_boundaries.py`): **161

  passed, 0 failed** (one allowlisted clean-interpreter subprocess

  guard flaked once with the recorded `WinError 6` Popen signature

  before any project code runs and re-passed on isolated retry).

* Focused S2-A + S2-C + FU1 (authority contract, V2 contract, input

  evidence, V2 adapter, V2 boundaries, prompt, runtime): **all passed,

  0 failed**.

* Focused S2-B + FU1 (record, codec, replay, boundaries, runs,

  persistence service): **all passed, 0 failed**.

* Focused semantic runtime / V2 execution wiring / motivating case /

  semantic integration / 2A / 3C / 4A / human review: **all passed, 0

  failed**.

* Full suite: **6748 collected; 6747 passed, 1 failed** — the single

  failure is `tests/domain/test_domain_boundaries.py::test_domain_

  imports_without_django_network_or_llm_dependencies`, a clean-

  interpreter subprocess guard (an area Q3-A does not touch) with the

  recorded `subprocess.run(capture_output=True) -> Popen ->

  _get_handles -> _make_inheritable -> OSError: [WinError 6]`

  signature before any project code runs (load-sensitive; the same

  class failed once more, in an allowlisted member, during the focused

  boundary batch and re-passed); it **re-passed on isolated retry**

  (exit 0). The known flake allowlist was NOT expanded; no non-flake

  node failed. (Earlier in the session, a full-suite run additionally

  showed 3 `tests/semantic/test_contract_sharing.py` failures —

  diagnosed and fixed in-session: a Q3-A test had popped the live

  transport module from `sys.modules`, breaking a module-identity pin

  in later tests; the test no longer disturbs global module state, and

  the full run above is clean apart from the one subprocess flake.)

* `python manage.py check`: System check identified no issues (0

  silenced).

* `python manage.py makemigrations --check --dry-run`: No changes

  detected (no model change; the harness is evaluation infrastructure

  only).

* `python manage.py migrate --plan`: unchanged (final entry

  `runs.0012_semantic_decision_record`).

* `git diff --check`: clean (see commit message for the diff

  summary).



No deployment performed in this commit; the Q3-A artifacts are

evaluation infrastructure and a DRAFT policy. The V2 route remains

`V2_AUTHORITY_QUALIFIED = False`; qualification (live capture under

the exact frozen prompt, then offline evaluation, then an APPROVED

policy) is future work — Q3-A explicitly does NOT execute live model

qualification and does NOT claim any qualification or approval.



**PRODUCT-INTEL.SEMANTIC-AUTHORITY-V2-S2-C-FU1 (Semantic Authority V2 —

Input Evidence Fidelity) — IMPLEMENTED / APPROVED / FROZEN**



Approval recorded at the start of Q3-A (operator briefing: "S2-C

APPROVED / FROZEN"); the corrected pre-freeze candidate is the frozen

Semantic V2 contract Qualification V3 qualifies against: binding

`("V2", "2.0", 1, 1, "SEMANTIC_AUTHORITY_V2_S2A_FU2")`, prompt `2.0`

(the corrected text; 2.0 never shipped). The S2-C-FU1 MUST-NOT-deploy

restriction remains in force until an explicitly reviewed deployment

phase.



Bounded INPUT-EVIDENCE corrective follow-up on the pending S2-C
candidate (canonical spec: PLAN §26.27; decision record: AD-071, amending
AD-070 in part), on the authoritative starting SHA
`a3127bca4bc4177b447ece8b20c33d83ec4ed415` (S2-C, PENDING FINAL REVIEW;
baseline collection 6528). S2-C is REVIEWED but NOT APPROVED / NOT
FROZEN. One review blocker was corrected before the Semantic V2 contract
can be declared FINAL: the S2-C "FINAL" V2 input did not provide the
structured product/commercial evidence the product goal requires —
`candidate_specs` was a misleading free-text slot always `None`, the
commercial context was a composed price/availability/seller/offer
string, no packaging/sales-unit channel existed, and the motivating
test claimed family/capacity/interface/form factor were "structured
evidence" merely because the tokens occur in the candidate TITLE. FU1
corrects the MODEL-OBSERVATION input contract so the model receives the
best SAFE product and commercial evidence already available in the
system, with explicit structure and provenance — while the AUTHORITY
side (S2-A) is untouched and the model still cannot bootstrap authority
from its own output.

**Versioning decision (honest, pre-freeze).** S2-C MUST NOT deploy and
NO historical production V2 record exists anywhere (verified: the
`runs_semanticdecisionrecord` table is absent from the development
database; V2 is persist-only, `V2_AUTHORITY_QUALIFIED = False`). FU1
therefore amends the PRE-FREEZE candidate in place: the contract
binding stays exactly `("V2", "2.0", 1, 1, "SEMANTIC_AUTHORITY_V2_S2A_FU2")`
and the prompt version stays `2.0` — 2.0 never shipped, so the frozen
2.0 that Qualification V3 will qualify against is the corrected text.
Bumping would create phantom versions of unshipped artifacts. The
anti-reinterpretation safety is unaffected: a pre-FU1-shaped payload
strictly fails closed under the corrected codec (proved by test).

**Extraction-capability audit (documented in `research/semantic_v2.py`).**
WHAT EXISTS TODAY: 3A `ListingObservation` carries the page-published
STRUCTURED fields (product title, MPN field, SKU, brand, price,
currency, availability, condition, seller, offer URL; JSON-LD / product
meta are the only offer mechanisms); the remaining JSON-LD material
(description, GTIN, category, ...) stays in the OPAQUE `raw_reference`,
which no business rule may parse (AD-040). 3B normalizes COMMERCIAL
attributes only. 3C compares EXPLICIT MPN fields only (frozen 2A).
The 6A/6B/6C specification framework and the 7A/7B comparable-research
extraction exist ONLY in the comparable-research flow and require an
ESTABLISHED identity — not available to main-flow listing candidates.
The 4D-D Micron 7500 alias acquisition is the ONLY reviewed
manufacturer TARGET context the main flow carries (ESTABLISHED =>
manufacturer, verified SSD category, exact source-published base MPN,
customer-defined R/T relation, bounded fetch provenance; no other
catalog attributes — the box quantity is NOT carried and is NOT claimed
as candidate packaging evidence). WHAT CAN BE SAFELY STRUCTURED:
published-structured-field facts only (brand candidate-side; the
commercial fields; the reviewed 4D-D target context). WHAT STAYS RAW:
the published title (and the requested description) as labeled RAW
OBSERVATION TEXT — no token is parsed into a structured fact. WHAT
GRANTS AUTHORITY: unchanged — `ProductEvidenceFactV2` requires the
frozen S2-A grounded-source vocabulary; the live main flow grounds
ZERO matched facts (the audit proves why). WHAT THE MODEL MAY SEE BUT
CANNOT GRANT AUTHORITY: everything in the observation sections
(structured or raw), the commercial/packaging evidence, and the
customer-retrieval relation.

**The corrected V2 input contract.** `SemanticMatchCaseV2` (17 required
top-level fields; no silent defaults; construction fails closed exactly
as S2-C): A. TARGET — NEW `TargetEvidenceV2`: the structured
caller-published MPN; the requested description as RAW OBSERVATION
TEXT (explicit None when absent); and `ReviewedTargetContextV2 | None`
(NEW — structured/reviewed target-side context: manufacturer, verified
category, matched base part number, bounded relation kind — today only
`CUSTOMER_RETRIEVAL_ALIAS` = zero identity authority, never
manufacturer-stated — the relation's family part numbers other than
the requested form, source name/URL, ISO-8601 UTC retrieval instant,
64-hex evidence body digest; fail-closed). B. CANDIDATE LISTING —
published identifier fields (MPN field / SKU), the frozen 3C evidence
source, NEW `CandidateProductEvidenceV2` (nine bounded product
dimensions — product family / generation / capacity / interface / form
factor / product role / accessory relation / brand / revision-suffix —
each a `CandidateObservationFactV2` (observed value + explicit
`CandidateEvidenceSourceV2` provenance: PUBLISHED_STRUCTURED_FIELD /
LISTING_TITLE / SPECIFICATION_TEXT / REVIEWED_PRODUCT_CONTEXT; NO
model-claim member) or explicit None; plus raw_title_text /
raw_specification_text RAW observation text) and NEW
`CandidateCommercialEvidenceV2` (condition / price / currency /
availability / seller as bounded facts, the published offer URL, and
the REQUIRED NEW `CandidateSalesUnitEvidenceV2` packaging channel —
ALWAYS explicit: UNAVAILABLE (all value fields None) or OBSERVED
(bounded `SalesUnitKindV2` SINGLE_UNIT / PACK_QUANTITY /
TRAY_OR_FACTORY_PACK / BUNDLE + published raw detail + provenance +
bounded positive int quantity where the kind carries one; PACK_QUANTITY
requires it, SINGLE_UNIT forbids it)). C / D / E — unchanged (the
deterministic identity context, the context provenance, and the
authority-side ProductEvidenceProfileV2). The misleading
`candidate_specs` / `candidate_commercial_context` free-text slots and
the loose top-level brand/condition/title fields are REMOVED (replaced
by the typed sections).

**Safe live builders (observation side).** NEW
`build_candidate_product_evidence_v2` (fills ONLY published
structured-field facts the extractor actually carries — brand; every
other dimension explicit None; the title as raw text; no specification
text — it stays in the opaque raw reference) and NEW
`build_candidate_commercial_evidence_v2` (published commercial fields
as bounded facts; the sales-unit channel ALWAYS the explicit
UNAVAILABLE state — the extractor publishes no packaging field and
nothing is inferred from price). `build_semantic_match_case_v2` gains
the EXPLICIT `reviewed_target_context` keyword (no silent default).
The SAFE authority-side builder `build_v2_product_evidence_profile` is
UNCHANGED (frozen S2-A signature; the live path still passes
matched_facts=frozenset(); the model's matched_attributes still cannot
enter it — the no-model-output parameter proof stands).

**4D-D target-context wiring.** NEW
`reviewed_target_context_from_alias_result` in
`execution/semantic_decision_v2_execution.py` (deterministic over the
ESTABLISHED result's own re-verified fields; non-ESTABLISHED ->
explicit None; an ESTABLISHED result missing a reviewed field fails
closed — defense in depth, the result's self-validation already makes
such a state unconstructible). The orchestration carries it into
`evaluate_semantic_matches_v2` (new EXPLICIT keyword) for every
V2-eligible candidate of the run. No 4D-D contract, codec, snapshot,
or fetch behavior changes; the 4D-D firewall is untouched (the context
is target-side observation evidence, zero identity authority).

**Prompt V2 corrected (version stays 2.0 — see decision above).** The
system prompt gains the EVIDENCE CLASSES rules: STRUCTURED FACT vs RAW
OBSERVATION TEXT vs COMMERCIAL / PACKAGING EVIDENCE vs REVIEWED TARGET
CONTEXT vs AUTHORITY-SIDE PRODUCT EVIDENCE; absence of packaging
evidence is NOT proof of equal sales unit and is never read as
"single unit"; no packaging value is inferred from price; a raw-text
token is not a structured fact and raw text never becomes manufacturer
authority; absence of a structured fact does not erase raw observation
evidence; never manufacture a missing fact (absent from all evidence ->
missing_critical_attributes); UNPROVEN sales unit + otherwise-matching
evidence -> PACKAGING_QUANTITY / BUNDLE missing + UNCERTAIN. The user
prompt renders the corrected sections (structured facts with source
labels or explicit absence; raw text under the raw label; commercial
facts + explicit sales-unit state; the reviewed target context labeled
STRUCTURED/REVIEWED / target-side only / zero identity authority).

**Persistence / replay.** The V2 codec's case section is corrected to
the exact new shape (strict key sets; unknown enums, invented evidence
sources, invalid sales-unit cross-states, and a tampered reviewed
context all fail closed; a pre-FU1-shaped payload — free-text
`description` / `title` / `specs` / `commercial_context` — is never
silently reinterpreted). The V2 run-binding check reads the corrected
target section. The V1 adapter, V1 payload bytes, V1 replay, the
envelope, the row, the service, and migration 0012 are byte-untouched.
NO migration.

**Motivating Micron case corrected.** The flawed node
`test_the_input_carries_the_structured_evaluation_context` is
CORRECTED IN PLACE as
`test_the_input_carries_the_corrected_evidence_contract`: it no longer
proves "structured family/capacity/interface/form factor" by title
tokens. It now proves accurately: (A) the raw candidate title evidence
reaches the model labeled RAW observation text; (B) truly structured
product facts are present only where the extraction layer produced
them — all four dimensions are explicit absences despite the title
tokens; (C) packaging/sales-unit evidence is explicitly ABSENT
(UNAVAILABLE) — the fixture's only candidate commercial fact is a
price, and a price is never a packaging observation; (D) the absence
renders with the never-infer rule (not silently interpreted as
equivalence). Unchanged adjacent nodes still prove: (E)
CUSTOMER_RETRIEVAL_RELATION retrieval-only (zero identity authority);
(F) the U5/NM-1 relationship ceiling (MATCH/HIGH + STRONG capped at
NEEDS_REVIEW without reviewed relationship authority); (G) no Machine
Price contamination (full orchestration). NEW full-orchestration node:
the ESTABLISHED 4D-D acquisition carries the reviewed manufacturer
TARGET context (Micron / SSD / base MPN / CUSTOMER_RETRIEVAL_ALIAS /
family part numbers / provenance) into the recorded V2 input with zero
identity authority, while the candidate-side packaging channel stays
explicitly UNAVAILABLE and the derived snapshots are unchanged
(NOT_ESTABLISHED / NEEDS_REVIEW).

Test preservation: no test deleted, renamed, skipped, xfailed,
deselected, ignored, or weakened merely to obtain green. The corrected
motivating node preserves the safety property it was meant to check
(the input reaches the model with honest evidence classes) while
removing the flawed claim. S2-C test-helper call sites were mechanically
updated to the corrected builder signature / case shape (the explicit
`reviewed_target_context` keyword; the typed evidence sections); every
safety assertion in those helpers is preserved. The package-export
pins gain the FU1 surface (strengthened). New nodes: 47 — NEW file
`tests/research/test_semantic_v2_input_evidence.py` (27: the 20
mandated input-evidence properties + the reviewed-target-context
contract incl. the 4D-D helper over the real recorded catalog fixture),
+8 prompt evidence-class nodes (`tests/semantic/test_contract_v2.py`),
+11 codec nodes (`tests/research/test_semantic_decision_v2.py` —
packaging single-unit / pack-quantity / tray / bundle round-trips if
observed; UNAVAILABLE default; reviewed-context round-trip + zero-live
replay; pre-FU1-shape refusal; legacy `specs` key refusal; invalid
cross-state / unknown-source / unknown-relation-kind refusal), +1
full-orchestration motivating node (`tests/execution/test_semantic_
v2_motivating_case.py`). No test file decreased; the known
Windows/Python-3.14 subprocess flake allowlist NOT expanded.

Validation (this session, candidate pass — final approval remains with
independent review):

* Collection baseline at `a3127bc`: **6528**; final: **6575** (+47 =
  27 new-file nodes + 8 prompt nodes + 11 codec nodes + 1 motivating
  node; no file decreased).
* Focused S2-C + FU1 (contract 60, input evidence 27, prompt 41,
  runtime 29, adapter 61, boundaries 32 + 50, execution 20, motivating
  case 10): **330 passed, 0 failed**.
* Focused S2-A + S2-B (authority contract + boundaries, record, codec,
  replay, runs, persistence service): **347 passed, 0 failed**
  (combined with the S2-C + FU1 batch: 677 passed, 0 failed).
* Full suite: **6575 passed, 0 failed**, 39 subtests passed, 0 errors,
  0 skipped, 0 xfailed, 0 deselected (~7 min; the known
  Windows/Python-3.14 subprocess-boundary flake class did not manifest
  in this run).
* `python manage.py check`: System check identified no issues.
* `python manage.py makemigrations --check --dry-run`: No changes
  detected (no model change).
* `python manage.py migrate --plan`: unchanged (final entry
  `runs.0012_semantic_decision_record`).
* `git diff --check`: clean.

No deployment performed in this commit; production does not move until
independently reviewed approval, and S2-C (and this FU1) explicitly
MUST NOT deploy. Qualification V3 is NOT started.

**PRODUCT-INTEL.SEMANTIC-AUTHORITY-V2-S2-C (Semantic Authority V2 —
Final Semantic V2 Contract + Eligibility + Execution Wiring) —
IMPLEMENTED / APPROVED / FROZEN (AMENDED IN PART BY S2-C-FU1; approval
recorded at the start of Q3-A)**

**PRODUCT-INTEL.SEMANTIC-AUTHORITY-V2-S2-C (Semantic Authority V2 —
Final Semantic V2 Contract + Eligibility + Execution Wiring) —
IMPLEMENTED / APPROVED / FROZEN (AMENDED IN PART BY S2-C-FU1; approval
recorded at the start of Q3-A)**

Bounded FINAL-CONTRACT + WIRING phase on the authoritative starting SHA
`c6caa23c024e48962191a0c856230b684fb21c3c` (S2-B-FU1, PENDING FINAL
REVIEW; baseline collection 6270). Canonical spec: PLAN §26.26; decision
record: AD-070. S2-C adds the FIRST FINAL Semantic V2 contract adapter
and wires V2 semantic execution into the comparable-research execution
flow for V2-eligible candidates. S2-C does NOT declare the V2 route
QUALIFIED for the new contract (explicit marker `V2_AUTHORITY_QUALIFIED
= False`; Qualification V3 comes after S2-C review/freeze) and gives V2
outputs ZERO production authority: no Machine Price, no canonical 4A
bucket, no Reviewed Price, no headline market statistics, no AI-
Assisted Comparable pricing output, no UI authority presentation, no
vendor authority, and no V2 human-review candidate. No migration (the
V2 record reuses the universal envelope row via the registered second
adapter); no deployment. After S2-C, the V1 live path is unchanged
(its predicate, prompt, parser, route, and runtime are untouched) and
V2 outcomes are evidence/provenance awaiting model qualification.

**The final V2 contract (frozen in code).**

* **Input V2** — NEW `research/semantic_v2.py`: `SemanticMatchCaseV2`,
  a versioned immutable value object (23 required fields, no silent
  defaults; absent candidate facts are explicit None) with five clearly
  separated sections — TARGET (case id, requested MPN, requested
  description); CANDIDATE LISTING (source URL, title, published MPN
  field, published SKU, brand/condition when separately observed, the
  reserved structured-listing-evidence section, the commercial
  price/package context labeled NEVER identity evidence, the frozen 3C
  evidence source); DETERMINISTIC IDENTITY CONTEXT (IdentityStateV2,
  substate, primary signal, all bounded signals, frozen normalized
  keys, the frozen relationship-requirement snapshot — contract-
  derived, not caller input); CONTEXT PROVENANCE (the bounded
  ContextProvenance classes as present — the three classes remain
  distinct; CUSTOMER_RETRIEVAL_RELATION is retrieval-only, zero
  identity authority); PRODUCT EVIDENCE (the authority-side
  ProductEvidenceProfileV2 — deterministic/reviewed only). Construction
  fails closed on a non-UNCERTAIN state, a context that disagrees with
  the frozen re-derivation of the assessment, a requirement that
  disagrees with the frozen table, or an unsupported profile.
* **Eligibility V2** — `is_v2_semantic_eligible(assessment)`: the frozen
  S2-A derived state only — DETERMINISTIC_UNCERTAIN -> eligible (U1 /
  U2 both signals / U3 / U4 / U5 both bounded near-miss shapes);
  VERIFIED / CONFLICT / UNEVALUABLE -> never eligible. No manufacturer
  special case; no Levenshtein; no arbitrary substring matching; the
  frozen V1 predicate is unchanged and remains the only V1 gate. The
  motivating Micron-style explicit near miss (requested …YYR vs
  candidate …YY: 3C MPN_MISMATCH, S2-A U5/NEAR_MISS_TRUNCATION) reaches
  the V2 semantic entry point.
* **Safe product-evidence builder** —
  `build_v2_product_evidence_profile(observation, context_provenances,
  matched_facts)`: STRONG is reachable only from bounded facts grounded
  in LISTING_PRODUCT_TITLE / REVIEWED_PRODUCT_CONTEXT (the frozen
  source vocabulary has no model-claim member and the builder
  signature accepts no model output — the V2 model's matched_attributes
  can never become authority facts; proven by test: a V2 MATCH/HIGH
  with rich claimed attributes leaves the derived quality LIMITED). Fail
  closed on ungrounded/unsupported facts. DOCUMENTED LIMITATION: the
  current main-flow deterministic extraction proves no exact bounded
  identity-dimension equality for listing candidates, so the live path
  passes matched_facts=frozenset() — candidates remain at most LIMITED
  / WEAK under the frozen S2-A bar (NEEDS_REVIEW until future evidence
  infrastructure); nothing is fabricated; the S2-A evidence bar is not
  weakened.
* **Output V2** — strict structured response: decision (MATCH /
  NO_MATCH / UNCERTAIN), confidence (HIGH/MEDIUM/LOW), a bounded 17-
  member generic reason-code vocabulary (no manufacturer-specific
  codes), bounded structured matched/conflicting attributes (12
  observation dimensions incl. PACKAGING_QUANTITY / BUNDLE /
  ACCESSORY_RELATION / BRAND / REVISION_OR_SUFFIX / CONDITION), bounded
  missing-critical dimensions, and a structured ConflictClass set
  validated against the frozen S2-A vocabulary. Frozen
  REASON_CODE_RULES keep reason/conflict coherence (NO_MATCH_CAPACITY
  requires ConflictClass.CAPACITY; NO_MATCH_MULTIPLE_CONFLICTS requires
  ≥2 ALWAYS_HARD; MATCH/UNCERTAIN never carry an ALWAYS_HARD class;
  NO_MATCH is always conflict-grounded). Unknown enums, missing
  fields, extra fields (no chain-of-thought surface), malformed lists,
  and incoherent combinations all fail closed. CONDITION stays
  PRICE_DIMENSION_ONLY; BRAND stays REVIEWABLE; PACKAGING_QUANTITY stays
  ALWAYS_HARD (physical-product equivalence ≠ sales-unit equivalence).
* **Prompt V2** — NEW `semantic/contract_v2.py`: `SEMANTIC_PROMPT_
  VERSION_V2 = "2.0"`, used unchanged by Qualification V3 unless an
  actual defect is found first. The frozen system prompt states the
  commercial-semantic-equivalence task; the explicit NOT-asked-to rules
  (no price estimation, no Machine Verified decisions, no overriding
  deterministic HARD_CONFLICT, no inferring manufacturer authority, no
  turning customer aliases into manufacturer equivalence, no market-
  aggregation decisions); the identifier rules (exact MPN strong but
  not only; missing candidate MPN not automatically NO_MATCH; title MPN
  may be compatibility/reference wording; careful SKU interpretation;
  near-miss not automatically equivalent); the provenance rules
  (customer retrieval = retrieval hint only; labeled manufacturer
  relation authority = stronger evidence; product context = grounding
  only); the sales-unit rules (different pack quantity/bundle is not
  pricing-comparable as the same sales unit; accessory/tray/caddy/
  enclosure is a material conflict); and "insufficient evidence ->
  UNCERTAIN, never a guess; a false MATCH is materially worse than
  UNCERTAIN". The user prompt deterministically renders the recorded
  V2 input's five sections (the historical prompt is reconstructable
  from the persisted input alone).
* **Runtime V2** — NEW `semantic/runtime_v2.py`: the V2 pinned route
  (amax/qwen3.8-27b PRIMARY, vllm-262k/Qwen3.6-27B-262K FALLBACK — the
  currently frozen qualified route identities, carried as V2 CONTRACT
  data, NOT the universal envelope; drift-pinned to the frozen FU3A
  route), temperature 0.0 / max_tokens 32768, fallback on EXECUTION
  FAILURE ONLY (a valid primary response at any confidence is final —
  no voting/consensus/disagreement/low-confidence/NO_MATCH fallback),
  model identity verification, bounded per-attempt provenance +
  evaluation instants, strict V2 output at the boundary (malformed ->
  MALFORMED_JSON; unknown/incoherent -> SCHEMA_INVALID), and the
  explicit `V2_AUTHORITY_QUALIFIED = False` marker. The V1 runtime is
  untouched.

**V2 persistence adapter (second registered) + execution wiring.**

* NEW `research/semantic_decision_v2.py` registered at the S2-B
  extension point: `SemanticDecisionRecordV2` (exact binding ("V2",
  "2.0", 1, 1, "SEMANTIC_AUTHORITY_V2_S2A_FU2"), the exact recorded V2
  input as the case section, the strict structured output, the V2
  route-pinned attempts, the derived audit snapshots incl. product
  evidence quality, self-verifying digests), the strict V2 payload
  codec (envelope schema 1 reused — no model change, no migration), the
  V2 zero-live replay (reconstruction + S2-A re-derivation + derived-
  agreement proof; exact-binding gate; a future V2-lineage binding is
  refused explicitly), the V2 run-binding check (recorded case target
  MPN/description == the run's canonical request), and
  `SEMANTIC_V2_ADAPTER`. Cross-adapter reinterpretation fails closed in
  both directions. The version-neutral transport-provenance value
  objects are reused from the first registered adapter module; the V2
  route pin and family rules are V2-adapter-owned. The universal
  envelope, the row, migration 0012, and the service are UNCHANGED (the
  codec registry gains the second entry; SUPPORTED_CONTRACT_BINDINGS is
  now the V1+V2 union, computed from the registry).
* NEW `execution/semantic_decision_v2_execution.py` + orchestration:
  after the unchanged V1 semantic integration and 4A aggregation,
  every V2-eligible candidate receives exactly one V2 evaluation on the
  V2 pinned route; ALL outcomes (MATCH / NO_MATCH / UNCERTAIN /
  RUNTIME_FAILURE / fallback success / fallback failure) persist as
  `SemanticDecisionRecordV2` in the atomic final publication block
  through the unchanged S2-B service. The 4D-D alias-expanded paid-
  search batch carries CUSTOMER_RETRIEVAL_RELATION provenance in the
  recorded V2 input (the 4D-D firewall restricts the V1 authority path
  only — V2 is persist-only, so the motivating alias-retrieved near
  misses reach the V2 semantic layer). V1 coexists unchanged: V1-
  eligible candidates run BOTH the unchanged V1 evaluation (V1 MATCH
  still creates its prompt-1.1 review candidate) and the new V2
  evaluation; the explicit V1->V2 switch decision belongs to
  Qualification V3. No V2 ExecutionDetailCode vocabulary, no V2
  execution-evidence rows (the ledger is the S2-B audit surface), no V2
  human-review candidate.

**Authority firewall (binding until Qualification V3).** No production
code path treats a V2 MATCH/HIGH as pricing-authoritative: V2 outcomes
are not in the 4A input, not in the review-candidate input, not in the
snapshot payload, and not in any public summary; the aggregation layer
owns no semantic output interpretation; the persistence layer owns no
authority logic; the V2 execution module imports no aggregation / review
/ price codec surface (mechanically guarded); `V2_AUTHORITY_QUALIFIED
is False` (drift-pinned in the adapter). The motivating-case test proves
a full run with a V2 MATCH/HIGH near-miss (retrieved through the
ESTABLISHED 4D-D alias relation, recorded as CUSTOMER_RETRIEVAL_
RELATION with derived relationship authority NOT_ESTABLISHED and tier
NEEDS_REVIEW) leaves Machine Price, Reviewed Price, the price summary,
and the review queue exactly the deterministic-only values.

Test preservation: no test deleted, renamed, skipped, xfailed,
deselected, ignored, or weakened merely to obtain green. Eleven existing
nodes whose pins encoded the S2-B-endpoint registry state ("exactly one
registered adapter" / "V2 is an unknown contract") were corrected ONLY
in that expectation while preserving the safety property (explicit,
fail-closed version-adapter dispatch): `test_supported_bindings_are_
exactly_the_frozen_v1_tuple` (now exactly the V1+V2 bindings, in
registration order), `test_supported_bindings_are_the_registry_union`
(len 2), `test_envelope_schema_version_and_semantic_contract_are_
distinct_axes` / `test_unknown_semantic_contract_fails_closed_at_
dispatch` / `test_unknown_semantic_contract_error_is_not_a_v1_shape_
error` (the unknown-contract axis is proven with actually unregistered
keys — "V2" is now registered), `test_registry_lookup_is_explicit_and_
fail_closed` (1xV2 registered; 2xV1/V2 and 1xV9 unregistered),
`test_v1_record_is_the_registered_v1_adapter_record` (unregistered
pairs 1xV9 / 2xV1 / 2xV2), `test_registry_is_the_explicit_version_
adapter_extension_point` (registry len 2; both adapters' envelope
version == SEMANTIC_DECISION_SCHEMA_VERSION; fail-closed pairs minus
1xV2), `test_storage_carries_unknown_semantic_contract_but_
interpretation_fails_closed` (storage/interpretation property proven
with "V9"), and `test_only_the_service_module_references_the_ledger_in_
execution` (the exact ledger-reference allowlist gains the S2-C V2
wiring module; the V1 path's zero-touch property is proven by the
adjacent unchanged nodes). Why each is a requirement correction: S2-C
mandates registering the V2 adapter at the S2-B extension point — the
"currently one adapter" / "V2 unknown" pins encoded the pre-S2-C state,
and every corrected node preserves (and where possible strengthens) the
underlying safety property (interpretation requires an explicitly
registered, exactly-bound adapter; unknown contracts fail closed; the
ledger-reference surface stays a narrow explicit allowlist). The
S2-B boundary MODULES guard set gains the fifth research module (the
same eight guards apply — strengthened) and the package-export pin
gains the V2 surface (strengthened); a new adjacent node proves cross-
CONTRACT reinterpretation (a V1-shaped body under the registered V2
name) is refused at the V2 adapter. New nodes: 233 across seven new
files (contract 60, prompt 33, runtime 29, adapter 50, boundaries 32,
execution 20, motivating case 9) + 16 auto-expanded directory scans for
the two new research modules + 8 auto-expanded S2-B boundary guards + 1
new cross-contract persistence node. No test file decreased.

Validation (this session, candidate pass — final approval remains with
independent review):

* Collection baseline at `c6caa23`: **6270**; final: **6528** (+258 =
  233 new-file nodes + 16 auto-expanded directory scans [domain +2,
  providers +2, runs +2, web +2, research-core per-file +8] + 8 auto-
  expanded S2-B boundary MODULES guards + 1 new cross-contract node; no
  file decreased).
* Focused new S2-C: contract **60 passed**, prompt **33 passed**,
  runtime **29 passed**, adapter **50 passed**, boundaries **32 passed**,
  execution wiring **20 passed**, motivating case **9 passed** (233
  combined, 0 failed).
* Focused S2-A: `tests/research/test_semantic_authority_v2.py` +
  boundaries -> **157 passed, 0 failed** (unchanged).
* Focused S2-B/FU1 (the six S2-B test files after the documented
  in-place corrections) -> **216 passed, 0 failed**.
* Semantic runtime / semantic integration / persistence / replay /
  human-review / 2A / 3C / 4A focused suites: green (see full suite).
* Full suite: **6528 passed, 0 failed**, 39 subtests passed, 0 errors,
  0 skipped, 0 xfailed, 0 deselected (the documented fixed eleven-node
  Windows/Python-3.14 subprocess-boundary flake class did not manifest
  in this run; during earlier focused batches, allowlist members
  `test_research_run_boundaries::test_the_domain_still_imports_without_
  django_present`, `test_enterprise_ssd_boundaries` x2,
  `test_listing_normalization_boundaries::test_importing_the_research_
  core_still_pulls_in_no_third_party_dependency`,
  `test_research_identity_boundaries::test_importing_the_research_core_
  pulls_in_no_third_party_dependency`, and
  `test_specification_boundaries::test_importing_specifications_pulls_in_
  no_third_party_dependency` failed once each with the recorded
  `subprocess.run(capture_output=True) -> Popen -> _get_handles ->
  _make_inheritable -> OSError: [WinError 6]` signature before any
  project code runs (load-sensitive); every one re-passed on isolated
  retry; the allowlist was NOT expanded and no node outside it failed).
* `python manage.py check`: System check identified no issues (0
  silenced). `python manage.py makemigrations --check --dry-run`: No
  changes detected (the runs model change is docstring-only — fields
  and help text untouched). `python manage.py migrate --plan`: includes
  `runs.0012_semantic_decision_record` (Create model SemanticDecision
  Record) as the final entry — unchanged.
* `git diff --check`: clean.

No deployment performed in this commit; production does not move until
independently reviewed approval, and S2-C explicitly MUST NOT deploy.

**PRODUCT-INTEL.SEMANTIC-AUTHORITY-V2-S2-B-FU1 (Semantic Authority V2 —
Decouple the Persistence Envelope from Semantic V1) — IMPLEMENTED /
PENDING FINAL REVIEW**

Bounded ARCHITECTURE CORRECTION on the pending S2-B candidate, on the
authoritative starting SHA `95d9fd903cf941996d63dcd9b7f48265daf7c2a4`
(S2-B, PENDING FINAL REVIEW; baseline collection 6227). Canonical spec:
PLAN §26.25; decision record: AD-069 (amending AD-068 in part). S2-B is
NOT approved: independent review found one architecture blocker — the
durable record/codec/replay infrastructure was hard-bound to the OLD
semantic V1 contract (semantic contract "V1", prompt "1.1", the exact
V1 prompt-input/output shape, and the exact current primary/fallback
provider/model route), which would have forced S2-C's final V2 semantic
contract either into the obsolete V1 persistence contract or into a new
persistence schema before schema v1 was ever used live. FU1 makes the
durable persistence ENVELOPE versionable independently from the semantic
contract it contains. No Semantic V2 contract is invented; no live
execution is wired; no V2 authority is enabled; no migration change; no
deployment. After FU1, production behavior is identical to the starting
SHA.

**The correction (exact architecture).** The version axes are now
independent: persistence envelope version != semantic contract version
!= prompt version != semantic input schema version != semantic output
schema version != runtime route version.

* **Universal envelope foundation** — `research/semantic_decision_
  record.py` rewritten: canonical encoding discipline (sorted keys,
  compact, ASCII, no floats), the strict decode helpers (exact key sets,
  strict enums, explicit nullability, sorted-unique set encodings, float
  refusal), the universal persistence binding (run UUID canonical,
  assessment_index non-negative int, source_url non-empty) with its
  section encoding/validation, the bounded error vocabulary
  (SemanticDecisionCodecError / SemanticDecisionReplayError), and the
  `SemanticDecisionContractAdapter` extension point (frozen dataclass:
  envelope_schema_version, semantic_contract_version, supported_
  bindings, record_type, + encode/decode/replay/run_binding_violation).
  It owns no semantic contract value.
* **Universal envelope codec** — `research/semantic_decision_codec.py`
  rewritten: `SEMANTIC_DECISION_SCHEMA_VERSION` (1) is now explicitly
  the PAYLOAD FORMAT (envelope) version — the row's `schema_version`
  column — independent of the recorded semantic contract version; the
  explicit adapter REGISTRY (a frozen tuple, currently exactly the
  Semantic V1 adapter) is the version-adapter extension point. Decode:
  row version registered -> payload is a mapping with no floats -> the
  payload's declared envelope version agrees with the row's -> the
  universal binding is exact and valid -> the `contract` section names
  a semantic contract version (the dispatch key) -> dispatch on the
  RECORDED (envelope schema version, semantic contract version) pair to
  the registered adapter — no adapter: explicit fail-closed refusal
  ("no registered contract adapter interprets this payload"), never
  best-effort decoded, never reinterpreted under a different contract.
  Encode: dispatch on the record's registered adapter type + universal
  framing self-check. `canonical_payload_digest` unchanged. The three
  universal research modules name no V1 route token and no quoted V1
  contract/prompt literal (mechanically guarded by test).
* **Universal replay dispatch** — `research/semantic_decision_replay.py`
  rewritten: `SUPPORTED_CONTRACT_BINDINGS` is exactly the union of the
  registered adapters' supported bindings (no gate/registry drift —
  currently the single V1 tuple); `replay_semantic_decision` reads the
  RECORD's recorded contract identity (never current module constants),
  refuses unsupported bindings explicitly ("refuses to reinterpret"),
  then selects the exact registered adapter and delegates the version-
  owned replay to it.
* **Semantic V1 adapter (first registered)** — NEW `research/
  semantic_decision_v1.py` owns, and ONLY it owns: the V1 contract
  identity (semantic contract V1, prompt 1.1, input/output schema v1,
  authority contract SEMANTIC_AUTHORITY_V2_S2A_FU2 = `V1_CONTRACT_
  BINDING`); the V1 pinned route (amax/qwen3.8-27b primary, vllm-262k/
  Qwen3.6-27B-262K fallback — a V1 contract rule, NOT an envelope
  invariant; drift-pinned to the frozen FU3A route); the V1 runtime-
  provenance mirrors (drift-pinned); the V1 prompt-input shape
  (SemanticPromptInput); the V1 typed record `SemanticDecisionRecordV1`
  (RENAMED from SemanticDecisionRecord, so the V1 payload is no longer
  conflated with the universal schema — the V1 exact-binding check, the
  V1 route pin, the S2-A context validation, the evaluation/execution
  coherence rules, and the self-verifying section digests all remain,
  now as V1-adapter rules); the strict V1 payload codec; the V1 pure
  zero-live replay (reconstruction + S2-A re-derivation + the derived-
  agreement proof); the V1 run-binding check (recorded prompt-input
  target MPN/description == the run's canonical request); and the
  registered instance `SEMANTIC_V1_ADAPTER` (envelope schema 1, semantic
  contract V1, supported bindings = (V1_CONTRACT_BINDING,), record type
  = SemanticDecisionRecordV1). The V1 payload's PERSISTED BYTES are
  byte-identical to the S2-B schema-v1 payload (same sections, same
  canonical encoding, same digests): no data migration, no re-encoding
  of existing artifacts.
* **Universal service** — `execution/semantic_decision_persistence.py`
  is contract-agnostic: persist dispatches the artifact through the
  registry (unregistered artifact type -> TypeError; the service names
  no V1 literal); load = digest verification + universal decode;
  replay = digest + universal decode + the universal binding
  verification (run exists, index in range, recorded source URL matches
  the run's persisted assessment at that index) + the ADAPTER-SPECIFIC
  recorded request-identity check (`adapter.run_binding_violation`) +
  the universal replay dispatch. The service owns no authority
  derivation logic (mechanically guarded) and no contract-specific
  assumption.
* **Model / migration UNCHANGED** — `runs.SemanticDecisionRecord` fields,
  help text, constraints, index, ordering, and migration 0012 (single
  additive CreateModel) are untouched — no replacement migration (the
  existing DB row was already a generic opaque payload box); only the
  model docstring is corrected.

**The important distinction (anti-reinterpretation preserved).** The
fix is NOT "allow arbitrary version strings while decoding everything as
V1": the STORAGE/TRANSPORT layer durably identifies/versions an artifact
without assuming any particular semantic contract (a row whose payload
names an unregistered contract with a CONSISTENT digest anchor stores
fine — proven by test); the INTERPRETATION/REPLAY layer requires a
registered, explicitly supported version-specific adapter, and unknown
or future semantic contracts fail closed at BOTH the codec dispatch and
the replay gate — never best-effort decoded, never silently re-
interpreted under the current contract.

**Immutability wording (audit correction).** The documentation that
claimed `editable=False` "enforces" immutability is corrected (model
docstring + service docstring): `editable=False` is NOT database
immutability enforcement — it only keeps fields out of Django auto-
generated forms. The ledger's immutability is the APPLICATION contract:
the single service-owned append-only write path that never overwrites,
the (run, assessment_index) uniqueness constraint, and the whole-
artifact digest anchor verified on every read; out-of-band mutation
(QuerySet.update() / raw SQL) bypasses the service and is detected
where the digest anchor differs — every read of the mutated row then
fails closed. No DB triggers added.

**Backward compatibility / no-wiring / authority.** Historical V1
artifacts decode/replay byte-exactly as before (the V1 payload format is
unchanged); legacy absence remains distinct (load returns None — never
NO_MATCH / NOT_EVALUATED / AI failure, never fabricated); the current V1
live execution path still creates and reads ZERO ledger records
(no-wiring tests unchanged); the S2-A frozen authority contract is
unmodified (the V1 adapter consumes it through the research package's
public export surface; the S2-A no-wiring lexical guards pass);
human-review behavior is unchanged; zero live AI/network work is
enforced by the unchanged sentinels. S2-C (final V2 input/output
contract + live wiring) is NOT started and will register its own V2
adapter through the same explicit extension point — the envelope, the
row, the migration, and the service do not change for that reason.

Test preservation: no test deleted, renamed, skipped, xfailed,
deselected, ignored, or weakened merely to obtain green. Existing nodes
whose pins encoded the now-rejected coupling (artifact schema v1 ==
semantic V1 forever, at the universal layer) were corrected ONLY in that
expectation while preserving the safety property (interpretation
requires an explicitly supported exact semantic contract): the record
class references move to `SemanticDecisionRecordV1` (mechanical rename
following the concept rename); the encode non-record TypeError pin moves
from "expected SemanticDecisionRecord" to "expected a registered
semantic-decision record artifact" (the dispatch is now on the registry);
the V1 contract/prompt/authority-binding rejection nodes now test the V1
adapter's pin (same rejections, same safety); the private section-
encoder imports move to the V1 module; the boundaries MODULES guard set
gains the fourth research module (the same eight guards apply —
strengthened); the package export pin updates to the new surface. New
nodes: 35 (5 record + 8 codec + 3 replay + 11 boundaries [3 new
decoupling guards + 8 auto-expanded parameterized nodes] + 4 runs + 4
persistence). In addition, the fourth research file auto-enters the
existing parametrized directory scans (domain caller-token, provider,
runs-persistence, web research, and the four research-core per-file
scans in `test_research_identity_boundaries.py`): +8 expanded nodes; no
test file decreased.

Validation (this session, candidate pass — final approval remains with
independent review):

* Collection baseline at `95d9fd9`: **6227**; final: **6270** (+43 = 35
  new nodes + 8 auto-expanded directory-scan nodes; no file decreased).
* Focused S2-B + FU1 batch (the six S2-B test files): **231 passed,
  0 failed** (196 S2-B nodes + 35 new).
* `tests/research/` + `tests/runs/`: **2960 passed, 6 failed** — the
  6 failures are EXACT members of the documented fixed eleven-node
  Windows/Python-3.14 subprocess-boundary flake allowlist (clean-
  interpreter import guards), each with the recorded `subprocess.Popen
  -> _winapi.DuplicateHandle -> OSError: [WinError 6] The handle is
  invalid` signature at `subprocess.py:1431` before any project code
  runs (load-sensitive; a different exact subset failed on the repeat
  batch); each re-passed on isolated retry (6/6 — one required a
  second isolated attempt, the documented high-load behavior). 36
  subtests passed.
* `tests/execution/` + `tests/semantic/`: **1125 passed, 0 failed**.
* Full suite: see final report (every non-allowlist node passing;
  allowlist members re-passing on isolated retry; the allowlist NOT
  expanded).
* `python manage.py check`: System check identified no issues (0
  silenced). `python manage.py makemigrations --check --dry-run`: No
  changes detected (the model docstring change is not serialized; fields
  and help text untouched). `python manage.py migrate --plan`: includes
  `runs.0012_semantic_decision_record` (Create model SemanticDecision
  Record) as the final entry — unchanged.
* `git diff --check`: clean.

No deployment performed in this commit; production does not move until
independently reviewed approval, and S2-B-FU1 explicitly MUST NOT
deploy.

**PRODUCT-INTEL.SEMANTIC-AUTHORITY-V2-S2-B (Semantic Authority V2 —
Persistence / Codec phase) — IMPLEMENTED / AMENDED IN PART BY S2-B-FU1
(PENDING FINAL REVIEW)**

CORRECTED IN PART BY S2-B-FU1 (section above; canonical spec PLAN
§26.25, AD-069, amending AD-068 in part): the durable persistence
ENVELOPE was hard-bound to the semantic V1 contract (the record
constructor, codec, and replay gate all required semantic contract V1 /
prompt 1.1 / input+output schema v1 / authority contract S2-A-FU2 / the
V1 pinned route). FU1 moved every V1 assumption into the first
registered version-specific adapter (`research/semantic_decision_v1.py`,
record renamed `SemanticDecisionRecordV1`); the envelope (foundation,
codec framing + registry dispatch, replay dispatch, service, row,
migration) is now contract-agnostic and durably identifies any
registered semantic contract — unknown/future contracts still fail
closed at the explicit adapter dispatch. All other S2-B content stands
as recorded below.

Bounded PERSISTENCE/CODEC phase on the authoritative starting SHA
`9206126d4fb13300028256964c98f477c5d17969` (S2-A-FU2, now APPROVED /
FROZEN; baseline collection 6003). Canonical spec: PLAN §26.24; decision
record: AD-068. S2-B persists the complete Semantic Authority V2
evaluation/provenance artifact needed for future execution and zero-live
historical replay. This phase is about RECORDING semantics, not granting
new production authority. S2-C (live execution wiring under the final V2
input/output contract) was NOT started; no production execution/runtime/
UI wiring; no deployment. After S2-B, production behavior is identical to
the starting SHA. V3 qualification has NOT happened; AI authority in
production has NOT expanded.

**Architecture decision (first-class ledger, not an overloaded review
candidate).** The earlier audit found full semantic provenance exists
mainly for MATCH / AiAssistedReviewCandidate paths; NO_MATCH / UNCERTAIN /
runtime failures preserve no structured decision history for future V2
authority/replay. S2-B therefore introduces `SemanticDecisionRecord` as a
first-class persisted semantic-decision artifact — the semantic
EXECUTION/PROVENANCE LEDGER (one record per assessed entry-point
candidate; ALL outcomes: MATCH / NO_MATCH / UNCERTAIN / RUNTIME_FAILURE /
NOT_EVALUATED, with or without fallback). `AiAssistedReviewCandidate`
remains the human-review WORKFLOW artifact (MATCH outcomes only; mutable
review state; forged-confirmation protections; HARD_CONFLICT
supersession; Reviewed Price behavior) and is NOT overloaded into the
universal ledger. The two share the narrow explicit (run,
assessment_index) stable binding and reference neither other's rows.

**Storage design (versioned JSON box + separate tamper anchor).** The
additive `runs.SemanticDecisionRecord` model (migration 0012, single
CreateModel) follows the frozen snapshot-box precedent
(PriceIntelligenceSnapshot / ResearchSupplementSnapshot / ResearchFxSnapshot
/ ResearchMicronAliasSnapshot): id (UUID4), run (FK CASCADE, related_name
`semantic_decision_records`), assessment_index, schema_version (codec
version; only 1 supported), `payload` (opaque codec-encoded artifact — ALL
semantic authority fields live inside; the schema is owned by the codec,
not the model; no ad hoc semantic columns), `payload_digest` (canonical
SHA-256 of the payload stored in a SEPARATE column, computed at write time
by the service, verified on every read — the whole-artifact tamper anchor
that in-payload section digests alone cannot provide: a payload altered
via QuerySet.update()/raw SQL is caught on read, fail closed), and
created_at (persistence time; distinct from the evaluation instants inside
the payload). One record per (run, assessment_index) (unique constraint).
Artifact columns are editable=False with a single service-owned write path
that never overwrites. Why opaque rather than scattered columns: the
artifact is a versioned contract with 20+ fields; scattering them across
columns would turn every contract version into a migration and give the
runs layer interpretation rights it does not have (runs stores, it does
not interpret). No indexed-query requirement exists (lookups are by (run,
assessment_index), covered by the unique constraint); S2-B adds no UI.

**The persisted artifact (schema v1) — minimum complete, immutable,
versioned.** Sections: (1) binding — run UUID (canonical string),
assessment_index, source_url; (2) contract binding — semantic contract
`V1` (the frozen FU3A production semantic contract), prompt `1.1`,
input/output schema version 1, authority contract
`SEMANTIC_AUTHORITY_V2_S2A_FU2` (the S2-A contract as frozen through
S2-A-FU2) — the artifact binds to the exact versions under which it was
produced; anything else fails closed at construction/decode; (3)
deterministic V2 context — IdentityStateV2, V2 sub-state, relationship
signals (primary + bounded overlay; constructor-validated as a legitimate
S2-A context), normalized requested/candidate keys, plus the derived
relationship-requirement snapshot; (4) product evidence — the bounded
`ProductEvidenceProfileV2` (usable-title fact + matched facts, each =
dimension x grounded candidate-side sources) in versioned encoded form,
the derived `ProductEvidenceQuality` snapshot, and the context provenances
(MANUFACTURER_PRODUCT_CONTEXT / MANUFACTURER_RELATION_AUTHORITY /
CUSTOMER_RETRIEVAL_RELATION) as actually present at evaluation time; (5)
recorded prompt input — the exact V1 case fields (case_id, target
MPN/description, candidate title/MPN field/SKU/specs, evidence source) —
the historical prompt is deterministically reconstructable without any
live call; (6) recorded semantic output — evaluation state (NOT_EVALUATED
/ EVALUATED / RUNTIME_FAILURE), decision (MATCH / NO_MATCH / UNCERTAIN),
confidence (HIGH / MEDIUM / LOW), structured `ConflictClass` set, bounded
reason code, recorded attribute lists — the V1 output contract admits no
prose, none is stored; a RUNTIME_FAILURE never carries a decision (never
interpreted as NO_MATCH); (7) runtime provenance — attempts in call order
(role PRIMARY/FALLBACK, number, provider, model, bounded outcome; the V1
pinned route is enforced), fallback_used, fallback reason, bounded final
failure class (family-consistent with attempt count), actual
provider/model (the OK attempt's; None on any failure), ISO-8601 UTC
evaluation instants (absent, never defaulted, for NOT_EVALUATED) — no
latency, no raw body, no exception text, no float anywhere (refused at
canonical encoding); (8) derived audit snapshots — relationship authority,
authority tier, fired rules under the exact bound contract version; (9)
integrity — self-verifying canonical SHA-256 input digest (binding +
contract + context + product evidence + prompt input) and output digest
(evaluation + execution + derived); the record constructor refuses a
record whose stored digests do not agree with its own sections.
Persisted-vs-re-derived: source inputs are persisted; only the small
derived set above is persisted (tamper/audit purpose — a reviewer sees
exactly what the frozen contract produced at evaluation time); everything
else is strictly re-derived and never stored; where both source inputs and
derived results are stored, the REPLAY path proves they agree.

**Strict versioned codec.** `research/semantic_decision_codec.py` (pure;
schema v1): exact field set at every level (missing AND extra keys
rejected); strict enums (unknown values rejected; set encodings sorted and
unique — no lossy collapsing); no float authority data (a float anywhere
in a payload is rejected); no silent defaulting of missing safety fields
(nullable = present key with null; an absent key is an error); decode wraps
every constructor/validation failure (including the record's digest
self-verification) in the bounded `SemanticDecisionCodecError`;
unsupported schema versions fail closed (no best-effort migration);
`canonical_payload_digest` = SHA-256 of the canonical (sorted-keys,
compact, ASCII) payload encoding (the digest-column value).

**Pure replay / reconstruction (zero-live).** `replay_semantic_decision`
(`research/semantic_decision_replay.py`; stdlib + research exports only —
no Django, no network, no clock, no semantic-runtime import): (a)
contract-binding gate — the known safe-replay envelope is EXACTLY
`("V1", "1.1", 1, 1, "SEMANTIC_AUTHORITY_V2_S2A_FU2")`
(`SUPPORTED_CONTRACT_BINDINGS`); any other binding (unknown OR future) is
refused explicitly — an old persisted decision is never silently
reinterpreted under a newer contract, and the historical binding is never
substituted by current module constants (the gate reads the RECORD's
versions); (b) reconstructs the historical `SemanticEvaluationV2` (the
exact evaluation used at the time; RUNTIME_FAILURE replays as
SEMANTIC_UNAVAILABLE-shaped, never NO_MATCH; NOT_EVALUATED replays as the
deterministic-policy state, never an AI failure); (c) reconstructs the
S2-A authority inputs (`IdentityStateAssessmentV2`, product-evidence
profile, context provenances, recorded prompt input); (d) re-derives under
the frozen S2-A module (relationship requirement, product evidence
quality, relationship authority, `derive_authority_tier` with no human
overlay — the overlay is a later workflow concern); (e) derived-agreement
proof: every stored derived audit snapshot must EXACTLY agree with the
re-derivation — disagreement (or a derivation that fails closed on the
recorded inputs) is a `SemanticDecisionReplayError`. The service-level
replay adds full binding verification against the run's persisted
evidence: the recorded request identity must equal the run's canonical
request, and the recorded source URL must bind to the run's snapshot
assessment at the recorded index (a same-request cross-run or out-of-range
artifact cannot replay over this run's evidence).

**Persistence service (the API future S2-C will call; NOT wired into live
execution in S2-B).** `execution/semantic_decision_persistence.py`
(execution composes research interpretation with runs storage — the runs
layer cannot import research under the frozen boundary):
`persist_semantic_decision` (encode + digest + transactional create;
run_id binding check; never overwrites — `SemanticDecisionAlreadyRecorded
Error`), `load_semantic_decision` (digest verification + strict decode;
ABSENCE returns None), `replay_semantic_decision_record` (load + binding
verification + pure replay; absent record raises
`SemanticDecisionRecordNotFoundError`). The service owns no authority
derivation logic (it composes the research-layer replay; mechanically
guarded).

**Backward compatibility.** Existing historical runs created before
V2/S2-B remain readable exactly as before. NO SemanticDecisionRecord is
ever fabricated for a legacy run: absence of a V2 semantic artifact means
"legacy semantic provenance unavailable under V2" — NOT NO_MATCH, NOT
NOT_EVALUATED, NOT an AI failure (pinned by test). Historical V1 behavior
is exactly what it was.

**No-wiring proof (S2-B scope boundary).** The current V1 semantic
execution path creates and reads ZERO ledger records: proved by a
fake-transport `evaluate_semantic_matches` execution test (the unchanged
in-memory V1 result is produced; the ledger count stays 0; a pre-existing
record is neither read nor mutated) and by source scans (no execution
module other than the S2-B service references the persistence surface; the
web layer references nothing). Live semantic execution wiring is S2-C,
together with the final V2 input/output contract — this prevents persisting
a temporary contract that would immediately become obsolete.

**S2-A contract preservation.** The frozen S2-A module and its export
surface are UNMODIFIED. The new pure modules consume the V2 vocabulary
through the research package's public export surface (the S2-A no-wiring
lexical guards pass unmodified). The runtime-provenance vocabularies are
mirrors of the frozen FU3A runtime (AttemptOutcome / SemanticFailureClass
/ SemanticFallbackReason + route constants), drift-pinned by tests — the
pure research layer imports no semantic runtime surface (the established
V2SemanticDecision-mirrors-SemanticDecision precedent). The recorded
derived snapshots are produced under `SEMANTIC_AUTHORITY_V2_S2A_FU2`: U1
NOT_REQUIRED, U2 SKU_EQUALS_TARGET NOT_APPLICABLE, U2 SKU_NOT_TARGET / U3
/ U5-NM-1 / U5-NM-2 REVIEWED_RELATION_AUTHORITY_REQUIRED, U4 NOT_
APPLICABLE, the NM-2 independent ceiling, customer retrieval zero
authority, HARD_CONFLICT precedence, the ProductEvidenceQuality bar,
immutable contract tables, "Market evidence found" terminology, and the
pricing-eligible separation — encoded, not redefined (the full S2-A suite
+ mirror pins + no-wiring scans pass unchanged).

Test preservation: no test deleted, renamed, skipped, xfailed, deselected,
ignored, or weakened. Six existing model-registry / ResearchRun field pins
were extended IN PLACE to include the new additive model (the mandated
"made twice" model-addition decision — the same pattern as 4B / 4C-A /
HUMAN-REVIEW / 4D-B / 4D-D / 8A-FX-A1 added their models):
`tests/research/test_research_identity_boundaries.py` (model set),
`tests/runs/test_research_run_boundaries.py` (model set + EXPECTED_FIELDS),
`tests/runs/test_comparable_research_execution.py` (ResearchRun field
set), `tests/web/test_web_boundaries.py` (model set),
`tests/providers/test_provider_boundaries.py` (model set). The
`AiAssistedReviewCandidate` model field inventory is re-pinned unchanged by
a new node. New nodes: 42 in `tests/research/test_semantic_decision_
record.py`, 47 in `tests/research/test_semantic_decision_codec.py`, 28 in
`tests/research/test_semantic_decision_replay.py`, 31 in `tests/research/
test_semantic_decision_boundaries.py`, 20 in `tests/runs/test_semantic_
decision_record.py`, 28 in `tests/execution/test_semantic_decision_
persistence.py` (196 new-file nodes) + 28 auto-expanded nodes in existing
parametrized guard scans (3 new research files enter the domain caller-
token, provider, research-core, runs-persistence, and web research scans).
Collection did not decrease.

Validation (this session, candidate pass — final approval remains with
ChatGPT after independent GitHub review):

* Collection baseline at `9206126`: **6003**; final: **6227** (+224 = 196
  new-file nodes + 28 auto-expanded guard-scan nodes for the 3 new research
  files; no file decreased).
* Focused new S2-B: record **42 passed**, codec **47 passed**, replay
  **28 passed**, boundaries **31 passed**, runs model/migration **20
  passed**, execution service **28 passed** (196 combined, 0 failed).
* `tests/research/` + `tests/runs/` directories: **2930 passed, 0 failed**,
  36 subtests passed (the subprocess-flake class did not manifest in this
  run).
* Focused directly-affected batch (`tests/semantic/`, semantic
  integration, review-candidate persistence, human-confirmed replay
  authority, public-replay persisted authority, human-review eligibility
  contract, price-result codec, 2A comparator, 3C matching, 4A
  aggregation): **646 passed, 0 failed**.
* Full suite, 4 runs (the load-sensitive flake class manifesting
  differently each run; every failed node in every run an exact allowlist
  member, every non-allowlist node passing in every run):
  * run 1: **6225 passed, 2 failed**, 39 subtests passed, 0 errors, 0
    skipped, 0 xfailed, 0 deselected — failures exactly allowlist nodes
    1–2 (`test_domain_boundaries::test_domain_imports_without_django_
    network_or_llm_dependencies`, `test_evaluation_boundaries::test_
    loading_the_corpus_imports_no_framework_or_provider`), each with the
    recorded `OSError: [WinError 6]` signature at `subprocess.Popen ->
    _winapi.DuplicateHandle` (subprocess.py:1431) before any project code
    runs; each re-passed on isolated retry (2/2).
  * run 2: **6217 passed, 10 failed** — all 10 exact allowlist members
    (5 confirmed by name: `test_enterprise_ssd_boundaries` x2, `test_
    listing_normalization_boundaries`, `test_research_identity_boundar
    ies`, `test_specification_boundaries`, `test_research_run_boundar
    ies` — plus the domain/evaluation/provider subprocess-guard family);
    each re-passed on isolated retry.
  * run 3: **6225 passed, 2 failed** — exactly allowlist nodes 1–2 with
    the recorded WinError-6 signature; each re-passed on isolated retry
    (2/2).
  * run 4 (definitive, complete failure capture): **6216 passed, 11
    failed** — ALL ELEVEN fixed allowlist nodes failed in one run (domain,
    evaluation, provider x3 incl. `test_http_pdf_imports_no_third_party_
    dependency`, enterprise_ssd x2, listing_normalization, research_
    identity, specification, research_run_boundaries), each with the
    recorded WinError-6 signature at subprocess.py:1431; every one
    re-passed on isolated retry (11/11 — two required a second isolated
    attempt on the high-load workstation, the documented load-sensitive
    behavior). NO node outside the allowlist failed in ANY run; the
    allowlist was NOT expanded.
* `python manage.py check`: System check identified no issues (0
  silenced). `python manage.py makemigrations --check`: No changes
  detected. `python manage.py migrate --plan`: includes
  `runs.0012_semantic_decision_record` (Create model SemanticDecision
  Record) as the final entry.
* `git diff --check`: clean. No test deleted/renamed/skipped/xfail/
  deselected; no production file changed other than the S2-B files listed
  above; exactly one additive migration; no live-execution wiring (the
  no-wiring tests pass).

No deployment performed in this commit; production does not move until
independently reviewed approval, and S2-B explicitly MUST NOT deploy.

**PRODUCT-INTEL.SEMANTIC-AUTHORITY-V2-S2-A-FU2 (Semantic Authority
Contract V2 — corrective follow-up: state-specific relationship
requirements) — IMPLEMENTED / APPROVED / FROZEN**

Bounded CONTRACT-ONLY corrective follow-up on the pending S2-A-FU1
candidate (canonical spec: PLAN §26.23; decision record: AD-067; S2-A-
FU1 spec: PLAN §26.22 / AD-066, amended in part), on the authoritative
starting SHA `f54489dbd4ea8375ba6924e21f3bce161caac9e1` (baseline
collection 5989). A third independent-review blocker in the S2-A line
was corrected: FU1's identifier-relationship gate was over-broad. S2-B
was NOT started; no persistence/migrations; no production execution/
runtime/UI wiring; no deployment. After S2-A-FU2, production behavior is
identical to the starting SHA. V3 qualification has NOT happened; AI
authority in production has NOT expanded.

**Blocker — the relationship gate was global, not state-specific.**
S2-A-FU1 correctly restored U4_NO_MPN (relationship authority
NOT_APPLICABLE), but then introduced an over-broad general gate: U1 / U2
/ U3 / U5 required `RelationshipAuthority.ESTABLISHED` before
AI_ASSISTED_COMPARABLE was allowed. That is NOT the approved contract:
the relationship-authority requirement must itself be STATE-SPECIFIC.
The purpose of semantic AI is to resolve deterministic uncertainty; the
absence of deterministic / manufacturer relationship proof must not
force every uncertain identifier-shaped listing into human review.

The relationship requirement is now bounded state/sub-state-specific
contract data — `SUBSTATE_RELATIONSHIP_REQUIREMENTS`: one
`RelationshipRequirement` (NOT_APPLICABLE / NOT_REQUIRED /
REVIEWED_RELATION_AUTHORITY_REQUIRED) per permitted (sub-state, primary
identifier-relationship signal) combination (14 entries). Runtime-
immutable tuple of immutable entries, pure fail-closed lookup
`substate_relationship_requirement` (TypeError on non-V2 inputs;
ValueError on any combination the table does not define — unknown
combinations never gain authority), completeness self-checked at import
against `_PRIMARY_SIGNALS_BY_SUBSTATE` (exactly one entry per permitted
pair). Explicit per-case policies:

* **U1_TITLE_MPN -> NOT_REQUIRED.** The state exists precisely because
deterministic 3C refuses to treat title text as manufacturer identity
authority; the semantic evaluation determines whether the MPN denotes
the product itself or is merely compatibility/reference/SEO text.
MATCH + HIGH + STRONG bounded product evidence + no HARD conflict + no
REVIEWABLE conflict => AI_ASSISTED_COMPARABLE is CAPABLE WITHOUT
MANUFACTURER_RELATION_AUTHORITY (tested with no provenance at all, with
customer retrieval only, and with product grounding only).
COMPATIBILITY_WORDING / accessory / product-role conflicts remain safety
inputs through the structured conflict taxonomy (ALWAYS_HARD
supersession; reviewable ceiling) — no recall expansion bypasses safety
(tested: U1 + COMPATIBILITY_WORDING overlay + ACCESSORY_RELATION /
PRODUCT_ROLE => HARD_CONFLICT; + OTHER_MATERIAL_CONFLICT => NEEDS_REVIEW).
* **U2_SKU_ONLY -> primary-signal-specific.** SKU_EQUALS_TARGET ->
NOT_APPLICABLE: the published SKU is frozen-2A identical to the target —
the relationship is deterministically established, so there is nothing
for a reviewed source to establish; U2 + SKU_EQUALS_TARGET + MATCH/HIGH
+ STRONG + clean conflicts => capable of AI_ASSISTED_COMPARABLE without
MANUFACTURER_RELATION_AUTHORITY (tested). SKU_NOT_TARGET ->
REVIEWED_RELATION_AUTHORITY_REQUIRED: the explicitly chosen conservative
policy (the published SKU is not the target) — capped at NEEDS_REVIEW
without reviewed relationship authority (including customer retrieval,
which never satisfies it); met with MANUFACTURER_RELATION_AUTHORITY
(tested).
* **U3_PARTIAL_BOUNDARY -> REVIEWED_RELATION_AUTHORITY_REQUIRED.**
Explicit conservative policy: PARTIAL boundary evidence is weaker than
U1's exact-title-MPN. The U3 choice is bounded and explicit — the
identical (NO_CTX, MATCH/HIGH, STRONG, clean) inputs are NOT capped for
U1 (tested), so the U3 policy does not silently determine U1/U2/U5
behavior.
* **U4_NO_MPN -> NOT_APPLICABLE.** FU1 behavior unchanged: relationship
authority NOT_APPLICABLE with or without relation provenance; MATCH +
HIGH + STRONG product evidence + clean conflicts => AI_ASSISTED_COMPARABLE capable; the gate rule never fires for U4 (tested; the FU1
TestU4AutoAuthority nodes pass unchanged).
* **U5_NEAR_MISS_MPN -> near-miss-shape-specific.** NM-1
(NEAR_MISS_TRUNCATION) -> REVIEWED_RELATION_AUTHORITY_REQUIRED: an
explicit bounded U5/NM-1 policy (strict prefix/truncation is uncertainty
only, never identity proof) — capped at NEEDS_REVIEW without reviewed
relationship authority, and the NM-2-specific substitution-ceiling rule
does NOT fire for NM-1 (tested). NM-2 (NEAR_MISS_SUBSTITUTION) ->
REVIEWED_RELATION_AUTHORITY_REQUIRED: the frozen Product-lead ceiling
(amendment 1) keeps its own explicit audit rule (CEILING_NEAR_MISS_SUBSTITUTION_WITHOUT_RELATION_AUTHORITY) — without reviewed
authoritative identifier relationship the maximum automatic tier is
NEEDS_REVIEW even for MATCH + HIGH + STRONG product evidence;
MANUFACTURER_RELATION_AUTHORITY may clear that specific ceiling, subject
to all remaining gates; CUSTOMER_RETRIEVAL_RELATION never does (tested;
the FU1 NM-2 nodes pass unchanged). For U5 + NM-2 the NM-2-specific
caps-first rule is the explicit audit form of the same requirement and
subsumes the general gate (which is conditioned on the tier still being
AI_ASSISTED).
* **Verified / C1 / E1 / E2 -> NOT_APPLICABLE** (no AI-authority path
consults the requirement).

The automatic tier is capped at NEEDS_REVIEW (fired rule
CEILING_IDENTIFIER_RELATIONSHIP_NOT_ESTABLISHED, name unchanged) when —
and only when — the candidate's table entry requires
REVIEWED_RELATION_AUTHORITY and dimension B is not ESTABLISHED. The
orthogonal dimensions themselves (A: `derive_product_evidence_quality`;
B: `derive_relationship_authority`) are unchanged from FU1; all FU1
immutable-table protections are retained (27-row matrix, 4 state
policies, 3 capability entries, 8 badges, private derivation tables,
no-mutable-globals import self-check) and the new requirement table is
added to the immutability proof. Precedence HARD_CONFLICT > HUMAN_CONFIRMED > AI authority is unchanged (existing precedence node passes
unchanged). CUSTOMER_RETRIEVAL_RELATION zero-authority and the NM-2
ceiling are unchanged.

Delivered (production changes only: `research/semantic_authority_v2.py`
and its public export surface in `research/__init__.py`):

* `RelationshipRequirement` (3 members), `SUBSTATE_RELATIONSHIP_REQUIREMENTS` (14 frozen entries), `substate_relationship_requirement`
(pure fail-closed lookup); import-time completeness self-check.
* `derive_authority_tier` gate re-keyed on the requirement table (the
FU1 blanket U1/U2/U3/U5 condition removed); fired-rule name preserved,
semantics documented as the state/sub-state-specific form.
* Module docstrings, `AuthorityRuleV2` rule docstring, and U1-U5
sub-state docstrings updated to the FU2 contract; export surface adds
the three new symbols.

Test preservation: no test deleted, renamed, skipped, xfailed,
deselected, ignored, or weakened. Exactly three FU1 nodes — the ones
that encoded the newly identified blanket relationship gate — were
corrected in place (each correction preserves or redirects the
surrounding safety contract; details below). New nodes: 14 in
`tests/research/test_semantic_authority_v2.py` (TestStateSpecificRelationshipRequirement 6 — frozen/complete table, per-case requirement
pins, fail-closed lookup; TestU1AutoAuthorityWithoutRelationRequirement
3 — required behaviors 1-2 + no-cross-state-leakage; TestU2U3U5StateSpecificPolicies 5 — required behaviors 3-5, 7-10). Boundary file
corrected/extended in place: `test_v2_contract_tables_are_immutable_data` gains the requirement-table immutability/completeness/fail-closed
block; `test_v2_is_exported_by_the_research_package` gains the three new
export pins.

Corrected existing nodes (requirement corrections, not implementation-
fitting):

* `tests/research/test_semantic_authority_v2.py::TestContextProvenance::
test_customer_retrieval_cannot_grant_auto_authority` — old expectation:
  U1 + MATCH/HIGH + STRONG title-grounded profile + CUSTOMER_CTX ->
  NEEDS_REVIEW + CEILING_IDENTIFIER_RELATIONSHIP_NOT_ESTABLISHED
  (customer retrieval cannot grant U1 auto authority — via FU1's
  blanket U1 gate). Corrected expectation: customer retrieval confers
  zero relationship authority (NOT_ESTABLISHED on U1, U2-SKU_NOT_TARGET, U3, U5-NM-1, U5-NM-2) and grounds no product evidence (WEAK
  without title/facts), and the zero-authority contract is pinned where
  it is binding — every REVIEWED_RELATION_AUTHORITY_REQUIRED state +
  CUSTOMER_CTX + STRONG -> NEEDS_REVIEW + the gate rule (the NM-2-specific rule for U5-NM-2). Why the old requirement was over-broad:
  FU1's blanket U1/U2/U3/U5 gate is exactly the contract FU2 corrects —
  U1 no longer requires reviewed relationship authority, so "customer
  retrieval cannot grant U1 auto authority" was the wrong form of the
  customer-retrieval safety contract. Safety preserved: customer
  retrieval never establishes a relationship, never grounds product
  evidence, and never clears a requirement where one exists (now
  pinned on all four requirement-bearing states).
* `tests/research/test_semantic_authority_v2.py::TestContextProvenance::
test_manufacturer_product_context_alone_cannot_reach_auto_tier` — old
  expectation: U1 + PRODUCT_CTX + STRONG reviewed-grounded profile ->
  NEEDS_REVIEW (product grounding alone cannot reach the auto tier —
  via FU1's blanket U1 gate). Corrected expectation: the real contract
  (reviewed product grounding strengthens dimension A but does NOT
  establish dimension B, so it cannot clear a reviewed-relationship
  requirement) pinned on U2-SKU_NOT_TARGET, U3, U5-NM-1, U5-NM-2:
  STRONG reviewed-grounded profile + PRODUCT_CTX -> NEEDS_REVIEW +
  NOT_ESTABLISHED + the gate rule (NM-2-specific rule for U5-NM-2). Why
  over-broad: same blanket U1 gate. Safety preserved: product grounding
  != relationship authority is pinned exactly where the requirement
  exists.
* `tests/research/test_semantic_authority_v2.py::TestRelationshipAuthorityStates::test_question_bearing_states_without_relation_authority_are_capped`
  — old expectation: {U1, U2 (RETAIL-SKU-1 =
  SKU_NOT_TARGET), U3, U5-NM-1} all capped (NEEDS_REVIEW + gate rule)
  without provenance and all reaching AI_ASSISTED with RELATION_CTX +
  STRONG. Corrected expectation: capped set = {U2-SKU_NOT_TARGET, U3,
  U5-NM-1} with the identical assertions; U1 (NOT_REQUIRED) and U2 +
  SKU_EQUALS_TARGET (NOT_APPLICABLE) removed from the cap set by the
  FU2 state-specific requirement — U1's new no-gate behavior is pinned
  by dedicated nodes. Why over-broad: the old node included U1 in the
  blanket gate. Safety preserved: no authority expansion for the
  requirement-bearing states (capped without provenance; cleared only
  by reviewed relationship authority).

Validation (this session, candidate pass — final approval remains with
ChatGPT after independent GitHub review):

* Collection baseline at `f54489d`: **5989**; final: **6003** (+14 new
  nodes; collection did not decrease).
* Focused S2-A: `tests/research/test_semantic_authority_v2.py` -> **147
  passed, 0 failed**; `tests/research/test_semantic_authority_v2_boundaries.py`
  -> **10 passed, 0 failed** (157 combined).
* Focused directly-affected batch (`tests/semantic/`, 2A comparator +
  normalization, 3C matching + boundaries + real fixtures, 4A
  aggregation suites + reviewed aggregation, human-review eligibility
  contract, research identity boundaries, execution semantic
  integration): **987 passed, 1 failed** — the single failure is
  allowlist node 9 (`test_research_identity_boundaries`), the recorded
  `subprocess.Popen -> _winapi.DuplicateHandle -> OSError: [WinError
  6]` signature before any project code runs; re-passed on isolated
  retry (1/1).
* `tests/research/` directory: 2456 collected -> **2451 passed, 5
  failed**; the 5 failures are EXACTLY allowlist nodes 6–10
  (`test_enterprise_ssd_boundaries` x2, `test_listing_normalization_
  boundaries`, `test_research_identity_boundaries`, `test_specification_
  boundaries`), each with the recorded WinError-6 signature; each
  re-passed on isolated retry (5/5).
* Full suite (run 1): **5995 passed, 39 subtests passed, 8 failed, 0
  errors, 0 skipped, 0 xfailed, 0 deselected**. The 8 failures are
  EXACT members of the documented fixed eleven-node Windows/Python-3.14
  subprocess-boundary flake allowlist (nodes 1, 3, 4, 5, 6, 7, 8, 11:
  `test_domain_boundaries`, `test_provider_boundaries` x3,
  `test_enterprise_ssd_boundaries` x2, `test_listing_normalization_
  boundaries`, `test_research_run_boundaries`), each with the recorded
  WinError-6 signature at `subprocess.py:1431`; each re-passed on
  isolated retry (8/8). NO node outside the allowlist failed; the
  allowlist was NOT expanded.
* Full suite (definitive run 2): **6003 passed, 39 subtests passed, 0
  failed, 0 errors, 0 skipped, 0 xfailed, 0 deselected** — a clean
  run; the flake class did not manifest.
* `python manage.py check`: System check identified no issues (0
  silenced). `python manage.py makemigrations --check --dry-run`: No
  changes detected.
* `git diff --check`: clean. No test deleted/renamed; no production
  file changed other than `research/semantic_authority_v2.py` +
  `research/__init__.py`; no migrations; no wiring (the no-wiring tests
  pass unchanged).

No deployment performed in this commit; production does not move until
independently reviewed approval, and S2-A-FU2 explicitly MUST NOT
deploy.

**PRODUCT-INTEL.SEMANTIC-AUTHORITY-V2-S2-A-FU1 (Semantic Authority
Contract V2 — corrective follow-up: orthogonal evidence gates + frozen
mappings) — IMPLEMENTED / AMENDED BY S2-A-FU2 (PENDING FINAL REVIEW)**

CORRECTED BY S2-A-FU2 (section above; canonical spec PLAN §26.23, AD-
067, amending AD-066 in part): FU1's general state-specific gate —
reaching AI_ASSISTED_COMPARABLE required the identifier-relationship
question to be ESTABLISHED for U1/U2/U3/U5 — was itself over-broad.
The relationship requirement is now the frozen state/sub-state-specific
`SUBSTATE_RELATIONSHIP_REQUIREMENTS` table (NOT_APPLICABLE / NOT_
REQUIRED / REVIEWED_RELATION_AUTHORITY_REQUIRED per permitted (sub-
state, primary signal) combination): U1_TITLE_MPN and U2 +
SKU_EQUALS_TARGET do NOT require MANUFACTURER_RELATION_AUTHORITY; U2 +
SKU_NOT_TARGET, U3, U5 + NM-1, and U5 + NM-2 do; U4 behavior is
unchanged (NOT_APPLICABLE). The orthogonal dimension derivations (A and
B), the NM-2 ceiling, customer-retrieval zero authority, and all FU1
immutable-table protections are unchanged.

Bounded CONTRACT-ONLY corrective follow-up on the pending S2-A
candidate (canonical spec: PLAN §26.22; decision record: AD-066; S2-A
spec: PLAN §26.21 / AD-065, amended in part), on the authoritative
starting SHA `46869f9a3ee6fad638b87b71cd14ed848224c057` (baseline
collection 5972). Two independent-review blockers in the S2-A contract
were corrected. S2-B was NOT started; no persistence/migrations; no
production execution/runtime/UI wiring; no deployment. After S2-A-FU1,
production behavior is identical to the starting SHA. V3 qualification
has NOT happened; AI authority in production has NOT expanded.

**Blocker 1 — U4 description-match was re-conservatized.** S2-A made
`ContextQuality.STRONG` globally equivalent to the presence of
`MANUFACTURER_RELATION_AUTHORITY`, and the matrix's only
`AI_ASSISTED_COMPARABLE` row was MATCH + HIGH + STRONG — so a U4_NO_MPN
candidate, which by definition has no candidate MPN relationship for a
manufacturer source to establish, could not normally obtain
AI_ASSISTED_COMPARABLE. The authority prerequisites are now TWO
ORTHOGONAL, state-specific dimensions, each derived independently:

* **A. Product evidence quality** — `ProductEvidenceQuality`
  (STRONG/LIMITED/WEAK), computed ONLY from the bounded
  `ProductEvidenceProfileV2` (usable product title + bounded
  matched-attribute facts) and reviewed product-grounding provenance
  classes — never from model confidence, decisions, or model-claimed
  attributes. Each matched-attribute fact is a
  (`ProductEvidenceDimension`, grounded candidate-side source) pair:
  the dimension vocabulary is the six hard product dimensions
  (PRODUCT_FAMILY, GENERATION, CAPACITY, INTERFACE, FORM_FACTOR,
  PRODUCT_ROLE — mirroring the same-named ALWAYS_HARD conflict
  classes); the source vocabulary is EXACTLY {LISTING_PRODUCT_TITLE,
  REVIEWED_PRODUCT_CONTEXT} — no model-claim source exists, so the
  future semantic runtime cannot self-promote its authority by
  asserting arbitrary matched attributes. The frozen STRONG bar is
  bounded and testable (future-qualifiable by V3): usable title AND
  >= `STRONG_PRODUCT_EVIDENCE_MIN_MATCHED_FACTS` (2) matched facts
  spanning >= `STRONG_PRODUCT_EVIDENCE_MIN_MATCHED_DIMENSIONS` (2)
  distinct hard product dimensions. A title alone is NOT strong.
  CUSTOMER_RETRIEVAL_RELATION grounds nothing; MANUFACTURER_PRODUCT_
  CONTEXT strengthens product grounding only; unsupported or
  state-contradicting profiles fail closed (ValueError).
* **B. Identifier relationship authority** — `RelationshipAuthority`
  (ESTABLISHED/NOT_ESTABLISHED/NOT_APPLICABLE) via
  `derive_relationship_authority`: U4_NO_MPN -> NOT_APPLICABLE (the
  question does not exist; relation provenance cannot change it);
  U1/U2/U3/U5 -> ESTABLISHED only with reviewed relation provenance
  (customer retrieval confers ZERO); verified -> ESTABLISHED by the
  frozen deterministic comparator; C1 -> NOT_ESTABLISHED; E1/E2 ->
  NOT_APPLICABLE.

The 27-row matrix is re-keyed on (decision x confidence x product
evidence quality) with the SAME tier values. Reaching
AI_ASSISTED_COMPARABLE additionally requires the state-specific
relationship question to be NOT_APPLICABLE (U4) or ESTABLISHED
(U1/U2/U3/U5) — the new general state-specific gate (fired rule
CEILING_IDENTIFIER_RELATIONSHIP_NOT_ESTABLISHED) preserves S2-A's
effective requirement for U1/U2/U3 and U5-NM-1 (no authority expansion
there). The NM-2 ceiling (amendment 1) REMAINS FROZEN: U5 +
NEAR_MISS_SUBSTITUTION without reviewed authoritative identifier
relationship caps the maximum automatic tier at NEEDS_REVIEW — even
for MATCH + HIGH + STRONG product evidence; CUSTOMER_RETRIEVAL_RELATION
cannot satisfy that gate. `ContextQuality` / `derive_context_quality`
are removed; `derive_authority_tier` gains a bounded `product_evidence`
profile parameter (default = conservative state-derived profile that
can never reach STRONG by itself).

Contracted + tested required behavior:

1. U4 + MATCH/HIGH + strong approved product evidence + no conflicts
   CAN produce AI_ASSISTED_COMPARABLE.
2. U4 does NOT require MANUFACTURER_RELATION_AUTHORITY (relationship
   authority is NOT_APPLICABLE for U4 with or without relation
   provenance).
3. U4 weak/incomplete evidence remains NEEDS_REVIEW or
   EXCLUDED_LOW_CONFIDENCE per the frozen matrix.
4. U5 NM-2 + MATCH/HIGH + strong product evidence but NO
   MANUFACTURER_RELATION_AUTHORITY remains NEEDS_REVIEW (NM-2 rule
   fires).
5. U5 NM-2 + valid MANUFACTURER_RELATION_AUTHORITY may pass that
   specific ceiling, subject to the rest of the authority gates
   (STRONG product evidence required; reviewable conflict caps; hard
   conflict supersedes).
6. CUSTOMER_RETRIEVAL_RELATION cannot satisfy the NM-2 relationship
   gate (zero relationship authority; with or without product
   grounding).

**Blocker 2 — frozen contract tables were mutable dicts.** Python
`Final` does not make a dict runtime-immutable. Every frozen contract
mapping is now a runtime-immutable tuple of immutable entries (tuples /
enums / frozen dataclasses / frozensets / str) with a pure lookup
function: `SEMANTIC_OUTCOME_TIER_MATRIX` (27; `semantic_outcome_tier`),
`DETERMINISTIC_STATE_POLICIES` (4; `deterministic_state_policy`),
`CONTEXT_PROVENANCE_CAPABILITIES` (3; `context_provenance_capabilities`),
`AUTHORITY_TIER_BADGES` (8; `authority_tier_badge`), and the private
`_PRIMARY_SIGNALS_BY_SUBSTATE` / `_STATE_OF_SUBSTATE` derivation
tables. The severity frozensets and the attention-order tuple remain
immutable. The module's global namespace is import-self-checked to
contain NO dict/list/set at all, and
`test_v2_contract_tables_are_immutable_data` now actually proves
immutability with real mutation attempts (TypeError / AttributeError /
FrozenInstanceError) over every frozen authority/context/display
mapping — no `.copy()` of mutable globals; the authoritative stored
contract itself is immutable (deterministically iterable,
equality-testable, completeness-checkable).

Delivered (only production changes: `research/semantic_authority_v2.py`
and its public export surface in `research/__init__.py`):

* `ProductEvidenceQuality`, `ProductEvidenceDimension` (6 members),
  `CandidateProductEvidenceSource` (2 members), `ProductEvidenceFactV2`,
  `ProductEvidenceProfileV2` (fail-closed construction +
  cross-consistency), `STRONG_PRODUCT_EVIDENCE_MIN_MATCHED_FACTS` /
  `STRONG_PRODUCT_EVIDENCE_MIN_MATCHED_DIMENSIONS` (2/2),
  `derive_product_evidence_quality` (fail closed on unsupported
  profiles).
* `RelationshipAuthority`, `derive_relationship_authority` (state-
  specific; U4 NOT_APPLICABLE), `has_relationship_authority` retained.
* `AuthorityDecisionV2` now records BOTH orthogonal dimensions
  (`product_evidence_quality` + `relationship_authority`) for audit;
  `AuthorityRuleV2` gains `CEILING_IDENTIFIER_RELATIONSHIP_NOT_
  ESTABLISHED`; `derive_authority_tier` gains the bounded
  `product_evidence` parameter and state/profile consistency checks
  (U4 without a usable title, or E2 with one, fails closed).
* Frozen mappings converted to immutable entry tuples + pure lookups
  (Blocker 2); import-time global-namespace check forbids any mutable
  container; matrix/policy/capability/badge completeness self-checks
  retained and adapted.
* Export surface: `ContextQuality` / `derive_context_quality` removed;
  the symbols above + the four lookup functions added.

Test preservation: no test deleted, renamed, skipped, xfailed,
deselected, ignored, or weakened. New nodes: 16 in
`tests/research/test_semantic_authority_v2.py` (TestU4AutoAuthority 3 —
blocker items 1–3; TestNM2CeilingWithStrongEvidence 3 — blocker items
4–6; TestRelationshipAuthorityStates 4; TestProductEvidenceBar 6 —
bounded evidence bar, no model self-promotion, fail-closed profiles,
state consistency) + 1 in
`tests/research/test_semantic_authority_v2_boundaries.py`
(`test_v2_module_has_no_mutable_global_state`). Existing S2-A nodes
corrected in place ONLY where they encoded the now-identified flawed
U4/global-STRONG contract (each correction preserves or strengthens the
surrounding safety contract; exact nodes, old/new expectations, and
justification enumerated below). NM-2, customer-retrieval, HARD_
CONFLICT, frozen V1, 3C, and 4A tests were NOT weakened.

Corrected existing nodes (requirement corrections, not
implementation-fitting):

* `TestNM2AuthorityCeiling::test_ceiling_without_any_context` — old:
  NM-2 + MATCH/HIGH, no provenance (implicit WEAK context: the matrix
  base was already NEEDS_REVIEW, so the ceiling constrained nothing)
  -> NEEDS_REVIEW + NM-2 rule. corrected: + explicit STRONG product-
  evidence profile -> NEEDS_REVIEW + NM-2 rule (+ STRONG quality and
  NOT_ESTABLISHED relationship assertions). why: blocker 1 requires
  proving the NM-2 ceiling cannot be bypassed by "excellent
  description/product alignment"; the old pin had no product evidence
  at all. strengthened.
* `TestNM2AuthorityCeiling::test_ceiling_with_manufacturer_product_
  context` — old: + PRODUCT_CTX (LIMITED base). corrected: + STRONG
  reviewed-grounded profile (AI-eligible base) -> NEEDS_REVIEW + rule.
  why: product grounding != relationship authority; the ceiling must
  visibly cap an AI-eligible base. strengthened.
* `TestNM2AuthorityCeiling::test_ceiling_with_customer_retrieval_
  relation` — old: + CUSTOMER_CTX (WEAK base). corrected: + STRONG
  title-grounded profile -> NEEDS_REVIEW + rule + NOT_ESTABLISHED.
  why: blocker item 6. strengthened.
* `TestNM2AuthorityCeiling::test_ceiling_with_customer_plus_product_
  context` — old: combined provenance (LIMITED base). corrected: +
  STRONG reviewed-grounded profile -> NEEDS_REVIEW + rule.
  strengthened.
* `TestNM2AuthorityCeiling::test_relation_authority_satisfies_the_gate`
  — old: RELATION_CTX alone -> AI_ASSISTED + `context_quality is
  ContextQuality.STRONG` (the flawed global-STRONG coupling: RELATION
  implied STRONG, hence the auto tier, with no product evidence).
  corrected: RELATION_CTX + STRONG reviewed-grounded profile ->
  AI_ASSISTED + STRONG product quality + ESTABLISHED relationship + no
  NM-2 rule. why: blocker 1 — the matrix row is now fed by the
  orthogonal product-evidence dimension; "may pass that specific
  ceiling, subject to the rest of the authority gates".
* `TestNM2AuthorityCeiling::test_nm2_may_remain_reviewable_even_with_
  match_high` — old: PRODUCT_CTX (LIMITED base) -> NEEDS_REVIEW; human
  CONFIRMED -> HUMAN_CONFIRMED. corrected: + STRONG reviewed-grounded
  profile -> NEEDS_REVIEW (ceiling caps an AI-eligible base); HUMAN_
  CONFIRMED preserved. strengthened.
* `TestNM2AuthorityCeiling::test_nm1_has_no_substitution_ceiling` —
  old: RELATION_CTX alone -> AI_ASSISTED (implicit STRONG via RELATION).
  corrected: RELATION_CTX + STRONG profile -> AI_ASSISTED + no NM-2
  rule + no general relationship-gate rule. why: the old expectation
  relied on the flawed coupling; NM-1 + ESTABLISHED relationship +
  STRONG product evidence reaches the auto tier under the corrected
  contract. contract preserved.
* `TestNM2AuthorityCeiling::test_hard_conflict_still_supersedes_
  ceilinged_nm2` — old: NO_CTX (WEAK base) + CAPACITY conflict ->
  HARD_CONFLICT + rule. corrected: + STRONG profile (would-be AI base)
  -> HARD_CONFLICT + rule. strengthened.
* `TestContextProvenance::test_capability_table_is_exactly_frozen` —
  old: `CONTEXT_PROVENANCE_CAPABILITIES == {dict}`. corrected: frozen
  entry-tuple full-vocabulary coverage + exact per-entry capability
  sets via `context_provenance_capabilities`. why: blocker 2
  representation; exact capability contract preserved.
* `TestContextProvenance::test_customer_retrieval_is_not_manufacturer_
  context` — old: dict subscript. corrected: pure lookup. mechanical
  (blocker 2); assertions unchanged.
* `TestContextProvenance::test_product_context_does_not_establish_the_
  relationship` — old: `derive_context_quality(PRODUCT_CTX) is
  ContextQuality.LIMITED`. corrected: `derive_product_evidence_quality`
  (no-title/no-facts profile, PRODUCT_CTX) is LIMITED + U5
  relationship NOT_ESTABLISHED. why: blocker 1 — context quality was
  the flawed coupling; corrected semantics: product grounding
  strengthens dimension A but does not establish dimension B.
* `TestContextProvenance::test_customer_retrieval_alone_is_weak_and_
  gateless` — old: `derive_context_quality(CUSTOMER_CTX/NO_CTX) is
  WEAK`. corrected: `derive_product_evidence_quality`(empty profile,
  CUSTOMER_CTX/NO_CTX) is WEAK. why: customer retrieval grounds no
  product evidence and no relationship.
* `TestContextProvenance::test_relation_authority_establishes_the_
  relationship` — old: `derive_context_quality(RELATION_CTX) is
  STRONG` (exactly the flawed global-STRONG assertion). corrected:
  `derive_relationship_authority`(U5, RELATION_CTX) is ESTABLISHED /
  (U5, PRODUCT_CTX) is NOT_ESTABLISHED. why: blocker 1 — the assertion
  now tests dimension B semantics.
* `TestContextProvenance::test_customer_plus_product_stays_limited_and_
  gateless` — old: quality LIMITED. corrected: product evidence LIMITED
  (empty profile) + no relationship. why: blocker 1.
* `TestContextProvenance::test_relation_plus_customer_stays_strong` —
  old: `derive_context_quality(combined) is STRONG`. corrected: U1
  relationship authority ESTABLISHED with the combined provenance
  (customer retrieval does not dilute). why: the old STRONG assertion
  encoded the flawed coupling; corrected semantics: the relationship
  stays ESTABLISHED.
* `TestContextProvenance::test_customer_retrieval_cannot_grant_auto_
  authority` — old: U1 + MATCH/HIGH + CUSTOMER_CTX -> `context_quality
  is WEAK` + NEEDS_REVIEW. corrected: + STRONG title-grounded profile
  -> STRONG quality + NOT_ESTABLISHED relationship + NEEDS_REVIEW +
  general gate rule. why: blocker 1 — even STRONG product evidence
  cannot reach auto authority through customer retrieval. strengthened.
* `TestContextProvenance::test_manufacturer_product_context_alone_
  cannot_reach_auto_tier` — old: PRODUCT_CTX -> LIMITED + NEEDS_REVIEW.
  corrected: + STRONG reviewed-grounded profile -> STRONG + NOT_
  ESTABLISHED + NEEDS_REVIEW. strengthened (product grounding alone,
  even at STRONG product evidence, cannot reach the auto tier).
* `TestContextProvenance::test_relation_authority_can_satisfy_the_
  matrix_gate` — old: RELATION_CTX -> STRONG + AI_ASSISTED. corrected:
  RELATION_CTX + STRONG reviewed-grounded profile -> STRONG +
  ESTABLISHED + AI_ASSISTED. why: both orthogonal dimensions must be
  met.
* `TestContextProvenance::test_context_quality_is_never_ai_derived` —
  old: quality pure in provenances; MATCH/LOW -> STRONG + EXCLUDED.
  corrected: quality pure in (profile, provenances); MATCH/LOW + STRONG
  profile -> STRONG + EXCLUDED. why: the no-AI-self-derivation contract
  is preserved on the corrected dimension.
* `TestContextProvenance::test_provenance_input_must_be_a_frozenset` —
  old: `derive_context_quality(set())` TypeError. corrected:
  `derive_product_evidence_quality(profile, set())` +
  `derive_relationship_authority(v2, set())` TypeErrors (+ retained
  `has_relationship_authority(set())`). boundary extended.
* `TestCompatibilityWording::test_wording_never_changes_the_authority_
  tier_by_itself` — old: `decision.context_quality` equality.
  corrected: `product_evidence_quality` + `relationship_authority`
  equality. why: field rename under the orthogonal redesign; the
  contract (wording overlay never changes the tier) is unchanged.
* `TestAuthorityMatrixCompleteness::test_matrix_defines_all_27_
  combinations` — old: grid over ContextQuality; `set(dict)`.
  corrected: grid over ProductEvidenceQuality; entry-tuple key set.
  why: blocker 1 re-key + blocker 2 representation; completeness (27)
  preserved.
* `TestAuthorityMatrixCompleteness::test_matrix_full_table_is_frozen`
  — old: `dict == expected`. corrected: entry tuple == expected in
  canonical order + per-row `semantic_outcome_tier` lookups. why:
  blocker 2; exact tier values unchanged.
* `TestAuthorityMatrixCompleteness::test_state_policy_table_is_
  complete_and_bounded` — old: dict subscript / `.items()`. corrected:
  entry tuple + `deterministic_state_policy` lookups. mechanical
  (blocker 2); policy contract unchanged.
* `TestAuthorityMatrixCompleteness::test_match_high_incomplete_
  context_is_needs_review` — old: implicit LIMITED/WEAK context from
  provenances. corrected: explicit LIMITED profile (title, no facts) +
  LIMITED-quality assertions, all three provenance sets. why: blocker 1
  — the "incomplete evidence" premise is carried by the orthogonal
  product-evidence dimension.
* `TestAuthorityMatrixCompleteness::test_match_high_reviewable_
  conflict_is_needs_review` — old: RELATION_CTX + conflict (implicit
  STRONG). corrected: + STRONG reviewed-grounded profile -> NEEDS_
  REVIEW + rule + STRONG assertion. strengthened (the reviewable-
  conflict ceiling visibly caps an AI-eligible base).
* `TestAuthorityMatrixCompleteness::test_condition_only_conflict_
  never_caps_authority` — old: RELATION_CTX -> AI_ASSISTED (implicit
  STRONG). corrected: + STRONG profile -> AI_ASSISTED. why: the auto
  row is now fed by explicit product evidence.
* `TestAuthorityMatrixCompleteness::test_hard_conflict_supersedes_
  match_high_strong` — old: RELATION_CTX -> HARD_CONFLICT. corrected: +
  STRONG profile -> HARD_CONFLICT. why: "strong" in the pin now means
  STRONG product evidence.
* `TestAuthorityMatrixCompleteness::test_uncertain_decision_with_
  actionable_context_is_needs_review` — old: PRODUCT_CTX (implicit
  LIMITED). corrected: + explicit LIMITED profile -> NEEDS_REVIEW +
  LIMITED assertion. why: the actionable premise is made explicit.
* `TestAuthorityMatrixCompleteness::test_precedence_hard_over_confirmed
  _over_ai` — old: parts 2/3 used RELATION_CTX (implicit STRONG); part
  1 positional human argument. corrected: + STRONG reviewed-grounded
  profile for parts 2/3; `human_review=` keyword for part 1. why: the
  AI premise requires explicit product evidence; precedence contract
  unchanged; positional -> keyword forced by the new
  `product_evidence` signature parameter.
* `TestAuthorityMatrixCompleteness::test_human_rejected_on_uncertain`,
  `::test_human_outcome_not_applicable_on_verified`,
  `::test_total_combination_space_is_defined_and_fail_closed` —
  corrected: positional human argument -> `human_review=` keyword (new
  signature); the total-combination node now asserts
  `decision.product_evidence_quality is derive_product_evidence_
  quality(default_profile, context)` (was `context_quality is
  derive_context_quality(context)`). mechanical adaptation; all tier /
  rule / fail-closed contracts unchanged.
* `TestUiVocabularyContract::test_badge_concepts_are_frozen` — old:
  `dict == expected`. corrected: entry tuple + `authority_tier_badge`
  lookups + full-vocabulary coverage. why: blocker 2; exact badge
  strings preserved.
* `tests/research/test_semantic_authority_v2_boundaries.py::test_v2_
  contract_tables_are_immutable_data` — old: `isinstance(..., dict)` +
  shape checks (did NOT prove immutability). corrected: real mutation
  attempts over every frozen authority/context/display mapping (public
  + private) proving TypeError / AttributeError / FrozenInstanceError;
  deterministic iterability; equality against lookup-rebuilt tables;
  completeness; severity frozensets and attention-order tuple
  invariants retained. why: blocker 2 requirement.
* `tests/research/test_semantic_authority_v2_boundaries.py::test_v2_is_
  exported_by_the_research_package` — old: expected export set
  including ContextQuality / derive_context_quality. corrected: the
  S2-A-FU1 export surface (orthogonal dimensions + lookup functions)
  + explicit absence pins for the removed symbols. why: the export
  surface is the public contract of the corrected module.

Unchanged (still collected and green): every section A/B/C/D/G node not
enumerated above (incl. `test_nm2_match_medium_stays_needs_review`,
`test_uncertain_decision_without_actionable_context_is_excluded`,
`test_u4_does_not_gain_deterministic_authority`,
`test_u4_weak_evidence_stays_distinguishable` — docstring wording only,
`test_verified_state_needs_no_ai`, `test_conflict_state_is_hard_and_ai_
eligible`, `test_unevaluable_state_has_no_ai_authority`,
`test_uncertain_state_not_evaluated_is_needs_review`,
`test_runtime_failure_is_semantic_unavailable_never_no_match`,
`test_match_medium_is_needs_review`, `test_low_confidence_is_excluded`,
`test_no_match_is_excluded`), the full no-wiring / frozen-V1 section,
all 3C/2A/4A suites, the semantic runtime suites, and every other
frozen regression suite.

Validation (this session, candidate pass — final approval remains with
ChatGPT after independent GitHub review):

* Collection baseline at `46869f9`: **5972**; final: **5989** (+17: 16
  new orthogonal-dimension nodes in `test_semantic_authority_v2.py` +
  1 new no-mutable-global-state guard in
  `test_semantic_authority_v2_boundaries.py`). Collection did not
  decrease.
* Focused S2-A: `tests/research/test_semantic_authority_v2.py` -> **133
  passed, 0 failed**; `tests/research/test_semantic_authority_v2_
  boundaries.py` -> **10 passed, 0 failed**.
* Focused directly-affected batch (`tests/semantic/`, 2A comparator +
  normalization, 3C matching + boundaries + real fixtures, 4A
  aggregation suites + reviewed aggregation, human-review eligibility
  contract, execution semantic integration): **775 passed, 0 failed**.
* `tests/research/` directory: 2442 collected -> **2437 passed, 5
  failed**; the 5 failures are EXACTLY allowlist nodes 6–10
  (`test_enterprise_ssd_boundaries` x2, `test_listing_normalization_
  boundaries`, `test_research_identity_boundaries`, `test_specification
  _boundaries` — the clean-interpreter import guards), each with the
  recorded `subprocess.Popen -> _winapi.DuplicateHandle -> OSError:
  [WinError 6] The handle is invalid` signature before any project code
  runs; each re-passed on isolated retry (5/5).
* Full suite (run 1): **5989 collected, 5987 passed, 39 subtests
  passed, 2 failed, 0 errors, 0 skipped, 0 xfailed, 0 deselected**. The
  2 failures are EXACTLY allowlist nodes 1–2 (`test_domain_boundaries
  .py::test_domain_imports_without_django_network_or_llm_dependencies`,
  `test_evaluation_boundaries.py::test_loading_the_corpus_imports_no_
  framework_or_provider`), each with the recorded WinError-6 signature
  at `subprocess.py:1431` (`Popen -> _make_inheritable ->
  _winapi.DuplicateHandle`); each re-passed on isolated retry (2/2).
  NO node outside the allowlist failed. (The same two nodes reproduced
  the signature again on a batched file retry — the documented load-
  sensitive flake class — and re-passed in isolation.)
* `python manage.py check`: System check identified no issues (0
  silenced). `python manage.py makemigrations --check --dry-run`: No
  changes detected.
* `git diff --check`: clean. No test deleted/renamed; no production
  file changed other than `research/semantic_authority_v2.py` +
  `research/__init__.py`; no migrations; no wiring (the no-wiring tests
  pass unchanged).

No deployment performed in this commit; production does not move until
independently reviewed approval, and S2-A-FU1 explicitly MUST NOT
deploy.

**PRODUCT-INTEL.SEMANTIC-AUTHORITY-V2-S2-A (Semantic Authority Contract
V2 — contract freeze) — IMPLEMENTED / AMENDED BY S2-A-FU1 (PENDING FINAL
REVIEW)**

CORRECTED BY S2-A-FU1 (section above; canonical spec PLAN §26.22, AD-
066, amending AD-065 in part): (a) the authority matrix recorded below
was keyed on a global `ContextQuality` whose STRONG value was equivalent
to the presence of MANUFACTURER_RELATION_AUTHORITY — re-conservatizing
U4_NO_MPN; S2-A-FU1 replaced it with two orthogonal prerequisites
(bounded product evidence quality + state-specific identifier
relationship authority, with U4 NOT_APPLICABLE) and removed
ContextQuality/derive_context_quality; (b) the frozen contract tables
recorded below were mutable dicts; S2-A-FU1 made them runtime-immutable
tuples of immutable entries with pure lookup functions. All other S2-A
content (states, near-miss, taxonomy, tiers, UI vocabulary, summary
wording, no-wiring proof) stands as recorded below. CORRECTED BY S2-A-
FU2: FU1's general gate (ESTABLISHED required for U1/U2/U3/U5) was
itself over-broad — the relationship requirement is now the frozen
state/sub-state-specific `SUBSTATE_RELATIONSHIP_REQUIREMENTS` table
(U1 and U2 + SKU_EQUALS_TARGET require no reviewed relationship
authority; U2 + SKU_NOT_TARGET, U3, U5 + NM-1, and U5 + NM-2 do; U4
unchanged; PLAN §26.23, AD-067).

Bounded CONTRACT-ONLY phase on the authoritative starting SHA
`1a3c4a91bfbc6acda32025fa5145805f572185ff` (baseline collection 5838).
Canonical spec: PLAN §26.21; decision record: AD-065. The Product Lead
approved the V2 deterministic state overlay design with three amendments,
all frozen here. S2-A establishes the approved design IN CODE as a pure
contract and wires NOTHING: after S2-A, production behavior is identical
to the starting SHA. V2 is not wired into execution, semantic, runs, web,
or providers. V3 qualification has NOT happened. AI authority has NOT
expanded. No deployment may occur from this phase.

Delivered (the only production changes are one new pure module and its
public export):

* **New pure module** `product_intelligence/research/semantic_authority_v2.py`
  (stdlib + frozen research/domain imports only; no Django, no I/O, no
  network, no LLM, no mutable global state; import-self-checked contract
  tables):
  - V2 states and bounded sub-states: DETERMINISTIC_VERIFIED (V_EXACT,
    V_NORMALIZED_EXACT), DETERMINISTIC_UNCERTAIN (U1_TITLE_MPN,
    U2_SKU_ONLY, U3_PARTIAL_BOUNDARY, U4_NO_MPN, U5_NEAR_MISS_MPN),
    DETERMINISTIC_CONFLICT (C1_INCOMPATIBLE_EXPLICIT_MPN),
    DETERMINISTIC_UNEVALUABLE (E1_NO_TARGET_MPN, E2_NO_CANDIDATE_
    EVIDENCE — the E2 addition is permitted by the "at minimum" contract
    and covers no-MPN + no-usable-title listings).
  - `derive_identity_state_v2(assessment)` — the pure derivation over the
    FROZEN `ListingIdentityAssessment` (3C). It re-runs only the frozen 2A
    comparator on the same two strings 3C compared (the same call the
    assessment's own constructor invariants make) to recover the frozen
    normalized keys; out-of-contract combinations fail closed.
  - Bounded relationship signals: EXACT, NORMALIZED_EXACT,
    TITLE_MPN_TOKEN, SKU_EQUALS_TARGET, SKU_NOT_TARGET, PARTIAL_BOUNDARY,
    NEAR_MISS_TRUNCATION, NEAR_MISS_SUBSTITUTION, COMPATIBILITY_WORDING
    (overlay only; frozen 4-token vocabulary {compatible, replacement,
    interchangeable, drop-in}; word-boundary matched against the listing
    title), EMPTY_MPN_FIELD, NO_RELATION.
  - NM-1 = strict prefix/truncation on the EXISTING frozen normalized MPN
    keys (either direction). NM-2 = same length, exactly one-character
    substitution. NOT implemented: Levenshtein fuzzy matching, arbitrary
    substring matching, generic containment authority, suffix stripping,
    manufacturer-specific acceptance, normalization changes. Near-miss
    membership is NEVER identity authority; outside NM-1/NM-2 an explicit
    MPN_MISMATCH remains deterministic conflict.
  - Structured conflict taxonomy: 14-value `ConflictClass` with exact
    frozen severity sets — ALWAYS_HARD (MPN_IDENTITY, PRODUCT_FAMILY,
    GENERATION, CAPACITY, INTERFACE, FORM_FACTOR, PRODUCT_ROLE,
    ACCESSORY_RELATION, PACKAGING_QUANTITY, BUNDLE), REVIEWABLE
    (REVISION_OR_SUFFIX, BRAND, OTHER_MATERIAL_CONFLICT — BRAND is
    reviewable, NOT hard), PRICE_DIMENSION_ONLY (CONDITION — a price
    dimension, never an identity conflict); disjoint and exhaustive
    (import-self-checked). Tray-vs-retail wording alone is not hard;
    single-vs-multipack is hard (PACKAGING_QUANTITY); drive-tray accessory
    vs drive is hard (PRODUCT_ROLE / ACCESSORY_RELATION).
  - Authority tier vocabulary: MACHINE_VERIFIED, AI_ASSISTED_COMPARABLE,
    NEEDS_REVIEW, HUMAN_CONFIRMED, HUMAN_REJECTED, HARD_CONFLICT,
    EXCLUDED_LOW_CONFIDENCE, SEMANTIC_UNAVAILABLE — NOT wired into any
    runtime. The matrix is pure contract data (no nested procedural
    burying): `DETERMINISTIC_STATE_POLICIES` (VERIFIED -> MACHINE_
    VERIFIED, no AI; CONFLICT -> HARD_CONFLICT, AI not eligible, human
    cannot confirm; UNEVALUABLE -> EXCLUDED_LOW_CONFIDENCE, no AI
    authority; UNCERTAIN -> NEEDS_REVIEW, the only future semantic entry
    point) and `SEMANTIC_OUTCOME_TIER_MATRIX` with ALL 27 (decision x
    confidence x context-quality) combinations defined: MATCH+HIGH
    requires STRONG context for AI_ASSISTED_COMPARABLE; MATCH+MEDIUM,
    MATCH+HIGH+incomplete context, and MATCH+HIGH+reviewable conflict ->
    NEEDS_REVIEW; MATCH+LOW / NO_MATCH / UNCERTAIN+non-actionable /
    UNCERTAIN+LOW -> EXCLUDED_LOW_CONFIDENCE; UNCERTAIN+actionable
    context -> NEEDS_REVIEW; runtime failure -> SEMANTIC_UNAVAILABLE,
    NEVER interpreted as NO_MATCH. Ceilings restrict only (never lift).
    Precedence: HARD_CONFLICT > HUMAN_CONFIRMED > AI authority. Semantic
    or human inputs supplied for non-eligible states are ignored (fail
    closed). CORRECTED BY S2-A-FU1: the matrix is re-keyed on (decision
    x confidence x PRODUCT evidence quality) with the same tier values,
    and the STRONG row's identifier-relationship requirement is state-
    specific — U4_NO_MPN is NOT_APPLICABLE, so U4 auto-authority never
    requires MANUFACTURER_RELATION_AUTHORITY; `ContextQuality` /
    `derive_context_quality` are removed (PLAN §26.22, AD-066).
  - Future UI display vocabulary (no UI implemented): the 8 mandatory
    badge concepts; frozen attention order (NEEDS_REVIEW, AI_ASSISTED_
    COMPARABLE, HUMAN_CONFIRMED, MACHINE_VERIFIED, HUMAN_REJECTED,
    HARD_CONFLICT, EXCLUDED_LOW_CONFIDENCE, SEMANTIC_UNAVAILABLE —
    ATTENTION, not authority); summary wording contract (below).
* **Public export** — `product_intelligence/research/__init__.py` gains
  the V2 contract exports (imports + `__all__` + a phase status note);
  no other line of the package changed behavior.

The three Product-lead amendments (frozen in data + tests):

1. **NM-2 auto-authority ceiling.** NM-2 (U5_NEAR_MISS_MPN +
   NEAR_MISS_SUBSTITUTION) MAY be classified uncertain and MAY eventually
   be evaluated by semantic AI, but WITHOUT reviewed authoritative
   relationship context its maximum future AUTOMATIC tier is
   NEEDS_REVIEW — even for MATCH + HIGH. Frozen as explicit matrix data
   (`NEAR_MISS_SUBSTITUTION_WITHOUT_RELATION_AUTHORITY` + the ceiling
   rule + audit rule), not a prompt convention. Generic safety rule, not
   a manufacturer special case. AI may still return MATCH/HIGH, the
   future UI may show it prominently, and a human may confirm it later —
   it simply cannot auto-price as AI-assisted comparable.
2. **Distinct context provenance classes.** `MANUFACTURER_PRODUCT_CONTEXT`
   (reviewed manufacturer product facts — base MPN/category/family; does
   NOT establish the identifier relationship), `MANUFACTURER_RELATION_
   AUTHORITY` (reviewed manufacturer / approved authoritative source
   explicitly establishing the relevant identifier relationship; the class
   that may raise relationship authority / STRONG context quality for
   matrix purposes), and `CUSTOMER_RETRIEVAL_RELATION` (project-defined
   retrieval recall aid) are distinct bounded classes with disjoint
   capability sets. Customer retrieval MUST NEVER, by itself: establish
   identity, produce Machine Verified, raise NM-2 to automatic comparable,
   raise context to authoritative STRONG, override conflict, enter 4A, or
   be described to the model as manufacturer-established equivalence
   (all structurally proved by tests). Context quality (STRONG / LIMITED /
   WEAK) is computed only from provenance classes — never from model
   confidence or AI matched_attributes. CORRECTED BY S2-A-FU1: the single
   context-quality dimension is split into TWO orthogonal prerequisites —
   bounded product evidence quality (profile + reviewed product
   grounding) and state-specific identifier relationship authority (U4
   NOT_APPLICABLE); the provenance classes and capability sets are
   unchanged (PLAN §26.22, AD-066).
3. **Summary wording.** The misleading headline "Comparable evidence: N
   listings" is forbidden when the count contains NEEDS_REVIEW items
   (frozen `FORBIDDEN_MARKET_EVIDENCE_HEADLINE`). The future wording is
   "Market evidence found: N listings" with tier breakdown (NEEDS_REVIEW
   MAY count under market evidence) plus a separate "Pricing-eligible
   comparable listings: N" line (NEEDS_REVIEW MUST NOT count; no price
   statistic may include Needs Review before confirmation). The legacy
   machine line "N comparable NEW listings (machine-verified)" may remain.

U4 description-match (NOT re-conservatized): a public listing with no
usable manufacturer MPN evidence but usable product title evidence is
DETERMINISTIC_UNCERTAIN / U4_NO_MPN and a future semantic AI entry point
(an intentional recall feature). S2-A defines the state/policy only — no
calls are wired. The CURRENT V1 runtime gate is unchanged and does not
call the AI on U4 (proved by test). Weak/generic descriptions stay
distinguishable through the future product-evidence-quality/confidence
gates (S2-A-FU1: the "context-quality" gates were corrected to the
orthogonal product evidence bar); eligibility does not mean authority.

Test preservation: no test deleted, renamed, skipped, xfailed,
deselected, ignored, or weakened. New nodes: 117 in
`tests/research/test_semantic_authority_v2.py` (A identity mapping; B
near-miss NM-1/NM-2 + ceiling; C context provenance; D conflict
taxonomy; E matrix completeness/precedence/fail-closed; F U4 recall
invariant; G no-wiring / frozen-V1 proof) + 9 in
`tests/research/test_semantic_authority_v2_boundaries.py` (import purity,
no I/O/arithmetic, immutable contract data, export surface,
vendor/caller-token absence) + 8 auto-expanded nodes in existing
parametrized boundary scans (research-core per-file scans, domain
caller-token scan, research Decimal scan, runs boundary scan, execution
comparable-research scan) = 134. All frozen suites (2A comparator, 3C
matching, 4A aggregation, semantic runtime/boundary, execution
integration, B2/B3, replay zero-live, vendor authority, FX, Micron
alias, V1 eligibility) remain collected and green.

Validation (this session, candidate pass — final approval remains with
ChatGPT after independent GitHub review):

* Collection baseline at `1a3c4a9`: **5838**; final: **5972** (+134;
  collection did not decrease).
* Focused new S2-A: 126 passed, 0 failed.
* Focused directly-affected batch (part-number comparator, 3C matching +
  boundaries + real fixtures, human-review eligibility contract, research
  identity boundaries, `tests/semantic/`, execution semantic
  integration): 766 passed, 1 failed — the single failure is
  `tests/research/test_research_identity_boundaries.py::test_importing_
  the_research_core_pulls_in_no_third_party_dependency`, a member of the
  documented fixed eleven-node Windows/Python-3.14 subprocess-boundary
  flake allowlist (failure occurs at `subprocess.Popen ->
  _winapi.DuplicateHandle` before any project code runs); re-passed on
  isolated retry.
* Full suite: 5972 collected, 5962 passed, 39 subtests passed, 10 failed,
  0 errors, 0 skipped, 0 xfailed, 0 deselected. The 10 failures are an
  EXACT subset of the documented fixed eleven-node Windows/Python-3.14
  subprocess-boundary flake allowlist (allowlist nodes 1–8 and 10; node 9
  did not fail in this run): every one is a boundary/import guard that
  spawns a clean subprocess and failed with the recorded
  `OSError: [WinError 6] The handle is invalid` (or
  `[WinError 50]`) signature at `subprocess.Popen ->
  _winapi.DuplicateHandle`; each re-passed on isolated retry (10/10 in
  one retry batch). NO node outside the allowlist failed.
* `python manage.py check`: System check identified no issues (0
  silenced). `python manage.py makemigrations --check --dry-run`: No
  changes detected.
* `git diff --check`: clean. No deleted/renamed test files (the phase is
  additive: 3 new files + 2 modified docs + the research package
  `__init__.py`).

No deployment performed in this commit; production does not move until
independently reviewed approval, and S2-A explicitly MUST NOT deploy.

**PRODUCT-INTEL.PUBLIC-RESEARCH-RECALL-FU2 (Serper wire-contract
compatibility correction) — IMPLEMENTED / PENDING FINAL REVIEW**

Bounded production-runtime compatibility correction to the approved /
deployed FU1 (canonical spec: PLAN §26.20), on the authoritative starting
SHA `2326d1d62738801598f8b52143d59b0bcdc86819` (baseline collection
5838). Transport/retrieval compatibility only: the ONLY production change
is the Serper request wire body. Nothing changes any identity, pricing,
vendor, semantic, human-review, comparable, FX, cache, or replay
authority.

After FU1 deployment, production request `f123617a-f467-4b0c-8302-
4272a108dd9f` (MPN `MTC20F2085S1RC64BH1T`, description `Micron 32GB
DDR5-6400 ECC 2Rx8 RDIMM CL52 Tray`) FAILED at the search step
(`PROVIDER_ERROR`). Persisted execution evidence shows FU1 working as
designed up to the provider call: the exact requested MPN was a first-
class exact-phrase search query, and the Micron 7500 SSD alias policy was
NOT_APPLICABLE ("request description explicitly establishes a
memory-module product; Micron 7500 SSD catalog policy does not apply")
with zero catalog fetches — the FU1 applicability gate is production-
validated and MUST NOT be changed by this phase. Controlled production
probes of `POST https://google.serper.dev/search` on the current
production account established the root cause:

* Probe A — `{"q": "\"MTC20F2085S1RC64BH1T\"", "num": 50}` => HTTP 400
  `{"message": "Query pattern not allowed for free accounts.",
  "statusCode": 400}`.
* Probe B — `{"q": "\"MTC20F2085S1RC64BH1T\""}` (same exact quoted MPN,
  WITHOUT `num`) => HTTP 200, with exact-MPN evidence in the organic
  results (first result: CDW, snippet including `Mfg #
  MTC20F2085S1RC64BH1T`).

Root cause: the explicit `num=50` result-count parameter introduced by
FU1 is incompatible with the current production Serper account; the exact
quoted MPN query itself is supported and useful.

Delivered:

* **Wire body is query text only** — `providers/serper.py` (the ONLY
  production file changed): the ordinary Serper request body again
  contains only `{"q": query.text}`; the provider's default organic
  result count applies. `DEFAULT_ORGANIC_RESULT_COUNT` removed; no dead
  constant, no misleading documentation. NO replacement value (e.g. 10),
  NO other explicit result-count parameter, NO pagination, NO second
  Serper call, NO retry behavior, NO account-tier detection, NO catch-and-
  silent-retry of the HTTP 400.
* **FU1 retrieval behavior remains** — `build_search_query(...)` still
  produces the exact quoted requested MPN as the entire paid query for an
  MPN + description request (the description is NOT re-added); MPN-only
  and description-only forms unchanged; the 4D-D alias-expanded query
  shape unchanged; the adapter still maps EVERY returned organic item
  (response contract preserved and test-pinned).
* **Identity/alias authority remains production-validated** — the
  production MPN classifies the Micron 7500 SSD alias policy
  NOT_APPLICABLE with zero catalog fetches when the description
  establishes DDR5/RDIMM/memory-module identity; generic pages with no
  explicit requested-MPN evidence are still rejected
  (NO_EXPLICIT_MPN_EVIDENCE); explicit conflicting MPN evidence is still
  rejected (MPN_MISMATCH); a stripped-base page is not an exact
  requested-MPN match merely because the requested MPN ends in T; no
  RDIMM packaging alias policy invented, no T-suffix authority
  established.

Test preservation: no test deleted, skipped, xfailed, deselected, or
ignored; no safety/authority assertion weakened. Exactly one FU1-added
node — the wire-body `num=50` pin in
`tests/execution/test_public_research_recall.py` (`TestSerperProvider
RecallPage.test_wire_body_requests_the_documented_organic_page`) — was
replaced in place (same class, same position, still collected; the old
name encoded the invalidated contract) with
`test_wire_body_carries_only_the_query_text_without_result_count`, which
pins the complete wire payload `payload == {"q": "<exact-MPN phrase>"}`
AND the explicit absence `"num" not in payload` — the contract
correction authorized by the production provider evidence (PLAN §26.20
item 2). The credential wire-body node in
`tests/providers/test_serper_provider.py`
(`test_search_sends_the_credential_in_a_header_never_in_the_url`) was
corrected in place: FU1's `num` pin replaced by the same complete-payload
+ `"num"`-absence pins (credential contract — header, never URL, never
body — preserved; import of the removed constant dropped). The companion
50-item response-mapping node (`test_adapter_maps_every_returned_
organic_item`) is preserved UNCHANGED: it proves the response contract
(map every returned organic item), independent of the request parameter.
All other FU1 recall, alias, codec, and presentation nodes are
unchanged.

Validation (this session, candidate pass — final approval remains with
ChatGPT after independent GitHub review):

* Collection baseline at `2326d1d`: **5838**; final: **5838** (the
  FU1 wire-body node was replaced in place — no node added, removed,
  renamed to avoid collection, or deselected).
* Focused:
  `tests/providers/test_serper_provider.py` -> **36 passed, 0
  failed**; `tests/execution/test_public_research_recall.py` ->
  **13 passed, 0 failed** (combined run **49 passed**); execution/
  orchestration + 4D-D + 4C-B + Micron alias batch (`test_execution_
  orchestration.py`, `test_execution_orchestration_duplicates.py`,
  `test_4d_d_orchestration.py`, `test_4d_d_fu1_real_adapter.py`,
  `test_4c_b_corrective_pass.py`, `test_micron_alias_authority.py`,
  `tests/research/test_micron_packaging_alias.py`,
  `tests/research/test_micron_alias_codec.py`,
  `tests/web/test_micron_alias_report.py`,
  `tests/web/test_micron_alias_presentation.py`,
  `tests/runs/test_micron_alias_snapshot.py`) -> **386 passed, 0
  failed**; full `tests/providers/` directory -> **831 passed, 3
  failed** where the 3 failures are exclusively the documented
  pre-existing Windows/Python-3.14 clean-interpreter subprocess flake
  class (`subprocess.Popen -> OSError: [WinError 6] The handle is
  invalid` / `[WinError 50] The request is not supported`):
  `test_provider_boundaries.py::test_importing_the_provider_boundary_
  pulls_in_no_third_party_dependency`,
  `::test_importing_the_page_boundary_pulls_in_no_third_party_
  dependency`, `::test_http_pdf_imports_no_third_party_dependency`
  — all three reproduced identically on the pristine starting SHA in a
  throwaway worktree (not caused by FU2) and all re-passed on isolated
  retry (146/146 in the file).
* Full suite: **5838 collected, 5838 passed, 39 subtests passed, 0
  failed, 0 errors, 0 skipped, 0 xfailed, 0 deselected** (a clean
  consecutive run; the flake class did not manifest in it).
* `python manage.py check`: System check identified no issues (0
  silenced). `python manage.py makemigrations --check --dry-run`: No
  changes detected.
* No live Serper call was made by the automated suite (the wire contract
  is proven at the real adapter request-construction boundary with
  `urllib.request.urlopen` monkeypatched); no production credentials
  were used.

No deployment performed in this commit; production does not move until
independently reviewed approval.

**PRODUCT-INTEL.PUBLIC-RESEARCH-RECALL-FU1 (Production-priority
Exact-MPN Recall Defect) — IMPLEMENTED / APPROVED / DEPLOYED** (runtime
SHA `2326d1d62738801598f8b52143d59b0bcdc86819`; the Serper wire contract
it introduced — explicit `num=50` — was corrected by FU2, PLAN §26.20,
see the FU2 section above)

Bounded production-priority corrective follow-up on the approved /
frozen / deployed starting SHA `2b66ac65fbce86adcd4218dfefe1a5c7349128e4`
(baseline collection 5802). Canonical spec: PLAN §26.19.

Production request `bb280c99-7b75-445e-b476-f612cadc1b27` (MPN
`MTC20F2085S1RC64BH1T`, description `Micron 32GB DDR5-6400 ECC 2Rx8 RDIMM
CL52 Tray`) completed with 0 comparable NEW listings: the one paid search
issued the blended query `"<MPN>" <description>`, and the engine returned
broad `Micron 32GB DDR5` description matches (all correctly rejected
NO_EXPLICIT_MPN_EVIDENCE) while no exact-full-MPN page entered the
response; the Serper adapter relied on the provider's default 10-result
page (no `num` requested). The same request was also routed to, and the
report presented as evaluated against, the `micron-7500-ssd-part-catalog-
v1` policy (Result NO_AUTHORITY_MATCH) even though the product is DDR5
RDIMM memory, not a Micron 7500 SSD. Independent public-web checking found
pages exposing the full requested MPN (SHI, CDW, CoreWave Labs,
CompSource) — used only as the reproduction clue; the fix is proven by
deterministic fixtures, not by live-web behavior.

Root causes (code-evidenced):

1. **Query displacement channel.** `execution/search_query.py` blended the
   description into the paid query. A quoted phrase is a SOFT ranking
   signal, and a query can only degenerate toward terms present in the
   query: the description's high-document-frequency terms displaced the
   rare exact-MPN results. The downstream pipeline is correct — every
   returned result is fetched/extracted/gated by frozen 3C — so the defect
   was entirely at the retrieval boundary.
2. **Provider default page cap.** `providers/serper.py` sent `{"q": ...}`
   with no result-count parameter: the response was truncated at the
   provider default (10 organic results, per the recorded 2C fixture),
   which can exceed the exact-MPN phrase's traceable candidate set only in
   the truncating direction.
3. **Shape-triggered SSD catalog policy.**
   `execution/micron_alias_authority.py` acquired the 7500 SSD alias
   authority for EVERY non-empty-MPN request (trigger = final R/T suffix
   shape only, no product-class evidence); a DDR5 RDIMM request therefore
   fetched the SSD catalog and the report showed the policy/source as
   though applicable. Authority was safe (NO_AUTHORITY_MATCH established
   nothing) but the applicability was not gated and the presentation was
   misleading.

Delivered (retrieval recall and identity authority remain separate
concerns; NOTHING below changes any identity/pricing/vendor/semantic/
human-review/comparable/FX/cache/replay authority):

* **Exact-MPN first-class retrieval path** — `execution/search_query.py`:
  for an explicit-MPN request (MPN + description) the paid query is now
  the exact-MPN phrase alone (`"<MPN>"`); the description is removed from
  the PAID QUERY and remains pipeline context (frozen 3C reads the
  request's MPN; semantic/presentation/review read the request's
  description directly). MPN-only and description-only forms are
  byte-identical to before. Any page the frozen 3C gate can ACCEPT
  contains the exact MPN and is reachable by the phrase query; pages
  without the MPN can only ever be REJECTED. The frozen 4D-D
  alias-expanded query shape is unchanged. No second paid search; the
  frozen 4C one-paid-call-per-run claim contract is untouched.
* **Adapter-internal recall page — CORRECTED BY FU2** —
  `providers/serper.py`: at FU1 time, `DEFAULT_ORGANIC_RESULT_COUNT = 50`
  (value test-locked) was requested in the wire body alongside `q`. FU2
  (PLAN §26.20) removed the explicit `num` parameter after the
  production Serper account rejected it (HTTP 400, "Query pattern not
  allowed for free accounts"; the identical query without `num` returns
  HTTP 200): the wire body is again `{"q": query.text}` only, the
  provider's default organic count applies, and the adapter still maps
  every returned organic item. One request per run (unchanged); the
  frozen 4C one-paid-call-per-run claim contract is untouched.
* **NOT_APPLICABLE policy applicability gate** —
  `research/micron_packaging_alias.py` +
  `execution/micron_alias_authority.py`: a new bounded pre-fetch
  abstention `NOT_APPLICABLE` (zero fetches, no provenance, no authority)
  is returned when the request description explicitly establishes a
  memory-module product under a bounded NEGATIVE vocabulary (`DIMM`,
  `RDIMM`, `UDIMM`, `SODIMM`, `LPCAMM`, `LPCAMM2`, `DRAM`, `DDR2`–`DDR5`;
  standalone ASCII tokens, case-insensitive; vocabulary pinned by test).
  Priority: NO_REQUESTED_MPN < NOT_APPLICABLE < INVALID_LOOKUP_BASE <
  fetch. It confers no authority and never blocks a request without such
  evidence (the catalog remains the only positive authority; SSD category
  evidence still comes only from the matched row's own `is-ssd`
  attribute). The result contract re-derives the applicability evidence
  from the stored description at construction (tamper-fail-closed); the
  V1 codec round-trips the new status with no schema change. Presentation:
  the report renders the truthful applicability wording ("does not apply
  to this request … no catalog lookup was attempted") and the not-
  applicable audit carries zero fetch provenance.
* **T-strip relationship NOT established** — the apparent
  `MTC20F2085S1RC64BH1T -> MTC20F2085S1RC64BH1` packaging relationship is
  NOT made authoritative by this phase (no reviewed manufacturer-source
  authority for memory packaging exists in the architecture). A page
  publishing the stripped base form is still an explicit MPN CONFLICT
  (MPN_MISMATCH) under frozen 2A/3C (regression-proven). If an RDIMM
  alias mechanism is ever needed it requires its own reviewed authority
  policy — explicitly out of scope.

Test preservation: no test deleted, renamed, skipped, xfailed,
deselected, or ignored. Five existing nodes whose pins encoded the
displaced-query / default-page / blended-ordinary-query behavior were
corrected in place with their original contracts preserved or
strengthened (details below). One test helper gained a `description`
parameter (the auto-expanded non-established-state matrix now constructs a
mechanically re-derivable NOT_APPLICABLE instance; its contract — no
non-established state carries authority — is unchanged and extended).

New regression nodes (36): `tests/execution/test_public_research_recall.py`
(13 — production MPN fixture: exact-MPN phrase query; exact candidate
ranked last among broad candidates still ACCEPTED through the real
orchestration pipeline; 11-broad + exact-last large page survives; generic
`Micron 32GB DDR5` pages still REJECTED NO_EXPLICIT_MPN_EVIDENCE;
conflicting explicit MPNs (incl. the T-stripped base form) still REJECTED
MPN_MISMATCH; title-only pages never acquire identity; Serper wire body
query-text-only with NO explicit result-count parameter (FU1's `num=50`
wire-body pin corrected by FU2, PLAN §26.20); adapter maps a 50-item
response page in full; NOT_APPLICABLE with zero
catalog fetches; priority over INVALID_LOOKUP_BASE; legitimate 7500 SSD
ESTABLISHED behavior and non-Micron SSD NO_AUTHORITY_MATCH behavior
intact), `tests/research/test_micron_packaging_alias.py` (17 — vocabulary
pin + matching rules + NOT_APPLICABLE result contract + 1
auto-expanded state-matrix node), `tests/research/test_micron_alias_codec.py`
(5 — NOT_APPLICABLE round-trip + four tamper rejections),
`tests/web/test_micron_alias_report.py` (1 — truthful NOT_APPLICABLE
presentation). Corrected existing nodes: `test_mpn_plus_description_query`
(now: explicit-MPN request issues the exact-MPN phrase as the ENTIRE paid
query — original contract "exact MPN is the primary search term" preserved
and strengthened; description-absence asserted), the three 4D-D
`TestBoundedAuthorityFailure` ordinary-query assertions (now the exact-
MPN phrase form; the 4D-D contracts under test — ONE bounded authority
fetch, audit persisted before the search, exactly ONE search, bounded
status — unchanged), and
`test_search_sends_the_credential_in_a_header_never_in_the_url` (wire-body
assertion pinned `{"q": ..., "num": 50}` at FU1 time — credential contract
preserved and the recall page size value-locked; corrected by FU2 to the
query-text-only wire body with an explicit `"num"`-absence pin, PLAN
§26.20).

Validation (this session, candidate pass — final approval remains with
ChatGPT after independent GitHub review):

* Collection baseline at `2b66ac6`: **5802**; final: **5838** (+36 new
  nodes: 13 in `tests/execution/test_public_research_recall.py` (new
  file), 17 in `tests/research/test_micron_packaging_alias.py`
  (16 new nodes + 1 auto-expanded non-established-state matrix node),
  5 in `tests/research/test_micron_alias_codec.py`, 1 in
  `tests/web/test_micron_alias_report.py`). Collection did not decrease;
  no node removed.
* Focused (all touched subsystems + authority preservation): the
  recall/4D-D/orchestration/micron/serper/matching/boundary/web-report
  batch -> **1196 passed** (4 clean-interpreter subprocess-boundary nodes
  exhibited the documented Windows/Python-3.14 flake class and re-passed
  on isolated retry); the vendor/compact-quote/B2-B3 replay/human-review/
  semantic/comparable/FX authority batch -> **489 passed, 0 failed**.
* Full suite: **5838 collected, 5838 passed, 39 subtests passed, 0
  failed, 0 errors, 0 skipped, 0 xfailed, 0 deselected** (a consecutive
  full run). Intermittent full-run failures in this session were limited
  to the documented pre-existing Windows/Python-3.14 clean-interpreter
  subprocess flake class (`subprocess.Popen -> OSError: [WinError 6] The
  handle is invalid` in the import-boundary nodes); the exact node class
  reproduced identically on the pristine starting SHA in a throwaway
  worktree (not caused by this phase), and every failed node re-passed on
  isolated retry.
* `python manage.py check`: System check identified no issues (0
  silenced). `python manage.py makemigrations --check --dry-run`: No
  changes detected.
* Live diagnostic: not performed. The only supported local live path
  (`scripts/serper_live_smoke.py`) requires the production `SERPER_API_KEY`
  (mission: do not require production credentials) and would consume paid
  search credits (provider-cost boundary); deterministic fixtures are the
  implementation proof, per the mission.

No deployment performed in this commit; production does not move until
independently reviewed approval.

**PRODUCT-INTEL.PILOT-UX-PRICE-INTELLIGENCE-FU1 (Sub-3 Advanced-Evidence
Median Presentation Correction) — IMPLEMENTED / PENDING FINAL REVIEW**

Bounded presentation-only corrective follow-up on the approved / frozen /
deployed starting SHA `284dce1d53e8e9406c4a3e3fac7b2d284716b119`,
implementing the smallest correction identified by the approved read-only
audit PRODUCT-INTEL.8A-POST / PILOT-UX-PRICE-INTELLIGENCE-AUDIT. The frozen
4A domain contract is CORRECT and UNCHANGED: `PriceAggregateBucket.median`
is an exact descriptive sample statistic that exists for every non-empty
bucket (count 1: sole observation; count 2: exact midpoint; count >= 3:
exact sample median); `market_range_low/high` remain threshold-gated to
count >= 3. The defect corrected here is PRESENTATION ONLY.

Delivered:

* **Advanced Evidence numeric Median gated at 3 observations** — the ONLY
  production change is
  `product_intelligence/web/templates/web/research_detail.html`: in the
  Price Intelligence Advanced Evidence bucket statistics (VERIFIED and
  AMBIGUOUS branches) and the Reviewed Price Advanced Evidence bucket
  statistics, the numeric `<dt>Median</dt>` row now renders only when
  `bucket.count >= 3` (template-level count gating; no new
  domain/display fields, no `web/presentation.py` change).
* **Count 1 / count 2 (both branches):** observation count, Low, High,
  Confidence, and the truthful small-sample explanation ("Sample size is
  too small (N observation(s)) to establish an observed market range.")
  render; NO numeric Median row; NO "Sample median" relabeling — the
  sub-3 number is suppressed entirely, not renamed.
* **Count >= 3 (both branches):** current behavior preserved — Low,
  Median, High, Confidence, and the observed-market-range line.
* **Reviewed Price presentation consistency corrected** — the Reviewed
  Price Advanced Evidence branch had the same statistics contract but
  lacked the small-sample notice; it now shows the identical truthful
  notice for count < 3, matching the corresponding Price Intelligence
  presentation. Reviewed Price computation and authority are UNCHANGED.
* **4A domain median contract unchanged (re-proven):** the median is still
  calculated by the frozen aggregation arithmetic, persisted in the
  snapshot payload, round-tripped through the codec, integrity-validated
  (tamper detection), and present on the domain object and display data
  (stringified). Only its Advanced Evidence HTML presentation is gated.
* **Frozen B2/B3 Quote & Market Summary authority unchanged:** 0
  comparable NEW -> no canonical market median/range; 1-2 comparable NEW
  -> observed span, no numeric median, "Not shown — fewer than 3
  comparable NEW listings."; >= 3 -> canonical numeric median. No
  REFURBISHED / USED / DAMAGED / condition-unknown / vendor / AI-assisted
  evidence gains canonical NEW-market authority.

No model changes. No migration. No changes to `research/aggregation.py`,
`research/price_result_codec.py`, `execution/`, `providers/`, `semantic/`,
`runs/models.py`, comparable research, human-review authority, vendor
authority, or FX/cache/replay behavior.

Test preservation: no test deleted, renamed, skipped, xfailed, deselected,
or ignored. Three existing tests whose legacy wordings encoded the old
presentation were corrected with their original contracts preserved or
strengthened (section-scoped Advanced Evidence assertions; details in the
phase report): `test_verified_snapshot_shows_median` (fixture moved to a
genuine count-3 result so its "a legitimate median is rendered" contract
is proven in the Advanced Evidence region — the shared count-1 fixture was
left untouched for the other tests),
`test_authorized_malformed_supplement_unavailable_no_partial` (the bare
page-global "Median" proxy replaced by section-scoped evidence that the
detailed stored report still renders: count / Low / High / stored price /
confidence / small-sample notice / VERIFIED status), and three further
"Median" proxy assertions in `test_compact_quote_report.py` resoped to the
Advanced Evidence section (stored Low/High value) so they prove the
detailed-report contract instead of the B2/B3 note. Six new focused nodes
prove the sub-3 suppression / count-3 preservation boundary for BOTH the
Machine (Price Intelligence, VERIFIED + AMBIGUOUS) and Reviewed Price
branches, scoped to the Advanced Evidence section and distinct from the
B2/B3 Quote & Market Summary.

Validation (this session, candidate pass — final approval remains with
ChatGPT after independent GitHub review):

* Collection baseline at `284dce1`: **5796**; final: **5802** (+6 new
  nodes: 3 in `tests/web/test_price_report.py`, 3 in
  `tests/web/test_human_confirmed_compact_quote.py`). Collection did not
  decrease; no node removed.
* Focused: `tests/web/test_price_report.py` + `test_presentation.py` +
  `test_compact_quote_report.py` + `test_compact_quote_presentation.py` +
  `test_report_layout.py` + `test_human_review.py` +
  `test_human_confirmed_compact_quote.py` + the research aggregation / 4A
  contract / price-result-codec / reviewed-aggregation suites -> **348
  passed, 0 failed**, 0 errors, 0 skipped, 0 xfailed, 0 deselected.
* Full suite (5802 collected): run 1 -> **5800 passed, 2 failed**; run 2
  -> **5791 passed, 11 failed**. Every failure in both runs is the
  documented pre-existing Windows/Python 3.14 clean-interpreter
  subprocess flake class (`subprocess.Popen -> _winapi.DuplicateHandle ->
  OSError: [WinError 6] The handle is invalid`); the exact 11-node
  failing set reproduced identically on the pristine starting SHA in a
  throwaway worktree (not caused by this phase), and every failed node
  re-passed on isolated retry. 0 errors, 0 skipped, 0 xfailed, 0
  deselected in both runs.
* `python manage.py check`: System check identified no issues (0
  silenced). `python manage.py makemigrations --check --dry-run`: No
  changes detected.

No deployment performed in this commit; production does not move until
independently reviewed approval.

**PRODUCT-INTEL.8A-FX-A1 (Canonical ECB Observation Cache) — IMPLEMENTED /
PENDING FINAL REVIEW**

Bounded implementation phase on the authoritative starting SHA
`55d1879a03da3dc6163a28c9524b5ef0396b76b3`, implementing the first safe
caching slice approved by the reviewed 8A design lineage (8A-PRE audit
APPROVED / COMPLETE; 8A-FX-DESIGN; 8A-FX-DESIGN-FU1 APPROVED / FROZEN as
design). Design record: `docs/PRODUCT_INTEL_8A_PRE_CACHING_FRESHNESS_
AUDIT.md`, `docs/PRODUCT_INTEL_8A_FX_DESIGN.md`,
`docs/PRODUCT_INTEL_8A_FX_DESIGN_FU1.md` (committed with this phase as
durable architecture evidence).

Purpose: cross-run reuse of the canonical production ECB daily FX
observation set. The cache replaces ONLY external acquisition of ECB FX
evidence under the approved freshness contract. It MUST NOT (and does not)
cache or reuse: public product pages; search/Serper results; vendor
observations; semantic model responses; identity decisions; Machine Price;
Reviewed Price; human-review state; comparable research; rendered reports;
negative/failure results.

Delivered:

* **Eligibility (policy-as-code, no class inspection):** cache active ONLY
  on the canonical default path, declared at the existing canonical-default
  construction site in `execution/orchestration.py::_try_fetch_fx_rates`:
  `fx_cache_eligible = fx_provider is None` (before
  `if fx_provider is None: fx_provider = EcbFxProvider()`). ANY explicitly
  injected provider (a fake, an `EcbFxProvider` instance, a subclass, a
  wrapper, any FxProvider-compatible object) unconditionally bypasses the
  cache (zero store reads, zero store writes) and executes the existing
  live acquisition contract byte-for-byte. No `isinstance`/`issubclass`/
  provider-class-identity check exists anywhere in the cache path
  (mechanically guarded). Existing injected-provider tests remain on the
  existing live contract by construction.
* **USD-only contract preserved:** currency discovery precedes any cache
  work; USD-only runs perform zero provider calls AND zero cache/store
  lookups (guarded by armed sentinels).
* **Feed identity:** one explicit stable canonical feed identifier
  `FX_FEED_ID_ECB_DAILY = "ecb:eurofxref-daily"` in `providers/fx.py`, bound
  (mirror-locked by test) to the endpoint
  `https://www.ecb.europa.eu/stats/eurofxref/eurofxref-daily.xml` (ownership
  stays in providers/fx.py), `provider_id="ECB"`, `base_currency="EUR"`.
  Not a provider class name; not user-configurable.
* **Cross-run store (new model + one additive migration 0011):**
  `runs.FxObservationStore` — feed identity, provider_id, base_currency,
  observation_date, full rate-set payload through the reused fail-closed FX
  codec V1, original provider `retrieved_at`, deterministic content digest,
  `last_proven_at` (timezone-aware proof instant, never truncated to a
  date), `created_at`. Unique constraint
  `(feed_id, observation_date, content_sha256)`; latest-selection index;
  non-empty check constraints. NO relation to any ResearchRun (cross-run
  content, not run evidence; no cascade; a failed run publication leaves a
  successfully persisted row intact). It does not overload
  ResearchFxSnapshot, PriceIntelligenceSnapshot, ExecutionEvidenceRecord,
  ResearchSupplementSnapshot, or Django's CACHES framework.
* **Content identity (pure research contract, new
  `research/fx_cache_contract.py` — stdlib only, no Django/provider/I/O):**
  `fx_document_content_sha256` — canonical SHA-256 over a byte-stable JSON
  representation of the FULL PARSED rate observation (provider_id +
  base_currency + observation_date + rates sorted by currency code, exact
  `str(Decimal)` text; no raw XML, no dict-order dependence, no locale,
  no float). Same observation_date + changed rates (a correction) =>
  different digest => distinct row; the superseded revision remains
  VALID_HISTORICAL and is never overwritten.
  `project_required_rates` — the shared full-set -> required-currencies
  projection (document order preserved; mirrors the provider's own filter,
  mirror-locked), so LIVE and CACHE_HIT run payloads are byte-identical for
  the same document. `no_publication_possible_between(T, N, zone)` — the
  pure freshness predicate over ACTUAL aware instants (naive => TypeError,
  T > N => ValueError): reuse is possible only while every Europe/Brussels
  calendar day overlapping the CLOSED interval [T, N] is Saturday/Sunday
  (the weekend stretch [Saturday 00:00, Monday 00:00 CET/CEST)). Working
  days: NO reuse, ever (a proof on a working day never covers any N >= T).
  TARGET closing days: conservatively treated as working days (no calendar
  data; no invented holidays). DST handled by zoneinfo. The system-local
  timezone is never consulted. No numeric TTL exists. This is an explicit
  conservative A1 policy, NOT a claim that ECB is physically incapable of
  an exceptional weekend correction.
* **LIVE path (canonical, reuse not allowed):** ONE full-set ECB fetch
  (`requested_currencies=None`) -> feed-binding validation (contract defect
  propagates) -> canonical digest -> persist/reconcile the cross-run content
  entry in its OWN transaction (before the run's atomic final publication)
  -> set `last_proven_at` only for a successful live observation -> project
  required currencies -> existing per-run FX codec V1 -> run's own
  ResearchFxSnapshot with `acquisition="LIVE"`. The original provider
  `retrieved_at` is preserved (never replaced by cache insertion or
  publication time).
* **CACHE_HIT path (canonical, approved reuse):** load the latest stored
  observation -> fail-closed decode + integrity validation (digest binding,
  feed invariants, cross-field consistency, impossible stored timestamps)
  -> pure freshness predicate on the row's ACTUAL `last_proven_at` -> if
  reusable: ZERO ECB calls, original `retrieved_at` preserved, projection
  from the full cached set, the run's own ResearchFxSnapshot with
  `acquisition="CACHE_HIT"`. A cache hit never masquerades as LIVE.
* **Failure semantics (reviewer correction, binding):** a malformed or
  unsupported EXISTING cache payload is NOT a cache miss — codec/integrity
  validation failure PROPAGATES (fail closed; never caught into a silent
  live fallback; the corrupted row is never deleted). Only "no row" is an
  ordinary miss (live acquisition). Live `FxProviderError` remains
  NONFATAL (run completes, no snapshot, store untouched). Uniqueness race
  on insert: bounded reconciliation ONLY for the specifically understood
  race (competing row for the exact
  (feed_id, observation_date, content_sha256) identity, exact
  semantic/content identity validated, convergent conditional
  `last_proven_at` re-proof; otherwise fail closed). Unrelated
  IntegrityError / other storage errors propagate. A cache persistence
  failure after a successful live fetch propagates (the cache is not
  silently pretended to have succeeded). No distributed locking; no
  select_for_update.
* **Per-run provenance (additive):** `ResearchFxSnapshot.acquisition`
  CharField, choices LIVE/CACHE_HIT, default LIVE (every pre-8A row was
  acquired live; migration preserves them as LIVE). REPLAY is a read
  behavior (compact_quote_replay reads the existing run snapshot with zero
  live provider calls and zero cache acquisition) and is NOT a stored
  value; replay never mutates the persisted acquisition.
* **Presentation (smallest additive change, auditable freshness):** the
  report renders one bounded FX evidence line where this run's compact
  quote exists (both ALLOWED and DENIED replay branches): ECB reference
  date, original provider retrieval instant (UTC), and the acquisition
  label ("Retrieved live during this research run" / "Reused from the
  canonical ECB observation cache"). No internal DB IDs, raw cache keys,
  exception text, provider raw body, or implementation details are exposed
  (guarded by test). The GET path performs zero live work and never reads
  the cross-run store (armed sentinels).

Authority invariants (unchanged, re-proven): frozen 4A public market
authority (Machine Price snapshot bytes identical across LIVE / CACHE_HIT /
FX-absent); Reviewed Price; deterministic identity; semantic identity;
AI_ASSISTED_MATCH authority; vendor supplemental authority; human-confirmed
authority; HARD_CONFLICT; semantic production route (PRIMARY
amax/qwen3.8-27b, FALLBACK vllm-262k/Qwen3.6-27B-262K; Nemotron-3-Super
qualified/reference only); fallback semantics; review semantics. FX remains
DISPLAY-SUPPLEMENTAL only; the compact-quote USD equivalent is identical
LIVE vs CACHE_HIT for the same document.

Validation (this session, candidate pass — final approval remains with
ChatGPT after independent GitHub review): see the 8A-FX-A1 validation
block recorded below (collection, focused suites, full suite,
`manage.py check`, `makemigrations --check`).

No deployment performed in this commit; production does not move until
independently reviewed approval.

**PRODUCT-INTEL.SEMANTIC-QWEN38-PRODUCTION-PROMOTION-B1 (Production
PRIMARY Route Promotion — Qwen 3.8) — IMPLEMENTED / PENDING FINAL
REVIEW**

Bounded production-route phase on the reviewed/frozen A1 HEAD
`b26b50e4a5ea1ae6be7fae4e8d680a6d3a880331`. Implements the
reviewer-authorized promotion of `amax/qwen3.8-27b` to the production
semantic PRIMARY seat. It is ONLY a route-identity change: no semantic
policy, prompt, parser, eligibility, authority, aggregation, or fallback
topology change. (Canonical spec: PLAN §26.17; operator documentation:
`docs/SEMANTIC_PROMOTION_REGRESSION.md`,
`docs/SEMANTIC_BENCHMARK_RUNNER.md`.)

Promotion basis (all frozen, independently reviewed):

* Frozen 64-case FULL qualification of `amax/qwen3.8-27b`: 100% valid
  output, 96.88% decision accuracy, 100% MATCH precision, 85.71% MATCH
  recall, 0 false MATCH, safety cost 2, all hard gates PASS — exactly
  matching the historical qualified Nemotron FULL-run headline metrics
  and wrong-case IDs (SMQ-0053, SMQ-0062) under the same frozen
  corpus/prompt/settings.
* A1 production-shaped live promotion regression (22 processed cases,
  16 semantic-called cases): both `amax/nemotron-3-super` and
  `amax/qwen3.8-27b` passed ALL six objective promotion gates
  (deterministic_states_verified,
  no_semantic_override_of_deterministic_authority,
  all_semantic_calls_valid, no_unsafe_match,
  ai_assisted_authority_boundary, provenance_integrity).
* Human review of the two surfaced model disagreements: SPR-0009
  (expected UNCERTAIN; Nemotron NO_MATCH/HIGH; Qwen 3.8 UNCERTAIN/LOW —
  no authority expansion) and SPR-0020 (expected MATCH; Nemotron
  UNCERTAIN/LOW; Qwen 3.8 MATCH/MEDIUM — the candidate SKU provides the
  exact target identity and the normalized title is aligned and
  non-conflicting, so Qwen 3.8's AI_ASSISTED_MATCH authority is
  supported). Both CLOSED: no promotion blocker.

Route change (the ONLY production code change):

* `product_intelligence/semantic/runtime.py`: `PRIMARY_MODEL` moved from
  `nemotron-3-super` to `qwen3.8-27b` (plus the module docstring's
  pinned-route block). The route remains code-pinned and NOT caller
  configurable: `validate_runtime_config` and `SemanticRuntimeResult`
  self-validation reject any other model in either seat, including the
  demoted former primary.

Production route after B1:

| Role | Provider | Model |
| --- | --- | --- |
| PRIMARY | `amax` | `qwen3.8-27b` |
| FALLBACK | `vllm-262k` | `Qwen3.6-27B-262K` |

Frozen and unchanged (re-proven by the updated route-identity tests):

* FALLBACK identity and topology — byte-for-byte unchanged. Nemotron is
  NOT made the fallback: Nemotron and Qwen 3.8 share provider `amax`, so
  preserving `amax -> vllm-262k` maintains provider-level execution
  redundancy; the production fallback exists for EXECUTION FAILURE, not
  semantic disagreement.
* Fallback on execution failure only, via the existing explicit
  allowlist; a valid primary response (MATCH / NO_MATCH / UNCERTAIN) is
  FINAL; semantic disagreement never enters fallback.
* Generation contract: temperature 0.0 (exact float), max_tokens 32768,
  request-timeout behavior, prompt v1.1, parser, response schema,
  enums, validation, reason-code handling.
* Authority/execution contract: deterministic identity matching,
  semantic eligibility (`_is_semantic_eligible`,
  `_has_usable_evidence`), `_map_semantic_decision`,
  AI_ASSISTED_MATCH authority (MATCH only), HARD_CONFLICT handling,
  Working Quote policy, Reviewed Price policy, human confirmation
  semantics, public 4A aggregation (AI_ASSISTED_MATCH remains excluded),
  commercial/vendor authority, execution evidence semantics.
* Frozen A1 artifacts: qualification corpus (SHA256 re-locked),
  `evaluation/semantic_promotion_regression/cases.json`, the
  promotion-regression harness behavior and its evaluation-only
  authorized-model catalog (nemotron role `production_primary` /
  qwen3.8-27b role `challenger` — frozen A1 evidence tooling, not
  production routing); no special-casing of SPR-0009 / SPR-0020 /
  SMQ-0053 / SMQ-0062.

Model status after B1:

* `amax/qwen3.8-27b` — production PRIMARY (reviewer-promoted).
* `vllm-262k/Qwen3.6-27B-262K` — production FALLBACK (unchanged).
* `amax/nemotron-3-super` — remains a formally QUALIFIED / REFERENCE
  model (full-qualification catalog entry and promotion-regression
  baseline); it is NOT the production primary and NOT the production
  fallback.

Test updates (route-identity freeze assertions only, moved from
Nemotron to the reviewer-approved Qwen 3.8 primary):
`tests/semantic/test_runtime.py`,
`tests/execution/test_semantic_integration.py`,
`tests/execution/test_4d_a_direct_acquisition.py`,
`tests/execution/test_review_candidate_persistence.py`,
`tests/web/test_cross_layer_regression.py`,
`tests/evaluation/semantic/test_promotion_regression_authority.py`,
`tests/evaluation/semantic/test_benchmark_runner.py`. All other
safety/authority/fallback tests are unchanged in strength. Two route
pins were strengthened (additive): the demoted former primary
`nemotron-3-super` is now rejected in the PRIMARY seat by
`validate_runtime_config`, and it is ALSO rejected in the FALLBACK
seat (same provider as the primary — provider redundancy). No test
was deleted, renamed, skipped, xfail'd, deselected, ignored, or
weakened.

Validation (this session, candidate pass — final approval remains with
ChatGPT after independent review):

* Collection: **5633** (A1-FU2 baseline 5632 + 1 new parametrize node).
  Collection did not decrease.
* Focused: `tests/semantic/test_runtime.py` 212 passed;
  `tests/semantic/test_runtime_boundaries.py` 10 passed;
  `tests/execution/test_semantic_integration.py` 50 passed;
  `tests/evaluation/semantic/test_promotion_regression_authority.py`
  58 passed; `tests/evaluation/semantic/test_promotion_regression_runner.py`
  55 passed; `tests/evaluation/semantic/test_live_runner_contract.py`
  48 passed; `tests/evaluation/semantic/test_benchmark_runner.py` +
  promotion-regression corpus/comparison + `tests/semantic/test_contract_sharing.py`
  + `tests/semantic/test_transport.py` 236 passed; the remaining
  route-constructing execution/web/runs suites 216 passed. 0 errors,
  0 skipped, 0 xfailed, 0 deselected.
* Full suite: 5633 collected; **5633 passed, 0 failed, 0 errors,
  0 skipped, 0 xfailed, 0 xpassed, 0 deselected**. No
  Windows/Python-3.14 subprocess flakes were observed in this run
  (they remain a known environmental class and would be reported if
  seen).
* `python manage.py check`: System check identified no issues (0
  silenced). `python manage.py makemigrations --check --dry-run`:
  No changes detected.
* No corpus file, prompt, parser, harness file, migration, dependency,
  or UI changed; no live model calls were made in this phase; no
  deployment performed in this commit; final approval remains with
  ChatGPT after independent GitHub review.

**PRODUCT-INTEL.SEMANTIC-QWEN38-PROMOTION-REGRESSION-A1 (Semantic
PRIMARY Promotion-Regression Harness) — IMPLEMENTED / APPROVED /
FROZEN**

A1 was independently reviewed and frozen at
`b26b50e4a5ea1ae6be7fae4e8d680a6d3a880331`; its frozen evidence
(qualification, live promotion regression, human review of the two
surfaced disagreements) was the basis for the B1 production PRIMARY
promotion recorded above.

Bounded evaluation-only phase on the reviewed main HEAD
`e8f5498f1c34803b4e13c85126ec57e3a3a8ff7d`. Builds a SEPARATE
promotion-regression facility for semantic PRIMARY candidates. It is
NOT authorization to promote `amax/qwen3.8-27b`, NOT a semantic policy
change, and NOT an attempt to improve any model's qualification score.
(canonical spec: PLAN §26.16; operator documentation:
`docs/SEMANTIC_PROMOTION_REGRESSION.md`; corpus documentation:
`evaluation/semantic_promotion_regression/README.md`.)

Frozen evidence at phase start:

* Production semantic route UNCHANGED and still frozen: PRIMARY
  `amax/nemotron-3-super`, FALLBACK `vllm-262k/Qwen3.6-27B-262K`,
  temperature 0.0, max_tokens 32768; fallback on execution failure
  only, never on semantic disagreement.
* `amax/qwen3.8-27b` completed the same frozen FULL semantic
  qualification as the production primary (both: PASS gates, 100% valid,
  100% match precision, 85.7% recall, 0 false matches); both models
  make the same two known semantic errors on the frozen 64-case corpus
  (SMQ-0053 expected MATCH -> NO_MATCH; SMQ-0062 expected MATCH ->
  UNCERTAIN). Those expectations are untouched by this phase.

Delivered:

1. **Separate production-shaped corpus** —
   `evaluation/semantic_promotion_regression/cases.json` (v1, 22 cases,
   all synthetic): categories A..J covering deterministic ACCEPTED,
   explicit MPN conflict, TITLE_TEXT / SKU_FIELD / PARTIAL-MPN semantic
   eligibility, no usable evidence, accessory/compatibility traps,
   capacity/form-factor/interface conflicts, generic
   normalized-exact-identity-plus-trailing-description cases (NOT copies
   of SMQ-0053/SMQ-0062), and all three semantic decision tiers. Each
   case declares its expected deterministic state (verified against the
   REAL frozen authority chain at run time) and its expected semantic
   call (verified against the frozen FU3B eligibility states + the
   usable-evidence title gate). The frozen 64-case qualification corpus
   is byte-identical to its frozen SHA256 (re-locked by new tests).
2. **Evaluation-only harness** —
   `product_intelligence/evaluation/semantic/promotion_regression.py`:
   single-attempt PRIMARY-seat loop per eligible case (no retry, no
   fallback chain — each model is tested in the primary seat), prompt
   v1.1 via the shared contract, the frozen strict parser/validator,
   exact provider-reported model-identity proof, the frozen transport
   status mapping (reused, not forked), disposition mapping
   (MATCH -> AI_ASSISTED_MATCH only; NO_MATCH/UNCERTAIN -> no
   authority), bounded per-case records, corpus/prompt SHA256
   manifests, six objective promotion gates, two-run comparison with
   per-case rows (decisions, confidences, validity, disagreement,
   positive-authority-expansion = mandatory human review,
   conservative-challenger-regression = recall loss, unsafe/false
   MATCH, safety-sensitive disagreement) and explicit
   `no_winner_declared`. Authorized models are explicitly limited to
   `amax/nemotron-3-super` (production_primary) and `amax/qwen3.8-27b`
   (challenger); unknown models fail closed. CLI:
   `product_intelligence/evaluation/semantic/promotion_regression_cli.py`
   (`list-cases` / `run` / `compare`).
3. **Authority-invariant tests** — 186 new nodes in
   `tests/evaluation/semantic/test_promotion_regression_{corpus,runner,authority,comparison}.py`:
   zero transport calls on deterministic ACCEPTED / MPN_MISMATCH / no
   usable evidence; strict-contract enforcement (prose, fences, unknown
   keys, invalid enums, wrong item types, identity drift) with no retry;
   MATCH stays AI_ASSISTED_MATCH and is excluded by frozen 4A
   (`IDENTITY_NOT_ACCEPTED`); a real production `AiAssistedMatchResult`
   constructs from harness provenance; HARD_CONFLICT not bypassed; no
   human confirmation / Reviewed Price fabricated; production route
   constants byte-identical and the frozen runtime REJECTS the
   challenger model (no override exists); harness imports no
   execution/runs/web/providers/Django (AST + clean-module-state); no
   production module references the harness; eligibility, specs-building,
   and single-attempt interpretation mirror-locked to the frozen
   execution/runtime originals over full outcome matrices.
4. **Reviewer-authorized boundary exception (recorded conflict,
   exacted in A1-FU1, least-privilege tightened in A1-FU2)** — the
   2A-era guard
   `test_no_outer_layer_is_wired_to_the_identity_primitive_yet`
   forbade ANY evaluation file from importing
   `product_intelligence.research`. The promotion-regression harness
   MUST replay the real deterministic identity chain
   (`assess_listing_identity`) rather than duplicating it inside
   evaluation, so the original 2A evaluation->research boundary was
   deliberately narrowed by an explicitly reviewer-authorized
   exception. The original A1 implementation introduced this exception
   itself (as a recorded conflict) using a too-broad
   `promotion_regression*` prefix match; the architecture reviewer
   AUTHORIZED the exception in A1-FU1 and required it to be an EXACT
   two-file allowlist; A1-FU2 tightened it to least privilege after
   independent review established that the CLI does not require the
   dependency. The current architecture contract is EXACTLY ONE
   reviewer-authorized exception:
   `product_intelligence/evaluation/semantic/promotion_regression.py`
   (the harness), implemented as the immutable
   `PROMOTION_REGRESSION_RESEARCH_EXCEPTION` set. The CLI
   (`product_intelligence/evaluation/semantic/promotion_regression_cli.py`)
   receives NO exception because it does not directly depend on
   research — it consumes the harness module. If the CLI or any other
   evaluation module later needs a direct research dependency, that
   requires a NEW explicit architecture-review decision. The exception
   exists so the evaluation harness can exercise the real frozen
   deterministic research chain instead of duplicating it. A
   complementary exact-allowlist guard
   (`test_only_promotion_regression_may_wire_research` +
   `test_promotion_regression_exception_is_an_exact_allowlist`)
   prevents the exception from expanding to other evaluation modules:
   no prefix, glob, or regex match — any future
   `promotion_regression_*` module is NOT covered without a new
   reviewer decision. All other evaluation files remain
   research-independent under the unchanged assertion. This was a
   reviewer-authorized governance correction, NOT an implementer-
   authorized redesign, and it does not approve A1.
5. **Documentation** — qualification vs promotion regression separated
   explicitly in `docs/SEMANTIC_PROMOTION_REGRESSION.md`, the corpus
   README, STATUS (this section), PLAN §26.16, and a cross-reference in
   `docs/SEMANTIC_BENCHMARK_RUNNER.md`. No automatic winner selection;
   production remains Nemotron primary; the regression comparison is
   evidence for a later human-reviewed promotion decision.

Validation (this session, candidate pass — final approval remains with
ChatGPT after independent review):

* Pre-A1 collection at `e8f5498`: **5436** collected.
* Post-A1 collection: **5631** collected (delta +195 = 186 new harness
  test nodes + 4 auto-expanded evaluation-boundary nodes [2 scans x 2
  new files] + 1 new complementary identity-boundary node + 2
  auto-expanded provider-boundary nodes + 2 auto-expanded
  web-boundary nodes).
* Focused (pre-existing): `tests/semantic/test_runtime.py`,
  `tests/semantic/test_runtime_boundaries.py`,
  `tests/execution/test_semantic_integration.py`,
  `tests/evaluation/semantic/test_benchmark_runner.py`,
  `tests/evaluation/semantic/test_live_runner_contract.py` -> 406 passed
  (baseline, pre-change) and re-passed post-change.
* Full suite (post-A1): **5631 passed, 0 failed, 0 skipped, 0 xfailed,
  0 deselected (+ 39 subtests passed)**. One full run earlier in the
  session showed 3 subprocess-boundary nodes failing with the documented
  Windows/Python-3.14 signature (`subprocess.Popen ->
  _winapi.DuplicateHandle -> OSError: [WinError 6]`); each re-passed on
  immediate retry (known environmental flake class, not a product
  defect). No node outside that flake class fails.
* Frozen evidence re-locked mechanically: qualification corpus SHA256
  `3c21d6fcd4eefa5cc383792abfd9308bd5c03315834c8ffdffd0f6a2b3619ca1`;
  qualification FULL prompt SHA256
  `f50e5584659f953ce73a97ccc8bc1ff487fbeeb37e2e0a72e52210613aeab1ff`;
  PRIMARY `amax/nemotron-3-super`; FALLBACK `vllm-262k/Qwen3.6-27B-262K`;
  temperature 0.0 (exact float); max_tokens 32768.

Live Nemotron-vs-Qwen promotion-regression run: NOT executed in this
phase (implementation uses fake/recorded transports only). Exact
human-executed commands are in `docs/SEMANTIC_PROMOTION_REGRESSION.md`.
No deployment performed in this commit; final approval remains with
ChatGPT after independent GitHub review.

**A1-FU1 governance correction (exact evaluation exception).**
ChatGPT's independent review of the actual A1 GitHub diff found one
governance defect: the A1 implementation had narrowed the 2A
evaluation->research safety boundary with a too-broad
`promotion_regression*` prefix exception BEFORE obtaining reviewer
authorization, and the A1 documentation described the boundary without
qualifying that the pre-existing safety test was changed. The
architecture reviewer AUTHORIZED the exception itself (the harness must
exercise the real deterministic research chain, never a copy) but
tightened it to an EXACT two-file allowlist. A1-FU1 changed exactly:

* `tests/research/test_research_identity_boundaries.py` — replaced the
  prefix-based exception with the immutable
  `PROMOTION_REGRESSION_RESEARCH_EXCEPTION` exact allowlist
  (`promotion_regression.py`, `promotion_regression_cli.py`), and added
  `test_promotion_regression_exception_is_an_exact_allowlist` proving
  the exception cannot expand implicitly (arbitrary
  `promotion_regression_*` names, other directories, and unrelated
  evaluation modules are all outside it). No other test was deleted,
  renamed, skipped, xfailed, deselected, or weakened.
* Wording corrected in this section (item 4), PLAN §26.16 (item 7),
  and `docs/SEMANTIC_PROMOTION_REGRESSION.md`: the boundary was
  deliberately narrowed by an architecture-reviewer authorized
  exception (A1-FU1), not by an implementer-authorized redesign, and
  the original A1 commit did not yet have that authorization.

A1-FU1 validation: focused boundary + promotion-regression suites
re-passed; collection and full-suite counts in the commit report below.
No production file, model route, corpus, prompt, parser, expectation,
migration, or UI changed. The live Nemotron-vs-Qwen comparison was
STILL not executed in A1-FU1; A1 remains PENDING FINAL REVIEW.

**A1-FU1 validation (this commit):**

* Collection: **5632** collected (A1 reviewed baseline 5631 + 1 new
  node `test_promotion_regression_exception_is_an_exact_allowlist`).
  Collection did not decrease.
* Focused: `tests/research/test_research_identity_boundaries.py` +
  `tests/evaluation/semantic/test_promotion_regression_{authority,runner,corpus,comparison}.py`
  -> 297 passed, 1 known environmental flake (`test_importing_the_research_core_pulls_in_no_third_party_dependency`,
  Windows/Python-3.14 `OSError: [WinError 6]`, re-passed on isolated retry).
  The A1 prompt named `test_promotion_regression_cli.py`; no such file
  was created by A1 (the CLI is covered by the authority import-
  boundary + runner/comparison suites). Focused boundary + runtime/
  integration suites: `tests/semantic/test_runtime.py`,
  `tests/semantic/test_runtime_boundaries.py`,
  `tests/execution/test_semantic_integration.py`,
  `tests/evaluation/semantic/test_benchmark_runner.py`,
  `tests/evaluation/semantic/test_live_runner_contract.py` -> 406 passed.
* Full suite: 5632 collected; **5621 passed (+ 39 subtests passed)**;
  11 failures — all 11 are
  the pre-existing Windows/Python-3.14 `OSError: [WinError 6]` /
  `[WinError 50]` subprocess-import flake class (one of the 15
  clean-interpreter import-boundary nodes), reproduced identically on
  the pristine A1 HEAD in a throwaway worktree (not caused by A1-FU1),
  and each node re-passed on isolated retry. 0 errors, 0 skipped,
  0 xfailed, 0 xpassed, 0 deselected.
* No production file, model route, corpus, prompt, parser,
  expectation, migration, or UI changed. No test deleted, renamed,
  skipped, xfailed, deselected, or weakened beyond the now exactly
  bounded, reviewer-authorized exception.

**A1-FU2 governance correction (least-privilege exception).**
ChatGPT's independent review of the actual FU1 GitHub commit confirmed
that FU1 replaced the too-broad `promotion_regression*` prefix
exception with an exact-path allowlist, but established that the FU1
two-file allowlist is not least privilege: `promotion_regression.py`
imports `product_intelligence.research` (and therefore requires the
reviewer-authorized exception), while `promotion_regression_cli.py`
does NOT import research — it consumes the harness module — and the
FU1 instruction had authorized the CLI only IF it actually required
the dependency. A1-FU2 changed exactly:

* `tests/research/test_research_identity_boundaries.py` —
  `PROMOTION_REGRESSION_RESEARCH_EXCEPTION` now contains EXACTLY ONE
  path: `product_intelligence/evaluation/semantic/promotion_regression.py`.
  The CLI is NOT exempt. `test_only_promotion_regression_may_wire_research`
  now asserts the allowlist holds exactly one entry (anti-vacuity);
  `test_promotion_regression_exception_is_an_exact_allowlist` now
  proves: the harness IS authorized and DOES import research today
  (the exception is load-bearing); the CLI is NOT authorized and does
  NOT import research; if the CLI ever begins importing research the
  boundary FAILS until a new explicit reviewer decision changes the
  allowlist; arbitrary `promotion_regression_*` names (extra / hack /
  temp / database / anything / cli_extra, other directories, outside
  the repository) remain unauthorized; and every real evaluation file
  importing research belongs to the exact one-file allowlist. No test
  was deleted, renamed, skipped, xfailed, deselected, or weakened.
* Wording corrected in this section (item 4), PLAN §26.16 (item 7),
  and `docs/SEMANTIC_PROMOTION_REGRESSION.md`: the current
  evaluation->research contract has exactly ONE reviewer-authorized
  exception (the harness); the CLI receives NO exception because it
  does not directly depend on research; a future direct research
  dependency for the CLI or any other evaluation module requires a NEW
  explicit architecture-review decision. FU1 history is preserved:
  FU1 used a two-file exact allowlist; FU2 tightens it to least
  privilege.

A1-FU2 validation:

* Collection: **5632** collected — unchanged from the A1-FU1 baseline
  (FU2 corrects existing nodes in place; no new test node).
* Focused: `tests/research/test_research_identity_boundaries.py` ->
  112 passed (the clean-interpreter subprocess node intermittently
  exhibits the pre-existing Windows/Python-3.14 `OSError: [WinError 6]`
  flake class in this environment and re-passes on isolated retry);
  `tests/evaluation/semantic/test_promotion_regression_{authority,runner,corpus,comparison}.py`
  -> 186 passed; `tests/semantic/test_runtime.py`,
  `tests/semantic/test_runtime_boundaries.py`,
  `tests/execution/test_semantic_integration.py`,
  `tests/evaluation/semantic/test_benchmark_runner.py`,
  `tests/evaluation/semantic/test_live_runner_contract.py` -> 406
  passed. 0 errors, 0 skipped, 0 xfailed, 0 deselected.
* No production file, model route, corpus, prompt, parser,
  expectation, migration, or UI changed. No test deleted, renamed,
  skipped, xfailed, deselected, or weakened. The live
  Nemotron-vs-Qwen comparison was STILL not executed in A1-FU2; A1
  remains PENDING FINAL REVIEW.

**PRODUCT-INTEL.PILOT-RELEASE-2-PROD-FIX1-FU4-FU1 (Exact Observed
Vendor Entity Correction) — IMPLEMENTED / PENDING FINAL REVIEW**

Bounded append-only corrective follow-up to the FU4 commit (SHA
1c8b96934c58fc567514bdc68b87da08b2cdcbe5). FU4 was BLOCKED in
independent review for one concrete production-fidelity defect: its
implementation/tests/docs substituted the unsupported named-entity
spellings for the two EXACT production-observed hexadecimal numeric
entities inside the paragraph-envelope section values. The FU4
implementation is retained; ONLY the two wrong entity literals and the
directly necessary tests/docs were corrected. No deployment performed
in this commit; final approval remains with ChatGPT after independent
GitHub review and a later production smoke. (Canonical spec: PLAN
§26.15.)

1. **Exact paragraph entity literal correction (production
   fidelity)** — the production-safe probe observed EXACTLY: Ingram
   — `&quot;` (166 occurrences), the exact hexadecimal numeric LF
   entity formed by `"&" + "#xA;"` (ampersand, hash, lowercase x,
   uppercase A, semicolon), and the exact hexadecimal numeric CR
   entity formed by `"&" + "#xD;"` (ampersand, hash, lowercase x,
   uppercase D, semicolon); CDW — none; Synnex EU — `&quot;` (154
   occurrences). The `&nbsp;` / `&cr;` spellings implemented by FU4
   are NOT supported by production evidence and are no longer
   decoded. The only approved decode table in
   `product_intelligence/providers/internal_vendor.py`
   (`_PARAGRAPH_ENTITY_LITERALS`) is now EXACTLY: `&quot;` -> U+0022,
   the exact hex numeric LF entity -> U+000A (LF), the exact hex
   numeric CR entity -> U+000D (CR). The two hex numeric literals are
   verified character-by-character (five characters each: LF
   0x26 0x23 0x78 0x41 0x3B; CR 0x26 0x23 0x78 0x44 0x3B) by
   import-time self-assertions in the production module and by a
   dedicated test. No html.unescape, no `html` import, no HTMLParser,
   no BeautifulSoup, no arbitrary numeric-entity regex. Decoding
   remains ONLY on the FU3 exact paragraph-envelope path; the
   retained plain-text contract remains undecoded.
2. **Numeric-entity boundary correction** — the FU4 false statement
   "no numeric entity was observed" is corrected: the two exact
   hexadecimal numeric entities above WERE observed and are approved;
   no OTHER numeric entity is approved. Every other named entity
   (including `&nbsp;` / `&cr;` / `&Quot;`), every other decimal
   numeric entity, every other hexadecimal numeric entity / equivalent
   representation (e.g. `&#10;` / `&#13;` / `&#x0a;` / `&#x0d;` /
   `&#X0A;` / `&#X0D;` / `&#x000A;` / `&#x000D;`), and every
   case/format variant of the two approved hex entities (`&#xa;` /
   `&#XA;` / `&#xd;` / `&#XD;`) remains undecoded — adversarially
   tested (fail-closed outside a string; inert raw text inside a
   string).
3. **Test corrections (test preservation maintained)** — no test node
   deleted or renamed. The FU4 node
   `test_nbsp_and_cr_entities_decoded_to_lf_and_cr` is RETAINED with
   its assertion purpose corrected: it now proves `&nbsp;` and `&cr;`
   are NOT decoded (the node's name records the rejected FU4
   contract). Five NEW FU4-FU1 provider nodes: the exact hex numeric
   LF entity -> LF; the exact hex numeric CR entity -> CR; the exact
   decode-table composition with character-by-character literal
   verification; non-decoding of equivalent numeric representations;
   non-decoding of hex-entity case variants.
   `test_plain_form_section_values_are_never_decoded` is strengthened
   (all approved spellings plus the unsupported `&nbsp;` / `&cr;`
   remain raw on the plain path); `test_unapproved_named_entities_
   are_never_decoded` now covers `&nbsp;` / `&cr;` as well. The
   faithful production-shaped synthetic fixtures (provider +
   execution) use the corrected exact entity encoding (`&quot;` +
   exact hex numeric LF/CR entities) and still produce: Ingram exact
   MPN / 1515.72 USD / CUSTOMER_PRICE / OUT_OF_STOCK / quantity 0;
   CDW NOT_FOUND; Synnex EU exact MPN / deterministic synthetic EUR
   price / LIST_PRICE / OUT_OF_STOCK / quantity 0. The execution
   integration fixture uses the same corrected exact entity
   encoding.
4. **Synnex preserved (not redesigned)** — the FU4 Synnex
   implementation was independently reviewed and is acceptable:
   `_synnex_availability_total()` and its narrow nested-path behavior
   are preserved unchanged; the GLOBAL `_safe_int` remains unchanged
   and still rejects strings; the flat Synnex compatibility form
   still rejects string quantities.
5. **Documentation corrections** — every FU4 statement (PLAN §26.14
   items 1/2/4/5, the §26.13 cross-reference note, the FU4 section
   below, and this status) claiming the unsupported `&nbsp;` -> LF /
   `&cr;` -> CR mapping is corrected to the exact production evidence;
   the FU4 block is recorded. FU4's SHA 1c8b969 was blocked in
   independent review because its implementation/tests/docs
   substituted unsupported `&nbsp;` / `&cr;` for the observed exact
   hex numeric entities.

**PRODUCT-INTEL.PILOT-RELEASE-2-PROD-FIX1-FU4 (Vendor Paragraph
Entity Decoding + Synnex Availability Wire Type) — IMPLEMENTED /
BLOCKED IN INDEPENDENT REVIEW (EXACT ENTITY LITERAL DEFECT) / ENTITY
LITERAL CONTRACT CORRECTED BY FU4-FU1 / PENDING FINAL REVIEW**

Bounded append-only corrective follow-up to the FU3 commit (SHA
2f8c693bd428527d17fb7268eee1b0fba5c014e6). FU3 has been independently
source-reviewed, deployed, and production-smoked. The production smoke
run a05a0aec-6f83-43d9-a3be-f9b41797f610 (requested MPN
`MTFDKBA480TFR-1BC1ZABYYR`, Micron 7450 PRO 480GB NVMe M.2 Non-SED)
completed with `ResearchRunState.COMPLETED`, but the persisted Vendor
result was `lookup_status=PARTIAL` / `retrieved_at=2026-09-25
02:16:02+00:00` / `observations=[]` / Ingram -> MALFORMED_SECTION /
CDW -> NOT_FOUND / Synnex EU -> MALFORMED_SECTION (no ResearchFx
Snapshot, because there were no usable Vendor observations). The FU3
outer-envelope fix DID work: the scanner now recognizes exactly
`<p>Ingram Product:` / `<p>CDW Product:` / `<p>Synnex EU Product:`.
The remaining failure was INSIDE the section literal representation —
two exact production-wire differences that FU3 did not cover, corrected
here with the narrowest bounded support. The previous implementation is
retained; no FU3 redesign; no deployment performed in this commit;
final approval remains with ChatGPT after independent GitHub review and
a later production smoke. (Canonical spec: PLAN §26.14.)

1. **Observed paragraph-envelope entity encoding (production-safe
   probe; structure/vocabulary only)** — the exact entity vocabulary
   inside the section values of the observed response (HTTP 200;
   `Content-Type: text/html; charset=utf-8`; approximately 5485 bytes;
   5 lines): Ingram — `&quot;` (166 occurrences), the exact
   hexadecimal numeric LF entity formed by `"&" + "#xA;"`, and the
   exact hexadecimal numeric CR entity formed by `"&" + "#xD;"`; CDW
   — none; Synnex EU — `&quot;` (154 occurrences). No other named
   entity (`&apos;` / `&lsquo;` / `&rsquo;` / `&amp;` / `&lt;` /
   `&gt;` / `&nbsp;` / `&cr;` / ...) and no OTHER numeric entity
   (decimal, or any other hex case/format spelling) was observed.
   (FU4-FU1 correction: the FU4 text's `&nbsp;` / `&cr;` vocabulary
   and its statement "no numeric entity was observed" were wrong —
   the observed entities are the two exact hexadecimal numeric
   entities; see §26.15.) After EXACTLY `&quot;` -> `"` (U+0022),
   the exact hex numeric LF entity -> LF (U+000A), the exact hex
   numeric CR entity -> CR (U+000D) — and nothing else — no
   recognized HTML entity remained and the UNCHANGED strict bounded
   literal parser succeeded: Ingram -> mapping (27 top-level keys),
   CDW -> not_found, Synnex EU -> mapping (2 top-level keys). At probe
   time Ingram mapped to 1515.72 USD CUSTOMER_PRICE OUT_OF_STOCK
   quantity 0 and Synnex to 966.58 EUR LIST_PRICE with
   `UnitPriceAmount` observed as the numeric string "966.58" (the
   existing `_safe_decimal` already supports numeric strings — no new
   generic price behavior) and `AvailabilityTotal` observed as the
   string "0". The old 962.86 EUR observation is historical; the
   962.86 vs 966.58 difference is mutable upstream commercial data, NOT
   an implementation acceptance invariant. The production contract is:
   exact requested MPN + valid finite non-negative price + EUR currency
   + LIST_PRICE + correct availability from the documented
   AvailabilityTotal semantics.
2. **Correction A: exact paragraph entity decoding (bounded)** — on
   the FU3 exact paragraph-envelope path ONLY, the section value text
   is normalized by EXACTLY three bounded literal replacements before
   the unchanged strict parser runs (FU4-FU1: the exact literals —
   `&quot;` / the exact hex numeric LF entity (`"&" + "#xA;"`) / the
   exact hex numeric CR entity (`"&" + "#xD;"`)). This is NOT
   html.unescape, NOT a generic entity table, NOT an arbitrary entity
   regex: no other named entity (`&apos;` / `&lsquo;` / `&rsquo;` /
   `&amp;` / `&lt;` / `&gt;` / `&nbsp;` / `&cr;` / ...), no OTHER
   numeric entity (decimal, or any other hex case/format spelling),
   no case/format variant is decoded — adversarially tested. The
   retained plain-text section
   contract is unchanged: literal entity spellings in a plain section
   remain plain text and are never decoded. Unknown/unapproved entity
   forms inside an authoritative literal remain fail-closed (a bare
   entity token outside a string fails the strict grammar ->
   MALFORMED_SECTION; inside a string it is inert raw text, never
   interpreted). A trailing `</p>` after a COMPLETE parsed value
   remains non-data interstitial material exactly as FU3 defined. The
   strict bounded literal grammar, the `{Not Found}` marker, the
   three-label allowlist, duplicate-label first-wins, max body size,
   one-network-call, no-redirect / no-proxy / no-eval / no-
   literal_eval behavior are all unchanged (re-proven). The raw Vendor
   body is never logged, persisted, put into exception detail, or
   exposed to user output.
3. **Correction B: Synnex nested string availability** — the current
   real nested Synnex wire represents
   `OnlineCheck.Item.AvailabilityTotal` as a non-negative integer,
   observed as the ASCII decimal digit STRING `"0"`. A narrow
   Synnex-specific reading (`_synnex_availability_total`) applied to
   the REAL nested path only accepts the existing `_safe_int` readings
   (non-negative int / finite integral Decimal) plus exactly the
   production-observed string form: ASCII decimal digits only,
   non-negative, no sign, no decimal point, no exponent, no whitespace
   coercion, bounded digit length ("0" -> 0, "12" -> 12). The GLOBAL
   `_safe_int` contract is UNCHANGED — it still rejects strings
   everywhere else (Ingram / CDW / flat Synnex compatibility form /
   other code paths). Rejected string forms ("-1" / "+1" / "1.0" /
   "1e2" / " 0 " / "" / "abc" / bool / float / list / dict /
   over-bounded) fail to UNKNOWN with quantity None — no stock state
   is fabricated.
4. **Faithful production-shaped full-adapter test (synthetic)** — the
   new fixture mirrors the CURRENT observed representation: exact `<p>`
   wrapper, `&quot;`-encoded quoted strings, the exact hex numeric
   LF/CR entities (`"&" + "#xA;"` / `"&" + "#xD;"`) in a non-
   authoritative synthetic Ingram field, CDW `{Not Found}`, nested
   Synnex OnlineCheck with fake SessionId / BuyerAccountId / SystemId
   sentinels, numeric-string `UnitPriceAmount`, digit-string `"0"`
   `AvailabilityTotal`. Deterministic synthetic mapping: Ingram exact
   MPN / 1515.72 USD / CUSTOMER_PRICE / OUT_OF_STOCK / quantity 0;
   Synnex exact MPN / 962.86 EUR (explicitly synthetic) / LIST_PRICE /
   OUT_OF_STOCK / quantity 0; CDW NOT_FOUND; exactly one network call;
   sentinels and entity spellings absent from the normalized response.
5. **Full execution integration + authority proofs (encoded fixture)**
   — REAL `execute_research_run`: one Vendor network call; run
   COMPLETED; ResearchSupplementSnapshot PARTIAL with retrieved_at
   non-null, Ingram observation present, Synnex observation present
   (OUT_OF_STOCK / quantity 0 from the string "0"), CDW NOT_FOUND
   issue present; sensitive metadata absent from the persisted
   supplement; Machine Price immutable (deterministic zero-public-
   search fixture: zero buckets, no vendor values in the artifact);
   Vendor supplemental only (paid search not suppressed; no semantic
   input; no public-search authority; no human-confirmed authority);
   the usable Synnex EUR observation triggers the EXISTING 4D-C
   execution-time currency discovery (exactly EUR + USD requested from
   the deterministic injected FX provider; ResearchFxSnapshot persists
   EUR + USD) — no FX production code modification; Compact Quote
   historical replay (armed fail-fast zero-live Search / Page / Vendor
   / ECB constructor+fetch / semantic / urllib boundaries, exactly as
   the existing FU3 zero-live test): Ingram Vendor row present, Synnex
   Vendor row present, CDW row absent, Synnex USD Equivalent from the
   persisted ResearchFxSnapshot.

**PRODUCT-INTEL.PILOT-RELEASE-2-PROD-FIX1-FU3 (Vendor Paragraph
Envelope) — IMPLEMENTED / PENDING FINAL REVIEW**

Bounded append-only corrective follow-up to the FU2 commit (SHA
ec67f0f2f8f357fb77dd3cc1a5947e50a1b80af2) closing the exact remaining
production defect: on the approved SHA, the production Vendor response
for `MTFDKBA480TFR-1BC1ZABYYR` (run
f3a82fda-f708-4974-806e-d13a18482f96) was persisted as FAILED /
retrieved_at None / zero observations because the section scanner did
not recognize the real OUTER response envelope (defect inside Vendor
response contract recognition, before source mapping, 2A binding,
persistence, or Compact Quote projection). The previous implementation is
retained; ONLY the scanner's section-label recognition is extended with
the observed exact paragraph form, plus directly necessary tests/docs.
Not a feature phase; no 8A caching; no Vendor adapter redesign; no
deployment performed in this commit. Candidate state; final approval
remains with the project lead. (Canonical spec: PLAN §26.13.)

1. **Observed production envelope (structure-only probe, no values
   printed)** — HTTP 200; `Content-Type: text/html; charset=utf-8`;
   approximately 5485 bytes for the observed Micron lookup (5 lines);
   each known section label appears exactly once; each recognized
   section line carries an exact literal `<p>` immediately before the
   known label (the observed three-character line prefix is the HTML
   paragraph opener); the source payload remains bounded literal data.
   Structurally: `<p>Ingram Product: { ... }</p>` /
   `<p>CDW Product: {Not Found}</p>` /
   `<p>Synnex EU Product: { ... }</p>`.
2. **Exact paragraph-prefix scanner support (narrowest possible)** —
   each of the three exact known labels is recognized in exactly two
   outer forms: the existing plain line-anchored form (unchanged) and
   the observed exact paragraph-prefix form. Contract: `optional
   whitespace + optional exact "<p>" + exact bounded known label`.
   Deliberately NOT a generic HTML parser: no other tag (`<div>` /
   `<span>` / `<script>` — adversarially tested), no attributes
   (`<p class="x">`), no nesting (`<p><span>`), no case variants, no
   text before `<p>` on the line, no tag stripping, no HTML unescaping,
   no DOM text search, no BeautifulSoup/HTMLParser, no generic-HTML
   regex scraping. Unknown labels remain untrusted and ignored. The
   strict bounded literal parser remains responsible for the section
   value; malformed content INSIDE a literal still fails that source
   closed; one malformed source does not destroy valid siblings;
   duplicate-label first-wins, max body size, one-network-call,
   no-redirect, no-proxy, and no-eval/literal_eval behavior all
   preserved (re-proven). A trailing observed `</p>` after a COMPLETE
   bounded literal is the already-supported post-literal interstitial
   material (never data). The raw body is never logged or persisted.
3. **Source contracts unchanged (re-proven end-to-end)** — hybrid
   Ingram (`vendorPartNumber` + nested `pricing.customerPrice` /
   `retailPrice` / `currencyCode` + top-level boolean `availability` +
   top-level `Avl_Quantity`) maps the exact-MPN paragraph body to
   1515.72 USD CUSTOMER_PRICE / OUT_OF_STOCK / quantity 0; nested
   Synnex EU (`OnlineCheck.Header.CurrencyCode`,
   `OnlineCheck.Item.ManufacturerItemIdentifier` / `UnitPriceAmount` /
   `AvailabilityTotal`) maps to 962.86 EUR / OUT_OF_STOCK / quantity 0;
   CDW remains `{Not Found}`; SessionId / BuyerAccountId / SystemId
   (fake sentinels in tests) remain stripped by the allowlist and absent
   from the normalized response, the persisted snapshot, logs, and
   exception detail.
4. **Full execution integration (paragraph fixture)** —
   `execute_research_run` with the paragraph-wrapped real structural
   fixture: one Vendor network call; bounded PARTIAL; retrieved_at
   present; both observations persist in the
   ResearchSupplementSnapshot; Machine Price unchanged (zero buckets,
   no vendor values); Vendor supplemental only (paid search not
   suppressed; no semantic input); the usable Synnex EUR observation
   triggers the existing 4D-C execution-time currency discovery (EUR +
   USD requested from the FX provider — no FX production code altered);
   the injected deterministic provider's success persists a
   ResearchFxSnapshot and the Synnex EUR Compact Quote row receives its
   persisted USD Equivalent.
5. **Compact Quote historical replay (armed zero-live)** — Ingram
   Vendor row + Synnex EU Vendor row present, CDW row absent,
   USD Equivalent from the persisted FX snapshot, with armed fail-fast
   Search/Page/Vendor/FX/Semantic/network boundaries (zero live replay
   I/O).
6. **Preserved production evidence** — the Human Confirmed semantic
   listings → Compact Quote architecture proven by run
   f3a82fda-f708-4974-806e-d13a18482f96 remains accepted and
   unchanged. That run's absence of a ResearchFxSnapshot is explained
   by its inputs: frozen 4A had no reportable non-USD bucket; Vendor
   returned zero usable observations due to this parser failure; the
   human-confirmed EUR evidence was added only later through review.
   Historical replay must NOT perform a live ECB call merely because a
   later human confirmation introduces EUR — that zero-live historical
   contract remains frozen. A NEW run after this repair obtains FX
   during execution because the Synnex EUR observation is then a usable
   Vendor observation.

**PRODUCT-INTEL.PILOT-RELEASE-2-PROD-FIX1-FU2 (Public Replay
Persisted-Snapshot Authority) — IMPLEMENTED / PENDING FINAL REVIEW**

Bounded append-only corrective follow-up to the FU1 commit (SHA
681a4a8b67895e510eb277c850c0e83318af17b9) closing the FINAL independent
review blocker for PROD-FIX1. The previous implementation is retained;
ONLY the public replay's price-evidence authority source is corrected,
plus directly necessary tests/docs. Not a feature phase; no 8A caching
implemented; no deployment performed in this commit. Candidate state;
final approval remains with the project lead. (Canonical spec: PLAN
§26.12.)

1. **Public replay persisted-snapshot authority (FINAL BLOCKER)** —
   `replay_public_compact_quote_projection` no longer accepts a
   caller-supplied `PriceAggregationResult` (the `price_result`
   parameter is removed; the only parameter is `run`). The denied
   replay now owns its authority exactly like the authorized replay:
   it loads `PriceIntelligenceSnapshot.objects.get(run=run)`, decodes
   it through the canonical price-result codec, verifies
   `decoded.request == run.to_research_request()`, and uses THAT
   decoded persisted result for the frozen public bucket projection,
   the shared human-confirmed binding derivation, and the
   human-confirmed price/currency/condition evidence. A same-request
   cross-run result (identical source URL / product title / MPN field
   / SKU / evidence source, different persisted price — Run A 1890
   USD vs Run B 999 USD) can no longer substitute for the persisted
   snapshot: confirmation establishes identity authority only over the
   persisted evidence belonging to that same run, and historical
   reports stay immutable. Fail-closed: missing snapshot
   (DoesNotExist — the existing persisted-artifact behavior shared
   with the authorized replay), malformed payload / unsupported schema
   version (`PriceResultCodecError`), request-provenance-corrupt
   snapshot (`CompactQuoteProjectionError`). The view's DENIED branch
   call site is updated to `replay_public_compact_quote_projection(
   run=run)`; the ALLOWED branch is unchanged. Denied branch remains
   vendor-free (no `ResearchSupplementSnapshot` read, no commercial
   supplement codec import, zero live Search/Page/Vendor/ECB/Semantic/
   network work; persisted `ResearchFxSnapshot` still allowed) —
   re-proven with armed fail-fast sentinels including a real persisted
   supplement with a sentinel vendor price. Machine Price untouched
   (snapshots byte-identical before/after both replays on both runs);
   human review state semantics unchanged (UNREVIEWED / REJECTED /
   tampered / stale / cross-run / undo rules re-proven unchanged);
   authorized replay behavior unchanged; the shared binding primitive
   and the 8-step review-POST validation are unchanged in strength.

**PRODUCT-INTEL.PILOT-RELEASE-2-PROD-FIX1-FU1 (Production
Review-Blocker Closure) — IMPLEMENTED / FINAL REVIEW BLOCKER
CORRECTED BY FU2 / PENDING FINAL REVIEW**

Bounded append-only corrective follow-up to the independently reviewed
PROD-FIX1 commit (SHA 8811104e14103c41346c05471b3170c55c97386a). The
previous implementation is retained; ONLY the review blockers below are
corrected, plus directly necessary tests/docs. Not a feature phase; no 8A
caching implemented; no deployment performed in this commit. Candidate
state; final approval remains with the project lead. (Canonical spec:
PLAN §26.11.)

1. **Vendor production-wire fidelity (BLOCKER 1)** — the adapter now
   supports the ACTUAL hybrid production Ingram placement: explicit
   `vendorPartNumber`, nested `pricing` (customerPrice / retailPrice /
   currencyCode), TOP-LEVEL boolean availability signal + TOP-LEVEL
   `Avl_Quantity`. The nested-pricing branch keeps its pricing authority
   (customerPrice present => authoritative; retailPrice fallback only
   when the customerPrice key is absent), keeps the canonical nested
   availability dict, and recognizes the hybrid top-level placement
   through the SAME bounded truth table (contradiction => UNKNOWN fail
   closed; false + 0 => OUT_OF_STOCK/0; true + positive => IN_STOCK);
   unrelated fields (e.g. `vendorName`) stay ignored by the allowlist.
   The full `execute_research_run` integration test now uses the faithful
   hybrid Ingram section and the REAL nested Synnex EU section
   (`OnlineCheck.Header.CurrencyCode`,
   `OnlineCheck.Item.ManufacturerItemIdentifier/UnitPriceAmount/
   AvailabilityTotal`) with fake/redacted SessionId / BuyerAccountId /
   SystemId at their realistic structural locations (the Header block),
   stripped by the allowlist. The flat forms remain separately tested
   compatibility forms and are no longer described as the only/exact
   production wire shape. Proof: exact MPN `MTFDKBA480TFR-1BC1ZABYYR` →
   one Ingram observation (1515.72 USD customer price, OUT_OF_STOCK,
   quantity 0), one Synnex EU observation (962.86 EUR, OUT_OF_STOCK,
   quantity 0), CDW NOT_FOUND.
   Section-scanner/strict-parser consistency: only the three exact
   line-anchored labels establish sections; a COMPLETE bounded literal is
   authoritative; unknown/interstitial text after it is never parsed into
   data and cannot poison the section; malformed content INSIDE a literal
   still fails that source closed (no generic HTML scraping).
2. **Human-confirmed authority ownership (BLOCKER 2)** — the single pure
   candidate-to-assessment binding primitive
   (`research.matching.is_review_candidate_binding_valid`) is now shared
   by the web GET presentation, the 8-step review-POST validation (unchanged
   in strength), and both historical replay boundaries — the binding rule
   exists in exactly one place. Both replay entry points
   (`replay_compact_quote_projection`,
   `replay_public_compact_quote_projection`) NO LONGER accept any
   caller-supplied index parameter: the effective human-confirmed
   selection is derived from PERSISTED state by
   `execution.compact_quote_replay.derive_human_confirmed_assessment_indices`,
   which proves each row is (1) an AiAssistedReviewCandidate for THIS run,
   (2) review_state CONFIRMED, (3) mapped to an in-range assessment index,
   (4) fully bound to that assessment (shared primitive), (5) still
   human-review eligible, (6) persisted price/currency exist (enforced by
   the projection). A bare caller integer can never mint HUMAN_CONFIRMED
   authority. The lowest-level pure projection helper
   (`project_human_confirmed_rows`) is retained as an
   already-authorized-selection consumer with that contract stated
   explicitly, keeping its defense-in-depth fail-closed checks.
   Machine Price untouched; human review run-scoped; historical GET
   remains zero-live-I/O.
3. **ECB trust-chain evidence correction (BLOCKER 3)** — NO insecure TLS
   bypass exists or was added; `providers/fx.py` remains unchanged. A
   later SECURE retry from the SAME production Python runtime (without
   installing certifi, without manually installing a certificate,
   without changing fx.py, without disabling TLS verification) succeeded
   and returned official rates: observation date 2026-09-24, USD 1.1367,
   ZAR 18.6836. Confirmed truth: the SSL certificate-chain verification
   failure WAS observed earlier; it was correctly converted to
   FxNetworkError; the run correctly completed without
   ResearchFxSnapshot; a later secure retry succeeded; no application
   change was required; the exact reason for the transient failure has
   NOT been proven; there is currently NO evidence-backed requirement to
   install/update a CA trust store (no such action is recorded as
   outstanding fact). The failure-path regression tests are retained
   (not removed, not weakened).
4. **Reviewed Price wording accuracy (presentation defect)** — the
   Reviewed Price summary sentence no longer states "includes N
   human-confirmed listings" from the validated-CONFIRMED-candidate count
   when fewer are actually price-eligible (e.g. UNKNOWN condition). The
   template now derives the truthful price-contributing counts from the
   reviewed buckets themselves (per-bucket `human_confirmed_count` /
   `deterministic_count` sums) and renders conditionally truthful wording.
   Reviewed-price eligibility is NOT changed to make the count match.

**PRODUCT-INTEL.PILOT-RELEASE-2-PROD-FIX1 (Production Correction) —
IMPLEMENTED / REVIEW BLOCKERS CORRECTED BY FU1 / PENDING FINAL REVIEW**

Bounded production-correction phase fixing defects discovered during real
Product Intelligence production use on the deployed PILOT-RELEASE-2 runtime
(frozen deployed runtime SHA 065320180c17b89c7460164326a0c9f49e01fe3b). Not a
feature phase; no 8A caching implemented; no deployment performed in this
commit. Candidate state; final approval remains with the project lead.

Corrections delivered (details in PLAN §26.10; review-blocker closures in
PLAN §26.11 / FU1 above):

1. **Vendor real-response contract** — the production Vendor API answers
   HTTP 200 / `text/html` with a section-oriented body that is NOT one JSON
   document (`Ingram Product: { ... }` / `CDW Product: {Not Found}` /
   `Synnex EU Product: { ... }`). The Internal Vendor adapter supports that
   bounded contract in addition to the retained canonical JSON wrapper:
   strict recursive-descent literal parsing (no eval / literal_eval), the
   exact `{Not Found}` bounded marker, the three exact section labels only,
   production field placements (canonical nested, the FU1 hybrid
   top-level-availability form, and the flat compatibility form) mapped
   through the SAME allowlist mappers, exact Decimal monetary behavior,
   exactly-one network call, transport/failure behavior preserved, one
   malformed section does not destroy valid siblings. The real Synnex
   sensitive metadata (SessionId / BuyerAccountId / SystemId) is stripped
   by the allowlist and never enters candidates, snapshots, logs, or error
   detail; the raw body is never persisted. Integration proof: exact MPN
   `MTFDKBA480TFR-1BC1ZABYYR` with the faithful hybrid production shape
   yields one Ingram observation (1515.72 USD, customer price,
   OUT_OF_STOCK, quantity 0), one Synnex EU observation (962.86 EUR,
   OUT_OF_STOCK, quantity 0), and a CDW NOT_FOUND issue.
2. **Currency formatting** — the Compact Quote price formatter no longer
   uses the currency code as a fallback prefix and appends it again.
   Known-symbol currencies keep `$1,515.72 USD` / `€962.86 EUR`; no-symbol
   currencies render once (`ZAR 30,999.0`, never `ZAR30,999.0 ZAR`). Decimal
   values and FX math untouched.
3. **AI-assisted semantic matches placement** — presentation-only reorder of
   `research_detail.html`: the section now renders immediately after
   "Compact quote summary" and before the detailed lower-level
   audit/research sections. Semantic eligibility and model behavior
   unchanged.
4. **Confirm Match -> Compact Quote** — a valid run-scoped, human-CONFIRMED
   semantic candidate now contributes a Compact Quote row for that SAME
   ResearchRun (projection-layer extension; frozen 4A artifacts never
   mutated). Identity authority only: price/currency from the persisted
   PriceIntelligenceSnapshot assessment, condition EXACTLY the persisted
   normalized condition (UNKNOWN stays "Unknown"; never upgraded), explicit
   "Human Confirmed" provenance note, persisted FX evidence only. UNREVIEWED
   / REJECTED / invalid-binding / cross-run candidates never enter; Undo
   removes the row on the next GET; historical GET remains zero live I/O.
   Machine Price and the frozen Reviewed Price behavior are unchanged.
5. **Research submit duplicate-click guard** — front-end-only inline JS on
   the new-research form: on valid submit the button is immediately
   disabled and relabeled `Researching…`. UX protection only — NOT a
   backend dedupe guarantee; no run sharing, MPN locking, caching, or
   lifecycle change. Invalid client-side validation leaves the button
   enabled.
6. **ECB / USD Equivalent TLS issue** — investigated, NOT bypassed. The
   production `ssl.SSLCertVerificationError` (unable to get local issuer
   certificate) is the secure verification working as designed; the
   provider classifies it as bounded `FxNetworkError` and orchestration
   keeps FX failure nonfatal (no ResearchFxSnapshot, original non-USD price
   survives, USD Equivalent unavailable) — locked in by regression tests,
   including mechanical no-insecure-bypass guards, all RETAINED by FU1.
   FU1 evidence correction: a later SECURE retry from the same production
   Python runtime (no certifi install, no manual certificate, no fx.py
   change, no disabled TLS verification) succeeded (observation date
   2026-09-24; USD 1.1367; ZAR 18.6836). The exact reason for the
   transient trust-chain failure has NOT been proven; there is currently NO
   evidence-backed requirement to install/update a CA trust store, and no
   such action is recorded as outstanding fact. No code change was
   required; if a future phase wants an explicitly configured trusted CA
   bundle, that is a new configuration contract to be designed and approved
   separately (none exists in the repository today).

**PILOT-RELEASE-1 DEPLOYED / ACCEPTED**

Internal pilot deployment is deployed and accepted on the internal Windows pilot server.

Verified live:
- pilot_check PASS
- Waitress service
- remote browser access
- real Serper execution
- AMAX / nemotron-3-super primary semantic execution
- human review
- comparable research
- persistent SQLite
- Windows service

**PRODUCT-INTEL.PILOT-UX — Semantic qualification APPROVED/FROZEN;
FU3A Production Semantic Runtime Contract APPROVED/FROZEN;
FU3B Semantic Execution Integration APPROVED/FROZEN;
HUMAN-REVIEW Human Review for AI-Assisted Matches APPROVED/FROZEN;
6B Enterprise SSD Category Schema APPROVED / RE-FROZEN;
6C Specification Evidence Extraction & Resolution IMPLEMENTED/APPROVED/FROZEN;
7A Comparable-Product Candidate Discovery IMPLEMENTED / APPROVED / FROZEN;
7B Enterprise SSD Similarity Scoring IMPLEMENTED / APPROVED / FROZEN.**
6D Authoritative Datasheet Specification Enrichment IMPLEMENTED / APPROVED / FROZEN

**PRODUCT-INTEL.4D — Customer Quote Research Expansion:
IMPLEMENTED / APPROVED / FROZEN / COMPLETE**

The complete customer-requirement expansion is closed: every 4D component
is approved and frozen. 4D-D (including correction pass 4D-D-FU1) was
IMPLEMENTED / PENDING FINAL REVIEW as the original candidate, was corrected
by FU1, was independently reviewed afterward, and is now APPROVED / FROZEN
(the candidate narrative below is preserved as history).

4D freeze record (4D-D, the last component frozen):
Frozen SHA: 065320180c17b89c7460164326a0c9f49e01fe3b
Frozen collection baseline: 5097 collected
Final acceptance execution: 5097 passed, 0 failed, 0 skipped,
0 xfailed, 0 deselected (+ 39 subtests passed)

**PILOT-RELEASE-2 (4D Customer Requirement Deployment & UAT) —
DEPLOYED / ACCEPTED**

Deployment/UAT phase, now closed: the already-frozen 4D customer
requirements are deployed to the internal production/pilot Windows
server. The recorded representative 4D production smoke validation
covered: a normal customer quote flow exercising current Price
Intelligence / Compact Quote behavior; Micron 7500 R/T packaging-alias
behavior.
The previously planned broader UAT matrix (direct-source acquisition
using a viable preferred-source case; normal Serper fallback; real
Vendor API commercial evidence; compact quote rendering; non-USD vendor
evidence + persisted ECB USD equivalent; Micron 7500 packaging-alias
BASE/R/T behavior; a non-eligible MPN proving alias abstention; Visual
FoxPro launcher -> browser prefill against the deployed server;
historical report reload causing zero new Search/Vendor/ECB/Micron/
Semantic live work; vendor-price access behavior under the existing
frozen network gate (4D-C-SEC REMOTE_ADDR / PI_VENDOR_PRICE_ALLOWED_
CIDRS, unchanged)) remains a validation reference; the production
records do not claim that every matrix case was separately executed
and evidenced during the 2026-09-23 cutover.

Deployment record:
- Deployed runtime SHA: 065320180c17b89c7460164326a0c9f49e01fe3b — the
  independently reviewed and frozen PRODUCT-INTEL.4D-D-FU1 runtime SHA.
  Deployment is Git-managed and exact-approved-SHA based (local
  `production` branch pinned to independently approved SHAs).
- Production smoke test passed: 2026-09-23.
- 4D is deployed; migrations through
  0010_research_micron_alias_snapshot are deployed (4D migrations
  0008 / 0009 / 0010).
- Production environment details (application path, persistent SQLite,
  service ID / WinSW wrapper, Waitress, port, health endpoint, 4D
  preferred-source configuration with `directmacro.com` enabled,
  Vendor API configuration) are recorded in the operational Confluence
  references and are not duplicated in this repository.
- The deployment relies on the internal server/network perimeter as the
  pilot authorization boundary; no application login/session/OAuth/
  per-user authorization is introduced.

Current pilot authentication decision (unchanged): the pilot server
itself has restricted access; people who can reach this internal server
are currently considered authorized for this pilot. Full application
authentication, login/session identity, OAuth, and per-user
authorization are NOT part of PILOT-RELEASE-2; they remain deferred
future production-hardening concerns (8C). Report UUID is not access
control. No session-based authorization is introduced. The frozen
4D-C-SEC vendor-price network gate is unchanged.

Runtime-vs-docs distinction (binding):
- Runtime freeze / deployed SHA = 065320180c17b89c7460164326a0c9f49e01fe3b.
- The later commits c6ad6ae (PRODUCT-INTEL.4D-CLOSE) and 7ff0ab7
  (PRODUCT-INTEL.4D-CLOSE-FU1) are docs-only project-state closures;
  production does not need to move merely to obtain those
  documentation edits.
- 7ff0ab7 is NOT the production runtime SHA; the deployed production
  runtime at 0653201 is intentional and correct.

**PRODUCT-INTEL.8A (Caching & Freshness) — IN PROGRESS**

State as of this record: 8A-PRE (Caching & Freshness Architecture
Audit) is **APPROVED / COMPLETE** — the audit was delivered as scoped
(read-only / design-first; record: `docs/PRODUCT_INTEL_8A_PRE_
CACHING_FRESHNESS_AUDIT.md`, committed with 8A-FX-A1). The 8A-FX design
lineage followed: 8A-FX-DESIGN (APPROVED / COMPLETE) and
8A-FX-DESIGN-FU1 (APPROVED / FROZEN as design). The first bounded
caching slice, **8A-FX-A1 (Canonical ECB Observation Cache), is
IMPLEMENTED / PENDING FINAL REVIEW** — see the Current state section at
the top of this document. No numeric TTL was introduced by any of
these phases; the approved freshness policy is the proof-instant +
Europe/Brussels weekend-closure contract.

The production-correction phase PRODUCT-INTEL.PILOT-RELEASE-2-PROD-FIX1
(above) and its bounded review-blocker closures PRODUCT-INTEL.PILOT-
RELEASE-2-PROD-FIX1-FU1 and PRODUCT-INTEL.PILOT-RELEASE-2-PROD-FIX1-FU2
(and the FU3 paragraph-envelope closure, the FU4 vendor paragraph
entity decoding + Synnex availability wire-type closure, and the
FU4-FU1 exact observed vendor entity correction) are PENDING
FINAL REVIEW and do NOT change the next-architecture-delivery selection
below. 8A caching is NOT implemented in PROD-FIX1, FU1, FU2, FU3,
FU4, or FU4-FU1.

The previous "post-UAT next is undecided" gate is closed: the
production deployment/smoke evidence now exists and the project lead
has selected the next architecture investigation.

8A-PRE was a READ-ONLY / DESIGN-FIRST phase: it investigated and
recorded a caching and freshness architecture before any caching
implementation. It was NOT authorization to implement caching, and no
actual TTL values were approved in that closure. Implementation was
authorized only by the separately reviewed 8A-FX design lineage and
the bounded 8A-FX-A1 phase instruction that followed.

Reason for choosing 8A-PRE: Product Intelligence is now in production,
and evidence classes have materially different freshness requirements.
The design must prevent stale evidence from being presented as current
while also avoiding unnecessary paid/live calls.

The future 8A design must distinguish at minimum:
- market/public prices — short freshness
- Vendor commercial observations — short freshness
- ECB FX rates — tied to persisted official observation date
- product specifications — longer freshness
- comparable research — medium freshness
- deterministic identity/authority evidence — not automatically
  equivalent to market-price freshness
- user/operator forced refresh
- historical reports — immutable replay, NEVER refreshed merely by GET

Later planned (directional; not an approved implementation order):
5A (Structured external API — PLANNED / NON-BLOCKING), 8B (Research
history — PLANNED), 8C (Production hardening — PLANNED). None of them
is NEXT. Authentication/session remains outside the current priority.

```
4D-PRE  Preferred Source Feasibility Audit  (evidence only) — APPROVED / FROZEN
4D-A    Source Acquisition Optimization — APPROVED / FROZEN
4D-B    Internal Vendor Commercial Evidence  — APPROVED / FROZEN
4D-C-A  ECB FX + Compact Quote Projection Foundation — APPROVED / FROZEN
4D-C-SEC Vendor Commercial Price Access Gate — APPROVED / FROZEN
4D-C    Compact Quote Summary (browser rendering) — APPROVED / FROZEN
4D-D-PRE1 Early 4D-D authority feasibility review — APPROVED / FROZEN
4D-D-PRE2 Micron official authority evidence capture — APPROVED / FROZEN
4D-D    Micron Packaging Alias Retrieval — APPROVED / FROZEN
4D-D-FU1 Runtime reachability + query-semantics closure — APPROVED / FROZEN
```

**PRODUCT-INTEL.4D-B — APPROVED / FROZEN**

Frozen SHA: c74c90b0590d1c393419d94a1c107bfe93f7143c
Frozen test baseline: 4299 collected

Internal Vendor API integrated as supplemental commercial evidence.
Key facts:
- Provider-neutral commercial boundary: `providers/commercial.py`
- Concrete adapter: `providers/internal_vendor.py`
- Supplemental persistence: `runs.ResearchSupplementSnapshot` (migration 0008)
- Versioned codec: `research/commercial_supplement_codec.py` (V1)
- At most ONE Vendor API call per ResearchRun
- Frozen 2A identity binding required for each commercial observation
- Brand new by VENDOR_API_POLICY (not source-published condition)
- **NO web exposure** — 4D-B does NOT render vendor commercial prices
- **NO authority expansion** — vendor evidence does NOT enter Machine Price,
  Reviewed Price, semantic authority, or comparable scoring
- Sensitive metadata (SessionId, BuyerAccountId, SystemId) stripped by allowlist
- 4D-C security gate resolved by frozen 4D-C-SEC REMOTE_ADDR-only access policy;
  4D-C browser rendering implemented (PRODUCT-INTEL.4D-C, approved / frozen)

**PRODUCT-INTEL.4D-C-A — APPROVED / FROZEN**

Frozen SHA: 059ade96ff2141684b973e576adcc91a10094707
Frozen test baseline: 4582 collected

ECB FX evidence persistence + Decimal-only USD-equivalent calculation +
deterministic compact quote-summary projection + historical-report replay.
Key facts:
- ECB FX provider: `providers/fx.py` (provider-neutral boundary + ECB adapter)
- FX persistence: `runs.ResearchFxSnapshot` (migration 0009)
- FX codec: `research/fx_codec.py` (V1)
- FX mathematics: `research/fx_math.py` (pure Decimal-only, ECB formula)
- Compact quote projection: `research/compact_quote.py` (data contract + tests)
- **NO browser HTML exposure** — 4D-C-A does NOT render vendor commercial prices
- ECB formula: USD Equivalent = amount_C / rate_C * rate_USD
- Semantic qualification APPROVED AND FROZEN (prompt v1.1, corpus, thresholds)
- Primary route: amax/nemotron-3-super; Fallback route: vllm-262k/Qwen3.6-27B-262K

**PRODUCT-INTEL.4D-C-SEC — APPROVED / FROZEN**

Frozen SHA: 75bfbe3d1b4a8abc12d655cc903298f08e06a8f0
Frozen test baseline: 4693 collected

4D-C-SEC establishes the server-side network access gate. Key facts:
- Configuration: `PI_VENDOR_PRICE_ALLOWED_CIDRS` (environment variable)
  - Comma-separated CIDR notation (IPv4/IPv6)
  - Absent or blank -> DENY (fail-closed default)
  - Example deployment value (never hardcoded): `10.0.0.0/8,192.168.50.0/24,172.16.8.0/21`
- Client address authority: `request.META["REMOTE_ADDR"]` ONLY
  - X-Forwarded-For, X-Real-IP, Forwarded header never trusted
  - Query parameters, cookies, Host header never trusted
  - Report UUID never access control
  - Proxy-aware client IP requires a separately reviewed trusted-proxy contract
- Module: `product_intelligence/web/commercial_access.py`
- Pure parsing function `_parse_allowed_cidrs` separately testable
- `CommercialPriceAccessConfigurationError` for malformed CIDR config
- Malformed CIDR -> entire config fails closed (deny all)
- IPv4 and IPv6 both supported
- Django setting read with lazy import pattern
- No auth, sessions, user models, OAuth, login pages, API tokens
- No changes to research/, providers/, or domain/ layers
- Views integration: `research_detail()` passes `vendor_commercial_access_allowed`
  boolean to template context — NO raw payload, NO vendor rows, NO sensitive metadata
- 4D-C browser rendering implemented (PRODUCT-INTEL.4D-C), approved / frozen;
  the server-side security branch selects authorized full replay vs denied
  public-only replay before any vendor supplemental artifact access
- Full application authentication deferred to 8C
- **NO authority expansion** — FX and projection do NOT enter Machine Price,
  Reviewed Price, semantic authority, or comparable scoring
- Historical replay: zero live FX calls, zero live Vendor API calls
- USD Equivalent is DISPLAY-SUPPLEMENTAL only
- ECB formula: USD Equivalent = amount_C / rate_C * rate_USD

**PRODUCT-INTEL.4D-C — APPROVED / FROZEN**

Frozen SHA: 4592b8966b703dfd6a72c3067d7b191314ff2968
Frozen test baseline: 4766 collected

Compact Quote Browser Rendering. Frozen prerequisites: 4D-C-A (SHA
059ade96ff2141684b973e576adcc91a10094707, 4582 collected) and 4D-C-SEC
(SHA 75bfbe3d1b4a8abc12d655cc903298f08e06a8f0, 4693 collected). Key facts:
- Server-side security branch in `research_detail()` occurs BEFORE any
  Vendor supplemental artifact is read, decoded, or projected
- ALLOWED: frozen 4D-C-A `replay_compact_quote_projection(str(run.id))`
  (complete projection; may read PriceIntelligenceSnapshot,
  ResearchFxSnapshot, ResearchSupplementSnapshot; zero live provider /
  network / semantic work; fail-closed behavior unchanged)
- DENIED: new public-only bounded read-side service
  `execution/compact_quote_public_replay.py` —
  `replay_public_compact_quote_projection`: PUBLIC_LISTING rows only via
  frozen `project_public_rows` + persisted FX evidence; NEVER reads
  ResearchSupplementSnapshot and never imports/calls vendor API,
  search, page, semantic, or ECB live provider paths
- Compact summary is built only when the existing
  PriceIntelligenceSnapshot decoded AND passed the existing request
  provenance check (`decoded.request == run.to_research_request()`);
  otherwise existing report error behavior is preserved
- New display-only web module `web/compact_quote_presentation.py`:
  vendor source labels `Ingram (Vendor API)` / `CDW (Vendor API)` /
  `Synnex EU (Vendor API)` (suffix appended once, never duplicated);
  public sources display hostname with leading `www.` stripped and the
  full SAFE source URL (from the paired frozen 4A bucket-member
  assessment, deterministic iteration order) as the link target via the
  reused `presentation._is_safe_href_url` helper; vendor rows never
  receive a URL; mapping mismatch fails closed (no guessed links)
- Template context never contains Vendor rows on the denied path — the
  `vendor_commercial_access_allowed` boolean is used only for the
  neutral notice, never as the row-hiding mechanism
- "Compact quote summary" table (Source / Price / USD Equivalent /
  Inventory / Brand New / Note) rendered near the top of the report,
  before the detailed Price Intelligence audit/evidence sections;
  existing sections untouched (additive only)
- No-data states: "No compact quote evidence is available." (zero rows)
  and "Compact quote summary unavailable." (expected persisted-artifact
  / projection failure only; programming errors propagate)
- REMOTE_ADDR-only authorization preserved (4D-C-SEC frozen policy);
  no forwarded-header logic added
- NO authority expansion: Vendor rows remain SUPPLEMENTAL DISPLAY ONLY
  (not Machine Price, Reviewed Price, deterministic/semantic identity,
  or comparable scoring); public compact rows derive only from frozen
  4A bucket membership; excluded listings never enter compact rows
- Web execution allowlist extended ONLY with
  `replay_compact_quote_projection` and
  `replay_public_compact_quote_projection` (public package API);
  web research allowlist extended ONLY with
  `compact_quote.{CompactQuoteProjection, CompactQuoteRow,
  CompactQuoteProjectionError}`, `fx_codec.FxCodecError`,
  `commercial_supplement_codec.SupplementCodecError`
- Frozen 4D-C-A `replay_compact_quote_projection()` behavior unchanged;
  the new service is additive

**PRODUCT-INTEL.4D-D-PRE1 — APPROVED / FROZEN**

Early 4D-D authority feasibility review. Binding conclusion at the time:
`NO CURRENT 4D-D ELIGIBILITY AUTHORITY EXISTS` (no reviewed manufacturer
authority chain available for packaging-alias retrieval; the requirement
remained customer-ruled and retrieval-only).

**PRODUCT-INTEL.4D-D-PRE2 — APPROVED / FROZEN**

Evidence SHA: 1cb65a3d6002006af9e1c77906a6de6b5a3fd42c

Micron official authority evidence capture (evidence only; no production
code). Recorded 12 sanitized anonymous-GET fixtures under
`tests/fixtures/pages/` plus `docs/MICRON_ALIAS_AUTHORITY_EVIDENCE.md`.
Recommendation: `AUTHORITY_EVIDENCE_SUFFICIENT_FOR_4D_D_SSD_V1`, scoped:
SSD only; the structured BASE catalog record owns the exact-MPN proof and
the `is-ssd` category proof; R/T per-part endpoints return
`Invalid Partnumber` and R/T page metadata is template echo — neither is
authority; no official R/T packaging-semantic statement exists.

**PRODUCT-INTEL.4D-D — APPROVED / FROZEN** (including correction pass
4D-D-FU1; the original candidate state — IMPLEMENTED / PENDING FINAL
REVIEW until corrected — is historical; see the FU1 approval record below)

Frozen SHA: 065320180c17b89c7460164326a0c9f49e01fe3b
Frozen collection baseline: 5097 collected
Final acceptance execution: 5097 passed, 0 failed, 0 skipped, 0 xfailed,
0 deselected (+ 39 subtests passed)

Micron Packaging Alias Retrieval, v1 scope: **Micron 7500 SSD ONLY** (not
generic Micron memory, not DRAM, not any other family; extending requires
additional reviewed authority policies and recorded manufacturer evidence).

Authority split (binding):

```
Micron catalog (reviewed 4D-D-PRE2 family-catalog endpoint):
    manufacturer / category / source-published BASE authority

Customer rule (final uppercase R/T strip, base must re-derive):
    R/T retrieval relation only (MICRON_PACKAGING_ALIAS)
    — never identity, never pricing authority
```

Key implementation facts:

- Pure research contracts: `research/micron_packaging_alias.py` — reviewed v1
  policy constants (policy id `micron-7500-ssd-part-catalog-v1`,
  manufacturer `Micron`, category `SSD`, exact reviewed catalog URL,
  approved origin `https://www.micron.com`), deterministic fail-closed
catalog-record extraction over the recorded fixture shape, `is-ssd == True`
(category evidence from the matched row's own structured attribute — never
inferred from description/URL/prefix/model knowledge), customer-rule
lookup-base derivation (final uppercase R/T only; lowercase and degenerate
inputs abstain), self-validating `MicronPackagingAliasRelation` and
`MicronAliasEligibilityResult` (every authority-bearing binding re-derived
at construction; frozen 2A `compare_part_numbers` used only for catalog-row
matching and reference labeling — frozen 2A/3C semantics unchanged, family
forms are NEVER established under 2A), `find_alias_reference` (read-side
reference labeling against alias identifiers only).
- Execution authority acquisition: `execution/micron_alias_authority.py` —
module-private reviewed v1 policy (no environment/DB/caller injection);
ONE reviewed family-catalog fetch per direct-insufficient non-empty-MPN
run through the existing PageFetcher protocol; bounded status vocabulary
(ESTABLISHED / NO_REQUESTED_MPN / INVALID_LOOKUP_BASE / NO_AUTHORITY_MATCH /
AMBIGUOUS_AUTHORITY_MATCH / CATEGORY_NOT_SSD / FETCH_FAILED / SOURCE_REFUSED /
HOST_ESCAPED / PARSE_FAILED); origin boundary (scheme downgrade, host
escape, port change, unparseable all fail closed); only the expected
provider classes are downgraded (`PageFetchError` -> FETCH_FAILED,
`UnsafeFetchTargetError` -> SOURCE_REFUSED) — no broad `Exception` catch
exists (FU1): a bare `Exception` or `RuntimeError` propagates to the
catastrophic boundary, and dependency-contract defects (fetcher without a
callable `fetch`; `fetch` returning a non-`FetchedPage` / contract-invalid
object) propagate `TypeError` rather than receiving a bounded status;
R/T detail endpoints are never fetched (not authority).
- Orchestration wiring (`execution/orchestration.py`, additive): the alias
  step runs only when fallback search is required AND the request MPN is
  non-empty; the bounded audit is persisted (its own pre-search durability
  step) BEFORE the ONE paid search; only an ESTABLISHED result changes the
  query (to `build_alias_expanded_search_query` — frozen OR shape: one
  parenthesized OR group `("REQUESTED" OR "ALIAS1" OR "ALIAS2")`, requested
  MPN first, established aliases in deterministic relation order, plus the
  ordinary description; the group alone when there is no description — an
  AND grouping would require every identifier simultaneously and defeat the
  recall purpose); every other result keeps the ordinary frozen query;
  `build_search_query` is unchanged; direct-sufficient runs perform zero
  Micron authority fetch and zero paid search; default runtime wiring (FU1):
  with no explicitly injected page fetcher the ordinary candidate fetcher
  is the frozen HTML-only default `HttpPageFetcher` and the ONE Micron
  authority fetch uses a lazily created JSON-configured `HttpPageFetcher`
  (explicit additive `accepted_media_types`/`accept_header` constructor
  capability; default configuration byte-equivalent to frozen 3A behavior,
  default `application/json` refusal unchanged) — the reviewed catalog
  endpoint publishes `application/json;charset=utf-8` (PRE2), so the HTML
  only default could never reach ESTABLISHED in the real runtime; an
  explicitly injected fetcher governs the authority fetch as well
  (deterministic fake-provider tests); semantic
  firewall: with an ESTABLISHED alias-expanded search, non-ACCEPTED
  assessments from that search batch are excluded from
  `evaluate_semantic_matches` (no AI_ASSISTED_MATCH / review candidates /
  Reviewed Price path membership) while remaining in frozen 4A input and
  exclusions; direct and ordinary non-alias assessments retain frozen
  semantic behavior; deterministic exact requested-MPN listings keep normal
  frozen 4A behavior.
- Persistence: `runs.ResearchMicronAliasSnapshot` (migration 0010) —
OneToOne per run (absent when acquisition was not performed),
`schema_version` 1, opaque codec-owned JSON payload, body SHA-256 (never
the catalog body), cascade with the run.
- Codec: `research/micron_alias_codec.py` (V1) — strict key sets, rejects
extra/missing keys and unknown versions, deterministic UTC second
precision, decode reconstructs the self-validating result so a tampered
payload cannot re-label a foreign manufacturer/category/URL/origin as v1
authority (fail closed).
- Web: `web/micron_alias_presentation.py` (display-only; consumes the
decoded persisted audit structurally per the frozen web-aggregation import
boundary) + a separate, clearly labeled "Micron packaging alias evidence"
section in `web/research_detail.html` rendered ONLY from the persisted
snapshot on historical GET (zero live Micron / search / vendor / FX /
semantic / network work, armed-fail-fast proven by
`tests/web/test_micron_alias_report.py`); alias reference rows are
persisted EXCLUDED assessments only — separate section, never Compact /
Machine / Reviewed / Comparable authority; fail-closed on codec error or
request-provenance mismatch (no partial alias data, main report unaffected).
- Boundary allowlists extended exactly: web research allowlist gains
`micron_alias_codec.{MicronAliasCodecError, decode_micron_alias_snapshot}`
and `micron_packaging_alias.{MicronAliasEligibilityStatus,
MicronAliasEligibilityResult, find_alias_reference}`; web runs-model import
guard gains `ResearchMicronAliasSnapshot`; model inventories in
`test_provider_boundaries.py`, `test_research_identity_boundaries.py`,
`test_web_boundaries.py`, `test_research_run_boundaries.py`, and
`test_comparable_research_execution.py` updated to the exact supersets.
- Final-acceptance hardening (this session, disclosed):
  `providers/http_page.py` — secure-transport setup failure
  (`ssl.SSLError` at TLS-context creation, an environmental
  Windows/Python-3.14 flake) is now classified as the adapter's bounded
  `PageFetchError` like every other transport failure (previously it
  escaped the classification); fetch semantics unchanged. Kept in FU1 as a
  separately tested transport-classification fix (regression: `_build_opener`
  OSError -> `PageFetchError`; non-OSError programming errors propagate).
  Frozen test doubles updated where 4D-D's documented pre-search authority
  fetch is visible to them: 4D-A same-URL dedup proofs are now per-URL
  (strengthened) and account for the one bounded authority fetch; the
  FX full-persistence double supplies the `FetchedPage`-required
  `retrieved_at` it was missing (the FX path is now actually exercised);
  the web REAL-0001 fetch proof is per-URL (strengthened) and accounts for
  the one bounded authority fetch.
- FU1 corrections (this session, disclosed; supersede the authority-module
  bounded-surface wording above): the interim 4D-D pass had bounded
  uncallable fetchers, unclassified bare-`Exception` fetch failures, and
  non-conforming fetch results to `FETCH_FAILED`; independent review
  classified these as dependency/programming contract defects, and FU1
  removes that broad catch entirely (only `PageFetchError` /
  `UnsafeFetchTargetError` are downgraded; bare `Exception`, `RuntimeError`,
  non-callable `fetch`, and non-`FetchedPage` returns propagate). Frozen
  test doubles that relied on the old bounded surface were corrected to
  contract-conforming `FetchedPage` returns / classified transport errors
  (4C-B evidence-write tests, 4D-A network-error fetcher, 4C-B credential
  placeholder fetcher, execution REAL-0001 per-URL fetch proof): intent and
  assertions preserved, none deleted, renamed, skipped, xfailed, or
  deselected.

**PRODUCT-INTEL.4D-D-FU1 — APPROVED / FROZEN**

Runtime reachability + query-semantics closure for 4D-D (append-only
correction on top of the 4D-D implementation commit; the 4D-D scope,
policy, status vocabulary, persistence, codec, web, and firewall semantics
are unchanged). Fixes three independently verified source-level acceptance
blockers:

- BLOCKER 1 — real default runtime reachability: the production authority
  endpoint returns `Content-Type: application/json;charset=utf-8` (PRE2),
  but the real default `HttpPageFetcher` accepted exactly `text/html` /
  `application/xhtml+xml`, so `MICRON_PACKAGING_ALIAS` was unreachable in
  the real default runtime (authority fetch -> content-type refusal ->
  FETCH_FAILED -> ordinary query). Fix: ADDITIVE immutable
  `accepted_media_types` / `accept_header` constructor configuration on the
  existing `HttpPageFetcher` (no second HTTP/provider abstraction; no
  browser; no requests/httpx; no cookie/proxy/auth). Default configuration
  is exactly the frozen 3A behavior (`application/json` still refused by
  default; the default refusal regression remains). JSON mode accepts
  exactly `application/json` (parameters and casing ignored) and nothing
  else, sends `Accept: application/json`, and keeps every SSRF / redirect /
  credential / timeout / size bound. Default orchestration wiring:
  `execute_research_run(page_fetcher=None)` now keeps the HTML-only default
  candidate fetcher and lazily creates the JSON-configured authority
  fetcher ONLY when fallback search is required AND the request MPN is
  non-empty (direct-sufficient runs never instantiate or fetch it); an
  explicitly injected fetcher governs the authority fetch as well (existing
  deterministic fake-provider tests preserved). Mandatory real-adapter
  integration: the REAL `HttpPageFetcher` with network internals safely
  monkeypatched/offline (public DNS fixture + controlled opener returning
  the PRE2-recorded catalog bytes with the recorded Content-Type) reaches
  ESTABLISHED for `MTFDKCC3T8TGP-1BK1DABYYR` (matched base
  `MTFDKCC3T8TGP-1BK1DABYY`, manufacturer Micron, category SSD); the
  default HTML-only real fetcher refuses the SAME recorded bytes
  (`PageFetchError` / bounded FETCH_FAILED); the default production wiring
  end-to-end (`page_fetcher=None`) sends `Accept: application/json` for the
  catalog, persists ESTABLISHED, and issues exactly ONE paid search.
- BLOCKER 2 — alias query semantics: `build_alias_expanded_search_query`
  now emits the FROZEN OR shape `("REQUESTED" OR "ALIAS1" OR "ALIAS2")
  description` (group alone without a description), requested MPN first,
  aliases in deterministic relation order, exactly ONE
  `SearchProvider.search()` call, `build_search_query` unchanged. Exact
  canonical strings (description `Micron 7500 3.84TB datacenter SSD`):

  ```
  BASE:  ("MTFDKCC3T8TGP-1BK1DABYY" OR "MTFDKCC3T8TGP-1BK1DABYYR" OR "MTFDKCC3T8TGP-1BK1DABYYT") Micron 7500 3.84TB datacenter SSD
  BASER: ("MTFDKCC3T8TGP-1BK1DABYYR" OR "MTFDKCC3T8TGP-1BK1DABYY" OR "MTFDKCC3T8TGP-1BK1DABYYT") Micron 7500 3.84TB datacenter SSD
  BASET: ("MTFDKCC3T8TGP-1BK1DABYYT" OR "MTFDKCC3T8TGP-1BK1DABYY" OR "MTFDKCC3T8TGP-1BK1DABYYR") Micron 7500 3.84TB datacenter SSD
  ```

- BLOCKER 3 — broad exception catch removed: the authority module no
  longer contains `except Exception` (in any form). Expected bounded
  transport failures are the explicit `PageFetchError` (-> FETCH_FAILED) /
  `UnsafeFetchTargetError` (-> SOURCE_REFUSED) classes; a bare
  `Exception("programming defect")` and a `RuntimeError` propagate to the
  catastrophic boundary. Dependency-contract defects (non-callable
  `fetch`; non-`FetchedPage` / contract-invalid return) propagate
  `TypeError` and are never given a bounded authority status.
- HTTP_PAGE opener-OSError change (14981e3): KEPT and now separately
  regression-tested as a transport-classification fix (`_build_opener`
  OSError -> bounded `PageFetchError`; non-OSError programming errors
  still propagate). It does not, and is not claimed to, solve the Micron
  JSON reachability issue (that is BLOCKER 1).

Production files changed (FU1): `providers/http_page.py` (additive
media-type capability, defaults unchanged), `execution/orchestration.py`
(default JSON authority fetcher wiring, additive),
`execution/micron_alias_authority.py` (broad catch removed; dependency
contract defects propagate), `execution/search_query.py` (OR query shape in
`build_alias_expanded_search_query`; `build_search_query` byte-identical).

Independent review of the pushed FU1 commit (ChatGPT, acting as project
lead / independent architecture reviewer) is complete and approved
PRODUCT-INTEL.4D-D-FU1. PRODUCT-INTEL.4D-D (including 4D-D-FU1) is
APPROVED / FROZEN:

Frozen SHA: 065320180c17b89c7460164326a0c9f49e01fe3b
Frozen collection baseline: 5097 collected
Final acceptance execution: 5097 passed, 0 failed, 0 skipped, 0 xfailed,
0 deselected (+ 39 subtests passed)

**Acceptance evidence (this session, candidate pass — historical; the
final accepted execution at 5097 followed the FU1 correction):**

- Focused 4D-D matrix (7 files): 258 passed.
- Collection: 4766 (frozen 4D-C baseline) + 258 (explicit new focused 4D-D
test nodes) + 1 (new explicit 4D-D model-field inventory test in
`test_research_run_boundaries.py`) + 27 (automatic parameterized expansion
in existing boundary scans: domain +2, providers +4, research identity +8,
runs +4, web +9 — one node per new production file per scanning
parametrize) = **5052** collected. (Correction of an earlier report's
arithmetic: 5052 − 258 = 4794, not 4785; 4794 = 4766 + 28 where the +28 is
the 1 explicit inventory test + 27 automatic expansions above.)
- FINAL full suite (zero deselection, no skip/xfail injection): 5052
collected, 5042 passed (+39 subtests), 10 failed — exactly 10 of the 11
fixed Windows/Python-3.14 subprocess-boundary allowlist nodes, each with
the observed signature `subprocess.Popen -> _winapi.DuplicateHandle ->
OSError: [WinError 6] The handle is invalid`; 0 skipped, 0 xfailed,
0 deselected. The 11th allowlist node
(`tests/domain/test_domain_boundaries.py::test_domain_imports_without_django_network_or_llm_dependencies`)
passed in the final run (non-deterministic by nature).
- `python manage.py check`: System check identified no issues (0 silenced).
- `python manage.py makemigrations --check --dry-run`: No changes detected.
- Frozen 2A/3C/4A/semantic/HUMAN-REVIEW/vendor-commercial/compact-quote
files byte-identical to the parent (mechanically verified).
- Process disclosure: an earlier interrupted 4D-D diagnostic session used
`--deselect` once (530 passed, 7 deselected — diagnostic boundary run only,
no test modified); the final acceptance suite used zero deselection.
- Historical marker: the 5052-collection numbers above record the
  candidate pass (pre-FU1). Final approval/freeze happened only after
  independent review of the pushed FU1 commit — APPROVED / FROZEN at
  SHA 065320180c17b89c7460164326a0c9f49e01fe3b, 5097 collected,
  5097 passed (see the 4D-D-FU1 approval record above).

Semantic qualification is APPROVED AND FROZEN:
- Semantic qualification corpus, prompt v1.1, evaluator mathematics,
  qualification thresholds, expected decisions, and safety gates approved
- Prompt v1.1 FULL SHA256: f50e5584659f953ce73a97ccc8bc1ff487fbeeb37e2e0a72e52210613aeab1ff
- Corpus SHA256: 3c21d6fcd4eefa5cc383792abfd9308bd5c03315834c8ffdffd0f6a2b3619ca1

**Two models passed the formal FULL qualification gates.** They are the
qualified production route:

| Role | Provider | Model |
| --- | --- | --- |
| PRIMARY | `amax` | `nemotron-3-super` |
| FALLBACK | `vllm-262k` | `Qwen3.6-27B-262K` |

Generation settings are fixed at `temperature=0.0`, `max_tokens=32768`.

FU3A — Production Semantic Runtime Contract — **APPROVED / FROZEN**
(corrective history: FU3A2B/C/D/E/F; FU3A2F was the final corrective pass —
ChatGPT's review of the final FU3A2F `runtime.py` and `test_runtime.py`
approved the contract):

FU3B — Semantic execution integration — **APPROVED / FROZEN**
(corrective history: FU3B was the execution-wiring pass; MiniMax M2.7 Thinking
independently reviewed the final FU3B implementation and found no production-code
or safety-contract blocker; ChatGPT performed the final approval/freeze review):
- `product_intelligence/semantic/contract.py` is the single source of truth for
  prompt v1.1, the decision vocabulary, the response schema, and the strict
  parser/validator. The evaluation harness re-exports those same objects;
  production does not depend on `evaluation.semantic.*`.
- `product_intelligence/semantic/transport.py` is the single source of truth
  for the transport implementation (HTTP call, error classification,
  `SemanticModelTransport`/`OpenAISemanticTransport`/`FakeSemanticModelTransport`);
  `evaluation/semantic/transport.py` re-exports it rather than keeping a copy.
- `product_intelligence/semantic/runtime.py` pins the qualified route
  (validation rejects any other provider/model/temperature/max_tokens before a
  transport call — temperature is checked by exact type, `type(x) is float`,
  so `0`/`False` are rejected even though numerically equal to `0.0`), falls
  back on an EXPLICIT allowlist of execution failures, requires exact
  provider-reported model identity, records per-attempt provenance, and never
  converts a programming exception into a fallback.
- The fallback allowlist and error taxonomy are complete over every code the
  canonical transport can return (`INVALID_PROVIDER_RESPONSE` is fallback
  eligible like `MALFORMED_JSON`/`SCHEMA_INVALID`; `CASE_REJECTED` is a known,
  non-fallback-eligible code — neither is lost into `UNKNOWN_ERROR`).
- `SemanticRuntimeResult` fully self-validates: every typed field is checked
  by exact type (not merely truthy-equal), and a failure's `error_type` is
  mechanically bound to what its attempts actually recorded.
- Importing `product_intelligence.semantic` pulls in no evaluation module, no
  Django, and no network client. The live transport is resolved lazily.

**The frozen semantic runtime is wired into execution** behind the semantic integration boundary for explicitly eligible candidates. The frozen runtime exists
and is tested offline; it is called from the research pipeline through `evaluate_semantic_matches` — that
wiring was FU3B, now implemented and approved.

AI_ASSISTED_MATCH remains outside existing 4A aggregation.

A semantic MATCH is represented by:
    original ListingIdentityAssessment.decision == REJECTED
    +
    AiAssistedMatchResult.disposition == AI_ASSISTED_MATCH

There is no AI_ASSISTED_MATCH ListingIdentityAssessment.

Existing 4A sees the original deterministic REJECTED assessment and
excludes it as IDENTITY_NOT_ACCEPTED.

Only EvidenceDecision.ACCEPTED automatically enters 4A Machine Price.

## Project facts (already delivered outside repo)

- FoxPro launcher: **Manually integrated outside this repository — delivered,
  not pending.** The client code is maintained in the existing Visual FoxPro
  sales-order application. The server-side GET prefill contract is implemented
  and localhost UAT passed.
- 4C-B-FU corrective: Exact structural duplicate ListingObservation
  deduplication implemented in `execution/orchestration._deduplicate_exact_observations`.

## FU3B — Semantic execution integration

**APPROVED / FROZEN**

FU3B wires the frozen FU3A semantic runtime into real research execution:

- Deterministic matching remains first authority; deterministic `ACCEPTED` bypasses semantic
- Explicit `MPN_MISMATCH` bypasses semantic
- Semantic eligible:
  - `NO_EXPLICIT_MPN_EVIDENCE + TITLE_TEXT`
  - `NO_EXPLICIT_MPN_EVIDENCE + SKU_FIELD`
  - `PARTIAL_MPN_ONLY`
- Not semantic-enabled in FU3B:
  - `NO_EXPLICIT_MPN_EVIDENCE + NONE`
  - description-only / `UNDECIDED`
- Bounded semantic failure leaves run usable
- Programming/config exceptions propagate to existing catastrophic boundary
- AI-assisted matches retained in `ExecutionResult.ai_assisted_matches`
- `ai_assisted_match_count` is derived
- `AiAssistedMatchResult` mechanically binds provenance
- `SEMANTIC` execution evidence uses bounded controlled detail codes
- Migration 0005 is choices-only metadata
- `AI_ASSISTED_MATCH` remains entirely outside 4A
- `PriceIntelligenceSnapshot` remains deterministic-only

## Phase ownership

| Phase | Description | Status |
| --- | --- | --- |
| PILOT-RELEASE-1 | Internal pilot deployment | **DEPLOYED / ACCEPTED** |
| PILOT-RELEASE-2 | 4D Customer Requirement Deployment & UAT | **DEPLOYED / ACCEPTED** (deployed runtime SHA 065320180c17b89c7460164326a0c9f49e01fe3b; production smoke passed 2026-09-23; migrations through 0010 deployed) |
| PILOT-RELEASE-2-PROD-FIX1 | Production quote-workflow defect corrections (Vendor real-response contract, currency formatting, semantic-section placement, Confirm Match -> Compact Quote, submit guard, ECB/TLS non-bypass) | **IMPLEMENTED / REVIEW BLOCKERS CORRECTED BY FU1 / PENDING FINAL REVIEW** (no deployment in this commit) |
| PILOT-RELEASE-2-PROD-FIX1-FU1 | Bounded review-blocker closure (vendor hybrid production-wire fidelity + section-scanner consistency, human-confirmed authority ownership at the replay boundary, ECB evidence correction, Reviewed Price wording accuracy) | **IMPLEMENTED / FINAL REVIEW BLOCKER CORRECTED BY FU2 / PENDING FINAL REVIEW** (no deployment in this commit; canonical spec PLAN §26.11) |
| PILOT-RELEASE-2-PROD-FIX1-FU2 | Final review-blocker closure (public/denied historical replay binds to the run's own persisted PriceIntelligenceSnapshot; caller-supplied price results removed as an authority input) | **IMPLEMENTED / PENDING FINAL REVIEW** (no deployment in this commit; canonical spec PLAN §26.12) |
| PILOT-RELEASE-2-PROD-FIX1-FU3 | Bounded production defect closure (vendor section scanner: exact observed `<p>` paragraph-prefix envelope — narrow literal, NOT a generic HTML parser) | **IMPLEMENTED / PENDING FINAL REVIEW** (no deployment in this commit; canonical spec PLAN §26.13) |
| PUBLIC-RESEARCH-RECALL-FU1 | Production-priority exact-MPN recall defect (exact-MPN first-class retrieval query; adapter recall page — `num=50` at FU1 time, corrected by FU2; Micron 7500 SSD policy NOT_APPLICABLE applicability gate) | **IMPLEMENTED / APPROVED / DEPLOYED** (runtime SHA 2326d1d62738801598f8b52143d59b0bcdc86819; canonical spec PLAN §26.19; baseline 5802 collected; Serper wire contract corrected by FU2, PLAN §26.20) |
| PUBLIC-RESEARCH-RECALL-FU2 | Serper wire-contract compatibility correction (explicit `num=50` result-count parameter removed; wire body `{"q": ...}` only; provider default organic count; all FU1 retrieval/identity/alias behavior unchanged) | **IMPLEMENTED / PENDING FINAL REVIEW** (no deployment in this commit; canonical spec PLAN §26.20; baseline 5838 collected) |
| 8A-PRE | Caching & Freshness Architecture Audit | **APPROVED / COMPLETE** (design audit delivered; READ-ONLY phase, no caching implementation; record: `docs/PRODUCT_INTEL_8A_PRE_CACHING_FRESHNESS_AUDIT.md`) |
| 8A-FX-DESIGN | FX cache lookup identity & freshness design | **APPROVED / COMPLETE** (design record; superseded where corrected by FU1; `docs/PRODUCT_INTEL_8A_FX_DESIGN.md`) |
| 8A-FX-DESIGN-FU1 | Freshness proof & canonical-feed eligibility closure | **APPROVED / FROZEN as design** (corrects the same-UTC-day proof window and the isinstance feed gate; `docs/PRODUCT_INTEL_8A_FX_DESIGN_FU1.md`) |
| 8A-FX-A1 | Canonical ECB Observation Cache (first safe caching slice) | **IMPLEMENTED / PENDING FINAL REVIEW** (no deployment in this commit; canonical spec PLAN §26.18; AD-064) |
| 4D-PRE | Preferred Source Feasibility Audit | Implemented (evidence only, frozen) |
| 4D-A | Source Acquisition Optimization | Implemented (frozen) |
| 4D-B | Internal Vendor Commercial Evidence | **Implemented (approved / frozen)** |
| 4D-C-A | ECB FX + Compact Quote Projection Foundation | **IMPLEMENTED / APPROVED / FROZEN** |
| 4D-C-SEC | Vendor Commercial Price Access Gate | **IMPLEMENTED / APPROVED / FROZEN** |
| 4D-C | Compact Quote Summary (browser rendering) | **IMPLEMENTED / APPROVED / FROZEN** |
| 4D-D | Micron Packaging Alias Retrieval (incl. 4D-D-FU1) | **Implemented (approved / frozen)**; PRE1 + PRE2 frozen; frozen SHA 065320180c17b89c7460164326a0c9f49e01fe3b; frozen baseline 5097 collected |
| 4C-A | Execution ownership/lifecycle/evidence primitives | Implemented (frozen) |
| 4C-B | Backend research execution | Implemented (frozen) |
| 4C-B-FU | Exact duplicate deduplication | Implemented (frozen) |
| 4C-C | Web execution/retry integration | Implemented (frozen) |
| 5A | Structured external API | Planned (not implemented; non-blocking for the current FoxPro/browser workflow) |
| 5B | FoxPro launcher | Server-side implemented; client integrated outside repo, UAT passed |
| PILOT-UX | Pilot UX polish + semantic qualification | **FROZEN** |
| HUMAN-REVIEW | Human review for AI-assisted semantic matches | Implemented (frozen)
| 6A | Product Specification Framework | Implemented (frozen)
| 6B | Enterprise SSD Category Schema | Implemented (approved / re-frozen)
| 6C | Specification Evidence Extraction & Resolution | Implemented (frozen)
| 6D | Authoritative Datasheet Specification Enrichment | Implemented (approved / frozen)
| 7A | Comparable-Product Candidate Discovery | Implemented (frozen)
| 7B | Enterprise SSD Similarity Scoring | Implemented (approved / frozen)
| 7C | Comparable-Product Presentation | **IMPLEMENTED / APPROVED / FROZEN** — 7C-PRE1 FROZEN; 7C-PRE2 FROZEN; 7C-A FROZEN; 7C-B FROZEN; 7C-C FROZEN
| SAP | SAP launcher integration | Future |


## Implementation snapshot

| Component | Package | Status |
| --- | --- | --- |
| Domain contracts + vocabularies | `domain/` | Implemented |
| Evaluation corpus + loader | `evaluation/` | Implemented |
| Semantic match corpus + evaluator | `evaluation/semantic/` | **Implemented (frozen)** |
| Semantic match prompt template v1.1 | `evaluation/semantic/prompt.py` | **Implemented (frozen)** |
| Semantic match export/import | `evaluation/semantic/` | **Implemented** |
| Semantic match transport | `evaluation/semantic/transport.py` | **Implemented** |
| Semantic match model catalog | `evaluation/semantic/model_catalog.py` | **Implemented** |
| Semantic match benchmark runner | `evaluation/semantic/runner.py` | **Implemented** |
| Semantic match CLI | `evaluation/semantic/cli.py` | **Implemented** |
| Semantic match comparison | `evaluation/semantic/comparison.py` | **Implemented** |
| Semantic match tests | `tests/evaluation/semantic/` | **Implemented (frozen)** |
| Semantic neutral contract (canonical) | `semantic/contract.py` | **Implemented (frozen, FU3A)** |
| Semantic neutral transport (canonical) | `semantic/transport.py` | **Implemented (frozen, FU3A)** |
| Semantic production runtime | `semantic/runtime.py` | **Implemented (frozen, FU3A)** |
| Semantic runtime tests | `tests/semantic/test_runtime.py` | **Implemented** |
| Semantic transport tests | `tests/semantic/test_transport.py` | **Implemented** |
| Semantic runtime boundaries | `tests/semantic/test_runtime_boundaries.py` | **Implemented** |
| Semantic contract sharing proof | `tests/semantic/test_contract_sharing.py` | **Implemented** |
| Semantic execution integration | `execution/semantic_integration.py` | **Implemented (frozen, FU3B)** |
| EvidenceDecision.AI_ASSISTED_MATCH | `domain/enums.py` | **Reserved (frozen semantic identity disposition, FU3A)** |
| Persisted run lifecycle | `runs/` | Implemented (ResearchRun) |
| Execution evidence model | `runs/` | Implemented (ExecutionEvidenceRecord) |
| Execution claim service | `runs/` | Implemented (claim_execution) |
| Execution completion service | `runs/` | Implemented (complete_execution) |
| Retry service | `runs/` | Implemented (retry_run) |
| Price intelligence snapshot | `runs/` | Implemented (PriceIntelligenceSnapshot) |
| Standalone web shell | `web/` | Implemented |
| Part-number comparison | `research/identity` | Implemented |
| Search provider boundary | `providers/search.py` | Implemented |
| Serper adapter | `providers/serper.py` | Implemented |
| Page fetch + extraction | `providers/http_page.py` + `research/listings.py` | Implemented |
| Listing normalization | `research/normalization.py` | Implemented |
| MPN matching + rejection | `research/matching.py` | Implemented |
| Price aggregation (frozen) | `research/aggregation.py` | **Implemented (frozen)** |
| Versioned codec | `research/price_result_codec.py` | Implemented |
| Price report presentation | `web/presentation.py` | Implemented |
| Research orchestration | `execution/` | **Implemented (frozen)** |
| Web execution wiring | `web/` | **Implemented (frozen)** |
| Structured API | — | 5A (not implemented) |
| FoxPro launcher | — | Server-side implemented; client integrated outside repo, UAT passed |
| SAP launcher | — | Future |
| Human review candidate model | `runs/` (AiAssistedReviewCandidate) | **Implemented (frozen, HUMAN-REVIEW)**
| Human review service | `runs/ai_assisted_review.py` | **Implemented (frozen, HUMAN-REVIEW)**
| Reviewed price aggregation | `research/aggregation.py` (aggregate_reviewed_listing_prices) | **Implemented (frozen, HUMAN-REVIEW)**
| Human review web view + URLs | `web/views.py` + `web/urls.py` | **Implemented (frozen, HUMAN-REVIEW)**
| Human review candidate presentation | `web/presentation.py` | **Implemented (frozen, HUMAN-REVIEW)**
| Product Specification Framework (6A) | `research/specifications.py` | **Implemented (frozen)**
| Enterprise SSD Category Schema (6B) | `research/enterprise_ssd.py` | **Implemented (approved / re-frozen)**
| Enterprise SSD Specification Extraction (6C) | `research/enterprise_ssd_extraction.py` | **Implemented (frozen)**
| Specification Evidence Execution (6C) | `execution/specification_evidence.py` | **Implemented (frozen)**
| Comparable-Candidate Contracts (7A) | `research/comparable_candidates.py` | **Implemented (frozen)**
| Enterprise SSD Candidate Extraction (7A) | `research/enterprise_ssd_candidate_extraction.py` | **Implemented (frozen)**
| Comparable Discovery Execution (7A) | `execution/comparable_discovery.py` | **Implemented (frozen)**
| Enterprise SSD Similarity Scoring (7B) | `research/enterprise_ssd_similarity.py` | **Implemented (approved / frozen)**
| Comparable Similarity Execution (7B) | `execution/comparable_similarity.py` | **Implemented (approved / frozen)**
| Comparable Research Results + Codec (7C-A) | `research/comparable_research_results.py` + `research/comparable_result_codec.py` | **Implemented (frozen)**
| Comparable Research Orchestration (7C-B) | `execution/comparable_orchestration.py` | **Implemented (frozen)**
| Comparable Web Trigger & Presentation (7C-C) | `web/views.py` + `web/comparable_presentation.py` | **Implemented (frozen)**
| Document Provider Boundary (6D) | `providers/document.py` | **Implemented (approved / frozen)**
| HTTP PDF Fetcher (6D) | `providers/http_pdf.py` | **Implemented (approved / frozen)**
| Datasheet Table Interpretation (6D) | `research/enterprise_ssd_datasheet.py` | **Implemented (approved / frozen)**
| Specification Enrichment Execution (6D) | `execution/specification_enrichment.py` | **Implemented (approved / frozen)**
| Commercial Source Boundary (4D-B) | `providers/commercial.py` | **Implemented (approved / frozen)** |
| Internal Vendor Adapter (4D-B) | `providers/internal_vendor.py` | **Implemented (approved / frozen)** |
| Supplemental Snapshot Model (4D-B) | `runs/models.py` (ResearchSupplementSnapshot) | **Implemented (approved / frozen)** |
| Supplemental Codec (4D-B) | `research/commercial_supplement_codec.py` | **Implemented (approved / frozen)** |
| ECB FX Provider (4D-C-A) | `providers/fx.py` | **Implemented (approved / frozen)** |
| FX Snapshot Model (4D-C-A) | `runs/models.py` (ResearchFxSnapshot) | **Implemented (approved / frozen)** |
| FX Codec (4D-C-A) | `research/fx_codec.py` | **Implemented (approved / frozen)** |
| FX Cache Contract (8A-FX-A1) | `research/fx_cache_contract.py` (pure digest + projection + freshness predicate) | **Implemented (pending final review)** |
| FX Observation Store Model (8A-FX-A1) | `runs/models.py` (FxObservationStore) + migration 0011 | **Implemented (pending final review)** |
| FX Observation Cache Service (8A-FX-A1) | `execution/fx_observation_cache.py` (lookup + bounded write + reconciliation) | **Implemented (pending final review)** |
| FX Mathematics (4D-C-A) | `research/fx_math.py` | **Implemented (approved / frozen)** |
| Compact Quote Projection (4D-C-A) | `research/compact_quote.py` | **Implemented (approved / frozen)** |
| Commercial Price Access Gate (4D-C-SEC) | `web/commercial_access.py` | **Implemented (approved / frozen)** |
| Compact Quote Public Replay (4D-C) | `execution/compact_quote_public_replay.py` | **Implemented (approved / frozen)** |
| Compact Quote Browser Presentation (4D-C) | `web/compact_quote_presentation.py` | **Implemented (approved / frozen)** |
| Micron 7500 Packaging Alias Contracts (4D-D) | `research/micron_packaging_alias.py` | **Implemented (approved / frozen)**; extended by PUBLIC-RESEARCH-RECALL-FU1 (bounded non-SSD applicability vocabulary + `NOT_APPLICABLE` pre-fetch abstention; v1 scope and all 4D-D authority semantics unchanged) |
| Micron Alias Snapshot Codec (4D-D) | `research/micron_alias_codec.py` | **Implemented (approved / frozen)**; round-trips the new `NOT_APPLICABLE` status with no schema change (V1) |
| Micron Alias Authority Acquisition (4D-D) | `execution/micron_alias_authority.py` | **Implemented (approved / frozen)**; extended by PUBLIC-RESEARCH-RECALL-FU1 (pre-fetch NOT_APPLICABLE applicability gate; zero fetches for established memory-module requests) |
| Alias Snapshot Model (4D-D) | `runs/models.py` (ResearchMicronAliasSnapshot) + migration 0010 | **Implemented (approved / frozen)** |
| Alias Browser Presentation (4D-D) | `web/micron_alias_presentation.py` | **Implemented (approved / frozen)** |

## Research orchestration

Base 4C orchestration contract: **frozen** (exact-MPN query prioritization
corrected by PUBLIC-RESEARCH-RECALL-FU1 — the paid query for an
explicit-MPN request is the exact-MPN phrase; see PLAN §26.19)
FU3B semantic execution extension: **APPROVED / FROZEN**

Implementation snapshot:

- Research orchestration: Base 4C frozen (recall correction per
  PUBLIC-RESEARCH-RECALL-FU1); FU3B semantic extension frozen
- Semantic execution integration: Implemented / APPROVED / FROZEN

## Web layer architecture

The web layer may import only the public execution API and the approved read-side research symbols:

```
web  ->  product_intelligence.execution  (execute_research_run, ExecutionError,
         ComparableResearchExecutionError, execute_comparable_research_with_default_providers)
web  ->  product_intelligence.runs  (ClaimExecutionFailed, retry_run, ResearchRun,
         confirm_candidate, reject_candidate, undo_review, review errors,
         trigger_comparable_research, ComparableResearchTriggerError,
         ComparableResearchClaimError)
web  ->  product_intelligence.research.price_result_codec
         (PriceResultCodecError, decode_price_aggregation_result)
web  ->  product_intelligence.research.aggregation
         (PriceAggregationResult, aggregate_reviewed_listing_prices)
web  ->  product_intelligence.research.matching
         (ListingIdentityAssessment, is_human_review_eligible_assessment)
web  ->  product_intelligence.research.comparable_result_codec
         (ComparableResultCodecError, decode_comparable_result)          # 7C-C
web  ->  product_intelligence.research.comparable_research_results
         (ComparableResultKind, AuthorityAttemptResult, ComparableCandidateResult,
          ComparableResearchResult, DatasheetAttemptResult,
          EvidenceSourceReference, FieldAssessmentResult, ProductEnrichmentAudit)  # 7C-C
web  ->  product_intelligence.research.enterprise_ssd
         (ENTERPRISE_SSD_SCHEMA)                                          # 7C-C
web  ->  product_intelligence.runs.models
         (ResearchRun, PriceIntelligenceSnapshot, AiAssistedReviewCandidate,
          ComparableResearchExecution, ComparableResearchState)            # 7C-C
```

**Narrow 7C-C read-side exception:**

The general prohibition on `product_intelligence.research.identity` remains.
However, the ONE narrow exception is:

```
views.py  ->  product_intelligence.research.identity  (compare_part_numbers)
```

This is allowed **solely** for persisted comparable-result / parent binding
validation in `views._validate_comparable_result_parent_binding()`. It is
the frozen 2A part-number comparison primitive used read-side only.
`comparable_presentation.py` (pure display) must NOT import this symbol.

The web layer MUST NOT import:
- `product_intelligence.execution.orchestration` (or any execution submodule)
- `product_intelligence.execution` (bare module import)
- `product_intelligence.providers` (or any provider submodule)
- `product_intelligence.runs.execution_claims` (internal)
- `product_intelligence.research.identity` (research decision primitive,
  except the ONE narrow views.py exception documented above)
- Any unapproved symbol from approved research modules

Web writes review state through the runs-owned review service
(`runs/ai_assisted_review.py`). Web may perform approved read-side
composition and binding validation as enforced by boundary tests.
Web must not bypass providers, must not own execution internals,
and must not carry research semantics.

`comparable_presentation.py` is DISPLAY-ONLY: it reuses the authoritative
URL safety helper from `presentation._is_safe_href_url` (no duplication),
imports only research contracts/schema for presentation, and contains no
runs, execution, providers, Django ORM, or research decision primitives.

## FoxPro ownership

FoxPro source code is NOT maintained in this repository. This repository
owns only the launcher-facing HTTP intake contract:

```
GET /research/new?mpn=<encoded>&description=<encoded>
```

The project lead maintains the FoxPro client code manually in the existing
Visual FoxPro sales-order application.

## Human Review authority model

HUMAN-REVIEW is IMPLEMENTED / APPROVED / FROZEN.

Required authority layers:

1. Deterministic identity
   ListingIdentityAssessment.decision == ACCEPTED
   remains the only automatic existing-4A identity authority.

2. Semantic match
   original ListingIdentityAssessment.decision == REJECTED
   +
   AiAssistedMatchResult.disposition == AI_ASSISTED_MATCH

   Snapshot assessment itself is never AI_ASSISTED_MATCH.

3. Human review overlay
   run-scoped AiAssistedReviewCandidate
   states:
       UNREVIEWED
       CONFIRMED
       REJECTED
   actions:
       Confirm
       Reject
       Undo

   Human confirmation never mutates snapshot assessment.

4. Machine Price
   deterministic ACCEPTED only.

5. Reviewed Price
   deterministic ACCEPTED
   +
   human-CONFIRMED semantic-eligible listings.

   Preserve origin:
       DETERMINISTIC
       HUMAN_CONFIRMED

6. Human confirmation changes identity authority only.
   Existing deterministic non-identity price eligibility remains:
       Decimal price
       comparable currency
       known condition

7. Candidate binding fails closed:
   exact run/snapshot assessment + provenance must match before mutation.

8. Candidate creation is run-scoped and participates in final publication.

9. No reviewer identity/authentication/audit identity was introduced.


## Eligibility boundary

Eligible original deterministic assessments ONLY:

    REJECTED
    + NO_EXPLICIT_MPN_EVIDENCE
    + TITLE_TEXT

    REJECTED
    + NO_EXPLICIT_MPN_EVIDENCE
    + SKU_FIELD

    REJECTED
    + PARTIAL_MPN_ONLY

Not eligible:

    ACCEPTED
    UNDECIDED
    MPN_MISMATCH
    NO_EXPLICIT_MPN_EVIDENCE + NONE
    any other non-semantic-eligible state


## Validation results

### 8A-FX-A1 CANDIDATE ACCEPTANCE SNAPSHOT (PENDING FINAL REVIEW)

Validation of PRODUCT-INTEL.8A-FX-A1 (Canonical ECB Observation Cache)
on starting SHA 55d1879a03da3dc6163a28c9524b5ef0396b76b3, this session
(Windows / Python 3.14 workstation; no deployment performed):

| Metric | Count |
| --- | --- |
| Collected (before) | 5633 |
| Collected (after) | 5783 |
| Full suite: passed | 5772 |
| Full suite: failed | 11 (EXACTLY the documented fixed eleven-node Windows/Python 3.14 subprocess-boundary flake allowlist; each with the recorded `OSError: [WinError 6]` `subprocess.Popen -> _winapi.DuplicateHandle` signature; 0 nodes outside the allowlist failed) |
| Full suite: errors | 0 |
| Full suite: skipped | 0 |
| Full suite: xfailed | 0 |
| Full suite: deselected | 0 |
| Full suite: subtests passed | 39 |

Focused A1 suites (this session, before the final full run): pure
temporal/codec contract 76 passed (tests/research/test_fx_cache_contract.py
— includes naive rejection, UTC/Brussels conversion, DST spring/fall,
weekend boundaries, UTC-vs-Brussels date divergence, digest
determinism/order-independence/correction-sensitivity, Decimal exactness);
store model 16 passed; cache service 37 passed (fail-closed integrity,
bounded reconciliation, unrelated-IntegrityError propagation);
canonical orchestration 22 passed (USD-only zero-work, LIVE one-fetch,
CACHE_HIT zero-fetch, injected fake/real/subclass/wrapper bypass,
working-day and Monday-boundary live revalidation, nonfatal
FxProviderError, corruption/unsupported-codec propagation, publication
atomicity, deterministic concurrency convergence, replay zero-live);
authority/guards 9 passed (Machine Price bytes identical LIVE/CACHE_HIT/
FX-absent; USD equivalent identical LIVE vs CACHE_HIT; no
provider-class-identity eligibility logic; FX step catches only bounded
FxProviderError; no dependency inversion); web presentation 7 passed
(line renders on both branches; labels correct; no internal detail
leakage; zero live/cache work on GET; provenance preserved; historical
rows LIVE). Feed-identity mirror-lock: +4 nodes in
tests/providers/test_fx_provider.py. Boundary inventories updated to the
exact supersets only: model inventories in
tests/providers/test_provider_boundaries.py,
tests/research/test_research_identity_boundaries.py,
tests/runs/test_research_run_boundaries.py, tests/web/test_web_boundaries.py
(gain `runs.FxObservationStore`); the research-core Decimal allowlist in
tests/research/test_listing_normalization_boundaries.py gains
`fx_cache_contract.py` (the new pure contract's exact-Decimal digest).
No test deleted, renamed, skipped, xfail'd, deselected, or weakened.

`python manage.py check` -> System check identified no issues (0
silenced). `python manage.py makemigrations --check --dry-run` -> No
changes detected (0011 is the only new migration). `git diff --check`
clean. Collection did not decrease (5633 -> 5783, +150).

Note on the flake class: the eleven allowlist nodes spawn a clean
subprocess to prove isolated imports; they failed in this final full run
with the documented WinError 6 signature and re-passed in isolated retry
earlier in the session (the class is non-deterministic by nature and is
recorded as such for every prior phase). No new failure class appeared:
the single non-flake failure observed in an earlier full run
(tests/research/test_listing_normalization_boundaries.py::
test_normalization_and_aggregation_may_use_decimal) was a real boundary
exposure from the new `research/fx_cache_contract.py` Decimal usage and
was corrected by the exact-superset allowlist entry above (disclosed here
and in the test file), after which the full suite showed only allowlist
members.

**8A-FX-A1-FU1 immutable retrieval-provenance integrity correction.**
Independent review of the actual A1 GitHub commit (starting SHA
`208a5a21c8fc1b8d9262983b4011e6c4611c5bc1`) found one bounded
provenance-integrity blocker: `_validate_row_integrity` compared the
decoded payload `retrieved_at` against the row's immutable
`original_retrieved_at` column and rejected only ONE direction of
disagreement (payload later than the column). The two values are the
SAME immutable provenance fact — the original provider retrieval
instant of this exact stored content — so a payload retrieved_at
EARLIER than the column was incorrectly accepted. A1-FU1 (append-only
correction; no A1 redesign, no caching/freshness/cache-identity/
authority change, no migration 0011 change, no existing commit
rewritten) makes the check EXACT instant equality after UTC
normalization: any mismatch in EITHER direction raises
`FxObservationStoreIntegrityError` (a persisted-cache integrity
failure — never a cache miss, never a live fallback, never a delete,
silent repair, or timestamp overwrite). No existing test encoded the
asymmetric comparison as intended behavior (reviewed before changing);
regression tests were added only.

Exact production change (single file
`product_intelligence/execution/fx_observation_cache.py`):

1. `_validate_row_integrity`: `parsed_retrieved > row.original_retrieved_at`
   replaced by `parsed_retrieved != row.original_retrieved_at` (exact
   instant equality; both disagreement directions corrupt).
2. `record_live_observation`: the immutable `original_retrieved_at`
   column is pinned ONCE at the write boundary to the codec V1's
deterministic whole-second precision (`stored_retrieved =
   utc_retrieved.replace(microsecond=0)`), so the payload
   representation and the column representation hold the SAME instant
   by construction. The frozen A1 authority tests (a LIVE run proves
   the document with the provider's real microsecond wall-clock
   `retrieved_at`, then a CACHE_HIT run reuses that exact system-
   written row) demonstrated that without this write-boundary pin,
every wall-clock-written row would carry a sub-second payload-vs-
column disagreement — precisely the state the FU1 contract classifies
corrupt. The proof-before-retrieval sanity check still uses the
full-precision instant (never loosened); the read path never
truncates (no read-side tolerance); `last_proven_at` / `created_at`
keep full precision. Cache identity, freshness policy, and all re-
proof semantics are unchanged: a later identical-content re-proof
still advances ONLY `last_proven_at`, and the re-proof input
`retrieved_at` never replaces either stored instant.

New regression nodes (8; no test deleted, renamed, skipped, xfailed,
deselected, or weakened):

* `tests/execution/test_fx_observation_cache.py` (+6): payload
  retrieved_at EARLIER than column -> FxObservationStoreIntegrityError
  (row retained); payload retrieved_at LATER than column ->
  FxObservationStoreIntegrityError (row retained); same instant via an
  equivalent Brussels-offset column representation -> accepted after
  instant normalization; same instant via the codec-accepted `Z`
  designator -> accepted; later identical-content re-proof (provider
  T2) -> original_retrieved_at / payload / created_at unchanged, only
  last_proven_at advanced; write boundary pins a microsecond wall-
  clock retrieved_at to the codec instant and the system-written row
  passes its own exact-instant validation on the next read.
* `tests/execution/test_fx_cache_orchestration.py` (+2): CACHE_HIT run
  over a row whose payload retrieved_at precedes its column -> fails
  closed through the existing catastrophic boundary (ExecutionError;
  run FAILED), ZERO ECB live fallback calls, corrupted row retained
  byte-identical (no repair); legitimate later live re-proof of
  identical content through a full canonical run -> converges on the
  same row; original_retrieved_at and stored payload unchanged; only
  last_proven_at advanced; run snapshot LIVE.

A1-FU1 validation (this session, Windows / Python 3.14 workstation; no
deployment performed):

| Metric | Count |
| --- | --- |
| Collected (before) | 5783 |
| Collected (after) | 5791 (+8; collection did not decrease) |
| Focused FX cache suites | 67 passed (59 pre-existing + 8 new) |
| All FX-related suites | 250 passed |
| Full suite: passed | 5789 |
| Full suite: failed | 2 (members of the fixed eleven-node Windows/Python 3.14 subprocess flake allowlist; each with the recorded `subprocess.Popen -> _winapi.DuplicateHandle -> OSError: [WinError 6]` signature; each re-passed on isolated retry; NO node outside the allowlist failed) |
| Full suite: errors / skipped / xfailed / deselected | 0 / 0 / 0 / 0 |
| Full suite: subtests passed | 39 |

`git diff --check` clean; `python manage.py check` -> System check
identified no issues (0 silenced); `python manage.py makemigrations
--check --dry-run` -> No changes detected (no model change; 0011
untouched). A1 remains PENDING FINAL REVIEW with this bounded
correction appended; the fixed eleven-node flake allowlist remains the
only permitted environmental failure set.

### PROD-FIX1-FU4-FU1 CANDIDATE ACCEPTANCE SNAPSHOT (PENDING FINAL
REVIEW)

| Metric | Count |
| --- | --- |
| Collected | 5352 |
| Passed | 5341 |
| Failed | 11 (exactly the fixed allowlist; non-deterministic) |
| Unexpected failures | 0 |
| Skipped | 0 |
| Xfailed | 0 |
| Deselected | 0 |
| Subtests passed | 39 |

Full-suite execution of the final FU4-FU1 tree (zero deselection, no
skip/xfail injection; JUnit report): 5352 tests + 39 subtests
executed; 5341 passed, 11 failed — the 11 failures are EXACTLY the
members of the fixed eleven-node Windows/Python 3.14 subprocess-boundary
flake allowlist (every one failed in this run), each with the recorded
signature `subprocess.run -> Popen -> _winapi.DuplicateHandle ->
OSError: [WinError 6] The handle is invalid` (2) / `[WinError 50] The
request is not supported` (9), and NO node outside that allowlist
failed. The allowlist is non-deterministic by nature, exactly as
recorded for every prior phase; the fixed allowlist remains exactly
11 nodes (not expanded).

Collection accounting: 5347 FU4 baseline + 5 FU4-FU1 net-new nodes
= 5352 collected. Net-new (all in
`tests/providers/test_vendor_section_response.py::TestParagraphEntity
Decoding`): `test_hex_numeric_lf_entity_decoded_to_lf` (the exact
hex numeric LF entity decodes to LF on the paragraph path),
`test_hex_numeric_cr_entity_decoded_to_cr` (the exact hex numeric CR
entity decodes to CR), `test_decode_table_is_exactly_the_observed_
literals` (the ONLY approved decode table contains exactly
`&quot;` / the exact hex numeric LF entity / the exact hex numeric CR
entity, with character-by-character literal verification: LF
0x26/0x23/0x78/0x41/0x3B, CR 0x26/0x23/0x78/0x44/0x3B; no `&nbsp;` /
`&cr;` entries), `test_equivalent_numeric_representations_are_never_
decoded` (decimal `&#10;` / `&#13;` / `&#65;` / `&#39;` / `&#38;`
/ `&#60;` / `&#62;` and hex variants `&#x0a;` / `&#x0d;` / `&#X0A;`
/ `&#X0D;` / `&#x000A;` / `&#x000D;` are NOT decoded — inert raw
text inside bounded strings), `test_hex_entity_case_variants_are_
never_decoded` (`&#xa;` / `&#XA;` / `&#xd;` / `&#XD;` are NOT
decoded). FU4-specific test corrections (node count unchanged):
`test_nbsp_and_cr_entities_decoded_to_lf_and_cr` RETAINED with its
assertion purpose corrected (now proves `&nbsp;` and `&cr;` are NOT
decoded; the name records the rejected FU4 contract),
`test_plain_form_section_values_are_never_decoded` strengthened
(all approved spellings plus the unsupported `&nbsp;` / `&cr;` remain
raw on the plain path), `test_unapproved_named_entities_are_never_
decoded` extended to cover `&nbsp;` / `&cr;`, faithful
production-shaped fixtures (provider + execution) corrected to the
exact observed entity encoding. No test node deleted or renamed
anywhere; no skip/xfail/deselection; no weakening.

Focused execution: `tests/providers/test_vendor_section_response.py`
127 passed (122 FU4 baseline + 5 FU4-FU1 net-new); relevant
Vendor/FX/Compact Quote/replay set (23 files) 801 passed / 0 failed.
`python manage.py check`: System check identified no issues
(0 silenced). `python manage.py makemigrations --check --dry-run`:
No changes detected.

### PROD-FIX1-FU4 CANDIDATE ACCEPTANCE SNAPSHOT (PENDING FINAL REVIEW)

| Metric | Count |
| --- | --- |
| Collected | 5347 |
| Passed | 5336 |
| Failed | 11 (exactly the fixed allowlist; non-deterministic) |
| Unexpected failures | 0 |
| Skipped | 0 |
| Xfailed | 0 |
| Deselected | 0 |
| Subtests passed | 39 |

Full-suite execution of the final FU4 tree (zero deselection, no
skip/xfail injection; JUnit report): 5347 tests + 39 subtests
executed; 5336 passed, 11 failed — the 11 failures are EXACTLY the
members of the fixed eleven-node Windows/Python 3.14 subprocess-boundary
flake allowlist (every one failed in this run), each with the recorded
signature `subprocess.run -> Popen -> _winapi.DuplicateHandle ->
OSError: [WinError 6] The handle is invalid` (2) / `[WinError 50] The
request is not supported` (9), and NO node outside that allowlist
failed. The allowlist is non-deterministic by nature, exactly as
recorded for every prior phase; the fixed allowlist remains exactly
11 nodes (not expanded).

Collection accounting: 5326 FU3 baseline + 21 FU4 net-new nodes
= 5347 collected. Net-new: tests/providers/test_vendor_section_
response.py +15 (TestParagraphEntityDecoding: paragraph-path entity
decoding (historical record: FU4 implemented the `&quot;` / `&nbsp;`
/ `&cr;` mapping — the exact entity-literal defect corrected by
FU4-FU1, see the FU4-FU1 snapshot above and PLAN §26.15), plain-form
non-decoding, adversarial unapproved named/numeric/case-variant
entity non-decoding with fail-closed parsing, faithful production-
shaped full adapter mapping; TestSynnexAvailabilityTotalString: `"0"`
-> OOS/0, positive digit string -> IN_STOCK/qty, int/Decimal
readings unchanged, string grammar rejections, over-bounded length,
flat-form scope, global `_safe_int` still rejects strings),
tests/execution/test_4d_b_vendor_
section_integration.py +6 (TestVendorParagraphEntitySectionIntegration:
full execute_research_run on the encoded fixture, persisted-snapshot
sensitive-metadata + entity-spelling absence, Machine Price
immutability, armed zero-live Compact Quote replay rows, execution-time
4D-C FX currency discovery EUR + USD with persisted ResearchFxSnapshot,
supplemental-only vendor authority). No boundary parameterization
expansion (no new production files; only existing files modified).

All 5326 FU3 baseline nodes remain collected. No existing test
deleted, renamed, skipped, xfailed, deselected, or weakened. Exact
disclosed test-file touches (safety contracts preserved):

* `tests/providers/test_vendor_section_response.py` — module docstring
  notes the FU4 observed entity encoding and Synnex availability wire
  type; NEW fixture `SECTION_BODY_PARAGRAPH_ENTITY` (production-shaped
  encoded wire; fake sentinels only; deterministic synthetic values);
  NEW class `TestParagraphEntityDecoding` (7 nodes); NEW class
  `TestSynnexAvailabilityTotalString` (8 nodes); `_safe_int` added to
  the test-only private import list. No existing node altered.
* `tests/execution/test_4d_b_vendor_section_integration.py` — module
  docstring notes the FU4 encoded-wire proofs; NEW fixture
  `SECTION_BODY_PARAGRAPH_ENTITY` (same synthetic payload as
  `SECTION_BODY_PARAGRAPH` with the observed entity encoding plus the
  production-observed Synnex numeric-string price and digit-string
  availability); NEW class `TestVendorParagraphEntitySectionIntegration`
  (6 nodes). No existing node altered.

`python manage.py check`: System check identified no issues
(0 silenced). `python manage.py makemigrations --check --dry-run`:
No changes detected.

### PROD-FIX1-FU3 CANDIDATE ACCEPTANCE SNAPSHOT (PENDING FINAL REVIEW)

| Metric | Count |
| --- | --- |
| Collected | 5326 |
| Passed | 5324 |
| Failed | 2 (exactly fixed-allowlist members; non-deterministic) |
| Unexpected failures | 0 |
| Skipped | 0 |
| Xfailed | 0 |
| Deselected | 0 |
| Subtests passed | 39 |

Definitive full-suite execution of the final FU3 tree (zero
deselection, no skip/xfail injection; JUnit report): 5326 tests +
39 subtests executed; 5324 passed, 2 failed — both failures are
members of the fixed eleven-node Windows/Python 3.14
subprocess-boundary flake allowlist, each with the recorded signature
`subprocess.Popen -> OSError: [WinError 6] The handle is invalid`
(verified per-failure from the JUnit report), and NO node outside that
allowlist failed. An earlier full execution of the same tree in this
session observed 11 failures — again EXACTLY members of the fixed
allowlist (every one of the 11 nodes failed once in that run), all
other nodes green. The allowlist is non-deterministic by nature, exactly
as recorded for every prior phase; the fixed allowlist remains exactly
11 nodes (not expanded).

The 2 failed nodes in the definitive execution (both
fixed-allowlist members):

1. `tests/domain/test_domain_boundaries.py::test_domain_imports_without_django_network_or_llm_dependencies`
2. `tests/evaluation/test_evaluation_boundaries.py::test_loading_the_corpus_imports_no_framework_or_provider`

Collection accounting: 5298 FU2 baseline + 28 FU3 net-new nodes
= 5326 collected. Net-new: tests/providers/test_vendor_section_
response.py +22 (TestParagraphEnvelope: exact `<p>` label recognition
per source, leading-whitespace tolerance, the full adversarial HTML
boundary set, trailing `</p>` interstitial proof, malformed-in-literal
fail-closed, duplicate-label policy, mixed plain/paragraph forms,
oversized paragraph body), tests/execution/test_4d_b_vendor_section_
integration.py +6 (TestVendorParagraphSectionIntegration: full
execute_research_run paragraph integration, persisted-snapshot
sensitive-metadata absence, Machine Price immutability, armed zero-
live Compact Quote replay rows, execution-time 4D-C FX currency
discovery EUR + USD with persisted ResearchFxSnapshot, supplemental-
only vendor authority). No boundary parameterization expansion (no new
production files; only existing files modified).

All 5298 FU2 baseline nodes remain collected. No existing test
deleted, renamed, skipped, xfailed, deselected, or weakened. Exact
disclosed test-file touches (safety contracts preserved):

* `tests/providers/test_vendor_section_response.py` — module docstring
  notes the FU3 observed paragraph envelope; NEW class
  `TestParagraphEnvelope` (22 nodes) + NEW faithful single-line-per-
  section paragraph fixture `SECTION_BODY_HYBRID_PARAGRAPH` (fake
  sentinels only). No existing node altered.
* `tests/execution/test_4d_b_vendor_section_integration.py` — module
  docstring notes the FU3 paragraph proofs; NEW fixture
  `SECTION_BODY_PARAGRAPH` (same synthetic source payload as the FU1
  fixture, ONLY the outer `<p>` envelope added), NEW
  `_RecordingFxProvider` (test-only, records requested currency sets),
  NEW class `TestVendorParagraphSectionIntegration` (6 nodes).
  No existing node altered.

`python manage.py check`: System check identified no issues
(0 silenced). `python manage.py makemigrations --check --dry-run`:
No changes detected.

### PROD-FIX1-FU2 CANDIDATE ACCEPTANCE SNAPSHOT (PENDING FINAL REVIEW)

| Metric | Count |
| --- | --- |
| Collected | 5298 |
| Passed | 5296 |
| Failed | 2 (exactly the fixed allowlist; non-deterministic) |
| Unexpected failures | 0 |
| Skipped | 0 |
| Xfailed | 0 |
| Deselected | 0 |
| Subtests passed | 39 |

Definitive full-suite execution of the final FU2 tree (zero
deselection, no skip/xfail injection): 5296 passed, 2 failed — both
failures are members of the fixed eleven-node Windows/Python 3.14
subprocess-boundary flake allowlist, each with the recorded signature
`subprocess.Popen -> _winapi.DuplicateHandle/CreateProcess ->
OSError: [WinError 6/50]` (verified per-failure from the JUnit
report), and NO node outside that allowlist failed. Three earlier
full executions of the same tree in this session observed 11, 2, and
1 failures respectively — in every case EXACTLY members of the fixed
allowlist, all other nodes green. The allowlist is non-deterministic
by nature, exactly as recorded for every prior phase; the fixed
allowlist remains exactly 11 nodes (not expanded).

The 2 failed nodes in the definitive execution (both
fixed-allowlist members):

1. `tests/domain/test_domain_boundaries.py::test_domain_imports_without_django_network_or_llm_dependencies`
2. `tests/evaluation/test_evaluation_boundaries.py::test_loading_the_corpus_imports_no_framework_or_provider`

The full fixed allowlist (all observed failures across the session's
four full executions were subset members of this list, never outside
it):

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

All 11 are boundary/import-guard tests that spawn a subprocess to
prove isolated imports; the failure occurs at
`subprocess.Popen -> _winapi.DuplicateHandle` before any project code
runs. No FU2 production or test file is imported by any of them.

Collection accounting: 5281 FU1 baseline + 17 FU2 net-new nodes
= 5298 collected. Net-new: tests/execution/test_public_replay_persisted_
authority.py +15 (NEW FILE: same-request cross-run 1890/999 borrow
premise, per-run persisted-evidence isolation, no-caller-price-result
signature proof, corrupt/missing snapshot fail-closed, denied-boundary
preservation, authorized-replay-unchanged + Machine Price
byte-identity), tests/execution/test_compact_quote_public_replay.py
+2 (missing-snapshot and malformed-price-payload fail-closed). No
boundary parameterization expansion (no new production files; only
existing files modified).

All 5281 FU1 baseline nodes remain collected. No existing test
deleted, renamed, skipped, xfailed, deselected, or weakened. Exact
disclosed test-file touches (safety contracts preserved):

* `tests/execution/test_public_replay_persisted_authority.py` — NEW
  FILE (15 nodes) proving the FU2 blocker regression.
* `tests/execution/test_compact_quote_public_replay.py` — call sites
  updated to the FU2 signature (the persisted snapshot is now
  established as the run's artifact; the replay receives only the
  run). `test_provenance_mismatch_is_refused` now proves the same
  contract against a request-provenance-CORRUPT PERSISTED snapshot
  (stronger: the corruption lives in the artifact, not in a supplied
  object). `test_duck_typed_price_result_is_refused` now proves the
  stronger contract that NO parameter accepts any caller-supplied
  price result (signature + TypeError + persisted-snapshot-only
  authority). `test_wrong_run_type_is_programming_error` updated to
  the FU2 signature. Two new fail-closed nodes added (missing
  snapshot, malformed price payload). The module-boundary AST test's
  runs.models allowlist gains exactly `PriceIntelligenceSnapshot`
  (the intentional persisted-authority read); all other guards
  unchanged. No node renamed, deleted, or weakened.
* `tests/execution/test_human_confirmed_replay_authority.py` — three
  call sites drop the removed `price_result=` keyword argument
  (UNREVIEWED public replay, CONFIRMED public replay, armed
  zero-live public replay); every assertion preserved byte-for-byte
  (same expected rows / prices / zero-live behavior). No node renamed
  or deleted.
* `tests/web/test_compact_quote_report.py`, `tests/web/
  test_web_boundaries.py`, and all other web/execution tests —
  UNCHANGED (view-level denied-branch tests already persist the run's
  PriceIntelligenceSnapshot; the authorized branch is untouched).

`python manage.py check`: System check identified no issues
(0 silenced). `python manage.py makemigrations --check --dry-run`:
No changes detected.

### PROD-FIX1-FU1 CANDIDATE ACCEPTANCE SNAPSHOT (PENDING FINAL REVIEW)

| Metric | Count |
| --- | --- |
| Collected | 5281 |
| Passed | 5281 |
| Failed | 0 |
| Skipped | 0 |
| Xfailed | 0 |
| Deselected | 0 |
| Subtests passed | 39 |

Definitive full-suite execution of the final FU1 tree (zero
deselection, no skip/xfail injection): 5281 passed, 0 failed,
39 subtests passed. During validation, two earlier full executions
of the same tree observed 10 and 11 failures respectively — in both
cases EXACTLY members of the fixed eleven-node Windows/Python 3.14
subprocess-boundary flake allowlist (observed signature
`subprocess.Popen -> _winapi.DuplicateHandle/CreateProcess ->
OSError: [WinError 6/50]`), with NO node outside that allowlist
failing and all three executions otherwise green. The allowlist is
non-deterministic by nature, exactly as recorded for every prior
phase; the fixed allowlist remains exactly 11 nodes (not expanded).

Collection accounting: 5247 PROD-FIX1 baseline + 34 FU1 net-new nodes
= 5281 collected. Net-new: tests/providers/test_vendor_section_response.py
+15 (12 hybrid production-placement adapter tests incl. the full
adapter-level unknown-label/interstitial-between-known-sections proof;
3 section-value interstitial/strictness parser tests),
tests/execution/test_human_confirmed_replay_authority.py +17 (NEW FILE:
replay/service boundary authority proofs A–G plus injection-surface
removal and Machine Price / no-persisted-price proofs),
tests/web/test_human_confirmed_compact_quote.py +2 (focused Reviewed
Price wording regressions). No boundary parameterization expansion (no
new production files; only existing files modified).

All 5247 baseline nodes remain collected. No existing test deleted,
skipped, xfailed, deselected, or weakened. Exact disclosed test-file
touches:

* `tests/providers/test_vendor_section_response.py` — module docstring
  and fixture comments corrected (flat forms described as separately
  tested COMPATIBILITY forms, not the only/exact production wire
  shape); `test_trailing_garbage_rejected` INPUT corrected from
  `{'a': 1} trailing junk` (a complete literal + interstitial text, now
  correctly ignored per the documented contract) to
  `{'a': 1 trailing junk` (an INCOMPLETE literal — still rejected;
  name and fail-closed intent preserved, strictness retained);
  new hybrid/interstitial tests added.
* `tests/execution/test_4d_b_vendor_section_integration.py` — the
  SECTION_BODY fixture corrected from the simplified flat
  "production-equivalent" shape to the faithful hybrid production shape
  (Ingram: nested pricing + top-level boolean availability + top-level
  Avl_Quantity + unrelated ignored fields; Synnex EU: REAL nested
  OnlineCheck form with fake/redacted SessionId / BuyerAccountId /
  SystemId in the Header block). All seven assertions of the seven
  existing tests are preserved and now run against the faithful shape.
* `tests/web/test_web_boundaries.py` — the web research-import
  allowlist gains exactly one symbol:
  `research.matching.is_review_candidate_binding_valid` (the single
  shared binding primitive now consumed by web/presentation.py).
  Guard strength unchanged (still an explicit symbol-level allowlist).
* `tests/providers/test_fx_tls_verification.py` — docstring-only
  evidence correction (BLOCKER 3): no longer records an outstanding
  CA-trust-store installation as fact (a later secure retry from the
  same production runtime succeeded; the transient root cause is
  unproven). Every assertion byte-identical.
* `tests/web/test_human_confirmed_compact_quote.py` — two focused
  wording regression tests ADDED (no existing test altered).
* `tests/execution/test_human_confirmed_replay_authority.py` — NEW FILE
  (17 nodes).

### PROD-FIX1 CANDIDATE ACCEPTANCE SNAPSHOT (PENDING FINAL REVIEW)

| Metric | Count |
| --- | --- |
| Collected | 5247 |
| Passed | 5247 |
| Failed | 0 |
| Skipped | 0 |
| Xfailed | 0 |
| Deselected | 0 |
| Subtests passed | 39 |

Collection accounting: frozen 4D-D baseline 5097 + 150 new PROD-FIX1
nodes (test_vendor_section_response.py 70, test_compact_quote_human_
confirmed.py 21, test_compact_quote_currency_formatting.py 16,
test_human_confirmed_compact_quote.py 15, test_research_submit_guard.py
10, test_fx_tls_verification.py 9, test_4d_b_vendor_section_integration.
py 7, test_fx_tls_production_chain.py 2). No boundary parameterization
expansion (no new production files; only existing files modified). No
existing test deleted, renamed, skipped, xfailed, deselected, or
weakened.

### 4D-D FINAL ACCEPTANCE SNAPSHOT (IMPLEMENTED / APPROVED / FROZEN)

| Metric | Count |
| --- | --- |
| Collected | 5097 |
| Passed | 5097 |
| Failed | 0 |
| Skipped | 0 |
| Xfailed | 0 |
| Deselected | 0 |
| Subtests passed | 39 |

Frozen SHA: 065320180c17b89c7460164326a0c9f49e01fe3b. With this
acceptance, PRODUCT-INTEL.4D (all components) is closed as
IMPLEMENTED / APPROVED / FROZEN / COMPLETE. The 5052-collection
candidate-pass evidence recorded in the 4D-D section above is preserved
as history.

### HISTORICAL FU3A2F FREEZE SNAPSHOT

| Metric | Count |
| --- | --- |
| Collected | 2158 |
| Passed | 2151 |
| Failed | 7 |
| (+ 39 subtests) | — |

### HISTORICAL FU3B FINAL REVIEW SNAPSHOT

| Metric | Count |
| --- | --- |
| Collected | 2212 |
| Passed | 2206 |
| Failed | 6 |

The six failures were exactly:

- `tests/evaluation/test_evaluation_boundaries.py::test_loading_the_corpus_imports_no_framework_or_provider`
- `tests/providers/test_provider_boundaries.py::test_importing_the_provider_boundary_pulls_in_no_third_party_dependency`
- `tests/providers/test_provider_boundaries.py::test_importing_the_page_boundary_pulls_in_no_third_party_dependency`
- `tests/research/test_listing_normalization_boundaries.py::test_importing_the_research_core_still_pulls_in_no_third_party_dependency`
- `tests/research/test_research_identity_boundaries.py::test_importing_the_research_core_pulls_in_no_third_party_dependency`
- `tests/runs/test_research_run_boundaries.py::test_the_domain_still_imports_without_django_present`

### 6B IMPLEMENTATION SNAPSHOT (APPROVED / RE-FROZEN)

| Metric | Count |
| --- | --- |
| Collected | 2782 |
| Passed | 2772 |
| Failed | 10 |
| Unexpected failures | 0 |

Evidence-backed corrective change (project-lead approved, re-frozen):
- Real Seagate Nytro 5050 manufacturer evidence demonstrated "2.5in"
  as an exact formatting equivalent of the existing 2.5-inch canonical form.
- Added: "2.5in" -> "2.5-inch" to _FORM_FACTOR_MAP.
- No schema version bump (field meaning, canonical value, enum unchanged).
- Regression test added: test_2_5_in_no_space.

The ten failures are the fixed approved Windows / Python 3.14
subprocess-boundary flake allowlist (all boundary/import-guard tests):

1. `tests/domain/test_domain_boundaries.py::test_domain_imports_without_django_network_or_llm_dependencies`
2. `tests/evaluation/test_evaluation_boundaries.py::test_loading_the_corpus_imports_no_framework_or_provider`
3. `tests/providers/test_provider_boundaries.py::test_importing_the_provider_boundary_pulls_in_no_third_party_dependency`
4. `tests/providers/test_provider_boundaries.py::test_importing_the_page_boundary_pulls_in_no_third_party_dependency`
5. `tests/research/test_enterprise_ssd_boundaries.py::test_importing_enterprise_ssd_pulls_in_no_third_party`
6. `tests/research/test_enterprise_ssd_boundaries.py::test_importing_enterprise_ssd_does_not_load_django`
7. `tests/research/test_listing_normalization_boundaries.py::test_importing_the_research_core_still_pulls_in_no_third_party_dependency`
8. `tests/research/test_research_identity_boundaries.py::test_importing_the_research_core_pulls_in_no_third_party_dependency`
9. `tests/research/test_specification_boundaries.py::test_importing_specifications_pulls_in_no_third_party_dependency`
10. `tests/runs/test_research_run_boundaries.py::test_the_domain_still_imports_without_django_present`

Observed failure signature (all 10 nodes):

    subprocess.Popen
    -> _winapi.DuplicateHandle
    -> OSError: [WinError 6] The handle is invalid

    or

    subprocess.Popen
    -> _winapi.CreateProcess
    -> OSError: [WinError 50] The request is not supported

These are environment-specific subprocess-boundary limitations on this Windows /
Python 3.14 workstation, not application defects. No node outside the fixed
ten-node allowlist fails. No test is skipped, xfailed, or weakened.

### 7A IMPLEMENTATION SNAPSHOT (APPROVED / FROZEN)

| Metric | Count |
| --- | --- |
| Collected | 3006 |
| Passed | 2996 |
| Failed | 10 (fixed approved allowlist only, non-deterministic) |
| Unexpected failures | 0 |

The ten failures are the fixed approved Windows / Python 3.14
subprocess-boundary flake allowlist (identical to 6C baseline).

7A implementation (contract-corrected pass):
- New production modules:
  - `research/comparable_candidates.py` (candidate contracts)
  - `research/enterprise_ssd_candidate_extraction.py` (pure extraction)
  - `execution/comparable_discovery.py` (execution + result audit)
- New test modules:
  - `tests/research/test_enterprise_ssd_candidate_extraction.py` (21 tests)
  - `tests/research/test_comparable_candidates.py` (38 tests)
  - `tests/execution/test_comparable_discovery.py` (27 tests)
- Total new tests: 86 (+ 16 boundary test nodes for new production files)
- Collection delta: 2904 -> 3006 (+102)
- Real Seagate fixture: 81 observations, 1 TARGET_SELF, 80 candidates
- No frozen file modifications
- No pre-7A test deletions
- Research boundary clean (no provider imports in research/)

Contract corrections applied in review-closure pass:
- Raw MPN (`manufacturer_part_number_raw`) preserved verbatim (not stripped)
- Raw title (`product_name_raw`) preserved verbatim (not stripped/blank-to-None)
- Bounded JS string decoder (no `.encode().decode("unicode_escape")` corruption)
- `ComparableCandidateAssessment` stores `target_identity: ProductIdentity` by exact type (`type(x) is ProductIdentity` — subclasses rejected)
- `__post_init__` re-derives disposition from target + observation
- `ComparableCandidate` requires all evidence to bind to the exact same `target_identity` object (cross-target evidence rejected)
- `deduplicate_candidate_assessments` rejects same-key assessments from different target identities
- `ComparableCandidateDiscoveryResult` enforces exact `assessment.observation is obs`
- `ComparableCandidateDiscoveryResult` enforces exact `assessment.target_identity is result.target_identity`
- `ComparableCandidateDiscoveryResult` enforces AUTHORITATIVE-only result invariant
- `ComparableCandidateDiscoveryResult` rejects foreign assessments in candidate evidence
- Real E2E crosses frozen 6C -> 7A (not synthetic all-UNKNOWN spec set)
- All bare-pass tests replaced with real adversarial coverage
- No skip/xfail/deselect/bare-pass in any 7A test

### 7B IMPLEMENTATION SNAPSHOT (IMPLEMENTED / APPROVED / FROZEN)

**Frozen 7A baseline:** 3006 collected.

| Metric | Count |
| --- | --- |
| Total collected | 3102 |
| Passed | 3092 |
| Failed | 10 (fixed approved allowlist only, non-deterministic) |
| Unexpected failures | 0 |
| Skipped | 0 |
| Xfailed | 0 |
| Deselected | 0 |

The ten failures are the fixed approved Windows / Python 3.14
subprocess-boundary flake allowlist (all boundary/import-guard tests).

**Collection accounting:**

| Component | Nodes |
| --- | --- |
| Frozen 7A baseline | 3006 |
| 7B research tests (`test_enterprise_ssd_similarity.py`) | 54 |
| 7B execution tests (`test_comparable_similarity.py`) | 34 |
| Boundary guard nodes | 8 |
| **Total** | **3102** |

7B implementation:
- New production modules:
  - `research/enterprise_ssd_similarity.py` (pure similarity scoring)
  - `execution/comparable_similarity.py` (execution + batch result)
- New test modules:
  - `tests/research/test_enterprise_ssd_similarity.py` (54 tests)
  - `tests/execution/test_comparable_similarity.py` (34 tests)
- Total new 7B tests: 88
- Collection delta: 3006 -> 3102 (+96)
- One modified test: `tests/research/test_listing_normalization_boundaries.py`
  (Decimal allowlist addition for new module)
- Real Seagate fixture: 81 observations -> 80 candidates -> 80 similarities
- Real Seagate vertical slice: frozen 6C -> frozen 7A -> 7B
- Known sibling XP15360SE70015 scored: 1 scoreable field (Form Factor)
- All 80 candidates have evidence_coverage = 1/12
- Real Form Factor exact match: field_similarity = 1
- Fetch count: 1 (one fetch per source, not 80)
- No frozen file modifications
- No pre-7B test deletions
- Research boundary clean (no provider imports in research/)
- 7B boundary: no SearchProvider, no LLM, no title parsing, no Interface splitting

Contract corrections (7B corrective implementation):
- SpecificationSimilarityFieldAssessment recomputes actual field similarity
  from raw resolutions; rejects wrong-but-in-range supplied score
- EnterpriseSsdSimilarityResult moved from research to execution layer
- Exact ComparableCandidateDiscoveryResult type enforced (no duck typing,
  TypeError BEFORE any fetch)
- Source outcomes retained in result (not discarded)
- 7B ComparableSimilaritySourceOutcome uses exact 7A ComparableCandidateSource
  descriptor object (not flattened source_name/source_url/source_authority)
- final_url structurally validated by require_fetchable_url()
- Candidate spec provenance audit: every observation traced to a FETCHED
  7B source outcome (product_identity, source_name, source_authority,
  source_url==final_url, retrieved_at all verified)
- ComparableCandidateSpecificationProfile enforces exact bridge output
  (rejects enriched identity with injected metadata)
- Exact scalar types enforced (bool/int/float substitutes rejected)
- Non-authoritative bridge test uses TEST-ONLY object.__setattr__ tampering
- 7A source binding: EnterpriseSsdSimilarityResult.__post_init__ derives
  canonical EXTRACTED source descriptors from the frozen 7A result and
  enforces exact object identity for every 7B source outcome. Copied/
  value-equal substitutes are rejected. Missing or extra outcomes rejected.

Key design decisions:
- VERIFIED-only scoring (UNKNOWN/UNVERIFIED/CONFLICT are NOT mismatches)
- 12-field equal weight (no domain-business weights in 7B v1)
- DECIMAL: min(target, candidate) / max(target, candidate)
- TEXT/ENUM/BOOLEAN: exact canonical equality (1 or 0)
- evidence_coverage = scored_field_count / 12
- observed_similarity = mean of scored field similarities
- evidence_weighted_similarity = sum of scored similarities / 12
- Self-validating EnterpriseSsdCandidateSimilarity (re-derives all fields,
  exact scalar types)
- Self-validating EnterpriseSsdSimilarityResult (execution-owned, exact
  discovery_result type, retained source outcomes, 7A source binding,
  provenance audit)
- Field score self-validation (SpecificationSimilarityFieldAssessment
  recomputes and rejects wrong supplied score)
- Candidate ProductIdentity bridge: EXACT, no manufacturer guessed,
  rejects non-AUTHORITATIVE evidence
- One-fetch-per-source execution (document held, extraction per identity)
- 7B source descriptor identity binding (exact 7A ComparableCandidateSource
  object reused in 7B outcome, enforced at result construction)
- No duck typing for ComparableCandidateDiscoveryResult
- No provenance string mutation (no .strip() on source_name/source_url)
- PageFetcher remains a structural protocol check (hasattr(page_fetcher, "fetch"));
  this is a protocol verification, not discovery-result authority

Evidence sparsity conclusion:
- Current candidate specification evidence is too sparse for useful
  differentiation (only 1 of 12 fields scoreable per candidate)
- This is a limitation of frozen 6C extraction capability (only
  "Form Factor" label mapped), not a 7B failure
- Candidate specification enrichment required before useful 7C presentation

No skip/xfail/deselect/bare-pass in any 7B test


### 6C IMPLEMENTATION SNAPSHOT (APPROVED / FROZEN)

| Metric | Count |
| --- | --- |
| Collected | 2904 |
| Passed | 2894 |
| Failed | 10 (fixed approved allowlist only, non-deterministic) |
| Unexpected failures | 0 |

The ten failures are the fixed approved Windows / Python 3.14
subprocess-boundary flake allowlist (identical to 6B baseline).

Corrective pass (final evidence-backed closure):
- Speculative extraction mechanisms removed:
  - JSON-LD Product additionalProperty/PropertyValue pairs (no real evidence)
  - HTML specification tables (no real evidence)
  - HTML definition lists (dt/dd pairs) (no real evidence)
- Embedded JavaScript JSON product data extraction implemented:
  - Structural anchor: var supportSpecsData = JSON.parse('...') (exact variable name)
  - Real evidence: Seagate Nytro 5050 support page (XP15360SE70005)
  - Array of 81 product records with skuNumber + features[]
  - Exact MPN match selection, no cross-record leak
  - Label mapping: "Form Factor" -> physical_form_factor (only proven label)
- Provenance trace: multiplicity-aware (each EXTRACTED outcome contributes
  capacity equal to observation_count)
- Raw value exact preservation (extractor does not strip/clean)
- final_url validated through require_fetchable_url contract
- Duplicate requested_url removed from SpecificationSourceOutcome
  (requested URL is always source.source_url)
- Real Seagate fixture: VERIFIED (raw "2.5in" -> canonical "2.5-inch" -> VERIFIED)
- Samsung PM9A3: still NO_OBSERVATIONS (spec table JS-rendered)
- No LLM implemented
- No persistence/web

## Next delivery priority

**8A (Caching & Freshness) series — current position:**

* **8A-PRE**: APPROVED / COMPLETE — Caching & Freshness Architecture
  Audit (read-only / design-first; delivered as scoped; no TTL values
  approved there; record committed as
  `docs/PRODUCT_INTEL_8A_PRE_CACHING_FRESHNESS_AUDIT.md`). It was chosen
  because Product Intelligence is in production and evidence classes
  have materially different freshness requirements: the design must
  prevent stale evidence from being presented as current while avoiding
  unnecessary paid/live calls. The design distinguished at minimum:
  market/public prices (short freshness); Vendor commercial observations
  (short freshness); ECB FX rates (tied to persisted official
  observation date); product specifications (longer freshness);
  comparable research (medium freshness); deterministic identity/
  authority evidence (not automatically equivalent to market-price
  freshness); user/operator forced refresh; historical reports
  (immutable replay, NEVER refreshed merely by GET).
* **8A-FX-DESIGN / 8A-FX-DESIGN-FU1**: APPROVED / FROZEN as design — the
  reviewed design lineage for the first caching slice (pre-fetch feed-
  identity lookup, post-fetch content identity, closure-window
  freshness over proof instants, canonical-default eligibility,
  fail-closed cache integrity).
* **8A-FX-A1 (Canonical ECB Observation Cache)**: IMPLEMENTED / PENDING
  FINAL REVIEW — the first safe caching slice (cross-run reuse of the
  canonical production ECB daily FX observation set; acquisition-only;
  FX remains DISPLAY-SUPPLEMENTAL). See Current state (top of document).
* **After 8A-FX-A1 approval**: next delivery undecided (directional
  candidates only — none approved as NEXT): 5A (Structured external API
  — PLANNED / NON-BLOCKING), 8B (Research history — PLANNED), 8C
  (Production hardening — PLANNED). Authentication/session remains
  outside the current priority.

**PILOT-RELEASE-2**: DEPLOYED / ACCEPTED — 4D Customer Requirement
Deployment & UAT. The already-frozen 4D customer requirements are
deployed to the internal production/pilot Windows server; the recorded
representative 4D production smoke validation covered a normal customer
quote flow exercising current Price Intelligence / Compact Quote
behavior and Micron 7500 R/T packaging-alias behavior. The previously
planned broader UAT matrix (direct-source acquisition using a viable
preferred-source case; normal Serper fallback; real Vendor API
commercial evidence; compact quote rendering; non-USD vendor evidence +
persisted ECB USD equivalent; Micron 7500 packaging-alias BASE/R/T
behavior; a non-eligible MPN proving alias abstention; Visual FoxPro
launcher -> browser prefill against the deployed server; historical
report reload causing zero new Search/Vendor/ECB/Micron/Semantic live
work; vendor-price access behavior under the existing frozen network
gate (4D-C-SEC REMOTE_ADDR / PI_VENDOR_PRICE_ALLOWED_CIDRS, unchanged))
remains a validation reference; the production records do not claim
that every matrix case was separately executed and evidenced during
the 2026-09-23 cutover.
Deployment record: deployed runtime SHA
065320180c17b89c7460164326a0c9f49e01fe3b (the independently reviewed
and frozen PRODUCT-INTEL.4D-D-FU1 runtime SHA; deployment is
Git-managed and exact-approved-SHA based); production smoke test
passed 2026-09-23; 4D is deployed; migrations through
0010_research_micron_alias_snapshot are deployed (4D migrations
0008 / 0009 / 0010). Production environment details are recorded in
the operational Confluence references and are not duplicated here.
Runtime-vs-docs: the later commits c6ad6ae and 7ff0ab7 are docs-only
project-state closures; production does not need to move merely to
obtain those documentation edits; 7ff0ab7 is not the production
runtime SHA. Authentication: the current pilot server
has restricted access and people who can reach this internal server are
currently considered authorized for this pilot; full application
authentication, login/session identity, OAuth, and per-user authorization
are NOT part of PILOT-RELEASE-2 and remain deferred future
production-hardening concerns (8C); report UUID is not access control; no
session-based authorization is introduced.

**PILOT-RELEASE-1**: DEPLOYED / ACCEPTED

**4D-PRE**: APPROVED / FROZEN (evidence only) — Preferred Source
         Feasibility Audit;
         audit 12 customer preferred sites;
         record per-site: direct lookup mechanism, static HTML capability,
         JS requirements, blocking behavior, MPN/price/currency evidence;
         recommendation: DIRECT / SERPER_FALLBACK / UNSUITABLE;
         no production code changes;
         evidence recorded in docs/PILOT_SOURCE_FEASIBILITY.md

**4D**: IMPLEMENTED / APPROVED / FROZEN / COMPLETE — Customer Quote
       Research Expansion;
       4D-PRE (feasibility audit) -> 4D-A (source optimization) ->
       4D-B (vendor commercial evidence) -> 4D-C (compact quote + FX) ->
       4D-D (Micron packaging alias, APPROVED / FROZEN including
       4D-D-FU1, frozen SHA 065320180c17b89c7460164326a0c9f49e01fe3b,
       frozen baseline 5097 collected, final acceptance 5097 passed /
       0 failed, v1 scope Micron 7500 SSD only);
       no frozen phase reopened; no frozen boundary weakened;
       4D-B triggered the §19 security gate, resolved by the frozen
       4D-C-SEC REMOTE_ADDR-only network gate;
       full application authentication remains a deferred 8C
       production-hardening concern; the current restricted internal
       pilot deployment assumes reachability = authorized for this pilot

**HUMAN-REVIEW**: IMPLEMENTED / APPROVED / FROZEN

**5A**: PLANNED / NOT IMPLEMENTED / non-blocking (not needed for the
current FoxPro/browser workflow; not the next delivery)

**5B**: Server-side implemented; client integrated outside repo; localhost UAT passed

**6A**: IMPLEMENTED / APPROVED / FROZEN —
         Product Specification Framework (framework only, no extraction)
         Corrective pass: evidence-derived constructor enforcement,
         deep immutability (MappingProxyType), schema/definition key
         consistency.

**6B**: IMPLEMENTED / APPROVED / RE-FROZEN —
         First Category-Specific Specification Schema;
         Enterprise SSD finalized; 12-field schema v1;
         strict deterministic normalization with exact-definition identity
         enforcement, strict thousands-grouping grammar, explicit IOPS unit;
         evidence-backed correction: "2.5in" -> "2.5-inch" (re-frozen);
         no extraction; no resolution; no authority inference

**6C**: IMPLEMENTED / APPROVED / FROZEN —
         Specification Evidence Extraction & Resolution;
         explicit approved-source descriptors (source_url validated at construction);
         existing PageFetcher acquisition (protocol imported, not duplicated);
         deterministic structured extraction (var supportSpecsData = JSON.parse('...'));
         structural assignment binding (only the JSON.parse directly assigned
         to supportSpecsData is extracted);
         source authority supplied explicitly, never hostname-inferred;
         frozen 6B normalization (with evidence-backed "2.5in" correction);
         frozen 6A resolution;
         complete ProductSpecificationSet with explicit UNKNOWN;
         source outcomes preserve complete source descriptor + self-consistency;
         requested_url removed (always source.source_url);
         provenance trace enforcement (multiplicity-aware);
         final_url validation through require_fetchable_url;
         raw value exact preservation (no stripping by extractor);
         no LLM implemented;
         no persistence/web;
         real manufacturer fixture: Seagate Nytro 5050 (XP15360SE70005)
         - embedded JSON data extraction works (1 observation);
         - Form Factor raw value "2.5in" extracted correctly;
         - frozen 6B normalization: "2.5in" -> "2.5-inch" -> VERIFIED;
         Samsung PM9A3: still NO_OBSERVATIONS (JS-rendered spec table);
         7A follows 6C

**7A**: IMPLEMENTED / APPROVED / FROZEN —
        Comparable-Product Candidate Discovery;
        evidence-backed candidate discovery from approved manufacturer catalog sources;
        explicit AUTHORITATIVE source required (SECONDARY rejected);
        no SearchProvider, no LLM, no spec filtering, no scoring/ranking;
        var supportSpecsData = JSON.parse('...') is first real mechanism;
        raw candidate evidence preserved (ComparableCandidateObservation);
        target-self exclusion uses frozen 2A compare_part_numbers();
        normalized-exact candidate dedup uses frozen 2A normalize_part_number();
        ProductIdentity NOT reused for discovered candidates;
        self-auditing ComparableCandidateDiscoveryResult;
        real Seagate vertical slice: 81 records -> 81 observations -> 1 TARGET_SELF -> 80 candidates;
        no persistence/web;

**7B**: IMPLEMENTED / APPROVED / FROZEN —
        Enterprise SSD Similarity Scoring;
        deterministic field-level similarity evidence;
        VERIFIED-only scoring (UNKNOWN/UNVERIFIED/CONFLICT never mismatch);
        candidate ProductIdentity bridge (EXACT, no manufacturer guess);
        12-field equal-weight (no business weights);
        DECIMAL min/max ratio, TEXT/ENUM/BOOLEAN exact equality;
        evidence_coverage = scored/12, evidence_weighted = sum/12;
        one-fetch-per-source execution (not one-fetch-per-candidate);
        frozen 6C extraction reuse per candidate identity;
        real Seagate fixture: 80 candidates, 1 scoreable field each (Form Factor);
        evidence too sparse for useful differentiation (candidate spec enrichment needed);
        6D completed the candidate-specification enrichment identified after the
7B freeze. 7C is IMPLEMENTED / APPROVED / FROZEN. 4D is
IMPLEMENTED / APPROVED / FROZEN / COMPLETE; PILOT-RELEASE-2 is
DEPLOYED / ACCEPTED; 8A-PRE subsequently COMPLETED (APPROVED), and the
8A series advanced through the approved design lineage to 8A-FX-A1
(IMPLEMENTED / PENDING FINAL REVIEW).

**7C-A**: COMPARABLE RESEARCH RESULTS + CODEC — IMPLEMENTED / APPROVED / FROZEN

**7C-B**: COMPARABLE RESEARCH ORCHESTRATION — IMPLEMENTED / APPROVED / FROZEN
        Frozen primitives composed into one bounded execution pipeline:
        claim ComparableResearchExecution
            -> exact parent ResearchRun request
            -> PRE1 authority acquisition
            -> target frozen 6C specification extraction
            -> frozen 7A candidate discovery
            -> candidate ProductIdentity bridge (frozen 7B)
            -> candidate 6C from HELD authoritative support documents
            -> ONE frozen 6D batch enrichment (target + candidates)
            -> frozen 6C + 6D composition
            -> pure frozen 7B similarity scoring
            -> pure ComparableResearchResult projection
            -> frozen V1 comparable codec
            -> atomic ComparableResearchExecution completion
        Exact bounded failure handling (PRE1 incomplete, codec errors,
        programming exceptions); no web/presentation routes; zero
        modifications to frozen contracts;
        real Seagate fixture vertical slice: 80 candidates, 7 scoreable
        fields per candidate (Form Factor + 6 Datasheet fields),
        evidence layers SUPPORT_PAGE/DATASHEET_PDF classified by
        object-identity pools, codec V1 round-trip verified;

**7C-C**: COMPARABLE WEB TRIGGER & PRESENTATION — IMPLEMENTED / APPROVED / FROZEN
        Web trigger route POST /research/<uuid>/comparables (research-comparables);
        default-provider adapter execute_comparable_research_with_default_providers();
        pure presentation module comparable_presentation.py (DISPLAY ONLY);
        comparable section AFTER existing review content in template;
        child selection: active (PENDING/RUNNING) > COMPLETED > FAILED (deterministic);
        result decode via frozen V1 codec + parent binding via frozen 2A comparison
        (binding validation in views._validate_comparable_result_parent_binding(),
        NOT in display-only comparable_presentation);
        candidate order exactly preserved (no ranking/sorting); ALL retained;
        Decimal values string-exact; labels/units from ENTERPRISE_SSD_SCHEMA;
        UNVERIFIED values visibly marked "Unverified — <value>";
        VERIFIED/CONFLICT/UNKNOWN resolution states branch correctly;
        complete AuthorityAttemptDisplay provenance (policy_id, outcome,
        requested_source_url, fetched_final_url, retrieved_at, matching_mpn);
        complete DatasheetAttemptDisplay provenance (outcome, source_name,
        source_url, final_url, retrieved_at, observation_count);
        complete EvidenceSourceReference provenance (source_name, source_url,
        evidence_layer, source_authority, retrieved_at);
        URL safety: reuses authoritative presentation._is_safe_href_url
        (no duplication in comparable_presentation);
        unsafe URLs: escaped text with no href;
        GET research_detail read-only: no trigger/executor/provider calls;
        CSRF: POST enforced with Django CSRF middleware;
        boundary tests updated for new research/execution/runs imports;
        boundary: comparable_presentation imports no runs/execution/providers/Django;
        views.py may import only compare_part_numbers (narrow 7C-C exception);
        new test count: 38 (7 runtime + 29 presentation + 39 report + 6 boundary = 81
        total test nodes in FU scope; 38 net new after accounting for strengthened
        existing nodes and removed duplicates);
        collection delta: 3812 -> 3850 (+38);

**6D**: IMPLEMENTED / APPROVED / FROZEN —
        Authoritative Datasheet Specification Enrichment;
        added AFTER 7B freeze because frozen 7B revealed only 1/12
        candidate evidence coverage;
        provider-neutral document/PDF boundary;
        concrete HttpPdfFetcher (stdlib urllib, bounded, no browser);
        pure research table interpretation (no PDF parser dependency);
        MPN -> table -> column -> row binding;
        six-field allowlist: capacity, sequential_read, sequential_write,
        random_read_iops, random_write_iops, endurance_dwpd;
        unit incorporation from structural row header when cell lacks unit;
        frozen 6B normalization (no modification required);
        frozen 6A resolution (VERIFIED for AUTHORITATIVE evidence);
        complete ProductSpecificationSet with explicit UNKNOWN;
        self-auditing SpecificationEnrichmentResult;
        one-fetch-per-datasheet deduplication;
        compose_6c_6d_specifications: merges 6C + 6D normalized evidence,
        re-resolves via frozen 6A (does NOT copy resolved values);
        physical_form_factor preserved VERIFIED from frozen 6C;
        candidate composition: scored_field_count=7, evidence_coverage=7/12;
        runtime dependency: pdfplumber>=0.11.0 (execution layer only);
        pdfplumber for PDF table extraction (execution layer only);
        real Seagate PDF fixture: Nytro 5550/5350 datasheet (8 pages);
        no LLM, no semantic model, no title parsing, no Interface splitting

### 6D IMPLEMENTATION SNAPSHOT (IMPLEMENTED / APPROVED / FROZEN)

**Frozen 7B baseline:** 3102 collected.

Total collected | 3353
Passed          | 3352
Failed          | 1
Unexpected failures | 0
Skipped         | 0
Xfailed         | 0
Deselected      | 0
Subtests passed | 39
Warnings        | 2

The single observed failure was:
tests/evaluation/test_evaluation_boundaries.py::test_loading_the_corpus_imports_no_framework_or_provider

It is a member of the fixed approved 11-node Windows/Python 3.14
subprocess-boundary flake allowlist. No node outside that allowlist failed.

**Allowlist expansion evidence (node 11):**
- `tests/providers/test_provider_boundaries.py::test_http_pdf_imports_no_third_party_dependency`
- Exact pytest failure: `subprocess.Popen -> _winapi.DuplicateHandle -> OSError: [WinError 6] The handle is invalid`
- Direct CMD semantic check: `[]` (stdlib urllib only, no third-party dependency)
- Project-lead approval: accepted as the 11th fixed environment-flake node

**Collection accounting (6D corrective closure):**

| Component | Nodes |
| --- | --- |
| Frozen 7B baseline | 3102 |
| 6D datasheet link extractor tests (`test_datasheet_link_extractor.py`) | 19 |
| 6D provider document tests (`test_document_provider.py`) | 29 |
| 6D HTTP PDF tests (`test_http_pdf.py`) | 20 |
| 6D research datasheet tests (`test_enterprise_ssd_datasheet.py`) | 70 |
| 6D execution enrichment tests (`test_specification_enrichment.py`) | 68 |
| 6D boundary guard tests (`test_specification_enrichment_boundaries.py`) | 17 |
| 6D provider boundary additions (`test_provider_boundaries.py`) | 4 |
| Boundary guard nodes from existing tests (parameterization expansion) | 24 |
| **Total** | **3353** |

Collection delta: 3102 -> 3353 (+251)

**Parameterization expansion derivation (24 nodes from existing tests):**

All 24 boundary guard nodes from existing tests are derived from actual parameterized
test expansion when new 6D production modules are added to directory-scanned sets:

- `test_provider_boundaries.py`:
  - 5 parametrize × GENERIC_BOUNDARY_MODULES: +1 each (document.py added) = +5
  - 1 parametrize × _python_files(PROVIDERS_ROOT): +2 (document.py, http_pdf.py) = +2
  - 1 parametrize × INNER_ROOTS: +2 (enterprise_ssd_datasheet.py, datasheet_link_extractor.py in research/) = +2
  - 1 parametrize × ADAPTER_MODULES: +1 (http_pdf.py) = +1
  Subtotal: +10

- `test_research_identity_boundaries.py`:
  - 4 parametrize × _python_files(RESEARCH_ROOT): +2 each = +8
  Subtotal: +8

- `test_research_run_boundaries.py`:
  - 1 parametrize × (_python_files(DOMAIN_ROOT) + _python_files(RESEARCH_ROOT)): +2 = +2
  Subtotal: +2

- `test_web_boundaries.py`:
  - 1 parametrize × INNER_ROOTS: +2 = +2
  Subtotal: +2

- `test_domain_boundaries.py`:
  - 1 parametrize × (_python_files(DOMAIN_ROOT) + _python_files(RESEARCH_ROOT)): +2 = +2
  Subtotal: +2

Grand total parameterization expansion: 10 + 8 + 2 + 2 + 2 = 24

6D production modules:
- `product_intelligence/providers/document.py` (provider-neutral boundary)
- `product_intelligence/providers/http_pdf.py` (concrete PDF fetcher)
- `product_intelligence/research/datasheet_link_extractor.py` (support-record datasheet-link extraction)
- `product_intelligence/research/enterprise_ssd_datasheet.py` (pure table interpretation)
- `product_intelligence/execution/specification_enrichment.py` (execution + result + composition + authority chain + batch)

6D test modules:
- `tests/research/test_datasheet_link_extractor.py` (19 tests) — real fixture
- `tests/providers/test_document_provider.py` (29 tests)
- `tests/providers/test_http_pdf.py` (20 tests)
- `tests/research/test_enterprise_ssd_datasheet.py` (70 tests)
- `tests/execution/test_specification_enrichment.py` (68 tests)
- `tests/research/test_specification_enrichment_boundaries.py` (17 tests)

**Corrective changes applied (6D review-closure pass):**
- Authority chain: `derive_datasheet_source()` derives datasheet URLs from
  frozen 7A EXTRACTED AUTHORITATIVE source via supportSpecsData extraction
- Real fixture: test_datasheet_link_extractor uses actual frozen Seagate HTML
  fixture (not synthetic replica)
- Batch execution: `enrich_enterprise_ssd_specifications_batch()` provides
  shared PDF fetch across product identities (1 fetch for 3 identities)
- Parser error taxonomy: only explicit verified exception classes caught
  (pdfplumber.utils.exceptions.PdfminerException, pdfminer.pdfparser.PDFSyntaxError);
  no module-name substring matching; RuntimeError propagates
- Result self-audit: empty-evidence hole closed (ENRICHED + positive count
  + zero raw observations rejected); ambiguous duplicate provenance rejected
- FetchedDocument URL contract: embedded credentials rejected for both
  requested_url and final_url
- Provider boundary guards: document.py (generic) and http_pdf.py (adapter)
  added to test_provider_boundaries.py guard sets
- Real frozen 6C composition: actual frozen 6C extraction from real HTML
  fixture + 6D enrichment from real PDF fixture
- Real frozen 7B vertical slice: full chain 6C + 6D -> 7A -> 7B with
  real Seagate fixtures (XP15360SE70015, XP3840SE70005 candidates)
- Real one-fetch proof: batch primitive proves 1 support page + 1 PDF for
  3 identities sharing one datasheet
- Type correction: `_find_mpn_column_global` return annotation corrected to
  `tuple[int, int, int, int, int] | None` (was missing row_idx)
- Adversarial result tests: 10 real constructor rejection tests using
  tampered frozen objects
- Parser exception monkeypatch tests: 5 tests proving pdfminer exceptions
  -> PARSE_FAILED, RuntimeError -> propagates, MPN ambiguity -> propagates

Real evidence:
- PDF source: Seagate Nytro 5550/5350 Datasheet
- PDF URL: /content/dam/seagate/en/content-fragments/products/datasheets/enterprise-rebranding/nytro-5550-5350-ssd/nytro-5550-5350-ssd-DS2099-4-2410US-en_US.pdf
- PDF SHA256: b449dc488c0a3aa6d28b6e0ac2373a7fc42d7780cc1a437439c823b39833010c
- PDF byte size: 201,997
- Parser: pdfplumber (via pdfminer.six)
- 8 pages, 15 tables across product families
- XP15360SE70005: 6 ENRICHED observations (all VERIFIED)
- XP15360SE70015: 6 ENRICHED observations (same column)
- XP3840SE70005: 6 ENRICHED observations (different column)
- Support-record extraction: exact skuNumber -> exact datasheet path
- All three SKUs share identical datasheet path (real fixture proven)

7B vertical slice evidence:
- Frozen 7A discovery: 81 records -> 80 candidates
- Required candidates found: XP15360SE70015, XP3840SE70005
- 7B bridge establish_candidate_product_identity: EXACT match
- Frozen 6C candidate evidence: physical_form_factor VERIFIED (from supportSpecsData)
- 6D candidate enrichment: 6 VERIFIED observations per candidate (capacity, sequential_read,
  sequential_write, random_read_iops, random_write_iops, endurance_dwpd)
- compose_6c_6d_specifications: merges 6C normalized evidence + 6D normalized evidence,
  re-resolves via frozen 6A (does NOT copy resolved values directly)
- Required candidates post-composition: scored_field_count=7, evidence_coverage=7/12
- XP15360SE70015:
  - scored_field_count = 7
  - evidence_coverage = Decimal(7)/Decimal(12)
  - observed_similarity = Decimal(1)
  - evidence_weighted_similarity = Decimal(7)/Decimal(12)
  - All 7 scored fields: field_similarity = 1 (exact match on all)
  - 5 non-scored fields: BOTH_NOT_VERIFIED
- XP3840SE70005:
  - scored_field_count = 7
  - evidence_coverage = Decimal(7)/Decimal(12)
  - observed_similarity = (Decimal('3.84')/Decimal('15.36') + 5 + Decimal('6900')/Decimal('7200')) / 7
    = Decimal('6.208333333333333333333333333333333333333') / 7
    = Decimal('0.8869047619047619047619047619047619047619')
  - evidence_weighted_similarity = Decimal('6.208333333333333333333333333333333333333') / 12
    = Decimal('0.5173611111111111111111111111111111111111')
  - capacity: SCORED, field_similarity = Decimal('0.25') (3.84 vs 15.36)
  - sequential_write: SCORED, field_similarity = Decimal('0.9583333333333333333333333333') (6900 vs 7200)
  - sequential_read, random_read_iops, random_write_iops, endurance_dwpd: SCORED, field_similarity = 1
  - physical_form_factor: SCORED, field_similarity = 1
  - 5 non-scored fields: BOTH_NOT_VERIFIED
- physical_form_factor remains SCORED for both candidates (preserved from frozen 6C)
- Batch one-fetch: 1 support page + 1 PDF for 3 identities (batch proof)
- Vertical slice test strengthened: asserts exact observed_similarity,
  evidence_weighted_similarity, and per-field field_similarity for both candidates

Strengthened vertical slice test (`test_real_7b_vertical_slice_with_enrichment`):
- Asserts exact scored_field_count = 7 (not >= 1)
- Asserts exact evidence_coverage = Decimal(7)/Decimal(12) (not > 0)
- Asserts exact observed_similarity per candidate
- Asserts exact evidence_weighted_similarity per candidate
- Asserts exact field_similarity for all 12 fields per candidate
- Asserts physical_form_factor SCORED (preserved from 6C)
- Asserts all 6 6D fields SCORED
- Asserts all 5 remaining fields BOTH_NOT_VERIFIED
- All assertions pass against real Seagate fixtures

New runtime dependency (declared in requirements.txt):
- pdfplumber>=0.11.0 (transitively pulls pdfminer.six): pure Python PDF table extraction
- Used in execution layer only; research layer remains parser-free
- Installed versions: pdfplumber 0.11.10, pdfminer.six 20260107
- Import boundary proof:
  - `import product_intelligence.research.enterprise_ssd_datasheet` loads zero third-party packages
  - `import product_intelligence.execution.specification_enrichment` loads pdfplumber + pdfminer.six
    (transitive through Django model imports in execution/__init__.py)
- Both packages explicitly imported in specification_enrichment.py:
  - `import pdfplumber` (open PDFs, extract tables)
  - `from pdfminer.pdfparser import PDFSyntaxError` and `from pdfplumber.utils.exceptions import PdfminerException` (bounded parser exception taxonomy)
- Both pdfplumber and pdfminer.six are explicitly declared runtime
  dependencies. pdfminer.six is also a dependency of pdfplumber, but is
  directly declared because 6D directly relies on its parser exception
  taxonomy.

No frozen file modifications.
No pre-6D test deletions.
No skip/xfail/deselect/bare-pass in any 6D test.

## Semantic qualification harness

**APPROVED / FROZEN**

The semantic qualification corpus, prompt v1.1, evaluator mathematics,
qualification thresholds, expected decisions, and safety gates are APPROVED AND FROZEN.

- Prompt v1.1 SHA256: f50e5584659f953ce73a97ccc8bc1ff487fbeeb37e2e0a72e52210613aeab1ff
- Corpus SHA256: 3c21d6fcd4eefa5cc383792abfd9308bd5c03315834c8ffdffd0f6a2b3619ca1

Do NOT modify:
- evaluation/semantic_corpus/cases.json truth labels or case contents
- SEMANTIC_PROMPT_VERSION = "1.1"
- semantic system/user prompt semantics
- semantic evaluator formulas
- qualification gates
- production research/matching.py
- production aggregation (4A FROZEN)
- production execution authority (frozen 4C/FU3B execution semantics preserved;
  future explicitly approved phases may extend)

Since FU3A2 the frozen prompt text, decision vocabulary, response schema and
strict parser/validator physically live in
`product_intelligence/semantic/contract.py`. `evaluation/semantic/prompt.py`,
`vocabulary.py` and `evaluator.py` re-export those same objects. The freeze
applies to the behaviour wherever it lives; the extraction was proved
behaviour-preserving by the two SHA256 fingerprints above.

## Model qualification runner

**IMPLEMENTED**

Semantic qualification harness infrastructure is implemented:

* transport.py - Abstract transport interface + OpenAI-compatible HTTP
* model_catalog.py - Explicit model catalog (8 primary + 1 smoke + 3 skip)
* runner.py - Benchmark runner with durable artifacts
* cli.py - CLI for list-models, run, evaluate, compare
* comparison.py - Offline comparison utility

All tests use fake transports / recorded responses. No live network calls.

**Two models have passed the formal FULL qualification gates**:
`amax/nemotron-3-super` (primary) and `vllm-262k/Qwen3.6-27B-262K` (fallback).
They are the pinned production route.

## FU3A — Production Semantic Runtime Contract

**APPROVED / FROZEN.** (Corrective history: FU3A2B, FU3A2C, FU3A2D, FU3A2E,
FU3A2F — labels for the corrective path to this freeze, not separate durable
phases. FU3A2F was the final corrective pass; ChatGPT's independent review of
the final FU3A2F `runtime.py` and `test_runtime.py` approved the contract.)

Both `semantic/contract.py` and `EvidenceDecision.AI_ASSISTED_MATCH` are now
frozen as part of this approval.

### Single source of truth

`product_intelligence/semantic/contract.py` is the canonical implementation of:

* Prompt v1.1 (`SEMANTIC_PROMPT_VERSION`, `SYSTEM_PROMPT`,
  `USER_PROMPT_TEMPLATE`, `SemanticPrompt`, `build_prompt`)
* `SemanticDecision`, `ConfidenceLevel`, `SemanticMatchResponse`
* `parse_raw_output`, `validate_response`, `RawOutputParseError`

`evaluation/semantic/prompt.py`, `vocabulary.py` and `evaluator.py` re-export
those objects. Sharing is proved by object identity, not by an import
statement (`tests/semantic/test_contract_sharing.py`). Production does not
import `product_intelligence.evaluation.semantic.*`.

`product_intelligence/semantic/transport.py` is likewise the canonical
transport implementation (HTTP call, error classification, all three
transport classes); `evaluation/semantic/transport.py` re-exports it rather
than keeping a second copy — proved by object identity in
`tests/semantic/test_contract_sharing.py`, same as the contract.

### Import boundary

Importing `product_intelligence.semantic` loads no
`product_intelligence.evaluation.*` module, no Django, and no network client
(`requests`, `urllib`, `urllib3`, `httpx`, `aiohttp`). `evaluation.semantic.transport`
is NOT whitelisted: the live transport is imported lazily inside transport
construction. Enforced by `tests/semantic/test_runtime_boundaries.py`, which
inspects real post-import `sys.modules` state from a clean module state — and
(FU3A2D) also restores each evicted module's *parent-package attribute*, not
only its `sys.modules` entry, so a test that reimports
`product_intelligence.semantic` cannot leave `product_intelligence.semantic`
(attribute access) and `sys.modules["product_intelligence.semantic"]`
pointing at two different objects for the rest of the test session.

### Pinned qualified route

| Setting | Value |
| --- | --- |
| Primary | `amax` / `nemotron-3-super` |
| Fallback | `vllm-262k` / `Qwen3.6-27B-262K` |
| temperature | `0.0` (exact float — `type(x) is float`, so `0`/`False` are rejected) |
| max_tokens | `32768` |

`SemanticRuntimeConfig` keeps these fields for compatibility, but
`validate_runtime_config` rejects any deviation before a transport is built or
called — by exact type where numeric equality alone would be insufficient
(`0`/`False` are numerically `== 0.0` but are not the qualified float). Only
`request_timeout_seconds` is configurable, and an unreadable or non-finite
environment value (`PI_SEMANTIC_REQUEST_TIMEOUT_SECONDS=abc`/`nan`/`inf`) fails
closed rather than silently defaulting.

### Fallback policy

Fallback uses an EXPLICIT allowlist (`PRIMARY_FALLBACK_ELIGIBLE_ERRORS`), never
"anything outside a deny set", so an unrecognised error code cannot silently
buy a second paid model call. Both lookup tables the runtime and
`SemanticRuntimeResult` index (`_PRIMARY_STATUS_TO_ERROR_TYPE`,
`_FALLBACK_STATUS_TO_ERROR_TYPE`) are complete over every non-OK status, and
every code the canonical transport's `ALL_ERROR_TYPES` can return has an
intentional mapping — proved by
`tests/semantic/test_runtime.py::TestEveryCanonicalTransportCodeHasAnIntentionalMapping`.

Eligible: `TIMEOUT`, `DNS_ERROR`, `TLS_ERROR`, `CONNECTION_ERROR`,
`RATE_LIMITED`, `HTTP_ERROR`, `PROVIDER_UNAVAILABLE`, `AUTHENTICATION_FAILED`,
`MODEL_NOT_FOUND`, `EMPTY_RESPONSE`, `MALFORMED_JSON`, `SCHEMA_INVALID`,
`MODEL_IDENTITY_MISMATCH`, `INVALID_RESPONSE` (FU3A2D: a malformed HTTP-200
provider envelope is an execution/output-contract failure of the same kind as
`MALFORMED_JSON`/`SCHEMA_INVALID`, and now buys one fallback attempt the same
way they do).

Not eligible: `INVALID_REQUEST_CONFIGURATION`, `UNSUPPORTED_PARAMETER`,
`PROVIDER_NOT_CONFIGURED`, `CASE_REJECTED` (FU3A2D: a content-policy rejection
of the case's own content — retrying the identical content against a
different model would not help — kept as its own known bounded status,
distinct from `UNKNOWN_ERROR`), an invalid `SemanticRuntimeConfig`, any
genuinely unrecognised error code, and programming exceptions.

A valid primary decision (`MATCH`, `NO_MATCH`, `UNCERTAIN`) is FINAL: exactly
one primary call, zero fallback calls.

### Model identity

Exact provider-reported model identity is mandatory. A primary that reports the
wrong model, or reports no model at all, falls back exactly once. A fallback
that reports the wrong model or no model is a final semantic failure — there is
no third provider.

### Provenance and safety

`SemanticRuntimeResult` carries the requested primary route, a tuple of frozen
`SemanticAttempt` records (provider, model, bounded status, latency), the
fallback flag and reason, and the bounded final error type. On ANY final
failure `actual_provider` and `actual_model` are `None`. No raw response, no
provider body, no exception text, no API key, and no chain-of-thought is
retained. Programming exceptions propagate rather than becoming a fallback.

`SemanticRuntimeResult` is fully self-validating (FU3A2D): every typed field
(`decision`, `confidence`, `error_type`, `fallback_reason`, `fallback_used`,
and the three attribute tuples) is checked by exact type, not merely accepted
and left to fail later inside `to_dict()`. A failure's `error_type` is
mechanically bound to what its attempts actually recorded — a one-attempt
failure's `error_type` must equal `_PRIMARY_STATUS_TO_ERROR_TYPE[first.status]`,
a two-attempt failure's must equal
`_FALLBACK_STATUS_TO_ERROR_TYPE[second.status]` — so a result cannot claim,
say, `PRIMARY_MODEL_NOT_FOUND` for an attempt that actually timed out.

### Relationship to 4A

The original deterministic assessment remains REJECTED.
The parallel AiAssistedMatchResult carries disposition AI_ASSISTED_MATCH.
Existing 4A sees the REJECTED assessment and excludes it as
IDENTITY_NOT_ACCEPTED.


## Known issues / debt

- FU3A Production Semantic Runtime Contract: APPROVED / FROZEN
- FU3B Semantic Execution Integration: APPROVED / FROZEN
- This Windows / Python 3.14 workstation has a fixed eleven-node subprocess-boundary
  flake allowlist. These nodes may fail independently between runs with
  OSError: [WinError 6/50] from subprocess.run(..., capture_output=True).
  No node outside the fixed eleven-node allowlist fails.
  Environment limitation, not a product defect.

**Current fixed Windows/Python 3.14 subprocess-boundary allowlist:**
11 exact nodes.

Node 11 (`tests/providers/test_provider_boundaries.py::test_http_pdf_imports_no_third_party_dependency`)
was qualified and approved during 6D. Historical snapshots retain the failure
counts actually observed at the time they were frozen (10 for 6B/6C/7A/7B).

## AD-059 — Authoritative Datasheet Specification Enrichment (6D)

**Status**: Accepted (6D implementation)

**Why added AFTER 7B**: Frozen 7B revealed that candidate specification
evidence from frozen 6C extraction is too sparse for useful differentiation.
All 80 Seagate candidates had evidence_coverage = 1/12 (only Form Factor).
6D extends specification evidence capability by adding manufacturer PDF
datasheet extraction without reopening frozen 6C extraction semantics.

**Architecture**:
- Provider-neutral document boundary (`providers/document.py`)
- Concrete HTTP PDF fetcher (`providers/http_pdf.py`, stdlib urllib)
- Pure research table interpretation (`research/enterprise_ssd_datasheet.py`)
- Execution enrichment composition (`execution/specification_enrichment.py`)
- pdfplumber for PDF table extraction (execution layer only)
- MPN -> table -> column -> row binding (exact raw equality)
- Unit incorporation from row header when cell lacks unit
- Six-field allowlist: capacity, sequential_read, sequential_write,
  random_read_iops, random_write_iops, endurance_dwpd
- Support-record datasheet-link extraction (`research/datasheet_link_extractor.py`)
- AUTHORITATIVE-only enforcement (SECONDARY rejected)
- Bounded model-row grammar (3 exact forms)
- Bounded spec-row grammar (6 exact regex patterns)
- Whole-PDF MPN uniqueness (global across all tables)
- Raw MPN exactness (no strip before comparison)
- Bounded parser exception handling (pdfminer/pdfplumber only)
- Fully self-auditing result (raw->outcome->normalized->resolution)
- 6C + 6D evidence composition primitive

**Constraints**:
- No LLM, no semantic model
- No title parsing
- No Interface splitting
- No frozen 6B modification
- No frozen 6C modification
- No frozen 7B modification
- Research layer is pure (no PDF parser, no I/O, no network)
- No frozen file modifications (verified)
- No pre-6D test deletions (verified)
- No skip/xfail/deselect/bare-pass in any 6D test (verified)

**Evidence**:
- Real Seagate Nytro 5550/5350 datasheet PDF fixture
- SHA256: b449dc488c0a3aa6d28b6e0ac2373a7fc42d7780cc1a437439c823b39833010c
- 201,997 bytes, 8 pages, 15 tables
- XP15360SE70005: 6 VERIFIED observations
- XP15360SE70015: 6 VERIFIED observations (same column)
- XP3840SE70005: 6 VERIFIED observations (different column)
- Support-record extraction: exact skuNumber -> exact datasheet path
- 6C + 6D composition: physical_form_factor preserved VERIFIED from 6C
- Candidate composition results (both candidates):
  - scored_field_count: 7 (1 from 6C + 6 from 6D)
  - evidence_coverage: 7/12
  - XP15360SE70015: observed_similarity=1 (all 7 fields match target)
  - XP3840SE70005: observed_similarity≈0.887 (capacity, sequential_write differ)

**Runtime dependency**:
- BOTH pdfplumber and pdfminer.six are explicitly declared runtime dependencies.
- pdfplumber for PDF table extraction (execution layer only)
- pdfminer.six for bounded parser exception taxonomy (execution layer only)
- pdfminer.six is also a transitive dependency of pdfplumber, but is directly
  declared for explicit import boundary control
- Research layer remains parser-free

**Test counts (actual collected)**:
| Module | Nodes |
| --- | --- |
| `test_datasheet_link_extractor.py` | 19 |
| `test_document_provider.py` | 29 |
| `test_http_pdf.py` | 20 |
| `test_enterprise_ssd_datasheet.py` | 70 |
| `test_specification_enrichment.py` | 68 |
| `test_specification_enrichment_boundaries.py` | 17 |
| `test_provider_boundaries.py` (6D additions) | 4 |
| **6D total** | **227** |

**Frozen**: PRODUCT-INTEL.6D approved by project lead.
