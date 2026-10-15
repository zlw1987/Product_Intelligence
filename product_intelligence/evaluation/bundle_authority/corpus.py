"""Strict loading, decoding, and integrity verification of the Q3-C FU4
Bundle Authority Qualification corpus family (design section 4 / 9.3).

Design of record:
``docs/PRODUCT_INTEL_Q3C_FU4_BUNDLE_AUTHORITY_QUALIFICATION_DESIGN.md``.

The corpus is the independently labeled benchmark the later qualification
phases measure the frozen FU4 contract against. Everything here is FAIL
CLOSED:

* the document schema is exact (missing AND extra keys rejected);
* every bounded contract vocabulary is drift-pinned to the frozen
  research exports (unknown values rejected — no literal re-derivation);
* the per-case digest, the corpus digest, and the manifest digest are
  verified on load (silent mutation after sealing is detectable);
* the evidence documents decode through the REAL frozen constructors
  (the constructor is the validator; design section 4.2(f)) and the
  RECORD-surface payload documents decode through the REAL universal
  codec (design section 4.2(g));
* the sealed source blocks are re-verified (declared archive digests,
  cue / clause / statement span grounding, evidence-side association —
  the I-3 provenance firewall at corpus level);
* the label governance of design section 4.6 is enforced mechanically
  (two distinct identities, ``REVIEWED`` status, the fixed independence
  attestation, the anti-derivation label-text scan, the expected-axis
  coherence pre-checks of design section 4.4).

Authority separation (binding, design section 4.6 / 9.3). This module
imports ONLY the frozen research public surface (constructors, record
types, bounded vocabularies, the house canonical digest, the universal
codec, the frozen P2 channel mapping) and the family's own modules. It
NEVER imports or invokes any FU4 authority derivation
(``derive_sales_unit_authority_fu4`` / ``derive_authority_tier_fu4`` /
``derive_authority_tier_for_contract_fu4``), the R1 zero-live replay, or
any model. The expected label is an independently reviewed INPUT: this
module checks it for structural coherence only; it never computes,
fills, coerces, or upgrades it. ``UNKNOWN`` and ``UNPROVEN`` are never
converted into ``PROVEN_EQUIVALENT`` here, and no pricing eligibility is
ever determined (the frozen ``PRICING_ELIGIBLE_TIERS`` constant is used
only to coherence-check a labeled consequence, never to derive one).

Trust boundary (design section 3). A valid digest proves INTERNAL
structural integrity only (layer L1). It does not establish that the
publisher actually made a claim (L3), that a published completeness
statement is physically complete (L4), or that a physical bundle
contains the listed components (L5). No cryptographic source-
authentication capability is claimed or invented by this module.

Sealed-raw defect scope (design section 5 stage semantics (i)-(iv)).
Cases whose expected outcome is ``REFUSED`` / ``NON_CONSTRUCTIBLE``
carry the sealed invalid documents of the adversarial matrix rows. The
loader runs the real constructors / codec / family checks over every
evidence document, classifies each observation by layer, and requires
the labeled refusal stage to be coherent with what is observable
WITHOUT executing the derivation:

* ``CORPUS_INTEGRITY`` — at least one case-document-integrity
  observation must fire (the defect is a case-internal inconsistency);
* ``CONSTRUCTION`` — at least one frozen-constructor or codec-level
  observation must fire;
* ``CODEC_DECODE`` — the record surface must be present and at least
  one codec-level observation must fire;
* ``PRESENTATION_GATE`` / ``REPLAY_AGREEMENT`` — no constructor-,
  codec-, or case-document-integrity observation may fire (the
  documents are exactly the self-consistent shapes whose defect is
  observed only above the construction layer — the derivation / replay
  observation point, which this module does not and may not execute).

Corroborative gate-layer observations (the channel-content digest
binding, the frozen P2 mapping equality, the sealed-source span
grounding) may fire under any stage: the loader sees what the
presentation gate would see, earlier. A sound (``DERIVED``) case must
carry zero observations of any layer.

Import boundary (design section 9.3 acceptance). The family package
imports ONLY: the standard library, the frozen research public surface
(the exact symbol allowlist is drift-pinned by the C1 test suite), the
domain layer, and the family's own modules. It never imports the
semantic_v2 harness, the execution / runs / web / providers layers, the
2.1 prompt owner, or Django.
"""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Final

from product_intelligence.research import (
    AuthorityRuleV2FU4,
    AuthorityTier,
    BUNDLE_COMPOSITION_EVIDENCE_VERSION_FU4,
    BundleCompositionEvidenceIntegrityError,
    BundleCompositionStateV2FU4,
    BundleQuantityAxisStateV2FU4,
    CandidateBundleCompositionEvidenceV2FU4,
    CandidateCompositionEvidenceBasisV2FU4,
    CandidateProductEvidenceSource,
    CompletenessBasisV2FU4,
    CompositionCompletenessAttestationV2FU4,
    ConflictClass,
    ConflictSubstateV2,
    ContextProvenance,
    EvidenceSideV2FU4,
    IdentityRelationshipSignal,
    IdentityStateAssessmentV2,
    IdentityStateV2,
    PRICING_ELIGIBLE_TIERS,
    ProductEvidenceDimension,
    ProductEvidenceFactV2,
    ProductEvidenceProfileV2,
    QuantityCompletenessAttestationV2FU4,
    QuantityNonMaterialityReasonV2FU4,
    RelationshipRequirement,
    SALES_UNIT_EXTRACTION_SCHEMA_VERSION,
    SalesUnitAuthorityV2,
    SalesUnitCueDisposition,
    SalesUnitCueField,
    SalesUnitCueReason,
    SalesUnitCueV1,
    SalesUnitExtractionIntegrityError,
    SalesUnitExtractionResult,
    SalesUnitExtractionState,
    SalesUnitIdentifierFieldNoteV1,
    SemanticEvaluationStateV2,
    SemanticEvaluationV2,
    TargetSalesUnitEvidenceSourceV2,
    TargetSalesUnitEvidenceV2,
    TargetSalesUnitEvidenceV2FU4,
    TargetSalesUnitFormV2,
    UncertainSubstateV2,
    UnevaluableSubstateV2,
    VerifiedSubstateV2,
    V2Confidence,
    V2SemanticDecision,
    V2_FU4_CONTRACT_BINDING,
    canonical_sha256,
    decode_semantic_decision_record,
    registered_envelope_schema_versions,
    sales_unit_channel_from_extraction,
    substate_relationship_requirement,
)
from product_intelligence.research.semantic_v2 import (
    CandidateCommercialEvidenceV2,
    CandidateEvidenceSourceV2,
    CandidateObservationFactV2,
    CandidateProductDimensionV2,
    CandidateProductEvidenceV2,
    CandidateSalesUnitEvidenceV2,
    PackagingEvidenceStateV2,
    ReviewedTargetContextV2,
    SalesUnitKindV2,
    SemanticMatchCaseV2,
    TargetEvidenceV2,
    TargetIdentifierRelationKindV2,
)

__all__ = [
    "CANONICAL_CORPUS_BYTES",
    "CASE_ID_PATTERN",
    "CHALLENGE_TAGS",
    "COMPOSITION_STATE_VALUES",
    "CORPUS_ID",
    "CORPUS_LABEL",
    "CORPUS_SCHEMA_VERSION",
    "FAIL_CLOSED",
    "FAMILY_STATEMENT",
    "FIRST_CORPUS_VERSION",
    "FU4_BINDING",
    "INDEPENDENCE_ATTESTATION",
    "LABELING_PROVENANCE_VALUES",
    "MANIFEST_SCHEMA_VERSION",
    "MATRIX_ROWS",
    "REFUSAL_ERROR_CLASSES",
    "REFUSAL_STAGES",
    "REPLAY_VALUES",
    "REVIEW_STATUS_VALUES",
    "STAGE_ERROR_CLASSES",
    "SURFACES",
    "TEXTUAL_RELATION_VALUES",
    "TRACKS",
    "UnitStates",
    "BINDING_AUTHORITY_CORPUS_VERSIONS",
    "BundleAuthorityCorpusError",
    "BundleAuthorityDigestError",
    "BundleAuthorityEvidenceError",
    "BundleAuthorityLabelError",
    "BundleAuthorityManifestError",
    "BundleAuthoritySchemaError",
    "BundleAuthoritySealError",
    "FamilyCaseEvidence",
    "FamilyCorpusBundle",
    "FamilyCorpusCase",
    "build_manifest_document",
    "case_state_digest",
    "corpus_state_digest",
    "load_bundle",
    "load_corpus",
    "verify_corpus_document",
    "verify_manifest",
]

# ---------------------------------------------------------------------------
# Family identity (design section 4.1 — DEC-C1-1; O-1 finalized at C1)
# ---------------------------------------------------------------------------

CORPUS_ID: Final[str] = "PI-FU4-BUNDLE-AUTHORITY-QUALIFICATION"
"""The family corpus identity (separate from the semantic family
``PI-SEMANTIC-V2-QUALIFICATION`` — never confused, never extended)."""

CORPUS_LABEL: Final[str] = "fu4-bundle-authority-qualification-v1"
"""The family corpus label (schema 1)."""

CORPUS_SCHEMA_VERSION: Final[int] = 1
"""The family corpus schema version. Any change is a new schema version —
never a silent edit (design section 4.1)."""

MANIFEST_SCHEMA_VERSION: Final[int] = 1
"""The family manifest schema version (the semantic family's manifest
shape + the ``statement`` / ``lineage`` additive keys of the R2 seal)."""

FIRST_CORPUS_VERSION: Final[str] = "1.0.0"
"""The family's first sealed version (the C2 population seal). The C1
skeleton seal demonstrates the 0-case build / load / regenerate
property over this identity."""

#: The registered FU4 binding — drift-pinned to the frozen research
#: export, never literal-copied (the P1 discipline).
FU4_BINDING: Final[tuple[str, str, int, int, str]] = tuple(
    V2_FU4_CONTRACT_BINDING
)

#: The family seal registry (design section 4.1): the corpus loads only
#: under the exact FU4 binding, at the version sealed under it. The
#: semantic family's ``BINDING_CORPUS_VERSIONS`` is NOT extended.
BINDING_AUTHORITY_CORPUS_VERSIONS: Final[
    dict[tuple[str, str, int, int, str], str]
] = {FU4_BINDING: FIRST_CORPUS_VERSION}

FAMILY_STATEMENT: Final[str] = (
    "Corpus 1.0.0 (family "
    "PI-FU4-BUNDLE-AUTHORITY-QUALIFICATION) is the independently labeled "
    "FU4 Bundle composition authority qualification corpus. It is not "
    "the semantic model qualification corpus (family "
    "PI-SEMANTIC-V2-QUALIFICATION, versions 1.0.0-1.2.0); it does not "
    "label semantic decisions; and it does not by itself qualify any "
    "model for production authority - the decision ladder of the family "
    "report governs."
)
"""The required manifest statement of the family's first version (the
1.2.0-manifest precedent — inside the manifest digest; a tampered
statement is an integrity error)."""

#: The first-version lineage (design section 4.5): null / null — the
#: family's first version derives from no earlier family version.
FIRST_VERSION_LINEAGE: Final[dict[str, None]] = {
    "derived_from_corpus_version": None,
    "derived_from_corpus_digest": None,
}

# ---------------------------------------------------------------------------
# Bounded family vocabularies (design section 4.3 / 4.4)
# ---------------------------------------------------------------------------

CASE_ID_PATTERN: Final[re.Pattern[str]] = re.compile(
    r"^FA4-(?:PROV|UNPR|CONTR|ADV|DELE)-[0-9]{3}$"
)
"""The family case-id grammar (design section 4.4): ``FA4-<CAT>-<NNN>``
with the five bounded categories (PROV / UNPR / CONTR / ADV / DELE)."""

TRACKS: Final[frozenset[str]] = frozenset({"A", "B", "A_B"})
SURFACES: Final[frozenset[str]] = frozenset(
    {"DERIVATION", "RECORD", "BOTH"}
)
EVIDENCE_KINDS: Final[frozenset[str]] = frozenset(
    {"SYNTHETIC", "RECORDED_FIXTURE", "REAL_MARKET"}
)
"""The evidence-kind vocabulary (the semantic family's vocabulary,
adopted — the C1 drift-pin test checks equality against the semantic
family's set)."""

MATRIX_ROWS: Final[frozenset[str]] = frozenset(
    {
        # Design section 5.1 (category A).
        "A1", "A2", "A3", "A4", "A5", "A6", "A7", "A8", "A-DELE",
        # Design section 5.2 (category B).
        "B1", "B2", "B3", "B4", "B5", "B6", "B7", "B8", "B9", "B10",
        "B11", "B12", "B-DELE",
        # Design section 5.3 (category C).
        "C1", "C2", "C2b", "C3", "C4", "C5", "C6", "C7",
        # Design section 5.4 (category D).
        "D1", "D2", "D3", "D4", "D5", "D6", "D7", "D8", "D9", "D10",
        "D11", "D12", "D13", "D14", "D15", "D16", "D17", "D18",
    }
)
"""The 48 distinct design-matrix rows (design section 5.6 coverage
accounting). The ``TB-*`` track-B sub-population rows are annotations
on these rows, not ``matrix_row`` values."""

CHALLENGE_TAGS: Final[frozenset[str]] = frozenset(
    {
        "attestation_missing",
        "cross_listing_substitution",
        "forged_attestation",
        "historical_binding_confusion",
        "semantic_match_unproven_bundle",
    }
)
"""The bounded challenge-tag vocabulary — the exact tag set the design
names (section 4.4 examples + the section 6.1 / 7.6 per-tag gate
denominators); O-1 finalized at C1. A new tag is a recorded schema
event, never a silent addition."""

UNIT_VALUES: Final[frozenset[str]] = frozenset(
    u.value for u in SalesUnitAuthorityV2
)
"""The expected unit vocabulary — drift-pinned to the frozen FU3
``SalesUnitAuthorityV2`` (the qualified axis)."""

QUANTITY_AXIS_VALUES: Final[frozenset[str]] = frozenset(
    s.value for s in BundleQuantityAxisStateV2FU4
)
COMPOSITION_STATE_VALUES: Final[frozenset[str]] = frozenset(
    s.value for s in BundleCompositionStateV2FU4
)
TIER_VALUES: Final[frozenset[str]] = frozenset(t.value for t in AuthorityTier)

CEILING_VALUES: Final[frozenset[str]] = frozenset(
    r.value for r in AuthorityRuleV2FU4 if r.value.startswith("CEILING_SALES_UNIT")
)
if len(CEILING_VALUES) != 2:
    raise AssertionError(
        "the frozen FU4 rule vocabulary must carry exactly the two "
        "restrict-only sales-unit ceilings (drift pin)"
    )

PRICING_ELIGIBLE_TIER_VALUES: Final[frozenset[str]] = frozenset(
    t.value for t in PRICING_ELIGIBLE_TIERS
)
"""The frozen pricing-eligible tier set — used ONLY to coherence-check a
labeled consequence (design section 4.4), never to derive eligibility."""

TEXTUAL_RELATION_VALUES: Final[frozenset[str]] = frozenset(
    {"T-AGREE", "T-DIFF-MATERIAL", "T-DIFF-UNESTABLISHED"}
)
"""The expected textual-relation label vocabulary (design section 4.4;
the derivation-side grammar is private contract data of the qualified
module — the label axis names the same three relations)."""

OUTCOME_VALUES: Final[frozenset[str]] = frozenset(
    {"DERIVED", "REFUSED", "NON_CONSTRUCTIBLE"}
)
REPLAY_VALUES: Final[frozenset[str]] = frozenset(
    {"REPLAY_PASS", "REPLAY_REFUSED", "NOT_APPLICABLE"}
)
REFUSAL_STAGES: Final[frozenset[str]] = frozenset(
    {
        "CONSTRUCTION",
        "CODEC_DECODE",
        "PRESENTATION_GATE",
        "REPLAY_AGREEMENT",
        "CORPUS_INTEGRITY",
    }
)
REFUSAL_ERROR_CLASSES: Final[frozenset[str]] = frozenset(
    {"CONSTRUCTOR", "CODEC", "PRESENTATION", "REPLAY"}
)
"""The bounded refusal error-class vocabulary (O-1 finalized at C1 for
the design's ``<bounded str | null>``): the frozen error class a
labeled refusal names, per stage."""

STAGE_ERROR_CLASSES: Final[dict[str, frozenset[str | None]]] = {
    "CONSTRUCTION": frozenset({"CONSTRUCTOR"}),
    "CODEC_DECODE": frozenset({"CODEC"}),
    "PRESENTATION_GATE": frozenset({"PRESENTATION"}),
    "REPLAY_AGREEMENT": frozenset({"REPLAY"}),
    "CORPUS_INTEGRITY": frozenset({None}),
}
"""A labeled error class must match its stage (a ``CODEC_DECODE`` label
never names a constructor class); the loader's own ``CORPUS_INTEGRITY``
stage names no implementation error class."""

LABELING_PROVENANCE_VALUES: Final[frozenset[str]] = frozenset(
    {
        "DESIGN_TABLE_GROUNDED",
        "REVIEWED_SOURCE_GROUNDED",
        "ADVERSARIAL_CONSTRUCTION",
    }
)
REVIEW_STATUS_VALUES: Final[frozenset[str]] = frozenset({"REVIEWED"})
"""A qualification corpus label is sealed only as ``REVIEWED`` (the
two-identity workflow of design section 4.6 / 8); ``UNREVIEWED`` labels
never enter the family."""

CANDIDATE_ATT_SOURCES: Final[frozenset[str]] = frozenset(
    {"PUBLISHED_STATEMENT", "ABSENT"}
)
TARGET_ATT_SOURCES: Final[frozenset[str]] = frozenset(
    {"PUBLISHED_STATEMENT", "REVIEWED_DETERMINATION", "ABSENT"}
)

CANDIDATE_BASIS_VALUES: Final[frozenset[str]] = frozenset(
    b.value for b in CandidateCompositionEvidenceBasisV2FU4
) | frozenset({"NONE"})
TARGET_EVIDENCE_SCHEMA_VALUES: Final[frozenset[str]] = frozenset(
    {"absent", "frozen_fu3", "fu4_v3"}
)

INDEPENDENCE_ATTESTATION: Final[str] = (
    "This expected outcome was established from the recorded source "
    "content and the cited approved-design rows without executing or "
    "reading the output of the FU4 derivation, the R1 record adapter, "
    "or any model"
)
"""The fixed per-case independence attestation (design section 4.6
item 2(b)) — exact equality, never free text."""

