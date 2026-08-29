"""Production semantic runtime (PRODUCT-INTEL.SEMANTIC.RUNTIME).

The single production entry point for semantic model evaluation.

Central invariant
-----------------
FALLBACK ON EXECUTION FAILURE, NEVER FALLBACK ON SEMANTIC DISAGREEMENT.

A valid primary response (``MATCH``, ``NO_MATCH`` or ``UNCERTAIN``) is FINAL:
exactly one primary call, zero fallback calls. Low confidence, a conservative
reason code, or a caller who "disagrees" never triggers a second model.

Qualified route (pinned)
------------------------
The production route is fixed by formal qualification and is NOT caller
configurable::

    PRIMARY   amax / nemotron-3-super
    FALLBACK  vllm-262k / Qwen3.6-27B-262K
    temperature 0.0, max_tokens 32768

``SemanticRuntimeConfig`` keeps these as fields for compatibility, but any
value differing from the qualified constants is rejected by validation before
any transport is built or called. Only the request timeout stays configurable.

Import purity
-------------
Importing ``product_intelligence.semantic`` must not import the evaluation
harness, Django, or any network client. The live transport dependency
(``product_intelligence.semantic.transport`` - itself neutral, never the
evaluation harness) is therefore resolved lazily, inside transport
construction, never at module import time. Enforced by
``tests/semantic/test_runtime_boundaries.py``.

Dependency direction::

    semantic.runtime  <-  semantic.contract   (prompt v1.1, parser, vocabulary)
    semantic.runtime  ->  semantic.transport  (lazily; neutral, not evaluation)

Neither this module nor any other production semantic source imports
``product_intelligence.evaluation`` at all, at module level or lazily.
``product_intelligence.evaluation.semantic.transport`` re-exports
``semantic.transport`` for the harness; the dependency runs one way, from the
harness to the neutral module, never from production to the harness.

Safety
------
No raw provider body, no exception text, no API key, and no chain-of-thought
ever reaches a ``SemanticRuntimeResult``. Programming defects are never
converted into a transport failure: an unexpected exception raised by an
injected transport propagates and never causes fallback.
"""

from __future__ import annotations

import logging
import math
import os
import time
from dataclasses import dataclass
from enum import Enum
from typing import Any

from product_intelligence.semantic.contract import (
    SEMANTIC_PROMPT_VERSION,
    ConfidenceLevel,
    RawOutputParseError,
    SemanticDecision,
    SemanticMatchResponse,
    build_prompt,
    parse_raw_output,
    validate_response,
)

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Qualified production route (FROZEN - not caller configurable)
# ---------------------------------------------------------------------------


PRIMARY_PROVIDER = "amax"
PRIMARY_MODEL = "nemotron-3-super"

FALLBACK_PROVIDER = "vllm-262k"
FALLBACK_MODEL = "Qwen3.6-27B-262K"

SEMANTIC_TEMPERATURE = 0.0
SEMANTIC_MAX_TOKENS = 32768

# The timeout is the ONLY tunable generation-adjacent setting.
DEFAULT_REQUEST_TIMEOUT_SECONDS = 300.0
MAX_REQUEST_TIMEOUT_SECONDS = 3600.0


def _default_timeout_seconds() -> float:
    """Read the configured request timeout from the environment.

    Absence is not an error: the qualified default is used. Presence with an
    unreadable or non-finite value IS an error - it fails closed rather than
    silently falling back to the default, because a caller who set the
    variable and got it wrong deserves to know, not to have their mistake
    quietly discarded.

    Raises:
        SemanticRuntimeConfigError: If the environment variable is set but is
            not a parseable, finite number (including "nan", "inf", "-inf",
            which ``float()`` parses successfully but which are not usable
            timeouts).
    """
    raw = os.environ.get("PI_SEMANTIC_REQUEST_TIMEOUT_SECONDS")
    if raw is None:
        return DEFAULT_REQUEST_TIMEOUT_SECONDS
    try:
        value = float(raw)
    except (TypeError, ValueError):
        raise SemanticRuntimeConfigError(
            "PI_SEMANTIC_REQUEST_TIMEOUT_SECONDS is set but is not a valid "
            f"number: {raw!r}"
        )
    if not math.isfinite(value):
        raise SemanticRuntimeConfigError(
            "PI_SEMANTIC_REQUEST_TIMEOUT_SECONDS must be finite, got "
            f"{raw!r}"
        )
    return value


# ---------------------------------------------------------------------------
# Fallback eligibility: EXPLICIT ALLOWLIST
# ---------------------------------------------------------------------------
#
# Fallback is permitted ONLY for a failure named in this set. Anything else - a
# local configuration defect, an unrecognised error code, a programming
# exception - fails closed after exactly one primary attempt.
#
# This is deliberately an allowlist and NOT "anything outside a deny set": an
# error code the runtime does not recognise must never silently buy a second
# paid model call.

PRIMARY_FALLBACK_ELIGIBLE_ERRORS = frozenset(
    {
        "TIMEOUT",
        "DNS_ERROR",
        "TLS_ERROR",
        "CONNECTION_ERROR",
        "RATE_LIMITED",
        "HTTP_ERROR",
        "PROVIDER_UNAVAILABLE",
        "AUTHENTICATION_FAILED",
        "MODEL_NOT_FOUND",
        "EMPTY_RESPONSE",
        "MALFORMED_JSON",
        "SCHEMA_INVALID",
        "MODEL_IDENTITY_MISMATCH",
        # An INVALID_PROVIDER_RESPONSE (malformed HTTP-200 envelope: missing/
        # empty/malformed "choices") is an execution/output-contract failure
        # of the SAME kind as MALFORMED_JSON or SCHEMA_INVALID - the primary
        # simply did not deliver a usable answer. It is fallback eligible for
        # exactly the reason those are.
        "INVALID_RESPONSE",
    }
)

# Explicitly NOT fallback eligible. Listed for documentation and for the guard
# test that proves the two sets do not overlap.
PRIMARY_NON_FALLBACK_ERRORS = frozenset(
    {
        "INVALID_REQUEST_CONFIGURATION",
        "UNSUPPORTED_PARAMETER",
        "PROVIDER_NOT_CONFIGURED",
        "UNKNOWN_ERROR",
        # A content-policy rejection is a property of the CASE (the prompt
        # content itself), not of the provider's momentary availability.
        # Retrying the identical prompt against a different model does not
        # change what was rejected - fallback would not help.
        "CASE_REJECTED",
    }
)


# ---------------------------------------------------------------------------
# Bounded failure taxonomy
# ---------------------------------------------------------------------------


