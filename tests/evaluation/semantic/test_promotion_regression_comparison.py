"""Promotion-regression comparison tests (PRODUCT-INTEL.SEMANTIC.PROMOTION-REGRESSION).

Offline tests for the two-run comparison and its human-review semantics:

* ideal-vs-ideal produces zero disagreements and zero review rows;
* challenger MATCH vs primary NO_MATCH/UNCERTAIN is flagged as
  ``positive_authority_expansion`` and always requires human review;
* primary MATCH vs challenger NO_MATCH/UNCERTAIN is flagged as a
  conservative challenger regression (recall loss);
* unsafe MATCHes fail the challenger's promotion gate (objective fact);
* invalid outputs are surfaced and never reinterpreted;
* provenance-incompatible runs fail closed;
* the comparison never declares a winner and carries no ranking/score.

No live network/model calls. No production files modified.
"""

from __future__ import annotations

import dataclasses
import json
from pathlib import Path

import pytest

from product_intelligence.evaluation.semantic.promotion_regression import (
    PromotionRegressionComparisonError,
    compare_promotion_regression_runs,
    get_authorized_model_spec,
    load_promotion_regression_corpus,
    run_promotion_regression,
    save_comparison,
    save_run,
)
from product_intelligence.semantic.transport import FakeSemanticModelTransport

NEOTRON_SPEC = get_authorized_model_spec("amax", "nemotron-3-super")
QWEN_SPEC = get_authorized_model_spec("amax", "qwen3.8-27b")
CORPUS = load_promotion_regression_corpus()
CALLED_IDS = tuple(c.case_id for c in CORPUS.cases if c.expected_semantic_call)


def _resp(decision: str) -> str:
    return json.dumps(
        {
            "decision": decision,
            "confidence": "HIGH",
            "matched_attributes": [],
            "conflicting_attributes": [],
            "missing_critical_attributes": [],
            "reason_code": "test",
        }
    )


def _ideal_run(spec, overrides: dict[str, str] | None = None):
    responses = {}
    for case in CORPUS.cases:
        if case.expected_semantic_call:
            responses[case.case_id] = _resp(case.expected_semantic_decision)
    if overrides:
        responses.update(overrides)
    transport = FakeSemanticModelTransport(
        case_ids=CALLED_IDS,
        responses=responses,
        provider_reported_model=spec.model,
    )
    run = run_promotion_regression(spec, transport)
    return run, transport


def _row(comparison, case_id: str):
    return next(r for r in comparison.rows if r.case_id == case_id)


# ---------------------------------------------------------------------------
# Ideal vs ideal: agreement, no review, no winner
# ---------------------------------------------------------------------------


class TestIdealComparison:
    def test_ideal_vs_ideal_no_disagreements(self):
        primary, _ = _ideal_run(NEOTRON_SPEC)
        challenger, _ = _ideal_run(QWEN_SPEC)
        comparison = compare_promotion_regression_runs(primary, challenger)
        assert comparison.provenance_compatible is True
        assert comparison.provenance_issues == ()
        assert comparison.aggregates["model_disagreement_count"] == 0
        assert comparison.aggregates["positive_authority_expansion_count"] == 0
        assert comparison.aggregates["conservative_challenger_regression_count"] == 0
        assert comparison.aggregates["human_review_required_count"] == 0
        assert comparison.human_review_case_ids == ()
        for row in comparison.rows:
            assert row.model_disagreement is False
            assert row.human_review_required is False

    def test_comparison_declares_no_winner(self):
        primary, _ = _ideal_run(NEOTRON_SPEC)
        challenger, _ = _ideal_run(QWEN_SPEC)
        comparison = compare_promotion_regression_runs(primary, challenger)
        data = comparison.to_dict()
        assert data["no_winner_declared"] is True
        assert "winner" not in data
        # Aggregates carry objective facts only: no scores, ranks, or
        # weighted combinations.
        for block in (data["aggregates"],):
            blob = json.dumps(block)
            assert "score" not in blob.lower()
            assert "rank" not in blob.lower()
            assert "winner" not in blob.lower()
        md = comparison.summary_md()
        assert "No winner declared" in md

    def test_comparison_rows_are_case_complete_and_bounded(self):
        primary, _ = _ideal_run(NEOTRON_SPEC)
        challenger, _ = _ideal_run(QWEN_SPEC)
        comparison = compare_promotion_regression_runs(primary, challenger)
        assert [r.case_id for r in comparison.rows] == [c.case_id for c in CORPUS.cases]
        called_row = _row(comparison, "SPR-0005").to_dict()
        assert called_row["expected_semantic_call"] is True
        assert called_row["expected_semantic_decision"] == "MATCH"
        assert called_row["expected_authority_outcome"] == "AI_ASSISTED_MATCH_ONLY"
        assert called_row["primary"]["decision"] == "MATCH"
        assert called_row["primary"]["confidence"] == "HIGH"
        assert called_row["primary"]["valid"] is True
        assert called_row["challenger"]["decision"] == "MATCH"
        # Bounded provenance only: raw model bodies never enter the
        # comparison artifact.
        blob = json.dumps(comparison.to_dict())
        assert "raw_output" not in blob
        # No-call cases are present but carry no model decisions.
        nocall_row = _row(comparison, "SPR-0001").to_dict()
        assert nocall_row["expected_semantic_call"] is False
        assert nocall_row["primary"]["decision"] is None
        assert nocall_row["challenger"]["decision"] is None


