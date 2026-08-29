"""Production semantic runtime tests (PRODUCT-INTEL.SEMANTIC.RUNTIME).

Offline tests for ``product_intelligence.semantic.runtime``: the pinned
qualified route, the explicit fallback allowlist, exact model identity,
per-attempt provenance, and the refusal to hide programming defects.

No live model calls. Every test injects a fake transport and counts the calls
it received, because "how many paid model calls did this cost" is itself part
of the contract.
"""

from __future__ import annotations

import pytest

from product_intelligence.evaluation.semantic.transport import (
    FakeSemanticModelTransport,
    TransportFailure,
    TransportResult,
)
from product_intelligence.semantic import (
    FALLBACK_MODEL,
    FALLBACK_PROVIDER,
    PRIMARY_FALLBACK_ELIGIBLE_ERRORS,
    PRIMARY_MODEL,
    PRIMARY_NON_FALLBACK_ERRORS,
    PRIMARY_PROVIDER,
    SEMANTIC_MAX_TOKENS,
    SEMANTIC_PROMPT_VERSION,
    SEMANTIC_TEMPERATURE,
    ConfidenceLevel,
    SemanticAttempt,
    SemanticAttemptStatus,
    SemanticDecision,
    SemanticRuntime,
    SemanticRuntimeConfig,
    SemanticRuntimeConfigError,
    SemanticRuntimeErrorType,
    SemanticRuntimeFallbackReason,
    SemanticRuntimeResult,
    validate_runtime_config,
)

CASE_ID = "SMQ-0001"


# =============================================================================
# Helpers
# =============================================================================


def make_response(
    decision: str = "MATCH",
    confidence: str = "HIGH",
    reason_code: str = "test_match",
) -> str:
    """A valid six-field response body."""
    return (
        "{"
        f'"decision": "{decision}", '
        f'"confidence": "{confidence}", '
        '"matched_attributes": ["brand"], '
        '"conflicting_attributes": [], '
        '"missing_critical_attributes": [], '
        f'"reason_code": "{reason_code}"'
        "}"
    )


class CountingTransport(FakeSemanticModelTransport):
    """Fake transport that records every call it received.

    ``calls`` is the assertion surface for "exactly one primary call and zero
    fallback calls".
    """

    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)
        self.calls: list[dict] = []

    def complete(self, **kwargs):
        self.calls.append(dict(kwargs))
        return super().complete(**kwargs)


def primary_transport(**kwargs) -> CountingTransport:
    """A counting primary transport reporting the qualified primary model."""
    kwargs.setdefault("case_ids", (CASE_ID,))
    kwargs.setdefault("provider_reported_model", PRIMARY_MODEL)
    return CountingTransport(**kwargs)


def fallback_transport(**kwargs) -> CountingTransport:
    """A counting fallback transport reporting the qualified fallback model."""
    kwargs.setdefault("case_ids", (CASE_ID,))
    kwargs.setdefault("provider_reported_model", FALLBACK_MODEL)
    kwargs.setdefault("responses", {CASE_ID: make_response("MATCH")})
    return CountingTransport(**kwargs)


def make_runtime(
    primary: CountingTransport | None = None,
    fallback: CountingTransport | None = None,
    config: SemanticRuntimeConfig | None = None,
) -> SemanticRuntime:
    """Build a runtime with injected transports."""
    return SemanticRuntime(
        config=config,
        primary_transport=primary if primary is not None else primary_transport(),
        fallback_transport=fallback if fallback is not None else fallback_transport(),
    )


def evaluate(runtime: SemanticRuntime) -> SemanticRuntimeResult:
    """Run the single test case through a runtime."""
    return runtime.evaluate(
        case_id=CASE_ID,
        target_mpn="TEST-MPN",
        target_description="Test product",
        candidate_title="Test Product",
        candidate_mpn_field="TEST-MPN",
    )


# =============================================================================
# The qualified route is mechanically pinned
# =============================================================================


class TestQualifiedRouteIsPinned:
    """The production route is fixed by qualification, not by the caller."""

    def test_default_config_is_the_qualified_route(self):
        """The defaults are exactly the two qualified models."""
        config = SemanticRuntimeConfig()

        assert config.primary_provider == "amax"
        assert config.primary_model == "nemotron-3-super"
        assert config.fallback_provider == "vllm-262k"
        assert config.fallback_model == "Qwen3.6-27B-262K"
        assert config.temperature == 0.0
        assert config.max_tokens == 32768

    def test_module_constants_are_the_qualified_route(self):
        """The exported constants name the qualified models."""
        assert PRIMARY_PROVIDER == "amax"
        assert PRIMARY_MODEL == "nemotron-3-super"
        assert FALLBACK_PROVIDER == "vllm-262k"
        assert FALLBACK_MODEL == "Qwen3.6-27B-262K"
        assert SEMANTIC_TEMPERATURE == 0.0
        assert SEMANTIC_MAX_TOKENS == 32768

    @pytest.mark.parametrize(
        ("field", "value"),
        [
            ("primary_provider", "openai"),
            ("primary_provider", "amax-2"),
            ("primary_model", "nemotron-3-super-thinking"),
            ("primary_model", "gpt-oss-120b"),
            ("fallback_provider", "vllm-32k"),
            ("fallback_model", "Qwen3.5-27B"),
            ("temperature", 0.7),
            ("temperature", 0.1),
            ("max_tokens", 4096),
            ("max_tokens", 65536),
        ],
    )
    def test_unqualified_value_is_rejected(self, field: str, value: object):
        """Any deviation from the qualified constants is refused."""
        config = SemanticRuntimeConfig(**{field: value})

        with pytest.raises(SemanticRuntimeConfigError) as exc_info:
            validate_runtime_config(config)

        assert field in str(exc_info.value)

    @pytest.mark.parametrize(
        ("field", "value"),
        [
            ("primary_provider", "openai"),
            ("primary_model", "nemotron-3-super-thinking"),
            ("fallback_provider", "vllm-32k"),
            ("fallback_model", "Qwen3.5-27B"),
            ("temperature", 0.7),
            ("max_tokens", 4096),
        ],
    )
    def test_unqualified_config_is_rejected_before_any_transport_call(
        self, field: str, value: object
    ):
        """Construction fails before a single model call is made.

        Validation that happened after the first call would still have cost a
        request against an unqualified model.
        """
        primary = primary_transport(responses={CASE_ID: make_response("MATCH")})
        fallback = fallback_transport()

        with pytest.raises(SemanticRuntimeConfigError):
            SemanticRuntime(
                config=SemanticRuntimeConfig(**{field: value}),
                primary_transport=primary,
                fallback_transport=fallback,
            )

        assert primary.calls == []
        assert fallback.calls == []

    def test_max_tokens_must_be_the_qualified_int_not_an_equal_float(self):
        """32768.0 is not the qualified int and is refused."""
        with pytest.raises(SemanticRuntimeConfigError):
            validate_runtime_config(SemanticRuntimeConfig(max_tokens=32768.0))

    def test_max_tokens_must_not_be_a_bool(self):
        """``True`` equals 1 numerically; it is still not a token budget."""
        with pytest.raises(SemanticRuntimeConfigError):
            validate_runtime_config(SemanticRuntimeConfig(max_tokens=True))

    @pytest.mark.parametrize(
        "temperature",
        [False, True, 0, 1, 0.1, "0.0", None],
    )
    def test_temperature_must_be_the_exact_qualified_float(self, temperature):
        """0/False/0.1/a non-numeric value are all refused.

        Python equality makes False == 0 == 0.0 and True == 1 == 1.0, so a
        bare ``!=`` comparison would silently accept temperature=False or
        temperature=0 as "the qualified 0.0". The formally qualified request
        shape is specifically the float 0.0 (what the qualification run's
        JSON body actually sent), not anything merely numerically equal to
        it.
        """
        with pytest.raises(SemanticRuntimeConfigError):
            validate_runtime_config(
                SemanticRuntimeConfig(temperature=temperature)
            )

    def test_temperature_0_0_float_is_accepted(self):
        """The exact qualified value continues to validate cleanly."""
        validate_runtime_config(SemanticRuntimeConfig(temperature=0.0))

    def test_temperature_rejection_happens_before_any_transport_call(self):
        """Construction fails before a single model call is made."""
        primary = primary_transport(responses={CASE_ID: make_response("MATCH")})
        fallback = fallback_transport()

        with pytest.raises(SemanticRuntimeConfigError):
            SemanticRuntime(
                config=SemanticRuntimeConfig(temperature=0),
                primary_transport=primary,
                fallback_transport=fallback,
            )

        assert primary.calls == []
        assert fallback.calls == []

    def test_qualified_config_is_accepted(self):
        """The qualified route itself validates cleanly."""
        validate_runtime_config(SemanticRuntimeConfig())

    def test_timeout_remains_configurable(self):
        """Timeout is the one genuinely tunable setting."""
        validate_runtime_config(SemanticRuntimeConfig(request_timeout_seconds=30.0))
        validate_runtime_config(SemanticRuntimeConfig(request_timeout_seconds=600.0))

    @pytest.mark.parametrize("timeout", [0.0, -1.0, 3600.1, 100000.0])
    def test_out_of_bounds_timeout_is_rejected(self, timeout: float):
        """A nonsensical timeout is still a configuration defect."""
        with pytest.raises(SemanticRuntimeConfigError):
            validate_runtime_config(
                SemanticRuntimeConfig(request_timeout_seconds=timeout)
            )

    def test_non_config_object_is_rejected(self):
        """A duck-typed stand-in cannot smuggle in another route."""
        with pytest.raises(TypeError):
            validate_runtime_config(object())


# =============================================================================
# Invalid environment timeout fails closed (FU3A2C)
# =============================================================================


