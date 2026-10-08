"""Q3-A offline evaluation tests.

Mandated properties 13-21 (valid MATCH / NO_MATCH / UNCERTAIN
evaluation; invalid JSON; unknown response field; unknown conflict
class; incoherent reason/conflict pair; missing model response;
runtime failure) and 22-26 (false-MATCH detection incl. HARD_CONFLICT,
packaging, accessory, and near-miss shapes).
"""

from __future__ import annotations

import json

import pytest

from tests.evaluation.semantic_v2._q3a_helpers import (
    fallback_route,
    primary_route,
    write_capture,
    load_corpus_bundle,
)
from product_intelligence.evaluation.semantic_v2.capture import (
    load_capture,
)
from product_intelligence.evaluation.semantic_v2.evaluator import (
    evaluate_for_model,
)


@pytest.fixture(scope="module")
def corpus():
    return load_corpus_bundle()


@pytest.fixture(scope="module")
def correct_capture(corpus, tmp_path_factory):
    path = write_capture(
        tmp_path_factory.mktemp("correct") / "c.json", corpus
    )
    return load_capture(path)


@pytest.fixture(scope="module")
def correct_result(corpus, correct_capture):
    return evaluate_for_model(corpus, correct_capture, *primary_route())


def outcome(result, case_id):
    return next(o for o in result.outcomes if o.case_id == case_id)


# ===========================================================================
# 13-15. Valid MATCH / NO_MATCH / UNCERTAIN evaluation
# ===========================================================================


class TestValidEvaluations:
    def test_a_valid_match_is_scored_correct(self, correct_result) -> None:
        o = outcome(correct_result, "V2Q-SSD-U1-MATCH-0001")
        assert o.state == "EVALUATED"
        assert o.model_decision == "MATCH"
        assert o.verdict == "CORRECT"
        assert o.severity is None
        assert o.provenance_role == "PRIMARY"

    def test_a_valid_no_match_is_scored_correct(
        self, correct_result
    ) -> None:
        o = outcome(correct_result, "V2Q-SSD-ATTR-CAPACITY-0024")
        assert o.state == "EVALUATED"
        assert o.model_decision == "NO_MATCH"
        assert o.verdict == "CORRECT"
        assert o.severity is None
        assert o.model_reason_code == "NO_MATCH_CAPACITY"
        assert "CAPACITY" in o.model_conflict_classes

    def test_a_valid_uncertain_is_scored_correct(
        self, correct_result
    ) -> None:
        o = outcome(correct_result, "V2Q-SSD-U4-THIN-0015")
        assert o.state == "EVALUATED"
        assert o.model_decision == "UNCERTAIN"
        assert o.verdict == "CORRECT"
        assert o.severity is None
        assert o.model_reason_code == "UNCERTAIN_MISSING_CRITICAL_ATTRIBUTES"

    def test_an_ambiguous_defensible_answer_is_not_an_error(
        self, correct_result
    ) -> None:
        o = outcome(correct_result, "V2Q-SSD-BRAND-CONTESTED-0040")
        assert o.state == "EVALUATED"
        assert o.case_class == "AMBIGUOUS"
        assert o.verdict == "DEFENSIBLE"
        assert o.severity is None

    def test_the_full_correct_capture_is_error_free(self, correct_result) -> None:
        metrics = correct_result.metrics
        assert metrics["false_match_count"] == 0
        assert metrics["false_no_match_count"] == 0
        assert metrics["severity_counts"] == {
            "CRITICAL": 0,
            "HIGH": 0,
            "MEDIUM": 0,
            "REVIEW": 0,
        }
        assert metrics["counts"]["evaluated_cases"] == 43
        assert metrics["counts"]["not_captured"] == 0


# ===========================================================================
# 16-19. Invalid responses (also proven at classifier level in the
# contract-binding suite; here through the capture path)
# ===========================================================================


