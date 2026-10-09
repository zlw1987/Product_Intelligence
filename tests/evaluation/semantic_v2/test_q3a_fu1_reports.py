"""Q3-A-FU1 reporting tests.

Mandated properties 18 (invalid responses reported, never passed), 27,
28, 29, 30: the direct report explicitly identifies the capture mode,
schema version, model identity, corpus / contract identity, run id,
and the direct coverage facts; production-route and direct-model
reports are never silently combined (each verifier refuses the other
mode); historical production-route baseline reports remain
byte-identical; the qualification policy remains DRAFT; offline
evaluation makes no network or model calls; the harness imports no
production execution surface.
"""

from __future__ import annotations

import ast
import json
import socket
from pathlib import Path

import pytest

from tests.evaluation.semantic_v2._q3a_helpers import (
    POLICY_PATH,
    BASELINE_REPORT_DIR,
    load_corpus_bundle,
    primary_route,
    fallback_route,
    write_capture,
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
    evaluate_direct_for_model,
    evaluate_for_model,
    evaluate_no_capture,
)
from product_intelligence.evaluation.semantic_v2.gates import (
    decide,
    evaluate_safety_gates,
)
from product_intelligence.evaluation.semantic_v2.policy import (
    evaluate_thresholds,
    load_policy,
)
from product_intelligence.evaluation.semantic_v2.report import (
    DIRECT_REPORT_KIND,
    PRODUCTION_REPORT_KIND,
    ReportError,
    build_direct_report,
    build_report,
    render_markdown,
    verify_direct_report,
    verify_report,
)


@pytest.fixture(scope="module")
def corpus():
    return load_corpus_bundle()


@pytest.fixture(scope="module")
def draft_policy():
    return load_policy(POLICY_PATH)


CAPACITY_CASE = "V2Q-SSD-ATTR-CAPACITY-0024"


def _direct_report(corpus, direct, policy, generated_utc="2026-10-08T00:00:00Z"):
    result, gates, decision, rationale = direct_decide_for(
        corpus, direct, policy
    )
    te = (
        evaluate_thresholds(policy, result.metrics)
        if policy is not None
        else None
    )
    report = build_direct_report(
        result=result,
        gates=gates,
        policy=policy,
        threshold_evaluation=te,
        decision=decision,
        rationale=rationale,
        corpus=corpus,
        direct_capture=direct,
        generated_utc=generated_utc,
    )
    return result, report


# ===========================================================================
# 8 (report identity fields). The direct report identifies everything
# ===========================================================================


