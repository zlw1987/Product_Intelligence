"""Tests for the Semantic Authority Contract V2 (S2-A, contract only).

Covers the frozen S2-A contract in
``product_intelligence.research.semantic_authority_v2``:

* A. identity V2 mapping over the frozen 3C assessment
* B. bounded near-miss relationship signals (NM-1 / NM-2) and the NM-2
   auto-authority ceiling
* C. distinct context provenance classes (product lead amendment 2)
* D. structured conflict taxonomy (severity sets)
* E. authority matrix completeness and precedence
* F. U4 description-match recall invariant
* G. no behavior wiring: the frozen V1 production semantic predicate /
   runtime / 3C outputs remain unchanged

Every assessment below is produced by the REAL frozen 3C chain
(``normalize_listing_observation`` + ``assess_listing_identity``); V2 never
re-derives identity on its own.
"""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

from product_intelligence.domain import ResearchRequest
from product_intelligence.domain.enums import (
    EvidenceDecision,
    IdentityMatchType,
)
from product_intelligence.research import (
    EvidenceSource,
    ExtractionMethod,
    IdentityRejectionReason,
    ListingObservation,
    assess_listing_identity,
    normalize_listing_observation,
)
from product_intelligence.research.semantic_authority_v2 import (
    ALWAYS_HARD_CONFLICT_CLASSES,
    AUTHORITY_TIER_BADGES,
    COMPATIBILITY_WORDING_VOCABULARY,
    CONTEXT_PROVENANCE_CAPABILITIES,
    DETERMINISTIC_STATE_POLICIES,
    FORBIDDEN_MARKET_EVIDENCE_HEADLINE,
    LEAD_MARKET_EVIDENCE_SUMMARY_TEMPLATE,
    LEGACY_MACHINE_VERIFIED_LINE_TEMPLATE,
    MARKET_EVIDENCE_TIERS,
    NearMissShape,
    PRICING_ELIGIBLE_SUMMARY_TEMPLATE,
    PRICING_ELIGIBLE_TIERS,
    PRICE_DIMENSION_ONLY_CONFLICT_CLASSES,
    REVIEWABLE_CONFLICT_CLASSES,
    SEMANTIC_OUTCOME_TIER_MATRIX,
    UI_ATTENTION_ORDER,
    AuthorityRuleV2,
    AuthorityTier,
    ConflictClass,
    ConflictSeverity,
    ConflictSubstateV2,
    ContextCapability,
    ContextProvenance,
    ContextQuality,
    HumanReviewStateV2,
    IdentityRelationshipSignal,
    IdentityStateAssessmentV2,
    IdentityStateV2,
    SemanticEvaluationStateV2,
    SemanticEvaluationV2,
    UncertainSubstateV2,
    UnevaluableSubstateV2,
    V2Confidence,
    V2SemanticDecision,
    VerifiedSubstateV2,
    conflict_class_severity,
    derive_authority_tier,
    derive_context_quality,
    derive_identity_state_v2,
    derive_tier_summary,
    has_relationship_authority,
    is_near_miss_substitution,
    is_near_miss_truncation,
    is_v2_semantic_entry_point,
    near_miss_shape,
)

REQUEST_MPN = "ABC-123"


# -- Helpers ----------------------------------------------------------------


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


def _v2(
    mpn: str | None = None,
    sku: str | None = None,
    title: str | None = "Test Product",
    req_mpn: str = REQUEST_MPN,
    description: str = "A test product",
) -> IdentityStateAssessmentV2:
    return derive_identity_state_v2(
        _assess(
            mpn=mpn,
            sku=sku,
            title=title,
            req_mpn=req_mpn,
            description=description,
        )
    )


def _match(confidence: V2Confidence, conflicts: frozenset[ConflictClass] = frozenset()):
    return SemanticEvaluationV2.evaluated(
        V2SemanticDecision.MATCH, confidence, conflicts
    )


NO_CTX = frozenset()
PRODUCT_CTX = frozenset({ContextProvenance.MANUFACTURER_PRODUCT_CONTEXT})
RELATION_CTX = frozenset({ContextProvenance.MANUFACTURER_RELATION_AUTHORITY})
CUSTOMER_CTX = frozenset({ContextProvenance.CUSTOMER_RETRIEVAL_RELATION})


# ===========================================================================
# A. Identity V2 mapping
# ===========================================================================


