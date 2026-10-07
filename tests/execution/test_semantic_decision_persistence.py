"""Tests for the S2-B semantic decision persistence service.

Covers ``product_intelligence.execution.semantic_decision_persistence``:

* persistence of ALL outcomes (MATCH / NO_MATCH / UNCERTAIN / runtime
  failure with fallback / runtime failure without fallback / not
  evaluated) with exact load round-trips;
* the whole-artifact tamper anchor (the row's separate digest column)
  catches DB-level payload mutation;
* replay through the service with full binding verification against the
  run's persisted evidence (request identity + snapshot assessment
  binding);
* absence semantics (legacy runs: load returns None — nothing is
  fabricated);
* ZERO live AI / provider / network work across persist + load + replay;
* S2-B no-wiring: the CURRENT V1 semantic execution path creates and
  reads ZERO records; the service owns no authority derivation logic.
"""

from __future__ import annotations

import hashlib
import json
import uuid
from unittest import mock

import pytest
from django.db import IntegrityError  # noqa: F401  (used by constraint tests elsewhere)

from product_intelligence.domain import ResearchRequest
from product_intelligence.research import (
    AttemptOutcome,
    AttemptRole,
    AuthorityRuleV2,
    AuthorityTier,
    ExtractionMethod,
    ListingObservation,
    ProductEvidenceDimension,
    ProductEvidenceFactV2,
    ProductEvidenceProfileV2,
    CandidateProductEvidenceSource,
    RelationshipRequirement,
    SemanticDecisionRecord,
    SemanticEvaluationStateV2,
    SemanticFallbackReason,
    SemanticFailureClass,
    SemanticDecisionAttempt,
    V2Confidence,
    V2SemanticDecision,
    PRICE_RESULT_SCHEMA_VERSION,
    aggregate_listing_prices,
    assess_listing_identity,
    derive_identity_state_v2,
    derive_product_evidence_quality,
    derive_relationship_authority,
    derive_authority_tier,
    normalize_listing_observation,
    substate_relationship_requirement,
    encode_price_aggregation_result,
    SemanticEvaluationV2,
)
from product_intelligence.runs.models import (
    AiAssistedReviewCandidate,
    PriceIntelligenceSnapshot,
    ResearchRun,
    SemanticDecisionRecord as SemanticDecisionRecordRow,
)
from product_intelligence.execution.semantic_decision_persistence import (
    SemanticDecisionAlreadyRecordedError,
    SemanticDecisionBindingError,
    SemanticDecisionPersistenceError,
    SemanticDecisionPayloadTamperedError,
    SemanticDecisionRecordNotFoundError,
    load_semantic_decision,
    persist_semantic_decision,
    replay_semantic_decision_record,
)
from product_intelligence.research.semantic_decision_codec import (
    SEMANTIC_DECISION_SCHEMA_VERSION,
    SemanticDecisionCodecError,
)

REQUEST = ResearchRequest(
    manufacturer_part_number="ABC-123", description="A test product"
)
SOURCE_URL = "https://example.com/test-product"
TITLE_SOURCES = frozenset({CandidateProductEvidenceSource.LISTING_PRODUCT_TITLE})


@pytest.fixture(autouse=True)
def _cleanup():
    yield
    SemanticDecisionRecordRow.objects.all().delete()
    AiAssistedReviewCandidate.objects.all().delete()
    PriceIntelligenceSnapshot.objects.all().delete()
    ResearchRun.objects.all().delete()


# ---------------------------------------------------------------------------
# Scenario builders: a real run + real snapshot + a bound artifact
# ---------------------------------------------------------------------------


