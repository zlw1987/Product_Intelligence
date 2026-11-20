"""Tests for the SEMANTIC-V2-PERF-PHASE0-UAT-FU1 correction (finding
F-1 — the PERF record encode/decode canonical-ordering asymmetry).

The real Phase 0 UAT persisted a PERF-bound record (output schema 2)
whose ``missing_critical_attributes`` carried the model-output order
``[PACKAGING_QUANTITY, BUNDLE]``: the shared frozen evaluation-section
encoder writes that list in the order given, while the shared set-value
decoder requires the sorted canonical order. The record persisted with
valid digests (computed over the same original order) but refused to
decode and replay through the application's registered-adapter path.

This suite pins the authorized correction:

* **Future PERF records.** ``SemanticDecisionRecordV2Perf.build()``
  normalizes ``missing_critical_attributes`` to the deterministic
  sorted tuple of exact enum string values at the builder boundary,
  BEFORE the section digests are computed: duplicate and invalid
  dimensions are refused (never silently deduplicated), all dimensions
  are preserved, and the stored field, the computed digests, and the
  decoded typed record of every record built from here on agree. The
  ACTUAL production record-building path
  (``execution.semantic_decision_v2_execution.
  build_semantic_decision_records_v2`` + the S2-B persistence service)
  is driven end to end with an unsorted model-output response.
* **The legacy UAT record.** The PERF decoder (its exact five-axis
  binding only) accepts the pre-normalization output-schema-2 records
  whose only noncanonical feature is the ordering of
  ``missing_critical_attributes``: the values must still be unique,
  valid ``SemanticAttributeDimensionV2`` members; the original
  serialized order is preserved verbatim; the record's normal
  construction validation, the ORIGINAL digest verification (a digest
  mismatch is refused, never repaired by recomputation or replacement
  of the stored digest), and the zero-live replay / derived-agreement
  proof all still apply. The persisted representation is never
  rewritten: decode + re-encode is byte-identical.
* **Everything else stays frozen.** Duplicates, unknown values, wrong
  types, absent keys, unrelated malformed fields, and tampered
  digests remain rejected; the frozen V2 (output schema 1) adapter
  keeps its exact strict contract (an unsorted V2 payload is STILL
  refused by it — the relaxation is PERF-only); all other evaluation
  fields keep their ordering semantics.

Zero live work: every test performs zero AI calls, zero provider
calls, and zero network calls (the DB-backed service tests use the
session test database and bounded in-memory records only).
"""

from __future__ import annotations

import json

import pytest

from product_intelligence.domain import ResearchRequest
from product_intelligence.research import (
    AttemptOutcome,
    AttemptRole,
    SemanticAttributeDimensionV2,
    SemanticDecisionAttempt,
    SemanticEvaluationStateV2,
    SemanticEvaluationV2,
    V2Confidence,
    V2SemanticDecision,
    assess_listing_identity,
    canonical_payload_digest,
    canonical_sha256,
    decode_semantic_decision_record,
    derive_authority_tier,
    encode_semantic_decision_record,
    normalize_listing_observation,
)
from product_intelligence.research import (
    SEMANTIC_V2_ADAPTER,
    SEMANTIC_V2_PERF_ADAPTER,
    V2_CONTRACT_BINDING,
    SemanticDecisionRecordV2,
)
from product_intelligence.research.semantic_decision_codec import (
    SemanticDecisionCodecError,
    adapter_for_record,
)
from product_intelligence.research.semantic_decision_record import (
    _binding_section,
)
from product_intelligence.research.semantic_decision_v2 import (
    PRIMARY_MODEL_V2,
    PRIMARY_PROVIDER_V2,
    _v2_derived_section,
    _v2_evaluation_section,
)
from product_intelligence.research.semantic_decision_v2_perf import (
    AUTHORITY_CONTRACT_VERSION_V2_PERF,
    FALLBACK_MODEL_V2_PERF,
    FALLBACK_PROVIDER_V2_PERF,
    PROMPT_VERSION_V2_PERF,
    PRIMARY_MODEL_V2_PERF,
    PRIMARY_PROVIDER_V2_PERF,
    SEMANTIC_CONTRACT_VERSION_V2_PERF,
    SEMANTIC_INPUT_SCHEMA_VERSION_V2_PERF,
    SEMANTIC_OUTPUT_SCHEMA_VERSION_V2_PERF,
    V2_PERF_CONTRACT_BINDING,
    SemanticDecisionAttemptPerf,
    SemanticDecisionReplayV2Perf,
    SemanticDecisionRecordV2Perf,
    _v2_perf_contract_section,
    _v2_perf_execution_section,
    replay_v2_perf_record,
    record_input_digest_v2_perf,
    record_output_digest_v2_perf,
)
from product_intelligence.research.semantic_v2 import (
    SemanticMatchResponseV2,
    SemanticReasonCodeV2,
)
from tests.research.test_semantic_decision_v2_perf import (
    FINISHED,
    REQUEST,
    RUN_ID,
    STARTED,
    _case,
    _perf_attempt,
    _raw_bytes,
)
# NOTE: the Phase 0 suite's TestPerfServiceRoundTrip class is imported
# LAZILY (inside the two methods that reuse its run/snapshot helper) —
# a module-level import of a test class would make pytest re-collect
# those nodes under this file's path (duplicated node ids).

