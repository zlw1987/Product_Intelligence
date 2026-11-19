"""Tests for the bounded per-attempt telemetry of the production
Semantic V2 runtime (SEMANTIC-V2-PERF Phase 0, A1).

Covers the V2 runtime's capture of the provider-reported, bounded
per-attempt measurements on ``SemanticAttempt``:

* the OK attempt carries the provider-reported token usage (the
  transport's bounded mapping) and the bounded finish reason — the
  exact provider values when they are within contract;
* unavailable telemetry is the EXPLICIT unknown (None), never zero and
  never invented: a transport that reports no usage projects to None;
  a failure attempt (no successful completion) carries None / None;
* out-of-contract telemetry projects to the explicit unknown — an
  out-of-grammar finish reason is NEVER carried raw (no unbounded
  provider text reaches the runtime result), and an out-of-contract
  usage mapping (negative / non-int counts) is refused, not
  zero-filled;
* the in-memory attempt keeps the measured float latency (the
  bounded persistence form — integer milliseconds — is applied by the
  record builder, never by the runtime);
* the V1 serialization surface of ``SemanticAttempt`` is UNCHANGED:
  ``to_dict`` still exposes exactly the four historical fields (the
  telemetry is the V2 instrumentation's, carried as bounded attempt
  attributes, and the V1 runtime sets none of them);
* routing / evaluation behavior is unchanged: the telemetry capture
  never alters the attempt status, the fallback decision, or the
  result classification (the same fakes produce the same outcomes as
  the frozen V2 suite).

Zero live work: bounded in-memory transport doubles only.
"""

from __future__ import annotations

import json

import pytest

from product_intelligence.domain import ResearchRequest
from product_intelligence.research import (
    ExtractionMethod,
    ListingObservation,
    assess_listing_identity,
    build_semantic_match_case_v2,
    build_v2_product_evidence_profile,
    derive_identity_state_v2,
    normalize_listing_observation,
)
from product_intelligence.semantic import transport as transport_module
from product_intelligence.semantic.runtime import (
    FINISH_REASON_MAX_LENGTH,
    SemanticAttempt,
    SemanticAttemptStatus,
    bounded_finish_reason,
    bounded_token_usage,
    is_bounded_finish_reason,
)
from product_intelligence.semantic.runtime_v2 import (
    FALLBACK_MODEL_V2,
    PRIMARY_MODEL_V2,
    PRIMARY_PROVIDER_V2,
    SemanticRuntimeV2,
)
from product_intelligence.semantic.transport import (
    FakeSemanticModelTransport,
    TransportFailure,
    TransportResult,
)

REQUEST = ResearchRequest("ABC-123", "A test product")

RESPONSE = json.dumps(
    {
        "decision": "MATCH",
        "confidence": "HIGH",
        "reason_code": "MATCH_DESCRIPTION_AND_ATTRIBUTES",
        "matched_attributes": [],
        "conflicting_attributes": [],
        "missing_critical_attributes": [],
        "conflict_classes": [],
    }
)


def _case():
    observation = ListingObservation(
        source_url="https://example.com/u1",
        extraction_method=ExtractionMethod.JSON_LD,
        product_title="ABC-123 1TB NVMe Drive",
        price_text="100",
        currency_text="USD",
        availability_text="In stock",
        condition_text="New",
    )
    assessment = assess_listing_identity(
        REQUEST, normalize_listing_observation(observation)
    )
    context = derive_identity_state_v2(assessment)
    profile = build_v2_product_evidence_profile(
        observation=assessment.normalized_listing.observation,
        context_provenances=frozenset(),
        matched_facts=frozenset(),
    )
    return build_semantic_match_case_v2(
        case_id="candidate-perf-test",
        request=REQUEST,
        assessment=assessment,
        context=context,
        product_evidence=profile,
        context_provenances=frozenset(),
        reviewed_target_context=None,
    )


