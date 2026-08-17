"""The research-run state machine.

The approved first lifecycle:

    CREATED -> RUNNING
    RUNNING -> COMPLETED
    RUNNING -> PARTIALLY_COMPLETED
    RUNNING -> FAILED

Everything else is refused. These tests spend most of their effort on the
refusals, because a state machine that only ever gets exercised along its happy
paths is indistinguishable from an attribute assignment.

All timestamps are supplied explicitly, so no assertion depends on the clock.
"""

from __future__ import annotations

from datetime import datetime, timezone as datetime_timezone

from django.db import IntegrityError, transaction
from django.test import TestCase

from product_intelligence.domain import ResearchRequest
from product_intelligence.domain.enums import ResearchRunState
from product_intelligence.runs.errors import (
    InvalidResearchRunTransition,
    ResearchRunLifecycleError,
    UnsupportedResearchRunStateChange,
)
from product_intelligence.runs.models import (
    ALLOWED_TRANSITIONS,
    TERMINAL_STATES,
    ResearchRun,
)

CREATED_AT = datetime(2026, 1, 5, 9, 0, tzinfo=datetime_timezone.utc)
STARTED_AT = datetime(2026, 1, 5, 9, 1, tzinfo=datetime_timezone.utc)
FINISHED_AT = datetime(2026, 1, 5, 9, 4, tzinfo=datetime_timezone.utc)
LATER = datetime(2026, 1, 5, 10, 0, tzinfo=datetime_timezone.utc)


def _new_run() -> ResearchRun:
    return ResearchRun.objects.create_from_request(
        ResearchRequest(
            manufacturer_part_number="ABC1234-A",
            description="24 port managed switch",
        ),
        created_at=CREATED_AT,
    )


def _running_run() -> ResearchRun:
    run = _new_run()
    run.transition_to(ResearchRunState.RUNNING, at=STARTED_AT)
    return run


class VocabularyTests(TestCase):
    def test_the_transition_table_covers_every_state_in_the_vocabulary(self) -> None:
        """No state may be missing a rule, and none may be invented here."""
        self.assertEqual(set(ALLOWED_TRANSITIONS), set(ResearchRunState))

    def test_the_persisted_choices_are_generated_from_the_domain_vocabulary(self) -> None:
        field_values = [value for value, _label in ResearchRun._meta.get_field("state").choices]

        self.assertEqual(field_values, [state.value for state in ResearchRunState])


class AllowedTransitionTests(TestCase):
    def test_created_to_running_sets_the_start_time(self) -> None:
        run = _new_run()

        run.transition_to(ResearchRunState.RUNNING, at=STARTED_AT)
        run.refresh_from_db()

        self.assertEqual(run.current_state, ResearchRunState.RUNNING)
        self.assertEqual(run.started_at, STARTED_AT)
        self.assertIsNone(run.finished_at)
        self.assertFalse(run.is_terminal)

    def test_running_to_completed(self) -> None:
        run = _running_run()

        run.transition_to(ResearchRunState.COMPLETED, at=FINISHED_AT)
        run.refresh_from_db()

        self.assertEqual(run.current_state, ResearchRunState.COMPLETED)
        self.assertEqual(run.started_at, STARTED_AT)
        self.assertEqual(run.finished_at, FINISHED_AT)
        self.assertTrue(run.is_terminal)

    def test_running_to_partially_completed(self) -> None:
        """A partial result is a real outcome, not a degraded failure."""
        run = _running_run()

        run.transition_to(ResearchRunState.PARTIALLY_COMPLETED, at=FINISHED_AT)
        run.refresh_from_db()

        self.assertEqual(run.current_state, ResearchRunState.PARTIALLY_COMPLETED)
        self.assertEqual(run.finished_at, FINISHED_AT)
        self.assertTrue(run.is_terminal)

    def test_running_to_failed(self) -> None:
        run = _running_run()

        run.transition_to(ResearchRunState.FAILED, at=FINISHED_AT)
        run.refresh_from_db()

        self.assertEqual(run.current_state, ResearchRunState.FAILED)
        self.assertEqual(run.finished_at, FINISHED_AT)
        self.assertTrue(run.is_terminal)

    def test_a_transition_accepts_the_state_value_as_well_as_the_enum(self) -> None:
        run = _new_run()

        run.transition_to("RUNNING", at=STARTED_AT)

        self.assertEqual(run.current_state, ResearchRunState.RUNNING)

    def test_a_transition_returns_the_run_so_a_caller_can_keep_using_it(self) -> None:
        run = _new_run()

        self.assertIs(run.transition_to(ResearchRunState.RUNNING, at=STARTED_AT), run)


