"""The FINAL Semantic V2 contract (S2-C).

PRODUCT-INTEL.SEMANTIC-AUTHORITY-V2-S2-C freezes the exact runtime contract
that Qualification V3 will use UNCHANGED:

* the explicit **V2 semantic eligibility predicate** over the frozen S2-A
  derived state (DETERMINISTIC_UNCERTAIN only — U1 / U2 / U3 / U4 / U5 —
  including the bounded near-miss states; verified, conflict, and
  unevaluable states are never V2-eligible);
* the final **Semantic V2 input contract** (``SemanticMatchCaseV2``) — a
  versioned immutable value object with clearly separated sections for the
  TARGET, the CANDIDATE LISTING, the DETERMINISTIC IDENTITY CONTEXT, the
  CONTEXT PROVENANCE, and the authority-side PRODUCT EVIDENCE. The input
  distinguishes four evidence classes with explicit provenance: STRUCTURED
  FACT (bounded value + source label), RAW OBSERVATION TEXT (published free
  text, labeled), COMMERCIAL / PACKAGING EVIDENCE (bounded, the sales-unit
  channel always explicit), and AUTHORITY-SIDE PRODUCT EVIDENCE
  (deterministic/reviewed only — the model can never create or upgrade it).
* the SAFE **product-evidence builder** (``build_v2_product_evidence_
  profile``) — the bounded STRONG evidence bar can only be reached from
  facts whose candidate-side grounding is independently present in
  ``LISTING_PRODUCT_TITLE`` or ``REVIEWED_PRODUCT_CONTEXT``; the model's
  ``matched_attributes`` can never become authority facts;
* the final **Semantic V2 output contract** — a strict structured response
  (decision / confidence / bounded reason code / bounded structured
  attributes / bounded missing-critical dimensions / structured
  ``ConflictClass`` set) validated against the frozen conflict vocabulary
  and the frozen reason-code rules; unknown values, missing fields, extra
  fields, and decision/conflict incoherence all fail closed.

What this module deliberately is:

* A PURE research-layer contract: stdlib + the domain contracts + the
  frozen research package's public export surface only. No Django, no I/O,
  no clock, no network, no LLM, no production semantic-runtime import, no
  mutable global state.
* The authority-side half of the V2 contract. The Prompt V2 renderer and
  the V2 runtime (routing / fallback / transport) live in the semantic
  layer and consume this module; the V2 persistence adapter
  (``semantic_decision_v2``) mirrors this module's contract identity and
  output vocabulary so the pure research layer never imports the runtime.

What this module deliberately is NOT:

* A redefinition of the frozen S2-A authority contract. It CONSUMES the
  frozen derived state (``derive_identity_state_v2``), the frozen
  relationship-requirement table (``substate_relationship_requirement``),
  the frozen product-evidence bar (``derive_product_evidence_quality``),
  and the frozen conflict taxonomy (``ConflictClass`` severity sets)
  through the research package's public exports. It adds no states, no
  signals, no severities, and no new eligibility fuzzy matching: the only
  near-miss states are the frozen bounded states.
* A qualification claim. The V2 route is NOT qualified for this new
  contract (see the ``V2_AUTHORITY_QUALIFIED`` marker in the V2 runtime /
  adapter mirrors). V2 outputs are evidence/provenance awaiting
  Qualification V3; nothing in this module grants pricing authority.
* A change to the V1 contract. The frozen FU3B V1 eligibility predicate
  (``execution.semantic_integration``) is unchanged; this module's V2
  predicate is a NEW, separate predicate with a wider (superset) reach:
  V2 additionally covers U4_NO_MPN and U5_NEAR_MISS_MPN.

Extraction-capability audit (S2-C-FU1 — what evidence exists today, what
is structured, what stays raw, and what may/may not grant authority):

* 3A ``ListingObservation`` carries the page-published STRUCTURED fields:
  product title, MPN field, SKU, brand, price, currency, availability,
  condition, seller, offer URL (JSON-LD / product meta are the only offer
  extraction mechanisms). The remaining JSON-LD material (description,
  GTIN, category, ...) survives in the OPAQUE ``raw_reference``, which no
  business rule may parse (AD-040).
* 3B normalizes COMMERCIAL attributes only (price / availability /
  condition / seller); it extracts no product attributes.
* 3C compares EXPLICIT MPN fields only (the frozen 2A comparator); title
  and SKU text never establish identity.
* The 6A/6B/6C specification framework and the 7A/7B comparable-research
  extraction exist ONLY in the comparable-research flow and require an
  ESTABLISHED product identity plus manufacturer support pages with the
  reviewed embedded structure — they are not available to main-flow
  listing candidates.
* 4D-D (the Micron 7500 packaging-alias acquisition) is the ONLY reviewed
  manufacturer TARGET context the main execution flow carries: when
  ESTABLISHED it proves the requested part's family-catalog membership
  (manufacturer, verified SSD category, the exact source-published base
  MPN) through a fail-closed deterministic parser over a reviewed origin.
  Its R/T relation is CUSTOMER-DEFINED (retrieval only, zero identity
  authority) and the result carries no other catalog attributes.

Consequences for this input contract:

* Candidate-side STRUCTURED product facts are filled ONLY from the
  page-published structured fields the extractor actually carries (brand
  today); every other product dimension remains explicit None (absent —
  never a guessed value). NO token of the raw title is parsed into a
  structured fact: token occurrence in the title is RAW observation
  evidence, not bounded structured evidence.
* The published title is carried as RAW observation text (labeled as
  such); the main flow carries no specification text (it stays in the
  opaque raw reference).
* The COMMERCIAL section carries the published commercial fields as
  bounded facts plus the bounded SALES-UNIT / PACKAGING channel whose
  state is always explicit: the extractor publishes no packaging field,
  so the live builder records ``UNAVAILABLE`` — never a value inferred
  from price, never a silent absence. The channel's bounded vocabulary
  represents single unit, pack quantity, tray/factory pack, and bundle.
* TARGET-side structured/reviewed facts exist only when the main flow
  carries a reviewed manufacturer target context (today: the ESTABLISHED
  4D-D acquisition, as ``ReviewedTargetContextV2``); the requested
  description is RAW observation text.
* AUTHORITY SIDE (unchanged S2-A safety bar): a ``ProductEvidenceFactV2``
  requires the frozen grounded-source vocabulary
  (LISTING_PRODUCT_TITLE / REVIEWED_PRODUCT_CONTEXT — no model-claim
  member). The main-flow extraction proves no exact bounded
  identity-dimension equality for listing candidates, so the live path
  passes ``matched_facts=frozenset()``: candidates remain at most LIMITED
  (usable title) or WEAK, and the frozen S2-A bar keeps them at
  NEEDS_REVIEW until future evidence infrastructure safely proves facts.
  None of the MODEL-OBSERVATION evidence above (structured or raw) can
  grant authority: observation is never equality proof, and the model
  never bootstraps the authority-side profile from its own output.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Final

from product_intelligence.domain.models import ResearchRequest
from product_intelligence.research import (
    ALWAYS_HARD_CONFLICT_CLASSES,
    ConflictClass,
    ContextProvenance,
    IdentityRelationshipSignal,
    IdentityStateAssessmentV2,
    IdentityStateV2,
    ProductEvidenceDimension,
    ProductEvidenceFactV2,
    ProductEvidenceProfileV2,
    RelationshipRequirement,
    UncertainSubstateV2,
    VerifiedSubstateV2,
    ConflictSubstateV2,
    UnevaluableSubstateV2,
    V2Confidence,
    V2SemanticDecision,
    derive_identity_state_v2,
    derive_product_evidence_quality,
    substate_relationship_requirement,
)
from product_intelligence.research.listings import ListingObservation
from product_intelligence.research.matching import ListingIdentityAssessment

__all__ = [
    "CandidateCommercialEvidenceV2",
    "CandidateEvidenceSourceV2",
    "CandidateObservationFactV2",
    "CandidateProductDimensionV2",
    "CandidateProductEvidenceV2",
    "CandidateSalesUnitEvidenceV2",
    "PackagingEvidenceStateV2",
    "REASON_CODE_RULES",
    "ReviewedTargetContextV2",
    "SALES_UNIT_EVIDENCE_UNAVAILABLE",
    "SalesUnitKindV2",
    "SemanticAttributeDimensionV2",
    "SemanticAttributeV2",
    "SemanticMatchCaseV2",
    "SemanticMatchResponseV2",
    "SemanticReasonCodeRuleV2",
    "SemanticReasonCodeV2",
    "SemanticV2ParseError",
    "TargetEvidenceV2",
    "TargetIdentifierRelationKindV2",
    "build_candidate_commercial_evidence_v2",
    "build_candidate_product_evidence_v2",
    "build_semantic_match_case_v2",
    "build_v2_product_evidence_profile",
    "is_v2_semantic_eligible",
    "parse_semantic_response_v2",
    "semantic_reason_code_rule",
    "validate_semantic_response_v2",
]


# ---------------------------------------------------------------------------
# V2 semantic eligibility (S2-C)
# ---------------------------------------------------------------------------


def is_v2_semantic_eligible(assessment: ListingIdentityAssessment) -> bool:
    """The explicit V2 semantic eligibility predicate (S2-C).

    Based on the frozen S2-A derived state — not on the V1 predicate and
    not on any fuzzy matching:

        DETERMINISTIC_VERIFIED    -> NOT V2-eligible
        DETERMINISTIC_CONFLICT    -> NOT V2-eligible
        DETERMINISTIC_UNEVALUABLE -> NOT V2-eligible
        DETERMINISTIC_UNCERTAIN   -> V2-eligible

    The uncertain states are exactly U1_TITLE_MPN, U2_SKU_ONLY (both
    primary signals), U3_PARTIAL_BOUNDARY, U4_NO_MPN (both primary
    signals), and U5_NEAR_MISS_MPN (the bounded NM-1 / NM-2 shapes only —
    the frozen near-miss logic is the ONLY near-miss authority; generic
    edit-distance or substring matching does not exist in this predicate).
    Eligibility is NOT authority: a V2-eligible candidate is merely
    admissible to the V2 semantic evaluation; the frozen S2-A gates decide
    what any V2 outcome may do.

    The CURRENT V1 predicate (``execution.semantic_integration``) is
    unchanged and remains the only gate of the V1 live path.

    Raises ``TypeError`` for a non-assessment input; ``ValueError`` for an
    assessment combination outside the frozen 3C contract (fail closed —
    the S2-A derivation already enforces this).
    """
    if not isinstance(assessment, ListingIdentityAssessment):
        raise TypeError(
            "assessment must be ListingIdentityAssessment, "
            f"got {type(assessment).__name__}"
        )
    context = derive_identity_state_v2(assessment)
    return context.state is IdentityStateV2.DETERMINISTIC_UNCERTAIN


# ---------------------------------------------------------------------------
# Bounded candidate-side observation evidence (S2-C-FU1)
# ---------------------------------------------------------------------------
# MODEL-OBSERVATION evidence only. Every value below is a published or
# established fact with explicit provenance — never a model claim, never a
# value inferred from raw text. None of it can grant authority: it cannot
# become a ProductEvidenceFactV2 (the frozen S2-A candidate-source
# vocabulary has no member for it) and a matching value is not a
# deterministic equality proof (equivalence is the model's semantic
# judgment under qualification).


class CandidateEvidenceSourceV2(str, Enum):
    """Bounded candidate-side provenance for one structured observation
    fact.

    Distinguishes WHERE the fact was published / established:

    * PUBLISHED_STRUCTURED_FIELD — a field the page deliberately published
      as structured data (JSON-LD / product meta) that the 3A extractor
      carries as a named observation field;
    * LISTING_TITLE — a deterministic title-published field (reserved:
      the live main-flow builder emits no title-derived facts — token
      occurrence in the raw title is not structured evidence);
    * SPECIFICATION_TEXT — a published specification / description text
      field (reserved: the main flow carries no specification text — the
      remaining JSON-LD material stays in the opaque raw reference, which
      no business rule may parse);
    * REVIEWED_PRODUCT_CONTEXT — a reviewed manufacturer product context
      carried by the main execution flow about the CANDIDATE (reserved:
      today the main flow carries no reviewed candidate-side product
      context).

    No member is a model claim: the V2 model's matched_attributes can
    never name a source for its own observations.
    """

    PUBLISHED_STRUCTURED_FIELD = "PUBLISHED_STRUCTURED_FIELD"
    LISTING_TITLE = "LISTING_TITLE"
    SPECIFICATION_TEXT = "SPECIFICATION_TEXT"
    REVIEWED_PRODUCT_CONTEXT = "REVIEWED_PRODUCT_CONTEXT"


@dataclass(frozen=True)
class CandidateObservationFactV2:
    """One bounded candidate observation fact (observed value + provenance).

    MODEL-OBSERVATION evidence only: a published / established value, never
    a value inferred from raw text and never a model claim. It may support
    the model's semantic reasoning; it is NOT authority-side evidence — it
    cannot become a ``ProductEvidenceFactV2`` and the value is not a
    deterministic equality proof against the target.
    """

    value: str
    source: CandidateEvidenceSourceV2

    def __post_init__(self) -> None:
        if not isinstance(self.value, str) or not self.value:
            raise ValueError(
                "a candidate observation fact's value must be a non-empty "
                "str preserved as published (an absent fact is None, "
                "never an empty sentinel)"
            )
        if not isinstance(self.source, CandidateEvidenceSourceV2):
            raise TypeError(
                "source must be CandidateEvidenceSourceV2, "
                f"got {type(self.source).__name__}"
            )

    def canonical(self) -> dict[str, object]:
        return {"value": self.value, "source": self.source.value}


def _canonical_fact(fact: CandidateObservationFactV2 | None) -> dict[str, object] | None:
    return None if fact is None else fact.canonical()


class CandidateProductDimensionV2(str, Enum):
    """Bounded candidate product-dimension vocabulary of the structured
    observation evidence (S2-C-FU1).

    These are the OBSERVATION dimensions the candidate's structured product
    evidence may carry a bounded fact for: product family, generation,
    capacity, interface, form factor, product role, accessory relation,
    brand, revision / suffix. They mirror the V2 output attribute
    vocabulary's product dimensions. CONDITION, price, and packaging /
    sales unit are COMMERCIAL dimensions (they live in
    ``CandidateCommercialEvidenceV2``); MPN / SKU are IDENTIFIER fields
    (they stay top-level published fields of the case). Each dimension is
    either a bounded fact (value + provenance) or explicit None (absent —
    never a guessed value).
    """

    PRODUCT_FAMILY = "PRODUCT_FAMILY"
    GENERATION = "GENERATION"
    CAPACITY = "CAPACITY"
    INTERFACE = "INTERFACE"
    FORM_FACTOR = "FORM_FACTOR"
    PRODUCT_ROLE = "PRODUCT_ROLE"
    ACCESSORY_RELATION = "ACCESSORY_RELATION"
    BRAND = "BRAND"
    REVISION_OR_SUFFIX = "REVISION_OR_SUFFIX"


#: The fixed rendering / encoding order of the bounded product dimensions.
_CANDIDATE_PRODUCT_DIMENSIONS: Final[tuple[CandidateProductDimensionV2, ...]] = (
    CandidateProductDimensionV2.PRODUCT_FAMILY,
    CandidateProductDimensionV2.GENERATION,
    CandidateProductDimensionV2.CAPACITY,
    CandidateProductDimensionV2.INTERFACE,
    CandidateProductDimensionV2.FORM_FACTOR,
    CandidateProductDimensionV2.PRODUCT_ROLE,
    CandidateProductDimensionV2.ACCESSORY_RELATION,
    CandidateProductDimensionV2.BRAND,
    CandidateProductDimensionV2.REVISION_OR_SUFFIX,
)


@dataclass(frozen=True)
class CandidateProductEvidenceV2:
    """Structured candidate PRODUCT observation evidence (S2-C-FU1).

    * The nine bounded product dimensions — each either a
      ``CandidateObservationFactV2`` (observed value + explicit source)
      or ``None`` (absent — never a guessed value; absence is not
      equivalence and not non-equivalence);
    * ``raw_title_text`` — the page-published listing title as RAW
      observation text. It may support the model's semantic reasoning but
      is NOT structured evidence and never becomes manufacturer authority:
      a token occurring in it is not a bounded fact;
    * ``raw_specification_text`` — RAW specification / description text
      when the extractor carries it. The main flow carries none today
      (the remaining JSON-LD material stays in the opaque raw reference,
      which no business rule may parse) — the channel is explicit None.

    This section is MODEL-OBSERVATION evidence. It is not, and cannot
    become, the authority-side ``ProductEvidenceProfileV2`` (a separate
    section of the case, derived only from the frozen S2-A evidence bar).
    """

    product_family: CandidateObservationFactV2 | None
    generation: CandidateObservationFactV2 | None
    capacity: CandidateObservationFactV2 | None
    interface: CandidateObservationFactV2 | None
    form_factor: CandidateObservationFactV2 | None
    product_role: CandidateObservationFactV2 | None
    accessory_relation: CandidateObservationFactV2 | None
    brand: CandidateObservationFactV2 | None
    revision_or_suffix: CandidateObservationFactV2 | None
    raw_title_text: str | None
    raw_specification_text: str | None

    def __post_init__(self) -> None:
        for dimension in _CANDIDATE_PRODUCT_DIMENSIONS:
            value = getattr(self, dimension.value.lower())
            if value is not None and not isinstance(
                value, CandidateObservationFactV2
            ):
                raise TypeError(
                    f"{dimension.value} must be CandidateObservationFactV2 "
                    f"or None, got {type(value).__name__}"
                )
        for name in ("raw_title_text", "raw_specification_text"):
            value = getattr(self, name)
            if value is not None and not isinstance(value, str):
                raise TypeError(
                    f"{name} must be str or None, got {type(value).__name__}"
                )

    def canonical(self) -> dict[str, object]:
        out: dict[str, object] = {
            dimension.value.lower(): _canonical_fact(
                getattr(self, dimension.value.lower())
            )
            for dimension in _CANDIDATE_PRODUCT_DIMENSIONS
        }
        out["raw_title_text"] = self.raw_title_text
        out["raw_specification_text"] = self.raw_specification_text
        return out


class SalesUnitKindV2(str, Enum):
    """Bounded sales-unit / packaging kinds the channel can represent when
    actually observed (S2-C-FU1).

    SINGLE_UNIT — one retail unit;
    PACK_QUANTITY — a pack of N (the bounded positive quantity carries N);
    TRAY_OR_FACTORY_PACK — a tray / factory pack (quantity optional when
    published);
    BUNDLE — a bundle (quantity optional when published).

    A kind is never inferred from price, availability, or any other
    commercial fact.
    """

    SINGLE_UNIT = "SINGLE_UNIT"
    PACK_QUANTITY = "PACK_QUANTITY"
    TRAY_OR_FACTORY_PACK = "TRAY_OR_FACTORY_PACK"
    BUNDLE = "BUNDLE"


class PackagingEvidenceStateV2(str, Enum):
    """The explicit state of the candidate's sales-unit / packaging
    channel (S2-C-FU1). The state is ALWAYS recorded — packaging absence
    is an explicit, persisted state, never a silent omission.
    """

    UNAVAILABLE = "UNAVAILABLE"
    """The listing published no packaging / sales-unit field. Absence is
    recorded, not guessed: it is not 'single unit', it is not 'probably
    fine', and it is never inferred from price or any other commercial
    fact."""
    OBSERVED = "OBSERVED"
    """A bounded packaging / sales-unit observation is present (kind +
    published raw detail + provenance, plus the bounded quantity where
    the kind carries one)."""


@dataclass(frozen=True)
class CandidateSalesUnitEvidenceV2:
    """The bounded candidate PACKAGING / SALES-UNIT evidence channel
    (S2-C-FU1 — required before S2-C freeze).

    The state is always explicit:

    * ``UNAVAILABLE`` — the listing published no packaging / sales-unit
      field (kind / quantity / raw_detail / source are all None). The
      model may not read this as 'single unit' or as equivalence;
    * ``OBSERVED`` — a bounded ``SalesUnitKindV2`` (single unit, pack
      quantity, tray/factory pack, bundle), the published raw detail,
      the provenance, and — for ``PACK_QUANTITY`` — the bounded positive
      integer quantity (optional for tray / bundle, forbidden for single
      unit).

    This is COMMERCIAL evidence (NEVER identity evidence). It can carry a
    PACKAGING_QUANTITY / BUNDLE CONFLICT conclusion for the model; it
    grants no authority and grounds no ProductEvidenceFactV2.
    """

    state: PackagingEvidenceStateV2
    kind: SalesUnitKindV2 | None
    quantity: int | None
    raw_detail: str | None
    source: CandidateEvidenceSourceV2 | None

    def __post_init__(self) -> None:
        if not isinstance(self.state, PackagingEvidenceStateV2):
            raise TypeError(
                "state must be PackagingEvidenceStateV2, "
                f"got {type(self.state).__name__}"
            )
        if self.kind is not None and not isinstance(self.kind, SalesUnitKindV2):
            raise TypeError(
                "kind must be SalesUnitKindV2 or None, "
                f"got {type(self.kind).__name__}"
            )
        if self.source is not None and not isinstance(
            self.source, CandidateEvidenceSourceV2
        ):
            raise TypeError(
                "source must be CandidateEvidenceSourceV2 or None, "
                f"got {type(self.source).__name__}"
            )
        if self.raw_detail is not None and not isinstance(self.raw_detail, str):
            raise TypeError(
                "raw_detail must be str or None, got "
                f"{type(self.raw_detail).__name__}"
            )
        if self.state is PackagingEvidenceStateV2.UNAVAILABLE:
            if (
                self.kind is not None
                or self.quantity is not None
                or self.raw_detail is not None
                or self.source is not None
            ):
                raise ValueError(
                    "an UNAVAILABLE sales-unit channel carries no value: "
                    "kind / quantity / raw_detail / source must all be None "
                    "(packaging absence is recorded, never guessed)"
                )
            return
        # OBSERVED: the bounded observation must be complete.
        if self.kind is None:
            raise ValueError(
                "an OBSERVED sales-unit channel requires a bounded kind "
                "(single unit / pack quantity / tray-factory pack / bundle)"
            )
        if self.raw_detail is None or not self.raw_detail:
            raise ValueError(
                "an OBSERVED sales-unit channel requires the published raw "
                "detail (the observed value as published)"
            )
        if self.source is None:
            raise ValueError(
                "an OBSERVED sales-unit channel requires explicit provenance"
            )
        if self.quantity is not None:
            if type(self.quantity) is not int or self.quantity < 1:
                raise ValueError(
                    "a sales-unit quantity must be a positive int "
                    f"(got {self.quantity!r})"
                )
        if self.kind is SalesUnitKindV2.PACK_QUANTITY and self.quantity is None:
            raise ValueError(
                "a PACK_QUANTITY sales unit requires the bounded positive "
                "quantity (a pack without a count is outside the contract)"
            )
        if self.kind is SalesUnitKindV2.SINGLE_UNIT and self.quantity is not None:
            raise ValueError(
                "a SINGLE_UNIT sales unit carries no quantity (the unit is "
                "the bounded value)"
            )

    def canonical(self) -> dict[str, object]:
        return {
            "state": self.state.value,
            "kind": self.kind.value if self.kind is not None else None,
            "quantity": self.quantity,
            "raw_detail": self.raw_detail,
            "source": self.source.value if self.source is not None else None,
        }


#: The single canonical absence for the sales-unit / packaging channel.
SALES_UNIT_EVIDENCE_UNAVAILABLE: Final[CandidateSalesUnitEvidenceV2] = (
    CandidateSalesUnitEvidenceV2(
        state=PackagingEvidenceStateV2.UNAVAILABLE,
        kind=None,
        quantity=None,
        raw_detail=None,
        source=None,
    )
)


@dataclass(frozen=True)
class CandidateCommercialEvidenceV2:
    """Structured candidate COMMERCIAL observation evidence (S2-C-FU1).

    NEVER identity evidence (the prompt labels the section; no authority
    derivation consumes it). Each commercial field the page published
    (condition, price, currency, availability, seller) becomes a bounded
    ``CandidateObservationFactV2`` with its published-structured-field
    provenance; absent fields are explicit None (never an empty sentinel).
    ``offer_url`` is the published offer link (plain text, absent = None).
    ``sales_unit`` is the bounded packaging / sales-unit channel — ALWAYS
    present with an explicit state (``UNAVAILABLE`` or ``OBSERVED``).
    """

    condition: CandidateObservationFactV2 | None
    price: CandidateObservationFactV2 | None
    currency: CandidateObservationFactV2 | None
    availability: CandidateObservationFactV2 | None
    seller: CandidateObservationFactV2 | None
    offer_url: str | None
    sales_unit: CandidateSalesUnitEvidenceV2

    def __post_init__(self) -> None:
        for name in ("condition", "price", "currency", "availability", "seller"):
            value = getattr(self, name)
            if value is not None and not isinstance(
                value, CandidateObservationFactV2
            ):
                raise TypeError(
                    f"{name} must be CandidateObservationFactV2 or None, "
                    f"got {type(value).__name__}"
                )
        if self.offer_url is not None and not isinstance(self.offer_url, str):
            raise TypeError(
                f"offer_url must be str or None, got {type(self.offer_url).__name__}"
            )
        if not isinstance(self.sales_unit, CandidateSalesUnitEvidenceV2):
            raise TypeError(
                "sales_unit must be CandidateSalesUnitEvidenceV2 (the "
                "packaging channel is always explicit; a case without a "
                f"sales_unit value is outside the contract), got "
                f"{type(self.sales_unit).__name__}"
            )

    def canonical(self) -> dict[str, object]:
        return {
            "condition": _canonical_fact(self.condition),
            "price": _canonical_fact(self.price),
            "currency": _canonical_fact(self.currency),
            "availability": _canonical_fact(self.availability),
            "seller": _canonical_fact(self.seller),
            "offer_url": self.offer_url,
            "sales_unit": self.sales_unit.canonical(),
        }


# ---------------------------------------------------------------------------
# Target-side evidence (S2-C-FU1)
# ---------------------------------------------------------------------------


class TargetIdentifierRelationKindV2(str, Enum):
    """Bounded kinds of the identifier relation a reviewed target context
    may record between the requested MPN and the reviewed base part.
    """

    CUSTOMER_RETRIEVAL_ALIAS = "CUSTOMER_RETRIEVAL_ALIAS"
    """A customer-defined retrieval relation (today: the 4D-D R/T packaging
    alias rule). ZERO identity authority: it is a retrieval hint about how
    the requested MPN relates to the reviewed base part, never a
    manufacturer-stated equivalence. (No other kind is wired; extending
    the vocabulary is a future reviewed change.)"""


def _validate_utc_instant(value: object, path: str) -> None:
    """Strict ISO-8601 UTC 'Z' instant grammar (the same discipline the
    persistence codec enforces on every recorded instant)."""
    if not isinstance(value, str) or not value:
        raise ValueError(f"{path} must be a non-empty ISO-8601 UTC instant str")
    if not value.endswith("Z"):
        raise ValueError(
            f"{path} must be an ISO-8601 UTC instant ending in 'Z', got {value!r}"
        )
    try:
        parsed = datetime.fromisoformat(value[:-1] + "+00:00")
    except ValueError:
        raise ValueError(
            f"{path}: not a valid ISO-8601 UTC instant: {value!r}"
        ) from None
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise ValueError(f"{path}: must be a timezone-aware UTC instant")


def _validate_sha256_hex(value: object, path: str) -> None:
    """64-character lowercase hex SHA-256 digest (fail closed)."""
    if not isinstance(value, str) or len(value) != 64:
        raise ValueError(f"{path} must be a 64-character hex SHA-256 digest")
    if any(ch not in "0123456789abcdef" for ch in value):
        raise ValueError(f"{path} must be a lowercase hex SHA-256 digest")


@dataclass(frozen=True)
class ReviewedTargetContextV2:
    """Reviewed manufacturer TARGET product context carried by the main
    execution flow (S2-C-FU1).

    STRUCTURED / REVIEWED observation evidence about the REQUESTED product
    — target-side only:

    * it NEVER grounds a candidate-side ``ProductEvidenceFactV2`` (the
      frozen S2-A candidate-source vocabulary is unchanged; the reviewed
      target context is not a candidate-side source);
    * its identifier relation is bounded: today only
      ``CUSTOMER_RETRIEVAL_ALIAS`` (zero identity authority, never
      manufacturer-stated equivalence). ``relation_family_part_numbers``
      are the customer-retrieval relation's family members OTHER than
      the requested form (full source-form part numbers, deterministic
      family order) — a retrieval shape, not a packaging claim;
    * it grants no pricing authority (V2 outputs are persist-only until
      Qualification V3).

    Today the main flow carries this context only from the ESTABLISHED 4D-D
    Micron 7500 alias acquisition (the reviewed family-catalog row matched
    by the frozen 2A comparator, verified ``is-ssd``, fetched from the
    reviewed origin; the acquisition is fail-closed and re-derives every
    authority-bearing field at construction). The field set is generic —
    a future reviewed source fills the same bounded shape. Absence is an
    explicit None on ``TargetEvidenceV2.reviewed_context`` (the main flow
    carries no other structured target facts today; the 6A/6C
    specification infrastructure exists only in the comparable-research
    flow and requires an established identity — nothing is fabricated).
    """

    manufacturer: str
    category: str
    matched_base_part_number: str
    relation_kind: TargetIdentifierRelationKindV2
    relation_family_part_numbers: tuple[str, ...]
    source_name: str
    source_url: str
    retrieved_at: str
    evidence_body_sha256: str

    def __post_init__(self) -> None:
        for name in (
            "manufacturer",
            "category",
            "matched_base_part_number",
            "source_name",
            "source_url",
        ):
            value = getattr(self, name)
            if not isinstance(value, str) or not value:
                raise ValueError(f"{name} must be a non-empty str")
        if not isinstance(self.relation_kind, TargetIdentifierRelationKindV2):
            raise TypeError(
                "relation_kind must be TargetIdentifierRelationKindV2, "
                f"got {type(self.relation_kind).__name__}"
            )
        if (
            not isinstance(self.relation_family_part_numbers, tuple)
            or not self.relation_family_part_numbers
        ):
            raise ValueError(
                "relation_family_part_numbers must be a non-empty tuple of "
                "str (the customer-retrieval relation's family members "
                "other than the requested form)"
            )
        for i, member in enumerate(self.relation_family_part_numbers):
            if not isinstance(member, str) or not member:
                raise ValueError(
                    f"relation_family_part_numbers[{i}] must be a "
                    "non-empty str"
                )
        if len(set(self.relation_family_part_numbers)) != len(
            self.relation_family_part_numbers
        ):
            raise ValueError(
                "relation_family_part_numbers must not contain duplicates"
            )
        _validate_utc_instant(self.retrieved_at, "retrieved_at")
        _validate_sha256_hex(self.evidence_body_sha256, "evidence_body_sha256")

    def canonical(self) -> dict[str, object]:
        return {
            "manufacturer": self.manufacturer,
            "category": self.category,
            "matched_base_part_number": self.matched_base_part_number,
            "relation_kind": self.relation_kind.value,
            "relation_family_part_numbers": list(
                self.relation_family_part_numbers
            ),
            "source_name": self.source_name,
            "source_url": self.source_url,
            "retrieved_at": self.retrieved_at,
            "evidence_body_sha256": self.evidence_body_sha256,
        }


@dataclass(frozen=True)
class TargetEvidenceV2:
    """Section A — TARGET-side evidence, with the evidence class explicit
    (S2-C-FU1).

    * ``mpn`` — STRUCTURED: the caller-published requested MPN (the run's
      identity anchor; the case binds to it and the persistence run-binding
      check verifies it against the run's canonical request);
    * ``description_raw_text`` — RAW observation text: the caller-published
      requested description. It may support semantic reasoning; it is not a
      reviewed or structured specification, and a token occurring in it is
      not structured evidence. Explicit None when the request carries no
      description (absent, never an empty sentinel);
    * ``reviewed_context`` — STRUCTURED / REVIEWED: present only when the
      main execution flow carries a reviewed manufacturer target context
      for this request; explicit None otherwise.
    """

    mpn: str
    description_raw_text: str | None
    reviewed_context: ReviewedTargetContextV2 | None

    def __post_init__(self) -> None:
        if not isinstance(self.mpn, str) or not self.mpn:
            raise ValueError("mpn must be a non-empty str (the run's identity anchor)")
        if self.description_raw_text is not None:
            if (
                not isinstance(self.description_raw_text, str)
                or not self.description_raw_text
            ):
                raise ValueError(
                    "description_raw_text must be a non-empty str or None "
                    "(an absent description is explicit None, never an "
                    "empty sentinel)"
                )
        if self.reviewed_context is not None and not isinstance(
            self.reviewed_context, ReviewedTargetContextV2
        ):
            raise TypeError(
                "reviewed_context must be ReviewedTargetContextV2 or None, "
                f"got {type(self.reviewed_context).__name__}"
            )

    def canonical(self) -> dict[str, object]:
        return {
            "mpn": self.mpn,
            "description_raw_text": self.description_raw_text,
            "reviewed_context": (
                self.reviewed_context.canonical()
                if self.reviewed_context is not None
                else None
            ),
        }


def _published_fact(value: str | None) -> CandidateObservationFactV2 | None:
    """A page-published structured field becomes a bounded fact with its
    provenance; an absent / empty field is explicit None."""
    if value is None:
        return None
    return CandidateObservationFactV2(
        value=value,
        source=CandidateEvidenceSourceV2.PUBLISHED_STRUCTURED_FIELD,
    )


def build_candidate_product_evidence_v2(
    observation: ListingObservation,
) -> CandidateProductEvidenceV2:
    """The live main-flow structured candidate PRODUCT observation evidence
    (S2-C-FU1).

    Fills ONLY bounded published-structured-field facts the 3A extractor
    actually carries: the page-published brand field. Every other product
    dimension stays explicit None (absent): the main-flow extractor
    normalizes no family / generation / capacity / interface / form factor
    / product role / accessory relation / revision-or-suffix facts, and NO
    token of the raw title is parsed into a structured fact — token
    occurrence in the title is RAW observation evidence, not bounded
    structured evidence (the flawed 'structured title evidence' claim
    S2-C-FU1 corrects).

    The published title is carried as ``raw_title_text`` (RAW observation
    text, labeled as such in the prompt); the main flow carries no
    specification text (``raw_specification_text`` is explicit None — the
    remaining JSON-LD material stays in the opaque raw reference, which no
    business rule may parse).
    """
    if not isinstance(observation, ListingObservation):
        raise TypeError(
            "observation must be ListingObservation, "
            f"got {type(observation).__name__}"
        )
    return CandidateProductEvidenceV2(
        product_family=None,
        generation=None,
        capacity=None,
        interface=None,
        form_factor=None,
        product_role=None,
        accessory_relation=None,
        brand=_published_fact(observation.brand_text),
        revision_or_suffix=None,
        raw_title_text=observation.product_title or None,
        raw_specification_text=None,
    )


def build_candidate_commercial_evidence_v2(
    observation: ListingObservation,
) -> CandidateCommercialEvidenceV2:
    """The live main-flow structured candidate COMMERCIAL observation
    evidence (S2-C-FU1).

    The published commercial fields (condition, price, currency,
    availability, seller, offer URL) become bounded facts with their
    published-structured-field provenance; absent fields are explicit
    None. These are NEVER identity evidence (the prompt labels the section;
    no authority derivation consumes it).

    The sales-unit / packaging channel is ALWAYS the explicit
    ``UNAVAILABLE`` state from the main-flow extractor: it publishes no
    packaging field, and no packaging value is inferred from price,
    availability, or any other commercial fact. A future extractor- or
    reviewed-source-provided packaging observation fills the same bounded
    channel (``OBSERVED``) — the contract already represents single unit,
    pack quantity, tray/factory pack, and bundle.
    """
    if not isinstance(observation, ListingObservation):
        raise TypeError(
            "observation must be ListingObservation, "
            f"got {type(observation).__name__}"
        )
    return CandidateCommercialEvidenceV2(
        condition=_published_fact(observation.condition_text),
        price=_published_fact(observation.price_text),
        currency=_published_fact(observation.currency_text),
        availability=_published_fact(observation.availability_text),
        seller=_published_fact(observation.seller_text),
        offer_url=observation.offer_url_text,
        sales_unit=SALES_UNIT_EVIDENCE_UNAVAILABLE,
    )


# ---------------------------------------------------------------------------
# Final Semantic V2 input contract
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class SemanticMatchCaseV2:
    """The final, versioned, immutable Semantic V2 input (S2-C, corrected
    in place by S2-C-FU1 before freeze).

    Everything the V2 prompt renders, in five clearly separated sections
    with the evidence class of every value explicit:

    * **A. TARGET** (``TargetEvidenceV2``) — the structured caller-
      published requested MPN (the run's identity anchor), the requested
      description as RAW observation text, and the reviewed manufacturer
      target context when the main execution flow carries one (explicit
      None otherwise). The case is identified by ``case_id``.
    * **B. CANDIDATE LISTING** — source URL, the published identifier
      fields (MPN field / SKU), the frozen 3C evidence source, the
      STRUCTURED candidate product observation evidence
      (``CandidateProductEvidenceV2`` — the nine bounded product
      dimensions, each a bounded fact with explicit provenance or an
      explicit absence, plus the raw title / specification observation
      text), and the STRUCTURED candidate commercial observation evidence
      (``CandidateCommercialEvidenceV2`` — the published commercial facts
      and the explicit sales-unit / packaging channel; NEVER identity
      evidence).
    * **C. DETERMINISTIC IDENTITY CONTEXT** — the frozen S2-A derived
      state (``identity_state`` / ``substate`` /
      ``primary_relationship_signal`` / all bounded
      ``relationship_signals`` / the frozen normalized requested and
      candidate keys) plus the frozen state-specific
      ``relationship_requirement`` snapshot.
    * **D. CONTEXT PROVENANCE** — the bounded
      ``ContextProvenance`` classes actually present. The three classes
      remain distinct: ``CUSTOMER_RETRIEVAL_RELATION`` is retrieval-only
      and carries zero identity authority; ``MANUFACTURER_PRODUCT_CONTEXT``
      is not ``MANUFACTURER_RELATION_AUTHORITY``.
    * **E. PRODUCT EVIDENCE** — the authority-side
      ``ProductEvidenceProfileV2`` (deterministic/reviewed only). The
      model may observe it and report semantic conclusions, but it can
      NEVER create or upgrade the authority-side profile: no member of the
      bounded candidate-source vocabulary is a model claim, and no
      model-observation evidence (section B, structured or raw) can ground
      an authority fact.

    Construction is fail-closed: exact types, no silent defaults (every
    field is required; absent evidence is explicit None / an explicit
    channel state), the recorded deterministic context must be a
    legitimate S2-A context, the state must be ``DETERMINISTIC_UNCERTAIN``
    (a semantic entry point — anything else is outside the V2 input
    contract), the primary signal and the relationship requirement must
    agree with the frozen tables, and the product-evidence profile must be
    state-consistent and supported by the recorded provenances.
    """

    # -- A. TARGET ---------------------------------------------------------
    case_id: str
    target: TargetEvidenceV2

    # -- B. CANDIDATE LISTING ---------------------------------------------
    candidate_source_url: str
    candidate_mpn_field: str | None
    candidate_sku: str | None
    candidate_evidence_source: str
    candidate_product: CandidateProductEvidenceV2
    candidate_commercial: CandidateCommercialEvidenceV2

    # -- C. DETERMINISTIC IDENTITY CONTEXT ---------------------------------
    identity_state: IdentityStateV2
    substate: (
        VerifiedSubstateV2
        | UncertainSubstateV2
        | ConflictSubstateV2
        | UnevaluableSubstateV2
    )
    primary_relationship_signal: IdentityRelationshipSignal
    relationship_signals: frozenset[IdentityRelationshipSignal]
    normalized_requested_part_number: str
    normalized_candidate_part_number: str
    relationship_requirement: RelationshipRequirement

    # -- D. CONTEXT PROVENANCE ----------------------------------------------
    context_provenances: frozenset[ContextProvenance]

    # -- E. PRODUCT EVIDENCE (authority side; deterministic/reviewed only) --
    product_evidence: ProductEvidenceProfileV2

    def __post_init__(self) -> None:
        # -- exact types (fail closed; no coercion, no defaults) ----------
        for name in (
            "case_id",
            "candidate_source_url",
            "candidate_evidence_source",
            "normalized_requested_part_number",
            "normalized_candidate_part_number",
        ):
            value = getattr(self, name)
            if not isinstance(value, str):
                raise TypeError(
                    f"{name} must be str, got {type(value).__name__}"
                )
        for name in ("candidate_mpn_field", "candidate_sku"):
            value = getattr(self, name)
            if value is not None and not isinstance(value, str):
                raise TypeError(
                    f"{name} must be str or None, got {type(value).__name__}"
                )
        if not self.case_id:
            raise ValueError("case_id must be non-empty")
        if not self.candidate_source_url:
            raise ValueError("candidate_source_url must be non-empty")
        if not self.candidate_evidence_source:
            raise ValueError("candidate_evidence_source must be non-empty")
        if not isinstance(self.target, TargetEvidenceV2):
            raise TypeError(
                f"target must be TargetEvidenceV2, got {type(self.target).__name__}"
            )
        if not isinstance(self.candidate_product, CandidateProductEvidenceV2):
            raise TypeError(
                "candidate_product must be CandidateProductEvidenceV2, "
                f"got {type(self.candidate_product).__name__}"
            )
        if not isinstance(
            self.candidate_commercial, CandidateCommercialEvidenceV2
        ):
            raise TypeError(
                "candidate_commercial must be CandidateCommercialEvidenceV2, "
                f"got {type(self.candidate_commercial).__name__}"
            )
        if not isinstance(self.identity_state, IdentityStateV2):
            raise TypeError(
                "identity_state must be IdentityStateV2, "
                f"got {type(self.identity_state).__name__}"
            )
        substate_type = type(self.substate)
        if substate_type not in (
            VerifiedSubstateV2,
            UncertainSubstateV2,
            ConflictSubstateV2,
            UnevaluableSubstateV2,
        ):
            raise TypeError(
                "substate must be a V2 sub-state enum member, "
                f"got {substate_type.__name__}"
            )
        if not isinstance(
            self.primary_relationship_signal, IdentityRelationshipSignal
        ):
            raise TypeError(
                "primary_relationship_signal must be "
                f"IdentityRelationshipSignal, got "
                f"{type(self.primary_relationship_signal).__name__}"
            )
        if not isinstance(self.relationship_signals, frozenset):
            raise TypeError(
                "relationship_signals must be a frozenset, "
                f"got {type(self.relationship_signals).__name__}"
            )
        for signal in self.relationship_signals:
            if not isinstance(signal, IdentityRelationshipSignal):
                raise TypeError(
                    "relationship_signals must contain only "
                    f"IdentityRelationshipSignal members, got {signal!r}"
                )
        if not isinstance(self.relationship_requirement, RelationshipRequirement):
            raise TypeError(
                "relationship_requirement must be RelationshipRequirement, "
                f"got {type(self.relationship_requirement).__name__}"
            )
        if not isinstance(self.context_provenances, frozenset):
            raise TypeError(
                "context_provenances must be a frozenset, "
                f"got {type(self.context_provenances).__name__}"
            )
        for provenance in self.context_provenances:
            if not isinstance(provenance, ContextProvenance):
                raise TypeError(
                    "context_provenances must contain only ContextProvenance "
                    f"members, got {provenance!r}"
                )
        if not isinstance(self.product_evidence, ProductEvidenceProfileV2):
            raise TypeError(
                "product_evidence must be ProductEvidenceProfileV2, "
                f"got {type(self.product_evidence).__name__}"
            )

        # -- C: the recorded context must be a legitimate S2-A context ---
        # (state/sub-state consistency, exactly one primary signal,
        # per-sub-state signal permission — the frozen constructor
        # validates and fails closed).
        context = IdentityStateAssessmentV2(
            state=self.identity_state,
            substate=self.substate,
            relationship_signals=self.relationship_signals,
            normalized_requested_part_number=(
                self.normalized_requested_part_number
            ),
            normalized_candidate_part_number=(
                self.normalized_candidate_part_number
            ),
        )
        if self.primary_relationship_signal is not (
            context.primary_relationship_signal
        ):
            raise ValueError(
                "primary_relationship_signal disagrees with the recorded "
                "relationship signals; the V2 input contract fails closed"
            )
        if self.identity_state is not IdentityStateV2.DETERMINISTIC_UNCERTAIN:
            raise ValueError(
                "a SemanticMatchCaseV2 exists only for a semantic entry "
                f"point ({IdentityStateV2.DETERMINISTIC_UNCERTAIN.value}); "
                f"got {self.identity_state.value}"
            )
        expected_requirement = substate_relationship_requirement(
            self.substate, self.primary_relationship_signal
        )
        if self.relationship_requirement is not expected_requirement:
            raise ValueError(
                "relationship_requirement disagrees with the frozen "
                "state/sub-state-specific requirement table; the V2 input "
                "contract fails closed (the requirement is contract data, "
                "not caller input)"
            )

        # -- E: authority-side evidence must be state-consistent and
        # supported (the frozen derivations fail closed).
        if (
            self.substate is UncertainSubstateV2.U4_NO_MPN
            and not self.product_evidence.has_usable_product_title
        ):
            raise ValueError(
                "U4_NO_MPN cases are derived through the frozen usable-"
                "title gate; a V2 input without a usable product title "
                "contradicts the state"
            )
        derive_product_evidence_quality(
            self.product_evidence, self.context_provenances
        )

    def canonical(self) -> dict[str, object]:
        """The exact canonical encoding of the V2 input (sections A–E).

        JSON-native only (no enums, no floats, no dataclasses): sets are
        encoded as sorted unique value lists, nullable candidate facts as
        explicit nulls.
        """
        return {
            "case_id": self.case_id,
            "target": self.target.canonical(),
            "candidate": {
                "source_url": self.candidate_source_url,
                "mpn_field": self.candidate_mpn_field,
                "sku": self.candidate_sku,
                "evidence_source": self.candidate_evidence_source,
                "product": self.candidate_product.canonical(),
                "commercial": self.candidate_commercial.canonical(),
            },
            "deterministic_identity_context": {
                "identity_state": self.identity_state.value,
                "substate": self.substate.value,
                "primary_relationship_signal": (
                    self.primary_relationship_signal.value
                ),
                "relationship_signals": sorted(
                    signal.value for signal in self.relationship_signals
                ),
                "normalized_requested_part_number": (
                    self.normalized_requested_part_number
                ),
                "normalized_candidate_part_number": (
                    self.normalized_candidate_part_number
                ),
                "relationship_requirement": (
                    self.relationship_requirement.value
                ),
            },
            "context_provenance": sorted(
                provenance.value for provenance in self.context_provenances
            ),
            "product_evidence": {
                "has_usable_product_title": (
                    self.product_evidence.has_usable_product_title
                ),
                "matched_facts": sorted(
                    (
                        {
                            "dimension": fact.dimension.value,
                            "sources": sorted(
                                source.value for source in fact.sources
                            ),
                        }
                        for fact in self.product_evidence.matched_facts
                    ),
                    key=lambda fact: (fact["dimension"], fact["sources"]),
                ),
            },
        }


def build_semantic_match_case_v2(
    *,
    case_id: str,
    request: ResearchRequest,
    assessment: ListingIdentityAssessment,
    context: IdentityStateAssessmentV2,
    product_evidence: ProductEvidenceProfileV2,
    context_provenances: frozenset[ContextProvenance],
    reviewed_target_context: ReviewedTargetContextV2 | None,
) -> SemanticMatchCaseV2:
    """Safely construct the final V2 input for one V2-eligible candidate.

    The builder binds the case to the REAL frozen facts and fails closed
    on any mismatch (no caller may present a foreign context, a foreign
    request, or a fabricated candidate):

    * ``assessment.requested_part_number`` must equal the request's
      canonical MPN (the case binds to the run's request);
    * ``context`` must equal the S2-A derivation RE-RUN on the same
      assessment (the deterministic context is contract-derived, not
      caller-supplied);
    * the candidate section is read from the assessment's frozen
      observation through the bounded evidence builders (absent facts are
      explicit None / an explicit channel state; the published title is
      RAW observation text, never parsed into structured facts; the
      sales-unit / packaging channel is the explicit UNAVAILABLE state —
      the main-flow extractor publishes no packaging field and nothing is
      inferred from price);
    * the authority-side ``product_evidence`` and
      ``context_provenances`` are the bounded evidence inputs (built by
      ``build_v2_product_evidence_profile`` in the live path);
    * ``reviewed_target_context`` is explicit: the reviewed manufacturer
      TARGET context the main execution flow carries for this request
      (today: the ESTABLISHED 4D-D alias acquisition), or explicit None
      when the main flow carries none.

    The relationship requirement is NOT a parameter: the case constructor
    derives and validates it from the frozen table.
    """
    if not isinstance(case_id, str) or not case_id:
        raise ValueError("case_id must be a non-empty str")
    if not isinstance(request, ResearchRequest):
        raise TypeError(
            "request must be ResearchRequest, "
            f"got {type(request).__name__}"
        )
    if not isinstance(assessment, ListingIdentityAssessment):
        raise TypeError(
            "assessment must be ListingIdentityAssessment, "
            f"got {type(assessment).__name__}"
        )
    if not isinstance(context, IdentityStateAssessmentV2):
        raise TypeError(
            "context must be IdentityStateAssessmentV2, "
            f"got {type(context).__name__}"
        )
    if not isinstance(product_evidence, ProductEvidenceProfileV2):
        raise TypeError(
            "product_evidence must be ProductEvidenceProfileV2, "
            f"got {type(product_evidence).__name__}"
        )
    if not isinstance(context_provenances, frozenset):
        raise TypeError(
            "context_provenances must be a frozenset, "
            f"got {type(context_provenances).__name__}"
        )
    if reviewed_target_context is not None and not isinstance(
        reviewed_target_context, ReviewedTargetContextV2
    ):
        raise TypeError(
            "reviewed_target_context must be ReviewedTargetContextV2 or "
            f"None (explicit absence), got "
            f"{type(reviewed_target_context).__name__}"
        )
    if assessment.requested_part_number != request.manufacturer_part_number:
        raise ValueError(
            "the assessment's requested part number does not bind to the "
            "request; the V2 case cannot be constructed for a foreign "
            "request"
        )
    rederived = derive_identity_state_v2(assessment)
    if rederived != context:
        raise ValueError(
            "the supplied deterministic context does not equal the frozen "
            "S2-A derivation of the assessment; the V2 case builder fails "
            "closed on a foreign or tampered context"
        )

    observation = assessment.normalized_listing.observation
    return SemanticMatchCaseV2(
        case_id=case_id,
        target=TargetEvidenceV2(
            mpn=request.manufacturer_part_number,
            description_raw_text=request.description or None,
            reviewed_context=reviewed_target_context,
        ),
        candidate_source_url=observation.source_url,
        candidate_mpn_field=observation.manufacturer_part_number_text,
        candidate_sku=observation.sku_text,
        candidate_evidence_source=assessment.candidate_evidence_source.value,
        candidate_product=build_candidate_product_evidence_v2(observation),
        candidate_commercial=build_candidate_commercial_evidence_v2(observation),
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
        context_provenances=context_provenances,
        product_evidence=product_evidence,
    )


# ---------------------------------------------------------------------------
# SAFE product-evidence builder (S2-C)
# ---------------------------------------------------------------------------


def build_v2_product_evidence_profile(
    *,
    observation: ListingObservation,
    context_provenances: frozenset[ContextProvenance],
    matched_facts: frozenset[ProductEvidenceFactV2],
) -> ProductEvidenceProfileV2:
    """The SAFE authority-side product-evidence builder (S2-C).

    The bounded ``ProductEvidenceProfileV2`` can only be reached from
    evidence that is independently present:

    * ``has_usable_product_title`` — the frozen usability gate over the
      observation's product title;
    * ``matched_facts`` — EXPLICITLY supplied bounded facts. Each fact is
      a (``ProductEvidenceDimension``, grounded candidate-side source)
      pair whose source vocabulary is exactly
      ``{LISTING_PRODUCT_TITLE, REVIEWED_PRODUCT_CONTEXT}`` (the frozen
      S2-A vocabulary has NO model-claim member, so a model's
      ``matched_attributes`` can never become an authority fact through
      this builder — there is no parameter to pass them into).

    Fail-closed cross-validation: a title-grounded fact requires a usable
    title (the profile constructor); a reviewed-context-grounded fact
    requires a provenance carrying ``GROUND_PRODUCT_FACTS`` (the frozen
    quality derivation); an empty fact set is the honest main-flow result.

    DOCUMENTED LIMITATION: the current main-flow deterministic extraction
    (``ListingObservation``) contains no attribute extraction that proves
    exact bounded identity-dimension equality with the target, so the
    live execution path passes ``matched_facts=frozenset()``: candidates
    remain at most LIMITED (usable title) or WEAK, and the frozen S2-A
    STRONG bar is not weakened. No fact is fabricated to increase recall.
    """
    if not isinstance(observation, ListingObservation):
        raise TypeError(
            "observation must be ListingObservation, "
            f"got {type(observation).__name__}"
        )
    if not isinstance(context_provenances, frozenset):
        raise TypeError(
            "context_provenances must be a frozenset, "
            f"got {type(context_provenances).__name__}"
        )
    if not isinstance(matched_facts, frozenset):
        raise TypeError(
            "matched_facts must be a frozenset, "
            f"got {type(matched_facts).__name__}"
        )
    for fact in matched_facts:
        if not isinstance(fact, ProductEvidenceFactV2):
            raise TypeError(
                "matched_facts must contain only ProductEvidenceFactV2, "
                f"got {fact!r}"
            )

    profile = ProductEvidenceProfileV2(
        has_usable_product_title=bool(observation.product_title),
        matched_facts=matched_facts,
    )
    # Fail closed on an unsupported profile (e.g. a reviewed-context
    # grounded fact without a grounding provenance).
    derive_product_evidence_quality(profile, context_provenances)
    return profile


# ---------------------------------------------------------------------------
# Final Semantic V2 output contract — bounded attribute vocabulary
# ---------------------------------------------------------------------------


class SemanticAttributeDimensionV2(str, Enum):
    """Bounded dimensions of a structured V2 attribute observation.

    The final V2 contract distinguishes, at minimum: product family,
    generation, capacity, interface, form factor, product role, accessory
    relation, packaging quantity / sales unit, bundle, brand,
    revision / suffix, and condition. These are OBSERVATION dimensions for
    the model's structured conclusions (matched / conflicting / missing);
    they are NOT the authority-side ``ProductEvidenceDimension``
    vocabulary (which stays bounded to the six hard identity dimensions).
    CONDITION is a price dimension, never identity.
    """

    PRODUCT_FAMILY = "PRODUCT_FAMILY"
    GENERATION = "GENERATION"
    CAPACITY = "CAPACITY"
    INTERFACE = "INTERFACE"
    FORM_FACTOR = "FORM_FACTOR"
    PRODUCT_ROLE = "PRODUCT_ROLE"
    ACCESSORY_RELATION = "ACCESSORY_RELATION"
    PACKAGING_QUANTITY = "PACKAGING_QUANTITY"
    BUNDLE = "BUNDLE"
    BRAND = "BRAND"
    REVISION_OR_SUFFIX = "REVISION_OR_SUFFIX"
    CONDITION = "CONDITION"


@dataclass(frozen=True)
class SemanticAttributeV2:
    """One bounded structured attribute observation (dimension + detail).

    ``detail`` is the observed value text (e.g. "3840GB vs 1920GB"); it is
    bounded audit context, never a keyword that determines
    HARD_CONFLICT — the structured ``ConflictClass`` set does that.
    """

    dimension: SemanticAttributeDimensionV2
    detail: str

    def __post_init__(self) -> None:
        if not isinstance(self.dimension, SemanticAttributeDimensionV2):
            raise TypeError(
                "dimension must be SemanticAttributeDimensionV2, "
                f"got {type(self.dimension).__name__}"
            )
        if not isinstance(self.detail, str):
            raise TypeError(
                f"detail must be str, got {type(self.detail).__name__}"
            )

    def canonical(self) -> dict[str, object]:
        return {"dimension": self.dimension.value, "detail": self.detail}


# ---------------------------------------------------------------------------
# Final Semantic V2 output contract — bounded reason-code vocabulary
# ---------------------------------------------------------------------------


class SemanticReasonCodeV2(str, Enum):
    """Bounded machine-readable V2 reason codes (S2-C).

    Generic semantic classes only — no manufacturer-specific codes. The
    code names the PRIMARY driver; it must stay internally coherent with
    the structured conflict set (frozen ``REASON_CODE_RULES``): a NO_MATCH
    caused by a CAPACITY conflict carries ``ConflictClass.CAPACITY``, and
    so on. Unknown codes fail closed.
    """

    # MATCH drivers.
    MATCH_EXACT_PRODUCT_CONTEXT = "MATCH_EXACT_PRODUCT_CONTEXT"
    """Product family / generation context aligns exactly on the supplied
    evidence (e.g. the identifiers and the product context agree)."""
    MATCH_DESCRIPTION_AND_ATTRIBUTES = "MATCH_DESCRIPTION_AND_ATTRIBUTES"
    """Description and bounded attributes (capacity / interface / form
    factor / role) align without a material conflict."""
    MATCH_AUTHORIZED_IDENTIFIER_RELATION = (
        "MATCH_AUTHORIZED_IDENTIFIER_RELATION"
    )
    """A labeled manufacturer relationship authority (when explicitly
    provided in the context provenance) establishes the identifier
    relation."""

    # UNCERTAIN drivers.
    UNCERTAIN_MISSING_CRITICAL_ATTRIBUTES = (
        "UNCERTAIN_MISSING_CRITICAL_ATTRIBUTES"
    )
    """Critical identity attributes are missing from the supplied
    evidence; more evidence (or review) is required."""
    UNCERTAIN_IDENTIFIER_RELATION = "UNCERTAIN_IDENTIFIER_RELATION"
    """The identifier relationship (title MPN wording, near-miss shape,
    SKU) cannot be resolved to equivalence or non-equivalence on the
    supplied evidence."""

    # NO_MATCH drivers (each names the required structured conflict).
    NO_MATCH_MPN_IDENTITY = "NO_MATCH_MPN_IDENTITY"
    NO_MATCH_PRODUCT_FAMILY = "NO_MATCH_PRODUCT_FAMILY"
    NO_MATCH_GENERATION = "NO_MATCH_GENERATION"
    NO_MATCH_CAPACITY = "NO_MATCH_CAPACITY"
    NO_MATCH_INTERFACE = "NO_MATCH_INTERFACE"
    NO_MATCH_FORM_FACTOR = "NO_MATCH_FORM_FACTOR"
    NO_MATCH_PRODUCT_ROLE = "NO_MATCH_PRODUCT_ROLE"
    NO_MATCH_ACCESSORY = "NO_MATCH_ACCESSORY"
    NO_MATCH_PACKAGING = "NO_MATCH_PACKAGING"
    """Different commercial sales unit / pack quantity (physical-product
    equivalence without sales-unit equivalence)."""
    NO_MATCH_BUNDLE = "NO_MATCH_BUNDLE"
    NO_MATCH_MULTIPLE_CONFLICTS = "NO_MATCH_MULTIPLE_CONFLICTS"
    """Two or more ALWAYS_HARD conflicts jointly establish non-equivalence."""
    NO_MATCH_OTHER = "NO_MATCH_OTHER"
    """A material conflict outside the named classes establishes
    non-equivalence."""


@dataclass(frozen=True)
class SemanticReasonCodeRuleV2:
    """The frozen coherence rule of one V2 reason code.

    * ``decision`` — the only decision family the code may serve;
    * ``required_conflict_classes`` — structured classes that MUST be
      present in the response's conflict set;
    * ``min_hard_conflict_count`` — minimum number of ALWAYS_HARD classes
      in the response's conflict set;
    * ``requires_nonempty_missing_attributes`` — the response must name at
      least one missing critical dimension;
    * ``requires_any_conflict`` — the response's conflict set must be
      non-empty.

    Plus the global per-decision invariants (enforced by
    ``validate_semantic_response_v2``): a MATCH or UNCERTAIN may never
    carry an ALWAYS_HARD conflict class (a hard conflict decides
    NO_MATCH), and a NO_MATCH is always grounded in its structured
    conflict set.
    """

    code: SemanticReasonCodeV2
    decision: V2SemanticDecision
    required_conflict_classes: frozenset[ConflictClass]
    min_hard_conflict_count: int
    requires_nonempty_missing_attributes: bool
    requires_any_conflict: bool


#: Frozen V2 reason-code rules: runtime-immutable tuple of immutable
#: entries, one per code, import-self-checked for completeness.
REASON_CODE_RULES: Final[tuple[SemanticReasonCodeRuleV2, ...]] = (
    SemanticReasonCodeRuleV2(
        code=SemanticReasonCodeV2.MATCH_EXACT_PRODUCT_CONTEXT,
        decision=V2SemanticDecision.MATCH,
        required_conflict_classes=frozenset(),
        min_hard_conflict_count=0,
        requires_nonempty_missing_attributes=False,
        requires_any_conflict=False,
    ),
    SemanticReasonCodeRuleV2(
        code=SemanticReasonCodeV2.MATCH_DESCRIPTION_AND_ATTRIBUTES,
        decision=V2SemanticDecision.MATCH,
        required_conflict_classes=frozenset(),
        min_hard_conflict_count=0,
        requires_nonempty_missing_attributes=False,
        requires_any_conflict=False,
    ),
    SemanticReasonCodeRuleV2(
        code=SemanticReasonCodeV2.MATCH_AUTHORIZED_IDENTIFIER_RELATION,
        decision=V2SemanticDecision.MATCH,
        required_conflict_classes=frozenset(),
        min_hard_conflict_count=0,
        requires_nonempty_missing_attributes=False,
        requires_any_conflict=False,
    ),
    SemanticReasonCodeRuleV2(
        code=SemanticReasonCodeV2.UNCERTAIN_MISSING_CRITICAL_ATTRIBUTES,
        decision=V2SemanticDecision.UNCERTAIN,
        required_conflict_classes=frozenset(),
        min_hard_conflict_count=0,
        requires_nonempty_missing_attributes=True,
        requires_any_conflict=False,
    ),
    SemanticReasonCodeRuleV2(
        code=SemanticReasonCodeV2.UNCERTAIN_IDENTIFIER_RELATION,
        decision=V2SemanticDecision.UNCERTAIN,
        required_conflict_classes=frozenset(),
        min_hard_conflict_count=0,
        requires_nonempty_missing_attributes=False,
        requires_any_conflict=False,
    ),
    SemanticReasonCodeRuleV2(
        code=SemanticReasonCodeV2.NO_MATCH_MPN_IDENTITY,
        decision=V2SemanticDecision.NO_MATCH,
        required_conflict_classes=frozenset({ConflictClass.MPN_IDENTITY}),
        min_hard_conflict_count=1,
        requires_nonempty_missing_attributes=False,
        requires_any_conflict=True,
    ),
    SemanticReasonCodeRuleV2(
        code=SemanticReasonCodeV2.NO_MATCH_PRODUCT_FAMILY,
        decision=V2SemanticDecision.NO_MATCH,
        required_conflict_classes=frozenset({ConflictClass.PRODUCT_FAMILY}),
        min_hard_conflict_count=1,
        requires_nonempty_missing_attributes=False,
        requires_any_conflict=True,
    ),
    SemanticReasonCodeRuleV2(
        code=SemanticReasonCodeV2.NO_MATCH_GENERATION,
        decision=V2SemanticDecision.NO_MATCH,
        required_conflict_classes=frozenset({ConflictClass.GENERATION}),
        min_hard_conflict_count=1,
        requires_nonempty_missing_attributes=False,
        requires_any_conflict=True,
    ),
    SemanticReasonCodeRuleV2(
        code=SemanticReasonCodeV2.NO_MATCH_CAPACITY,
        decision=V2SemanticDecision.NO_MATCH,
        required_conflict_classes=frozenset({ConflictClass.CAPACITY}),
        min_hard_conflict_count=1,
        requires_nonempty_missing_attributes=False,
        requires_any_conflict=True,
    ),
    SemanticReasonCodeRuleV2(
        code=SemanticReasonCodeV2.NO_MATCH_INTERFACE,
        decision=V2SemanticDecision.NO_MATCH,
        required_conflict_classes=frozenset({ConflictClass.INTERFACE}),
        min_hard_conflict_count=1,
        requires_nonempty_missing_attributes=False,
        requires_any_conflict=True,
    ),
    SemanticReasonCodeRuleV2(
        code=SemanticReasonCodeV2.NO_MATCH_FORM_FACTOR,
        decision=V2SemanticDecision.NO_MATCH,
        required_conflict_classes=frozenset({ConflictClass.FORM_FACTOR}),
        min_hard_conflict_count=1,
        requires_nonempty_missing_attributes=False,
        requires_any_conflict=True,
    ),
    SemanticReasonCodeRuleV2(
        code=SemanticReasonCodeV2.NO_MATCH_PRODUCT_ROLE,
        decision=V2SemanticDecision.NO_MATCH,
        required_conflict_classes=frozenset({ConflictClass.PRODUCT_ROLE}),
        min_hard_conflict_count=1,
        requires_nonempty_missing_attributes=False,
        requires_any_conflict=True,
    ),
    SemanticReasonCodeRuleV2(
        code=SemanticReasonCodeV2.NO_MATCH_ACCESSORY,
        decision=V2SemanticDecision.NO_MATCH,
        required_conflict_classes=frozenset({ConflictClass.ACCESSORY_RELATION}),
        min_hard_conflict_count=1,
        requires_nonempty_missing_attributes=False,
        requires_any_conflict=True,
    ),
    SemanticReasonCodeRuleV2(
        code=SemanticReasonCodeV2.NO_MATCH_PACKAGING,
        decision=V2SemanticDecision.NO_MATCH,
        required_conflict_classes=frozenset(
            {ConflictClass.PACKAGING_QUANTITY}
        ),
        min_hard_conflict_count=1,
        requires_nonempty_missing_attributes=False,
        requires_any_conflict=True,
    ),
    SemanticReasonCodeRuleV2(
        code=SemanticReasonCodeV2.NO_MATCH_BUNDLE,
        decision=V2SemanticDecision.NO_MATCH,
        required_conflict_classes=frozenset({ConflictClass.BUNDLE}),
        min_hard_conflict_count=1,
        requires_nonempty_missing_attributes=False,
        requires_any_conflict=True,
    ),
    SemanticReasonCodeRuleV2(
        code=SemanticReasonCodeV2.NO_MATCH_MULTIPLE_CONFLICTS,
        decision=V2SemanticDecision.NO_MATCH,
        required_conflict_classes=frozenset(),
        min_hard_conflict_count=2,
        requires_nonempty_missing_attributes=False,
        requires_any_conflict=True,
    ),
    SemanticReasonCodeRuleV2(
        code=SemanticReasonCodeV2.NO_MATCH_OTHER,
        decision=V2SemanticDecision.NO_MATCH,
        required_conflict_classes=frozenset(),
        min_hard_conflict_count=0,
        requires_nonempty_missing_attributes=False,
        requires_any_conflict=True,
    ),
)


def semantic_reason_code_rule(
    code: SemanticReasonCodeV2,
) -> SemanticReasonCodeRuleV2:
    """Pure fail-closed lookup of one frozen reason-code rule."""
    if not isinstance(code, SemanticReasonCodeV2):
        raise TypeError(
            "code must be SemanticReasonCodeV2, "
            f"got {type(code).__name__}"
        )
    for rule in REASON_CODE_RULES:
        if rule.code is code:
            return rule
    raise ValueError(
        f"reason code {code.value} has no frozen rule; the rules table "
        "must cover the whole vocabulary"
    )


# Mechanical self-consistency of the frozen V2 reason-code rules, verified
# once at import (pure data check, no mutable state): exactly one rule per
# code, the code's family prefix agrees with the rule's decision, every
# NO_MATCH rule is conflict-grounded, and the module's global namespace
# carries no mutable containers.
if len(REASON_CODE_RULES) != len(SemanticReasonCodeV2) or {
    rule.code for rule in REASON_CODE_RULES
} != set(SemanticReasonCodeV2):
    raise RuntimeError(
        "REASON_CODE_RULES must define exactly one rule per V2 reason code"
    )
for _rule in REASON_CODE_RULES:
    _expected_prefix = {
        V2SemanticDecision.MATCH: "MATCH_",
        V2SemanticDecision.NO_MATCH: "NO_MATCH_",
        V2SemanticDecision.UNCERTAIN: "UNCERTAIN_",
    }[_rule.decision]
    if not _rule.code.value.startswith(_expected_prefix):
        raise RuntimeError(
            f"reason code {_rule.code.value} family prefix disagrees with "
            f"its frozen decision {_rule.decision.value}"
        )
    if (
        _rule.decision is V2SemanticDecision.NO_MATCH
        and not _rule.requires_any_conflict
    ):
        raise RuntimeError(
            f"NO_MATCH reason code {_rule.code.value} must be grounded in "
            "its structured conflict set"
        )
for _global_name, _global_value in list(globals().items()):
    if _global_name.startswith("__"):
        continue
    if isinstance(_global_value, (dict, list, set)):
        raise RuntimeError(
            f"semantic_v2 global {_global_name} is a mutable container; "
            "frozen V2 contract data must be runtime-immutable"
        )


# ---------------------------------------------------------------------------
# Final Semantic V2 output contract — the strict structured response
# ---------------------------------------------------------------------------


class SemanticV2ParseError(ValueError):
    """The raw V2 model output is not the exact V2 JSON response shape.

    Bounded: the message names the failing shape rule, never the raw
    model content.
    """


_V2_RESPONSE_KEYS: Final[frozenset[str]] = frozenset(
    {
        "decision",
        "confidence",
        "reason_code",
        "matched_attributes",
        "conflicting_attributes",
        "missing_critical_attributes",
        "conflict_classes",
    }
)

_V2_ATTRIBUTE_KEYS: Final[frozenset[str]] = frozenset(
    {"dimension", "detail"}
)


def parse_semantic_response_v2(raw_output: str) -> dict[str, object]:
    """Parse raw V2 model output into a response dict (strict).

    The discipline mirrors the frozen V1 parser and is TIGHTER where the
    V2 contract is structured:

    * the entire trimmed output is exactly one JSON object — no prose
      before/after, no Markdown fences, no arrays;
    * the exact V2 key set: missing keys AND extra keys are rejected
      (no chain-of-thought field, no free-form hidden reasoning field,
      no prose-only semantic authority).

    Raises ``SemanticV2ParseError`` on any shape violation.
    """
    if not isinstance(raw_output, str):
        raise SemanticV2ParseError(
            "raw V2 output must be a string, "
            f"got {type(raw_output).__name__}"
        )
    trimmed = raw_output.strip()
    if not trimmed:
        raise SemanticV2ParseError("empty V2 output")
    if trimmed.startswith("```"):
        raise SemanticV2ParseError("markdown code fences are not allowed")
    if not trimmed.startswith("{"):
        raise SemanticV2ParseError(
            "V2 output must be a JSON object starting with '{'"
        )
    if not trimmed.endswith("}"):
        raise SemanticV2ParseError("V2 output must end with '}'")
    try:
        parsed = json.loads(trimmed)
    except json.JSONDecodeError:
        raise SemanticV2ParseError("invalid JSON") from None
    if not isinstance(parsed, dict):
        raise SemanticV2ParseError("V2 output must be a JSON object")
    missing = _V2_RESPONSE_KEYS - set(parsed.keys())
    if missing:
        raise SemanticV2ParseError(f"missing required keys: {sorted(missing)}")
    unknown = set(parsed.keys()) - _V2_RESPONSE_KEYS
    if unknown:
        raise SemanticV2ParseError(f"unknown keys: {sorted(unknown)}")
    return parsed


def _dec_v2_attribute_list(
    value: object, path: str
) -> tuple[SemanticAttributeV2, ...]:
    """Decode a bounded structured-attribute list (exact shape, no
    duplicates, no unknown dimension)."""
    if not isinstance(value, list):
        raise SemanticV2ParseError(f"{path} must be an array")
    out: list[SemanticAttributeV2] = []
    seen: set[tuple[str, str]] = set()
    for i, item in enumerate(value):
        item_path = f"{path}[{i}]"
        if not isinstance(item, dict):
            raise SemanticV2ParseError(
                f"{item_path} must be an object with dimension and detail"
            )
        keys = set(item.keys())
        if keys != _V2_ATTRIBUTE_KEYS:
            raise SemanticV2ParseError(
                f"{item_path} must carry exactly the keys "
                f"{sorted(_V2_ATTRIBUTE_KEYS)}"
            )
        dimension_raw = item["dimension"]
        if not isinstance(dimension_raw, str):
            raise SemanticV2ParseError(
                f"{item_path}.dimension must be a string"
            )
        try:
            dimension = SemanticAttributeDimensionV2(dimension_raw)
        except ValueError:
            raise SemanticV2ParseError(
                f"{item_path}.dimension {dimension_raw!r} is not a bounded "
                "V2 attribute dimension"
            ) from None
        detail_raw = item["detail"]
        if not isinstance(detail_raw, str):
            raise SemanticV2ParseError(f"{item_path}.detail must be a string")
        key = (dimension.value, detail_raw)
        if key in seen:
            raise SemanticV2ParseError(f"{item_path} is a duplicate entry")
        seen.add(key)
        out.append(SemanticAttributeV2(dimension=dimension, detail=detail_raw))
    return tuple(out)


def _dec_v2_dimension_list(value: object, path: str) -> tuple[SemanticAttributeDimensionV2, ...]:
    """Decode a bounded dimension list (missing critical attributes)."""
    if not isinstance(value, list):
        raise SemanticV2ParseError(f"{path} must be an array")
    out: list[SemanticAttributeDimensionV2] = []
    seen: set[str] = set()
    for i, item in enumerate(value):
        if not isinstance(item, str):
            raise SemanticV2ParseError(f"{path}[{i}] must be a string")
        try:
            dimension = SemanticAttributeDimensionV2(item)
        except ValueError:
            raise SemanticV2ParseError(
                f"{path}[{i}] {item!r} is not a bounded V2 attribute "
                "dimension"
            ) from None
        if dimension.value in seen:
            raise SemanticV2ParseError(f"{path}[{i}] is a duplicate entry")
        seen.add(dimension.value)
        out.append(dimension)
    return tuple(out)


def _dec_v2_conflict_classes(value: object, path: str) -> frozenset[ConflictClass]:
    """Decode the structured conflict-class set against the FROZEN
    ConflictClass vocabulary (unknown classes fail closed)."""
    if not isinstance(value, list):
        raise SemanticV2ParseError(f"{path} must be an array")
    out: set[ConflictClass] = set()
    for i, item in enumerate(value):
        if not isinstance(item, str):
            raise SemanticV2ParseError(f"{path}[{i}] must be a string")
        try:
            conflict = ConflictClass(item)
        except ValueError:
            raise SemanticV2ParseError(
                f"{path}[{i}] {item!r} is not a bounded ConflictClass; "
                "unknown conflict classes fail closed"
            ) from None
        if conflict in out:
            raise SemanticV2ParseError(f"{path}[{i}] is a duplicate entry")
        out.add(conflict)
    return frozenset(out)


def _validate_v2_response_coherence(
    decision: V2SemanticDecision,
    reason_code: SemanticReasonCodeV2,
    missing: tuple[SemanticAttributeDimensionV2, ...],
    conflict_classes: frozenset[ConflictClass],
) -> None:
    """The frozen decision/conflict-class coherence rules (fail closed)."""
    rule = semantic_reason_code_rule(reason_code)
    if rule.decision is not decision:
        raise ValueError(
            f"reason code {reason_code.value} contradicts decision "
            f"{decision.value} (the frozen rule serves "
            f"{rule.decision.value} only)"
        )
    if not (rule.required_conflict_classes <= conflict_classes):
        missing_classes = sorted(
            conflict.value
            for conflict in rule.required_conflict_classes
            if conflict not in conflict_classes
        )
        raise ValueError(
            f"reason code {reason_code.value} requires structured "
            f"conflict classes {missing_classes} that the response does "
            "not carry; the reason code contradicts the conflict set"
        )
    hard_count = len(conflict_classes & ALWAYS_HARD_CONFLICT_CLASSES)
    if hard_count < rule.min_hard_conflict_count:
        raise ValueError(
            f"reason code {reason_code.value} requires at least "
            f"{rule.min_hard_conflict_count} ALWAYS_HARD conflict "
            f"classes; the response carries {hard_count}"
        )
    if rule.requires_nonempty_missing_attributes and not missing:
        raise ValueError(
            f"reason code {reason_code.value} requires at least one "
            "missing critical attribute"
        )
    if rule.requires_any_conflict and not conflict_classes:
        raise ValueError(
            f"reason code {reason_code.value} (decision "
            f"{decision.value}) must be grounded in a non-empty "
            "structured conflict set"
        )
    if decision in (V2SemanticDecision.MATCH, V2SemanticDecision.UNCERTAIN):
        hard = conflict_classes & ALWAYS_HARD_CONFLICT_CLASSES
        if hard:
            raise ValueError(
                f"decision {decision.value} may not carry an ALWAYS_HARD "
                "conflict class; a hard conflict is a structured NO_MATCH "
                "and can never be overridden or hidden by the semantic "
                "output"
            )


@dataclass(frozen=True)
class SemanticMatchResponseV2:
    """The final strict structured Semantic V2 output (S2-C).

    decision / confidence / reason code are bounded enums; attributes are
    bounded structured (dimension + detail) observations; conflict
    classes are the frozen ``ConflictClass`` values. The frozen
    ``REASON_CODE_RULES`` keep the reason code internally coherent with
    the structured conflict set. No prose field exists: there is no
    chain-of-thought field and no free-form hidden-reasoning surface.

    Construction (direct or via ``validate_semantic_response_v2``) fails
    closed on unknown enums, malformed lists, and incoherent
    decision/conflict combinations.
    """

    decision: V2SemanticDecision
    confidence: V2Confidence
    reason_code: SemanticReasonCodeV2
    matched_attributes: tuple[SemanticAttributeV2, ...]
    conflicting_attributes: tuple[SemanticAttributeV2, ...]
    missing_critical_attributes: tuple[SemanticAttributeDimensionV2, ...]
    conflict_classes: frozenset[ConflictClass]

    def __post_init__(self) -> None:
        if not isinstance(self.decision, V2SemanticDecision):
            raise TypeError(
                "decision must be V2SemanticDecision, "
                f"got {type(self.decision).__name__}"
            )
        if not isinstance(self.confidence, V2Confidence):
            raise TypeError(
                "confidence must be V2Confidence, "
                f"got {type(self.confidence).__name__}"
            )
        if not isinstance(self.reason_code, SemanticReasonCodeV2):
            raise TypeError(
                "reason_code must be SemanticReasonCodeV2, "
                f"got {type(self.reason_code).__name__}"
            )
        if not isinstance(self.matched_attributes, tuple):
            raise TypeError("matched_attributes must be a tuple")
        for i, item in enumerate(self.matched_attributes):
            if not isinstance(item, SemanticAttributeV2):
                raise TypeError(
                    f"matched_attributes[{i}] must be SemanticAttributeV2, "
                    f"got {type(item).__name__}"
                )
        if not isinstance(self.conflicting_attributes, tuple):
            raise TypeError("conflicting_attributes must be a tuple")
        for i, item in enumerate(self.conflicting_attributes):
            if not isinstance(item, SemanticAttributeV2):
                raise TypeError(
                    f"conflicting_attributes[{i}] must be "
                    f"SemanticAttributeV2, got {type(item).__name__}"
                )
        if not isinstance(self.missing_critical_attributes, tuple):
            raise TypeError("missing_critical_attributes must be a tuple")
        for i, item in enumerate(self.missing_critical_attributes):
            if not isinstance(item, SemanticAttributeDimensionV2):
                raise TypeError(
                    f"missing_critical_attributes[{i}] must be "
                    "SemanticAttributeDimensionV2, "
                    f"got {type(item).__name__}"
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
        _validate_v2_response_coherence(
            self.decision,
            self.reason_code,
            self.missing_critical_attributes,
            self.conflict_classes,
        )


def validate_semantic_response_v2(
    response: dict[str, object] | SemanticMatchResponseV2,
) -> SemanticMatchResponseV2:
    """Validate (and normalize) a parsed V2 response dict into the strict
    structured ``SemanticMatchResponseV2``.

    Strict enums for decision / confidence / reason code / attribute
    dimensions / conflict classes (unknown values fail closed); exact
    shapes for the attribute lists; duplicates rejected; the frozen
    reason-code coherence rules enforced. Raises
    ``SemanticV2ParseError`` for shape violations and ``ValueError`` /
    ``TypeError`` for vocabulary / coherence violations.
    """
    if isinstance(response, SemanticMatchResponseV2):
        return response
    if not isinstance(response, dict):
        raise SemanticV2ParseError(
            "response must be the parsed V2 response mapping, "
            f"got {type(response).__name__}"
        )
    missing = _V2_RESPONSE_KEYS - set(response.keys())
    if missing:
        raise SemanticV2ParseError(
            f"missing required keys: {sorted(missing)}"
        )
    unknown = set(response.keys()) - _V2_RESPONSE_KEYS
    if unknown:
        raise SemanticV2ParseError(f"unknown keys: {sorted(unknown)}")

    decision_raw = response["decision"]
    if not isinstance(decision_raw, str):
        raise SemanticV2ParseError("decision must be a string")
    try:
        decision = V2SemanticDecision(decision_raw)
    except ValueError:
        raise SemanticV2ParseError(
            f"decision {decision_raw!r} is not a bounded V2 decision"
        ) from None

    confidence_raw = response["confidence"]
    if not isinstance(confidence_raw, str):
        raise SemanticV2ParseError("confidence must be a string")
    try:
        confidence = V2Confidence(confidence_raw)
    except ValueError:
        raise SemanticV2ParseError(
            f"confidence {confidence_raw!r} is not a bounded V2 confidence"
        ) from None

    reason_raw = response["reason_code"]
    if not isinstance(reason_raw, str):
        raise SemanticV2ParseError("reason_code must be a string")
    try:
        reason_code = SemanticReasonCodeV2(reason_raw)
    except ValueError:
        raise SemanticV2ParseError(
            f"reason_code {reason_raw!r} is not a bounded V2 reason code"
        ) from None

    matched = _dec_v2_attribute_list(
        response["matched_attributes"], "matched_attributes"
    )
    conflicting = _dec_v2_attribute_list(
        response["conflicting_attributes"], "conflicting_attributes"
    )
    missing = _dec_v2_dimension_list(
        response["missing_critical_attributes"], "missing_critical_attributes"
    )
    conflict_classes = _dec_v2_conflict_classes(
        response["conflict_classes"], "conflict_classes"
    )

    return SemanticMatchResponseV2(
        decision=decision,
        confidence=confidence,
        reason_code=reason_code,
        matched_attributes=matched,
        conflicting_attributes=conflicting,
        missing_critical_attributes=missing,
        conflict_classes=conflict_classes,
    )
