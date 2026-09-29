"""Promotion-regression corpus tests (PRODUCT-INTEL.SEMANTIC.PROMOTION-REGRESSION).

Offline tests for the production-shaped promotion-regression corpus:

* the corpus is SEPARATE from the frozen 64-case qualification corpus and
  does not collide with it;
* the frozen qualification corpus and prompt v1.1 are byte-identical to
  their frozen fingerprints (this phase must not move them);
* every case realizes its declared deterministic state under the REAL
  frozen authority chain (assess_listing_identity) and its declared
  semantic-call expectation under the frozen eligibility rules;
* the loader fails closed on structural defects.

No live network/model calls. No production files modified.
"""

from __future__ import annotations

import copy
import json
from pathlib import Path

import pytest

from product_intelligence.evaluation.semantic.promotion_regression import (
    PROMOTION_REGRESSION_CATEGORIES,
    PromotionRegressionCaseError,
    PromotionRegressionCorpusError,
    assess_case,
    load_promotion_regression_corpus,
    semantic_call_is_expected,
)

REPO_ROOT = Path(__file__).resolve().parents[3]
PROMOTION_CORPUS_PATH = (
    REPO_ROOT / "evaluation" / "semantic_promotion_regression" / "cases.json"
)
FROZEN_QUALIFICATION_CORPUS_PATH = (
    REPO_ROOT / "evaluation" / "semantic_corpus" / "cases.json"
)

# Frozen fingerprints from the approved FULL qualification (recorded in
# STATUS and locked by tests/semantic/test_contract_sharing.py).
FROZEN_FULL_PROMPT_SHA256 = (
    "f50e5584659f953ce73a97ccc8bc1ff487fbeeb37e2e0a72e52210613aeab1ff"
)
FROZEN_CORPUS_SHA256 = (
    "3c21d6fcd4eefa5cc383792abfd9308bd5c03315834c8ffdffd0f6a2b3619ca1"
)


# ---------------------------------------------------------------------------
# Corpus identity and separation from the frozen qualification corpus
# ---------------------------------------------------------------------------


def test_corpus_file_is_outside_the_python_package() -> None:
    """Evaluation data stays reviewable reference data, like the
    qualification corpus."""
    assert PROMOTION_CORPUS_PATH.is_file()
    assert "product_intelligence" not in PROMOTION_CORPUS_PATH.parts


def test_corpus_loads() -> None:
    corpus = load_promotion_regression_corpus()
    assert corpus.corpus_version == 1
    assert len(corpus.cases) == 22


def test_case_ids_are_unique_and_prefixed_spr() -> None:
    corpus = load_promotion_regression_corpus()
    ids = [c.case_id for c in corpus.cases]
    assert len(set(ids)) == len(ids)
    for cid in ids:
        assert cid.startswith("SPR-")
        assert len(cid) == 8


def test_every_category_covered() -> None:
    corpus = load_promotion_regression_corpus()
    present = {c.category for c in corpus.cases}
    assert present == set(PROMOTION_REGRESSION_CATEGORIES)
    for case in corpus.cases:
        assert case.category_name == PROMOTION_REGRESSION_CATEGORIES[case.category]


def test_called_cases_cover_all_three_expected_decisions() -> None:
    corpus = load_promotion_regression_corpus()
    decisions = {
        c.expected_semantic_decision for c in corpus.cases if c.expected_semantic_call
    }
    assert decisions == {"MATCH", "NO_MATCH", "UNCERTAIN"}


def test_no_id_collision_with_frozen_qualification_corpus() -> None:
    """The promotion-regression corpus must not reuse or shadow a single
    frozen qualification case ID."""
    promotion_ids = {
        c.case_id for c in load_promotion_regression_corpus().cases
    }
    from product_intelligence.evaluation.semantic.loader import load_corpus

    qualification_ids = {c.case_id for c in load_corpus().cases}
    assert promotion_ids.isdisjoint(qualification_ids)
    assert promotion_ids