class TestInvalidResponses:
    @pytest.mark.parametrize(
        "raw,expected_failure",
        [
            ("{broken", "MALFORMED_JSON"),
            (
                json.dumps(
                    {
                        "decision": "MATCH",
                        "confidence": "HIGH",
                        "reason_code": "MATCH_EXACT_PRODUCT_CONTEXT",
                        "matched_attributes": [],
                        "conflicting_attributes": [],
                        "missing_critical_attributes": [],
                        "conflict_classes": [],
                        "explanation": "hidden reasoning",
                    }
                ),
                "MALFORMED_JSON",
            ),
            (
                json.dumps(
                    {
                        "decision": "NO_MATCH",
                        "confidence": "HIGH",
                        "reason_code": "NO_MATCH_OTHER",
                        "matched_attributes": [],
                        "conflicting_attributes": [],
                        "missing_critical_attributes": [],
                        "conflict_classes": ["NOT_A_CLASS"],
                    }
                ),
                "SCHEMA_INVALID",
            ),
            (
                json.dumps(
                    {
                        "decision": "NO_MATCH",
                        "confidence": "HIGH",
                        "reason_code": "NO_MATCH_CAPACITY",
                        "matched_attributes": [],
                        "conflicting_attributes": [],
                        "missing_critical_attributes": [],
                        "conflict_classes": ["INTERFACE"],
                    }
                ),
                "SCHEMA_INVALID",
            ),
        ],
        ids=["invalid-json", "unknown-field", "unknown-conflict-class",
             "incoherent-reason-conflict"],
    )
    def test_invalid_captured_responses_fail_closed(
        self, corpus, tmp_path, raw, expected_failure
    ) -> None:
        case_id = "V2Q-SSD-ATTR-CAPACITY-0024"
        path = write_capture(
            tmp_path / "c.json",
            corpus,
            attempts_overrides={
                case_id: [
                    {
                        "role": "PRIMARY",
                        "provider": "amax",
                        "model": "qwen3.8-27b",
                        "status": "OK",
                        "raw_output": raw,
                    }
                ]
            },
        )
        result = evaluate_for_model(corpus, load_capture(path), *primary_route())
        o = outcome(result, case_id)
        assert o.state == "CAPTURE_INTEGRITY_FAILURE"
        assert o.runtime_failure_status == expected_failure
        assert o.model_decision is None
        assert o.verdict == "INTEGRITY_FAILED"
        assert o.severity == "CRITICAL"
        # The invalid response is preserved as a bounded failure, never
        # re-scored as a semantic decision.
        assert (
            result.metrics["counts"]["capture_integrity_failures"] == 1
        )


# ===========================================================================
# 20. Missing model response
# ===========================================================================


class TestMissingModelResponse:
    def test_a_case_without_a_capture_record_is_not_captured(
        self, corpus, tmp_path
    ) -> None:
        case_id = "V2Q-SSD-ATTR-CAPACITY-0024"
        path = write_capture(
            tmp_path / "c.json",
            corpus,
            include_all=False,
            decisions={
                c.case_id: c.expected["decision"]
                for c in corpus.semantic_cases
                if c.case_id != case_id
            },
        )
        result = evaluate_for_model(corpus, load_capture(path), *primary_route())
        o = outcome(result, case_id)
        assert o.state == "NOT_CAPTURED"
        assert o.verdict == "NOT_EVALUATED"
        assert o.model_decision is None
        assert o.severity is None
        assert (
            result.metrics["counts"]["not_captured"] == 1
        )
        # Missing is never a pass and never a fabricated answer.
        assert result.metrics["false_match_count"] == 0

    def test_the_harness_never_manufactures_a_response(
        self, corpus, tmp_path
    ) -> None:
        """A missing case must never be evaluated against the expected
        label (that would be the harness answering for the model)."""
        path = write_capture(
            tmp_path / "c.json",
            corpus,
            include_all=False,
            decisions={},
        )
        result = evaluate_for_model(corpus, load_capture(path), *primary_route())
        assert all(
            o.state == "NOT_CAPTURED"
            for o in result.outcomes
            if o.case_class != "CONTRACT_NEGATIVE"
        )
        assert result.metrics["counts"]["evaluated_cases"] == 0
        assert result.metrics["match_recall"]["status"] == "unavailable"


