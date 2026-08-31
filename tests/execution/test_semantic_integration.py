"""Execution-integration safety tests for semantic integration (PRODUCT-INTEL.FU3B).

This test suite proves, offline and with counting fakes, that:
1. Deterministic ACCEPTED never triggers semantic calls
2. REJECTED/MPN_MISMATCH never triggers semantic calls
3. REJECTED/NO_EXPLICIT_MPN_EVIDENCE+TITLE_TEXT triggers semantic calls
4. REJECTED/NO_EXPLICIT_MPN_EVIDENCE+SKU_FIELD triggers semantic calls
5. REJECTED/PARTIAL_MPN_ONLY triggers semantic calls
6. REJECTED/NO_EXPLICIT_MPN_EVIDENCE+NONE does NOT trigger semantic calls
7. AI_ASSISTED_MATCH never enters 4A aggregation
8. Semantic failure does not fail execution
9. Programming exceptions propagate
10. Lazy runtime construction
11. Safe bounded provenance is preserved
12. AiAssistedMatchResult self-validates
13. Real deterministic matcher produces expected states

NO LIVE SEMANTIC CALLS. All tests use FakeSemanticModelTransport.
"""

from __future__ import annotations

from decimal import Decimal
from typing import TYPE_CHECKING
from unittest.mock import MagicMock, patch

import pytest

from product_intelligence.domain import ResearchRequest
from product_intelligence.domain.enums import (
    EvidenceDecision,
    IdentityMatchType,
    ResearchRunState,
)
from product_intelligence.domain.evidence import (
    ExecutionDetailCode,
    ExecutionOutcome,
    ExecutionStage,
)
import product_intelligence.execution.semantic_integration
from product_intelligence.execution.semantic_integration import (
    AiAssistedMatchResult,
    _is_semantic_eligible,
    _has_usable_evidence,
    evaluate_semantic_matches,
)
from product_intelligence.research.aggregation import (
    PriceAggregationExclusionReason,
    aggregate_listing_prices,
)
from product_intelligence.research.listings import (
    ExtractionMethod,
    ListingObservation,
)
from product_intelligence.research.matching import (
    EvidenceSource,
    IdentityRejectionReason,
    ListingIdentityAssessment,
    assess_listing_identity,
)
from product_intelligence.research.normalization import (
    NormalizedAvailability,
    NormalizedCondition,
    NormalizedListingObservation,
)
from product_intelligence.semantic import (
    ConfidenceLevel,
    SemanticDecision,
    SemanticRuntime,
    SemanticRuntimeConfig,
    SemanticRuntimeResult,
)
from product_intelligence.semantic.transport import FakeSemanticModelTransport

from product_intelligence.execution.evidence_writer import (
    read_execution_evidence,
)
if TYPE_CHECKING:
    from product_intelligence.execution.evidence_writer import (
        ExecutionEvidenceWriter,
    )
    from product_intelligence.execution.orchestration import (
        ExecutionError,
    )


def _make_fresh_evidence_writer() -> ExecutionEvidenceWriter:
    """Create an evidence writer backed by a real ResearchRun (DB)."""
    from product_intelligence.runs.models import ResearchRun
    request = ResearchRequest("TEST-MPN", "Test product description")
    run = ResearchRun.objects.create_from_request(request)
    from product_intelligence.execution.evidence_writer import (
        ExecutionEvidenceWriter,
    )
    return ExecutionEvidenceWriter(run)


def _make_observation(
    *,
    title: str | None = "Test Product",
    mpn: str | None = None,
    sku: str | None = None,
    brand: str | None = None,
    price: str | None = "100.00",
    currency: str | None = "USD",
    condition: str | None = "new",
) -> ListingObservation:
    """Build a ListingObservation for testing."""
    return ListingObservation(
        source_url="https://example.com/test-product",
        extraction_method=ExtractionMethod.JSON_LD,
        product_title=title,
        manufacturer_part_number_text=mpn,
        sku_text=sku,
        brand_text=brand,
        price_text=price,
        currency_text=currency,
        condition_text=condition,
    )


def _make_normalized(observation: ListingObservation) -> NormalizedListingObservation:
    """Build a NormalizedListingObservation from an observation."""
    price_amount = None
    if observation.price_text:
        try:
            price_amount = Decimal(observation.price_text)
        except Exception:
            pass
    return NormalizedListingObservation(
        observation=observation,
        price_amount=price_amount,
        currency_code=observation.currency_text,
        availability=NormalizedAvailability.UNKNOWN,
        condition=NormalizedCondition.NEW,
        seller_name=None,
        normalization_issues=(),
    )


def _make_fake_runtime(
    responses: dict[str, str] | None = None,
    case_ids: tuple[str, ...] = (),
    provider_reported_model: str = "nemotron-3-super",
) -> SemanticRuntime:
    """Create a fake SemanticRuntime for testing."""
    transport = FakeSemanticModelTransport(
        responses=responses or {},
        case_ids=case_ids,
        provider_reported_model=provider_reported_model,
    )
    config = SemanticRuntimeConfig()
    return SemanticRuntime(config=config, primary_transport=transport)


def _match_response(decision: SemanticDecision) -> str:
    """Build a valid JSON response string for FakeSemanticModelTransport."""
    return (
        '{'
        f'"decision": "{decision.value}", '
        '"confidence": "HIGH", '
        '"matched_attributes": ["brand"], '
        '"conflicting_attributes": [], '
        '"missing_critical_attributes": [], '
        '"reason_code": "test_match"'
        '}'
    )


def _failure_result() -> SemanticRuntimeResult:
    """Build a failure SemanticRuntimeResult for testing.

    Uses a two-attempt result (primary CONNECTION_ERROR -> fallback
    MODEL_NOT_FOUND) so the self-validating result is routing-consistent.
    """
    from product_intelligence.semantic.runtime import (
        SemanticAttempt,
        SemanticAttemptStatus,
        SemanticRuntimeErrorType,
        SemanticRuntimeFallbackReason,
    )
    primary_attempt = SemanticAttempt(
        provider="amax",
        model="nemotron-3-super",
        status=SemanticAttemptStatus.CONNECTION_ERROR,
        latency_ms=30000,
    )
    fallback_attempt = SemanticAttempt(
        provider="vllm-262k",
        model="Qwen3.6-27B-262K",
        status=SemanticAttemptStatus.MODEL_NOT_FOUND,
        latency_ms=5000,
    )
    return SemanticRuntimeResult(
        case_id="SMQ-0001",
        target_mpn="TEST-MPN",
        target_description="desc",
        candidate_title="title",
        candidate_mpn_field=None,
        candidate_sku=None,
        candidate_specs=None,
        evidence_source="UNKNOWN",
        requested_primary_provider="amax",
        requested_primary_model="nemotron-3-super",
        attempts=(primary_attempt, fallback_attempt),
        fallback_used=True,
        fallback_reason=SemanticRuntimeFallbackReason.CONNECTION_ERROR,
        actual_provider=None,
        actual_model=None,
        decision=None,
        confidence=None,
        matched_attributes=(),
        conflicting_attributes=(),
        missing_critical_attributes=(),
        reason_code=None,
        error_type=SemanticRuntimeErrorType.FALLBACK_MODEL_NOT_FOUND,
    )


# ================================================================
# Section 1: Critical real-source tests using actual matcher
# ================================================================