D = SemanticAttributeDimensionV2

# The exact ordering the real UAT persisted (model-output order — NOT
# the sorted canonical order): the legacy compatibility must accept
# precisely this shape.
UAT_ORDER = (D.PACKAGING_QUANTITY, D.BUNDLE)
# The canonical sorted form of the same two dimensions.
SORTED_ORDER = (D.BUNDLE, D.PACKAGING_QUANTITY)
# The complete dimension vocabulary in REVERSE canonical order (all
# eleven members — "preserve all dimensions").
ALL_REVERSED = tuple(reversed(sorted(D, key=lambda d: d.value)))
ALL_SORTED = tuple(sorted(D, key=lambda d: d.value))


def _uncertain_evaluation():
    """The UAT shape: UNCERTAIN / MEDIUM with the missing-attributes
    reason code (the frozen rule requires a non-empty missing set)."""
    return (
        SemanticEvaluationStateV2.EVALUATED,
        V2SemanticDecision.UNCERTAIN,
        V2Confidence.MEDIUM,
        SemanticReasonCodeV2.UNCERTAIN_MISSING_CRITICAL_ATTRIBUTES,
    )


def _perf_attempts():
    """One primary attempt with the UAT record's exact telemetry."""
    return (
        _perf_attempt(
            latency_ms=41936,
            prompt_tokens=2789,
            completion_tokens=4170,
            finish_reason="stop",
        ),
    )


def _build_uncertain_perf_record(missing):
    """A PERF record of the UAT semantic shape via the ACTUAL builder
    (post-correction: ``missing`` is normalized at the boundary)."""
    case, context, profile = _case()
    state, decision, confidence, reason = _uncertain_evaluation()
    tier = derive_authority_tier(
        context,
        SemanticEvaluationV2.evaluated(decision, confidence, frozenset()),
        case.context_provenances,
        profile,
    )
    return SemanticDecisionRecordV2Perf.build(
        run_id=RUN_ID,
        assessment_index=1,
        source_url=case.candidate_source_url,
        case=case,
        evaluation_state=state,
        decision=decision,
        confidence=confidence,
        reason_code=reason,
        conflict_classes=frozenset(),
        matched_attributes=(),
        conflicting_attributes=(),
        missing_critical_attributes=missing,
        attempts=_perf_attempts(),
        fallback_used=False,
        fallback_reason=None,
        error_type=None,
        actual_provider=PRIMARY_PROVIDER_V2_PERF,
        actual_model=PRIMARY_MODEL_V2_PERF,
        evaluation_started_at=STARTED,
        evaluation_finished_at=FINISHED,
        product_evidence_quality=tier.product_evidence_quality,
        relationship_authority=tier.relationship_authority,
        authority_tier=tier.tier,
        fired_rules=tier.fired_rules,
    )


def _legacy_uncertain_perf_record(
    missing=UAT_ORDER, run_id=RUN_ID, assessment_index=1
):
    """Reconstruct EXACTLY what the pre-correction production build
    persisted for the UAT record: the section digests were computed
    over the given (original) ordering, and the record was constructed
    with that same ordering (the constructor never normalized — only
    ``build()`` does, now).

    For the UAT ordering this is byte-for-byte the shape of the
    persisted row: stored field, payload, and digests all carry the
    original model-output order.
    """
    case, context, profile = _case()
    state, decision, confidence, reason = _uncertain_evaluation()
    tier = derive_authority_tier(
        context,
        SemanticEvaluationV2.evaluated(decision, confidence, frozenset()),
        case.context_provenances,
        profile,
    )
    attempts = _perf_attempts()
    input_digest = canonical_sha256(
        {
            "binding": _binding_section(
                run_id, assessment_index, case.candidate_source_url
            ),
            "contract": _v2_perf_contract_section(),
            "case": case.canonical(),
        }
    )
    output_digest = canonical_sha256(
        {
            "evaluation": _v2_evaluation_section(
                state,
                decision,
                confidence,
                frozenset(),
                reason,
                (),
                (),
                missing,
            ),
            "execution": _v2_perf_execution_section(
                attempts,
                False,
                None,
                None,
                PRIMARY_PROVIDER_V2_PERF,
                PRIMARY_MODEL_V2_PERF,
                STARTED,
                FINISHED,
            ),
            "derived": _v2_derived_section(
                tier.product_evidence_quality,
                tier.relationship_authority,
                tier.tier,
                tier.fired_rules,
            ),
        }
    )
    return SemanticDecisionRecordV2Perf(
        run_id=run_id,
        assessment_index=assessment_index,
        source_url=case.candidate_source_url,
        semantic_contract_version=SEMANTIC_CONTRACT_VERSION_V2_PERF,
        prompt_version=PROMPT_VERSION_V2_PERF,
        input_schema_version=SEMANTIC_INPUT_SCHEMA_VERSION_V2_PERF,
        output_schema_version=SEMANTIC_OUTPUT_SCHEMA_VERSION_V2_PERF,
        authority_contract_version=AUTHORITY_CONTRACT_VERSION_V2_PERF,
        case=case,
        evaluation_state=state,
        decision=decision,
        confidence=confidence,
        reason_code=reason,
        conflict_classes=frozenset(),
        matched_attributes=(),
        conflicting_attributes=(),
        missing_critical_attributes=missing,
        attempts=attempts,
        fallback_used=False,
        fallback_reason=None,
        error_type=None,
        actual_provider=PRIMARY_PROVIDER_V2_PERF,
        actual_model=PRIMARY_MODEL_V2_PERF,
        evaluation_started_at=STARTED,
        evaluation_finished_at=FINISHED,
        product_evidence_quality=tier.product_evidence_quality,
        relationship_authority=tier.relationship_authority,
        authority_tier=tier.tier,
        fired_rules=tier.fired_rules,
        input_digest=input_digest,
        output_digest=output_digest,
    )


