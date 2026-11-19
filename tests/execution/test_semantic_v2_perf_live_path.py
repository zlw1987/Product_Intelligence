"""Tests for the live-path bounded performance instrumentation
(SEMANTIC-V2-PERF Phase 0, A1 — the versioned successor record).

Covers the S2-C live V2 execution wiring
(``product_intelligence.execution.semantic_decision_v2_execution``)
after the Phase 0 cutover:

* the live path now persists the VERSIONED SUCCESSOR of the frozen V2
  ledger record (``SemanticDecisionRecordV2Perf`` — recorded output
  schema 2, the same semantic contract / prompt / input schema /
  authority axes) with the bounded per-attempt instrumentation:
  integer-millisecond latency, the provider-reported prompt /
  completion token counts (explicit null = unknown, never zero), the
  bounded finish reason;
* unavailable provider telemetry persists as the explicit unknown
  (null) — never zero and never invented — including the failure
  attempts (no successful completion -> no usage / finish reason);
* historical coexistence: a pre-existing output-schema-1 V2 record
  still loads and replays byte-identically through the frozen V2
  adapter in the same ledger, and the V1 path is untouched;
* the AUTHORITY FIREWALL holds over the instrumented record: a V2
  MATCH/HIGH never enters the frozen 4A aggregation, never alters the
  Machine Price, and never creates a review candidate (the
  instrumentation is provenance, never authority input).

Zero live AI / provider / network work: fake transports only.
"""

from __future__ import annotations

import json

import pytest

from product_intelligence.domain import ResearchRequest
from product_intelligence.research import (
    V2Confidence,
    V2SemanticDecision,
    ExtractionMethod,
    ListingObservation,
    aggregate_listing_prices,
    assess_listing_identity,
    normalize_listing_observation,
)
from product_intelligence.research import (
    V2_PERF_CONTRACT_BINDING,
    SemanticDecisionAttemptPerf,
    SemanticDecisionRecordV2Perf,
    SemanticDecisionReplayV2Perf,
)
from product_intelligence.research.semantic_decision_v2 import (
    V2_CONTRACT_BINDING,
    SemanticDecisionRecordV2,
)
from product_intelligence.runs.models import (
    AiAssistedReviewCandidate,
    PriceIntelligenceSnapshot,
    ResearchRun,
    SemanticDecisionRecord as SemanticDecisionRecordRow,
)
from product_intelligence.execution.semantic_decision_persistence import (
    load_semantic_decision,
    persist_semantic_decision,
    replay_semantic_decision_record,
)
from product_intelligence.execution.semantic_decision_v2_execution import (
    build_semantic_decision_records_v2,
    evaluate_semantic_matches_v2,
    persist_semantic_decision_records_v2,
)
from product_intelligence.semantic.runtime_v2 import (
    FALLBACK_MODEL_V2,
    PRIMARY_MODEL_V2,
    SemanticRuntimeV2,
)
from product_intelligence.semantic.transport import FakeSemanticModelTransport


REQUEST = ResearchRequest("ABC-123", "A test product")


@pytest.fixture(autouse=True)
def _cleanup():
    yield
    SemanticDecisionRecordRow.objects.all().delete()
    AiAssistedReviewCandidate.objects.all().delete()
    PriceIntelligenceSnapshot.objects.all().delete()
    ResearchRun.objects.all().delete()


def _v2_response(
    decision: str = "MATCH",
    confidence: str = "HIGH",
    reason_code: str = "MATCH_DESCRIPTION_AND_ATTRIBUTES",
) -> str:
    return json.dumps(
        {
            "decision": decision,
            "confidence": confidence,
            "reason_code": reason_code,
            "matched_attributes": [],
            "conflicting_attributes": [],
            "missing_critical_attributes": [],
            "conflict_classes": [],
        }
    )


