"""The Semantic V2 FU4 contract adapter (Q3-B5-P5 R1 — the record / replay
layer of the separately gated FU4 registration step).

PRODUCT-INTEL.SEMANTIC-AUTHORITY-V2-Q3-B5-P5-R1 executes design section 4 /
6 / 10.1 of ``docs/PRODUCT_INTEL_Q3B5_P5_FU4_BINDING_REPLAY_
QUALIFICATION_DESIGN.md`` (the CONDITIONALLY APPROVED R1 scope): the
approved, corrected, research-only FU4 bundle-composition authority
contract (``semantic_authority_fu4`` — token
``SEMANTIC_AUTHORITY_V2_S2A_FU4``, bundle-composition evidence schema v3)
is made PERSISTABLE AND REPLAYABLE through the universal semantic-
decision envelope, without changing historical FU2 / FU3 interpretation
and without enabling production authority. This module is the THIRD
registered adapter at the codec's explicit extension point; it owns, and
ONLY it owns:

* the FU4 contract identity: semantic contract ``V2`` (the final S2-C
  semantic contract — unchanged: FU4 governs the AUTHORITY layer
  downstream of the recorded decision, it is not a new semantic
  contract), prompt ``2.1`` (the approved separately versioned Prompt
  2.1 — NO new prompt version; the mirror is drift-pinned to the
  semantic layer's 2.1 owner by test), input schema 1, output schema 1
  (the strict 7-key response — the Q3-B4 §5.6 invariance), authority
  contract ``SEMANTIC_AUTHORITY_V2_S2A_FU4`` (imported from the research
  export — same package, no mirror) — the exact tuple
  ``V2_FU4_CONTRACT_BINDING``; anything else is outside this adapter and
  fails closed (never silently reinterpreted). The semantic-layer binding
  owner constant (design DEC-6) is the separately gated R2 deliverable;
  until it exists this adapter is the record-level owner of the tuple,
  composed from the frozen exports (no literal authority token in this
  source — the P1 discipline).
* the pinned route mirror: ``amax`` / ``qwen3.8-27b`` primary and
  ``vllm-262k`` / ``Qwen3.6-27B-262K`` fallback — the SAME frozen
  qualified route identities the V2 adapter pins (a FU4-bound record's
  attempts followed this exact route — any other provider/model is a
  FU4 contract violation, fail closed; drift-pinned to the V2 runtime
  and the V2 adapter by test);
* the explicit ``V2_FU4_AUTHORITY_QUALIFIED`` marker (False — the
  registration is NOT a qualification: the marker is pinned False and is
  not a registration deliverable; a qualification under the FU4 binding
  is a separate governance event with its own marker flip + consumer
  guard);
* the versioned evidence-schema pins (bundle-composition evidence schema
  3 — ``BUNDLE_COMPOSITION_EVIDENCE_VERSION_FU4`` — and sales-unit
  extraction schema 1 — ``SALES_UNIT_EXTRACTION_SCHEMA_VERSION``; a
  superseded or unknown version document is undecodable — the T5
  discipline: any change is a new version, never a silent
  reinterpretation);
* the FU4 typed record (``SemanticDecisionRecordV2FU4``) — the V2
  record's field set (universal binding; the exact recorded V2 case;
  the recorded evaluation; the recorded execution provenance) with the
  FU4 exact-binding check (a record bound to any other tuple is
  un-constructible — the anti-reinterpretation invariant, mirror of the
  V2 record's frozen pin), the FU4 ``derived`` section values (the FULL
  ``AuthorityDecisionV2FU4`` audit surface: tier, fired rules, product-
  evidence quality, relationship authority, identity-resolution bound,
  sales-unit authority, + the six bundle-axis audit fields — exactly
  None for non-bundle channels), the NEW version-owned ``authority``
  evidence fields (the v3 candidate composition record — digest-bound,
  the embedded original extraction result WITHIN its evidence digest —
  the discriminator-selected target evidence — the explicit
  ``absent / frozen_fu3 / fu4_v3`` shapes — and the quantity-completeness
  attestation), the same V2 evaluation / execution coherence rules, and
  the self-verifying section digests (``input_digest`` = canonical over
  {binding, contract, case} — the contract section carries the FU4
  binding, so an FU4 input digest is distinct from a same-case FU2 / FU3
  input digest by exactly the recorded authority axis; ``output_digest``
  = canonical over {evaluation, execution, authority, derived});
* the strict FU4 payload codec (the exact FU4 section key sets — the
  universal framing + the V2 case / evaluation / execution sections
  byte-identical + the FU4 derived / authority sections; fail closed;
  no floats; the strict evidence-document decode — field-by-field
  against the exact canonical key sets, typed reconstruction through
  the FU4 constructors (the constructor is the validator), and the
  round-trip document identity — a document that decodes to a different
  record is refused: no two documents, one record);
* the FU4 pure zero-live replay (reconstruction + the v3 presentation-
  gate verification via the derivation itself + the FU4 re-derivation +
  the full derived-agreement proof over the FU4 audit surface);
* the registered instance ``SEMANTIC_V2_FU4_ADAPTER`` (envelope schema
  1, semantic contract V2, ``supported_bindings = (V2_FU4_CONTRACT_
  BINDING,)``, record type = ``SemanticDecisionRecordV2FU4``) — appended
  to the codec registry AFTER the V2 adapter (registration order
  preserved: V1, V2, V2-FU4 — the codec's claim-based decode
  disambiguation (FIND-1 / DEC-9) selects exactly one claiming adapter
  on the full recorded five-axis binding; zero claims fail closed,
  multiple claims fail closed; no adapter-failover decoding).

The FU4 record is a NEW type (FIND-2 / DEC-7): the frozen
``SemanticDecisionRecordV2`` constructor exactly pins semantic contract
"V2" + prompt "2.0" + authority FU2 — an FU4-bound record cannot be, or
be decoded as, a V2 record, and the per-binding discipline (Q3-B4 §6.1
item 5) requires each binding's record to carry the derived snapshots OF
ITS TOKEN under a record type that cannot be mis-bound. No historical
record is upgraded to FU4: a 2.0/FU2 record's binding does not claim
this adapter, and re-encoding a historical record under the FU4 binding
would change its contract section (hence its input digest) and fail its
own integrity verification.

The universal parts — the envelope framing (payload schema version +
binding + contract dispatch), the adapter registry, the claim-based
decode dispatch, the row-level tamper anchor, the universal replay
dispatch (its five-tuple gate + per-binding selection already implement
the post-registration semantics — the replay module is byte-unchanged),
the persistence service — live in ``semantic_decision_record.py`` /
``semantic_decision_codec.py`` / ``semantic_decision_replay.py`` and the
runs / execution layers.

This module is pure research-layer contract: stdlib + the research
package's public export surface + the frozen research contract modules
(``semantic_v2``, ``semantic_decision_record``, ``semantic_decision_v2``,
``semantic_authority_fu3``, ``sales_unit_extraction``,
``semantic_authority_fu4``) only; no Django, no I/O, no clock, no float
authority data, no network, no production semantic-runtime import (the
V2 runtime vocabulary it names is mirrored, drift-pinned by tests).
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Final

from product_intelligence.research import (
    AttemptOutcome,
    AuthorityTier,
    CandidateEvidenceSourceV2,
    CandidateSalesUnitEvidenceV2,
    ConflictClass,
    ContextProvenance,
    IdentityStateAssessmentV2,
    PackagingEvidenceStateV2,
    ProductEvidenceProfileV2,
    ProductEvidenceQuality,
    RelationshipAuthority,
    RelationshipRequirement,
    SalesUnitKindV2,
    SemanticAttributeDimensionV2,
    SemanticAttributeV2,
    SemanticDecisionAttempt,
    SemanticEvaluationStateV2,
    SemanticEvaluationV2,
    SemanticFallbackReason,
    SemanticFailureClass,
    SemanticMatchCaseV2,
    SemanticMatchResponseV2,
    SemanticReasonCodeV2,
    V2Confidence,
    V2SemanticDecision,
    derive_product_evidence_quality,
    derive_relationship_authority,
    substate_relationship_requirement,
)
from product_intelligence.research.sales_unit_extraction import (
    SALES_UNIT_EXTRACTION_SCHEMA_VERSION,
    SalesUnitCueDisposition,
    SalesUnitCueField,
    SalesUnitCueReason,
    SalesUnitCueV1,
    SalesUnitExtractionResult,
    SalesUnitExtractionState,
    SalesUnitIdentifierFieldNoteV1,
)
from product_intelligence.research.semantic_authority_fu3 import (
    IdentityResolutionBoundV2,
    SalesUnitAuthorityV2,
    TargetSalesUnitEvidenceSourceV2,
    TargetSalesUnitEvidenceV2,
    TargetSalesUnitFormV2,
)
from product_intelligence.research.semantic_authority_fu4 import (
    AUTHORITY_CONTRACT_VERSION_V2_FU4,
    AuthorityDecisionV2FU4,
    AuthorityRuleV2FU4,
    BUNDLE_COMPOSITION_EVIDENCE_VERSION_FU4,
    BundleCompositionStateV2FU4,
    BundleQuantityAxisStateV2FU4,
    CandidateBundleCompositionEvidenceV2FU4,
    CandidateCompositionEvidenceBasisV2FU4,
    CompletenessBasisV2FU4,
    CompositionCompletenessAttestationV2FU4,
    EvidenceSideV2FU4,
    QuantityCompletenessAttestationV2FU4,
    QuantityNonMaterialityReasonV2FU4,
    TargetSalesUnitEvidenceV2FU4,
    derive_authority_tier_fu4,
)
from product_intelligence.research.semantic_decision_record import (
    SemanticDecisionCodecError,
    SemanticDecisionContractAdapter,
    SemanticDecisionReplayError,
    _BINDING_KEYS,
    _binding_section,
    _check_keys,
    _dec_bool,
    _dec_int,
    _dec_list,
    _dec_mapping,
    _dec_optional_str,
    _dec_optional_str_enum,
    _dec_required,
    _dec_sorted_unique_str_list,
    _dec_str,
    _dec_str_enum,
    _dec_str_list,
    _validate_binding_fields,
    _validate_digest,
    _validate_str,
    _validate_timestamp,
    canonical_sha256,
)
from product_intelligence.research.semantic_decision_v2 import (
    SEMANTIC_CONTRACT_VERSION_V2,
    SEMANTIC_INPUT_SCHEMA_VERSION_V2,
    SEMANTIC_OUTPUT_SCHEMA_VERSION_V2,
    PRIMARY_PROVIDER_V2,
    PRIMARY_MODEL_V2,
    FALLBACK_PROVIDER_V2,
    FALLBACK_MODEL_V2,
    _V2_CONTRACT_KEYS,
    _V2_EVALUATION_KEYS,
    _V2_EXECUTION_KEYS,
    _V2_INTEGRITY_KEYS,
    _V2_ONE_ATTEMPT_FAILURE_CLASSES,
    _V2_TWO_ATTEMPT_FAILURE_CLASSES,
    _dec_v2_attribute_list,
    _dec_v2_attempt,
    _dec_v2_case,
    _v2_evaluation_section,
    _v2_execution_section,
)

__all__ = [
    "FALLBACK_MODEL_V2_FU4",
    "FALLBACK_PROVIDER_V2_FU4",
    "PRIMARY_MODEL_V2_FU4",
    "PRIMARY_PROVIDER_V2_FU4",
    "PROMPT_VERSION_V2_FU4",
    "SEMANTIC_CONTRACT_VERSION_V2_FU4",
    "SEMANTIC_INPUT_SCHEMA_VERSION_V2_FU4",
    "SEMANTIC_OUTPUT_SCHEMA_VERSION_V2_FU4",
    "SEMANTIC_V2_FU4_ADAPTER",
    "V2_FU4_AUTHORITY_QUALIFIED",
    "V2_FU4_CONTRACT_BINDING",
    "SemanticDecisionReplayV2FU4",
    "SemanticDecisionRecordV2FU4",
    "SemanticV2FU4ContractAdapter",
    "encode_v2_fu4_payload",
    "record_input_digest_v2_fu4",
    "record_output_digest_v2_fu4",
    "reconstruct_identity_context_v2_fu4",
    "reconstruct_semantic_evaluation_v2_fu4",
    "replay_v2_fu4_record",
]


# ---------------------------------------------------------------------------
# The FU4 contract identity (owned by THIS adapter, not by the envelope)
# ---------------------------------------------------------------------------

SEMANTIC_CONTRACT_VERSION_V2_FU4: Final[str] = "V2"
"""The final Semantic V2 contract this adapter interprets: the S2-C
frozen V2 input / output contracts, prompt 2.1, the pinned route, the
strict structured response — IDENTICAL to the V2 adapter's semantic
contract axis (FU4 governs the AUTHORITY layer downstream of the
recorded decision; the envelope dispatch key stays "V2" — the
disambiguation design section 4.3 relies on this). The FU4 line is
discriminated by the full recorded five-axis binding (axis 5 = the FU4
token), never by a new semantic-contract string (a new string would make
the recorded payload's contract section disagree with the binding's
axis 0 — a silent reinterpretation of a version axis)."""

PROMPT_VERSION_V2_FU4: Final[str] = "2.1"
"""The exact prompt version of the FU4 record binding (mirrors
``semantic.contract_v2_1.SEMANTIC_PROMPT_VERSION_V2_1``; drift-pinned by
tests). NO new prompt version: the 2.1 text names no authority token and
asserts nothing FU4 contradicts (the P3 design §7.4 determination); a
2.2 would be a phantom version."""

SEMANTIC_INPUT_SCHEMA_VERSION_V2_FU4: Final[int] = 1
"""Version of the recorded input section — the EXACT V2 case (input
schema 1 is byte-identical under the FU4 binding: the composition facts
are DERIVATION-INPUT records presented to the derivation, never case
fields — the P3 D2 / FU3 target-record precedent)."""

SEMANTIC_OUTPUT_SCHEMA_VERSION_V2_FU4: Final[int] = 1
"""Version of the recorded output section — the strict 7-key structured
response (identical under every binding — the Q3-B4 §5.6 invariance)."""

#: The EXACT contract binding this adapter interprets and replays:
#: (semantic contract, prompt, input schema, output schema, authority
#: contract). One entry. The authority axis is the separately versioned
#: FU4 token (imported — no literal token in this source). A future
#: binding is a future adapter — never an implicit reinterpretation of
#: this one. The existing 2.1/FU3 binding is NOT reused for changed
#: authority semantics (the P3 design §7.4).
V2_FU4_CONTRACT_BINDING: Final[tuple[str, str, int, int, str]] = (
    SEMANTIC_CONTRACT_VERSION_V2_FU4,
    PROMPT_VERSION_V2_FU4,
    SEMANTIC_INPUT_SCHEMA_VERSION_V2_FU4,
    SEMANTIC_OUTPUT_SCHEMA_VERSION_V2_FU4,
    AUTHORITY_CONTRACT_VERSION_V2_FU4,
)

# The pinned route — the SAME frozen qualified route identities the V2
# adapter pins (identical values; mirrored here as FU4 contract data and
# drift-pinned by tests against both the V2 adapter and the V2 runtime).
# A FU4-bound record's attempts followed this exact route — any other
# provider/model in a FU4 record is a FU4 contract violation and fails
# closed. This is a rule of the FU4 record contract, NOT an invariant of
# the persistence envelope.
PRIMARY_PROVIDER_V2_FU4: Final[str] = "amax"
PRIMARY_MODEL_V2_FU4: Final[str] = "qwen3.8-27b"
FALLBACK_PROVIDER_V2_FU4: Final[str] = "vllm-262k"
FALLBACK_MODEL_V2_FU4: Final[str] = "Qwen3.6-27B-262K"

#: The explicit qualification-boundary marker (mirrored; drift-pinned by
#: tests against the V2 runtime / V2 adapter markers): registering the
#: FU4 binding in the codec / replay union is NOT a qualification. The
#: FU4 route is NOT qualified; no production authority code path treats
#: a FU4 record's MATCH/HIGH as pricing-authoritative. A qualification
#: under the FU4 binding is a separate governance event (its own marker
#: flip + the W1 atomic consumer guard).
V2_FU4_AUTHORITY_QUALIFIED: Final[bool] = False


# ---------------------------------------------------------------------------
# The FU4 section encodings (the exact FU4 payload shapes)
# ---------------------------------------------------------------------------


def _fu4_contract_section() -> dict[str, object]:
    """The FU4 contract binding section (frozen; see module constants)."""
    return {
        "semantic_contract_version": SEMANTIC_CONTRACT_VERSION_V2_FU4,
        "prompt_version": PROMPT_VERSION_V2_FU4,
        "input_schema_version": SEMANTIC_INPUT_SCHEMA_VERSION_V2_FU4,
        "output_schema_version": SEMANTIC_OUTPUT_SCHEMA_VERSION_V2_FU4,
        "authority_contract_version": AUTHORITY_CONTRACT_VERSION_V2_FU4,
    }


def _fu4_attestation_document(
    attestation: CompositionCompletenessAttestationV2FU4 | None,
) -> dict[str, object] | None:
    """The completeness-attestation payload document: the attestation's
    canonical document PLUS its self-verifying ``attestation_digest``
    (the constructor requires the digest field; the record's
    ``evidence_digest`` covers the canonical-minus-digest form)."""
    if attestation is None:
        return None
    return {
        **attestation.canonical(),
        "attestation_digest": attestation.attestation_digest,
    }


def _fu4_extraction_result_document(
    result: SalesUnitExtractionResult | None,
) -> dict[str, object] | None:
    """The embedded original extraction-result payload document: the
    result's canonical document (schema v1, every cue with its full
    provenance, the established unit, ``input_digest``) PLUS its
    self-verifying ``result_digest``."""
    if result is None:
        return None
    return {
        **result.canonical(),
        "result_digest": result.result_digest,
    }


def _fu4_candidate_composition_document(
    record: CandidateBundleCompositionEvidenceV2FU4 | None,
) -> dict[str, object] | None:
    """The candidate composition payload document: the v3 record's FULL
    canonical document (including ``schema_version: 3``, the embedded
    attestation's document WITH its digest, and — for the
    EXTRACTION_RESULT_V1 basis — the embedded original result's document
    WITH both digests) PLUS the record's ``evidence_digest``."""
    if record is None:
        return None
    return {
        **record.canonical(),
        "completeness_attestation": _fu4_attestation_document(
            record.completeness_attestation
        ),
        "extraction_result": _fu4_extraction_result_document(
            record.extraction_result
        ),
        "evidence_digest": record.evidence_digest,
    }


