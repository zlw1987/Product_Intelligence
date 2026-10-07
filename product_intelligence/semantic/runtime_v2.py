"""The production Semantic V2 runtime (S2-C).

The V2 runtime executes the FINAL Semantic V2 contract
(``semantic.contract_v2`` prompt + ``research.semantic_v2`` input/output
contracts) against the currently frozen qualified route identities:

    PRIMARY   amax / qwen3.8-27b
    FALLBACK  vllm-262k / Qwen3.6-27B-262K
    temperature 0.0, max_tokens 32768

These route pins are V2 CONTRACT data (they belong to the V2 semantic
contract adapter/runtime, NOT to the universal persistence envelope), and
they are the V2 QUALIFICATION CANDIDATES: the identical route identities
the V1 runtime is qualified on, carried as separate V2-owned constants so
a future V3 qualification may pin or move the V2 route without touching
the V1 contract.

Central invariant (unchanged from the frozen FU3A runtime): FALLBACK ON
EXECUTION FAILURE ONLY. A valid primary response (MATCH / NO_MATCH /
UNCERTAIN, at any confidence) is FINAL — exactly one primary call, zero
fallback calls. Low confidence, a conservative reason code, or semantic
disagreement never triggers a second model.

QUALIFICATION BOUNDARY (S2-C): the V2 route is NOT qualified for the new
V2 contract. ``V2_AUTHORITY_QUALIFIED`` is the explicit marker of that
boundary: V2 outputs are evidence/provenance awaiting Qualification V3,
and no production authority code path treats a V2 MATCH/HIGH as
pricing-authoritative. The marker is drift-pinned (and asserted False) by
architecture tests.

The bounded transport-provenance vocabularies and the routing tables are
mirrors of the frozen FU3A runtime (drift-pinned by tests), exactly as the
V1 persistence adapter's mirrors are. Import purity: this module imports
no Django and no network client at module level; the live transport is
resolved lazily inside transport construction (``semantic.transport``).

Programming defects are never converted into a transport failure: an
unexpected exception raised by an injected transport propagates and never
causes fallback. No raw provider body, no exception text, no API key, and
no chain-of-thought ever reach a ``SemanticRuntimeResultV2``.
"""

from __future__ import annotations

import logging
import math
import os
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Final

from product_intelligence.research.semantic_v2 import (
    SemanticMatchCaseV2,
    SemanticMatchResponseV2,
    parse_semantic_response_v2,
    validate_semantic_response_v2,
)
from product_intelligence.semantic.contract_v2 import (
    SEMANTIC_PROMPT_VERSION_V2,
    build_semantic_prompt_v2,
)
from product_intelligence.semantic.runtime import (
    DEFAULT_REQUEST_TIMEOUT_SECONDS,
    MAX_REQUEST_TIMEOUT_SECONDS,
    PRIMARY_FALLBACK_ELIGIBLE_ERRORS,
    PRIMARY_NON_FALLBACK_ERRORS,
    SemanticAttempt,
    SemanticAttemptStatus,
    SemanticRuntimeConfigError,
    SemanticRuntimeErrorType,
    SemanticRuntimeFallbackReason,
)

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# V2 qualified route candidates (pinned; V2-contract-owned, not envelope)
# ---------------------------------------------------------------------------


PRIMARY_PROVIDER_V2: Final[str] = "amax"
PRIMARY_MODEL_V2: Final[str] = "qwen3.8-27b"

FALLBACK_PROVIDER_V2: Final[str] = "vllm-262k"
FALLBACK_MODEL_V2: Final[str] = "Qwen3.6-27B-262K"

SEMANTIC_TEMPERATURE_V2: Final[float] = 0.0
SEMANTIC_MAX_TOKENS_V2: Final[int] = 32768

#: The explicit S2-C qualification-boundary marker. The V2 route is NOT
#: qualified for the new V2 contract: Qualification V3 happens AFTER S2-C,
#: and no production authority code path treats V2 MATCH/HIGH as
#: pricing-authoritative while this marker is False. Drift-pinned by the
#: V2 persistence adapter and asserted by architecture tests.
V2_AUTHORITY_QUALIFIED: Final[bool] = False

#: Fallback eligibility: EXECUTION failures only (the frozen allowlist is
#: transport-world data, shared with the V1 runtime by identity).
PRIMARY_FALLBACK_ELIGIBLE_ERRORS_V2: Final[frozenset[str]] = (
    PRIMARY_FALLBACK_ELIGIBLE_ERRORS
)
PRIMARY_NON_FALLBACK_ERRORS_V2: Final[frozenset[str]] = (
    PRIMARY_NON_FALLBACK_ERRORS
)


