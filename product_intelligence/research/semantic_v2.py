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
  CONTEXT PROVENANCE, and the authority-side PRODUCT EVIDENCE;
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

Documented limitation (product-evidence builder): the current main-flow
deterministic extraction (3A ``ListingObservation``) contains no
deterministic attribute extraction that proves exact bounded
identity-dimension equality between the target and a listing candidate
(that infrastructure exists only in the comparable-research
specification flow). The live execution path therefore constructs the
authority-side profile with ZERO matched facts: candidates remain at most
LIMITED (usable title) or WEAK, and the frozen S2-A bar keeps them at
NEEDS_REVIEW until future evidence infrastructure safely proves facts.
No fact is ever fabricated, and no unsafe heuristic is introduced to
increase recall.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
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
    "REASON_CODE_RULES",
    "SemanticAttributeDimensionV2",
    "SemanticAttributeV2",
    "SemanticMatchCaseV2",
    "SemanticMatchResponseV2",
    "SemanticReasonCodeRuleV2",
    "SemanticReasonCodeV2",
    "SemanticV2ParseError",
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
# Final Semantic V2 input contract
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class SemanticMatchCaseV2:
    """The final, versioned, immutable Semantic V2 input (S2-C).

    Everything the V2 prompt renders, in five clearly separated sections:

    * **A. TARGET** — ``case_id``, ``target_mpn``, ``target_description``.
    * **B. CANDIDATE LISTING** — source URL, title, published MPN field,
      published SKU, brand and condition when separately observed,
      structured listing evidence already available (``candidate_specs``),
      commercial price/package context (``candidate_commercial_context`` —
      NEVER identity proof), and the frozen 3C evidence source.
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
      ``ProductEvidenceProfileV2`` (deterministic/reviewed only). The model
      may observe it and report semantic conclusions, but it can NEVER
      create or upgrade the authority-side profile: no member of the
      bounded candidate-source vocabulary is a model claim.

    Construction is fail-closed: exact types, no silent defaults (every
    field is required; absent candidate facts are explicit ``None``), the
    recorded deterministic context must be a legitimate S2-A context, the
    state must be ``DETERMINISTIC_UNCERTAIN`` (a semantic entry point —
    anything else is outside the V2 input contract), the primary signal
    and the relationship requirement must agree with the frozen tables,
    and the product-evidence profile must be state-consistent and
    supported by the recorded provenances.
    """

    # -- A. TARGET ---------------------------------------------------------
    case_id: str
    target_mpn: str
    target_description: str

    # -- B. CANDIDATE LISTING ---------------------------------------------
    candidate_source_url: str
    candidate_title: str | None
    candidate_mpn_field: str | None
    candidate_sku: str | None
    candidate_brand: str | None
    candidate_condition: str | None
    candidate_specs: str | None
    candidate_commercial_context: str | None
    candidate_evidence_source: str

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
            "target_mpn",
            "target_description",
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
        for name in (
            "candidate_title",
            "candidate_mpn_field",
            "candidate_sku",
            "candidate_brand",
            "candidate_condition",
            "candidate_specs",
            "candidate_commercial_context",
        ):
            value = getattr(self, name)
            if value is not None and not isinstance(value, str):
                raise TypeError(
                    f"{name} must be str or None, got {type(value).__name__}"
                )
        if not self.case_id:
            raise ValueError("case_id must be non-empty")
        if not self.target_mpn:
            raise ValueError(
                "target_mpn must be non-empty; a V2 semantic case always "
                "carries the requested MPN (the no-target state is "
                "unevaluable and never V2-eligible)"
            )
        if not self.candidate_source_url:
            raise ValueError("candidate_source_url must be non-empty")
        if not self.candidate_evidence_source:
            raise ValueError("candidate_evidence_source must be non-empty")
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
            "target": {
                "mpn": self.target_mpn,
                "description": self.target_description,
            },
            "candidate": {
                "source_url": self.candidate_source_url,
                "title": self.candidate_title,
                "mpn_field": self.candidate_mpn_field,
                "sku": self.candidate_sku,
                "brand": self.candidate_brand,
                "condition": self.candidate_condition,
                "specs": self.candidate_specs,
                "commercial_context": self.candidate_commercial_context,
                "evidence_source": self.candidate_evidence_source,
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


def _observation_field(value: str | None) -> str | None:
    """Absent/empty observed text is recorded as explicit ``None`` (absent),
    never as a defaulted sentinel string."""
    if value is None:
        return None
    return value or None


def _compose_commercial_context(observation: ListingObservation) -> str | None:
    """The commercial price/package observations, rendered as CONTEXT ONLY.

    These observations are NEVER identity evidence: the V2 prompt labels
    the section accordingly, and no authority derivation consumes it.
    """
    parts: list[str] = []
    if observation.price_text:
        price = observation.price_text
        if observation.currency_text:
            price = f"{price} {observation.currency_text}"
        parts.append(f"Price: {price}")
    if observation.availability_text:
        parts.append(f"Availability: {observation.availability_text}")
    if observation.seller_text:
        parts.append(f"Seller: {observation.seller_text}")
    if observation.offer_url_text:
        parts.append(f"Offer: {observation.offer_url_text}")
    if not parts:
        return None
    return " | ".join(parts)


def build_semantic_match_case_v2(
    *,
    case_id: str,
    request: ResearchRequest,
    assessment: ListingIdentityAssessment,
    context: IdentityStateAssessmentV2,
    product_evidence: ProductEvidenceProfileV2,
    context_provenances: frozenset[ContextProvenance],
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
      observation (absent facts are explicit ``None``);
    * the authority-side ``product_evidence`` and
      ``context_provenances`` are the bounded evidence inputs (built by
      ``build_v2_product_evidence_profile`` in the live path);
    * ``candidate_specs`` is ``None`` today: the main-flow deterministic
      extraction carries no structured listing evidence beyond the
      separately observed fields (the section is reserved for future
      deterministic extraction; nothing is fabricated).

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
        target_mpn=request.manufacturer_part_number,
        target_description=request.description,
        candidate_source_url=observation.source_url,
        candidate_title=_observation_field(observation.product_title),
        candidate_mpn_field=_observation_field(
            observation.manufacturer_part_number_text
        ),
        candidate_sku=_observation_field(observation.sku_text),
        candidate_brand=_observation_field(observation.brand_text),
        candidate_condition=_observation_field(observation.condition_text),
        candidate_specs=None,
        candidate_commercial_context=_compose_commercial_context(observation),
        candidate_evidence_source=assessment.candidate_evidence_source.value,
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