def _legacy_payload(record):
    """The persisted payload of a legacy record, in its ORIGINAL
    serialized order (the exact bytes shape the UAT row carries)."""
    return encode_semantic_decision_record(record)


# ===========================================================================
# 1. Future PERF records: builder-boundary canonical ordering
# ===========================================================================


class TestF1NewRecordCanonicalization:
    def test_reverse_order_missing_dimensions_are_saved_sorted(self):
        record = _build_uncertain_perf_record(missing=UAT_ORDER)
        # The stored field is the deterministic sorted tuple of the
        # exact enum string values — NOT the model-output order.
        assert record.missing_critical_attributes == SORTED_ORDER
        # The recorded evaluation section (the digest input) agrees.
        assert record.evaluation_section()["missing_critical_attributes"] == (
            ["BUNDLE", "PACKAGING_QUANTITY"]
        )
        # The self-verifying digests agree with the section encodings.
        assert record_input_digest_v2_perf(record) == record.input_digest
        assert record_output_digest_v2_perf(record) == record.output_digest
        # The persisted payload carries the sorted canonical order.
        payload = encode_semantic_decision_record(record)
        assert payload["evaluation"]["missing_critical_attributes"] == (
            ["BUNDLE", "PACKAGING_QUANTITY"]
        )
        assert payload["contract"]["output_schema_version"] == 2

    def test_reverse_order_record_decodes_and_replays(self):
        record = _build_uncertain_perf_record(missing=UAT_ORDER)
        payload = json.loads(json.dumps(encode_semantic_decision_record(record)))
        decoded = decode_semantic_decision_record(payload, schema_version=1)
        assert type(decoded) is SemanticDecisionRecordV2Perf
        assert decoded == record
        assert adapter_for_record(decoded) is SEMANTIC_V2_PERF_ADAPTER
        replay = replay_v2_perf_record(decoded)
        assert isinstance(replay, SemanticDecisionReplayV2Perf)
        assert replay.contract_binding == V2_PERF_CONTRACT_BINDING
        assert replay.authority_decision.tier is record.authority_tier
        assert replay.authority_decision.fired_rules == record.fired_rules

    def test_all_dimensions_in_reverse_order_are_preserved_sorted(self):
        # Every one of the twelve bounded dimensions, in reverse
        # canonical order: all are preserved, none is dropped or
        # deduplicated, and the stored order is the sorted form.
        record = _build_uncertain_perf_record(missing=ALL_REVERSED)
        assert len(record.missing_critical_attributes) == 12
        assert record.missing_critical_attributes == ALL_SORTED
        payload = json.loads(
            json.dumps(encode_semantic_decision_record(record))
        )
        decoded = decode_semantic_decision_record(payload, schema_version=1)
        assert decoded == record
        assert decoded.missing_critical_attributes == ALL_SORTED
        replay = replay_v2_perf_record(decoded)
        assert replay.contract_binding == V2_PERF_CONTRACT_BINDING

    def test_duplicate_missing_dimensions_refused_at_build(self):
        with pytest.raises(ValueError, match="duplicate"):
            _build_uncertain_perf_record(missing=(D.BUNDLE, D.BUNDLE))

    def test_invalid_missing_dimension_refused_at_build(self):
        # A non-member entry is refused (invalid), and a non-sequence
        # is refused (wrong type) — never coerced, never dropped.
        with pytest.raises(TypeError, match="SemanticAttributeDimensionV2"):
            _build_uncertain_perf_record(missing=("BUNDLE",))
        with pytest.raises(TypeError, match="tuple"):
            _build_uncertain_perf_record(missing=D.BUNDLE)

    def test_already_sorted_build_is_the_canonical_noop(self):
        # A record built from an already-canonical list keeps exactly
        # the pre-correction digests (normalization is a no-op for it):
        # previously persisted canonical records stay valid, and the
        # digests are the ones computed over the sorted section.
        record = _build_uncertain_perf_record(missing=SORTED_ORDER)
        assert record.missing_critical_attributes == SORTED_ORDER
        assert record_output_digest_v2_perf(record) == record.output_digest
        payload = json.loads(
            json.dumps(encode_semantic_decision_record(record))
        )
        decoded = decode_semantic_decision_record(payload, schema_version=1)
        assert decoded == record

    def test_fallback_two_attempt_record_with_missing_dimensions_round_trips(
        self,
    ):
        # The existing two-attempt fallback shape stays valid WITH a
        # (now canonicalized) multi-element missing set.
        case, context, profile = _case()
        state, decision, confidence, reason = _uncertain_evaluation()
        tier = derive_authority_tier(
            context,
            SemanticEvaluationV2.evaluated(decision, confidence, frozenset()),
            case.context_provenances,
            profile,
        )
        from product_intelligence.research import (
            SemanticFallbackReason,
        )

        record = SemanticDecisionRecordV2Perf.build(
            run_id=RUN_ID,
            assessment_index=1,
            source_url=case.candidate_source_url,
            case=case,
            evaluation_state=state,
            decision=decision,
            confidence=confidence,
            reason_code=reason,
            conflict_classes=frozenset(),
            matched_attributes=(),
            conflicting_attributes=(),
            missing_critical_attributes=UAT_ORDER,
            attempts=(
                _perf_attempt(
                    number=1,
                    outcome=AttemptOutcome.RATE_LIMITED,
                    latency_ms=120,
                    prompt_tokens=None,
                    completion_tokens=None,
                    finish_reason=None,
                ),
                _perf_attempt(
                    number=2,
                    outcome=AttemptOutcome.OK,
                    latency_ms=45000,
                    prompt_tokens=900,
                    completion_tokens=1500,
                    finish_reason="length",
                ),
            ),
            fallback_used=True,
            fallback_reason=SemanticFallbackReason.RATE_LIMITED,
            error_type=None,
            actual_provider=FALLBACK_PROVIDER_V2_PERF,
            actual_model=FALLBACK_MODEL_V2_PERF,
            evaluation_started_at=STARTED,
            evaluation_finished_at=FINISHED,
            product_evidence_quality=tier.product_evidence_quality,
            relationship_authority=tier.relationship_authority,
            authority_tier=tier.tier,
            fired_rules=tier.fired_rules,
        )
        assert record.missing_critical_attributes == SORTED_ORDER
        payload = json.loads(
            json.dumps(encode_semantic_decision_record(record))
        )
        decoded = decode_semantic_decision_record(payload, schema_version=1)
        assert decoded == record
        assert decoded.attempts[0].latency_ms == 120
        assert decoded.attempts[1].finish_reason == "length"
        replay = replay_v2_perf_record(decoded)
        assert replay.contract_binding == V2_PERF_CONTRACT_BINDING


