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


# ---------------------------------------------------------------------------
# VREF-R0 vendor-refresh lifecycle errors
# ---------------------------------------------------------------------------


class VendorRefreshError(ResearchRunLifecycleError):
    """Base class for vendor-refresh lifecycle failures (VREF-R0)."""


class VendorRefreshTriggerError(VendorRefreshError):
    """Raised when trigger_vendor_refresh cannot create or locate a child.

    The bounded reasons cover parent eligibility and trigger-input
    validation. ``operator`` is self-reported provenance, not
    authentication; a non-string or out-of-bounds (length not 1..128)
    operator is refused here — the bound is service-level, because the
    database CHECK covers non-emptiness only and SQLite does not enforce
    ``CharField.max_length`` — so the row's non-empty CHECK never fires
    through the race-recovery path. A non-string ``trigger_source``
    (including an unhashable list/dict) is refused with a bounded error,
    never a native TypeError.
    """

    REASON_PARENT_NOT_FOUND: str = "parent_not_found"
    REASON_PARENT_NOT_COMPLETED: str = "parent_not_completed"
    REASON_NO_SNAPSHOT: str = "no_snapshot"
    REASON_NO_MPN: str = "no_mpn"
    REASON_INVALID_OPERATOR: str = "invalid_operator"
    REASON_INVALID_TRIGGER_SOURCE: str = "invalid_trigger_source"

    def __init__(self, run_id: object, reason: str, detail: str | None = None) -> None:
        self.run_id = run_id
        self.reason = reason
        self.detail = detail
        msg = f"vendor refresh trigger failed for run {run_id}: {reason}"
        if detail:
            msg += f" ({detail})"
        super().__init__(msg)


class VendorRefreshClaimError(VendorRefreshError):
    """Raised when claim_vendor_refresh cannot transition PENDING -> RUNNING."""

    def __init__(self, child_id: object, detail: str | None = None) -> None:
        self.child_id = child_id
        self.detail = detail
        msg = f"vendor refresh claim failed for {child_id}"
        if detail:
            msg += f" ({detail})"
        super().__init__(msg)


class VendorRefreshCompletionError(VendorRefreshError):
    """Raised when complete_vendor_refresh cannot transition RUNNING -> COMPLETED.

    Invalid schema-version or payload input is rejected BEFORE the
    conditional UPDATE (no malformed COMPLETED row is published, zero row
    mutation). The CAS itself matches the stored RUNNING shape; it does
    not authenticate the caller as the original claim winner (that
    decision is owned by the R1 gate).
    """

    REASON_INVALID_SCHEMA_VERSION: str = "invalid_schema_version"
    REASON_INVALID_PAYLOAD: str = "invalid_payload"

    def __init__(self, child_id: object, detail: str | None = None, *, reason: str | None = None) -> None:
        self.child_id = child_id
        self.detail = detail
        self.reason = reason
        msg = f"vendor refresh completion failed for {child_id}"
        if detail:
            msg += f" ({detail})"
        super().__init__(msg)


class VendorRefreshFailureError(VendorRefreshError):
    """Raised when fail_vendor_refresh cannot transition RUNNING -> FAILED.

    The R1-reserved reason ``EXECUTION_INTERRUPTED`` is rejected with a
    bounded error BEFORE any UPDATE (zero row mutation) even though the
    value exists in the model vocabulary — the storage constraint admits
    it for the separately approved R1 recovery transition (DESIGN2-FU3
    F1). Every other bounded-vocabulary reason is legal in R0. The check
    is fail-closed on type: a non-string reason (including an unhashable
    list/dict) is rejected with a bounded error, never a native
    TypeError.
    """

    REASON_RESERVED_EXECUTION_INTERRUPTED: str = "reserved_execution_interrupted"
    REASON_INVALID_FAILURE_REASON: str = "invalid_failure_reason"

    def __init__(self, child_id: object, detail: str | None = None, *, reason: str | None = None) -> None:
        self.child_id = child_id
        self.detail = detail
        self.reason = reason
        msg = f"vendor refresh failure recording failed for {child_id}"
        if detail:
            msg += f" ({detail})"
        super().__init__(msg)
