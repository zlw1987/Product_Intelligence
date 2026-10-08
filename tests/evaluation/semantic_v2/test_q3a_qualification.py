"""Q3-A qualification decision tests.

Mandated properties 27-32 (ambiguous-case exclusion from hard
accuracy; no denominator reported as 100%; independent
primary/fallback qualification; incomplete model coverage cannot
PASS; policy pending cannot PASS; safety failure cannot be masked by
high aggregate accuracy) plus the metric structure and decision
precedence.
"""

from __future__ import annotations

import json

import pytest

from tests.evaluation.semantic_v2._q3a_helpers import (
    POLICY_PATH,
    load_corpus_bundle,
    primary_route,
    fallback_route,
    write_capture,
    write_approved_policy,
)
from product_intelligence.evaluation.semantic_v2.capture import (
    load_capture,
)
from product_intelligence.evaluation.semantic_v2.evaluator import (
    compute_metrics,
    evaluate_no_capture,
    evaluate_for_model,
)
from product_intelligence.evaluation.semantic_v2.gates import (
    decide,
    evaluate_safety_gates,
)
from product_intelligence.evaluation.semantic_v2.policy import (
    evaluate_thresholds,
    load_policy,
    policy_applies_to,
)


@pytest.fixture(scope="module")
def corpus():
    return load_corpus_bundle()


@pytest.fixture(scope="module")
def draft_policy():
    return load_policy(POLICY_PATH)


def _decide_for(corpus, capture, policy, route=None):
    route = route if route is not None else primary_route()
    result = evaluate_for_model(corpus, capture, *route)
    gates = evaluate_safety_gates(result)
    te = (
        evaluate_thresholds(policy, result.metrics)
        if policy is not None
        and policy_applies_to(policy, corpus.corpus_id, corpus.corpus_version)
        else None
    )
    decision, rationale = decide(result, gates, policy, te)
    return result, gates, decision, rationale


# ===========================================================================
# 27. Ambiguous-case exclusion from hard accuracy
# ===========================================================================


class TestAmbiguousExclusion:
    def test_ambiguous_cases_do_not_enter_the_hard_denominators(
        self, corpus, tmp_path
    ) -> None:
        path = write_capture(tmp_path / "c.json", corpus)
        result = evaluate_for_model(corpus, load_capture(path), *primary_route())
        m = result.metrics
        auth = m["counts"]["authoritative_evaluated"]
        amb = m["counts"]["ambiguous_evaluated"]
        total_eval = m["counts"]["evaluated_cases"]
        assert total_eval == auth + amb
        # Every hard metric denominator is an authoritative count.
        assert m["match_recall"]["denominator"] <= auth
        assert m["no_match_accuracy"]["denominator"] <= auth
        assert m["uncertain_rate"]["denominator"] == auth
        # The ambiguous surface is separate and visible.
        assert m["ambiguous"]["evaluated"] == amb == 7
        assert m["ambiguous"]["defensible"] == 7
        assert m["ambiguous"]["outside_defensible"] == 0

    def test_an_ambiguous_case_forced_to_match_is_not_silently_correct(
        self, corpus, tmp_path
    ) -> None:
        """A model MATCH on a case whose acceptable set excludes MATCH
        must be visible (OUTSIDE_DEFENSIBLE), not counted as a correct
        authoritative answer."""
        path = write_capture(
            tmp_path / "c.json",
            corpus,
            decisions={"V2Q-SSD-BRAND-CONTESTED-0040": "MATCH"},
        )
        result = evaluate_for_model(corpus, load_capture(path), *primary_route())
        m = result.metrics
        assert m["ambiguous"]["outside_defensible"] == 1
        example = m["ambiguous"]["outside_examples"][0]
        assert example["case_id"] == "V2Q-SSD-BRAND-CONTESTED-0040"
        assert example["severity"] == "HIGH"
        # And it is NOT in the authoritative false-match examples.
        ids = {
            e["case_id"] for e in m["false_match_examples"]
        }
        assert "V2Q-SSD-BRAND-CONTESTED-0040" not in ids


