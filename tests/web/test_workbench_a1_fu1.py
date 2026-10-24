"""PILOT-UX-WORKBENCH-A1-FU1 — standards-mode document structure.

Root cause of the A1 390px capture clipping: the rendered pages carried no
``<!DOCTYPE html>`` (and no explicit ``<html>``/``<head>``/``<body>``
envelope), so browsers parsed them in quirks mode (BackCompat). The mobile
viewport contract (``width=device-width``) and the programmatic layout audit
could not be trusted on such documents, and the committed 390px captures
proved the pages laid out wider than the requested CSS viewport while the
old overflow-only probe (measuring a different, CDP-emulated path) reported
zero findings.

These nodes pin the corrected document envelope on the rendered HTML (the
repeatable, CI-safe half of the viewport-fidelity contract; the browser half
lives in ``scripts/layout_probe.js`` /
``scripts/capture_preview_screenshots.js``, which now hard-fail when the
measured layout viewport differs from the requested width).

Additive: the 33 A1 nodes in ``tests/web/test_workbench_a1.py`` are
untouched.
"""

from __future__ import annotations

from html.parser import HTMLParser

from django.test import TestCase
from django.urls import reverse

# Tags that are BODY content: none of them may appear before <body> opens.
BODY_CONTENT_TAGS = {
    "h1", "h2", "h3", "h4", "main", "header", "footer", "nav",
    "form", "table", "input", "textarea", "button", "script", "section",
    "a", "p", "div", "dl", "dt", "dd", "ul", "ol", "li", "details", "summary",
}

VIEWPORT_META_CONTENT = "width=device-width, initial-scale=1"


class _DocumentStructureParser(HTMLParser):
    """Records the document envelope structure of a rendered page."""

    VOID = {
        "area", "base", "br", "col", "embed", "hr", "img", "input",
        "link", "meta", "param", "source", "track", "wbr",
    }

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.first_decl: str | None = None
        self.saw_html = self.saw_head = self.saw_body = False
        self.html_count = self.head_count = self.body_count = 0
        self.head_open_depth = 0
        self.head_still_open_at_body = False
        self.viewport_meta: str | None = None
        self.charset_meta = False
        self.title_in_head = False
        self.body_content_before_body: list[str] = []
        self.html_closed = False
        self.trailing_after_html_close: list[str] = []
        self.stack: list[str] = []

    def handle_decl(self, decl) -> None:
        if self.first_decl is None:
            self.first_decl = decl.strip()

    def handle_starttag(self, tag, attrs) -> None:
        if tag == "html":
            self.saw_html = True
            self.html_count += 1
        elif tag == "head":
            self.saw_head = True
            self.head_count += 1
            self.head_open_depth += 1
        elif tag == "body":
            self.saw_body = True
            self.body_count += 1
            self.head_still_open_at_body = self.head_open_depth > 0
            self.head_open_depth = 0
        if not self.saw_body and tag in BODY_CONTENT_TAGS:
            self.body_content_before_body.append(tag)
        if self.head_open_depth > 0:
            if tag == "meta":
                attrd = dict(attrs)
                if attrd.get("name") == "viewport":
                    self.viewport_meta = attrd.get("content")
                if "charset" in attrd:
                    self.charset_meta = True
            elif tag == "title":
                self.title_in_head = True
        if tag not in self.VOID:
            self.stack.append(tag)

    def handle_endtag(self, tag) -> None:
        if tag in self.VOID:
            return
        if tag == "html":
            self.html_closed = True
        if tag == "head":
            self.head_open_depth -= 1
        while self.stack and self.stack[-1] != tag:
            self.stack.pop()
        if self.stack:
            self.stack.pop()

    def handle_data(self, data) -> None:
        if self.html_closed and data.strip():
            self.trailing_after_html_close.append(data.strip()[:40])


def _structure(html: str) -> _DocumentStructureParser:
    p = _DocumentStructureParser()
    p.feed(html)
    p.close()
    return p


