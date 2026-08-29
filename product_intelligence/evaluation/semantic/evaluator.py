"""Semantic match evaluator (PRODUCT-INTEL.SEMANTIC).

This module computes evaluation metrics for semantic match models.
It is used for offline qualification without any live model integration.

No network or API calls are made. All evaluation is against recorded responses.

Single source of truth (FU3A2)
------------------------------
``parse_raw_output``, ``validate_response`` and ``RawOutputParseError`` are
NOT defined here. They are re-exported from the neutral production contract
``product_intelligence.semantic.contract`` so evaluation and production apply
the *same* parsing and validation objects. Only evaluator mathematics is
defined locally.
"""

from __future__ import annotations

from collections import Counter, defaultdict
from dataclasses import dataclass, field
from typing import Any

from product_intelligence.evaluation.semantic.loader import (
    SemanticMatchCase,
    SemanticCorpus,
    SemanticMatchResponse,
)
from product_intelligence.evaluation.semantic.vocabulary import (
    ConfidenceLevel,
    SemanticCaseClass,
    SemanticDecision,
)

# Canonical contract objects - re-exported, never re-implemented.
from product_intelligence.semantic.contract import (
    RawOutputParseError,
    parse_raw_output,
    validate_response,
)


# ---------------------------------------------------------------------------
# Metrics data structures
# ---------------------------------------------------------------------------


@dataclass
class ConfusionMatrix:
    """3x3 confusion matrix for semantic decisions.

    Rows = actual decision, Columns = predicted decision.
    M_M = actual MATCH, predicted MATCH (true positive)
    M_N = actual MATCH, predicted NO_MATCH
    M_U = actual MATCH, predicted UNCERTAIN
    N_M = actual NO_MATCH, predicted MATCH (false positive)
    N_N = actual NO_MATCH, predicted NO_MATCH (true negative)
    N_U = actual NO_MATCH, predicted UNCERTAIN
    U_M = actual UNCERTAIN, predicted MATCH (false positive)
    U_N = actual UNCERTAIN, predicted NO_MATCH
    U_U = actual UNCERTAIN, predicted UNCERTAIN (true positive)
    """

    # Actual MATCH row
    match_to_match: int = 0
    match_to_no_match: int = 0
    match_to_uncertain: int = 0
    # Actual NO_MATCH row
    no_match_to_match: int = 0
    no_match_to_no_match: int = 0
    no_match_to_uncertain: int = 0
    # Actual UNCERTAIN row
    uncertain_to_match: int = 0
    uncertain_to_no_match: int = 0
    uncertain_to_uncertain: int = 0

    @property
    def total(self) -> int:
        """Total cases in confusion matrix (excludes missing/invalid)."""
        return (
            self.match_to_match + self.match_to_no_match + self.match_to_uncertain +
            self.no_match_to_match + self.no_match_to_no_match + self.no_match_to_uncertain +
            self.uncertain_to_match + self.uncertain_to_no_match + self.uncertain_to_uncertain
        )

    @property
    def M_M(self) -> int:
        return self.match_to_match

    @property
    def M_N(self) -> int:
        return self.match_to_no_match

    @property
    def M_U(self) -> int:
        return self.match_to_uncertain

    @property
    def N_M(self) -> int:
        return self.no_match_to_match

    @property
    def N_N(self) -> int:
        return self.no_match_to_no_match

    @property
    def N_U(self) -> int:
        return self.no_match_to_uncertain

    @property
    def U_M(self) -> int:
        return self.uncertain_to_match

    @property
    def U_N(self) -> int:
        return self.uncertain_to_no_match

    @property
    def U_U(self) -> int:
        return self.uncertain_to_uncertain


@dataclass
class PerClassMetrics:
    """Metrics for one SemanticCaseClass."""

    case_count: int = 0
    valid_count: int = 0
    correct: int = 0
    false_match_count: int = 0

    # Predicted decision counts (for reporting)
    predicted_match_count: int = 0
    predicted_no_match_count: int = 0
    predicted_uncertain_count: int = 0

    # Expected decision counts (for reporting)
    match_expected_count: int = 0
    no_match_expected_count: int = 0
    uncertain_expected_count: int = 0

    @property
    def accuracy(self) -> float:
        if self.valid_count == 0:
            return 0.0
        return self.correct / self.valid_count