class _TelemetryTransport(transport_module.SemanticModelTransport):
    """A bounded in-memory transport double with controllable
    provider-reported telemetry (no live work)."""

    def __init__(
        self,
        *,
        raw_output: str = RESPONSE,
        provider_reported_model: str | None = PRIMARY_MODEL_V2,
        token_usage: dict | None = {
            "prompt_tokens": 120,
            "completion_tokens": 340,
            "total_tokens": 460,
        },
        finish_reason: str | None = "stop",
        error_type: str | None = None,
    ) -> None:
        self._raw_output = raw_output
        self._provider_reported_model = provider_reported_model
        self._token_usage = token_usage
        self._finish_reason = finish_reason
        self._error_type = error_type
        self.calls = 0

    def complete(self, **kwargs):
        self.calls += 1
        if self._error_type is not None:
            return TransportFailure(error_type=self._error_type)
        return TransportResult(
            raw_output=self._raw_output,
            latency_ms=15.0,
            provider_status="200",
            provider_id="amax-test",
            model_id=PRIMARY_MODEL_V2,
            provider_reported_model=self._provider_reported_model,
            finish_reason=self._finish_reason,
            token_usage=self._token_usage,
        )


def _runtime(primary, fallback=None):
    return SemanticRuntimeV2(
        primary_transport=primary,
        fallback_transport=(
            fallback
            if fallback is not None
            else _TelemetryTransport(
                provider_reported_model=FALLBACK_MODEL_V2,
                error_type="CONNECTION_ERROR",
            )
        ),
    )


# ===========================================================================
# 1. Bounded capture (positive)
# ===========================================================================


class TestBoundedCapture:
    def test_ok_attempt_carries_the_provider_reported_telemetry(self):
        transport = _TelemetryTransport(
            token_usage={
                "prompt_tokens": 120,
                "completion_tokens": 340,
                "total_tokens": 460,
            },
            finish_reason="stop",
        )
        result = _runtime(transport).evaluate(_case())
        assert result.response is not None
        assert result.attempts[0].status is SemanticAttemptStatus.OK
        assert result.attempts[0].token_usage == {
            "prompt_tokens": 120,
            "completion_tokens": 340,
            "total_tokens": 460,
        }
        assert result.attempts[0].finish_reason == "stop"
        assert result.attempts[0].latency_ms >= 0.0

    @pytest.mark.parametrize("finish", ("stop", "length", "content_filter"))
    def test_grammar_bounded_finish_reasons_are_recorded_verbatim(self, finish):
        result = _runtime(
            _TelemetryTransport(finish_reason=finish)
        ).evaluate(_case())
        assert result.attempts[0].finish_reason == finish

    def test_max_length_finish_reason_is_recorded(self):
        finish = "a" * FINISH_REASON_MAX_LENGTH
        assert is_bounded_finish_reason(finish)
        result = _runtime(_TelemetryTransport(finish_reason=finish)).evaluate(
            _case()
        )
        assert result.attempts[0].finish_reason == finish

    def test_failed_attempt_after_fallback_carries_its_own_telemetry(self):
        # Primary fails (no successful completion -> explicit unknowns);
        # the fallback succeeds and carries ITS reported telemetry.
        primary = _TelemetryTransport(error_type="RATE_LIMITED")
        fallback = _TelemetryTransport(
            provider_reported_model=FALLBACK_MODEL_V2,
            token_usage={"prompt_tokens": 77, "completion_tokens": 88},
            finish_reason="length",
        )
        result = _runtime(primary, fallback).evaluate(_case())
        assert result.fallback_used is True
        assert len(result.attempts) == 2
        assert result.attempts[0].status is SemanticAttemptStatus.RATE_LIMITED
        assert result.attempts[0].token_usage is None
        assert result.attempts[0].finish_reason is None
        assert result.attempts[1].status is SemanticAttemptStatus.OK
        assert result.attempts[1].token_usage == {
            "prompt_tokens": 77,
            "completion_tokens": 88,
        }
        assert result.attempts[1].finish_reason == "length"


