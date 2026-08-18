"""The page-fetch contracts (PRODUCT-INTEL.3A).

`PageFetchRequest` and `FetchedPage` are validated at construction, so an
unfetchable request and an unattributable page cannot exist. Most of what
matters here is what they refuse.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from product_intelligence.providers.page import (
    ALLOWED_FETCH_SCHEMES,
    FetchedPage,
    PageFetchError,
    PageFetchRequest,
    UnsafeFetchTargetError,
    require_fetchable_url,
)

RETRIEVED_AT = datetime(2026, 8, 17, 12, 0, tzinfo=timezone.utc)


def _page(**overrides) -> FetchedPage:
    values = {
        "requested_url": "https://example.com/product",
        "final_url": "https://example.com/product",
        "retrieved_at": RETRIEVED_AT,
        "status_code": 200,
        "body_text": "<html></html>",
        "fetcher_id": "test",
    }
    values.update(overrides)
    return FetchedPage(**values)


class TestFetchableUrls:
    def test_an_absolute_https_url_is_accepted_as_observed(self) -> None:
        url = "https://example.com/a/b?c=d&e=f#g"

        assert require_fetchable_url(url) == url

    def test_surrounding_whitespace_is_removed(self) -> None:
        assert require_fetchable_url("  https://example.com/a  ") == (
            "https://example.com/a"
        )

    @pytest.mark.parametrize(
        "url",
        [
            "file:///etc/passwd",
            "ftp://example.com/x",
            "javascript:alert(1)",
            "data:text/html,<b>hi</b>",
            "gopher://example.com/",
        ],
    )
    def test_a_non_web_scheme_is_refused(self, url: str) -> None:
        """A fetcher honouring `file:` would read the server's own disk."""
        with pytest.raises(ValueError):
            require_fetchable_url(url)

    @pytest.mark.parametrize("url", ["/products/1", "//example.com/x", "example.com/x"])
    def test_a_relative_or_scheme_relative_url_is_refused(self, url: str) -> None:
        with pytest.raises(ValueError):
            require_fetchable_url(url)

    @pytest.mark.parametrize(
        "url",
        [
            "https://user:password@example.com/x",
            "https://user@example.com/x",
            "http://admin:hunter2@internal.example.com/",
        ],
    )
    def test_embedded_credentials_are_refused(self, url: str) -> None:
        """A request that cannot hold a credential beats a promise to strip one."""
        with pytest.raises(ValueError, match="credential"):
            require_fetchable_url(url)

    def test_a_blank_url_is_refused(self) -> None:
        with pytest.raises(ValueError):
            require_fetchable_url("   ")

    def test_a_non_string_url_is_a_caller_defect(self) -> None:
        with pytest.raises(TypeError):
            require_fetchable_url(object())

    def test_only_http_and_https_are_allowed(self) -> None:
        assert ALLOWED_FETCH_SCHEMES == frozenset({"http", "https"})


class TestPageFetchRequest:
    def test_it_carries_one_url_and_nothing_else(self) -> None:
        """No render mode, header override, cookie jar, or proxy selection.

        Each would be a way for a caller to weaken the fetcher's rules from
        outside. A test on the exact field list is what keeps that true.
        """
        from dataclasses import fields

        assert [field.name for field in fields(PageFetchRequest)] == ["url"]

    def test_it_validates_its_url_at_construction(self) -> None:
        with pytest.raises(ValueError):
            PageFetchRequest("file:///etc/passwd")

    def test_it_is_frozen(self) -> None:
        request = PageFetchRequest("https://example.com/x")

        with pytest.raises(Exception):
            request.url = "https://elsewhere.example/x"  # type: ignore[misc]


class TestFetchedPage:
    def test_it_records_what_was_returned(self) -> None:
        page = _page(
            body_text="<html>hi</html>",
            content_type="text/html; charset=utf-8",
            body_byte_count=15,
        )

        assert page.status_code == 200
        assert page.body_text == "<html>hi</html>"
        assert page.content_type == "text/html; charset=utf-8"
        assert page.body_byte_count == 15

    def test_requested_and_final_urls_are_both_required(self) -> None:
        """A redirect is evidence; keeping only one URL would discard it."""
        page = _page(
            requested_url="http://example.com/p",
            final_url="https://www.example.com/p",
            redirect_count=2,
        )

        assert page.requested_url == "http://example.com/p"
        assert page.final_url == "https://www.example.com/p"
        assert page.was_redirected is True

    def test_an_unredirected_page_reports_no_redirect(self) -> None:
        assert _page().was_redirected is False

    def test_it_holds_no_extracted_field(self) -> None:
        """Title, price, part number, seller: all 3A extraction, none of them here."""
        from dataclasses import fields

        assert [field.name for field in fields(FetchedPage)] == [
            "requested_url",
            "final_url",
            "retrieved_at",
            "status_code",
            "body_text",
            "content_type",
            "body_byte_count",
            "redirect_count",
            "fetcher_id",
        ]

    def test_a_naive_retrieval_time_is_refused(self) -> None:
        with pytest.raises(ValueError, match="timezone-aware"):
            _page(retrieved_at=datetime(2026, 8, 17, 12, 0))

    def test_a_non_utc_offset_is_accepted(self) -> None:
        """Awareness is the rule, not a particular zone."""
        moment = datetime(2026, 8, 17, 12, 0, tzinfo=timezone(timedelta(hours=-5)))

        assert _page(retrieved_at=moment).retrieved_at == moment

    def test_the_body_is_kept_exactly(self) -> None:
        """Not trimmed: a reviewer checks a parser against what the page said."""
        body = "\n  <html>  spaced  </html>  \n"

        assert _page(body_text=body).body_text == body

    def test_a_missing_fetcher_id_is_refused(self) -> None:
        with pytest.raises(ValueError, match="provenance"):
            _page(fetcher_id="   ")

    @pytest.mark.parametrize("field", ["body_byte_count", "redirect_count"])
    def test_a_negative_count_is_refused(self, field: str) -> None:
        with pytest.raises(ValueError):
            _page(**{field: -1})

    def test_a_boolean_status_code_is_refused(self) -> None:
        """`True` is an `int` in Python, and it is not a status code."""
        with pytest.raises(TypeError):
            _page(status_code=True)

    def test_a_non_string_body_is_refused(self) -> None:
        with pytest.raises(TypeError):
            _page(body_text=b"<html></html>")


class TestFailureConcepts:
    def test_a_refusal_is_distinguishable_from_a_failure(self) -> None:
        """The one subclass that earns its place.

        "We declined to go there" and "the site was down" have opposite
        meanings for whether a retry could ever succeed.
        """
        assert issubclass(UnsafeFetchTargetError, PageFetchError)

        with pytest.raises(PageFetchError):
            raise UnsafeFetchTargetError("refused")
