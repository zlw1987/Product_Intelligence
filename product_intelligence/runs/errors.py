"""Application-level errors for the research-run lifecycle.

These are deliberately *not* domain errors. `DomainValidationError` covers a
contract constructed with invalid input; the error here covers an application
operation that the lifecycle does not allow. Keeping them separate stops the
stdlib-only domain from having to know that a state machine exists.
"""

from __future__ import annotations


class ResearchRunLifecycleError(Exception):
    """Base class for lifecycle failures on a persisted research run."""


class InvalidResearchRunTransition(ResearchRunLifecycleError):
    """Raised when a state transition is not permitted.

    An invalid transition is an explicit failure, never a silent coercion: a
    run that cannot legally move is left exactly as it was, and the caller is
    told which move was refused. Silently clamping to the nearest legal state
    would let a caller believe a run progressed when it did not — the same
    class of fabricated certainty the rest of the system forbids.
    """

    def __init__(self, current: object, target: object) -> None:
        self.current = current
        self.target = target
        super().__init__(
            f"a research run in state {getattr(current, 'value', current)} cannot "
            f"transition to {getattr(target, 'value', target)}"
        )


class InvalidInitialResearchRunState(ResearchRunLifecycleError):
    """Raised when a run is first persisted in anything other than `CREATED`.

    A lifecycle that can be entered halfway is not a lifecycle. Without this,
    `ResearchRun.objects.create(state="COMPLETED", ...)` would record a run that
    finished without ever having started — structurally plausible to the
    database once the timestamps are filled in, and a complete fiction about
    what happened.
    """

    def __init__(self, attempted: str) -> None:
        self.attempted = attempted
        super().__init__(
            f"a research run must be created in CREATED, not {attempted}; "
            "reach later states through transition_to()"
        )


class UnsupportedResearchRunStateChange(ResearchRunLifecycleError):
    """Raised when a persisted run's state was changed outside the lifecycle API.

    Distinct from `InvalidResearchRunTransition` on purpose: the move attempted
    here may well have been a legal one, but it was made by assigning to the
    field and saving, which skips the transition rules and the timestamps that
    go with them. The problem is the route, not the destination, and the two
    failures read very differently in a traceback.
    """

    def __init__(self, persisted: str, attempted: str) -> None:
        self.persisted = persisted
        self.attempted = attempted
        super().__init__(
            f"the state of a saved research run changed from {persisted} to "
            f"{attempted} outside transition_to(); lifecycle state is not a "
            "freely assignable field"
        )


# ---------------------------------------------------------------------------
# 7C-A comparable-research lifecycle errors
# ---------------------------------------------------------------------------


class ComparableResearchError(ResearchRunLifecycleError):
    """Base class for comparable-research lifecycle failures."""


class ComparableResearchTriggerError(ComparableResearchError):
    """Raised when trigger_comparable_research cannot create a child attempt."""

    REASON_PARENT_NOT_FOUND: str = "parent_not_found"
    REASON_PARENT_NOT_COMPLETED: str = "parent_not_completed"
    REASON_NO_SNAPSHOT: str = "no_snapshot"
    REASON_ACTIVE_CHILD_EXISTS: str = "active_child_exists"

    def __init__(self, run_id: object, reason: str, detail: str | None = None) -> None:
        self.run_id = run_id
        self.reason = reason
        self.detail = detail
        msg = f"comparable research trigger failed for run {run_id}: {reason}"
        if detail:
            msg += f" ({detail})"
        super().__init__(msg)


class ComparableResearchClaimError(ComparableResearchError):
    """Raised when claim_comparable_research cannot transition PENDING -> RUNNING."""

    def __init__(self, child_id: object, detail: str | None = None) -> None:
        self.child_id = child_id
        self.detail = detail
        msg = f"comparable research claim failed for {child_id}"
        if detail:
            msg += f" ({detail})"
        super().__init__(msg)


class ComparableResearchCompletionError(ComparableResearchError):
    """Raised when complete_comparable_research cannot transition RUNNING -> COMPLETED."""

    def __init__(self, child_id: object, detail: str | None = None) -> None:
        self.child_id = child_id
        self.detail = detail
        msg = f"comparable research completion failed for {child_id}"
        if detail:
            msg += f" ({detail})"
        super().__init__(msg)


class ComparableResearchFailureError(ComparableResearchError):
    """Raised when fail_comparable_research cannot transition RUNNING -> FAILED."""

    def __init__(self, child_id: object, detail: str | None = None) -> None:
        self.child_id = child_id
        self.detail = detail
        msg = f"comparable research failure recording failed for {child_id}"
        if detail:
            msg += f" ({detail})"
        super().__init__(msg)
