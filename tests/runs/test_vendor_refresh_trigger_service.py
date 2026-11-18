"""VENDOR-REFRESH-WEB — the shared trigger + claim decision service.

D nodes over ``product_intelligence.runs.trigger_and_claim_vendor_
refresh`` — the serialized decision extracted verbatim from the VREF-
R1-3 command (M3 Option A + M4 SQLite A3) and shared by the command
and the web POST trigger.

The GENUINE file-backed process concurrency (single winner, cooldown
interleavings, SQLite locking behavior) is proven by the unchanged C
suite ``tests/runs/test_vendor_refresh_concurrency.py``; the command's
behavioral pins (stdout, exit codes) remain green over the service in
``tests/runs/test_vendor_refresh_command.py``. This suite pins the
service's OWN bounded contract:

* the six bounded decision kinds (created / in_progress /
  in_progress_anomaly / cooldown / ineligible / database_busy);
* single-winner + post-claim execution ownership (M3 Option A): only
  the invocation that creates the child claims it; a pre-existing
  PENDING child is reported, never claimed, never executed;
* the five-minute repeat safeguard (STRICT ``< 300 s``; the
  ``force_repeat`` parameter bypasses the cooldown refusal ONLY and
  never the in-progress report; a refusal leaves NO new child);
* ineligibility (the R0 trigger's bounded reasons, zero mutation);
* the busy-outcome mapping (zero mutation, manual re-run);
* a propagated claim failure (structurally unreachable under the
  lock) escapes UNCAUGHT: total rollback, no partial PENDING row;
* operator / trigger_source pass-through (recorded verbatim; the
  WEB_UI member is accepted; the command's MANAGEMENT_COMMAND
  default is unchanged).
"""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone as dt_timezone
from unittest.mock import patch

import pytest
from django.db import OperationalError
from django.test import TestCase

from product_intelligence.domain import ResearchRequest
from product_intelligence.domain.enums import ResearchRunState
from product_intelligence.runs import (
    VendorRefreshClaimError,
    VendorRefreshTriggerDecision,
    claim_vendor_refresh,
    complete_vendor_refresh,
    fail_vendor_refresh,
    trigger_and_claim_vendor_refresh,
    trigger_vendor_refresh,
)
from product_intelligence.runs.errors import VendorRefreshTriggerError
from product_intelligence.runs.models import (
    PriceIntelligenceSnapshot,
    ResearchRun,
    VendorRefreshExecution,
    VendorRefreshFailureReason,
    VendorRefreshState,
    VendorRefreshTriggerSource,
)

TEST_MPN = "BCM957608-P2200GQF00"
TEST_DESCRIPTION = "Enterprise SSD"
PINNED = datetime(2026, 6, 1, 12, 0, 0, tzinfo=dt_timezone.utc)


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


def _make_terminal_child(run: ResearchRun, *, at: datetime, complete: bool = True):
    child = claim_vendor_refresh(trigger_vendor_refresh(run.id, operator="op-t").id)
    if complete:
        return complete_vendor_refresh(
            child.id,
            1,
            {"schema_version": 1, "vendor_commercial_result": {"marker": "test"}},
            at=at,
        )
    return fail_vendor_refresh(
        child.id, VendorRefreshFailureReason.INTERNAL_ERROR, at=at
    )


# ---------------------------------------------------------------------------
# The created kind (single winner + ownership)
# ---------------------------------------------------------------------------


class TestCreatedKind(TestCase):
    """The decision that creates a child claims it in the same
    serialized transaction and returns the durably RUNNING row (the
    caller owns the post-commit execution)."""

    def test_created_returns_the_claimed_running_child(self) -> None:
        run = _make_completed_run()
        decision = trigger_and_claim_vendor_refresh(
            run.id, operator="op-a", trigger_source=VendorRefreshTriggerSource.WEB_UI
        )
        assert decision.kind == VendorRefreshTriggerDecision.KIND_CREATED
        child = decision.created_child
        assert child.state == VendorRefreshState.RUNNING
        assert child.active_slot == 1
        assert child.started_at is not None
        assert child.finished_at is None
        assert child.operator == "op-a"  # recorded verbatim
        assert child.trigger_source == VendorRefreshTriggerSource.WEB_UI
        assert child.requested_mpn == TEST_MPN  # the captured binding
        # Exactly one row for the parent.
        assert VendorRefreshExecution.objects.filter(parent_run=run).count() == 1

    def test_created_is_the_only_claim_winner(self) -> None:
        """A second decision over the same parent (the first child
        still RUNNING) reports in_progress: no second claim, no second
        row (the single-winner / ownership guarantee at the service
        level; the genuine process race is the C suite's)."""
        run = _make_completed_run()
        first = trigger_and_claim_vendor_refresh(run.id, operator="op-1")
        assert first.kind == VendorRefreshTriggerDecision.KIND_CREATED
        second = trigger_and_claim_vendor_refresh(run.id, operator="op-2")
        assert second.kind == VendorRefreshTriggerDecision.KIND_IN_PROGRESS
        assert [c.id for c in second.active_children] == [first.created_child.id]
        assert VendorRefreshExecution.objects.filter(parent_run=run).count() == 1
        # The first child is untouched (never re-claimed).
        first.created_child.refresh_from_db()
        assert first.created_child.operator == "op-1"
        assert first.created_child.state == VendorRefreshState.RUNNING


