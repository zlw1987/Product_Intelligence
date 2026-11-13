"""Vendor commercial refresh command (VREF-R1-3, decisions M3/M4).

The normal vendor-refresh command: one invocation triggers, claims, and
executes exactly ONE vendor-refresh child for a COMPLETED parent
research run — or reports why it did not, with zero mutation and zero
network calls.

Approved architecture (design SHA
``52d877d55c81c3e07c14027639264faaa07859a3``, sections 3.3 / 3.4 /
5 / 8.3 / 10.2 / 11):

* **M3 Option A** — only the invocation that creates the child may
  claim and execute it. The ownership proof is structural: the active-
  children snapshot is read UNDER the database write lock, and a
  competing writer must hold the same lock to INSERT, so if the
  snapshot is empty when the trigger's INSERT succeeds, THIS invocation
  created the row. A pre-existing active child (PENDING or RUNNING) is
  REPORTED (id, state, recorded operator, created_at/started_at) and
  left untouched — no claim, no execution, zero network calls. A
  PENDING child is NEVER claimed or executed by this command.
* **M4 SQLite A3** — the five-minute repeat safeguard is atomic with
  the decision + INSERT + claim inside ONE short ``transaction.atomic()``
  whose FIRST statement is a zero-row write on
  ``runs_vendorrefreshexecution`` (``active_slot=2`` — a value the
  storage CHECK constraint admits on no row) that mutates NOTHING while
  SQLite semantics grant the transaction the file RESERVED lock. Every
  other writer serializes behind it. The transaction contains no
  network, no sleeps, no I/O of any kind. COMMIT precedes the Vendor
  HTTP call (I10). ``--force-repeat`` bypasses the cooldown refusal
  ONLY — it does not bypass the in-progress report and it records
  nothing on the row.
* **The ONLY claim call site in R1** — ``claim_vendor_refresh`` is
  referenced by exactly one call in this module, inside the serialized
  transaction. A claim failure (structurally unreachable under the
  lock) propagates OUT of the transaction (total rollback) and is
  bounded at the outer boundary; it is NEVER caught to continue. The
  post-claim executor (public execution API) never claims.
* **Post-commit execution** — after COMMIT the child is durably
  RUNNING and the SAME invocation calls the public execution entry
  exactly once; the executor's bounded outcomes (T1-T4) are mapped to
  the command outcome classes below.

Bounded stdout contract (design section 8.3): every line starts with
``vendor refresh: ``; lines carry the parent run id, child ids, bounded
state/reason/lookup_status vocabulary values, the recorded operator,
bounded timestamps, and the command outcome class. No secrets, no raw
exception text, no raw private Vendor response content, no base URL,
and no reflection of untrusted input (an invalid identifier is refused
without echoing it).

Outcome classes:

* ``INELIGIBLE`` — [S0] invalid parent-run UUID / invalid operator
  bound, or the trigger service's bounded parent-eligibility refusal
  (zero mutation; the serialized transaction rolled back); non-zero
  exit.
* ``IN_PROGRESS`` — an active child (PENDING or RUNNING) exists;
  reported and left untouched (zero mutation, zero network); exit 0.
* ``COOLDOWN_REFUSAL`` — the latest terminal child finished less than
  300 s ago and ``--force-repeat`` was not given (zero mutation, zero
  network); exit 0.
* ``CREATED_EXECUTED`` — reported as the ``child-created`` line; this
  invocation created, claimed, and executed the child. Followed by the
  child's terminal outcome:
* ``COMPLETED`` — the child is durably COMPLETED (T1); exit 0.
* ``FAILED`` — the child is durably FAILED by this invocation's single
  bounded post-claim defect write (T1 fail outcome, bounded R0_LEGAL
  reason); exit 0.
* ``TERMINAL_REPORTED`` — the actual durable state is reported
  verbatim (T2 lost-terminal-CAS report, the not-found anomaly, or a
  non-terminal read-established anomaly; no second terminal write, no
  assertion); exit 0.
* ``TERMINALIZATION_NOT_RECORDED`` — T3 (the fresh read established the
  current durable shape; the child is not terminal); non-zero exit.
* ``TERMINALIZATION_OUTCOME_UNKNOWN`` — T4 (neither outcome is
  established; manual re-check); non-zero exit.
* ``DATABASE_BUSY`` — contention beyond the busy timeout (or another
  definite database failure) at the serialization point; the
  transaction rolled back (zero mutation); manual re-run; non-zero
  exit.
* ``UNEXPECTED_ERROR`` — a contract defect at the terminal CAS (T2b),
  a propagated claim failure (structurally unreachable), or any other
  non-bounded raise (the ``pilot_check`` non-zero class; bounded
  output — the exception type name only, never raw text); non-zero
  exit.

Exit codes: 0 for the bounded outcomes (IN_PROGRESS, COOLDOWN_REFUSAL,
COMPLETED, FAILED, TERMINAL_REPORTED); 2 for INELIGIBLE; 3 for
TERMINALIZATION_NOT_RECORDED / TERMINALIZATION_OUTCOME_UNKNOWN /
UNEXPECTED_ERROR; 4 for DATABASE_BUSY.

Arguments: exactly ONE positional (the PARENT run UUID), ``--operator``
(required, 1..128, recorded verbatim — self-reported provenance, NOT
authentication), and ``--force-repeat`` (optional, cooldown bypass
only). There is NO child-id positional and NO other flag.

The command surface is host-side: authorization is controlled Windows
host access on the deployment host (frozen DESIGN2 section 4.2); no
Django authentication, no URL, no POST surface. The R1-4 recovery
command and recovery surface do NOT exist (BLOCKED pending O8): no
recovery flag, no evidence mechanism, no reserved-reason writer is
provided by this module.

Import discipline (design section 10.1, O4): this module is the ONLY
``runs/`` module importing the ``product_intelligence.execution``
public API (the outer-surface direction, mirroring ``web``); it imports
NO provider, NO web, NO research, and NO domain symbol. The concrete
adapter is constructed only inside the execution core (S7), strictly
post-commit, from the factory supplied by the execution runtime —
never here.
"""