class TestTimeoutEnvironmentFailsClosed:
    """PI_SEMANTIC_REQUEST_TIMEOUT_SECONDS: absent is fine, present-and-wrong
    is a configuration error - never a silent fallback to the default.
    """

    ENV_VAR = "PI_SEMANTIC_REQUEST_TIMEOUT_SECONDS"

    def test_env_absent_uses_the_qualified_default(self, monkeypatch):
        from product_intelligence.semantic.runtime import (
            DEFAULT_REQUEST_TIMEOUT_SECONDS,
            _default_timeout_seconds,
        )

        monkeypatch.delenv(self.ENV_VAR, raising=False)

        assert _default_timeout_seconds() == DEFAULT_REQUEST_TIMEOUT_SECONDS
        assert DEFAULT_REQUEST_TIMEOUT_SECONDS == 300.0

    def test_env_valid_value_is_used(self, monkeypatch):
        from product_intelligence.semantic.runtime import _default_timeout_seconds

        monkeypatch.setenv(self.ENV_VAR, "30")

        assert _default_timeout_seconds() == 30.0

    def test_env_unparseable_string_fails_closed(self, monkeypatch):
        from product_intelligence.semantic.runtime import _default_timeout_seconds

        monkeypatch.setenv(self.ENV_VAR, "abc")

        with pytest.raises(SemanticRuntimeConfigError):
            _default_timeout_seconds()

    def test_env_nan_fails_closed(self, monkeypatch):
        """``float("nan")`` parses without raising - the isfinite check is
        what actually catches this.
        """
        from product_intelligence.semantic.runtime import _default_timeout_seconds

        monkeypatch.setenv(self.ENV_VAR, "nan")

        with pytest.raises(SemanticRuntimeConfigError):
            _default_timeout_seconds()

    def test_env_inf_fails_closed(self, monkeypatch):
        from product_intelligence.semantic.runtime import _default_timeout_seconds

        monkeypatch.setenv(self.ENV_VAR, "inf")

        with pytest.raises(SemanticRuntimeConfigError):
            _default_timeout_seconds()

    def test_env_negative_inf_fails_closed(self, monkeypatch):
        from product_intelligence.semantic.runtime import _default_timeout_seconds

        monkeypatch.setenv(self.ENV_VAR, "-inf")

        with pytest.raises(SemanticRuntimeConfigError):
            _default_timeout_seconds()

    def test_direct_construction_with_nan_fails_closed(self):
        """Bypassing the environment entirely: a directly constructed config
        with a NaN timeout must still be rejected. NaN compares False
        against every relational operator, so a bare bounds check would let
        it through silently - this is exactly what the isfinite guard in
        validate_runtime_config exists to prevent.
        """
        config = SemanticRuntimeConfig(request_timeout_seconds=float("nan"))

        with pytest.raises(SemanticRuntimeConfigError, match="finite"):
            validate_runtime_config(config)

    @pytest.mark.parametrize("timeout", [float("inf"), float("-inf")])
    def test_direct_construction_with_infinite_fails_closed(self, timeout):
        config = SemanticRuntimeConfig(request_timeout_seconds=timeout)

        with pytest.raises(SemanticRuntimeConfigError, match="finite"):
            validate_runtime_config(config)

    def test_invalid_env_timeout_fails_before_any_transport_is_built(
        self, monkeypatch
    ):
        """The failure happens while building SemanticRuntimeConfig itself -
        strictly before validate_runtime_config, and therefore strictly
        before either transport is constructed or called.
        """
        monkeypatch.setenv(self.ENV_VAR, "not-a-number")

        with pytest.raises(SemanticRuntimeConfigError):
            SemanticRuntime()

    def test_invalid_env_timeout_is_not_reported_as_provider_not_configured(
        self, monkeypatch
    ):
        """A local timeout configuration defect must be reported as exactly
        that - not laundered into PROVIDER_NOT_CONFIGURED, which would
        wrongly suggest the fix is to set a base-URL environment variable
        rather than to fix the timeout value.
        """
        monkeypatch.setenv(self.ENV_VAR, "abc")

        with pytest.raises(SemanticRuntimeConfigError) as exc_info:
            SemanticRuntime()

        assert "PROVIDER_NOT_CONFIGURED" not in str(exc_info.value)


# =============================================================================
# Exact model strings and generation parameters reach the transport
# =============================================================================


class TestTransportCallParameters:
    """What the runtime actually sends to a provider."""

    def test_primary_receives_bare_qualified_model_name(self):
        """The primary call uses the bare model name, not provider/model."""
        primary = primary_transport(responses={CASE_ID: make_response("MATCH")})

        evaluate(make_runtime(primary=primary))

        assert len(primary.calls) == 1
        assert primary.calls[0]["model"] == "nemotron-3-super"
        assert "/" not in primary.calls[0]["model"]

    def test_fallback_receives_bare_qualified_model_name(self):
        """The fallback call uses the bare fallback model name."""
        primary = primary_transport(failure_error_types={CASE_ID: "TIMEOUT"})
        fallback = fallback_transport()

        evaluate(make_runtime(primary=primary, fallback=fallback))

        assert len(fallback.calls) == 1
        assert fallback.calls[0]["model"] == "Qwen3.6-27B-262K"
        assert "/" not in fallback.calls[0]["model"]

    def test_qualified_generation_parameters_are_sent(self):
        """temperature=0.0 and max_tokens=32768 reach the provider."""
        primary = primary_transport(responses={CASE_ID: make_response("MATCH")})

        evaluate(make_runtime(primary=primary))

        assert primary.calls[0]["temperature"] == 0.0
        assert primary.calls[0]["max_tokens"] == 32768

    def test_both_providers_receive_the_identical_prompt(self):
        """Fallback re-asks the same question; it does not reframe it."""
        primary = primary_transport(failure_error_types={CASE_ID: "TIMEOUT"})
        fallback = fallback_transport()

        evaluate(make_runtime(primary=primary, fallback=fallback))

        assert primary.calls[0]["system_prompt"] == fallback.calls[0]["system_prompt"]
        assert primary.calls[0]["user_prompt"] == fallback.calls[0]["user_prompt"]


# =============================================================================
# A valid primary decision is FINAL
# =============================================================================


class TestValidPrimaryIsFinal:
    """MATCH, NO_MATCH and UNCERTAIN each end the evaluation."""

    @pytest.mark.parametrize("decision", ["MATCH", "NO_MATCH", "UNCERTAIN"])
    def test_valid_primary_decision_makes_exactly_one_call(self, decision: str):
        """Exactly one primary call, zero fallback calls."""
        primary = primary_transport(responses={CASE_ID: make_response(decision)})
        fallback = fallback_transport()

        result = evaluate(make_runtime(primary=primary, fallback=fallback))

        assert result.decision.value == decision
        assert len(primary.calls) == 1
        assert len(fallback.calls) == 0
        assert result.fallback_used is False
        assert result.fallback_reason is None
        assert result.attempt_count == 1

    @pytest.mark.parametrize("confidence", ["HIGH", "MEDIUM", "LOW"])
    def test_low_confidence_is_not_a_reason_to_fall_back(self, confidence: str):
        """Confidence is a semantic judgement, never an execution failure."""
        primary = primary_transport(
            responses={CASE_ID: make_response("UNCERTAIN", confidence)}
        )
        fallback = fallback_transport()

        result = evaluate(make_runtime(primary=primary, fallback=fallback))

        assert result.confidence.value == confidence
        assert len(fallback.calls) == 0
        assert result.fallback_used is False

    def test_successful_primary_names_the_primary_as_provenance(self):
        """A primary answer is attributed to the primary model."""
        result = evaluate(
            make_runtime(
                primary=primary_transport(responses={CASE_ID: make_response("MATCH")})
            )
        )

        assert result.actual_provider == "amax"
        assert result.actual_model == "nemotron-3-super"
        assert result.error_type is None


# =============================================================================
# Fallback eligibility is an explicit allowlist
# =============================================================================