def _fu4_target_fu4_document(
    record: TargetSalesUnitEvidenceV2FU4,
) -> dict[str, object]:
    """The target evidence payload document for the ``fu4_v3`` shape:
    the FU4 target record's canonical document (with
    ``schema_version: 3``) PLUS its ``evidence_digest``."""
    return {
        **record.canonical(),
        "completeness_attestation": _fu4_attestation_document(
            record.completeness_attestation
        ),
        "evidence_digest": record.evidence_digest,
    }


def _fu4_target_evidence_document(
    target: (
        TargetSalesUnitEvidenceV2FU4 | TargetSalesUnitEvidenceV2 | None
    ),
) -> dict[str, object] | None:
    """The target evidence payload document — the EXPLICIT bounded shape
    discriminator (design DEC-8; no shape inference at decode):
    ``None`` = the default single unit (no target record presented);
    ``{"schema": "frozen_fu3", "document": …}`` = the frozen FU3
    record's three fields as recorded (read as composition-ABSENT under
    FU4 — D18, a property of the FU4 token + the frozen record);
    ``{"schema": "fu4_v3", "document": …}`` = the versioned FU4 target
    record."""
    if target is None:
        return None
    if isinstance(target, TargetSalesUnitEvidenceV2FU4):
        return {
            "schema": "fu4_v3",
            "document": _fu4_target_fu4_document(target),
        }
    return {
        "schema": "frozen_fu3",
        "document": {
            "form": target.form.value,
            "quantity": target.quantity,
            "source": target.source.value,
        },
    }


def _fu4_quantity_attestation_document(
    attestation: QuantityCompletenessAttestationV2FU4 | None,
) -> dict[str, object] | None:
    """The quantity attestation payload document: the canonical document
    (with ``schema_version: 3``) PLUS its ``attestation_digest``."""
    if attestation is None:
        return None
    return {
        **attestation.canonical(),
        "attestation_digest": attestation.attestation_digest,
    }


def _fu4_authority_section(
    candidate_composition: CandidateBundleCompositionEvidenceV2FU4 | None,
    target_evidence: (
        TargetSalesUnitEvidenceV2FU4 | TargetSalesUnitEvidenceV2 | None
    ),
    quantity_attestation: QuantityCompletenessAttestationV2FU4 | None,
) -> dict[str, object]:
    """The NEW FU4 authority-evidence section (the exact key set): the
    three version-owned evidence documents, each self-versioned and
    digest-sealed (or an explicit null — nullable means the key is
    present with a null value, never an absent key)."""
    return {
        "candidate_composition": _fu4_candidate_composition_document(
            candidate_composition
        ),
        "target_evidence": _fu4_target_evidence_document(target_evidence),
        "quantity_attestation": _fu4_quantity_attestation_document(
            quantity_attestation
        ),
    }


def _fu4_derived_section(
    product_evidence_quality: ProductEvidenceQuality,
    relationship_authority: RelationshipAuthority,
    authority_tier: AuthorityTier,
    fired_rules: frozenset[AuthorityRuleV2FU4],
    identity_resolution_bound: IdentityResolutionBoundV2,
    sales_unit_authority: SalesUnitAuthorityV2,
    quantity_axis_state: BundleQuantityAxisStateV2FU4 | None,
    candidate_composition_state: BundleCompositionStateV2FU4 | None,
    target_composition_state: BundleCompositionStateV2FU4 | None,
    candidate_completeness_attestation_digest: str | None,
    target_completeness_attestation_digest: str | None,
    quantity_attestation_digest: str | None,
) -> dict[str, object]:
    """The FU4 derived section — the full ``AuthorityDecisionV2FU4``
    audit surface (the frozen S2-A snapshots + the identity-resolution
    bound + the sales-unit authority + the six bounded bundle-axis audit
    fields — explicit null for non-bundle channels; the determinations
    are RECORDED, never silent)."""
    return {
        "product_evidence_quality": product_evidence_quality.value,
        "relationship_authority": relationship_authority.value,
        "authority_tier": authority_tier.value,
        "fired_rules": sorted(rule.value for rule in fired_rules),
        "identity_resolution_bound": identity_resolution_bound.value,
        "sales_unit_authority": sales_unit_authority.value,
        "quantity_axis_state": (
            quantity_axis_state.value
            if quantity_axis_state is not None
            else None
        ),
        "candidate_composition_state": (
            candidate_composition_state.value
            if candidate_composition_state is not None
            else None
        ),
        "target_composition_state": (
            target_composition_state.value
            if target_composition_state is not None
            else None
        ),
        "candidate_completeness_attestation_digest": (
            candidate_completeness_attestation_digest
        ),
        "target_completeness_attestation_digest": (
            target_completeness_attestation_digest
        ),
        "quantity_attestation_digest": quantity_attestation_digest,
    }


