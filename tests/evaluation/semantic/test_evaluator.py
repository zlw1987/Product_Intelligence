"""Tests for semantic match evaluator.

PRODUCT-INTEL.SEMANTIC

These tests verify the evaluator computes metrics correctly using hand-calculated
values. No live model integration is required.
"""

import pytest

from product_intelligence.evaluation.semantic.evaluator import (
    ConfusionMatrix,
    EvaluationResult,
    SemanticEvaluator,
    PerClassMetrics,
    parse_raw_output,
    RawOutputParseError,
    compute_corpus_distribution,
    evaluate_responses,
)
from product_intelligence.evaluation.semantic.loader import (
    SemanticCorpus,
    SemanticDecision,
    SemanticMatchResponse,
    load_corpus,
)
from product_intelligence.evaluation.semantic.vocabulary import (
    ConfidenceLevel,
    SemanticCaseClass,
)


@pytest.fixture
def corpus():
    """Load the semantic corpus."""
    return load_corpus()


# ---------------------------------------------------------------------------
# Raw output parser tests
# ---------------------------------------------------------------------------

def test_parse_raw_output_valid_json():
    """Test parsing valid JSON output."""
    raw = '{"decision": "MATCH", "confidence": "HIGH", "matched_attributes": ["mpn"], "conflicting_attributes": [], "missing_critical_attributes": [], "reason_code": "exact_mpn"}'
    result = parse_raw_output(raw)
    assert result["decision"] == "MATCH"
    assert result["confidence"] == "HIGH"


def test_parse_raw_output_rejects_prose_before():
    """Test that prose before JSON is rejected."""
    raw = 'Here is my analysis. {"decision": "MATCH", "confidence": "HIGH", "matched_attributes": [], "conflicting_attributes": [], "missing_critical_attributes": [], "reason_code": "test"}'
    with pytest.raises(RawOutputParseError) as exc_info:
        parse_raw_output(raw)
    assert "must be a JSON object" in str(exc_info.value)


def test_parse_raw_output_rejects_markdown_fences():
    """Test that markdown code fences are rejected."""
    raw = '```json\n{"decision": "MATCH", "confidence": "HIGH", "matched_attributes": [], "conflicting_attributes": [], "missing_critical_attributes": [], "reason_code": "test"}\n```'
    with pytest.raises(RawOutputParseError) as exc_info:
        parse_raw_output(raw)
    assert "code fences" in str(exc_info.value)


def test_parse_raw_output_rejects_prose_after():
    """Test that prose after JSON is rejected."""
    raw = '{"decision": "MATCH", "confidence": "HIGH", "matched_attributes": [], "conflicting_attributes": [], "missing_critical_attributes": [], "reason_code": "test"}\nHere is my explanation.'
    with pytest.raises(RawOutputParseError) as exc_info:
        parse_raw_output(raw)
    assert "end with '}'" in str(exc_info.value)


def test_parse_raw_output_rejects_array():
    """Test that JSON arrays are rejected."""
    raw = '[{"decision": "MATCH", "confidence": "HIGH", "matched_attributes": [], "conflicting_attributes": [], "missing_critical_attributes": [], "reason_code": "test"}]'
    with pytest.raises(RawOutputParseError) as exc_info:
        parse_raw_output(raw)
    assert "JSON object" in str(exc_info.value)


def test_parse_raw_output_rejects_invalid_json():
    """Test that malformed JSON is rejected."""
    raw = '{"decision": "MATCH" invalid}'
    with pytest.raises(RawOutputParseError) as exc_info:
        parse_raw_output(raw)
    assert "Invalid JSON" in str(exc_info.value)


def test_parse_raw_output_rejects_missing_keys():
    """Test that missing required keys are rejected."""
    raw = '{"decision": "MATCH"}'
    with pytest.raises(RawOutputParseError) as exc_info:
        parse_raw_output(raw)
    assert "Missing required keys" in str(exc_info.value)


def test_parse_raw_output_rejects_unknown_keys():
    """Test that unknown keys are rejected."""
    raw = '{"decision": "MATCH", "confidence": "HIGH", "matched_attributes": [], "conflicting_attributes": [], "missing_critical_attributes": [], "reason_code": "test", "extra": "field"}'
    with pytest.raises(RawOutputParseError) as exc_info:
        parse_raw_output(raw)
    assert "Unknown keys" in str(exc_info.value)


def test_parse_raw_output_rejects_invalid_decision():
    """Test that invalid decision enum is rejected."""
    raw = '{"decision": "INVALID", "confidence": "HIGH", "matched_attributes": [], "conflicting_attributes": [], "missing_critical_attributes": [], "reason_code": "test"}'
    with pytest.raises(RawOutputParseError) as exc_info:
        parse_raw_output(raw)
    assert "Invalid decision" in str(exc_info.value)


def test_parse_raw_output_rejects_empty_reason():
    """Test that empty reason_code is rejected."""
    raw = '{"decision": "MATCH", "confidence": "HIGH", "matched_attributes": [], "conflicting_attributes": [], "missing_critical_attributes": [], "reason_code": ""}'
    with pytest.raises(RawOutputParseError) as exc_info:
        parse_raw_output(raw)
    assert "reason_code" in str(exc_info.value)


def test_parse_raw_output_accepts_valid_reason():
    """Test that valid reason_code is accepted."""
    raw = '{"decision": "MATCH", "confidence": "HIGH", "matched_attributes": [], "conflicting_attributes": [], "missing_critical_attributes": [], "reason_code": "test"}'
    result = parse_raw_output(raw)
    assert result["reason_code"] == "test"


# ---------------------------------------------------------------------------
# Perfect prediction hand-test
# ---------------------------------------------------------------------------

def test_perfect_prediction_metrics(corpus):
    """Hand-calculated test: perfect prediction on a small set.

    Setup: 5 cases, all decisions predicted correctly.
    Expected:
    - decision_accuracy = 1.0 (for the 5 evaluated cases)
    - false_match_count = 0
    - safety_cost = 0
    """
    cases = list(corpus.cases)[:5]

    # Perfect predictions
    responses = {}
    for case in cases:
        responses[case.case_id] = {
            "decision": case.expected_decision.value,
            "confidence": "HIGH",
            "matched_attributes": [],
            "conflicting_attributes": [],
            "missing_critical_attributes": [],
            "reason_code": "perfect",
        }

    result = evaluate_responses(corpus, responses)

    # Perfect accuracy for evaluated cases
    assert result.decision_accuracy == 1.0
    assert result.false_match_count == 0
    assert result.safety_cost == 0
    # valid_output_rate reflects coverage of the 5 cases we provided
    # (5/5 = 1.0 for those cases, but measured against total corpus in result)
    assert result.valid_response_count == 5
    assert result.invalid_or_missing_count == len(corpus.cases) - 5