class TestRealMatcherSemanticEligibility:
    """Section 3: Real deterministic matcher produces expected states.

    These tests use assess_listing_identity() to produce actual assessments,
    then verify the semantic integration behaves correctly.
    """

    def test_exact_mpn_accepted_no_semantic(self) -> None:
        """A. Listing explicit MPN exact -> ACCEPTED -> semantic calls = 0."""
        observation = _make_observation(mpn="TEST-MPN", title="Test Product")
        norm = _make_normalized(observation)
        request = ResearchRequest("TEST-MPN", "Test product description")
        assessment = assess_listing_identity(request, norm)
        assert assessment.decision is EvidenceDecision.ACCEPTED
        assert assessment.candidate_evidence_source is EvidenceSource.EXPLICIT_MPN_FIELD
        assert _is_semantic_eligible(assessment) is False
        runtime = _make_fake_runtime()
        writer = _make_fresh_evidence_writer()
        results = evaluate_semantic_matches(request, [assessment], writer, runtime)
        assert runtime._primary_transport.call_count == 0
        assert len(results) == 0

    def test_mpn_mismatch_rejected_no_semantic(self) -> None:
        """B. Listing explicit MPN different -> REJECTED/MPN_MISMATCH -> 0 calls."""
        observation = _make_observation(mpn="DIFFERENT-MPN", title="Test Product")
        norm = _make_normalized(observation)
        request = ResearchRequest("TEST-MPN", "Test product description")
        assessment = assess_listing_identity(request, norm)
        assert assessment.decision is EvidenceDecision.REJECTED
        assert assessment.rejection_reason is IdentityRejectionReason.MPN_MISMATCH
        assert _is_semantic_eligible(assessment) is False
        runtime = _make_fake_runtime()
        writer = _make_fresh_evidence_writer()
        results = evaluate_semantic_matches(request, [assessment], writer, runtime)
        assert runtime._primary_transport.call_count == 0
        assert len(results) == 0

    def test_mpn_in_title_only_semantic_eligible(self) -> None:
        """C. Target MPN in title -> REJECTED/NO_EXPLICIT_MPN+TITLE_TEXT -> 1 call."""
        observation = _make_observation(
            title="TEST-MPN Compatible Product",
            mpn=None,
        )
        norm = _make_normalized(observation)
        request = ResearchRequest("TEST-MPN", "Test product description")
        assessment = assess_listing_identity(request, norm)
        assert assessment.decision is EvidenceDecision.REJECTED
        assert assessment.rejection_reason is IdentityRejectionReason.NO_EXPLICIT_MPN_EVIDENCE
        assert assessment.candidate_evidence_source is EvidenceSource.TITLE_TEXT
        assert _is_semantic_eligible(assessment) is True
        assert _has_usable_evidence(assessment) is True
        import hashlib
        url_hash = hashlib.sha256("https://example.com/test-product".encode()).hexdigest()[:8]
        case_id = f"candidate-{url_hash}-0"
        responses = {case_id: _match_response(SemanticDecision.MATCH)}
        runtime = _make_fake_runtime(responses=responses, case_ids=(case_id,))
        writer = _make_fresh_evidence_writer()
        results = evaluate_semantic_matches(request, [assessment], writer, runtime)
        assert runtime._primary_transport.call_count == 1
        assert len(results) == 1
        assert results[0].disposition is EvidenceDecision.AI_ASSISTED_MATCH

    def test_sku_field_no_explicit_mpn_semantic_eligible(self) -> None:
        """D. SKU evidence but no explicit MPN -> REJECTED/NO_EXPLICIT_MPN+SKU_FIELD."""
        observation = _make_observation(
            title="Test Product",
            sku="TEST-MPN-SKU",
            mpn=None,
        )
        norm = _make_normalized(observation)
        request = ResearchRequest("TEST-MPN", "Test product description")
        assessment = assess_listing_identity(request, norm)
        assert assessment.decision is EvidenceDecision.REJECTED
        assert assessment.rejection_reason is IdentityRejectionReason.NO_EXPLICIT_MPN_EVIDENCE
        assert assessment.candidate_evidence_source is EvidenceSource.SKU_FIELD
        assert _is_semantic_eligible(assessment) is True
        assert _has_usable_evidence(assessment) is True
        import hashlib
        url_hash = hashlib.sha256("https://example.com/test-product".encode()).hexdigest()[:8]
        case_id = f"candidate-{url_hash}-0"
        responses = {case_id: _match_response(SemanticDecision.MATCH)}
        runtime = _make_fake_runtime(responses=responses, case_ids=(case_id,))
        writer = _make_fresh_evidence_writer()
        results = evaluate_semantic_matches(request, [assessment], writer, runtime)
        assert runtime._primary_transport.call_count == 1
        assert len(results) == 1

    def test_partial_mpn_semantic_eligible(self) -> None:
        """E. Explicit partial MPN -> REJECTED/PARTIAL_MPN_ONLY -> 1 call."""
        # Partial: the MPN prefix matches but suffix differs
        observation = _make_observation(
            title="Test Product",
            mpn="TEST",  # partial match of "TEST-MPN"
        )
        norm = _make_normalized(observation)
        request = ResearchRequest("TEST-MPN", "Test product description")
        assessment = assess_listing_identity(request, norm)
        assert assessment.decision is EvidenceDecision.REJECTED
        assert assessment.rejection_reason is IdentityRejectionReason.PARTIAL_MPN_ONLY
        assert _is_semantic_eligible(assessment) is True
        import hashlib
        url_hash = hashlib.sha256("https://example.com/test-product".encode()).hexdigest()[:8]
        case_id = f"candidate-{url_hash}-0"
        responses = {case_id: _match_response(SemanticDecision.MATCH)}
        runtime = _make_fake_runtime(responses=responses, case_ids=(case_id,))
        writer = _make_fresh_evidence_writer()
        results = evaluate_semantic_matches(request, [assessment], writer, runtime)
        assert runtime._primary_transport.call_count == 1

    def test_no_evidence_source_none_no_semantic(self) -> None:
        """F. No identifier evidence / source NONE -> semantic calls = 0."""
        observation = _make_observation(
            title="Generic Product",
            mpn=None,
            sku=None,
            brand=None,
        )
        norm = _make_normalized(observation)
        request = ResearchRequest("TEST-MPN", "Test product description")
        assessment = assess_listing_identity(request, norm)
        assert assessment.decision is EvidenceDecision.REJECTED
        assert assessment.rejection_reason is IdentityRejectionReason.NO_EXPLICIT_MPN_EVIDENCE
        assert assessment.candidate_evidence_source is EvidenceSource.NONE
        assert _is_semantic_eligible(assessment) is False
        runtime = _make_fake_runtime()
        writer = _make_fresh_evidence_writer()
        results = evaluate_semantic_matches(request, [assessment], writer, runtime)
        assert runtime._primary_transport.call_count == 0
        assert len(results) == 0


# ================================================================
# Section 2: Eligibility boundary tests
# ================================================================