# ===========================================================================
# 2. The legacy UAT record: original ordering restored to readability
# ===========================================================================


class TestF1LegacyUatRecord:
    def test_legacy_uat_ordering_decodes_and_replays(self):
        record = _legacy_uncertain_perf_record(missing=UAT_ORDER)
        # Sanity: this IS the pre-correction shape — the stored field
        # and the digests carry the original (unsorted) order.
        assert record.missing_critical_attributes == UAT_ORDER
        assert record.missing_critical_attributes != SORTED_ORDER
        payload = json.loads(json.dumps(_legacy_payload(record)))
        assert payload["evaluation"]["missing_critical_attributes"] == (
            ["PACKAGING_QUANTITY", "BUNDLE"]
        )
        decoded = decode_semantic_decision_record(payload, schema_version=1)
        assert type(decoded) is SemanticDecisionRecordV2Perf
        assert decoded == record
        assert adapter_for_record(decoded) is SEMANTIC_V2_PERF_ADAPTER
        replay = replay_v2_perf_record(decoded)
        assert isinstance(replay, SemanticDecisionReplayV2Perf)
        assert replay.contract_binding == V2_PERF_CONTRACT_BINDING
        assert replay.authority_decision.tier is record.authority_tier
        assert replay.authority_decision.fired_rules == record.fired_rules
        assert replay.case == record.case

    def test_legacy_persisted_representation_is_unchanged(self):
        record = _legacy_uncertain_perf_record(missing=UAT_ORDER)
        original = _raw_bytes(record)
        payload = json.loads(original.decode("utf-8"))
        decoded = decode_semantic_decision_record(payload, schema_version=1)
        # Decode never rewrites the artifact: re-encoding the decoded
        # record reproduces the EXACT persisted bytes (the original
        # serialized order included).
        assert _raw_bytes(decoded) == original
        assert decoded.missing_critical_attributes == UAT_ORDER

    def test_legacy_decoded_record_retains_the_recorded_information(self):
        record = _legacy_uncertain_perf_record(missing=UAT_ORDER)
        decoded = decode_semantic_decision_record(
            json.loads(json.dumps(_legacy_payload(record))), schema_version=1
        )
        # Original recorded dimensions (the UAT ordering, verbatim).
        assert decoded.missing_critical_attributes == UAT_ORDER
        # Execution instrumentation, unchanged.
        assert decoded.attempts[0].latency_ms == 41936
        assert decoded.attempts[0].prompt_tokens == 2789
        assert decoded.attempts[0].completion_tokens == 4170
        assert decoded.attempts[0].finish_reason == "stop"
        assert decoded.fallback_used is False
        # The exact five-axis PERF binding, unchanged.
        assert (
            decoded.semantic_contract_version,
            decoded.prompt_version,
            decoded.input_schema_version,
            decoded.output_schema_version,
            decoded.authority_contract_version,
        ) == V2_PERF_CONTRACT_BINDING
        assert decoded.output_schema_version == 2
        # Derived authority information, unchanged (evidence-only).
        assert decoded.authority_tier is record.authority_tier
        assert decoded.fired_rules == record.fired_rules
        assert decoded.product_evidence_quality is (
            record.product_evidence_quality
        )
        assert decoded.relationship_authority is (
            record.relationship_authority
        )
        # The stored digests are the ORIGINAL ones (never recomputed).
        assert decoded.input_digest == record.input_digest
        assert decoded.output_digest == record.output_digest

    def test_legacy_record_replay_proves_zero_live_derived_agreement(self):
        record = _legacy_uncertain_perf_record(missing=UAT_ORDER)
        decoded = decode_semantic_decision_record(
            json.loads(json.dumps(_legacy_payload(record))), schema_version=1
        )
        replay = replay_v2_perf_record(decoded)
        # The re-derivation agrees with the stored derived snapshots —
        # the instrumentation is provenance, never a derivation input.
        assert replay.authority_decision.tier is decoded.authority_tier
        assert replay.authority_decision.fired_rules == decoded.fired_rules
        assert replay.relationship_authority is decoded.relationship_authority
        assert replay.record is decoded