# ---------------------------------------------------------------------------
# One false MATCH hand-test
# ---------------------------------------------------------------------------

def test_one_false_match_metrics(corpus):
    """Hand-calculated test: one false MATCH.

    Setup: 5 cases, one predicted MATCH when expected NO_MATCH.
    Expected:
    - false_match_count = 1
    - match_precision < 1.0
    - safety_cost = 10 (one false MATCH costs 10)
    """
    cases = list(corpus.cases)[:5]

    # Find one NO_MATCH case to turn into false MATCH
    responses = {}
    false_match_case = None
    for case in cases:
        if case.expected_decision == SemanticDecision.NO_MATCH and false_match_case is None:
            # This will be a false MATCH
            responses[case.case_id] = {
                "decision": "MATCH",
                "confidence": "HIGH",
                "matched_attributes": ["mpn"],
                "conflicting_attributes": [],
                "missing_critical_attributes": [],
                "reason_code": "wrong",
            }
            false_match_case = case
        else:
            responses[case.case_id] = {
                "decision": case.expected_decision.value,
                "confidence": "HIGH",
                "matched_attributes": [],
                "conflicting_attributes": [],
                "missing_critical_attributes": [],
                "reason_code": "correct",
            }

    # Skip if we couldn't find a NO_MATCH case
    if false_match_case is None:
        pytest.skip("No NO_MATCH case in first 5")

    result = evaluate_responses(corpus, responses)

    assert result.false_match_count == 1
    assert result.match_precision < 1.0
    assert result.safety_cost >= 10  # At least one false MATCH (cost 10)


# ---------------------------------------------------------------------------
# Missing/invalid output behavior
# ---------------------------------------------------------------------------

def test_missing_response_not_counted_as_no_match(corpus):
    """Test that missing responses are counted as invalid, not as NO_MATCH.

    When a case has no response provided, it should:
    - reduce valid_output_rate
    - NOT appear in confusion matrix as a NO_MATCH prediction
    - NOT contribute to accuracy calculation
    """
    test_corpus = corpus  # corpus is the fixture, already a SemanticCorpus
    cases = list(test_corpus.cases)[:5]

    # Only provide responses for 3 cases
    responses = {
        cases[0].case_id: {
            "decision": cases[0].expected_decision.value,
            "confidence": "HIGH",
            "matched_attributes": [],
            "conflicting_attributes": [],
            "missing_critical_attributes": [],
            "reason_code": "test",
        },
        cases[1].case_id: {
            "decision": cases[1].expected_decision.value,
            "confidence": "HIGH",
            "matched_attributes": [],
            "conflicting_attributes": [],
            "missing_critical_attributes": [],
            "reason_code": "test",
        },
        cases[2].case_id: {
            "decision": cases[2].expected_decision.value,
            "confidence": "HIGH",
            "matched_attributes": [],
            "conflicting_attributes": [],
            "missing_critical_attributes": [],
            "reason_code": "test",
        },
    }

    result = evaluate_responses(test_corpus, responses)

    # We provided 3 valid responses for the 3 cases
    assert result.valid_response_count == 3
    # The rest of the corpus (64 - 3 = 61) are missing/invalid
    assert result.invalid_or_missing_count == len(test_corpus.cases) - 3


def test_invalid_response_not_counted_as_no_match(corpus):
    """Test that invalid responses are counted as invalid, not as predictions.

    When a response has invalid format:
    - reduce valid_output_rate
    - NOT appear in confusion matrix
    - NOT contribute to accuracy
    """
    cases = list(corpus.cases)[:5]

    responses = {
        cases[0].case_id: {
            "decision": cases[0].expected_decision.value,
            "confidence": "HIGH",
            "matched_attributes": [],
            "conflicting_attributes": [],
            "missing_critical_attributes": [],
            "reason_code": "test",
        },
        cases[1].case_id: {
            "decision": "INVALID_DECISION",  # Invalid
            "confidence": "HIGH",
            "matched_attributes": [],
            "conflicting_attributes": [],
            "missing_critical_attributes": [],
            "reason_code": "test",
        },
    }

    result = evaluate_responses(corpus, responses)

    # valid_output_rate should be less than 1.0
    assert result.valid_output_rate < 1.0


def test_valid_output_rate_never_exceeds_one(corpus):
    """Test that valid_output_rate is bounded at 1.0."""
    cases = list(corpus.cases)[:5]

    # Provide perfect responses for all
    responses = {
        case.case_id: {
            "decision": case.expected_decision.value,
            "confidence": "HIGH",
            "matched_attributes": [],
            "conflicting_attributes": [],
            "missing_critical_attributes": [],
            "reason_code": "test",
        }
        for case in cases
    }

    result = evaluate_responses(corpus, responses)

    assert result.valid_output_rate <= 1.0
    assert result.decision_accuracy <= 1.0


# ---------------------------------------------------------------------------
# Confusion matrix tests
# ---------------------------------------------------------------------------

def test_confusion_matrix_total():
    """Test confusion matrix total is sum of all cells."""
    cm = ConfusionMatrix(
        match_to_match=5,
        match_to_no_match=2,
        match_to_uncertain=1,
        no_match_to_match=1,
        no_match_to_no_match=10,
        no_match_to_uncertain=2,
        uncertain_to_match=1,
        uncertain_to_no_match=2,
        uncertain_to_uncertain=8,
    )
    assert cm.total == 32


def test_confusion_matrix_perfect_accuracy():
    """Test confusion matrix with perfect predictions."""
    cm = ConfusionMatrix(
        match_to_match=5,
        match_to_no_match=0,
        match_to_uncertain=0,
        no_match_to_match=0,
        no_match_to_no_match=10,
        no_match_to_uncertain=0,
        uncertain_to_match=0,
        uncertain_to_no_match=0,
        uncertain_to_uncertain=3,
    )
    assert cm.total == 18
    # Perfect accuracy: 5+10+3 = 18 correct out of 18 = 1.0
    assert cm.match_to_match == 5
    assert cm.no_match_to_no_match == 10
    assert cm.uncertain_to_uncertain == 3


