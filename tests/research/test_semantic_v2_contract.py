"""Tests for the FINAL Semantic V2 contract (S2-C).

Covers ``product_intelligence.research.semantic_v2``:

* A. **Eligibility V2** — the explicit new predicate over the frozen S2-A
  derived state: VERIFIED / CONFLICT / UNEVALUABLE never eligible;
  U1 / U2 (both signals) / U3 / U4 / U5 (NM-1 and NM-2) eligible. The
  frozen V1 predicate is not consulted.
* B. **Input V2** — the exact ``SemanticMatchCaseV2`` field set, the
  immutable typed contract, no silent defaults, the context-provenance
  separation (customer relation retrieval-only), the relationship
  requirement snapshot, the deterministic state, the structured product
  evidence, and the product-evidence authority that can never originate
  from model output.
* C. **Output V2** — the exact strict structured response schema: MATCH /
  NO_MATCH / UNCERTAIN valid; unknown field rejected; missing field
  rejected; unknown enum rejected; malformed list rejected;
  conflict/reason incoherence rejected; HARD conflicts structured; the
  condition price-only distinction preserved.
* The **safe product-evidence builder** (the STRONG bar only from
  bounded grounded facts; no fabricated facts; the documented main-flow
  limitation).

Every assessment below is produced by the REAL frozen 3C chain
(``normalize_listing_observation`` + ``assess_listing_identity``); the V2
contract never re-derives identity on its own.
"""

from __future__ import annotations

import dataclasses
import json

import pytest

from product_intelligence.domain import ResearchRequest
from product_intelligence.research import (
    ALWAYS_HARD_CONFLICT_CLASSES,
    ConflictClass,
    ContextProvenance,
    ExtractionMethod,
    IdentityStateV2,
    ListingObservation,
    ProductEvidenceDimension,
    ProductEvidenceFactV2,
    ProductEvidenceProfileV2,
    ProductEvidenceQuality,
    UncertainSubstateV2,
    V2Confidence,
    V2SemanticDecision,
    assess_listing_identity,
    derive_identity_state_v2,
    is_reviewable_conflict_class,
    normalize_listing_observation,
)
from product_intelligence.research.semantic_v2 import (
    REASON_CODE_RULES,
    SemanticAttributeDimensionV2,
    SemanticAttributeV2,
    SemanticMatchCaseV2,
    SemanticMatchResponseV2,
    SemanticReasonCodeV2,
    SemanticV2ParseError,
    build_semantic_match_case_v2,
    build_v2_product_evidence_profile,
    is_v2_semantic_eligible,
    parse_semantic_response_v2,
    semantic_reason_code_rule,
    validate_semantic_response_v2,
)

REQUEST_MPN = "ABC-123"
REQUEST = ResearchRequest(REQUEST_MPN, "A test product")

NO_CTX = frozenset()
PRODUCT_CTX = frozenset({ContextProvenance.MANUFACTURER_PRODUCT_CONTEXT})
RELATION_CTX = frozenset({ContextProvenance.MANUFACTURER_RELATION_AUTHORITY})
CUSTOMER_CTX = frozenset({ContextProvenance.CUSTOMER_RETRIEVAL_RELATION})


# -- Helpers (the real frozen 3C chain) ------------------------------------


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
    normalized = normalize_listing_observation(_observation(mpn=mpn, sku=sku, title=title))
    request = ResearchRequest(manufacturer_part_number=req_mpn, description=description)
    return assess_listing_identity(request, normalized)


def _v2(mpn=None, sku=None, title="Test Product", req_mpn=REQUEST_MPN):
    return derive_identity_state_v2(_assess(mpn=mpn, sku=sku, title=title, req_mpn=req_mpn))


def _case_for(
    assessment,
    *,
    request=None,
    provenances=NO_CTX,
    facts=frozenset(),
    case_id="candidate-test-0",
) -> SemanticMatchCaseV2:
    request = request or REQUEST
    context = derive_identity_state_v2(assessment)
    profile = build_v2_product_evidence_profile(
        observation=assessment.normalized_listing.observation,
        context_provenances=provenances,
        matched_facts=facts,
    )
    return build_semantic_match_case_v2(
        case_id=case_id,
        request=request,
        assessment=assessment,
        context=context,
        product_evidence=profile,
        context_provenances=provenances,
    )


def _title_facts():
    from product_intelligence.research import CandidateProductEvidenceSource

    return frozenset(
        {
            ProductEvidenceFactV2(
                ProductEvidenceDimension.CAPACITY,
                frozenset({CandidateProductEvidenceSource.LISTING_PRODUCT_TITLE}),
            ),
            ProductEvidenceFactV2(
                ProductEvidenceDimension.INTERFACE,
                frozenset({CandidateProductEvidenceSource.LISTING_PRODUCT_TITLE}),
            ),
        }
    )


def _response_dict(
    decision: str = "MATCH",
    confidence: str = "HIGH",
    reason_code: str = "MATCH_DESCRIPTION_AND_ATTRIBUTES",
    matched=None,
    conflicting=None,
    missing=None,
    conflicts=None,
) -> dict:
    return {
        "decision": decision,
        "confidence": confidence,
        "reason_code": reason_code,
        "matched_attributes": matched
        if matched is not None
        else [{"dimension": "PRODUCT_FAMILY", "detail": "aligned family"}],
        "conflicting_attributes": conflicting
        if conflicting is not None
        else [],
        "missing_critical_attributes": missing if missing is not None else [],
        "conflict_classes": conflicts if conflicts is not None else [],
    }