#: The mechanical anti-derivation scan (design section 4.6 item 2(b) —
#: the semantic family's rule, adopted + extended with the
#: implementation-output names): label text (grounding citation +
#: rationale) must not name any model or implementation output as the
#: source of the expected outcome. The fixed attestation statement is
#: checked by equality, not scanned.
FORBIDDEN_LABEL_TOKENS: Final[frozenset[str]] = frozenset(
    {
        "model output",
        "model response",
        "model-generated",
        "assistant output",
        "llm output",
        "qwen",
        "nemotron",
        "minimax",
        "gpt-",
        "gemma",
        "mistral",
        "llama",
        "derivation output",
        "implementation output",
        "derive_sales_unit_authority",
        "derive_authority_tier",
        "replay agreement",
    }
)

SYNTHETIC_RECORDING_ATTESTATION: Final[str] = "by-construction"
"""The fixed recording attestation of a SYNTHETIC source block (design
section 4.4): the by-construction text is the case's own ground truth —
no retrieval, no archive, no URL."""

# ---------------------------------------------------------------------------
# Bounded contract vocabularies drift-pinned to the frozen research
# exports (the P1 discipline — no literal copies of contract values)
# ---------------------------------------------------------------------------

_DECISION_VALUES: Final[frozenset[str]] = frozenset(
    d.value for d in V2SemanticDecision
)
_CONFIDENCE_VALUES: Final[frozenset[str]] = frozenset(
    c.value for c in V2Confidence
)
_EVAL_STATE_VALUES: Final[frozenset[str]] = frozenset(
    s.value for s in SemanticEvaluationStateV2
)
_CONFLICT_VALUES: Final[frozenset[str]] = frozenset(
    c.value for c in ConflictClass
)
_PROVENANCE_VALUES: Final[frozenset[str]] = frozenset(
    p.value for p in ContextProvenance
)
_STATE_VALUES: Final[frozenset[str]] = frozenset(s.value for s in IdentityStateV2)
_SUBSTATE_MEMBERS: Final[dict[str, Any]] = {
    **{m.value: m for m in VerifiedSubstateV2},
    **{m.value: m for m in UncertainSubstateV2},
    **{m.value: m for m in ConflictSubstateV2},
    **{m.value: m for m in UnevaluableSubstateV2},
}
_SIGNAL_VALUES: Final[frozenset[str]] = frozenset(
    s.value for s in IdentityRelationshipSignal
)
_REQUIREMENT_VALUES: Final[frozenset[str]] = frozenset(
    r.value for r in RelationshipRequirement
)
_CANDIDATE_EVIDENCE_SOURCE_VALUES: Final[frozenset[str]] = frozenset(
    s.value for s in CandidateEvidenceSourceV2
)
_TARGET_EVIDENCE_SOURCE_VALUES: Final[frozenset[str]] = frozenset(
    s.value for s in TargetSalesUnitEvidenceSourceV2
)
_TARGET_FORM_VALUES: Final[frozenset[str]] = frozenset(
    f.value for f in TargetSalesUnitFormV2
)
_CHANNEL_STATE_VALUES: Final[frozenset[str]] = frozenset(
    s.value for s in PackagingEvidenceStateV2
)
_CHANNEL_KIND_VALUES: Final[frozenset[str]] = frozenset(
    k.value for k in SalesUnitKindV2
)
_CANDIDATE_PRODUCT_DIMENSION_KEYS: Final[frozenset[str]] = frozenset(
    d.value.lower() for d in CandidateProductDimensionV2
)
_PRODUCT_EVIDENCE_DIMENSION_VALUES: Final[frozenset[str]] = frozenset(
    d.value for d in ProductEvidenceDimension
)
_AUTH_SOURCE_VALUES: Final[frozenset[str]] = frozenset(
    s.value for s in CandidateProductEvidenceSource
)
_CUE_FIELD_VALUES: Final[frozenset[str]] = frozenset(
    f.value for f in SalesUnitCueField
)
_CUE_DISPOSITION_VALUES: Final[frozenset[str]] = frozenset(
    d.value for d in SalesUnitCueDisposition
)
_CUE_REASON_VALUES: Final[frozenset[str]] = frozenset(
    r.value for r in SalesUnitCueReason
)
_EXTRACTION_STATE_VALUES: Final[frozenset[str]] = frozenset(
    s.value for s in SalesUnitExtractionState
)
_SIDE_VALUES: Final[frozenset[str]] = frozenset(
    s.value for s in EvidenceSideV2FU4
)
_COMPLETENESS_BASIS_VALUES: Final[frozenset[str]] = frozenset(
    b.value for b in CompletenessBasisV2FU4
)
_QUANTITY_REASON_VALUES: Final[frozenset[str]] = frozenset(
    r.value for r in QuantityNonMaterialityReasonV2FU4
)

_SHA256_PATTERN = re.compile(r"^[0-9a-f]{64}$")
_UTC_INSTANT_PATTERN = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(\.\d{1,6})?Z$")
_POSIX_RELATIVE_PATH_PATTERN = re.compile(r"^[A-Za-z0-9_./-]+$")

#: The frozen P2 extraction schema version (drift-pinned).
_EXTRACTION_SCHEMA_VERSION: Final[int] = SALES_UNIT_EXTRACTION_SCHEMA_VERSION
#: The frozen FU4 evidence schema version (drift-pinned).
_FU4_EVIDENCE_VERSION: Final[int] = BUNDLE_COMPOSITION_EVIDENCE_VERSION_FU4

#: The registered universal-codec envelope schema versions (drift-pinned
#: — the codec registry is the authority, never a literal here).
_ENVELOPE_VERSIONS: Final[tuple[int, ...]] = (
    registered_envelope_schema_versions()
)

# ---------------------------------------------------------------------------
# Bounded errors (explicit, deterministic failure reasons)
# ---------------------------------------------------------------------------


class BundleAuthorityCorpusError(Exception):
    """A bounded family corpus failure.

    ``failure_stage`` is a bounded vocabulary member naming the failing
    layer; ``reason`` is the deterministic, explicit failure reason
    (the exact check + the exact document path + the observed value)
    suitable for a future qualification report.
    """

    failure_stage: str

    def __init__(self, failure_stage: str, reason: str) -> None:
        super().__init__(f"[{failure_stage}] {reason}")
        self.failure_stage = failure_stage
        self.reason = reason


class BundleAuthoritySchemaError(BundleAuthorityCorpusError):
    """The corpus / case document violates the strict schema
    (structure, types, bounded vocabularies, identities)."""


class BundleAuthorityLabelError(BundleAuthorityCorpusError):
    """A label violates the label-governance contract of design
    section 4.6 (two identities, review state, the fixed independence
    attestation, the anti-derivation scan) or the expected-axis
    coherence pre-checks of design section 4.4."""


class BundleAuthorityEvidenceError(BundleAuthorityCorpusError):
    """An evidence document failed the frozen constructors / codec, or
    the evidence-side association / sealed-source grounding failed."""


class BundleAuthoritySealError(BundleAuthorityCorpusError):
    """The corpus identity is not the exact family seal (corpus id,
    version, binding, schema version)."""


class BundleAuthorityDigestError(BundleAuthorityCorpusError):
    """A digest does not verify (case / corpus / manifest / archive)."""


class BundleAuthorityManifestError(BundleAuthorityCorpusError):
    """The manifest structure or its agreement with the corpus failed."""


_STAGE_SCHEMA = "SCHEMA"
_STAGE_LABEL_GOVERNANCE = "LABEL_GOVERNANCE"
_STAGE_EVIDENCE = "EVIDENCE_INTEGRITY"
_STAGE_SEAL = "SEAL_IDENTITY"
_STAGE_DIGEST = "DIGEST_INTEGRITY"
_STAGE_MANIFEST = "MANIFEST_INTEGRITY"


def _schema(reason: str) -> BundleAuthoritySchemaError:
    return BundleAuthoritySchemaError(_STAGE_SCHEMA, reason)


def _label(reason: str) -> BundleAuthorityLabelError:
    return BundleAuthorityLabelError(_STAGE_LABEL_GOVERNANCE, reason)


def _evidence(reason: str) -> BundleAuthorityEvidenceError:
    return BundleAuthorityEvidenceError(_STAGE_EVIDENCE, reason)


def _seal(reason: str) -> BundleAuthoritySealError:
    return BundleAuthoritySealError(_STAGE_SEAL, reason)


def _digest(reason: str) -> BundleAuthorityDigestError:
    return BundleAuthorityDigestError(_STAGE_DIGEST, reason)


def _manifest(reason: str) -> BundleAuthorityManifestError:
    return BundleAuthorityManifestError(_STAGE_MANIFEST, reason)


# ---------------------------------------------------------------------------
# Document-level strict primitives (no coercion, no silent defaults)
# ---------------------------------------------------------------------------


def _exact_keys(value: Any, keys: frozenset[str], path: str) -> None:
    if not isinstance(value, dict):
        raise _schema(
            f"{path}: expected an object, got {type(value).__name__}"
        )
    missing = keys - value.keys()
    if missing:
        raise _schema(f"{path}: missing required keys: {sorted(missing)}")
    unknown = value.keys() - keys
    if unknown:
        raise _schema(f"{path}: unknown keys: {sorted(unknown)}")


def _json_native(value: Any, path: str) -> None:
    """Fail closed on any value the canonical encoding cannot represent
    exactly (floats, non-str keys, and every non-JSON-native object)."""
    if value is None or isinstance(value, (str, bool, int)):
        return
    if isinstance(value, float):
        raise _schema(
            f"{path}: float {value!r} is not permitted (no float "
            "authority data)"
        )
    if isinstance(value, list):
        for i, item in enumerate(value):
            _json_native(item, f"{path}[{i}]")
        return
    if isinstance(value, dict):
        for key, item in value.items():
            if not isinstance(key, str):
                raise _schema(
                    f"{path}: non-string key {key!r} is not permitted"
                )
            _json_native(item, f"{path}.{key}")
        return
    raise _schema(
        f"{path}: {type(value).__name__} is not JSON-native"
    )


def _str(value: Any, path: str, *, allow_empty: bool = False) -> str:
    if not isinstance(value, str) or (not allow_empty and not value):
        raise _schema(
            f"{path}: expected a {'non-empty ' if not allow_empty else ''}"
            f"str, got {value!r}"
        )
    return value


def _opt_str(value: Any, path: str) -> str | None:
    if value is None:
        return None
    return _str(value, path)


def _str_enum(value: Any, allowed: frozenset[str], path: str) -> str:
    if not isinstance(value, str) or value not in allowed:
        raise _schema(
            f"{path}: expected one of {sorted(allowed)}, got {value!r}"
        )
    return value


def _int(value: Any, path: str, *, minimum: int | None = None) -> int:
    if type(value) is not int:
        raise _schema(f"{path}: expected an int, got {type(value).__name__}")
    if minimum is not None and value < minimum:
        raise _schema(f"{path}: expected an int >= {minimum}, got {value!r}")
    return value


def _opt_int(value: Any, path: str, *, minimum: int | None = None) -> int | None:
    if value is None:
        return None
    return _int(value, path, minimum=minimum)


def _bool(value: Any, path: str) -> bool:
    if type(value) is not bool:
        raise _schema(f"{path}: expected a bool, got {type(value).__name__}")
    return value


def _opt_bool(value: Any, path: str) -> bool | None:
    if value is None:
        return None
    return _bool(value, path)


def _str_list(
    value: Any, path: str, *, allowed: frozenset[str] | None = None
) -> list[str]:
    if not isinstance(value, list) or not all(
        isinstance(item, str) for item in value
    ):
        raise _schema(f"{path}: expected a list of str")
    if allowed is not None and any(item not in allowed for item in value):
        raise _schema(
            f"{path}: expected members of {sorted(allowed)}, got {value!r}"
        )
    return value


def _sorted_unique_str_list(value: Any, path: str) -> list[str]:
    if (
        not isinstance(value, list)
        or not all(isinstance(item, str) for item in value)
        or len(set(value)) != len(value)
        or value != sorted(value)
    ):
        raise _schema(
            f"{path}: expected a sorted, unique list of str "
            f"(the canonical set encoding), got {value!r}"
        )
    return value


def utc_instant(value: Any, path: str) -> str:
    """Public strict UTC-instant decode (the builder entry point)."""
    return _utc_instant(value, path)


def _sha256(value: Any, path: str) -> str:
    if not isinstance(value, str) or not _SHA256_PATTERN.match(value):
        raise _schema(
            f"{path}: expected a 64-hex SHA-256 digest, got {value!r}"
        )
    return value


def _opt_sha256(value: Any, path: str) -> str | None:
    if value is None:
        return None
    return _sha256(value, path)


def _utc_instant(value: Any, path: str) -> str:
    if not isinstance(value, str) or not _UTC_INSTANT_PATTERN.match(value):
        raise _schema(
            f"{path}: expected an ISO-8601 UTC instant "
            f"('YYYY-MM-DDTHH:MM:SS[.ffffff]Z'), got {value!r}"
        )
    try:
        parsed = datetime.fromisoformat(value[:-1] + "+00:00")
    except ValueError:
        raise _schema(f"{path}: invalid ISO-8601 UTC instant {value!r}") from None
    if parsed.utcoffset() is None:
        raise _schema(f"{path}: non-UTC instant {value!r}")
    return value


def _opt_utc_instant(value: Any, path: str) -> str | None:
    if value is None:
        return None
    return _utc_instant(value, path)


def _relative_posix_path(value: Any, path: str) -> str:
    """A repo-relative POSIX path (no absolute, no parent reference, no
    platform separator — the canonical form the archive digest binds)."""
    _str(value, path)
    if (
        value.startswith("/")
        or "\\" in value
        or ".." in value.split("/")
        or not _POSIX_RELATIVE_PATH_PATTERN.match(value)
    ):
        raise _schema(
            f"{path}: expected a repo-relative POSIX path "
            f"(no absolute / parent / backslash), got {value!r}"
        )
    return value


def _opt_relative_posix_path(value: Any, path: str) -> str | None:
    if value is None:
        return None
    return _relative_posix_path(value, path)


# ---------------------------------------------------------------------------
# Observations (the sealed-raw defect scoping — see module docstring)
# ---------------------------------------------------------------------------

L_CONSTRUCTOR: Final[str] = "CONSTRUCTOR"
L_CODEC: Final[str] = "CODEC"
L_CASE_DOCUMENT: Final[str] = "CASE_DOCUMENT"
L_CASE_DOCUMENT_MIRROR: Final[str] = "CASE_DOCUMENT_MIRROR"
L_GATE: Final[str] = "GATE"


@dataclass(frozen=True)
class _Observation:
    """One fired family / frozen-constructor check over a case."""

    check: str
    layer: str
    detail: str


# ---------------------------------------------------------------------------
# Typed evidence-document decodes (the REAL frozen constructors are the
# validators; the canonical round-trip proves the sealed document is the
# EXACT frozen construction)
# ---------------------------------------------------------------------------


def _decode_str_enum_or_none(value: Any, allowed: frozenset[str], path: str):
    if value is None:
        return None
    _str_enum(value, allowed, path)
    return value


def decode_channel_document(doc: Any, *, path: str = "channel") -> CandidateSalesUnitEvidenceV2:
    """Strict-decode the 5-field frozen S2-C channel document and prove
    the canonical round-trip (the sealed document must be the exact
    canonical form of its own frozen construction)."""
    _exact_keys(
        doc,
        frozenset({"state", "kind", "quantity", "raw_detail", "source"}),
        path,
    )
    state = _str_enum(doc["state"], _CHANNEL_STATE_VALUES, f"{path}.state")
    kind = _decode_str_enum_or_none(
        doc["kind"], _CHANNEL_KIND_VALUES, f"{path}.kind"
    )
    quantity = _opt_int(doc["quantity"], f"{path}.quantity", minimum=1)
    raw_detail = _opt_str(doc["raw_detail"], f"{path}.raw_detail")
    source = _decode_str_enum_or_none(
        doc["source"], _CANDIDATE_EVIDENCE_SOURCE_VALUES, f"{path}.source"
    )
    try:
        channel = CandidateSalesUnitEvidenceV2(
            state=PackagingEvidenceStateV2(state),
            kind=SalesUnitKindV2(kind) if kind is not None else None,
            quantity=quantity,
            raw_detail=raw_detail,
            source=(
                CandidateEvidenceSourceV2(source)
                if source is not None
                else None
            ),
        )
    except (ValueError, TypeError) as exc:
        raise _evidence(f"{path}: frozen channel constructor: {exc}") from exc
    if channel.canonical() != doc:
        raise _evidence(
            f"{path}: the sealed document is not the exact canonical "
            "form of its frozen channel construction (round-trip "
            "identity failed)"
        )
    return channel


def _decode_target_evidence_v2(doc: Any, path: str) -> TargetEvidenceV2:
    _exact_keys(
        doc,
        frozenset({"mpn", "description_raw_text", "reviewed_context"}),
        path,
    )
    reviewed_raw = doc["reviewed_context"]
    reviewed = None
    if reviewed_raw is not None:
        rpath = f"{path}.reviewed_context"
        _exact_keys(
            reviewed_raw,
            frozenset(
                {
                    "manufacturer",
                    "category",
                    "matched_base_part_number",
                    "relation_kind",
                    "relation_family_part_numbers",
                    "source_name",
                    "source_url",
                    "retrieved_at",
                    "evidence_body_sha256",
                }
            ),
            rpath,
        )
        relation_kind = _str_enum(
            reviewed_raw["relation_kind"],
            frozenset(k.value for k in TargetIdentifierRelationKindV2),
            f"{rpath}.relation_kind",
        )
        family = reviewed_raw["relation_family_part_numbers"]
        if (
            not isinstance(family, list)
            or not family
            or any(not isinstance(f, str) or not f for f in family)
            or len(set(family)) != len(family)
        ):
            raise _schema(
                f"{rpath}.relation_family_part_numbers: expected a "
                "non-empty unique list of non-empty strings"
            )
        _utc_instant(reviewed_raw["retrieved_at"], f"{rpath}.retrieved_at")
        _sha256(reviewed_raw["evidence_body_sha256"], f"{rpath}.evidence_body_sha256")
        for key in (
            "manufacturer",
            "category",
            "matched_base_part_number",
            "source_name",
            "source_url",
        ):
            _str(reviewed_raw[key], f"{rpath}.{key}")
        reviewed = ReviewedTargetContextV2(
            manufacturer=reviewed_raw["manufacturer"],
            category=reviewed_raw["category"],
            matched_base_part_number=reviewed_raw["matched_base_part_number"],
            relation_kind=TargetIdentifierRelationKindV2(relation_kind),
            relation_family_part_numbers=tuple(family),
            source_name=reviewed_raw["source_name"],
            source_url=reviewed_raw["source_url"],
            retrieved_at=reviewed_raw["retrieved_at"],
            evidence_body_sha256=reviewed_raw["evidence_body_sha256"],
        )
    return TargetEvidenceV2(
        mpn=_str(doc["mpn"], f"{path}.mpn"),
        description_raw_text=_opt_str(
            doc["description_raw_text"], f"{path}.description_raw_text"
        ),
        reviewed_context=reviewed,
    )