class TestSemanticEligibility:
    """Tests for _is_semantic_eligible against all deterministic states."""

    def test_accepted_not_eligible(self) -> None:
        obs = _make_observation(mpn="TEST-MPN")
        norm = _make_normalized(obs)
        request = ResearchRequest("TEST-MPN", "desc")
        assessment = assess_listing_identity(request, norm)
        assert assessment.decision is EvidenceDecision.ACCEPTED
        assert _is_semantic_eligible(assessment) is False

    def test_rejected_mpn_mismatch_not_eligible(self) -> None:
        obs = _make_observation(mpn="DIFFERENT-MPN")
        norm = _make_normalized(obs)
        request = ResearchRequest("TEST-MPN", "desc")
        assessment = assess_listing_identity(request, norm)
        assert assessment.rejection_reason is IdentityRejectionReason.MPN_MISMATCH
        assert _is_semantic_eligible(assessment) is False

    def test_rejected_no_mpn_evidence_title_eligible(self) -> None:
        obs = _make_observation(title="TEST-MPN Product", mpn=None)
        norm = _make_normalized(obs)
        request = ResearchRequest("TEST-MPN", "desc")
        assessment = assess_listing_identity(request, norm)
        assert assessment.candidate_evidence_source is EvidenceSource.TITLE_TEXT
        assert _is_semantic_eligible(assessment) is True

    def test_rejected_no_mpn_evidence_sku_eligible(self) -> None:
        obs = _make_observation(title="Test", sku="TEST-SKU", mpn=None)
        norm = _make_normalized(obs)
        request = ResearchRequest("TEST-MPN", "desc")
        assessment = assess_listing_identity(request, norm)
        assert assessment.candidate_evidence_source is EvidenceSource.SKU_FIELD
        assert _is_semantic_eligible(assessment) is True

    def test_rejected_no_mpn_evidence_none_not_eligible(self) -> None:
        obs = _make_observation(title="Generic Product", mpn=None, sku=None)
        norm = _make_normalized(obs)
        request = ResearchRequest("TEST-MPN", "desc")
        assessment = assess_listing_identity(request, norm)
        assert assessment.candidate_evidence_source is EvidenceSource.NONE
        assert _is_semantic_eligible(assessment) is False

    def test_rejected_partial_mpn_eligible(self) -> None:
        obs = _make_observation(title="Test", mpn="TEST")
        norm = _make_normalized(obs)
        request = ResearchRequest("TEST-MPN", "desc")
        assessment = assess_listing_identity(request, norm)
        assert assessment.rejection_reason is IdentityRejectionReason.PARTIAL_MPN_ONLY
        assert _is_semantic_eligible(assessment) is True

    def test_undecided_not_eligible(self) -> None:
        obs = _make_observation(title="Test", brand="Brand")
        norm = _make_normalized(obs)
        request = ResearchRequest("", "description only")
        assessment = assess_listing_identity(request, norm)
        assert assessment.decision is EvidenceDecision.UNDECIDED
        assert _is_semantic_eligible(assessment) is False


# ================================================================
# Section 3: Programming exception propagation
# ================================================================


class TestProgrammingExceptionPropagation:
    """Section 4: Programming exceptions propagate, not swallowed."""

    def test_runtime_error_propagates(self) -> None:
        """Injected RuntimeError propagates, no fake SEMANTIC_UNAVAILABLE."""
        runtime = MagicMock(spec=SemanticRuntime)
        runtime.evaluate.side_effect = RuntimeError("sentinel")
        obs = _make_observation(title="TEST-MPN Product", mpn=None)
        norm = _make_normalized(obs)
        request = ResearchRequest("TEST-MPN", "desc")
        assessment = assess_listing_identity(request, norm)
        writer = _make_fresh_evidence_writer()
        with pytest.raises(RuntimeError, match="sentinel"):
            evaluate_semantic_matches(request, [assessment], writer, runtime)

    def test_type_error_propagates(self) -> None:
        """TypeError from runtime.evaluate propagates."""
        runtime = MagicMock(spec=SemanticRuntime)
        runtime.evaluate.side_effect = TypeError("bad arg")
        obs = _make_observation(title="TEST-MPN Product", mpn=None)
        norm = _make_normalized(obs)
        request = ResearchRequest("TEST-MPN", "desc")
        assessment = assess_listing_identity(request, norm)
        writer = _make_fresh_evidence_writer()
        with pytest.raises(TypeError, match="bad arg"):
            evaluate_semantic_matches(request, [assessment], writer, runtime)


# ================================================================
# Section 4: Lazy runtime construction
# ================================================================


class TestLazyRuntimeConstruction:
    """Section 5: get_default_runtime called only when needed."""

    def test_no_eligible_no_runtime_call(self) -> None:
        """Zero eligible candidates -> get_default_runtime call count == 0."""
        obs = _make_observation(mpn="TEST-MPN")
        norm = _make_normalized(obs)
        request = ResearchRequest("TEST-MPN", "desc")
        assessment = assess_listing_identity(request, norm)
        assert assessment.decision is EvidenceDecision.ACCEPTED
        writer = _make_fresh_evidence_writer()
        with patch(
            "product_intelligence.execution.semantic_integration.get_default_runtime"
        ) as mock_get:
            mock_get.side_effect = RuntimeError("should not be called")
            results = evaluate_semantic_matches(request, [assessment], writer)
            assert mock_get.call_count == 0
            assert len(results) == 0

    def test_eligible_triggers_runtime_once(self) -> None:
        """One eligible candidate -> get_default_runtime called once."""
        obs = _make_observation(title="TEST-MPN Product", mpn=None)
        norm = _make_normalized(obs)
        request = ResearchRequest("TEST-MPN", "desc")
        assessment = assess_listing_identity(request, norm)
        writer = _make_fresh_evidence_writer()
        import hashlib
        url_hash = hashlib.sha256("https://example.com/test-product".encode()).hexdigest()[:8]
        case_id = f"candidate-{url_hash}-0"
        fake_runtime = _make_fake_runtime(
            responses={case_id: _match_response(SemanticDecision.MATCH)},
            case_ids=(case_id,),
        )
        with patch(
            "product_intelligence.execution.semantic_integration.get_default_runtime"
        ) as mock_get:
            mock_get.return_value = fake_runtime
            results = evaluate_semantic_matches(request, [assessment], writer)
            assert mock_get.call_count == 1
            assert fake_runtime._primary_transport.call_count == 1

    def test_ineligible_candidates_no_runtime(self) -> None:
        """All candidates resolved/ineligible -> runtime never constructed."""
        obs1 = _make_observation(mpn="TEST-MPN")
        obs2 = _make_observation(mpn="DIFFERENT-MPN")
        norm1 = _make_normalized(obs1)
        norm2 = _make_normalized(obs2)
        request = ResearchRequest("TEST-MPN", "desc")
        assessments = [
            assess_listing_identity(request, norm1),
            assess_listing_identity(request, norm2),
        ]
        writer = _make_fresh_evidence_writer()
        with patch(
            "product_intelligence.execution.semantic_integration.get_default_runtime"
        ) as mock_get:
            mock_get.side_effect = RuntimeError("must not be called")
            results = evaluate_semantic_matches(request, assessments, writer)
            assert mock_get.call_count == 0
            assert len(results) == 0


# ================================================================
# Section 5: AI-assisted results separation
# ================================================================


class TestAggregationCorrectness:
    """Section 8: Aggregation correctness with deterministic ACCEPTED assessments.

    The real 4A safety contract (AI-assisted exclusion) is proved by
    TestRealOrchestrationIntegration.test_mixed_deterministic_and_ai_assisted_price_run.
    These tests verify the aggregation primitive itself works correctly.
    """

    def test_accepted_assessments_produce_correct_bucket_stats(self) -> None:
        """Three ACCEPTED assessments with different prices produce correct bucket."""
        request = ResearchRequest("TEST-MPN", "Test product")
        accepted_prices = []
        for i, price in enumerate([Decimal("90"), Decimal("100"), Decimal("110")]):
            obs = _make_observation(
                title=f"Product {i}", mpn="TEST-MPN", price=str(price), currency="USD"
            )
            norm = _make_normalized(obs)
            assessment = ListingIdentityAssessment(
                normalized_listing=norm, requested_part_number="TEST-MPN",
                candidate_part_number_raw="TEST-MPN", candidate_part_number_compared="TEST-MPN",
                candidate_evidence_source=EvidenceSource.EXPLICIT_MPN_FIELD,
                match_type=IdentityMatchType.EXACT, decision=EvidenceDecision.ACCEPTED, rejection_reason=None,
            )
            accepted_prices.append(assessment)

        all_assessments = tuple(accepted_prices)
        result = aggregate_listing_prices(request, all_assessments)
        assert len(result.buckets) == 1
        bucket = result.buckets[0]
        assert bucket.count == 3
        assert bucket.low == Decimal("90")
        assert bucket.median == Decimal("100")
        assert bucket.high == Decimal("110")

    def test_single_accepted_assessment_produces_one_bucket(self) -> None:
        """One ACCEPTED assessment produces exactly one bucket with count 1."""
        request = ResearchRequest("TEST-MPN", "Test product")
        obs = _make_observation(title="Product", mpn="TEST-MPN", price="100", currency="USD")
        norm = _make_normalized(obs)
        assessment = ListingIdentityAssessment(
            normalized_listing=norm, requested_part_number="TEST-MPN",
            candidate_part_number_raw="TEST-MPN", candidate_part_number_compared="TEST-MPN",
            candidate_evidence_source=EvidenceSource.EXPLICIT_MPN_FIELD,
            match_type=IdentityMatchType.EXACT, decision=EvidenceDecision.ACCEPTED, rejection_reason=None,
        )
        result = aggregate_listing_prices(request, (assessment,))
        assert len(result.buckets) == 1
        assert result.buckets[0].count == 1


