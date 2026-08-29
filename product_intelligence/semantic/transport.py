"""Semantic model transport layer (PRODUCT-INTEL.SEMANTIC.TRANSPORT).

Neutral production transport abstraction for calling semantic model providers
via an OpenAI-compatible chat completions API.

Single source of truth (FU3A2B)
--------------------------------
This module is the CANONICAL implementation, importable by both production and
the evaluation harness without either depending on the other. Both
``product_intelligence.semantic.runtime`` (lazily, at transport-construction
time) and ``product_intelligence.evaluation.semantic.*`` import THIS module;
neither imports the other.

``product_intelligence/evaluation/semantic/transport.py`` re-exports every
name from here; it keeps no second implementation. Production code imports
this module lazily (inside transport construction, never at module import
time) so importing ``product_intelligence.semantic`` stays free of urllib and
of the evaluation harness.

No live model call happens at import time. All tests use fake transports.
"""

from __future__ import annotations

import os
import time
import urllib.error
import urllib.request
import json
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any


# ---------------------------------------------------------------------------
# Fatal error codes (bounded vocabulary)
# ---------------------------------------------------------------------------

# RUN-FATAL: These errors abort the entire run after recording the attempted case
RUN_FATAL_ERROR_TYPES = frozenset([
    "AUTHENTICATION_FAILED",
    "MODEL_NOT_FOUND",
    "MODEL_IDENTITY_MISMATCH",
    "UNSUPPORTED_PARAMETER",
    "INVALID_REQUEST_CONFIGURATION",
    "RATE_LIMITED",
    "PROVIDER_UNAVAILABLE",
])

# CASE-LOCAL: These errors only affect the current case and allow continuation
CASE_LOCAL_ERROR_TYPES = frozenset([
    "CASE_REJECTED",
])

# Network-level errors (non-fatal for run, but fail the case)
NETWORK_ERROR_TYPES = frozenset([
    "TIMEOUT",
    "DNS_ERROR",
    "TLS_ERROR",
    "CONNECTION_ERROR",
])

# Response-level errors (non-fatal for run, but fail the case)
RESPONSE_ERROR_TYPES = frozenset([
    "HTTP_ERROR",
    "INVALID_PROVIDER_RESPONSE",
    "RESPONSE_DECODE_ERROR",
])

# All error types for validation
ALL_ERROR_TYPES = RUN_FATAL_ERROR_TYPES | CASE_LOCAL_ERROR_TYPES | NETWORK_ERROR_TYPES | RESPONSE_ERROR_TYPES


# ---------------------------------------------------------------------------
# Error classification helpers (bounded vocabulary)
# ---------------------------------------------------------------------------