class SemanticRuntimeErrorType(str, Enum):
    """Bounded vocabulary for semantic runtime failures.

    These are the ONLY error types the runtime exposes. No raw exception
    string and no provider-specific message ever appears here.
    """

    # Primary attempt failures.
    PRIMARY_TIMEOUT = "PRIMARY_TIMEOUT"
    PRIMARY_CONNECTION_ERROR = "PRIMARY_CONNECTION_ERROR"
    PRIMARY_RATE_LIMITED = "PRIMARY_RATE_LIMITED"
    PRIMARY_HTTP_ERROR = "PRIMARY_HTTP_ERROR"
    PRIMARY_AUTHENTICATION_FAILED = "PRIMARY_AUTHENTICATION_FAILED"
    PRIMARY_MODEL_NOT_FOUND = "PRIMARY_MODEL_NOT_FOUND"
    PRIMARY_PROVIDER_UNAVAILABLE = "PRIMARY_PROVIDER_UNAVAILABLE"
    PRIMARY_INVALID_RESPONSE = "PRIMARY_INVALID_RESPONSE"
    PRIMARY_EMPTY_RESPONSE = "PRIMARY_EMPTY_RESPONSE"
    PRIMARY_MALFORMED_JSON = "PRIMARY_MALFORMED_JSON"
    PRIMARY_SCHEMA_INVALID = "PRIMARY_SCHEMA_INVALID"
    PRIMARY_MODEL_IDENTITY_MISMATCH = "PRIMARY_MODEL_IDENTITY_MISMATCH"
    PRIMARY_INVALID_REQUEST_CONFIGURATION = "PRIMARY_INVALID_REQUEST_CONFIGURATION"
    PRIMARY_UNSUPPORTED_PARAMETER = "PRIMARY_UNSUPPORTED_PARAMETER"
    PRIMARY_CASE_REJECTED = "PRIMARY_CASE_REJECTED"
    PRIMARY_UNKNOWN_ERROR = "PRIMARY_UNKNOWN_ERROR"

    # Fallback attempt failures (no third provider exists).
    FALLBACK_TIMEOUT = "FALLBACK_TIMEOUT"
    FALLBACK_CONNECTION_ERROR = "FALLBACK_CONNECTION_ERROR"
    FALLBACK_RATE_LIMITED = "FALLBACK_RATE_LIMITED"
    FALLBACK_HTTP_ERROR = "FALLBACK_HTTP_ERROR"
    FALLBACK_AUTHENTICATION_FAILED = "FALLBACK_AUTHENTICATION_FAILED"
    FALLBACK_MODEL_NOT_FOUND = "FALLBACK_MODEL_NOT_FOUND"
    FALLBACK_PROVIDER_UNAVAILABLE = "FALLBACK_PROVIDER_UNAVAILABLE"
    FALLBACK_INVALID_RESPONSE = "FALLBACK_INVALID_RESPONSE"
    FALLBACK_EMPTY_RESPONSE = "FALLBACK_EMPTY_RESPONSE"
    FALLBACK_MALFORMED_JSON = "FALLBACK_MALFORMED_JSON"
    FALLBACK_SCHEMA_INVALID = "FALLBACK_SCHEMA_INVALID"
    FALLBACK_MODEL_IDENTITY_MISMATCH = "FALLBACK_MODEL_IDENTITY_MISMATCH"
    FALLBACK_CASE_REJECTED = "FALLBACK_CASE_REJECTED"
    FALLBACK_UNKNOWN_ERROR = "FALLBACK_UNKNOWN_ERROR"

    # Local configuration errors (fail closed, never fallback).
    CONFIG_INVALID = "CONFIG_INVALID"
    PROVIDER_NOT_CONFIGURED = "PROVIDER_NOT_CONFIGURED"

    # Both providers attempted, neither produced an accepted response.
    BOTH_UNAVAILABLE = "BOTH_UNAVAILABLE"


class SemanticRuntimeFallbackReason(str, Enum):
    """Why the fallback provider was entered.

    Every member is an EXECUTION failure of the primary attempt. Semantic
    disagreement has no member here, by construction.
    """

    NONE = "NONE"
    TIMEOUT = "TIMEOUT"
    DNS_ERROR = "DNS_ERROR"
    TLS_ERROR = "TLS_ERROR"
    CONNECTION_ERROR = "CONNECTION_ERROR"
    RATE_LIMITED = "RATE_LIMITED"
    HTTP_ERROR = "HTTP_ERROR"
    AUTHENTICATION_FAILED = "AUTHENTICATION_FAILED"
    MODEL_NOT_FOUND = "MODEL_NOT_FOUND"
    PROVIDER_UNAVAILABLE = "PROVIDER_UNAVAILABLE"
    EMPTY_RESPONSE = "EMPTY_RESPONSE"
    MALFORMED_JSON = "MALFORMED_JSON"
    SCHEMA_INVALID = "SCHEMA_INVALID"
    INVALID_RESPONSE = "INVALID_RESPONSE"
    MODEL_IDENTITY_MISMATCH = "MODEL_IDENTITY_MISMATCH"


class SemanticAttemptStatus(str, Enum):
    """Bounded outcome status of one provider attempt."""

    OK = "OK"
    TIMEOUT = "TIMEOUT"
    DNS_ERROR = "DNS_ERROR"
    TLS_ERROR = "TLS_ERROR"
    CONNECTION_ERROR = "CONNECTION_ERROR"
    RATE_LIMITED = "RATE_LIMITED"
    HTTP_ERROR = "HTTP_ERROR"
    AUTHENTICATION_FAILED = "AUTHENTICATION_FAILED"
    MODEL_NOT_FOUND = "MODEL_NOT_FOUND"
    PROVIDER_UNAVAILABLE = "PROVIDER_UNAVAILABLE"
    PROVIDER_NOT_CONFIGURED = "PROVIDER_NOT_CONFIGURED"
    INVALID_REQUEST_CONFIGURATION = "INVALID_REQUEST_CONFIGURATION"
    UNSUPPORTED_PARAMETER = "UNSUPPORTED_PARAMETER"
    EMPTY_RESPONSE = "EMPTY_RESPONSE"
    MALFORMED_JSON = "MALFORMED_JSON"
    SCHEMA_INVALID = "SCHEMA_INVALID"
    INVALID_RESPONSE = "INVALID_RESPONSE"
    MODEL_IDENTITY_MISMATCH = "MODEL_IDENTITY_MISMATCH"
    CASE_REJECTED = "CASE_REJECTED"
    UNKNOWN_ERROR = "UNKNOWN_ERROR"


# Transport error codes that map onto an attempt status. A code absent from
# this table is bounded to UNKNOWN_ERROR, which is not in the fallback
# allowlist and therefore fails closed.
_TRANSPORT_ERROR_TO_STATUS: dict[str, SemanticAttemptStatus] = {
    "TIMEOUT": SemanticAttemptStatus.TIMEOUT,
    "DNS_ERROR": SemanticAttemptStatus.DNS_ERROR,
    "TLS_ERROR": SemanticAttemptStatus.TLS_ERROR,
    "CONNECTION_ERROR": SemanticAttemptStatus.CONNECTION_ERROR,
    "RATE_LIMITED": SemanticAttemptStatus.RATE_LIMITED,
    "HTTP_ERROR": SemanticAttemptStatus.HTTP_ERROR,
    "AUTHENTICATION_FAILED": SemanticAttemptStatus.AUTHENTICATION_FAILED,
    "MODEL_NOT_FOUND": SemanticAttemptStatus.MODEL_NOT_FOUND,
    "PROVIDER_UNAVAILABLE": SemanticAttemptStatus.PROVIDER_UNAVAILABLE,
    "PROVIDER_NOT_CONFIGURED": SemanticAttemptStatus.PROVIDER_NOT_CONFIGURED,
    "INVALID_REQUEST_CONFIGURATION": SemanticAttemptStatus.INVALID_REQUEST_CONFIGURATION,
    "UNSUPPORTED_PARAMETER": SemanticAttemptStatus.UNSUPPORTED_PARAMETER,
    "INVALID_PROVIDER_RESPONSE": SemanticAttemptStatus.INVALID_RESPONSE,
    "RESPONSE_DECODE_ERROR": SemanticAttemptStatus.MALFORMED_JSON,
    "EMPTY_RESPONSE": SemanticAttemptStatus.EMPTY_RESPONSE,
    "MALFORMED_JSON": SemanticAttemptStatus.MALFORMED_JSON,
    "SCHEMA_INVALID": SemanticAttemptStatus.SCHEMA_INVALID,
    "MODEL_IDENTITY_MISMATCH": SemanticAttemptStatus.MODEL_IDENTITY_MISMATCH,
    "CASE_REJECTED": SemanticAttemptStatus.CASE_REJECTED,
}

