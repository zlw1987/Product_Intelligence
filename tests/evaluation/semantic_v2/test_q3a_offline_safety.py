"""Q3-A offline-safety tests.

Mandated properties 33-36 (no network access in offline replay; no AI
calls in offline replay; no authority promotion; historical results
retain exact corpus and contract identity) plus the ground-truth
anti-manipulation proofs: qualification cannot be made to pass by
changing expectations to fit model output.
"""

from __future__ import annotations

import json
import socket
import sys
from copy import deepcopy
from pathlib import Path

import pytest

from tests.evaluation.semantic_v2._q3a_helpers import (
    POLICY_PATH,
    load_corpus_bundle,
    primary_route,
    write_capture,
    write_approved_policy,
)
from product_intelligence.evaluation.semantic_v2.capture import (
    load_capture,
)
from product_intelligence.evaluation.semantic_v2.corpus import (
    load_corpus,
)
from product_intelligence.evaluation.semantic_v2.evaluator import (
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
from product_intelligence.evaluation.semantic_v2.report import (
    ReportError,
    build_report,
    render_markdown,
    verify_report,
)


@pytest.fixture(scope="module")
def corpus():
    return load_corpus_bundle()


@pytest.fixture(scope="module")
def full_capture(corpus, tmp_path_factory):
    path = write_capture(
        tmp_path_factory.mktemp("full") / "c.json", corpus
    )
    return load_capture(path)


def _full_report(corpus, capture, policy, generated_utc):
    result = evaluate_for_model(corpus, capture, *primary_route())
    gates = evaluate_safety_gates(result)
    te = (
        evaluate_thresholds(policy, result.metrics)
        if policy is not None
        and policy_applies_to(policy, corpus.corpus_id, corpus.corpus_version)
        else None
    )
    decision, rationale = decide(result, gates, policy, te)
    return build_report(
        result=result,
        gates=gates,
        policy=policy,
        threshold_evaluation=te,
        decision=decision,
        rationale=rationale,
        corpus=corpus,
        generated_utc=generated_utc,
    )


# ===========================================================================
# 33. No network access in offline replay
# ===========================================================================


class TestNoNetwork:
    def test_offline_evaluation_makes_no_network_call(
        self, corpus, full_capture, monkeypatch
    ) -> None:
        def refuse(*args, **kwargs):
            raise AssertionError("offline replay must not use the network")

        monkeypatch.setattr(socket, "socket", refuse)
        monkeypatch.setattr(socket, "create_connection", refuse)
        monkeypatch.setattr(socket, "getaddrinfo", refuse)

        # The full pipeline: load, evaluate, gate, decide, report.
        policy = load_policy(POLICY_PATH)
        report = _full_report(
            corpus, full_capture, policy, "2026-10-08T00:00:00Z"
        )
        assert report["decision"] in {
            "POLICY_PENDING",
            "QUALIFIED",
            "NOT_QUALIFIED",
            "INCOMPLETE_COVERAGE",
        }
        # And the report renders too (still no socket).
        text = render_markdown(report)
        assert "Semantic V2 Qualification Report" in text

    def test_corpus_and_capture_loading_make_no_network_call(
        self, corpus, full_capture, monkeypatch
    ) -> None:
        def refuse(*args, **kwargs):
            raise AssertionError("loading must not use the network")

        monkeypatch.setattr(socket, "socket", refuse)
        monkeypatch.setattr(socket, "getaddrinfo", refuse)
        assert full_capture.records
        assert corpus.cases


# ===========================================================================
# 34. No AI calls in offline replay
# ===========================================================================


class TestNoAICalls:
    def test_the_live_transport_is_never_imported(self, corpus, tmp_path) -> None:
        """Offline evaluation must not pull the live transport into the
        process. (If another test already imported it, we only verify it
        was not imported BY the evaluation - global module state is not
        disturbed.)"""
        present_before = "product_intelligence.semantic.transport" in sys.modules
        import product_intelligence.evaluation.semantic_v2  # noqa: F401

        path = write_capture(tmp_path / "c.json", corpus)
        result = evaluate_for_model(corpus, load_capture(path), *primary_route())
        assert result.outcomes
        if not present_before:
            assert "product_intelligence.semantic.transport" not in sys.modules
            assert "openai" not in sys.modules

    def test_constructing_a_runtime_would_be_detected(
        self, corpus, full_capture, monkeypatch
    ) -> None:
        import product_intelligence.semantic.runtime_v2 as rv2

        def refuse_init(self, *a, **k):
            raise AssertionError(
                "offline replay must not construct a live runtime"
            )

        monkeypatch.setattr(
            rv2.SemanticRuntimeV2, "__init__", refuse_init
        )
        evaluate_for_model(corpus, full_capture, *primary_route())

    def test_the_harness_modules_name_no_ai_surface(self) -> None:
        package_root = (
            Path(__file__).resolve().parents[3]
            / "product_intelligence"
            / "evaluation"
            / "semantic_v2"
        )
        forbidden = (
            "semantic.transport",
            "get_openai",
            "SemanticRuntimeV2(",
            "from product_intelligence.semantic.runtime import",
        )
        for path in sorted(package_root.glob("*.py")):
            text = path.read_text(encoding="utf-8")
            for token in forbidden:
                assert token not in text, (
                    f"{path.name} references {token!r}; the offline "
                    "harness must not reach the live AI surface"
                )


# ===========================================================================
# 35. No authority promotion
# ===========================================================================


class TestNoAuthorityPromotion:
    def test_the_qualification_marker_stays_false(self) -> None:
        from product_intelligence.research import V2_AUTHORITY_QUALIFIED
        from product_intelligence.semantic.runtime_v2 import (
            V2_AUTHORITY_QUALIFIED as RUNTIME_MARKER,
        )

        assert V2_AUTHORITY_QUALIFIED is False
        assert RUNTIME_MARKER is False

    def test_the_report_grants_no_authority(
        self, corpus, full_capture
    ) -> None:
        policy = load_policy(POLICY_PATH)
        report = _full_report(
            corpus, full_capture, policy, "2026-10-08T00:00:00Z"
        )
        assert report["authority"]["granted"] is False
        assert report["authority"]["v2_authority_qualified"] is False
        # No decision token grants authority.
        assert report["decision"] in {
            "POLICY_PENDING",
            "QUALIFIED",
            "NOT_QUALIFIED",
            "INCOMPLETE_COVERAGE",
            "BELOW_THRESHOLD",
            "THRESHOLD_INDETERMINATE",
            "FAIL_CLOSED",
        }
        # Even a QUALIFIED (mechanism) decision grants nothing.
        text = json.dumps(report)
        assert "MACHINE_VERIFIED" not in text
        assert "HUMAN_CONFIRMED" not in text
        assert "AI_ASSISTED_COMPARABLE" not in text

    def test_a_customer_alias_cannot_promote_authority(
        self, corpus, tmp_path
    ) -> None:
        """The harness cross-checks the input-aware rule the production
        parser cannot see: MATCH_AUTHORIZED_IDENTIFIER_RELATION is only
        lawful when the recorded input labeled manufacturer relation
        authority. A customer-retrieval alias is never that."""
        case_id = "V2Q-SSD-U5NM1-ALIAS-0022"  # customer alias only
        from tests.evaluation.semantic_v2._q3a_helpers import (
            make_response,
        )

        raw = make_response(
            "MATCH",
            reason_code="MATCH_AUTHORIZED_IDENTIFIER_RELATION",
        )
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
        o = next(x for x in result.outcomes if x.case_id == case_id)
        assert "UNAUTHORIZED_AUTHORITY_CLAIM" in o.notes
        assert "CUSTOMER_ALIAS_PROMOTION" in o.notes
        gates = evaluate_safety_gates(result)
        assert not gates["zero_unauthorized_authority_promotion"].passed
        assert not gates[
            "zero_customer_alias_authority_promotion"
        ].passed

    def test_labeled_relation_authority_is_not_flagged(
        self, corpus, full_capture
    ) -> None:
        """S20 carries MANUFACTURER_RELATION_AUTHORITY in the input, so
        the authorized-relation reason is lawful there (the full
        correct capture scores it CORRECT without any authority note)."""
        o = next(
            x for x in full_capture.records
            if x.case_id == "V2Q-SSD-U5NM2-RELAUTH-0020"
        )
        assert o.attempts[0].status == "OK"
        result = evaluate_for_model(corpus, full_capture, *primary_route())
        scored = next(
            x for x in result.outcomes
            if x.case_id == "V2Q-SSD-U5NM2-RELAUTH-0020"
        )
        assert scored.verdict == "CORRECT"
        assert "UNAUTHORIZED_AUTHORITY_CLAIM" not in scored.notes

    def test_the_harness_imports_no_pricing_or_review_surface(self) -> None:
        package_root = (
            Path(__file__).resolve().parents[3]
            / "product_intelligence"
            / "evaluation"
            / "semantic_v2"
        )
        forbidden = (
            "product_intelligence.execution",
            "product_intelligence.runs",
            "product_intelligence.web",
            "product_intelligence.providers",
            "aggregation",
            "ai_assisted_review",
            "price_result_codec",
            "django",
        )
        for path in sorted(package_root.glob("*.py")):
            text = path.read_text(encoding="utf-8")
            for token in forbidden:
                assert token not in text, (
                    f"{path.name} references {token!r}; the harness is "
                    "evaluation infrastructure only"
                )


# ===========================================================================
# 36. Historical results retain exact corpus and contract identity
# ===========================================================================


class TestHistoricalIdentity:
    def test_re_evaluating_reproduces_the_same_report_digest(
        self, corpus, full_capture
    ) -> None:
        policy = load_policy(POLICY_PATH)
        r1 = _full_report(
            corpus, full_capture, policy, "2026-10-08T00:00:00Z"
        )
        r2 = _full_report(
            corpus, full_capture, policy, "2026-10-08T00:00:00Z"
        )
        assert r1["report_digest"] == r2["report_digest"]
        # A different generation instant does not move the digest.
        r3 = _full_report(
            corpus, full_capture, policy, "2031-01-01T00:00:00Z"
        )
        assert r3["report_digest"] == r1["report_digest"]

    def test_a_report_verifies_against_its_corpus(self, corpus, full_capture) -> None:
        policy = load_policy(POLICY_PATH)
        report = _full_report(
            corpus, full_capture, policy, "2026-10-08T00:00:00Z"
        )
        verify_report(report, corpus)  # must not raise

    def test_a_report_does_not_verify_against_a_mutated_corpus(
        self, corpus, full_capture, tmp_path
    ) -> None:
        policy = load_policy(POLICY_PATH)
        report = _full_report(
            corpus, full_capture, policy, "2026-10-08T00:00:00Z"
        )
        doc = deepcopy(corpus.document)
        target = next(
            c for c in doc["cases"]
            if c["case_class"] == "AUTHORITATIVE"
        )
        new_decision = (
            "MATCH" if target["expected"]["decision"] != "MATCH"
            else "NO_MATCH"
        )
        target["expected"]["decision"] = new_decision
        target["expected"]["acceptable_decisions"] = [new_decision]
        from product_intelligence.evaluation.semantic_v2.canonical import (
            canonical_sha256,
        )

        state_view = {k: v for k, v in target.items() if k != "case_digest"}
        target["case_digest"] = canonical_sha256(state_view)
        state = {
            k: v for k, v in doc.items()
            if k not in ("label_revisions", "corpus_digest")
        }
        doc["corpus_digest"] = canonical_sha256(state)
        path = tmp_path / "mutated.json"
        path.write_text(json.dumps(doc), encoding="utf-8")
        mutated = load_corpus(path)
        assert mutated.corpus_digest != corpus.corpus_digest
        with pytest.raises(ReportError, match="corpus digest"):
            verify_report(report, mutated)

    def test_a_capture_cannot_follow_a_corpus_revision(
        self, corpus, full_capture, tmp_path
    ) -> None:
        """The capture is bound to the corpus digest it was produced
        for; after a (legitimate) corpus revision the same capture is
        no longer interpretable - it must fail closed."""
        from product_intelligence.evaluation.semantic_v2.evaluator import (
            QualificationContractError,
        )

        doc = deepcopy(corpus.document)
        target = next(
            c for c in doc["cases"]
            if c["case_id"] == "V2Q-SSD-U1-THIN-0005"
        )
        target["expected"]["decision"] = "MATCH"
        target["expected"]["acceptable_decisions"] = ["MATCH", "UNCERTAIN"]
        from product_intelligence.evaluation.semantic_v2.canonical import (
            canonical_sha256,
        )

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
        with pytest.raises(QualificationContractError, match="different corpus"):
            evaluate_for_model(revised, full_capture, *primary_route())

    def test_the_committed_baseline_reports_verify(
        self, corpus
    ) -> None:
        baseline_dir = (
            Path(__file__).resolve().parents[3]
            / "evaluation"
            / "semantic_v2_qualification"
            / "reports"
            / "q3a_baseline"
        )
        reports = sorted(baseline_dir.glob("*__report.json"))
        assert len(reports) == 2
        for path in reports:
            report = json.loads(path.read_text(encoding="utf-8"))
            verify_report(report, corpus)
            assert report["decision"] == "POLICY_PENDING"
            assert report["authority"]["granted"] is False


# ===========================================================================
# Ground-truth anti-manipulation (spec section 1.8 + 4)
# ===========================================================================


class TestAntiManipulation:
    def test_changing_expectations_to_fit_model_output_is_detectable(
        self, corpus, full_capture, tmp_path
    ) -> None:
        """The attack: a model says MATCH where the independent label
        says NO_MATCH; the label is then 'revised' to MATCH to fit the
        output. Proof: (a) the unmanipulated evaluation is an error;
        (b) the manipulation changes the corpus digest; (c) the
        unmanipulated historical report no longer verifies against the
        manipulated corpus - it stays bound to its original identity."""
        from product_intelligence.evaluation.semantic_v2.canonical import (
            canonical_sha256,
        )

        victim = "V2Q-SSD-ATTR-CAPACITY-0024"  # label: NO_MATCH
        # (a) the model's MATCH is a false MATCH on the true corpus
        path = write_capture(
            tmp_path / "c.json",
            corpus,
            decisions={victim: "MATCH"},
        )
        result = evaluate_for_model(corpus, load_capture(path), *primary_route())
        gates = evaluate_safety_gates(result)
        o = next(x for x in result.outcomes if x.case_id == victim)
        assert o.verdict == "FALSE_MATCH"
        assert o.severity == "CRITICAL"
        assert not gates[
            "zero_false_match_on_always_hard_conflicts"
        ].passed
        policy = load_policy(POLICY_PATH)
        report_before = _full_report(
            corpus, load_capture(path), policy, "2026-10-08T00:00:00Z"
        )

        # (b) the 'revision' to fit the output: the digest must change
        doc = deepcopy(corpus.document)
        target = next(c for c in doc["cases"] if c["case_id"] == victim)
        target["expected"]["decision"] = "MATCH"
        target["expected"]["acceptable_decisions"] = ["MATCH"]
        target["expected"]["conflict_classes"] = []
        state_view = {k: v for k, v in target.items() if k != "case_digest"}
        target["case_digest"] = canonical_sha256(state_view)
        state = {
            k: v for k, v in doc.items()
            if k not in ("label_revisions", "corpus_digest")
        }
        doc["corpus_digest"] = canonical_sha256(state)
        assert doc["corpus_digest"] != corpus.corpus_digest
        mpath = tmp_path / "manipulated.json"
        mpath.write_text(json.dumps(doc), encoding="utf-8")
        manipulated = load_corpus(mpath)

        # (c) the historical report stays with its original corpus
        verify_report(report_before, corpus)
        with pytest.raises(ReportError, match="corpus digest"):
            verify_report(report_before, manipulated)
        # And the capture bound to the original corpus cannot be
        # evaluated against the manipulated one.
        from product_intelligence.evaluation.semantic_v2.evaluator import (
            QualificationContractError,
        )

        with pytest.raises(QualificationContractError):
            evaluate_for_model(
                manipulated, load_capture(path), *primary_route()
            )

    def test_an_unsealed_label_edit_is_rejected_on_load(
        self, corpus, tmp_path
    ) -> None:
        """Silent mutation (edit the label, keep the old digest) is
        caught at load time - the corpus cannot be used at all in that
        state."""
        doc = deepcopy(corpus.document)
        target = next(
            c for c in doc["cases"]
            if c["case_id"] == "V2Q-SSD-ATTR-CAPACITY-0024"
        )
        target["expected"]["decision"] = "MATCH"
        target["expected"]["acceptable_decisions"] = ["MATCH"]
        # corpus_digest NOT recomputed
        path = tmp_path / "silent.json"
        path.write_text(json.dumps(doc), encoding="utf-8")
        from product_intelligence.evaluation.semantic_v2.corpus import (
            CorpusIntegrityError,
        )

        with pytest.raises(CorpusIntegrityError, match="case_digest"):
            load_corpus(path)

    def test_the_baseline_report_is_reproducible(
        self, corpus
    ) -> None:
        """The committed no-capture baseline reports are exactly what
        the pipeline produces for the committed corpus (deterministic
        offline report)."""
        from product_intelligence.evaluation.semantic_v2.evaluator import (
            evaluate_no_capture,
        )
        from product_intelligence.evaluation.semantic_v2.gates import (
            decide,
            evaluate_safety_gates,
        )
        from product_intelligence.evaluation.semantic_v2.report import (
            build_report,
        )

        policy = load_policy(POLICY_PATH)
        for route in (primary_route(), ("vllm-262k", "Qwen3.6-27B-262K")):
            result = evaluate_no_capture(corpus, *route)
            gates = evaluate_safety_gates(result)
            te = evaluate_thresholds(policy, result.metrics)
            decision, rationale = decide(result, gates, policy, te)
            rebuilt = build_report(
                result=result,
                gates=gates,
                policy=policy,
                threshold_evaluation=te,
                decision=decision,
                rationale=rationale,
                corpus=corpus,
                generated_utc="2026-10-08T00:00:00Z",
            )
            stem = f"no-capture_{route[0]}_{route[1]}"
            committed = json.loads(
                (
                    Path(__file__).resolve().parents[3]
                    / "evaluation"
                    / "semantic_v2_qualification"
                    / "reports"
                    / "q3a_baseline"
                    / f"{stem}__report.json"
                ).read_text(encoding="utf-8")
            )
            assert rebuilt["report_digest"] == committed["report_digest"]
            committed.pop("generated_utc")
            rebuilt.pop("generated_utc")
            assert committed == rebuilt