def _decode_observation_fact(value: Any, path: str) -> CandidateObservationFactV2 | None:
    if value is None:
        return None
    _exact_keys(value, frozenset({"value", "source"}), path)
    source = _str_enum(
        value["source"], _CANDIDATE_EVIDENCE_SOURCE_VALUES, f"{path}.source"
    )
    return CandidateObservationFactV2(
        value=_str(value["value"], f"{path}.value"),
        source=CandidateEvidenceSourceV2(source),
    )


def _decode_candidate_product(doc: Any, path: str) -> CandidateProductEvidenceV2:
    _exact_keys(doc, _CANDIDATE_PRODUCT_DIMENSION_KEYS | frozenset(
        {"raw_title_text", "raw_specification_text"}
    ), path)
    return CandidateProductEvidenceV2(
        **{
            dimension: _decode_observation_fact(
                doc[dimension], f"{path}.{dimension}"
            )
            for dimension in sorted(_CANDIDATE_PRODUCT_DIMENSION_KEYS)
        },
        raw_title_text=_opt_str(doc["raw_title_text"], f"{path}.raw_title_text"),
        raw_specification_text=_opt_str(
            doc["raw_specification_text"], f"{path}.raw_specification_text"
        ),
    )


def _decode_candidate_commercial(doc: Any, path: str) -> CandidateCommercialEvidenceV2:
    _exact_keys(
        doc,
        frozenset(
            {
                "condition",
                "price",
                "currency",
                "availability",
                "seller",
                "offer_url",
                "sales_unit",
            }
        ),
        path,
    )
    return CandidateCommercialEvidenceV2(
        condition=_decode_observation_fact(doc["condition"], f"{path}.condition"),
        price=_decode_observation_fact(doc["price"], f"{path}.price"),
        currency=_decode_observation_fact(doc["currency"], f"{path}.currency"),
        availability=_decode_observation_fact(
            doc["availability"], f"{path}.availability"
        ),
        seller=_decode_observation_fact(doc["seller"], f"{path}.seller"),
        offer_url=_opt_str(doc["offer_url"], f"{path}.offer_url"),
        sales_unit=decode_channel_document(
            doc["sales_unit"], path=f"{path}.sales_unit"
        ),
    )


def _decode_product_profile(doc: Any, path: str) -> ProductEvidenceProfileV2:
    _exact_keys(
        doc,
        frozenset({"has_usable_product_title", "matched_facts"}),
        path,
    )
    facts_raw = doc["matched_facts"]
    if not isinstance(facts_raw, list):
        raise _schema(f"{path}.matched_facts: expected a list")
    facts: set[ProductEvidenceFactV2] = set()
    for i, fact in enumerate(facts_raw):
        fpath = f"{path}.matched_facts[{i}]"
        _exact_keys(fact, frozenset({"dimension", "sources"}), fpath)
        dimension = _str_enum(
            fact["dimension"],
            _PRODUCT_EVIDENCE_DIMENSION_VALUES,
            f"{fpath}.dimension",
        )
        sources = _sorted_unique_str_list(fact["sources"], f"{fpath}.sources")
        if not sources or any(s not in _AUTH_SOURCE_VALUES for s in sources):
            raise _schema(
                f"{fpath}.sources: expected a non-empty sorted unique "
                f"list drawn from {sorted(_AUTH_SOURCE_VALUES)}"
            )
        facts.add(
            ProductEvidenceFactV2(
                ProductEvidenceDimension(dimension),
                frozenset(CandidateProductEvidenceSource(s) for s in sources),
            )
        )
    return ProductEvidenceProfileV2(
        has_usable_product_title=_bool(
            doc["has_usable_product_title"], f"{path}.has_usable_product_title"
        ),
        matched_facts=frozenset(facts),
    )


def decode_v2_case_document(doc: Any, *, path: str = "v2_case_document") -> SemanticMatchCaseV2:
    """Strict-decode the EXACT ``SemanticMatchCaseV2`` input document
    (the frozen S2-C case contract — the family's constructor-path
    equivalent of the semantic family's ``decode_match_case``, per
    design section 4.4). The REAL frozen case constructor is the final
    arbiter and the ``canonical()`` round-trip proves the sealed
    document is the exact canonical form."""
    _exact_keys(
        doc,
        frozenset(
            {
                "case_id",
                "target",
                "candidate",
                "deterministic_identity_context",
                "context_provenance",
                "product_evidence",
            }
        ),
        path,
    )
    target = _decode_target_evidence_v2(doc["target"], f"{path}.target")
    cand = doc["candidate"]
    cpath = f"{path}.candidate"
    _exact_keys(
        cand,
        frozenset(
            {"source_url", "mpn_field", "sku", "evidence_source", "product", "commercial"}
        ),
        cpath,
    )
    product = _decode_candidate_product(cand["product"], f"{cpath}.product")
    commercial = _decode_candidate_commercial(
        cand["commercial"], f"{cpath}.commercial"
    )
    dic = doc["deterministic_identity_context"]
    dpath = f"{path}.deterministic_identity_context"
    _exact_keys(
        dic,
        frozenset(
            {
                "identity_state",
                "substate",
                "primary_relationship_signal",
                "relationship_signals",
                "normalized_requested_part_number",
                "normalized_candidate_part_number",
                "relationship_requirement",
            }
        ),
        dpath,
    )
    state = _str_enum(dic["identity_state"], _STATE_VALUES, f"{dpath}.identity_state")
    substate_value = _str_enum(
        dic["substate"], frozenset(_SUBSTATE_MEMBERS), f"{dpath}.substate"
    )
    substate = _SUBSTATE_MEMBERS[substate_value]
    primary_value = _str_enum(
        dic["primary_relationship_signal"],
        _SIGNAL_VALUES,
        f"{dpath}.primary_relationship_signal",
    )
    signals = _sorted_unique_str_list(
        dic["relationship_signals"], f"{dpath}.relationship_signals"
    )
    if not signals or any(s not in _SIGNAL_VALUES for s in signals):
        raise _schema(f"{dpath}.relationship_signals: unknown signal member")
    req_value = _str_enum(
        dic["relationship_requirement"],
        _REQUIREMENT_VALUES,
        f"{dpath}.relationship_requirement",
    )
    normalized_requested = _str(
        dic["normalized_requested_part_number"],
        f"{dpath}.normalized_requested_part_number",
    )
    normalized_candidate = _str(
        dic["normalized_candidate_part_number"],
        f"{dpath}.normalized_candidate_part_number",
    )
    try:
        assessment = IdentityStateAssessmentV2(
            state=IdentityStateV2(state),
            substate=substate,
            relationship_signals=frozenset(
                IdentityRelationshipSignal(s) for s in signals
            ),
            normalized_requested_part_number=normalized_requested,
            normalized_candidate_part_number=normalized_candidate,
        )
    except (ValueError, TypeError) as exc:
        raise _evidence(f"{dpath}: frozen identity assessment: {exc}") from exc
    if assessment.primary_relationship_signal.value != primary_value:
        raise _evidence(
            f"{dpath}: primary_relationship_signal {primary_value!r} "
            "disagrees with the recorded relationship signals "
            f"(frozen: {assessment.primary_relationship_signal.value!r})"
        )
    expected_requirement = substate_relationship_requirement(
        substate, assessment.primary_relationship_signal
    )
    if expected_requirement.value != req_value:
        raise _evidence(
            f"{dpath}: relationship_requirement {req_value!r} disagrees "
            f"with the frozen table ({expected_requirement.value!r})"
        )
    provenances_raw = _sorted_unique_str_list(
        doc["context_provenance"], f"{path}.context_provenance"
    )
    if any(p not in _PROVENANCE_VALUES for p in provenances_raw):
        raise _schema(f"{path}.context_provenance: unknown provenance member")
    profile = _decode_product_profile(doc["product_evidence"], f"{path}.product_evidence")
    try:
        case = SemanticMatchCaseV2(
            case_id=_str(doc["case_id"], f"{path}.case_id"),
            target=target,
            candidate_source_url=_str(cand["source_url"], f"{cpath}.source_url"),
            candidate_mpn_field=_opt_str(cand["mpn_field"], f"{cpath}.mpn_field"),
            candidate_sku=_opt_str(cand["sku"], f"{cpath}.sku"),
            candidate_evidence_source=_str(
                cand["evidence_source"], f"{cpath}.evidence_source"
            ),
            candidate_product=product,
            candidate_commercial=commercial,
            identity_state=assessment.state,
            substate=assessment.substate,
            primary_relationship_signal=assessment.primary_relationship_signal,
            relationship_signals=assessment.relationship_signals,
            normalized_requested_part_number=normalized_requested,
            normalized_candidate_part_number=normalized_candidate,
            relationship_requirement=expected_requirement,
            context_provenances=frozenset(
                ContextProvenance(p) for p in provenances_raw
            ),
            product_evidence=profile,
        )
    except (ValueError, TypeError) as exc:
        raise _evidence(f"{path}: frozen V2 case constructor: {exc}") from exc
    if case.canonical() != doc:
        raise _evidence(
            f"{path}: the sealed document is not the exact canonical form "
            "of its frozen V2 case construction (round-trip identity failed)"
        )
    return case


def _decode_completeness_attestation(
    doc: Any, *, path: str, side: EvidenceSideV2FU4 | None = None
) -> CompositionCompletenessAttestationV2FU4:
    """Strict-decode a composition-completeness attestation document
    (the frozen record constructor is the validator: the digest
    self-verifies, the side / basis / source-class coherence is
    enforced — no model claim member exists in the vocabulary)."""
    _exact_keys(
        doc,
        frozenset(
            {
                "schema_version",
                "subject_side",
                "basis",
                "source",
                "clause_digest",
                "attestation_text",
                "attestation_digest",
            }
        ),
        path,
    )
    version = _int(doc["schema_version"], f"{path}.schema_version")
    if version != _FU4_EVIDENCE_VERSION:
        raise _evidence(
            f"{path}.schema_version: expected {_FU4_EVIDENCE_VERSION} "
            f"(the frozen FU4 evidence version), got {version!r}"
        )
    subject = _str_enum(doc["subject_side"], _SIDE_VALUES, f"{path}.subject_side")
    basis = _str_enum(doc["basis"], _COMPLETENESS_BASIS_VALUES, f"{path}.basis")
    source = _str(doc["source"], f"{path}.source")
    if source not in _CANDIDATE_EVIDENCE_SOURCE_VALUES | _TARGET_EVIDENCE_SOURCE_VALUES:
        raise _evidence(
            f"{path}.source: expected a frozen non-model attestation class "
            f"({sorted(_CANDIDATE_EVIDENCE_SOURCE_VALUES | _TARGET_EVIDENCE_SOURCE_VALUES)}), "
            f"got {source!r}"
        )
    clause_digest = _sha256(doc["clause_digest"], f"{path}.clause_digest")
    attestation_text = _str(doc["attestation_text"], f"{path}.attestation_text")
    attestation_digest = _sha256(
        doc["attestation_digest"], f"{path}.attestation_digest"
    )
    for enum in (
        lambda: CandidateEvidenceSourceV2(source),
        lambda: TargetSalesUnitEvidenceSourceV2(source),
    ):
        try:
            source_value = enum()
        except (ValueError, TypeError):
            continue
        try:
            attestation = CompositionCompletenessAttestationV2FU4(
                _FU4_EVIDENCE_VERSION,
                EvidenceSideV2FU4(subject),
                CompletenessBasisV2FU4(basis),
                source_value,
                clause_digest,
                attestation_text,
                attestation_digest,
            )
        except (ValueError, TypeError, BundleCompositionEvidenceIntegrityError) as exc:
            # The other source-class enum is the next attempt; the
            # side/basis coherence is the constructor's to enforce.
            continue
        if side is not None and attestation.subject_side is not side:
            raise _evidence(
                f"{path}: subject_side {subject!r} does not match the "
                f"record side {side.value!r} (evidence-side association)"
            )
        if (
            {
                **attestation.canonical(),
                "attestation_digest": attestation.attestation_digest,
            }
            != doc
        ):
            raise _evidence(
                f"{path}: the sealed document is not the exact sealed "
                "form of its frozen attestation construction (round-trip "
                "identity failed)"
            )
        return attestation
    raise _evidence(
        f"{path}: the frozen attestation constructor refused the sealed "
        "document (side / basis / source-class / digest incoherent)"
    )


def _decode_quantity_attestation(
    doc: Any, *, path: str
) -> QuantityCompletenessAttestationV2FU4:
    _exact_keys(
        doc,
        frozenset(
            {
                "schema_version",
                "subject_side",
                "reason",
                "source",
                "attestation_text",
                "attestation_digest",
            }
        ),
        path,
    )
    version = _int(doc["schema_version"], f"{path}.schema_version")
    if version != _FU4_EVIDENCE_VERSION:
        raise _evidence(
            f"{path}.schema_version: expected {_FU4_EVIDENCE_VERSION}, "
            f"got {version!r}"
        )
    subject = _str_enum(doc["subject_side"], _SIDE_VALUES, f"{path}.subject_side")
    reason = _str_enum(doc["reason"], _QUANTITY_REASON_VALUES, f"{path}.reason")
    source = _str_enum(
        doc["source"], _TARGET_EVIDENCE_SOURCE_VALUES, f"{path}.source"
    )
    attestation_text = _str(doc["attestation_text"], f"{path}.attestation_text")
    attestation_digest = _sha256(
        doc["attestation_digest"], f"{path}.attestation_digest"
    )
    try:
        attestation = QuantityCompletenessAttestationV2FU4(
            _FU4_EVIDENCE_VERSION,
            EvidenceSideV2FU4(subject),
            QuantityNonMaterialityReasonV2FU4(reason),
            TargetSalesUnitEvidenceSourceV2(source),
            attestation_text,
            attestation_digest,
        )
    except (ValueError, TypeError, BundleCompositionEvidenceIntegrityError) as exc:
        raise _evidence(
            f"{path}: frozen quantity attestation constructor: {exc}"
        ) from exc
    if (
        {
            **attestation.canonical(),
            "attestation_digest": attestation.attestation_digest,
        }
        != doc
    ):
        raise _evidence(
            f"{path}: the sealed document is not the exact sealed form "
            "of its frozen attestation construction (round-trip identity "
            "failed)"
        )
    return attestation


def _decode_extraction_result(doc: Any, *, path: str) -> SalesUnitExtractionResult:
    """Strict-decode a frozen P2 extraction result document (schema
    v1). The result constructor re-computes the ``result_digest`` (the
    sealed document must be the exact self-consistent original) and
    ``verify_integrity()`` re-proves the cue-span containment."""
    _exact_keys(
        doc,
        frozenset(
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
        ),
        path,
    )
    version = _int(doc["schema_version"], f"{path}.schema_version")
    if version != _EXTRACTION_SCHEMA_VERSION:
        raise _evidence(
            f"{path}.schema_version: expected {_EXTRACTION_SCHEMA_VERSION} "
            f"(the frozen P2 extraction schema), got {version!r}"
        )
    state = _str_enum(doc["state"], _EXTRACTION_STATE_VALUES, f"{path}.state")
    cues_raw = doc["cues"]
    if not isinstance(cues_raw, list):
        raise _schema(f"{path}.cues: expected a list")
    cues: list[SalesUnitCueV1] = []
    for i, cue_doc in enumerate(cues_raw):
        cpath = f"{path}.cues[{i}]"
        _exact_keys(
            cue_doc,
            frozenset(
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
            ),
            cpath,
        )
        field = _str_enum(cue_doc["field"], _CUE_FIELD_VALUES, f"{cpath}.field")
        source = _str_enum(
            cue_doc["source"],
            _CANDIDATE_EVIDENCE_SOURCE_VALUES,
            f"{cpath}.source",
        )
        kind = _decode_str_enum_or_none(
            cue_doc["kind"], _CHANNEL_KIND_VALUES, f"{cpath}.kind"
        )
        disposition = _str_enum(
            cue_doc["disposition"], _CUE_DISPOSITION_VALUES, f"{cpath}.disposition"
        )
        reason = _decode_str_enum_or_none(
            cue_doc["reason"], _CUE_REASON_VALUES, f"{cpath}.reason"
        )
        try:
            cues.append(
                SalesUnitCueV1(
                    field=SalesUnitCueField(field),
                    source=CandidateEvidenceSourceV2(source),
                    raw_field_value=_str(
                        cue_doc["raw_field_value"], f"{cpath}.raw_field_value"
                    ),
                    cue_text=_str(cue_doc["cue_text"], f"{cpath}.cue_text"),
                    cue_start=_int(cue_doc["cue_start"], f"{cpath}.cue_start", minimum=0),
                    cue_end=_int(cue_doc["cue_end"], f"{cpath}.cue_end", minimum=0),
                    kind=SalesUnitKindV2(kind) if kind is not None else None,
                    quantity=_opt_int(cue_doc["quantity"], f"{cpath}.quantity", minimum=1),
                    disposition=SalesUnitCueDisposition(disposition),
                    reason=SalesUnitCueReason(reason) if reason is not None else None,
                )
            )
        except (ValueError, TypeError) as exc:
            raise _evidence(f"{cpath}: frozen cue constructor: {exc}") from exc
    notes_raw = doc["identifier_field_notes"]
    if not isinstance(notes_raw, list):
        raise _schema(f"{path}.identifier_field_notes: expected a list")
    notes: list[SalesUnitIdentifierFieldNoteV1] = []
    for i, note_doc in enumerate(notes_raw):
        npath = f"{path}.identifier_field_notes[{i}]"
        _exact_keys(
            note_doc, frozenset({"field_name", "token_text"}), npath
        )
        try:
            notes.append(
                SalesUnitIdentifierFieldNoteV1(
                    field_name=_str(note_doc["field_name"], f"{npath}.field_name"),
                    token_text=_str(note_doc["token_text"], f"{npath}.token_text"),
                )
            )
        except (ValueError, TypeError) as exc:
            raise _evidence(
                f"{npath}: frozen identifier-field note constructor: {exc}"
            ) from exc
    established_kind = _decode_str_enum_or_none(
        doc["established_kind"], _CHANNEL_KIND_VALUES, f"{path}.established_kind"
    )
    established_quantity = _opt_int(
        doc["established_quantity"], f"{path}.established_quantity", minimum=1
    )
    input_digest = _sha256(doc["input_digest"], f"{path}.input_digest")
    # The sealed document carries the result's self-verifying
    # ``result_digest`` (the codec sealed form). The frozen constructor
    # re-computes it over the content and refuses a stale / forged
    # value - the digest is never recovered or re-issued here.
    stored_result_digest = _sha256(doc["result_digest"], f"{path}.result_digest")
    try:
        result = SalesUnitExtractionResult(
            _EXTRACTION_SCHEMA_VERSION,
            SalesUnitExtractionState(state),
            tuple(cues),
            tuple(notes),
            SalesUnitKindV2(established_kind)
            if established_kind is not None
            else None,
            established_quantity,
            input_digest,
            stored_result_digest,
        )
    except (
        ValueError,
        TypeError,
        SalesUnitExtractionIntegrityError,
    ) as exc:
        raise _evidence(f"{path}: frozen extraction result constructor: {exc}") from exc
    if {
        **result.canonical(),
        "result_digest": result.result_digest,
    } != doc:
        raise _evidence(
            f"{path}: the sealed document is not the exact sealed form "
            "of its frozen extraction result construction (round-trip "
            "identity failed)"
        )
    try:
        result.verify_integrity()
    except SalesUnitExtractionIntegrityError as exc:
        raise _evidence(
            f"{path}: the sealed result fails its own integrity "
            f"verification: {exc}"
        ) from exc
    return result


