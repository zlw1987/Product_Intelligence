"""Execution claim tests (PRODUCT-INTEL.4C-A).

These tests verify the atomic execution-ownership primitives:

* Execution claim (claim_execution)
* Execution completion (complete_execution)  
* Retry creation (retry_run)
"""

from __future__ import annotations

from datetime import datetime, timezone as datetime_timezone

from django.test import TestCase

from product_intelligence.domain import ResearchRequest
from product_intelligence.domain.enums import ResearchRunState
from product_intelligence.runs.execution_claims import (
    ClaimExecutionFailed,
    complete_execution,
    retry_run,
    claim_execution,
)
from product_intelligence.runs.models import ResearchRun

CREATED_AT = datetime(2026, 1, 5, 9, 0, tzinfo=datetime_timezone.utc)
STARTED_AT = datetime(2026, 1, 5, 9, 1, tzinfo=datetime_timezone.utc)
FINISHED_AT = datetime(2026, 1, 5, 9, 4, tzinfo=datetime_timezone.utc)
LATER = datetime(2026, 1, 5, 10, 0, tzinfo=datetime_timezone.utc)


class ClaimExecutionTests(TestCase):
    """Tests for claim_execution()."""

    def test_created_run_can_be_claimed(self) -> None:
        """A run in CREATED state can be claimed."""
        run = ResearchRun.objects.create_from_request(
            ResearchRequest(
                manufacturer_part_number="ABC123",
                description="test product",
            ),
            created_at=CREATED_AT,
        )

        self.assertEqual(run.current_state, ResearchRunState.CREATED)

        claimed = claim_execution(run_id=str(run.id))

        self.assertEqual(claimed.current_state, ResearchRunState.RUNNING)
        # started_at is set by timezone.now(), not the test constant
        self.assertIsNotNone(claimed.started_at)
        self.assertIsNone(claimed.finished_at)

    def test_second_claim_fails(self) -> None:
        """A second claim attempt on an already-claimed run fails."""
        run = ResearchRun.objects.create_from_request(
            ResearchRequest(
                manufacturer_part_number="ABC123",
                description="test product",
            ),
            created_at=CREATED_AT,
        )

        # First claim succeeds
        claim_execution(run_id=str(run.id))

        # Second claim fails
        with self.assertRaises(ClaimExecutionFailed) as caught:
            claim_execution(run_id=str(run.id))

        self.assertEqual(caught.exception.reason, ClaimExecutionFailed.REASON_ALREADY_CLAIMED)

        # Run state unchanged
        run.refresh_from_db()
        self.assertEqual(run.current_state, ResearchRunState.RUNNING)

    def test_terminal_run_claim_fails(self) -> None:
        """A terminal run cannot be claimed."""
        run = ResearchRun.objects.create_from_request(
            ResearchRequest(
                manufacturer_part_number="ABC123",
                description="test product",
            ),
            created_at=CREATED_AT,
        )

        run.transition_to(ResearchRunState.RUNNING, at=STARTED_AT)
        run.transition_to(ResearchRunState.COMPLETED, at=FINISHED_AT)

        with self.assertRaises(ClaimExecutionFailed) as caught:
            claim_execution(run_id=str(run.id))

        self.assertEqual(caught.exception.reason, ClaimExecutionFailed.REASON_TERMINAL_STATE)

    def test_claim_fails_for_nonexistent_run(self) -> None:
        """Claiming a nonexistent run fails."""
        with self.assertRaises(ClaimExecutionFailed) as caught:
            claim_execution(run_id="00000000-0000-0000-0000-000000000000")

        self.assertEqual(caught.exception.reason, ClaimExecutionFailed.REASON_RUN_NOT_FOUND)


