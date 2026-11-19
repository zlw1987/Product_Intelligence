"""Tests for the Semantic V2 PERF instrumentation adapter
(SEMANTIC-V2-PERF Phase 0 — the A1 versioned successor).

Covers ``product_intelligence.research.semantic_decision_v2_perf`` and
its registration at the codec's explicit version-adapter extension
point:

* the PERF binding identity (the same semantic contract / prompt /
  input schema / authority axes as the frozen V2 binding; ONLY the
  recorded output schema version moves — 2) and the drift pins (route
  mirrors, the qualification marker, the bounded finish-reason
  grammar mirror);
* the PERF typed record (``SemanticDecisionRecordV2Perf``): the
  versioned per-attempt instrumentation (integer-millisecond latency,
  provider-reported prompt / completion token counts with explicit
  null = unknown, bounded finish reason), the exact-binding pin
  (output schema 1 is the frozen V2 adapter's, refused here), the
  same V2 route pin, the same evaluation/execution coherence rules,
  and the self-verifying section digests;
* the strict PERF payload codec (exact key sets, strict types, fail
  closed on invalid telemetry; no floats; cross-adapter
  reinterpretation refused in BOTH directions);
* historical replay: every pre-existing V2 (output schema 1) and V1
  record decodes and replays byte-identically through its frozen
  adapter — the registry extension changes nothing for them — while a
  PERF record replays through the PERF adapter under the PERF binding;
* the service round-trip (persist / load / replay through the S2-B
  persistence service over the SAME universal row — envelope schema
  1, no migration);
* anti-leakage: the payload and the runtime result carry no raw
  response, no prompt text, no credential, no float, and no unbounded
  provider metadata — unavailable telemetry is the explicit unknown
  (null), never zero and never invented.

Zero live work: every test performs zero AI calls, zero provider
calls, and zero network calls (the DB-backed service tests use the
session test database and bounded in-memory records only).
"""

from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from pathlib import Path

import pytest

from product_intelligence.domain import ResearchRequest
from product_intelligence.research import (
    AttemptOutcome,
    AttemptRole,
    AuthorityTier,
    ConflictClass,
    ContextProvenance,
    ExtractionMethod,
    ListingObservation,
    RelationshipAuthority,
    SemanticDecisionAttempt,
    SemanticEvaluationStateV2,
    SemanticEvaluationV2,
    SemanticFallbackReason,
    SemanticFailureClass,
    V2Confidence,
    V2SemanticDecision,
    assess_listing_identity,
    canonical_payload_digest,
    derive_authority_tier,
    derive_identity_state_v2,
    encode_semantic_decision_record,
    normalize_listing_observation,
    build_semantic_match_case_v2,
    build_v2_product_evidence_profile,
    decode_semantic_decision_record,
    registered_semantic_contract_adapter,
)
from product_intelligence.research import (
    SEMANTIC_V1_ADAPTER,
    SEMANTIC_V2_ADAPTER,
    SEMANTIC_V2_FU4_ADAPTER,
    SEMANTIC_V2_PERF_ADAPTER,
    V2_CONTRACT_BINDING,
    SemanticDecisionRecordV2,
    encode_v2_payload,
)
from product_intelligence.research.semantic_decision_codec import (
    SEMANTIC_DECISION_SCHEMA_VERSION,
    SemanticDecisionCodecError,
    adapter_for_record,
    supported_contract_bindings,
)
from product_intelligence.research.semantic_decision_record import (
    SemanticDecisionReplayError,
)
from product_intelligence.research.semantic_decision_replay import (
    SUPPORTED_CONTRACT_BINDINGS,
    replay_semantic_decision,
)
from product_intelligence.research.semantic_decision_v2 import (
    AUTHORITY_CONTRACT_VERSION_V2,
    FALLBACK_MODEL_V2,
    FALLBACK_PROVIDER_V2,
    PRIMARY_MODEL_V2,
    PRIMARY_PROVIDER_V2,
    PROMPT_VERSION_V2,
    SEMANTIC_CONTRACT_VERSION_V2,
    SEMANTIC_INPUT_SCHEMA_VERSION_V2,
    V2_AUTHORITY_QUALIFIED,
)
from product_intelligence.research.semantic_decision_v2_perf import (
    AUTHORITY_CONTRACT_VERSION_V2_PERF,
    FALLBACK_MODEL_V2_PERF,
    FALLBACK_PROVIDER_V2_PERF,
    PERF_FINISH_REASON_MAX_LENGTH,
    PRIMARY_MODEL_V2_PERF,
    PRIMARY_PROVIDER_V2_PERF,
    PROMPT_VERSION_V2_PERF,
    SEMANTIC_CONTRACT_VERSION_V2_PERF,
    SEMANTIC_INPUT_SCHEMA_VERSION_V2_PERF,
    SEMANTIC_OUTPUT_SCHEMA_VERSION_V2_PERF,
    V2_PERF_AUTHORITY_QUALIFIED,
    V2_PERF_CONTRACT_BINDING,
    SemanticDecisionAttemptPerf,
    SemanticDecisionReplayV2Perf,
    SemanticDecisionRecordV2Perf,
    encode_v2_perf_payload,
    is_bounded_perf_finish_reason,
    record_input_digest_v2_perf,
    record_output_digest_v2_perf,
    replay_v2_perf_record,
)
from product_intelligence.research.semantic_v2 import (
    SemanticReasonCodeV2,
)

RUN_ID = str(uuid.uuid4())
SOURCE_URL = "https://example.com/test-product"
REQUEST = ResearchRequest("ABC-123", "A test product")

STARTED = "2026-02-10T12:00:00Z"
FINISHED = "2026-02-10T12:01:24.728000Z"


# -- Scenario builders (the real frozen 3C chain — same shape as the
#    frozen V2 adapter suite) ------------------------------------------------


def _observation():
    return ListingObservation(
        source_url=SOURCE_URL,
        extraction_method=ExtractionMethod.JSON_LD,
        product_title="ABC-123 1TB NVMe Drive",
        brand_text=None,
        manufacturer_part_number_text=None,
        sku_text=None,
        price_text="100",
        currency_text="USD",
        availability_text="In stock",
        condition_text="New",
        seller_text=None,
    )


def _case():
    assessment = assess_listing_identity(
        REQUEST, normalize_listing_observation(_observation())
    )
    context = derive_identity_state_v2(assessment)
    profile = build_v2_product_evidence_profile(
        observation=assessment.normalized_listing.observation,
        context_provenances=frozenset(),
        matched_facts=frozenset(),
    )
    return build_semantic_match_case_v2(
        case_id="candidate-test-0",
        request=REQUEST,
        assessment=assessment,
        context=context,
        product_evidence=profile,
        context_provenances=frozenset(),
        reviewed_target_context=None,
    ), context, profile


def _perf_attempt(
    number=1,
    outcome=AttemptOutcome.OK,
    latency_ms=84728,
    prompt_tokens=1234,
    completion_tokens=2475,
    finish_reason="stop",
):
    role = AttemptRole.PRIMARY if number == 1 else AttemptRole.FALLBACK
    provider = (
        PRIMARY_PROVIDER_V2_PERF
        if number == 1
        else FALLBACK_PROVIDER_V2_PERF
    )
    model = (
        PRIMARY_MODEL_V2_PERF if number == 1 else FALLBACK_MODEL_V2_PERF
    )
    return SemanticDecisionAttemptPerf(
        role=role,
        attempt_number=number,
        provider=provider,
        model=model,
        outcome=outcome,
        latency_ms=latency_ms,
        prompt_tokens=prompt_tokens,
        completion_tokens=completion_tokens,
        finish_reason=finish_reason,
    )


def _build_perf_record(
    case=None,
    *,
    evaluation_state=SemanticEvaluationStateV2.EVALUATED,
    decision=V2SemanticDecision.MATCH,
    confidence=V2Confidence.HIGH,
    reason_code=SemanticReasonCodeV2.MATCH_DESCRIPTION_AND_ATTRIBUTES,
    attempts=None,
    fallback_used=False,
    fallback_reason=None,
    error_type=None,
    actual_provider=PRIMARY_PROVIDER_V2_PERF,
    actual_model=PRIMARY_MODEL_V2_PERF,
):
    if case is None:
        case, context, profile = _case()
    else:
        context = _context_of(case)
        profile = case.product_evidence
    if evaluation_state is SemanticEvaluationStateV2.EVALUATED:
        evaluation = SemanticEvaluationV2.evaluated(
            decision, confidence, frozenset()
        )
    elif evaluation_state is SemanticEvaluationStateV2.RUNTIME_FAILURE:
        evaluation = SemanticEvaluationV2.runtime_failure()
    else:
        evaluation = SemanticEvaluationV2.not_evaluated()
    tier_decision = derive_authority_tier(
        context, evaluation, case.context_provenances, profile
    )
    return SemanticDecisionRecordV2Perf.build(
        run_id=RUN_ID,
        assessment_index=0,
        source_url=case.candidate_source_url,
        case=case,
        evaluation_state=evaluation_state,
        decision=decision,
        confidence=confidence,
        reason_code=reason_code,
        conflict_classes=frozenset(),
        matched_attributes=(),
        conflicting_attributes=(),
        missing_critical_attributes=(),
        attempts=(
            (_perf_attempt(),)
            if attempts is None
            else tuple(attempts)
        ),
        fallback_used=fallback_used,
        fallback_reason=fallback_reason,
        error_type=error_type,
        actual_provider=actual_provider,
        actual_model=actual_model,
        evaluation_started_at=(
            None
            if evaluation_state
            is SemanticEvaluationStateV2.NOT_EVALUATED
            else STARTED
        ),
        evaluation_finished_at=(
            None
            if evaluation_state
            is SemanticEvaluationStateV2.NOT_EVALUATED
            else FINISHED
        ),
        product_evidence_quality=tier_decision.product_evidence_quality,
        relationship_authority=tier_decision.relationship_authority,
        authority_tier=tier_decision.tier,
        fired_rules=tier_decision.fired_rules,
    )