def _decode_candidate_composition(
    doc: Any, *, path: str
) -> CandidateBundleCompositionEvidenceV2FU4:
    """Strict-decode a v3 candidate composition record document (the
    frozen record constructor is the validator: the state/coherence
    matrix, the basis / extraction-anchor coherence, the embedded
    attestation + embedded original result, and the ``evidence_digest``
    all re-verify)."""
    _exact_keys(
        doc,
        frozenset(
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
        ),
        path,
    )
    version = _int(doc["schema_version"], f"{path}.schema_version")
    if version != _FU4_EVIDENCE_VERSION:
        raise _evidence(
            f"{path}.schema_version: expected {_FU4_EVIDENCE_VERSION} "
            "(the frozen FU4 evidence version — a superseded / unknown "
            f"version is never silently reinterpreted), got {version!r}"
        )
    basis = _str_enum(doc["basis"], CANDIDATE_BASIS_VALUES - {"NONE"}, f"{path}.basis")
    state = _str_enum(doc["state"], COMPOSITION_STATE_VALUES, f"{path}.state")
    source = _str_enum(doc["source"], _CANDIDATE_EVIDENCE_SOURCE_VALUES, f"{path}.source")
    attestation_doc = doc["completeness_attestation"]
    attestation = (
        _decode_completeness_attestation(
            attestation_doc, path=f"{path}.completeness_attestation"
        )
        if attestation_doc is not None
        else None
    )
    additional = doc["additional_clauses"]
    if (
        not isinstance(additional, list)
        or not all(isinstance(item, str) for item in additional)
    ):
        raise _schema(f"{path}.additional_clauses: expected a list of str")
    result_doc = doc["extraction_result"]
    result = (
        _decode_extraction_result(result_doc, path=f"{path}.extraction_result")
        if result_doc is not None
        else None
    )
    try:
        record = CandidateBundleCompositionEvidenceV2FU4(
            _FU4_EVIDENCE_VERSION,
            CandidateCompositionEvidenceBasisV2FU4(basis),
            BundleCompositionStateV2FU4(state),
            attestation,
            _opt_str(doc["composition_clause"], f"{path}.composition_clause"),
            tuple(additional),
            CandidateEvidenceSourceV2(source),
            _opt_int(doc["channel_quantity"], f"{path}.channel_quantity", minimum=1),
            _opt_sha256(doc["extraction_result_digest"], f"{path}.extraction_result_digest"),
            _opt_sha256(doc["extraction_input_digest"], f"{path}.extraction_input_digest"),
            result,
            _sha256(doc["channel_content_digest"], f"{path}.channel_content_digest"),
            _sha256(doc["evidence_digest"], f"{path}.evidence_digest"),
        )
    except (
        ValueError,
        TypeError,
        BundleCompositionEvidenceIntegrityError,
        SalesUnitExtractionIntegrityError,
    ) as exc:
        raise _evidence(
            f"{path}: frozen candidate composition constructor: {exc}"
        ) from exc
    if _candidate_sealed_form(record) != doc:
        raise _evidence(
            f"{path}: the sealed document is not the exact sealed form "
            "of its frozen composition record construction (round-trip "
            "identity failed)"
        )
    return record


def _candidate_sealed_form(
    record: CandidateBundleCompositionEvidenceV2FU4,
) -> dict[str, Any]:
    """The family sealed form of a v3 candidate composition record
    (the frozen codec's document convention): the canonical document
    with the embedded attestation / extraction-result documents
    carrying their self-verifying digests, plus the record's
    ``evidence_digest``."""
    form = dict(record.canonical())
    if record.completeness_attestation is not None:
        att = record.completeness_attestation
        form["completeness_attestation"] = {
            **att.canonical(),
            "attestation_digest": att.attestation_digest,
        }
    if record.extraction_result is not None:
        res = record.extraction_result
        form["extraction_result"] = {
            **res.canonical(),
            "result_digest": res.result_digest,
        }
    form["evidence_digest"] = record.evidence_digest
    return form


def _decode_target_fu4(doc: Any, *, path: str) -> TargetSalesUnitEvidenceV2FU4:
    """Strict-decode an FU4 v3 target-side record document (the frozen
    constructor is the validator: the form / quantity rules, the
    bundle-only composition coherence, the embedded attestation's side
    / basis / clause binding, the ``evidence_digest``)."""
    _exact_keys(
        doc,
        frozenset(
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
        ),
        path,
    )
    version = _int(doc["schema_version"], f"{path}.schema_version")
    if version != _FU4_EVIDENCE_VERSION:
        raise _evidence(
            f"{path}.schema_version: expected {_FU4_EVIDENCE_VERSION}, "
            f"got {version!r}"
        )
    form = _str_enum(doc["form"], _TARGET_FORM_VALUES, f"{path}.form")
    source = _str_enum(doc["source"], _TARGET_EVIDENCE_SOURCE_VALUES, f"{path}.source")
    composition_state = _decode_str_enum_or_none(
        doc["composition_state"], COMPOSITION_STATE_VALUES, f"{path}.composition_state"
    )
    attestation_doc = doc["completeness_attestation"]
    attestation = (
        _decode_completeness_attestation(
            attestation_doc, path=f"{path}.completeness_attestation"
        )
        if attestation_doc is not None
        else None
    )
    try:
        record = TargetSalesUnitEvidenceV2FU4(
            _FU4_EVIDENCE_VERSION,
            TargetSalesUnitFormV2(form),
            _opt_int(doc["quantity"], f"{path}.quantity", minimum=1),
            TargetSalesUnitEvidenceSourceV2(source),
            _opt_str(doc["composition_clause"], f"{path}.composition_clause"),
            BundleCompositionStateV2FU4(composition_state)
            if composition_state is not None
            else None,
            attestation,
            _sha256(doc["evidence_digest"], f"{path}.evidence_digest"),
        )
    except (
        ValueError,
        TypeError,
        BundleCompositionEvidenceIntegrityError,
    ) as exc:
        raise _evidence(f"{path}: frozen target record constructor: {exc}") from exc
    if _target_fu4_sealed_form(record) != doc:
        raise _evidence(
            f"{path}: the sealed document is not the exact sealed form "
            "of its frozen target record construction (round-trip identity "
            "failed)"
        )
    return record


def _target_fu4_sealed_form(
    record: TargetSalesUnitEvidenceV2FU4,
) -> dict[str, Any]:
    """The family sealed form of an FU4 v3 target record (the frozen
    codec's document convention): the canonical document with the
    embedded attestation carrying its self-verifying digest, plus the
    record's ``evidence_digest``."""
    form = dict(record.canonical())
    if record.completeness_attestation is not None:
        att = record.completeness_attestation
        form["completeness_attestation"] = {
            **att.canonical(),
            "attestation_digest": att.attestation_digest,
        }
    form["evidence_digest"] = record.evidence_digest
    return form


def _decode_target_fu3(doc: Any, *, path: str) -> TargetSalesUnitEvidenceV2:
    """Strict-decode a frozen FU3 target-side record document (the
    version-owned ``frozen_fu3`` shape: form / quantity / source only —
    the D18 composition-ABSENT reading, no implicit upgrade)."""
    _exact_keys(
        doc, frozenset({"form", "quantity", "source"}), path
    )
    form = _str_enum(doc["form"], _TARGET_FORM_VALUES, f"{path}.form")
    source = _str_enum(doc["source"], _TARGET_EVIDENCE_SOURCE_VALUES, f"{path}.source")
    try:
        record = TargetSalesUnitEvidenceV2(
            TargetSalesUnitFormV2(form),
            _opt_int(doc["quantity"], f"{path}.quantity", minimum=1),
            TargetSalesUnitEvidenceSourceV2(source),
        )
    except (ValueError, TypeError) as exc:
        raise _evidence(f"{path}: frozen FU3 target record constructor: {exc}") from exc
    projection = {
        "form": record.form.value,
        "quantity": record.quantity,
        "source": record.source.value,
    }
    if projection != doc:
        raise _evidence(
            f"{path}: the sealed document is not the exact projection of "
            "its frozen FU3 target record (round-trip identity failed)"
        )
    return record


# ---------------------------------------------------------------------------
# The sealed source blocks (the original published source content +
# provenance; the L3 recording act)
# ---------------------------------------------------------------------------

_SOURCE_BLOCK_KEYS = frozenset(
    {
        "title_text",
        "structured_fields",
        "source_url",
        "retrieved_utc",
        "raw_reference",
        "archive",
        "archive_digest",
        "recording_attestation",
    }
)
# ---------------------------------------------------------------------------
# The sealed source blocks (the original published source content +
# provenance; the L3 recording act)
# ---------------------------------------------------------------------------

_SOURCE_BLOCK_KEYS = frozenset(
    {
        "title_text",
        "structured_fields",
        "source_url",
        "retrieved_utc",
        "raw_reference",
        "archive",
        "archive_digest",
        "recording_attestation",
    }
)


def _decode_source_block(doc: Any, *, path: str, kind: str) -> dict[str, Any]:
    """Strict-decode one side's sealed source block. The block records
    the ORIGINAL published source content + the retrieval metadata; the
    per-evidence-kind provenance rules of design section 4.4 apply:

    * SYNTHETIC — by-construction: no URL, no retrieval instant, no
      archive, the fixed ``by-construction`` recording attestation;
    * RECORDED_FIXTURE / REAL_MARKET — retrieved: URL + retrieval
      instant + raw reference + archive path + archive digest + the
      recording attestation (the L3 recording act), archived under the
      family ``sources/`` layout for REAL_MARKET.
    """
    _exact_keys(doc, _SOURCE_BLOCK_KEYS, path)
    title_text = _opt_str(doc["title_text"], f"{path}.title_text")
    structured_fields = doc["structured_fields"]
    if not isinstance(structured_fields, dict):
        raise _schema(f"{path}.structured_fields: expected an object")
    for key, value in structured_fields.items():
        _str(key, f"{path}.structured_fields key")
        _str(value, f"{path}.structured_fields[{key!r}]", allow_empty=True)
    source_url = _opt_str(doc["source_url"], f"{path}.source_url")
    retrieved_utc = _opt_utc_instant(doc["retrieved_utc"], f"{path}.retrieved_utc")
    raw_reference = _opt_str(doc["raw_reference"], f"{path}.raw_reference")
    archive = _opt_relative_posix_path(doc["archive"], f"{path}.archive")
    archive_digest = _opt_sha256(doc["archive_digest"], f"{path}.archive_digest")
    recording_attestation = _opt_str(
        doc["recording_attestation"], f"{path}.recording_attestation"
    )
    if kind == "SYNTHETIC":
        if (
            source_url is not None
            or retrieved_utc is not None
            or raw_reference is not None
            or archive is not None
            or archive_digest is not None
        ):
            raise _schema(
                f"{path}: a SYNTHETIC source block is by-construction "
                "(no URL / retrieval instant / raw reference / archive)"
            )
        if recording_attestation != SYNTHETIC_RECORDING_ATTESTATION:
            raise _schema(
                f"{path}: a SYNTHETIC source block carries the fixed "
                f"{SYNTHETIC_RECORDING_ATTESTATION!r} recording "
                f"attestation, got {recording_attestation!r}"
            )
    else:
        if (
            source_url is None
            or retrieved_utc is None
            or raw_reference is None
            or archive is None
            or archive_digest is None
            or recording_attestation is None
        ):
            raise _schema(
                f"{path}: a {kind} source block requires the retrieval "
                "metadata (source_url + retrieved_utc + raw_reference + "
                "archive + archive_digest + the recording attestation)"
            )
        if kind == "REAL_MARKET":
            prefix = (
                "evaluation/fu4_bundle_authority_qualification/sources/"
            )
            if not archive.startswith(prefix):
                raise _schema(
                    f"{path}: a REAL_MARKET archive lives under the "
                    f"family sources/ layout ({prefix}...), got {archive!r}"
                )
    return {
        "title_text": title_text,
        "structured_fields": structured_fields,
        "source_url": source_url,
        "retrieved_utc": retrieved_utc,
        "raw_reference": raw_reference,
        "archive": archive,
        "archive_digest": archive_digest,
        "recording_attestation": recording_attestation,
    }


def _source_texts(block: dict[str, Any]) -> list[str]:
    """The sealed published texts of one side (the span-grounding
    universe): the title text + every structured field value."""
    texts: list[str] = []
    if block["title_text"] is not None:
        texts.append(block["title_text"])
    texts.extend(block["structured_fields"].values())
    return texts


def _span_grounded(text: str, block: dict[str, Any]) -> bool:
    """True when the verbatim published text is span-grounded in the
    sealed source block (the cue / clause / statement the evidence
    claims was published on this side)."""
    return any(text in published for published in _source_texts(block))


# ---------------------------------------------------------------------------
# The scripted context (the Track A derivation inputs' identity side —
# the frozen S2-A context documents, never an authority input)
# ---------------------------------------------------------------------------


def _decode_identity_assessment(
    doc: Any, *, path: str
) -> IdentityStateAssessmentV2:
    _exact_keys(
        doc,
        frozenset(
            {
                "state",
                "substate",
                "relationship_signals",
                "normalized_requested_part_number",
                "normalized_candidate_part_number",
            }
        ),
        path,
    )
    state = _str_enum(doc["state"], _STATE_VALUES, f"{path}.state")
    substate_value = _str_enum(
        doc["substate"], frozenset(_SUBSTATE_MEMBERS), f"{path}.substate"
    )
    signals = _sorted_unique_str_list(
        doc["relationship_signals"], f"{path}.relationship_signals"
    )
    if not signals or any(s not in _SIGNAL_VALUES for s in signals):
        raise _schema(f"{path}.relationship_signals: unknown signal member")
    normalized_requested = _str(
        doc["normalized_requested_part_number"],
        f"{path}.normalized_requested_part_number",
    )
    normalized_candidate = _str(
        doc["normalized_candidate_part_number"],
        f"{path}.normalized_candidate_part_number",
    )
    try:
        assessment = IdentityStateAssessmentV2(
            state=IdentityStateV2(state),
            substate=_SUBSTATE_MEMBERS[substate_value],
            relationship_signals=frozenset(
                IdentityRelationshipSignal(s) for s in signals
            ),
            normalized_requested_part_number=normalized_requested,
            normalized_candidate_part_number=normalized_candidate,
        )
    except (ValueError, TypeError) as exc:
        raise _evidence(
            f"{path}: frozen identity assessment constructor: {exc}"
        ) from exc
    projection = {
        "state": assessment.state.value,
        "substate": assessment.substate.value,
        "relationship_signals": sorted(
            s.value for s in assessment.relationship_signals
        ),
        "normalized_requested_part_number": assessment.normalized_requested_part_number,
        "normalized_candidate_part_number": assessment.normalized_candidate_part_number,
    }
    if projection != doc:
        raise _evidence(
            f"{path}: the sealed document is not the exact projection of "
            "its frozen identity assessment (round-trip identity failed)"
        )
    return assessment


def _decode_evaluation(doc: Any, *, path: str) -> SemanticEvaluationV2:
    _exact_keys(
        doc,
        frozenset(
            {"evaluation_state", "decision", "confidence", "conflict_classes"}
        ),
        path,
    )
    eval_state = _str_enum(
        doc["evaluation_state"], _EVAL_STATE_VALUES, f"{path}.evaluation_state"
    )
    decision = _decode_str_enum_or_none(
        doc["decision"], _DECISION_VALUES, f"{path}.decision"
    )
    confidence = _decode_str_enum_or_none(
        doc["confidence"], _CONFIDENCE_VALUES, f"{path}.confidence"
    )
    conflicts = _sorted_unique_str_list(
        doc["conflict_classes"], f"{path}.conflict_classes"
    )
    if any(c not in _CONFLICT_VALUES for c in conflicts):
        raise _schema(f"{path}.conflict_classes: unknown conflict class member")
    try:
        evaluation = SemanticEvaluationV2(
            evaluation_state=SemanticEvaluationStateV2(eval_state),
            decision=V2SemanticDecision(decision) if decision is not None else None,
            confidence=V2Confidence(confidence) if confidence is not None else None,
            conflict_classes=frozenset(ConflictClass(c) for c in conflicts),
        )
    except (ValueError, TypeError) as exc:
        raise _evidence(f"{path}: frozen evaluation constructor: {exc}") from exc
    projection = {
        "evaluation_state": evaluation.evaluation_state.value,
        "decision": (
            evaluation.decision.value if evaluation.decision is not None else None
        ),
        "confidence": (
            evaluation.confidence.value
            if evaluation.confidence is not None
            else None
        ),
        "conflict_classes": sorted(
            c.value for c in evaluation.conflict_classes
        ),
    }
    if projection != doc:
        raise _evidence(
            f"{path}: the sealed document is not the exact projection of "
            "its frozen evaluation (round-trip identity failed)"
        )
    return evaluation


def _decode_scripted_context(
    doc: Any, *, path: str
) -> tuple[
    IdentityStateAssessmentV2,
    SemanticEvaluationV2,
    frozenset[ContextProvenance],
    ProductEvidenceProfileV2 | None,
]:
    _exact_keys(
        doc,
        frozenset(
            {
                "identity_assessment",
                "evaluation",
                "context_provenances",
                "product_evidence",
                "human_review",
            }
        ),
        path,
    )
    assessment = _decode_identity_assessment(
        doc["identity_assessment"], path=f"{path}.identity_assessment"
    )
    evaluation = _decode_evaluation(doc["evaluation"], path=f"{path}.evaluation")
    provenances_raw = _sorted_unique_str_list(
        doc["context_provenances"], f"{path}.context_provenances"
    )
    if any(p not in _PROVENANCE_VALUES for p in provenances_raw):
        raise _schema(f"{path}.context_provenances: unknown provenance member")
    profile_doc = doc["product_evidence"]
    profile = (
        _decode_product_profile(profile_doc, f"{path}.product_evidence")
        if profile_doc is not None
        else None
    )
    if doc["human_review"] is not None:
        raise _schema(
            f"{path}.human_review: expected null (human overlays are out "
            "of Track A — the replay precedent); the family schema v1 "
            "carries no overlay"
        )
    return (
        assessment,
        evaluation,
        frozenset(ContextProvenance(p) for p in provenances_raw),
        profile,
    )