# ===========================================================================
# 2. The explicit unknown (never zero, never invented)
# ===========================================================================


class TestExplicitUnknown:
    def test_unreported_usage_is_none_never_zero(self):
        result = _runtime(
            _TelemetryTransport(token_usage=None, finish_reason="stop")
        ).evaluate(_case())
        assert result.attempts[0].status is SemanticAttemptStatus.OK
        assert result.attempts[0].token_usage is None
        assert result.attempts[0].finish_reason == "stop"

    def test_unreported_finish_reason_is_none(self):
        result = _runtime(
            _TelemetryTransport(
                token_usage={"prompt_tokens": 1, "completion_tokens": 2},
                finish_reason=None,
            )
        ).evaluate(_case())
        assert result.attempts[0].finish_reason is None
        assert result.attempts[0].token_usage == {
            "prompt_tokens": 1,
            "completion_tokens": 2,
        }

    def test_failure_attempt_carries_no_telemetry(self):
        # A normalized transport failure carries no successful
        # completion: both telemetry fields are the explicit unknown.
        result = _runtime(
            _TelemetryTransport(error_type="CONNECTION_ERROR"),
            fallback=_TelemetryTransport(
                provider_reported_model=FALLBACK_MODEL_V2,
                error_type="CONNECTION_ERROR",
            ),
        ).evaluate(_case())
        assert result.response is None
        assert result.error_type.value == "FALLBACK_CONNECTION_ERROR"
        for attempt in result.attempts:
            assert attempt.token_usage is None
            assert attempt.finish_reason is None
            assert attempt.latency_ms >= 0.0


# ===========================================================================
# 3. Out-of-contract telemetry projects to the explicit unknown
#    (never raw, never zero-filled, never a crash)
# ===========================================================================


class TestOutOfContractProjection:
    def test_out_of_grammar_finish_reason_is_none_never_raw(self):
        garbage = "The model thought these were the same product.!"
        result = _runtime(_TelemetryTransport(finish_reason=garbage)).evaluate(
            _case()
        )
        assert result.attempts[0].finish_reason is None
        # The raw provider text never reaches the result.
        assert garbage not in repr(result)

    def test_negative_usage_projects_to_none(self):
        result = _runtime(
            _TelemetryTransport(
                token_usage={"prompt_tokens": -3, "completion_tokens": 10}
            )
        ).evaluate(_case())
        assert result.attempts[0].token_usage is None

    def test_non_int_usage_projects_to_none(self):
        result = _runtime(
            _TelemetryTransport(
                token_usage={"prompt_tokens": "120", "completion_tokens": 5}
            )
        ).evaluate(_case())
        assert result.attempts[0].token_usage is None

    def test_bool_usage_projects_to_none(self):
        result = _runtime(
            _TelemetryTransport(
                token_usage={"prompt_tokens": True, "completion_tokens": 5}
            )
        ).evaluate(_case())
        assert result.attempts[0].token_usage is None

    def test_non_mapping_usage_projects_to_none(self):
        result = _runtime(
            _TelemetryTransport(token_usage=(120, 340))  # type: ignore[arg-type]
        ).evaluate(_case())
        assert result.attempts[0].token_usage is None

    def test_attempt_constructor_refuses_out_of_contract_telemetry(self):
        # Direct construction (a test double or a programming defect)
        # fails closed — the bounded grammar is enforced at the class,
        # not only at the projection.
        with pytest.raises(ValueError, match="finish_reason"):
            SemanticAttempt(
                provider=PRIMARY_PROVIDER_V2,
                model=PRIMARY_MODEL_V2,
                status=SemanticAttemptStatus.OK,
                latency_ms=1.0,
                finish_reason="NOT BOUNDED",
            )
        with pytest.raises(ValueError, match="token_usage"):
            SemanticAttempt(
                provider=PRIMARY_PROVIDER_V2,
                model=PRIMARY_MODEL_V2,
                status=SemanticAttemptStatus.OK,
                latency_ms=1.0,
                token_usage={"prompt_tokens": -1},
            )

    def test_bounded_helpers_project_to_the_explicit_unknown(self):
        assert bounded_finish_reason("stop") == "stop"
        assert bounded_finish_reason(None) is None
        assert bounded_finish_reason("STOP") is None
        assert bounded_finish_reason("a" * (FINISH_REASON_MAX_LENGTH + 1)) is None
        assert bounded_token_usage(None) is None
        assert bounded_token_usage({"prompt_tokens": 1}) == {
            "prompt_tokens": 1
        }
        assert bounded_token_usage({"prompt_tokens": -1}) is None
        assert bounded_token_usage({"prompt_tokens": 1.5}) is None
        assert bounded_token_usage([1, 2]) is None


