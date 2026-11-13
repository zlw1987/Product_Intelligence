"""VREF-R1-3 — the normal vendor-refresh command (design sections
3.3 / 3.4 / 5 / 8.3 / 10.2 / 11 row 1 Stage A / 12 rows 1, 10, 11,
16, 19).

The command ``runs/management/commands/vendor_refresh.py`` is the ONLY
claim call site in R1: inside one serialized short write transaction
(the M4 A3 zero-row lock statement + fresh active-children snapshot +
cooldown decision + trigger INSERT + claim UPDATE) it commits a
durably RUNNING child BEFORE any network activity (I10), and the same
invocation then calls the public execution entry exactly once (M3
Option A: only the invocation that creates the child may claim and
execute it).

Class discipline (design section 12 legend): the nodes in THIS file
are D — deterministic sequential invocations over the in-memory suite
database with pinned clocks, counting fakes, and ORM spies. The C
class (GENUINE independent-connection / process concurrency against a
FILE-based SQLite) lives in ``test_vendor_refresh_concurrency.py``
(next to this file) and is the only concurrency proof of this phase.

Stage A (design section 11 row 1) — the R0 absence pin
``TestNoRecoverySurface::test_no_vendor_refresh_management_command_
exists`` in ``test_vendor_refresh_claims.py`` evolved IN PLACE at this
gate (node ID preserved) into the exact command-surface pin; the
parser-error / ineligibility / exit-code nodes below are the NEW
Stage A regression coverage authorized by that evolution row.

No recovery surface exists at R1-3 (R1-4 BLOCKED pending O8): no
recovery command, no recovery flag, no reserved-reason writer.
"""

from __future__ import annotations

import ast
import uuid
from datetime import datetime, timedelta, timezone as dt_timezone
from decimal import Decimal
from io import StringIO
from pathlib import Path
from unittest.mock import patch

import pytest
from django.core.management import call_command, get_commands
from django.core.management.base import CommandError
from django.db import OperationalError
from django.test import TestCase
from django.test.utils import CaptureQueriesContext
from django.db import connections

from product_intelligence.domain import ResearchRequest
from product_intelligence.domain.enums import ResearchRunState
from product_intelligence.providers.commercial import (
    CommercialSourceResponse,
    LookupStatus,
)
from product_intelligence.runs import (
    VendorRefreshClaimError,
    claim_vendor_refresh,
    complete_vendor_refresh,
    trigger_vendor_refresh,
)
from product_intelligence.runs.errors import VendorRefreshTriggerError
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
    VendorRefreshTriggerSource,
)

import product_intelligence.execution.vendor_refresh as core
from product_intelligence.execution.vendor_refresh import (
    VendorRefreshExecutionError,
    execute_claimed_vendor_refresh,
)
import product_intelligence.runs.management.commands.vendor_refresh as command_module

from tests.execution.test_vendor_commercial_binding import (
    build_success_exact_match_response,
    build_transport_failed_no_retrieved_at_response,
)

# The canned response binds EXACT against this MPN (the golden 4D-B
# input of record).
TEST_MPN = "BCM957608-P2200GQF00"
TEST_DESCRIPTION = "Enterprise SSD"
CONFIGURED_ENV = "PI_VENDOR_LOOKUP_BASE_URL"
CONFIGURED_BASE_URL = "http://vendor.internal/secret-api"

