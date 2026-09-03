"""Contract tests for is_human_review_eligible_assessment.

PRODUCT-INTEL.HUMAN-REVIEW.

Validates the frozen FU3B human-review eligibility predicate against every
case defined in the architecture specification. This predicate MUST exactly
mirror frozen FU3B original-assessment eligibility and cannot drift.

TRUE cases:
- REJECTED + NO_EXPLICIT_MPN_EVIDENCE + TITLE_TEXT
- REJECTED + NO_EXPLICIT_MPN_EVIDENCE + SKU_FIELD
- REJECTED + PARTIAL_MPN_ONLY

FALSE cases:
- ACCEPTED
- UNDECIDED
- REJECTED + MPN_MISMATCH
- REJECTED + NO_EXPLICIT_MPN_EVIDENCE + NONE
- any other unsupported state
"""

from __future__ import annotations

from decimal import Decimal

import pytest

from product_intelligence.domain import ResearchRequest
from product_intelligence.domain.enums import (
    EvidenceDecision,
    IdentityMatchType,
)
from product_intelligence.research.matching import (
    EvidenceSource,
    IdentityRejectionReason,
    ListingIdentityAssessment,
    is_human_review_eligible_assessment,
)
from product_intelligence.research.normalization import (
    NormalizedAvailability,
    NormalizedCondition,
    NormalizedListingObservation,
)
from product_intelligence.research.listings import (
    ExtractionMethod,
    ListingObservation,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_observation(
    source_url: str = "https://example.com/1",
    mpn_text: str | None = None,
    sku_text: str | None = None,
    product_title: str | None = None,
) -> ListingObservation:
    return ListingObservation(
        source_url=source_url,
        extraction_method=ExtractionMethod.JSON_LD,
        manufacturer_part_number_text=mpn_text,
        sku_text=sku_text,
        product_title=product_title,
        price_text="99.99",
        currency_text="USD",
        condition_text="new",
    )


def _make_normalized(observation: ListingObservation) -> NormalizedListingObservation:
    return NormalizedListingObservation(
        observation=observation,
        price_amount=Decimal("99.99"),
        currency_code="USD",
        condition=NormalizedCondition.NEW,
        availability=NormalizedAvailability.UNKNOWN,
        seller_name="Test Seller",
        normalization_issues=(),
    )


def _make_assessment(
    normalized: NormalizedListingObservation,
    evidence_source: EvidenceSource,
    decision: EvidenceDecision,
    rejection_reason: IdentityRejectionReason | None,
    match_type: IdentityMatchType = IdentityMatchType.UNKNOWN,
    candidate_raw: str = "",
    candidate_compared: str = "",
    requested_mpn: str = "TEST-001",
) -> ListingIdentityAssessment:
    return ListingIdentityAssessment(
        normalized_listing=normalized,
        requested_part_number=requested_mpn,
        candidate_part_number_raw=candidate_raw,
        candidate_part_number_compared=candidate_compared,
        candidate_evidence_source=evidence_source,
        match_type=match_type,
        decision=decision,
        rejection_reason=rejection_reason,
    )


# ---------------------------------------------------------------------------
# TRUE cases — eligible
# ---------------------------------------------------------------------------


class TestEligibleTrueCases:
    """Cases that MUST return True."""

    def test_rejected_no_explicit_mpn_title_text(self) -> None:
        """REJECTED + NO_EXPLICIT_MPN_EVIDENCE + TITLE_TEXT is eligible."""
        obs = _make_observation(
            mpn_text="",
            sku_text=None,
            product_title="Product for TEST-001",
        )
        norm = _make_normalized(obs)
        assessment = _make_assessment(
            normalized=norm,
            evidence_source=EvidenceSource.TITLE_TEXT,
            decision=EvidenceDecision.REJECTED,
            rejection_reason=IdentityRejectionReason.NO_EXPLICIT_MPN_EVIDENCE,
            candidate_raw="TEST-001",
            candidate_compared="TEST-001",
        )
        assert is_human_review_eligible_assessment(assessment) is True

    def test_rejected_no_explicit_mpn_sku_field(self) -> None:
        """REJECTED + NO_EXPLICIT_MPN_EVIDENCE + SKU_FIELD is eligible."""
        obs = _make_observation(
            mpn_text=None,
            sku_text="TEST-SKU",
            product_title=None,
        )
        norm = _make_normalized(obs)
        assessment = _make_assessment(
            normalized=norm,
            evidence_source=EvidenceSource.SKU_FIELD,
            decision=EvidenceDecision.REJECTED,
            rejection_reason=IdentityRejectionReason.NO_EXPLICIT_MPN_EVIDENCE,
            candidate_raw="TEST-SKU",
            candidate_compared="TEST-SKU",
        )
        assert is_human_review_eligible_assessment(assessment) is True

    def test_rejected_partial_mpn_only(self) -> None:
        """REJECTED + PARTIAL_MPN_ONLY is eligible.

        This test constructs a valid PARTIAL assessment through the real
        matching function to prove the predicate works with real assessments.
        """
        from product_intelligence.research.matching import assess_listing_identity
        from product_intelligence.domain import ResearchRequest

        # PARTIAL: requested "TEST-001" vs candidate "TEST-001-EXT"
        # (prefix at boundary)
        obs = _make_observation(
            mpn_text="TEST-001-EXT",
            sku_text=None,
            product_title=None,
        )
        norm = _make_normalized(obs)
        request = ResearchRequest(
            manufacturer_part_number="TEST-001",
            description="Test product",
        )
        assessment = assess_listing_identity(request, norm)
        assert assessment.decision is EvidenceDecision.REJECTED
        assert assessment.rejection_reason is IdentityRejectionReason.PARTIAL_MPN_ONLY
        assert is_human_review_eligible_assessment(assessment) is True


# ---------------------------------------------------------------------------
# FALSE cases — not eligible
# ---------------------------------------------------------------------------


class TestNotEligibleFalseCases:
    """Cases that MUST return False."""

    def test_accepted(self) -> None:
        """ACCEPTED is NOT eligible for human review."""
        from product_intelligence.research.matching import assess_listing_identity
        from product_intelligence.domain import ResearchRequest

        obs = _make_observation(mpn_text="TEST-001", product_title=None)
        norm = _make_normalized(obs)
        request = ResearchRequest(
            manufacturer_part_number="TEST-001",
            description="Test product",
        )
        assessment = assess_listing_identity(request, norm)
        assert assessment.decision is EvidenceDecision.ACCEPTED
        assert is_human_review_eligible_assessment(assessment) is False

    def test_undecided(self) -> None:
        """UNDECIDED is NOT eligible."""
        obs = _make_observation(mpn_text=None, sku_text=None, product_title=None)
        norm = _make_normalized(obs)
        assessment = _make_assessment(
            normalized=norm,
            evidence_source=EvidenceSource.NONE,
            decision=EvidenceDecision.UNDECIDED,
            rejection_reason=IdentityRejectionReason.NO_REQUESTED_MPN,
            requested_mpn="",
        )
        assert is_human_review_eligible_assessment(assessment) is False

    def test_rejected_mpn_mismatch(self) -> None:
        """REJECTED + MPN_MISMATCH is NOT eligible."""
        from product_intelligence.research.matching import assess_listing_identity
        from product_intelligence.domain import ResearchRequest

        obs = _make_observation(mpn_text="WRONG-MPN", product_title=None)
        norm = _make_normalized(obs)
        request = ResearchRequest(
            manufacturer_part_number="TEST-001",
            description="Test product",
        )
        assessment = assess_listing_identity(request, norm)
        assert assessment.decision is EvidenceDecision.REJECTED
        assert assessment.rejection_reason is IdentityRejectionReason.MPN_MISMATCH
        assert is_human_review_eligible_assessment(assessment) is False

    def test_rejected_no_explicit_mpn_none(self) -> None:
        """REJECTED + NO_EXPLICIT_MPN_EVIDENCE + NONE is NOT eligible.

        NONE evidence source means no usable identifier was found at all,
        so there's nothing for semantic evaluation to work with.
        """
        from product_intelligence.research.matching import assess_listing_identity
        from product_intelligence.domain import ResearchRequest

        obs = _make_observation(mpn_text=None, sku_text=None, product_title=None)
        norm = _make_normalized(obs)
        request = ResearchRequest(
            manufacturer_part_number="TEST-001",
            description="Test product",
        )
        assessment = assess_listing_identity(request, norm)
        assert assessment.decision is EvidenceDecision.REJECTED
        assert assessment.rejection_reason is IdentityRejectionReason.NO_EXPLICIT_MPN_EVIDENCE
        assert assessment.candidate_evidence_source is EvidenceSource.NONE
        assert is_human_review_eligible_assessment(assessment) is False

    def test_rejected_no_explicit_mpn_explicit_mpn_field(self) -> None:
        """REJECTED + NO_EXPLICIT_MPN_EVIDENCE + EXPLICIT_MPN_FIELD is NOT eligible.

        Uses the REAL matcher. The observation publishes manufacturer_part_number_text
        = "mpn:" which the narrow wrapper cleanup strips to an empty compared
        identifier. The real matcher preserves EXPLICIT_MPN_FIELD as the source
        because the field existed, but rejects for NO_EXPLICIT_MPN_EVIDENCE
        because the compared value was empty after cleanup.

        EXPLICIT_MPN_FIELD source with NO_EXPLICIT_MPN_EVIDENCE reason is not
        semantic-eligible because there was no useful identifier to evaluate.
        """
        from product_intelligence.research.matching import assess_listing_identity

        # "mpn:" -> after cleanup "" -> empty compared -> NO_EXPLICIT_MPN_EVIDENCE
        obs = _make_observation(
            mpn_text="mpn:",
            sku_text=None,
            product_title=None,
        )
        norm = _make_normalized(obs)
        request = ResearchRequest(
            manufacturer_part_number="TEST-001",
            description="Test product",
        )
        assessment = assess_listing_identity(request, norm)

        # Prove the real matcher produced EXPLICIT_MPN_FIELD source
        assert assessment.candidate_evidence_source is EvidenceSource.EXPLICIT_MPN_FIELD
        assert assessment.decision is EvidenceDecision.REJECTED
        assert assessment.rejection_reason is IdentityRejectionReason.NO_EXPLICIT_MPN_EVIDENCE

        # EXPLICIT_MPN_FIELD with NO_EXPLICIT_MPN_EVIDENCE is NOT human-review eligible
        assert is_human_review_eligible_assessment(assessment) is False


# ---------------------------------------------------------------------------
# Parity regression: research predicate == execution predicate
# ---------------------------------------------------------------------------


class TestSemanticEligibilityParity:
    """Prove that the research-layer predicate and the execution-layer
    predicate agree for all frozen FU3B cases.

    is_human_review_eligible_assessment (research/matching.py) is the
    human-review authority predicate.
    _is_semantic_eligible (execution/semantic_integration.py) is the
    semantic evaluation eligibility predicate.

    For any assessment reachable through the frozen FU3B execution path,
    these two MUST return the same boolean. The human-review predicate
    mirrors semantic eligibility because only semantically-eligible
    assessments can appear as AiAssistedMatchResult.original_assessment.
    """

    def test_eligible_rejected_no_explicit_mpn_title_text_parity(self) -> None:
        """TITLE_TEXT evidence: both predicates must return True."""
        from product_intelligence.execution.semantic_integration import (
            _is_semantic_eligible,
        )
        from product_intelligence.research.matching import assess_listing_identity

        obs = _make_observation(
            mpn_text="",
            sku_text=None,
            product_title="Product for TEST-001",
        )
        norm = _make_normalized(obs)
        request = ResearchRequest(
            manufacturer_part_number="TEST-001",
            description="Test product",
        )
        assessment = assess_listing_identity(request, norm)
        assert is_human_review_eligible_assessment(assessment) == _is_semantic_eligible(assessment)
        assert is_human_review_eligible_assessment(assessment) is True

    def test_eligible_rejected_no_explicit_mpn_sku_field_parity(self) -> None:
        """SKU_FIELD evidence: both predicates must return True."""
        from product_intelligence.execution.semantic_integration import (
            _is_semantic_eligible,
        )
        from product_intelligence.research.matching import assess_listing_identity

        obs = _make_observation(
            mpn_text=None,
            sku_text="TEST-SKU",
            product_title=None,
        )
        norm = _make_normalized(obs)
        request = ResearchRequest(
            manufacturer_part_number="TEST-001",
            description="Test product",
        )
        assessment = assess_listing_identity(request, norm)
        assert is_human_review_eligible_assessment(assessment) == _is_semantic_eligible(assessment)
        assert is_human_review_eligible_assessment(assessment) is True

    def test_eligible_rejected_partial_mpn_only_parity(self) -> None:
        """PARTIAL_MPN_ONLY: both predicates must return True."""
        from product_intelligence.execution.semantic_integration import (
            _is_semantic_eligible,
        )
        from product_intelligence.research.matching import assess_listing_identity

        obs = _make_observation(
            mpn_text="TEST-001-EXT",
            sku_text=None,
            product_title=None,
        )
        norm = _make_normalized(obs)
        request = ResearchRequest(
            manufacturer_part_number="TEST-001",
            description="Test product",
        )
        assessment = assess_listing_identity(request, norm)
        assert is_human_review_eligible_assessment(assessment) == _is_semantic_eligible(assessment)
        assert is_human_review_eligible_assessment(assessment) is True

    def test_not_eligible_accepted_parity(self) -> None:
        """ACCEPTED: both predicates must return False."""
        from product_intelligence.execution.semantic_integration import (
            _is_semantic_eligible,
        )
        from product_intelligence.research.matching import assess_listing_identity

        obs = _make_observation(
            mpn_text="TEST-001",
            sku_text=None,
            product_title=None,
        )
        norm = _make_normalized(obs)
        request = ResearchRequest(
            manufacturer_part_number="TEST-001",
            description="Test product",
        )
        assessment = assess_listing_identity(request, norm)
        assert is_human_review_eligible_assessment(assessment) == _is_semantic_eligible(assessment)
        assert is_human_review_eligible_assessment(assessment) is False

    def test_not_eligible_rejected_mpn_mismatch_parity(self) -> None:
        """MPN_MISMATCH: both predicates must return False."""
        from product_intelligence.execution.semantic_integration import (
            _is_semantic_eligible,
        )
        from product_intelligence.research.matching import assess_listing_identity

        obs = _make_observation(
            mpn_text="WRONG-MPN",
            sku_text=None,
            product_title=None,
        )
        norm = _make_normalized(obs)
        request = ResearchRequest(
            manufacturer_part_number="TEST-001",
            description="Test product",
        )
        assessment = assess_listing_identity(request, norm)
        assert is_human_review_eligible_assessment(assessment) == _is_semantic_eligible(assessment)
        assert is_human_review_eligible_assessment(assessment) is False

    def test_not_eligible_rejected_no_explicit_mpn_none_parity(self) -> None:
        """NO_EXPLICIT_MPN_EVIDENCE + NONE: both predicates must return False."""
        from product_intelligence.execution.semantic_integration import (
            _is_semantic_eligible,
        )
        from product_intelligence.research.matching import assess_listing_identity

        obs = _make_observation(
            mpn_text=None,
            sku_text=None,
            product_title=None,
        )
        norm = _make_normalized(obs)
        request = ResearchRequest(
            manufacturer_part_number="TEST-001",
            description="Test product",
        )
        assessment = assess_listing_identity(request, norm)
        assert is_human_review_eligible_assessment(assessment) == _is_semantic_eligible(assessment)
        assert is_human_review_eligible_assessment(assessment) is False

    def test_not_eligible_rejected_no_explicit_mpn_explicit_mpn_field_parity(
        self,
    ) -> None:
        """NO_EXPLICIT_MPN_EVIDENCE + EXPLICIT_MPN_FIELD: both must return False."""
        from product_intelligence.execution.semantic_integration import (
            _is_semantic_eligible,
        )
        from product_intelligence.research.matching import assess_listing_identity

        # "mpn:" -> after cleanup "" -> NO_EXPLICIT_MPN_EVIDENCE + EXPLICIT_MPN_FIELD
        obs = _make_observation(
            mpn_text="mpn:",
            sku_text=None,
            product_title=None,
        )
        norm = _make_normalized(obs)
        request = ResearchRequest(
            manufacturer_part_number="TEST-001",
            description="Test product",
        )
        assessment = assess_listing_identity(request, norm)
        assert is_human_review_eligible_assessment(assessment) == _is_semantic_eligible(assessment)
        assert is_human_review_eligible_assessment(assessment) is False
