"""Creating a persisted research run from the canonical request.

Every test here pins its own timestamps. Nothing reads the wall clock, so
nothing here can pass or fail depending on when it runs.
"""

from __future__ import annotations

from datetime import datetime, timezone as datetime_timezone

from django.db import IntegrityError, transaction
from django.test import TestCase

from product_intelligence.domain import ResearchRequest
from product_intelligence.domain.enums import ResearchRunState
from product_intelligence.domain.errors import DomainValidationError
from product_intelligence.runs.models import ResearchRun

CREATED_AT = datetime(2026, 1, 5, 9, 0, tzinfo=datetime_timezone.utc)


class CreateFromRequestTests(TestCase):
    def test_creates_a_run_from_a_valid_request(self) -> None:
        request = ResearchRequest(
            manufacturer_part_number="MZ-V8P1T0B/AM",
            description="1TB NVMe M.2 solid state drive",
        )

        run = ResearchRun.objects.create_from_request(request, created_at=CREATED_AT)

        self.assertEqual(run.manufacturer_part_number, "MZ-V8P1T0B/AM")
        self.assertEqual(run.description, "1TB NVMe M.2 solid state drive")
        self.assertEqual(run.created_at, CREATED_AT)
        self.assertEqual(ResearchRun.objects.count(), 1)

    def test_creates_a_run_from_a_part_number_only_request(self) -> None:
        request = ResearchRequest(manufacturer_part_number="ABC1234-A", description="")

        run = ResearchRun.objects.create_from_request(request, created_at=CREATED_AT)
        run.refresh_from_db()

        self.assertEqual(run.manufacturer_part_number, "ABC1234-A")
        self.assertEqual(run.description, "")
        self.assertEqual(run.current_state, ResearchRunState.CREATED)

    def test_creates_a_run_from_a_description_only_request(self) -> None:
        request = ResearchRequest(
            manufacturer_part_number="",
            description="rack mount rail kit, 2U",
        )

        run = ResearchRun.objects.create_from_request(request, created_at=CREATED_AT)
        run.refresh_from_db()

        self.assertEqual(run.manufacturer_part_number, "")
        self.assertEqual(run.description, "rack mount rail kit, 2U")
        self.assertEqual(run.current_state, ResearchRunState.CREATED)

    def test_persists_the_canonical_whitespace_form(self) -> None:
        """Surrounding whitespace is gone; the interior is untouched.

        The request already decided this. What this proves is that persistence
        stores the canonical value rather than re-normalizing, re-stripping, or
        otherwise editing it on the way to the database.
        """
        request = ResearchRequest(
            manufacturer_part_number="  ABC1234-A \n",
            description="\t 24 port  managed switch \t",
        )

        run = ResearchRun.objects.create_from_request(request, created_at=CREATED_AT)
        run.refresh_from_db()

        self.assertEqual(run.manufacturer_part_number, "ABC1234-A")
        self.assertEqual(run.description, "24 port  managed switch")

    def test_a_new_run_starts_in_created_with_no_start_or_finish_time(self) -> None:
        run = ResearchRun.objects.create_from_request(
            ResearchRequest(manufacturer_part_number="ABC1234-A", description=""),
            created_at=CREATED_AT,
        )
        run.refresh_from_db()

        self.assertEqual(run.current_state, ResearchRunState.CREATED)
        self.assertEqual(run.state, "CREATED")
        self.assertEqual(run.created_at, CREATED_AT)
        self.assertIsNone(run.started_at)
        self.assertIsNone(run.finished_at)
        self.assertFalse(run.is_terminal)

    def test_a_run_cannot_be_created_from_an_empty_request(self) -> None:
        """The rule is reused, not reimplemented.

        The request contract refuses a pair that is empty on both sides, so no
        such request exists to hand to the manager. That is the whole reason
        `create_from_request` takes a `ResearchRequest` and not two strings.
        """
        with self.assertRaises(DomainValidationError):
            ResearchRequest(manufacturer_part_number="   ", description="")

        self.assertEqual(ResearchRun.objects.count(), 0)

    def test_the_manager_refuses_anything_that_is_not_a_research_request(self) -> None:
        with self.assertRaises(TypeError):
            ResearchRun.objects.create_from_request(
                {"manufacturer_part_number": "ABC1234-A", "description": ""}  # type: ignore[arg-type]
            )

        self.assertEqual(ResearchRun.objects.count(), 0)

    def test_the_database_refuses_a_run_that_asked_nothing(self) -> None:
        """A backstop below the application API, proven rather than assumed."""
        with self.assertRaises(IntegrityError), transaction.atomic():
            ResearchRun.objects.create(
                manufacturer_part_number="",
                description="",
                created_at=CREATED_AT,
            )

        self.assertEqual(ResearchRun.objects.count(), 0)

    def test_a_run_rebuilds_the_canonical_request_it_was_created_from(self) -> None:
        """Later phases consume the contract, never the database row."""
        request = ResearchRequest(
            manufacturer_part_number="ABC1234-A",
            description="24 port managed switch",
        )

        run = ResearchRun.objects.create_from_request(request, created_at=CREATED_AT)

        self.assertEqual(ResearchRun.objects.get(pk=run.pk).to_research_request(), request)


class IdentityTests(TestCase):
    def test_a_run_has_a_uuid_that_survives_a_reload(self) -> None:
        import uuid

        run = ResearchRun.objects.create_from_request(
            ResearchRequest(manufacturer_part_number="ABC1234-A", description=""),
            created_at=CREATED_AT,
        )
        original_id = run.id

        self.assertIsInstance(original_id, uuid.UUID)

        reloaded = ResearchRun.objects.get(pk=original_id)

        self.assertEqual(reloaded.id, original_id)

    def test_the_identifier_does_not_change_when_the_run_progresses(self) -> None:
        """A report URL must stay valid for the life of the record."""
        run = ResearchRun.objects.create_from_request(
            ResearchRequest(manufacturer_part_number="ABC1234-A", description=""),
            created_at=CREATED_AT,
        )
        original_id = run.id

        run.transition_to(ResearchRunState.RUNNING, at=CREATED_AT)
        run.transition_to(ResearchRunState.COMPLETED, at=CREATED_AT)
        run.refresh_from_db()

        self.assertEqual(run.id, original_id)
        self.assertEqual(ResearchRun.objects.count(), 1)

    def test_two_runs_of_the_same_request_are_separate_records(self) -> None:
        request = ResearchRequest(
            manufacturer_part_number="ABC1234-A",
            description="24 port managed switch",
        )

        first = ResearchRun.objects.create_from_request(request, created_at=CREATED_AT)
        second = ResearchRun.objects.create_from_request(request, created_at=CREATED_AT)

        self.assertNotEqual(first.id, second.id)
        self.assertEqual(ResearchRun.objects.count(), 2)