# ---------------------------------------------------------------------------
# The FU4 typed record (the version-owned artifact of the FU4 binding)
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class SemanticDecisionRecordV2FU4:
    """One complete, immutable Semantic V2 / FU4 decision / provenance
    artifact for one candidate assessment of one research run (Q3-B5-P5
    R1 — the THIRD registered semantic contract adapter's typed record).

    This is the FU4 record — a NEW type (FIND-2 / DEC-7): the frozen V2
    record type exactly pins prompt "2.0" + authority FU2 and cannot
    carry the FU4 binding; the per-binding discipline (Q3-B4 §6.1 item
    5) requires this binding's record to carry the derived snapshots OF
    THE FU4 TOKEN under a record type that cannot be mis-bound. The
    universal envelope (the runs row + the payload framing) is
    contract-agnostic; every version-specific rule of this record — the
    exact FU4 contract binding, the pinned route, the FU4 section
    shapes, the FU4 digest layout — is a rule of the FU4 record contract
    owned by this adapter.

    Sections
    --------

    * **binding** — the universal persistence binding (run identity, the
      assessment's stable position in the run's ordered assessment
      tuple, the listing source URL);
    * **contract** — the EXACT FU4 binding (semantic contract V2, prompt
      2.1, input schema 1, output schema 1, authority
      ``SEMANTIC_AUTHORITY_V2_S2A_FU4``); the adapter refuses any other
      binding;
    * **case** — the EXACT final V2 input (``SemanticMatchCaseV2``;
      input schema 1 — byte-identical in shape under the FU4 binding:
      the composition facts are DERIVATION-INPUT records, never case
      fields);
    * **evaluation** — the recorded strict structured V2 output (output
      schema 1 — identical under every binding);
    * **execution** — the recorded runtime provenance (attempts in call
      order on the pinned route, fallback use/reason, bounded failure
      class, actual provider/model, evaluation instants);
    * **derived** — the FU4 derived audit snapshots: the frozen S2-A
      snapshots (product evidence quality, relationship authority,
      authority tier, fired rules — the FU4 rule vocabulary) PLUS the
      identity-resolution bound, the sales-unit authority, and the six
      bounded bundle-axis audit fields (exactly None for non-bundle
      channels — the determinations are recorded, never silent); the
      stored section must be a VALID ``AuthorityDecisionV2FU4`` (the
      firewall invariants are enforced at construction — an
      AI_ASSISTED_COMPARABLE + UNPROVEN / CONTRADICTED exposure is
      un-constructible, hence undecodable);
    * **authority** — the NEW version-owned evidence: the v3 candidate
      composition record (digest-bound; the EXTRACTION_RESULT_V1 basis
      carries the EXACT original ``SalesUnitExtractionResult`` within
      its ``evidence_digest``), the target evidence (the explicit
      absent / frozen_fu3 / fu4_v3 shapes — the discriminator records
      WHICH record shape the derivation consumed), the quantity-
      completeness attestation (when present);
    * **integrity** — self-verifying input/output section digests
      (``input_digest`` = canonical over {binding, contract, case};
      ``output_digest`` = canonical over {evaluation, execution,
      authority, derived}).

    The record stores no float, reads no clock, performs no I/O, and
    grants no authority: it is a record of what happened, verifiable
    under the FU4 contract binding.
    """

    # -- universal binding (envelope-level addressing) -------------------------
    run_id: str
    assessment_index: int
    source_url: str

    # -- FU4 contract binding (adapter-owned identity) --------------------------
    semantic_contract_version: str
    prompt_version: str
    input_schema_version: int
    output_schema_version: int
    authority_contract_version: str

    # -- exact recorded V2 input (case; input schema 1, byte-identical shape) ---
    case: SemanticMatchCaseV2

    # -- recorded strict structured V2 output (output schema 1) -----------------
    evaluation_state: SemanticEvaluationStateV2
    decision: V2SemanticDecision | None
    confidence: V2Confidence | None
    reason_code: SemanticReasonCodeV2 | None
    conflict_classes: frozenset[ConflictClass]
    matched_attributes: tuple[SemanticAttributeV2, ...]
    conflicting_attributes: tuple[SemanticAttributeV2, ...]
    missing_critical_attributes: tuple[SemanticAttributeDimensionV2, ...]

    # -- recorded runtime provenance (the pinned route) ---------------------------
    attempts: tuple[SemanticDecisionAttempt, ...]
    fallback_used: bool
    fallback_reason: SemanticFallbackReason | None
    error_type: SemanticFailureClass | None
    actual_provider: str | None
    actual_model: str | None
    evaluation_started_at: str | None
    evaluation_finished_at: str | None

    # -- FU4 derived audit snapshots (replay proves agreement) -------------------
    product_evidence_quality: ProductEvidenceQuality
    relationship_authority: RelationshipAuthority
    authority_tier: AuthorityTier
    fired_rules: frozenset[AuthorityRuleV2FU4]
    identity_resolution_bound: IdentityResolutionBoundV2
    sales_unit_authority: SalesUnitAuthorityV2
    quantity_axis_state: BundleQuantityAxisStateV2FU4 | None
    candidate_composition_state: BundleCompositionStateV2FU4 | None
    target_composition_state: BundleCompositionStateV2FU4 | None
    candidate_completeness_attestation_digest: str | None
    target_completeness_attestation_digest: str | None
    quantity_attestation_digest: str | None

    # -- FU4 authority evidence (the version-owned section) ----------------------
    candidate_composition: CandidateBundleCompositionEvidenceV2FU4 | None
    target_evidence: (
        TargetSalesUnitEvidenceV2FU4 | TargetSalesUnitEvidenceV2 | None
    )
    quantity_attestation: QuantityCompletenessAttestationV2FU4 | None

    # -- integrity -------------------------------------------------------------------
    input_digest: str
    output_digest: str

    def __post_init__(self) -> None:
        self._validate_types()
        self._validate_binding()
        self._validate_contract_binding()
        self._validate_evaluation_and_execution()
        self._validate_authority_evidence()
        self._validate_derived()
        self._validate_digests()

    # -- type validation ------------------------------------------------------------

    def _validate_types(self) -> None:
        if not isinstance(self.case, SemanticMatchCaseV2):
            raise TypeError(
                "case must be SemanticMatchCaseV2, "
                f"got {type(self.case).__name__}"
            )
        if not isinstance(
            self.evaluation_state, SemanticEvaluationStateV2
        ):
            raise TypeError(
                "evaluation_state must be SemanticEvaluationStateV2, "
                f"got {type(self.evaluation_state).__name__}"
            )
        if (
            self.decision is not None
            and not isinstance(self.decision, V2SemanticDecision)
        ):
            raise TypeError(
                "decision must be V2SemanticDecision or None, "
                f"got {type(self.decision).__name__}"
            )
        if (
            self.confidence is not None
            and not isinstance(self.confidence, V2Confidence)
        ):
            raise TypeError(
                "confidence must be V2Confidence or None, "
                f"got {type(self.confidence).__name__}"
            )
        if (
            self.reason_code is not None
            and not isinstance(self.reason_code, SemanticReasonCodeV2)
        ):
            raise TypeError(
                "reason_code must be SemanticReasonCodeV2 or None, "
                f"got {type(self.reason_code).__name__}"
            )
        if not isinstance(self.conflict_classes, frozenset):
            raise TypeError(
                "conflict_classes must be a frozenset, "
                f"got {type(self.conflict_classes).__name__}"
            )
        for conflict in self.conflict_classes:
            if not isinstance(conflict, ConflictClass):
                raise TypeError(
                    "conflict_classes must contain only ConflictClass "
                    f"members, got {conflict!r}"
                )
        for name in ("matched_attributes", "conflicting_attributes"):
            value = getattr(self, name)
            if not isinstance(value, tuple):
                raise TypeError(
                    f"{name} must be a tuple, got {type(value).__name__}"
                )
            for i, item in enumerate(value):
                if not isinstance(item, SemanticAttributeV2):
                    raise TypeError(
                        f"{name}[{i}] must be SemanticAttributeV2, "
                        f"got {type(item).__name__}"
                    )
        if not isinstance(self.missing_critical_attributes, tuple):
            raise TypeError(
                "missing_critical_attributes must be a tuple, "
                f"got {type(self.missing_critical_attributes).__name__}"
            )
        for i, item in enumerate(self.missing_critical_attributes):
            if not isinstance(item, SemanticAttributeDimensionV2):
                raise TypeError(
                    f"missing_critical_attributes[{i}] must be "
                    "SemanticAttributeDimensionV2, "
                    f"got {type(item).__name__}"
                )
        if not isinstance(self.attempts, tuple):
            raise TypeError(
                f"attempts must be a tuple, got {type(self.attempts).__name__}"
            )
        for i, attempt in enumerate(self.attempts):
            if not isinstance(attempt, SemanticDecisionAttempt):
                raise TypeError(
                    f"attempts[{i}] must be SemanticDecisionAttempt, "
                    f"got {type(attempt).__name__}"
                )
        if not isinstance(self.fallback_used, bool):
            raise TypeError(
                "fallback_used must be bool, "
                f"got {type(self.fallback_used).__name__}"
            )
        if (
            self.fallback_reason is not None
            and not isinstance(self.fallback_reason, SemanticFallbackReason)
        ):
            raise TypeError(
                "fallback_reason must be SemanticFallbackReason or None, "
                f"got {type(self.fallback_reason).__name__}"
            )
        if (
            self.error_type is not None
            and not isinstance(self.error_type, SemanticFailureClass)
        ):
            raise TypeError(
                "error_type must be SemanticFailureClass or None, "
                f"got {type(self.error_type).__name__}"
            )
        if self.actual_provider is not None:
            _validate_str(
                self.actual_provider, "actual_provider", allow_empty=False
            )
        if self.actual_model is not None:
            _validate_str(self.actual_model, "actual_model", allow_empty=False)
        _validate_timestamp(self.evaluation_started_at, "evaluation_started_at")
        _validate_timestamp(self.evaluation_finished_at, "evaluation_finished_at")
        if not isinstance(
            self.product_evidence_quality, ProductEvidenceQuality
        ):
            raise TypeError(
                "product_evidence_quality must be ProductEvidenceQuality, "
                f"got {type(self.product_evidence_quality).__name__}"
            )
        if not isinstance(
            self.relationship_authority, RelationshipAuthority
        ):
            raise TypeError(
                "relationship_authority must be RelationshipAuthority, "
                f"got {type(self.relationship_authority).__name__}"
            )
        if not isinstance(self.authority_tier, AuthorityTier):
            raise TypeError(
                "authority_tier must be AuthorityTier, "
                f"got {type(self.authority_tier).__name__}"
            )
        if not isinstance(self.fired_rules, frozenset):
            raise TypeError(
                "fired_rules must be a frozenset, "
                f"got {type(self.fired_rules).__name__}"
            )
        for rule in self.fired_rules:
            if not isinstance(rule, AuthorityRuleV2FU4):
                raise TypeError(
                    "fired_rules must contain only AuthorityRuleV2FU4 "
                    f"members, got {rule!r}"
                )
        if not isinstance(
            self.identity_resolution_bound, IdentityResolutionBoundV2
        ):
            raise TypeError(
                "identity_resolution_bound must be IdentityResolutionBoundV2, "
                f"got {type(self.identity_resolution_bound).__name__}"
            )
        if not isinstance(
            self.sales_unit_authority, SalesUnitAuthorityV2
        ):
            raise TypeError(
                "sales_unit_authority must be SalesUnitAuthorityV2, "
                f"got {type(self.sales_unit_authority).__name__}"
            )
        for name, expected in (
            ("quantity_axis_state", BundleQuantityAxisStateV2FU4),
            ("candidate_composition_state", BundleCompositionStateV2FU4),
            ("target_composition_state", BundleCompositionStateV2FU4),
        ):
            value = getattr(self, name)
            if value is None:
                continue
            if not isinstance(value, expected):
                raise TypeError(
                    f"{name} must be {expected.__name__} or None (the "
                    "bounded bundle-axis audit field), got "
                    f"{type(value).__name__}"
                )
        for name in (
            "candidate_completeness_attestation_digest",
            "target_completeness_attestation_digest",
            "quantity_attestation_digest",
        ):
            value = getattr(self, name)
            if value is not None and not isinstance(value, str):
                raise TypeError(
                    f"{name} must be str or None, got "
                    f"{type(value).__name__}"
                )
        # -- the FU4 authority evidence (the version-owned section) -------------
        if self.candidate_composition is not None and not isinstance(
            self.candidate_composition,
            CandidateBundleCompositionEvidenceV2FU4,
        ):
            raise TypeError(
                "candidate_composition must be "
                "CandidateBundleCompositionEvidenceV2FU4 or None, got "
                f"{type(self.candidate_composition).__name__}"
            )
        if self.target_evidence is not None and not isinstance(
            self.target_evidence,
            (TargetSalesUnitEvidenceV2FU4, TargetSalesUnitEvidenceV2),
        ):
            raise TypeError(
                "target_evidence must be TargetSalesUnitEvidenceV2FU4, the "
                "frozen TargetSalesUnitEvidenceV2, or None (the default "
                "single unit), got "
                f"{type(self.target_evidence).__name__}"
            )
        if self.quantity_attestation is not None and not isinstance(
            self.quantity_attestation,
            QuantityCompletenessAttestationV2FU4,
        ):
            raise TypeError(
                "quantity_attestation must be "
                "QuantityCompletenessAttestationV2FU4 or None, got "
                f"{type(self.quantity_attestation).__name__}"
            )

    # -- universal binding (validated by the envelope foundation) ----------------

    def _validate_binding(self) -> None:
        _validate_binding_fields(
            self.run_id, self.assessment_index, self.source_url
        )

    # -- FU4 contract binding (the adapter's exact pin) ---------------------------

    def _validate_contract_binding(self) -> None:
        # The FU4 adapter interprets exactly one contract binding.
        # Anything else is outside this adapter's safe-replay envelope
        # and fails closed at construction (never silently
        # reinterpreted — the anti-reinterpretation invariant, mirror
        # of the V2 record's frozen pin).
        if self.semantic_contract_version != SEMANTIC_CONTRACT_VERSION_V2_FU4:
            raise ValueError(
                "semantic_contract_version must be "
                f"{SEMANTIC_CONTRACT_VERSION_V2_FU4!r} for this FU4 record, "
                f"got {self.semantic_contract_version!r}; an artifact "
                "bound to another semantic contract is outside the FU4 "
                "adapter and fails closed"
            )
        if self.prompt_version != PROMPT_VERSION_V2_FU4:
            raise ValueError(
                "prompt_version must be "
                f"{PROMPT_VERSION_V2_FU4!r} for the FU4 binding, got "
                f"{self.prompt_version!r}"
            )
        for name, value, expected in (
            (
                "input_schema_version",
                self.input_schema_version,
                SEMANTIC_INPUT_SCHEMA_VERSION_V2_FU4,
            ),
            (
                "output_schema_version",
                self.output_schema_version,
                SEMANTIC_OUTPUT_SCHEMA_VERSION_V2_FU4,
            ),
        ):
            if isinstance(value, bool) or not isinstance(value, int):
                raise TypeError(
                    f"{name} must be int, got {type(value).__name__}"
                )
            if value != expected:
                raise ValueError(
                    f"{name} must be {expected} for the FU4 binding, "
                    f"got {value}"
                )
        if self.authority_contract_version != AUTHORITY_CONTRACT_VERSION_V2_FU4:
            raise ValueError(
                "authority_contract_version must be "
                f"{AUTHORITY_CONTRACT_VERSION_V2_FU4!r} for the FU4 "
                "binding, got "
                f"{self.authority_contract_version!r}; the derived audit "
                "snapshots of this artifact were produced under the "
                "exact bound authority contract (the FU4 token), and no "
                "other"
            )

    # -- evaluation + execution coherence (the FU4 route pin lives here) ----------

    def _validate_evaluation_and_execution(self) -> None:
        state = self.evaluation_state

        if state is SemanticEvaluationStateV2.NOT_EVALUATED:
            # No call happened: no output, no execution, no instants.
            for name, value in (
                ("decision", self.decision),
                ("confidence", self.confidence),
                ("reason_code", self.reason_code),
                ("error_type", self.error_type),
                ("actual_provider", self.actual_provider),
                ("actual_model", self.actual_model),
                ("evaluation_started_at", self.evaluation_started_at),
                ("evaluation_finished_at", self.evaluation_finished_at),
            ):
                if value is not None:
                    raise ValueError(
                        f"NOT_EVALUATED may not carry {name}; a record "
                        "that was never evaluated has no semantic output "
                        "and no runtime provenance (absence is never "
                        "defaulted)"
                    )
            if self.conflict_classes:
                raise ValueError(
                    "NOT_EVALUATED may not carry conflict classes; "
                    "conflicts are observed by an evaluation"
                )
            if (
                self.matched_attributes
                or self.conflicting_attributes
                or self.missing_critical_attributes
            ):
                raise ValueError(
                    "NOT_EVALUATED may not carry recorded attribute lists"
                )
            if self.attempts:
                raise ValueError(
                    "NOT_EVALUATED may not carry attempts; no provider "
                    "was called"
                )
            if self.fallback_used or self.fallback_reason is not None:
                raise ValueError(
                    "NOT_EVALUATED may not record fallback use or a "
                    "fallback reason"
                )
            return

        # EVALUATED and RUNTIME_FAILURE both attempted: instants required.
        if (
            self.evaluation_started_at is None
            or self.evaluation_finished_at is None
        ):
            raise ValueError(f"{state.value} requires both evaluation instants")
        started = datetime.fromisoformat(
            self.evaluation_started_at.replace("Z", "+00:00")
        )
        finished = datetime.fromisoformat(
            self.evaluation_finished_at.replace("Z", "+00:00")
        )
        if finished < started:
            raise ValueError(
                "evaluation_finished_at must not precede "
                "evaluation_started_at"
            )

        attempt_count = len(self.attempts)
        if attempt_count not in (1, 2):
            raise ValueError(
                f"{state.value} requires exactly one or two recorded "
                f"attempts, got {attempt_count}"
            )
        # Role / number / route pinning (the FU4 record contract = the
        # pinned route; the attempts are recorded in call order).
        for i, attempt in enumerate(self.attempts):
            if attempt.attempt_number != i + 1:
                raise ValueError(
                    f"attempts[{i}].attempt_number must be {i + 1} "
                    f"(call order), got {attempt.attempt_number}"
                )
            if i == 0:
                if (
                    attempt.provider != PRIMARY_PROVIDER_V2_FU4
                    or attempt.model != PRIMARY_MODEL_V2_FU4
                ):
                    raise ValueError(
                        "the primary attempt of a FU4-bound record must "
                        f"be the pinned primary {PRIMARY_PROVIDER_V2_FU4}/"
                        f"{PRIMARY_MODEL_V2_FU4}, got "
                        f"{attempt.provider}/{attempt.model}"
                    )
            else:
                if (
                    attempt.provider != FALLBACK_PROVIDER_V2_FU4
                    or attempt.model != FALLBACK_MODEL_V2_FU4
                ):
                    raise ValueError(
                        "the fallback attempt of a FU4-bound record must "
                        f"be the pinned fallback {FALLBACK_PROVIDER_V2_FU4}/"
                        f"{FALLBACK_MODEL_V2_FU4}, got "
                        f"{attempt.provider}/{attempt.model}"
                    )

        if attempt_count == 2 and not self.fallback_used:
            raise ValueError(
                "fallback_used must be True when two attempts were "
                "recorded"
            )
        if attempt_count == 1 and self.fallback_used:
            raise ValueError(
                "fallback_used must be False when one attempt was "
                "recorded"
            )
        if attempt_count == 2 and self.fallback_reason is None:
            raise ValueError(
                "a two-attempt record must record the fallback reason"
            )
        if (
            attempt_count == 2
            and self.fallback_reason is SemanticFallbackReason.NONE
        ):
            raise ValueError(
                "the recorded fallback reason must not be NONE when a "
                "fallback attempt was made"
            )
        if attempt_count == 1 and self.fallback_reason is not None:
            raise ValueError(
                "a one-attempt record must not carry a fallback reason"
            )

        if state is SemanticEvaluationStateV2.EVALUATED:
            # Success: a strict structured V2 response, an OK final
            # attempt, and provenance attributed to exactly that
            # attempt.
            if (
                self.decision is None
                or self.confidence is None
                or self.reason_code is None
            ):
                raise ValueError(
                    "EVALUATED requires a decision, a confidence, and "
                    "the bounded V2 reason code"
                )
            if self.error_type is not None:
                raise ValueError(
                    "EVALUATED may not carry an error_type; the "
                    "evaluation produced an accepted response"
                )
            if self.attempts[-1].outcome is not AttemptOutcome.OK:
                raise ValueError(
                    "an EVALUATED record must end with an OK attempt"
                )
            if (
                attempt_count == 2
                and self.attempts[0].outcome is AttemptOutcome.OK
            ):
                raise ValueError(
                    "a successful primary is final: a two-attempt "
                    "record cannot have an OK primary attempt"
                )
            ok_attempt = self.attempts[-1]
            if self.actual_provider != ok_attempt.provider:
                raise ValueError(
                    "actual_provider must be the provider of the OK "
                    "attempt"
                )
            if self.actual_model != ok_attempt.model:
                raise ValueError(
                    "actual_model must be the model of the OK attempt"
                )
            # The strict structured V2 output must be coherent under the
            # frozen reason-code rules (unknown decision/confidence/
            # reason codes, unknown conflict classes, missing fields,
            # extra fields, and decision/conflict incoherence all fail
            # closed).
            SemanticMatchResponseV2(
                decision=self.decision,
                confidence=self.confidence,
                reason_code=self.reason_code,
                matched_attributes=self.matched_attributes,
                conflicting_attributes=self.conflicting_attributes,
                missing_critical_attributes=(
                    self.missing_critical_attributes
                ),
                conflict_classes=self.conflict_classes,
            )
        else:  # RUNTIME_FAILURE
            # Failure: never shaped like a decision.
            if (
                self.decision is not None
                or self.confidence is not None
                or self.reason_code is not None
            ):
                raise ValueError(
                    "RUNTIME_FAILURE may not carry a decision, "
                    "confidence, or reason code; a runtime failure is "
                    "never interpreted as NO_MATCH"
                )
            if (
                self.conflict_classes
                or self.matched_attributes
                or self.conflicting_attributes
                or self.missing_critical_attributes
            ):
                raise ValueError(
                    "RUNTIME_FAILURE may not carry conflict classes or "
                    "recorded attribute lists"
                )
            if (
                self.actual_provider is not None
                or self.actual_model is not None
            ):
                raise ValueError(
                    "RUNTIME_FAILURE must not name an actual provider "
                    "or model; no provider produced an accepted "
                    "response"
                )
            if any(
                attempt.outcome is AttemptOutcome.OK
                for attempt in self.attempts
            ):
                raise ValueError(
                    "a RUNTIME_FAILURE record must not contain an OK "
                    "attempt"
                )
            if self.error_type is None:
                raise ValueError(
                    "RUNTIME_FAILURE requires the bounded failure class"
                )
            allowed_family = (
                _V2_ONE_ATTEMPT_FAILURE_CLASSES
                if attempt_count == 1
                else _V2_TWO_ATTEMPT_FAILURE_CLASSES
            )
            if self.error_type not in allowed_family:
                raise ValueError(
                    f"error_type {self.error_type.value} is inconsistent "
                    f"with {attempt_count} recorded attempt(s)"
                )

    # -- the FU4 authority evidence (the version-owned section) -------------------

    def _validate_authority_evidence(self) -> None:
        channel = self.case.candidate_commercial.sales_unit
        if self.candidate_composition is not None:
            # The presentation gate (the v3 original-result
            # association) is REPLAY's verification — the derivation
            # itself is the verifier (no private-gate re-implementation
            # here). At construction the record pins only its own
            # invariants: the evidence schema version, the record's own
            # self-verifying digest, and the channel coherence (a
            # composition record over a non-BUNDLE / UNAVAILABLE
            # channel is contract misuse — the derivation refuses it;
            # the record refuses it too, so the shape is undecodable).
            record = self.candidate_composition
            if (
                record.schema_version
                != BUNDLE_COMPOSITION_EVIDENCE_VERSION_FU4
            ):
                raise ValueError(
                    "the candidate composition evidence must be schema "
                    f"version {BUNDLE_COMPOSITION_EVIDENCE_VERSION_FU4} "
                    f"(the versioned FU4 evidence schema), got "
                    f"{record.schema_version!r}; a superseded or unknown "
                    "evidence version is never silently reinterpreted"
                )
            if (
                channel.state is not PackagingEvidenceStateV2.OBSERVED
                or channel.kind is not SalesUnitKindV2.BUNDLE
            ):
                raise ValueError(
                    "a candidate composition record requires the "
                    "recorded OBSERVED BUNDLE channel (composition is a "
                    "bundle-only fact; an UNAVAILABLE or non-BUNDLE "
                    "channel admits no composition evidence — contract "
                    "misuse, fail closed)"
                )
            record.verify()
        if self.quantity_attestation is not None:
            att = self.quantity_attestation
            if (
                att.schema_version
                != BUNDLE_COMPOSITION_EVIDENCE_VERSION_FU4
            ):
                raise ValueError(
                    "the quantity attestation must be schema version "
                    f"{BUNDLE_COMPOSITION_EVIDENCE_VERSION_FU4} (the "
                    "versioned FU4 evidence schema), got "
                    f"{att.schema_version!r}"
                )
            if (
                channel.state is not PackagingEvidenceStateV2.OBSERVED
                or channel.kind is not SalesUnitKindV2.BUNDLE
            ):
                raise ValueError(
                    "a quantity attestation requires the recorded "
                    "OBSERVED BUNDLE channel (the quantity axis is a "
                    "bundle-only fact; an UNAVAILABLE or non-BUNDLE "
                    "channel admits no quantity attestation — contract "
                    "misuse, fail closed)"
                )
            att.verify()
        if (
            isinstance(self.target_evidence, TargetSalesUnitEvidenceV2FU4)
            and self.target_evidence.schema_version
            != BUNDLE_COMPOSITION_EVIDENCE_VERSION_FU4
        ):
            raise ValueError(
                "the FU4 target evidence must be schema version "
                f"{BUNDLE_COMPOSITION_EVIDENCE_VERSION_FU4} (the "
                "versioned FU4 evidence schema), got "
                f"{self.target_evidence.schema_version!r}"
            )
        if isinstance(self.target_evidence, TargetSalesUnitEvidenceV2FU4):
            self.target_evidence.verify()

    # -- derived snapshots (a valid FU4 decision — the firewall invariants) --------

    def _validate_derived(self) -> None:
        if not self.fired_rules:
            raise ValueError(
                "an authority decision must record at least one fired "
                "rule"
            )
        # The stored derived section must be a VALID FU4 decision: the
        # AuthorityDecisionV2FU4 constructor enforces the same
        # construction invariants the derivation produces (an
        # AI_ASSISTED_COMPARABLE tier with an UNPROVEN or CONTRADICTED
        # unit is un-constructible — the exposure is undecodable, not
        # merely unreplayable; the restrict-only ceilings fire only
        # with their unit state on NEEDS_REVIEW).
        AuthorityDecisionV2FU4(
            tier=self.authority_tier,
            fired_rules=self.fired_rules,
            product_evidence_quality=self.product_evidence_quality,
            relationship_authority=self.relationship_authority,
            identity_resolution_bound=self.identity_resolution_bound,
            sales_unit_authority=self.sales_unit_authority,
            quantity_axis_state=self.quantity_axis_state,
            candidate_composition_state=self.candidate_composition_state,
            target_composition_state=self.target_composition_state,
            candidate_completeness_attestation_digest=(
                self.candidate_completeness_attestation_digest
            ),
            target_completeness_attestation_digest=(
                self.target_completeness_attestation_digest
            ),
            quantity_attestation_digest=self.quantity_attestation_digest,
        )

    # -- integrity self-verification ---------------------------------------------------

    def _validate_digests(self) -> None:
        _validate_digest(self.input_digest, "input_digest")
        _validate_digest(self.output_digest, "output_digest")
        expected_input = record_input_digest_v2_fu4(self)
        expected_output = record_output_digest_v2_fu4(self)
        if self.input_digest != expected_input:
            raise ValueError(
                "input_digest does not agree with the record's input "
                "sections (binding, contract, case); the artifact is "
                "corrupt or was built with the wrong digest"
            )
        if self.output_digest != expected_output:
            raise ValueError(
                "output_digest does not agree with the record's output "
                "sections (evaluation, execution, authority, derived); "
                "the artifact is corrupt or was built with the wrong "
                "digest"
            )

    # -- section accessors (shared by the FU4 codec and the digest functions) -------

    def case_section(self) -> dict[str, object]:
        return self.case.canonical()

    def binding_section(self) -> dict[str, object]:
        return _binding_section(
            self.run_id, self.assessment_index, self.source_url
        )

    def contract_section(self) -> dict[str, object]:
        return _fu4_contract_section()

    def evaluation_section(self) -> dict[str, object]:
        return _v2_evaluation_section(
            self.evaluation_state,
            self.decision,
            self.confidence,
            self.conflict_classes,
            self.reason_code,
            self.matched_attributes,
            self.conflicting_attributes,
            self.missing_critical_attributes,
        )

    def execution_section(self) -> dict[str, object]:
        return _v2_execution_section(
            self.attempts,
            self.fallback_used,
            self.fallback_reason,
            self.error_type,
            self.actual_provider,
            self.actual_model,
            self.evaluation_started_at,
            self.evaluation_finished_at,
        )

    def authority_section(self) -> dict[str, object]:
        return _fu4_authority_section(
            self.candidate_composition,
            self.target_evidence,
            self.quantity_attestation,
        )

    def derived_section(self) -> dict[str, object]:
        return _fu4_derived_section(
            self.product_evidence_quality,
            self.relationship_authority,
            self.authority_tier,
            self.fired_rules,
            self.identity_resolution_bound,
            self.sales_unit_authority,
            self.quantity_axis_state,
            self.candidate_composition_state,
            self.target_composition_state,
            self.candidate_completeness_attestation_digest,
            self.target_completeness_attestation_digest,
            self.quantity_attestation_digest,
        )

    def integrity_section(self) -> dict[str, str]:
        return {
            "input_digest": self.input_digest,
            "output_digest": self.output_digest,
        }

    # -- construction convenience --------------------------------------------------------

    @classmethod
    def build(
        cls,
        *,
        run_id: str,
        assessment_index: int,
        source_url: str,
        case: SemanticMatchCaseV2,
        evaluation_state: SemanticEvaluationStateV2,
        decision: V2SemanticDecision | None,
        confidence: V2Confidence | None,
        reason_code: SemanticReasonCodeV2 | None,
        conflict_classes: frozenset[ConflictClass],
        matched_attributes: tuple[SemanticAttributeV2, ...],
        conflicting_attributes: tuple[SemanticAttributeV2, ...],
        missing_critical_attributes: tuple[SemanticAttributeDimensionV2, ...],
        attempts: tuple[SemanticDecisionAttempt, ...],
        fallback_used: bool,
        fallback_reason: SemanticFallbackReason | None,
        error_type: SemanticFailureClass | None,
        actual_provider: str | None,
        actual_model: str | None,
        evaluation_started_at: str | None,
        evaluation_finished_at: str | None,
        product_evidence_quality: ProductEvidenceQuality,
        relationship_authority: RelationshipAuthority,
        authority_tier: AuthorityTier,
        fired_rules: frozenset[AuthorityRuleV2FU4],
        identity_resolution_bound: IdentityResolutionBoundV2,
        sales_unit_authority: SalesUnitAuthorityV2,
        quantity_axis_state: BundleQuantityAxisStateV2FU4 | None,
        candidate_composition_state: BundleCompositionStateV2FU4 | None,
        target_composition_state: BundleCompositionStateV2FU4 | None,
        candidate_completeness_attestation_digest: str | None,
        target_completeness_attestation_digest: str | None,
        quantity_attestation_digest: str | None,
        candidate_composition: CandidateBundleCompositionEvidenceV2FU4 | None,
        target_evidence: (
            TargetSalesUnitEvidenceV2FU4 | TargetSalesUnitEvidenceV2 | None
        ),
        quantity_attestation: QuantityCompletenessAttestationV2FU4 | None,
    ) -> "SemanticDecisionRecordV2FU4":
        """Build a FU4 record, computing the self-verifying section
        digests. The contract binding is the FU4 frozen one (semantic
        contract V2, prompt 2.1, input/output schema 1, authority
        ``SEMANTIC_AUTHORITY_V2_S2A_FU4``): the builder takes no version
        parameters so a FU4 artifact cannot be bound to a contract this
        adapter does not know.
        """
        input_digest = canonical_sha256(
            {
                "binding": _binding_section(
                    run_id, assessment_index, source_url
                ),
                "contract": _fu4_contract_section(),
                "case": case.canonical(),
            }
        )
        output_digest = canonical_sha256(
            {
                "evaluation": _v2_evaluation_section(
                    evaluation_state,
                    decision,
                    confidence,
                    conflict_classes,
                    reason_code,
                    matched_attributes,
                    conflicting_attributes,
                    missing_critical_attributes,
                ),
                "execution": _v2_execution_section(
                    attempts,
                    fallback_used,
                    fallback_reason,
                    error_type,
                    actual_provider,
                    actual_model,
                    evaluation_started_at,
                    evaluation_finished_at,
                ),
                "authority": _fu4_authority_section(
                    candidate_composition,
                    target_evidence,
                    quantity_attestation,
                ),
                "derived": _fu4_derived_section(
                    product_evidence_quality,
                    relationship_authority,
                    authority_tier,
                    fired_rules,
                    identity_resolution_bound,
                    sales_unit_authority,
                    quantity_axis_state,
                    candidate_composition_state,
                    target_composition_state,
                    candidate_completeness_attestation_digest,
                    target_completeness_attestation_digest,
                    quantity_attestation_digest,
                ),
            }
        )
        return cls(
            run_id=run_id,
            assessment_index=assessment_index,
            source_url=source_url,
            semantic_contract_version=SEMANTIC_CONTRACT_VERSION_V2_FU4,
            prompt_version=PROMPT_VERSION_V2_FU4,
            input_schema_version=SEMANTIC_INPUT_SCHEMA_VERSION_V2_FU4,
            output_schema_version=SEMANTIC_OUTPUT_SCHEMA_VERSION_V2_FU4,
            authority_contract_version=AUTHORITY_CONTRACT_VERSION_V2_FU4,
            case=case,
            evaluation_state=evaluation_state,
            decision=decision,
            confidence=confidence,
            reason_code=reason_code,
            conflict_classes=conflict_classes,
            matched_attributes=matched_attributes,
            conflicting_attributes=conflicting_attributes,
            missing_critical_attributes=missing_critical_attributes,
            attempts=attempts,
            fallback_used=fallback_used,
            fallback_reason=fallback_reason,
            error_type=error_type,
            actual_provider=actual_provider,
            actual_model=actual_model,
            evaluation_started_at=evaluation_started_at,
            evaluation_finished_at=evaluation_finished_at,
            product_evidence_quality=product_evidence_quality,
            relationship_authority=relationship_authority,
            authority_tier=authority_tier,
            fired_rules=fired_rules,
            identity_resolution_bound=identity_resolution_bound,
            sales_unit_authority=sales_unit_authority,
            quantity_axis_state=quantity_axis_state,
            candidate_composition_state=candidate_composition_state,
            target_composition_state=target_composition_state,
            candidate_completeness_attestation_digest=(
                candidate_completeness_attestation_digest
            ),
            target_completeness_attestation_digest=(
                target_completeness_attestation_digest
            ),
            quantity_attestation_digest=quantity_attestation_digest,
            candidate_composition=candidate_composition,
            target_evidence=target_evidence,
            quantity_attestation=quantity_attestation,
            input_digest=input_digest,
            output_digest=output_digest,
        )


