"""The standard-library page fetcher (PRODUCT-INTEL.3A).

Offline throughout. `socket.getaddrinfo` and the opener are both replaced, so
this file makes no DNS query and opens no connection — the suite stays
deterministic and costs nothing.

Most of these tests are refusals, deliberately. A fetcher that consumes URLs
originating from an external search provider is judged by what it declines to
open, and a safety rule exercised only along its happy path is indistinguishable
from no rule at all.
"""

from __future__ import annotations

import io
import socket
import urllib.error
from datetime import datetime, timezone
from email.message import Message

import pytest

from product_intelligence.providers import http_page
from product_intelligence.providers.http_page import (
    ACCEPTED_MEDIA_TYPES,
    DEFAULT_MAX_REDIRECTS,
    DEFAULT_MAX_RESPONSE_BYTES,
    DEFAULT_TIMEOUT_SECONDS,
    FETCHER_ID,
    USER_AGENT,
    HttpPageFetcher,
)
from product_intelligence.providers.page import (
    PageFetchError,
    PageFetchRequest,
    UnsafeFetchTargetError,
)

RETRIEVED_AT = datetime(2026, 8, 17, 12, 0, tzinfo=timezone.utc)
PUBLIC_ADDRESS = "93.184.216.34"


def _clock() -> datetime:
    return RETRIEVED_AT


def _headers(**values: str) -> Message:
    message = Message()
    for name, value in values.items():
        message[name.replace("_", "-")] = value
    return message


class _Response:
    """The narrow slice of an HTTP response object the fetcher actually uses."""

    def __init__(
        self, body: bytes, *, status: int = 200, content_type: str = "text/html", **extra
    ) -> None:
        self._body = io.BytesIO(body)
        self.status = status
        self.headers = _headers(Content_Type=content_type, **extra)

    def read(self, amount: int | None = None) -> bytes:
        return self._body.read(amount)

    def getcode(self) -> int:
        return self.status

    def __enter__(self) -> "_Response":
        return self

    def __exit__(self, *exc_info: object) -> None:
        return None


class _RecordingOpener:
    """Stands in for the real opener, recording every request it is handed."""

    def __init__(self, *outcomes: object) -> None:
        self._outcomes = list(outcomes)
        self.requests: list[object] = []

    def open(self, request, timeout=None):  # noqa: ANN001
        self.requests.append(request)
        self.timeout = timeout
        outcome = self._outcomes.pop(0)
        if isinstance(outcome, Exception):
            raise outcome
        return outcome


@pytest.fixture
def public_dns(monkeypatch: pytest.MonkeyPatch) -> None:
    """Every host resolves to one public address."""
    monkeypatch.setattr(
        http_page.socket,
        "getaddrinfo",
        lambda host, port, **kwargs: [
            (socket.AF_INET, socket.SOCK_STREAM, 6, "", (PUBLIC_ADDRESS, port))
        ],
    )


def _install_opener(monkeypatch: pytest.MonkeyPatch, opener: _RecordingOpener) -> None:
    monkeypatch.setattr(http_page, "_build_opener", lambda: opener)