# ================================================================
# Section 6: AiAssistedMatchResult self-validation
# ================================================================


class TestAiAssistedMatchResultValidation:
    """Adversarial constructor tests for AiAssistedMatchResult."""
    # ---------------------------------------------------------------

    def _make_semantic_eligible_assessment(
        self, *, sku: str | None = None
    ) -> ListingIdentityAssessment:
        """Create a semantic-eligible assessment for provenance testing.

        By default uses TITLE_TEXT evidence source (no SKU).
        Pass sku= to create a SKU_FIELD evidence source assessment.
        """
        obs = _make_observation(
            title="TEST-MPN Compatible Product",
            mpn=None,
            sku=sku,
        )
        norm = _make_normalized(obs)
        request = ResearchRequest("TEST-MPN", "Test description")
        assessment = assess_listing_identity(request, norm)
        # Verify it is semantic-eligible
        assert assessment.decision is EvidenceDecision.REJECTED
        assert assessment.rejection_reason is IdentityRejectionReason.NO_EXPLICIT_MPN_EVIDENCE
        expected_source = EvidenceSource.SKU_FIELD if sku else EvidenceSource.TITLE_TEXT
        assert assessment.candidate_evidence_source is expected_source
        return assessment

    def _make_provenanced_result(
        self,
        assessment: ListingIdentityAssessment,
        *,
        target_mpn: str | None = None,
        candidate_title: str | None = None,
        candidate_mpn_field: str | None = None,
        candidate_sku: str | None = None,
        evidence_source: str | None = None,
    ) -> SemanticRuntimeResult:
        """Build a SemanticRuntimeResult matching the assessment's provenance,
        with optional field overrides for adversarial testing."""
        from product_intelligence.semantic.runtime import (
            SemanticAttempt,
            SemanticAttemptStatus,
        )
        observation = assessment.normalized_listing.observation
        if target_mpn is None:
            target_mpn = assessment.requested_part_number
        if candidate_title is None:
            candidate_title = observation.product_title or ""
        if candidate_mpn_field is None:
            candidate_mpn_field = (
                observation.manufacturer_part_number_text
                if observation.manufacturer_part_number_text
                else None
            )
        if candidate_sku is None:
            candidate_sku = (
                observation.sku_text
                if observation.sku_text
                else None
            )
        if evidence_source is None:
            evidence_source = assessment.candidate_evidence_source.value
        attempt = SemanticAttempt(
            provider="amax",
            model="nemotron-3-super",
            status=SemanticAttemptStatus.OK,
            latency_ms=100,
        )
        return SemanticRuntimeResult(
            case_id="provenance-test",
            target_mpn=target_mpn,
            target_description="test desc",
            candidate_title=candidate_title,
            candidate_mpn_field=candidate_mpn_field,
            candidate_sku=candidate_sku,
            candidate_specs=None,
            evidence_source=evidence_source,
            requested_primary_provider="amax",
            requested_primary_model="nemotron-3-super",
            attempts=(attempt,),
            fallback_used=False,
            fallback_reason=None,
            actual_provider="amax",
            actual_model="nemotron-3-super",
            decision=SemanticDecision.MATCH,
            confidence=ConfidenceLevel.HIGH,
            matched_attributes=("description",),
            conflicting_attributes=(),
            missing_critical_attributes=(),
            reason_code="test_match",
            error_type=None,
        )

    def test_provenance_target_mpn_mismatch_rejected(self) -> None:
        """Mismatched target_mpn is rejected at construction."""
        assessment = self._make_semantic_eligible_assessment()
        result = self._make_provenanced_result(
            assessment,
            target_mpn="WRONG-MPN",
        )
        with pytest.raises(ValueError, match="Provenance mismatch"):
            AiAssistedMatchResult(
                original_assessment=assessment,
                semantic_result=result,
                disposition=EvidenceDecision.AI_ASSISTED_MATCH,
            )

    def test_provenance_candidate_title_mismatch_rejected(self) -> None:
        """Mismatched candidate_title is rejected at construction."""
        assessment = self._make_semantic_eligible_assessment()
        result = self._make_provenanced_result(
            assessment,
            candidate_title="Wrong Title",
        )
        with pytest.raises(ValueError, match="Provenance mismatch"):
            AiAssistedMatchResult(
                original_assessment=assessment,
                semantic_result=result,
                disposition=EvidenceDecision.AI_ASSISTED_MATCH,
            )

    def test_provenance_candidate_mpn_field_mismatch_rejected(self) -> None:
        """Mismatched candidate_mpn_field is rejected at construction."""
        assessment = self._make_semantic_eligible_assessment()
        # Assessment has mpn=None; result claims mpn_field="SOME-MPN"
        result = self._make_provenanced_result(
            assessment,
            candidate_mpn_field="SOME-MPN",
        )
        with pytest.raises(ValueError, match="Provenance mismatch"):
            AiAssistedMatchResult(
                original_assessment=assessment,
                semantic_result=result,
                disposition=EvidenceDecision.AI_ASSISTED_MATCH,
            )

    def test_provenance_candidate_sku_mismatch_rejected(self) -> None:
        """Mismatched candidate_sku is rejected at construction."""
        assessment = self._make_semantic_eligible_assessment(sku="SKU-001")
        # Assessment has sku="SKU-001"; result claims sku="WRONG-SKU"
        result = self._make_provenanced_result(
            assessment,
            candidate_sku="WRONG-SKU",
        )
        with pytest.raises(ValueError, match="Provenance mismatch"):
            AiAssistedMatchResult(
                original_assessment=assessment,
                semantic_result=result,
                disposition=EvidenceDecision.AI_ASSISTED_MATCH,
            )

    def test_provenance_evidence_source_mismatch_rejected(self) -> None:
        """Mismatched evidence_source is rejected at construction."""
        assessment = self._make_semantic_eligible_assessment()
        # Assessment has evidence_source=TITLE_TEXT; result claims SKU_FIELD
        assert assessment.candidate_evidence_source is EvidenceSource.TITLE_TEXT
        result = self._make_provenanced_result(
            assessment,
            evidence_source="SKU_FIELD",
        )
        with pytest.raises(ValueError, match="Provenance mismatch"):
            AiAssistedMatchResult(
                original_assessment=assessment,
                semantic_result=result,
                disposition=EvidenceDecision.AI_ASSISTED_MATCH,
            )

    def test_provenance_matching_result_constructs(self) -> None:
        """A legitimately provenanced result constructs successfully."""
        assessment = self._make_semantic_eligible_assessment()
        result = self._make_provenanced_result(assessment)
        # All provenance fields match the assessment
        match = AiAssistedMatchResult(
            original_assessment=assessment,
            semantic_result=result,
            disposition=EvidenceDecision.AI_ASSISTED_MATCH,
        )
        assert match.disposition is EvidenceDecision.AI_ASSISTED_MATCH
        assert match.original_assessment is assessment

    def _make_semantic_match_result(self) -> SemanticRuntimeResult:
        from product_intelligence.semantic.runtime import (
            SemanticAttempt,
            SemanticAttemptStatus,
            SemanticRuntimeErrorType,
        )
        attempt = SemanticAttempt(
            provider="amax",
            model="nemotron-3-super",
            status=SemanticAttemptStatus.OK,
            latency_ms=100,
        )
        return SemanticRuntimeResult(
            case_id="SMQ-0001",
            target_mpn="TEST-MPN",
            target_description="desc",
            candidate_title="title",
            candidate_mpn_field=None,
            candidate_sku=None,
            candidate_specs=None,
            evidence_source="UNKNOWN",
            requested_primary_provider="amax",
            requested_primary_model="nemotron-3-super",
            attempts=(attempt,),
            fallback_used=False,
            fallback_reason=None,
            actual_provider="amax",
            actual_model="nemotron-3-super",
            decision=SemanticDecision.MATCH,
            confidence=ConfidenceLevel.HIGH,
            matched_attributes=("brand",),
            conflicting_attributes=(),
            missing_critical_attributes=(),
            reason_code="test_match",
            error_type=None,
        )

    def test_accepted_assessment_rejected_by_constructor(self) -> None:
        """Cannot construct with ACCEPTED assessment."""
        obs = _make_observation(mpn="TEST-MPN")
        norm = _make_normalized(obs)
        request = ResearchRequest("TEST-MPN", "desc")
        assessment = assess_listing_identity(request, norm)
        assert assessment.decision is EvidenceDecision.ACCEPTED
        semantic_result = self._make_semantic_match_result()
        with pytest.raises(ValueError, match="ACCEPTED"):
            AiAssistedMatchResult(
                original_assessment=assessment,
                semantic_result=semantic_result,
                disposition=EvidenceDecision.AI_ASSISTED_MATCH,
            )

    def test_mpn_mismatch_rejected_by_constructor(self) -> None:
        """Cannot construct with MPN_MISMATCH REJECTED assessment."""
        obs = _make_observation(mpn="DIFFERENT-MPN")
        norm = _make_normalized(obs)
        request = ResearchRequest("TEST-MPN", "desc")
        assessment = assess_listing_identity(request, norm)
        assert assessment.rejection_reason is IdentityRejectionReason.MPN_MISMATCH
        semantic_result = self._make_semantic_match_result()
        with pytest.raises(ValueError, match="MPN_MISMATCH"):
            AiAssistedMatchResult(
                original_assessment=assessment,
                semantic_result=semantic_result,
                disposition=EvidenceDecision.AI_ASSISTED_MATCH,
            )

    def test_error_type_rejected_by_constructor(self) -> None:
        """Cannot construct with error semantic result."""
        obs = _make_observation(title="TEST-MPN Product", mpn=None)
        norm = _make_normalized(obs)
        request = ResearchRequest("TEST-MPN", "desc")
        assessment = assess_listing_identity(request, norm)
        error_result = _failure_result()
        with pytest.raises(ValueError, match="error_type"):
            AiAssistedMatchResult(
                original_assessment=assessment,
                semantic_result=error_result,
                disposition=EvidenceDecision.AI_ASSISTED_MATCH,
            )

    def test_wrong_disposition_rejected(self) -> None:
        """Cannot construct with non-AI_ASSISTED_MATCH disposition."""
        obs = _make_observation(title="TEST-MPN Product", mpn=None)
        norm = _make_normalized(obs)
        request = ResearchRequest("TEST-MPN", "desc")
        assessment = assess_listing_identity(request, norm)
        semantic_result = self._make_semantic_match_result()
        with pytest.raises(ValueError, match="AI_ASSISTED_MATCH"):
            AiAssistedMatchResult(
                original_assessment=assessment,
                semantic_result=semantic_result,
                disposition=EvidenceDecision.ACCEPTED,
            )

    def test_wrong_semantic_decision_rejected(self) -> None:
        """Cannot construct with NO_MATCH semantic decision."""
        from product_intelligence.semantic.runtime import (
            SemanticAttempt,
            SemanticAttemptStatus,
            SemanticRuntimeErrorType,
        )
        obs = _make_observation(title="TEST-MPN Product", mpn=None)
        norm = _make_normalized(obs)
        request = ResearchRequest("TEST-MPN", "desc")
        assessment = assess_listing_identity(request, norm)
        attempt = SemanticAttempt(
            provider="amax",
            model="nemotron-3-super",
            status=SemanticAttemptStatus.OK,
            latency_ms=100,
        )
        no_match_result = SemanticRuntimeResult(
            case_id="SMQ-0001",
            target_mpn="TEST-MPN",
            target_description="desc",
            candidate_title="title",
            candidate_mpn_field=None,
            candidate_sku=None,
            candidate_specs=None,
            evidence_source="UNKNOWN",
            requested_primary_provider="amax",
            requested_primary_model="nemotron-3-super",
            attempts=(attempt,),
            fallback_used=False,
            fallback_reason=None,
            actual_provider="amax",
            actual_model="nemotron-3-super",
            decision=SemanticDecision.NO_MATCH,
            confidence=ConfidenceLevel.HIGH,
            matched_attributes=(),
            conflicting_attributes=(),
            missing_critical_attributes=(),
            reason_code="DIFFERENT_PRODUCT",
            error_type=None,
        )
        with pytest.raises(ValueError, match="SemanticDecision.MATCH"):
            AiAssistedMatchResult(
                original_assessment=assessment,
                semantic_result=no_match_result,
                disposition=EvidenceDecision.AI_ASSISTED_MATCH,
            )

    def test_none_source_rejected_by_constructor(self) -> None:
        """Cannot construct with NO_EXPLICIT_MPN_EVIDENCE + NONE source."""
        # Manually create assessment with NONE source that is REJECTED
        obs = _make_observation(title="Generic Product")
        norm = _make_normalized(obs)
        assessment = ListingIdentityAssessment(
            normalized_listing=norm,
            requested_part_number="TEST-MPN",
            candidate_part_number_raw="",
            candidate_part_number_compared="",
            candidate_evidence_source=EvidenceSource.NONE,
            match_type=IdentityMatchType.UNKNOWN,
            decision=EvidenceDecision.REJECTED,
            rejection_reason=IdentityRejectionReason.NO_EXPLICIT_MPN_EVIDENCE,
        )
        semantic_result = self._make_semantic_match_result()
        with pytest.raises(ValueError, match="not semantic-eligible"):
            AiAssistedMatchResult(
                original_assessment=assessment,
                semantic_result=semantic_result,
                disposition=EvidenceDecision.AI_ASSISTED_MATCH,
            )


