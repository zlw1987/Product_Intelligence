"""Tests for the Semantic Authority Contract V2 (S2-A, contract only, as
corrected by S2-A-FU1).

Covers the frozen S2-A/S2-A-FU1 contract in
``product_intelligence.research.semantic_authority_v2``:

* A. identity V2 mapping over the frozen 3C assessment
* B. bounded near-miss relationship signals (NM-1 / NM-2) and the NM-2
   auto-authority ceiling
* C. distinct context provenance classes (product lead amendment 2)
* D. structured conflict taxonomy (severity sets)
* E. authority matrix completeness and precedence
* F. U4 description-match recall invariant
* F2. orthogonal authority prerequisites (S2-A-FU1): bounded product
   evidence quality (dimension A) + state-specific identifier-relationship
   authority (dimension B); U4 auto-authority without
   MANUFACTURER_RELATION_AUTHORITY; NM-2 ceiling with strong product
   evidence
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
    CandidateProductEvidenceSource,
    ProductEvidenceDimension,
    ProductEvidenceFactV2,
    ProductEvidenceProfileV2,
    ProductEvidenceQuality,
    RelationshipAuthority,
    REVIEWABLE_CONFLICT_CLASSES,
    SEMANTIC_OUTCOME_TIER_MATRIX,
    UI_ATTENTION_ORDER,
    STRONG_PRODUCT_EVIDENCE_MIN_MATCHED_DIMENSIONS,
    STRONG_PRODUCT_EVIDENCE_MIN_MATCHED_FACTS,
    AuthorityRuleV2,
    AuthorityTier,
    ConflictClass,
    ConflictSeverity,
    ConflictSubstateV2,
    ContextCapability,
    ContextProvenance,
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
    authority_tier_badge,
    conflict_class_severity,
    context_provenance_capabilities,
    derive_authority_tier,
    derive_identity_state_v2,
    derive_product_evidence_quality,
    derive_relationship_authority,
    derive_tier_summary,
    deterministic_state_policy,
    has_relationship_authority,
    is_near_miss_substitution,
    is_near_miss_truncation,
    is_v2_semantic_entry_point,
    near_miss_shape,
    semantic_outcome_tier,
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

TITLE_SOURCES = frozenset({CandidateProductEvidenceSource.LISTING_PRODUCT_TITLE})
REVIEWED_SOURCES = frozenset(
    {CandidateProductEvidenceSource.REVIEWED_PRODUCT_CONTEXT}
)


def _strong_profile(
    sources: frozenset[CandidateProductEvidenceSource] = TITLE_SOURCES,
) -> ProductEvidenceProfileV2:
    """A bounded STRONG product-evidence profile (S2-A-FU1): a usable
    product title plus two matched-attribute facts on two distinct hard
    product dimensions, each grounded in bounded candidate-side sources
    (never model claims)."""
    return ProductEvidenceProfileV2(
        has_usable_product_title=True,
        matched_facts=frozenset(
            {
                ProductEvidenceFactV2(
                    ProductEvidenceDimension.CAPACITY, sources
                ),
                ProductEvidenceFactV2(
                    ProductEvidenceDimension.INTERFACE, sources
                ),
            }
        ),
    )


def _limited_title_profile() -> ProductEvidenceProfileV2:
    """Incomplete product evidence: a usable title but no bounded
    matched-attribute corroboration (the S2-A-FU1 evidence bar is not
    met by a title alone)."""
    return ProductEvidenceProfileV2(
        has_usable_product_title=True, matched_facts=frozenset()
    )


def _no_title_no_facts_profile() -> ProductEvidenceProfileV2:
    return ProductEvidenceProfileV2(
        has_usable_product_title=False, matched_facts=frozenset()
    )


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
        # S2-A-FU1: even with STRONG product evidence (excellent
        # description/product alignment) the NM-2 ceiling holds without
        # reviewed relationship authority.
        decision = derive_authority_tier(
            u5_nm2, _match(V2Confidence.HIGH), NO_CTX, _strong_profile()
        )
        assert decision.tier is AuthorityTier.NEEDS_REVIEW
        assert decision.product_evidence_quality is ProductEvidenceQuality.STRONG
        assert decision.relationship_authority is RelationshipAuthority.NOT_ESTABLISHED
        assert AuthorityRuleV2.CEILING_NEAR_MISS_SUBSTITUTION_WITHOUT_RELATION_AUTHORITY in decision.fired_rules

    def test_ceiling_with_manufacturer_product_context(
        self, u5_nm2
    ) -> None:
        """Reviewed product grounding is NOT reviewed relationship
        authority: the ceiling holds even with STRONG product evidence
        grounded in that reviewed product context."""
        decision = derive_authority_tier(
            u5_nm2,
            _match(V2Confidence.HIGH),
            PRODUCT_CTX,
            _strong_profile(REVIEWED_SOURCES),
        )
        assert decision.tier is AuthorityTier.NEEDS_REVIEW
        assert decision.product_evidence_quality is ProductEvidenceQuality.STRONG
        assert AuthorityRuleV2.CEILING_NEAR_MISS_SUBSTITUTION_WITHOUT_RELATION_AUTHORITY in decision.fired_rules

    def test_ceiling_with_customer_retrieval_relation(self, u5_nm2) -> None:
        """CUSTOMER_RETRIEVAL_RELATION confers zero relationship
        authority: the ceiling holds even with STRONG title-grounded
        product evidence."""
        decision = derive_authority_tier(
            u5_nm2, _match(V2Confidence.HIGH), CUSTOMER_CTX, _strong_profile()
        )
        assert decision.tier is AuthorityTier.NEEDS_REVIEW
        assert decision.product_evidence_quality is ProductEvidenceQuality.STRONG
        assert decision.relationship_authority is RelationshipAuthority.NOT_ESTABLISHED
        assert AuthorityRuleV2.CEILING_NEAR_MISS_SUBSTITUTION_WITHOUT_RELATION_AUTHORITY in decision.fired_rules

    def test_ceiling_with_customer_plus_product_context(self, u5_nm2) -> None:
        """Customer retrieval plus reviewed product grounding still does
        not establish the identifier relationship: the ceiling holds even
        with STRONG product evidence."""
        combined = frozenset({
            ContextProvenance.CUSTOMER_RETRIEVAL_RELATION,
            ContextProvenance.MANUFACTURER_PRODUCT_CONTEXT,
        })
        decision = derive_authority_tier(
            u5_nm2,
            _match(V2Confidence.HIGH),
            combined,
            _strong_profile(REVIEWED_SOURCES),
        )
        assert decision.tier is AuthorityTier.NEEDS_REVIEW
        assert decision.product_evidence_quality is ProductEvidenceQuality.STRONG
        assert AuthorityRuleV2.CEILING_NEAR_MISS_SUBSTITUTION_WITHOUT_RELATION_AUTHORITY in decision.fired_rules

    def test_relation_authority_satisfies_the_gate(self, u5_nm2) -> None:
        """With reviewed relationship authority the NM-2 ceiling is
        passed and the matrix PERMITS the automatic tier — subject to the
        rest of the authority gates (here: STRONG product evidence, no
        conflicts). The ceiling rule must not fire."""
        decision = derive_authority_tier(
            u5_nm2,
            _match(V2Confidence.HIGH),
            RELATION_CTX,
            _strong_profile(REVIEWED_SOURCES),
        )
        assert decision.tier is AuthorityTier.AI_ASSISTED_COMPARABLE
        assert decision.product_evidence_quality is ProductEvidenceQuality.STRONG
        assert decision.relationship_authority is RelationshipAuthority.ESTABLISHED
        assert AuthorityRuleV2.CEILING_NEAR_MISS_SUBSTITUTION_WITHOUT_RELATION_AUTHORITY not in decision.fired_rules

    def test_nm2_may_remain_reviewable_even_with_match_high(
        self, u5_nm2
    ) -> None:
        """MATCH + HIGH + STRONG product evidence does not auto-price
        NM-2 without relationship authority; a human may still confirm it
        later."""
        decision = derive_authority_tier(
            u5_nm2,
            _match(V2Confidence.HIGH),
            PRODUCT_CTX,
            _strong_profile(REVIEWED_SOURCES),
        )
        assert decision.tier is AuthorityTier.NEEDS_REVIEW

        confirmed = derive_authority_tier(
            u5_nm2,
            _match(V2Confidence.HIGH),
            PRODUCT_CTX,
            _strong_profile(REVIEWED_SOURCES),
            HumanReviewStateV2.CONFIRMED,
        )
        assert confirmed.tier is AuthorityTier.HUMAN_CONFIRMED

    def test_nm2_match_medium_stays_needs_review(self, u5_nm2) -> None:
        decision = derive_authority_tier(
            u5_nm2, _match(V2Confidence.MEDIUM), RELATION_CTX
        )
        assert decision.tier is AuthorityTier.NEEDS_REVIEW

    def test_nm1_has_no_substitution_ceiling(self) -> None:
        """The NM-2 substitution ceiling is specific to the bounded NM-2
        shape: an NM-1 truncation with relationship authority and STRONG
        product evidence may reach the automatic tier."""
        u5_nm1 = _v2(mpn="ABC-12")
        assert u5_nm1.near_miss_substitution_active is False
        decision = derive_authority_tier(
            u5_nm1,
            _match(V2Confidence.HIGH),
            RELATION_CTX,
            _strong_profile(REVIEWED_SOURCES),
        )
        assert decision.tier is AuthorityTier.AI_ASSISTED_COMPARABLE
        assert (
            AuthorityRuleV2
            .CEILING_NEAR_MISS_SUBSTITUTION_WITHOUT_RELATION_AUTHORITY
            not in decision.fired_rules
        )
        assert (
            AuthorityRuleV2.CEILING_IDENTIFIER_RELATIONSHIP_NOT_ESTABLISHED
            not in decision.fired_rules
        )

    def test_hard_conflict_still_supersedes_ceilinged_nm2(self, u5_nm2) -> None:
        # S2-A-FU1: the hard-conflict supersession is proven from a
        # would-be AI_ASSISTED base (STRONG product evidence).
        decision = derive_authority_tier(
            u5_nm2,
            _match(V2Confidence.HIGH, frozenset({ConflictClass.CAPACITY})),
            NO_CTX,
            _strong_profile(),
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
        # S2-A-FU1: the table is a frozen tuple of (provenance,
        # capabilities) entries; the exact capability sets are pinned per
        # entry through the pure lookup.
        assert {
            provenance
            for provenance, _capabilities in CONTEXT_PROVENANCE_CAPABILITIES
        } == set(ContextProvenance)
        assert len(CONTEXT_PROVENANCE_CAPABILITIES) == 3
        assert context_provenance_capabilities(
            ContextProvenance.MANUFACTURER_PRODUCT_CONTEXT
        ) == frozenset({ContextCapability.GROUND_PRODUCT_FACTS})
        assert context_provenance_capabilities(
            ContextProvenance.MANUFACTURER_RELATION_AUTHORITY
        ) == frozenset(
            {
                ContextCapability.GROUND_PRODUCT_FACTS,
                ContextCapability.ESTABLISH_IDENTIFIER_RELATIONSHIP,
            }
        )
        assert context_provenance_capabilities(
            ContextProvenance.CUSTOMER_RETRIEVAL_RELATION
        ) == frozenset({ContextCapability.RETRIEVAL_RECALL_ONLY})

    def test_customer_retrieval_is_not_manufacturer_context(self) -> None:
        customer = context_provenance_capabilities(
            ContextProvenance.CUSTOMER_RETRIEVAL_RELATION
        )
        assert ContextCapability.ESTABLISH_IDENTIFIER_RELATIONSHIP not in customer
        assert ContextCapability.GROUND_PRODUCT_FACTS not in customer
        assert customer == frozenset({ContextCapability.RETRIEVAL_RECALL_ONLY})

    def test_product_context_does_not_establish_the_relationship(self) -> None:
        product = context_provenance_capabilities(
            ContextProvenance.MANUFACTURER_PRODUCT_CONTEXT
        )
        assert ContextCapability.ESTABLISH_IDENTIFIER_RELATIONSHIP not in product
        assert has_relationship_authority(PRODUCT_CTX) is False
        # S2-A-FU1: reviewed product grounding strengthens PRODUCT
        # evidence (dimension A -> LIMITED) but does not establish the
        # identifier relationship (dimension B -> NOT_ESTABLISHED for a
        # question-bearing state).
        assert (
            derive_product_evidence_quality(_no_title_no_facts_profile(), PRODUCT_CTX)
            is ProductEvidenceQuality.LIMITED
        )
        u5 = _v2(mpn="ABC-124")
        assert (
            derive_relationship_authority(u5, PRODUCT_CTX)
            is RelationshipAuthority.NOT_ESTABLISHED
        )

    def test_customer_retrieval_alone_is_weak_and_gateless(self) -> None:
        assert has_relationship_authority(CUSTOMER_CTX) is False
        # S2-A-FU1: customer retrieval grounds no product evidence:
        # without a title or matched facts, product evidence quality is
        # WEAK.
        no_evidence = _no_title_no_facts_profile()
        assert derive_product_evidence_quality(no_evidence, CUSTOMER_CTX) is ProductEvidenceQuality.WEAK
        assert derive_product_evidence_quality(no_evidence, NO_CTX) is ProductEvidenceQuality.WEAK

    def test_relation_authority_establishes_the_relationship(self) -> None:
        # S2-A-FU1: relationship authority answers the state-specific
        # identifier-relationship question (dimension B) — it no longer
        # stands in for product evidence quality (dimension A).
        assert has_relationship_authority(RELATION_CTX) is True
        u5 = _v2(mpn="ABC-124")
        assert (
            derive_relationship_authority(u5, RELATION_CTX)
            is RelationshipAuthority.ESTABLISHED
        )
        assert (
            derive_relationship_authority(u5, PRODUCT_CTX)
            is RelationshipAuthority.NOT_ESTABLISHED
        )

    def test_customer_plus_product_stays_limited_and_gateless(self) -> None:
        combined = PRODUCT_CTX | CUSTOMER_CTX
        assert has_relationship_authority(combined) is False
        assert (
            derive_product_evidence_quality(_no_title_no_facts_profile(), combined)
            is ProductEvidenceQuality.LIMITED
        )

    def test_relation_plus_customer_stays_strong(self) -> None:
        # S2-A-FU1: customer retrieval does not dilute an established
        # identifier relationship — relationship authority "stays"
        # ESTABLISHED when customer retrieval is added.
        combined = RELATION_CTX | CUSTOMER_CTX
        assert has_relationship_authority(combined) is True
        u1 = _v2(title="Has ABC-123 in the title")
        assert (
            derive_relationship_authority(u1, combined)
            is RelationshipAuthority.ESTABLISHED
        )

    def test_customer_retrieval_cannot_grant_auto_authority(self) -> None:
        """Customer retrieval confers ZERO relationship authority and no
        product grounding: even STRONG title-grounded product evidence
        cannot reach automatic comparable authority for a question-bearing
        state (U1) when only customer retrieval is present."""
        u1 = _v2(title="Has ABC-123 in the title")
        decision = derive_authority_tier(
            u1, _match(V2Confidence.HIGH), CUSTOMER_CTX, _strong_profile()
        )
        assert decision.product_evidence_quality is ProductEvidenceQuality.STRONG
        assert decision.relationship_authority is RelationshipAuthority.NOT_ESTABLISHED
        assert decision.tier is AuthorityTier.NEEDS_REVIEW
        assert decision.tier is not AuthorityTier.AI_ASSISTED_COMPARABLE
        assert (
            AuthorityRuleV2.CEILING_IDENTIFIER_RELATIONSHIP_NOT_ESTABLISHED
            in decision.fired_rules
        )

    def test_manufacturer_product_context_alone_cannot_reach_auto_tier(
        self,
    ) -> None:
        # S2-A-FU1: even at STRONG product evidence (grounded in the
        # reviewed product context), product grounding alone cannot reach
        # the automatic tier — the identifier-relationship question is
        # unanswered.
        u1 = _v2(title="Has ABC-123 in the title")
        decision = derive_authority_tier(
            u1,
            _match(V2Confidence.HIGH),
            PRODUCT_CTX,
            _strong_profile(REVIEWED_SOURCES),
        )
        assert decision.product_evidence_quality is ProductEvidenceQuality.STRONG
        assert decision.relationship_authority is RelationshipAuthority.NOT_ESTABLISHED
        assert decision.tier is AuthorityTier.NEEDS_REVIEW

    def test_relation_authority_can_satisfy_the_matrix_gate(self) -> None:
        # S2-A-FU1: both orthogonal prerequisites must be met: STRONG
        # product evidence (dimension A) AND an established identifier
        # relationship (dimension B).
        u1 = _v2(title="Has ABC-123 in the title")
        decision = derive_authority_tier(
            u1,
            _match(V2Confidence.HIGH),
            RELATION_CTX,
            _strong_profile(REVIEWED_SOURCES),
        )
        assert decision.product_evidence_quality is ProductEvidenceQuality.STRONG
        assert decision.relationship_authority is RelationshipAuthority.ESTABLISHED
        assert decision.tier is AuthorityTier.AI_ASSISTED_COMPARABLE

    def test_context_quality_is_never_ai_derived(self) -> None:
        """A LOW AI outcome cannot raise product evidence quality, and a
        HIGH one cannot lower it: quality is a pure function of the
        bounded profile + provenance classes, never of the evaluation."""
        profile = _strong_profile(REVIEWED_SOURCES)
        assert (
            derive_product_evidence_quality(profile, RELATION_CTX)
            is derive_product_evidence_quality(profile, RELATION_CTX)
        )
        u1 = _v2(title="Has ABC-123 in the title")
        low = derive_authority_tier(
            u1,
            SemanticEvaluationV2.evaluated(V2SemanticDecision.MATCH, V2Confidence.LOW),
            RELATION_CTX,
            profile,
        )
        assert low.product_evidence_quality is ProductEvidenceQuality.STRONG
        assert low.tier is AuthorityTier.EXCLUDED_LOW_CONFIDENCE

    def test_provenance_input_must_be_a_frozenset(self) -> None:
        with pytest.raises(TypeError):
            derive_product_evidence_quality(
                _no_title_no_facts_profile(), set()  # type: ignore[arg-type]
            )
        with pytest.raises(TypeError):
            has_relationship_authority(set())  # type: ignore[arg-type]
        u1 = _v2(title="Has ABC-123 in the title")
        with pytest.raises(TypeError):
            derive_relationship_authority(u1, set())  # type: ignore[arg-type]


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
        assert (
            decision_plain.product_evidence_quality
            is decision_worded.product_evidence_quality
        )
        assert (
            decision_plain.relationship_authority
            is decision_worded.relationship_authority
        )


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
            for quality in ProductEvidenceQuality
        }
        assert {key for key, _tier in SEMANTIC_OUTCOME_TIER_MATRIX} == grid
        assert len(SEMANTIC_OUTCOME_TIER_MATRIX) == 27

    def test_matrix_full_table_is_frozen(self) -> None:
        M, NM, U = V2SemanticDecision.MATCH, V2SemanticDecision.NO_MATCH, V2SemanticDecision.UNCERTAIN
        H, MD, L = V2Confidence.HIGH, V2Confidence.MEDIUM, V2Confidence.LOW
        S, LI, W = ProductEvidenceQuality.STRONG, ProductEvidenceQuality.LIMITED, ProductEvidenceQuality.WEAK
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
        # S2-A-FU1: the exact 27-row tier table is frozen; the stored
        # representation is an immutable entry tuple in canonical (enum
        # definition) order.
        order = (
            {m: i for i, m in enumerate(V2SemanticDecision)},
            {m: i for i, m in enumerate(V2Confidence)},
            {m: i for i, m in enumerate(ProductEvidenceQuality)},
        )
        assert SEMANTIC_OUTCOME_TIER_MATRIX == tuple(
            (key, expected[key])
            for key in sorted(
                expected,
                key=lambda k: (order[0][k[0]], order[1][k[1]], order[2][k[2]]),
            )
        )
        for key, tier in expected.items():
            assert semantic_outcome_tier(*key) is tier

    def test_state_policy_table_is_complete_and_bounded(self) -> None:
        # S2-A-FU1: the table is a frozen tuple of (state, policy)
        # entries with a pure lookup.
        assert {
            state for state, _policy in DETERMINISTIC_STATE_POLICIES
        } == set(IdentityStateV2)
        assert len(DETERMINISTIC_STATE_POLICIES) == 4
        assert deterministic_state_policy(
            IdentityStateV2.DETERMINISTIC_VERIFIED
        ).deterministic_tier is AuthorityTier.MACHINE_VERIFIED
        assert deterministic_state_policy(
            IdentityStateV2.DETERMINISTIC_CONFLICT
        ).deterministic_tier is AuthorityTier.HARD_CONFLICT
        assert deterministic_state_policy(
            IdentityStateV2.DETERMINISTIC_UNEVALUABLE
        ).deterministic_tier is AuthorityTier.EXCLUDED_LOW_CONFIDENCE
        assert deterministic_state_policy(
            IdentityStateV2.DETERMINISTIC_UNCERTAIN
        ).deterministic_tier is AuthorityTier.NEEDS_REVIEW

        # Only the uncertain state is a semantic entry point.
        for state, policy in DETERMINISTIC_STATE_POLICIES:
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
        # S2-A-FU1: incomplete product evidence (a usable title without
        # bounded matched-attribute corroboration — LIMITED) caps
        # MATCH + HIGH at NEEDS_REVIEW under any provenance set.
        u1 = _v2(title="Has ABC-123 in the title")
        for ctx in (PRODUCT_CTX, CUSTOMER_CTX, NO_CTX):
            decision = derive_authority_tier(
                u1, _match(V2Confidence.HIGH), ctx, _limited_title_profile()
            )
            assert decision.tier is AuthorityTier.NEEDS_REVIEW, ctx
            assert decision.product_evidence_quality is ProductEvidenceQuality.LIMITED

    def test_match_high_reviewable_conflict_is_needs_review(self) -> None:
        # S2-A-FU1: the reviewable-conflict ceiling caps a would-be
        # AI_ASSISTED base (STRONG product evidence + established
        # relationship) at NEEDS_REVIEW.
        u1 = _v2(title="Has ABC-123 in the title")
        decision = derive_authority_tier(
            u1,
            _match(V2Confidence.HIGH, frozenset({ConflictClass.REVISION_OR_SUFFIX})),
            RELATION_CTX,
            _strong_profile(REVIEWED_SOURCES),
        )
        assert decision.tier is AuthorityTier.NEEDS_REVIEW
        assert decision.product_evidence_quality is ProductEvidenceQuality.STRONG
        assert AuthorityRuleV2.CEILING_REVIEWABLE_CONFLICT in decision.fired_rules

    def test_condition_only_conflict_never_caps_authority(self) -> None:
        u1 = _v2(title="Has ABC-123 in the title")
        decision = derive_authority_tier(
            u1,
            _match(V2Confidence.HIGH, frozenset({ConflictClass.CONDITION})),
            RELATION_CTX,
            _strong_profile(REVIEWED_SOURCES),
        )
        assert decision.tier is AuthorityTier.AI_ASSISTED_COMPARABLE
        assert AuthorityRuleV2.CEILING_REVIEWABLE_CONFLICT not in decision.fired_rules

    def test_hard_conflict_supersedes_match_high_strong(self) -> None:
        # S2-A-FU1: "strong" now means STRONG product evidence (dimension
        # A); the hard conflict supersedes even that.
        u1 = _v2(title="Has ABC-123 in the title")
        decision = derive_authority_tier(
            u1,
            _match(V2Confidence.HIGH, frozenset({ConflictClass.CAPACITY})),
            RELATION_CTX,
            _strong_profile(REVIEWED_SOURCES),
        )
        assert decision.tier is AuthorityTier.HARD_CONFLICT
        assert AuthorityRuleV2.HARD_CONFLICT_SUPERSEDES in decision.fired_rules

    def test_uncertain_decision_with_actionable_context_is_needs_review(
        self,
    ) -> None:
        # S2-A-FU1: actionable product evidence = LIMITED or STRONG (a
        # usable title is the bounded "something to act on" fact).
        u1 = _v2(title="Has ABC-123 in the title")
        decision = derive_authority_tier(
            u1,
            SemanticEvaluationV2.evaluated(V2SemanticDecision.UNCERTAIN, V2Confidence.HIGH),
            PRODUCT_CTX,
            _limited_title_profile(),
        )
        assert decision.tier is AuthorityTier.NEEDS_REVIEW
        assert decision.product_evidence_quality is ProductEvidenceQuality.LIMITED

    def test_uncertain_decision_without_actionable_context_is_excluded(
        self,
    ) -> None:
        # S2-A-FU1: no usable title, no reviewed grounding, no matched
        # facts -> WEAK product evidence -> EXCLUDED (the default
        # conservative profile asserts no title for U1).
        u1 = _v2(title="Has ABC-123 in the title")
        decision = derive_authority_tier(
            u1,
            SemanticEvaluationV2.evaluated(V2SemanticDecision.UNCERTAIN, V2Confidence.HIGH),
            NO_CTX,
        )
        assert decision.tier is AuthorityTier.EXCLUDED_LOW_CONFIDENCE
        assert decision.product_evidence_quality is ProductEvidenceQuality.WEAK

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
            c,
            _match(V2Confidence.HIGH),
            RELATION_CTX,
            human_review=HumanReviewStateV2.CONFIRMED,
        )
        assert decision.tier is AuthorityTier.HARD_CONFLICT
        assert AuthorityRuleV2.HARD_CONFLICT_SUPERSEDES_HUMAN in decision.fired_rules

        # 2. HUMAN_CONFIRMED beats AI authority.
        u1 = _v2(title="Has ABC-123 in the title")
        decision = derive_authority_tier(
            u1,
            _match(V2Confidence.HIGH),
            RELATION_CTX,
            _strong_profile(REVIEWED_SOURCES),
            HumanReviewStateV2.CONFIRMED,
        )
        assert decision.tier is AuthorityTier.HUMAN_CONFIRMED
        assert AuthorityRuleV2.HUMAN_CONFIRMED_APPLIED in decision.fired_rules

        # 3. AI authority is the floor of the three (both orthogonal
        #    prerequisites met: STRONG product evidence + established
        #    relationship).
        decision = derive_authority_tier(
            u1,
            _match(V2Confidence.HIGH),
            RELATION_CTX,
            _strong_profile(REVIEWED_SOURCES),
        )
        assert decision.tier is AuthorityTier.AI_ASSISTED_COMPARABLE

    def test_human_rejected_on_uncertain(self) -> None:
        u1 = _v2(title="Has ABC-123 in the title")
        decision = derive_authority_tier(
            u1, None, NO_CTX, human_review=HumanReviewStateV2.REJECTED
        )
        assert decision.tier is AuthorityTier.HUMAN_REJECTED
        assert AuthorityRuleV2.HUMAN_REJECTED_APPLIED in decision.fired_rules

    def test_human_outcome_not_applicable_on_verified(self) -> None:
        v = _v2(mpn="ABC-123")
        decision = derive_authority_tier(
            v, None, NO_CTX, human_review=HumanReviewStateV2.CONFIRMED
        )
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
            policy = deterministic_state_policy(state)
            # The default (no explicit profile) is the conservative
            # state-derived profile: no title asserted for the
            # representatives here (none is U4), no matched facts.
            default_profile = _no_title_no_facts_profile()
            for evaluation in evaluations:
                for context in contexts:
                    for human in humans:
                        decision = derive_authority_tier(
                            assessment_v2, evaluation, context,
                            human_review=human,
                        )
                        assert decision.tier in set(AuthorityTier)
                        assert (
                            decision.product_evidence_quality
                            is derive_product_evidence_quality(default_profile, context)
                        )
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
        excluded through the frozen product-evidence-quality/confidence
        gates (S2-A-FU1)."""
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
# F2. Orthogonal authority prerequisites (S2-A-FU1)
# ===========================================================================


