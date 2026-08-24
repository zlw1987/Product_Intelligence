"""Execution claim and lifecycle primitives (PRODUCT-INTEL.4C-A).

This module introduces the durable primitives needed before paid execution
can safely exist. It answers four questions durably:

1. Has this ResearchRun already been claimed for execution?
2. What execution attempts happened?
3. Did execution finish successfully or fail?
4. If the user retries, how do we preserve the failed run rather than
   silently executing it again?

No provider/network work is part of this task. This is purely about
execution ownership and lifecycle transitions.

Execution ownership invariant
-----------------------------

For one persisted ResearchRun:

    at most one execution claim may succeed

The claim must be database-backed and concurrency-safe. The eventual 4C-B
implementation will perform the paid provider call only AFTER this claim
succeeds. Therefore a duplicate caller must never be able to observe a
state that allows it to make the same paid call again.

Claim semantics
---------------

A claim is an atomic operation that transitions a run from CREATED to RUNNING.
If the run is already RUNNING, a terminal state, or has been claimed by
another caller, the claim fails closed.

The claim operation is:

* ATOMIC: either the run transitions to RUNNING, or nothing changes.
* FAIL-CLOSED: a failed claim never leaves the run in an ambiguous state.
* DURABLE: the claim is persisted before returning success.

The atomicity is achieved through Django's transaction and select_for_update
mechanism. SQLite supports row-level locking through SELECT FOR UPDATE, so
the same code works in tests and production.

Retry semantics
---------------

A failed or terminal ResearchRun is never reset to CREATED and executed
again in place. Retry means:

    create a NEW ResearchRun
    from the exact canonical ResearchRequest of the old run

The old run remains durable history. The new run begins through the existing
normal run-creation contract. No old snapshot is copied. No old execution
evidence is copied. No provider/network work is performed as part of retry
creation.

This module provides:

* claim_execution(run_id) -> ResearchRun
    Attempt to claim a run for execution. Returns the run if successful,
    raises ClaimExecutionFailed otherwise.

* complete_execution(run_id, state, at=None) -> ResearchRun
    Mark a run as completed (COMPLETED, PARTIALLY_COMPLETED, or FAILED).
    Must be called on a claimed (RUNNING) run.

* retry_run(run_id) -> ResearchRun
    Create a new run from the request of an old (terminal or failed) run.
    The old run remains unchanged.

The actual orchestration (calling search, fetch, extract, etc.) is 4C-B's
responsibility. This module only provides the lifecycle primitives.
"""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from django.utils import timezone

from product_intelligence.domain.enums import ResearchRunState
from product_intelligence.runs.errors import (
    InvalidResearchRunTransition,
    ResearchRunLifecycleError,
)
from product_intelligence.runs.models import ResearchRun

if TYPE_CHECKING:
    from typing import Final


__all__ = [
    "ClaimExecutionFailed",
    "complete_execution",
    "retry_run",
    "claim_execution",
]

# ---------------------------------------------------------------------------
# Errors
# ---------------------------------------------------------------------------


class ClaimExecutionFailed(ResearchRunLifecycleError):
    """Raised when an execution claim could not be granted.

    This is an explicit failure, never a silent coercion. If a run cannot
    be claimed, the caller is told exactly why.
    """

    REASON_RUN_NOT_FOUND: Final[str] = "run_not_found"
    REASON_ALREADY_CLAIMED: Final[str] = "already_claimed"
    REASON_TERMINAL_STATE: Final[str] = "terminal_state"
    REASON_CANNOT_CLAIM_CREATED: Final[str] = "cannot_claim_created"

    def __init__(
        self,
        run_id: object,
        reason: str,
        detail: str | None = None,
    ) -> None:
        self.run_id = run_id
        self.reason = reason
        self.detail = detail
        msg = f"execution claim failed for run {run_id}: {reason}"
        if detail:
            msg += f" ({detail})"
        super().__init__(msg)


# ---------------------------------------------------------------------------
# Execution claim
# ---------------------------------------------------------------------------


