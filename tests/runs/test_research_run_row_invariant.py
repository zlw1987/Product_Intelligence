"""The structural invariant every stored row must satisfy (1A-FU1).

1A enforced the lifecycle in application code and backed it with a single
narrow database rule ("finished implies started"). An audit of the shapes an
ordinary `objects.create(...)` could persist found ten invalid ones getting
through — a `RUNNING` row with no start time, a `COMPLETED` row that never
finished, a `CREATED` row carrying both timestamps, and runs created directly
in a terminal state.

These tests fix that behaviour in place. They are deliberately split by who is
doing the rejecting:

* `InitialStateTests` — the application refuses to *create* a run anywhere but
  `CREATED`;
* `StoredRowShapeTests` — the database refuses a structurally impossible row
  even when the application guards are deliberately bypassed with
  `QuerySet.update()`, which never runs `Model.save()`.

That split is the responsibility boundary itself: the database judges the row,
the application judges the path. Neither is asked to do the other's job.
"""

from __future__ import annotations

from datetime import datetime, timezone as datetime_timezone

from django.db import IntegrityError, transaction
from django.db.models import Q
from django.test import TestCase

from product_intelligence.domain import ResearchRequest
from product_intelligence.domain.enums import ResearchRunState
from product_intelligence.runs.errors import (
    InvalidInitialResearchRunState,
    ResearchRunLifecycleError,
)
from product_intelligence.runs.models import TERMINAL_STATES, ResearchRun

CREATED_AT = datetime(2026, 1, 5, 9, 0, tzinfo=datetime_timezone.utc)
STARTED_AT = datetime(2026, 1, 5, 9, 1, tzinfo=datetime_timezone.utc)
FINISHED_AT = datetime(2026, 1, 5, 9, 4, tzinfo=datetime_timezone.utc)

TERMINAL_IN_ORDER = sorted(TERMINAL_STATES, key=lambda state: state.value)


def _request() -> ResearchRequest:
    return ResearchRequest(
        manufacturer_part_number="ABC1234-A",
        description="24 port managed switch",
    )


def _created_run() -> ResearchRun:
    return ResearchRun.objects.create_from_request(_request(), created_at=CREATED_AT)


class InitialStateTests(TestCase):
    """A run enters the database in CREATED, whatever the caller asked for."""

    def test_the_supported_creation_path_starts_in_created(self) -> None:
        run = _created_run()
        run.refresh_from_db()

        self.assertEqual(run.current_state, ResearchRunState.CREATED)
        self.assertIsNone(run.started_at)
        self.assertIsNone(run.finished_at)

    def test_creating_a_run_directly_in_running_is_refused(self) -> None:
        with self.assertRaises(InvalidInitialResearchRunState):
            ResearchRun.objects.create(
                manufacturer_part_number="ABC1234-A",
                description="24 port managed switch",
                state=ResearchRunState.RUNNING.value,
                created_at=CREATED_AT,
                started_at=STARTED_AT,
            )

        self.assertEqual(ResearchRun.objects.count(), 0)

    def test_creating_a_run_directly_in_a_terminal_state_is_refused(self) -> None:
        for terminal in TERMINAL_IN_ORDER:
            with self.subTest(terminal=terminal):
                with self.assertRaises(InvalidInitialResearchRunState) as caught:
                    ResearchRun.objects.create(
                        manufacturer_part_number="ABC1234-A",
                        description="24 port managed switch",
                        state=terminal.value,
                        created_at=CREATED_AT,
                        started_at=STARTED_AT,
                        finished_at=FINISHED_AT,
                    )

                self.assertIsInstance(caught.exception, ResearchRunLifecycleError)
                self.assertEqual(caught.exception.attempted, terminal.value)

        self.assertEqual(ResearchRun.objects.count(), 0)

    def test_an_unsaved_run_cannot_transition(self) -> None:
        """There is nothing to move: a run begins life in the database."""
        run = ResearchRun(
            manufacturer_part_number="ABC1234-A",
            description="24 port managed switch",
        )

        with self.assertRaises(ResearchRunLifecycleError):
            run.transition_to(ResearchRunState.RUNNING, at=STARTED_AT)

        self.assertEqual(ResearchRun.objects.count(), 0)

    def test_a_saved_run_can_still_be_saved_again_without_a_state_change(self) -> None:
        """The creation guard must not fire on ordinary later writes."""
        run = _created_run()
        run.description = "24 port managed switch, rack mount"
        run.save(update_fields=["description"])

        self.assertEqual(
            ResearchRun.objects.get(pk=run.pk).description,
            "24 port managed switch, rack mount",
        )


