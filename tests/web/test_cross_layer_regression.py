"""Cross-layer regression: REJECTED original -> semantic MATCH -> human CONFIRM -> Reviewed Price.

PRODUCT-INTEL.HUMAN-REVIEW.

This test proves the REAL frozen FU3B execution architecture end to end:

A. A real semantic-eligible deterministic REJECTED assessment is created
B. A real AiAssistedMatchResult wraps it (semantic MATCH authority)
C. Deterministic snapshot contains the ORIGINAL REJECTED assessment
D. Review candidate is persisted mapped to that REJECTED assessment
E. GET detail reports binding_valid=True with review actions
F. POST confirm succeeds through the real web review endpoint
G. Snapshot assessment is STILL REJECTED (never mutated)
H. Reviewed Price includes the listing as HUMAN_CONFIRMED
I. Machine Price remains unchanged / excludes the REJECTED listing

This test MUST fail against the current (broken) implementation that expects
assessment.decision == AI_ASSISTED_MATCH, because no such assessment exists.

After the FU3B authority alignment fix, all assertions pass.
"""

from __future__ import annotations

from decimal import Decimal

import pytest
from django.test import Client
from django.urls import reverse

from product_intelligence.domain import ResearchRequest
from product_intelligence.domain.enums import ResearchRunState
from product_intelligence.research.aggregation import aggregate_listing_prices
from product_intelligence.research.matching import (
    EvidenceSource,
    IdentityRejectionReason,
    ListingIdentityAssessment,
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
from product_intelligence.domain.enums import (
    EvidenceDecision,
    IdentityMatchType,
)
from product_intelligence.research.price_result_codec import (
    PRICE_RESULT_SCHEMA_VERSION,
    encode_price_aggregation_result,
)
from product_intelligence.runs.models import (
    AiAssistedReviewCandidate,
    PriceIntelligenceSnapshot,
    ResearchRun,
)


@pytest.fixture
def client() -> Client:
    return Client()


@pytest.mark.usefixtures("human_review_db_isolation")
class TestRejectedOriginalToReviewedPriceRegression:
    """Mandatory regression proving REAL architecture end to end.

    This test exercises the complete FU3B human review flow with
    REAL frozen-runtime-reachable assessments.
    """

    @pytest.fixture
    def full_stack_run(self) -> tuple[
        ResearchRun,
        AiAssistedReviewCandidate,
        ListingIdentityAssessment,
    ]:
        """Build a run with REAL FU3B execution architecture persistence.

        A: Real semantic-eligible deterministic REJECTED assessment through
           assess_listing_identity()
        B: REAL SemanticRuntimeResult with SemanticDecision.MATCH
        C: REAL AiAssistedMatchResult wrapping (A) + (B)
        D: REAL _create_review_candidates() persists the candidate
        E: Deterministic snapshot with ORIGINAL REJECTED assessment

        No simulated or MagicMock objects. No direct AiAssistedReviewCandidate
        creation. Uses frozen production objects and functions.
        """
        from product_intelligence.research.matching import assess_listing_identity
        from product_intelligence.execution.semantic_integration import (
            AiAssistedMatchResult,
        )
        from product_intelligence.execution.orchestration import (
            _create_review_candidates,
        )
        from product_intelligence.semantic import (
            SemanticDecision,
            SemanticRuntimeResult,
            SemanticAttempt,
            SemanticAttemptStatus,
        )
        from product_intelligence.semantic.contract import (
            ConfidenceLevel as SemanticConfidenceLevel,
        )

        request = ResearchRequest(
            manufacturer_part_number="REG-001",
            description="Regression test product",
        )
        run = ResearchRun.objects.create_from_request(request)
        run.transition_to(ResearchRunState.RUNNING)
        run.transition_to(ResearchRunState.COMPLETED)

        # A: Real semantic-eligible deterministic REJECTED assessment through
        # the actual matching function: assess_listing_identity()
        obs = ListingObservation(
            source_url="https://example.com/regression-1",
            extraction_method=ExtractionMethod.JSON_LD,
            manufacturer_part_number_text="",
            sku_text=None,
            product_title="Component for REG-001 system",
            price_text="149.99",
            currency_text="USD",
            condition_text="new",
        )
        norm = NormalizedListingObservation(
            observation=obs,
            price_amount=Decimal("149.99"),
            currency_code="USD",
            condition=NormalizedCondition.NEW,
            availability=NormalizedAvailability.UNKNOWN,
            seller_name="Regression Seller",
            normalization_issues=(),
        )
        assessment = assess_listing_identity(request, norm)

        # Prove the real matcher produced the expected FU3B state
        assert assessment.decision is EvidenceDecision.REJECTED
        assert assessment.rejection_reason is IdentityRejectionReason.NO_EXPLICIT_MPN_EVIDENCE
        assert assessment.candidate_evidence_source is EvidenceSource.TITLE_TEXT

        # B: REAL SemanticRuntimeResult with SemanticDecision.MATCH
        # Bounded provenance matches the observation
        semantic_result = SemanticRuntimeResult(
            case_id="regression-case-1",
            target_mpn="REG-001",
            target_description="Regression test product",
            candidate_title=obs.product_title or "",
            candidate_mpn_field=(
                obs.manufacturer_part_number_text
                if obs.manufacturer_part_number_text
                else None
            ),
            candidate_sku=obs.sku_text if obs.sku_text else None,
            candidate_specs=None,
            evidence_source=assessment.candidate_evidence_source.value,
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

        # C: REAL AiAssistedMatchResult wrapping REJECTED original + MATCH semantic
        match_result = AiAssistedMatchResult(
            original_assessment=assessment,
            semantic_result=semantic_result,
            disposition=EvidenceDecision.AI_ASSISTED_MATCH,
        )

        # Prove: original_assessment is REJECTED, not AI_ASSISTED_MATCH
        assert match_result.original_assessment.decision is EvidenceDecision.REJECTED
        assert match_result.disposition is EvidenceDecision.AI_ASSISTED_MATCH

        # D: REAL _create_review_candidates() persists the candidate
        assessments = (assessment,)
        _create_review_candidates(run, assessments, (match_result,))

        # Retrieve the persisted candidate from DB (not directly created)
        candidate = AiAssistedReviewCandidate.objects.get(run=run)
        assert candidate.assessment_index == 0
        assert candidate.review_state == AiAssistedReviewCandidate.REVIEW_STATE_UNREVIEWED
        assert candidate.source_url == obs.source_url
        assert candidate.evidence_source == "TITLE_TEXT"

        # E: Deterministic snapshot with ORIGINAL REJECTED assessment
        price_result = aggregate_listing_prices(request, assessments)
        payload = encode_price_aggregation_result(price_result)
        PriceIntelligenceSnapshot.objects.create(
            run=run,
            schema_version=PRICE_RESULT_SCHEMA_VERSION,
            payload=payload,
        )

        # Prove: snapshot contains REJECTED assessment
        from product_intelligence.research.price_result_codec import (
            decode_price_aggregation_result,
        )
        snapshot = run.price_intelligence_snapshot
        decoded = decode_price_aggregation_result(
            snapshot.payload,
            schema_version=snapshot.schema_version,
        )
        assert decoded.assessments[0].decision is EvidenceDecision.REJECTED

        return run, candidate, assessment

    def test_e_get_binding_valid_shows_review_actions(
        self, client: Client, full_stack_run
    ) -> None:
        """E: GET detail reports binding_valid=True with review actions rendered.

        Proves the candidate is visible in the UI with Confirm/Reject buttons.
        """
        run, candidate, assessment = full_stack_run
        url = reverse("research-detail", kwargs={"run_id": run.id})
        response = client.get(url)
        assert response.status_code == 200

        # Context-level proof
        candidates = response.context.get("review_candidates")
        assert candidates is not None
        assert len(candidates) == 1
        assert candidates[0].binding_valid is True
        assert candidates[0].review_state == AiAssistedReviewCandidate.REVIEW_STATE_UNREVIEWED

        # HTML-level proof: candidate-specific review URL and action buttons are rendered
        content = response.content.decode("utf-8")
        review_url = reverse(
            "research-review",
            kwargs={"run_id": run.id, "candidate_id": candidate.id},
        )
        # The review form targeting this candidate must be in the page
        assert f'action="{review_url}"' in content, (
            "Candidate-specific review URL must be present in rendered HTML"
        )
        # Confirm/reject actions must be present
        assert 'value="confirm"' in content, (
            "Confirm action/button must be present in rendered HTML"
        )
        assert 'value="reject"' in content, (
            "Reject action/button must be present in rendered HTML"
        )

    def test_f_post_confirm_succeeds(
        self, client: Client, full_stack_run
    ) -> None:
        """F: POST confirm succeeds through the real web endpoint."""
        run, candidate, assessment = full_stack_run
        review_url = reverse(
            "research-review",
            kwargs={"run_id": run.id, "candidate_id": candidate.id},
        )
        response = client.post(review_url, {"action": "confirm"})
        assert response.status_code in (301, 302)

        candidate.refresh_from_db()
        assert candidate.review_state == AiAssistedReviewCandidate.REVIEW_STATE_CONFIRMED

    def test_g_snapshot_assessment_still_rejected(
        self, client: Client, full_stack_run
    ) -> None:
        """G: Underlying snapshot assessment is STILL REJECTED after confirm.

        The PriceIntelligenceSnapshot must NEVER be mutated. Human confirmation
        is an authority overlay, not an assessment mutation.
        """
        from product_intelligence.research.price_result_codec import (
            decode_price_aggregation_result,
        )
        from product_intelligence.runs import confirm_candidate

        run, candidate, original_assessment = full_stack_run

        # Get the original payload
        snapshot = run.price_intelligence_snapshot
        original_payload = snapshot.payload

        # Confirm the candidate
        confirm_candidate(candidate.id)
        candidate.refresh_from_db()
        assert candidate.review_state == AiAssistedReviewCandidate.REVIEW_STATE_CONFIRMED

        # Snapshot must be unchanged
        snapshot.refresh_from_db()
        assert snapshot.payload == original_payload

        # Decode and verify assessment is still REJECTED
        decoded = decode_price_aggregation_result(
            snapshot.payload,
            schema_version=snapshot.schema_version,
        )
        assert len(decoded.assessments) == 1
        still_assessment = decoded.assessments[0]
        assert still_assessment.decision is EvidenceDecision.REJECTED
        assert still_assessment.rejection_reason is IdentityRejectionReason.NO_EXPLICIT_MPN_EVIDENCE

    def test_h_reviewed_price_includes_human_confirmed(
        self, client: Client, full_stack_run
    ) -> None:
        """H: Reviewed Price includes the listing as HUMAN_CONFIRMED."""
        from product_intelligence.research.aggregation import ReviewedListingOrigin
        from product_intelligence.runs import confirm_candidate

        run, candidate, _ = full_stack_run

        confirm_candidate(candidate.id)

        url = reverse("research-detail", kwargs={"run_id": run.id})
        response = client.get(url)
        assert response.status_code == 200

        reviewed = response.context.get("reviewed_result")
        assert reviewed is not None, "Reviewed price must be available after confirmation"
        assert len(reviewed.buckets) == 1
        bucket = reviewed.buckets[0]
        assert bucket.count == 1
        assert bucket.deterministic_count == 0
        assert bucket.human_confirmed_count == 1
        # Presentation layer converts to string
        assert bucket.median == "149.99"
        # Verify origin through the bucket entries
        assert len(bucket.entries) == 1
        entry = bucket.entries[0]
        assert entry.origin == "HUMAN_CONFIRMED"

    def test_i_machine_price_excludes_rejected(
        self, client: Client, full_stack_run
    ) -> None:
        """I: Machine Price remains unchanged / excludes the REJECTED listing."""
        from product_intelligence.runs import confirm_candidate

        run, candidate, _ = full_stack_run

        # Even after confirmation, machine price must NOT include the listing
        confirm_candidate(candidate.id)

        url = reverse("research-detail", kwargs={"run_id": run.id})
        response = client.get(url)
        assert response.status_code == 200

        report = response.context.get("report_presentation")
        assert report is not None
        # Machine price has zero buckets (REJECTED listing excluded)
        assert len(report.buckets) == 0
        assert report.verification_status == "UNKNOWN"

    def test_full_flow_e_through_i(
        self, client: Client, full_stack_run
    ) -> None:
        """Full flow: E -> F -> G -> H -> I in one test."""
        from product_intelligence.research.price_result_codec import (
            decode_price_aggregation_result,
        )
        from product_intelligence.runs import confirm_candidate

        run, candidate, _ = full_stack_run

        # E: GET shows binding_valid=True
        url = reverse("research-detail", kwargs={"run_id": run.id})
        response = client.get(url)
        assert response.status_code == 200
        assert response.context["review_candidates"][0].binding_valid is True

        # Machine price before confirm: empty
        report_before = response.context["report_presentation"]
        assert len(report_before.buckets) == 0

        # No reviewed price before confirm
        assert response.context.get("reviewed_result") is None

        # F: POST confirm
        review_url = reverse(
            "research-review",
            kwargs={"run_id": run.id, "candidate_id": candidate.id},
        )
        response = client.post(review_url, {"action": "confirm"})
        assert response.status_code in (301, 302)
        candidate.refresh_from_db()
        assert candidate.review_state == AiAssistedReviewCandidate.REVIEW_STATE_CONFIRMED

        # G + H + I: GET after confirm
        response = client.get(url)
        assert response.status_code == 200

        # G: Snapshot still has REJECTED assessment
        snapshot = run.price_intelligence_snapshot
        decoded = decode_price_aggregation_result(
            snapshot.payload,
            schema_version=snapshot.schema_version,
        )
        assert decoded.assessments[0].decision is EvidenceDecision.REJECTED

        # I: Machine price still empty
        report_after = response.context["report_presentation"]
        assert len(report_after.buckets) == 0

        # H: Reviewed price has HUMAN_CONFIRMED entry
        reviewed = response.context["reviewed_result"]
        assert reviewed is not None
        assert reviewed.buckets[0].human_confirmed_count == 1
        assert reviewed.buckets[0].deterministic_count == 0

    def test_assessment_decision_is_rejected_not_ai_assisted(self, full_stack_run) -> None:
        """Proof: the persisted assessment is REJECTED, never AI_ASSISTED_MATCH.

        This is the core assertion that distinguishes the real FU3B architecture
        from the broken implementation.
        """
        run, candidate, original_assessment = full_stack_run

        # The original assessment used in the snapshot is REJECTED
        assert original_assessment.decision is EvidenceDecision.REJECTED
        assert original_assessment.decision is not EvidenceDecision.AI_ASSISTED_MATCH

        # The decoded snapshot assessment is also REJECTED
        snapshot = run.price_intelligence_snapshot
        from product_intelligence.research.price_result_codec import (
            decode_price_aggregation_result,
        )
        decoded = decode_price_aggregation_result(
            snapshot.payload,
            schema_version=snapshot.schema_version,
        )
        assert decoded.assessments[0].decision is EvidenceDecision.REJECTED
        assert decoded.assessments[0].decision is not EvidenceDecision.AI_ASSISTED_MATCH

        # The candidate exists and maps to this REJECTED assessment
        assert candidate.assessment_index == 0