class TimestampTests(TestCase):
    def test_the_start_time_is_written_once_and_never_moves(self) -> None:
        """RUNNING is reachable only from CREATED, which is reachable from nowhere.

        The guarantee is structural, so the proof is that no later legal move,
        and no refused one, can rewrite it.
        """
        run = _running_run()

        run.transition_to(ResearchRunState.COMPLETED, at=FINISHED_AT)
        run.refresh_from_db()

        self.assertEqual(run.started_at, STARTED_AT)

        with self.assertRaises(InvalidResearchRunTransition):
            run.transition_to(ResearchRunState.RUNNING, at=LATER)

        run.refresh_from_db()
        self.assertEqual(run.started_at, STARTED_AT)

    def test_a_repeated_running_transition_is_refused_rather_than_restarted(self) -> None:
        run = _running_run()

        with self.assertRaises(InvalidResearchRunTransition):
            run.transition_to(ResearchRunState.RUNNING, at=LATER)

        run.refresh_from_db()
        self.assertEqual(run.started_at, STARTED_AT)
        self.assertEqual(run.current_state, ResearchRunState.RUNNING)

    def test_the_finish_time_stays_absent_until_a_terminal_state(self) -> None:
        run = _new_run()
        self.assertIsNone(run.finished_at)

        run.transition_to(ResearchRunState.RUNNING, at=STARTED_AT)
        run.refresh_from_db()
        self.assertIsNone(run.finished_at)

        run.transition_to(ResearchRunState.FAILED, at=FINISHED_AT)
        run.refresh_from_db()
        self.assertEqual(run.finished_at, FINISHED_AT)

    def test_every_terminal_state_records_a_finish_time(self) -> None:
        for terminal in sorted(TERMINAL_STATES, key=lambda state: state.value):
            with self.subTest(terminal=terminal):
                run = _running_run()

                run.transition_to(terminal, at=FINISHED_AT)
                run.refresh_from_db()

                self.assertEqual(run.finished_at, FINISHED_AT)
                self.assertEqual(run.started_at, STARTED_AT)
                self.assertEqual(run.created_at, CREATED_AT)

    def test_the_database_refuses_timestamps_that_contradict_the_state(self) -> None:
        """A `CREATED` run has no timestamps, and the database knows it.

        The full state/timestamp invariant is exercised in
        `test_research_run_row_invariant.py`; this keeps the lifecycle tests
        honest about the fact that the two are backed by storage, not only by
        the transition method.
        """
        run = _new_run()
        run.finished_at = FINISHED_AT

        with self.assertRaises(IntegrityError), transaction.atomic():
            run.save(update_fields=["finished_at"])