def claim_execution(run_id: str | None = None, *, run: ResearchRun | None = None) -> ResearchRun:
    """Attempt to claim a research run for execution.

    This is an ATOMIC operation: either the run transitions from CREATED
    to RUNNING, or nothing changes. A claim never leaves the run in an
    ambiguous state.

    The implementation uses a **database-level compare-and-set** pattern:
    one UPDATE statement that only succeeds if the run is in CREATED state.
    This is portable across databases (including SQLite which does not
    support SELECT FOR UPDATE).

    Parameters
    ----------
    run_id : str, optional
        The UUID of the run to claim, as a string. Exactly one of `run_id`
        or `run` must be provided.

    run : ResearchRun, optional
        A ResearchRun instance to claim. Exactly one of `run_id` or `run`
        must be provided.

    Returns
    -------
    ResearchRun
        The claimed run, now in RUNNING state with a started_at timestamp.

    Raises
    ------
    ClaimExecutionFailed
        If the run cannot be claimed. Reasons include:
        * run_not_found: no run with that ID exists
        * already_claimed: another caller has already claimed this run
        * terminal_state: the run is in a terminal state
        * cannot_claim_created: the run is already CLAIMED (should not happen
          with proper use, but guards against misuse)

    Notes
    -----
    The atomicity is achieved through a single UPDATE statement with a WHERE
    clause that checks the current state. This is portable across databases
    (SQLite, PostgreSQL, MySQL).

    The run must be in CREATED state. A run in RUNNING or any terminal state
    (COMPLETED, PARTIALLY_COMPLETED, FAILED) cannot be claimed.

    Examples
    --------
    >>> run = ResearchRun.objects.create_from_request(request)
    >>> # First caller claims successfully
    >>> claimed = claim_execution(run_id=str(run.id))
    >>> assert claimed.current_state == ResearchRunState.RUNNING
    >>> # Second caller fails
    >>> try:
    ...     claim_execution(run_id=str(run.id))
    ... except ClaimExecutionFailed as exc:
    ...     print(exc.reason)  # "already_claimed"
    """
    if (run_id is None) == (run is None):
        raise TypeError("exactly one of run_id or run must be provided")

    # Normalize to run_id
    target_id = str(run.id if run is not None else run_id)

    try:
        # Use a database-level compare-and-set with a single UPDATE statement
        # This is portable across SQLite, PostgreSQL, and MySQL
        # SQLite does NOT support SELECT FOR UPDATE - this pattern works everywhere
        # We use Django's ORM update() which handles parameter quoting properly
        rows_affected = ResearchRun.objects.filter(
            id=target_id,
            state=ResearchRunState.CREATED,
            started_at__isnull=True,
            finished_at__isnull=True,
        ).update(
            state=ResearchRunState.RUNNING,
            started_at=timezone.now(),
        )

        if rows_affected == 0:
            # No row matched our conditions - run may not exist or state changed
            try:
                run = ResearchRun.objects.get(id=target_id)
            except ResearchRun.DoesNotExist:
                raise ClaimExecutionFailed(
                    run_id=target_id,
                    reason=ClaimExecutionFailed.REASON_RUN_NOT_FOUND,
                    detail=f"no run with ID {target_id}",
                ) from None

            if run.state == ResearchRunState.RUNNING:
                raise ClaimExecutionFailed(
                    run_id=target_id,
                    reason=ClaimExecutionFailed.REASON_ALREADY_CLAIMED,
                    detail="another caller claimed this run first",
                )
            elif run.state in {
                ResearchRunState.COMPLETED.value,
                ResearchRunState.PARTIALLY_COMPLETED.value,
                ResearchRunState.FAILED.value,
            }:
                raise ClaimExecutionFailed(
                    run_id=target_id,
                    reason=ClaimExecutionFailed.REASON_TERMINAL_STATE,
                    detail=f"run is in terminal state {run.state}",
                )
            else:
                raise ClaimExecutionFailed(
                    run_id=target_id,
                    reason=ClaimExecutionFailed.REASON_CANNOT_CLAIM_CREATED,
                    detail=f"run is in unexpected state {run.state.value}",
                )

        # Success - fetch and return the updated run
        run = ResearchRun.objects.get(id=target_id)
        return run

    except ResearchRun.DoesNotExist:
        raise ClaimExecutionFailed(
            run_id=target_id,
            reason=ClaimExecutionFailed.REASON_RUN_NOT_FOUND,
            detail=f"no run with ID {target_id}",
        ) from None


# ---------------------------------------------------------------------------
# Execution completion
# ---------------------------------------------------------------------------