def _v2_runtime(
    response: str | None = _v2_response(),
    primary_error: str | None = None,
    fallback_response: str | None = None,
    fallback_error: str | None = None,
    finish_reason: str | None = "stop",
) -> SemanticRuntimeV2:
    def _t(error=None, raw=None, model=PRIMARY_MODEL_V2):
        return FakeSemanticModelTransport(
            responses={"UNKNOWN": raw} if raw is not None else None,
            failure_error_types={"UNKNOWN": error} if error else None,
            provider_reported_model=model,
            finish_reason=finish_reason if raw is not None else None,
            case_ids=("UNKNOWN",),
        )

    return SemanticRuntimeV2(
        primary_transport=_t(primary_error, response),
        fallback_transport=_t(
            fallback_error,
            fallback_response,
            model=FALLBACK_MODEL_V2,
        ),
    )


def _u1_run_and_assessment():
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
    run = ResearchRun.objects.create_from_request(REQUEST)
    return run, assessment


def _persist_live(run, assessment, runtime):
    outcomes = evaluate_semantic_matches_v2(
        REQUEST,
        (assessment,),
        context_provenances_by_assessment={},
        reviewed_target_context=None,
        runtime_v2=runtime,
    )
    published = aggregate_listing_prices(REQUEST, (assessment,)).assessments
    records = build_semantic_decision_records_v2(run, published, outcomes)
    persist_semantic_decision_records_v2(run, records)
    return records[0], outcomes[0]


# ===========================================================================
# 1. The live path persists the instrumented successor record
# ===========================================================================


class TestLivePathInstrumentedRecord:
    def test_live_match_persists_the_perf_record_with_telemetry(self):
        run, assessment = _u1_run_and_assessment()
        record, outcome = _persist_live(
            run, assessment, _v2_runtime(finish_reason="stop")
        )
        # The live record is the VERSIONED SUCCESSOR (not the frozen
        # V2 record type, and not a subclass — a distinct registered
        # record type).
        assert type(record) is SemanticDecisionRecordV2Perf
        assert (
            record.semantic_contract_version,
            record.prompt_version,
            record.input_schema_version,
            record.output_schema_version,
            record.authority_contract_version,
        ) == V2_PERF_CONTRACT_BINDING
        assert record.output_schema_version == 2

        # The bounded instrumentation came from the provider report of
        # the fake transport (the runtime's own measured wall-clock
        # latency in its bounded integer-millisecond form — the fake
        # completes in a fraction of a millisecond, so 0 is the honest
        # measurement; the fixed 500 / 50 usage; the reported finish
        # reason).
        attempt = record.attempts[0]
        assert isinstance(attempt, SemanticDecisionAttemptPerf)
        assert isinstance(attempt.latency_ms, int)
        assert attempt.latency_ms >= 0
        assert attempt.prompt_tokens == 500
        assert attempt.completion_tokens == 50
        assert attempt.finish_reason == "stop"

        # The in-memory runtime measurement stays the float (the
        # integer-millisecond form is the persistence form, applied by
        # the record builder — the runtime is unchanged in behavior).
        assert isinstance(outcome.result.attempts[0].latency_ms, float)

        loaded = load_semantic_decision(run.id, 0)
        assert type(loaded) is SemanticDecisionRecordV2Perf
        assert loaded == record
        assert adapter_is_claimed_by_the_perf_adapter(run.id, 0)

    def test_live_row_reuses_the_same_universal_row(self):
        run, assessment = _u1_run_and_assessment()
        _persist_live(run, assessment, _v2_runtime(finish_reason="stop"))
        row = SemanticDecisionRecordRow.objects.get(
            run_id=run.id, assessment_index=0
        )
        # No migration: envelope schema version 1, the same row shape;
        # the version lives in the payload's contract section.
        assert row.schema_version == 1
        assert row.payload["schema_version"] == 1
        assert row.payload["contract"]["output_schema_version"] == 2

    def test_live_failure_record_carries_the_explicit_unknowns(self):
        # No successful completion: the provider reported no usage and
        # no finish reason -> both persist as null (never 0, never
        # invented); the measured latency still persists.
        run, assessment = _u1_run_and_assessment()
        record, _ = _persist_live(
            run,
            assessment,
            _v2_runtime(
                primary_error="CONNECTION_ERROR",
                fallback_error="CONNECTION_ERROR",
            ),
        )
        assert record.evaluation_state.value == "RUNTIME_FAILURE"
        assert len(record.attempts) == 2
        for attempt in record.attempts:
            assert attempt.prompt_tokens is None
            assert attempt.completion_tokens is None
            assert attempt.finish_reason is None
            assert isinstance(attempt.latency_ms, int)
            assert attempt.latency_ms >= 0
        row = SemanticDecisionRecordRow.objects.get(
            run_id=run.id, assessment_index=0
        )
        for persisted in row.payload["execution"]["attempts"]:
            assert persisted["prompt_tokens"] is None
            assert persisted["completion_tokens"] is None
            assert persisted["finish_reason"] is None

    def test_live_fallback_record_carries_per_attempt_identity(self):
        # Primary fails (no usage), fallback succeeds (its own usage +
        # finish reason): the instrumentation is PER ATTEMPT, never
        # attributed to the wrong attempt.
        run, assessment = _u1_run_and_assessment()
        record, _ = _persist_live(
            run,
            assessment,
            _v2_runtime(
                primary_error="RATE_LIMITED",
                fallback_response=_v2_response(),
                finish_reason="length",
            ),
        )
        assert record.fallback_used is True
        primary, fallback = record.attempts
        assert primary.outcome.value == "RATE_LIMITED"
        assert primary.prompt_tokens is None
        assert primary.completion_tokens is None
        assert primary.finish_reason is None
        assert fallback.outcome.value == "OK"
        assert fallback.prompt_tokens == 500
        assert fallback.completion_tokens == 50
        assert fallback.finish_reason == "length"

    def test_live_record_replays_through_the_service(self):
        from product_intelligence.research import (
            PRICE_RESULT_SCHEMA_VERSION,
            encode_price_aggregation_result,
        )

        run, assessment = _u1_run_and_assessment()
        record, _ = _persist_live(
            run, assessment, _v2_runtime(finish_reason="stop")
        )
        price_result = aggregate_listing_prices(REQUEST, (assessment,))
        PriceIntelligenceSnapshot.objects.create(
            run=run,
            schema_version=PRICE_RESULT_SCHEMA_VERSION,
            payload=encode_price_aggregation_result(price_result),
        )
        replay = replay_semantic_decision_record(run.id, 0)
        assert isinstance(replay, SemanticDecisionReplayV2Perf)
        assert replay.contract_binding == V2_PERF_CONTRACT_BINDING
        assert replay.case == record.case
        assert replay.record == record