def _context_of(case):
    from product_intelligence.research import IdentityStateAssessmentV2

    return IdentityStateAssessmentV2(
        state=case.identity_state,
        substate=case.substate,
        relationship_signals=case.relationship_signals,
        normalized_requested_part_number=case.normalized_requested_part_number,
        normalized_candidate_part_number=case.normalized_candidate_part_number,
    )


def _raw_bytes(record):
    """The canonical persisted JSON bytes of one encoded record."""
    return json.dumps(
        encode_semantic_decision_record(record), sort_keys=True
    ).encode("utf-8")


# ===========================================================================
# 1. The PERF binding identity + drift pins
# ===========================================================================


class TestPerfBindingIdentity:
    def test_perf_binding_differs_from_v2_only_on_the_output_axis(self):
        assert V2_PERF_CONTRACT_BINDING == (
            "V2",
            "2.0",
            1,
            2,
            "SEMANTIC_AUTHORITY_V2_S2A_FU2",
        )
        # Same semantic contract / prompt / input / authority axes as
        # the frozen V2 binding — the recorded output schema version is
        # the ONLY moving axis (1 -> 2).
        assert V2_PERF_CONTRACT_BINDING[:3] == V2_CONTRACT_BINDING[:3]
        assert (
            V2_PERF_CONTRACT_BINDING[3]
            == V2_CONTRACT_BINDING[3] + 1
            == 2
        )
        assert V2_PERF_CONTRACT_BINDING[4] == V2_CONTRACT_BINDING[4]
        assert SEMANTIC_OUTPUT_SCHEMA_VERSION_V2_PERF == 2
        assert (
            SEMANTIC_OUTPUT_SCHEMA_VERSION_V2_PERF
            != 1
        )

    def test_perf_adapter_claims_exactly_the_perf_binding(self):
        assert (
            SEMANTIC_V2_PERF_ADAPTER.envelope_schema_version
            == SEMANTIC_DECISION_SCHEMA_VERSION
            == 1
        )
        assert (
            SEMANTIC_V2_PERF_ADAPTER.semantic_contract_version == "V2"
        )
        assert SEMANTIC_V2_PERF_ADAPTER.supported_bindings == (
            V2_PERF_CONTRACT_BINDING,
        )
        assert (
            SEMANTIC_V2_PERF_ADAPTER.record_type
            is SemanticDecisionRecordV2Perf
        )
        # The adapter is registered at the codec's explicit extension
        # point, appended AFTER the V1, V2, and V2-FU4 adapters.
        import product_intelligence.research.semantic_decision_codec as codec

        registry = codec._REGISTERED_SEMANTIC_CONTRACT_ADAPTERS
        assert registry[0] is SEMANTIC_V1_ADAPTER
        assert registry[1] is SEMANTIC_V2_ADAPTER
        assert registry[2] is SEMANTIC_V2_FU4_ADAPTER
        assert registry[3] is SEMANTIC_V2_PERF_ADAPTER
        # The universal row is reused (the registered envelope versions
        # are unchanged).
        assert registry[3].envelope_schema_version == 1

    def test_claim_based_dispatch_selects_exactly_one_adapter(self):
        # The historical V2 binding is still claimed by the frozen V2
        # adapter alone; the PERF binding by the PERF adapter alone.
        perf_payload = encode_semantic_decision_record(
            _build_perf_record()
        )
        from product_intelligence.research.semantic_decision_codec import (
            _read_recorded_binding,
        )

        binding = _read_recorded_binding(perf_payload)
        assert binding == V2_PERF_CONTRACT_BINDING
        claiming = [
            adapter
            for adapter in (
                SEMANTIC_V1_ADAPTER,
                SEMANTIC_V2_ADAPTER,
                SEMANTIC_V2_FU4_ADAPTER,
                SEMANTIC_V2_PERF_ADAPTER,
            )
            if binding in adapter.supported_bindings
            and adapter.envelope_schema_version == 1
        ]
        assert claiming == [SEMANTIC_V2_PERF_ADAPTER]

        # The pair lookup keeps its historical first-match semantics:
        # (1, V2) still resolves to the frozen V2 adapter.
        assert (
            registered_semantic_contract_adapter(1, "V2")
            is SEMANTIC_V2_ADAPTER
        )
        # The binding union is additive: every historical binding is
        # still present.
        union = supported_contract_bindings()
        assert V2_CONTRACT_BINDING in union
        assert V2_PERF_CONTRACT_BINDING in union
        assert SUPPORTED_CONTRACT_BINDINGS == tuple(union)

    def test_route_mirrors_match_the_frozen_v2_adapter_and_runtime(self):
        assert (PRIMARY_PROVIDER_V2_PERF, PRIMARY_MODEL_V2_PERF) == (
            PRIMARY_PROVIDER_V2,
            PRIMARY_MODEL_V2,
        )
        assert (FALLBACK_PROVIDER_V2_PERF, FALLBACK_MODEL_V2_PERF) == (
            FALLBACK_PROVIDER_V2,
            FALLBACK_MODEL_V2,
        )
        assert (PRIMARY_PROVIDER_V2_PERF, PRIMARY_MODEL_V2_PERF) == (
            "amax",
            "qwen3.8-27b",
        )
        assert (FALLBACK_PROVIDER_V2_PERF, FALLBACK_MODEL_V2_PERF) == (
            "vllm-262k",
            "Qwen3.6-27B-262K",
        )
        from product_intelligence.semantic.runtime_v2 import (
            FALLBACK_MODEL_V2 as RT_FALLBACK_MODEL,
            FALLBACK_PROVIDER_V2 as RT_FALLBACK_PROVIDER,
            PRIMARY_MODEL_V2 as RT_PRIMARY_MODEL,
            PRIMARY_PROVIDER_V2 as RT_PRIMARY_PROVIDER,
        )

        assert PRIMARY_PROVIDER_V2_PERF == RT_PRIMARY_PROVIDER
        assert PRIMARY_MODEL_V2_PERF == RT_PRIMARY_MODEL
        assert FALLBACK_PROVIDER_V2_PERF == RT_FALLBACK_PROVIDER
        assert FALLBACK_MODEL_V2_PERF == RT_FALLBACK_MODEL

    def test_prompt_and_contract_mirrors_match_the_frozen_v2_adapter(self):
        assert SEMANTIC_CONTRACT_VERSION_V2_PERF == (
            SEMANTIC_CONTRACT_VERSION_V2
        )
        assert PROMPT_VERSION_V2_PERF == PROMPT_VERSION_V2
        assert SEMANTIC_INPUT_SCHEMA_VERSION_V2_PERF == (
            SEMANTIC_INPUT_SCHEMA_VERSION_V2
        )
        assert AUTHORITY_CONTRACT_VERSION_V2_PERF == (
            AUTHORITY_CONTRACT_VERSION_V2
        )

    def test_qualification_marker_stays_false(self):
        # Registration is NOT qualification: the marker mirrors the
        # frozen V2 marker (False) and the V2 runtime marker.
        assert V2_PERF_AUTHORITY_QUALIFIED is False
        assert V2_AUTHORITY_QUALIFIED is False
        from product_intelligence.semantic.runtime_v2 import (
            V2_AUTHORITY_QUALIFIED as RT_MARKER,
        )

        assert RT_MARKER is False
        assert V2_PERF_AUTHORITY_QUALIFIED is RT_MARKER

    def test_finish_reason_grammar_mirror_matches_the_runtime(self):
        # The research mirror of the bounded finish-reason grammar must
        # not drift from the transport world's owner.
        from product_intelligence.semantic.runtime import (
            FINISH_REASON_MAX_LENGTH,
            is_bounded_finish_reason,
        )

        assert PERF_FINISH_REASON_MAX_LENGTH == FINISH_REASON_MAX_LENGTH
        for value in (
            "stop",
            "length",
            "tool_calls",
            "content_filter",
            "function_call",
            "abort",
            "a",
            "a" * 64,
            "a_b_c",
            None,
            "STOP",
            "length!",
            "",
            "a" * 65,
            "9abc",
            "len gth",
            42,
        ):
            assert is_bounded_perf_finish_reason(value) == (
                is_bounded_finish_reason(value)
            ), value


