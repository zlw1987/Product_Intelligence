"""Tests for the S2-A-FU4 bundle-composition authority contract
(PRODUCT-INTEL.SEMANTIC-AUTHORITY-V2-Q3-B5-P4, as CORRECTED IN PLACE by
PRODUCT-INTEL.SEMANTIC-AUTHORITY-V2-Q3-B5-P4-FU1).

Covers ``product_intelligence.research.semantic_authority_fu4`` — the
separately versioned authority contract
``SEMANTIC_AUTHORITY_V2_S2A_FU4`` implementing the approved, CORRECTED
Q3-B5-P3 bundle-composition authority design
(``docs/PRODUCT_INTEL_Q3B5_P3_BUNDLE_COMPOSITION_DESIGN.md`` — Blocker A
quantity completeness + Blocker B composition completeness, + the FU1
channel-content binding amendment, schema version 2):

**Q3-B5-P4-FU1 (this correction, recorded).** The independent GitHub
source review of Q3-B5-P4 found two defects: (1) the derivation's
presentation gate checked only source class + published quantity
against the channel — a self-verifying digest is not proof of
cross-record association — so a composition record built from listing
A's channel / extraction result was accepted over listing B's channel
whenever source class, bundle form, and quantity agreed; (2) the gate
compared the published integer quantities with object identity
(``is not``), which wrongly refuses separately deserialized equal
quantities greater than 256. Corrected (versioned evidence schema v2 —
the candidate record's ``channel_content_digest`` binding over the
exact canonical channel content, including the published
``raw_detail``; the presentation gate re-verifies the association at
derivation time; quantity compared by exact value). This file's
corrections are: the schema-version pin (A2) and the unknown-version
node (B9) moved from 1 to 2 / 3 respectively (the versioned amendment
— the recorded conflict of the Q3-B5-P3-FU1 discipline: any change is a
new version, never a silent edit); two direct positional constructions
gain the one new field (B4 / B5); the record helpers bind to the
canonical channel their derivation call-sites present (the
``_candidate_established`` helper now constructs over its marker-
carrying channel, and every call-site presenting an ESTABLISHED record
presents THAT channel — the fixtures previously embodied the
substitution defect: an EST record presented over a channel whose
published ``raw_detail`` carries no completeness statement); and the
new B11 adversarial class (the mandated matrix over the corrected
binding). No test is deleted, renamed, skipped, xfailed, deselected,
ignored, or weakened: every preserved node keeps its name, its
asserted unit / tier / rule expectations, and its intent — only the
fixture CONSTRUCTION aligns the record with the channel it is
presented over (the corrected contract), exactly as the Q3-B4-FU2 /
Q3-B5-P2-FU1 precedents recorded their in-place corrections.

* **A — Preservation.** A1 file-digest pins (every frozen input of
  section 8 byte-identical to the starting SHA
  ``bc12c4a36e4dd4bef85a958b6e7406ca1c87361f``); A2 delegation identity
  (the FU4 dispatch's FU2 / FU3 arms ≡ the frozen derivations, same
  inputs ⇒ same outputs / same exceptions; unknown token fails closed;
  non-string TypeError); A3 suite preservation (the 98-node FU3 suite
  file + the 111 / 7-node extraction suite files are digest-pinned
  UNCHANGED and pass unmodified — re-run by validation); A4 the
  production codec / replay registries are unchanged and refuse an
  FU4-bound payload; the live record type still pins the FU2 token;
  ``V2_AUTHORITY_QUALIFIED`` False in both pinned locations; no live
  module imports the FU4 module (AST + lexical scan); A5 / A6 the
  Django checks and the collection accounting run as validation
  commands; A7 the two-token coexistence pin (the SAME recorded
  count-only bundle inputs derive PROVEN_EQUIVALENT under the FU3 arm
  and UNPROVEN under the FU4 arm — documented per-binding behavior,
  never drift).
* **B — The composition evidence schema (construction-level).** B1 the
  five-way distinction + the marker rows over published text (through
  the REAL frozen extractor chain); B2 empty / truncated markers never
  establish (un-constructible at the type level); B3 count-only never
  bound; B4 provenance refusal (no member is a model claim); B5
  integrity (tampered / forged records refused at construction AND at
  presentation); B6 determinism (equal inputs ⇒ byte-equal records;
  the canonical order of additional_clauses); B7 the frozen target
  record under FU4 (D18); B8 clause-grammar edges (the grammar decides
  the TEXTUAL axis only); B9 the composition-completeness attestation
  constructor (Blocker B); B10 the quantity-completeness attestation
  constructor (Blocker A); B11 (FU1) the channel-content binding:
  cross-listing substitution refused (RECORDED_CHANNEL and EXTRACTION
  bases), separately deserialized equal quantities > 256 derive, equal
  quantity over different composition, tampered binding /
  association, valid same-listing derivation, and the
  constructor-time + derivation-time integrity enforcement.
* **C — The comparison rules (one row per mandated rule).** C1 missing
  / partial / completeness-unknown composition ⇒ UNPROVEN; C2 equal
  counts without composition ⇒ UNPROVEN (FU4) while FU3 PROVEN; C3
  materially established difference ⇒ CONTRADICTED (both sides
  ESTABLISHED); C4 unestablished difference ⇒ UNPROVEN; C5 equal
  complete compositions with sufficient provenance ⇒
  PROVEN_EQUIVALENT (the corrected D6 conjunction); C6 conflicting
  title and structured fields ⇒ fail closed; C7 form before contents;
  C8 MPN-in-clause non-inference; C9 model-output non-inference; C10
  the quantity-completeness axis (every axis state; the Blocker A
  defect row); C11 the completeness axis (Blocker B rows; repetition ≠
  completeness); C12 the copied attestation (no copy detection; the
  detectable launderings are unconstructible; the audit surface
  records both attestations).
* **D — Tier, overlay, and the Q3-B4 §4.1 invariant.** D1 the exact
  MATCH + HIGH + STRONG + clean composition over every corrected bundle
  shape (the automatic-tier ceiling invariants); D2 the human overlay
  is preserved (a firewall-capped bundle candidate confirmed by a
  recorded CONFIRM derives HUMAN_CONFIRMED); D3 the ceiling rules never
  lift, never touch MACHINE_VERIFIED, never fire outside the automatic
  tier (the FU3 invariants re-proven over the FU4 decision type).
* **E — Binding / replay / qualification (contract phase).** E1 the
  registries are exactly as frozen (the production codec knows exactly
  the V1 + 2.0/FU2 bindings; the harness exactly the two production
  bindings; no corpus 1.2.0 artifact exists); E2 the registration step
  is specified, not executed (no FU4 entry anywhere); E3 replay: an
  FU4-bound payload is refused by the production replay registry; an
  unknown token in a record payload fails closed; the FU3 arm replays
  the historical binding unchanged (A2).
* **F — False-positive resistance (the never-infer list, FU4
  edition).** F1 no composition is derived from price / availability /
  condition / seller / offer URL / the raw reference / the identifier
  fields / the model output / absence / a matching MPN / one listing /
  one price; F2 specification quantities inside a clause are item text,
  never promoted to the bundle's quantity; F3 multi-offer
  independence; F4 the attestation trust boundary (the derivation
  reads exactly the bounded fields; the attestation text is NEVER
  read; a presented attestation is digest-verified before any axis
  uses it; no attestation is ever constructed by the derivation; no
  similarity / fuzzy computation exists in the module).

Every case is an OFFLINE recorded-input construction (synthetic
``ListingObservation`` + the frozen extractor chain, or a directly
constructed frozen channel / result / record) with scripted evaluation
doubles — NO live call, NO model capture, NO network.
"""

from __future__ import annotations

import ast
import dataclasses
import hashlib
import inspect
import json
import sys
from pathlib import Path

import pytest

from product_intelligence.domain import ResearchRequest
from product_intelligence.research import (
    AUTHORITY_CONTRACT_VERSION_V2,
    AuthorityRuleV2,
    AuthorityTier,
    CandidateEvidenceSourceV2,
    CandidateProductEvidenceSource,
    CandidateSalesUnitEvidenceV2,
    ConflictClass,
    ContextProvenance,
    ExtractionMethod,
    HumanReviewStateV2,
    IdentityStateAssessmentV2,
    ListingObservation,
    PackagingEvidenceStateV2,
    ProductEvidenceDimension,
    ProductEvidenceFactV2,
    ProductEvidenceProfileV2,
    ProductEvidenceQuality,
    PRICING_ELIGIBLE_TIERS,
    RelationshipAuthority,
    SALES_UNIT_EVIDENCE_UNAVAILABLE,
    SalesUnitKindV2,
    SalesUnitExtractionIntegrityError,
    SalesUnitExtractionState,
    SemanticEvaluationStateV2,
    SemanticEvaluationV2,
    V2Confidence,
    V2SemanticDecision,
    V1_CONTRACT_BINDING,
    V2_CONTRACT_BINDING,
    assess_listing_identity,
    derive_authority_tier,
    derive_identity_state_v2,
    extract_and_map_sales_unit_evidence,
    normalize_listing_observation,
    supported_contract_bindings,
)
from product_intelligence.research import semantic_authority_fu4 as fu4
from product_intelligence.research import semantic_authority_fu3 as fu3
from product_intelligence.research.semantic_authority_fu3 import (
    AUTHORITY_CONTRACT_VERSION_V2_FU3,
    AuthorityDecisionV2FU3,
    SalesUnitAuthorityV2,
    TargetSalesUnitEvidenceSourceV2,
    TargetSalesUnitEvidenceV2,
    TargetSalesUnitFormV2,
    derive_authority_tier_for_contract as _fu3_dispatch,
)
from product_intelligence.research.semantic_authority_fu4 import (
    AUTHORITY_CONTRACT_VERSION_V2_FU4,
    AuthorityDecisionV2FU4,
    AuthorityRuleV2FU4,
    BUNDLE_COMPOSITION_EVIDENCE_VERSION_FU4,
    BundleCompositionEvidenceIntegrityError,
    BundleCompositionStateV2FU4,
    BundleQuantityAxisStateV2FU4,
    CandidateBundleCompositionEvidenceV2FU4,
    CandidateCompositionEvidenceBasisV2FU4,
    CompletenessBasisV2FU4,
    CompositionCompletenessAttestationV2FU4,
    EvidenceSideV2FU4,
    KNOWN_AUTHORITY_CONTRACT_TOKENS_FU4,
    QuantityCompletenessAttestationV2FU4,
    QuantityNonMaterialityReasonV2FU4,
    TargetSalesUnitEvidenceV2FU4,
    UnknownAuthorityContractTokenError,
    candidate_composition_from_channel,
    candidate_composition_from_extraction,
    classify_clause_closure,
    derive_authority_tier_for_contract_fu4,
    derive_authority_tier_fu4,
    derive_sales_unit_authority_fu4,
    derive_sales_unit_authority_fu4_case,
    extract_published_bundle_clause,
    is_known_authority_contract_token_fu4,
)
from product_intelligence.research.semantic_v2 import SemanticMatchCaseV2

REPO_ROOT = Path(__file__).resolve().parents[2]
PACKAGE_ROOT = REPO_ROOT / "product_intelligence"
FU4_MODULE_PATH = PACKAGE_ROOT / "research" / "semantic_authority_fu4.py"

REQUEST_MPN = "ABC-123"

SV = BundleCompositionStateV2FU4.SYNTACTICALLY_VALID
EST = BundleCompositionStateV2FU4.ESTABLISHED
PART = BundleCompositionStateV2FU4.PARTIAL
ABSENT = BundleCompositionStateV2FU4.ABSENT
CONTR_PUB = BundleCompositionStateV2FU4.CONTRADICTED_PUBLISHED
P = SalesUnitAuthorityV2.PROVEN_EQUIVALENT
U = SalesUnitAuthorityV2.UNPROVEN
C = SalesUnitAuthorityV2.CONTRADICTED
Q_CONSISTENT = BundleQuantityAxisStateV2FU4.CONSISTENT
Q_BOTH_UNPUBLISHED = BundleQuantityAxisStateV2FU4.BOTH_UNPUBLISHED
Q_ATTESTED = BundleQuantityAxisStateV2FU4.ATTESTED_NOT_MATERIAL
Q_CONTRADICTED = BundleQuantityAxisStateV2FU4.CONTRADICTED
Q_UNDETERMINED = BundleQuantityAxisStateV2FU4.UNDETERMINED

# ---------------------------------------------------------------------------
# A1. The exact frozen file digests at the phase's starting SHA
# (bc12c4a36e4dd4bef85a958b6e7406ca1c87361f). The pins compute over the
# working tree; every listed file is a BYTE-FROZEN input of this phase
# (design section 8), so the working-tree digest IS the starting-SHA
# digest — any edit to a frozen file fails the pin.
# ---------------------------------------------------------------------------

FROZEN_MODULE_PINS: dict[str, str] = {
    "product_intelligence/research/semantic_authority_v2.py": (
        "78301d308e0a5e748c2a22cd8785c673b7c2230b54cc60f4714ee2da6b74d8a5"
    ),
    "product_intelligence/research/semantic_authority_fu3.py": (
        "4ea529452e50a62b63778c97e37856f5660a0c5426654d7918725b3d59e24c0f"
    ),
    "product_intelligence/research/sales_unit_extraction.py": (
        "0dd6016503292a926d86f3dbafa97e59a713a4386df2a648882e4942cc6737b6"
    ),
    "product_intelligence/research/semantic_v2.py": (
        "d573d8086bc51db1653f99cebe42aa476ff954fc9d582f8f014ec2d4a97e7d7d"
    ),
    "product_intelligence/research/semantic_decision_v2.py": (
        "9176380cc67090b1b799e7f9ad1640e5f2858ea1b9680897ff3cb7ad5f4cffeb"
    ),
    "product_intelligence/research/semantic_decision_codec.py": (
        "ef31ef38ca5159c01cbfab9056ae20365c1dd58a8c6fb33b8f45f9f80a03b769"
    ),
    "product_intelligence/research/semantic_decision_replay.py": (
        "481f58aecf08893f0aab683a620bf25a41960e529f40ae197be06be1e272f803"
    ),
    "product_intelligence/semantic/contract_v2.py": (
        "d1a69692f57ece6bab8362e77c7067a9642f214d2b115403c1638fe537aa7492"
    ),
    "product_intelligence/semantic/contract_v2_1.py": (
        "dc86899f233eb97beb70007a128745bfc04d374a48dc1d45aec4f6703dede1ec"
    ),
    "product_intelligence/semantic/runtime_v2.py": (
        "e0791384a218409a1e390e304cfc6da1d0e002b404955722b94d557b8c02cc36"
    ),
    "product_intelligence/evaluation/semantic_v2/corpus.py": (
        "876edbe8322889653a5a2178b30f2daf0c7d9a540e52906bf70cad91cddbcc40"
    ),
    "product_intelligence/evaluation/semantic_v2/gates.py": (
        "113c7b53605b4a85d5b11fe93e182518fd1efcf1115b7f797177d4508cc58371"
    ),
    "product_intelligence/evaluation/semantic_v2/report.py": (
        "cad62e4234f7478a326cb5a398f40bc4e1c2e7f2ac1915954179be0c3363c6f1"
    ),
    "product_intelligence/evaluation/semantic_v2/capture.py": (
        "4da8b79a33ffc86363fb01af1b6b5ff0533191374da53a46ecf5b137e00f73fd"
    ),
    "product_intelligence/evaluation/semantic_v2/direct_capture.py": (
        "58b790879efb13f167bf20ae56c96807a47dca9deda10e433d4aece5015e616d"
    ),
    "product_intelligence/evaluation/semantic_v2/cli.py": (
        "0102c4ccc98034d6f5ede3bd2d7be238ae37a4136ca60a634ebd387fb1509376"
    ),
    "product_intelligence/evaluation/semantic_v2/fixtures.py": (
        "cdb60166cf71d3f313b254a1eb652cdec711c8a8cc39a8676eb245bec5f109a8"
    ),
    "product_intelligence/evaluation/semantic_v2/policy.py": (
        "af951180594a4e10cba64db22be114e4bd4b03bb204179c689bef20617e387f4"
    ),
}

CORPUS_ARTIFACT_PINS: dict[str, str] = {
    "evaluation/semantic_v2_qualification/corpus_v1.json": (
        "ffb407b3e440f08ae5e92f8fe4444d23d46744753dee8088fc8e6fea79a8430b"
    ),
    "evaluation/semantic_v2_qualification/manifest_v1.json": (
        "caa5d76ffdce92a4de1b7f9e04dfef640518b3d0ec1580ec916cedf27f607c44"
    ),
    "evaluation/semantic_v2_qualification/corpus_2_1.json": (
        "6f5254c8772ea34547ef8a8315ce4f2352df48d8c2121ed431248d047777bff9"
    ),
    "evaluation/semantic_v2_qualification/manifest_2_1.json": (
        "f37956e45b3d873e583d6f2f42ac7e6f5393110b8ea64e95a9a98e1c02d36ac7"
    ),
    "evaluation/semantic_v2_qualification/policy/"
    "qualification_policy_draft_1.json": (
        "6bc30d3781b7cac27e8dd767849ca53e6d4141095ca972d528ffbee2e4cdc111"
    ),
}

# The frozen historical SUITE files (A3: they pass UNCHANGED — their
# digests prove this phase did not edit a single node of them). The
# FU3 suite file is treated separately below: the approved design
# mandates the FU4 successor module inside research/ (D1) which must
# import the FU3 module and reuse its frozen vocabulary (D9 / D10 /
# D11 / T8) — the FU3 reachability guard's stated property ("no
# production module OUTSIDE the research contract surface references
# it") therefore recognizes exactly one additional contract-surface
# module. That recognition is pinned line-exactly below; every other
# byte of the FU3 suite file is byte-identical to the starting SHA.
SUITE_FILE_PINS: dict[str, str] = {
    "tests/research/test_sales_unit_extraction.py": (
        "d91011523b1cdce2078785968caf5029fd3caa47afdae1eb97871ecbaab48e56"
    ),
    "tests/research/test_sales_unit_extraction_recorded_pages.py": (
        "dcbb83804b6e2d57bd9dbd1e62ccf1f0e2cd2e0f9173b7158cb596ada456739d"
    ),
}

FU3_SUITE_PATH = "tests/research/test_semantic_authority_v2_fu3.py"
FU3_SUITE_STARTING_SHA_DIGEST = (
    "8f56cc1d11c06e081fe2c2d7b8fa7d50fb2d82b8984415765e6415467099ea0b"
)
FU3_GUARD_ORIGINAL_LINE = (
    '        allowed_paths = {FU3_MODULE_PATH, '
    'PACKAGE_ROOT / "research" / "__init__.py"}'
)
FU3_GUARD_RECORDED_LINE = (
    '        allowed_paths = {FU3_MODULE_PATH, '
    'PACKAGE_ROOT / "research" / "__init__.py", '
    'PACKAGE_ROOT / "research" / "semantic_authority_fu4.py"}'
)


def _file_digest(relative_path: str) -> str:
    return hashlib.sha256((REPO_ROOT / relative_path).read_bytes()).hexdigest()


# ---------------------------------------------------------------------------
# Recorded-input construction (the real frozen 3C chain, the FU3-test
# pattern)
# ---------------------------------------------------------------------------


def _observation(
    mpn: str | None = None,
    sku: str | None = None,
    title: str | None = "Test Product",
) -> ListingObservation:
    return ListingObservation(
        source_url="https://example.com/product",
        extraction_method=ExtractionMethod.JSON_LD,
        product_title=title,
        brand_text=None,
        manufacturer_part_number_text=mpn,
        sku_text=sku,
        price_text="100",
        currency_text="USD",
        availability_text="In stock",
        condition_text="New",
        seller_text=None,
    )


def _assess(
    mpn: str | None = None,
    sku: str | None = None,
    title: str | None = "Test Product",
    req_mpn: str = REQUEST_MPN,
    description: str = "A test product",
):
    normalized = normalize_listing_observation(
        _observation(mpn=mpn, sku=sku, title=title)
    )
    request = ResearchRequest(
        manufacturer_part_number=req_mpn, description=description
    )
    return assess_listing_identity(request, normalized)


def _v2(
    mpn: str | None = None,
    sku: str | None = None,
    title: str | None = "Test Product",
    req_mpn: str = REQUEST_MPN,
    description: str = "A test product",
) -> IdentityStateAssessmentV2:
    return derive_identity_state_v2(
        _assess(
            mpn=mpn, sku=sku, title=title, req_mpn=req_mpn,
            description=description,
        )
    )


def _eval(
    decision: V2SemanticDecision,
    confidence: V2Confidence,
    conflicts: frozenset[ConflictClass] = frozenset(),
) -> SemanticEvaluationV2:
    return SemanticEvaluationV2.evaluated(decision, confidence, conflicts)


def _match(
    high: bool = True, conflicts: frozenset[ConflictClass] = frozenset()
) -> SemanticEvaluationV2:
    return _eval(
        V2SemanticDecision.MATCH,
        V2Confidence.HIGH if high else V2Confidence.MEDIUM,
        conflicts,
    )


NO_CTX = frozenset()
PRODUCT_CTX = frozenset({ContextProvenance.MANUFACTURER_PRODUCT_CONTEXT})
RELATION_CTX = frozenset({ContextProvenance.MANUFACTURER_RELATION_AUTHORITY})
CUSTOMER_CTX = frozenset({ContextProvenance.CUSTOMER_RETRIEVAL_RELATION})

TITLE_SOURCES = frozenset({CandidateProductEvidenceSource.LISTING_PRODUCT_TITLE})


def _strong_profile() -> ProductEvidenceProfileV2:
    """A bounded STRONG product-evidence profile: a usable title plus
    two matched facts on two distinct hard product dimensions, grounded
    in the listing title (never a model claim)."""
    return ProductEvidenceProfileV2(
        has_usable_product_title=True,
        matched_facts=frozenset(
            {
                ProductEvidenceFactV2(
                    ProductEvidenceDimension.CAPACITY, TITLE_SOURCES
                ),
                ProductEvidenceFactV2(
                    ProductEvidenceDimension.INTERFACE, TITLE_SOURCES
                ),
            }
        ),
    )


