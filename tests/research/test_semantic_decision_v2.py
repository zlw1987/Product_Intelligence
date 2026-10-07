"""Tests for the Semantic V2 persistence adapter (S2-C, groups F/G).

Covers ``product_intelligence.research.semantic_decision_v2``:

* the V2 typed record (``SemanticDecisionRecordV2``): the exact V2
  contract binding, the V2 pinned route, the strict structured V2
  output coherence, the self-verifying digests, ALL outcomes
  (MATCH / NO_MATCH / UNCERTAIN / RUNTIME_FAILURE / fallback success /
  fallback failure / not evaluated);
* the strict V2 payload codec (exact field sets, strict enums, fail
  closed on unknown/missing/extra, no floats, cross-adapter
  reinterpretation refused);
* the V2 pure zero-live replay (reconstruction + S2-A re-derivation +
  the derived-agreement proof; tamper fail closed; unknown V2 version
  fail closed; V1 replay unchanged);
* the adapter-registry integration (the V2 adapter is the second
  registered adapter; dispatch on the recorded contract identity).

Zero live work: every test below performs zero AI calls, zero provider
calls, and zero network calls (sentinel-armed where the live surface is
importable).
"""

from __future__ import annotations

import copy
import json
import uuid

import pytest

from product_intelligence.domain import ResearchRequest
from product_intelligence.research import (
    ALWAYS_HARD_CONFLICT_CLASSES,
    AttemptOutcome,
    AttemptRole,
    AuthorityTier,
    ContextProvenance,
    ExtractionMethod,
    IdentityStateV2,
    ListingObservation,
    ProductEvidenceProfileV2,
    RelationshipRequirement,
    SemanticDecisionAttempt,
    SemanticEvaluationStateV2,
    SemanticEvaluationV2,
    SemanticFallbackReason,
    SemanticFailureClass,
    V2Confidence,
    V2SemanticDecision,
    assess_listing_identity,
    derive_authority_tier,
    derive_identity_state_v2,
    derive_product_evidence_quality,
    derive_relationship_authority,
    normalize_listing_observation,
)
from product_intelligence.research.semantic_decision_codec import (
    SEMANTIC_DECISION_SCHEMA_VERSION,
    SemanticDecisionCodecError,
    adapter_for_record,
    canonical_payload_digest,
    decode_semantic_decision_record,
    encode_semantic_decision_record,
    registered_semantic_contract_adapter,
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
    SEMANTIC_OUTPUT_SCHEMA_VERSION_V2,
    SEMANTIC_V2_ADAPTER,
    V2_AUTHORITY_QUALIFIED,
    V2_CONTRACT_BINDING,
    SemanticDecisionReplayV2,
    SemanticDecisionRecordV2,
    encode_v2_payload,
    replay_v2_record,
)
from product_intelligence.research.semantic_v2 import (
    SemanticAttributeDimensionV2,
    SemanticAttributeV2,
    SemanticMatchCaseV2,
    SemanticReasonCodeV2,
    build_semantic_match_case_v2,
    build_v2_product_evidence_profile,
)
from product_intelligence.research import ConflictClass

RUN_ID = str(uuid.uuid4())
SOURCE_URL = "https://example.com/test-product"
REQUEST = ResearchRequest("ABC-123", "A test product")

STARTED = "2026-02-10T12:00:00Z"
FINISHED = "2026-02-10T12:00:03.250000Z"


# -- Scenario builders (the real frozen 3C chain) --------------------------


def _observation(mpn=None, sku=None, title="ABC-123 1TB NVMe Drive"):
    return ListingObservation(
        source_url=SOURCE_URL,
        extraction_method=ExtractionMethod.JSON_LD,
        product_title=title,
        brand_text=None,
        manufacturer_part_number_text=mpn,
        sku_text=sku,
        price_text="100",
        currency_text="USD",
        availability_text="In stock",
        condition_text="New",
        seller_text=None,
    )


def _assessment(mpn=None, sku=None, title="ABC-123 1TB NVMe Drive"):
    normalized = normalize_listing_observation(_observation(mpn, sku, title))
    return assess_listing_identity(REQUEST, normalized)


def _case(mpn=None, sku=None, title="ABC-123 1TB NVMe Drive", provenances=None):
    assessment = _assessment(mpn=mpn, sku=sku, title=title)
    context = derive_identity_state_v2(assessment)
    provenances = (
        frozenset() if provenances is None else provenances
    )
    profile = build_v2_product_evidence_profile(
        observation=assessment.normalized_listing.observation,
        context_provenances=provenances,
        matched_facts=frozenset(),
    )
    return build_semantic_match_case_v2(
        case_id="candidate-test-0",
        request=REQUEST,
        assessment=assessment,
        context=context,
        product_evidence=profile,
        context_provenances=provenances,
    )


def _primary_ok():
    return SemanticDecisionAttempt(
        AttemptRole.PRIMARY, 1, PRIMARY_PROVIDER_V2, PRIMARY_MODEL_V2,
        AttemptOutcome.OK,
    )


def _primary_failed(outcome):
    return SemanticDecisionAttempt(
        AttemptRole.PRIMARY, 1, PRIMARY_PROVIDER_V2, PRIMARY_MODEL_V2,
        outcome,
    )


def _fallback_ok():
    return SemanticDecisionAttempt(
        AttemptRole.FALLBACK, 2, FALLBACK_PROVIDER_V2, FALLBACK_MODEL_V2,
        AttemptOutcome.OK,
    )