class TestFallbackAllowlist:
    """Fallback happens only for a named, fallback-eligible failure."""

    def test_allowlist_contents_are_exactly_the_qualified_set(self):
        """The allowlist is pinned; a silent addition must fail this test.

        FU3A2D: INVALID_RESPONSE was added. A malformed HTTP-200 provider
        envelope (missing/empty/malformed "choices") is an execution/output-
        contract failure of the primary, exactly like MALFORMED_JSON or
        SCHEMA_INVALID - it must buy exactly one fallback attempt, the same
        as those two. Its earlier absence from this set was the defect FU3A2D
        closes, not a frozen routing decision being reopened.
        """
        assert PRIMARY_FALLBACK_ELIGIBLE_ERRORS == frozenset(
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
                "INVALID_RESPONSE",
            }
        )

    def test_allowlist_and_denylist_do_not_overlap(self):
        """No failure may be both eligible and ineligible."""
        assert not (PRIMARY_FALLBACK_ELIGIBLE_ERRORS & PRIMARY_NON_FALLBACK_ERRORS)

    @pytest.mark.parametrize(
        ("error_type", "expected_reason"),
        [
            ("TIMEOUT", SemanticRuntimeFallbackReason.TIMEOUT),
            ("DNS_ERROR", SemanticRuntimeFallbackReason.DNS_ERROR),
            ("TLS_ERROR", SemanticRuntimeFallbackReason.TLS_ERROR),
            ("CONNECTION_ERROR", SemanticRuntimeFallbackReason.CONNECTION_ERROR),
            ("RATE_LIMITED", SemanticRuntimeFallbackReason.RATE_LIMITED),
            ("HTTP_ERROR", SemanticRuntimeFallbackReason.HTTP_ERROR),
            (
                "PROVIDER_UNAVAILABLE",
                SemanticRuntimeFallbackReason.PROVIDER_UNAVAILABLE,
            ),
            (
                "AUTHENTICATION_FAILED",
                SemanticRuntimeFallbackReason.AUTHENTICATION_FAILED,
            ),
            ("MODEL_NOT_FOUND", SemanticRuntimeFallbackReason.MODEL_NOT_FOUND),
        ],
    )
    def test_eligible_transport_failure_falls_back_exactly_once(
        self, error_type: str, expected_reason: SemanticRuntimeFallbackReason
    ):
        """Each allowlisted transport failure buys exactly one fallback call."""
        primary = primary_transport(failure_error_types={CASE_ID: error_type})
        fallback = fallback_transport()

        result = evaluate(make_runtime(primary=primary, fallback=fallback))

        assert len(primary.calls) == 1
        assert len(fallback.calls) == 1
        assert result.fallback_used is True
        assert result.fallback_reason is expected_reason
        assert result.decision.value == "MATCH"

    @pytest.mark.parametrize(
        "error_type",
        [
            "INVALID_REQUEST_CONFIGURATION",
            "UNSUPPORTED_PARAMETER",
            "PROVIDER_NOT_CONFIGURED",
        ],
    )
    def test_non_eligible_failure_makes_zero_fallback_calls(self, error_type: str):
        """A local configuration defect must not buy a second model call."""
        primary = primary_transport(failure_error_types={CASE_ID: error_type})
        fallback = fallback_transport()

        result = evaluate(make_runtime(primary=primary, fallback=fallback))

        assert len(primary.calls) == 1
        assert len(fallback.calls) == 0
        assert result.fallback_used is False
        assert result.fallback_reason is None
        assert result.decision is None
        assert result.attempt_count == 1

    @pytest.mark.parametrize(
        "error_type",
        ["SOMETHING_NEW", "", "not_a_known_code"],
    )
    def test_unrecognised_error_code_makes_zero_fallback_calls(self, error_type: str):
        """A genuinely unknown code is NOT fallback eligible.

        This is what an allowlist buys over a denylist: a transport error code
        added later cannot silently start costing a second paid call.

        CASE_REJECTED is deliberately NOT parametrized here (FU3A2D): it is a
        KNOWN bounded code from the canonical transport's ``ALL_ERROR_TYPES``,
        not an unrecognised one, and it maps to its own
        ``SemanticAttemptStatus.CASE_REJECTED`` rather than to
        ``UNKNOWN_ERROR``. See ``TestCaseRejectedProvenance`` below.
        """
        primary = primary_transport(failure_error_types={CASE_ID: error_type})
        fallback = fallback_transport()

        result = evaluate(make_runtime(primary=primary, fallback=fallback))

        assert len(fallback.calls) == 0
        assert result.fallback_used is False
        assert result.decision is None
        assert result.attempts[0].status is SemanticAttemptStatus.UNKNOWN_ERROR

    def test_unconfigured_primary_provider_makes_zero_fallback_calls(self):
        """A missing local provider configuration fails closed.

        The constructor treats ``None`` as "build a live transport", so the
        unconfigured outcome of that build is simulated directly rather than
        by reaching for the environment.
        """
        fallback = fallback_transport()
        runtime = make_runtime(fallback=fallback)
        runtime._primary_transport = None  # what an unconfigured build returns

        result = evaluate(runtime)

        assert len(fallback.calls) == 0
        assert result.fallback_used is False
        assert result.error_type is SemanticRuntimeErrorType.PROVIDER_NOT_CONFIGURED
        assert result.attempts[0].status is (
            SemanticAttemptStatus.PROVIDER_NOT_CONFIGURED
        )


# =============================================================================
# INVALID_PROVIDER_RESPONSE triggers fallback exactly once (FU3A2D)
# =============================================================================


class TestInvalidProviderResponseTriggersFallback:
    """A malformed HTTP-200 provider envelope is an execution/output-contract
    failure of the primary - the same class of failure as MALFORMED_JSON or
    SCHEMA_INVALID - and buys exactly one Qwen fallback attempt.
    """

    def test_primary_invalid_provider_response_falls_back_exactly_once(self):
        primary = primary_transport(
            failure_error_types={CASE_ID: "INVALID_PROVIDER_RESPONSE"}
        )
        fallback = fallback_transport()

        result = evaluate(make_runtime(primary=primary, fallback=fallback))

        assert len(primary.calls) == 1
        assert len(fallback.calls) == 1
        assert result.attempts[0].status is SemanticAttemptStatus.INVALID_RESPONSE
        assert result.fallback_used is True
        assert result.fallback_reason is (
            SemanticRuntimeFallbackReason.INVALID_RESPONSE
        )

    def test_fallback_success_after_invalid_provider_response_returns_qwen_answer(
        self,
    ):
        """The fallback's real semantic answer is what the caller gets back."""
        primary = primary_transport(
            failure_error_types={CASE_ID: "INVALID_PROVIDER_RESPONSE"}
        )
        fallback = fallback_transport(responses={CASE_ID: make_response("NO_MATCH")})

        result = evaluate(make_runtime(primary=primary, fallback=fallback))

        assert result.decision.value == "NO_MATCH"
        assert result.actual_provider == FALLBACK_PROVIDER
        assert result.actual_model == FALLBACK_MODEL
        assert result.attempt_count == 2

    def test_both_invalid_provider_response_is_a_final_failure_no_third_provider(
        self,
    ):
        primary = primary_transport(
            failure_error_types={CASE_ID: "INVALID_PROVIDER_RESPONSE"}
        )
        fallback = fallback_transport(
            failure_error_types={CASE_ID: "INVALID_PROVIDER_RESPONSE"}
        )

        result = evaluate(make_runtime(primary=primary, fallback=fallback))

        assert len(primary.calls) == 1
        assert len(fallback.calls) == 1
        assert result.attempt_count == 2
        assert result.decision is None
        assert result.error_type is (
            SemanticRuntimeErrorType.FALLBACK_INVALID_RESPONSE
        )

    def test_invalid_response_with_fallback_unconfigured_still_makes_two_attempts(
        self,
    ):
        """Fallback is still ENTERED even when the fallback provider is
        locally unconfigured: PROVIDER_NOT_CONFIGURED is itself a recorded
        second attempt, never a reason to collapse the result down to one
        attempt. This is what proves the dataclass invariant (a one-attempt
        result is impossible for a fallback-eligible primary status) matches
        what ``evaluate()`` really does, even in this edge case.

        The unconfigured fallback is simulated directly (what
        ``SemanticRuntime._build_transport`` returns when a live transport
        cannot be built), the same way
        ``test_unconfigured_primary_provider_makes_zero_fallback_calls``
        simulates it for the primary. No live calls.
        """
        primary = primary_transport(
            failure_error_types={CASE_ID: "INVALID_PROVIDER_RESPONSE"}
        )
        runtime = make_runtime(primary=primary)
        runtime._fallback_transport = None  # what an unconfigured build returns

        result = evaluate(runtime)

        assert result.attempt_count == 2
        assert result.attempts[0].status is SemanticAttemptStatus.INVALID_RESPONSE
        assert result.attempts[1].status is (
            SemanticAttemptStatus.PROVIDER_NOT_CONFIGURED
        )
        assert result.fallback_used is True
        assert result.fallback_reason is (
            SemanticRuntimeFallbackReason.INVALID_RESPONSE
        )
        assert result.decision is None
        assert result.actual_provider is None
        assert result.actual_model is None


# =============================================================================
# CASE_REJECTED is a known bounded code, never UNKNOWN_ERROR (FU3A2D)
# =============================================================================


class TestCaseRejectedProvenance:
    """CASE_REJECTED (a content-policy rejection of the CASE itself) is a
    canonical known transport code, not an unrecognised one. It must not be
    lost into UNKNOWN_ERROR, and it remains non-fallback: retrying the
    identical rejected content against a different model would not help.
    """

    def test_case_rejected_is_a_distinct_known_status_not_unknown(self):
        primary = primary_transport(failure_error_types={CASE_ID: "CASE_REJECTED"})
        fallback = fallback_transport()

        result = evaluate(make_runtime(primary=primary, fallback=fallback))

        assert result.attempts[0].status is SemanticAttemptStatus.CASE_REJECTED
        assert result.attempts[0].status is not SemanticAttemptStatus.UNKNOWN_ERROR

    def test_case_rejected_makes_zero_fallback_calls(self):
        primary = primary_transport(failure_error_types={CASE_ID: "CASE_REJECTED"})
        fallback = fallback_transport()

        result = evaluate(make_runtime(primary=primary, fallback=fallback))

        assert len(primary.calls) == 1
        assert len(fallback.calls) == 0
        assert result.fallback_used is False
        assert result.fallback_reason is None
        assert result.attempt_count == 1

    def test_case_rejected_has_its_own_final_error_type(self):
        primary = primary_transport(failure_error_types={CASE_ID: "CASE_REJECTED"})

        result = evaluate(make_runtime(primary=primary))

        assert result.error_type is SemanticRuntimeErrorType.PRIMARY_CASE_REJECTED

    def test_case_rejected_is_not_fallback_eligible(self):
        assert "CASE_REJECTED" not in PRIMARY_FALLBACK_ELIGIBLE_ERRORS
        assert "CASE_REJECTED" in PRIMARY_NON_FALLBACK_ERRORS


class TestEveryCanonicalTransportCodeHasAnIntentionalMapping:
    """Every code the neutral transport can actually return must have a
    deliberate runtime mapping - never a silent fall-through to
    UNKNOWN_ERROR, which would make a real, classifiable failure
    indistinguishable from a code the runtime has genuinely never seen.

    A truly unrecognised string - one that does not appear in the canonical
    transport's vocabulary at all - is the ONLY thing that may still map to
    UNKNOWN_ERROR, and UNKNOWN_ERROR must never be fallback-eligible.
    """

    def test_every_all_error_types_code_has_a_non_unknown_mapping(self):
        from product_intelligence.semantic.runtime import (
            _attempt_status_for_error,
        )
        from product_intelligence.semantic.transport import ALL_ERROR_TYPES

        assert ALL_ERROR_TYPES, "the canonical transport must define error codes"

        for code in sorted(ALL_ERROR_TYPES):
            status = _attempt_status_for_error(code)
            assert status is not SemanticAttemptStatus.UNKNOWN_ERROR, (
                f"canonical transport code {code!r} has no intentional "
                "runtime mapping and silently becomes UNKNOWN_ERROR"
            )

    @pytest.mark.parametrize(
        "future_code",
        ["SOME_BRAND_NEW_CODE_2027", "", "not_a_real_code", "case_rejected"],
    )
    def test_truly_unrecognised_code_still_maps_to_unknown_error(
        self, future_code: str
    ):
        """A code that is NOT part of the canonical vocabulary at all -
        including a near-miss like lowercase "case_rejected" - stays
        UNKNOWN_ERROR. This is what proves the guard above is actually
        testing something: UNKNOWN_ERROR is reachable, just not for any code
        the transport can really send.
        """
        from product_intelligence.semantic.runtime import (
            _attempt_status_for_error,
        )
        from product_intelligence.semantic.transport import ALL_ERROR_TYPES

        assert future_code not in ALL_ERROR_TYPES

        assert _attempt_status_for_error(future_code) is (
            SemanticAttemptStatus.UNKNOWN_ERROR
        )

    def test_unknown_error_is_never_fallback_eligible(self):
        assert "UNKNOWN_ERROR" not in PRIMARY_FALLBACK_ELIGIBLE_ERRORS


