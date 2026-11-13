"""Post-claim vendor-refresh execution core (VREF-R1-2, decision M2).

Implements the approved R1 execution architecture (design SHA
``52d877d55c81c3e07c14027639264faaa07859a3``, sections 3.2 / 5 / 6 /
10.2) on the frozen R0 lifecycle services (VREF-R0 SHA
``3983db4b57e9b960d5bf6841042c93a14687fdd0``) and the R1-1 D10 shared
binding/encoding helper (implementation SHA
``6c123229bf075d72704f233f7176651656540cf9``).

POST-CLAIM ONLY. This module:

* NEVER claims: it contains no reference to ``claim_vendor_refresh``
  (or any claim symbol) in any form (AST-pinned) and performs no
  PENDING -> RUNNING transition; it executes no PENDING or terminal
  child.
* catches NO claim error at all (AST-pinned): a claim error proves the
  claim was NOT won; it is never treated as proof of ownership and no
  path proceeds to execution or makes a Vendor call after one.
* treats its RUNNING state re-assert as a fail-closed PRECONDITION, not
  caller-identity authentication: no ownership fact is inferred from
  any row state. The at-most-one Vendor lookup guarantee (LB-1) is
  scoped to the future authorized cooperating command (CMD) execution
  path (R1-3), not to arbitrary privileged direct executor calls; the
  direct-executor-reuse limit is documented and adversarially pinned
  by the R1-2 tests (mocked interleaving; genuine concurrency belongs
  to the R1-3 C nodes).
* constructs the adapter exactly once, at S7, strictly AFTER the state
  re-assert and all preflight checks (I13), from the supplied zero-arg
  factory (or from the supplied test-double instance). It imports NO
  provider class in any form — the concrete adapter arrives only via
  ``vendor_refresh_runtime`` (the only R1 module that imports
  ``providers.internal_vendor``).
* performs at most ONE ``adapter.lookup(query)`` per call and NEVER
  retries a Vendor request.
* issues at most ONE terminal write per call, through the frozen R0
  services, with the approved T1-T4 terminal-CAS outcome contract; a
  state refusal (absent / PENDING / terminal / otherwise not a valid
  RUNNING execution) is bounded with ZERO construction, ZERO lookup,
  and ZERO terminal writes — an already-invalid execution state is
  never disposed of via ``fail_vendor_refresh``.

Execution sequence (approved S4-S9 over the [A] precondition and the
S0 argument discipline):

    S0   exactly one of ``vendor_adapter`` / ``vendor_adapter_factory``
         (neither, both, or a non-callable factory: bounded
         ``adapter_argument_conflict``; zero DB, zero calls)
    [A]  re-read the child; require RUNNING + active_slot=1 +
         finished_at NULL; else bounded state refusal
    S4   load the parent; require the eligible COMPLETED state and
         ``child.requested_mpn == parent.manufacturer_part_number``;
         a genuine missing-parent fact (absent parent link) or a
         parent state/MPN contract violation is
         MPN_BINDING_VIOLATION (zero construction, zero lookup); a
         DATABASE read error is a bounded INTERNAL_ERROR
         infrastructure failure — never an MPN identity conflict
         (zero construction, zero lookup); an unexpected programming
         error PROPAGATES — it is never silently converted into
         missing-parent evidence
    S5   require ``PI_VENDOR_LOOKUP_BASE_URL`` present and non-blank;
         else VENDOR_LOOKUP_CONFIG_MISSING (zero construction, zero
         lookup)
    S6   construct ``CommercialLookupQuery`` from the EXACT
         ``child.requested_mpn``; require ``query.mpn ==
         child.requested_mpn``; else MPN_QUERY_NORMALIZATION_MISMATCH
         — rejected BEFORE constructing any adapter
    S7   construct the adapter exactly once and perform the single
         lookup; strictly outside any database transaction (I10); a
         construction or lookup exception is INTERNAL_ERROR, never
         re-issued
    S8   bind and encode with the R1-1 D10 helper
         (``bind_and_encode_vendor_lookup``); a codec encoding failure
         is RESULT_ENCODING_FAILED — the full V1 encoding happens
         BEFORE the complete CAS, so no malformed COMPLETED payload is
         ever published
    S9   complete through the frozen R0 ``complete_vendor_refresh``
         with the T1-T4 terminal-CAS outcome contract

Terminal CAS outcome contract (T1-T4; FU3-F1: the frozen services
RETURN the re-read row on success and RAISE the typed error with
``reason=None`` on a zero-row CAS — there is no exposed rowcount, so
outcomes are classified by return / typed error + reason / database
error, never by a rowcount):

    T1   the service RETURNS the durably stored terminal row
    T2   typed error with ``reason=None`` (lost terminal CAS): the
         pinned READ-ONLY reconciliation fresh-reads the row and
         classifies its ACTUAL state: terminal (COMPLETED / FAILED)
         -> the actual durable row is returned verbatim; absent ->
         bounded state_not_found; non-terminal (PENDING / RUNNING /
         other) -> bounded state_not_running REFUSAL carrying the
         actually-read-established state — never a normal return;
         fresh-read database error -> bounded
         terminalization_outcome_unknown (no raw DatabaseError
         escapes as the final public outcome). No second terminal
         write, no retry, no lookup, no execution resumption, NO
         ``fail_vendor_refresh`` as a substitute for an uncertain
         successful completion, and NO RUNNING assertion — the read
         establishes what it establishes
    T2b  typed error with an EXPLICIT reason
         (``invalid_schema_version`` / ``invalid_payload`` /
         ``invalid_failure_reason`` / ``reserved_execution_interrupted``):
         a contract/programming defect, NOT a CAS loser — surfaced as
         that reason with no terminal-state report and no T2
         classification
    T3   Django database error, write demonstrably not committed: the
         reconciliation fresh read proves the current durable shape
         (RUNNING per the read, never assumed) and reports
         terminalization_not_recorded
    T4   Django database error, ambiguous persistence outcome: neither
         outcome is assumed — the reconciliation fresh read classifies
         (terminal: actual durable state; RUNNING:
         terminalization_not_recorded; read also fails:
         terminalization_outcome_unknown). The fresh read is over a
         DEMONSTRABLY USABLE connection: outside a managed
         transaction over the file-based deployment database the
         possibly-compromised DBAPI connection is explicitly
         discarded and a replacement is established and
         demonstrated usable (lightweight statement) BEFORE the row
         is read over it — Django's wrapper is NOT assumed to
         replace a compromised connection; under a managed
         transaction the wrapper's own usability gate applies (the
         connection is never closed there); over an in-memory
         database outside a managed transaction no reliable fresh
         read is possible and terminalization_outcome_unknown is
         reported conservatively. Never a Vendor call retry, never a
         ``fail_vendor_refresh`` to compensate for an unknown
         completion; the actual durable terminal result is preserved
         when reliably established

No FX, search, semantic, comparable, web, or pricing-authority side
effect occurs on any path of this module (AST + sentinel pinned).

Import allowlist (AST-pinned): stdlib (``__future__``, ``os``,
``uuid``, ``typing``); ``django.db`` (the ``DatabaseError`` class for
the T3/T4 reconciliation + the ``connections`` handler for the T4
demonstrably-usable fresh-connection establishment — the only Django
import surface; no ``django.db.transaction``, no open transaction
across the lookup, I10); ``product_intelligence.runs`` PUBLIC symbols
(the complete/fail services + the bounded terminal errors + the model
for the state re-assert); ``product_intelligence.execution.vendor_
commercial_binding`` (the D10 helper); ``product_intelligence.providers.commercial`` (the
network-free ``CommercialLookupQuery`` contract type). NO import of
``providers.internal_vendor`` in any form (I13); NO research, NO web,
NO fx, NO semantic, NO comparable, NO search, NO domain import.
"""