_STATUS_TO_FALLBACK_REASON: dict[
    SemanticAttemptStatus, SemanticRuntimeFallbackReason
] = {
    SemanticAttemptStatus.TIMEOUT: SemanticRuntimeFallbackReason.TIMEOUT,
    SemanticAttemptStatus.DNS_ERROR: SemanticRuntimeFallbackReason.DNS_ERROR,
    SemanticAttemptStatus.TLS_ERROR: SemanticRuntimeFallbackReason.TLS_ERROR,
    SemanticAttemptStatus.CONNECTION_ERROR: SemanticRuntimeFallbackReason.CONNECTION_ERROR,
    SemanticAttemptStatus.RATE_LIMITED: SemanticRuntimeFallbackReason.RATE_LIMITED,
    SemanticAttemptStatus.HTTP_ERROR: SemanticRuntimeFallbackReason.HTTP_ERROR,
    SemanticAttemptStatus.AUTHENTICATION_FAILED: SemanticRuntimeFallbackReason.AUTHENTICATION_FAILED,
    SemanticAttemptStatus.MODEL_NOT_FOUND: SemanticRuntimeFallbackReason.MODEL_NOT_FOUND,
    SemanticAttemptStatus.PROVIDER_UNAVAILABLE: SemanticRuntimeFallbackReason.PROVIDER_UNAVAILABLE,
    SemanticAttemptStatus.EMPTY_RESPONSE: SemanticRuntimeFallbackReason.EMPTY_RESPONSE,
    SemanticAttemptStatus.MALFORMED_JSON: SemanticRuntimeFallbackReason.MALFORMED_JSON,
    SemanticAttemptStatus.SCHEMA_INVALID: SemanticRuntimeFallbackReason.SCHEMA_INVALID,
    SemanticAttemptStatus.INVALID_RESPONSE: SemanticRuntimeFallbackReason.INVALID_RESPONSE,
    SemanticAttemptStatus.MODEL_IDENTITY_MISMATCH: SemanticRuntimeFallbackReason.MODEL_IDENTITY_MISMATCH,
    # CASE_REJECTED is deliberately absent: it is not fallback-eligible, so it
    # must never appear as a fallback_reason.
}

_PRIMARY_STATUS_TO_ERROR_TYPE: dict[
    SemanticAttemptStatus, SemanticRuntimeErrorType
] = {
    SemanticAttemptStatus.TIMEOUT: SemanticRuntimeErrorType.PRIMARY_TIMEOUT,
    SemanticAttemptStatus.DNS_ERROR: SemanticRuntimeErrorType.PRIMARY_CONNECTION_ERROR,
    SemanticAttemptStatus.TLS_ERROR: SemanticRuntimeErrorType.PRIMARY_CONNECTION_ERROR,
    SemanticAttemptStatus.CONNECTION_ERROR: SemanticRuntimeErrorType.PRIMARY_CONNECTION_ERROR,
    SemanticAttemptStatus.RATE_LIMITED: SemanticRuntimeErrorType.PRIMARY_RATE_LIMITED,
    SemanticAttemptStatus.HTTP_ERROR: SemanticRuntimeErrorType.PRIMARY_HTTP_ERROR,
    SemanticAttemptStatus.AUTHENTICATION_FAILED: SemanticRuntimeErrorType.PRIMARY_AUTHENTICATION_FAILED,
    SemanticAttemptStatus.MODEL_NOT_FOUND: SemanticRuntimeErrorType.PRIMARY_MODEL_NOT_FOUND,
    SemanticAttemptStatus.PROVIDER_UNAVAILABLE: SemanticRuntimeErrorType.PRIMARY_PROVIDER_UNAVAILABLE,
    SemanticAttemptStatus.PROVIDER_NOT_CONFIGURED: SemanticRuntimeErrorType.PROVIDER_NOT_CONFIGURED,
    SemanticAttemptStatus.INVALID_REQUEST_CONFIGURATION: SemanticRuntimeErrorType.PRIMARY_INVALID_REQUEST_CONFIGURATION,
    SemanticAttemptStatus.UNSUPPORTED_PARAMETER: SemanticRuntimeErrorType.PRIMARY_UNSUPPORTED_PARAMETER,
    SemanticAttemptStatus.EMPTY_RESPONSE: SemanticRuntimeErrorType.PRIMARY_EMPTY_RESPONSE,
    SemanticAttemptStatus.MALFORMED_JSON: SemanticRuntimeErrorType.PRIMARY_MALFORMED_JSON,
    SemanticAttemptStatus.SCHEMA_INVALID: SemanticRuntimeErrorType.PRIMARY_SCHEMA_INVALID,
    SemanticAttemptStatus.INVALID_RESPONSE: SemanticRuntimeErrorType.PRIMARY_INVALID_RESPONSE,
    SemanticAttemptStatus.MODEL_IDENTITY_MISMATCH: SemanticRuntimeErrorType.PRIMARY_MODEL_IDENTITY_MISMATCH,
    SemanticAttemptStatus.CASE_REJECTED: SemanticRuntimeErrorType.PRIMARY_CASE_REJECTED,
    SemanticAttemptStatus.UNKNOWN_ERROR: SemanticRuntimeErrorType.PRIMARY_UNKNOWN_ERROR,
}