class TestSuccessfulFetch:
    def test_it_returns_what_the_destination_returned(
        self, monkeypatch: pytest.MonkeyPatch, public_dns: None
    ) -> None:
        opener = _RecordingOpener(
            _Response(b"<html>body</html>", content_type="text/html; charset=utf-8")
        )
        _install_opener(monkeypatch, opener)

        page = HttpPageFetcher(clock=_clock).fetch(
            PageFetchRequest("https://example.com/product")
        )

        assert page.status_code == 200
        assert page.body_text == "<html>body</html>"
        assert page.content_type == "text/html; charset=utf-8"
        assert page.body_byte_count == 17
        assert page.requested_url == page.final_url == "https://example.com/product"
        assert page.redirect_count == 0
        assert page.retrieved_at == RETRIEVED_AT
        assert page.fetcher_id == FETCHER_ID

    def test_it_issues_a_get_and_sends_no_credential(
        self, monkeypatch: pytest.MonkeyPatch, public_dns: None
    ) -> None:
        """No cookie, no authorization, no application secret — none exists here."""
        opener = _RecordingOpener(_Response(b"<html></html>"))
        _install_opener(monkeypatch, opener)

        HttpPageFetcher(clock=_clock).fetch(PageFetchRequest("https://example.com/p"))

        request = opener.requests[0]
        assert request.get_method() == "GET"
        assert request.data is None
        sent = {name.lower() for name in request.headers}
        assert sent == {"User-agent".lower(), "Accept".lower(), "Accept-encoding".lower()}
        assert "authorization" not in sent
        assert "cookie" not in sent

    def test_the_user_agent_identifies_this_application_honestly(self) -> None:
        """No browser impersonation, and it is never rotated."""
        lowered = USER_AGENT.lower()

        assert "productintelligencebot" in lowered
        for pretence in ("mozilla", "chrome", "safari", "webkit", "gecko"):
            assert pretence not in lowered

    def test_the_declared_charset_is_used(
        self, monkeypatch: pytest.MonkeyPatch, public_dns: None
    ) -> None:
        body = "café".encode("latin-1")
        opener = _RecordingOpener(
            _Response(body, content_type="text/html; charset=iso-8859-1")
        )
        _install_opener(monkeypatch, opener)

        page = HttpPageFetcher(clock=_clock).fetch(PageFetchRequest("https://e.com/p"))

        assert page.body_text == "café"

    def test_an_undecodable_byte_does_not_destroy_the_page(
        self, monkeypatch: pytest.MonkeyPatch, public_dns: None
    ) -> None:
        """One bad byte in a marketing paragraph must not cost the whole document."""
        opener = _RecordingOpener(_Response(b"<html>\xff ok</html>"))
        _install_opener(monkeypatch, opener)

        page = HttpPageFetcher(clock=_clock).fetch(PageFetchRequest("https://e.com/p"))

        assert "ok</html>" in page.body_text

    def test_an_unknown_charset_falls_back_rather_than_failing(
        self, monkeypatch: pytest.MonkeyPatch, public_dns: None
    ) -> None:
        opener = _RecordingOpener(
            _Response(b"<html>x</html>", content_type="text/html; charset=not-a-codec")
        )
        _install_opener(monkeypatch, opener)

        page = HttpPageFetcher(clock=_clock).fetch(PageFetchRequest("https://e.com/p"))

        assert page.body_text == "<html>x</html>"