def _classify_http_error(status_code: int, error_body: dict[str, Any] | None = None) -> str:
    """Classify HTTP error status into bounded error types.

    Inspects only in memory. Never persists raw body/message.

    Args:
        status_code: HTTP status code
        error_body: Parsed error response body (optional)

    Returns:
        Bounded error type string
    """
    if error_body is None:
        error_body = {}

    # For 400/401/403/404/429/5xx, inspect structured error fields
    error_code = None
    error_type_field = None

    if isinstance(error_body, dict):
        # Try structured OpenAI-compatible fields
        if "error" in error_body and isinstance(error_body["error"], dict):
            err_obj = error_body["error"]
            error_code = err_obj.get("code")
            error_type_field = err_obj.get("type")
            message = err_obj.get("message")
        else:
            message = None
        # Also check top-level message for non-standard formats
        if message is None:
            message = error_body.get("message")

    # Classification based on status code and error fields
    if status_code in (401, 403):
        return "AUTHENTICATION_FAILED"

    if status_code == 429:
        return "RATE_LIMITED"

    if status_code == 404:
        return "MODEL_NOT_FOUND"

    if status_code == 400:
        # Inspect error code/type for 400s - do NOT treat all 400 as fatal
        if error_code == "unsupported_parameter":
            return "UNSUPPORTED_PARAMETER"
        if error_code == "invalid_request":
            return "INVALID_REQUEST_CONFIGURATION"
        if error_type_field == "model_not_found":
            return "MODEL_NOT_FOUND"
        if error_type_field == "context_length_exceeded":
            return "INVALID_REQUEST_CONFIGURATION"
        if error_code == "content_policy_violation":
            return "CASE_REJECTED"

        # Message-based classification for LiteLLM and other providers
        # Inspect message for unsupported parameter indicators (IN MEMORY ONLY)
        #
        # A provider may return syntactically valid JSON with a malformed
        # error schema, e.g. {"message": 123} or {"error": {"message": 123}}.
        # That is malformed EXTERNAL data, not a local defect - it must not
        # crash string classification. Only a non-empty str is inspected;
        # anything else falls through to the bounded HTTP_ERROR default below.
        if isinstance(message, str) and message:
            msg_lower = message.lower()
            if (
                "unsupported params" in msg_lower or
                "unsupported parameter" in msg_lower or
                "unsupported parameters" in msg_lower or
                "unsupportedparamserror" in msg_lower or
                "does not support parameters" in msg_lower
            ):
                return "UNSUPPORTED_PARAMETER"

        # Default: non-fatal for case, run continues
        return "HTTP_ERROR"

    if 500 <= status_code < 600:
        return "PROVIDER_UNAVAILABLE"

    # Unknown/unclassifiable - remain bounded HTTP_ERROR
    return "HTTP_ERROR"


@dataclass(frozen=True)
class TransportResult:
    """Result from a semantic model transport call."""

    raw_output: str
    latency_ms: float
    provider_status: str
    provider_id: str | None = None
    model_id: str | None = None
    token_usage: dict[str, int] | None = None
    # provider_reported_model is the model name returned by the provider
    # (may differ from requested model for thinking models, etc.)
    provider_reported_model: str | None = None
    # finish_reason is the reason the model stopped generating
    finish_reason: str | None = None

    def to_dict(self) -> dict[str, Any]:
        """Return a dictionary representation for JSON serialization."""
        return {
            "raw_output": self.raw_output,
            "latency_ms": self.latency_ms,
            "provider_status": self.provider_status,
            "provider_id": self.provider_id,
            "model_id": self.model_id,
            "token_usage": self.token_usage,
            "provider_reported_model": self.provider_reported_model,
            "finish_reason": self.finish_reason,
        }


@dataclass(frozen=True)
class TransportFailure:
    """Transport failure result with safe normalized error reporting.

    Only safe bounded fields are persisted. No raw exception messages,
    URLs, API keys, or unbounded diagnostic text.
    """

    # Safe bounded error codes from the normalized vocabulary
    error_type: str  # TIMEOUT, DNS_ERROR, TLS_ERROR, CONNECTION_ERROR, HTTP_ERROR,
                     # INVALID_PROVIDER_RESPONSE, RESPONSE_DECODE_ERROR
    transport_status: str | None = None  # Numeric HTTP status if available
    http_status: int | None = None  # Numeric HTTP status code

    # error_message is NOT persisted - raw exception content is never stored
    # error_message field remains for API compatibility but is always None
    # in persisted form

    def to_dict(self) -> dict[str, Any]:
        """Return a dictionary representation for JSON serialization.

        Only safe bounded fields are included. No raw error messages,
        exception strings, URLs, or credentials.
        """
        return {
            "error_type": self.error_type,
            "transport_status": self.transport_status,
            "http_status": self.http_status,
            # error_message intentionally omitted - raw content never persisted
        }


# ---------------------------------------------------------------------------
# Transport interface
# ---------------------------------------------------------------------------