# ---------------------------------------------------------------------------
# In-progress (PENDING and RUNNING; the M3 Option A orphan rule)
# ---------------------------------------------------------------------------


class TestInProgressKind(TestCase):
    def test_preexisting_pending_orphan_is_reported_never_claimed(self) -> None:
        run = _make_completed_run()
        orphan = trigger_vendor_refresh(run.id, operator="op-orphan")
        decision = trigger_and_claim_vendor_refresh(run.id, operator="op-new")
        assert decision.kind == VendorRefreshTriggerDecision.KIND_IN_PROGRESS
        assert decision.created_child is None
        orphan.refresh_from_db()
        assert orphan.state == VendorRefreshState.PENDING  # untouched
        assert orphan.operator == "op-orphan"  # provenance untouched
        assert VendorRefreshExecution.objects.filter(parent_run=run).count() == 1

    def test_preexisting_running_child_is_reported(self) -> None:
        run = _make_completed_run()
        running = claim_vendor_refresh(
            trigger_vendor_refresh(run.id, operator="op-r").id
        )
        decision = trigger_and_claim_vendor_refresh(run.id, operator="op-new")
        assert decision.kind == VendorRefreshTriggerDecision.KIND_IN_PROGRESS
        assert [c.id for c in decision.active_children] == [running.id]
        running.refresh_from_db()
        assert running.state == VendorRefreshState.RUNNING


# ---------------------------------------------------------------------------
# Cooldown (the five-minute repeat safeguard; STRICT < 300 s)
# ---------------------------------------------------------------------------


class TestCooldownKind(TestCase):
    def _terminal_at(self, run, age_seconds: float):
        return _make_terminal_child(
            run, at=PINNED - timedelta(seconds=age_seconds)
        )

    def test_within_cooldown_refused_no_child(self) -> None:
        run = _make_completed_run()
        blocker = self._terminal_at(run, 299.9)
        with patch("django.utils.timezone.now", lambda: PINNED):
            decision = trigger_and_claim_vendor_refresh(run.id, operator="op-new")
        assert decision.kind == VendorRefreshTriggerDecision.KIND_COOLDOWN
        assert decision.cooldown_child.id == blocker.id
        assert decision.cooldown_age_seconds == 299
        assert VendorRefreshExecution.objects.filter(parent_run=run).count() == 1

    def test_boundary_exactly_300s_allowed(self) -> None:
        """The refusal is STRICT ``< 300 s`` (O7): age exactly 300.0
        permits a new attempt."""
        run = _make_completed_run()
        self._terminal_at(run, 300.0)
        with patch("django.utils.timezone.now", lambda: PINNED):
            decision = trigger_and_claim_vendor_refresh(run.id, operator="op-new")
        assert decision.kind == VendorRefreshTriggerDecision.KIND_CREATED
        assert VendorRefreshExecution.objects.filter(parent_run=run).count() == 2

    def test_force_repeat_bypasses_cooldown_only(self) -> None:
        run = _make_completed_run()
        self._terminal_at(run, 10.0)
        with patch("django.utils.timezone.now", lambda: PINNED):
            decision = trigger_and_claim_vendor_refresh(
                run.id, operator="op-new", force_repeat=True
            )
        assert decision.kind == VendorRefreshTriggerDecision.KIND_CREATED
        assert VendorRefreshExecution.objects.filter(parent_run=run).count() == 2

    def test_force_repeat_does_not_bypass_in_progress(self) -> None:
        run = _make_completed_run()
        orphan = trigger_vendor_refresh(run.id, operator="op-orphan")
        decision = trigger_and_claim_vendor_refresh(
            run.id, operator="op-new", force_repeat=True
        )
        assert decision.kind == VendorRefreshTriggerDecision.KIND_IN_PROGRESS
        assert [c.id for c in decision.active_children] == [orphan.id]
        assert VendorRefreshExecution.objects.filter(parent_run=run).count() == 1

    def test_tie_break_prefers_the_larger_id_at_identical_finished_at(self) -> None:
        run = _make_completed_run()
        first = _make_terminal_child(run, at=PINNED - timedelta(seconds=10.0))
        second = _make_terminal_child(run, at=PINNED - timedelta(seconds=10.0))
        with patch("django.utils.timezone.now", lambda: PINNED):
            decision = trigger_and_claim_vendor_refresh(run.id, operator="op-new")
        assert decision.kind == VendorRefreshTriggerDecision.KIND_COOLDOWN
        assert decision.cooldown_child.id == max(first.id, second.id)

    def test_failed_terminal_child_also_blocks_cooldown(self) -> None:
        """The safeguard is against the latest TERMINAL child (either
        state) — a failed attempt still bounds the repeat rate."""
        run = _make_completed_run()
        _make_terminal_child(
            run, at=PINNED - timedelta(seconds=10.0), complete=False
        )
        with patch("django.utils.timezone.now", lambda: PINNED):
            decision = trigger_and_claim_vendor_refresh(run.id, operator="op-new")
        assert decision.kind == VendorRefreshTriggerDecision.KIND_COOLDOWN