# ===========================================================================
# 28. No denominator reported as 100%
# ===========================================================================


class TestUnavailableDenominators:
    def test_zero_denominator_metrics_are_unavailable_not_100(
        self, corpus
    ) -> None:
        result = evaluate_no_capture(corpus, *primary_route())
        m = result.metrics
        for key in (
            "match_precision",
            "match_recall",
            "no_match_accuracy",
            "uncertain_rate",
            "valid_structured_response_rate",
        ):
            entry = m[key]
            assert entry["denominator"] == 0
            assert entry["value"] is None
            assert entry["status"] == "unavailable"
            assert entry["value"] != "1.000000"

    def test_unavailable_thresholds_are_never_met(
        self, corpus, tmp_path
    ) -> None:
        policy = load_policy(write_approved_policy(tmp_path, corpus))
        result = evaluate_no_capture(corpus, *primary_route())
        te = evaluate_thresholds(policy, result.metrics)
        # Ratio thresholds have no denominator: reported unavailable,
        # never met-by-default.
        for name in (
            "match_precision_min",
            "match_recall_min",
            "valid_structured_response_rate_min",
        ):
            assert te[name]["met"] is None, name
            assert te[name]["status"] == "unavailable", name
        # Coverage IS computable (0 evaluated of 43 eligible) and is
        # simply not met - never silently satisfied.
        assert te["eligible_coverage_min"]["met"] is False
        assert te["eligible_coverage_min"]["value"] == "0.000000"


# ===========================================================================
# 29. Independent primary/fallback qualification
# ===========================================================================