# ===========================================================================
# 2. Historical coexistence (old records unchanged in the same ledger)
# ===========================================================================


class TestHistoricalCoexistence:
    def test_historical_v2_record_still_loads_and_replays_byte_identically(
        self,
    ):
        from product_intelligence.research import (
            PRICE_RESULT_SCHEMA_VERSION,
            encode_price_aggregation_result,
            derive_authority_tier,
            derive_identity_state_v2,
        )
        from product_intelligence.research import (
            AttemptOutcome,
            AttemptRole,
            SemanticDecisionAttempt,
            SemanticEvaluationStateV2,
            SemanticEvaluationV2,
        )
        from product_intelligence.research import (
            build_semantic_match_case_v2,
            build_v2_product_evidence_profile,
        )
        from product_intelligence.research.semantic_v2 import (
            SemanticReasonCodeV2 as _Reason,
        )

        run, assessment = _u1_run_and_assessment()
        observation = assessment.normalized_listing.observation
        context = derive_identity_state_v2(assessment)
        profile = build_v2_product_evidence_profile(
            observation=observation,
            context_provenances=frozenset(),
            matched_facts=frozenset(),
        )
        case = build_semantic_match_case_v2(
            case_id="candidate-historical",
            request=REQUEST,
            assessment=assessment,
            context=context,
            product_evidence=profile,
            context_provenances=frozenset(),
            reviewed_target_context=None,
        )
        evaluation = SemanticEvaluationV2.evaluated(
            V2SemanticDecision.MATCH, V2Confidence.HIGH, frozenset()
        )
        tier_decision = derive_authority_tier(
            context, evaluation, frozenset(), profile
        )
        historical = SemanticDecisionRecordV2.build(
            run_id=str(run.id),
            assessment_index=0,
            source_url=case.candidate_source_url,
            case=case,
            evaluation_state=SemanticEvaluationStateV2.EVALUATED,
            decision=V2SemanticDecision.MATCH,
            confidence=V2Confidence.HIGH,
            reason_code=_Reason.MATCH_DESCRIPTION_AND_ATTRIBUTES,
            conflict_classes=frozenset(),
            matched_attributes=(),
            conflicting_attributes=(),
            missing_critical_attributes=(),
            attempts=(
                SemanticDecisionAttempt(
                    AttemptRole.PRIMARY, 1, "amax", "qwen3.8-27b",
                    AttemptOutcome.OK,
                ),
            ),
            fallback_used=False,
            fallback_reason=None,
            error_type=None,
            actual_provider="amax",
            actual_model="qwen3.8-27b",
            evaluation_started_at="2026-02-10T12:00:00Z",
            evaluation_finished_at="2026-02-10T12:01:24.728000Z",
            product_evidence_quality=tier_decision.product_evidence_quality,
            relationship_authority=tier_decision.relationship_authority,
            authority_tier=tier_decision.tier,
            fired_rules=tier_decision.fired_rules,
        )
        persist_semantic_decision(run, historical)
        row = SemanticDecisionRecordRow.objects.get(
            run_id=run.id, assessment_index=0
        )
        original_bytes = json.dumps(
            row.payload, sort_keys=True, separators=(",", ":")
        ).encode("utf-8")

        # The live successor builder over the SAME run writes a
        # DIFFERENT binding (output schema 2) — both records coexist in
        # the ledger (one per assessment_index).
        outcomes = evaluate_semantic_matches_v2(
            REQUEST,
            (assessment,),
            context_provenances_by_assessment={},
            reviewed_target_context=None,
            runtime_v2=_v2_runtime(finish_reason="stop"),
        )
        price_result = aggregate_listing_prices(REQUEST, (assessment,))
        PriceIntelligenceSnapshot.objects.create(
            run=run,
            schema_version=PRICE_RESULT_SCHEMA_VERSION,
            payload=encode_price_aggregation_result(price_result),
        )
        live = build_semantic_decision_records_v2(
            run, price_result.assessments, outcomes
        )[0]
        assert live.output_schema_version == 2
        # Persist the live record under the next assessment index (the
        # (run, index) uniqueness is per index — the historical row at
        # index 0 stays untouched).
        live_at_1 = _rebind(live, run, 1)
        persist_semantic_decision(run, live_at_1)

        # The historical row is byte-unchanged and still decodes /
        # replays under the FROZEN V2 adapter.
        row.refresh_from_db()
        assert json.dumps(
            row.payload, sort_keys=True, separators=(",", ":")
        ).encode("utf-8") == original_bytes
        loaded = load_semantic_decision(run.id, 0)
        assert type(loaded) is SemanticDecisionRecordV2
        assert (
            loaded.semantic_contract_version,
            loaded.prompt_version,
            loaded.input_schema_version,
            loaded.output_schema_version,
            loaded.authority_contract_version,
        ) == V2_CONTRACT_BINDING
        replay = replay_semantic_decision_record(run.id, 0)
        assert replay.contract_binding == V2_CONTRACT_BINDING
        assert type(replay.record) is SemanticDecisionRecordV2
        # And the successor row loads under the PERF adapter (the
        # replay's assessment-binding check requires a persisted
        # assessment at that index — the load + binding axis is the
        # phase-0 surface; the full service replay over the live index
        # 0 row is pinned in TestLivePathInstrumentedRecord).
        loaded_perf = load_semantic_decision(run.id, 1)
        assert type(loaded_perf) is SemanticDecisionRecordV2Perf
        assert loaded_perf.output_schema_version == 2

    def test_v1_live_path_still_writes_zero_ledger_records(self):
        # The V1 path is untouched by the shared SemanticAttempt
        # extension: a V1-only evaluation writes zero rows.
        from product_intelligence.research import (
            ExtractionMethod,
            ListingObservation,
        )
        from product_intelligence.execution.evidence_writer import (
            ExecutionEvidenceWriter,
        )
        from product_intelligence.execution.semantic_integration import (
            evaluate_semantic_matches,
        )
        from product_intelligence.semantic import SemanticRuntime

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
        run = ResearchRun.objects.create_from_request(REQUEST)
        writer = ExecutionEvidenceWriter(run)
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
                provider_reported_model="qwen3.8-27b",
            ),
            fallback_transport=FakeSemanticModelTransport(
                responses={"*": v1_response},
                case_ids=("*",),
                provider_reported_model="Qwen3.6-27B-262K",
            ),
        )
        evaluate_semantic_matches(
            REQUEST, (assessment,), writer, runtime=runtime
        )
        assert SemanticDecisionRecordRow.objects.count() == 0