def complete_execution(
    run_id: str | None = None,
    *,
    run: ResearchRun | None = None,
    target_state: ResearchRunState,
    at: datetime | None = None,
) -> ResearchRun:
    """Mark a claimed run as completed (or failed).

    This operation transitions a run from RUNNING to a terminal state.
    It is the caller's responsibility to ensure that:

    * The run is in RUNNING state when this is called.
    * The caller has performed the research orchestration successfully
      (or determines that failure is the correct outcome).

    Parameters
    ----------
    run_id : str, optional
        The UUID of the run to complete. Exactly one of `run_id` or `run`
        must be provided.

    run : ResearchRun, optional
        A ResearchRun instance to complete. Exactly one of `run_id` or `run`
        must be provided.

    target_state : ResearchRunState
        The terminal state to transition to. Must be one of:
        * COMPLETED: the orchestration completed successfully.
        * PARTIALLY_COMPLETED: the orchestration completed but only
          partially (e.g., pricing found but no comparables).
        * FAILED: the orchestration failed.

    at : datetime, optional
        The moment the completion happened. Defaults to timezone.now().

    Returns
    -------
    ResearchRun
        The completed run, now in the target terminal state.

    Raises
    ------
    ResearchRunLifecycleError
        If the run is not in RUNNING state, or if target_state is not
        a terminal state.

    Notes
    -----
    This operation uses a database-level compare-and-set pattern with a single
    UPDATE statement to ensure atomicity across databases (including SQLite).

    This operation does NOT perform the orchestration. It only records
    the outcome. The orchestration (calling search, fetch, extract, etc.)
    is 4C-B's responsibility.

    Examples
    --------
    >>> run = claim_execution(run_id=str(run_id))
    >>> # Perform orchestration here...
    >>> # Then mark as completed
    >>> completed = complete_execution(run=run, target_state=ResearchRunState.COMPLETED)
    >>> assert completed.current_state == ResearchRunState.COMPLETED
    """
    if (run_id is None) == (run is None):
        raise TypeError("exactly one of run_id or run must be provided")

    if target_state not in {
        ResearchRunState.COMPLETED,
        ResearchRunState.PARTIALLY_COMPLETED,
        ResearchRunState.FAILED,
    }:
        raise ValueError(
            f"target_state must be a terminal state, got {target_state}"
        )

    # Normalize to run_id
    target_id = str(run.id if run is not None else run_id)
    current_time = at if at is not None else timezone.now()

    try:
        # Use a database-level compare-and-set with a single UPDATE statement
        # This is portable across SQLite, PostgreSQL, and MySQL
        # SQLite does NOT support SELECT FOR UPDATE - this pattern works everywhere
        # We use Django's ORM update() which handles parameter quoting properly
        rows_affected = ResearchRun.objects.filter(
            id=target_id,
            state=ResearchRunState.RUNNING,
            started_at__isnull=False,
            finished_at__isnull=True,
        ).update(
            state=target_state,
            finished_at=current_time,
        )

        if rows_affected == 0:
            # No row matched our conditions - run may not exist or state changed
            try:
                run = ResearchRun.objects.get(id=target_id)
            except ResearchRun.DoesNotExist:
                raise ResearchRunLifecycleError(
                    f"no run with ID {target_id}"
                )

            if run.state != ResearchRunState.RUNNING:
                raise ResearchRunLifecycleError(
                    f"cannot complete a run in state {run.state}; must be RUNNING"
                )
            else:
                raise ResearchRunLifecycleError(
                    f"run {target_id} was already completed by another caller"
                )

        # Success - fetch and return the updated run
        run = ResearchRun.objects.get(id=target_id)
        return run

    except ResearchRun.DoesNotExist:
        raise ResearchRunLifecycleError(
            f"no run with ID {target_id}"
        ) from None


# ---------------------------------------------------------------------------
# Retry creation
# ---------------------------------------------------------------------------


def retry_run(old_run: ResearchRun) -> ResearchRun:
    """Create a new run from the request of an old (terminal or failed) run.

    A failed or terminal ResearchRun is never reset to CREATED and executed
    again in place. Retry means:

        create a NEW ResearchRun
        from the exact canonical ResearchRequest of the old run

    The old run remains durable history. The new run begins through the
    existing normal run-creation contract.

    No old snapshot is copied. No old execution evidence is copied.
    No provider/network work is performed as part of retry creation.

    Parameters
    ----------
    old_run : ResearchRun
        A terminal or failed run to retry. The run's current_state must
        be terminal (COMPLETED, PARTIALLY_COMPLETED, or FAILED).

    Returns
    -------
    ResearchRun
        A new run with the same ResearchRequest as the old run. The new
        run is in CREATED state.

    Raises
    ------
    ResearchRunLifecycleError
        If the old run is not in a terminal state.

    Examples
    --------
    >>> old_run = complete_execution(
    ...     run_id=old_run_id, target_state=ResearchRunState.FAILED
    ... )
    >>> new_run = retry_run(old_run)
    >>> assert new_run.current_state == ResearchRunState.CREATED
    >>> assert new_run.id != old_run.id
    >>> assert new_run.manufacturer_part_number == old_run.manufacturer_part_number
    >>> assert new_run.description == old_run.description
    """
    current = old_run.current_state

    if current not in {
        ResearchRunState.COMPLETED,
        ResearchRunState.PARTIALLY_COMPLETED,
        ResearchRunState.FAILED,
    }:
        raise ResearchRunLifecycleError(
            f"cannot retry a run in state {current.value}; "
            f"must be a terminal state"
        )

    # Rebuild the canonical request
    request = old_run.to_research_request()

    # Create a new run using the existing manager API
    new_run = ResearchRun.objects.create_from_request(request)

    return new_run
