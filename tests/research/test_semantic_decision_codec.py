"""Tests for the strict versioned semantic-decision codec (S2-B).

Covers ``product_intelligence.research.semantic_decision_codec``:

* deterministic canonical encoding (no floats, no lossy serialization);
* exact round-trip decode for ALL outcomes;
* fail-closed strictness: extra fields, missing fields, unknown schema
  version, unknown enums, wrong types, unsorted/duplicated set encodings,
  malformed payloads;
* tamper detection: digests that do not agree with their sections are
  rejected at decode (wrapped in the bounded codec error).
"""

from __future__ import annotations

import dataclasses
import json

import pytest

from product_intelligence.research import (
    AttemptOutcome,
    AttemptRole,
    AuthorityTier,
    ConflictClass,
    ContextProvenance,
    ProductEvidenceProfileV2,
    ProductEvidenceQuality,
    SemanticEvaluationStateV2,
    SemanticFallbackReason,
    SemanticFailureClass,
    V2Confidence,
    V2SemanticDecision,
    SEMANTIC_DECISION_SCHEMA_VERSION,
    canonical_payload_digest,
    decode_semantic_decision_record,
    encode_semantic_decision_record,
    replay_semantic_decision,
)
from product_intelligence.research.semantic_decision_codec import (
    SemanticDecisionCodecError,
)

from tests.research.test_semantic_decision_record import (
    RUN_ID,
    SOURCE_URL,
    STARTED,
    FINISHED,
    _build,
    _fallback_failed,
    _fallback_ok,
    _limited_profile,
    _match_record,
    _primary_failed,
    _primary_ok,
)


def _payload_of(record) -> dict:
    return encode_semantic_decision_record(record)


def _decode(payload: dict, version: int = SEMANTIC_DECISION_SCHEMA_VERSION):
    return decode_semantic_decision_record(payload, schema_version=version)


# ===========================================================================
# Deterministic encoding
# ===========================================================================


class TestDeterministicEncoding:
    def test_encode_twice_is_identical(self) -> None:
        record = _match_record()
        a = _payload_of(record)
        b = _payload_of(record)
        assert a == b
        assert json.dumps(a, sort_keys=True) == json.dumps(b, sort_keys=True)

    def test_encode_is_json_native_only(self) -> None:
        record = _match_record()
        json.dumps(_payload_of(record))  # must serialize without error

    def test_payload_contains_no_floats(self) -> None:
        for record in (
            _match_record(),
            _build(
                decision=V2SemanticDecision.NO_MATCH,
                confidence=V2Confidence.MEDIUM,
                reason_code="capacity_mismatch",
                matched_attributes=(),
            ),
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
                error_type=SemanticFailureClass.BOTH_UNAVAILABLE,
            ),
            _build(
                evaluation_state=SemanticEvaluationStateV2.NOT_EVALUATED,
                decision=None,
                confidence=None,
                reason_code=None,
                matched_attributes=(),
                attempts=(),
                started=None,
                finished=None,
            ),
        ):
            payload = _payload_of(record)

            def walk(value, path):
                if isinstance(value, dict):
                    for key, item in value.items():
                        walk(item, f"{path}.{key}")
                elif isinstance(value, list):
                    for i, item in enumerate(value):
                        walk(item, f"{path}[{i}]")
                elif isinstance(value, float):
                    raise AssertionError(f"float at {path}: {value!r}")

            walk(payload, "payload")

    def test_set_sections_encoded_sorted_unique(self) -> None:
        record = _match_record(
            conflict_classes=frozenset(
                {ConflictClass.BRAND, ConflictClass.CONDITION}
            )
        )
        payload = _payload_of(record)
        conflicts = payload["evaluation"]["conflict_classes"]
        assert conflicts == ["BRAND", "CONDITION"]
        assert payload["context"]["context_provenances"] == []

    def test_canonical_payload_digest_is_stable_and_sensitive(self) -> None:
        payload = _payload_of(_match_record())
        digest = canonical_payload_digest(payload)
        assert digest == canonical_payload_digest(json.loads(json.dumps(payload)))
        tampered = json.loads(json.dumps(payload))
        tampered["derived"]["authority_tier"] = "NEEDS_REVIEW"
        assert canonical_payload_digest(tampered) != digest


# ===========================================================================
# Exact round-trip for all outcomes
# ===========================================================================