# ===========================================================================
# 3. The authority firewall holds over the instrumented record
# ===========================================================================


class TestFirewallOverInstrumentedRecord:
    def test_instrumented_match_high_needs_no_pricing_authority(self):
        # A V2 MATCH/HIGH persisted as the instrumented successor
        # record still feeds NOTHING into the deterministic surfaces:
        # the 4A aggregation over the run's assessments is
        # deterministic-only, and no review candidate exists.
        from product_intelligence.research import (
            PRICE_RESULT_SCHEMA_VERSION,
            decode_price_aggregation_result,
            encode_price_aggregation_result,
        )
        from product_intelligence.research.aggregation import (
            aggregate_reviewed_listing_prices,
        )

        run, assessment = _u1_run_and_assessment()
        record, _ = _persist_live(
            run, assessment, _v2_runtime(finish_reason="stop")
        )
        assert type(record) is SemanticDecisionRecordV2Perf
        assert record.decision is V2SemanticDecision.MATCH
        assert record.confidence is V2Confidence.HIGH

        # No review candidate of any kind for the run.
        assert AiAssistedReviewCandidate.objects.filter(
            run=run
        ).count() == 0

        price_result = aggregate_listing_prices(REQUEST, (assessment,))
        snapshot = PriceIntelligenceSnapshot.objects.create(
            run=run,
            schema_version=PRICE_RESULT_SCHEMA_VERSION,
            payload=encode_price_aggregation_result(price_result),
        )
        decoded = decode_price_aggregation_result(
            snapshot.payload, schema_version=snapshot.schema_version
        )
        reviewed = aggregate_reviewed_listing_prices(
            REQUEST, decoded.assessments, frozenset()
        )
        # Deterministic-only: the reviewed aggregation sees zero human
        # confirmations (the V2 record grants none) and the buckets
        # carry only the deterministic evidence.
        assert all(
            bucket.human_confirmed_count == 0 for bucket in reviewed.buckets
        )
        for bucket in reviewed.buckets:
            assert bucket.deterministic_count == bucket.count


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def adapter_is_claimed_by_the_perf_adapter(run_id, index) -> bool:
    row = SemanticDecisionRecordRow.objects.get(
        run_id=run_id, assessment_index=index
    )
    return (
        row.payload["contract"]["output_schema_version"] == 2
        and load_semantic_decision(run_id, index) is not None
    )


