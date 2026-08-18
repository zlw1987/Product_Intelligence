"""The standard-library page fetcher (PRODUCT-INTEL.3A).

`HttpPageFetcher` is the concrete `PageFetcher`: one bounded, synchronous
GET per document, built on `urllib.request` and nothing else. It is
self-hosted and free — no crawler service, no browser, no browser farm, no
proxy pool, and no per-page fee — which is deliberate, because part of what 3A
exists to discover is whether any of that is actually needed.

It executes no JavaScript. A page whose product data exists only after
client-side rendering yields whatever its static document contains, which may
be nothing. That is a finding about the source, recorded as such, and not a
reason to acquire browser infrastructure inside this phase.

Every fetch is bounded
----------------------

| Bound | Default | Why |
| --- | --- | --- |
| Timeout | 10.0 s per hop | One unresponsive host cannot hold a caller open. |
| Redirects | 3 | Enough for the ordinary `http->https`, apex-to-`www`, and canonical-slug hops; short enough that a redirect loop ends quickly. |
| Response size | 5 MiB | Real retail product pages routinely run past 1 MiB of markup. The limit refuses rather than truncates: a document cut mid-tag would be parsed as though it were complete, and a parser reporting fewer listings because bytes went missing is worse than a fetch that failed loudly. |
| Content type | `text/html`, `application/xhtml+xml` | This fetcher retrieves a document for HTML extraction. A PDF, an image, or a JSON API response is not that, and sniffing past a server's own declaration would be guessing. |

The document only
-----------------

One request retrieves one document. No image, script, stylesheet, font, or
frame referenced by that document is fetched, no link in it is followed, and
nothing is queued. `Accept-Encoding: identity` is sent so the bytes counted
against the size bound are the bytes that arrive.

Destination safety
------------------

A URL reaching this fetcher may have come from an external search provider, so
every destination is untrusted:

* scheme, host presence, and absence of embedded credentials are enforced by
  the `PageFetchRequest` contract before a fetch starts;
* the host is resolved with `socket.getaddrinfo`, and **every** address it
  resolves to must be publicly routable. One private address among several is a
  refusal, not a reason to try the others;
* loopback, private, link-local (including the cloud metadata address
  `169.254.169.254`), unspecified, multicast, and reserved destinations are
  refused, as are IPv4-mapped and 6to4-embedded forms of them;
* redirects are **not** followed by `urllib`. This fetcher follows them itself
  and puts each hop through the identical URL and address checks, because a
  public host redirecting to `http://127.0.0.1/` is the ordinary shape of this
  attack;
* the opener is assembled by hand from HTTP and HTTPS handlers only. There is
  no `FileHandler`, no `FTPHandler`, no `UnknownHandler`, and no `ProxyHandler`,
  so `file:` and `ftp:` are unreachable through it and no ambient proxy
  environment variable can redirect a fetch;
* no cookie processor is installed, no `Authorization` header is ever set, and
  no application or provider credential exists in this module to send. The
  request carries a User-Agent, an Accept, and an Accept-Encoding header, and
  nothing else;
* the method is GET. No form is submitted and no other verb is issued.

What this does **not** amount to
--------------------------------

These are application-level checks, and they are not network isolation. Two
gaps are real and are stated rather than papered over:

1. **DNS time-of-check/time-of-use.** The name is resolved once for validation,
   and `urllib` resolves it again when it connects. A DNS answer that changes
   between those two moments — the classic rebinding attack — is not prevented
   here. Closing it properly means owning the socket: resolving once, connecting
   to the pinned address, and carrying the original hostname through TLS
   verification and the `Host` header. That is a real change to how the
   connection is made, and it belongs to a phase that is hardening deployment
   rather than one that is learning what pages contain.
2. **Egress is otherwise unrestricted.** Anything this process could reach, it
   can still reach if a name resolves to a public address that fronts something
   internal.

The durable answer to both is network-level: an egress allowlist, or an
outbound proxy, in the deployment. This module makes the ordinary mistakes hard
and says plainly what it does not solve.

Politeness
----------

The User-Agent identifies this application honestly. It does not impersonate a
browser, it is not rotated, and no bot-detection measure is worked around. A
`403` or a `429` is recorded as what the site said and is not retried against —
respecting it is both correct and the cheapest way to learn which sources need
a different approach.
"""

from __future__ import annotations

import ipaddress
import socket
import urllib.error
import urllib.request
from collections.abc import Callable
from datetime import datetime, timezone
from urllib.parse import urljoin, urlsplit

from product_intelligence.providers.page import (
    FetchedPage,
    PageFetchError,
    PageFetchRequest,
    UnsafeFetchTargetError,
    require_fetchable_url,
)

#: `FetchedPage.fetcher_id` for every page this fetcher produces.
FETCHER_ID = "stdlib-http"

#: One slow host cannot hold a caller open indefinitely. Applied per hop.
DEFAULT_TIMEOUT_SECONDS = 10.0