_FALLBACK_STATUS_TO_ERROR_TYPE: dict[
    SemanticAttemptStatus, SemanticRuntimeErrorType
] = {
    SemanticAttemptStatus.TIMEOUT: SemanticRuntimeErrorType.FALLBACK_TIMEOUT,
    SemanticAttemptStatus.DNS_ERROR: SemanticRuntimeErrorType.FALLBACK_CONNECTION_ERROR,
    SemanticAttemptStatus.TLS_ERROR: SemanticRuntimeErrorType.FALLBACK_CONNECTION_ERROR,
    SemanticAttemptStatus.CONNECTION_ERROR: SemanticRuntimeErrorType.FALLBACK_CONNECTION_ERROR,
    SemanticAttemptStatus.RATE_LIMITED: SemanticRuntimeErrorType.FALLBACK_RATE_LIMITED,
    SemanticAttemptStatus.HTTP_ERROR: SemanticRuntimeErrorType.FALLBACK_HTTP_ERROR,
    SemanticAttemptStatus.AUTHENTICATION_FAILED: SemanticRuntimeErrorType.FALLBACK_AUTHENTICATION_FAILED,
    SemanticAttemptStatus.MODEL_NOT_FOUND: SemanticRuntimeErrorType.FALLBACK_MODEL_NOT_FOUND,
    SemanticAttemptStatus.PROVIDER_UNAVAILABLE: SemanticRuntimeErrorType.FALLBACK_PROVIDER_UNAVAILABLE,
    SemanticAttemptStatus.PROVIDER_NOT_CONFIGURED: SemanticRuntimeErrorType.PROVIDER_NOT_CONFIGURED,
    SemanticAttemptStatus.INVALID_REQUEST_CONFIGURATION: SemanticRuntimeErrorType.FALLBACK_INVALID_RESPONSE,
    SemanticAttemptStatus.UNSUPPORTED_PARAMETER: SemanticRuntimeErrorType.FALLBACK_INVALID_RESPONSE,
    SemanticAttemptStatus.EMPTY_RESPONSE: SemanticRuntimeErrorType.FALLBACK_EMPTY_RESPONSE,
    SemanticAttemptStatus.MALFORMED_JSON: SemanticRuntimeErrorType.FALLBACK_MALFORMED_JSON,
    SemanticAttemptStatus.SCHEMA_INVALID: SemanticRuntimeErrorType.FALLBACK_SCHEMA_INVALID,
    SemanticAttemptStatus.INVALID_RESPONSE: SemanticRuntimeErrorType.FALLBACK_INVALID_RESPONSE,
    SemanticAttemptStatus.MODEL_IDENTITY_MISMATCH: SemanticRuntimeErrorType.FALLBACK_MODEL_IDENTITY_MISMATCH,
    SemanticAttemptStatus.CASE_REJECTED: SemanticRuntimeErrorType.FALLBACK_CASE_REJECTED,
    SemanticAttemptStatus.UNKNOWN_ERROR: SemanticRuntimeErrorType.FALLBACK_UNKNOWN_ERROR,
}


# ---------------------------------------------------------------------------
# Per-attempt provenance
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class SemanticAttempt:
    """One provider attempt, with its own bounded outcome.

    Recorded for every attempt the runtime actually made, successful or not,
    so a both-provider failure still explains itself. Carries no raw body, no
    exception text, and no credential.
    """

    provider: str
    model: str
    status: SemanticAttemptStatus
    latency_ms: float

    def __post_init__(self) -> None:
        if not isinstance(self.provider, str) or not self.provider:
            raise ValueError("provider must be a non-empty string")
        if not isinstance(self.model, str) or not self.model:
            raise ValueError("model must be a non-empty string")
        if not isinstance(self.status, SemanticAttemptStatus):
            raise TypeError(
                f"status must be SemanticAttemptStatus, "
                f"got {type(self.status).__name__}"
            )
        if isinstance(self.latency_ms, bool) or not isinstance(
            self.latency_ms, (int, float)
        ):
            raise TypeError(
                f"latency_ms must be a number, got {type(self.latency_ms).__name__}"
            )
        if not math.isfinite(self.latency_ms):
            raise ValueError(f"latency_ms must be finite, got {self.latency_ms}")
        if self.latency_ms < 0:
            raise ValueError(f"latency_ms must be >= 0, got {self.latency_ms}")

    def to_dict(self) -> dict[str, Any]:
        """Return a safe dictionary representation."""
        return {
            "provider": self.provider,
            "model": self.model,
            "status": self.status.value,
            "latency_ms": self.latency_ms,
        }


# ---------------------------------------------------------------------------
# Runtime result contract
# ---------------------------------------------------------------------------


def _require_str_tuple(value: Any, field_name: str) -> None:
    """Raise unless ``value`` is a ``tuple`` of ``str``.

    Shared by ``SemanticRuntimeResult``'s three attribute-list fields, so a
    caller cannot construct a "valid" result whose ``to_dict()`` (or any other
    consumer) would only discover the wrong shape later.
    """
    if not isinstance(value, tuple):
        raise TypeError(f"{field_name} must be a tuple, got {type(value).__name__}")
    for i, item in enumerate(value):
        if not isinstance(item, str):
            raise TypeError(
                f"{field_name}[{i}] must be str, got {type(item).__name__}"
            )


