"""Comparable execution lifecycle primitive tests (PRODUCT-INTEL.7C-A).

Tests for:
- trigger_comparable_research idempotency and eligibility
- claim_comparable_research compare-and-set
- complete_comparable_research atomic completion
- fail_comparable_research atomic failure
- Parent eligibility validation
- Transaction-safe IntegrityError recovery
- Retry after failure (new child, old preserved)
"""

from __future__ import annotations

import pytest
from django.db import IntegrityError, transaction
from django.test import TestCase
from django.utils import timezone

from product_intelligence.domain import ResearchRequest
from product_intelligence.domain.enums import ResearchRunState
from product_intelligence.runs import (
    ComparableResearchClaimError,
    ComparableResearchCompletionError,
    ComparableResearchFailureError,
    ComparableResearchTriggerError,
)
from product_intelligence.runs.comparable_execution_claims import (
    claim_comparable_research,
    complete_comparable_research,
    fail_comparable_research,
    trigger_comparable_research,
)
from product_intelligence.runs.models import (
    ComparableResearchExecution,
    ComparableResearchFailureReason,
    ComparableResearchState,
    PriceIntelligenceSnapshot,
    ResearchRun,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_completed_run() -> ResearchRun:
    """Create a COMPLETED ResearchRun with a snapshot."""
    request = ResearchRequest(
        manufacturer_part_number="XP15360SE70005",
        description="Seagate Nytro 5050",
    )
    run = ResearchRun.objects.create_from_request(request)
    run.transition_to(ResearchRunState.RUNNING)
    run.transition_to(ResearchRunState.COMPLETED)
    PriceIntelligenceSnapshot.objects.create(
        run=run,
        schema_version=1,
        payload={
            "request": {
                "manufacturer_part_number": "XP15360SE70005",
                "description": "Seagate Nytro 5050",
            },
            "assessments": [],
            "buckets": [],
            "exclusions": [],
            "verification_status": "VERIFIED",
        },
    )
    return run


def _make_run_in_state(state: ResearchRunState) -> ResearchRun:
    """Create a ResearchRun in the given state (no snapshot)."""
    request = ResearchRequest(
        manufacturer_part_number="XP15360SE70005",
        description="Test",
    )
    run = ResearchRun.objects.create_from_request(request)
    if state is ResearchRunState.RUNNING:
        run.transition_to(ResearchRunState.RUNNING)
    elif state in (ResearchRunState.COMPLETED, ResearchRunState.PARTIALLY_COMPLETED,
                   ResearchRunState.FAILED):
        run.transition_to(ResearchRunState.RUNNING)
        run.transition_to(state)
    return run


# ---------------------------------------------------------------------------
# TRIGGER
# ---------------------------------------------------------------------------


class TestTriggerComparableResearch(TestCase):
    """trigger_comparable_research lifecycle tests."""

    def test_creates_pending_child(self) -> None:
        run = _make_completed_run()
        child = trigger_comparable_research(run.id)
        assert child.parent_run_id == run.id
        assert child.state == ComparableResearchState.PENDING
        assert child.active_slot == 1
        assert child.started_at is None
        assert child.finished_at is None
        assert child.result_schema_version is None
        assert child.result_payload is None
        assert child.failure_reason is None

    def test_idempotent_returns_same_pending(self) -> None:
        run = _make_completed_run()
        c1 = trigger_comparable_research(run.id)
        c2 = trigger_comparable_research(run.id)
        assert c1.id == c2.id

    def test_returns_existing_running(self) -> None:
        run = _make_completed_run()
        child = trigger_comparable_research(run.id)
        claim_comparable_research(child.id)
        returned = trigger_comparable_research(run.id)
        assert returned.id == child.id
        assert returned.state == ComparableResearchState.RUNNING

    def test_returns_existing_completed(self) -> None:
        run = _make_completed_run()
        child = trigger_comparable_research(run.id)
        claim_comparable_research(child.id)
        complete_comparable_research(child.id, 1, {"kind": "FULL"})
        returned = trigger_comparable_research(run.id)
        assert returned.id == child.id
        assert returned.state == ComparableResearchState.COMPLETED

    def test_rejects_parent_not_found(self) -> None:
        import uuid
        with pytest.raises(ComparableResearchTriggerError) as exc_info:
            trigger_comparable_research(uuid.uuid4())
        assert exc_info.value.reason == "parent_not_found"

    def test_rejects_parent_running(self) -> None:
        run = _make_run_in_state(ResearchRunState.RUNNING)
        with pytest.raises(ComparableResearchTriggerError) as exc_info:
            trigger_comparable_research(run.id)
        assert exc_info.value.reason == "parent_not_completed"

    def test_rejects_parent_failed(self) -> None:
        run = _make_run_in_state(ResearchRunState.FAILED)
        with pytest.raises(ComparableResearchTriggerError) as exc_info:
            trigger_comparable_research(run.id)
        assert exc_info.value.reason == "parent_not_completed"

    def test_rejects_parent_partially_completed(self) -> None:
        run = _make_run_in_state(ResearchRunState.PARTIALLY_COMPLETED)
        with pytest.raises(ComparableResearchTriggerError) as exc_info:
            trigger_comparable_research(run.id)
        assert exc_info.value.reason == "parent_not_completed"

    def test_rejects_parent_created(self) -> None:
        request = ResearchRequest(
            manufacturer_part_number="TEST", description="test",
        )
        run = ResearchRun.objects.create_from_request(request)
        with pytest.raises(ComparableResearchTriggerError) as exc_info:
            trigger_comparable_research(run.id)
        assert exc_info.value.reason == "parent_not_completed"

    def test_rejects_completed_without_snapshot(self) -> None:
        """A COMPLETED parent without a snapshot is rejected."""
        run = _make_run_in_state(ResearchRunState.COMPLETED)
        # No snapshot created
        with pytest.raises(ComparableResearchTriggerError) as exc_info:
            trigger_comparable_research(run.id)
        assert exc_info.value.reason == "no_snapshot"

    def test_str_returns_expected_format(self) -> None:
        run = _make_completed_run()
        child = trigger_comparable_research(run.id)
        s = str(child)
        assert "ComparableResearchExecution" in s
        assert str(run.id) in s
        assert "PENDING" in s


# ---------------------------------------------------------------------------
# CLAIM
# ---------------------------------------------------------------------------


class TestClaimComparableResearch(TestCase):
    """claim_comparable_research compare-and-set tests."""

    def test_claims_pending_to_running(self) -> None:
        run = _make_completed_run()
        child = trigger_comparable_research(run.id)
        claimed = claim_comparable_research(child.id)
        assert claimed.state == ComparableResearchState.RUNNING
        assert claimed.active_slot == 1
        assert claimed.started_at is not None
        assert claimed.finished_at is None

    def test_rejects_already_running(self) -> None:
        run = _make_completed_run()
        child = trigger_comparable_research(run.id)
        claim_comparable_research(child.id)
        with pytest.raises(ComparableResearchClaimError):
            claim_comparable_research(child.id)

    def test_rejects_completed_child(self) -> None:
        run = _make_completed_run()
        child = trigger_comparable_research(run.id)
        claim_comparable_research(child.id)
        complete_comparable_research(child.id, 1, {"kind": "FULL"})
        with pytest.raises(ComparableResearchClaimError):
            claim_comparable_research(child.id)

    def test_rejects_nonexistent_child(self) -> None:
        import uuid
        with pytest.raises(ComparableResearchClaimError):
            claim_comparable_research(uuid.uuid4())


# ---------------------------------------------------------------------------
# COMPLETE
# ---------------------------------------------------------------------------


class TestCompleteComparableResearch(TestCase):
    """complete_comparable_research atomic tests."""

    def test_completes_running(self) -> None:
        run = _make_completed_run()
        child = trigger_comparable_research(run.id)
        claim_comparable_research(child.id)
        payload = {"kind": "FULL", "target_mpn": "XP15360SE70005"}
        completed = complete_comparable_research(child.id, 1, payload)
        assert completed.state == ComparableResearchState.COMPLETED
        assert completed.active_slot is None
        assert completed.finished_at is not None
        assert completed.result_schema_version == 1
        assert completed.result_payload == payload
        assert completed.failure_reason is None

    def test_rejects_pending_child(self) -> None:
        run = _make_completed_run()
        child = trigger_comparable_research(run.id)
        with pytest.raises(ComparableResearchCompletionError):
            complete_comparable_research(child.id, 1, {"kind": "FULL"})

    def test_rejects_failed_child(self) -> None:
        run = _make_completed_run()
        child = trigger_comparable_research(run.id)
        claim_comparable_research(child.id)
        fail_comparable_research(child.id, "INTERNAL_ERROR")
        with pytest.raises(ComparableResearchCompletionError):
            complete_comparable_research(child.id, 1, {"kind": "FULL"})

    def test_rejects_nonexistent_child(self) -> None:
        import uuid
        with pytest.raises(ComparableResearchCompletionError):
            complete_comparable_research(uuid.uuid4(), 1, {"kind": "FULL"})

    def test_active_slot_becomes_null(self) -> None:
        """After completion, the active slot is freed."""
        run = _make_completed_run()
        child = trigger_comparable_research(run.id)
        claim_comparable_research(child.id)
        complete_comparable_research(child.id, 1, {"kind": "FULL"})
        # A new child can now be created (the slot is free)
        new_child = trigger_comparable_research(run.id)
        # But trigger returns the completed one (idempotency)
        assert new_child.id == child.id
        assert new_child.state == ComparableResearchState.COMPLETED


# ---------------------------------------------------------------------------
# FAIL
# ---------------------------------------------------------------------------


class TestFailComparableResearch(TestCase):
    """fail_comparable_research atomic tests."""

    def test_fails_running(self) -> None:
        run = _make_completed_run()
        child = trigger_comparable_research(run.id)
        claim_comparable_research(child.id)
        failed = fail_comparable_research(
            child.id,
            ComparableResearchFailureReason.DISCOVERY_FAILED,
        )
        assert failed.state == ComparableResearchState.FAILED
        assert failed.active_slot is None
        assert failed.finished_at is not None
        assert failed.result_schema_version is None
        assert failed.result_payload is None
        assert (
            failed.failure_reason
            == ComparableResearchFailureReason.DISCOVERY_FAILED
        )

    def test_rejects_pending_child(self) -> None:
        run = _make_completed_run()
        child = trigger_comparable_research(run.id)
        with pytest.raises(ComparableResearchFailureError):
            fail_comparable_research(child.id, "INTERNAL_ERROR")

    def test_rejects_nonexistent_child(self) -> None:
        import uuid
        with pytest.raises(ComparableResearchFailureError):
            fail_comparable_research(uuid.uuid4(), "INTERNAL_ERROR")

    def test_rejects_invalid_failure_reason(self) -> None:
        run = _make_completed_run()
        child = trigger_comparable_research(run.id)
        claim_comparable_research(child.id)
        with pytest.raises(ValueError):
            fail_comparable_research(child.id, "NOT_A_REAL_REASON")


# ---------------------------------------------------------------------------
# Retry after failure
# ---------------------------------------------------------------------------


class TestRetryAfterFailure(TestCase):
    """A failed child is preserved; a new trigger creates a new child."""

    def test_old_failed_preserved_new_child_created(self) -> None:
        run = _make_completed_run()
        # First attempt: trigger -> claim -> fail
        child1 = trigger_comparable_research(run.id)
        claim_comparable_research(child1.id)
        fail_comparable_research(
            child1.id,
            ComparableResearchFailureReason.DISCOVERY_FAILED,
        )
        child1.refresh_from_db()
        assert child1.state == ComparableResearchState.FAILED

        # Second attempt: trigger should NOT return the failed child.
        # It should find no active/completed child, then create a new PENDING.
        child2 = trigger_comparable_research(run.id)
        assert child2.id != child1.id
        assert child2.state == ComparableResearchState.PENDING

        # Old failed child still exists
        child1.refresh_from_db()
        assert child1.state == ComparableResearchState.FAILED

    def test_multiple_failures_preserved(self) -> None:
        """Multiple failed children can coexist."""
        run = _make_completed_run()
        children = []
        for _ in range(3):
            child = trigger_comparable_research(run.id)
            claim_comparable_research(child.id)
            fail_comparable_research(
                child.id,
                ComparableResearchFailureReason.INTERNAL_ERROR,
            )
            children.append(child)

        # All three FAILED children exist
        assert (
            ComparableResearchExecution.objects.filter(
                parent_run=run,
                state=ComparableResearchState.FAILED,
            ).count()
            == 3
        )

        # A new trigger creates a 4th PENDING child
        new_child = trigger_comparable_research(run.id)
        assert new_child.state == ComparableResearchState.PENDING
        assert new_child.id not in {c.id for c in children}


# ---------------------------------------------------------------------------
# Trigger with string UUID
# ---------------------------------------------------------------------------


class TestTriggerWithStringUUID(TestCase):
    """trigger_comparable_research accepts str UUIDs."""

    def test_string_uuid(self) -> None:
        run = _make_completed_run()
        child = trigger_comparable_research(str(run.id))
        assert child.parent_run_id == run.id


# ---------------------------------------------------------------------------
# BLOCKER 1: IntegrityError recovery
# ---------------------------------------------------------------------------


class TestIntegrityErrorRecovery(TestCase):
    """trigger_comparable_research correctly handles IntegrityError collisions.

    BLOCKER 1 regression tests:
    1. expected active-slot conflict -> winning child returned
    2. unrelated IntegrityError -> exact IntegrityError propagates
    """

    def test_expected_collision_returns_winning_active_child(self) -> None:
        """When the UNIQUE constraint fires, the winning active child is
        returned. We force the collision-recovery branch by mocking create."""
        from unittest.mock import patch

        run = _make_completed_run()

        # Pre-create the winning child directly (simulates another caller)
        winner = ComparableResearchExecution.objects.create(
            parent_run=run,
            state=ComparableResearchState.PENDING,
            active_slot=1,
        )

        # Force the collision-recovery branch by mocking create to raise
        # IntegrityError, so the optimistic pre-check does not short-circuit.
        def mock_create(*args, **kwargs):
            raise IntegrityError('unique constraint violation')

        with patch.object(
            type(ComparableResearchExecution.objects),
            'create',
            mock_create,
        ):
            result = trigger_comparable_research(run.id)

        assert result.id == winner.id
        assert result.state == ComparableResearchState.PENDING

    def test_expected_collision_returns_running_winner(self) -> None:
        """Collision recovery returns a RUNNING winner."""
        from unittest.mock import patch

        run = _make_completed_run()
        winner = ComparableResearchExecution.objects.create(
            parent_run=run,
            state=ComparableResearchState.PENDING,
            active_slot=1,
        )
        # Simulate claim
        ComparableResearchExecution.objects.filter(id=winner.id).update(
            state=ComparableResearchState.RUNNING,
            started_at=timezone.now(),
        )
        winner.refresh_from_db()

        def mock_create(*args, **kwargs):
            raise IntegrityError('unique constraint violation')

        with patch.object(
            type(ComparableResearchExecution.objects),
            'create',
            mock_create,
        ):
            result = trigger_comparable_research(run.id)

        assert result.id == winner.id
        assert result.state == ComparableResearchState.RUNNING

    def test_unrelated_integrityerror_propagates_original(self) -> None:
        """If no winner is found after IntegrityError, the ORIGINAL
        IntegrityError propagates (not ComparableResearchTriggerError)."""
        from unittest.mock import patch

        run = _make_completed_run()

        # Mock the ORM create at the manager class level to simulate an unrelated
        # IntegrityError that is NOT the expected UNIQUE collision.
        def mock_create(*args, **kwargs):
            raise IntegrityError("simulated unrelated integrity error")

        with patch.object(
            type(ComparableResearchExecution.objects),
            "create",
            mock_create,
        ):
            with pytest.raises(IntegrityError, match="simulated unrelated"):
                trigger_comparable_research(run.id)

    def test_unrelated_integrityerror_not_wrapped(self) -> None:
        """An unrelated IntegrityError is NOT wrapped as
        ComparableResearchTriggerError."""
        from unittest.mock import patch

        run = _make_completed_run()

        def mock_create(*args, **kwargs):
            raise IntegrityError("database constraint violation")

        with patch.object(
            type(ComparableResearchExecution.objects),
            "create",
            mock_create,
        ):
            with pytest.raises(IntegrityError):
                trigger_comparable_research(run.id)
            # If we get here without ComparableResearchTriggerError, pass



# ---------------------------------------------------------------------------
# Lifecycle state property
# ---------------------------------------------------------------------------


class TestLifecycleStateProperty(TestCase):
    """ComparableResearchExecution.current_state property."""

    def test_current_state(self) -> None:
        run = _make_completed_run()
        child = trigger_comparable_research(run.id)
        assert child.current_state == ComparableResearchState.PENDING