class TestRoundTrip:
    @pytest.mark.parametrize(
        "make_record",
        [
            lambda: _match_record(),
            lambda: _build(
                decision=V2SemanticDecision.NO_MATCH,
                confidence=V2Confidence.MEDIUM,
                reason_code="capacity_mismatch",
                matched_attributes=(),
                conflicting_attributes=("capacity",),
            ),
            lambda: _build(
                decision=V2SemanticDecision.UNCERTAIN,
                confidence=V2Confidence.LOW,
                reason_code="insufficient_evidence",
                matched_attributes=(),
                profile=_limited_profile(),
            ),
            lambda: _build(
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
            ),
            lambda: _build(
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
            lambda: _build(
                evaluation_state=SemanticEvaluationStateV2.RUNTIME_FAILURE,
                decision=None,
                confidence=None,
                reason_code=None,
                matched_attributes=(),
                attempts=(_primary_failed(AttemptOutcome.CASE_REJECTED),),
                error_type=SemanticFailureClass.PRIMARY_CASE_REJECTED,
            ),
            lambda: _build(
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
            "fallback_success",
            "runtime_failure_both",
            "runtime_failure_primary_only",
            "not_evaluated",
        ],
    )
    def test_round_trip_is_exact(self, make_record) -> None:
        record = make_record()
        decoded = _decode(_payload_of(record))
        assert decoded == record
        # The decoded artifact replays (contract gate + derived agreement).
        replay = replay_semantic_decision(decoded)
        assert replay.record is decoded


class TestExactDecode:
    def test_provenance_fields_round_trip_exactly(self) -> None:
        record = _match_record()
        decoded = _decode(_payload_of(record))
        assert decoded.prompt_input().case_id == record.prompt_input().case_id
        assert decoded.actual_provider == "amax"
        assert decoded.actual_model == "qwen3.8-27b"
        assert decoded.attempts[0].provider == "amax"
        assert decoded.attempts[0].model == "qwen3.8-27b"
        assert decoded.evaluation_started_at == STARTED
        assert decoded.evaluation_finished_at == FINISHED
        assert decoded.prompt_version == "1.1"
        assert decoded.run_id == RUN_ID
        assert decoded.source_url == SOURCE_URL
        assert decoded.assessment_index == 0

    def test_product_evidence_profile_round_trips_exactly(self) -> None:
        record = _match_record()
        decoded = _decode(_payload_of(record))
        assert decoded.product_evidence == record.product_evidence
        assert isinstance(decoded.product_evidence, ProductEvidenceProfileV2)
        assert decoded.product_evidence_quality is ProductEvidenceQuality.STRONG
        assert decoded.product_evidence.matched_facts == (
            record.product_evidence.matched_facts
        )

    def test_conflict_classes_round_trip_exactly(self) -> None:
        conflicts = frozenset(
            {
                ConflictClass.CAPACITY,
                ConflictClass.BRAND,
                ConflictClass.PACKAGING_QUANTITY,
            }
        )
        record = _build(
            decision=V2SemanticDecision.UNCERTAIN,
            confidence=V2Confidence.MEDIUM,
            reason_code="multiple_differences",
            conflict_classes=conflicts,
            profile=_limited_profile(),
        )
        decoded = _decode(_payload_of(record))
        assert decoded.conflict_classes == conflicts

    def test_context_provenances_round_trip_distinctly(self) -> None:
        provenances = frozenset(
            {
                ContextProvenance.MANUFACTURER_PRODUCT_CONTEXT,
                ContextProvenance.CUSTOMER_RETRIEVAL_RELATION,
            }
        )
        record = _build(
            decision=V2SemanticDecision.MATCH,
            confidence=V2Confidence.HIGH,
            provenances=provenances,
        )
        decoded = _decode(_payload_of(record))
        assert decoded.context_provenances == provenances
        # Distinct classes stay distinct (no collapsing, no aliasing).
        assert ContextProvenance.MANUFACTURER_RELATION_AUTHORITY not in (
            decoded.context_provenances
        )


# ===========================================================================
# Strictness: schema / fields / enums / types
# ===========================================================================


class TestStrictness:
    def test_unknown_schema_version_rejected(self) -> None:
        payload = _payload_of(_match_record())
        with pytest.raises(SemanticDecisionCodecError, match="unsupported schema_version"):
            _decode(payload, version=2)
        with pytest.raises(SemanticDecisionCodecError, match="unsupported schema_version"):
            _decode(payload, version=0)

    def test_schema_version_must_be_int(self) -> None:
        payload = _payload_of(_match_record())
        with pytest.raises(SemanticDecisionCodecError, match="schema_version must be int"):
            _decode(payload, version=True)
        with pytest.raises(SemanticDecisionCodecError, match="schema_version must be int"):
            _decode(payload, version="1")

    def test_payload_must_be_mapping(self) -> None:
        with pytest.raises(SemanticDecisionCodecError, match="payload must be a mapping"):
            _decode(["not", "a", "mapping"])
        with pytest.raises(SemanticDecisionCodecError, match="payload must be a mapping"):
            _decode("nope")

    def test_extra_top_level_field_rejected(self) -> None:
        payload = _payload_of(_match_record())
        payload["junk"] = {"x": 1}
        with pytest.raises(SemanticDecisionCodecError, match="unexpected keys"):
            _decode(payload)

    def test_extra_nested_field_rejected(self) -> None:
        payload = _payload_of(_match_record())
        payload["execution"]["latency_ms"] = 120
        with pytest.raises(SemanticDecisionCodecError, match="unexpected keys"):
            _decode(payload)

    def test_missing_top_level_field_rejected(self) -> None:
        payload = _payload_of(_match_record())
        del payload["integrity"]
        with pytest.raises(SemanticDecisionCodecError, match="missing required keys"):
            _decode(payload)

    def test_missing_nested_field_rejected(self) -> None:
        payload = _payload_of(_match_record())
        del payload["execution"]["attempts"]
        with pytest.raises(SemanticDecisionCodecError, match="missing required key"):
            _decode(payload)

    def test_nullability_is_explicit_not_defaulted(self) -> None:
        # A nullable field with a NULL value decodes; the ABSENT key does not.
        record = _match_record()
        payload = _payload_of(record)
        assert payload["prompt_input"]["candidate_mpn_field"] is None
        decoded = _decode(payload)
        assert decoded.candidate_mpn_field is None
        del payload["prompt_input"]["candidate_mpn_field"]
        with pytest.raises(SemanticDecisionCodecError, match="missing required key"):
            _decode(payload)

    @pytest.mark.parametrize(
        "section, key, bad",
        [
            ("evaluation", "decision", "MAYBE"),
            ("evaluation", "confidence", "VERY_HIGH"),
            ("evaluation", "evaluation_state", "PARTIALLY_EVALUATED"),
            ("context", "identity_state", "DETERMINISTIC_MAYBE"),
            ("context", "substate", "U9_NO_SUCH_SUBSTATE"),
            ("context", "relationship_requirement", "WHATEVER"),
            ("context", "identity_state", "DETERMINISTIC_UNCERTAIN"),  # control: valid
            ("product_evidence", "quality", "GREAT"),
            ("derived", "relationship_authority", "PROBABLY"),
            ("derived", "authority_tier", "SUPER_AUTO"),
            ("derived", "fired_rules", ["NO_SUCH_RULE"]),
            ("execution", "fallback_reason", "BECAUSE_WE_FELT_LIKE_IT"),
            ("execution", "error_type", "MYSTERY_FAILURE"),
            ("execution", "attempts", None),  # handled specially below
        ],
        ids=[
            "decision",
            "confidence",
            "evaluation_state",
            "identity_state",
            "substate",
            "relationship_requirement",
            "identity_state_valid_control",
            "quality",
            "relationship_authority",
            "authority_tier",
            "fired_rules",
            "fallback_reason",
            "error_type",
            "attempt_outcome",
        ],
    )
    def test_unknown_enum_rejected(self, section, key, bad) -> None:
        if bad == "DETERMINISTIC_UNCERTAIN":
            # Control: the valid value decodes fine.
            payload = _payload_of(_match_record())
            assert payload[section][key] == bad
            _decode(payload)
            return
        payload = _payload_of(_match_record())
        if bad is None and key == "attempts":
            # Unknown attempt outcome inside a structurally valid attempt.
            payload["execution"]["attempts"][0]["outcome"] = "NOPE"
        else:
            payload[section][key] = bad
        # Recompute the affected digest so the ONLY remaining violation is
        # the unknown enum value itself (the enum check must be the one
        # that fires, not a stale digest).
        if section in ("binding", "contract", "context", "product_evidence",
                       "prompt_input"):
            payload["integrity"]["input_digest"] = _recompute_input(payload)
        else:
            payload["integrity"]["output_digest"] = _recompute_output(payload)
        with pytest.raises(SemanticDecisionCodecError, match="unknown"):
            _decode(payload)

    def test_wrong_type_rejected_bool_for_int(self) -> None:
        payload = _payload_of(_match_record())
        payload["binding"]["assessment_index"] = True
        payload["integrity"]["input_digest"] = _recompute_input(payload)
        with pytest.raises(SemanticDecisionCodecError, match="expected int"):
            _decode(payload)

    def test_unsorted_set_encoding_rejected(self) -> None:
        payload = _payload_of(
            _match_record(
                conflict_classes=frozenset(
                    {ConflictClass.CAPACITY, ConflictClass.BRAND}
                )
            )
        )
        assert payload["evaluation"]["conflict_classes"] == [
            "BRAND",
            "CAPACITY",
        ]
        payload["evaluation"]["conflict_classes"] = [
            "CAPACITY",
            "BRAND",
        ]
        payload["integrity"]["output_digest"] = _recompute_output(payload)
        with pytest.raises(
            SemanticDecisionCodecError, match="sorted order"
        ):
            _decode(payload)

    def test_duplicate_set_values_rejected(self) -> None:
        payload = _payload_of(_match_record())
        payload["context"]["context_provenances"] = [
            "MANUFACTURER_PRODUCT_CONTEXT",
            "MANUFACTURER_PRODUCT_CONTEXT",
        ]
        payload["integrity"]["input_digest"] = _recompute_input(payload)
        with pytest.raises(SemanticDecisionCodecError, match="unique"):
            _decode(payload)

    def test_float_payload_rejected(self) -> None:
        payload = _payload_of(_match_record())
        payload["execution"]["attempts"][0]["latency_ms"] = 12.5
        with pytest.raises(SemanticDecisionCodecError, match="float"):
            _decode(payload)


def _recompute_input(payload: dict) -> str:
    """Recompute the input digest over a (possibly tampered) payload."""
    from product_intelligence.research import canonical_sha256

    return canonical_sha256(
        {
            "binding": payload["binding"],
            "contract": payload["contract"],
            "context": payload["context"],
            "product_evidence": payload["product_evidence"],
            "prompt_input": payload["prompt_input"],
        }
    )


def _recompute_output(payload: dict) -> str:
    from product_intelligence.research import canonical_sha256

    return canonical_sha256(
        {
            "evaluation": payload["evaluation"],
            "execution": payload["execution"],
            "derived": payload["derived"],
        }
    )


# ===========================================================================
# Tamper detection at decode
# ===========================================================================


class TestDecodeTamper:
    def test_tampered_evaluation_with_stale_output_digest_rejected(
        self,
    ) -> None:
        payload = _payload_of(_match_record())
        payload["evaluation"]["decision"] = "NO_MATCH"
        # output_digest is now stale relative to the evaluation section.
        with pytest.raises(SemanticDecisionCodecError):
            _decode(payload)

    def test_tampered_binding_with_stale_input_digest_rejected(self) -> None:
        payload = _payload_of(_match_record())
        payload["binding"]["source_url"] = "https://attacker.example/x"
        with pytest.raises(SemanticDecisionCodecError):
            _decode(payload)

    def test_tampered_derived_tier_with_stale_output_digest_rejected(
        self,
    ) -> None:
        payload = _payload_of(_match_record())
        payload["derived"]["authority_tier"] = "MACHINE_VERIFIED"
        with pytest.raises(SemanticDecisionCodecError):
            _decode(payload)

    def test_swapped_digests_rejected(self) -> None:
        record = _match_record()
        payload = _payload_of(record)
        payload["integrity"]["input_digest"], payload["integrity"][
            "output_digest"
        ] = payload["integrity"]["output_digest"], payload["integrity"][
            "input_digest"
        ]
        with pytest.raises(SemanticDecisionCodecError):
            _decode(payload)

    def test_encode_rejects_non_record(self) -> None:
        with pytest.raises(TypeError, match="expected SemanticDecisionRecord"):
            encode_semantic_decision_record(object())  # type: ignore[arg-type]
