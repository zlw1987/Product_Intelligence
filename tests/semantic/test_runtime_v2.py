"""Tests for the production Semantic V2 runtime (S2-C, group E).

Covers ``product_intelligence.semantic.runtime_v2``:

* the V2 pinned route is EXACT (the currently frozen qualified route
  identities, owned by the V2 contract; any deviation is rejected before
  any transport is built or called);
* fallback is permitted for EXECUTION FAILURE only (the frozen
  allowlist): MATCH / NO_MATCH / UNCERTAIN — at any confidence — never
  triggers a fallback; a non-allowlisted primary failure fails closed
  after exactly one attempt;
* the runtime-failure fallback provenance is exact (attempts in call
  order on the V2 pinned route, the bounded fallback reason derived from
  the primary status, the bounded final failure class, actual
  provider/model attribution);
* the strict structured V2 output is enforced at the runtime boundary
  (malformed JSON -> MALFORMED_JSON; unknown enum / incoherent
  decision-conflict combination -> SCHEMA_INVALID; model identity
  mismatch -> MODEL_IDENTITY_MISMATCH);
* no live network in tests (fake transports only); programming defects
  propagate (never converted into a transport failure).
"""

from __future__ import annotations

import json

import pytest

from product_intelligence.domain import ResearchRequest
from product_intelligence.research import (
    ExtractionMethod,
    ListingObservation,
    assess_listing_identity,
    derive_identity_state_v2,
    normalize_listing_observation,
)
from product_intelligence.research.semantic_v2 import (
    build_semantic_match_case_v2,
    build_v2_product_evidence_profile,
)
from product_intelligence.semantic.contract_v2 import SEMANTIC_PROMPT_VERSION_V2
from product_intelligence.semantic.runtime import (
    SemanticAttemptStatus,
    SemanticRuntimeErrorType,
    SemanticRuntimeFallbackReason,
)
from product_intelligence.semantic.runtime_v2 import (
    FALLBACK_MODEL_V2,
    FALLBACK_PROVIDER_V2,
    PRIMARY_FALLBACK_ELIGIBLE_ERRORS_V2,
    PRIMARY_MODEL_V2,
    PRIMARY_NON_FALLBACK_ERRORS_V2,
    PRIMARY_PROVIDER_V2,
    SEMANTIC_MAX_TOKENS_V2,
    SEMANTIC_TEMPERATURE_V2,
    V2_AUTHORITY_QUALIFIED,
    SemanticRuntimeConfigError,
    SemanticRuntimeConfigV2,
    SemanticRuntimeResultV2,
    SemanticRuntimeV2,
    get_default_runtime_v2,
    reset_default_runtime_v2,
)
from product_intelligence.semantic.transport import FakeSemanticModelTransport

REQUEST = ResearchRequest("ABC-123", "A test product")
NO_CTX = frozenset()


def _case(title="Has ABC-123 in the title"):
    observation = ListingObservation(
        source_url="https://example.com/product",
        extraction_method=ExtractionMethod.JSON_LD,
        product_title=title,
        brand_text=None,
        manufacturer_part_number_text=None,
        sku_text=None,
        price_text="100",
        currency_text="USD",
        availability_text="In stock",
        condition_text="New",
        seller_text=None,
    )
    normalized = normalize_listing_observation(observation)
    assessment = assess_listing_identity(REQUEST, normalized)
    context = derive_identity_state_v2(assessment)
    profile = build_v2_product_evidence_profile(
        observation=observation,
        context_provenances=NO_CTX,
        matched_facts=frozenset(),
    )
    return build_semantic_match_case_v2(
        case_id="candidate-test-0",
        request=REQUEST,
        assessment=assessment,
        context=context,
        product_evidence=profile,
        context_provenances=NO_CTX,
        reviewed_target_context=None,
    )


def _response_json(**overrides) -> str:
    body = {
        "decision": "MATCH",
        "confidence": "HIGH",
        "reason_code": "MATCH_DESCRIPTION_AND_ATTRIBUTES",
        "matched_attributes": [],
        "conflicting_attributes": [],
        "missing_critical_attributes": [],
        "conflict_classes": [],
    }
    body.update(overrides)
    return json.dumps(body)