def test_frozen_qualification_corpus_is_byte_identical() -> None:
    """This phase must NOT modify the frozen 64-case qualification corpus."""
    from product_intelligence.evaluation.semantic.loader import load_corpus
    from product_intelligence.evaluation.semantic.runner import (
        _compute_corpus_sha256,
    )

    assert _compute_corpus_sha256(load_corpus()) == FROZEN_CORPUS_SHA256


def test_frozen_qualification_prompt_is_unchanged() -> None:
    """Prompt v1.1 must be byte-identical to the frozen qualification
    fingerprint: no prompt wording changes, no model-specific additions."""
    from product_intelligence.evaluation.semantic.loader import load_corpus
    from product_intelligence.evaluation.semantic.runner import (
        BenchmarkRunConfig,
        _compute_prompt_sha256,
    )
    from product_intelligence.evaluation.semantic.transport import (
        FakeSemanticModelTransport,
    )

    corpus = load_corpus()
    config = BenchmarkRunConfig(
        provider="amax",
        model="nemotron-3-super",
        case_selection="FULL",
        transport=FakeSemanticModelTransport(),
    )
    assert _compute_prompt_sha256(tuple(corpus.cases), config) == FROZEN_FULL_PROMPT_SHA256


def test_frozen_qualification_case_count_unchanged() -> None:
    from product_intelligence.evaluation.semantic.loader import load_corpus

    assert len(load_corpus().cases) == 64


# ---------------------------------------------------------------------------
# Every case realizes its declared production shape
# ---------------------------------------------------------------------------


def test_every_case_realizes_its_declared_deterministic_state() -> None:
    """The frozen authority chain must reproduce each case's declared
    deterministic state; a case that does not is defective and fails
    closed in the runner."""
    corpus = load_promotion_regression_corpus()
    for case in corpus.cases:
        assessment = assess_case(case)  # raises on mismatch
        expected = case.expected_deterministic
        assert assessment.decision.value == expected.decision
        assert (
            assessment.rejection_reason.value
            if assessment.rejection_reason is not None
            else None
        ) == expected.rejection_reason
        assert assessment.candidate_evidence_source.value == expected.evidence_source
        assert assessment.match_type.value == expected.match_type


def test_every_case_conforms_to_frozen_eligibility_rules() -> None:
    """The declared semantic-call expectation must equal what the frozen
    FU3B eligibility states + usable-evidence gate actually produce."""
    corpus = load_promotion_regression_corpus()
    for case in corpus.cases:
        assessment = assess_case(case)
        assert semantic_call_is_expected(assessment) is case.expected_semantic_call


@pytest.mark.parametrize(
    "case_id,category",
    [
        ("SPR-0001", "A"),
        ("SPR-0002", "A"),
        ("SPR-0003", "B"),
        ("SPR-0004", "B"),
        ("SPR-0005", "C"),
        ("SPR-0006", "C"),
        ("SPR-0007", "D"),
        ("SPR-0008", "D"),
        ("SPR-0009", "E"),
        ("SPR-0010", "E"),
        ("SPR-0011", "F"),
        ("SPR-0012", "F"),
        ("SPR-0013", "G"),
        ("SPR-0014", "G"),
        ("SPR-0015", "G"),
        ("SPR-0016", "G"),
        ("SPR-0017", "H"),
        ("SPR-0018", "H"),
        ("SPR-0019", "H"),
        ("SPR-0020", "I"),
        ("SPR-0021", "I"),
        ("SPR-0022", "J"),
    ],
)
def test_case_shape_by_category(case_id: str, category: str) -> None:
    """Spot the production shape each case must have."""
    corpus = load_promotion_regression_corpus()
    case = corpus.get_case(case_id)
    assert case.category == category
    assessment = assess_case(case)
    if category == "A":
        assert assessment.decision.value == "ACCEPTED"
        assert case.expected_semantic_call is False
    elif category == "B":
        assert assessment.decision.value == "REJECTED"
        assert assessment.rejection_reason.value == "MPN_MISMATCH"
        assert case.expected_semantic_call is False
    elif category == "F":
        assert case.expected_semantic_call is False
    else:
        assert case.expected_semantic_call is True
        assert case.expected_semantic_decision in ("MATCH", "NO_MATCH", "UNCERTAIN")
    if category in ("G", "H"):
        assert case.match_is_unsafe is True
    if category == "B":
        assert case.match_is_unsafe is False  # protected by the no-override gate