class TestU4AutoAuthority:
    """S2-A-FU1 blocker 1: U4_NO_MPN description-match candidates are NOT
    re-conservatized. A no-MPN candidate has no identifier relationship
    for a manufacturer source to establish; its auto-authority bar is the
    bounded product/description evidence bar, and
    MANUFACTURER_RELATION_AUTHORITY is never required."""

    def _u4(self) -> IdentityStateAssessmentV2:
        v2 = _v2(title="Usable title without any MPN")
        assert v2.substate is UncertainSubstateV2.U4_NO_MPN
        return v2

    def test_u4_match_high_strong_product_evidence_reaches_ai_assisted(self) -> None:
        """1. U4 + MATCH + HIGH + strong approved product evidence + no
        conflicts CAN produce AI_ASSISTED_COMPARABLE."""
        u4 = self._u4()
        decision = derive_authority_tier(
            u4, _match(V2Confidence.HIGH), NO_CTX, _strong_profile()
        )
        assert decision.tier is AuthorityTier.AI_ASSISTED_COMPARABLE
        assert decision.product_evidence_quality is ProductEvidenceQuality.STRONG
        assert decision.relationship_authority is RelationshipAuthority.NOT_APPLICABLE
        assert AuthorityRuleV2.SEMANTIC_OUTCOME_MATRIX in decision.fired_rules
        assert (
            AuthorityRuleV2.CEILING_IDENTIFIER_RELATIONSHIP_NOT_ESTABLISHED
            not in decision.fired_rules
        )

    def test_u4_does_not_require_manufacturer_relation_authority(self) -> None:
        """2. U4 auto-authority does NOT require
        MANUFACTURER_RELATION_AUTHORITY: the identifier-relationship
        question does not exist for a no-MPN candidate (NOT_APPLICABLE),
        with or without relation provenance present."""
        u4 = self._u4()
        assert (
            derive_relationship_authority(u4, NO_CTX)
            is RelationshipAuthority.NOT_APPLICABLE
        )
        assert (
            derive_relationship_authority(u4, RELATION_CTX)
            is RelationshipAuthority.NOT_APPLICABLE
        )
        assert (
            derive_relationship_authority(u4, CUSTOMER_CTX)
            is RelationshipAuthority.NOT_APPLICABLE
        )
        without_relation = derive_authority_tier(
            u4, _match(V2Confidence.HIGH), NO_CTX, _strong_profile()
        )
        assert without_relation.tier is AuthorityTier.AI_ASSISTED_COMPARABLE
        with_relation = derive_authority_tier(
            u4,
            _match(V2Confidence.HIGH),
            RELATION_CTX,
            _strong_profile(REVIEWED_SOURCES),
        )
        assert with_relation.tier is AuthorityTier.AI_ASSISTED_COMPARABLE
        assert (
            with_relation.relationship_authority
            is RelationshipAuthority.NOT_APPLICABLE
        )

    def test_u4_weak_evidence_stays_needs_review_or_excluded(self) -> None:
        """3. U4 weak/incomplete evidence remains NEEDS_REVIEW or
        EXCLUDED_LOW_CONFIDENCE according to the frozen matrix (the bar
        is bounded: a title alone is not strong)."""
        u4 = self._u4()
        # Title only (LIMITED product evidence) + MATCH + HIGH -> NEEDS_REVIEW.
        limited = derive_authority_tier(
            u4, _match(V2Confidence.HIGH), NO_CTX, _limited_title_profile()
        )
        assert limited.tier is AuthorityTier.NEEDS_REVIEW
        assert limited.product_evidence_quality is ProductEvidenceQuality.LIMITED
        # MATCH + MEDIUM + STRONG -> NEEDS_REVIEW.
        medium = derive_authority_tier(
            u4, _match(V2Confidence.MEDIUM), NO_CTX, _strong_profile()
        )
        assert medium.tier is AuthorityTier.NEEDS_REVIEW
        # MATCH + LOW + STRONG -> EXCLUDED.
        low = derive_authority_tier(
            u4, _match(V2Confidence.LOW), NO_CTX, _strong_profile()
        )
        assert low.tier is AuthorityTier.EXCLUDED_LOW_CONFIDENCE
        # NO_MATCH + HIGH + STRONG -> EXCLUDED.
        no_match = derive_authority_tier(
            u4,
            SemanticEvaluationV2.evaluated(
                V2SemanticDecision.NO_MATCH, V2Confidence.HIGH
            ),
            NO_CTX,
            _strong_profile(),
        )
        assert no_match.tier is AuthorityTier.EXCLUDED_LOW_CONFIDENCE
        # A reviewable conflict still caps U4 at NEEDS_REVIEW.
        reviewable = derive_authority_tier(
            u4,
            _match(
                V2Confidence.HIGH, frozenset({ConflictClass.REVISION_OR_SUFFIX})
            ),
            NO_CTX,
            _strong_profile(),
        )
        assert reviewable.tier is AuthorityTier.NEEDS_REVIEW
        assert AuthorityRuleV2.CEILING_REVIEWABLE_CONFLICT in reviewable.fired_rules