def _fake(
    error: str | None = None,
    response: str | None = None,
    model: str | None = None,
) -> FakeSemanticModelTransport:
    """One bounded fake transport (zero network).

    ``error`` forces a TransportFailure of that error type for every call;
    ``response`` returns the raw V2 response string; ``model`` is the
    identity the provider reports (the runtime requires a proven model
    identity — the frozen V1 test discipline). Pass PRIMARY_MODEL_V2 for
    a primary-role fake and FALLBACK_MODEL_V2 for a fallback-role fake.
    """
    return FakeSemanticModelTransport(
        responses={"UNKNOWN": response} if response is not None else None,
        failure_error_types={"UNKNOWN": error} if error else None,
        provider_reported_model=model,
        case_ids=("UNKNOWN",),
    )


def _runtime(
    primary_error: str | None = None,
    primary_response: str | None = None,
    fallback_error: str | None = None,
    fallback_response: str | None = None,
):
    return SemanticRuntimeV2(
        primary_transport=_fake(
            primary_error, primary_response, PRIMARY_MODEL_V2
        ),
        fallback_transport=_fake(
            fallback_error, fallback_response, FALLBACK_MODEL_V2
        ),
    )


# ===========================================================================
# Route pins
# ===========================================================================


class TestV2RoutePins:
    def test_primary_route_exact(self) -> None:
        assert PRIMARY_PROVIDER_V2 == "amax"
        assert PRIMARY_MODEL_V2 == "qwen3.8-27b"

    def test_fallback_route_exact(self) -> None:
        assert FALLBACK_PROVIDER_V2 == "vllm-262k"
        assert FALLBACK_MODEL_V2 == "Qwen3.6-27B-262K"

    def test_generation_pins_exact(self) -> None:
        assert SEMANTIC_TEMPERATURE_V2 == 0.0
        assert SEMANTIC_MAX_TOKENS_V2 == 32768
        assert type(SEMANTIC_TEMPERATURE_V2) is float

    def test_a_different_route_is_rejected_before_any_transport(self) -> None:
        with pytest.raises(SemanticRuntimeConfigError, match="pinned"):
            SemanticRuntimeV2(
                config=SemanticRuntimeConfigV2(primary_model="other-model"),
                primary_transport=object(),
                fallback_transport=object(),
            )
        with pytest.raises(SemanticRuntimeConfigError, match="pinned"):
            SemanticRuntimeV2(
                config=SemanticRuntimeConfigV2(fallback_provider="other"),
                primary_transport=object(),
                fallback_transport=object(),
            )
        with pytest.raises(SemanticRuntimeConfigError, match="temperature"):
            SemanticRuntimeV2(
                config=SemanticRuntimeConfigV2(temperature=0),
                primary_transport=object(),
                fallback_transport=object(),
            )
        with pytest.raises(SemanticRuntimeConfigError, match="max_tokens"):
            SemanticRuntimeV2(
                config=SemanticRuntimeConfigV2(max_tokens=32768.0),
                primary_transport=object(),
                fallback_transport=object(),
            )

    def test_the_result_cannot_claim_a_foreign_route(self) -> None:
        case = _case()
        result = _runtime(primary_response=_response_json()).evaluate(case)
        assert result.requested_primary_provider == PRIMARY_PROVIDER_V2
        assert result.requested_primary_model == PRIMARY_MODEL_V2
        assert result.prompt_version == SEMANTIC_PROMPT_VERSION_V2
        assert result.actual_provider == PRIMARY_PROVIDER_V2
        assert result.actual_model == PRIMARY_MODEL_V2

    def test_fallback_allowlist_is_execution_failures_only(self) -> None:
        # The two sets are disjoint and the eligible set contains no
        # semantic-disagreement member (there is none by construction).
        assert PRIMARY_FALLBACK_ELIGIBLE_ERRORS_V2.isdisjoint(
            PRIMARY_NON_FALLBACK_ERRORS_V2
        )
        assert "CASE_REJECTED" in PRIMARY_NON_FALLBACK_ERRORS_V2
        assert "CASE_REJECTED" not in PRIMARY_FALLBACK_ELIGIBLE_ERRORS_V2

    def test_the_qualification_boundary_marker_is_false(self) -> None:
        # S2-C: the V2 route is NOT qualified for the new contract.
        assert V2_AUTHORITY_QUALIFIED is False