# =============================================================================
# Empty, malformed and schema-invalid are three distinct behaviours
# =============================================================================


class TestResponseLevelFailures:
    """Three different ways a syntactically present response can be unusable."""

    def test_empty_response_falls_back_once(self):
        """An empty body is an execution failure, not a semantic answer."""
        primary = primary_transport(responses={CASE_ID: ""})
        fallback = fallback_transport()

        result = evaluate(make_runtime(primary=primary, fallback=fallback))

        assert len(primary.calls) == 1
        assert len(fallback.calls) == 1
        assert result.attempts[0].status is SemanticAttemptStatus.EMPTY_RESPONSE
        assert result.fallback_reason is SemanticRuntimeFallbackReason.EMPTY_RESPONSE
        assert result.decision.value == "MATCH"

    def test_malformed_json_falls_back_once(self):
        """Syntactically invalid JSON is MALFORMED_JSON, distinctly."""
        primary = primary_transport(responses={CASE_ID: '{"decision": "MATCH"'})
        fallback = fallback_transport()

        result = evaluate(make_runtime(primary=primary, fallback=fallback))

        assert len(primary.calls) == 1
        assert len(fallback.calls) == 1
        assert result.attempts[0].status is SemanticAttemptStatus.MALFORMED_JSON
        assert result.fallback_reason is SemanticRuntimeFallbackReason.MALFORMED_JSON
        assert result.decision.value == "MATCH"

    def test_schema_invalid_falls_back_once(self):
        """Valid JSON with all six keys can still fail typed validation.

        ``matched_attributes`` carries a non-string. The raw JSON shape parser
        accepts it (the value is a list); typed validation rejects it. This is
        a genuinely different failure from a missing key, and it is what
        SCHEMA_INVALID names.
        """
        schema_invalid = (
            '{"decision": "MATCH", "confidence": "HIGH", '
            '"matched_attributes": ["brand", 7], '
            '"conflicting_attributes": [], '
            '"missing_critical_attributes": [], '
            '"reason_code": "exact_mpn_match"}'
        )
        primary = primary_transport(responses={CASE_ID: schema_invalid})
        fallback = fallback_transport()

        result = evaluate(make_runtime(primary=primary, fallback=fallback))

        assert len(primary.calls) == 1
        assert len(fallback.calls) == 1
        assert result.attempts[0].status is SemanticAttemptStatus.SCHEMA_INVALID
        assert result.fallback_reason is SemanticRuntimeFallbackReason.SCHEMA_INVALID
        assert result.decision.value == "MATCH"

    def test_schema_invalid_body_passes_raw_shape_parsing(self):
        """The SCHEMA_INVALID fixture really does get past the JSON parser.

        Otherwise the test above would be a second malformed-JSON test wearing
        a different name.
        """
        from product_intelligence.semantic.contract import (
            parse_raw_output,
            validate_response,
        )

        body = (
            '{"decision": "MATCH", "confidence": "HIGH", '
            '"matched_attributes": ["brand", 7], '
            '"conflicting_attributes": [], '
            '"missing_critical_attributes": [], '
            '"reason_code": "exact_mpn_match"}'
        )

        parsed = parse_raw_output(body)  # must NOT raise
        assert parsed["decision"] == "MATCH"

        with pytest.raises(TypeError):
            validate_response(parsed)

    def test_missing_required_keys_is_malformed_not_schema_invalid(self):
        """A missing key fails the raw shape parser, so it is MALFORMED_JSON.

        Keeps the two failures genuinely distinct rather than collapsing one
        into the other's name.
        """
        primary = primary_transport(responses={CASE_ID: '{"decision": "MATCH"}'})
        fallback = fallback_transport()

        result = evaluate(make_runtime(primary=primary, fallback=fallback))

        assert result.attempts[0].status is SemanticAttemptStatus.MALFORMED_JSON
        assert len(fallback.calls) == 1


# =============================================================================
# Exact model identity
# =============================================================================


class TestModelIdentity:
    """Identity must be proven, never assumed."""

    def test_primary_wrong_model_falls_back_exactly_once(self):
        """A wrong reported model means the qualified model did not answer."""
        primary = primary_transport(
            responses={CASE_ID: make_response("MATCH")},
            provider_reported_model="nemotron-3-super-thinking",
        )
        fallback = fallback_transport()

        result = evaluate(make_runtime(primary=primary, fallback=fallback))

        assert len(primary.calls) == 1
        assert len(fallback.calls) == 1
        assert result.attempts[0].status is (
            SemanticAttemptStatus.MODEL_IDENTITY_MISMATCH
        )
        assert result.fallback_reason is (
            SemanticRuntimeFallbackReason.MODEL_IDENTITY_MISMATCH
        )
        assert result.decision.value == "MATCH"
        assert result.actual_provider == "vllm-262k"
        assert result.actual_model == "Qwen3.6-27B-262K"

    def test_primary_missing_model_identity_falls_back_exactly_once(self):
        """No reported model means identity cannot be proven.

        A response is never accepted merely because the provider declined to
        say which model produced it.
        """
        primary = primary_transport(
            responses={CASE_ID: make_response("MATCH")},
            provider_reported_model=None,
        )
        fallback = fallback_transport()

        result = evaluate(make_runtime(primary=primary, fallback=fallback))

        assert len(primary.calls) == 1
        assert len(fallback.calls) == 1
        assert result.attempts[0].status is (
            SemanticAttemptStatus.MODEL_IDENTITY_MISMATCH
        )
        assert result.decision.value == "MATCH"
        assert result.actual_model == "Qwen3.6-27B-262K"

    def test_fallback_wrong_model_is_a_final_failure(self):
        """No third provider exists. A wrong fallback model ends it."""
        primary = primary_transport(failure_error_types={CASE_ID: "TIMEOUT"})
        fallback = fallback_transport(provider_reported_model="Qwen3.5-27B")

        result = evaluate(make_runtime(primary=primary, fallback=fallback))

        assert len(primary.calls) == 1
        assert len(fallback.calls) == 1
        assert result.decision is None
        assert result.error_type is (
            SemanticRuntimeErrorType.FALLBACK_MODEL_IDENTITY_MISMATCH
        )
        assert result.actual_provider is None
        assert result.actual_model is None

    def test_fallback_missing_model_identity_is_a_final_failure(self):
        """An unproven fallback identity is also final."""
        primary = primary_transport(failure_error_types={CASE_ID: "TIMEOUT"})
        fallback = fallback_transport(provider_reported_model=None)

        result = evaluate(make_runtime(primary=primary, fallback=fallback))

        assert len(fallback.calls) == 1
        assert result.decision is None
        assert result.error_type is (
            SemanticRuntimeErrorType.FALLBACK_MODEL_IDENTITY_MISMATCH
        )
        assert result.actual_provider is None

    def test_correct_model_identity_is_accepted(self):
        """The qualified model reporting itself is accepted."""
        primary = primary_transport(
            responses={CASE_ID: make_response("MATCH")},
            provider_reported_model="nemotron-3-super",
        )

        result = evaluate(make_runtime(primary=primary))

        assert result.decision.value == "MATCH"
        assert result.actual_model == "nemotron-3-super"


# =============================================================================
# Programming defects stay visible
# =============================================================================


class TestProgrammingDefectsAreNotHidden:
    """An unexpected exception is a bug, not a provider outage."""

    def test_primary_runtime_error_propagates_and_does_not_fall_back(self):
        """A RuntimeError from the primary transport reaches the caller."""

        class ExplodingTransport(CountingTransport):
            def complete(self, **kwargs):
                self.calls.append(dict(kwargs))
                raise RuntimeError("sentinel")

        primary = ExplodingTransport(case_ids=(CASE_ID,))
        fallback = fallback_transport()

        with pytest.raises(RuntimeError, match="sentinel"):
            evaluate(make_runtime(primary=primary, fallback=fallback))

        assert len(primary.calls) == 1
        assert len(fallback.calls) == 0

    @pytest.mark.parametrize(
        "exception",
        [
            TypeError("sentinel-type"),
            AttributeError("sentinel-attr"),
            KeyError("sentinel-key"),
            ZeroDivisionError("sentinel-zero"),
        ],
    )
    def test_other_programming_exceptions_also_propagate(self, exception: Exception):
        """No broad catch converts a defect into a CONNECTION_ERROR."""

        class ExplodingTransport(CountingTransport):
            def complete(self, **kwargs):
                self.calls.append(dict(kwargs))
                raise exception

        primary = ExplodingTransport(case_ids=(CASE_ID,))
        fallback = fallback_transport()

        with pytest.raises(type(exception)):
            evaluate(make_runtime(primary=primary, fallback=fallback))

        assert len(fallback.calls) == 0

    def test_fallback_exception_propagates_too(self):
        """The fallback path has no broad catch either."""

        class ExplodingTransport(CountingTransport):
            def complete(self, **kwargs):
                self.calls.append(dict(kwargs))
                raise RuntimeError("fallback-sentinel")

        primary = primary_transport(failure_error_types={CASE_ID: "TIMEOUT"})
        fallback = ExplodingTransport(case_ids=(CASE_ID,))

        with pytest.raises(RuntimeError, match="fallback-sentinel"):
            evaluate(make_runtime(primary=primary, fallback=fallback))

    def test_runtime_source_has_no_bare_broad_except(self):
        """No ``except Exception`` may remain in the runtime source.

        Transport.complete already owns network and provider normalization; a
        broad catch here would re-hide exactly the defects above.
        """
        import ast
        from pathlib import Path

        import product_intelligence.semantic.runtime as runtime_module

        tree = ast.parse(
            Path(runtime_module.__file__).read_text(encoding="utf-8")
        )

        broad = []
        for node in ast.walk(tree):
            if isinstance(node, ast.ExceptHandler):
                if node.type is None:
                    broad.append("bare except")
                elif isinstance(node.type, ast.Name) and node.type.id in (
                    "Exception",
                    "BaseException",
                ):
                    broad.append(node.type.id)

        assert broad == [], (
            f"product_intelligence/semantic/runtime.py contains broad excepts "
            f"{broad}; programming defects must stay visible"
        )