# ===========================================================================
# 3b. SEMANTIC-V2-PERF-PHASE0-FU2 F2 — the provider's usage object
#     propagates as bounded telemetry through the REAL transport
#     (HTTP body -> OpenAISemanticTransport -> V2 runtime ->
#     SemanticAttempt), and F3 — the finish-reason grammar is
#     full-string (a trailing newline is the explicit unknown, never
#     a persisted value)
# ===========================================================================


class _RealTransportResp:
    def __init__(self, body: bytes) -> None:
        self.status = 200
        self._body = body

    def read(self):
        return self._body

    def __enter__(self):
        return self

    def __exit__(self, *a):
        pass


def _v2_body(usage: object | None, finish_reason: str | None = "stop") -> bytes:
    body: dict = {
        "model": PRIMARY_MODEL_V2,
        "choices": [
            {"message": {"content": RESPONSE}},
        ],
    }
    if finish_reason is not None:
        body["choices"][0]["finish_reason"] = finish_reason
    if usage is not None:
        body["usage"] = usage
    return json.dumps(body).encode("utf-8")


def _runtime_over_real_transport(
    monkeypatch, usage: object | None, finish_reason: str | None = "stop"
) -> object:
    """A V2 runtime whose primary IS the real OpenAISemanticTransport
    over a mocked HTTP 200 response carrying the given usage object
    (end-to-end: provider JSON -> transport -> runtime attempt)."""
    resp = _RealTransportResp(_v2_body(usage, finish_reason))

    class _Opener:
        def open(self, req, **kw):
            return resp

    monkeypatch.setattr(
        "urllib.request.build_opener", lambda *a, **kw: _Opener()
    )
    transport = transport_module.OpenAISemanticTransport(
        base_url="https://example.invalid/v1"
    )
    return _runtime(transport)


class TestUsagePropagationEndToEnd:
    """F2: the five provider usage shapes through the real transport
    into the SemanticAttempt telemetry (never fabricated, never
    inferred)."""

    def test_usage_missing_entirely_is_none(self, monkeypatch):
        result = _runtime_over_real_transport(monkeypatch, None).evaluate(
            _case()
        )
        assert result.attempts[0].status is SemanticAttemptStatus.OK
        assert result.attempts[0].token_usage is None

    def test_empty_usage_object_is_all_explicit_none(self, monkeypatch):
        result = _runtime_over_real_transport(monkeypatch, {}).evaluate(
            _case()
        )
        assert result.attempts[0].token_usage == {
            "prompt_tokens": None,
            "completion_tokens": None,
            "total_tokens": None,
        }

    def test_one_missing_token_field_stays_none_not_inferred_from_total(
        self, monkeypatch
    ):
        # completion_tokens absent while total IS reported: the missing
        # count reaches the attempt as the explicit unknown — never
        # inferred from total_tokens, never a fabricated zero.
        result = _runtime_over_real_transport(
            monkeypatch, {"prompt_tokens": 100, "total_tokens": 150}
        ).evaluate(_case())
        assert result.attempts[0].token_usage == {
            "prompt_tokens": 100,
            "completion_tokens": None,
            "total_tokens": 150,
        }
        assert result.attempts[0].token_usage["completion_tokens"] is None
        assert result.attempts[0].token_usage["completion_tokens"] != 50

    def test_explicit_zero_counts_remain_zero(self, monkeypatch):
        result = _runtime_over_real_transport(
            monkeypatch,
            {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0},
        ).evaluate(_case())
        assert result.attempts[0].token_usage == {
            "prompt_tokens": 0,
            "completion_tokens": 0,
            "total_tokens": 0,
        }

    def test_valid_positive_counts_are_preserved_verbatim(self, monkeypatch):
        result = _runtime_over_real_transport(
            monkeypatch,
            {
                "prompt_tokens": 100,
                "completion_tokens": 200,
                "total_tokens": 300,
            },
        ).evaluate(_case())
        assert result.attempts[0].token_usage == {
            "prompt_tokens": 100,
            "completion_tokens": 200,
            "total_tokens": 300,
        }