# ===========================================================================
# Fallback policy: execution failure only
# ===========================================================================


class TestFallbackPolicy:
    def test_match_does_not_trigger_fallback(self) -> None:
        primary = _fake(response=_response_json(decision="MATCH"), model=PRIMARY_MODEL_V2)
        fallback = _fake(model=FALLBACK_MODEL_V2)
        runtime = SemanticRuntimeV2(
            primary_transport=primary, fallback_transport=fallback
        )
        result = runtime.evaluate(_case())
        assert result.response.decision.value == "MATCH"
        assert result.fallback_used is False
        assert primary.call_count == 1
        assert fallback.call_count == 0
        assert len(result.attempts) == 1

    def test_no_match_does_not_trigger_fallback(self) -> None:
        primary = _fake(
            response=_response_json(
                decision="NO_MATCH",
                reason_code="NO_MATCH_CAPACITY",
                conflicting_attributes=[
                    {"dimension": "CAPACITY", "detail": "3840GB vs 1920GB"}
                ],
                conflict_classes=["CAPACITY"],
            ),
            model=PRIMARY_MODEL_V2,
        )
        fallback = _fake(model=FALLBACK_MODEL_V2)
        runtime = SemanticRuntimeV2(
            primary_transport=primary, fallback_transport=fallback
        )
        result = runtime.evaluate(_case())
        assert result.response.decision.value == "NO_MATCH"
        assert result.fallback_used is False
        assert fallback.call_count == 0

    def test_uncertain_does_not_trigger_fallback(self) -> None:
        primary = _fake(
            response=_response_json(
                decision="UNCERTAIN",
                confidence="MEDIUM",
                reason_code="UNCERTAIN_IDENTIFIER_RELATION",
                matched_attributes=[],
            ),
            model=PRIMARY_MODEL_V2,
        )
        fallback = _fake(model=FALLBACK_MODEL_V2)
        runtime = SemanticRuntimeV2(
            primary_transport=primary, fallback_transport=fallback
        )
        result = runtime.evaluate(_case())
        assert result.response.decision.value == "UNCERTAIN"
        assert result.fallback_used is False
        assert fallback.call_count == 0

    def test_low_confidence_does_not_trigger_fallback(self) -> None:
        primary = _fake(
            response=_response_json(
                decision="MATCH",
                confidence="LOW",
                reason_code="MATCH_DESCRIPTION_AND_ATTRIBUTES",
            ),
            model=PRIMARY_MODEL_V2,
        )
        fallback = _fake(model=FALLBACK_MODEL_V2)
        runtime = SemanticRuntimeV2(
            primary_transport=primary, fallback_transport=fallback
        )
        result = runtime.evaluate(_case())
        assert result.response.confidence.value == "LOW"
        assert result.fallback_used is False
        assert fallback.call_count == 0

    def test_execution_failure_triggers_fallback_exactly_once(self) -> None:
        primary = _fake(error="TIMEOUT")
        fallback = _fake(response=_response_json(), model=FALLBACK_MODEL_V2)
        runtime = SemanticRuntimeV2(
            primary_transport=primary, fallback_transport=fallback
        )
        result = runtime.evaluate(_case())
        assert result.response is not None
        assert result.fallback_used is True
        assert result.fallback_reason is SemanticRuntimeFallbackReason.TIMEOUT
        assert len(result.attempts) == 2
        assert fallback.call_count == 1
        assert result.actual_provider == FALLBACK_PROVIDER_V2
        assert result.actual_model == FALLBACK_MODEL_V2

    def test_non_fallback_eligible_failure_fails_closed_after_one_attempt(
        self,
    ) -> None:
        # CASE_REJECTED is a property of the case, not the provider:
        # no fallback, one attempt.
        primary = _fake(error="CASE_REJECTED")
        fallback = _fake(model=FALLBACK_MODEL_V2)
        runtime = SemanticRuntimeV2(
            primary_transport=primary, fallback_transport=fallback
        )
        result = runtime.evaluate(_case())
        assert result.response is None
        assert result.error_type is (
            SemanticRuntimeErrorType.PRIMARY_CASE_REJECTED
        )
        assert result.fallback_used is False
        assert fallback.call_count == 0
        assert len(result.attempts) == 1

    def test_unconfigured_provider_fails_closed_without_fallback(self, monkeypatch) -> None:
        # PROVIDER_NOT_CONFIGURED is a local configuration error: no
        # paid retry. (The env must be deterministically absent — a
        # configured workstation environment would otherwise build a
        # live transport.)
        monkeypatch.delenv("PI_SEMANTIC_AMAX_BASE_URL", raising=False)
        monkeypatch.delenv("PI_SEMANTIC_VLLM_262K_BASE_URL", raising=False)
        runtime = SemanticRuntimeV2()
        result = runtime.evaluate(_case())
        assert result.response is None
        assert result.error_type is (
            SemanticRuntimeErrorType.PROVIDER_NOT_CONFIGURED
        )
        assert result.fallback_used is False
        assert len(result.attempts) == 1
        assert result.attempts[0].status is (
            SemanticAttemptStatus.PROVIDER_NOT_CONFIGURED
        )

    def test_two_attempts_two_failures_provenance_exact(self) -> None:
        primary = _fake(error="RATE_LIMITED")
        fallback = _fake(error="HTTP_ERROR", model=FALLBACK_MODEL_V2)
        runtime = SemanticRuntimeV2(
            primary_transport=primary, fallback_transport=fallback
        )
        result = runtime.evaluate(_case())
        assert result.response is None
        # The bounded final failure class is mechanically bound to the
        # FINAL (fallback) attempt's status.
        assert result.error_type is SemanticRuntimeErrorType.FALLBACK_HTTP_ERROR
        assert result.fallback_used is True
        assert result.fallback_reason is SemanticRuntimeFallbackReason.RATE_LIMITED
        assert len(result.attempts) == 2
        assert result.attempts[0].provider == PRIMARY_PROVIDER_V2
        assert result.attempts[0].model == PRIMARY_MODEL_V2
        assert result.attempts[0].status is SemanticAttemptStatus.RATE_LIMITED
        assert result.attempts[1].provider == FALLBACK_PROVIDER_V2
        assert result.attempts[1].model == FALLBACK_MODEL_V2
        assert result.attempts[1].status is SemanticAttemptStatus.HTTP_ERROR
        assert result.actual_provider is None
        assert result.actual_model is None

    def test_fallback_failure_provenance_exact(self) -> None:
        primary = _fake(error="TIMEOUT")
        fallback = _fake(error="TIMEOUT", model=FALLBACK_MODEL_V2)
        runtime = SemanticRuntimeV2(
            primary_transport=primary, fallback_transport=fallback
        )
        result = runtime.evaluate(_case())
        assert result.response is None
        assert result.error_type is SemanticRuntimeErrorType.FALLBACK_TIMEOUT
        assert result.fallback_used is True
        assert result.fallback_reason is SemanticRuntimeFallbackReason.TIMEOUT

    def test_model_identity_mismatch_is_bounded(self) -> None:
        primary = FakeSemanticModelTransport(
            responses={"UNKNOWN": _response_json()},
            case_ids=("UNKNOWN",),
            provider_reported_model="some-other-model",
        )
        fallback = FakeSemanticModelTransport(
            responses={"UNKNOWN": _response_json()},
            case_ids=("UNKNOWN",),
            provider_reported_model=FALLBACK_MODEL_V2,
        )
        runtime = SemanticRuntimeV2(
            primary_transport=primary, fallback_transport=fallback
        )
        result = runtime.evaluate(_case())
        # The primary reported a different model: the primary attempt is
        # MODEL_IDENTITY_MISMATCH (fallback-eligible), the fallback
        # proved its identity and answered.
        assert result.response is not None
        assert result.fallback_used is True
        assert result.fallback_reason is (
            SemanticRuntimeFallbackReason.MODEL_IDENTITY_MISMATCH
        )
        assert result.actual_provider == FALLBACK_PROVIDER_V2

    def test_the_prompt_used_is_the_final_prompt_v2(self) -> None:
        captured: dict = {}

        class _CapturingTransport(FakeSemanticModelTransport):
            def complete(self, *, system_prompt, user_prompt, model, **kwargs):
                captured["system"] = system_prompt
                captured["user"] = user_prompt
                captured["model"] = model
                return super().complete(
                    system_prompt=system_prompt,
                    user_prompt=user_prompt,
                    model=model,
                    **kwargs,
                )

        transport = _CapturingTransport(
            responses={"UNKNOWN": _response_json()},
            case_ids=("UNKNOWN",),
            provider_reported_model=PRIMARY_MODEL_V2,
        )
        runtime = SemanticRuntimeV2(
            primary_transport=transport, fallback_transport=transport
        )
        case = _case()
        runtime.evaluate(case)
        from product_intelligence.semantic.contract_v2 import (
            SYSTEM_PROMPT_V2,
            build_semantic_prompt_v2,
        )

        expected = build_semantic_prompt_v2(case)
        assert captured["system"] == SYSTEM_PROMPT_V2
        assert captured["user"] == expected.user_prompt
        assert captured["model"] == PRIMARY_MODEL_V2