class TestV2IdentityMapping:
    """The frozen 3C assessment maps to exactly one V2 state/sub-state."""

    def test_exact_mpn_maps_to_verified_v_exact(self) -> None:
        assessment = _assess(mpn="ABC-123")
        assert assessment.decision is EvidenceDecision.ACCEPTED
        assert assessment.match_type is IdentityMatchType.EXACT

        v2 = derive_identity_state_v2(assessment)
        assert v2.state is IdentityStateV2.DETERMINISTIC_VERIFIED
        assert v2.substate is VerifiedSubstateV2.V_EXACT
        assert v2.primary_relationship_signal is IdentityRelationshipSignal.EXACT
        assert v2.is_semantic_entry_point is False
        assert is_v2_semantic_entry_point(v2) is False

    def test_normalized_exact_maps_to_verified_v_normalized_exact(self) -> None:
        assessment = _assess(mpn="abc 123")
        assert assessment.decision is EvidenceDecision.ACCEPTED
        assert assessment.match_type is IdentityMatchType.NORMALIZED_EXACT

        v2 = derive_identity_state_v2(assessment)
        assert v2.state is IdentityStateV2.DETERMINISTIC_VERIFIED
        assert v2.substate is VerifiedSubstateV2.V_NORMALIZED_EXACT
        assert v2.primary_relationship_signal is (
            IdentityRelationshipSignal.NORMALIZED_EXACT
        )
        assert v2.is_semantic_entry_point is False

    def test_title_mpn_maps_to_u1(self) -> None:
        assessment = _assess(title="Has ABC-123 in the title")
        assert assessment.decision is EvidenceDecision.REJECTED
        assert assessment.rejection_reason is (
            IdentityRejectionReason.NO_EXPLICIT_MPN_EVIDENCE
        )
        assert assessment.candidate_evidence_source is EvidenceSource.TITLE_TEXT

        v2 = derive_identity_state_v2(assessment)
        assert v2.state is IdentityStateV2.DETERMINISTIC_UNCERTAIN
        assert v2.substate is UncertainSubstateV2.U1_TITLE_MPN
        assert v2.primary_relationship_signal is (
            IdentityRelationshipSignal.TITLE_MPN_TOKEN
        )
        assert v2.is_semantic_entry_point is True

    def test_sku_only_maps_to_u2(self) -> None:
        assessment = _assess(sku="RETAIL-SKU-1")
        assert assessment.decision is EvidenceDecision.REJECTED
        assert assessment.rejection_reason is (
            IdentityRejectionReason.NO_EXPLICIT_MPN_EVIDENCE
        )
        assert assessment.candidate_evidence_source is EvidenceSource.SKU_FIELD

        v2 = derive_identity_state_v2(assessment)
        assert v2.state is IdentityStateV2.DETERMINISTIC_UNCERTAIN
        assert v2.substate is UncertainSubstateV2.U2_SKU_ONLY
        assert v2.primary_relationship_signal is (
            IdentityRelationshipSignal.SKU_NOT_TARGET
        )

    def test_sku_equal_to_target_maps_to_u2_with_sku_equals_target(self) -> None:
        v2 = _v2(sku="ABC-123")
        assert v2.substate is UncertainSubstateV2.U2_SKU_ONLY
        assert v2.primary_relationship_signal is (
            IdentityRelationshipSignal.SKU_EQUALS_TARGET
        )
        # A SKU that equals the target is still not identity authority.
        assert v2.state is IdentityStateV2.DETERMINISTIC_UNCERTAIN
        assert v2.is_semantic_entry_point is True

    def test_partial_boundary_maps_to_u3(self) -> None:
        assessment = _assess(mpn="ABC")
        assert assessment.decision is EvidenceDecision.REJECTED
        assert assessment.rejection_reason is IdentityRejectionReason.PARTIAL_MPN_ONLY
        assert assessment.match_type is IdentityMatchType.PARTIAL

        v2 = derive_identity_state_v2(assessment)
        assert v2.state is IdentityStateV2.DETERMINISTIC_UNCERTAIN
        assert v2.substate is UncertainSubstateV2.U3_PARTIAL_BOUNDARY
        assert v2.primary_relationship_signal is (
            IdentityRelationshipSignal.PARTIAL_BOUNDARY
        )

    def test_no_mpn_usable_title_maps_to_u4(self) -> None:
        assessment = _assess(title="Usable title without any MPN")
        assert assessment.decision is EvidenceDecision.REJECTED
        assert assessment.rejection_reason is (
            IdentityRejectionReason.NO_EXPLICIT_MPN_EVIDENCE
        )
        assert assessment.candidate_evidence_source is EvidenceSource.NONE

        v2 = derive_identity_state_v2(assessment)
        assert v2.state is IdentityStateV2.DETERMINISTIC_UNCERTAIN
        assert v2.substate is UncertainSubstateV2.U4_NO_MPN
        assert v2.primary_relationship_signal is IdentityRelationshipSignal.NO_RELATION
        assert v2.is_semantic_entry_point is True

    def test_empty_mpn_usable_title_maps_to_u4(self) -> None:
        assessment = _assess(mpn="mpn:", title="Usable title with empty MPN field")
        assert assessment.decision is EvidenceDecision.REJECTED
        assert assessment.rejection_reason is (
            IdentityRejectionReason.NO_EXPLICIT_MPN_EVIDENCE
        )
        assert assessment.candidate_evidence_source is EvidenceSource.EXPLICIT_MPN_FIELD

        v2 = derive_identity_state_v2(assessment)
        assert v2.state is IdentityStateV2.DETERMINISTIC_UNCERTAIN
        assert v2.substate is UncertainSubstateV2.U4_NO_MPN
        assert v2.primary_relationship_signal is (
            IdentityRelationshipSignal.EMPTY_MPN_FIELD
        )

    def test_no_mpn_no_usable_title_maps_to_unevaluable_e2(self) -> None:
        v2 = _v2(title=None)
        assert v2.state is IdentityStateV2.DETERMINISTIC_UNEVALUABLE
        assert v2.substate is UnevaluableSubstateV2.E2_NO_CANDIDATE_EVIDENCE
        assert v2.is_semantic_entry_point is False

    def test_empty_mpn_no_usable_title_maps_to_unevaluable_e2(self) -> None:
        v2 = _v2(mpn="mpn:", title=None)
        assert v2.state is IdentityStateV2.DETERMINISTIC_UNEVALUABLE
        assert v2.substate is UnevaluableSubstateV2.E2_NO_CANDIDATE_EVIDENCE
        assert v2.primary_relationship_signal is (
            IdentityRelationshipSignal.EMPTY_MPN_FIELD
        )

    def test_no_target_mpn_maps_to_unevaluable_e1(self) -> None:
        assessment = _assess(req_mpn="", description="description-only request")
        assert assessment.decision is EvidenceDecision.UNDECIDED
        assert assessment.rejection_reason is IdentityRejectionReason.NO_REQUESTED_MPN

        v2 = derive_identity_state_v2(assessment)
        assert v2.state is IdentityStateV2.DETERMINISTIC_UNEVALUABLE
        assert v2.substate is UnevaluableSubstateV2.E1_NO_TARGET_MPN
        assert v2.primary_relationship_signal is IdentityRelationshipSignal.NO_RELATION
        assert v2.is_semantic_entry_point is False

    def test_unrelated_explicit_mpn_maps_to_conflict_c1(self) -> None:
        assessment = _assess(mpn="XYZ-999")
        assert assessment.decision is EvidenceDecision.REJECTED
        assert assessment.rejection_reason is IdentityRejectionReason.MPN_MISMATCH

        v2 = derive_identity_state_v2(assessment)
        assert v2.state is IdentityStateV2.DETERMINISTIC_CONFLICT
        assert v2.substate is ConflictSubstateV2.C1_INCOMPATIBLE_EXPLICIT_MPN
        assert v2.primary_relationship_signal is IdentityRelationshipSignal.NO_RELATION
        assert v2.is_semantic_entry_point is False

    def test_frozen_v1_decisions_are_unchanged_alongside_v2(self) -> None:
        """V2 is an overlay: the frozen 3C decision/reason/source/match
        tuple is byte-identical for every mapped case."""
        cases = [
            ("ABC-123", None, "Test Product"),
            ("abc 123", None, "Test Product"),
            (None, None, "Has ABC-123 in the title"),
            (None, "RETAIL-SKU-1", "Test Product"),
            ("ABC", None, "Test Product"),
            (None, None, "Usable title without any MPN"),
            ("mpn:", None, "Usable title with empty MPN field"),
            ("XYZ-999", None, "Test Product"),
            ("ABC-1234", None, "Test Product"),
            ("ABC-124", None, "Test Product"),
        ]
        expected = [
            (EvidenceDecision.ACCEPTED, None, EvidenceSource.EXPLICIT_MPN_FIELD, IdentityMatchType.EXACT),
            (EvidenceDecision.ACCEPTED, None, EvidenceSource.EXPLICIT_MPN_FIELD, IdentityMatchType.NORMALIZED_EXACT),
            (EvidenceDecision.REJECTED, IdentityRejectionReason.NO_EXPLICIT_MPN_EVIDENCE, EvidenceSource.TITLE_TEXT, IdentityMatchType.UNKNOWN),
            (EvidenceDecision.REJECTED, IdentityRejectionReason.NO_EXPLICIT_MPN_EVIDENCE, EvidenceSource.SKU_FIELD, IdentityMatchType.UNKNOWN),
            (EvidenceDecision.REJECTED, IdentityRejectionReason.PARTIAL_MPN_ONLY, EvidenceSource.EXPLICIT_MPN_FIELD, IdentityMatchType.PARTIAL),
            (EvidenceDecision.REJECTED, IdentityRejectionReason.NO_EXPLICIT_MPN_EVIDENCE, EvidenceSource.NONE, IdentityMatchType.UNKNOWN),
            (EvidenceDecision.REJECTED, IdentityRejectionReason.NO_EXPLICIT_MPN_EVIDENCE, EvidenceSource.EXPLICIT_MPN_FIELD, IdentityMatchType.UNKNOWN),
            (EvidenceDecision.REJECTED, IdentityRejectionReason.MPN_MISMATCH, EvidenceSource.EXPLICIT_MPN_FIELD, IdentityMatchType.UNKNOWN),
            (EvidenceDecision.REJECTED, IdentityRejectionReason.MPN_MISMATCH, EvidenceSource.EXPLICIT_MPN_FIELD, IdentityMatchType.UNKNOWN),
            (EvidenceDecision.REJECTED, IdentityRejectionReason.MPN_MISMATCH, EvidenceSource.EXPLICIT_MPN_FIELD, IdentityMatchType.UNKNOWN),
        ]
        for (mpn, sku, title), want in zip(cases, expected):
            assessment = _assess(mpn=mpn, sku=sku, title=title)
            got = (
                assessment.decision,
                assessment.rejection_reason,
                assessment.candidate_evidence_source,
                assessment.match_type,
            )
            assert got == want, (mpn, sku, title)

    def test_normalized_keys_are_carried_for_audit(self) -> None:
        v2 = _v2(mpn="abc 123")
        assert v2.normalized_requested_part_number == "ABC-123"
        assert v2.normalized_candidate_part_number == "ABC-123"

        v2 = _v2(mpn="ABC-124")
        assert v2.normalized_requested_part_number == "ABC-123"
        assert v2.normalized_candidate_part_number == "ABC-124"

    def test_derivation_requires_a_real_assessment(self) -> None:
        with pytest.raises(TypeError):
            derive_identity_state_v2("not an assessment")  # type: ignore[arg-type]


# ===========================================================================
# B. Bounded near-miss relationship signals
# ===========================================================================


class TestNearMissTruncation:
    """NM-1: strict prefix/truncation on the FROZEN normalized MPN keys."""

    def test_target_longer_prefix_maps_to_u5(self) -> None:
        # "ABC-12" is a strict prefix of "ABC-123" at a mid-token position,
        # so the frozen 3C gate rejects it as MPN_MISMATCH (not PARTIAL).
        assessment = _assess(mpn="ABC-12")
        assert assessment.rejection_reason is IdentityRejectionReason.MPN_MISMATCH

        v2 = derive_identity_state_v2(assessment)
        assert v2.state is IdentityStateV2.DETERMINISTIC_UNCERTAIN
        assert v2.substate is UncertainSubstateV2.U5_NEAR_MISS_MPN
        assert v2.primary_relationship_signal is (
            IdentityRelationshipSignal.NEAR_MISS_TRUNCATION
        )
        assert v2.near_miss_substitution_active is False

    def test_candidate_longer_prefix_maps_to_u5(self) -> None:
        v2 = _v2(mpn="ABC-1234")
        assert v2.substate is UncertainSubstateV2.U5_NEAR_MISS_MPN
        assert v2.primary_relationship_signal is (
            IdentityRelationshipSignal.NEAR_MISS_TRUNCATION
        )

    def test_nm1_membership_is_never_identity_authority(self) -> None:
        for mpn in ("ABC-12", "ABC-1234"):
            v2 = _v2(mpn=mpn)
            assert v2.state is not IdentityStateV2.DETERMINISTIC_VERIFIED
            assert v2.primary_relationship_signal not in (
                IdentityRelationshipSignal.EXACT,
                IdentityRelationshipSignal.NORMALIZED_EXACT,
            )
            # Uncertain, inspectable — not verified, not hard-conflict.
            assert v2.state is IdentityStateV2.DETERMINISTIC_UNCERTAIN

    def test_frozen_3c_boundary_partial_stays_u3_not_u5(self) -> None:
        # "ABC" is a prefix of "ABC-123" ending at a preserved separator:
        # the FROZEN 3C classifier calls this PARTIAL, and V2 must map it
        # to U3 — the frozen classification is never overridden.
        v2 = _v2(mpn="ABC")
        assert v2.substate is UncertainSubstateV2.U3_PARTIAL_BOUNDARY
        assert v2.primary_relationship_signal is (
            IdentityRelationshipSignal.PARTIAL_BOUNDARY
        )
        assert not v2.has_signal(IdentityRelationshipSignal.NEAR_MISS_TRUNCATION)

    def test_non_prefix_substring_is_conflict_not_near_miss(self) -> None:
        # "BC-123" occurs inside "ABC-123" but is not a prefix: no arbitrary
        # substring matching is permitted.
        v2 = _v2(mpn="BC-123")
        assert v2.state is IdentityStateV2.DETERMINISTIC_CONFLICT
        assert v2.substate is ConflictSubstateV2.C1_INCOMPATIBLE_EXPLICIT_MPN

    def test_identical_keys_are_not_near_misses(self) -> None:
        v2 = _v2(mpn="abc 123")
        assert v2.state is IdentityStateV2.DETERMINISTIC_VERIFIED
        assert near_miss_shape("ABC-123", "ABC-123") is None
        assert is_near_miss_truncation("ABC-123", "ABC-123") is False
        assert is_near_miss_substitution("ABC-123", "ABC-123") is False