from __future__ import annotations

import os
import uuid
from typing import TYPE_CHECKING, Callable

from django.db import DatabaseError, connections

from product_intelligence.execution.vendor_commercial_binding import (
    bind_and_encode_vendor_lookup,
)
from product_intelligence.providers.commercial import CommercialLookupQuery
from product_intelligence.runs import (
    VendorRefreshCompletionError,
    VendorRefreshFailureError,
    VendorRefreshExecution,
    VendorRefreshFailureReason,
    VendorRefreshState,
    complete_vendor_refresh,
    fail_vendor_refresh,
)

if TYPE_CHECKING:  # pragma: no cover - annotation only
    from product_intelligence.providers.commercial import (
        CommercialSourceResponse,
    )

__all__ = [
    "VendorRefreshExecutionError",
    "execute_claimed_vendor_refresh",
]

# The deployment-owned Vendor lookup base URL (frozen 4D-B config
# contract: present and non-blank after strip; the frozen adapter
# re-validates the exact value lazily as the first statement of
# lookup()).
_VENDOR_LOOKUP_BASE_URL_ENV = "PI_VENDOR_LOOKUP_BASE_URL"

# The frozen parent state an execution may re-verify against
# (``ResearchRunState.COMPLETED.value``). The domain vocabulary is not
# imported here: the execution core stays inside its pinned import
# allowlist, and the stored value IS the bounded vocabulary member.
_PARENT_ELIGIBLE_STATE = "COMPLETED"