# ---------------------------------------------------------------------------
# The label governance (design section 4.6 — mechanically enforced)
# ---------------------------------------------------------------------------

_LABEL_KEYS = frozenset(
    {
        "labeling_provenance",
        "grounding_citation",
        "author",
        "author_utc",
        "reviewer",
        "reviewer_utc",
        "review_status",
        "independence_attestation",
        "rationale",
    }
)


def _decode_label(doc: Any, *, case_id: str) -> dict[str, Any]:
    """Strict-decode + governance-check the label block. The label is
    an independently reviewed INPUT: this checks its structure and its
    recorded independence only — it never reads, computes, or fills any
    expected outcome (the anti-derivation contract of design
    section 4.6 item 2)."""
    path = f"case {case_id}: label"
    _exact_keys(doc, _LABEL_KEYS, path)
    _str_enum(
        doc["labeling_provenance"],
        LABELING_PROVENANCE_VALUES,
        f"{path}.labeling_provenance",
    )
    grounding_citation = _str(
        doc["grounding_citation"], f"{path}.grounding_citation"
    )
    author = _str(doc["author"], f"{path}.author")
    _utc_instant(doc["author_utc"], f"{path}.author_utc")
    reviewer = _str(doc["reviewer"], f"{path}.reviewer")
    _utc_instant(doc["reviewer_utc"], f"{path}.reviewer_utc")
    review_status = _str_enum(doc["review_status"], REVIEW_STATUS_VALUES, f"{path}.review_status")
    independence_attestation = _str(
        doc["independence_attestation"], f"{path}.independence_attestation"
    )
    rationale = _str(doc["rationale"], f"{path}.rationale")

    # Two distinct recorded identities (design section 4.6 item 4 — the
    # loader enforces inequality; a self-reviewed case is not a
    # qualification case).
    if author == reviewer:
        raise _label(
            f"{path}: label.author and label.reviewer must be distinct "
            f"recorded identities (the two-identity rule), both {author!r}"
        )
    # The fixed independence attestation (exact equality — the
    # statement is the contract, never free text).
    if independence_attestation != INDEPENDENCE_ATTESTATION:
        raise _label(
            f"{path}.independence_attestation: expected the fixed "
            "independence attestation statement, got different text"
        )
    # The mechanical anti-derivation scan (design section 4.6 item 2(b)):
    # label text must not name any model or implementation output as the
    # source of the expected outcome.
    for field_name, text in (
        ("grounding_citation", grounding_citation),
        ("rationale", rationale),
    ):
        lowered = text.lower()
        for token in sorted(FORBIDDEN_LABEL_TOKENS):
            if token in lowered:
                raise _label(
                    f"{path}.{field_name} names {token!r}; the expected "
                    "outcome must be independent of any model or "
                    "implementation output (the anti-derivation "
                    "contract)"
                )
    return dict(doc)


# ---------------------------------------------------------------------------
# The expected block (the independently labeled outcome + the
# coherence pre-checks of design section 4.4)
# ---------------------------------------------------------------------------

_EXPECTED_KEYS = frozenset(
    {
        "outcome",
        "unit",
        "quantity_axis",
        "candidate_composition_state",
        "target_composition_state",
        "textual_relation",
        "tier",
        "expected_ceiling",
        "pricing_eligible",
        "replay",
        "refusal",
        "semantic_identity_note",
    }
)
_REFUSAL_KEYS = frozenset({"stage", "error_type"})


def _decode_expected(
    doc: Any, *, case_id: str, track: str, surface: str | None
) -> dict[str, Any]:
    path = f"case {case_id}: expected"
    _exact_keys(doc, _EXPECTED_KEYS, path)
    outcome = _str_enum(doc["outcome"], OUTCOME_VALUES, f"{path}.outcome")
    unit = _decode_str_enum_or_none(doc["unit"], UNIT_VALUES, f"{path}.unit")
    quantity_axis = _decode_str_enum_or_none(
        doc["quantity_axis"], QUANTITY_AXIS_VALUES, f"{path}.quantity_axis"
    )
    cand_state = _decode_str_enum_or_none(
        doc["candidate_composition_state"],
        COMPOSITION_STATE_VALUES,
        f"{path}.candidate_composition_state",
    )
    tgt_state = _decode_str_enum_or_none(
        doc["target_composition_state"],
        COMPOSITION_STATE_VALUES,
        f"{path}.target_composition_state",
    )
    textual_relation = _decode_str_enum_or_none(
        doc["textual_relation"], TEXTUAL_RELATION_VALUES, f"{path}.textual_relation"
    )
    tier = _decode_str_enum_or_none(doc["tier"], TIER_VALUES, f"{path}.tier")
    ceiling = _decode_str_enum_or_none(
        doc["expected_ceiling"], CEILING_VALUES, f"{path}.expected_ceiling"
    )
    pricing_eligible = _opt_bool(doc["pricing_eligible"], f"{path}.pricing_eligible")
    replay = _str_enum(doc["replay"], REPLAY_VALUES, f"{path}.replay")
    refusal_doc = doc["refusal"]
    refusal = None
    if refusal_doc is not None:
        _exact_keys(refusal_doc, _REFUSAL_KEYS, f"{path}.refusal")
        stage = _str_enum(
            refusal_doc["stage"], REFUSAL_STAGES, f"{path}.refusal.stage"
        )
        error_type = _decode_str_enum_or_none(
            refusal_doc["error_type"],
            REFUSAL_ERROR_CLASSES,
            f"{path}.refusal.error_type",
        )
        if error_type is not None and error_type not in STAGE_ERROR_CLASSES[stage]:
            raise _schema(
                f"{path}.refusal.error_type: {error_type!r} is not the "
                f"error class of stage {stage!r} "
                f"(expected {sorted(s for s in STAGE_ERROR_CLASSES[stage] if s)})"
            )
        refusal = {"stage": stage, "error_type": error_type}
    semantic_identity_note = _opt_str(
        doc["semantic_identity_note"], f"{path}.semantic_identity_note"
    )
    return {
        "outcome": outcome,
        "unit": unit,
        "quantity_axis": quantity_axis,
        "candidate_composition_state": cand_state,
        "target_composition_state": tgt_state,
        "textual_relation": textual_relation,
        "tier": tier,
        "expected_ceiling": ceiling,
        "pricing_eligible": pricing_eligible,
        "replay": replay,
        "refusal": refusal,
        "semantic_identity_note": semantic_identity_note,
        "track": track,
        "surface": surface,
    }


def _check_expected_coherence(expected: dict[str, Any], *, case_id: str) -> None:
    """The expected-axis coherence pre-checks of design section 4.4 —
    the label is checked for obvious incoherence BEFORE the
    implementation is ever run; an incoherent label is a
    corpus-integrity failure, never a test failure. The checks use the
    frozen contract DATA (the bounded vocabularies, the frozen
    pricing-eligible tier set, the frozen ceiling-to-unit keying) —
    they never derive an outcome."""
    path = f"case {case_id}: expected"
    outcome = expected["outcome"]
    replay = expected["replay"]
    surface = expected["surface"]
    unit = expected["unit"]
    tier = expected["tier"]
    pricing_eligible = expected["pricing_eligible"]
    refusal = expected["refusal"]

    if outcome == "DERIVED":
        if unit is None:
            raise _label(
                f"{path}: a DERIVED expectation names its bounded unit "
                "state (no default is ever filled in)"
            )
        if tier is None:
            raise _label(
                f"{path}: a DERIVED expectation names its bounded tier "
                "(the tier derivation is total over a valid scripted "
                "context — no null is filled in)"
            )
        if pricing_eligible is None:
            raise _label(
                f"{path}: a DERIVED expectation names its tier-level "
                "pricing-eligibility consequence (bool, never null — "
                "null only when outcome != DERIVED)"
            )
        if refusal is not None:
            raise _label(f"{path}: a DERIVED expectation carries no refusal")
        if surface in ("RECORD", "BOTH") and replay != "REPLAY_PASS":
            raise _label(
                f"{path}: a DERIVED record-surface expectation names "
                f"replay REPLAY_PASS, got {replay!r}"
            )
        if surface == "DERIVATION" and replay != "NOT_APPLICABLE":
            raise _label(
                f"{path}: a DERIVED derivation-surface expectation names "
                f"replay NOT_APPLICABLE, got {replay!r}"
            )
        # The stated coherence rules (design section 4.4).
        if unit == "PROVEN_EQUIVALENT":
            if expected["quantity_axis"] not in (
                "CONSISTENT",
                "BOTH_UNPUBLISHED",
                "ATTESTED_NOT_MATERIAL",
            ):
                raise _label(
                    f"{path}: unit PROVEN_EQUIVALENT requires the "
                    "quantity axis CONSISTENT / BOTH_UNPUBLISHED / "
                    "ATTESTED_NOT_MATERIAL, got "
                    f"{expected['quantity_axis']!r}"
                )
            if (
                expected["candidate_composition_state"] != "ESTABLISHED"
                or expected["target_composition_state"] != "ESTABLISHED"
            ):
                raise _label(
                    f"{path}: unit PROVEN_EQUIVALENT requires both "
                    "composition states ESTABLISHED, got "
                    f"({expected['candidate_composition_state']!r}, "
                    f"{expected['target_composition_state']!r})"
                )
        if pricing_eligible is True:
            if unit != "PROVEN_EQUIVALENT":
                raise _label(
                    f"{path}: pricing_eligible true requires unit "
                    "PROVEN_EQUIVALENT (the human-review overlay arm is "
                    f"vacuous in family schema v1 - human_review null), "
                    f"got {unit!r}"
                )
            if tier not in PRICING_ELIGIBLE_TIER_VALUES:
                raise _label(
                    f"{path}: pricing_eligible true requires the frozen "
                    f"pricing-eligible tier set {sorted(PRICING_ELIGIBLE_TIER_VALUES)}, "
                    f"got tier {tier!r}"
                )
    else:  # REFUSED / NON_CONSTRUCTIBLE — no unit is derived
        if unit is not None:
            raise _label(
                f"{path}: an {outcome} expectation derives no unit "
                f"(unit must be null, got {unit!r})"
            )
        for axis_field in (
            "quantity_axis",
            "candidate_composition_state",
            "target_composition_state",
            "textual_relation",
            "tier",
            "expected_ceiling",
            "pricing_eligible",
        ):
            if expected[axis_field] is not None:
                raise _label(
                    f"{path}: an {outcome} expectation carries no "
                    f"derived {axis_field} (must be null, got "
                    f"{expected[axis_field]!r})"
                )
        if refusal is None:
            raise _label(
                f"{path}: an {outcome} expectation names its refusal "
                "(stage + the bounded error class or null)"
            )
        if surface in ("RECORD", "BOTH") and replay != "REPLAY_REFUSED":
            raise _label(
                f"{path}: an {outcome} record-surface expectation names "
                f"replay REPLAY_REFUSED, got {replay!r}"
            )
        if surface == "DERIVATION" and replay != "NOT_APPLICABLE":
            raise _label(
                f"{path}: an {outcome} derivation-surface expectation "
                f"names replay NOT_APPLICABLE, got {replay!r}"
            )
    # The frozen ceiling-to-unit keying (the restrict-only ceilings are
    # keyed exactly to the unit states — the firewall invariant): a
    # labeled ceiling must name the unit state that fires it.
    ceiling = expected["expected_ceiling"]
    if ceiling == "CEILING_SALES_UNIT_NOT_PROVEN" and unit != "UNPROVEN":
        raise _label(
            f"{path}: expected_ceiling CEILING_SALES_UNIT_NOT_PROVEN "
            f"keys exactly to unit UNPROVEN, got {unit!r}"
        )
    if ceiling == "CEILING_SALES_UNIT_CONTRADICTED" and unit != "CONTRADICTED":
        raise _label(
            f"{path}: expected_ceiling CEILING_SALES_UNIT_CONTRADICTED "
            f"keys exactly to unit CONTRADICTED, got {unit!r}"
        )
    # The semantic-identity note is Track A_B context (the independent
    # semantic-axis statement) — required for A_B cases, never for
    # pure Track A, optional for the B-only model controls.
    note = expected["semantic_identity_note"]
    track = expected["track"]
    if track == "A_B" and note is None:
        raise _label(
            f"{path}: an A_B case carries the independent semantic-axis "
            "statement (semantic_identity_note non-null)"
        )
    if track == "A" and note is not None:
        raise _label(
            f"{path}: a pure Track A case carries no semantic-identity "
            "note (context belongs to the A_B / B cases)"
        )


# ---------------------------------------------------------------------------
# The per-case strict decode (design section 4.4 exact key set + the
# family checks; the sealed-raw defect scope from the module docstring)
# ---------------------------------------------------------------------------

_CASE_KEYS = frozenset(
    {
        "case_id",
        "case_category",
        "matrix_row",
        "challenge_tags",
        "evidence_kind",
        "track",
        "surface",
        "source",
        "recorded_case",
        "derivation_inputs",
        "scripted_context",
        "published_quantity",
        "completeness_attestation_source",
        "expected",
        "label",
        "case_digest",
    }
)
_SOURCE_KEYS = frozenset({"target", "candidate"})
_RECORDS_KEYS_BASE = frozenset({"v2_case_document"})
_RECORDS_KEYS_RECORD_SURFACE = _RECORDS_KEYS_BASE | frozenset({"payload_document"})
_DERIVATION_INPUT_KEYS = frozenset(
    {
        "channel",
        "candidate_composition",
        "candidate_basis",
        "extraction_evidence",
        "target_evidence",
        "quantity_attestation",
    }
)
_EXTRACTION_EVIDENCE_KEYS = frozenset({"input_document", "result_document"})
_TARGET_EVIDENCE_KEYS = frozenset({"schema", "document"})
_PUBLISHED_QUANTITY_KEYS = frozenset({"candidate", "target", "citation"})
_ATT_SOURCE_KEYS = frozenset({"state", "verbatim", "anchor"})
_CAND_ATT_SOURCE_KEYS = frozenset({"state", "verbatim", "location"})


@dataclass(frozen=True)
class FamilyCaseEvidence:
    """The typed, frozen-constructor-verified evidence of one case."""

    v2_case: SemanticMatchCaseV2
    channel: CandidateSalesUnitEvidenceV2
    candidate_composition: CandidateBundleCompositionEvidenceV2FU4 | None
    extraction_result: SalesUnitExtractionResult | None
    target_evidence: (
        TargetSalesUnitEvidenceV2FU4 | TargetSalesUnitEvidenceV2 | None
    )
    quantity_attestation: QuantityCompletenessAttestationV2FU4 | None
    identity_assessment: IdentityStateAssessmentV2
    evaluation: SemanticEvaluationV2
    context_provenances: frozenset[ContextProvenance]
    product_evidence: ProductEvidenceProfileV2 | None
    payload_record: object | None


@dataclass(frozen=True)
class FamilyCorpusCase:
    """One decoded, digest-verified family corpus case."""

    case_id: str
    track: str
    surface: str | None
    evidence_kind: str
    matrix_row: str
    document: dict[str, Any]
    evidence: FamilyCaseEvidence
    expected: dict[str, Any]
    label: dict[str, Any]
    case_digest: str


def _decode_published_quantity(doc: Any, *, path: str) -> dict[str, Any]:
    _exact_keys(doc, _PUBLISHED_QUANTITY_KEYS, path)
    candidate = _opt_int(doc["candidate"], f"{path}.candidate", minimum=1)
    target = _opt_int(doc["target"], f"{path}.target", minimum=1)
    citation = _str(doc["citation"], f"{path}.citation")
    return {"candidate": candidate, "target": target, "citation": citation}


def _decode_att_source_candidate(doc: Any, *, path: str) -> dict[str, Any]:
    _exact_keys(doc, _CAND_ATT_SOURCE_KEYS, path)
    state = _str_enum(doc["state"], CANDIDATE_ATT_SOURCES, f"{path}.state")
    verbatim = _opt_str(doc["verbatim"], f"{path}.verbatim")
    location = _opt_str(doc["location"], f"{path}.location")
    if state == "ABSENT" and (verbatim is not None or location is not None):
        raise _schema(
            f"{path}: an ABSENT candidate attestation source carries no "
            "verbatim / location"
        )
    if state == "PUBLISHED_STATEMENT" and (
        verbatim is None or location is None
    ):
        raise _schema(
            f"{path}: a PUBLISHED_STATEMENT candidate attestation source "
            "carries the verbatim statement + its location"
        )
    return {"state": state, "verbatim": verbatim, "location": location}


def _decode_att_source_target(doc: Any, *, path: str) -> dict[str, Any]:
    _exact_keys(doc, _ATT_SOURCE_KEYS, path)
    state = _str_enum(doc["state"], TARGET_ATT_SOURCES, f"{path}.state")
    verbatim = _opt_str(doc["verbatim"], f"{path}.verbatim")
    anchor = _opt_str(doc["anchor"], f"{path}.anchor")
    if state == "ABSENT" and (verbatim is not None or anchor is not None):
        raise _schema(
            f"{path}: an ABSENT target attestation source carries no "
            "verbatim / anchor"
        )
    if state == "PUBLISHED_STATEMENT" and (
        verbatim is None or anchor is not None
    ):
        raise _schema(
            f"{path}: a PUBLISHED_STATEMENT target attestation source "
            "carries the verbatim statement and no review anchor"
        )
    if state == "REVIEWED_DETERMINATION" and (
        verbatim is None or anchor is None
    ):
        raise _schema(
            f"{path}: a REVIEWED_DETERMINATION target attestation source "
            "carries the recorded determination + its review anchor"
        )
    return {"state": state, "verbatim": verbatim, "anchor": anchor}