FORBIDDEN_SURFACE_FLAGS = (
    "--retry",
    "--recover",
    "--recovery",
    "--force",
    "--stale",
    "--reassign",
    "--resurrect",
    "--interrupt",
    "--reset",
    "--reclaim",
    "--evidence",
    "--attest-host-inventory",
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_completed_run(
    mpn: str = TEST_MPN, description: str = TEST_DESCRIPTION
) -> ResearchRun:
    request = ResearchRequest(manufacturer_part_number=mpn, description=description)
    run = ResearchRun.objects.create_from_request(request)
    run.transition_to(ResearchRunState.RUNNING)
    run.transition_to(ResearchRunState.COMPLETED)
    PriceIntelligenceSnapshot.objects.create(
        run=run,
        schema_version=1,
        payload={
            "request": {"manufacturer_part_number": mpn, "description": description},
            "assessments": [],
            "buckets": [],
            "exclusions": [],
            "verification_status": "VERIFIED",
        },
    )
    return run


def _make_pending_child(run: ResearchRun, operator: str = "op-a") -> VendorRefreshExecution:
    """A NON-COMMAND trigger (the orphan-PENDING shape, M3)."""
    return trigger_vendor_refresh(run.id, operator=operator)


def _make_running_child(run: ResearchRun, operator: str = "op-a") -> VendorRefreshExecution:
    return claim_vendor_refresh(_make_pending_child(run, operator).id)


def _make_terminal_child(
    run: ResearchRun,
    operator: str = "op-a",
    *,
    finished_at: datetime | None = None,
    complete: bool = True,
) -> VendorRefreshExecution:
    child = _make_running_child(run, operator)
    if complete:
        return complete_vendor_refresh(
            child.id, 1, _frozen_payload(), at=finished_at
        )
    return child


def _frozen_payload() -> dict:
    from product_intelligence.research.commercial_supplement_codec import (
        ResearchSupplementResult,
        VendorCommercialResult,
        encode_research_supplement_result,
    )

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


def _row_snapshot(pk) -> dict:
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
    """The parent ResearchRun + every original persisted artifact
    (I7 byte-identity frame)."""
    fresh = ResearchRun.objects.get(pk=run.pk)
    snapshot = {
        "run_state": fresh.state,
        "run_mpn": fresh.manufacturer_part_number,
        "run_description": fresh.description,
        "run_created_at": fresh.created_at,
        "run_started_at": fresh.started_at,
        "run_finished_at": fresh.finished_at,
        "price_snapshot_count": PriceIntelligenceSnapshot.objects.filter(run=fresh).count(),
        "supplement_snapshot_count": ResearchSupplementSnapshot.objects.filter(run=fresh).count(),
        "fx_snapshot_count": ResearchFxSnapshot.objects.filter(run=fresh).count(),
        "micron_alias_count": ResearchMicronAliasSnapshot.objects.filter(run=fresh).count(),
        "evidence_count": ExecutionEvidenceRecord.objects.filter(run=fresh).count(),
        "review_candidate_count": AiAssistedReviewCandidate.objects.filter(run=fresh).count(),
        "comparable_count": ComparableResearchExecution.objects.filter(parent_run=fresh).count(),
    }
    price = PriceIntelligenceSnapshot.objects.filter(run=fresh).first()
    if price is not None:
        snapshot["price_schema_version"] = price.schema_version
        snapshot["price_payload"] = price.payload
        snapshot["price_created_at"] = price.created_at
    return snapshot


class _FakeVendorAdapter:
    """Canned-response adapter; records lookup() calls."""

    def __init__(self, response: CommercialSourceResponse | None) -> None:
        self.response = response
        self.lookup_queries: list = []

    def lookup(self, query):
        self.lookup_queries.append(query)
        return self.response


class _CountingFactory:
    """Zero-arg counting factory (design section 3.2 sentinel
    discipline)."""

    def __init__(self, response: CommercialSourceResponse | None) -> None:
        self.response = response
        self.invocations = 0
        self.constructed: list[_FakeVendorAdapter] = []

    def __call__(self) -> _FakeVendorAdapter:
        self.invocations += 1
        adapter = _FakeVendorAdapter(self.response)
        self.constructed.append(adapter)
        return adapter

    @property
    def lookup_count(self) -> int:
        return sum(len(a.lookup_queries) for a in self.constructed)


def _fake_runtime_entry(factory: _CountingFactory):
    """The command-stack execution entry over a counting factory
    (the runtime's delegation, with the concrete adapter replaced by
    the test double — the flow itself is NOT patched)."""

    def entry(child_id):
        return execute_claimed_vendor_refresh(
            child_id, vendor_adapter_factory=factory
        )

    return entry


def _spied_service(real):
    calls: list = []

    def spy(*args, **kwargs):
        calls.append((args, kwargs))
        return real(*args, **kwargs)

    spy.calls = calls
    return spy


def _invoke(*args) -> tuple:
    """Run the real command class via call_command; return
    (exit_code, stdout_text). Parser errors raise CommandError."""
    out = StringIO()
    try:
        call_command("vendor_refresh", *args, stdout=out)
        code = None
    except SystemExit as exc:
        code = exc.code
    return code, out.getvalue()


def _outcome_lines(text: str) -> list[str]:
    return [line for line in text.splitlines() if "outcome: " in line]


# ---------------------------------------------------------------------------
# Stage A — parser surface + [S0] ineligibility (zero DB statements)
# ---------------------------------------------------------------------------


class TestParserSurfaceAndS0(TestCase):
    """The R1-3 Stage A new nodes (design section 11 row 1): parser
    errors and [S0] refusals with ZERO database statements."""

    def test_missing_operator_is_a_parser_error_with_zero_db_statements(self) -> None:
        run = _make_completed_run()
        with CaptureQueriesContext(connections["default"]) as ctx:
            with pytest.raises(CommandError):
                call_command("vendor_refresh", str(run.id), stdout=StringIO())
        assert len(ctx.captured_queries) == 0
        assert VendorRefreshExecution.objects.filter(parent_run=run).count() == 0

    def test_forbidden_surface_flags_are_parser_errors_with_zero_db_statements(
        self
    ) -> None:
        run = _make_completed_run()
        for flag in FORBIDDEN_SURFACE_FLAGS:
            with CaptureQueriesContext(connections["default"]) as ctx:
                with pytest.raises(CommandError):
                    call_command(
                        "vendor_refresh", str(run.id), "--operator", "op-a", flag,
                        stdout=StringIO(),
                    )
            assert len(ctx.captured_queries) == 0, f"{flag} touched the database"
        assert VendorRefreshExecution.objects.filter(parent_run=run).count() == 0

    def test_unknown_flag_is_a_parser_error_with_zero_db_statements(self) -> None:
        run = _make_completed_run()
        with CaptureQueriesContext(connections["default"]) as ctx:
            with pytest.raises(CommandError):
                call_command(
                    "vendor_refresh", str(run.id), "--operator", "op-a",
                    "--bogus", stdout=StringIO(),
                )
        assert len(ctx.captured_queries) == 0
        assert VendorRefreshExecution.objects.filter(parent_run=run).count() == 0

    def test_child_id_positional_is_rejected_with_zero_db_statements(self) -> None:
        run = _make_completed_run()
        with CaptureQueriesContext(connections["default"]) as ctx:
            with pytest.raises(CommandError):
                call_command(
                    "vendor_refresh", str(run.id), str(uuid.uuid4()),
                    "--operator", "op-a", stdout=StringIO(),
                )
        assert len(ctx.captured_queries) == 0
        assert VendorRefreshExecution.objects.filter(parent_run=run).count() == 0

    def test_invalid_parent_run_uuid_is_ineligible_with_zero_db_statements(self) -> None:
        marker = "ZZZNOTAUUIDMARKER"
        with CaptureQueriesContext(connections["default"]) as ctx:
            code, text = _invoke(f"{marker}-not-a-uuid", "--operator", "op-a")
        assert code == 2
        assert "outcome: INELIGIBLE reason=invalid_parent_run_uuid" in text
        # The untrusted input is never reflected in the output.
        assert marker not in text
        assert len(ctx.captured_queries) == 0

    def test_over_long_operator_is_ineligible_with_zero_db_statements(self) -> None:
        run = _make_completed_run()
        with CaptureQueriesContext(connections["default"]) as ctx:
            code, text = _invoke(str(run.id), "--operator", "x" * 129)
        assert code == 2
        assert "outcome: INELIGIBLE reason=invalid_operator" in text
        assert len(ctx.captured_queries) == 0
        assert VendorRefreshExecution.objects.filter(parent_run=run).count() == 0

    def test_empty_operator_is_ineligible_with_zero_db_statements(self) -> None:
        run = _make_completed_run()
        with CaptureQueriesContext(connections["default"]) as ctx:
            code, text = _invoke(str(run.id), "--operator", "")
        assert code == 2
        assert "outcome: INELIGIBLE reason=invalid_operator" in text
        assert len(ctx.captured_queries) == 0
        assert VendorRefreshExecution.objects.filter(parent_run=run).count() == 0

    def test_missing_parent_is_ineligible_with_zero_children_and_zero_calls(self) -> None:
        factory = _CountingFactory(build_success_exact_match_response())
        trigger_spy = _spied_service(trigger_vendor_refresh)
        claim_spy = _spied_service(claim_vendor_refresh)
        with (
            patch.dict(os_environ(), {CONFIGURED_ENV: CONFIGURED_BASE_URL}),
            patch.object(command_module, "trigger_vendor_refresh", trigger_spy),
            patch.object(command_module, "claim_vendor_refresh", claim_spy),
            patch.object(
                command_module,
                "execute_claimed_vendor_refresh_with_default_providers",
                _recording_stub(),
            ),
        ):
            code, text = _invoke(str(uuid.uuid4()), "--operator", "op-a")
        assert code == 2
        assert "outcome: INELIGIBLE reason=parent_not_found" in text
        assert len(claim_spy.calls) == 0
        assert factory.invocations == 0
        assert factory.lookup_count == 0
        assert VendorRefreshExecution.objects.count() == 0


def os_environ() -> dict:
    import os

    return os.environ


def _recording_stub():
    calls = []

    def stub(child_id):
        calls.append(child_id)

    stub.calls = calls
    return stub


# ---------------------------------------------------------------------------
# Row 1 — end-to-end success (D)
# ---------------------------------------------------------------------------


class TestEndToEndSuccess(TestCase):
    """One complete successful command invocation over the real
    command class: exactly one trigger INSERT, one claim UPDATE, one
    factory invocation, one lookup, one complete UPDATE; the parent +
    all original artifacts byte-identical (I7); bounded stdout; exit 0."""

    def _success_invocation(self, **kwargs):
        run = _make_completed_run()
        artifacts_before = _parent_artifact_snapshot(run)
        row_before_absent = VendorRefreshExecution.objects.filter(parent_run=run).count()
        assert row_before_absent == 0
        factory = _CountingFactory(build_success_exact_match_response())
        trigger_spy = _spied_service(trigger_vendor_refresh)
        claim_spy = _spied_service(claim_vendor_refresh)
        complete_spy = _spied_service(complete_vendor_refresh)
        fail_spy = _spied_service(core.fail_vendor_refresh)
        with (
            patch.dict(os_environ(), {CONFIGURED_ENV: CONFIGURED_BASE_URL}),
            patch.object(command_module, "trigger_vendor_refresh", trigger_spy),
            patch.object(command_module, "claim_vendor_refresh", claim_spy),
            patch.object(core, "complete_vendor_refresh", complete_spy),
            patch.object(core, "fail_vendor_refresh", fail_spy),
            patch.object(
                command_module,
                "execute_claimed_vendor_refresh_with_default_providers",
                _fake_runtime_entry(factory),
            ),
        ):
            code, text = _invoke(
                str(run.id), "--operator", kwargs.get("operator", "op-a")
            )
        child = VendorRefreshExecution.objects.get(parent_run=run)
        return {
            "run": run,
            "child": child,
            "code": code,
            "text": text,
            "factory": factory,
            "trigger_spy": trigger_spy,
            "claim_spy": claim_spy,
            "complete_spy": complete_spy,
            "fail_spy": fail_spy,
            "artifacts_before": artifacts_before,
        }

    def test_successful_invocation_counts_are_each_exactly_one(self) -> None:
        out = self._success_invocation()
        assert out["code"] == 0
        assert len(out["trigger_spy"].calls) == 1
        assert len(out["claim_spy"].calls) == 1  # no second claim on any re-entry
        assert out["factory"].invocations == 1
        assert out["factory"].lookup_count == 1
        assert len(out["complete_spy"].calls) == 1
        assert len(out["fail_spy"].calls) == 0

    def test_successful_invocation_row_shape_and_payload(self) -> None:
        out = self._success_invocation()
        child = out["child"]
        assert child.state == VendorRefreshState.COMPLETED
        assert child.active_slot is None
        assert child.started_at is not None
        assert child.finished_at is not None
        assert child.result_schema_version == 1
        assert child.requested_mpn == TEST_MPN
        payload = child.result_payload
        assert payload["vendor_commercial_result"]["lookup_status"] == "SUCCESS"
        observations = payload["vendor_commercial_result"]["observations"]
        assert len(observations) == 1
        assert observations[0]["vendor_mpn_match_type"] == "EXACT"
        assert observations[0]["brand_new"] is True
        assert observations[0]["brand_new_basis"] == "VENDOR_API_POLICY"

    def test_successful_invocation_parent_and_artifacts_byte_identical(self) -> None:
        out = self._success_invocation()
        assert _parent_artifact_snapshot(out["run"]) == out["artifacts_before"]

    def test_successful_invocation_stdout_bounded_order(self) -> None:
        out = self._success_invocation()
        lines = out["text"].splitlines()
        assert all(line.startswith("vendor refresh: ") for line in lines)
        child = out["child"]
        assert f"vendor refresh: parent-run {child.parent_run_id}" in lines
        assert "vendor refresh: no-prior-child" in lines
        assert (
            f"vendor refresh: child-created {child.id} operator=op-a "
            f"trigger-source={VendorRefreshTriggerSource.MANAGEMENT_COMMAND}"
        ) in lines
        assert (
            f"vendor refresh: outcome: COMPLETED lookup-status=SUCCESS "
            f"retrieved-at={payload_retrieved_at(child)}"
        ) in lines
        # CREATED_EXECUTED (the child-created line) precedes the outcome.
        assert lines.index(
            f"vendor refresh: child-created {child.id} operator=op-a "
            f"trigger-source={VendorRefreshTriggerSource.MANAGEMENT_COMMAND}"
        ) < lines.index(
            f"vendor refresh: outcome: COMPLETED lookup-status=SUCCESS "
            f"retrieved-at={payload_retrieved_at(child)}"
        )
        assert len(_outcome_lines(out["text"])) == 1

    def test_successful_invocation_records_verbatim_operator(self) -> None:
        operator = "op-verbatim-7"
        out = self._success_invocation(operator=operator)
        child = out["child"]
        assert child.operator == operator  # recorded verbatim (I6)
        assert child.trigger_source == VendorRefreshTriggerSource.MANAGEMENT_COMMAND
        # The SAME invocation was the executor: its counting factory
        # (owned by this process) was the one constructed.
        assert out["factory"].invocations == 1

    def test_stdout_carries_no_base_url_or_vendor_content(self) -> None:
        out = self._success_invocation()
        text = out["text"]
        assert "secret-api" not in text
        assert CONFIGURED_BASE_URL not in text
        # Raw private Vendor response content (price, source name) must
        # not appear; only bounded vocabulary values do.
        assert "2120.00" not in text
        assert "Ingram" not in text
        assert "lookup-status=SUCCESS" in text

    def test_transport_failed_response_is_a_completed_result(self) -> None:
        """An executed lookup with a FAILED transport result is a
        COMPLETED payload (the 4D-B semantics), NOT a FAILED child."""
        run = _make_completed_run()
        factory = _CountingFactory(build_transport_failed_no_retrieved_at_response())
        with (
            patch.dict(os_environ(), {CONFIGURED_ENV: CONFIGURED_BASE_URL}),
            patch.object(
                command_module,
                "execute_claimed_vendor_refresh_with_default_providers",
                _fake_runtime_entry(factory),
            ),
        ):
            code, text = _invoke(str(run.id), "--operator", "op-a")
        assert code == 0
        child = VendorRefreshExecution.objects.get(parent_run=run)
        assert child.state == VendorRefreshState.COMPLETED
        assert child.result_payload["vendor_commercial_result"]["lookup_status"] == "FAILED"
        assert child.result_payload["vendor_commercial_result"]["retrieved_at"] is None
        assert "outcome: COMPLETED lookup-status=FAILED retrieved-at=-" in text
        assert factory.invocations == 1
        assert factory.lookup_count == 1


def payload_retrieved_at(child: VendorRefreshExecution) -> str:
    value = child.result_payload["vendor_commercial_result"]["retrieved_at"]
    if value is None:
        return "-"
    return value


# ---------------------------------------------------------------------------
# Row 10 — M3 Option A: existing PENDING never silently executed
# ---------------------------------------------------------------------------


class TestOptionAExistingChildren(TestCase):
    """A pre-existing active child (created by a NON-COMMAND surface)
    is reported (id, state, recorded operator, created_at/started_at)
    and left untouched: no claim, no executor call, zero network. The
    orphan PENDING is additionally machine-refused by the executor."""

    def test_preexisting_pending_child_is_reported_and_untouched(self) -> None:
        run = _make_completed_run()
        orphan = _make_pending_child(run, operator="op-programmatic")
        before = _row_snapshot(orphan.pk)
        factory = _CountingFactory(build_success_exact_match_response())
        claim_spy = _spied_service(claim_vendor_refresh)
        trigger_spy = _spied_service(trigger_vendor_refresh)
        with (
            patch.dict(os_environ(), {CONFIGURED_ENV: CONFIGURED_BASE_URL}),
            patch.object(command_module, "trigger_vendor_refresh", trigger_spy),
            patch.object(command_module, "claim_vendor_refresh", claim_spy),
            patch.object(
                command_module,
                "execute_claimed_vendor_refresh_with_default_providers",
                _fake_runtime_entry(factory),
            ),
        ):
            code, text = _invoke(str(run.id), "--operator", "op-a")
        assert code == 0
        assert "outcome: IN_PROGRESS" in text
        assert f"vendor refresh: active-child {orphan.id}" in text
        assert f"state={VendorRefreshState.PENDING}" in text
        assert "operator=op-programmatic" in text
        # Left untouched, byte-identical.
        assert _row_snapshot(orphan.pk) == before
        assert VendorRefreshExecution.objects.filter(parent_run=run).count() == 1
        assert len(claim_spy.calls) == 0
        assert len(trigger_spy.calls) == 0
        assert factory.invocations == 0
        assert factory.lookup_count == 0

    def test_preexisting_running_child_is_reported_in_progress(self) -> None:
        run = _make_completed_run()
        orphan = _make_running_child(run, operator="op-programmatic")
        before = _row_snapshot(orphan.pk)
        factory = _CountingFactory(build_success_exact_match_response())
        with (
            patch.dict(os_environ(), {CONFIGURED_ENV: CONFIGURED_BASE_URL}),
            patch.object(
                command_module,
                "execute_claimed_vendor_refresh_with_default_providers",
                _fake_runtime_entry(factory),
            ),
        ):
            code, text = _invoke(str(run.id), "--operator", "op-a")
        assert code == 0
        assert "outcome: IN_PROGRESS" in text
        assert f"vendor refresh: active-child {orphan.id}" in text
        assert _row_snapshot(orphan.pk) == before
        assert factory.invocations == 0
        assert factory.lookup_count == 0

    def test_direct_executor_on_orphan_pending_is_machine_refused(self) -> None:
        """The machine guard behind the procedural rule (M3): even a
        DIRECT executor call on the orphan PENDING row is refused with
        zero construction, zero lookup, and a byte-identical row."""
        run = _make_completed_run()
        orphan = _make_pending_child(run, operator="op-programmatic")
        before = _row_snapshot(orphan.pk)
        factory = _CountingFactory(build_success_exact_match_response())
        fail_spy = _spied_service(core.fail_vendor_refresh)
        with (
            patch.dict(os_environ(), {CONFIGURED_ENV: CONFIGURED_BASE_URL}),
            patch.object(core, "fail_vendor_refresh", fail_spy),
        ):
            with pytest.raises(VendorRefreshExecutionError) as excinfo:
                execute_claimed_vendor_refresh(
                    orphan.id, vendor_adapter_factory=factory
                )
        assert excinfo.value.reason == VendorRefreshExecutionError.REASON_STATE_NOT_RUNNING
        assert len(fail_spy.calls) == 0
        assert factory.invocations == 0
        assert factory.lookup_count == 0
        assert _row_snapshot(orphan.pk) == before


# ---------------------------------------------------------------------------
# Row 11 — the five-minute repeat safeguard (pinned clock)
# ---------------------------------------------------------------------------


class TestCooldownSafeguard(TestCase):
    """The safeguard runs BEFORE a new child is persisted and BEFORE
    any Vendor call; a refusal creates zero children and makes zero
    network calls; STRICT ``< 300 s`` against the latest terminal
    child's ``finished_at`` (max, tie-break id DESC); --force-repeat
    bypasses the cooldown refusal ONLY."""

    FIXED = datetime(2026, 6, 1, 12, 0, 0, tzinfo=dt_timezone.utc)

    def _terminal_child_at(self, run, age_seconds: float, operator="op-t"):
        finished_at = self.FIXED - timedelta(seconds=age_seconds)
        return _make_terminal_child(run, operator=operator, finished_at=finished_at)

    def test_refusal_within_cooldown_makes_zero_children_claims_lookups(self) -> None:
        run = _make_completed_run()
        blocker = self._terminal_child_at(run, 299.9)
        factory = _CountingFactory(build_success_exact_match_response())
        claim_spy = _spied_service(claim_vendor_refresh)
        trigger_spy = _spied_service(trigger_vendor_refresh)
        with (
            patch("django.utils.timezone.now", lambda: self.FIXED),
            patch.dict(os_environ(), {CONFIGURED_ENV: CONFIGURED_BASE_URL}),
            patch.object(command_module, "trigger_vendor_refresh", trigger_spy),
            patch.object(command_module, "claim_vendor_refresh", claim_spy),
            patch.object(
                command_module,
                "execute_claimed_vendor_refresh_with_default_providers",
                _fake_runtime_entry(factory),
            ),
        ):
            code, text = _invoke(str(run.id), "--operator", "op-a")
        assert code == 0
        assert "outcome: COOLDOWN_REFUSAL" in text
        # The refusal stdout carries the blocking child id + finished_at + age.
        assert f"vendor refresh: blocking-child {blocker.id}" in text
        assert f"finished-at={blocker.finished_at.isoformat()}" in text
        assert "age-seconds=299" in text
        assert VendorRefreshExecution.objects.filter(parent_run=run).count() == 1
        assert len(trigger_spy.calls) == 0
        assert len(claim_spy.calls) == 0
        assert factory.invocations == 0
        assert factory.lookup_count == 0

    def test_allowed_outside_cooldown_creates_a_new_child(self) -> None:
        run = _make_completed_run()
        self._terminal_child_at(run, 300.1)
        factory = _CountingFactory(build_success_exact_match_response())
        with (
            patch("django.utils.timezone.now", lambda: self.FIXED),
            patch.dict(os_environ(), {CONFIGURED_ENV: CONFIGURED_BASE_URL}),
            patch.object(
                command_module,
                "execute_claimed_vendor_refresh_with_default_providers",
                _fake_runtime_entry(factory),
            ),
        ):
            code, text = _invoke(str(run.id), "--operator", "op-a")
        assert code == 0
        assert "outcome: COMPLETED" in text
        assert VendorRefreshExecution.objects.filter(parent_run=run).count() == 2
        assert factory.invocations == 1

    def test_boundary_is_strictly_less_than_300s(self) -> None:
        """Age EXACTLY 300.0 s is allowed (the refusal is STRICT
        ``< 300 s``; O7)."""
        run = _make_completed_run()
        self._terminal_child_at(run, 300.0)
        factory = _CountingFactory(build_success_exact_match_response())
        with (
            patch("django.utils.timezone.now", lambda: self.FIXED),
            patch.dict(os_environ(), {CONFIGURED_ENV: CONFIGURED_BASE_URL}),
            patch.object(
                command_module,
                "execute_claimed_vendor_refresh_with_default_providers",
                _fake_runtime_entry(factory),
            ),
        ):
            code, text = _invoke(str(run.id), "--operator", "op-a")
        assert code == 0
        assert "outcome: COMPLETED" in text
        assert VendorRefreshExecution.objects.filter(parent_run=run).count() == 2

    def test_force_repeat_bypasses_cooldown(self) -> None:
        run = _make_completed_run()
        self._terminal_child_at(run, 299.9)
        factory = _CountingFactory(build_success_exact_match_response())
        with (
            patch("django.utils.timezone.now", lambda: self.FIXED),
            patch.dict(os_environ(), {CONFIGURED_ENV: CONFIGURED_BASE_URL}),
            patch.object(
                command_module,
                "execute_claimed_vendor_refresh_with_default_providers",
                _fake_runtime_entry(factory),
            ),
        ):
            code, text = _invoke(str(run.id), "--operator", "op-a", "--force-repeat")
        assert code == 0
        assert "outcome: COMPLETED" in text
        assert VendorRefreshExecution.objects.filter(parent_run=run).count() == 2
        assert factory.invocations == 1

    def test_force_repeat_does_not_bypass_in_progress(self) -> None:
        run = _make_completed_run()
        orphan = _make_pending_child(run, operator="op-programmatic")
        before = _row_snapshot(orphan.pk)
        factory = _CountingFactory(build_success_exact_match_response())
        claim_spy = _spied_service(claim_vendor_refresh)
        with (
            patch.dict(os_environ(), {CONFIGURED_ENV: CONFIGURED_BASE_URL}),
            patch.object(command_module, "claim_vendor_refresh", claim_spy),
            patch.object(
                command_module,
                "execute_claimed_vendor_refresh_with_default_providers",
                _fake_runtime_entry(factory),
            ),
        ):
            code, text = _invoke(str(run.id), "--operator", "op-a", "--force-repeat")
        assert code == 0
        assert "outcome: IN_PROGRESS" in text
        assert len(claim_spy.calls) == 0
        assert factory.invocations == 0
        assert factory.lookup_count == 0
        assert _row_snapshot(orphan.pk) == before

    def test_tie_break_prefers_the_larger_id_at_identical_finished_at(self) -> None:
        run = _make_completed_run()
        first = self._terminal_child_at(run, 10.0, operator="op-t1")
        second = self._terminal_child_at(run, 10.0, operator="op-t2")
        assert first.finished_at == second.finished_at
        expected_blocker = max(first.id, second.id)
        factory = _CountingFactory(build_success_exact_match_response())
        with (
            patch("django.utils.timezone.now", lambda: self.FIXED),
            patch.dict(os_environ(), {CONFIGURED_ENV: CONFIGURED_BASE_URL}),
            patch.object(
                command_module,
                "execute_claimed_vendor_refresh_with_default_providers",
                _fake_runtime_entry(factory),
            ),
        ):
            code, text = _invoke(str(run.id), "--operator", "op-a")
        assert code == 0
        assert "outcome: COOLDOWN_REFUSAL" in text
        assert f"vendor refresh: blocking-child {expected_blocker}" in text
        assert factory.invocations == 0


# ---------------------------------------------------------------------------
# Row 3 (command level) — config-missing / normalization-mismatch /
# factory-error fail-closed paths
# ---------------------------------------------------------------------------


class TestFailClosedPreflightPaths(TestCase):
    """Bounded preflight refusals through the full command flow:
    zero construction, zero lookup, zero complete, one bounded fail
    write (T1 fail outcome), exit 0, child durably FAILED."""

    def _fail_closed(self, run, env: dict, factory) -> tuple:
        complete_spy = _spied_service(complete_vendor_refresh)
        fail_spy = _spied_service(core.fail_vendor_refresh)
        with (
            patch.dict(os_environ(), env, clear=True),
            patch.object(core, "complete_vendor_refresh", complete_spy),
            patch.object(core, "fail_vendor_refresh", fail_spy),
            patch.object(
                command_module,
                "execute_claimed_vendor_refresh_with_default_providers",
                _fake_runtime_entry(factory),
            ),
        ):
            code, text = _invoke(str(run.id), "--operator", "op-a")
        return code, text, factory, complete_spy, fail_spy

    def test_missing_base_url_fails_closed(self) -> None:
        run = _make_completed_run()
        factory = _CountingFactory(build_success_exact_match_response())
        env = dict(os_environ())
        env.pop(CONFIGURED_ENV, None)
        code, text, factory, complete_spy, fail_spy = self._fail_closed(run, env, factory)
        assert code == 0
        assert (
            "outcome: FAILED failure-reason=VENDOR_LOOKUP_CONFIG_MISSING" in text
        )
        assert len(complete_spy.calls) == 0
        assert len(fail_spy.calls) == 1
        assert factory.invocations == 0
        assert factory.lookup_count == 0
        row = _row_snapshot(VendorRefreshExecution.objects.get(parent_run=run).pk)
        assert row["state"] == VendorRefreshState.FAILED
        assert row["failure_reason"] == VendorRefreshFailureReason.VENDOR_LOOKUP_CONFIG_MISSING
        assert row["result_payload"] is None
        assert row["result_schema_version"] is None

    def test_blank_base_url_fails_closed_like_missing(self) -> None:
        run = _make_completed_run()
        factory = _CountingFactory(build_success_exact_match_response())
        env = dict(os_environ())
        env[CONFIGURED_ENV] = "   "
        code, text, factory, complete_spy, fail_spy = self._fail_closed(run, env, factory)
        assert code == 0
        assert (
            "outcome: FAILED failure-reason=VENDOR_LOOKUP_CONFIG_MISSING" in text
        )
        assert len(complete_spy.calls) == 0
        assert len(fail_spy.calls) == 1
        assert factory.invocations == 0
        assert factory.lookup_count == 0
        row = _row_snapshot(VendorRefreshExecution.objects.get(parent_run=run).pk)
        assert row["state"] == VendorRefreshState.FAILED
        assert row["failure_reason"] == VendorRefreshFailureReason.VENDOR_LOOKUP_CONFIG_MISSING

    def test_factory_raising_fails_internal_error(self) -> None:
        run = _make_completed_run()
        factory = _CountingFactory(build_success_exact_match_response())
        real_factory = factory

        def raising_factory():
            real_factory.invocations += 1
            raise RuntimeError("simulated construction failure")

        complete_spy = _spied_service(complete_vendor_refresh)
        fail_spy = _spied_service(core.fail_vendor_refresh)
        with (
            patch.dict(os_environ(), {CONFIGURED_ENV: CONFIGURED_BASE_URL}),
            patch.object(core, "complete_vendor_refresh", complete_spy),
            patch.object(core, "fail_vendor_refresh", fail_spy),
            patch.object(
                command_module,
                "execute_claimed_vendor_refresh_with_default_providers",
                _fake_runtime_entry_raising_factory(raising_factory),
            ),
        ):
            code, text = _invoke(str(run.id), "--operator", "op-a")
        assert code == 0
        assert "outcome: FAILED failure-reason=INTERNAL_ERROR" in text
        assert len(complete_spy.calls) == 0
        assert len(fail_spy.calls) == 1
        assert real_factory.invocations == 1  # factory 1 (failed)
        assert real_factory.lookup_count == 0  # no object -> lookup() 0


def _fake_runtime_entry_raising_factory(factory):
    def entry(child_id):
        return execute_claimed_vendor_refresh(
            child_id, vendor_adapter_factory=factory
        )

    return entry


class TestNormalizationMismatchThroughCommand(TestCase):
    """Row 4 (command level): the frozen query type would transmit an
    MPN different from the immutable captured binding — bounded
    MPN_QUERY_NORMALIZATION_MISMATCH fail, zero construction, zero
    lookup, the captured MPN never rewritten."""

    def test_surrounding_whitespace_mpn_fails_before_any_adapter(self) -> None:
        run = _make_completed_run()
        whitespace_mpn = f"{TEST_MPN} "
        ResearchRun.objects.filter(id=run.id).update(
            manufacturer_part_number=whitespace_mpn
        )
        factory = _CountingFactory(build_success_exact_match_response())
        complete_spy = _spied_service(complete_vendor_refresh)
        fail_spy = _spied_service(core.fail_vendor_refresh)
        with (
            patch.dict(os_environ(), {CONFIGURED_ENV: CONFIGURED_BASE_URL}),
            patch.object(core, "complete_vendor_refresh", complete_spy),
            patch.object(core, "fail_vendor_refresh", fail_spy),
            patch.object(
                command_module,
                "execute_claimed_vendor_refresh_with_default_providers",
                _fake_runtime_entry(factory),
            ),
        ):
            code, text = _invoke(str(run.id), "--operator", "op-a")
        assert code == 0
        assert (
            "outcome: FAILED "
            "failure-reason=MPN_QUERY_NORMALIZATION_MISMATCH" in text
        )
        assert len(complete_spy.calls) == 0
        assert len(fail_spy.calls) == 1
        assert factory.invocations == 0
        assert factory.lookup_count == 0
        row = _row_snapshot(VendorRefreshExecution.objects.get(parent_run=run).pk)
        assert row["state"] == VendorRefreshState.FAILED
        # The captured binding is byte-identical after (never rewritten).
        assert row["requested_mpn"] == whitespace_mpn


# ---------------------------------------------------------------------------
# Row 7 (command level) / section 8.3 — T1-T4 outcome mapping + the
# exit-code matrix
# ---------------------------------------------------------------------------


class TestTerminalOutcomeMapping(TestCase):
    """The executor's bounded outcomes mapped to the command outcome
    classes and exit codes (design section 8.3)."""

    def _parent(self):
        return _make_completed_run()

    def _run_with_executor_error(self, run, error: VendorRefreshExecutionError):
        def raiser(child_id):
            raise error

        with patch.dict(os_environ(), {CONFIGURED_ENV: CONFIGURED_BASE_URL}):
            with patch.object(
                command_module,
                "execute_claimed_vendor_refresh_with_default_providers",
                raiser,
            ):
                return _invoke(str(run.id), "--operator", "op-a")

    def test_state_not_running_terminal_reports_actual_durable_state(self) -> None:
        run = self._parent()
        code, text = self._run_with_executor_error(
            run,
            VendorRefreshExecutionError(
                VendorRefreshExecutionError.REASON_STATE_NOT_RUNNING,
                durable_state=VendorRefreshState.FAILED,
            ),
        )
        assert code == 0
        assert "outcome: TERMINAL_REPORTED state=FAILED" in text

    def test_state_not_found_reports_absent_with_exit_zero(self) -> None:
        run = self._parent()
        code, text = self._run_with_executor_error(
            run,
            VendorRefreshExecutionError(
                VendorRefreshExecutionError.REASON_STATE_NOT_FOUND,
            ),
        )
        assert code == 0
        assert "outcome: TERMINAL_REPORTED state=ABSENT" in text

    def test_terminalization_not_recorded_is_nonzero_with_gate_note(self) -> None:
        run = self._parent()
        code, text = self._run_with_executor_error(
            run,
            VendorRefreshExecutionError(
                VendorRefreshExecutionError.REASON_TERMINALIZATION_NOT_RECORDED,
                durable_state=VendorRefreshState.RUNNING,
            ),
        )
        assert code != 0
        assert "outcome: TERMINALIZATION_NOT_RECORDED state=RUNNING" in text
        assert "recovery gate (R1-4) is blocked pending O8" in text

    def test_terminalization_outcome_unknown_is_nonzero_with_gate_note(self) -> None:
        run = self._parent()
        code, text = self._run_with_executor_error(
            run,
            VendorRefreshExecutionError(
                VendorRefreshExecutionError.REASON_TERMINALIZATION_OUTCOME_UNKNOWN,
            ),
        )
        assert code != 0
        assert "outcome: TERMINALIZATION_OUTCOME_UNKNOWN" in text
        assert "recovery gate (R1-4) is blocked pending O8" in text

    def test_t2b_contract_defect_is_nonzero(self) -> None:
        run = self._parent()
        code, text = self._run_with_executor_error(
            run, VendorRefreshExecutionError("invalid_payload")
        )
        assert code != 0
        assert "outcome: UNEXPECTED_ERROR reason=invalid_payload" in text

    def test_lost_complete_race_reports_actual_durable_state_without_retry(self) -> None:
        """D (row 7, T2 CAS-lost race through the REAL executor): a
        competing terminal write commits first; the executor's complete
        raises the typed zero-row error (reason=None); the pinned
        read-only reconciliation returns the ACTUAL durable shape; the
        command reports it with exit 0, NO retry, and NO fail issued
        as a substitute."""
        run = self._parent()
        factory = _CountingFactory(build_success_exact_match_response())
        real_complete = complete_vendor_refresh
        real_fail = core.fail_vendor_refresh
        from product_intelligence.runs import fail_vendor_refresh as real_fail_service

        competing_writes = {"fail": 0}

        def competing_complete(child_id, version, payload):
            # A competing row-4-shaped terminal writer commits first.
            competing_writes["fail"] += 1
            real_fail_service(child_id, VendorRefreshFailureReason.INTERNAL_ERROR)
            # The executor's own complete then loses the terminal CAS.
            return real_complete(child_id, version, payload)

        complete_spy = _spied_service(competing_complete)
        fail_spy = _spied_service(real_fail)
        with (
            patch.dict(os_environ(), {CONFIGURED_ENV: CONFIGURED_BASE_URL}),
            patch.object(core, "complete_vendor_refresh", complete_spy),
            patch.object(core, "fail_vendor_refresh", fail_spy),
            patch.object(
                command_module,
                "execute_claimed_vendor_refresh_with_default_providers",
                _fake_runtime_entry(factory),
            ),
        ):
            code, text = _invoke(str(run.id), "--operator", "op-a")
        assert code == 0
        assert (
            "outcome: TERMINAL_REPORTED state=FAILED "
            "failure-reason=INTERNAL_ERROR" in text
        )
        assert len(complete_spy.calls) == 1  # no retry
        assert competing_writes["fail"] == 1  # the competitor's single write
        assert len(fail_spy.calls) == 0  # the executor issued NO fail
        assert factory.invocations == 1
        assert factory.lookup_count == 1
        row = _row_snapshot(VendorRefreshExecution.objects.get(parent_run=run).pk)
        assert row["state"] == VendorRefreshState.FAILED
        assert row["result_payload"] is None

    def test_state_not_running_pending_is_bounded_error_nonzero(self) -> None:
        """VREF-R1-3-FU1 F1: a NON-TERMINAL read-established state
        (PENDING) is NOT a successful terminal report — bounded error
        outcome with the actual state, non-zero exit, manual re-check."""
        run = self._parent()
        code, text = self._run_with_executor_error(
            run,
            VendorRefreshExecutionError(
                VendorRefreshExecutionError.REASON_STATE_NOT_RUNNING,
                durable_state=VendorRefreshState.PENDING,
            ),
        )
        assert code != 0
        assert "outcome: TERMINALIZATION_NOT_RECORDED state=PENDING" in text
        assert "the child is not durably terminal" in text
        assert "recovery gate (R1-4) is blocked pending O8" in text

    def test_state_not_running_running_is_bounded_error_nonzero(self) -> None:
        """VREF-R1-3-FU1 F1: the same bounded error treatment over a
        read-established RUNNING (otherwise anomalous) state."""
        run = self._parent()
        code, text = self._run_with_executor_error(
            run,
            VendorRefreshExecutionError(
                VendorRefreshExecutionError.REASON_STATE_NOT_RUNNING,
                durable_state=VendorRefreshState.RUNNING,
            ),
        )
        assert code != 0
        assert "outcome: TERMINALIZATION_NOT_RECORDED state=RUNNING" in text
        assert "the child is not durably terminal" in text
        assert "recovery gate (R1-4) is blocked pending O8" in text

    def test_state_not_running_non_terminal_issues_no_further_write_or_claim(
        self
    ) -> None:
        """VREF-R1-3-FU1 F1: the non-terminal report is reporting only
        — the invocation's write statements are EXACTLY the trigger
        INSERT + the zero-row lock UPDATE + the one claim UPDATE (the
        command's own serialized transaction); the bounded error
        outcome adds NO second terminal write, NO further claim, and
        NO Vendor lookup."""
        run = self._parent()

        def raiser(child_id):
            raise VendorRefreshExecutionError(
                VendorRefreshExecutionError.REASON_STATE_NOT_RUNNING,
                durable_state=VendorRefreshState.RUNNING,
            )

        with CaptureQueriesContext(connections["default"]) as ctx:
            with patch.object(
                command_module,
                "execute_claimed_vendor_refresh_with_default_providers",
                raiser,
            ):
                code, text = _invoke(str(run.id), "--operator", "op-a")
        assert code != 0
        upper = [q["sql"].lstrip().upper() for q in ctx.captured_queries]
        assert sum(s.startswith("INSERT") for s in upper) == 1  # the trigger
        assert sum(s.startswith("UPDATE") for s in upper) == 2  # lock + the one claim
        assert sum(s.startswith("DELETE") for s in upper) == 0


class TestStdoutOutsideWriteTransaction(TestCase):
    """VREF-R1-3-FU1 F2: the IN_PROGRESS / COOLDOWN_REFUSAL / anomalous-
    trigger branches emit their bounded stdout only AFTER the
    serialized write transaction has exited — no transaction lock is
    held during stdout writing. The positive control (the [L] zero-row
    lock statement observed at savepoint depth +1 over the TestCase
    frame) proves the instrumentation actually sees the command's
    inner transaction; the refusal rows' byte-identity and zero-call
    pins prove the business behavior is unchanged (no new child, no
    claim, no lookup)."""

    def _run_with_depth_spy(self, run: ResearchRun) -> tuple:
        out = StringIO()
        cmd = command_module.Command(stdout=out)
        write_depths: list = []
        real_write = cmd.stdout.write

        def spy_write(msg, *args, **kwargs):
            # Instance-attribute shadow: the first argument IS the line
            # (no self binding).
            write_depths.append((msg, len(connections["default"].savepoint_ids)))
            return real_write(msg, *args, **kwargs)

        cmd.stdout.write = spy_write
        lock_depths: list = []
        real_model = VendorRefreshExecution

        class _RecordingQS:
            def __init__(self, qs) -> None:
                self._qs = qs

            def update(self, *a, **k):
                lock_depths.append(len(connections["default"].savepoint_ids))
                return self._qs.update(*a, **k)

        class _Proxy:
            class objects:
                @staticmethod
                def filter(*args, **kwargs):
                    qs = real_model.objects.filter(*args, **kwargs)
                    if "active_slot" in kwargs:
                        return _RecordingQS(qs)
                    return qs

        baseline = len(connections["default"].savepoint_ids)
        stub = _recording_stub()
        with (
            patch.dict(os_environ(), {CONFIGURED_ENV: CONFIGURED_BASE_URL}),
            patch.object(command_module, "VendorRefreshExecution", _Proxy),
            patch.object(
                command_module,
                "execute_claimed_vendor_refresh_with_default_providers",
                stub,
            ),
        ):
            try:
                cmd.handle(parent_run=str(run.id), operator="op-a", force_repeat=False)
                code = None
            except SystemExit as exc:
                code = exc.code
        return code, out.getvalue(), write_depths, lock_depths, baseline, stub

    def test_in_progress_stdout_is_emitted_outside_the_write_transaction(self) -> None:
        run = _make_completed_run()
        orphan = _make_pending_child(run, operator="op-programmatic")
        before = _row_snapshot(orphan.pk)
        code, text, write_depths, lock_depths, baseline, stub = self._run_with_depth_spy(run)
        # Positive control: the [L] zero-row lock statement ran INSIDE
        # the command's serialized transaction (depth +1 over the
        # TestCase frame).
        assert lock_depths == [baseline + 1]
        # Business behavior preserved: bounded IN_PROGRESS, exit 0, no
        # new child, the orphan byte-identical, executor never entered.
        assert code == 0
        assert "outcome: IN_PROGRESS" in text
        assert VendorRefreshExecution.objects.filter(parent_run=run).count() == 1
        assert _row_snapshot(orphan.pk) == before
        assert len(stub.calls) == 0
        # F2: EVERY stdout line of the refusal invocation was emitted
        # OUTSIDE the command's write transaction (baseline depth).
        assert write_depths
        assert all(depth == baseline for _, depth in write_depths)

    def test_cooldown_refusal_stdout_is_emitted_outside_the_write_transaction(
        self
    ) -> None:
        run = _make_completed_run()
        _make_terminal_child(run, operator="op-t")  # finished just now: inside the window
        code, text, write_depths, lock_depths, baseline, stub = self._run_with_depth_spy(run)
        assert lock_depths == [baseline + 1]
        # Business behavior preserved: bounded COOLDOWN_REFUSAL with the
        # blocking child's facts, exit 0, no new child, executor never
        # entered.
        assert code == 0
        assert "outcome: COOLDOWN_REFUSAL" in text
        assert "blocking-child" in text
        assert "age-seconds=" in text
        assert VendorRefreshExecution.objects.filter(parent_run=run).count() == 1
        assert len(stub.calls) == 0
        assert write_depths
        assert all(depth == baseline for _, depth in write_depths)


class TestOuterBoundaryOutcomes(TestCase):
    """DATABASE_BUSY, the propagated claim failure, and non-bounded
    raises: bounded output, non-zero exit, zero mutation."""

    def test_database_busy_is_bounded_nonzero_with_zero_mutation(self) -> None:
        run = _make_completed_run()
        factory = _CountingFactory(build_success_exact_match_response())
        claim_spy = _spied_service(claim_vendor_refresh)
        with (
            patch.dict(os_environ(), {CONFIGURED_ENV: CONFIGURED_BASE_URL}),
            patch.object(command_module, "VendorRefreshExecution", _make_model_proxy()),
            patch.object(command_module, "claim_vendor_refresh", claim_spy),
            patch.object(
                command_module,
                "execute_claimed_vendor_refresh_with_default_providers",
                _fake_runtime_entry(factory),
            ),
        ):
            code, text = _invoke(str(run.id), "--operator", "op-a")
        assert code != 0
        assert "outcome: DATABASE_BUSY" in text
        assert "no state changed" in text
        assert len(claim_spy.calls) == 0
        assert factory.invocations == 0
        assert factory.lookup_count == 0
        assert VendorRefreshExecution.objects.filter(parent_run=run).count() == 0

    def test_claim_failure_propagates_bounded_nonzero_with_total_rollback(self) -> None:
        """M (row 19): the in-transaction claim RAISES (the
        structurally-unreachable shape); the transaction rolls back
        (no row), the executor is NEVER entered, and the raise is NOT
        caught to continue — bounded non-zero exit."""
        run = _make_completed_run()
        factory = _CountingFactory(build_success_exact_match_response())
        trigger_spy = _spied_service(trigger_vendor_refresh)
        claim_raised = {"count": 0}

        def raising_claim(child_id):
            claim_raised["count"] += 1
            raise VendorRefreshClaimError(child_id=child_id)

        stub = _recording_stub()
        with (
            patch.dict(os_environ(), {CONFIGURED_ENV: CONFIGURED_BASE_URL}),
            patch.object(command_module, "trigger_vendor_refresh", trigger_spy),
            patch.object(command_module, "claim_vendor_refresh", raising_claim),
            patch.object(
                command_module,
                "execute_claimed_vendor_refresh_with_default_providers",
                stub,
            ),
        ):
            code, text = _invoke(str(run.id), "--operator", "op-a")
        assert code != 0
        assert "outcome: UNEXPECTED_ERROR" in text
        # Total rollback: no child row survived.
        assert VendorRefreshExecution.objects.filter(parent_run=run).count() == 0
        assert len(stub.calls) == 0  # the executor was never entered
        assert factory.invocations == 0
        assert claim_raised["count"] == 1

    def test_unexpected_error_is_bounded_without_raw_text(self) -> None:
        run = _make_completed_run()

        def raiser(child_id):
            raise ValueError("boom-secret-detail")

        with patch.object(
            command_module,
            "execute_claimed_vendor_refresh_with_default_providers",
            raiser,
        ):
            code, text = _invoke(str(run.id), "--operator", "op-a")
        assert code != 0
        assert "outcome: UNEXPECTED_ERROR reason=ValueError" in text
        assert "boom-secret-detail" not in text


def _make_model_proxy():
    """A proxy over VendorRefreshExecution whose ``objects.filter``
    raises OperationalError ONLY for the zero-row lock statement call
    (the one carrying ``active_slot``); every other read goes to the
    real manager."""
    from product_intelligence.runs import models as runs_models

    class _RaisingQS:
        def update(self, *a, **k):
            raise OperationalError("database is locked")

    class _Proxy:
        id = runs_models.VendorRefreshExecution.id
        parent_run_id = runs_models.VendorRefreshExecution.parent_run_id

        class objects:
            @staticmethod
            def filter(*args, **kwargs):
                if "active_slot" in kwargs:
                    return _RaisingQS()
                return runs_models.VendorRefreshExecution.objects.filter(*args, **kwargs)

        @classmethod
        def __class_getitem__(cls, item):
            return cls

    return _Proxy()


# ---------------------------------------------------------------------------
# Row 19 / Row 15 / O4 — AST pins: single claim site, no claim error
# caught, read-only except bodies, import discipline
# ---------------------------------------------------------------------------


REPO_ROOT = Path(__file__).resolve().parents[2]
PACKAGE_ROOT = REPO_ROOT / "product_intelligence"
COMMAND_PATH = (
    PACKAGE_ROOT / "runs" / "management" / "commands" / "vendor_refresh.py"
)
R1_EXECUTION_FILES = {
    "vendor_refresh.py",
    "vendor_refresh_runtime.py",
    "vendor_commercial_binding.py",
}


def _tree(path: Path) -> ast.Module:
    return ast.parse(path.read_text(encoding="utf-8"))


def _imported_modules(tree: ast.Module) -> set[str]:
    modules: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            modules.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module is not None:
            modules.add(node.module)
    return modules


class TestSingleClaimSiteAst(TestCase):
    """Row 19: the command is the ONLY R1 module referencing
    ``claim_vendor_refresh`` — at EXACTLY ONE call site (inside the
    serialized transaction); no R1 module catches a claim error; the
    command's except bodies are read-only."""

    def test_command_is_the_only_r1_module_referencing_the_claim_primitive(self) -> None:
        for name in sorted(R1_EXECUTION_FILES):
            tree = _tree(PACKAGE_ROOT / "execution" / name)
            for node in ast.walk(tree):
                identifiers = []
                if isinstance(node, ast.Name):
                    identifiers.append(node.id)
                elif isinstance(node, ast.Attribute):
                    identifiers.append(node.attr)
                elif isinstance(node, ast.ImportFrom):
                    identifiers.extend(alias.name for alias in node.names)
                for identifier in identifiers:
                    assert identifier != "claim_vendor_refresh", (
                        f"R1 execution module {name} references the claim "
                        "primitive (FU1-F1: POST-CLAIM ONLY)"
                    )
        # No OTHER runs module references it either.
        for path in sorted((PACKAGE_ROOT / "runs").rglob("*.py")):
            if path == COMMAND_PATH:
                continue
            tree = _tree(path)
            for node in ast.walk(tree):
                if isinstance(node, ast.Name) and node.id == "claim_vendor_refresh":
                    pytest.fail(
                        f"runs module {path.name} references the claim "
                        "primitive (the command is the only claim site)"
                    )

    def test_command_has_exactly_one_claim_call_site(self) -> None:
        tree = _tree(COMMAND_PATH)
        call_sites = [
            node
            for node in ast.walk(tree)
            if isinstance(node, ast.Call)
            and isinstance(node.func, ast.Name)
            and node.func.id == "claim_vendor_refresh"
        ]
        assert len(call_sites) == 1, (
            f"the command must contain EXACTLY ONE claim call site; "
            f"got {len(call_sites)}"
        )

    def test_no_r1_module_catches_a_claim_or_terminal_cas_error(self) -> None:
        claim_error = "VendorRefreshClaimError"
        cas_errors = {"VendorRefreshCompletionError", "VendorRefreshFailureError"}
        core_path = PACKAGE_ROOT / "execution" / "vendor_refresh.py"
        for path in sorted((PACKAGE_ROOT / "execution").glob("vendor_*.py")):
            if path == core_path:
                continue
            for name_ in _except_named_errors(_tree(path)):
                assert name_ != claim_error, (
                    f"{path.name} catches a claim error; claim errors are "
                    "NEVER caught in any R1 module (FU3-F1)"
                )
                assert name_ not in cas_errors, (
                    f"{path.name} catches a terminal-CAS error; the "
                    "completion/failure errors are caught ONLY in the "
                    "execution core's pinned read-only reconciliation "
                    "(FU3-F1)"
                )
        # The execution core (R1-2) may catch the completion/failure
        # errors in its pinned reconciliation — but NEVER a claim error.
        for name_ in _except_named_errors(_tree(core_path)):
            assert name_ != claim_error, (
                "the execution core catches a claim error (FU3-F1)"
            )
        # The command itself: no claim or terminal-CAS error named in
        # any except handler.
        for name_ in _except_named_errors(_tree(COMMAND_PATH)):
            assert name_ != claim_error and name_ not in cas_errors, (
                f"the command catches {name_}"
            )


def _except_named_errors(tree: ast.Module) -> list[str]:
    named: list[str] = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.ExceptHandler) or node.type is None:
            continue
        if isinstance(node.type, ast.Name):
            named.append(node.type.id)
        elif isinstance(node.type, (ast.Tuple, ast.List)):
            named.extend(
                elt.id for elt in node.type.elts if isinstance(elt, ast.Name)
            )
    return named

    def test_command_except_bodies_are_read_only(self) -> None:
        """No except body in the command issues a terminal write, a
        claim, a factory invocation, or a lookup (the reconciliation
        branches are read-only: SELECT + report)."""
        tree = _tree(COMMAND_PATH)
        forbidden_calls = {
            "claim_vendor_refresh",
            "trigger_vendor_refresh",
            "complete_vendor_refresh",
            "fail_vendor_refresh",
            "execute_claimed_vendor_refresh_with_default_providers",
            "lookup",
        }
        for node in ast.walk(tree):
            if not isinstance(node, ast.ExceptHandler):
                continue
            for sub in ast.walk(node):
                if isinstance(sub, ast.Call):
                    if isinstance(sub.func, ast.Name):
                        assert sub.func.id not in forbidden_calls, (
                            f"except body issues {sub.func.id}()"
                        )
                    elif isinstance(sub.func, ast.Attribute):
                        assert sub.func.attr not in forbidden_calls, (
                            f"except body issues {sub.func.attr}()"
                        )