# ===========================================================================
# A. Eligibility V2
# ===========================================================================


class TestV2Eligibility:
    """The explicit V2 predicate over the frozen S2-A derived state."""

    def test_deterministic_verified_is_not_eligible(self) -> None:
        assert _v2(mpn=REQUEST_MPN).state is IdentityStateV2.DETERMINISTIC_VERIFIED
        assert is_v2_semantic_eligible(_assess(mpn=REQUEST_MPN)) is False

    def test_deterministic_normalized_exact_is_not_eligible(self) -> None:
        # 2A normalized equality (case difference) is VERIFIED, not
        # eligible.
        assessment = _assess(mpn="abc-123", req_mpn="ABC-123")
        assert _v2(mpn="abc-123", req_mpn="ABC-123").state is (
            IdentityStateV2.DETERMINISTIC_VERIFIED
        )
        assert is_v2_semantic_eligible(assessment) is False

    def test_deterministic_conflict_is_not_eligible(self) -> None:
        # Outside the bounded near-miss shapes: explicit mismatch stays
        # a deterministic conflict — AI not eligible.
        assert _v2(mpn="XYZ-999").state is IdentityStateV2.DETERMINISTIC_CONFLICT
        assert is_v2_semantic_eligible(_assess(mpn="XYZ-999")) is False

    def test_unevaluable_no_target_mpn_is_not_eligible(self) -> None:
        assessment = _assess(req_mpn="", title="No target mpn")
        context = derive_identity_state_v2(assessment)
        assert context.state is IdentityStateV2.DETERMINISTIC_UNEVALUABLE
        assert is_v2_semantic_eligible(assessment) is False

    def test_unevaluable_no_candidate_evidence_is_not_eligible(self) -> None:
        assessment = _assess(title=None, mpn=None, sku=None)
        context = derive_identity_state_v2(assessment)
        assert context.state is IdentityStateV2.DETERMINISTIC_UNEVALUABLE
        assert is_v2_semantic_eligible(assessment) is False

    def test_u1_title_mpn_is_eligible(self) -> None:
        assessment = _assess(title="Has ABC-123 in the title")
        context = _v2(title="Has ABC-123 in the title")
        assert context.substate is UncertainSubstateV2.U1_TITLE_MPN
        assert is_v2_semantic_eligible(assessment) is True

    def test_u2_sku_equals_target_is_eligible(self) -> None:
        assessment = _assess(sku=REQUEST_MPN)
        context = _v2(sku=REQUEST_MPN)
        assert context.substate is UncertainSubstateV2.U2_SKU_ONLY
        assert is_v2_semantic_eligible(assessment) is True

    def test_u2_sku_not_target_is_eligible(self) -> None:
        assessment = _assess(sku="RETAIL-SKU-1")
        context = _v2(sku="RETAIL-SKU-1")
        assert context.substate is UncertainSubstateV2.U2_SKU_ONLY
        assert is_v2_semantic_eligible(assessment) is True

    def test_u3_partial_boundary_is_eligible(self) -> None:
        assessment = _assess(mpn="ABC")
        context = _v2(mpn="ABC")
        assert context.substate is UncertainSubstateV2.U3_PARTIAL_BOUNDARY
        assert is_v2_semantic_eligible(assessment) is True

    def test_u4_no_mpn_usable_title_is_eligible(self) -> None:
        assessment = _assess(title="Usable title without any MPN")
        context = _v2(title="Usable title without any MPN")
        assert context.substate is UncertainSubstateV2.U4_NO_MPN
        assert is_v2_semantic_eligible(assessment) is True

    def test_u5_nm1_truncation_is_eligible(self) -> None:
        # Motivating near-miss shape: the candidate MPN is a strict
        # prefix of the requested MPN (3C: MPN_MISMATCH; S2-A: NM-1).
        assessment = _assess(
            mpn="MTFDKCC3T8TGP-1BK1DABYY", req_mpn="MTFDKCC3T8TGP-1BK1DABYYR"
        )
        context = _v2(
            mpn="MTFDKCC3T8TGP-1BK1DABYY", req_mpn="MTFDKCC3T8TGP-1BK1DABYYR"
        )
        assert context.substate is UncertainSubstateV2.U5_NEAR_MISS_MPN
        assert is_v2_semantic_eligible(assessment) is True

    def test_u5_nm2_substitution_is_eligible(self) -> None:
        assessment = _assess(mpn="ABC-124")
        context = _v2(mpn="ABC-124")
        assert context.substate is UncertainSubstateV2.U5_NEAR_MISS_MPN
        assert is_v2_semantic_eligible(assessment) is True

    def test_the_v1_predicate_is_not_consulted(self) -> None:
        # The V2 predicate reaches states the frozen V1 predicate never
        # does (U4 / U5) and refuses states both refuse — proven by
        # behavior: the V1 predicate (imported unchanged) disagrees on
        # exactly the states S2-C adds.
        from product_intelligence.execution.semantic_integration import (
            _is_semantic_eligible as v1_eligible,
        )

        u4 = _assess(title="Usable title without any MPN")
        assert v1_eligible(u4) is False
        assert is_v2_semantic_eligible(u4) is True

        u5 = _assess(mpn="ABC-124")
        assert v1_eligible(u5) is False
        assert is_v2_semantic_eligible(u5) is True

        u1 = _assess(title="Has ABC-123 in the title")
        assert v1_eligible(u1) is True
        assert is_v2_semantic_eligible(u1) is True

    def test_non_assessment_input_fails_closed(self) -> None:
        with pytest.raises(TypeError):
            is_v2_semantic_eligible("not an assessment")  # type: ignore[arg-type]