class RefusedTransitionTests(TestCase):
    def test_created_cannot_jump_straight_to_a_terminal_state(self) -> None:
        for terminal in sorted(TERMINAL_STATES, key=lambda state: state.value):
            with self.subTest(terminal=terminal):
                run = _new_run()

                with self.assertRaises(InvalidResearchRunTransition):
                    run.transition_to(terminal, at=FINISHED_AT)

    def test_a_refused_transition_changes_nothing_in_memory_or_on_disk(self) -> None:
        """The regression that matters: refusal must not half-apply."""
        run = _new_run()

        with self.assertRaises(InvalidResearchRunTransition):
            run.transition_to(ResearchRunState.COMPLETED, at=FINISHED_AT)

        self.assertEqual(run.current_state, ResearchRunState.CREATED)
        self.assertIsNone(run.started_at)
        self.assertIsNone(run.finished_at)

        stored = ResearchRun.objects.get(pk=run.pk)
        self.assertEqual(stored.current_state, ResearchRunState.CREATED)
        self.assertIsNone(stored.started_at)
        self.assertIsNone(stored.finished_at)

    def test_a_terminal_run_cannot_transition_again(self) -> None:
        for terminal in sorted(TERMINAL_STATES, key=lambda state: state.value):
            for target in sorted(ResearchRunState, key=lambda state: state.value):
                with self.subTest(terminal=terminal, target=target):
                    run = _running_run()
                    run.transition_to(terminal, at=FINISHED_AT)

                    with self.assertRaises(InvalidResearchRunTransition):
                        run.transition_to(target, at=LATER)

                    run.refresh_from_db()
                    self.assertEqual(run.current_state, terminal)
                    self.assertEqual(run.finished_at, FINISHED_AT)

    def test_a_run_cannot_move_backwards_to_created(self) -> None:
        run = _running_run()

        with self.assertRaises(InvalidResearchRunTransition):
            run.transition_to(ResearchRunState.CREATED, at=LATER)

    def test_a_refusal_names_both_states_and_is_an_application_error(self) -> None:
        run = _new_run()

        with self.assertRaises(InvalidResearchRunTransition) as caught:
            run.transition_to(ResearchRunState.FAILED, at=FINISHED_AT)

        self.assertIsInstance(caught.exception, ResearchRunLifecycleError)
        self.assertEqual(caught.exception.current, ResearchRunState.CREATED)
        self.assertEqual(caught.exception.target, ResearchRunState.FAILED)
        self.assertIn("CREATED", str(caught.exception))
        self.assertIn("FAILED", str(caught.exception))

    def test_a_state_outside_the_vocabulary_is_rejected(self) -> None:
        run = _new_run()

        with self.assertRaises(ValueError):
            run.transition_to("ALMOST_DONE", at=LATER)

        self.assertEqual(run.current_state, ResearchRunState.CREATED)

    def test_assigning_the_state_field_directly_does_not_bypass_the_rules(self) -> None:
        """The lifecycle is enforced, not merely documented."""
        run = _new_run()
        run.state = ResearchRunState.COMPLETED.value

        with self.assertRaises(UnsupportedResearchRunStateChange):
            run.save()

        stored = ResearchRun.objects.get(pk=run.pk)
        self.assertEqual(stored.current_state, ResearchRunState.CREATED)
        self.assertIsNone(stored.finished_at)

    def test_even_a_legal_target_must_go_through_the_transition_api(self) -> None:
        """The route is the problem, not the destination."""
        run = _new_run()
        run.state = ResearchRunState.RUNNING.value

        with self.assertRaises(UnsupportedResearchRunStateChange):
            run.save(update_fields=["state"])

        self.assertEqual(
            ResearchRun.objects.get(pk=run.pk).current_state, ResearchRunState.CREATED
        )


class ReloadTests(TestCase):
    def test_lifecycle_state_survives_a_reload_from_the_database(self) -> None:
        run = _running_run()
        run.transition_to(ResearchRunState.PARTIALLY_COMPLETED, at=FINISHED_AT)

        reloaded = ResearchRun.objects.get(pk=run.pk)

        self.assertEqual(reloaded.current_state, ResearchRunState.PARTIALLY_COMPLETED)
        self.assertEqual(reloaded.created_at, CREATED_AT)
        self.assertEqual(reloaded.started_at, STARTED_AT)
        self.assertEqual(reloaded.finished_at, FINISHED_AT)
        self.assertTrue(reloaded.is_terminal)

    def test_a_reloaded_terminal_run_still_refuses_to_move(self) -> None:
        """Terminality is a property of the record, not of one instance."""
        run = _running_run()
        run.transition_to(ResearchRunState.COMPLETED, at=FINISHED_AT)

        reloaded = ResearchRun.objects.get(pk=run.pk)

        self.assertEqual(reloaded.allowed_transitions(), frozenset())
        with self.assertRaises(InvalidResearchRunTransition):
            reloaded.transition_to(ResearchRunState.FAILED, at=LATER)

    def test_a_reloaded_created_run_can_still_be_started(self) -> None:
        run = _new_run()

        reloaded = ResearchRun.objects.get(pk=run.pk)
        reloaded.transition_to(ResearchRunState.RUNNING, at=STARTED_AT)

        self.assertEqual(
            ResearchRun.objects.get(pk=run.pk).current_state, ResearchRunState.RUNNING
        )