# ================================================================
# Section 7: Semantic failure handling
# ================================================================


class TestSemanticFailureHandling:
    """Semantic failure does not fail execution."""

    def test_semantic_failure_keeps_candidate_unresolved(self) -> None:
        """Semantic runtime failure result keeps candidate unresolved."""
        obs = _make_observation(title="TEST-MPN Product", mpn=None)
        norm = _make_normalized(obs)
        request = ResearchRequest("TEST-MPN", "desc")
        assessment = assess_listing_identity(request, norm)
        runtime = MagicMock(spec=SemanticRuntime)
        runtime.evaluate.return_value = _failure_result()
        writer = _make_fresh_evidence_writer()
        results = evaluate_semantic_matches(request, [assessment], writer, runtime)
        assert len(results) == 0
        assert runtime.evaluate.call_count == 1

    def test_semantic_no_match_excluded(self) -> None:
        """Semantic NO_MATCH excludes from AI-assisted results."""
        obs = _make_observation(title="TEST-MPN Product", mpn=None)
        norm = _make_normalized(obs)
        request = ResearchRequest("TEST-MPN", "desc")
        assessment = assess_listing_identity(request, norm)
        import hashlib
        url_hash = hashlib.sha256("https://example.com/test-product".encode()).hexdigest()[:8]
        case_id = f"candidate-{url_hash}-0"
        responses = {case_id: _match_response(SemanticDecision.NO_MATCH)}
        runtime = _make_fake_runtime(responses=responses, case_ids=(case_id,))
        writer = _make_fresh_evidence_writer()
        results = evaluate_semantic_matches(request, [assessment], writer, runtime)
        assert runtime._primary_transport.call_count == 1
        assert len(results) == 0


# ================================================================
# Section 8: Multiple candidates
# ================================================================


