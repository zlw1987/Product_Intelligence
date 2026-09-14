"""ComparableResearchExecution lifecycle model tests (PRODUCT-INTEL.7C-A).

Tests for:
- Model field contracts
- Lifecycle shape constraint
- UNIQUE(parent_run, active_slot) invariant
- Multiple terminal rows allowed
- Two active rows rejected
- related_name='+' creates no reverse accessor
- ResearchRun exact-field preservation
"""

from __future__ import annotations

import pytest
from django.db import IntegrityError
from django.test import TestCase

from product_intelligence.domain import ResearchRequest
from product_intelligence.domain.enums import ResearchRunState
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
        payload={"buckets": [], "assessments": [], "exclusions": [],
                 "verification_status": "VERIFIED"},
    )
    return run


# ---------------------------------------------------------------------------
# Model field contracts
# ---------------------------------------------------------------------------


class TestComparableResearchExecutionFields(TestCase):
    """ComparableResearchExecution has exactly the approved fields."""

    def test_exact_fields(self) -> None:
        expected = {
            "id",
            "parent_run",
            "state",
            "active_slot",
            "created_at",
            "started_at",
            "finished_at",
            "result_schema_version",
            "result_payload",
            "failure_reason",
        }
        actual = {
            f.name
            for f in ComparableResearchExecution._meta.get_fields()
        }
        assert actual == expected

    def test_parent_run_has_no_reverse_accessor(self) -> None:
        """related_name='+' means no reverse accessor on ResearchRun."""
        # ResearchRun should NOT have a comparableresearchexecution_set field
        assert not hasattr(ResearchRun, "comparableresearchexecution_set")
        assert not hasattr(ResearchRun, "comparable_research_execution")
        assert not hasattr(ResearchRun, "comparable_executions")

    def test_research_run_exact_fields_unchanged(self) -> None:
        """ResearchRun has exactly the same fields as before 7C-A."""
        expected = {
            "id",
            "manufacturer_part_number",
            "description",
            "state",
            "created_at",
            "started_at",
            "finished_at",
            "price_intelligence_snapshot",
            "execution_evidence",
            "ai_assisted_review_candidates",
        }
        actual = {f.name for f in ResearchRun._meta.get_fields()}
        assert actual == expected

    def test_uuid_primary_key(self) -> None:
        pk = ComparableResearchExecution._meta.get_field("id")
        assert pk.primary_key is True

    def test_state_choices(self) -> None:
        field = ComparableResearchExecution._meta.get_field("state")
        choices = {code for code, label in field.choices}
        assert choices == {
            ComparableResearchState.PENDING,
            ComparableResearchState.RUNNING,
            ComparableResearchState.COMPLETED,
            ComparableResearchState.FAILED,
        }
        assert field.default == ComparableResearchState.PENDING

    def test_active_slot_nullable(self) -> None:
        field = ComparableResearchExecution._meta.get_field("active_slot")
        assert field.null is True


# ---------------------------------------------------------------------------
# Lifecycle shape constraint
# ---------------------------------------------------------------------------