from __future__ import annotations

import sys
import uuid
from datetime import timedelta

from django.core.management.base import BaseCommand
from django.db import OperationalError, transaction
from django.utils import timezone

from product_intelligence.execution import (
    VendorRefreshExecutionError,
    execute_claimed_vendor_refresh_with_default_providers,
)
from product_intelligence.runs import (
    VendorRefreshExecution,
    VendorRefreshFailureReason,
    VendorRefreshState,
    VendorRefreshTriggerError,
    VendorRefreshTriggerSource,
    claim_vendor_refresh,
    trigger_vendor_refresh,
)

# Bounded exit codes (design section 8.3).
EXIT_BOUNDED = 0
EXIT_INELIGIBLE = 2
EXIT_UNEXPECTED = 3
EXIT_DATABASE_BUSY = 4

# The five-minute repeat safeguard window (design section 3.4, O7:
# STRICT ``< 300 s`` refusal against the latest terminal child's
# ``finished_at``; the clock is sampled inside the serialized
# transaction — single host, single clock).
_COOLDOWN_SECONDS = 300

# The service-level operator bound (frozen R0 contract, recorded
# verbatim; the command re-checks it at [S0] so an out-of-bounds
# operator is refused before ANY database access).
_OPERATOR_MIN_LEN = 1
_OPERATOR_MAX_LEN = 128

# The zero-row lock statement targets a value the storage CHECK
# constraint (``active_slot`` in {1, NULL}) admits on no row: it can
# match ZERO rows and mutate NOTHING, while SQLite grants the
# executing transaction the file RESERVED lock (design section 3.4
# A3; verified semantics, Appendix A).
_LOCK_SLOT = 2