def record_input_digest_v2_fu4(record: SemanticDecisionRecordV2FU4) -> str:
    """SHA-256 over the canonical encoding of the FU4 record's INPUT
    sections: binding + contract + the exact recorded V2 input (case).
    The contract section carries the FU4 binding — an FU4 input digest
    is distinct from a same-case FU2 / FU3 input digest by exactly the
    recorded authority axis (the binding is recorded INSIDE the input
    digest — a historical record is un-upgradable to FU4 by
    construction)."""
    return canonical_sha256(
        {
            "binding": record.binding_section(),
            "contract": record.contract_section(),
            "case": record.case_section(),
        }
    )


def record_output_digest_v2_fu4(record: SemanticDecisionRecordV2FU4) -> str:
    """SHA-256 over the canonical encoding of the FU4 record's OUTPUT
    sections: recorded V2 evaluation + recorded execution provenance +
    the FU4 authority evidence + the FU4 derived audit snapshots."""
    return canonical_sha256(
        {
            "evaluation": record.evaluation_section(),
            "execution": record.execution_section(),
            "authority": record.authority_section(),
            "derived": record.derived_section(),
        }
    )


# ---------------------------------------------------------------------------
# The FU4 payload codec (the exact FU4 section shapes; strict, fail closed)
# ---------------------------------------------------------------------------