def _decode_case_structure(raw: dict[str, Any], *, index: int) -> dict[str, Any]:
    """Phase 1 — the pure structural decode (exact key sets, types,
    bounded vocabularies, the case-id grammar, the track/surface
    coherence, the label governance, the expected-block decode). Any
    violation is a corpus-integrity failure regardless of the labeled
    outcome (a structurally invalid document is never a sealed row)."""
    case_id = raw.get("case_id", f"<index {index}>")
    cpath = f"case {case_id}"
    _exact_keys(raw, _CASE_KEYS, cpath)
    case_id = _str(raw["case_id"], f"{cpath}.case_id")
    if not CASE_ID_PATTERN.match(case_id):
        raise _schema(
            f"{cpath}.case_id: must match {CASE_ID_PATTERN.pattern} "
            f"(the family case-id grammar), got {case_id!r}"
        )
    _str(raw["case_category"], f"{cpath}.case_category")
    _str_enum(raw["matrix_row"], MATRIX_ROWS, f"{cpath}.matrix_row")
    tags = raw["challenge_tags"]
    if (
        not isinstance(tags, list)
        or not all(t in CHALLENGE_TAGS for t in tags)
        or len(set(tags)) != len(tags)
        or tags != sorted(tags)
    ):
        raise _schema(
            f"{cpath}.challenge_tags: must be a sorted unique list of "
            f"bounded tags {sorted(CHALLENGE_TAGS)}"
        )
    kind = _str_enum(raw["evidence_kind"], EVIDENCE_KINDS, f"{cpath}.evidence_kind")
    track = _str_enum(raw["track"], TRACKS, f"{cpath}.track")
    surface_raw = raw["surface"]
    if track == "B":
        if surface_raw is not None:
            raise _schema(
                f"{cpath}.surface: a track B case carries no Track A "
                f"surface (expected null), got {surface_raw!r}"
            )
        surface: str | None = None
    else:
        surface = _str_enum(surface_raw, SURFACES, f"{cpath}.surface")

    # -- the sealed source blocks (the original published content) --
    source_doc = raw["source"]
    spath = f"{cpath}.source"
    _exact_keys(source_doc, _SOURCE_KEYS, spath)
    candidate_block = _decode_source_block(
        source_doc["candidate"], path=f"{spath}.candidate", kind=kind
    )
    target_block = _decode_source_block(
        source_doc["target"], path=f"{spath}.target", kind=kind
    )

    # -- recorded_case: the V2 input document (+ the sealed payload on
    #    the record surface) --
    recorded_doc = raw["recorded_case"]
    rpath = f"{cpath}.recorded_case"
    if surface in ("RECORD", "BOTH"):
        _exact_keys(recorded_doc, _RECORDS_KEYS_RECORD_SURFACE, rpath)
    else:
        _exact_keys(recorded_doc, _RECORDS_KEYS_BASE, rpath)
        if "payload_document" in recorded_doc:
            raise _schema(
                f"{rpath}.payload_document: a derivation-surface case "
                "carries no sealed record payload"
            )
    payload_doc = (
        recorded_doc["payload_document"] if "payload_document" in recorded_doc else None
    )
    if payload_doc is not None:
        if not isinstance(payload_doc, dict):
            raise _schema(f"{rpath}.payload_document: expected an object")
        _json_native(payload_doc, f"{rpath}.payload_document")

    # -- derivation_inputs --
    di_doc = raw["derivation_inputs"]
    dipath = f"{cpath}.derivation_inputs"
    _exact_keys(di_doc, _DERIVATION_INPUT_KEYS, dipath)
    basis = _str_enum(di_doc["candidate_basis"], CANDIDATE_BASIS_VALUES, f"{dipath}.candidate_basis")
    ext_doc = di_doc["extraction_evidence"]
    if ext_doc is not None:
        epath = f"{dipath}.extraction_evidence"
        _exact_keys(ext_doc, _EXTRACTION_EVIDENCE_KEYS, epath)
        input_document = ext_doc["input_document"]
        if input_document is not None:
            if not isinstance(input_document, dict):
                raise _schema(f"{epath}.input_document: expected an object")
            _json_native(input_document, f"{epath}.input_document")
    target_ev_doc = di_doc["target_evidence"]
    if not isinstance(target_ev_doc, dict):
        raise _schema(f"{dipath}.target_evidence: expected an object")
    _exact_keys(target_ev_doc, _TARGET_EVIDENCE_KEYS, f"{dipath}.target_evidence")
    _str_enum(
        target_ev_doc["schema"],
        TARGET_EVIDENCE_SCHEMA_VALUES,
        f"{dipath}.target_evidence.schema",
    )

    # -- published_quantity + the attestation-source blocks --
    published_quantity = _decode_published_quantity(
        raw["published_quantity"], path=f"{cpath}.published_quantity"
    )
    att_doc = raw["completeness_attestation_source"]
    apath = f"{cpath}.completeness_attestation_source"
    _exact_keys(att_doc, frozenset({"candidate", "target"}), apath)
    cand_att = _decode_att_source_candidate(
        att_doc["candidate"], path=f"{apath}.candidate"
    )
    tgt_att = _decode_att_source_target(att_doc["target"], path=f"{apath}.target")

    # -- expected + label --
    expected = _decode_expected(
        raw["expected"], case_id=case_id, track=track, surface=surface
    )
    _check_expected_coherence(expected, case_id=case_id)
    label = _decode_label(raw["label"], case_id=case_id)
    _sha256(raw["case_digest"], f"{cpath}.case_digest")

    return {
        "case_id": case_id,
        "track": track,
        "surface": surface,
        "evidence_kind": kind,
        "challenge_tags": tuple(tags),
        "candidate_source_block": candidate_block,
        "target_source_block": target_block,
        "recorded_case_doc": recorded_doc["v2_case_document"],
        "payload_doc": payload_doc,
        "derivation_inputs_doc": di_doc,
        "candidate_basis": basis,
        "published_quantity": published_quantity,
        "candidate_att_source": cand_att,
        "target_att_source": tgt_att,
        "expected": expected,
        "label": label,
        "case_digest": raw["case_digest"],
        "document": raw,
    }


def _typed_decode(
    structured: dict[str, Any],
    *,
    case_id: str,
    outcome: str,
    observations: list[_Observation],
) -> FamilyCaseEvidence | None:
    """Phases 2-3 — decode every evidence document through the REAL
    frozen constructors (the constructor is the validator) and run the
    family coherence checks. For a sound (DERIVED) case any observation
    is a corpus-integrity failure, raised immediately. For a sealed-raw
    defect case the observations are collected for the stage-coherence
    rule (the module docstring)."""
    dipath = f"case {case_id}: derivation_inputs"
    strict = outcome == "DERIVED"

    def _fail(exc: BundleAuthorityCorpusError) -> None:
        if strict:
            raise exc
        # sealed-raw: a typed-decode failure is an observation at the
        # frozen-constructor / codec layer (the named check is in the
        # reason; the scoping rule reads the layer).
        check = exc.reason.split(":")[0]
        layer = L_CODEC if "codec" in str(exc).lower() or "payload" in check.lower() else L_CONSTRUCTOR
        observations.append(_Observation(check, layer, exc.reason))

    # -- the recorded V2 case document --
    try:
        v2_case = decode_v2_case_document(
            structured["recorded_case_doc"],
            path=f"case {case_id}: recorded_case.v2_case_document",
        )
    except BundleAuthorityCorpusError as exc:
        _fail(exc)
        v2_case = None

    # -- the channel --
    try:
        channel = decode_channel_document(
            structured["derivation_inputs_doc"]["channel"],
            path=f"{dipath}.channel",
        )
    except BundleAuthorityCorpusError as exc:
        _fail(exc)
        channel = None

    # -- the candidate composition record --
    cand_doc = structured["derivation_inputs_doc"]["candidate_composition"]
    candidate_composition = None
    if cand_doc is not None:
        try:
            candidate_composition = _decode_candidate_composition(
                cand_doc, path=f"{dipath}.candidate_composition"
            )
        except BundleAuthorityCorpusError as exc:
            _fail(exc)
            candidate_composition = None

    # -- the extraction evidence --
    ext_doc = structured["derivation_inputs_doc"]["extraction_evidence"]
    extraction_result = None
    extraction_input_document = None
    if ext_doc is not None:
        extraction_input_document = ext_doc["input_document"]
        result_doc = ext_doc["result_document"]
        if result_doc is not None:
            try:
                extraction_result = _decode_extraction_result(
                    result_doc, path=f"{dipath}.extraction_evidence.result_document"
                )
            except BundleAuthorityCorpusError as exc:
                _fail(exc)
                extraction_result = None

    # -- the target evidence --
    target_ev_doc = structured["derivation_inputs_doc"]["target_evidence"]
    target_evidence = None
    if target_ev_doc["schema"] != "absent":
        if target_ev_doc["document"] is None:
            obs = _Observation(
                "CONSTRUCTOR_TARGET_EVIDENCE",
                L_CONSTRUCTOR,
                f"{dipath}.target_evidence: schema {target_ev_doc['schema']!r} "
                "requires the sealed record document (document null)",
            )
            if strict:
                raise _evidence(obs.detail)
            observations.append(obs)
        else:
            try:
                if target_ev_doc["schema"] == "fu4_v3":
                    target_evidence = _decode_target_fu4(
                        target_ev_doc["document"],
                        path=f"{dipath}.target_evidence.document",
                    )
                else:
                    target_evidence = _decode_target_fu3(
                        target_ev_doc["document"],
                        path=f"{dipath}.target_evidence.document",
                    )
            except BundleAuthorityCorpusError as exc:
                _fail(exc)
                target_evidence = None

    # -- the quantity attestation --
    qty_doc = structured["derivation_inputs_doc"]["quantity_attestation"]
    quantity_attestation = None
    if qty_doc is not None:
        try:
            quantity_attestation = _decode_quantity_attestation(
                qty_doc, path=f"{dipath}.quantity_attestation"
            )
        except BundleAuthorityCorpusError as exc:
            _fail(exc)
            quantity_attestation = None

    # -- the scripted context documents --
    scpath = f"case {case_id}: scripted_context"
    sc_doc = structured["document"]["scripted_context"]
    identity_assessment = None
    evaluation = None
    context_provenances: frozenset[ContextProvenance] = frozenset()
    product_evidence: ProductEvidenceProfileV2 | None = None
    try:
        identity_assessment, evaluation, context_provenances, product_evidence = (
            _decode_scripted_context(sc_doc, path=scpath)
        )
    except BundleAuthorityCorpusError as exc:
        _fail(exc)

    # -- the sealed record payload (the real universal codec — the
    #    codec reads the payload's own declared envelope version; a
    #    foreign / forged framing is refused by the codec itself) --
    payload_record = None
    if structured["payload_doc"] is not None:
        declared_envelope = structured["payload_doc"].get("schema_version")
        try:
            payload_record = decode_semantic_decision_record(
                structured["payload_doc"],
                schema_version=declared_envelope,
            )
        except Exception as exc:  # the codec's bounded error + framing
            obs = _Observation(
                "CODEC_PAYLOAD",
                L_CODEC,
                f"case {case_id}: recorded_case.payload_document: the "
                f"frozen universal codec refused the sealed payload "
                f"({type(exc).__name__}: {exc})",
            )
            if strict:
                raise _evidence(obs.detail)
            observations.append(obs)
            payload_record = None

    if strict:
        # A sound case must have decoded every document (any None is a
        # collected observation — raise it).
        for obs in observations:
            raise _evidence(obs.detail)

    # -- family coherence checks (cross-document) --
    _run_family_checks(
        structured,
        case_id=case_id,
        v2_case=v2_case,
        channel=channel,
        candidate_composition=candidate_composition,
        extraction_result=extraction_result,
        extraction_input_document=extraction_input_document,
        target_evidence=target_evidence,
        quantity_attestation=quantity_attestation,
        identity_assessment=identity_assessment,
        evaluation=evaluation,
        context_provenances=context_provenances,
        product_evidence=product_evidence,
        payload_record=payload_record,
        strict=strict,
        observations=observations,
    )

    if strict and observations:
        raise _evidence(observations[0].detail)

    return FamilyCaseEvidence(
        v2_case=v2_case,
        channel=channel,
        candidate_composition=candidate_composition,
        extraction_result=extraction_result,
        target_evidence=target_evidence,
        quantity_attestation=quantity_attestation,
        identity_assessment=identity_assessment,
        evaluation=evaluation,
        context_provenances=context_provenances,
        product_evidence=product_evidence,
        payload_record=payload_record,
    )