class ValidShapeTests(TestCase):
    """Each of the three legal shapes stores and reloads."""

    def test_a_created_row_persists(self) -> None:
        run = _created_run()

        stored = ResearchRun.objects.get(pk=run.pk)

        self.assertEqual(stored.current_state, ResearchRunState.CREATED)
        self.assertIsNone(stored.started_at)
        self.assertIsNone(stored.finished_at)

    def test_a_running_row_produced_by_a_transition_persists(self) -> None:
        run = _created_run()
        run.transition_to(ResearchRunState.RUNNING, at=STARTED_AT)

        stored = ResearchRun.objects.get(pk=run.pk)

        self.assertEqual(stored.current_state, ResearchRunState.RUNNING)
        self.assertEqual(stored.started_at, STARTED_AT)
        self.assertIsNone(stored.finished_at)

    def test_every_terminal_row_produced_by_a_transition_persists(self) -> None:
        for terminal in TERMINAL_IN_ORDER:
            with self.subTest(terminal=terminal):
                run = _created_run()
                run.transition_to(ResearchRunState.RUNNING, at=STARTED_AT)
                run.transition_to(terminal, at=FINISHED_AT)

                stored = ResearchRun.objects.get(pk=run.pk)

                self.assertEqual(stored.current_state, terminal)
                self.assertEqual(stored.started_at, STARTED_AT)
                self.assertEqual(stored.finished_at, FINISHED_AT)


class StoredRowShapeTests(TestCase):
    """The database rejects impossible rows with the application out of the way.

    `QuerySet.update()` issues SQL directly: it does not call `Model.save()`,
    so none of the lifecycle guards run. That is exactly why it is the right
    instrument here — what is left standing is the database's own guarantee.
    """

    def _refuses(self, **updates: object) -> None:
        run = _created_run()

        with self.assertRaises(IntegrityError), transaction.atomic():
            ResearchRun.objects.filter(pk=run.pk).update(**updates)

    def test_created_cannot_hold_a_start_time(self) -> None:
        self._refuses(started_at=STARTED_AT)

    def test_created_cannot_hold_a_finish_time(self) -> None:
        self._refuses(finished_at=FINISHED_AT)

    def test_created_cannot_hold_both_timestamps(self) -> None:
        self._refuses(started_at=STARTED_AT, finished_at=FINISHED_AT)

    def test_running_requires_a_start_time(self) -> None:
        self._refuses(state=ResearchRunState.RUNNING.value)

    def test_running_forbids_a_finish_time(self) -> None:
        self._refuses(
            state=ResearchRunState.RUNNING.value,
            started_at=STARTED_AT,
            finished_at=FINISHED_AT,
        )

    def test_a_terminal_state_requires_a_start_time(self) -> None:
        for terminal in TERMINAL_IN_ORDER:
            with self.subTest(terminal=terminal):
                self._refuses(state=terminal.value, finished_at=FINISHED_AT)

    def test_a_terminal_state_requires_a_finish_time(self) -> None:
        for terminal in TERMINAL_IN_ORDER:
            with self.subTest(terminal=terminal):
                self._refuses(state=terminal.value, started_at=STARTED_AT)

    def test_a_terminal_state_requires_both_timestamps(self) -> None:
        for terminal in TERMINAL_IN_ORDER:
            with self.subTest(terminal=terminal):
                self._refuses(state=terminal.value)

    def test_a_state_outside_the_vocabulary_cannot_be_stored(self) -> None:
        """`choices` is validation, not storage. The constraint is storage."""
        self._refuses(state="ALMOST_DONE", started_at=STARTED_AT)

    def test_a_bypass_may_still_skip_the_transition_path(self) -> None:
        """The documented remaining gap, asserted rather than left implicit.

        A direct write can move a run along a route `transition_to` forbids,
        because a check constraint sees one row and not the sequence that
        produced it. What it cannot do is leave an inconsistent row behind —
        every test above is that half of the boundary.
        """
        run = _created_run()

        moved = ResearchRun.objects.filter(pk=run.pk).update(
            state=ResearchRunState.COMPLETED.value,
            started_at=STARTED_AT,
            finished_at=FINISHED_AT,
        )

        self.assertEqual(moved, 1)
        stored = ResearchRun.objects.get(pk=run.pk)
        self.assertEqual(stored.current_state, ResearchRunState.COMPLETED)
        # Structurally valid, and provenance-wise a fiction: it was never
        # RUNNING. Proving otherwise needs history the database does not keep.
        self.assertEqual(stored.started_at, STARTED_AT)


class ConstraintInventoryTests(TestCase):
    def test_the_table_carries_exactly_the_two_intended_constraints(self) -> None:
        """No leftovers: the narrower 1A rule was replaced, not stacked."""
        names = {constraint.name for constraint in ResearchRun._meta.constraints}

        self.assertEqual(
            names,
            {
                "research_run_has_mpn_or_description",
                "research_run_state_matches_timestamps",
            },
        )

    def test_the_shape_constraint_covers_every_state_in_the_vocabulary(self) -> None:
        """A state absent from the rule would be a hole, not a permission."""
        constraint = next(
            c
            for c in ResearchRun._meta.constraints
            if c.name == "research_run_state_matches_timestamps"
        )

        named: set[str] = set()
        for branch in constraint.condition.children:
            for field, value in branch.children if isinstance(branch, Q) else []:
                if field == "state":
                    named.add(value)
                elif field == "state__in":
                    named.update(value)

        self.assertEqual(named, {state.value for state in ResearchRunState})

    def test_the_request_content_constraint_still_applies(self) -> None:
        with self.assertRaises(IntegrityError), transaction.atomic():
            ResearchRun.objects.create(
                manufacturer_part_number="",
                description="",
                created_at=CREATED_AT,
            )