_V2_FU4_TOP_LEVEL_KEYS: Final[frozenset[str]] = frozenset(
    {
        "schema_version",
        "binding",
        "contract",
        "case",
        "evaluation",
        "execution",
        "derived",
        "authority",
        "integrity",
    }
)

_V2_FU4_DERIVED_KEYS: Final[frozenset[str]] = frozenset(
    {
        "product_evidence_quality",
        "relationship_authority",
        "authority_tier",
        "fired_rules",
        "identity_resolution_bound",
        "sales_unit_authority",
        "quantity_axis_state",
        "candidate_composition_state",
        "target_composition_state",
        "candidate_completeness_attestation_digest",
        "target_completeness_attestation_digest",
        "quantity_attestation_digest",
    }
)

_V2_FU4_AUTHORITY_KEYS: Final[frozenset[str]] = frozenset(
    {
        "candidate_composition",
        "target_evidence",
        "quantity_attestation",
    }
)

_V2_FU4_TARGET_WRAPPED_KEYS: Final[frozenset[str]] = frozenset(
    {"schema", "document"}
)

#: The exact bounded target-evidence shape discriminator (design DEC-8 —
#: no shape inference at decode; an unknown discriminator is a codec
#: error).
_V2_FU4_TARGET_FROZEN = "frozen_fu3"
_V2_FU4_TARGET_FU4_V3 = "fu4_v3"

_V2_FU4_CANDIDATE_DOC_KEYS: Final[frozenset[str]] = frozenset(
    {
        "schema_version",
        "basis",
        "state",
        "completeness_attestation",
        "composition_clause",
        "additional_clauses",
        "source",
        "channel_quantity",
        "extraction_result_digest",
        "extraction_input_digest",
        "extraction_result",
        "channel_content_digest",
        "evidence_digest",
    }
)

_V2_FU4_ATTESTATION_DOC_KEYS: Final[frozenset[str]] = frozenset(
    {
        "schema_version",
        "subject_side",
        "basis",
        "source",
        "clause_digest",
        "attestation_text",
        "attestation_digest",
    }
)

_V2_FU4_RESULT_DOC_KEYS: Final[frozenset[str]] = frozenset(
    {
        "schema_version",
        "state",
        "cues",
        "identifier_field_notes",
        "established_kind",
        "established_quantity",
        "input_digest",
        "result_digest",
    }
)

_V2_FU4_CUE_DOC_KEYS: Final[frozenset[str]] = frozenset(
    {
        "field",
        "source",
        "raw_field_value",
        "cue_text",
        "cue_start",
        "cue_end",
        "kind",
        "quantity",
        "disposition",
        "reason",
    }
)

_V2_FU4_NOTE_DOC_KEYS: Final[frozenset[str]] = frozenset(
    {"field_name", "token_text"}
)

_V2_FU4_TARGET_FU4_DOC_KEYS: Final[frozenset[str]] = frozenset(
    {
        "schema_version",
        "form",
        "quantity",
        "source",
        "composition_clause",
        "composition_state",
        "completeness_attestation",
        "evidence_digest",
    }
)

_V2_FU4_TARGET_FROZEN_DOC_KEYS: Final[frozenset[str]] = frozenset(
    {"form", "quantity", "source"}
)

_V2_FU4_QUANTITY_ATTESTATION_DOC_KEYS: Final[frozenset[str]] = frozenset(
    {
        "schema_version",
        "subject_side",
        "reason",
        "source",
        "attestation_text",
        "attestation_digest",
    }
)


def encode_v2_fu4_payload(
    record: SemanticDecisionRecordV2FU4,
) -> dict[str, object]:
    """Encode a ``SemanticDecisionRecordV2FU4`` into the full framed
    payload (envelope schema version 1, semantic contract V2, the FU4
    binding).

    The returned dict contains only native JSON types (str, int, bool,
    list, dict, None) — no enum members, no dataclass objects, no
    floats. Set-valued fields are encoded as sorted unique value lists;
    order-significant fields (attempts, attribute lists, clauses, cues)
    keep their order.

    Raises ``TypeError`` if the input is not a FU4 record (caller
    defect).
    """
    if not isinstance(record, SemanticDecisionRecordV2FU4):
        raise TypeError(
            f"expected SemanticDecisionRecordV2FU4, "
            f"got {type(record).__name__}"
        )
    return {
        "schema_version": 1,
        "binding": record.binding_section(),
        "contract": record.contract_section(),
        "case": record.case_section(),
        "evaluation": record.evaluation_section(),
        "execution": record.execution_section(),
        "derived": record.derived_section(),
        "authority": record.authority_section(),
        "integrity": record.integrity_section(),
    }


def _dec_fu4_attestation(
    raw: object, path: str
) -> CompositionCompletenessAttestationV2FU4:
    """Strict decode of the embedded completeness attestation document
    (the exact canonical key set + ``attestation_digest``; the FU4
    constructor is the validator — the basis / subject-side /
    source-class coherence, the clause_digest binding, and the digest
    self-verification all fail closed here)."""
    doc = _dec_mapping(raw, path)
    _check_keys(doc, _V2_FU4_ATTESTATION_DOC_KEYS, path)
    subject_side = _dec_str_enum(
        EvidenceSideV2FU4,
        _dec_required(doc, "subject_side", path),
        f"{path}.subject_side",
    )
    basis = _dec_str_enum(
        CompletenessBasisV2FU4,
        _dec_required(doc, "basis", path),
        f"{path}.basis",
    )
    source_value = _dec_str(
        _dec_required(doc, "source", path), f"{path}.source", allow_empty=False
    )
    # The subject side's frozen non-model class (both enums share the
    # bounded value set; the constructor re-enforces the coherence).
    if subject_side is EvidenceSideV2FU4.CANDIDATE:
        source = _dec_str_enum(
            CandidateEvidenceSourceV2, source_value, f"{path}.source"
        )
    else:
        source = _dec_str_enum(
            TargetSalesUnitEvidenceSourceV2, source_value, f"{path}.source"
        )
    attestation = CompositionCompletenessAttestationV2FU4(
        _dec_int(
            _dec_required(doc, "schema_version", path),
            f"{path}.schema_version",
        ),
        subject_side,
        basis,
        source,
        _dec_str(
            _dec_required(doc, "clause_digest", path),
            f"{path}.clause_digest",
            allow_empty=False,
        ),
        _dec_str(
            _dec_required(doc, "attestation_text", path),
            f"{path}.attestation_text",
            allow_empty=False,
        ),
        _dec_str(
            _dec_required(doc, "attestation_digest", path),
            f"{path}.attestation_digest",
            allow_empty=False,
        ),
    )
    if doc != {
        **attestation.canonical(),
        "attestation_digest": attestation.attestation_digest,
    }:
        raise SemanticDecisionCodecError(
            f"{path}: the stored attestation document does not round-"
            "trip to the reconstructed attestation (no two documents, "
            "one record)"
        )
    return attestation


def _dec_fu4_cue(raw: object, path: str) -> SalesUnitCueV1:
    """Strict decode of one recorded cue document (the exact key set;
    the frozen cue constructor re-verifies the span-bound provenance —
    a cue cannot claim text its field never published)."""
    doc = _dec_mapping(raw, path)
    _check_keys(doc, _V2_FU4_CUE_DOC_KEYS, path)
    quantity_raw = _dec_required(doc, "quantity", path)
    return SalesUnitCueV1(
        field=_dec_str_enum(
            SalesUnitCueField, _dec_required(doc, "field", path), f"{path}.field"
        ),
        source=_dec_str_enum(
            CandidateEvidenceSourceV2,
            _dec_required(doc, "source", path),
            f"{path}.source",
        ),
        raw_field_value=_dec_str(
            _dec_required(doc, "raw_field_value", path),
            f"{path}.raw_field_value",
            allow_empty=False,
        ),
        cue_text=_dec_str(
            _dec_required(doc, "cue_text", path),
            f"{path}.cue_text",
            allow_empty=False,
        ),
        cue_start=_dec_int(
            _dec_required(doc, "cue_start", path), f"{path}.cue_start"
        ),
        cue_end=_dec_int(
            _dec_required(doc, "cue_end", path), f"{path}.cue_end"
        ),
        kind=_dec_optional_str_enum(
            SalesUnitKindV2, _dec_required(doc, "kind", path), f"{path}.kind"
        ),
        quantity=(
            None if quantity_raw is None else _dec_int(quantity_raw, f"{path}.quantity")
        ),
        disposition=_dec_str_enum(
            SalesUnitCueDisposition,
            _dec_required(doc, "disposition", path),
            f"{path}.disposition",
        ),
        reason=_dec_optional_str_enum(
            SalesUnitCueReason,
            _dec_required(doc, "reason", path),
            f"{path}.reason",
        ),
    )