class TestNearMissSubstitution:
    """NM-2: same length, exactly one-character substitution."""

    def test_one_substitution_maps_to_u5(self) -> None:
        assessment = _assess(mpn="ABC-124")
        assert assessment.rejection_reason is IdentityRejectionReason.MPN_MISMATCH

        v2 = derive_identity_state_v2(assessment)
        assert v2.state is IdentityStateV2.DETERMINISTIC_UNCERTAIN
        assert v2.substate is UncertainSubstateV2.U5_NEAR_MISS_MPN
        assert v2.primary_relationship_signal is (
            IdentityRelationshipSignal.NEAR_MISS_SUBSTITUTION
        )
        assert v2.near_miss_substitution_active is True

    def test_two_substitutions_is_conflict(self) -> None:
        v2 = _v2(mpn="ABX-125")
        assert v2.state is IdentityStateV2.DETERMINISTIC_CONFLICT
        assert v2.substate is ConflictSubstateV2.C1_INCOMPATIBLE_EXPLICIT_MPN
        assert v2.primary_relationship_signal is IdentityRelationshipSignal.NO_RELATION

    def test_unequal_length_non_prefix_is_conflict(self) -> None:
        # Different length and no prefix relationship: outside NM-1 and
        # outside NM-2.
        v2 = _v2(mpn="XBC-1234")
        assert v2.state is IdentityStateV2.DETERMINISTIC_CONFLICT

    def test_transposition_is_conflict_not_fuzzy(self) -> None:
        # "ACB-123" vs "ABC-123": one-character move (Levenshtein 2). No
        # edit-distance matching exists in the contract.
        assert is_near_miss_substitution("ABC-123", "ACB-123") is False
        assert near_miss_shape("ABC-123", "ACB-123") is None
        v2 = _v2(mpn="ACB-123")
        assert v2.state is IdentityStateV2.DETERMINISTIC_CONFLICT

    def test_case_difference_is_normalized_exact_not_near_miss(self) -> None:
        v2 = _v2(mpn="abc-123")
        assert v2.state is IdentityStateV2.DETERMINISTIC_VERIFIED
        assert v2.substate is VerifiedSubstateV2.V_NORMALIZED_EXACT

    def test_whitespace_hyphen_difference_is_normalized_exact(self) -> None:
        v2 = _v2(mpn="ABC 123")
        assert v2.state is IdentityStateV2.DETERMINISTIC_VERIFIED
        assert v2.substate is VerifiedSubstateV2.V_NORMALIZED_EXACT

    def test_nm2_predicates_are_bounded(self) -> None:
        # NM-2 is same-length exactly-one-difference; nothing else.
        assert is_near_miss_substitution("ABC-123", "ABC-124") is True
        assert is_near_miss_substitution("ABC-123", "ABC-12X") is True
        assert is_near_miss_substitution("ABC-123", "ABX-125") is False
        assert is_near_miss_substitution("ABC-123", "ABC-12") is False
        assert is_near_miss_substitution("ABC-123", "") is False
        assert is_near_miss_substitution("", "ABC-123") is False
        assert is_near_miss_substitution("", "") is False
        # NM-1 is strict prefix in either direction.
        assert is_near_miss_truncation("ABC-123", "ABC-12") is True
        assert is_near_miss_truncation("ABC-12", "ABC-123") is True
        assert is_near_miss_truncation("ABC-123", "BC-123") is False
        assert is_near_miss_truncation("ABC-123", "ABC-123") is False
        assert is_near_miss_truncation("ABC-123", "") is False
        assert near_miss_shape("ABC-123", "ABC-12") is NearMissShape.NM1_TRUNCATION
        assert near_miss_shape("ABC-12", "ABC-123") is NearMissShape.NM1_TRUNCATION
        assert near_miss_shape("ABC-123", "ABC-124") is NearMissShape.NM2_SUBSTITUTION
        assert near_miss_shape("ABC-123", "XYZ-999") is None

    def test_nm2_is_not_identity_authority(self) -> None:
        v2 = _v2(mpn="ABC-124")
        assert v2.state is IdentityStateV2.DETERMINISTIC_UNCERTAIN
        assert v2.is_semantic_entry_point is True
        assert v2.primary_relationship_signal not in (
            IdentityRelationshipSignal.EXACT,
            IdentityRelationshipSignal.NORMALIZED_EXACT,
        )


class TestNM2AuthorityCeiling:
    """Product-lead amendment 1: the NM-2 auto-authority ceiling.

    NM-2 without reviewed relationship authority caps the maximum
    AUTOMATIC tier at NEEDS_REVIEW — even for MATCH + HIGH. The ceiling is
    contract data, not a prompt convention.
    """

    @pytest.fixture()
    def u5_nm2(self) -> IdentityStateAssessmentV2:
        v2 = _v2(mpn="ABC-124")
        assert v2.substate is UncertainSubstateV2.U5_NEAR_MISS_MPN
        assert v2.near_miss_substitution_active
        return v2

    def test_ceiling_without_any_context(self, u5_nm2) -> None:
        decision = derive_authority_tier(u5_nm2, _match(V2Confidence.HIGH), NO_CTX)
        assert decision.tier is AuthorityTier.NEEDS_REVIEW
        assert AuthorityRuleV2.CEILING_NEAR_MISS_SUBSTITUTION_WITHOUT_RELATION_AUTHORITY in decision.fired_rules

    def test_ceiling_with_manufacturer_product_context(
        self, u5_nm2
    ) -> None:
        """Reviewed product grounding is NOT reviewed relationship
        authority: the ceiling holds."""
        decision = derive_authority_tier(u5_nm2, _match(V2Confidence.HIGH), PRODUCT_CTX)
        assert decision.tier is AuthorityTier.NEEDS_REVIEW
        assert AuthorityRuleV2.CEILING_NEAR_MISS_SUBSTITUTION_WITHOUT_RELATION_AUTHORITY in decision.fired_rules

    def test_ceiling_with_customer_retrieval_relation(self, u5_nm2) -> None:
        decision = derive_authority_tier(
            u5_nm2, _match(V2Confidence.HIGH), CUSTOMER_CTX
        )
        assert decision.tier is AuthorityTier.NEEDS_REVIEW
        assert AuthorityRuleV2.CEILING_NEAR_MISS_SUBSTITUTION_WITHOUT_RELATION_AUTHORITY in decision.fired_rules

    def test_ceiling_with_customer_plus_product_context(self, u5_nm2) -> None:
        combined = frozenset({
            ContextProvenance.CUSTOMER_RETRIEVAL_RELATION,
            ContextProvenance.MANUFACTURER_PRODUCT_CONTEXT,
        })
        decision = derive_authority_tier(u5_nm2, _match(V2Confidence.HIGH), combined)
        assert decision.tier is AuthorityTier.NEEDS_REVIEW
        assert AuthorityRuleV2.CEILING_NEAR_MISS_SUBSTITUTION_WITHOUT_RELATION_AUTHORITY in decision.fired_rules

    def test_relation_authority_satisfies_the_gate(self, u5_nm2) -> None:
        """With reviewed relationship authority the matrix PERMITS the
        automatic tier: the ceiling rule must not fire."""
        decision = derive_authority_tier(u5_nm2, _match(V2Confidence.HIGH), RELATION_CTX)
        assert decision.tier is AuthorityTier.AI_ASSISTED_COMPARABLE
        assert decision.context_quality is ContextQuality.STRONG
        assert AuthorityRuleV2.CEILING_NEAR_MISS_SUBSTITUTION_WITHOUT_RELATION_AUTHORITY not in decision.fired_rules

    def test_nm2_may_remain_reviewable_even_with_match_high(
        self, u5_nm2
    ) -> None:
        """MATCH + HIGH does not auto-price NM-2 without relationship
        authority; a human may still confirm it later."""
        decision = derive_authority_tier(
            u5_nm2, _match(V2Confidence.HIGH), PRODUCT_CTX
        )
        assert decision.tier is AuthorityTier.NEEDS_REVIEW

        confirmed = derive_authority_tier(
            u5_nm2,
            _match(V2Confidence.HIGH),
            PRODUCT_CTX,
            HumanReviewStateV2.CONFIRMED,
        )
        assert confirmed.tier is AuthorityTier.HUMAN_CONFIRMED

    def test_nm2_match_medium_stays_needs_review(self, u5_nm2) -> None:
        decision = derive_authority_tier(
            u5_nm2, _match(V2Confidence.MEDIUM), RELATION_CTX
        )
        assert decision.tier is AuthorityTier.NEEDS_REVIEW

    def test_nm1_has_no_substitution_ceiling(self) -> None:
        """The ceiling is specific to the bounded NM-2 shape: a NM-1
        truncation with relationship authority may reach the automatic
        tier where the matrix permits it."""
        u5_nm1 = _v2(mpn="ABC-12")
        assert u5_nm1.near_miss_substitution_active is False
        decision = derive_authority_tier(u5_nm1, _match(V2Confidence.HIGH), RELATION_CTX)
        assert decision.tier is AuthorityTier.AI_ASSISTED_COMPARABLE
        assert (
            AuthorityRuleV2
            .CEILING_NEAR_MISS_SUBSTITUTION_WITHOUT_RELATION_AUTHORITY
            not in decision.fired_rules
        )

    def test_hard_conflict_still_supersedes_ceilinged_nm2(self, u5_nm2) -> None:
        decision = derive_authority_tier(
            u5_nm2,
            _match(V2Confidence.HIGH, frozenset({ConflictClass.CAPACITY})),
            NO_CTX,
        )
        assert decision.tier is AuthorityTier.HARD_CONFLICT
        assert AuthorityRuleV2.HARD_CONFLICT_SUPERSEDES in decision.fired_rules


