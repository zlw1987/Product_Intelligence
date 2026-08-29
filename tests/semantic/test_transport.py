"""Production transport regression tests (PRODUCT-INTEL.SEMANTIC.TRANSPORT).

``product_intelligence/semantic/transport.py`` is the canonical transport
implementation (FU3A2B). These tests protect two things:

1. Every previously-existing bounded normalization path (HTTP status
   classification, URLError/TimeoutError network conditions, JSON decode
   failures) still behaves exactly as before.
2. A genuine programming defect (``RuntimeError``, ``TypeError``,
   ``AttributeError`` raised somewhere unexpected) is no longer swallowed by
   a blanket ``except Exception`` and converted into a fake
   ``CONNECTION_ERROR``. It propagates.

No live network calls. ``urllib.request.build_opener`` and
``OpenAISemanticTransport._make_request`` are patched/monkeypatched.
"""

from __future__ import annotations

import json
import urllib.error

import pytest

from product_intelligence.semantic.transport import (
    OpenAISemanticTransport,
    TransportFailure,
    TransportResult,
    _classify_http_error,
    _HTTPResponse,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _transport() -> OpenAISemanticTransport:
    return OpenAISemanticTransport(base_url="https://example.invalid/v1")


class _MockResp:
    """Minimal response supporting the context-manager protocol urlopen uses."""

    def __init__(self, status: int, body: bytes):
        self.status = status
        self._body = body

    def read(self):
        return self._body

    def __enter__(self):
        return self

    def __exit__(self, *a):
        pass


def _open_ok(resp: _MockResp):
    """Factory returning a callable that yields ``resp`` from ``opener.open()``."""

    def _call(req, **kw):
        return resp

    return _call


def _make_http_error(status: int, body: dict | str) -> urllib.error.HTTPError:
    """Build an HTTPError with a body that supports ``read()``."""
    raw = json.dumps(body).encode("utf-8") if isinstance(body, dict) else str(body).encode("utf-8")
    err = urllib.error.HTTPError(
        url="https://example.invalid/v1/chat/completions",
        code=status,
        msg=f"HTTP {status}",
        hdrs={},
        fp=None,
    )
    err.read = lambda: raw
    return err


def _complete(transport: OpenAISemanticTransport) -> TransportResult | TransportFailure:
    return transport.complete(
        system_prompt="sys", user_prompt="usr", model="nemotron-3-super",
    )


# =============================================================================
# Programming defects propagate - the actual FU3A2C regression
# =============================================================================


class TestProgrammingDefectsPropagate:
    """A defect in ``_make_request`` must reach the caller, not become a
    normalized CONNECTION_ERROR. This is the central behavior change of
    FU3A2C: the old blanket ``except Exception`` at the end of ``complete()``
    is gone.
    """

    def test_runtime_error_from_make_request_propagates(self, monkeypatch):
        """The exact regression named in the corrective task."""
        transport = _transport()

        def _boom(self, request_body):
            raise RuntimeError("sentinel")

        monkeypatch.setattr(OpenAISemanticTransport, "_make_request", _boom)

        with pytest.raises(RuntimeError, match="sentinel"):
            _complete(transport)

    @pytest.mark.parametrize(
        "exception",
        [
            TypeError("sentinel-type"),
            AttributeError("sentinel-attr"),
            KeyError("sentinel-key"),
            ZeroDivisionError("sentinel-zero"),
        ],
    )
    def test_other_programming_exceptions_propagate(self, monkeypatch, exception):
        """No exception type is special-cased back into a swallow."""
        transport = _transport()

        def _boom(self, request_body):
            raise exception

        monkeypatch.setattr(OpenAISemanticTransport, "_make_request", _boom)

        with pytest.raises(type(exception)):
            _complete(transport)

    def test_defect_is_not_reported_as_connection_error(self, monkeypatch):
        """Never confuse the two: a propagated exception is not a result at
        all, bounded or otherwise - it must not come back disguised as
        ``TransportFailure(error_type="CONNECTION_ERROR")``.
        """
        transport = _transport()

        def _boom(self, request_body):
            raise RuntimeError("sentinel")

        monkeypatch.setattr(OpenAISemanticTransport, "_make_request", _boom)

        try:
            result = _complete(transport)
        except RuntimeError:
            result = None

        assert result is None, (
            "a RuntimeError must propagate as an exception, not resolve to "
            f"a TransportFailure/TransportResult ({result!r})"
        )


# =============================================================================
# Known network/provider conditions still normalize exactly as before
# =============================================================================


class TestKnownHttpErrorPaths:
    """Real ``urllib.error.HTTPError`` -> bounded HTTP classification."""

    def _error_transport(self, monkeypatch, status: int, body: dict | str = ""):
        err = _make_http_error(status, body)

        class _Opener:
            def open(self, req, **kw):
                raise err

        monkeypatch.setattr(
            "urllib.request.build_opener", lambda *a, **kw: _Opener()
        )
        return _transport()

    def test_http400_unsupported_parameter(self, monkeypatch):
        t = self._error_transport(
            monkeypatch,
            400,
            {
                "error": {
                    "message": (
                        "litellm.UnsupportedParamsError: openai does not "
                        "support parameters: ['reasoning_effort']"
                    ),
                },
            },
        )
        result = _complete(t)
        assert isinstance(result, TransportFailure)
        assert result.error_type == "UNSUPPORTED_PARAMETER"
        assert result.http_status == 400

    def test_http400_raw_provider_message_not_persisted(self, monkeypatch):
        t = self._error_transport(
            monkeypatch,
            400,
            {"error": {"message": "litellm.UnsupportedParamsError: SECRET_KEY_LEAK"}},
        )
        result = _complete(t)
        assert isinstance(result, TransportFailure)
        assert "SECRET_KEY_LEAK" not in json.dumps(result.to_dict())

    @pytest.mark.parametrize(
        ("status", "body", "expected"),
        [
            (401, "", "AUTHENTICATION_FAILED"),
            (404, "malformed", "MODEL_NOT_FOUND"),
            (429, "", "RATE_LIMITED"),
            (503, "", "PROVIDER_UNAVAILABLE"),
            (400, "malformed", "HTTP_ERROR"),
        ],
    )
    def test_status_only_fallback(self, monkeypatch, status, body, expected):
        t = self._error_transport(monkeypatch, status, body)
        result = _complete(t)
        assert isinstance(result, TransportFailure)
        assert result.error_type == expected
        assert result.http_status == status

    def test_malformed_error_body_keeps_baseline_classification(self, monkeypatch):
        """A non-JSON error body must not crash - and must not be silently
        misclassified either; it keeps the status-only baseline.
        """
        t = self._error_transport(monkeypatch, 429, "not json at all {")
        result = _complete(t)
        assert isinstance(result, TransportFailure)
        assert result.error_type == "RATE_LIMITED"

    def test_error_body_read_failure_keeps_baseline_classification(
        self, monkeypatch
    ):
        """``e.read()`` itself failing (a legitimate I/O condition, not a
        defect) must still return the status-only baseline, not crash.
        """
        err = urllib.error.HTTPError(
            url="https://example.invalid/v1/chat/completions",
            code=503,
            msg="HTTP 503",
            hdrs={},
            fp=None,
        )

        def _read_fails():
            raise OSError("connection reset while reading error body")

        err.read = _read_fails

        class _Opener:
            def open(self, req, **kw):
                raise err

        monkeypatch.setattr(
            "urllib.request.build_opener", lambda *a, **kw: _Opener()
        )
        result = _complete(_transport())
        assert isinstance(result, TransportFailure)
        assert result.error_type == "PROVIDER_UNAVAILABLE"


class TestMalformedProviderErrorMessage:
    """A provider may return syntactically valid JSON with a malformed error
    schema - e.g. ``{"message": 123}`` or ``{"error": {"message": 123}}``.
    That is malformed EXTERNAL data, not a local defect: it must not raise
    ``AttributeError`` out of ``str.lower()`` on a non-string value. The
    classifier must fall back to the bounded ``HTTP_ERROR`` baseline instead.
    """

    @pytest.mark.parametrize(
        "error_body",
        [
            {"message": 123},
            {"message": {}},
            {"message": []},
            {"message": True},
            {"error": {"message": 123}},
            {"error": {"message": {}}},
            {"error": {"message": []}},
            {"error": {"message": True}},
        ],
    )
    def test_classify_http_error_does_not_crash_on_non_string_message(
        self, error_body
    ):
        """Direct unit coverage of the classifier for every malformed shape."""
        result = _classify_http_error(400, error_body)
        assert result == "HTTP_ERROR"

    @pytest.mark.parametrize(
        "error_body",
        [
            {"message": 123},
            {"error": {"message": 123}},
        ],
    )
    def test_complete_status_400_with_non_string_message_via_httperror(
        self, monkeypatch, error_body
    ):
        """The real ``OpenAISemanticTransport.complete()`` path (HTTPError
        raised by urllib) with a status-400 response carrying a non-string
        provider message: no AttributeError, result is TransportFailure,
        error_type is the baseline HTTP_ERROR.
        """
        err = _make_http_error(400, error_body)

        class _Opener:
            def open(self, req, **kw):
                raise err

        monkeypatch.setattr(
            "urllib.request.build_opener", lambda *a, **kw: _Opener()
        )
        result = _complete(_transport())

        assert isinstance(result, TransportFailure)
        assert result.error_type == "HTTP_ERROR"
        assert result.http_status == 400

    def test_complete_status_400_with_non_string_message_in_band(
        self, monkeypatch
    ):
        """The in-band non-200 response path (``result.status_code != 200``
        inside ``complete()``, no HTTPError raised) with a malformed error
        schema must also not crash.
        """
        body = json.dumps({"error": {"message": 123}}).encode("utf-8")
        resp = _MockResp(status=400, body=body)

        class _Opener:
            def open(self, req, **kw):
                return resp

        monkeypatch.setattr(
            "urllib.request.build_opener", lambda *a, **kw: _Opener()
        )
        result = _complete(_transport())

        assert isinstance(result, TransportFailure)
        assert result.error_type == "HTTP_ERROR"
        assert result.http_status == 400


class TestKnownUrlAndTimeoutErrorPaths:
    """Real ``urllib.error.URLError`` and bare ``TimeoutError`` conditions."""

    def _opener_raising(self, monkeypatch, exc: BaseException):
        class _Opener:
            def open(self, req, **kw):
                raise exc

        monkeypatch.setattr(
            "urllib.request.build_opener", lambda *a, **kw: _Opener()
        )
        return _transport()

    def test_urlerror_timeout_reason(self, monkeypatch):
        t = self._opener_raising(
            monkeypatch, urllib.error.URLError(TimeoutError("timed out"))
        )
        result = _complete(t)
        assert isinstance(result, TransportFailure)
        assert result.error_type == "TIMEOUT"

    def test_urlerror_connection_refused_reason(self, monkeypatch):
        t = self._opener_raising(
            monkeypatch, urllib.error.URLError(ConnectionRefusedError("refused"))
        )
        result = _complete(t)
        assert isinstance(result, TransportFailure)
        assert result.error_type == "CONNECTION_ERROR"

    def test_urlerror_dns_reason(self, monkeypatch):
        t = self._opener_raising(
            monkeypatch, urllib.error.URLError(OSError("Name or service not known"))
        )
        result = _complete(t)
        assert isinstance(result, TransportFailure)
        assert result.error_type == "CONNECTION_ERROR"

    def test_bare_timeout_error(self, monkeypatch):
        t = self._opener_raising(monkeypatch, TimeoutError("timed out"))
        result = _complete(t)
        assert isinstance(result, TransportFailure)
        assert result.error_type == "TIMEOUT"

    def test_bare_connection_reset_after_open(self, monkeypatch):
        """A reset that happens on ``response.read()`` (inside our own
        ``_make_request``, after ``opener.open()`` already returned) is not
        wrapped into URLError by urllib - it surfaces as a raw ``OSError``
        subclass and must still normalize to CONNECTION_ERROR, not crash.
        """

        class _RespThatResetsOnRead:
            status = 200

            def read(self):
                raise ConnectionResetError("connection reset by peer")

            def __enter__(self):
                return self

            def __exit__(self, *a):
                pass

        class _Opener:
            def open(self, req, **kw):
                return _RespThatResetsOnRead()

        monkeypatch.setattr(
            "urllib.request.build_opener", lambda *a, **kw: _Opener()
        )
        result = _complete(_transport())
        assert isinstance(result, TransportFailure)
        assert result.error_type == "CONNECTION_ERROR"

    def test_body_not_valid_utf8(self, monkeypatch):
        """A response body that is not valid UTF-8 is malformed provider
        data, not a defect - it must normalize, not crash.
        """

        class _RespWithBadBytes:
            status = 200

            def read(self):
                return b"\xff\xfe not utf-8"

            def __enter__(self):
                return self

            def __exit__(self, *a):
                pass

        class _Opener:
            def open(self, req, **kw):
                return _RespWithBadBytes()

        monkeypatch.setattr(
            "urllib.request.build_opener", lambda *a, **kw: _Opener()
        )
        result = _complete(_transport())
        assert isinstance(result, TransportFailure)
        assert result.error_type == "CONNECTION_ERROR"


class TestKnownResponseShapePaths:
    """A 200 response whose body is malformed JSON, or malformed shape."""

    def _ok_transport(self, monkeypatch, raw_body: bytes):
        resp = _MockResp(status=200, body=raw_body)

        class _Opener:
            def open(self, req, **kw):
                return resp

        monkeypatch.setattr(
            "urllib.request.build_opener", lambda *a, **kw: _Opener()
        )
        return _transport()

    def test_malformed_json_200_body(self, monkeypatch):
        t = self._ok_transport(monkeypatch, b"not json {")
        result = _complete(t)
        assert isinstance(result, TransportFailure)
        assert result.error_type == "RESPONSE_DECODE_ERROR"

    def test_top_level_json_array_not_object(self, monkeypatch):
        t = self._ok_transport(monkeypatch, b"[1, 2, 3]")
        result = _complete(t)
        assert isinstance(result, TransportFailure)
        assert result.error_type == "INVALID_PROVIDER_RESPONSE"

    def test_top_level_json_scalar_not_object(self, monkeypatch):
        """A bare JSON int would raise TypeError on ``"choices" not in 42``
        if not explicitly guarded - this proves it fails closed instead.
        """
        t = self._ok_transport(monkeypatch, b"42")
        result = _complete(t)
        assert isinstance(result, TransportFailure)
        assert result.error_type == "INVALID_PROVIDER_RESPONSE"

    def test_choices_missing(self, monkeypatch):
        t = self._ok_transport(monkeypatch, json.dumps({}).encode("utf-8"))
        result = _complete(t)
        assert isinstance(result, TransportFailure)
        assert result.error_type == "INVALID_PROVIDER_RESPONSE"

    def test_choices_empty(self, monkeypatch):
        t = self._ok_transport(
            monkeypatch, json.dumps({"choices": []}).encode("utf-8")
        )
        result = _complete(t)
        assert isinstance(result, TransportFailure)
        assert result.error_type == "INVALID_PROVIDER_RESPONSE"

    def test_choices_is_a_string_not_a_list(self, monkeypatch):
        """``choices`` present and truthy but the wrong TYPE - would raise
        AttributeError on ``"n".get(...)`` (indexing a string) if not
        explicitly handled.
        """
        t = self._ok_transport(
            monkeypatch, json.dumps({"choices": "not a list"}).encode("utf-8")
        )
        result = _complete(t)
        assert isinstance(result, TransportFailure)
        assert result.error_type == "INVALID_PROVIDER_RESPONSE"

    def test_choices_entries_are_strings_not_objects(self, monkeypatch):
        """A list of strings instead of a list of message objects - would
        raise AttributeError on ``"oops".get("message", {})``.
        """
        t = self._ok_transport(
            monkeypatch, json.dumps({"choices": ["oops"]}).encode("utf-8")
        )
        result = _complete(t)
        assert isinstance(result, TransportFailure)
        assert result.error_type == "INVALID_PROVIDER_RESPONSE"

    def test_usage_is_not_a_mapping(self, monkeypatch):
        """``usage`` present but not a dict - would raise AttributeError on
        ``usage.get(...)``.
        """
        t = self._ok_transport(
            monkeypatch,
            json.dumps(
                {
                    "choices": [{"message": {"content": "hi"}}],
                    "usage": "not a mapping",
                }
            ).encode("utf-8"),
        )
        result = _complete(t)
        assert isinstance(result, TransportFailure)
        assert result.error_type == "INVALID_PROVIDER_RESPONSE"


class TestKnownSuccessPath:
    """The canonical 200 success path is unaffected by the narrowing."""

    def test_canonical_success(self, monkeypatch):
        body = {
            "model": "nemotron-3-super",
            "choices": [
                {
                    "message": {"content": "hello", "reasoning": "SECRET_SENTINEL"},
                    "finish_reason": "stop",
                }
            ],
            "usage": {
                "prompt_tokens": 100,
                "completion_tokens": 200,
                "total_tokens": 300,
            },
        }
        resp = _MockResp(status=200, body=json.dumps(body).encode("utf-8"))

        class _Opener:
            def open(self, req, **kw):
                return resp

        monkeypatch.setattr(
            "urllib.request.build_opener", lambda *a, **kw: _Opener()
        )
        result = _complete(_transport())

        assert isinstance(result, TransportResult)
        assert result.raw_output == "hello"
        assert result.provider_reported_model == "nemotron-3-super"
        assert result.finish_reason == "stop"
        assert result.token_usage == {
            "prompt_tokens": 100,
            "completion_tokens": 200,
            "total_tokens": 300,
        }
        # message.reasoning is never extracted into raw_output or persisted.
        assert "SECRET_SENTINEL" not in result.raw_output
        assert "SECRET_SENTINEL" not in json.dumps(result.to_dict())

    def test_missing_top_level_model_is_none(self, monkeypatch):
        body = {"choices": [{"message": {"content": "hi"}}]}
        resp = _MockResp(status=200, body=json.dumps(body).encode("utf-8"))

        class _Opener:
            def open(self, req, **kw):
                return resp

        monkeypatch.setattr(
            "urllib.request.build_opener", lambda *a, **kw: _Opener()
        )
        result = _complete(_transport())

        assert isinstance(result, TransportResult)
        assert result.provider_reported_model is None

    def test_missing_finish_reason_is_none(self, monkeypatch):
        body = {"choices": [{"message": {"content": "hi"}}]}
        resp = _MockResp(status=200, body=json.dumps(body).encode("utf-8"))

        class _Opener:
            def open(self, req, **kw):
                return resp

        monkeypatch.setattr(
            "urllib.request.build_opener", lambda *a, **kw: _Opener()
        )
        result = _complete(_transport())

        assert isinstance(result, TransportResult)
        assert result.finish_reason is None
