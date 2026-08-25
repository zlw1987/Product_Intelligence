"""POST → ResearchRun → execute → redirect → report (PRODUCT-INTEL.1B, 4C-C).

The browser workflow creates exactly one run, calls the backend executor
synchronously, and redirects to the report. Tests here MUST mock
execute_research_run so they never make real paid Serper calls.
"""

from __future__ import annotations

from unittest import mock

from django.http import HttpResponse
from django.test import Client, TestCase
from django.urls import reverse

from product_intelligence.domain import ResearchRequest
from product_intelligence.domain.enums import ResearchRunState
from product_intelligence.runs.models import ResearchRun


class SuccessfulSubmissionTests(TestCase):
    """POST with valid data creates a run, executes it, and redirects."""

    def submit(self, **data: str) -> HttpResponse:
        payload = {"manufacturer_part_number": "", "description": ""}
        payload.update(data)
        return self.client.post(reverse("research-new"), payload)

    def test_a_valid_submission_creates_exactly_one_run(self) -> None:
        with mock.patch(
            "product_intelligence.web.views.execute_research_run",
            return_value=None,
        ) as mock_exec:
            self.submit(
                manufacturer_part_number="MZ-V8P1T0B/AM",
                description="1TB NVMe M.2 solid state drive",
            )

        self.assertEqual(ResearchRun.objects.count(), 1)
        mock_exec.assert_called_once()

    def test_execute_research_run_called_with_run_id(self) -> None:
        with mock.patch(
            "product_intelligence.web.views.execute_research_run",
            return_value=None,
        ) as mock_exec:
            self.submit(
                manufacturer_part_number="MZ-V8P1T0B/AM",
                description="1TB NVMe M.2 solid state drive",
            )

        run = ResearchRun.objects.get()
        mock_exec.assert_called_once_with(str(run.id))

    def test_canonical_request_values_are_correct(self) -> None:
        with mock.patch(
            "product_intelligence.web.views.execute_research_run",
            return_value=None,
        ):
            self.submit(
                manufacturer_part_number="  MZ-V8P1T0B/AM \n",
                description="\t 1TB NVMe  M.2 drive \t",
            )

        run = ResearchRun.objects.get()

        self.assertEqual(run.manufacturer_part_number, "MZ-V8P1T0B/AM")
        self.assertEqual(run.description, "1TB NVMe  M.2 drive")

    def test_creation_goes_through_the_supported_manager_api(self) -> None:
        """The view calls `create_from_request`, not a raw insert."""
        with mock.patch(
            "product_intelligence.web.views.execute_research_run",
            return_value=None,
        ):
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
        with mock.patch(
            "product_intelligence.web.views.execute_research_run",
            return_value=None,
        ):
            response = self.submit(manufacturer_part_number="ABC1234-A")

        run = ResearchRun.objects.get()

        self.assertEqual(response.status_code, 302)
        self.assertEqual(
            response["Location"],
            reverse("research-detail", kwargs={"run_id": run.id}),
        )

    def test_following_the_redirect_shows_the_same_run(self) -> None:
        with mock.patch(
            "product_intelligence.web.views.execute_research_run",
            return_value=None,
        ):
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
        with mock.patch(
            "product_intelligence.web.views.execute_research_run",
            return_value=None,
        ):
            self.submit(manufacturer_part_number="ABC1234-A")

        run = ResearchRun.objects.get()
        detail_url = reverse("research-detail", kwargs={"run_id": run.id})

        for _ in range(3):
            self.assertEqual(self.client.get(detail_url).status_code, 200)

        self.assertEqual(ResearchRun.objects.count(), 1)

    def test_a_part_number_only_request_round_trips(self) -> None:
        with mock.patch(
            "product_intelligence.web.views.execute_research_run",
            return_value=None,
        ):
            response = self.submit(manufacturer_part_number="ABC1234-A")

        run = ResearchRun.objects.get()

        self.assertEqual(response.status_code, 302)
        self.assertEqual(run.manufacturer_part_number, "ABC1234-A")
        self.assertEqual(run.description, "")
        self.assertContains(self.client.get(response["Location"]), "ABC1234-A")

    def test_a_description_only_request_round_trips(self) -> None:
        with mock.patch(
            "product_intelligence.web.views.execute_research_run",
            return_value=None,
        ):
            response = self.submit(description="rack mount rail kit, 2U")

        run = ResearchRun.objects.get()

        self.assertEqual(response.status_code, 302)
        self.assertEqual(run.manufacturer_part_number, "")
        self.assertEqual(run.description, "rack mount rail kit, 2U")
        self.assertContains(
            self.client.get(response["Location"]), "rack mount rail kit, 2U"
        )

    def test_two_submissions_create_two_distinct_runs(self) -> None:
        with mock.patch(
            "product_intelligence.web.views.execute_research_run",
            return_value=None,
        ):
            first = self.submit(manufacturer_part_number="ABC1234-A")
            second = self.submit(manufacturer_part_number="ABC1234-B")

        self.assertEqual(ResearchRun.objects.count(), 2)
        self.assertNotEqual(first["Location"], second["Location"])

    def test_two_submissions_call_execute_twice(self) -> None:
        with mock.patch(
            "product_intelligence.web.views.execute_research_run",
            return_value=None,
        ) as mock_exec:
            self.submit(manufacturer_part_number="ABC1234-A")
            self.submit(manufacturer_part_number="ABC1234-B")

        self.assertEqual(mock_exec.call_count, 2)