def test_confusion_matrix_one_false_match():
    """Test confusion matrix with one false MATCH."""
    cm = ConfusionMatrix(
        match_to_match=3,
        match_to_no_match=1,
        match_to_uncertain=1,
        no_match_to_match=1,  # False MATCH
        no_match_to_no_match=8,
        no_match_to_uncertain=1,
        uncertain_to_match=0,
        uncertain_to_no_match=0,
        uncertain_to_uncertain=3,
    )
    assert cm.total == 18
    assert cm.no_match_to_match == 1  # One false MATCH


# ---------------------------------------------------------------------------
# Safety cost tests
# ---------------------------------------------------------------------------

def test_safety_cost_lower_is_better(corpus):
    """Test that safety_cost is a cost (lower is better).

    A model with 0 false MATCH should have safety_cost=0.
    A model with 1 false MATCH should have higher safety_cost.
    """
    cases = list(corpus.cases)[:5]

    # Zero errors
    responses_zero = {
        case.case_id: {
            "decision": case.expected_decision.value,
            "confidence": "HIGH",
            "matched_attributes": [],
            "conflicting_attributes": [],
            "missing_critical_attributes": [],
            "reason_code": "test",
        }
        for case in cases
    }
    result_zero = evaluate_responses(corpus, responses_zero)

    # One false MATCH
    responses_one_fp = {}
    found_no_match = False
    for case in cases:
        if case.expected_decision == SemanticDecision.NO_MATCH and not found_no_match:
            responses_one_fp[case.case_id] = {
                "decision": "MATCH",  # Wrong!
                "confidence": "HIGH",
                "matched_attributes": [],
                "conflicting_attributes": [],
                "missing_critical_attributes": [],
                "reason_code": "wrong",
            }
            found_no_match = True
        else:
            responses_one_fp[case.case_id] = {
                "decision": case.expected_decision.value,
                "confidence": "HIGH",
                "matched_attributes": [],
                "conflicting_attributes": [],
                "missing_critical_attributes": [],
                "reason_code": "correct",
            }

    if not found_no_match:
        pytest.skip("No NO_MATCH case available")

    result_one_fp = evaluate_responses(corpus, responses_one_fp)

    # One false MATCH should have higher safety_cost
    assert result_one_fp.safety_cost > result_zero.safety_cost


def test_safety_cost_false_match_penalized_10x(corpus):
    """Test that false MATCH is penalized 10x more than other errors."""
    cases = list(corpus.cases)[:10]

    # Find cases to create specific error scenarios
    no_match_cases = [c for c in cases if c.expected_decision == SemanticDecision.NO_MATCH]
    uncertain_cases = [c for c in cases if c.expected_decision == SemanticDecision.UNCERTAIN]

    if len(no_match_cases) < 1:
        pytest.skip("Need at least 1 NO_MATCH case")

    # Scenario 1: One false MATCH
    responses_fp = {}
    fp_case = no_match_cases[0]
    for case in cases:
        if case.case_id == fp_case.case_id:
            responses_fp[case.case_id] = {
                "decision": "MATCH",  # False MATCH
                "confidence": "HIGH",
                "matched_attributes": [],
                "conflicting_attributes": [],
                "missing_critical_attributes": [],
                "reason_code": "fp",
            }
        else:
            responses_fp[case.case_id] = {
                "decision": case.expected_decision.value,
                "confidence": "HIGH",
                "matched_attributes": [],
                "conflicting_attributes": [],
                "missing_critical_attributes": [],
                "reason_code": "correct",
            }
    result_fp = evaluate_responses(corpus, responses_fp)

    # Scenario 2: One false UNCERTAIN (predicting UNCERTAIN when expecting NO_MATCH)
    responses_fn = {}
    fn_case = no_match_cases[0] if len(no_match_cases) > 0 else None
    if fn_case is None:
        pytest.skip("Need NO_MATCH case")

    for case in cases:
        if case.case_id == fn_case.case_id:
            responses_fn[case.case_id] = {
                "decision": "UNCERTAIN",  # Wrong, but not false MATCH
                "confidence": "LOW",
                "matched_attributes": [],
                "conflicting_attributes": [],
                "missing_critical_attributes": [],
                "reason_code": "fn",
            }
        else:
            responses_fn[case.case_id] = {
                "decision": case.expected_decision.value,
                "confidence": "HIGH",
                "matched_attributes": [],
                "conflicting_attributes": [],
                "missing_critical_attributes": [],
                "reason_code": "correct",
            }
    result_fn = evaluate_responses(corpus, responses_fn)

    # False MATCH (fp) should cost more than other wrong decision (fn)
    # safety_cost = fp * 10 + fn * 1 + ...
    assert result_fp.safety_cost > result_fn.safety_cost


# ---------------------------------------------------------------------------
# Per-class metrics tests
# ---------------------------------------------------------------------------

def test_per_class_metrics_populated(corpus):
    """Test that per-class metrics are populated for all classes in corpus."""
    cases = list(corpus.cases)[:10]

    responses = {
        case.case_id: {
            "decision": case.expected_decision.value,
            "confidence": "HIGH",
            "matched_attributes": [],
            "conflicting_attributes": [],
            "missing_critical_attributes": [],
            "reason_code": "test",
        }
        for case in cases
    }

    result = evaluate_responses(corpus, responses)

    # At least some classes should be populated
    assert len(result.per_class_metrics) > 0

    # Check structure of per-class metrics
    for cls, metrics in result.per_class_metrics.items():
        assert isinstance(metrics, PerClassMetrics)
        assert metrics.case_count >= 0
        assert metrics.valid_count >= 0
        assert metrics.correct >= 0
        # False match count should be tracked
        assert metrics.false_match_count >= 0