# ---------------------------------------------------------------------------
# Disagreement semantics: expansion vs conservative regression
# ---------------------------------------------------------------------------


class TestDisagreementSemantics:
    def test_challenger_match_vs_primary_no_match_is_expansion_and_review(self):
        # SPR-0008 expects UNCERTAIN: primary UNCERTAIN (ideal), challenger
        # MATCH - the challenger expands positive authority relative to
        # production. Not a gate failure (case is not unsafe), but a
        # mandatory human-review condition.
        primary, _ = _ideal_run(NEOTRON_SPEC)
        challenger, _ = _ideal_run(QWEN_SPEC, {"SPR-0008": _resp("MATCH")})
        comparison = compare_promotion_regression_runs(primary, challenger)
        row = _row(comparison, "SPR-0008")
        assert row.model_disagreement is True
        assert row.positive_authority_expansion is True
        assert row.conservative_challenger_regression is False
        assert row.challenger_false_match is True
        assert row.human_review_required is True
        assert "SPR-0008" in comparison.human_review_case_ids
        # Both promotion gates still PASS: this is review material, not a
        # safety failure.
        assert primary.promotion_gate_passed is True
        assert challenger.promotion_gate_passed is True

    def test_challenger_match_vs_primary_uncertain_is_expansion(self):
        # SPR-0009 expects UNCERTAIN for both; challenger says MATCH.
        primary, _ = _ideal_run(NEOTRON_SPEC)
        challenger, _ = _ideal_run(QWEN_SPEC, {"SPR-0009": _resp("MATCH")})
        comparison = compare_promotion_regression_runs(primary, challenger)
        row = _row(comparison, "SPR-0009")
        assert row.positive_authority_expansion is True
        assert row.model_disagreement is True
        assert row.human_review_required is True

    def test_primary_match_vs_challenger_no_match_is_recall_loss(self):
        # SPR-0005 expects MATCH: primary MATCH (ideal), challenger
        # NO_MATCH - conservative challenger regression / recall loss.
        primary, _ = _ideal_run(NEOTRON_SPEC)
        challenger, _ = _ideal_run(QWEN_SPEC, {"SPR-0005": _resp("NO_MATCH")})
        comparison = compare_promotion_regression_runs(primary, challenger)
        row = _row(comparison, "SPR-0005")
        assert row.model_disagreement is True
        assert row.positive_authority_expansion is False
        assert row.conservative_challenger_regression is True
        assert row.human_review_required is True
        # A NO_MATCH where MATCH was expected is NOT a false match.
        assert row.challenger_false_match is False
        assert row.challenger_unsafe_match is False

    def test_unsafe_match_flags_safety_sensitive_disagreement(self):
        # SPR-0013 (accessory trap, expected NO_MATCH, unsafe): challenger
        # MATCH vs primary NO_MATCH -> expansion AND safety-sensitive.
        primary, _ = _ideal_run(NEOTRON_SPEC)
        challenger, _ = _ideal_run(QWEN_SPEC, {"SPR-0013": _resp("MATCH")})
        comparison = compare_promotion_regression_runs(primary, challenger)
        row = _row(comparison, "SPR-0013")
        assert row.model_disagreement is True
        assert row.positive_authority_expansion is True
        assert row.disagreement_safety_sensitive is True
        assert row.challenger_unsafe_match is True
        assert row.human_review_required is True
        assert comparison.aggregates["disagreement_safety_sensitive_count"] == 1
        # The challenger's promotion gate FAILS on the unsafe MATCH.
        assert challenger.promotion_gate_passed is False
        failed = [g for g in challenger.gates if not g.passed]
        assert [g.name for g in failed] == ["no_unsafe_match"]

    def test_agreement_on_unsafe_case_is_not_a_disagreement(self):
        primary, _ = _ideal_run(NEOTRON_SPEC)
        challenger, _ = _ideal_run(QWEN_SPEC)
        comparison = compare_promotion_regression_runs(primary, challenger)
        row = _row(comparison, "SPR-0013")
        assert row.model_disagreement is False
        assert row.disagreement_safety_sensitive is False
        assert row.human_review_required is False

    def test_roles_are_explicit_and_directional(self):
        """Swapping the runs swaps the direction of the flags: the
        comparison is about roles (production baseline vs challenger), not
        about model names."""
        # Nemotron MATCHes SPR-0005 (ideal), qwen NO_MATCHes it.
        primary, _ = _ideal_run(NEOTRON_SPEC)
        challenger, _ = _ideal_run(QWEN_SPEC, {"SPR-0005": _resp("NO_MATCH")})
        forward = compare_promotion_regression_runs(primary, challenger)
        assert _row(forward, "SPR-0005").conservative_challenger_regression is True
        assert _row(forward, "SPR-0005").positive_authority_expansion is False

        swapped = compare_promotion_regression_runs(challenger, primary)
        assert _row(swapped, "SPR-0005").positive_authority_expansion is True
        assert _row(swapped, "SPR-0005").conservative_challenger_regression is False


