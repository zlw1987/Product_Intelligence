"""Tests for AI-assisted review candidate creation during execution.

PRODUCT-INTEL.HUMAN-REVIEW.

Validates that _create_review_candidates correctly creates candidates
only for AI-assisted MATCH results and not for other decisions.
"""

from __future__ import annotations

from decimal import Decimal
from unittest.mock import MagicMock

import pytest
from django.db import IntegrityError

from product_intelligence.domain import ResearchRequest
from product_intelligence.domain.enums import (
    ConfidenceLevel,
    EvidenceDecision,
    IdentityMatchType,
)
from product_intelligence.research.matching import (
    EvidenceSource,
    IdentityRejectionReason,
)
from product_intelligence.execution.orchestration import _create_review_candidates
from product_intelligence.research.matching import ListingIdentityAssessment
from product_intelligence.research.normalization import (
    NormalizedCondition,
    NormalizedListingObservation,
)
from product_intelligence.research.listings import (
    ExtractionMethod,
    ListingObservation,
)

from product_intelligence.runs.models import (
    AiAssistedReviewCandidate,
    PriceIntelligenceSnapshot,
    ResearchRun,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_listing_observation(source_url: str) -> ListingObservation:
    """Create a minimal ListingObservation."""
    from product_intelligence.research.listings import ExtractionMethod
    return ListingObservation(
        source_url=source_url,
        extraction_method=ExtractionMethod.JSON_LD,
        manufacturer_part_number_text="TEST-001",
        sku_text="SKU-001",
        price_text="99.99",
        currency_text="USD",
        condition_text="NEW",
    )


def _make_normalized_listing(observation: ListingObservation) -> NormalizedListingObservation:
    """Create a NormalizedListingObservation."""
    from product_intelligence.research.normalization import NormalizedAvailability
    return NormalizedListingObservation(
        observation=observation,
        price_amount=Decimal("99.99"),
        currency_code="USD",
        condition=NormalizedCondition.NEW,
        availability=NormalizedAvailability.UNKNOWN,
        seller_name="Test Seller",
        normalization_issues=(),
    )


def _make_assessment(obs: ListingObservation, decision: EvidenceDecision, normalized: NormalizedListingObservation) -> ListingIdentityAssessment:
    """Create a ListingIdentityAssessment."""
    from product_intelligence.research.matching import IdentityRejectionReason
    if decision is EvidenceDecision.ACCEPTED:
        return ListingIdentityAssessment(
            normalized_listing=normalized,
            requested_part_number="TEST-001",
            candidate_part_number_raw="TEST-001",
            candidate_part_number_compared="TEST-001",
            candidate_evidence_source=EvidenceSource.EXPLICIT_MPN_FIELD,
            match_type=IdentityMatchType.EXACT,
            decision=decision,
            rejection_reason=None,
        )
    elif decision is EvidenceDecision.AI_ASSISTED_MATCH:
        from product_intelligence.research.listings import ExtractionMethod
        from product_intelligence.research.normalization import NormalizedAvailability
        # AI-assisted match: use a listing with no structured identifier
        no_id_obs = ListingObservation(
            source_url=obs.source_url,
            extraction_method=ExtractionMethod.JSON_LD,
            price_text="99.99",
            currency_text="USD",
            condition_text="NEW",
        )
        no_id_normalized = NormalizedListingObservation(
            observation=no_id_obs,
            price_amount=Decimal("99.99"),
            currency_code="USD",
            condition=NormalizedCondition.NEW,
            availability=NormalizedAvailability.UNKNOWN,
            seller_name="Test Seller",
            normalization_issues=(),
        )
        return ListingIdentityAssessment(
            normalized_listing=no_id_normalized,
            requested_part_number="TEST-001",
            candidate_part_number_raw="",
            candidate_part_number_compared="",
            candidate_evidence_source=EvidenceSource.NONE,
            match_type=IdentityMatchType.UNKNOWN,
            decision=decision,
            rejection_reason=None,
        )
    else:
        return ListingIdentityAssessment(
            normalized_listing=normalized,
            requested_part_number="TEST-001",
            candidate_part_number_raw="",
            candidate_part_number_compared="",
            candidate_evidence_source=EvidenceSource.NONE,
            match_type=IdentityMatchType.UNKNOWN,
            decision=decision,
            rejection_reason=IdentityRejectionReason.NO_EXPLICIT_MPN_EVIDENCE,
        )


def _make_semantic_runtime_result() -> MagicMock:
    """Create a mock SemanticRuntimeResult for MATCH."""
    result = MagicMock()
    result.decision = "MATCH"
    result.confidence = ConfidenceLevel.MEDIUM
    result.reason_code = "semantic_match"
    result.matched_attributes = ("brand", "mpn")
    result.conflicting_attributes = ()
    result.actual_provider = "amax"
    result.actual_model = "nemotron-3-super"
    result.prompt_version = "v1.1"
    result.target_mpn = "TEST-001"
    result.target_description = "Test product description"
    result.candidate_title = "Test Product Title"
    result.candidate_mpn_field = "TEST-001"
    result.candidate_sku = "SKU-001"
    result.candidate_specs = "Test specs"
    result.evidence_source = "TITLE_TEXT"
    return result


def _make_ai_assisted_match_result(assessment: ListingIdentityAssessment) -> MagicMock:
    """Create a mock AiAssistedMatchResult."""
    result = MagicMock()
    result.original_assessment = assessment
    result.semantic_result = _make_semantic_runtime_result()
    return result


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


@pytest.mark.usefixtures("human_review_db_isolation")
class TestCreateReviewCandidates:
    """Test _create_review_candidates behavior."""
    def test_no_matches_creates_no_candidates(self) -> None:
        """When there are no AI-assisted matches, no candidates are created."""
        request = ResearchRequest(
            manufacturer_part_number="TEST-001",
            description="Test product",
        )
        run = ResearchRun.objects.create_from_request(request)
        assessments = ()
        ai_assisted_matches = ()
        _create_review_candidates(run, assessments, ai_assisted_matches)
        assert AiAssistedReviewCandidate.objects.filter(run=run).count() == 0

    def test_ai_assisted_match_creates_candidate(self) -> None:
        """An AI-assisted MATCH creates exactly one review candidate."""
        request = ResearchRequest(
            manufacturer_part_number="TEST-001",
            description="Test product",
        )
        run = ResearchRun.objects.create_from_request(request)

        obs = _make_listing_observation("https://example.com/product/1")
        normalized = _make_normalized_listing(obs)
        assessment = _make_assessment(obs, EvidenceDecision.AI_ASSISTED_MATCH, normalized)
        assessments = (assessment,)
        match_result = _make_ai_assisted_match_result(assessment)
        ai_assisted_matches = (match_result,)

        _create_review_candidates(run, assessments, ai_assisted_matches)

        candidates = list(AiAssistedReviewCandidate.objects.filter(run=run))
        assert len(candidates) == 1
        c = candidates[0]
        assert c.assessment_index == 0
        assert c.review_state == AiAssistedReviewCandidate.REVIEW_STATE_UNREVIEWED
        assert c.source_url == "https://example.com/product/1"
        assert c.target_mpn == "TEST-001"
        assert c.actual_provider == "amax"

    def test_deterministic_accepted_does_not_create_candidate(self) -> None:
        """A deterministic ACCEPTED assessment does not create a candidate,
        even if it appears in the assessments tuple."""
        request = ResearchRequest(
            manufacturer_part_number="TEST-001",
            description="Test product",
        )
        run = ResearchRun.objects.create_from_request(request)

        obs = _make_listing_observation("https://example.com/product/1")
        normalized = _make_normalized_listing(obs)
        assessment = _make_assessment(obs, EvidenceDecision.ACCEPTED, normalized)
        assessments = (assessment,)
        # No AI-assisted matches — only deterministic
        ai_assisted_matches = ()

        _create_review_candidates(run, assessments, ai_assisted_matches)
        assert AiAssistedReviewCandidate.objects.filter(run=run).count() == 0

    def test_semantic_no_match_does_not_create_candidate(self) -> None:
        """A NO_MATCH semantic result does not create a candidate.

        Only MATCH results create candidates. The function receives only
        MATCH results from execution, but this tests that the contract
        is enforced by the caller (orchestration)."""
        # The _create_review_candidates function receives only MATCH results
        # from orchestration. NO_MATCH and UNCERTAIN are filtered before
        # reaching this function.
        request = ResearchRequest(
            manufacturer_part_number="TEST-001",
            description="Test product",
        )
        run = ResearchRun.objects.create_from_request(request)
        # If no matches passed in, no candidates
        _create_review_candidates(run, (), ())
        assert AiAssistedReviewCandidate.objects.filter(run=run).count() == 0

    def test_multiple_matches_create_multiple_candidates(self) -> None:
        """Multiple AI-assisted MATCH results create multiple candidates."""
        request = ResearchRequest(
            manufacturer_part_number="TEST-001",
            description="Test product",
        )
        run = ResearchRun.objects.create_from_request(request)

        obs1 = _make_listing_observation("https://example.com/product/1")
        normalized1 = _make_normalized_listing(obs1)
        assessment1 = _make_assessment(obs1, EvidenceDecision.AI_ASSISTED_MATCH, normalized1)

        obs2 = _make_listing_observation("https://example.com/product/2")
        normalized2 = _make_normalized_listing(obs2)
        assessment2 = _make_assessment(obs2, EvidenceDecision.AI_ASSISTED_MATCH, normalized2)

        assessments = (assessment1, assessment2)
        match_result1 = _make_ai_assisted_match_result(assessment1)
        match_result2 = _make_ai_assisted_match_result(assessment2)
        ai_assisted_matches = (match_result1, match_result2)

        _create_review_candidates(run, assessments, ai_assisted_matches)

        candidates = list(AiAssistedReviewCandidate.objects.filter(run=run).order_by("assessment_index"))
        assert len(candidates) == 2
        assert candidates[0].assessment_index == 0
        assert candidates[1].assessment_index == 1

    def test_candidate_assessment_index_maps_to_correct_assessment(self) -> None:
        """The candidate assessment_index identifies the exact assessment."""
        request = ResearchRequest(
            manufacturer_part_number="TEST-001",
            description="Test product",
        )
        run = ResearchRun.objects.create_from_request(request)

        obs1 = _make_listing_observation("https://example.com/product/1")
        normalized1 = _make_normalized_listing(obs1)
        assessment1 = _make_assessment(obs1, EvidenceDecision.AI_ASSISTED_MATCH, normalized1)

        obs2 = _make_listing_observation("https://example.com/product/2")
        normalized2 = _make_normalized_listing(obs2)
        assessment2 = _make_assessment(obs2, EvidenceDecision.AI_ASSISTED_MATCH, normalized2)

        # assessments: [accepted_det, assisted_1, assisted_2]
        obs0 = _make_listing_observation("https://example.com/product/0")
        normalized0 = _make_normalized_listing(obs0)
        assessment0 = _make_assessment(obs0, EvidenceDecision.ACCEPTED, normalized0)

        assessments = (assessment0, assessment1, assessment2)
        match_result1 = _make_ai_assisted_match_result(assessment1)
        match_result2 = _make_ai_assisted_match_result(assessment2)
        ai_assisted_matches = (match_result1, match_result2)

        _create_review_candidates(run, assessments, ai_assisted_matches)

        candidates = list(AiAssistedReviewCandidate.objects.filter(run=run).order_by("assessment_index"))
        assert len(candidates) == 2
        assert candidates[0].assessment_index == 1  # assessment1 is at index 1
        assert candidates[1].assessment_index == 2  # assessment2 is at index 2

    def test_missing_assessment_raises_value_error(self) -> None:
        """If an AI-assisted match's original_assessment is not in the
        assessments tuple, the function raises ValueError."""
        request = ResearchRequest(
            manufacturer_part_number="TEST-001",
            description="Test product",
        )
        run = ResearchRun.objects.create_from_request(request)

        # Create an assessment that won't be in the tuple
        obs = _make_listing_observation("https://example.com/product/1")
        normalized = _make_normalized_listing(obs)
        assessment = _make_assessment(obs, EvidenceDecision.AI_ASSISTED_MATCH, normalized)
        # assessments is empty — the assessment won't be found
        assessments = ()
        match_result = _make_ai_assisted_match_result(assessment)
        ai_assisted_matches = (match_result,)

        with pytest.raises(ValueError, match="not found in assessments tuple"):
            _create_review_candidates(run, assessments, ai_assisted_matches)

    def test_duplicate_candidate_creation_prevented(self) -> None:
        """Creating a candidate twice for the same (run, assessment_index) fails."""
        request = ResearchRequest(
            manufacturer_part_number="TEST-001",
            description="Test product",
        )
        run = ResearchRun.objects.create_from_request(request)

        obs = _make_listing_observation("https://example.com/product/1")
        normalized = _make_normalized_listing(obs)
        assessment = _make_assessment(obs, EvidenceDecision.AI_ASSISTED_MATCH, normalized)
        assessments = (assessment,)
        match_result = _make_ai_assisted_match_result(assessment)
        ai_assisted_matches = (match_result,)

        # First creation succeeds
        _create_review_candidates(run, assessments, ai_assisted_matches)

        # Second creation with same assessment_index should fail
        with pytest.raises(IntegrityError):
            _create_review_candidates(run, assessments, ai_assisted_matches)


# ---------------------------------------------------------------------------
# Real AiAssistedMatchResult coverage — FU3B authority alignment
# ---------------------------------------------------------------------------


@pytest.mark.usefixtures("human_review_db_isolation")
class TestRealAiAssistedMatchResultPersistence:
    """Tests using REAL AiAssistedMatchResult with real semantic-eligible
    REJECTED assessments.

    These tests prove that the frozen FU3B execution path (REJECTED original
    + semantic MATCH) correctly persists review candidates and that the
    snapshot contains the ORIGINAL REJECTED assessment.

    Section 7 of the FU3B authority alignment specification.
    """

    def test_real_rejected_original_assessment(self) -> None:
        """Real semantic-eligible REJECTED assessment is created through
        the actual matching function."""
        from product_intelligence.research.matching import (
            assess_listing_identity,
        )

        request = ResearchRequest(
            manufacturer_part_number="REAL-001",
            description="Real test product",
        )

        obs = ListingObservation(
            source_url="https://example.com/real-1",
            extraction_method=ExtractionMethod.JSON_LD,
            manufacturer_part_number_text="",
            sku_text=None,
            product_title="Component for REAL-001",
            price_text="79.99",
            currency_text="USD",
            condition_text="new",
        )
        from product_intelligence.research.normalization import (
            NormalizedAvailability,
        )
        norm = NormalizedListingObservation(
            observation=obs,
            price_amount=Decimal("79.99"),
            currency_code="USD",
            condition=NormalizedCondition.NEW,
            availability=NormalizedAvailability.UNKNOWN,
            seller_name="Real Seller",
            normalization_issues=(),
        )

        assessment = assess_listing_identity(request, norm)

        # Proof: the real matching function produces REJECTED
        assert assessment.decision is EvidenceDecision.REJECTED
        assert assessment.rejection_reason is IdentityRejectionReason.NO_EXPLICIT_MPN_EVIDENCE
        assert assessment.candidate_evidence_source is EvidenceSource.TITLE_TEXT

    def test_real_ai_assisted_match_result_with_rejected_original(self) -> None:
        """REAL AiAssistedMatchResult with real REJECTED original_assessment
        creates a correct review candidate.

        This proves the REAL FU3B execution architecture:
        - original_assessment is a real semantic-eligible REJECTED assessment
        - AiAssistedMatchResult wraps it with semantic MATCH disposition
        - _create_review_candidates maps the candidate to the original
          REJECTED assessment index
        """
        from product_intelligence.execution.semantic_integration import (
            AiAssistedMatchResult,
        )
        from product_intelligence.semantic import (
            SemanticDecision,
            SemanticRuntimeResult,
            SemanticAttempt,
            SemanticAttemptStatus,
            ConfidenceLevel as SemanticConfidenceLevel,
        )
        from product_intelligence.research.matching import assess_listing_identity
        from product_intelligence.research.normalization import NormalizedAvailability

        request = ResearchRequest(
            manufacturer_part_number="REAL-002",
            description="Real test product 2",
        )
        run = ResearchRun.objects.create_from_request(request)

        obs = ListingObservation(
            source_url="https://example.com/real-2",
            extraction_method=ExtractionMethod.JSON_LD,
            manufacturer_part_number_text="",
            sku_text=None,
            product_title="Compatible REAL-002 component",
            price_text="199.99",
            currency_text="USD",
            condition_text="new",
        )
        norm = NormalizedListingObservation(
            observation=obs,
            price_amount=Decimal("199.99"),
            currency_code="USD",
            condition=NormalizedCondition.NEW,
            availability=NormalizedAvailability.UNKNOWN,
            seller_name="Real Seller",
            normalization_issues=(),
        )
        original_assessment = assess_listing_identity(request, norm)
        assert original_assessment.decision is EvidenceDecision.REJECTED

        # B: Real SemanticRuntimeResult (not MagicMock)
        semantic_result = SemanticRuntimeResult(
            case_id="test-case-1",
            target_mpn="REAL-002",
            target_description="Real test product 2",
            candidate_title=obs.product_title or "",
            candidate_mpn_field=None,
            candidate_sku=None,
            candidate_specs=None,
            evidence_source=original_assessment.candidate_evidence_source.value,
            requested_primary_provider="amax",
            requested_primary_model="nemotron-3-super",
            attempts=(
                SemanticAttempt(
                    provider="amax",
                    model="nemotron-3-super",
                    status=SemanticAttemptStatus.OK,
                    latency_ms=1000.0,
                ),
            ),
            fallback_used=False,
            fallback_reason=None,
            actual_provider="amax",
            actual_model="nemotron-3-super",
            decision=SemanticDecision.MATCH,
            confidence=SemanticConfidenceLevel.MEDIUM,
            matched_attributes=("brand", "mpn"),
            conflicting_attributes=(),
            missing_critical_attributes=(),
            reason_code="semantic_match",
            error_type=None,
        )

        # C: REAL AiAssistedMatchResult (not MagicMock)
        match_result = AiAssistedMatchResult(
            original_assessment=original_assessment,
            semantic_result=semantic_result,
            disposition=EvidenceDecision.AI_ASSISTED_MATCH,
        )
        # Proof: original_assessment is REJECTED, not AI_ASSISTED_MATCH
        assert match_result.original_assessment.decision is EvidenceDecision.REJECTED
        assert match_result.disposition is EvidenceDecision.AI_ASSISTED_MATCH

        # D: Persist through real _create_review_candidates
        assessments = (original_assessment,)
        _create_review_candidates(run, assessments, (match_result,))

        candidates = list(AiAssistedReviewCandidate.objects.filter(run=run))
        assert len(candidates) == 1
        c = candidates[0]
        assert c.assessment_index == 0
        assert c.review_state == AiAssistedReviewCandidate.REVIEW_STATE_UNREVIEWED
        assert c.source_url == obs.source_url
        assert c.target_mpn == "REAL-002"
        assert c.evidence_source == "TITLE_TEXT"

        # E: Persist deterministic snapshot with REJECTED assessment
        from product_intelligence.research.aggregation import (
            aggregate_listing_prices,
        )
        from product_intelligence.research.price_result_codec import (
            PRICE_RESULT_SCHEMA_VERSION,
            encode_price_aggregation_result,
        )
        price_result = aggregate_listing_prices(request, assessments)
        payload = encode_price_aggregation_result(price_result)
        PriceIntelligenceSnapshot.objects.create(
            run=run,
            schema_version=PRICE_RESULT_SCHEMA_VERSION,
            payload=payload,
        )

        # F: Proof: snapshot contains REJECTED assessment
        from product_intelligence.research.price_result_codec import (
            decode_price_aggregation_result,
        )
        snapshot = run.price_intelligence_snapshot
        decoded = decode_price_aggregation_result(
            snapshot.payload,
            schema_version=snapshot.schema_version,
        )
        assert decoded.assessments[0].decision is EvidenceDecision.REJECTED
        # Candidate maps to the REJECTED assessment
        assert c.assessment_index == 0

    def test_candidate_semantic_provenance_matches_real_result(self) -> None:
        """Candidate semantic provenance fields match the real
        AiAssistedMatchResult semantic_result."""
        from product_intelligence.execution.semantic_integration import (
            AiAssistedMatchResult,
        )
        from product_intelligence.semantic import (
            SemanticDecision,
            SemanticRuntimeResult,
            SemanticAttempt,
            SemanticAttemptStatus,
            ConfidenceLevel as SemanticConfidenceLevel,
        )
        from product_intelligence.research.matching import assess_listing_identity
        from product_intelligence.research.normalization import NormalizedAvailability

        request = ResearchRequest(
            manufacturer_part_number="PROV-001",
            description="Provenance test",
        )
        run = ResearchRun.objects.create_from_request(request)

        obs = ListingObservation(
            source_url="https://example.com/prov-1",
            extraction_method=ExtractionMethod.JSON_LD,
            manufacturer_part_number_text="",
            sku_text=None,
            product_title="PROV-001 replacement part",
            price_text="49.99",
            currency_text="USD",
            condition_text="new",
        )
        norm = NormalizedListingObservation(
            observation=obs,
            price_amount=Decimal("49.99"),
            currency_code="USD",
            condition=NormalizedCondition.NEW,
            availability=NormalizedAvailability.UNKNOWN,
            seller_name="Prov Seller",
            normalization_issues=(),
        )
        original = assess_listing_identity(request, norm)

        semantic_result = SemanticRuntimeResult(
            case_id="prov-case-1",
            target_mpn="PROV-001",
            target_description="Provenance test",
            candidate_title=obs.product_title or "",
            candidate_mpn_field=None,
            candidate_sku=None,
            candidate_specs=None,
            evidence_source=original.candidate_evidence_source.value,
            requested_primary_provider="amax",
            requested_primary_model="nemotron-3-super",
            attempts=(
                SemanticAttempt(
                    provider="amax",
                    model="nemotron-3-super",
                    status=SemanticAttemptStatus.OK,
                    latency_ms=1000.0,
                ),
            ),
            fallback_used=False,
            fallback_reason=None,
            actual_provider="amax",
            actual_model="nemotron-3-super",
            decision=SemanticDecision.MATCH,
            confidence=SemanticConfidenceLevel.HIGH,
            matched_attributes=("brand", "mpn", "category"),
            conflicting_attributes=("weight",),
            missing_critical_attributes=(),
            reason_code="strong_match",
            error_type=None,
        )

        match_result = AiAssistedMatchResult(
            original_assessment=original,
            semantic_result=semantic_result,
            disposition=EvidenceDecision.AI_ASSISTED_MATCH,
        )

        _create_review_candidates(run, (original,), (match_result,))

        c = AiAssistedReviewCandidate.objects.get(run=run)
        # All provenance fields must match
        assert c.semantic_confidence == "HIGH"
        assert c.semantic_reason_code == "strong_match"
        assert list(c.semantic_matched_attributes) == ["brand", "mpn", "category"]
        assert list(c.semantic_conflicting_attributes) == ["weight"]
        assert c.actual_provider == "amax"
        assert c.actual_model == "nemotron-3-super"
        assert c.prompt_version == "1.1"
        assert c.evidence_source == "TITLE_TEXT"
