"""Q3-A-FU1 independent direct-model evaluation tests.

Mandated properties 8-10, 13-18, 21, 23, 25-26: wrong / unknown
provider-model fails closed; cross-mode evaluation fails closed;
contract-negative responses fail closed; corpus digest and prompt/
contract mismatches fail closed; missing / runtime-failure / invalid
responses cannot PASS; direct-model coverage uses its own denominator;
the production parser is reused without approximation; synthetic labels
stay synthetic; the motivating Micron case is unchanged.
"""

from __future__ import annotations

import json

import pytest

from tests.evaluation.semantic_v2._q3a_helpers import (
    load_corpus_bundle,
    primary_route,
    fallback_route,
    write_capture,
)
from tests.evaluation.semantic_v2._q3a_fu1_helpers import (
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
)


@pytest.fixture(scope="module")
def corpus():
    return load_corpus_bundle()


def outcome(result, case_id):
    return next(o for o in result.outcomes if o.case_id == case_id)


MICRON_CASE = "V2Q-SSD-U5NM1-MICRON-0018"
CAPACITY_CASE = "V2Q-SSD-ATTR-CAPACITY-0024"


# ===========================================================================
# 8-10. Model identity enforcement (fail closed)
# ===========================================================================


class TestModelIdentityEnforcement:
    def test_wrong_provider_model_fails_closed(self, corpus, tmp_path) -> None:
        """A capture bound to the primary cannot be evaluated as the
        fallback (and vice versa): responses never transfer between
        model identities."""
        p_path = write_direct_capture(tmp_path / "p.json", corpus)
        capture = load_direct_capture(p_path)
        with pytest.raises(QualificationContractError, match="bound to"):
            evaluate_direct_for_model(
                corpus, capture, *fallback_route()
            )
        f_path = write_direct_capture(
            tmp_path / "f.json", corpus, target=fallback_route()
        )
        f_capture = load_direct_capture(f_path)
        with pytest.raises(QualificationContractError, match="bound to"):
            evaluate_direct_for_model(corpus, f_capture, *primary_route())

    def test_unknown_provider_model_fails_closed(self, corpus, tmp_path) -> None:
        path = write_direct_capture(tmp_path / "p.json", corpus)
        capture = load_direct_capture(path)
        with pytest.raises(
            QualificationContractError, match="not one of the frozen"
        ):
            evaluate_direct_for_model(
                corpus, capture, "not-a-pinned-provider", "not-a-pinned-model"
            )

    def test_cross_mode_evaluation_fails_closed(self, corpus, tmp_path) -> None:
        """A direct document is void in the production-route evaluator
        and a production document is void in the direct evaluator - in
        both directions, never reinterpreted."""
        d_path = write_direct_capture(tmp_path / "d.json", corpus)
        d_doc = load_direct_capture(d_path)
        with pytest.raises(QualificationContractError, match="direct-model"):
            evaluate_for_model(corpus, d_doc, *primary_route())

        p_path = write_capture(tmp_path / "p.json", corpus)
        p_doc = load_capture(p_path)
        with pytest.raises(
            QualificationContractError, match="production-route"
        ):
            evaluate_direct_for_model(corpus, p_doc, *primary_route())

    def test_direct_evaluation_imports_no_production_orchestration(
        self, corpus, tmp_path
    ) -> None:
        """The direct-model evaluator path never pulls the production
        execution surface into the process."""
        import sys

        before = {
            name for name in sys.modules
            if name.startswith("product_intelligence.execution")
        }
        path = write_direct_capture(tmp_path / "c.json", corpus)
        evaluate_direct_for_model(
            corpus, load_direct_capture(path), *primary_route()
        )
        after = {
            name for name in sys.modules
            if name.startswith("product_intelligence.execution")
        }
        assert after == before


# ===========================================================================
# 13-15. Contract / capture mismatch (fail closed)
# ===========================================================================