class CompleteExecutionTests(TestCase):
    """Tests for complete_execution()."""

    def test_running_run_can_be_completed(self) -> None:
        """A claimed run can be marked as completed."""
        run = ResearchRun.objects.create_from_request(
            ResearchRequest(
                manufacturer_part_number="ABC123",
                description="test product",
            ),
            created_at=CREATED_AT,
        )

        run.transition_to(ResearchRunState.RUNNING, at=STARTED_AT)

        completed = complete_execution(
            run_id=str(run.id),
            target_state=ResearchRunState.COMPLETED,
            at=FINISHED_AT,
        )

        self.assertEqual(completed.current_state, ResearchRunState.COMPLETED)
        self.assertEqual(completed.started_at, STARTED_AT)
        self.assertEqual(completed.finished_at, FINISHED_AT)

    def test_running_run_can_be_marked_partially_completed(self) -> None:
        """A run with partial results can be marked PARTIALLY_COMPLETED."""
        run = ResearchRun.objects.create_from_request(
            ResearchRequest(
                manufacturer_part_number="ABC123",
                description="test product",
            ),
            created_at=CREATED_AT,
        )

        run.transition_to(ResearchRunState.RUNNING, at=STARTED_AT)

        completed = complete_execution(
            run_id=str(run.id),
            target_state=ResearchRunState.PARTIALLY_COMPLETED,
            at=FINISHED_AT,
        )

        self.assertEqual(completed.current_state, ResearchRunState.PARTIALLY_COMPLETED)
        self.assertEqual(completed.finished_at, FINISHED_AT)

    def test_running_run_can_be_marked_failed(self) -> None:
        """A failed run can be marked FAILED."""
        run = ResearchRun.objects.create_from_request(
            ResearchRequest(
                manufacturer_part_number="ABC123",
                description="test product",
            ),
            created_at=CREATED_AT,
        )

        run.transition_to(ResearchRunState.RUNNING, at=STARTED_AT)

        completed = complete_execution(
            run_id=str(run.id),
            target_state=ResearchRunState.FAILED,
            at=FINISHED_AT,
        )

        self.assertEqual(completed.current_state, ResearchRunState.FAILED)

    def test_cannot_complete_created_run(self) -> None:
        """A run that hasn't been claimed cannot be completed."""
        from product_intelligence.runs.errors import ResearchRunLifecycleError

        run = ResearchRun.objects.create_from_request(
            ResearchRequest(
                manufacturer_part_number="ABC123",
                description="test product",
            ),
            created_at=CREATED_AT,
        )

        with self.assertRaises(ResearchRunLifecycleError):
            complete_execution(
                run_id=str(run.id),
                target_state=ResearchRunState.COMPLETED,
                at=FINISHED_AT,
            )

    def test_cannot_complete_already_completed_run(self) -> None:
        """A terminal run cannot be completed again."""
        from product_intelligence.runs.errors import ResearchRunLifecycleError

        run = ResearchRun.objects.create_from_request(
            ResearchRequest(
                manufacturer_part_number="ABC123",
                description="test product",
            ),
            created_at=CREATED_AT,
        )

        run.transition_to(ResearchRunState.RUNNING, at=STARTED_AT)
        run.transition_to(ResearchRunState.COMPLETED, at=FINISHED_AT)

        with self.assertRaises(ResearchRunLifecycleError):
            complete_execution(
                run_id=str(run.id),
                target_state=ResearchRunState.FAILED,
                at=LATER,
            )

    def test_invalid_target_state_raises(self) -> None:
        """complete_execution rejects non-terminal target states."""
        run = ResearchRun.objects.create_from_request(
            ResearchRequest(
                manufacturer_part_number="ABC123",
                description="test product",
            ),
            created_at=CREATED_AT,
        )

        with self.assertRaises(ValueError):
            complete_execution(
                run_id=str(run.id),
                target_state=ResearchRunState.RUNNING,
                at=FINISHED_AT,
            )


