"""Shared vendor-refresh trigger + claim decision service
(VENDOR-REFRESH-WEB, extracted from VREF-R1-3 decision M3 Option A +
M4 SQLite A3 — behavior-identical).

The R1-3 management command and the web POST trigger share EXACTLY ONE
serialized decision: inside one short ``transaction.atomic()`` whose
FIRST statement is the zero-row write lock on
``runs_vendorrefreshexecution`` (``active_slot=2`` — a value the
storage CHECK constraint admits on no row) that mutates NOTHING while
SQLite semantics grant the transaction the file RESERVED lock:

    [L]  the zero-row lock statement (serializes every other writer);
    [b]  the fresh active-children snapshot under the lock;
    [D1] an active child (PENDING or RUNNING) is reported and left
         untouched — no INSERT, no claim, no executor call;
    [c]  the latest terminal child (fresh, under the lock):
         max(finished_at), tie-break id DESC;
    [D2] the five-minute repeat safeguard (STRICT ``< 300 s``); a
         refusal leaves NO new child and makes zero network calls;
    [d]  the R0 trigger (INSERT; eligibility re-checked in the
         service; the UNIQUE constraint remains the hard invariant);
    [O]  the ownership proof under the lock: if the returned child
         was in the [b] snapshot, this invocation did NOT create it —
         fail-closed (the transaction is marked to roll back; the
         PENDING row never reaches durability alone);
    [f]  THE one and only claim of this invocation (PENDING ->
         RUNNING, same transaction).

M3 Option A is preserved verbatim: only the invocation that creates
the child may claim and execute it. A PENDING child is NEVER claimed
or executed by this service.

This module is the SINGLE claim call site of the application:
``claim_vendor_refresh`` is referenced by exactly one call in this
module. The claim does NOT catch claim errors: a propagated claim
failure (structurally unreachable under the lock) escapes the
transaction (total rollback) and the caller's outer boundary reports
it — it is NEVER caught to continue.

The transaction contains no network, no sleeps, no I/O of any kind.
COMMIT precedes any post-claim execution: the caller performs the
post-commit execution (the public execution API) OUTSIDE this
function — this service never executes.

Bounded outcomes (``VendorRefreshTriggerDecision.kind``):

* ``created``               — this invocation created AND claimed the
                              child (``created_child`` is the RUNNING
                              row); the caller owns the post-commit
                              execution;
* ``in_progress``           — an existing active child (PENDING or
                              RUNNING) is reported (``active_children``)
                              and left untouched;
* ``in_progress_anomaly``   — [O] fired: the trigger returned a
                              pre-existing active child; the INSERT was
                              rolled back; the child is reported and
                              left untouched (structurally unreachable
                              under the lock — a competing writer must
                              hold the same RESERVED lock to INSERT);
* ``cooldown``              — the latest terminal child finished less
                              than 300 s ago and ``force_repeat`` was
                              not given; NO new child, zero network
                              (``cooldown_child`` + ``cooldown_age_
                              seconds`` carry the bounded reporting
                              data);
* ``ineligible``            — the R0 trigger's bounded parent-eligibility
                              refusal (``ineligible_reason``); the
                              transaction rolled back: zero mutation;
* ``database_busy``         — contention beyond the busy timeout (or
                              another definite database failure) at the
                              serialization point; the transaction never
                              committed: ZERO mutation; manual re-run.

No ``force_repeat`` bypass of the in-progress report exists anywhere:
the repeat safeguard is the ONLY thing a bypass flag can affect.

Import discipline: this is a ``runs/`` module. It imports the runs
lifecycle (claims + models + bounded errors) and Django ORM only — NO
``product_intelligence.execution`` import (the O4 carve-out remains the
command ONLY: the caller performs the post-commit execution), NO
provider, NO web, NO research, NO domain import (the domain vocabulary
is reached through the runs models).
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import timedelta

from django.db import OperationalError, transaction
from django.utils import timezone

from product_intelligence.runs.errors import VendorRefreshTriggerError
from product_intelligence.runs.models import (
    VendorRefreshExecution,
    VendorRefreshState,
    VendorRefreshTriggerSource,
)
from product_intelligence.runs.vendor_refresh_claims import (
    claim_vendor_refresh,
    trigger_vendor_refresh,
)

__all__ = [
    "VendorRefreshTriggerDecision",
    "trigger_and_claim_vendor_refresh",
]

# The five-minute repeat safeguard window (VREF-R1-3, O7: STRICT
# ``< 300 s`` refusal against the latest terminal child's ``finished_at``;
# the clock is sampled inside the serialized transaction — single host,
# single clock).
_COOLDOWN_SECONDS = 300

# The zero-row lock statement targets a value the storage CHECK
# constraint (``active_slot`` in {1, NULL}) admits on no row: it can
# match ZERO rows and mutate NOTHING, while SQLite grants the
# executing transaction the file RESERVED lock (VREF-R1-3, M4 A3).
_LOCK_SLOT = 2

# --- Bounded decision kinds -------------------------------------------

KIND_CREATED = "created"
KIND_IN_PROGRESS = "in_progress"
KIND_IN_PROGRESS_ANOMALY = "in_progress_anomaly"
KIND_COOLDOWN = "cooldown"
KIND_INELIGIBLE = "ineligible"
KIND_DATABASE_BUSY = "database_busy"


@dataclass(frozen=True)
class VendorRefreshTriggerDecision:
    """The bounded outcome of one serialized trigger + claim decision.

    Exactly the reporting data of the pre-extraction command branches —
    no more. The caller (command / web view) maps the kind to its own
    bounded surface (stdout + exit code / redirect + page notice).

    The ``KIND_*`` class attributes are the bounded kind vocabulary,
    reachable through the runs public API without importing the
    service submodule (the web layer and the command compare against
    these).
    """

    KIND_CREATED = KIND_CREATED
    KIND_IN_PROGRESS = KIND_IN_PROGRESS
    KIND_IN_PROGRESS_ANOMALY = KIND_IN_PROGRESS_ANOMALY
    KIND_COOLDOWN = KIND_COOLDOWN
    KIND_INELIGIBLE = KIND_INELIGIBLE
    KIND_DATABASE_BUSY = KIND_DATABASE_BUSY

    kind: str
    # ``created``: the durably RUNNING child this invocation created
    # and claimed (the post-claim executor's input).
    created_child: VendorRefreshExecution | None = None
    # ``in_progress`` / ``in_progress_anomaly``: the reported active
    # children (left untouched; never claimed, never executed).
    active_children: tuple = ()
    # ``cooldown``: the blocking latest terminal child + its integer
    # age in seconds at the in-transaction clock sample.
    cooldown_child: VendorRefreshExecution | None = None
    cooldown_age_seconds: int | None = None
    # ``ineligible``: the bounded trigger-service refusal reason
    # (content-free vocabulary member).
    ineligible_reason: str | None = None


def trigger_and_claim_vendor_refresh(
    run_id: uuid.UUID | str,
    *,
    operator: str,
    trigger_source: str = VendorRefreshTriggerSource.MANAGEMENT_COMMAND,
    force_repeat: bool = False,
) -> VendorRefreshTriggerDecision:
    """One serialized trigger + claim decision for a parent run.

    Parameters mirror the R0 trigger service fail-closed input
    contract: ``operator`` is the self-reported trigger initiator
    (recorded verbatim; the trigger service validates 1..128) and
    ``trigger_source`` is a bounded vocabulary member (the trigger
    service validates membership). ``force_repeat`` bypasses the
    cooldown refusal ONLY.

    Returns a ``VendorRefreshTriggerDecision`` (see module docstring
    for the bounded kinds). A claim failure (structurally unreachable
    under the lock) PROPAGATES: the transaction rolls back completely
    and no partial PENDING row survives.
    """
    target_id = str(run_id)

    try:
        with transaction.atomic():
            # [L] — the zero-row lock statement: mutates NOTHING,
            # acquires the file RESERVED lock, and serializes every
            # other writer behind this transaction.
            VendorRefreshExecution.objects.filter(
                parent_run_id=target_id, active_slot=_LOCK_SLOT
            ).update(active_slot=_LOCK_SLOT)

            # [b] — fresh active-children snapshot under the lock.
            active_children = list(
                VendorRefreshExecution.objects.filter(
                    parent_run_id=target_id,
                    state__in=sorted(VendorRefreshState.ACTIVE_STATES),
                ).order_by("created_at", "id")
            )

            # [D1] — an active child (PENDING or RUNNING) is reported
            # and left untouched: NO INSERT, NO claim, NO executor
            # call. A PENDING child is never claimed by this service
            # (M3 Option A).
            if active_children:
                return VendorRefreshTriggerDecision(
                    kind=KIND_IN_PROGRESS,
                    active_children=tuple(active_children),
                )

            # [c] — the latest terminal child (fresh, under the
            # lock): max(finished_at), tie-break id DESC
            # (deterministic; O7).
            latest_terminal = (
                VendorRefreshExecution.objects.filter(
                    parent_run_id=target_id,
                    state__in=sorted(VendorRefreshState.TERMINAL_STATES),
                )
                .order_by("-finished_at", "-id")
                .first()
            )

            # [D2] — the five-minute repeat safeguard (STRICT
            # ``< 300 s``): refusal leaves NO new child and makes
            # zero network calls. ``force_repeat`` bypasses THIS
            # refusal only.
            now = timezone.now()
            if (
                latest_terminal is not None
                and latest_terminal.finished_at is not None
                and (now - latest_terminal.finished_at)
                < timedelta(seconds=_COOLDOWN_SECONDS)
                and not force_repeat
            ):
                return VendorRefreshTriggerDecision(
                    kind=KIND_COOLDOWN,
                    cooldown_child=latest_terminal,
                    cooldown_age_seconds=int(
                        (now - latest_terminal.finished_at).total_seconds()
                    ),
                )

            # [d] — the R0 trigger (INSERT; eligibility re-checked in
            # the service under the lock; the UNIQUE constraint
            # remains the hard invariant for any writer that does not
            # take the lock).
            child = trigger_vendor_refresh(
                target_id,
                operator=operator,
                trigger_source=trigger_source,
            )

            # [O] — the ownership proof under the lock: if the
            # returned child was in the step-[b] snapshot, this
            # invocation did NOT create it. Fail-closed: the
            # transaction is marked to ROLL BACK (the INSERT is
            # discarded — a PENDING row never reaches durability
            # alone on this path), NO claim, NO executor call.
            # Structurally unreachable under the lock (a competing
            # writer must hold the same RESERVED lock to INSERT).
            if child.id in {a.id for a in active_children}:
                transaction.set_rollback(True)
                return VendorRefreshTriggerDecision(
                    kind=KIND_IN_PROGRESS_ANOMALY,
                    active_children=(child,),
                )

            # [f] — THE one and only claim of this invocation
            # (PENDING -> RUNNING, same transaction; exactly one on
            # success, zero on every other path). A raise here
            # (structurally unreachable) propagates OUT of the atomic
            # block -> total rollback -> no row. It is NEVER caught
            # to continue.
            claimed = claim_vendor_refresh(child.id)
            return VendorRefreshTriggerDecision(
                kind=KIND_CREATED, created_child=claimed
            )
    except VendorRefreshTriggerError as err:
        # [d] — the parent is not eligible (re-checked in the service
        # under the lock). The transaction rolled back: zero mutation.
        # Bounded reason (content-free).
        return VendorRefreshTriggerDecision(
            kind=KIND_INELIGIBLE, ineligible_reason=err.reason
        )
    except OperationalError:
        # Contention beyond the busy timeout (or another definite
        # database failure) at the serialization point. The transaction
        # never committed: ZERO mutation (the lock statement changed 0
        # rows by construction), zero claims, zero lookups. Bounded
        # report; NO automatic re-run.
        return VendorRefreshTriggerDecision(kind=KIND_DATABASE_BUSY)
