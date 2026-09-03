"""Runs-layer review service for AI-assisted semantic match candidates.

PRODUCT-INTEL.HUMAN-REVIEW.

This module owns the write path for human review decisions: confirm, reject,
and undo. It uses transaction.atomic and row-level F for safe concurrent
updates to the review_state field.

Design rules:
* Same-state confirm/reject is an idempotent no-op.
* Undo on an UNREVIEWED candidate is a safe no-op.
* A candidate from another run fails closed.
* An invalid candidate UUID fails closed.
* A non-reviewable/non-terminal run fails closed.
* Concurrent updates use F expressions — no JSON read-modify-write.
* The PriceIntelligenceSnapshot is never mutated.
* Confirming a candidate NEVER changes EvidenceDecision to ACCEPTED.
"""

from __future__ import annotations

import uuid
from datetime import datetime

from django.db import transaction
from django.utils import timezone

from product_intelligence.runs.errors import ResearchRunLifecycleError
from product_intelligence.domain.enums import ResearchRunState

from product_intelligence.runs.models import (
    AiAssistedReviewCandidate,
    ResearchRun,
    TERMINAL_STATES,
)


# ---------------------------------------------------------------------------
# Errors
# ---------------------------------------------------------------------------


class ReviewError(Exception):
    """Base error for review operations."""

    pass


class CandidateNotFoundError(ReviewError):
    """The candidate UUID does not exist."""

    pass


class InvalidCandidateError(ReviewError):
    """The candidate is invalid (e.g., stale assessment mapping)."""

    pass


class RunNotReviewableError(ReviewError):
    """The run is not in a reviewable state."""

    pass


class InvalidReviewActionError(ReviewError):
    """The requested action is invalid for the current review state."""

    pass


class ReviewConflictError(ReviewError):
    """A concurrent or prior operation put the candidate in a conflicting state.

    Raised when the candidate's current state contradicts the requested action
    after a conditional-update race. For example:
    - CONFIRMED + reject -> conflict
    - REJECTED + confirm -> conflict
    - Concurrent confirm/reject loser
    """

    pass


class CrossRunReviewError(ReviewError):
    """The candidate belongs to a different run than the one in the request."""

    pass


# ---------------------------------------------------------------------------
# Run validation
# ---------------------------------------------------------------------------


def _validate_run_reviewable(run: ResearchRun) -> None:
    """Validate that the run is in a state where review is allowed.

    Review is only allowed for terminal runs (COMPLETED, PARTIALLY_COMPLETED).
    FAILED runs are not reviewable because they may not have a snapshot.
    RUNNING/CREATED runs are not reviewable because execution is not done.
    """
    if run.current_state is ResearchRunState.FAILED:
        raise RunNotReviewableError(
            f"Run {run.id} is in FAILED state and cannot be reviewed."
        )
    if run.current_state not in TERMINAL_STATES:
        raise RunNotReviewableError(
            f"Run {run.id} is in {run.current_state.value} state; "
            "review is only available for completed runs."
        )


# ---------------------------------------------------------------------------
# Public review operations
# ---------------------------------------------------------------------------


def confirm_candidate(
    candidate_id: uuid.UUID,
    run_id: uuid.UUID | None = None,
) -> AiAssistedReviewCandidate:
    """Confirm an AI-assisted review candidate.

    Sets the review_state to CONFIRMED. Idempotent: if already CONFIRMED,
    returns the candidate without error.

    Args:
        candidate_id: The UUID of the candidate to confirm.
        run_id: If provided, the candidate must belong to this run.

    Returns:
        The updated AiAssistedReviewCandidate.

    Raises:
        CandidateNotFoundError: If the candidate does not exist.
        RunNotReviewableError: If the run is not in a reviewable state.
        InvalidCandidateError: If the run has no snapshot.
        CrossRunReviewError: If the candidate belongs to a different run.
    """
    return _update_review_state(
        candidate_id=candidate_id,
        target_state=AiAssistedReviewCandidate.REVIEW_STATE_CONFIRMED,
        action='confirm',
        expected_run_id=run_id,
    )


def reject_candidate(
    candidate_id: uuid.UUID,
    run_id: uuid.UUID | None = None,
) -> AiAssistedReviewCandidate:
    """Reject an AI-assisted review candidate.

    Sets the review_state to REJECTED. Idempotent: if already REJECTED,
    returns the candidate without error.

    Args:
        candidate_id: The UUID of the candidate to reject.
        run_id: If provided, the candidate must belong to this run.

    Returns:
        The updated AiAssistedReviewCandidate.

    Raises:
        CandidateNotFoundError: If the candidate does not exist.
        RunNotReviewableError: If the run is not in a reviewable state.
        InvalidCandidateError: If the run has no snapshot.
        CrossRunReviewError: If the candidate belongs to a different run.
    """
    return _update_review_state(
        candidate_id=candidate_id,
        target_state=AiAssistedReviewCandidate.REVIEW_STATE_REJECTED,
        action='reject',
        expected_run_id=run_id,
    )


def undo_review(
    candidate_id: uuid.UUID,
    run_id: uuid.UUID | None = None,
) -> AiAssistedReviewCandidate:
    """Undo a review decision, restoring UNREVIEWED state.

    Sets the review_state back to UNREVIEWED. Idempotent: if already
    UNREVIEWED, returns the candidate without error.

    Args:
        candidate_id: The UUID of the candidate to undo.
        run_id: If provided, the candidate must belong to this run.

    Returns:
        The updated AiAssistedReviewCandidate.

    Raises:
        CandidateNotFoundError: If the candidate does not exist.
        RunNotReviewableError: If the run is not in a reviewable state.
        InvalidCandidateError: If the run has no snapshot.
        CrossRunReviewError: If the candidate belongs to a different run.
    """
    return _update_review_state(
        candidate_id=candidate_id,
        target_state=AiAssistedReviewCandidate.REVIEW_STATE_UNREVIEWED,
        action='undo',
        expected_run_id=run_id,
    )