class RetryRunTests(TestCase):
    """Tests for retry_run()."""

    def test_retry_creates_new_run(self) -> None:
        """retry_run creates a distinct run with the same request."""
        old_run = ResearchRun.objects.create_from_request(
            ResearchRequest(
                manufacturer_part_number="ABC123",
                description="test product",
            ),
            created_at=CREATED_AT,
        )

        old_run.transition_to(ResearchRunState.RUNNING, at=STARTED_AT)
        old_run.transition_to(ResearchRunState.FAILED, at=FINISHED_AT)

        new_run = retry_run(old_run)

        self.assertNotEqual(new_run.id, old_run.id)
        self.assertEqual(new_run.current_state, ResearchRunState.CREATED)
        self.assertEqual(new_run.manufacturer_part_number, old_run.manufacturer_part_number)
        self.assertEqual(new_run.description, old_run.description)

        # Old run unchanged
        old_run.refresh_from_db()
        self.assertEqual(old_run.current_state, ResearchRunState.FAILED)

    def test_retry_from_completed_run(self) -> None:
        """A completed run can be retried."""
        old_run = ResearchRun.objects.create_from_request(
            ResearchRequest(
                manufacturer_part_number="ABC123",
                description="test product",
            ),
            created_at=CREATED_AT,
        )

        old_run.transition_to(ResearchRunState.RUNNING, at=STARTED_AT)
        old_run.transition_to(ResearchRunState.COMPLETED, at=FINISHED_AT)

        new_run = retry_run(old_run)

        self.assertEqual(new_run.current_state, ResearchRunState.CREATED)
        self.assertNotEqual(new_run.id, old_run.id)

    def test_retry_from_partially_completed_run(self) -> None:
        """A partially completed run can be retried."""
        old_run = ResearchRun.objects.create_from_request(
            ResearchRequest(
                manufacturer_part_number="ABC123",
                description="test product",
            ),
            created_at=CREATED_AT,
        )

        old_run.transition_to(ResearchRunState.RUNNING, at=STARTED_AT)
        old_run.transition_to(ResearchRunState.PARTIALLY_COMPLETED, at=FINISHED_AT)

        new_run = retry_run(old_run)

        self.assertEqual(new_run.current_state, ResearchRunState.CREATED)
        self.assertNotEqual(new_run.id, old_run.id)

    def test_cannot_retry_running_run(self) -> None:
        """A running (non-terminal) run cannot be retried."""
        from product_intelligence.runs.errors import ResearchRunLifecycleError

        run = ResearchRun.objects.create_from_request(
            ResearchRequest(
                manufacturer_part_number="ABC123",
                description="test product",
            ),
            created_at=CREATED_AT,
        )

        run.transition_to(ResearchRunState.RUNNING, at=STARTED_AT)

        with self.assertRaises(ResearchRunLifecycleError):
            retry_run(run)

    def test_retry_does_not_copy_snapshot(self) -> None:
        """A retry does not copy the old run's price snapshot."""
        from product_intelligence.runs.models import PriceIntelligenceSnapshot

        old_run = ResearchRun.objects.create_from_request(
            ResearchRequest(
                manufacturer_part_number="ABC123",
                description="test product",
            ),
            created_at=CREATED_AT,
        )

        old_run.transition_to(ResearchRunState.RUNNING, at=STARTED_AT)
        old_run.transition_to(ResearchRunState.COMPLETED, at=FINISHED_AT)

        # Create a snapshot for the old run
        old_run.price_intelligence_snapshot = PriceIntelligenceSnapshot.objects.create(
            run=old_run,
            schema_version=1,
            payload={"test": "data"},
            created_at=FINISHED_AT,
        )

        old_run.refresh_from_db()
        self.assertIsNotNone(old_run.price_intelligence_snapshot)

        # Retry
        new_run = retry_run(old_run)

        # New run has no snapshot
        self.assertFalse(
            hasattr(new_run, "price_intelligence_snapshot")
            and new_run.price_intelligence_snapshot is not None
        )

    def test_retry_does_not_copy_execution_evidence(self) -> None:
        """A retry does not copy the old run's execution evidence."""
        from product_intelligence.runs.models import ExecutionEvidenceRecord

        old_run = ResearchRun.objects.create_from_request(
            ResearchRequest(
                manufacturer_part_number="ABC123",
                description="test product",
            ),
            created_at=CREATED_AT,
        )

        old_run.transition_to(ResearchRunState.RUNNING, at=STARTED_AT)
        old_run.transition_to(ResearchRunState.COMPLETED, at=FINISHED_AT)

        # Add some evidence records
        ExecutionEvidenceRecord.objects.create(
            run=old_run,
            attempt_number=1,
            stage="SEARCH",
            outcome="SUCCESS",
            detail_code="",
        )

        old_run.refresh_from_db()
        self.assertEqual(old_run.execution_evidence.count(), 1)

        # Retry
        new_run = retry_run(old_run)

        # New run has no evidence records
        self.assertEqual(new_run.execution_evidence.count(), 0)