# ===========================================================================
# Strict structured output at the runtime boundary
# ===========================================================================


class TestStrictOutputAtRuntime:
    def test_malformed_json_is_bounded(self) -> None:
        runtime = _runtime(
            primary_response="not json", fallback_response=_response_json()
        )
        result = runtime.evaluate(_case())
        # The primary delivered no usable answer (bounded MALFORMED_
        # JSON); the fallback is a real (fake) answer, so the result
        # succeeds via the fallback with exact provenance.
        assert result.response is not None
        assert result.fallback_used is True
        assert result.fallback_reason is SemanticRuntimeFallbackReason.MALFORMED_JSON
        assert result.attempts[0].status is SemanticAttemptStatus.MALFORMED_JSON
        assert result.actual_provider == FALLBACK_PROVIDER_V2
        assert result.actual_model == FALLBACK_MODEL_V2

    def test_unknown_reason_code_is_schema_invalid(self) -> None:
        primary = _fake(response=_response_json(reason_code="exact_mpn_match"), model=PRIMARY_MODEL_V2)
        fallback = _fake(model=FALLBACK_MODEL_V2)
        runtime = SemanticRuntimeV2(
            primary_transport=primary, fallback_transport=fallback
        )
        result = runtime.evaluate(_case())
        assert result.response is None
        assert result.attempts[0].status is SemanticAttemptStatus.SCHEMA_INVALID

    def test_incoherent_decision_conflict_is_schema_invalid(self) -> None:
        # MATCH + ALWAYS_HARD conflict: incoherent under the frozen
        # rules -> SCHEMA_INVALID (never accepted as a valid response).
        primary = _fake(response=_response_json(conflict_classes=["CAPACITY"]), model=PRIMARY_MODEL_V2)
        fallback = _fake(model=FALLBACK_MODEL_V2)
        runtime = SemanticRuntimeV2(
            primary_transport=primary, fallback_transport=fallback
        )
        result = runtime.evaluate(_case())
        assert result.response is None
        assert result.attempts[0].status is SemanticAttemptStatus.SCHEMA_INVALID

    def test_extra_field_is_rejected(self) -> None:
        primary = _fake(response=_response_json(chain_of_thought="because"), model=PRIMARY_MODEL_V2)
        fallback = _fake(model=FALLBACK_MODEL_V2)
        runtime = SemanticRuntimeV2(
            primary_transport=primary, fallback_transport=fallback
        )
        result = runtime.evaluate(_case())
        assert result.response is None
        assert result.attempts[0].status is (
            SemanticAttemptStatus.MALFORMED_JSON
        )

    def test_accepted_response_carries_the_strict_structure(self) -> None:
        runtime = _runtime(
            primary_response=_response_json(
                decision="UNCERTAIN",
                confidence="MEDIUM",
                reason_code="UNCERTAIN_MISSING_CRITICAL_ATTRIBUTES",
                matched_attributes=[],
                missing_critical_attributes=["CAPACITY"],
            ),
            fallback_response=_response_json(),
        )
        result = runtime.evaluate(_case())
        assert result.response.decision.value == "UNCERTAIN"
        assert result.response.reason_code.value == (
            "UNCERTAIN_MISSING_CRITICAL_ATTRIBUTES"
        )
        assert result.response.missing_critical_attributes
        assert result.response.conflict_classes == frozenset()