# The frozen supplement codec schema version (V1), exactly as the R0
# complete service validates the bounded agreement at the dict level.
_RESULT_SCHEMA_VERSION = 1


class VendorRefreshExecutionError(Exception):
    """Bounded execution-layer failure for the post-claim executor.

    ``reason`` is bounded to exactly three families (content-free —
    never untrusted input content):

    * the persisted R0_LEGAL failure-reason vocabulary, carried when
      the child was terminalized FAILED through the frozen service
      with that reason (S4-S8 defects, T1 fail outcome):
      ``MPN_BINDING_VIOLATION`` / ``VENDOR_LOOKUP_CONFIG_MISSING`` /
      ``MPN_QUERY_NORMALIZATION_MISMATCH`` / ``RESULT_ENCODING_FAILED``
      / ``INTERNAL_ERROR``;
    * the non-persisted refusal/outcome reasons (no terminal write
      issued, or the T2 anomaly / T2 read-failure / T3 / T4
      reconciliation outcomes):
      ``state_not_found`` / ``state_not_running`` /
      ``adapter_argument_conflict`` / ``terminalization_not_recorded``
      / ``terminalization_outcome_unknown``;
    * the T2b explicit terminal-CAS input-rejection reasons
      (``invalid_schema_version`` / ``invalid_payload`` /
      ``invalid_failure_reason`` / ``reserved_execution_interrupted``):
      contract/programming defects, never CAS losers.

    A T2 (lost terminal CAS) terminal outcome is NOT this error: the
    executor RETURNS the actual durable terminal row. A T2
    NON-TERMINAL anomaly (the fresh read establishes PENDING /
    RUNNING / any other non-terminal shape) IS this error:
    ``state_not_running`` carrying the actually-read-established
    ``durable_state`` — a bounded refusal, never a normal return.

    ``durable_state`` carries the ACTUAL durable child state
    established by the reconciliation fresh read (T3/T4) or by the
    recorded T1 fail write; it is None when nothing durable was
    established (pre-DB refusals, T2b defects, the invalid-UUID
    refusal, T2 read failures, T4 outcome-unknown).
    """

    REASON_STATE_NOT_FOUND = "state_not_found"
    REASON_STATE_NOT_RUNNING = "state_not_running"
    REASON_ADAPTER_ARGUMENT_CONFLICT = "adapter_argument_conflict"
    REASON_TERMINALIZATION_NOT_RECORDED = "terminalization_not_recorded"
    REASON_TERMINALIZATION_OUTCOME_UNKNOWN = "terminalization_outcome_unknown"

    #: The non-persisted refusal/outcome reasons (bounded vocabulary).
    NON_PERSISTED_REASONS: frozenset[str] = frozenset({
        REASON_STATE_NOT_FOUND,
        REASON_STATE_NOT_RUNNING,
        REASON_ADAPTER_ARGUMENT_CONFLICT,
        REASON_TERMINALIZATION_NOT_RECORDED,
        REASON_TERMINALIZATION_OUTCOME_UNKNOWN,
    })

    def __init__(
        self,
        reason: str,
        *,
        child_id: str | None = None,
        durable_state: str | None = None,
        detail: str | None = None,
    ) -> None:
        self.reason = reason
        self.child_id = child_id
        self.durable_state = durable_state
        self.detail = detail
        msg = f"vendor refresh execution failed: {reason}"
        if child_id is not None:
            msg += f" (child {child_id})"
        if detail:
            msg += f": {detail}"
        super().__init__(msg)