class TestContractMismatchFailsClosed:
    def test_contract_negative_response_fails_closed(
        self, corpus, tmp_path
    ) -> None:
        """A record for a contract-negative case is a schema-bypass
        attack: it cannot be evaluated (proved at corpus verification;
        a document that slips past load is void at evaluation)."""
        cn_id = next(
            c.case_id for c in corpus.cases if c.case_class == "CONTRACT_NEGATIVE"
        )
        path = write_direct_capture(tmp_path / "c.json", corpus)
        doc = json.loads(path.read_text(encoding="utf-8"))
        doc["records"].append(
            {
                "case_id": cn_id,
                "execution_status": "OK",
                "raw_output": json.dumps({"decision": "MATCH"}),
            }
        )
        path.write_text(json.dumps(doc), encoding="utf-8")
        with pytest.raises(QualificationContractError, match="schema-bypass"):
            evaluate_direct_for_model(
                corpus, load_direct_capture(path), *primary_route()
            )

    def test_corpus_digest_mismatch_fails_closed(self, corpus, tmp_path) -> None:
        path = write_direct_capture(tmp_path / "c.json", corpus)
        doc = json.loads(path.read_text(encoding="utf-8"))
        doc["corpus_digest"] = "f" * 64
        path.write_text(json.dumps(doc), encoding="utf-8")
        with pytest.raises(QualificationContractError, match="different corpus"):
            evaluate_direct_for_model(
                corpus, load_direct_capture(path), *primary_route()
            )

    def test_prompt_contract_mismatch_fails_closed(
        self, corpus, tmp_path
    ) -> None:
        path = write_direct_capture(tmp_path / "c.json", corpus)
        doc = json.loads(path.read_text(encoding="utf-8"))
        doc["prompt_version"] = "1.1"
        path.write_text(json.dumps(doc), encoding="utf-8")
        with pytest.raises(Exception, match="prompt_version"):
            load_direct_capture(path)
        path2 = write_direct_capture(tmp_path / "c2.json", corpus)
        doc2 = json.loads(path2.read_text(encoding="utf-8"))
        doc2["semantic_contract"] = "V1"
        path2.write_text(json.dumps(doc2), encoding="utf-8")
        with pytest.raises(Exception, match="semantic_contract"):
            load_direct_capture(path2)

    def test_evaluation_against_a_revised_corpus_fails_closed(
        self, corpus, tmp_path
    ) -> None:
        """A direct capture bound to the original corpus digest cannot
        be evaluated against a revised corpus (fail closed, never
        silently re-scored) - the direct counterpart of the Q3-A
        property."""
        from copy import deepcopy

        from product_intelligence.evaluation.semantic_v2.canonical import (
            canonical_sha256,
        )
        from product_intelligence.evaluation.semantic_v2.corpus import (
            load_corpus,
        )

        doc = deepcopy(corpus.document)
        target = next(
            c for c in doc["cases"] if c["case_id"] == MICRON_CASE
        )
        target["expected"]["decision"] = "MATCH"
        target["expected"]["acceptable_decisions"] = ["MATCH"]
        state_view = {k: v for k, v in target.items() if k != "case_digest"}
        target["case_digest"] = canonical_sha256(state_view)
        state = {
            k: v for k, v in doc.items()
            if k not in ("label_revisions", "corpus_digest")
        }
        doc["corpus_digest"] = canonical_sha256(state)
        path = tmp_path / "revised.json"
        path.write_text(json.dumps(doc), encoding="utf-8")
        revised = load_corpus(path)
        c_path = write_direct_capture(tmp_path / "c.json", corpus)
        with pytest.raises(QualificationContractError, match="different corpus"):
            evaluate_direct_for_model(
                revised, load_direct_capture(c_path), *primary_route()
            )


# ===========================================================================
# 16-18. Missing / runtime-failure / invalid responses cannot PASS
# ===========================================================================