class SemanticModelTransport(ABC):
    """Abstract interface for semantic model transports."""

    @abstractmethod
    def complete(
        self,
        *,
        system_prompt: str,
        user_prompt: str,
        model: str,
        temperature: float = 0.0,
        max_tokens: int = 1024,
    ) -> TransportResult | TransportFailure:
        """Call the semantic model with prompts.

        Args:
            system_prompt: The system prompt
            user_prompt: The user prompt
            model: The bare qualified model ID (e.g. ``"nemotron-3-super"``),
                not a ``provider/model`` compound string. The caller (the
                production runtime, or a benchmark run config) already knows
                which provider it is talking to; this is the model name that
                provider's own API expects in its request body.
            temperature: Temperature setting
            max_tokens: Maximum completion tokens

        Returns:
            TransportResult on success, TransportFailure on error
        """
        pass


# ---------------------------------------------------------------------------
# Fake transport for tests
# ---------------------------------------------------------------------------


class FakeSemanticModelTransport(SemanticModelTransport):
    """Fake transport for testing.

    Returns configurable responses without network calls.
    """

    def __init__(
        self,
        *,  # Force keyword args
        responses: dict[str, str] | None = None,
        failures: set[str] | None = None,
        failure_error_types: dict[str, str] | None = None,
        case_error_map: dict[str, str] | None = None,
        provider_status: str = "200",
        provider_id: str = "fake",
        model_id: str | None = None,
        provider_reported_model: str | None = None,
        finish_reason: str | None = None,
        case_ids: tuple[str, ...] | None = None,  # Ordered case IDs for testing
    ):
        """Initialize fake transport.

        Args:
            responses: Dict mapping case_id -> raw_output for valid responses
            failures: Set of case_ids that should return failures (uses CONNECTION_ERROR)
            failure_error_types: Dict mapping case_id -> error_type for specific failures
            case_error_map: Dict mapping case_id -> error_type (alternative to failure_error_types)
            provider_status: HTTP status to return
            provider_id: Provider identifier
            model_id: Model ID to report (can be different from requested)
            provider_reported_model: Model name reported by provider (if different)
            finish_reason: Reason the model stopped generating
            case_ids: Ordered tuple of case IDs being processed (for testing with non-heuristic extraction)
        """
        self._responses = responses or {}
        self._failures = failures or set()
        self._failure_error_types = failure_error_types or {}
        self._case_error_map = case_error_map or {}
        self._provider_status = provider_status
        self._provider_id = provider_id
        self._model_id = model_id
        self._provider_reported_model = provider_reported_model
        self._finish_reason = finish_reason
        self._case_ids = case_ids or ()
        self.call_count = 0  # Track number of calls for testing

    def complete(
        self,
        *,
        system_prompt: str,
        user_prompt: str,
        model: str,
        temperature: float = 0.0,
        max_tokens: int = 1024,
    ) -> TransportResult | TransportFailure:
        """Return fake response without network call."""
        self.call_count += 1  # Track call count

        # Extract case_id from prompts (for testing)
        case_id = self._extract_case_id(system_prompt, user_prompt)

        # If prompt extraction failed but we have case_ids, use call index
        if case_id == "UNKNOWN" and self._case_ids and self.call_count <= len(self._case_ids):
            case_id = self._case_ids[self.call_count - 1]

        # Check for specific error type first
        if case_id in self._failure_error_types:
            error_type = self._failure_error_types[case_id]
            return TransportFailure(
                error_type=error_type,
                transport_status=self._provider_status,
                http_status=None,
            )

        if case_id in self._failures:
            return TransportFailure(
                error_type="CONNECTION_ERROR",
                transport_status=self._provider_status,
                http_status=None,
            )

        raw_output = self._responses.get(case_id, '{"decision": "MATCH", "confidence": "HIGH", "matched_attributes": [], "conflicting_attributes": [], "missing_critical_attributes": [], "reason_code": "test"}')

        return TransportResult(
            raw_output=raw_output,
            latency_ms=15.0,
            provider_status=self._provider_status,
            provider_id=self._provider_id,
            model_id=self._model_id or model,  # Report model_id (can differ from requested)
            provider_reported_model=self._provider_reported_model,
            finish_reason=self._finish_reason,
            token_usage={"prompt_tokens": 500, "completion_tokens": 50},
        )

    def _extract_case_id(self, system_prompt: str, user_prompt: str) -> str:
        """Extract case_id from prompts (testing helper)."""
        # Simple heuristic: look for SMQ-XXXX in prompts
        import re
        match = re.search(r"SMQ-\d+", system_prompt + user_prompt)
        if match:
            return match.group(0)
        return "UNKNOWN"


