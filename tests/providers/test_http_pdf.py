"""Tests for the HTTP PDF fetcher (PRODUCT-INTEL.6D)."""

import pytest
from datetime import datetime, timezone
from unittest.mock import patch, MagicMock, call

from product_intelligence.providers.http_pdf import (
    HttpPdfFetcher,
    FETCHER_ID,
    ACCEPTED_MEDIA_TYPES,
    DEFAULT_MAX_RESPONSE_BYTES,
    DEFAULT_TIMEOUT_SECONDS,
    DEFAULT_MAX_REDIRECTS,
    REDIRECT_STATUS_CODES,
)
from product_intelligence.providers.document import (
    DocumentFetchError,
    DocumentFetchRequest,
    FetchedDocument,
    UnsafeDocumentTargetError,
)


class TestHttpPdfFetcherConstruction:
    def test_default_construction(self) -> None:
        fetcher = HttpPdfFetcher()
        assert fetcher._timeout == DEFAULT_TIMEOUT_SECONDS
        assert fetcher._max_redirects == DEFAULT_MAX_REDIRECTS
        assert fetcher._max_response_bytes == DEFAULT_MAX_RESPONSE_BYTES

    def test_custom_timeout(self) -> None:
        fetcher = HttpPdfFetcher(timeout=5.0)
        assert fetcher._timeout == 5.0

    def test_zero_timeout_refused(self) -> None:
        with pytest.raises(ValueError, match="timeout must be positive"):
            HttpPdfFetcher(timeout=0)

    def test_negative_timeout_refused(self) -> None:
        with pytest.raises(ValueError, match="timeout must be positive"):
            HttpPdfFetcher(timeout=-1)

    def test_zero_redirects_allowed(self) -> None:
        fetcher = HttpPdfFetcher(max_redirects=0)
        assert fetcher._max_redirects == 0

    def test_negative_redirects_refused(self) -> None:
        with pytest.raises(ValueError, match="max_redirects must not be negative"):
            HttpPdfFetcher(max_redirects=-1)

    def test_custom_max_bytes(self) -> None:
        fetcher = HttpPdfFetcher(max_response_bytes=1_000_000)
        assert fetcher._max_response_bytes == 1_000_000

    def test_zero_max_bytes_refused(self) -> None:
        with pytest.raises(ValueError, match="max_response_bytes must be positive"):
            HttpPdfFetcher(max_response_bytes=0)


class TestHttpPdfFetcherFetch:
    def test_non_request_type_refused(self) -> None:
        fetcher = HttpPdfFetcher()
        with pytest.raises(TypeError, match="request must be a DocumentFetchRequest"):
            fetcher.fetch("not a request")  # type: ignore

    def _make_response(self, content_type: str = "application/pdf", body: bytes = b"%PDF test"):
        mock_response = MagicMock()
        mock_response.headers.get.return_value = content_type
        mock_response.read.return_value = body
        mock_response.status = 200
        mock_response.getcode.return_value = 200
        mock_response.__enter__ = MagicMock(return_value=mock_response)
        mock_response.__exit__ = MagicMock(return_value=False)
        return mock_response

    @patch("product_intelligence.providers.http_pdf._assert_destination_is_public")
    @patch("product_intelligence.providers.http_pdf._build_opener")
    def test_successful_pdf_fetch(self, mock_build_opener, mock_assert_public) -> None:
        mock_response = self._make_response()
        mock_opener = MagicMock()
        mock_opener.open.return_value = mock_response
        mock_build_opener.return_value = mock_opener

        fetcher = HttpPdfFetcher(clock=lambda: datetime(2025, 1, 1, tzinfo=timezone.utc))
        req = DocumentFetchRequest(url="https://example.com/doc.pdf")
        result = fetcher.fetch(req)

        assert isinstance(result, FetchedDocument)
        assert result.final_url == "https://example.com/doc.pdf"
        assert result.content_type == "application/pdf"
        assert result.body_bytes == b"%PDF test"
        assert result.body_byte_count == 9
        assert result.fetcher_id == FETCHER_ID

    @patch("product_intelligence.providers.http_pdf._assert_destination_is_public")
    @patch("product_intelligence.providers.http_pdf._build_opener")
    def test_non_pdf_content_type_refused(self, mock_build_opener, mock_assert_public) -> None:
        mock_response = self._make_response(content_type="text/html")
        mock_opener = MagicMock()
        mock_opener.open.return_value = mock_response
        mock_build_opener.return_value = mock_opener

        fetcher = HttpPdfFetcher()
        req = DocumentFetchRequest(url="https://example.com/page.html")
        with pytest.raises(DocumentFetchError, match="PDF documents only"):
            fetcher.fetch(req)

    @patch("product_intelligence.providers.http_pdf._assert_destination_is_public")
    @patch("product_intelligence.providers.http_pdf._build_opener")
    def test_oversized_pdf_refused_not_truncated(self, mock_build_opener, mock_assert_public) -> None:
        body = b"x" * (DEFAULT_MAX_RESPONSE_BYTES + 1)
        mock_response = self._make_response(body=body)
        mock_response.headers.get.side_effect = lambda k, d=None: (
            "10000000000" if k == "Content-Length" else "application/pdf"
        )
        mock_opener = MagicMock()
        mock_opener.open.return_value = mock_response
        mock_build_opener.return_value = mock_opener

        fetcher = HttpPdfFetcher(max_response_bytes=DEFAULT_MAX_RESPONSE_BYTES)
        req = DocumentFetchRequest(url="https://example.com/big.pdf")
        with pytest.raises(DocumentFetchError, match="above"):
            fetcher.fetch(req)