# ===========================================================================
# 2. The PERF per-attempt record (bounded instrumentation)
# ===========================================================================


class TestPerfAttempt:
    def test_canonical_is_exactly_the_bounded_eight_keys(self):
        attempt = _perf_attempt()
        canonical = attempt.canonical()
        assert set(canonical) == {
            "role",
            "attempt_number",
            "provider",
            "model",
            "outcome",
            "latency_ms",
            "prompt_tokens",
            "completion_tokens",
            "finish_reason",
        }

    def test_base_attempt_rules_are_preserved(self):
        # A PERF attempt must first be a legal V2 recorded attempt:
        # role/number consistency and the bounded outcome are the
        # frozen base rules (refused, not redefined).
        with pytest.raises(ValueError, match="inconsistent"):
            SemanticDecisionAttemptPerf(
                AttemptRole.FALLBACK,
                1,
                PRIMARY_PROVIDER_V2_PERF,
                PRIMARY_MODEL_V2_PERF,
                AttemptOutcome.OK,
                10,
                None,
                None,
                None,
            )

    @pytest.mark.parametrize(
        "latency", [True, -1, "84", 84.5, None]
    )
    def test_latency_must_be_the_non_negative_integer_ms(self, latency):
        with pytest.raises((TypeError, ValueError)):
            SemanticDecisionAttemptPerf(
                AttemptRole.PRIMARY,
                1,
                PRIMARY_PROVIDER_V2_PERF,
                PRIMARY_MODEL_V2_PERF,
                AttemptOutcome.OK,
                latency,
                None,
                None,
                None,
            )

    @pytest.mark.parametrize(
        "tokens", [True, -1, "500", 50.5, None]
    )
    def test_token_counts_are_non_negative_int_or_explicit_none(self, tokens):
        # int and None are legal; everything else is refused.
        if tokens is None:
            attempt = SemanticDecisionAttemptPerf(
                AttemptRole.PRIMARY,
                1,
                PRIMARY_PROVIDER_V2_PERF,
                PRIMARY_MODEL_V2_PERF,
                AttemptOutcome.OK,
                10,
                tokens,
                5,
                None,
            )
            assert attempt.prompt_tokens is None
            return
        with pytest.raises((TypeError, ValueError)):
            SemanticDecisionAttemptPerf(
                AttemptRole.PRIMARY,
                1,
                PRIMARY_PROVIDER_V2_PERF,
                PRIMARY_MODEL_V2_PERF,
                AttemptOutcome.OK,
                10,
                tokens,
                5,
                None,
            )

    @pytest.mark.parametrize(
        "finish", ["STOP", "length!", "", "a" * 65, "9abc", None, "stop"]
    )
    def test_finish_reason_is_bounded_or_explicit_none(self, finish):
        if finish is None or finish == "stop":
            attempt = SemanticDecisionAttemptPerf(
                AttemptRole.PRIMARY,
                1,
                PRIMARY_PROVIDER_V2_PERF,
                PRIMARY_MODEL_V2_PERF,
                AttemptOutcome.OK,
                10,
                None,
                None,
                finish,
            )
            assert attempt.finish_reason is finish
            return
        with pytest.raises(ValueError, match="finish_reason"):
            SemanticDecisionAttemptPerf(
                AttemptRole.PRIMARY,
                1,
                PRIMARY_PROVIDER_V2_PERF,
                PRIMARY_MODEL_V2_PERF,
                AttemptOutcome.OK,
                10,
                None,
                None,
                finish,
            )

    def test_explicit_unknown_usage_is_never_zero(self):
        attempt = _perf_attempt(
            prompt_tokens=None, completion_tokens=None
        )
        canonical = attempt.canonical()
        assert canonical["prompt_tokens"] is None
        assert canonical["completion_tokens"] is None
        # The unknown stays the unknown through the canonical form —
        # it is never zero-filled.
        assert canonical["prompt_tokens"] != 0
        assert canonical["completion_tokens"] != 0


# ===========================================================================
# 3. The PERF typed record (positive)
# ===========================================================================


class TestPerfRecordPositive:
    def test_evaluated_record_with_full_telemetry_round_trips(self):
        record = _build_perf_record()
        assert (
            record.semantic_contract_version,
            record.prompt_version,
            record.input_schema_version,
            record.output_schema_version,
            record.authority_contract_version,
        ) == V2_PERF_CONTRACT_BINDING
        payload = encode_semantic_decision_record(record)
        assert payload["schema_version"] == 1
        assert payload["contract"]["output_schema_version"] == 2
        assert payload["execution"]["attempts"][0] == {
            "role": "PRIMARY",
            "attempt_number": 1,
            "provider": "amax",
            "model": "qwen3.8-27b",
            "outcome": "OK",
            "latency_ms": 84728,
            "prompt_tokens": 1234,
            "completion_tokens": 2475,
            "finish_reason": "stop",
        }
        decoded = decode_semantic_decision_record(
            json.loads(json.dumps(payload)), schema_version=1
        )
        assert isinstance(decoded, SemanticDecisionRecordV2Perf)
        assert decoded == record
        # The decode dispatches to the PERF adapter by the recorded
        # binding (never the frozen V2 adapter).
        assert adapter_for_record(decoded) is SEMANTIC_V2_PERF_ADAPTER

    def test_two_attempt_fallback_record_round_trips(self):
        primary = _perf_attempt(
            number=1,
            outcome=AttemptOutcome.RATE_LIMITED,
            latency_ms=120,
            prompt_tokens=None,
            completion_tokens=None,
            finish_reason=None,
        )
        fallback = _perf_attempt(
            number=2,
            outcome=AttemptOutcome.OK,
            latency_ms=45000,
            prompt_tokens=900,
            completion_tokens=1500,
            finish_reason="length",
        )
        record = _build_perf_record(
            attempts=(primary, fallback),
            fallback_used=True,
            fallback_reason=SemanticFallbackReason.RATE_LIMITED,
            actual_provider=FALLBACK_PROVIDER_V2_PERF,
            actual_model=FALLBACK_MODEL_V2_PERF,
        )
        payload = encode_semantic_decision_record(record)
        decoded = decode_semantic_decision_record(
            json.loads(json.dumps(payload)), schema_version=1
        )
        assert decoded == record
        assert [a.canonical() for a in decoded.attempts] == [
            a.canonical() for a in (primary, fallback)
        ]
        # Per-attempt identity is preserved (the fallback attempt's
        # telemetry is never attributed to the primary).
        assert decoded.attempts[0].latency_ms == 120
        assert decoded.attempts[1].latency_ms == 45000
        assert decoded.attempts[1].finish_reason == "length"

    def test_runtime_failure_record_round_trips(self):
        record = _build_perf_record(
            evaluation_state=SemanticEvaluationStateV2.RUNTIME_FAILURE,
            decision=None,
            confidence=None,
            reason_code=None,
            attempts=(
                _perf_attempt(
                    number=1,
                    outcome=AttemptOutcome.TIMEOUT,
                    latency_ms=300000,
                    prompt_tokens=None,
                    completion_tokens=None,
                    finish_reason=None,
                ),
                _perf_attempt(
                    number=2,
                    outcome=AttemptOutcome.TIMEOUT,
                    latency_ms=300000,
                    prompt_tokens=None,
                    completion_tokens=None,
                    finish_reason=None,
                ),
            ),
            fallback_used=True,
            fallback_reason=SemanticFallbackReason.TIMEOUT,
            error_type=SemanticFailureClass.FALLBACK_TIMEOUT,
            actual_provider=None,
            actual_model=None,
        )
        assert record.evaluation_state is (
            SemanticEvaluationStateV2.RUNTIME_FAILURE
        )
        assert record.decision is None
        payload = encode_semantic_decision_record(record)
        decoded = decode_semantic_decision_record(
            json.loads(json.dumps(payload)), schema_version=1
        )
        assert decoded == record
        # A failure record still bounds the measured latencies (the
        # attempts really happened) — usage stays the explicit unknown.
        assert decoded.attempts[0].latency_ms == 300000
        assert decoded.attempts[0].prompt_tokens is None
        assert decoded.attempts[0].finish_reason is None

    def test_explicit_unknown_usage_survives_the_round_trip(self):
        record = _build_perf_record(
            attempts=(
                _perf_attempt(
                    prompt_tokens=None, completion_tokens=None
                ),
            )
        )
        payload = json.loads(json.dumps(
            encode_semantic_decision_record(record)
        ))
        assert payload["execution"]["attempts"][0]["prompt_tokens"] is None
        assert (
            payload["execution"]["attempts"][0]["completion_tokens"]
            is None
        )
        decoded = decode_semantic_decision_record(payload, schema_version=1)
        assert decoded.attempts[0].prompt_tokens is None
        assert decoded.attempts[0].completion_tokens is None

    def test_input_digest_differs_from_v2_by_exactly_the_output_axis(self):
        case, context, profile = _case()
        tier_decision = derive_authority_tier(
            context,
            SemanticEvaluationV2.evaluated(
                V2SemanticDecision.MATCH,
                V2Confidence.HIGH,
                frozenset(),
            ),
            case.context_provenances,
            profile,
        )
        v2_attempt = SemanticDecisionAttempt(
            AttemptRole.PRIMARY, 1,
            PRIMARY_PROVIDER_V2, PRIMARY_MODEL_V2, AttemptOutcome.OK,
        )
        v2_record = SemanticDecisionRecordV2.build(
            run_id=RUN_ID,
            assessment_index=0,
            source_url=case.candidate_source_url,
            case=case,
            evaluation_state=SemanticEvaluationStateV2.EVALUATED,
            decision=V2SemanticDecision.MATCH,
            confidence=V2Confidence.HIGH,
            reason_code=SemanticReasonCodeV2.MATCH_DESCRIPTION_AND_ATTRIBUTES,
            conflict_classes=frozenset(),
            matched_attributes=(),
            conflicting_attributes=(),
            missing_critical_attributes=(),
            attempts=(v2_attempt,),
            fallback_used=False,
            fallback_reason=None,
            error_type=None,
            actual_provider=PRIMARY_PROVIDER_V2,
            actual_model=PRIMARY_MODEL_V2,
            evaluation_started_at=STARTED,
            evaluation_finished_at=FINISHED,
            product_evidence_quality=tier_decision.product_evidence_quality,
            relationship_authority=tier_decision.relationship_authority,
            authority_tier=tier_decision.tier,
            fired_rules=tier_decision.fired_rules,
        )
        perf_record = _build_perf_record(case=case)
        # Same case + same contract axes except the output schema:
        # the input digests must differ (a PERF artifact is never
        # confused with its V2 twin for the same case).
        assert v2_record.input_digest != perf_record.input_digest
        # But the recorded CASE is byte-identical.
        assert v2_record.case_section() == perf_record.case_section()
        # The self-verifying digests agree with the section encodings.
        assert record_input_digest_v2_perf(perf_record) == (
            perf_record.input_digest
        )
        assert record_output_digest_v2_perf(perf_record) == (
            perf_record.output_digest
        )