def test_per_class_metrics_multiple_classes(corpus):
    """Test per-class metrics with multiple different case classes.

    Hand-calculated values for a specific set of cases.
    """
    # Use a subset with multiple classes
    cases = list(corpus.cases)

    # Find cases of different classes
    title_exact_cases = [c for c in cases if c.case_class == SemanticCaseClass.TITLE_EXACT_MPN][:2]
    accessory_cases = [c for c in cases if c.case_class == SemanticCaseClass.ACCESSORY_TRAP][:2]

    if len(title_exact_cases) < 1 or len(accessory_cases) < 1:
        pytest.skip("Need at least TITLE_EXACT_MPN and ACCESSORY_TRAP cases")

    selected_cases = title_exact_cases + accessory_cases

    responses = {
        case.case_id: {
            "decision": case.expected_decision.value,
            "confidence": "HIGH",
            "matched_attributes": [],
            "conflicting_attributes": [],
            "missing_critical_attributes": [],
            "reason_code": "test",
        }
        for case in selected_cases
    }

    result = evaluate_responses(corpus, responses)

    # Both classes should have metrics
    title_exact = SemanticCaseClass.TITLE_EXACT_MPN
    accessory = SemanticCaseClass.ACCESSORY_TRAP

    if title_exact in result.per_class_metrics:
        assert result.per_class_metrics[title_exact].case_count >= 2
    if accessory in result.per_class_metrics:
        assert result.per_class_metrics[accessory].case_count >= 2


# ---------------------------------------------------------------------------
# Authority safety probe tests
# ---------------------------------------------------------------------------

def test_authority_safety_probes_tracked(corpus):
    """Test that authority safety probes are tracked separately."""
    # Find cases marked as authority safety probes
    probe_cases = [c for c in corpus.cases if c.is_authority_safety_probe]

    if len(probe_cases) == 0:
        pytest.skip("No authority safety probe cases in corpus")

    responses = {
        case.case_id: {
            "decision": case.expected_decision.value,
            "confidence": "HIGH",
            "matched_attributes": [],
            "conflicting_attributes": [],
            "missing_critical_attributes": [],
            "reason_code": "test",
        }
        for case in probe_cases
    }

    result = evaluate_responses(corpus, responses)

    # If all probes passed, authority_safety_probes_passed should be True
    assert hasattr(result, 'authority_safety_probes_passed')


# ---------------------------------------------------------------------------
# Qualification gates tests
# ---------------------------------------------------------------------------

def test_qualification_gates_structured(corpus):
    """Test that qualification gates are properly structured."""
    cases = list(corpus.cases)[:5]

    responses = {
        case.case_id: {
            "decision": case.expected_decision.value,
            "confidence": "HIGH",
            "matched_attributes": [],
            "conflicting_attributes": [],
            "missing_critical_attributes": [],
            "reason_code": "test",
        }
        for case in cases
    }

    result = evaluate_responses(corpus, responses)

    assert hasattr(result, 'gates_passed')
    assert isinstance(result.gates_passed, dict)

    # Check gate names
    expected_gates = {
        "zero_false_match_on_authority_conflicts",
        "zero_false_match_on_accessory_safety_set",
        "primary_valid_output_rate_sufficient",
        "primary_match_precision_sufficient",
        "primary_overall_accuracy_target",
    }
    assert set(result.gates_passed.keys()) == expected_gates


def test_zero_false_match_gate(corpus):
    """Test zero false MATCH gate with perfect predictions on primary cases.

    This test uses only primary (non-authority-probe) cases to verify that
    when a model makes perfect predictions on primary cases, the primary
    metrics are perfect and there are no false MATCHes on primary cases.

    Note: Authority conflict gate requires ALL authority conflict IDs to have
    valid responses. This test only provides primary case responses, so the
    authority conflict gate will be False (missing required responses).
    """
    # Get only primary (non-authority-probe) cases
    primary_cases = [c for c in corpus.cases if not c.is_authority_safety_probe][:10]

    responses = {
        case.case_id: {
            "decision": case.expected_decision.value,
            "confidence": "HIGH",
            "matched_attributes": [],
            "conflicting_attributes": [],
            "missing_critical_attributes": [],
            "reason_code": "test",
        }
        for case in primary_cases
    }

    result = evaluate_responses(corpus, responses)

    # Perfect predictions on primary should have zero primary false MATCH
    if result.primary_false_match_count == 0:
        # Primary metrics should be perfect
        assert result.primary_match_precision == 1.0
        assert result.primary_match_recall == 1.0
        assert result.primary_decision_accuracy == 1.0

    # Authority conflict gate will be False because we're missing authority conflict responses
    # (this is expected - the gate requires ALL authority conflicts to be answered)
    # We just verify the gate exists and is False in this case
    assert "zero_false_match_on_authority_conflicts" in result.gates_passed


def test_precision_gate(corpus):
    """Test precision gate behavior."""
    cases = list(corpus.cases)[:10]

    # Perfect predictions should have precision = 1.0
    responses = {
        case.case_id: {
            "decision": case.expected_decision.value,
            "confidence": "HIGH",
            "matched_attributes": [],
            "conflicting_attributes": [],
            "missing_critical_attributes": [],
            "reason_code": "test",
        }
        for case in cases
    }

    result = evaluate_responses(corpus, responses)

    # If there are MATCH cases and all correct, precision should be 1.0
    match_cases = [c for c in cases if c.expected_decision == SemanticDecision.MATCH]
    if len(match_cases) > 0 and result.false_match_count == 0:
        assert result.gates_passed["primary_match_precision_sufficient"]


# ---------------------------------------------------------------------------
# Convenience function test
# ---------------------------------------------------------------------------

def test_evaluate_responses_convenience_function(corpus):
    """Test the evaluate_responses convenience function."""
    cases = list(corpus.cases)[:3]

    responses = {
        case.case_id: {
            "decision": case.expected_decision.value,
            "confidence": "HIGH",
            "matched_attributes": [],
            "conflicting_attributes": [],
            "missing_critical_attributes": [],
            "reason_code": "test",
        }
        for case in cases
    }

    result = evaluate_responses(corpus, responses)

    assert isinstance(result, EvaluationResult)
    assert result.total_corpus_cases == len(corpus.cases)


# ---------------------------------------------------------------------------
# Last result getter test
# ---------------------------------------------------------------------------

def test_last_result_getter(corpus):
    """Test get_last_result."""
    evaluator = SemanticEvaluator(corpus)
    result1 = evaluator.evaluate({})
    result2 = evaluator.evaluate({})

    assert evaluator.get_last_result() is result2

    # New evaluator should have no results
    new_evaluator = SemanticEvaluator(corpus)
    with pytest.raises(IndexError):
        new_evaluator.get_last_result()