def _fallback_failed(outcome):
    return SemanticDecisionAttempt(
        AttemptRole.FALLBACK, 2, FALLBACK_PROVIDER_V2, FALLBACK_MODEL_V2,
        outcome,
    )


def _build_record(
    case=None,
    *,
    evaluation_state=SemanticEvaluationStateV2.EVALUATED,
    decision=None,
    confidence=None,
    reason_code=SemanticReasonCodeV2.MATCH_DESCRIPTION_AND_ATTRIBUTES,
    conflict_classes=frozenset(),
    matched_attributes=(),
    conflicting_attributes=(),
    missing_critical_attributes=(),
    attempts=(_primary_ok(),),
    fallback_used=False,
    fallback_reason=None,
    error_type=None,
    actual_provider=PRIMARY_PROVIDER_V2,
    actual_model=PRIMARY_MODEL_V2,
    run_id=RUN_ID,
    assessment_index=0,
    source_url=SOURCE_URL,
    tier_override=None,
    rules_override=None,
):
    case = case if case is not None else _case()
    provenances = case.context_provenances
    profile = case.product_evidence
    if evaluation_state is SemanticEvaluationStateV2.EVALUATED:
        evaluation = SemanticEvaluationV2.evaluated(
            decision, confidence, conflict_classes
        )
    elif evaluation_state is SemanticEvaluationStateV2.RUNTIME_FAILURE:
        evaluation = SemanticEvaluationV2.runtime_failure()
    else:
        evaluation = SemanticEvaluationV2.not_evaluated()
    tier_decision = derive_authority_tier(
        _context_of(case),
        evaluation,
        provenances,
        profile,
    )
    return SemanticDecisionRecordV2.build(
        run_id=run_id,
        assessment_index=assessment_index,
        source_url=source_url,
        case=case,
        evaluation_state=evaluation_state,
        decision=decision,
        confidence=confidence,
        reason_code=reason_code,
        conflict_classes=conflict_classes,
        matched_attributes=matched_attributes,
        conflicting_attributes=conflicting_attributes,
        missing_critical_attributes=missing_critical_attributes,
        attempts=attempts,
        fallback_used=fallback_used,
        fallback_reason=fallback_reason,
        error_type=error_type,
        actual_provider=actual_provider,
        actual_model=actual_model,
        evaluation_started_at=(
            STARTED if evaluation_state is not SemanticEvaluationStateV2.NOT_EVALUATED else None
        ),
        evaluation_finished_at=(
            FINISHED if evaluation_state is not SemanticEvaluationStateV2.NOT_EVALUATED else None
        ),
        product_evidence_quality=tier_decision.product_evidence_quality,
        relationship_authority=tier_decision.relationship_authority,
        authority_tier=(
            tier_override if tier_override is not None else tier_decision.tier
        ),
        fired_rules=(
            rules_override if rules_override is not None else tier_decision.fired_rules
        ),
    )


def _context_of(case):
    # Reconstruct the context the case carries (the case constructor
    # already proved it is a legitimate S2-A context).
    from product_intelligence.research import IdentityStateAssessmentV2

    return IdentityStateAssessmentV2(
        state=case.identity_state,
        substate=case.substate,
        relationship_signals=case.relationship_signals,
        normalized_requested_part_number=case.normalized_requested_part_number,
        normalized_candidate_part_number=case.normalized_candidate_part_number,
    )


# ===========================================================================
# F1. The V2 record: contract identity + route pin + all outcomes
# ===========================================================================


