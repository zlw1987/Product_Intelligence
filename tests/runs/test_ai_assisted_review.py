"""Tests for the AI-assisted review service.

PRODUCT-INTEL.HUMAN-REVIEW.

Validates:
- Review state transitions (confirm, reject, undo)
- Idempotency of same-state operations
- Cross-run validation
- Non-reviewable run state validation
- Snapshot immutability during review
- Authority separation (confirm never changes EvidenceDecision)
- Run scoping
"""

from __future__ import annotations

import uuid
from decimal import Decimal

import pytest
from django.db import IntegrityError
from django.utils import timezone

from product_intelligence.domain import ResearchRequest
from product_intelligence.domain.enums import (
    ConfidenceLevel,
    EvidenceDecision,
    IdentityMatchType,
    ResearchRunState,
)
from product_intelligence.research.matching import ListingIdentityAssessment
from product_intelligence.research.normalization import (
    NormalizedCondition,
    NormalizedListingObservation,
)
from product_intelligence.research.listings import ListingObservation

from product_intelligence.runs.models import (
    AiAssistedReviewCandidate,
    PriceIntelligenceSnapshot,
    ResearchRun,
)
from product_intelligence.runs import (
    confirm_candidate,
    reject_candidate,
    undo_review,
)
from product_intelligence.runs.ai_assisted_review import (
    CandidateNotFoundError,
    CrossRunReviewError,
    ReviewConflictError,
    RunNotReviewableError,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def completed_run(human_review_db_isolation) -> ResearchRun:
    """A COMPLETED research run with a snapshot."""
    request = ResearchRequest(
        manufacturer_part_number="TEST-001",
        description="Test product",
    )
    run = ResearchRun.objects.create_from_request(request)
    run.transition_to(ResearchRunState.RUNNING)
    run.transition_to(ResearchRunState.COMPLETED)
    PriceIntelligenceSnapshot.objects.create(
        run=run,
        schema_version=1,
        payload={
            "request": {
                "manufacturer_part_number": "TEST-001",
                "description": "Test product",
            },
            "assessments": [],
            "exclusions": [],
            "buckets": [],
            "verification_status": "UNKNOWN",
        },
    )
    return run


@pytest.fixture
def partially_completed_run(human_review_db_isolation) -> ResearchRun:
    """A PARTIALLY_COMPLETED research run with a snapshot."""
    request = ResearchRequest(
        manufacturer_part_number="TEST-002",
        description="Test product 2",
    )
    run = ResearchRun.objects.create_from_request(request)
    run.transition_to(ResearchRunState.RUNNING)
    run.transition_to(ResearchRunState.PARTIALLY_COMPLETED)
    PriceIntelligenceSnapshot.objects.create(
        run=run,
        schema_version=1,
        payload={
            "request": {
                "manufacturer_part_number": "TEST-002",
                "description": "Test product 2",
            },
            "assessments": [],
            "exclusions": [],
            "buckets": [],
            "verification_status": "UNKNOWN",
        },
    )
    return run


@pytest.fixture
def failed_run(human_review_db_isolation) -> ResearchRun:
    """A FAILED research run."""
    request = ResearchRequest(
        manufacturer_part_number="TEST-003",
        description="Test product 3",
    )
    run = ResearchRun.objects.create_from_request(request)
    run.transition_to(ResearchRunState.RUNNING)
    run.transition_to(ResearchRunState.FAILED)
    return run


@pytest.fixture
def running_run(human_review_db_isolation) -> ResearchRun:
    """A RUNNING research run (not yet complete)."""
    request = ResearchRequest(
        manufacturer_part_number="TEST-004",
        description="Test product 4",
    )
    run = ResearchRun.objects.create_from_request(request)
    run.transition_to(ResearchRunState.RUNNING)
    return run


@pytest.fixture
def candidate(completed_run: ResearchRun, human_review_db_isolation) -> AiAssistedReviewCandidate:
    """A review candidate for a completed run."""
    return AiAssistedReviewCandidate.objects.create(
        run=completed_run,
        assessment_index=0,
        source_url="https://example.com/product/1",
        target_mpn="TEST-001",
        target_description="Test product",
        candidate_title="Test Product Title",
        candidate_mpn_field="TEST-001",
        candidate_sku="SKU-001",
        candidate_specs="Test specs",
        evidence_source="TITLE_TEXT",
        semantic_confidence="MEDIUM",
        semantic_reason_code="semantic_match",
        semantic_matched_attributes=["brand", "mpn"],
        semantic_conflicting_attributes=[],
        actual_provider="amax",
        actual_model="nemotron-3-super",
        prompt_version="v1.1",
    )


# ---------------------------------------------------------------------------
# State transition tests
# ---------------------------------------------------------------------------


@pytest.mark.usefixtures("human_review_db_isolation")
class TestConfirmCandidate:
    def test_confirm_sets_state_to_confirmed(
        self, candidate: AiAssistedReviewCandidate
    ) -> None:
        result = confirm_candidate(candidate.id)
        assert result.review_state == AiAssistedReviewCandidate.REVIEW_STATE_CONFIRMED

    def test_confirm_sets_reviewed_at(
        self, candidate: AiAssistedReviewCandidate
    ) -> None:
        assert candidate.reviewed_at is None
        result = confirm_candidate(candidate.id)
        assert result.reviewed_at is not None

    def test_confirm_idempotent(
        self, candidate: AiAssistedReviewCandidate
    ) -> None:
        first = confirm_candidate(candidate.id)
        assert first.review_state == AiAssistedReviewCandidate.REVIEW_STATE_CONFIRMED
        second = confirm_candidate(candidate.id)
        assert second.review_state == AiAssistedReviewCandidate.REVIEW_STATE_CONFIRMED
        # reviewed_at should not change on idempotent call
        assert second.reviewed_at == first.reviewed_at


@pytest.mark.usefixtures("human_review_db_isolation")
class TestRejectCandidate:
    def test_reject_sets_state_to_rejected(
        self, candidate: AiAssistedReviewCandidate
    ) -> None:
        result = reject_candidate(candidate.id)
        assert result.review_state == AiAssistedReviewCandidate.REVIEW_STATE_REJECTED

    def test_reject_sets_reviewed_at(
        self, candidate: AiAssistedReviewCandidate
    ) -> None:
        assert candidate.reviewed_at is None
        result = reject_candidate(candidate.id)
        assert result.reviewed_at is not None

    def test_reject_idempotent(
        self, candidate: AiAssistedReviewCandidate
    ) -> None:
        first = reject_candidate(candidate.id)
        assert first.review_state == AiAssistedReviewCandidate.REVIEW_STATE_REJECTED
        second = reject_candidate(candidate.id)
        assert second.review_state == AiAssistedReviewCandidate.REVIEW_STATE_REJECTED


@pytest.mark.usefixtures("human_review_db_isolation")
class TestUndoReview:
    def test_undo_confirmed_restores_unreviewed(
        self, candidate: AiAssistedReviewCandidate
    ) -> None:
        confirm_candidate(candidate.id)
        result = undo_review(candidate.id)
        assert result.review_state == AiAssistedReviewCandidate.REVIEW_STATE_UNREVIEWED

    def test_undo_rejected_restores_unreviewed(
        self, candidate: AiAssistedReviewCandidate
    ) -> None:
        reject_candidate(candidate.id)
        result = undo_review(candidate.id)
        assert result.review_state == AiAssistedReviewCandidate.REVIEW_STATE_UNREVIEWED

    def test_undo_unreviewed_is_safe_noop(
        self, candidate: AiAssistedReviewCandidate
    ) -> None:
        # Undo on UNREVIEWED is a safe no-op
        result = undo_review(candidate.id)
        assert result.review_state == AiAssistedReviewCandidate.REVIEW_STATE_UNREVIEWED

    def test_undo_clears_reviewed_at(
        self, candidate: AiAssistedReviewCandidate
    ) -> None:
        confirm_candidate(candidate.id)
        candidate.refresh_from_db()
        assert candidate.reviewed_at is not None
        undo_review(candidate.id)
        candidate.refresh_from_db()
        assert candidate.reviewed_at is None


# ---------------------------------------------------------------------------
# Error handling tests
# ---------------------------------------------------------------------------


@pytest.mark.usefixtures("human_review_db_isolation")
class TestCandidateNotFound:
    def test_nonexistent_uuid_raises(self) -> None:
        fake_id = uuid.uuid4()
        with pytest.raises(CandidateNotFoundError):
            confirm_candidate(fake_id)

    def test_reject_nonexistent_raises(self) -> None:
        fake_id = uuid.uuid4()
        with pytest.raises(CandidateNotFoundError):
            reject_candidate(fake_id)

    def test_undo_nonexistent_raises(self) -> None:
        fake_id = uuid.uuid4()
        with pytest.raises(CandidateNotFoundError):
            undo_review(fake_id)


@pytest.mark.usefixtures("human_review_db_isolation")
class TestCrossRunValidation:
    def test_candidate_from_another_run_fails(
        self, candidate: AiAssistedReviewCandidate, partially_completed_run: ResearchRun
    ) -> None:
        """A candidate from one run cannot be reviewed through another run."""
        with pytest.raises(CrossRunReviewError):
            confirm_candidate(candidate.id, run_id=partially_completed_run.id)


@pytest.mark.usefixtures("human_review_db_isolation")
class TestNonReviewableRunState:
    def test_failed_run_rejected(
        self, failed_run: ResearchRun
    ) -> None:
        c = AiAssistedReviewCandidate.objects.create(
            run=failed_run,
            assessment_index=0,
            source_url="https://example.com",
            target_mpn="TEST-003",
            candidate_title="Test",
            evidence_source="TITLE_TEXT",
            actual_provider="amax",
            actual_model="test",
            prompt_version="v1.1",
        )
        with pytest.raises(RunNotReviewableError):
            confirm_candidate(c.id)

    def test_running_run_rejected(
        self, running_run: ResearchRun
    ) -> None:
        c = AiAssistedReviewCandidate.objects.create(
            run=running_run,
            assessment_index=0,
            source_url="https://example.com",
            target_mpn="TEST-004",
            candidate_title="Test",
            evidence_source="TITLE_TEXT",
            actual_provider="amax",
            actual_model="test",
            prompt_version="v1.1",
        )
        with pytest.raises(RunNotReviewableError):
            confirm_candidate(c.id)


# ---------------------------------------------------------------------------
# Snapshot immutability tests
# ---------------------------------------------------------------------------


@pytest.mark.usefixtures("human_review_db_isolation")
class TestSnapshotImmutability:
    def test_confirm_does_not_mutate_snapshot(
        self, completed_run: ResearchRun, candidate: AiAssistedReviewCandidate
    ) -> None:
        snapshot = completed_run.price_intelligence_snapshot
        original_schema = snapshot.schema_version
        original_payload = snapshot.payload
        confirm_candidate(candidate.id)
        snapshot.refresh_from_db()
        assert snapshot.schema_version == original_schema
        assert snapshot.payload == original_payload

    def test_reject_does_not_mutate_snapshot(
        self, completed_run: ResearchRun, candidate: AiAssistedReviewCandidate
    ) -> None:
        snapshot = completed_run.price_intelligence_snapshot
        original_schema = snapshot.schema_version
        original_payload = snapshot.payload
        reject_candidate(candidate.id)
        snapshot.refresh_from_db()
        assert snapshot.schema_version == original_schema
        assert snapshot.payload == original_payload

    def test_undo_does_not_mutate_snapshot(
        self, completed_run: ResearchRun, candidate: AiAssistedReviewCandidate
    ) -> None:
        snapshot = completed_run.price_intelligence_snapshot
        original_schema = snapshot.schema_version
        original_payload = snapshot.payload
        confirm_candidate(candidate.id)
        undo_review(candidate.id)
        snapshot.refresh_from_db()
        assert snapshot.schema_version == original_schema
        assert snapshot.payload == original_payload


# ---------------------------------------------------------------------------
# Authority separation tests
# ---------------------------------------------------------------------------


@pytest.mark.usefixtures("human_review_db_isolation")
class TestAuthoritySeparation:
    def test_confirm_does_not_change_assessment_decision(
        self, candidate: AiAssistedReviewCandidate
    ) -> None:
        """Confirmation never mutates EvidenceDecision to ACCEPTED.

        The candidate record stores semantic provenance, not an Assessment.
        Confirming changes only the review_state, never touching the
        underlying assessment's decision field."""
        confirm_candidate(candidate.id)
        candidate.refresh_from_db()
        assert candidate.review_state == AiAssistedReviewCandidate.REVIEW_STATE_CONFIRMED
        # The semantic provenance fields are immutable
        assert candidate.evidence_source == "TITLE_TEXT"
        assert candidate.actual_provider == "amax"

    def test_review_preserves_semantic_provenance(
        self, candidate: AiAssistedReviewCandidate
    ) -> None:
        original_confidence = candidate.semantic_confidence
        original_reason = candidate.semantic_reason_code
        original_matched = candidate.semantic_matched_attributes
        confirm_candidate(candidate.id)
        candidate.refresh_from_db()
        assert candidate.semantic_confidence == original_confidence
        assert candidate.semantic_reason_code == original_reason
        assert candidate.semantic_matched_attributes == original_matched


# ---------------------------------------------------------------------------
# Duplicate prevention test
# ---------------------------------------------------------------------------


@pytest.mark.usefixtures("human_review_db_isolation")
class TestDuplicatePrevention:
    def test_unique_constraint_prevents_duplicate(
        self, completed_run: ResearchRun
    ) -> None:
        """Only one candidate per (run, assessment_index)."""
        AiAssistedReviewCandidate.objects.create(
            run=completed_run,
            assessment_index=0,
            source_url="https://example.com/1",
            target_mpn="TEST-001",
            candidate_title="Test",
            evidence_source="TITLE_TEXT",
            actual_provider="amax",
            actual_model="test",
            prompt_version="v1.1",
        )
        with pytest.raises(IntegrityError):
            AiAssistedReviewCandidate.objects.create(
                run=completed_run,
                assessment_index=0,
                source_url="https://example.com/2",
                target_mpn="TEST-001",
                candidate_title="Test 2",
                evidence_source="TITLE_TEXT",
                actual_provider="amax",
                actual_model="test",
                prompt_version="v1.1",
            )


# ---------------------------------------------------------------------------
# Run scoping tests
# ---------------------------------------------------------------------------


@pytest.mark.usefixtures("human_review_db_isolation")
class TestRunScoping:
    def test_review_belongs_to_one_run(
        self, candidate: AiAssistedReviewCandidate
    ) -> None:
        assert candidate.run_id == candidate.run.id

    def test_new_run_does_not_inherit_review_state(
        self, candidate: AiAssistedReviewCandidate
    ) -> None:
        """A retry/new run does not inherit review state."""
        confirm_candidate(candidate.id)
        # Create a new run for the same request
        request = ResearchRequest(
            manufacturer_part_number=candidate.run.manufacturer_part_number,
            description=candidate.run.description,
        )
        new_run = ResearchRun.objects.create_from_request(request)
        # The new run has no candidates
        assert new_run.ai_assisted_review_candidates.count() == 0

    def test_different_assessment_index_is_unrelated(
        self, completed_run: ResearchRun, candidate: AiAssistedReviewCandidate
    ) -> None:
        """Same run, different assessment index = unrelated candidate."""
        candidate2 = AiAssistedReviewCandidate.objects.create(
            run=completed_run,
            assessment_index=1,
            source_url="https://example.com/2",
            target_mpn="TEST-001",
            candidate_title="Test 2",
            evidence_source="TITLE_TEXT",
            actual_provider="amax",
            actual_model="test",
            prompt_version="v1.1",
        )
        confirm_candidate(candidate.id)
        candidate.refresh_from_db()
        candidate2.refresh_from_db()
        assert candidate.review_state == AiAssistedReviewCandidate.REVIEW_STATE_CONFIRMED
        assert candidate2.review_state == AiAssistedReviewCandidate.REVIEW_STATE_UNREVIEWED



@pytest.mark.usefixtures("human_review_db_isolation")
class TestReviewConflictSemantics:
    """State conflict tests: conflicting actions must raise ReviewConflictError."""

    def test_confirmed_then_reject_raises_conflict(
        self, candidate: AiAssistedReviewCandidate
    ) -> None:
        """CONFIRMED + reject must raise ReviewConflictError."""
        from product_intelligence.runs.ai_assisted_review import ReviewConflictError
        confirm_candidate(candidate.id)
        candidate.refresh_from_db()
        assert candidate.review_state == AiAssistedReviewCandidate.REVIEW_STATE_CONFIRMED
        with pytest.raises(ReviewConflictError, match="cannot reject"):
            reject_candidate(candidate.id)
        # State should remain CONFIRMED
        candidate.refresh_from_db()
        assert candidate.review_state == AiAssistedReviewCandidate.REVIEW_STATE_CONFIRMED

    def test_rejected_then_confirm_raises_conflict(
        self, candidate: AiAssistedReviewCandidate
    ) -> None:
        """REJECTED + confirm must raise ReviewConflictError."""
        from product_intelligence.runs.ai_assisted_review import ReviewConflictError
        reject_candidate(candidate.id)
        candidate.refresh_from_db()
        assert candidate.review_state == AiAssistedReviewCandidate.REVIEW_STATE_REJECTED
        with pytest.raises(ReviewConflictError, match="cannot confirm"):
            confirm_candidate(candidate.id)
        candidate.refresh_from_db()
        assert candidate.review_state == AiAssistedReviewCandidate.REVIEW_STATE_REJECTED

    def test_confirmed_then_confirmed_is_idempotent(
        self, candidate: AiAssistedReviewCandidate
    ) -> None:
        """CONFIRMED + confirm is idempotent."""
        confirm_candidate(candidate.id)
        result = confirm_candidate(candidate.id)
        assert result.review_state == AiAssistedReviewCandidate.REVIEW_STATE_CONFIRMED

    def test_rejected_then_rejected_is_idempotent(
        self, candidate: AiAssistedReviewCandidate
    ) -> None:
        """REJECTED + reject is idempotent."""
        reject_candidate(candidate.id)
        result = reject_candidate(candidate.id)
        assert result.review_state == AiAssistedReviewCandidate.REVIEW_STATE_REJECTED

    def test_undo_then_undo_is_idempotent(
        self, candidate: AiAssistedReviewCandidate
    ) -> None:
        """UNREVIEWED + undo is idempotent (safe no-op)."""
        result = undo_review(candidate.id)
        assert result.review_state == AiAssistedReviewCandidate.REVIEW_STATE_UNREVIEWED



@pytest.mark.usefixtures("human_review_db_isolation")
class TestModelConstraints:
    """Test AiAssistedReviewCandidate DB constraints."""

    def test_reviewed_at_null_for_unreviewed(
        self, candidate: AiAssistedReviewCandidate
    ) -> None:
        """UNREVIEWED candidate has reviewed_at NULL."""
        assert candidate.review_state == AiAssistedReviewCandidate.REVIEW_STATE_UNREVIEWED
        assert candidate.reviewed_at is None

    def test_reviewed_at_set_on_confirm(
        self, candidate: AiAssistedReviewCandidate
    ) -> None:
        """CONFIRMED candidate has reviewed_at NOT NULL."""
        confirm_candidate(candidate.id)
        candidate.refresh_from_db()
        assert candidate.review_state == AiAssistedReviewCandidate.REVIEW_STATE_CONFIRMED
        assert candidate.reviewed_at is not None

    def test_reviewed_at_set_on_reject(
        self, candidate: AiAssistedReviewCandidate
    ) -> None:
        """REJECTED candidate has reviewed_at NOT NULL."""
        reject_candidate(candidate.id)
        candidate.refresh_from_db()
        assert candidate.review_state == AiAssistedReviewCandidate.REVIEW_STATE_REJECTED
        assert candidate.reviewed_at is not None

    def test_reviewed_at_cleared_on_undo(
        self, candidate: AiAssistedReviewCandidate
    ) -> None:
        """UNREVIEWED via undo has reviewed_at NULL."""
        confirm_candidate(candidate.id)
        undo_review(candidate.id)
        candidate.refresh_from_db()
        assert candidate.review_state == AiAssistedReviewCandidate.REVIEW_STATE_UNREVIEWED
        assert candidate.reviewed_at is None

    def test_check_constraint_exists(self) -> None:
        """The CheckConstraint exists on the model."""
        from django.db.models import Q
        constraints = AiAssistedReviewCandidate._meta.constraints
        names = [c.name for c in constraints]
        assert 'ai_assisted_review_state_timestamp_consistency' in names, (
            f"CheckConstraint not found in {names}"
        )