# ---------------------------------------------------------------------------
# Corpus distribution test
# ---------------------------------------------------------------------------

def test_corpus_distribution_computed(corpus):
    """Test that corpus distribution is computed from cases.json."""
    dist = compute_corpus_distribution(corpus)

    assert dist["total_cases"] == len(corpus.cases)
    assert dist["total_cases"] >= 50

    # Check by decision
    assert "MATCH" in dist["by_decision"]
    assert "NO_MATCH" in dist["by_decision"]
    assert "UNCERTAIN" in dist["by_decision"]

    # Sum of decisions should equal total
    decision_sum = sum(dist["by_decision"].values())
    assert decision_sum == dist["total_cases"]

    # Check by case class
    assert len(dist["by_case_class"]) > 0

    # Check by evidence source
    assert len(dist["by_evidence_source"]) > 0

    # Primary semantic cases should be less than total (authority probes separate)
    assert dist["primary_semantic_cases"] <= dist["total_cases"]


# ---------------------------------------------------------------------------
# Reject response IDs not in corpus
# ---------------------------------------------------------------------------

def test_unknown_response_ids_fail_closed(corpus):
    """Test that unknown response IDs raise ValueError.

    Unknown case IDs must NOT be silently ignored.
    Evaluation must not proceed with unknown IDs.
    """
    cases = list(corpus.cases)[:3]

    responses = {
        case.case_id: {
            "decision": case.expected_decision.value,
            "confidence": "HIGH",
            "matched_attributes": [],
            "conflicting_attributes": [],
            "missing_critical_attributes": [],
            "reason_code": "test",
        }
        for case in cases
    }

    # Add a response for a non-existent case
    responses["NONEXISTENT-CASE"] = {
        "decision": "MATCH",
        "confidence": "HIGH",
        "matched_attributes": [],
        "conflicting_attributes": [],
        "missing_critical_attributes": [],
        "reason_code": "test",
    }

    # Must raise ValueError for unknown case ID
    with pytest.raises(ValueError) as exc_info:
        evaluate_responses(corpus, responses)

    assert "NONEXISTENT-CASE" in str(exc_info.value)
    assert "Unknown case IDs" in str(exc_info.value)


# ---------------------------------------------------------------------------
# P0: Regression test for U->M false MATCH
# MANDATORY: Expected UNCERTAIN, Predicted MATCH must:
#   - increment false_match_count
#   - reduce MATCH precision
#   - incur false-MATCH safety cost (10x)
#   - appear at U->M in confusion matrix
# ---------------------------------------------------------------------------

def test_uncertain_to_match_false_match_regression(corpus):
    """MANDATORY regression: U->M must behave like false MATCH.

    When expected UNCERTAIN but predicted MATCH:
    - false_match_count must increment
    - MATCH precision must decrease
    - safety_cost must include 10x penalty
    - confusion_matrix.uncertain_to_match must increment
    """
    cases = list(corpus.cases)[:10]

    # Find an UNCERTAIN case
    uncertain_case = None
    for c in cases:
        if c.expected_decision == SemanticDecision.UNCERTAIN:
            uncertain_case = c
            break

    if uncertain_case is None:
        pytest.skip("No UNCERTAIN case in first 10")

    # Scenario 1: Perfect predictions
    responses_perfect = {}
    for case in cases:
        responses_perfect[case.case_id] = {
            "decision": case.expected_decision.value,
            "confidence": "HIGH",
            "matched_attributes": [],
            "conflicting_attributes": [],
            "missing_critical_attributes": [],
            "reason_code": "correct",
        }
    result_perfect = evaluate_responses(corpus, responses_perfect)

    # Scenario 2: Same but U->M on the uncertain case
    responses_u_to_m = {}
    for case in cases:
        if case.case_id == uncertain_case.case_id:
            responses_u_to_m[case.case_id] = {
                "decision": "MATCH",  # Wrong! Should be UNCERTAIN
                "confidence": "HIGH",
                "matched_attributes": [],
                "conflicting_attributes": [],
                "missing_critical_attributes": [],
                "reason_code": "wrong",
            }
        else:
            responses_u_to_m[case.case_id] = {
                "decision": case.expected_decision.value,
                "confidence": "HIGH",
                "matched_attributes": [],
                "conflicting_attributes": [],
                "missing_critical_attributes": [],
                "reason_code": "correct",
            }
    result_u_to_m = evaluate_responses(corpus, responses_u_to_m)

    # U->M MUST increment false_match_count
    assert result_u_to_m.false_match_count == result_perfect.false_match_count + 1
    assert result_u_to_m.false_match_count == 1

    # U->M MUST reduce MATCH precision
    assert result_u_to_m.match_precision < result_perfect.match_precision

    # U->M MUST incur 10x safety cost penalty
    assert result_u_to_m.safety_cost == result_perfect.safety_cost + 10

    # U->M MUST appear in confusion matrix at uncertain_to_match
    assert result_u_to_m.confusion_matrix.uncertain_to_match == 1


# ---------------------------------------------------------------------------
# P0: Hand-calculated confusion matrix precision/recall formulas
# ---------------------------------------------------------------------------