@dataclass
class EvaluationResult:
    """Complete evaluation result."""

    # Corpus-level counts
    total_corpus_cases: int
    valid_response_count: int
    invalid_or_missing_count: int

    # Full corpus rate metrics
    valid_output_rate: float

    # Full corpus decision accuracy
    decision_accuracy: float

    # MATCH metrics
    match_precision: float
    match_recall: float
    false_match_count: int
    false_match_rate: float

    # NO_MATCH metrics
    no_match_precision: float
    no_match_recall: float

    # UNCERTAIN metrics
    uncertain_precision: float
    uncertain_recall: float

    # Confusion matrix
    confusion_matrix: ConfusionMatrix

    # Per-class metrics
    per_class_metrics: dict[SemanticCaseClass, PerClassMetrics]

    # Safety cost (lower is better)
    safety_cost: float

    # Authority safety probe results
    authority_safety_probes_passed: bool
    authority_false_match_count: int

    # Accessory safety set results
    accessory_safety_set_false_match_count: int

    # PRIMARY-only headline metrics
    primary_valid_response_count: int
    primary_valid_output_rate: float
    primary_decision_accuracy: float
    primary_match_precision: float
    primary_match_recall: float
    primary_false_match_count: int
    primary_false_match_rate: float
    primary_safety_cost: float

    # Primary confusion matrix (for verification)
    primary_confusion_matrix: ConfusionMatrix

    # Qualification gates
    gates_passed: dict[str, bool]


# ---------------------------------------------------------------------------
# Raw output parser / response validator
# ---------------------------------------------------------------------------
#
# ``RawOutputParseError``, ``parse_raw_output`` and ``validate_response`` are
# imported above from ``product_intelligence.semantic.contract``. They are the
# canonical implementations; this module deliberately keeps no copy of them.


def _compute_metrics_from_cm(cm: ConfusionMatrix) -> tuple[float, float, float, int, float, float, float, float, float, float]:
    """Compute all metrics exclusively from a confusion matrix.

    Returns:
        (decision_accuracy, match_precision, match_recall, false_match_count,
         false_match_rate, no_match_precision, no_match_recall,
         uncertain_precision, uncertain_recall, safety_cost)
    """
    mt = cm.total
    if mt == 0:
        return (0.0,) * 10

    M_M, M_N, M_U = cm.M_M, cm.M_N, cm.M_U
    N_M, N_N, N_U = cm.N_M, cm.N_N, cm.N_U
    U_M, U_N, U_U = cm.U_M, cm.U_N, cm.U_U

    # Decision accuracy = (M_M + N_N + U_U) / total
    decision_accuracy = (M_M + N_N + U_U) / mt

    # MATCH precision = M_M / (M_M + N_M + U_M)
    match_prec_denom = M_M + N_M + U_M
    match_precision = M_M / match_prec_denom if match_prec_denom > 0 else 0.0

    # MATCH recall = M_M / (M_M + M_N + M_U)
    match_recall_denom = M_M + M_N + M_U
    match_recall = M_M / match_recall_denom if match_recall_denom > 0 else 0.0

    # False MATCH count = N_M + U_M
    false_match_count = N_M + U_M

    # False MATCH rate = (N_M + U_M) / (N_M + N_N + N_U + U_M + U_N + U_U)
    non_match_actual = N_M + N_N + N_U + U_M + U_N + U_U
    false_match_rate = false_match_count / non_match_actual if non_match_actual > 0 else 0.0

    # NO_MATCH precision = N_N / (M_N + N_N + U_N)
    nm_prec_denom = M_N + N_N + U_N
    no_match_precision = N_N / nm_prec_denom if nm_prec_denom > 0 else 0.0

    # NO_MATCH recall = N_N / (N_M + N_N + N_U)
    nm_recall_denom = N_M + N_N + N_U
    no_match_recall = N_N / nm_recall_denom if nm_recall_denom > 0 else 0.0

    # UNCERTAIN precision = U_U / (M_U + N_U + U_U)
    unc_prec_denom = M_U + N_U + U_U
    uncertain_precision = U_U / unc_prec_denom if unc_prec_denom > 0 else 0.0

    # UNCERTAIN recall = U_U / (U_M + U_N + U_U)
    unc_recall_denom = U_M + U_N + U_U
    uncertain_recall = U_U / unc_recall_denom if unc_recall_denom > 0 else 0.0

    # Safety cost = 10*(N_M + U_M) + 1*(M_N + M_U + N_U + U_N)
    safety_cost = 10 * (N_M + U_M) + (M_N + M_U + N_U + U_N)

    return (
        decision_accuracy, match_precision, match_recall, false_match_count,
        false_match_rate, no_match_precision, no_match_recall,
        uncertain_precision, uncertain_recall, safety_cost
    )