# =============================================================================
# Per-attempt provenance
# =============================================================================


class TestAttemptProvenance:
    """Every attempt the runtime made is recorded, with its own status."""

    def test_attempt_shape_is_frozen_and_typed(self):
        """A SemanticAttempt carries provider, model, status and latency."""
        attempt = SemanticAttempt(
            provider="amax",
            model="nemotron-3-super",
            status=SemanticAttemptStatus.OK,
            latency_ms=12.5,
        )

        assert attempt.provider == "amax"
        assert attempt.model == "nemotron-3-super"
        assert attempt.status is SemanticAttemptStatus.OK
        assert attempt.latency_ms == 12.5

        with pytest.raises(AttributeError):
            attempt.provider = "other"  # frozen

    def test_attempt_rejects_a_plain_string_status(self):
        """The status vocabulary cannot be bypassed with a raw string."""
        with pytest.raises(TypeError):
            SemanticAttempt(
                provider="amax",
                model="nemotron-3-super",
                status="OK",
                latency_ms=1.0,
            )

    def test_attempt_rejects_negative_latency(self):
        """Latency is a measurement, not a free-form field."""
        with pytest.raises(ValueError):
            SemanticAttempt(
                provider="amax",
                model="nemotron-3-super",
                status=SemanticAttemptStatus.OK,
                latency_ms=-1.0,
            )

    def test_successful_primary_records_one_attempt(self):
        """One call, one attempt record."""
        result = evaluate(
            make_runtime(
                primary=primary_transport(responses={CASE_ID: make_response("MATCH")})
            )
        )

        assert len(result.attempts) == 1
        assert result.attempts[0].provider == "amax"
        assert result.attempts[0].model == "nemotron-3-super"
        assert result.attempts[0].status is SemanticAttemptStatus.OK
        assert result.attempts[0].latency_ms >= 0.0

    def test_failed_attempt_still_records_latency(self):
        """A failed attempt retains a safe latency figure."""
        primary = primary_transport(failure_error_types={CASE_ID: "TIMEOUT"})

        result = evaluate(make_runtime(primary=primary))

        assert result.attempts[0].status is SemanticAttemptStatus.TIMEOUT
        assert result.attempts[0].latency_ms >= 0.0

    def test_both_providers_failing_records_two_independent_statuses(self):
        """Two attempts, each with its own bounded status."""
        primary = primary_transport(failure_error_types={CASE_ID: "TIMEOUT"})
        fallback = fallback_transport(
            failure_error_types={CASE_ID: "PROVIDER_UNAVAILABLE"}
        )

        result = evaluate(make_runtime(primary=primary, fallback=fallback))

        assert len(result.attempts) == 2

        first, second = result.attempts
        assert first.provider == "amax"
        assert first.model == "nemotron-3-super"
        assert first.status is SemanticAttemptStatus.TIMEOUT

        assert second.provider == "vllm-262k"
        assert second.model == "Qwen3.6-27B-262K"
        assert second.status is SemanticAttemptStatus.PROVIDER_UNAVAILABLE

        # The two statuses really are independent, not one copied twice.
        assert first.status is not second.status

    def test_fallback_reason_always_records_why_fallback_was_entered(self):
        """Even when both fail, the reason names the PRIMARY failure."""
        primary = primary_transport(failure_error_types={CASE_ID: "RATE_LIMITED"})
        fallback = fallback_transport(failure_error_types={CASE_ID: "TIMEOUT"})

        result = evaluate(make_runtime(primary=primary, fallback=fallback))

        assert result.fallback_used is True
        assert result.fallback_reason is SemanticRuntimeFallbackReason.RATE_LIMITED
        assert result.error_type is SemanticRuntimeErrorType.FALLBACK_TIMEOUT

    def test_requested_primary_route_is_always_recorded(self):
        """The requested route is reported even when the fallback answered."""
        primary = primary_transport(failure_error_types={CASE_ID: "TIMEOUT"})
        fallback = fallback_transport()

        result = evaluate(make_runtime(primary=primary, fallback=fallback))

        assert result.requested_primary_provider == "amax"
        assert result.requested_primary_model == "nemotron-3-super"
        assert result.actual_provider == "vllm-262k"
        assert result.actual_model == "Qwen3.6-27B-262K"

    def test_attempt_count_matches_attempts_length(self):
        """attempt_count is derived, so it cannot disagree with attempts."""
        primary = primary_transport(failure_error_types={CASE_ID: "TIMEOUT"})
        fallback = fallback_transport()

        result = evaluate(make_runtime(primary=primary, fallback=fallback))

        assert result.attempt_count == len(result.attempts) == 2


# =============================================================================
# Failure claims no provenance
# =============================================================================


class TestFailureClaimsNoProvenance:
    """A failed result never names a provider that answered, because none did."""

    @pytest.mark.parametrize(
        ("primary_error", "fallback_error"),
        [
            ("TIMEOUT", "TIMEOUT"),
            ("CONNECTION_ERROR", "HTTP_ERROR"),
            ("RATE_LIMITED", "PROVIDER_UNAVAILABLE"),
        ],
    )
    def test_both_provider_failure_has_no_actual_provider_or_model(
        self, primary_error: str, fallback_error: str
    ):
        """Both failed, so there is no actual provider to name."""
        primary = primary_transport(failure_error_types={CASE_ID: primary_error})
        fallback = fallback_transport(failure_error_types={CASE_ID: fallback_error})

        result = evaluate(make_runtime(primary=primary, fallback=fallback))

        assert result.decision is None
        assert result.actual_provider is None
        assert result.actual_model is None
        assert result.error_type is not None

    def test_non_eligible_primary_failure_has_no_actual_provider_or_model(self):
        """A fail-closed result names no provider either."""
        primary = primary_transport(
            failure_error_types={CASE_ID: "INVALID_REQUEST_CONFIGURATION"}
        )

        result = evaluate(make_runtime(primary=primary))

        assert result.actual_provider is None
        assert result.actual_model is None

    def test_a_failed_result_cannot_be_fabricated_with_provenance(self):
        """The contract itself refuses the impossible state.

        The single attempt is otherwise perfectly valid (a real, non-
        fallback-eligible primary failure - CASE_REJECTED, not TIMEOUT,
        since TIMEOUT is fallback-eligible and a one-attempt result with it
        is rejected before this check is ever reached - correct shape for a
        one-attempt result) so the ONLY thing wrong with this construction -
        and the only thing the raised message can be about - is the
        fabricated actual_provider/actual_model on a result with no
        decision.
        """
        with pytest.raises(ValueError, match="must not name an actual provider"):
            SemanticRuntimeResult(
                case_id=CASE_ID,
                target_mpn="TEST-MPN",
                target_description="Test product",
                candidate_title="Test Product",
                candidate_mpn_field=None,
                candidate_sku=None,
                candidate_specs=None,
                evidence_source="UNKNOWN",
                requested_primary_provider="amax",
                requested_primary_model="nemotron-3-super",
                attempts=(
                    SemanticAttempt(
                        provider="amax",
                        model="nemotron-3-super",
                        status=SemanticAttemptStatus.CASE_REJECTED,
                        latency_ms=1.0,
                    ),
                ),
                fallback_used=False,
                fallback_reason=None,
                actual_provider="amax",
                actual_model="nemotron-3-super",
                decision=None,
                confidence=None,
                matched_attributes=(),
                conflicting_attributes=(),
                missing_critical_attributes=(),
                reason_code=None,
                error_type=SemanticRuntimeErrorType.PRIMARY_CASE_REJECTED,
            )

    def test_a_result_cannot_carry_both_a_decision_and_an_error(self):
        """A decision and a failure are mutually exclusive.

        The single attempt is otherwise perfectly valid (a real successful
        primary, correct shape for a one-attempt result) so the ONLY thing
        wrong with this construction is carrying both a decision and an
        error_type.
        """
        from product_intelligence.semantic import SemanticDecision

        with pytest.raises(ValueError, match="not both"):
            SemanticRuntimeResult(
                case_id=CASE_ID,
                target_mpn="TEST-MPN",
                target_description="Test product",
                candidate_title="Test Product",
                candidate_mpn_field=None,
                candidate_sku=None,
                candidate_specs=None,
                evidence_source="UNKNOWN",
                requested_primary_provider="amax",
                requested_primary_model="nemotron-3-super",
                attempts=(
                    SemanticAttempt(
                        provider="amax",
                        model="nemotron-3-super",
                        status=SemanticAttemptStatus.OK,
                        latency_ms=1.0,
                    ),
                ),
                fallback_used=False,
                fallback_reason=None,
                actual_provider="amax",
                actual_model="nemotron-3-super",
                decision=SemanticDecision.MATCH,
                confidence=None,
                matched_attributes=(),
                conflicting_attributes=(),
                missing_critical_attributes=(),
                reason_code="x",
                error_type=SemanticRuntimeErrorType.BOTH_UNAVAILABLE,
            )


# =============================================================================
# Impossible provenance is mechanically rejected (FU3A2C)
# =============================================================================


def _primary_ok_attempt() -> SemanticAttempt:
    return SemanticAttempt(
        provider=PRIMARY_PROVIDER,
        model=PRIMARY_MODEL,
        status=SemanticAttemptStatus.OK,
        latency_ms=1.0,
    )