def _assert_valid_envelope(p: _DocumentStructureParser, page: str) -> None:
    assert p.first_decl is not None, f"{page}: no doctype declaration at all"
    assert p.first_decl.startswith("DOCTYPE html"), (
        f"{page}: document does not begin with <!DOCTYPE html> "
        f"(got {p.first_decl!r}); a missing doctype puts the page in "
        "quirks mode, where the mobile viewport contract is not reliable"
    )
    assert p.html_count == 1, f"{page}: expected exactly one <html>, got {p.html_count}"
    assert p.head_count == 1, f"{page}: expected exactly one <head>, got {p.head_count}"
    assert p.body_count == 1, f"{page}: expected exactly one <body>, got {p.body_count}"
    assert p.saw_html and p.saw_head and p.saw_body, f"{page}: html/head/body envelope incomplete"
    assert not p.head_still_open_at_body, f"{page}: </head> does not precede <body>"
    assert p.charset_meta, f"{page}: no charset meta in <head>"
    assert p.title_in_head, f"{page}: no <title> in <head>"
    assert p.body_content_before_body == [], (
        f"{page}: body content leaked into <head>: {p.body_content_before_body}"
    )
    assert p.html_closed, f"{page}: document is not closed with </html>"
    assert p.trailing_after_html_close == [], (
        f"{page}: content after </html>: {p.trailing_after_html_close}"
    )
    assert p.stack == [], f"{page}: unbalanced markup, open tags {p.stack}"


class StandardsModeDocumentTests(TestCase):
    """The rendered pages are valid standards-mode HTML documents.

    ``TestCase`` (per-test transaction rollback) so these nodes create
    throwaway runs without leaking into the session test database.
    """

    def _detail_html(self, mpn: str) -> str:
        from product_intelligence.domain import ResearchRequest
        from product_intelligence.runs.models import ResearchRun

        run = ResearchRun.objects.create_from_request(
            ResearchRequest(manufacturer_part_number=mpn, description="structure")
        )
        return self.client.get(f"/research/{run.id}").content.decode()

    def test_intake_page_is_standards_mode_document(self) -> None:
        html = self.client.get(reverse("research-new")).content.decode()
        p = _structure(html)
        _assert_valid_envelope(p, "intake")
        # The viewport meta is what makes 390 CSS px mean 390 device px on
        # mobile; it must be in <head>, with the effective contract text.
        self.assertEqual(p.viewport_meta, VIEWPORT_META_CONTENT)

    def test_detail_page_is_standards_mode_document(self) -> None:
        html = self._detail_html("FU1-STRUCT")
        p = _structure(html)
        _assert_valid_envelope(p, "detail")
        self.assertEqual(p.viewport_meta, VIEWPORT_META_CONTENT)
        # The report's page-column width declaration must not break the
        # envelope: it stays a <style> inside <head> (moved by FU1 from the
        # content block), and the frozen widened value is intact.
        head_part = html[: html.index("</head>")]
        self.assertIn("--pi-page-max-width: 70rem", head_part)
        self.assertIn("<style>", head_part)

    def test_intake_page_keeps_exactly_one_inline_script(self) -> None:
        # The PROD-FIX1 duplicate-click guard remains the page's single
        # inline script (frozen A1 contract) — the document envelope did not
        # add or move any script.
        html = self.client.get(reverse("research-new")).content.decode()
        self.assertEqual(html.count("<script>"), 1)
        self.assertIn('form.addEventListener("submit"', html)

    def test_document_beginning_is_the_doctype_with_no_prefix_bytes(self) -> None:
        htmls = (
            self.client.get(reverse("research-new")).content.decode(),
            self._detail_html("FU1-BEGIN"),
        )
        for i, html in enumerate(htmls):
            page = "intake" if i == 0 else "detail"
            self.assertTrue(
                html.lstrip().startswith("<!DOCTYPE html>"),
                f"{page}: rendered document must begin with the doctype, "
                f"got {html.lstrip()[:60]!r}",
            )
            self.assertEqual(html.count("<!DOCTYPE html>"), 1, page)