def _dec_fu4_extraction_result(
    raw: object, path: str
) -> SalesUnitExtractionResult:
    """Strict decode of the embedded original extraction result
    (the exact canonical key set + ``result_digest``; the frozen
    result constructor is the validator — the schema-version pin
    (extraction schema 1), the state/cue/established-unit coherence,
    the cue re-canonicalization, and the non-canonical digest refusal
    all fail closed here; the round-trip check pins the canonical cue
    order)."""
    doc = _dec_mapping(raw, path)
    _check_keys(doc, _V2_FU4_RESULT_DOC_KEYS, path)
    if _dec_int(
        _dec_required(doc, "schema_version", path),
        f"{path}.schema_version",
    ) != SALES_UNIT_EXTRACTION_SCHEMA_VERSION:
        raise SemanticDecisionCodecError(
            f"{path}.schema_version: the embedded extraction result "
            f"must be extraction schema version "
            f"{SALES_UNIT_EXTRACTION_SCHEMA_VERSION} (the frozen P2 "
            "extraction schema), got "
            f"{doc['schema_version']!r} (a superseded or unknown "
            "extraction version is never silently reinterpreted)"
        )
    cues_raw = _dec_list(_dec_required(doc, "cues", path), f"{path}.cues")
    notes_raw = _dec_list(
        _dec_required(doc, "identifier_field_notes", path),
        f"{path}.identifier_field_notes",
    )
    established_quantity_raw = _dec_required(
        doc, "established_quantity", path
    )
    result = SalesUnitExtractionResult(
        _dec_int(
            _dec_required(doc, "schema_version", path),
            f"{path}.schema_version",
        ),
        _dec_str_enum(
            SalesUnitExtractionState,
            _dec_required(doc, "state", path),
            f"{path}.state",
        ),
        tuple(
            _dec_fu4_cue(
                _dec_mapping(item, f"{path}.cues[{i}]"),
                f"{path}.cues[{i}]",
            )
            for i, item in enumerate(cues_raw)
        ),
        tuple(
            SalesUnitIdentifierFieldNoteV1(
                field_name=_dec_str(
                    _dec_required(
                        _dec_mapping(item, f"{path}.identifier_field_notes[{i}]"),
                        "field_name",
                        f"{path}.identifier_field_notes[{i}]",
                    ),
                    f"{path}.identifier_field_notes[{i}].field_name",
                    allow_empty=False,
                ),
                token_text=_dec_str(
                    _dec_required(
                        _dec_mapping(item, f"{path}.identifier_field_notes[{i}]"),
                        "token_text",
                        f"{path}.identifier_field_notes[{i}]",
                    ),
                    f"{path}.identifier_field_notes[{i}].token_text",
                    allow_empty=False,
                ),
            )
            for i, item in enumerate(notes_raw)
        ),
        _dec_optional_str_enum(
            SalesUnitKindV2,
            _dec_required(doc, "established_kind", path),
            f"{path}.established_kind",
        ),
        None
        if established_quantity_raw is None
        else _dec_int(
            established_quantity_raw, f"{path}.established_quantity"
        ),
        _dec_str(
            _dec_required(doc, "input_digest", path),
            f"{path}.input_digest",
            allow_empty=False,
        ),
        _dec_str(
            _dec_required(doc, "result_digest", path),
            f"{path}.result_digest",
            allow_empty=False,
        ),
    )
    if doc != {
        **result.canonical(),
        "result_digest": result.result_digest,
    }:
        raise SemanticDecisionCodecError(
            f"{path}: the stored extraction-result document does not "
            "round-trip to the reconstructed result (no two documents, "
            "one record — the canonical cue order is the only accepted "
            "encoding)"
        )
    return result


def _dec_fu4_candidate_composition(
    raw: object, path: str
) -> CandidateBundleCompositionEvidenceV2FU4:
    """Strict decode of the candidate composition document (the exact
    v3 canonical key set + ``evidence_digest``): field-by-field against
    the exact key set (missing AND extra keys refused; unknown enum
    values refused), typed reconstruction through the FU4 constructor
    (the constructor is the validator — the schema-version pin, the
    state/coherence matrix, the basis/extraction-digest coherence, the
    embedded original-result association invariants, and the
    ``evidence_digest`` re-verification all fail closed here), and the
    round-trip document identity (a document that decodes to a
    different record is refused)."""
    doc = _dec_mapping(raw, path)
    _check_keys(doc, _V2_FU4_CANDIDATE_DOC_KEYS, path)
    attestation_raw = _dec_required(
        doc, "completeness_attestation", path
    )
    result_raw = _dec_required(doc, "extraction_result", path)
    channel_quantity_raw = _dec_required(doc, "channel_quantity", path)
    record = CandidateBundleCompositionEvidenceV2FU4(
        _dec_int(
            _dec_required(doc, "schema_version", path),
            f"{path}.schema_version",
        ),
        _dec_str_enum(
            CandidateCompositionEvidenceBasisV2FU4,
            _dec_required(doc, "basis", path),
            f"{path}.basis",
        ),
        _dec_str_enum(
            BundleCompositionStateV2FU4,
            _dec_required(doc, "state", path),
            f"{path}.state",
        ),
        None
        if attestation_raw is None
        else _dec_fu4_attestation(
            attestation_raw, f"{path}.completeness_attestation"
        ),
        _dec_optional_str(
            _dec_required(doc, "composition_clause", path),
            f"{path}.composition_clause",
        ),
        _dec_str_list(
            _dec_required(doc, "additional_clauses", path),
            f"{path}.additional_clauses",
        ),
        _dec_str_enum(
            CandidateEvidenceSourceV2,
            _dec_required(doc, "source", path),
            f"{path}.source",
        ),
        None
        if channel_quantity_raw is None
        else _dec_int(channel_quantity_raw, f"{path}.channel_quantity"),
        _dec_optional_str(
            _dec_required(doc, "extraction_result_digest", path),
            f"{path}.extraction_result_digest",
        ),
        _dec_optional_str(
            _dec_required(doc, "extraction_input_digest", path),
            f"{path}.extraction_input_digest",
        ),
        None
        if result_raw is None
        else _dec_fu4_extraction_result(result_raw, f"{path}.extraction_result"),
        _dec_str(
            _dec_required(doc, "channel_content_digest", path),
            f"{path}.channel_content_digest",
            allow_empty=False,
        ),
        _dec_str(
            _dec_required(doc, "evidence_digest", path),
            f"{path}.evidence_digest",
            allow_empty=False,
        ),
    )
    if doc != _fu4_candidate_composition_document(record):
        raise SemanticDecisionCodecError(
            f"{path}: the stored candidate-composition document does "
            "not round-trip to the reconstructed record (no two "
            "documents, one record)"
        )
    return record


def _dec_fu4_target_evidence(
    raw: object, path: str
) -> (
    TargetSalesUnitEvidenceV2FU4 | TargetSalesUnitEvidenceV2 | None
):
    """Strict decode of the target evidence (the EXPLICIT bounded shape
    discriminator — design DEC-8; an unknown discriminator is a codec
    error): ``null`` = the default single unit; ``"frozen_fu3"`` = the
    frozen FU3 record's three fields (the frozen constructor is the
    validator); ``"fu4_v3"`` = the versioned FU4 target record (the
    FU4 constructor + the round-trip document identity)."""
    if raw is None:
        return None
    wrapped = _dec_mapping(raw, path)
    _check_keys(wrapped, _V2_FU4_TARGET_WRAPPED_KEYS, path)
    schema = _dec_str(
        _dec_required(wrapped, "schema", path), f"{path}.schema", allow_empty=False
    )
    doc = _dec_required(wrapped, "document", path)
    if schema == _V2_FU4_TARGET_FROZEN:
        d = _dec_mapping(doc, f"{path}.document")
        _check_keys(d, _V2_FU4_TARGET_FROZEN_DOC_KEYS, f"{path}.document")
        quantity_raw = _dec_required(d, "quantity", f"{path}.document")
        target = TargetSalesUnitEvidenceV2(
            _dec_str_enum(
                TargetSalesUnitFormV2,
                _dec_required(d, "form", f"{path}.document"),
                f"{path}.document.form",
            ),
            None
            if quantity_raw is None
            else _dec_int(quantity_raw, f"{path}.document.quantity"),
            _dec_str_enum(
                TargetSalesUnitEvidenceSourceV2,
                _dec_required(d, "source", f"{path}.document"),
                f"{path}.document.source",
            ),
        )
        if d != {
            "form": target.form.value,
            "quantity": target.quantity,
            "source": target.source.value,
        }:
            raise SemanticDecisionCodecError(
                f"{path}.document: the stored frozen-FU3 target document "
                "does not round-trip to the reconstructed record (no two "
                "documents, one record)"
            )
        return target
    if schema == _V2_FU4_TARGET_FU4_V3:
        d = _dec_mapping(doc, f"{path}.document")
        _check_keys(d, _V2_FU4_TARGET_FU4_DOC_KEYS, f"{path}.document")
        attestation_raw = _dec_required(
            d, "completeness_attestation", f"{path}.document"
        )
        quantity_raw = _dec_required(d, "quantity", f"{path}.document")
        target = TargetSalesUnitEvidenceV2FU4(
            _dec_int(
                _dec_required(d, "schema_version", f"{path}.document"),
                f"{path}.document.schema_version",
            ),
            _dec_str_enum(
                TargetSalesUnitFormV2,
                _dec_required(d, "form", f"{path}.document"),
                f"{path}.document.form",
            ),
            None
            if quantity_raw is None
            else _dec_int(quantity_raw, f"{path}.document.quantity"),
            _dec_str_enum(
                TargetSalesUnitEvidenceSourceV2,
                _dec_required(d, "source", f"{path}.document"),
                f"{path}.document.source",
            ),
            _dec_optional_str(
                _dec_required(d, "composition_clause", f"{path}.document"),
                f"{path}.document.composition_clause",
            ),
            _dec_optional_str_enum(
                BundleCompositionStateV2FU4,
                _dec_required(d, "composition_state", f"{path}.document"),
                f"{path}.document.composition_state",
            ),
            None
            if attestation_raw is None
            else _dec_fu4_attestation(
                attestation_raw,
                f"{path}.document.completeness_attestation",
            ),
            _dec_str(
                _dec_required(d, "evidence_digest", f"{path}.document"),
                f"{path}.document.evidence_digest",
                allow_empty=False,
            ),
        )
        if d != _fu4_target_fu4_document(target):
            raise SemanticDecisionCodecError(
                f"{path}.document: the stored FU4 target document does "
                "not round-trip to the reconstructed record (no two "
                "documents, one record)"
            )
        return target
    raise SemanticDecisionCodecError(
        f"{path}.schema: unknown target-evidence shape discriminator "
        f"{schema!r} (the exact bounded set is 'frozen_fu3' / "
        "'fu4_v3'; no shape is inferred)"
    )


def _dec_fu4_quantity_attestation(
    raw: object, path: str
) -> QuantityCompletenessAttestationV2FU4 | None:
    """Strict decode of the quantity attestation document (the exact
    canonical key set + ``attestation_digest``; the FU4 constructor is
    the validator — the review-process sole-authority source class, the
    bounded reason vocabulary, and the digest self-verification fail
    closed here)."""
    if raw is None:
        return None
    doc = _dec_mapping(raw, path)
    _check_keys(doc, _V2_FU4_QUANTITY_ATTESTATION_DOC_KEYS, path)
    attestation = QuantityCompletenessAttestationV2FU4(
        _dec_int(
            _dec_required(doc, "schema_version", path),
            f"{path}.schema_version",
        ),
        _dec_str_enum(
            EvidenceSideV2FU4,
            _dec_required(doc, "subject_side", path),
            f"{path}.subject_side",
        ),
        _dec_str_enum(
            QuantityNonMaterialityReasonV2FU4,
            _dec_required(doc, "reason", path),
            f"{path}.reason",
        ),
        _dec_str_enum(
            TargetSalesUnitEvidenceSourceV2,
            _dec_required(doc, "source", path),
            f"{path}.source",
        ),
        _dec_str(
            _dec_required(doc, "attestation_text", path),
            f"{path}.attestation_text",
            allow_empty=False,
        ),
        _dec_str(
            _dec_required(doc, "attestation_digest", path),
            f"{path}.attestation_digest",
            allow_empty=False,
        ),
    )
    if doc != {
        **attestation.canonical(),
        "attestation_digest": attestation.attestation_digest,
    }:
        raise SemanticDecisionCodecError(
            f"{path}: the stored quantity-attestation document does not "
            "round-trip to the reconstructed attestation (no two "
            "documents, one record)"
        )
    return attestation