# ---------------------------------------------------------------------------
# Accessory safety set definition
# ---------------------------------------------------------------------------

ACCESSORY_SAFETY_CLASSES = frozenset([
    'accessory_trap',
    'compatible_with_trap',
    'replacement_trap',
    'multipack_trap',
    'drive_vs_enclosure',
])


# ---------------------------------------------------------------------------
# Evaluator
# ---------------------------------------------------------------------------


class SemanticEvaluator:
    """Evaluate semantic match model responses against ground truth."""

    def __init__(self, corpus: SemanticCorpus):
        """Initialize with a loaded corpus."""
        self.corpus = corpus
        self._results: list[EvaluationResult] = []

        # Pre-compute case sets
        self._authority_probe_ids: set[str] = set()
        self._authority_conflict_ids: set[str] = set()  # authority probes where expected != MATCH
        self._accessory_safety_ids: set[str] = set()
        self._primary_case_ids: set[str] = set()

        for case in corpus.cases:
            if case.is_authority_safety_probe:
                self._authority_probe_ids.add(case.case_id)
                # Authority conflicts are authority probes where expected != MATCH
                if case.expected_decision != SemanticDecision.MATCH:
                    self._authority_conflict_ids.add(case.case_id)
            else:
                self._primary_case_ids.add(case.case_id)
                if case.case_class.value in ACCESSORY_SAFETY_CLASSES:
                    self._accessory_safety_ids.add(case.case_id)

    def evaluate(
        self,
        responses: dict[str, dict[str, Any] | SemanticMatchResponse],
    ) -> EvaluationResult:
        """Evaluate model responses against corpus ground truth.

        Args:
            responses: Dict mapping case_id to model response (raw dict, parsed dict, or validated)

        Returns:
            EvaluationResult with all metrics.

        Raises:
            ValueError: If any response case_id is not in the corpus.
        """
        # Corpus case IDs - build this first for unknown ID check
        corpus_case_ids = {c.case_id for c in self.corpus.cases}

        # Check for unknown response IDs BEFORE processing
        unknown_ids = set(responses.keys()) - corpus_case_ids
        if unknown_ids:
            raise ValueError(f"Unknown case IDs in responses: {sorted(unknown_ids)}")

        # Validate responses and separate valid/invalid
        valid_response_ids: set[str] = set()
        invalid_response_ids: set[str] = set()
        for case_id, response in responses.items():
            try:
                validate_response(response)
                valid_response_ids.add(case_id)
            except (ValueError, TypeError):
                invalid_response_ids.add(case_id)

        # Corpus case IDs
        corpus_case_ids = {c.case_id for c in self.corpus.cases}

        # Total counts
        total_corpus_cases = len(self.corpus.cases)

        # Valid responses for corpus cases
        response_ids_in_corpus = valid_response_ids & corpus_case_ids
        valid_response_count = len(response_ids_in_corpus)

        # Invalid responses for corpus cases
        invalid_for_corpus = invalid_response_ids & corpus_case_ids

        # Missing = corpus cases without any response
        missing_case_ids = corpus_case_ids - valid_response_ids - invalid_response_ids
        invalid_or_missing_count = len(missing_case_ids) + len(invalid_for_corpus)

        # valid_output_rate = valid corpus responses / total corpus cases
        valid_output_rate = valid_response_count / total_corpus_cases if total_corpus_cases > 0 else 0.0

        # =================================================================
        # Build confusion matrices
        # =================================================================

        # Full corpus confusion matrix
        cm = ConfusionMatrix()

        # Primary-only confusion matrix
        primary_cm = ConfusionMatrix()

        # Authority safety probe tracking
        authority_false_match_count = 0

        # Accessory safety set tracking
        accessory_false_match_count = 0

        # Per-class metrics
        per_class_data: dict[SemanticCaseClass, PerClassMetrics] = {}
        for case in self.corpus.cases:
            if case.case_class not in per_class_data:
                per_class_data[case.case_class] = PerClassMetrics()
            per_class_data[case.case_class].case_count += 1
            # Track expected decision distribution
            if case.expected_decision == SemanticDecision.MATCH:
                per_class_data[case.case_class].match_expected_count += 1
            elif case.expected_decision == SemanticDecision.NO_MATCH:
                per_class_data[case.case_class].no_match_expected_count += 1
            else:
                per_class_data[case.case_class].uncertain_expected_count += 1

        # Process each case
        for case in self.corpus.cases:
            case_id = case.case_id
            expected = case.expected_decision
            is_authority_probe = case.is_authority_safety_probe
            is_primary = not is_authority_probe
            is_accessory = case_id in self._accessory_safety_ids

            if case_id not in valid_response_ids:
                # Missing/invalid response - NOT a prediction
                # Count as invalid for coverage only, does NOT affect confusion matrix
                continue

            predicted = validate_response(responses[case_id]).decision

            # Update per-class predicted counts
            cls = case.case_class
            per_class_data[cls].valid_count += 1
            if predicted == SemanticDecision.MATCH:
                per_class_data[cls].predicted_match_count += 1
            elif predicted == SemanticDecision.NO_MATCH:
                per_class_data[cls].predicted_no_match_count += 1
            else:
                per_class_data[cls].predicted_uncertain_count += 1

            # Update confusion matrices
            if expected == SemanticDecision.MATCH:
                if predicted == SemanticDecision.MATCH:
                    cm.match_to_match += 1
                    per_class_data[cls].correct += 1
                elif predicted == SemanticDecision.NO_MATCH:
                    cm.match_to_no_match += 1
                else:
                    cm.match_to_uncertain += 1
            elif expected == SemanticDecision.NO_MATCH:
                if predicted == SemanticDecision.MATCH:
                    cm.no_match_to_match += 1
                    per_class_data[cls].false_match_count += 1
                    if is_authority_probe:
                        authority_false_match_count += 1
                    if is_accessory:
                        accessory_false_match_count += 1
                elif predicted == SemanticDecision.NO_MATCH:
                    cm.no_match_to_no_match += 1
                    per_class_data[cls].correct += 1
                else:
                    cm.no_match_to_uncertain += 1
            else:  # UNCERTAIN
                if predicted == SemanticDecision.MATCH:
                    cm.uncertain_to_match += 1
                    per_class_data[cls].false_match_count += 1
                    if is_accessory:
                        accessory_false_match_count += 1
                elif predicted == SemanticDecision.NO_MATCH:
                    cm.uncertain_to_no_match += 1
                else:
                    cm.uncertain_to_uncertain += 1
                    per_class_data[cls].correct += 1

            # Primary-only confusion matrix (only primary cases)
            if is_primary:
                if expected == SemanticDecision.MATCH:
                    if predicted == SemanticDecision.MATCH:
                        primary_cm.match_to_match += 1
                    elif predicted == SemanticDecision.NO_MATCH:
                        primary_cm.match_to_no_match += 1
                    else:
                        primary_cm.match_to_uncertain += 1
                elif expected == SemanticDecision.NO_MATCH:
                    if predicted == SemanticDecision.MATCH:
                        primary_cm.no_match_to_match += 1
                    elif predicted == SemanticDecision.NO_MATCH:
                        primary_cm.no_match_to_no_match += 1
                    else:
                        primary_cm.no_match_to_uncertain += 1
                else:  # UNCERTAIN
                    if predicted == SemanticDecision.MATCH:
                        primary_cm.uncertain_to_match += 1
                    elif predicted == SemanticDecision.NO_MATCH:
                        primary_cm.uncertain_to_no_match += 1
                    else:
                        primary_cm.uncertain_to_uncertain += 1

        # =================================================================
        # Compute metrics exclusively from confusion matrices
        # =================================================================

        # Full corpus metrics
        (
            decision_accuracy, match_precision, match_recall, false_match_count,
            false_match_rate, no_match_precision, no_match_recall,
            uncertain_precision, uncertain_recall, safety_cost
        ) = _compute_metrics_from_cm(cm)

        # Primary-only metrics
        (
            primary_decision_accuracy, primary_match_precision, primary_match_recall,
            primary_false_match_count, primary_false_match_rate, _,
            _, _, _, primary_safety_cost
        ) = _compute_metrics_from_cm(primary_cm)

        # Primary valid response count (from primary case IDs)
        primary_response_ids = response_ids_in_corpus & self._primary_case_ids
        primary_valid_response_count = len(primary_response_ids)
        primary_valid_output_rate = (
            primary_valid_response_count / len(self._primary_case_ids)
            if self._primary_case_ids else 0.0
        )

        # =================================================================
        # Gates
        # =================================================================

        # Authority conflict gate: requires ALL authority_conflict_ids to have
        # valid responses AND zero false MATCH on them
        authority_conflict_valid_responses = self._authority_conflict_ids & valid_response_ids
        authority_conflict_missing_or_invalid = (
            len(self._authority_conflict_ids) > 0 and
            authority_conflict_valid_responses != self._authority_conflict_ids
        )
        authority_safety_probes_passed = (
            not authority_conflict_missing_or_invalid and
            authority_false_match_count == 0
        )

        # Accessory safety gate: requires ALL accessory_safety_ids to have
        # valid responses AND zero false MATCH on them
        accessory_valid_responses = self._accessory_safety_ids & valid_response_ids
        accessory_missing_or_invalid = (
            len(self._accessory_safety_ids) > 0 and
            accessory_valid_responses != self._accessory_safety_ids
        )
        accessory_gate_passed = (
            not accessory_missing_or_invalid and
            accessory_false_match_count == 0
        )

        gates_passed = {
            "zero_false_match_on_authority_conflicts": authority_safety_probes_passed,
            "zero_false_match_on_accessory_safety_set": accessory_gate_passed,
            "primary_valid_output_rate_sufficient": primary_valid_output_rate >= 0.99,
            "primary_match_precision_sufficient": primary_match_precision >= 0.98,
            "primary_overall_accuracy_target": primary_decision_accuracy >= 0.90,
        }

        result = EvaluationResult(
            total_corpus_cases=total_corpus_cases,
            valid_response_count=valid_response_count,
            invalid_or_missing_count=invalid_or_missing_count,
            valid_output_rate=valid_output_rate,
            decision_accuracy=decision_accuracy,
            match_precision=match_precision,
            match_recall=match_recall,
            false_match_count=false_match_count,
            false_match_rate=false_match_rate,
            no_match_precision=no_match_precision,
            no_match_recall=no_match_recall,
            uncertain_precision=uncertain_precision,
            uncertain_recall=uncertain_recall,
            confusion_matrix=cm,
            per_class_metrics=per_class_data,
            safety_cost=safety_cost,
            authority_safety_probes_passed=authority_safety_probes_passed,
            authority_false_match_count=authority_false_match_count,
            accessory_safety_set_false_match_count=accessory_false_match_count,
            primary_valid_response_count=primary_valid_response_count,
            primary_valid_output_rate=primary_valid_output_rate,
            primary_decision_accuracy=primary_decision_accuracy,
            primary_match_precision=primary_match_precision,
            primary_match_recall=primary_match_recall,
            primary_false_match_count=primary_false_match_count,
            primary_false_match_rate=primary_false_match_rate,
            primary_safety_cost=primary_safety_cost,
            primary_confusion_matrix=primary_cm,
            gates_passed=gates_passed,
        )

        self._results.append(result)
        return result

    def get_last_result(self) -> EvaluationResult:
        """Get the last evaluation result."""
        if not self._results:
            raise IndexError("No evaluation results available")
        return self._results[-1]