def _primary_failed_attempt(
    status: SemanticAttemptStatus = SemanticAttemptStatus.TIMEOUT,
) -> SemanticAttempt:
    return SemanticAttempt(
        provider=PRIMARY_PROVIDER, model=PRIMARY_MODEL, status=status, latency_ms=1.0,
    )


def _fallback_ok_attempt() -> SemanticAttempt:
    return SemanticAttempt(
        provider=FALLBACK_PROVIDER,
        model=FALLBACK_MODEL,
        status=SemanticAttemptStatus.OK,
        latency_ms=1.0,
    )


def _fallback_failed_attempt(
    status: SemanticAttemptStatus = SemanticAttemptStatus.HTTP_ERROR,
) -> SemanticAttempt:
    return SemanticAttempt(
        provider=FALLBACK_PROVIDER, model=FALLBACK_MODEL, status=status, latency_ms=1.0,
    )


def _valid_success_kwargs(**overrides) -> dict:
    """A minimal, entirely valid one-attempt primary-success result's kwargs.

    Every adversarial test below starts from a construction that is known
    valid and changes exactly ONE thing, so a raised error can only be about
    the thing that test is checking.
    """
    base = dict(
        case_id=CASE_ID,
        target_mpn="TEST-MPN",
        target_description="Test product",
        candidate_title="Test Product",
        candidate_mpn_field=None,
        candidate_sku=None,
        candidate_specs=None,
        evidence_source="UNKNOWN",
        requested_primary_provider=PRIMARY_PROVIDER,
        requested_primary_model=PRIMARY_MODEL,
        attempts=(_primary_ok_attempt(),),
        fallback_used=False,
        fallback_reason=None,
        actual_provider=PRIMARY_PROVIDER,
        actual_model=PRIMARY_MODEL,
        decision=SemanticDecision.MATCH,
        confidence=ConfidenceLevel.HIGH,
        matched_attributes=(),
        conflicting_attributes=(),
        missing_critical_attributes=(),
        reason_code="exact_mpn_match",
        error_type=None,
    )
    base.update(overrides)
    return base


def _valid_failure_kwargs(**overrides) -> dict:
    """A minimal, entirely valid one-attempt primary-failure result's kwargs."""
    base = dict(
        case_id=CASE_ID,
        target_mpn="TEST-MPN",
        target_description="Test product",
        candidate_title="Test Product",
        candidate_mpn_field=None,
        candidate_sku=None,
        candidate_specs=None,
        evidence_source="UNKNOWN",
        requested_primary_provider=PRIMARY_PROVIDER,
        requested_primary_model=PRIMARY_MODEL,
        attempts=(_primary_failed_attempt(SemanticAttemptStatus.PROVIDER_NOT_CONFIGURED),),
        fallback_used=False,
        fallback_reason=None,
        actual_provider=None,
        actual_model=None,
        decision=None,
        confidence=None,
        matched_attributes=(),
        conflicting_attributes=(),
        missing_critical_attributes=(),
        reason_code=None,
        error_type=SemanticRuntimeErrorType.PROVIDER_NOT_CONFIGURED,
    )
    base.update(overrides)
    return base


class TestImpossibleProvenanceRejected:
    """Adversarial constructor calls, each changing exactly one field away
    from an otherwise-valid result, proving the __post_init__ invariant that
    field alone protects.
    """

    # -- both baseline fixtures must themselves be valid --

    def test_valid_success_fixture_constructs(self):
        SemanticRuntimeResult(**_valid_success_kwargs())

    def test_valid_failure_fixture_constructs(self):
        SemanticRuntimeResult(**_valid_failure_kwargs())

    # -- attempt count: never zero, never more than two --

    def test_zero_attempts_rejected(self):
        with pytest.raises(ValueError, match="exactly one or two attempts"):
            SemanticRuntimeResult(**_valid_success_kwargs(attempts=()))

    def test_three_attempts_rejected(self):
        with pytest.raises(ValueError, match="exactly one or two attempts"):
            SemanticRuntimeResult(
                **_valid_success_kwargs(
                    attempts=(
                        _primary_failed_attempt(),
                        _fallback_failed_attempt(),
                        _primary_failed_attempt(),
                    )
                )
            )

    # -- one-attempt shape --

    def test_one_attempt_with_fallback_used_true_rejected(self):
        with pytest.raises(ValueError, match="fallback_used must be False"):
            SemanticRuntimeResult(**_valid_success_kwargs(fallback_used=True))

    def test_one_attempt_with_a_fallback_reason_rejected(self):
        with pytest.raises(ValueError, match="fallback_reason must be None"):
            SemanticRuntimeResult(
                **_valid_success_kwargs(
                    fallback_reason=SemanticRuntimeFallbackReason.TIMEOUT
                )
            )

    def test_one_attempt_naming_the_fallback_provider_rejected(self):
        with pytest.raises(ValueError, match="pinned primary"):
            SemanticRuntimeResult(
                **_valid_failure_kwargs(attempts=(_fallback_failed_attempt(),))
            )

    # -- two-attempt shape --

    def test_two_attempts_with_fallback_used_false_rejected(self):
        with pytest.raises(ValueError, match="fallback_used must be True"):
            SemanticRuntimeResult(
                **_valid_success_kwargs(
                    attempts=(_primary_failed_attempt(), _fallback_ok_attempt()),
                    fallback_used=False,
                    fallback_reason=SemanticRuntimeFallbackReason.TIMEOUT,
                    actual_provider=FALLBACK_PROVIDER,
                    actual_model=FALLBACK_MODEL,
                )
            )

    def test_two_attempts_with_no_fallback_reason_rejected(self):
        with pytest.raises(ValueError, match="fallback_reason must be set"):
            SemanticRuntimeResult(
                **_valid_success_kwargs(
                    attempts=(_primary_failed_attempt(), _fallback_ok_attempt()),
                    fallback_used=True,
                    fallback_reason=None,
                    actual_provider=FALLBACK_PROVIDER,
                    actual_model=FALLBACK_MODEL,
                )
            )

    def test_two_attempts_first_not_primary_rejected(self):
        with pytest.raises(ValueError, match="first attempt.*must be the .*pinned primary"):
            SemanticRuntimeResult(
                **_valid_failure_kwargs(
                    attempts=(_fallback_failed_attempt(), _fallback_failed_attempt()),
                    fallback_used=True,
                    fallback_reason=SemanticRuntimeFallbackReason.HTTP_ERROR,
                )
            )

    def test_two_attempts_second_not_fallback_rejected(self):
        with pytest.raises(ValueError, match="second attempt.*must be the .*pinned fallback"):
            SemanticRuntimeResult(
                **_valid_failure_kwargs(
                    attempts=(
                        _primary_failed_attempt(SemanticAttemptStatus.TIMEOUT),
                        _primary_failed_attempt(SemanticAttemptStatus.HTTP_ERROR),
                    ),
                    fallback_used=True,
                    fallback_reason=SemanticRuntimeFallbackReason.TIMEOUT,
                )
            )

    def test_two_attempts_first_ok_rejected(self):
        """A primary that succeeded ends the evaluation after one attempt;
        two attempts with the first already OK is a structurally impossible
        combination.
        """
        with pytest.raises(ValueError, match="cannot have status OK"):
            SemanticRuntimeResult(
                **_valid_success_kwargs(
                    attempts=(_primary_ok_attempt(), _fallback_ok_attempt()),
                    fallback_used=True,
                    fallback_reason=SemanticRuntimeFallbackReason.TIMEOUT,
                    actual_provider=FALLBACK_PROVIDER,
                    actual_model=FALLBACK_MODEL,
                )
            )

    def test_two_attempts_first_status_not_fallback_eligible_rejected(self):
        """PROVIDER_NOT_CONFIGURED is not in the fallback allowlist; a
        fallback must never have been attempted for it.
        """
        with pytest.raises(ValueError, match="not fallback-eligible"):
            SemanticRuntimeResult(
                **_valid_failure_kwargs(
                    attempts=(
                        _primary_failed_attempt(
                            SemanticAttemptStatus.PROVIDER_NOT_CONFIGURED
                        ),
                        _fallback_failed_attempt(),
                    ),
                    fallback_used=True,
                    fallback_reason=SemanticRuntimeFallbackReason.TIMEOUT,
                )
            )

    def test_fallback_reason_must_match_first_attempts_status(self):
        """The first attempt failed with TIMEOUT; claiming the fallback
        reason was RATE_LIMITED is a provenance lie.
        """
        with pytest.raises(ValueError, match="fallback_reason must be"):
            SemanticRuntimeResult(
                **_valid_failure_kwargs(
                    attempts=(
                        _primary_failed_attempt(SemanticAttemptStatus.TIMEOUT),
                        _fallback_failed_attempt(),
                    ),
                    fallback_used=True,
                    fallback_reason=SemanticRuntimeFallbackReason.RATE_LIMITED,
                )
            )

    # -- success shape --

    def test_one_attempt_success_with_non_ok_attempt_rejected(self):
        """CASE_REJECTED, not the TIMEOUT default: TIMEOUT is fallback-
        eligible, so a one-attempt result with it is rejected earlier, for a
        different reason, before this check is ever reached. CASE_REJECTED
        isolates the "success claims an attempt that is not OK" check alone.
        """
        with pytest.raises(ValueError, match="OK primary attempt"):
            SemanticRuntimeResult(
                **_valid_success_kwargs(
                    attempts=(
                        _primary_failed_attempt(SemanticAttemptStatus.CASE_REJECTED),
                    )
                )
            )

    def test_one_attempt_success_attributed_to_fallback_rejected(self):
        with pytest.raises(ValueError, match="pinned primary"):
            SemanticRuntimeResult(
                **_valid_success_kwargs(
                    actual_provider=FALLBACK_PROVIDER, actual_model=FALLBACK_MODEL,
                )
            )

    def test_two_attempt_success_with_non_ok_fallback_rejected(self):
        with pytest.raises(ValueError, match="OK fallback attempt"):
            SemanticRuntimeResult(
                **_valid_success_kwargs(
                    attempts=(_primary_failed_attempt(), _fallback_failed_attempt()),
                    fallback_used=True,
                    fallback_reason=SemanticRuntimeFallbackReason.TIMEOUT,
                    actual_provider=FALLBACK_PROVIDER,
                    actual_model=FALLBACK_MODEL,
                )
            )

    def test_two_attempt_success_attributed_to_primary_rejected(self):
        with pytest.raises(ValueError, match="pinned fallback"):
            SemanticRuntimeResult(
                **_valid_success_kwargs(
                    attempts=(_primary_failed_attempt(), _fallback_ok_attempt()),
                    fallback_used=True,
                    fallback_reason=SemanticRuntimeFallbackReason.TIMEOUT,
                    actual_provider=PRIMARY_PROVIDER,
                    actual_model=PRIMARY_MODEL,
                )
            )

    def test_success_without_confidence_rejected(self):
        with pytest.raises(ValueError, match="must carry a confidence"):
            SemanticRuntimeResult(**_valid_success_kwargs(confidence=None))

    def test_success_with_empty_reason_code_rejected(self):
        with pytest.raises(ValueError, match="non-empty reason_code"):
            SemanticRuntimeResult(**_valid_success_kwargs(reason_code=""))

    def test_success_with_none_reason_code_rejected(self):
        with pytest.raises(ValueError, match="non-empty reason_code"):
            SemanticRuntimeResult(**_valid_success_kwargs(reason_code=None))

    @pytest.mark.parametrize(
        "bad_reason_code",
        [123, True, {}, [], "", "   ", "\t"],
        ids=["int", "bool", "dict", "list", "empty_str", "spaces", "tab"],
    )
    def test_success_with_non_string_or_blank_reason_code_rejected(
        self, bad_reason_code
    ):
        """``reason_code`` must be exactly typed: a non-truthy check alone
        would let 123, True, {}, or whitespace-only strings slip through
        construction, only to fail later somewhere harder to diagnose (e.g.
        ``to_dict()`` / JSON serialization).
        """
        with pytest.raises(ValueError, match="non-empty reason_code"):
            SemanticRuntimeResult(
                **_valid_success_kwargs(reason_code=bad_reason_code)
            )

    # -- failure shape --

    def test_failure_with_an_ok_attempt_rejected(self):
        """A failure cannot have an OK attempt hiding in its provenance -
        an OK attempt is, by definition, a success.
        """
        with pytest.raises(ValueError, match="must not contain an OK attempt"):
            SemanticRuntimeResult(
                **_valid_failure_kwargs(attempts=(_primary_ok_attempt(),))
            )

    def test_failure_with_a_confidence_rejected(self):
        with pytest.raises(ValueError, match="must not carry a confidence"):
            SemanticRuntimeResult(
                **_valid_failure_kwargs(confidence=ConfidenceLevel.LOW)
            )

    def test_failure_with_a_reason_code_rejected(self):
        with pytest.raises(ValueError, match="must not carry a reason_code"):
            SemanticRuntimeResult(**_valid_failure_kwargs(reason_code="something"))

    def test_failure_with_nonempty_matched_attributes_rejected(self):
        with pytest.raises(ValueError, match="empty matched_attributes"):
            SemanticRuntimeResult(
                **_valid_failure_kwargs(matched_attributes=("brand",))
            )

    def test_failure_with_nonempty_conflicting_attributes_rejected(self):
        with pytest.raises(ValueError, match="empty conflicting_attributes"):
            SemanticRuntimeResult(
                **_valid_failure_kwargs(conflicting_attributes=("capacity",))
            )

    def test_failure_with_nonempty_missing_critical_attributes_rejected(self):
        with pytest.raises(ValueError, match="empty missing_critical_attributes"):
            SemanticRuntimeResult(
                **_valid_failure_kwargs(missing_critical_attributes=("suffix",))
            )

    # -- requested route and prompt version are always pinned --

    def test_requested_primary_provider_not_pinned_rejected(self):
        with pytest.raises(ValueError, match="pinned primary provider"):
            SemanticRuntimeResult(
                **_valid_success_kwargs(requested_primary_provider="openai")
            )

    def test_requested_primary_model_not_pinned_rejected(self):
        with pytest.raises(ValueError, match="pinned primary model"):
            SemanticRuntimeResult(
                **_valid_success_kwargs(requested_primary_model="gpt-4")
            )

    def test_prompt_version_not_pinned_rejected(self):
        with pytest.raises(ValueError, match="prompt_version must equal"):
            SemanticRuntimeResult(
                **_valid_success_kwargs(prompt_version="2.0")
            )

    def test_prompt_version_default_is_the_pinned_version(self):
        result = SemanticRuntimeResult(**_valid_success_kwargs())
        assert result.prompt_version == SEMANTIC_PROMPT_VERSION == "1.1"