@dataclass(frozen=True)
class SemanticRuntimeResult:
    """Result of one semantic runtime evaluation.

    ``actual_provider`` / ``actual_model`` name the provider that produced the
    accepted semantic response. On ANY final failure both are ``None``: no
    provider produced a usable answer, so naming one would be a false
    provenance claim.
    """

    # Request metadata.
    case_id: str
    target_mpn: str
    target_description: str
    candidate_title: str
    candidate_mpn_field: str | None
    candidate_sku: str | None
    candidate_specs: str | None
    evidence_source: str

    # Requested (pinned) primary route.
    requested_primary_provider: str
    requested_primary_model: str

    # Per-attempt provenance, in call order.
    attempts: tuple[SemanticAttempt, ...]

    # Routing outcome.
    fallback_used: bool
    fallback_reason: SemanticRuntimeFallbackReason | None

    # Provenance of the accepted answer (None on any final failure).
    actual_provider: str | None
    actual_model: str | None

    # Semantic response fields (None/empty on failure).
    decision: SemanticDecision | None
    confidence: ConfidenceLevel | None
    matched_attributes: tuple[str, ...]
    conflicting_attributes: tuple[str, ...]
    missing_critical_attributes: tuple[str, ...]
    reason_code: str | None

    # Bounded final failure classification (None on success).
    error_type: SemanticRuntimeErrorType | None

    prompt_version: str = SEMANTIC_PROMPT_VERSION

    def __post_init__(self) -> None:
        if not isinstance(self.attempts, tuple):
            raise TypeError(
                f"attempts must be a tuple, got {type(self.attempts).__name__}"
            )
        for i, attempt in enumerate(self.attempts):
            if not isinstance(attempt, SemanticAttempt):
                raise TypeError(
                    f"attempts[{i}] must be SemanticAttempt, "
                    f"got {type(attempt).__name__}"
                )

        # -- exact field types, checked before any of it is trusted below --
        #
        # A caller must not be able to construct decision="MATCH" (a plain
        # string) and have it succeed here only for to_dict() - or anything
        # else that trusts `.value` - to crash later, somewhere harder to
        # diagnose.
        if self.decision is not None and not isinstance(self.decision, SemanticDecision):
            raise TypeError(
                f"decision must be SemanticDecision or None, "
                f"got {type(self.decision).__name__}"
            )
        if self.confidence is not None and not isinstance(
            self.confidence, ConfidenceLevel
        ):
            raise TypeError(
                f"confidence must be ConfidenceLevel or None, "
                f"got {type(self.confidence).__name__}"
            )
        if self.error_type is not None and not isinstance(
            self.error_type, SemanticRuntimeErrorType
        ):
            raise TypeError(
                f"error_type must be SemanticRuntimeErrorType or None, "
                f"got {type(self.error_type).__name__}"
            )
        if self.fallback_reason is not None and not isinstance(
            self.fallback_reason, SemanticRuntimeFallbackReason
        ):
            raise TypeError(
                f"fallback_reason must be SemanticRuntimeFallbackReason or "
                f"None, got {type(self.fallback_reason).__name__}"
            )
        if not isinstance(self.fallback_used, bool):
            raise TypeError(
                f"fallback_used must be bool, got {type(self.fallback_used).__name__}"
            )
        _require_str_tuple(self.matched_attributes, "matched_attributes")
        _require_str_tuple(self.conflicting_attributes, "conflicting_attributes")
        _require_str_tuple(
            self.missing_critical_attributes, "missing_critical_attributes"
        )

        # -- the pinned route is not merely requested, it is the ONLY route --
        if self.requested_primary_provider != PRIMARY_PROVIDER:
            raise ValueError(
                "requested_primary_provider must equal the pinned primary "
                f"provider {PRIMARY_PROVIDER!r}, got "
                f"{self.requested_primary_provider!r}"
            )
        if self.requested_primary_model != PRIMARY_MODEL:
            raise ValueError(
                "requested_primary_model must equal the pinned primary model "
                f"{PRIMARY_MODEL!r}, got {self.requested_primary_model!r}"
            )
        if self.prompt_version != SEMANTIC_PROMPT_VERSION:
            raise ValueError(
                f"prompt_version must equal {SEMANTIC_PROMPT_VERSION!r}, "
                f"got {self.prompt_version!r}"
            )

        # -- attempt count: exactly one or exactly two, never zero or three+ --
        attempt_count = len(self.attempts)
        if attempt_count not in (1, 2):
            raise ValueError(
                f"a result must carry exactly one or two attempts, got "
                f"{attempt_count}; there is a primary and at most one "
                "fallback, no more, and a result cannot exist with none"
            )

        # -- shape of the attempts themselves, by count --
        if attempt_count == 1:
            attempt = self.attempts[0]
            if self.fallback_used:
                raise ValueError(
                    "fallback_used must be False when only one attempt was made"
                )
            if self.fallback_reason is not None:
                raise ValueError(
                    "fallback_reason must be None when only one attempt was made"
                )
            if attempt.provider != PRIMARY_PROVIDER or attempt.model != PRIMARY_MODEL:
                raise ValueError(
                    "the sole attempt of a one-attempt result must be the "
                    f"pinned primary ({PRIMARY_PROVIDER}/{PRIMARY_MODEL}), got "
                    f"{attempt.provider}/{attempt.model}"
                )
            if (
                attempt.status is not SemanticAttemptStatus.OK
                and attempt.status.value in PRIMARY_FALLBACK_ELIGIBLE_ERRORS
            ):
                raise ValueError(
                    f"a one-attempt result cannot have a primary status of "
                    f"{attempt.status.value!r}: this status is fallback-"
                    "eligible, so the real runtime always makes a second "
                    "(fallback) attempt for it - a one-attempt result "
                    "claiming this status is an impossible routing history"
                )
        else:  # attempt_count == 2
            first, second = self.attempts
            if not self.fallback_used:
                raise ValueError(
                    "fallback_used must be True when two attempts were made"
                )
            if self.fallback_reason is None:
                raise ValueError(
                    "fallback_reason must be set when two attempts were made"
                )
            if first.provider != PRIMARY_PROVIDER or first.model != PRIMARY_MODEL:
                raise ValueError(
                    "the first attempt of a two-attempt result must be the "
                    f"pinned primary ({PRIMARY_PROVIDER}/{PRIMARY_MODEL}), got "
                    f"{first.provider}/{first.model}"
                )
            if second.provider != FALLBACK_PROVIDER or second.model != FALLBACK_MODEL:
                raise ValueError(
                    "the second attempt of a two-attempt result must be the "
                    f"pinned fallback ({FALLBACK_PROVIDER}/{FALLBACK_MODEL}), "
                    f"got {second.provider}/{second.model}"
                )
            if first.status is SemanticAttemptStatus.OK:
                raise ValueError(
                    "a fallback was attempted, so the first (primary) attempt "
                    "cannot have status OK - a successful primary is final "
                    "after exactly one attempt"
                )
            if first.status.value not in PRIMARY_FALLBACK_ELIGIBLE_ERRORS:
                raise ValueError(
                    f"the first attempt's status {first.status.value!r} is not "
                    "fallback-eligible; a fallback must not have been "
                    "attempted for this failure"
                )
            expected_reason = _STATUS_TO_FALLBACK_REASON[first.status]
            if self.fallback_reason is not expected_reason:
                raise ValueError(
                    f"fallback_reason must be {expected_reason!r}, derived "
                    f"from the first attempt's status {first.status.value!r}, "
                    f"got {self.fallback_reason!r}"
                )

        # -- decision and failure are mutually exclusive --
        if self.decision is not None and self.error_type is not None:
            raise ValueError(
                "a result carries either a decision or an error_type, not both"
            )
        if self.decision is None and self.error_type is None:
            raise ValueError("a result without a decision must carry an error_type")

        if self.decision is not None:
            # -- success: provenance, the OK attempt, and a real response --
            if not self.actual_provider or not self.actual_model:
                raise ValueError(
                    "a successful result must name the provider and model that "
                    "produced the accepted semantic response"
                )
            if attempt_count == 1:
                if self.attempts[0].status is not SemanticAttemptStatus.OK:
                    raise ValueError(
                        "a one-attempt success must have an OK primary attempt"
                    )
                if (
                    self.actual_provider != PRIMARY_PROVIDER
                    or self.actual_model != PRIMARY_MODEL
                ):
                    raise ValueError(
                        "a one-attempt success must be attributed to the "
                        f"pinned primary ({PRIMARY_PROVIDER}/{PRIMARY_MODEL}), "
                        f"got {self.actual_provider}/{self.actual_model}"
                    )
            else:
                if self.attempts[1].status is not SemanticAttemptStatus.OK:
                    raise ValueError(
                        "a two-attempt success must have an OK fallback attempt"
                    )
                if (
                    self.actual_provider != FALLBACK_PROVIDER
                    or self.actual_model != FALLBACK_MODEL
                ):
                    raise ValueError(
                        "a two-attempt success must be attributed to the "
                        f"pinned fallback ({FALLBACK_PROVIDER}/{FALLBACK_MODEL}), "
                        f"got {self.actual_provider}/{self.actual_model}"
                    )
            if self.confidence is None:
                raise ValueError("a successful result must carry a confidence")
            if not isinstance(self.reason_code, str) or not self.reason_code.strip():
                raise ValueError(
                    "a successful result must carry a non-empty reason_code "
                    "(a str with non-whitespace content), "
                    f"got {type(self.reason_code).__name__} {self.reason_code!r}"
                )
        else:
            # -- failure: no provenance, no OK attempt, empty response fields --
            if self.actual_provider is not None or self.actual_model is not None:
                raise ValueError(
                    "a failed result must not name an actual provider or model; "
                    "no provider produced an accepted semantic response"
                )
            if any(a.status is SemanticAttemptStatus.OK for a in self.attempts):
                raise ValueError(
                    "a failed result must not contain an OK attempt; an OK "
                    "attempt is by definition a success"
                )
            if self.confidence is not None:
                raise ValueError("a failed result must not carry a confidence")
            if self.reason_code is not None:
                raise ValueError("a failed result must not carry a reason_code")
            if self.matched_attributes != ():
                raise ValueError("a failed result must have empty matched_attributes")
            if self.conflicting_attributes != ():
                raise ValueError(
                    "a failed result must have empty conflicting_attributes"
                )
            if self.missing_critical_attributes != ():
                raise ValueError(
                    "a failed result must have empty missing_critical_attributes"
                )

            # -- error_type is mechanically bound to attempt provenance --
            #
            # A failure cannot claim an error_type that does not match what
            # actually happened: e.g. the sole/last attempt failed with
            # TIMEOUT, but error_type claims PRIMARY_MODEL_NOT_FOUND. Both
            # lookup tables are complete over every non-OK status (proved by
            # tests/semantic/test_runtime.py), so this is a direct index, not
            # a `.get()` with a silently-wrong default.
            if attempt_count == 1:
                expected_error_type = _PRIMARY_STATUS_TO_ERROR_TYPE[
                    self.attempts[0].status
                ]
                if self.error_type is not expected_error_type:
                    raise ValueError(
                        f"error_type must be {expected_error_type!r}, derived "
                        "from the sole attempt's status "
                        f"{self.attempts[0].status.value!r}, got "
                        f"{self.error_type!r}"
                    )
            else:
                expected_error_type = _FALLBACK_STATUS_TO_ERROR_TYPE[
                    self.attempts[1].status
                ]
                if self.error_type is not expected_error_type:
                    raise ValueError(
                        f"error_type must be {expected_error_type!r}, derived "
                        "from the second attempt's status "
                        f"{self.attempts[1].status.value!r}, got "
                        f"{self.error_type!r}"
                    )

    @property
    def attempt_count(self) -> int:
        """Number of provider attempts actually made."""
        return len(self.attempts)

    def to_dict(self) -> dict[str, Any]:
        """Return a safe dictionary representation for serialization.

        Contains no raw response, no provider body, no exception text, no API
        key, and no chain-of-thought.
        """
        return {
            "case_id": self.case_id,
            "target_mpn": self.target_mpn,
            "target_description": self.target_description,
            "candidate_title": self.candidate_title,
            "candidate_mpn_field": self.candidate_mpn_field,
            "candidate_sku": self.candidate_sku,
            "candidate_specs": self.candidate_specs,
            "evidence_source": self.evidence_source,
            "prompt_version": self.prompt_version,
            "requested_primary_provider": self.requested_primary_provider,
            "requested_primary_model": self.requested_primary_model,
            "attempts": [a.to_dict() for a in self.attempts],
            "attempt_count": self.attempt_count,
            "fallback_used": self.fallback_used,
            "fallback_reason": (
                self.fallback_reason.value if self.fallback_reason else None
            ),
            "actual_provider": self.actual_provider,
            "actual_model": self.actual_model,
            "decision": self.decision.value if self.decision else None,
            "confidence": self.confidence.value if self.confidence else None,
            "matched_attributes": self.matched_attributes,
            "conflicting_attributes": self.conflicting_attributes,
            "missing_critical_attributes": self.missing_critical_attributes,
            "reason_code": self.reason_code,
            "error_type": self.error_type.value if self.error_type else None,
        }