class TestFinishReasonFullStringValidation:
    """F3: the bounded grammar is full-string — a trailing newline
    (LF/CRLF) or any other stray character is the explicit unknown,
    and the accepted lowercase-identifier vocabulary is unchanged."""

    @pytest.mark.parametrize(
        "finish",
        ["stop", "length", "content_filter"],
    )
    def test_accepted_identifiers_remain_valid_and_recorded_verbatim(
        self, finish
    ):
        assert is_bounded_finish_reason(finish)
        assert bounded_finish_reason(finish) == finish
        result = _runtime(
            _TelemetryTransport(finish_reason=finish)
        ).evaluate(_case())
        assert result.attempts[0].finish_reason == finish

    @pytest.mark.parametrize(
        "finish",
        ["stop\n", "stop\r\n", "length\n", "content_filter\r\n", "stop "],
    )
    def test_trailing_newline_and_stray_characters_are_out_of_grammar(
        self, finish
    ):
        assert not is_bounded_finish_reason(finish)
        assert bounded_finish_reason(finish) is None

    def test_runtime_projects_a_trailing_newline_finish_reason_to_none(
        self, monkeypatch
    ):
        # End-to-end: the provider's "stop\n" reaches the real
        # transport, and the attempt carries the explicit unknown —
        # the raw value is never carried or reformatted.
        result = _runtime_over_real_transport(
            monkeypatch, None, finish_reason="stop\n"
        ).evaluate(_case())
        assert result.attempts[0].status is SemanticAttemptStatus.OK
        assert result.attempts[0].finish_reason is None
        assert "stop\n" not in repr(result)

    def test_attempt_constructor_refuses_a_trailing_newline_finish_reason(self):
        for finish in ("stop\n", "stop\r\n"):
            with pytest.raises(ValueError, match="finish_reason"):
                SemanticAttempt(
                    provider=PRIMARY_PROVIDER_V2,
                    model=PRIMARY_MODEL_V2,
                    status=SemanticAttemptStatus.OK,
                    latency_ms=1.0,
                    finish_reason=finish,
                )
        # The accepted vocabulary still constructs cleanly.
        for finish in ("stop", "length", "content_filter"):
            attempt = SemanticAttempt(
                provider=PRIMARY_PROVIDER_V2,
                model=PRIMARY_MODEL_V2,
                status=SemanticAttemptStatus.OK,
                latency_ms=1.0,
                finish_reason=finish,
            )
            assert attempt.finish_reason == finish

    def test_bounded_helpers_accept_partial_usage_shapes(self):
        # F2 at the projection seam: an explicit per-count None is IN
        # contract (the provider's usage object reported without that
        # count) — while an invalid count still refuses the whole
        # mapping (never zero-filled, never coerced).
        assert bounded_token_usage(
            {"prompt_tokens": 100, "completion_tokens": None}
        ) == {"prompt_tokens": 100, "completion_tokens": None}
        assert bounded_token_usage(
            {"prompt_tokens": 0, "completion_tokens": 0}
        ) == {"prompt_tokens": 0, "completion_tokens": 0}
        assert bounded_token_usage({"prompt_tokens": "100"}) is None
        assert bounded_token_usage({"prompt_tokens": -1}) is None