class TestCommandImportDiscipline(TestCase):
    """Row 15 / O4: the command's exact import allowlist; it is the
    ONLY runs module importing the execution public API; no provider,
    web, research, or domain import anywhere in the command."""

    def test_only_the_command_imports_execution_from_the_runs_layer(self) -> None:
        offenders = []
        for path in sorted((PACKAGE_ROOT / "runs").rglob("*.py")):
            if path == COMMAND_PATH:
                continue
            imported = _imported_modules(_tree(path))
            for module in imported:
                if module == "product_intelligence.execution" or module.startswith(
                    "product_intelligence.execution."
                ):
                    offenders.append(path.name)
        assert not offenders, (
            f"runs modules importing execution (O4 carve-out is the "
            f"command ONLY): {offenders}"
        )

    def test_command_import_allowlist(self) -> None:
        imported = _imported_modules(_tree(COMMAND_PATH))
        allowlist = {
            "__future__",
            "sys",
            "uuid",
            "datetime",
            "django.core.management.base",
            "django.db",
            "django.utils",
            "product_intelligence.execution",
            "product_intelligence.runs",
        }
        assert imported <= allowlist, (
            f"the command imports outside the allowlist: "
            f"{imported - allowlist}"
        )
        # The django.utils import is the ``timezone`` module reference
        # only (no other django.utils symbol).
        tree = _tree(COMMAND_PATH)
        django_utils_names = {
            alias.name
            for node in ast.walk(tree)
            if isinstance(node, ast.ImportFrom)
            and node.module == "django.utils"
            for alias in node.names
        }
        assert django_utils_names == {"timezone"}, (
            f"the command's django.utils import must be exactly "
            f"{{'timezone'}}; got {django_utils_names}"
        )

    def test_command_imports_no_provider_web_research_or_domain(self) -> None:
        imported = _imported_modules(_tree(COMMAND_PATH))
        for module in imported:
            for forbidden in (
                "product_intelligence.providers",
                "product_intelligence.web",
                "product_intelligence.research",
                "product_intelligence.domain",
            ):
                assert not module.startswith(forbidden), (
                    f"the command imports {module} ({forbidden} is "
                    "forbidden by design section 10.1)"
                )

    def test_command_references_no_concrete_adapter_class(self) -> None:
        tree = _tree(COMMAND_PATH)
        for node in ast.walk(tree):
            if isinstance(node, ast.Name):
                assert node.id != "InternalVendorAdapter"
            elif isinstance(node, ast.Attribute):
                assert node.attr != "InternalVendorAdapter"