# ---------------------------------------------------------------------------
# OpenAI-compatible HTTP transport
# ---------------------------------------------------------------------------


class OpenAISemanticTransport(SemanticModelTransport):
    """OpenAI-compatible HTTP transport.

    Supports providers that implement the chat completions API:
    - amax (OpenAI-compatible endpoint)
    - vllm-262k (vLLM server)

    Credentials are read from environment variables.
    """

    def __init__(
        self,
        *,
        base_url: str,
        api_key: str | None = None,
        request_timeout_seconds: float = 300.0,
        provider_id: str = "openai-compatible",
    ):
        """Initialize OpenAI-compatible transport.

        Args:
            base_url: Base URL for the endpoint (e.g., https://api.amax.ai/v1)
            api_key: API key if required (optional for some endpoints)
            request_timeout_seconds: Request timeout in seconds (default: 300.0)
            provider_id: Provider identifier for provenance
        """
        import math

        # Validate request_timeout_seconds: must be numeric, finite, and > 0
        if not isinstance(request_timeout_seconds, (int, float)):
            raise ValueError(f"request_timeout_seconds must be numeric, got {type(request_timeout_seconds).__name__}")
        if isinstance(request_timeout_seconds, bool):
            raise ValueError(f"request_timeout_seconds must not be boolean, got {type(request_timeout_seconds).__name__}")
        if not math.isfinite(request_timeout_seconds):
            raise ValueError(f"request_timeout_seconds must be finite, got {request_timeout_seconds}")
        if request_timeout_seconds <= 0:
            raise ValueError(f"request_timeout_seconds must be > 0, got {request_timeout_seconds}")

        self._base_url = base_url.rstrip("/")
        self._api_key = api_key
        self._request_timeout_seconds = request_timeout_seconds
        self._provider_id = provider_id

    def complete(
        self,
        *,
        system_prompt: str,
        user_prompt: str,
        model: str,
        temperature: float = 0.0,
        max_tokens: int = 1024,
    ) -> TransportResult | TransportFailure:
        """Call OpenAI-compatible endpoint with prompts.

        Uses safe normalized error reporting. No raw exception messages,
        URLs, API keys, or credentials are persisted.

        Redirects are NOT followed - 3xx responses fail closed.
        """
        start_time = time.perf_counter()

        try:
            # Build request body
            request_body = {
                "model": model,
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                "temperature": temperature,
                "max_tokens": max_tokens,
            }

            # Make request
            result = self._make_request(request_body)

            elapsed_ms = (time.perf_counter() - start_time) * 1000

            # Parse response
            if result.status_code != 200:
                # Try to classify the error from response body if available.
                # json.JSONDecodeError is the only exception a malformed (but
                # syntactically-JSON-attempted) error body can legitimately
                # raise here; anything else is a real defect and must not be
                # swallowed.
                error_type = "HTTP_ERROR"
                try:
                    response_data = json.loads(result.body)
                    if isinstance(response_data, dict):
                        error_type = _classify_http_error(result.status_code, response_data)
                except json.JSONDecodeError:
                    pass  # Use default HTTP_ERROR if body can't be parsed

                return TransportFailure(
                    error_type=error_type,
                    transport_status=str(result.status_code),
                    http_status=result.status_code,
                )

            try:
                response_data = json.loads(result.body)
            except json.JSONDecodeError:
                return TransportFailure(
                    error_type="RESPONSE_DECODE_ERROR",
                    transport_status="200",
                    http_status=200,
                )

            # A 200 response whose body decodes to something other than a
            # JSON object (e.g. a bare number or a JSON array) is malformed
            # provider data, not a programming defect - fail closed instead
            # of letting the membership/indexing below raise TypeError.
            if not isinstance(response_data, dict):
                return TransportFailure(
                    error_type="INVALID_PROVIDER_RESPONSE",
                    transport_status="200",
                    http_status=200,
                )

            # Extract content
            if "choices" not in response_data or not response_data["choices"]:
                return TransportFailure(
                    error_type="INVALID_PROVIDER_RESPONSE",
                    transport_status="200",
                    http_status=200,
                )

            try:
                choice = response_data["choices"][0]
                raw_output = choice.get("message", {}).get("content", "")

                # Extract provider-reported model and finish_reason
                provider_reported_model = response_data.get("model")
                finish_reason = choice.get("finish_reason")

                # Extract token usage if available
                token_usage = None
                if "usage" in response_data:
                    usage = response_data["usage"]
                    token_usage = {
                        "prompt_tokens": usage.get("prompt_tokens", 0),
                        "completion_tokens": usage.get("completion_tokens", 0),
                        "total_tokens": usage.get("total_tokens", 0),
                    }
            except (AttributeError, TypeError, KeyError, IndexError):
                # The body was valid JSON with a "choices" list, but its
                # internal shape did not match the API contract (e.g. an
                # entry that is a string instead of an object, or "usage"
                # that is not a mapping). This is malformed PROVIDER data,
                # handled with the same bounded code as a missing/empty
                # choices list above - not a blanket Exception catch, and
                # not something that should surface as an unhandled crash.
                return TransportFailure(
                    error_type="INVALID_PROVIDER_RESPONSE",
                    transport_status="200",
                    http_status=200,
                )

            return TransportResult(
                raw_output=raw_output,
                latency_ms=elapsed_ms,
                provider_status="200",
                provider_id=self._provider_id,
                model_id=model,
                provider_reported_model=provider_reported_model,
                finish_reason=finish_reason,
                token_usage=token_usage,
            )

        except urllib.error.HTTPError as e:
            # HTTP errors (4xx, 5xx) - fail closed with classification
            error_type = _classify_http_error(e.code)

            # Try to refine classification using structured body if available.
            # e.read() / .decode("utf-8") / json.loads() can legitimately fail
            # on a malformed or non-UTF-8 error body; that is expected
            # provider-side variance, not a defect, so the baseline
            # classification above is kept. Anything else is not swallowed.
            try:
                raw_body = e.read()
                decoded_body = raw_body.decode("utf-8")
                parsed_body = json.loads(decoded_body)

                if isinstance(parsed_body, dict):
                    error_type = _classify_http_error(e.code, parsed_body)
            except (OSError, UnicodeDecodeError, json.JSONDecodeError):
                # Keep baseline classification if body can't be read/parsed
                pass

            return TransportFailure(
                error_type=error_type,
                transport_status=str(e.code),
                http_status=e.code,
            )
        except urllib.error.URLError as e:
            # Network-level errors
            reason = e.reason
            if isinstance(reason, TimeoutError):
                error_type = "TIMEOUT"
            elif isinstance(reason, OSError):
                # Could be DNS, connection refused, etc.
                error_type = "CONNECTION_ERROR"
            else:
                error_type = "CONNECTION_ERROR"

            return TransportFailure(
                error_type=error_type,
                transport_status=None,
                http_status=None,
            )
        except TimeoutError:
            return TransportFailure(
                error_type="TIMEOUT",
                transport_status=None,
                http_status=None,
            )
        except (OSError, UnicodeDecodeError):
            # A legitimate network/decode-layer failure that urllib did not
            # wrap into HTTPError/URLError - e.g. a connection reset mid-read
            # (response.read() happens in our own _make_request, after
            # urlopen has already returned), or a response body that is not
            # valid UTF-8. Still bounded: no raw exception text is persisted.
            #
            # A genuine programming defect (TypeError, AttributeError,
            # RuntimeError, ...) is deliberately NOT caught here. It
            # propagates to the caller instead of being reported as a fake
            # CONNECTION_ERROR - that used to be a blanket `except Exception`
            # and is exactly the behavior this narrowing removes.
            return TransportFailure(
                error_type="CONNECTION_ERROR",
                transport_status=None,
                http_status=None,
            )

    def _make_request(self, request_body: dict[str, Any]) -> "_HTTPResponse":
        """Make HTTP request and return response wrapper.

        Redirect following is DISABLED - 3xx responses fail closed.
        Authorization header is NOT forwarded to redirected destinations.
        """
        url = f"{self._base_url}/chat/completions"

        data = json.dumps(request_body).encode("utf-8")

        req = urllib.request.Request(
            url,
            data=data,
            headers={
                "Content-Type": "application/json",
                "Accept": "application/json",
            },
            method="POST",
        )

        if self._api_key is not None:
            req.add_header("Authorization", f"Bearer {self._api_key}")

        # Use a redirect handler that does NOT follow redirects
        # This ensures 3xx responses fail closed rather than forwarding
        # the Authorization header to an unintended destination
        class NoRedirectHandler(urllib.request.HTTPRedirectHandler):
            def redirect_request(self, req, fp, code, msg, headers, newurl):
                return None  # Don't follow redirect

        opener = urllib.request.build_opener(NoRedirectHandler)

        try:
            with opener.open(req, timeout=self._request_timeout_seconds) as response:
                body = response.read().decode("utf-8")
                return _HTTPResponse(status_code=response.status, body=body)
        except urllib.error.HTTPError as e:
            # Re-raise HTTP errors so they can be handled above
            raise
        except urllib.error.URLError as e:
            # Re-raise URL errors so they can be handled above
            raise