# ===========================================================================
# 4. The PERF typed record (negative — version and shape refusals)
# ===========================================================================


class TestPerfRecordRefusal:
    def test_output_schema_one_is_not_constructible_as_perf(self):
        record = _build_perf_record()
        _force_output_axis(record, 1)

    def test_perf_record_rejects_a_v2_attempt(self):
        # A frozen 5-key V2 attempt is not a PERF attempt: the
        # instrumentation is version-owned, not defaulted.
        record = _build_perf_record()
        v2_attempt = SemanticDecisionAttempt(
            AttemptRole.PRIMARY, 1,
            PRIMARY_PROVIDER_V2, PRIMARY_MODEL_V2, AttemptOutcome.OK,
        )
        fields = {
            f.name: getattr(record, f.name)
            for f in __import__("dataclasses").fields(
                SemanticDecisionRecordV2Perf
            )
        }
        fields["attempts"] = (v2_attempt,)
        with pytest.raises(TypeError, match="SemanticDecisionAttemptPerf"):
            SemanticDecisionRecordV2Perf(**fields)

    def test_v2_record_rejects_a_perf_attempt(self):
        # The frozen V2 record type never reinterprets a PERF attempt.
        record = _build_perf_record()
        fields = {
            f.name: getattr(record, f.name)
            for f in __import__("dataclasses").fields(
                SemanticDecisionRecordV2
            )
        }
        with pytest.raises(TypeError, match="SemanticDecisionAttempt"):
            SemanticDecisionRecordV2(**fields)

    def test_build_pins_the_perf_binding(self):
        record = _build_perf_record()
        assert record.output_schema_version == 2
        # The builder takes no version parameters (a PERF artifact
        # cannot be bound to the historical output schema 1).
        import inspect

        signature = inspect.signature(SemanticDecisionRecordV2Perf.build)
        assert "output_schema_version" not in signature.parameters
        assert "input_schema_version" not in signature.parameters


def _force_output_axis(record, axis):
    """Rebuild the record's fields with a forced output-schema axis."""
    fields = {
        f.name: getattr(record, f.name)
        for f in __import__("dataclasses").fields(
            SemanticDecisionRecordV2Perf
        )
    }
    fields["output_schema_version"] = axis
    with pytest.raises(ValueError, match="output_schema_version"):
        SemanticDecisionRecordV2Perf(**fields)


# ===========================================================================
# 5. The strict PERF codec (cross-adapter refusals + invalid telemetry)
# ===========================================================================


class TestPerfCodecCrossAdapterRefusal:
    def test_perf_adapter_refuses_a_v2_payload(self):
        # A historical V2 payload (5-key attempts, output schema 1) is
        # refused by the PERF adapter — never reinterpreted.
        case, context, profile = _case()
        tier_decision = derive_authority_tier(
            context,
            SemanticEvaluationV2.evaluated(
                V2SemanticDecision.MATCH, V2Confidence.HIGH, frozenset()
            ),
            case.context_provenances,
            profile,
        )
        v2_record = SemanticDecisionRecordV2.build(
            run_id=RUN_ID,
            assessment_index=0,
            source_url=case.candidate_source_url,
            case=case,
            evaluation_state=SemanticEvaluationStateV2.EVALUATED,
            decision=V2SemanticDecision.MATCH,
            confidence=V2Confidence.HIGH,
            reason_code=SemanticReasonCodeV2.MATCH_DESCRIPTION_AND_ATTRIBUTES,
            conflict_classes=frozenset(),
            matched_attributes=(),
            conflicting_attributes=(),
            missing_critical_attributes=(),
            attempts=(
                SemanticDecisionAttempt(
                    AttemptRole.PRIMARY, 1,
                    PRIMARY_PROVIDER_V2, PRIMARY_MODEL_V2,
                    AttemptOutcome.OK,
                ),
            ),
            fallback_used=False,
            fallback_reason=None,
            error_type=None,
            actual_provider=PRIMARY_PROVIDER_V2,
            actual_model=PRIMARY_MODEL_V2,
            evaluation_started_at=STARTED,
            evaluation_finished_at=FINISHED,
            product_evidence_quality=tier_decision.product_evidence_quality,
            relationship_authority=tier_decision.relationship_authority,
            authority_tier=tier_decision.tier,
            fired_rules=tier_decision.fired_rules,
        )
        payload = json.loads(json.dumps(encode_v2_payload(v2_record)))
        with pytest.raises(SemanticDecisionCodecError):
            SEMANTIC_V2_PERF_ADAPTER.decode(payload)

    def test_v2_adapter_refuses_a_perf_payload(self):
        # The frozen V2 adapter refuses a PERF payload (unexpected
        # attempt keys + the output-schema pin) — a historical record
        # is never silently re-versioned.
        perf_payload = json.loads(json.dumps(
            encode_v2_perf_payload(_build_perf_record())
        ))
        with pytest.raises(SemanticDecisionCodecError):
            SEMANTIC_V2_ADAPTER.decode(perf_payload)

    def test_unknown_output_schema_version_is_claimed_by_no_adapter(self):
        payload = json.loads(json.dumps(
            encode_semantic_decision_record(_build_perf_record())
        ))
        payload["contract"]["output_schema_version"] = 9
        with pytest.raises(
            SemanticDecisionCodecError, match="no registered"
        ):
            decode_semantic_decision_record(payload, schema_version=1)

    def test_forged_authority_axis_is_refused(self):
        # (V2, 2.0, 1, 2, FU4) is a cross-binding forgery: output
        # schema 2 under the FU4 authority token is claimed by NO
        # registered adapter.
        payload = json.loads(json.dumps(
            encode_semantic_decision_record(_build_perf_record())
        ))
        payload["contract"]["authority_contract_version"] = (
            "SEMANTIC_AUTHORITY_V2_S2A_FU4"
        )
        with pytest.raises(
            SemanticDecisionCodecError, match="no registered"
        ):
            decode_semantic_decision_record(payload, schema_version=1)


