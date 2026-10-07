"""Tests for the persisted semantic-decision artifact (S2-B).

Covers the pure ``SemanticDecisionRecord`` contract in
``product_intelligence.research.semantic_decision_record``:

* construction of records for ALL semantic outcomes (MATCH / NO_MATCH /
  UNCERTAIN, runtime failure with and without fallback, fallback-used
  success, not-evaluated);
* fail-closed construction (state/evaluation coherence, route pinning,
  attempt shape, timestamps, binding, contract versions, digests);
* canonical digests (self-verification; float refusal).

The mirror-vocabulary drift pins and the import-boundary guards live in
``test_semantic_decision_boundaries.py``; codec strictness in
``test_semantic_decision_codec.py``; replay in
``test_semantic_decision_replay.py``.
"""

from __future__ import annotations

import dataclasses
import uuid

import pytest

from product_intelligence.domain import ResearchRequest
from product_intelligence.research import (
    AttemptOutcome,
    AttemptRole,
    AuthorityRuleV2,
    AuthorityTier,
    CandidateProductEvidenceSource,
    ConflictClass,
    ContextProvenance,
    ExtractionMethod,
    IdentityRelationshipSignal,
    IdentityStateV2,
    ListingObservation,
    ProductEvidenceDimension,
    ProductEvidenceFactV2,
    ProductEvidenceProfileV2,
    ProductEvidenceQuality,
    RelationshipAuthority,
    RelationshipRequirement,
    SEMANTIC_CONTRACT_VERSION,
    SemanticDecisionAttempt,
    SemanticDecisionRecord,
    SemanticEvaluationStateV2,
    SemanticEvaluationV2,
    SemanticFallbackReason,
    SemanticFailureClass,
    UncertainSubstateV2,
    V2Confidence,
    V2SemanticDecision,
    assess_listing_identity,
    canonical_sha256,
    derive_authority_tier,
    derive_identity_state_v2,
    derive_product_evidence_quality,
    derive_relationship_authority,
    normalize_listing_observation,
    record_input_digest,
    record_output_digest,
    substate_relationship_requirement,
)

RUN_ID = str(uuid.UUID("11111111-1111-1111-1111-111111111111"))
SOURCE_URL = "https://example.com/product"
STARTED = "2026-02-10T12:00:00Z"
FINISHED = "2026-02-10T12:00:03.250000Z"

TITLE_SOURCES = frozenset({CandidateProductEvidenceSource.LISTING_PRODUCT_TITLE})


# -- 3C-chain helpers (the REAL frozen deterministic facts) -------------------