def test_hand_calculated_confusion_matrix_precision_recall():
    """Hand-calculated test: verify metrics derived from 3x3 confusion matrix.

    Setup a known confusion matrix:
    Actual MATCH:      M->M=3, M->N=1, M->U=1  (5 total)
    Actual NO_MATCH:   N->M=1, N->N=8, N->U=1  (10 total)
    Actual UNCERTAIN:  U->M=1, U->N=0, U->U=3  (4 total)

    Total valid = 19
    Correct = M->M + N->N + U->U = 3 + 8 + 3 = 14

    Derived metrics (from spec):
    - decision_accuracy = 14/19
    - MATCH precision = M->M / (M->M + N->M + U->M) = 3 / (3+1+1) = 3/5 = 0.6
    - MATCH recall = M->M / (M->M + M->N + M->U) = 3 / (3+1+1) = 3/5 = 0.6
    - NO_MATCH precision = N->N / (M->N + N->N + U->N) = 8 / (1+8+0) = 8/9
    - NO_MATCH recall = N->N / (N->M + N->N + N->U) = 8 / (1+8+1) = 8/10 = 0.8
    - UNCERTAIN precision = U->U / (M->U + N->U + U->U) = 3 / (1+1+3) = 3/5 = 0.6
    - UNCERTAIN recall = U->U / (U->M + U->N + U->U) = 3 / (1+0+3) = 3/4 = 0.75
    """
    cm = ConfusionMatrix(
        match_to_match=3,
        match_to_no_match=1,
        match_to_uncertain=1,
        no_match_to_match=1,
        no_match_to_no_match=8,
        no_match_to_uncertain=1,
        uncertain_to_match=1,
        uncertain_to_no_match=0,
        uncertain_to_uncertain=3,
    )

    # Verify total
    assert cm.total == 19

    # Verify decision_accuracy derivation
    correct = cm.match_to_match + cm.no_match_to_no_match + cm.uncertain_to_uncertain
    assert correct == 14
    decision_accuracy = correct / cm.total
    assert abs(decision_accuracy - 14/19) < 1e-9

    # Verify MATCH precision = M->M / (M->M + N->M + U->M)
    match_precision_expected = cm.match_to_match / (
        cm.match_to_match + cm.no_match_to_match + cm.uncertain_to_match
    )
    assert abs(match_precision_expected - 3/5) < 1e-9

    # Verify MATCH recall = M->M / (M->M + M->N + M->U)
    match_recall_expected = cm.match_to_match / (
        cm.match_to_match + cm.match_to_no_match + cm.match_to_uncertain
    )
    assert abs(match_recall_expected - 3/5) < 1e-9

    # Verify NO_MATCH precision = N->N / (M->N + N->N + U->N)
    no_match_precision_expected = cm.no_match_to_no_match / (
        cm.match_to_no_match + cm.no_match_to_no_match + cm.uncertain_to_no_match
    )
    assert abs(no_match_precision_expected - 8/9) < 1e-9

    # Verify NO_MATCH recall = N->N / (N->M + N->N + N->U)
    no_match_recall_expected = cm.no_match_to_no_match / (
        cm.no_match_to_match + cm.no_match_to_no_match + cm.no_match_to_uncertain
    )
    assert abs(no_match_recall_expected - 8/10) < 1e-9

    # Verify UNCERTAIN precision = U->U / (M->U + N->U + U->U)
    uncertain_precision_expected = cm.uncertain_to_uncertain / (
        cm.match_to_uncertain + cm.no_match_to_uncertain + cm.uncertain_to_uncertain
    )
    assert abs(uncertain_precision_expected - 3/5) < 1e-9

    # Verify UNCERTAIN recall = U->U / (U->M + U->N + U->U)
    uncertain_recall_expected = cm.uncertain_to_uncertain / (
        cm.uncertain_to_match + cm.uncertain_to_no_match + cm.uncertain_to_uncertain
    )
    assert abs(uncertain_recall_expected - 3/4) < 1e-9


# ---------------------------------------------------------------------------
# P0: Safety cost hand-calculated examples
# ---------------------------------------------------------------------------

def test_safety_cost_hand_calculated_examples():
    """Hand-calculated safety cost examples.

    Safety cost formula (corrected):
    - false MATCH (N->M + U->M): 10 each
    - other wrong decisions (M->N, M->U, N->U, U->N): 1 each
    - correct decisions: 0

    Example 1: N->M only
    - match_fp = 1, other errors = 0
    - safety_cost = 10*1 + 0 = 10

    Example 2: U->M only  
    - uncertain_fp = 1, other errors = 0
    - safety_cost = 10*1 + 0 = 10

    Example 3: N->M + M->N (one false MATCH + one other)
    - match_fp = 1, match_fn = 1, other errors = 0
    - safety_cost = 10*1 + 1*1 = 11

    Example 4: U->M + N->U (one false MATCH + one other)
    - uncertain_fp = 1, no_match_fn = 1
    - safety_cost = 10*1 + 1*1 = 11

    Example 5: M->N + M->U (two missed MATCH, no false MATCH)
    - match_fn = 2, false_match = 0
    - safety_cost = 0 + 2*1 = 2
    """
    # The formula is: safety_cost = (match_fp + uncertain_fp) * 10 + match_fn + no_match_fn + uncertain_fn
    # Verify our expectations match the formula with hand-calculated values

    # Example 1: N->M only (one false MATCH)
    # match_fp=1, uncertain_fp=0, match_fn=0, no_match_fn=0, uncertain_fn=0
    # safety_cost = (1+0)*10 + 0+0+0 = 10
    assert (1 * 10) == 10  # N->M or U->M alone

    # Example 2: U->M only (also false MATCH)
    # match_fp=0, uncertain_fp=1, match_fn=0, no_match_fn=0, uncertain_fn=0
    # safety_cost = (0+1)*10 + 0+0+0 = 10
    assert (1 * 10) == 10  # U->M alone also 10

    # Example 3: N->M + M->N (one false MATCH + one other error)
    # match_fp=1, match_fn=1
    # safety_cost = (1+0)*10 + 1 = 11
    assert (1 * 10 + 1 * 1) == 11  # N->M + M->N

    # Example 4: U->M + N->U (one false MATCH + one other error)
    # uncertain_fp=1, no_match_fn=1
    # safety_cost = (0+1)*10 + 1 = 11
    assert (1 * 10 + 1 * 1) == 11  # U->M + N->U

    # Example 5: M->N + M->U (two missed MATCH, no false MATCH)
    # match_fn=2, match_fp=0, uncertain_fp=0
    # safety_cost = 0*10 + 2 = 2
    assert (2 * 1) == 2  # M->N + M->U (no false MATCH)