class TestNM2CeilingWithStrongEvidence:
    """S2-A-FU1: the NM-2 rule MUST REMAIN. U5 +
    NEAR_MISS_SUBSTITUTION without reviewed authoritative identifier
    relationship caps the maximum automatic tier at NEEDS_REVIEW — even
    with MATCH + HIGH + excellent description/product alignment."""

    def _u5_nm2(self) -> IdentityStateAssessmentV2:
        v2 = _v2(mpn="ABC-124")
        assert v2.substate is UncertainSubstateV2.U5_NEAR_MISS_MPN
        assert v2.near_miss_substitution_active
        return v2

    def test_u5_nm2_strong_product_evidence_without_relation_authority_stays_needs_review(self) -> None:
        """4. U5 NM-2 + MATCH/HIGH + strong product evidence but NO
        MANUFACTURER_RELATION_AUTHORITY remains NEEDS_REVIEW."""
        u5 = self._u5_nm2()
        decision = derive_authority_tier(
            u5,
            _match(V2Confidence.HIGH),
            PRODUCT_CTX,
            _strong_profile(REVIEWED_SOURCES),
        )
        assert decision.tier is AuthorityTier.NEEDS_REVIEW
        assert decision.product_evidence_quality is ProductEvidenceQuality.STRONG
        assert decision.relationship_authority is RelationshipAuthority.NOT_ESTABLISHED
        assert (
            AuthorityRuleV2
            .CEILING_NEAR_MISS_SUBSTITUTION_WITHOUT_RELATION_AUTHORITY
            in decision.fired_rules
        )

    def test_u5_nm2_valid_relation_authority_may_pass_the_ceiling(self) -> None:
        """5. U5 NM-2 + valid MANUFACTURER_RELATION_AUTHORITY may pass
        that specific ceiling, subject to the rest of the authority gates
        (STRONG product evidence; conflicts still cap / supersede)."""
        u5 = self._u5_nm2()
        decision = derive_authority_tier(
            u5,
            _match(V2Confidence.HIGH),
            RELATION_CTX,
            _strong_profile(REVIEWED_SOURCES),
        )
        assert decision.tier is AuthorityTier.AI_ASSISTED_COMPARABLE
        assert decision.relationship_authority is RelationshipAuthority.ESTABLISHED
        assert (
            AuthorityRuleV2
            .CEILING_NEAR_MISS_SUBSTITUTION_WITHOUT_RELATION_AUTHORITY
            not in decision.fired_rules
        )
        # The rest of the gates still apply: a reviewable conflict caps.
        reviewable = derive_authority_tier(
            u5,
            _match(V2Confidence.HIGH, frozenset({ConflictClass.BRAND})),
            RELATION_CTX,
            _strong_profile(REVIEWED_SOURCES),
        )
        assert reviewable.tier is AuthorityTier.NEEDS_REVIEW
        assert AuthorityRuleV2.CEILING_REVIEWABLE_CONFLICT in reviewable.fired_rules
        # A hard conflict still supersedes.
        hard = derive_authority_tier(
            u5,
            _match(V2Confidence.HIGH, frozenset({ConflictClass.GENERATION})),
            RELATION_CTX,
            _strong_profile(REVIEWED_SOURCES),
        )
        assert hard.tier is AuthorityTier.HARD_CONFLICT
        assert AuthorityRuleV2.HARD_CONFLICT_SUPERSEDES in hard.fired_rules

    def test_customer_retrieval_cannot_satisfy_the_nm2_relationship_gate(self) -> None:
        """6. CUSTOMER_RETRIEVAL_RELATION confers zero relationship
        authority: it cannot satisfy the NM-2 gate even alongside STRONG
        product evidence (alone, or with product grounding)."""
        u5 = self._u5_nm2()
        for ctx in (CUSTOMER_CTX, PRODUCT_CTX | CUSTOMER_CTX):
            decision = derive_authority_tier(
                u5, _match(V2Confidence.HIGH), ctx, _strong_profile()
            )
            assert decision.tier is AuthorityTier.NEEDS_REVIEW, ctx
            assert (
                decision.relationship_authority
                is RelationshipAuthority.NOT_ESTABLISHED
            ), ctx
            assert (
                AuthorityRuleV2
                .CEILING_NEAR_MISS_SUBSTITUTION_WITHOUT_RELATION_AUTHORITY
                in decision.fired_rules
            ), ctx
        assert (
            derive_relationship_authority(u5, CUSTOMER_CTX)
            is RelationshipAuthority.NOT_ESTABLISHED
        )