def execute_claimed_vendor_refresh(
    child_id: uuid.UUID | str,
    *,
    vendor_adapter: object | None = None,
    vendor_adapter_factory: Callable[[], object] | None = None,
) -> VendorRefreshExecution:
    """Execute one already-claimed RUNNING vendor-refresh child.

    POST-CLAIM ONLY: this function never claims, never transitions
    PENDING -> RUNNING, and never executes a PENDING or terminal
    child. Its authority boundary is the scoped CMD-path contract
    (design section 3.2, FU2-F1): on the authorized cooperating
    command execution path (R1-3) the caller is the invocation that
    created the child and won its claim CAS, calling post-commit in
    the same process; the function verifies NO caller identity — the
    [A] RUNNING re-assert is a fail-closed precondition, not
    ownership authentication. Direct calls against a still-RUNNING
    child are the documented privileged-writer limit, adversarially
    pinned by the R1-2 tests.

    Parameters
    ----------
    child_id
        The VendorRefreshExecution to execute (UUID or its string form).
    vendor_adapter
        A pre-constructed adapter instance (test doubles only in R1).
        Mutually exclusive with ``vendor_adapter_factory``.
    vendor_adapter_factory
        A zero-arg callable constructing the adapter (the production
        command path supplies the concrete adapter CLASS from
        ``vendor_refresh_runtime``). Mutually exclusive with
        ``vendor_adapter``. The factory is invoked exactly once, at
        S7, after all preflight checks (I13).

    Returns
    -------
    VendorRefreshExecution
        The durably stored terminal row: T1 (this call's complete CAS
        won) or the T2/T4 actual durable TERMINAL state established
        by the reconciliation fresh read.

    Raises
    ------
    VendorRefreshExecutionError
        Bounded state refusals (zero writes — including the
        invalid-UUID refusal, whose message reflects no part of the
        untrusted input), the persisted S4-S8 defect reasons (the
        child is durably FAILED, or its actual durable state is
        reported on the T2 fail path), the T2b explicit-reason
        defects, the T2 non-terminal anomaly refusal (the actual
        read-established state, never a normal return), and the
        T2/T3/T4 outcomes (``terminalization_not_recorded`` /
        ``terminalization_outcome_unknown``).
    """
    # S0 — argument discipline: exactly one adapter source.
    # (Zero DB, zero construction, zero lookup, zero terminal writes.)
    if (vendor_adapter is None) == (vendor_adapter_factory is None):
        raise VendorRefreshExecutionError(
            VendorRefreshExecutionError.REASON_ADAPTER_ARGUMENT_CONFLICT,
            detail=(
                "exactly one of vendor_adapter or "
                "vendor_adapter_factory must be supplied"
            ),
        )
    if vendor_adapter_factory is not None and not callable(vendor_adapter_factory):
        raise VendorRefreshExecutionError(
            VendorRefreshExecutionError.REASON_ADAPTER_ARGUMENT_CONFLICT,
            detail="vendor_adapter_factory must be a zero-arg callable",
        )

    # An unresolvable child identity is a bounded state refusal (the
    # row is absent), not a native UUID error. The untrusted input is
    # NEVER reflected in the public error message (bounded output):
    # no child_id is carried, so neither a very long invalid string
    # nor any embedded content can be echoed back.
    try:
        target_id = str(uuid.UUID(str(child_id)))
    except (TypeError, ValueError):
        raise VendorRefreshExecutionError(
            VendorRefreshExecutionError.REASON_STATE_NOT_FOUND,
            detail="child_id is not a valid UUID",
        ) from None

    # [A] — state re-assert (READ-ONLY precondition; NOT ownership
    # authentication; NOT a claim). Refusals: zero construction, zero
    # lookup, ZERO terminal writes — an already-invalid execution
    # state is bounded-refused, never disposed of via fail.
    child = _load_running_child_or_refuse(target_id)

    # S4 — parent load + eligible COMPLETED re-check (defensive) +
    # captured-MPN binding. Classification (FU1-F1):
    #   * genuine missing-parent fact (absent parent link) or a
    #     parent state/MPN contract violation ->
    #     MPN_BINDING_VIOLATION (zero construction, zero lookup);
    #   * a DATABASE read error -> bounded INTERNAL_ERROR
    #     infrastructure failure (zero construction, zero lookup) —
    #     never an MPN identity conflict;
    #   * an unexpected programming error -> PROPAGATES (never
    #     silently converted into missing-parent evidence).
    parent, parent_read_database_error = _load_parent_for_binding(child)
    if parent_read_database_error:
        return _outer_boundary_fail(
            target_id, VendorRefreshFailureReason.INTERNAL_ERROR
        )
    if (
        parent is None
        or getattr(parent, "current_state", None) is None
        or parent.current_state.value != _PARENT_ELIGIBLE_STATE
        or child.requested_mpn != parent.manufacturer_part_number
    ):
        return _outer_boundary_fail(
            target_id, VendorRefreshFailureReason.MPN_BINDING_VIOLATION
        )

    # S5 — deployment configuration present and non-blank.
    # Missing/blank: bounded fail, zero construction, zero lookup.
    if not os.environ.get(_VENDOR_LOOKUP_BASE_URL_ENV, "").strip():
        return _outer_boundary_fail(
            target_id, VendorRefreshFailureReason.VENDOR_LOOKUP_CONFIG_MISSING
        )

    # S6 — the query is built from the EXACT captured MPN; the frozen
    # query type strips surrounding whitespace, so any divergence is
    # a normalization mismatch, rejected BEFORE constructing any
    # adapter. (Zero construction, zero lookup on rejection.)
    try:
        query = CommercialLookupQuery(mpn=child.requested_mpn)
    except (TypeError, ValueError):
        return _outer_boundary_fail(
            target_id,
            VendorRefreshFailureReason.MPN_QUERY_NORMALIZATION_MISMATCH,
        )
    if query.mpn != child.requested_mpn:
        return _outer_boundary_fail(
            target_id,
            VendorRefreshFailureReason.MPN_QUERY_NORMALIZATION_MISMATCH,
        )

    # S7 — FIRST and ONLY adapter construction (I13) + THE single
    # lookup (LB-1/LB-2). Strictly outside any database transaction
    # (I10 — no transaction is opened by this function at all). A
    # construction failure or a lookup exception is a bounded
    # post-claim defect (INTERNAL_ERROR); no Vendor request is ever
    # retried.
    try:
        adapter = (
            vendor_adapter
            if vendor_adapter_factory is None
            else vendor_adapter_factory()
        )
        response = adapter.lookup(query)
    except Exception:
        return _outer_boundary_fail(
            target_id, VendorRefreshFailureReason.INTERNAL_ERROR
        )

    # S8 — bind and encode with the R1-1 D10 helper (pure: no DB, no
    # env, no network). The full frozen V1 codec encoding happens
    # BEFORE the complete CAS, so no malformed COMPLETED payload can
    # be published. A codec encoding failure is RESULT_ENCODING_FAILED.
    try:
        encoded = bind_and_encode_vendor_lookup(child.requested_mpn, response)
    except Exception:
        return _outer_boundary_fail(
            target_id, VendorRefreshFailureReason.RESULT_ENCODING_FAILED
        )

    # S9 — frozen R0 complete, with the T1-T4 terminal-CAS outcome
    # contract. NO fail is ever issued after this point: a successful
    # lookup is never reclassified under a failed reason.
    try:
        # T1 — the service returns the durably stored terminal row.
        return complete_vendor_refresh(
            target_id, _RESULT_SCHEMA_VERSION, encoded
        )
    except VendorRefreshCompletionError as err:
        if err.reason is not None:
            # T2b — explicit-reason input rejection: a
            # contract/programming defect, NOT a CAS loser. No
            # terminal-state report, no second write, no T2
            # classification.
            raise VendorRefreshExecutionError(
                err.reason,
                child_id=target_id,
                detail=err.detail,
            ) from err
        # T2 — lost terminal CAS (reason=None): the pinned READ-ONLY
        # reconciliation over the actual durable state.
        return _reconcile_terminal_cas_loss(target_id)
    except DatabaseError:
        # T3/T4 — definite or ambiguous persistence outcome:
        # classified by the reconciliation fresh read, never assumed.
        return _reconcile_db_error(target_id)