# ===========================================================================
# B. Input V2
# ===========================================================================


class TestInputV2:
    def test_exact_field_set(self) -> None:
        names = {field.name for field in dataclasses.fields(SemanticMatchCaseV2)}
        assert names == {
            # A. TARGET
            "case_id",
            "target_mpn",
            "target_description",
            # B. CANDIDATE LISTING
            "candidate_source_url",
            "candidate_title",
            "candidate_mpn_field",
            "candidate_sku",
            "candidate_brand",
            "candidate_condition",
            "candidate_specs",
            "candidate_commercial_context",
            "candidate_evidence_source",
            # C. DETERMINISTIC IDENTITY CONTEXT
            "identity_state",
            "substate",
            "primary_relationship_signal",
            "relationship_signals",
            "normalized_requested_part_number",
            "normalized_candidate_part_number",
            "relationship_requirement",
            # D. CONTEXT PROVENANCE
            "context_provenances",
            # E. PRODUCT EVIDENCE
            "product_evidence",
        }

    def test_immutable_typed_contract(self) -> None:
        case = _case_for(_assess(title="Has ABC-123 in the title"))
        with pytest.raises(dataclasses.FrozenInstanceError):
            case.case_id = "tampered"  # type: ignore[misc]
        # Every field is exactly typed (the constructor refuses
        # strings where enums are required, lists where frozensets).
        with pytest.raises(TypeError):
            SemanticMatchCaseV2(
                **{
                    **case.__dict__,
                    "identity_state": "DETERMINISTIC_UNCERTAIN",
                }
            )
        with pytest.raises(TypeError):
            SemanticMatchCaseV2(
                **{
                    **case.__dict__,
                    "context_provenances": set(),  # type: ignore[arg-type]
                }
            )

    def test_no_silent_defaults(self) -> None:
        for field in dataclasses.fields(SemanticMatchCaseV2):
            assert field.default is dataclasses.MISSING, field.name
            assert field.default_factory is dataclasses.MISSING, field.name

    def test_missing_field_fails_closed(self) -> None:
        case = _case_for(_assess(title="Has ABC-123 in the title"))
        kwargs = dict(case.__dict__)
        del kwargs["relationship_requirement"]
        with pytest.raises(TypeError):
            SemanticMatchCaseV2(**kwargs)

    def test_context_provenance_separation(self) -> None:
        # The three bounded classes are distinct and recorded as-present;
        # the customer-retrieval class is stored as its own class (never
        # merged into, or described as, manufacturer equivalence).
        assessment = _assess(title="Has ABC-123 in the title")
        case = _case_for(assessment, provenances=CUSTOMER_CTX)
        assert case.context_provenances is CUSTOMER_CTX
        assert case.context_provenances == frozenset(
            {ContextProvenance.CUSTOMER_RETRIEVAL_RELATION}
        )
        case_both = _case_for(assessment, provenances=RELATION_CTX | CUSTOMER_CTX)
        assert case_both.context_provenances == frozenset(
            {
                ContextProvenance.MANUFACTURER_RELATION_AUTHORITY,
                ContextProvenance.CUSTOMER_RETRIEVAL_RELATION,
            }
        )
        # The encoded input keeps them as separate values.
        encoded = case_both.canonical()["context_provenance"]
        assert encoded == [
            "CUSTOMER_RETRIEVAL_RELATION",
            "MANUFACTURER_RELATION_AUTHORITY",
        ]

    def test_customer_relation_is_retrieval_only_in_the_input(self) -> None:
        # The V2 input carries no identity-authority surface for the
        # customer relation: the provenance section is the class set
        # only, and the frozen S2-A capability table (consumed by every
        # derivation) gives it RETRIEVAL_RECALL_ONLY.
        from product_intelligence.research import (
            ContextCapability,
            context_provenance_capabilities,
        )

        capabilities = context_provenance_capabilities(
            ContextProvenance.CUSTOMER_RETRIEVAL_RELATION
        )
        assert capabilities == frozenset(
            {ContextCapability.RETRIEVAL_RECALL_ONLY}
        )
        case = _case_for(
            _assess(mpn="ABC-124"), provenances=CUSTOMER_CTX
        )
        # No field of the input grants the customer relation authority:
        # the recorded requirement for U5/NM-2 is the frozen
        # reviewed-relation requirement, unchanged by the provenance.
        assert case.relationship_requirement.value == (
            "REVIEWED_RELATION_AUTHORITY_REQUIRED"
        )

    def test_relationship_requirement_present_and_frozen(self) -> None:
        # The requirement snapshot is the frozen table's value per
        # state/substate — U1 NOT_REQUIRED, U2-equals NOT_APPLICABLE,
        # U2-not-target / U3 / U5 REVIEWED_RELATION_AUTHORITY_REQUIRED,
        # U4 NOT_APPLICABLE.
        from product_intelligence.research import RelationshipRequirement

        assert (
            _case_for(_assess(title="Has ABC-123 in the title")).relationship_requirement
            is RelationshipRequirement.NOT_REQUIRED
        )
        assert (
            _case_for(_assess(sku=REQUEST_MPN)).relationship_requirement
            is RelationshipRequirement.NOT_APPLICABLE
        )
        assert (
            _case_for(_assess(sku="RETAIL-SKU-1")).relationship_requirement
            is RelationshipRequirement.REVIEWED_RELATION_AUTHORITY_REQUIRED
        )
        assert (
            _case_for(_assess(mpn="ABC")).relationship_requirement
            is RelationshipRequirement.REVIEWED_RELATION_AUTHORITY_REQUIRED
        )
        assert (
            _case_for(_assess(title="Usable title without any MPN")).relationship_requirement
            is RelationshipRequirement.NOT_APPLICABLE
        )
        assert (
            _case_for(_assess(mpn="ABC-124")).relationship_requirement
            is RelationshipRequirement.REVIEWED_RELATION_AUTHORITY_REQUIRED
        )
        # A caller-supplied requirement that disagrees with the frozen
        # table fails closed.
        assessment = _assess(title="Has ABC-123 in the title")
        context = derive_identity_state_v2(assessment)
        profile = build_v2_product_evidence_profile(
            observation=assessment.normalized_listing.observation,
            context_provenances=NO_CTX,
            matched_facts=frozenset(),
        )
        with pytest.raises(ValueError, match="relationship_requirement"):
            SemanticMatchCaseV2(
                case_id="candidate-x",
                target_mpn=REQUEST_MPN,
                target_description="A test product",
                candidate_source_url="https://example.com/product",
                candidate_title="Has ABC-123 in the title",
                candidate_mpn_field=None,
                candidate_sku=None,
                candidate_brand=None,
                candidate_condition=None,
                candidate_specs=None,
                candidate_commercial_context="Price: 100 USD | Availability: In stock",
                candidate_evidence_source="TITLE_TEXT",
                identity_state=context.state,
                substate=context.substate,
                primary_relationship_signal=context.primary_relationship_signal,
                relationship_signals=context.relationship_signals,
                normalized_requested_part_number=context.normalized_requested_part_number,
                normalized_candidate_part_number=context.normalized_candidate_part_number,
                relationship_requirement=RelationshipRequirement.REVIEWED_RELATION_AUTHORITY_REQUIRED,
                context_provenances=NO_CTX,
                product_evidence=profile,
            )

    def test_deterministic_state_present_and_exact(self) -> None:
        assessment = _assess(mpn="ABC-124")
        case = _case_for(assessment)
        context = derive_identity_state_v2(assessment)
        assert case.identity_state is IdentityStateV2.DETERMINISTIC_UNCERTAIN
        assert case.substate is context.substate
        assert case.primary_relationship_signal is context.primary_relationship_signal
        assert case.relationship_signals == context.relationship_signals
        assert (
            case.normalized_requested_part_number
            == context.normalized_requested_part_number
        )
        assert (
            case.normalized_candidate_part_number
            == context.normalized_candidate_part_number
        )
        # The builder refuses a foreign context (fail closed).
        other = derive_identity_state_v2(_assess(mpn="ABC-999"))
        with pytest.raises(ValueError, match="frozen"):
            build_semantic_match_case_v2(
                case_id="candidate-x",
                request=REQUEST,
                assessment=assessment,
                context=other,
                product_evidence=ProductEvidenceProfileV2(
                    has_usable_product_title=True, matched_facts=frozenset()
                ),
                context_provenances=NO_CTX,
            )

    def test_builder_refuses_a_foreign_request(self) -> None:
        assessment = _assess(title="Has ABC-123 in the title")
        context = derive_identity_state_v2(assessment)
        profile = build_v2_product_evidence_profile(
            observation=assessment.normalized_listing.observation,
            context_provenances=NO_CTX,
            matched_facts=frozenset(),
        )
        with pytest.raises(ValueError, match="request"):
            build_semantic_match_case_v2(
                case_id="candidate-x",
                request=ResearchRequest("OTHER-MPN", "A different request"),
                assessment=assessment,
                context=context,
                product_evidence=profile,
                context_provenances=NO_CTX,
            )

    def test_structured_product_evidence_present(self) -> None:
        assessment = _assess(title="Usable title without any MPN")
        case = _case_for(assessment)
        assert isinstance(case.product_evidence, ProductEvidenceProfileV2)
        assert case.product_evidence.has_usable_product_title is True
        # Live main-flow builder: zero matched facts (documented
        # limitation) — the evidence is structured and bounded.
        assert case.product_evidence.matched_facts == frozenset()
        encoded = case.canonical()["product_evidence"]
        assert encoded == {
            "has_usable_product_title": True,
            "matched_facts": [],
        }

    def test_the_input_admits_only_uncertain_states(self) -> None:
        # A VERIFIED / CONFLICT / UNEVALUABLE context cannot form a V2
        # input (the semantic entry point is uncertain only) — fail
        # closed at construction.
        assessment = _assess(mpn=REQUEST_MPN)  # ACCEPTED -> VERIFIED
        context = derive_identity_state_v2(assessment)
        profile = build_v2_product_evidence_profile(
            observation=assessment.normalized_listing.observation,
            context_provenances=NO_CTX,
            matched_facts=frozenset(),
        )
        from product_intelligence.research import RelationshipRequirement

        with pytest.raises(ValueError, match="semantic entry point"):
            SemanticMatchCaseV2(
                case_id="candidate-x",
                target_mpn=REQUEST_MPN,
                target_description="A test product",
                candidate_source_url="https://example.com/product",
                candidate_title="Test Product",
                candidate_mpn_field=REQUEST_MPN,
                candidate_sku=None,
                candidate_brand=None,
                candidate_condition=None,
                candidate_specs=None,
                candidate_commercial_context=None,
                candidate_evidence_source="EXPLICIT_MPN_FIELD",
                identity_state=context.state,
                substate=context.substate,
                primary_relationship_signal=context.primary_relationship_signal,
                relationship_signals=context.relationship_signals,
                normalized_requested_part_number=context.normalized_requested_part_number,
                normalized_candidate_part_number=context.normalized_candidate_part_number,
                relationship_requirement=RelationshipRequirement.NOT_APPLICABLE,
                context_provenances=NO_CTX,
                product_evidence=profile,
            )

    def test_u4_requires_a_usable_title(self) -> None:
        # A U4 case without a usable product title contradicts the state
        # (S2-A derives U4 through the frozen usable-title gate).
        assessment = _assess(title="Usable title without any MPN")
        context = derive_identity_state_v2(assessment)
        from product_intelligence.research import (
            RelationshipRequirement,
        )

        with pytest.raises(ValueError, match="usable"):
            SemanticMatchCaseV2(
                case_id="candidate-x",
                target_mpn=REQUEST_MPN,
                target_description="A test product",
                candidate_source_url="https://example.com/product",
                candidate_title="Usable title without any MPN",
                candidate_mpn_field=None,
                candidate_sku=None,
                candidate_brand=None,
                candidate_condition=None,
                candidate_specs=None,
                candidate_commercial_context=None,
                candidate_evidence_source="NONE",
                identity_state=IdentityStateV2.DETERMINISTIC_UNCERTAIN,
                substate=context.substate,
                primary_relationship_signal=context.primary_relationship_signal,
                relationship_signals=context.relationship_signals,
                normalized_requested_part_number=context.normalized_requested_part_number,
                normalized_candidate_part_number=context.normalized_candidate_part_number,
                relationship_requirement=RelationshipRequirement.NOT_APPLICABLE,
                context_provenances=NO_CTX,
                product_evidence=ProductEvidenceProfileV2(
                    has_usable_product_title=False, matched_facts=frozenset()
                ),
            )