class TestDirectReportIdentity:
    def test_the_report_identifies_mode_schema_model_corpus_contract(
        self, corpus, tmp_path, draft_policy
    ) -> None:
        path = write_direct_capture(
            tmp_path / "c.json",
            corpus,
            capture_run_id="DIRECT-RUN-77",
            missing=("V2Q-SSD-U4-THIN-0015",),
            failures={CAPACITY_CASE: "TIMEOUT"},
            invalid={"V2Q-SSD-U1-MATCH-0001": "{broken"},
        )
        _result, report = _direct_report(
            corpus, load_direct_capture(path), draft_policy
        )
        # Capture mode + schema version + kind.
        assert report["capture_mode"] == "DIRECT_MODEL_QUALIFICATION"
        assert report["capture_schema_version"] == 1
        assert report["report_kind"] == DIRECT_REPORT_KIND
        # Provider/model (bound target identity).
        assert report["model"]["provider"] == primary_route()[0]
        assert report["model"]["model"] == primary_route()[1]
        assert report["model"]["target_provider"] == primary_route()[0]
        assert report["model"]["target_model"] == primary_route()[1]
        # Corpus identity and digest.
        assert report["corpus"]["corpus_id"] == corpus.corpus_id
        assert report["corpus"]["corpus_version"] == corpus.corpus_version
        assert report["corpus"]["corpus_digest"] == corpus.corpus_digest
        # Frozen contract / prompt identity.
        assert report["contract"]["semantic_contract_binding"] == [
            "V2",
            "2.0",
            1,
            1,
            "SEMANTIC_AUTHORITY_V2_S2A_FU2",
        ]
        assert report["contract"]["prompt_version"] == "2.0"
        assert (
            report["contract"]["runtime_config_identity"][
                "v2_authority_qualified"
            ]
            is False
        )
        # Capture run id + provenance + evaluation timestamp.
        assert report["capture"]["capture_run_id"] == "DIRECT-RUN-77"
        assert report["capture"]["captured_at"] == "2026-10-08T12:00:00Z"
        assert report["generated_utc"] == "2026-10-08T00:00:00Z"
        # Direct coverage facts (the mode's own denominator).
        cov = report["coverage"]
        assert cov["eligible_semantic_cases"] == 43
        assert cov["evaluated_cases"] == 40
        assert cov["not_captured"] == 1
        assert cov["runtime_failure"] == 1
        assert cov["capture_integrity_failure"] == 1
        assert cov["complete"] is False
        assert cov["missing_case_ids"] == ["V2Q-SSD-U4-THIN-0015"]
        assert cov["runtime_failure_case_ids"] == [CAPACITY_CASE]
        assert cov["invalid_response_case_ids"] == ["V2Q-SSD-U1-MATCH-0001"]
        # Per-substate and per-category performance are present.
        assert report["metrics"]["by_substate"]
        assert report["metrics"]["by_category"]
        # Hard safety gates + policy status + decision.
        assert len(report["safety_gates"]) == 8
        assert report["policy"]["status"] == "DRAFT"
        assert report["decision"] in {
            "NOT_QUALIFIED",
            "INCOMPLETE_COVERAGE",
            "POLICY_PENDING",
        }

    def test_the_false_match_case_ids_are_reported(
        self, corpus, tmp_path
    ) -> None:
        path = write_direct_capture(
            tmp_path / "c.json",
            corpus,
            decisions={CAPACITY_CASE: "MATCH"},
        )
        _result, report = _direct_report(
            corpus, load_direct_capture(path), None
        )
        ids = {
            e["case_id"] for e in report["metrics"]["false_match_examples"]
        }
        assert ids == {CAPACITY_CASE}
        assert not report["safety_gates"][
            "zero_false_match_on_always_hard_conflicts"
        ]["passed"]
        assert (
            report["safety_gates"][
                "zero_false_match_on_always_hard_conflicts"
            ]["failing_case_ids"]
            == [CAPACITY_CASE]
        )

    def test_the_direct_markdown_identifies_the_mode(
        self, corpus, tmp_path, draft_policy
    ) -> None:
        path = write_direct_capture(tmp_path / "c.json", corpus)
        _result, report = _direct_report(
            corpus, load_direct_capture(path), draft_policy
        )
        text = render_markdown(report)
        assert "Direct-Model Qualification Report" in text
        assert "DIRECT_MODEL_QUALIFICATION" in text
        assert "independent direct-model capture" in text
        assert "Coverage (direct-model denominator)" in text


# ===========================================================================
# 8 (never combined) + 29. Cross-mode separation, historical bytes
# ===========================================================================