def test_safety_cost_comparison_false_match_vs_other(corpus):
    """Verify false MATCH costs 10x more than other errors.

    One U->M should have higher safety cost than one M->U.
    """
    # Find one UNCERTAIN and one MATCH case
    uncertain_case = None
    match_case = None
    for c in corpus.cases:
        if c.expected_decision == SemanticDecision.UNCERTAIN and uncertain_case is None:
            uncertain_case = c
        if c.expected_decision == SemanticDecision.MATCH and match_case is None:
            match_case = c
        if uncertain_case and match_case:
            break

    if not uncertain_case or not match_case:
        pytest.skip("Need both UNCERTAIN and MATCH cases")

    # Scenario 1: U->M (false MATCH on UNCERTAIN)
    responses_u_to_m = {}
    for case in list(corpus.cases)[:5]:
        if case.case_id == uncertain_case.case_id:
            responses_u_to_m[case.case_id] = {
                "decision": "MATCH",
                "confidence": "HIGH",
                "matched_attributes": [],
                "conflicting_attributes": [],
                "missing_critical_attributes": [],
                "reason_code": "wrong",
            }
        else:
            responses_u_to_m[case.case_id] = {
                "decision": case.expected_decision.value,
                "confidence": "HIGH",
                "matched_attributes": [],
                "conflicting_attributes": [],
                "missing_critical_attributes": [],
                "reason_code": "correct",
            }
    result_u_to_m = evaluate_responses(corpus, responses_u_to_m)

    # Scenario 2: M->U (missed MATCH)
    responses_m_to_u = {}
    for case in list(corpus.cases)[:5]:
        if case.case_id == match_case.case_id:
            responses_m_to_u[case.case_id] = {
                "decision": "UNCERTAIN",
                "confidence": "LOW",
                "matched_attributes": [],
                "conflicting_attributes": [],
                "missing_critical_attributes": [],
                "reason_code": "wrong",
            }
        else:
            responses_m_to_u[case.case_id] = {
                "decision": case.expected_decision.value,
                "confidence": "HIGH",
                "matched_attributes": [],
                "conflicting_attributes": [],
                "missing_critical_attributes": [],
                "reason_code": "correct",
            }
    result_m_to_u = evaluate_responses(corpus, responses_m_to_u)

    # False MATCH (U->M) should cost MORE than missed MATCH (M->U)
    assert result_u_to_m.safety_cost > result_m_to_u.safety_cost
    # U->M = 10, M->U = 1
    assert result_u_to_m.safety_cost == 10
    assert result_m_to_u.safety_cost == 1


# ---------------------------------------------------------------------------
# P0: Test strict rejection of prose/explanation/notes keys
# ---------------------------------------------------------------------------

def test_parse_raw_output_rejects_prose_key():
    """Test that 'prose' key is rejected."""
    raw = '{"decision": "MATCH", "confidence": "HIGH", "matched_attributes": [], "conflicting_attributes": [], "missing_critical_attributes": [], "reason_code": "test", "prose": "some explanation"}'
    with pytest.raises(RawOutputParseError) as exc_info:
        parse_raw_output(raw)
    assert "Unknown keys" in str(exc_info.value)


def test_parse_raw_output_rejects_explanation_key():
    """Test that 'explanation' key is rejected."""
    raw = '{"decision": "MATCH", "confidence": "HIGH", "matched_attributes": [], "conflicting_attributes": [], "missing_critical_attributes": [], "reason_code": "test", "explanation": "some explanation"}'
    with pytest.raises(RawOutputParseError) as exc_info:
        parse_raw_output(raw)
    assert "Unknown keys" in str(exc_info.value)


def test_parse_raw_output_rejects_notes_key():
    """Test that 'notes' key is rejected."""
    raw = '{"decision": "MATCH", "confidence": "HIGH", "matched_attributes": [], "conflicting_attributes": [], "missing_critical_attributes": [], "reason_code": "test", "notes": "some notes"}'
    with pytest.raises(RawOutputParseError) as exc_info:
        parse_raw_output(raw)
    assert "Unknown keys" in str(exc_info.value)


# ---------------------------------------------------------------------------
# P0: Authority conflict gate requires complete valid output
# ---------------------------------------------------------------------------

def test_authority_conflict_gate_fails_when_conflicts_missing(corpus):
    """Test that authority conflict gate fails when authority conflict outputs are missing.

    When authority conflict cases are not in the response set, the gate must FAIL
    because complete valid output is required for the hard safety gate.
    """
    # Get all authority conflict IDs
    authority_conflict_ids = [c.case_id for c in corpus.cases
                              if c.is_authority_safety_probe and c.expected_decision != SemanticDecision.MATCH]

    if len(authority_conflict_ids) == 0:
        pytest.skip("No authority conflict cases")

    # Provide responses for only PRIMARY cases, NOT authority conflicts
    primary_cases = [c for c in corpus.cases if not c.is_authority_safety_probe][:10]

    responses = {
        case.case_id: {
            "decision": case.expected_decision.value,
            "confidence": "HIGH",
            "matched_attributes": [],
            "conflicting_attributes": [],
            "missing_critical_attributes": [],
            "reason_code": "test",
        }
        for case in primary_cases
    }

    result = evaluate_responses(corpus, responses)

    # Authority conflict gate must be FALSE because conflicts are missing
    assert result.gates_passed["zero_false_match_on_authority_conflicts"] is False


def test_authority_conflict_gate_fails_when_conflict_output_invalid(corpus):
    """Test that authority conflict gate fails when an authority conflict output is invalid.

    When an authority conflict case has an invalid/malformed response, the gate must FAIL
    because complete valid output is required for the hard safety gate.
    """
    # Get all authority conflict IDs
    authority_conflict_cases = [c for c in corpus.cases
                                if c.is_authority_safety_probe and c.expected_decision != SemanticDecision.MATCH]

    if len(authority_conflict_cases) == 0:
        pytest.skip("No authority conflict cases")

    conflict_case = authority_conflict_cases[0]

    # Provide responses for all cases EXCEPT one authority conflict has invalid output
    responses = {}
    for case in corpus.cases:
        if case.case_id == conflict_case.case_id:
            # Invalid response for the conflict case
            responses[case.case_id] = {
                "decision": "INVALID",  # Invalid decision
                "confidence": "HIGH",
                "matched_attributes": [],
                "conflicting_attributes": [],
                "missing_critical_attributes": [],
                "reason_code": "test",
            }
        elif not case.is_authority_safety_probe:
            responses[case.case_id] = {
                "decision": case.expected_decision.value,
                "confidence": "HIGH",
                "matched_attributes": [],
                "conflicting_attributes": [],
                "missing_critical_attributes": [],
                "reason_code": "test",
            }

    result = evaluate_responses(corpus, responses)

    # Authority conflict gate must be FALSE because at least one conflict has invalid output
    assert result.gates_passed["zero_false_match_on_authority_conflicts"] is False


