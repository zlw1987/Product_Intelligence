"""Tests over the shipped evaluation corpus itself.

These check the corpus as data: that it loads, that the approved seed
identities are present with their provenance, that the adversarial coverage the
benchmark was built for is intact, and that real and synthetic cases cannot be
confused for one another.

Nothing here tests resolver behaviour. There is no resolver.
"""

from __future__ import annotations

import dataclasses
from datetime import date
from pathlib import Path

import pytest

from product_intelligence.domain import ResearchRequest
from product_intelligence.evaluation import (
    REQUIRED_SYNTHETIC_CHALLENGE_TAGS,
    AuthoritativeProvenance,
    CaseKind,
    ChallengeTag,
    EvaluationCorpus,
    ExpectedResolution,
    ProvenanceKind,
    SyntheticProvenance,
    default_corpus_paths,
    load_corpus,
)
from product_intelligence.evaluation.vocabulary import ABSTAINING_RESOLUTIONS

# The seed identities approved for PRODUCT-INTEL.0B, each independently checked
# against a manufacturer-controlled source before the corpus was written. They
# are repeated here rather than read from the corpus: a test that derived its
# expectations from the file under test would pass no matter what the file said.
APPROVED_SEED_IDENTITIES = {
    "Samsung": "MZ-QL23T800",
    "Micron": "MTFDKCC3T8TFR-1BC1ZABYY",
    "Intel": "PK8071305072902",
    "Kingston": "KSM48R40BS4TMM-32HMR",
    "Broadcom": "BCM957504-N425G",
}


@pytest.fixture(scope="module")
def corpus() -> EvaluationCorpus:
    return load_corpus()


def test_every_default_corpus_file_exists() -> None:
    for path in default_corpus_paths():
        assert path.is_file(), f"missing corpus file {path}"


def test_corpus_loads_and_is_not_empty(corpus: EvaluationCorpus) -> None:
    assert len(corpus) == len(corpus.cases)
    assert corpus.real_verified
    assert corpus.synthetic
    assert len(corpus.real_verified) + len(corpus.synthetic) == len(corpus)


def test_case_ids_are_unique(corpus: EvaluationCorpus) -> None:
    ids = [case.case_id for case in corpus]

    assert len(set(ids)) == len(ids)


def test_approved_seed_identities_are_present(corpus: EvaluationCorpus) -> None:
    real = {
        (case.expectation.manufacturer, case.expectation.canonical_manufacturer_part_number)
        for case in corpus.real_verified
    }

    assert set(APPROVED_SEED_IDENTITIES.items()) <= real


def test_real_cases_expect_an_exact_identity(corpus: EvaluationCorpus) -> None:
    for case in corpus.real_verified:
        assert case.expectation.resolution is ExpectedResolution.EXACT_IDENTITY
        assert case.expectation.canonical_manufacturer_part_number
        assert case.expectation.manufacturer


def test_real_cases_carry_authoritative_provenance(corpus: EvaluationCorpus) -> None:
    for case in corpus.real_verified:
        provenance = case.provenance

        assert isinstance(provenance, AuthoritativeProvenance), case.case_id
        assert provenance.kind is ProvenanceKind.MANUFACTURER
        assert provenance.source_name
        assert provenance.source_url.startswith("https://")
        assert provenance.verification_note
        assert isinstance(provenance.verified_on, date)


def test_synthetic_cases_cannot_masquerade_as_real(corpus: EvaluationCorpus) -> None:
    """A constructed case must never carry source-shaped provenance.

    A fabricated citation is worse than no citation: a later reviewer would
    trust it. The construction note is the honest alternative.
    """
    for case in corpus.synthetic:
        provenance = case.provenance

        assert case.case_kind is CaseKind.SYNTHETIC
        assert isinstance(provenance, SyntheticProvenance), case.case_id
        assert provenance.kind is ProvenanceKind.SYNTHETIC_CONSTRUCTION
        assert provenance.construction
        assert not hasattr(provenance, "source_url")
        assert not hasattr(provenance, "verification_note")


def test_synthetic_derivations_reference_real_cases(corpus: EvaluationCorpus) -> None:
    for case in corpus.synthetic:
        for referenced in case.provenance.derived_from_case_ids:
            assert referenced in corpus.by_id, case.case_id


def test_every_required_challenge_class_is_exercised(corpus: EvaluationCorpus) -> None:
    """Coverage is the point of the synthetic set.

    A benchmark that quietly loses a challenge class stops measuring the
    failure it was built for, and nothing else would notice.
    """
    counts = corpus.challenge_tag_counts(corpus.synthetic)
    uncovered = sorted(
        tag.value for tag in REQUIRED_SYNTHETIC_CHALLENGE_TAGS if counts[tag] == 0
    )

    assert not uncovered, f"synthetic corpus exercises no case for {uncovered}"