class TestPrimaryFallbackIndependence:
    def test_a_primary_pass_does_not_qualify_the_fallback(
        self, corpus, tmp_path
    ) -> None:
        """One run where the PRIMARY answered every case correctly:
        the primary view is fully covered (QUALIFIED with an approved
        policy); the SAME run projected onto the fallback model has NO
        fallback data (the primary's success finalized every case
        before the fallback was invoked) - the fallback cannot ride on
        the primary's PASS."""
        path = write_capture(tmp_path / "run.json", corpus)
        approved = load_policy(write_approved_policy(tmp_path, corpus))
        p_result, _p_gates, p_decision, _ = _decide_for(
            corpus, load_capture(path), approved, primary_route()
        )
        f_result, _f_gates, f_decision, f_rationale = _decide_for(
            corpus, load_capture(path), approved, fallback_route()
        )
        assert p_result.model == primary_route()[1]
        assert f_result.model == fallback_route()[1]
        assert p_decision == "QUALIFIED", p_decision
        assert f_decision == "INCOMPLETE_COVERAGE", f_decision
        assert f_result.metrics["counts"]["not_invoked"] == 43
        assert f_result.metrics["counts"]["evaluated_cases"] == 0
        assert any("not_invoked=43" in r for r in f_rationale)

    def test_the_fallback_is_qualified_on_its_own_answers(
        self, corpus, tmp_path
    ) -> None:
        """A run where the primary failed and the FALLBACK answered
        every case: the fallback view is fully covered; the primary
        view is all runtime failures (its own answers failed)."""
        path = write_capture(tmp_path / "run.json", corpus, execution="fallback")
        approved = load_policy(write_approved_policy(tmp_path, corpus))
        p_result, _p_gates, p_decision, _ = _decide_for(
            corpus, load_capture(path), approved, primary_route()
        )
        f_result, _f_gates, f_decision, _ = _decide_for(
            corpus, load_capture(path), approved, fallback_route()
        )
        assert f_decision == "QUALIFIED", f_decision
        assert f_result.metrics["counts"]["evaluated_cases"] == 43
        assert p_decision == "INCOMPLETE_COVERAGE"
        assert p_result.metrics["counts"]["runtime_failure_count"] == 43

    def test_a_fallback_error_does_not_taint_the_primary(
        self, corpus, tmp_path
    ) -> None:
        """Deliberate hard errors in the fallback's answers NOT_QUALIFY
        the fallback while the same run's primary view (all runtime
        failures) is separately incomplete - scores never cross models."""
        path = write_capture(
            tmp_path / "run.json",
            corpus,
            execution="fallback",
            decisions={"V2Q-SSD-ATTR-CAPACITY-0024": "MATCH"},
        )
        approved = load_policy(
            write_approved_policy(
                tmp_path,
                corpus,
                thresholds={
                    "match_precision_min": 0.0,
                    "match_recall_min": 0.0,
                    "valid_structured_response_rate_min": 0.0,
                    "eligible_coverage_min": 0.0,
                },
            )
        )
        f_result, f_gates, f_decision, _ = _decide_for(
            corpus, load_capture(path), approved, fallback_route()
        )
        p_result, _p_gates, p_decision, _ = _decide_for(
            corpus, load_capture(path), approved, primary_route()
        )
        assert f_decision == "NOT_QUALIFIED"
        assert not f_gates[
            "zero_false_match_on_always_hard_conflicts"
        ].passed
        assert f_result.metrics["false_match_count"] == 1
        assert p_decision == "INCOMPLETE_COVERAGE"
        assert p_result.metrics["false_match_count"] == 0

    def test_each_model_is_reported_with_its_own_route_role(
        self, corpus
    ) -> None:
        for route, role in (
            (primary_route(), "PRIMARY"),
            (fallback_route(), "FALLBACK"),
        ):
            result = evaluate_no_capture(corpus, *route)
            assert result.route_role == role
            assert (result.provider, result.model) == route

    def test_two_reports_never_share_case_scores(self, corpus, tmp_path) -> None:
        # Primary run: the primary answers S14 wrongly (false NO_MATCH);
        # fallback run: the fallback answers S14 correctly.
        p_path = write_capture(
            tmp_path / "p.json", corpus,
            decisions={"V2Q-DIMM-U4-MATCH-0014": "NO_MATCH"},
        )
        f_path = write_capture(
            tmp_path / "f.json", corpus, execution="fallback",
        )
        p_result = evaluate_for_model(
            corpus, load_capture(p_path), *primary_route()
        )
        f_result = evaluate_for_model(
            corpus, load_capture(f_path), *fallback_route()
        )
        p_o = next(
            o for o in p_result.outcomes
            if o.case_id == "V2Q-DIMM-U4-MATCH-0014"
        )
        f_o = next(
            o for o in f_result.outcomes
            if o.case_id == "V2Q-DIMM-U4-MATCH-0014"
        )
        assert p_o.verdict == "FALSE_NO_MATCH"
        assert f_o.verdict == "CORRECT"


# ===========================================================================
# 30. Incomplete model coverage cannot PASS
# ===========================================================================