class TestV2RecordContractIdentity:
    def test_the_v2_contract_binding_is_exact(self) -> None:
        record = _build_record(
            decision=V2SemanticDecision.MATCH, confidence=V2Confidence.HIGH
        )
        assert record.semantic_contract_version == SEMANTIC_CONTRACT_VERSION_V2 == "V2"
        assert record.prompt_version == PROMPT_VERSION_V2 == "2.0"
        assert record.input_schema_version == SEMANTIC_INPUT_SCHEMA_VERSION_V2 == 1
        assert record.output_schema_version == SEMANTIC_OUTPUT_SCHEMA_VERSION_V2 == 1
        assert (
            record.authority_contract_version
            == AUTHORITY_CONTRACT_VERSION_V2
            == "SEMANTIC_AUTHORITY_V2_S2A_FU2"
        )
        assert (
            record.semantic_contract_version,
            record.prompt_version,
            record.input_schema_version,
            record.output_schema_version,
            record.authority_contract_version,
        ) == V2_CONTRACT_BINDING

    def test_a_foreign_semantic_contract_is_refused(self) -> None:
        with pytest.raises(ValueError, match="semantic_contract_version"):
            _build_record(
                decision=V2SemanticDecision.MATCH,
                confidence=V2Confidence.HIGH,
            ).__class__(
                **{
                    **_build_record(
                        decision=V2SemanticDecision.MATCH,
                        confidence=V2Confidence.HIGH,
                    ).__dict__,
                    "semantic_contract_version": "V1",
                }
            )

    def test_a_foreign_prompt_version_is_refused(self) -> None:
        with pytest.raises(ValueError, match="prompt_version"):
            SemanticDecisionRecordV2(
                **{
                    **_build_record(
                        decision=V2SemanticDecision.MATCH,
                        confidence=V2Confidence.HIGH,
                    ).__dict__,
                    "prompt_version": "1.1",
                }
            )

    def test_the_v2_route_pin_is_exact(self) -> None:
        assert (PRIMARY_PROVIDER_V2, PRIMARY_MODEL_V2) == ("amax", "qwen3.8-27b")
        assert (FALLBACK_PROVIDER_V2, FALLBACK_MODEL_V2) == (
            "vllm-262k",
            "Qwen3.6-27B-262K",
        )

    def test_a_foreign_primary_route_in_a_v2_record_is_refused(self) -> None:
        with pytest.raises(ValueError, match="pinned primary"):
            _build_record(
                decision=V2SemanticDecision.MATCH,
                confidence=V2Confidence.HIGH,
                attempts=(
                    SemanticDecisionAttempt(
                        AttemptRole.PRIMARY, 1, "other-provider", "other-model",
                        AttemptOutcome.OK,
                    ),
                ),
                actual_provider="other-provider",
                actual_model="other-model",
            )

    def test_a_foreign_fallback_route_in_a_v2_record_is_refused(self) -> None:
        with pytest.raises(ValueError, match="pinned fallback"):
            _build_record(
                decision=V2SemanticDecision.MATCH,
                confidence=V2Confidence.HIGH,
                attempts=(
                    _primary_failed(AttemptOutcome.TIMEOUT),
                    SemanticDecisionAttempt(
                        AttemptRole.FALLBACK, 2, "other-provider", "other-model",
                        AttemptOutcome.OK,
                    ),
                ),
                fallback_used=True,
                fallback_reason=SemanticFallbackReason.TIMEOUT,
                actual_provider="other-provider",
                actual_model="other-model",
            )

    def test_the_qualification_marker_is_false(self) -> None:
        # S2-C: the V2 route is NOT qualified for the new contract.
        assert V2_AUTHORITY_QUALIFIED is False


# ===========================================================================
# F2. The V2 record: ALL outcomes
# ===========================================================================