def test_challenge_tags_are_from_the_controlled_vocabulary(
    corpus: EvaluationCorpus,
) -> None:
    for case in corpus:
        assert case.challenge_tags
        for tag in case.challenge_tags:
            assert isinstance(tag, ChallengeTag)


def test_negative_assertions_are_internally_consistent(
    corpus: EvaluationCorpus,
) -> None:
    """A case may not forbid the identity it expects."""
    for case in corpus:
        forbidden = case.expectation.must_not_resolve_to
        canonical = case.expectation.canonical_manufacturer_part_number

        assert len(set(forbidden)) == len(forbidden), case.case_id
        assert canonical not in forbidden, case.case_id


def test_abstaining_cases_claim_no_canonical_identity(
    corpus: EvaluationCorpus,
) -> None:
    """Expecting abstention and naming the answer would contradict itself."""
    for case in corpus:
        if case.expectation.resolution not in ABSTAINING_RESOLUTIONS:
            continue

        assert case.expectation.canonical_manufacturer_part_number is None, case.case_id
        assert case.expectation.reason, case.case_id
        assert case.expectation.requires_abstention


def test_corpus_exercises_abstention_and_resolution_both(
    corpus: EvaluationCorpus,
) -> None:
    """A corpus of only-answerable cases would measure the wrong half.

    Correct abstention is a first-class outcome for this product, so each
    abstaining class has to be represented or the metrics defined in
    evaluation/README.md have nothing to score.
    """
    assert corpus.with_resolution(ExpectedResolution.EXACT_IDENTITY)
    for resolution in ABSTAINING_RESOLUTIONS:
        assert corpus.with_resolution(resolution), resolution.value


def test_forbidden_identities_are_recorded_for_the_confusable_cases(
    corpus: EvaluationCorpus,
) -> None:
    """False-positive prevention is why the near-miss cases exist."""
    for tag in (ChallengeTag.NEAR_MISS_MPN, ChallengeTag.ACCESSORY_CONFUSION):
        cases = corpus.with_challenge_tag(tag)

        assert cases, tag.value
        for case in cases:
            assert case.expectation.must_not_resolve_to, case.case_id


def test_every_case_input_is_a_valid_research_request(
    corpus: EvaluationCorpus,
) -> None:
    for case in corpus:
        assert isinstance(case.input.as_research_request(), ResearchRequest)


def test_case_inputs_are_stored_verbatim(corpus: EvaluationCorpus) -> None:
    """The corpus must not pre-clean what the system is supposed to handle.

    Surrounding whitespace is a challenge class; a corpus that stripped it on
    the way in would ship a case that tests nothing.
    """
    padded = corpus.with_challenge_tag(ChallengeTag.SURROUNDING_WHITESPACE)

    assert padded
    for case in padded:
        raw = case.input.manufacturer_part_number + case.input.description
        assert raw != raw.strip()
        assert case.input.as_research_request().manufacturer_part_number == (
            case.input.manufacturer_part_number.strip()
        )


def test_no_case_records_a_price_or_stock_claim(corpus: EvaluationCorpus) -> None:
    """Market prices are observations at a moment, not product properties.

    A price frozen into this corpus would fail a correct implementation for
    running later. Price evaluation belongs against timestamped listing
    snapshots — see evaluation/README.md.
    """
    field_names = {field.name for field in dataclasses.fields(type(corpus.cases[0].expectation))}

    assert not any(
        token in name
        for name in field_names
        for token in ("price", "cost", "stock", "availability", "currency")
    )


def test_readme_documents_the_evaluation_metrics() -> None:
    """The metric definitions are the deliverable; none of them is computed yet.

    They live in prose because there is no resolver to score, and a metric
    function with nothing to measure would be exactly the placeholder for
    unbuilt behaviour the testing strategy forbids. This guards the prose from
    quietly losing one.
    """
    readme = (
        Path(__file__).resolve().parents[2] / "evaluation" / "README.md"
    ).read_text(encoding="utf-8")

    for metric in (
        "Identity accuracy",
        "False-confidence rate",
        "Abstention correctness",
        "False-exact rate",
    ):
        assert metric in readme, metric


def test_loaded_cases_are_read_only(corpus: EvaluationCorpus) -> None:
    """Nothing being measured may edit the thing measuring it."""
    case = corpus.cases[0]

    with pytest.raises(dataclasses.FrozenInstanceError):
        case.case_id = "REWRITTEN"
    with pytest.raises(TypeError):
        corpus.by_id["REAL-0001"] = case
    assert isinstance(case.challenge_tags, tuple)
    assert isinstance(case.expectation.must_not_resolve_to, tuple)