def _run_family_checks(
    structured: dict[str, Any],
    *,
    case_id: str,
    v2_case: SemanticMatchCaseV2 | None,
    channel: CandidateSalesUnitEvidenceV2 | None,
    candidate_composition: CandidateBundleCompositionEvidenceV2FU4 | None,
    extraction_result: SalesUnitExtractionResult | None,
    extraction_input_document: dict[str, Any] | None,
    target_evidence: (
        TargetSalesUnitEvidenceV2FU4 | TargetSalesUnitEvidenceV2 | None
    ),
    quantity_attestation: QuantityCompletenessAttestationV2FU4 | None,
    identity_assessment: IdentityStateAssessmentV2 | None,
    evaluation: SemanticEvaluationV2 | None,
    context_provenances: frozenset[ContextProvenance],
    product_evidence: ProductEvidenceProfileV2 | None,
    payload_record: object | None,
    strict: bool,
    observations: list[_Observation],
) -> None:
    """The family cross-document checks (the case-document-integrity
    layer + the corroborative gate layer). Each fired check is one
    deterministic observation; the layer tags feed the sealed-raw
    stage-coherence rule."""
    dipath = f"case {case_id}: derivation_inputs"

    def _obs(check: str, layer: str, detail: str) -> None:
        observation = _Observation(check, layer, detail)
        if strict:
            raise _evidence(detail)
        observations.append(observation)

    candidate_block = structured["candidate_source_block"]
    target_block = structured["target_source_block"]
    basis = structured["candidate_basis"]
    published_quantity = structured["published_quantity"]

    # CASEDOC_CHANNEL_EQUALITY (design section 4.4: "the loader
    # enforces channel == recorded_case's channel"; D6-ii): the
    # derivation channel is the recorded case's channel.
    if v2_case is not None and channel is not None:
        if channel.canonical() != v2_case.candidate_commercial.sales_unit.canonical():
            _obs(
                "CASEDOC_CHANNEL_EQUALITY",
                L_CASE_DOCUMENT,
                f"{dipath}.channel: the derivation channel is not the "
                "recorded case's channel (corpus-internal inconsistency "
                "- the D6-ii shape)",
            )

    # CASEDOC_BASIS_COHERENCE: the recorded basis matches the documents
    # it claims (a NONE basis carries no candidate evidence; an
    # EXTRACTION basis carries the extraction evidence + the matching
    # embedded original; a RECORDED_CHANNEL basis carries the record
    # alone). The presence variants mirror the constructor's own basis /
    # embedded-original requirements (the loader observes them earlier -
    # the CASE_DOCUMENT_MIRROR layer).
    if candidate_composition is not None and basis == "NONE":
        _obs(
            "CASEDOC_BASIS_COHERENCE",
            L_CASE_DOCUMENT_MIRROR,
            f"{dipath}.candidate_basis: NONE carries no candidate "
            "composition record, got one",
        )
    if basis == "EXTRACTION_RESULT_V1":
        if candidate_composition is None or extraction_result is None:
            _obs(
                "CASEDOC_BASIS_COHERENCE",
                L_CASE_DOCUMENT_MIRROR,
                f"{dipath}.candidate_basis: EXTRACTION_RESULT_V1 "
                "requires the candidate composition record + the "
                "recorded extraction evidence (both present)",
            )
        elif candidate_composition is not None and extraction_result is not None:
            if (
                candidate_composition.extraction_result is None
                or candidate_composition.extraction_result.canonical()
                != extraction_result.canonical()
            ):
                _obs(
                    "CASEDOC_EMBEDDED_RESULT_EQUALITY",
                    L_CASE_DOCUMENT,
                    f"{dipath}: the record's embedded original extraction "
                    "result is not the case's recorded extraction "
                    "evidence (the association anchor - the D4 / D5 "
                    "shape)",
                )
    if basis == "RECORDED_CHANNEL" and extraction_result is not None:
        _obs(
            "CASEDOC_BASIS_COHERENCE",
            L_CASE_DOCUMENT_MIRROR,
            f"{dipath}.candidate_basis: RECORDED_CHANNEL carries no "
            "extraction evidence (the record is built from the recorded "
            "channel alone)",
        )
    if basis == "NONE" and extraction_result is not None:
        _obs(
            "CASEDOC_BASIS_COHERENCE",
            L_CASE_DOCUMENT_MIRROR,
            f"{dipath}.candidate_basis: NONE carries no extraction "
            "evidence",
        )
    if candidate_composition is not None and basis in (
        "EXTRACTION_RESULT_V1",
        "RECORDED_CHANNEL",
    ):
        if (
            candidate_composition.basis is not None
            and candidate_composition.basis.value != basis
        ):
            _obs(
                "CASEDOC_BASIS_COHERENCE",
                L_CASE_DOCUMENT,
                f"{dipath}.candidate_basis: the record's basis "
                f"({candidate_composition.basis.value!r}) disagrees with "
                f"the case's candidate_basis ({basis!r})",
            )

    # GATE_CHANNEL_CONTENT_BINDING (the presentation gate's own step 0,
    # observed earlier by the loader - the D3-i cross-listing shape):
    # the record binds the EXACT presented channel content.
    if candidate_composition is not None and channel is not None:
        if (
            canonical_sha256(channel.canonical())
            != candidate_composition.channel_content_digest
        ):
            _obs(
                "GATE_CHANNEL_CONTENT_BINDING",
                L_GATE,
                f"{dipath}.candidate_composition: the record's "
                "channel_content_digest does not bind the case's "
                "presented channel (cross-listing substitution - the "
                "D3-i shape)",
            )

    # GATE_FROZEN_MAPPING (the presentation gate's step 3, observed
    # earlier - the D5-i wrong-result forgery): the frozen P2 mapping
    # of the embedded original equals the presented channel.
    if (
        candidate_composition is not None
        and candidate_composition.extraction_result is not None
        and channel is not None
    ):
        try:
            mapped = sales_unit_channel_from_extraction(
                candidate_composition.extraction_result
            )
        except (
            SalesUnitExtractionIntegrityError,
            BundleCompositionEvidenceIntegrityError,
            ValueError,
            TypeError,
        ) as exc:
            _obs(
                "GATE_FROZEN_MAPPING",
                L_GATE,
                f"{dipath}.candidate_composition: the frozen P2 mapping "
                f"refused the embedded original result ({exc})",
            )
        else:
            if mapped.canonical() != channel.canonical():
                _obs(
                    "GATE_FROZEN_MAPPING",
                    L_GATE,
                    f"{dipath}.candidate_composition: the frozen P2 "
                    "mapping of the embedded original result is not the "
                    "presented channel (the wrong-result forgery - the "
                    "D5-i shape)",
                )

    # SOURCE_EXTRACTION_INPUT_DIGEST (D6-i): the recorded examined
    # input is the input the embedded result binds (the construction-
    # level binding, mirrored at corpus level).
    if extraction_result is not None and extraction_input_document is not None:
        if canonical_sha256(extraction_input_document) != extraction_result.input_digest:
            _obs(
                "SOURCE_EXTRACTION_INPUT_DIGEST",
                L_CONSTRUCTOR,
                f"{dipath}.extraction_evidence.input_document: the "
                "recorded examined input is not the input the embedded "
                "result's input_digest binds (the examined input was "
                "altered after extraction - the D6-i shape)",
            )

    # SOURCE_CUE_GROUNDING: every cue's recorded field text is the
    # text the sealed candidate source block published (a cue cannot
    # claim text its side never published - the cross-listing /
    # fabricated-field shape).
    if extraction_result is not None:
        for i, cue in enumerate(extraction_result.cues):
            if cue.field is SalesUnitCueField.PRODUCT_TITLE:
                if (
                    candidate_block["title_text"] is None
                    or cue.raw_field_value != candidate_block["title_text"]
                ):
                    _obs(
                        "SOURCE_CUE_GROUNDING",
                        L_GATE,
                        f"{dipath}.extraction_evidence.result_document."
                        f"cues[{i}]: the PRODUCT_TITLE cue's recorded "
                        "field text is not the sealed candidate title "
                        "(missing source provenance / cross-listing)",
                    )
            else:  # STRUCTURED_PACKAGING_FIELD
                if cue.raw_field_value not in candidate_block["structured_fields"].values():
                    _obs(
                        "SOURCE_CUE_GROUNDING",
                        L_GATE,
                        f"{dipath}.extraction_evidence.result_document."
                        f"cues[{i}]: the STRUCTURED_PACKAGING_FIELD cue's "
                        "recorded field text is not a sealed candidate "
                        "structured field value (missing source "
                        "provenance / cross-listing)",
                    )

    # SOURCE_CLAUSE_GROUNDING: every sealed verbatim clause the
    # candidate / target records claim is grounded in THAT side's
    # sealed source block (the I-3 provenance firewall at corpus level
    # - a candidate clause the candidate never published, or a target
    # clause the target never published, is a side-association /
    # substitution failure).
    if candidate_composition is not None:
        for i, clause in enumerate(
            (
                [candidate_composition.composition_clause]
                if candidate_composition.composition_clause is not None
                else []
            )
            + list(candidate_composition.additional_clauses)
        ):
            if not _span_grounded(clause, candidate_block):
                _obs(
                    "SOURCE_CLAUSE_GROUNDING",
                    L_GATE,
                    f"{dipath}.candidate_composition: clause "
                    f"{clause!r} is not span-grounded in the sealed "
                    "CANDIDATE source block (evidence-side association "
                    "- the candidate evidence must be published on the "
                    "candidate side)",
                )
    if (
        isinstance(target_evidence, TargetSalesUnitEvidenceV2FU4)
        and target_evidence.composition_clause is not None
    ):
        if not _span_grounded(target_evidence.composition_clause, target_block):
            _obs(
                "SOURCE_CLAUSE_GROUNDING",
                L_GATE,
                f"{dipath}.target_evidence: clause "
                f"{target_evidence.composition_clause!r} is not "
                "span-grounded in the sealed TARGET source block "
                "(evidence-side association - the target evidence must "
                "be published on the target side)",
            )

    # SOURCE_ATTESTATION_GROUNDING: a PUBLISHED-basis attestation's
    # verbatim statement is a published statement of the subject side
    # (span-grounded in that side's sealed source). A REVIEWED-basis
    # determination is review-constructed (no span requirement - the
    # review's recorded text).
    if candidate_composition is not None and (
        candidate_composition.completeness_attestation is not None
    ):
        att = candidate_composition.completeness_attestation
        if att.basis is CompletenessBasisV2FU4.PUBLISHED_COMPLETENESS_STATEMENT:
            if not _span_grounded(att.attestation_text, candidate_block):
                _obs(
                    "SOURCE_ATTESTATION_GROUNDING",
                    L_GATE,
                    f"{dipath}.candidate_composition: the published "
                    "completeness statement "
                    f"{att.attestation_text!r} is not span-grounded in "
                    "the sealed candidate source block (a model claim "
                    "disguised as publisher evidence is refused here)",
                )
    if (
        isinstance(target_evidence, TargetSalesUnitEvidenceV2FU4)
        and target_evidence.completeness_attestation is not None
    ):
        att = target_evidence.completeness_attestation
        if att.basis is CompletenessBasisV2FU4.PUBLISHED_COMPLETENESS_STATEMENT:
            if not _span_grounded(att.attestation_text, target_block):
                _obs(
                    "SOURCE_ATTESTATION_GROUNDING",
                    L_GATE,
                    f"{dipath}.target_evidence: the published "
                    "completeness statement "
                    f"{att.attestation_text!r} is not span-grounded in "
                    "the sealed target source block (a model claim "
                    "disguised as publisher evidence is refused here)",
                )

    # CASEDOC_ATTESTATION_SOURCE_BLOCK: the case's recorded
    # attestation-source blocks agree with the records' embedded
    # attestations (the side association of the label context - the
    # PUBLISHED_STATEMENT / REVIEWED_DETERMINATION / ABSENT states).
    # A sealed-raw case whose record document the constructors refused
    # is not cross-checked here (the constructor observation carries
    # the defect; the block's claim about the rejected document's
    # embedded attestation is not observable at the loader).
    cand_att = structured["candidate_att_source"]
    cand_doc_present = (
        structured["derivation_inputs_doc"]["candidate_composition"] is not None
    )
    if candidate_composition is not None:
        embedded = candidate_composition.completeness_attestation
        if embedded is not None:
            if cand_att["state"] != "PUBLISHED_STATEMENT":
                _obs(
                    "CASEDOC_ATTESTATION_SOURCE_BLOCK",
                    L_CASE_DOCUMENT,
                    f"case {case_id}: completeness_attestation_source."
                    "candidate: the candidate record carries its "
                    "published completeness attestation; the case block "
                    f"must state PUBLISHED_STATEMENT, got {cand_att['state']!r}",
                )
            elif cand_att["verbatim"] != embedded.attestation_text:
                _obs(
                    "CASEDOC_ATTESTATION_SOURCE_BLOCK",
                    L_CASE_DOCUMENT,
                    f"case {case_id}: completeness_attestation_source."
                    "candidate.verbatim: the recorded statement is not "
                    "the candidate record's attestation text",
                )
        else:
            if cand_att["state"] != "ABSENT":
                _obs(
                    "CASEDOC_ATTESTATION_SOURCE_BLOCK",
                    L_CASE_DOCUMENT,
                    f"case {case_id}: completeness_attestation_source."
                    "candidate: the candidate record carries no "
                    "completeness attestation; the case block must "
                    f"state ABSENT, got {cand_att['state']!r}",
                )
    elif cand_doc_present:
        pass  # sealed raw: the record document was constructor-refused
    else:
        if cand_att["state"] != "ABSENT":
            _obs(
                "CASEDOC_ATTESTATION_SOURCE_BLOCK",
                L_CASE_DOCUMENT,
                f"case {case_id}: completeness_attestation_source.candidate: "
                "no candidate composition record exists; the case block "
                f"must state ABSENT, got {cand_att['state']!r}",
            )
    tgt_att = structured["target_att_source"]
    tgt_doc_present = (
        structured["derivation_inputs_doc"]["target_evidence"]["schema"] != "absent"
    )
    if isinstance(target_evidence, TargetSalesUnitEvidenceV2FU4):
        embedded = target_evidence.completeness_attestation
        if embedded is not None:
            expected_state = (
                "PUBLISHED_STATEMENT"
                if embedded.basis
                is CompletenessBasisV2FU4.PUBLISHED_COMPLETENESS_STATEMENT
                else "REVIEWED_DETERMINATION"
            )
            if tgt_att["state"] != expected_state:
                _obs(
                    "CASEDOC_ATTESTATION_SOURCE_BLOCK",
                    L_CASE_DOCUMENT,
                    f"case {case_id}: completeness_attestation_source."
                    f"target: the target record's attestation basis "
                    f"requires {expected_state!r}, got {tgt_att['state']!r}",
                )
            elif tgt_att["verbatim"] != embedded.attestation_text:
                _obs(
                    "CASEDOC_ATTESTATION_SOURCE_BLOCK",
                    L_CASE_DOCUMENT,
                    f"case {case_id}: completeness_attestation_source."
                    "target.verbatim: the recorded determination is not "
                    "the target record's attestation text",
                )
        else:
            if tgt_att["state"] != "ABSENT":
                _obs(
                    "CASEDOC_ATTESTATION_SOURCE_BLOCK",
                    L_CASE_DOCUMENT,
                    f"case {case_id}: completeness_attestation_source."
                    "target: the target record carries no completeness "
                    f"attestation; the case block must state ABSENT, "
                    f"got {tgt_att['state']!r}",
                )
    elif isinstance(target_evidence, TargetSalesUnitEvidenceV2):
        # A frozen FU3 target record: the D18 composition-ABSENT
        # reading - no composition attestation can stand on it.
        if tgt_att["state"] != "ABSENT":
            _obs(
                "CASEDOC_ATTESTATION_SOURCE_BLOCK",
                L_CASE_DOCUMENT,
                f"case {case_id}: completeness_attestation_source.target: "
                "the frozen FU3 target record is read as "
                "composition-ABSENT; the case block must state ABSENT, "
                f"got {tgt_att['state']!r}",
            )
    elif tgt_doc_present:
        pass  # sealed raw: the fu4_v3 document was constructor-refused
    else:
        if tgt_att["state"] != "ABSENT":
            _obs(
                "CASEDOC_ATTESTATION_SOURCE_BLOCK",
                L_CASE_DOCUMENT,
                f"case {case_id}: completeness_attestation_source.target: "
                "no FU4 target record with a composition attestation "
                f"exists; the case block must state ABSENT, got "
                f"{tgt_att['state']!r}",
            )

    # CASEDOC_PUBLISHED_QUANTITY: the case's recorded published
    # quantities agree with the records that carry them (the quantity
    # evidence coherence - the channel's published count, the target
    # record's quantity).
    if channel is not None and published_quantity["candidate"] != channel.quantity:
        _obs(
            "CASEDOC_PUBLISHED_QUANTITY",
            L_CASE_DOCUMENT,
            f"case {case_id}: published_quantity.candidate "
            f"({published_quantity['candidate']!r}) is not the channel's "
            f"published quantity ({channel.quantity!r})",
        )
    if target_evidence is not None and published_quantity["target"] != target_evidence.quantity:
        _obs(
            "CASEDOC_PUBLISHED_QUANTITY",
            L_CASE_DOCUMENT,
            f"case {case_id}: published_quantity.target "
            f"({published_quantity['target']!r}) is not the target "
            f"record's quantity ({target_evidence.quantity!r})",
        )

    # CASEDOC_QUANTITY_AXIS: the quantity attestation's derivation-input
    # validation (design D15 / the frozen derivation's admissibility
    # rule, mirrored at corpus level): the attestation stands on the
    # asymmetric published axis, subject = the actually-missing side.
    if quantity_attestation is not None:
        cand_q = published_quantity["candidate"]
        tgt_q = published_quantity["target"]
        missing_side = (
            EvidenceSideV2FU4.CANDIDATE if cand_q is None else None
        ) or (EvidenceSideV2FU4.TARGET if tgt_q is None else None)
        if missing_side is None:
            _obs(
                "CASEDOC_QUANTITY_AXIS",
                L_CONSTRUCTOR,
                f"case {case_id}: the quantity attestation is presented "
                "over a non-asymmetric published quantity axis (both "
                "sides publish or both are silent - the contract-misuse "
                "shape, the D15-ii refusal)",
            )
        elif quantity_attestation.subject_side is not missing_side:
            _obs(
                "CASEDOC_QUANTITY_AXIS",
                L_CONSTRUCTOR,
                f"case {case_id}: the quantity attestation's subject "
                f"side ({quantity_attestation.subject_side.value!r}) is "
                f"not the actually-missing side ({missing_side.value!r}) "
                "(the D15-i integrity error)",
            )

    # CASEDOC_CONTEXT_CASE_EQUALITY: the scripted context is the
    # recorded case's own identity side (the tier axis derives over
    # exactly this context + this case's channel).
    if v2_case is not None:
        if identity_assessment is not None:
            if (
                identity_assessment.state is not v2_case.identity_state
                or identity_assessment.substate is not v2_case.substate
                or identity_assessment.relationship_signals
                != v2_case.relationship_signals
                or identity_assessment.normalized_requested_part_number
                != v2_case.normalized_requested_part_number
                or identity_assessment.normalized_candidate_part_number
                != v2_case.normalized_candidate_part_number
            ):
                _obs(
                    "CASEDOC_CONTEXT_CASE_EQUALITY",
                    L_CASE_DOCUMENT,
                    f"case {case_id}: scripted_context.identity_assessment "
                    "disagrees with the recorded case's deterministic "
                    "identity context",
                )
        if (
            frozenset(context_provenances) != v2_case.context_provenances
        ):
            _obs(
                "CASEDOC_CONTEXT_CASE_EQUALITY",
                L_CASE_DOCUMENT,
                f"case {case_id}: scripted_context.context_provenances "
                "disagrees with the recorded case's context provenances",
            )
        if product_evidence is not None and (
            _product_profile_document(product_evidence)
            != _product_profile_document(v2_case.product_evidence)
        ):
            _obs(
                "CASEDOC_CONTEXT_CASE_EQUALITY",
                L_CASE_DOCUMENT,
                f"case {case_id}: scripted_context.product_evidence "
                "disagrees with the recorded case's product-evidence "
                "profile",
            )

    # CASEDOC_PAYLOAD_CASE_EQUALITY / _EVALUATION_EQUALITY: a sealed
    # record payload that decodes is the record of THIS case under THIS
    # scripted evaluation (a record over another case / another
    # evaluation is a corpus-internal inconsistency - the D3-iii shape
    # keeps the same case, swaps the authority section only).
    if payload_record is not None:
        if v2_case is not None and (
            payload_record.case is None
            or payload_record.case.canonical()
            != structured["recorded_case_doc"]
        ):
            _obs(
                "CASEDOC_PAYLOAD_CASE_EQUALITY",
                L_CASE_DOCUMENT,
                f"case {case_id}: the sealed payload's case section is "
                "not the recorded case document (the record is over "
                "another case)",
            )
        if evaluation is not None:
            record_projection = {
                "evaluation_state": payload_record.evaluation_state.value,
                "decision": (
                    payload_record.decision.value
                    if payload_record.decision is not None
                    else None
                ),
                "confidence": (
                    payload_record.confidence.value
                    if payload_record.confidence is not None
                    else None
                ),
                "conflict_classes": sorted(
                    c.value for c in payload_record.conflict_classes
                ),
            }
            if record_projection != structured["document"]["scripted_context"]["evaluation"]:
                _obs(
                    "CASEDOC_PAYLOAD_EVALUATION_EQUALITY",
                    L_CASE_DOCUMENT,
                    f"case {case_id}: the sealed payload's evaluation "
                    "section is not the case's scripted evaluation",
                )
    return None


def _product_profile_document(profile: ProductEvidenceProfileV2) -> dict[str, Any]:
    return {
        "has_usable_product_title": profile.has_usable_product_title,
        "matched_facts": sorted(
            (
                {
                    "dimension": fact.dimension.value,
                    "sources": sorted(s.value for s in fact.sources),
                }
                for fact in profile.matched_facts
            ),
            key=lambda fact: (fact["dimension"], fact["sources"]),
        ),
    }


def _apply_sealed_raw_scoping(
    structured: dict[str, Any], observations: list[_Observation]
) -> None:
    """The stage-coherence rule of the module docstring, applied to a
    sealed-raw defect case (outcome REFUSED / NON_CONSTRUCTIBLE)."""
    case_id = structured["case_id"]
    surface = structured["surface"]
    refusal = structured["expected"]["refusal"]
    stage = refusal["stage"]
    layers = {obs.layer for obs in observations}
    constructor_layer = layers & {L_CONSTRUCTOR, L_CODEC}
    case_document_layers = layers & {L_CASE_DOCUMENT, L_CASE_DOCUMENT_MIRROR}

    if stage == "CORPUS_INTEGRITY":
        if not case_document_layers:
            raise _label(
                f"case {case_id}: the labeled CORPUS_INTEGRITY defect is "
                "not present - no case-document-integrity check fired "
                "over the sealed documents (an incoherent label is a "
                "corpus-integrity failure, never a test failure)"
            )
    elif stage == "CONSTRUCTION":
        if not (constructor_layer | (layers & {L_CASE_DOCUMENT_MIRROR})):
            raise _label(
                f"case {case_id}: the labeled CONSTRUCTION defect is not "
                "observable - no frozen constructor / codec / "
                "construction-level coherence check fired over the "
                "sealed documents (the defect would be caught at no "
                "construction layer; incoherent label)"
            )
        if layers & {L_CASE_DOCUMENT}:
            raise _label(
                f"case {case_id}: a case-document-integrity observation "
                "fired - the defect is observed at the family loader "
                "(CORPUS_INTEGRITY), not at CONSTRUCTION (incoherent "
                "label)"
            )
    elif stage == "CODEC_DECODE":
        if surface not in ("RECORD", "BOTH"):
            raise _label(
                f"case {case_id}: the CODEC_DECODE stage requires the "
                f"record surface, got {surface!r}"
            )
        if L_CODEC not in layers:
            raise _label(
                f"case {case_id}: the labeled CODEC_DECODE defect is not "
                "observable - the frozen universal codec accepted the "
                "sealed payload (incoherent label)"
            )
        if layers & {L_CASE_DOCUMENT}:
            raise _label(
                f"case {case_id}: a case-document-integrity observation "
                "fired - the defect is observed at the family loader "
                "(CORPUS_INTEGRITY), not at CODEC_DECODE (incoherent "
                "label)"
            )
    else:  # PRESENTATION_GATE / REPLAY_AGREEMENT
        if constructor_layer or case_document_layers:
            raised = ", ".join(
                sorted(f"{obs.check} ({obs.layer})" for obs in observations)
            )
            raise _label(
                f"case {case_id}: the labeled {stage} defect requires "
                "exactly the self-consistent sealed shapes (no "
                "constructor- / codec- / case-document-integrity "
                f"observation), but fired: {raised} (incoherent label)"
            )
    return None


