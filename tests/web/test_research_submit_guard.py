"""Web/template tests: research form duplicate-click guard (PROD-FIX1,
defect 5).

Market research is synchronous and may take significant time. A
front-end-only guard on the new-research form prevents rapid repeat
clicks from firing repeated submissions:

* on a valid form submit the button is immediately disabled;
* the visible text changes to ``Researching…``;
* the normal POST continues (no interception, no backend change);
* if client-side validation prevents submission, the button is NOT
  permanently disabled.

This is UX protection only — it is NOT a backend dedupe guarantee: no
run sharing, no MPN locking, no caching, no lifecycle change. The guard
is plain inline JavaScript (no framework).
"""

from __future__ import annotations

from unittest import mock

from django.test import TestCase, Client
from django.urls import reverse


class TestResearchSubmitGuardRendering(TestCase):
    """The rendered new-research page carries the guard contract."""

    def setUp(self) -> None:
        self.client = Client()

    def _page(self) -> str:
        response = self.client.get(reverse("research-new"))
        assert response.status_code == 200
        return response.content.decode()

    def test_form_has_guard_id(self) -> None:
        html = self._page()
        assert 'id="research-new-form"' in html

    def test_submit_button_has_guard_id_and_default_text(self) -> None:
        html = self._page()
        assert 'id="research-submit-button"' in html
        assert ">Run Market Research</button>" in html
        # The button must NOT be disabled in the initial render
        import re

        match = re.search(
            r'<button[^>]*id="research-submit-button"[^>]*>', html
        )
        assert match is not None
        assert "disabled" not in match.group(0)

    def test_guard_script_attached_to_submit(self) -> None:
        html = self._page()
        assert "form.addEventListener(\"submit\"" in html
        assert "research-new-form" in html
        assert "research-submit-button" in html

    def test_guard_disables_button_on_submit(self) -> None:
        html = self._page()
        # Immediately disable on submit
        assert "button.disabled = true" in html

    def test_guard_changes_visible_text_to_researching(self) -> None:
        html = self._page()
        # \u2026 is the horizontal ellipsis; the rendered text is
        # "Researching…"
        assert "Researching\\u2026" in html

    def test_guard_respects_client_validation(self) -> None:
        html = self._page()
        # If client-side validation prevents submission, the button must
        # not be permanently disabled: the handler checks validity first.
        assert "form.checkValidity" in html
        # The validity check comes BEFORE the disable (guard ordering)
        check_pos = html.index("form.checkValidity")
        disable_pos = html.index("button.disabled = true")
        assert check_pos < disable_pos

    def test_guard_is_inline_plain_javascript(self) -> None:
        html = self._page()
        # No framework, no external script asset: the guard is a small
        # inline <script> block.
        assert "<script>" in html
        assert "src=" not in html.split("<script>")[1].split("</script>")[0]


class TestResearchSubmitGuardBehavior(TestCase):
    """The guard is UX-only: the server contract is unchanged."""

    def setUp(self) -> None:
        self.client = Client()

    def test_valid_submission_still_executes_exactly_once(self) -> None:
        """The POST still runs the research exactly once (no backend
        dedupe added or removed)."""
        with mock.patch(
            "product_intelligence.web.views.execute_research_run",
            return_value=None,
        ) as mock_exec:
            response = self.client.post(
                reverse("research-new"),
                {
                    "manufacturer_part_number": "GUARD-MPN-1",
                    "description": "guard test product",
                },
            )
        # Redirect to the report (normal flow)
        assert response.status_code == 302
        mock_exec.assert_called_once()

    def test_no_backend_dedupe_state_introduced(self) -> None:
        """Two distinct valid submissions still create two distinct runs
        — the guard shares no in-progress run and adds no MPN lock."""
        with mock.patch(
            "product_intelligence.web.views.execute_research_run",
            return_value=None,
        ) as mock_exec:
            self.client.post(
                reverse("research-new"),
                {"manufacturer_part_number": "GUARD-MPN-2", "description": "a"},
            )
            self.client.post(
                reverse("research-new"),
                {"manufacturer_part_number": "GUARD-MPN-2", "description": "b"},
            )
        assert mock_exec.call_count == 2
        from product_intelligence.runs.models import ResearchRun

        assert ResearchRun.objects.count() == 2

    def test_researching_text_not_the_initial_button_text(self) -> None:
        """The initial page never shows 'Researching…' as the button label
        (it only appears after a client-side submit)."""
        response = self.client.get(reverse("research-new"))
        html = response.content.decode()
        # The template source contains the JS string (escaped), but the
        # rendered BUTTON text is still the default label
        import re

        match = re.search(
            r'<button[^>]*id="research-submit-button"[^>]*>(.*?)</button>',
            html,
            re.S,
        )
        assert match is not None
        assert match.group(1).strip() == "Run Market Research"