# ===========================================================================
# C. Context provenance classes (Product-lead amendment 2)
# ===========================================================================


class TestContextProvenance:
    """The three provenance classes are distinct and structurally bounded."""

    def test_three_classes_are_distinct_members(self) -> None:
        members = list(ContextProvenance)
        assert len(members) == 3
        assert ContextProvenance.MANUFACTURER_PRODUCT_CONTEXT is not (
            ContextProvenance.MANUFACTURER_RELATION_AUTHORITY
        )
        assert ContextProvenance.MANUFACTURER_PRODUCT_CONTEXT is not (
            ContextProvenance.CUSTOMER_RETRIEVAL_RELATION
        )
        assert ContextProvenance.MANUFACTURER_RELATION_AUTHORITY is not (
            ContextProvenance.CUSTOMER_RETRIEVAL_RELATION
        )

    def test_capability_table_is_exactly_frozen(self) -> None:
        assert CONTEXT_PROVENANCE_CAPABILITIES == {
            ContextProvenance.MANUFACTURER_PRODUCT_CONTEXT: frozenset(
                {ContextCapability.GROUND_PRODUCT_FACTS}
            ),
            ContextProvenance.MANUFACTURER_RELATION_AUTHORITY: frozenset(
                {
                    ContextCapability.GROUND_PRODUCT_FACTS,
                    ContextCapability.ESTABLISH_IDENTIFIER_RELATIONSHIP,
                }
            ),
            ContextProvenance.CUSTOMER_RETRIEVAL_RELATION: frozenset(
                {ContextCapability.RETRIEVAL_RECALL_ONLY}
            ),
        }

    def test_customer_retrieval_is_not_manufacturer_context(self) -> None:
        customer = CONTEXT_PROVENANCE_CAPABILITIES[
            ContextProvenance.CUSTOMER_RETRIEVAL_RELATION
        ]
        assert ContextCapability.ESTABLISH_IDENTIFIER_RELATIONSHIP not in customer
        assert ContextCapability.GROUND_PRODUCT_FACTS not in customer
        assert customer == frozenset({ContextCapability.RETRIEVAL_RECALL_ONLY})

    def test_product_context_does_not_establish_the_relationship(self) -> None:
        product = CONTEXT_PROVENANCE_CAPABILITIES[
            ContextProvenance.MANUFACTURER_PRODUCT_CONTEXT
        ]
        assert ContextCapability.ESTABLISH_IDENTIFIER_RELATIONSHIP not in product
        assert has_relationship_authority(PRODUCT_CTX) is False
        assert derive_context_quality(PRODUCT_CTX) is ContextQuality.LIMITED

    def test_customer_retrieval_alone_is_weak_and_gateless(self) -> None:
        assert has_relationship_authority(CUSTOMER_CTX) is False
        assert derive_context_quality(CUSTOMER_CTX) is ContextQuality.WEAK
        assert derive_context_quality(NO_CTX) is ContextQuality.WEAK

    def test_relation_authority_establishes_the_relationship(self) -> None:
        assert has_relationship_authority(RELATION_CTX) is True
        assert derive_context_quality(RELATION_CTX) is ContextQuality.STRONG

    def test_customer_plus_product_stays_limited_and_gateless(self) -> None:
        combined = PRODUCT_CTX | CUSTOMER_CTX
        assert has_relationship_authority(combined) is False
        assert derive_context_quality(combined) is ContextQuality.LIMITED

    def test_relation_plus_customer_stays_strong(self) -> None:
        combined = RELATION_CTX | CUSTOMER_CTX
        assert has_relationship_authority(combined) is True
        assert derive_context_quality(combined) is ContextQuality.STRONG

    def test_customer_retrieval_cannot_grant_auto_authority(self) -> None:
        """Customer retrieval context can never be the STRONG that the
        MATCH + HIGH matrix row requires — so no automatic comparable
        authority is reachable through it, for any sub-state."""
        u1 = _v2(title="Has ABC-123 in the title")
        decision = derive_authority_tier(u1, _match(V2Confidence.HIGH), CUSTOMER_CTX)
        assert decision.context_quality is ContextQuality.WEAK
        assert decision.tier is AuthorityTier.NEEDS_REVIEW
        assert decision.tier is not AuthorityTier.AI_ASSISTED_COMPARABLE

    def test_manufacturer_product_context_alone_cannot_reach_auto_tier(
        self,
    ) -> None:
        u1 = _v2(title="Has ABC-123 in the title")
        decision = derive_authority_tier(u1, _match(V2Confidence.HIGH), PRODUCT_CTX)
        assert decision.context_quality is ContextQuality.LIMITED
        assert decision.tier is AuthorityTier.NEEDS_REVIEW

    def test_relation_authority_can_satisfy_the_matrix_gate(self) -> None:
        u1 = _v2(title="Has ABC-123 in the title")
        decision = derive_authority_tier(u1, _match(V2Confidence.HIGH), RELATION_CTX)
        assert decision.context_quality is ContextQuality.STRONG
        assert decision.tier is AuthorityTier.AI_ASSISTED_COMPARABLE

    def test_context_quality_is_never_ai_derived(self) -> None:
        """A LOW AI outcome cannot raise quality, and a HIGH one cannot
        lower it: quality is a pure function of the provenance classes."""
        assert (
            derive_context_quality(RELATION_CTX)
            is derive_context_quality(RELATION_CTX)
        )
        u1 = _v2(title="Has ABC-123 in the title")
        low = derive_authority_tier(
            u1,
            SemanticEvaluationV2.evaluated(V2SemanticDecision.MATCH, V2Confidence.LOW),
            RELATION_CTX,
        )
        assert low.context_quality is ContextQuality.STRONG
        assert low.tier is AuthorityTier.EXCLUDED_LOW_CONFIDENCE

    def test_provenance_input_must_be_a_frozenset(self) -> None:
        with pytest.raises(TypeError):
            derive_context_quality(set())  # type: ignore[arg-type]
        with pytest.raises(TypeError):
            has_relationship_authority(set())  # type: ignore[arg-type]


class TestCompatibilityWording:
    """COMPATIBILITY_WORDING is a bounded overlay signal, not authority."""

    def test_vocabulary_is_frozen(self) -> None:
        assert COMPATIBILITY_WORDING_VOCABULARY == frozenset(
            {"compatible", "replacement", "interchangeable", "drop-in"}
        )

    def test_wording_overlays_a_u4_state_without_changing_it(self) -> None:
        v2 = _v2(title="Generic SSD compatible storage")
        assert v2.substate is UncertainSubstateV2.U4_NO_MPN
        assert v2.primary_relationship_signal is IdentityRelationshipSignal.NO_RELATION
        assert v2.has_signal(IdentityRelationshipSignal.COMPATIBILITY_WORDING)
        assert v2.state is IdentityStateV2.DETERMINISTIC_UNCERTAIN

    def test_wording_overlays_a_verified_state_without_changing_it(self) -> None:
        v2 = _v2(mpn="ABC-123", title="ABC-123 compatible module")
        assert v2.substate is VerifiedSubstateV2.V_EXACT
        assert v2.primary_relationship_signal is IdentityRelationshipSignal.EXACT
        assert v2.has_signal(IdentityRelationshipSignal.COMPATIBILITY_WORDING)

    def test_wording_does_not_fire_inside_words(self) -> None:
        # "compatible" inside "Incompatible" and "replacement" inside
        # "replacements" are not standalone vocabulary tokens: no signal.
        v2 = _v2(mpn="XYZ-999", title="Incompatible replacements unit")
        assert v2.substate is ConflictSubstateV2.C1_INCOMPATIBLE_EXPLICIT_MPN
        assert not v2.has_signal(IdentityRelationshipSignal.COMPATIBILITY_WORDING)

    def test_wording_fires_for_standalone_hyphenated_token(self) -> None:
        v2 = _v2(mpn="XYZ-999", title="Drop-in replacement drive")
        assert v2.substate is ConflictSubstateV2.C1_INCOMPATIBLE_EXPLICIT_MPN
        assert v2.has_signal(IdentityRelationshipSignal.COMPATIBILITY_WORDING)

    def test_wording_never_changes_the_authority_tier_by_itself(self) -> None:
        plain = _v2(title="Plain title without any MPN")
        worded = _v2(title="Compatible unit without any MPN")
        assert plain.substate is worded.substate
        assert plain.state is worded.state
        decision_plain = derive_authority_tier(plain, None, RELATION_CTX)
        decision_worded = derive_authority_tier(worded, None, RELATION_CTX)
        assert decision_plain.tier is decision_worded.tier
        assert decision_plain.context_quality is decision_worded.context_quality