# ---------------------------------------------------------------------------
# Ineligibility (the R0 trigger's bounded reasons; zero mutation)
# ---------------------------------------------------------------------------


class TestIneligibleKind(TestCase):
    def _assert_ineligible(self, run_id: uuid.UUID, reason: str) -> None:
        before = VendorRefreshExecution.objects.count()
        decision = trigger_and_claim_vendor_refresh(run_id, operator="op-x")
        assert decision.kind == VendorRefreshTriggerDecision.KIND_INELIGIBLE
        assert decision.ineligible_reason == reason
        assert decision.created_child is None
        assert VendorRefreshExecution.objects.count() == before

    def test_parent_not_found(self) -> None:
        self._assert_ineligible(uuid.uuid4(), "parent_not_found")

    def test_parent_not_completed(self) -> None:
        run = ResearchRun.objects.create_from_request(
            ResearchRequest(manufacturer_part_number=TEST_MPN, description=TEST_DESCRIPTION)
        )
        self._assert_ineligible(run.id, "parent_not_completed")

    def test_partially_completed_parent(self) -> None:
        run = ResearchRun.objects.create_from_request(
            ResearchRequest(manufacturer_part_number=TEST_MPN, description=TEST_DESCRIPTION)
        )
        run.transition_to(ResearchRunState.RUNNING)
        run.transition_to(ResearchRunState.PARTIALLY_COMPLETED)
        PriceIntelligenceSnapshot.objects.create(
            run=run,
            schema_version=1,
            payload={
                "request": {"manufacturer_part_number": TEST_MPN, "description": TEST_DESCRIPTION},
                "assessments": [],
                "buckets": [],
                "exclusions": [],
                "verification_status": "VERIFIED",
            },
        )
        self._assert_ineligible(run.id, "parent_not_completed")

    def test_no_snapshot(self) -> None:
        run = ResearchRun.objects.create_from_request(
            ResearchRequest(manufacturer_part_number=TEST_MPN, description=TEST_DESCRIPTION)
        )
        run.transition_to(ResearchRunState.RUNNING)
        run.transition_to(ResearchRunState.COMPLETED)
        self._assert_ineligible(run.id, "no_snapshot")

    def test_no_mpn(self) -> None:
        run = _make_completed_run(mpn="", description="description only")
        # The captured binding must be non-empty: a description-only
        # COMPLETED parent has no MPN to refresh.
        run.description  # touch
        self._assert_ineligible(run.id, "no_mpn")

    def test_invalid_operator_passes_through(self) -> None:
        run = _make_completed_run()
        decision = trigger_and_claim_vendor_refresh(run.id, operator="x" * 129)
        assert decision.kind == VendorRefreshTriggerDecision.KIND_INELIGIBLE
        assert decision.ineligible_reason == "invalid_operator"
        assert VendorRefreshExecution.objects.filter(parent_run=run).count() == 0

    def test_invalid_trigger_source_passes_through(self) -> None:
        run = _make_completed_run()
        decision = trigger_and_claim_vendor_refresh(
            run.id, operator="op-x", trigger_source="SCHEDULER"
        )
        assert decision.kind == VendorRefreshTriggerDecision.KIND_INELIGIBLE
        assert decision.ineligible_reason == "invalid_trigger_source"
        assert VendorRefreshExecution.objects.filter(parent_run=run).count() == 0


