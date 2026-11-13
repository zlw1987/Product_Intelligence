"""VREF-R1-2 — post-claim vendor-refresh execution core (deterministic + mocked-race nodes).

VREF-R1-2-FU1 — execution failure boundary corrections:

* F1 — the S4 parent load classifies faults precisely: a database
  read error (fault-injected ``django.db.OperationalError``) is a
  bounded INTERNAL_ERROR infrastructure failure (MPN_BINDING_VIOLATION
  is NOT persisted; zero construction, zero lookup); an unexpected
  programming error propagates (never silently converted into
  missing-parent evidence).
* F2 — the T3/T4 reconciliation fresh read is over a trustworthy
  connection: under the suite's managed transaction the connection is
  never closed (no blind close; the in-memory suite DB is not
  destroyed); the ACTUAL connection-recovery property (the
  possibly-compromised DBAPI connection demonstrably replaced by a
  verified new one over a FILE-BACKED SQLite database, the production
  non-managed context) is proven by the clean-subprocess probe nodes
  at the bottom of this module — a patched
  ``_reconciliation_fresh_read`` returning a canned row is not
  sufficient evidence by itself.
* F3 — a T2 typed CAS error with reason=None triggers READ-ONLY
  reconciliation: terminal -> the actual durable row is returned;
  absent -> bounded state_not_found; PENDING / RUNNING -> bounded
  state_not_running REFUSAL carrying the actual read-established state
  (never a normal return); fresh-read database error -> bounded
  terminalization_outcome_unknown (no raw DatabaseError escapes).
* F4 — an invalid child_id is never reflected verbatim in the public
  error message (bounded state_not_found; zero DB, adapter, or
  network activity).

Covers ``product_intelligence.execution.vendor_refresh.execute_claimed_
vendor_refresh`` and the runtime entry
``execute_claimed_vendor_refresh_with_default_providers`` over the
approved R1 execution architecture (design SHA
``52d877d55c81c3e07c14027639264faaa07859a3`` sections 3.2 / 5 / 6 /
10.2 / 12) on the frozen R0 lifecycle services and the R1-1 D10 helper
(implementation base SHA ``6c123229bf075d72704f233f7176651656540cf9``).

Classification (design section 12 legend): D = deterministic sequential
(single connection, in-memory suite DB); M = mocked race-path
(monkeypatched primitives/sentinels force interleavings that are
impractical to time — explicitly labeled MOCKED, NOT a concurrency
proof; genuine concurrency is proven only by the R1-3 C nodes).

Contract pins (task sections 3-7; design section 12 rows 2-4, 6, 7,
13-15, 19, 20 D/M portions):

* POST-CLAIM ONLY: the executor never claims, never transitions
  PENDING -> RUNNING, never executes a PENDING or terminal child, and
  never catches a claim error (AST-pinned in the network boundary
  suite).
* fail-closed state refusals (absent / PENDING / COMPLETED / FAILED /
  otherwise not a valid RUNNING execution): bounded, ZERO adapter
  construction, ZERO lookup calls, ZERO terminal writes — an
  already-invalid execution state is never disposed of via
  ``fail_vendor_refresh``.
* valid RUNNING path: S4-S9 exactly once; the adapter is constructed
  exactly once via the lazy factory (or the supplied test-double
  instance); at most one ``lookup()``; no retry; no open transaction
  across the lookup (I10).
* pre-lookup bounded failures terminalize via the appropriate R0_LEGAL
  reason (MPN_BINDING_VIOLATION / VENDOR_LOOKUP_CONFIG_MISSING /
  MPN_QUERY_NORMALIZATION_MISMATCH / RESULT_ENCODING_FAILED /
  INTERNAL_ERROR); transport-level FAILED CommercialSourceResponse is
  a COMPLETED result (lookup_status FAILED, retrieved_at None), not an
  execution-machinery failure.
* T1-T4 terminal-CAS outcome contract (FU3-F1): the frozen services
  return the re-read row on success and raise the typed error with
  reason=None on a zero-row CAS (no exposed rowcount); T2 (reason=None)
  is a read-only reconciliation over the actual durable state (no
  second terminal write, no retry, no lookup, no fail as substitute,
  no RUNNING assertion); T2b (explicit reason) is a
  contract/programming defect, never a CAS loser; T3/T4 are
  classified by the reconciliation fresh read, never assumed.
* no second Vendor call for any failure; no FX/search/semantic/
  comparable/web/pricing-authority side effect on any path; parent and
  all original artifacts byte-identical (I7).

Golden provenance: the canned ``CommercialSourceResponse`` builders and
the expected encoded payloads are the R1-1 golden cases (imported from
``tests/execution/test_vendor_commercial_binding.py`` — captured before
the D10 extraction from the frozen pre-extraction orchestration path),
reused here for policy equivalence (design section 12 rows 5/6/17).
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
import uuid
from contextlib import nullcontext
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path
from unittest.mock import patch

import pytest
from django.db import OperationalError
from django.db import connections
from django.test import TestCase
from django.test.utils import CaptureQueriesContext

from product_intelligence.domain import ResearchRequest
from product_intelligence.domain.enums import ResearchRunState
from product_intelligence.providers.commercial import (
    CommercialAvailability,
    CommercialPriceBasis,
    CommercialSourceCandidate,
    CommercialSourceResponse,
    LookupStatus,
)
from product_intelligence.research.commercial_supplement_codec import (
    ResearchSupplementResult,
    SupplementCodecError,
    VendorCommercialResult,
    decode_research_supplement_result,
    encode_research_supplement_result,
)
# Public API surface (lazy exports) — these imports double as the export
# regression for the frozen R0 primitives the executor builds on.
from product_intelligence.runs import (
    claim_vendor_refresh,
    complete_vendor_refresh,
    fail_vendor_refresh,
    trigger_vendor_refresh,
)
from product_intelligence.runs.errors import (
    VendorRefreshCompletionError,
    VendorRefreshFailureError,
)
from product_intelligence.runs.models import (
    AiAssistedReviewCandidate,
    ComparableResearchExecution,
    ExecutionEvidenceRecord,
    PriceIntelligenceSnapshot,
    ResearchFxSnapshot,
    ResearchMicronAliasSnapshot,
    ResearchRun,
    ResearchSupplementSnapshot,
    VendorRefreshExecution,
    VendorRefreshFailureReason,
    VendorRefreshState,
)

import product_intelligence.execution.vendor_refresh as core
from product_intelligence.execution.vendor_refresh import (
    VendorRefreshExecutionError,
    execute_claimed_vendor_refresh,
)
from product_intelligence.execution.vendor_refresh_runtime import (
    execute_claimed_vendor_refresh_with_default_providers,
)

# R1-1 golden inputs + goldens (policy equivalence; the canned
# responses are byte-identical to the golden-capture inputs of record).
from tests.execution.test_vendor_commercial_binding import (
    GOLDEN_MIXED_USABLE_AND_UNUSABLE,
    GOLDEN_SUCCESS_EXACT_MATCH,
    GOLDEN_TRANSPORT_FAILED_NO_RETRIEVED_AT,
    GOLDEN_TRANSPORT_FAILED_RETRIEVED_AT_CLEARED,
    build_mixed_usable_and_unusable_response,
    build_success_exact_match_response,
    build_transport_failed_no_retrieved_at_response,
    build_transport_failed_retrieved_at_cleared_response,
)

GOLDEN_MPN = "BCM957608-P2200GQF00"
RETRIEVED_AT = datetime(2025, 1, 15, 10, 30, 45, tzinfo=timezone.utc)
CONFIGURED_BASE_URL = "http://vendor.internal/api"
CONFIGURED_ENV = "PI_VENDOR_LOOKUP_BASE_URL"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_completed_run(
    mpn: str = GOLDEN_MPN,
    description: str = "VREF-R1-2 execution core test",
    with_original_supplement: bool = False,
) -> ResearchRun:
    """A COMPLETED parent with its PriceIntelligenceSnapshot."""
    request = ResearchRequest(manufacturer_part_number=mpn, description=description)
    run = ResearchRun.objects.create_from_request(request)
    run.transition_to(ResearchRunState.RUNNING)
    run.transition_to(ResearchRunState.COMPLETED)
    PriceIntelligenceSnapshot.objects.create(
        run=run,
        schema_version=1,
        payload={
            "request": {
                "manufacturer_part_number": mpn,
                "description": description,
            },
            "assessments": [],
            "buckets": [],
            "exclusions": [],
            "verification_status": "VERIFIED",
        },
    )
    if with_original_supplement:
        ResearchSupplementSnapshot.objects.create(
            run=run,
            schema_version=1,
            payload=encode_research_supplement_result(
                ResearchSupplementResult(
                    vendor_commercial_result=VendorCommercialResult(
                        lookup_status="SUCCESS",
                        retrieved_at=RETRIEVED_AT,
                        observations=(),
                        source_issues=(),
                    )
                )
            ),
        )
    return run


def _frozen_payload() -> dict:
    """A minimal frozen V1 supplement payload (valid complete input)."""
    return encode_research_supplement_result(
        ResearchSupplementResult(
            vendor_commercial_result=VendorCommercialResult(
                lookup_status="FAILED",
                retrieved_at=None,
                observations=(),
                source_issues=(),
            )
        )
    )


def _make_pending_child(run: ResearchRun, operator: str = "op-a") -> VendorRefreshExecution:
    return trigger_vendor_refresh(run.id, operator=operator)


def _make_running_child(run: ResearchRun, operator: str = "op-a") -> VendorRefreshExecution:
    return claim_vendor_refresh(_make_pending_child(run, operator).id)


def _row_snapshot(pk) -> dict:
    """Every stored field of the child row, re-read from the database."""
    r = VendorRefreshExecution.objects.get(pk=pk)
    return {
        "id": r.id,
        "parent_run_id": r.parent_run_id,
        "requested_mpn": r.requested_mpn,
        "state": r.state,
        "active_slot": r.active_slot,
        "trigger_source": r.trigger_source,
        "operator": r.operator,
        "created_at": r.created_at,
        "started_at": r.started_at,
        "finished_at": r.finished_at,
        "result_schema_version": r.result_schema_version,
        "result_payload": r.result_payload,
        "failure_reason": r.failure_reason,
    }


def _parent_artifact_snapshot(run: ResearchRun) -> dict:
    """The parent ResearchRun + every original persisted artifact,
    re-read from the database (I7 byte-identity frame)."""
    fresh_run = ResearchRun.objects.get(pk=run.pk)
    snapshot = {
        "run_state": fresh_run.state,
        "run_mpn": fresh_run.manufacturer_part_number,
        "run_description": fresh_run.description,
        "run_created_at": fresh_run.created_at,
        "run_started_at": fresh_run.started_at,
        "run_finished_at": fresh_run.finished_at,
        "price_snapshot_count": PriceIntelligenceSnapshot.objects.filter(run=fresh_run).count(),
        "supplement_snapshot_count": ResearchSupplementSnapshot.objects.filter(run=fresh_run).count(),
        "fx_snapshot_count": ResearchFxSnapshot.objects.filter(run=fresh_run).count(),
        "micron_alias_count": ResearchMicronAliasSnapshot.objects.filter(run=fresh_run).count(),
        "evidence_count": ExecutionEvidenceRecord.objects.filter(run=fresh_run).count(),
        "review_candidate_count": AiAssistedReviewCandidate.objects.filter(run=fresh_run).count(),
        "comparable_count": ComparableResearchExecution.objects.filter(parent_run=fresh_run).count(),
    }
    price = PriceIntelligenceSnapshot.objects.filter(run=fresh_run).first()
    if price is not None:
        snapshot["price_schema_version"] = price.schema_version
        snapshot["price_payload"] = price.payload
        snapshot["price_created_at"] = price.created_at
    supplement = ResearchSupplementSnapshot.objects.filter(run=fresh_run).first()
    if supplement is not None:
        snapshot["supplement_schema_version"] = supplement.schema_version
        snapshot["supplement_payload"] = supplement.payload
        snapshot["supplement_created_at"] = supplement.created_at
    return snapshot


class _FakeVendorAdapter:
    """Canned-response adapter; records lookup() calls and simulated
    HTTP requests (one request per lookup that reaches the wire)."""

    constructions = 0

    def __init__(
        self,
        *,
        response: CommercialSourceResponse | None = None,
        raise_lookup: BaseException | None = None,
        http_requests_per_lookup: int = 1,
    ) -> None:
        type(self).constructions += 1
        self.response = response
        self.raise_lookup = raise_lookup
        self.http_requests_per_lookup = http_requests_per_lookup
        self.lookup_queries: list = []
        self.http_request_count = 0
        self.savepoint_depth_at_lookup: list[int] = []

    def lookup(self, query):
        self.lookup_queries.append(query)
        # I10 probe: record the savepoint depth while the (simulated)
        # request is in flight — the executor must not open any
        # transaction/savepoint of its own around the lookup.
        self.savepoint_depth_at_lookup.append(
            len(connections["default"].savepoint_ids)
        )
        if self.raise_lookup is not None:
            raise self.raise_lookup
        self.http_request_count += self.http_requests_per_lookup
        return self.response


class _CountingFactory:
    """Zero-arg counting factory (design section 3.2 sentinel
    discipline): records invocation and constructs the fake adapter."""

    def __init__(
        self,
        adapter_kwargs: dict | None = None,
        raise_construction: BaseException | None = None,
    ) -> None:
        self.invocations = 0
        self.adapter_kwargs = adapter_kwargs or {}
        self.raise_construction = raise_construction
        self.constructed: list[_FakeVendorAdapter] = []

    def __call__(self) -> _FakeVendorAdapter:
        self.invocations += 1
        if self.raise_construction is not None:
            raise self.raise_construction
        adapter = _FakeVendorAdapter(**self.adapter_kwargs)
        self.constructed.append(adapter)
        return adapter


def _spied_service(real):
    """Wrap a frozen terminal-CAS service with a call counter
    (behavior unchanged: the real service runs)."""
    calls: list = []

    def spy(*args, **kwargs):
        calls.append((args, kwargs))
        return real(*args, **kwargs)

    spy.calls = calls
    return spy


# ---------------------------------------------------------------------------
# S0 — argument discipline
# ---------------------------------------------------------------------------


class TestArgumentDiscipline(TestCase):
    """Exactly one adapter source (instance OR factory) — bounded
    refusal before any DB access, zero construction, zero lookup, zero
    terminal writes."""

    def _running_child(self) -> VendorRefreshExecution:
        return _make_running_child(_make_completed_run())

    def test_neither_adapter_nor_factory_refused(self) -> None:
        child = self._running_child()
        before = _row_snapshot(child.pk)
        fail_spy = _spied_service(fail_vendor_refresh)
        complete_spy = _spied_service(complete_vendor_refresh)
        with (
            patch.object(core, "fail_vendor_refresh", fail_spy),
            patch.object(core, "complete_vendor_refresh", complete_spy),
            patch.dict(os.environ, {CONFIGURED_ENV: CONFIGURED_BASE_URL}),
        ):
            with pytest.raises(VendorRefreshExecutionError) as excinfo:
                execute_claimed_vendor_refresh(child.id)
        assert excinfo.value.reason == VendorRefreshExecutionError.REASON_ADAPTER_ARGUMENT_CONFLICT
        assert _row_snapshot(child.pk) == before
        assert len(fail_spy.calls) == 0
        assert len(complete_spy.calls) == 0

    def test_both_adapter_and_factory_refused(self) -> None:
        child = self._running_child()
        before = _row_snapshot(child.pk)
        factory = _CountingFactory()
        fail_spy = _spied_service(fail_vendor_refresh)
        with (
            patch.object(core, "fail_vendor_refresh", fail_spy),
            patch.dict(os.environ, {CONFIGURED_ENV: CONFIGURED_BASE_URL}),
        ):
            with pytest.raises(VendorRefreshExecutionError) as excinfo:
                execute_claimed_vendor_refresh(
                    child.id,
                    vendor_adapter=_FakeVendorAdapter(),
                    vendor_adapter_factory=factory,
                )
        assert excinfo.value.reason == VendorRefreshExecutionError.REASON_ADAPTER_ARGUMENT_CONFLICT
        assert factory.invocations == 0
        assert len(fail_spy.calls) == 0
        assert _row_snapshot(child.pk) == before

    def test_non_callable_factory_refused(self) -> None:
        child = self._running_child()
        before = _row_snapshot(child.pk)
        fail_spy = _spied_service(fail_vendor_refresh)
        with (
            patch.object(core, "fail_vendor_refresh", fail_spy),
            patch.dict(os.environ, {CONFIGURED_ENV: CONFIGURED_BASE_URL}),
        ):
            with pytest.raises(VendorRefreshExecutionError) as excinfo:
                execute_claimed_vendor_refresh(
                    child.id, vendor_adapter_factory="not-callable"
                )
        assert excinfo.value.reason == VendorRefreshExecutionError.REASON_ADAPTER_ARGUMENT_CONFLICT
        assert len(fail_spy.calls) == 0
        assert _row_snapshot(child.pk) == before

    def test_invalid_child_id_is_bounded_state_refusal(self) -> None:
        factory = _CountingFactory(
            {"response": build_success_exact_match_response()}
        )
        fail_spy = _spied_service(fail_vendor_refresh)
        with (
            patch.object(core, "fail_vendor_refresh", fail_spy),
            patch.dict(os.environ, {CONFIGURED_ENV: CONFIGURED_BASE_URL}),
        ):
            with pytest.raises(VendorRefreshExecutionError) as excinfo:
                execute_claimed_vendor_refresh(
                    "not-a-uuid", vendor_adapter_factory=factory
                )
        assert excinfo.value.reason == VendorRefreshExecutionError.REASON_STATE_NOT_FOUND
        assert factory.invocations == 0
        assert len(fail_spy.calls) == 0

    def test_invalid_uuid_long_input_not_reflected_bounded_state_not_found(self) -> None:
        """FU1-F4 — a very long invalid child_id is refused with the
        bounded state_not_found reason and the input is NEVER
        reflected verbatim in the public error message; zero DB,
        adapter, or network activity."""
        factory = _CountingFactory({"response": build_success_exact_match_response()})
        fail_spy = _spied_service(fail_vendor_refresh)
        very_long = "invalid-uuid-" + "z" * 4096
        with (
            patch.object(core, "fail_vendor_refresh", fail_spy),
            patch.dict(os.environ, {CONFIGURED_ENV: CONFIGURED_BASE_URL}),
            CaptureQueriesContext(connections["default"]) as captured,
        ):
            with pytest.raises(VendorRefreshExecutionError) as excinfo:
                execute_claimed_vendor_refresh(very_long, vendor_adapter_factory=factory)
        assert excinfo.value.reason == VendorRefreshExecutionError.REASON_STATE_NOT_FOUND
        assert excinfo.value.child_id is None  # no identity carried
        assert very_long not in str(excinfo.value)  # not reflected verbatim
        assert len(captured.captured_queries) == 0  # no DB activity
        assert factory.invocations == 0  # no adapter -> no lookup -> no network
        assert len(fail_spy.calls) == 0

    def test_invalid_uuid_sensitive_marker_not_reflected_bounded_state_not_found(self) -> None:
        """FU1-F4 — a unique sensitive marker embedded in the invalid
        input is never reflected in the public error message; the
        reason remains bounded state_not_found; zero DB, adapter, or
        network activity."""
        factory = _CountingFactory({"response": build_success_exact_match_response()})
        fail_spy = _spied_service(fail_vendor_refresh)
        marker = "SENSITIVE-MARKER-7f3e9d1a-b4c2"
        bad_id = f"not-a-uuid-{marker}-tail"
        with (
            patch.object(core, "fail_vendor_refresh", fail_spy),
            patch.dict(os.environ, {CONFIGURED_ENV: CONFIGURED_BASE_URL}),
            CaptureQueriesContext(connections["default"]) as captured,
        ):
            with pytest.raises(VendorRefreshExecutionError) as excinfo:
                execute_claimed_vendor_refresh(bad_id, vendor_adapter_factory=factory)
        assert excinfo.value.reason == VendorRefreshExecutionError.REASON_STATE_NOT_FOUND
        assert excinfo.value.child_id is None  # no identity carried
        assert marker not in str(excinfo.value)
        assert bad_id not in str(excinfo.value)
        assert len(captured.captured_queries) == 0  # no DB activity
        assert factory.invocations == 0  # no adapter -> no lookup -> no network
        assert len(fail_spy.calls) == 0


# ---------------------------------------------------------------------------
# [A] — state re-assert refusals (fail-closed; zero writes)
# ---------------------------------------------------------------------------


class TestStateRefusal(TestCase):
    """Absent / PENDING / COMPLETED / FAILED (or otherwise not a valid
    RUNNING execution) child: bounded state refusal with ZERO adapter
    construction, ZERO lookup calls, ZERO terminal writes — the
    already-invalid execution state is never disposed of via
    ``fail_vendor_refresh`` (task section 5 mandatory fail-closed
    interpretation)."""

    def test_absent_child_refused_state_not_found(self) -> None:
        fail_spy = _spied_service(fail_vendor_refresh)
        complete_spy = _spied_service(complete_vendor_refresh)
        factory = _CountingFactory({"response": build_success_exact_match_response()})
        absent_id = uuid.uuid4()
        with (
            patch.object(core, "fail_vendor_refresh", fail_spy),
            patch.object(core, "complete_vendor_refresh", complete_spy),
            patch.dict(os.environ, {CONFIGURED_ENV: CONFIGURED_BASE_URL}),
        ):
            with pytest.raises(VendorRefreshExecutionError) as excinfo:
                execute_claimed_vendor_refresh(absent_id, vendor_adapter_factory=factory)
        assert excinfo.value.reason == VendorRefreshExecutionError.REASON_STATE_NOT_FOUND
        assert excinfo.value.durable_state is None
        assert factory.invocations == 0
        assert len(fail_spy.calls) == 0
        assert len(complete_spy.calls) == 0

    def test_pending_child_refused_state_not_running_zero_writes(self) -> None:
        run = _make_completed_run()
        child = _make_pending_child(run)
        before = _row_snapshot(child.pk)
        fail_spy = _spied_service(fail_vendor_refresh)
        complete_spy = _spied_service(complete_vendor_refresh)
        factory = _CountingFactory({"response": build_success_exact_match_response()})
        with (
            patch.object(core, "fail_vendor_refresh", fail_spy),
            patch.object(core, "complete_vendor_refresh", complete_spy),
            patch.dict(os.environ, {CONFIGURED_ENV: CONFIGURED_BASE_URL}),
        ):
            with pytest.raises(VendorRefreshExecutionError) as excinfo:
                execute_claimed_vendor_refresh(child.id, vendor_adapter_factory=factory)
        assert excinfo.value.reason == VendorRefreshExecutionError.REASON_STATE_NOT_RUNNING
        assert excinfo.value.durable_state == VendorRefreshState.PENDING
        assert factory.invocations == 0
        assert len(fail_spy.calls) == 0
        assert len(complete_spy.calls) == 0
        assert _row_snapshot(child.pk) == before

    def test_completed_child_refused_state_not_running_zero_writes(self) -> None:
        run = _make_completed_run()
        child = _make_running_child(run)
        complete_vendor_refresh(child.id, 1, _frozen_payload())
        before = _row_snapshot(child.pk)
        fail_spy = _spied_service(fail_vendor_refresh)
        complete_spy = _spied_service(complete_vendor_refresh)
        factory = _CountingFactory({"response": build_success_exact_match_response()})
        with (
            patch.object(core, "fail_vendor_refresh", fail_spy),
            patch.object(core, "complete_vendor_refresh", complete_spy),
            patch.dict(os.environ, {CONFIGURED_ENV: CONFIGURED_BASE_URL}),
        ):
            with pytest.raises(VendorRefreshExecutionError) as excinfo:
                execute_claimed_vendor_refresh(child.id, vendor_adapter_factory=factory)
        assert excinfo.value.reason == VendorRefreshExecutionError.REASON_STATE_NOT_RUNNING
        assert excinfo.value.durable_state == VendorRefreshState.COMPLETED
        assert factory.invocations == 0
        assert len(fail_spy.calls) == 0
        assert len(complete_spy.calls) == 0
        assert _row_snapshot(child.pk) == before

    def test_failed_child_refused_state_not_running_zero_writes(self) -> None:
        run = _make_completed_run()
        child = _make_running_child(run)
        fail_vendor_refresh(child.id, VendorRefreshFailureReason.INTERNAL_ERROR)
        before = _row_snapshot(child.pk)
        fail_spy = _spied_service(fail_vendor_refresh)
        complete_spy = _spied_service(complete_vendor_refresh)
        factory = _CountingFactory({"response": build_success_exact_match_response()})
        with (
            patch.object(core, "fail_vendor_refresh", fail_spy),
            patch.object(core, "complete_vendor_refresh", complete_spy),
            patch.dict(os.environ, {CONFIGURED_ENV: CONFIGURED_BASE_URL}),
        ):
            with pytest.raises(VendorRefreshExecutionError) as excinfo:
                execute_claimed_vendor_refresh(child.id, vendor_adapter_factory=factory)
        assert excinfo.value.reason == VendorRefreshExecutionError.REASON_STATE_NOT_RUNNING
        assert excinfo.value.durable_state == VendorRefreshState.FAILED
        assert factory.invocations == 0
        assert len(fail_spy.calls) == 0
        assert len(complete_spy.calls) == 0
        assert _row_snapshot(child.pk) == before

    def test_refusal_reasons_are_bounded_non_persisted(self) -> None:
        """Every state refusal is a bounded VendorRefreshExecutionError
        whose reason sits in the non-persisted vocabulary (no
        terminal write was issued, so no persisted reason applies)."""
        run = _make_completed_run()
        pending = _make_pending_child(run, operator="op-p")
        complete_spy = _spied_service(complete_vendor_refresh)
        fail_spy = _spied_service(fail_vendor_refresh)
        with (
            patch.object(core, "fail_vendor_refresh", fail_spy),
            patch.object(core, "complete_vendor_refresh", complete_spy),
            patch.dict(os.environ, {CONFIGURED_ENV: CONFIGURED_BASE_URL}),
        ):
            with pytest.raises(VendorRefreshExecutionError) as excinfo:
                execute_claimed_vendor_refresh(uuid.uuid4(), vendor_adapter_factory=_CountingFactory())
            assert excinfo.value.reason in VendorRefreshExecutionError.NON_PERSISTED_REASONS
            with pytest.raises(VendorRefreshExecutionError) as excinfo:
                execute_claimed_vendor_refresh(pending.id, vendor_adapter_factory=_CountingFactory())
            assert excinfo.value.reason in VendorRefreshExecutionError.NON_PERSISTED_REASONS
            assert excinfo.value.reason == VendorRefreshExecutionError.REASON_STATE_NOT_RUNNING
        assert len(fail_spy.calls) == 0
        assert len(complete_spy.calls) == 0


# ---------------------------------------------------------------------------
# Valid RUNNING path — S4-S9, T1, LB-2 (exactly one lookup)
# ---------------------------------------------------------------------------


class TestValidRunningSuccessPath(TestCase):
    """A valid RUNNING child: preflight passes, the factory is invoked
    exactly once (first construction, I13), exactly one lookup (LB-2),
    full V1 codec encoding before the complete CAS, T1 return."""

    def _spies(self):
        return _spied_service(fail_vendor_refresh), _spied_service(complete_vendor_refresh)

    def test_success_single_lookup_completes_with_golden_payload(self) -> None:
        run = _make_completed_run()
        child = _make_running_child(run)
        artifacts_before = _parent_artifact_snapshot(run)
        fail_spy, complete_spy = self._spies()
        factory = _CountingFactory({"response": build_success_exact_match_response()})
        with (
            patch.object(core, "fail_vendor_refresh", fail_spy),
            patch.object(core, "complete_vendor_refresh", complete_spy),
            patch.dict(os.environ, {CONFIGURED_ENV: CONFIGURED_BASE_URL}),
        ):
            returned = execute_claimed_vendor_refresh(child.id, vendor_adapter_factory=factory)
        # T1 — the frozen service's re-read durably stored row.
        assert returned.id == child.id
        row = _row_snapshot(child.pk)
        assert row["state"] == VendorRefreshState.COMPLETED
        assert row["active_slot"] is None
        assert row["finished_at"] is not None
        assert row["result_schema_version"] == 1
        # Policy equivalence: the stored payload IS the R1-1 golden.
        assert row["result_payload"] == GOLDEN_SUCCESS_EXACT_MATCH
        # LB-2: exactly one construction, exactly one lookup.
        assert factory.invocations == 1
        adapter = factory.constructed[0]
        assert len(adapter.lookup_queries) == 1
        assert adapter.lookup_queries[0].mpn == child.requested_mpn == GOLDEN_MPN
        assert adapter.http_request_count == 1
        # Single complete, zero fail.
        assert len(complete_spy.calls) == 1
        assert len(fail_spy.calls) == 0
        # I7: parent and all original artifacts byte-identical.
        assert _parent_artifact_snapshot(run) == artifacts_before

    def test_partial_response_completes_with_partial_status(self) -> None:
        run = _make_completed_run()
        child = _make_running_child(run)
        factory = _CountingFactory({"response": build_mixed_usable_and_unusable_response()})
        with patch.dict(os.environ, {CONFIGURED_ENV: CONFIGURED_BASE_URL}):
            execute_claimed_vendor_refresh(child.id, vendor_adapter_factory=factory)
        row = _row_snapshot(child.pk)
        assert row["state"] == VendorRefreshState.COMPLETED
        assert row["result_payload"] == GOLDEN_MIXED_USABLE_AND_UNUSABLE
        assert factory.invocations == 1
        assert len(factory.constructed[0].lookup_queries) == 1

    def test_transport_failed_response_is_completed_result_not_machinery_failure(self) -> None:
        """Transport-level FAILED CommercialSourceResponse: child state
        COMPLETED, encoded lookup_status FAILED, retrieved_at None — no
        automatic execution-machinery failure (task section 6)."""
        run = _make_completed_run()
        child = _make_running_child(run)
        fail_spy, complete_spy = self._spies()
        factory = _CountingFactory(
            {"response": build_transport_failed_no_retrieved_at_response()}
        )
        with (
            patch.object(core, "fail_vendor_refresh", fail_spy),
            patch.object(core, "complete_vendor_refresh", complete_spy),
            patch.dict(os.environ, {CONFIGURED_ENV: CONFIGURED_BASE_URL}),
        ):
            execute_claimed_vendor_refresh(child.id, vendor_adapter_factory=factory)
        row = _row_snapshot(child.pk)
        assert row["state"] == VendorRefreshState.COMPLETED  # NOT FAILED
        assert row["result_payload"] == GOLDEN_TRANSPORT_FAILED_NO_RETRIEVED_AT
        assert row["result_payload"]["vendor_commercial_result"]["lookup_status"] == "FAILED"
        assert row["result_payload"]["vendor_commercial_result"]["retrieved_at"] is None
        assert len(fail_spy.calls) == 0
        assert len(complete_spy.calls) == 1
        assert factory.invocations == 1
        assert len(factory.constructed[0].lookup_queries) == 1

    def test_transport_failed_with_stale_retrieved_at_cleared(self) -> None:
        run = _make_completed_run()
        child = _make_running_child(run)
        factory = _CountingFactory(
            {"response": build_transport_failed_retrieved_at_cleared_response()}
        )
        with patch.dict(os.environ, {CONFIGURED_ENV: CONFIGURED_BASE_URL}):
            execute_claimed_vendor_refresh(child.id, vendor_adapter_factory=factory)
        row = _row_snapshot(child.pk)
        assert row["state"] == VendorRefreshState.COMPLETED
        assert row["result_payload"] == GOLDEN_TRANSPORT_FAILED_RETRIEVED_AT_CLEARED
        assert row["result_payload"]["vendor_commercial_result"]["retrieved_at"] is None

    def test_full_v1_codec_encoding_happens_before_the_complete_cas(self) -> None:
        """The complete CAS receives the FULL frozen V1-encoded dict
        (decode-able, schema V1, golden-equal) — no malformed or
        partial payload is ever published."""
        run = _make_completed_run()
        child = _make_running_child(run)
        fail_spy, complete_spy = self._spies()
        factory = _CountingFactory({"response": build_success_exact_match_response()})
        with (
            patch.object(core, "fail_vendor_refresh", fail_spy),
            patch.object(core, "complete_vendor_refresh", complete_spy),
            patch.dict(os.environ, {CONFIGURED_ENV: CONFIGURED_BASE_URL}),
        ):
            execute_claimed_vendor_refresh(child.id, vendor_adapter_factory=factory)
        assert len(complete_spy.calls) == 1
        args, kwargs = complete_spy.calls[0]
        assert args[0] == str(child.id)
        assert args[1] == 1  # frozen V1 schema version
        encoded = args[2]
        # The frozen decoder accepts exactly what the complete CAS stored.
        decoded = decode_research_supplement_result(encoded)
        assert encoded == GOLDEN_SUCCESS_EXACT_MATCH
        assert _row_snapshot(child.pk)["result_payload"] == GOLDEN_SUCCESS_EXACT_MATCH
        assert decoded.vendor_commercial_result.lookup_status == "SUCCESS"

    def test_adapter_instance_path_uses_supplied_double(self) -> None:
        """A pre-constructed adapter instance (test doubles only in R1)
        is used as-is: no factory, exactly one lookup."""
        run = _make_completed_run()
        child = _make_running_child(run)
        adapter = _FakeVendorAdapter(response=build_success_exact_match_response())
        with patch.dict(os.environ, {CONFIGURED_ENV: CONFIGURED_BASE_URL}):
            execute_claimed_vendor_refresh(child.id, vendor_adapter=adapter)
        assert len(adapter.lookup_queries) == 1
        assert adapter.http_request_count == 1
        row = _row_snapshot(child.pk)
        assert row["state"] == VendorRefreshState.COMPLETED
        assert row["result_payload"] == GOLDEN_SUCCESS_EXACT_MATCH

    def test_no_transaction_open_across_the_lookup(self) -> None:
        """I10 — no database transaction (savepoint) of the executor's
        own surrounds the lookup: the savepoint depth at lookup time
        equals the depth before the call."""
        run = _make_completed_run()
        child = _make_running_child(run)
        factory = _CountingFactory({"response": build_success_exact_match_response()})
        depth_before = len(connections["default"].savepoint_ids)
        with patch.dict(os.environ, {CONFIGURED_ENV: CONFIGURED_BASE_URL}):
            execute_claimed_vendor_refresh(child.id, vendor_adapter_factory=factory)
        adapter = factory.constructed[0]
        assert adapter.savepoint_depth_at_lookup == [depth_before]

    def test_runtime_entry_delegates_with_the_adapter_class_as_factory(self) -> None:
        """The runtime supplies the concrete InternalVendorAdapter CLASS
        as the zero-arg factory (function-level import) and delegates
        once; it constructs nothing itself (O9)."""
        run = _make_completed_run()
        child = _make_running_child(run)
        sentinel = object()
        delegations: list[dict] = []

        def fake_execute(child_id, *, vendor_adapter=None, vendor_adapter_factory=None):
            delegations.append(
                {
                    "child_id": child_id,
                    "vendor_adapter": vendor_adapter,
                    "vendor_adapter_factory": vendor_adapter_factory,
                }
            )
            return sentinel

        class _FakeAdapterClass:
            constructions = 0

            def __init__(self):
                type(self).constructions += 1

        with (
            patch.object(
                core, "execute_claimed_vendor_refresh", fake_execute
            ),
            patch(
                "product_intelligence.providers.internal_vendor.InternalVendorAdapter",
                _FakeAdapterClass,
            ),
        ):
            result = execute_claimed_vendor_refresh_with_default_providers(child.id)
        assert result is sentinel
        assert len(delegations) == 1
        assert delegations[0]["vendor_adapter"] is None
        assert delegations[0]["vendor_adapter_factory"] is _FakeAdapterClass
        # The runtime itself constructed nothing; the single
        # construction belongs to the core's S7 (not invoked here
        # because the delegation was faked).
        assert _FakeAdapterClass.constructions == 0

    def test_runtime_entry_end_to_end_with_patched_default_adapter(self) -> None:
        """Runtime entry over a real RUNNING child: the patched
        default adapter class is constructed exactly once (at S7) and
        looked up exactly once; the child completes with the golden
        payload."""
        run = _make_completed_run()
        child = _make_running_child(run)

        class _FakeAdapterClass:
            constructions = 0
            lookups = 0

            def lookup(self, query):
                type(self).lookups += 1
                return build_success_exact_match_response()

            def __init__(self):
                type(self).constructions += 1

        with (
            patch(
                "product_intelligence.providers.internal_vendor.InternalVendorAdapter",
                _FakeAdapterClass,
            ),
            patch.dict(os.environ, {CONFIGURED_ENV: CONFIGURED_BASE_URL}),
        ):
            execute_claimed_vendor_refresh_with_default_providers(child.id)
        assert _FakeAdapterClass.constructions == 1
        assert _FakeAdapterClass.lookups == 1
        row = _row_snapshot(child.pk)
        assert row["state"] == VendorRefreshState.COMPLETED
        assert row["result_payload"] == GOLDEN_SUCCESS_EXACT_MATCH

    def test_runtime_entry_zero_construction_on_state_refusal(self) -> None:
        """O9/LB-3 — the runtime's lazy factory means a state refusal
        never constructs the default adapter (the eager-construction
        precedent would have constructed it here)."""
        run = _make_completed_run()
        child = _make_pending_child(run)

        class _FakeAdapterClass:
            constructions = 0

            def __init__(self):
                type(self).constructions += 1

            def lookup(self, query):
                raise AssertionError("lookup must not run")

        with (
            patch(
                "product_intelligence.providers.internal_vendor.InternalVendorAdapter",
                _FakeAdapterClass,
            ),
            patch.dict(os.environ, {CONFIGURED_ENV: CONFIGURED_BASE_URL}),
        ):
            with pytest.raises(VendorRefreshExecutionError) as excinfo:
                execute_claimed_vendor_refresh_with_default_providers(child.id)
        assert excinfo.value.reason == VendorRefreshExecutionError.REASON_STATE_NOT_RUNNING
        assert _FakeAdapterClass.constructions == 0


# ---------------------------------------------------------------------------
# S4 — parent load + eligible COMPLETED re-check + captured-MPN binding
# ---------------------------------------------------------------------------


class TestMPNBindingViolation(TestCase):
    """S4 defects: bounded MPN_BINDING_VIOLATION fail, zero
    construction, zero lookup."""

    def _assert_binding_violation(self, child: VendorRefreshExecution) -> tuple:
        run = VendorRefreshExecution.objects.get(pk=child.pk).parent_run
        artifacts_before = _parent_artifact_snapshot(run)
        fail_spy = _spied_service(fail_vendor_refresh)
        complete_spy = _spied_service(complete_vendor_refresh)
        factory = _CountingFactory({"response": build_success_exact_match_response()})
        with (
            patch.object(core, "fail_vendor_refresh", fail_spy),
            patch.object(core, "complete_vendor_refresh", complete_spy),
            patch.dict(os.environ, {CONFIGURED_ENV: CONFIGURED_BASE_URL}),
        ):
            with pytest.raises(VendorRefreshExecutionError) as excinfo:
                execute_claimed_vendor_refresh(child.id, vendor_adapter_factory=factory)
        row = _row_snapshot(child.pk)
        assert excinfo.value.reason == VendorRefreshFailureReason.MPN_BINDING_VIOLATION
        assert excinfo.value.durable_state == VendorRefreshState.FAILED
        assert row["state"] == VendorRefreshState.FAILED
        assert row["failure_reason"] == VendorRefreshFailureReason.MPN_BINDING_VIOLATION
        assert row["result_schema_version"] is None
        assert row["result_payload"] is None
        assert factory.invocations == 0
        assert len(fail_spy.calls) == 1
        assert len(complete_spy.calls) == 0
        assert _parent_artifact_snapshot(run) == artifacts_before
        return factory, fail_spy, complete_spy

    def test_requested_mpn_tampered_fails_binding_violation(self) -> None:
        run = _make_completed_run()
        child = _make_running_child(run)
        VendorRefreshExecution.objects.filter(id=child.id).update(
            requested_mpn="TAMPERED-MPN"
        )
        self._assert_binding_violation(child)

    def test_parent_no_longer_completed_fails_binding_violation(self) -> None:
        run = _make_completed_run()
        child = _make_running_child(run)
        # Defensive S4 re-check: a parent that left COMPLETED (anomalous
        # raw write) is not an eligible execution parent.
        ResearchRun.objects.filter(id=run.id).update(state="FAILED")
        self._assert_binding_violation(child)

    def test_binding_violation_never_rewrites_the_captured_mpn(self) -> None:
        run = _make_completed_run()
        child = _make_running_child(run)
        VendorRefreshExecution.objects.filter(id=child.id).update(
            requested_mpn="TAMPERED-MPN"
        )
        self._assert_binding_violation(child)
        row = _row_snapshot(child.pk)
        assert row["requested_mpn"] == "TAMPERED-MPN"  # byte-identical
        assert row["operator"] == "op-a"


# ---------------------------------------------------------------------------
# S4 — parent-load fault classification (FU1-F1)
# ---------------------------------------------------------------------------


class TestParentLoadFaults(TestCase):
    """FU1-F1 — the S4 parent load classifies faults precisely:

    * a DATABASE read error (fault-injected ``django.db.
      OperationalError``) is a bounded INTERNAL_ERROR infrastructure
      failure — NEVER an MPN identity conflict (MPN_BINDING_VIOLATION
      is not persisted), with ZERO adapter construction and ZERO
      Vendor lookup;
    * an unexpected programming error PROPAGATES — it is never
      silently converted into missing-parent evidence and issues zero
      terminal writes (the child stays RUNNING).

    Genuine missing-parent facts and parent state/MPN contract
    violations retain MPN_BINDING_VIOLATION (the TestMPNBindingViolation
    nodes above)."""

    def test_parent_load_database_error_is_internal_error_not_binding_violation(self) -> None:
        """Fault injection: the parent read raises ``django.db.
        OperationalError`` — MPN_BINDING_VIOLATION is NOT persisted,
        no Vendor construction/lookup occurs, and the approved bounded
        INTERNAL_ERROR infrastructure handling applies (the single
        outer-boundary fail with its own T1-T4 contract)."""
        run = _make_completed_run()
        child = _make_running_child(run)
        fail_spy = _spied_service(fail_vendor_refresh)
        complete_spy = _spied_service(complete_vendor_refresh)
        factory = _CountingFactory({"response": build_success_exact_match_response()})
        parent_descriptor = VendorRefreshExecution.parent_run
        with (
            patch.object(
                parent_descriptor,
                "get_object",
                side_effect=OperationalError(
                    "fault: parent read infrastructure failure"
                ),
            ),
            patch.object(core, "fail_vendor_refresh", fail_spy),
            patch.object(core, "complete_vendor_refresh", complete_spy),
            patch.dict(os.environ, {CONFIGURED_ENV: CONFIGURED_BASE_URL}),
        ):
            with pytest.raises(VendorRefreshExecutionError) as excinfo:
                execute_claimed_vendor_refresh(child.id, vendor_adapter_factory=factory)
        # Bounded infrastructure failure — NOT an MPN identity conflict.
        assert excinfo.value.reason == VendorRefreshFailureReason.INTERNAL_ERROR
        assert excinfo.value.reason != VendorRefreshFailureReason.MPN_BINDING_VIOLATION
        assert excinfo.value.durable_state == VendorRefreshState.FAILED
        # MPN_BINDING_VIOLATION is not persisted.
        row = _row_snapshot(child.pk)
        assert row["state"] == VendorRefreshState.FAILED
        assert row["failure_reason"] == VendorRefreshFailureReason.INTERNAL_ERROR
        assert row["failure_reason"] != VendorRefreshFailureReason.MPN_BINDING_VIOLATION
        assert row["result_schema_version"] is None
        assert row["result_payload"] is None
        # Zero adapter construction -> zero Vendor lookup.
        assert factory.invocations == 0
        assert len(fail_spy.calls) == 1  # the single outer-boundary fail
        assert len(complete_spy.calls) == 0

    def test_parent_load_programming_error_is_not_missing_parent_evidence(self) -> None:
        """An unexpected programming error from the parent load
        PROPAGATES: it is never silently converted into missing-parent
        evidence (MPN_BINDING_VIOLATION) nor into a bounded
        infrastructure failure — the child stays RUNNING, zero writes,
        zero construction."""
        run = _make_completed_run()
        child = _make_running_child(run)
        before = _row_snapshot(child.pk)
        fail_spy = _spied_service(fail_vendor_refresh)
        complete_spy = _spied_service(complete_vendor_refresh)
        factory = _CountingFactory({"response": build_success_exact_match_response()})
        parent_descriptor = VendorRefreshExecution.parent_run
        with (
            patch.object(
                parent_descriptor,
                "get_object",
                side_effect=TypeError("fault: programming defect in parent load"),
            ),
            patch.object(core, "fail_vendor_refresh", fail_spy),
            patch.object(core, "complete_vendor_refresh", complete_spy),
            patch.dict(os.environ, {CONFIGURED_ENV: CONFIGURED_BASE_URL}),
        ):
            with pytest.raises(TypeError):
                execute_claimed_vendor_refresh(child.id, vendor_adapter_factory=factory)
        assert _row_snapshot(child.pk) == before  # zero writes
        assert factory.invocations == 0
        assert len(fail_spy.calls) == 0
        assert len(complete_spy.calls) == 0


# ---------------------------------------------------------------------------
# S5 — deployment configuration
# ---------------------------------------------------------------------------


class TestVendorConfigMissing(TestCase):
    """S5 defects: bounded VENDOR_LOOKUP_CONFIG_MISSING fail, zero
    construction, zero lookup, zero HTTP requests."""

    def _assert_config_missing(self, child: VendorRefreshExecution, env: dict) -> None:
        fail_spy = _spied_service(fail_vendor_refresh)
        complete_spy = _spied_service(complete_vendor_refresh)
        factory = _CountingFactory({"response": build_success_exact_match_response()})
        with (
            patch.object(core, "fail_vendor_refresh", fail_spy),
            patch.object(core, "complete_vendor_refresh", complete_spy),
            patch.dict(os.environ, env, clear=True),
        ):
            with pytest.raises(VendorRefreshExecutionError) as excinfo:
                execute_claimed_vendor_refresh(child.id, vendor_adapter_factory=factory)
        row = _row_snapshot(child.pk)
        assert excinfo.value.reason == VendorRefreshFailureReason.VENDOR_LOOKUP_CONFIG_MISSING
        assert excinfo.value.durable_state == VendorRefreshState.FAILED
        assert row["state"] == VendorRefreshState.FAILED
        assert row["failure_reason"] == VendorRefreshFailureReason.VENDOR_LOOKUP_CONFIG_MISSING
        assert row["result_schema_version"] is None
        assert row["result_payload"] is None
        assert factory.invocations == 0
        assert len(fail_spy.calls) == 1
        assert len(complete_spy.calls) == 0

    def test_missing_base_url_fails_config_missing(self) -> None:
        child = _make_running_child(_make_completed_run())
        self._assert_config_missing(child, env={})

    def test_blank_base_url_fails_config_missing(self) -> None:
        child = _make_running_child(_make_completed_run())
        self._assert_config_missing(child, env={CONFIGURED_ENV: "   "})

    def test_config_check_precedes_normalization_check(self) -> None:
        """S5 fires before S6: a whitespace-MPN child (which would also
        be a normalization mismatch) with no config fails with
        VENDOR_LOOKUP_CONFIG_MISSING — the approved S4-S9 order."""
        run = _make_completed_run()
        child = _make_running_child(run)
        whitespace_mpn = f"{GOLDEN_MPN} "
        ResearchRun.objects.filter(id=run.id).update(
            manufacturer_part_number=whitespace_mpn
        )
        VendorRefreshExecution.objects.filter(id=child.id).update(
            requested_mpn=whitespace_mpn
        )
        self._assert_config_missing(child, env={})


# ---------------------------------------------------------------------------
# S6 — query construction + normalization agreement (pre-adapter)
# ---------------------------------------------------------------------------


class TestNormalizationMismatch(TestCase):
    """S6 defects: the frozen query type would transmit an MPN
    different from the immutable captured binding — bounded
    MPN_QUERY_NORMALIZATION_MISMATCH fail, zero construction, zero
    lookup, the captured MPN never rewritten."""

    def _assert_normalization_mismatch(self, child: VendorRefreshExecution) -> None:
        fail_spy = _spied_service(fail_vendor_refresh)
        complete_spy = _spied_service(complete_vendor_refresh)
        factory = _CountingFactory({"response": build_success_exact_match_response()})
        with (
            patch.object(core, "fail_vendor_refresh", fail_spy),
            patch.object(core, "complete_vendor_refresh", complete_spy),
            patch.dict(os.environ, {CONFIGURED_ENV: CONFIGURED_BASE_URL}),
        ):
            with pytest.raises(VendorRefreshExecutionError) as excinfo:
                execute_claimed_vendor_refresh(child.id, vendor_adapter_factory=factory)
        row = _row_snapshot(child.pk)
        assert (
            excinfo.value.reason
            == VendorRefreshFailureReason.MPN_QUERY_NORMALIZATION_MISMATCH
        )
        assert excinfo.value.durable_state == VendorRefreshState.FAILED
        assert row["state"] == VendorRefreshState.FAILED
        assert (
            row["failure_reason"]
            == VendorRefreshFailureReason.MPN_QUERY_NORMALIZATION_MISMATCH
        )
        assert factory.invocations == 0
        assert len(fail_spy.calls) == 1
        assert len(complete_spy.calls) == 0

    def test_surrounding_whitespace_mpn_fails_before_any_adapter(self) -> None:
        """Fixture-level whitespace capture (trigger verbatim capture is
        R0-pinned): the query strips, so the transmitted MPN would
        diverge from the captured binding — rejected pre-adapter."""
        run = _make_completed_run()
        child = _make_running_child(run)
        whitespace_mpn = f"{GOLDEN_MPN} "
        ResearchRun.objects.filter(id=run.id).update(
            manufacturer_part_number=whitespace_mpn
        )
        VendorRefreshExecution.objects.filter(id=child.id).update(
            requested_mpn=whitespace_mpn
        )
        self._assert_normalization_mismatch(child)
        assert _row_snapshot(child.pk)["requested_mpn"] == whitespace_mpn

    def test_all_whitespace_mpn_fails_before_any_adapter(self) -> None:
        run = _make_completed_run()
        child = _make_running_child(run)
        ResearchRun.objects.filter(id=run.id).update(manufacturer_part_number="   ")
        VendorRefreshExecution.objects.filter(id=child.id).update(
            requested_mpn="   "
        )
        self._assert_normalization_mismatch(child)
        assert _row_snapshot(child.pk)["requested_mpn"] == "   "


# ---------------------------------------------------------------------------
# S7 — lazy factory construction + single lookup (no retry)
# ---------------------------------------------------------------------------


class TestFactoryAndProviderErrors(TestCase):
    """S7: the factory is the first (and only) construction point; a
    construction failure or a provider programming exception is a
    bounded INTERNAL_ERROR fail with no Vendor request re-issued."""

    def test_factory_invoked_exactly_once_on_success(self) -> None:
        run = _make_completed_run()
        child = _make_running_child(run)
        factory = _CountingFactory({"response": build_success_exact_match_response()})
        with patch.dict(os.environ, {CONFIGURED_ENV: CONFIGURED_BASE_URL}):
            execute_claimed_vendor_refresh(child.id, vendor_adapter_factory=factory)
        assert factory.invocations == 1
        assert len(factory.constructed) == 1
        assert len(factory.constructed[0].lookup_queries) == 1

    def test_factory_construction_failure_internal_error(self) -> None:
        run = _make_completed_run()
        child = _make_running_child(run)
        artifacts_before = _parent_artifact_snapshot(run)
        fail_spy = _spied_service(fail_vendor_refresh)
        complete_spy = _spied_service(complete_vendor_refresh)
        factory = _CountingFactory(raise_construction=RuntimeError("factory defect"))
        with (
            patch.object(core, "fail_vendor_refresh", fail_spy),
            patch.object(core, "complete_vendor_refresh", complete_spy),
            patch.dict(os.environ, {CONFIGURED_ENV: CONFIGURED_BASE_URL}),
        ):
            with pytest.raises(VendorRefreshExecutionError) as excinfo:
                execute_claimed_vendor_refresh(child.id, vendor_adapter_factory=factory)
        row = _row_snapshot(child.pk)
        assert excinfo.value.reason == VendorRefreshFailureReason.INTERNAL_ERROR
        assert excinfo.value.durable_state == VendorRefreshState.FAILED
        assert row["state"] == VendorRefreshState.FAILED
        assert row["failure_reason"] == VendorRefreshFailureReason.INTERNAL_ERROR
        # factory 1 (failed), no object, lookup 0, HTTP 0.
        assert factory.invocations == 1
        assert factory.constructed == []
        assert len(fail_spy.calls) == 1
        assert len(complete_spy.calls) == 0
        assert _parent_artifact_snapshot(run) == artifacts_before

    def test_lookup_programming_exception_internal_error_no_retry(self) -> None:
        run = _make_completed_run()
        child = _make_running_child(run)
        fail_spy = _spied_service(fail_vendor_refresh)
        complete_spy = _spied_service(complete_vendor_refresh)
        factory = _CountingFactory(
            {
                "response": build_success_exact_match_response(),
                "raise_lookup": RuntimeError("provider programming defect"),
                "http_requests_per_lookup": 0,  # the request never reached the wire
            }
        )
        with (
            patch.object(core, "fail_vendor_refresh", fail_spy),
            patch.object(core, "complete_vendor_refresh", complete_spy),
            patch.dict(os.environ, {CONFIGURED_ENV: CONFIGURED_BASE_URL}),
        ):
            with pytest.raises(VendorRefreshExecutionError) as excinfo:
                execute_claimed_vendor_refresh(child.id, vendor_adapter_factory=factory)
        row = _row_snapshot(child.pk)
        assert excinfo.value.reason == VendorRefreshFailureReason.INTERNAL_ERROR
        assert row["state"] == VendorRefreshState.FAILED
        assert row["failure_reason"] == VendorRefreshFailureReason.INTERNAL_ERROR
        adapter = factory.constructed[0]
        # Exactly one lookup attempt — never retried.
        assert len(adapter.lookup_queries) == 1
        assert adapter.http_request_count == 0
        assert factory.invocations == 1
        assert len(fail_spy.calls) == 1
        assert len(complete_spy.calls) == 0

    def test_malformed_nonblank_base_url_real_adapter_zero_http(self) -> None:
        """The approved config split (design section 10.3): a MALFORMED
        non-blank base URL passes S5 (non-blank), the factory IS
        invoked (1 construction — side-effect-free), the real adapter's
        lookup() raises ValueError in _ensure_configured — its first
        statement, before any Request/opener — so lookup() is 1
        (raised) with HTTP requests 0, and the child fails with
        INTERNAL_ERROR (the bounded reason does not overclaim)."""
        run = _make_completed_run()
        child = _make_running_child(run)
        fail_spy = _spied_service(fail_vendor_refresh)
        complete_spy = _spied_service(complete_vendor_refresh)

        opener_probe_calls = []

        def opener_probe():
            opener_probe_calls.append(1)
            raise AssertionError("no HTTP request may be built")

        from product_intelligence.providers.internal_vendor import (
            InternalVendorAdapter,
        )

        with (
            patch.object(core, "fail_vendor_refresh", fail_spy),
            patch.object(core, "complete_vendor_refresh", complete_spy),
            patch.dict(
                os.environ, {CONFIGURED_ENV: "not-a-valid-base-url"}, clear=True
            ),
            patch(
                "product_intelligence.providers.internal_vendor._get_vendor_opener",
                side_effect=opener_probe,
            ),
        ):
            with pytest.raises(VendorRefreshExecutionError) as excinfo:
                execute_claimed_vendor_refresh(
                    child.id, vendor_adapter_factory=InternalVendorAdapter
                )
        row = _row_snapshot(child.pk)
        assert excinfo.value.reason == VendorRefreshFailureReason.INTERNAL_ERROR
        assert excinfo.value.durable_state == VendorRefreshState.FAILED
        assert row["state"] == VendorRefreshState.FAILED
        assert row["failure_reason"] == VendorRefreshFailureReason.INTERNAL_ERROR
        assert len(fail_spy.calls) == 1
        assert len(complete_spy.calls) == 0
        assert opener_probe_calls == []  # HTTP requests: 0


# ---------------------------------------------------------------------------
# S8 — bind and encode (D10 helper) before the complete CAS
# ---------------------------------------------------------------------------


class TestResultEncodingFailed(TestCase):
    """S8: a codec encoding failure is RESULT_ENCODING_FAILED — the
    full V1 encoding happens before the complete CAS, so no malformed
    COMPLETED payload is ever published."""

    def test_codec_encoding_failure_result_encoding_failed(self) -> None:
        run = _make_completed_run()
        child = _make_running_child(run)
        artifacts_before = _parent_artifact_snapshot(run)
        fail_spy = _spied_service(fail_vendor_refresh)
        complete_spy = _spied_service(complete_vendor_refresh)
        factory = _CountingFactory({"response": build_success_exact_match_response()})
        with (
            patch.object(core, "fail_vendor_refresh", fail_spy),
            patch.object(core, "complete_vendor_refresh", complete_spy),
            patch.dict(os.environ, {CONFIGURED_ENV: CONFIGURED_BASE_URL}),
            patch(
                "product_intelligence.research.commercial_supplement_codec."
                "encode_research_supplement_result",
                side_effect=SupplementCodecError("codec failure"),
            ),
        ):
            with pytest.raises(VendorRefreshExecutionError) as excinfo:
                execute_claimed_vendor_refresh(child.id, vendor_adapter_factory=factory)
        row = _row_snapshot(child.pk)
        assert excinfo.value.reason == VendorRefreshFailureReason.RESULT_ENCODING_FAILED
        assert excinfo.value.durable_state == VendorRefreshState.FAILED
        assert row["state"] == VendorRefreshState.FAILED
        assert row["failure_reason"] == VendorRefreshFailureReason.RESULT_ENCODING_FAILED
        # The lookup DID run (factory 1, lookup 1, HTTP 1); no COMPLETED
        # row, no payload.
        assert factory.invocations == 1
        assert len(factory.constructed[0].lookup_queries) == 1
        assert factory.constructed[0].http_request_count == 1
        assert row["result_schema_version"] is None
        assert row["result_payload"] is None
        assert len(fail_spy.calls) == 1
        assert len(complete_spy.calls) == 0
        assert _parent_artifact_snapshot(run) == artifacts_before


# ---------------------------------------------------------------------------
# S9 — T1-T4 terminal-CAS outcome contract (FU3-F1)
# ---------------------------------------------------------------------------


class TestTerminalCasOutcomes(TestCase):
    """The frozen services return the re-read row on success (T1) and
    raise the typed error with reason=None on a zero-row CAS (T2) —
    there is no exposed rowcount; explicit-reason raises are T2b
    defects (never CAS losers); Django database errors are T3/T4
    (classified by the reconciliation fresh read, never assumed)."""

    def _running_child_with_spy(self):
        run = _make_completed_run()
        child = _make_running_child(run)
        fail_spy = _spied_service(fail_vendor_refresh)
        complete_spy = _spied_service(complete_vendor_refresh)
        return run, child, fail_spy, complete_spy

    def test_t1_success_returns_the_durable_stored_row(self) -> None:
        run, child, fail_spy, complete_spy = self._running_child_with_spy()
        factory = _CountingFactory({"response": build_success_exact_match_response()})
        with (
            patch.object(core, "fail_vendor_refresh", fail_spy),
            patch.object(core, "complete_vendor_refresh", complete_spy),
            patch.dict(os.environ, {CONFIGURED_ENV: CONFIGURED_BASE_URL}),
        ):
            returned = execute_claimed_vendor_refresh(child.id, vendor_adapter_factory=factory)
        row = _row_snapshot(child.pk)
        assert returned.pk == child.pk
        assert returned.state == VendorRefreshState.COMPLETED
        assert returned.result_payload == row["result_payload"] == GOLDEN_SUCCESS_EXACT_MATCH
        assert returned is not row  # the service's own re-read, not a proxy
        assert len(complete_spy.calls) == 1
        assert len(fail_spy.calls) == 0

    def test_t2_lost_complete_cas_reports_actual_terminal_state(self) -> None:
        """D — the competing terminal write (test-local row-4 writer,
        real frozen service) commits AFTER the executor's [A] read and
        BEFORE the complete UPDATE runs (the mocked interleaving of the
        race); the executor's REAL complete_vendor_refresh then raises
        the typed reason=None zero-row error; the pinned read-only
        reconciliation fresh-reads and reports the ACTUAL durable
        terminal shape; zero further terminal writes; NO fail issued by
        the executor; no retry; no RUNNING assertion."""
        run, child, fail_spy, complete_spy = self._running_child_with_spy()
        real_complete = complete_vendor_refresh
        complete_attempts = []

        def complete_after_competing_write(*args, **kwargs):
            complete_attempts.append(1)
            # The competing row-4 writer (test-local, real service)
            # terminalizes the child after the [A] read, before the
            # complete UPDATE runs.
            fail_vendor_refresh(child.id, VendorRefreshFailureReason.INTERNAL_ERROR)
            return real_complete(*args, **kwargs)

        factory = _CountingFactory({"response": build_success_exact_match_response()})
        with (
            patch.object(core, "fail_vendor_refresh", fail_spy),
            patch.object(core, "complete_vendor_refresh", complete_after_competing_write),
            patch.dict(os.environ, {CONFIGURED_ENV: CONFIGURED_BASE_URL}),
        ):
            returned = execute_claimed_vendor_refresh(child.id, vendor_adapter_factory=factory)
        # The actual durable state, verbatim.
        row = _row_snapshot(child.pk)
        assert returned.pk == child.pk
        assert returned.state == row["state"] == VendorRefreshState.FAILED
        assert returned.failure_reason == row["failure_reason"] == VendorRefreshFailureReason.INTERNAL_ERROR
        assert returned.result_payload is None
        # The executor's own accounting: one lookup (it reached S7),
        # exactly one complete attempt (no retry), ZERO fail calls by
        # the executor, zero further writes.
        assert len(complete_attempts) == 1
        assert len(factory.constructed[0].lookup_queries) == 1
        assert len(fail_spy.calls) == 0

    def test_t2_lost_complete_cas_absent_child_bounded_not_found(self) -> None:
        """D — the reconciliation fresh read finds the child absent:
        bounded not-found report (read-only; nothing to terminalize);
        no RUNNING assertion, no fail issued."""
        run, child, fail_spy, complete_spy = self._running_child_with_spy()
        factory = _CountingFactory({"response": build_success_exact_match_response()})

        def raise_absent_cas(*args, **kwargs):
            raise VendorRefreshCompletionError(
                child_id=str(child.id),
                detail=f"no VendorRefreshExecution with ID {child.id}",
            )

        def absent_fresh_read(target_id):
            raise VendorRefreshExecution.DoesNotExist

        with (
            patch.object(core, "fail_vendor_refresh", fail_spy),
            patch.object(core, "complete_vendor_refresh", raise_absent_cas),
            patch.object(core, "_reconciliation_fresh_read", absent_fresh_read),
            patch.dict(os.environ, {CONFIGURED_ENV: CONFIGURED_BASE_URL}),
        ):
            with pytest.raises(VendorRefreshExecutionError) as excinfo:
                execute_claimed_vendor_refresh(child.id, vendor_adapter_factory=factory)
        assert excinfo.value.reason == VendorRefreshExecutionError.REASON_STATE_NOT_FOUND
        assert len(fail_spy.calls) == 0
        assert len(factory.constructed[0].lookup_queries) == 1

    def test_t2_anomalous_pending_shape_reported_without_running_assertion(self) -> None:
        """D — the reconciliation fresh read establishes a non-terminal
        anomalous shape (PENDING): a BOUNDED state_not_running REFUSAL
        carrying the ACTUAL read-established state (FU1-F3 — strictly
        stronger than a normal return); no RUNNING assertion, no
        second terminal write, no fail, no retry, no second lookup,
        no rewrite."""
        run, child, fail_spy, complete_spy = self._running_child_with_spy()
        before = _row_snapshot(child.pk)
        factory = _CountingFactory({"response": build_success_exact_match_response()})
        anomalous_row = VendorRefreshExecution(
            state=VendorRefreshState.PENDING,
            active_slot=1,
            finished_at=None,
        )

        def raise_zero_row_cas(*args, **kwargs):
            raise VendorRefreshCompletionError(
                child_id=str(child.id),
                detail=f"child is in state {VendorRefreshState.COMPLETED}, expected RUNNING",
            )

        with (
            patch.object(core, "fail_vendor_refresh", fail_spy),
            patch.object(core, "complete_vendor_refresh", raise_zero_row_cas),
            patch.object(core, "_reconciliation_fresh_read", lambda tid: anomalous_row),
            patch.dict(os.environ, {CONFIGURED_ENV: CONFIGURED_BASE_URL}),
        ):
            with pytest.raises(VendorRefreshExecutionError) as excinfo:
                execute_claimed_vendor_refresh(child.id, vendor_adapter_factory=factory)
        # The bounded anomalous-state refusal: the ACTUAL read-
        # established state (PENDING) is carried — never a normal
        # return, never a RUNNING assertion, never a persisted reason.
        err = excinfo.value
        assert err.reason == VendorRefreshExecutionError.REASON_STATE_NOT_RUNNING
        assert err.reason in VendorRefreshExecutionError.NON_PERSISTED_REASONS
        assert err.durable_state == VendorRefreshState.PENDING
        assert err.durable_state is not VendorRefreshState.RUNNING
        # No fail issued; no second lookup after reconciliation began;
        # exactly one complete attempt (the losing one).
        assert len(fail_spy.calls) == 0
        assert len(factory.constructed[0].lookup_queries) == 1
        # The row on disk is untouched (the anomalous read was a
        # refusal, not a rewrite).
        assert _row_snapshot(child.pk) == before

    def test_t2_anomalous_running_shape_refused_with_actual_state(self) -> None:
        """D — the reconciliation fresh read establishes a non-terminal
        anomalous shape (RUNNING): a BOUNDED state_not_running refusal
        carrying the ACTUAL read-established state — the read-carried
        state is a refusal, NOT a RUNNING assertion and NOT a normal
        return; no fail, no rewrite, no second lookup (FU1-F3)."""
        run, child, fail_spy, complete_spy = self._running_child_with_spy()
        before = _row_snapshot(child.pk)
        factory = _CountingFactory({"response": build_success_exact_match_response()})
        anomalous_running = VendorRefreshExecution(
            state=VendorRefreshState.RUNNING, active_slot=1, finished_at=None
        )

        def raise_zero_row_cas(*args, **kwargs):
            raise VendorRefreshCompletionError(
                child_id=str(child.id),
                detail=f"child is in state {VendorRefreshState.COMPLETED}, expected RUNNING",
            )

        with (
            patch.object(core, "fail_vendor_refresh", fail_spy),
            patch.object(core, "complete_vendor_refresh", raise_zero_row_cas),
            patch.object(
                core, "_reconciliation_fresh_read", lambda tid: anomalous_running
            ),
            patch.dict(os.environ, {CONFIGURED_ENV: CONFIGURED_BASE_URL}),
        ):
            with pytest.raises(VendorRefreshExecutionError) as excinfo:
                execute_claimed_vendor_refresh(child.id, vendor_adapter_factory=factory)
        assert excinfo.value.reason == VendorRefreshExecutionError.REASON_STATE_NOT_RUNNING
        assert excinfo.value.reason in VendorRefreshExecutionError.NON_PERSISTED_REASONS
        assert excinfo.value.durable_state == VendorRefreshState.RUNNING  # read-carried
        assert len(fail_spy.calls) == 0
        assert len(factory.constructed[0].lookup_queries) == 1
        assert _row_snapshot(child.pk) == before

    def test_t2_fresh_read_database_error_terminalization_outcome_unknown(self) -> None:
        """D — the reconciliation fresh read itself raises a database
        error: bounded terminalization_outcome_unknown — no raw
        DatabaseError escapes as the final public outcome; no fail,
        no second complete, no second lookup (FU1-F3)."""
        run, child, fail_spy, complete_spy = self._running_child_with_spy()
        factory = _CountingFactory({"response": build_success_exact_match_response()})
        complete_attempts = []

        def raise_zero_row_cas(*args, **kwargs):
            complete_attempts.append(1)
            raise VendorRefreshCompletionError(
                child_id=str(child.id),
                detail=f"child is in state {VendorRefreshState.COMPLETED}, expected RUNNING",
            )

        def raise_read_error(tid):
            raise OperationalError("cannot establish fresh read")

        with (
            patch.object(core, "fail_vendor_refresh", fail_spy),
            patch.object(core, "complete_vendor_refresh", raise_zero_row_cas),
            patch.object(core, "_reconciliation_fresh_read", raise_read_error),
            patch.dict(os.environ, {CONFIGURED_ENV: CONFIGURED_BASE_URL}),
        ):
            with pytest.raises(VendorRefreshExecutionError) as excinfo:
                execute_claimed_vendor_refresh(child.id, vendor_adapter_factory=factory)
        # No raw DatabaseError escapes as the final public outcome.
        assert type(excinfo.value) is VendorRefreshExecutionError
        assert not isinstance(excinfo.value, OperationalError)
        assert (
            excinfo.value.reason
            == VendorRefreshExecutionError.REASON_TERMINALIZATION_OUTCOME_UNKNOWN
        )
        assert excinfo.value.durable_state is None
        assert len(fail_spy.calls) == 0
        assert len(complete_attempts) == 1  # no retry
        assert len(factory.constructed[0].lookup_queries) == 1  # no second lookup

    def test_t2b_invalid_payload_is_defect_not_cas_loser(self) -> None:
        """D — explicit reason (invalid_payload): a
        contract/programming defect, NOT a CAS loser — surfaced as that
        reason with no terminal-state report, zero row mutation, no
        fail issued."""
        run, child, fail_spy, complete_spy = self._running_child_with_spy()
        before = _row_snapshot(child.pk)
        factory = _CountingFactory({"response": build_success_exact_match_response()})
        fresh_read_calls = []

        def raise_invalid_payload(*args, **kwargs):
            raise VendorRefreshCompletionError(
                child_id=str(child.id),
                detail="payload rejected",
                reason=VendorRefreshCompletionError.REASON_INVALID_PAYLOAD,
            )

        with (
            patch.object(core, "fail_vendor_refresh", fail_spy),
            patch.object(core, "complete_vendor_refresh", raise_invalid_payload),
            patch.object(
                core,
                "_reconciliation_fresh_read",
                lambda tid: fresh_read_calls.append(1)
                or VendorRefreshExecution.objects.get(id=tid),
            ),
            patch.dict(os.environ, {CONFIGURED_ENV: CONFIGURED_BASE_URL}),
        ):
            with pytest.raises(VendorRefreshExecutionError) as excinfo:
                execute_claimed_vendor_refresh(child.id, vendor_adapter_factory=factory)
        assert (
            excinfo.value.reason
            == VendorRefreshCompletionError.REASON_INVALID_PAYLOAD
        )
        # No T2 terminal-state report: the reconciliation fresh read is
        # never used for a T2b defect.
        assert fresh_read_calls == []
        assert _row_snapshot(child.pk) == before
        assert len(fail_spy.calls) == 0

    def test_t2b_invalid_schema_version_is_defect_not_cas_loser(self) -> None:
        run, child, fail_spy, complete_spy = self._running_child_with_spy()
        before = _row_snapshot(child.pk)
        factory = _CountingFactory({"response": build_success_exact_match_response()})

        def raise_invalid_version(*args, **kwargs):
            raise VendorRefreshCompletionError(
                child_id=str(child.id),
                detail="version rejected",
                reason=VendorRefreshCompletionError.REASON_INVALID_SCHEMA_VERSION,
            )

        with (
            patch.object(core, "fail_vendor_refresh", fail_spy),
            patch.object(core, "complete_vendor_refresh", raise_invalid_version),
            patch.dict(os.environ, {CONFIGURED_ENV: CONFIGURED_BASE_URL}),
        ):
            with pytest.raises(VendorRefreshExecutionError) as excinfo:
                execute_claimed_vendor_refresh(child.id, vendor_adapter_factory=factory)
        assert (
            excinfo.value.reason
            == VendorRefreshCompletionError.REASON_INVALID_SCHEMA_VERSION
        )
        assert _row_snapshot(child.pk) == before
        assert len(fail_spy.calls) == 0

    def test_t3_definite_write_failure_terminalization_not_recorded(self) -> None:
        """D — the complete service raises a definite Django database
        error (database is locked): the reconciliation FRESH READ
        establishes RUNNING (not assumed) and reports
        terminalization_not_recorded; no fail issued; the row remains
        RUNNING (a reported HOLD)."""
        run, child, fail_spy, complete_spy = self._running_child_with_spy()
        before = _row_snapshot(child.pk)
        factory = _CountingFactory({"response": build_success_exact_match_response()})

        def raise_locked(*args, **kwargs):
            raise OperationalError("database is locked")

        with (
            patch.object(core, "fail_vendor_refresh", fail_spy),
            patch.object(core, "complete_vendor_refresh", raise_locked),
            patch.dict(os.environ, {CONFIGURED_ENV: CONFIGURED_BASE_URL}),
        ):
            with pytest.raises(VendorRefreshExecutionError) as excinfo:
                execute_claimed_vendor_refresh(child.id, vendor_adapter_factory=factory)
        assert (
            excinfo.value.reason
            == VendorRefreshExecutionError.REASON_TERMINALIZATION_NOT_RECORDED
        )
        # Established by the (real) fresh read, never assumed.
        assert excinfo.value.durable_state == VendorRefreshState.RUNNING
        row = _row_snapshot(child.pk)
        assert row["state"] == VendorRefreshState.RUNNING
        assert row == before  # zero executor writes
        assert len(fail_spy.calls) == 0
        assert len(factory.constructed[0].lookup_queries) == 1  # no second lookup

    def test_t4_fresh_read_terminal_reports_actual_durable_state(self) -> None:
        """D — ambiguous persistence error; the reconciliation fresh
        read (patched) establishes a terminal COMPLETED row: the
        completion IS durably recorded — the T2 report shape (no
        error; the actual durable state is returned); no fail."""
        run, child, fail_spy, complete_spy = self._running_child_with_spy()
        factory = _CountingFactory({"response": build_success_exact_match_response()})
        durable_completed = VendorRefreshExecution(
            state=VendorRefreshState.COMPLETED,
            active_slot=None,
            finished_at=datetime(2026, 1, 2, 3, 4, 5, tzinfo=timezone.utc),
            result_schema_version=1,
            result_payload=GOLDEN_SUCCESS_EXACT_MATCH,
        )

        def raise_ambiguous(*args, **kwargs):
            raise OperationalError("disk I/O error after statement dispatch")

        with (
            patch.object(core, "fail_vendor_refresh", fail_spy),
            patch.object(core, "complete_vendor_refresh", raise_ambiguous),
            patch.object(core, "_reconciliation_fresh_read", lambda tid: durable_completed),
            patch.dict(os.environ, {CONFIGURED_ENV: CONFIGURED_BASE_URL}),
        ):
            returned = execute_claimed_vendor_refresh(child.id, vendor_adapter_factory=factory)
        assert returned is durable_completed
        assert returned.state == VendorRefreshState.COMPLETED
        assert len(fail_spy.calls) == 0

    def test_t4_fresh_read_running_terminalization_not_recorded(self) -> None:
        """D — ambiguous persistence error; the reconciliation fresh
        read (patched) establishes RUNNING: T3 shape —
        terminalization_not_recorded; no fail, no RUNNING assertion
        (the state is read-carried, never assumed)."""
        run, child, fail_spy, complete_spy = self._running_child_with_spy()
        factory = _CountingFactory({"response": build_success_exact_match_response()})
        durable_running = VendorRefreshExecution(
            state=VendorRefreshState.RUNNING, active_slot=1, finished_at=None
        )

        def raise_ambiguous(*args, **kwargs):
            raise OperationalError("connection dropped mid-commit")

        with (
            patch.object(core, "fail_vendor_refresh", fail_spy),
            patch.object(core, "complete_vendor_refresh", raise_ambiguous),
            patch.object(core, "_reconciliation_fresh_read", lambda tid: durable_running),
            patch.dict(os.environ, {CONFIGURED_ENV: CONFIGURED_BASE_URL}),
        ):
            with pytest.raises(VendorRefreshExecutionError) as excinfo:
                execute_claimed_vendor_refresh(child.id, vendor_adapter_factory=factory)
        assert (
            excinfo.value.reason
            == VendorRefreshExecutionError.REASON_TERMINALIZATION_NOT_RECORDED
        )
        assert excinfo.value.durable_state == VendorRefreshState.RUNNING
        assert len(fail_spy.calls) == 0

    def test_t4_fresh_read_also_fails_terminalization_outcome_unknown(self) -> None:
        """D — ambiguous persistence error; the reconciliation fresh
        read ALSO fails: terminalization_outcome_unknown — zero
        writes, no fail issued, no RUNNING assertion, no second
        complete, no second lookup."""
        run, child, fail_spy, complete_spy = self._running_child_with_spy()
        factory = _CountingFactory({"response": build_success_exact_match_response()})
        complete_attempts = []

        def raise_ambiguous(*args, **kwargs):
            complete_attempts.append(1)
            raise OperationalError("connection dropped mid-commit")

        def raise_read_error(tid):
            raise OperationalError("cannot establish fresh read")

        with (
            patch.object(core, "fail_vendor_refresh", fail_spy),
            patch.object(core, "complete_vendor_refresh", raise_ambiguous),
            patch.object(core, "_reconciliation_fresh_read", raise_read_error),
            patch.dict(os.environ, {CONFIGURED_ENV: CONFIGURED_BASE_URL}),
        ):
            with pytest.raises(VendorRefreshExecutionError) as excinfo:
                execute_claimed_vendor_refresh(child.id, vendor_adapter_factory=factory)
        assert (
            excinfo.value.reason
            == VendorRefreshExecutionError.REASON_TERMINALIZATION_OUTCOME_UNKNOWN
        )
        assert excinfo.value.durable_state is None
        assert len(fail_spy.calls) == 0
        assert len(complete_attempts) == 1  # no retry
        assert len(factory.constructed[0].lookup_queries) == 1  # no second lookup

    def test_fail_path_t2_already_terminal_returns_actual_row(self) -> None:
        """D — the outer-boundary fail itself loses the CAS (the child
        is already terminal — a competing row-3 writer commits after
        the [A] read and before the fail UPDATE runs): the read-only
        reconciliation reports the ACTUAL durable state (the T2 return
        shape); exactly one fail attempt (the losing one), no second
        fail, no rewrite, no lookup (S5 pre-adapter)."""
        run, child, fail_spy, complete_spy = self._running_child_with_spy()
        factory = _CountingFactory({"response": build_success_exact_match_response()})
        real_fail = fail_vendor_refresh
        fail_attempts = []

        def fail_after_competing_write(*args, **kwargs):
            fail_attempts.append(1)
            # The competing row-3 writer (test-local, real service)
            # terminalizes the child after the [A] read, before the
            # fail UPDATE runs.
            complete_vendor_refresh(child.id, 1, _frozen_payload())
            return real_fail(*args, **kwargs)

        with (
            patch.object(core, "fail_vendor_refresh", fail_after_competing_write),
            patch.object(core, "complete_vendor_refresh", complete_spy),
            patch.dict(os.environ, {}, clear=True),  # S5 defect: config missing
        ):
            returned = execute_claimed_vendor_refresh(child.id, vendor_adapter_factory=factory)
        # The T2 report: the ACTUAL durable state, verbatim (bounded,
        # recorded; the defect's own terminalization is simply not
        # persisted — append-only, no rewrite).
        row = _row_snapshot(child.pk)
        assert returned.pk == child.pk
        assert returned.state == row["state"] == VendorRefreshState.COMPLETED
        assert row["failure_reason"] is None
        # Exactly one fail attempt by the executor (the losing one);
        # no complete through the executor's binding; S5 pre-adapter.
        assert len(fail_attempts) == 1
        assert len(complete_spy.calls) == 0
        assert factory.invocations == 0

    def test_no_fail_after_a_complete_attempt(self) -> None:
        """Across every S9 shape (T1/T2/T2b/T3/T4), the executor never
        issues a fail after the complete attempt: a successful lookup
        is never reclassified under a failed reason."""
        run, child, fail_spy, complete_spy = self._running_child_with_spy()
        factory = _CountingFactory({"response": build_success_exact_match_response()})
        with (
            patch.object(core, "fail_vendor_refresh", fail_spy),
            patch.object(core, "complete_vendor_refresh", complete_spy),
            patch.dict(os.environ, {CONFIGURED_ENV: CONFIGURED_BASE_URL}),
        ):
            execute_claimed_vendor_refresh(child.id, vendor_adapter_factory=factory)
        assert len(fail_spy.calls) == 0
        assert len(complete_spy.calls) == 1


# ---------------------------------------------------------------------------
# The outer-boundary fail's own T2b/T3/T4 (design section 5)
# ---------------------------------------------------------------------------


class TestOuterBoundaryFailOutcomes(TestCase):
    """The S4-S8 bounded fail carries the SAME T1-T4 outcome contract
    as the complete: T2 (reason=None) reports the actual durable
    state; T2b (explicit reason) is a defect, not a CAS loser; T3/T4
    are classified by the reconciliation fresh read."""

    def _config_missing_setup(self):
        run = _make_completed_run()
        child = _make_running_child(run)
        fail_spy = _spied_service(fail_vendor_refresh)
        complete_spy = _spied_service(complete_vendor_refresh)
        factory = _CountingFactory({"response": build_success_exact_match_response()})
        return run, child, fail_spy, complete_spy, factory

    def test_fail_path_t2b_reserved_reason_not_treated_as_cas_loser(self) -> None:
        run, child, fail_spy, complete_spy, factory = self._config_missing_setup()
        before = _row_snapshot(child.pk)

        def raise_reserved(*args, **kwargs):
            raise VendorRefreshFailureError(
                child_id=str(child.id),
                detail="reserved reason rejected",
                reason=VendorRefreshFailureError.REASON_RESERVED_EXECUTION_INTERRUPTED,
            )

        with (
            patch.object(core, "fail_vendor_refresh", raise_reserved),
            patch.object(core, "complete_vendor_refresh", complete_spy),
            patch.dict(os.environ, {}, clear=True),
        ):
            with pytest.raises(VendorRefreshExecutionError) as excinfo:
                execute_claimed_vendor_refresh(child.id, vendor_adapter_factory=factory)
        assert (
            excinfo.value.reason
            == VendorRefreshFailureError.REASON_RESERVED_EXECUTION_INTERRUPTED
        )
        assert _row_snapshot(child.pk) == before
        assert factory.invocations == 0

    def test_fail_path_t3_definite_write_failure(self) -> None:
        run, child, fail_spy, complete_spy, factory = self._config_missing_setup()

        def raise_locked(*args, **kwargs):
            raise OperationalError("database is locked")

        with (
            patch.object(core, "fail_vendor_refresh", raise_locked),
            patch.object(core, "complete_vendor_refresh", complete_spy),
            patch.dict(os.environ, {}, clear=True),
        ):
            with pytest.raises(VendorRefreshExecutionError) as excinfo:
                execute_claimed_vendor_refresh(child.id, vendor_adapter_factory=factory)
        assert (
            excinfo.value.reason
            == VendorRefreshExecutionError.REASON_TERMINALIZATION_NOT_RECORDED
        )
        # The (real) reconciliation fresh read establishes RUNNING.
        assert excinfo.value.durable_state == VendorRefreshState.RUNNING
        assert _row_snapshot(child.pk)["state"] == VendorRefreshState.RUNNING
        assert factory.invocations == 0

    def test_fail_path_t4_outcome_unknown(self) -> None:
        run, child, fail_spy, complete_spy, factory = self._config_missing_setup()

        def raise_ambiguous(*args, **kwargs):
            raise OperationalError("connection dropped mid-commit")

        def raise_read_error(tid):
            raise OperationalError("cannot establish fresh read")

        with (
            patch.object(core, "fail_vendor_refresh", raise_ambiguous),
            patch.object(core, "complete_vendor_refresh", complete_spy),
            patch.object(core, "_reconciliation_fresh_read", raise_read_error),
            patch.dict(os.environ, {}, clear=True),
        ):
            with pytest.raises(VendorRefreshExecutionError) as excinfo:
                execute_claimed_vendor_refresh(child.id, vendor_adapter_factory=factory)
        assert (
            excinfo.value.reason
            == VendorRefreshExecutionError.REASON_TERMINALIZATION_OUTCOME_UNKNOWN
        )
        assert factory.invocations == 0


# ---------------------------------------------------------------------------
# T3/T4 — fresh-read connection property (FU1-F2)
# ---------------------------------------------------------------------------


class TestT4FreshReadConnectionProperty(TestCase):
    """FU1-F2 — under the suite's MANAGED transaction (in-memory DB),
    the reconciliation fresh read never closes the connection (no
    blind close: the in-memory suite database would be destroyed and
    the managed transaction state aborted); the read goes through the
    wrapper's own usability gate. The actual new-connection property
    (the possibly-compromised connection demonstrably replaced) is
    proven by the file-backed subprocess nodes below, in the
    production (non-managed, autocommit, file-based) context."""

    def test_t3_definite_write_failure_confirmed_running_connection_untouched(self) -> None:
        """1 — DEFINITE write failure (error observed before any
        commit), confirmed RUNNING by the REAL fresh read:
        terminalization_not_recorded with the actually-read state; the
        managed connection is NOT closed (same DBAPI connection before
        and after); zero executor writes, no fail."""
        run = _make_completed_run()
        child = _make_running_child(run)
        before = _row_snapshot(child.pk)
        factory = _CountingFactory({"response": build_success_exact_match_response()})
        fail_spy = _spied_service(fail_vendor_refresh)

        def raise_locked(*args, **kwargs):
            raise OperationalError("database is locked")

        conn = connections["default"]
        conn.ensure_connection()
        dbapi_before = id(conn.connection)
        with (
            patch.object(core, "fail_vendor_refresh", fail_spy),
            patch.object(core, "complete_vendor_refresh", raise_locked),
            patch.dict(os.environ, {CONFIGURED_ENV: CONFIGURED_BASE_URL}),
        ):
            with pytest.raises(VendorRefreshExecutionError) as excinfo:
                execute_claimed_vendor_refresh(child.id, vendor_adapter_factory=factory)
        assert (
            excinfo.value.reason
            == VendorRefreshExecutionError.REASON_TERMINALIZATION_NOT_RECORDED
        )
        assert excinfo.value.durable_state == VendorRefreshState.RUNNING  # read-established
        # No blind close under the managed transaction.
        assert id(conn.connection) == dbapi_before
        assert _row_snapshot(child.pk) == before  # zero executor writes
        assert len(fail_spy.calls) == 0
        assert len(factory.constructed[0].lookup_queries) == 1  # no second lookup

    def test_t4_ambiguous_write_confirmed_running_managed_transaction_no_close(self) -> None:
        """2 — AMBIGUOUS write outcome under the managed in-memory
        transaction: the REAL (unpatched) fresh read independently
        confirms RUNNING through the wrapper's usability gate; the
        managed connection is NOT closed; terminalization_not_recorded
        (never assumed, never a fail)."""
        run = _make_completed_run()
        child = _make_running_child(run)
        before = _row_snapshot(child.pk)
        factory = _CountingFactory({"response": build_success_exact_match_response()})
        fail_spy = _spied_service(fail_vendor_refresh)

        def raise_ambiguous(*args, **kwargs):
            raise OperationalError("connection dropped mid-commit")

        conn = connections["default"]
        conn.ensure_connection()
        dbapi_before = id(conn.connection)
        with (
            patch.object(core, "fail_vendor_refresh", fail_spy),
            patch.object(core, "complete_vendor_refresh", raise_ambiguous),
            patch.dict(os.environ, {CONFIGURED_ENV: CONFIGURED_BASE_URL}),
        ):
            with pytest.raises(VendorRefreshExecutionError) as excinfo:
                execute_claimed_vendor_refresh(child.id, vendor_adapter_factory=factory)
        assert (
            excinfo.value.reason
            == VendorRefreshExecutionError.REASON_TERMINALIZATION_NOT_RECORDED
        )
        assert excinfo.value.durable_state == VendorRefreshState.RUNNING  # read-established
        assert id(conn.connection) == dbapi_before  # no close inside the managed txn
        assert _row_snapshot(child.pk) == before
        assert len(fail_spy.calls) == 0
        assert len(factory.constructed[0].lookup_queries) == 1  # no second lookup


# ---------------------------------------------------------------------------
# T3/T4 — file-backed connection-recovery property (FU1-F2; subprocess)
# ---------------------------------------------------------------------------

_FILE_BACKED_PROBE_SCRIPT = r'''
"""T3/T4 file-backed connection-recovery probe.