class TestV2RecordOutcomes:
    def test_match_recorded(self) -> None:
        record = _build_record(
            decision=V2SemanticDecision.MATCH,
            confidence=V2Confidence.HIGH,
            reason_code=SemanticReasonCodeV2.MATCH_DESCRIPTION_AND_ATTRIBUTES,
            matched_attributes=(
                SemanticAttributeV2(
                    SemanticAttributeDimensionV2.PRODUCT_FAMILY, "7500 PRO"
                ),
            ),
        )
        assert record.evaluation_state is SemanticEvaluationStateV2.EVALUATED
        assert record.decision is V2SemanticDecision.MATCH
        assert record.confidence is V2Confidence.HIGH
        assert record.reason_code is (
            SemanticReasonCodeV2.MATCH_DESCRIPTION_AND_ATTRIBUTES
        )

    def test_no_match_recorded(self) -> None:
        record = _build_record(
            decision=V2SemanticDecision.NO_MATCH,
            confidence=V2Confidence.HIGH,
            reason_code=SemanticReasonCodeV2.NO_MATCH_CAPACITY,
            conflict_classes=frozenset({ConflictClass.CAPACITY}),
        )
        assert record.decision is V2SemanticDecision.NO_MATCH
        assert record.conflict_classes == frozenset({ConflictClass.CAPACITY})

    def test_uncertain_recorded(self) -> None:
        record = _build_record(
            decision=V2SemanticDecision.UNCERTAIN,
            confidence=V2Confidence.MEDIUM,
            reason_code=SemanticReasonCodeV2.UNCERTAIN_IDENTIFIER_RELATION,
            matched_attributes=(),
        )
        assert record.decision is V2SemanticDecision.UNCERTAIN

    def test_runtime_failure_recorded(self) -> None:
        record = _build_record(
            evaluation_state=SemanticEvaluationStateV2.RUNTIME_FAILURE,
            decision=None,
            confidence=None,
            reason_code=None,
            conflict_classes=frozenset(),
            matched_attributes=(),
            conflicting_attributes=(),
            missing_critical_attributes=(),
            attempts=(_primary_failed(AttemptOutcome.TIMEOUT),),
            fallback_used=False,
            fallback_reason=None,
            error_type=SemanticFailureClass.PRIMARY_TIMEOUT,
            actual_provider=None,
            actual_model=None,
        )
        assert record.evaluation_state is SemanticEvaluationStateV2.RUNTIME_FAILURE
        assert record.decision is None
        assert record.error_type is SemanticFailureClass.PRIMARY_TIMEOUT
        # A runtime failure is NEVER shaped like a NO_MATCH.
        from product_intelligence.research import AuthorityRuleV2

        assert AuthorityTier.SEMANTIC_UNAVAILABLE == record.authority_tier

    def test_fallback_success_recorded(self) -> None:
        record = _build_record(
            decision=V2SemanticDecision.MATCH,
            confidence=V2Confidence.HIGH,
            attempts=(
                _primary_failed(AttemptOutcome.RATE_LIMITED),
                _fallback_ok(),
            ),
            fallback_used=True,
            fallback_reason=SemanticFallbackReason.RATE_LIMITED,
            actual_provider=FALLBACK_PROVIDER_V2,
            actual_model=FALLBACK_MODEL_V2,
        )
        assert record.fallback_used is True
        assert record.fallback_reason is SemanticFallbackReason.RATE_LIMITED
        assert record.actual_provider == FALLBACK_PROVIDER_V2
        assert record.actual_model == FALLBACK_MODEL_V2
        assert len(record.attempts) == 2

    def test_fallback_failure_recorded(self) -> None:
        record = _build_record(
            evaluation_state=SemanticEvaluationStateV2.RUNTIME_FAILURE,
            decision=None,
            confidence=None,
            reason_code=None,
            conflict_classes=frozenset(),
            matched_attributes=(),
            conflicting_attributes=(),
            missing_critical_attributes=(),
            attempts=(
                _primary_failed(AttemptOutcome.TIMEOUT),
                _fallback_failed(AttemptOutcome.HTTP_ERROR),
            ),
            fallback_used=True,
            fallback_reason=SemanticFallbackReason.TIMEOUT,
            error_type=SemanticFailureClass.FALLBACK_HTTP_ERROR,
            actual_provider=None,
            actual_model=None,
        )
        assert record.error_type is SemanticFailureClass.FALLBACK_HTTP_ERROR

    def test_not_evaluated_recorded(self) -> None:
        record = _build_record(
            evaluation_state=SemanticEvaluationStateV2.NOT_EVALUATED,
            decision=None,
            confidence=None,
            reason_code=None,
            conflict_classes=frozenset(),
            matched_attributes=(),
            conflicting_attributes=(),
            missing_critical_attributes=(),
            attempts=(),
            fallback_used=False,
            fallback_reason=None,
            error_type=None,
            actual_provider=None,
            actual_model=None,
        )
        assert record.evaluation_state is SemanticEvaluationStateV2.NOT_EVALUATED
        assert record.attempts == ()

    def test_incoherent_structured_output_is_refused(self) -> None:
        # NO_MATCH_CAPACITY without the CAPACITY conflict class: the
        # reason code contradicts the structured conflict set — the
        # record fails closed.
        with pytest.raises(ValueError, match="requires structured conflict"):
            _build_record(
                decision=V2SemanticDecision.NO_MATCH,
                confidence=V2Confidence.HIGH,
                reason_code=SemanticReasonCodeV2.NO_MATCH_CAPACITY,
                conflict_classes=frozenset(),
            )

    def test_a_match_with_a_hard_conflict_is_refused(self) -> None:
        with pytest.raises(ValueError, match="ALWAYS_HARD"):
            _build_record(
                decision=V2SemanticDecision.MATCH,
                confidence=V2Confidence.HIGH,
                conflict_classes=frozenset({ConflictClass.CAPACITY}),
            )

    def test_a_runtime_failure_carrying_a_decision_is_refused(self) -> None:
        with pytest.raises(ValueError, match="decision"):
            _build_record(
                evaluation_state=SemanticEvaluationStateV2.RUNTIME_FAILURE,
                decision=V2SemanticDecision.NO_MATCH,
                confidence=V2Confidence.HIGH,
                reason_code=SemanticReasonCodeV2.NO_MATCH_OTHER,
                conflict_classes=frozenset({ConflictClass.BRAND}),
                attempts=(_primary_failed(AttemptOutcome.TIMEOUT),),
                error_type=SemanticFailureClass.PRIMARY_TIMEOUT,
                actual_provider=None,
                actual_model=None,
            )

    def test_a_two_attempt_record_requires_fallback_provenance(self) -> None:
        with pytest.raises(ValueError, match="fallback_used"):
            _build_record(
                decision=V2SemanticDecision.MATCH,
                confidence=V2Confidence.HIGH,
                attempts=(_primary_ok(), _fallback_ok()),
                fallback_used=False,
            )


# ===========================================================================
# F3. The V2 codec: strict encode/decode
# ===========================================================================