class TestMultipleCandidates:
    """Multiple candidate semantic evaluation."""

    def test_mixed_eligibility_counts(self) -> None:
        """Only eligible candidates trigger semantic calls."""
        # Accepted: no semantic
        obs1 = _make_observation(title="P1", mpn="TEST-MPN")
        # MPN mismatch: no semantic
        obs2 = _make_observation(title="P2", mpn="DIFFERENT")
        # Title-only eligible: semantic
        obs3 = _make_observation(title="TEST-MPN Compatible", mpn=None)
        # NONE source: no semantic
        obs4 = _make_observation(title="Generic", mpn=None, sku=None)

        norms = [_make_normalized(o) for o in [obs1, obs2, obs3, obs4]]
        request = ResearchRequest("TEST-MPN", "desc")
        assessments = [assess_listing_identity(request, n) for n in norms]

        import hashlib
        url_hash = hashlib.sha256("https://example.com/test-product".encode()).hexdigest()[:8]
        case_id = f"candidate-{url_hash}-2"
        responses = {case_id: _match_response(SemanticDecision.MATCH)}
        runtime = _make_fake_runtime(responses=responses, case_ids=(case_id,))
        writer = _make_fresh_evidence_writer()
        results = evaluate_semantic_matches(request, assessments, writer, runtime)
        assert runtime._primary_transport.call_count == 1
        assert len(results) == 1


# ================================================================
# Section 9: Safe provenance
# ================================================================


class TestSafeProvenanceOnly:
    """No raw output/body/API key/CoT leakage."""

    def test_semantic_result_contains_no_raw_output(self) -> None:
        obs = _make_observation(title="TEST-MPN Product", mpn=None)
        norm = _make_normalized(obs)
        request = ResearchRequest("TEST-MPN", "Test product")
        assessment = assess_listing_identity(request, norm)
        import hashlib
        url_hash = hashlib.sha256("https://example.com/test-product".encode()).hexdigest()[:8]
        case_id = f"candidate-{url_hash}-0"
        responses = {case_id: _match_response(SemanticDecision.MATCH)}
        runtime = _make_fake_runtime(responses=responses, case_ids=(case_id,))
        writer = _make_fresh_evidence_writer()
        results = evaluate_semantic_matches(request, [assessment], writer, runtime)
        assert len(results) == 1
        result_dict = results[0].semantic_result.to_dict()
        assert "raw_output" not in result_dict
        assert "raw_response" not in result_dict
        assert "body" not in result_dict
        assert "api_key" not in result_dict
        assert "authorization" not in result_dict
        assert "decision" in result_dict
        assert "confidence" in result_dict


# ================================================================
# Section 10: Deterministic authority
# ================================================================


class TestDeterministicAuthority:
    """Deterministic result authority remains stronger."""

    def test_semantic_cannot_override_deterministic(self) -> None:
        obs1 = _make_observation(mpn="TEST-MPN", brand="Brand1")
        norm = _make_normalized(obs1)
        request = ResearchRequest("TEST-MPN", "Test product")
        assessment = assess_listing_identity(request, norm)
        assert assessment.decision is EvidenceDecision.ACCEPTED
        runtime = _make_fake_runtime()
        writer = _make_fresh_evidence_writer()
        results = evaluate_semantic_matches(request, [assessment], writer, runtime)
        assert runtime._primary_transport.call_count == 0
        assert len(results) == 0


# ================================================================
# Section 11: ExecutionResult ai_assisted_matches
# ================================================================


class TestExecutionResultAiAssisted:
    """ExecutionResult retains ai_assisted_matches tuple."""

    def test_ai_assisted_matches_property(self) -> None:
        from product_intelligence.execution.orchestration import ExecutionResult
        from product_intelligence.runs.models import ResearchRun
        req = ResearchRequest("TEST-MPN", "desc")
        run = ResearchRun.objects.create_from_request(req)
        result = ExecutionResult(
            run=run,
            snapshot=None,
            search_result_count=5,
            fetch_success_count=3,
            extract_observation_count=3,
            accepted_assessment_count=1,
            verification_status=None,
            price_buckets=1,
            ai_assisted_matches=(),
        )
        assert result.ai_assisted_match_count == 0
        assert isinstance(result.ai_assisted_matches, tuple)

    def test_backward_compat_match_count(self) -> None:
        """ai_assisted_match_count is a derived property."""
        from product_intelligence.execution.orchestration import ExecutionResult
        from product_intelligence.runs.models import ResearchRun
        req = ResearchRequest("TEST-MPN", "desc")
        run = ResearchRun.objects.create_from_request(req)
        result = ExecutionResult(
            run=run,
            snapshot=None,
            search_result_count=5,
            fetch_success_count=3,
            extract_observation_count=3,
            accepted_assessment_count=1,
            verification_status=None,
            price_buckets=1,
        )
        assert result.ai_assisted_match_count == 0
        # Verify it is a property not a stored field
        import inspect
        assert isinstance(
            type(result).__dict__.get("ai_assisted_match_count"), property
        )


# ================================================================
# Section 12: Persisted execution evidence for SEMANTIC stage
# ================================================================


class TestSemanticExecutionEvidence:
    """Section 9: Persisted evidence for SEMANTIC stage combinations."""

    def test_semantic_match_valid_evidence(self) -> None:
        """SEMANTIC/SUCCESS/SEMANTIC_MATCH is valid."""
        writer = _make_fresh_evidence_writer()
        record = writer.append_execution_attempt(
            stage=ExecutionStage.SEMANTIC,
            outcome=ExecutionOutcome.SUCCESS,
            candidate_url="https://example.com/test",
            detail_code=ExecutionDetailCode.for_semantic_match(),
        )
        assert record.stage == ExecutionStage.SEMANTIC.value
        assert record.outcome == ExecutionOutcome.SUCCESS.value
        assert record.detail_code == ExecutionDetailCode.SEMANTIC_MATCH.value

    def test_semantic_no_match_valid_evidence(self) -> None:
        """SEMANTIC/SUCCESS/SEMANTIC_NO_MATCH is valid."""
        writer = _make_fresh_evidence_writer()
        record = writer.append_execution_attempt(
            stage=ExecutionStage.SEMANTIC,
            outcome=ExecutionOutcome.SUCCESS,
            candidate_url="https://example.com/test",
            detail_code=ExecutionDetailCode.for_semantic_no_match(),
        )
        assert record.detail_code == ExecutionDetailCode.SEMANTIC_NO_MATCH.value

    def test_semantic_uncertain_valid_evidence(self) -> None:
        """SEMANTIC/SUCCESS/SEMANTIC_UNCERTAIN is valid."""
        writer = _make_fresh_evidence_writer()
        record = writer.append_execution_attempt(
            stage=ExecutionStage.SEMANTIC,
            outcome=ExecutionOutcome.SUCCESS,
            candidate_url="https://example.com/test",
            detail_code=ExecutionDetailCode.for_semantic_uncertain(),
        )
        assert record.detail_code == ExecutionDetailCode.SEMANTIC_UNCERTAIN.value

    def test_semantic_unavailable_valid_evidence(self) -> None:
        """SEMANTIC/FAILED/SEMANTIC_UNAVAILABLE is valid."""
        writer = _make_fresh_evidence_writer()
        record = writer.append_execution_attempt(
            stage=ExecutionStage.SEMANTIC,
            outcome=ExecutionOutcome.FAILED,
            candidate_url="https://example.com/test",
            detail_code=ExecutionDetailCode.for_semantic_unavailable(),
        )
        assert record.outcome == ExecutionOutcome.FAILED.value
        assert record.detail_code == ExecutionDetailCode.SEMANTIC_UNAVAILABLE.value

    def test_semantic_invalid_combination_fails(self) -> None:
        """SEMANTIC/SUCCESS with non-semantic detail code fails."""
        writer = _make_fresh_evidence_writer()
        with pytest.raises(ValueError, match="Invalid detail_code"):
            writer.append_execution_attempt(
                stage=ExecutionStage.SEMANTIC,
                outcome=ExecutionOutcome.SUCCESS,
                candidate_url="https://example.com/test",
                detail_code=ExecutionDetailCode.OK,
            )

    def test_semantic_failed_with_success_code_fails(self) -> None:
        """SEMANTIC/FAILED with SEMANTIC_MATCH fails (impossible)."""
        writer = _make_fresh_evidence_writer()
        with pytest.raises(ValueError, match="Invalid detail_code"):
            writer.append_execution_attempt(
                stage=ExecutionStage.SEMANTIC,
                outcome=ExecutionOutcome.FAILED,
                candidate_url="https://example.com/test",
                detail_code=ExecutionDetailCode.for_semantic_match(),
            )

    def test_evidence_reader_validates_semantic(self) -> None:
        """Reader validates SEMANTIC stage records."""
        from product_intelligence.execution.evidence_writer import (
            read_execution_evidence,
        )
        writer = _make_fresh_evidence_writer()
        writer.append_execution_attempt(
            stage=ExecutionStage.SEMANTIC,
            outcome=ExecutionOutcome.SUCCESS,
            candidate_url="https://example.com/test",
            detail_code=ExecutionDetailCode.for_semantic_match(),
        )
        writer.append_execution_attempt(
            stage=ExecutionStage.SEMANTIC,
            outcome=ExecutionOutcome.FAILED,
            candidate_url="https://example.com/test",
            detail_code=ExecutionDetailCode.for_semantic_unavailable(),
        )
        records = read_execution_evidence(writer._run)
        assert len(records) == 2
        assert records[0].stage == ExecutionStage.SEMANTIC.value
        assert records[0].detail_code == ExecutionDetailCode.SEMANTIC_MATCH.value
        assert records[1].detail_code == ExecutionDetailCode.SEMANTIC_UNAVAILABLE.value


