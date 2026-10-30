"""Vendor-refresh execution lifecycle primitive tests (VREF-R0).

PRODUCT-INTEL.VREF-R0 — persistence and lifecycle CAS for
``VendorRefreshExecution`` children of a COMPLETED ``ResearchRun``.

Covers the DESIGN2 frozen contract:

- the four stored lifecycle shapes and every invalid CHECK/UNIQUE shape
  (direct-DB constraint behavior);
- trigger eligibility (each bounded reason), verbatim canonical-MPN
  capture, and the legal absence of the original vendor snapshot;
- idempotency: active-child deduplication (concept 1) and post-terminal
  new attempts (concept 2); insert race → winner; unrelated
  IntegrityError propagation;
- claim / complete / fail compare-and-set: single-winner terminalization,
  atomic COMPLETED payload publication, zero-mutation duplicate
  terminalization;
- complete pre-mutation validation of the bounded
  schema-version/payload agreement (the frozen decoder reads the
  payload's top-level ``schema_version`` key; the stored version must
  equal it and both must be frozen V1 — performed at the dict level so
  the runs layer imports no research code; full codec validity is the
  producer's and the reader's job, per DESIGN2 §3.1), with no malformed
  COMPLETED row ever published;
- the R0 ``fail`` service REJECTION of the R1-reserved
  ``EXECUTION_INTERRUPTED`` reason BEFORE any UPDATE (zero row mutation),
  while the storage constraints still admit it for the future R1
  recovery transition;
- the absence of every recovery-based terminalization surface (no
  reclaim, no RUNNING→PENDING reset, no automatic retry, no
  operator-forced recovery, no reassignment) and of the R1 command /
  execution surfaces;
- parent-delete cascade;
- the parent ResearchRun and EVERY original snapshot/evidence artifact
  byte-identical before and after a full refresh lifecycle.

All tests are deterministic and offline: no network, no clock beyond
pinned datetimes, in-memory SQLite per the session test database.
"""

from __future__ import annotations

import ast
import uuid
from datetime import datetime, timezone
from decimal import Decimal
from unittest.mock import patch

import pytest
from django.db import IntegrityError
from django.test import TestCase

from product_intelligence.domain import ResearchRequest
from product_intelligence.domain.enums import ResearchRunState
from product_intelligence.research.commercial_supplement_codec import (
    ResearchSupplementResult,
    SupplementCodecError,
    SupplementSourceObservation,
    VendorCommercialResult,
    decode_research_supplement_result,
    encode_research_supplement_result,
)
# Public API surface (lazy exports) — these imports double as the export
# regression for the four primitives, the bounded errors, and the model
# vocabularies.
from product_intelligence.runs import (
    VendorRefreshClaimError,
    VendorRefreshCompletionError,
    VendorRefreshError,
    VendorRefreshFailureError,
    VendorRefreshTriggerError,
    claim_vendor_refresh,
    complete_vendor_refresh,
    fail_vendor_refresh,
    trigger_vendor_refresh,
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
    VendorRefreshTriggerSource,
)

TEST_MPN = "MTFDKCC3T8TGP-1BK1DABYYR"
TEST_DESCRIPTION = "Test enterprise SSD"
PINNED = datetime(2026, 1, 2, 3, 4, 5, tzinfo=timezone.utc)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_completed_run(mpn: str = TEST_MPN, description: str = TEST_DESCRIPTION) -> ResearchRun:
    """Create a COMPLETED ResearchRun with its PriceIntelligenceSnapshot."""
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
    return run


def _make_run_in_state(state: ResearchRunState) -> ResearchRun:
    """Create a ResearchRun in the given state (no snapshot)."""
    request = ResearchRequest(manufacturer_part_number=TEST_MPN, description=TEST_DESCRIPTION)
    run = ResearchRun.objects.create_from_request(request)
    if state is ResearchRunState.RUNNING:
        run.transition_to(ResearchRunState.RUNNING)
    elif state in (
        ResearchRunState.COMPLETED,
        ResearchRunState.PARTIALLY_COMPLETED,
        ResearchRunState.FAILED,
    ):
        run.transition_to(ResearchRunState.RUNNING)
        run.transition_to(state)
    return run


def _valid_payload(
    lookup_status: str = "SUCCESS",
    mpn: str = TEST_MPN,
    with_observation: bool = True,
) -> dict:
    """A frozen V1 supplement payload encoded with the frozen codec."""
    observations: tuple[SupplementSourceObservation, ...] = ()
    if with_observation:
        observations = (
            SupplementSourceObservation(
                source_name="source_alpha",
                explicit_candidate_mpn=mpn,
                vendor_mpn_match_type="EXACT",
                price_amount=Decimal("4740.18"),
                currency_code="EUR",
                availability="IN_STOCK",
                price_basis="CUSTOMER_PRICE",
                quantity=1,
                note_kind=None,
                brand_new=True,
                brand_new_basis="VENDOR_API_POLICY",
            ),
        )
    return encode_research_supplement_result(
        ResearchSupplementResult(
            vendor_commercial_result=VendorCommercialResult(
                lookup_status=lookup_status,
                retrieved_at=PINNED,
                observations=observations,
                source_issues=(),
            )
        )
    )


def _row_snapshot(pk) -> dict:
    """Every stored field of the row, re-read from the database."""
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


def _make_pending_child(run: ResearchRun, operator: str = "op-a") -> VendorRefreshExecution:
    return trigger_vendor_refresh(run.id, operator=operator)


def _make_running_child(run: ResearchRun, operator: str = "op-a") -> VendorRefreshExecution:
    child = _make_pending_child(run, operator=operator)
    return claim_vendor_refresh(child.id)


# ---------------------------------------------------------------------------
# Model lifecycle shapes — direct-DB constraint behavior
# ---------------------------------------------------------------------------