@dataclass(frozen=True)
class _HTTPResponse:
    """Simple HTTP response wrapper."""

    status_code: int
    body: str


# ---------------------------------------------------------------------------
# Provider configuration helpers
# ---------------------------------------------------------------------------


def get_openai_transport_for_provider(
    provider: str,
    request_timeout_seconds: float = 300.0,
) -> OpenAISemanticTransport:
    """Create OpenAI transport from environment configuration.

    Args:
        provider: Provider name ('amax' or 'vllm-262k')
        request_timeout_seconds: Request timeout in seconds (default: 300.0)

    Returns:
        Configured OpenAISemanticTransport

    Raises:
        ValueError: If provider is not configured
    """
    if provider == "amax":
        base_url = os.environ.get("PI_SEMANTIC_AMAX_BASE_URL")
        api_key = os.environ.get("PI_SEMANTIC_AMAX_API_KEY")
        if not base_url:
            raise ValueError(
                "PI_SEMANTIC_AMAX_BASE_URL environment variable is required"
            )
        return OpenAISemanticTransport(
            base_url=base_url,
            api_key=api_key if api_key else None,
            request_timeout_seconds=request_timeout_seconds,
            provider_id="amax",
        )

    elif provider == "vllm-262k":
        base_url = os.environ.get("PI_SEMANTIC_VLLM_262K_BASE_URL")
        api_key = os.environ.get("PI_SEMANTIC_VLLM_262K_API_KEY")
        if not base_url:
            raise ValueError(
                "PI_SEMANTIC_VLLM_262K_BASE_URL environment variable is required"
            )
        return OpenAISemanticTransport(
            base_url=base_url,
            api_key=api_key if api_key else None,
            request_timeout_seconds=request_timeout_seconds,
            provider_id="vllm-262k",
        )

    else:
        raise ValueError(f"Unknown provider: {provider}")