# ---------------------------------------------------------------------------
# Real redirect tests
# ---------------------------------------------------------------------------

class TestHttpPdfFetcherRedirects:
    """Real HTTP redirect simulation."""

    def _make_http_error(self, code: int, location: str | None = None):
        import urllib.error
        headers = MagicMock()
        headers.get.return_value = location
        exc = urllib.error.HTTPError(
            url="https://example.com/original.pdf",
            code=code,
            msg="Redirect",
            hdrs=headers,
            fp=None,
        )
        exc.close = MagicMock()
        return exc

    @patch("product_intelligence.providers.http_pdf._assert_destination_is_public")
    @patch("product_intelligence.providers.http_pdf._build_opener")
    def test_final_url_preserved_after_redirect(self, mock_build_opener, mock_assert_public) -> None:
        """Actually simulate: requested URL -> HTTP 302 -> final PDF URL."""
        original_url = "https://example.com/redirect.pdf"
        final_url = "https://cdn.example.com/datasheet.pdf"

        mock_response = MagicMock()
        mock_response.headers.get.return_value = "application/pdf"
        mock_response.read.return_value = b"%PDF real"
        mock_response.__enter__ = MagicMock(return_value=mock_response)
        mock_response.__exit__ = MagicMock(return_value=False)

        mock_opener = MagicMock()
        # First call raises HTTPError (302 redirect), second call returns PDF
        redirect_exc = self._make_http_error(302, final_url)
        mock_opener.open.side_effect = [redirect_exc, mock_response]
        mock_build_opener.return_value = mock_opener

        fetcher = HttpPdfFetcher(
            max_redirects=3,
            clock=lambda: datetime(2025, 1, 1, tzinfo=timezone.utc),
        )
        req = DocumentFetchRequest(url=original_url)
        result = fetcher.fetch(req)

        assert result.requested_url == original_url
        assert result.final_url == final_url
        assert result.redirect_count == 1

    @patch("product_intelligence.providers.http_pdf._assert_destination_is_public")
    @patch("product_intelligence.providers.http_pdf._build_opener")
    def test_redirect_to_credential_url_refused(self, mock_build_opener, mock_assert_public) -> None:
        """Redirect to a URL with credentials must be refused."""
        original_url = "https://example.com/doc.pdf"
        credential_url = "https://user:pass@evil.com/doc.pdf"

        mock_opener = MagicMock()
        redirect_exc = self._make_http_error(302, credential_url)
        mock_opener.open.side_effect = [redirect_exc]
        mock_build_opener.return_value = mock_opener

        fetcher = HttpPdfFetcher()
        req = DocumentFetchRequest(url=original_url)
        with pytest.raises(UnsafeDocumentTargetError, match="refused redirect"):
            fetcher.fetch(req)

    @patch("product_intelligence.providers.http_pdf._assert_destination_is_public")
    @patch("product_intelligence.providers.http_pdf._build_opener")
    def test_redirect_limit_exceeded(self, mock_build_opener, mock_assert_public) -> None:
        """Too many redirects -> DocumentFetchError."""
        mock_opener = MagicMock()
        # Chain of redirects that exceeds limit
        def always_redirect(*args, **kwargs):
            exc = self._make_http_error(302, "https://example.com/next.pdf")
            raise exc
        mock_opener.open.side_effect = always_redirect
        mock_build_opener.return_value = mock_opener

        fetcher = HttpPdfFetcher(max_redirects=2)
        req = DocumentFetchRequest(url="https://example.com/start.pdf")
        with pytest.raises(DocumentFetchError, match="exceeded.*redirects"):
            fetcher.fetch(req)


# ---------------------------------------------------------------------------
# Response size boundary — body-level oversize
# ---------------------------------------------------------------------------

class TestHttpPdfFetcherBodyOversize:
    """Body-level oversize test WITHOUT usable Content-Length."""

    @patch("product_intelligence.providers.http_pdf._assert_destination_is_public")
    @patch("product_intelligence.providers.http_pdf._build_opener")
    def test_body_oversize_without_content_length(self, mock_build_opener, mock_assert_public) -> None:
        """response.read(max+1) returns max+1 bytes -> DocumentFetchError."""
        max_bytes = 1000
        body = b"x" * (max_bytes + 1)

        mock_response = MagicMock()
        # No Content-Length header
        mock_response.headers.get.return_value = "application/pdf"
        mock_response.read.return_value = body
        mock_response.__enter__ = MagicMock(return_value=mock_response)
        mock_response.__exit__ = MagicMock(return_value=False)

        mock_opener = MagicMock()
        mock_opener.open.return_value = mock_response
        mock_build_opener.return_value = mock_opener

        fetcher = HttpPdfFetcher(max_response_bytes=max_bytes)
        req = DocumentFetchRequest(url="https://example.com/no-cl.pdf")
        with pytest.raises(DocumentFetchError, match="returned more than"):
            fetcher.fetch(req)


class TestHttpPdfFetcherContentTypes:
    def test_only_pdf_accepted(self) -> None:
        assert ACCEPTED_MEDIA_TYPES == frozenset({"application/pdf"})

    def test_html_not_accepted(self) -> None:
        assert "text/html" not in ACCEPTED_MEDIA_TYPES

    def test_json_not_accepted(self) -> None:
        assert "application/json" not in ACCEPTED_MEDIA_TYPES


class TestHttpPdfFetcherProviderBoundary:
    def test_no_enterprise_ssd_import(self) -> None:
        import product_intelligence.providers.http_pdf as mod
        source = open(mod.__file__).read()
        assert "enterprise_ssd" not in source.lower()
        assert "SequentialRead" not in source
        assert "DWPD" not in source
        assert "capacity" not in source
