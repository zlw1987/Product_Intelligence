"""Bounded HTTP PDF acquisition (PRODUCT-INTEL.6D — providers layer).

Concrete `DocumentFetcher` implementation for PDF documents, built on
`urllib.request` and nothing else. Self-hosted and free — no external
service, no per-document fee, no browser.

Every fetch is bounded:

| Bound | Default | Why |
| --- | --- | --- |
| Timeout | 10.0 s per hop | One unresponsive host cannot hold a caller open. |
| Redirects | 3 | Enough for http->https and canonical-slug hops. |
| Response size | 10 MiB | Real manufacturer datasheets are typically under 5 MiB. |
| Content type | `application/pdf` only | This fetcher retrieves PDF documents. |

This fetcher is NOT a general-purpose document fetcher. It accepts only
`application/pdf` content type. An HTML page, image, or JSON response
is refused.

Destination safety follows the same principles as HttpPageFetcher:
- Every address the name resolves to must be publicly routable
- Loopback, private, link-local, multicast, reserved destinations are refused
- Redirects are followed manually with revalidation of each hop
- No credential, cookie, or authorization header is ever set
"""

from __future__ import annotations

import ipaddress
import socket
import urllib.error
import urllib.request
from collections.abc import Callable
from datetime import datetime, timezone
from urllib.parse import urljoin, urlsplit

from product_intelligence.providers.document import (
    DocumentFetchError,
    DocumentFetchRequest,
    FetchedDocument,
    UnsafeDocumentTargetError,
)


FETCHER_ID = "stdlib-http-pdf"
DEFAULT_TIMEOUT_SECONDS = 10.0
DEFAULT_MAX_REDIRECTS = 3
DEFAULT_MAX_RESPONSE_BYTES = 10 * 1024 * 1024  # 10 MiB
ACCEPTED_MEDIA_TYPES: frozenset[str] = frozenset({"application/pdf"})
USER_AGENT = "ProductIntelligenceBot/0.1 (+deterministic datasheet acquisition)"
REDIRECT_STATUS_CODES: frozenset[int] = frozenset({301, 302, 303, 307, 308})


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


# ---------------------------------------------------------------------------
# Reusable safety checks from http_page.py (same logic, no cross-import)
# ---------------------------------------------------------------------------


class _NoRedirectHandler(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):  # noqa: D102
        return None


def _build_opener() -> urllib.request.OpenerDirector:
    opener = urllib.request.OpenerDirector()
    opener.add_handler(urllib.request.HTTPHandler())
    opener.add_handler(urllib.request.HTTPSHandler())
    opener.add_handler(_NoRedirectHandler())
    opener.add_handler(urllib.request.HTTPErrorProcessor())
    opener.add_handler(urllib.request.HTTPDefaultErrorHandler())
    return opener


def _unwrap_address(address: ipaddress._BaseAddress) -> ipaddress._BaseAddress:
    if isinstance(address, ipaddress.IPv6Address):
        if address.ipv4_mapped is not None:
            return address.ipv4_mapped
        if address.sixtofour is not None:
            return address.sixtofour
    return address


def _is_publicly_routable(address: ipaddress._BaseAddress) -> bool:
    resolved = _unwrap_address(address)
    if (
        resolved.is_loopback
        or resolved.is_private
        or resolved.is_link_local
        or resolved.is_multicast
        or resolved.is_reserved
        or resolved.is_unspecified
    ):
        return False
    return bool(resolved.is_global)


def _assert_destination_is_public(url: str) -> None:
    parts = urlsplit(url)
    host = parts.hostname
    if not host:
        raise UnsafeDocumentTargetError(f"no host to resolve in {url!r}")

    port = 443 if parts.scheme.lower() == "https" else 80
    try:
        infos = socket.getaddrinfo(host, port, proto=socket.IPPROTO_TCP)
    except socket.gaierror as exc:
        raise DocumentFetchError(f"could not resolve host {host!r}: {exc}") from exc
    except OSError as exc:
        raise DocumentFetchError(f"could not resolve host {host!r}") from exc

    if not infos:
        raise DocumentFetchError(f"host {host!r} resolved to no addresses")

    for info in infos:
        raw = info[4][0]
        try:
            address = ipaddress.ip_address(raw.split("%", 1)[0])
        except ValueError as exc:
            raise UnsafeDocumentTargetError(
                f"host {host!r} resolved to an unrecognizable address"
            ) from exc
        if not _is_publicly_routable(address):
            raise UnsafeDocumentTargetError(
                f"host {host!r} resolves to non-public address {address}; "
                "a fetch target must be publicly routable"
            )


def _require_fetchable_url(value: str, field_name: str = "url") -> str:
    """Validate URL structure (mirrors providers.page)."""
    text = value.strip()
    if not text:
        raise ValueError(f"{field_name} is required; there is nothing to fetch")

    parts = urlsplit(text)
    if parts.scheme.lower() not in ("http", "https"):
        raise ValueError(
            f"{field_name} must be an absolute http:// or https:// URL, got {text!r}"
        )
    if not parts.hostname:
        raise ValueError(f"{field_name} must include a host, got {text!r}")
    if parts.username is not None or parts.password is not None:
        raise ValueError(
            f"{field_name} must not embed credentials; a fetch target carries no "
            "authentication"
        )
    return text