# ================================================================
# Section 14: Real orchestration-level integration tests
# ================================================================


class TestRealOrchestrationIntegration:
    """True execution-integration tests through execute_research_run().

    These tests exercise the full research orchestration pipeline with
    injected fake search results and page fetchers, proving that:
    A. AI_ASSISTED_MATCH never reaches 4A aggregation
    B. Semantic failure keeps the run usable
    C. Programming exceptions use the real catastrophic boundary
    D. Zero-call authority works through real orchestration

    NO live semantic calls. All tests use FakeSemanticModelTransport.
    """

    def _make_search_result(self, url: str) -> MagicMock:
        """Create a mock search result."""
        result = MagicMock()
        result.source_url = url
        result.title = "Product"
        result.snippet = "Description"
        result.price_hint_text = None
        result.part_number_hint = None
        result.raw_reference = None
        return result

    def _make_search_response(self, urls: list[str]) -> MagicMock:
        """Create a mock SearchResponse for given URLs."""
        from datetime import datetime, timezone
        from product_intelligence.providers.search import SearchQuery

        results = tuple(self._make_search_result(url) for url in urls)
        response = MagicMock()
        response.provider_id = "test"
        response.query = MagicMock(spec=SearchQuery)
        response.retrieved_at = datetime.now(tz=timezone.utc)
        response.results = results
        response.raw_response_reference = None
        return response

    def _make_page_fetcher(self, url_to_body: dict[str, str]) -> MagicMock:
        """Create a fake page fetcher that returns different bodies per URL."""
        from datetime import datetime, timezone
        from product_intelligence.providers.page import FetchedPage, PageFetchRequest

        fetcher = MagicMock()

        def _fetch(request: PageFetchRequest) -> FetchedPage:
            body = url_to_body.get(request.url, "<html></html>")
            return FetchedPage(
                requested_url=request.url,
                final_url=request.url,
                retrieved_at=datetime.now(tz=timezone.utc),
                status_code=200,
                body_text=body,
                content_type="text/html",
                body_byte_count=len(body),
                redirect_count=0,
                fetcher_id="test",
            )

        fetcher.fetch.side_effect = _fetch
        return fetcher

    def _json_ld_page(self, payload: dict) -> str:
        """Build an HTML page with a JSON-LD script block."""
        import json
        text = json.dumps(payload)
        return f'<html><body><script type="application/ld+json">{text}</script></body></html>'

    def _accepted_json_ld(self, price: str, currency: str = "USD", mpn: str = "TEST-MPN") -> str:
        """JSON-LD for an ACCEPTED listing (exact MPN match)."""
        return self._json_ld_page({
            "@type": "Product",
            "name": "Test Product",
            "mpn": mpn,
            "offers": {
                "@type": "Offer",
                "price": price,
                "priceCurrency": currency,
                "itemCondition": "https://schema.org/NewCondition",
            },
        })

    def _semantic_eligible_json_ld(self, price: str, requested_mpn: str = "TEST-MPN", title: str | None = None, sku: str | None = None) -> str:
        """JSON-LD for a semantic-eligible listing (no explicit MPN evidence).

        The title MUST contain the requested MPN so that _find_evidence
        returns TITLE_TEXT (semantic-eligible). Without the MPN in the title,
        _find_evidence returns NONE and the candidate is not eligible.
        """
        if title is None:
            title = f"Compatible {requested_mpn} Product"
        elif requested_mpn not in title:
            # Ensure the requested MPN appears in the title
            title = f"{requested_mpn} {title}"
        payload: dict = {
            "@type": "Product",
            "name": title,
        }
        if sku is not None:
            payload["sku"] = sku
        payload["offers"] = {
            "@type": "Offer",
            "price": price,
            "priceCurrency": "USD",
            "itemCondition": "https://schema.org/NewCondition",
        }
        return self._json_ld_page(payload)

    # ------------------------------------------------------------------
    # 2A: MIXED DETERMINISTIC + AI-ASSISTED PRICE RUN
    # ------------------------------------------------------------------

    def test_mixed_deterministic_and_ai_assisted_price_run(self) -> None:
        """Real run: deterministic ACCEPTED + semantic-eligible MATCH.

        Proves AI_ASSISTED_MATCH never reaches 4A aggregation.
        """
        from product_intelligence.execution import execute_research_run
        from product_intelligence.providers.search import SearchProvider
        from product_intelligence.runs.models import PriceIntelligenceSnapshot, ResearchRun

        request = ResearchRequest("TEST-MPN", "Test product")

        # Two search results
        url1 = "https://example.com/exact-match"
        url2 = "https://example.com/semantic-match"

        # Page 1: exact MPN match (ACCEPTED) with price 100
        page1 = self._accepted_json_ld("100", "USD", "TEST-MPN")
        # Page 2: no explicit MPN, title present (semantic-eligible) with price 9999
        page2 = self._semantic_eligible_json_ld("9999")

        search_response = self._make_search_response([url1, url2])
        search_provider = MagicMock(spec=SearchProvider)
        search_provider.search.return_value = search_response

        page_fetcher = self._make_page_fetcher({url1: page1, url2: page2})

        # Fake semantic runtime returns MATCH
        fake_runtime = _make_fake_runtime(
            responses={"*": _match_response(SemanticDecision.MATCH)},
            case_ids=("*",),
        )

        # Create run
        run = ResearchRun.objects.create_from_request(request)

        # Execute with patched semantic runtime
        with patch.object(
            product_intelligence.execution.semantic_integration,
            "get_default_runtime",
            return_value=fake_runtime,
        ):
            result = execute_research_run(
                str(run.id),
                search_provider=search_provider,
                page_fetcher=page_fetcher,
            )

        # Run completes successfully
        assert result.run.current_state == ResearchRunState.COMPLETED

        # AI-assisted: exactly 1 match
        assert len(result.ai_assisted_matches) == 1
        assert result.ai_assisted_match_count == 1

        ai = result.ai_assisted_matches[0]
        assert ai.original_assessment.decision is not EvidenceDecision.ACCEPTED
        assert ai.disposition == EvidenceDecision.AI_ASSISTED_MATCH

        # 4A: bucket contains ONLY the deterministic price (100)
        assert result.snapshot is not None
        payload = result.snapshot.payload
        buckets = payload.get("buckets", [])
        assert len(buckets) == 1, f"Expected 1 bucket, got {len(buckets)}: {payload}"
        bucket = buckets[0]
        assert bucket["count"] == 1
        # Price values are stored as strings in the encoded payload
        assert str(bucket["low"]) == "100", f"low={bucket.get('low')!r}"
        assert str(bucket["median"]) == "100", f"median={bucket.get('median')!r}"
        assert str(bucket["high"]) == "100", f"high={bucket.get('high')!r}"

        # 9999 appears in NO 4A bucket
        all_prices = []
        for b in buckets:
            all_prices.append(str(b.get("low", "")))
            all_prices.append(str(b.get("median", "")))
            all_prices.append(str(b.get("high", "")))
        assert "9999" not in all_prices, f"9999 found in prices: {all_prices}"

    # ------------------------------------------------------------------
    # 2B: BOUNDED SEMANTIC FAILURE KEEPS REAL RUN USABLE
    # ------------------------------------------------------------------

    def test_semantic_failure_keeps_run_usable(self) -> None:
        """Real run: semantic-eligible candidate, runtime failure.

        Proves semantic unavailability does not fail the run.
        """
        from product_intelligence.execution import execute_research_run
        from product_intelligence.providers.search import SearchProvider
        from product_intelligence.runs.models import PriceIntelligenceSnapshot, ResearchRun
        from product_intelligence.semantic.runtime import (
            SemanticAttempt,
            SemanticAttemptStatus,
            SemanticRuntimeErrorType,
        )

        request = ResearchRequest("TEST-MPN", "Test product")
        url = "https://example.com/semantic-only"

        # Page: no explicit MPN, title present (semantic-eligible)
        page = self._semantic_eligible_json_ld("500")

        search_response = self._make_search_response([url])
        search_provider = MagicMock(spec=SearchProvider)
        search_provider.search.return_value = search_response

        page_fetcher = self._make_page_fetcher({url: page})

        # Fake semantic runtime returns a legitimate failure
        attempt = SemanticAttempt(
            provider="amax",
            model="nemotron-3-super",
            status=SemanticAttemptStatus.CASE_REJECTED,
            latency_ms=100,
        )
        failure_result = SemanticRuntimeResult(
            case_id="test",
            target_mpn="TEST-MPN",
            target_description="Test product",
            candidate_title="Compatible TEST-MPN Product",
            candidate_mpn_field=None,
            candidate_sku=None,
            candidate_specs=None,
            evidence_source="TITLE_TEXT",
            requested_primary_provider="amax",
            requested_primary_model="nemotron-3-super",
            attempts=(attempt,),
            fallback_used=False,
            fallback_reason=None,
            actual_provider=None,
            actual_model=None,
            decision=None,
            confidence=None,
            matched_attributes=(),
            conflicting_attributes=(),
            missing_critical_attributes=(),
            reason_code=None,
            error_type=SemanticRuntimeErrorType.PRIMARY_CASE_REJECTED,
        )

        # Runtime that returns failure
        fake_runtime = MagicMock(spec=SemanticRuntime)
        fake_runtime.evaluate.return_value = failure_result

        run = ResearchRun.objects.create_from_request(request)

        with patch.object(
            product_intelligence.execution.semantic_integration,
            "get_default_runtime",
            return_value=fake_runtime,
        ):
            result = execute_research_run(
                str(run.id),
                search_provider=search_provider,
                page_fetcher=page_fetcher,
            )

        # Semantic runtime called once
        fake_runtime.evaluate.assert_called_once()

        # No AI-assisted match
        assert len(result.ai_assisted_matches) == 0
        assert result.ai_assisted_match_count == 0

        # Run reaches COMPLETED
        assert result.run.current_state == ResearchRunState.COMPLETED

        # Snapshot is published
        assert result.snapshot is not None

        # SEMANTIC/FAILED evidence exists
        records = read_execution_evidence(result.run)
        semantic_records = [r for r in records if r.stage == ExecutionStage.SEMANTIC.value]
        assert len(semantic_records) == 1
        assert semantic_records[0].outcome == ExecutionOutcome.FAILED.value
        assert semantic_records[0].detail_code == ExecutionDetailCode.SEMANTIC_UNAVAILABLE.value

    # ------------------------------------------------------------------
    # 2C: PROGRAMMING EXCEPTION USES REAL CATASTROPHIC BOUNDARY
    # ------------------------------------------------------------------

    def test_programming_exception_fails_run(self) -> None:
        """Real run: semantic runtime raises RuntimeError.

        Proves the existing bounded catastrophic boundary catches it.
        """
        from product_intelligence.execution import execute_research_run, ExecutionError
        from product_intelligence.providers.search import SearchProvider
        from product_intelligence.runs.models import PriceIntelligenceSnapshot, ResearchRun

        request = ResearchRequest("TEST-MPN", "Test product")
        url = "https://example.com/semantic-only"

        page = self._semantic_eligible_json_ld("500")

        search_response = self._make_search_response([url])
        search_provider = MagicMock(spec=SearchProvider)
        search_provider.search.return_value = search_response

        page_fetcher = self._make_page_fetcher({url: page})

        # Runtime that raises RuntimeError
        fake_runtime = MagicMock(spec=SemanticRuntime)
        fake_runtime.evaluate.side_effect = RuntimeError("sentinel")

        run = ResearchRun.objects.create_from_request(request)

        with patch.object(
            product_intelligence.execution.semantic_integration,
            "get_default_runtime",
            return_value=fake_runtime,
        ):
            with pytest.raises(ExecutionError):
                execute_research_run(
                    str(run.id),
                    search_provider=search_provider,
                    page_fetcher=page_fetcher,
                )

        # Run reaches FAILED
        run.refresh_from_db()
        assert run.current_state == ResearchRunState.FAILED

        # No snapshot exists
        assert not PriceIntelligenceSnapshot.objects.filter(run_id=run.id).exists()

    # ------------------------------------------------------------------
    # 2D: ZERO-CALL AUTHORITY THROUGH REAL ORCHESTRATION
    # ------------------------------------------------------------------

    def test_zero_call_authority_through_orchestration(self) -> None:
        """Real run: only ACCEPTED candidates, no semantic call.

        Proves get_default_runtime is never invoked when all candidates
        are deterministically resolved.
        """
        from product_intelligence.execution import execute_research_run
        from product_intelligence.providers.search import SearchProvider
        from product_intelligence.runs.models import ResearchRun

        request = ResearchRequest("TEST-MPN", "Test product")
        url = "https://example.com/exact-only"

        # Page: exact MPN match (ACCEPTED)
        page = self._accepted_json_ld("100", "USD", "TEST-MPN")

        search_response = self._make_search_response([url])
        search_provider = MagicMock(spec=SearchProvider)
        search_provider.search.return_value = search_response

        page_fetcher = self._make_page_fetcher({url: page})

        # Sentinel: get_default_runtime must NOT be called
        sentinel_called = []

        def _sentinel_get_default_runtime():
            sentinel_called.append(True)
            raise RuntimeError("get_default_runtime should not be called")

        run = ResearchRun.objects.create_from_request(request)

        with patch.object(
            product_intelligence.execution.semantic_integration,
            "get_default_runtime",
            _sentinel_get_default_runtime,
        ):
            result = execute_research_run(
                str(run.id),
                search_provider=search_provider,
                page_fetcher=page_fetcher,
            )

        # get_default_runtime was NOT called
        assert len(sentinel_called) == 0, "get_default_runtime was called for ACCEPTED-only run"

        # Run still completes
        assert result.run.current_state == ResearchRunState.COMPLETED
        assert result.snapshot is not None