Runs in a clean subprocess over a FILE-BACKED SQLite database, OUTSIDE
any managed transaction (the production post-commit context,
autocommit). It proves the actual connection-recovery property: after
an (ambiguous/definite) terminal-CAS database error, the
reconciliation fresh read is over a NEW DBAPI connection — the
possibly-compromised one was discarded, the replacement was
demonstrated usable (lightweight statement), and the row was read
over the replacement. A patched `_reconciliation_fresh_read` returning
a canned row is not sufficient evidence by itself; this probe uses
the REAL executor and the REAL fresh read."""
import json
import os
import sys
import traceback

os.environ["DJANGO_SETTINGS_MODULE"] = "config.settings"
import django

django.setup()

from django.core.management import call_command
from django.db import OperationalError, connections

call_command("migrate", run_syncdb=True, verbosity=0)
conn = connections["default"]
assert os.path.isfile(conn.settings_dict["NAME"]), "probe requires a file-backed database"
assert conn.in_atomic_block is False, "probe requires the non-managed production context"

from product_intelligence.domain import ResearchRequest
from product_intelligence.domain.enums import ResearchRunState
from product_intelligence.providers.commercial import (
    CommercialSourceResponse,
    LookupStatus,
)
from product_intelligence.runs import (
    claim_vendor_refresh,
    complete_vendor_refresh,
    trigger_vendor_refresh,
)
from product_intelligence.runs.models import (
    PriceIntelligenceSnapshot,
    ResearchRun,
    VendorRefreshExecution,
)

import product_intelligence.execution.vendor_refresh as core
from product_intelligence.execution.vendor_refresh import (
    VendorRefreshExecutionError,
    execute_claimed_vendor_refresh,
)

MPN = "BCM957608-P2200GQF00"


def make_running_child():
    request = ResearchRequest(manufacturer_part_number=MPN, description="t4 probe")
    run = ResearchRun.objects.create_from_request(request)
    run.transition_to(ResearchRunState.RUNNING)
    run.transition_to(ResearchRunState.COMPLETED)
    PriceIntelligenceSnapshot.objects.create(
        run=run,
        schema_version=1,
        payload={
            "request": {"manufacturer_part_number": MPN, "description": "t4 probe"},
            "assessments": [],
            "buckets": [],
            "exclusions": [],
            "verification_status": "VERIFIED",
        },
    )
    return claim_vendor_refresh(
        trigger_vendor_refresh(run.id, operator="probe").id
    )


class CannedAdapter:
    def lookup(self, query):
        return CommercialSourceResponse(
            status=LookupStatus.FAILED,
            retrieved_at=None,
            candidates=(),
            issues=(),
        )


def run_scenario(name: str) -> dict:
    os.environ["PI_VENDOR_LOOKUP_BASE_URL"] = "http://vendor.internal/api"
    child = make_running_child()
    conn.ensure_connection()
    dbapi_before = id(conn.connection)
    lookups = []

    def factory():
        adapter = CannedAdapter()
        original = adapter.lookup

        def counting(query):
            lookups.append(1)
            return original(query)

        adapter.lookup = counting
        return adapter

    out = {"dbapi_before": dbapi_before}
    real_complete = core.complete_vendor_refresh
    original_get_new_connection = conn.get_new_connection

    def invoke():
        return execute_claimed_vendor_refresh(str(child.id), vendor_adapter_factory=factory)

    try:
        if name == "definite_verified_running":
            def definite_failure(*a, **k):
                raise OperationalError("database is locked")

            core.complete_vendor_refresh = definite_failure
            try:
                returned = invoke()
                out["returned_state"] = returned.state
            except VendorRefreshExecutionError as e:
                out["error"] = e.reason
                out["durable_state"] = e.durable_state
                out["row_state"] = VendorRefreshExecution.objects.get(id=child.id).state
        elif name == "ambiguous_verified_completed":
            def ambiguous_after_commit(*a, **k):
                real_complete(*a, **k)  # the write durably commits
                raise OperationalError("simulated ambiguous commit outcome")

            core.complete_vendor_refresh = ambiguous_after_commit
            try:
                returned = invoke()
                out["returned_state"] = returned.state
                out["returned_schema"] = returned.result_schema_version
                out["returned_lookup_status"] = (
                    returned.result_payload["vendor_commercial_result"]["lookup_status"]
                )
                out["row_state"] = VendorRefreshExecution.objects.get(id=child.id).state
            except VendorRefreshExecutionError as e:
                out["error"] = e.reason
                out["durable_state"] = e.durable_state
        elif name == "ambiguous_verified_running":
            def ambiguous_no_commit(*a, **k):
                raise OperationalError("simulated ambiguous commit outcome")

            core.complete_vendor_refresh = ambiguous_no_commit
            try:
                returned = invoke()
                out["returned_state"] = returned.state
            except VendorRefreshExecutionError as e:
                out["error"] = e.reason
                out["durable_state"] = e.durable_state
                out["row_state"] = VendorRefreshExecution.objects.get(id=child.id).state
        elif name == "ambiguous_reconnect_fails":
            def ambiguous_no_commit2(*a, **k):
                raise OperationalError("simulated ambiguous commit outcome")

            core.complete_vendor_refresh = ambiguous_no_commit2

            def broken_get_new_connection(conn_params):
                raise OperationalError("simulated connection replacement failure")

            conn.get_new_connection = broken_get_new_connection
            try:
                invoke()
                out["returned"] = True
            except VendorRefreshExecutionError as e:
                out["error"] = e.reason
                out["durable_state"] = e.durable_state
                out["connection_none"] = conn.connection is None
    finally:
        core.complete_vendor_refresh = real_complete
        conn.get_new_connection = original_get_new_connection
    out["dbapi_after"] = id(conn.connection)
    out["dbapi_changed"] = out["dbapi_after"] != out["dbapi_before"]
    out["lookup_count"] = len(lookups)
    return out


results = None
result_path = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "probe_result.json"
)
try:
    results = {name: run_scenario(name) for name in sys.argv[1:]}
    payload = json.dumps(results, default=str)
except Exception:
    with open(result_path, "w", encoding="utf-8") as f:
        f.write(json.dumps({"probe_error": traceback.format_exc()}))
    raise
with open(result_path, "w", encoding="utf-8") as f:
    f.write(payload)
print("PROBE_RESULT:" + payload)
'''


REPO_ROOT = Path(__file__).resolve().parents[2]


def _run_file_backed_probe() -> dict:
    """Run the T3/T4 file-backed probe in a clean subprocess (a temp
    file-backed SQLite database; the in-memory suite DB is untouched)
    and return the parsed per-scenario results.

    Spawn discipline: the child's stdin/stdout/stderr are NOT
    redirected at all — with any redirection CPython duplicates the
    child handles via ``DuplicateHandle`` (``_make_inheritable``), and
    that is the exact call site of the documented load-sensitive
    WinError 6/50 pipe-setup flake class of this Windows / Python
    3.14 workstation. The probe writes its own result file instead;
    a bounded spawn retry remains as the last-resort guard (no
    assertion changes)."""
    probe_dir = Path(tempfile.mkdtemp(prefix="vref_t4_file_backed_"))
    try:
        db_file = probe_dir / "t4_probe.sqlite3"
        script_file = probe_dir / "t4_probe.py"
        result_file = probe_dir / "probe_result.json"
        script_file.write_text(_FILE_BACKED_PROBE_SCRIPT, encoding="utf-8")
        env = dict(os.environ)
        env["PYTHONPATH"] = str(REPO_ROOT)
        env["PI_SQLITE_PATH"] = str(db_file)
        attempt = 0
        while True:
            attempt += 1
            try:
                r = subprocess.run(
                    [
                        sys.executable,
                        str(script_file),
                        "definite_verified_running",
                        "ambiguous_verified_completed",
                        "ambiguous_verified_running",
                        "ambiguous_reconnect_fails",
                    ],
                    env=env,
                    cwd=str(REPO_ROOT),
                    timeout=600,
                )
            except OSError as exc:
                # The documented load-sensitive Windows subprocess-
                # boundary flake class (WinError 6/50 in CreateProcess
                # handle setup): bounded retry of the spawn; no
                # assertion changes.
                flake = ("WinError 6" in str(exc)) or ("WinError 50" in str(exc))
                if attempt >= 3 or not flake:
                    raise
                time.sleep(0.5 * attempt)
                continue
            break
        assert result_file.exists(), "probe produced no result file"
        data = json.loads(result_file.read_text(encoding="utf-8"))
        assert "probe_error" not in data, f"probe raised:\n{data['probe_error']}"
        assert r.returncode == 0, f"probe exited with {r.returncode}"
        return data
    finally:
        shutil.rmtree(probe_dir, ignore_errors=True)


@pytest.fixture(scope="module")
def file_backed_t4_probe_results() -> dict:
    return _run_file_backed_probe()


def test_t3_file_backed_definite_write_failure_confirmed_running_new_connection(
    file_backed_t4_probe_results,
) -> None:
    """FU1-F2 (file-backed, production context) 1 — DEFINITE write
    failure; the reconciliation read is over a NEW DBAPI connection
    (the old one demonstrably discarded) and independently confirms
    RUNNING -> terminalization_not_recorded; no second Vendor call."""
    out = file_backed_t4_probe_results["definite_verified_running"]
    assert out["dbapi_changed"] is True  # actual new connection established
    assert out["error"] == "terminalization_not_recorded"
    assert out["durable_state"] == "RUNNING"  # read-established, never assumed
    assert out["row_state"] == "RUNNING"
    assert out["lookup_count"] == 1


def test_t4_file_backed_ambiguous_write_independently_verified_completed(
    file_backed_t4_probe_results,
) -> None:
    """FU1-F2 (file-backed, production context) 2 — AMBIGUOUS write
    outcome (the write durably committed, the signal was lost): the
    NEW connection's independent read verifies COMPLETED — the actual
    durable terminal result is preserved (returned, not an error);
    no Vendor call retry, no fail."""
    out = file_backed_t4_probe_results["ambiguous_verified_completed"]
    assert out["dbapi_changed"] is True  # actual new connection established
    assert "error" not in out  # the durable terminal result is returned
    assert out["returned_state"] == "COMPLETED"
    assert out["returned_schema"] == 1
    assert out["returned_lookup_status"] == "FAILED"
    assert out["row_state"] == "COMPLETED"
    assert out["lookup_count"] == 1


def test_t4_file_backed_ambiguous_write_independently_verified_running(
    file_backed_t4_probe_results,
) -> None:
    """FU1-F2 (file-backed, production context) 3 — AMBIGUOUS write
    outcome (no commit): the NEW connection's independent read
    verifies RUNNING -> terminalization_not_recorded; no fail issued;
    no Vendor call retry."""
    out = file_backed_t4_probe_results["ambiguous_verified_running"]
    assert out["dbapi_changed"] is True  # actual new connection established
    assert out["error"] == "terminalization_not_recorded"
    assert out["durable_state"] == "RUNNING"
    assert out["row_state"] == "RUNNING"
    assert out["lookup_count"] == 1


def test_t4_file_backed_ambiguous_write_reconnect_failure_outcome_unknown(
    file_backed_t4_probe_results,
) -> None:
    """FU1-F2 (file-backed, production context) 4 — AMBIGUOUS write
    outcome where the connection REPLACEMENT itself fails: bounded
    terminalization_outcome_unknown (no raw error escapes); the
    possibly-compromised connection was discarded (None held); no
    durable state assumed; no Vendor call retry."""
    out = file_backed_t4_probe_results["ambiguous_reconnect_fails"]
    assert out["error"] == "terminalization_outcome_unknown"
    assert out["durable_state"] is None
    assert out["connection_none"] is True  # the compromised connection was discarded
    assert out["lookup_count"] == 1


# ---------------------------------------------------------------------------
# Direct executor reuse (design section 12 row 20, D/M portions)
# ---------------------------------------------------------------------------


class TestDirectExecutorReuse(TestCase):
    """The documented privileged-writer limit of the LB-1 scope:
    sequential direct reuse after terminalization is machine-refused
    at the state re-assert (zero calls); the MOCKED concurrent
    interleaving (M — explicitly NOT a concurrency proof) shows two
    direct lookups with exactly one terminal write (I3)."""

    def test_direct_sequential_reuse_refused_before_lookup(self) -> None:
        """D — crash-orphan RUNNING child (real trigger + claim, no
        executor call — the W2 orphan shape). Direct call #1 completes
        (T1, lookup #1); sequential direct call #2 is refused at the
        state re-assert: ZERO factory invocations, ZERO additional
        lookups, row byte-identical."""
        run = _make_completed_run()
        child = _make_running_child(run)
        factory1 = _CountingFactory({"response": build_success_exact_match_response()})
        factory2 = _CountingFactory({"response": build_success_exact_match_response()})
        with patch.dict(os.environ, {CONFIGURED_ENV: CONFIGURED_BASE_URL}):
            returned1 = execute_claimed_vendor_refresh(child.id, vendor_adapter_factory=factory1)
        assert returned1.state == VendorRefreshState.COMPLETED
        after_first = _row_snapshot(child.pk)
        with patch.dict(os.environ, {CONFIGURED_ENV: CONFIGURED_BASE_URL}):
            with pytest.raises(VendorRefreshExecutionError) as excinfo:
                execute_claimed_vendor_refresh(child.id, vendor_adapter_factory=factory2)
        assert excinfo.value.reason == VendorRefreshExecutionError.REASON_STATE_NOT_RUNNING
        assert excinfo.value.durable_state == VendorRefreshState.COMPLETED
        # Call #2: zero construction, zero lookup.
        assert factory2.invocations == 0
        assert _row_snapshot(child.pk) == after_first
        # Total lookups across both calls: exactly one.
        total_lookups = len(factory1.constructed[0].lookup_queries)
        assert total_lookups == 1

    def test_mocked_concurrent_direct_reuse_two_lookups_one_terminal_write(self) -> None:
        """M (MOCKED interleaving — explicitly NOT a concurrency proof;
        genuine concurrent direct reuse is proven only by the R1-3 C
        nodes). Two direct executor calls over the same still-RUNNING
        orphan: the re-assert of call B is monkeypatched to the
        pre-terminalization RUNNING snapshot (B read RUNNING before A's
        terminalization committed — the interleaving a real race
        produces), so BOTH reach the lookup (2 Vendor requests
        demonstrated); the frozen complete service admits exactly ONE
        terminal write (I3): A's RETURNS (T1), B's raises the typed
        zero-row error and its pinned read-only reconciliation reports
        the ACTUAL durable COMPLETED shape (T2). The node's pinned
        limit statement: the state re-assert is NOT ownership
        authentication; the terminal CAS bounds terminal writes, NOT
        external requests; LB-1 is scoped to the authorized
        cooperating CMD execution path."""
        run = _make_completed_run()
        child = _make_running_child(run)
        pre_terminal_snapshot = _row_snapshot(child.pk)
        assert pre_terminal_snapshot["state"] == VendorRefreshState.RUNNING

        stale_running = VendorRefreshExecution.objects.get(id=child.id)
        fail_spy = _spied_service(fail_vendor_refresh)
        with patch.object(core, "fail_vendor_refresh", fail_spy):
            # Call A — the real path: lookup #1, complete wins (T1).
            factory_a = _CountingFactory({"response": build_success_exact_match_response()})
            with patch.dict(os.environ, {CONFIGURED_ENV: CONFIGURED_BASE_URL}):
                returned_a = execute_claimed_vendor_refresh(child.id, vendor_adapter_factory=factory_a)
            assert returned_a.state == VendorRefreshState.COMPLETED
            durable_row = _row_snapshot(child.pk)

            # Call B — mocked re-assert (stale RUNNING read) + REAL
            # complete service (raises the typed reason=None zero-row
            # error); its pinned read-only reconciliation fresh-reads
            # the actual durable state.
            factory_b = _CountingFactory({"response": build_success_exact_match_response()})
            with (
                patch.object(core, "_load_running_child_or_refuse", lambda tid: stale_running),
                patch.dict(os.environ, {CONFIGURED_ENV: CONFIGURED_BASE_URL}),
            ):
                returned_b = execute_claimed_vendor_refresh(child.id, vendor_adapter_factory=factory_b)
        # B's reconciliation reported the ACTUAL durable COMPLETED
        # shape; exactly one terminal write committed (I3).
        assert returned_b.state == VendorRefreshState.COMPLETED
        assert returned_b.result_payload == durable_row["result_payload"]
        assert _row_snapshot(child.pk) == durable_row

        # Two Vendor requests demonstrated; no fail issued by either
        # call; the frozen complete service admitted exactly one
        # winning terminal write (A's) — B's zero-row CAS is the
        # read-only T2 report.
        assert len(factory_a.constructed[0].lookup_queries) == 1
        assert len(factory_b.constructed[0].lookup_queries) == 1
        assert len(fail_spy.calls) == 0


# ---------------------------------------------------------------------------
# I7 — parent and all original artifacts byte-identical (design row 13/14)
# ---------------------------------------------------------------------------


class TestParentArtifactByteIdentity(TestCase):
    """The parent ResearchRun + EVERY original persisted artifact is
    byte-identical before and after the executor's success and bounded
    failure paths (I7)."""

    def test_success_path_parent_and_artifacts_byte_identical(self) -> None:
        run = _make_completed_run(with_original_supplement=True)
        child = _make_running_child(run)
        before = _parent_artifact_snapshot(run)
        factory = _CountingFactory({"response": build_success_exact_match_response()})
        with patch.dict(os.environ, {CONFIGURED_ENV: CONFIGURED_BASE_URL}):
            execute_claimed_vendor_refresh(child.id, vendor_adapter_factory=factory)
        assert _parent_artifact_snapshot(run) == before

    def test_every_bounded_failure_path_parent_and_artifacts_byte_identical(self) -> None:
        for name in (
            "binding-violation",
            "config-missing",
            "normalization-mismatch",
            "factory-failure",
            "encoding-failure",
        ):
            with self.subTest(case=name):
                run = _make_completed_run(with_original_supplement=True)
                child = _make_running_child(run)
                # Fixture-level tampering (test setup — NOT an R1
                # operation): the byte-identity frame is the state
                # AFTER setup, before the executor runs.
                if name == "binding-violation":
                    VendorRefreshExecution.objects.filter(id=child.id).update(
                        requested_mpn="TAMPERED"
                    )
                elif name == "normalization-mismatch":
                    ResearchRun.objects.filter(id=run.id).update(
                        manufacturer_part_number=f"{GOLDEN_MPN} "
                    )
                    VendorRefreshExecution.objects.filter(id=child.id).update(
                        requested_mpn=f"{GOLDEN_MPN} "
                    )
                before = _parent_artifact_snapshot(run)
                fail_spy = _spied_service(fail_vendor_refresh)
                complete_spy = _spied_service(complete_vendor_refresh)
                if name == "factory-failure":
                    factory = _CountingFactory(raise_construction=RuntimeError("boom"))
                else:
                    factory = _CountingFactory(
                        {"response": build_success_exact_match_response()}
                    )
                env = (
                    {} if name == "config-missing" else {CONFIGURED_ENV: CONFIGURED_BASE_URL}
                )
                encoder_patch = (
                    patch(
                        "product_intelligence.research.commercial_supplement_codec."
                        "encode_research_supplement_result",
                        side_effect=SupplementCodecError("codec failure"),
                    )
                    if name == "encoding-failure"
                    else nullcontext()
                )
                with (
                    patch.object(core, "fail_vendor_refresh", fail_spy),
                    patch.object(core, "complete_vendor_refresh", complete_spy),
                    patch.dict(os.environ, env, clear=True),
                    encoder_patch,
                ):
                    with pytest.raises(VendorRefreshExecutionError):
                        execute_claimed_vendor_refresh(
                            child.id, vendor_adapter_factory=factory
                        )
                assert _parent_artifact_snapshot(run) == before
                assert len(complete_spy.calls) == 0
                # The single intended fail (or its T1/T2/T3/T4 outcome)
                # — never a second terminal write by the executor.
                assert len(fail_spy.calls) == 1


# ---------------------------------------------------------------------------
# Zero FX / search / semantic / comparable / web side effects (design row 15)
# ---------------------------------------------------------------------------


def _touched_probe(*_args, **_kwargs):
    raise AssertionError("forbidden surface touched by the vendor refresh executor")


class TestZeroSideEffects(TestCase):
    """Sentinel instrumentation (design section 12 row 15, D): no FX,
    search, page-fetch, semantic, comparable, ResearchRun-execution-claim,
    or raw-HTTP surface is touched on any executor path."""

    def _sentinels(self):
        return (
            patch(
                "product_intelligence.providers.serper."
                "SerperSearchProvider.from_environment",
                side_effect=_touched_probe,
            ),
            patch(
                "product_intelligence.providers.http_page."
                "HttpPageFetcher.__init__",
                side_effect=_touched_probe,
            ),
            patch(
                "product_intelligence.providers.http_pdf."
                "HttpPdfFetcher.__init__",
                side_effect=_touched_probe,
            ),
            patch(
                "product_intelligence.providers.fx."
                "EcbFxProvider.__init__",
                side_effect=_touched_probe,
            ),
            patch(
                "product_intelligence.execution.fx_observation_cache."
                "try_reuse_latest_observation",
                side_effect=_touched_probe,
            ),
            patch(
                "product_intelligence.execution.fx_observation_cache."
                "record_live_observation",
                side_effect=_touched_probe,
            ),
            patch(
                "product_intelligence.runs.comparable_execution_claims."
                "trigger_comparable_research",
                side_effect=_touched_probe,
            ),
            patch(
                "product_intelligence.runs.comparable_execution_claims."
                "claim_comparable_research",
                side_effect=_touched_probe,
            ),
            patch(
                "product_intelligence.runs.execution_claims.claim_execution",
                side_effect=_touched_probe,
            ),
            patch(
                "product_intelligence.runs.execution_claims.complete_execution",
                side_effect=_touched_probe,
            ),
            patch(
                "product_intelligence.runs.execution_claims.retry_run",
                side_effect=_touched_probe,
            ),
            patch(
                "product_intelligence.providers.internal_vendor."
                "InternalVendorAdapter",
                side_effect=_touched_probe,
            ),
            patch(
                "product_intelligence.providers.internal_vendor."
                "_get_vendor_opener",
                side_effect=_touched_probe,
            ),
            patch("urllib.request.urlopen", side_effect=_touched_probe),
            patch("socket.create_connection", side_effect=_touched_probe),
        )

    def test_success_path_touches_no_other_surface(self) -> None:
        run = _make_completed_run()
        child = _make_running_child(run)
        sentinels = self._sentinels()
        try:
            for s in sentinels:
                s.start()
            factory = _CountingFactory({"response": build_success_exact_match_response()})
            with patch.dict(os.environ, {CONFIGURED_ENV: CONFIGURED_BASE_URL}):
                execute_claimed_vendor_refresh(child.id, vendor_adapter_factory=factory)
        finally:
            for s in sentinels:
                s.stop()
        assert _row_snapshot(child.pk)["state"] == VendorRefreshState.COMPLETED

    def test_state_refusal_touches_no_other_surface(self) -> None:
        run = _make_completed_run()
        child = _make_pending_child(run)
        sentinels = self._sentinels()
        try:
            for s in sentinels:
                s.start()
            factory = _CountingFactory({"response": build_success_exact_match_response()})
            with patch.dict(os.environ, {CONFIGURED_ENV: CONFIGURED_BASE_URL}):
                with pytest.raises(VendorRefreshExecutionError):
                    execute_claimed_vendor_refresh(child.id, vendor_adapter_factory=factory)
        finally:
            for s in sentinels:
                s.stop()
        assert factory.invocations == 0

    def test_bounded_failure_paths_touch_no_other_surface(self) -> None:
        for name in (
            "binding-violation",
            "config-missing",
            "normalization-mismatch",
            "factory-failure",
            "encoding-failure",
        ):
            with self.subTest(case=name):
                run = _make_completed_run()
                child = _make_running_child(run)
                if name == "binding-violation":
                    VendorRefreshExecution.objects.filter(id=child.id).update(
                        requested_mpn="TAMPERED"
                    )
                elif name == "normalization-mismatch":
                    ResearchRun.objects.filter(id=run.id).update(
                        manufacturer_part_number=f"{GOLDEN_MPN} "
                    )
                    VendorRefreshExecution.objects.filter(id=child.id).update(
                        requested_mpn=f"{GOLDEN_MPN} "
                    )
                sentinels = self._sentinels()
                try:
                    for s in sentinels:
                        s.start()
                    if name == "factory-failure":
                        factory = _CountingFactory(
                            raise_construction=RuntimeError("boom")
                        )
                    else:
                        factory = _CountingFactory(
                            {"response": build_success_exact_match_response()}
                        )
                    env = (
                        {}
                        if name == "config-missing"
                        else {CONFIGURED_ENV: CONFIGURED_BASE_URL}
                    )
                    encoder_patch = (
                        patch(
                            "product_intelligence.research.commercial_supplement_codec."
                            "encode_research_supplement_result",
                            side_effect=SupplementCodecError("codec failure"),
                        )
                        if name == "encoding-failure"
                        else nullcontext()
                    )
                    with (
                        patch.dict(os.environ, env, clear=True),
                        encoder_patch,
                    ):
                        with pytest.raises(VendorRefreshExecutionError):
                            execute_claimed_vendor_refresh(
                                child.id, vendor_adapter_factory=factory
                            )
                finally:
                    for s in sentinels:
                        s.stop()


# ---------------------------------------------------------------------------
# R0 latent codec-defect regression (disclosed at VREF-R1-1)
# ---------------------------------------------------------------------------


class TestR0LatentCodecDefectRegression(TestCase):
    """Regression for the disclosed R0 latent defect (VREF-R1-1 commit
    record): the ORIGINAL 4D-B orchestration lookup path carried an
    inline ``except SupplementCodecError`` clause that referenced the
    name without importing it, so a genuine codec failure surfaced as
    ``NameError`` (context=SupplementCodecError) instead of the codec
    error. Over the post-extraction path (the original 4D-B orchestration
    lookup path delegating to the R1-1 D10 helper), a REAL
    SupplementCodecError must propagate as that exception — not
    NameError — without exposing raw Vendor text. The frozen run-level
    contract (``test_codec_error_fails_run``) is unchanged."""

    def test_real_supplement_codec_error_propagates_not_name_error(self) -> None:
        import product_intelligence.execution.orchestration as orch
        from product_intelligence.providers import internal_vendor as iv_mod

        raw_marker = "RAW_VENDOR_TEXT_MARKER"
        response = CommercialSourceResponse(
            status=LookupStatus.SUCCESS,
            retrieved_at=RETRIEVED_AT,
            candidates=(
                CommercialSourceCandidate(
                    source_name=f"src-{raw_marker}",
                    explicit_candidate_mpn=GOLDEN_MPN,
                    price_amount=Decimal("2120.00"),
                    currency_code="USD",
                    availability=CommercialAvailability.IN_STOCK,
                    price_basis=CommercialPriceBasis.CUSTOMER_PRICE,
                ),
            ),
            issues=(),
        )

        class _CannedAdapter:
            constructions = 0

            def __init__(self):
                type(self).constructions += 1

            def lookup(self, query):
                return response

        request = ResearchRequest(
            manufacturer_part_number=GOLDEN_MPN,
            description="R0 latent codec-defect regression",
        )
        with (
            patch.object(iv_mod, "InternalVendorAdapter", _CannedAdapter),
            patch.dict(os.environ, {CONFIGURED_ENV: CONFIGURED_BASE_URL}),
            patch(
                "product_intelligence.research.commercial_supplement_codec."
                "encode_research_supplement_result",
                side_effect=SupplementCodecError("codec failure"),
            ),
        ):
            with pytest.raises(SupplementCodecError) as excinfo:
                orch._try_vendor_commercial_lookup(None, request)
        # The exception IS the real codec error (the latent defect
        # surfaced NameError instead — a NameError is not a
        # SupplementCodecError, so this pins the correction).
        assert type(excinfo.value) is SupplementCodecError
        assert not isinstance(excinfo.value, NameError)
        # No raw Vendor text is exposed in the propagated error.
        assert raw_marker not in str(excinfo.value)
        assert _CannedAdapter.constructions == 1