# ---------------------------------------------------------------------------
# Invalid outputs are surfaced, never reinterpreted
# ---------------------------------------------------------------------------


class TestInvalidOutputSurface:
    def test_invalid_challenger_output_surfaced_and_gated(self):
        bad = "I think they match.\n" + _resp("MATCH")
        primary, _ = _ideal_run(NEOTRON_SPEC)
        challenger, _ = _ideal_run(QWEN_SPEC, {"SPR-0005": bad})
        comparison = compare_promotion_regression_runs(primary, challenger)
        row = _row(comparison, "SPR-0005")
        assert row.challenger_valid is False
        assert row.challenger_decision is None
        # An invalid output is NOT reinterpreted as a decision, so there is
        # no disagreement to compare - but the case is still review
        # material because the challenger failed the response contract.
        assert row.model_disagreement is False
        assert row.human_review_required is True
        assert challenger.promotion_gate_passed is False

    def test_both_invalid_is_not_a_disagreement(self):
        bad = "```json\n" + _resp("MATCH") + "\n```"
        primary, _ = _ideal_run(NEOTRON_SPEC, {"SPR-0005": bad})
        challenger, _ = _ideal_run(QWEN_SPEC, {"SPR-0005": bad})
        comparison = compare_promotion_regression_runs(primary, challenger)
        row = _row(comparison, "SPR-0005")
        assert row.primary_valid is False
        assert row.challenger_valid is False
        assert row.model_disagreement is False
        assert row.human_review_required is True


# ---------------------------------------------------------------------------
# Provenance compatibility: fail closed
# ---------------------------------------------------------------------------