# ---------------------------------------------------------------------------
# Runtime configuration
# ---------------------------------------------------------------------------


class SemanticRuntimeConfigError(ValueError):
    """Raised when a configuration deviates from the qualified route."""


@dataclass(frozen=True)
class SemanticRuntimeConfig:
    """Configuration for the semantic runtime.

    The route fields exist for compatibility and for explicit, readable call
    sites. They are NOT tunable: validation rejects any value other than the
    qualified constants, before any transport is built or called. Only
    ``request_timeout_seconds`` is genuinely configurable.

    No API key is ever stored in a field; credentials stay in the server
    environment and are read by the transport adapter.
    """

    primary_provider: str = PRIMARY_PROVIDER
    primary_model: str = PRIMARY_MODEL

    fallback_provider: str = FALLBACK_PROVIDER
    fallback_model: str = FALLBACK_MODEL

    temperature: float = SEMANTIC_TEMPERATURE
    max_tokens: int = SEMANTIC_MAX_TOKENS

    request_timeout_seconds: float = DEFAULT_REQUEST_TIMEOUT_SECONDS

    @classmethod
    def from_environment(cls) -> SemanticRuntimeConfig:
        """Build the qualified configuration, timeout from the environment."""
        return cls(request_timeout_seconds=_default_timeout_seconds())


def validate_runtime_config(config: SemanticRuntimeConfig) -> None:
    """Reject any configuration that is not the qualified production route.

    Raises:
        TypeError: If ``config`` is not a ``SemanticRuntimeConfig``.
        SemanticRuntimeConfigError: If the route, temperature, or max_tokens
            deviates from the qualified constants, or the timeout is out of
            bounds.
    """
    if not isinstance(config, SemanticRuntimeConfig):
        raise TypeError(
            f"config must be SemanticRuntimeConfig, got {type(config).__name__}"
        )

    # max_tokens must be the exact qualified integer, not a truthy equal
    # (bool(True) == 1, and 32768.0 == 32768).
    if isinstance(config.max_tokens, bool) or not isinstance(config.max_tokens, int):
        raise SemanticRuntimeConfigError(
            f"max_tokens must be the int {SEMANTIC_MAX_TOKENS}, "
            f"got {type(config.max_tokens).__name__}"
        )

    # temperature must be the exact qualified float, not merely a numerically
    # equal value of another type. Python equality makes False == 0 == 0.0
    # and True == 1 == 1.0, so a bare `!=` check below would silently accept
    # temperature=False or temperature=0 as "the qualified 0.0". This is not
    # the formally qualified request shape: the qualification run sent a JSON
    # body with `"temperature": 0.0`, and only a Python float serializes to
    # that.
    if type(config.temperature) is not float:
        raise SemanticRuntimeConfigError(
            f"temperature must be the exact float {SEMANTIC_TEMPERATURE!r}, "
            f"got {type(config.temperature).__name__} {config.temperature!r}; "
            "bool and int are not accepted here even where numerically equal"
        )

    pinned = (
        ("primary_provider", config.primary_provider, PRIMARY_PROVIDER),
        ("primary_model", config.primary_model, PRIMARY_MODEL),
        ("fallback_provider", config.fallback_provider, FALLBACK_PROVIDER),
        ("fallback_model", config.fallback_model, FALLBACK_MODEL),
        ("temperature", config.temperature, SEMANTIC_TEMPERATURE),
        ("max_tokens", config.max_tokens, SEMANTIC_MAX_TOKENS),
    )
    for name, actual, qualified in pinned:
        if actual != qualified:
            raise SemanticRuntimeConfigError(
                f"{name} is pinned to the qualified value {qualified!r}, "
                f"got {actual!r}; the production semantic route is fixed by "
                "formal qualification and cannot be substituted by a caller"
            )

    timeout = config.request_timeout_seconds
    if isinstance(timeout, bool) or not isinstance(timeout, (int, float)):
        raise SemanticRuntimeConfigError(
            f"request_timeout_seconds must be a number, "
            f"got {type(timeout).__name__}"
        )
    # NaN compares False against every relational operator, so a bare
    # `timeout <= 0` / `timeout > MAX` check would silently let NaN through.
    # +inf and -inf are already caught by the bounds below, but are rejected
    # here too, explicitly, so "non-finite is rejected" does not depend on
    # where MAX_REQUEST_TIMEOUT_SECONDS happens to be set.
    if not math.isfinite(timeout):
        raise SemanticRuntimeConfigError(
            f"request_timeout_seconds must be finite, got {timeout}"
        )
    if timeout <= 0:
        raise SemanticRuntimeConfigError(
            f"request_timeout_seconds must be > 0, got {timeout}"
        )
    if timeout > MAX_REQUEST_TIMEOUT_SECONDS:
        raise SemanticRuntimeConfigError(
            f"request_timeout_seconds must be <= {MAX_REQUEST_TIMEOUT_SECONDS}, "
            f"got {timeout}"
        )