def _decode_v2_fu4_payload(payload: dict[str, object]) -> SemanticDecisionRecordV2FU4:
    """Decode a FU4-framed payload into a validated FU4 record.

    Raises ``SemanticDecisionCodecError`` for any structural violation
    and wraps every record-constructor failure (including the self-
    verifying digest check, the FU4 exact-binding check, the evidence-
    schema pins, and the derived-section decision invariants) in the
    same bounded error.
    """
    _check_keys(payload, _V2_FU4_TOP_LEVEL_KEYS, "top-level")

    # -- binding (the universal section; re-validated strictly here) --
    binding = _dec_mapping(
        _dec_required(payload, "binding", "top-level"), "binding"
    )
    _check_keys(binding, _BINDING_KEYS, "binding")
    run_id = _dec_str(
        _dec_required(binding, "run_id", "binding"),
        "binding.run_id",
        allow_empty=False,
    )
    assessment_index = _dec_int(
        _dec_required(binding, "assessment_index", "binding"),
        "binding.assessment_index",
    )
    source_url = _dec_str(
        _dec_required(binding, "source_url", "binding"),
        "binding.source_url",
        allow_empty=False,
    )

    # -- contract (the exact five axes; the FU4 pin is enforced by the
    #    record constructor — a foreign axis is a codec error) --
    contract = _dec_mapping(
        _dec_required(payload, "contract", "top-level"), "contract"
    )
    _check_keys(contract, _V2_CONTRACT_KEYS, "contract")
    semantic_contract_version = _dec_str(
        _dec_required(contract, "semantic_contract_version", "contract"),
        "contract.semantic_contract_version",
        allow_empty=False,
    )
    prompt_version = _dec_str(
        _dec_required(contract, "prompt_version", "contract"),
        "contract.prompt_version",
        allow_empty=False,
    )
    input_schema_version = _dec_int(
        _dec_required(contract, "input_schema_version", "contract"),
        "contract.input_schema_version",
    )
    output_schema_version = _dec_int(
        _dec_required(contract, "output_schema_version", "contract"),
        "contract.output_schema_version",
    )
    authority_contract_version = _dec_str(
        _dec_required(contract, "authority_contract_version", "contract"),
        "contract.authority_contract_version",
        allow_empty=False,
    )

    # -- case (the exact recorded V2 input; the V2 adapter's strict
    #    case decode is reused — input schema 1 is byte-identical) --
    case = _dec_v2_case(
        _dec_mapping(_dec_required(payload, "case", "top-level"), "case"),
        "case",
    )

    # -- evaluation (the strict structured V2 output) --
    evaluation_data = _dec_mapping(
        _dec_required(payload, "evaluation", "top-level"), "evaluation"
    )
    _check_keys(evaluation_data, _V2_EVALUATION_KEYS, "evaluation")
    evaluation_state = _dec_str_enum(
        SemanticEvaluationStateV2,
        _dec_required(evaluation_data, "evaluation_state", "evaluation"),
        "evaluation.evaluation_state",
    )
    decision = _dec_optional_str_enum(
        V2SemanticDecision,
        _dec_required(evaluation_data, "decision", "evaluation"),
        "evaluation.decision",
    )
    confidence = _dec_optional_str_enum(
        V2Confidence,
        _dec_required(evaluation_data, "confidence", "evaluation"),
        "evaluation.confidence",
    )
    reason_code = _dec_optional_str_enum(
        SemanticReasonCodeV2,
        _dec_required(evaluation_data, "reason_code", "evaluation"),
        "evaluation.reason_code",
    )
    conflict_classes = frozenset(
        _dec_str_enum(
            ConflictClass, value, f"evaluation.conflict_classes[{i}]"
        )
        for i, value in enumerate(
            _dec_sorted_unique_str_list(
                _dec_required(
                    evaluation_data, "conflict_classes", "evaluation"
                ),
                "evaluation.conflict_classes",
            )
        )
    )
    matched_attributes = _dec_v2_attribute_list(
        _dec_list(
            _dec_required(
                evaluation_data, "matched_attributes", "evaluation"
            ),
            "evaluation.matched_attributes",
        ),
        "evaluation.matched_attributes",
    )
    conflicting_attributes = _dec_v2_attribute_list(
        _dec_list(
            _dec_required(
                evaluation_data, "conflicting_attributes", "evaluation"
            ),
            "evaluation.conflicting_attributes",
        ),
        "evaluation.conflicting_attributes",
    )
    missing_critical_attributes = tuple(
        _dec_str_enum(
            SemanticAttributeDimensionV2,
            value,
            f"evaluation.missing_critical_attributes[{i}]",
        )
        for i, value in enumerate(
            _dec_sorted_unique_str_list(
                _dec_required(
                    evaluation_data, "missing_critical_attributes",
                    "evaluation",
                ),
                "evaluation.missing_critical_attributes",
            )
        )
    )

    # -- execution (the pinned route) --
    execution_data = _dec_mapping(
        _dec_required(payload, "execution", "top-level"), "execution"
    )
    _check_keys(execution_data, _V2_EXECUTION_KEYS, "execution")
    attempts_raw = _dec_list(
        _dec_required(execution_data, "attempts", "execution"),
        "execution.attempts",
    )
    attempts = tuple(
        _dec_v2_attempt(
            _dec_mapping(item, f"execution.attempts[{i}]"),
            f"execution.attempts[{i}]",
        )
        for i, item in enumerate(attempts_raw)
    )
    fallback_used = _dec_bool(
        _dec_required(execution_data, "fallback_used", "execution"),
        "execution.fallback_used",
    )
    fallback_reason = _dec_optional_str_enum(
        SemanticFallbackReason,
        _dec_required(execution_data, "fallback_reason", "execution"),
        "execution.fallback_reason",
    )
    error_type = _dec_optional_str_enum(
        SemanticFailureClass,
        _dec_required(execution_data, "error_type", "execution"),
        "execution.error_type",
    )
    actual_provider = _dec_optional_str(
        _dec_required(execution_data, "actual_provider", "execution"),
        "execution.actual_provider",
    )
    actual_model = _dec_optional_str(
        _dec_required(execution_data, "actual_model", "execution"),
        "execution.actual_model",
    )
    evaluation_started_at = _dec_optional_str(
        _dec_required(
            execution_data, "evaluation_started_at", "execution"
        ),
        "execution.evaluation_started_at",
    )
    evaluation_finished_at = _dec_optional_str(
        _dec_required(
            execution_data, "evaluation_finished_at", "execution"
        ),
        "execution.evaluation_finished_at",
    )

    # -- derived (the FU4 audit surface — the exact key set) --
    derived_data = _dec_mapping(
        _dec_required(payload, "derived", "top-level"), "derived"
    )
    _check_keys(derived_data, _V2_FU4_DERIVED_KEYS, "derived")
    product_evidence_quality = _dec_str_enum(
        ProductEvidenceQuality,
        _dec_required(derived_data, "product_evidence_quality", "derived"),
        "derived.product_evidence_quality",
    )
    relationship_authority = _dec_str_enum(
        RelationshipAuthority,
        _dec_required(derived_data, "relationship_authority", "derived"),
        "derived.relationship_authority",
    )
    authority_tier = _dec_str_enum(
        AuthorityTier,
        _dec_required(derived_data, "authority_tier", "derived"),
        "derived.authority_tier",
    )
    fired_rules = frozenset(
        _dec_str_enum(
            AuthorityRuleV2FU4, value, f"derived.fired_rules[{i}]"
        )
        for i, value in enumerate(
            _dec_sorted_unique_str_list(
                _dec_required(derived_data, "fired_rules", "derived"),
                "derived.fired_rules",
            )
        )
    )
    identity_resolution_bound = _dec_str_enum(
        IdentityResolutionBoundV2,
        _dec_required(
            derived_data, "identity_resolution_bound", "derived"
        ),
        "derived.identity_resolution_bound",
    )
    sales_unit_authority = _dec_str_enum(
        SalesUnitAuthorityV2,
        _dec_required(
            derived_data, "sales_unit_authority", "derived"
        ),
        "derived.sales_unit_authority",
    )
    quantity_axis_state = _dec_optional_str_enum(
        BundleQuantityAxisStateV2FU4,
        _dec_required(derived_data, "quantity_axis_state", "derived"),
        "derived.quantity_axis_state",
    )
    candidate_composition_state = _dec_optional_str_enum(
        BundleCompositionStateV2FU4,
        _dec_required(
            derived_data, "candidate_composition_state", "derived"
        ),
        "derived.candidate_composition_state",
    )
    target_composition_state = _dec_optional_str_enum(
        BundleCompositionStateV2FU4,
        _dec_required(derived_data, "target_composition_state", "derived"),
        "derived.target_composition_state",
    )
    candidate_completeness_attestation_digest = _dec_optional_str(
        _dec_required(
            derived_data,
            "candidate_completeness_attestation_digest",
            "derived",
        ),
        "derived.candidate_completeness_attestation_digest",
    )
    target_completeness_attestation_digest = _dec_optional_str(
        _dec_required(
            derived_data, "target_completeness_attestation_digest", "derived"
        ),
        "derived.target_completeness_attestation_digest",
    )
    quantity_attestation_digest = _dec_optional_str(
        _dec_required(
            derived_data, "quantity_attestation_digest", "derived"
        ),
        "derived.quantity_attestation_digest",
    )

    # -- authority (the NEW FU4 authority-evidence section — strict
    #    typed decode through the FU4 constructors; the constructor is
    #    the validator) --
    authority_data = _dec_mapping(
        _dec_required(payload, "authority", "top-level"), "authority"
    )
    _check_keys(authority_data, _V2_FU4_AUTHORITY_KEYS, "authority")
    candidate_composition_raw = _dec_required(
        authority_data, "candidate_composition", "authority"
    )
    candidate_composition = (
        None
        if candidate_composition_raw is None
        else _dec_fu4_candidate_composition(
            candidate_composition_raw, "authority.candidate_composition"
        )
    )
    target_evidence = _dec_fu4_target_evidence(
        _dec_required(authority_data, "target_evidence", "authority"),
        "authority.target_evidence",
    )
    quantity_attestation = _dec_fu4_quantity_attestation(
        _dec_required(
            authority_data, "quantity_attestation", "authority"
        ),
        "authority.quantity_attestation",
    )

    # -- integrity --
    integrity_data = _dec_mapping(
        _dec_required(payload, "integrity", "top-level"), "integrity"
    )
    _check_keys(integrity_data, _V2_INTEGRITY_KEYS, "integrity")
    input_digest = _dec_str(
        _dec_required(integrity_data, "input_digest", "integrity"),
        "integrity.input_digest",
        allow_empty=False,
    )
    output_digest = _dec_str(
        _dec_required(integrity_data, "output_digest", "integrity"),
        "integrity.output_digest",
        allow_empty=False,
    )

    # The FU4 record constructor re-validates everything (types,
    # coherence, the FU4 route pin, the FU4 exact contract binding, the
    # evidence-schema pins, the derived-section decision invariants,
    # digests) and fails closed; any constructor violation is wrapped in
    # the bounded codec error by the caller.
    return SemanticDecisionRecordV2FU4(
        run_id=run_id,
        assessment_index=assessment_index,
        source_url=source_url,
        semantic_contract_version=semantic_contract_version,
        prompt_version=prompt_version,
        input_schema_version=input_schema_version,
        output_schema_version=output_schema_version,
        authority_contract_version=authority_contract_version,
        case=case,
        evaluation_state=evaluation_state,
        decision=decision,
        confidence=confidence,
        reason_code=reason_code,
        conflict_classes=conflict_classes,
        matched_attributes=matched_attributes,
        conflicting_attributes=conflicting_attributes,
        missing_critical_attributes=missing_critical_attributes,
        attempts=attempts,
        fallback_used=fallback_used,
        fallback_reason=fallback_reason,
        error_type=error_type,
        actual_provider=actual_provider,
        actual_model=actual_model,
        evaluation_started_at=evaluation_started_at,
        evaluation_finished_at=evaluation_finished_at,
        product_evidence_quality=product_evidence_quality,
        relationship_authority=relationship_authority,
        authority_tier=authority_tier,
        fired_rules=fired_rules,
        identity_resolution_bound=identity_resolution_bound,
        sales_unit_authority=sales_unit_authority,
        quantity_axis_state=quantity_axis_state,
        candidate_composition_state=candidate_composition_state,
        target_composition_state=target_composition_state,
        candidate_completeness_attestation_digest=(
            candidate_completeness_attestation_digest
        ),
        target_completeness_attestation_digest=(
            target_completeness_attestation_digest
        ),
        quantity_attestation_digest=quantity_attestation_digest,
        candidate_composition=candidate_composition,
        target_evidence=target_evidence,
        quantity_attestation=quantity_attestation,
        input_digest=input_digest,
        output_digest=output_digest,
    )


# ---------------------------------------------------------------------------
# The FU4 pure zero-live replay / reconstruction
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class SemanticDecisionReplayV2FU4:
    """The verified reconstruction of one persisted FU4 semantic
    decision.

    Carries the original record (for provenance), the reconstructed S2-A
    authority inputs (the exact recorded V2 input case is the authority
    input: the deterministic context, the context provenances, and the
    authority-side product evidence), the reconstructed FU4 authority
    evidence (the v3 candidate composition record, the discriminator-
    selected target evidence, the quantity attestation), the re-derived
    FU4 authority decision (proved to agree with the stored derived
    audit surface — the FULL ``AuthorityDecisionV2FU4``: the frozen S2-A
    snapshots + the bound + the unit + the six bundle-axis audit
    fields), the recorded V2 input (from which the exact historical 2.1
    prompt is deterministically reconstructable without any live call),
    and the recorded FU4 contract binding.
    """

    record: SemanticDecisionRecordV2FU4
    identity_context: IdentityStateAssessmentV2
    semantic_evaluation: SemanticEvaluationV2
    context_provenances: frozenset[ContextProvenance]
    product_evidence: ProductEvidenceProfileV2
    product_evidence_quality: ProductEvidenceQuality
    relationship_requirement: RelationshipRequirement
    relationship_authority: RelationshipAuthority
    authority_decision: AuthorityDecisionV2FU4
    candidate_composition: CandidateBundleCompositionEvidenceV2FU4 | None
    target_evidence: (
        TargetSalesUnitEvidenceV2FU4 | TargetSalesUnitEvidenceV2 | None
    )
    quantity_attestation: QuantityCompletenessAttestationV2FU4 | None
    case: SemanticMatchCaseV2
    contract_binding: tuple[str, str, int, int, str]


def reconstruct_identity_context_v2_fu4(
    record: SemanticDecisionRecordV2FU4,
) -> IdentityStateAssessmentV2:
    """Reconstruct the deterministic V2 context from the persisted FU4
    record's exact recorded input. The frozen V2 case constructor
    re-validates the recorded state / sub-state / signal combination
    (fail closed): a context that is not a legitimate S2-A context
    cannot be reconstructed."""
    case = record.case
    return IdentityStateAssessmentV2(
        state=case.identity_state,
        substate=case.substate,
        relationship_signals=case.relationship_signals,
        normalized_requested_part_number=(
            case.normalized_requested_part_number
        ),
        normalized_candidate_part_number=(
            case.normalized_candidate_part_number
        ),
    )


