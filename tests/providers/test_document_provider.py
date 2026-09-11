"""Tests for the fetched-document provider boundary (PRODUCT-INTEL.6D)."""

import pytest
from datetime import datetime, timezone
from product_intelligence.providers.document import (
    DocumentFetchRequest,
    DocumentFetchError,
    FetchedDocument,
    UnsafeDocumentTargetError,
)


class TestDocumentFetchRequest:
    """DocumentFetchRequest validation."""

    def test_valid_url(self) -> None:
        req = DocumentFetchRequest(url="https://example.com/doc.pdf")
        assert req.url == "https://example.com/doc.pdf"

    def test_https_url(self) -> None:
        req = DocumentFetchRequest(url="https://www.seagate.com/path/to/file.pdf")
        assert req.url == "https://www.seagate.com/path/to/file.pdf"

    def test_http_url(self) -> None:
        req = DocumentFetchRequest(url="http://example.com/doc.pdf")
        assert req.url == "http://example.com/doc.pdf"

    def test_empty_url_refused(self) -> None:
        with pytest.raises(ValueError, match="url must be a non-empty string"):
            DocumentFetchRequest(url="")

    def test_non_string_url_refused(self) -> None:
        with pytest.raises(ValueError, match="url must be a non-empty string"):
            DocumentFetchRequest(url=123)  # type: ignore

    def test_file_url_refused(self) -> None:
        with pytest.raises(ValueError, match="must be an absolute http:// or https://"):
            DocumentFetchRequest(url="file:///etc/passwd")

    def test_data_url_refused(self) -> None:
        with pytest.raises(ValueError, match="must be an absolute http:// or https://"):
            DocumentFetchRequest(url="data:application/pdf;base64,abc")

    def test_no_host_refused(self) -> None:
        with pytest.raises(ValueError, match="must include a host"):
            DocumentFetchRequest(url="https:///path")

    def test_relative_url_refused(self) -> None:
        with pytest.raises(ValueError, match="must be an absolute http:// or https://"):
            DocumentFetchRequest(url="/path/to/file.pdf")

    def test_credential_url_refused(self) -> None:
        with pytest.raises(ValueError, match="must not embed credentials"):
            DocumentFetchRequest(url="https://user:pass@example.com/doc.pdf")

    def test_whitespace_stripped(self) -> None:
        req = DocumentFetchRequest(url="  https://example.com/doc.pdf  ")
        assert req.url == "https://example.com/doc.pdf"


class TestFetchedDocument:
    """FetchedDocument validation."""

    def _make_valid(self, **overrides) -> FetchedDocument:
        defaults = {
            "requested_url": "https://example.com/doc.pdf",
            "final_url": "https://example.com/doc.pdf",
            "retrieved_at": datetime(2025, 1, 1, 12, 0, 0, tzinfo=timezone.utc),
            "content_type": "application/pdf",
            "body_bytes": b"%PDF-1.4 test bytes",
            "body_byte_count": 19,
            "redirect_count": 0,
            "fetcher_id": "test-fetcher",
        }
        defaults.update(overrides)
        return FetchedDocument(**defaults)

    def test_valid_document(self) -> None:
        doc = self._make_valid()
        assert doc.requested_url == "https://example.com/doc.pdf"
        assert doc.final_url == "https://example.com/doc.pdf"
        assert doc.body_byte_count == 19
        assert doc.content_type == "application/pdf"

    def test_body_byte_count_must_match_len(self) -> None:
        with pytest.raises(ValueError, match="body_byte_count"):
            self._make_valid(body_bytes=b"%PDF-1.4 test bytes", body_byte_count=999)

    def test_naive_datetime_refused(self) -> None:
        with pytest.raises(ValueError, match="timezone-aware"):
            self._make_valid(
                retrieved_at=datetime(2025, 1, 1, 12, 0, 0)
            )

    def test_content_type_optional(self) -> None:
        doc = self._make_valid(content_type=None)
        assert doc.content_type is None

    def test_redirect_count_default(self) -> None:
        doc = self._make_valid()
        assert doc.redirect_count == 0

    def test_redirect_count_nonzero(self) -> None:
        doc = self._make_valid(redirect_count=2)
        assert doc.redirect_count == 2

    def test_negative_redirect_count_refused(self) -> None:
        with pytest.raises(ValueError, match="redirect_count must not be negative"):
            self._make_valid(redirect_count=-1)

    def test_empty_fetcher_id_refused(self) -> None:
        with pytest.raises(ValueError, match="fetcher_id must be a non-empty string"):
            self._make_valid(fetcher_id="")

    def test_non_bytes_body_refused(self) -> None:
        with pytest.raises(TypeError, match="body_bytes must be bytes"):
            self._make_valid(body_bytes="not bytes", body_byte_count=9)

    def test_empty_body_allowed(self) -> None:
        doc = self._make_valid(body_bytes=b"", body_byte_count=0)
        assert doc.body_byte_count == 0

    def test_body_byte_count_consistency(self) -> None:
        doc = self._make_valid()
        assert doc.body_byte_count == len(doc.body_bytes)

    # -- Credential rejection for both URL fields --

    def test_requested_url_with_credentials_rejected(self) -> None:
        """requested_url with embedded credentials must be rejected."""
        with pytest.raises(ValueError, match="must not embed credentials"):
            self._make_valid(
                requested_url="https://user:pass@example.com/doc.pdf",
            )

    def test_final_url_with_credentials_rejected(self) -> None:
        """final_url with embedded credentials must be rejected."""
        with pytest.raises(ValueError, match="must not embed credentials"):
            self._make_valid(
                final_url="https://user:pass@example.com/doc.pdf",
            )

    def test_requested_url_with_only_username_rejected(self) -> None:
        """requested_url with only username (no password) must be rejected."""
        with pytest.raises(ValueError, match="must not embed credentials"):
            self._make_valid(
                requested_url="https://user@example.com/doc.pdf",
            )

    def test_final_url_with_only_username_rejected(self) -> None:
        """final_url with only username (no password) must be rejected."""
        with pytest.raises(ValueError, match="must not embed credentials"):
            self._make_valid(
                final_url="https://user@example.com/doc.pdf",
            )


class TestDocumentFetchError:
    """DocumentFetchError is a plain Exception."""

    def test_document_fetch_error_is_exception(self) -> None:
        err = DocumentFetchError("connection timeout")
        assert isinstance(err, Exception)
        assert str(err) == "connection timeout"

    def test_unsafe_document_target_error_is_subclass(self) -> None:
        err = UnsafeDocumentTargetError("refused private address")
        assert isinstance(err, DocumentFetchError)
        assert isinstance(err, Exception)
        assert str(err) == "refused private address"


class TestDocumentBoundaryContainsNoBusinessLabels:
    """Provider/document boundary contains no Enterprise SSD business labels/rules."""

    def test_no_enterprise_ssd_import(self) -> None:
        import product_intelligence.providers.document as mod
        source = open(mod.__file__).read()
        assert "enterprise_ssd" not in source.lower()
        assert "SequentialRead" not in source
        assert "RandomWrite" not in source
        assert "DWPD" not in source
        assert "capacity" not in source
        assert "form_factor" not in source