class TestLifecycleShapeConstraint(TestCase):
    """The DB-level CHECK constraint enforces lifecycle shapes."""

    def test_pending_shape(self) -> None:
        run = _make_completed_run()
        child = ComparableResearchExecution.objects.create(
            parent_run=run,
            state=ComparableResearchState.PENDING,
            active_slot=1,
        )
        assert child.state == ComparableResearchState.PENDING
        assert child.active_slot == 1
        assert child.started_at is None
        assert child.finished_at is None
        assert child.result_schema_version is None
        assert child.result_payload is None
        assert child.failure_reason is None

    def test_running_shape_via_update(self) -> None:
        """Manually create a RUNNING row (normally done by claim)."""
        run = _make_completed_run()
        child = ComparableResearchExecution.objects.create(
            parent_run=run,
            state=ComparableResearchState.PENDING,
            active_slot=1,
        )
        # Transition to RUNNING via direct update (simulate claim)
        from django.utils import timezone
        ComparableResearchExecution.objects.filter(
            id=child.id,
        ).update(
            state=ComparableResearchState.RUNNING,
            started_at=timezone.now(),
        )
        child.refresh_from_db()
        assert child.state == ComparableResearchState.RUNNING
        assert child.active_slot == 1
        assert child.started_at is not None
        assert child.finished_at is None
        assert child.result_schema_version is None
        assert child.result_payload is None
        assert child.failure_reason is None

    def test_completed_shape_via_update(self) -> None:
        """Manually create a COMPLETED row (normally done by complete)."""
        run = _make_completed_run()
        child = ComparableResearchExecution.objects.create(
            parent_run=run,
            state=ComparableResearchState.PENDING,
            active_slot=1,
        )
        from django.utils import timezone
        ComparableResearchExecution.objects.filter(id=child.id).update(
            state=ComparableResearchState.RUNNING,
            started_at=timezone.now(),
        )
        ComparableResearchExecution.objects.filter(id=child.id).update(
            state=ComparableResearchState.COMPLETED,
            active_slot=None,
            finished_at=timezone.now(),
            result_schema_version=1,
            result_payload={"kind": "FULL"},
        )
        child.refresh_from_db()
        assert child.state == ComparableResearchState.COMPLETED
        assert child.active_slot is None
        assert child.started_at is not None
        assert child.finished_at is not None
        assert child.result_schema_version == 1
        assert child.result_payload == {"kind": "FULL"}
        assert child.failure_reason is None

    def test_failed_shape_via_update(self) -> None:
        """Manually create a FAILED row."""
        run = _make_completed_run()
        child = ComparableResearchExecution.objects.create(
            parent_run=run,
            state=ComparableResearchState.PENDING,
            active_slot=1,
        )
        from django.utils import timezone
        ComparableResearchExecution.objects.filter(id=child.id).update(
            state=ComparableResearchState.RUNNING,
            started_at=timezone.now(),
        )
        ComparableResearchExecution.objects.filter(id=child.id).update(
            state=ComparableResearchState.FAILED,
            active_slot=None,
            finished_at=timezone.now(),
            failure_reason=ComparableResearchFailureReason.INTERNAL_ERROR,
        )
        child.refresh_from_db()
        assert child.state == ComparableResearchState.FAILED
        assert child.active_slot is None
        assert child.started_at is not None
        assert child.finished_at is not None
        assert child.result_schema_version is None
        assert child.result_payload is None
        assert child.failure_reason == ComparableResearchFailureReason.INTERNAL_ERROR

    def test_rejects_invalid_shape(self) -> None:
        """PENDING with non-null started_at is rejected."""
        run = _make_completed_run()
        from django.utils import timezone
        with pytest.raises(IntegrityError):
            ComparableResearchExecution.objects.create(
                parent_run=run,
                state=ComparableResearchState.PENDING,
                active_slot=1,
                started_at=timezone.now(),  # Invalid: PENDING must have NULL started_at
            )


# ---------------------------------------------------------------------------
# UNIQUE(parent_run, active_slot) invariant
# ---------------------------------------------------------------------------