def _default_timeout_seconds_v2() -> float:
    """Read the configured request timeout from the environment.

    Mirrors the frozen V1 runtime discipline: absence is not an error (the
    qualified default is used); presence with an unreadable or non-finite
    value fails closed.
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
        ) from None
    if not math.isfinite(value):
        raise SemanticRuntimeConfigError(
            "PI_SEMANTIC_REQUEST_TIMEOUT_SECONDS must be finite, got "
            f"{raw!r}"
        )
    return value


# ---------------------------------------------------------------------------
# Bounded routing tables (V2 mirrors of the frozen FU3A runtime; drift-
# pinned by tests — the routing discipline is the transport world's, not
# contract-specific)
# ---------------------------------------------------------------------------


_V2_TRANSPORT_ERROR_TO_STATUS: Final[dict[str, SemanticAttemptStatus]] = {
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
    "INVALID_REQUEST_CONFIGURATION": (
        SemanticAttemptStatus.INVALID_REQUEST_CONFIGURATION
    ),
    "UNSUPPORTED_PARAMETER": SemanticAttemptStatus.UNSUPPORTED_PARAMETER,
    "INVALID_PROVIDER_RESPONSE": SemanticAttemptStatus.INVALID_RESPONSE,
    "RESPONSE_DECODE_ERROR": SemanticAttemptStatus.MALFORMED_JSON,
    "EMPTY_RESPONSE": SemanticAttemptStatus.EMPTY_RESPONSE,
    "MALFORMED_JSON": SemanticAttemptStatus.MALFORMED_JSON,
    "SCHEMA_INVALID": SemanticAttemptStatus.SCHEMA_INVALID,
    "MODEL_IDENTITY_MISMATCH": SemanticAttemptStatus.MODEL_IDENTITY_MISMATCH,
    "CASE_REJECTED": SemanticAttemptStatus.CASE_REJECTED,
}

_V2_STATUS_TO_FALLBACK_REASON: Final[
    dict[SemanticAttemptStatus, SemanticRuntimeFallbackReason]
] = {
    SemanticAttemptStatus.TIMEOUT: SemanticRuntimeFallbackReason.TIMEOUT,
    SemanticAttemptStatus.DNS_ERROR: SemanticRuntimeFallbackReason.DNS_ERROR,
    SemanticAttemptStatus.TLS_ERROR: SemanticRuntimeFallbackReason.TLS_ERROR,
    SemanticAttemptStatus.CONNECTION_ERROR: (
        SemanticRuntimeFallbackReason.CONNECTION_ERROR
    ),
    SemanticAttemptStatus.RATE_LIMITED: SemanticRuntimeFallbackReason.RATE_LIMITED,
    SemanticAttemptStatus.HTTP_ERROR: SemanticRuntimeFallbackReason.HTTP_ERROR,
    SemanticAttemptStatus.AUTHENTICATION_FAILED: (
        SemanticRuntimeFallbackReason.AUTHENTICATION_FAILED
    ),
    SemanticAttemptStatus.MODEL_NOT_FOUND: (
        SemanticRuntimeFallbackReason.MODEL_NOT_FOUND
    ),
    SemanticAttemptStatus.PROVIDER_UNAVAILABLE: (
        SemanticRuntimeFallbackReason.PROVIDER_UNAVAILABLE
    ),
    SemanticAttemptStatus.EMPTY_RESPONSE: (
        SemanticRuntimeFallbackReason.EMPTY_RESPONSE
    ),
    SemanticAttemptStatus.MALFORMED_JSON: (
        SemanticRuntimeFallbackReason.MALFORMED_JSON
    ),
    SemanticAttemptStatus.SCHEMA_INVALID: (
        SemanticRuntimeFallbackReason.SCHEMA_INVALID
    ),
    SemanticAttemptStatus.INVALID_RESPONSE: (
        SemanticRuntimeFallbackReason.INVALID_RESPONSE
    ),
    SemanticAttemptStatus.MODEL_IDENTITY_MISMATCH: (
        SemanticRuntimeFallbackReason.MODEL_IDENTITY_MISMATCH
    ),
}

_V2_PRIMARY_STATUS_TO_ERROR_TYPE: Final[
    dict[SemanticAttemptStatus, SemanticRuntimeErrorType]
] = {
    SemanticAttemptStatus.TIMEOUT: SemanticRuntimeErrorType.PRIMARY_TIMEOUT,
    SemanticAttemptStatus.DNS_ERROR: (
        SemanticRuntimeErrorType.PRIMARY_CONNECTION_ERROR
    ),
    SemanticAttemptStatus.TLS_ERROR: (
        SemanticRuntimeErrorType.PRIMARY_CONNECTION_ERROR
    ),
    SemanticAttemptStatus.CONNECTION_ERROR: (
        SemanticRuntimeErrorType.PRIMARY_CONNECTION_ERROR
    ),
    SemanticAttemptStatus.RATE_LIMITED: (
        SemanticRuntimeErrorType.PRIMARY_RATE_LIMITED
    ),
    SemanticAttemptStatus.HTTP_ERROR: (
        SemanticRuntimeErrorType.PRIMARY_HTTP_ERROR
    ),
    SemanticAttemptStatus.AUTHENTICATION_FAILED: (
        SemanticRuntimeErrorType.PRIMARY_AUTHENTICATION_FAILED
    ),
    SemanticAttemptStatus.MODEL_NOT_FOUND: (
        SemanticRuntimeErrorType.PRIMARY_MODEL_NOT_FOUND
    ),
    SemanticAttemptStatus.PROVIDER_UNAVAILABLE: (
        SemanticRuntimeErrorType.PRIMARY_PROVIDER_UNAVAILABLE
    ),
    SemanticAttemptStatus.PROVIDER_NOT_CONFIGURED: (
        SemanticRuntimeErrorType.PROVIDER_NOT_CONFIGURED
    ),
    SemanticAttemptStatus.INVALID_REQUEST_CONFIGURATION: (
        SemanticRuntimeErrorType.PRIMARY_INVALID_REQUEST_CONFIGURATION
    ),
    SemanticAttemptStatus.UNSUPPORTED_PARAMETER: (
        SemanticRuntimeErrorType.PRIMARY_UNSUPPORTED_PARAMETER
    ),
    SemanticAttemptStatus.EMPTY_RESPONSE: (
        SemanticRuntimeErrorType.PRIMARY_EMPTY_RESPONSE
    ),
    SemanticAttemptStatus.MALFORMED_JSON: (
        SemanticRuntimeErrorType.PRIMARY_MALFORMED_JSON
    ),
    SemanticAttemptStatus.SCHEMA_INVALID: (
        SemanticRuntimeErrorType.PRIMARY_SCHEMA_INVALID
    ),
    SemanticAttemptStatus.INVALID_RESPONSE: (
        SemanticRuntimeErrorType.PRIMARY_INVALID_RESPONSE
    ),
    SemanticAttemptStatus.MODEL_IDENTITY_MISMATCH: (
        SemanticRuntimeErrorType.PRIMARY_MODEL_IDENTITY_MISMATCH
    ),
    SemanticAttemptStatus.CASE_REJECTED: (
        SemanticRuntimeErrorType.PRIMARY_CASE_REJECTED
    ),
    SemanticAttemptStatus.UNKNOWN_ERROR: (
        SemanticRuntimeErrorType.PRIMARY_UNKNOWN_ERROR
    ),
}

_V2_FALLBACK_STATUS_TO_ERROR_TYPE: Final[
    dict[SemanticAttemptStatus, SemanticRuntimeErrorType]
] = {
    SemanticAttemptStatus.TIMEOUT: SemanticRuntimeErrorType.FALLBACK_TIMEOUT,
    SemanticAttemptStatus.DNS_ERROR: (
        SemanticRuntimeErrorType.FALLBACK_CONNECTION_ERROR
    ),
    SemanticAttemptStatus.TLS_ERROR: (
        SemanticRuntimeErrorType.FALLBACK_CONNECTION_ERROR
    ),
    SemanticAttemptStatus.CONNECTION_ERROR: (
        SemanticRuntimeErrorType.FALLBACK_CONNECTION_ERROR
    ),
    SemanticAttemptStatus.RATE_LIMITED: (
        SemanticRuntimeErrorType.FALLBACK_RATE_LIMITED
    ),
    SemanticAttemptStatus.HTTP_ERROR: SemanticRuntimeErrorType.FALLBACK_HTTP_ERROR,
    SemanticAttemptStatus.AUTHENTICATION_FAILED: (
        SemanticRuntimeErrorType.FALLBACK_AUTHENTICATION_FAILED
    ),
    SemanticAttemptStatus.MODEL_NOT_FOUND: (
        SemanticRuntimeErrorType.FALLBACK_MODEL_NOT_FOUND
    ),
    SemanticAttemptStatus.PROVIDER_UNAVAILABLE: (
        SemanticRuntimeErrorType.FALLBACK_PROVIDER_UNAVAILABLE
    ),
    SemanticAttemptStatus.PROVIDER_NOT_CONFIGURED: (
        SemanticRuntimeErrorType.PROVIDER_NOT_CONFIGURED
    ),
    SemanticAttemptStatus.INVALID_REQUEST_CONFIGURATION: (
        SemanticRuntimeErrorType.FALLBACK_INVALID_RESPONSE
    ),
    SemanticAttemptStatus.UNSUPPORTED_PARAMETER: (
        SemanticRuntimeErrorType.FALLBACK_INVALID_RESPONSE
    ),
    SemanticAttemptStatus.EMPTY_RESPONSE: (
        SemanticRuntimeErrorType.FALLBACK_EMPTY_RESPONSE
    ),
    SemanticAttemptStatus.MALFORMED_JSON: (
        SemanticRuntimeErrorType.FALLBACK_MALFORMED_JSON
    ),
    SemanticAttemptStatus.SCHEMA_INVALID: (
        SemanticRuntimeErrorType.FALLBACK_SCHEMA_INVALID
    ),
    SemanticAttemptStatus.INVALID_RESPONSE: (
        SemanticRuntimeErrorType.FALLBACK_INVALID_RESPONSE
    ),
    SemanticAttemptStatus.MODEL_IDENTITY_MISMATCH: (
        SemanticRuntimeErrorType.FALLBACK_MODEL_IDENTITY_MISMATCH
    ),
    SemanticAttemptStatus.CASE_REJECTED: (
        SemanticRuntimeErrorType.FALLBACK_CASE_REJECTED
    ),
    SemanticAttemptStatus.UNKNOWN_ERROR: (
        SemanticRuntimeErrorType.FALLBACK_UNKNOWN_ERROR
    ),
}


def _utc_now_iso() -> str:
    """A bounded ISO-8601 UTC instant (microsecond precision, 'Z').

    The grammar is the one the persistence record validates; the runtime
    is the only place an instant is produced for a V2 record.
    """
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%f") + "Z"


# ---------------------------------------------------------------------------
# Runtime configuration (the V2 route is pinned, not caller-configurable)
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class SemanticRuntimeConfigV2:
    """Configuration for the Semantic V2 runtime.

    The route fields exist for explicit, readable call sites. They are NOT
    tunable: validation rejects any value other than the V2 pinned
    constants, before any transport is built or called. Only
    ``request_timeout_seconds`` is genuinely configurable (the same
    environment variable the V1 runtime reads).

    No API key is ever stored in a field; credentials stay in the server
    environment and are read by the transport adapter.
    """

    primary_provider: str = PRIMARY_PROVIDER_V2
    primary_model: str = PRIMARY_MODEL_V2

    fallback_provider: str = FALLBACK_PROVIDER_V2
    fallback_model: str = FALLBACK_MODEL_V2

    temperature: float = SEMANTIC_TEMPERATURE_V2
    max_tokens: int = SEMANTIC_MAX_TOKENS_V2

    request_timeout_seconds: float = DEFAULT_REQUEST_TIMEOUT_SECONDS

    @classmethod
    def from_environment(cls) -> "SemanticRuntimeConfigV2":
        """Build the V2 configuration, timeout from the environment."""
        return cls(request_timeout_seconds=_default_timeout_seconds_v2())


def validate_runtime_config_v2(config: SemanticRuntimeConfigV2) -> None:
    """Reject any configuration that is not the V2 pinned route.

    Raises:
        TypeError: If ``config`` is not a ``SemanticRuntimeConfigV2``.
        SemanticRuntimeConfigError: If the route, temperature, or
            max_tokens deviate from the V2 pinned constants, or the
            timeout is out of bounds.
    """
    if not isinstance(config, SemanticRuntimeConfigV2):
        raise TypeError(
            f"config must be SemanticRuntimeConfigV2, "
            f"got {type(config).__name__}"
        )

    if isinstance(config.max_tokens, bool) or not isinstance(
        config.max_tokens, int
    ):
        raise SemanticRuntimeConfigError(
            f"max_tokens must be the int {SEMANTIC_MAX_TOKENS_V2}, "
            f"got {type(config.max_tokens).__name__}"
        )

    if type(config.temperature) is not float:
        raise SemanticRuntimeConfigError(
            f"temperature must be the exact float {SEMANTIC_TEMPERATURE_V2!r}, "
            f"got {type(config.temperature).__name__} {config.temperature!r}; "
            "bool and int are not accepted here even where numerically equal"
        )

    pinned = (
        ("primary_provider", config.primary_provider, PRIMARY_PROVIDER_V2),
        ("primary_model", config.primary_model, PRIMARY_MODEL_V2),
        ("fallback_provider", config.fallback_provider, FALLBACK_PROVIDER_V2),
        ("fallback_model", config.fallback_model, FALLBACK_MODEL_V2),
        ("temperature", config.temperature, SEMANTIC_TEMPERATURE_V2),
        ("max_tokens", config.max_tokens, SEMANTIC_MAX_TOKENS_V2),
    )
    for name, actual, qualified in pinned:
        if actual != qualified:
            raise SemanticRuntimeConfigError(
                f"{name} is pinned to the V2 value {qualified!r}, "
                f"got {actual!r}; the V2 semantic route is fixed by the "
                "frozen route identities and cannot be substituted by a "
                "caller"
            )

    timeout = config.request_timeout_seconds
    if isinstance(timeout, bool) or not isinstance(timeout, (int, float)):
        raise SemanticRuntimeConfigError(
            f"request_timeout_seconds must be a number, "
            f"got {type(timeout).__name__}"
        )
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
# V2 runtime result contract
# ---------------------------------------------------------------------------

_TIMESTAMP_PATTERN_V2 = (
    r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(\.\d{1,6})?Z$"
)


def _validate_v2_instant(value: str | None, path: str) -> None:
    import re

    if not isinstance(value, str) or not re.match(_TIMESTAMP_PATTERN_V2, value):
        raise ValueError(
            f"{path}: must be an ISO-8601 UTC instant ending in 'Z', "
            f"got {value!r}"
        )


@dataclass(frozen=True)
class SemanticRuntimeResultV2:
    """Result of one Semantic V2 runtime evaluation.

    Carries the EXACT V2 input (``case``), the per-attempt provenance on
    the V2 pinned route, the routing outcome (fallback on execution
    failure only), the provenance of the accepted answer (None on any
    final failure), the strict structured V2 response (or the bounded
    failure classification), and the bounded evaluation instants.

    ``actual_provider`` / ``actual_model`` name the provider that produced
    the accepted V2 response. On ANY final failure both are ``None``.

    No raw response, no provider body, no exception text, no API key, and
    no chain-of-thought is carried.
    """

    case: SemanticMatchCaseV2

    requested_primary_provider: str
    requested_primary_model: str

    attempts: tuple[SemanticAttempt, ...]

    fallback_used: bool
    fallback_reason: SemanticRuntimeFallbackReason | None

    actual_provider: str | None
    actual_model: str | None

    response: SemanticMatchResponseV2 | None
    error_type: SemanticRuntimeErrorType | None

    evaluation_started_at: str
    evaluation_finished_at: str

    prompt_version: str = SEMANTIC_PROMPT_VERSION_V2

    def __post_init__(self) -> None:
        if not isinstance(self.case, SemanticMatchCaseV2):
            raise TypeError(
                "case must be SemanticMatchCaseV2, "
                f"got {type(self.case).__name__}"
            )
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

        if self.requested_primary_provider != PRIMARY_PROVIDER_V2:
            raise ValueError(
                "requested_primary_provider must equal the V2 pinned "
                f"primary provider {PRIMARY_PROVIDER_V2!r}, got "
                f"{self.requested_primary_provider!r}"
            )
        if self.requested_primary_model != PRIMARY_MODEL_V2:
            raise ValueError(
                "requested_primary_model must equal the V2 pinned primary "
                f"model {PRIMARY_MODEL_V2!r}, got {self.requested_primary_model!r}"
            )
        if self.prompt_version != SEMANTIC_PROMPT_VERSION_V2:
            raise ValueError(
                f"prompt_version must equal {SEMANTIC_PROMPT_VERSION_V2!r}, "
                f"got {self.prompt_version!r}"
            )

        if not isinstance(self.fallback_used, bool):
            raise TypeError(
                "fallback_used must be bool, "
                f"got {type(self.fallback_used).__name__}"
            )
        if (
            self.fallback_reason is not None
            and not isinstance(self.fallback_reason, SemanticRuntimeFallbackReason)
        ):
            raise TypeError(
                "fallback_reason must be SemanticRuntimeFallbackReason or "
                f"None, got {type(self.fallback_reason).__name__}"
            )
        if (
            self.error_type is not None
            and not isinstance(self.error_type, SemanticRuntimeErrorType)
        ):
            raise TypeError(
                "error_type must be SemanticRuntimeErrorType or None, "
                f"got {type(self.error_type).__name__}"
            )
        if (
            self.response is not None
            and not isinstance(self.response, SemanticMatchResponseV2)
        ):
            raise TypeError(
                "response must be SemanticMatchResponseV2 or None, "
                f"got {type(self.response).__name__}"
            )
        _validate_v2_instant(self.evaluation_started_at, "evaluation_started_at")
        _validate_v2_instant(
            self.evaluation_finished_at, "evaluation_finished_at"
        )

        attempt_count = len(self.attempts)
        if attempt_count not in (1, 2):
            raise ValueError(
                f"a V2 result must carry exactly one or two attempts, got "
                f"{attempt_count}; there is a primary and at most one "
                "fallback, no more, and a result cannot exist with none"
            )

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
            if (
                attempt.provider != PRIMARY_PROVIDER_V2
                or attempt.model != PRIMARY_MODEL_V2
            ):
                raise ValueError(
                    "the sole attempt of a one-attempt V2 result must be the "
                    f"pinned primary ({PRIMARY_PROVIDER_V2}/{PRIMARY_MODEL_V2}), "
                    f"got {attempt.provider}/{attempt.model}"
                )
            if (
                attempt.status is not SemanticAttemptStatus.OK
                and attempt.status.value in PRIMARY_FALLBACK_ELIGIBLE_ERRORS_V2
            ):
                raise ValueError(
                    f"a one-attempt V2 result cannot have a primary status of "
                    f"{attempt.status.value!r}: this status is fallback-"
                    "eligible, so the real runtime always makes a second "
                    "(fallback) attempt for it"
                )
        else:
            first, second = self.attempts
            if not self.fallback_used:
                raise ValueError(
                    "fallback_used must be True when two attempts were made"
                )
            if self.fallback_reason is None:
                raise ValueError(
                    "fallback_reason must be set when two attempts were made"
                )
            if (
                first.provider != PRIMARY_PROVIDER_V2
                or first.model != PRIMARY_MODEL_V2
            ):
                raise ValueError(
                    "the first attempt of a two-attempt V2 result must be the "
                    f"pinned primary ({PRIMARY_PROVIDER_V2}/{PRIMARY_MODEL_V2}), "
                    f"got {first.provider}/{first.model}"
                )
            if (
                second.provider != FALLBACK_PROVIDER_V2
                or second.model != FALLBACK_MODEL_V2
            ):
                raise ValueError(
                    "the second attempt of a two-attempt V2 result must be the "
                    f"pinned fallback ({FALLBACK_PROVIDER_V2}/{FALLBACK_MODEL_V2}), "
                    f"got {second.provider}/{second.model}"
                )
            if first.status is SemanticAttemptStatus.OK:
                raise ValueError(
                    "a fallback was attempted, so the first (primary) attempt "
                    "cannot have status OK - a successful primary is final "
                    "after exactly one attempt"
                )
            if first.status.value not in PRIMARY_FALLBACK_ELIGIBLE_ERRORS_V2:
                raise ValueError(
                    f"the first attempt's status {first.status.value!r} is not "
                    "fallback-eligible; a fallback must not have been "
                    "attempted for this failure"
                )
            expected_reason = _V2_STATUS_TO_FALLBACK_REASON[first.status]
            if self.fallback_reason is not expected_reason:
                raise ValueError(
                    f"fallback_reason must be {expected_reason!r}, derived "
                    f"from the first attempt's status {first.status.value!r}, "
                    f"got {self.fallback_reason!r}"
                )

        # -- response and failure are mutually exclusive --
        if self.response is not None and self.error_type is not None:
            raise ValueError(
                "a V2 result carries either a response or an error_type, not both"
            )
        if self.response is None and self.error_type is None:
            raise ValueError(
                "a V2 result without a response must carry an error_type"
            )

        if self.response is not None:
            if not self.actual_provider or not self.actual_model:
                raise ValueError(
                    "a successful V2 result must name the provider and model "
                    "that produced the accepted V2 response"
                )
            if attempt_count == 1:
                if self.attempts[0].status is not SemanticAttemptStatus.OK:
                    raise ValueError(
                        "a one-attempt success must have an OK primary attempt"
                    )
                if (
                    self.actual_provider != PRIMARY_PROVIDER_V2
                    or self.actual_model != PRIMARY_MODEL_V2
                ):
                    raise ValueError(
                        "a one-attempt V2 success must be attributed to the "
                        f"pinned primary ({PRIMARY_PROVIDER_V2}/{PRIMARY_MODEL_V2}), "
                        f"got {self.actual_provider}/{self.actual_model}"
                    )
            else:
                if self.attempts[1].status is not SemanticAttemptStatus.OK:
                    raise ValueError(
                        "a two-attempt V2 success must have an OK fallback attempt"
                    )
                if (
                    self.actual_provider != FALLBACK_PROVIDER_V2
                    or self.actual_model != FALLBACK_MODEL_V2
                ):
                    raise ValueError(
                        "a two-attempt V2 success must be attributed to the "
                        f"pinned fallback ({FALLBACK_PROVIDER_V2}/{FALLBACK_MODEL_V2}), "
                        f"got {self.actual_provider}/{self.actual_model}"
                    )
        else:
            if self.actual_provider is not None or self.actual_model is not None:
                raise ValueError(
                    "a failed V2 result must not name an actual provider or "
                    "model; no provider produced an accepted V2 response"
                )
            if any(
                a.status is SemanticAttemptStatus.OK for a in self.attempts
            ):
                raise ValueError(
                    "a failed V2 result must not contain an OK attempt; an OK "
                    "attempt is by definition a success"
                )
            if attempt_count == 1:
                expected_error_type = _V2_PRIMARY_STATUS_TO_ERROR_TYPE[
                    self.attempts[0].status
                ]
                if self.error_type is not expected_error_type:
                    raise ValueError(
                        f"error_type must be {expected_error_type!r}, derived "
                        "from the sole attempt's status "
                        f"{self.attempts[0].status.value!r}, got {self.error_type!r}"
                    )
            else:
                expected_error_type = _V2_FALLBACK_STATUS_TO_ERROR_TYPE[
                    self.attempts[1].status
                ]
                if self.error_type is not expected_error_type:
                    raise ValueError(
                        f"error_type must be {expected_error_type!r}, derived "
                        "from the second attempt's status "
                        f"{self.attempts[1].status.value!r}, got {self.error_type!r}"
                    )


# ---------------------------------------------------------------------------
# Production Semantic V2 runtime
# ---------------------------------------------------------------------------


class SemanticRuntimeV2:
    """Production Semantic V2 runtime with pinned primary/fallback routing.

    Routing rules (identical discipline to the frozen FU3A runtime):

    1. Call PRIMARY (V2 pinned route) once.
    2. A valid primary V2 decision (MATCH / NO_MATCH / UNCERTAIN, at any
       confidence) is FINAL - exactly one call, zero fallback calls.
    3. A primary failure named in the fallback-eligible allowlist calls
       the FALLBACK (V2 pinned route) exactly once.
    4. Any other primary failure fails closed after one attempt.
    5. A fallback failure is final - there is no third provider.

    Programming defects are never swallowed: an unexpected exception
    raised by a transport propagates to the caller and never causes
    fallback.
    """

    def __init__(
        self,
        config: SemanticRuntimeConfigV2 | None = None,
        primary_transport: Any | None = None,
        fallback_transport: Any | None = None,
    ) -> None:
        self._config = (
            config
            if config is not None
            else SemanticRuntimeConfigV2.from_environment()
        )
        # Validate BEFORE constructing or calling any transport.
        validate_runtime_config_v2(self._config)

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
    def config(self) -> SemanticRuntimeConfigV2:
        """The validated, V2-pinned configuration in use."""
        return self._config

    def _build_transport(self, provider: str, role: str) -> Any | None:
        """Build a live transport for ``provider``, or None if unconfigured.

        The transport adapter is imported lazily here, never at module
        import time (the production semantic package stays free of the
        network client at import). A missing provider configuration fails
        closed at call time with PROVIDER_NOT_CONFIGURED.
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
            logger.warning(
                "Semantic V2 %s provider is not configured; the runtime "
                "fails closed",
                role,
            )
            return None

    # -- public API ---------------------------------------------------------

    def evaluate(self, case: SemanticMatchCaseV2) -> SemanticRuntimeResultV2:
        """Evaluate commercial semantic equivalence for one V2 case.

        Returns a ``SemanticRuntimeResultV2`` with per-attempt provenance
        for every outcome: an accepted strict structured V2 response, or
        the bounded final failure classification. The runtime returns a
        result for every model or provider failure; it does not swallow
        programming defects.
        """
        if not isinstance(case, SemanticMatchCaseV2):
            raise TypeError(
                "case must be SemanticMatchCaseV2, "
                f"got {type(case).__name__}"
            )
        prompt = build_semantic_prompt_v2(case)
        started_at = _utc_now_iso()

        # -- primary attempt ------------------------------------------------
        primary_response, primary_attempt = self._attempt(
            transport=self._primary_transport,
            provider=self._config.primary_provider,
            model=self._config.primary_model,
            prompt=prompt,
        )
        if primary_attempt.status is SemanticAttemptStatus.OK:
            assert primary_response is not None  # OK implies a validated response
            return self._success(
                case=case,
                attempts=(primary_attempt,),
                fallback_used=False,
                fallback_reason=None,
                provider=self._config.primary_provider,
                model=self._config.primary_model,
                response=primary_response,
                started_at=started_at,
            )

        # -- fallback eligibility (EXECUTION FAILURE ONLY) -------------------
        if primary_attempt.status.value not in PRIMARY_FALLBACK_ELIGIBLE_ERRORS_V2:
            logger.warning(
                "Semantic V2 primary attempt failed with %s for case %s; "
                "not fallback eligible, failing closed",
                primary_attempt.status.value,
                case.case_id,
            )
            return self._failure(
                case=case,
                attempts=(primary_attempt,),
                fallback_used=False,
                fallback_reason=None,
                error_type=_V2_PRIMARY_STATUS_TO_ERROR_TYPE.get(
                    primary_attempt.status,
                    SemanticRuntimeErrorType.PRIMARY_UNKNOWN_ERROR,
                ),
                started_at=started_at,
            )

        fallback_reason = _V2_STATUS_TO_FALLBACK_REASON[primary_attempt.status]
        logger.warning(
            "Semantic V2 primary attempt failed with %s for case %s; "
            "entering fallback",
            primary_attempt.status.value,
            case.case_id,
        )

        # -- fallback attempt (exactly once) ---------------------------------
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
                case=case,
                attempts=attempts,
                fallback_used=True,
                fallback_reason=fallback_reason,
                provider=self._config.fallback_provider,
                model=self._config.fallback_model,
                response=fallback_response,
                started_at=started_at,
            )

        logger.warning(
            "Semantic V2 fallback attempt failed with %s for case %s; no "
            "further provider exists",
            fallback_attempt.status.value,
            case.case_id,
        )
        return self._failure(
            case=case,
            attempts=attempts,
            fallback_used=True,
            fallback_reason=fallback_reason,
            error_type=_V2_FALLBACK_STATUS_TO_ERROR_TYPE.get(
                fallback_attempt.status,
                SemanticRuntimeErrorType.BOTH_UNAVAILABLE,
            ),
            started_at=started_at,
        )

    # -- one attempt --------------------------------------------------------

    def _attempt(
        self,
        transport: Any | None,
        provider: str,
        model: str,
        prompt: Any,
    ) -> tuple[SemanticMatchResponseV2 | None, SemanticAttempt]:
        """Make one provider attempt and classify its bounded outcome.

        Any exception the transport raises, rather than the normalized
        failure it is contracted to return, is a programming defect and
        propagates.
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

        if hasattr(outcome, "error_type"):
            return None, SemanticAttempt(
                provider=provider,
                model=model,
                status=self._attempt_status_for_error(outcome.error_type),
                latency_ms=latency_ms,
            )

        response, status = self._interpret(outcome, model)
        return response, SemanticAttempt(
            provider=provider,
            model=model,
            status=status,
            latency_ms=latency_ms,
        )

    def _attempt_status_for_error(self, error_type: Any) -> SemanticAttemptStatus:
        """Map a transport error code onto a bounded attempt status.

        An unrecognised code is bounded to ``UNKNOWN_ERROR``, which is not
        in the fallback allowlist and therefore fails closed.
        """
        if not isinstance(error_type, str):
            return SemanticAttemptStatus.UNKNOWN_ERROR
        return _V2_TRANSPORT_ERROR_TO_STATUS.get(
            error_type, SemanticAttemptStatus.UNKNOWN_ERROR
        )

    def _interpret(
        self,
        outcome: Any,
        model: str,
    ) -> tuple[SemanticMatchResponseV2 | None, SemanticAttemptStatus]:
        """Verify model identity, then parse and strictly validate the raw
        V2 output.

        Model identity is mandatory and exact: a provider that reports a
        different model, or no model at all, has not proven it ran the
        pinned model - ``MODEL_IDENTITY_MISMATCH``. The V2 output must be
        the exact strict structured response (unknown enums, extra
        fields, incoherent decision/conflict combinations all fail
        closed as ``SCHEMA_INVALID``; malformed JSON fails as
        ``MALFORMED_JSON``).
        """
        reported = getattr(outcome, "provider_reported_model", None)
        if reported is None:
            logger.warning(
                "Provider reported no model identity; identity cannot be proven"
            )
            return None, SemanticAttemptStatus.MODEL_IDENTITY_MISMATCH
        if reported != model:
            logger.warning(
                "Provider reported a model that is not the requested model"
            )
            return None, SemanticAttemptStatus.MODEL_IDENTITY_MISMATCH

        raw_output = getattr(outcome, "raw_output", None)
        if not isinstance(raw_output, str) or not raw_output.strip():
            return None, SemanticAttemptStatus.EMPTY_RESPONSE

        try:
            parsed = parse_semantic_response_v2(raw_output)
        except Exception:
            # Bounded: no exception text is logged or retained.
            return None, SemanticAttemptStatus.MALFORMED_JSON

        try:
            validated = validate_semantic_response_v2(parsed)
        except (TypeError, ValueError):
            return None, SemanticAttemptStatus.SCHEMA_INVALID

        return validated, SemanticAttemptStatus.OK

    # -- result builders ----------------------------------------------------

    def _success(
        self,
        *,
        case: SemanticMatchCaseV2,
        attempts: tuple[SemanticAttempt, ...],
        fallback_used: bool,
        fallback_reason: SemanticRuntimeFallbackReason | None,
        provider: str,
        model: str,
        response: SemanticMatchResponseV2,
        started_at: str,
    ) -> SemanticRuntimeResultV2:
        return SemanticRuntimeResultV2(
            case=case,
            requested_primary_provider=self._config.primary_provider,
            requested_primary_model=self._config.primary_model,
            attempts=attempts,
            fallback_used=fallback_used,
            fallback_reason=fallback_reason,
            actual_provider=provider,
            actual_model=model,
            response=response,
            error_type=None,
            evaluation_started_at=started_at,
            evaluation_finished_at=_utc_now_iso(),
        )

    def _failure(
        self,
        *,
        case: SemanticMatchCaseV2,
        attempts: tuple[SemanticAttempt, ...],
        fallback_used: bool,
        fallback_reason: SemanticRuntimeFallbackReason | None,
        error_type: SemanticRuntimeErrorType,
        started_at: str,
    ) -> SemanticRuntimeResultV2:
        return SemanticRuntimeResultV2(
            case=case,
            requested_primary_provider=self._config.primary_provider,
            requested_primary_model=self._config.primary_model,
            attempts=attempts,
            fallback_used=fallback_used,
            fallback_reason=fallback_reason,
            actual_provider=None,
            actual_model=None,
            response=None,
            error_type=error_type,
            evaluation_started_at=started_at,
            evaluation_finished_at=_utc_now_iso(),
        )


# ---------------------------------------------------------------------------
# Default runtime instance
# ---------------------------------------------------------------------------


_default_runtime_v2: SemanticRuntimeV2 | None = None


def get_default_runtime_v2() -> SemanticRuntimeV2:
    """Return the process-wide V2 runtime, built on first call.

    Lazy: a run with zero V2-eligible candidates constructs and calls
    zero V2 transports.
    """
    global _default_runtime_v2
    if _default_runtime_v2 is None:
        _default_runtime_v2 = SemanticRuntimeV2()
    return _default_runtime_v2


def reset_default_runtime_v2() -> None:
    """Drop the process-wide V2 runtime (tests)."""
    global _default_runtime_v2
    _default_runtime_v2 = None