# ---------------------------------------------------------------------------
# Database busy + the propagated claim failure
# ---------------------------------------------------------------------------


class TestBusyAndClaimPropagation(TestCase):
    def test_lock_statement_busy_maps_to_database_busy(self) -> None:
        run = _make_completed_run()
        real_model = VendorRefreshExecution

        class _RaisingQS:
            def update(self, *a, **k):
                raise OperationalError("database is locked")

        class _Proxy:
            class objects:
                @staticmethod
                def filter(*args, **kwargs):
                    if "active_slot" in kwargs:
                        return _RaisingQS()
                    return real_model.objects.filter(*args, **kwargs)

        with patch(
            "product_intelligence.runs.vendor_refresh_trigger.VendorRefreshExecution",
            _Proxy,
        ):
            decision = trigger_and_claim_vendor_refresh(run.id, operator="op-x")
        assert decision.kind == VendorRefreshTriggerDecision.KIND_DATABASE_BUSY
        assert VendorRefreshExecution.objects.filter(parent_run=run).count() == 0

    def test_claim_failure_propagates_with_total_rollback(self) -> None:
        """The structurally-unreachable claim failure is NEVER caught
        to continue: the exception propagates and the transaction
        rolls back completely (no partial PENDING row survives)."""
        run = _make_completed_run()

        def raising_claim(child_id):
            raise VendorRefreshClaimError(child_id=str(child_id))

        with patch(
            "product_intelligence.runs.vendor_refresh_trigger.claim_vendor_refresh",
            raising_claim,
        ):
            with pytest.raises(VendorRefreshClaimError):
                trigger_and_claim_vendor_refresh(run.id, operator="op-x")
        assert VendorRefreshExecution.objects.filter(parent_run=run).count() == 0


# ---------------------------------------------------------------------------
# The bounded decision surface
# ---------------------------------------------------------------------------


class TestDecisionSurface(TestCase):
    def test_kind_vocabulary_is_bounded_and_public(self) -> None:
        assert VendorRefreshTriggerDecision.KIND_CREATED == "created"
        assert VendorRefreshTriggerDecision.KIND_IN_PROGRESS == "in_progress"
        assert (
            VendorRefreshTriggerDecision.KIND_IN_PROGRESS_ANOMALY
            == "in_progress_anomaly"
        )
        assert VendorRefreshTriggerDecision.KIND_COOLDOWN == "cooldown"
        assert VendorRefreshTriggerDecision.KIND_INELIGIBLE == "ineligible"
        assert VendorRefreshTriggerDecision.KIND_DATABASE_BUSY == "database_busy"

    def test_the_service_is_exported_through_the_runs_public_api(self) -> None:
        import product_intelligence.runs as runs_pkg

        assert "trigger_and_claim_vendor_refresh" in runs_pkg.__all__
        assert "VendorRefreshTriggerDecision" in runs_pkg.__all__
        assert runs_pkg.trigger_and_claim_vendor_refresh is (
            trigger_and_claim_vendor_refresh
        )
        assert runs_pkg.VendorRefreshTriggerDecision is VendorRefreshTriggerDecision

    def test_the_service_imports_no_execution_symbol(self) -> None:
        """O4 preserved: the service (a runs module) performs the
        decision ONLY — the post-commit execution stays with the
        caller (the command / the web view)."""
        import ast
        from pathlib import Path

        path = Path(
            "product_intelligence/runs/vendor_refresh_trigger.py"
        ).resolve()
        tree = ast.parse(path.read_text(encoding="utf-8"))
        modules = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                modules.update(alias.name for alias in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module and not node.level:
                modules.add(node.module)
        for module in modules:
            assert not (
                module == "product_intelligence.execution"
                or module.startswith("product_intelligence.execution.")
            ), f"the service imports execution: {module}"
        # No provider / web / research import either.
        for forbidden in (
            "product_intelligence.providers",
            "product_intelligence.web",
            "product_intelligence.research",
            "product_intelligence.domain",
        ):
            assert not any(
                module == forbidden or module.startswith(forbidden + ".")
                for module in modules
            ), f"the service imports {forbidden}"
