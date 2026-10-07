"""Tests for the pure zero-live replay / reconstruction path (S2-B).

Covers ``product_intelligence.research.semantic_decision_replay``:

* exact reconstruction of the historical semantic evaluation for ALL
  outcomes (MATCH / NO_MATCH / UNCERTAIN / runtime failure / not
  evaluated, with and without fallback);
* exact reconstruction of the S2-A authority inputs (V2 context, product
  evidence profile, context provenances);
* the derived-agreement proof (stored audit snapshots vs re-derivation);
* the contract-binding gate (unknown / future versions refused explicitly;
  historical versions never replaced by current module constants);
* ZERO live AI calls and ZERO provider/network calls (armed fail-fast
  sentinels).
"""

from __future__ import annotations

import dataclasses
from unittest import mock

import pytest

from product_intelligence.research import (
    AttemptOutcome,
    AuthorityRuleV2,
    AuthorityTier,
    ConflictClass,
    ContextProvenance,
    ProductEvidenceProfileV2,
    ProductEvidenceQuality,
    RelationshipAuthority,
    RelationshipRequirement,
    SemanticEvaluationStateV2,
    SemanticEvaluationV2,
    SemanticFallbackReason,
    SemanticFailureClass,
    V2Confidence,
    V2SemanticDecision,
    SUPPORTED_CONTRACT_BINDINGS,
    ProductEvidenceFactV2,
    ProductEvidenceDimension,
    CandidateProductEvidenceSource,
    reconstruct_identity_context,
    reconstruct_semantic_evaluation,
    replay_semantic_decision,
)
from product_intelligence.research.semantic_decision_replay import (
    SemanticDecisionReplay,
    SemanticDecisionReplayError,
)

from tests.research.test_semantic_decision_record import (
    _build,
    _fallback_failed,
    _fallback_ok,
    _limited_profile,
    _match_record,
    _primary_failed,
    _primary_ok,
    _strong_profile,
    _u1,
)

def _Record_build_primary_ok():
    from product_intelligence.research import (
        AttemptRole,
        SemanticDecisionAttempt,
    )

    return SemanticDecisionAttempt(
        role=AttemptRole.PRIMARY,
        attempt_number=1,
        provider="amax",
        model="qwen3.8-27b",
        outcome=AttemptOutcome.OK,
    )


TITLE_SOURCES = frozenset({CandidateProductEvidenceSource.LISTING_PRODUCT_TITLE})


def _not_evaluated_record():
    return _build(
        evaluation_state=SemanticEvaluationStateV2.NOT_EVALUATED,
        decision=None,
        confidence=None,
        reason_code=None,
        matched_attributes=(),
        attempts=(),
        started=None,
        finished=None,
    )