class TestRelationshipAuthorityStates:
    """S2-A-FU1: dimension B is state-specific — the
    identifier-relationship question exists only where the candidate
    published identifier-like evidence (U1/U2/U3/U5) or was verified by
    the frozen deterministic comparator."""

    def test_u4_is_not_applicable_with_or_without_relation_provenance(self) -> None:
        u4 = _v2(title="Usable title without any MPN")
        assert (
            derive_relationship_authority(u4, NO_CTX)
            is RelationshipAuthority.NOT_APPLICABLE
        )
        assert (
            derive_relationship_authority(u4, RELATION_CTX)
            is RelationshipAuthority.NOT_APPLICABLE
        )
        assert (
            derive_relationship_authority(u4, CUSTOMER_CTX)
            is RelationshipAuthority.NOT_APPLICABLE
        )

    def test_u1_u2_u3_u5_require_reviewed_relation_provenance(self) -> None:
        cases = {
            "u1": _v2(title="Has ABC-123 in the title"),
            "u2": _v2(sku="RETAIL-SKU-1"),
            "u3": _v2(mpn="ABC"),
            "u5_nm1": _v2(mpn="ABC-12"),
            "u5_nm2": _v2(mpn="ABC-124"),
        }
        for name, v2 in cases.items():
            assert v2.state is IdentityStateV2.DETERMINISTIC_UNCERTAIN, name
            assert (
                derive_relationship_authority(v2, NO_CTX)
                is RelationshipAuthority.NOT_ESTABLISHED
            ), name
            assert (
                derive_relationship_authority(v2, RELATION_CTX)
                is RelationshipAuthority.ESTABLISHED
            ), name

    def test_verified_established_conflict_not_established_unevaluable_not_applicable(self) -> None:
        v = _v2(mpn="ABC-123")
        assert (
            derive_relationship_authority(v, NO_CTX)
            is RelationshipAuthority.ESTABLISHED
        )
        c1 = _v2(mpn="XYZ-999")
        assert (
            derive_relationship_authority(c1, NO_CTX)
            is RelationshipAuthority.NOT_ESTABLISHED
        )
        e1 = _v2(req_mpn="", description="description only")
        assert (
            derive_relationship_authority(e1, NO_CTX)
            is RelationshipAuthority.NOT_APPLICABLE
        )
        e2 = _v2(title=None)
        assert (
            derive_relationship_authority(e2, NO_CTX)
            is RelationshipAuthority.NOT_APPLICABLE
        )

    def test_question_bearing_states_without_relation_authority_are_capped(self) -> None:
        """U1/U2/U3 (and U5 NM-1) + MATCH + HIGH + STRONG product
        evidence still require the identifier-relationship question to be
        ESTABLISHED for automatic authority — preserving the pre-FU1
        effective requirement (no authority expansion for these
        states)."""
        cases = {
            "u1": _v2(title="Has ABC-123 in the title"),
            "u2": _v2(sku="RETAIL-SKU-1"),
            "u3": _v2(mpn="ABC"),
            "u5_nm1": _v2(mpn="ABC-12"),
        }
        for name, v2 in cases.items():
            capped = derive_authority_tier(
                v2, _match(V2Confidence.HIGH), NO_CTX, _strong_profile()
            )
            assert capped.tier is AuthorityTier.NEEDS_REVIEW, name
            assert (
                AuthorityRuleV2.CEILING_IDENTIFIER_RELATIONSHIP_NOT_ESTABLISHED
                in capped.fired_rules
            ), name
            passed = derive_authority_tier(
                v2,
                _match(V2Confidence.HIGH),
                RELATION_CTX,
                _strong_profile(REVIEWED_SOURCES),
            )
            assert passed.tier is AuthorityTier.AI_ASSISTED_COMPARABLE, name