def _outer_boundary_fail(target_id: str, reason: str) -> VendorRefreshExecution:
    """The single post-claim outer boundary (BEFORE any complete attempt).

    Maps one bounded S4-S8 defect to ONE R0_LEGAL fail through the
    frozen service and then raises ``VendorRefreshExecutionError`` —
    subject to the fail's own T1-T4 terminal-CAS outcome contract:

    * T1 — the fail CAS wins; the child is durably FAILED with
      ``reason``; raise with the persisted reason.
    * T2 — the fail CAS lost (child already terminal per fresh read);
      RETURN the actual durable row (bounded, recorded, no rewrite;
      the defect's own terminalization is simply not persisted —
      append-only).
    * T2b — the fail raised with an EXPLICIT reason (input rejection):
      raise with that reason; no terminal-state report.
    * T3/T4 — a Django database error from the fail: classified by the
      reconciliation fresh read (terminal: actual durable row;
      RUNNING / non-terminal: terminalization_not_recorded; read
      fails: terminalization_outcome_unknown).

    ``reason`` is always a member of ``R0_LEGAL`` (the reserved value
    is never passed to the frozen service).
    """
    try:
        # T1 — the fail CAS wins; the child is durably FAILED.
        fail_vendor_refresh(target_id, reason)
    except VendorRefreshFailureError as err:
        if err.reason is not None:
            # T2b — not a CAS loser; no terminal-state report.
            raise VendorRefreshExecutionError(
                err.reason,
                child_id=target_id,
                detail=err.detail,
            ) from err
        # T2 — the child was already terminal when the fail ran.
        return _reconcile_terminal_cas_loss(target_id)
    except DatabaseError:
        # T3/T4 — the fail's persistence outcome is definite-not-
        # committed or ambiguous; classified by the fresh read.
        return _reconcile_db_error(target_id)
    raise VendorRefreshExecutionError(
        reason,
        child_id=target_id,
        durable_state=VendorRefreshState.FAILED,
    )