class TestV2Codec:
    def _round_trip(self, record):
        payload = encode_v2_payload(record)
        assert payload["schema_version"] == SEMANTIC_DECISION_SCHEMA_VERSION
        assert payload["contract"]["semantic_contract_version"] == "V2"
        assert payload["contract"]["prompt_version"] == "2.0"
        # The V2 payload carries the recorded V2 input under its own
        # section (no V1 "prompt_input" section, no V2 leakage into the
        # universal framing).
        assert "case" in payload
        assert "prompt_input" not in payload
        decoded = decode_semantic_decision_record(
            payload, schema_version=SEMANTIC_DECISION_SCHEMA_VERSION
        )
        assert isinstance(decoded, SemanticDecisionRecordV2)
        assert decoded == record
        return decoded

    def test_match_round_trip(self) -> None:
        record = _build_record(
            decision=V2SemanticDecision.MATCH,
            confidence=V2Confidence.HIGH,
            matched_attributes=(
                SemanticAttributeV2(
                    SemanticAttributeDimensionV2.CAPACITY, "3840GB"
                ),
            ),
        )
        self._round_trip(record)

    def test_no_match_round_trip(self) -> None:
        record = _build_record(
            decision=V2SemanticDecision.NO_MATCH,
            confidence=V2Confidence.MEDIUM,
            reason_code=SemanticReasonCodeV2.NO_MATCH_PACKAGING,
            conflict_classes=frozenset({ConflictClass.PACKAGING_QUANTITY}),
        )
        decoded = self._round_trip(record)
        assert decoded.conflict_classes == frozenset(
            {ConflictClass.PACKAGING_QUANTITY}
        )

    def test_uncertain_round_trip(self) -> None:
        record = _build_record(
            decision=V2SemanticDecision.UNCERTAIN,
            confidence=V2Confidence.LOW,
            reason_code=SemanticReasonCodeV2.UNCERTAIN_MISSING_CRITICAL_ATTRIBUTES,
            matched_attributes=(),
            missing_critical_attributes=(
                SemanticAttributeDimensionV2.REVISION_OR_SUFFIX,
            ),
        )
        decoded = self._round_trip(record)
        assert decoded.missing_critical_attributes == (
            SemanticAttributeDimensionV2.REVISION_OR_SUFFIX,
        )

    def test_runtime_failure_round_trip(self) -> None:
        record = _build_record(
            evaluation_state=SemanticEvaluationStateV2.RUNTIME_FAILURE,
            decision=None,
            confidence=None,
            reason_code=None,
            conflict_classes=frozenset(),
            matched_attributes=(),
            conflicting_attributes=(),
            missing_critical_attributes=(),
            attempts=(
                _primary_failed(AttemptOutcome.TIMEOUT),
                _fallback_failed(AttemptOutcome.TIMEOUT),
            ),
            fallback_used=True,
            fallback_reason=SemanticFallbackReason.TIMEOUT,
            error_type=SemanticFailureClass.BOTH_UNAVAILABLE,
            actual_provider=None,
            actual_model=None,
        )
        self._round_trip(record)

    def test_fallback_success_round_trip(self) -> None:
        record = _build_record(
            decision=V2SemanticDecision.MATCH,
            confidence=V2Confidence.HIGH,
            attempts=(_primary_failed(AttemptOutcome.TIMEOUT), _fallback_ok()),
            fallback_used=True,
            fallback_reason=SemanticFallbackReason.TIMEOUT,
            actual_provider=FALLBACK_PROVIDER_V2,
            actual_model=FALLBACK_MODEL_V2,
        )
        self._round_trip(record)

    def test_not_evaluated_round_trip(self) -> None:
        record = _build_record(
            evaluation_state=SemanticEvaluationStateV2.NOT_EVALUATED,
            decision=None,
            confidence=None,
            reason_code=None,
            conflict_classes=frozenset(),
            matched_attributes=(),
            conflicting_attributes=(),
            missing_critical_attributes=(),
            attempts=(),
            fallback_used=False,
            fallback_reason=None,
            error_type=None,
            actual_provider=None,
            actual_model=None,
        )
        self._round_trip(record)

    def test_the_exact_v2_input_is_stored(self) -> None:
        record = _build_record(
            decision=V2SemanticDecision.MATCH, confidence=V2Confidence.HIGH
        )
        payload = encode_v2_payload(record)
        case = payload["case"]
        assert case["target"]["mpn"] == "ABC-123"
        assert case["target"]["description"] == "A test product"
        assert case["candidate"]["source_url"] == SOURCE_URL
        assert case["deterministic_identity_context"]["identity_state"] == (
            "DETERMINISTIC_UNCERTAIN"
        )
        assert case["context_provenance"] == []
        assert case["product_evidence"]["matched_facts"] == []

    def test_exact_versions_are_stored(self) -> None:
        record = _build_record(
            decision=V2SemanticDecision.MATCH, confidence=V2Confidence.HIGH
        )
        payload = encode_v2_payload(record)
        assert payload["contract"] == {
            "semantic_contract_version": "V2",
            "prompt_version": "2.0",
            "input_schema_version": 1,
            "output_schema_version": 1,
            "authority_contract_version": "SEMANTIC_AUTHORITY_V2_S2A_FU2",
        }

    def test_exact_attempts_are_stored(self) -> None:
        record = _build_record(
            decision=V2SemanticDecision.MATCH,
            confidence=V2Confidence.HIGH,
            attempts=(_primary_failed(AttemptOutcome.TIMEOUT), _fallback_ok()),
            fallback_used=True,
            fallback_reason=SemanticFallbackReason.TIMEOUT,
            actual_provider=FALLBACK_PROVIDER_V2,
            actual_model=FALLBACK_MODEL_V2,
        )
        payload = encode_v2_payload(record)
        assert payload["execution"]["attempts"] == [
            {
                "role": "PRIMARY",
                "attempt_number": 1,
                "provider": "amax",
                "model": "qwen3.8-27b",
                "outcome": "TIMEOUT",
            },
            {
                "role": "FALLBACK",
                "attempt_number": 2,
                "provider": "vllm-262k",
                "model": "Qwen3.6-27B-262K",
                "outcome": "OK",
            },
        ]
        assert payload["execution"]["fallback_used"] is True
        assert payload["execution"]["fallback_reason"] == "TIMEOUT"
        assert payload["execution"]["actual_provider"] == "vllm-262k"
        assert payload["execution"]["actual_model"] == "Qwen3.6-27B-262K"

    def test_extra_top_level_key_rejected(self) -> None:
        record = _build_record(
            decision=V2SemanticDecision.MATCH, confidence=V2Confidence.HIGH
        )
        payload = copy.deepcopy(encode_v2_payload(record))
        payload["chain_of_thought"] = "because"
        with pytest.raises(SemanticDecisionCodecError, match="unexpected keys"):
            decode_semantic_decision_record(
                payload, schema_version=SEMANTIC_DECISION_SCHEMA_VERSION
            )

    def test_missing_top_level_key_rejected(self) -> None:
        record = _build_record(
            decision=V2SemanticDecision.MATCH, confidence=V2Confidence.HIGH
        )
        payload = copy.deepcopy(encode_v2_payload(record))
        del payload["derived"]
        with pytest.raises(SemanticDecisionCodecError, match="missing required keys"):
            decode_semantic_decision_record(
                payload, schema_version=SEMANTIC_DECISION_SCHEMA_VERSION
            )

    def test_v1_shaped_payload_under_the_v2_name_is_refused(self) -> None:
        # Cross-adapter reinterpretation: a V1 payload (prompt_input
        # section, no case section) stored under the V2 contract name is
        # refused by the V2 adapter — never decoded best-effort.
        from product_intelligence.research import (
            SemanticDecisionRecordV1,
        )
        from product_intelligence.research.semantic_decision_v1 import (
            encode_v1_payload,
        )

        v1_case = _case()
        v1_record = _build_v1_record()
        payload = encode_v1_payload(v1_record)
        payload["contract"]["semantic_contract_version"] = "V2"
        with pytest.raises(SemanticDecisionCodecError):
            decode_semantic_decision_record(
                payload, schema_version=SEMANTIC_DECISION_SCHEMA_VERSION
            )

    def test_v2_shaped_payload_under_the_v1_name_is_refused(self) -> None:
        record = _build_record(
            decision=V2SemanticDecision.MATCH, confidence=V2Confidence.HIGH
        )
        payload = copy.deepcopy(encode_v2_payload(record))
        payload["contract"]["semantic_contract_version"] = "V1"
        with pytest.raises(SemanticDecisionCodecError):
            decode_semantic_decision_record(
                payload, schema_version=SEMANTIC_DECISION_SCHEMA_VERSION
            )

    def test_unknown_enum_in_v2_payload_rejected(self) -> None:
        record = _build_record(
            decision=V2SemanticDecision.MATCH, confidence=V2Confidence.HIGH
        )
        payload = copy.deepcopy(encode_v2_payload(record))
        payload["evaluation"]["decision"] = "PERHAPS"
        with pytest.raises(SemanticDecisionCodecError, match="unknown"):
            decode_semantic_decision_record(
                payload, schema_version=SEMANTIC_DECISION_SCHEMA_VERSION
            )

    def test_float_anywhere_rejected(self) -> None:
        record = _build_record(
            decision=V2SemanticDecision.MATCH, confidence=V2Confidence.HIGH
        )
        payload = copy.deepcopy(encode_v2_payload(record))
        payload["case"]["candidate"]["title"] = 1.5
        with pytest.raises(SemanticDecisionCodecError, match="float"):
            decode_semantic_decision_record(
                payload, schema_version=SEMANTIC_DECISION_SCHEMA_VERSION
            )

    def test_tampered_digest_fails_closed(self) -> None:
        record = _build_record(
            decision=V2SemanticDecision.MATCH, confidence=V2Confidence.HIGH
        )
        payload = copy.deepcopy(encode_v2_payload(record))
        payload["evaluation"]["confidence"] = "LOW"
        with pytest.raises(SemanticDecisionCodecError):
            decode_semantic_decision_record(
                payload, schema_version=SEMANTIC_DECISION_SCHEMA_VERSION
            )

    def test_registry_dispatches_the_v2_record_to_the_v2_adapter(self) -> None:
        record = _build_record(
            decision=V2SemanticDecision.MATCH, confidence=V2Confidence.HIGH
        )
        assert adapter_for_record(record) is SEMANTIC_V2_ADAPTER
        assert (
            registered_semantic_contract_adapter(1, "V2") is SEMANTIC_V2_ADAPTER
        )
        # The universal encode entry point dispatches on the registry.
        payload = encode_semantic_decision_record(record)
        assert payload["contract"]["semantic_contract_version"] == "V2"

    def test_an_unregistered_artifact_type_cannot_encode(self) -> None:
        class _Unknown:
            pass

        with pytest.raises(TypeError, match="registered"):
            encode_semantic_decision_record(_Unknown())

    def test_payload_digest_is_canonical(self) -> None:
        record = _build_record(
            decision=V2SemanticDecision.MATCH, confidence=V2Confidence.HIGH
        )
        payload = encode_v2_payload(record)
        assert canonical_payload_digest(payload) == canonical_payload_digest(
            copy.deepcopy(payload)
        )