# ===========================================================================
# D. Structured conflict taxonomy
# ===========================================================================


class TestConflictTaxonomy:
    def test_always_hard_membership_is_exact(self) -> None:
        assert ALWAYS_HARD_CONFLICT_CLASSES == frozenset(
            {
                ConflictClass.MPN_IDENTITY,
                ConflictClass.PRODUCT_FAMILY,
                ConflictClass.GENERATION,
                ConflictClass.CAPACITY,
                ConflictClass.INTERFACE,
                ConflictClass.FORM_FACTOR,
                ConflictClass.PRODUCT_ROLE,
                ConflictClass.ACCESSORY_RELATION,
                ConflictClass.PACKAGING_QUANTITY,
                ConflictClass.BUNDLE,
            }
        )

    def test_reviewable_membership_is_exact(self) -> None:
        assert REVIEWABLE_CONFLICT_CLASSES == frozenset(
            {
                ConflictClass.REVISION_OR_SUFFIX,
                ConflictClass.BRAND,
                ConflictClass.OTHER_MATERIAL_CONFLICT,
            }
        )

    def test_price_dimension_only_membership_is_exact(self) -> None:
        assert PRICE_DIMENSION_ONLY_CONFLICT_CLASSES == frozenset(
            {ConflictClass.CONDITION}
        )

    def test_severity_sets_are_disjoint_and_cover_the_vocabulary(self) -> None:
        all_classes = set(ConflictClass)
        assert ALWAYS_HARD_CONFLICT_CLASSES | REVIEWABLE_CONFLICT_CLASSES | PRICE_DIMENSION_ONLY_CONFLICT_CLASSES == all_classes
        assert not (ALWAYS_HARD_CONFLICT_CLASSES & REVIEWABLE_CONFLICT_CLASSES)
        assert not (ALWAYS_HARD_CONFLICT_CLASSES & PRICE_DIMENSION_ONLY_CONFLICT_CLASSES)
        assert not (REVIEWABLE_CONFLICT_CLASSES & PRICE_DIMENSION_ONLY_CONFLICT_CLASSES)

    def test_brand_is_reviewable_not_hard(self) -> None:
        assert ConflictClass.BRAND in REVIEWABLE_CONFLICT_CLASSES
        assert ConflictClass.BRAND not in ALWAYS_HARD_CONFLICT_CLASSES
        assert conflict_class_severity(ConflictClass.BRAND) is ConflictSeverity.REVIEWABLE

    def test_revision_or_suffix_is_reviewable(self) -> None:
        assert conflict_class_severity(
            ConflictClass.REVISION_OR_SUFFIX
        ) is ConflictSeverity.REVIEWABLE

    def test_condition_is_price_dimension_only(self) -> None:
        assert conflict_class_severity(
            ConflictClass.CONDITION
        ) is ConflictSeverity.PRICE_DIMENSION_ONLY
        assert ConflictClass.CONDITION not in ALWAYS_HARD_CONFLICT_CLASSES
        assert ConflictClass.CONDITION not in REVIEWABLE_CONFLICT_CLASSES

    def test_drive_accessory_classes_are_hard(self) -> None:
        # Drive-tray accessory vs drive is hard via PRODUCT_ROLE /
        # ACCESSORY_RELATION.
        assert conflict_class_severity(
            ConflictClass.PRODUCT_ROLE
        ) is ConflictSeverity.ALWAYS_HARD
        assert conflict_class_severity(
            ConflictClass.ACCESSORY_RELATION
        ) is ConflictSeverity.ALWAYS_HARD

    def test_single_vs_multipack_is_hard(self) -> None:
        assert conflict_class_severity(
            ConflictClass.PACKAGING_QUANTITY
        ) is ConflictSeverity.ALWAYS_HARD

    def test_every_class_has_one_bounded_severity(self) -> None:
        for conflict in ConflictClass:
            severity = conflict_class_severity(conflict)
            assert severity in (
                ConflictSeverity.ALWAYS_HARD,
                ConflictSeverity.REVIEWABLE,
                ConflictSeverity.PRICE_DIMENSION_ONLY,
            )

    def test_severity_rejects_non_conflict_classes(self) -> None:
        with pytest.raises(TypeError):
            conflict_class_severity("CAPACITY")  # type: ignore[arg-type]


# ===========================================================================
# E. Authority matrix completeness and precedence
# ===========================================================================


