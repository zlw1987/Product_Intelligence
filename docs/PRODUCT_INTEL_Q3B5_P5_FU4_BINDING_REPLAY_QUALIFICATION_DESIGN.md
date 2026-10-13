# Product Intelligence — Q3-B5-P5: FU4 Versioned Binding, Qualification and Replay Integration Design

**Mode: DESIGN ONLY — no implementation in this phase.** No code, no test, no
capture, no deployment, no migration, no model call, no authority promotion,
no corpus reseal. The only artifact of this phase is this document, committed
design-only, append-only, on the starting SHA below.

**Starting SHA:** `4c4e563a9f82b5b6f76b3b0edcce5142b3d6b982`
(Q3-B5-P4-FU2 endpoint — the FU4 extraction-evidence-association closure;
baseline collection **7500, re-verified this session** by a full
`pytest --collect-only` over the working tree at this SHA).

**Scope.** This document designs the smallest safe integration of the
approved, corrected, research-only FU4 bundle-composition authority contract
(`product_intelligence/research/semantic_authority_fu4.py`,
`SEMANTIC_AUTHORITY_V2_S2A_FU4`, bundle-composition evidence schema v3) into
Product Intelligence's **versioned offline qualification and replay
infrastructure**. It is the integration design of record for the separately
gated registration step that the approved FU4 design
(`docs/PRODUCT_INTEL_Q3B5_P3_BUNDLE_COMPOSITION_DESIGN.md`, §7.3 — "the
separately gated registration step (specified, not executed)") left to its
own phase. That step is NOT executed here.

The goal, restated: support **reproducible, auditable FU4 offline records** —
persistence, deterministic zero-live replay, and offline qualification under
the new binding — **without changing historical FU2/FU3 interpretation and
without enabling production authority**.

**Relationship to the prior documents.**

| Document | Role here |
| --- | --- |
| `docs/PRODUCT_INTEL_Q3B5_P3_BUNDLE_COMPOSITION_DESIGN.md` | The approved FU4 contract design (CORRECTED — Blocker A / Blocker B + Revision records 2 / 3). §7.3 specifies the registration step this document designs; D12–D15, §7.1–§7.5, §8, §10–§13 are binding inputs. |
| `docs/PRODUCT_INTEL_SEMANTIC_V2_PROMPT_2_1_DESIGN_Q3B3_FU2.md` (Q3-B3-FU2 rev 2) | The approved Prompt 2.1 design; the SU axis and P1–P6 outcome table the model side speaks to. |
| `docs/PRODUCT_INTEL_SEMANTIC_V2_Q3B4_AUTHORITY_BOUNDARY_DECISION.md` | The approved Q3-B4 decision (Option D firewall; AD-Q3B4-1..6): per-binding replay discipline (§6.5), the amendment pattern (§6.1), W1's atomic consumer guard, Q3-C conditioning (AD-Q3B4-6). |
| `docs/PRODUCT_INTEL_Q3B5_P1_INDEPENDENT_AUDIT.md` | The P1 independent audit (PASS; finding F-4: the DRAFT policy is scoped to corpus 1.0.0 — a policy-governance step is owed by any later qualification lineage, carried into this design §5.6). |
| `docs/PRODUCT_INTELLIGENCE_STATUS.md` / `docs/PRODUCT_INTELLIGENCE_PLAN.md` | Phase state and decision log. The PLAN's canonical spec currently ends at §26.38 (Q3-B5-P2-FU1); the Q3-B5-P3 / P4 / P4-FU1 / P4-FU2 phases are recorded in STATUS. The documented STATUS/PLAN catch-up (audit F-3 lineage) applies: the registration phase implemented from this design gets its own PLAN §26.x row at its completion. No conflict exists — the PLAN is not yet the record for these phases; STATUS + the approved design documents are. |

**What this document deliberately is NOT.**

* Not an implementation. No module, test, corpus artifact, or registry entry
  is created or changed by this phase.
* Not an execution of the registration step. Everything §4–§5 specify is
  executed only by the separately gated registration phase(s) (§10), after
  independent review of BOTH this document and the current FU4 module
  (Q3-B5-P4-FU2 — itself pending final review at the starting SHA).
* Not a qualification or promotion decision. `V2_AUTHORITY_QUALIFIED` stays
  False in both pinned locations; nothing here activates V2 authority,
  connects any derivation to pricing, or changes any tier reachable from a
  live path.

---

# 1. Source evidence inventory

Every entry below was re-verified at the starting SHA this session (file
digests are the SHA-256 of the working-tree file; the FU4 contract phase's
A1 pin set — `tests/research/test_semantic_authority_v2_fu4.py`
`FROZEN_MODULE_PINS` / `CORPUS_ARTIFACT_PINS` — records the same digests).

## 1.1 The persistence envelope and codec (research layer)

* `product_intelligence/research/semantic_decision_record.py` — the
  version-independent envelope foundation: `canonical_sha256` (sorted keys,
  compact separators, ASCII, no floats), the bounded error vocabulary
  (`SemanticDecisionCodecError`, `SemanticDecisionReplayError`,
  `CanonicalDigestError`), the universal binding section
  (`run_id` / `assessment_index` / `source_url`), and the
  `SemanticDecisionContractAdapter` extension point. The adapter dataclass
  carries **exactly the fields the registration step needs**:
  `envelope_schema_version`, `semantic_contract_version`,
  `supported_bindings: tuple[tuple[str, str, int, int, str], ...]` (the
  five-axis binding tuples), `record_type`, plus `encode` / `decode` /
  `replay` / `run_binding_violation`.
* `product_intelligence/research/semantic_decision_codec.py`
  (digest `ef31ef38ca5159c01cbfab9056ae20365c1dd58a8c6fb33b8f45f9f80a03b769`)
  — the universal envelope codec:
  `SEMANTIC_DECISION_SCHEMA_VERSION = 1`; the registry
  `_REGISTERED_SEMANTIC_CONTRACT_ADAPTERS = (SEMANTIC_V1_ADAPTER,
  SEMANTIC_V2_ADAPTER,)`; `registered_semantic_contract_adapter(envelope,
  contract)` — **first-match lookup on the two-axis pair** (this is the
  dispatch surface the FU4 registration must amend — §4.3, FIND-1);
  `supported_contract_bindings()` — the union of the registered adapters'
  `supported_bindings` (currently exactly `(V1, 2.0/FU2)`); `decode_semantic_
  decision_record(payload, schema_version)` — universal framing (envelope
  version agreement, exact universal binding, the `contract` section's
  `semantic_contract_version` as the dispatch key), no-float walk, adapter
  dispatch, bounded decode.
* `product_intelligence/research/semantic_decision_replay.py`
  (digest `481f58aecf08893f0aab683a620bf25a41960e529f40ae197be06be1e272f803`)
  — the universal zero-live replay dispatch: `SUPPORTED_CONTRACT_BINDINGS`
  (= `supported_contract_bindings()`); `replay_semantic_decision(record)`
  reads the record's EXPLICITLY RECORDED five-axis binding, refuses anything
  outside the union, then selects the registered adapter whose
  `supported_bindings` **contain the full five-tuple**
  (`_adapter_for_binding`). The replay side already dispatches per-binding;
  only the codec's decode side dispatches per two-axis pair (FIND-1).
* `product_intelligence/research/semantic_decision_v1.py` — the frozen V1
  adapter: `V1_CONTRACT_BINDING = ("V1", "1.1", 1, 1,
  "SEMANTIC_AUTHORITY_V2_S2A_FU2")`; route pin amax / qwen3.8-27b primary,
  vllm-262k / Qwen3.6-27B-262K fallback; `supported_bindings =
  (V1_CONTRACT_BINDING,)`.
* `product_intelligence/research/semantic_decision_v2.py`
  (digest `9176380cc67090b1b799e7f9ad1640e5f2858ea1b9680897ff3cb7ad5f4cffeb`)
  — the frozen V2 adapter: `V2_CONTRACT_BINDING = ("V2", "2.0", 1, 1,
  "SEMANTIC_AUTHORITY_V2_S2A_FU2")`; `supported_bindings =
  (V2_CONTRACT_BINDING,)`; the `SemanticDecisionRecordV2` typed record whose
  constructor **exactly pins** semantic contract "V2", prompt "2.0", input /
  output schema 1, authority FU2 (a 2.1 or FU3 or FU4 value is
  un-constructible — FIND-2); the pinned route; `V2_AUTHORITY_QUALIFIED =
  False` (pinned location 1); the exact V2 payload section key sets
  (`_V2_TOP_LEVEL_KEYS`: `schema_version` / `binding` / `contract` / `case` /
  `evaluation` / `execution` / `derived` / `integrity`); the V2 replay
  (reconstruction + frozen-derivation re-derivation + derived-agreement
  proof).
* `product_intelligence/runs/models.py` — `SemanticDecisionRecord` (the
  Django model, ~line 845 ff.): one row per (run, assessment_index), opaque
  `payload` column + separate `payload_digest` column (the whole-artifact
  tamper anchor) + `schema_version` column (the ENVELOPE format version,
  1). Its docstring states the extension point verbatim: "A future semantic
  contract … reuses this row by registering a new contract adapter; no model
  change, no new migration, no data rewrite … Unknown or future semantic
  contracts stored here are durably identifiable but fail closed on
  interpretation."
* `product_intelligence/execution/semantic_decision_persistence.py` — the
  persistence service: write (encode + `canonical_payload_digest`), read
  (row digest re-verify + `decode_semantic_decision_record`), replay
  (`replay_semantic_decision_record`). It calls ONLY the universal codec /
  replay entry points — it needs no change at registration (the codec is the
  single dispatch surface).

## 1.2 The authority contracts (research layer)

* `product_intelligence/research/semantic_authority_v2.py`
  (digest `78301d308e0a5e748c2a22cd8785c673b7c2230b54cc60f4714ee2da6b74d8a5`)
  — the frozen S2-A authority contract as frozen through S2-A-FU2 (token
  `SEMANTIC_AUTHORITY_V2_S2A_FU2`): `derive_authority_tier` (the frozen
  derivation; precedence HARD_CONFLICT > HUMAN_CONFIRMED > AI; the 27-entry
  matrix; the restrict-only ceilings), `derive_relationship_authority`,
  `derive_product_evidence_quality`, `substate_relationship_requirement`,
  the `AuthorityTier` vocabulary (`MACHINE_VERIFIED` /
  `AI_ASSISTED_COMPARABLE` / `NEEDS_REVIEW` / `HUMAN_CONFIRMED` /
  `HARD_CONFLICT` / `EXCLUDED_LOW_CONFIDENCE`), and the pricing-eligibility
  constants: `PRICING_ELIGIBLE_TIERS = {MACHINE_VERIFIED,
  AI_ASSISTED_COMPARABLE, HUMAN_CONFIRMED}`, `MARKET_EVIDENCE_TIERS =
  PRICING_ELIGIBLE_TIERS | {NEEDS_REVIEW}`, with import-self-checks that
  `NEEDS_REVIEW` is never pricing-eligible.
* `product_intelligence/research/semantic_authority_fu3.py`
  (digest `4ea529452e50a62b63778c97e37856f5660a0c5426654d7918725b3d59e24c0f`)
  — the frozen FU3 firewall (token `SEMANTIC_AUTHORITY_V2_S2A_FU3`):
  `IdentityResolutionBoundV2` (the 14-row table), `SalesUnitAuthorityV2`
  (PROVEN_EQUIVALENT / UNPROVEN / CONTRADICTED), `TargetSalesUnitEvidenceV2`
  (the frozen target-side record: `form` / `quantity` / `source`),
  `derive_authority_tier_fu3` (frozen derivation + the two restrict-only
  ceilings `CEILING_SALES_UNIT_NOT_PROVEN` /
  `CEILING_SALES_UNIT_CONTRADICTED`), `AuthorityDecisionV2FU3`, and the
  per-binding dispatch `derive_authority_tier_for_contract` (FU2 arm = the
  frozen derivation; FU3 arm = the FU3 derivation; unknown token =
  `UnknownAuthorityContractTokenError`).
* `product_intelligence/research/semantic_authority_fu4.py`
  (3614 lines; the FU4-owned pending-review module; the only FU4 file in the
  tree) — the approved, corrected FU4 contract (token
  `SEMANTIC_AUTHORITY_V2_S2A_FU4`; `BUNDLE_COMPOSITION_EVIDENCE_VERSION_FU4
  = 3`; `KNOWN_AUTHORITY_CONTRACT_TOKENS_FU4 = {FU2, FU3, FU4}`). The
  registration step's frozen inputs from this module:
  * the five-way `BundleCompositionStateV2FU4` (SYNTACTICALLY_VALID /
    ESTABLISHED / PARTIAL / ABSENT / CONTRADICTED_PUBLISHED);
  * `CandidateBundleCompositionEvidenceV2FU4` — fields `schema_version` /
    `basis` (EXTRACTION_RESULT_V1 | RECORDED_CHANNEL) / `state` /
    `completeness_attestation` / `composition_clause` /
    `additional_clauses` / `source` / `channel_quantity` /
    `extraction_result_digest` / `extraction_input_digest` /
    `extraction_result` (the EXACT original `SalesUnitExtractionResult`,
    inside `evidence_digest`) / `channel_content_digest` /
    `evidence_digest`; `canonical()` (the document minus
    `evidence_digest`, INCLUDING the embedded result's canonical) and
    `verify()` (digest re-verification);
  * `TargetSalesUnitEvidenceV2FU4` — the frozen FU3 record's fields plus
    `schema_version` / `composition_clause` / `composition_state` /
    `completeness_attestation` / `evidence_digest`; `canonical()` /
    `verify()`;
  * `CompositionCompletenessAttestationV2FU4` and
    `QuantityCompletenessAttestationV2FU4` — self-verifying, audit-text-
    only, bounded-basis / side / source records; `canonical()` / `verify()`;
  * `AuthorityDecisionV2FU4` — the FU3 decision field set PLUS the bounded
    bundle-axis audit fields (`quantity_axis_state`,
    `candidate_composition_state`, `target_composition_state`,
    `candidate_completeness_attestation_digest`,
    `target_completeness_attestation_digest`,
    `quantity_attestation_digest` — exactly None for non-bundle channels),
    with the same construction invariants (AI_ASSISTED_COMPARABLE +
    UNPROVEN / CONTRADICTED is un-constructible);
  * the presentation gate `_verify_candidate_composition` — the v3
    four-step original-result association chain (embedded result's own
    integrity; record anchors = result digests; the frozen P2 mapping of the
    embedded result EQUALS the presented channel; the recomputed
    composition EQUALS the complete record) plus the intact RECORDED_
    CHANNEL exact-construction check and the channel-content-digest
    binding; `_verify_target_evidence`;
  * `derive_sales_unit_authority_fu4` / `derive_sales_unit_authority_fu4_
    case` (the U0–U21 table; non-bundle arms delegate to the frozen FU3
    derivation), `derive_authority_tier_fu4`, and the superset dispatch
    `derive_authority_tier_for_contract_fu4(token, assessment, evaluation,
    context_provenances, product_evidence, human_review, *, sales_unit_
    channel, target_unit_evidence, candidate_composition, quantity_
    attestation)` — the FU2 / FU3 arms delegate byte-identically
    (delegation identity pinned by the FU4 suite's A2); composition /
    attestation inputs under a historical token are contract misuse
    (fail closed).
* `product_intelligence/research/sales_unit_extraction.py`
  (digest `0dd6016503292a926d86f3dbafa97e59a713a4386df2a648882e4942cc6737b6`)
  — the frozen P2 extraction (schema v1): `SALES_UNIT_EXTRACTION_SCHEMA_
  VERSION = 1`; `SalesUnitExtractionResult` (`schema_version` / `state` /
  `cues` / `identifier_field_notes` / `established_kind` /
  `established_quantity` / `input_digest` / `result_digest`;
  `canonical()` — JSON-native document including the cues' full provenance
  — and `verify_integrity()` — both digests recomputed + cue-span
  containment); `sales_unit_channel_from_extraction` (the frozen lossy
  mapping: OBSERVED_UNAMBIGUOUS → the frozen channel over the PRIMARY
  established cue's published text; every other state → the canonical
  UNAVAILABLE absence); `extract_sales_unit_evidence` (the deterministic cue
  engine over one `ListingObservation`).
* `product_intelligence/research/semantic_v2.py`
  (digest `d573d8086bc51db1653f99cebe42aa476ff954fc9d582f8f014ec2d4a97e7d7d`)
  — the frozen S2-C input contract: `SemanticMatchCaseV2` (the recorded V2
  input, input-schema-1 shape: target, candidate, deterministic identity
  context, context provenances, product evidence), `CandidateSalesUnit
  EvidenceV2` (the S2-C-FU1 recorded channel: `state` / `kind` / `quantity`
  / `raw_detail` / `source`; `canonical()` — the five-field document the
  FU4 `channel_content_digest` binds), `SemanticMatchResponseV2` (the strict
  7-key output, output-schema-1), the bounded enums.

## 1.3 The prompt contracts and live runtime (semantic layer)

* `product_intelligence/semantic/contract_v2.py`
  (digest `d1a69692f57ece6bab8362e77c7067a9642f214d2b115403c1638fe537aa7492`)
  — the frozen Prompt 2.0: `SEMANTIC_PROMPT_VERSION_V2 = "2.0"`,
  `SYSTEM_PROMPT_V2` (canonical `{"text": …}` digest
  `c0cc98bdd6d357e81d4692218f18d354351fc2833267b3062b7cd74b18445a84` —
  recomputed this session), `build_semantic_prompt_v2`,
  `render_v2_user_prompt`.
* `product_intelligence/semantic/contract_v2_1.py`
  (digest `dc86899f233eb97beb70007a128745bfc04d374a48dc1d45aec4f6703dede1ec`)
  — the separately versioned Prompt 2.1 owner:
  `SEMANTIC_PROMPT_VERSION_V2_1 = "2.1"`,
  `V2_1_CONTRACT_BINDING = ("V2", "2.1", 1, 1,
  "SEMANTIC_AUTHORITY_V2_S2A_FU3")` (composed from the research exports —
  no literal token in source; import-self-checked to move ONLY the prompt
  and authority axes), `SYSTEM_PROMPT_V2_1` (canonical `{"text": …}` digest
  `e2949e7544d26228ac6f5555ae8ebd28019076e1de88ace25e79a5d942d818fc` —
  recomputed this session; the 2.1 COMMERCIAL SALES-UNIT RULES commit the
  model to the absolute rule, the ambiguous-cue UNCERTAIN, and the
  never-read-UNAVAILABLE-as-single-unit discipline; the prompt names no
  authority token), `build_semantic_prompt_v2_1` / `render_v2_1_user_prompt`
  (the frozen 2.0 rendering + exactly the two approved annotation lines;
  fail-closed on 2.0 anchor drift). **This module is the binding-constant
  owner for the registration step (§4.5).**
* `product_intelligence/semantic/runtime_v2.py`
  (digest `e0791384a218409a1e390e304cfc6da1d0e002b404955722b94d557b8c02cc36`)
  — the live V2 runtime: the pinned route (PRIMARY `amax` / `qwen3.8-27b`,
  FALLBACK `vllm-262k` / `Qwen3.6-27B-262K`), `V2_AUTHORITY_QUALIFIED =
  False` (pinned location 2), and the live prompt axis: the runtime executes
  the FROZEN 2.0 builder (`SEMANTIC_PROMPT_VERSION_V2 == "2.0"` — drift-
  pinned by the FU4 A4 node). **The registration step does not touch this
  module: no live 2.1 execution exists, and none is created here.**

## 1.4 The qualification harness (evaluation layer)

* `product_intelligence/evaluation/semantic_v2/corpus.py`
  (digest `876edbe8322889653a5a2178b30f2daf0c7d9a540e52906bf70cad91cddbcc40`)
  — strict corpus loading: `CORPUS_SCHEMA_VERSION = 1`; the binding seal
  registry
  `BINDING_CORPUS_VERSIONS = {("V2","2.0",1,1,FU2) → "1.0.0",
  ("V2","2.1",1,1,FU3) → "1.1.0"}`; `KNOWN_PRODUCTION_BINDINGS` (the key
  set); the exact corpus-document key set (`corpus_id`,
  `corpus_schema_version`, `corpus_version`, `corpus_label`, `created_utc`,
  `semantic_contract_binding`, `cases`, `label_revisions`, `corpus_digest`);
  the per-case strict decode (real `SemanticMatchCaseV2` constructor as the
  arbiter, bounded rejection classes); the per-case and whole-corpus digest
  verification; the `label_revisions` numbering / A–D reason-class rules;
  `build_manifest_document` / `verify_manifest` (manifest schema 1:
  `manifest_schema_version`, `corpus_id`, `corpus_version`,
  `semantic_contract_binding`, `corpus_digest`, `case_count`, `cases`,
  `manifest_digest`).
* `product_intelligence/evaluation/semantic_v2/fixtures.py`
  (digest `cdb60166cf71d3f313b254a1eb652cdec711c8a8cc39a8676eb245bec5f109a8`)
  — the auditable corpus source: `CORPUS_ID = "PI-SEMANTIC-V2-
  QUALIFICATION"`, `CORPUS_VERSION = "1.0.0"`, `CORPUS_VERSION_2_1 = "1.1.0"`,
  `CORPUS_CREATED_UTC = "2026-10-08T00:00:00Z"`, `build_corpus_document()`,
  `build_corpus_2_1_document()` (the 1.1.0 BINDING-ONLY re-seal: every
  per-case document byte-identical to 1.0.0; exactly `{corpus_version,
  semantic_contract_binding, corpus_digest}` moved; `label_revisions`
  empty), `build_manifest_document(corpus_document)`.
* `product_intelligence/evaluation/semantic_v2/gates.py`
  (digest `113c7b53605b4a85d5b11fe93e182518fd1efcf1115b7f797177d4508cc58371`)
  — the eight MANDATORY hard safety gates (zero false MATCH on ALWAYS_HARD /
  packaging / accessory conflicts; zero schema-bypass acceptance; zero
  unauthorized authority promotion; zero customer-alias promotion;
  zero contract-version mismatch; zero silent missing evaluation);
  `decide` (FAIL_CLOSED > NOT_QUALIFIED > POLICY_PENDING >
  INCOMPLETE_COVERAGE > THRESHOLD_INDETERMINATE > BELOW_THRESHOLD >
  QUALIFIED). The `zero_contract_version_mismatch` gate pins
  `KNOWN_PRODUCTION_BINDINGS` (drift-pinned to the research export and the
  semantic layer's 2.1 owner — the gate's detail text branches on the
  binding).
* `product_intelligence/evaluation/semantic_v2/report.py`
  (digest `cad62e4234f7478a326cb5a398f40bc4e1c2e7f2ac1915954179be0c3363c6f1`)
  — the report contract: the `contract` section (`_contract_section` —
  exactly the two known production bindings; the REAL system-prompt digest
  of the bound prompt version: 2.0 `c0cc98bd…` / 2.1 `e2949e75…`; the
  runtime config identity incl. `v2_authority_qualified`); the `authority`
  section (`granted: false` + the note "this report is evaluation evidence
  only; it grants no pricing authority, no tier promotion, and no
  human-review behavior change"); the corpus / model / policy / metrics /
  safety-gates sections; `verify_report` / `verify_direct_report` (the
  report re-binds to the exact corpus + contract + per-case snapshot +
  digests).
* `product_intelligence/evaluation/semantic_v2/capture.py`
  (digest `4da8b79a33ffc86363fb01af1b6b5ff0533191374da53a46ecf5b137e00f73fd`)
  / `direct_capture.py` (digest `58b790879efb13f167bf20ae56c96807a47dca9deda10e433d4aece5015e616d`)
  — the two capture schemas (schema 1 each): PRODUCTION_ROUTE (the frozen
  2.0 prompt only; the live runtime's builder) and DIRECT_MODEL_
  QUALIFICATION (exactly the pinned routes; prompt axis ∈ {2.0, 2.1});
  per-attempt route pinning (any other provider/model is a capture
  integrity error); fallback-on-execution-failure-only; the corpus binding
  `(corpus_id, corpus_version, corpus_digest)` + the **prompt-axis** cross-
  version check — **the authority axis is not a capture-binding axis** (a
  capture binds to the corpus's bound PROMPT version, never to the corpus's
  authority token).
* `product_intelligence/evaluation/semantic_v2/evaluator.py` — the
  offline per-model evaluation (read this session; NOT in the FU4 A1
  pin table — it is pinned by its own Q3-A / P1 suites, and is a
  declared byte-frozen input of R2):
  `_score_semantic` (the model's decision vs the corpus label; the
  FALSE_MATCH severity classes incl. `commercial_sales_unit_safety`),
  `evaluate_no_capture` (every eligible semantic case NOT_CAPTURED — never
  a pass, never a fabricated response; contract-negative cases still
  evaluated for rejection correctness; the route must be one of the two
  pinned routes), `evaluate_for_model` / `evaluate_direct_for_model`
  (primary / fallback independence: the per-model projection),
  `compute_metrics` (the separate semantic-accuracy / safety metric
  surface: match_precision / match_recall over AUTHORITATIVE evaluated
  cases only, valid_structured_response_rate, eligible_coverage, the
  ambiguity and contract-negative slices).
* `product_intelligence/evaluation/semantic_v2/policy.py`
  (digest `af951180594a4e10cba64db22be114e4bd4b03bb204179c689bef20617e387f4`)
  — the policy artifact contract (schema 1): the exact threshold vocabulary
  (`match_precision_min`, `match_recall_min`,
  `valid_structured_response_rate_min`, `eligible_coverage_min`), the
  DRAFT / APPROVED status discipline (an APPROVED policy must name
  `approved_by` + `approved_utc`; an unapproved one carries neither),
  `policy_applies_to` (corpus_id + corpus_version), `evaluate_thresholds`
  (a threshold with an insufficient denominator is `met: null` — never
  satisfied by default).
* `product_intelligence/evaluation/semantic_v2/cli.py`
  (digest `0102c4ccc98034d6f5ede3bd2d7be238ae37a4136ca60a634ebd387fb1509376`)
  — the corpus-build / corpus-digest / corpus-manifest / evaluate /
  evaluate-direct / verify-report commands (offline; the committed
  artifacts regenerate byte-for-byte).

## 1.5 The corpus artifacts of record

| Artifact | Version | Binding | Corpus digest | Manifest digest | Cases |
| --- | --- | --- | --- | --- | --- |
| `evaluation/semantic_v2_qualification/corpus_v1.json` | 1.0.0 | `["V2","2.0",1,1,"SEMANTIC_AUTHORITY_V2_S2A_FU2"]` | `2c37ba088c317d8cefc6ad0dd7e0d73cfd085f6474ef43eb6953e3cf0170b549` | `aa870660f287236d6d08a40c9cc15d58b5bfe2b36772e286102fe4a0673452e9` (manifest_v1.json, file digest `caa5d76f…`) | 56 |
| `evaluation/semantic_v2_qualification/corpus_2_1.json` | 1.1.0 | `["V2","2.1",1,1,"SEMANTIC_AUTHORITY_V2_S2A_FU3"]` | `14396eae884841e20063cb4da0d4424ce8f05ff8745f2c787fc395d250ea8dcd` | `c135b4a9f2e7b09908615c2a8bb3f28472e262b3c6440b9dc4adacf82ab4f6c2` (manifest_2_1.json, file digest `f37956e4…`) | 56 |
| `evaluation/semantic_v2_qualification/policy/qualification_policy_draft_1.json` | draft-1 (DRAFT, `approved: false`) | applicable to corpus 1.0.0 only | file digest `6bc30d37…` | — | — |

`label_revisions` is empty in both corpus versions. The 1.1.0 document is a
binding-only re-seal of 1.0.0 (56/56 per-case documents byte-identical; only
`{corpus_version, semantic_contract_binding, corpus_digest}` moved). No
corpus 1.2.0 artifact exists (pinned by the FU4 suite's A4 / E2).

The three sales-unit-relevant corpus cases (verified this session):

| Case | Class | Substate | Recorded channel | Expected |
| --- | --- | --- | --- | --- |
| `V2Q-SSD-SU-TRAY-0032` | AUTHORITATIVE | U2_SKU_ONLY | OBSERVED TRAY_OR_FACTORY_PACK, qty None, "tray of 20" | NO_MATCH + PACKAGING_QUANTITY, `commercial_sales_unit_safety: true` |
| `V2Q-SSD-SU-MULTI-0033` | AUTHORITATIVE | U2_SKU_ONLY | OBSERVED PACK_QUANTITY, qty 4, "pack of 4" | NO_MATCH + PACKAGING_QUANTITY, `commercial_sales_unit_safety: true` |
| `V2Q-GPU-SU-BUNDLE-0034` | AUTHORITATIVE | U4_NO_MPN | OBSERVED BUNDLE, qty None, "GPU + power cables + bracket kit" | NO_MATCH + BUNDLE, `commercial_sales_unit_safety: true` |

All three are conflict cases against the DEFAULT single-unit target (no
target-side bundle record exists in the corpus). Case 0034's clause is fully
parseable under the FU4 materiality grammar but carries NO completeness
marker ⇒ SYNTACTICALLY_VALID ⇒ composition-unknown ⇒ under FU4 the bundle
arm derives CONTRADICTED via the form axis (U9 — form before contents),
exactly as the frozen FU3 arm does (form mismatch). **The committed corpus
contains no ESTABLISHED-composition (attested) case: the FU4 PROVEN path
(U19 / U20) is exercised only at the research (deterministic) level, never
by a model-corpus label.**

The committed no-capture baseline reports: `reports/q3a_baseline/` (corpus
1.0.0; policy null; decision POLICY_PENDING; authority granted=false) and
`reports/q3b5_baseline_2_1/` (corpus 1.1.0; policy null — the DRAFT policy
is inapplicable to 1.1.0; decision POLICY_PENDING; authority granted=false).

## 1.6 The test suites of record (node counts at the starting SHA)

| Suite | Nodes | Role |
| --- | --- | --- |
| `tests/research/test_semantic_authority_v2_fu4.py` | 224 | The FU4 contract suite (A1 file pins, A2 token / delegation identity, A4 registries / reachability, A7 two-token coexistence, B1–B12 evidence schema, C1–C12 comparison rules, D1–D3 tier / overlay, E1–E2 contract-phase registries, F1–F4 never-infer). |
| `tests/research/test_semantic_authority_v2_fu3.py` | 98 | The frozen FU3 suite (byte-pinned by the FU4 A1 as starting-SHA + the one recorded guard allow-line). |
| `tests/research/test_sales_unit_extraction.py` | 111 | The frozen P2 extraction suite (digest-pinned unchanged). |
| `tests/research/test_sales_unit_extraction_recorded_pages.py` | 7 | The P2 recorded-page suite (digest-pinned unchanged). |
| `tests/evaluation/semantic_v2/test_q3b5_p1_binding_replay.py` | 20 | The P1 binding / replay isolation suite (the 2.1 binding drift pins, the codec registry pins, the cross-version corpus / capture / report refusals, the FU3 payload refusal, the sales-unit-blindness documented property). |
| `tests/research/test_semantic_decision_codec.py` | (suite of record) | The universal codec strictness / dispatch / tamper suite. |
| `tests/research/test_semantic_decision_replay.py` | (suite of record) | The universal replay gate suite (the `SUPPORTED_CONTRACT_BINDINGS` exact-tuple + length-2 pins; the gate-fires rows). |
| `tests/research/test_semantic_decision_v2.py` / `test_semantic_decision_record.py` / `test_semantic_decision_boundaries.py` | (suites of record) | The V2 adapter / envelope / boundary suites. |
| `tests/evaluation/semantic_v2/test_q3a_*` | (suites of record) | The Q3-A harness suites (corpus integrity, evaluation, qualification, reports, direct capture). |

**Full-suite collection at the starting SHA: 7500** (re-verified this
session). Skipped / xfailed / deselected: 0 / 0 / 0. The documented
load-sensitive clean-interpreter subprocess guard flake class (Q3-B5-P2-
FU1) is unchanged.

## 1.7 The FU4 suite's recorded contract-phase pins that the registration step moves

The registration step, by definition, moves the "registries are exactly as
frozen" pins to "registries are exactly as registered". The EXACT nodes that
assert the pre-registration state (and therefore require the documented,
name-preserving, in-place correction of the P1 / P2-FU1 / Q3-B4-FU2 /
Q3-B5-P4-FU1 / FU2 precedent when the registration phase runs):

In `tests/research/test_semantic_authority_v2_fu4.py`:
* `TestA1FrozenFilePins` — the `FROZEN_MODULE_PINS` / `CORPUS_ARTIFACT_
  PINS` / `SUITE_FILE_PINS` tables re-pin to the registration phase's own
  starting SHA, excluding the files that phase owns (the codec, the research
  `__init__`, the semantic / harness extension targets);
* `TestA4RegistriesAndReachability.test_the_production_codec_registry_is_
  unchanged` (asserts `supported_contract_bindings() == (V1, 2.0/FU2)`);
* `TestA4RegistriesAndReachability.test_the_harness_registries_are_unchanged`
  (asserts the harness knows exactly two bindings, no 1.2.0 artifact, no
  `CORPUS_VERSION_2_1_FU4`);
* `TestA4RegistriesAndReachability.test_an_fu4_bound_payload_is_refused_by_
  production_replay` (asserts the replay registry refuses an FU4-bound
  payload);
* `TestE1ContractPhaseRegistries.test_the_registries_are_exactly_as_frozen`;
* `TestE2RegistrationStepNotExecuted.test_no_binding_registration_happened_
  in_the_contract_phase`.
(The A4 reachability nodes — no live module references the FU4 surface, the
FU4 module is research-pure, no pricing path is activated, no vendor /
caller names — are STRENGTHENED, not moved: at registration the new adapter
module joins the allowed research surface, and the live-module / pricing /
runtime exclusions stand unchanged.)

In `tests/evaluation/semantic_v2/test_q3b5_p1_binding_replay.py`:
* `TestBindingDriftPins.test_the_2_1_binding_is_drift_pinned` (asserts
  `KNOWN_PRODUCTION_BINDINGS == {2.0/FU2, 2.1/FU3}`);
* `TestProductionAdapterUnchanged.test_the_codec_registry_still_knows_
  exactly_the_v1_and_2_0_bindings` (asserts the 2.1/FU3 binding is NOT in
  `SUPPORTED_CONTRACT_BINDINGS` and 2.0/FU2 IS);
* `TestProductionAdapterUnchanged.test_an_fu3_bound_payload_is_refused_by_
  the_production_codec` (STAYS TRUE post-registration — the FU3 payload is
  still refused, now at the codec's binding-disambiguation gate instead of
  the V2 adapter's strict check; the docstring records the moved failure
  point).

In `tests/research/test_semantic_decision_codec.py`:
* `TestEnvelopeIndependence.test_registry_lookup_is_explicit_and_fail_closed`
  (asserts `supported_contract_bindings() == (V1, 2.0/FU2)` and the
  single-adapter lookups; the single-lookup assertions stay true — the
  registration order keeps `SEMANTIC_V2_ADAPTER` first for the `(1, "V2")`
  pair — only the expected `supported_contract_bindings()` tuple gains the
  third entry).

In `tests/research/test_semantic_decision_replay.py`:
* `TestContractBindingGate.test_supported_bindings_are_exactly_the_frozen_
  v1_tuple` (the exact two-tuple assertion gains the third entry) and the
  node asserting `len(SUPPORTED_CONTRACT_BINDINGS) == 2` (→ 3).

No other node in any suite asserts the pre-registration registry state
(verified this session by inspection of the four suites above; the
cross-version corpus / capture / report refusal nodes are keyed on corpus
identity + prompt axis, not on the binding count, and stay unchanged).

---

# 2. Current version / binding matrix

## 2.1 The five-axis binding tuples (exactly as of the starting SHA)

Axes: `(semantic contract version, prompt version, input schema version,
output schema version, authority contract version)`.

| Binding | Owner | Codec-registered | Replay-registered | Harness-registered | Corpus sealed under it |
| --- | --- | --- | --- | --- | --- |
| `("V1","1.1",1,1,"SEMANTIC_AUTHORITY_V2_S2A_FU2")` | `research/semantic_decision_v1.py` `V1_CONTRACT_BINDING` | YES (V1 adapter) | YES | — (historical V1, not a harness binding) | — |
| `("V2","2.0",1,1,"SEMANTIC_AUTHORITY_V2_S2A_FU2")` | `research/semantic_decision_v2.py` `V2_CONTRACT_BINDING` | YES (V2 adapter) | YES | YES → "1.0.0" | 1.0.0 (`2c37ba08…`) |
| `("V2","2.1",1,1,"SEMANTIC_AUTHORITY_V2_S2A_FU3")` | `semantic/contract_v2_1.py` `V2_1_CONTRACT_BINDING` | NO (refused — pinned) | NO (refused — pinned) | YES → "1.1.0" | 1.1.0 (`14396eae…`) |
| `("V2","2.1",1,1,"SEMANTIC_AUTHORITY_V2_S2A_FU4")` | — does not exist yet (this design §3) | NO (refused — pinned) | NO (refused — pinned) | NO (no entry; no 1.2.0) | — (no artifact) |

## 2.2 Per-surface accepted bindings

* **Persistence codec** (`semantic_decision_codec.py`): decodes exactly the
  V1 + 2.0/FU2 bindings (the union of the two registered adapters'
  `supported_bindings`). Every other binding — including 2.1/FU3 and
  2.1/FU4 — is refused at dispatch / decode (pinned).
* **Replay** (`semantic_decision_replay.py`): replays exactly the same two
  bindings (`SUPPORTED_CONTRACT_BINDINGS`, derived). The FU2 / FU3
  delegation arms of the FU4 superset dispatch cover the historical tokens
  at the DERIVATION level (research), not at the record level: no persisted
  record bound to FU3 exists or can be constructed (the live record type
  pins FU2).
* **Qualification harness** (`corpus.py`): qualifies exactly the two
  production bindings, each sealed to its own corpus version (1.0.0 /
  1.1.0); the eight gates, the report contract section, the capture
  loaders, and the CLI all branch on exactly these two (drift-pinned, no
  literal copies outside the semantic layer's 2.1 owner).
* **Live runtime** (`runtime_v2.py`): executes the frozen 2.0 prompt builder
  on the pinned route; records under 2.0/FU2; `V2_AUTHORITY_QUALIFIED`
  False. No live 2.1 execution path exists (2.1 is qualification-capture
  only, via the harness runner).
* **Pricing**: `PRICING_ELIGIBLE_TIERS = {MACHINE_VERIFIED,
  AI_ASSISTED_COMPARABLE, HUMAN_CONFIRMED}`; `NEEDS_REVIEW` is never
  pricing-eligible (import-self-checked); no pricing path reads any FU3 /
  FU4 state (no live module references the FU3 / FU4 contract surfaces —
  lexical / AST guards).

## 2.3 The version axes in play (independent, each separately versioned)

| Axis | Current values | Owner |
| --- | --- | --- |
| Envelope schema version (persisted JSON format) | 1 | `semantic_decision_record.py` / `semantic_decision_codec.py` |
| Semantic contract version | V1, V2 | the adapters |
| Prompt version | 1.1 (V1), 2.0, 2.1 | `contract.py` / `contract_v2.py` / `contract_v2_1.py` |
| Input schema version | 1 (both V2 adapters) | the V2 case contract (`semantic_v2.py`) |
| Output schema version | 1 (the strict 7-key response) | `semantic_v2.py` |
| Authority contract token | FU2 (frozen), FU3 (frozen), FU4 (research-only) | `semantic_authority_v2.py` / `_fu3.py` / `_fu4.py` |
| Bundle-composition evidence schema | 3 (v1 + FU1 channel-content binding + FU2 embedded original result) | `semantic_authority_fu4.py` |
| Sales-unit extraction schema | 1 | `sales_unit_extraction.py` |
| Corpus schema / version | 1 / {1.0.0, 1.1.0} | `corpus.py` / `fixtures.py` |
| Capture schema / mode | 1 / {PRODUCTION_ROUTE, DIRECT_MODEL_QUALIFICATION} | `capture.py` / `direct_capture.py` |
| Policy schema / status | 1 / DRAFT (1.0.0-scoped) | `policy.py` |
| Manifest schema | 1 | `corpus.py` / `fixtures.py` |
| Report contract | 1 (the exact section key sets) | `report.py` |

---

# 3. Proposed FU4 binding and evidence-version pins

## 3.1 DEC-1 — the binding

The FU4 production binding is, exactly as the approved design's §7.1 / D12:

```
("V2", "2.1", 1, 1, "SEMANTIC_AUTHORITY_V2_S2A_FU4")
```

Axis by axis:

* **Semantic contract "V2"** — the final S2-C semantic contract (the
  `SemanticMatchCaseV2` input, the strict structured response, the V2
  evaluation / execution / derived semantics). Unchanged: FU4 governs the
  AUTHORITY layer downstream of the recorded decision; it is not a new
  semantic contract (the envelope dispatch key stays "V2" — the
  disambiguation design §4.3 relies on this).
* **Prompt "2.1"** — the approved, separately versioned Prompt 2.1 (system
  text digest `e2949e75…`; user rendering = the frozen 2.0 rendering +
  exactly the two approved annotation lines). **No new prompt version**
  (P3 §7.4: the 2.1 text names no authority token, describes no
  derivation, and asserts nothing FU4 contradicts; a 2.2 would be a
  phantom version — the 2.1 module's own import check refuses a version
  bump without a text change).
* **Input schema 1** — the recorded V2 input is byte-identical in shape
  (P3 D2: the composition facts are DERIVATION-INPUT records passed to the
  derivation, not case fields; the FU3 `TargetSalesUnitEvidenceV2`
  precedent).
* **Output schema 1** — the 7-key strict response (the Q3-B4 §5.6
  invariance: the output contract is identical under every binding).
* **Authority `SEMANTIC_AUTHORITY_V2_S2A_FU4`** — the separately versioned
  bundle-composition authority contract (P3 D1 / D12: the token is the
  derivation identity, the binding is the record / corpus / harness
  identity; both move together, and the existing 2.1/FU3 binding is NOT
  reused for changed authority semantics).

The binding constant is composed from the frozen exports (the P1
discipline: no literal token in source; drift-pinned by test) and is owned
by the semantic layer at registration (a research module cannot import the
semantic layer — dependency direction). **DEC-6:** the owner is
`product_intelligence/semantic/contract_v2_1.py`, extended alongside
`V2_1_CONTRACT_BINDING` (the existing constant byte-unchanged), with an
import self-check that the new binding moves ONLY the authority axis
relative to the existing 2.1 binding (the P1 self-check pattern). The
codec adapter (research layer) carries the MIRROR constants, drift-pinned
against the semantic-layer owner by test — the exact house pattern the V2
adapter uses for its prompt / route mirrors.

## 3.2 Sufficiency analysis — what the binding alone does and does not identify

The task's question: does the binding uniquely identify (i) the Prompt 2.1
semantic decision contract, (ii) the FU4 authority contract, (iii) the FU4
candidate composition evidence schema v3, (iv) the target-side composition
and quantity attestation schemas, (v) the frozen P2 extraction-result
schema and mapping, (vi) the deterministic derivation rules?

**Identified by the binding alone:**

1. **The Prompt 2.1 semantic decision contract** — YES. Axes (V2, 2.1, 1, 1)
   select, by the registered-contract discipline, exactly the frozen 2.1
   system text (a version IS its text — `SemanticPromptV2_1` refuses a
   foreign body), the exact user rendering, the input case shape (input
   schema 1 = the `SemanticMatchCaseV2` section contract), and the 7-key
   output contract. The historical prompt is deterministically
   reconstructable from the recorded case + the bound prompt axis (no live
   call).
2. **The FU4 authority contract** — YES. Axis 5 selects the derivation
   identity: `derive_authority_tier_for_contract_fu4`'s FU4 arm
   (`derive_authority_tier_fu4`), the `AuthorityDecisionV2FU4` record, the
   mirrored rule vocabulary, the two restrict-only ceilings, and the v3
   presentation gate. The derivation RULES themselves are the code of the
   FU4 module at its pinned SHA (the contract is the code; the binding
   names which code applies — the per-binding replay discipline, Q3-B4
   §6.5).
3. **The deterministic derivation rules** — YES (same mechanism as 2; the
   delegation identity of the FU2 / FU3 arms is pinned, so "the rules under
   the recorded token" is total and unambiguous for a record).

**NOT identified by the binding alone — the smallest additional evidence
metadata needed (DEC-2):**

4. **The bundle-composition evidence schema version (3)** — the binding
   names the authority token, but the evidence schema is versioned
   INDEPENDENTLY within it (v1 → v2 → v3 across Q3-B5-P4 / FU1 / FU2; the
   T5 discipline: any change is a new version, never a silent edit). A
   record must carry the schema version of every evidence document it
   presents. → **The FU4 payload's version-owned `authority` section
   (§4.2) carries the full canonical document of each evidence record —
   each document includes its own `schema_version` field (3) and its
   self-verifying digest** — and the adapter's decode pins
   `BUNDLE_COMPOSITION_EVIDENCE_VERSION_FU4` (drift-pinned against the FU4
   module) as the only constructible value. A v1 / v2 / unknown document is
   un-constructible (the FU4 constructor refuses) and undecodable (the
   adapter's strict section check refuses).
5. **The target-side composition + quantity attestation schemas** — same
   mechanism: `TargetSalesUnitEvidenceV2FU4.canonical()` /
   `QuantityCompletenessAttestationV2FU4.canonical()` each carry
   `schema_version: 3` + their self-verifying digests inside the
   `authority` section.
6. **The frozen P2 extraction-result schema (1) and the frozen mapping** —
   the EXTRACTION_RESULT_V1 candidate record embeds the EXACT original
   `SalesUnitExtractionResult`; its canonical document (inside the
   candidate record's document, inside the `authority` section) carries
   `schema_version: 1`, both self-verifying digests, and every cue with its
   full provenance. The mapping (`sales_unit_channel_from_extraction`) is
   FROZEN CODE — version-identified by the module's pinned SHA, not by any
   axis: the basis token `EXTRACTION_RESULT_V1` names the mapping's input
   schema by construction (the same discipline as the FU3 target record
   being a derivation input, not a binding axis). The adapter's decode
   pins `SALES_UNIT_EXTRACTION_SCHEMA_VERSION` (drift-pinned against
   `sales_unit_extraction.py`).
7. **The runtime route (provider / model provenance)** — the binding
   carries no route axis (neither does the 2.0/FU2 binding — the route is
   adapter-owned contract data, mirrored and drift-pinned to the runtime).
   → The FU4 adapter pins the same frozen route (amax / qwen3.8-27b
   primary, vllm-262k / Qwen3.6-27B-262K fallback) and enforces it over the
   recorded `execution` section's attempts exactly as the V2 adapter does.
8. **The corpus version (1.2.0) and the prompt-text digest** — these are
   HARNESS / REPORT identity, not record identity: the harness's
   `BINDING_CORPUS_VERSIONS` seal maps the binding → "1.2.0" (§5.1), and
   the report's `contract` section records the REAL 2.1 system-prompt
   digest (`e2949e75…`) + the binding + the runtime config identity
   (§5.5).

**Conclusion (DEC-2):** the proposed binding is SUFFICIENT as record-
contract identity; the smallest additional evidence metadata is (a) the
version-owned `authority` section of the FU4 payload (the three evidence
documents, each self-versioned and digest-sealed), and (b) the adapter-
owned schema-version pins (evidence schema 3, extraction schema 1) plus the
route mirror. **No new binding axis is added, and no existing record is
reinterpreted.**

## 3.3 The frozen inputs the binding must not move

The registration step's frozen set = the current tree MINUS the files it
owns (§10, per phase). In particular, the registration step does NOT move:
the FU4 module's derivation / dispatch / case-level signatures (the C8 /
F1 signature pins of the FU4 suite), the FU4 evidence schema value (3 — a
move would be a NEW schema version behind the same or a new token, per T5,
never a silent edit), the extraction schema (1), the S2-C channel, the FU3
/ FU2 modules, the 2.0 / 2.1 prompt texts, the V1 / V2 adapters and record
types, the eight gates, the DRAFT policy, or the committed 1.0.0 / 1.1.0
artifacts.

---

# 4. Codec / replay registration design

## 4.1 The extension point (as stated by the storage contract)

The `runs.SemanticDecisionRecord` row is storage, not interpretation: an
opaque payload + envelope `schema_version` (1) + whole-artifact
`payload_digest`. The codec's docstring and the model's docstring state the
extension point: a future semantic contract / binding reuses the row by
registering a new contract adapter — no model change, no migration, no data
rewrite. The FU4 registration is exactly this path, with ONE required
versioned amendment to the codec's dispatch surface (FIND-1, §4.3) that the
P3 design's §7.3 step 4 presupposed but did not specify.

## 4.2 The FU4 record adapter (NEW module)

**DEC-7:** the registration step adds a NEW research-layer module
(proposed name `product_intelligence/research/semantic_decision_v2_fu4.py`)
owning, and ONLY owning:

* the FU4 contract identity mirrors (semantic contract "V2", prompt "2.1"
  (mirrored, drift-pinned to `contract_v2_1`), input schema 1, output
  schema 1, authority `AUTHORITY_CONTRACT_VERSION_V2_FU4` (imported from
  the research export — same package, no mirror needed)), composed into
  the FU4 binding tuple (drift-pinned against the semantic-layer owner
  `V2_1_FU4_CONTRACT_BINDING`);
* the pinned route mirror (identical values to the V2 adapter's — the
  frozen qualified route identities; drift-pinned to `runtime_v2`);
* the `V2_AUTHORITY_QUALIFIED` mirror stays False — the FU4 adapter carries
  the SAME explicit qualification-boundary marker as the V2 adapter (the
  registration is NOT a qualification: the marker is pinned False and is
  NOT a registration deliverable);
* the FU4 typed record `SemanticDecisionRecordV2FU4` — the V2 record's
  field set (universal binding; contract identity; the exact recorded case;
  the recorded evaluation; the recorded execution provenance; the integrity
  digests) with:
  * the constructor's exact-binding check pinning the FU4 binding (a
    record bound to any other tuple is un-constructible — the anti-
    reinterpretation invariant, mirror of the V2 record's frozen pin);
  * the V2 evaluation / execution coherence rules (identical — the same
    output contract, the same route pin, the same attempt discipline);
  * the FU4 `derived` section values (the full `AuthorityDecisionV2FU4`
    audit surface: tier, fired rules, product-evidence quality,
    relationship authority, identity-resolution bound, sales-unit
    authority, + the six bundle-axis audit fields — exactly None for
    non-bundle channels);
  * the NEW version-owned `authority` evidence fields:
    `candidate_composition: CandidateBundleCompositionEvidenceV2FU4 | None`
    (the v3 record — digest-bound, the embedded original extraction result
    WITHIN its `evidence_digest`),
    `target_evidence: TargetSalesUnitEvidenceV2FU4 | TargetSalesUnitEvidenceV2 | None`
    (DEC-8: the three recorded shapes — an explicit FU4 record, the frozen
    FU3 record (read as composition-ABSENT under FU4, D18), or None = the
    default single unit; the record discriminates them explicitly —
    §4.2a),
    `quantity_attestation: QuantityCompletenessAttestationV2FU4 | None`;
  * the self-verifying section digests: `input_digest` = canonical over
    `{binding, contract, case}` (the V2 definition — the contract section
    carries the FU4 binding, so an FU4 input digest is distinct from a
    same-case FU3 / FU2 input digest by exactly the recorded authority
    axis), `output_digest` = canonical over `{evaluation, execution,
    authority, derived}`.
* the strict FU4 payload codec (the exact FU4 section key sets — §4.2a;
  fail closed; no floats; the strict evidence-document decode — §4.2b);
* the FU4 pure zero-live replay (§6) returning
  `SemanticDecisionReplayV2FU4` (the record, the reconstructed identity
  context / semantic evaluation / provenances / product evidence, the
  reconstructed authority evidence, the re-derived `AuthorityDecisionV2FU4`
  proved to agree with the stored derived section, the case, and the
  contract binding);
* the registered instance `SEMANTIC_V2_FU4_ADAPTER` (envelope schema 1,
  semantic contract "V2", `supported_bindings = (FU4 binding,)`, record
  type = the FU4 record) — appended to the codec registry AFTER the V2
  adapter (registration order preserved: V1, V2, V2-FU4 — §4.3).

**FIND-2:** the FU4 record is a NEW type. The frozen `SemanticDecision
RecordV2` constructor exactly pins prompt "2.0" + authority FU2 — an FU4-
bound record cannot be, or be decoded as, a V2 record. Reusing the V2
record type (by relaxing its pin) is forbidden: `semantic_decision_v2.py`
is a byte-frozen input of the registration step (its suite + the FU4 A1
pin stand), and the per-binding discipline (Q3-B4 §6.1 item 5) requires
each binding's record to carry the derived snapshots OF ITS TOKEN under a
record type that cannot be mis-bound.

### 4.2a The FU4 payload's version-owned sections (exact shapes)

The universal framing is unchanged: top-level `schema_version: 1`,
`binding` (the exact universal keys), `contract` (the exact five keys,
recording the FU4 binding). The version-owned sections:

* `case` — the EXACT V2 case section (input schema 1; the FU4 adapter
  reuses the V2 adapter's strict case decode — the recorded input is
  byte-identical in shape, D2);
* `evaluation` — the EXACT V2 evaluation section (output schema 1);
* `execution` — the EXACT V2 execution section (the pinned route);
* `derived` — the FU4 derived section, the exact key set:
  `{product_evidence_quality, relationship_authority, authority_tier,
  fired_rules, identity_resolution_bound, sales_unit_authority,
  quantity_axis_state, candidate_composition_state,
  target_composition_state, candidate_completeness_attestation_digest,
  target_completeness_attestation_digest, quantity_attestation_digest}`
  (the `AuthorityDecisionV2FU4` audit surface, values from the bounded
  enums; the bundle-axis fields explicit null for non-bundle channels);
* `authority` — the NEW FU4 authority-evidence section, the exact key set:
  `{candidate_composition, target_evidence, quantity_attestation}`:
  * `candidate_composition: object | null` — null when no candidate
    composition evidence was presented (the non-bundle / channel-
    UNAVAILABLE / no-bundle-record shapes); otherwise the record's FULL
    canonical document (the `CandidateBundleCompositionEvidenceV2FU4.
    canonical()` key set — including `schema_version: 3`, the embedded
    attestation's canonical (with its `attestation_digest`), and — for the
    EXTRACTION_RESULT_V1 basis — the embedded original result's canonical
    (with `schema_version: 1`, both digests, every cue)) PLUS
    `evidence_digest`;
  * `target_evidence: object | null` — null = the default single unit
    (NO target record presented); otherwise `{schema: "frozen_fu3" |
    "fu4_v3", document: …}` — `"frozen_fu3"`: the FU3 record's three
    fields (`form`, `quantity`, `source`) as recorded; `"fu4_v3"`: the
    `TargetSalesUnitEvidenceV2FU4.canonical()` document (with
    `schema_version: 3`) PLUS `evidence_digest`;
  * `quantity_attestation: object | null` — null or the
    `QuantityCompletenessAttestationV2FU4.canonical()` document (with
    `schema_version: 3`) PLUS `attestation_digest`.

  The `schema` discriminator on `target_evidence` is DEC-8: an explicit,
  bounded, fail-closed discriminator (an unknown discriminator is a codec
  error; a `"fu4_v3"` document that does not reconstruct a digest-
  verifying record is a codec error; a `"frozen_fu3"` document whose
  fields violate the frozen FU3 constructor is a codec error). The
  discriminator records WHICH record shape the derivation consumed —
  replay re-presents the same shape (D18's composition-ABSENT reading of a
  frozen record is a property of the FU4 token + the frozen record, not of
  the payload).

* `integrity` — `{input_digest, output_digest}` (the V2 section, the FU4
  digest definitions above).

### 4.2b The strict evidence decode (fail closed at every level)

The `authority` section decodes into TYPED records through the FU4
constructors (the constructor is the validator — the house pattern):

1. each embedded document is decoded field-by-field against the EXACT
   canonical key set (missing AND extra keys refused; unknown enum values
   refused; the digest shape checks stand);
2. the typed record is reconstructed and its `verify()` / constructor
   digest re-verification runs (a tampered document — any field edited, a
   digest not recomputed, a superseded `schema_version`, a missing embedded
   extraction result — is refused with `SemanticDecisionCodecError`);
3. the round-trip check: the reconstructed record's `canonical()` must
   EQUAL the stored document (a document that decodes to a different
   record is refused — no two documents, one record);
4. the attestation digests (embedded completeness attestations, the
   quantity attestation) are re-verified within (step 2 covers them —
   they are inside the record digests).

## 4.3 FIND-1 — the codec dispatch incompatibility and the required versioned amendment

**The incompatibility (exact).** The universal codec dispatches decode on
the TWO-axis pair `(envelope schema version, semantic contract version)`:
`registered_semantic_contract_adapter` returns the FIRST registered
adapter matching the pair, and `decode_semantic_decision_record` delegates
to it. The FU4 binding's semantic-contract axis is "V2" — the SAME pair
`(1, "V2")` as the existing V2 adapter. With both adapters registered,
every V2-contract payload dispatches to `SEMANTIC_V2_ADAPTER` (registered
first), whose strict decode reconstructs a `SemanticDecisionRecordV2`,
whose constructor refuses the FU4 binding (FIND-2) — the FU4 adapter is
UNREACHABLE. Registering a second "V2" adapter without amending the
dispatch therefore accomplishes nothing (an FU4-bound payload is refused
exactly as today), and re-keying the FU4 binding under a NEW semantic-
contract version string (e.g. "V2_FU4") is FORBIDDEN: it would make the
recorded payload's `contract.semantic_contract_version` disagree with the
binding's axis 0 (the payload must record the contract it was produced
under — "V2" — and the envelope dispatch key is that recorded value), i.e.
a silent reinterpretation of the version axes.

**DEC-9 — the required versioned amendment (the smallest safe one).**
Amend `semantic_decision_codec.py`'s decode dispatch from first-match-on-
pair to **claim-based disambiguation on the full recorded five-tuple
binding**, mirroring the replay module's EXISTING per-binding selection
(`_adapter_for_binding`: the registered adapter whose `supported_bindings`
contain the record's binding):

* the universal envelope framing is UNCHANGED (the declared envelope
  version agreement, the exact universal binding section, the contract
  section's presence, the no-float walk);
* the dispatch reads the FULL recorded contract section (the five axes —
  the exact key set every adapter already enforces; reading them at the
  envelope level adds no new shape assumption — the same five keys, the
  same types) and computes
  `claiming = [a for a in registry if a.envelope_schema_version == sv and
  binding in a.supported_bindings]`;
* `len(claiming) == 1` → that adapter decodes (for EVERY currently
  registered binding — V1, 2.0/FU2, and, post-registration, 2.1/FU4 — the
  claiming set is a singleton, so the resolution is IDENTICAL to today's
  first-match resolution: behavior-preserving by construction);
* `len(claiming) == 0` → refused with the existing bounded
  "no registered contract adapter interprets this payload" error (an
  unknown / future / cross-binding payload — e.g. 2.1/FU3, 2.0/FU4, 2.1/
  FU9, 2.2/anything — fails closed exactly as today);
* `len(claiming) > 1` → refused with a distinct bounded contract-registry-
  defect error (two adapters claiming one binding is a registry
  inconsistency; unreachable by construction — the bindings are disjoint —
  but fail closed, never first-match);
* the public single-adapter lookup `registered_semantic_contract_adapter`
  KEEPS its first-match semantics (it is an introspection helper; the
  registration order V1, V2, V2-FU4 keeps `registered_semantic_contract_
  adapter(1, "V2") is SEMANTIC_V2_ADAPTER` true — the existing node stands);
* the registry tuple gains the FU4 adapter as its THIRD entry (additive;
  `supported_contract_bindings()` = the union — V1, 2.0/FU2, 2.1/FU4 —
  which the replay module picks up automatically: `SUPPORTED_CONTRACT_
  BINDINGS` is DERIVED from the codec registry, so **`semantic_decision_
  replay.py` needs NO change** — its five-tuple gate + `_adapter_for_
  binding` selection already implement the exact post-amendment
  semantics);
* the persistence service (`execution/semantic_decision_persistence.py`)
  and the runs model need NO change (they call the universal entry points
  only).

**Behavior-preservation proof obligation (R1 acceptance, §10):** for every
payload that decodes today (V1 or 2.0/FU2, well-formed or malformed), the
amended codec selects the same adapter and raises the same error class;
the existing codec / replay / decision-record suites pass, with the
recorded node corrections of §1.7 (the exact expected-tuple assertions
gain the third entry) and no other byte changed. The amendment is a
versioned contract change to the codec module (its digest moves; the FU4
A1 pin set re-pins per §1.7) — recorded, reviewed, and gated like every
prior registration (P1's harness extension, P4's research export block).

**Rejected alternative (recorded):** an adapter failover loop (try the
first adapter; on a binding-mismatch decode error, try the next). Rejected
because it introduces decode-error MASKING (a malformed payload's exact
failure stage depends on adapter order), weakens the bounded error
identity, and makes the single-adapter lookup's semantics lie. The claim-
based disambiguation keeps the decode single-pass and the error stage
deterministic.

## 4.4 Replay registration (consequence, not change)

After R1: `SUPPORTED_CONTRACT_BINDINGS` = exactly
`(V1, 2.0/FU2, 2.1/FU4)`. `replay_semantic_decision` (byte-unchanged)
gates on the record's recorded binding and dispatches by five-tuple claim:
the FU4 record replays through `SEMANTIC_V2_FU4_ADAPTER.replay` (§6); the
V1 / V2 records replay through their frozen adapters exactly as today; a
2.1/FU3 record cannot exist (no adapter can construct it — FIND-2) and a
2.1/FU3-shaped raw binding is refused at the gate. **No historical record
is upgraded to FU4:** a 2.0/FU2 record's binding selects the V2 adapter
(the FU4 adapter does not claim it); the FU4 replay requires the FU4
record TYPE (type-distinguishable); and the FU4 dispatch's FU2 / FU3 arms
delegate to the frozen derivations (delegation identity pinned) — the
historical tokens interpret historical records under their historical
rules, byte-identically.

## 4.5 The semantic-layer binding constant (R2)

`product_intelligence/semantic/contract_v2_1.py` gains, alongside
`V2_1_CONTRACT_BINDING` (byte-unchanged): the FU4 successor binding
constant (composed from `SEMANTIC_CONTRACT_VERSION_V2`,
`SEMANTIC_PROMPT_VERSION_V2_1`, `SEMANTIC_INPUT_SCHEMA_VERSION_V2`,
`SEMANTIC_OUTPUT_SCHEMA_V2`, and the research export
`AUTHORITY_CONTRACT_VERSION_V2_FU4` — no literal token), with import
self-checks: the FU3 binding unchanged; the FU4 binding moves ONLY the
authority axis relative to the FU3 binding; the FU4 token distinct from
the FU2 / FU3 tokens. The research FU4 adapter's mirror is drift-pinned
against this owner by test (the P1 discipline).

---

# 5. Corpus and qualification strategy

## 5.1 DEC-3 — corpus versioning: the 1.2.0 binding-only re-seal (required)

**Is corpus 1.2.0 required? YES** — for the harness's seal discipline, not
for the model: the harness qualifies EXACTLY the known production bindings,
and a corpus document's binding must be one of them at the version sealed
under that binding (`corpus.load_corpus` — "a corpus version is only
interpretable under the production binding it was sealed with (cross-
version replay refusal)"). An FU4-bound baseline report (the R2 deliverable
of P3 §7.3 step 5) must seal against a corpus the FU4 binding seals; the
only corpus the FU4 binding seals is a NEW version. Qualifying FU4
directly against the committed 1.1.0 corpus is REFUSED by design: 1.1.0
is sealed under 2.1/FU3 (its digest `14396eae…` binds that tuple), the
`zero_contract_version_mismatch` gate pins the binding against
`KNOWN_PRODUCTION_BINDINGS`, and the report contract re-binds to the
corpus's exact binding — presenting an FU4 report over the FU3-sealed
corpus is a cross-lineage combination the harness exists to refuse.

The re-seal (P3 D14, the P1 1.1.0 precedent executed verbatim):

* NEW artifacts `evaluation/semantic_v2_qualification/corpus_2_1_fu4.json`
  + `manifest_2_1_fu4.json` (the P3 §7.3 step 2 proposed names);
* derived from the sealed 1.1.0 document by moving EXACTLY
  `{corpus_version → "1.2.0", semantic_contract_binding → the FU4 tuple,
  corpus_digest → recomputed over the re-sealed state}`;
* 56/56 per-case documents (payload, expected outcome, label, challenge
  metadata, sealed per-case `case_digest`) BYTE-IDENTICAL to 1.1.0
  (mechanical proof by test — every per-case digest verified against the
  1.1.0 document); `label_revisions` stays EMPTY (no label moved);
  `corpus_id`, `corpus_schema_version`, `corpus_label`, `created_utc`
  unchanged;
* `fixtures.py` gains `CORPUS_VERSION_2_1_FU4 = "1.2.0"` +
  `build_corpus_2_1_fu4_document()` (mirroring `build_corpus_2_1_
  document`); `corpus.py`'s `BINDING_CORPUS_VERSIONS` gains the third
  entry `((V2, 2.1, 1, 1, FU4) → "1.2.0")` and `KNOWN_PRODUCTION_BINDINGS`
  becomes EXACTLY the three production bindings (drift-pinned — no literal
  copies); `cli.corpus-build` gains the 1.2.0 generation (regenerating
  from the source must reproduce the committed re-seal byte-for-byte —
  pinned by test, the P1 property);
* the committed 1.0.0 / 1.1.0 artifacts + manifests + the DRAFT policy
  re-pin byte-identical (the A1 pin set).

## 5.2 Binding-only re-seal versus additional Bundle-specific cases

**DEC-4: the registration step reseals BINDING-ONLY. No case is added,
changed, relabeled, or re-expected.** Rationale (recorded, not
re-litigable by the implementation):

* The corpus labels the MODEL's semantic output (decision, conflict
  classes, missing dimensions) — it does NOT label authority tiers or
  composition states (the Q3-B4 §5.4(3) property: the firewall family
  changes no label). FU4 changes the DETERMINISTIC authority derivation
  downstream of the recorded decision; the model's duties (and therefore
  its labels) are unchanged by the authority token (P3 §7.4 — the prompt
  is binding-agnostic for the model).
* The committed corpus contains NO attested-composition case (§1.5): the
  three sales-unit cases are all conflict shapes against the default
  single-unit target. Adding completeness-marker bundle cases (e.g.
  "bundle: 2x RAM + 1x CPU, complete list") would add MODEL-side coverage
  only (the labels would be NO_MATCH + BUNDLE under the absolute rule,
  binding-agnostic) — and every new expected answer is an evaluation-truth
  move requiring the A/B/C/D statement and an independent label source
  (CLAUDE.md: "The corpus in evaluation/ is the benchmark … changing an
  expected answer requires stating which of these it is"). That governance
  is a SEPARATE, separately gated corpus step (a 1.2.x / 1.3.0 case
  addition with explicit label approval) — OPEN-3, §11 — NOT a
  precondition of FU4 registration.
* The FU4 PROVEN path (U19 / U20 — attested equal compositions) is
  exercised COMPLETELY at the research (deterministic) level by the FU4
  suite (C5, B11, B12, D1 rows — 224 nodes at the starting SHA) over
  offline recorded-input constructions. Model-corpus coverage of that path
  would measure the MODEL (which is token-agnostic for the prompt), not
  the FU4 authority derivation.

Consequence (recorded): under the binding-only 1.2.0, every bundle case
the corpus contains derives, through the FU4 dispatch, EXACTLY the unit
state the frozen FU3 dispatch derives over the same recorded channel
(0032 / 0033: non-bundle arms — delegated byte-identically; 0034: the
bundle arm's form axis — CONTRADICTED against the default single-unit
target, U9, as under FU3). The no-capture baseline's gate arithmetic is
therefore binding-agnostic BY CONSTRUCTION over the committed shapes (the
P3 §7.3 step 5 property; verified row-by-row at R2).

## 5.3 Frozen expected labels versus newly authorized labels

All 56 expected labels are FROZEN in 1.2.0 (binding-only re-seal;
`label_revisions` empty; per-case digests byte-identical to 1.1.0, which
itself is byte-identical to 1.0.0 per-case). There are NO newly authorized
labels in the registration step. Any future label change follows the
corpus governance of record (a numbered `label_revisions` entry with the
A–D reason class + statement + before/after digests, under a NEW corpus
version — the loader enforces the numbering; a binding-only re-seal can
never carry label revisions).

## 5.4 The two metric surfaces (the mandated distinction)

**DEC-5: semantic-model performance and deterministic FU4 authority
correctness are MEASURED ON SEPARATE SURFACES, and the registration step
must keep them separate in every report and in every acceptance
statement.**

### 5.4.1 Semantic-model performance (the harness surface — binding-agnostic for 2.1)

The EXISTING harness metric surface, UNCHANGED (no threshold added, moved,
or relaxed):

* the per-model evaluation (authoritative / ambiguous / contract-negative
  slices; the FALSE_MATCH / FALSE_NO_MATCH / ABSTAIN_ON_DEFINITE /
  DEFENSIBLE / OUTSIDE_DEFENSIBLE verdicts; the `commercial_sales_unit_
  safety` CRITICAL severity class);
* the metrics: match_precision (authoritative evaluated only), match_
  recall, valid_structured_response_rate, eligible_coverage, plus the
  visibility slices (ambiguous defensible / outside, contract-negative
  rejection correctness, runtime-failure status counts);
* the eight MANDATORY hard safety gates (the names and the fail-closed
  semantics unchanged; the `zero_contract_version_mismatch` gate pins the
  THREE known production bindings at R2, its detail text branching on the
  binding as today);
* the decision ladder (POLICY_PENDING until an applicable APPROVED policy
  exists — §5.6).

Model performance over the 2.1 binding is IDENTICAL in expectation across
the FU3 and FU4 bindings (same prompt text, same input schema, same 7-key
output — the authority axis is downstream of the recorded decision). The
2.1-lineage capture evidence qualified under corpus 1.1.0 (the Q3-C
lineage) therefore remains the model-side evidence for the 2.1 prompt; an
FU4-lineage model capture over 1.2.0 (a FUTURE live step — OPEN-4) would
re-verify the same labels under the new seal. The registration step
performs NO capture and NO model call.

### 5.4.2 Deterministic FU4 authority correctness (the research + replay surface)

FU4 authority correctness is a DETERMINISTIC property, verified offline,
independently of any model output:

* **Authority derivation accuracy** — the FU4 decision table (U0–U21) over
  the full adversarial shape set: the corrected D6 conjunction (form
  before composition; ESTABLISHED on both sides via independent
  attestations; textual agreement; the determined quantity axis
  CONSISTENT / BOTH_UNPUBLISHED / ATTESTED_NOT_MATERIAL / CONTRADICTED /
  UNDETERMINED), the fail-closed arms (missing / partial /
  completeness-unknown ⇒ UNPROVEN; the asymmetric unattested gap ⇒
  UNPROVEN; the materially established difference ⇒ CONTRADICTED), and the
  non-bundle delegation (byte-identical to the frozen FU3 derivation).
  Exercised by the FU4 suite's C / D rows (224 nodes at the starting SHA)
  and re-exercised at R1 over the registered record (decode → re-derive →
  agree).
* **False-PROVEN and false-automatic-comparable detection** — the Q3-B4
  §4.1 invariant under FU4: `SalesUnitAuthorityV2 ∈ {UNPROVEN,
  CONTRADICTED}` ⇒ NEVER `AI_ASSISTED_COMPARABLE`, for every model
  decision / confidence / identifier substate / provenance / conflict-
  class combination (the restrict-only ceilings `CEILING_SALES_UNIT_NOT_
  PROVEN` / `CEILING_SALES_UNIT_CONTRADICTED`; the constructor invariants
  make the exposure un-constructible; the exhaustive restrict-only sweep
  over the FU4 decision type — the FU3 suite's sweep precedent, extended;
  the false-PROVEN defect shape of Q3-B5-P4-FU2 — the forged self-
  consistent ESTABLISHED record over a marker-free publication — is
  refused at the presentation gate, pinned at B12).
* **Evidence integrity** — the v3 association chain (embedded result
  integrity; anchor equality; frozen P2 mapping equality; re-composition
  equality), the attestation digest self-verification, the record
  `evidence_digest` re-verification, the round-trip document identity
  (§4.2b), the row-level `payload_digest` anchor.
* **Replay determinism** — §6: equal decoded records ⇒ equal re-derivation
  ⇒ exact agreement with the stored derived section; `encode(decode(
  payload)) == payload`; byte-identical historical replay (R1
  acceptance).
* **Provider / model provenance** — the pinned route over the recorded
  execution section (a non-pinned provider/model in an FU4 record is a
  contract violation at construction / decode; the harness capture loaders
  enforce the same frozen route identities, unchanged).
* **Primary / fallback independence** — the harness's per-model projection
  is unchanged: one capture run, per-model views (a successful primary
  finalizes the case; the primary model's PASS never qualifies the
  fallback; the fallback model's view counts a primary-answered case as
  not invoked). The registration step adds no routing behavior.

## 5.5 The offline no-capture baselines (R2 deliverable)

NEW committed no-capture baseline reports for the FU4 binding over BOTH
pinned candidates (the P1 arithmetic — the committed baselines are
no-capture; the decision POLICY_PENDING; the authority section
`granted: false` + `v2_authority_qualified: false` + the existing note
text; the contract section bound to the FU4 tuple with the REAL 2.1
system-prompt digest `e2949e75…`): proposed directory
`evaluation/semantic_v2_qualification/reports/q3b5_p5_baseline_1_2_0/`
(four report files — `no-capture_amax_qwen3.8-27b__report.{json,md}`,
`no-capture_vllm-262k_Qwen3.6-27B-262K__report.{json,md}`). The REPORT
SCHEMA IS UNCHANGED (the exact section key sets stand; `report.py` gains
only the third-binding branch in `_contract_section` — the binding's
authority axis in the section, the 2.1 prompt digest, the runtime config
identity as today). The committed 1.0.0 / 1.1.0 baselines re-pin
byte-identical; the cross-version report refusal matrix extends
(a committed 1.2.0 report refused on the 1.1.0 / 1.0.0 corpora and vice
versa — the `verify_report` corpus-binding check, unchanged mechanism).

## 5.6 DEC-4b — exact policy approval requirements

* The EXISTING DRAFT policy (`draft-1`, applicable to corpus 1.0.0 ONLY,
  `approved: false`) is UNCHANGED. Its four proposed thresholds
  (match_precision_min 0.99, match_recall_min 0.90,
  valid_structured_response_rate_min 0.99, eligible_coverage_min 1.0) are
  a DRAFT proposal — NOT finalized acceptance thresholds — and the
  registration step MUST NOT modify, extend, or approve it, and MUST NOT
  introduce any threshold for 1.2.0.
* A QUALIFIED decision over corpus 1.2.0 requires an APPROVED policy
  applicable to `(PI-SEMANTIC-V2-QUALIFICATION, "1.2.0")` — the policy
  contract's exact requirements: `status: "APPROVED"`,
  `approval.approved: true`, a named `approved_by`, a valid UTC
  `approved_utc`, the EXACT four-threshold vocabulary (the values are a
  governance decision — this design neither proposes nor freezes them),
  and the applicability binding to the 1.2.0 corpus identity. Until such a
  policy exists, every FU4-lineage qualification decision is
  POLICY_PENDING (the ladder: safety gates > policy approval > coverage >
  thresholds). This extends the documented F-4 debt (the DRAFT policy is
  inapplicable to 1.1.0) to the FU4 lineage: the policy-governance step is
  OWED by every 2.1-successor corpus version, is separately gated, and is
  NOT part of the registration step.
* The eight hard safety gates are MANDATORY and non-configurable — they
  bind the FU4 lineage exactly as they bind the others (a gate failure is
  NOT_QUALIFIED regardless of the policy state).

---

# 6. Deterministic replay algorithm (FU4)

`replay_semantic_decision` (byte-unchanged) gates the record's EXPLICITLY
RECORDED five-tuple binding against `SUPPORTED_CONTRACT_BINDINGS` (post-
R1: V1, 2.0/FU2, 2.1/FU4) and dispatches to the claiming adapter. The FU4
adapter's `replay` performs, for one decoded `SemanticDecisionRecordV2FU4`
(each step fails closed with `SemanticDecisionReplayError` /
`SemanticDecisionCodecError` as noted — a missing, unknown, inconsistent,
or tampered evidence NEVER yields a decision):

1. **Exact-binding gate (adapter-owned).** The record's contract section
   must equal the FU4 binding constant (enforced at construction; the
   replay re-asserts it — a record that could not be constructed otherwise
   is a registry defect; fail closed).
2. **Load the exact recorded semantic input / output.** The recorded case
   (the `SemanticMatchCaseV2` — constructor-re-validated: the S2-A context
   legitimacy, the UNCERTAIN-only entry point, the frozen requirement-
   table agreement, the authority-side evidence support), the recorded
   evaluation (the strict structured output — the reason-code coherence
   rules re-run by the record constructor), the recorded execution
   provenance (the attempts on the pinned route, the fallback
   discipline).
3. **Load the complete FU4 derivation evidence.** From the `authority`
   section (already strict-decoded + digest-verified at construction,
   §4.2b): the candidate composition record (v3 — for the EXTRACTION_
   RESULT_V1 basis WITH the embedded original `SalesUnitExtractionResult`
   and its two self-verifying digests), the target evidence (the
   discriminator-selected shape), the quantity attestation (when
   present).
4. **Verify every relevant evidence digest and schema version.** The
   record's `verify()` (the `evidence_digest` over the full record
   INCLUDING the embedded attestation and the embedded original result),
   the embedded attestation's `attestation_digest` self-verification, the
   embedded original result's `verify_integrity()` (BOTH stored digests
   recomputed + cue-span containment), the schema-version pins (evidence
   3; extraction 1) — a tampered or superseded document produces no
   derivation input (`BundleCompositionEvidenceIntegrityError` / codec
   error).
5. **Verify candidate / channel / extraction association.** The derivation
   itself is the verifier (no private-gate re-implementation at replay):
   the presentation gate re-runs over (decoded candidate record, the
   RECORDED channel from the case) — the channel-content-digest binding,
   the RECORDED_CHANNEL exact-construction check, and the v3 four-step
   original-result chain (embedded integrity; anchor equality; the frozen
   P2 mapping EQUALS the recorded channel; the recomputed composition
   EQUALS the complete record) — plus the target evidence gate (the
   attestation coherence over the target record). A cross-listing
   substitution, a wrong embedded result, or a forged association is
   refused here — NO unit is derived from it.
6. **Recompute the FU4 authority decision.** `derive_authority_tier_
   for_contract_fu4("SEMANTIC_AUTHORITY_V2_S2A_FU4", identity_context,
   semantic_evaluation, context_provenances, product_evidence,
   human_review=None, sales_unit_channel=<the recorded channel>,
   target_unit_evidence=<the decoded target shape>, candidate_composition=
   <the decoded record>, quantity_attestation=<the decoded attestation>)`
   — the token selects the FU4 arm (the historical arms are unreachable
   under this token by construction); the human overlay is NOT replayed
   (the overlay is a later workflow concern — the recorded derived
   snapshots were produced without it, exactly as under the V2 replay).
   The frozen relationship-requirement / product-evidence-quality /
   relationship-authority derivations re-run as under the V2 replay (the
   derived section carries them).
7. **Compare the replayed decision with the recorded decision.** EVERY
   field of the re-derived `AuthorityDecisionV2FU4` must EXACTLY agree
   with the stored `derived` section: tier, fired rules (the FU4
   vocabulary), product-evidence quality, relationship authority,
   identity-resolution bound, sales-unit authority, quantity-axis state,
   candidate / target composition states, the three attestation digests —
   plus the requirement / quality / agreement checks of step 6's frozen
   derivations (the V2 replay's derived-agreement proof, extended to the
   FU4 audit surface). Any disagreement (a stored snapshot from another
   contract, a tampered derived section, a derivation that fails closed on
   the recorded inputs) is a `SemanticDecisionReplayError` naming the
   disagreeing fields.
8. **Return** `SemanticDecisionReplayV2FU4` (the record, the
   reconstructed context / evaluation / provenances / product evidence,
   the reconstructed authority evidence, the proved authority decision,
   the case, the contract binding) — zero live AI calls, zero provider /
   network calls by construction (the module is import-self-checked: the
   research-pure discipline of the FU4 suite's A4 node, extended to the
   adapter).

**Historical FU2 / FU3 replay — byte-compatible and semantically
unchanged.** The V1 adapter, the V2 adapter, and their record types are
byte-frozen inputs of the registration step (digest-pinned at R1). Every
persisted historical record (V1; 2.0/FU2) decodes under the same adapter,
through the same section codec, into the same typed record, and replays
under the same frozen derivation with the same derived-agreement proof —
the R1 acceptance includes a byte-compatibility row over the existing
historical replay fixtures (the `tests/research/test_historical_replay*.py`
suite passes unchanged). The 2.1/FU3 binding remains a harness-only
binding (no record adapter claims it — unchanged by the registration).
**No historical record is silently upgraded to FU4:** the upgrade is
unrepresentable — a record's binding is recorded inside its
`input_digest`; a 2.0/FU2 record's binding does not claim the FU4
adapter; re-encoding a historical record under the FU4 binding would
change its contract section (hence its input digest) and fail its own
integrity verification. The ONE deliberately coexisting semantic
difference (same recorded inputs, different token ⇒ different bundle
state — the A7 two-token row) extends to three tokens at R1 (FU3 arm ⇒
the frozen count-based behavior; FU4 arm ⇒ the corrected D6 conjunction;
FU2 arm ⇒ the frozen derivation with no unit input) — pinned as
documented per-binding behavior, never drift.

---

# 7. Authority / pricing firewall — isolation proof obligations

The exact boundaries that prevent offline FU4 records from influencing live
production, each with its ENFORCEMENT POINT and its PROOF OBLIGATION at the
registration step (all obligations pinned by test; all standing UNCHANGED
in substance — the registration adds the FU4 lineage to the same
firewall):

1. **`V2_AUTHORITY_QUALIFIED = False`** — enforcement: the two pinned
   constants (`research/semantic_decision_v2.py`, `semantic/runtime_v2.
   py`) + the FU4 adapter's own mirror. Proof: the A4 node (both
   locations False; the FU4 record type's marker False) re-pinned at R1 /
   R2 — the registration does NOT flip it (qualification success under
   the FU4 binding, when it ever occurs, is a SEPARATE governance event
   with its own marker flip + consumer guard — AD-Q3B4-6 / W1).
2. **Historical authority tokens** — enforcement: the frozen FU2 / FU3
   modules (byte-pinned); the V1 / V2 adapters (byte-pinned); the FU4
   dispatch's delegation arms (delegation identity pinned — same inputs ⇒
   same outputs / same exceptions). Proof: the historical suites pass
   unchanged (the 98-node FU3 suite, the extraction suites, the
   historical replay suites, the P1 binding-replay suite modulo the
   recorded §1.7 corrections); the A2 delegation-identity rows stand; the
   three-token coexistence row (R1 new).
3. **Existing live record binding** — enforcement: the live V2 record
   type's constructor pin (prompt "2.0", authority FU2 — un-constructible
   under any other binding); the live runtime's frozen 2.0 builder
   (`runtime_v2.SEMANTIC_PROMPT_VERSION_V2 == "2.0"` drift-pinned). Proof:
   the A4 node "the live record type still pins the FU2 token" stands
   byte-for-byte; `runtime_v2.py` is a byte-frozen input of BOTH R1 and
   R2 (the registration wires NO live path — no live execution under 2.1/
   FU4 exists or is created).
4. **Production pricing eligibility rules** — enforcement:
   `PRICING_ELIGIBLE_TIERS` (the frozen constant; the import self-check
   that NEEDS_REVIEW is excluded); the aggregation / matching surfaces
   (own no FU3 / FU4 symbol — the lexical guards). Proof: the A4 node
   "no V2 pricing path is activated" stands (the aggregation surface is
   byte-pinned; `NEEDS_REVIEW not in PRICING_ELIGIBLE_TIERS`).
5. **`NEEDS_REVIEW` as non-pricing-eligible** — enforcement: the same
   frozen constant + self-check + the FU4 ceilings (a would-be
   AI_ASSISTED_COMPARABLE with an UNPROVEN / CONTRADICTED unit is capped
   at NEEDS_REVIEW; the cap tier is never pricing-eligible). Proof: the
   D1 / D3 rows stand under the registered record; the exhaustive
   restrict-only sweep over the FU4 decision type (R1 new node).
6. **Human review and HARD_CONFLICT precedence** — enforcement: the
   frozen derivation's precedence (HARD_CONFLICT > HUMAN_CONFIRMED > AI);
   the FU4 ceilings never lift, never touch MACHINE_VERIFIED, never fire
   outside the automatic tier; the overlay is explicit / run-scoped /
   persisted / auditable and OUTSIDE the FU4 replay (step 6,
   human_review=None). Proof: the D2 rows (a firewall-capped bundle
   candidate confirmed derives HUMAN_CONFIRMED; a model-reported
   ALWAYS_HARD BUNDLE conflict still supersedes) stand; the record
   carries no overlay state (the V2 record's existing discipline).
7. **Customer / retrieval relationship authority restrictions** —
   enforcement: the frozen `derive_relationship_authority` (customer
   retrieval is a retrieval hint only — zero identity authority;
   MANUFACTURER_RELATION_AUTHORITY required for the specific relation);
   the harness gates `zero_unauthorized_authority_promotion` /
   `zero_customer_alias_authority_promotion` (unchanged). Proof: the FU4
   derivation DELEGATES relationship authority to the frozen function
   (the audit field is the frozen determination — no new relationship-
   authority surface exists in the FU4 module; the C9 / F1 rows stand);
   the eight gates run over the FU4 lineage exactly as over the others.
8. **Qualification success ≠ production activation** — enforcement: the
   report's `authority` section (`granted: false` + the "evaluation
   evidence only" note — the report contract's existing fields); the
   POLICY_PENDING ladder (no applicable APPROVED policy ⇒ never
   QUALIFIED); the absence of any runtime wiring (item 3). Proof: the
   committed 1.2.0 no-capture baselines carry `granted: false` +
   `v2_authority_qualified: false` (R2 pin); the verify-report binding
   stands. **Any future production integration — a live 2.1/FU4 execution
   path, an FU4-derived tier reaching pricing aggregation, or the
   qualification marker flip — requires its own separately approval-
   gated architecture review** (the W1 atomic consumer guard — PROVEN_
   EQUIVALENT or a recorded human CONFIRMED or excluded with a recorded
   reason — ships with the FIRST such consumer, unchanged in predicate:
   it reads `SalesUnitAuthorityV2`, whose vocabulary is unchanged; the
   FU4 token changes only WHEN each state is derived for bundles).

---

# 8. Migration and compatibility analysis

## 8.1 The six "without" properties (all satisfied)

1. **No database migrations.** The `runs.SemanticDecisionRecord` row is
   unchanged (same columns; envelope `schema_version` stays 1 — the
   ENVELOPE format is unchanged; the version-owned sections are adapter-
   owned and live inside the opaque payload). `makemigrations --check
   --dry-run` must report "No changes detected" at R1 and R2 acceptance.
   The model's docstring states the path this design executes: a future
   semantic contract reuses the row by registering a new adapter.
2. **No change to frozen SemanticDecisionRecord semantics.** The V1 / V2
   record types, their constructors, their section codecs, and their
   digests are byte-frozen inputs (digest-pinned at R1). The FU4 record is
   a NEW type (FIND-2 / DEC-7) — the envelope's interpretation
   discipline (unknown / future contracts fail closed; a registered
   adapter per binding) is exactly what the foundation was designed for.
3. **No change to Prompt 2.0 / 2.1 behavior.** The 2.0 / 2.1 texts are
   byte-frozen (digests `c0cc98bd…` / `e2949e75…` re-pinned); the 2.1
   builders are unchanged; the registration adds a binding constant
   alongside, never a prompt version (a phantom 2.2 is refused by the 2.1
   module's own import check — and no text change is needed, P3 §7.4).
4. **No rewriting of historical corpus artifacts.** 1.0.0 / 1.1.0 + both
   manifests re-pin byte-identical; 1.2.0 is a NEW sealed artifact
   (binding-only — §5.1). No label, per-case document, or
   `label_revisions` entry moves.
5. **No reinterpretation of old replay records.** Per-binding dispatch
   forever (the recorded token selects the derivation; the recorded
   binding selects the adapter); the V1 / V2 adapters are byte-unchanged;
   the codec amendment is behavior-preserving for every currently
   decodable payload (§4.3 proof obligation); the 2.1/FU3 binding remains
   un-registered at the codec level (harness-only), exactly as today.
6. **No live model calls.** The registration step is offline: codec /
   adapter / record / replay work over constructed payloads; the corpus
   re-seal is a deterministic document transform; the baselines are
   no-capture; the validation runs the existing pytest suites (no
   transport, no provider, no capture runner).

## 8.2 The ONE required versioned amendment (documented, not blocked)

The codec dispatch amendment (FIND-1 / DEC-9) is the single frozen
contract that cannot support FU4 AS-IS. It is documented here with its
exact scope (§4.3), its behavior-preservation proof obligation, its
rejected alternative, and its recorded node corrections (§1.7). It is NOT
a blocker to the design or to the registration phase — it IS part of the
registration phase's bounded scope (R1). If the independent review of
this document finds the amendment unsatisfactory, the fallback is to
DEFER the record-level registration (R1) while executing the
qualification-level registration (R2) — the harness surface (corpus
seal, gates, report, baselines) is codec-independent and fully executable
on its own; the two are separable by construction (R1 and R2 touch
disjoint module sets). That fallback is a governance decision, not a
technical necessity (DEC-9 is recommended and, as designed, safe).

## 8.3 Compatibility matrix (post-registration state)

| Surface | Before | After |
| --- | --- | --- |
| Codec-registered bindings | V1, 2.0/FU2 | V1, 2.0/FU2, 2.1/FU4 |
| Replay-safe bindings | V1, 2.0/FU2 | V1, 2.0/FU2, 2.1/FU4 |
| Harness bindings / corpus seal | 2.0/FU2→1.0.0, 2.1/FU3→1.1.0 | + 2.1/FU4→1.2.0 |
| 2.1/FU3 | harness-only (codec-refused) | harness-only (codec-refused — unchanged) |
| Live record binding | 2.0/FU2 | 2.0/FU2 (unchanged) |
| Live prompt / route | 2.0 / the pinned route | 2.0 / the pinned route (unchanged) |
| `V2_AUTHORITY_QUALIFIED` | False (×2) | False (×2 + the FU4 adapter mirror) |
| Pricing-eligible tiers | {MV, AAC, HC} | {MV, AAC, HC} (unchanged) |
| Committed corpus artifacts | 1.0.0, 1.1.0 | + 1.2.0 (new seal) |
| Policy | DRAFT 1.0.0-scoped | DRAFT 1.0.0-scoped (unchanged; 1.2.0-scoped policy = the separate governance step, §5.6) |

---

# 9. Adversarial test matrix (registration step)

Conventions (the P1 / P2 / FU3 / FU4 precedent): every case is an OFFLINE
recorded-input or recorded-payload construction with scripted evaluation
doubles — NO live call, NO model capture, NO network. The matrix below is
the MANDATED minimum for the registration phase (R1: the record / replay
layer, new test file proposed `tests/research/test_semantic_decision_v2_
fu4.py`; R2: the qualification layer, new test file proposed
`tests/evaluation/semantic_v2/test_q3b5_p5_fu4_registration.py`). All
EXISTING safety tests and their expected behavior are preserved (the
recorded §1.7 node corrections are the only in-place edits — names
preserved, intents preserved or strengthened; no test deleted, renamed,
skipped, xfailed, deselected, ignored, or weakened; the Windows subprocess
flake allowlist is NOT expanded).

## 9.1 R1 — record / codec / replay layer

1. **FU2 / FU3 / FU4 binding coexistence.** (R1) The codec registry knows
   EXACTLY `(V1, 2.0/FU2, 2.1/FU4)` — a forged fourth binding is refused;
   the replay union is the same; the 2.1/FU3 binding is STILL refused by
   the codec and the replay (harness-only, unchanged); the three-token
   derivation coexistence row (the A7 extension): the SAME recorded
   count-only bundle inputs derive PROVEN_EQUIVALENT through the FU4
   dispatch's FU3 arm and UNPROVEN through its FU4 arm, and the FU2 arm
   refuses a unit input as contract misuse — documented per-binding
   behavior, never drift.
2. **Unknown authority token rejection.** (R1) A payload whose contract
   section records an unknown / future / misspelled token
   (`SEMANTIC_AUTHORITY_V2_S2A_FU9`, case / whitespace variants, an
   empty string) is refused at the codec's claim-based disambiguation
   ("no registered adapter claims") — never decoded best-effort, never
   under the nearest known contract; the FU4 dispatch's own unknown-token
   row stands (research level).
3. **Unknown composition schema rejection.** (R1) An FU4 payload whose
   `authority` section carries a candidate document with
   `schema_version` 4 (future) or any non-3 value is refused (the
   strict decode + the constructor pin); a superseded-v2 document (no
   embedded `extraction_result` on the EXTRACTION basis) is refused — a
   superseded schema is never silently reinterpreted.
4. **FU4 schema v1 / v2 rejection where v3 is required.** (R1) Hand-
   built v1-shaped (no `channel_content_digest`, no embedding) and
   v2-shaped (no embedding) documents are refused at decode (the exact
   key-set check) AND would be un-constructible through the FU4
   constructors (the version pin) — both layers pinned.
5. **Missing embedded extraction result.** (R1) An EXTRACTION_RESULT_V1
   candidate document with `extraction_result: null` is refused (the
   basis coherence: an extraction record whose original result is missing
   is un-constructible — the constructor AND the decode reject it; a
   RECORDED_CHANNEL document with a non-null embedding is refused
   symmetrically).
6. **Tampered extraction-result digests.** (R1) (a) out-of-band tamper of
   the embedded result's `result_digest` (a stored value not covered by
   the embedding's canonical round-trip is impossible — the round-trip
   check catches any field edit; the DIGEST-VALUE tamper that survives
   the record digest is caught by the gate's step-(1) own re-verification
   of the embedded original's integrity) — refused, no unit derived;
   (b) a tampered `input_digest` of the embedded result — refused;
   (c) a cue-span tamper (`cue_text` no longer a substring of
   `raw_field_value` at the recorded span) — `verify_integrity` refuses.
7. **Valid but wrong extraction result.** (R1) A self-consistent embedded
   result whose FROZEN P2 mapping is NOT the recorded channel (gate step
   3) — refused; a self-consistent embedded result that maps to the
   recorded channel but whose recomputed composition DIFFERS from the
   complete record (gate step 4 — the strongest wrong-result forgery) —
   refused; the RECORDED_CHANNEL analog (a hand-forged self-verifying
   record that is not the exact construction of the recorded channel) —
   refused.
8. **Identical primary clause with conflicting secondary cues.** (R1, the
   B12 rows at record level) A genuine CONTRADICTED_PUBLISHED record
   stands over its own mapped channel (UNPROVEN over every bundle target;
   the form rule over non-bundle) and its derived section records the
   contradiction; a forged swapped / dropped secondary cue over a content-
   identical channel is refused; the frozen-channel content bound is
   pinned (a genuine record from one content-identical publication over
   the other's channel still fails closed — the documented bound).
9. **Cross-listing evidence substitution.** (R1) A record constructed
   from listing A's channel / result presented over listing B's recorded
   channel in the payload (identical source class / bundle form /
   quantity) — the derivation's presentation gate refuses (the channel-
   content digest + the v3 chain); the replay therefore fails closed
   (no derived-agreement — the recorded derived section cannot have been
   produced from the substituted evidence without tampering its own
   digests).
10. **Candidate / target attestation laundering.** (R1) A candidate-
    subject attestation with a target-side source class (or vice versa);
    a candidate-side record carrying a REVIEWED-basis attestation; a
    clause_digest bound to a different clause; a quantity attestation
    whose subject side is not the actually-missing side; a quantity
    attestation over a non-asymmetric axis — all un-constructible /
    integrity-refused at decode AND at the gate (the B9 / B10 rows at
    record level).
11. **Missing quantity completeness.** (R1) The Blocker A defect shape
    (byte-identical attested clauses, candidate quantity 2, target None,
    NO quantity attestation): the derivation returns UNPROVEN (the
    UNDETERMINED axis) — a payload whose derived section records
    PROVEN_EQUIVALENT + AI_ASSISTED_COMPARABLE over that evidence is
    undecodable (the constructor invariants) or replays to a mismatch
    (the derived-agreement proof); the axis state is recorded (never
    silent) in every bundle comparison.
12. **Contradicted Bundle composition.** (R1) Two ESTABLISHED clauses
    with a materially established difference (U17) ⇒ CONTRADICTED ⇒ the
    would-be AI_ASSISTED_COMPARABLE is capped at NEEDS_REVIEW with
    CEILING_SALES_UNIT_CONTRADICTED — the decision's audit fields record
    the axis states + attestation digests; the Q3-B4 §4.1 invariant row
    (NEVER AI_ASSISTED_COMPARABLE) at record level.
13. **Recorded versus replayed authority mismatch.** (R1) A full tamper
    sweep over the FU4 payload: each derived field (tier; fired rules;
    unit; bound; quality; relationship authority; quantity-axis state;
    composition states; the three attestation digests), each evaluation
    field, each execution field, each authority-evidence document —
    mutated with the digests NOT recomputed ⇒ decode refuses (stale
    section digest) or replay refuses (derived-agreement mismatch, naming
    the field); mutated WITH the output digest recomputed but the
    derivation still disagreeing (a forged snapshot consistent with its
    own digests but not with the recorded evidence) ⇒ the replay's
    re-derivation agreement proof refuses. No tamper shape yields a
    passed replay.
14. **Wrong provider / model provenance.** (R1) An FU4 record whose
    primary / fallback attempt names any provider / model outside the
    pinned route is un-constructible (the V2-style route pin, mirrored in
    the FU4 adapter) and undecodable; the harness capture loaders' frozen-
    route pins stand (R2 re-exercises them over the 1.2.0 corpus).
15. **Historical replay byte compatibility.** (R1) (a) every existing
    historical replay fixture (V1; 2.0/FU2) decodes to the SAME typed
    record, replays to the SAME decision, and re-encodes BYTE-IDENTICAL
    under the amended codec (the behavior-preservation proof, concrete);
    (b) the codec's error behavior over a malformed V1 / V2 payload is
    the same error class at the same stage (modulo the §1.7 recorded
    message-path nodes); (c) the `registered_semantic_contract_adapter`
    single-lookup results are unchanged (V1 → V1 adapter; (1,"V2") → V2
    adapter — registration order preserved).
16. **The disambiguation gate itself.** (R1) A 2.0-prompt axis under the
    FU4 token (a forged `(V2, 2.0, 1, 1, FU4)` binding) is refused (no
    adapter claims it); a 2.1-prompt axis under the FU2 token is refused
    (the V2 adapter does not claim it; the FU4 adapter does not either);
    the two-adapters-claiming-one-binding registry defect is
    unrepresentable but the guard row (a monkeypatched double claim)
    fails closed.

## 9.2 R2 — qualification / corpus layer

17. **The 1.2.0 re-seal field-by-field verification.** (R2) Independently
    recomputed digests: 56/56 per-case documents byte-identical to the
    committed 1.1.0 document (every per-case digest verified);
    `label_revisions` empty; EXACTLY `{corpus_version, semantic_contract_
    binding, corpus_digest}` moved; `corpus_id` / `corpus_schema_version`
    / `corpus_label` / `created_utc` unchanged; the manifest verifies
    against the corpus; regenerating from `fixtures` reproduces the
    committed artifact byte-for-byte.
18. **Corpus digest mismatch.** (R2) A tampered 1.2.0 document (any per-
    case field; the corpus digest; the binding; the version) is refused
    by `load_corpus` (the per-case digest check; the seal check; the
    whole-corpus digest check); a capture / report bound to the WRONG
    1.2.0 digest (a lookalike re-seal) is refused against the committed
    corpus.
19. **The cross-binding corpus refusal matrix (extended).** (R2) 1.2.0
    under the 2.0/FU2 binding — refused; 1.2.0 under the 2.1/FU3 binding
    — refused; 1.1.0 under the 2.1/FU4 binding — refused; 1.0.0 under the
    2.1/FU4 binding — refused; a 2.2 prompt axis under any binding —
    refused (the existing matrix rows stand for 1.0.0 / 1.1.0 — the P1
    suite passes unchanged except the §1.7 recorded nodes).
20. **The cross-lineage capture / report refusal.** (R2) A 2.1 direct
    capture sealed to the 1.1.0 corpus digest is refused against the
    1.2.0 corpus (different corpus — the capture binds to the exact
    corpus it was produced for); a committed 1.2.0 no-capture baseline is
    refused on the 1.1.0 / 1.0.0 corpora (the `verify_report` corpus-
    binding check); the committed 1.0.0 / 1.1.0 baselines remain refused
    on the other corpora (the P1 rows stand).
21. **Qualification success without live authority activation.** (R2)
    Every committed 1.2.0 baseline report carries `authority.granted ==
    false`, `v2_authority_qualified == false`, and the existing
    "evaluation evidence only" note; the decision is POLICY_PENDING (no
    applicable APPROVED policy exists for 1.2.0 — the DRAFT is 1.0.0-
    scoped and unchanged); a hypothetical full-pass evaluation over 1.2.0
    with the DRAFT policy (presented by construction in the test) is
    POLICY_PENDING, NEVER QUALIFIED (the applicability check fails
    closed); the live record type still pins the FU2 token; `runtime_v2.
    py` is byte-identical; no live module references the FU4 surface
    (the A4 AST / lexical scan stands, extended to the new adapter
    module's allowed surface).
22. **No automatic pricing promotion from UNPROVEN / CONTRADICTED
    units.** (R2) Over EVERY committed 1.2.0 case, the FU4 derivation of
    the recorded channel (the no-capture arithmetic): 0032 / 0033 / 0034
    derive CONTRADICTED (the form axis) and the remaining cases'
    non-bundle / UNAVAILABLE channels derive per the frozen delegation —
    NO case derives a unit state that would lift a ceiling; the derived
    tier over MATCH + HIGH + STRONG + clean for the three safety cases is
    NEEDS_REVIEW (ceiling fired), never AI_ASSISTED_COMPARABLE;
    `NEEDS_REVIEW not in PRICING_ELIGIBLE_TIERS` stands. (R1 carries the
    exhaustive sweep over the decision type; R2 pins it over the
    committed corpus shapes.)
23. **Provider / model provenance at the harness level.** (R2) The
    1.2.0 baselines are produced for exactly the two pinned routes
    (amax / qwen3.8-27b, vllm-262k / Qwen3.6-27B-262K) with the route
    identity recorded in the report's runtime config section (unchanged
    shape); a baseline naming any other identity is unproducible (the
    `evaluate_no_capture` route check).
24. **Primary / fallback independence.** (R2) The two 1.2.0 baselines are
    separate per-model artifacts (the existing no-capture discipline);
    the direct-capture per-model projection is unchanged (the Q3-A-FU1
    suite stands over the 1.2.0 corpus — a new capture-construction row
    verifies the 1.2.0 seal accepts a well-formed 2.1 direct capture
    constructed in-test — no live call).

---

# 10. Bounded implementation phases and acceptance criteria

The registration step is executed as TWO sequentially gated sub-phases
(DEC-10; P3 §7.3 listed the deliverables as one step — the split is an
implementation-governance choice: the two sub-phases touch DISJOINT
module sets, have independent frozen-pin groups, and are independently
reviewable; R2 does not depend on R1's internals, only on its acceptance).
NEITHER sub-phase implements production or test code in THIS design
phase.

## 10.1 R1 — the record / replay layer (codec + adapter + replay)

**Scope (the exact files):**
* NEW `product_intelligence/research/semantic_decision_v2_fu4.py` (§4.2 —
  the adapter, the record type, the payload codec, the replay);
* MODIFIED `product_intelligence/research/semantic_decision_codec.py`
  (the DEC-9 disambiguation amendment + the registry's third entry —
  nothing else);
* MODIFIED `product_intelligence/research/__init__.py` (the strictly
  additive export block: the FU4 adapter / record / replay symbols — the
  FU3 / FU2 / V1 / V2 export blocks untouched);
* NEW `tests/research/test_semantic_decision_v2_fu4.py` (the §9.1
  matrix, rows 1–16);
* RECORDED in-place corrections: the §1.7 nodes in
  `test_semantic_authority_v2_fu4.py` (A1 re-pin at R1's starting SHA
  minus the R1-owned files; A4 / E1 / E2 → the registered state),
  `test_q3b5_p1_binding_replay.py` (the two registry-set nodes),
  `test_semantic_decision_codec.py` (the expected `supported_contract_
  bindings()` tuple), `test_semantic_decision_replay.py` (the exact-
  tuple + length nodes) — each documented in the commit record with its
  old / new assertion, name preserved, intent preserved or strengthened.

**Frozen (byte-pinned at R1's starting SHA):** the FU4 module; the FU2 /
FU3 modules; the extraction module; `semantic_v2.py`; the V1 / V2
adapters + record types; the envelope foundation; the replay module;
`contract_v2.py` / `contract_v2_1.py` / `runtime_v2.py`; the entire
harness; the corpus artifacts; the DRAFT policy.

**Acceptance (ALL must hold):**
1. The §9.1 matrix (rows 1–16) passes as NEW nodes; no existing test
   deleted / renamed / skipped / xfailed / deselected / weakened (the
   §1.7 recorded corrections are the only in-place edits);
2. the full historical suites pass (the 224-node FU4 suite modulo §1.7;
   the 98-node FU3 suite; the 111 + 7 extraction suites; the decision-
   record / codec / replay / V2 suites modulo §1.7; the historical
   replay suites) — the byte-compatibility row (9.1-15) is concrete
   proof;
3. collection non-decreasing from R1's starting SHA (7500 at the current
   endpoint + the R1 nodes; the node-level diff: 0 removed / 0 renamed
   except the §1.7 recorded corrections); skipped / xfailed /
   deselected 0 / 0 / 0; the Windows flake allowlist NOT expanded;
4. `python manage.py check` — no issues; `python manage.py
   makemigrations --check --dry-run` — "No changes detected";
5. `V2_AUTHORITY_QUALIFIED` False in BOTH pinned locations + the FU4
   adapter's mirror (pinned); no live module references the FU4 record
   surface (the A4 AST / lexical scan stands); `runtime_v2.py` byte-
   identical; the pricing surfaces byte-identical;
6. no model call, no capture, no deployment, no corpus change, no policy
   change.

## 10.2 R2 — the qualification layer (binding constant + corpus seal +
harness + baselines)

**Scope (the exact files):**
* MODIFIED `product_intelligence/semantic/contract_v2_1.py` (the FU4
  binding constant + import self-checks — additive; the existing
  constant byte-unchanged);
* MODIFIED `product_intelligence/evaluation/semantic_v2/fixtures.py`
  (`CORPUS_VERSION_2_1_FU4 = "1.2.0"` + `build_corpus_2_1_fu4_
  document()`);
* MODIFIED `product_intelligence/evaluation/semantic_v2/corpus.py`
  (the third `BINDING_CORPUS_VERSIONS` entry; `KNOWN_PRODUCTION_BINDINGS`
  = exactly three);
* MODIFIED `product_intelligence/evaluation/semantic_v2/gates.py` (the
  `zero_contract_version_mismatch` detail-text branch for the third
  binding — the eight gate names / semantics unchanged);
* MODIFIED `product_intelligence/evaluation/semantic_v2/report.py` (the
  `_contract_section` third-binding branch — the report schema
  unchanged);
* MODIFIED `product_intelligence/evaluation/semantic_v2/cli.py` (the
  corpus-build's 1.2.0 generation);
* NEW `evaluation/semantic_v2_qualification/corpus_2_1_fu4.json` +
  `manifest_2_1_fu4.json` (the 1.2.0 seal);
* NEW `evaluation/semantic_v2_qualification/reports/q3b5_p5_baseline_
  1_2_0/` (four no-capture baseline files);
* NEW `tests/evaluation/semantic_v2/test_q3b5_p5_fu4_registration.py`
  (the §9.2 matrix, rows 17–24);
* RECORDED in-place corrections: the §1.7 nodes in
  `test_q3b5_p1_binding_replay.py` (the drift-pin set; the codec-registry
  node) and `test_semantic_authority_v2_fu4.py` (the A1 re-pin at R2's
  starting SHA minus the R2-owned files; the harness-registry node → the
  three-binding state) — documented as at R1.
* VERIFIED BYTE-UNCHANGED at R2: `capture.py`, `direct_capture.py`,
  `policy.py`, `evaluator.py` (the prompt-axis capture mechanism and the
  metric surface are binding-count-agnostic — the registration changes
  no capture / evaluation / policy behavior; if inspection at R2's
  starting SHA shows otherwise, R2 STOPS and reports the conflict —
  these files are expected frozen inputs).

**Acceptance (ALL must hold):**
1. the §9.2 matrix (rows 17–24) passes as NEW nodes; no existing test
   deleted / renamed / skipped / xfailed / deselected / weakened;
2. the 1.2.0 re-seal verifies field-by-field (row 17) and regenerates
   byte-for-byte from the fixtures (the P1 property); the committed
   1.0.0 / 1.1.0 artifacts + manifests + the DRAFT policy re-pin byte-
   identical;
3. the full harness suites pass (the Q3-A suites; the P1 binding-replay
   suite modulo §1.7); the eight gates + the decision ladder unchanged in
   substance; every 1.2.0 baseline is POLICY_PENDING with `granted:
   false` (row 21);
4. collection non-decreasing; 0 / 0 / 0 skips; the flake allowlist NOT
   expanded; `manage.py check` clean; `makemigrations --check --dry-run`
   clean;
5. `V2_AUTHORITY_QUALIFIED` False in both pinned locations (byte-pinned
   modules); `runtime_v2.py` byte-identical; no live module references
   the FU4 surface; the pricing surfaces byte-identical;
6. no model call, no capture, no deployment, no corpus LABEL change
   (binding-only), no threshold / policy change, no authority
   activation.

## 10.3 Explicitly out of scope for both sub-phases (and for any step
this design authorizes)

* No model call, no benchmark capture (a 2.1 direct capture over 1.2.0 is
  a future live qualification step — OPEN-4), no deployment;
* No policy creation or approval (the 1.2.0-scoped APPROVED policy is the
  separate governance step — §5.6);
* No runtime wiring (no live 2.1 / FU4 execution path; the live runtime
  stays on the frozen 2.0 / FU2 record), no `V2_AUTHORITY_QUALIFIED`
  flip, no W1 consumer, no pricing change;
* No case addition / label change (OPEN-3); no 1.3.0;
* No envelope schema version move (the envelope stays 1);
* No change to the FU4 module (it is a frozen input of both sub-phases —
  a defect found by the pending review of Q3-B5-P4-FU2 is corrected in
  its OWN separately gated correction phase, per the FU1 / FU2
  precedent, BEFORE R1 starts — the registration freezes what the review
  ratifies).

---

# 11. OPEN / BLOCKED / DECIDED questions

## DECIDED (by this design, each with its enforcement point)

* **D-P5-1 — the binding.** `("V2", "2.1", 1, 1,
  "SEMANTIC_AUTHORITY_V2_S2A_FU4")` is the FU4 production binding
  (P3 D12, adopted verbatim). The existing 2.1/FU3 binding is NOT reused
  for changed authority semantics; no new prompt version.
* **D-P5-2 — binding sufficiency.** The binding alone identifies the
  Prompt 2.1 decision contract, the FU4 authority contract, and the
  derivation rules; it does NOT identify the evidence / extraction
  schema versions, the route, or the corpus version — the smallest
  additional evidence metadata is the payload's version-owned
  `authority` section (self-versioned, digest-sealed documents) + the
  adapter-owned schema pins (3 / 1) + the route mirror + the harness
  seal (1.2.0) + the report's real prompt digest (§3.2). No new binding
  axis.
* **D-P5-3 — the record type.** A NEW FU4 record type + a NEW registered
  adapter (the V2 record type is byte-frozen and exactly pins 2.0/FU2 —
  FIND-2 / DEC-7); the envelope schema version stays 1.
* **D-P5-4 — the codec dispatch.** The claim-based disambiguation
  amendment (FIND-1 / DEC-9) is the required versioned amendment to the
  frozen codec; it is behavior-preserving for every currently decodable
  payload; the failover-loop alternative is rejected.
* **D-P5-5 — the corpus.** 1.2.0 is REQUIRED at registration (the seal
  discipline); it is a BINDING-ONLY re-seal (56/56 per-case documents
  byte-identical to 1.1.0; `label_revisions` empty; exactly
  `{corpus_version, semantic_contract_binding, corpus_digest}` moved).
  No new case at registration (DEC-4).
* **D-P5-6 — the binding constant owner.** The semantic layer
  (`contract_v2_1.py`, alongside the FU3 constant — DEC-6); the research
  adapter mirrors (drift-pinned).
* **D-P5-7 — the target-evidence discriminator.** The explicit bounded
  `absent / frozen_fu3 / fu4_v3` discriminator in the `authority` section
  (DEC-8) — no shape inference at decode.
* **D-P5-8 — the metric surfaces.** Semantic-model performance and
  deterministic FU4 authority correctness are measured on separate
  surfaces with separate acceptance statements (DEC-5); no harness
  threshold is added, moved, or relaxed; the eight gates are mandatory
  and unchanged in substance.
* **D-P5-9 — the policy.** The DRAFT (1.0.0-scoped) is unchanged; a
  QUALIFIED decision over 1.2.0 requires an APPROVED policy applicable
  to 1.2.0 — a separate governance step with the exact four-threshold
  vocabulary (values NOT decided here); until then POLICY_PENDING
  (DEC-4b / §5.6).
* **D-P5-10 — the phase split.** Two sequentially gated sub-phases, R1
  (record / replay) then R2 (qualification), disjoint module sets, each
  independently reviewable; R2 is executable even if R1 is deferred
  (the §8.2 fallback).
* **D-P5-11 — the report schema.** UNCHANGED (the exact section key sets
  stand; only the `_contract_section` binding branch extends); the
  committed baselines carry `granted: false` + the existing note.

## OPEN (governance decisions, NOT preconditions of this design's
internal coherence)

* **O-1 — Naming.** The proposed module / type / constant / artifact
  names (`semantic_decision_v2_fu4.py`, `SemanticDecisionRecordV2FU4`,
  `SEMANTIC_V2_FU4_ADAPTER`, `V2_1_FU4_CONTRACT_BINDING`,
  `corpus_2_1_fu4.json` / `manifest_2_1_fu4.json`, the baseline report
  directory) are PROPOSALS of record (the P3 design proposed the corpus
  / manifest names; this design extends the pattern). The registration
  phase finalizes them; any rename is a documentation-level decision with
  no contract effect (the contracts are the digest-sealed documents and
  the pinned constants, not the names).
* **O-2 — A future 1.2.x / 1.3.0 case addition** (completeness-marker
  bundle cases for MODEL-side coverage — the FU4 PROVEN path is already
  fully covered at the research level; a model-corpus case would label
  the MODEL, binding-agnostically). Requires the evaluation-truth A/B/C/
  D statement + an independent label source + a new corpus version (or a
  case-addition re-seal with `label_revisions` where labels genuinely
  move). A governance decision for a FUTURE phase; NOT required for the
  FU4 registration, and NOT authorized by this design.
* **O-3 — The live 2.1 / FU4 execution path** (a future runtime decision:
  when the V2 route is qualified and a live 2.1 execution is approved,
  the live record binding moves to a 2.1 binding — FU4 by then, if the
  qualification disposes it — with the W1 atomic consumer guard shipping
  with the first pricing consumer). A separate architecture review +
  explicit approval; NOT authorized by this design.
* **O-4 — The model capture over 1.2.0** (a live qualification run — the
  2.1 prompt, the pinned routes, the direct or production-route mode).
  A separately gated live step AFTER the policy governance (O: the
  1.2.0-scoped APPROVED policy) and the registration; NO capture in R1 /
  R2.

## BLOCKED

* **B-1 (dependency gate, recorded):** R1 must NOT start while
  Q3-B5-P4-FU2 (the current HEAD, the FU4 module's final correction) is
  still PENDING independent review. The registration step freezes the
  reviewed FU4 module as its byte-pinned input (evidence schema v3); a
  further correction (a v4) would move the freeze point. This is a
  sequencing gate, not a design blocker: the design is version-tolerant
  by construction (the adapter pins the CURRENT schema constant,
  drift-pinned; the decode refuses superseded documents), so a v4
  correction before R1 merely re-pins the constants — but the clean
  ordering is: review ratifies Q3-B5-P4-FU2 → R1 → R2.
* **B-2:** NONE. The one frozen-contract incompatibility (the codec
  dispatch, FIND-1) is RESOLVED by this design's DEC-9 amendment —
  documented with its exact scope, its proof obligation, and its
  rejected alternative. No other frozen contract cannot support FU4:
  the envelope, the row, the service, the replay module, the harness
  mechanism, and the prompts all extend (or do not move) as specified.

---

# 12. Risks, alternatives, and recommended design

## 12.1 Risks (each with its mitigation of record)

* **R-1 — the codec dispatch amendment touches a universal module.**
  Mitigation: DEC-9 is claim-based (each existing binding is claimed by
  exactly one adapter — resolution-identical to today's first-match),
  single-pass, fail-closed on zero / multiple claims; the behavior-
  preservation proof is CONCRETE (9.1-15: byte-identical decode /
  replay / re-encode over every historical fixture + the same error
  class / stage over malformed ones); the amendment is R1's ONLY
  change to the codec (the registry entry + the dispatch — nothing
  else); the replay module and the persistence service are untouched.
* **R-2 — the pin-movement surface is large** (the §1.7 node
  corrections across four suites + the A1 re-pins at R1's and R2's
  starting SHAs). Mitigation: every correction is mechanical (an
  expected set gains its documented third member; a digest table re-
  pins to the phase's own starting SHA), recorded IN PLACE with the old
  / new assertion named, under the project's documented precedent
  (the P1 harness-pin extension; the P2-FU1 / Q3-B4-FU2 / FU1 / FU2
  recorded test corrections); no correction weakens a safety property —
  each post-correction node pins a STRICTLY MORE registry state (exactly
  three, no more, no cross-binding combination).
* **R-3 — the 1.2.0 re-seal's determinism.** Mitigation: the re-seal is
  a pure document transform (the `build_corpus_2_1_fu4_document`
  pattern of the P1 1.1.0 transform); regeneration from the auditable
  fixtures must reproduce the committed artifact byte-for-byte (the P1
  property, re-pinned at R2); the field-by-field verification (9.2-17)
  is independent of the builder (recomputed digests over the committed
  1.1.0 document).
* **R-4 — confusion: "registered adapter" ≠ "live authority".**
  Mitigation: the isolation proof obligations (§7) pin, at R1 and R2,
  that the live runtime is byte-unchanged, the live record type pins
  FU2, `V2_AUTHORITY_QUALIFIED` is False everywhere, the baselines are
  `granted: false` / POLICY_PENDING, and no pricing surface owns an FU4
  symbol; the report's existing note text ("evaluation evidence only")
  stands on every 1.2.0 artifact. The registration makes FU4 records
  PERSISTABLE AND REPLAYABLE — nothing more.
* **R-5 — the frozen-channel granularity bound** (the documented P4-FU2
  bound: two content-identical publications are indistinguishable at the
  channel level). Mitigation: the bound is PINNED (the B12 rows) and
  carried into the record contract (the embedding proves every authority-
  relevant fact of the record over the embedded original); the bound
  does not widen at registration (no channel change is authorized — the
  channel is byte-frozen); a future channel version is a new input-
  schema axis + a new binding, separately gated.
* **R-6 — the policy governance gap (F-4 lineage) could be misread as
  "qualified".** Mitigation: the decision ladder is fail-closed by
  construction (POLICY_PENDING without an applicable APPROVED policy);
  9.2-21 pins the hypothetical full-pass + DRAFT-policy shape as
  POLICY_PENDING, never QUALIFIED; the design states the 1.2.0-scoped
  policy step as a separate governance decision (O: §5.6) with the
  EXACT approval requirements (named approver, UTC instant, the four-
  threshold vocabulary).
* **R-7 — Windows subprocess flake class** (the documented load-
  sensitive clean-interpreter guard flakes). Mitigation: unchanged
  behavior; the flake allowlist is NOT expanded; the validation
  reporting discipline (itemized flake class, isolated re-pass) stands.

## 12.2 Alternatives considered (and rejected, with reasons)

* **A-1 — Reuse the V2 record type for FU4 (relax its binding pin).**
  Rejected: `semantic_decision_v2.py` is byte-frozen (the V2 record's
  exact pin is the anti-reinterpretation invariant); relaxing it would
  let a 2.0 record and a 2.1/FU4 record share one type with conditional
  validation — the per-binding discipline (Q3-B4 §6.1: a bound record
  carries the derived snapshots OF ITS TOKEN under a record type that
  cannot be mis-bound) requires the new type (DEC-7).
* **A-2 — A new semantic-contract version string for the FU4 lineage
  (e.g. "V2_FU4" as the dispatch key).** Rejected: the recorded payload's
  `contract.semantic_contract_version` is the contract that PRODUCED the
  evaluation — "V2" (the S2-C contract, unchanged by FU4 — the input /
  output / evaluation semantics are identical); a new string would make
  the envelope dispatch key disagree with the binding's axis 0 (a silent
  reinterpretation of a version axis) and would fragment the V2 case
  section codec (the same input contract re-versioned). The five-tuple
  binding (axis 5 = the token) is the designed discrimination surface.
* **A-3 — The codec failover loop (try adapters in order).** Rejected:
  decode-error masking; non-deterministic failure stage; the single-
  adapter lookup's semantics would lie (DEC-9's claim-based
  disambiguation is single-pass and stage-stable).
* **A-4 — Qualify FU4 directly against the committed 1.1.0 corpus (no
  1.2.0).** Rejected: the seal discipline (`load_corpus` refuses a
  version/binding disagreement; the `zero_contract_version_mismatch`
  gate pins the binding; the report re-binds to the corpus's exact
  binding) makes a 1.1.0-sealed corpus unusable for an FU4-bound
  report; and the P1 precedent (a binding-only re-seal per production
  binding) is the established, reviewed pattern (DEC-3).
* **A-5 — A new prompt version (2.2) for the FU4 lineage.** Rejected:
  the 2.1 text is unchanged by FU4 (P3 §7.4 — the prompt names no
  authority token and asserts nothing FU4 contradicts); a 2.2 would be a
  phantom version (the 2.1 module's import check refuses a version bump
  without a text change) and would fragment the qualification lineage
  (the 2.1 capture evidence, the P1 seal, and the Q3-C conditioning
  would not apply).
* **A-6 — Add completeness-marker bundle cases to the 1.2.0 re-seal.**
  Rejected for the registration step: the corpus labels the model (the
  authority token is downstream of the label); every new expected answer
  is an evaluation-truth move requiring the A/B/C/D statement + an
  independent label source; the FU4 PROVEN path is fully exercised at
  the research level (DEC-4). Recorded as the future O-2 governance
  option.
* **A-7 — Register the FU4 binding in the codec WITHOUT the disambiguation
  amendment (relying on adapter order).** Rejected: unreachable (FIND-1)
  — the first-match dispatch keeps selecting the V2 adapter for the
  (1,"V2") pair, whose strict decode refuses every FU4 payload;
  registration without the amendment would be a NO-OP with a dead
  registry entry — worse than nothing (a false claim of capability).
* **A-8 — Execute R1 and R2 as one phase.** Considered (P3 §7.3's shape)
  and rejected for governance: the two sub-phases have disjoint frozen-
  pin groups and independent review surfaces; a defect in either is
  isolated to its layer; R2 is executable even if R1 is deferred (the
  §8.2 fallback). The contract content is identical under either
  shape.

## 12.3 Recommended design

Execute the registration step as R1 then R2, exactly as specified:

1. **R1:** the claim-based codec disambiguation amendment (DEC-9) + the
   new FU4 record adapter (DEC-7) + the FU4 binding's registration in
   the codec / replay union + the §9.1 matrix — making FU4-bound
   records persistable, decodable, and replayable with full evidence-
   integrity verification, while every historical record decodes /
   replays / re-encodes byte-identically.
2. **R2:** the semantic-layer binding constant (DEC-6) + the 1.2.0
   binding-only corpus seal (DEC-3) + the harness's third production
   binding (corpus / gates / report / cli; capture / direct-capture /
   policy / evaluator byte-unchanged) + the committed 1.2.0 no-capture
   baselines (POLICY_PENDING, `granted: false`) + the §9.2 matrix —
   making the FU4 binding qualify exactly as the 2.0 / 2.1 lineages
   qualify: sealed corpus, fail-closed gates, separate metric surfaces,
   separate policy governance.
3. **Both:** no model call, no capture, no deployment, no migration, no
   label change, no threshold change, no authority activation, no live
   wiring; `V2_AUTHORITY_QUALIFIED` False; the pricing firewall intact
   at every pin (§7); the recorded node corrections of §1.7 in place,
   documented, names preserved.

The result is the P3 design's §7.3 deliverable — EXACTLY: the semantic-
layer binding constant; the corpus 1.2.0 binding-only re-seal; the
harness registry extension; the codec + replay extension (with the
disambiguation amendment this design specifies); the offline no-capture
baselines; and the Q3-C interaction preserved (qualification remains
conditioned on the firewall disposition; the W1 guard predicate is
unchanged; a future qualified state under the FU4 binding inherits the
same ceilings).

---

# 13. What this phase does not do (invariance list)

* No code, no tests, no artifacts other than this document (committed
  design-only, append-only, on main).
* No execution of the registration step (R1 / R2 are specified, not
  performed).
* No change to the FU4 module, the FU2 / FU3 modules, the S2-C channel,
  the extraction schema, the 2.0 / 2.1 contracts, the codec, the replay
  module, the corpus (1.0.0 / 1.1.0), the DRAFT policy, the eight gates,
  the live runtime, or the pricing surfaces.
* No binding registration, no corpus reseal, no capture, no
  qualification decision, no policy approval, no authority promotion, no
  pricing wiring, no deployment, no migration, no model call.
* No change to any test (the §1.7 recorded corrections are specified for
  the registration phase, not made here).
* No Qwen self-audit (the independent review of this document and the
  underlying source is ChatGPT's, per the task).
* Unrelated worktree artifacts (the untracked session / benchmark files,
  the pre-existing `tmp_collection.txt` modification) are preserved; the
  commit stages only this document.

---

# 14. Sources (complete list cited above)

* `CLAUDE.md` — the operating contract (frozen-phase semantics; test
  preservation; evaluation-truth rules; deterministic ownership;
  unknown-beats-fabricated-certainty).
* `docs/PRODUCT_INTELLIGENCE_STATUS.md` — the Q3-B5-P4 / P4-FU1 /
  P4-FU2 sections (the FU4 contract + corrections of record; the
  7500-collection endpoint), the Q3-B5-P2 / P2-FU1 sections (the
  extraction + bundle-identity correction; the FU4 proposal of record),
  the Q3-B5-P1 section (the 2.1 binding + 1.1.0 re-seal precedent).
* `docs/PRODUCT_INTEL_Q3B5_P3_BUNDLE_COMPOSITION_DESIGN.md` — the
  approved, corrected FU4 design (D1–D20, T1–T10, §7.1–§7.5, §8–§13).
* `docs/PRODUCT_INTEL_SEMANTIC_V2_Q3B4_AUTHORITY_BOUNDARY_DECISION.md` —
  §4.1 (the invariant), §5.4–§5.6, §6.1–§6.5 (the amendment pattern;
  AD-Q3B4-5; W1; per-binding replay), §8–§9.
* `docs/PRODUCT_INTEL_Q3B5_P1_INDEPENDENT_AUDIT.md` — finding F-4 (the
  policy scoping debt), F-3 (the STATUS / PLAN documentation lag).
* `product_intelligence/research/semantic_decision_record.py` — the
  envelope foundation + the `SemanticDecisionContractAdapter` extension
  point (§1.1).
* `product_intelligence/research/semantic_decision_codec.py` — the
  registry, the two-axis dispatch (FIND-1), `supported_contract_
  bindings()`, the universal framing (§1.1, §4.3).
* `product_intelligence/research/semantic_decision_replay.py` — the
  per-binding replay gate + `_adapter_for_binding` (the five-tuple
  selection DEC-9 mirrors) (§1.1, §4.3–§4.4).
* `product_intelligence/research/semantic_decision_v1.py` /
  `semantic_decision_v2.py` — the frozen adapters, record types, the
  exact-binding pins, the route mirrors, `V2_AUTHORITY_QUALIFIED`
  (location 1) (§1.1, FIND-2).
* `product_intelligence/research/semantic_authority_v2.py` — the frozen
  S2-A derivation, the tier / rule vocabularies, the relationship
  authority, `PRICING_ELIGIBLE_TIERS` / `MARKET_EVIDENCE_TIERS` + the
  import self-checks (§1.2, §7).
* `product_intelligence/research/semantic_authority_fu3.py` — the frozen
  FU3 firewall: the bound table, `SalesUnitAuthorityV2`, the frozen
  target record, the two restrict-only ceilings, the per-binding
  dispatch (§1.2).
* `product_intelligence/research/semantic_authority_fu4.py` — the FU4
  contract (the v3 evidence schema; the presentation gate's four-step
  chain; the U0–U21 table; `AuthorityDecisionV2FU4`; the superset
  dispatch) — read in full this session (§1.2, §3, §6).
* `product_intelligence/research/sales_unit_extraction.py` — the frozen
  P2 extraction (schema v1; the self-verifying result; `canonical()`;
  `verify_integrity()`; `sales_unit_channel_from_extraction`) (§1.2).
* `product_intelligence/research/semantic_v2.py` — the frozen S2-C input
  contract: `SemanticMatchCaseV2`, the recorded channel + its
  `canonical()` (the `channel_content_digest` bound), the 7-key output
  (§1.2).
* `product_intelligence/runs/models.py` — the `SemanticDecisionRecord`
  row + the stated adapter-extension point (§1.1, §4.1, §8.1).
* `product_intelligence/execution/semantic_decision_persistence.py` —
  the persistence service over the universal entry points (§1.1, §4.3).
* `product_intelligence/semantic/contract_v2.py` /
  `contract_v2_1.py` — the frozen 2.0 / 2.1 prompt contracts,
  `V2_1_CONTRACT_BINDING`, the system-prompt digests (recomputed this
  session), the 2.1 builder's fail-closed anchors (§1.3, §3.1, DEC-6).
* `product_intelligence/semantic/runtime_v2.py` — the live route +
  `V2_AUTHORITY_QUALIFIED` (location 2) + the frozen 2.0 prompt axis
  (§1.3, §7).
* `product_intelligence/evaluation/semantic_v2/{corpus,fixtures,gates,
  report,capture,direct_capture,evaluator,policy,cli}.py` — the
  harness registries, the seal discipline, the eight gates, the report
  contract, the capture schemas + route pins, the metric surface, the
  policy contract, the corpus-build CLI (§1.4, §4.5, §5).
* `evaluation/semantic_v2_qualification/{corpus_v1.json, corpus_2_1.
  json, manifest_v1.json, manifest_2_1.json, policy/qualification_
  policy_draft_1.json, reports/q3a_baseline/, reports/q3b5_baseline_2_
  1/}` — the committed corpus / policy / baseline artifacts (digests +
  the three sales-unit cases verified this session) (§1.5).
* `tests/research/test_semantic_authority_v2_fu4.py` (224 nodes; the A1
  pin tables; the §1.7 node inventory), `tests/research/test_semantic_
  authority_v2_fu3.py` (98), `tests/research/test_sales_unit_extraction.
  py` (111) + `test_sales_unit_extraction_recorded_pages.py` (7),
  `tests/evaluation/semantic_v2/test_q3b5_p1_binding_replay.py` (20),
  `tests/research/test_semantic_decision_codec.py` /
  `test_semantic_decision_replay.py` (the dispatch / gate suites) (§1.6,
  §1.7, §9).
* `docs/PRODUCT_INTELLIGENCE_PLAN.md` — §26.x decision log (through
  §26.38 at the starting SHA) + AD-077..AD-082 (the Q3-B4 / P1 / P2 /
  P2-FU1 decisions of record) (§14 header table; the documented STATUS/
  PLAN catch-up applies to the registration phase's completion).