# ===========================================================================
# B/6. Safe product-evidence builder
# ===========================================================================


class TestProductEvidenceBuilderSafety:
    def test_live_main_flow_builder_emits_no_facts(self) -> None:
        # The current main-flow deterministic extraction proves no exact
        # bounded identity-dimension equality for listing candidates:
        # the live builder emits the usable-title fact only — no
        # fabricated matched facts (the documented limitation).
        observation = _observation(title="Some product title")
        profile = build_v2_product_evidence_profile(
            observation=observation,
            context_provenances=NO_CTX,
            matched_facts=frozenset(),
        )
        assert profile.has_usable_product_title is True
        assert profile.matched_facts == frozenset()

    def test_no_usable_title_records_no_title(self) -> None:
        observation = _observation(title=None, sku="SOME-SKU")
        profile = build_v2_product_evidence_profile(
            observation=observation,
            context_provenances=NO_CTX,
            matched_facts=frozenset(),
        )
        assert profile.has_usable_product_title is False

    def test_model_output_cannot_self_promote_product_evidence_quality(self) -> None:
        # THE core S2-C safety proof: a V2 MATCH + HIGH response with
        # rich matched_attributes cannot raise the authority-side
        # ProductEvidenceQuality — the quality derives only from the
        # builder's bounded profile (here: title only -> LIMITED) and
        # the frozen S2-A bar. The model's attribute list is recorded
        # as its OWN output section, never as authority facts.
        from product_intelligence.research import (
            derive_authority_tier,
            derive_product_evidence_quality,
            SemanticEvaluationV2,
        )

        assessment = _assess(mpn="ABC-124")  # U5/NM-2
        case = _case_for(assessment)
        profile = case.product_evidence
        quality = derive_product_evidence_quality(profile, NO_CTX)
        assert quality is ProductEvidenceQuality.LIMITED

        model_response = validate_semantic_response_v2(
            _response_dict(
                decision="MATCH",
                confidence="HIGH",
                reason_code="MATCH_DESCRIPTION_AND_ATTRIBUTES",
                matched=[
                    {"dimension": "PRODUCT_FAMILY", "detail": "7500 PRO"},
                    {"dimension": "CAPACITY", "detail": "3840GB"},
                    {"dimension": "INTERFACE", "detail": "U.3"},
                ],
            )
        )
        # The model claims three aligned dimensions — but the
        # authority-side quality is STILL LIMITED (title only): the
        # claimed attributes are not grounded facts.
        evaluation = SemanticEvaluationV2.evaluated(
            model_response.decision,
            model_response.confidence,
            model_response.conflict_classes,
        )
        decision = derive_authority_tier(
            derive_identity_state_v2(assessment),
            evaluation,
            NO_CTX,
            profile,
        )
        assert decision.product_evidence_quality is ProductEvidenceQuality.LIMITED
        # ...and the frozen NM-2 ceiling + relationship requirement keep
        # the tier at NEEDS_REVIEW (no self-promotion to automatic
        # comparable).
        from product_intelligence.research import AuthorityTier

        assert decision.tier is AuthorityTier.NEEDS_REVIEW

    def test_strong_is_reachable_only_from_bounded_grounded_facts(self) -> None:
        # A deterministic caller MAY pass explicitly grounded facts; the
        # STRONG bar (frozen S2-A) then applies exactly: >= 2 facts
        # spanning >= 2 distinct hard dimensions, title-grounded, with a
        # usable title.
        from product_intelligence.research import (
            CandidateProductEvidenceSource,
            derive_product_evidence_quality,
        )

        observation = _observation(title="A 3840GB U.3 drive")
        facts = frozenset(
            {
                ProductEvidenceFactV2(
                    ProductEvidenceDimension.CAPACITY,
                    frozenset({CandidateProductEvidenceSource.LISTING_PRODUCT_TITLE}),
                ),
                ProductEvidenceFactV2(
                    ProductEvidenceDimension.INTERFACE,
                    frozenset({CandidateProductEvidenceSource.LISTING_PRODUCT_TITLE}),
                ),
            }
        )
        profile = build_v2_product_evidence_profile(
            observation=observation,
            context_provenances=NO_CTX,
            matched_facts=facts,
        )
        assert (
            derive_product_evidence_quality(profile, NO_CTX)
            is ProductEvidenceQuality.STRONG
        )

    def test_title_grounded_fact_requires_a_usable_title(self) -> None:
        from product_intelligence.research import CandidateProductEvidenceSource

        observation = _observation(title=None, sku="SOME-SKU")
        facts = frozenset(
            {
                ProductEvidenceFactV2(
                    ProductEvidenceDimension.CAPACITY,
                    frozenset({CandidateProductEvidenceSource.LISTING_PRODUCT_TITLE}),
                )
            }
        )
        with pytest.raises(ValueError, match="usable product title"):
            build_v2_product_evidence_profile(
                observation=observation,
                context_provenances=NO_CTX,
                matched_facts=facts,
            )

    def test_reviewed_grounded_fact_requires_a_grounding_provenance(self) -> None:
        from product_intelligence.research import CandidateProductEvidenceSource

        observation = _observation()
        facts = frozenset(
            {
                ProductEvidenceFactV2(
                    ProductEvidenceDimension.CAPACITY,
                    frozenset({CandidateProductEvidenceSource.REVIEWED_PRODUCT_CONTEXT}),
                )
            }
        )
        with pytest.raises(ValueError, match="reviewed product provenance"):
            build_v2_product_evidence_profile(
                observation=observation,
                context_provenances=CUSTOMER_CTX,  # grounds nothing
                matched_facts=facts,
            )
        # A reviewed grounding provenance supports the fact.
        profile = build_v2_product_evidence_profile(
            observation=observation,
            context_provenances=PRODUCT_CTX,
            matched_facts=facts,
        )
        assert profile.matched_facts == facts

    def test_the_builder_signature_accepts_no_model_output(self) -> None:
        # Architecture proof: there is no parameter for a model response
        # or its matched_attributes — the model output cannot enter the
        # authority-side builder at all.
        import inspect

        parameters = inspect.signature(build_v2_product_evidence_profile).parameters
        assert set(parameters) == {
            "observation",
            "context_provenances",
            "matched_facts",
        }
        for name, parameter in parameters.items():
            assert parameter.kind in (
                inspect.Parameter.KEYWORD_ONLY,
                inspect.Parameter.POSITIONAL_OR_KEYWORD,
            )