# ---------------------------------------------------------------------------
# Row 16 — no new browser mutation surface
# ---------------------------------------------------------------------------


class TestNoBrowserSurface(TestCase):
    """R1-3 adds a host-side management command and NOTHING to the web
    layer: the URLconf route set is byte-equal to the frozen R0/
    production set, and no recovery command is registered."""

    # The frozen route set of record at the R1-2 endpoint (design
    # section 12 row 16: URLconf route set byte-equal to the frozen
    # R0/production set — no new route).
    FROZEN_ROUTES = [
        ("root", ""),
        ("healthz", "healthz"),
        ("research-new", "research/new"),
        ("research-detail", "research/<uuid:run_id>"),
        ("research-retry", "research/<uuid:run_id>/retry"),
        (
            "research-review",
            "research/<uuid:run_id>/review/<uuid:candidate_id>",
        ),
        ("research-comparables", "research/<uuid:run_id>/comparables"),
    ]

    def test_urlconf_route_set_is_the_frozen_set(self) -> None:
        from django.urls import get_resolver

        def walk(patterns, prefix=""):
            out = []
            for p in patterns:
                if hasattr(p, "url_patterns"):
                    out.extend(walk(p.url_patterns, prefix + str(p.pattern)))
                else:
                    out.append((p.name, prefix + str(p.pattern)))
            return out

        assert walk(get_resolver().url_patterns) == self.FROZEN_ROUTES

    def test_command_registry_gains_exactly_the_vendor_refresh_command(self) -> None:
        commands = get_commands()
        assert commands.get("vendor_refresh") == "product_intelligence.runs"
        # R1-4 remains prohibited: no recovery command is registered.
        assert "vendor_refresh_recovery" not in commands

    def test_command_module_defines_no_view_or_url_surface(self) -> None:
        tree = _tree(COMMAND_PATH)
        imported = _imported_modules(tree)
        for module in imported:
            assert not module.startswith("django.urls"), (
                "the command must not import URL routing"
            )
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                assert "view" not in node.name.lower()