class TestProductEvidenceBar:
    """S2-A-FU1: dimension A — the bounded, testable auto-authority
    evidence bar. A title alone is not strong; matched attributes must be
    grounded in bounded candidate-side sources (never model claims)."""

    def test_strong_bar_requires_title_and_two_dimensions(self) -> None:
        # Pin the bounded thresholds.
        assert STRONG_PRODUCT_EVIDENCE_MIN_MATCHED_FACTS == 2
        assert STRONG_PRODUCT_EVIDENCE_MIN_MATCHED_DIMENSIONS == 2

        # A usable title alone is LIMITED, not STRONG.
        assert (
            derive_product_evidence_quality(_limited_title_profile(), NO_CTX)
            is ProductEvidenceQuality.LIMITED
        )
        # Two facts on ONE dimension is not breadth: LIMITED.
        one_dim = ProductEvidenceProfileV2(
            True,
            frozenset(
                {
                    ProductEvidenceFactV2(
                        ProductEvidenceDimension.CAPACITY, TITLE_SOURCES
                    ),
                    ProductEvidenceFactV2(
                        ProductEvidenceDimension.CAPACITY,
                        TITLE_SOURCES | REVIEWED_SOURCES,
                    ),
                }
            ),
        )
        assert (
            derive_product_evidence_quality(one_dim, PRODUCT_CTX)
            is ProductEvidenceQuality.LIMITED
        )
        # Two facts on TWO dimensions + title: STRONG.
        assert (
            derive_product_evidence_quality(_strong_profile(), NO_CTX)
            is ProductEvidenceQuality.STRONG
        )
        # Two reviewed-grounded facts but no usable title: LIMITED.
        no_title = ProductEvidenceProfileV2(
            False,
            frozenset(
                {
                    ProductEvidenceFactV2(
                        ProductEvidenceDimension.CAPACITY, REVIEWED_SOURCES
                    ),
                    ProductEvidenceFactV2(
                        ProductEvidenceDimension.INTERFACE, REVIEWED_SOURCES
                    ),
                }
            ),
        )
        assert (
            derive_product_evidence_quality(no_title, PRODUCT_CTX)
            is ProductEvidenceQuality.LIMITED
        )
        # Reviewed grounding alone (no title, no facts): LIMITED.
        assert (
            derive_product_evidence_quality(
                _no_title_no_facts_profile(), PRODUCT_CTX
            )
            is ProductEvidenceQuality.LIMITED
        )
        # Nothing at all: WEAK — customer retrieval grounds nothing.
        empty = _no_title_no_facts_profile()
        assert (
            derive_product_evidence_quality(empty, NO_CTX)
            is ProductEvidenceQuality.WEAK
        )
        assert (
            derive_product_evidence_quality(empty, CUSTOMER_CTX)
            is ProductEvidenceQuality.WEAK
        )

    def test_matched_fact_sources_are_bounded_no_model_self_promotion(self) -> None:
        # The grounded-source vocabulary has exactly two members: frozen
        # page evidence and reviewed product context. There is NO member
        # for a model claim, so the model cannot self-promote its
        # authority by asserting arbitrary matched attributes.
        assert frozenset(CandidateProductEvidenceSource) == frozenset(
            {
                CandidateProductEvidenceSource.LISTING_PRODUCT_TITLE,
                CandidateProductEvidenceSource.REVIEWED_PRODUCT_CONTEXT,
            }
        )
        # The dimension vocabulary is bounded to the six hard product
        # dimensions (the positive of the ALWAYS_HARD conflict classes).
        assert frozenset(ProductEvidenceDimension) == frozenset(
            {
                ProductEvidenceDimension.PRODUCT_FAMILY,
                ProductEvidenceDimension.GENERATION,
                ProductEvidenceDimension.CAPACITY,
                ProductEvidenceDimension.INTERFACE,
                ProductEvidenceDimension.FORM_FACTOR,
                ProductEvidenceDimension.PRODUCT_ROLE,
            }
        )
        # An ungrounded fact is outside the contract.
        with pytest.raises(ValueError):
            ProductEvidenceFactV2(ProductEvidenceDimension.CAPACITY, frozenset())
        with pytest.raises(TypeError):
            ProductEvidenceFactV2("CAPACITY", TITLE_SOURCES)  # type: ignore[arg-type]
        with pytest.raises(TypeError):
            ProductEvidenceFactV2(
                ProductEvidenceDimension.CAPACITY, TITLE_SOURCES | {"model"}  # type: ignore[operator]
            )

    def test_reviewed_grounded_fact_requires_reviewed_provenance(self) -> None:
        reviewed_only = ProductEvidenceProfileV2(
            False,
            frozenset(
                {
                    ProductEvidenceFactV2(
                        ProductEvidenceDimension.CAPACITY, REVIEWED_SOURCES
                    ),
                    ProductEvidenceFactV2(
                        ProductEvidenceDimension.INTERFACE, REVIEWED_SOURCES
                    ),
                }
            ),
        )
        # No provenance: unsupported -> fail closed.
        with pytest.raises(ValueError):
            derive_product_evidence_quality(reviewed_only, NO_CTX)
        # Customer retrieval can never ground a fact -> fail closed.
        with pytest.raises(ValueError):
            derive_product_evidence_quality(reviewed_only, CUSTOMER_CTX)
        # Reviewed product provenances support it (still LIMITED: no
        # usable title).
        assert (
            derive_product_evidence_quality(reviewed_only, PRODUCT_CTX)
            is ProductEvidenceQuality.LIMITED
        )
        assert (
            derive_product_evidence_quality(reviewed_only, RELATION_CTX)
            is ProductEvidenceQuality.LIMITED
        )

    def test_title_grounded_fact_requires_a_title(self) -> None:
        with pytest.raises(ValueError):
            ProductEvidenceProfileV2(
                False,
                frozenset(
                    {
                        ProductEvidenceFactV2(
                            ProductEvidenceDimension.CAPACITY, TITLE_SOURCES
                        )
                    }
                ),
            )

    def test_profile_state_consistency_fails_closed(self) -> None:
        u4 = _v2(title="Usable title without any MPN")
        # U4 was derived through the frozen usable-title gate: a profile
        # without a title contradicts the state.
        with pytest.raises(ValueError):
            derive_authority_tier(
                u4,
                None,
                NO_CTX,
                ProductEvidenceProfileV2(False, frozenset()),
            )
        # The default profile (no explicit evidence) is consistent: U4
        # carries its derived usable-title fact and still cannot reach
        # STRONG without explicit matched facts.
        default = derive_authority_tier(u4, None, NO_CTX)
        assert default.product_evidence_quality is ProductEvidenceQuality.LIMITED
        e2 = _v2(title=None)
        assert e2.substate is UnevaluableSubstateV2.E2_NO_CANDIDATE_EVIDENCE
        with pytest.raises(ValueError):
            derive_authority_tier(
                e2,
                None,
                NO_CTX,
                ProductEvidenceProfileV2(True, frozenset()),
            )

    def test_product_evidence_quality_is_never_model_derived(self) -> None:
        """The quality dimension is a pure function of the bounded
        profile + provenances: a LOW decision cannot raise it, and a HIGH
        one cannot lower it."""
        profile = _strong_profile()
        u4 = _v2(title="Usable title without any MPN")
        low = derive_authority_tier(u4, _match(V2Confidence.LOW), NO_CTX, profile)
        assert low.product_evidence_quality is ProductEvidenceQuality.STRONG
        assert low.tier is AuthorityTier.EXCLUDED_LOW_CONFIDENCE
        high = derive_authority_tier(u4, _match(V2Confidence.HIGH), NO_CTX, profile)
        assert high.product_evidence_quality is ProductEvidenceQuality.STRONG
        assert high.tier is AuthorityTier.AI_ASSISTED_COMPARABLE