class TestF1LegacyServiceRoundTrip:
    """The exact application path the UAT failed on: persist ->
    ``load_semantic_decision`` -> ``replay_semantic_decision_record``
    over the SAME universal row (envelope schema 1, no migration)."""

    def test_legacy_record_persists_loads_and_replays_through_the_service(
        self,
    ):
        from product_intelligence.execution.semantic_decision_persistence import (
            load_semantic_decision,
            persist_semantic_decision,
            replay_semantic_decision_record,
        )
        from product_intelligence.runs.models import (
            PriceIntelligenceSnapshot,
            ResearchRun,
            SemanticDecisionRecord,
        )

        from tests.research.test_semantic_decision_v2_perf import (
            TestPerfServiceRoundTrip,
        )

        run = TestPerfServiceRoundTrip()._run_and_snapshot()
        record = _legacy_uncertain_perf_record(
            missing=UAT_ORDER,
            run_id=str(run.id),
            assessment_index=0,
        )
        row = persist_semantic_decision(run, record)
        assert row.schema_version == 1
        assert row.payload_digest == canonical_payload_digest(row.payload)
        # The persisted row carries the ORIGINAL model-output order.
        assert row.payload["evaluation"]["missing_critical_attributes"] == (
            ["PACKAGING_QUANTITY", "BUNDLE"]
        )
        original_bytes = _raw_bytes(record)
        loaded = load_semantic_decision(run.id, 0)
        assert type(loaded) is SemanticDecisionRecordV2Perf
        assert loaded == record
        # The load never rewrote the row's representation.
        assert _raw_bytes(loaded) == original_bytes
        replay = replay_semantic_decision_record(run.id, 0)
        assert isinstance(replay, SemanticDecisionReplayV2Perf)
        assert replay.contract_binding == V2_PERF_CONTRACT_BINDING
        assert replay.authority_decision.tier is record.authority_tier

        row.refresh_from_db()
        assert (
            json.dumps(row.payload, sort_keys=True)
            == json.dumps(record and _legacy_payload(record), sort_keys=True)
        )
        assert row.payload_digest == canonical_payload_digest(row.payload)

        # Cleanup (the session test DB — the same discipline the
        # Phase 0 service tests use).
        SemanticDecisionRecord.objects.all().delete()
        PriceIntelligenceSnapshot.objects.all().delete()
        ResearchRun.objects.all().delete()


# ===========================================================================
# 3. Legacy compatibility is narrowly scoped: everything else still
#    fails closed
# ===========================================================================