def _make_run_and_snapshot() -> tuple[ResearchRun, object]:
    """A run whose snapshot carries one real U1_TITLE_MPN assessment."""
    observation = ListingObservation(
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
    normalized = normalize_listing_observation(observation)
    assessment = assess_listing_identity(REQUEST, normalized)
    run = ResearchRun.objects.create_from_request(REQUEST)
    price_result = aggregate_listing_prices(REQUEST, (assessment,))
    snapshot = PriceIntelligenceSnapshot.objects.create(
        run=run,
        schema_version=PRICE_RESULT_SCHEMA_VERSION,
        payload=encode_price_aggregation_result(price_result),
    )
    return run, assessment


def _case_id_for(url: str, index: int) -> str:
    url_hash = hashlib.sha256(url.encode()).hexdigest()[:8]
    return f"candidate-{url_hash}-{index}"


def _strong_profile() -> ProductEvidenceProfileV2:
    return ProductEvidenceProfileV2(
        has_usable_product_title=True,
        matched_facts=frozenset(
            {
                ProductEvidenceFactV2(
                    ProductEvidenceDimension.CAPACITY, TITLE_SOURCES
                ),
                ProductEvidenceFactV2(
                    ProductEvidenceDimension.INTERFACE, TITLE_SOURCES
                ),
            }
        ),
    )


def _limited_profile() -> ProductEvidenceProfileV2:
    return ProductEvidenceProfileV2(
        has_usable_product_title=True, matched_facts=frozenset()
    )


def _primary_ok() -> SemanticDecisionAttempt:
    return SemanticDecisionAttempt(
        AttemptRole.PRIMARY, 1, "amax", "qwen3.8-27b", AttemptOutcome.OK
    )


def _primary_failed(outcome: AttemptOutcome) -> SemanticDecisionAttempt:
    return SemanticDecisionAttempt(
        AttemptRole.PRIMARY, 1, "amax", "qwen3.8-27b", outcome
    )


def _fallback_ok() -> SemanticDecisionAttempt:
    return SemanticDecisionAttempt(
        AttemptRole.FALLBACK, 2, "vllm-262k", "Qwen3.6-27B-262K",
        AttemptOutcome.OK,
    )


def _fallback_failed(outcome: AttemptOutcome) -> SemanticDecisionAttempt:
    return SemanticDecisionAttempt(
        AttemptRole.FALLBACK, 2, "vllm-262k", "Qwen3.6-27B-262K", outcome
    )


def _build_artifact(
    run: ResearchRun,
    assessment,
    *,
    profile=None,
    provenances=None,
    evaluation_state=SemanticEvaluationStateV2.EVALUATED,
    decision=None,
    confidence=None,
    conflict_classes=frozenset(),
    reason_code="exact_mpn_match",
    matched_attributes=("mpn", "capacity"),
    conflicting_attributes=(),
    missing_critical_attributes=(),
    attempts=(_primary_ok(),),
    fallback_used=False,
    fallback_reason=None,
    error_type=None,
    actual_provider=None,
    actual_model=None,
    started="2026-02-10T12:00:00Z",
    finished="2026-02-10T12:00:03.250000Z",
    source_url: str = SOURCE_URL,
    target_mpn: str | None = None,
    target_description: str | None = None,
) -> SemanticDecisionRecord:
    context = derive_identity_state_v2(assessment)
    profile = profile if profile is not None else _strong_profile()
    provenances = frozenset() if provenances is None else provenances
    if evaluation_state is SemanticEvaluationStateV2.EVALUATED:
        if actual_provider is None:
            ok = attempts[-1]
            actual_provider, actual_model = ok.provider, ok.model
        evaluation = SemanticEvaluationV2.evaluated(
            decision, confidence, conflict_classes
        )
    elif evaluation_state is SemanticEvaluationStateV2.RUNTIME_FAILURE:
        evaluation = SemanticEvaluationV2.runtime_failure()
    else:
        evaluation = SemanticEvaluationV2.not_evaluated()
    tier_decision = derive_authority_tier(
        context, evaluation, provenances, profile
    )
    return SemanticDecisionRecord.build(
        run_id=str(run.id),
        assessment_index=0,
        source_url=source_url,
        identity_state=context.state,
        substate=context.substate,
        relationship_signals=context.relationship_signals,
        normalized_requested_part_number=context.normalized_requested_part_number,
        normalized_candidate_part_number=context.normalized_candidate_part_number,
        relationship_requirement=substate_relationship_requirement(
            context.substate, context.primary_relationship_signal
        ),
        product_evidence=profile,
        product_evidence_quality=derive_product_evidence_quality(
            profile, provenances
        ),
        context_provenances=provenances,
        case_id=_case_id_for(SOURCE_URL, 0),
        target_mpn=REQUEST.manufacturer_part_number
        if target_mpn is None
        else target_mpn,
        target_description=REQUEST.description
        if target_description is None
        else target_description,
        candidate_title="ABC-123 1TB NVMe Drive",
        candidate_mpn_field=None,
        candidate_sku=None,
        candidate_specs=None,
        evidence_source="TITLE_TEXT",
        evaluation_state=evaluation_state,
        decision=decision,
        confidence=confidence,
        conflict_classes=conflict_classes,
        reason_code=reason_code,
        matched_attributes=matched_attributes,
        conflicting_attributes=conflicting_attributes,
        missing_critical_attributes=missing_critical_attributes,
        attempts=attempts,
        fallback_used=fallback_used,
        fallback_reason=fallback_reason,
        error_type=error_type,
        actual_provider=actual_provider,
        actual_model=actual_model,
        evaluation_started_at=started,
        evaluation_finished_at=finished,
        relationship_authority=derive_relationship_authority(
            context, provenances
        ),
        authority_tier=tier_decision.tier,
        fired_rules=tier_decision.fired_rules,
    )


# ===========================================================================
# Persist + load round-trips (all outcomes)
# ===========================================================================


class TestPersistLoad:
    @pytest.mark.parametrize(
        "kwargs",
        [
            dict(
                decision=V2SemanticDecision.MATCH,
                confidence=V2Confidence.HIGH,
            ),
            dict(
                decision=V2SemanticDecision.NO_MATCH,
                confidence=V2Confidence.MEDIUM,
                reason_code="capacity_mismatch",
                matched_attributes=(),
                profile=_limited_profile(),
            ),
            dict(
                decision=V2SemanticDecision.UNCERTAIN,
                confidence=V2Confidence.LOW,
                reason_code="insufficient_evidence",
                matched_attributes=(),
                profile=_limited_profile(),
            ),
            dict(
                evaluation_state=SemanticEvaluationStateV2.RUNTIME_FAILURE,
                decision=None,
                confidence=None,
                reason_code=None,
                matched_attributes=(),
                attempts=(
                    _primary_failed(AttemptOutcome.TIMEOUT),
                    _fallback_failed(AttemptOutcome.CASE_REJECTED),
                ),
                fallback_used=True,
                fallback_reason=SemanticFallbackReason.TIMEOUT,
                error_type=SemanticFailureClass.BOTH_UNAVAILABLE,
            ),
            dict(
                evaluation_state=SemanticEvaluationStateV2.RUNTIME_FAILURE,
                decision=None,
                confidence=None,
                reason_code=None,
                matched_attributes=(),
                attempts=(_primary_failed(AttemptOutcome.CASE_REJECTED),),
                error_type=SemanticFailureClass.PRIMARY_CASE_REJECTED,
            ),
            dict(
                evaluation_state=SemanticEvaluationStateV2.NOT_EVALUATED,
                decision=None,
                confidence=None,
                reason_code=None,
                matched_attributes=(),
                attempts=(),
                started=None,
                finished=None,
            ),
        ],
        ids=[
            "match",
            "no_match",
            "uncertain",
            "runtime_failure_fallback",
            "runtime_failure_no_fallback",
            "not_evaluated",
        ],
    )
    def test_round_trip(self, kwargs) -> None:
        run, assessment = _make_run_and_snapshot()
        artifact = _build_artifact(run, assessment, **kwargs)
        row = persist_semantic_decision(run, artifact)
        assert row.id is not None
        assert row.schema_version == SEMANTIC_DECISION_SCHEMA_VERSION
        loaded = load_semantic_decision(run.id, 0)
        assert loaded == artifact

    def test_persist_stores_digest_anchor(self) -> None:
        from product_intelligence.research import canonical_payload_digest

        run, assessment = _make_run_and_snapshot()
        artifact = _build_artifact(
            run, assessment,
            decision=V2SemanticDecision.MATCH, confidence=V2Confidence.HIGH,
        )
        row = persist_semantic_decision(run, artifact)
        assert row.payload_digest == canonical_payload_digest(
            encode_payload_of(artifact)
        )
        assert len(row.payload_digest) == 64

    def test_persist_run_id_mismatch_fails_closed(self) -> None:
        run, assessment = _make_run_and_snapshot()
        other_run = ResearchRun.objects.create_from_request(
            ResearchRequest(manufacturer_part_number="ZZZ", description="d")
        )
        artifact = _build_artifact(
            other_run, assessment,
            decision=V2SemanticDecision.MATCH, confidence=V2Confidence.HIGH,
        )
        with pytest.raises(SemanticDecisionPersistenceError, match="run_id"):
            persist_semantic_decision(run, artifact)
        assert SemanticDecisionRecordRow.objects.count() == 0

    def test_persist_never_overwrites(self) -> None:
        run, assessment = _make_run_and_snapshot()
        artifact = _build_artifact(
            run, assessment,
            decision=V2SemanticDecision.MATCH, confidence=V2Confidence.HIGH,
        )
        first = persist_semantic_decision(run, artifact)
        with pytest.raises(SemanticDecisionAlreadyRecordedError):
            persist_semantic_decision(run, artifact)
        # The first record is intact.
        assert load_semantic_decision(run.id, 0) == artifact
        assert SemanticDecisionRecordRow.objects.filter(run=run).count() == 1

    def test_load_absent_returns_none_not_failure(self) -> None:
        """Legacy absence semantics: a run without a record loads as None —
        'legacy semantic provenance unavailable under V2', never
        NO_MATCH / NOT_EVALUATED / AI failure, never a fabricated row."""
        run, _assessment = _make_run_and_snapshot()
        assert load_semantic_decision(run.id, 0) is None
        assert load_semantic_decision(str(uuid.uuid4()), 0) is None
        assert SemanticDecisionRecordRow.objects.count() == 0

    def test_db_level_payload_tamper_detected(self) -> None:
        run, assessment = _make_run_and_snapshot()
        artifact = _build_artifact(
            run, assessment,
            decision=V2SemanticDecision.MATCH, confidence=V2Confidence.HIGH,
        )
        row = persist_semantic_decision(run, artifact)
        # A write that bypasses the service (raw QuerySet update) corrupts
        # the payload; the separate digest column must catch it on read.
        tampered = json.loads(json.dumps(row.payload))
        tampered["derived"]["authority_tier"] = "MACHINE_VERIFIED"
        SemanticDecisionRecordRow.objects.filter(pk=row.pk).update(
            payload=tampered
        )
        with pytest.raises(SemanticDecisionPayloadTamperedError):
            load_semantic_decision(run.id, 0)
        with pytest.raises(SemanticDecisionPayloadTamperedError):
            replay_semantic_decision_record(run.id, 0)

    def test_unsupported_row_schema_version_fails_closed(self) -> None:
        run, assessment = _make_run_and_snapshot()
        artifact = _build_artifact(
            run, assessment,
            decision=V2SemanticDecision.MATCH, confidence=V2Confidence.HIGH,
        )
        row = persist_semantic_decision(run, artifact)
        SemanticDecisionRecordRow.objects.filter(pk=row.pk).update(
            schema_version=99
        )
        with pytest.raises(SemanticDecisionCodecError, match="unsupported"):
            load_semantic_decision(run.id, 0)


def encode_payload_of(artifact) -> dict:
    from product_intelligence.research import encode_semantic_decision_record

    return encode_semantic_decision_record(artifact)


# ===========================================================================
# Replay through the service (binding verification)
# ===========================================================================


class TestServiceReplay:
    def test_replay_full_path_success(self) -> None:
        run, assessment = _make_run_and_snapshot()
        artifact = _build_artifact(
            run, assessment,
            decision=V2SemanticDecision.MATCH, confidence=V2Confidence.HIGH,
        )
        persist_semantic_decision(run, artifact)
        replay = replay_semantic_decision_record(run.id, 0)
        assert replay.record == artifact
        assert replay.semantic_evaluation.decision is V2SemanticDecision.MATCH
        assert replay.semantic_evaluation.confidence is V2Confidence.HIGH
        # U1 + MATCH/HIGH + STRONG: the S2-A-FU2 recorded tier.
        assert replay.authority_decision.tier is AuthorityTier.AI_ASSISTED_COMPARABLE
        assert replay.relationship_requirement is (
            RelationshipRequirement.NOT_REQUIRED
        )
        assert replay.prompt_input.target_mpn == "ABC-123"

    def test_replay_runtime_failure_full_path(self) -> None:
        run, assessment = _make_run_and_snapshot()
        artifact = _build_artifact(
            run, assessment,
            evaluation_state=SemanticEvaluationStateV2.RUNTIME_FAILURE,
            decision=None,
            confidence=None,
            reason_code=None,
            matched_attributes=(),
            attempts=(
                _primary_failed(AttemptOutcome.TIMEOUT),
                _fallback_failed(AttemptOutcome.CASE_REJECTED),
            ),
            fallback_used=True,
            fallback_reason=SemanticFallbackReason.TIMEOUT,
            error_type=SemanticFailureClass.BOTH_UNAVAILABLE,
        )
        persist_semantic_decision(run, artifact)
        replay = replay_semantic_decision_record(run.id, 0)
        assert replay.authority_decision.tier is AuthorityTier.SEMANTIC_UNAVAILABLE
        assert AuthorityRuleV2.RUNTIME_FAILURE in replay.authority_decision.fired_rules

    def test_replay_source_url_binding_mismatch_fails(self) -> None:
        run, assessment = _make_run_and_snapshot()
        artifact = _build_artifact(
            run, assessment,
            decision=V2SemanticDecision.MATCH,
            confidence=V2Confidence.HIGH,
            source_url="https://attacker.example/other",
        )
        persist_semantic_decision(run, artifact)
        with pytest.raises(SemanticDecisionBindingError, match="source URL"):
            replay_semantic_decision_record(run.id, 0)

    def test_replay_request_identity_mismatch_fails(self) -> None:
        run, assessment = _make_run_and_snapshot()
        artifact = _build_artifact(
            run, assessment,
            decision=V2SemanticDecision.MATCH,
            confidence=V2Confidence.HIGH,
            target_mpn="DIFFERENT-MPN",
        )
        persist_semantic_decision(run, artifact)
        with pytest.raises(SemanticDecisionBindingError, match="request identity"):
            replay_semantic_decision_record(run.id, 0)

    def test_replay_out_of_range_index_fails(self) -> None:
        run, assessment = _make_run_and_snapshot()
        artifact = _build_artifact(
            run, assessment,
            decision=V2SemanticDecision.MATCH,
            confidence=V2Confidence.HIGH,
        )
        # Rebuild the artifact around an out-of-range binding index with
        # consistent digests (the record layer does not know the snapshot's
        # assessment count — the service's binding check does).
        from product_intelligence.research import (
            record_output_digest,
        )
        from product_intelligence.research import SemanticDecisionRecord as _R
        from product_intelligence.research.semantic_decision_record import (
            _binding_section,
            _contract_section,
            _context_section,
            _product_evidence_section,
            canonical_sha256,
        )

        kwargs = artifact.__dict__.copy()
        kwargs["assessment_index"] = 7
        kwargs["input_digest"] = canonical_sha256(
            {
                "binding": _binding_section(
                    artifact.run_id, 7, artifact.source_url
                ),
                "contract": _contract_section(),
                "context": _context_section(
                    artifact.identity_state,
                    artifact.substate,
                    artifact.relationship_signals,
                    artifact.normalized_requested_part_number,
                    artifact.normalized_candidate_part_number,
                    artifact.relationship_requirement,
                    artifact.context_provenances,
                ),
                "product_evidence": _product_evidence_section(
                    artifact.product_evidence,
                    artifact.product_evidence_quality,
                ),
                "prompt_input": artifact.prompt_input().canonical(),
            }
        )
        kwargs["output_digest"] = record_output_digest(artifact)
        artifact7 = _R(**kwargs)
        persist_semantic_decision(run, artifact7)
        with pytest.raises(SemanticDecisionBindingError, match="out of range"):
            replay_semantic_decision_record(run.id, 7)

    def test_replay_run_without_snapshot_fails(self) -> None:
        run, assessment = _make_run_and_snapshot()
        artifact = _build_artifact(
            run, assessment,
            decision=V2SemanticDecision.MATCH,
            confidence=V2Confidence.HIGH,
        )
        persist_semantic_decision(run, artifact)
        PriceIntelligenceSnapshot.objects.filter(run=run).delete()
        with pytest.raises(SemanticDecisionBindingError, match="no PriceIntelligenceSnapshot"):
            replay_semantic_decision_record(run.id, 0)

    def test_replay_absent_record_raises_not_none(self) -> None:
        run, _assessment = _make_run_and_snapshot()
        with pytest.raises(SemanticDecisionRecordNotFoundError):
            replay_semantic_decision_record(run.id, 0)

    def test_replay_cross_run_fails_closed(self) -> None:
        run, assessment = _make_run_and_snapshot()
        artifact = _build_artifact(
            run, assessment,
            decision=V2SemanticDecision.MATCH,
            confidence=V2Confidence.HIGH,
        )
        persist_semantic_decision(run, artifact)
        other_run = ResearchRun.objects.create_from_request(
            ResearchRequest(manufacturer_part_number="ABC-123", description="A test product")
        )
        # Same request, different run: the record must not replay against
        # the other run's evidence.
        PriceIntelligenceSnapshot.objects.create(
            run=other_run,
            schema_version=PRICE_RESULT_SCHEMA_VERSION,
            payload=encode_price_aggregation_result(
                aggregate_listing_prices(REQUEST, (assessment,))
            ),
        )
        # The other run has NO record: replay there fails closed (not found),
        # and the original run's record cannot be read through the other
        # run's identity.
        with pytest.raises(SemanticDecisionRecordNotFoundError):
            replay_semantic_decision_record(other_run.id, 0)
        assert load_semantic_decision(other_run.id, 0) is None


# ===========================================================================
# Human-review separation
# ===========================================================================


class TestHumanReviewSeparation:
    def test_record_creation_creates_no_review_candidate(self) -> None:
        run, assessment = _make_run_and_snapshot()
        artifact = _build_artifact(
            run, assessment,
            decision=V2SemanticDecision.MATCH, confidence=V2Confidence.HIGH,
        )
        persist_semantic_decision(run, artifact)
        assert AiAssistedReviewCandidate.objects.filter(run=run).count() == 0
        assert SemanticDecisionRecordRow.objects.filter(run=run).count() == 1

    def test_review_candidate_coexists_with_record_unchanged(self) -> None:
        """When both exist (the S2-C shape), each keeps its own semantics:
        the review candidate's state machine is untouched by the record."""
        run, assessment = _make_run_and_snapshot()
        artifact = _build_artifact(
            run, assessment,
            decision=V2SemanticDecision.MATCH, confidence=V2Confidence.HIGH,
        )
        persist_semantic_decision(run, artifact)
        candidate = AiAssistedReviewCandidate.objects.create(
            run=run,
            assessment_index=0,
            source_url=SOURCE_URL,
            target_mpn="ABC-123",
            target_description="A test product",
            candidate_title="ABC-123 1TB NVMe Drive",
            candidate_mpn_field="",
            candidate_sku="",
            candidate_specs="",
            evidence_source="TITLE_TEXT",
            semantic_confidence="HIGH",
            semantic_reason_code="exact_mpn_match",
            semantic_matched_attributes=["mpn"],
            semantic_conflicting_attributes=[],
            actual_provider="amax",
            actual_model="qwen3.8-27b",
            prompt_version="1.1",
        )
        assert candidate.review_state == "UNREVIEWED"
        # The ledger record is unaffected by the review row existing.
        assert load_semantic_decision(run.id, 0) == artifact
        replay = replay_semantic_decision_record(run.id, 0)
        assert replay.record == artifact


# ===========================================================================
# Zero live work
# ===========================================================================


class TestZeroLiveWork:
    def _arm_sentinels(self):
        def boom(*args, **kwargs):
            raise AssertionError("live semantic/provider/network call made")

        return [
            mock.patch(
                "product_intelligence.semantic.runtime.SemanticRuntime.evaluate",
                side_effect=boom,
            ),
            mock.patch(
                "product_intelligence.semantic.transport.get_openai_transport_for_provider",
                side_effect=boom,
            ),
            mock.patch("urllib.request.urlopen", side_effect=boom),
        ]

    def test_persist_load_replay_perform_zero_live_work(self) -> None:
        run, assessment = _make_run_and_snapshot()
        artifact = _build_artifact(
            run, assessment,
            decision=V2SemanticDecision.MATCH, confidence=V2Confidence.HIGH,
        )
        sentinels = self._arm_sentinels()
        try:
            for s in sentinels:
                s.start()
            persist_semantic_decision(run, artifact)
            assert load_semantic_decision(run.id, 0) == artifact
            replay = replay_semantic_decision_record(run.id, 0)
        finally:
            for s in reversed(sentinels):
                s.stop()
        assert replay.authority_decision.tier is AuthorityTier.AI_ASSISTED_COMPARABLE


# ===========================================================================
# S2-B no-wiring: current V1 execution does not touch the ledger
# ===========================================================================


class TestNoLiveWiring:
    def test_v1_semantic_execution_creates_no_records(self) -> None:
        """The CURRENT V1 semantic execution path (FU3B integration) runs a
        real (fake-transport) evaluation and persists ZERO
        SemanticDecisionRecord rows: S2-B defines the persistence API;
        live wiring is S2-C."""
        from product_intelligence.execution.evidence_writer import (
            ExecutionEvidenceWriter,
        )
        from product_intelligence.execution.semantic_integration import (
            evaluate_semantic_matches,
        )
        from product_intelligence.semantic import SemanticRuntime
        from product_intelligence.semantic.transport import (
            FakeSemanticModelTransport,
        )

        run, assessment = _make_run_and_snapshot()
        writer = ExecutionEvidenceWriter(run)
        match_json = json.dumps(
            {
                "decision": "MATCH",
                "confidence": "HIGH",
                "matched_attributes": ["mpn"],
                "conflicting_attributes": [],
                "missing_critical_attributes": [],
                "reason_code": "exact_mpn_match",
            }
        )
        fake = FakeSemanticModelTransport(
            responses={_case_id_for(SOURCE_URL, 0): match_json},
            case_ids=(_case_id_for(SOURCE_URL, 0),),
            provider_reported_model="qwen3.8-27b",
        )
        runtime = SemanticRuntime(
            primary_transport=fake, fallback_transport=fake
        )
        results = evaluate_semantic_matches(
            REQUEST, (assessment,), writer, runtime=runtime
        )
        # The V1 path produced its (unchanged) in-memory result...
        assert len(results) == 1
        assert results[0].semantic_result.decision.value == "MATCH"
        # ...and wrote nothing to the V2 ledger.
        assert SemanticDecisionRecordRow.objects.count() == 0
        assert AiAssistedReviewCandidate.objects.count() == 0

    def test_v1_semantic_execution_does_not_read_records(self) -> None:
        """A pre-existing record is invisible to the current V1 execution
        path: no read, no mutation."""
        from product_intelligence.execution.evidence_writer import (
            ExecutionEvidenceWriter,
        )
        from product_intelligence.execution.semantic_integration import (
            evaluate_semantic_matches,
        )
        from product_intelligence.semantic import SemanticRuntime
        from product_intelligence.semantic.transport import (
            FakeSemanticModelTransport,
        )

        run, assessment = _make_run_and_snapshot()
        artifact = _build_artifact(
            run, assessment,
            decision=V2SemanticDecision.MATCH, confidence=V2Confidence.HIGH,
        )
        row = persist_semantic_decision(run, artifact)
        before = row.payload

        writer = ExecutionEvidenceWriter(run)
        match_json = json.dumps(
            {
                "decision": "NO_MATCH",
                "confidence": "HIGH",
                "matched_attributes": [],
                "conflicting_attributes": ["capacity"],
                "missing_critical_attributes": [],
                "reason_code": "capacity_mismatch",
            }
        )
        fake = FakeSemanticModelTransport(
            responses={_case_id_for(SOURCE_URL, 0): match_json},
            case_ids=(_case_id_for(SOURCE_URL, 0),),
            provider_reported_model="qwen3.8-27b",
        )
        runtime = SemanticRuntime(
            primary_transport=fake, fallback_transport=fake
        )
        evaluate_semantic_matches(
            REQUEST, (assessment,), writer, runtime=runtime
        )
        row.refresh_from_db()
        assert row.payload == before
        assert SemanticDecisionRecordRow.objects.count() == 1

    def test_only_the_service_module_references_the_ledger_in_execution(
        self,
    ) -> None:
        """Source-level no-wiring: no execution module other than the S2-B
        service references the semantic-decision persistence surface."""
        import product_intelligence.execution
        from pathlib import Path

        root = Path(product_intelligence.execution.__file__).parent
        for path in sorted(root.rglob("*.py")):
            if path.name == "semantic_decision_persistence.py":
                continue
            source = path.read_text(encoding="utf-8")
            assert "semantic_decision_persistence" not in source, path.name
            assert "SemanticDecisionRecordRow" not in source, path.name

    def test_web_layer_references_no_ledger(self) -> None:
        """No UI wiring in S2-B: the web layer never names the ledger."""
        import product_intelligence.web
        from pathlib import Path

        root = Path(product_intelligence.web.__file__).parent
        for path in sorted(root.rglob("*.py")):
            source = path.read_text(encoding="utf-8")
            assert "semantic_decision" not in source.lower(), path.name
            assert "SemanticDecisionRecord" not in source, path.name

    def test_service_owns_no_authority_derivation_logic(self) -> None:
        """The persistence service composes research's codec + replay; it
        does not itself import any S2-A authority derivation function
        (the persistence layer does not gain authority logic)."""
        import ast
        import product_intelligence.execution.semantic_decision_persistence as svc
        from pathlib import Path

        source = Path(svc.__file__).read_text(encoding="utf-8")
        tree = ast.parse(source)
        imported_names = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom):
                imported_names.update(alias.name for alias in node.names)
        assert not (imported_names & {
            "derive_authority_tier",
            "derive_identity_state_v2",
            "derive_product_evidence_quality",
            "derive_relationship_authority",
            "substate_relationship_requirement",
        }), (
            "the persistence service must not import authority derivation "
            "functions; it composes the research-layer replay"
        )
        # It does compose the pure replay (the authority logic's home).
        assert "replay_semantic_decision" in imported_names