def _rebind(record, run, assessment_index):
    """The same record content re-bound to another assessment index
    (a test-world shape: one run, two ledger slots — the (run, index)
    uniqueness is per index). The section digests are recomputed by
    the builder over the re-bound universal binding."""
    from dataclasses import fields

    values = {f.name: getattr(record, f.name) for f in fields(record)}
    return SemanticDecisionRecordV2Perf.build(
        run_id=str(run.id),
        assessment_index=assessment_index,
        source_url=record.source_url,
        case=record.case,
        evaluation_state=record.evaluation_state,
        decision=record.decision,
        confidence=record.confidence,
        reason_code=record.reason_code,
        conflict_classes=record.conflict_classes,
        matched_attributes=record.matched_attributes,
        conflicting_attributes=record.conflicting_attributes,
        missing_critical_attributes=record.missing_critical_attributes,
        attempts=record.attempts,
        fallback_used=record.fallback_used,
        fallback_reason=record.fallback_reason,
        error_type=record.error_type,
        actual_provider=record.actual_provider,
        actual_model=record.actual_model,
        evaluation_started_at=record.evaluation_started_at,
        evaluation_finished_at=record.evaluation_finished_at,
        product_evidence_quality=record.product_evidence_quality,
        relationship_authority=record.relationship_authority,
        authority_tier=record.authority_tier,
        fired_rules=record.fired_rules,
    )