class TestCoverageSemantics:
    def test_missing_response_is_not_captured(self, corpus, tmp_path) -> None:
        path = write_direct_capture(
            tmp_path / "c.json", corpus, missing=(CAPACITY_CASE,)
        )
        result = evaluate_direct_for_model(
            corpus, load_direct_capture(path), *primary_route()
        )
        o = outcome(result, CAPACITY_CASE)
        assert o.state == "NOT_CAPTURED"
        assert o.verdict == "NOT_EVALUATED"
        assert o.model_decision is None
        assert result.metrics["counts"]["not_captured"] == 1
        assert result.metrics["counts"]["evaluated_cases"] == 42

    def test_runtime_failure_is_preserved_not_scored(self, corpus, tmp_path) -> None:
        path = write_direct_capture(
            tmp_path / "c.json", corpus, failures={CAPACITY_CASE: "TIMEOUT"}
        )
        result = evaluate_direct_for_model(
            corpus, load_direct_capture(path), *primary_route()
        )
        o = outcome(result, CAPACITY_CASE)
        assert o.state == "RUNTIME_FAILURE"
        assert o.verdict == "RUNTIME_FAILED"
        assert o.model_decision is None
        assert o.runtime_failure_status == "TIMEOUT"
        assert o.provenance_role == "DIRECT"
        assert result.metrics["counts"]["runtime_failures_by_status"] == {
            "TIMEOUT": 1
        }

    def test_invalid_response_is_an_integrity_failure(self, corpus, tmp_path) -> None:
        path = write_direct_capture(
            tmp_path / "c.json", corpus, invalid={CAPACITY_CASE: "{broken"}
        )
        result = evaluate_direct_for_model(
            corpus, load_direct_capture(path), *primary_route()
        )
        o = outcome(result, CAPACITY_CASE)
        assert o.state == "CAPTURE_INTEGRITY_FAILURE"
        assert o.verdict == "INTEGRITY_FAILED"
        assert o.severity == "CRITICAL"
        assert o.runtime_failure_status == "MALFORMED_JSON"
        assert o.model_decision is None
        # The invalid response is never substituted with the expected
        # answer: the case is not counted as evaluated.
        assert result.metrics["counts"]["evaluated_cases"] == 42
        assert result.metrics["counts"]["capture_integrity_failures"] == 1

    def test_none_of_these_states_is_a_successful_evaluation(
        self, corpus, tmp_path
    ) -> None:
        path = write_direct_capture(
            tmp_path / "c.json",
            corpus,
            missing=("V2Q-SSD-U4-THIN-0015",),
            failures={CAPACITY_CASE: "EMPTY_RESPONSE"},
            invalid={"V2Q-SSD-U1-MATCH-0001": "{broken"},
        )
        result = evaluate_direct_for_model(
            corpus, load_direct_capture(path), *primary_route()
        )
        m = result.metrics
        assert m["counts"]["evaluated_cases"] == 40
        assert m["counts"]["not_captured"] == 1
        assert m["counts"]["runtime_failure_count"] == 1
        assert m["counts"]["capture_integrity_failures"] == 1
        # The three non-EVALUATED states are separate surfaces; none
        # enters the evaluated count.
        states = {
            o.state
            for o in result.outcomes
            if o.case_class != "CONTRACT_NEGATIVE"
        }
        assert states == {
            "EVALUATED",
            "NOT_CAPTURED",
            "RUNTIME_FAILURE",
            "CAPTURE_INTEGRITY_FAILURE",
        }

    def test_not_invoked_never_appears_in_direct_mode(
        self, corpus, tmp_path
    ) -> None:
        """The production-route NOT_INVOKED state has no direct-mode
        meaning: the coverage denominators of the two modes are never
        mixed."""
        for target in (primary_route(), fallback_route()):
            path = write_direct_capture(
                tmp_path / f"{target[0]}.json", corpus, target=target
            )
            result = evaluate_direct_for_model(
                corpus, load_direct_capture(path), *target
            )
            assert result.metrics["counts"]["not_invoked"] == 0
            assert "NOT_INVOKED" not in {
                o.state for o in result.outcomes
            }

    def test_direct_coverage_uses_its_own_denominator(
        self, corpus, tmp_path
    ) -> None:
        """Direct-mode coverage is 43 eligible cases of THIS model's
        capture - with one missing record the valid-response denominator
        is 42: the direct denominator is this capture's own, never the
        production-route view of another run."""
        path = write_direct_capture(
            tmp_path / "c.json", corpus, missing=(CAPACITY_CASE,)
        )
        result = evaluate_direct_for_model(
            corpus, load_direct_capture(path), *primary_route()
        )
        m = result.metrics
        assert m["counts"]["eligible_semantic_cases"] == 43
        assert m["counts"]["not_captured"] == 1
        rate = m["valid_structured_response_rate"]
        assert rate["denominator"] == 42
        assert rate["numerator"] == 42


# ===========================================================================
# 23. The production parser is reused without approximation
# ===========================================================================