class TestAuthorityMatrixCompleteness:
    def test_matrix_defines_all_27_combinations(self) -> None:
        grid = {
            (decision, confidence, quality)
            for decision in V2SemanticDecision
            for confidence in V2Confidence
            for quality in ContextQuality
        }
        assert set(SEMANTIC_OUTCOME_TIER_MATRIX) == grid
        assert len(SEMANTIC_OUTCOME_TIER_MATRIX) == 27

    def test_matrix_full_table_is_frozen(self) -> None:
        M, NM, U = V2SemanticDecision.MATCH, V2SemanticDecision.NO_MATCH, V2SemanticDecision.UNCERTAIN
        H, MD, L = V2Confidence.HIGH, V2Confidence.MEDIUM, V2Confidence.LOW
        S, LI, W = ContextQuality.STRONG, ContextQuality.LIMITED, ContextQuality.WEAK
        AI = AuthorityTier.AI_ASSISTED_COMPARABLE
        NR = AuthorityTier.NEEDS_REVIEW
        EX = AuthorityTier.EXCLUDED_LOW_CONFIDENCE
        expected = {
            (M, H, S): AI, (M, H, LI): NR, (M, H, W): NR,
            (M, MD, S): NR, (M, MD, LI): NR, (M, MD, W): NR,
            (M, L, S): EX, (M, L, LI): EX, (M, L, W): EX,
            (NM, H, S): EX, (NM, H, LI): EX, (NM, H, W): EX,
            (NM, MD, S): EX, (NM, MD, LI): EX, (NM, MD, W): EX,
            (NM, L, S): EX, (NM, L, LI): EX, (NM, L, W): EX,
            (U, H, S): NR, (U, H, LI): NR, (U, H, W): EX,
            (U, MD, S): NR, (U, MD, LI): NR, (U, MD, W): EX,
            (U, L, S): EX, (U, L, LI): EX, (U, L, W): EX,
        }
        assert SEMANTIC_OUTCOME_TIER_MATRIX == expected

    def test_state_policy_table_is_complete_and_bounded(self) -> None:
        assert set(DETERMINISTIC_STATE_POLICIES) == set(IdentityStateV2)
        assert DETERMINISTIC_STATE_POLICIES[
            IdentityStateV2.DETERMINISTIC_VERIFIED
        ].deterministic_tier is AuthorityTier.MACHINE_VERIFIED
        assert DETERMINISTIC_STATE_POLICIES[
            IdentityStateV2.DETERMINISTIC_CONFLICT
        ].deterministic_tier is AuthorityTier.HARD_CONFLICT
        assert DETERMINISTIC_STATE_POLICIES[
            IdentityStateV2.DETERMINISTIC_UNEVALUABLE
        ].deterministic_tier is AuthorityTier.EXCLUDED_LOW_CONFIDENCE
        assert DETERMINISTIC_STATE_POLICIES[
            IdentityStateV2.DETERMINISTIC_UNCERTAIN
        ].deterministic_tier is AuthorityTier.NEEDS_REVIEW

        # Only the uncertain state is a semantic entry point.
        for state, policy in DETERMINISTIC_STATE_POLICIES.items():
            assert policy.semantic_eligible is (
                state is IdentityStateV2.DETERMINISTIC_UNCERTAIN
            )
            assert policy.ai_authority_permitted is (
                state is IdentityStateV2.DETERMINISTIC_UNCERTAIN
            )
            assert policy.human_confirmation_permitted is (
                state is IdentityStateV2.DETERMINISTIC_UNCERTAIN
            )

    def test_verified_state_needs_no_ai(self) -> None:
        v = _v2(mpn="ABC-123")
        decision = derive_authority_tier(v)
        assert decision.tier is AuthorityTier.MACHINE_VERIFIED
        assert AuthorityRuleV2.STATE_POLICY_DETERMINISTIC in decision.fired_rules

        # Even a supplied MATCH + HIGH + STRONG cannot change it.
        decision = derive_authority_tier(v, _match(V2Confidence.HIGH), RELATION_CTX)
        assert decision.tier is AuthorityTier.MACHINE_VERIFIED
        assert AuthorityRuleV2.INELIGIBLE_STATE_IGNORES_SEMANTIC in decision.fired_rules

    def test_conflict_state_is_hard_and_ai_ineligible(self) -> None:
        c = _v2(mpn="XYZ-999")
        decision = derive_authority_tier(c)
        assert decision.tier is AuthorityTier.HARD_CONFLICT

        decision = derive_authority_tier(c, _match(V2Confidence.HIGH), RELATION_CTX)
        assert decision.tier is AuthorityTier.HARD_CONFLICT
        assert AuthorityRuleV2.INELIGIBLE_STATE_IGNORES_SEMANTIC in decision.fired_rules

    def test_unevaluable_state_has_no_ai_authority(self) -> None:
        e1 = _v2(req_mpn="", description="description only")
        decision = derive_authority_tier(e1)
        assert decision.tier is AuthorityTier.EXCLUDED_LOW_CONFIDENCE

        decision = derive_authority_tier(e1, _match(V2Confidence.HIGH), RELATION_CTX)
        assert decision.tier is AuthorityTier.EXCLUDED_LOW_CONFIDENCE
        assert AuthorityRuleV2.INELIGIBLE_STATE_IGNORES_SEMANTIC in decision.fired_rules

    def test_uncertain_state_not_evaluated_is_needs_review(self) -> None:
        u1 = _v2(title="Has ABC-123 in the title")
        decision = derive_authority_tier(u1)
        assert decision.tier is AuthorityTier.NEEDS_REVIEW

    def test_runtime_failure_is_semantic_unavailable_never_no_match(self) -> None:
        u1 = _v2(title="Has ABC-123 in the title")
        decision = derive_authority_tier(
            u1, SemanticEvaluationV2.runtime_failure(), RELATION_CTX
        )
        assert decision.tier is AuthorityTier.SEMANTIC_UNAVAILABLE
        assert AuthorityRuleV2.RUNTIME_FAILURE in decision.fired_rules
        assert decision.tier is not AuthorityTier.EXCLUDED_LOW_CONFIDENCE
        assert decision.tier is not AuthorityTier.HARD_CONFLICT

    def test_match_medium_is_needs_review(self) -> None:
        u1 = _v2(title="Has ABC-123 in the title")
        decision = derive_authority_tier(u1, _match(V2Confidence.MEDIUM), RELATION_CTX)
        assert decision.tier is AuthorityTier.NEEDS_REVIEW

    def test_match_high_incomplete_context_is_needs_review(self) -> None:
        u1 = _v2(title="Has ABC-123 in the title")
        for ctx in (PRODUCT_CTX, CUSTOMER_CTX, NO_CTX):
            decision = derive_authority_tier(u1, _match(V2Confidence.HIGH), ctx)
            assert decision.tier is AuthorityTier.NEEDS_REVIEW, ctx

    def test_match_high_reviewable_conflict_is_needs_review(self) -> None:
        u1 = _v2(title="Has ABC-123 in the title")
        decision = derive_authority_tier(
            u1,
            _match(V2Confidence.HIGH, frozenset({ConflictClass.REVISION_OR_SUFFIX})),
            RELATION_CTX,
        )
        assert decision.tier is AuthorityTier.NEEDS_REVIEW
        assert AuthorityRuleV2.CEILING_REVIEWABLE_CONFLICT in decision.fired_rules

    def test_condition_only_conflict_never_caps_authority(self) -> None:
        u1 = _v2(title="Has ABC-123 in the title")
        decision = derive_authority_tier(
            u1, _match(V2Confidence.HIGH, frozenset({ConflictClass.CONDITION})), RELATION_CTX
        )
        assert decision.tier is AuthorityTier.AI_ASSISTED_COMPARABLE
        assert AuthorityRuleV2.CEILING_REVIEWABLE_CONFLICT not in decision.fired_rules

    def test_hard_conflict_supersedes_match_high_strong(self) -> None:
        u1 = _v2(title="Has ABC-123 in the title")
        decision = derive_authority_tier(
            u1, _match(V2Confidence.HIGH, frozenset({ConflictClass.CAPACITY})), RELATION_CTX
        )
        assert decision.tier is AuthorityTier.HARD_CONFLICT
        assert AuthorityRuleV2.HARD_CONFLICT_SUPERSEDES in decision.fired_rules

    def test_uncertain_decision_with_actionable_context_is_needs_review(
        self,
    ) -> None:
        u1 = _v2(title="Has ABC-123 in the title")
        decision = derive_authority_tier(
            u1,
            SemanticEvaluationV2.evaluated(V2SemanticDecision.UNCERTAIN, V2Confidence.HIGH),
            PRODUCT_CTX,
        )
        assert decision.tier is AuthorityTier.NEEDS_REVIEW

    def test_uncertain_decision_without_actionable_context_is_excluded(
        self,
    ) -> None:
        u1 = _v2(title="Has ABC-123 in the title")
        decision = derive_authority_tier(
            u1,
            SemanticEvaluationV2.evaluated(V2SemanticDecision.UNCERTAIN, V2Confidence.HIGH),
            NO_CTX,
        )
        assert decision.tier is AuthorityTier.EXCLUDED_LOW_CONFIDENCE

    def test_low_confidence_is_excluded(self) -> None:
        u1 = _v2(title="Has ABC-123 in the title")
        decision = derive_authority_tier(
            u1, _match(V2Confidence.LOW), RELATION_CTX
        )
        assert decision.tier is AuthorityTier.EXCLUDED_LOW_CONFIDENCE

    def test_no_match_is_excluded(self) -> None:
        u1 = _v2(title="Has ABC-123 in the title")
        decision = derive_authority_tier(
            u1,
            SemanticEvaluationV2.evaluated(V2SemanticDecision.NO_MATCH, V2Confidence.HIGH),
            RELATION_CTX,
        )
        assert decision.tier is AuthorityTier.EXCLUDED_LOW_CONFIDENCE

    def test_precedence_hard_over_confirmed_over_ai(self) -> None:
        # 1. HARD_CONFLICT beats HUMAN_CONFIRMED.
        c = _v2(mpn="XYZ-999")
        decision = derive_authority_tier(
            c, _match(V2Confidence.HIGH), RELATION_CTX, HumanReviewStateV2.CONFIRMED
        )
        assert decision.tier is AuthorityTier.HARD_CONFLICT
        assert AuthorityRuleV2.HARD_CONFLICT_SUPERSEDES_HUMAN in decision.fired_rules

        # 2. HUMAN_CONFIRMED beats AI authority.
        u1 = _v2(title="Has ABC-123 in the title")
        decision = derive_authority_tier(
            u1, _match(V2Confidence.HIGH), RELATION_CTX, HumanReviewStateV2.CONFIRMED
        )
        assert decision.tier is AuthorityTier.HUMAN_CONFIRMED
        assert AuthorityRuleV2.HUMAN_CONFIRMED_APPLIED in decision.fired_rules

        # 3. AI authority is the floor of the three.
        decision = derive_authority_tier(u1, _match(V2Confidence.HIGH), RELATION_CTX)
        assert decision.tier is AuthorityTier.AI_ASSISTED_COMPARABLE

    def test_human_rejected_on_uncertain(self) -> None:
        u1 = _v2(title="Has ABC-123 in the title")
        decision = derive_authority_tier(u1, None, NO_CTX, HumanReviewStateV2.REJECTED)
        assert decision.tier is AuthorityTier.HUMAN_REJECTED
        assert AuthorityRuleV2.HUMAN_REJECTED_APPLIED in decision.fired_rules

    def test_human_outcome_not_applicable_on_verified(self) -> None:
        v = _v2(mpn="ABC-123")
        decision = derive_authority_tier(v, None, NO_CTX, HumanReviewStateV2.CONFIRMED)
        assert decision.tier is AuthorityTier.MACHINE_VERIFIED
        assert AuthorityRuleV2.HUMAN_OUTCOME_NOT_APPLICABLE in decision.fired_rules

    def test_total_combination_space_is_defined_and_fail_closed(self) -> None:
        """Every (state x evaluation x context x human) combination yields
        a bounded tier; ineligible states are unaffected by any semantic or
        human input."""
        representatives = {
            IdentityStateV2.DETERMINISTIC_VERIFIED: _v2(mpn="ABC-123"),
            IdentityStateV2.DETERMINISTIC_CONFLICT: _v2(mpn="XYZ-999"),
            IdentityStateV2.DETERMINISTIC_UNEVALUABLE: _v2(
                req_mpn="", description="description only"
            ),
            IdentityStateV2.DETERMINISTIC_UNCERTAIN: _v2(
                title="Has ABC-123 in the title"
            ),
        }
        evaluations = [
            SemanticEvaluationV2.not_evaluated(),
            SemanticEvaluationV2.runtime_failure(),
            SemanticEvaluationV2.evaluated(V2SemanticDecision.MATCH, V2Confidence.HIGH),
            SemanticEvaluationV2.evaluated(V2SemanticDecision.NO_MATCH, V2Confidence.MEDIUM),
            SemanticEvaluationV2.evaluated(V2SemanticDecision.UNCERTAIN, V2Confidence.LOW),
        ]
        contexts = [NO_CTX, PRODUCT_CTX, RELATION_CTX, CUSTOMER_CTX]
        humans = [None, HumanReviewStateV2.CONFIRMED, HumanReviewStateV2.REJECTED]

        for state, assessment_v2 in representatives.items():
            policy = DETERMINISTIC_STATE_POLICIES[state]
            for evaluation in evaluations:
                for context in contexts:
                    for human in humans:
                        decision = derive_authority_tier(
                            assessment_v2, evaluation, context, human
                        )
                        assert decision.tier in set(AuthorityTier)
                        assert decision.context_quality is derive_context_quality(context)
                        if not policy.semantic_eligible:
                            # Deterministic authority governs: the tier can
                            # only be the policy tier (human overlay is not
                            # applicable to these states).
                            assert decision.tier is policy.deterministic_tier

    def test_unknown_state_substate_combination_fails_closed(self) -> None:
        with pytest.raises(ValueError):
            IdentityStateAssessmentV2(
                state=IdentityStateV2.DETERMINISTIC_VERIFIED,
                substate=UncertainSubstateV2.U1_TITLE_MPN,
                relationship_signals=frozenset(
                    {IdentityRelationshipSignal.TITLE_MPN_TOKEN}
                ),
                normalized_requested_part_number="A",
                normalized_candidate_part_number="B",
            )
        with pytest.raises(ValueError):
            IdentityStateAssessmentV2(
                state=IdentityStateV2.DETERMINISTIC_CONFLICT,
                substate=UnevaluableSubstateV2.E1_NO_TARGET_MPN,
                relationship_signals=frozenset(
                    {IdentityRelationshipSignal.NO_RELATION}
                ),
                normalized_requested_part_number="",
                normalized_candidate_part_number="",
            )
        with pytest.raises(ValueError):
            IdentityStateAssessmentV2(
                state=IdentityStateV2.DETERMINISTIC_UNCERTAIN,
                substate=VerifiedSubstateV2.V_EXACT,
                relationship_signals=frozenset(
                    {IdentityRelationshipSignal.EXACT}
                ),
                normalized_requested_part_number="A",
                normalized_candidate_part_number="A",
            )

    def test_unknown_signal_combination_fails_closed(self) -> None:
        # U5 does not permit NO_RELATION.
        with pytest.raises(ValueError):
            IdentityStateAssessmentV2(
                state=IdentityStateV2.DETERMINISTIC_UNCERTAIN,
                substate=UncertainSubstateV2.U5_NEAR_MISS_MPN,
                relationship_signals=frozenset(
                    {IdentityRelationshipSignal.NO_RELATION}
                ),
                normalized_requested_part_number="A",
                normalized_candidate_part_number="B",
            )
        # U1 does not permit EXACT.
        with pytest.raises(ValueError):
            IdentityStateAssessmentV2(
                state=IdentityStateV2.DETERMINISTIC_UNCERTAIN,
                substate=UncertainSubstateV2.U1_TITLE_MPN,
                relationship_signals=frozenset(
                    {IdentityRelationshipSignal.EXACT}
                ),
                normalized_requested_part_number="A",
                normalized_candidate_part_number="A",
            )
        # Two primary signals are impossible.
        with pytest.raises(ValueError):
            IdentityStateAssessmentV2(
                state=IdentityStateV2.DETERMINISTIC_CONFLICT,
                substate=ConflictSubstateV2.C1_INCOMPATIBLE_EXPLICIT_MPN,
                relationship_signals=frozenset(
                    {
                        IdentityRelationshipSignal.NO_RELATION,
                        IdentityRelationshipSignal.NEAR_MISS_SUBSTITUTION,
                    }
                ),
                normalized_requested_part_number="A",
                normalized_candidate_part_number="B",
            )
        # A foreign sub-state enum family is a type error.
        with pytest.raises(TypeError):
            IdentityStateAssessmentV2(
                state=IdentityStateV2.DETERMINISTIC_VERIFIED,
                substate=IdentityStateV2.DETERMINISTIC_VERIFIED,  # type: ignore[arg-type]
                relationship_signals=frozenset(
                    {IdentityRelationshipSignal.EXACT}
                ),
                normalized_requested_part_number="A",
                normalized_candidate_part_number="A",
            )

    def test_semantic_evaluation_construction_fails_closed(self) -> None:
        with pytest.raises(ValueError):
            SemanticEvaluationV2(
                evaluation_state=SemanticEvaluationStateV2.NOT_EVALUATED,
                decision=V2SemanticDecision.NO_MATCH,
            )
        with pytest.raises(ValueError):
            SemanticEvaluationV2(
                evaluation_state=SemanticEvaluationStateV2.RUNTIME_FAILURE,
                decision=V2SemanticDecision.NO_MATCH,
                confidence=V2Confidence.HIGH,
            )
        with pytest.raises(ValueError):
            SemanticEvaluationV2(
                evaluation_state=SemanticEvaluationStateV2.EVALUATED,
                decision=V2SemanticDecision.MATCH,
                confidence=None,
            )
        with pytest.raises(TypeError):
            SemanticEvaluationV2(
                evaluation_state=SemanticEvaluationStateV2.EVALUATED,
                decision="MATCH",  # type: ignore[arg-type]
                confidence=V2Confidence.HIGH,
            )