class TestF1LegacyRefusals:
    def test_duplicate_dimensions_refused_at_decode(self):
        record = _legacy_uncertain_perf_record(missing=UAT_ORDER)
        payload = json.loads(json.dumps(_legacy_payload(record)))
        payload["evaluation"]["missing_critical_attributes"] = [
            "BUNDLE",
            "BUNDLE",
        ]
        with pytest.raises(SemanticDecisionCodecError, match="unique"):
            decode_semantic_decision_record(payload, schema_version=1)

    def test_unknown_dimension_value_refused_at_decode(self):
        record = _legacy_uncertain_perf_record(missing=UAT_ORDER)
        payload = json.loads(json.dumps(_legacy_payload(record)))
        payload["evaluation"]["missing_critical_attributes"] = [
            "PACKAGING_QUANTITY",
            "NOT_A_DIMENSION",
        ]
        with pytest.raises(
            SemanticDecisionCodecError, match="unknown"
        ):
            decode_semantic_decision_record(payload, schema_version=1)

    def test_wrong_type_refused_at_decode(self):
        record = _legacy_uncertain_perf_record(missing=UAT_ORDER)
        payload = json.loads(json.dumps(_legacy_payload(record)))
        payload["evaluation"]["missing_critical_attributes"] = [
            7,
            "BUNDLE",
        ]
        with pytest.raises(SemanticDecisionCodecError, match="string"):
            decode_semantic_decision_record(payload, schema_version=1)

    def test_absent_key_refused_at_decode(self):
        record = _legacy_uncertain_perf_record(missing=UAT_ORDER)
        payload = json.loads(json.dumps(_legacy_payload(record)))
        del payload["evaluation"]["missing_critical_attributes"]
        with pytest.raises(
            SemanticDecisionCodecError, match="missing required key"
        ):
            decode_semantic_decision_record(payload, schema_version=1)

    def test_reordered_legacy_payload_with_original_digests_refused(self):
        # The legacy compatibility accepts ONLY the exact serialized
        # order the stored digests were computed over: the same values
        # re-sorted while the ORIGINAL (unsorted-order) digests are
        # kept is a digest mismatch — refused, never "repaired" by
        # recomputation.
        record = _legacy_uncertain_perf_record(missing=UAT_ORDER)
        payload = json.loads(json.dumps(_legacy_payload(record)))
        payload["evaluation"]["missing_critical_attributes"] = [
            "BUNDLE",
            "PACKAGING_QUANTITY",
        ]
        with pytest.raises(SemanticDecisionCodecError):
            decode_semantic_decision_record(payload, schema_version=1)

    def test_canonical_payload_reordered_with_canonical_digests_refused(self):
        # The mirror direction: a post-correction (sorted) record whose
        # payload list is re-shuffled while its sorted-order digests
        # are kept is refused exactly the same way.
        record = _build_uncertain_perf_record(missing=SORTED_ORDER)
        payload = json.loads(json.dumps(encode_semantic_decision_record(record)))
        payload["evaluation"]["missing_critical_attributes"] = [
            "PACKAGING_QUANTITY",
            "BUNDLE",
        ]
        with pytest.raises(SemanticDecisionCodecError):
            decode_semantic_decision_record(payload, schema_version=1)

    def test_unrelated_malformed_fields_still_refused(self):
        record = _legacy_uncertain_perf_record(missing=UAT_ORDER)
        base = json.loads(json.dumps(_legacy_payload(record)))

        # (a) an unexpected top-level key.
        forged = json.loads(json.dumps(base))
        forged["unexpected_section"] = {}
        with pytest.raises(SemanticDecisionCodecError):
            decode_semantic_decision_record(forged, schema_version=1)

        # (b) the other set-valued fields keep the STRICT sorted
        #     canonical requirement (the relaxation is this field's
        #     ordering alone).
        unsorted_rules = json.loads(json.dumps(base))
        rules = unsorted_rules["derived"]["fired_rules"]
        if len(rules) >= 2:
            unsorted_rules["derived"]["fired_rules"] = list(reversed(rules))
            with pytest.raises(SemanticDecisionCodecError, match="sorted"):
                decode_semantic_decision_record(
                    unsorted_rules, schema_version=1
                )

        # (c) the instrumentation stays digest-anchored: a tampered
        #     latency with the stored digests is refused.
        tampered = json.loads(json.dumps(base))
        tampered["execution"]["attempts"][0]["latency_ms"] += 1
        with pytest.raises(SemanticDecisionCodecError):
            decode_semantic_decision_record(tampered, schema_version=1)

    def test_stale_digest_after_dimension_change_refused(self):
        # Swap ONE recorded dimension (a different fact, not a
        # reordering) while keeping the stored digests: refused.
        record = _legacy_uncertain_perf_record(missing=UAT_ORDER)
        payload = json.loads(json.dumps(_legacy_payload(record)))
        payload["evaluation"]["missing_critical_attributes"] = [
            "BUNDLE",
            "CAPACITY",
        ]
        with pytest.raises(SemanticDecisionCodecError):
            decode_semantic_decision_record(payload, schema_version=1)