def _build_v1_record() -> "SemanticDecisionRecordV1":
    """A minimal V1 record (the V1 adapter is unchanged and registered)."""
    from product_intelligence.research import (
        substate_relationship_requirement,
        SemanticDecisionRecordV1 as V1Record,
    )

    case = _case()
    context = _context_of(case)
    evaluation = SemanticEvaluationV2.evaluated(
        V2SemanticDecision.MATCH, V2Confidence.HIGH
    )
    tier = derive_authority_tier(
        context, evaluation, case.context_provenances, case.product_evidence
    )
    return V1Record.build(
        run_id=RUN_ID,
        assessment_index=0,
        source_url=SOURCE_URL,
        identity_state=context.state,
        substate=context.substate,
        relationship_signals=context.relationship_signals,
        normalized_requested_part_number=context.normalized_requested_part_number,
        normalized_candidate_part_number=context.normalized_candidate_part_number,
        relationship_requirement=substate_relationship_requirement(
            context.substate, context.primary_relationship_signal
        ),
        product_evidence=case.product_evidence,
        product_evidence_quality=derive_product_evidence_quality(
            case.product_evidence, case.context_provenances
        ),
        context_provenances=case.context_provenances,
        case_id=case.case_id,
        target_mpn=case.target_mpn,
        target_description=case.target_description,
        candidate_title=case.candidate_title or "",
        candidate_mpn_field=case.candidate_mpn_field,
        candidate_sku=case.candidate_sku,
        candidate_specs=None,
        evidence_source=case.candidate_evidence_source,
        evaluation_state=SemanticEvaluationStateV2.EVALUATED,
        decision=V2SemanticDecision.MATCH,
        confidence=V2Confidence.HIGH,
        conflict_classes=frozenset(),
        reason_code="exact_mpn_match",
        matched_attributes=("mpn",),
        conflicting_attributes=(),
        missing_critical_attributes=(),
        attempts=(_primary_ok(),),
        fallback_used=False,
        fallback_reason=None,
        error_type=None,
        actual_provider=PRIMARY_PROVIDER_V2,
        actual_model=PRIMARY_MODEL_V2,
        evaluation_started_at=STARTED,
        evaluation_finished_at=FINISHED,
        relationship_authority=tier.relationship_authority,
        authority_tier=tier.tier,
        fired_rules=tier.fired_rules,
    )