# ===========================================================================
# F. U4 description-match recall invariant
# ===========================================================================


class TestU4RecallInvariant:
    """U4_NO_MPN is an intentional recall feature: a missing MPN must not
    make a usable-title listing a conflict or an excluded state."""

    def test_no_mpn_usable_title_stays_uncertain(self) -> None:
        v2 = _v2(title="Usable title without any MPN")
        assert v2.state is IdentityStateV2.DETERMINISTIC_UNCERTAIN
        assert v2.substate is UncertainSubstateV2.U4_NO_MPN
        assert v2.state is not IdentityStateV2.DETERMINISTIC_CONFLICT
        assert v2.state is not IdentityStateV2.DETERMINISTIC_UNEVALUABLE
        assert v2.is_semantic_entry_point is True

    def test_empty_mpn_usable_title_stays_uncertain(self) -> None:
        v2 = _v2(mpn="mpn:", title="Usable title with empty MPN field")
        assert v2.state is IdentityStateV2.DETERMINISTIC_UNCERTAIN
        assert v2.substate is UncertainSubstateV2.U4_NO_MPN
        assert v2.is_semantic_entry_point is True

    def test_u4_does_not_gain_deterministic_authority(self) -> None:
        v2 = _v2(title="Usable title without any MPN")
        decision = derive_authority_tier(v2)
        # Uncertain is NEEDS_REVIEW by default — never machine-verified.
        assert decision.tier is AuthorityTier.NEEDS_REVIEW
        assert decision.tier is not AuthorityTier.MACHINE_VERIFIED

    def test_u4_weak_evidence_stays_distinguishable(self) -> None:
        """Eligibility does not mean authority: a weak U4 outcome is still
        excluded through the frozen context-quality/confidence gates."""
        v2 = _v2(title="Usable title without any MPN")
        decision = derive_authority_tier(v2, _match(V2Confidence.LOW), RELATION_CTX)
        assert decision.tier is AuthorityTier.EXCLUDED_LOW_CONFIDENCE
        decision = derive_authority_tier(v2, _match(V2Confidence.HIGH), NO_CTX)
        assert decision.tier is AuthorityTier.NEEDS_REVIEW

    def test_u4_v1_runtime_eligibility_is_unchanged(self) -> None:
        """S2-A wires nothing: the CURRENT production semantic gate does
        not call the AI on U4 (source NONE) assessments."""
        from product_intelligence.execution.semantic_integration import (
            _is_semantic_eligible,
        )

        assessment = _assess(title="Usable title without any MPN")
        assert assessment.candidate_evidence_source is EvidenceSource.NONE
        assert _is_semantic_eligible(assessment) is False


# ===========================================================================
# G. UI display vocabulary (frozen for the future V2 UI)
# ===========================================================================


