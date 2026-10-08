"""The Q3-A qualification corpus SOURCE (declarative case definitions).

This module is the auditable source of the frozen corpus
(``evaluation/semantic_v2_qualification/corpus_v1.json``). It runs the
EXACT frozen production chain for every semantic case:

    ResearchRequest
      -> ListingObservation
      -> normalize_listing_observation          (frozen 3B)
      -> assess_listing_identity                (frozen 3C)
      -> derive_identity_state_v2               (frozen S2-A)
      -> build_semantic_match_case_v2 /
         SemanticMatchCaseV2                    (frozen S2-C input contract)

and records the resulting ``case.canonical()`` payload into the corpus
document. Ground-truth labels are declared INDEPENDENTLY of any model
output: every label carries a bounded source kind
(CONTRACT_GROUNDED / PRODUCT_KNOWLEDGE_GROUNDED /
REVIEWED_SOURCE_GROUNDED), an explicit source citation, the independent
evidence supporting it, a reviewer identity, and an ambiguity
classification. Synthetic cases are labeled SYNTHETIC and never
pretend to be real-market evidence; recorded-fixture cases cite the
exact in-repository recorded artifact.

CONTRACT-SURFACE cases exercise the full input surface of the frozen
V2 contract (structured candidate facts, observed packaging, raw
specification text) that the live main-flow builder does not emit today
(the extraction-capability audit in ``research/semantic_v2.py``); they
are built through the same real ``SemanticMatchCaseV2`` constructor, so
every fail-closed rule applies.

The generator self-checks each case: the derived deterministic
substate/primary signal must equal the one declared by the case author,
or generation fails loudly (a fixture that lands in the wrong state is a
corpus defect, never a silent relabel).

This module imports the frozen research contract (authorized by the
Q3-A exact-allowlist exception in
``tests/research/test_research_identity_boundaries.py``) and no other
production surface. It performs no I/O other than what its caller asks
for (building the corpus document is pure; writing files is the CLI's
job).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Final

from product_intelligence.evaluation.semantic_v2.canonical import (
    canonical_sha256,
)
from product_intelligence.domain import ResearchRequest
from product_intelligence.research import (
    CandidateProductEvidenceSource,
    ContextProvenance,
    ProductEvidenceDimension,
    ProductEvidenceFactV2,
    ProductEvidenceProfileV2,
    V2_CONTRACT_BINDING,
    build_semantic_match_case_v2,
    build_v2_product_evidence_profile,
    derive_identity_state_v2,
    derive_product_evidence_quality,
    normalize_listing_observation,
    substate_relationship_requirement,
)
from product_intelligence.research.listings import (
    ExtractionMethod,
    ListingObservation,
)
from product_intelligence.research.matching import assess_listing_identity
from product_intelligence.research.semantic_v2 import (
    CandidateCommercialEvidenceV2,
    CandidateEvidenceSourceV2,
    CandidateObservationFactV2,
    CandidateProductEvidenceV2,
    CandidateSalesUnitEvidenceV2,
    PackagingEvidenceStateV2,
    ReviewedTargetContextV2,
    SALES_UNIT_EVIDENCE_UNAVAILABLE,
    SalesUnitKindV2,
    SemanticMatchCaseV2,
    TargetEvidenceV2,
    TargetIdentifierRelationKindV2,
)

__all__ = [
    "CASES",
    "CORPUS_CREATED_UTC",
    "CORPUS_ID",
    "CORPUS_LABEL",
    "CORPUS_VERSION",
    "MICRON_CATALOG_FIXTURE_BODY_SHA256",
    "build_corpus_document",
    "build_corpus_state",
    "build_manifest_document",
]


# ---------------------------------------------------------------------------
# Corpus identity (deterministic; declared, never clock-derived)
# ---------------------------------------------------------------------------

CORPUS_ID: Final[str] = "PI-SEMANTIC-V2-QUALIFICATION"
CORPUS_VERSION: Final[str] = "1.0.0"
CORPUS_LABEL: Final[str] = "q3a-independent-v2-qualification"

#: The declared creation instant of corpus 1.0.0 (deterministic constant;
#: the corpus is a versioned artifact, not a runtime observation).
CORPUS_CREATED_UTC: Final[str] = "2026-10-08T00:00:00Z"

#: The recorded 4D-D Micron 7500 part-catalog fixture body digest
#: (tests/fixtures/pages/micron_7500_part_catalog.json, recorded
#: 2026-09-22; the 4D-D acquisition carries this exact body digest).
MICRON_CATALOG_FIXTURE_BODY_SHA256: Final[str] = (
    "160d4fe97a5df5249e8f6404f6b005c0515fab4def1b4668fdaf87c727600743"
)

#: The recorded 4D-D catalog origin (the reviewed source URL of the
#: fixture; carried as data, never fetched by this module).
MICRON_7500_CATALOG_URL: Final[str] = (
    "https://www.micron.com/content/micron/us/en/products/storage/ssd/"
    "data-center-ssd/7500-ssd/part-catalog/_jcr_content.products.json/"
    "getpartcatalog/storage/7500-ssd/-/en_US"
)

#: The recorded retrieval DATE of the fixture. The fixture preserves no
#: sub-daily instant; the corpus declares midnight UTC of the recorded
#: date as a deterministic placeholder (documented in the case label).
MICRON_7500_CATALOG_RECORDED_UTC: Final[str] = "2026-09-22T00:00:00Z"


# ---------------------------------------------------------------------------
# Bounded corpus vocabularies (frozen for corpus schema version 1)
# ---------------------------------------------------------------------------

CASE_CLASSES: Final[frozenset[str]] = frozenset(
    {"AUTHORITATIVE", "AMBIGUOUS", "CONTRACT_NEGATIVE"}
)
EVIDENCE_KINDS: Final[frozenset[str]] = frozenset(
    {"SYNTHETIC", "RECORDED_FIXTURE", "REAL_MARKET"}
)
INPUT_SHAPES: Final[frozenset[str]] = frozenset(
    {"LIVE_SHAPE", "CONTRACT_SURFACE"}
)
CATEGORIES: Final[frozenset[str]] = frozenset(
    {
        "enterprise_ssd",
        "server_memory",
        "processor",
        "network_adapter",
        "workstation_gpu",
    }
)
CHALLENGE_TAGS: Final[frozenset[str]] = frozenset(
    {
        "exact_product_alt_wording",
        "title_mpn_only",
        "compatibility_wording",
        "different_generation",
        "different_capacity",
        "different_interface",
        "different_form_factor",
        "accessory_vs_product",
        "standalone_vs_bundle",
        "single_vs_multipack",
        "tray_vs_retail",
        "missing_candidate_mpn",
        "different_sku_same_product",
        "sku_matches_target_mpn",
        "near_miss_one_char",
        "near_miss_truncated",
        "different_brand",
        "condition_only_difference",
        "missing_critical_specs",
        "customer_retrieval_alias",
        "manufacturer_product_context_only",
        "reviewed_relation_authority",
        "contradictory_listing_evidence",
        "misleading_seo",
        "insufficient_evidence",
        "sales_unit_unproven",
        "multi_conflict",
        "cross_category",
        "partial_mpn_boundary",
    }
)
LABEL_SOURCE_KINDS: Final[frozenset[str]] = frozenset(
    {
        "CONTRACT_GROUNDED",
        "PRODUCT_KNOWLEDGE_GROUNDED",
        "REVIEWED_SOURCE_GROUNDED",
    }
)
REVIEWER_STATUSES: Final[frozenset[str]] = frozenset({"REVIEWED", "UNREVIEWED"})
AMBIGUITY_CLASSES: Final[frozenset[str]] = frozenset(
    {
        "UNAMBIGUOUS",
        "CONTESTABLE",
        "INSUFFICIENTLY_SUPPORTED",
    }
)
DECISIONS: Final[frozenset[str]] = frozenset(
    {"MATCH", "NO_MATCH", "UNCERTAIN"}
)
CONFLICT_CLASSES: Final[frozenset[str]] = frozenset(
    {
        "MPN_IDENTITY",
        "PRODUCT_FAMILY",
        "GENERATION",
        "CAPACITY",
        "INTERFACE",
        "FORM_FACTOR",
        "PRODUCT_ROLE",
        "ACCESSORY_RELATION",
        "PACKAGING_QUANTITY",
        "BUNDLE",
        "REVISION_OR_SUFFIX",
        "BRAND",
        "OTHER_MATERIAL_CONFLICT",
        "CONDITION",
    }
)
MISSING_DIMENSIONS: Final[frozenset[str]] = frozenset(
    {
        "PRODUCT_FAMILY",
        "GENERATION",
        "CAPACITY",
        "INTERFACE",
        "FORM_FACTOR",
        "PRODUCT_ROLE",
        "ACCESSORY_RELATION",
        "PACKAGING_QUANTITY",
        "BUNDLE",
        "BRAND",
        "REVISION_OR_SUFFIX",
        "CONDITION",
    }
)
REJECTION_CLASSES: Final[frozenset[str]] = frozenset(
    {
        "NON_UNCERTAIN_STATE",
        "INVALID_INPUT_SCHEMA",
        "FOREIGN_DETERMINISTIC_CONTEXT",
        "UNSUPPORTED_EVIDENCE",
    }
)
PROVENANCES: Final[frozenset[str]] = frozenset(
    {
        "MANUFACTURER_PRODUCT_CONTEXT",
        "MANUFACTURER_RELATION_AUTHORITY",
        "CUSTOMER_RETRIEVAL_RELATION",
    }
)
CANDIDATE_FACT_SOURCES: Final[frozenset[str]] = frozenset(
    {
        "PUBLISHED_STRUCTURED_FIELD",
        "LISTING_TITLE",
        "SPECIFICATION_TEXT",
        "REVIEWED_PRODUCT_CONTEXT",
    }
)
AUTHORITY_FACT_SOURCES: Final[frozenset[str]] = frozenset(
    {
        "LISTING_PRODUCT_TITLE",
        "REVIEWED_PRODUCT_CONTEXT",
    }
)
PRODUCT_FACT_DIMENSIONS: Final[frozenset[str]] = frozenset(
    {
        "product_family",
        "generation",
        "capacity",
        "interface",
        "form_factor",
        "product_role",
        "accessory_relation",
        "brand",
        "revision_or_suffix",
    }
)
SALES_UNIT_KINDS: Final[frozenset[str]] = frozenset(
    {
        "SINGLE_UNIT",
        "PACK_QUANTITY",
        "TRAY_OR_FACTORY_PACK",
        "BUNDLE",
    }
)

#: Mechanical ground-truth guard: label evidence is INDEPENDENT of any
#: model output. A citation naming candidate model output (or a
#: candidate model) is rejected at corpus build time.
FORBIDDEN_EVIDENCE_TOKENS: Final[frozenset[str]] = frozenset(
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
    }
)


# ---------------------------------------------------------------------------
# Declarative case building blocks
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Obs:
    """One declared candidate listing observation (as published)."""

    mpn: str | None = None
    sku: str | None = None
    title: str | None = None
    brand: str | None = None
    condition: str | None = None
    price: str | None = "100"
    currency: str | None = "USD"
    availability: str | None = "In stock"
    seller: str | None = None
    offer_url: str | None = None


@dataclass(frozen=True)
class ReviewedCtx:
    """One declared reviewed manufacturer TARGET context (bounded)."""

    manufacturer: str
    category: str
    matched_base_part_number: str
    relation_family_part_numbers: tuple[str, ...]
    source_name: str
    source_url: str
    retrieved_at: str
    evidence_body_sha256: str


@dataclass(frozen=True)
class SalesUnit:
    """One declared OBSERVED sales-unit / packaging channel value."""

    kind: str
    quantity: int | None
    raw_detail: str
    source: str = "PUBLISHED_STRUCTURED_FIELD"


@dataclass(frozen=True)
class CaseDecl:
    """One declared corpus case (input side + independent label side).

    Semantic cases (AUTHORITATIVE / AMBIGUOUS) carry the observation,
    the deterministic-context self-check (expected substate / primary
    signal), and the independent label. CONTRACT_NEGATIVE cases carry an
    explicit patch list applied to a valid base payload (the attack /
    invalid-state surface) plus the expected rejection class.
    """

    case_id: str
    category: str
    case_class: str
    evidence_kind: str
    input_shape: str
    challenge_tags: tuple[str, ...]
    request_mpn: str
    request_description: str
    obs: Obs
    provenances: tuple[str, ...] = ()
    authority_facts: tuple[tuple[str, tuple[str, ...]], ...] = ()
    reviewed_context: ReviewedCtx | None = None
    # CONTRACT_SURFACE overrides:
    product_facts: tuple[tuple[str, str, str], ...] = ()
    raw_specification_text: str | None = None
    sales_unit: SalesUnit | None = None
    # deterministic-context self-check (semantic cases):
    expected_substate: str | None = None
    expected_primary_signal: str | None = None
    # label side (semantic cases):
    expected_decision: str | None = None
    acceptable_decisions: tuple[str, ...] | None = None
    expected_conflict_classes: tuple[str, ...] = ()
    expected_missing_dimensions: tuple[str, ...] = ()
    expected_reason_code: str | None = None
    commercial_sales_unit_safety: bool = False
    label_source_kind: str | None = None
    label_source: str | None = None
    label_evidence: str | None = None
    reviewer: str | None = None
    reviewer_status: str | None = None
    ambiguity: str | None = None
    # contract-negative side:
    base_payload_case_id: str | None = None
    patches: tuple[tuple[tuple[str, ...], Any], ...] = ()
    expected_rejection_class: str | None = None


def _micron_reviewed_ctx(requested_form: str) -> ReviewedCtx:
    """The reviewed 4D-D Micron 7500 target context for one requested
    family form, from the recorded fixture (the base part published in
    the recorded catalog; the family is the frozen 4D-D v1 shape)."""
    base = "MTFDKCC3T8TGP-1BK1DABYY"
    family = (base, base + "R", base + "T")
    others = tuple(f for f in family if f != requested_form)
    return ReviewedCtx(
        manufacturer="Micron",
        category="SSD",
        matched_base_part_number=base,
        relation_family_part_numbers=others,
        source_name="Micron 7500 part catalog (recorded 4D-D fixture)",
        source_url=MICRON_7500_CATALOG_URL,
        retrieved_at=MICRON_7500_CATALOG_RECORDED_UTC,
        evidence_body_sha256=MICRON_CATALOG_FIXTURE_BODY_SHA256,
    )


# ---------------------------------------------------------------------------
# Case declarations (the corpus source of truth)
# ---------------------------------------------------------------------------

# -- U1 TITLE_MPN -----------------------------------------------------------

_S1 = CaseDecl(
    case_id="V2Q-SSD-U1-MATCH-0001",
    category="enterprise_ssd",
    case_class="AUTHORITATIVE",
    evidence_kind="RECORDED_FIXTURE",
    input_shape="LIVE_SHAPE",
    challenge_tags=("exact_product_alt_wording", "title_mpn_only"),
    request_mpn="MZ1L2960HCJR-00A07",
    request_description="Samsung SSD PM9A3 960GB M.2 NVMe PCIe Gen4",
    obs=Obs(
        title=(
            "SSD disk Samsung PM9A3 960GB M.2 22110 NVMe PCIe Gen4 x4 "
            "| MZ1L2960HCJR-00A07"
        ),
    ),
    expected_substate="U1_TITLE_MPN",
    expected_primary_signal="TITLE_MPN_TOKEN",
    expected_decision="MATCH",
    label_source_kind="REVIEWED_SOURCE_GROUNDED",
    label_source=(
        "evaluation/semantic_corpus/cases.json SMQ-0001 "
        "(provenance: project_uat)"
    ),
    label_evidence=(
        "The recorded project-UAT expectation for this exact scenario: "
        "the exact requested MPN is published in the listing title "
        "together with an aligned product description (960GB M.2 NVMe "
        "Gen4 PM9A3); no conflicting attribute is published. Exact MPN "
        "equality in the title is strong identifier evidence; the "
        "frozen V2 contract's own U1 state exists for exactly this "
        "semantic resolution."
    ),
    reviewer="PROJECT_UAT (recorded in repository)",
    reviewer_status="REVIEWED",
    ambiguity="UNAMBIGUOUS",
)

_S2 = CaseDecl(
    case_id="V2Q-SSD-U1-COMPAT-0002",
    category="enterprise_ssd",
    case_class="AUTHORITATIVE",
    evidence_kind="RECORDED_FIXTURE",
    input_shape="LIVE_SHAPE",
    challenge_tags=("compatibility_wording", "accessory_vs_product"),
    request_mpn="MZ1L2960HCJR-00A07",
    request_description="Samsung SSD PM9A3 960GB M.2 NVMe PCIe Gen4",
    obs=Obs(
        title="2.5-inch drive tray compatible with Samsung MZ1L2960HCJR-00A07",
    ),
    expected_substate="U1_TITLE_MPN",
    expected_primary_signal="TITLE_MPN_TOKEN",
    expected_decision="NO_MATCH",
    expected_conflict_classes=("ACCESSORY_RELATION",),
    expected_reason_code="NO_MATCH_ACCESSORY",
    label_source_kind="REVIEWED_SOURCE_GROUNDED",
    label_source=(
        "evaluation/semantic_corpus/cases.json SMQ-0005 "
        "(provenance: project_uat)"
    ),
    label_evidence=(
        "The recorded project-UAT expectation: 'compatible with' is "
        "compatibility wording, not product identity; the listing "
        "publishes a drive tray (an accessory), not the requested SSD. "
        "The frozen conflict taxonomy makes ACCESSORY_RELATION "
        "ALWAYS_HARD; the frozen prompt: an accessory instead of the "
        "requested product is a material conflict -> NO_MATCH."
    ),
    reviewer="PROJECT_UAT (recorded in repository)",
    reviewer_status="REVIEWED",
    ambiguity="UNAMBIGUOUS",
)

_S3 = CaseDecl(
    case_id="V2Q-SSD-U1-SEO-0003",
    category="enterprise_ssd",
    case_class="AUTHORITATIVE",
    evidence_kind="SYNTHETIC",
    input_shape="LIVE_SHAPE",
    challenge_tags=("misleading_seo", "different_capacity"),
    request_mpn="SYN-SSD-3840-U3",
    request_description="3.84TB U.3 NVMe data center SSD",
    obs=Obs(
        title="7.68TB NVMe SSD - fast upgrade from SYN-SSD-3840-U3 - hot deal",
    ),
    expected_substate="U1_TITLE_MPN",
    expected_primary_signal="TITLE_MPN_TOKEN",
    expected_decision="NO_MATCH",
    expected_conflict_classes=("CAPACITY",),
    expected_reason_code="NO_MATCH_CAPACITY",
    label_source_kind="CONTRACT_GROUNDED",
    label_source="synthetic by-construction scenario (corpus 1.0.0)",
    label_evidence=(
        "By construction the requested product is 3.84TB and the "
        "published title states 7.68TB; the requested MPN appears only "
        "as SEO reference wording ('upgrade from'). Different published "
        "capacity is the ALWAYS_HARD CAPACITY conflict; the frozen "
        "contract requires NO_MATCH grounded in it. The identifier "
        "token in marketing wording is not identity evidence."
    ),
    reviewer="PRODUCT-INTEL.Q3A.CORPUS-AUTHOR (synthetic by-construction)",
    reviewer_status="REVIEWED",
    ambiguity="UNAMBIGUOUS",
)

_S4 = CaseDecl(
    case_id="V2Q-CPU-U1-CROSSREF-0004",
    category="processor",
    case_class="AUTHORITATIVE",
    evidence_kind="SYNTHETIC",
    input_shape="LIVE_SHAPE",
    challenge_tags=("compatibility_wording", "different_generation"),
    request_mpn="SYN-CPU-9254",
    request_description="32-core server processor, generation 9254",
    obs=Obs(
        title=(
            "Synthetic 9354 32-Core Server CPU (replacement for "
            "SYN-CPU-9254)"
        ),
    ),
    expected_substate="U1_TITLE_MPN",
    expected_primary_signal="TITLE_MPN_TOKEN",
    expected_decision="NO_MATCH",
    expected_conflict_classes=("GENERATION",),
    expected_reason_code="NO_MATCH_GENERATION",
    label_source_kind="CONTRACT_GROUNDED",
    label_source="synthetic by-construction scenario (corpus 1.0.0)",
    label_evidence=(
        "By construction the listing publishes generation 9354 as the "
        "product and references the requested 9254 only as 'replacement "
        "for' (compatibility wording). A different published generation "
        "is the ALWAYS_HARD GENERATION conflict -> NO_MATCH."
    ),
    reviewer="PRODUCT-INTEL.Q3A.CORPUS-AUTHOR (synthetic by-construction)",
    reviewer_status="REVIEWED",
    ambiguity="UNAMBIGUOUS",
)

_S5 = CaseDecl(
    case_id="V2Q-SSD-U1-THIN-0005",
    category="enterprise_ssd",
    case_class="AMBIGUOUS",
    evidence_kind="RECORDED_FIXTURE",
    input_shape="LIVE_SHAPE",
    challenge_tags=("title_mpn_only", "insufficient_evidence"),
    request_mpn="MTFDKCC3T8TGP-1BK1DABYY",
    request_description="Micron 7500 4TB U.3 NVMe SSD",
    obs=Obs(title="MTFDKCC3T8TGP-1BK1DABYY"),
    expected_substate="U1_TITLE_MPN",
    expected_primary_signal="TITLE_MPN_TOKEN",
    expected_decision="UNCERTAIN",
    acceptable_decisions=("MATCH", "UNCERTAIN"),
    label_source_kind="REVIEWED_SOURCE_GROUNDED",
    label_source=(
        "tests/fixtures/pages/micron_7500_part_catalog.json (recorded "
        "4D-D fixture, 2026-09-22); evaluation/semantic_corpus/cases.json "
        "SMQ-0001 pattern (provenance: project_uat)"
    ),
    label_evidence=(
        "The recorded catalog confirms the title MPN is a real published "
        "part (7500 4TB U.3), so NO_MATCH is not defensible. But the "
        "listing publishes nothing beyond the identifier token: no "
        "capacity, no form factor, no brand. The recorded project-UAT "
        "corpus scores the analogous bare-identifier case UNCERTAIN "
        "(SMQ-0002: base identifier without the establishing suffix -> "
        "UNCERTAIN). Both 'strong identifier evidence -> MATCH' and "
        "'identifier alone is not the only evidence -> UNCERTAIN' are "
        "defensible readings of the frozen prompt; the case is "
        "legitimately contested and is NOT forced to either pole."
    ),
    reviewer="PROJECT_UAT (recorded) + Q3-A corpus author (classification)",
    reviewer_status="REVIEWED",
    ambiguity="CONTESTABLE",
)

# -- U2 SKU_ONLY --------------------------------------------------------------

_S6 = CaseDecl(
    case_id="V2Q-SSD-U2E-MATCH-0006",
    category="enterprise_ssd",
    case_class="AUTHORITATIVE",
    evidence_kind="SYNTHETIC",
    input_shape="LIVE_SHAPE",
    challenge_tags=("exact_product_alt_wording",),
    request_mpn="SYN-SSD-3840-U3",
    request_description="3.84TB U.3 NVMe data center SSD",
    obs=Obs(
        sku="SYN-SSD-3840-U3",
        title="3.84TB U.3 NVMe SSD, data center",
    ),
    expected_substate="U2_SKU_ONLY",
    expected_primary_signal="SKU_EQUALS_TARGET",
    expected_decision="MATCH",
    label_source_kind="CONTRACT_GROUNDED",
    label_source="synthetic by-construction scenario (corpus 1.0.0)",
    label_evidence=(
        "The published SKU is frozen-2A identical to the requested MPN "
        "(the deterministic layer records SKU_EQUALS_TARGET; the frozen "
        "relationship table makes this state NOT_APPLICABLE for "
        "reviewed-relation gating). The title aligns on capacity and "
        "form factor by construction; no conflicting attribute is "
        "published. Commercial equivalence is established by the "
        "supplied evidence."
    ),
    reviewer="PRODUCT-INTEL.Q3A.CORPUS-AUTHOR (synthetic by-construction)",
    reviewer_status="REVIEWED",
    ambiguity="UNAMBIGUOUS",
)

_S7 = CaseDecl(
    case_id="V2Q-SSD-U2E-COLLIDE-0007",
    category="enterprise_ssd",
    case_class="AUTHORITATIVE",
    evidence_kind="SYNTHETIC",
    input_shape="LIVE_SHAPE",
    challenge_tags=("sku_matches_target_mpn", "accessory_vs_product"),
    request_mpn="SYN-SSD-3840-U3",
    request_description="3.84TB U.3 NVMe data center SSD",
    obs=Obs(
        sku="SYN-SSD-3840-U3",
        title="SAS to NVMe adapter cable, 25cm",
    ),
    expected_substate="U2_SKU_ONLY",
    expected_primary_signal="SKU_EQUALS_TARGET",
    expected_decision="NO_MATCH",
    expected_conflict_classes=("PRODUCT_ROLE",),
    expected_reason_code="NO_MATCH_PRODUCT_ROLE",
    label_source_kind="CONTRACT_GROUNDED",
    label_source="synthetic by-construction scenario (corpus 1.0.0)",
    label_evidence=(
        "By construction the published SKU accidentally equals the "
        "requested MPN while the published title describes an adapter "
        "cable - a different product role. The frozen prompt: SKU "
        "evidence must be interpreted carefully; a different product "
        "role is the ALWAYS_HARD PRODUCT_ROLE conflict -> NO_MATCH. "
        "An identifier coincidence never overrides published product "
        "evidence."
    ),
    reviewer="PRODUCT-INTEL.Q3A.CORPUS-AUTHOR (synthetic by-construction)",
    reviewer_status="REVIEWED",
    ambiguity="UNAMBIGUOUS",
)

_S8 = CaseDecl(
    case_id="V2Q-SSD-U2N-MATCH-0008",
    category="enterprise_ssd",
    case_class="AUTHORITATIVE",
    evidence_kind="SYNTHETIC",
    input_shape="LIVE_SHAPE",
    challenge_tags=("different_sku_same_product",),
    request_mpn="SYN-SSD-3840-U3",
    request_description="3.84TB U.3 NVMe data center SSD",
    obs=Obs(
        sku="STOR-U3-3840-RET",
        title="3.84TB U.3 NVMe SSD, data center, new",
    ),
    expected_substate="U2_SKU_ONLY",
    expected_primary_signal="SKU_NOT_TARGET",
    expected_decision="MATCH",
    label_source_kind="CONTRACT_GROUNDED",
    label_source="synthetic by-construction scenario (corpus 1.0.0)",
    label_evidence=(
        "The published SKU differs from the requested MPN (a retailer "
        "SKU), which the frozen contract explicitly states is not by "
        "itself proof of a different product. Capacity and form factor "
        "align by construction; no conflicting attribute is published. "
        "Commercial equivalence holds on the supplied evidence."
    ),
    reviewer="PRODUCT-INTEL.Q3A.CORPUS-AUTHOR (synthetic by-construction)",
    reviewer_status="REVIEWED",
    ambiguity="UNAMBIGUOUS",
)

_S9 = CaseDecl(
    case_id="V2Q-DIMM-U2N-THIN-0009",
    category="server_memory",
    case_class="AMBIGUOUS",
    evidence_kind="SYNTHETIC",
    input_shape="LIVE_SHAPE",
    challenge_tags=("different_sku_same_product", "missing_critical_specs"),
    request_mpn="SYN-DIMM-96G-6400",
    request_description="96GB DDR5-6400 server memory module",
    obs=Obs(
        sku="MEM-96-DS",
        title="96GB DDR5 server memory",
    ),
    expected_substate="U2_SKU_ONLY",
    expected_primary_signal="SKU_NOT_TARGET",
    expected_decision="UNCERTAIN",
    acceptable_decisions=("MATCH", "UNCERTAIN"),
    label_source_kind="CONTRACT_GROUNDED",
    label_source="synthetic by-construction scenario (corpus 1.0.0)",
    label_evidence=(
        "Capacity (96GB) and family (DDR5 server memory) align by "
        "construction, but the published title states no memory speed; "
        "the requested product is 6400 MT/s and a different speed is a "
        "material (interface-dimension) difference. Neither equivalence "
        "nor non-equivalence is established by the supplied evidence: "
        "MATCH (no conflicting evidence) and UNCERTAIN (critical speed "
        "attribute missing) are both defensible; NO_MATCH would require "
        "published contrary evidence the scenario does not provide."
    ),
    reviewer="PRODUCT-INTEL.Q3A.CORPUS-AUTHOR (synthetic by-construction)",
    reviewer_status="REVIEWED",
    ambiguity="CONTESTABLE",
)

# -- U3 PARTIAL_BOUNDARY ------------------------------------------------------

_S10 = CaseDecl(
    case_id="V2Q-SSD-U3-MATCH-0010",
    category="enterprise_ssd",
    case_class="AUTHORITATIVE",
    evidence_kind="RECORDED_FIXTURE",
    input_shape="LIVE_SHAPE",
    challenge_tags=("partial_mpn_boundary",),
    request_mpn="MTFDKCC3T8TGP-1BK1DABYY",
    request_description="Micron 7500 4TB U.3 NVMe SSD",
    obs=Obs(
        mpn="MTFDKCC3T8TGP",
        title="Micron 7500 4TB U.3 NVMe SSD",
        brand="Micron",
    ),
    expected_substate="U3_PARTIAL_BOUNDARY",
    expected_primary_signal="PARTIAL_BOUNDARY",
    expected_decision="MATCH",
    label_source_kind="REVIEWED_SOURCE_GROUNDED",
    label_source=(
        "tests/fixtures/pages/micron_7500_part_catalog.json (recorded "
        "4D-D fixture, 2026-09-22)"
    ),
    label_evidence=(
        "The published partial MPN 'MTFDKCC3T8TGP' is exactly the "
        "recorded catalog's published family prefix of the requested "
        "part MTFDKCC3T8TGP-1BK1DABYY ('7500 4TB U.3 SSD'); the listing "
        "additionally publishes brand Micron and the aligned family / "
        "capacity / form-factor designation by construction. The "
        "identifier is consistent with the requested product and no "
        "conflicting attribute is published; the partial-boundary state "
        "exists for this semantic resolution."
    ),
    reviewer="PRODUCT-INTEL.Q3A.CORPUS-AUTHOR (recorded fixture)",
    reviewer_status="REVIEWED",
    ambiguity="UNAMBIGUOUS",
)

_S11 = CaseDecl(
    case_id="V2Q-SSD-U3-CAP-0011",
    category="enterprise_ssd",
    case_class="AUTHORITATIVE",
    evidence_kind="RECORDED_FIXTURE",
    input_shape="LIVE_SHAPE",
    challenge_tags=("partial_mpn_boundary", "different_capacity"),
    request_mpn="MTFDKCC3T8TGP-1BK1DABYY",
    request_description="Micron 7500 4TB U.3 NVMe SSD",
    obs=Obs(
        mpn="MTFDKCC3T8TGP",
        title="Micron 7500 8TB U.3 NVMe SSD",
        brand="Micron",
    ),
    expected_substate="U3_PARTIAL_BOUNDARY",
    expected_primary_signal="PARTIAL_BOUNDARY",
    expected_decision="NO_MATCH",
    expected_conflict_classes=("CAPACITY",),
    expected_reason_code="NO_MATCH_CAPACITY",
    label_source_kind="REVIEWED_SOURCE_GROUNDED",
    label_source=(
        "tests/fixtures/pages/micron_7500_part_catalog.json (recorded "
        "4D-D fixture, 2026-09-22)"
    ),
    label_evidence=(
        "The recorded catalog lists the 7500 family as distinct parts "
        "per capacity (4TB and 8TB are separate published parts); the "
        "partial identifier is family-consistent but the published "
        "capacity (8TB) differs from the requested 4TB - the ALWAYS_HARD "
        "CAPACITY conflict decides NO_MATCH regardless of the identifier."
    ),
    reviewer="PRODUCT-INTEL.Q3A.CORPUS-AUTHOR (recorded fixture)",
    reviewer_status="REVIEWED",
    ambiguity="UNAMBIGUOUS",
)

_S12 = CaseDecl(
    case_id="V2Q-SSD-U3-THIN-0012",
    category="enterprise_ssd",
    case_class="AUTHORITATIVE",
    evidence_kind="SYNTHETIC",
    input_shape="LIVE_SHAPE",
    challenge_tags=("partial_mpn_boundary", "missing_critical_specs",
                    "insufficient_evidence"),
    request_mpn="SYN-SSD-1920-U2",
    request_description="1.92TB U.2 NVMe data center SSD",
    obs=Obs(
        mpn="SYN-SSD-1920",
        title="NVMe data center SSD",
    ),
    expected_substate="U3_PARTIAL_BOUNDARY",
    expected_primary_signal="PARTIAL_BOUNDARY",
    expected_decision="UNCERTAIN",
    expected_missing_dimensions=("CAPACITY", "FORM_FACTOR"),
    expected_reason_code="UNCERTAIN_MISSING_CRITICAL_ATTRIBUTES",
    label_source_kind="CONTRACT_GROUNDED",
    label_source="synthetic by-construction scenario (corpus 1.0.0)",
    label_evidence=(
        "The published partial identifier is consistent by construction, "
        "but the title publishes no capacity and no form factor: the "
        "critical identity dimensions are absent from all supplied "
        "evidence. The frozen prompt: never manufacture a missing fact; "
        "insufficient evidence -> UNCERTAIN (missing_critical_attributes "
        "names the gap)."
    ),
    reviewer="PRODUCT-INTEL.Q3A.CORPUS-AUTHOR (synthetic by-construction)",
    reviewer_status="REVIEWED",
    ambiguity="UNAMBIGUOUS",
)

# -- U4 NO_MPN ----------------------------------------------------------------

_S13 = CaseDecl(
    case_id="V2Q-SSD-U4-AMBIG-0013",
    category="enterprise_ssd",
    case_class="AMBIGUOUS",
    evidence_kind="RECORDED_FIXTURE",
    input_shape="LIVE_SHAPE",
    challenge_tags=("missing_candidate_mpn", "insufficient_evidence"),
    request_mpn="MTFDKCC3T8TGP-1BK1DABYY",
    request_description="Micron 7500 4TB U.3 NVMe SSD",
    obs=Obs(
        title="Micron 7500 4TB U.3 NVMe SSD",
        brand="Micron",
    ),
    expected_substate="U4_NO_MPN",
    expected_primary_signal="NO_RELATION",
    expected_decision="UNCERTAIN",
    acceptable_decisions=("UNCERTAIN", "MATCH"),
    label_source_kind="REVIEWED_SOURCE_GROUNDED",
    label_source=(
        "tests/fixtures/pages/micron_7500_part_catalog.json (recorded "
        "4D-D fixture, 2026-09-22)"
    ),
    label_evidence=(
        "The recorded catalog publishes THREE distinct 7500 4TB U.3 "
        "parts (MTFDKCC3T8TGP-1BK1DABYY, MTFDKCC3T8TGP-1BK1JABYY, "
        "MTFDKCC3T8TGP-1BK1DFCYY). The candidate publishes brand, "
        "family, capacity, and form factor but no identifier: the "
        "evidence cannot distinguish which of the three published parts "
        "is listed, so UNCERTAIN is independently supported. MATCH is "
        "defensible only by ignoring the recorded ambiguity; the case "
        "is genuinely contested and stays visible at both poles."
    ),
    reviewer="PRODUCT-INTEL.Q3A.CORPUS-AUTHOR (recorded fixture)",
    reviewer_status="REVIEWED",
    ambiguity="CONTESTABLE",
)

_S14 = CaseDecl(
    case_id="V2Q-DIMM-U4-MATCH-0014",
    category="server_memory",
    case_class="AUTHORITATIVE",
    evidence_kind="SYNTHETIC",
    input_shape="LIVE_SHAPE",
    challenge_tags=("missing_candidate_mpn", "exact_product_alt_wording"),
    request_mpn="SYN-DIMM-96G-6400",
    request_description="96GB DDR5-6400 MRDIMM server memory",
    obs=Obs(
        title="96GB DDR5-6400 MRDIMM Server Memory Module",
        brand="SyntheticMemory",
    ),
    expected_substate="U4_NO_MPN",
    expected_primary_signal="NO_RELATION",
    expected_decision="MATCH",
    label_source_kind="CONTRACT_GROUNDED",
    label_source="synthetic by-construction scenario (corpus 1.0.0)",
    label_evidence=(
        "No candidate MPN is published, but the title publishes the "
        "full aligned attribute set by construction: capacity 96GB, "
        "speed DDR5-6400, module type MRDIMM, role server memory - "
        "exactly the requested product's description. The missing "
        "candidate MPN is explicitly NOT automatically NO_MATCH under "
        "the frozen prompt; on the supplied evidence the product is "
        "commercially equivalent."
    ),
    reviewer="PRODUCT-INTEL.Q3A.CORPUS-AUTHOR (synthetic by-construction)",
    reviewer_status="REVIEWED",
    ambiguity="UNAMBIGUOUS",
)

_S15 = CaseDecl(
    case_id="V2Q-SSD-U4-THIN-0015",
    category="enterprise_ssd",
    case_class="AUTHORITATIVE",
    evidence_kind="SYNTHETIC",
    input_shape="LIVE_SHAPE",
    challenge_tags=(
        "missing_candidate_mpn",
        "missing_critical_specs",
        "insufficient_evidence",
    ),
    request_mpn="SYN-SSD-3840-U3",
    request_description="3.84TB U.3 NVMe data center SSD",
    obs=Obs(title="NVMe SSD"),
    expected_substate="U4_NO_MPN",
    expected_primary_signal="NO_RELATION",
    expected_decision="UNCERTAIN",
    expected_missing_dimensions=("CAPACITY", "FORM_FACTOR"),
    expected_reason_code="UNCERTAIN_MISSING_CRITICAL_ATTRIBUTES",
    label_source_kind="CONTRACT_GROUNDED",
    label_source="synthetic by-construction scenario (corpus 1.0.0)",
    label_evidence=(
        "The published title is only 'NVMe SSD': no capacity, no form "
        "factor, no family designation, no identifier. The critical "
        "identity dimensions are absent from all supplied evidence; the "
        "frozen prompt requires UNCERTAIN with the gap named, never a "
        "guess in either direction."
    ),
    reviewer="PRODUCT-INTEL.Q3A.CORPUS-AUTHOR (synthetic by-construction)",
    reviewer_status="REVIEWED",
    ambiguity="UNAMBIGUOUS",
)

_S16 = CaseDecl(
    case_id="V2Q-NIC-U4-ROLE-0016",
    category="network_adapter",
    case_class="AUTHORITATIVE",
    evidence_kind="SYNTHETIC",
    input_shape="LIVE_SHAPE",
    challenge_tags=("missing_candidate_mpn", "cross_category"),
    request_mpn="SYN-NIC-25GE-SFP",
    request_description="25GbE SFP28 network interface card",
    obs=Obs(
        title="PCIe 4.0 NVMe M.2 2280 2TB Solid State Drive",
        price="50",
    ),
    expected_substate="U4_NO_MPN",
    expected_primary_signal="NO_RELATION",
    expected_decision="NO_MATCH",
    expected_conflict_classes=("PRODUCT_ROLE",),
    expected_reason_code="NO_MATCH_PRODUCT_ROLE",
    label_source_kind="CONTRACT_GROUNDED",
    label_source="synthetic by-construction scenario (corpus 1.0.0)",
    label_evidence=(
        "By construction the listing publishes a solid-state drive, a "
        "different product category and role than the requested network "
        "interface card. A cross-category listing is the ALWAYS_HARD "
        "PRODUCT_ROLE conflict -> NO_MATCH; commercial equivalence "
        "across product categories does not exist."
    ),
    reviewer="PRODUCT-INTEL.Q3A.CORPUS-AUTHOR (synthetic by-construction)",
    reviewer_status="REVIEWED",
    ambiguity="UNAMBIGUOUS",
)

_S17 = CaseDecl(
    case_id="V2Q-SSD-U4-COND-0017",
    category="enterprise_ssd",
    case_class="AUTHORITATIVE",
    evidence_kind="SYNTHETIC",
    input_shape="LIVE_SHAPE",
    challenge_tags=("condition_only_difference",),
    request_mpn="SYN-SSD-3840-U3",
    request_description="3.84TB U.3 NVMe data center SSD, new",
    obs=Obs(
        title="3.84TB U.3 NVMe SSD, data center",
        condition="Refurbished",
    ),
    expected_substate="U4_NO_MPN",
    expected_primary_signal="NO_RELATION",
    expected_decision="MATCH",
    label_source_kind="CONTRACT_GROUNDED",
    label_source="synthetic by-construction scenario (corpus 1.0.0)",
    label_evidence=(
        "All published identity attributes align by construction; the "
        "only difference is condition (published 'Refurbished' vs the "
        "requested 'new'). The frozen taxonomy is explicit: CONDITION is "
        "PRICE_DIMENSION_ONLY, never an identity conflict. A NO_MATCH on "
        "condition alone would be a false NO_MATCH; the correct "
        "commercial-identity decision is MATCH."
    ),
    reviewer="PRODUCT-INTEL.Q3A.CORPUS-AUTHOR (synthetic by-construction)",
    reviewer_status="REVIEWED",
    ambiguity="UNAMBIGUOUS",
)

# -- U5 NEAR_MISS -------------------------------------------------------------

_S18 = CaseDecl(
    case_id="V2Q-SSD-U5NM1-MICRON-0018",
    category="enterprise_ssd",
    case_class="AUTHORITATIVE",
    evidence_kind="RECORDED_FIXTURE",
    input_shape="LIVE_SHAPE",
    challenge_tags=(
        "near_miss_truncated",
        "customer_retrieval_alias",
        "sales_unit_unproven",
    ),
    request_mpn="MTFDKCC3T8TGP-1BK1DABYYR",
    request_description="Micron 7500 4TB U.3 NVMe SSD",
    obs=Obs(
        mpn="MTFDKCC3T8TGP-1BK1DABYY",
        title="Micron 7500 4TB U.3 NVMe SSD Data Center",
        brand="Micron",
    ),
    provenances=("CUSTOMER_RETRIEVAL_RELATION",),
    reviewed_context=_micron_reviewed_ctx("MTFDKCC3T8TGP-1BK1DABYYR"),
    expected_substate="U5_NEAR_MISS_MPN",
    expected_primary_signal="NEAR_MISS_TRUNCATION",
    expected_decision="UNCERTAIN",
    expected_missing_dimensions=("PACKAGING_QUANTITY",),
    expected_reason_code="UNCERTAIN_MISSING_CRITICAL_ATTRIBUTES",
    commercial_sales_unit_safety=True,
    label_source_kind="REVIEWED_SOURCE_GROUNDED",
    label_source=(
        "tests/fixtures/pages/micron_7500_part_catalog.json (recorded "
        "4D-D fixture, 2026-09-22, body digest "
        + MICRON_CATALOG_FIXTURE_BODY_SHA256[:12]
        + "...); product_intelligence/research/micron_packaging_alias.py "
        "(frozen 4D-D v1 customer R/T rule)"
    ),
    label_evidence=(
        "Motivating case. The candidate's published MPN is the exact "
        "recorded catalog part '7500 4TB U.3 SSD'; the requested form "
        "differs by a truncated final 'R'. The recorded 4D-D fixture "
        "establishes the base part's identity, but the R/T family "
        "relation is a CUSTOMER-DEFINED retrieval rule: no manufacturer "
        "document states what the final R suffix denotes (the 4D-D "
        "module records this explicitly), so the R form's commercial "
        "sales unit is UNPROVEN. Sharing a base identifier is not "
        "equivalence: physical-product family membership (grounded) is "
        "distinct from sales-unit comparability (unproven). The frozen "
        "prompt's never-infer rule requires UNCERTAIN with "
        "PACKAGING_QUANTITY named missing; a false MATCH here is the "
        "exact commercial-safety error the case exists to catch. The "
        "customer-retrieval relation carries zero identity authority."
    ),
    reviewer="PRODUCT-INTEL.Q3A.CORPUS-AUTHOR (recorded fixture + frozen 4D-D rule)",
    reviewer_status="REVIEWED",
    ambiguity="UNAMBIGUOUS",
)

_S19 = CaseDecl(
    case_id="V2Q-SSD-U5NM1-REVCONFLICT-0019",
    category="enterprise_ssd",
    case_class="AUTHORITATIVE",
    evidence_kind="SYNTHETIC",
    input_shape="LIVE_SHAPE",
    challenge_tags=(
        "near_miss_truncated",
        "different_capacity",
        "different_interface",
        "multi_conflict",
    ),
    request_mpn="SYN-SSD-3840-G4",
    request_description="3.84TB PCIe Gen4 U.3 NVMe SSD",
    obs=Obs(
        mpn="SYN-SSD-3840-G4U",
        title="7.68TB PCIe Gen5 U.3 NVMe SSD",
    ),
    expected_substate="U5_NEAR_MISS_MPN",
    expected_primary_signal="NEAR_MISS_TRUNCATION",
    expected_decision="NO_MATCH",
    expected_conflict_classes=("CAPACITY", "INTERFACE"),
    expected_reason_code="NO_MATCH_MULTIPLE_CONFLICTS",
    label_source_kind="CONTRACT_GROUNDED",
    label_source="synthetic by-construction scenario (corpus 1.0.0)",
    label_evidence=(
        "The candidate identifier is a reverse-direction truncation "
        "near miss (the requested key is a strict prefix), and the "
        "published title states two ALWAYS_HARD conflicts by "
        "construction: capacity 7.68TB vs 3.84TB and interface Gen5 vs "
        "Gen4. Published attribute conflicts decide NO_MATCH regardless "
        "of the identifier shape."
    ),
    reviewer="PRODUCT-INTEL.Q3A.CORPUS-AUTHOR (synthetic by-construction)",
    reviewer_status="REVIEWED",
    ambiguity="UNAMBIGUOUS",
)

_S20 = CaseDecl(
    case_id="V2Q-SSD-U5NM2-RELAUTH-0020",
    category="enterprise_ssd",
    case_class="AUTHORITATIVE",
    evidence_kind="SYNTHETIC",
    input_shape="LIVE_SHAPE",
    challenge_tags=("near_miss_one_char", "reviewed_relation_authority"),
    request_mpn="SYN-SSD-ABCD-01",
    request_description="Synthetic 3.84TB U.3 NVMe SSD, revision 01",
    obs=Obs(
        mpn="SYN-SSD-ABCD-02",
        title="Synthetic 3.84TB U.3 NVMe SSD, revision 02",
    ),
    provenances=("MANUFACTURER_RELATION_AUTHORITY",),
    expected_substate="U5_NEAR_MISS_MPN",
    expected_primary_signal="NEAR_MISS_SUBSTITUTION",
    expected_decision="MATCH",
    expected_reason_code="MATCH_AUTHORIZED_IDENTIFIER_RELATION",
    label_source_kind="CONTRACT_GROUNDED",
    label_source="synthetic by-construction scenario (corpus 1.0.0)",
    label_evidence=(
        "The scenario explicitly carries labeled manufacturer "
        "relationship authority (MANUFACTURER_RELATION_AUTHORITY), which "
        "by construction establishes the 01/02 identifier relation; the "
        "frozen prompt names that provenance as stronger evidence and "
        "the bounded reason vocabulary includes "
        "MATCH_AUTHORIZED_IDENTIFIER_RELATION for exactly this shape. "
        "All other attributes align by construction; no conflict is "
        "published. (Synthetic: the 'reviewed authority' is a "
        "by-construction scenario input, not a real manufacturer "
        "document.)"
    ),
    reviewer="PRODUCT-INTEL.Q3A.CORPUS-AUTHOR (synthetic by-construction)",
    reviewer_status="REVIEWED",
    ambiguity="UNAMBIGUOUS",
)

_S21 = CaseDecl(
    case_id="V2Q-SSD-U5NM2-NOAUTH-0021",
    category="enterprise_ssd",
    case_class="AMBIGUOUS",
    evidence_kind="SYNTHETIC",
    input_shape="LIVE_SHAPE",
    challenge_tags=("near_miss_one_char",),
    request_mpn="SYN-SSD-ABCD-01",
    request_description="Synthetic 3.84TB U.3 NVMe SSD",
    obs=Obs(
        mpn="SYN-SSD-ABCD-02",
        title="Synthetic 3.84TB U.3 NVMe SSD",
    ),
    expected_substate="U5_NEAR_MISS_MPN",
    expected_primary_signal="NEAR_MISS_SUBSTITUTION",
    expected_decision="UNCERTAIN",
    acceptable_decisions=("NO_MATCH", "UNCERTAIN"),
    label_source_kind="CONTRACT_GROUNDED",
    label_source="synthetic by-construction scenario (corpus 1.0.0)",
    label_evidence=(
        "One-character substitution near miss with NO reviewed "
        "relationship authority and no published attribute difference. "
        "The frozen near-miss semantics state a one-character "
        "difference CAN mean a different revision - but the scenario "
        "publishes nothing proving it does. NO_MATCH (treat as "
        "different revision) and UNCERTAIN (insufficient evidence) are "
        "both defensible; MATCH is not (no identifier relation is "
        "established, and the frozen table requires reviewed relation "
        "authority for this substate in any future automatic tier)."
    ),
    reviewer="PRODUCT-INTEL.Q3A.CORPUS-AUTHOR (synthetic by-construction)",
    reviewer_status="REVIEWED",
    ambiguity="CONTESTABLE",
)

_S22 = CaseDecl(
    case_id="V2Q-SSD-U5NM1-ALIAS-0022",
    category="enterprise_ssd",
    case_class="AUTHORITATIVE",
    evidence_kind="SYNTHETIC",
    input_shape="LIVE_SHAPE",
    challenge_tags=(
        "customer_retrieval_alias",
        "near_miss_truncated",
        "sales_unit_unproven",
    ),
    request_mpn="MTFDKCC3T8TGP-1BK1DABYYT",
    request_description="Micron 7500 4TB U.3 NVMe SSD",
    obs=Obs(
        mpn="MTFDKCC3T8TGP-1BK1DABYY",
        title="Micron 7500 4TB U.3 NVMe SSD Data Center",
        brand="Micron",
    ),
    provenances=("CUSTOMER_RETRIEVAL_RELATION",),
    expected_substate="U5_NEAR_MISS_MPN",
    expected_primary_signal="NEAR_MISS_TRUNCATION",
    expected_decision="UNCERTAIN",
    expected_missing_dimensions=("PACKAGING_QUANTITY",),
    expected_reason_code="UNCERTAIN_MISSING_CRITICAL_ATTRIBUTES",
    commercial_sales_unit_safety=True,
    label_source_kind="CONTRACT_GROUNDED",
    label_source=(
        "frozen 4D-D v1 customer R/T rule "
        "(product_intelligence/research/micron_packaging_alias.py); "
        "recorded catalog context "
        "(tests/fixtures/pages/micron_7500_part_catalog.json)"
    ),
    label_evidence=(
        "Same family shape as the motivating case, without the reviewed "
        "target context: only the customer-retrieval relation is "
        "present. The frozen contract assigns CUSTOMER_RETRIEVAL_RELATION "
        "ZERO identity authority (retrieval hint only); the T form's "
        "sales unit is unproven by manufacturer-stated evidence. The "
        "alias must not promote the pair to MATCH: the independent "
        "commercial answer on this evidence is UNCERTAIN with the "
        "sales-unit gap named."
    ),
    reviewer="PRODUCT-INTEL.Q3A.CORPUS-AUTHOR (frozen rule + recorded fixture)",
    reviewer_status="REVIEWED",
    ambiguity="UNAMBIGUOUS",
)

_S23 = CaseDecl(
    case_id="V2Q-SSD-U5NM2-PRODCONTEXT-0023",
    category="enterprise_ssd",
    case_class="AMBIGUOUS",
    evidence_kind="SYNTHETIC",
    input_shape="LIVE_SHAPE",
    challenge_tags=(
        "manufacturer_product_context_only",
        "near_miss_one_char",
    ),
    request_mpn="SYN-SSD-ABCD-01",
    request_description="Synthetic 3.84TB U.3 NVMe SSD",
    obs=Obs(
        mpn="SYN-SSD-ABCD-02",
        title="Synthetic 3.84TB U.3 NVMe SSD",
    ),
    provenances=("MANUFACTURER_PRODUCT_CONTEXT",),
    authority_facts=(
        ("CAPACITY", ("LISTING_PRODUCT_TITLE",)),
        ("FORM_FACTOR", ("LISTING_PRODUCT_TITLE",)),
    ),
    expected_substate="U5_NEAR_MISS_MPN",
    expected_primary_signal="NEAR_MISS_SUBSTITUTION",
    expected_decision="UNCERTAIN",
    acceptable_decisions=("NO_MATCH", "UNCERTAIN"),
    label_source_kind="CONTRACT_GROUNDED",
    label_source="synthetic by-construction scenario (corpus 1.0.0)",
    label_evidence=(
        "MANUFACTURER_PRODUCT_CONTEXT grounds product facts (the "
        "authority-side profile reaches STRONG by construction: two "
        "hard dimensions title-grounded) but the frozen capability set "
        "excludes ESTABLISH_IDENTIFIER_RELATIONSHIP: product context "
        "without relationship authority does not establish the 01/02 "
        "identifier relation. The NM-2 substate keeps its conservative "
        "policy; NO_MATCH and UNCERTAIN are both defensible, MATCH is "
        "not."
    ),
    reviewer="PRODUCT-INTEL.Q3A.CORPUS-AUTHOR (synthetic by-construction)",
    reviewer_status="REVIEWED",
    ambiguity="CONTESTABLE",
)

# -- Attribute-conflict battery -----------------------------------------------

_S24 = CaseDecl(
    case_id="V2Q-SSD-ATTR-CAPACITY-0024",
    category="enterprise_ssd",
    case_class="AUTHORITATIVE",
    evidence_kind="SYNTHETIC",
    input_shape="LIVE_SHAPE",
    challenge_tags=("different_capacity",),
    request_mpn="SYN-SSD-3840-U3",
    request_description="3.84TB U.3 NVMe data center SSD",
    obs=Obs(title="7.68TB U.3 NVMe SSD, data center"),
    expected_substate="U4_NO_MPN",
    expected_primary_signal="NO_RELATION",
    expected_decision="NO_MATCH",
    expected_conflict_classes=("CAPACITY",),
    expected_reason_code="NO_MATCH_CAPACITY",
    label_source_kind="CONTRACT_GROUNDED",
    label_source="synthetic by-construction scenario (corpus 1.0.0)",
    label_evidence=(
        "The published title states 7.68TB against the requested 3.84TB "
        "by construction; capacity is ALWAYS_HARD -> NO_MATCH."
    ),
    reviewer="PRODUCT-INTEL.Q3A.CORPUS-AUTHOR (synthetic by-construction)",
    reviewer_status="REVIEWED",
    ambiguity="UNAMBIGUOUS",
)

_S25 = CaseDecl(
    case_id="V2Q-DIMM-ATTR-CAPACITY-0025",
    category="server_memory",
    case_class="AUTHORITATIVE",
    evidence_kind="SYNTHETIC",
    input_shape="LIVE_SHAPE",
    challenge_tags=("different_capacity",),
    request_mpn="SYN-DIMM-96G-6400",
    request_description="96GB DDR5-6400 server memory",
    obs=Obs(title="128GB DDR5-6400 Server Memory Module"),
    expected_substate="U4_NO_MPN",
    expected_primary_signal="NO_RELATION",
    expected_decision="NO_MATCH",
    expected_conflict_classes=("CAPACITY",),
    expected_reason_code="NO_MATCH_CAPACITY",
    label_source_kind="CONTRACT_GROUNDED",
    label_source="synthetic by-construction scenario (corpus 1.0.0)",
    label_evidence=(
        "Published capacity 128GB vs requested 96GB by construction; "
        "memory capacity is the ALWAYS_HARD CAPACITY dimension -> "
        "NO_MATCH (different category than SSD: memory module)."
    ),
    reviewer="PRODUCT-INTEL.Q3A.CORPUS-AUTHOR (synthetic by-construction)",
    reviewer_status="REVIEWED",
    ambiguity="UNAMBIGUOUS",
)

_S26 = CaseDecl(
    case_id="V2Q-GPU-ATTR-MEM-0026",
    category="workstation_gpu",
    case_class="AUTHORITATIVE",
    evidence_kind="SYNTHETIC",
    input_shape="LIVE_SHAPE",
    challenge_tags=("different_capacity",),
    request_mpn="SYN-GPU-24G",
    request_description="24GB workstation GPU, PCIe",
    obs=Obs(title="48GB Workstation GPU, PCIe 4.0"),
    expected_substate="U4_NO_MPN",
    expected_primary_signal="NO_RELATION",
    expected_decision="NO_MATCH",
    expected_conflict_classes=("CAPACITY",),
    expected_reason_code="NO_MATCH_CAPACITY",
    label_source_kind="CONTRACT_GROUNDED",
    label_source="synthetic by-construction scenario (corpus 1.0.0)",
    label_evidence=(
        "Published memory size 48GB vs requested 24GB by construction; "
        "GPU memory size is the capacity dimension (ALWAYS_HARD) -> "
        "NO_MATCH (different category: workstation GPU)."
    ),
    reviewer="PRODUCT-INTEL.Q3A.CORPUS-AUTHOR (synthetic by-construction)",
    reviewer_status="REVIEWED",
    ambiguity="UNAMBIGUOUS",
)

_S27 = CaseDecl(
    case_id="V2Q-CPU-ATTR-GEN-0027",
    category="processor",
    case_class="AUTHORITATIVE",
    evidence_kind="SYNTHETIC",
    input_shape="LIVE_SHAPE",
    challenge_tags=("different_generation",),
    request_mpn="SYN-CPU-9004-32",
    request_description="32-core server CPU, generation 9004",
    obs=Obs(title="32-Core Server CPU, Generation 9005, Socket SP5"),
    expected_substate="U4_NO_MPN",
    expected_primary_signal="NO_RELATION",
    expected_decision="NO_MATCH",
    expected_conflict_classes=("GENERATION",),
    expected_reason_code="NO_MATCH_GENERATION",
    label_source_kind="CONTRACT_GROUNDED",
    label_source="synthetic by-construction scenario (corpus 1.0.0)",
    label_evidence=(
        "Published generation 9005 vs requested 9004 by construction; "
        "generation is ALWAYS_HARD -> NO_MATCH (different category: "
        "processor)."
    ),
    reviewer="PRODUCT-INTEL.Q3A.CORPUS-AUTHOR (synthetic by-construction)",
    reviewer_status="REVIEWED",
    ambiguity="UNAMBIGUOUS",
)

_S28 = CaseDecl(
    case_id="V2Q-SSD-ATTR-IFACE-0028",
    category="enterprise_ssd",
    case_class="AUTHORITATIVE",
    evidence_kind="SYNTHETIC",
    input_shape="LIVE_SHAPE",
    challenge_tags=("different_interface",),
    request_mpn="SYN-SSD-3840-SATA",
    request_description="3.84TB SATA 6Gbps 2.5-inch enterprise SSD",
    obs=Obs(title="3.84TB NVMe U.3 2.5-inch Enterprise SSD"),
    expected_substate="U4_NO_MPN",
    expected_primary_signal="NO_RELATION",
    expected_decision="NO_MATCH",
    expected_conflict_classes=("INTERFACE",),
    expected_reason_code="NO_MATCH_INTERFACE",
    label_source_kind="CONTRACT_GROUNDED",
    label_source="synthetic by-construction scenario (corpus 1.0.0)",
    label_evidence=(
        "Published interface NVMe vs requested SATA 6Gbps by "
        "construction (capacity and size align); interface is "
        "ALWAYS_HARD -> NO_MATCH."
    ),
    reviewer="PRODUCT-INTEL.Q3A.CORPUS-AUTHOR (synthetic by-construction)",
    reviewer_status="REVIEWED",
    ambiguity="UNAMBIGUOUS",
)

_S29 = CaseDecl(
    case_id="V2Q-SSD-ATTR-FF-0029",
    category="enterprise_ssd",
    case_class="AUTHORITATIVE",
    evidence_kind="SYNTHETIC",
    input_shape="LIVE_SHAPE",
    challenge_tags=("different_form_factor",),
    request_mpn="SYN-SSD-1920-M2",
    request_description="1.92TB M.2 2280 NVMe SSD",
    obs=Obs(title="1.92TB U.3 2.5-inch NVMe SSD"),
    expected_substate="U4_NO_MPN",
    expected_primary_signal="NO_RELATION",
    expected_decision="NO_MATCH",
    expected_conflict_classes=("FORM_FACTOR",),
    expected_reason_code="NO_MATCH_FORM_FACTOR",
    label_source_kind="CONTRACT_GROUNDED",
    label_source="synthetic by-construction scenario (corpus 1.0.0)",
    label_evidence=(
        "Published form factor U.3 2.5-inch vs requested M.2 2280 by "
        "construction (capacity aligns); form factor is ALWAYS_HARD -> "
        "NO_MATCH."
    ),
    reviewer="PRODUCT-INTEL.Q3A.CORPUS-AUTHOR (synthetic by-construction)",
    reviewer_status="REVIEWED",
    ambiguity="UNAMBIGUOUS",
)

_S30 = CaseDecl(
    case_id="V2Q-NIC-ATTR-IFACE-0030",
    category="network_adapter",
    case_class="AUTHORITATIVE",
    evidence_kind="SYNTHETIC",
    input_shape="LIVE_SHAPE",
    challenge_tags=("different_interface",),
    request_mpn="SYN-NIC-10GE",
    request_description="10GbE SFP+ network interface card",
    obs=Obs(title="25GbE SFP28 PCIe Network Interface Card"),
    expected_substate="U4_NO_MPN",
    expected_primary_signal="NO_RELATION",
    expected_decision="NO_MATCH",
    expected_conflict_classes=("INTERFACE",),
    expected_reason_code="NO_MATCH_INTERFACE",
    label_source_kind="CONTRACT_GROUNDED",
    label_source="synthetic by-construction scenario (corpus 1.0.0)",
    label_evidence=(
        "Published interface 25GbE SFP28 vs requested 10GbE SFP+ by "
        "construction; interface speed is the ALWAYS_HARD INTERFACE "
        "dimension -> NO_MATCH (different category: network adapter)."
    ),
    reviewer="PRODUCT-INTEL.Q3A.CORPUS-AUTHOR (synthetic by-construction)",
    reviewer_status="REVIEWED",
    ambiguity="UNAMBIGUOUS",
)

_S31 = CaseDecl(
    case_id="V2Q-SSD-ACC-CADDY-0031",
    category="enterprise_ssd",
    case_class="AUTHORITATIVE",
    evidence_kind="RECORDED_FIXTURE",
    input_shape="LIVE_SHAPE",
    challenge_tags=("accessory_vs_product", "compatibility_wording"),
    request_mpn="MZ1L2960HCJR-00A07",
    request_description="Samsung SSD PM9A3 960GB M.2 NVMe PCIe Gen4",
    obs=Obs(
        title="Replacement SSD caddy for MZ1L2960HCJR-00A07",
    ),
    expected_substate="U1_TITLE_MPN",
    expected_primary_signal="TITLE_MPN_TOKEN",
    expected_decision="NO_MATCH",
    expected_conflict_classes=("ACCESSORY_RELATION",),
    expected_reason_code="NO_MATCH_ACCESSORY",
    label_source_kind="REVIEWED_SOURCE_GROUNDED",
    label_source=(
        "evaluation/semantic_corpus/cases.json SMQ-0006 "
        "(provenance: project_uat)"
    ),
    label_evidence=(
        "The recorded project-UAT expectation: 'replacement caddy for' "
        "is compatibility/reference wording; the listed product is a "
        "caddy (accessory), not the SSD. ACCESSORY_RELATION is "
        "ALWAYS_HARD -> NO_MATCH."
    ),
    reviewer="PROJECT_UAT (recorded in repository)",
    reviewer_status="REVIEWED",
    ambiguity="UNAMBIGUOUS",
)

_S32 = CaseDecl(
    case_id="V2Q-SSD-SU-TRAY-0032",
    category="enterprise_ssd",
    case_class="AUTHORITATIVE",
    evidence_kind="SYNTHETIC",
    input_shape="CONTRACT_SURFACE",
    challenge_tags=("tray_vs_retail",),
    request_mpn="SYN-SSD-3840-U3",
    request_description="3.84TB U.3 NVMe data center SSD, retail single unit",
    obs=Obs(
        sku="STOR-3840-U3-TRAY20",
        title="3.84TB U.3 NVMe SSD, data center (tray)",
    ),
    sales_unit=SalesUnit(
        kind="TRAY_OR_FACTORY_PACK",
        quantity=None,
        raw_detail="tray of 20",
    ),
    expected_substate="U2_SKU_ONLY",
    expected_primary_signal="SKU_NOT_TARGET",
    expected_decision="NO_MATCH",
    expected_conflict_classes=("PACKAGING_QUANTITY",),
    expected_reason_code="NO_MATCH_PACKAGING",
    commercial_sales_unit_safety=True,
    label_source_kind="CONTRACT_GROUNDED",
    label_source="synthetic by-construction scenario (corpus 1.0.0)",
    label_evidence=(
        "By construction the request is a retail single unit and the "
        "candidate publishes (in its structured packaging field) a tray "
        "of 20. The frozen contract is explicit: physical-product "
        "equivalence is never sales-unit equivalence; a tray/factory "
        "pack candidate against a retail single-unit target carries the "
        "ALWAYS_HARD PACKAGING_QUANTITY conflict -> NO_MATCH. "
        "(CONTRACT_SURFACE: the live extractor publishes no packaging "
        "field today; the frozen channel represents this observation.)"
    ),
    reviewer="PRODUCT-INTEL.Q3A.CORPUS-AUTHOR (synthetic by-construction)",
    reviewer_status="REVIEWED",
    ambiguity="UNAMBIGUOUS",
)

_S33 = CaseDecl(
    case_id="V2Q-SSD-SU-MULTI-0033",
    category="enterprise_ssd",
    case_class="AUTHORITATIVE",
    evidence_kind="SYNTHETIC",
    input_shape="CONTRACT_SURFACE",
    challenge_tags=("single_vs_multipack",),
    request_mpn="SYN-SSD-1920-M2",
    request_description="1.92TB M.2 2280 NVMe SSD, single unit",
    obs=Obs(
        sku="PK-1920-M2-4",
        title="1.92TB M.2 NVMe SSD (pack of 4)",
    ),
    sales_unit=SalesUnit(
        kind="PACK_QUANTITY",
        quantity=4,
        raw_detail="pack of 4",
    ),
    expected_substate="U2_SKU_ONLY",
    expected_primary_signal="SKU_NOT_TARGET",
    expected_decision="NO_MATCH",
    expected_conflict_classes=("PACKAGING_QUANTITY",),
    expected_reason_code="NO_MATCH_PACKAGING",
    commercial_sales_unit_safety=True,
    label_source_kind="CONTRACT_GROUNDED",
    label_source="synthetic by-construction scenario (corpus 1.0.0)",
    label_evidence=(
        "By construction the request is a single unit and the candidate "
        "publishes a pack of 4 in its structured packaging field. "
        "Single-versus-multi-pack is a frozen ALWAYS_HARD "
        "PACKAGING_QUANTITY conflict -> NO_MATCH; the same physical "
        "drive is not pricing-comparable as the same sales unit."
    ),
    reviewer="PRODUCT-INTEL.Q3A.CORPUS-AUTHOR (synthetic by-construction)",
    reviewer_status="REVIEWED",
    ambiguity="UNAMBIGUOUS",
)

_S34 = CaseDecl(
    case_id="V2Q-GPU-SU-BUNDLE-0034",
    category="workstation_gpu",
    case_class="AUTHORITATIVE",
    evidence_kind="SYNTHETIC",
    input_shape="CONTRACT_SURFACE",
    challenge_tags=("standalone_vs_bundle",),
    request_mpn="SYN-GPU-24G",
    request_description="24GB workstation GPU, standalone card",
    obs=Obs(
        title="Workstation GPU 24GB + 2x Power Cable + Bracket Kit",
    ),
    sales_unit=SalesUnit(
        kind="BUNDLE",
        quantity=None,
        raw_detail="GPU + power cables + bracket kit",
    ),
    expected_substate="U4_NO_MPN",
    expected_primary_signal="NO_RELATION",
    expected_decision="NO_MATCH",
    expected_conflict_classes=("BUNDLE",),
    expected_reason_code="NO_MATCH_BUNDLE",
    commercial_sales_unit_safety=True,
    label_source_kind="CONTRACT_GROUNDED",
    label_source="synthetic by-construction scenario (corpus 1.0.0)",
    label_evidence=(
        "By construction the request is a standalone card and the "
        "candidate publishes a bundle (card + cables + bracket) in its "
        "structured packaging field. Standalone-versus-bundle is the "
        "ALWAYS_HARD BUNDLE conflict -> NO_MATCH (different category: "
        "workstation GPU)."
    ),
    reviewer="PRODUCT-INTEL.Q3A.CORPUS-AUTHOR (synthetic by-construction)",
    reviewer_status="REVIEWED",
    ambiguity="UNAMBIGUOUS",
)

_S35 = CaseDecl(
    case_id="V2Q-SSD-SAME-ALTWORDING-0035",
    category="enterprise_ssd",
    case_class="AUTHORITATIVE",
    evidence_kind="SYNTHETIC",
    input_shape="LIVE_SHAPE",
    challenge_tags=("exact_product_alt_wording", "different_sku_same_product"),
    request_mpn="SYN-SSD-3840-U3",
    request_description="3.84TB U.3 NVMe data center SSD",
    obs=Obs(
        sku="DC-SSD-3.84-U3-NEW",
        title=(
            "Enterprise NVMe Solid State Drive, 3.84 Terabytes, U.3 "
            "2.5in, PCIe Gen4"
        ),
    ),
    expected_substate="U2_SKU_ONLY",
    expected_primary_signal="SKU_NOT_TARGET",
    expected_decision="MATCH",
    label_source_kind="CONTRACT_GROUNDED",
    label_source="synthetic by-construction scenario (corpus 1.0.0)",
    label_evidence=(
        "The exact product expressed in different legitimate listing "
        "wording by construction: '3.84 Terabytes' = 3.84TB, 'U.3 2.5in' "
        "= U.3 form factor, 'Enterprise NVMe Solid State Drive' = the "
        "requested family/role. A different retailer SKU is not proof of "
        "a different product (frozen prompt). No conflicting attribute "
        "is published; commercial equivalence holds."
    ),
    reviewer="PRODUCT-INTEL.Q3A.CORPUS-AUTHOR (synthetic by-construction)",
    reviewer_status="REVIEWED",
    ambiguity="UNAMBIGUOUS",
)

_S36 = CaseDecl(
    case_id="V2Q-SSD-MULTI-CONFLICT-0036",
    category="enterprise_ssd",
    case_class="AUTHORITATIVE",
    evidence_kind="SYNTHETIC",
    input_shape="LIVE_SHAPE",
    challenge_tags=(
        "multi_conflict",
        "different_capacity",
        "different_form_factor",
        "different_interface",
    ),
    request_mpn="SYN-SSD-3840-U3-GEN4",
    request_description="3.84TB U.3 NVMe PCIe Gen4 data center SSD",
    obs=Obs(title="7.68TB M.2 NVMe PCIe Gen5 SSD"),
    expected_substate="U4_NO_MPN",
    expected_primary_signal="NO_RELATION",
    expected_decision="NO_MATCH",
    expected_conflict_classes=("CAPACITY", "FORM_FACTOR", "INTERFACE"),
    expected_reason_code="NO_MATCH_MULTIPLE_CONFLICTS",
    label_source_kind="CONTRACT_GROUNDED",
    label_source="synthetic by-construction scenario (corpus 1.0.0)",
    label_evidence=(
        "By construction three ALWAYS_HARD conflicts are published "
        "simultaneously (7.68TB vs 3.84TB; M.2 vs U.3; Gen5 vs Gen4). "
        "Two or more hard conflicts jointly establish non-equivalence; "
        "the bounded reason NO_MATCH_MULTIPLE_CONFLICTS names this "
        "shape."
    ),
    reviewer="PRODUCT-INTEL.Q3A.CORPUS-AUTHOR (synthetic by-construction)",
    reviewer_status="REVIEWED",
    ambiguity="UNAMBIGUOUS",
)

_S37 = CaseDecl(
    case_id="V2Q-SSD-CONTRA-0037",
    category="enterprise_ssd",
    case_class="AUTHORITATIVE",
    evidence_kind="SYNTHETIC",
    input_shape="CONTRACT_SURFACE",
    challenge_tags=("contradictory_listing_evidence",),
    request_mpn="SYN-SSD-3840-U3",
    request_description="3.84TB U.3 NVMe data center SSD",
    obs=Obs(title="3.84TB U.3 NVMe SSD, data center"),
    raw_specification_text="Capacity: 7.68TB; Form factor: U.3",
    expected_substate="U4_NO_MPN",
    expected_primary_signal="NO_RELATION",
    expected_decision="UNCERTAIN",
    label_source_kind="CONTRACT_GROUNDED",
    label_source="synthetic by-construction scenario (corpus 1.0.0)",
    label_evidence=(
        "The published title states 3.84TB while the published "
        "specification text states 7.68TB: the listing contradicts "
        "itself. Neither value can be taken as the product's capacity on "
        "the supplied evidence, so no conflict class can be established "
        "and no equivalence can be affirmed. The frozen prompt: "
        "insufficient or ambiguous evidence -> UNCERTAIN, never a "
        "guess; asserting CAPACITY either way would be manufacturing a "
        "fact from contradictory evidence."
    ),
    reviewer="PRODUCT-INTEL.Q3A.CORPUS-AUTHOR (synthetic by-construction)",
    reviewer_status="REVIEWED",
    ambiguity="UNAMBIGUOUS",
)

_S38 = CaseDecl(
    case_id="V2Q-SSD-SEO-MATCH-0038",
    category="enterprise_ssd",
    case_class="AUTHORITATIVE",
    evidence_kind="SYNTHETIC",
    input_shape="LIVE_SHAPE",
    challenge_tags=("misleading_seo", "exact_product_alt_wording"),
    request_mpn="SYN-SSD-3840-U3",
    request_description="3.84TB U.3 NVMe data center SSD",
    obs=Obs(
        title=(
            "SYN-SSD-3840-U3 | 3.84TB U.3 NVMe SSD | best price | free "
            "shipping | hot deal 2026 | data center enterprise"
        ),
    ),
    expected_substate="U1_TITLE_MPN",
    expected_primary_signal="TITLE_MPN_TOKEN",
    expected_decision="MATCH",
    label_source_kind="CONTRACT_GROUNDED",
    label_source="synthetic by-construction scenario (corpus 1.0.0)",
    label_evidence=(
        "SEO noise around an aligned product: the title publishes the "
        "exact requested MPN token and the aligned capacity/form factor; "
        "the marketing tokens ('best price', 'free shipping', 'hot "
        "deal') carry no product evidence in either direction. Misleading "
        "wording must not manufacture a false NO_MATCH; commercial "
        "equivalence holds on the supplied evidence."
    ),
    reviewer="PRODUCT-INTEL.Q3A.CORPUS-AUTHOR (synthetic by-construction)",
    reviewer_status="REVIEWED",
    ambiguity="UNAMBIGUOUS",
)

_S39 = CaseDecl(
    case_id="V2Q-DIMM-COND-0039",
    category="server_memory",
    case_class="AUTHORITATIVE",
    evidence_kind="SYNTHETIC",
    input_shape="LIVE_SHAPE",
    challenge_tags=("condition_only_difference",),
    request_mpn="SYN-DIMM-96G-6400",
    request_description="96GB DDR5-6400 server memory, new",
    obs=Obs(
        sku="MEM-96G-6400-REF",
        title="96GB DDR5-6400 MRDIMM Server Memory",
        condition="Open box",
    ),
    expected_substate="U2_SKU_ONLY",
    expected_primary_signal="SKU_NOT_TARGET",
    expected_decision="MATCH",
    label_source_kind="CONTRACT_GROUNDED",
    label_source="synthetic by-construction scenario (corpus 1.0.0)",
    label_evidence=(
        "All identity attributes align by construction; the only "
        "difference is published condition ('Open box' vs requested "
        "new). CONDITION is frozen PRICE_DIMENSION_ONLY - never an "
        "identity conflict (different category: server memory module)."
    ),
    reviewer="PRODUCT-INTEL.Q3A.CORPUS-AUTHOR (synthetic by-construction)",
    reviewer_status="REVIEWED",
    ambiguity="UNAMBIGUOUS",
)

_S40 = CaseDecl(
    case_id="V2Q-SSD-BRAND-CONTESTED-0040",
    category="enterprise_ssd",
    case_class="AMBIGUOUS",
    evidence_kind="SYNTHETIC",
    input_shape="LIVE_SHAPE",
    challenge_tags=("different_brand",),
    request_mpn="SYN-SSD-3840-U3",
    request_description="SyntheticBrand 3.84TB U.3 NVMe data center SSD",
    obs=Obs(
        title="OtherBrand 3.84TB U.3 NVMe Data Center SSD",
        brand="OtherBrand",
    ),
    expected_substate="U4_NO_MPN",
    expected_primary_signal="NO_RELATION",
    expected_decision="UNCERTAIN",
    acceptable_decisions=("NO_MATCH", "UNCERTAIN"),
    label_source_kind="CONTRACT_GROUNDED",
    label_source="synthetic by-construction scenario (corpus 1.0.0)",
    label_evidence=(
        "The candidate publishes a different brand than the requested "
        "product while all other attributes align. BRAND is a frozen "
        "REVIEWABLE conflict (material but resolvable by inspection): in "
        "real markets a different published brand may be a genuinely "
        "different product or an OEM/relabel of the same physical "
        "product, and the supplied evidence decides neither. NO_MATCH "
        "(published brand is material) and UNCERTAIN (inspection "
        "required) are both defensible; MATCH would ignore a published "
        "material difference."
    ),
    reviewer="PRODUCT-INTEL.Q3A.CORPUS-AUTHOR (synthetic by-construction)",
    reviewer_status="REVIEWED",
    ambiguity="CONTESTABLE",
)

_S41 = CaseDecl(
    case_id="V2Q-SSD-U1-PRODCTX-0041",
    category="enterprise_ssd",
    case_class="AUTHORITATIVE",
    evidence_kind="SYNTHETIC",
    input_shape="LIVE_SHAPE",
    challenge_tags=("manufacturer_product_context_only", "title_mpn_only"),
    request_mpn="SYN-SSD-3840-U3",
    request_description="3.84TB U.3 NVMe data center SSD",
    obs=Obs(
        title="3.84TB U.3 NVMe SSD, data center (SYN-SSD-3840-U3)",
    ),
    provenances=("MANUFACTURER_PRODUCT_CONTEXT",),
    authority_facts=(
        ("CAPACITY", ("LISTING_PRODUCT_TITLE",)),
        ("FORM_FACTOR", ("LISTING_PRODUCT_TITLE",)),
    ),
    expected_substate="U1_TITLE_MPN",
    expected_primary_signal="TITLE_MPN_TOKEN",
    expected_decision="MATCH",
    label_source_kind="CONTRACT_GROUNDED",
    label_source="synthetic by-construction scenario (corpus 1.0.0)",
    label_evidence=(
        "The title publishes the exact requested MPN token with aligned "
        "attributes by construction, and the scenario carries "
        "MANUFACTURER_PRODUCT_CONTEXT with a STRONG title-grounded "
        "authority profile (two hard dimensions). Product context "
        "strengthens product grounding but is not needed for the "
        "decision: the U1 state does not require reviewed relation "
        "authority, and the identifier + attribute evidence establishes "
        "commercial equivalence."
    ),
    reviewer="PRODUCT-INTEL.Q3A.CORPUS-AUTHOR (synthetic by-construction)",
    reviewer_status="REVIEWED",
    ambiguity="UNAMBIGUOUS",
)

_S42 = CaseDecl(
    case_id="V2Q-NIC-ACC-BRACKET-0042",
    category="network_adapter",
    case_class="AUTHORITATIVE",
    evidence_kind="SYNTHETIC",
    input_shape="LIVE_SHAPE",
    challenge_tags=("accessory_vs_product", "cross_category"),
    request_mpn="SYN-NIC-25GE-SFP",
    request_description="25GbE SFP28 network interface card",
    obs=Obs(
        title="Low-profile PCIe bracket and SAS cable kit",
        price="15",
    ),
    expected_substate="U4_NO_MPN",
    expected_primary_signal="NO_RELATION",
    expected_decision="NO_MATCH",
    expected_conflict_classes=("ACCESSORY_RELATION",),
    expected_reason_code="NO_MATCH_ACCESSORY",
    label_source_kind="CONTRACT_GROUNDED",
    label_source="synthetic by-construction scenario (corpus 1.0.0)",
    label_evidence=(
        "By construction the listing publishes a bracket/cable kit - an "
        "accessory - against the requested network interface card. "
        "ACCESSORY_RELATION is ALWAYS_HARD -> NO_MATCH (different "
        "category: network adapter)."
    ),
    reviewer="PRODUCT-INTEL.Q3A.CORPUS-AUTHOR (synthetic by-construction)",
    reviewer_status="REVIEWED",
    ambiguity="UNAMBIGUOUS",
)

_S43 = CaseDecl(
    case_id="V2Q-SSD-UNPROVEN-FORM-0043",
    category="enterprise_ssd",
    case_class="AMBIGUOUS",
    evidence_kind="SYNTHETIC",
    input_shape="LIVE_SHAPE",
    challenge_tags=(
        "missing_candidate_mpn",
        "missing_critical_specs",
        "insufficient_evidence",
    ),
    request_mpn="SYN-SSD-3840-U3",
    request_description="3.84TB U.3 NVMe data center SSD",
    obs=Obs(title="3.84TB NVMe SSD"),
    expected_substate="U4_NO_MPN",
    expected_primary_signal="NO_RELATION",
    expected_decision="UNCERTAIN",
    acceptable_decisions=("MATCH", "UNCERTAIN"),
    label_source_kind="CONTRACT_GROUNDED",
    label_source="synthetic by-construction scenario (corpus 1.0.0)",
    label_evidence=(
        "Capacity and interface align by construction, but the form "
        "factor (U.3 vs M.2 vs 2.5-inch) is published nowhere: a hard "
        "identity dimension is unproven. Neither equivalence (form "
        "factor unverified) nor non-equivalence (no contrary evidence) "
        "is established; MATCH and UNCERTAIN are both defensible."
    ),
    reviewer="PRODUCT-INTEL.Q3A.CORPUS-AUTHOR (synthetic by-construction)",
    reviewer_status="REVIEWED",
    ambiguity="CONTESTABLE",
)


# ---------------------------------------------------------------------------
# Contract-negative declarations (invalid states / schema violations /
# authority-boundary attacks). Each is a patch list applied to a valid
# base payload (declared by case id); the expected rejection class is
# bounded.
# ---------------------------------------------------------------------------

_CN_BASE_U1 = "V2Q-SSD-SEO-MATCH-0038"  # a valid U1 payload base
_CN_BASE_U5 = "V2Q-SSD-U5NM1-MICRON-0018"  # a valid U5 (reviewed ctx) base

_C1 = CaseDecl(
    case_id="V2Q-CN-VERIFIED-0044",
    category="enterprise_ssd",
    case_class="CONTRACT_NEGATIVE",
    evidence_kind="SYNTHETIC",
    input_shape="LIVE_SHAPE",
    challenge_tags=("title_mpn_only",),
    request_mpn="SYN-VER-1",
    request_description="verified-state attack probe",
    obs=Obs(mpn="SYN-VER-1", title="SYN-VER-1 drive"),
    base_payload_case_id=_CN_BASE_U1,
    patches=(
        (
            ("deterministic_identity_context", "identity_state"),
            "DETERMINISTIC_VERIFIED",
        ),
        (
            ("deterministic_identity_context", "substate"),
            "V_EXACT",
        ),
        (
            ("deterministic_identity_context", "primary_relationship_signal"),
            "EXACT",
        ),
        (("deterministic_identity_context", "relationship_signals"), ["EXACT"]),
        (
            ("deterministic_identity_context", "normalized_candidate_part_number"),
            "SYN-VER-1",
        ),
        (
            ("deterministic_identity_context", "relationship_requirement"),
            "NOT_APPLICABLE",
        ),
    ),
    expected_rejection_class="NON_UNCERTAIN_STATE",
)

_C2 = CaseDecl(
    case_id="V2Q-CN-CONFLICT-0045",
    category="enterprise_ssd",
    case_class="CONTRACT_NEGATIVE",
    evidence_kind="SYNTHETIC",
    input_shape="LIVE_SHAPE",
    challenge_tags=("title_mpn_only",),
    request_mpn="SYN-C-1",
    request_description="conflict-state attack probe",
    obs=Obs(mpn="SYN-C-2", title="SYN-C-2 drive"),
    base_payload_case_id=_CN_BASE_U1,
    patches=(
        (
            ("deterministic_identity_context", "identity_state"),
            "DETERMINISTIC_CONFLICT",
        ),
        (
            ("deterministic_identity_context", "substate"),
            "C1_INCOMPATIBLE_EXPLICIT_MPN",
        ),
        (
            ("deterministic_identity_context", "primary_relationship_signal"),
            "NO_RELATION",
        ),
        (("deterministic_identity_context", "relationship_signals"), ["NO_RELATION"]),
        (
            ("deterministic_identity_context", "normalized_requested_part_number"),
            "SYN-C-1",
        ),
        (
            ("deterministic_identity_context", "normalized_candidate_part_number"),
            "SYN-C-2",
        ),
        (
            ("deterministic_identity_context", "relationship_requirement"),
            "NOT_APPLICABLE",
        ),
    ),
    expected_rejection_class="NON_UNCERTAIN_STATE",
)

_C3 = CaseDecl(
    case_id="V2Q-CN-UNEVALUABLE-0046",
    category="enterprise_ssd",
    case_class="CONTRACT_NEGATIVE",
    evidence_kind="SYNTHETIC",
    input_shape="LIVE_SHAPE",
    challenge_tags=("title_mpn_only",),
    request_mpn="SYN-E1",
    request_description="unevaluable-state attack probe",
    obs=Obs(title="SYN-E1 probe"),
    base_payload_case_id=_CN_BASE_U1,
    patches=(
        (
            ("deterministic_identity_context", "identity_state"),
            "DETERMINISTIC_UNEVALUABLE",
        ),
        (
            ("deterministic_identity_context", "substate"),
            "E1_NO_TARGET_MPN",
        ),
        (
            ("deterministic_identity_context", "primary_relationship_signal"),
            "NO_RELATION",
        ),
        (("deterministic_identity_context", "relationship_signals"), ["NO_RELATION"]),
        (
            ("deterministic_identity_context", "normalized_requested_part_number"),
            "",
        ),
        (
            ("deterministic_identity_context", "normalized_candidate_part_number"),
            "",
        ),
        (
            ("deterministic_identity_context", "relationship_requirement"),
            "NOT_APPLICABLE",
        ),
    ),
    expected_rejection_class="NON_UNCERTAIN_STATE",
)

_C4 = CaseDecl(
    case_id="V2Q-CN-REQ-TAMPER-0047",
    category="enterprise_ssd",
    case_class="CONTRACT_NEGATIVE",
    evidence_kind="SYNTHETIC",
    input_shape="LIVE_SHAPE",
    challenge_tags=("title_mpn_only",),
    request_mpn="SYN-REQ-T",
    request_description="tampered requirement probe",
    obs=Obs(title="SYN-REQ-T (probe)"),
    base_payload_case_id=_CN_BASE_U1,
    patches=(
        (
            ("deterministic_identity_context", "relationship_requirement"),
            "REVIEWED_RELATION_AUTHORITY_REQUIRED",
        ),
    ),
    expected_rejection_class="FOREIGN_DETERMINISTIC_CONTEXT",
)

_C5 = CaseDecl(
    case_id="V2Q-CN-FOREIGN-SIGNAL-0048",
    category="enterprise_ssd",
    case_class="CONTRACT_NEGATIVE",
    evidence_kind="SYNTHETIC",
    input_shape="LIVE_SHAPE",
    challenge_tags=("title_mpn_only",),
    request_mpn="SYN-FS-1",
    request_description="foreign signal probe",
    obs=Obs(title="SYN-FS-1 (probe)"),
    base_payload_case_id=_CN_BASE_U1,
    patches=(
        (
            ("deterministic_identity_context", "substate"),
            "U2_SKU_ONLY",
        ),
        (
            ("deterministic_identity_context", "primary_relationship_signal"),
            "TITLE_MPN_TOKEN",
        ),
        (
            ("deterministic_identity_context", "relationship_signals"),
            ["TITLE_MPN_TOKEN"],
        ),
    ),
    expected_rejection_class="FOREIGN_DETERMINISTIC_CONTEXT",
)

_C6 = CaseDecl(
    case_id="V2Q-CN-STATE-MISMATCH-0049",
    category="enterprise_ssd",
    case_class="CONTRACT_NEGATIVE",
    evidence_kind="SYNTHETIC",
    input_shape="LIVE_SHAPE",
    challenge_tags=("title_mpn_only",),
    request_mpn="SYN-SM-1",
    request_description="state/substate mismatch probe",
    obs=Obs(title="SYN-SM-1 (probe)"),
    base_payload_case_id=_CN_BASE_U1,
    patches=(
        (("deterministic_identity_context", "substate"), "V_EXACT"),
    ),
    expected_rejection_class="FOREIGN_DETERMINISTIC_CONTEXT",
)

_C7 = CaseDecl(
    case_id="V2Q-CN-UNKNOWN-ENUM-0050",
    category="enterprise_ssd",
    case_class="CONTRACT_NEGATIVE",
    evidence_kind="SYNTHETIC",
    input_shape="LIVE_SHAPE",
    challenge_tags=("title_mpn_only",),
    request_mpn="SYN-UE-1",
    request_description="unknown enum probe",
    obs=Obs(title="SYN-UE-1 (probe)"),
    base_payload_case_id=_CN_BASE_U1,
    patches=(
        (("deterministic_identity_context", "substate"), "U9_INVENTED"),
    ),
    expected_rejection_class="INVALID_INPUT_SCHEMA",
)

_C8 = CaseDecl(
    case_id="V2Q-CN-UNKNOWN-EVIDENCE-SRC-0051",
    category="enterprise_ssd",
    case_class="CONTRACT_NEGATIVE",
    evidence_kind="SYNTHETIC",
    input_shape="LIVE_SHAPE",
    challenge_tags=("title_mpn_only",),
    request_mpn="SYN-UES-1",
    request_description="invented candidate evidence source probe",
    obs=Obs(title="SYN-UES-1 (probe)", brand="ProbeBrand"),
    base_payload_case_id=_CN_BASE_U1,
    patches=(
        (
            ("candidate", "product", "brand"),
            {"value": "ProbeBrand", "source": "MODEL_CLAIM"},
        ),
    ),
    expected_rejection_class="INVALID_INPUT_SCHEMA",
)

_C9 = CaseDecl(
    case_id="V2Q-CN-CLAIM-FACTOR-0052",
    category="enterprise_ssd",
    case_class="CONTRACT_NEGATIVE",
    evidence_kind="SYNTHETIC",
    input_shape="LIVE_SHAPE",
    challenge_tags=("title_mpn_only",),
    request_mpn="SYN-CF-1",
    request_description="authority-side model-claim source probe",
    obs=Obs(title="SYN-CF-1 (probe)"),
    base_payload_case_id=_CN_BASE_U1,
    patches=(
        (
            ("product_evidence", "matched_facts"),
            [
                {
                    "dimension": "CAPACITY",
                    "sources": ["MODEL_CLAIM"],
                }
            ],
        ),
    ),
    expected_rejection_class="INVALID_INPUT_SCHEMA",
)

_C10 = CaseDecl(
    case_id="V2Q-CN-EXTRA-KEY-0053",
    category="enterprise_ssd",
    case_class="CONTRACT_NEGATIVE",
    evidence_kind="SYNTHETIC",
    input_shape="LIVE_SHAPE",
    challenge_tags=("title_mpn_only",),
    request_mpn="SYN-EK-1",
    request_description="extra top-level key probe",
    obs=Obs(title="SYN-EK-1 (probe)"),
    base_payload_case_id=_CN_BASE_U1,
    patches=(
        (("injected_field",), "authority"),
    ),
    expected_rejection_class="INVALID_INPUT_SCHEMA",
)

_C11 = CaseDecl(
    case_id="V2Q-CN-SALESUNIT-X-0054",
    category="enterprise_ssd",
    case_class="CONTRACT_NEGATIVE",
    evidence_kind="SYNTHETIC",
    input_shape="LIVE_SHAPE",
    challenge_tags=("title_mpn_only",),
    request_mpn="SYN-SX-1",
    request_description="sales-unit cross-state probe",
    obs=Obs(title="SYN-SX-1 (probe)"),
    base_payload_case_id=_CN_BASE_U1,
    patches=(
        (
            ("candidate", "commercial", "sales_unit", "quantity"),
            20,
        ),
    ),
    expected_rejection_class="INVALID_INPUT_SCHEMA",
)

_C12 = CaseDecl(
    case_id="V2Q-CN-U4-NOTITLE-0055",
    category="enterprise_ssd",
    case_class="CONTRACT_NEGATIVE",
    evidence_kind="SYNTHETIC",
    input_shape="LIVE_SHAPE",
    challenge_tags=("title_mpn_only",),
    request_mpn="SYN-NT-1",
    request_description="U4 without usable title probe",
    obs=Obs(title="SYN-NT-1 (probe)"),
    base_payload_case_id=_CN_BASE_U1,
    patches=(
        (
            ("deterministic_identity_context", "substate"),
            "U4_NO_MPN",
        ),
        (
            ("deterministic_identity_context", "primary_relationship_signal"),
            "NO_RELATION",
        ),
        (
            ("deterministic_identity_context", "relationship_signals"),
            ["NO_RELATION"],
        ),
        (
            ("deterministic_identity_context", "relationship_requirement"),
            "NOT_APPLICABLE",
        ),
        (
            ("product_evidence", "has_usable_product_title"),
            False,
        ),
    ),
    expected_rejection_class="FOREIGN_DETERMINISTIC_CONTEXT",
)

_C13 = CaseDecl(
    case_id="V2Q-CN-REVIEWED-TAMPER-0056",
    category="enterprise_ssd",
    case_class="CONTRACT_NEGATIVE",
    evidence_kind="SYNTHETIC",
    input_shape="LIVE_SHAPE",
    challenge_tags=("customer_retrieval_alias",),
    request_mpn="SYN-RT-1",
    request_description="invented reviewed-relation kind probe",
    obs=Obs(mpn="SYN-RT-0", title="SYN-RT probe"),
    base_payload_case_id=_CN_BASE_U5,
    patches=(
        (
            ("target", "reviewed_context", "relation_kind"),
            "MANUFACTURER_STATED_ALIAS",
        ),
    ),
    expected_rejection_class="INVALID_INPUT_SCHEMA",
)


CASES: Final[tuple[CaseDecl, ...]] = (
    _S1,
    _S2,
    _S3,
    _S4,
    _S5,
    _S6,
    _S7,
    _S8,
    _S9,
    _S10,
    _S11,
    _S12,
    _S13,
    _S14,
    _S15,
    _S16,
    _S17,
    _S18,
    _S19,
    _S20,
    _S21,
    _S22,
    _S23,
    _S24,
    _S25,
    _S26,
    _S27,
    _S28,
    _S29,
    _S30,
    _S31,
    _S32,
    _S33,
    _S34,
    _S35,
    _S36,
    _S37,
    _S38,
    _S39,
    _S40,
    _S41,
    _S42,
    _S43,
    _C1,
    _C2,
    _C3,
    _C4,
    _C5,
    _C6,
    _C7,
    _C8,
    _C9,
    _C10,
    _C11,
    _C12,
    _C13,
)


# ---------------------------------------------------------------------------
# Frozen-chain case construction
# ---------------------------------------------------------------------------


def _authority_facts(decl: CaseDecl) -> frozenset[ProductEvidenceFactV2]:
    facts: set[ProductEvidenceFactV2] = set()
    for dimension_value, sources in decl.authority_facts:
        dimension = ProductEvidenceDimension(dimension_value)
        for source_value in sources:
            if source_value not in AUTHORITY_FACT_SOURCES:
                raise ValueError(
                    f"{decl.case_id}: authority fact source {source_value!r} "
                    "is outside the frozen S2-A grounded vocabulary"
                )
        facts.add(
            ProductEvidenceFactV2(
                dimension,
                frozenset(
                    CandidateProductEvidenceSource(s) for s in sources
                ),
            )
        )
    return frozenset(facts)


def _reviewed_context(decl: CaseDecl) -> ReviewedTargetContextV2 | None:
    ctx = decl.reviewed_context
    if ctx is None:
        return None
    return ReviewedTargetContextV2(
        manufacturer=ctx.manufacturer,
        category=ctx.category,
        matched_base_part_number=ctx.matched_base_part_number,
        relation_kind=TargetIdentifierRelationKindV2.CUSTOMER_RETRIEVAL_ALIAS,
        relation_family_part_numbers=ctx.relation_family_part_numbers,
        source_name=ctx.source_name,
        source_url=ctx.source_url,
        retrieved_at=ctx.retrieved_at,
        evidence_body_sha256=ctx.evidence_body_sha256,
    )


def _build_observation(decl: CaseDecl) -> ListingObservation:
    o = decl.obs
    return ListingObservation(
        source_url=f"https://example.com/v2q-cases/{decl.case_id.lower()}",
        extraction_method=ExtractionMethod.JSON_LD,
        product_title=o.title,
        brand_text=o.brand,
        manufacturer_part_number_text=o.mpn,
        sku_text=o.sku,
        price_text=o.price,
        currency_text=o.currency,
        availability_text=o.availability,
        condition_text=o.condition,
        seller_text=o.seller,
        offer_url_text=o.offer_url,
    )


def _build_semantic_case(decl: CaseDecl) -> SemanticMatchCaseV2:
    """Run the exact frozen chain for one semantic case declaration."""
    request = ResearchRequest(
        manufacturer_part_number=decl.request_mpn,
        description=decl.request_description,
    )
    observation = _build_observation(decl)
    normalized = normalize_listing_observation(observation)
    assessment = assess_listing_identity(request, normalized)
    context = derive_identity_state_v2(assessment)
    provenances = frozenset(
        ContextProvenance(p) for p in decl.provenances
    )
    facts = _authority_facts(decl)
    reviewed = _reviewed_context(decl)

    # Self-check: the fixture must land in the declared deterministic
    # state (a corpus defect if not - fail loudly at generation time).
    if decl.expected_substate is not None:
        if context.substate.value != decl.expected_substate:
            raise ValueError(
                f"{decl.case_id}: declared substate "
                f"{decl.expected_substate} but the frozen chain derived "
                f"{context.substate.value}"
            )
    if decl.expected_primary_signal is not None:
        if context.primary_relationship_signal.value != decl.expected_primary_signal:
            raise ValueError(
                f"{decl.case_id}: declared primary signal "
                f"{decl.expected_primary_signal} but the frozen chain "
                f"derived {context.primary_relationship_signal.value}"
            )

    if decl.input_shape == "LIVE_SHAPE":
        profile = build_v2_product_evidence_profile(
            observation=observation,
            context_provenances=provenances,
            matched_facts=facts,
        )
        return build_semantic_match_case_v2(
            case_id=decl.case_id,
            request=request,
            assessment=assessment,
            context=context,
            product_evidence=profile,
            context_provenances=provenances,
            reviewed_target_context=reviewed,
        )

    # CONTRACT_SURFACE: the declared candidate section replaces the
    # live builder's output, but the REAL case constructor still
    # validates everything (state, requirement table, evidence bar).
    product = _contract_surface_product(decl, observation)
    commercial = _contract_surface_commercial(decl, observation)
    profile = ProductEvidenceProfileV2(
        has_usable_product_title=bool(observation.product_title),
        matched_facts=facts,
    )
    derive_product_evidence_quality(profile, provenances)
    return SemanticMatchCaseV2(
        case_id=decl.case_id,
        target=TargetEvidenceV2(
            mpn=request.manufacturer_part_number,
            description_raw_text=request.description or None,
            reviewed_context=reviewed,
        ),
        candidate_source_url=observation.source_url,
        candidate_mpn_field=observation.manufacturer_part_number_text,
        candidate_sku=observation.sku_text,
        candidate_evidence_source=assessment.candidate_evidence_source.value,
        candidate_product=product,
        candidate_commercial=commercial,
        identity_state=context.state,
        substate=context.substate,
        primary_relationship_signal=context.primary_relationship_signal,
        relationship_signals=context.relationship_signals,
        normalized_requested_part_number=(
            context.normalized_requested_part_number
        ),
        normalized_candidate_part_number=(
            context.normalized_candidate_part_number
        ),
        relationship_requirement=substate_relationship_requirement(
            context.substate, context.primary_relationship_signal
        ),
        context_provenances=provenances,
        product_evidence=profile,
    )


def _contract_surface_product(
    decl: CaseDecl, observation: ListingObservation
) -> CandidateProductEvidenceV2:
    dims = {
        "product_family": None,
        "generation": None,
        "capacity": None,
        "interface": None,
        "form_factor": None,
        "product_role": None,
        "accessory_relation": None,
        "brand": (
            CandidateObservationFactV2(
                value=observation.brand_text,
                source=CandidateEvidenceSourceV2.PUBLISHED_STRUCTURED_FIELD,
            )
            if observation.brand_text
            else None
        ),
        "revision_or_suffix": None,
    }
    for dimension_value, fact_value, source_value in decl.product_facts:
        if dimension_value not in PRODUCT_FACT_DIMENSIONS:
            raise ValueError(
                f"{decl.case_id}: unknown product dimension "
                f"{dimension_value!r}"
            )
        if source_value not in CANDIDATE_FACT_SOURCES:
            raise ValueError(
                f"{decl.case_id}: unknown candidate fact source "
                f"{source_value!r}"
            )
        dims[dimension_value] = CandidateObservationFactV2(
            value=fact_value,
            source=CandidateEvidenceSourceV2(source_value),
        )
    return CandidateProductEvidenceV2(
        product_family=dims["product_family"],
        generation=dims["generation"],
        capacity=dims["capacity"],
        interface=dims["interface"],
        form_factor=dims["form_factor"],
        product_role=dims["product_role"],
        accessory_relation=dims["accessory_relation"],
        brand=dims["brand"],
        revision_or_suffix=dims["revision_or_suffix"],
        raw_title_text=observation.product_title or None,
        raw_specification_text=decl.raw_specification_text,
    )


def _contract_surface_commercial(
    decl: CaseDecl, observation: ListingObservation
) -> CandidateCommercialEvidenceV2:
    def fact(text: str | None) -> CandidateObservationFactV2 | None:
        if text is None:
            return None
        return CandidateObservationFactV2(
            value=text,
            source=CandidateEvidenceSourceV2.PUBLISHED_STRUCTURED_FIELD,
        )

    sales_unit = SALES_UNIT_EVIDENCE_UNAVAILABLE
    if decl.sales_unit is not None:
        su = decl.sales_unit
        if su.kind not in SALES_UNIT_KINDS:
            raise ValueError(f"{decl.case_id}: unknown sales unit kind {su.kind!r}")
        sales_unit = CandidateSalesUnitEvidenceV2(
            state=PackagingEvidenceStateV2.OBSERVED,
            kind=SalesUnitKindV2(su.kind),
            quantity=su.quantity,
            raw_detail=su.raw_detail,
            source=CandidateEvidenceSourceV2(su.source),
        )
    return CandidateCommercialEvidenceV2(
        condition=fact(observation.condition_text),
        price=fact(observation.price_text),
        currency=fact(observation.currency_text),
        availability=fact(observation.availability_text),
        seller=fact(observation.seller_text),
        offer_url=observation.offer_url_text,
        sales_unit=sales_unit,
    )


# ---------------------------------------------------------------------------
# Contract-negative payload construction
# ---------------------------------------------------------------------------


def _apply_patches(
    payload: dict[str, Any], patches: tuple[tuple[tuple[str, ...], Any], ...]
) -> dict[str, Any]:
    out: dict[str, Any] = json_clone(payload)
    for path, value in patches:
        node = out
        for key in path[:-1]:
            node = node[key]
        node[path[-1]] = value
    return out


def _cn_payload(decl: CaseDecl, base: dict[str, Any]) -> dict[str, Any]:
    payload = _apply_patches(base, decl.patches)
    payload["case_id"] = decl.case_id
    return payload


# ---------------------------------------------------------------------------
# Corpus document / state / manifest assembly
# ---------------------------------------------------------------------------


def _case_document(
    decl: CaseDecl,
    payload: dict[str, Any],
    substate: str,
    primary_signal: str,
) -> dict[str, Any]:
    expected: dict[str, Any]
    label: dict[str, Any]
    if decl.case_class == "CONTRACT_NEGATIVE":
        expected = {
            "disposition": "INPUT_REJECTED",
            "rejection_class": decl.expected_rejection_class,
            "decision": None,
            "acceptable_decisions": None,
            "conflict_classes": [],
            "missing_dimensions": [],
            "expected_reason_code": None,
            "commercial_sales_unit_safety": False,
        }
        label = {
            "source_kind": "CONTRACT_GROUNDED",
            "source": (
                "frozen Semantic V2 input contract "
                "(research/semantic_v2.py construction rules)"
            ),
            "evidence": (
                "The payload violates the frozen V2 input contract; the "
                "real case constructor must reject it. Expected rejection "
                "class recorded for harness verification."
            ),
            "reviewer": "PRODUCT-INTEL.Q3A.CORPUS-AUTHOR",
            "reviewer_status": "REVIEWED",
            "ambiguity": "UNAMBIGUOUS",
        }
    else:
        if decl.expected_decision is None:
            raise ValueError(
                f"{decl.case_id}: semantic case without expected decision"
            )
        if decl.acceptable_decisions is None:
            if decl.case_class != "AUTHORITATIVE":
                raise ValueError(
                    f"{decl.case_id}: non-authoritative case must declare "
                    "its acceptable decision set"
                )
            acceptable = (decl.expected_decision,)
        else:
            acceptable = tuple(decl.acceptable_decisions)
        expected = {
            "disposition": "SEMANTIC_EVALUATION",
            "rejection_class": None,
            "decision": decl.expected_decision,
            "acceptable_decisions": list(acceptable),
            "conflict_classes": list(decl.expected_conflict_classes),
            "missing_dimensions": list(decl.expected_missing_dimensions),
            "expected_reason_code": decl.expected_reason_code,
            "commercial_sales_unit_safety": (
                decl.commercial_sales_unit_safety
            ),
        }
        label = {
            "source_kind": decl.label_source_kind,
            "source": decl.label_source,
            "evidence": decl.label_evidence,
            "reviewer": decl.reviewer,
            "reviewer_status": decl.reviewer_status,
            "ambiguity": decl.ambiguity,
        }
        _check_label_independence(decl, label)

    doc = {
        "case_id": decl.case_id,
        "category": decl.category,
        "case_class": decl.case_class,
        "evidence_kind": decl.evidence_kind,
        "input_shape": decl.input_shape,
        "challenge_tags": sorted(decl.challenge_tags),
        "substate": substate,
        "primary_signal": primary_signal,
        "input_payload": payload,
        "expected": expected,
        "label": label,
    }
    return doc


def _check_label_independence(decl: CaseDecl, label: dict[str, Any]) -> None:
    """Mechanical ground-truth guard: the label's evidence/source must
    not name any candidate model or model output (labels are
    independently established, never derived from the system under
    test)."""
    for field_name in ("source", "evidence"):
        text = (label[field_name] or "").lower()
        for token in FORBIDDEN_EVIDENCE_TOKENS:
            if token in text:
                raise ValueError(
                    f"{decl.case_id}: label {field_name} names "
                    f"{token!r}; ground truth must be independent of "
                    "any model output"
                )


def _semantic_case_docs() -> list[tuple[CaseDecl, dict[str, Any], str, str]]:
    out: list[tuple[CaseDecl, dict[str, Any], str, str]] = []
    for decl in CASES:
        if decl.case_class == "CONTRACT_NEGATIVE":
            continue
        case = _build_semantic_case(decl)
        payload = case.canonical()
        out.append(
            (
                decl,
                payload,
                case.substate.value,
                case.primary_relationship_signal.value,
            )
        )
    return out


def _base_payloads(
    semantic: list[tuple[CaseDecl, dict[str, Any], str, str]],
) -> dict[str, dict[str, Any]]:
    return {
        decl.case_id: payload
        for decl, payload, _sub, _prim in semantic
    }


def build_corpus_state() -> dict[str, Any]:
    """The digest-relevant corpus state (deterministic)."""
    semantic = _semantic_case_docs()
    bases = _base_payloads(semantic)
    case_docs: list[dict[str, Any]] = []
    for decl in CASES:
        if decl.case_class == "CONTRACT_NEGATIVE":
            base_id = decl.base_payload_case_id
            if base_id not in bases:
                raise ValueError(
                    f"{decl.case_id}: contract-negative base payload "
                    f"{base_id!r} not found"
                )
            payload = _cn_payload(decl, bases[base_id])
            substate, primary = (
                payload["deterministic_identity_context"]["substate"],
                payload["deterministic_identity_context"][
                    "primary_relationship_signal"
                ],
            )
        else:
            match = [
                (d, p, s, pr)
                for d, p, s, pr in semantic
                if d.case_id == decl.case_id
            ]
            if len(match) != 1:
                raise ValueError(
                    f"{decl.case_id}: expected exactly one built "
                    f"semantic case, found {len(match)}"
                )
            _d, payload, substate, primary = match[0]
        doc = _case_document(decl, payload, substate, primary)
        _check_case_vocabulary(doc)
        state_view = {k: v for k, v in doc.items() if k != "case_digest"}
        doc["case_digest"] = canonical_sha256(state_view)
        case_docs.append(doc)
    case_docs.sort(key=lambda d: d["case_id"])
    state = {
        "corpus_id": CORPUS_ID,
        "corpus_schema_version": 1,
        "corpus_version": CORPUS_VERSION,
        "corpus_label": CORPUS_LABEL,
        "created_utc": CORPUS_CREATED_UTC,
        "semantic_contract_binding": list(V2_CONTRACT_BINDING),
        "cases": case_docs,
    }
    _self_check_coverage(case_docs)
    return state


def _check_case_vocabulary(doc: dict[str, Any]) -> None:
    case_id = doc["case_id"]
    if doc["case_class"] not in CASE_CLASSES:
        raise ValueError(f"{case_id}: unknown case class {doc['case_class']!r}")
    if doc["evidence_kind"] not in EVIDENCE_KINDS:
        raise ValueError(
            f"{case_id}: unknown evidence kind {doc['evidence_kind']!r}"
        )
    if doc["input_shape"] not in INPUT_SHAPES:
        raise ValueError(f"{case_id}: unknown input shape {doc['input_shape']!r}")
    if doc["category"] not in CATEGORIES:
        raise ValueError(f"{case_id}: unknown category {doc['category']!r}")
    for tag in doc["challenge_tags"]:
        if tag not in CHALLENGE_TAGS:
            raise ValueError(f"{case_id}: unknown challenge tag {tag!r}")
    expected = doc["expected"]
    for cc in expected["conflict_classes"]:
        if cc not in CONFLICT_CLASSES:
            raise ValueError(f"{case_id}: unknown conflict class {cc!r}")
    for dim in expected["missing_dimensions"]:
        if dim not in MISSING_DIMENSIONS:
            raise ValueError(f"{case_id}: unknown missing dimension {dim!r}")
    label = doc["label"]
    if label["source_kind"] not in LABEL_SOURCE_KINDS:
        raise ValueError(f"{case_id}: unknown label source kind")
    if label["reviewer_status"] not in REVIEWER_STATUSES:
        raise ValueError(f"{case_id}: unknown reviewer status")
    if label["ambiguity"] not in AMBIGUITY_CLASSES:
        raise ValueError(f"{case_id}: unknown ambiguity class")
    if doc["case_class"] == "CONTRACT_NEGATIVE":
        if expected["rejection_class"] not in REJECTION_CLASSES:
            raise ValueError(f"{case_id}: unknown rejection class")
    else:
        if expected["decision"] not in DECISIONS:
            raise ValueError(f"{case_id}: unknown decision {expected['decision']!r}")
        for d in expected["acceptable_decisions"]:
            if d not in DECISIONS:
                raise ValueError(f"{case_id}: unknown acceptable decision {d!r}")
        if expected["decision"] not in expected["acceptable_decisions"]:
            raise ValueError(
                f"{case_id}: expected decision must be inside its "
                "acceptable set"
            )
        if len(expected["acceptable_decisions"]) > 1 and (
            doc["case_class"] != "AMBIGUOUS"
        ):
            raise ValueError(
                f"{case_id}: a multi-pole acceptable set requires the "
                "AMBIGUOUS case class"
            )


def _self_check_coverage(case_docs: list[dict[str, Any]]) -> None:
    """The corpus must cover the mandated surface; fail loudly otherwise.

    * every frozen S2-A uncertain substate (with both U2 primary
      signals and both U5 near-miss shapes);
    * the motivating Micron pair;
    * at least one case in at least four distinct product categories;
    * authoritative cases in every required adversarial family (by
      challenge tag).
    """
    semantic = [
        d for d in case_docs if d["case_class"] != "CONTRACT_NEGATIVE"
    ]
    substates = {
        (d["substate"], d["primary_signal"]) for d in semantic
    }
    required_states = {
        ("U1_TITLE_MPN", "TITLE_MPN_TOKEN"),
        ("U2_SKU_ONLY", "SKU_EQUALS_TARGET"),
        ("U2_SKU_ONLY", "SKU_NOT_TARGET"),
        ("U3_PARTIAL_BOUNDARY", "PARTIAL_BOUNDARY"),
        ("U4_NO_MPN", "NO_RELATION"),
        ("U5_NEAR_MISS_MPN", "NEAR_MISS_TRUNCATION"),
        ("U5_NEAR_MISS_MPN", "NEAR_MISS_SUBSTITUTION"),
    }
    missing = required_states - substates
    if missing:
        raise ValueError(f"corpus is missing required substates: {sorted(missing)}")

    micron = [
        d
        for d in semantic
        if "MTFDKCC3T8TGP-1BK1DABYYR"
        in d["input_payload"]["target"]["mpn"]
        and "MTFDKCC3T8TGP-1BK1DABYY"
        in str(d["input_payload"]["candidate"]["mpn_field"])
    ]
    if not micron:
        raise ValueError("the motivating Micron pair is missing from the corpus")

    categories = {d["category"] for d in semantic}
    if len(categories) < 4:
        raise ValueError(
            f"corpus must span at least four product categories, "
            f"found {sorted(categories)}"
        )

    all_tags = {
        tag for d in semantic for tag in d["challenge_tags"]
    }
    required_tags = {
        "exact_product_alt_wording",
        "title_mpn_only",
        "compatibility_wording",
        "different_generation",
        "different_capacity",
        "different_interface",
        "different_form_factor",
        "accessory_vs_product",
        "standalone_vs_bundle",
        "single_vs_multipack",
        "tray_vs_retail",
        "missing_candidate_mpn",
        "different_sku_same_product",
        "sku_matches_target_mpn",
        "near_miss_one_char",
        "near_miss_truncated",
        "different_brand",
        "condition_only_difference",
        "missing_critical_specs",
        "customer_retrieval_alias",
        "manufacturer_product_context_only",
        "reviewed_relation_authority",
        "contradictory_listing_evidence",
        "misleading_seo",
        "insufficient_evidence",
    }
    missing_tags = required_tags - all_tags
    if missing_tags:
        raise ValueError(
            f"corpus is missing required adversarial coverage: "
            f"{sorted(missing_tags)}"
        )

    if not any(
        d["case_class"] == "CONTRACT_NEGATIVE" for d in case_docs
    ):
        raise ValueError("corpus must contain contract-negative cases")
    if not any(d["case_class"] == "AMBIGUOUS" for d in case_docs):
        raise ValueError("corpus must contain ambiguous cases")
    if not any(
        d["case_class"] == "AUTHORITATIVE" for d in case_docs
    ):
        raise ValueError("corpus must contain authoritative cases")


def build_corpus_document() -> dict[str, Any]:
    """The full corpus document (state + revisions + digest)."""
    state = build_corpus_state()
    doc = {
        **state,
        "label_revisions": [],
    }
    doc["corpus_digest"] = canonical_sha256(state)
    return doc


def build_manifest_document(
    corpus_document: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """The reproducible manifest for one corpus document."""
    doc = corpus_document if corpus_document is not None else build_corpus_document()
    if "corpus_digest" not in doc:
        raise ValueError("manifest requires the corpus digest")
    cases = [
        {
            "case_id": case["case_id"],
            "case_class": case["case_class"],
            "category": case["category"],
            "substate": case["substate"],
            "primary_signal": case["primary_signal"],
            "case_digest": case["case_digest"],
        }
        for case in doc["cases"]
    ]
    state = {
        "manifest_schema_version": 1,
        "corpus_id": doc["corpus_id"],
        "corpus_version": doc["corpus_version"],
        "semantic_contract_binding": list(doc["semantic_contract_binding"]),
        "corpus_digest": doc["corpus_digest"],
        "case_count": len(cases),
        "cases": cases,
    }
    state["manifest_digest"] = canonical_sha256(state)
    return state


def json_clone(value: Any) -> Any:
    """A deep clone through the JSON boundary (payloads are JSON-native)."""
    import json as _json

    return _json.loads(_json.dumps(value))