def _observation(
    mpn: str | None = None,
    sku: str | None = None,
    title: str | None = "Test Product",
    url: str = SOURCE_URL,
) -> ListingObservation:
    return ListingObservation(
        source_url=url,
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


def _assess(
    mpn: str | None = None,
    sku: str | None = None,
    title: str | None = "Test Product",
    url: str = SOURCE_URL,
    req_mpn: str = "ABC-123",
    description: str = "A test product",
):
    normalized = normalize_listing_observation(
        _observation(mpn=mpn, sku=sku, title=title, url=url)
    )
    request = ResearchRequest(
        manufacturer_part_number=req_mpn, description=description
    )
    return assess_listing_identity(request, normalized)


def _u1():
    """U1_TITLE_MPN: the requested MPN appears in the title only."""
    return derive_identity_state_v2(_assess(title="ABC-123 1TB NVMe Drive"))


def _u2_sku_not_target():
    return derive_identity_state_v2(
        _assess(sku="RETAIL-SKU-1", title="Test Product")
    )


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


# -- record builders (the honest writer: derived values from the contract) ---


def _primary_ok() -> SemanticDecisionAttempt:
    return SemanticDecisionAttempt(
        role=AttemptRole.PRIMARY,
        attempt_number=1,
        provider="amax",
        model="qwen3.8-27b",
        outcome=AttemptOutcome.OK,
    )


def _primary_failed(outcome: AttemptOutcome) -> SemanticDecisionAttempt:
    return SemanticDecisionAttempt(
        role=AttemptRole.PRIMARY,
        attempt_number=1,
        provider="amax",
        model="qwen3.8-27b",
        outcome=outcome,
    )


def _fallback_ok() -> SemanticDecisionAttempt:
    return SemanticDecisionAttempt(
        role=AttemptRole.FALLBACK,
        attempt_number=2,
        provider="vllm-262k",
        model="Qwen3.6-27B-262K",
        outcome=AttemptOutcome.OK,
    )


def _fallback_failed(outcome: AttemptOutcome) -> SemanticDecisionAttempt:
    return SemanticDecisionAttempt(
        role=AttemptRole.FALLBACK,
        attempt_number=2,
        provider="vllm-262k",
        model="Qwen3.6-27B-262K",
        outcome=outcome,
    )


def _build(
    *,
    v2=None,
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
    started=STARTED,
    finished=FINISHED,
) -> SemanticDecisionRecord:
    """Build a record with honestly derived audit snapshots."""
    context = v2 if v2 is not None else _u1()
    profile = profile if profile is not None else _strong_profile()
    provenances = (
        frozenset() if provenances is None else provenances
    )
    if evaluation_state is SemanticEvaluationStateV2.EVALUATED:
        if actual_provider is None and attempts:
            ok = attempts[-1]
            actual_provider = ok.provider
            actual_model = ok.model
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
        run_id=RUN_ID,
        assessment_index=0,
        source_url=SOURCE_URL,
        identity_state=context.state,
        substate=context.substate,
        relationship_signals=context.relationship_signals,
        normalized_requested_part_number=(
            context.normalized_requested_part_number
        ),
        normalized_candidate_part_number=(
            context.normalized_candidate_part_number
        ),
        relationship_requirement=substate_relationship_requirement(
            context.substate, context.primary_relationship_signal
        ),
        product_evidence=profile,
        product_evidence_quality=derive_product_evidence_quality(
            profile, provenances
        ),
        context_provenances=provenances,
        case_id="candidate-00000000-0",
        target_mpn="ABC-123",
        target_description="A test product",
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


def _match_record(**kwargs) -> SemanticDecisionRecord:
    kwargs.setdefault("decision", V2SemanticDecision.MATCH)
    kwargs.setdefault("confidence", V2Confidence.HIGH)
    return _build(**kwargs)


# ===========================================================================
# A. All outcomes construct
# ===========================================================================


class TestAllOutcomesConstruct:
    def test_match_high_strong_reaches_recorded_auto_tier(self) -> None:
        record = _match_record()
        assert record.evaluation_state is (
            SemanticEvaluationStateV2.EVALUATED
        )
        assert record.decision is V2SemanticDecision.MATCH
        assert record.confidence is V2Confidence.HIGH
        # U1 is NOT_REQUIRED (S2-A-FU2): MATCH/HIGH/STRONG records the
        # automatic tier, with the matrix rule fired.
        assert record.authority_tier is AuthorityTier.AI_ASSISTED_COMPARABLE
        assert AuthorityRuleV2.SEMANTIC_OUTCOME_MATRIX in record.fired_rules
        assert record.actual_provider == "amax"
        assert record.actual_model == "qwen3.8-27b"
        assert record.error_type is None
        assert record.fallback_used is False

    def test_no_match_is_recorded(self) -> None:
        record = _build(
            decision=V2SemanticDecision.NO_MATCH,
            confidence=V2Confidence.MEDIUM,
            reason_code="capacity_mismatch",
            matched_attributes=(),
            conflicting_attributes=("capacity",),
        )
        assert record.decision is V2SemanticDecision.NO_MATCH
        assert record.authority_tier is AuthorityTier.EXCLUDED_LOW_CONFIDENCE
        assert record.conflicting_attributes == ("capacity",)

    def test_uncertain_with_reviewable_conflict_is_recorded(self) -> None:
        record = _build(
            decision=V2SemanticDecision.UNCERTAIN,
            confidence=V2Confidence.LOW,
            conflict_classes=frozenset({ConflictClass.BRAND}),
            reason_code="brand_disagreement",
            profile=_limited_profile(),
        )
        assert record.decision is V2SemanticDecision.UNCERTAIN
        assert record.conflict_classes == frozenset({ConflictClass.BRAND})
        assert record.authority_tier is AuthorityTier.EXCLUDED_LOW_CONFIDENCE

    def test_runtime_failure_both_unavailable_is_recorded(self) -> None:
        record = _build(
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
        assert record.evaluation_state is (
            SemanticEvaluationStateV2.RUNTIME_FAILURE
        )
        assert record.decision is None
        assert record.authority_tier is AuthorityTier.SEMANTIC_UNAVAILABLE
        assert AuthorityRuleV2.RUNTIME_FAILURE in record.fired_rules
        assert record.actual_provider is None
        assert record.actual_model is None
        assert record.error_type is SemanticFailureClass.BOTH_UNAVAILABLE
        # A runtime failure is never shaped like a decision.
        assert record.matched_attributes == ()

    def test_runtime_failure_primary_only_is_recorded(self) -> None:
        record = _build(
            evaluation_state=SemanticEvaluationStateV2.RUNTIME_FAILURE,
            decision=None,
            confidence=None,
            reason_code=None,
            matched_attributes=(),
            attempts=(_primary_failed(AttemptOutcome.CASE_REJECTED),),
            fallback_used=False,
            fallback_reason=None,
            error_type=SemanticFailureClass.PRIMARY_CASE_REJECTED,
        )
        assert record.evaluation_state is (
            SemanticEvaluationStateV2.RUNTIME_FAILURE
        )
        assert len(record.attempts) == 1
        assert record.fallback_used is False
        assert record.error_type is SemanticFailureClass.PRIMARY_CASE_REJECTED

    def test_fallback_used_success_is_recorded(self) -> None:
        record = _build(
            decision=V2SemanticDecision.MATCH,
            confidence=V2Confidence.LOW,
            reason_code="title_mpn_match",
            attempts=(
                _primary_failed(AttemptOutcome.MALFORMED_JSON),
                _fallback_ok(),
            ),
            fallback_used=True,
            fallback_reason=SemanticFallbackReason.MALFORMED_JSON,
            profile=_limited_profile(),
        )
        assert record.fallback_used is True
        assert record.fallback_reason is SemanticFallbackReason.MALFORMED_JSON
        # Provenance is attributed to the fallback (the OK attempt).
        assert record.actual_provider == "vllm-262k"
        assert record.actual_model == "Qwen3.6-27B-262K"
        assert record.attempts[0].outcome is AttemptOutcome.MALFORMED_JSON
        assert record.attempts[1].outcome is AttemptOutcome.OK
        assert record.decision is V2SemanticDecision.MATCH

    def test_not_evaluated_is_recorded(self) -> None:
        record = _build(
            evaluation_state=SemanticEvaluationStateV2.NOT_EVALUATED,
            decision=None,
            confidence=None,
            reason_code=None,
            matched_attributes=(),
            attempts=(),
            started=None,
            finished=None,
        )
        assert record.evaluation_state is (
            SemanticEvaluationStateV2.NOT_EVALUATED
        )
        assert record.attempts == ()
        assert record.evaluation_started_at is None
        assert record.evaluation_finished_at is None
        assert record.fallback_used is False
        # NOT_EVALUATED is not an AI failure: the deterministic policy
        # tier is recorded for an uncertain entry point.
        assert record.authority_tier is AuthorityTier.NEEDS_REVIEW
        assert AuthorityRuleV2.STATE_POLICY_DETERMINISTIC in (
            record.fired_rules
        )

    def test_u2_sku_not_target_requirement_is_recorded(self) -> None:
        v2 = _u2_sku_not_target()
        record = _build(
            v2=v2,
            decision=V2SemanticDecision.MATCH,
            confidence=V2Confidence.HIGH,
            # The recorded requirement is REVIEWED_RELATION_AUTHORITY_
            # REQUIRED; without relationship provenance the tier is
            # capped (the S2-A-FU2 state-specific gate).
        )
        assert record.relationship_requirement is (
            RelationshipRequirement.REVIEWED_RELATION_AUTHORITY_REQUIRED
        )
        assert record.relationship_authority is (
            RelationshipAuthority.NOT_ESTABLISHED
        )
        assert record.authority_tier is AuthorityTier.NEEDS_REVIEW
        assert AuthorityRuleV2.CEILING_IDENTIFIER_RELATIONSHIP_NOT_ESTABLISHED in (
            record.fired_rules
        )


# ===========================================================================
# B. Fail-closed construction
# ===========================================================================


class TestFailClosedConstruction:
    def test_run_failure_with_decision_rejected(self) -> None:
        with pytest.raises(ValueError, match="never interpreted as NO_MATCH"):
            _build(
                evaluation_state=SemanticEvaluationStateV2.RUNTIME_FAILURE,
                decision=V2SemanticDecision.NO_MATCH,
                confidence=V2Confidence.HIGH,
                reason_code=None,
                matched_attributes=(),
                attempts=(_primary_failed(AttemptOutcome.TIMEOUT),),
                error_type=SemanticFailureClass.PRIMARY_TIMEOUT,
            )

    def test_evaluated_without_confidence_rejected(self) -> None:
        # Direct construction bypasses the helper's evaluation build: the
        # record's own coherence check must reject it (digests aside, this
        # fires first in the validation order).
        base = _match_record()
        with pytest.raises(ValueError, match="decision and a confidence"):
            dataclasses.replace(base, confidence=None)

    def test_not_evaluated_with_attempts_rejected(self) -> None:
        with pytest.raises(ValueError, match="NOT_EVALUATED"):
            _build(
                evaluation_state=SemanticEvaluationStateV2.NOT_EVALUATED,
                decision=None,
                confidence=None,
                reason_code=None,
                matched_attributes=(),
                attempts=(_primary_ok(),),
                started=None,
                finished=None,
            )

    def test_not_evaluated_with_timestamps_rejected(self) -> None:
        with pytest.raises(ValueError, match="NOT_EVALUATED"):
            _build(
                evaluation_state=SemanticEvaluationStateV2.NOT_EVALUATED,
                decision=None,
                confidence=None,
                reason_code=None,
                matched_attributes=(),
                attempts=(),
            )

    @pytest.mark.parametrize(
        "bad_started, bad_finished",
        [
            (None, FINISHED),
            (STARTED, None),
        ],
    )
    def test_evaluated_requires_both_instants(
        self, bad_started, bad_finished
    ) -> None:
        with pytest.raises(ValueError, match="evaluation instants"):
            _build(
                decision=V2SemanticDecision.MATCH,
                confidence=V2Confidence.HIGH,
                started=bad_started,
                finished=bad_finished,
            )

    @pytest.mark.parametrize(
        "bad",
        [
            "2026-02-10 12:00:00Z",  # not ISO T-separated
            "2026-02-10T12:00:00+00:00",  # offset, not Z
            "2026-02-10T12:00:00",  # naive
            "2026-13-10T12:00:00Z",  # invalid month (grammar passes, calendar fails)
            "not-a-timestamp",
        ],
    )
    def test_timestamp_grammar_rejects(self, bad) -> None:
        with pytest.raises(ValueError):
            _build(
                decision=V2SemanticDecision.MATCH,
                confidence=V2Confidence.HIGH,
                started=bad,
                finished=FINISHED,
            )

    def test_finished_before_started_rejected(self) -> None:
        with pytest.raises(ValueError, match="precede"):
            _build(
                decision=V2SemanticDecision.MATCH,
                confidence=V2Confidence.HIGH,
                started=FINISHED,
                finished=STARTED,
            )

    def test_non_entry_point_context_rejected(self) -> None:
        # V_EXACT (verified) is not a semantic entry point: the ledger
        # records entry-point candidates only.
        from product_intelligence.research import (
            IdentityRelationshipSignal as Signal,
            VerifiedSubstateV2,
        )

        base = _match_record()
        kwargs = base.__dict__.copy()
        kwargs.update(
            identity_state=IdentityStateV2.DETERMINISTIC_VERIFIED,
            substate=VerifiedSubstateV2.V_EXACT,
            relationship_signals=frozenset({Signal.EXACT}),
            relationship_requirement=RelationshipRequirement.NOT_APPLICABLE,
        )
        # The construction itself (inside dataclasses.replace) must fail
        # closed on the non-entry-point context (it fires before the digest
        # self-verification in the validation order).
        with pytest.raises(ValueError, match="entry point"):
            dataclasses.replace(base, **kwargs)

    def test_primary_attempt_wrong_provider_rejected(self) -> None:
        with pytest.raises(ValueError, match="pinned primary"):
            _build(
                decision=V2SemanticDecision.MATCH,
                confidence=V2Confidence.HIGH,
                attempts=(
                    SemanticDecisionAttempt(
                        AttemptRole.PRIMARY,
                        1,
                        "some-other-provider",
                        "qwen3.8-27b",
                        AttemptOutcome.OK,
                    ),
                ),
            )

    def test_fallback_attempt_wrong_model_rejected(self) -> None:
        with pytest.raises(ValueError, match="pinned fallback"):
            _build(
                decision=V2SemanticDecision.MATCH,
                confidence=V2Confidence.LOW,
                attempts=(
                    _primary_failed(AttemptOutcome.TIMEOUT),
                    SemanticDecisionAttempt(
                        AttemptRole.FALLBACK,
                        2,
                        "vllm-262k",
                        "some-other-model",
                        AttemptOutcome.OK,
                    ),
                ),
                fallback_used=True,
                fallback_reason=SemanticFallbackReason.TIMEOUT,
            )

    def test_ok_primary_cannot_have_fallback(self) -> None:
        with pytest.raises(ValueError, match="successful primary is final"):
            _build(
                decision=V2SemanticDecision.MATCH,
                confidence=V2Confidence.HIGH,
                attempts=(_primary_ok(), _fallback_ok()),
                fallback_used=True,
                fallback_reason=SemanticFallbackReason.TIMEOUT,
            )

    def test_three_attempts_rejected(self) -> None:
        with pytest.raises(ValueError, match="one or two"):
            _build(
                decision=V2SemanticDecision.MATCH,
                confidence=V2Confidence.HIGH,
                attempts=(_primary_ok(), _fallback_ok(), _fallback_ok()),
            )

    def test_zero_attempts_for_evaluated_rejected(self) -> None:
        with pytest.raises(ValueError, match="one or two"):
            _build(
                decision=V2SemanticDecision.MATCH,
                confidence=V2Confidence.HIGH,
                attempts=(),
            )

    def test_one_attempt_failure_with_fallback_class_rejected(self) -> None:
        with pytest.raises(ValueError, match="inconsistent"):
            _build(
                evaluation_state=SemanticEvaluationStateV2.RUNTIME_FAILURE,
                decision=None,
                confidence=None,
                reason_code=None,
                matched_attributes=(),
                attempts=(_primary_failed(AttemptOutcome.TIMEOUT),),
                error_type=SemanticFailureClass.FALLBACK_TIMEOUT,
            )

    def test_two_attempt_failure_with_primary_class_rejected(self) -> None:
        with pytest.raises(ValueError, match="inconsistent"):
            _build(
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
                error_type=SemanticFailureClass.PRIMARY_TIMEOUT,
            )

    def test_two_attempts_without_fallback_used_rejected(self) -> None:
        with pytest.raises(ValueError, match="fallback_used must be True"):
            _build(
                decision=V2SemanticDecision.MATCH,
                confidence=V2Confidence.LOW,
                attempts=(
                    _primary_failed(AttemptOutcome.TIMEOUT),
                    _fallback_ok(),
                ),
            )

    def test_fallback_reason_none_rejected_for_two_attempts(self) -> None:
        with pytest.raises(ValueError, match="must not be NONE"):
            _build(
                decision=V2SemanticDecision.MATCH,
                confidence=V2Confidence.LOW,
                attempts=(
                    _primary_failed(AttemptOutcome.TIMEOUT),
                    _fallback_ok(),
                ),
                fallback_used=True,
                fallback_reason=SemanticFallbackReason.NONE,
            )

    def test_run_id_must_be_canonical_uuid(self) -> None:
        base = _match_record()
        with pytest.raises(ValueError, match="canonical UUID"):
            dataclasses.replace(base, run_id="not-a-uuid")
        # Uppercase hex letters are not the canonical form.
        with pytest.raises(ValueError, match="canonical UUID form"):
            dataclasses.replace(
                base, run_id="ABCDEFAB-1234-5678-9ABC-DEF012345678"
            )

    def test_assessment_index_must_be_non_negative_int(self) -> None:
        base = _match_record()
        with pytest.raises(ValueError, match=">= 0"):
            dataclasses.replace(base, assessment_index=-1)
        with pytest.raises(TypeError, match="assessment_index"):
            dataclasses.replace(base, assessment_index=True)

    def test_contract_binding_rejects_other_prompt_version(self) -> None:
        from product_intelligence.research.semantic_decision_record import (
            AUTHORITY_CONTRACT_VERSION,
            PROMPT_VERSION_V1,
            SEMANTIC_CONTRACT_VERSION,
            SEMANTIC_INPUT_SCHEMA_VERSION,
            SEMANTIC_OUTPUT_SCHEMA_VERSION,
        )

        base = _match_record()
        kwargs = base.__dict__.copy()
        kwargs["prompt_version"] = "1.0"
        with pytest.raises(ValueError, match="prompt_version"):
            SemanticDecisionRecord(**kwargs)

    def test_contract_binding_rejects_future_authority_contract(self) -> None:
        base = _match_record()
        kwargs = base.__dict__.copy()
        kwargs["authority_contract_version"] = "SEMANTIC_AUTHORITY_V3_FUTURE"
        with pytest.raises(
            ValueError, match="authority_contract_version"
        ):
            SemanticDecisionRecord(**kwargs)


# ===========================================================================
# C. Digest self-verification
# ===========================================================================


class TestDigestSelfVerification:
    def test_input_digest_covers_input_sections(self) -> None:
        record = _match_record()
        assert record.input_digest == record_input_digest(record)
        assert record.output_digest == record_output_digest(record)

    def test_tampered_input_section_breaks_digest(self) -> None:
        record = _match_record()
        with pytest.raises(ValueError, match="input_digest"):
            dataclasses.replace(record, candidate_title="A different title")

    def test_tampered_output_section_breaks_digest(self) -> None:
        record = _match_record()
        with pytest.raises(ValueError, match="output_digest"):
            dataclasses.replace(
                record,
                authority_tier=AuthorityTier.NEEDS_REVIEW,
            )

    def test_tampered_derived_snapshot_breaks_digest(self) -> None:
        record = _match_record()
        with pytest.raises(ValueError, match="output_digest"):
            dataclasses.replace(
                record,
                fired_rules=frozenset(
                    {AuthorityRuleV2.STATE_POLICY_DETERMINISTIC}
                ),
            )

    def test_tampered_binding_section_breaks_digest(self) -> None:
        record = _match_record()
        with pytest.raises(ValueError, match="input_digest"):
            dataclasses.replace(
                record, source_url="https://evil.example.com/other"
            )

    def test_canonical_sha256_is_deterministic(self) -> None:
        value = {"b": 2, "a": [1, 2, 3], "c": None}
        assert canonical_sha256(value) == canonical_sha256(value)
        # Key order is canonicalized: equal dicts in different order hash
        # identically; different content hashes differently.
        assert canonical_sha256({"a": 1, "b": 2}) == canonical_sha256(
            {"b": 2, "a": 1}
        )
        assert canonical_sha256({"a": 1}) != canonical_sha256({"a": 2})

    def test_canonical_sha256_refuses_floats(self) -> None:
        from product_intelligence.research import CanonicalDigestError

        with pytest.raises(CanonicalDigestError, match="float"):
            canonical_sha256({"latency_ms": 12.5})

    def test_contract_section_matches_module_constants(self) -> None:
        record = _match_record()
        assert record.semantic_contract_version == SEMANTIC_CONTRACT_VERSION
        assert record.prompt_version == "1.1"
        assert record.input_schema_version == 1
        assert record.output_schema_version == 1
        assert (
            record.authority_contract_version
            == "SEMANTIC_AUTHORITY_V2_S2A_FU2"
        )