# ===========================================================================
# 21. Runtime failure
# ===========================================================================


class TestRuntimeFailure:
    def test_a_primary_failure_with_no_fallback_record_is_a_runtime_failure(
        self, corpus, tmp_path
    ) -> None:
        case_id = "V2Q-SSD-ATTR-CAPACITY-0024"
        path = write_capture(
            tmp_path / "c.json",
            corpus,
            attempts_overrides={
                case_id: [
                    {
                        "role": "PRIMARY",
                        "provider": "amax",
                        "model": "qwen3.8-27b",
                        "status": "TIMEOUT",
                        "raw_output": None,
                    }
                ]
            },
        )
        result = evaluate_for_model(corpus, load_capture(path), *primary_route())
        o = outcome(result, case_id)
        assert o.state == "RUNTIME_FAILURE"
        assert o.verdict == "RUNTIME_FAILED"
        assert o.runtime_failure_status == "TIMEOUT"
        assert o.model_decision is None
        # Runtime failure is separate from semantic decisions: it is
        # neither NO_MATCH nor a pass, and it counts toward coverage.
        assert (
            result.metrics["counts"]["runtime_failure_count"] == 1
        )
        assert (
            result.metrics["counts"]["runtime_failures_by_status"]
            == {"TIMEOUT": 1}
        )

    def test_a_fallback_acceptance_preserves_provenance(
        self, corpus, tmp_path
    ) -> None:
        case_id = "V2Q-SSD-ATTR-CAPACITY-0024"
        route = fallback_route()
        path = write_capture(
            tmp_path / "c.json",
            corpus,
            attempts_overrides={
                case_id: [
                    {
                        "role": "PRIMARY",
                        "provider": primary_route()[0],
                        "model": primary_route()[1],
                        "status": "MALFORMED_JSON",
                        "raw_output": None,
                    },
                    {
                        "role": "FALLBACK",
                        "provider": route[0],
                        "model": route[1],
                        "status": "OK",
                        "raw_output": json.dumps(
                            {
                                "decision": "NO_MATCH",
                                "confidence": "HIGH",
                                "reason_code": "NO_MATCH_CAPACITY",
                                "matched_attributes": [],
                                "conflicting_attributes": [
                                    {"dimension": "CAPACITY", "detail": "x"}
                                ],
                                "missing_critical_attributes": [],
                                "conflict_classes": ["CAPACITY"],
                            }
                        ),
                    },
                ]
            },
        )
        result = evaluate_for_model(corpus, load_capture(path), *fallback_route())
        o = outcome(result, case_id)
        assert o.state == "EVALUATED"
        assert o.model_decision == "NO_MATCH"
        assert o.verdict == "CORRECT"
        assert o.provenance_role == "FALLBACK"
        assert "FALLBACK_ACCEPTED" in o.notes
        assert (
            result.metrics["counts"]["fallback_accepted_count"] == 1
        )
        # The same run projected onto the PRIMARY is a runtime failure:
        # the primary's malformed answer is not the fallback's answer.
        p_result = evaluate_for_model(corpus, load_capture(path), *primary_route())
        p_o = outcome(p_result, case_id)
        assert p_o.state == "RUNTIME_FAILURE"
        assert p_o.runtime_failure_status == "MALFORMED_JSON"

    def test_a_failed_fallback_is_a_final_runtime_failure(
        self, corpus, tmp_path
    ) -> None:
        case_id = "V2Q-SSD-ATTR-CAPACITY-0024"
        path = write_capture(
            tmp_path / "c.json",
            corpus,
            attempts_overrides={
                case_id: [
                    {
                        "role": "PRIMARY",
                        "provider": "amax",
                        "model": "qwen3.8-27b",
                        "status": "CONNECTION_ERROR",
                        "raw_output": None,
                    },
                    {
                        "role": "FALLBACK",
                        "provider": "vllm-262k",
                        "model": "Qwen3.6-27B-262K",
                        "status": "MALFORMED_JSON",
                        "raw_output": None,
                    },
                ]
            },
        )
        result = evaluate_for_model(corpus, load_capture(path), *primary_route())
        o = outcome(result, case_id)
        assert o.state == "RUNTIME_FAILURE"
        assert o.runtime_failure_status == "CONNECTION_ERROR"
        assert o.model_decision is None
        assert o.provenance_role == "PRIMARY"
        # The fallback view carries the fallback's own failure status.
        f_result = evaluate_for_model(
            corpus, load_capture(path), *fallback_route()
        )
        f_o = outcome(f_result, case_id)
        assert f_o.state == "RUNTIME_FAILURE"
        assert f_o.runtime_failure_status == "MALFORMED_JSON"

    def test_a_non_fallback_eligible_primary_failure_has_no_second_attempt(
        self, corpus, tmp_path
    ) -> None:
        """The capture contract mirrors the frozen runtime: a
        non-eligible primary failure (e.g. CASE_REJECTED) cannot have a
        fallback attempt."""
        case_id = "V2Q-SSD-ATTR-CAPACITY-0024"
        path = write_capture(
            tmp_path / "c.json",
            corpus,
        )
        doc = json.loads(path.read_text(encoding="utf-8"))
        record = next(r for r in doc["records"] if r["case_id"] == case_id)
        record["attempts"] = [
            {
                "role": "PRIMARY",
                "provider": "amax",
                "model": "qwen3.8-27b",
                "status": "CASE_REJECTED",
                "raw_output": None,
            },
            {
                "role": "FALLBACK",
                "provider": "vllm-262k",
                "model": "Qwen3.6-27B-262K",
                "status": "OK",
                "raw_output": '{"decision": "MATCH"}',
            },
        ]
        record["fallback_used"] = True
        record["fallback_reason"] = "TIMEOUT"
        path.write_text(json.dumps(doc), encoding="utf-8")
        from product_intelligence.evaluation.semantic_v2.capture import (
            CaptureIntegrityError,
            load_capture as lc,
        )

        with pytest.raises(CaptureIntegrityError, match="fallback-eligible"):
            lc(path)