# ===========================================================================
# 4. The frozen contracts stay frozen: the V2 (output schema 1)
#    adapter is untouched and keeps its strict sorted requirement
# ===========================================================================


def _v2_uncertain_record(missing):
    case, context, profile = _case()
    state, decision, confidence, reason = _uncertain_evaluation()
    tier = derive_authority_tier(
        context,
        SemanticEvaluationV2.evaluated(decision, confidence, frozenset()),
        case.context_provenances,
        profile,
    )
    return SemanticDecisionRecordV2.build(
        run_id=RUN_ID,
        assessment_index=1,
        source_url=case.candidate_source_url,
        case=case,
        evaluation_state=state,
        decision=decision,
        confidence=confidence,
        reason_code=reason,
        conflict_classes=frozenset(),
        matched_attributes=(),
        conflicting_attributes=(),
        missing_critical_attributes=missing,
        attempts=(
            SemanticDecisionAttempt(
                AttemptRole.PRIMARY, 1,
                PRIMARY_PROVIDER_V2, PRIMARY_MODEL_V2, AttemptOutcome.OK,
            ),
        ),
        fallback_used=False,
        fallback_reason=None,
        error_type=None,
        actual_provider=PRIMARY_PROVIDER_V2,
        actual_model=PRIMARY_MODEL_V2,
        evaluation_started_at=STARTED,
        evaluation_finished_at=FINISHED,
        product_evidence_quality=tier.product_evidence_quality,
        relationship_authority=tier.relationship_authority,
        authority_tier=tier.tier,
        fired_rules=tier.fired_rules,
    )


class TestF1FrozenContractsUnchanged:
    def test_v2_schema1_record_still_dispatches_to_frozen_v2_adapter(self):
        record = _v2_uncertain_record(missing=SORTED_ORDER)
        assert record.output_schema_version == 1
        payload = json.loads(json.dumps(encode_semantic_decision_record(record)))
        decoded = decode_semantic_decision_record(payload, schema_version=1)
        assert type(decoded) is SemanticDecisionRecordV2
        assert adapter_for_record(decoded) is SEMANTIC_V2_ADAPTER
        assert decoded == record
        from product_intelligence.research.semantic_decision_replay import (
            replay_semantic_decision,
        )

        replay = replay_semantic_decision(decoded)
        assert replay.contract_binding == V2_CONTRACT_BINDING

    def test_v2_adapter_still_requires_sorted_missing_list(self):
        # The frozen V2 (output schema 1) surface is NOT relaxed by the
        # FU1 correction: a V2 payload carrying an unsorted multi-element
        # missing list is still refused by the shared strict set
        # encoding (the PERF-only legacy exception does not apply to
        # it — the PERF adapter does not claim the schema-1 binding).
        record = _v2_uncertain_record(missing=UAT_ORDER)
        payload = json.loads(json.dumps(encode_semantic_decision_record(record)))
        assert payload["evaluation"]["missing_critical_attributes"] == (
            ["PACKAGING_QUANTITY", "BUNDLE"]
        )
        with pytest.raises(
            SemanticDecisionCodecError, match="sorted order"
        ):
            decode_semantic_decision_record(payload, schema_version=1)
        # ...while the same values in the canonical sorted order still
        # decode under the frozen V2 adapter (the historical contract).
        canonical = _v2_uncertain_record(missing=SORTED_ORDER)
        canonical_payload = json.loads(
            json.dumps(encode_semantic_decision_record(canonical))
        )
        decoded = decode_semantic_decision_record(
            canonical_payload, schema_version=1
        )
        assert type(decoded) is SemanticDecisionRecordV2
        assert decoded.missing_critical_attributes == SORTED_ORDER


# ===========================================================================
# 5. The production record-building path (not a test-only helper)
# ===========================================================================


