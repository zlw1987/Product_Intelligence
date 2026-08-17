"""POST → ResearchRun → redirect → report (PRODUCT-INTEL.1B).

The browser workflow has to create exactly one run, through the supported
lifecycle API, in `CREATED`, with no start or finish time — and then get out of
the way. Nothing here may execute research, because nothing that could exists.
"""

from __future__ import annotations

from unittest import mock

from django.http import HttpResponse
from django.test import Client, TestCase
from django.urls import reverse

from product_intelligence.domain.enums import ResearchRunState
from product_intelligence.runs.models import ResearchRun


class SuccessfulSubmissionTests(TestCase):
    def submit(self, **data: str) -> HttpResponse:
        payload = {"manufacturer_part_number": "", "description": ""}
        payload.update(data)
        return self.client.post(reverse("research-new"), payload)

    def test_a_valid_submission_creates_exactly_one_run(self) -> None:
        self.submit(
            manufacturer_part_number="MZ-V8P1T0B/AM",
            description="1TB NVMe M.2 solid state drive",
        )

        self.assertEqual(ResearchRun.objects.count(), 1)

    def test_the_persisted_values_are_the_canonical_ones(self) -> None:
        self.submit(
            manufacturer_part_number="  MZ-V8P1T0B/AM \n",
            description="\t 1TB NVMe  M.2 drive \t",
        )

        run = ResearchRun.objects.get()

        self.assertEqual(run.manufacturer_part_number, "MZ-V8P1T0B/AM")
        self.assertEqual(run.description, "1TB NVMe  M.2 drive")

    def test_the_new_run_is_created_and_has_not_started_or_finished(self) -> None:
        self.submit(manufacturer_part_number="ABC1234-A")

        run = ResearchRun.objects.get()

        self.assertEqual(run.current_state, ResearchRunState.CREATED)
        self.assertEqual(run.state, "CREATED")
        self.assertIsNone(run.started_at)
        self.assertIsNone(run.finished_at)
        self.assertIsNotNone(run.created_at)

    def test_creation_goes_through_the_supported_manager_api(self) -> None:
        """The view calls `create_from_request`, not a raw insert.

        Observed rather than read off the source: the manager method is the one
        supported creation path, and watching the canonical request arrive there
        shows which route the web layer took. It also shows what it handed over
        — a `ResearchRequest`, not two loose strings.
        """
        with mock.patch.object(
            ResearchRun.objects,
            "create_from_request",
            wraps=ResearchRun.objects.create_from_request,
        ) as create_from_request:
            self.submit(
                manufacturer_part_number="ABC1234-A",
                description="24 port managed switch",
            )

        create_from_request.assert_called_once()
        submitted = create_from_request.call_args.args[0]

        self.assertEqual(submitted.manufacturer_part_number, "ABC1234-A")
        self.assertEqual(submitted.description, "24 port managed switch")
        self.assertEqual(ResearchRun.objects.count(), 1)

    def test_a_successful_submission_redirects_to_that_run(self) -> None:
        response = self.submit(manufacturer_part_number="ABC1234-A")
        run = ResearchRun.objects.get()

        self.assertEqual(response.status_code, 302)
        self.assertEqual(
            response["Location"],
            reverse("research-detail", kwargs={"run_id": run.id}),
        )

    def test_following_the_redirect_shows_the_same_run(self) -> None:
        response = self.client.post(
            reverse("research-new"),
            {
                "manufacturer_part_number": "ABC1234-A",
                "description": "24 port managed switch",
            },
            follow=True,
        )
        run = ResearchRun.objects.get()

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, str(run.id))
        self.assertContains(response, "ABC1234-A")

    def test_reloading_the_report_creates_no_second_run(self) -> None:
        """Post/Redirect/Get: the address you land on is a plain GET."""
        self.submit(manufacturer_part_number="ABC1234-A")
        run = ResearchRun.objects.get()
        detail_url = reverse("research-detail", kwargs={"run_id": run.id})

        for _ in range(3):
            self.assertEqual(self.client.get(detail_url).status_code, 200)

        self.assertEqual(ResearchRun.objects.count(), 1)

    def test_a_part_number_only_request_round_trips(self) -> None:
        response = self.submit(manufacturer_part_number="ABC1234-A")
        run = ResearchRun.objects.get()

        self.assertEqual(response.status_code, 302)
        self.assertEqual(run.manufacturer_part_number, "ABC1234-A")
        self.assertEqual(run.description, "")
        self.assertContains(self.client.get(response["Location"]), "ABC1234-A")

    def test_a_description_only_request_round_trips(self) -> None:
        response = self.submit(description="rack mount rail kit, 2U")
        run = ResearchRun.objects.get()

        self.assertEqual(response.status_code, 302)
        self.assertEqual(run.manufacturer_part_number, "")
        self.assertEqual(run.description, "rack mount rail kit, 2U")
        self.assertContains(
            self.client.get(response["Location"]), "rack mount rail kit, 2U"
        )

    def test_two_submissions_create_two_distinct_runs(self) -> None:
        first = self.submit(manufacturer_part_number="ABC1234-A")
        second = self.submit(manufacturer_part_number="ABC1234-B")

        self.assertEqual(ResearchRun.objects.count(), 2)
        self.assertNotEqual(first["Location"], second["Location"])


class CsrfTests(TestCase):
    """CSRF protection is on, and stays on."""

    def test_a_post_without_a_csrf_token_is_refused(self) -> None:
        strict_client = Client(enforce_csrf_checks=True)

        response = strict_client.post(
            reverse("research-new"),
            {"manufacturer_part_number": "ABC1234-A", "description": ""},
        )

        self.assertEqual(response.status_code, 403)
        self.assertEqual(ResearchRun.objects.count(), 0)

    def test_a_post_with_a_csrf_token_succeeds(self) -> None:
        strict_client = Client(enforce_csrf_checks=True)
        strict_client.get(reverse("research-new"))
        token = strict_client.cookies["csrftoken"].value

        response = strict_client.post(
            reverse("research-new"),
            {
                "manufacturer_part_number": "ABC1234-A",
                "description": "",
                "csrfmiddlewaretoken": token,
            },
        )

        self.assertEqual(response.status_code, 302)
        self.assertEqual(ResearchRun.objects.count(), 1)


class RootRedirectTests(TestCase):
    def test_the_root_address_leads_to_the_form(self) -> None:
        response = self.client.get("/")

        self.assertEqual(response.status_code, 302)
        self.assertEqual(response["Location"], reverse("research-new"))

    def test_the_root_address_creates_nothing(self) -> None:
        self.client.get("/", follow=True)

        self.assertEqual(ResearchRun.objects.count(), 0)