class TestProvenanceCompatibility:
    def _tampered(self, run, **overrides):
        manifest = dict(run.manifest)
        manifest.update(overrides)
        return dataclasses.replace(run, manifest=manifest)

    @pytest.mark.parametrize(
        "field,value,code",
        [
            ("corpus_sha256", "0" * 64, "CORPUS_SHA256_MISMATCH"),
            ("corpus_version", 99, "CORPUS_VERSION_MISMATCH"),
            ("prompt_version", "9.9", "PROMPT_VERSION_MISMATCH"),
            ("prompt_sha256", "1" * 64, "PROMPT_SHA256_MISMATCH"),
            (
                "generation_parameters",
                {"temperature": 0.1, "max_tokens": 32768},
                "GENERATION_PARAMETER_MISMATCH",
            ),
            (
                "transport_parameters",
                {"request_timeout_seconds": 120.0},
                "REQUEST_TIMEOUT_MISMATCH",
            ),
        ],
    )
    def test_tampered_manifest_is_incompatible(self, field, value, code):
        primary, _ = _ideal_run(NEOTRON_SPEC)
        challenger, _ = _ideal_run(QWEN_SPEC)
        tampered = self._tampered(challenger, **{field: value})
        with pytest.raises(PromotionRegressionComparisonError, match=code):
            compare_promotion_regression_runs(primary, tampered)

    def test_non_completed_run_is_incompatible(self):
        primary, _ = _ideal_run(NEOTRON_SPEC)
        challenger, _ = _ideal_run(QWEN_SPEC)
        tampered = self._tampered(challenger, run_status="FAILED_PROVIDER")
        with pytest.raises(PromotionRegressionComparisonError, match="RUN_NOT_COMPLETED"):
            compare_promotion_regression_runs(primary, tampered)

    def test_case_order_mismatch_is_incompatible(self):
        primary, _ = _ideal_run(NEOTRON_SPEC)
        challenger, _ = _ideal_run(QWEN_SPEC)
        ids = list(challenger.manifest["case_ids"])
        ids[-1], ids[-2] = ids[-2], ids[-1]
        tampered = self._tampered(challenger, case_ids=ids)
        with pytest.raises(PromotionRegressionComparisonError, match="CASE_ID_ORDER_MISMATCH"):
            compare_promotion_regression_runs(primary, tampered)

    def test_soft_mode_reports_issues_without_raising(self):
        primary, _ = _ideal_run(NEOTRON_SPEC)
        challenger, _ = _ideal_run(QWEN_SPEC)
        tampered = self._tampered(challenger, corpus_sha256="0" * 64)
        comparison = compare_promotion_regression_runs(
            primary, tampered, require_compatible=False
        )
        assert comparison.provenance_compatible is False
        assert any("CORPUS_SHA256_MISMATCH" in i for i in comparison.provenance_issues)


# ---------------------------------------------------------------------------
# Artifacts
# ---------------------------------------------------------------------------


class TestComparisonArtifacts:
    def test_save_comparison_writes_json_and_md(self, tmp_path: Path):
        primary, _ = _ideal_run(NEOTRON_SPEC)
        challenger, _ = _ideal_run(QWEN_SPEC, {"SPR-0013": _resp("MATCH")})
        comparison = compare_promotion_regression_runs(primary, challenger)
        comp_dir = save_comparison(comparison, output_dir=tmp_path)
        assert (comp_dir / "comparison.json").exists()
        assert (comp_dir / "comparison.md").exists()
        data = json.loads((comp_dir / "comparison.json").read_text(encoding="utf-8"))
        assert data["benchmark_kind"] == "semantic_promotion_regression_comparison"
        assert data["no_winner_declared"] is True
        assert data["challenger_run"]["promotion_gate_passed"] is False
        assert "SPR-0013" in data["human_review_case_ids"]
        md = (comp_dir / "comparison.md").read_text(encoding="utf-8")
        assert "No winner declared" in md
        assert "Mandatory human-review list" in md
        assert "SPR-0013" in md
        assert "positive authority expansion" in md.lower() or "Expansion" in md

    def test_comparison_roundtrip_from_disk(self, tmp_path: Path):
        from product_intelligence.evaluation.semantic.promotion_regression import (
            load_run,
        )

        primary, _ = _ideal_run(NEOTRON_SPEC, {"SPR-0008": _resp("UNCERTAIN")})
        challenger, _ = _ideal_run(QWEN_SPEC, {"SPR-0008": _resp("MATCH")})
        d_p = save_run(primary, output_dir=tmp_path)
        d_c = save_run(challenger, output_dir=tmp_path)
        loaded_p = load_run(d_p)
        loaded_c = load_run(d_c)
        comparison = compare_promotion_regression_runs(loaded_p, loaded_c)
        row = _row(comparison, "SPR-0008")
        assert row.positive_authority_expansion is True
        assert row.human_review_required is True
        assert comparison.aggregates["positive_authority_expansion_count"] == 1