class TestModeSeparationAndHistoricalBytes:
    def test_the_two_modes_are_never_combined(self, corpus, tmp_path) -> None:
        """Each report binds exactly one capture mode and one model;
        the production builder's output keeps its production identity
        (with the explicit PRODUCTION_ROUTE capture-mode section), and
        each mode's verifier refuses the other mode's report."""
        p_path = write_capture(tmp_path / "p.json", corpus)
        prod_result = evaluate_for_model(
            corpus, load_capture(p_path), *primary_route()
        )
        prod_gates = evaluate_safety_gates(prod_result)
        policy = load_policy(POLICY_PATH)
        te = evaluate_thresholds(policy, prod_result.metrics)
        decision, rationale = decide(prod_result, prod_gates, policy, te)
        prod_report = build_report(
            result=prod_result,
            gates=prod_gates,
            policy=policy,
            threshold_evaluation=te,
            decision=decision,
            rationale=rationale,
            corpus=corpus,
            generated_utc="2026-10-08T00:00:00Z",
        )
        # The production report identifies itself as production-route
        # evidence (mode section on the capture) and carries the
        # production kind - no direct-mode fields.
        assert prod_report["report_kind"] == PRODUCTION_REPORT_KIND
        assert "capture_mode" not in prod_report
        assert prod_report["capture"]["capture_mode"] == "PRODUCTION_ROUTE"
        assert prod_report["capture"]["capture_schema_version"] == 1

        d_path = write_direct_capture(tmp_path / "d.json", corpus)
        _r, d_report = _direct_report(
            corpus, load_direct_capture(d_path), policy
        )
        assert d_report["report_kind"] == DIRECT_REPORT_KIND
        assert "coverage" in d_report
        # Cross-mode verification fails closed in both directions.
        with pytest.raises(ReportError, match="cross-mode"):
            verify_report(d_report, corpus)
        with pytest.raises(ReportError, match="cross-mode"):
            verify_direct_report(prod_report, corpus)
        # Same-mode verification passes.
        verify_report(prod_report, corpus)
        verify_direct_report(d_report, corpus)

    def test_historical_baseline_reports_remain_byte_identical(
        self, corpus, draft_policy
    ) -> None:
        """The committed no-capture baseline reports (both pinned
        candidates) are exactly what the (unchanged) production-route
        pipeline produces - byte for byte, JSON and Markdown."""
        for route, stem_route in (
            (primary_route(), "amax_qwen3.8-27b"),
            (fallback_route(), "vllm-262k_Qwen3.6-27B-262K"),
        ):
            result = evaluate_no_capture(corpus, *route)
            gates = evaluate_safety_gates(result)
            te = evaluate_thresholds(draft_policy, result.metrics)
            decision, rationale = decide(result, gates, draft_policy, te)
            rebuilt = build_report(
                result=result,
                gates=gates,
                policy=draft_policy,
                threshold_evaluation=te,
                decision=decision,
                rationale=rationale,
                corpus=corpus,
                generated_utc="2026-10-08T00:00:00Z",
            )
            stem = f"no-capture_{stem_route}"
            committed_json = (
                BASELINE_REPORT_DIR / f"{stem}__report.json"
            ).read_text(encoding="utf-8")
            assert (
                json.dumps(rebuilt, indent=1, sort_keys=True,
                           ensure_ascii=True)
                + "\n"
            ) == committed_json, stem
            committed_md = (
                BASELINE_REPORT_DIR / f"{stem}__report.md"
            ).read_text(encoding="utf-8")
            assert render_markdown(rebuilt) == committed_md, stem

    def test_a_direct_report_does_not_verify_as_historical_production(
        self, corpus, tmp_path
    ) -> None:
        """verify_report (the historical production-route verifier)
        refuses direct reports: no silent reinterpretation."""
        path = write_direct_capture(tmp_path / "d.json", corpus)
        _r, report = _direct_report(corpus, load_direct_capture(path), None)
        with pytest.raises(ReportError, match="cross-mode"):
            verify_report(report, corpus)

    def test_a_direct_report_verifies_against_its_corpus(
        self, corpus, tmp_path
    ) -> None:
        path = write_direct_capture(tmp_path / "d.json", corpus)
        _r, report = _direct_report(corpus, load_direct_capture(path), None)
        verify_direct_report(report, corpus)  # must not raise
        # Tamper the report: the digest catches it.
        tampered = json.loads(json.dumps(report))
        tampered["coverage"]["evaluated_cases"] = 1
        with pytest.raises(ReportError, match="digest"):
            verify_direct_report(tampered, corpus)
        # A label revision stops the direct report from verifying too.
        from copy import deepcopy

        from product_intelligence.evaluation.semantic_v2.canonical import (
            canonical_sha256,
        )
        from product_intelligence.evaluation.semantic_v2.corpus import (
            load_corpus,
        )

        doc = deepcopy(corpus.document)
        target = next(
            c for c in doc["cases"] if c["case_id"] == CAPACITY_CASE
        )
        target["expected"]["decision"] = (
            "MATCH" if target["expected"]["decision"] != "MATCH"
            else "NO_MATCH"
        )
        target["expected"]["acceptable_decisions"] = [
            target["expected"]["decision"]
        ]
        state_view = {k: v for k, v in target.items() if k != "case_digest"}
        target["case_digest"] = canonical_sha256(state_view)
        state = {
            k: v for k, v in doc.items()
            if k not in ("label_revisions", "corpus_digest")
        }
        doc["corpus_digest"] = canonical_sha256(state)
        mut_path = tmp_path / "mutated.json"
        mut_path.write_text(json.dumps(doc), encoding="utf-8")
        mutated = load_corpus(mut_path)
        with pytest.raises(ReportError, match="corpus digest"):
            verify_direct_report(report, mutated)