class TestModelLifecycleShapes(TestCase):
    """The stored shapes are enforced by the database for ANY writer.

    Valid shapes are accepted; invalid shapes are rejected with
    IntegrityError. ``editable=False`` is NOT claimed to reject these —
    the constraints below are the enforcement (DESIGN2-FU1 C6).
    """

    def _parent(self) -> ResearchRun:
        return _make_completed_run()

    def test_pending_shape_accepted(self) -> None:
        run = self._parent()
        child = VendorRefreshExecution.objects.create(
            parent_run=run,
            requested_mpn=TEST_MPN,
            state=VendorRefreshState.PENDING,
            active_slot=1,
            trigger_source=VendorRefreshTriggerSource.MANAGEMENT_COMMAND,
            operator="op-a",
        )
        child.refresh_from_db()
        assert child.started_at is None
        assert child.finished_at is None
        assert child.result_schema_version is None
        assert child.result_payload is None
        assert child.failure_reason is None

    def test_running_shape_accepted(self) -> None:
        run = self._parent()
        child = VendorRefreshExecution.objects.create(
            parent_run=run,
            requested_mpn=TEST_MPN,
            state=VendorRefreshState.RUNNING,
            active_slot=1,
            trigger_source=VendorRefreshTriggerSource.MANAGEMENT_COMMAND,
            operator="op-a",
            started_at=PINNED,
        )
        assert child.finished_at is None
        assert child.result_payload is None

    def test_completed_shape_accepted(self) -> None:
        """A COMPLETED shape with a non-null payload passes the CHECK.

        Codec validity is NOT a database concern (the frozen codec owns
        it, at producer and reader); the stored shape only requires
        version >= 1 and a present payload.
        """
        run = self._parent()
        child = VendorRefreshExecution.objects.create(
            parent_run=run,
            requested_mpn=TEST_MPN,
            state=VendorRefreshState.COMPLETED,
            active_slot=None,
            trigger_source=VendorRefreshTriggerSource.MANAGEMENT_COMMAND,
            operator="op-a",
            started_at=PINNED,
            finished_at=PINNED,
            result_schema_version=1,
            result_payload={"marker": "direct-db-shape"},
        )
        assert child.failure_reason is None

    def test_failed_shape_accepted(self) -> None:
        run = self._parent()
        child = VendorRefreshExecution.objects.create(
            parent_run=run,
            requested_mpn=TEST_MPN,
            state=VendorRefreshState.FAILED,
            active_slot=None,
            trigger_source=VendorRefreshTriggerSource.MANAGEMENT_COMMAND,
            operator="op-a",
            started_at=PINNED,
            finished_at=PINNED,
            failure_reason=VendorRefreshFailureReason.INTERNAL_ERROR,
        )
        assert child.result_schema_version is None
        assert child.result_payload is None

    def test_completed_without_payload_rejected(self) -> None:
        run = self._parent()
        with pytest.raises(IntegrityError):
            VendorRefreshExecution.objects.create(
                parent_run=run,
                requested_mpn=TEST_MPN,
                state=VendorRefreshState.COMPLETED,
                active_slot=None,
                trigger_source=VendorRefreshTriggerSource.MANAGEMENT_COMMAND,
                operator="op-a",
                started_at=PINNED,
                finished_at=PINNED,
                result_schema_version=1,
                # result_payload intentionally NULL
            )

    def test_completed_with_null_version_rejected(self) -> None:
        run = self._parent()
        with pytest.raises(IntegrityError):
            VendorRefreshExecution.objects.create(
                parent_run=run,
                requested_mpn=TEST_MPN,
                state=VendorRefreshState.COMPLETED,
                active_slot=None,
                trigger_source=VendorRefreshTriggerSource.MANAGEMENT_COMMAND,
                operator="op-a",
                started_at=PINNED,
                finished_at=PINNED,
                # result_schema_version intentionally NULL
                result_payload={"marker": "x"},
            )

    def test_completed_with_version_zero_rejected(self) -> None:
        run = self._parent()
        with pytest.raises(IntegrityError):
            VendorRefreshExecution.objects.create(
                parent_run=run,
                requested_mpn=TEST_MPN,
                state=VendorRefreshState.COMPLETED,
                active_slot=None,
                trigger_source=VendorRefreshTriggerSource.MANAGEMENT_COMMAND,
                operator="op-a",
                started_at=PINNED,
                finished_at=PINNED,
                result_schema_version=0,
                result_payload={"marker": "x"},
            )

    def test_running_with_result_rejected(self) -> None:
        run = self._parent()
        with pytest.raises(IntegrityError):
            VendorRefreshExecution.objects.create(
                parent_run=run,
                requested_mpn=TEST_MPN,
                state=VendorRefreshState.RUNNING,
                active_slot=1,
                trigger_source=VendorRefreshTriggerSource.MANAGEMENT_COMMAND,
                operator="op-a",
                started_at=PINNED,
                result_schema_version=1,
                result_payload={"marker": "x"},
            )

    def test_pending_with_started_at_rejected(self) -> None:
        run = self._parent()
        with pytest.raises(IntegrityError):
            VendorRefreshExecution.objects.create(
                parent_run=run,
                requested_mpn=TEST_MPN,
                state=VendorRefreshState.PENDING,
                active_slot=1,
                trigger_source=VendorRefreshTriggerSource.MANAGEMENT_COMMAND,
                operator="op-a",
                started_at=PINNED,
            )

    def test_terminal_completed_with_active_slot_rejected(self) -> None:
        run = self._parent()
        with pytest.raises(IntegrityError):
            VendorRefreshExecution.objects.create(
                parent_run=run,
                requested_mpn=TEST_MPN,
                state=VendorRefreshState.COMPLETED,
                active_slot=1,
                trigger_source=VendorRefreshTriggerSource.MANAGEMENT_COMMAND,
                operator="op-a",
                started_at=PINNED,
                finished_at=PINNED,
                result_schema_version=1,
                result_payload={"marker": "x"},
            )

    def test_terminal_failed_with_active_slot_rejected(self) -> None:
        run = self._parent()
        with pytest.raises(IntegrityError):
            VendorRefreshExecution.objects.create(
                parent_run=run,
                requested_mpn=TEST_MPN,
                state=VendorRefreshState.FAILED,
                active_slot=1,
                trigger_source=VendorRefreshTriggerSource.MANAGEMENT_COMMAND,
                operator="op-a",
                started_at=PINNED,
                finished_at=PINNED,
                failure_reason=VendorRefreshFailureReason.INTERNAL_ERROR,
            )

    def test_active_slot_two_rejected(self) -> None:
        run = self._parent()
        with pytest.raises(IntegrityError):
            VendorRefreshExecution.objects.create(
                parent_run=run,
                requested_mpn=TEST_MPN,
                state=VendorRefreshState.PENDING,
                active_slot=2,
                trigger_source=VendorRefreshTriggerSource.MANAGEMENT_COMMAND,
                operator="op-a",
            )

    def test_unknown_state_rejected(self) -> None:
        """The lifecycle-shape CHECK confines `state` to the vocabulary."""
        run = self._parent()
        with pytest.raises(IntegrityError):
            VendorRefreshExecution.objects.create(
                parent_run=run,
                requested_mpn=TEST_MPN,
                state="BOGUS",
                active_slot=1,
                trigger_source=VendorRefreshTriggerSource.MANAGEMENT_COMMAND,
                operator="op-a",
            )

    def test_empty_requested_mpn_rejected(self) -> None:
        run = self._parent()
        with pytest.raises(IntegrityError):
            VendorRefreshExecution.objects.create(
                parent_run=run,
                requested_mpn="",
                state=VendorRefreshState.PENDING,
                active_slot=1,
                trigger_source=VendorRefreshTriggerSource.MANAGEMENT_COMMAND,
                operator="op-a",
            )

    def test_empty_operator_rejected(self) -> None:
        run = self._parent()
        with pytest.raises(IntegrityError):
            VendorRefreshExecution.objects.create(
                parent_run=run,
                requested_mpn=TEST_MPN,
                state=VendorRefreshState.PENDING,
                active_slot=1,
                trigger_source=VendorRefreshTriggerSource.MANAGEMENT_COMMAND,
                operator="",
            )

    def test_invalid_trigger_source_rejected(self) -> None:
        run = self._parent()
        with pytest.raises(IntegrityError):
            VendorRefreshExecution.objects.create(
                parent_run=run,
                requested_mpn=TEST_MPN,
                state=VendorRefreshState.PENDING,
                active_slot=1,
                trigger_source="WEB_POST",
                operator="op-a",
            )

    def test_unknown_failure_reason_rejected(self) -> None:
        run = self._parent()
        with pytest.raises(IntegrityError):
            VendorRefreshExecution.objects.create(
                parent_run=run,
                requested_mpn=TEST_MPN,
                state=VendorRefreshState.FAILED,
                active_slot=None,
                trigger_source=VendorRefreshTriggerSource.MANAGEMENT_COMMAND,
                operator="op-a",
                started_at=PINNED,
                finished_at=PINNED,
                failure_reason="NOT_A_REAL_REASON",
            )

    def test_second_active_row_rejected(self) -> None:
        """UNIQUE(parent_run, active_slot): at most one active child."""
        run = self._parent()
        VendorRefreshExecution.objects.create(
            parent_run=run,
            requested_mpn=TEST_MPN,
            state=VendorRefreshState.PENDING,
            active_slot=1,
            trigger_source=VendorRefreshTriggerSource.MANAGEMENT_COMMAND,
            operator="op-a",
        )
        with pytest.raises(IntegrityError):
            VendorRefreshExecution.objects.create(
                parent_run=run,
                requested_mpn=TEST_MPN,
                state=VendorRefreshState.PENDING,
                active_slot=1,
                trigger_source=VendorRefreshTriggerSource.MANAGEMENT_COMMAND,
                operator="op-b",
            )

    def test_two_terminal_rows_allowed(self) -> None:
        """UNIQUE admits NULL active_slot: terminal history may grow."""
        run = self._parent()
        for reason in (
            VendorRefreshFailureReason.INTERNAL_ERROR,
            VendorRefreshFailureReason.VENDOR_LOOKUP_CONFIG_MISSING,
        ):
            VendorRefreshExecution.objects.create(
                parent_run=run,
                requested_mpn=TEST_MPN,
                state=VendorRefreshState.FAILED,
                active_slot=None,
                trigger_source=VendorRefreshTriggerSource.MANAGEMENT_COMMAND,
                operator="op-a",
                started_at=PINNED,
                finished_at=PINNED,
                failure_reason=reason,
            )
        assert (
            VendorRefreshExecution.objects.filter(parent_run=run).count() == 2
        )

    def test_direct_orm_update_can_bypass_the_cas_path(self) -> None:
        """DESIGN2-FU1 C6 — documented, not claimed against.

        A direct ``QuerySet.update()`` moving a PENDING row to a full
        COMPLETED shape succeeds at the database level: the lifecycle
        guarantee is application-level (the four CAS primitives are the
        only application write path). No claim is made that
        ``editable=False`` itself rejects arbitrary writes.
        """
        run = self._parent()
        child = _make_pending_child(run)
        VendorRefreshExecution.objects.filter(pk=child.pk).update(
            state=VendorRefreshState.COMPLETED,
            active_slot=None,
            started_at=PINNED,
            finished_at=PINNED,
            result_schema_version=1,
            result_payload=_valid_payload(),
        )
        child.refresh_from_db()
        assert child.state == VendorRefreshState.COMPLETED
        assert child.result_payload is not None


# ---------------------------------------------------------------------------
# TRIGGER — eligibility, capture, provenance
# ---------------------------------------------------------------------------