def decode_corpus_case_document(raw: dict[str, Any], *, index: int = 0) -> FamilyCorpusCase:
    """The public strict decoder for one family case document (the
    exact key set + every check + the per-case digest). Raises a
    bounded ``BundleAuthorityCorpusError`` with the deterministic,
    explicit failure reason on any violation."""
    structured = _decode_case_structure(raw, index=index)
    case_id = structured["case_id"]
    outcome = structured["expected"]["outcome"]
    observations: list[_Observation] = []
    evidence = _typed_decode(
        structured, case_id=case_id, outcome=outcome, observations=observations
    )
    if outcome != "DERIVED":
        _apply_sealed_raw_scoping(structured, observations)
    # The per-case digest (the family rule: SHA-256 over the case
    # document minus ``case_digest``).
    state_view = {
        k: v for k, v in structured["document"].items() if k != "case_digest"
    }
    if canonical_sha256(state_view) != structured["case_digest"]:
        raise _digest(
            f"case {case_id}: case_digest does not verify (the case was "
            "mutated after sealing)"
        )
    return FamilyCorpusCase(
        case_id=case_id,
        track=structured["track"],
        surface=structured["surface"],
        evidence_kind=structured["evidence_kind"],
        matrix_row=structured["document"]["matrix_row"],
        document=structured["document"],
        evidence=evidence,
        expected=structured["expected"],
        label=structured["label"],
        case_digest=structured["case_digest"],
    )


# ---------------------------------------------------------------------------
# Corpus-level strict verification (design sections 4.1 / 4.2 / 4.5)
# ---------------------------------------------------------------------------

_CORPUS_KEYS = frozenset(
    {
        "corpus_id",
        "corpus_schema_version",
        "corpus_version",
        "corpus_label",
        "created_utc",
        "semantic_contract_binding",
        "cases",
        "label_revisions",
        "corpus_digest",
    }
)
_LABEL_REVISION_KEYS = frozenset(
    {
        "revision",
        "case_id",
        "utc",
        "reason_class",
        "statement",
        "digest_before",
        "digest_after",
    }
)
_REASON_CLASSES = frozenset({"A", "B", "C", "D"})


@dataclass(frozen=True)
class FamilyCorpusBundle:
    """The verified family corpus: document + decoded cases + identity."""

    document: dict[str, Any]
    cases: tuple[FamilyCorpusCase, ...]
    corpus_id: str
    corpus_version: str
    corpus_digest: str
    semantic_contract_binding: tuple[str, str, int, int, str]
    created_utc: str


def corpus_state_digest(document: dict[str, Any]) -> str:
    """The family corpus digest: SHA-256 over the canonical corpus state
    view — the full document minus ``corpus_digest`` (all per-case
    digests + version + binding + id + schema + created + label
    revisions; design section 4.2). The case list order is covered:
    reordering the cases without re-sealing changes the digest."""
    _json_native(document, "corpus document")
    return canonical_sha256(
        {k: v for k, v in document.items() if k != "corpus_digest"}
    )


def case_state_digest(case_document: dict[str, Any]) -> str:
    """The family per-case digest: SHA-256 over the case document minus
    ``case_digest`` (the semantic family's per-case rule, adopted)."""
    _json_native(case_document, "case document")
    return canonical_sha256(
        {k: v for k, v in case_document.items() if k != "case_digest"}
    )


def _check_label_revisions(revisions: Any, case_ids: set[str]) -> None:
    if not isinstance(revisions, list):
        raise _schema("corpus document: label_revisions must be a list")
    seen: set[int] = set()
    for i, revision in enumerate(revisions):
        rpath = f"corpus document: label_revisions[{i}]"
        _exact_keys(revision, _LABEL_REVISION_KEYS, rpath)
        number = _int(revision["revision"], f"{rpath}.revision", minimum=1)
        if number in seen:
            raise _schema(f"{rpath}.revision: not unique")
        seen.add(number)
        if revision["case_id"] not in case_ids:
            raise _schema(
                f"{rpath}.case_id: {revision['case_id']!r} is not a "
                "corpus case"
            )
        _utc_instant(revision["utc"], f"{rpath}.utc")
        _str_enum(
            revision["reason_class"], _REASON_CLASSES, f"{rpath}.reason_class"
        )
        _str(revision["statement"], f"{rpath}.statement")
        _sha256(revision["digest_before"], f"{rpath}.digest_before")
        _sha256(revision["digest_after"], f"{rpath}.digest_after")
    if seen != set(range(1, len(revisions) + 1)):
        raise _schema(
            "corpus document: label_revisions must be numbered 1..N "
            "without gaps"
        )


def verify_corpus_document(document: Any) -> FamilyCorpusBundle:
    """Strict-verify one family corpus document (in memory). Raises the
    bounded ``BundleAuthorityCorpusError`` family with the
    deterministic, explicit failure reason.

    The seal registry check (design section 4.2(a)): the corpus loads
    ONLY under the exact FU4 binding, at the version sealed under it —
    any other corpus id / version / binding / schema version fails
    closed (cross-version / cross-binding / cross-family refusal).
    """
    if not isinstance(document, dict):
        raise _schema(
            f"corpus document: expected an object, got {type(document).__name__}"
        )
    _exact_keys(document, _CORPUS_KEYS, "corpus document")

    # -- the family identity (exact, sealed) --
    if document["corpus_id"] != CORPUS_ID:
        raise _seal(
            f"corpus document: corpus_id {document['corpus_id']!r} is not "
            f"the family corpus {CORPUS_ID!r} (cross-family refusal)"
        )
    if document["corpus_schema_version"] != CORPUS_SCHEMA_VERSION:
        raise _schema(
            f"corpus document: unknown corpus schema version "
            f"{document['corpus_schema_version']!r}; only "
            f"{CORPUS_SCHEMA_VERSION} is supported (fail closed)"
        )
    if document["corpus_label"] != CORPUS_LABEL:
        raise _seal(
            f"corpus document: corpus_label "
            f"{document['corpus_label']!r} is not the family label "
            f"{CORPUS_LABEL!r}"
        )
    _utc_instant(document["created_utc"], "corpus document: created_utc")

    # -- the exact FU4 binding + the sealed version under it --
    binding_raw = document["semantic_contract_binding"]
    if (
        not isinstance(binding_raw, list)
        or len(binding_raw) != 5
        or not all(
            isinstance(item, (str, int)) and not isinstance(item, bool)
            for item in binding_raw
        )
    ):
        raise _seal(
            "corpus document: semantic_contract_binding must be the "
            "five-axis contract identity (list of 5)"
        )
    binding_key = tuple(binding_raw)
    if binding_key not in BINDING_AUTHORITY_CORPUS_VERSIONS:
        raise _seal(
            f"corpus document: semantic_contract_binding "
            f"{list(binding_raw)!r} is not the family seal binding "
            f"{list(FU4_BINDING)!r} (the family loads only under the "
            "exact registered FU4 binding - never a lookalike)"
        )
    sealed_version = BINDING_AUTHORITY_CORPUS_VERSIONS[binding_key]
    if document["corpus_version"] != sealed_version:
        raise _seal(
            f"corpus document: corpus version "
            f"{document['corpus_version']!r} is not the version sealed "
            f"under binding {list(binding_raw)!r} ({sealed_version!r}) - "
            "a corpus version is only interpretable under the binding "
            "it was sealed with (cross-version refusal)"
        )

    # -- the cases (strict per-case decode + id uniqueness) --
    raw_cases = document["cases"]
    if not isinstance(raw_cases, list):
        raise _schema("corpus document: cases must be a list")
    seen_ids: set[str] = set()
    cases: list[FamilyCorpusCase] = []
    for i, raw in enumerate(raw_cases):
        case = decode_corpus_case_document(raw, index=i)
        if case.case_id in seen_ids:
            raise _schema(
                f"duplicate case id {case.case_id!r}; case ids must be "
                "unique (fail closed)"
            )
        seen_ids.add(case.case_id)
        cases.append(case)

    _check_label_revisions(document["label_revisions"], seen_ids)

    # -- the corpus digest --
    if corpus_state_digest(document) != document["corpus_digest"]:
        raise _digest(
            "corpus document: corpus_digest does not verify (the corpus "
            "state was mutated after sealing - including any case "
            "reordering without re-sealing)"
        )

    return FamilyCorpusBundle(
        document=document,
        cases=tuple(cases),
        corpus_id=document["corpus_id"],
        corpus_version=document["corpus_version"],
        corpus_digest=document["corpus_digest"],
        semantic_contract_binding=binding_key,  # type: ignore[arg-type]
        created_utc=document["created_utc"],
    )


# ---------------------------------------------------------------------------
# The manifest (design section 4.5 - schema 1, statement + lineage)
# ---------------------------------------------------------------------------

_MANIFEST_KEYS = frozenset(
    {
        "manifest_schema_version",
        "corpus_id",
        "corpus_version",
        "semantic_contract_binding",
        "corpus_digest",
        "case_count",
        "cases",
        "statement",
        "lineage",
        "manifest_digest",
    }
)
_MANIFEST_CASE_KEYS = frozenset(
    {"case_id", "case_digest", "evidence_kind", "track", "matrix_row"}
)
_LINEAGE_KEYS = frozenset(
    {"derived_from_corpus_version", "derived_from_corpus_digest"}
)


def build_manifest_document(document: dict[str, Any]) -> dict[str, Any]:
    """The reproducible family manifest for one verified corpus document
    (the per-case projection keeps the manifest auditable without
    re-opening the corpus document - the semantic family's manifest
    convention; the ``statement`` / ``lineage`` additive keys of the R2
    seal)."""
    cases = [
        {
            "case_id": case["case_id"],
            "case_digest": case["case_digest"],
            "evidence_kind": case["evidence_kind"],
            "track": case["track"],
            "matrix_row": case["matrix_row"],
        }
        for case in document["cases"]
    ]
    state: dict[str, Any] = {
        "manifest_schema_version": MANIFEST_SCHEMA_VERSION,
        "corpus_id": document["corpus_id"],
        "corpus_version": document["corpus_version"],
        "semantic_contract_binding": list(
            document["semantic_contract_binding"]
        ),
        "corpus_digest": document["corpus_digest"],
        "case_count": len(cases),
        "cases": cases,
        "statement": FAMILY_STATEMENT,
        "lineage": dict(FIRST_VERSION_LINEAGE),
    }
    state["manifest_digest"] = canonical_sha256(state)
    return state


def verify_manifest(bundle: FamilyCorpusBundle, manifest: Any) -> None:
    """Verify a family manifest against one verified corpus (fail
    closed). Checks, in order: the manifest schema version; the exact
    corpus family identity / version / binding; the case count; the
    per-case projection (ids, digests, evidence kind, track, matrix
    row - in order); the required statement; the first-version lineage;
    and the manifest digest."""
    mpath = "manifest"
    if not isinstance(manifest, dict):
        raise _manifest(
            f"{mpath}: expected an object, got {type(manifest).__name__}"
        )
    _exact_keys(manifest, _MANIFEST_KEYS, mpath)
    if manifest["manifest_schema_version"] != MANIFEST_SCHEMA_VERSION:
        raise _manifest(
            f"{mpath}: unknown manifest schema version "
            f"{manifest['manifest_schema_version']!r}; only "
            f"{MANIFEST_SCHEMA_VERSION} is supported (fail closed)"
        )
    if manifest["corpus_id"] != bundle.corpus_id:
        raise _manifest(
            f"{mpath}: corpus_id {manifest['corpus_id']!r} does not "
            f"match the corpus {bundle.corpus_id!r}"
        )
    if manifest["corpus_version"] != bundle.corpus_version:
        raise _manifest(
            f"{mpath}: corpus_version {manifest['corpus_version']!r} "
            f"does not match the corpus {bundle.corpus_version!r}"
        )
    if (
        not isinstance(manifest["semantic_contract_binding"], list)
        or tuple(manifest["semantic_contract_binding"])
        != bundle.semantic_contract_binding
    ):
        raise _manifest(
            f"{mpath}: semantic_contract_binding "
            f"{manifest['semantic_contract_binding']!r} does not match "
            f"the corpus binding {list(bundle.semantic_contract_binding)!r}"
        )
    if manifest["corpus_digest"] != bundle.corpus_digest:
        raise _manifest(
            f"{mpath}: corpus_digest {manifest['corpus_digest']!r} does "
            f"not match the corpus {bundle.corpus_digest!r}"
        )
    if _int(manifest["case_count"], f"{mpath}.case_count") != len(bundle.cases):
        raise _manifest(
            f"{mpath}: case_count {manifest['case_count']!r} does not "
            f"match the corpus case list ({len(bundle.cases)})"
        )
    raw_cases = manifest["cases"]
    if not isinstance(raw_cases, list) or len(raw_cases) != len(bundle.cases):
        raise _manifest(
            f"{mpath}: the case projection must list every corpus case "
            f"({len(bundle.cases)}), got {type(raw_cases).__name__} of "
            f"length {len(raw_cases) if isinstance(raw_cases, list) else 'n/a'}"
        )
    for i, (raw, case) in enumerate(zip(raw_cases, bundle.cases)):
        cpath = f"{mpath}.cases[{i}]"
        _exact_keys(raw, _MANIFEST_CASE_KEYS, cpath)
        projection = {
            "case_id": case.case_id,
            "case_digest": case.case_digest,
            "evidence_kind": case.evidence_kind,
            "track": case.track,
            "matrix_row": case.matrix_row,
        }
        if raw != projection:
            raise _manifest(
                f"{cpath}: the manifest case projection disagrees with "
                "the corpus case document (case id / digest / evidence "
                f"kind / track / matrix row - got {raw!r})"
            )
    if manifest["statement"] != FAMILY_STATEMENT:
        raise _manifest(
            f"{mpath}: the family statement of the first version is "
            "tampered (the statement is inside the manifest digest)"
        )
    lineage = manifest["lineage"]
    _exact_keys(lineage, _LINEAGE_KEYS, f"{mpath}.lineage")
    if lineage != FIRST_VERSION_LINEAGE:
        raise _manifest(
            f"{mpath}.lineage: the family's first version derives from "
            f"no earlier family version (expected {FIRST_VERSION_LINEAGE}), "
            f"got {lineage}"
        )
    state = {k: v for k, v in manifest.items() if k != "manifest_digest"}
    if canonical_sha256(state) != manifest["manifest_digest"]:
        raise _manifest(
            f"{mpath}: manifest_digest does not verify (the manifest "
            "was mutated after sealing)"
        )
    return None


# ---------------------------------------------------------------------------
# File loading (the stable canonical serialization + the declared
# source-file digest consistency)
# ---------------------------------------------------------------------------

CANONICAL_CORPUS_BYTES = (
    "the house canonical serialization: json.dumps(document, "
    "indent=1, sort_keys=True, ensure_ascii=True) + newline"
)


def canonically_serialize(document: dict[str, Any]) -> bytes:
    return (
        json.dumps(document, indent=1, sort_keys=True, ensure_ascii=True)
        + "\n"
    ).encode("utf-8")


def _repo_root_of(corpus_path: Path) -> Path:
    """The repository root from the family storage layout (design
    section 4.2): ``<root>/evaluation/fu4_bundle_authority_
    qualification/<name>.json`` - the cited archive paths are
    repo-relative."""
    return corpus_path.resolve().parents[2]


def _verify_cited_archives(
    bundle: FamilyCorpusBundle, repo_root: Path
) -> None:
    """The declared source-file digest consistency (design section
    4.2): every cited archive file is re-read and its SHA-256 must
    equal the declared ``archive_digest`` (a cited file that moved or
    was substituted is a load failure - the case is not reproducible
    offline). The re-verification proves the archive's integrity only
    (the L3 recording-act boundary - design section 3.2)."""
    for case in bundle.cases:
        for side in ("candidate", "target"):
            block = case.document["source"][side]
            archive = block.get("archive")
            archive_digest = block.get("archive_digest")
            if archive is None or archive_digest is None:
                continue
            file = repo_root / archive
            if not file.is_file():
                raise _digest(
                    f"case {case.case_id}: source.{side}.archive: the "
                    f"cited archive file {archive!r} is missing (the "
                    "declared source-file digest cannot verify)"
                )
            actual = hashlib.sha256(file.read_bytes()).hexdigest()
            if actual != archive_digest:
                raise _digest(
                    f"case {case.case_id}: source.{side}.archive_digest: "
                    "the cited archive file's digest does not match the "
                    f"declared value (the source file moved or was "
                    f"substituted; declared {archive_digest!r}, actual "
                    f"{actual!r})"
                )
    return None


def load_corpus(path: str | Path) -> FamilyCorpusBundle:
    """Load + strictly verify one sealed family corpus file.

    The file must be in the stable canonical serialization (the house
    form - byte re-serialization must reproduce the file, modulo the
    documented autocrlf working-tree state); the document must verify
    (identity, seal, cases, revisions, digest); every cited archive
    must re-verify its declared digest. Raises the bounded
    ``BundleAuthorityCorpusError`` family with the deterministic,
    explicit failure reason."""
    file = Path(path)
    if not file.is_file():
        raise BundleAuthorityCorpusError(
            _STAGE_SCHEMA, f"corpus file not found: {file}"
        )
    raw = file.read_bytes()
    try:
        document = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise _schema(f"corpus is not valid JSON: {exc}") from exc
    if not isinstance(document, dict):
        raise _schema(
            f"corpus document: expected an object, got {type(document).__name__}"
        )
    # The stable canonical serialization (check 6): the file must
    # re-serialize byte-identically (modulo the documented autocrlf
    # working-tree expansion - the house two-state discipline).
    canonical = canonically_serialize(document)
    lf = b"\n"
    crlf = b"\r\n"
    if raw not in (canonical, canonical.replace(lf, crlf)):
        raise _schema(
            f"corpus file {file.name}: not in the stable canonical "
            "serialization (sorted keys / compact indent / ASCII - "
            "the re-serialization differs; a reordered / reformatted "
            "file is a tamper, never a silent re-wrap)"
        )
    bundle = verify_corpus_document(document)
    _verify_cited_archives(bundle, _repo_root_of(file))
    return bundle


def load_bundle(
    corpus_path: str | Path, manifest_path: str | Path
) -> FamilyCorpusBundle:
    """Load + verify the sealed corpus AND its manifest (the full
    manifest-integrity check set of design section 4.5)."""
    file = Path(corpus_path)
    bundle = load_corpus(file)
    manifest_file = Path(manifest_path)
    if not manifest_file.is_file():
        raise _manifest(f"manifest file not found: {manifest_file}")
    mraw = manifest_file.read_bytes()
    try:
        manifest = json.loads(mraw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise _manifest(f"manifest is not valid JSON: {exc}") from exc
    if not isinstance(manifest, dict):
        raise _manifest(
            f"manifest: expected an object, got {type(manifest).__name__}"
        )
    mcanon = canonically_serialize(manifest)
    lf = b"\n"
    crlf = b"\r\n"
    if mraw not in (mcanon, mcanon.replace(lf, crlf)):
        raise _manifest(
            f"manifest file {manifest_file.name}: not in the stable "
            "canonical serialization (the re-serialization differs)"
        )
    verify_manifest(bundle, manifest)
    return bundle