# The persisted post-claim defect reasons: a command-invoked executor
# failure carrying one of these means the child was durably FAILED by
# the single bounded fail write (T1 fail outcome).
_PERSISTED_FAILURE_REASONS = frozenset({
    VendorRefreshFailureReason.MPN_BINDING_VIOLATION,
    VendorRefreshFailureReason.VENDOR_LOOKUP_CONFIG_MISSING,
    VendorRefreshFailureReason.MPN_QUERY_NORMALIZATION_MISMATCH,
    VendorRefreshFailureReason.RESULT_ENCODING_FAILED,
    VendorRefreshFailureReason.INTERNAL_ERROR,
})

# The T2b explicit terminal-CAS input-rejection reasons (contract /
# programming defects, NOT CAS losers): non-zero exit, bounded report.
_T2B_CONTRACT_DEFECT_REASONS = frozenset({
    "invalid_schema_version",
    "invalid_payload",
    "invalid_failure_reason",
    "reserved_execution_interrupted",
})


class Command(BaseCommand):
    help = (
        "Trigger, claim, and execute one vendor commercial refresh for "
        "a COMPLETED research run."
    )

    def add_arguments(self, parser) -> None:
        parser.add_argument(
            "parent_run",
            help="The UUID of the parent research run (must be COMPLETED).",
        )
        parser.add_argument(
            "--operator",
            required=True,
            help=(
                "Self-reported operator identity (1..128 characters, "
                "recorded verbatim). Provenance, not authentication."
            ),
        )
        parser.add_argument(
            "--force-repeat",
            action="store_true",
            help=(
                "Allow a new refresh within the five-minute repeat "
                "safeguard window (cooldown bypass only; an in-progress "
                "child still blocks, and nothing is recorded on the row)."
            ),
        )

    def handle(self, *args, **options):
        try:
            exit_code = self._run(options)
        except Exception as exc:  # noqa: BLE001 - the bounded outer boundary below
            # The bounded outer boundary (the ``pilot_check`` non-zero
            # class): any non-bounded raise — including a propagated
            # claim failure, which is structurally unreachable under the
            # lock and which is NEVER caught to continue (the serialized
            # transaction has already rolled back) — is reported with
            # the exception TYPE NAME ONLY: no raw exception text, no
            # untrusted input content.
            self._write(
                f"vendor refresh: outcome: UNEXPECTED_ERROR "
                f"reason={type(exc).__name__}"
            )
            self._write(
                "vendor refresh: note: an unexpected error terminated the "
                "invocation; no further action was taken; manual re-check"
            )
            exit_code = EXIT_UNEXPECTED
        sys.exit(exit_code)

    # ------------------------------------------------------------------
    # The invocation flow (design section 10.2, NORMAL COMMAND)
    # ------------------------------------------------------------------

    def _run(self, options: dict) -> int:
        parent_arg = options["parent_run"]
        operator = options["operator"]
        force_repeat = bool(options["force_repeat"])

        # [S0] — argument validation. ZERO DB access, zero network: an
        # ineligible invocation must not even read the database. The
        # untrusted input is never reflected in the output.
        try:
            parent_id = str(uuid.UUID(str(parent_arg)))
        except (TypeError, ValueError, AttributeError):
            self._write(
                "vendor refresh: outcome: INELIGIBLE reason=invalid_parent_run_uuid"
            )
            self._write(
                "vendor refresh: detail: the parent run identifier is not "
                "a valid UUID"
            )
            return EXIT_INELIGIBLE
        if not isinstance(operator, str) or not (
            _OPERATOR_MIN_LEN <= len(operator) <= _OPERATOR_MAX_LEN
        ):
            self._write("vendor refresh: outcome: INELIGIBLE reason=invalid_operator")
            self._write(
                "vendor refresh: detail: the operator must be 1..128 "
                "characters, recorded verbatim"
            )
            return EXIT_INELIGIBLE

        # [S1] — informational display read (read-only; may be stale by
        # the time of [S2] — the decision below is authoritative, this
        # is human information only).
        self._display_state(parent_id)

        # [S2] — the serialized short write transaction (M4 A3): the
        # safeguard decision, the trigger INSERT, and THE one and only
        # claim of this invocation, committed BEFORE any network
        # activity. No network, no sleeps, no I/O inside.
        claimed = None
        try:
            with transaction.atomic():
                # [L] — the zero-row lock statement: mutates NOTHING,
                # acquires the file RESERVED lock, and serializes every
                # other writer behind this transaction.
                VendorRefreshExecution.objects.filter(
                    parent_run_id=parent_id, active_slot=_LOCK_SLOT
                ).update(active_slot=_LOCK_SLOT)

                # [b] — fresh active-children snapshot under the lock.
                active_children = list(
                    VendorRefreshExecution.objects.filter(
                        parent_run_id=parent_id,
                        state__in=sorted(VendorRefreshState.ACTIVE_STATES),
                    ).order_by("created_at", "id")
                )

                # [D1] — an active child (PENDING or RUNNING) is
                # reported and left untouched: NO INSERT, NO claim, NO
                # executor call, zero network. A PENDING child is never
                # claimed or executed by this command (M3 Option A).
                if active_children:
                    self._write("vendor refresh: outcome: IN_PROGRESS")
                    for child in active_children:
                        self._write(self._child_line(child))
                    return EXIT_BOUNDED

                # [c] — the latest terminal child (fresh, under the
                # lock): max(finished_at), tie-break id DESC
                # (deterministic; O7).
                latest_terminal = (
                    VendorRefreshExecution.objects.filter(
                        parent_run_id=parent_id,
                        state__in=sorted(VendorRefreshState.TERMINAL_STATES),
                    )
                    .order_by("-finished_at", "-id")
                    .first()
                )

                # [D2] — the five-minute repeat safeguard (STRICT
                # ``< 300 s``): refusal leaves NO new child, makes zero
                # network calls. ``--force-repeat`` bypasses THIS
                # refusal only.
                now = timezone.now()
                if (
                    latest_terminal is not None
                    and latest_terminal.finished_at is not None
                    and (now - latest_terminal.finished_at)
                    < timedelta(seconds=_COOLDOWN_SECONDS)
                    and not force_repeat
                ):
                    self._write("vendor refresh: outcome: COOLDOWN_REFUSAL")
                    age_seconds = int(
                        (now - latest_terminal.finished_at).total_seconds()
                    )
                    self._write(
                        "vendor refresh: blocking-child "
                        f"{latest_terminal.id} state={latest_terminal.state} "
                        f"finished-at={latest_terminal.finished_at.isoformat()} "
                        f"age-seconds={age_seconds}"
                    )
                    return EXIT_BOUNDED

                # [d] — the R0 trigger (INSERT; eligibility re-checked
                # in the service; the UNIQUE constraint remains the hard
                # invariant for any writer that does not take the lock).
                child = trigger_vendor_refresh(parent_id, operator=operator)

                # [O] — the ownership proof under the lock: if the
                # returned child was in the step-[b] snapshot, this
                # invocation did NOT create it. Fail-closed: report and
                # exit — NO claim, NO executor call, zero network.
                # Structurally unreachable under the lock (a competing
                # writer must hold the same RESERVED lock to INSERT).
                if child.id in {a.id for a in active_children}:
                    self._write("vendor refresh: outcome: IN_PROGRESS")
                    self._write(self._child_line(child))
                    self._write(
                        "vendor refresh: note: anomaly - the trigger "
                        "returned a pre-existing active child; no claim "
                        "was issued"
                    )
                    return EXIT_BOUNDED

                # [f] — THE one and only claim of this invocation
                # (PENDING -> RUNNING, same transaction; exactly one on
                # success, zero on every other path). A raise here
                # (structurally unreachable) propagates OUT of the
                # atomic block -> total rollback -> no row, zero calls,
                # bounded non-zero exit at the outer boundary. It is
                # NEVER caught to continue.
                claimed = claim_vendor_refresh(child.id)
        except VendorRefreshTriggerError as err:
            # [d] — the parent is not eligible (re-checked in the
            # service under the lock). The transaction rolled back:
            # zero mutation. Bounded reason (content-free), non-zero
            # exit.
            self._write(f"vendor refresh: outcome: INELIGIBLE reason={err.reason}")
            self._write(
                "vendor refresh: detail: the parent run is not eligible "
                "for a vendor refresh"
            )
            return EXIT_INELIGIBLE
        except OperationalError:
            # Contention beyond the busy timeout (or another definite
            # database failure) at the serialization point. The
            # transaction never committed: ZERO mutation (the lock
            # statement changed 0 rows by construction), zero claims,
            # zero lookups. Bounded report; NO automatic re-run.
            self._write("vendor refresh: outcome: DATABASE_BUSY")
            self._write(
                "vendor refresh: note: the database was locked or "
                "unavailable; no state changed; re-run manually"
            )
            return EXIT_DATABASE_BUSY

        # [S3] — COMMIT: the child is durably RUNNING, BEFORE any
        # network activity (I10). On the command path a PENDING row is
        # never committed alone (I5).
        self._write(
            f"vendor refresh: child-created {claimed.id} "
            f"operator={operator} "
            f"trigger-source={VendorRefreshTriggerSource.MANAGEMENT_COMMAND}"
        )

        # [S4'] — post-commit execution through the public execution
        # API (the post-claim executor; it never claims). The concrete
        # adapter is constructed only inside the execution core (S7),
        # after all preflight checks — never in this module.
        try:
            row = execute_claimed_vendor_refresh_with_default_providers(
                claimed.id
            )
        except VendorRefreshExecutionError as err:
            return self._report_execution_error(err)
        return self._report_returned_row(row)

    # ------------------------------------------------------------------
    # Bounded reporting
    # ------------------------------------------------------------------

    def _write(self, line: str) -> None:
        self.stdout.write(line)

    def _display_state(self, parent_id: str) -> None:
        """[S1] — the informational display read (read-only)."""
        self._write(f"vendor refresh: parent-run {parent_id}")
        active_children = list(
            VendorRefreshExecution.objects.filter(
                parent_run_id=parent_id,
                state__in=sorted(VendorRefreshState.ACTIVE_STATES),
            ).order_by("created_at", "id")
        )
        latest_terminal = (
            VendorRefreshExecution.objects.filter(
                parent_run_id=parent_id,
                state__in=sorted(VendorRefreshState.TERMINAL_STATES),
            )
            .order_by("-finished_at", "-id")
            .first()
        )
        if not active_children and latest_terminal is None:
            self._write("vendor refresh: no-prior-child")
            return
        for child in active_children:
            self._write(self._child_line(child))
        if latest_terminal is not None:
            self._write(
                f"vendor refresh: latest-terminal {latest_terminal.id} "
                f"state={latest_terminal.state} "
                f"finished-at={latest_terminal.finished_at.isoformat()}"
            )

    def _child_line(self, child: VendorRefreshExecution) -> str:
        """The bounded per-child display line: id, state, recorded
        operator, lifecycle timestamps (no payload content)."""
        started = (
            child.started_at.isoformat() if child.started_at is not None else "-"
        )
        return (
            f"vendor refresh: active-child {child.id} "
            f"state={child.state} operator={child.operator} "
            f"created-at={child.created_at.isoformat()} started-at={started}"
        )

    def _report_execution_error(self, err: VendorRefreshExecutionError) -> int:
        """Map the executor's bounded failure/outcome error to the
        command outcome classes (design sections 8.3 / 10.2)."""
        reason = err.reason
        if reason in _PERSISTED_FAILURE_REASONS:
            # T1 fail outcome: the child is durably FAILED with the
            # bounded reason (the single post-claim defect write).
            self._write(f"vendor refresh: outcome: FAILED failure-reason={reason}")
            return EXIT_BOUNDED
        if reason == VendorRefreshExecutionError.REASON_STATE_NOT_RUNNING:
            # T2 report (or the read-established non-terminal anomaly):
            # the ACTUAL durable state, verbatim — no assertion, no
            # second terminal write.
            state = str(err.durable_state) if err.durable_state is not None else "UNRESOLVED"
            self._write(
                f"vendor refresh: outcome: TERMINAL_REPORTED state={state}"
            )
            return EXIT_BOUNDED
        if reason == VendorRefreshExecutionError.REASON_STATE_NOT_FOUND:
            self._write("vendor refresh: outcome: TERMINAL_REPORTED state=ABSENT")
            self._write(
                "vendor refresh: note: the child row was absent at report "
                "time"
            )
            return EXIT_BOUNDED
        if reason == VendorRefreshExecutionError.REASON_TERMINALIZATION_NOT_RECORDED:
            state = str(err.durable_state) if err.durable_state is not None else "UNRESOLVED"
            self._write(
                f"vendor refresh: outcome: TERMINALIZATION_NOT_RECORDED "
                f"state={state}"
            )
            self._write(
                "vendor refresh: note: the terminal write is not durably "
                "recorded; the recovery gate (R1-4) is blocked pending "
                "O8; manual re-check per runbook"
            )
            return EXIT_UNEXPECTED
        if reason == VendorRefreshExecutionError.REASON_TERMINALIZATION_OUTCOME_UNKNOWN:
            self._write("vendor refresh: outcome: TERMINALIZATION_OUTCOME_UNKNOWN")
            self._write(
                "vendor refresh: note: the terminalization outcome is "
                "unresolved; the recovery gate (R1-4) is blocked pending "
                "O8; manual re-check per runbook"
            )
            return EXIT_UNEXPECTED
        if reason in _T2B_CONTRACT_DEFECT_REASONS:
            # A contract/programming defect at the terminal CAS (NOT a
            # CAS loser): the child was not terminalized by this
            # invocation; non-zero exit alerts the operator.
            self._write(f"vendor refresh: outcome: UNEXPECTED_ERROR reason={reason}")
            self._write(
                "vendor refresh: note: a contract defect at the terminal "
                "CAS; the child was not terminalized by this invocation; "
                "manual re-check"
            )
            return EXIT_UNEXPECTED
        # ``adapter_argument_conflict`` (unreachable: the runtime entry
        # always supplies the factory) and any future reason: bounded,
        # non-zero.
        self._write(f"vendor refresh: outcome: UNEXPECTED_ERROR reason={reason}")
        return EXIT_UNEXPECTED

    def _report_returned_row(
        self, row: VendorRefreshExecution
    ) -> int:
        """Map the executor's returned durable terminal row to the
        command outcome classes. The returned row is ACTUAL durable
        state (T1, or the T2/T4 reconciliation read) — reported
        verbatim, never assumed."""
        if row.state == VendorRefreshState.COMPLETED:
            payload = row.result_payload if isinstance(row.result_payload, dict) else {}
            vcr = payload.get("vendor_commercial_result")
            vcr = vcr if isinstance(vcr, dict) else {}
            lookup_status = vcr.get("lookup_status") or "UNRESOLVED"
            retrieved_at = vcr.get("retrieved_at") or "-"
            self._write(
                "vendor refresh: outcome: COMPLETED "
                f"lookup-status={lookup_status} retrieved-at={retrieved_at}"
            )
            return EXIT_BOUNDED
        if row.state == VendorRefreshState.FAILED:
            # T2 fail path: the child was ALREADY durably FAILED before
            # this invocation's bounded fail write ran — the actual
            # durable shape, verbatim; no rewrite.
            failure_reason = row.failure_reason or "UNRESOLVED"
            self._write(
                f"vendor refresh: outcome: TERMINAL_REPORTED state=FAILED "
                f"failure-reason={failure_reason}"
            )
            return EXIT_BOUNDED
        # Defensive (the executor returns only terminal rows): report
        # the actual state verbatim, never assume.
        self._write(
            f"vendor refresh: outcome: TERMINAL_REPORTED state={row.state}"
        )
        return EXIT_BOUNDED