# ===========================================================================
# 4. The V1 surface and the routing behavior are unchanged
# ===========================================================================


class TestV1SurfaceUnchanged:
    def test_v1_attempt_to_dict_is_exactly_the_four_historical_fields(self):
        # The V1 serialization contract is frozen: the telemetry is a
        # bounded in-memory attribute, never a V1 serialization field.
        attempt = SemanticAttempt(
            provider="amax",
            model="qwen3.8-27b",
            status=SemanticAttemptStatus.TIMEOUT,
            latency_ms=4.0,
        )
        assert set(attempt.to_dict()) == {
            "provider",
            "model",
            "status",
            "latency_ms",
        }

    def test_v1_attempt_defaults_the_telemetry_to_the_explicit_unknown(self):
        # Every pre-existing V1 construction (four fields) is
        # unchanged: the new fields default to None.
        attempt = SemanticAttempt(
            provider="amax",
            model="qwen3.8-27b",
            status=SemanticAttemptStatus.OK,
            latency_ms=1.0,
        )
        assert attempt.token_usage is None
        assert attempt.finish_reason is None

    def test_v1_runtime_result_serialization_is_safe_and_unchanged(self):
        from product_intelligence.semantic.runtime import (
            PRIMARY_MODEL,
            PRIMARY_PROVIDER,
            SemanticRuntime,
        )

        v1_response = json.dumps(
            {
                "decision": "MATCH",
                "confidence": "HIGH",
                "matched_attributes": ["mpn"],
                "conflicting_attributes": [],
                "missing_critical_attributes": [],
                "reason_code": "exact_mpn_match",
            }
        )
        runtime = SemanticRuntime(
            primary_transport=FakeSemanticModelTransport(
                responses={"*": v1_response},
                case_ids=("*",),
                provider_reported_model=PRIMARY_MODEL,
            ),
            fallback_transport=FakeSemanticModelTransport(
                responses={"*": v1_response},
                case_ids=("*",),
                provider_reported_model="Qwen3.6-27B-262K",
            ),
        )
        result = runtime.evaluate(
            case_id="candidate-v1",
            target_mpn="ABC-123",
            target_description="A test product",
            candidate_title="ABC-123 1TB NVMe Drive",
            candidate_mpn_field="ABC-123",
        )
        payload = result.to_dict()
        # The V1 attempts serialize to the four historical fields only.
        for attempt_payload in payload["attempts"]:
            assert set(attempt_payload) == {
                "provider",
                "model",
                "status",
                "latency_ms",
            }
        # The V1 routing decision is unchanged by the shared class
        # extension: a valid primary response is final.
        assert payload["decision"] == "MATCH"
        assert payload["actual_provider"] == PRIMARY_PROVIDER

    def test_telemetry_capture_never_changes_the_routing_decision(self):
        # Same failure allowlist, same fallback behavior: the capture
        # is observation-only.
        primary = _TelemetryTransport(
            error_type="RATE_LIMITED",
            finish_reason="stop",
            token_usage={"prompt_tokens": 1, "completion_tokens": 1},
        )
        fallback = _TelemetryTransport(
            provider_reported_model=FALLBACK_MODEL_V2,
            finish_reason="length",
            token_usage={"prompt_tokens": 2, "completion_tokens": 2},
        )
        result = _runtime(primary, fallback).evaluate(_case())
        assert result.fallback_used is True
        assert result.fallback_reason.value == "RATE_LIMITED"
        assert result.response is not None
        assert result.actual_provider == "vllm-262k"
        # And a non-fallback-eligible failure still fails closed after
        # one attempt (the frozen routing rule): CASE_REJECTED is not
        # in the execution-failure allowlist.
        result = _runtime(
            _TelemetryTransport(error_type="CASE_REJECTED")
        ).evaluate(_case())
        assert result.fallback_used is False
        assert len(result.attempts) == 1
        assert result.error_type.value == "PRIMARY_CASE_REJECTED"