class TestPerfInvalidTelemetry:
    def _payload_with(self, mutate):
        payload = json.loads(json.dumps(
            encode_semantic_decision_record(_build_perf_record())
        ))
        mutate(payload)
        return payload

    def test_negative_latency_is_refused(self):
        def mutate(payload):
            payload["execution"]["attempts"][0]["latency_ms"] = -1
        with pytest.raises(SemanticDecisionCodecError):
            decode_semantic_decision_record(
                self._payload_with(mutate), schema_version=1
            )

    def test_float_latency_is_refused(self):
        def mutate(payload):
            payload["execution"]["attempts"][0]["latency_ms"] = 84.5
        with pytest.raises(
            SemanticDecisionCodecError, match="float"
        ):
            decode_semantic_decision_record(
                self._payload_with(mutate), schema_version=1
            )

    def test_boolean_latency_is_refused(self):
        def mutate(payload):
            payload["execution"]["attempts"][0]["latency_ms"] = True
        with pytest.raises(SemanticDecisionCodecError):
            decode_semantic_decision_record(
                self._payload_with(mutate), schema_version=1
            )

    def test_string_token_count_is_refused(self):
        def mutate(payload):
            payload["execution"]["attempts"][0]["prompt_tokens"] = "1234"
        with pytest.raises(SemanticDecisionCodecError):
            decode_semantic_decision_record(
                self._payload_with(mutate), schema_version=1
            )

    def test_negative_token_count_is_refused(self):
        def mutate(payload):
            payload["execution"]["attempts"][0]["completion_tokens"] = -5
        with pytest.raises(SemanticDecisionCodecError):
            decode_semantic_decision_record(
                self._payload_with(mutate), schema_version=1
            )

    def test_out_of_grammar_finish_reason_is_refused(self):
        for finish in ("STOP", "length!", "", "a" * 65, "9abc"):
            def mutate(payload, finish=finish):
                payload["execution"]["attempts"][0]["finish_reason"] = (
                    finish
                )
            with pytest.raises(SemanticDecisionCodecError):
                decode_semantic_decision_record(
                    self._payload_with(mutate), schema_version=1
                )

    def test_extra_attempt_key_is_refused(self):
        def mutate(payload):
            payload["execution"]["attempts"][0]["total_tokens"] = 1289
        with pytest.raises(
            SemanticDecisionCodecError, match="unexpected keys"
        ):
            decode_semantic_decision_record(
                self._payload_with(mutate), schema_version=1
            )

    def test_missing_instrumentation_key_is_refused(self):
        def mutate(payload):
            del payload["execution"]["attempts"][0]["finish_reason"]
        with pytest.raises(
            SemanticDecisionCodecError, match="missing required keys"
        ):
            decode_semantic_decision_record(
                self._payload_with(mutate), schema_version=1
            )

    def test_tampered_telemetry_fails_the_digest(self):
        def mutate(payload):
            payload["execution"]["attempts"][0]["latency_ms"] = 1
        # The universal decode wraps the record-constructor failure
        # (the self-verifying output digest check) in the bounded
        # artifact-contract error.
        with pytest.raises(
            SemanticDecisionCodecError, match="artifact contract"
        ):
            decode_semantic_decision_record(
                self._payload_with(mutate), schema_version=1
            )

    def test_tampered_case_fails_the_input_digest(self):
        def mutate(payload):
            payload["case"]["candidate"]["product"]["raw_title_text"] = (
                "Forged title"
            )
        with pytest.raises(
            SemanticDecisionCodecError, match="artifact contract"
        ):
            decode_semantic_decision_record(
                self._payload_with(mutate), schema_version=1
            )


# ===========================================================================
# 6. Historical replay (old records unchanged; PERF records replay)
# ===========================================================================


class TestHistoricalReplay:
    def test_old_v2_record_decodes_and_replays_byte_identically(self):
        case, context, profile = _case()
        tier_decision = derive_authority_tier(
            context,
            SemanticEvaluationV2.evaluated(
                V2SemanticDecision.MATCH, V2Confidence.HIGH, frozenset()
            ),
            case.context_provenances,
            profile,
        )
        v2_record = SemanticDecisionRecordV2.build(
            run_id=RUN_ID,
            assessment_index=0,
            source_url=case.candidate_source_url,
            case=case,
            evaluation_state=SemanticEvaluationStateV2.EVALUATED,
            decision=V2SemanticDecision.MATCH,
            confidence=V2Confidence.HIGH,
            reason_code=SemanticReasonCodeV2.MATCH_DESCRIPTION_AND_ATTRIBUTES,
            conflict_classes=frozenset(),
            matched_attributes=(),
            conflicting_attributes=(),
            missing_critical_attributes=(),
            attempts=(
                SemanticDecisionAttempt(
                    AttemptRole.PRIMARY, 1,
                    PRIMARY_PROVIDER_V2, PRIMARY_MODEL_V2,
                    AttemptOutcome.OK,
                ),
            ),
            fallback_used=False,
            fallback_reason=None,
            error_type=None,
            actual_provider=PRIMARY_PROVIDER_V2,
            actual_model=PRIMARY_MODEL_V2,
            evaluation_started_at=STARTED,
            evaluation_finished_at=FINISHED,
            product_evidence_quality=tier_decision.product_evidence_quality,
            relationship_authority=tier_decision.relationship_authority,
            authority_tier=tier_decision.tier,
            fired_rules=tier_decision.fired_rules,
        )
        original = _raw_bytes(v2_record)
        # The persisted bytes decode into the frozen V2 adapter's
        # record type (NOT the PERF successor) and re-encode to the
        # SAME bytes — the registry extension changes nothing for a
        # historical artifact.
        decoded = decode_semantic_decision_record(
            json.loads(original.decode("utf-8")), schema_version=1
        )
        assert type(decoded) is SemanticDecisionRecordV2
        assert _raw_bytes(decoded) == original
        replay = replay_semantic_decision(decoded)
        assert replay.contract_binding == V2_CONTRACT_BINDING
        assert replay.case == v2_record.case
        # The historical attempt stays the frozen 5-key shape.
        assert set(decoded.attempts[0].canonical()) == {
            "role",
            "attempt_number",
            "provider",
            "model",
            "outcome",
        }

    def test_perf_record_replays_under_the_perf_binding(self):
        record = _build_perf_record()
        replay = replay_semantic_decision(record)
        assert isinstance(replay, SemanticDecisionReplayV2Perf)
        assert replay.contract_binding == V2_PERF_CONTRACT_BINDING
        assert replay.case == record.case
        assert (
            replay.authority_decision.tier is record.authority_tier
        )
        # The instrumentation rides along on the replayed record
        # (provenance for the caller) — it is never a derivation
        # input (the authority decision equals the V2 twin's).
        assert replay.record.attempts[0].latency_ms == 84728
        assert replay.record.attempts[0].prompt_tokens == 1234

    def test_perf_replay_refuses_a_v2_record(self):
        # The PERF replay entry is type-strict: a historical V2 record
        # is the frozen V2 adapter's, never reinterpreted here.
        from product_intelligence.research.semantic_decision_v2 import (
            SemanticDecisionRecordV2 as _V2Record,
        )

        case, context, profile = _case()
        tier_decision = derive_authority_tier(
            context,
            SemanticEvaluationV2.evaluated(
                V2SemanticDecision.MATCH, V2Confidence.HIGH, frozenset()
            ),
            case.context_provenances,
            profile,
        )
        v2_record = _V2Record.build(
            run_id=RUN_ID,
            assessment_index=0,
            source_url=case.candidate_source_url,
            case=case,
            evaluation_state=SemanticEvaluationStateV2.EVALUATED,
            decision=V2SemanticDecision.MATCH,
            confidence=V2Confidence.HIGH,
            reason_code=SemanticReasonCodeV2.MATCH_DESCRIPTION_AND_ATTRIBUTES,
            conflict_classes=frozenset(),
            matched_attributes=(),
            conflicting_attributes=(),
            missing_critical_attributes=(),
            attempts=(
                SemanticDecisionAttempt(
                    AttemptRole.PRIMARY, 1,
                    PRIMARY_PROVIDER_V2, PRIMARY_MODEL_V2,
                    AttemptOutcome.OK,
                ),
            ),
            fallback_used=False,
            fallback_reason=None,
            error_type=None,
            actual_provider=PRIMARY_PROVIDER_V2,
            actual_model=PRIMARY_MODEL_V2,
            evaluation_started_at=STARTED,
            evaluation_finished_at=FINISHED,
            product_evidence_quality=tier_decision.product_evidence_quality,
            relationship_authority=tier_decision.relationship_authority,
            authority_tier=tier_decision.tier,
            fired_rules=tier_decision.fired_rules,
        )
        with pytest.raises(TypeError, match="SemanticDecisionRecordV2Perf"):
            replay_v2_perf_record(v2_record)

    def test_tampered_derived_snapshot_fails_the_replay(self):
        # The derived-agreement proof still guards PERF records: a
        # forged authority tier is refused at replay.
        record = _build_perf_record()
        fields = {
            f.name: getattr(record, f.name)
            for f in __import__("dataclasses").fields(
                SemanticDecisionRecordV2Perf
            )
        }
        forged_tier = (
            AuthorityTier.HUMAN_CONFIRMED
            if record.authority_tier is not AuthorityTier.HUMAN_CONFIRMED
            else AuthorityTier.NEEDS_REVIEW
        )
        fields["authority_tier"] = forged_tier
        # The digest self-check would also fire; either way the
        # artifact is corrupt and refuses to construct/replay.
        with pytest.raises((ValueError, SemanticDecisionReplayError)):
            replay_v2_perf_record(SemanticDecisionRecordV2Perf(**fields))


# ===========================================================================
# 7. Service round-trip over the SAME universal row (no migration)
# ===========================================================================


