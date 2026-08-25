"""The standalone intake form (PRODUCT-INTEL.1B, 4C-C).

The form's whole job is translation: raw strings in, a canonical
`ResearchRequest` out, or a readable error. These tests therefore check what it
*delegates* as hard as what it accepts — a form that quietly grew its own
whitespace or part-number rules would still pass a happy-path test while
silently owning a policy that belongs to the domain.
"""

from __future__ import annotations

from unittest import mock

from django.test import SimpleTestCase, TestCase
from django.urls import reverse

from product_intelligence.domain import ResearchRequest
from product_intelligence.runs.models import ResearchRun
from product_intelligence.web.forms import ResearchRequestForm


class FormFieldTests(SimpleTestCase):
    def test_the_form_offers_a_part_number_and_a_description(self) -> None:
        form = ResearchRequestForm()

        self.assertEqual(
            list(form.fields),
            ["manufacturer_part_number", "description"],
        )

    def test_both_fields_are_individually_optional(self) -> None:
        """Neither field is required on its own; the pair rule is the contract's."""
        form = ResearchRequestForm()

        self.assertFalse(form.fields["manufacturer_part_number"].required)
        self.assertFalse(form.fields["description"].required)

    def test_a_part_number_and_a_description_are_accepted(self) -> None:
        form = ResearchRequestForm(
            {
                "manufacturer_part_number": "MZ-V8P1T0B/AM",
                "description": "1TB NVMe M.2 solid state drive",
            }
        )

        self.assertTrue(form.is_valid())
        self.assertEqual(
            form.research_request,
            ResearchRequest(
                manufacturer_part_number="MZ-V8P1T0B/AM",
                description="1TB NVMe M.2 solid state drive",
            ),
        )

    def test_a_part_number_alone_is_accepted(self) -> None:
        form = ResearchRequestForm(
            {"manufacturer_part_number": "ABC1234-A", "description": ""}
        )

        self.assertTrue(form.is_valid())
        self.assertEqual(form.research_request.manufacturer_part_number, "ABC1234-A")
        self.assertEqual(form.research_request.description, "")

    def test_a_description_alone_is_accepted(self) -> None:
        form = ResearchRequestForm(
            {"manufacturer_part_number": "", "description": "rack mount rail kit, 2U"}
        )

        self.assertTrue(form.is_valid())
        self.assertEqual(form.research_request.manufacturer_part_number, "")
        self.assertEqual(form.research_request.description, "rack mount rail kit, 2U")

    def test_an_empty_submission_is_rejected(self) -> None:
        form = ResearchRequestForm({"manufacturer_part_number": "", "description": ""})

        self.assertFalse(form.is_valid())
        self.assertTrue(form.non_field_errors())

    def test_a_whitespace_only_submission_is_rejected(self) -> None:
        """Whitespace is not content — and the contract, not the form, says so."""
        form = ResearchRequestForm(
            {"manufacturer_part_number": "   ", "description": "\t\n "}
        )

        self.assertFalse(form.is_valid())

    def test_surrounding_whitespace_is_canonicalized_by_the_contract(self) -> None:
        form = ResearchRequestForm(
            {
                "manufacturer_part_number": "  ABC1234-A \n",
                "description": "\t 24 port  managed switch \t",
            }
        )

        self.assertTrue(form.is_valid())
        self.assertEqual(form.research_request.manufacturer_part_number, "ABC1234-A")
        # Interior spacing survives: stripping is a boundary rule, not a
        # rewriting one.
        self.assertEqual(form.research_request.description, "24 port  managed switch")

    def test_the_form_does_not_normalize_a_part_number(self) -> None:
        """Case, punctuation, hyphens, and interior spacing are left alone.

        Part-number normalization is a deterministic identity decision (2A/3C).
        A version of it invented at the transport boundary would be a matching
        rule in the one layer forbidden to make one — and one character can mean
        a different product.
        """
        raw = "abc 1234_a/b.c-D"
        form = ResearchRequestForm(
            {"manufacturer_part_number": raw, "description": ""}
        )

        self.assertTrue(form.is_valid())
        self.assertEqual(form.research_request.manufacturer_part_number, raw)

    def test_no_canonical_request_exists_for_an_invalid_submission(self) -> None:
        form = ResearchRequestForm({"manufacturer_part_number": "", "description": ""})

        self.assertFalse(form.is_valid())
        with self.assertRaises(ValueError):
            form.research_request