# ===========================================================================
# C. Output V2
# ===========================================================================


class TestOutputV2:
    def test_exact_json_schema(self) -> None:
        raw = json.dumps(_response_dict())
        parsed = parse_semantic_response_v2(raw)
        assert set(parsed) == {
            "decision",
            "confidence",
            "reason_code",
            "matched_attributes",
            "conflicting_attributes",
            "missing_critical_attributes",
            "conflict_classes",
        }

    def test_match_valid(self) -> None:
        response = validate_semantic_response_v2(
            parse_semantic_response_v2(json.dumps(_response_dict()))
        )
        assert response.decision is V2SemanticDecision.MATCH
        assert response.confidence is V2Confidence.HIGH
        assert isinstance(response, SemanticMatchResponseV2)

    def test_no_match_valid(self) -> None:
        response = validate_semantic_response_v2(
            parse_semantic_response_v2(
                json.dumps(
                    _response_dict(
                        decision="NO_MATCH",
                        reason_code="NO_MATCH_CAPACITY",
                        conflicting=[
                            {
                                "dimension": "CAPACITY",
                                "detail": "3840GB vs 1920GB",
                            }
                        ],
                        conflicts=["CAPACITY"],
                    )
                )
            )
        )
        assert response.decision is V2SemanticDecision.NO_MATCH
        assert response.conflict_classes == frozenset({ConflictClass.CAPACITY})

    def test_uncertain_valid(self) -> None:
        response = validate_semantic_response_v2(
            parse_semantic_response_v2(
                json.dumps(
                    _response_dict(
                        decision="UNCERTAIN",
                        confidence="MEDIUM",
                        reason_code="UNCERTAIN_IDENTIFIER_RELATION",
                        matched=[],
                    )
                )
            )
        )
        assert response.decision is V2SemanticDecision.UNCERTAIN

    def test_unknown_field_rejected(self) -> None:
        raw = json.dumps(_response_dict())
        parsed = json.loads(raw)
        parsed["chain_of_thought"] = "because..."
        with pytest.raises(SemanticV2ParseError, match="unknown keys"):
            parse_semantic_response_v2(json.dumps(parsed))

    def test_missing_field_rejected(self) -> None:
        parsed = _response_dict()
        del parsed["conflict_classes"]
        with pytest.raises(SemanticV2ParseError, match="missing required keys"):
            parse_semantic_response_v2(json.dumps(parsed))

    def test_unknown_decision_rejected(self) -> None:
        with pytest.raises((SemanticV2ParseError, ValueError)):
            validate_semantic_response_v2(_response_dict(decision="PERHAPS"))

    def test_unknown_confidence_rejected(self) -> None:
        with pytest.raises((SemanticV2ParseError, ValueError)):
            validate_semantic_response_v2(_response_dict(confidence="VERY_HIGH"))

    def test_unknown_reason_code_rejected(self) -> None:
        with pytest.raises(SemanticV2ParseError, match="bounded V2 reason code"):
            validate_semantic_response_v2(
                _response_dict(reason_code="exact_mpn_match")
            )

    def test_unknown_conflict_class_rejected(self) -> None:
        with pytest.raises(SemanticV2ParseError, match="ConflictClass"):
            validate_semantic_response_v2(
                _response_dict(conflicts=["NOT_A_CLASS"])
            )

    def test_unknown_attribute_dimension_rejected(self) -> None:
        with pytest.raises(SemanticV2ParseError, match="dimension"):
            validate_semantic_response_v2(
                _response_dict(
                    matched=[{"dimension": "SOMETHING_ELSE", "detail": "x"}]
                )
            )

    def test_malformed_attribute_list_rejected(self) -> None:
        with pytest.raises(SemanticV2ParseError):
            validate_semantic_response_v2(
                _response_dict(matched="not a list")
            )
        with pytest.raises(SemanticV2ParseError):
            validate_semantic_response_v2(
                _response_dict(matched=["not an object"])
            )
        with pytest.raises(SemanticV2ParseError, match="exactly the keys"):
            validate_semantic_response_v2(
                _response_dict(matched=[{"dimension": "CAPACITY"}])
            )
        with pytest.raises(SemanticV2ParseError, match="duplicate"):
            validate_semantic_response_v2(
                _response_dict(
                    matched=[
                        {"dimension": "CAPACITY", "detail": "x"},
                        {"dimension": "CAPACITY", "detail": "x"},
                    ]
                )
            )
        with pytest.raises(SemanticV2ParseError):
            validate_semantic_response_v2(
                _response_dict(missing=["CAPACITY", "CAPACITY"])
            )
        with pytest.raises(SemanticV2ParseError):
            validate_semantic_response_v2(
                _response_dict(conflicts=["CAPACITY", "CAPACITY"])
            )

    def test_malformed_json_rejected(self) -> None:
        with pytest.raises(SemanticV2ParseError):
            parse_semantic_response_v2("not json at all")
        with pytest.raises(SemanticV2ParseError):
            parse_semantic_response_v2('```json\n{}\n```')
        with pytest.raises(SemanticV2ParseError):
            parse_semantic_response_v2('{"decision": "MATCH"} and prose')
        with pytest.raises(SemanticV2ParseError):
            parse_semantic_response_v2("[]")

    def test_no_match_capacity_must_carry_the_capacity_conflict(self) -> None:
        # Reason/conflict coherence: NO_MATCH caused by CAPACITY must
        # carry ConflictClass.CAPACITY.
        with pytest.raises(ValueError, match="requires structured conflict"):
            validate_semantic_response_v2(
                _response_dict(
                    decision="NO_MATCH",
                    reason_code="NO_MATCH_CAPACITY",
                    conflicting=[],
                    conflicts=["FORM_FACTOR"],
                )
            )
        # ...and is valid when it carries it.
        response = validate_semantic_response_v2(
            _response_dict(
                decision="NO_MATCH",
                reason_code="NO_MATCH_CAPACITY",
                conflicting=[{"dimension": "CAPACITY", "detail": "3840GB vs 1920GB"}],
                conflicts=["CAPACITY"],
            )
        )
        assert ConflictClass.CAPACITY in response.conflict_classes

    def test_no_match_multiple_conflicts_requires_two_hard(self) -> None:
        with pytest.raises(ValueError, match="ALWAYS_HARD"):
            validate_semantic_response_v2(
                _response_dict(
                    decision="NO_MATCH",
                    reason_code="NO_MATCH_MULTIPLE_CONFLICTS",
                    conflicts=["CAPACITY"],
                )
            )
        validate_semantic_response_v2(
            _response_dict(
                decision="NO_MATCH",
                reason_code="NO_MATCH_MULTIPLE_CONFLICTS",
                conflicts=["CAPACITY", "FORM_FACTOR"],
            )
        )

    def test_no_match_other_requires_a_nonempty_conflict_set(self) -> None:
        with pytest.raises(ValueError, match="non-empty"):
            validate_semantic_response_v2(
                _response_dict(
                    decision="NO_MATCH",
                    reason_code="NO_MATCH_OTHER",
                    conflicts=[],
                )
            )

    def test_match_with_a_hard_conflict_is_incoherent(self) -> None:
        with pytest.raises(ValueError, match="ALWAYS_HARD"):
            validate_semantic_response_v2(
                _response_dict(
                    decision="MATCH",
                    conflicts=["CAPACITY"],
                )
            )

    def test_uncertain_with_a_hard_conflict_is_incoherent(self) -> None:
        with pytest.raises(ValueError, match="ALWAYS_HARD"):
            validate_semantic_response_v2(
                _response_dict(
                    decision="UNCERTAIN",
                    reason_code="UNCERTAIN_IDENTIFIER_RELATION",
                    conflicts=["PRODUCT_ROLE"],
                )
            )

    def test_reason_code_facing_the_wrong_decision_is_incoherent(self) -> None:
        with pytest.raises(ValueError, match="contradicts decision"):
            validate_semantic_response_v2(
                _response_dict(
                    decision="MATCH",
                    reason_code="NO_MATCH_CAPACITY",
                    conflicts=["CAPACITY"],
                )
            )

    def test_uncertain_missing_critical_requires_missing_dimensions(self) -> None:
        with pytest.raises(ValueError, match="missing critical"):
            validate_semantic_response_v2(
                _response_dict(
                    decision="UNCERTAIN",
                    reason_code="UNCERTAIN_MISSING_CRITICAL_ATTRIBUTES",
                    missing=[],
                )
            )
        response = validate_semantic_response_v2(
            _response_dict(
                decision="UNCERTAIN",
                reason_code="UNCERTAIN_MISSING_CRITICAL_ATTRIBUTES",
                missing=["CAPACITY"],
            )
        )
        assert response.missing_critical_attributes == (
            SemanticAttributeDimensionV2.CAPACITY,
        )

    def test_hard_conflict_is_structured_not_keyword(self) -> None:
        # HARD_CONFLICT determination comes from the structured
        # ConflictClass set (the frozen S2-A severity), never from
        # keyword matching on the detail text.
        response = validate_semantic_response_v2(
            _response_dict(
                decision="NO_MATCH",
                reason_code="NO_MATCH_ACCESSORY",
                conflicting=[
                    {
                        "dimension": "ACCESSORY_RELATION",
                        "detail": "drive tray not the drive itself",
                    }
                ],
                conflicts=["ACCESSORY_RELATION"],
            )
        )
        assert response.conflict_classes == frozenset(
            {ConflictClass.ACCESSORY_RELATION}
        )
        assert ConflictClass.ACCESSORY_RELATION in (
            ALWAYS_HARD_CONFLICT_CLASSES
        )

    def test_condition_is_price_dimension_only_preserved(self) -> None:
        # CONDITION stays a price dimension (never identity): a MATCH
        # with a condition conflict is coherent (no hard class), and the
        # frozen S2-A severity is unchanged.
        from product_intelligence.research import (
            is_price_dimension_only_class,
        )

        response = validate_semantic_response_v2(
            _response_dict(
                decision="MATCH",
                reason_code="MATCH_DESCRIPTION_AND_ATTRIBUTES",
                conflicting=[{"dimension": "CONDITION", "detail": "New vs Renewed"}],
                conflicts=["CONDITION"],
            )
        )
        assert response.conflict_classes == frozenset({ConflictClass.CONDITION})
        assert is_price_dimension_only_class(ConflictClass.CONDITION) is True
        assert ConflictClass.CONDITION not in ALWAYS_HARD_CONFLICT_CLASSES

    def test_brand_is_reviewable_preserved(self) -> None:
        # BRAND is REVIEWABLE (not hard) — the frozen S2-A rule the V2
        # output contract consumes.
        assert is_reviewable_conflict_class(ConflictClass.BRAND) is True
        validate_semantic_response_v2(
            _response_dict(
                decision="NO_MATCH",
                reason_code="NO_MATCH_OTHER",
                conflicting=[{"dimension": "BRAND", "detail": "OEM vs private label"}],
                conflicts=["BRAND"],
            )
        )