def _runtime_failure_record():
    return _build(
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


def _fallback_match_record():
    return _build(
        decision=V2SemanticDecision.MATCH,
        confidence=V2Confidence.LOW,
        reason_code="title_mpn_match",
        profile=_limited_profile(),
        attempts=(
            _primary_failed(AttemptOutcome.MALFORMED_JSON),
            _fallback_ok(),
        ),
        fallback_used=True,
        fallback_reason=SemanticFallbackReason.MALFORMED_JSON,
    )


# ===========================================================================
# E1. Exact reconstruction of the historical evaluation
# ===========================================================================


class TestExactEvaluationReconstruction:
    def test_match_replay_exact(self) -> None:
        record = _match_record()
        replay = replay_semantic_decision(record)
        assert replay.semantic_evaluation == SemanticEvaluationV2.evaluated(
            V2SemanticDecision.MATCH,
            V2Confidence.HIGH,
            frozenset(),
        )
        assert replay.record is record

    def test_no_match_replay_exact(self) -> None:
        record = _build(
            decision=V2SemanticDecision.NO_MATCH,
            confidence=V2Confidence.MEDIUM,
            reason_code="capacity_mismatch",
            matched_attributes=(),
            conflicting_attributes=("capacity",),
            profile=_limited_profile(),
        )
        replay = replay_semantic_decision(record)
        assert replay.semantic_evaluation == SemanticEvaluationV2.evaluated(
            V2SemanticDecision.NO_MATCH,
            V2Confidence.MEDIUM,
            frozenset(),
        )

    def test_uncertain_replay_exact(self) -> None:
        conflicts = frozenset({ConflictClass.BRAND, ConflictClass.CAPACITY})
        record = _build(
            decision=V2SemanticDecision.UNCERTAIN,
            confidence=V2Confidence.LOW,
            reason_code="brand_and_capacity",
            conflict_classes=conflicts,
            profile=_limited_profile(),
        )
        replay = replay_semantic_decision(record)
        assert replay.semantic_evaluation == SemanticEvaluationV2.evaluated(
            V2SemanticDecision.UNCERTAIN,
            V2Confidence.LOW,
            conflicts,
        )
        # The structured conflict classes are exactly what was recorded.
        assert replay.semantic_evaluation.conflict_classes == conflicts

    def test_runtime_failure_replay_exact(self) -> None:
        replay = replay_semantic_decision(_runtime_failure_record())
        assert replay.semantic_evaluation == SemanticEvaluationV2.runtime_failure()
        assert replay.semantic_evaluation.decision is None
        # A runtime failure replays as SEMANTIC_UNAVAILABLE — never as
        # NO_MATCH and never as exclusion on evidence grounds.
        assert replay.authority_decision.tier is AuthorityTier.SEMANTIC_UNAVAILABLE
        assert AuthorityRuleV2.RUNTIME_FAILURE in replay.authority_decision.fired_rules

    def test_not_evaluated_replay_exact(self) -> None:
        replay = replay_semantic_decision(_not_evaluated_record())
        assert replay.semantic_evaluation == SemanticEvaluationV2.not_evaluated()
        # NOT_EVALUATED is not an AI failure: the deterministic policy tier
        # governs the entry point.
        assert replay.authority_decision.tier is AuthorityTier.NEEDS_REVIEW
        assert AuthorityRuleV2.STATE_POLICY_DETERMINISTIC in (
            replay.authority_decision.fired_rules
        )

    def test_fallback_match_replay_preserves_provenance(self) -> None:
        replay = replay_semantic_decision(_fallback_match_record())
        record = replay.record
        assert record.fallback_used is True
        assert record.fallback_reason is SemanticFallbackReason.MALFORMED_JSON
        assert record.attempts[0].outcome is AttemptOutcome.MALFORMED_JSON
        assert record.attempts[1].outcome is AttemptOutcome.OK
        # The accepted answer is attributed to the fallback provider/model.
        assert record.actual_provider == "vllm-262k"
        assert record.actual_model == "Qwen3.6-27B-262K"
        assert replay.prompt_input.case_id == record.case_id


# ===========================================================================
# E2. Exact reconstruction of the S2-A authority inputs
# ===========================================================================


class TestAuthorityInputReconstruction:
    def test_identity_context_reconstructed(self) -> None:
        record = _match_record()
        replay = replay_semantic_decision(record)
        assert replay.identity_context == _u1()
        assert replay.identity_context == reconstruct_identity_context(record)
        assert replay.identity_context.state is record.identity_state
        assert replay.identity_context.substate is record.substate
        assert replay.identity_context.relationship_signals == (
            record.relationship_signals
        )
        assert replay.relationship_requirement is (
            RelationshipRequirement.NOT_REQUIRED
        )

    def test_product_evidence_reconstructed(self) -> None:
        record = _match_record()
        replay = replay_semantic_decision(record)
        assert replay.product_evidence == _strong_profile()
        assert replay.product_evidence_quality is ProductEvidenceQuality.STRONG
        assert replay.product_evidence is record.product_evidence

    def test_context_provenances_reconstructed(self) -> None:
        provenances = frozenset(
            {
                ContextProvenance.MANUFACTURER_RELATION_AUTHORITY,
                ContextProvenance.CUSTOMER_RETRIEVAL_RELATION,
            }
        )
        record = _build(
            decision=V2SemanticDecision.MATCH,
            confidence=V2Confidence.HIGH,
            provenances=provenances,
        )
        replay = replay_semantic_decision(record)
        assert replay.context_provenances == provenances
        # Customer retrieval never dilutes relationship authority.
        assert replay.relationship_authority is RelationshipAuthority.ESTABLISHED
        assert replay.authority_decision.tier is AuthorityTier.AI_ASSISTED_COMPARABLE

    def test_prompt_input_is_the_recorded_historical_input(self) -> None:
        record = _match_record()
        replay = replay_semantic_decision(record)
        prompt = replay.prompt_input
        assert prompt.target_mpn == "ABC-123"
        assert prompt.target_description == "A test product"
        assert prompt.candidate_title == "ABC-123 1TB NVMe Drive"
        assert prompt.candidate_mpn_field is None
        assert prompt.evidence_source == "TITLE_TEXT"
        # The historical binding is carried, not the current constants.
        assert replay.contract_binding == (
            record.semantic_contract_version,
            record.prompt_version,
            record.input_schema_version,
            record.output_schema_version,
            record.authority_contract_version,
        )


# ===========================================================================
# E3. Derived-agreement proof (tamper / version-drift detection)
# ===========================================================================


class TestDerivedAgreementProof:
    def _rebuild_with(self, record, **changes):
        """Recompute the section digests around altered fields (via the
        module's own section encoders) so ONLY the derived-agreement check
        — not the digest self-verification — can fire at replay."""
        from product_intelligence.research import SemanticDecisionRecord
        from product_intelligence.research.semantic_decision_record import (
            _binding_section,
            _contract_section,
            _context_section,
            _derived_section,
            _evaluation_section,
            _execution_section,
            _product_evidence_section,
            canonical_sha256,
        )

        kwargs = record.__dict__.copy()
        kwargs.update(changes)

        input_digest = canonical_sha256(
            {
                "binding": _binding_section(
                    kwargs["run_id"],
                    kwargs["assessment_index"],
                    kwargs["source_url"],
                ),
                "contract": _contract_section(),
                "context": _context_section(
                    kwargs["identity_state"],
                    kwargs["substate"],
                    kwargs["relationship_signals"],
                    kwargs["normalized_requested_part_number"],
                    kwargs["normalized_candidate_part_number"],
                    kwargs["relationship_requirement"],
                    kwargs["context_provenances"],
                ),
                "product_evidence": _product_evidence_section(
                    kwargs["product_evidence"],
                    kwargs["product_evidence_quality"],
                ),
                "prompt_input": record.prompt_input().canonical(),
            }
        )
        output_digest = canonical_sha256(
            {
                "evaluation": _evaluation_section(
                    kwargs["evaluation_state"],
                    kwargs["decision"],
                    kwargs["confidence"],
                    kwargs["conflict_classes"],
                    kwargs["reason_code"],
                    kwargs["matched_attributes"],
                    kwargs["conflicting_attributes"],
                    kwargs["missing_critical_attributes"],
                ),
                "execution": _execution_section(
                    kwargs["attempts"],
                    kwargs["fallback_used"],
                    kwargs["fallback_reason"],
                    kwargs["error_type"],
                    kwargs["actual_provider"],
                    kwargs["actual_model"],
                    kwargs["evaluation_started_at"],
                    kwargs["evaluation_finished_at"],
                ),
                "derived": _derived_section(
                    kwargs["relationship_authority"],
                    kwargs["authority_tier"],
                    kwargs["fired_rules"],
                ),
            }
        )
        kwargs["input_digest"] = input_digest
        kwargs["output_digest"] = output_digest
        return SemanticDecisionRecord(**kwargs)

    def test_tampered_tier_fails_replay(self) -> None:
        record = _match_record()
        corrupted = self._rebuild_with(
            record, authority_tier=AuthorityTier.NEEDS_REVIEW
        )
        with pytest.raises(
            SemanticDecisionReplayError, match="authority_tier"
        ):
            replay_semantic_decision(corrupted)

    def test_tampered_fired_rules_fail_replay(self) -> None:
        record = _match_record()
        corrupted = self._rebuild_with(
            record,
            fired_rules=frozenset({AuthorityRuleV2.STATE_POLICY_DETERMINISTIC}),
        )
        with pytest.raises(
            SemanticDecisionReplayError, match="fired_rules"
        ):
            replay_semantic_decision(corrupted)

    def test_tampered_requirement_fails_replay(self) -> None:
        record = _match_record()
        corrupted = self._rebuild_with(
            record,
            relationship_requirement=(
                RelationshipRequirement.REVIEWED_RELATION_AUTHORITY_REQUIRED
            ),
        )
        with pytest.raises(
            SemanticDecisionReplayError, match="relationship_requirement"
        ):
            replay_semantic_decision(corrupted)

    def test_tampered_quality_fails_replay(self) -> None:
        record = _match_record()
        corrupted = self._rebuild_with(
            record, product_evidence_quality=ProductEvidenceQuality.WEAK
        )
        with pytest.raises(
            SemanticDecisionReplayError, match="product_evidence_quality"
        ):
            replay_semantic_decision(corrupted)

    def test_tampered_relationship_authority_fails_replay(self) -> None:
        record = _match_record()
        corrupted = self._rebuild_with(
            record,
            relationship_authority=RelationshipAuthority.NOT_APPLICABLE,
        )
        with pytest.raises(
            SemanticDecisionReplayError, match="relationship_authority"
        ):
            replay_semantic_decision(corrupted)

    def test_corrupt_inputs_fail_closed(self) -> None:
        # A profile that grounds its facts in reviewed product context while
        # NO reviewed product provenance is present: the record constructor
        # accepts it (the profile is internally consistent, and the derived
        # snapshots are stored values), but the bound contract fails closed
        # on re-derivation — replay must refuse the artifact.
        from product_intelligence.research import (
            SemanticDecisionRecord as _Record,
        )

        profile = ProductEvidenceProfileV2(
            has_usable_product_title=True,
            matched_facts=frozenset(
                {
                    ProductEvidenceFactV2(
                        ProductEvidenceDimension.CAPACITY,
                        frozenset(
                            {CandidateProductEvidenceSource.REVIEWED_PRODUCT_CONTEXT}
                        ),
                    ),
                    ProductEvidenceFactV2(
                        ProductEvidenceDimension.INTERFACE,
                        frozenset(
                            {CandidateProductEvidenceSource.REVIEWED_PRODUCT_CONTEXT}
                        ),
                    ),
                }
            ),
        )
        context = _u1()
        record = _Record.build(
            run_id="11111111-1111-1111-1111-111111111111",
            assessment_index=0,
            source_url="https://example.com/product",
            identity_state=context.state,
            substate=context.substate,
            relationship_signals=context.relationship_signals,
            normalized_requested_part_number=context.normalized_requested_part_number,
            normalized_candidate_part_number=context.normalized_candidate_part_number,
            relationship_requirement=RelationshipRequirement.NOT_REQUIRED,
            product_evidence=profile,
            product_evidence_quality=ProductEvidenceQuality.STRONG,
            context_provenances=frozenset(),  # no reviewed product provenance
            case_id="candidate-00000000-0",
            target_mpn="ABC-123",
            target_description="A test product",
            candidate_title="ABC-123 1TB NVMe Drive",
            candidate_mpn_field=None,
            candidate_sku=None,
            candidate_specs=None,
            evidence_source="TITLE_TEXT",
            evaluation_state=SemanticEvaluationStateV2.EVALUATED,
            decision=V2SemanticDecision.MATCH,
            confidence=V2Confidence.HIGH,
            conflict_classes=frozenset(),
            reason_code="exact_mpn_match",
            matched_attributes=("mpn",),
            conflicting_attributes=(),
            missing_critical_attributes=(),
            attempts=(
                _Record_build_primary_ok(),
            ),
            fallback_used=False,
            fallback_reason=None,
            error_type=None,
            actual_provider="amax",
            actual_model="qwen3.8-27b",
            evaluation_started_at="2026-02-10T12:00:00Z",
            evaluation_finished_at="2026-02-10T12:00:03Z",
            relationship_authority=RelationshipAuthority.NOT_ESTABLISHED,
            authority_tier=AuthorityTier.EXCLUDED_LOW_CONFIDENCE,
            fired_rules=frozenset({AuthorityRuleV2.SEMANTIC_OUTCOME_MATRIX}),
        )
        with pytest.raises(
            SemanticDecisionReplayError, match="bound authority contract"
        ):
            replay_semantic_decision(record)

    def test_replay_is_deterministic(self) -> None:
        record = _runtime_failure_record()
        a = replay_semantic_decision(record)
        b = replay_semantic_decision(record)
        assert a == b
        assert isinstance(a, SemanticDecisionReplay)


# ===========================================================================
# E4. Contract-binding gate (anti-reinterpretation)
# ===========================================================================


class TestContractBindingGate:
    def test_supported_bindings_are_exactly_the_frozen_v1_tuple(self) -> None:
        assert SUPPORTED_CONTRACT_BINDINGS == (
            ("V1", "1.1", 1, 1, "SEMANTIC_AUTHORITY_V2_S2A_FU2"),
        )

    def test_gate_fires_for_unknown_binding(self, monkeypatch) -> None:
        record = _match_record()
        # Simulate code that knows only a DIFFERENT (e.g. future) binding:
        # the record's historical binding must be refused explicitly.
        monkeypatch.setattr(
            "product_intelligence.research.semantic_decision_replay."
            "SUPPORTED_CONTRACT_BINDINGS",
            (
                (
                    "V2_FUTURE",
                    "2.0",
                    1,
                    1,
                    "SEMANTIC_AUTHORITY_V2_S2A_FU2",
                ),
            ),
        )
        with pytest.raises(
            SemanticDecisionReplayError,
            match="refuses to reinterpret",
        ):
            replay_semantic_decision(record)

    def test_gate_fires_for_future_authority_contract(self, monkeypatch) -> None:
        record = _match_record()
        monkeypatch.setattr(
            "product_intelligence.research.semantic_decision_replay."
            "SUPPORTED_CONTRACT_BINDINGS",
            (
                (
                    "V1",
                    "1.1",
                    1,
                    1,
                    "SEMANTIC_AUTHORITY_V3_FUTURE",
                ),
            ),
        )
        with pytest.raises(
            SemanticDecisionReplayError,
            match="unsupported contract binding",
        ):
            replay_semantic_decision(record)

    def test_replay_never_substitutes_current_prompt_for_historical(self) -> None:
        # The replay gate reads the RECORD's binding, not module constants:
        # with the supported table empty, even an artifact bound to the
        # current prompt version must be refused.
        record = _match_record()
        assert record.prompt_version == "1.1"
        with mock.patch(
            "product_intelligence.research.semantic_decision_replay."
            "SUPPORTED_CONTRACT_BINDINGS",
            (),
        ):
            with pytest.raises(SemanticDecisionReplayError):
                replay_semantic_decision(record)

    def test_future_bound_payload_fails_at_decode(self) -> None:
        # A payload bound to a future authority contract is outside schema
        # v1: it cannot even construct a record (let alone replay).
        from product_intelligence.research import (
            SEMANTIC_DECISION_SCHEMA_VERSION,
            decode_semantic_decision_record,
            encode_semantic_decision_record,
        )
        from product_intelligence.research.semantic_decision_codec import (
            SemanticDecisionCodecError,
        )

        record = _match_record()
        payload = encode_semantic_decision_record(record)
        payload["contract"]["authority_contract_version"] = (
            "SEMANTIC_AUTHORITY_V3_FUTURE"
        )
        with pytest.raises(SemanticDecisionCodecError):
            decode_semantic_decision_record(
                payload, schema_version=SEMANTIC_DECISION_SCHEMA_VERSION
            )


# ===========================================================================
# E5. Zero live AI / zero provider network
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

    @pytest.mark.parametrize(
        "make_record",
        [
            lambda: _match_record(),
            lambda: _build(
                decision=V2SemanticDecision.NO_MATCH,
                confidence=V2Confidence.MEDIUM,
                reason_code="capacity_mismatch",
                matched_attributes=(),
                profile=_limited_profile(),
            ),
            lambda: _build(
                decision=V2SemanticDecision.UNCERTAIN,
                confidence=V2Confidence.LOW,
                reason_code="insufficient",
                matched_attributes=(),
                profile=_limited_profile(),
            ),
            _runtime_failure_record,
            _not_evaluated_record,
            _fallback_match_record,
        ],
        ids=[
            "match",
            "no_match",
            "uncertain",
            "runtime_failure",
            "not_evaluated",
            "fallback_match",
        ],
    )
    def test_replay_performs_zero_live_work(self, make_record) -> None:
        record = make_record()
        sentinels = self._arm_sentinels()
        try:
            for sentinel in sentinels:
                sentinel.start()
            replay = replay_semantic_decision(record)
        finally:
            for sentinel in reversed(sentinels):
                sentinel.stop()
        assert isinstance(replay, SemanticDecisionReplay)
        # And the pure reconstructions too.
        sentinels = self._arm_sentinels()
        try:
            for sentinel in sentinels:
                sentinel.start()
            reconstruct_semantic_evaluation(record)
            reconstruct_identity_context(record)
        finally:
            for sentinel in reversed(sentinels):
                sentinel.stop()
