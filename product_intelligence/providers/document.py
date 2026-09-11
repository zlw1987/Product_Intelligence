"""Fetched-document provider boundary (PRODUCT-INTEL.6D).

Provider-neutral contract for acquired binary documents (e.g. PDF datasheets).

Sits beside the HTML page-fetch boundary in providers/page.py but targets
a different document class: binary manufacturer datasheets rather than
rendered web pages.

This module defines:
    FetchedDocument   one acquired document with provenance
    DocumentFetchError   bounded acquisition failure
    DocumentFetchRequest  one document to acquire

It does NOT:
    - name a specific document format (PDF, images, etc.)
    - open sockets or resolve hosts
    - execute JavaScript
    - parse document content

Content type, byte bounds, and redirect policy belong to a concrete
implementation. This contract carries only the shape of the answer.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Protocol


class DocumentFetchError(Exception):
    """A document could not be retrieved.

    One general failure concept, mirroring the page-fetch boundary's
    precedent. A taxonomy designed before real failures is wrong in the
    places that matter.

    Programming / construction errors raise TypeError or ValueError instead.
    """


class UnsafeDocumentTargetError(DocumentFetchError):
    """The fetcher refused to open a destination.

    Mirrors UnsafeFetchTargetError from the page boundary. The destination
    was refused before or instead of being contacted.
    """


@dataclass(frozen=True)
class DocumentFetchRequest:
    """One document to retrieve, named by URL.

    Mirrors PageFetchRequest. The URL is validated at construction.

    Parameters
    ----------
    url : str
        Absolute http(s) URL with a host, no credentials.
    """

    url: str

    def __post_init__(self) -> None:
        if not isinstance(self.url, str) or not self.url.strip():
            raise ValueError("url must be a non-empty string")
        object.__setattr__(self, "url", self.url.strip())

        # Structural URL validation (mirrors providers.page require_fetchable_url)
        from urllib.parse import urlsplit

        parts = urlsplit(self.url)
        if parts.scheme.lower() not in ("http", "https"):
            raise ValueError(
                f"url must be an absolute http:// or https:// URL, got {self.url!r}"
            )
        if not parts.hostname:
            raise ValueError(f"url must include a host, got {self.url!r}")
        if parts.username is not None or parts.password is not None:
            raise ValueError(
                "url must not embed credentials; a document target carries no "
                "authentication"
            )


@dataclass(frozen=True)
class FetchedDocument:
    """What one document URL returned, recorded rather than interpreted.

    Every field is untrusted external content. A fetched document is data
    to be analysed, never an instruction to be followed.

    Attributes
    ----------
    requested_url : str
        The originally requested URL.
    final_url : str
        The actual URL the document came from (after redirects).
        Equal to requested_url when nothing redirected.
    retrieved_at : datetime
        Timezone-aware retrieval timestamp.
    content_type : str | None
        Raw Content-Type header value as received.
    body_bytes : bytes
        The raw document bytes.
    body_byte_count : int
        How many bytes were read.
    redirect_count : int
        How many redirect hops were followed.
    fetcher_id : str
        Identifies the implementation that produced this observation.
    """

    requested_url: str
    final_url: str
    retrieved_at: datetime
    content_type: str | None
    body_bytes: bytes
    body_byte_count: int
    redirect_count: int = 0
    fetcher_id: str = "unknown"

    def __post_init__(self) -> None:
        # URL fields — both must be structurally valid and credential-free
        for field in ("requested_url", "final_url"):
            value = getattr(self, field)
            if not isinstance(value, str) or not value.strip():
                raise ValueError(f"{field} must be a non-empty string")
            object.__setattr__(self, field, value.strip())

            from urllib.parse import urlsplit

            parts = urlsplit(value)
            if parts.scheme.lower() not in ("http", "https"):
                raise ValueError(
                    f"{field} must be an absolute http:// or https:// URL"
                )
            if not parts.hostname:
                raise ValueError(f"{field} must include a host")
            if parts.username is not None or parts.password is not None:
                raise ValueError(
                    f"{field} must not embed credentials; a document URL "
                    "carries no authentication"
                )

        # retrieved_at
        if not isinstance(self.retrieved_at, datetime):
            raise TypeError(
                f"retrieved_at must be a datetime, got {type(self.retrieved_at).__name__}"
            )
        if self.retrieved_at.tzinfo is None or self.retrieved_at.utcoffset() is None:
            raise ValueError("retrieved_at must be timezone-aware")

        # content_type
        if self.content_type is not None:
            if not isinstance(self.content_type, str):
                raise TypeError(
                    f"content_type must be a string or None, got "
                    f"{type(self.content_type).__name__}"
                )
            object.__setattr__(
                self,
                "content_type",
                self.content_type.strip() or None,
            )

        # body_bytes
        if not isinstance(self.body_bytes, bytes):
            raise TypeError(
                f"body_bytes must be bytes, got {type(self.body_bytes).__name__}"
            )

        # body_byte_count
        if isinstance(self.body_byte_count, bool) or not isinstance(
            self.body_byte_count, int
        ):
            raise TypeError(
                f"body_byte_count must be an int, got "
                f"{type(self.body_byte_count).__name__}"
            )
        if self.body_byte_count < 0:
            raise ValueError("body_byte_count must not be negative")

        # Consistency: body_byte_count must match len(body_bytes)
        if self.body_byte_count != len(self.body_bytes):
            raise ValueError(
                f"body_byte_count ({self.body_byte_count}) does not match "
                f"len(body_bytes) ({len(self.body_bytes)}). "
                "They must be identical."
            )

        # redirect_count
        if isinstance(self.redirect_count, bool) or not isinstance(
            self.redirect_count, int
        ):
            raise TypeError(
                f"redirect_count must be an int, got "
                f"{type(self.redirect_count).__name__}"
            )
        if self.redirect_count < 0:
            raise ValueError("redirect_count must not be negative")

        # fetcher_id
        if not isinstance(self.fetcher_id, str) or not self.fetcher_id.strip():
            raise ValueError("fetcher_id must be a non-empty string")
        object.__setattr__(self, "fetcher_id", self.fetcher_id.strip())


class DocumentFetcher(Protocol):
    """The boundary a caller depends on for document acquisition.

    One synchronous method. An implementation conforms by shape and
    inherits nothing.

    An implementation is expected to:

    * accept a DocumentFetchRequest and return a FetchedDocument;
    * bound its own timeout, redirects, and response size;
    * validate content type against an accepted set (e.g. application/pdf);
    * raise DocumentFetchError when retrieval fails;
    * raise UnsafeDocumentTargetError when it refuses a destination;
    * send no credential, no cookie, and no authorization header;
    * execute no JavaScript and submit no forms.
    """

    def fetch(self, request: DocumentFetchRequest) -> FetchedDocument:
        """Retrieve one document and return what the destination returned."""
        ...