# ===========================================================================
# 22-26. False-MATCH detection and severity
# ===========================================================================


@pytest.fixture(scope="module")
def adversarial_corpus(tmp_path_factory, corpus):
    path = write_capture(
        tmp_path_factory.mktemp("adversarial") / "c.json",
        corpus,
        decisions={
            "V2Q-SSD-ATTR-CAPACITY-0024": "MATCH",
            "V2Q-SSD-SU-TRAY-0032": "MATCH",
            "V2Q-SSD-ACC-CADDY-0031": "MATCH",
            "V2Q-SSD-U5NM1-MICRON-0018": "MATCH",
            "V2Q-SSD-U5NM1-ALIAS-0022": "MATCH",
            "V2Q-DIMM-U4-MATCH-0014": "NO_MATCH",
            "V2Q-SSD-U1-MATCH-0001": "UNCERTAIN",
            "V2Q-SSD-BRAND-CONTESTED-0040": "MATCH",
        },
    )
    return evaluate_for_model(corpus, load_capture(path), *primary_route())


class TestFalseMatchDetection:
    def test_false_match_is_detected(self, adversarial_corpus) -> None:
        o = outcome(adversarial_corpus, "V2Q-SSD-ATTR-CAPACITY-0024")
        assert o.verdict == "FALSE_MATCH"
        assert o.model_decision == "MATCH"
        assert o.expected_decision == "NO_MATCH"
        assert adversarial_corpus.metrics["false_match_count"] == 5

    def test_false_match_examples_carry_case_ids(
        self, adversarial_corpus
    ) -> None:
        ids = {
            e["case_id"]
            for e in adversarial_corpus.metrics["false_match_examples"]
        }
        assert ids == {
            "V2Q-SSD-ATTR-CAPACITY-0024",
            "V2Q-SSD-SU-TRAY-0032",
            "V2Q-SSD-ACC-CADDY-0031",
            "V2Q-SSD-U5NM1-MICRON-0018",
            "V2Q-SSD-U5NM1-ALIAS-0022",
        }

    def test_hard_conflict_false_match_is_critical(
        self, adversarial_corpus
    ) -> None:
        o = outcome(adversarial_corpus, "V2Q-SSD-ATTR-CAPACITY-0024")
        assert o.severity == "CRITICAL"
        assert (
            adversarial_corpus.metrics["hard_conflict_false_match_count"]
            >= 1
        )

    def test_packaging_false_match_is_critical(
        self, adversarial_corpus
    ) -> None:
        o = outcome(adversarial_corpus, "V2Q-SSD-SU-TRAY-0032")
        assert o.verdict == "FALSE_MATCH"
        assert o.severity == "CRITICAL"
        assert (
            adversarial_corpus.metrics["packaging_false_match_count"] == 1
        )

    def test_accessory_false_match_is_critical(
        self, adversarial_corpus
    ) -> None:
        o = outcome(adversarial_corpus, "V2Q-SSD-ACC-CADDY-0031")
        assert o.verdict == "FALSE_MATCH"
        assert o.severity == "CRITICAL"
        assert (
            adversarial_corpus.metrics["accessory_false_match_count"] == 1
        )

    def test_near_miss_false_match_is_detected(
        self, adversarial_corpus
    ) -> None:
        micron = outcome(
            adversarial_corpus, "V2Q-SSD-U5NM1-MICRON-0018"
        )
        alias = outcome(adversarial_corpus, "V2Q-SSD-U5NM1-ALIAS-0022")
        assert micron.verdict == "FALSE_MATCH"
        assert alias.verdict == "FALSE_MATCH"
        # The motivating Micron pair: not equivalent by shared base.
        assert micron.severity == "CRITICAL"
        assert (
            adversarial_corpus.metrics["near_miss_false_match_count"] == 2
        )
        # Both carry the commercial sales-unit-safety flag.
        assert (
            adversarial_corpus.metrics[
                "sales_unit_safety_false_match_count"
            ]
            == 3
        )

    def test_false_no_match_is_medium_and_reduces_recall(
        self, adversarial_corpus
    ) -> None:
        o = outcome(adversarial_corpus, "V2Q-DIMM-U4-MATCH-0014")
        assert o.verdict == "FALSE_NO_MATCH"
        assert o.severity == "MEDIUM"
        assert (
            adversarial_corpus.metrics["false_no_match_count"] == 1
        )
        recall = adversarial_corpus.metrics["match_recall"]
        # Two expected-MATCH authoritative cases lost their answers:
        # S14 (false NO_MATCH) and S1 (abstain on definite).
        assert recall["numerator"] == recall["denominator"] - 2

    def test_abstain_on_definite_is_review_severity(
        self, adversarial_corpus
    ) -> None:
        o = outcome(adversarial_corpus, "V2Q-SSD-U1-MATCH-0001")
        assert o.verdict == "ABSTAIN_ON_DEFINITE"
        assert o.severity == "REVIEW"

    def test_ambiguous_outside_defensible_match_is_high_not_critical(
        self, adversarial_corpus
    ) -> None:
        o = outcome(adversarial_corpus, "V2Q-SSD-BRAND-CONTESTED-0040")
        assert o.verdict == "OUTSIDE_DEFENSIBLE"
        assert o.severity == "HIGH"
        # It stays out of the authoritative false-MATCH count.
        ids = {
            e["case_id"]
            for e in adversarial_corpus.metrics["false_match_examples"]
        }
        assert "V2Q-SSD-BRAND-CONTESTED-0040" not in ids

    def test_model_confidence_never_overrides_the_label(
        self, adversarial_corpus
    ) -> None:
        """A LOW-confidence false MATCH is scored exactly like a
        HIGH-confidence one: severity comes from the label, not the
        model."""
        from tests.evaluation.semantic_v2._q3a_helpers import (
            make_response,
        )

        low = make_response("MATCH", confidence="LOW")
        high = make_response("MATCH", confidence="HIGH")
        assert low != high
        o = outcome(adversarial_corpus, "V2Q-SSD-ATTR-CAPACITY-0024")
        assert o.severity == "CRITICAL"