class TestIncompleteCoverage:
    def test_partial_capture_cannot_qualify_with_an_approved_policy(
        self, corpus, tmp_path
    ) -> None:
        half = [
            c.case_id
            for c in corpus.semantic_cases[:20]
        ]
        path = write_capture(
            tmp_path / "c.json",
            corpus,
            include_all=False,
            decisions={
                cid: corpus.case(cid).expected["decision"] for cid in half
            },
        )
        approved = load_policy(write_approved_policy(tmp_path, corpus))
        _result, _gates, decision, rationale = _decide_for(
            corpus, load_capture(path), approved
        )
        assert decision == "INCOMPLETE_COVERAGE"
        assert any("not_captured=23" in r for r in rationale)
        assert "QUALIFIED" != decision

    def test_runtime_failures_block_qualification(
        self, corpus, tmp_path
    ) -> None:
        path = write_capture(
            tmp_path / "c.json",
            corpus,
            attempts_overrides={
                "V2Q-SSD-ATTR-CAPACITY-0024": [
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
        approved = load_policy(write_approved_policy(tmp_path, corpus))
        _result, _gates, decision, rationale = _decide_for(
            corpus, load_capture(path), approved
        )
        assert decision == "INCOMPLETE_COVERAGE"
        assert any("runtime_failures=1" in r for r in rationale)


# ===========================================================================
# 31. Policy pending cannot PASS
# ===========================================================================


class TestPolicyPending:
    def test_the_shipped_policy_is_draft(self) -> None:
        policy = load_policy(POLICY_PATH)
        assert policy.status == "DRAFT"
        assert policy.approved is False
        assert policy.approved_by is None

    def test_a_perfect_model_with_a_draft_policy_is_policy_pending(
        self, corpus, tmp_path
    ) -> None:
        path = write_capture(tmp_path / "c.json", corpus)
        draft = load_policy(POLICY_PATH)
        result, gates, decision, rationale = _decide_for(
            corpus, load_capture(path), draft
        )
        assert all(g.passed for g in gates.values())
        assert result.metrics["false_match_count"] == 0
        assert decision == "POLICY_PENDING"
        assert any("DRAFT" in r for r in rationale)
        assert decision != "QUALIFIED"

    def test_no_policy_at_all_is_policy_pending(self, corpus, tmp_path) -> None:
        path = write_capture(tmp_path / "c.json", corpus)
        _result, _gates, decision, rationale = _decide_for(
            corpus, load_capture(path), None
        )
        assert decision == "POLICY_PENDING"
        assert any("no approved applicable policy" in r for r in rationale)

    def test_a_policy_for_a_different_corpus_is_policy_pending(
        self, corpus, tmp_path
    ) -> None:
        foreign_policy_path = tmp_path / "foreign.json"
        policy_doc = json.loads(POLICY_PATH.read_text(encoding="utf-8"))
        policy_doc["applicability"]["corpus_version"] = "9.9.9"
        foreign_policy_path.write_text(
            json.dumps(policy_doc), encoding="utf-8"
        )
        policy = load_policy(foreign_policy_path)
        path = write_capture(tmp_path / "c.json", corpus)
        _result, _gates, decision, rationale = _decide_for(
            corpus, load_capture(path), policy
        )
        assert decision == "POLICY_PENDING"

    def test_an_approved_policy_can_qualify_a_perfect_model(
        self, corpus, tmp_path
    ) -> None:
        """Mechanism proof (test scope): with an APPROVED policy and a
        fully correct capture, the decision machinery reaches
        QUALIFIED. This does not approve any production threshold."""
        path = write_capture(tmp_path / "c.json", corpus)
        approved = load_policy(write_approved_policy(tmp_path, corpus))
        result, gates, decision, rationale = _decide_for(
            corpus, load_capture(path), approved
        )
        assert decision == "QUALIFIED"
        assert all(g.passed for g in gates.values())
        assert result.metrics["match_precision"]["value"] == "1.000000"


# ===========================================================================
# 32. Safety failure cannot be masked by high aggregate accuracy
# ===========================================================================


class TestSafetyNotMasked:
    def test_one_critical_false_match_beats_perfect_aggregates(
        self, corpus, tmp_path
    ) -> None:
        # 42/43 correct, 1 CRITICAL hard-conflict false MATCH: aggregate
        # accuracy is ~97.7% but the decision must be NOT_QUALIFIED.
        path = write_capture(
            tmp_path / "c.json",
            corpus,
            decisions={"V2Q-SSD-ATTR-CAPACITY-0024": "MATCH"},
        )
        approved = load_policy(
            write_approved_policy(
                tmp_path,
                corpus,
                thresholds={
                    "match_precision_min": 0.0,
                    "match_recall_min": 0.0,
                    "valid_structured_response_rate_min": 0.0,
                    "eligible_coverage_min": 0.0,
                },
            )
        )
        result, gates, decision, rationale = _decide_for(
            corpus, load_capture(path), approved
        )
        assert decision == "NOT_QUALIFIED"
        assert not gates[
            "zero_false_match_on_always_hard_conflicts"
        ].passed
        assert any(
            r.startswith("SAFETY_GATE_FAILED") for r in rationale
        )
        # The safety failure stays visible in the metrics too.
        assert result.metrics["hard_conflict_false_match_count"] == 1

    def test_safety_failure_with_a_draft_policy_stays_not_qualified(
        self, corpus, tmp_path
    ) -> None:
        path = write_capture(
            tmp_path / "c.json",
            corpus,
            decisions={"V2Q-SSD-SU-TRAY-0032": "MATCH"},
        )
        draft = load_policy(POLICY_PATH)
        _result, gates, decision, rationale = _decide_for(
            corpus, load_capture(path), draft
        )
        assert decision == "NOT_QUALIFIED"
        assert not gates[
            "zero_false_match_on_packaging_quantity_conflicts"
        ].passed
        assert any(
            r.startswith("SAFETY_GATE_FAILED") for r in rationale
        )


# ===========================================================================
# Metric structure / decision precedence
# ===========================================================================


class TestMetricStructure:
    def test_every_metric_entry_is_bounded(self, corpus, tmp_path) -> None:
        path = write_capture(tmp_path / "c.json", corpus)
        result = evaluate_for_model(corpus, load_capture(path), *primary_route())
        m = result.metrics
        for key in (
            "match_precision",
            "match_recall",
            "no_match_accuracy",
            "uncertain_rate",
            "valid_structured_response_rate",
        ):
            entry = m[key]
            assert set(entry) == {
                "numerator",
                "denominator",
                "value",
                "status",
            }
            assert entry["status"] in {"computed", "unavailable"}

    def test_runtime_and_semantic_errors_are_separate_surfaces(
        self, corpus, tmp_path
    ) -> None:
        path = write_capture(
            tmp_path / "c.json",
            corpus,
            attempts_overrides={
                "V2Q-SSD-ATTR-CAPACITY-0024": [
                    {
                        "role": "PRIMARY",
                        "provider": "amax",
                        "model": "qwen3.8-27b",
                        "status": "TIMEOUT",
                        "raw_output": None,
                    }
                ]
            },
            decisions={"V2Q-DIMM-U4-MATCH-0014": "MATCH"},
        )
        result = evaluate_for_model(corpus, load_capture(path), *primary_route())
        m = result.metrics
        assert m["counts"]["runtime_failure_count"] == 1
        assert m["false_match_count"] == 0
        assert m["false_no_match_count"] == 0
        # The runtime failure is not hidden inside any accuracy number:
        # the valid-response rate denominator sees it.
        assert (
            m["valid_structured_response_rate"]["numerator"]
            == m["valid_structured_response_rate"]["denominator"] - 1
        )

    def test_decision_precedence_safety_beats_policy(
        self, corpus, tmp_path
    ) -> None:
        """Even with a DRAFT policy (which alone would say
        POLICY_PENDING), a safety failure says NOT_QUALIFIED."""
        path = write_capture(
            tmp_path / "c.json",
            corpus,
            decisions={"V2Q-SSD-ACC-CADDY-0031": "MATCH"},
        )
        draft = load_policy(POLICY_PATH)
        _result, gates, decision, _ = _decide_for(
            corpus, load_capture(path), draft
        )
        assert decision == "NOT_QUALIFIED"
        assert not gates[
            "zero_false_match_on_accessory_product_role_conflicts"
        ].passed

    def test_the_no_capture_baseline_decision_is_fail_closed(
        self, corpus, draft_policy
    ) -> None:
        for route in (primary_route(), fallback_route()):
            result = evaluate_no_capture(corpus, *route)
            gates = evaluate_safety_gates(result)
            te = evaluate_thresholds(
                draft_policy, result.metrics
            ) if policy_applies_to(
                draft_policy, corpus.corpus_id, corpus.corpus_version
            ) else None
            decision, rationale = decide(
                result, gates, draft_policy, te
            )
            assert decision == "POLICY_PENDING"
            assert any(
                "not_captured=43" in r for r in rationale
            ), rationale
            assert decision not in {"QUALIFIED", "BELOW_THRESHOLD"}