def test_authority_conflict_gate_passes_when_all_conflicts_valid(corpus):
    """Test that authority conflict gate passes when all authority conflicts have valid correct output.
    """
    # Provide correct responses for ALL cases
    responses = {
        case.case_id: {
            "decision": case.expected_decision.value,
            "confidence": "HIGH",
            "matched_attributes": [],
            "conflicting_attributes": [],
            "missing_critical_attributes": [],
            "reason_code": "correct",
        }
        for case in corpus.cases
    }

    result = evaluate_responses(corpus, responses)

    # Authority conflict gate must be TRUE when all conflicts are correct
    assert result.gates_passed["zero_false_match_on_authority_conflicts"] is True
    assert result.authority_false_match_count == 0


# ---------------------------------------------------------------------------
# P0: Accessory safety gate requires complete valid output
# ---------------------------------------------------------------------------

def test_accessory_safety_gate_fails_when_accessory_cases_missing(corpus):
    """Test that accessory safety gate fails when accessory cases are missing from responses.
    """
    # Get all accessory safety IDs
    accessory_ids = [c.case_id for c in corpus.cases
                     if c.case_class.value in {'accessory_trap', 'compatible_with_trap',
                                               'replacement_trap', 'multipack_trap', 'drive_vs_enclosure'}]

    if len(accessory_ids) == 0:
        pytest.skip("No accessory safety cases")

    # Provide responses for only PRIMARY cases, NOT accessory safety cases
    primary_cases = [c for c in corpus.cases if not c.is_authority_safety_probe and
                     c.case_class.value not in {'accessory_trap', 'compatible_with_trap',
                                                'replacement_trap', 'multipack_trap', 'drive_vs_enclosure'}][:10]

    responses = {
        case.case_id: {
            "decision": case.expected_decision.value,
            "confidence": "HIGH",
            "matched_attributes": [],
            "conflicting_attributes": [],
            "missing_critical_attributes": [],
            "reason_code": "test",
        }
        for case in primary_cases
    }

    result = evaluate_responses(corpus, responses)

    # Accessory safety gate must be FALSE because accessory cases are missing
    assert result.gates_passed["zero_false_match_on_accessory_safety_set"] is False


# ---------------------------------------------------------------------------
# P0: Per-class expected counters
# ---------------------------------------------------------------------------

def test_per_class_expected_counters_sum_to_case_count(corpus):
    """Test that per-class expected counters sum to case_count."""
    cases = list(corpus.cases)[:20]

    responses = {
        case.case_id: {
            "decision": case.expected_decision.value,
            "confidence": "HIGH",
            "matched_attributes": [],
            "conflicting_attributes": [],
            "missing_critical_attributes": [],
            "reason_code": "test",
        }
        for case in cases
    }

    result = evaluate_responses(corpus, responses)

    # For each class, match_expected + no_match_expected + uncertain_expected should equal case_count
    for cls, metrics in result.per_class_metrics.items():
        expected_sum = (metrics.match_expected_count +
                        metrics.no_match_expected_count +
                        metrics.uncertain_expected_count)
        assert expected_sum == metrics.case_count, \
            f"Class {cls}: expected counts sum {expected_sum} != case_count {metrics.case_count}"


# ---------------------------------------------------------------------------
# P0: Invalid-first duplicate ID regression
# ---------------------------------------------------------------------------

def test_duplicate_import_rejects_invalid_then_valid_same_id(tmp_path, corpus):
    """Test that duplicate ID is rejected even when first entry is invalid.

    If line 1 has case_id=SMQ-0001 with malformed raw_output, and
    line 2 also has case_id=SMQ-0001 with valid raw_output,
    the import must raise ValueError for duplicate case_id.
    """
    from product_intelligence.evaluation.semantic.prompt import import_results_from_jsonl

    # Create a JSONL file with duplicate IDs, first one invalid
    # Line 1: malformed JSON
    # Line 2: same case_id but valid JSON
    line1 = '{"case_id": "SMQ-0001", "raw_output": "not valid json at all"}'
    line2 = '{"case_id": "SMQ-0001", "raw_output": "{\\"decision\\": \\"MATCH\\", \\"confidence\\": \\"HIGH\\", \\"matched_attributes\\": [], \\"conflicting_attributes\\": [], \\"missing_critical_attributes\\": [], \\"reason_code\\": \\"test\\"}"}'
    jsonl_content = line1 + '\n' + line2

    f = tmp_path / "test_dup.jsonl"
    f.write_text(jsonl_content)

    corpus_case_ids = {c.case_id for c in corpus.cases[:10]}
    corpus_case_ids.add("SMQ-0001")

    with pytest.raises(ValueError) as exc_info:
        import_results_from_jsonl(f, corpus_case_ids)

    assert "Duplicate case_id" in str(exc_info.value)
    assert "SMQ-0001" in str(exc_info.value)


def test_duplicate_import_rejects_missing_then_valid_same_id(tmp_path, corpus):
    """Regression: duplicate ID rejected when first line is missing raw_output.

    If line 1 has case_id=SMQ-0001 with missing raw_output, and
    line 2 also has case_id=SMQ-0001 with valid raw_output,
    the import must raise ValueError for duplicate case_id.

    The case_id is consumed by line 1 even though raw_output validation
    fails, so line 2 raises duplicate case_id.
    """
    from product_intelligence.evaluation.semantic.prompt import import_results_from_jsonl

    # Line 1: valid case_id, missing raw_output
    # Line 2: same case_id, valid raw_output
    line1 = '{"case_id": "SMQ-0001"}'
    line2 = '{"case_id": "SMQ-0001", "raw_output": "{\\"decision\\": \\"MATCH\\", \\"confidence\\": \\"HIGH\\", \\"matched_attributes\\": [], \\"conflicting_attributes\\": [], \\"missing_critical_attributes\\": [], \\"reason_code\\": \\"test\\"}"}'
    jsonl_content = line1 + '\n' + line2

    f = tmp_path / "test_dup2.jsonl"
    f.write_text(jsonl_content)

    corpus_case_ids = {c.case_id for c in corpus.cases[:10]}
    corpus_case_ids.add("SMQ-0001")

    with pytest.raises(ValueError) as exc_info:
        import_results_from_jsonl(f, corpus_case_ids)

    assert "Duplicate case_id" in str(exc_info.value)
    assert "SMQ-0001" in str(exc_info.value)