class TestTriggerEligibility(TestCase):
    """trigger_vendor_refresh eligibility and row content."""

    def test_creates_pending_child(self) -> None:
        run = _make_completed_run()
        child = trigger_vendor_refresh(run.id, operator="op-a")
        assert child.parent_run_id == run.id
        assert child.state == VendorRefreshState.PENDING
        assert child.active_slot == 1
        assert child.requested_mpn == TEST_MPN
        assert child.trigger_source == VendorRefreshTriggerSource.MANAGEMENT_COMMAND
        assert child.operator == "op-a"
        assert child.created_at is not None
        assert child.started_at is None
        assert child.finished_at is None
        assert child.result_schema_version is None
        assert child.result_payload is None
        assert child.failure_reason is None

    def test_mpn_captured_verbatim_no_rewrite(self) -> None:
        """The capture is the parent's field VERBATIM: no strip, no fix."""
        weird_mpn = "  MTD FDK  CC3 "
        request = ResearchRequest(manufacturer_part_number=weird_mpn, description="x")
        run = ResearchRun.objects.create_from_request(request)
        # create_from_request strips surrounding whitespace, so build the
        # anomalous parent row directly (a path only a privileged writer
        # could produce) and prove the trigger still copies it verbatim.
        ResearchRun.objects.filter(pk=run.pk).update(
            manufacturer_part_number=weird_mpn
        )
        run.refresh_from_db()
        run.transition_to(ResearchRunState.RUNNING)
        run.transition_to(ResearchRunState.COMPLETED)
        PriceIntelligenceSnapshot.objects.create(
            run=run,
            schema_version=1,
            payload={
                "request": {"manufacturer_part_number": weird_mpn, "description": "x"},
                "assessments": [],
                "buckets": [],
                "exclusions": [],
                "verification_status": "VERIFIED",
            },
        )
        child = trigger_vendor_refresh(run.id, operator="op-a")
        assert child.requested_mpn == weird_mpn

    def test_operator_recorded_verbatim(self) -> None:
        run = _make_completed_run()
        child = trigger_vendor_refresh(run.id, operator="opé-ratör #7 (shared admin)")
        assert child.operator == "opé-ratör #7 (shared admin)"

    def test_rejects_parent_not_found(self) -> None:
        with pytest.raises(VendorRefreshTriggerError) as exc_info:
            trigger_vendor_refresh(uuid.uuid4(), operator="op-a")
        assert exc_info.value.reason == VendorRefreshTriggerError.REASON_PARENT_NOT_FOUND

    def test_rejects_parent_created(self) -> None:
        request = ResearchRequest(manufacturer_part_number=TEST_MPN, description="x")
        run = ResearchRun.objects.create_from_request(request)
        with pytest.raises(VendorRefreshTriggerError) as exc_info:
            trigger_vendor_refresh(run.id, operator="op-a")
        assert exc_info.value.reason == VendorRefreshTriggerError.REASON_PARENT_NOT_COMPLETED

    def test_rejects_parent_running(self) -> None:
        run = _make_run_in_state(ResearchRunState.RUNNING)
        with pytest.raises(VendorRefreshTriggerError) as exc_info:
            trigger_vendor_refresh(run.id, operator="op-a")
        assert exc_info.value.reason == VendorRefreshTriggerError.REASON_PARENT_NOT_COMPLETED

    def test_rejects_parent_failed(self) -> None:
        run = _make_run_in_state(ResearchRunState.FAILED)
        with pytest.raises(VendorRefreshTriggerError) as exc_info:
            trigger_vendor_refresh(run.id, operator="op-a")
        assert exc_info.value.reason == VendorRefreshTriggerError.REASON_PARENT_NOT_COMPLETED

    def test_rejects_parent_partially_completed(self) -> None:
        run = _make_run_in_state(ResearchRunState.PARTIALLY_COMPLETED)
        with pytest.raises(VendorRefreshTriggerError) as exc_info:
            trigger_vendor_refresh(run.id, operator="op-a")
        assert exc_info.value.reason == VendorRefreshTriggerError.REASON_PARENT_NOT_COMPLETED

    def test_rejects_completed_without_snapshot(self) -> None:
        run = _make_run_in_state(ResearchRunState.COMPLETED)
        with pytest.raises(VendorRefreshTriggerError) as exc_info:
            trigger_vendor_refresh(run.id, operator="op-a")
        assert exc_info.value.reason == VendorRefreshTriggerError.REASON_NO_SNAPSHOT

    def test_rejects_description_only_run(self) -> None:
        """A description-only COMPLETED run has no canonical MPN to refresh."""
        request = ResearchRequest(manufacturer_part_number="", description="desc only")
        run = ResearchRun.objects.create_from_request(request)
        run.transition_to(ResearchRunState.RUNNING)
        run.transition_to(ResearchRunState.COMPLETED)
        PriceIntelligenceSnapshot.objects.create(
            run=run,
            schema_version=1,
            payload={
                "request": {"manufacturer_part_number": "", "description": "desc only"},
                "assessments": [],
                "buckets": [],
                "exclusions": [],
                "verification_status": "VERIFIED",
            },
        )
        with pytest.raises(VendorRefreshTriggerError) as exc_info:
            trigger_vendor_refresh(run.id, operator="op-a")
        assert exc_info.value.reason == VendorRefreshTriggerError.REASON_NO_MPN

    def test_allows_missing_original_supplement_snapshot(self) -> None:
        """Absence of the original vendor snapshot is NOT an error (§8.4)."""
        run = _make_completed_run()
        assert not ResearchSupplementSnapshot.objects.filter(run=run).exists()
        child = trigger_vendor_refresh(run.id, operator="op-a")
        assert child.state == VendorRefreshState.PENDING

    def test_allows_existing_original_supplement_snapshot(self) -> None:
        run = _make_completed_run()
        ResearchSupplementSnapshot.objects.create(
            run=run,
            schema_version=1,
            payload=_valid_payload(lookup_status="FAILED", with_observation=False),
        )
        child = trigger_vendor_refresh(run.id, operator="op-a")
        assert child.state == VendorRefreshState.PENDING
        assert child.requested_mpn == TEST_MPN

    def test_rejects_empty_operator(self) -> None:
        run = _make_completed_run()
        with pytest.raises(VendorRefreshTriggerError) as exc_info:
            trigger_vendor_refresh(run.id, operator="")
        assert exc_info.value.reason == VendorRefreshTriggerError.REASON_INVALID_OPERATOR
        assert VendorRefreshExecution.objects.count() == 0

    def test_rejects_non_string_operator(self) -> None:
        run = _make_completed_run()
        with pytest.raises(VendorRefreshTriggerError) as exc_info:
            trigger_vendor_refresh(run.id, operator=42)  # type: ignore[arg-type]
        assert exc_info.value.reason == VendorRefreshTriggerError.REASON_INVALID_OPERATOR
        assert VendorRefreshExecution.objects.count() == 0

    def test_rejects_unknown_trigger_source(self) -> None:
        run = _make_completed_run()
        with pytest.raises(VendorRefreshTriggerError) as exc_info:
            trigger_vendor_refresh(
                run.id, operator="op-a", trigger_source="SCHEDULER"
            )
        assert (
            exc_info.value.reason == VendorRefreshTriggerError.REASON_INVALID_TRIGGER_SOURCE
        )
        assert VendorRefreshExecution.objects.count() == 0

    def test_string_uuid_accepted(self) -> None:
        run = _make_completed_run()
        child = trigger_vendor_refresh(str(run.id), operator="op-a")
        assert child.parent_run_id == run.id

    def test_ineligible_trigger_creates_no_row(self) -> None:
        run = _make_run_in_state(ResearchRunState.RUNNING)
        with pytest.raises(VendorRefreshTriggerError):
            trigger_vendor_refresh(run.id, operator="op-a")
        assert VendorRefreshExecution.objects.count() == 0


# ---------------------------------------------------------------------------
# TRIGGER — idempotency and the insert race
# ---------------------------------------------------------------------------


class TestTriggerIdempotencyAndRace(TestCase):
    """Concept 1 (active dedup), concept 2 (post-terminal new attempt),
    and the UNIQUE(parent_run, active_slot) race behavior."""

    def test_double_trigger_returns_same_pending_one_row(self) -> None:
        run = _make_completed_run()
        c1 = trigger_vendor_refresh(run.id, operator="op-a")
        c2 = trigger_vendor_refresh(run.id, operator="op-b")
        assert c1.id == c2.id
        assert VendorRefreshExecution.objects.filter(parent_run=run).count() == 1
        # The second invocation neither transfers nor re-attests provenance.
        c2.refresh_from_db()
        assert c2.operator == "op-a"

    def test_trigger_over_stuck_running_returns_existing_row(self) -> None:
        """A RUNNING child occupies its slot; the trigger reports it."""
        run = _make_completed_run()
        child = _make_running_child(run)
        returned = trigger_vendor_refresh(run.id, operator="op-b")
        assert returned.id == child.id
        assert returned.state == VendorRefreshState.RUNNING
        assert VendorRefreshExecution.objects.filter(parent_run=run).count() == 1

    def test_terminal_failed_history_does_not_block_new_attempt(self) -> None:
        run = _make_completed_run()
        c1 = _make_running_child(run, operator="op-a")
        fail_vendor_refresh(c1.id, VendorRefreshFailureReason.INTERNAL_ERROR)
        c1.refresh_from_db()
        assert c1.state == VendorRefreshState.FAILED
        c2 = trigger_vendor_refresh(run.id, operator="op-b")
        assert c2.id != c1.id
        assert c2.state == VendorRefreshState.PENDING
        assert VendorRefreshExecution.objects.filter(parent_run=run).count() == 2
        # Append-only: the first child is untouched.
        c1.refresh_from_db()
        assert c1.state == VendorRefreshState.FAILED
        assert c1.operator == "op-a"

    def test_terminal_completed_history_does_not_block_new_attempt(self) -> None:
        run = _make_completed_run()
        c1 = _make_running_child(run)
        complete_vendor_refresh(c1.id, 1, _valid_payload())
        c1.refresh_from_db()
        assert c1.state == VendorRefreshState.COMPLETED
        c2 = trigger_vendor_refresh(run.id, operator="op-b")
        assert c2.id != c1.id
        assert c2.state == VendorRefreshState.PENDING
        assert VendorRefreshExecution.objects.filter(parent_run=run).count() == 2

    def test_insert_race_returns_active_winner(self) -> None:
        """UNIQUE fires for the loser; the savepoint rolls back; the
        existing active winner is returned."""
        run = _make_completed_run()
        winner = _make_pending_child(run, operator="winner-op")

        create_called = [False]
        orig_filter = VendorRefreshExecution.objects.filter
        call_n = [0]

        def mock_create(*a, **kw):
            create_called[0] = True
            raise IntegrityError("unique constraint violation")

        def mock_filter(*a, **kw):
            if "state__in" in kw:
                call_n[0] += 1
                if call_n[0] == 1:
                    # Bypass the optimistic pre-check so the create() path
                    # and the recovery branch both execute.
                    return VendorRefreshExecution.objects.none()
            return orig_filter(*a, **kw)

        with patch.object(VendorRefreshExecution.objects, "create", mock_create):
            with patch.object(VendorRefreshExecution.objects, "filter", mock_filter):
                result = trigger_vendor_refresh(run.id, operator="loser-op")

        assert create_called[0]
        assert result.id == winner.id
        assert result.state == VendorRefreshState.PENDING
        assert result.operator == "winner-op"
        assert VendorRefreshExecution.objects.filter(parent_run=run).count() == 1

    def test_insert_race_returns_running_winner(self) -> None:
        run = _make_completed_run()
        winner = _make_running_child(run, operator="winner-op")

        create_called = [False]
        orig_filter = VendorRefreshExecution.objects.filter
        call_n = [0]

        def mock_create(*a, **kw):
            create_called[0] = True
            raise IntegrityError("unique constraint violation")

        def mock_filter(*a, **kw):
            if "state__in" in kw:
                call_n[0] += 1
                if call_n[0] == 1:
                    return VendorRefreshExecution.objects.none()
            return orig_filter(*a, **kw)

        with patch.object(VendorRefreshExecution.objects, "create", mock_create):
            with patch.object(VendorRefreshExecution.objects, "filter", mock_filter):
                result = trigger_vendor_refresh(run.id, operator="loser-op")

        assert create_called[0]
        assert result.id == winner.id
        assert result.state == VendorRefreshState.RUNNING

    def test_unrelated_integrityerror_propagates(self) -> None:
        """No active winner after the IntegrityError: the ORIGINAL error
        propagates (it is not converted to a trigger error)."""
        run = _make_completed_run()

        def mock_create(*a, **kw):
            raise IntegrityError("simulated unrelated integrity error")

        with patch.object(VendorRefreshExecution.objects, "create", mock_create):
            with pytest.raises(IntegrityError, match="simulated unrelated"):
                trigger_vendor_refresh(run.id, operator="op-a")

    def test_unrelated_integrityerror_not_wrapped(self) -> None:
        run = _make_completed_run()

        def mock_create(*a, **kw):
            raise IntegrityError("database constraint violation")

        with patch.object(VendorRefreshExecution.objects, "create", mock_create):
            with pytest.raises(IntegrityError):
                trigger_vendor_refresh(run.id, operator="op-a")
        with pytest.raises(IntegrityError):
            # and it is specifically NOT a VendorRefreshTriggerError
            try:
                with patch.object(
                    VendorRefreshExecution.objects, "create", mock_create
                ):
                    trigger_vendor_refresh(run.id, operator="op-a")
            except VendorRefreshTriggerError:
                pytest.fail("unrelated IntegrityError was wrapped")