# ===========================================================================
# 27-28. Offline boundary: no network, no model calls, no production
# execution imports
# ===========================================================================


class TestOfflineBoundary:
    def test_the_direct_pipeline_makes_no_network_call(
        self, corpus, tmp_path, draft_policy, monkeypatch
    ) -> None:

        def refuse(*args, **kwargs):
            raise AssertionError("offline evaluation must not use the network")

        monkeypatch.setattr(socket, "socket", refuse)
        monkeypatch.setattr(socket, "create_connection", refuse)
        monkeypatch.setattr(socket, "getaddrinfo", refuse)
        path = write_direct_capture(tmp_path / "c.json", corpus)
        report = _direct_report(
            corpus, load_direct_capture(path), draft_policy
        )[1]
        assert report["report_digest"]
        assert render_markdown(report)

    def test_the_direct_modules_import_no_production_execution_surface(
        self, corpus, tmp_path
    ) -> None:
        """AST scan: the direct-model path (and every harness module)
        imports no production execution / runs / web / providers /
        transport surface - offline evaluation only.

        Q3-B (bounded live capture runner): ``live_capture.py`` is the
        ONE module that may reference the live transport, and only as
        a LAZY function-level import of the approved factory
        (``get_openai_transport_for_provider``) inside transport
        construction - never at module level, never the production
        runtime module. The execution / runs / web / providers prefix
        ban applies to it too.
        """
        package_root = (
            Path(__file__).resolve().parents[3]
            / "product_intelligence"
            / "evaluation"
            / "semantic_v2"
        )
        forbidden_prefixes = (
            "product_intelligence.execution",
            "product_intelligence.runs",
            "product_intelligence.web",
            "product_intelligence.providers",
        )
        forbidden_modules = {
            "product_intelligence.semantic.transport",
            "product_intelligence.semantic.runtime",
        }
        q3b_live = "live_capture.py"
        for path in sorted(package_root.glob("*.py")):
            tree = ast.parse(path.read_text(encoding="utf-8"))
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    names = [alias.name for alias in node.names]
                elif isinstance(node, ast.ImportFrom) and node.module:
                    names = [node.module]
                else:
                    continue
                for name in names:
                    assert not any(
                        name.startswith(prefix)
                        for prefix in forbidden_prefixes
                    ), f"{path.name} imports {name}"
                    if path.name != q3b_live:
                        assert name not in forbidden_modules, (
                            f"{path.name} imports {name}"
                        )
        # The Q3-B exception is exactly ONE named module, it exists,
        # and its transport reference is precisely bounded: no
        # module-level transport import; exactly ONE function-level
        # import of the approved factory; the production runtime
        # module is still forbidden for it.
        live_path = package_root / q3b_live
        assert live_path.is_file()
        live_tree = ast.parse(live_path.read_text(encoding="utf-8"))
        for node in live_tree.body:
            if isinstance(node, ast.Import):
                names = [alias.name for alias in node.names]
            elif isinstance(node, ast.ImportFrom) and node.module:
                names = [node.module]
            else:
                continue
            for name in names:
                assert name not in forbidden_modules, (
                    f"live_capture.py has a module-level import of "
                    f"{name}; the transport must be imported lazily "
                    "inside transport construction only"
                )
        transport_imports = [
            node
            for node in ast.walk(live_tree)
            if isinstance(node, ast.ImportFrom)
            and node.module == "product_intelligence.semantic.transport"
        ]
        assert len(transport_imports) == 1
        assert {alias.name for alias in transport_imports[0].names} == {
            "get_openai_transport_for_provider"
        }
        function_bodies = [
            node
            for node in ast.walk(live_tree)
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
        ]
        assert any(
            transport_imports[0] in set(ast.walk(func))
            for func in function_bodies
        )

    def test_direct_reports_are_reproducible(self, corpus, tmp_path) -> None:
        """Two runs over the same direct capture produce the same
        report digest (generated_utc is excluded from the digest)."""
        path = write_direct_capture(tmp_path / "c.json", corpus)
        direct = load_direct_capture(path)
        _r1, r1 = _direct_report(corpus, direct, None, "2026-10-08T00:00:00Z")
        _r2, r2 = _direct_report(corpus, direct, None, "2031-01-01T00:00:00Z")
        assert r1["report_digest"] == r2["report_digest"]
        assert r1["generated_utc"] != r2["generated_utc"]
