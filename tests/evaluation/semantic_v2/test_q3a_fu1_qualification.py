"""Q3-A-FU1 qualification decision tests.

Mandated properties 19-20, 22, 24, 30-32: primary qualification does
not qualify the fallback; fallback qualification does not qualify the
primary; production-route coverage retains NOT_INVOKED (the two modes'
denominators are never mixed); false-MATCH safety gates work identically
in both modes; the qualification policy remains DRAFT (no QUALIFIED
under the unapproved policy); V2_AUTHORITY_QUALIFIED remains False; no
Machine Price, Reviewed Price, or human-review authority change.
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
    make_response,
)
from tests.evaluation.semantic_v2._q3a_fu1_helpers import (
    direct_decide_for,
    write_direct_capture,
)
from product_intelligence.evaluation.semantic_v2.capture import (
    load_capture,
)
from product_intelligence.evaluation.semantic_v2.direct_capture import (
    load_direct_capture,
)
from product_intelligence.evaluation.semantic_v2.evaluator import (
    QualificationContractError,
    evaluate_direct_for_model,
    evaluate_for_model,
    evaluate_no_capture,
)
from product_intelligence.evaluation.semantic_v2.gates import (
    HARD_SAFETY_GATES,
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
    """The shipped policy artifact: DRAFT, unapproved. Never qualified
    under it - in either mode."""
    return load_policy(POLICY_PATH)


CAPACITY_CASE = "V2Q-SSD-ATTR-CAPACITY-0024"
ALIAS_CASE = "V2Q-SSD-U5NM1-ALIAS-0022"


def _production_decide_for(corpus, capture, policy, route):
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
# 19-20. Independent direct-model qualification (no data crossing)
# ===========================================================================


class TestIndependentDirectQualification:
    def test_primary_qualification_does_not_qualify_the_fallback(
        self, corpus, tmp_path
    ) -> None:
        """A fully correct DIRECT primary capture qualifies the primary
        (decision mechanism, test-scope approved policy); the fallback
        gets NOTHING from it: evaluating the primary capture as the
        fallback fails closed, and the fallback's own no-capture state
        is INCOMPLETE_COVERAGE - never QUALIFIED."""
        path = write_direct_capture(tmp_path / "p.json", corpus)
        approved = load_policy(write_approved_policy(tmp_path, corpus))
        _r, _g, decision, _ = direct_decide_for(
            corpus, load_direct_capture(path), approved
        )
        assert decision == "QUALIFIED", decision

        # No data crossing: the primary capture is not the fallback's
        # data.
        with pytest.raises(QualificationContractError, match="bound to"):
            evaluate_direct_for_model(
                corpus, load_direct_capture(path), *fallback_route()
            )
        # The fallback's own state (no capture of its own): incomplete.
        f_result = evaluate_no_capture(corpus, *fallback_route())
        f_gates = evaluate_safety_gates(f_result)
        f_te = evaluate_thresholds(approved, f_result.metrics)
        f_decision, _ = decide(f_result, f_gates, approved, f_te)
        assert f_decision == "INCOMPLETE_COVERAGE", f_decision

    def test_fallback_qualification_does_not_qualify_the_primary(
        self, corpus, tmp_path
    ) -> None:
        """The mirror: a fully correct DIRECT fallback capture
        qualifies the fallback; the primary gets nothing from it."""
        path = write_direct_capture(
            tmp_path / "f.json", corpus, target=fallback_route()
        )
        approved = load_policy(write_approved_policy(tmp_path, corpus))
        _r, _g, decision, _ = direct_decide_for(
            corpus, load_direct_capture(path), approved
        )
        assert decision == "QUALIFIED", decision

        with pytest.raises(QualificationContractError, match="bound to"):
            evaluate_direct_for_model(
                corpus, load_direct_capture(path), *primary_route()
            )
        p_result = evaluate_no_capture(corpus, *primary_route())
        p_gates = evaluate_safety_gates(p_result)
        p_te = evaluate_thresholds(approved, p_result.metrics)
        p_decision, _ = decide(p_result, p_gates, approved, p_te)
        assert p_decision == "INCOMPLETE_COVERAGE", p_decision

    def test_both_models_qualify_independently_on_their_own_captures(
        self, corpus, tmp_path
    ) -> None:
        """Two separate direct captures (one per pinned model, distinct
        run ids) each fully qualify their own model - no production
        run, no manufactured primary failure, no shared data."""
        p_path = write_direct_capture(
            tmp_path / "p.json", corpus, capture_run_id="DIRECT-P-1"
        )
        f_path = write_direct_capture(
            tmp_path / "f.json",
            corpus,
            target=fallback_route(),
            capture_run_id="DIRECT-F-1",
        )
        approved = load_policy(write_approved_policy(tmp_path, corpus))
        p_result, p_gates, p_decision, _ = direct_decide_for(
            corpus, load_direct_capture(p_path), approved
        )
        f_result, f_gates, f_decision, _ = direct_decide_for(
            corpus, load_direct_capture(f_path), approved
        )
        assert p_decision == "QUALIFIED"
        assert f_decision == "QUALIFIED"
        assert p_result.provider == primary_route()[0]
        assert f_result.provider == fallback_route()[0]
        assert all(g.passed for g in p_gates.values())
        assert all(g.passed for g in f_gates.values())

    def test_incomplete_direct_coverage_cannot_qualify(
        self, corpus, tmp_path
    ) -> None:
        """Every eligible semantic case needs an accepted, parser-valid
        response: one missing record (or one runtime failure) keeps the
        decision at INCOMPLETE_COVERAGE even under an approved policy
        with zero thresholds."""
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
        missing = write_direct_capture(
            tmp_path / "m.json", corpus, missing=(CAPACITY_CASE,)
        )
        _r, _g, d_missing, _ = direct_decide_for(
            corpus, load_direct_capture(missing), approved
        )
        assert d_missing == "INCOMPLETE_COVERAGE", d_missing
        failed = write_direct_capture(
            tmp_path / "f.json", corpus, failures={CAPACITY_CASE: "TIMEOUT"}
        )
        _r, _g, d_failed, _ = direct_decide_for(
            corpus, load_direct_capture(failed), approved
        )
        assert d_failed == "INCOMPLETE_COVERAGE", d_failed


# ===========================================================================
# 22. Production-route coverage retains NOT_INVOKED (never mixed)
# ===========================================================================


class TestCoverageDenominatorsNeverMixed:
    def test_production_route_retains_not_invoked(
        self, corpus, tmp_path
    ) -> None:
        """A production-route run where the primary answered everything:
        the fallback VIEW of that run is 43 NOT_INVOKED / 0 evaluated -
        the production-route semantics are unchanged by FU1."""
        path = write_capture(tmp_path / "run.json", corpus)
        f_result = evaluate_for_model(
            corpus, load_capture(path), *fallback_route()
        )
        assert f_result.metrics["counts"]["not_invoked"] == 43
        assert f_result.metrics["counts"]["evaluated_cases"] == 0
        assert f_result.capture_mode == "PRODUCTION_ROUTE"

    def test_direct_mode_has_no_not_invoked(
        self, corpus, tmp_path
    ) -> None:
        """The same model's DIRECT capture is its own 43-case
        denominator: 43 evaluated, 0 NOT_INVOKED, 0 NOT_CAPTURED. The
        two views coexist and never share coverage numbers."""
        path = write_direct_capture(
            tmp_path / "d.json", corpus, target=fallback_route()
        )
        d_result = evaluate_direct_for_model(
            corpus, load_direct_capture(path), *fallback_route()
        )
        assert d_result.metrics["counts"]["evaluated_cases"] == 43
        assert d_result.metrics["counts"]["not_invoked"] == 0
        assert d_result.metrics["counts"]["not_captured"] == 0
        assert d_result.capture_mode == "DIRECT_MODEL_QUALIFICATION"
        # A production-route run projected onto the same model is still
        # all NOT_INVOKED - the direct capture does not feed it.
        p_path = write_capture(tmp_path / "run.json", corpus)
        f_view = evaluate_for_model(
            corpus, load_capture(p_path), *fallback_route()
        )
        assert f_view.metrics["counts"]["not_invoked"] == 43


# ===========================================================================
# 24. False-MATCH safety gates work identically in both modes
# ===========================================================================


class TestSafetyGatesIdenticalInBothModes:
    def test_false_match_fails_closed_in_direct_mode(
        self, corpus, tmp_path
    ) -> None:
        """A direct capture with a false MATCH on the hard-conflict
        capacity case is NOT_QUALIFIED (safety outranks accuracy) even
        under an approved zero-threshold policy."""
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
        path = write_direct_capture(
            tmp_path / "c.json", corpus, decisions={CAPACITY_CASE: "MATCH"}
        )
        result, gates, decision, rationale = direct_decide_for(
            corpus, load_direct_capture(path), approved
        )
        assert decision == "NOT_QUALIFIED", decision
        assert not gates[
            "zero_false_match_on_always_hard_conflicts"
        ].passed
        assert gates["zero_false_match_on_always_hard_conflicts"].failing_case_ids == (
            CAPACITY_CASE,
        )
        assert any(r.startswith("SAFETY_GATE_FAILED:") for r in rationale)
        # The false MATCH stays visible with its case id.
        examples = {
            e["case_id"]
            for e in result.metrics["false_match_examples"]
        }
        assert examples == {CAPACITY_CASE}

    def test_gates_agree_case_for_case_between_modes(
        self, corpus, tmp_path
    ) -> None:
        """The SAME label-consistent responses, captured as a
        production-route run and as a direct-model capture of the same
        model, trip exactly the same gates (here: all eight pass); the
        adversarial variant trips the same gates in both modes."""
        # Correct responses.
        p_path = write_capture(tmp_path / "p.json", corpus)
        d_path = write_direct_capture(tmp_path / "d.json", corpus)
        p_result = evaluate_for_model(
            corpus, load_capture(p_path), *primary_route()
        )
        d_result = evaluate_direct_for_model(
            corpus, load_direct_capture(d_path), *primary_route()
        )
        p_gates, d_gates = (
            evaluate_safety_gates(p_result),
            evaluate_safety_gates(d_result),
        )
        for name in HARD_SAFETY_GATES:
            assert p_gates[name].passed == d_gates[name].passed, name
            assert p_gates[name].failing_case_ids == d_gates[name].failing_case_ids, name

        # Adversarial: a false MATCH + an unauthorized authority claim.
        alias_raw = make_response(
            "MATCH", reason_code="MATCH_AUTHORIZED_IDENTIFIER_RELATION"
        )
        p_path2 = write_capture(
            tmp_path / "p2.json",
            corpus,
            decisions={CAPACITY_CASE: "MATCH"},
            attempts_overrides={
                ALIAS_CASE: [
                    {
                        "role": "PRIMARY",
                        "provider": primary_route()[0],
                        "model": primary_route()[1],
                        "status": "OK",
                        "raw_output": alias_raw,
                    }
                ]
            },
        )
        d_path2 = write_direct_capture(
            tmp_path / "d2.json",
            corpus,
            decisions={CAPACITY_CASE: "MATCH"},
            raw_overrides={ALIAS_CASE: alias_raw},
        )
        p2 = evaluate_for_model(
            corpus, load_capture(p_path2), *primary_route()
        )
        d2 = evaluate_direct_for_model(
            corpus, load_direct_capture(d_path2), *primary_route()
        )
        p2_gates, d2_gates = (
            evaluate_safety_gates(p2),
            evaluate_safety_gates(d2),
        )
        for name in HARD_SAFETY_GATES:
            assert p2_gates[name].passed == d2_gates[name].passed, name
            assert p2_gates[name].failing_case_ids == d2_gates[name].failing_case_ids, name
        assert not d2_gates[
            "zero_unauthorized_authority_promotion"
        ].passed
        assert not d2_gates[
            "zero_customer_alias_authority_promotion"
        ].passed
        assert d2_gates["zero_customer_alias_authority_promotion"].failing_case_ids == (
            ALIAS_CASE,
        )

    def test_alias_promotion_flagged_in_direct_mode(
        self, corpus, tmp_path
    ) -> None:
        """The input-aware cross-check (the production parser cannot
        see): a customer-retrieval-alias case answered with a
        manufacturer-relation claim is flagged in the direct mode too."""
        path = write_direct_capture(
            tmp_path / "c.json",
            corpus,
            raw_overrides={
                ALIAS_CASE: make_response(
                    "MATCH",
                    reason_code="MATCH_AUTHORIZED_IDENTIFIER_RELATION",
                )
            },
        )
        result = evaluate_direct_for_model(
            corpus, load_direct_capture(path), *primary_route()
        )
        o = next(x for x in result.outcomes if x.case_id == ALIAS_CASE)
        assert "UNAUTHORIZED_AUTHORITY_CLAIM" in o.notes
        assert "CUSTOMER_ALIAS_PROMOTION" in o.notes
        gates = evaluate_safety_gates(result)
        assert not gates[
            "zero_unauthorized_authority_promotion"
        ].passed


# ===========================================================================
# 30-32. Policy status, authority marker, firewall
# ===========================================================================


class TestPolicyAndAuthorityBoundaries:
    def test_the_shipped_policy_remains_draft_and_cannot_qualify(
        self, corpus, tmp_path, draft_policy
    ) -> None:
        """Even a fully correct direct capture stays POLICY_PENDING
        under the DRAFT policy - in both modes."""
        assert draft_policy.status == "DRAFT"
        assert draft_policy.approved is False
        for target in (primary_route(), fallback_route()):
            path = write_direct_capture(
                tmp_path / f"{target[0]}.json", corpus, target=target
            )
            _r, _g, decision, rationale = direct_decide_for(
                corpus, load_direct_capture(path), draft_policy
            )
            assert decision == "POLICY_PENDING", decision
            assert any(r.startswith("POLICY_PENDING") for r in rationale)

    def test_v2_authority_qualified_remains_false(self, corpus, tmp_path) -> None:
        from product_intelligence.research import V2_AUTHORITY_QUALIFIED
        from product_intelligence.semantic.runtime_v2 import (
            V2_AUTHORITY_QUALIFIED as RUNTIME_MARKER,
        )

        assert V2_AUTHORITY_QUALIFIED is False
        assert RUNTIME_MARKER is False
        path = write_direct_capture(tmp_path / "c.json", corpus)
        result = evaluate_direct_for_model(
            corpus, load_direct_capture(path), *primary_route()
        )
        # The evaluation itself changes no authority state.
        from product_intelligence.research import (
            V2_AUTHORITY_QUALIFIED as AFTER_MARKER,
        )

        assert AFTER_MARKER is False
        assert result.route_role == "PRIMARY"

    def test_the_direct_report_grants_no_authority(
        self, corpus, tmp_path, draft_policy
    ) -> None:
        """No Machine Price, no Reviewed Price, no human-review
        authority: the direct report's authority section is the same
        explicit no-grant as the production-route report's."""
        from product_intelligence.evaluation.semantic_v2.report import (
            build_direct_report,
        )

        path = write_direct_capture(tmp_path / "c.json", corpus)
        result, gates, decision, rationale = direct_decide_for(
            corpus, load_direct_capture(path), draft_policy
        )
        te = evaluate_thresholds(draft_policy, result.metrics)
        report = build_direct_report(
            result=result,
            gates=gates,
            policy=draft_policy,
            threshold_evaluation=te,
            decision=decision,
            rationale=rationale,
            corpus=corpus,
            direct_capture=load_direct_capture(path),
            generated_utc="2026-10-08T00:00:00Z",
        )
        assert report["authority"]["granted"] is False
        assert report["authority"]["v2_authority_qualified"] is False
        text = json.dumps(report)
        assert "MACHINE_VERIFIED" not in text
        assert "HUMAN_CONFIRMED" not in text
        assert "AI_ASSISTED_COMPARABLE" not in text
        # The report explicitly identifies the DRAFT policy status.
        assert report["policy"]["status"] == "DRAFT"
        assert report["decision"] == "POLICY_PENDING"