# ---------------------------------------------------------------------------
# CLAIM — CAS PENDING -> RUNNING
# ---------------------------------------------------------------------------


class TestClaimCas(TestCase):
    """claim_vendor_refresh: one conditional UPDATE, one winner."""

    def test_claims_pending_to_running(self) -> None:
        run = _make_completed_run()
        child = _make_pending_child(run)
        claimed = claim_vendor_refresh(child.id)
        assert claimed.state == VendorRefreshState.RUNNING
        assert claimed.active_slot == 1
        assert claimed.started_at is not None
        assert claimed.finished_at is None
        assert claimed.result_payload is None

    def test_double_claim_single_winner(self) -> None:
        """The second claimer loses: bounded error, zero mutation — the
        winner's started_at is not overwritten."""
        run = _make_completed_run()
        child = _make_pending_child(run)
        winner = claim_vendor_refresh(child.id)
        before = _row_snapshot(child.pk)
        with pytest.raises(VendorRefreshClaimError):
            claim_vendor_refresh(child.id)
        assert _row_snapshot(child.pk) == before
        assert before["state"] == VendorRefreshState.RUNNING
        assert before["started_at"] is not None

    def test_claim_rejects_completed_child(self) -> None:
        run = _make_completed_run()
        child = _make_running_child(run)
        complete_vendor_refresh(child.id, 1, _valid_payload())
        with pytest.raises(VendorRefreshClaimError):
            claim_vendor_refresh(child.id)

    def test_claim_rejects_failed_child(self) -> None:
        run = _make_completed_run()
        child = _make_running_child(run)
        fail_vendor_refresh(child.id, VendorRefreshFailureReason.INTERNAL_ERROR)
        with pytest.raises(VendorRefreshClaimError):
            claim_vendor_refresh(child.id)

    def test_claim_rejects_nonexistent_child(self) -> None:
        with pytest.raises(VendorRefreshClaimError):
            claim_vendor_refresh(uuid.uuid4())

    def test_claim_does_not_modify_operator_or_binding(self) -> None:
        run = _make_completed_run()
        child = trigger_vendor_refresh(run.id, operator="trigger-initiator")
        before = _row_snapshot(child.pk)
        claim_vendor_refresh(child.id)
        after = _row_snapshot(child.pk)
        assert after["operator"] == before["operator"] == "trigger-initiator"
        assert after["requested_mpn"] == before["requested_mpn"] == TEST_MPN
        assert after["trigger_source"] == VendorRefreshTriggerSource.MANAGEMENT_COMMAND
        assert after["created_at"] == before["created_at"]


# ---------------------------------------------------------------------------
# COMPLETE — CAS RUNNING -> COMPLETED with atomic result publication
# ---------------------------------------------------------------------------


class TestCompleteCas(TestCase):
    """complete_vendor_refresh: pre-mutation codec validation, then one
    atomic UPDATE publishing state + slot + timestamp + version + payload."""

    def test_completes_running(self) -> None:
        run = _make_completed_run()
        child = _make_running_child(run)
        payload = _valid_payload()
        completed = complete_vendor_refresh(child.id, 1, payload, at=PINNED)
        assert completed.state == VendorRefreshState.COMPLETED
        assert completed.active_slot is None
        assert completed.started_at is not None
        assert completed.finished_at == PINNED
        assert completed.result_schema_version == 1
        assert completed.result_payload == payload
        assert completed.failure_reason is None

    def test_atomic_completed_payload_publication(self) -> None:
        """After the single UPDATE, a fresh database read shows the
        complete terminal shape at once: there is no committed state in
        which a COMPLETED child lacks its payload (also structurally
        impossible — see TestModelLifecycleShapes)."""
        run = _make_completed_run()
        child = _make_running_child(run)
        payload = _valid_payload()
        complete_vendor_refresh(child.id, 1, payload)
        fresh = VendorRefreshExecution.objects.get(pk=child.pk)
        assert fresh.state == VendorRefreshState.COMPLETED
        assert fresh.active_slot is None
        assert fresh.finished_at is not None
        assert fresh.result_schema_version == 1
        assert fresh.result_payload == payload

    def test_stored_payload_round_trips_frozen_codec(self) -> None:
        run = _make_completed_run()
        child = _make_running_child(run)
        complete_vendor_refresh(child.id, 1, _valid_payload())
        fresh = VendorRefreshExecution.objects.get(pk=child.pk)
        decoded = decode_research_supplement_result(fresh.result_payload)
        assert (
            decoded.vendor_commercial_result.lookup_status == "SUCCESS"
        )

    def test_complete_rejects_pending_child(self) -> None:
        run = _make_completed_run()
        child = _make_pending_child(run)
        with pytest.raises(VendorRefreshCompletionError):
            complete_vendor_refresh(child.id, 1, _valid_payload())

    def test_complete_rejects_nonexistent_child(self) -> None:
        with pytest.raises(VendorRefreshCompletionError):
            complete_vendor_refresh(uuid.uuid4(), 1, _valid_payload())

    def test_rejects_wrong_version_before_mutation(self) -> None:
        """version != frozen V1: rejected BEFORE the UPDATE; zero mutation."""
        run = _make_completed_run()
        child = _make_running_child(run)
        before = _row_snapshot(child.pk)
        with pytest.raises(VendorRefreshCompletionError) as exc_info:
            complete_vendor_refresh(child.id, 2, _valid_payload())
        assert (
            exc_info.value.reason
            == VendorRefreshCompletionError.REASON_INVALID_SCHEMA_VERSION
        )
        assert _row_snapshot(child.pk) == before

    def test_rejects_zero_version_before_mutation(self) -> None:
        run = _make_completed_run()
        child = _make_running_child(run)
        before = _row_snapshot(child.pk)
        with pytest.raises(VendorRefreshCompletionError) as exc_info:
            complete_vendor_refresh(child.id, 0, _valid_payload())
        assert (
            exc_info.value.reason
            == VendorRefreshCompletionError.REASON_INVALID_SCHEMA_VERSION
        )
        assert _row_snapshot(child.pk) == before

    def test_rejects_bool_version_before_mutation(self) -> None:
        """bool is not accepted as an int version (True == 1 trap)."""
        run = _make_completed_run()
        child = _make_running_child(run)
        before = _row_snapshot(child.pk)
        with pytest.raises(VendorRefreshCompletionError) as exc_info:
            complete_vendor_refresh(child.id, True, _valid_payload())  # type: ignore[arg-type]
        assert (
            exc_info.value.reason
            == VendorRefreshCompletionError.REASON_INVALID_SCHEMA_VERSION
        )
        assert _row_snapshot(child.pk) == before

    def test_rejects_non_int_version_before_mutation(self) -> None:
        run = _make_completed_run()
        child = _make_running_child(run)
        before = _row_snapshot(child.pk)
        with pytest.raises(VendorRefreshCompletionError) as exc_info:
            complete_vendor_refresh(child.id, "1", _valid_payload())  # type: ignore[arg-type]
        assert (
            exc_info.value.reason
            == VendorRefreshCompletionError.REASON_INVALID_SCHEMA_VERSION
        )
        assert _row_snapshot(child.pk) == before

    def test_rejects_payload_with_unsupported_schema_version(self) -> None:
        """Stored version 1 vs a payload claiming codec version 2:
        the payload does not carry the frozen V1, rejected before the
        UPDATE; zero mutation."""
        run = _make_completed_run()
        child = _make_running_child(run)
        before = _row_snapshot(child.pk)
        bad_payload = _valid_payload()
        bad_payload["schema_version"] = 2
        with pytest.raises(VendorRefreshCompletionError) as exc_info:
            complete_vendor_refresh(child.id, 1, bad_payload)
        assert (
            exc_info.value.reason == VendorRefreshCompletionError.REASON_INVALID_PAYLOAD
        )
        assert _row_snapshot(child.pk) == before

    def test_rejects_payload_missing_schema_version(self) -> None:
        """A payload without the codec's top-level schema_version key is
        not a frozen-codec payload: rejected before the UPDATE."""
        run = _make_completed_run()
        child = _make_running_child(run)
        before = _row_snapshot(child.pk)
        bad_payload = _valid_payload()
        del bad_payload["schema_version"]
        with pytest.raises(VendorRefreshCompletionError) as exc_info:
            complete_vendor_refresh(child.id, 1, bad_payload)
        assert (
            exc_info.value.reason == VendorRefreshCompletionError.REASON_INVALID_PAYLOAD
        )
        assert _row_snapshot(child.pk) == before

    def test_rejects_non_int_payload_schema_version(self) -> None:
        run = _make_completed_run()
        child = _make_running_child(run)
        before = _row_snapshot(child.pk)
        bad_payload = _valid_payload()
        bad_payload["schema_version"] = "1"
        with pytest.raises(VendorRefreshCompletionError) as exc_info:
            complete_vendor_refresh(child.id, 1, bad_payload)
        assert (
            exc_info.value.reason == VendorRefreshCompletionError.REASON_INVALID_PAYLOAD
        )
        assert _row_snapshot(child.pk) == before

    def test_agreement_rejects_stored_version_mismatch_direction(self) -> None:
        """Both directions of a disagreement are rejected: stored 2 vs a
        V1 payload (version check) and stored 1 vs a non-V1 payload
        (agreement check) — no malformed COMPLETED row in either case."""
        run = _make_completed_run()
        child = _make_running_child(run)
        before = _row_snapshot(child.pk)
        v1_payload = _valid_payload()
        with pytest.raises(VendorRefreshCompletionError):
            complete_vendor_refresh(child.id, 2, v1_payload)
        assert _row_snapshot(child.pk) == before
        v2_payload = _valid_payload()
        v2_payload["schema_version"] = 2
        with pytest.raises(VendorRefreshCompletionError):
            complete_vendor_refresh(child.id, 1, v2_payload)
        assert _row_snapshot(child.pk) == before

    def test_full_codec_validity_is_producer_and_reader_job(self) -> None:
        """DESIGN2 §3.1 boundary, pinned: the complete service enforces
        the bounded version agreement at the dict level (the runs layer
        imports no research code — the architecture guards pin it). Full
        frozen-codec validity of the payload internals is enforced by the
        producer (the frozen encoder, before the complete CAS in R1)
        and by the reader (the frozen decoder in history replay, failing
        closed in R2). A version-agreeing payload with malformed
        internals therefore passes the complete service's bounded check,
        and the frozen decoder rejects it on read."""
        run = _make_completed_run()
        child = _make_running_child(run)
        corrupted = _valid_payload()
        del corrupted["vendor_commercial_result"]
        # The bounded agreement check sees schema_version == 1 == stored.
        completed = complete_vendor_refresh(child.id, 1, corrupted)
        assert completed.state == VendorRefreshState.COMPLETED
        # ...and the frozen reader fails closed on it (no numeric
        # fabrication; the affected row is rendered unreadable in R2).
        with pytest.raises(SupplementCodecError):
            decode_research_supplement_result(completed.result_payload)

    def test_rejects_non_dict_payload_before_mutation(self) -> None:
        run = _make_completed_run()
        child = _make_running_child(run)
        before = _row_snapshot(child.pk)
        with pytest.raises(VendorRefreshCompletionError) as exc_info:
            complete_vendor_refresh(child.id, 1, "not-a-dict")  # type: ignore[arg-type]
        assert (
            exc_info.value.reason == VendorRefreshCompletionError.REASON_INVALID_PAYLOAD
        )
        assert _row_snapshot(child.pk) == before

    def test_failed_lookup_payload_is_a_valid_completion(self) -> None:
        """An executed lookup with a FAILED result COMPLETES the child
        (4D-B semantics): the payload carries lookup_status=FAILED."""
        run = _make_completed_run()
        child = _make_running_child(run)
        payload = _valid_payload(lookup_status="FAILED", with_observation=False)
        completed = complete_vendor_refresh(child.id, 1, payload)
        assert completed.state == VendorRefreshState.COMPLETED
        assert (
            completed.result_payload["vendor_commercial_result"]["lookup_status"]
            == "FAILED"
        )