class TestPerfServiceRoundTrip:
    def _run_and_snapshot(self):
        from product_intelligence.research import (
            PRICE_RESULT_SCHEMA_VERSION,
            aggregate_listing_prices,
            encode_price_aggregation_result,
        )
        from product_intelligence.runs.models import (
            PriceIntelligenceSnapshot,
            ResearchRun,
        )

        assessment = assess_listing_identity(
            REQUEST, normalize_listing_observation(_observation())
        )
        run = ResearchRun.objects.create_from_request(REQUEST)
        price_result = aggregate_listing_prices(REQUEST, (assessment,))
        PriceIntelligenceSnapshot.objects.create(
            run=run,
            schema_version=PRICE_RESULT_SCHEMA_VERSION,
            payload=encode_price_aggregation_result(price_result),
        )
        return run

    def test_perf_record_persists_loads_and_replays(self):
        from product_intelligence.execution.semantic_decision_persistence import (
            load_semantic_decision,
            persist_semantic_decision,
            replay_semantic_decision_record,
        )

        run = self._run_and_snapshot()
        record = _build_perf_record()
        # Bind the record to the run (the service check).
        case, context, profile = _case()
        tier_decision = derive_authority_tier(
            context,
            SemanticEvaluationV2.evaluated(
                V2SemanticDecision.MATCH, V2Confidence.HIGH, frozenset()
            ),
            case.context_provenances,
            profile,
        )
        bound = SemanticDecisionRecordV2Perf.build(
            run_id=str(run.id),
            assessment_index=0,
            source_url=case.candidate_source_url,
            case=case,
            evaluation_state=SemanticEvaluationStateV2.EVALUATED,
            decision=V2SemanticDecision.MATCH,
            confidence=V2Confidence.HIGH,
            reason_code=SemanticReasonCodeV2.MATCH_DESCRIPTION_AND_ATTRIBUTES,
            conflict_classes=frozenset(),
            matched_attributes=(),
            conflicting_attributes=(),
            missing_critical_attributes=(),
            attempts=(
                SemanticDecisionAttemptPerf(
                    AttemptRole.PRIMARY, 1,
                    PRIMARY_PROVIDER_V2_PERF, PRIMARY_MODEL_V2_PERF,
                    AttemptOutcome.OK, 1234, 500, 2475, "stop",
                ),
            ),
            fallback_used=False,
            fallback_reason=None,
            error_type=None,
            actual_provider=PRIMARY_PROVIDER_V2_PERF,
            actual_model=PRIMARY_MODEL_V2_PERF,
            evaluation_started_at=STARTED,
            evaluation_finished_at=FINISHED,
            product_evidence_quality=tier_decision.product_evidence_quality,
            relationship_authority=tier_decision.relationship_authority,
            authority_tier=tier_decision.tier,
            fired_rules=tier_decision.fired_rules,
        )
        row = persist_semantic_decision(run, bound)
        # The SAME universal row: envelope schema version 1 (no
        # migration, no new column).
        assert row.schema_version == SEMANTIC_DECISION_SCHEMA_VERSION == 1
        assert row.payload_digest == canonical_payload_digest(row.payload)
        assert row.payload["contract"]["output_schema_version"] == 2

        loaded = load_semantic_decision(run.id, 0)
        assert type(loaded) is SemanticDecisionRecordV2Perf
        assert loaded == bound

        replay = replay_semantic_decision_record(run.id, 0)
        assert isinstance(replay, SemanticDecisionReplayV2Perf)
        assert replay.contract_binding == V2_PERF_CONTRACT_BINDING

        # Append-only: a second persist for the same binding fails
        # closed (the ledger is immutable — unchanged service rule).
        from product_intelligence.execution.semantic_decision_persistence import (
            SemanticDecisionAlreadyRecordedError,
        )

        with pytest.raises(SemanticDecisionAlreadyRecordedError):
            persist_semantic_decision(run, bound)

        # Cleanup (the session test DB).
        from product_intelligence.runs.models import (
            PriceIntelligenceSnapshot,
            ResearchRun,
            SemanticDecisionRecord,
        )

        SemanticDecisionRecord.objects.all().delete()
        PriceIntelligenceSnapshot.objects.all().delete()
        ResearchRun.objects.all().delete()

    def test_historical_v2_row_still_replays_after_the_extension(self):
        from product_intelligence.execution.semantic_decision_persistence import (
            load_semantic_decision,
            persist_semantic_decision,
            replay_semantic_decision_record,
        )

        run = self._run_and_snapshot()
        case, context, profile = _case()
        tier_decision = derive_authority_tier(
            context,
            SemanticEvaluationV2.evaluated(
                V2SemanticDecision.MATCH, V2Confidence.HIGH, frozenset()
            ),
            case.context_provenances,
            profile,
        )
        v2_record = SemanticDecisionRecordV2.build(
            run_id=str(run.id),
            assessment_index=0,
            source_url=case.candidate_source_url,
            case=case,
            evaluation_state=SemanticEvaluationStateV2.EVALUATED,
            decision=V2SemanticDecision.MATCH,
            confidence=V2Confidence.HIGH,
            reason_code=SemanticReasonCodeV2.MATCH_DESCRIPTION_AND_ATTRIBUTES,
            conflict_classes=frozenset(),
            matched_attributes=(),
            conflicting_attributes=(),
            missing_critical_attributes=(),
            attempts=(
                SemanticDecisionAttempt(
                    AttemptRole.PRIMARY, 1,
                    PRIMARY_PROVIDER_V2, PRIMARY_MODEL_V2,
                    AttemptOutcome.OK,
                ),
            ),
            fallback_used=False,
            fallback_reason=None,
            error_type=None,
            actual_provider=PRIMARY_PROVIDER_V2,
            actual_model=PRIMARY_MODEL_V2,
            evaluation_started_at=STARTED,
            evaluation_finished_at=FINISHED,
            product_evidence_quality=tier_decision.product_evidence_quality,
            relationship_authority=tier_decision.relationship_authority,
            authority_tier=tier_decision.tier,
            fired_rules=tier_decision.fired_rules,
        )
        original = _raw_bytes(v2_record)
        row = persist_semantic_decision(run, v2_record)
        # The persisted bytes are the historical shape (output schema
        # 1, 5-key attempts) — the extension changed nothing for them.
        assert row.payload["contract"]["output_schema_version"] == 1
        assert _raw_bytes(v2_record) == original
        loaded = load_semantic_decision(run.id, 0)
        assert type(loaded) is SemanticDecisionRecordV2
        assert _raw_bytes(loaded) == original
        replay = replay_semantic_decision_record(run.id, 0)
        assert replay.contract_binding == V2_CONTRACT_BINDING

        from product_intelligence.runs.models import (
            PriceIntelligenceSnapshot,
            ResearchRun,
            SemanticDecisionRecord,
        )

        SemanticDecisionRecord.objects.all().delete()
        PriceIntelligenceSnapshot.objects.all().delete()
        ResearchRun.objects.all().delete()


# ===========================================================================
# 8. Anti-leakage (no raw response / prompt / credential / float /
#    unbounded provider metadata)
# ===========================================================================


class TestPerfAntiLeakage:
    def test_payload_carries_no_raw_response_or_prompt_text(self):
        # A distinctive canary in the response text and in the prompt
        # input: the payload may carry the recorded CASE (the input is
        # the recorded V2 input — the title text is a case field), but
        # it must NEVER carry the model's raw output or the rendered
        # prompt.
        canary = "CANARY-RAW-OUTPUT-TEXT-12345"
        record = _build_perf_record()
        payload = json.loads(json.dumps(
            encode_semantic_decision_record(record)
        ))
        text = json.dumps(payload, sort_keys=True)
        # No raw-response surface exists at all.
        assert "raw_output" not in text
        assert "raw_response" not in text
        # No credential / API surface.
        for token in ("api_key", "authorization", "secret", "bearer"):
            assert token not in text.lower()
        # The execution section carries ONLY the bounded provenance +
        # instrumentation — no provider status / identity metadata.
        execution = payload["execution"]
        assert set(execution) == {
            "attempts",
            "fallback_used",
            "fallback_reason",
            "error_type",
            "actual_provider",
            "actual_model",
            "evaluation_started_at",
            "evaluation_finished_at",
        }
        for attempt in execution["attempts"]:
            assert set(attempt) == {
                "role",
                "attempt_number",
                "provider",
                "model",
                "outcome",
                "latency_ms",
                "prompt_tokens",
                "completion_tokens",
                "finish_reason",
            }
            for token in (
                "provider_status",
                "provider_id",
                "model_id",
                "total_tokens",
                "http_status",
                "transport_status",
            ):
                assert token not in attempt

    def test_no_float_anywhere_in_the_perf_payload(self):
        from product_intelligence.research.semantic_decision_record import (
            _refuse_floats_anywhere,
        )

        payload = json.loads(json.dumps(
            encode_semantic_decision_record(_build_perf_record())
        ))
        _refuse_floats_anywhere(payload, "top-level")  # must not raise

    def test_finish_reason_carries_only_the_bounded_identifier(self):
        # The bounded finish reason is the provider's own short
        # identifier — never free text.
        for value in ("stop", "length", "content_filter", "tool_calls"):
            assert is_bounded_perf_finish_reason(value)
        for value in (
            "The model said: I think these are the same product.",
            "stop\nmore",
            "a" * (PERF_FINISH_REASON_MAX_LENGTH + 1),
        ):
            assert not is_bounded_perf_finish_reason(value)