class TestUniqueConstraint(TestCase):
    """The UNIQUE constraint enforces one active child per parent."""

    def test_one_active_allowed(self) -> None:
        """One active child per parent is fine."""
        run = _make_completed_run()
        c1 = ComparableResearchExecution.objects.create(
            parent_run=run,
            state=ComparableResearchState.PENDING,
            active_slot=1,
        )
        assert c1.active_slot == 1

    def test_two_active_rejected(self) -> None:
        """Two active children for the same parent is rejected."""
        run = _make_completed_run()
        ComparableResearchExecution.objects.create(
            parent_run=run,
            state=ComparableResearchState.PENDING,
            active_slot=1,
        )
        with pytest.raises(IntegrityError):
            ComparableResearchExecution.objects.create(
                parent_run=run,
                state=ComparableResearchState.PENDING,
                active_slot=1,
            )

    def test_multiple_terminal_allowed(self) -> None:
        """Multiple terminal (NULL active_slot) children are allowed."""
        run = _make_completed_run()
        from django.utils import timezone
        now = timezone.now()
        # Create two FAILED children manually
        ComparableResearchExecution.objects.create(
            parent_run=run,
            state=ComparableResearchState.FAILED,
            active_slot=None,
            started_at=now,
            finished_at=now,
            failure_reason=ComparableResearchFailureReason.INTERNAL_ERROR,
        )
        ComparableResearchExecution.objects.create(
            parent_run=run,
            state=ComparableResearchState.FAILED,
            active_slot=None,
            started_at=now,
            finished_at=now,
            failure_reason=ComparableResearchFailureReason.INTERNAL_ERROR,
        )
        assert (
            ComparableResearchExecution.objects.filter(
                parent_run=run, state=ComparableResearchState.FAILED
            ).count()
            == 2
        )

    def test_active_and_terminal_coexist(self) -> None:
        """One active + multiple terminal children for same parent."""
        run = _make_completed_run()
        from django.utils import timezone
        now = timezone.now()
        # Create a terminal child
        ComparableResearchExecution.objects.create(
            parent_run=run,
            state=ComparableResearchState.FAILED,
            active_slot=None,
            started_at=now,
            finished_at=now,
            failure_reason=ComparableResearchFailureReason.INTERNAL_ERROR,
        )
        # Create an active child
        c1 = ComparableResearchExecution.objects.create(
            parent_run=run,
            state=ComparableResearchState.PENDING,
            active_slot=1,
        )
        assert c1.active_slot == 1
        assert (
            ComparableResearchExecution.objects.filter(
                parent_run=run
            ).count()
            == 2
        )

    def test_active_slot_only_one_or_null(self) -> None:
        """active_slot can only be 1 or NULL."""
        run = _make_completed_run()
        with pytest.raises(IntegrityError):
            ComparableResearchExecution.objects.create(
                parent_run=run,
                state=ComparableResearchState.PENDING,
                active_slot=2,  # Invalid
            )

    def test_different_parents_can_both_have_active(self) -> None:
        """Different parents can each have their own active child."""
        r1 = _make_completed_run()
        r2 = _make_completed_run()
        c1 = ComparableResearchExecution.objects.create(
            parent_run=r1,
            state=ComparableResearchState.PENDING,
            active_slot=1,
        )
        c2 = ComparableResearchExecution.objects.create(
            parent_run=r2,
            state=ComparableResearchState.PENDING,
            active_slot=1,
        )
        assert c1.active_slot == 1
        assert c2.active_slot == 1


# ---------------------------------------------------------------------------
# Failure reason vocabulary
# ---------------------------------------------------------------------------


class TestFailureReasonVocabulary(TestCase):
    """Failure reason CHECK constraint enforces bounded vocabulary."""

    def test_valid_failure_reasons(self) -> None:
        """All defined failure reasons are accepted."""
        run = _make_completed_run()
        from django.utils import timezone
        now = timezone.now()
        for reason in ComparableResearchFailureReason.ALL:
            ComparableResearchExecution.objects.create(
                parent_run=run,
                state=ComparableResearchState.FAILED,
                active_slot=None,
                started_at=now,
                finished_at=now,
                failure_reason=reason,
            )

    def test_invalid_failure_reason_rejected(self) -> None:
        """Unknown failure reason is rejected."""
        run = _make_completed_run()
        from django.utils import timezone
        now = timezone.now()
        with pytest.raises(IntegrityError):
            ComparableResearchExecution.objects.create(
                parent_run=run,
                state=ComparableResearchState.FAILED,
                active_slot=None,
                started_at=now,
                finished_at=now,
                failure_reason="UNKNOWN_REASON",
            )


# ---------------------------------------------------------------------------
# Cascade delete
# ---------------------------------------------------------------------------


class TestCascadeDelete(TestCase):
    """Deleting a parent run deletes all its comparable children."""

    def test_cascade_on_parent_delete(self) -> None:
        run = _make_completed_run()
        c1 = ComparableResearchExecution.objects.create(
            parent_run=run,
            state=ComparableResearchState.PENDING,
            active_slot=1,
        )
        run_id = run.id
        run.delete()
        assert (
            ComparableResearchExecution.objects.filter(
                parent_run_id=run_id
            ).count()
            == 0
        )