def _load_running_child_or_refuse(target_id: str) -> VendorRefreshExecution:
    """[A] — the state re-assert (READ-ONLY, fail-closed).

    The row must exist and be a valid RUNNING execution (state
    RUNNING, active_slot=1, finished_at NULL). This is a PRECONDITION
    on the row shape — NOT caller-identity authentication and NOT a
    claim: no ownership fact is inferred from any row state, and no
    terminal write is issued for a refusal (an already-invalid
    execution state is bounded-refused, never disposed of via
    ``fail_vendor_refresh``).

    Raises
    ------
    VendorRefreshExecutionError
        ``state_not_found`` (absent row) or ``state_not_running``
        (PENDING / COMPLETED / FAILED / any other non-RUNNING shape),
        in every case with zero construction, zero lookup, and zero
        terminal writes.
    """
    try:
        child = VendorRefreshExecution.objects.get(id=target_id)
    except VendorRefreshExecution.DoesNotExist:
        raise VendorRefreshExecutionError(
            VendorRefreshExecutionError.REASON_STATE_NOT_FOUND,
            child_id=target_id,
            detail="no VendorRefreshExecution with this ID",
        ) from None
    if (
        child.state != VendorRefreshState.RUNNING
        or child.active_slot != 1
        or child.finished_at is not None
    ):
        raise VendorRefreshExecutionError(
            VendorRefreshExecutionError.REASON_STATE_NOT_RUNNING,
            child_id=target_id,
            durable_state=child.state,
            detail=f"child is in state {child.state}, expected RUNNING",
        )
    return child