def _channel(
    kind: SalesUnitKindV2,
    quantity: int | None = None,
    raw_detail: str = "published packaging field",
    source: CandidateEvidenceSourceV2 = (
        CandidateEvidenceSourceV2.PUBLISHED_STRUCTURED_FIELD
    ),
) -> CandidateSalesUnitEvidenceV2:
    """An OBSERVED recorded sales-unit channel with explicit provenance."""
    return CandidateSalesUnitEvidenceV2(
        state=PackagingEvidenceStateV2.OBSERVED,
        kind=kind,
        quantity=quantity,
        raw_detail=raw_detail,
        source=source,
    )


UNAVAILABLE = SALES_UNIT_EVIDENCE_UNAVAILABLE

# The canonical bundle clause of this file's worked examples.
CLAUSE = "2x RAM + 1x CPU"


# ---------------------------------------------------------------------------
# Digest-verified record assembly (the test-side mirror of the module's
# canonical documents — the constructors re-verify them; a drift here
# fails immediately at construction).
# ---------------------------------------------------------------------------


def _canon_digest(document: dict[str, object]) -> str:
    encoded = json.dumps(
        document, sort_keys=True, separators=(",", ":"), ensure_ascii=True
    )
    return hashlib.sha256(encoded.encode("ascii")).hexdigest()


def _clause_digest(clause: str) -> str:
    return hashlib.sha256(clause.encode("utf-8")).hexdigest()


def _make_attestation(
    subject_side: EvidenceSideV2FU4,
    basis: CompletenessBasisV2FU4,
    source,
    clause_digest: str,
    attestation_text: str,
    schema_version: int = BUNDLE_COMPOSITION_EVIDENCE_VERSION_FU4,
) -> CompositionCompletenessAttestationV2FU4:
    document = {
        "schema_version": schema_version,
        "subject_side": subject_side.value,
        "basis": basis.value,
        "source": source.value,
        "clause_digest": clause_digest,
        "attestation_text": attestation_text,
    }
    return CompositionCompletenessAttestationV2FU4(
        schema_version,
        subject_side,
        basis,
        source,
        clause_digest,
        attestation_text,
        _canon_digest(document),
    )


def _make_target_fu4(
    form: TargetSalesUnitFormV2,
    quantity: int | None,
    source: TargetSalesUnitEvidenceSourceV2,
    composition_clause: str | None = None,
    composition_state: BundleCompositionStateV2FU4 | None = None,
    completeness_attestation: (
        CompositionCompletenessAttestationV2FU4 | None
    ) = None,
    schema_version: int = BUNDLE_COMPOSITION_EVIDENCE_VERSION_FU4,
) -> TargetSalesUnitEvidenceV2FU4:
    document = {
        "schema_version": schema_version,
        "form": form.value,
        "quantity": quantity,
        "source": source.value,
        "composition_clause": composition_clause,
        "composition_state": (
            composition_state.value if composition_state is not None else None
        ),
        "completeness_attestation": (
            completeness_attestation.canonical()
            if completeness_attestation is not None
            else None
        ),
    }
    return TargetSalesUnitEvidenceV2FU4(
        schema_version,
        form,
        quantity,
        source,
        composition_clause,
        composition_state,
        completeness_attestation,
        _canon_digest(document),
    )


def _make_quantity_attestation(
    subject_side: EvidenceSideV2FU4,
    reason: QuantityNonMaterialityReasonV2FU4,
    source: TargetSalesUnitEvidenceSourceV2,
    attestation_text: str,
    schema_version: int = BUNDLE_COMPOSITION_EVIDENCE_VERSION_FU4,
) -> QuantityCompletenessAttestationV2FU4:
    document = {
        "schema_version": schema_version,
        "subject_side": subject_side.value,
        "reason": reason.value,
        "source": source.value,
        "attestation_text": attestation_text,
    }
    return QuantityCompletenessAttestationV2FU4(
        schema_version,
        subject_side,
        reason,
        source,
        attestation_text,
        _canon_digest(document),
    )


def _make_candidate_record(
    basis: CandidateCompositionEvidenceBasisV2FU4,
    state: BundleCompositionStateV2FU4,
    composition_clause: str | None,
    source: CandidateEvidenceSourceV2,
    channel_quantity: int | None = None,
    additional_clauses: tuple[str, ...] = (),
    completeness_attestation: (
        CompositionCompletenessAttestationV2FU4 | None
    ) = None,
    extraction_result_digest: str | None = None,
    extraction_input_digest: str | None = None,
    channel_content_digest: str | None = None,
    schema_version: int = BUNDLE_COMPOSITION_EVIDENCE_VERSION_FU4,
) -> CandidateBundleCompositionEvidenceV2FU4:
    """The test-side mirror of the module's candidate record (schema
    v2). ``channel_content_digest`` defaults to the binding of the
    CANONICAL channel this record describes — the OBSERVED BUNDLE
    channel with this record's source / quantity and the
    corpus-shaped ``raw_detail`` (``bundle: <clause>`` / ``bundle`` for
    ABSENT) — so the hand-built record is EXACTLY the construction of
    the channel the derivation call-sites present (the FU1 binding);
    pass an explicit digest to pin a different recorded anchor."""
    if channel_content_digest is None:
        raw_detail = (
            "bundle" if composition_clause is None else f"bundle: {composition_clause}"
        )
        bound_channel = CandidateSalesUnitEvidenceV2(
            state=PackagingEvidenceStateV2.OBSERVED,
            kind=SalesUnitKindV2.BUNDLE,
            quantity=channel_quantity,
            raw_detail=raw_detail,
            source=source,
        )
        channel_content_digest = _canon_digest(bound_channel.canonical())
    document = {
        "schema_version": schema_version,
        "basis": basis.value,
        "state": state.value,
        "completeness_attestation": (
            completeness_attestation.canonical()
            if completeness_attestation is not None
            else None
        ),
        "composition_clause": composition_clause,
        "additional_clauses": list(additional_clauses),
        "source": source.value,
        "channel_quantity": channel_quantity,
        "extraction_result_digest": extraction_result_digest,
        "extraction_input_digest": extraction_input_digest,
        "channel_content_digest": channel_content_digest,
    }
    return CandidateBundleCompositionEvidenceV2FU4(
        schema_version,
        basis,
        state,
        completeness_attestation,
        composition_clause,
        additional_clauses,
        source,
        channel_quantity,
        extraction_result_digest,
        extraction_input_digest,
        channel_content_digest,
        _canon_digest(document),
    )


# Convenience records over the canonical clause.
TS = TargetSalesUnitEvidenceSourceV2.REVIEWED_TARGET_CONTEXT
TSD = TargetSalesUnitEvidenceSourceV2.REQUEST_DESCRIPTION
SRC = CandidateEvidenceSourceV2.PUBLISHED_STRUCTURED_FIELD
SRCT = CandidateEvidenceSourceV2.LISTING_TITLE


def _target(
    quantity: int | None = None,
    source: TargetSalesUnitEvidenceSourceV2 = TS,
    clause: str | None = None,
    state: BundleCompositionStateV2FU4 | None = None,
    att: CompositionCompletenessAttestationV2FU4 | None = None,
) -> TargetSalesUnitEvidenceV2FU4:
    """A BUNDLE-form FU4 target record (the non-bundle forms use
    ``_make_target_fu4`` directly)."""
    return _make_target_fu4(
        TargetSalesUnitFormV2.BUNDLE, quantity, source, clause, state, att
    )


def _target_established(
    clause: str = CLAUSE,
    basis: CompletenessBasisV2FU4 = (
        CompletenessBasisV2FU4.PUBLISHED_COMPLETENESS_STATEMENT
    ),
    quantity: int | None = None,
    att_text: str = ", complete list",
) -> TargetSalesUnitEvidenceV2FU4:
    att = _make_attestation(
        EvidenceSideV2FU4.TARGET, basis, TS, _clause_digest(clause), att_text
    )
    return _target(quantity, TS, clause, EST, att)


def _candidate_channel(
    quantity: int | None = None,
    raw_detail: str = f"bundle: {CLAUSE}",
    source: CandidateEvidenceSourceV2 = SRC,
) -> CandidateSalesUnitEvidenceV2:
    return _channel(SalesUnitKindV2.BUNDLE, quantity, raw_detail, source)


def _candidate_record(
    quantity: int | None = None,
    clause: str = CLAUSE,
    state: BundleCompositionStateV2FU4 = SV,
    att: CompositionCompletenessAttestationV2FU4 | None = None,
    source: CandidateEvidenceSourceV2 = SRC,
) -> CandidateBundleCompositionEvidenceV2FU4:
    return _make_candidate_record(
        CandidateCompositionEvidenceBasisV2FU4.RECORDED_CHANNEL,
        state,
        clause,
        source,
        channel_quantity=quantity,
        completeness_attestation=att,
    )


# The ESTABLISHED candidate's canonical channel: the published
# completeness statement is PART of the presented publication's
# raw_detail (the FU1 binding: an EST record is the construction of
# THIS channel — presenting it over a marker-free channel is the
# cross-listing substitution the corrected gate refuses).
EST_RAW_DETAIL = f"bundle: {CLAUSE}, complete list"


def _candidate_established_channel(
    quantity: int | None = None,
    source: CandidateEvidenceSourceV2 = SRC,
) -> CandidateSalesUnitEvidenceV2:
    return _channel(SalesUnitKindV2.BUNDLE, quantity, EST_RAW_DETAIL, source)


def _candidate_established(quantity: int | None = None):
    """The ESTABLISHED candidate record — constructed (not hand-built)
    over its canonical marker-carrying channel, so it is exactly the
    construction of the channel its call-sites present."""
    return candidate_composition_from_channel(
        _candidate_established_channel(quantity)
    )


def _quantity_attestation(
    subject_side: EvidenceSideV2FU4,
    text: str = (
        "review determination: the subject source structurally publishes "
        "no bundle counts for this offer shape"
    ),
) -> QuantityCompletenessAttestationV2FU4:
    return _make_quantity_attestation(
        subject_side,
        QuantityNonMaterialityReasonV2FU4.SUBJECT_SOURCE_STRUCTURALLY_WITHOUT_BUNDLE_COUNTS,
        TS,
        text,
    )


def _extract(title: str, structured: str | None = None):
    return extract_and_map_sales_unit_evidence(_observation(title=title), structured)


def _tier(
    channel: CandidateSalesUnitEvidenceV2,
    candidate_composition: CandidateBundleCompositionEvidenceV2FU4 | None,
    target_unit_evidence,
    quantity_attestation: QuantityCompletenessAttestationV2FU4 | None = None,
    assessment: IdentityStateAssessmentV2 | None = None,
    evaluation: SemanticEvaluationV2 | None = None,
    provenances: frozenset[ContextProvenance] = NO_CTX,
    profile: ProductEvidenceProfileV2 | None = None,
    human: HumanReviewStateV2 | None = None,
) -> AuthorityDecisionV2FU4:
    """The Q3-B4 §4.1 composition (MATCH + HIGH + STRONG + clean + U1
    exact-identifier) unless overridden."""
    return derive_authority_tier_fu4(
        assessment or _v2(title=f"Has {REQUEST_MPN} in the title"),
        channel,
        evaluation if evaluation is not None else _match(),
        provenances,
        profile if profile is not None else _strong_profile(),
        human,
        target_unit_evidence=target_unit_evidence,
        candidate_composition=candidate_composition,
        quantity_attestation=quantity_attestation,
    )


# ===========================================================================
# A. Preservation (the frozen side of the ledger)
# ===========================================================================


class TestA1FrozenFilePins:
    @pytest.mark.parametrize(
        "relative_path,expected_digest",
        sorted(FROZEN_MODULE_PINS.items()),
        ids=lambda v: v if isinstance(v, str) else str(v),
    )
    def test_frozen_module_is_byte_identical_to_the_starting_sha(
        self, relative_path: str, expected_digest: str
    ) -> None:
        assert _file_digest(relative_path) == expected_digest, (
            f"{relative_path} changed; it is a BYTE-FROZEN input of the "
            "FU4 contract phase (design section 8) — the FU4 amendment "
            "lives behind its own token and module, never in place"
        )

    @pytest.mark.parametrize(
        "relative_path,expected_digest",
        sorted(CORPUS_ARTIFACT_PINS.items()),
    )
    def test_corpus_and_policy_artifacts_are_repinned(
        self, relative_path: str, expected_digest: str
    ) -> None:
        assert _file_digest(relative_path) == expected_digest, (
            f"{relative_path} changed; the committed corpus artifacts "
            "(1.0.0 / 1.1.0) and the DRAFT policy are byte-frozen under "
            "their own bindings (no reseal in the contract phase)"
        )

    @pytest.mark.parametrize(
        "relative_path,expected_digest", sorted(SUITE_FILE_PINS.items())
    )
    def test_frozen_historical_suite_files_are_unchanged(
        self, relative_path: str, expected_digest: str
    ) -> None:
        """A3 (suite-level): the full 111 / 7-node P2 / P2-FU1
        extraction suites pass UNCHANGED — this pin proves this phase
        edited no node of them; the suites themselves are re-run by
        validation."""
        assert _file_digest(relative_path) == expected_digest, (
            f"{relative_path} changed; the historical extraction suites "
            "are preservation-proof inputs of the FU4 phase"
        )

    def test_the_fu3_suite_is_unchanged_except_the_recorded_allowline(self) -> None:
        """A3 (suite-level, the recorded exception): the full 98-node
        FU3 suite passes with EXACTLY ONE mechanical line changed in
        its reachability guard — the guard's ``allowed_paths`` set
        recognizes the FU4 successor contract module that the approved
        design mandates (design D1: the FU4 module lives in research/;
        D9 / D10 / D11 / T8: it imports the FU3 module, mirrors its
        rule set, and reuses its frozen vocabulary — the FU3 lexical
        markers are therefore unavoidable inside the FU4 module). The
        guard's stated safety property — "no production module OUTSIDE
        the research contract surface references it" — is unchanged:
        the FU4 module is research contract surface (the same category
        as ``research/__init__.py``, already allowed), and the FU4 test
        file's own reachability guard re-pins that no live / persistence
        / pricing / presentation module references the FU4 surface. This
        pin proves the working FU3 suite file equals its starting-SHA
        content plus exactly that one recorded line — no other byte.
        The 98-node FU3 suite re-runs unmodified by validation."""
        text = (
            REPO_ROOT / FU3_SUITE_PATH
        ).read_text(encoding="utf-8")
        assert text.count(FU3_GUARD_RECORDED_LINE) == 1, (
            "the FU3 guard's recorded FU4 allow-line must appear exactly "
            "once"
        )
        starting_sha_text = text.replace(
            FU3_GUARD_RECORDED_LINE, FU3_GUARD_ORIGINAL_LINE
        )
        assert hashlib.sha256(starting_sha_text.encode("utf-8")).hexdigest() == (
            FU3_SUITE_STARTING_SHA_DIGEST
        ), (
            "the FU3 suite file differs from its starting-SHA content by "
            "more than the one recorded guard allow-line (any other edit "
            "to the frozen historical suite is a preservation violation)"
        )


class TestA2TokenAndDelegationIdentity:
    def test_the_fu4_token_is_separately_versioned(self) -> None:
        assert (
            AUTHORITY_CONTRACT_VERSION_V2_FU4
            == "SEMANTIC_AUTHORITY_V2_S2A_FU4"
        )
        assert AUTHORITY_CONTRACT_VERSION_V2_FU4 != AUTHORITY_CONTRACT_VERSION_V2
        assert AUTHORITY_CONTRACT_VERSION_V2_FU4 != AUTHORITY_CONTRACT_VERSION_V2_FU3
        assert KNOWN_AUTHORITY_CONTRACT_TOKENS_FU4 == frozenset(
            {
                AUTHORITY_CONTRACT_VERSION_V2,
                AUTHORITY_CONTRACT_VERSION_V2_FU3,
                AUTHORITY_CONTRACT_VERSION_V2_FU4,
            }
        )
        assert BUNDLE_COMPOSITION_EVIDENCE_VERSION_FU4 == 2
        # The frozen FU3 constant stays exactly {FU2, FU3}.
        assert fu3.KNOWN_AUTHORITY_CONTRACT_TOKENS == frozenset(
            {AUTHORITY_CONTRACT_VERSION_V2, AUTHORITY_CONTRACT_VERSION_V2_FU3}
        )
        # The rule set mirrors the FU3 set exactly (D10: no new rule).
        assert {r.value for r in AuthorityRuleV2FU4} == {
            r.value for r in fu3.AuthorityRuleV2FU3
        }
        assert {r.value for r in AuthorityRuleV2FU4} == (
            {r.value for r in AuthorityRuleV2}
            | {"CEILING_SALES_UNIT_NOT_PROVEN", "CEILING_SALES_UNIT_CONTRADICTED"}
        )

    def test_is_known_authority_contract_token_fu4(self) -> None:
        assert is_known_authority_contract_token_fu4(AUTHORITY_CONTRACT_VERSION_V2)
        assert is_known_authority_contract_token_fu4(AUTHORITY_CONTRACT_VERSION_V2_FU3)
        assert is_known_authority_contract_token_fu4(AUTHORITY_CONTRACT_VERSION_V2_FU4)
        for token in (
            "SEMANTIC_AUTHORITY_V2_S2A_FU9",
            "SEMANTIC_AUTHORITY_V2_S2A_FU1",
            "SEMANTIC_AUTHORITY_V3_S2A_FU4",
            "semantics_authority_v2_s2a_fu4",  # near-miss spelling
            "SEMANTIC_AUTHORITY_V2_S2A_FU4 ",  # trailing whitespace
            " SEMANTIC_AUTHORITY_V2_S2A_FU4",  # leading whitespace
            "semantic_authority_v2_s2a_fu4",  # case variant
            "",
            "V2",
            "1.1",
        ):
            assert not is_known_authority_contract_token_fu4(token)
        with pytest.raises(TypeError):
            is_known_authority_contract_token_fu4(None)  # type: ignore[arg-type]

    def test_the_versioned_vocabularies_are_exactly_bounded(self) -> None:
        assert {s.value for s in BundleCompositionStateV2FU4} == {
            "SYNTACTICALLY_VALID",
            "ESTABLISHED",
            "PARTIAL",
            "ABSENT",
            "CONTRADICTED_PUBLISHED",
        }
        assert {s.value for s in EvidenceSideV2FU4} == {
            "CANDIDATE",
            "TARGET",
        }
        assert {b.value for b in CompletenessBasisV2FU4} == {
            "PUBLISHED_COMPLETENESS_STATEMENT",
            "REVIEWED_COMPOSITION_ATTESTATION",
        }
        assert {r.value for r in QuantityNonMaterialityReasonV2FU4} == {
            "SUBJECT_SOURCE_STRUCTURALLY_WITHOUT_BUNDLE_COUNTS",
            "PUBLISHED_COUNT_NOT_UNIT_MULTIPLICITY",
        }
        assert {s.value for s in BundleQuantityAxisStateV2FU4} == {
            "CONSISTENT",
            "BOTH_UNPUBLISHED",
            "ATTESTED_NOT_MATERIAL",
            "CONTRADICTED",
            "UNDETERMINED",
        }
        assert {b.value for b in CandidateCompositionEvidenceBasisV2FU4} == {
            "EXTRACTION_RESULT_V1",
            "RECORDED_CHANNEL",
        }
        # The versioned marker lists (T9 discipline).
        assert fu4._COMPLETENESS_MARKERS == (
            "complete list",
            "all items listed",
            "everything included",
            "all included",
            "full contents",
            "nothing else included",
        )
        assert fu4._COMPLETENESS_MARKER_DELIMITERS == (
            "+",
            ",",
            "&",
            ";",
            "and",
            "—",
            "–",
            "(",
        )
        assert fu4._INCOMPLETE_MARKERS == (
            "etc.",
            "etc",
            "…",
            "...",
            "and more",
            "+ more",
            "and so on",
            "among others",
            "and other",
        )

    def _identity_inputs(self):
        """The fixed parameterized input set (the FU3 suite's shapes)."""
        shapes = {
            "u1": _v2(title=f"Has {REQUEST_MPN} in the title"),
            "u2e": _v2(sku=REQUEST_MPN),
            "u2n": _v2(sku="RETAIL-SKU-1"),
            "u3": _v2(mpn="ABC"),
            "u4": _v2(title="Usable title without any MPN"),
            "u5_nm1": _v2(mpn=f"{REQUEST_MPN}X"),
            "u5_nm2": _v2(mpn="ABC-124"),
            "c1": _v2(mpn="ZZZ-000"),
            "v_exact": _v2(mpn=REQUEST_MPN),
        }
        e1 = derive_identity_state_v2(
            _assess(req_mpn="", description="description only")
        )
        e2 = _v2(title=None)
        shapes = {**shapes, "e1": e1, "e2": e2}
        evaluations = (
            None,
            SemanticEvaluationV2.runtime_failure(),
            _match(),
            _match(high=False),
            _eval(V2SemanticDecision.NO_MATCH, V2Confidence.HIGH),
            _eval(
                V2SemanticDecision.NO_MATCH,
                V2Confidence.HIGH,
                frozenset({ConflictClass.BUNDLE}),
            ),
        )
        provenance_sets = (NO_CTX, PRODUCT_CTX, RELATION_CTX, CUSTOMER_CTX)
        profile_options = (None, _strong_profile())
        humans = (None, HumanReviewStateV2.CONFIRMED, HumanReviewStateV2.REJECTED)
        return shapes, evaluations, provenance_sets, profile_options, humans

    def test_fu2_arm_delegates_byte_identically_to_the_frozen_derivation(
        self,
    ) -> None:
        """A2: the FU4 dispatch's FU2 arm ≡ the frozen
        ``derive_authority_tier`` (same decision fields, same fired
        rules) — the historical token replays identically under the FU4
        code (the per-binding discipline made mechanical)."""
        shapes, evaluations, provenance_sets, profile_options, humans = (
            self._identity_inputs()
        )
        for name, assessment_v2 in shapes.items():
            profile_opts = (None,) if name in ("e1", "e2") else profile_options
            for profile in profile_opts:
                for evaluation in evaluations:
                    for provenances in provenance_sets:
                        for human in humans:
                            expected = derive_authority_tier(
                                assessment_v2,
                                evaluation,
                                provenances,
                                profile,
                                human,
                            )
                            actual = derive_authority_tier_for_contract_fu4(
                                AUTHORITY_CONTRACT_VERSION_V2,
                                assessment_v2,
                                evaluation,
                                provenances,
                                profile,
                                human,
                            )
                            assert type(actual) is type(expected)
                            assert not isinstance(actual, AuthorityDecisionV2FU3)
                            assert not isinstance(actual, AuthorityDecisionV2FU4)
                            assert actual == expected

    def test_fu2_arm_refuses_sales_unit_inputs(self) -> None:
        u1 = _v2(title=f"Has {REQUEST_MPN} in the title")
        with pytest.raises(ValueError, match="no sales-unit input"):
            derive_authority_tier_for_contract_fu4(
                AUTHORITY_CONTRACT_VERSION_V2,
                u1,
                _match(),
                NO_CTX,
                _strong_profile(),
                sales_unit_channel=_candidate_channel(),
            )
        with pytest.raises(ValueError, match="composition axis"):
            derive_authority_tier_for_contract_fu4(
                AUTHORITY_CONTRACT_VERSION_V2,
                u1,
                _match(),
                NO_CTX,
                _strong_profile(),
                candidate_composition=_candidate_record(),
            )

    def test_fu3_arm_delegates_byte_identically_to_the_frozen_fu3_derivation(
        self,
    ) -> None:
        """A2: the FU4 dispatch's FU3 arm ≡ the frozen
        ``derive_authority_tier_fu3`` (same decision fields, same fired
        rules, same exceptions) — including the frozen count-based BUNDLE
        behavior (A7's shape)."""
        shapes, evaluations, provenance_sets, profile_options, humans = (
            self._identity_inputs()
        )
        channels = (
            UNAVAILABLE,
            _channel(SalesUnitKindV2.SINGLE_UNIT),
            _channel(SalesUnitKindV2.PACK_QUANTITY, 4),
            _channel(SalesUnitKindV2.TRAY_OR_FACTORY_PACK, None),
            _candidate_channel(None),
            _candidate_channel(3, raw_detail="bundle of 3"),
        )
        targets = (
            None,
            TargetSalesUnitEvidenceV2(
                TargetSalesUnitFormV2.BUNDLE, 3, TS
            ),
            TargetSalesUnitEvidenceV2(
                TargetSalesUnitFormV2.PACK_QUANTITY, 4, TS
            ),
        )
        for name, assessment_v2 in shapes.items():
            profile_opts = (None,) if name in ("e1", "e2") else profile_options
            for profile in profile_opts:
                for evaluation in evaluations:
                    for provenances in (NO_CTX, RELATION_CTX):
                        for human in humans:
                            for channel in channels:
                                for target in targets:
                                    expected = _fu3_dispatch(
                                        AUTHORITY_CONTRACT_VERSION_V2_FU3,
                                        assessment_v2,
                                        evaluation,
                                        provenances,
                                        profile,
                                        human,
                                        sales_unit_channel=channel,
                                        target_unit_evidence=target,
                                    )
                                    actual = derive_authority_tier_for_contract_fu4(
                                        AUTHORITY_CONTRACT_VERSION_V2_FU3,
                                        assessment_v2,
                                        evaluation,
                                        provenances,
                                        profile,
                                        human,
                                        sales_unit_channel=channel,
                                        target_unit_evidence=target,
                                    )
                                    assert type(actual) is type(expected)
                                    assert isinstance(actual, AuthorityDecisionV2FU3)
                                    assert not isinstance(actual, AuthorityDecisionV2FU4)
                                    assert actual == expected

    def test_fu3_arm_refuses_composition_and_attestation_inputs(self) -> None:
        """The FU3 contract has no composition axis: silently dropping or
        interpreting the FU4 inputs would be a re-interpretation of a
        frozen contract (contract misuse, fail closed)."""
        u1 = _v2(title=f"Has {REQUEST_MPN} in the title")
        with pytest.raises(ValueError, match="no composition axis"):
            derive_authority_tier_for_contract_fu4(
                AUTHORITY_CONTRACT_VERSION_V2_FU3,
                u1,
                _match(),
                NO_CTX,
                _strong_profile(),
                sales_unit_channel=_candidate_channel(),
                candidate_composition=_candidate_record(),
            )
        with pytest.raises(ValueError, match="no composition axis"):
            derive_authority_tier_for_contract_fu4(
                AUTHORITY_CONTRACT_VERSION_V2_FU3,
                u1,
                _match(),
                NO_CTX,
                _strong_profile(),
                sales_unit_channel=_candidate_channel(),
                quantity_attestation=_quantity_attestation(EvidenceSideV2FU4.TARGET),
            )
        with pytest.raises(ValueError, match="no composition axis"):
            derive_authority_tier_for_contract_fu4(
                AUTHORITY_CONTRACT_VERSION_V2_FU3,
                u1,
                _match(),
                NO_CTX,
                _strong_profile(),
                sales_unit_channel=_candidate_channel(),
                target_unit_evidence=_target_established(),
            )

    def test_fu4_arm_requires_the_recorded_channel(self) -> None:
        u1 = _v2(title=f"Has {REQUEST_MPN} in the title")
        with pytest.raises(ValueError, match="sales-unit channel"):
            derive_authority_tier_for_contract_fu4(
                AUTHORITY_CONTRACT_VERSION_V2_FU4,
                u1,
                _match(),
                NO_CTX,
                _strong_profile(),
            )

    def test_unknown_tokens_fail_closed(self) -> None:
        u1 = _v2(title=f"Has {REQUEST_MPN} in the title")
        for token in (
            "SEMANTIC_AUTHORITY_V2_S2A_FU9",
            "",
            "SEMANTIC_AUTHORITY_V2_S2A_FU4 ",
            "semantic_authority_v2_s2a_fu4",
        ):
            with pytest.raises(UnknownAuthorityContractTokenError):
                derive_authority_tier_for_contract_fu4(
                    token, u1, sales_unit_channel=UNAVAILABLE
                )
        assert issubclass(UnknownAuthorityContractTokenError, ValueError)

    def test_non_string_token_fails_closed(self) -> None:
        u1 = _v2(title=f"Has {REQUEST_MPN} in the title")
        with pytest.raises(TypeError):
            derive_authority_tier_for_contract_fu4(
                None, u1  # type: ignore[arg-type]
            )
        with pytest.raises(TypeError):
            derive_authority_tier_for_contract_fu4(
                42, u1  # type: ignore[arg-type]
            )


