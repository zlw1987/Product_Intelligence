"""The durable report shell (PRODUCT-INTEL.1B).

Three things matter here and are tested directly:

* the page shows the run's real, persisted facts;
* it says plainly that research execution is not connected, rather than
  implying work is under way;
* it changes nothing — a report that advanced the run it reports on would be a
  research trigger wearing a report's clothes.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone as datetime_timezone

from django.test import TestCase
from django.urls import reverse

from product_intelligence.domain import ResearchRequest
from product_intelligence.domain.enums import ResearchRunState
from product_intelligence.runs.models import ResearchRun

CREATED_AT = datetime(2026, 1, 5, 9, 30, 15, tzinfo=datetime_timezone.utc)


def create_run(
    manufacturer_part_number: str = "MZ-V8P1T0B/AM",
    description: str = "1TB NVMe M.2 solid state drive",
) -> ResearchRun:
    return ResearchRun.objects.create_from_request(
        ResearchRequest(
            manufacturer_part_number=manufacturer_part_number,
            description=description,
        ),
        created_at=CREATED_AT,
    )


def detail_url(run: ResearchRun) -> str:
    return reverse("research-detail", kwargs={"run_id": run.id})


class ReportContentTests(TestCase):
    def test_an_existing_run_is_served(self) -> None:
        response = self.client.get(detail_url(create_run()))

        self.assertEqual(response.status_code, 200)

    def test_the_identifier_in_the_url_selects_the_right_run(self) -> None:
        wanted = create_run(manufacturer_part_number="ABC1234-A", description="")
        other = create_run(manufacturer_part_number="ABC1234-B", description="")

        response = self.client.get(detail_url(wanted))

        self.assertContains(response, str(wanted.id))
        self.assertNotContains(response, str(other.id))
        self.assertContains(response, "ABC1234-A")
        self.assertNotContains(response, "ABC1234-B")

    def test_the_part_number_is_shown(self) -> None:
        response = self.client.get(detail_url(create_run()))

        self.assertContains(response, "MZ-V8P1T0B/AM")

    def test_the_description_is_shown(self) -> None:
        response = self.client.get(detail_url(create_run()))

        self.assertContains(response, "1TB NVMe M.2 solid state drive")

    def test_the_current_state_is_shown(self) -> None:
        response = self.client.get(detail_url(create_run()))

        self.assertContains(response, "CREATED")

    def test_the_created_timestamp_is_shown(self) -> None:
        response = self.client.get(detail_url(create_run()))

        self.assertContains(response, "2026-01-05 09:30:15 UTC")

    def test_absent_start_and_finish_times_are_not_invented(self) -> None:
        """A CREATED run has neither, so the page shows neither."""
        response = self.client.get(detail_url(create_run()))
        html = response.content.decode()

        self.assertNotIn("Started", html)
        self.assertNotIn("Finished", html)

    def test_an_empty_field_is_reported_as_not_supplied(self) -> None:
        run = create_run(manufacturer_part_number="ABC1234-A", description="")

        response = self.client.get(detail_url(run))

        self.assertContains(response, "Not supplied")

    def test_the_page_says_research_execution_is_not_connected(self) -> None:
        response = self.client.get(detail_url(create_run()))

        self.assertContains(response, "Research request created.")
        self.assertContains(response, "not yet connected")

    def test_the_page_shows_no_fabricated_result(self) -> None:
        """No placeholder price and no empty-value filler.

        A blank report is honest; a `$0` or an `N/A median` is a claim the
        system has no evidence for, and a reader would believe it.
        """
        response = self.client.get(detail_url(create_run()))
        html = response.content.decode()

        for fabricated in ("$", "N/A", "0.00"):
            self.assertNotIn(fabricated, html)


class ReportIsReadOnlyTests(TestCase):
    def test_viewing_a_report_does_not_transition_the_run(self) -> None:
        run = create_run()

        for _ in range(3):
            self.client.get(detail_url(run))

        run.refresh_from_db()

        self.assertEqual(run.current_state, ResearchRunState.CREATED)

    def test_viewing_a_report_does_not_touch_the_timestamps(self) -> None:
        run = create_run()

        self.client.get(detail_url(run))
        run.refresh_from_db()

        self.assertEqual(run.created_at, CREATED_AT)
        self.assertIsNone(run.started_at)
        self.assertIsNone(run.finished_at)

    def test_viewing_a_report_creates_no_row(self) -> None:
        run = create_run()

        self.client.get(detail_url(run))

        self.assertEqual(ResearchRun.objects.count(), 1)
        self.assertEqual(ResearchRun.objects.get().id, run.id)


class MissingRunTests(TestCase):
    def test_an_unknown_identifier_is_a_404(self) -> None:
        response = self.client.get(
            reverse("research-detail", kwargs={"run_id": uuid.uuid4()})
        )

        self.assertEqual(response.status_code, 404)

    def test_a_malformed_identifier_is_a_404_not_a_server_error(self) -> None:
        for malformed in ("/research/not-a-uuid", "/research/12345", "/research/"):
            with self.subTest(path=malformed):
                self.assertEqual(self.client.get(malformed).status_code, 404)


class EscapingTests(TestCase):
    """MPN and description are untrusted input from every intake."""

    def test_script_like_input_is_escaped_rather_than_rendered(self) -> None:
        payload = '<script>alert("xss")</script>'
        run = create_run(manufacturer_part_number=payload, description="")

        response = self.client.get(detail_url(run))
        html = response.content.decode()

        self.assertNotIn(payload, html)
        self.assertNotIn("<script>alert", html)
        self.assertIn("&lt;script&gt;", html)

    def test_markup_in_a_description_is_escaped(self) -> None:
        run = create_run(
            manufacturer_part_number="",
            description='<img src=x onerror="alert(1)"> 2U rail kit',
        )

        response = self.client.get(detail_url(run))
        html = response.content.decode()

        self.assertNotIn("<img src=x", html)
        self.assertIn("&lt;img src=x", html)
        self.assertIn("2U rail kit", html)

    def test_markup_submitted_through_the_form_is_escaped_end_to_end(self) -> None:
        self.client.post(
            reverse("research-new"),
            {
                "manufacturer_part_number": "<b>ABC1234-A</b>",
                "description": "</dd><script>alert(1)</script>",
            },
        )
        run = ResearchRun.objects.get()

        html = self.client.get(detail_url(run)).content.decode()

        self.assertIn("&lt;b&gt;ABC1234-A&lt;/b&gt;", html)
        self.assertNotIn("<script>alert(1)</script>", html)
        self.assertNotIn("</dd><script>", html)