class TestF1ProductionBuildPath:
    def test_production_build_normalizes_an_unsorted_model_response(
        self,
    ):
        from product_intelligence.execution.semantic_decision_persistence import (
            load_semantic_decision,
            persist_semantic_decision,
            replay_semantic_decision_record,
        )
        from product_intelligence.execution.semantic_decision_v2_execution import (
            SemanticDecisionV2Outcome,
            build_semantic_decision_records_v2,
        )
        from product_intelligence.runs.models import (
            PriceIntelligenceSnapshot,
            ResearchRun,
            SemanticDecisionRecord,
        )
        from product_intelligence.semantic.runtime import (
            SemanticAttempt,
            SemanticAttemptStatus,
        )
        from product_intelligence.semantic.runtime_v2 import (
            SemanticRuntimeResultV2,
        )

        from tests.research.test_semantic_decision_v2_perf import (
            TestPerfServiceRoundTrip,
        )

        # The real frozen 3C chain: the same request / observation the
        # Phase 0 suite uses. The run carries the single-assessment
        # price snapshot the replay run-binding check verifies against.
        run = TestPerfServiceRoundTrip()._run_and_snapshot()
        assessment = assess_listing_identity(
            REQUEST, normalize_listing_observation(_case_observation())
        )
        case = _case_for(assessment)

        # The model response in MODEL-OUTPUT order — the exact shape
        # that produced the UAT record (UNCERTAIN / MEDIUM /
        # UNCERTAIN_MISSING_CRITICAL_ATTRIBUTES, [PACKAGING_QUANTITY,
        # BUNDLE]).
        response = SemanticMatchResponseV2(
            decision=V2SemanticDecision.UNCERTAIN,
            confidence=V2Confidence.MEDIUM,
            reason_code=(
                SemanticReasonCodeV2.UNCERTAIN_MISSING_CRITICAL_ATTRIBUTES
            ),
            matched_attributes=(),
            conflicting_attributes=(),
            missing_critical_attributes=UAT_ORDER,
            conflict_classes=frozenset(),
        )
        result = SemanticRuntimeResultV2(
            case=case,
            requested_primary_provider=PRIMARY_PROVIDER_V2,
            requested_primary_model=PRIMARY_MODEL_V2,
            attempts=(
                SemanticAttempt(
                    provider=PRIMARY_PROVIDER_V2,
                    model=PRIMARY_MODEL_V2,
                    status=SemanticAttemptStatus.OK,
                    latency_ms=41936.347,
                    token_usage={
                        "prompt_tokens": 2789,
                        "completion_tokens": 4170,
                    },
                    finish_reason="stop",
                ),
            ),
            fallback_used=False,
            fallback_reason=None,
            actual_provider=PRIMARY_PROVIDER_V2,
            actual_model=PRIMARY_MODEL_V2,
            response=response,
            error_type=None,
            evaluation_started_at=STARTED,
            evaluation_finished_at=FINISHED,
        )
        outcome = SemanticDecisionV2Outcome(
            assessment=assessment,
            context=_context_for(case),
            product_evidence=case.product_evidence,
            context_provenances=case.context_provenances,
            case=case,
            result=result,
        )

        # THE production record-building path (the orchestration's
        # publication entry): unsorted model output in, canonical
        # persisted record out.
        records = build_semantic_decision_records_v2(
            run, (assessment,), (outcome,)
        )
        assert len(records) == 1
        record = records[0]
        assert record.missing_critical_attributes == SORTED_ORDER
        payload = encode_semantic_decision_record(record)
        assert payload["evaluation"]["missing_critical_attributes"] == (
            ["BUNDLE", "PACKAGING_QUANTITY"]
        )
        assert payload["contract"]["output_schema_version"] == 2
        # The instrumentation is the bounded integer-millisecond /
        # provider-reported form (41936.347 -> 41936).
        assert record.attempts[0].latency_ms == 41936
        assert record.attempts[0].prompt_tokens == 2789
        assert record.attempts[0].completion_tokens == 4170
        assert record.attempts[0].finish_reason == "stop"

        # And the record that was persisted before the correction
        # (the legacy shape) still loads and replays through the same
        # service in the same row shape.
        row = persist_semantic_decision(run, record)
        assert row.payload_digest == canonical_payload_digest(row.payload)
        loaded = load_semantic_decision(run.id, 0)
        assert loaded == record
        replay = replay_semantic_decision_record(run.id, 0)
        assert isinstance(replay, SemanticDecisionReplayV2Perf)
        assert replay.contract_binding == V2_PERF_CONTRACT_BINDING

        # Cleanup (the session test DB).
        SemanticDecisionRecord.objects.all().delete()
        PriceIntelligenceSnapshot.objects.all().delete()
        ResearchRun.objects.all().delete()


def _case_observation():
    from product_intelligence.research import ExtractionMethod, ListingObservation

    return ListingObservation(
        source_url="https://example.com/test-product",
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


def _context_for(case):
    from product_intelligence.research import IdentityStateAssessmentV2

    return IdentityStateAssessmentV2(
        state=case.identity_state,
        substate=case.substate,
        relationship_signals=case.relationship_signals,
        normalized_requested_part_number=case.normalized_requested_part_number,
        normalized_candidate_part_number=case.normalized_candidate_part_number,
    )


def _case_for(assessment):
    from product_intelligence.research import (
        build_semantic_match_case_v2,
        build_v2_product_evidence_profile,
        derive_identity_state_v2,
    )

    context = derive_identity_state_v2(assessment)
    profile = build_v2_product_evidence_profile(
        observation=assessment.normalized_listing.observation,
        context_provenances=frozenset(),
        matched_facts=frozenset(),
    )
    return build_semantic_match_case_v2(
        case_id="candidate-fu1-0",
        request=REQUEST,
        assessment=assessment,
        context=context,
        product_evidence=profile,
        context_provenances=frozenset(),
        reviewed_target_context=None,
    )