# ---------------------------------------------------------------------------
# FAIL — CAS RUNNING -> FAILED with a validated bounded reason
# ---------------------------------------------------------------------------


class TestFailCas(TestCase):
    """fail_vendor_refresh: reason validated BEFORE any UPDATE, then one
    atomic UPDATE to the terminal FAILED shape."""

    def test_fails_running(self) -> None:
        run = _make_completed_run()
        child = _make_running_child(run)
        failed = fail_vendor_refresh(
            child.id,
            VendorRefreshFailureReason.VENDOR_LOOKUP_CONFIG_MISSING,
            at=PINNED,
        )
        assert failed.state == VendorRefreshState.FAILED
        assert failed.active_slot is None
        assert failed.started_at is not None
        assert failed.finished_at == PINNED
        assert failed.result_schema_version is None
        assert failed.result_payload is None
        assert (
            failed.failure_reason
            == VendorRefreshFailureReason.VENDOR_LOOKUP_CONFIG_MISSING
        )

    def test_all_non_reserved_reasons_accepted(self) -> None:
        """No over-rejection: every other bounded reason remains legal."""
        for reason in sorted(VendorRefreshFailureReason.R0_LEGAL):
            with self.subTest(reason=reason):
                run = _make_completed_run()
                child = _make_running_child(run)
                failed = fail_vendor_refresh(child.id, reason)
                assert failed.state == VendorRefreshState.FAILED
                assert failed.failure_reason == reason

    def test_r0_legal_reasons_are_exactly_the_five_non_reserved(self) -> None:
        assert VendorRefreshFailureReason.R0_LEGAL == (
            VendorRefreshFailureReason.ALL
            - {VendorRefreshFailureReason.EXECUTION_INTERRUPTED}
        )
        assert len(VendorRefreshFailureReason.R0_LEGAL) == 5

    def test_fail_rejects_pending_child(self) -> None:
        run = _make_completed_run()
        child = _make_pending_child(run)
        before = _row_snapshot(child.pk)
        with pytest.raises(VendorRefreshFailureError):
            fail_vendor_refresh(child.id, VendorRefreshFailureReason.INTERNAL_ERROR)
        assert _row_snapshot(child.pk) == before

    def test_fail_rejects_nonexistent_child(self) -> None:
        with pytest.raises(VendorRefreshFailureError):
            fail_vendor_refresh(
                uuid.uuid4(), VendorRefreshFailureReason.INTERNAL_ERROR
            )

    def test_rejects_unknown_reason_before_mutation(self) -> None:
        run = _make_completed_run()
        child = _make_running_child(run)
        before = _row_snapshot(child.pk)
        with pytest.raises(VendorRefreshFailureError) as exc_info:
            fail_vendor_refresh(child.id, "NOT_A_REAL_REASON")
        assert (
            exc_info.value.reason
            == VendorRefreshFailureError.REASON_INVALID_FAILURE_REASON
        )
        assert _row_snapshot(child.pk) == before

    def test_rejects_reserved_execution_interrupted_on_valid_running_row(self) -> None:
        """DESIGN2-FU3 F1 — over a row whose FULL CAS preconditions hold,
        the reserved reason is rejected with ZERO row mutation."""
        run = _make_completed_run()
        child = _make_running_child(run)
        before = _row_snapshot(child.pk)
        assert before["state"] == VendorRefreshState.RUNNING
        assert before["active_slot"] == 1
        assert before["finished_at"] is None
        with pytest.raises(VendorRefreshFailureError) as exc_info:
            fail_vendor_refresh(
                child.id, VendorRefreshFailureReason.EXECUTION_INTERRUPTED
            )
        assert (
            exc_info.value.reason
            == VendorRefreshFailureError.REASON_RESERVED_EXECUTION_INTERRUPTED
        )
        after = _row_snapshot(child.pk)
        assert after == before
        assert after["state"] == VendorRefreshState.RUNNING
        assert after["failure_reason"] is None
        assert after["active_slot"] == 1
        assert after["finished_at"] is None

    def test_reserved_rejection_issues_no_db_statement(self) -> None:
        """The rejection happens BEFORE any UPDATE — in fact before any
        database statement: the CAS filter query and the conditional
        update are both provably never issued."""
        run = _make_completed_run()
        child = _make_running_child(run)
        filter_calls = [0]
        update_calls = [0]
        orig_filter = VendorRefreshExecution.objects.filter

        def spy_filter(*a, **kw):
            filter_calls[0] += 1
            qs = orig_filter(*a, **kw)
            orig_update = qs.update

            def spy_update(*ua, **ukw):
                update_calls[0] += 1
                return orig_update(*ua, **ukw)

            qs.update = spy_update
            return qs

        with patch.object(VendorRefreshExecution.objects, "filter", spy_filter):
            with pytest.raises(VendorRefreshFailureError):
                fail_vendor_refresh(
                    child.id, VendorRefreshFailureReason.EXECUTION_INTERRUPTED
                )
        assert filter_calls[0] == 0
        assert update_calls[0] == 0
        child.refresh_from_db()
        assert child.state == VendorRefreshState.RUNNING
        assert child.failure_reason is None

    def test_reserved_reason_still_representable_in_database(self) -> None:
        """The storage constraint ADMITS the reserved value: a direct
        terminal write with EXECUTION_INTERRUPTED passes the CHECKs —
        proving the rejection lives in the R0 service, not the schema,
        and the future R1 recovery transition needs no schema change."""
        run = _make_completed_run()
        child = _make_pending_child(run)
        VendorRefreshExecution.objects.filter(pk=child.pk).update(
            state=VendorRefreshState.FAILED,
            active_slot=None,
            started_at=PINNED,
            finished_at=PINNED,
            failure_reason=VendorRefreshFailureReason.EXECUTION_INTERRUPTED,
        )
        child.refresh_from_db()
        assert child.state == VendorRefreshState.FAILED
        assert child.failure_reason == VendorRefreshFailureReason.EXECUTION_INTERRUPTED


# ---------------------------------------------------------------------------
# Terminalization — single winner, zero-mutation duplicates
# ---------------------------------------------------------------------------


class TestTerminalizationSingleWinner(TestCase):
    """Rows 3–4 of the R0 state-transition table: at most one terminal
    write commits per row (atomic single-winner terminalization). The CAS
    does NOT authenticate the issuer as the claim winner (DESIGN2-FU3
    F2); no ownership is claimed here."""

    def test_complete_then_fail_rejected_zero_mutation(self) -> None:
        run = _make_completed_run()
        child = _make_running_child(run)
        complete_vendor_refresh(child.id, 1, _valid_payload(), at=PINNED)
        before = _row_snapshot(child.pk)
        with pytest.raises(VendorRefreshFailureError):
            fail_vendor_refresh(
                child.id, VendorRefreshFailureReason.INTERNAL_ERROR, at=PINNED
            )
        assert _row_snapshot(child.pk) == before

    def test_fail_then_complete_rejected_zero_mutation(self) -> None:
        run = _make_completed_run()
        child = _make_running_child(run)
        fail_vendor_refresh(
            child.id, VendorRefreshFailureReason.INTERNAL_ERROR, at=PINNED
        )
        before = _row_snapshot(child.pk)
        with pytest.raises(VendorRefreshCompletionError):
            complete_vendor_refresh(child.id, 1, _valid_payload(), at=PINNED)
        assert _row_snapshot(child.pk) == before

    def test_duplicate_complete_rejected_zero_mutation(self) -> None:
        run = _make_completed_run()
        child = _make_running_child(run)
        complete_vendor_refresh(child.id, 1, _valid_payload(), at=PINNED)
        before = _row_snapshot(child.pk)
        with pytest.raises(VendorRefreshCompletionError):
            complete_vendor_refresh(child.id, 1, _valid_payload(), at=PINNED)
        assert _row_snapshot(child.pk) == before

    def test_duplicate_fail_rejected_zero_mutation(self) -> None:
        run = _make_completed_run()
        child = _make_running_child(run)
        fail_vendor_refresh(
            child.id, VendorRefreshFailureReason.INTERNAL_ERROR, at=PINNED
        )
        before = _row_snapshot(child.pk)
        with pytest.raises(VendorRefreshFailureError):
            fail_vendor_refresh(
                child.id, VendorRefreshFailureReason.INTERNAL_ERROR, at=PINNED
            )
        assert _row_snapshot(child.pk) == before

    def test_terminalized_row_frees_the_active_slot(self) -> None:
        run = _make_completed_run()
        child = _make_running_child(run)
        fail_vendor_refresh(child.id, VendorRefreshFailureReason.INTERNAL_ERROR)
        new_child = trigger_vendor_refresh(run.id, operator="op-2")
        assert new_child.id != child.id
        assert new_child.state == VendorRefreshState.PENDING

    def test_terminal_state_rejects_every_primitive(self) -> None:
        run = _make_completed_run()
        child = _make_running_child(run)
        complete_vendor_refresh(child.id, 1, _valid_payload())
        with pytest.raises(VendorRefreshClaimError):
            claim_vendor_refresh(child.id)
        with pytest.raises(VendorRefreshCompletionError):
            complete_vendor_refresh(child.id, 1, _valid_payload())
        with pytest.raises(VendorRefreshFailureError):
            fail_vendor_refresh(child.id, VendorRefreshFailureReason.INTERNAL_ERROR)