def _load_parent_for_binding(child: VendorRefreshExecution) -> tuple[object | None, bool]:
    """S4 — the parent load for the eligible-state + MPN binding check.

    Returns ``(parent, database_error)``:

    * the loaded parent (or ``None`` for the genuine missing-parent
      fact — an absent parent link) with ``database_error=False``;
    * ``parent=None`` with ``database_error=True`` when the read
      raised a Django database error (an infrastructure failure —
      the caller maps it to bounded INTERNAL_ERROR, never to an MPN
      identity conflict).

    An unexpected programming error is NOT caught: it propagates to
    the caller instead of silently becoming missing-parent evidence.
    """
    try:
        return child.parent_run, False
    except VendorRefreshExecution._meta.get_field(
        "parent_run"
    ).related_model.DoesNotExist:
        # The genuine missing-parent fact (dangling / NULL parent
        # link): the storage-level ``RelatedObjectDoesNotExist`` is a
        # subclass of the related model's ``DoesNotExist``, so this
        # one bound covers both raise paths.
        return None, False
    except DatabaseError:
        # A database read error is infrastructure failure, not
        # missing-parent evidence and not an MPN identity conflict.
        return None, True


def _reconcile_terminal_cas_loss(target_id: str) -> VendorRefreshExecution:
    """T2 — the terminal CAS matched zero rows: the child was already
    terminal (or gone) when the UPDATE ran.

    Pinned READ-ONLY reconciliation (FU3-F1): FRESH READ, classify
    the ACTUAL durable state — never a second terminal write, never a
    retry, never a lookup, never a ``fail_vendor_refresh`` as a
    substitute for an uncertain successful completion, and never a
    RUNNING assertion (the read establishes what it establishes):

    * terminal (COMPLETED / FAILED) -> that row is returned verbatim;
    * absent -> bounded ``state_not_found`` refusal (nothing to
      terminalize);
    * non-terminal (PENDING / RUNNING / other) -> bounded
      ``state_not_running`` REFUSAL carrying the actually-
      read-established state — an anomaly, never a normal return;
    * the fresh read raises a database error -> bounded
      ``terminalization_outcome_unknown`` — no raw DatabaseError
      escapes as the final public outcome.
    """
    try:
        row = _reconciliation_fresh_read(target_id)
    except VendorRefreshExecution.DoesNotExist:
        raise VendorRefreshExecutionError(
            VendorRefreshExecutionError.REASON_STATE_NOT_FOUND,
            child_id=target_id,
            detail="child absent at terminal-CAS reconciliation",
        ) from None
    except DatabaseError:
        raise VendorRefreshExecutionError(
            VendorRefreshExecutionError.REASON_TERMINALIZATION_OUTCOME_UNKNOWN,
            child_id=target_id,
            detail=(
                "fresh read at terminal-CAS reconciliation raised a "
                "database error"
            ),
        ) from None
    if row.state in VendorRefreshState.TERMINAL_STATES:
        return row
    raise VendorRefreshExecutionError(
        VendorRefreshExecutionError.REASON_STATE_NOT_RUNNING,
        child_id=target_id,
        durable_state=row.state,
        detail=(
            "terminal-CAS reconciliation fresh read established the "
            "non-terminal state; refusing with the actual read-"
            "established state (no RUNNING assertion, no second "
            "terminal write)"
        ),
    )