#: Enough for http->https, apex-to-www, and canonical-slug hops. Not a crawler.
DEFAULT_MAX_REDIRECTS = 3

#: 5 MiB. Real retail product pages run well past 1 MiB of markup; a document
#: larger than this is refused rather than truncated, because a page cut
#: mid-element would be parsed as if it were whole.
DEFAULT_MAX_RESPONSE_BYTES = 5 * 1024 * 1024

#: The document types this fetcher will accept. Compared against the media type
#: only, with parameters and casing ignored. Anything else is refused rather
#: than sniffed.
ACCEPTED_MEDIA_TYPES: frozenset[str] = frozenset(
    {"text/html", "application/xhtml+xml"}
)

#: An honest identifier. Not a browser string, never rotated.
USER_AGENT = "ProductIntelligenceBot/0.1 (+deterministic listing extraction)"

#: Status codes this fetcher follows itself, one hop at a time, revalidating.
REDIRECT_STATUS_CODES: frozenset[int] = frozenset({301, 302, 303, 307, 308})

#: Fallback decoding when a response declares no usable charset. `replace`
#: rather than `strict`: a single undecodable byte in a marketing paragraph must
#: not destroy an otherwise-extractable page, and the substitution is visible.
FALLBACK_ENCODING = "utf-8"


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


class _NoRedirectHandler(urllib.request.HTTPRedirectHandler):
    """Stop `urllib` from following redirects on its own.

    Returning `None` from `redirect_request` makes `urllib` raise `HTTPError`
    for the 3xx instead of transparently following it. That is exactly what is
    wanted: this fetcher follows redirects itself so it can revalidate every
    hop, and a library that quietly followed one would defeat the address checks
    on the only hop that matters — the last.
    """

    def redirect_request(self, req, fp, code, msg, headers, newurl):  # noqa: D102
        return None


def _build_opener() -> urllib.request.OpenerDirector:
    """Assemble a deliberately minimal opener.

    Built by hand rather than with `build_opener()`, which installs a
    `FileHandler`, an `FTPHandler`, an `UnknownHandler`, and a `ProxyHandler`.
    Each of those is a way for a URL — or an environment variable — to send this
    code somewhere other than the public web page it was asked for.
    """
    opener = urllib.request.OpenerDirector()
    opener.add_handler(urllib.request.HTTPHandler())
    opener.add_handler(urllib.request.HTTPSHandler())
    opener.add_handler(_NoRedirectHandler())
    opener.add_handler(urllib.request.HTTPErrorProcessor())
    opener.add_handler(urllib.request.HTTPDefaultErrorHandler())
    return opener


def _unwrap_address(address: ipaddress._BaseAddress) -> ipaddress._BaseAddress:
    """Reduce an IPv6 address to the IPv4 address it actually reaches, if any.

    `::ffff:127.0.0.1` and `2002:7f00:1::` are loopback wearing a different
    notation. Checking the wrapper's flags alone would let both through.
    """
    if isinstance(address, ipaddress.IPv6Address):
        if address.ipv4_mapped is not None:
            return address.ipv4_mapped
        if address.sixtofour is not None:
            return address.sixtofour
    return address


def _is_publicly_routable(address: ipaddress._BaseAddress) -> bool:
    """Whether an address is one this fetcher is willing to open.

    Expressed as an allowlist (`is_global`) with the specific classes named
    again underneath it. The redundancy is intentional: `is_global` is the rule,
    and the explicit flags make the refusals legible in a review and keep the
    check meaningful if a future interpreter's `is_global` ever widens.
    """
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
    """Resolve a URL's host and refuse any non-public destination.

    Every address the name resolves to must be public. A host answering with one
    public and one loopback address is refused outright rather than filtered
    down to the acceptable one — which address a later connection picks is not
    this code's decision to make.
    """
    parts = urlsplit(url)
    host = parts.hostname
    if not host:
        raise UnsafeFetchTargetError(f"no host to resolve in {url!r}")

    port = 443 if parts.scheme.lower() == "https" else 80
    try:
        infos = socket.getaddrinfo(host, port, proto=socket.IPPROTO_TCP)
    except socket.gaierror as exc:
        raise PageFetchError(f"could not resolve host {host!r}: {exc}") from exc
    except OSError as exc:
        raise PageFetchError(f"could not resolve host {host!r}") from exc

    if not infos:
        raise PageFetchError(f"host {host!r} resolved to no addresses")

    for info in infos:
        raw = info[4][0]
        try:
            address = ipaddress.ip_address(raw.split("%", 1)[0])
        except ValueError as exc:
            raise UnsafeFetchTargetError(
                f"host {host!r} resolved to an unrecognizable address"
            ) from exc
        if not _is_publicly_routable(address):
            raise UnsafeFetchTargetError(
                f"host {host!r} resolves to non-public address {address}; "
                "a fetch target must be publicly routable"
            )