# ---------------------------------------------------------------------------
# R0 surface absence — no recovery, no retry, no R1 surface
# ---------------------------------------------------------------------------


_FORBIDDEN_SURFACE_TOKENS = (
    "reclaim",
    "reset",
    "retry",
    "recover",
    "recovery",
    "force",
    "stale",
    "reassign",
    "resurrect",
    "interrupt",
)


class TestNoRecoverySurface(TestCase):
    """The R0 service surface is EXACTLY the four primitives. Nothing
    reclaims, resets, retries, recovers, or reassigns a RUNNING attempt,
    and the R1 command/execution surfaces do not exist yet."""

    def test_service_module_exposes_exactly_four_primitives(self) -> None:
        from product_intelligence.runs import vendor_refresh_claims

        assert vendor_refresh_claims.__all__ == [
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
        public_functions = {
            name
            for name, obj in vars(vendor_refresh_claims).items()
            if not name.startswith("_")
            and callable(obj)
            and getattr(obj, "__module__", None)
            == "product_intelligence.runs.vendor_refresh_claims"
        }
        assert public_functions == {
            "trigger_vendor_refresh",
            "claim_vendor_refresh",
            "complete_vendor_refresh",
            "fail_vendor_refresh",
        }

    def test_module_defines_no_recovery_functions(self) -> None:
        """AST-pinned: no function in the module carries a
        recovery/retry/reset/reclaim/force token (or any R1 primitive)."""
        from pathlib import Path

        from product_intelligence.runs import vendor_refresh_claims

        path = Path(vendor_refresh_claims.__file__)
        tree = ast.parse(path.read_text(encoding="utf-8"))
        func_names = [
            node.name
            for node in ast.walk(tree)
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
        ]
        for name in func_names:
            lowered = name.lower()
            assert not any(
                token in lowered for token in _FORBIDDEN_SURFACE_TOKENS
            ), f"forbidden R0 surface function: {name}"
        # The four primitives are the only public callables (no helpers
        # may grow into a fifth surface).
        assert sorted(n for n in func_names if not n.startswith("_")) == [
            "claim_vendor_refresh",
            "complete_vendor_refresh",
            "fail_vendor_refresh",
            "trigger_vendor_refresh",
        ]

    def test_public_api_has_no_vendor_refresh_recovery_symbols(self) -> None:
        import product_intelligence.runs as runs_pkg

        for name in runs_pkg.__all__:
            lowered = name.lower()
            if "vendor" not in lowered:
                continue
            assert not any(
                token in lowered for token in _FORBIDDEN_SURFACE_TOKENS
            ), f"forbidden R0 public symbol: {name}"

    def test_no_vendor_refresh_management_command_exists(self) -> None:
        """R0 ships no command surface (the vendor_refresh command is
        R1): no such command file exists in the runs package."""
        from pathlib import Path

        commands_root = Path(
            "product_intelligence/runs/management/commands"
        ).resolve()
        if commands_root.is_dir():
            assert not list(commands_root.glob("vendor_refresh*"))

    def test_no_vendor_refresh_execution_module_exists(self) -> None:
        """R0 ships no execution/runtime surface (R1): no such module in
        the execution package, and nothing network-capable was added."""
        from pathlib import Path

        execution_root = Path("product_intelligence/execution").resolve()
        assert not list(execution_root.glob("vendor_refresh*.py"))

    def test_no_implicit_retry_after_failure(self) -> None:
        """Nothing revives or re-attempts a FAILED child: row count is
        stable and the row keeps its terminal shape without a new
        explicit trigger."""
        run = _make_completed_run()
        child = _make_running_child(run)
        fail_vendor_refresh(child.id, VendorRefreshFailureReason.INTERNAL_ERROR)
        count_before = VendorRefreshExecution.objects.filter(parent_run=run).count()
        # Re-assert the terminal row is inert: no primitive moves it.
        with pytest.raises(VendorRefreshClaimError):
            claim_vendor_refresh(child.id)
        assert (
            VendorRefreshExecution.objects.filter(parent_run=run).count()
            == count_before
        )
        child.refresh_from_db()
        assert child.state == VendorRefreshState.FAILED

    def test_stuck_running_cannot_be_forced_terminal(self) -> None:
        """A stuck RUNNING row (claim committed, no complete/fail issued)
        stays RUNNING and occupies its slot; NO R0 path terminalizes it.
        Trigger reports it; claim rejects it; only the (absent-in-R0)
        execution's own complete/fail CAS could terminate it."""
        run = _make_completed_run()
        child = _make_running_child(run)
        # 1) A subsequent trigger returns the existing row, creates
        # nothing, and does not terminalize it.
        returned = trigger_vendor_refresh(run.id, operator="op-b")
        assert returned.id == child.id
        # 2) No second claim is possible.
        with pytest.raises(VendorRefreshClaimError):
            claim_vendor_refresh(child.id)
        # 3) The row is still RUNNING and active.
        child.refresh_from_db()
        assert child.state == VendorRefreshState.RUNNING
        assert child.active_slot == 1
        assert child.finished_at is None
        assert VendorRefreshExecution.objects.filter(parent_run=run).count() == 1


# ---------------------------------------------------------------------------
# Public exports and deterministic history index
# ---------------------------------------------------------------------------


class TestPublicExportsAndIndex(TestCase):
    """The four primitives, the bounded errors, and the model symbols are
    exposed through the product_intelligence.runs public API."""

    def test_public_api_exports_primitives_and_errors(self) -> None:
        import product_intelligence.runs as runs_pkg

        for name in (
            "trigger_vendor_refresh",
            "claim_vendor_refresh",
            "complete_vendor_refresh",
            "fail_vendor_refresh",
            "VendorRefreshError",
            "VendorRefreshTriggerError",
            "VendorRefreshClaimError",
            "VendorRefreshCompletionError",
            "VendorRefreshFailureError",
        ):
            assert name in runs_pkg.__all__
            assert hasattr(runs_pkg, name)

        assert issubclass(runs_pkg.VendorRefreshTriggerError, runs_pkg.VendorRefreshError)
        assert issubclass(runs_pkg.VendorRefreshClaimError, runs_pkg.VendorRefreshError)
        assert issubclass(
            runs_pkg.VendorRefreshCompletionError, runs_pkg.VendorRefreshError
        )
        assert issubclass(runs_pkg.VendorRefreshFailureError, runs_pkg.VendorRefreshError)

    def test_public_api_exports_model_and_vocabularies(self) -> None:
        import product_intelligence.runs as runs_pkg

        assert runs_pkg.VendorRefreshExecution is VendorRefreshExecution
        assert runs_pkg.VendorRefreshState is VendorRefreshState
        assert runs_pkg.VendorRefreshFailureReason is VendorRefreshFailureReason
        assert runs_pkg.VendorRefreshTriggerSource is VendorRefreshTriggerSource
        for name in (
            "VendorRefreshExecution",
            "VendorRefreshState",
            "VendorRefreshFailureReason",
            "VendorRefreshTriggerSource",
        ):
            assert name in runs_pkg.__all__

    def test_deterministic_history_index_defined(self) -> None:
        index_fields = [
            tuple(index.fields) for index in VendorRefreshExecution._meta.indexes
        ]
        assert ("parent_run", "created_at", "id") in index_fields

    def test_identical_timestamp_history_orders_deterministically(self) -> None:
        """Two terminal rows with IDENTICAL created_at order by the id
        tie-breaker: a stable total order independent of iteration."""
        run = _make_completed_run()
        a = VendorRefreshExecution.objects.create(
            parent_run=run,
            requested_mpn=TEST_MPN,
            state=VendorRefreshState.FAILED,
            active_slot=None,
            trigger_source=VendorRefreshTriggerSource.MANAGEMENT_COMMAND,
            operator="op-a",
            created_at=PINNED,
            started_at=PINNED,
            finished_at=PINNED,
            failure_reason=VendorRefreshFailureReason.INTERNAL_ERROR,
        )
        b = VendorRefreshExecution.objects.create(
            parent_run=run,
            requested_mpn=TEST_MPN,
            state=VendorRefreshState.FAILED,
            active_slot=None,
            trigger_source=VendorRefreshTriggerSource.MANAGEMENT_COMMAND,
            operator="op-b",
            created_at=PINNED,
            started_at=PINNED,
            finished_at=PINNED,
            failure_reason=VendorRefreshFailureReason.INTERNAL_ERROR,
        )
        ordered = list(
            VendorRefreshExecution.objects.filter(parent_run=run)
            .order_by("created_at", "id")
        )
        assert [r.id for r in ordered] == sorted([a.id, b.id])
        # A second read agrees (deterministic).
        ordered_again = list(
            VendorRefreshExecution.objects.filter(parent_run=run)
            .order_by("created_at", "id")
        )
        assert [r.id for r in ordered_again] == [r.id for r in ordered]


# ---------------------------------------------------------------------------
# Cascade and the original-artifact non-mutation invariant
# ---------------------------------------------------------------------------


class TestCascadeAndIsolation(TestCase):
    """Parent-delete cascade, and the DESIGN2 §9 invariant: the parent
    ResearchRun and every original snapshot/evidence artifact are
    byte-identical before and after any refresh."""

    def test_parent_delete_cascades_to_all_children(self) -> None:
        run = _make_completed_run()
        pending = _make_pending_child(run)
        running = None
        # One active slot: terminal the first child, then create the
        # remaining shapes directly for the cascade assertion.
        claimed = claim_vendor_refresh(pending.id)
        fail_vendor_refresh(
            claimed.id,
            VendorRefreshFailureReason.INTERNAL_ERROR,
        )
        running = VendorRefreshExecution.objects.create(
            parent_run=run,
            requested_mpn=TEST_MPN,
            state=VendorRefreshState.RUNNING,
            active_slot=1,
            trigger_source=VendorRefreshTriggerSource.MANAGEMENT_COMMAND,
            operator="op-a",
            started_at=PINNED,
        )
        completed = VendorRefreshExecution.objects.create(
            parent_run=run,
            requested_mpn=TEST_MPN,
            state=VendorRefreshState.COMPLETED,
            active_slot=None,
            trigger_source=VendorRefreshTriggerSource.MANAGEMENT_COMMAND,
            operator="op-b",
            created_at=PINNED,
            started_at=PINNED,
            finished_at=PINNED,
            result_schema_version=1,
            result_payload=_valid_payload(),
        )
        failed = VendorRefreshExecution.objects.create(
            parent_run=run,
            requested_mpn=TEST_MPN,
            state=VendorRefreshState.FAILED,
            active_slot=None,
            trigger_source=VendorRefreshTriggerSource.MANAGEMENT_COMMAND,
            operator="op-c",
            created_at=PINNED,
            started_at=PINNED,
            finished_at=PINNED,
            failure_reason=VendorRefreshFailureReason.INTERNAL_ERROR,
        )
        assert VendorRefreshExecution.objects.filter(parent_run=run).count() == 4
        run.delete()
        assert VendorRefreshExecution.objects.filter(
            pk__in=[pending.id, running.id, completed.id, failed.id]
        ).count() == 0

    @staticmethod
    def _capture_artifacts(run: ResearchRun) -> dict:
        """Byte-level capture of the parent row and EVERY original
        snapshot/evidence artifact."""
        run.refresh_from_db()
        capture: dict = {
            "run": {
                "manufacturer_part_number": run.manufacturer_part_number,
                "description": run.description,
                "state": run.state,
                "created_at": run.created_at,
                "started_at": run.started_at,
                "finished_at": run.finished_at,
            }
        }

        def _one(model, **filters):
            row = model.objects.get(**filters)
            data = {}
            for field in model._meta.concrete_fields:
                if field.name == "id":
                    continue
                value = getattr(row, field.name)
                if hasattr(value, "items"):
                    value = repr(sorted(value.items()))
                data[field.name] = value
            return data

        capture["price_snapshot"] = _one(PriceIntelligenceSnapshot, run=run)
        capture["supplement_snapshot"] = _one(ResearchSupplementSnapshot, run=run)
        capture["fx_snapshot"] = _one(ResearchFxSnapshot, run=run)
        capture["alias_snapshot"] = _one(ResearchMicronAliasSnapshot, run=run)
        capture["evidence"] = [
            _one(ExecutionEvidenceRecord, **rec)
            for rec in (
                {"pk": e.pk}
                for e in ExecutionEvidenceRecord.objects.filter(run=run)
            )
        ]
        capture["review_candidates"] = [
            _one(AiAssistedReviewCandidate, **cand)
            for cand in (
                {"pk": c.pk} for c in AiAssistedReviewCandidate.objects.filter(run=run)
            )
        ]
        capture["comparable"] = [
            _one(ComparableResearchExecution, **child)
            for child in (
                {"pk": c.pk}
                for c in ComparableResearchExecution.objects.filter(parent_run=run)
            )
        ]
        return capture

    def _build_fully_artifacted_completed_run(self) -> ResearchRun:
        run = _make_completed_run()
        # Original vendor artifact: an executed lookup with a FAILED
        # result (the documented production incident shape).
        ResearchSupplementSnapshot.objects.create(
            run=run,
            schema_version=1,
            payload=_valid_payload(lookup_status="FAILED", with_observation=False),
        )
        ResearchFxSnapshot.objects.create(
            run=run,
            schema_version=1,
            payload={
                "schema_version": 1,
                "base_currency": "EUR",
                "observation_date": "2026-01-01",
                "rates": {"USD": "1.08"},
                "provider_retrieved_at": "2026-01-01T00:00:00+00:00",
            },
            acquisition="LIVE",
        )
        ResearchMicronAliasSnapshot.objects.create(
            run=run,
            schema_version=1,
            payload={
                "schema_version": 1,
                "mpn": TEST_MPN,
                "alias_candidates": [],
            },
        )
        ExecutionEvidenceRecord.objects.create(
            run=run,
            attempt_number=1,
            stage="SEARCH",
            outcome="SUCCESS",
            candidate_url="",
            detail_code="OK",
        )
        ExecutionEvidenceRecord.objects.create(
            run=run,
            attempt_number=2,
            stage="FETCH",
            outcome="SUCCESS",
            candidate_url="https://example.com/product/1",
            detail_code="OK",
        )
        AiAssistedReviewCandidate.objects.create(
            run=run,
            assessment_index=0,
            source_url="https://example.com/product/1",
            target_mpn=TEST_MPN,
            target_description=TEST_DESCRIPTION,
            candidate_title="Test Product Title",
            candidate_mpn_field=TEST_MPN,
            candidate_sku="SKU-001",
            candidate_specs="Test specs",
            evidence_source="TITLE_TEXT",
            semantic_confidence="MEDIUM",
            semantic_reason_code="semantic_match",
            semantic_matched_attributes=["brand", "mpn"],
            semantic_conflicting_attributes=[],
            actual_provider="amax",
            actual_model="nemotron-3-super",
            prompt_version="v1.1",
        )
        # A terminal comparable child (created through the 7C-A path).
        from product_intelligence.runs import (
            claim_comparable_research,
            complete_comparable_research,
            trigger_comparable_research,
        )

        comparable = trigger_comparable_research(run.id)
        claim_comparable_research(comparable.id)
        complete_comparable_research(comparable.id, 1, {"kind": "FULL"})
        return run

    def test_original_artifacts_unchanged_after_full_lifecycle(self) -> None:
        run = self._build_fully_artifacted_completed_run()
        before = self._capture_artifacts(run)

        # Attempt 1: a full successful refresh lifecycle.
        child1 = trigger_vendor_refresh(run.id, operator="op-a")
        claim_vendor_refresh(child1.id)
        complete_vendor_refresh(child1.id, 1, _valid_payload())
        # Attempt 2: a full failed refresh lifecycle.
        child2 = trigger_vendor_refresh(run.id, operator="op-b")
        claim_vendor_refresh(child2.id)
        fail_vendor_refresh(
            child2.id, VendorRefreshFailureReason.VENDOR_LOOKUP_CONFIG_MISSING
        )
        # Attempt 3: a stuck RUNNING row (crash simulation).
        child3 = trigger_vendor_refresh(run.id, operator="op-c")
        claim_vendor_refresh(child3.id)

        after = self._capture_artifacts(run)
        assert after == before

        # The refresh rows are the ONLY new durable records.
        assert (
            VendorRefreshExecution.objects.filter(parent_run=run).count() == 3
        )
        assert (
            ResearchSupplementSnapshot.objects.filter(run=run).count() == 1
        )
        snap = ResearchSupplementSnapshot.objects.get(run=run)
        assert (
            snap.payload["vendor_commercial_result"]["lookup_status"] == "FAILED"
        ), "the original vendor artifact must keep its original payload"


# ---------------------------------------------------------------------------
# VREF-R0-FU1 — input boundary closure (trigger + fail primitives)
# ---------------------------------------------------------------------------


def _parent_row_snapshot(run: ResearchRun) -> dict:
    """Every stored column of the parent ResearchRun row (zero-mutation
    proof: a trigger refusal must leave the parent byte-identical)."""
    return dict(ResearchRun.objects.filter(pk=run.pk).values().first())


class TestOperatorBoundaryClosure(TestCase):
    """Fix 1 — ``operator`` is a string of length 1..128 inclusive, bound
    at the service level (SQLite does not enforce ``CharField.max_length``),
    recorded verbatim without stripping or truncation; refusals carry a
    bounded error with no row mutation and no echo of the untrusted
    input content."""

    def test_operator_length_128_accepted_and_preserved_verbatim(self) -> None:
        run = _make_completed_run()
        operator = "A" * 128
        child = trigger_vendor_refresh(run.id, operator=operator)
        assert child.operator == operator
        assert len(child.operator) == 128
        assert VendorRefreshExecution.objects.filter(parent_run=run).count() == 1

    def test_operator_length_129_rejected_before_insert(self) -> None:
        run = _make_completed_run()
        parent_before = _parent_row_snapshot(run)
        with pytest.raises(VendorRefreshTriggerError) as exc_info:
            trigger_vendor_refresh(run.id, operator="B" * 129)
        assert (
            exc_info.value.reason
            == VendorRefreshTriggerError.REASON_INVALID_OPERATOR
        )
        assert VendorRefreshExecution.objects.count() == 0
        assert _parent_row_snapshot(run) == parent_before

    def test_operator_very_long_input_yields_bounded_error_message(self) -> None:
        run = _make_completed_run()
        marker = "SECRET-OPERATOR-CONTENT"  # 23 characters
        operator = marker * 5000  # 115,000 characters
        assert len(operator) == 115_000
        parent_before = _parent_row_snapshot(run)
        with pytest.raises(VendorRefreshTriggerError) as exc_info:
            trigger_vendor_refresh(run.id, operator=operator)
        assert (
            exc_info.value.reason
            == VendorRefreshTriggerError.REASON_INVALID_OPERATOR
        )
        message = str(exc_info.value)
        assert len(message) <= 512
        assert marker not in message
        assert operator[:64] not in message
        assert VendorRefreshExecution.objects.count() == 0
        assert _parent_row_snapshot(run) == parent_before

    def test_operator_length_1_accepted_and_preserved_verbatim(self) -> None:
        run = _make_completed_run()
        child = trigger_vendor_refresh(run.id, operator="A")
        assert child.operator == "A"
        assert VendorRefreshExecution.objects.filter(parent_run=run).count() == 1

    def test_operator_whitespace_only_preserved_verbatim(self) -> None:
        """No stripping: leading/trailing whitespace on a normal value is
        preserved (length 10), and GENUINELY whitespace-only operators are
        legal (length 1..128) and recorded exactly as provided."""
        run = _make_completed_run()
        child = trigger_vendor_refresh(run.id, operator="  padded  ")
        assert child.operator == "  padded  "

        # Genuine whitespace-only coverage (the prior node body only
        # exercised padded non-whitespace content):
        # a length-1 whitespace value is the sharpest no-strip probe
        # (stripping would turn it into an empty string and reject it),
        # a mixed-whitespace value must not be normalized, and the
        # all-whitespace form of the 128-character bound must be accepted.
        for ws in (" ", " \t\n ", " " * 128):
            assert ws.isspace() and not ws.strip()
            assert 1 <= len(ws) <= 128
            run_ws = _make_completed_run()
            child_ws = trigger_vendor_refresh(run_ws.id, operator=ws)
            assert child_ws.operator == ws
            assert VendorRefreshExecution.objects.filter(
                parent_run=run_ws
            ).count() == 1

    def test_operator_empty_rejected_with_zero_mutation(self) -> None:
        run = _make_completed_run()
        parent_before = _parent_row_snapshot(run)
        with pytest.raises(VendorRefreshTriggerError) as exc_info:
            trigger_vendor_refresh(run.id, operator="")
        assert (
            exc_info.value.reason
            == VendorRefreshTriggerError.REASON_INVALID_OPERATOR
        )
        assert VendorRefreshExecution.objects.count() == 0
        assert _parent_row_snapshot(run) == parent_before

    def test_operator_none_rejected_with_zero_mutation(self) -> None:
        run = _make_completed_run()
        parent_before = _parent_row_snapshot(run)
        with pytest.raises(VendorRefreshTriggerError) as exc_info:
            trigger_vendor_refresh(run.id, operator=None)  # type: ignore[arg-type]
        assert (
            exc_info.value.reason
            == VendorRefreshTriggerError.REASON_INVALID_OPERATOR
        )
        assert VendorRefreshExecution.objects.count() == 0
        assert _parent_row_snapshot(run) == parent_before

    def test_operator_unhashable_list_rejected_with_zero_mutation(self) -> None:
        run = _make_completed_run()
        parent_before = _parent_row_snapshot(run)
        with pytest.raises(VendorRefreshTriggerError) as exc_info:
            trigger_vendor_refresh(run.id, operator=["op-a"])  # type: ignore[arg-type]
        assert (
            exc_info.value.reason
            == VendorRefreshTriggerError.REASON_INVALID_OPERATOR
        )
        assert VendorRefreshExecution.objects.count() == 0
        assert _parent_row_snapshot(run) == parent_before

    def test_operator_error_message_bounded_and_content_free(self) -> None:
        """Every refusal shape (non-string, unhashable, over-long string)
        yields a bounded message that carries no input content."""
        run = _make_completed_run()
        for bad in (None, 42, ["op-a"], "Z" * 500):
            with pytest.raises(VendorRefreshTriggerError) as exc_info:
                trigger_vendor_refresh(run.id, operator=bad)  # type: ignore[arg-type]
            message = str(exc_info.value)
            assert len(message) <= 512
            assert "Z" * 64 not in message
        assert VendorRefreshExecution.objects.count() == 0


class TestTriggerSourceBoundaryClosure(TestCase):
    """Fix 2 — ``trigger_source`` fails closed on type: unhashable values
    (list/dict) do not leak a native TypeError from the set membership
    test; other invalid non-string values are rejected through the
    existing bounded error class; the valid vocabulary is unchanged."""

    def test_trigger_source_unhashable_list_rejected_fail_closed(self) -> None:
        run = _make_completed_run()
        parent_before = _parent_row_snapshot(run)
        with pytest.raises(VendorRefreshTriggerError) as exc_info:
            trigger_vendor_refresh(
                run.id,
                operator="op-a",
                trigger_source=[
                    VendorRefreshTriggerSource.MANAGEMENT_COMMAND
                ],  # type: ignore[arg-type]
            )
        assert (
            exc_info.value.reason
            == VendorRefreshTriggerError.REASON_INVALID_TRIGGER_SOURCE
        )
        assert VendorRefreshExecution.objects.count() == 0
        assert _parent_row_snapshot(run) == parent_before

    def test_trigger_source_unhashable_dict_rejected_fail_closed(self) -> None:
        run = _make_completed_run()
        parent_before = _parent_row_snapshot(run)
        with pytest.raises(VendorRefreshTriggerError) as exc_info:
            trigger_vendor_refresh(
                run.id,
                operator="op-a",
                trigger_source={
                    "value": VendorRefreshTriggerSource.MANAGEMENT_COMMAND
                },  # type: ignore[arg-type]
            )
        assert (
            exc_info.value.reason
            == VendorRefreshTriggerError.REASON_INVALID_TRIGGER_SOURCE
        )
        assert VendorRefreshExecution.objects.count() == 0
        assert _parent_row_snapshot(run) == parent_before

    def test_trigger_source_none_rejected_fail_closed(self) -> None:
        run = _make_completed_run()
        parent_before = _parent_row_snapshot(run)
        with pytest.raises(VendorRefreshTriggerError) as exc_info:
            trigger_vendor_refresh(
                run.id, operator="op-a", trigger_source=None  # type: ignore[arg-type]
            )
        assert (
            exc_info.value.reason
            == VendorRefreshTriggerError.REASON_INVALID_TRIGGER_SOURCE
        )
        assert VendorRefreshExecution.objects.count() == 0
        assert _parent_row_snapshot(run) == parent_before

    def test_trigger_source_int_rejected_fail_closed(self) -> None:
        run = _make_completed_run()
        parent_before = _parent_row_snapshot(run)
        with pytest.raises(VendorRefreshTriggerError) as exc_info:
            trigger_vendor_refresh(
                run.id, operator="op-a", trigger_source=42  # type: ignore[arg-type]
            )
        assert (
            exc_info.value.reason
            == VendorRefreshTriggerError.REASON_INVALID_TRIGGER_SOURCE
        )
        assert VendorRefreshExecution.objects.count() == 0
        assert _parent_row_snapshot(run) == parent_before

    def test_trigger_source_long_invalid_string_bounded_message(self) -> None:
        run = _make_completed_run()
        parent_before = _parent_row_snapshot(run)
        bad = "S" * 100_000
        with pytest.raises(VendorRefreshTriggerError) as exc_info:
            trigger_vendor_refresh(run.id, operator="op-a", trigger_source=bad)
        message = str(exc_info.value)
        assert len(message) <= 512
        assert bad[:64] not in message
        assert VendorRefreshExecution.objects.count() == 0
        assert _parent_row_snapshot(run) == parent_before

    def test_trigger_source_valid_vocabulary_unchanged(self) -> None:
        """No over-rejection: the single V1 member is still accepted.
        The vocabulary itself is unchanged."""
        assert VendorRefreshTriggerSource.ALL == frozenset(
            {VendorRefreshTriggerSource.MANAGEMENT_COMMAND}
        )
        run = _make_completed_run()
        child = trigger_vendor_refresh(
            run.id,
            operator="op-a",
            trigger_source=VendorRefreshTriggerSource.MANAGEMENT_COMMAND,
        )
        assert child.trigger_source == VendorRefreshTriggerSource.MANAGEMENT_COMMAND


class TestFailReasonBoundaryClosure(TestCase):
    """Fix 2 — ``failure_reason`` fails closed on type: unhashable values
    (list/dict) do not leak a native TypeError; other invalid non-string
    values are rejected through the existing bounded error class; every
    refusal happens BEFORE any UPDATE (zero row mutation over a row whose
    full CAS preconditions hold). The reserved-value rejection and the
    accepted-vocabulary behavior are pinned by the pre-existing nodes."""

    def _running_child(self) -> tuple[ResearchRun, VendorRefreshExecution]:
        run = _make_completed_run()
        return run, _make_running_child(run)

    def test_fail_reason_unhashable_list_rejected_zero_mutation(self) -> None:
        run, child = self._running_child()
        before = _row_snapshot(child.pk)
        assert before["state"] == VendorRefreshState.RUNNING
        with pytest.raises(VendorRefreshFailureError) as exc_info:
            fail_vendor_refresh(
                child.id,
                [VendorRefreshFailureReason.INTERNAL_ERROR],  # type: ignore[arg-type]
            )
        assert (
            exc_info.value.reason
            == VendorRefreshFailureError.REASON_INVALID_FAILURE_REASON
        )
        assert _row_snapshot(child.pk) == before

    def test_fail_reason_unhashable_dict_rejected_zero_mutation(self) -> None:
        run, child = self._running_child()
        before = _row_snapshot(child.pk)
        assert before["state"] == VendorRefreshState.RUNNING
        with pytest.raises(VendorRefreshFailureError) as exc_info:
            fail_vendor_refresh(
                child.id,
                {"value": VendorRefreshFailureReason.INTERNAL_ERROR},  # type: ignore[arg-type]
            )
        assert (
            exc_info.value.reason
            == VendorRefreshFailureError.REASON_INVALID_FAILURE_REASON
        )
        assert _row_snapshot(child.pk) == before

    def test_fail_reason_none_rejected_zero_mutation(self) -> None:
        run, child = self._running_child()
        before = _row_snapshot(child.pk)
        assert before["state"] == VendorRefreshState.RUNNING
        with pytest.raises(VendorRefreshFailureError) as exc_info:
            fail_vendor_refresh(child.id, None)  # type: ignore[arg-type]
        assert (
            exc_info.value.reason
            == VendorRefreshFailureError.REASON_INVALID_FAILURE_REASON
        )
        assert _row_snapshot(child.pk) == before

    def test_fail_reason_int_rejected_zero_mutation(self) -> None:
        run, child = self._running_child()
        before = _row_snapshot(child.pk)
        assert before["state"] == VendorRefreshState.RUNNING
        with pytest.raises(VendorRefreshFailureError) as exc_info:
            fail_vendor_refresh(child.id, 42)  # type: ignore[arg-type]
        assert (
            exc_info.value.reason
            == VendorRefreshFailureError.REASON_INVALID_FAILURE_REASON
        )
        assert _row_snapshot(child.pk) == before

    def test_fail_reason_long_invalid_string_bounded_message(self) -> None:
        run, child = self._running_child()
        before = _row_snapshot(child.pk)
        bad = "F" * 100_000
        with pytest.raises(VendorRefreshFailureError) as exc_info:
            fail_vendor_refresh(child.id, bad)
        message = str(exc_info.value)
        assert len(message) <= 512
        assert bad[:64] not in message
        assert _row_snapshot(child.pk) == before