def _reconcile_db_error(target_id: str) -> VendorRefreshExecution:
    """T3/T4 — the terminal CAS raised a Django database error:
    neither commit nor rollback may be assumed.

    The reconciliation fresh read classifies by what it establishes
    (never by an assumption about the failed write):

    * terminal row -> the actual durable state is returned (the
      terminalization IS durably recorded — the T2 report shape);
    * RUNNING row -> ``terminalization_not_recorded`` (T3: the write
      demonstrably did not commit; the row remains RUNNING per the
      read — a reported HOLD, never an assumption);
    * PENDING or other non-terminal row -> ``terminalization_not_
      recorded`` with the actually-read state reported (no RUNNING
      assertion);
    * the read also fails, or the row is absent -> ``terminalization_
      outcome_unknown`` (T4: neither outcome is established; zero
      writes; no fail issued; operator re-check per the runbook).

    A fail is NEVER issued here: a successful lookup is never
    reclassified under a failed reason.
    """
    try:
        row = _reconciliation_fresh_read(target_id)
    except (VendorRefreshExecution.DoesNotExist, DatabaseError):
        raise VendorRefreshExecutionError(
            VendorRefreshExecutionError.REASON_TERMINALIZATION_OUTCOME_UNKNOWN,
            child_id=target_id,
            detail="fresh read at terminal-CAS reconciliation also failed",
        ) from None
    if row.state not in VendorRefreshState.TERMINAL_STATES:
        raise VendorRefreshExecutionError(
            VendorRefreshExecutionError.REASON_TERMINALIZATION_NOT_RECORDED,
            child_id=target_id,
            durable_state=row.state,
            detail=(
                "the terminal write is not durably recorded; the fresh "
                "read establishes the current durable shape"
            ),
        )
    return row


def _reconciliation_fresh_read(target_id: str) -> VendorRefreshExecution:
    """The single bounded fresh read used by the pinned terminal-CAS
    reconciliation (T2/T3/T4).

    The read must be trustworthy, not merely convenient — an ambiguous
    commit outcome (T4) leaves the current DBAPI connection possibly
    compromised, and Django's wrapper is NOT assumed to replace it
    automatically:

    * under a MANAGED transaction (``in_atomic_block`` — the suite's
      TestCase frame): the connection is the transaction's own
      connection; closing it would abort the managed state and, for
      the in-memory suite database, destroy it. No close is issued:
      the statement below goes through the wrapper's own usability
      gate (``close_if_unusable_or_obsolete`` + ``is_usable``), and if
      the wrapper cannot establish a usable connection the read
      raises and the caller reports ``terminalization_outcome_
      unknown`` — never an assumed state.
    * over an IN-MEMORY database outside a managed transaction: a
      fresh connection would be a new EMPTY database (the data dies
      with the last connection) — no reliable fresh read is possible;
      signal it as a database error and let the caller report
      ``terminalization_outcome_unknown`` conservatively.
    * otherwise (the production post-commit path over the file-based
      deployment database, autocommit): the possibly-compromised
      connection is explicitly closed (discarding the compromised
      DBAPI connection), a replacement connection is established, and
      its usability is DEMONSTRATED with a lightweight statement
      BEFORE the row is read over it.

    No row cache, no state assumption: the read is always a fresh
    SELECT and returns the ACTUAL durable row.
    """
    conn = connections["default"]
    if conn.in_atomic_block:
        return VendorRefreshExecution.objects.get(id=target_id)
    if _is_in_memory_database_name(conn.settings_dict.get("NAME")):
        raise DatabaseError(
            "in-memory database: a fresh connection cannot establish a "
            "reliable reconciliation read"
        )
    conn.close()
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT 1")
        cursor.fetchone()
    finally:
        cursor.close()
    return VendorRefreshExecution.objects.get(id=target_id)


def _is_in_memory_database_name(name) -> bool:
    """The sqlite in-memory forms (``:memory:`` or a relative ``file:``
    URI carrying ``mode=memory``) — mirroring the sqlite3 backend's
    own in-memory detection. The deployment database is file-based
    (design section 1.6); in-memory names are the test/dev pattern
    whose data dies with the last connection, so a "fresh
    connection" there would read a new empty database."""
    if not isinstance(name, str) or not name or os.path.isabs(name):
        return False
    return name == ":memory:" or "mode=memory" in name