class TestExactFieldTypesRejected:
    """A caller must not be able to construct a typed field with the wrong
    type and have construction succeed only for a later consumer (``to_dict``
    or anything else that trusts ``.value``) to crash.
    """

    def test_decision_as_plain_string_rejected(self):
        with pytest.raises(TypeError, match="decision must be SemanticDecision"):
            SemanticRuntimeResult(**_valid_success_kwargs(decision="MATCH"))

    def test_confidence_as_plain_string_rejected(self):
        with pytest.raises(TypeError, match="confidence must be ConfidenceLevel"):
            SemanticRuntimeResult(**_valid_success_kwargs(confidence="HIGH"))

    def test_error_type_as_plain_string_rejected(self):
        with pytest.raises(
            TypeError, match="error_type must be SemanticRuntimeErrorType"
        ):
            SemanticRuntimeResult(
                **_valid_failure_kwargs(error_type="PROVIDER_NOT_CONFIGURED")
            )

    def test_fallback_reason_as_plain_string_rejected(self):
        with pytest.raises(
            TypeError, match="fallback_reason must be SemanticRuntimeFallbackReason"
        ):
            SemanticRuntimeResult(
                **_valid_success_kwargs(
                    attempts=(_primary_failed_attempt(), _fallback_ok_attempt()),
                    fallback_used=True,
                    fallback_reason="TIMEOUT",
                    actual_provider=FALLBACK_PROVIDER,
                    actual_model=FALLBACK_MODEL,
                )
            )

    @pytest.mark.parametrize("value", [1, 0, "true", "false", None])
    def test_fallback_used_non_bool_rejected(self, value):
        with pytest.raises(TypeError, match="fallback_used must be bool"):
            SemanticRuntimeResult(**_valid_success_kwargs(fallback_used=value))

    @pytest.mark.parametrize(
        "field_name",
        ["matched_attributes", "conflicting_attributes", "missing_critical_attributes"],
    )
    def test_attribute_field_as_list_instead_of_tuple_rejected(self, field_name):
        with pytest.raises(TypeError, match=f"{field_name} must be a tuple"):
            SemanticRuntimeResult(
                **_valid_success_kwargs(**{field_name: ["brand"]})
            )

    @pytest.mark.parametrize(
        "field_name",
        ["matched_attributes", "conflicting_attributes", "missing_critical_attributes"],
    )
    def test_attribute_field_with_non_string_element_rejected(self, field_name):
        with pytest.raises(TypeError, match=rf"{field_name}\[0\] must be str"):
            SemanticRuntimeResult(
                **_valid_success_kwargs(**{field_name: (7,)})
            )

    def test_type_errors_are_checked_before_business_rules(self):
        """A wrong TYPE is reported as such, not masked by a value-shape
        error that happens to fire first for unrelated reasons - decision as
        a string is caught even on an otherwise-broken construction.
        """
        with pytest.raises(TypeError):
            SemanticRuntimeResult(
                **_valid_success_kwargs(decision="MATCH", attempts=())
            )