# ===========================================================================
# The bounded V2 reason-code vocabulary
# ===========================================================================


class TestReasonCodeVocabulary:
    def test_the_vocabulary_is_bounded_and_generic(self) -> None:
        assert len(list(SemanticReasonCodeV2)) == 17
        # No manufacturer-specific codes.
        for code in SemanticReasonCodeV2:
            assert "MICRON" not in code.value
            assert "SEAGATE" not in code.value
            assert "WD" not in code.value.split("_")

    def test_rules_cover_the_whole_vocabulary_exactly_once(self) -> None:
        assert len(REASON_CODE_RULES) == len(SemanticReasonCodeV2)
        assert {rule.code for rule in REASON_CODE_RULES} == set(
            SemanticReasonCodeV2
        )
        for code in SemanticReasonCodeV2:
            rule = semantic_reason_code_rule(code)
            assert rule.code is code

    def test_lookup_fails_closed(self) -> None:
        with pytest.raises(TypeError):
            semantic_reason_code_rule("NO_MATCH_CAPACITY")  # type: ignore[arg-type]

    def test_decision_families_are_coherent(self) -> None:
        families = {
            V2SemanticDecision.MATCH: "MATCH_",
            V2SemanticDecision.NO_MATCH: "NO_MATCH_",
            V2SemanticDecision.UNCERTAIN: "UNCERTAIN_",
        }
        for rule in REASON_CODE_RULES:
            assert rule.code.value.startswith(families[rule.decision])
            if rule.decision is V2SemanticDecision.NO_MATCH:
                assert rule.requires_any_conflict