def reconstruct_semantic_evaluation_v2_fu4(
    record: SemanticDecisionRecordV2FU4,
) -> SemanticEvaluationV2:
    """Reconstruct the exact historical V2 semantic evaluation.

    * ``EVALUATED`` -> the recorded decision / confidence / conflict
      classes (the exact evaluation used at the time);
    * ``RUNTIME_FAILURE`` -> the explicit runtime-failure state (NEVER
      interpreted as NO_MATCH or anything evidence-shaped);
    * ``NOT_EVALUATED`` -> the explicit not-evaluated state (the
      deterministic state governs; this is not an AI failure).
    """
    if record.evaluation_state is SemanticEvaluationStateV2.EVALUATED:
        if record.decision is None or record.confidence is None:
            raise SemanticDecisionReplayError(
                "an EVALUATED record must carry the recorded decision "
                "and confidence; the artifact is corrupt"
            )
        return SemanticEvaluationV2.evaluated(
            record.decision, record.confidence, record.conflict_classes
        )
    if record.evaluation_state is SemanticEvaluationStateV2.RUNTIME_FAILURE:
        return SemanticEvaluationV2.runtime_failure()
    if record.evaluation_state is SemanticEvaluationStateV2.NOT_EVALUATED:
        return SemanticEvaluationV2.not_evaluated()
    raise SemanticDecisionReplayError(
        "the record carries an unknown evaluation state; nothing to "
        "reconstruct"
    )


def _fu4_contract_binding(
    record: SemanticDecisionRecordV2FU4,
) -> tuple[str, str, int, int, str]:
    return (
        record.semantic_contract_version,
        record.prompt_version,
        record.input_schema_version,
        record.output_schema_version,
        record.authority_contract_version,
    )


def _replay_v2_fu4_record(record: object) -> SemanticDecisionReplayV2FU4:
    """The FU4 adapter's zero-live replay of one FU4 record (design
    section 6).

    Steps (each fails closed with ``SemanticDecisionReplayError`` /
    ``SemanticDecisionCodecError`` as noted — a missing, unknown,
    inconsistent, or tampered evidence NEVER yields a decision):

    1. **Exact-binding gate (adapter-owned).** The record's contract
       section must equal the FU4 binding constant (enforced at
       construction; the replay re-asserts it — a record that could not
       be constructed otherwise is a registry defect; fail closed).
    2. **Load the exact recorded semantic input / output.** The
       recorded case (constructor-re-validated), the recorded
       evaluation (the strict structured output), the recorded
       execution provenance (the attempts on the pinned route, the
       fallback discipline).
    3. **Load the complete FU4 derivation evidence.** From the
       ``authority`` section (already strict-decoded + digest-verified
       at construction): the candidate composition record (v3 — for the
       EXTRACTION_RESULT_V1 basis WITH the embedded original result and
       its two self-verifying digests), the target evidence (the
       discriminator-selected shape), the quantity attestation (when
       present).
    4. **Verify every relevant evidence digest and schema version.**
       The record's own ``verify()`` ran at construction; the
       derivation below re-runs the v3 presentation gate, which
       re-verifies the ``evidence_digest`` (the embedded attestation
       and the embedded original result within), the embedded
       attestation's ``attestation_digest`` self-verification, the
       embedded original result's ``verify_integrity()`` (BOTH stored
       digests recomputed + cue-span containment), and the schema-
       version pins — a tampered or superseded document produces no
       derivation input.
    5. **Verify candidate / channel / extraction association.** The
       derivation itself is the verifier (no private-gate
       re-implementation at replay): the presentation gate re-runs over
       (decoded candidate record, the RECORDED channel from the case)
       — the channel-content-digest binding, the RECORDED_CHANNEL
       exact-construction check, and the v3 four-step original-result
       chain — plus the target evidence gate. A cross-listing
       substitution, a wrong embedded result, or a forged association
       is refused here — NO unit is derived from it.
    6. **Recompute the FU4 authority decision.** ``derive_authority_
       tier_fu4`` over the reconstructed inputs (the token selects the
       FU4 arm); the human overlay is NOT replayed (the overlay is a
       later workflow concern — the recorded derived snapshots were
       produced without it, exactly as under the V2 replay). The
       frozen relationship-requirement / product-evidence-quality /
       relationship-authority derivations re-run as under the V2
       replay (the derived section carries them).
    7. **Compare the replayed decision with the recorded decision.**
       EVERY field of the re-derived ``AuthorityDecisionV2FU4`` must
       EXACTLY agree with the stored ``derived`` section — any
       disagreement (a stored snapshot from another contract, a
       tampered derived section, a derivation that fails closed on the
       recorded inputs) is a ``SemanticDecisionReplayError`` naming the
       disagreeing fields.
    8. **Return** ``SemanticDecisionReplayV2FU4`` — zero live AI
       calls, zero provider / network calls by construction.
    """
    if not isinstance(record, SemanticDecisionRecordV2FU4):
        raise TypeError(
            "the FU4 replay adapter expects a SemanticDecisionRecordV2"
            "FU4, got "
            f"{type(record).__name__}"
        )
    binding = _fu4_contract_binding(record)
    if binding not in (V2_FU4_CONTRACT_BINDING,):
        raise SemanticDecisionReplayError(
            "unsupported contract binding "
            f"(semantic contract {binding[0]!r}, prompt {binding[1]!r}, "
            f"input schema {binding[2]}, output schema {binding[3]}, "
            f"authority contract {binding[4]!r}); the FU4 adapter "
            "cannot safely replay it and refuses to reinterpret a "
            "historical decision under a contract it does not know"
        )

    case = record.case
    try:
        identity_context = reconstruct_identity_context_v2_fu4(record)
        semantic_evaluation = reconstruct_semantic_evaluation_v2_fu4(record)
        product_evidence = case.product_evidence
        context_provenances = case.context_provenances
        channel: CandidateSalesUnitEvidenceV2 = (
            case.candidate_commercial.sales_unit
        )

        requirement = substate_relationship_requirement(
            identity_context.substate,
            identity_context.primary_relationship_signal,
        )
        quality = derive_product_evidence_quality(
            product_evidence, context_provenances
        )
        relationship_authority = derive_relationship_authority(
            identity_context, context_provenances
        )
        authority_decision = derive_authority_tier_fu4(
            identity_context,
            channel,
            semantic_evaluation,
            context_provenances,
            product_evidence,
            None,
            target_unit_evidence=record.target_evidence,
            candidate_composition=record.candidate_composition,
            quantity_attestation=record.quantity_attestation,
        )
    except SemanticDecisionReplayError:
        raise
    except (TypeError, ValueError):
        raise SemanticDecisionReplayError(
            "the recorded inputs violate the bound FU4 authority "
            "contract; the artifact is corrupt or its evidence "
            "association fails closed, and it cannot be replayed"
        ) from None

    # -- derived-agreement proof (tamper / version-drift detection) ----
    mismatches: list[str] = []
    if requirement is not case.relationship_requirement:
        mismatches.append("relationship_requirement")
    if quality is not record.product_evidence_quality:
        mismatches.append("product_evidence_quality")
    if relationship_authority is not record.relationship_authority:
        mismatches.append("relationship_authority")
    if authority_decision.tier is not record.authority_tier:
        mismatches.append("authority_tier")
    if authority_decision.fired_rules != record.fired_rules:
        mismatches.append("fired_rules")
    if authority_decision.identity_resolution_bound is not (
        record.identity_resolution_bound
    ):
        mismatches.append("identity_resolution_bound")
    if authority_decision.sales_unit_authority is not (
        record.sales_unit_authority
    ):
        mismatches.append("sales_unit_authority")
    if authority_decision.quantity_axis_state is not (
        record.quantity_axis_state
    ):
        mismatches.append("quantity_axis_state")
    if authority_decision.candidate_composition_state is not (
        record.candidate_composition_state
    ):
        mismatches.append("candidate_composition_state")
    if authority_decision.target_composition_state is not (
        record.target_composition_state
    ):
        mismatches.append("target_composition_state")
    if (
        authority_decision.candidate_completeness_attestation_digest
        != record.candidate_completeness_attestation_digest
    ):
        mismatches.append("candidate_completeness_attestation_digest")
    if (
        authority_decision.target_completeness_attestation_digest
        != record.target_completeness_attestation_digest
    ):
        mismatches.append("target_completeness_attestation_digest")
    if authority_decision.quantity_attestation_digest != (
        record.quantity_attestation_digest
    ):
        mismatches.append("quantity_attestation_digest")
    if mismatches:
        raise SemanticDecisionReplayError(
            "stored FU4 derived audit snapshots do not agree with "
            f"re-derivation under the bound FU4 authority contract: "
            f"{', '.join(mismatches)}; the artifact is tampered or was "
            "produced under a contract this code cannot verify"
        )

    return SemanticDecisionReplayV2FU4(
        record=record,
        identity_context=identity_context,
        semantic_evaluation=semantic_evaluation,
        context_provenances=context_provenances,
        product_evidence=product_evidence,
        product_evidence_quality=quality,
        relationship_requirement=requirement,
        relationship_authority=relationship_authority,
        authority_decision=authority_decision,
        candidate_composition=record.candidate_composition,
        target_evidence=record.target_evidence,
        quantity_attestation=record.quantity_attestation,
        case=case,
        contract_binding=binding,
    )


def replay_v2_fu4_record(
    record: SemanticDecisionRecordV2FU4,
) -> SemanticDecisionReplayV2FU4:
    """Public FU4 replay entry (delegates to the adapter
    implementation)."""
    return _replay_v2_fu4_record(record)


def _fu4_run_binding_violation(
    record: object,
    *,
    request_mpn: str,
    request_description: str,
) -> str | None:
    """The FU4-specific run-binding check: the recorded V2 input's
    target MPN / description must equal the run's canonical request
    (the universal parts — the row exists, the digest verifies, the
    recorded index is in range, and the recorded source URL matches the
    run's persisted assessment at that index — are checked by the
    persistence service). Returns a bounded violation message, or None
    when the binding holds."""
    if not isinstance(record, SemanticDecisionRecordV2FU4):
        raise TypeError(
            "the FU4 run-binding check expects a "
            f"SemanticDecisionRecordV2FU4, got {type(record).__name__}"
        )
    if (
        record.case.target.mpn != request_mpn
        or (record.case.target.description_raw_text or "")
        != (request_description or "")
    ):
        return (
            "the record's request identity does not match the run's "
            "canonical request; the artifact does not bind to this run"
        )
    return None


# ---------------------------------------------------------------------------
# The registered FU4 adapter (the third entry of the universal registry)
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class SemanticV2FU4ContractAdapter(SemanticDecisionContractAdapter):
    """The registered adapter for the FU4 record / replay binding
    (envelope schema version 1, semantic contract V2, the separately
    versioned FU4 authority axis)."""

    def encode(self, record: object) -> dict[str, object]:
        return encode_v2_fu4_payload(record)

    def decode(self, payload: dict[str, object]) -> SemanticDecisionRecordV2FU4:
        return _decode_v2_fu4_payload(payload)

    def replay(
        self, record: object
    ) -> SemanticDecisionReplayV2FU4:
        return _replay_v2_fu4_record(record)

    def run_binding_violation(
        self,
        record: object,
        *,
        request_mpn: str,
        request_description: str,
    ) -> str | None:
        return _fu4_run_binding_violation(
            record,
            request_mpn=request_mpn,
            request_description=request_description,
        )


SEMANTIC_V2_FU4_ADAPTER: Final[SemanticV2FU4ContractAdapter] = (
    SemanticV2FU4ContractAdapter(
        envelope_schema_version=1,
        semantic_contract_version=SEMANTIC_CONTRACT_VERSION_V2_FU4,
        supported_bindings=(V2_FU4_CONTRACT_BINDING,),
        record_type=SemanticDecisionRecordV2FU4,
    )
)


# ---------------------------------------------------------------------------
# Mechanical self-consistency of the FU4 record-contract data, verified
# once at import (pure data checks, no mutable state). If a future edit
# breaks any of these contracts, the module refuses to import.
# ---------------------------------------------------------------------------

if V2_FU4_CONTRACT_BINDING != (
    "V2",
    "2.1",
    1,
    1,
    AUTHORITY_CONTRACT_VERSION_V2_FU4,
):
    raise RuntimeError(
        "the FU4 record binding is exactly (V2, 2.1, 1, 1, the FU4 "
        "authority token) — a future binding is a future adapter, never "
        "an implicit reinterpretation"
    )
if SEMANTIC_CONTRACT_VERSION_V2_FU4 != SEMANTIC_CONTRACT_VERSION_V2:
    raise RuntimeError(
        "the FU4 binding keeps the FINAL Semantic V2 contract axis "
        "(FU4 governs the authority layer downstream of the recorded "
        "decision; it is not a new semantic contract — the envelope "
        "dispatch key stays V2)"
    )
if (
    SEMANTIC_INPUT_SCHEMA_VERSION_V2_FU4
    != SEMANTIC_INPUT_SCHEMA_VERSION_V2
    or SEMANTIC_OUTPUT_SCHEMA_VERSION_V2_FU4
    != SEMANTIC_OUTPUT_SCHEMA_VERSION_V2
):
    raise RuntimeError(
        "the FU4 binding keeps the exact V2 input / output schema "
        "versions (the recorded input is byte-identical in shape; the "
        "output contract is identical under every binding)"
    )
if (
    (PRIMARY_PROVIDER_V2_FU4, PRIMARY_MODEL_V2_FU4)
    != (PRIMARY_PROVIDER_V2, PRIMARY_MODEL_V2)
    or (FALLBACK_PROVIDER_V2_FU4, FALLBACK_MODEL_V2_FU4)
    != (FALLBACK_PROVIDER_V2, FALLBACK_MODEL_V2)
):
    raise RuntimeError(
        "the FU4 record contract pins the SAME frozen qualified route "
        "identities the V2 adapter pins (the route is adapter-owned "
        "contract data, mirrored and drift-pinned)"
    )
if V2_FU4_AUTHORITY_QUALIFIED is not False:
    raise RuntimeError(
        "the FU4 registration is NOT a qualification: the explicit "
        "qualification-boundary marker stays False (a qualification "
        "under the FU4 binding is a separate governance event with its "
        "own marker flip + consumer guard)"
    )
for _global_name, _global_value in list(globals().items()):
    if _global_name.startswith("__"):
        continue
    if isinstance(_global_value, (dict, list, set)):
        raise RuntimeError(
            f"semantic_decision_v2_fu4 global {_global_name} is a "
            "mutable container; frozen contract data must be runtime-"
            "immutable (house discipline)"
        )