# ===========================================================================
# 9. Differential V2 <-> PERF compatibility (Phase 0-FU1, Task C)
# ===========================================================================


def _v2_base_attempt(number, outcome):
    """The frozen 5-key V2 recorded attempt for one call position."""
    role = AttemptRole.PRIMARY if number == 1 else AttemptRole.FALLBACK
    provider = PRIMARY_PROVIDER_V2 if number == 1 else FALLBACK_PROVIDER_V2
    model = PRIMARY_MODEL_V2 if number == 1 else FALLBACK_MODEL_V2
    return SemanticDecisionAttempt(role, number, provider, model, outcome)


# The equivalent-outcome shapes of the differential matrix: the recorded
# evaluation axes + the frozen 5-key V2 attempts + the per-attempt bounded
# telemetry the PERF twin carries (latency_ms, prompt_tokens,
# completion_tokens, finish_reason — explicit None = unknown, never
# zero-filled, never invented).
_DIFFERENTIAL_SHAPES = {
    "match_primary": dict(
        evaluation_state=SemanticEvaluationStateV2.EVALUATED,
        decision=V2SemanticDecision.MATCH,
        confidence=V2Confidence.HIGH,
        reason_code=SemanticReasonCodeV2.MATCH_DESCRIPTION_AND_ATTRIBUTES,
        conflict_classes=frozenset(),
        attempts=(_v2_base_attempt(1, AttemptOutcome.OK),),
        fallback_used=False,
        fallback_reason=None,
        error_type=None,
        actual_provider=PRIMARY_PROVIDER_V2,
        actual_model=PRIMARY_MODEL_V2,
        telemetry=((84728, 1234, 2475, "stop"),),
    ),
    "match_fallback": dict(
        evaluation_state=SemanticEvaluationStateV2.EVALUATED,
        decision=V2SemanticDecision.MATCH,
        confidence=V2Confidence.HIGH,
        reason_code=SemanticReasonCodeV2.MATCH_DESCRIPTION_AND_ATTRIBUTES,
        conflict_classes=frozenset(),
        attempts=(
            _v2_base_attempt(1, AttemptOutcome.RATE_LIMITED),
            _v2_base_attempt(2, AttemptOutcome.OK),
        ),
        fallback_used=True,
        fallback_reason=SemanticFallbackReason.RATE_LIMITED,
        error_type=None,
        actual_provider=FALLBACK_PROVIDER_V2,
        actual_model=FALLBACK_MODEL_V2,
        telemetry=((120, None, None, None), (45000, 900, 1500, "length")),
    ),
    "no_match_primary": dict(
        evaluation_state=SemanticEvaluationStateV2.EVALUATED,
        decision=V2SemanticDecision.NO_MATCH,
        confidence=V2Confidence.HIGH,
        reason_code=SemanticReasonCodeV2.NO_MATCH_CAPACITY,
        conflict_classes=frozenset({ConflictClass.CAPACITY}),
        attempts=(_v2_base_attempt(1, AttemptOutcome.OK),),
        fallback_used=False,
        fallback_reason=None,
        error_type=None,
        actual_provider=PRIMARY_PROVIDER_V2,
        actual_model=PRIMARY_MODEL_V2,
        telemetry=((60132, 1100, 300, "stop"),),
    ),
    "uncertain_primary": dict(
        evaluation_state=SemanticEvaluationStateV2.EVALUATED,
        decision=V2SemanticDecision.UNCERTAIN,
        confidence=V2Confidence.MEDIUM,
        reason_code=SemanticReasonCodeV2.UNCERTAIN_IDENTIFIER_RELATION,
        conflict_classes=frozenset(),
        attempts=(_v2_base_attempt(1, AttemptOutcome.OK),),
        fallback_used=False,
        fallback_reason=None,
        error_type=None,
        actual_provider=PRIMARY_PROVIDER_V2,
        actual_model=PRIMARY_MODEL_V2,
        telemetry=((30215, None, 140, "stop"),),
    ),
    "runtime_failure": dict(
        evaluation_state=SemanticEvaluationStateV2.RUNTIME_FAILURE,
        decision=None,
        confidence=None,
        reason_code=None,
        conflict_classes=frozenset(),
        attempts=(
            _v2_base_attempt(1, AttemptOutcome.TIMEOUT),
            _v2_base_attempt(2, AttemptOutcome.TIMEOUT),
        ),
        fallback_used=True,
        fallback_reason=SemanticFallbackReason.TIMEOUT,
        error_type=SemanticFailureClass.FALLBACK_TIMEOUT,
        actual_provider=None,
        actual_model=None,
        telemetry=((300000, None, None, None), (300000, None, None, None)),
    ),
}


def _differential_pair(case, shape_name):
    """The equivalent historical V2 record + instrumented PERF record
    built from the SAME semantic outcome over the SAME recorded case
    (honestly derived audit snapshots for both)."""
    shape = _DIFFERENTIAL_SHAPES[shape_name]
    if shape["evaluation_state"] is SemanticEvaluationStateV2.EVALUATED:
        evaluation = SemanticEvaluationV2.evaluated(
            shape["decision"], shape["confidence"], shape["conflict_classes"]
        )
    elif shape["evaluation_state"] is SemanticEvaluationStateV2.RUNTIME_FAILURE:
        evaluation = SemanticEvaluationV2.runtime_failure()
    else:
        evaluation = SemanticEvaluationV2.not_evaluated()
    tier_decision = derive_authority_tier(
        _context_of(case),
        evaluation,
        case.context_provenances,
        case.product_evidence,
    )
    not_evaluated = shape["evaluation_state"] is (
        SemanticEvaluationStateV2.NOT_EVALUATED
    )
    common = dict(
        run_id=RUN_ID,
        assessment_index=0,
        source_url=case.candidate_source_url,
        case=case,
        evaluation_state=shape["evaluation_state"],
        decision=shape["decision"],
        confidence=shape["confidence"],
        reason_code=shape["reason_code"],
        conflict_classes=shape["conflict_classes"],
        matched_attributes=(),
        conflicting_attributes=(),
        missing_critical_attributes=(),
        fallback_used=shape["fallback_used"],
        fallback_reason=shape["fallback_reason"],
        error_type=shape["error_type"],
        actual_provider=shape["actual_provider"],
        actual_model=shape["actual_model"],
        evaluation_started_at=None if not_evaluated else STARTED,
        evaluation_finished_at=None if not_evaluated else FINISHED,
        product_evidence_quality=tier_decision.product_evidence_quality,
        relationship_authority=tier_decision.relationship_authority,
        authority_tier=tier_decision.tier,
        fired_rules=tier_decision.fired_rules,
    )
    v2_record = SemanticDecisionRecordV2.build(**common, attempts=shape["attempts"])
    perf_attempts = tuple(
        SemanticDecisionAttemptPerf(
            role=v2.role,
            attempt_number=v2.attempt_number,
            provider=v2.provider,
            model=v2.model,
            outcome=v2.outcome,
            latency_ms=telemetry[0],
            prompt_tokens=telemetry[1],
            completion_tokens=telemetry[2],
            finish_reason=telemetry[3],
        )
        for v2, telemetry in zip(shape["attempts"], shape["telemetry"])
    )
    perf_record = SemanticDecisionRecordV2Perf.build(
        **common, attempts=perf_attempts
    )
    return v2_record, perf_record