class FormPageTests(TestCase):
    def test_the_form_page_is_served(self) -> None:
        response = self.client.get(reverse("research-new"))

        self.assertEqual(response.status_code, 200)

    def test_the_page_contains_both_input_fields(self) -> None:
        response = self.client.get(reverse("research-new"))
        html = response.content.decode()

        self.assertIn('name="manufacturer_part_number"', html)
        self.assertIn('name="description"', html)

    def test_the_page_states_that_research_will_execute_on_submit(self) -> None:
        response = self.client.get(reverse("research-new"))

        self.assertContains(response, "Run Market Research")

    def test_a_get_never_creates_a_run_even_with_query_parameters(self) -> None:
        """The launcher entry point is 5B. A GET is a form display, full stop."""
        response = self.client.get(
            reverse("research-new"),
            {"mpn": "ABC1234-A", "description": "24 port managed switch"},
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(ResearchRun.objects.count(), 0)

    def test_an_invalid_submission_creates_no_run_and_shows_the_error(self) -> None:
        response = self.client.post(
            reverse("research-new"),
            {"manufacturer_part_number": "  ", "description": ""},
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(ResearchRun.objects.count(), 0)
        self.assertContains(response, "at least a manufacturer part")

    def test_reposting_an_invalid_submission_still_creates_nothing(self) -> None:
        for _ in range(2):
            self.client.post(
                reverse("research-new"),
                {"manufacturer_part_number": "", "description": ""},
            )

        self.assertEqual(ResearchRun.objects.count(), 0)

    def test_the_form_page_carries_a_csrf_token(self) -> None:
        response = self.client.get(reverse("research-new"))

        self.assertContains(response, "csrfmiddlewaretoken")


class FormExecutionIntegrationTests(TestCase):
    """POST form submission triggers execution (4C-C)."""

    def test_valid_submission_calls_execute_once(self) -> None:
        """A valid POST creates a run and calls execute_research_run once."""
        with mock.patch(
            "product_intelligence.web.views.execute_research_run",
            return_value=None,
        ) as mock_exec:
            self.client.post(
                reverse("research-new"),
                {
                    "manufacturer_part_number": "ABC1234-A",
                    "description": "24 port managed switch",
                },
            )

        self.assertEqual(mock_exec.call_count, 1)
        run = ResearchRun.objects.get()
        mock_exec.assert_called_once_with(str(run.id))

    def test_valid_submission_creates_one_run(self) -> None:
        """A valid POST creates exactly one run."""
        with mock.patch(
            "product_intelligence.web.views.execute_research_run",
            return_value=None,
        ):
            self.client.post(
                reverse("research-new"),
                {
                    "manufacturer_part_number": "ABC1234-A",
                    "description": "",
                },
            )

        self.assertEqual(ResearchRun.objects.count(), 1)

    def test_invalid_submission_calls_execute_zero_times(self) -> None:
        """An invalid POST creates no run and calls execute zero times."""
        with mock.patch(
            "product_intelligence.web.views.execute_research_run",
            return_value=None,
        ) as mock_exec:
            self.client.post(
                reverse("research-new"),
                {
                    "manufacturer_part_number": "",
                    "description": "",
                },
            )

        self.assertEqual(ResearchRun.objects.count(), 0)
        mock_exec.assert_not_called()

    def test_execution_error_still_creates_run_and_redirects(self) -> None:
        """When execute_research_run raises ExecutionError, run is created and
        user is redirected to the report (actual terminalization is handled by
        the real executor, not by this mock)."""
        from product_intelligence.execution import ExecutionError

        with mock.patch(
            "product_intelligence.web.views.execute_research_run",
            side_effect=ExecutionError("search failed"),
        ):
            response = self.client.post(
                reverse("research-new"),
                {
                    "manufacturer_part_number": "ABC1234-A",
                    "description": "",
                },
            )

        # Run is created (CREATED state - the mock does not terminalize it)
        self.assertEqual(ResearchRun.objects.count(), 1)
        # We redirect to the report so the user can see the current state
        self.assertEqual(response.status_code, 302)
        self.assertIn("research", response["Location"])