# ===========================================================================
# Result invariants + defect propagation
# ===========================================================================


class TestResultInvariants:
    def test_a_fabricated_one_attempt_fallback_eligible_status_is_rejected(
        self,
    ) -> None:
        case = _case()
        with pytest.raises(ValueError, match="fallback-eligible"):
            SemanticRuntimeResultV2(
                case=case,
                requested_primary_provider=PRIMARY_PROVIDER_V2,
                requested_primary_model=PRIMARY_MODEL_V2,
                attempts=(
                    _attempt(1, "TIMEOUT"),
                ),
                fallback_used=False,
                fallback_reason=None,
                actual_provider=None,
                actual_model=None,
                response=None,
                error_type=SemanticRuntimeErrorType.PRIMARY_TIMEOUT,
                evaluation_started_at="2026-02-10T12:00:00Z",
                evaluation_finished_at="2026-02-10T12:00:01Z",
            )

    def test_a_failure_with_an_ok_attempt_is_rejected(self) -> None:
        case = _case()
        with pytest.raises(ValueError, match="OK attempt"):
            SemanticRuntimeResultV2(
                case=case,
                requested_primary_provider=PRIMARY_PROVIDER_V2,
                requested_primary_model=PRIMARY_MODEL_V2,
                attempts=(_attempt(1, "OK"),),
                fallback_used=False,
                fallback_reason=None,
                actual_provider=None,
                actual_model=None,
                response=None,
                error_type=SemanticRuntimeErrorType.PRIMARY_UNKNOWN_ERROR,
                evaluation_started_at="2026-02-10T12:00:00Z",
                evaluation_finished_at="2026-02-10T12:00:01Z",
            )

    def test_a_success_with_an_error_type_is_rejected(self) -> None:
        case = _case()
        runtime = _runtime(primary_response=_response_json())
        result = runtime.evaluate(case)
        with pytest.raises(ValueError, match="either a response or an error_type"):
            SemanticRuntimeResultV2(
                **{
                    **result.__dict__,
                    "error_type": SemanticRuntimeErrorType.PRIMARY_TIMEOUT,
                }
            )

    def test_a_foreign_case_cannot_be_wrapped(self) -> None:
        with pytest.raises(TypeError, match="case must be SemanticMatchCaseV2"):
            SemanticRuntimeResultV2(
                case="not a case",  # type: ignore[arg-type]
                requested_primary_provider=PRIMARY_PROVIDER_V2,
                requested_primary_model=PRIMARY_MODEL_V2,
                attempts=(),
                fallback_used=False,
                fallback_reason=None,
                actual_provider=None,
                actual_model=None,
                response=None,
                error_type=None,
                evaluation_started_at="2026-02-10T12:00:00Z",
                evaluation_finished_at="2026-02-10T12:00:01Z",
            )

    def test_programming_defects_propagate_and_never_fallback(self) -> None:
        class _Boom:
            def complete(self, **kwargs):
                raise RuntimeError("injected programming defect")

        fallback = FakeSemanticModelTransport()
        runtime = SemanticRuntimeV2(
            primary_transport=_Boom(), fallback_transport=fallback
        )
        with pytest.raises(RuntimeError, match="injected programming defect"):
            runtime.evaluate(_case())
        assert fallback.call_count == 0

    def test_default_runtime_is_lazy_and_resettable(self) -> None:
        reset_default_runtime_v2()
        runtime = get_default_runtime_v2()
        assert runtime is get_default_runtime_v2()
        reset_default_runtime_v2()
        assert get_default_runtime_v2() is not runtime


def _attempt(number: int, status_value: str):
    from product_intelligence.semantic.runtime import SemanticAttempt

    provider, model = (
        (PRIMARY_PROVIDER_V2, PRIMARY_MODEL_V2)
        if number == 1
        else (FALLBACK_PROVIDER_V2, FALLBACK_MODEL_V2)
    )
    return SemanticAttempt(
        provider=provider,
        model=model,
        status=SemanticAttemptStatus(status_value),
        latency_ms=1.0,
    )