# ---------------------------------------------------------------------------
# Internal implementation
# ---------------------------------------------------------------------------


def _update_review_state(
    candidate_id: uuid.UUID,
    target_state: str,
    action: str,
    expected_run_id: uuid.UUID | None = None,
) -> AiAssistedReviewCandidate:
    """Update the review state of one candidate.

    Uses a conditional database update with F expressions to prevent lost
    updates on concurrent access. All validation and the state transition
    occur inside a single transaction.atomic() block for cross-run safety.

    Concurrency semantics:
    - The entire operation (fetch + validate + update) is wrapped in
      transaction.atomic().
    - The state transition uses a conditional update that checks the current
      review_state before changing it, preventing lost updates when two
      concurrent requests target the same candidate.
    - On SQLite, select_for_update() is a no-op (no row locking), so the
      conditional update is the primary concurrency protection.
    - Idempotency: a same-state operation returns immediately without touching
      the database row. A concurrent-winner race returns the current state
      rather than raising an error.

    Args:
        candidate_id: The UUID of the candidate.
        target_state: The target review state string.
        action: The action name ('confirm', 'reject', 'undo').
        expected_run_id: If provided, the candidate must belong to this run.

    Returns:
        The refreshed AiAssistedReviewCandidate after the update.

    Raises:
        CandidateNotFoundError: If the candidate does not exist.
        RunNotReviewableError: If the run is not in a reviewable state.
        InvalidCandidateError: If the run has no snapshot.
        CrossRunReviewError: If the candidate belongs to a different run.
    """
    if candidate_id is None:
        raise CandidateNotFoundError("Candidate ID is required.")

    with transaction.atomic():
        # Fetch the candidate inside the transaction
        try:
            candidate = AiAssistedReviewCandidate.objects.get(
                id=candidate_id
            )
        except AiAssistedReviewCandidate.DoesNotExist:
            raise CandidateNotFoundError(
                f"Review candidate {candidate_id} does not exist."
            )

        # Cross-run validation: candidate must belong to the expected run
        if expected_run_id is not None and candidate.run_id != expected_run_id:
            raise CrossRunReviewError(
                f"Candidate {candidate_id} belongs to run {candidate.run_id}, "
                f"not the expected run {expected_run_id}."
            )

        # Validate the run state
        _validate_run_reviewable(candidate.run)

        # Validate the assessment index maps to an actual assessment
        _validate_assessment_mapping(candidate)

        # Idempotency: if already in the target state, return as-is
        if candidate.review_state == target_state:
            return candidate

        # Build the conditional update: only update if the current state is
        # the expected prior state for this transition. This prevents lost
        # updates when two concurrent requests target the same candidate.
        now = timezone.now()
        reviewed_at = now if target_state != AiAssistedReviewCandidate.REVIEW_STATE_UNREVIEWED else None

        if target_state == AiAssistedReviewCandidate.REVIEW_STATE_CONFIRMED:
            rows = AiAssistedReviewCandidate.objects.filter(
                pk=candidate.id,
                review_state=AiAssistedReviewCandidate.REVIEW_STATE_UNREVIEWED,
            ).update(
                review_state=target_state,
                reviewed_at=reviewed_at,
            )
        elif target_state == AiAssistedReviewCandidate.REVIEW_STATE_REJECTED:
            rows = AiAssistedReviewCandidate.objects.filter(
                pk=candidate.id,
                review_state=AiAssistedReviewCandidate.REVIEW_STATE_UNREVIEWED,
            ).update(
                review_state=target_state,
                reviewed_at=reviewed_at,
            )
        elif target_state == AiAssistedReviewCandidate.REVIEW_STATE_UNREVIEWED:
            rows = AiAssistedReviewCandidate.objects.filter(
                pk=candidate.id,
                review_state__in=AiAssistedReviewCandidate.TERMINAL_REVIEW_STATES,
            ).update(
                review_state=target_state,
                reviewed_at=reviewed_at,
            )
        else:
            raise InvalidReviewActionError(
                f"Unknown target state: {target_state!r}"
            )

        if rows == 0:
            # Another concurrent operation already changed the state, or the
            # transition was invalid for the current state.
            candidate.refresh_from_db()
            if candidate.review_state == target_state:
                # Idempotent: the current state matches what was requested.
                return candidate
            # The current state contradicts the requested action.
            raise ReviewConflictError(
                f"Candidate {candidate_id} is in {candidate.review_state} state; "
                f"cannot {action} (expected target: {target_state})."
            )

        candidate.refresh_from_db()

    return candidate



def _validate_assessment_mapping(candidate: AiAssistedReviewCandidate) -> None:
    """Validate that the candidate's assessment index references a valid run snapshot.

    This is the runs-layer portion of fail-closed binding validation.
    It only checks runs-owned data (snapshot existence). Full provenance binding
    (URL, title, MPN, SKU matching) is performed at the web consumption layer,
    where research imports are allowed.

    Uses narrow exception handling: ObjectDoesNotExist is expected when
    the snapshot has not been created yet.
    """
    from django.core.exceptions import ObjectDoesNotExist

    try:
        snapshot = candidate.run.price_intelligence_snapshot
    except ObjectDoesNotExist:
        raise InvalidCandidateError(
            f"Run {candidate.run.id} has no PriceIntelligenceSnapshot; "
            "review cannot be performed."
        )
