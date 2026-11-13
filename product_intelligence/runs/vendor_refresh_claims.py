"""Vendor-refresh execution lifecycle primitives (VREF-R0).

Runs-layer only. Provides exactly four lifecycle primitives for
VendorRefreshExecution children of a COMPLETED ResearchRun:

- ``trigger_vendor_refresh``: INSERT a PENDING child (trigger input is
  validated fail-closed first: operator is a string of length 1..128,
  recorded verbatim; trigger_source is a string in the bounded
  vocabulary, non-string values rejected without a native TypeError);
  idempotent on an existing active child; a post-terminal invocation
  creates a NEW child).
- ``claim_vendor_refresh``: CAS PENDING -> RUNNING (atomic single-winner
  claim; one conditional UPDATE).
- ``complete_vendor_refresh``: CAS RUNNING -> COMPLETED, atomically
  publishing the result payload in the same UPDATE (the R0 service
  validates only the bounded V1 schema-version agreement; full codec
  validity is the future R1 producer's and R2 reader's job).
- ``fail_vendor_refresh``: CAS RUNNING -> FAILED with a validated bounded
  failure reason in the same UPDATE (fail-closed on type: a non-string
  reason, including an unhashable list/dict, is rejected with a bounded
  error, never a native TypeError).

These are the COMPLETE set of legal row transitions in R0 (DESIGN2 §3.3
state-transition table). What R0 forbids is EXTRA recovery-based
terminalization of an allegedly stale or interrupted RUNNING execution:
no stale reclaim, no threshold-triggered forced failure, no RUNNING ->
PENDING reset, no automatic retry, no operator-forced
interruption/recovery, and no reassignment of an existing RUNNING attempt.
A stuck RUNNING row keeps occupying its active slot until the separately
approved R1 operational recovery gate resolves it on trusted external
evidence.

What the CAS guarantees (DESIGN2-FU3 F2): the WHERE clause verifies the
row's current stored shape, so at most one concurrent writer can win the
claim and at most one terminal write can commit per row — atomic
single-winner terminalization. It does NOT authenticate the terminal
caller as the original claim winner; no ownership enforcement is claimed
or implemented in R0 (R0 has no execution surface). The R1 gate owns
that decision.

Payload validation (DESIGN2 §3.1, FU1 C7): the R0 complete service
validates ONLY the bounded V1 schema-version agreement — before the
conditional UPDATE, the stored ``result_schema_version`` must equal the
payload's codec schema version, and both must be the frozen V1.
An invalid pairing is rejected with a bounded error BEFORE any UPDATE:
zero row mutation, no malformed COMPLETED row. Full frozen-codec
validity of the payload is NOT an R0 concern: per the frozen DESIGN2 it
belongs to the future R1 producer (the frozen
``encode_research_supplement_result`` before the complete CAS) and the
future R2 reader (the frozen ``decode_research_supplement_result`` in
history replay, failing closed). This module therefore does NOT import
the research core (the architecture guards pin that runs/ stays free of
research imports; the exception mechanism is locked to an unrelated
evaluation harness). No second codec is introduced and the frozen codec
is unmodified.

Concurrency: the UNIQUE(parent_run, active_slot) constraint is the hard
invariant against concurrent double-creation; on an insert conflict the
failing savepoint rolls back and the existing active winner is returned
(7C-A pattern). An unrelated IntegrityError propagates unchanged.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Final

from django.db import IntegrityError, transaction
from django.utils import timezone

from product_intelligence.domain.enums import ResearchRunState
from product_intelligence.runs.errors import (
    VendorRefreshClaimError,
    VendorRefreshCompletionError,
    VendorRefreshError,
    VendorRefreshFailureError,
    VendorRefreshTriggerError,
)
from product_intelligence.runs.models import (
    PriceIntelligenceSnapshot,
    ResearchRun,
    VendorRefreshExecution,
    VendorRefreshFailureReason,
    VendorRefreshState,
    VendorRefreshTriggerSource,
)

__all__ = [
    "VendorRefreshClaimError",
    "VendorRefreshCompletionError",
    "VendorRefreshError",
    "VendorRefreshFailureError",
    "VendorRefreshTriggerError",
    "claim_vendor_refresh",
    "complete_vendor_refresh",
    "fail_vendor_refresh",
    "trigger_vendor_refresh",
]

# The frozen supplement codec (research/commercial_supplement_codec.py)
# supports exactly one schema version: V1. The payload's codec schema
# version is the value of its top-level ``schema_version`` key, exactly
# as the frozen decoder reads it; the bounded agreement check below is
# performed at that level, keeping this runs module free of research
# imports (DESIGN2 §3.1: in R0 the complete service validates only this
# bounded agreement; full codec validity is the future R1 producer's
# and the future R2 reader's job, fail-closed).
_FROZEN_SUPPLEMENT_CODEC_VERSION: Final[int] = 1

# The service-level operator bound (DESIGN2 §3.1: CharField(128),
# "free text, bounded length"). Enforced here, in the service: the
# database CHECK covers non-emptiness only, and SQLite does not enforce
# Django CharField.max_length, so without this check an over-long
# operator would be silently persisted. A valid operator is recorded
# verbatim — no stripping, no truncation.
_MIN_OPERATOR_LEN: Final[int] = 1
_MAX_OPERATOR_LEN: Final[int] = 128


def _active_children(parent_run_id: str):
    """The active (PENDING/RUNNING) children of a parent, if any."""
    return VendorRefreshExecution.objects.filter(
        parent_run_id=parent_run_id,
        state__in=[VendorRefreshState.PENDING, VendorRefreshState.RUNNING],
    )


# ---------------------------------------------------------------------------
# TRIGGER
# ---------------------------------------------------------------------------


def trigger_vendor_refresh(
    run_id: uuid.UUID | str,
    *,
    operator: str,
    trigger_source: str = VendorRefreshTriggerSource.MANAGEMENT_COMMAND,
) -> VendorRefreshExecution:
    """Create or locate a vendor-refresh child for a parent ResearchRun.

    Trigger input (validated fail-closed BEFORE any lookup or INSERT):

    - ``operator`` must be a string of length 1..128 inclusive
      (``invalid_operator``); it is recorded verbatim — no stripping,
      no truncation. The bound is service-level: the database CHECK
      covers non-emptiness only, and SQLite does not enforce
      ``CharField.max_length``. The error names the type or the length,
      never the input's content.
    - ``trigger_source`` must be a string in the bounded vocabulary
      (``invalid_trigger_source``); a non-string value — including an
      unhashable list/dict, which would otherwise leak a native
      ``TypeError`` from the membership test — is rejected here.

    Eligibility (fail-closed, bounded reasons; DESIGN2 §3.3):

    1. parent exists (``parent_not_found``);
    2. parent state is COMPLETED (``parent_not_completed``) —
       PARTIALLY_COMPLETED / FAILED / RUNNING / CREATED are not eligible;
    3. parent has a PriceIntelligenceSnapshot (``no_snapshot``) — a
       defensive invariant (a constructed COMPLETED row always has one;
       a row without one is anomalous and refused);
    4. parent.manufacturer_part_number is non-empty (``no_mpn``).

    The original ResearchSupplementSnapshot may be absent: absence is NOT
    an eligibility error — the refresh history then simply shows
    "original: not recorded".

    The captured binding is ``parent.manufacturer_part_number`` VERBATIM:
    no stripping, no rewriting, no coercion.

    Idempotency (DESIGN2-FU1 C2, concepts 1 and 2; concept 3 is an R3
    requirement, not implemented here):

    - an existing ACTIVE child (PENDING/RUNNING) is returned unchanged —
      nothing is created and nothing is executed;
    - existing TERMINAL history does not block a new explicit attempt: a
      new PENDING child is created (a new attempt, a new timestamped
      evidence point; no prior child is rewritten).

    Concurrency: the UNIQUE(parent_run, active_slot) constraint fires for
    a losing concurrent INSERT; the failing savepoint rolls back and the
    existing active winner is returned. An unrelated IntegrityError
    propagates unchanged (7C-A pattern).

    Raises
    ------
    VendorRefreshTriggerError
        If the parent is not eligible or the trigger input is invalid.
    IntegrityError
        If the insert fails for a reason unrelated to the active-slot
        uniqueness invariant.
    """
    target_id = str(run_id)

    # Trigger input validation (before any parent lookup or INSERT):
    # operator is mandatory self-reported provenance, recorded verbatim
    # and bounded to 1..128 characters; trigger_source is bounded and
    # fail-closed on type. Rejections echo the type or the length, never
    # the (untrusted) input content.
    if not isinstance(operator, str):
        raise VendorRefreshTriggerError(
            run_id=target_id,
            reason=VendorRefreshTriggerError.REASON_INVALID_OPERATOR,
            detail=(
                "operator is the mandatory self-reported identity of the "
                f"trigger initiator; expected a string, "
                f"got {type(operator).__name__}"
            ),
        )
    if not _MIN_OPERATOR_LEN <= len(operator) <= _MAX_OPERATOR_LEN:
        raise VendorRefreshTriggerError(
            run_id=target_id,
            reason=VendorRefreshTriggerError.REASON_INVALID_OPERATOR,
            detail=(
                "operator is the mandatory self-reported identity of the "
                "trigger initiator; expected a string of length "
                f"{_MIN_OPERATOR_LEN} to {_MAX_OPERATOR_LEN} inclusive, "
                f"got length {len(operator)}"
            ),
        )
    if (
        not isinstance(trigger_source, str)
        or trigger_source not in VendorRefreshTriggerSource.ALL
    ):
        raise VendorRefreshTriggerError(
            run_id=target_id,
            reason=VendorRefreshTriggerError.REASON_INVALID_TRIGGER_SOURCE,
            detail=(
                "trigger_source must be one of "
                f"{sorted(VendorRefreshTriggerSource.ALL)}; "
                f"got {type(trigger_source).__name__}"
            ),
        )

    # 1. Parent exists.
    try:
        parent = ResearchRun.objects.get(id=target_id)
    except ResearchRun.DoesNotExist:
        raise VendorRefreshTriggerError(
            run_id=target_id,
            reason=VendorRefreshTriggerError.REASON_PARENT_NOT_FOUND,
            detail=f"no ResearchRun with ID {target_id}",
        )

    # 2. Parent state is COMPLETED.
    if parent.current_state is not ResearchRunState.COMPLETED:
        raise VendorRefreshTriggerError(
            run_id=target_id,
            reason=VendorRefreshTriggerError.REASON_PARENT_NOT_COMPLETED,
            detail=(
                f"parent is in state {parent.current_state.value}, only "
                "COMPLETED is eligible"
            ),
        )

    # 3. Defensive COMPLETED snapshot invariant.
    try:
        parent.price_intelligence_snapshot  # type: ignore[union-attr]
    except PriceIntelligenceSnapshot.DoesNotExist:
        raise VendorRefreshTriggerError(
            run_id=target_id,
            reason=VendorRefreshTriggerError.REASON_NO_SNAPSHOT,
            detail="COMPLETED parent has no PriceIntelligenceSnapshot",
        )

    # 4. A non-empty canonical MPN to refresh.
    if not parent.manufacturer_part_number:
        raise VendorRefreshTriggerError(
            run_id=target_id,
            reason=VendorRefreshTriggerError.REASON_NO_MPN,
            detail=(
                "parent has no canonical manufacturer_part_number to "
                "refresh"
            ),
        )

    # The original ResearchSupplementSnapshot is deliberately NOT checked:
    # its absence is a legal "original: not recorded" state (DESIGN2 §8.4).

    # Concept 1: an existing active child is returned unchanged.
    existing_active = _active_children(target_id).first()
    if existing_active is not None:
        return existing_active

    # Concept 2: terminal history does not block a new explicit attempt.
    # Create a NEW PENDING child, capturing the parent's canonical MPN
    # verbatim.
    created_child: VendorRefreshExecution | None = None
    saved_integrity_error: IntegrityError | None = None
    try:
        with transaction.atomic():
            created_child = VendorRefreshExecution.objects.create(
                parent_run=parent,
                requested_mpn=parent.manufacturer_part_number,
                state=VendorRefreshState.PENDING,
                active_slot=1,
                trigger_source=trigger_source,
                operator=operator,
            )
    except IntegrityError as exc:
        # The UNIQUE(parent_run, active_slot) constraint may have fired
        # against a concurrent winner. The failing savepoint has already
        # rolled back here; the winner is looked up OUTSIDE the failed
        # scope.
        saved_integrity_error = exc

    if saved_integrity_error is not None:
        winner = _active_children(target_id).first()
        if winner is not None:
            return winner
        # No active winner — the IntegrityError was unrelated.
        # Propagate the ORIGINAL IntegrityError, do not convert it.
        raise saved_integrity_error

    # No collision — return the exact object produced by create(), not a
    # post-commit re-query.
    assert created_child is not None
    return created_child


# ---------------------------------------------------------------------------
# CLAIM
# ---------------------------------------------------------------------------


def claim_vendor_refresh(child_id: uuid.UUID | str) -> VendorRefreshExecution:
    """Claim a PENDING vendor-refresh child (PENDING -> RUNNING).

    One conditional UPDATE (compare-and-set): only succeeds if the child
    is currently PENDING with the active slot and no start timestamp. At
    most one caller can win the claim; the loser gets
    ``VendorRefreshClaimError`` and performs no further work. There is no
    network call here — the claim is the only prerequisite for the
    (R1) execution to issue its single Vendor lookup.

    The claim does not modify ``operator`` (the recorded trigger
    initiator) or ``requested_mpn``. The CAS guarantees an atomic
    single-winner claim, NOT the identity of the winner for later
    verification (DESIGN2-FU3 F2).

    Raises
    ------
    VendorRefreshClaimError
        If the child cannot be claimed (not found, or not PENDING).
    """
    target_id = str(child_id)
    now = timezone.now()

    rows = VendorRefreshExecution.objects.filter(
        id=target_id,
        state=VendorRefreshState.PENDING,
        active_slot=1,
        started_at__isnull=True,
    ).update(
        state=VendorRefreshState.RUNNING,
        started_at=now,
    )

    if rows == 0:
        try:
            child = VendorRefreshExecution.objects.get(id=target_id)
        except VendorRefreshExecution.DoesNotExist:
            raise VendorRefreshClaimError(
                child_id=target_id,
                detail=f"no VendorRefreshExecution with ID {target_id}",
            )
        raise VendorRefreshClaimError(
            child_id=target_id,
            detail=f"child is in state {child.state}, expected PENDING",
        )

    return VendorRefreshExecution.objects.get(id=target_id)


# ---------------------------------------------------------------------------
# COMPLETE
# ---------------------------------------------------------------------------


def complete_vendor_refresh(
    child_id: uuid.UUID | str,
    result_schema_version: int,
    result_payload: object,
    *,
    at: datetime | None = None,
) -> VendorRefreshExecution:
    """Complete a RUNNING vendor-refresh child (RUNNING -> COMPLETED).

    One atomic conditional UPDATE writes ``state``, ``active_slot=NULL``,
    ``finished_at``, ``result_schema_version``, and ``result_payload``
    together: no committed state exists in which a COMPLETED child lacks
    its payload.

    Before the UPDATE, the bounded version agreement is validated
    (DESIGN2 §3.4 step 8, FU1 C7) — at the dict level, so this runs
    module imports no research code:

    - ``result_schema_version`` must be exactly the frozen supplement
      codec version (V1 = 1);
    - ``result_payload`` must be a dict carrying the codec's top-level
      ``schema_version`` key;
    - the stored version must equal the payload's codec schema version
      (the frozen decoder reads exactly that key).

    An invalid pairing is rejected with ``VendorRefreshCompletionError``
    BEFORE any UPDATE: zero row mutation, no malformed COMPLETED row.
    That bounded V1 schema-version agreement is EXACTLY what the R0
    complete service validates — nothing more. Full codec validity of
    the payload internals is not an R0 concern: per the frozen DESIGN2
    it belongs to the future R1 producer (the frozen encoder, before
    the complete CAS) and the future R2 reader (the frozen decoder in
    history replay, failing closed) — DESIGN2 §3.1. No new codec is
    introduced and the frozen codec is unmodified.

    Raises
    ------
    VendorRefreshCompletionError
        If the version/payload input is invalid, or the child cannot be
        completed (not found, or not RUNNING).
    """
    target_id = str(child_id)

    # --- Pre-mutation validation (zero row mutation on failure) ---------
    if type(result_schema_version) is not int:
        raise VendorRefreshCompletionError(
            child_id=target_id,
            detail=(
                "result_schema_version must be an int agreeing with the "
                f"frozen supplement codec version "
                f"({_FROZEN_SUPPLEMENT_CODEC_VERSION}); got "
                f"{type(result_schema_version).__name__}"
            ),
            reason=VendorRefreshCompletionError.REASON_INVALID_SCHEMA_VERSION,
        )
    if result_schema_version != _FROZEN_SUPPLEMENT_CODEC_VERSION:
        raise VendorRefreshCompletionError(
            child_id=target_id,
            detail=(
                "result_schema_version must agree with the frozen "
                f"supplement codec version ({_FROZEN_SUPPLEMENT_CODEC_VERSION}); "
                f"got {result_schema_version}"
            ),
            reason=VendorRefreshCompletionError.REASON_INVALID_SCHEMA_VERSION,
        )
    if not isinstance(result_payload, dict):
        raise VendorRefreshCompletionError(
            child_id=target_id,
            detail=(
                "result_payload must be the codec-encoded dict produced "
                "by the frozen encode_research_supplement_result; got "
                f"{type(result_payload).__name__}"
            ),
            reason=VendorRefreshCompletionError.REASON_INVALID_PAYLOAD,
        )
    # The payload's codec schema version, exactly as the frozen decoder
    # reads it: the top-level `schema_version` key.
    payload_version = result_payload.get("schema_version")
    if payload_version != _FROZEN_SUPPLEMENT_CODEC_VERSION:
        raise VendorRefreshCompletionError(
            child_id=target_id,
            detail=(
                "result_payload does not carry the frozen supplement "
                f"codec schema version ({_FROZEN_SUPPLEMENT_CODEC_VERSION}); "
                f"got {payload_version!r}"
            ),
            reason=VendorRefreshCompletionError.REASON_INVALID_PAYLOAD,
        )
    # Bounded agreement: the stored version equals the payload's codec
    # schema version (both the frozen V1).
    if result_schema_version != payload_version:
        raise VendorRefreshCompletionError(
            child_id=target_id,
            detail=(
                f"result_schema_version {result_schema_version} does not "
                f"agree with the payload's codec schema version "
                f"{payload_version!r}"
            ),
            reason=VendorRefreshCompletionError.REASON_INVALID_PAYLOAD,
        )

    now = at if at is not None else timezone.now()

    rows = VendorRefreshExecution.objects.filter(
        id=target_id,
        state=VendorRefreshState.RUNNING,
        active_slot=1,
        finished_at__isnull=True,
    ).update(
        state=VendorRefreshState.COMPLETED,
        active_slot=None,
        finished_at=now,
        result_schema_version=result_schema_version,
        result_payload=result_payload,
    )

    if rows == 0:
        try:
            child = VendorRefreshExecution.objects.get(id=target_id)
        except VendorRefreshExecution.DoesNotExist:
            raise VendorRefreshCompletionError(
                child_id=target_id,
                detail=f"no VendorRefreshExecution with ID {target_id}",
            )
        raise VendorRefreshCompletionError(
            child_id=target_id,
            detail=f"child is in state {child.state}, expected RUNNING",
        )

    return VendorRefreshExecution.objects.get(id=target_id)


# ---------------------------------------------------------------------------
# FAIL
# ---------------------------------------------------------------------------


def fail_vendor_refresh(
    child_id: uuid.UUID | str,
    failure_reason: str,
    *,
    at: datetime | None = None,
) -> VendorRefreshExecution:
    """Fail a RUNNING vendor-refresh child (RUNNING -> FAILED).

    One atomic conditional UPDATE writes ``state``, ``active_slot=NULL``,
    ``finished_at``, and ``failure_reason`` together; the result fields
    remain NULL.

    ``failure_reason`` is validated against the bounded vocabulary
    MINUS the R1-reserved value ``EXECUTION_INTERRUPTED`` (DESIGN2-FU3
    F1). The reserved value exists in the model vocabulary so the
    separately approved R1 recovery transition can store it without a
    schema change, but it is NOT a legal argument to the R0 fail
    primitive: passing it is rejected with a bounded error BEFORE any
    UPDATE — zero row mutation, even over a row whose full CAS
    preconditions hold. Every other bounded-vocabulary reason is
    accepted (no over-rejection).

    The check is fail-closed on type: a non-string reason — including
    an unhashable list/dict, which would otherwise leak a native
    ``TypeError`` from the set membership test — is rejected with
    ``invalid_failure_reason`` BEFORE any UPDATE; the error names the
    type, never the content.

    Raises
    ------
    VendorRefreshFailureError
        If the reason is the reserved R1 value, if the reason is outside
        the bounded vocabulary, or if the child cannot be failed (not
        found, or not RUNNING).
    """
    target_id = str(child_id)

    # --- Pre-mutation validation (zero row mutation on failure) ---------
    # The reserved-value check stays first (DESIGN2-FU3 F1); the ==
    # comparison is safe for any type, so non-string input cannot
    # bypass it, and the reserved string value always maps to
    # reserved_execution_interrupted before the type check below.
    if failure_reason == VendorRefreshFailureReason.EXECUTION_INTERRUPTED:
        raise VendorRefreshFailureError(
            child_id=target_id,
            detail=(
                "EXECUTION_INTERRUPTED is reserved for the separately "
                "approved R1 recovery transition; the R0 fail primitive "
                "does not accept it (zero row mutation)"
            ),
            reason=VendorRefreshFailureError.REASON_RESERVED_EXECUTION_INTERRUPTED,
        )
    if (
        not isinstance(failure_reason, str)
        or failure_reason not in VendorRefreshFailureReason.ALL
    ):
        raise VendorRefreshFailureError(
            child_id=target_id,
            detail=(
                "failure_reason must be one of "
                f"{sorted(VendorRefreshFailureReason.R0_LEGAL)}; "
                f"got {type(failure_reason).__name__}"
            ),
            reason=VendorRefreshFailureError.REASON_INVALID_FAILURE_REASON,
        )

    now = at if at is not None else timezone.now()

    rows = VendorRefreshExecution.objects.filter(
        id=target_id,
        state=VendorRefreshState.RUNNING,
        active_slot=1,
        finished_at__isnull=True,
    ).update(
        state=VendorRefreshState.FAILED,
        active_slot=None,
        finished_at=now,
        failure_reason=failure_reason,
    )

    if rows == 0:
        try:
            child = VendorRefreshExecution.objects.get(id=target_id)
        except VendorRefreshExecution.DoesNotExist:
            raise VendorRefreshFailureError(
                child_id=target_id,
                detail=f"no VendorRefreshExecution with ID {target_id}",
            )
        raise VendorRefreshFailureError(
            child_id=target_id,
            detail=f"child is in state {child.state}, expected RUNNING",
        )

    return VendorRefreshExecution.objects.get(id=target_id)