class TestErrorTypeBoundToAttemptProvenance:
    """A failure's ``error_type`` must be exactly what the failing attempt's
    status derives, via the same lookup tables the runtime itself uses to
    build a result. A mismatch is a provenance lie - e.g. the attempt
    genuinely timed out, but ``error_type`` claims MODEL_NOT_FOUND.
    """

    def test_one_attempt_failure_error_type_must_match_the_attempts_status(self):
        """CASE_REJECTED, not TIMEOUT: TIMEOUT is fallback-eligible, so a
        one-attempt result with that status is itself refused before
        error_type binding is ever reached (see
        TestOneAttemptFallbackEligibilityIsEnforced). CASE_REJECTED is a
        genuine non-fallback-eligible status, so a one-attempt result with
        it is real and this isolates the error_type-binding check alone.
        """
        with pytest.raises(ValueError, match="error_type must be"):
            SemanticRuntimeResult(
                **_valid_failure_kwargs(
                    attempts=(
                        _primary_failed_attempt(SemanticAttemptStatus.CASE_REJECTED),
                    ),
                    error_type=SemanticRuntimeErrorType.PRIMARY_MODEL_NOT_FOUND,
                )
            )

    def test_one_attempt_failure_error_type_matching_is_accepted(self):
        """The correctly-derived error_type constructs cleanly."""
        SemanticRuntimeResult(
            **_valid_failure_kwargs(
                attempts=(
                    _primary_failed_attempt(
                        SemanticAttemptStatus.INVALID_REQUEST_CONFIGURATION
                    ),
                ),
                error_type=(
                    SemanticRuntimeErrorType.PRIMARY_INVALID_REQUEST_CONFIGURATION
                ),
            )
        )

    def test_two_attempt_failure_error_type_must_match_the_second_attempts_status(
        self,
    ):
        with pytest.raises(ValueError, match="error_type must be"):
            SemanticRuntimeResult(
                **_valid_failure_kwargs(
                    attempts=(
                        _primary_failed_attempt(SemanticAttemptStatus.TIMEOUT),
                        _fallback_failed_attempt(SemanticAttemptStatus.HTTP_ERROR),
                    ),
                    fallback_used=True,
                    fallback_reason=SemanticRuntimeFallbackReason.TIMEOUT,
                    # The second (fallback) attempt failed with HTTP_ERROR;
                    # claiming FALLBACK_TIMEOUT instead is a provenance lie.
                    error_type=SemanticRuntimeErrorType.FALLBACK_TIMEOUT,
                )
            )

    def test_two_attempt_failure_error_type_matching_is_accepted(self):
        SemanticRuntimeResult(
            **_valid_failure_kwargs(
                attempts=(
                    _primary_failed_attempt(SemanticAttemptStatus.TIMEOUT),
                    _fallback_failed_attempt(SemanticAttemptStatus.HTTP_ERROR),
                ),
                fallback_used=True,
                fallback_reason=SemanticRuntimeFallbackReason.TIMEOUT,
                error_type=SemanticRuntimeErrorType.FALLBACK_HTTP_ERROR,
            )
        )

    def test_case_rejected_error_type_binding(self):
        """The new FU3A2D CASE_REJECTED status has its own bound error_type
        too - not folded into some other failure's classification.
        """
        SemanticRuntimeResult(
            **_valid_failure_kwargs(
                attempts=(_primary_failed_attempt(SemanticAttemptStatus.CASE_REJECTED),),
                error_type=SemanticRuntimeErrorType.PRIMARY_CASE_REJECTED,
            )
        )

        with pytest.raises(ValueError, match="error_type must be"):
            SemanticRuntimeResult(
                **_valid_failure_kwargs(
                    attempts=(
                        _primary_failed_attempt(SemanticAttemptStatus.CASE_REJECTED),
                    ),
                    error_type=SemanticRuntimeErrorType.PRIMARY_UNKNOWN_ERROR,
                )
            )

    def test_invalid_response_error_type_binding(self):
        """INVALID_RESPONSE is fallback-eligible (FU3A2D): a one-attempt
        failure carrying it is an impossible routing history and is refused
        at construction - see TestOneAttemptFallbackEligibilityIsEnforced.
        The two-attempt path is the genuine shape and keeps its exact
        error_type binding.
        """
        with pytest.raises(ValueError, match="fallback-eligible"):
            SemanticRuntimeResult(
                **_valid_failure_kwargs(
                    attempts=(
                        _primary_failed_attempt(SemanticAttemptStatus.INVALID_RESPONSE),
                    ),
                    error_type=SemanticRuntimeErrorType.PRIMARY_INVALID_RESPONSE,
                )
            )
        SemanticRuntimeResult(
            **_valid_failure_kwargs(
                attempts=(
                    _primary_failed_attempt(SemanticAttemptStatus.INVALID_RESPONSE),
                    _fallback_failed_attempt(
                        SemanticAttemptStatus.INVALID_RESPONSE
                    ),
                ),
                fallback_used=True,
                fallback_reason=SemanticRuntimeFallbackReason.INVALID_RESPONSE,
                error_type=SemanticRuntimeErrorType.FALLBACK_INVALID_RESPONSE,
            )
        )


class TestAllNonOkStatusesHaveCompleteErrorTypeMappings:
    """The two lookup tables ``__post_init__`` indexes directly (not via
    ``.get()``) must cover every non-OK ``SemanticAttemptStatus`` member, or
    a legitimate result carrying an uncovered status would raise KeyError
    from inside a supposedly-valid construction.
    """

    def test_primary_status_to_error_type_covers_every_non_ok_status(self):
        from product_intelligence.semantic.runtime import (
            _PRIMARY_STATUS_TO_ERROR_TYPE,
        )

        non_ok = set(SemanticAttemptStatus) - {SemanticAttemptStatus.OK}
        missing = non_ok - set(_PRIMARY_STATUS_TO_ERROR_TYPE)
        assert missing == set()

    def test_fallback_status_to_error_type_covers_every_non_ok_status(self):
        from product_intelligence.semantic.runtime import (
            _FALLBACK_STATUS_TO_ERROR_TYPE,
        )

        non_ok = set(SemanticAttemptStatus) - {SemanticAttemptStatus.OK}
        missing = non_ok - set(_FALLBACK_STATUS_TO_ERROR_TYPE)
        assert missing == set()


class TestOneAttemptFallbackEligibilityIsEnforced:
    """A one-attempt result is a genuine shape ``evaluate()`` can produce
    ONLY when the primary's failure status is NOT fallback-eligible.

    A primary failure named in ``PRIMARY_FALLBACK_ELIGIBLE_ERRORS`` always
    buys exactly one fallback attempt in the real routing (see
    ``SemanticRuntime.evaluate``) - so a one-attempt result claiming such a
    status is a fabricated routing history, not an outcome the runtime could
    ever actually produce, and ``__post_init__`` must refuse to construct it.

    This replaces the previous
    ``test_every_non_ok_status_constructs_a_valid_one_attempt_failure``,
    which wrongly asserted that EVERY non-OK status (including fallback-
    eligible ones like TIMEOUT) could validly appear in a one-attempt
    result. That assertion encoded an impossible state and is corrected
    here into two accurate proofs, split by fallback eligibility. Together
    they still exercise the direct-index lookup for every non-OK status,
    exactly as the original test intended.
    """

    @pytest.mark.parametrize(
        "status",
        [
            s
            for s in SemanticAttemptStatus
            if s is not SemanticAttemptStatus.OK
            and s.value not in PRIMARY_FALLBACK_ELIGIBLE_ERRORS
        ],
    )
    def test_non_fallback_eligible_status_constructs_a_valid_one_attempt_failure(
        self, status
    ):
        """Every status the runtime never sends to fallback is a genuine
        one-attempt failure shape and must construct cleanly.
        """
        from product_intelligence.semantic.runtime import (
            _PRIMARY_STATUS_TO_ERROR_TYPE,
        )

        SemanticRuntimeResult(
            **_valid_failure_kwargs(
                attempts=(_primary_failed_attempt(status),),
                error_type=_PRIMARY_STATUS_TO_ERROR_TYPE[status],
            )
        )

    @pytest.mark.parametrize(
        "status",
        [
            s
            for s in SemanticAttemptStatus
            if s is not SemanticAttemptStatus.OK
            and s.value in PRIMARY_FALLBACK_ELIGIBLE_ERRORS
        ],
    )
    def test_fallback_eligible_status_rejects_a_one_attempt_failure(self, status):
        """Every status the runtime always sends to fallback must be refused
        as a one-attempt result, no matter how the error_type is bound.
        """
        from product_intelligence.semantic.runtime import (
            _PRIMARY_STATUS_TO_ERROR_TYPE,
        )

        with pytest.raises(ValueError, match="fallback-eligible"):
            SemanticRuntimeResult(
                **_valid_failure_kwargs(
                    attempts=(_primary_failed_attempt(status),),
                    error_type=_PRIMARY_STATUS_TO_ERROR_TYPE[status],
                )
            )


class TestSemanticAttemptRejectsNonFiniteLatency:
    """SemanticAttempt.latency_ms must be a finite, non-negative number."""

    @pytest.mark.parametrize(
        "latency", [float("nan"), float("inf"), float("-inf")]
    )
    def test_non_finite_latency_rejected(self, latency: float):
        with pytest.raises(ValueError, match="finite"):
            SemanticAttempt(
                provider=PRIMARY_PROVIDER,
                model=PRIMARY_MODEL,
                status=SemanticAttemptStatus.OK,
                latency_ms=latency,
            )

    def test_finite_latency_accepted(self):
        SemanticAttempt(
            provider=PRIMARY_PROVIDER,
            model=PRIMARY_MODEL,
            status=SemanticAttemptStatus.OK,
            latency_ms=12.5,
        )


# =============================================================================
# Serialization safety
# =============================================================================


class TestResultSerialization:
    """No raw body, exception text, credential or chain-of-thought escapes."""

    def test_success_serialization_is_safe(self):
        """A successful result serializes to bounded, safe fields only."""
        result = evaluate(
            make_runtime(
                primary=primary_transport(responses={CASE_ID: make_response("MATCH")})
            )
        )

        payload = result.to_dict()
        text = str(payload).lower()

        assert "raw_output" not in payload
        assert "raw_response" not in payload
        assert "api_key" not in text
        assert "secret" not in text
        assert "authorization" not in text
        assert "traceback" not in text
        assert "reasoning" not in payload
        assert "chain_of_thought" not in payload

        assert payload["decision"] == "MATCH"
        assert payload["actual_provider"] == "amax"
        assert payload["prompt_version"] == "1.1"

    def test_failure_serialization_is_safe_and_carries_attempts(self):
        """A both-fail result still serializes both attempt records."""
        primary = primary_transport(failure_error_types={CASE_ID: "TIMEOUT"})
        fallback = fallback_transport(failure_error_types={CASE_ID: "HTTP_ERROR"})

        result = evaluate(make_runtime(primary=primary, fallback=fallback))
        payload = result.to_dict()

        assert payload["decision"] is None
        assert payload["actual_provider"] is None
        assert payload["actual_model"] is None
        assert payload["error_type"] == "FALLBACK_HTTP_ERROR"
        assert payload["fallback_reason"] == "TIMEOUT"
        assert [a["status"] for a in payload["attempts"]] == ["TIMEOUT", "HTTP_ERROR"]

        text = str(payload).lower()
        assert "api_key" not in text
        assert "secret" not in text
        assert "traceback" not in text

    def test_attempt_serialization_carries_only_bounded_fields(self):
        """An attempt record exposes exactly four safe fields."""
        attempt = SemanticAttempt(
            provider="amax",
            model="nemotron-3-super",
            status=SemanticAttemptStatus.TIMEOUT,
            latency_ms=4.0,
        )

        assert set(attempt.to_dict()) == {
            "provider",
            "model",
            "status",
            "latency_ms",
        }


# =============================================================================
# The fake transport really does model the transport contract
# =============================================================================


def test_transport_contract_shapes_are_distinguishable() -> None:
    """The runtime classifies outcomes structurally; the shapes must differ.

    A TransportFailure carries ``error_type`` and a TransportResult does not.
    If that ever stopped being true, the runtime would misclassify outcomes.
    """
    failure = TransportFailure(error_type="TIMEOUT")
    success = TransportResult(
        raw_output=make_response(),
        latency_ms=1.0,
        provider_status="200",
    )

    assert hasattr(failure, "error_type")
    assert not hasattr(success, "error_type")
    assert hasattr(success, "raw_output")