class TestUiVocabularyContract:
    def test_badge_concepts_are_frozen(self) -> None:
        assert AUTHORITY_TIER_BADGES == {
            AuthorityTier.MACHINE_VERIFIED: "Machine Verified",
            AuthorityTier.AI_ASSISTED_COMPARABLE: "AI-Assisted Comparable — not machine verified",
            AuthorityTier.NEEDS_REVIEW: "Needs Review — not verified",
            AuthorityTier.HUMAN_CONFIRMED: "Human Confirmed",
            AuthorityTier.HUMAN_REJECTED: "Human Rejected",
            AuthorityTier.HARD_CONFLICT: "Hard Conflict — excluded",
            AuthorityTier.EXCLUDED_LOW_CONFIDENCE: "Low Confidence",
            AuthorityTier.SEMANTIC_UNAVAILABLE: "AI Evidence Unavailable",
        }

    def test_attention_order_is_frozen(self) -> None:
        assert UI_ATTENTION_ORDER == (
            AuthorityTier.NEEDS_REVIEW,
            AuthorityTier.AI_ASSISTED_COMPARABLE,
            AuthorityTier.HUMAN_CONFIRMED,
            AuthorityTier.MACHINE_VERIFIED,
            AuthorityTier.HUMAN_REJECTED,
            AuthorityTier.HARD_CONFLICT,
            AuthorityTier.EXCLUDED_LOW_CONFIDENCE,
            AuthorityTier.SEMANTIC_UNAVAILABLE,
        )
        # Ordering means ATTENTION, not authority: it is a permutation of
        # the whole tier vocabulary with review candidates first.
        assert frozenset(UI_ATTENTION_ORDER) == set(AuthorityTier)
        assert UI_ATTENTION_ORDER[0] is AuthorityTier.NEEDS_REVIEW
        assert UI_ATTENTION_ORDER[1] is AuthorityTier.AI_ASSISTED_COMPARABLE
        assert set(UI_ATTENTION_ORDER[2:4]) == {
            AuthorityTier.HUMAN_CONFIRMED,
            AuthorityTier.MACHINE_VERIFIED,
        }

    def test_market_evidence_summary_wording_is_frozen(self) -> None:
        assert LEAD_MARKET_EVIDENCE_SUMMARY_TEMPLATE == (
            "Market evidence found: {count} listings"
        )
        # The misleading headline must not be the market-evidence wording.
        assert FORBIDDEN_MARKET_EVIDENCE_HEADLINE == "Comparable evidence"
        assert FORBIDDEN_MARKET_EVIDENCE_HEADLINE not in (
            LEAD_MARKET_EVIDENCE_SUMMARY_TEMPLATE
        )

    def test_pricing_eligible_summary_wording_is_frozen(self) -> None:
        assert PRICING_ELIGIBLE_SUMMARY_TEMPLATE == (
            "Pricing-eligible comparable listings: {count}"
        )

    def test_legacy_machine_line_may_remain(self) -> None:
        assert LEGACY_MACHINE_VERIFIED_LINE_TEMPLATE == (
            "{count} comparable NEW listings (machine-verified)"
        )

    def test_tier_count_sets_are_frozen(self) -> None:
        assert MARKET_EVIDENCE_TIERS == frozenset(
            {
                AuthorityTier.MACHINE_VERIFIED,
                AuthorityTier.AI_ASSISTED_COMPARABLE,
                AuthorityTier.HUMAN_CONFIRMED,
                AuthorityTier.NEEDS_REVIEW,
            }
        )
        assert PRICING_ELIGIBLE_TIERS == frozenset(
            {
                AuthorityTier.MACHINE_VERIFIED,
                AuthorityTier.AI_ASSISTED_COMPARABLE,
                AuthorityTier.HUMAN_CONFIRMED,
            }
        )
        assert PRICING_ELIGIBLE_TIERS < MARKET_EVIDENCE_TIERS
        assert MARKET_EVIDENCE_TIERS == PRICING_ELIGIBLE_TIERS | {
            AuthorityTier.NEEDS_REVIEW
        }

    def test_summary_counts_amendment_example(self) -> None:
        tiers = (
            [AuthorityTier.MACHINE_VERIFIED] * 2
            + [AuthorityTier.AI_ASSISTED_COMPARABLE] * 3
            + [AuthorityTier.HUMAN_CONFIRMED] * 1
            + [AuthorityTier.NEEDS_REVIEW] * 1
        )
        summary = derive_tier_summary(tiers)
        assert summary.market_evidence_count == 7
        assert summary.pricing_eligible_count == 6
        assert summary.needs_review_count == 1
        assert summary.market_evidence_headline == "Market evidence found: 7 listings"
        assert summary.pricing_eligible_headline == (
            "Pricing-eligible comparable listings: 6"
        )
        assert (AuthorityTier.NEEDS_REVIEW, 1) in summary.per_tier_counts
        assert (AuthorityTier.MACHINE_VERIFIED, 2) in summary.per_tier_counts

    def test_needs_review_counts_market_but_never_pricing_eligible(self) -> None:
        summary = derive_tier_summary([AuthorityTier.NEEDS_REVIEW])
        assert summary.market_evidence_count == 1
        assert summary.pricing_eligible_count == 0

    def test_excluded_tiers_are_not_market_evidence(self) -> None:
        summary = derive_tier_summary(
            [
                AuthorityTier.HARD_CONFLICT,
                AuthorityTier.EXCLUDED_LOW_CONFIDENCE,
                AuthorityTier.SEMANTIC_UNAVAILABLE,
                AuthorityTier.HUMAN_REJECTED,
            ]
        )
        assert summary.market_evidence_count == 0
        assert summary.pricing_eligible_count == 0
        assert summary.needs_review_count == 0

    def test_tier_summary_construction_fails_closed(self) -> None:
        from product_intelligence.research.semantic_authority_v2 import (
            TierSummaryV2,
        )

        with pytest.raises(ValueError):
            TierSummaryV2(
                market_evidence_count=1,
                pricing_eligible_count=0,
                needs_review_count=1,
                per_tier_counts=frozenset(
                    {
                        (AuthorityTier.NEEDS_REVIEW, 1),
                        (AuthorityTier.NEEDS_REVIEW, 0),
                    }
                ),
            )
        with pytest.raises(TypeError):
            TierSummaryV2(
                market_evidence_count="1",  # type: ignore[arg-type]
                pricing_eligible_count=0,
                needs_review_count=0,
                per_tier_counts=frozenset(),
            )
        with pytest.raises(TypeError):
            derive_tier_summary(["MACHINE_VERIFIED"])  # type: ignore[arg-type]


# ===========================================================================
# No behavior wiring (production V1 remains unchanged)
# ===========================================================================


class TestNoBehaviorWiring:
    """S2-A is contract-only: no production layer may import the V2
    module, and the frozen V1 predicates / runtime / 3C outputs remain
    exactly what they were at the starting SHA."""

    REPO_ROOT = Path(__file__).resolve().parents[2]
    PACKAGE_ROOT = REPO_ROOT / "product_intelligence"
    V2_MODULE = "product_intelligence.research.semantic_authority_v2"

    def _python_files(self, root: Path) -> list[Path]:
        return sorted(root.rglob("*.py"))

    def _imported_modules(self, path: Path) -> set[str]:
        modules: set[str] = set()
        for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
            if isinstance(node, ast.Import):
                modules.update(alias.name for alias in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module and not node.level:
                modules.add(node.module)
        return modules

    @pytest.mark.parametrize(
        "layer",
        ["execution", "semantic", "runs", "web", "providers"],
    )
    def test_no_production_layer_imports_the_v2_module(self, layer: str) -> None:
        root = self.PACKAGE_ROOT / layer
        assert root.is_dir()
        for path in self._python_files(root):
            imported = self._imported_modules(path)
            offending = {
                module
                for module in imported
                if module == self.V2_MODULE or module.startswith(self.V2_MODULE + ".")
            }
            assert not offending, f"{path} imports the S2-A contract module"
            # Lexical as well: the module name must not appear at all.
            assert "semantic_authority_v2" not in path.read_text(
                encoding="utf-8"
            ), f"{path} references the S2-A contract module"

    def test_research_core_does_not_call_the_v2_module(self) -> None:
        """Inside research/, only the package __init__ (public export) and
        the contract module itself may reference V2. No frozen 3C/4A/2A
        path calls it."""
        for path in self._python_files(self.PACKAGE_ROOT / "research"):
            if path.name in ("__init__.py", "semantic_authority_v2.py"):
                continue
            source = path.read_text(encoding="utf-8")
            assert "semantic_authority_v2" not in source, (
                f"{path.name} references the S2-A contract module; the "
                "frozen research pipeline must not call it"
            )

    def test_v1_semantic_eligibility_truth_table_is_unchanged(self) -> None:
        from product_intelligence.execution.semantic_integration import (
            _has_usable_evidence,
            _is_semantic_eligible,
        )

        frozen_truth = {
            # (mpn, sku, title, req_mpn) -> eligible
            ("ABC-123", None, "Test Product"): False,          # ACCEPTED
            (None, None, "Has ABC-123 in the title"): True,    # TITLE_TEXT
            (None, "RETAIL-SKU-1", "Test Product"): True,      # SKU_FIELD
            ("ABC", None, "Test Product"): True,               # PARTIAL
            (None, None, "Usable title without any MPN"): False,  # NONE
            ("XYZ-999", None, "Test Product"): False,          # MPN_MISMATCH
        }
        for (mpn, sku, title), expected in frozen_truth.items():
            assessment = _assess(mpn=mpn, sku=sku, title=title)
            assert _is_semantic_eligible(assessment) is expected, (mpn, sku, title)

        undecided = _assess(req_mpn="", description="description only")
        assert _is_semantic_eligible(undecided) is False

        # The usable-evidence gate is still title presence.
        assert _has_usable_evidence(_assess(title="Any title")) is True
        assert _has_usable_evidence(_assess(title=None)) is False

    def test_v1_human_review_eligibility_is_unchanged(self) -> None:
        from product_intelligence.research.matching import (
            is_human_review_eligible_assessment,
        )

        assert is_human_review_eligible_assessment(
            _assess(mpn="ABC-123")
        ) is False
        assert is_human_review_eligible_assessment(
            _assess(title="Has ABC-123 in the title")
        ) is True
        assert is_human_review_eligible_assessment(
            _assess(sku="RETAIL-SKU-1")
        ) is True
        assert is_human_review_eligible_assessment(
            _assess(mpn="ABC")
        ) is True
        assert is_human_review_eligible_assessment(
            _assess(mpn="XYZ-999")
        ) is False
        assert is_human_review_eligible_assessment(
            _assess(title="Usable title without any MPN")
        ) is False

    def test_semantic_runtime_route_is_unchanged(self) -> None:
        from product_intelligence.semantic import contract, runtime

        assert contract.SEMANTIC_PROMPT_VERSION == "1.1"
        assert runtime.PRIMARY_PROVIDER == "amax"
        assert runtime.PRIMARY_MODEL == "qwen3.8-27b"
        assert runtime.FALLBACK_PROVIDER == "vllm-262k"
        assert runtime.FALLBACK_MODEL == "Qwen3.6-27B-262K"
        assert type(runtime.SEMANTIC_TEMPERATURE) is float
        assert runtime.SEMANTIC_TEMPERATURE == 0.0
        assert runtime.SEMANTIC_MAX_TOKENS == 32768

    def test_v2_module_is_importable_from_the_research_package(self) -> None:
        import product_intelligence.research as research

        assert "derive_identity_state_v2" in research.__all__
        assert "derive_authority_tier" in research.__all__
        assert "IdentityStateV2" in research.__all__
        assert research.derive_identity_state_v2 is derive_identity_state_v2