# ===========================================================================
# G. The V2 zero-live replay
# ===========================================================================


class TestV2Replay:
    def _arm_zero_live_sentinels(self, monkeypatch):
        def boom(*args, **kwargs):
            raise AssertionError("zero-live replay must never call a model")

        from product_intelligence.semantic import runtime, transport

        monkeypatch.setattr(runtime, "get_default_runtime", boom)
        monkeypatch.setattr(runtime, "reset_default_runtime", boom)
        monkeypatch.setattr(
            transport, "get_openai_transport_for_provider", boom
        )
        # The V2 adapter module never imports the production runtime
        # surface (mechanically guarded by the boundaries file).
        import product_intelligence.research.semantic_decision_v2 as v2mod

        for attr in dir(v2mod):
            assert "runtime" not in attr.lower() or attr.startswith("_"), attr

    def test_replay_performs_zero_live_work(self, monkeypatch) -> None:
        self._arm_zero_live_sentinels(monkeypatch)
        record = _build_record(
            decision=V2SemanticDecision.MATCH, confidence=V2Confidence.HIGH
        )
        replay = replay_semantic_decision(record)
        assert isinstance(replay, SemanticDecisionReplayV2)
        assert replay.record == record

    def test_match_replay_exact(self) -> None:
        record = _build_record(
            decision=V2SemanticDecision.MATCH,
            confidence=V2Confidence.HIGH,
            reason_code=SemanticReasonCodeV2.MATCH_DESCRIPTION_AND_ATTRIBUTES,
            matched_attributes=(
                SemanticAttributeV2(
                    SemanticAttributeDimensionV2.CAPACITY, "3840GB"
                ),
            ),
        )
        replay = replay_v2_record(record)
        assert replay.identity_context.state is IdentityStateV2.DETERMINISTIC_UNCERTAIN
        assert (
            replay.semantic_evaluation.decision is V2SemanticDecision.MATCH
        )
        assert replay.semantic_evaluation.confidence is V2Confidence.HIGH
        assert replay.contract_binding == V2_CONTRACT_BINDING
        assert replay.case == record.case
        # The re-derivation agrees with the stored snapshots.
        assert replay.authority_decision.tier is record.authority_tier
        assert (
            replay.authority_decision.fired_rules == record.fired_rules
        )

    def test_no_match_replay_exact(self) -> None:
        record = _build_record(
            decision=V2SemanticDecision.NO_MATCH,
            confidence=V2Confidence.HIGH,
            reason_code=SemanticReasonCodeV2.NO_MATCH_PRODUCT_FAMILY,
            conflict_classes=frozenset({ConflictClass.PRODUCT_FAMILY}),
        )
        replay = replay_v2_record(record)
        assert replay.semantic_evaluation.decision is V2SemanticDecision.NO_MATCH

    def test_uncertain_replay_exact(self) -> None:
        record = _build_record(
            decision=V2SemanticDecision.UNCERTAIN,
            confidence=V2Confidence.MEDIUM,
            reason_code=SemanticReasonCodeV2.UNCERTAIN_IDENTIFIER_RELATION,
            matched_attributes=(),
        )
        replay = replay_v2_record(record)
        assert replay.semantic_evaluation.decision is (
            V2SemanticDecision.UNCERTAIN
        )

    def test_runtime_failure_replay_exact(self) -> None:
        record = _build_record(
            evaluation_state=SemanticEvaluationStateV2.RUNTIME_FAILURE,
            decision=None,
            confidence=None,
            reason_code=None,
            conflict_classes=frozenset(),
            matched_attributes=(),
            conflicting_attributes=(),
            missing_critical_attributes=(),
            attempts=(_primary_failed(AttemptOutcome.TIMEOUT),),
            fallback_used=False,
            fallback_reason=None,
            error_type=SemanticFailureClass.PRIMARY_TIMEOUT,
            actual_provider=None,
            actual_model=None,
        )
        replay = replay_v2_record(record)
        # A runtime failure replays as the explicit unavailable state —
        # NEVER as a NO_MATCH, and the derived tier is
        # SEMANTIC_UNAVAILABLE.
        assert (
            replay.semantic_evaluation.evaluation_state
            is SemanticEvaluationStateV2.RUNTIME_FAILURE
        )
        assert replay.semantic_evaluation.decision is None
        assert replay.authority_decision.tier is AuthorityTier.SEMANTIC_UNAVAILABLE

    def test_fallback_replay_exact(self) -> None:
        record = _build_record(
            decision=V2SemanticDecision.MATCH,
            confidence=V2Confidence.HIGH,
            attempts=(_primary_failed(AttemptOutcome.TIMEOUT), _fallback_ok()),
            fallback_used=True,
            fallback_reason=SemanticFallbackReason.TIMEOUT,
            actual_provider=FALLBACK_PROVIDER_V2,
            actual_model=FALLBACK_MODEL_V2,
        )
        replay = replay_v2_record(record)
        assert replay.record.fallback_used is True
        assert replay.record.fallback_reason is SemanticFallbackReason.TIMEOUT
        assert replay.record.actual_provider == FALLBACK_PROVIDER_V2

    def test_tampered_derived_tier_fails_closed(self) -> None:
        record = _build_record(
            decision=V2SemanticDecision.MATCH,
            confidence=V2Confidence.HIGH,
            tier_override=AuthorityTier.MACHINE_VERIFIED,
        )
        with pytest.raises(SemanticDecisionReplayError, match="do not agree"):
            replay_v2_record(record)

    def test_tampered_fired_rules_fail_closed(self) -> None:
        from product_intelligence.research import AuthorityRuleV2

        record = _build_record(
            decision=V2SemanticDecision.MATCH,
            confidence=V2Confidence.HIGH,
            rules_override=frozenset(
                {AuthorityRuleV2.HARD_CONFLICT_SUPERSEDES}
            ),
        )
        with pytest.raises(SemanticDecisionReplayError, match="do not agree"):
            replay_v2_record(record)

    def test_tampered_relationship_requirement_fails_closed(self) -> None:
        # The case's recorded requirement is contract-derived: a case
        # whose requirement disagrees with the frozen table cannot even
        # be constructed (the input contract fails closed).
        case = _case()  # U1: NOT_REQUIRED
        assert case.relationship_requirement is not (
            RelationshipRequirement.REVIEWED_RELATION_AUTHORITY_REQUIRED
        )
        with pytest.raises(ValueError, match="relationship_requirement"):
            SemanticMatchCaseV2(
                **{
                    **case.__dict__,
                    "relationship_requirement": (
                        RelationshipRequirement
                        .REVIEWED_RELATION_AUTHORITY_REQUIRED
                    ),
                }
            )

    def test_unknown_future_v2_binding_is_refused(self) -> None:
        # A FUTURE V2-lineage binding (prompt 2.1) is outside the
        # adapter's exact supported binding: the replay gate (which
        # reads the RECORD's binding) refuses it explicitly — never
        # silently reinterpreted under the current V2 contract.
        raw = _raw_binding_record(
            ("V2", "2.1", 1, 1, "SEMANTIC_AUTHORITY_V2_S2A_FU2")
        )
        with pytest.raises(
            SemanticDecisionReplayError, match="refuses to reinterpret"
        ):
            replay_semantic_decision(raw)

    def test_a_v1_binding_is_routed_to_the_v1_adapter_not_v2(self) -> None:
        # A record whose recorded binding is the V1 one is dispatched to
        # the V1 adapter by the universal gate — the V2 adapter never
        # interprets it (and the V1 adapter's type check refuses a
        # V2-shaped object bound to V1).
        raw = _raw_binding_record(
            ("V1", "1.1", 1, 1, "SEMANTIC_AUTHORITY_V2_S2A_FU2")
        )
        with pytest.raises(
            TypeError, match="V1 replay adapter expects a SemanticDecisionRecordV1"
        ):
            replay_semantic_decision(raw)
        # The V2 adapter itself refuses anything that is not a V2
        # record.
        with pytest.raises(TypeError, match="SemanticDecisionRecordV2"):
            replay_v2_record(raw)

    def test_the_v1_replay_is_unchanged_through_the_universal_dispatch(self) -> None:
        # The universal dispatch routes a V1-bound record to the V1
        # adapter (historical V1 replay unchanged).
        v1_record = _build_v1_record()
        replay = replay_semantic_decision(v1_record)
        from product_intelligence.research import SemanticDecisionReplay

        assert isinstance(replay, SemanticDecisionReplay)
        assert replay.contract_binding == (
            "V1",
            "1.1",
            1,
            1,
            "SEMANTIC_AUTHORITY_V2_S2A_FU2",
        )

    def test_the_supported_bindings_gate_includes_v2(self) -> None:
        assert V2_CONTRACT_BINDING in SUPPORTED_CONTRACT_BINDINGS
        assert ("V1", "1.1", 1, 1, "SEMANTIC_AUTHORITY_V2_S2A_FU2") in (
            SUPPORTED_CONTRACT_BINDINGS
        )


def _raw_binding_record(binding):
    """A minimal object exposing only the recorded contract-identity
    attributes (the universal gate reads the RECORD's binding, not the
    record's class): enough to prove the gate's behavior."""

    class _RawRecord:
        pass

    raw = _RawRecord()
    (
        raw.semantic_contract_version,
        raw.prompt_version,
        raw.input_schema_version,
        raw.output_schema_version,
        raw.authority_contract_version,
    ) = binding
    return raw