class InvalidSubmissionTests(TestCase):
    """Invalid form submission creates no run and does not call execute."""

    def test_an_invalid_submission_creates_no_run(self) -> None:
        response = self.client.post(
            reverse("research-new"),
            {"manufacturer_part_number": "  ", "description": ""},
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(ResearchRun.objects.count(), 0)

    def test_invalid_submission_does_not_call_execute(self) -> None:
        with mock.patch(
            "product_intelligence.web.views.execute_research_run",
            return_value=None,
        ) as mock_exec:
            self.client.post(
                reverse("research-new"),
                {"manufacturer_part_number": "  ", "description": ""},
            )

        mock_exec.assert_not_called()

    def test_reposting_an_invalid_submission_still_creates_nothing(self) -> None:
        for _ in range(2):
            self.client.post(
                reverse("research-new"),
                {"manufacturer_part_number": "", "description": ""},
            )

        self.assertEqual(ResearchRun.objects.count(), 0)


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
        with mock.patch(
            "product_intelligence.web.views.execute_research_run",
            return_value=None,
        ):
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


class GetPrefillTests(TestCase):
    """GET /research/new prefill behavior (4C-C, 5B)."""

    def test_mpn_only_prefill(self) -> None:
        """GET with mpn param prefill the MPN field only."""
        response = self.client.get(
            reverse("research-new"),
            {"mpn": "ABC1234-A"},
        )

        self.assertEqual(response.status_code, 200)
        html = response.content.decode()
        # Check the MPN field has the prefill value
        self.assertIn('value="ABC1234-A"', html)
        # Description should be empty
        self.assertIn('name="description"', html)

    def test_description_only_prefill(self) -> None:
        """GET with description param prefill the description field only."""
        response = self.client.get(
            reverse("research-new"),
            {"description": "rack mount rail kit, 2U"},
        )

        self.assertEqual(response.status_code, 200)
        html = response.content.decode()
        self.assertIn("rack mount rail kit, 2U", html)

    def test_both_prefill(self) -> None:
        """GET with both mpn and description prefill both fields."""
        response = self.client.get(
            reverse("research-new"),
            {"mpn": "ABC1234-A", "description": "24 port managed switch"},
        )

        self.assertEqual(response.status_code, 200)
        html = response.content.decode()
        self.assertIn('value="ABC1234-A"', html)
        self.assertIn("24 port managed switch", html)

    def test_reserved_characters_roundtrip(self) -> None:
        """Reserved characters in query params are handled correctly."""
        response = self.client.get(
            reverse("research-new"),
            {"mpn": "MZ-V8P1T0B/AM", "description": "1TB NVMe M.2 SSD"},
        )

        self.assertEqual(response.status_code, 200)
        html = response.content.decode()
        self.assertIn('value="MZ-V8P1T0B/AM"', html)
        self.assertIn("1TB NVMe M.2 SSD", html)

    def test_get_creates_zero_runs(self) -> None:
        """GET never creates a run regardless of query parameters."""
        for _ in range(3):
            self.client.get(
                reverse("research-new"),
                {"mpn": "ABC1234-A", "description": "24 port managed switch"},
            )

        self.assertEqual(ResearchRun.objects.count(), 0)

    def test_get_calls_execute_zero_times(self) -> None:
        """GET never calls execute_research_run."""
        with mock.patch(
            "product_intelligence.web.views.execute_research_run",
            return_value=None,
        ) as mock_exec:
            self.client.get(
                reverse("research-new"),
                {"mpn": "ABC1234-A"},
            )

        mock_exec.assert_not_called()

    def test_unknown_query_parameters_ignored(self) -> None:
        """Unknown query params don't break the page or cause errors."""
        response = self.client.get(
            reverse("research-new"),
            {"mpn": "ABC1234-A", "foo": "bar", "baz": "qux"},
        )

        self.assertEqual(response.status_code, 200)
        # Form still renders correctly
        self.assertIn('value="ABC1234-A"', response.content.decode())


class RetryIntegrationTests(TestCase):
    """Test POST /research/<uuid>/retry for FAILED runs (4C-C)."""

    def setUp(self) -> None:
        """Create a FAILED run for testing."""
        from django.utils import timezone

        self.run = ResearchRun.objects.create(
            manufacturer_part_number="TEST-MPN",
            description="Test description",
        )
        # Manually transition to FAILED state
        ResearchRun.objects.filter(id=self.run.id).update(
            state=ResearchRunState.FAILED,
            started_at=self.run.created_at,
            finished_at=timezone.now(),
        )
        self.run.refresh_from_db()

    def test_retry_post_creates_new_run(self) -> None:
        """POST /research/<uuid>/retry creates exactly one new run."""
        old_count = ResearchRun.objects.count()

        with mock.patch(
            "product_intelligence.web.views.execute_research_run",
            return_value=None,
        ):
            response = self.client.post(
                reverse("research-retry", kwargs={"run_id": self.run.id}),
            )

        self.assertEqual(ResearchRun.objects.count(), old_count + 1)

    def test_retry_get_returns_405(self) -> None:
        """GET /research/<uuid>/retry must return 405 Method Not Allowed."""
        response = self.client.get(
            reverse("research-retry", kwargs={"run_id": self.run.id})
        )

        self.assertEqual(response.status_code, 405)

    def test_retry_post_requires_csrf(self) -> None:
        """Retry POST enforces CSRF."""
        strict_client = Client(enforce_csrf_checks=True)
        # GET /research-retry returns 405 (method not allowed), so we get the CSRF token
        # from the detail page instead
        strict_client.get(
            reverse("research-detail", kwargs={"run_id": self.run.id})
        )
        token = strict_client.cookies["csrftoken"].value

        with mock.patch(
            "product_intelligence.web.views.execute_research_run",
            return_value=None,
        ):
            response = strict_client.post(
                reverse("research-retry", kwargs={"run_id": self.run.id}),
                {"csrfmiddlewaretoken": token},
            )

        self.assertEqual(response.status_code, 302)

    def test_retry_old_run_unchanged(self) -> None:
        """Old run remains FAILED and unchanged after retry."""
        old_id = self.run.id
        old_state = self.run.current_state
        old_mpn = self.run.manufacturer_part_number
        old_created = self.run.created_at

        with mock.patch(
            "product_intelligence.web.views.execute_research_run",
            return_value=None,
        ):
            self.client.post(
                reverse("research-retry", kwargs={"run_id": self.run.id}),
            )

        self.run.refresh_from_db()

        self.assertEqual(self.run.id, old_id)
        self.assertEqual(self.run.current_state, old_state)
        self.assertEqual(self.run.manufacturer_part_number, old_mpn)
        self.assertEqual(self.run.created_at, old_created)

    def test_retry_new_run_has_same_request(self) -> None:
        """New run has same MPN and description as old run."""
        with mock.patch(
            "product_intelligence.web.views.execute_research_run",
            return_value=None,
        ):
            self.client.post(
                reverse("research-retry", kwargs={"run_id": self.run.id}),
            )

        new_run = ResearchRun.objects.exclude(id=self.run.id).first()

        self.assertIsNotNone(new_run)
        self.assertEqual(new_run.manufacturer_part_number, "TEST-MPN")
        self.assertEqual(new_run.description, "Test description")

    def test_retry_execute_called_with_new_run_id(self) -> None:
        """execute_research_run is called with the new run id, not the old."""
        with mock.patch(
            "product_intelligence.web.views.execute_research_run",
            return_value=None,
        ) as mock_exec:
            self.client.post(
                reverse("research-retry", kwargs={"run_id": self.run.id}),
            )

        new_run = ResearchRun.objects.exclude(id=self.run.id).first()
        mock_exec.assert_called_once_with(str(new_run.id))

    def test_retry_on_non_failed_run_does_not_create_run(self) -> None:
        """Retry on CREATED run redirects without creating anything."""
        created_run = ResearchRun.objects.create(
            manufacturer_part_number="CREATED-MPN",
            description="Created run",
        )
        old_count = ResearchRun.objects.count()

        with mock.patch(
            "product_intelligence.web.views.execute_research_run",
            return_value=None,
        ):
            response = self.client.post(
                reverse("research-retry", kwargs={"run_id": created_run.id}),
            )

        self.assertEqual(response.status_code, 302)
        self.assertEqual(ResearchRun.objects.count(), old_count)


class RetryCsrfNegativeTest(TestCase):
    """Explicit CSRF negative test for retry POST."""

    def setUp(self) -> None:
        from django.utils import timezone

        self.run = ResearchRun.objects.create(
            manufacturer_part_number="TEST-MPN",
            description="Test description",
        )
        ResearchRun.objects.filter(id=self.run.id).update(
            state=ResearchRunState.FAILED,
            started_at=self.run.created_at,
            finished_at=timezone.now(),
        )
        self.run.refresh_from_db()

    def test_retry_post_without_csrf_is_refused(self) -> None:
        """POST /research/<uuid>/retry without CSRF token returns 403."""
        strict_client = Client(enforce_csrf_checks=True)
        strict_client.get(
            reverse("research-detail", kwargs={"run_id": self.run.id})
        )
        token = strict_client.cookies["csrftoken"].value

        with mock.patch(
            "product_intelligence.web.views.execute_research_run",
            return_value=None,
        ):
            # POST without the token
            response = strict_client.post(
                reverse("research-retry", kwargs={"run_id": self.run.id}),
                {},  # no csrfmiddlewaretoken
            )

        self.assertEqual(response.status_code, 403)
        # No new run was created
        self.assertEqual(ResearchRun.objects.count(), 1)


class RetrySnapshotNonCopyTest(TestCase):
    """Prove retry does not copy old run's snapshot or evidence records."""

    def setUp(self) -> None:
        from django.utils import timezone

        self.old_run = ResearchRun.objects.create(
            manufacturer_part_number="TEST-MPN",
            description="Test description",
        )
        # Create the old run in FAILED state (required for retry)
        ResearchRun.objects.filter(id=self.old_run.id).update(
            state=ResearchRunState.FAILED,
            started_at=self.old_run.created_at,
            finished_at=timezone.now(),
        )
        self.old_run.refresh_from_db()
        # Give the old run a snapshot (simulating it had one before failing)
        from product_intelligence.runs.models import PriceIntelligenceSnapshot
        PriceIntelligenceSnapshot.objects.create(
            run=self.old_run,
            schema_version=1,
            payload={"fake": "payload"},
        )
        self.old_run.refresh_from_db()

    def test_retry_does_not_copy_old_snapshot(self) -> None:
        """New retry run has no snapshot copied from the old FAILED run."""
        # Verify old run has snapshot
        self.assertTrue(
            hasattr(self.old_run, "price_intelligence_snapshot") and
            self.old_run.price_intelligence_snapshot is not None
        )

        with mock.patch(
            "product_intelligence.web.views.execute_research_run",
            return_value=None,
        ):
            self.client.post(
                reverse("research-retry", kwargs={"run_id": self.old_run.id}),
            )

        new_run = ResearchRun.objects.exclude(id=self.old_run.id).first()
        self.assertIsNotNone(new_run)

        # New run should NOT have a snapshot
        try:
            has_snapshot = new_run.price_intelligence_snapshot is not None
        except Exception:
            # price_intelligence_snapshot descriptor raises RelatedObjectDoesNotExist
            # when there is no snapshot, which is the expected case
            has_snapshot = False
        self.assertFalse(has_snapshot, "New run should not have a snapshot copied from old run")


class StartErrorNoticeTest(TestCase):
    """Tests for the ?start_error=1 transient notice."""

    def test_execution_exception_redirects_with_start_error(self) -> None:
        """Unexpected exception before execution starts -> redirect with start_error=1."""
        def patched_execute(run_id: str, **kwargs: Any) -> Any:
            raise RuntimeError("Unexpected server error")

        with mock.patch(
            "product_intelligence.web.views.execute_research_run",
            side_effect=patched_execute,
        ):
            response = self.client.post(
                reverse("research-new"),
                {
                    "manufacturer_part_number": "ABC1234-A",
                    "description": "",
                },
            )

        # Should redirect
        self.assertEqual(response.status_code, 302)
        self.assertIn("start_error=1", response["Location"])

        # Report shows safe notice, not raw exception
        report_response = self.client.get(response["Location"])
        html = report_response.content.decode()
        self.assertIn("not ready to execute", html)
        self.assertNotIn("Unexpected server error", html)
        self.assertNotIn("RuntimeError", html)
        self.assertNotIn("SERPER_API_KEY", html)

    def test_start_error_flag_renders_on_creatable_run(self) -> None:
        """?start_error=1 renders safe notice on CREATED run."""
        run = ResearchRun.objects.create(
            manufacturer_part_number="TEST-MPN",
            description="Test",
        )

        response = self.client.get(
            reverse("research-detail", kwargs={"run_id": run.id}),
            {"start_error": "1"},
        )

        html = response.content.decode()
        self.assertIn("not ready to execute", html)

    def test_start_error_flag_not_shown_without_flag(self) -> None:
        """Without ?start_error=1, the safe notice is not shown."""
        run = ResearchRun.objects.create(
            manufacturer_part_number="TEST-MPN",
            description="Test",
        )

        response = self.client.get(
            reverse("research-detail", kwargs={"run_id": run.id}),
        )

        html = response.content.decode()
        self.assertNotIn("not ready to execute", html)


class RetryErrorNoticeTest(TestCase):
    """Tests for the ?retry_error=1 transient notice."""

    def test_retry_run_failure_redirects_with_retry_error(self) -> None:
        """When retry_run itself fails, redirect to old run with retry_error=1."""
        from django.utils import timezone

        old_run = ResearchRun.objects.create(
            manufacturer_part_number="TEST-MPN",
            description="Test description",
        )
        ResearchRun.objects.filter(id=old_run.id).update(
            state=ResearchRunState.FAILED,
            started_at=old_run.created_at,
            finished_at=timezone.now(),
        )
        old_run.refresh_from_db()

        def patched_retry_run(failed_run: Any) -> Any:
            raise RuntimeError("retry_run failed")

        with mock.patch(
            "product_intelligence.web.views.retry_run",
            side_effect=patched_retry_run,
        ):
            response = self.client.post(
                reverse("research-retry", kwargs={"run_id": old_run.id}),
            )

        # Should redirect to old run with retry_error=1
        self.assertEqual(response.status_code, 302)
        self.assertIn(str(old_run.id), response["Location"])
        self.assertIn("retry_error=1", response["Location"])

        # Report shows safe retry notice
        report_response = self.client.get(response["Location"])
        html = report_response.content.decode()
        self.assertIn("could not be restarted", html)
        self.assertNotIn("retry_run failed", html)
        self.assertNotIn("RuntimeError", html)


class PreStartErrorSafeContentTest(TestCase):
    """Prove start_error/retry_error notices expose no sensitive content."""

    def test_start_error_exposes_no_serper_key(self) -> None:
        run = ResearchRun.objects.create(
            manufacturer_part_number="TEST-MPN",
            description="Test",
        )

        response = self.client.get(
            reverse("research-detail", kwargs={"run_id": run.id}),
            {"start_error": "1"},
        )

        html = response.content.decode()
        self.assertNotIn("SERPER_API_KEY", html)
        self.assertNotIn("api_key", html)
        self.assertNotIn("secret", html)

    def test_retry_error_exposes_no_serper_key(self) -> None:
        from django.utils import timezone

        run = ResearchRun.objects.create(
            manufacturer_part_number="TEST-MPN",
            description="Test",
        )
        ResearchRun.objects.filter(id=run.id).update(
            state=ResearchRunState.FAILED,
            started_at=run.created_at,
            finished_at=timezone.now(),
        )
        run.refresh_from_db()

        response = self.client.get(
            reverse("research-detail", kwargs={"run_id": run.id}),
            {"retry_error": "1"},
        )

        html = response.content.decode()
        self.assertNotIn("SERPER_API_KEY", html)
        self.assertNotIn("api_key", html)
        self.assertNotIn("secret", html)