def _media_type(content_type: str | None) -> str:
    """The bare media type, lowercased, with parameters discarded."""
    if not content_type:
        return ""
    return content_type.split(";", 1)[0].strip().lower()


def _charset(content_type: str | None) -> str | None:
    """The `charset` parameter of a Content-Type header, if it declares one."""
    if not content_type:
        return None
    for parameter in content_type.split(";")[1:]:
        name, separator, value = parameter.partition("=")
        if separator and name.strip().lower() == "charset":
            return value.strip().strip('"').strip("'") or None
    return None


def _decode(body: bytes, content_type: str | None) -> str:
    """Decode a response body using the charset the response declared.

    The header is the only signal used. A `<meta charset>` inside the document
    is not consulted: reading it means parsing the bytes to decide how to read
    the bytes, and the failure it would fix — a page that declares one encoding
    in HTTP and another in HTML — is rarer than the confusion of having two
    sources of truth. `errors="replace"` keeps a stray byte from costing the
    whole page.
    """
    declared = _charset(content_type)
    if declared:
        try:
            return body.decode(declared, errors="replace")
        except LookupError:
            pass
    return body.decode(FALLBACK_ENCODING, errors="replace")


class HttpPageFetcher:
    """`PageFetcher` backed by the standard library.

    Conforms to the protocol structurally — it inherits nothing and exposes only
    `fetch`.

    Every bound is a constructor parameter with a conservative default, so a
    caller may tighten one. Nothing here lets a caller supply a header, a
    cookie, a proxy, or a credential: those are not configuration, they are the
    rules.
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

    def fetch(self, request: PageFetchRequest) -> FetchedPage:
        """Retrieve one document, following at most `max_redirects` hops.

        Each hop is revalidated as though it were the original request: the URL
        must still be an absolute, credential-free http(s) URL, and its host
        must still resolve exclusively to public addresses.
        """
        if not isinstance(request, PageFetchRequest):
            raise TypeError(
                f"request must be a PageFetchRequest, got {type(request).__name__}"
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
                    "Accept": "text/html,application/xhtml+xml",
                    # Bytes counted against the size bound are the bytes that
                    # arrive; no transparent decompression in between.
                    "Accept-Encoding": "identity",
                },
            )

            try:
                with opener.open(http_request, timeout=self._timeout) as response:
                    return self._read_page(
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
                    raise PageFetchError(
                        f"fetch of {current_url!r} failed with HTTP {status}"
                    ) from exc

                if redirects >= self._max_redirects:
                    raise PageFetchError(
                        f"fetch of {request.url!r} exceeded {self._max_redirects} "
                        "redirects"
                    ) from exc

                try:
                    current_url = require_fetchable_url(
                        urljoin(current_url, location), "redirect target"
                    )
                except (TypeError, ValueError) as url_error:
                    raise UnsafeFetchTargetError(
                        f"refused redirect from {current_url!r}: {url_error}"
                    ) from url_error
                redirects += 1
            except urllib.error.URLError as exc:
                raise PageFetchError(
                    f"fetch of {current_url!r} failed: {exc.reason}"
                ) from exc
            except TimeoutError as exc:
                raise PageFetchError(f"fetch of {current_url!r} timed out") from exc
            except OSError as exc:
                raise PageFetchError(
                    f"fetch of {current_url!r} failed due to a transport error"
                ) from exc

    def _read_page(
        self,
        response,
        *,
        requested_url: str,
        final_url: str,
        redirects: int,
    ) -> FetchedPage:
        """Turn a successful response into a `FetchedPage`, or refuse it."""
        content_type = response.headers.get("Content-Type")
        media_type = _media_type(content_type)
        if media_type not in ACCEPTED_MEDIA_TYPES:
            raise PageFetchError(
                f"{final_url!r} returned content type {media_type or 'unknown'!r}; "
                "this fetcher retrieves HTML documents only"
            )

        declared_length = response.headers.get("Content-Length")
        if declared_length and declared_length.strip().isdigit():
            if int(declared_length) > self._max_response_bytes:
                raise PageFetchError(
                    f"{final_url!r} declared {declared_length} bytes, above the "
                    f"{self._max_response_bytes}-byte limit"
                )

        # One byte past the limit, so "at the limit" and "over it" are
        # distinguishable without reading an unbounded amount.
        body = response.read(self._max_response_bytes + 1)
        if len(body) > self._max_response_bytes:
            raise PageFetchError(
                f"{final_url!r} returned more than {self._max_response_bytes} "
                "bytes; the response is refused rather than truncated, because a "
                "document cut mid-element would be parsed as though it were whole"
            )

        return FetchedPage(
            requested_url=requested_url,
            final_url=final_url,
            retrieved_at=self._clock(),
            status_code=getattr(response, "status", None) or response.getcode(),
            body_text=_decode(body, content_type),
            content_type=content_type,
            body_byte_count=len(body),
            redirect_count=redirects,
            fetcher_id=FETCHER_ID,
        )
