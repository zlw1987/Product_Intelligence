"""Comparable-research execution lifecycle primitives (PRODUCT-INTEL.7C-A).

Runs-layer only. Provides trigger, claim, complete, and fail operations
for ComparableResearchExecution children of ResearchRun.

These primitives use database-level compare-and-set patterns for atomicity
and rely on the UNIQUE(parent_run, active_slot) constraint as the hard
invariant against concurrent double-creation.

Parent eligibility (7C v1):
    ONLY ResearchRunState.COMPLETED is eligible.
    PARTIALLY_COMPLETED, FAILED, RUNNING, CREATED are NOT eligible.
    A COMPLETED parent must have its PriceIntelligenceSnapshot.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from django.db import IntegrityError, transaction
from django.utils import timezone

from product_intelligence.domain.enums import ResearchRunState
from product_intelligence.runs.errors import (
    ComparableResearchClaimError,
    ComparableResearchCompletionError,
    ComparableResearchFailureError,
    ComparableResearchTriggerError,
)
from product_intelligence.runs.models import (
    ComparableResearchExecution,
    ComparableResearchFailureReason,
    ComparableResearchState,
    PriceIntelligenceSnapshot,
    ResearchRun,
)

if TYPE_CHECKING:
    pass


__all__ = [
    "ComparableResearchClaimError",
    "ComparableResearchCompletionError",
    "ComparableResearchFailureError",
    "ComparableResearchTriggerError",
    "claim_comparable_research",
    "complete_comparable_research",
    "fail_comparable_research",
    "trigger_comparable_research",
]


# ---------------------------------------------------------------------------
# TRIGGER
# ---------------------------------------------------------------------------


def trigger_comparable_research(run_id: uuid.UUID | str) -> ComparableResearchExecution:
    """Create or locate a comparable-research child for a parent ResearchRun.

    Eligibility rules (7C v1):
    - Parent must exist.
    - Parent state must be COMPLETED (not PARTIALLY_COMPLETED, FAILED, etc.).
    - Parent must have a PriceIntelligenceSnapshot.

    Idempotency:
    - If an active (PENDING/RUNNING) child exists, return it.
    - If a COMPLETED child exists, return it.
    - Otherwise, create a new PENDING child.

    Concurrency:
    - Uses the UNIQUE(parent_run, active_slot) constraint as the hard invariant.
    - On IntegrityError, rolls back the failing insert inside a savepoint,
      then queries for the winning child outside the failed scope.
    - If the IntegrityError is not explained by an active/completed winner,
      re-raises it (unrelated database error).

    Returns
    -------
    ComparableResearchExecution
        The active or existing completed child.

    Raises
    ------
    ComparableResearchTriggerError
        If the parent is not eligible or invariant is violated.
    """
    target_id = str(run_id)

    # 1. Validate parent eligibility (outside transaction for clarity).
    try:
        parent = ResearchRun.objects.get(id=target_id)
    except ResearchRun.DoesNotExist:
        raise ComparableResearchTriggerError(
            run_id=target_id,
            reason=ComparableResearchTriggerError.REASON_PARENT_NOT_FOUND,
            detail=f"no ResearchRun with ID {target_id}",
        )

    if parent.current_state is not ResearchRunState.COMPLETED:
        raise ComparableResearchTriggerError(
            run_id=target_id,
            reason=ComparableResearchTriggerError.REASON_PARENT_NOT_COMPLETED,
            detail=f"parent is in state {parent.current_state.value}, only COMPLETED is eligible",
        )

    # 2. Validate COMPLETED snapshot invariant.
    try:
        parent.price_intelligence_snapshot  # type: ignore[union-attr]
    except PriceIntelligenceSnapshot.DoesNotExist:
        raise ComparableResearchTriggerError(
            run_id=target_id,
            reason=ComparableResearchTriggerError.REASON_NO_SNAPSHOT,
            detail="COMPLETED parent has no PriceIntelligenceSnapshot",
        )

    # 3. Check for existing active or completed child (optimistic path).
    existing_active = ComparableResearchExecution.objects.filter(
        parent_run_id=target_id,
        state__in=[ComparableResearchState.PENDING, ComparableResearchState.RUNNING],
    ).first()
    if existing_active:
        return existing_active

    existing_completed = ComparableResearchExecution.objects.filter(
        parent_run_id=target_id,
        state=ComparableResearchState.COMPLETED,
    ).first()
    if existing_completed:
        return existing_completed

    # 4. Create a new PENDING child.
    # Use a savepoint so IntegrityError recovery can query safely.
    saved_integrity_error: IntegrityError | None = None
    try:
        with transaction.atomic():
            ComparableResearchExecution.objects.create(
                parent_run=parent,
                state=ComparableResearchState.PENDING,
                active_slot=1,
            )
    except IntegrityError as exc:
        # The UNIQUE(parent_run, active_slot) constraint may have fired.
        # The failing transaction/savepoint has already rolled back here.
        # We must NOT query inside the atomic scope.
        saved_integrity_error = exc

    if saved_integrity_error is not None:
        # Query for an active or completed child that another caller created.
        winner = ComparableResearchExecution.objects.filter(
            parent_run_id=target_id,
            state__in=[
                ComparableResearchState.PENDING,
                ComparableResearchState.RUNNING,
            ],
        ).first()
        if winner is not None:
            return winner

        completed = ComparableResearchExecution.objects.filter(
            parent_run_id=target_id,
            state=ComparableResearchState.COMPLETED,
        ).first()
        if completed is not None:
            return completed

        # No winner found — the IntegrityError was unrelated.
        # Propagate the ORIGINAL IntegrityError, do not convert it.
        raise saved_integrity_error

    # No collision — the create succeeded. Fetch the created child.
    return ComparableResearchExecution.objects.get(
        parent_run_id=target_id,
        state=ComparableResearchState.PENDING,
        active_slot=1,
    )


# ---------------------------------------------------------------------------
# CLAIM
# ---------------------------------------------------------------------------


def claim_comparable_research(child_id: uuid.UUID | str) -> ComparableResearchExecution:
    """Claim a PENDING comparable-research child (PENDING -> RUNNING).

    Uses a database-level compare-and-set UPDATE: only succeeds if the
    child is currently PENDING. At most one caller can claim successfully.

    Parameters
    ----------
    child_id : UUID or str
        The ComparableResearchExecution to claim.

    Returns
    -------
    ComparableResearchExecution
        The claimed child, now in RUNNING state.

    Raises
    ------
    ComparableResearchClaimError
        If the child cannot be claimed (wrong state, not found, etc.).
    """
    target_id = str(child_id)
    now = timezone.now()

    rows = ComparableResearchExecution.objects.filter(
        id=target_id,
        state=ComparableResearchState.PENDING,
        active_slot=1,
        started_at__isnull=True,
    ).update(
        state=ComparableResearchState.RUNNING,
        started_at=now,
    )

    if rows == 0:
        try:
            child = ComparableResearchExecution.objects.get(id=target_id)
        except ComparableResearchExecution.DoesNotExist:
            raise ComparableResearchClaimError(
                child_id=target_id,
                detail=f"no ComparableResearchExecution with ID {target_id}",
            )
        raise ComparableResearchClaimError(
            child_id=target_id,
            detail=f"child is in state {child.state}, expected PENDING",
        )

    return ComparableResearchExecution.objects.get(id=target_id)


# ---------------------------------------------------------------------------
# COMPLETE
# ---------------------------------------------------------------------------


def complete_comparable_research(
    child_id: uuid.UUID | str,
    result_schema_version: int,
    result_payload: dict,
    *,
    at: datetime | None = None,
) -> ComparableResearchExecution:
    """Complete a RUNNING comparable-research child (RUNNING -> COMPLETED).

    Atomically writes state, active_slot, finished_at, result fields in
    a single UPDATE. No committed state may have COMPLETED without its result.

    Parameters
    ----------
    child_id : UUID or str
        The ComparableResearchExecution to complete.
    result_schema_version : int
        The codec version of the result payload (>= 1).
    result_payload : dict
        The versioned codec-encoded ComparableResearchResult.
    at : datetime, optional
        Completion timestamp. Defaults to timezone.now().

    Returns
    -------
    ComparableResearchExecution
        The completed child.

    Raises
    ------
    ComparableResearchCompletionError
        If the child cannot be completed.
    """
    target_id = str(child_id)
    now = at if at is not None else timezone.now()

    rows = ComparableResearchExecution.objects.filter(
        id=target_id,
        state=ComparableResearchState.RUNNING,
        active_slot=1,
        finished_at__isnull=True,
    ).update(
        state=ComparableResearchState.COMPLETED,
        active_slot=None,
        finished_at=now,
        result_schema_version=result_schema_version,
        result_payload=result_payload,
    )

    if rows == 0:
        try:
            child = ComparableResearchExecution.objects.get(id=target_id)
        except ComparableResearchExecution.DoesNotExist:
            raise ComparableResearchCompletionError(
                child_id=target_id,
                detail=f"no ComparableResearchExecution with ID {target_id}",
            )
        raise ComparableResearchCompletionError(
            child_id=target_id,
            detail=f"child is in state {child.state}, expected RUNNING",
        )

    return ComparableResearchExecution.objects.get(id=target_id)


# ---------------------------------------------------------------------------
# FAIL
# ---------------------------------------------------------------------------


def fail_comparable_research(
    child_id: uuid.UUID | str,
    failure_reason: str,
    *,
    at: datetime | None = None,
) -> ComparableResearchExecution:
    """Fail a RUNNING comparable-research child (RUNNING -> FAILED).

    Atomically writes state, active_slot, finished_at, failure_reason
    in a single UPDATE. Result fields remain NULL.

    If the database publication itself fails, propagates the DB exception.
    Does NOT claim failure was persisted.

    Parameters
    ----------
    child_id : UUID or str
        The ComparableResearchExecution to fail.
    failure_reason : str
        One of ComparableResearchFailureReason constants.
    at : datetime, optional
        Failure timestamp. Defaults to timezone.now().

    Returns
    -------
    ComparableResearchExecution
        The failed child.

    Raises
    ------
    ComparableResearchFailureError
        If the child cannot be failed.
    """
    target_id = str(child_id)
    now = at if at is not None else timezone.now()

    if failure_reason not in ComparableResearchFailureReason.ALL:
        raise ValueError(
            f"failure_reason must be a known ComparableResearchFailureReason, "
            f"got {failure_reason!r}"
        )

    rows = ComparableResearchExecution.objects.filter(
        id=target_id,
        state=ComparableResearchState.RUNNING,
        active_slot=1,
        finished_at__isnull=True,
    ).update(
        state=ComparableResearchState.FAILED,
        active_slot=None,
        finished_at=now,
        failure_reason=failure_reason,
    )

    if rows == 0:
        try:
            child = ComparableResearchExecution.objects.get(id=target_id)
        except ComparableResearchExecution.DoesNotExist:
            raise ComparableResearchFailureError(
                child_id=target_id,
                detail=f"no ComparableResearchExecution with ID {target_id}",
            )
        raise ComparableResearchFailureError(
            child_id=target_id,
            detail=f"child is in state {child.state}, expected RUNNING",
        )

    return ComparableResearchExecution.objects.get(id=target_id)