def test_smq_error_cases_not_copied() -> None:
    """Category I cases must be GENERAL contracts, not copies of the known
    SMQ-0053 / SMQ-0062 qualification cases (which this phase must not
    tune to)."""
    corpus = load_promotion_regression_corpus()
    for case in corpus.cases:
        if case.category != "I":
            continue
        text = json.dumps(
            {
                "case_id": case.case_id,
                "title": case.candidate_product_title,
                "mpn": case.candidate_mpn_field,
                "sku": case.candidate_sku,
                "target_mpn": case.target_mpn,
                "target_description": case.target_description,
                "reason": case.critical_reason,
            },
            ensure_ascii=False,
        )
        # The frozen error cases' distinctive literals must not appear.
        assert "SMQ-0053" not in text
        assert "SMQ-0062" not in text
        assert "SYN-Prod-X500" not in text
        assert "SYN-UNIT-789" not in text
        assert "Widget" not in text
        assert "Complete System" not in text
        assert "Advanced Features" not in text


# ---------------------------------------------------------------------------
# Loader fail-closed behavior
# ---------------------------------------------------------------------------


def _corpus_dict() -> dict:
    with open(PROMOTION_CORPUS_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def _write(tmp_path: Path, data: dict) -> Path:
    path = tmp_path / "cases.json"
    path.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
    return path


def test_loader_missing_file_fails_closed(tmp_path: Path) -> None:
    with pytest.raises(PromotionRegressionCorpusError):
        load_promotion_regression_corpus(tmp_path / "nope.json")


def test_loader_invalid_json_fails_closed(tmp_path: Path) -> None:
    path = tmp_path / "cases.json"
    path.write_text("{not json", encoding="utf-8")
    with pytest.raises(PromotionRegressionCorpusError):
        load_promotion_regression_corpus(path)


def test_loader_wrong_benchmark_kind_fails_closed(tmp_path: Path) -> None:
    data = _corpus_dict()
    data["benchmark_kind"] = "semantic_model_qualification"
    with pytest.raises(PromotionRegressionCorpusError):
        load_promotion_regression_corpus(_write(tmp_path, data))


def test_loader_duplicate_case_id_fails_closed(tmp_path: Path) -> None:
    data = _corpus_dict()
    dup = copy.deepcopy(data["cases"][0])
    data["cases"].append(dup)
    with pytest.raises(PromotionRegressionCorpusError, match="Duplicate case_id"):
        load_promotion_regression_corpus(_write(tmp_path, data))


def test_loader_smq_prefix_fails_closed(tmp_path: Path) -> None:
    data = _corpus_dict()
    data["cases"][0]["case_id"] = "SMQ-0999"
    with pytest.raises(PromotionRegressionCorpusError, match="SPR-"):
        load_promotion_regression_corpus(_write(tmp_path, data))


def test_loader_unknown_category_fails_closed(tmp_path: Path) -> None:
    data = _corpus_dict()
    data["cases"][0]["category"] = "Z"
    with pytest.raises(PromotionRegressionCorpusError):
        load_promotion_regression_corpus(_write(tmp_path, data))


def test_loader_category_name_mismatch_fails_closed(tmp_path: Path) -> None:
    data = _corpus_dict()
    data["cases"][0]["category_name"] = "something_else"
    with pytest.raises(PromotionRegressionCorpusError):
        load_promotion_regression_corpus(_write(tmp_path, data))


def test_loader_call_without_decision_fails_closed(tmp_path: Path) -> None:
    data = _corpus_dict()
    for case in data["cases"]:
        if case["expected_semantic_call"]:
            case["expected_semantic_decision"] = None
            break
    with pytest.raises(PromotionRegressionCorpusError):
        load_promotion_regression_corpus(_write(tmp_path, data))


def test_loader_decision_without_call_fails_closed(tmp_path: Path) -> None:
    data = _corpus_dict()
    for case in data["cases"]:
        if not case["expected_semantic_call"]:
            case["expected_semantic_decision"] = "MATCH"
            break
    with pytest.raises(PromotionRegressionCorpusError):
        load_promotion_regression_corpus(_write(tmp_path, data))


def test_loader_unsafe_without_call_fails_closed(tmp_path: Path) -> None:
    data = _corpus_dict()
    for case in data["cases"]:
        if not case["expected_semantic_call"]:
            case["match_is_unsafe"] = True
            break
    with pytest.raises(PromotionRegressionCorpusError):
        load_promotion_regression_corpus(_write(tmp_path, data))


def test_loader_missing_category_coverage_fails_closed(tmp_path: Path) -> None:
    data = _corpus_dict()
    data["cases"] = [c for c in data["cases"] if c["category"] != "J"]
    with pytest.raises(PromotionRegressionCorpusError, match="category"):
        load_promotion_regression_corpus(_write(tmp_path, data))


def test_loader_missing_decision_coverage_fails_closed(tmp_path: Path) -> None:
    data = _corpus_dict()
    # Convert every called UNCERTAIN case to MATCH: category coverage stays
    # intact, but the corpus no longer expects the UNCERTAIN tier.
    for case in data["cases"]:
        if case["expected_semantic_call"] and case["expected_semantic_decision"] == "UNCERTAIN":
            case["expected_semantic_decision"] = "MATCH"
    with pytest.raises(PromotionRegressionCorpusError, match="UNCERTAIN"):
        load_promotion_regression_corpus(_write(tmp_path, data))


def test_loader_accepted_with_rejection_reason_fails_closed(tmp_path: Path) -> None:
    data = _corpus_dict()
    for case in data["cases"]:
        if case["expected_deterministic"]["decision"] == "ACCEPTED":
            case["expected_deterministic"]["rejection_reason"] = "MPN_MISMATCH"
            break
    with pytest.raises(PromotionRegressionCorpusError):
        load_promotion_regression_corpus(_write(tmp_path, data))


def test_loader_rejected_without_rejection_reason_fails_closed(tmp_path: Path) -> None:
    data = _corpus_dict()
    for case in data["cases"]:
        if case["expected_deterministic"]["decision"] == "REJECTED":
            case["expected_deterministic"]["rejection_reason"] = None
            break
    with pytest.raises(PromotionRegressionCorpusError):
        load_promotion_regression_corpus(_write(tmp_path, data))


def test_loader_bad_evidence_source_fails_closed(tmp_path: Path) -> None:
    data = _corpus_dict()
    data["cases"][0]["expected_deterministic"]["evidence_source"] = "GUESSWORK"
    with pytest.raises(PromotionRegressionCorpusError):
        load_promotion_regression_corpus(_write(tmp_path, data))


def test_loader_bad_provenance_fails_closed(tmp_path: Path) -> None:
    data = _corpus_dict()
    data["cases"][0]["provenance"] = "made_up"
    with pytest.raises(PromotionRegressionCorpusError):
        load_promotion_regression_corpus(_write(tmp_path, data))


def test_defective_case_fails_closed_in_runner(tmp_path: Path) -> None:
    """A case whose declared deterministic state is NOT realized by the
    frozen authority chain must abort the run with the dedicated
    fail-closed error - a promotion-regression case whose production
    shape is wrong measures nothing."""
    from product_intelligence.evaluation.semantic.promotion_regression import (
        run_promotion_regression,
        get_authorized_model_spec,
    )
    from product_intelligence.semantic.transport import FakeSemanticModelTransport

    data = _corpus_dict()
    # Break SPR-0001's declared state: the real matcher will produce
    # ACCEPTED/EXACT, not the mutated declaration.
    for case in data["cases"]:
        if case["case_id"] == "SPR-0001":
            case["expected_deterministic"]["match_type"] = "NORMALIZED_EXACT"
            break
    broken_corpus = load_promotion_regression_corpus(_write(tmp_path, data))
    spec = get_authorized_model_spec("amax", "nemotron-3-super")
    with pytest.raises(PromotionRegressionCaseError):
        run_promotion_regression(spec, FakeSemanticModelTransport(), corpus=broken_corpus)