class TestA4RegistriesAndReachability:
    def test_the_production_codec_registry_is_unchanged(self) -> None:
        """A4: the production codec knows exactly the V1 + 2.0/FU2
        bindings; the replay registry is the same union — the FU4
        contract phase registers NOTHING (§7.2 / D13)."""
        assert supported_contract_bindings() == (
            V1_CONTRACT_BINDING,
            V2_CONTRACT_BINDING,
        )
        from product_intelligence.research.semantic_decision_replay import (
            SUPPORTED_CONTRACT_BINDINGS,
        )

        assert SUPPORTED_CONTRACT_BINDINGS == (
            V1_CONTRACT_BINDING,
            V2_CONTRACT_BINDING,
        )
        assert all(
            binding[4] in (AUTHORITY_CONTRACT_VERSION_V2,)
            for binding in supported_contract_bindings()
        )

    def test_the_harness_registries_are_unchanged(self) -> None:
        """E1 / D13: the harness knows exactly the two production
        bindings (2.0/FU2 ↔ 1.0.0, 2.1/FU3 ↔ 1.1.0); there is NO corpus
        1.2.0 artifact and NO FU4 entry anywhere (the registration step
        is separately gated — design §7.3)."""
        from product_intelligence.evaluation.semantic_v2 import corpus as harness_corpus
        from product_intelligence.evaluation.semantic_v2 import fixtures as harness_fixtures

        assert harness_corpus.BINDING_CORPUS_VERSIONS == {
            V2_CONTRACT_BINDING: "1.0.0",
            ("V2", "2.1", 1, 1, AUTHORITY_CONTRACT_VERSION_V2_FU3): "1.1.0",
        }
        assert harness_corpus.KNOWN_PRODUCTION_BINDINGS == frozenset(
            {
                V2_CONTRACT_BINDING,
                ("V2", "2.1", 1, 1, AUTHORITY_CONTRACT_VERSION_V2_FU3),
            }
        )
        assert AUTHORITY_CONTRACT_VERSION_V2_FU4 not in {
            binding[4] for binding in harness_corpus.KNOWN_PRODUCTION_BINDINGS
        }
        assert not hasattr(harness_fixtures, "CORPUS_VERSION_2_1_FU4")
        for name in ("corpus_2_1_fu4.json", "manifest_2_1_fu4.json"):
            assert not (
                REPO_ROOT / "evaluation" / "semantic_v2_qualification" / name
            ).exists(), f"{name} exists; corpus 1.2.0 is the separately " \
                      "gated registration step, NOT the contract phase"

    def test_an_fu4_bound_payload_is_refused_by_production_replay(self) -> None:
        """A4 / E3: a record bound to the FU4 token is outside the
        CURRENT live adapters: the replay registry refuses it (never
        silently reinterpreted), and the live V2 record type cannot even
        be constructed under it (the frozen exact-token check)."""
        from product_intelligence.research.semantic_decision_replay import (
            replay_semantic_decision,
        )
        from product_intelligence.research.semantic_decision_record import (
            SemanticDecisionReplayError,
        )

        class _RawRecord:
            pass

        raw = _RawRecord()
        (
            raw.semantic_contract_version,
            raw.prompt_version,
            raw.input_schema_version,
            raw.output_schema_version,
            raw.authority_contract_version,
        ) = ("V2", "2.1", 1, 1, AUTHORITY_CONTRACT_VERSION_V2_FU4)
        with pytest.raises(
            SemanticDecisionReplayError, match="refuses to reinterpret"
        ):
            replay_semantic_decision(raw)

        from tests.research.test_semantic_decision_v2 import (
            _build_record,
        )

        record = _build_record(
            decision=V2SemanticDecision.MATCH, confidence=V2Confidence.HIGH
        )
        with pytest.raises(ValueError, match="authority_contract_version"):
            dataclasses.replace(
                record, authority_contract_version=AUTHORITY_CONTRACT_VERSION_V2_FU4
            )
        assert record.authority_contract_version == AUTHORITY_CONTRACT_VERSION_V2

    def test_an_unknown_token_in_a_record_payload_fails_closed(self) -> None:
        """E3: an unknown / future token in a record payload is refused
        by the production replay (never replayed under the nearest
        known contract)."""
        from product_intelligence.research.semantic_decision_replay import (
            replay_semantic_decision,
        )
        from product_intelligence.research.semantic_decision_record import (
            SemanticDecisionReplayError,
        )

        class _RawRecord:
            pass

        raw = _RawRecord()
        (
            raw.semantic_contract_version,
            raw.prompt_version,
            raw.input_schema_version,
            raw.output_schema_version,
            raw.authority_contract_version,
        ) = ("V2", "2.1", 1, 1, "SEMANTIC_AUTHORITY_V2_S2A_FU9")
        with pytest.raises(SemanticDecisionReplayError):
            replay_semantic_decision(raw)

    def test_v2_authority_stays_unqualified_in_both_pinned_locations(
        self,
    ) -> None:
        from product_intelligence.research import semantic_decision_v2 as sdv2
        from product_intelligence.semantic import runtime_v2

        assert sdv2.V2_AUTHORITY_QUALIFIED is False
        assert runtime_v2.V2_AUTHORITY_QUALIFIED is False
        assert runtime_v2.SEMANTIC_PROMPT_VERSION_V2 == "2.0"

    def _imported_modules(self, path: Path) -> set[str]:
        modules: set[str] = set()
        for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
            if isinstance(node, ast.Import):
                modules.update(alias.name for alias in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module and not node.level:
                modules.add(node.module)
        return modules

    def test_no_live_module_references_the_fu4_contract(self) -> None:
        """The FU4 contract is unreachable from the live V2 runtime
        wiring, persistence, pricing, and presentation: no production
        module outside the research contract surface references it (AST
        import scan + lexical scan of the module name and every
        FU4-specific public symbol)."""
        fu4_symbol = "product_intelligence.research.semantic_authority_fu4"
        lexical_markers = (
            "semantic_authority_fu4",
            "AuthorityDecisionV2FU4",
            "AuthorityRuleV2FU4",
            "derive_authority_tier_fu4",
            "derive_sales_unit_authority_fu4",
            "CandidateBundleCompositionEvidenceV2FU4",
            "TargetSalesUnitEvidenceV2FU4",
            "CompositionCompletenessAttestationV2FU4",
            "QuantityCompletenessAttestationV2FU4",
            "BundleCompositionStateV2FU4",
            "S2A_FU4",
        )
        allowed_paths = {FU4_MODULE_PATH, PACKAGE_ROOT / "research" / "__init__.py"}
        for layer in ("research", "execution", "semantic", "runs", "web", "providers"):
            root = PACKAGE_ROOT / layer
            assert root.is_dir()
            for path in sorted(root.rglob("*.py")):
                if path in allowed_paths:
                    continue
                imported = self._imported_modules(path)
                offending = {
                    module
                    for module in imported
                    if module == fu4_symbol or module.startswith(fu4_symbol + ".")
                }
                assert not offending, f"{path} imports the FU4 contract module"
                source = path.read_text(encoding="utf-8")
                for marker in lexical_markers:
                    assert marker not in source, (
                        f"{path.name} references the FU4 contract surface "
                        f"({marker!r}); the new token is unreachable from "
                        "live wiring"
                    )

    def test_the_fu4_module_is_research_pure(self) -> None:
        source = FU4_MODULE_PATH.read_text(encoding="utf-8")
        modules = self._imported_modules(FU4_MODULE_PATH)
        disallowed = {
            module
            for module in modules
            if module.split(".")[0] != "product_intelligence"
            and module.split(".")[0] not in sys.stdlib_module_names
        }
        assert not disallowed, f"the FU4 contract imports {sorted(disallowed)}"
        for forbidden in (
            "django",
            "product_intelligence.runs",
            "product_intelligence.providers",
            "product_intelligence.evaluation",
            "product_intelligence.web",
            "product_intelligence.execution",
            "product_intelligence.semantic",
        ):
            offending = {
                module
                for module in modules
                if module == forbidden or module.startswith(forbidden + ".")
            }
            assert not offending, f"the FU4 contract imports {sorted(offending)}"
        for io_module in (
            "requests",
            "httpx",
            "urllib",
            "socket",
            "ssl",
            "http",
            "pathlib",
            "sqlite3",
            "os",
            "shutil",
            "tempfile",
            "subprocess",
            "webbrowser",
            "time",
            "datetime",
            "decimal",
            "statistics",
            "math",
            "difflib",
        ):
            offending = {
                module
                for module in modules
                if module == io_module or module.startswith(io_module + ".")
            }
            assert not offending, f"the FU4 contract performs I/O: {offending}"
        for clock_token in ("utcnow", "datetime.now", "time.time", "time.monotonic"):
            assert clock_token not in source
        # No fuzzy / similarity computation exists in the module (F4 /
        # T3: text independence is not a deterministic contract fact —
        # the derivation owns no inference surface).
        for similarity_token in ("difflib", "SequenceMatcher", "levenshtein", "jaro_winkler"):
            assert similarity_token not in source, (
                f"the FU4 contract contains a similarity / fuzzy "
                f"computation surface ({similarity_token!r}); the "
                "derivation is pure, deterministic, and bounded"
            )

    def test_no_v2_pricing_path_is_activated(self) -> None:
        """Machine Price / Reviewed Price behavior is byte-unchanged: the
        frozen aggregation surface owns no FU4 symbol, and the ceiling
        tier (NEEDS_REVIEW) is not pricing-eligible under the frozen
        summary contract."""
        from product_intelligence.research.aggregation import (
            aggregate_reviewed_listing_prices,
        )

        assert AuthorityTier.NEEDS_REVIEW not in PRICING_ELIGIBLE_TIERS
        assert aggregate_reviewed_listing_prices.__module__ == (
            "product_intelligence.research.aggregation"
        )
        for path in (
            PACKAGE_ROOT / "research" / "aggregation.py",
            PACKAGE_ROOT / "research" / "matching.py",
        ):
            source = path.read_text(encoding="utf-8")
            assert "semantic_authority_fu4" not in source
            assert "AuthorityDecisionV2FU4" not in source

    def test_the_fu4_module_names_no_vendor_or_caller_system(self) -> None:
        from tests.domain.test_domain_boundaries import (
            CALLER_TOKENS,
            VENDOR_TOKENS,
            _find_tokens,
        )

        source = FU4_MODULE_PATH.read_text(encoding="utf-8")
        assert not _find_tokens(source, VENDOR_TOKENS)
        assert not _find_tokens(source, CALLER_TOKENS)


class TestA7TwoTokenCoexistence:
    """A7: the SAME recorded inputs derive different units under the two
    coexisting tokens — documented per-binding behavior, pinned as a
    two-token row so it is never silent drift."""

    def test_count_only_bundle_pair_coexists_over_the_two_tokens(self) -> None:
        channel = _candidate_channel(quantity=3, raw_detail="bundle of 3")
        frozen_target = TargetSalesUnitEvidenceV2(
            TargetSalesUnitFormV2.BUNDLE, 3, TS
        )
        # Under the FU3 binding: the frozen count-based behavior
        # (PROVEN_EQUIVALENT — byte-unchanged).
        fu3_decision = derive_authority_tier_for_contract_fu4(
            AUTHORITY_CONTRACT_VERSION_V2_FU3,
            _v2(title=f"Has {REQUEST_MPN} in the title"),
            _match(),
            NO_CTX,
            _strong_profile(),
            sales_unit_channel=channel,
            target_unit_evidence=frozen_target,
        )
        assert isinstance(fu3_decision, AuthorityDecisionV2FU3)
        assert fu3_decision.sales_unit_authority is P
        assert fu3_decision.tier is AuthorityTier.AI_ASSISTED_COMPARABLE
        # Under the FU4 binding: the candidate composition is ABSENT
        # (count-only — a published count is not the complete identity
        # of a bundle) ⇒ UNPROVEN (the corrected restriction).
        fu4_decision = derive_authority_tier_for_contract_fu4(
            AUTHORITY_CONTRACT_VERSION_V2_FU4,
            _v2(title=f"Has {REQUEST_MPN} in the title"),
            _match(),
            NO_CTX,
            _strong_profile(),
            sales_unit_channel=channel,
            target_unit_evidence=frozen_target,
        )
        assert isinstance(fu4_decision, AuthorityDecisionV2FU4)
        assert not isinstance(fu4_decision, AuthorityDecisionV2FU3)
        assert fu4_decision.sales_unit_authority is U
        assert fu4_decision.tier is AuthorityTier.NEEDS_REVIEW
        assert AuthorityRuleV2FU4.CEILING_SALES_UNIT_NOT_PROVEN in (
            fu4_decision.fired_rules
        )
        # The determinations are RECORDED, never silent: the quantity
        # axis is CONSISTENT (both publish 3) but the composition axis
        # is ABSENT on both sides — the unit is UNPROVEN regardless.
        assert fu4_decision.quantity_axis_state is Q_CONSISTENT
        assert fu4_decision.candidate_composition_state is ABSENT
        assert fu4_decision.target_composition_state is ABSENT
        assert fu4_decision.candidate_completeness_attestation_digest is None
        assert fu4_decision.target_completeness_attestation_digest is None
        assert fu4_decision.quantity_attestation_digest is None
        # The unit-level coexistence (the same recorded input).
        assert (
            fu3.sales_unit_authority_from_channel(channel, frozen_target) is P
        )
        assert (
            derive_sales_unit_authority_fu4(
                channel,
                candidate_composition_from_channel(channel),
                frozen_target,
            )
            is U
        )
        assert (
            derive_sales_unit_authority_fu4(
                channel, None, frozen_target
            )
            is U
        )

    def test_count_only_bundle_pair_vs_uncounted_target_is_unproven_under_both(
        self,
    ) -> None:
        channel = _candidate_channel(quantity=3, raw_detail="bundle of 3")
        frozen_target = TargetSalesUnitEvidenceV2(
            TargetSalesUnitFormV2.BUNDLE, None, TS
        )
        assert (
            fu3.sales_unit_authority_from_channel(channel, frozen_target) is U
        )
        assert (
            derive_sales_unit_authority_fu4(channel, None, frozen_target) is U
        )


# ===========================================================================
# B. The composition evidence schema (construction-level)
# ===========================================================================


class TestB1FiveWayDistinctionAndMarkerRows:
    """B1: the five-way distinction + the marker rows (§4) over
    published text — each yields exactly the recorded extraction state
    (frozen) AND exactly the recorded FU4 evidence state with the
    attestation (or its absence) exact, the clause text verbatim, and
    the provenance (field + source + span / basis + digest) intact."""

    def test_bare_bundle_is_ambiguous_and_yields_no_record(self) -> None:
        result, channel = _extract("Gaming bundle")
        assert result.state is SalesUnitExtractionState.AMBIGUOUS_CUE
        assert channel.state is PackagingEvidenceStateV2.UNAVAILABLE
        assert candidate_composition_from_extraction(result) is None

    @pytest.mark.parametrize("phrase", ["bundle of 3", "3-unit bundle", "3 unit bundle"])
    def test_count_only_bundle_is_ambiguous_and_never_bound(self, phrase: str) -> None:
        result, channel = _extract(f"PC {phrase}")
        assert result.state is SalesUnitExtractionState.AMBIGUOUS_CUE
        assert channel.state is PackagingEvidenceStateV2.UNAVAILABLE
        assert candidate_composition_from_extraction(result) is None
        # The corpus-shaped channel (the extractor never produces it):
        # ABSENT with the count mirrored verbatim (B3).
        corpus_channel = _candidate_channel(quantity=3, raw_detail="bundle of 3")
        record = candidate_composition_from_channel(corpus_channel)
        assert record.state is ABSENT
        assert record.composition_clause is None
        assert record.channel_quantity == 3
        assert record.completeness_attestation is None
        assert record.basis is CandidateCompositionEvidenceBasisV2FU4.RECORDED_CHANNEL
        record.verify()

    def test_partially_described_contents_is_partial(self) -> None:
        for title in (
            "bundle: 2x RAM etc.",
            "bundle (2x RAM + 1x CPU",  # unclosed paren
            "bundle: 2x RAM + ",  # dangling separator
        ):
            result, channel = _extract(title)
            assert result.state is SalesUnitExtractionState.OBSERVED_UNAMBIGUOUS
            assert channel.kind is SalesUnitKindV2.BUNDLE
            record = candidate_composition_from_extraction(result)
            assert record is not None
            assert record.state is PART, title
            assert record.completeness_attestation is None
            assert record.composition_clause is not None
            record.verify()

    def test_closed_no_marker_is_syntactically_valid_without_attestation(
        self,
    ) -> None:
        """The CORRECTED demotion (Blocker B): a closed, marker-free
        clause is SYNTACTICALLY_VALID — completeness UNKNOWN — never
        ESTABLISHED."""
        for title in ("bundle: 2x RAM + 1x CPU", "bundle (2x RAM + 1x CPU)"):
            result, channel = _extract(title)
            record = candidate_composition_from_extraction(result)
            assert record is not None
            assert record.state is SV, title
            assert record.composition_clause == CLAUSE, title
            assert record.completeness_attestation is None
            assert record.basis is CandidateCompositionEvidenceBasisV2FU4.EXTRACTION_RESULT_V1
            assert record.extraction_result_digest == result.result_digest
            assert record.extraction_input_digest == result.input_digest
            assert record.channel_quantity is None
            record.verify()
            # The channel basis over the same published phrase agrees.
            channel_record = candidate_composition_from_channel(channel)
            assert channel_record.state is SV
            assert channel_record.composition_clause == CLAUSE

    def test_colon_form_marker_in_recorded_field_text_establishes(
        self,
    ) -> None:
        """The cue engine's COLON-form span stops at the first comma —
        the marker segment sits in the RECORDED field text immediately
        after the cue span (design §3.5b, extraction basis)."""
        result, channel = _extract("bundle: 2x RAM + 1x CPU, complete list")
        assert channel.raw_detail == "bundle: 2x RAM + 1x CPU"
        record = candidate_composition_from_extraction(result)
        assert record is not None
        assert record.state is EST
        assert record.composition_clause == CLAUSE
        att = record.completeness_attestation
        assert att is not None
        assert att.basis is CompletenessBasisV2FU4.PUBLISHED_COMPLETENESS_STATEMENT
        assert att.subject_side is EvidenceSideV2FU4.CANDIDATE
        assert att.source is CandidateEvidenceSourceV2.LISTING_TITLE
        assert att.attestation_text == ", complete list"
        assert att.clause_digest == _clause_digest(CLAUSE)
        att.verify()
        record.verify()

    def test_paren_form_marker_inside_the_clause_establishes(self) -> None:
        result, _channel = _extract("bundle (2x RAM + 1x CPU, all items listed)")
        record = candidate_composition_from_extraction(result)
        assert record is not None
        assert record.state is EST
        assert record.composition_clause == CLAUSE
        assert record.completeness_attestation is not None
        assert (
            record.completeness_attestation.attestation_text
            == ", all items listed"
        )
        record.verify()

    def test_incompleteness_marker_dominates_the_completeness_marker(
        self,
    ) -> None:
        """D5: a clause containing ``etc.`` is PARTIAL with NO
        attestation, even with a trailing ``complete list`` — the marker
        can never rescue an incomplete statement."""
        result, _channel = _extract("bundle: 2x RAM etc., complete list")
        record = candidate_composition_from_extraction(result)
        assert record is not None
        assert record.state is PART
        assert record.completeness_attestation is None
        # The channel basis over the same phrase agrees.
        corpus_channel = _candidate_channel(
            raw_detail="bundle: 2x RAM etc., complete list"
        )
        channel_record = candidate_composition_from_channel(corpus_channel)
        assert channel_record.state is PART
        assert channel_record.completeness_attestation is None

    def test_conflicting_title_and_structured_fields_contradict_published(
        self,
    ) -> None:
        result, channel = _extract(
            "bundle: 2x RAM + 1x CPU", "Bundle (2x SSD + cable)"
        )
        assert result.state is SalesUnitExtractionState.OBSERVED_UNAMBIGUOUS
        # The channel presents ONLY the primary (structured) clause.
        assert channel.raw_detail == "Bundle (2x SSD + cable)"
        record = candidate_composition_from_extraction(result)
        assert record is not None
        assert record.state is CONTR_PUB
        # Primary = the structured clause; the title clause is recorded
        # as the other published side (NONE adopted).
        assert record.composition_clause == "2x SSD + cable"
        assert record.additional_clauses == ("2x RAM + 1x CPU",)
        assert record.completeness_attestation is None
        assert record.source is CandidateEvidenceSourceV2.PUBLISHED_STRUCTURED_FIELD
        record.verify()

    def test_identical_repeated_clauses_are_one_clause_without_attestation(
        self,
    ) -> None:
        """Consistency ≠ completeness: same-page repetition (title +
        structured, byte-identical, no marker) is SYNTACTICALLY_VALID —
        the repeated clause is textual agreement with itself, never
        attested (design §6 item 4 correction)."""
        result, _channel = _extract(
            "bundle: 2x RAM + 1x CPU", "bundle: 2x RAM + 1x CPU"
        )
        record = candidate_composition_from_extraction(result)
        assert record is not None
        assert record.state is SV
        assert record.composition_clause == CLAUSE
        assert record.completeness_attestation is None
        record.verify()

    def test_repeated_clause_is_attested_only_by_the_primary_sources_marker(
        self,
    ) -> None:
        """A marker in a cue of a DIFFERENT field than the record's
        recorded (primary) clause is not adopted: the attestation must
        bind the record's source — the single clause stays
        SYNTACTICALLY_VALID (self-inconsistent publication)."""
        result, _channel = _extract(
            "bundle: 2x RAM + 1x CPU, complete list", "bundle: 2x RAM + 1x CPU"
        )
        record = candidate_composition_from_extraction(result)
        assert record is not None
        # Primary = the structured cue (no marker); the title's marker
        # sits in a different field ⇒ not adopted.
        assert record.source is CandidateEvidenceSourceV2.PUBLISHED_STRUCTURED_FIELD
        assert record.state is SV
        assert record.completeness_attestation is None
        record.verify()

    def test_a_truncated_copublication_of_the_same_clause_blocks_attestation(
        self,
    ) -> None:
        """The most-restrictive rule over identical repeated clauses:
        a truncated (unclosed paren) co-publication of the same clause
        form is PARTIAL and blocks the attestation — the single clause
        stands PARTIAL for audit, never ESTABLISHED (fail closed)."""
        result, channel = _extract(
            "bundle (2x RAM + 1x CPU", "bundle (2x RAM + 1x CPU, complete list)"
        )
        assert result.state is SalesUnitExtractionState.OBSERVED_UNAMBIGUOUS
        record = candidate_composition_from_extraction(result)
        assert record is not None
        assert record.state is PART
        assert record.composition_clause == CLAUSE
        assert record.completeness_attestation is None
        record.verify()
        # And it can never contribute to PROVEN_EQUIVALENT (the record is
        # presented over its OWN mapped channel — the FU1 binding).
        assert (
            derive_sales_unit_authority_fu4(
                channel, record, _target_established()
            )
            is U
        )


class TestB2EmptyMarkersNeverEstablish:
    @pytest.mark.parametrize(
        "title",
        [
            "bundle:",  # title-final empty colon marker
            "bundle ()",  # empty paren marker
            "bundle: ",  # trailing whitespace
            "bundle (",  # unclosed, title-final
        ],
    )
    def test_empty_marker_shapes_never_establish(self, title: str) -> None:
        result, channel = _extract(title)
        record = candidate_composition_from_extraction(result)
        assert record is not None
        assert record.state in (ABSENT, PART), title
        assert record.composition_clause in (None, ""), title
        assert record.completeness_attestation is None
        record.verify()
        channel_record = candidate_composition_from_channel(channel)
        assert channel_record.state in (ABSENT, PART), title
        assert channel_record.completeness_attestation is None

    def test_syntactically_valid_constructor_refuses_truncated_clauses(self) -> None:
        valid = _candidate_record(None, CLAUSE, SV)
        for bad_clause in ("", "   ", "2x RAM +", "2x RAM + ", "2x RAM + 2x", "2x RAM etc."):
            with pytest.raises(ValueError):
                _make_candidate_record(
                    CandidateCompositionEvidenceBasisV2FU4.RECORDED_CHANNEL,
                    SV,
                    bad_clause,
                    SRC,
                    channel_quantity=None,
                )
        # The valid record verifies (the rejection is the clause's, not
        # the record's).
        valid.verify()

    def test_established_constructor_refuses_truncated_clauses(self) -> None:
        att = _make_attestation(
            EvidenceSideV2FU4.CANDIDATE,
            CompletenessBasisV2FU4.PUBLISHED_COMPLETENESS_STATEMENT,
            SRC,
            _clause_digest(CLAUSE),
            ", complete list",
        )
        for bad_clause in ("", "2x RAM +", "2x RAM etc."):
            with pytest.raises(ValueError):
                _make_candidate_record(
                    CandidateCompositionEvidenceBasisV2FU4.RECORDED_CHANNEL,
                    EST,
                    bad_clause,
                    SRC,
                    completeness_attestation=att,
                )

    def test_a_completeness_marker_cannot_rescue_a_dangling_residue(self) -> None:
        """D5 at the derivation-input level: the published statement
        "2x RAM + , complete list" ends on a dangling separator — the
        marker tail's residue is PARTIAL, recorded for audit, with NO
        attestation (never ESTABLISHED)."""
        record = candidate_composition_from_channel(
            _candidate_channel(raw_detail="bundle: 2x RAM + , complete list")
        )
        assert record.state is PART
        assert record.composition_clause == "2x RAM + , complete list"
        assert record.completeness_attestation is None
        # And it can never contribute to PROVEN_EQUIVALENT.
        assert (
            derive_sales_unit_authority_fu4(
                _candidate_channel(raw_detail="bundle: 2x RAM + , complete list"),
                record,
                _target_established(),
            )
            is U
        )


class TestB4ProvenanceRefusal:
    def test_candidate_record_refuses_non_extractor_sources(self) -> None:
        for source in (
            CandidateEvidenceSourceV2.SPECIFICATION_TEXT,
            CandidateEvidenceSourceV2.REVIEWED_PRODUCT_CONTEXT,
        ):
            with pytest.raises(ValueError, match="non-model"):
                _make_candidate_record(
                    CandidateCompositionEvidenceBasisV2FU4.RECORDED_CHANNEL,
                    SV,
                    CLAUSE,
                    source,
                )
            with pytest.raises(ValueError, match="non-model"):
                CandidateBundleCompositionEvidenceV2FU4(
                    BUNDLE_COMPOSITION_EVIDENCE_VERSION_FU4,
                    CandidateCompositionEvidenceBasisV2FU4.RECORDED_CHANNEL,
                    SV,
                    None,
                    CLAUSE,
                    (),
                    source,
                    None,
                    None,
                    None,
                    "0" * 63 + "1",  # channel-content binding (v2)
                    "0" * 64,
                )

    def test_target_record_refuses_candidate_source_classes(self) -> None:
        with pytest.raises(TypeError):
            _make_target_fu4(
                TargetSalesUnitFormV2.BUNDLE,
                None,
                CandidateEvidenceSourceV2.LISTING_TITLE,  # type: ignore[arg-type]
                CLAUSE,
                SV,
            )
        with pytest.raises(TypeError):
            TargetSalesUnitEvidenceV2FU4(
                BUNDLE_COMPOSITION_EVIDENCE_VERSION_FU4,
                TargetSalesUnitFormV2.BUNDLE,
                None,
                CandidateEvidenceSourceV2.PUBLISHED_STRUCTURED_FIELD,  # type: ignore[arg-type]
                None,
                None,
                None,
                "0" * 64,
            )

    def test_no_member_is_a_model_claim(self) -> None:
        # The bounded vocabularies contain no model-claim member.
        assert {s.value for s in CandidateEvidenceSourceV2} == {
            "PUBLISHED_STRUCTURED_FIELD",
            "LISTING_TITLE",
            "SPECIFICATION_TEXT",
            "REVIEWED_PRODUCT_CONTEXT",
        }
        assert fu4._CANDIDATE_NON_MODEL_SOURCES == (
            CandidateEvidenceSourceV2.LISTING_TITLE,
            CandidateEvidenceSourceV2.PUBLISHED_STRUCTURED_FIELD,
        )
        assert {s.value for s in TargetSalesUnitEvidenceSourceV2} == {
            "REVIEWED_TARGET_CONTEXT",
            "REQUEST_DESCRIPTION",
        }

    def test_basis_vocabulary_has_no_model_basis(self) -> None:
        assert {b.value for b in CompletenessBasisV2FU4} == {
            "PUBLISHED_COMPLETENESS_STATEMENT",
            "REVIEWED_COMPOSITION_ATTESTATION",
        }
        assert {r.value for r in QuantityNonMaterialityReasonV2FU4} == {
            "SUBJECT_SOURCE_STRUCTURALLY_WITHOUT_BUNDLE_COUNTS",
            "PUBLISHED_COUNT_NOT_UNIT_MULTIPLICITY",
        }


class TestB5Integrity:
    def test_a_tampered_evidence_record_is_refused_at_construction(self) -> None:
        valid = _candidate_record(None, CLAUSE, SV)
        # Clause edited, digest not recomputed: the constructor's
        # digest re-verification refuses it.
        with pytest.raises(BundleCompositionEvidenceIntegrityError):
            dataclasses.replace(valid, composition_clause="2x RAM + 1x SSD")
        # The valid record verifies.
        valid.verify()

    def test_construction_reverifies_the_digest(self) -> None:
        with pytest.raises(BundleCompositionEvidenceIntegrityError):
            _make_candidate_record(
                CandidateCompositionEvidenceBasisV2FU4.RECORDED_CHANNEL,
                SV,
                CLAUSE,
                SRC,
                schema_version=BUNDLE_COMPOSITION_EVIDENCE_VERSION_FU4,
            ).__class__(
                BUNDLE_COMPOSITION_EVIDENCE_VERSION_FU4,
                CandidateCompositionEvidenceBasisV2FU4.RECORDED_CHANNEL,
                SV,
                None,
                CLAUSE,
                (),
                SRC,
                None,
                None,
                None,
                "0" * 63 + "1",  # channel-content binding (v2)
                "0" * 64,  # digest does not verify
            )

    def test_presentation_reverification_catches_an_out_of_band_tamper(self) -> None:
        """A record tampered AFTER construction (bypassing the
        constructor) is refused at the derivation's presentation gate —
        no unit is derived from it."""
        valid = _candidate_record(None, CLAUSE, SV)
        channel = _candidate_channel()
        object.__setattr__(valid, "composition_clause", "2x RAM + 1x SSD")
        with pytest.raises(BundleCompositionEvidenceIntegrityError):
            derive_sales_unit_authority_fu4(channel, valid, _target_established())
        object.__setattr__(valid, "composition_clause", CLAUSE)
        # Restored: it verifies again (the gate is the digest, not a
        # one-shot flag).
        assert (
            derive_sales_unit_authority_fu4(channel, valid, _target_established())
            is U  # SV vs EST: one side completeness-unknown
        )

    def test_basis_digest_coherence_is_enforced(self) -> None:
        # A RECORDED_CHANNEL record claiming extraction digests.
        with pytest.raises(ValueError, match="no extraction digests"):
            _make_candidate_record(
                CandidateCompositionEvidenceBasisV2FU4.RECORDED_CHANNEL,
                SV,
                CLAUSE,
                SRC,
                extraction_result_digest="ab" * 32,
                extraction_input_digest="cd" * 32,
            )
        # An EXTRACTION_RESULT_V1 record missing its digests.
        with pytest.raises(ValueError, match="carries both extraction"):
            _make_candidate_record(
                CandidateCompositionEvidenceBasisV2FU4.EXTRACTION_RESULT_V1,
                SV,
                CLAUSE,
                SRC,
            )
        # Malformed digests.
        with pytest.raises(ValueError, match="hex digest"):
            _make_candidate_record(
                CandidateCompositionEvidenceBasisV2FU4.RECORDED_CHANNEL,
                SV,
                CLAUSE,
                SRC,
                extraction_result_digest=None,
                extraction_input_digest="XYZ",
            )

    def test_contradicted_published_coherence_is_enforced(self) -> None:
        # CONTRADICTED_PUBLISHED with additional_clauses == ().
        with pytest.raises(ValueError, match="non-empty set"):
            _make_candidate_record(
                CandidateCompositionEvidenceBasisV2FU4.RECORDED_CHANNEL,
                CONTR_PUB,
                CLAUSE,
                SRC,
            )
        # A clause set where "additional" equals primary.
        with pytest.raises(ValueError, match="differ from every other"):
            _make_candidate_record(
                CandidateCompositionEvidenceBasisV2FU4.RECORDED_CHANNEL,
                CONTR_PUB,
                CLAUSE,
                SRC,
                additional_clauses=(CLAUSE,),
            )
        # ABSENT carrying a clause.
        with pytest.raises(ValueError, match="carries no clause"):
            _make_candidate_record(
                CandidateCompositionEvidenceBasisV2FU4.RECORDED_CHANNEL,
                ABSENT,
                CLAUSE,
                SRC,
            )
        # SYNTACTICALLY_VALID carrying an attestation.
        att = _make_attestation(
            EvidenceSideV2FU4.CANDIDATE,
            CompletenessBasisV2FU4.PUBLISHED_COMPLETENESS_STATEMENT,
            SRC,
            _clause_digest(CLAUSE),
            ", complete list",
        )
        with pytest.raises(ValueError, match="NO completeness attestation"):
            _make_candidate_record(
                CandidateCompositionEvidenceBasisV2FU4.RECORDED_CHANNEL,
                SV,
                CLAUSE,
                SRC,
                completeness_attestation=att,
            )

    def test_a_tampered_extraction_result_produces_no_evidence_record(self) -> None:
        result, _channel = _extract("bundle: 2x RAM + 1x CPU")
        # Tamper out-of-band (bypassing the constructor): the
        # presentation gate (verify_integrity) refuses the result.
        object.__setattr__(result, "result_digest", "0" * 64)
        with pytest.raises(SalesUnitExtractionIntegrityError):
            candidate_composition_from_extraction(result)
        # The forged result also cannot map to a channel (the P2 gate).
        from product_intelligence.research import sales_unit_channel_from_extraction

        with pytest.raises(SalesUnitExtractionIntegrityError):
            sales_unit_channel_from_extraction(result)

    def test_a_record_claiming_provenance_the_channel_never_recorded(self) -> None:
        """The derivation's channel binding: a record whose source /
        channel_quantity disagree with the presented channel is an
        integrity error (no derivation input)."""
        record = _candidate_record(None, CLAUSE, SV)
        foreign_channel = _candidate_channel(
            source=CandidateEvidenceSourceV2.LISTING_TITLE,
            raw_detail="bundle: 2x RAM + 1x CPU",
        )
        with pytest.raises(BundleCompositionEvidenceIntegrityError, match="source"):
            derive_sales_unit_authority_fu4(foreign_channel, record, _target_established())
        mismatched_channel = _candidate_channel(quantity=2)
        with pytest.raises(
            BundleCompositionEvidenceIntegrityError, match="channel_quantity"
        ):
            derive_sales_unit_authority_fu4(
                mismatched_channel, record, _target_established()
            )


class TestB6Determinism:
    def test_equal_inputs_produce_byte_equal_records(self) -> None:
        result_a, channel_a = _extract("bundle: 2x RAM + 1x CPU, complete list")
        result_b, channel_b = _extract("bundle: 2x RAM + 1x CPU, complete list")
        assert result_a.result_digest == result_b.result_digest
        record_a = candidate_composition_from_extraction(result_a)
        record_b = candidate_composition_from_extraction(result_b)
        assert record_a == record_b
        assert record_a is not None and record_b is not None
        assert record_a.evidence_digest == record_b.evidence_digest
        assert record_a.canonical() == record_b.canonical()
        channel_record_a = candidate_composition_from_channel(channel_a)
        channel_record_b = candidate_composition_from_channel(channel_b)
        assert channel_record_a == channel_record_b
        assert channel_record_a.evidence_digest == channel_record_b.evidence_digest

    def test_the_canonical_order_of_additional_clauses_is_pinned(self) -> None:
        """CONTRADICTED_PUBLISHED: the primary clause is the channel
        mapping's primary cue (structured first, else first title span);
        the additional clauses are the OTHER published clauses in
        canonical order (extraction field order, then span order)."""
        result, channel = _extract(
            "bundle: AAA, bundle: BBB", "bundle: CCC"
        )
        assert channel.raw_detail == "bundle: CCC"
        record = candidate_composition_from_extraction(result)
        assert record is not None
        assert record.state is CONTR_PUB
        assert record.composition_clause == "CCC"
        assert record.additional_clauses == ("AAA", "BBB")
        record.verify()

    def test_the_derivation_is_deterministic_over_equal_inputs(self) -> None:
        # Equal inputs (the FU1 binding: the record is the construction
        # of the presented channel in BOTH derivations — same content,
        # separately constructed objects).
        channel = _candidate_established_channel()
        record = candidate_composition_from_channel(channel)
        target = _target_established()
        first = _tier(channel, record, target)
        second = _tier(
            _candidate_established_channel(),
            candidate_composition_from_channel(
                _candidate_established_channel()
            ),
            _target_established(),
        )
        assert first == second
        assert first.tier is AuthorityTier.AI_ASSISTED_COMPARABLE


class TestB7FrozenTargetUnderFu4:
    def test_the_frozen_target_record_is_read_as_composition_absent(self) -> None:
        """D18: a frozen target record is read exactly as its fields
        state — form + count, composition ABSENT (the field does not
        exist; no implicit upgrade)."""
        channel = _candidate_established_channel()
        record = candidate_composition_from_channel(channel)
        frozen_target = TargetSalesUnitEvidenceV2(
            TargetSalesUnitFormV2.BUNDLE, None, TS
        )
        decision = _tier(channel, record, frozen_target)
        assert decision.sales_unit_authority is U
        assert decision.target_composition_state is ABSENT
        assert decision.target_completeness_attestation_digest is None
        # The unit-level derivation agrees.
        assert (
            derive_sales_unit_authority_fu4(channel, record, frozen_target) is U
        )

    def test_non_bundle_target_forms_with_composition_fields_are_unconstructible(
        self,
    ) -> None:
        for form in (
            TargetSalesUnitFormV2.SINGLE_UNIT,
            TargetSalesUnitFormV2.PACK_QUANTITY,
            TargetSalesUnitFormV2.TRAY_OR_FACTORY_PACK,
        ):
            quantity = 4 if form is TargetSalesUnitFormV2.PACK_QUANTITY else None
            with pytest.raises(ValueError, match="bundle-only"):
                _make_target_fu4(form, quantity, TS, CLAUSE, SV)

    def test_a_bundle_target_record_requires_the_composition_state(self) -> None:
        with pytest.raises(ValueError, match="REQUIRES"):
            _make_target_fu4(TargetSalesUnitFormV2.BUNDLE, None, TS)
        with pytest.raises(ValueError, match="no CONTRADICTED_PUBLISHED"):
            _make_target_fu4(
                TargetSalesUnitFormV2.BUNDLE, None, TS, CLAUSE, CONTR_PUB
            )


class TestB8ClauseGrammarEdges:
    """B8: the grammar decides the TEXTUAL axis only (the attestation
    context is stated on every row)."""

    def test_multiset_equal_is_textual_agreement(self) -> None:
        # U20 when both sides ESTABLISHED (the record is the
        # construction of the presented channel — the FU1 binding).
        assert (
            derive_sales_unit_authority_fu4(
                _candidate_established_channel(),
                _candidate_established(),
                _target_established(clause="1x CPU + 2x RAM"),
            )
            is P
        )
        # U15 when either side unattested.
        assert (
            derive_sales_unit_authority_fu4(
                _candidate_channel(),
                _candidate_record(),
                _target_established(clause="1x CPU + 2x RAM"),
            )
            is U
        )

    def test_multiset_differ_is_material_when_both_established(self) -> None:
        assert (
            derive_sales_unit_authority_fu4(
                _candidate_established_channel(),
                _candidate_established(),
                _target_established(clause="2x RAM + 1x SSD"),
            )
            is C
        )
        assert (
            derive_sales_unit_authority_fu4(
                _candidate_channel(),
                _candidate_record(),
                _target_established(clause="2x RAM + 1x SSD"),
            )
            is U
        )

    def test_a_grammar_residual_is_never_material(self) -> None:
        # "2x RAM + 1x CPU (revised)" — the parenthesized qualifier is
        # residual: NOT fully parseable ⇒ T-DIFF-UNESTABLISHED ⇒ U21 when
        # both ESTABLISHED, U15 otherwise (never CONTRADICTED).
        assert (
            derive_sales_unit_authority_fu4(
                _candidate_established_channel(),
                _candidate_established(),
                _target_established(clause="2x RAM + 1x CPU (revised)"),
            )
            is U
        )
        assert (
            derive_sales_unit_authority_fu4(
                _candidate_channel(),
                _candidate_record(),
                _target_established(clause="2x RAM + 1x CPU (revised)"),
            )
            is U
        )

    def test_the_0034_shape_is_fully_parseable_but_unattested(self) -> None:
        """The committed corpus 0034 text carries no completeness marker
        ⇒ SYNTACTICALLY_VALID ⇒ UNPROVEN (U15) against a byte-identical
        target — and PROVEN (U19) when both sides are attested."""
        channel = _candidate_channel(raw_detail="GPU + power cables + bracket kit")
        record = candidate_composition_from_channel(channel)
        assert record.state is SV
        assert (
            derive_sales_unit_authority_fu4(
                channel,
                record,
                _target(state=SV, clause="GPU + power cables + bracket kit"),
            )
            is U
        )
        attested_channel = _candidate_channel(
            raw_detail="GPU + power cables + bracket kit, complete list"
        )
        attested_record = candidate_composition_from_channel(attested_channel)
        assert attested_record.state is EST
        assert (
            derive_sales_unit_authority_fu4(
                attested_channel,
                attested_record,
                _target_established(clause="GPU + power cables + bracket kit"),
            )
            is P
        )

    def test_a_non_canonical_quantity_is_not_fully_parseable(self) -> None:
        assert fu4._full_parse_clause("04x RAM") is None
        assert fu4._full_parse_clause("100000x RAM") is None
        assert (
            derive_sales_unit_authority_fu4(
                _candidate_channel(raw_detail="bundle: 04x RAM + 1x CPU"),
                candidate_composition_from_channel(
                    _candidate_channel(raw_detail="bundle: 04x RAM + 1x CPU")
                ),
                _target_established(clause="04x RAM + 1x CPU"),
            )
            is U
        )

    def test_a_trailing_incomplete_quantity_token_is_partial(self) -> None:
        record = candidate_composition_from_channel(
            _candidate_channel(raw_detail="bundle: 2x RAM + 1x CPU + 2x")
        )
        assert record.state is PART
        assert record.completeness_attestation is None


# ===========================================================================
# B9 / B10. The attestation constructors (Blocker B / Blocker A)
# ===========================================================================


class TestB9CompletenessAttestationConstructor:
    def test_a_candidate_side_record_cannot_carry_a_review_basis(self) -> None:
        with pytest.raises(ValueError, match="un-constructible"):
            _make_attestation(
                EvidenceSideV2FU4.CANDIDATE,
                CompletenessBasisV2FU4.REVIEWED_COMPOSITION_ATTESTATION,
                SRC,
                _clause_digest(CLAUSE),
                "review anchor",
            )

    def test_subject_side_source_class_coherence(self) -> None:
        # CANDIDATE subject + a target-side class.
        with pytest.raises(ValueError, match="frozen candidate non-model"):
            _make_attestation(
                EvidenceSideV2FU4.CANDIDATE,
                CompletenessBasisV2FU4.PUBLISHED_COMPLETENESS_STATEMENT,
                TS,
                _clause_digest(CLAUSE),
                ", complete list",
            )
        # TARGET subject + a candidate-side class.
        with pytest.raises(ValueError, match="frozen target classes"):
            _make_attestation(
                EvidenceSideV2FU4.TARGET,
                CompletenessBasisV2FU4.PUBLISHED_COMPLETENESS_STATEMENT,
                SRC,
                _clause_digest(CLAUSE),
                ", complete list",
            )

    def test_an_attestation_over_a_different_clause_is_an_integrity_error(self) -> None:
        # Inside an ESTABLISHED candidate record: the clause_digest must
        # bind the record's clause.
        foreign_att = _make_attestation(
            EvidenceSideV2FU4.CANDIDATE,
            CompletenessBasisV2FU4.PUBLISHED_COMPLETENESS_STATEMENT,
            SRC,
            _clause_digest("2x RAM + 1x SSD"),
            ", complete list",
        )
        with pytest.raises(BundleCompositionEvidenceIntegrityError, match="clause"):
            _candidate_record(None, CLAUSE, EST, foreign_att)
        # Same for the target-side record.
        foreign_target_att = _make_attestation(
            EvidenceSideV2FU4.TARGET,
            CompletenessBasisV2FU4.PUBLISHED_COMPLETENESS_STATEMENT,
            TS,
            _clause_digest("2x RAM + 1x SSD"),
            ", complete list",
        )
        with pytest.raises(BundleCompositionEvidenceIntegrityError, match="clause"):
            _make_target_fu4(
                TargetSalesUnitFormV2.BUNDLE,
                None,
                TS,
                CLAUSE,
                EST,
                foreign_target_att,
            )

    def test_a_published_basis_attestation_text_is_exactly_the_verbatim_marker(
        self,
    ) -> None:
        record = candidate_composition_from_channel(
            _candidate_channel(raw_detail="bundle: 2x RAM + 1x CPU, complete list")
        )
        assert record.state is EST
        att = record.completeness_attestation
        assert att is not None
        assert att.attestation_text == ", complete list"
        assert att.basis is CompletenessBasisV2FU4.PUBLISHED_COMPLETENESS_STATEMENT
        # The PUBLISHED basis is machine-constructed from the recorded
        # marker — never free text.
        record2 = candidate_composition_from_extraction(
            _extract("bundle: 2x RAM + 1x CPU, complete list")[0]
        )
        assert record2 is not None
        assert record2.completeness_attestation is not None
        assert record2.completeness_attestation.attestation_text == (
            ", complete list"
        )

    def test_a_tampered_attestation_is_refused(self) -> None:
        att = _make_attestation(
            EvidenceSideV2FU4.TARGET,
            CompletenessBasisV2FU4.REVIEWED_COMPOSITION_ATTESTATION,
            TS,
            _clause_digest(CLAUSE),
            "verified against the manufacturer-published bundle spec",
        )
        with pytest.raises(BundleCompositionEvidenceIntegrityError):
            dataclasses.replace(att, attestation_text="verified (edited)")
        # Out-of-band tamper: refused at presentation.
        object.__setattr__(att, "attestation_text", "forged determination")
        with pytest.raises(BundleCompositionEvidenceIntegrityError):
            att.verify()

    def test_an_attestation_over_a_partial_or_absent_clause_is_unconstructible(
        self,
    ) -> None:
        att = _make_attestation(
            EvidenceSideV2FU4.CANDIDATE,
            CompletenessBasisV2FU4.PUBLISHED_COMPLETENESS_STATEMENT,
            SRC,
            _clause_digest("2x RAM etc."),
            ", complete list",
        )
        with pytest.raises(ValueError, match="textually valid"):
            _candidate_record(None, "2x RAM etc.", EST, att)
        with pytest.raises(ValueError, match="carries no clause"):
            _candidate_record(None, "2x RAM etc.", ABSENT, att)

    def test_target_state_attestation_coherence(self) -> None:
        att = _make_attestation(
            EvidenceSideV2FU4.TARGET,
            CompletenessBasisV2FU4.REVIEWED_COMPOSITION_ATTESTATION,
            TS,
            _clause_digest(CLAUSE),
            "verified against the manufacturer-published bundle spec",
        )
        # ESTABLISHED with no coherent attestation.
        with pytest.raises(ValueError, match="verified completeness attestation"):
            _make_target_fu4(
                TargetSalesUnitFormV2.BUNDLE, None, TS, CLAUSE, EST
            )
        # SYNTACTICALLY_VALID with one.
        with pytest.raises(ValueError, match="NO completeness attestation"):
            _make_target_fu4(
                TargetSalesUnitFormV2.BUNDLE, None, TS, CLAUSE, SV, att
            )
        # A candidate-subject attestation in a target record.
        cand_att = _make_attestation(
            EvidenceSideV2FU4.CANDIDATE,
            CompletenessBasisV2FU4.PUBLISHED_COMPLETENESS_STATEMENT,
            SRC,
            _clause_digest(CLAUSE),
            ", complete list",
        )
        with pytest.raises(ValueError, match="subjects the TARGET side"):
            _make_target_fu4(
                TargetSalesUnitFormV2.BUNDLE, None, TS, CLAUSE, EST, cand_att
            )
        # A coherent attestation constructs.
        ok = _make_target_fu4(
            TargetSalesUnitFormV2.BUNDLE, None, TS, CLAUSE, EST, att
        )
        ok.verify()

    def test_an_empty_attestation_text_is_unconstructible(self) -> None:
        with pytest.raises(ValueError, match="non-empty"):
            _make_attestation(
                EvidenceSideV2FU4.TARGET,
                CompletenessBasisV2FU4.REVIEWED_COMPOSITION_ATTESTATION,
                TS,
                _clause_digest(CLAUSE),
                "",
            )

    def test_a_unknown_schema_version_is_unconstructible(self) -> None:
        # Version 2 is the shipped schema (the Q3-B5-P4-FU1 channel-
        # content binding amendment); anything else is unknown.
        with pytest.raises(ValueError, match="schema_version"):
            _make_attestation(
                EvidenceSideV2FU4.TARGET,
                CompletenessBasisV2FU4.REVIEWED_COMPOSITION_ATTESTATION,
                TS,
                _clause_digest(CLAUSE),
                "x",
                schema_version=3,
            )


class TestB10QuantityAttestationConstructor:
    def test_the_vocabulary_bounds(self) -> None:
        assert {r.value for r in QuantityNonMaterialityReasonV2FU4} == {
            "SUBJECT_SOURCE_STRUCTURALLY_WITHOUT_BUNDLE_COUNTS",
            "PUBLISHED_COUNT_NOT_UNIT_MULTIPLICITY",
        }
        assert {s.value for s in EvidenceSideV2FU4} == {"CANDIDATE", "TARGET"}
        # The source is exactly the two frozen non-model attestation
        # classes (the review process is the sole authority).
        with pytest.raises(ValueError, match="sole quantity-attestation"):
            _make_quantity_attestation(
                EvidenceSideV2FU4.TARGET,
                QuantityNonMaterialityReasonV2FU4.PUBLISHED_COUNT_NOT_UNIT_MULTIPLICITY,
                CandidateEvidenceSourceV2.LISTING_TITLE,  # type: ignore[arg-type]
                "x",
            )

    def test_an_empty_attestation_text_is_unconstructible(self) -> None:
        with pytest.raises(ValueError, match="non-empty"):
            _make_quantity_attestation(
                EvidenceSideV2FU4.TARGET,
                QuantityNonMaterialityReasonV2FU4.PUBLISHED_COUNT_NOT_UNIT_MULTIPLICITY,
                TS,
                "",
            )

    def test_a_tampered_attestation_is_refused_at_construction_and_presentation(
        self,
    ) -> None:
        att = _quantity_attestation(EvidenceSideV2FU4.TARGET)
        with pytest.raises(BundleCompositionEvidenceIntegrityError):
            dataclasses.replace(att, attestation_text="edited")
        object.__setattr__(att, "reason", QuantityNonMaterialityReasonV2FU4.PUBLISHED_COUNT_NOT_UNIT_MULTIPLICITY)
        with pytest.raises(BundleCompositionEvidenceIntegrityError):
            att.verify()

    def test_the_attestation_never_supplies_a_quantity_value(self) -> None:
        fields = {f.name for f in dataclasses.fields(QuantityCompletenessAttestationV2FU4)}
        assert fields == {
            "schema_version",
            "subject_side",
            "reason",
            "source",
            "attestation_text",
            "attestation_digest",
        }
        assert "quantity" not in fields and "value" not in fields

    def test_an_attestation_with_the_wrong_subject_side_is_an_integrity_error(
        self,
    ) -> None:
        channel = _candidate_established_channel(quantity=2)
        record = _candidate_established(quantity=2)
        # The missing side is the TARGET — the attestation must stand on
        # it.
        wrong_subject = _quantity_attestation(EvidenceSideV2FU4.CANDIDATE)
        with pytest.raises(
            BundleCompositionEvidenceIntegrityError, match="actually-missing side"
        ):
            derive_sales_unit_authority_fu4(
                channel, record, _target_established(), wrong_subject
            )
        # The right subject stands: ATTESTED_NOT_MATERIAL ⇒ PROVEN.
        assert (
            derive_sales_unit_authority_fu4(
                channel, record, _target_established(), _quantity_attestation(EvidenceSideV2FU4.TARGET)
            )
            is P
        )

    def test_an_attestation_over_a_non_asymmetric_axis_is_contract_misuse(
        self,
    ) -> None:
        att = _quantity_attestation(EvidenceSideV2FU4.TARGET)
        # Both publish.
        with pytest.raises(ValueError, match="asymmetric"):
            derive_sales_unit_authority_fu4(
                _candidate_established_channel(quantity=2),
                _candidate_established(quantity=2),
                _target_established(quantity=2),
                att,
            )
        # Both absent.
        with pytest.raises(ValueError, match="asymmetric"):
            derive_sales_unit_authority_fu4(
                _candidate_established_channel(),
                _candidate_established(),
                _target_established(),
                att,
            )
        # Over a non-bundle channel (there is no quantity axis at all).
        with pytest.raises(ValueError, match="bundle-only"):
            derive_sales_unit_authority_fu4(
                _channel(SalesUnitKindV2.PACK_QUANTITY, 4, "pack of 4"),
                None,
                TargetSalesUnitEvidenceV2(
                    TargetSalesUnitFormV2.PACK_QUANTITY, 4, TS
                ),
                att,
            )


class TestB11ChannelContentBindingFU1:
    """B11 (Q3-B5-P4-FU1 — the mandated adversarial matrix over the
    corrected presentation gate): the version-2 channel-content binding
    refuses cross-listing composition evidence substitution (a
    self-verifying digest is not proof of cross-record association),
    the published integer quantities compare by exact value (not
    object identity), and the association is re-verified at derivation
    time and enforced at construction time."""

    def test_same_source_and_quantity_different_raw_detail_is_refused(self) -> None:
        """Two channels with identical source and quantity but
        different published raw_detail (two listings): a record from
        listing A is refused over listing B's channel — even though
        source class, bundle form, and quantity all agree."""
        listing_a = _candidate_channel(quantity=3, raw_detail="bundle of 3")
        listing_b = _candidate_channel(quantity=3, raw_detail="bundle of 3 (SSD)")
        assert (
            listing_a.source is listing_b.source
            and listing_a.kind is listing_b.kind
            and listing_a.quantity == listing_b.quantity
            and listing_a.raw_detail != listing_b.raw_detail
        )
        record = candidate_composition_from_channel(listing_a)
        with pytest.raises(
            BundleCompositionEvidenceIntegrityError, match="does not belong"
        ):
            derive_sales_unit_authority_fu4(listing_b, record, None)
        # Over its OWN listing the same record stands (ABSENT ⇒ UNPROVEN).
        assert (
            derive_sales_unit_authority_fu4(
                listing_a,
                record,
                TargetSalesUnitEvidenceV2(TargetSalesUnitFormV2.BUNDLE, 3, TS),
            )
            is U
        )

    def test_an_extraction_record_from_listing_a_is_refused_over_listing_b(self) -> None:
        """EXTRACTION_RESULT_V1 basis: the record is digest-bound to
        the result AND to the result's mapped channel (the verifiable
        relationship extraction result → mapped channel → record); a
        record from listing A's result is refused over listing B's
        mapped channel — identical source class, bundle form, and
        quantity (both publish a marker-carrying bundle of no count),
        different publication."""
        result_a, channel_a = _extract("bundle: 2x RAM + 1x CPU, complete list")
        result_b, channel_b = _extract("bundle: 2x SSD + 1x cable, complete list")
        record_a = candidate_composition_from_extraction(result_a)
        assert record_a is not None and record_a.state is EST
        assert channel_a.source is channel_b.source
        assert channel_a.kind is channel_b.kind
        assert channel_a.quantity == channel_b.quantity
        assert channel_a.raw_detail != channel_b.raw_detail
        # Same listing: the association stands (PROVEN over the
        # attested-equal target).
        assert (
            derive_sales_unit_authority_fu4(
                channel_a, record_a, _target_established()
            )
            is P
        )
        # Cross-listing: the association fails (refused).
        with pytest.raises(
            BundleCompositionEvidenceIntegrityError, match="does not belong"
        ):
            derive_sales_unit_authority_fu4(
                channel_b, record_a, _target_established()
            )

    def test_separately_deserialized_equal_quantities_above_256_derive(self) -> None:
        """Blocker 2: two separately deserialized channels with equal
        published quantity greater than 256 (distinct ``int`` objects —
        small-int interning does not mask the comparison): the
        corrected gate compares by EXACT VALUE — the record of one
        deserialization stands over the other, and the derivation is
        content-deterministic (the old ``is not`` comparison refused
        this valid same-publication record)."""
        q1 = json.loads("300")
        q2 = json.loads("300")
        assert q1 == q2 and q1 is not q2  # the premise: distinct objects
        channel_1 = _candidate_established_channel(quantity=q1)
        channel_2 = _candidate_established_channel(quantity=q2)
        record = candidate_composition_from_channel(channel_1)
        assert record.channel_quantity == q2
        assert record.channel_quantity is not q2
        # SV / ABSENT shape (count-only): UNPROVEN over the frozen
        # same-count bundle target.
        plain_1 = _candidate_channel(quantity=q1)
        plain_2 = _candidate_channel(quantity=q2)
        plain_record = candidate_composition_from_channel(plain_1)
        assert (
            derive_sales_unit_authority_fu4(
                plain_2,
                plain_record,
                TargetSalesUnitEvidenceV2(
                    TargetSalesUnitFormV2.BUNDLE, q2, TS
                ),
            )
            is U
        )
        # ESTABLISHED shape: PROVEN over the attested-equal same-count
        # target — the value-equal quantities agree on the axis.
        assert (
            derive_sales_unit_authority_fu4(
                channel_2,
                record,
                _target_established(quantity=q2),
            )
            is P
        )

    def test_equal_quantity_but_different_composition(self) -> None:
        """Equal published quantity never substitutes for the
        composition axis: a material difference over two ESTABLISHED
        clauses ⇒ CONTRADICTED; one side unattested ⇒ UNPROVEN."""
        assert (
            derive_sales_unit_authority_fu4(
                _candidate_established_channel(quantity=2),
                _candidate_established(quantity=2),
                _target_established(clause="2x RAM + 1x SSD", quantity=2),
            )
            is C
        )
        assert (
            derive_sales_unit_authority_fu4(
                _candidate_channel(quantity=2),
                _candidate_record(quantity=2),
                _target(2, TS, "2x RAM + 1x SSD", SV),
            )
            is U
        )

    def test_a_tampered_channel_provenance_is_refused(self) -> None:
        """The presented channel's provenance tampered (same content
        otherwise): the record cannot stand over a channel that never
        recorded its source — refused at the derivation gate."""
        channel = _candidate_channel()
        record = candidate_composition_from_channel(channel)
        tampered = CandidateSalesUnitEvidenceV2(
            state=PackagingEvidenceStateV2.OBSERVED,
            kind=SalesUnitKindV2.BUNDLE,
            quantity=channel.quantity,
            raw_detail=channel.raw_detail,
            source=CandidateEvidenceSourceV2.LISTING_TITLE,
        )
        with pytest.raises(
            BundleCompositionEvidenceIntegrityError, match="provenance"
        ):
            derive_sales_unit_authority_fu4(tampered, record, None)

    def test_a_tampered_extraction_association_is_refused(self) -> None:
        """The EXTRACTION record's association anchors tampered:
        (a) out-of-band tamper of the recorded extraction result_digest
        — the record's own evidence digest no longer verifies at the
        presentation gate; (b) the record presented over the MAPPED
        CHANNEL OF A FOREIGN RESULT — the mapped-channel association
        fails. Either way: no derivation input."""
        result, channel = _extract("bundle: 2x RAM + 1x CPU, complete list")
        record = candidate_composition_from_extraction(result)
        assert record is not None
        # (a) Out-of-band tamper of the recorded extraction result_digest
        # (bypassing the constructor): the record's own evidence digest
        # no longer verifies at the presentation gate.
        object.__setattr__(record, "extraction_result_digest", "0" * 64)
        with pytest.raises(BundleCompositionEvidenceIntegrityError):
            derive_sales_unit_authority_fu4(channel, record, None)
        foreign_result, foreign_channel = _extract(
            "bundle: 2x SSD + 1x cable, complete list"
        )
        foreign_record = candidate_composition_from_extraction(foreign_result)
        with pytest.raises(
            BundleCompositionEvidenceIntegrityError, match="does not belong"
        ):
            derive_sales_unit_authority_fu4(channel, foreign_record, None)

    def test_a_valid_same_listing_channel_and_composition_derives(self) -> None:
        """The positive control: a record built over a channel, presented
        over that SAME channel, derives per the axes (no spurious
        refusal) — both bases."""
        channel = _candidate_established_channel()
        record = candidate_composition_from_channel(channel)
        assert (
            derive_sales_unit_authority_fu4(
                channel, record, _target_established()
            )
            is P
        )
        result, mapped = _extract("bundle: 2x RAM + 1x CPU, complete list")
        extraction_record = candidate_composition_from_extraction(result)
        assert (
            derive_sales_unit_authority_fu4(
                mapped, extraction_record, _target_established()
            )
            is P
        )

    def test_count_only_bundle_remains_unproven_under_the_corrected_gate(self) -> None:
        """The P2-FU1 rule survives the binding: a corpus-shaped
        count-only bundle (ABSENT composition) never proves against
        anything — including a target bundle of the same count."""
        channel = _candidate_channel(quantity=3, raw_detail="bundle of 3")
        record = candidate_composition_from_channel(channel)
        assert record is not None and record.state is ABSENT
        assert (
            derive_sales_unit_authority_fu4(
                channel,
                record,
                TargetSalesUnitEvidenceV2(
                    TargetSalesUnitFormV2.BUNDLE, 3, TS
                ),
            )
            is U
        )

    def test_historical_fu3_replay_is_unchanged_over_the_corrected_gate(self) -> None:
        """The historical FU3 replay is untouched by the FU1 binding
        (the frozen derivation has no composition axis — the same
        count-only bundle inputs still derive PROVEN_EQUIVALENT under
        the frozen rule; the coexistence pin, A7, stands)."""
        channel = _candidate_channel(quantity=3, raw_detail="bundle of 3")
        frozen_target = TargetSalesUnitEvidenceV2(
            TargetSalesUnitFormV2.BUNDLE, 3, TS
        )
        assert (
            fu3.sales_unit_authority_from_channel(channel, frozen_target) is P
        )

    def test_the_fu4_match_high_strong_ceiling_is_unchanged(self) -> None:
        """The MATCH + HIGH + STRONG ceiling invariants over the
        corrected gate: attested-equal ⇒ the automatic tier stands;
        the same shape WITHOUT the completeness statement ⇒ capped at
        NEEDS_REVIEW (the restriction is intact)."""
        channel = _candidate_established_channel()
        record = candidate_composition_from_channel(channel)
        stands = _tier(channel, record, _target_established())
        assert stands.tier is AuthorityTier.AI_ASSISTED_COMPARABLE
        assert stands.sales_unit_authority is P
        capped = _tier(
            _candidate_channel(), _candidate_record(), _target(None, TS, CLAUSE, SV)
        )
        assert capped.tier is AuthorityTier.NEEDS_REVIEW
        assert capped.sales_unit_authority is U
        assert AuthorityRuleV2FU4.CEILING_SALES_UNIT_NOT_PROVEN in capped.fired_rules

    def test_constructor_time_integrity_enforcement(self) -> None:
        """Schema v2 at construction: a malformed channel_content_digest
        is un-constructible; an out-of-band tamper of the binding field
        is refused at the presentation gate (the record's evidence
        digest covers it)."""
        with pytest.raises(ValueError, match="channel_content_digest"):
            _make_candidate_record(
                CandidateCompositionEvidenceBasisV2FU4.RECORDED_CHANNEL,
                SV,
                CLAUSE,
                SRC,
                channel_content_digest="not-a-digest",
            )
        channel = _candidate_channel()
        record = candidate_composition_from_channel(channel)
        object.__setattr__(record, "channel_content_digest", "0" * 64)
        with pytest.raises(BundleCompositionEvidenceIntegrityError):
            derive_sales_unit_authority_fu4(channel, record, None)

    def test_a_record_cannot_claim_a_clause_the_channel_never_published(
        self,
    ) -> None:
        """A hand-forged RECORDED_CHANNEL record — self-verifying, bound
        to the presented channel's content digest, matching source and
        quantity — claiming an ESTABLISHED composition the count-only
        publication never made: refused. The record must be EXACTLY the
        construction of the presented channel (the association is
        re-verified at derivation time, not assumed from the digest)."""
        channel = _candidate_channel(quantity=3, raw_detail="bundle of 3")
        att = _make_attestation(
            EvidenceSideV2FU4.CANDIDATE,
            CompletenessBasisV2FU4.PUBLISHED_COMPLETENESS_STATEMENT,
            SRC,
            _clause_digest(CLAUSE),
            ", complete list",
        )
        forged = _make_candidate_record(
            CandidateCompositionEvidenceBasisV2FU4.RECORDED_CHANNEL,
            EST,
            CLAUSE,
            SRC,
            channel_quantity=3,
            completeness_attestation=att,
            channel_content_digest=_canon_digest(channel.canonical()),
        )
        with pytest.raises(
            BundleCompositionEvidenceIntegrityError, match="not the construction"
        ):
            derive_sales_unit_authority_fu4(
                channel, forged, _target_established(quantity=3)
            )

    def test_a_handforged_extraction_record_cannot_claim_a_foreign_clause(
        self,
    ) -> None:
        """EXTRACTION_RESULT_V1 basis: a hand-forged record with
        fabricated (self-verifying) extraction digests, bound to the
        presented channel's content digest — but whose clause is not
        the determined form of the presented channel's published
        raw_detail: refused (the extraction → mapped-channel → record
        association's clause check)."""
        channel = _candidate_channel(raw_detail="bundle: 2x RAM + 1x CPU")
        att = _make_attestation(
            EvidenceSideV2FU4.CANDIDATE,
            CompletenessBasisV2FU4.PUBLISHED_COMPLETENESS_STATEMENT,
            SRC,
            _clause_digest("2x SSD + 1x cable"),
            ", complete list",
        )
        forged = _make_candidate_record(
            CandidateCompositionEvidenceBasisV2FU4.EXTRACTION_RESULT_V1,
            EST,
            "2x SSD + 1x cable",
            SRC,
            channel_quantity=None,
            completeness_attestation=att,
            extraction_result_digest="ab" * 32,
            extraction_input_digest="cd" * 32,
            channel_content_digest=_canon_digest(channel.canonical()),
        )
        with pytest.raises(
            BundleCompositionEvidenceIntegrityError, match="primary clause"
        ):
            derive_sales_unit_authority_fu4(
                channel, forged, _target_established(clause="2x SSD + 1x cable")
            )


# ===========================================================================
# C. The comparison rules (task item 4 — one row per mandated rule)
# ===========================================================================


class TestC1MissingPartialOrCompletenessUnknown:
    """C1: missing, partial, or completeness-unknown composition ⇒
    UNPROVEN (over every BUNDLE-form target shape; the form rule owns
    non-bundle targets)."""

    BUNDLE_TARGETS = {
        "frozen-no-count": TargetSalesUnitEvidenceV2(
            TargetSalesUnitFormV2.BUNDLE, None, TS
        ),
        "frozen-count-2": TargetSalesUnitEvidenceV2(
            TargetSalesUnitFormV2.BUNDLE, 2, TS
        ),
        "fu4-sv": _target(None, TS, CLAUSE, SV),
        "fu4-est": _target_established(),
        "fu4-part": _target(None, TS, "2x RAM etc.", PART),
    }

    @pytest.mark.parametrize("target", list(BUNDLE_TARGETS.values()), ids=list(BUNDLE_TARGETS.keys()))
    def test_candidate_absent_is_unproven(self, target) -> None:
        assert (
            derive_sales_unit_authority_fu4(
                _candidate_channel(), None, target
            )
            is U
        )

    @pytest.mark.parametrize("target", list(BUNDLE_TARGETS.values()), ids=list(BUNDLE_TARGETS.keys()))
    def test_candidate_partial_is_unproven(self, target) -> None:
        channel = _candidate_channel(raw_detail="bundle: 2x RAM etc.")
        record = candidate_composition_from_channel(channel)
        assert record is not None and record.state is PART
        assert derive_sales_unit_authority_fu4(channel, record, target) is U

    @pytest.mark.parametrize(
        "target",
        [
            _target(None, TS, CLAUSE, SV),
            _target_established(),
        ],
        ids=["target-sv", "target-est"],
    )
    def test_candidate_syntactically_valid_unattested_is_unproven(
        self, target
    ) -> None:
        # Even against a byte-identical, quantity-satisfied, ESTABLISHED
        # target — Blocker B: textual agreement is not completeness.
        assert (
            derive_sales_unit_authority_fu4(
                _candidate_channel(), _candidate_record(), target
            )
            is U
        )

    @pytest.mark.parametrize(
        "target",
        [
            TargetSalesUnitEvidenceV2(TargetSalesUnitFormV2.BUNDLE, None, TS),
            TargetSalesUnitEvidenceV2(TargetSalesUnitFormV2.BUNDLE, 2, TS),
        ],
        ids=["frozen-no-count", "frozen-count-2"],
    )
    def test_target_absent_frozen_record_is_unproven(self, target) -> None:
        # The "contents known on only one side" regression, preserved
        # under FU4 (the frozen target record carries no composition
        # field — D18: read as composition-ABSENT, no implicit upgrade).
        # The FU1 binding: each record is presented over its OWN
        # channel (the EST record's marker-carrying channel).
        for record, rec_channel in (
            (None, _candidate_channel()),
            (_candidate_record(), _candidate_channel()),
            (_candidate_established(), _candidate_established_channel()),
        ):
            assert derive_sales_unit_authority_fu4(rec_channel, record, target) is U

    @pytest.mark.parametrize(
        "target",
        [
            _target(None, TS, "2x RAM etc.", PART),
            _target(None, TS, "bundle (2x RAM", PART),
        ],
        ids=["target-partial-marker", "target-partial-unclosed"],
    )
    def test_target_partial_is_unproven(self, target) -> None:
        assert (
            derive_sales_unit_authority_fu4(
                _candidate_established_channel(), _candidate_established(), target
            )
            is U
        )
        assert (
            derive_sales_unit_authority_fu4(
                _candidate_channel(), _candidate_record(), target
            )
            is U
        )

    def test_target_syntactically_valid_vs_candidate_established_is_unproven(
        self,
    ) -> None:
        assert (
            derive_sales_unit_authority_fu4(
                _candidate_established_channel(),
                _candidate_established(),
                _target(None, TS, CLAUSE, SV),
            )
            is U
        )

    def test_form_rule_owns_non_bundle_targets(self) -> None:
        # U9: a bundle channel vs a non-bundle target is CONTRADICTED
        # before any composition is read (the default single unit
        # included) — for EVERY candidate composition shape (the FU1
        # binding: each record over its OWN channel).
        for record, rec_channel in (
            (None, _candidate_channel()),
            (_candidate_record(), _candidate_channel()),
            (_candidate_established(), _candidate_established_channel()),
        ):
            assert (
                derive_sales_unit_authority_fu4(
                    rec_channel, record, None
                )
                is C
            )
            assert (
                derive_sales_unit_authority_fu4(
                    rec_channel,
                    record,
                    TargetSalesUnitEvidenceV2(
                        TargetSalesUnitFormV2.PACK_QUANTITY, 4, TS
                    ),
                )
                is C
            )


class TestC2EqualCountsWithoutComposition:
    def test_equal_counts_without_composition_is_unproven_under_fu4(self) -> None:
        channel = _candidate_channel(quantity=3, raw_detail="bundle of 3")
        record = candidate_composition_from_channel(channel)
        assert record is not None and record.state is ABSENT
        frozen_target = TargetSalesUnitEvidenceV2(
            TargetSalesUnitFormV2.BUNDLE, 3, TS
        )
        assert (
            derive_sales_unit_authority_fu4(channel, record, frozen_target) is U
        )
        # The same inputs under the frozen FU3 contract: PROVEN (the
        # coexistence pin — A7).
        assert (
            fu3.sales_unit_authority_from_channel(channel, frozen_target) is P
        )

    def test_count_only_vs_uncounted_target_is_unproven_under_both(self) -> None:
        channel = _candidate_channel(quantity=3, raw_detail="bundle of 3")
        frozen_target = TargetSalesUnitEvidenceV2(
            TargetSalesUnitFormV2.BUNDLE, None, TS
        )
        assert (
            fu3.sales_unit_authority_from_channel(channel, frozen_target) is U
        )
        assert (
            derive_sales_unit_authority_fu4(channel, None, frozen_target) is U
        )


class TestC3MateriallyEstablishedDifference:
    def test_material_difference_over_two_established_clauses_contradicts(
        self,
    ) -> None:
        decision = _tier(
            _candidate_established_channel(),
            _candidate_established(),
            _target_established(clause="2x RAM + 1x SSD"),
        )
        assert decision.sales_unit_authority is C
        assert decision.tier is AuthorityTier.NEEDS_REVIEW
        assert AuthorityRuleV2FU4.CEILING_SALES_UNIT_CONTRADICTED in decision.fired_rules
        assert decision.tier is not AuthorityTier.AI_ASSISTED_COMPARABLE
        # The determinations are recorded.
        assert decision.candidate_composition_state is EST
        assert decision.target_composition_state is EST

    def test_a_material_difference_without_both_side_completeness_is_unproven(
        self,
    ) -> None:
        # One side UNATTESTED (SYNTACTICALLY_VALID): the safe direction —
        # a material difference without both-side completeness is never
        # a contradiction (U15).
        assert (
            derive_sales_unit_authority_fu4(
                _candidate_channel(),
                _candidate_record(),
                _target_established(clause="2x RAM + 1x SSD"),
            )
            is U
        )
        assert (
            derive_sales_unit_authority_fu4(
                _candidate_established_channel(),
                _candidate_established(),
                _target(None, TS, "2x RAM + 1x SSD", SV),
            )
            is U
        )

    def test_the_q3b4_4_1_invariant_holds_over_material_difference(self) -> None:
        # NEVER AI_ASSISTED_COMPARABLE; the hand-constructed decision
        # with that tier + unit is un-constructible (the constructor
        # invariant).
        with pytest.raises(ValueError, match="contradicted"):
            AuthorityDecisionV2FU4(
                tier=AuthorityTier.AI_ASSISTED_COMPARABLE,
                fired_rules=frozenset(
                    {
                        AuthorityRuleV2FU4.STATE_POLICY_DETERMINISTIC,
                        AuthorityRuleV2FU4.SEMANTIC_OUTCOME_MATRIX,
                    }
                ),
                product_evidence_quality=ProductEvidenceQuality.STRONG,
                relationship_authority=RelationshipAuthority.NOT_APPLICABLE,
                identity_resolution_bound=fu3.IdentityResolutionBoundV2.PART_NUMBER,
                sales_unit_authority=C,
                quantity_axis_state=Q_BOTH_UNPUBLISHED,
                candidate_composition_state=EST,
                target_composition_state=EST,
                candidate_completeness_attestation_digest="ab" * 32,
                target_completeness_attestation_digest="cd" * 32,
                quantity_attestation_digest=None,
            )


class TestC4UnestablishedDifference:
    def test_unestablished_difference_is_unproven_never_contradicted(self) -> None:
        assert (
            derive_sales_unit_authority_fu4(
                _candidate_established_channel(),
                _candidate_established(),
                _target_established(clause="2x RAM + 1x CPU (revised)"),
            )
            is U
        )
        decision = _tier(
            _candidate_established_channel(),
            _candidate_established(),
            _target_established(clause="2x RAM + 1x CPU (revised)"),
        )
        assert decision.tier is AuthorityTier.NEEDS_REVIEW
        assert AuthorityRuleV2FU4.CEILING_SALES_UNIT_NOT_PROVEN in decision.fired_rules


class TestC5EqualCompleteCompositions:
    """C5: equal complete compositions with sufficient provenance ⇒
    PROVEN_EQUIVALENT (U19 / U20 — the CORRECTED D6 conjunction)."""

    @pytest.mark.parametrize(
        "candidate_raw,target_clause,quantity_attestation,expected_axis",
        [
            # U19 byte-identical, Q = CONSISTENT.
            ("bundle: 2x RAM + 1x CPU, complete list", CLAUSE, 2, Q_CONSISTENT),
            # U19 byte-identical, Q = BOTH_UNPUBLISHED.
            ("bundle: 2x RAM + 1x CPU, complete list", CLAUSE, None, Q_BOTH_UNPUBLISHED),
            # U20 multiset-equal (byte-different), Q = BOTH_UNPUBLISHED.
            ("bundle: 2x RAM + 1x CPU, complete list", "1x CPU + 2x RAM", None, Q_BOTH_UNPUBLISHED),
            # U20 multiset-equal, Q = CONSISTENT.
            ("bundle: 2x RAM + 1x CPU, complete list", "1x CPU + 2x RAM", 2, Q_CONSISTENT),
        ],
        ids=["u19-consistent", "u19-both-unpublished", "u20-both-unpublished", "u20-consistent"],
    )
    def test_proven_over_independent_attestations(
        self,
        candidate_raw: str,
        target_clause: str,
        quantity_attestation: int | None,
        expected_axis: BundleQuantityAxisStateV2FU4,
    ) -> None:
        channel = _candidate_channel(quantity=quantity_attestation, raw_detail=candidate_raw)
        record = candidate_composition_from_channel(channel)
        assert record is not None and record.state is EST
        target = _target_established(clause=target_clause, quantity=quantity_attestation)
        decision = _tier(channel, record, target)
        assert decision.sales_unit_authority is P
        # The tier STANDS under MATCH + HIGH + STRONG (no ceiling fired).
        assert decision.tier is AuthorityTier.AI_ASSISTED_COMPARABLE
        assert AuthorityRuleV2FU4.CEILING_SALES_UNIT_NOT_PROVEN not in decision.fired_rules
        assert AuthorityRuleV2FU4.CEILING_SALES_UNIT_CONTRADICTED not in decision.fired_rules
        # The determinations are recorded.
        assert decision.quantity_axis_state is expected_axis
        assert decision.candidate_composition_state is EST
        assert decision.target_composition_state is EST
        assert decision.candidate_completeness_attestation_digest is not None
        assert decision.target_completeness_attestation_digest is not None
        assert decision.quantity_attestation_digest is None

    def test_attested_equal_with_an_asymmetric_quantity_gap_proves_with_the_attestation(
        self,
    ) -> None:
        # The FU1 binding: the record is presented over the SAME channel
        # it was constructed from (the marker-carrying publication).
        channel = _candidate_established_channel(quantity=2)
        record = candidate_composition_from_channel(channel)
        target = _target_established()  # target quantity None
        att = _quantity_attestation(EvidenceSideV2FU4.TARGET)
        decision = _tier(channel, record, target, att)
        assert decision.sales_unit_authority is P
        assert decision.quantity_axis_state is Q_ATTESTED
        assert decision.quantity_attestation_digest == att.attestation_digest
        assert decision.tier is AuthorityTier.AI_ASSISTED_COMPARABLE

    def test_the_same_row_with_the_count_rule_violated_contradicts(self) -> None:
        decision = _tier(
            _candidate_established_channel(quantity=2),
            _candidate_established(quantity=2),
            _target_established(quantity=3),
        )
        assert decision.sales_unit_authority is C
        assert decision.quantity_axis_state is Q_CONTRADICTED
        assert decision.tier is AuthorityTier.NEEDS_REVIEW
        assert AuthorityRuleV2FU4.CEILING_SALES_UNIT_CONTRADICTED in decision.fired_rules

    def test_the_same_row_with_one_side_unattested_is_unproven(self) -> None:
        # The Blocker B negative twin of the positive row.
        assert (
            derive_sales_unit_authority_fu4(
                _candidate_channel(), _candidate_record(), _target_established()
            )
            is U
        )
        assert (
            derive_sales_unit_authority_fu4(
                _candidate_established_channel(), _candidate_established(), _target(None, TS, CLAUSE, SV)
            )
            is U
        )


class TestC6ConflictingTitleAndStructured:
    def test_conflicting_published_contents_fail_closed_for_every_target(self) -> None:
        # The FU1 binding: the EXTRACTION record is presented over its
        # OWN mapped channel (the frozen P2 mapping of the result).
        result, channel = _extract("bundle: 2x RAM + 1x CPU", "Bundle (2x SSD + cable)")
        record = candidate_composition_from_extraction(result)
        assert record is not None and record.state is CONTR_PUB
        # UNPROVEN for EVERY target shape — including a target whose
        # clause equals one of the published clauses and is itself
        # ESTABLISHED (a self-contradiction is unpinned in both
        # directions, never adopted as a conflict against the target).
        targets = (
            None,
            TargetSalesUnitEvidenceV2(TargetSalesUnitFormV2.BUNDLE, None, TS),
            _target(None, TS, "2x SSD + cable", EST,
                    _make_attestation(EvidenceSideV2FU4.TARGET,
                                      CompletenessBasisV2FU4.PUBLISHED_COMPLETENESS_STATEMENT,
                                      TS, _clause_digest("2x SSD + cable"), ", complete list")),
            _target(None, TS, CLAUSE, EST,
                    _make_attestation(EvidenceSideV2FU4.TARGET,
                                      CompletenessBasisV2FU4.PUBLISHED_COMPLETENESS_STATEMENT,
                                      TS, _clause_digest(CLAUSE), ", complete list")),
        )
        for target in targets:
            if target is None or (
                isinstance(target, TargetSalesUnitEvidenceV2)
                and target.form is not TargetSalesUnitFormV2.BUNDLE
            ):
                continue
            assert derive_sales_unit_authority_fu4(channel, record, target) is U
        # Non-bundle targets: the form rule (CONTRADICTED).
        assert (
            derive_sales_unit_authority_fu4(
                channel,
                record,
                TargetSalesUnitEvidenceV2(TargetSalesUnitFormV2.PACK_QUANTITY, 4, TS),
            )
            is C
        )
        decision = _tier(
            channel,
            record,
            _target(None, TS, CLAUSE, EST,
                    _make_attestation(EvidenceSideV2FU4.TARGET,
                                      CompletenessBasisV2FU4.PUBLISHED_COMPLETENESS_STATEMENT,
                                      TS, _clause_digest(CLAUSE), ", complete list")),
        )
        assert decision.tier is AuthorityTier.NEEDS_REVIEW
        assert AuthorityRuleV2FU4.CEILING_SALES_UNIT_NOT_PROVEN in decision.fired_rules

    def test_the_frozen_kind_quantity_conflict_shape_is_repinned(self) -> None:
        """At the channel level, the frozen P2 rule: kind or quantity
        conflict across the fields ⇒ CONTRADICTED_CUES ⇒ recorded
        absence ⇒ UNPROVEN (unchanged)."""
        result, channel = _extract("pack of 4", "tray of 10")
        assert result.state is SalesUnitExtractionState.CONTRADICTED_CUES
        assert channel.state is PackagingEvidenceStateV2.UNAVAILABLE
        assert candidate_composition_from_extraction(result) is None
        assert (
            derive_sales_unit_authority_fu4(channel, None, None) is U
        )


class TestC7FormBeforeContents:
    @pytest.mark.parametrize(
        "target",
        [
            None,
            TargetSalesUnitEvidenceV2(
                TargetSalesUnitFormV2.SINGLE_UNIT, None, TS
            ),
            TargetSalesUnitEvidenceV2(
                TargetSalesUnitFormV2.PACK_QUANTITY, 4, TS
            ),
            TargetSalesUnitEvidenceV2(
                TargetSalesUnitFormV2.TRAY_OR_FACTORY_PACK, None, TS
            ),
        ],
        ids=["default-single", "single", "pack", "tray"],
    )
    def test_an_established_composition_never_explains_away_a_form_mismatch(
        self, target
    ) -> None:
        assert (
            derive_sales_unit_authority_fu4(
                _candidate_established_channel(), _candidate_established(), target
            )
            is C
        )


class TestC8MPNInClauseNonInference:
    def test_clauses_differing_only_in_an_embedded_part_number(self) -> None:
        # The items differ — no identity weight given: material
        # difference ⇒ CONTRADICTED when both sides ESTABLISHED (the
        # FU1 binding: each record is presented over the SAME channel
        # it was constructed from).
        assert (
            derive_sales_unit_authority_fu4(
                _candidate_channel(raw_detail="bundle: 1x SSD M.2 9A0, complete list"),
                candidate_composition_from_channel(
                    _candidate_channel(raw_detail="bundle: 1x SSD M.2 9A0, complete list")
                ),
                _target_established(clause="1x SSD M.2 9A0"),
            )
            is P
        )
        assert (
            derive_sales_unit_authority_fu4(
                _candidate_channel(raw_detail="bundle: 1x SSD M.2 9A0, complete list"),
                candidate_composition_from_channel(
                    _candidate_channel(raw_detail="bundle: 1x SSD M.2 9A0, complete list")
                ),
                _target_established(clause="1x SSD M.2 9B0"),
            )
            is C
        )
        # The same with one side unattested ⇒ UNPROVEN (U15).
        assert (
            derive_sales_unit_authority_fu4(
                _candidate_channel(raw_detail="bundle: 1x SSD M.2 9A0"),
                candidate_composition_from_channel(
                    _candidate_channel(raw_detail="bundle: 1x SSD M.2 9A0")
                ),
                _target_established(clause="1x SSD M.2 9B0"),
            )
            is U
        )

    def test_the_comparison_takes_no_mpn_or_price_input(self) -> None:
        params = set(inspect.signature(derive_sales_unit_authority_fu4).parameters)
        assert params == {
            "channel",
            "candidate_composition",
            "target_evidence",
            "quantity_attestation",
        }


class TestC9ModelOutputNonInference:
    def test_a_model_claim_of_bundle_agreement_changes_nothing(self) -> None:
        """A scripted evaluation whose MATCH + HIGH + STRONG claims
        agreement changes NOTHING under the FU4 dispatch: the unit
        derivation's inputs are signature-pinned (channel + evidence
        records + the quantity attestation's bounded fields only)."""
        channel = _candidate_channel(quantity=3, raw_detail="bundle of 3")
        # The model says MATCH with the packaging conflict class cleared
        # (the recorded shape): the unit is still UNPROVEN and the tier
        # still capped.
        decision = _tier(channel, None, TargetSalesUnitEvidenceV2(
            TargetSalesUnitFormV2.BUNDLE, 3, TS
        ))
        assert decision.sales_unit_authority is U
        assert decision.tier is AuthorityTier.NEEDS_REVIEW
        assert AuthorityRuleV2FU4.CEILING_SALES_UNIT_NOT_PROVEN in decision.fired_rules
        # A model claim of "the compositions are complete" — even over
        # byte-identical clauses — never attests: no model-claim member
        # exists in the attestation vocabulary, and the evaluation has
        # no path into the unit derivation.
        decision2 = _tier(
            _candidate_channel(),
            _candidate_record(),
            _target(None, TS, CLAUSE, SV),
            evaluation=_match(),
        )
        assert decision2.sales_unit_authority is U

    def test_the_authority_rule_trail_never_gains_a_model_sourced_rule(self) -> None:
        decision = _tier(
            _candidate_established_channel(), _candidate_established(), _target_established()
        )
        assert {r.value for r in decision.fired_rules} <= {
            r.value for r in AuthorityRuleV2FU4
        }


class TestC10QuantityCompletenessAxis:
    """C10: one row per axis state over textually-agreed,
    both-ESTABLISHED clauses (Blocker A)."""

    def test_q_consistent_proves(self) -> None:
        decision = _tier(
            _candidate_established_channel(quantity=2),
            _candidate_established(quantity=2),
            _target_established(quantity=2),
        )
        assert decision.sales_unit_authority is P
        assert decision.quantity_axis_state is Q_CONSISTENT

    def test_q_both_unpublished_proves(self) -> None:
        decision = _tier(
            _candidate_established_channel(), _candidate_established(), _target_established()
        )
        assert decision.sales_unit_authority is P
        assert decision.quantity_axis_state is Q_BOTH_UNPUBLISHED

    def test_q_contradicted_contradicts_even_without_completeness(self) -> None:
        # The count difference over the same stated composition is not
        # gated by completeness (U16 — the pre-correction broadening).
        decision = _tier(
            _candidate_channel(quantity=2),
            _candidate_record(quantity=2),
            _target(3, TS, CLAUSE, SV),
        )
        assert decision.sales_unit_authority is C
        assert decision.quantity_axis_state is Q_CONTRADICTED
        # Both ESTABLISHED as well.
        assert (
            derive_sales_unit_authority_fu4(
                _candidate_established_channel(quantity=2),
                _candidate_established(quantity=2),
                _target_established(quantity=3),
            )
            is C
        )

    def test_q_undetermined_is_unproven_the_blocker_a_defect_row(self) -> None:
        """The shape the PRE-CORRECTION design derived PROVEN over
        ("at least one side publishes none — no inference"): byte-
        identical clauses, both sides attested complete, candidate
        quantity 2, target quantity None ⇒ UNPROVEN (U18)."""
        decision = _tier(
            _candidate_established_channel(quantity=2),
            _candidate_established(quantity=2),
            _target_established(),
        )
        assert decision.sales_unit_authority is U
        assert decision.quantity_axis_state is Q_UNDETERMINED
        assert decision.tier is AuthorityTier.NEEDS_REVIEW
        assert AuthorityRuleV2FU4.CEILING_SALES_UNIT_NOT_PROVEN in decision.fired_rules

    def test_q_attested_not_material_proves(self) -> None:
        att = _quantity_attestation(EvidenceSideV2FU4.TARGET)
        decision = _tier(
            _candidate_established_channel(quantity=2),
            _candidate_established(quantity=2),
            _target_established(),
            att,
        )
        assert decision.sales_unit_authority is P
        assert decision.quantity_axis_state is Q_ATTESTED
        assert decision.quantity_attestation_digest == att.attestation_digest
        # The reverse roles (the candidate side missing — attested by
        # the review record with subject_side = CANDIDATE, T10).
        att_candidate = _quantity_attestation(EvidenceSideV2FU4.CANDIDATE)
        assert (
            derive_sales_unit_authority_fu4(
                _candidate_established_channel(),
                _candidate_established(),
                _target_established(quantity=2),
                att_candidate,
            )
            is P
        )

    def test_the_parsed_entry_count_is_never_compared_against_the_published_count(
        self,
    ) -> None:
        """D17a / T4: the 3-entry clause with published quantity 3
        derives purely from the published values; and a 1-entry clause
        with published quantity 3 is NOT contradicted by its own entry
        count (the count-vs-entry-count check is forbidden)."""
        three_entry = "1x A + 1x B + 1x C"
        assert (
            derive_sales_unit_authority_fu4(
                _candidate_channel(quantity=3, raw_detail=f"bundle: {three_entry}, complete list"),
                candidate_composition_from_channel(
                    _candidate_channel(quantity=3, raw_detail=f"bundle: {three_entry}, complete list")
                ),
                _target_established(clause=three_entry, quantity=3),
            )
            is P
        )
        one_entry = "1x A"
        assert (
            derive_sales_unit_authority_fu4(
                _candidate_channel(quantity=3, raw_detail=f"bundle: {one_entry}, complete list"),
                candidate_composition_from_channel(
                    _candidate_channel(quantity=3, raw_detail=f"bundle: {one_entry}, complete list")
                ),
                _target_established(clause=one_entry, quantity=3),
            )
            is P
        )

    def test_no_quantity_is_inferred_from_absence_mpn_price_or_model_output(
        self,
    ) -> None:
        params = set(inspect.signature(derive_sales_unit_authority_fu4).parameters)
        assert params == {
            "channel",
            "candidate_composition",
            "target_evidence",
            "quantity_attestation",
        }
        # The axis uses ONLY the published counts: a clause full of
        # numbers never supplies a quantity (F2's row re-pinned at the
        # axis level).
        channel = _candidate_channel(raw_detail="bundle: 1x 960GB SSD + 1x 4TB HDD")
        record = candidate_composition_from_channel(channel)
        assert record.channel_quantity is None
        decision = _tier(
            channel,
            record,
            _target_established(clause="1x 960GB SSD + 1x 4TB HDD"),
        )
        assert decision.quantity_axis_state is Q_BOTH_UNPUBLISHED


class TestC11CompletenessAxis:
    def test_byte_identical_no_attestation_both_quantities_absent(self) -> None:
        """Decision-matrix case 1: textual agreement without
        completeness is not equivalence (U15)."""
        decision = _tier(
            _candidate_channel(), _candidate_record(), _target(None, TS, CLAUSE, SV)
        )
        assert decision.sales_unit_authority is U
        assert decision.candidate_composition_state is SV
        assert decision.target_composition_state is SV

    def test_byte_identical_one_side_attested(self) -> None:
        """Case 7's shape over byte-identity: one-sided completeness
        never proves (U15)."""
        assert (
            derive_sales_unit_authority_fu4(
                _candidate_channel(), _candidate_record(), _target_established()
            )
            is U
        )
        assert (
            derive_sales_unit_authority_fu4(
                _candidate_established_channel(), _candidate_established(), _target(None, TS, CLAUSE, SV)
            )
            is U
        )

    def test_multiset_equal_incomplete_source_evidence(self) -> None:
        """Case 7: both clauses fully parse and the multisets are equal
        (byte-different) but one side lacks a verified completeness
        attestation ⇒ UNPROVEN — multiset equality establishes textual
        agreement, never completeness (D16 corrected)."""
        assert (
            derive_sales_unit_authority_fu4(
                _candidate_channel(raw_detail="bundle: 2x RAM + 1x CPU, complete list"),
                candidate_composition_from_channel(
                    _candidate_channel(raw_detail="bundle: 2x RAM + 1x CPU, complete list")
                ),
                _target(None, TS, "1x CPU + 2x RAM", SV),
            )
            is U
        )

    def test_both_attested_material_difference_contradicts(self) -> None:
        """Case 6."""
        assert (
            derive_sales_unit_authority_fu4(
                _candidate_established_channel(),
                _candidate_established(),
                _target_established(clause="2x RAM + 1x SSD"),
            )
            is C
        )

    def test_one_attested_material_difference_is_unproven(self) -> None:
        """Case 6's safe direction: a material difference requires
        completeness on BOTH sides; one-sided completeness never
        contradicts."""
        assert (
            derive_sales_unit_authority_fu4(
                _candidate_channel(),
                _candidate_record(),
                _target_established(clause="2x RAM + 1x SSD"),
            )
            is U
        )

    def test_same_page_repetition_is_not_completeness(self) -> None:
        """The §6 identical-repetition correction: the repeated clause
        is SYNTACTICALLY_VALID, NO attestation (consistency is textual
        agreement with itself) ⇒ UNPROVEN against a byte-identical
        ESTABLISHED target."""
        result, channel = _extract(
            "bundle: 2x RAM + 1x CPU", "bundle: 2x RAM + 1x CPU"
        )
        record = candidate_composition_from_extraction(result)
        assert record is not None
        assert record.state is SV
        assert record.completeness_attestation is None
        assert (
            derive_sales_unit_authority_fu4(channel, record, _target_established())
            is U
        )


class TestC12CopiedAttestation:
    def test_the_constructible_copied_shape_derives_per_the_axes(self) -> None:
        """Case 9: a target review attestation over a clause byte
        identical to the candidate's — the derivation cannot detect the
        copy (T3 / T3'): the pair derives per the axes (PROVEN
        reachable when the attestations stand as recorded). The
        contract performs NO copy detection (no similarity /
        provenance-of-text computation exists in the module)."""
        # The FU1 binding: the candidate record is presented over the
        # SAME channel it was constructed from.
        channel = _candidate_established_channel()
        record = candidate_composition_from_channel(channel)
        # The "copy": the target's clause is byte-identical to the
        # candidate's, attested by a REVIEWED determination.
        target = _target(
            None,
            TS,
            CLAUSE,
            EST,
            _make_attestation(
                EvidenceSideV2FU4.TARGET,
                CompletenessBasisV2FU4.REVIEWED_COMPOSITION_ATTESTATION,
                TS,
                _clause_digest(CLAUSE),
                "verified against the candidate listing's publication",
            ),
        )
        decision = _tier(channel, record, target)
        assert decision.sales_unit_authority is P
        # (c) The audit surface records both attestations — the
        # reviewer's inspection surface (basis + source live on the
        # records; the digests on the decision).
        assert decision.candidate_completeness_attestation_digest == (
            record.completeness_attestation.attestation_digest
        )
        assert decision.target_completeness_attestation_digest == (
            target.completeness_attestation.attestation_digest
        )

    def test_the_detectable_launderings_are_unconstructible_or_refused(self) -> None:
        """(d) The detectable launderings: a candidate-side
        completeness claim with a REVIEWED basis; a target-side
        attestation with a candidate source class; an attestation over a
        different clause (the clause_digest mismatch); a subject-side
        mismatch — each is un-constructible / integrity-refused (B9 /
        B10)."""
        with pytest.raises(ValueError, match="un-constructible"):
            _make_attestation(
                EvidenceSideV2FU4.CANDIDATE,
                CompletenessBasisV2FU4.REVIEWED_COMPOSITION_ATTESTATION,
                SRC,
                _clause_digest(CLAUSE),
                "copied review",
            )
        with pytest.raises(ValueError, match="frozen target classes"):
            _make_attestation(
                EvidenceSideV2FU4.TARGET,
                CompletenessBasisV2FU4.REVIEWED_COMPOSITION_ATTESTATION,
                SRC,
                _clause_digest(CLAUSE),
                "copied review",
            )
        with pytest.raises(BundleCompositionEvidenceIntegrityError, match="clause"):
            _target(
                None,
                TS,
                CLAUSE,
                EST,
                _make_attestation(
                    EvidenceSideV2FU4.TARGET,
                    CompletenessBasisV2FU4.REVIEWED_COMPOSITION_ATTESTATION,
                    TS,
                    _clause_digest("a different clause"),
                    "copied review",
                ),
            )
        with pytest.raises(BundleCompositionEvidenceIntegrityError, match="actually-missing"):
            derive_sales_unit_authority_fu4(
                _candidate_established_channel(quantity=2),
                _candidate_established(quantity=2),
                _target_established(),
                _quantity_attestation(EvidenceSideV2FU4.CANDIDATE),
            )

    def test_no_similarity_computation_exists_in_the_module(self) -> None:
        source = FU4_MODULE_PATH.read_text(encoding="utf-8")
        for token in ("difflib", "SequenceMatcher", "levenshtein", "jaro_winkler"):
            assert token not in source


# ===========================================================================
# D. Tier, overlay, and the Q3-B4 §4.1 invariant
# ===========================================================================


class TestD1TierInvariants:
    def test_silent_multi_bundle_needs_review(self) -> None:
        """No cue at all: channel UNAVAILABLE ⇒ UNPROVEN ⇒
        NEEDS_REVIEW (CEILING_SALES_UNIT_NOT_PROVEN) under MATCH + HIGH
        + STRONG + clean."""
        decision = _tier(UNAVAILABLE, None, None)
        assert decision.sales_unit_authority is U
        assert decision.tier is AuthorityTier.NEEDS_REVIEW
        assert AuthorityRuleV2FU4.CEILING_SALES_UNIT_NOT_PROVEN in decision.fired_rules

    def test_count_only_pair_needs_review(self) -> None:
        decision = _tier(
            _candidate_channel(quantity=3, raw_detail="bundle of 3"),
            None,
            TargetSalesUnitEvidenceV2(TargetSalesUnitFormV2.BUNDLE, 3, TS),
        )
        assert decision.sales_unit_authority is U
        assert decision.tier is AuthorityTier.NEEDS_REVIEW
        assert AuthorityRuleV2FU4.CEILING_SALES_UNIT_NOT_PROVEN in decision.fired_rules

    def test_equal_unattested_text_needs_review(self) -> None:
        """Blocker B: the pre-correction design derived PROVEN here."""
        decision = _tier(
            _candidate_channel(),
            _candidate_record(),
            _target(None, TS, CLAUSE, SV),
        )
        assert decision.sales_unit_authority is U
        assert decision.tier is AuthorityTier.NEEDS_REVIEW
        assert AuthorityRuleV2FU4.CEILING_SALES_UNIT_NOT_PROVEN in decision.fired_rules

    def test_asymmetric_unattested_quantity_over_attested_equal_text_needs_review(
        self,
    ):
        """Blocker A: byte-identical clauses, both attested, candidate
        quantity 2, target quantity None ⇒ UNPROVEN ⇒ NEEDS_REVIEW."""
        decision = _tier(
            _candidate_established_channel(quantity=2),
            _candidate_established(quantity=2),
            _target_established(),
        )
        assert decision.sales_unit_authority is U
        assert decision.quantity_axis_state is Q_UNDETERMINED
        assert decision.tier is AuthorityTier.NEEDS_REVIEW
        assert AuthorityRuleV2FU4.CEILING_SALES_UNIT_NOT_PROVEN in decision.fired_rules

    def test_material_difference_over_two_attested_compositions_needs_review(
        self,
    ) -> None:
        decision = _tier(
            _candidate_established_channel(),
            _candidate_established(),
            _target_established(clause="2x RAM + 1x SSD"),
        )
        assert decision.sales_unit_authority is C
        assert decision.tier is AuthorityTier.NEEDS_REVIEW
        assert AuthorityRuleV2FU4.CEILING_SALES_UNIT_CONTRADICTED in decision.fired_rules

    def test_attested_equal_quantity_satisfied_stands(self) -> None:
        """The positive row: a proven unit leaves the automatic tier
        standing (the firewall's own design — pricing eligibility still
        requires the separately gated W1 guard + qualification;
        V2_AUTHORITY_QUALIFIED False)."""
        decision = _tier(
            _candidate_established_channel(), _candidate_established(), _target_established()
        )
        assert decision.sales_unit_authority is P
        assert decision.tier is AuthorityTier.AI_ASSISTED_COMPARABLE
        assert AuthorityRuleV2FU4.CEILING_SALES_UNIT_NOT_PROVEN not in decision.fired_rules
        assert AuthorityRuleV2FU4.CEILING_SALES_UNIT_CONTRADICTED not in decision.fired_rules

    @pytest.mark.parametrize(
        "unit,expected_tier,expected_rule",
        [
            (U, AuthorityTier.NEEDS_REVIEW, AuthorityRuleV2FU4.CEILING_SALES_UNIT_NOT_PROVEN),
            (C, AuthorityTier.NEEDS_REVIEW, AuthorityRuleV2FU4.CEILING_SALES_UNIT_CONTRADICTED),
            (P, AuthorityTier.AI_ASSISTED_COMPARABLE, None),
        ],
        ids=["unproven", "contradicted", "proven"],
    )
    def test_the_match_high_strong_ceiling_invariants(
        self,
        unit: SalesUnitAuthorityV2,
        expected_tier: AuthorityTier,
        expected_rule: AuthorityRuleV2FU4 | None,
    ) -> None:
        """The Q3-B4 §4.1 invariant over the FU4 decision type: MATCH +
        HIGH + STRONG + clean + U1 exact-identifier never reaches a
        pricing-eligible automatic tier while the unit is not PROVEN."""
        if unit is U:
            decision = _tier(_candidate_channel(), _candidate_record(), _target(None, TS, CLAUSE, SV))
        elif unit is C:
            decision = _tier(
                _candidate_established_channel(), _candidate_established(),
                _target_established(clause="2x RAM + 1x SSD"),
            )
        else:
            decision = _tier(
                _candidate_established_channel(), _candidate_established(), _target_established()
            )
        assert decision.sales_unit_authority is unit
        assert decision.tier is expected_tier
        if expected_rule is not None:
            assert expected_rule in decision.fired_rules
        assert (expected_rule is not None) == (
            AuthorityTier.AI_ASSISTED_COMPARABLE not in (decision.tier,)
        )


class TestD2HumanOverlay:
    def test_a_firewall_capped_bundle_candidate_confirmed_derives_human_confirmed(
        self,
    ) -> None:
        """D2: a firewall-capped bundle candidate (UNPROVEN) confirmed
        by a recorded HumanReviewStateV2 CONFIRM derives HUMAN_CONFIRMED
        under the FU4 dispatch (precedence HARD_CONFLICT >
        HUMAN_CONFIRMED > AI unchanged)."""
        channel = _candidate_channel()
        record = _candidate_record()
        target = _target(None, TS, CLAUSE, SV)
        without = _tier(channel, record, target)
        assert without.tier is AuthorityTier.NEEDS_REVIEW
        confirmed = _tier(
            channel, record, target, human=HumanReviewStateV2.CONFIRMED
        )
        assert confirmed.tier is AuthorityTier.HUMAN_CONFIRMED
        assert AuthorityRuleV2FU4.HUMAN_CONFIRMED_APPLIED in confirmed.fired_rules
        assert AuthorityRuleV2FU4.CEILING_SALES_UNIT_NOT_PROVEN not in (
            confirmed.fired_rules
        )
        rejected = _tier(
            channel, record, target, human=HumanReviewStateV2.REJECTED
        )
        assert rejected.tier is AuthorityTier.HUMAN_REJECTED

    def test_a_model_reported_always_hard_bundle_conflict_still_supersedes(
        self,
    ) -> None:
        """A model-reported ALWAYS_HARD BUNDLE conflict supersedes the
        overlay (the frozen rule, unchanged)."""
        channel = _candidate_channel()
        record = _candidate_record()
        target = _target(None, TS, CLAUSE, SV)
        decision = _tier(
            channel,
            record,
            target,
            evaluation=_eval(
                V2SemanticDecision.NO_MATCH,
                V2Confidence.HIGH,
                frozenset({ConflictClass.BUNDLE}),
            ),
            human=HumanReviewStateV2.CONFIRMED,
        )
        assert decision.tier is AuthorityTier.HARD_CONFLICT
        assert decision.tier is not AuthorityTier.HUMAN_CONFIRMED

    def test_a_generic_semantic_match_never_infers_confirmation(self) -> None:
        decision = _tier(_candidate_channel(), _candidate_record(), _target(None, TS, CLAUSE, SV))
        assert decision.tier is not AuthorityTier.HUMAN_CONFIRMED
        assert AuthorityRuleV2FU4.HUMAN_CONFIRMED_APPLIED not in decision.fired_rules


class TestD3CeilingInvariants:
    def test_the_ceiling_never_lifts_and_fires_only_on_the_automatic_tier(
        self,
    ) -> None:
        """U3 + no relation (the frozen requirement ceiling already
        holds NEEDS_REVIEW) + UNPROVEN unit: no redundant ceiling rule —
        the frozen audit trail stands exactly (restrict only)."""
        u3 = _v2(mpn="ABC")
        decision = derive_authority_tier_fu4(
            u3,
            UNAVAILABLE,
            _match(),
            NO_CTX,
            _strong_profile(),
            target_unit_evidence=None,
            candidate_composition=None,
        )
        assert decision.tier is AuthorityTier.NEEDS_REVIEW
        assert AuthorityRuleV2FU4.CEILING_IDENTIFIER_RELATIONSHIP_NOT_ESTABLISHED in decision.fired_rules
        assert AuthorityRuleV2FU4.CEILING_SALES_UNIT_NOT_PROVEN not in decision.fired_rules
        # The trail projects back onto the frozen vocabulary exactly.
        frozen = derive_authority_tier(u3, _match(), NO_CTX, _strong_profile())
        assert decision.frozen_fired_rules == frozen.fired_rules

    def test_the_ceiling_never_touches_machine_verified(self) -> None:
        v_exact = _v2(mpn=REQUEST_MPN)
        decision = derive_authority_tier_fu4(
            v_exact,
            _candidate_channel(),
            _match(),
            NO_CTX,
            _strong_profile(),
            target_unit_evidence=TargetSalesUnitEvidenceV2(
                TargetSalesUnitFormV2.BUNDLE, None, TS
            ),
            candidate_composition=None,
        )
        assert decision.tier is AuthorityTier.MACHINE_VERIFIED
        assert decision.sales_unit_authority is U
        assert AuthorityRuleV2FU4.CEILING_SALES_UNIT_NOT_PROVEN not in decision.fired_rules

    @pytest.mark.parametrize(
        "tier,unit,rule",
        [
            (
                AuthorityTier.AI_ASSISTED_COMPARABLE,
                U,
                AuthorityRuleV2FU4.CEILING_SALES_UNIT_NOT_PROVEN,
            ),
            (
                AuthorityTier.AI_ASSISTED_COMPARABLE,
                C,
                AuthorityRuleV2FU4.CEILING_SALES_UNIT_CONTRADICTED,
            ),
        ],
        ids=["ai-assisted-unproven", "ai-assisted-contradicted"],
    )
    def test_the_unproven_and_contradicted_exposures_are_unconstructible(
        self, tier, unit, rule
    ) -> None:
        with pytest.raises(ValueError, match="never hold the automatic"):
            AuthorityDecisionV2FU4(
                tier=tier,
                fired_rules=frozenset({rule}),
                product_evidence_quality=ProductEvidenceQuality.STRONG,
                relationship_authority=RelationshipAuthority.NOT_APPLICABLE,
                identity_resolution_bound=fu3.IdentityResolutionBoundV2.PART_NUMBER,
                sales_unit_authority=unit,
                quantity_axis_state=None,
                candidate_composition_state=None,
                target_composition_state=None,
                candidate_completeness_attestation_digest=None,
                target_completeness_attestation_digest=None,
                quantity_attestation_digest=None,
            )

    @pytest.mark.parametrize(
        "tier,unit,rule",
        [
            (AuthorityTier.NEEDS_REVIEW, C, AuthorityRuleV2FU4.CEILING_SALES_UNIT_NOT_PROVEN),
            (AuthorityTier.MACHINE_VERIFIED, U, AuthorityRuleV2FU4.CEILING_SALES_UNIT_NOT_PROVEN),
            (AuthorityTier.NEEDS_REVIEW, U, AuthorityRuleV2FU4.CEILING_SALES_UNIT_CONTRADICTED),
            (AuthorityTier.HARD_CONFLICT, C, AuthorityRuleV2FU4.CEILING_SALES_UNIT_CONTRADICTED),
        ],
        ids=["wrong-unit-not-proven", "wrong-tier-not-proven", "wrong-unit-contradicted", "wrong-tier-contradicted"],
    )
    def test_the_ceiling_rules_only_fire_with_their_unit_state_on_needs_review(
        self, tier, unit, rule
    ) -> None:
        with pytest.raises(ValueError, match="fires only"):
            AuthorityDecisionV2FU4(
                tier=tier,
                fired_rules=frozenset({rule}),
                product_evidence_quality=ProductEvidenceQuality.LIMITED,
                relationship_authority=RelationshipAuthority.NOT_APPLICABLE,
                identity_resolution_bound=fu3.IdentityResolutionBoundV2.NONE,
                sales_unit_authority=unit,
                quantity_axis_state=None,
                candidate_composition_state=None,
                target_composition_state=None,
                candidate_completeness_attestation_digest=None,
                target_completeness_attestation_digest=None,
                quantity_attestation_digest=None,
            )

    def test_the_fu4_decision_is_type_distinguishable_from_the_fu3_decision(
        self,
    ) -> None:
        decision = _tier(_candidate_channel(), _candidate_record(), _target(None, TS, CLAUSE, SV))
        assert type(decision) is AuthorityDecisionV2FU4
        assert not isinstance(decision, AuthorityDecisionV2FU3)
        # The non-bundle audit fields are exactly None.
        pack_decision = _tier(
            _channel(SalesUnitKindV2.PACK_QUANTITY, 4),
            None,
            TargetSalesUnitEvidenceV2(TargetSalesUnitFormV2.PACK_QUANTITY, 4, TS),
        )
        assert pack_decision.quantity_axis_state is None
        assert pack_decision.candidate_composition_state is None
        assert pack_decision.target_composition_state is None
        assert pack_decision.candidate_completeness_attestation_digest is None
        assert pack_decision.target_completeness_attestation_digest is None
        assert pack_decision.quantity_attestation_digest is None


# ===========================================================================
# E. Binding / replay / qualification (contract phase)
# ===========================================================================


class TestE1ContractPhaseRegistries:
    def test_the_registries_are_exactly_as_frozen(self) -> None:
        # A4 / E1: the production codec + replay registries, the live
        # record pin, the harness registries, and the qualification
        # marker — all unchanged by the contract phase (the full pin
        # set lives in TestA4RegistriesAndReachability).
        assert supported_contract_bindings() == (
            V1_CONTRACT_BINDING,
            V2_CONTRACT_BINDING,
        )
        from product_intelligence.semantic.contract_v2_1 import (
            V2_1_CONTRACT_BINDING,
        )

        assert V2_1_CONTRACT_BINDING == (
            "V2",
            "2.1",
            1,
            1,
            AUTHORITY_CONTRACT_VERSION_V2_FU3,
        )

    def test_the_committed_2_1_binding_is_still_the_fu3_one(self) -> None:
        """The existing 2.1 binding byte-unchanged alongside (no FU4
        successor binding exists at the contract phase — D13)."""
        from product_intelligence.semantic import contract_v2_1

        assert (
            contract_v2_1.V2_1_CONTRACT_BINDING[4]
            == AUTHORITY_CONTRACT_VERSION_V2_FU3
        )
        assert AUTHORITY_CONTRACT_VERSION_V2_FU4 not in getattr(
            contract_v2_1, "__dict__", {}
        ).values()


class TestE2RegistrationStepNotExecuted:
    def test_no_binding_registration_happened_in_the_contract_phase(self) -> None:
        """E2 (the specified registration step is NOT executed): no
        FU4 entry in any registry — the harness knows exactly two
        production bindings; the codec exactly two adapters' bindings;
        no corpus 1.2.0 artifact; no CORPUS_VERSION_2_1_FU4 constant."""
        from product_intelligence.evaluation.semantic_v2 import corpus as harness_corpus
        from product_intelligence.evaluation.semantic_v2 import fixtures as harness_fixtures

        assert all(
            binding[4] != AUTHORITY_CONTRACT_VERSION_V2_FU4
            for binding in harness_corpus.BINDING_CORPUS_VERSIONS
        )
        assert not hasattr(harness_fixtures, "CORPUS_VERSION_2_1_FU4")
        for name in ("corpus_2_1_fu4.json", "manifest_2_1_fu4.json"):
            assert not (
                REPO_ROOT / "evaluation" / "semantic_v2_qualification" / name
            ).exists()


# ===========================================================================
# F. False-positive resistance (the never-infer list, FU4 edition)
# ===========================================================================


class TestF1NeverInfer:
    def test_no_composition_is_derived_from_commercial_facts(self) -> None:
        """Two observations identical in every examined published field
        but different in price / availability / condition / seller / offer
        URL produce the SAME published cues and the SAME composition
        evidence (the commercial facts are recorded in the input digest
        — the examined input — but no composition fact is derived from
        them)."""
        from product_intelligence.research import extract_sales_unit_evidence

        base = _observation(title="bundle: 2x RAM + 1x CPU, complete list")
        variant = dataclasses.replace(
            base,
            price_text="999",
            availability_text="Backorder",
            condition_text="Refurbished",
            seller_text="Some Seller",
            offer_url_text="https://example.com/other-offer",
        )
        result_a = extract_sales_unit_evidence(base)
        result_b = extract_sales_unit_evidence(variant)
        assert result_a.cues == result_b.cues
        assert result_a.state is SalesUnitExtractionState.OBSERVED_UNAMBIGUOUS
        record_a = candidate_composition_from_extraction(result_a)
        record_b = candidate_composition_from_extraction(result_b)
        assert record_a is not None and record_b is not None
        assert record_a.state == record_b.state
        assert record_a.composition_clause == record_b.composition_clause
        assert record_a.completeness_attestation is not None
        assert record_a.completeness_attestation.attestation_text == (
            record_b.completeness_attestation.attestation_text
        )
        assert record_a.source == record_b.source

    def test_the_raw_reference_is_never_read(self) -> None:
        """Two observations identical in every named field but with
        different opaque raw references are the same extraction input
        (AD-040: no business rule parses the raw reference)."""
        from product_intelligence.research import extract_sales_unit_evidence

        base = _observation(title="bundle: 2x RAM + 1x CPU")
        variant = dataclasses.replace(
            base, raw_reference="opaque reference the extractor never reads"
        )
        result_a = extract_sales_unit_evidence(base)
        result_b = extract_sales_unit_evidence(variant)
        assert result_a.input_digest == result_b.input_digest
        assert result_a.result_digest == result_b.result_digest

    def test_the_identifier_fields_are_set_aside_never_evidence(self) -> None:
        from product_intelligence.research import extract_sales_unit_evidence

        result = extract_sales_unit_evidence(
            _observation(mpn="4PACK-SSD-001", sku="2-BUNDLE-001", title="Plain product")
        )
        assert result.state is SalesUnitExtractionState.NO_PACKAGING_PUBLISHED
        assert candidate_composition_from_extraction(result) is None

    def test_the_model_output_is_never_an_input(self) -> None:
        params = set(inspect.signature(derive_sales_unit_authority_fu4).parameters)
        assert not params & {"evaluation", "model_output", "confidence"}
        case_params = set(
            inspect.signature(derive_sales_unit_authority_fu4_case).parameters
        )
        assert not case_params & {"evaluation", "model_output"}

    def test_absence_never_derives_a_composition(self) -> None:
        result, channel = _extract("Plain product title")
        assert result.state is SalesUnitExtractionState.NO_PACKAGING_PUBLISHED
        assert channel.state is PackagingEvidenceStateV2.UNAVAILABLE
        assert candidate_composition_from_extraction(result) is None
        assert derive_sales_unit_authority_fu4(channel, None, None) is U


class TestF2SpecificationQuantitiesAreItemText:
    def test_a_specification_quantity_inside_a_clause_is_item_text(self) -> None:
        entries = fu4._full_parse_clause("1x 960GB SSD + 1x fan")
        assert entries == ((1, "960gb ssd"), (1, "fan"))
        # No parsed quantity or item is ever promoted to the bundle's
        # channel / target quantity: the axis over published counts only.
        channel = _candidate_channel(raw_detail="bundle: 1x 960GB SSD + 1x fan, complete list")
        record = candidate_composition_from_channel(channel)
        assert record.state is EST
        decision = _tier(
            channel,
            record,
            _target_established(clause="1x 960GB SSD + 1x fan"),
        )
        assert decision.sales_unit_authority is P
        assert decision.quantity_axis_state is Q_BOTH_UNPUBLISHED

    def test_an_out_of_grammar_residual_is_never_material(self) -> None:
        # Parentheses are not in the item-token character class: NOT
        # fully parseable ⇒ UNPROVEN, never CONTRADICTED from a half-
        # understood clause.
        assert fu4._full_parse_clause("1x 960GB SSD + 1x fan (tray)") is None
        assert (
            derive_sales_unit_authority_fu4(
                _candidate_channel(raw_detail="bundle: 1x 960GB SSD + 1x fan (tray), complete list"),
                candidate_composition_from_channel(
                    _candidate_channel(raw_detail="bundle: 1x 960GB SSD + 1x fan (tray), complete list")
                ),
                _target_established(clause="1x 960GB SSD + 1x fan"),
            )
            is U
        )


class TestF3MultiOfferIndependence:
    def test_two_observations_with_different_clauses_extract_independently(
        self,
    ) -> None:
        from product_intelligence.research import extract_sales_unit_evidence

        result_a = extract_sales_unit_evidence(
            _observation(title="bundle: 2x RAM + 1x CPU")
        )
        result_b = extract_sales_unit_evidence(
            _observation(title="bundle: 2x SSD + 1x cable")
        )
        assert result_a.input_digest != result_b.input_digest
        record_a = candidate_composition_from_extraction(result_a)
        record_b = candidate_composition_from_extraction(result_b)
        assert record_a is not None and record_b is not None
        assert record_a.composition_clause == "2x RAM + 1x CPU"
        assert record_b.composition_clause == "2x SSD + 1x cable"
        # No cross-contamination: each record is digest-bound to its own
        # result, and each verifies against its own channel.
        assert record_a.extraction_result_digest == result_a.result_digest
        assert record_b.extraction_result_digest == result_b.result_digest
        channel_a = _candidate_channel(
            raw_detail="bundle: 2x RAM + 1x CPU",
            source=CandidateEvidenceSourceV2.LISTING_TITLE,
        )
        # record_a binds channel_a (and is refused over a channel with a
        # different recorded provenance — a record cannot claim
        # provenance the channel never recorded).
        assert (
            derive_sales_unit_authority_fu4(
                channel_a, record_a, _target_established()
            )
            is U
        )
        with pytest.raises(
            BundleCompositionEvidenceIntegrityError, match="provenance"
        ):
            derive_sales_unit_authority_fu4(
                _candidate_channel(raw_detail="bundle: 2x RAM + 1x CPU"),
                record_a,
                _target_established(clause="2x RAM + 1x CPU"),
            )


class TestF4AttestationTrustBoundary:
    def test_the_attestation_text_is_never_read_by_the_derivation(self) -> None:
        """Two target records differing ONLY in the attestation's
        recorded text (each with its own verified digest) derive the
        SAME unit and the SAME axis determinations — the bounded fields
        (basis / source / clause_digest / attestation_digest) drive the
        behavior; the text is the reviewer's audit anchor, not a
        derivation input."""
        # The FU1 binding: the candidate record is presented over the
        # SAME channel it was constructed from.
        channel = _candidate_established_channel()
        record = candidate_composition_from_channel(channel)
        target_a = _target(
            None,
            TS,
            CLAUSE,
            EST,
            _make_attestation(
                EvidenceSideV2FU4.TARGET,
                CompletenessBasisV2FU4.REVIEWED_COMPOSITION_ATTESTATION,
                TS,
                _clause_digest(CLAUSE),
                "verified against manufacturer spec A (anchor text one)",
            ),
        )
        target_b = _target(
            None,
            TSD,
            CLAUSE,
            EST,
            _make_attestation(
                EvidenceSideV2FU4.TARGET,
                CompletenessBasisV2FU4.REVIEWED_COMPOSITION_ATTESTATION,
                TSD,
                _clause_digest(CLAUSE),
                "completely different determination text two",
            ),
        )
        unit_a = derive_sales_unit_authority_fu4(channel, record, target_a)
        unit_b = derive_sales_unit_authority_fu4(channel, record, target_b)
        assert unit_a is P and unit_b is P
        decision_a = _tier(channel, record, target_a)
        decision_b = _tier(channel, record, target_b)
        assert decision_a.quantity_axis_state == decision_b.quantity_axis_state
        assert decision_a.candidate_composition_state == decision_b.candidate_composition_state
        assert decision_a.target_composition_state == decision_b.target_composition_state

    def test_a_presented_attestation_is_digest_verified_before_any_axis_uses_it(
        self,
    ) -> None:
        att = _quantity_attestation(EvidenceSideV2FU4.TARGET)
        object.__setattr__(att, "attestation_text", "tampered after construction")
        # The FU1 binding: the record over its OWN channel, so the
        # candidate gate passes and the TAMPERED QUANTITY attestation's
        # own verify is what fires (before any axis uses it).
        channel = _candidate_established_channel(quantity=2)
        record = _candidate_established(quantity=2)
        with pytest.raises(BundleCompositionEvidenceIntegrityError):
            derive_sales_unit_authority_fu4(
                channel, record, _target_established(), att
            )

    def test_no_attestation_is_ever_constructed_by_the_derivation(self) -> None:
        """The unit derivation returns ONLY the unit vocabulary (no
        attestation is manufactured); the tier derivation's attestation
        digests come exclusively from the presented records (presenting
        none ⇒ exactly None)."""
        unit = derive_sales_unit_authority_fu4(
            _candidate_channel(), _candidate_record(), _target(None, TS, CLAUSE, SV)
        )
        assert unit in (P, U, C)
        decision = _tier(
            _candidate_channel(), _candidate_record(), _target(None, TS, CLAUSE, SV)
        )
        assert decision.candidate_completeness_attestation_digest is None
        assert decision.target_completeness_attestation_digest is None
        assert decision.quantity_attestation_digest is None

    def test_the_case_level_entry_point_reads_exactly_the_recorded_channel(self) -> None:
        """The case-level entry point is a pure function of the
        recorded V2 input's channel (input schema 1 — unchanged) and
        the derivation-side records (D2): the separately gated
        integration shape (dataclasses.replace of ONLY the channel over
        the frozen builder's case) is the recorded input."""
        from product_intelligence.research import (
            build_semantic_match_case_v2,
            build_v2_product_evidence_profile,
        )

        channel = _candidate_channel()
        record = _candidate_record()
        target = _target(None, TS, CLAUSE, SV)
        unit_direct = derive_sales_unit_authority_fu4(channel, record, target)

        normalized = normalize_listing_observation(
            _observation(title=f"Has {REQUEST_MPN} in the title")
        )
        request = ResearchRequest(
            manufacturer_part_number=REQUEST_MPN, description="A test product"
        )
        assessment = assess_listing_identity(request, normalized)
        context = derive_identity_state_v2(assessment)
        profile = build_v2_product_evidence_profile(
            observation=assessment.normalized_listing.observation,
            context_provenances=frozenset(),
            matched_facts=frozenset(),
        )
        case = build_semantic_match_case_v2(
            case_id="fu4-gated-0",
            request=request,
            assessment=assessment,
            context=context,
            product_evidence=profile,
            context_provenances=frozenset(),
            reviewed_target_context=None,
        )
        replaced = dataclasses.replace(
            case,
            candidate_commercial=dataclasses.replace(
                case.candidate_commercial, sales_unit=channel
            ),
        )
        assert isinstance(replaced, SemanticMatchCaseV2)
        assert replaced.candidate_commercial.sales_unit == channel
        assert (
            derive_sales_unit_authority_fu4_case(replaced, record, target)
            is unit_direct
        )
        with pytest.raises(TypeError):
            derive_sales_unit_authority_fu4_case(
                "not a case", record, target  # type: ignore[arg-type]
            )