class TestProductionParserReuse:
    def test_same_responses_score_identically_in_both_modes(
        self, corpus, tmp_path
    ) -> None:
        """The label-consistent responses of one full run, captured as a
        production-route run (primary answers) and as a direct-model
        capture of the primary, must score case-for-case identically:
        the direct path composes the SAME frozen production parser and
        the SAME label-driven scoring - no approximation."""
        p_path = write_capture(tmp_path / "p.json", corpus)
        prod = evaluate_for_model(
            corpus, load_capture(p_path), *primary_route()
        )
        d_path = write_direct_capture(tmp_path / "d.json", corpus)
        direct = evaluate_direct_for_model(
            corpus, load_direct_capture(d_path), *primary_route()
        )
        prod_by_id = {o.case_id: o for o in prod.outcomes}
        for o in direct.outcomes:
            p = prod_by_id[o.case_id]
            assert (
                o.state,
                o.verdict,
                o.severity,
                o.model_decision,
                o.model_confidence,
                o.model_reason_code,
                o.model_conflict_classes,
            ) == (
                p.state,
                p.verdict,
                p.severity,
                p.model_decision,
                p.model_confidence,
                p.model_reason_code,
                p.model_conflict_classes,
            ), o.case_id

    def test_invalid_response_classification_matches_production(
        self, corpus, tmp_path
    ) -> None:
        """The same malformed raw output fails identically in both
        modes (same parser composition: MALFORMED_JSON)."""
        raw = "{broken"
        p_path = write_capture(
            tmp_path / "p.json",
            corpus,
            attempts_overrides={
                CAPACITY_CASE: [
                    {
                        "role": "PRIMARY",
                        "provider": primary_route()[0],
                        "model": primary_route()[1],
                        "status": "OK",
                        "raw_output": raw,
                    }
                ]
            },
        )
        prod = evaluate_for_model(
            corpus, load_capture(p_path), *primary_route()
        )
        d_path = write_direct_capture(
            tmp_path / "d.json", corpus, invalid={CAPACITY_CASE: raw}
        )
        direct = evaluate_direct_for_model(
            corpus, load_direct_capture(d_path), *primary_route()
        )
        assert outcome(prod, CAPACITY_CASE).state == (
            outcome(direct, CAPACITY_CASE).state
        ) == "CAPTURE_INTEGRITY_FAILURE"
        assert outcome(prod, CAPACITY_CASE).runtime_failure_status == (
            outcome(direct, CAPACITY_CASE).runtime_failure_status
        ) == "MALFORMED_JSON"

    def test_schema_invalid_classification_matches_production(
        self, corpus, tmp_path
    ) -> None:
        raw = json.dumps(
            {
                "decision": "NO_MATCH",
                "confidence": "HIGH",
                "reason_code": "NO_MATCH_OTHER",
                "matched_attributes": [],
                "conflicting_attributes": [],
                "missing_critical_attributes": [],
                "conflict_classes": ["NOT_A_CLASS"],
            }
        )
        d_path = write_direct_capture(
            tmp_path / "d.json", corpus, invalid={CAPACITY_CASE: raw}
        )
        direct = evaluate_direct_for_model(
            corpus, load_direct_capture(d_path), *primary_route()
        )
        assert outcome(direct, CAPACITY_CASE).runtime_failure_status == (
            "SCHEMA_INVALID"
        )


# ===========================================================================
# 25-26. Ground-truth preservation
# ===========================================================================


class TestGroundTruthPreservation:
    def test_the_micron_case_remains_unchanged(self, corpus, tmp_path) -> None:
        """The motivating Micron pair (…YYR vs …YY) still expects
        UNCERTAIN with the commercial sales-unit-safety flag; a direct
        capture that answers it correctly scores CORRECT, and one that
        says MATCH is a CRITICAL false MATCH in both modes."""
        case = corpus.case(MICRON_CASE)
        assert case.expected["decision"] == "UNCERTAIN"
        assert case.expected["commercial_sales_unit_safety"] is True
        assert "PACKAGING_QUANTITY" in case.expected["missing_dimensions"]

        path = write_direct_capture(tmp_path / "c.json", corpus)
        result = evaluate_direct_for_model(
            corpus, load_direct_capture(path), *primary_route()
        )
        o = outcome(result, MICRON_CASE)
        assert o.state == "EVALUATED"
        assert o.verdict == "CORRECT"
        assert o.model_decision == "UNCERTAIN"

        wrong = write_direct_capture(
            tmp_path / "w.json", corpus, decisions={MICRON_CASE: "MATCH"}
        )
        w_result = evaluate_direct_for_model(
            corpus, load_direct_capture(wrong), *primary_route()
        )
        w_o = outcome(w_result, MICRON_CASE)
        assert w_o.verdict == "FALSE_MATCH"
        assert w_o.severity == "CRITICAL"

    def test_synthetic_labels_remain_identified_as_synthetic(
        self, corpus, tmp_path
    ) -> None:
        """The direct pipeline never re-labels evidence kinds: the
        synthetic cases keep their synthetic labels in the corpus the
        report binds to, and the report's per-case label snapshots
        verify against exactly that corpus (no real-market claim)."""
        synthetic_ids = {
            c["case_id"]
            for c in corpus.document["cases"]
            if c["evidence_kind"] == "SYNTHETIC"
        }
        assert synthetic_ids
        assert not any(
            c["evidence_kind"] == "REAL_MARKET"
            for c in corpus.document["cases"]
        )
        path = write_direct_capture(tmp_path / "c.json", corpus)
        result = evaluate_direct_for_model(
            corpus, load_direct_capture(path), *primary_route()
        )
        reported = {
            o.case_id: o for o in result.outcomes if o.case_id in synthetic_ids
        }
        assert len(reported) == len(synthetic_ids)
        for case_id, o in reported.items():
            doc_case = next(
                c for c in corpus.document["cases"] if c["case_id"] == case_id
            )
            # The per-case label snapshot in the evaluation is exactly
            # the sealed corpus label (the report binds to this digest;
            # synthetic evidence is never re-labelled).
            assert o.expected_decision == doc_case["expected"]["decision"]
            assert o.acceptable_decisions == tuple(
                doc_case["expected"].get("acceptable_decisions") or ()
            ) or o.acceptable_decisions is None