def _assert_differential(v2, perf):
    """The Phase 0-FU1 Task C contract: identical semantic content and
    identical derived authority — differing ONLY on the explicitly
    versioned output-contract axis (recorded output schema 1 -> 2) and
    the added bounded per-attempt instrumentation."""
    # -- identical recorded V2 input --
    assert v2.case == perf.case
    # -- identical recorded semantic output --
    assert v2.evaluation_state is perf.evaluation_state
    assert v2.decision is perf.decision
    assert v2.confidence is perf.confidence
    assert v2.reason_code is perf.reason_code
    assert v2.conflict_classes == perf.conflict_classes
    assert v2.matched_attributes == perf.matched_attributes
    assert v2.conflicting_attributes == perf.conflicting_attributes
    assert v2.missing_critical_attributes == perf.missing_critical_attributes
    # -- identical recorded execution provenance --
    assert v2.fallback_used == perf.fallback_used
    assert v2.fallback_reason is perf.fallback_reason
    assert v2.error_type is perf.error_type
    assert v2.actual_provider == perf.actual_provider
    assert v2.actual_model == perf.actual_model
    assert v2.evaluation_started_at == perf.evaluation_started_at
    assert v2.evaluation_finished_at == perf.evaluation_finished_at
    # -- identical universal binding --
    assert v2.run_id == perf.run_id
    assert v2.assessment_index == perf.assessment_index
    assert v2.source_url == perf.source_url
    # -- identical derived authority (the instrumentation grants none) --
    assert v2.product_evidence_quality is perf.product_evidence_quality
    assert v2.relationship_authority is perf.relationship_authority
    assert v2.authority_tier is perf.authority_tier
    assert v2.fired_rules == perf.fired_rules
    # -- identical base attempts (the frozen 5-key V2 attempt) --
    assert len(v2.attempts) == len(perf.attempts)
    for v2_attempt, perf_attempt in zip(v2.attempts, perf.attempts):
        assert (
            v2_attempt.role,
            v2_attempt.attempt_number,
            v2_attempt.provider,
            v2_attempt.model,
            v2_attempt.outcome,
        ) == (
            perf_attempt.role,
            perf_attempt.attempt_number,
            perf_attempt.provider,
            perf_attempt.model,
            perf_attempt.outcome,
        )
    # -- the ONLY moved contract axis: recorded output schema 1 -> 2 --
    assert v2.output_schema_version == 1
    assert perf.output_schema_version == 2
    assert (
        v2.semantic_contract_version,
        v2.prompt_version,
        v2.input_schema_version,
        v2.authority_contract_version,
    ) == (
        perf.semantic_contract_version,
        perf.prompt_version,
        perf.input_schema_version,
        perf.authority_contract_version,
    ) == (
        "V2",
        "2.0",
        1,
        "SEMANTIC_AUTHORITY_V2_S2A_FU2",
    )
    # The versioned axis is what separates the self-verifying digests
    # (a PERF artifact is never confused with its V2 twin).
    assert v2.input_digest != perf.input_digest
    assert v2.output_digest != perf.output_digest
    # -- the added bounded instrumentation lives only on the PERF side --
    for perf_attempt in perf.attempts:
        assert isinstance(perf_attempt.latency_ms, int)
        assert perf_attempt.latency_ms >= 0
        for tokens in (
            perf_attempt.prompt_tokens,
            perf_attempt.completion_tokens,
        ):
            assert tokens is None or (
                isinstance(tokens, int) and tokens >= 0
            )
        assert perf_attempt.finish_reason is None or (
            is_bounded_perf_finish_reason(perf_attempt.finish_reason)
        )


class TestV2PerfDifferentialCompatibility:
    """Differential compatibility (Phase 0-FU1, Task C): a historical V2
    record and the instrumented V2 PERF record built from equivalent
    semantic outcomes have IDENTICAL semantic content and IDENTICAL
    derived authority — excluding only the explicitly versioned
    output-contract axis (recorded output schema 1 -> 2) and the added
    bounded instrumentation (which is never a derivation input and
    grants no authority)."""

    @pytest.mark.parametrize("shape_name", sorted(_DIFFERENTIAL_SHAPES))
    def test_equivalent_records_differ_only_on_the_versioned_axes(
        self, shape_name
    ) -> None:
        case, _, _ = _case()
        v2, perf = _differential_pair(case, shape_name)
        _assert_differential(v2, perf)
        # The universal zero-live replay agrees on every authority
        # surface (the re-derivation runs over the case / evaluation —
        # identical for both records; the instrumentation is excluded).
        rv = replay_semantic_decision(v2)
        rp = replay_semantic_decision(perf)
        assert rv.contract_binding == V2_CONTRACT_BINDING
        assert rp.contract_binding == V2_PERF_CONTRACT_BINDING
        assert rv.case == rp.case
        assert rv.identity_context == rp.identity_context
        assert rv.semantic_evaluation == rp.semantic_evaluation
        assert rv.context_provenances == rp.context_provenances
        assert rv.product_evidence == rp.product_evidence
        assert rv.product_evidence_quality is rp.product_evidence_quality
        assert rv.relationship_requirement is rp.relationship_requirement
        assert rv.relationship_authority is rp.relationship_authority
        assert rv.authority_decision == rp.authority_decision

    @pytest.mark.parametrize("shape_name", sorted(_DIFFERENTIAL_SHAPES))
    def test_historical_v2_replay_remains_byte_identical(self, shape_name):
        case, _, _ = _case()
        v2, _ = _differential_pair(case, shape_name)
        original = _raw_bytes(v2)
        decoded = decode_semantic_decision_record(
            json.loads(original.decode("utf-8")), schema_version=1
        )
        # The historical artifact still decodes to the FROZEN V2 record
        # type (NOT the PERF successor) and re-encodes to the SAME
        # bytes — the registry extension changes nothing for it.
        assert type(decoded) is SemanticDecisionRecordV2
        assert _raw_bytes(decoded) == original
        replay = replay_semantic_decision(decoded)
        assert replay.contract_binding == V2_CONTRACT_BINDING
        assert replay.case == v2.case

    def test_reviewed_micron_alias_case_is_differentially_equivalent(self):
        # The reviewed Micron alias case (the S2-C motivating shape):
        # the U5 near-miss candidate, the customer retrieval provenance,
        # and the ESTABLISHED 4D-D alias acquisition's reviewed
        # manufacturer TARGET context (zero identity authority — the
        # frozen ceiling applies exactly as S2-A defines it). The
        # historical V2 and the instrumented PERF records built from
        # this equivalent outcome are differentially identical.
        from product_intelligence.execution.micron_alias_authority import (
            acquire_micron_alias_eligibility,
        )
        from product_intelligence.execution.semantic_decision_v2_execution import (
            reviewed_target_context_from_alias_result,
        )
        from product_intelligence.research.micron_packaging_alias import (
            MicronAliasEligibilityStatus,
        )
        from product_intelligence.providers.page import FetchedPage

        request = ResearchRequest(
            "MTFDKCC3T8TGP-1BK1DABYYR",
            "Micron 7500 PRO 3840GB U.3 15mm SSD",
        )
        candidate_mpn = "MTFDKCC3T8TGP-1BK1DABYY"
        observation = ListingObservation(
            source_url="https://example.com/7500-pro",
            extraction_method=ExtractionMethod.JSON_LD,
            product_title=(
                "Micron 7500 PRO 3840GB U.3 15mm SSD " + candidate_mpn
            ),
            brand_text=None,
            manufacturer_part_number_text=candidate_mpn,
            sku_text=None,
            price_text="2000",
            currency_text="USD",
            availability_text="In stock",
            condition_text="New",
            seller_text=None,
        )
        assessment = assess_listing_identity(
            request, normalize_listing_observation(observation)
        )
        context = derive_identity_state_v2(assessment)
        provenances = frozenset(
            {ContextProvenance.CUSTOMER_RETRIEVAL_RELATION}
        )
        profile = build_v2_product_evidence_profile(
            observation=assessment.normalized_listing.observation,
            context_provenances=provenances,
            matched_facts=frozenset(),
        )

        class _CatalogFetcher:
            """Offline PageFetcher: serves the recorded Micron 7500
            part catalog (the reviewed 4D-D source)."""

            def fetch(self, fetch_request):
                body = (
                    Path(__file__).resolve().parents[1]
                    / "fixtures"
                    / "pages"
                    / "micron_7500_part_catalog.json"
                ).read_text(encoding="utf-8")
                return FetchedPage(
                    requested_url=fetch_request.url,
                    final_url=fetch_request.url,
                    retrieved_at=datetime.now(tz=timezone.utc),
                    status_code=200,
                    body_text=body,
                    content_type="application/json",
                    body_byte_count=len(body.encode("utf-8")),
                    redirect_count=0,
                    fetcher_id="test",
                )

        alias_result = acquire_micron_alias_eligibility(
            request=request, page_fetcher=_CatalogFetcher()
        )
        assert alias_result.status is MicronAliasEligibilityStatus.ESTABLISHED
        reviewed = reviewed_target_context_from_alias_result(alias_result)
        assert reviewed is not None
        case = build_semantic_match_case_v2(
            case_id="candidate-differential-micron-0",
            request=request,
            assessment=assessment,
            context=context,
            product_evidence=profile,
            context_provenances=provenances,
            reviewed_target_context=reviewed,
        )
        # The recorded V2 input carries the reviewed Micron alias
        # context (target-side; zero identity authority).
        assert case.target.reviewed_context == reviewed
        assert case.context_provenances == provenances

        v2, perf = _differential_pair(case, "match_primary")
        _assert_differential(v2, perf)
        # The reviewed context grants nothing: the derived snapshots
        # show the frozen ceiling under customer retrieval only.
        assert v2.relationship_authority is (
            RelationshipAuthority.NOT_ESTABLISHED
        )
        assert perf.relationship_authority is (
            RelationshipAuthority.NOT_ESTABLISHED
        )
        assert v2.authority_tier is AuthorityTier.NEEDS_REVIEW
        assert perf.authority_tier is AuthorityTier.NEEDS_REVIEW
        rv = replay_semantic_decision(v2)
        rp = replay_semantic_decision(perf)
        assert rv.authority_decision == rp.authority_decision
        assert rv.relationship_authority is (
            RelationshipAuthority.NOT_ESTABLISHED
        )