class TestDestinationSafety:
    @pytest.mark.parametrize(
        "address",
        [
            "127.0.0.1",
            "10.1.2.3",
            "192.168.0.5",
            "172.16.0.1",
            "169.254.169.254",
            "0.0.0.0",
            "224.0.0.1",
            "::1",
            "fe80::1",
            "fc00::1",
            "::ffff:127.0.0.1",
            "2002:7f00:1::",
        ],
    )
    def test_a_non_public_destination_is_refused(
        self, monkeypatch: pytest.MonkeyPatch, address: str
    ) -> None:
        """Including the cloud metadata address and IPv6-wrapped loopback."""
        family = socket.AF_INET6 if ":" in address else socket.AF_INET
        monkeypatch.setattr(
            http_page.socket,
            "getaddrinfo",
            lambda host, port, **kwargs: [(family, socket.SOCK_STREAM, 6, "", (address, port))],
        )
        opener = _RecordingOpener(_Response(b"<html></html>"))
        _install_opener(monkeypatch, opener)

        with pytest.raises(UnsafeFetchTargetError):
            HttpPageFetcher(clock=_clock).fetch(PageFetchRequest("https://intranet.example/p"))

        assert opener.requests == [], "the refusal must happen before any request"

    def test_one_private_address_among_several_refuses_the_whole_host(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Which address a later connection picks is not this code's decision."""
        monkeypatch.setattr(
            http_page.socket,
            "getaddrinfo",
            lambda host, port, **kwargs: [
                (socket.AF_INET, socket.SOCK_STREAM, 6, "", (PUBLIC_ADDRESS, port)),
                (socket.AF_INET, socket.SOCK_STREAM, 6, "", ("127.0.0.1", port)),
            ],
        )
        _install_opener(monkeypatch, _RecordingOpener(_Response(b"<html></html>")))

        with pytest.raises(UnsafeFetchTargetError):
            HttpPageFetcher(clock=_clock).fetch(PageFetchRequest("https://mixed.example/p"))

    def test_a_public_destination_is_allowed(
        self, monkeypatch: pytest.MonkeyPatch, public_dns: None
    ) -> None:
        """So the refusals above cannot be passing for the wrong reason."""
        _install_opener(monkeypatch, _RecordingOpener(_Response(b"<html>ok</html>")))

        page = HttpPageFetcher(clock=_clock).fetch(PageFetchRequest("https://example.com/p"))

        assert page.body_text == "<html>ok</html>"

    def test_an_unresolvable_host_is_a_fetch_failure_not_a_refusal(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        def _fail(host, port, **kwargs):
            raise socket.gaierror("no such host")

        monkeypatch.setattr(http_page.socket, "getaddrinfo", _fail)

        with pytest.raises(PageFetchError) as caught:
            HttpPageFetcher(clock=_clock).fetch(PageFetchRequest("https://nope.example/p"))

        assert not isinstance(caught.value, UnsafeFetchTargetError)


class TestRedirects:
    def _redirect(self, location: str, status: int = 302) -> urllib.error.HTTPError:
        return urllib.error.HTTPError(
            "https://example.com/p",
            status,
            "Found",
            _headers(Location=location),
            io.BytesIO(b""),
        )

    def test_a_redirect_is_followed_and_recorded(
        self, monkeypatch: pytest.MonkeyPatch, public_dns: None
    ) -> None:
        opener = _RecordingOpener(
            self._redirect("https://www.example.com/final"),
            _Response(b"<html>final</html>"),
        )
        _install_opener(monkeypatch, opener)

        page = HttpPageFetcher(clock=_clock).fetch(PageFetchRequest("https://example.com/p"))

        assert page.requested_url == "https://example.com/p"
        assert page.final_url == "https://www.example.com/final"
        assert page.redirect_count == 1

    def test_a_relative_redirect_is_resolved(
        self, monkeypatch: pytest.MonkeyPatch, public_dns: None
    ) -> None:
        opener = _RecordingOpener(
            self._redirect("/canonical/slug"), _Response(b"<html>x</html>")
        )
        _install_opener(monkeypatch, opener)

        page = HttpPageFetcher(clock=_clock).fetch(PageFetchRequest("https://example.com/p"))

        assert page.final_url == "https://example.com/canonical/slug"

    def test_a_redirect_to_a_private_address_is_refused(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """The ordinary shape of this attack: a public host pointing inward.

        The first hop resolves publicly and the second does not, so a fetcher
        that validated only the original target would fetch the private page.
        """
        resolutions = iter([PUBLIC_ADDRESS, "127.0.0.1"])
        monkeypatch.setattr(
            http_page.socket,
            "getaddrinfo",
            lambda host, port, **kwargs: [
                (socket.AF_INET, socket.SOCK_STREAM, 6, "", (next(resolutions), port))
            ],
        )
        opener = _RecordingOpener(
            self._redirect("http://internal.example/admin"),
            _Response(b"<html>secret</html>"),
        )
        _install_opener(monkeypatch, opener)

        with pytest.raises(UnsafeFetchTargetError):
            HttpPageFetcher(clock=_clock).fetch(PageFetchRequest("https://example.com/p"))

        assert len(opener.requests) == 1, "the second hop must never be requested"

    @pytest.mark.parametrize(
        "location",
        ["file:///etc/passwd", "javascript:alert(1)", "ftp://example.com/x"],
    )
    def test_a_redirect_to_a_non_web_scheme_is_refused(
        self, monkeypatch: pytest.MonkeyPatch, public_dns: None, location: str
    ) -> None:
        opener = _RecordingOpener(self._redirect(location), _Response(b"<html></html>"))
        _install_opener(monkeypatch, opener)

        with pytest.raises(UnsafeFetchTargetError):
            HttpPageFetcher(clock=_clock).fetch(PageFetchRequest("https://example.com/p"))

    def test_a_redirect_carrying_credentials_is_refused(
        self, monkeypatch: pytest.MonkeyPatch, public_dns: None
    ) -> None:
        opener = _RecordingOpener(
            self._redirect("https://user:pw@example.com/x"), _Response(b"<html></html>")
        )
        _install_opener(monkeypatch, opener)

        with pytest.raises(UnsafeFetchTargetError):
            HttpPageFetcher(clock=_clock).fetch(PageFetchRequest("https://example.com/p"))

    def test_a_redirect_loop_ends(
        self, monkeypatch: pytest.MonkeyPatch, public_dns: None
    ) -> None:
        opener = _RecordingOpener(*[self._redirect("https://example.com/p") for _ in range(6)])
        _install_opener(monkeypatch, opener)

        with pytest.raises(PageFetchError, match="redirect"):
            HttpPageFetcher(clock=_clock, max_redirects=2).fetch(
                PageFetchRequest("https://example.com/p")
            )

        assert len(opener.requests) == 3

    def test_the_library_is_not_allowed_to_follow_redirects_itself(self) -> None:
        """If `urllib` followed them, the last hop — the only one that matters —
        would never be revalidated."""
        handler = http_page._NoRedirectHandler()

        assert handler.redirect_request(None, None, 302, "Found", _headers(), "x") is None


class TestBounds:
    def test_an_oversized_response_is_refused_not_truncated(
        self, monkeypatch: pytest.MonkeyPatch, public_dns: None
    ) -> None:
        """A document cut mid-element would be parsed as though it were whole."""
        _install_opener(monkeypatch, _RecordingOpener(_Response(b"x" * 5000)))

        with pytest.raises(PageFetchError, match="refused rather than truncated"):
            HttpPageFetcher(clock=_clock, max_response_bytes=1000).fetch(
                PageFetchRequest("https://example.com/p")
            )

    def test_a_response_at_the_limit_is_accepted(
        self, monkeypatch: pytest.MonkeyPatch, public_dns: None
    ) -> None:
        _install_opener(monkeypatch, _RecordingOpener(_Response(b"x" * 1000)))

        page = HttpPageFetcher(clock=_clock, max_response_bytes=1000).fetch(
            PageFetchRequest("https://example.com/p")
        )

        assert page.body_byte_count == 1000

    def test_a_declared_oversize_is_refused_before_reading(
        self, monkeypatch: pytest.MonkeyPatch, public_dns: None
    ) -> None:
        _install_opener(
            monkeypatch,
            _RecordingOpener(_Response(b"x" * 10, Content_Length="99999999")),
        )

        with pytest.raises(PageFetchError, match="above the"):
            HttpPageFetcher(clock=_clock, max_response_bytes=1000).fetch(
                PageFetchRequest("https://example.com/p")
            )

    def test_the_timeout_is_passed_to_the_opener(
        self, monkeypatch: pytest.MonkeyPatch, public_dns: None
    ) -> None:
        opener = _RecordingOpener(_Response(b"<html></html>"))
        _install_opener(monkeypatch, opener)

        HttpPageFetcher(clock=_clock, timeout=2.5).fetch(
            PageFetchRequest("https://example.com/p")
        )

        assert opener.timeout == 2.5

    def test_the_defaults_are_conservative(self) -> None:
        assert DEFAULT_TIMEOUT_SECONDS == 10.0
        assert DEFAULT_MAX_REDIRECTS == 3
        assert DEFAULT_MAX_RESPONSE_BYTES == 5 * 1024 * 1024

    @pytest.mark.parametrize(
        "kwargs",
        [{"timeout": 0}, {"timeout": -1}, {"max_redirects": -1}, {"max_response_bytes": 0}],
    )
    def test_an_unbounded_configuration_is_refused(self, kwargs: dict) -> None:
        with pytest.raises(ValueError):
            HttpPageFetcher(**kwargs)


class TestContentTypes:
    @pytest.mark.parametrize(
        "content_type", ["text/html", "text/HTML; charset=utf-8", "application/xhtml+xml"]
    )
    def test_html_documents_are_accepted(
        self, monkeypatch: pytest.MonkeyPatch, public_dns: None, content_type: str
    ) -> None:
        _install_opener(
            monkeypatch, _RecordingOpener(_Response(b"<html></html>", content_type=content_type))
        )

        page = HttpPageFetcher(clock=_clock).fetch(PageFetchRequest("https://example.com/p"))

        assert page.status_code == 200

    @pytest.mark.parametrize(
        "content_type",
        ["application/pdf", "image/jpeg", "application/json", "application/zip", ""],
    )
    def test_anything_else_is_refused_rather_than_sniffed(
        self, monkeypatch: pytest.MonkeyPatch, public_dns: None, content_type: str
    ) -> None:
        _install_opener(
            monkeypatch, _RecordingOpener(_Response(b"%PDF-1.4", content_type=content_type))
        )

        with pytest.raises(PageFetchError, match="HTML documents only"):
            HttpPageFetcher(clock=_clock).fetch(PageFetchRequest("https://example.com/p"))

    def test_the_accepted_set_is_exactly_two_media_types(self) -> None:
        assert ACCEPTED_MEDIA_TYPES == frozenset({"text/html", "application/xhtml+xml"})


class TestFailures:
    def test_a_403_is_reported_rather_than_worked_around(
        self, monkeypatch: pytest.MonkeyPatch, public_dns: None
    ) -> None:
        """Respecting a block is correct, and it is how a source gets classified."""
        _install_opener(
            monkeypatch,
            _RecordingOpener(
                urllib.error.HTTPError(
                    "https://example.com/p", 403, "Forbidden", _headers(), io.BytesIO(b"")
                )
            ),
        )

        with pytest.raises(PageFetchError, match="HTTP 403"):
            HttpPageFetcher(clock=_clock).fetch(PageFetchRequest("https://example.com/p"))

    def test_a_429_is_not_retried(
        self, monkeypatch: pytest.MonkeyPatch, public_dns: None
    ) -> None:
        opener = _RecordingOpener(
            urllib.error.HTTPError(
                "https://example.com/p", 429, "Too Many Requests", _headers(), io.BytesIO(b"")
            )
        )
        _install_opener(monkeypatch, opener)

        with pytest.raises(PageFetchError, match="HTTP 429"):
            HttpPageFetcher(clock=_clock).fetch(PageFetchRequest("https://example.com/p"))

        assert len(opener.requests) == 1, "no retry policy exists"

    def test_a_transport_failure_becomes_a_page_fetch_error(
        self, monkeypatch: pytest.MonkeyPatch, public_dns: None
    ) -> None:
        _install_opener(
            monkeypatch, _RecordingOpener(urllib.error.URLError("connection refused"))
        )

        with pytest.raises(PageFetchError):
            HttpPageFetcher(clock=_clock).fetch(PageFetchRequest("https://example.com/p"))

    def test_a_timeout_becomes_a_page_fetch_error(
        self, monkeypatch: pytest.MonkeyPatch, public_dns: None
    ) -> None:
        _install_opener(monkeypatch, _RecordingOpener(TimeoutError()))

        with pytest.raises(PageFetchError, match="timed out"):
            HttpPageFetcher(clock=_clock).fetch(PageFetchRequest("https://example.com/p"))

    def test_a_wrong_argument_type_is_a_caller_defect(self) -> None:
        with pytest.raises(TypeError):
            HttpPageFetcher(clock=_clock).fetch("https://example.com/p")  # type: ignore[arg-type]


class TestOpenerConstruction:
    def test_the_opener_reaches_only_http_and_https(self) -> None:
        """No `FileHandler`, no `FTPHandler`, no `UnknownHandler`.

        Assembled by hand rather than with `build_opener()`, which installs all
        three — each a way for a URL to send this code somewhere other than the
        public web page it was asked for.
        """
        opener = http_page._build_opener()

        assert set(opener.handle_open) <= {"http", "https", "unknown"}
        assert "file" not in opener.handle_open
        assert "ftp" not in opener.handle_open
        assert "unknown" not in opener.handle_open

    def test_no_proxy_handler_is_installed(self) -> None:
        """An ambient proxy environment variable must not redirect a fetch."""
        import urllib.request

        opener = http_page._build_opener()

        assert not any(
            isinstance(handler, urllib.request.ProxyHandler)
            for handler in opener.handlers
        )

    def test_no_cookie_processor_is_installed(self) -> None:
        import urllib.request

        opener = http_page._build_opener()

        assert not any(
            isinstance(handler, urllib.request.HTTPCookieProcessor)
            for handler in opener.handlers
        )