def evaluate_responses(
    corpus: SemanticCorpus,
    responses: dict[str, dict[str, Any] | SemanticMatchResponse],
) -> EvaluationResult:
    """Convenience function to evaluate responses against corpus."""
    evaluator = SemanticEvaluator(corpus)
    return evaluator.evaluate(responses)


# ---------------------------------------------------------------------------
# Corpus summary generation
# ---------------------------------------------------------------------------


def compute_corpus_distribution(corpus: SemanticCorpus) -> dict[str, Any]:
    """Compute actual distribution statistics from corpus."""
    total = len(corpus.cases)

    decision_counts = Counter(c.expected_decision for c in corpus.cases)
    class_counts = Counter(c.case_class for c in corpus.cases)
    evidence_source_counts = Counter(c.candidate_evidence_source for c in corpus.cases)
    provenance_counts = Counter(c.provenance for c in corpus.cases)

    authority_probe_count = sum(1 for c in corpus.cases if c.is_authority_safety_probe)
    primary_semantic_count = sum(
        1 for c in corpus.cases
        if c.candidate_evidence_source != "EXPLICIT_MPN_FIELD"
        and not c.is_authority_safety_probe
    )

    return {
        "total_cases": total,
        "by_decision": {
            "MATCH": decision_counts.get(SemanticDecision.MATCH, 0),
            "NO_MATCH": decision_counts.get(SemanticDecision.NO_MATCH, 0),
            "UNCERTAIN": decision_counts.get(SemanticDecision.UNCERTAIN, 0),
        },
        "by_case_class": {cls.value: count for cls, count in class_counts.items()},
        "by_evidence_source": dict(evidence_source_counts),
        "by_provenance": dict(provenance_counts),
        "authority_safety_probes": authority_probe_count,
        "primary_semantic_cases": primary_semantic_count,
    }