# ---------------------------------------------------------------------------
# Transport outcome classification (neutral, duck-typed)
# ---------------------------------------------------------------------------
#
# The runtime deliberately does not import the transport adapter's classes at
# module import time. A transport outcome is classified structurally:
#
#   failure -> carries ``error_type``
#   success -> carries ``raw_output``
#
# This keeps the production package import free of the adapter (and of the
# urllib it uses), and lets any conforming transport be injected.


def _is_transport_failure(outcome: Any) -> bool:
    """True when a transport outcome is a failure (carries ``error_type``)."""
    return hasattr(outcome, "error_type")


def _attempt_status_for_error(error_type: Any) -> SemanticAttemptStatus:
    """Map a transport error code onto a bounded attempt status.

    An unrecognised code is bounded to ``UNKNOWN_ERROR``, which is not in the
    fallback allowlist and therefore fails closed.
    """
    if not isinstance(error_type, str):
        return SemanticAttemptStatus.UNKNOWN_ERROR
    return _TRANSPORT_ERROR_TO_STATUS.get(
        error_type, SemanticAttemptStatus.UNKNOWN_ERROR
    )


# ---------------------------------------------------------------------------
# Production semantic runtime
# ---------------------------------------------------------------------------


class SemanticRuntime:
    """Production semantic runtime with pinned primary/fallback routing.

    The ONE central abstraction for semantic evaluation. Callers use this;
    never a transport directly.

    Routing rules:

    1. Call PRIMARY once.
    2. A valid primary decision (MATCH / NO_MATCH / UNCERTAIN) is FINAL -
       exactly one call, zero fallback calls.
    3. A primary failure named in ``PRIMARY_FALLBACK_ELIGIBLE_ERRORS`` calls
       the FALLBACK exactly once.
    4. Any other primary failure fails closed after one attempt.
    5. A fallback failure is final - there is no third provider.

    Programming defects are never swallowed: an unexpected exception raised by
    a transport propagates to the caller and never causes fallback.
    """

    def __init__(
        self,
        config: SemanticRuntimeConfig | None = None,
        primary_transport: Any | None = None,
        fallback_transport: Any | None = None,
    ):
        """Initialize the runtime.

        Args:
            config: Runtime configuration. Defaults to the qualified route.
                Validated before any transport is built or called.
            primary_transport: Injected primary transport (tests, or a caller
                that already holds one). Built from the environment if omitted.
            fallback_transport: Injected fallback transport.

        Raises:
            SemanticRuntimeConfigError: If the configuration is not the
                qualified production route.
        """
        self._config = (
            config if config is not None else SemanticRuntimeConfig.from_environment()
        )

        # Validate BEFORE constructing or calling any transport.
        validate_runtime_config(self._config)

        self._primary_transport = (
            primary_transport
            if primary_transport is not None
            else self._build_transport(self._config.primary_provider, "primary")
        )
        self._fallback_transport = (
            fallback_transport
            if fallback_transport is not None
            else self._build_transport(self._config.fallback_provider, "fallback")
        )

    @property
    def config(self) -> SemanticRuntimeConfig:
        """The validated, qualified configuration in use."""
        return self._config

    def _build_transport(self, provider: str, role: str) -> Any | None:
        """Build a live transport for ``provider``, or None if unconfigured.

        The transport adapter is imported lazily here, never at module import
        time, so importing ``product_intelligence.semantic`` stays free of
        urllib and any other network client library. The adapter is the
        neutral ``product_intelligence.semantic.transport`` module - this
        never reaches into the evaluation harness.
        """
        from product_intelligence.semantic.transport import (
            get_openai_transport_for_provider,
        )

        try:
            return get_openai_transport_for_provider(
                provider,
                request_timeout_seconds=self._config.request_timeout_seconds,
            )
        except ValueError:
            # Missing local provider configuration. Fails closed at call time
            # with PROVIDER_NOT_CONFIGURED; the raw exception is never logged.
            logger.warning(
                "Semantic %s provider is not configured; the runtime fails closed",
                role,
            )
            return None

    # -- public API ---------------------------------------------------------

    def evaluate(
        self,
        case_id: str,
        target_mpn: str,
        target_description: str,
        candidate_title: str,
        candidate_mpn_field: str | None = None,
        candidate_sku: str | None = None,
        candidate_specs: str | None = None,
        evidence_source: str = "UNKNOWN",
    ) -> SemanticRuntimeResult:
        """Evaluate semantic match for one candidate.

        Returns:
            A ``SemanticRuntimeResult`` with per-attempt provenance. The
            runtime returns a result for every model or provider failure; it
            does not swallow programming defects.
        """
        request_fields = {
            "case_id": case_id,
            "target_mpn": target_mpn,
            "target_description": target_description,
            "candidate_title": candidate_title,
            "candidate_mpn_field": candidate_mpn_field,
            "candidate_sku": candidate_sku,
            "candidate_specs": candidate_specs,
            "evidence_source": evidence_source,
        }

        prompt = build_prompt(
            case_id=case_id,
            target_mpn=target_mpn,
            target_description=target_description,
            candidate_title=candidate_title,
            candidate_mpn_field=candidate_mpn_field,
            candidate_sku=candidate_sku,
            candidate_specs=candidate_specs,
            evidence_source=evidence_source,
        )

        # -- primary attempt ------------------------------------------------
        primary_response, primary_attempt = self._attempt(
            transport=self._primary_transport,
            provider=self._config.primary_provider,
            model=self._config.primary_model,
            prompt=prompt,
        )

        if primary_attempt.status is SemanticAttemptStatus.OK:
            assert primary_response is not None  # OK implies a parsed response
            return self._success(
                request_fields=request_fields,
                attempts=(primary_attempt,),
                fallback_used=False,
                fallback_reason=None,
                provider=self._config.primary_provider,
                model=self._config.primary_model,
                response=primary_response,
            )

        # -- fallback eligibility (EXPLICIT ALLOWLIST) ----------------------
        if primary_attempt.status.value not in PRIMARY_FALLBACK_ELIGIBLE_ERRORS:
            logger.warning(
                "Semantic primary attempt failed with %s for case %s; "
                "not fallback eligible, failing closed",
                primary_attempt.status.value,
                case_id,
            )
            return self._failure(
                request_fields=request_fields,
                attempts=(primary_attempt,),
                fallback_used=False,
                fallback_reason=None,
                error_type=_PRIMARY_STATUS_TO_ERROR_TYPE.get(
                    primary_attempt.status,
                    SemanticRuntimeErrorType.PRIMARY_UNKNOWN_ERROR,
                ),
            )

        fallback_reason = _STATUS_TO_FALLBACK_REASON[primary_attempt.status]

        logger.warning(
            "Semantic primary attempt failed with %s for case %s; entering fallback",
            primary_attempt.status.value,
            case_id,
        )

        # -- fallback attempt (exactly once) --------------------------------
        fallback_response, fallback_attempt = self._attempt(
            transport=self._fallback_transport,
            provider=self._config.fallback_provider,
            model=self._config.fallback_model,
            prompt=prompt,
        )
        attempts = (primary_attempt, fallback_attempt)

        if fallback_attempt.status is SemanticAttemptStatus.OK:
            assert fallback_response is not None
            return self._success(
                request_fields=request_fields,
                attempts=attempts,
                fallback_used=True,
                fallback_reason=fallback_reason,
                provider=self._config.fallback_provider,
                model=self._config.fallback_model,
                response=fallback_response,
            )

        logger.warning(
            "Semantic fallback attempt failed with %s for case %s; "
            "no further provider exists",
            fallback_attempt.status.value,
            case_id,
        )
        return self._failure(
            request_fields=request_fields,
            attempts=attempts,
            fallback_used=True,
            fallback_reason=fallback_reason,
            error_type=_FALLBACK_STATUS_TO_ERROR_TYPE.get(
                fallback_attempt.status, SemanticRuntimeErrorType.BOTH_UNAVAILABLE
            ),
        )

    # -- one attempt --------------------------------------------------------

    def _attempt(
        self,
        transport: Any | None,
        provider: str,
        model: str,
        prompt: Any,
    ) -> tuple[SemanticMatchResponse | None, SemanticAttempt]:
        """Make one provider attempt and classify its bounded outcome.

        Latency is measured around the whole attempt, so a failed attempt also
        retains a safe latency figure.

        Any exception the transport raises, rather than the normalized failure
        it is contracted to return, is a programming defect and propagates.
        The runtime does not catch broad exceptions here: ``complete`` already
        owns network and provider normalization.
        """
        if transport is None:
            return None, SemanticAttempt(
                provider=provider,
                model=model,
                status=SemanticAttemptStatus.PROVIDER_NOT_CONFIGURED,
                latency_ms=0.0,
            )

        started = time.perf_counter()
        outcome = transport.complete(
            system_prompt=prompt.system_prompt,
            user_prompt=prompt.user_prompt,
            model=model,
            temperature=self._config.temperature,
            max_tokens=self._config.max_tokens,
        )
        latency_ms = (time.perf_counter() - started) * 1000.0

        if _is_transport_failure(outcome):
            return None, SemanticAttempt(
                provider=provider,
                model=model,
                status=_attempt_status_for_error(outcome.error_type),
                latency_ms=latency_ms,
            )

        response, status = self._interpret(outcome, model)
        return response, SemanticAttempt(
            provider=provider,
            model=model,
            status=status,
            latency_ms=latency_ms,
        )

    def _interpret(
        self,
        outcome: Any,
        model: str,
    ) -> tuple[SemanticMatchResponse | None, SemanticAttemptStatus]:
        """Verify model identity, then parse and validate the raw output.

        Model identity is mandatory and exact. A provider that reports a
        different model, or reports no model at all, has not proven it ran the
        qualified model - both are ``MODEL_IDENTITY_MISMATCH``. A response is
        never accepted merely because ``provider_reported_model`` is ``None``.
        """
        reported = getattr(outcome, "provider_reported_model", None)
        if reported is None:
            logger.warning(
                "Provider reported no model identity; identity cannot be proven"
            )
            return None, SemanticAttemptStatus.MODEL_IDENTITY_MISMATCH
        if reported != model:
            logger.warning("Provider reported a model that is not the requested model")
            return None, SemanticAttemptStatus.MODEL_IDENTITY_MISMATCH

        raw_output = getattr(outcome, "raw_output", None)
        if not isinstance(raw_output, str) or not raw_output.strip():
            return None, SemanticAttemptStatus.EMPTY_RESPONSE

        try:
            parsed = parse_raw_output(raw_output)
        except RawOutputParseError:
            # Bounded: no exception text is logged or retained.
            return None, SemanticAttemptStatus.MALFORMED_JSON

        try:
            validated = validate_response(parsed)
        except (TypeError, ValueError):
            return None, SemanticAttemptStatus.SCHEMA_INVALID

        return validated, SemanticAttemptStatus.OK

    # -- result builders ----------------------------------------------------

    def _success(
        self,
        request_fields: dict[str, Any],
        attempts: tuple[SemanticAttempt, ...],
        fallback_used: bool,
        fallback_reason: SemanticRuntimeFallbackReason | None,
        provider: str,
        model: str,
        response: SemanticMatchResponse,
    ) -> SemanticRuntimeResult:
        """Build a successful result naming the provider that answered."""
        return SemanticRuntimeResult(
            **request_fields,
            requested_primary_provider=self._config.primary_provider,
            requested_primary_model=self._config.primary_model,
            attempts=attempts,
            fallback_used=fallback_used,
            fallback_reason=fallback_reason,
            actual_provider=provider,
            actual_model=model,
            decision=response.decision,
            confidence=response.confidence,
            matched_attributes=response.matched_attributes,
            conflicting_attributes=response.conflicting_attributes,
            missing_critical_attributes=response.missing_critical_attributes,
            reason_code=response.reason_code,
            error_type=None,
        )

    def _failure(
        self,
        request_fields: dict[str, Any],
        attempts: tuple[SemanticAttempt, ...],
        fallback_used: bool,
        fallback_reason: SemanticRuntimeFallbackReason | None,
        error_type: SemanticRuntimeErrorType,
    ) -> SemanticRuntimeResult:
        """Build a failed result. No provenance is claimed for a failure."""
        return SemanticRuntimeResult(
            **request_fields,
            requested_primary_provider=self._config.primary_provider,
            requested_primary_model=self._config.primary_model,
            attempts=attempts,
            fallback_used=fallback_used,
            fallback_reason=fallback_reason,
            actual_provider=None,
            actual_model=None,
            decision=None,
            confidence=None,
            matched_attributes=(),
            conflicting_attributes=(),
            missing_critical_attributes=(),
            reason_code=None,
            error_type=error_type,
        )


# ---------------------------------------------------------------------------
# Default runtime instance
# ---------------------------------------------------------------------------


_default_runtime: SemanticRuntime | None = None


def get_default_runtime() -> SemanticRuntime:
    """Return the process-wide runtime, built on first call."""
    global _default_runtime
    if _default_runtime is None:
        _default_runtime = SemanticRuntime()
    return _default_runtime


def reset_default_runtime() -> None:
    """Drop the process-wide runtime (tests)."""
    global _default_runtime
    _default_runtime = None