def _media_type(content_type: str | None) -> str:
    if not content_type:
        return ""
    return content_type.split(";", 1)[0].strip().lower()


# ---------------------------------------------------------------------------
# HttpPdfFetcher
# ---------------------------------------------------------------------------


class HttpPdfFetcher:
    """`DocumentFetcher` backed by the standard library for PDF documents.

    Conforms to the `DocumentFetcher` protocol structurally.

    Every bound is a constructor parameter with a conservative default.
    """

    def __init__(
        self,
        *,
        timeout: float = DEFAULT_TIMEOUT_SECONDS,
        max_redirects: int = DEFAULT_MAX_REDIRECTS,
        max_response_bytes: int = DEFAULT_MAX_RESPONSE_BYTES,
        clock: Callable[[], datetime] = _utc_now,
    ) -> None:
        if timeout <= 0:
            raise ValueError("timeout must be positive")
        if max_redirects < 0:
            raise ValueError("max_redirects must not be negative")
        if max_response_bytes <= 0:
            raise ValueError("max_response_bytes must be positive")

        self._timeout = timeout
        self._max_redirects = max_redirects
        self._max_response_bytes = max_response_bytes
        self._clock = clock

    def fetch(self, request: DocumentFetchRequest) -> FetchedDocument:
        """Retrieve one PDF document, following at most `max_redirects` hops.

        Each hop is revalidated as though it were the original request.
        """
        if not isinstance(request, DocumentFetchRequest):
            raise TypeError(
                f"request must be a DocumentFetchRequest, got {type(request).__name__}"
            )

        opener = _build_opener()
        current_url = request.url
        redirects = 0

        while True:
            _assert_destination_is_public(current_url)

            http_request = urllib.request.Request(
                current_url,
                method="GET",
                headers={
                    "User-Agent": USER_AGENT,
                    "Accept": "application/pdf",
                    "Accept-Encoding": "identity",
                },
            )

            try:
                with opener.open(http_request, timeout=self._timeout) as response:
                    return self._read_document(
                        response,
                        requested_url=request.url,
                        final_url=current_url,
                        redirects=redirects,
                    )
            except urllib.error.HTTPError as exc:
                location = exc.headers.get("Location") if exc.headers else None
                status = exc.code
                exc.close()

                if status not in REDIRECT_STATUS_CODES or not location:
                    raise DocumentFetchError(
                        f"fetch of {current_url!r} failed with HTTP {status}"
                    ) from exc

                if redirects >= self._max_redirects:
                    raise DocumentFetchError(
                        f"fetch of {request.url!r} exceeded {self._max_redirects} "
                        "redirects"
                    ) from exc

                try:
                    current_url = _require_fetchable_url(
                        urljoin(current_url, location), "redirect target"
                    )
                except (TypeError, ValueError) as url_error:
                    raise UnsafeDocumentTargetError(
                        f"refused redirect from {current_url!r}: {url_error}"
                    ) from exc
                redirects += 1
            except urllib.error.URLError as exc:
                raise DocumentFetchError(
                    f"fetch of {current_url!r} failed: {exc.reason}"
                ) from exc
            except TimeoutError as exc:
                raise DocumentFetchError(f"fetch of {current_url!r} timed out") from exc
            except OSError as exc:
                raise DocumentFetchError(
                    f"fetch of {current_url!r} failed due to a transport error"
                ) from exc

    def _read_document(
        self,
        response,
        *,
        requested_url: str,
        final_url: str,
        redirects: int,
    ) -> FetchedDocument:
        """Turn a successful response into a FetchedDocument, or refuse it."""
        content_type = response.headers.get("Content-Type")
        media_type = _media_type(content_type)
        if media_type not in ACCEPTED_MEDIA_TYPES:
            raise DocumentFetchError(
                f"{final_url!r} returned content type {media_type or 'unknown'!r}; "
                "this fetcher retrieves PDF documents only"
            )

        declared_length = response.headers.get("Content-Length")
        if declared_length and declared_length.strip().isdigit():
            if int(declared_length) > self._max_response_bytes:
                raise DocumentFetchError(
                    f"{final_url!r} declared {declared_length} bytes, above the "
                    f"{self._max_response_bytes}-byte limit"
                )

        body = response.read(self._max_response_bytes + 1)
        if len(body) > self._max_response_bytes:
            raise DocumentFetchError(
                f"{final_url!r} returned more than {self._max_response_bytes} "
                "bytes; the response is refused rather than truncated"
            )

        return FetchedDocument(
            requested_url=requested_url,
            final_url=final_url,
            retrieved_at=self._clock(),
            content_type=content_type,
            body_bytes=body,
            body_byte_count=len(body),
            redirect_count=redirects,
            fetcher_id=FETCHER_ID,
        )