# ===========================================================================
# G. UI display vocabulary (frozen for the future V2 UI)
# ===========================================================================


class TestUiVocabularyContract:
    def test_badge_concepts_are_frozen(self) -> None:
        # S2-A-FU1: the badge table is a frozen tuple of (tier, badge)
        # entries with a pure lookup; the exact badge strings are pinned.
        assert {
            tier for tier, _badge in AUTHORITY_TIER_BADGES
        } == set(AuthorityTier)
        assert len(AUTHORITY_TIER_BADGES) == 8
        expected = {
            AuthorityTier.MACHINE_VERIFIED: "Machine Verified",
            AuthorityTier.AI_ASSISTED_COMPARABLE: "AI-Assisted Comparable — not machine verified",
            AuthorityTier.NEEDS_REVIEW: "Needs Review — not verified",
            AuthorityTier.HUMAN_CONFIRMED: "Human Confirmed",
            AuthorityTier.HUMAN_REJECTED: "Human Rejected",
            AuthorityTier.HARD_CONFLICT: "Hard Conflict — excluded",
            AuthorityTier.EXCLUDED_LOW_CONFIDENCE: "Low Confidence",
            AuthorityTier.SEMANTIC_UNAVAILABLE: "AI Evidence Unavailable",
        }
        for tier, badge in AUTHORITY_TIER_BADGES:
            assert badge == expected[tier]
            assert authority_tier_badge(tier) == expected[tier]

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
