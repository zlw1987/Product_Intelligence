"""The 2A comparator against the 0B evaluation corpus.

The corpus is **test input here, never a runtime dependency**: the loader is
imported by this test module, not by `product_intelligence.research`, and a
guard test asserts that separation. Nothing in this file changes the corpus, and
nothing in it may: an expected answer moves only under the discipline in
`evaluation/README.md`, and "the implementation failed this case" is explicitly
not a reason.

Scope, stated once so these assertions are not over-read: the corpus records
which *product* is the correct answer, and this phase implements only the
part-number comparison primitive. So these tests assert what the comparator does
with the corpus's part-number strings — they do not claim the system resolves a
product, which it cannot: there is no search, no candidate source, and no
resolver.
"""

from __future__ import annotations

import pytest

from product_intelligence.domain import IdentityMatchType
from product_intelligence.evaluation.loader import load_corpus
from product_intelligence.evaluation.vocabulary import ExpectedResolution
from product_intelligence.research.identity import (
    compare_part_numbers,
    compare_request_to_candidate,
)

CORPUS = load_corpus()
CASES = tuple(CORPUS)


def _case_ids(case) -> str:
    return case.case_id


# ---------------------------------------------------------------------------
# Exact
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("case", CORPUS.real_verified, ids=_case_ids)
def test_every_verified_part_number_matches_itself_exactly(case) -> None:
    """The floor. A comparator that fails this is not comparing anything."""
    part_number = case.expectation.canonical_manufacturer_part_number

    assert compare_part_numbers(part_number, part_number).match_type is (
        IdentityMatchType.EXACT
    )


@pytest.mark.parametrize("case", CORPUS.real_verified, ids=_case_ids)
def test_a_verified_part_number_survives_the_canonical_request(case) -> None:
    """Through the real intake contract, which is how a request actually arrives."""
    request = case.input.as_research_request()
    canonical = case.expectation.canonical_manufacturer_part_number

    assert compare_request_to_candidate(request, canonical).match_type is (
        IdentityMatchType.EXACT
    )


@pytest.mark.parametrize(
    "case",
    [CORPUS.case("SYN-0002"), CORPUS.case("SYN-0013")],
    ids=_case_ids,
)
def test_a_part_number_only_case_still_compares(case) -> None:
    """A missing description is not a reason to weaken a part-number comparison."""
    request = case.input.as_research_request()

    assert compare_request_to_candidate(
        request, case.expectation.canonical_manufacturer_part_number
    ).match_type is IdentityMatchType.EXACT


def test_the_surrounding_whitespace_case_is_unaffected_by_its_padding() -> None:
    """SYN-0004: spaces, a tab, and a newline around both supplied values.

    The corpus stores them verbatim, so the case still tests something. The
    canonical request removes them, and the comparison is unchanged.
    """
    case = CORPUS.case("SYN-0004")
    request = case.input.as_research_request()

    assessment = compare_request_to_candidate(
        request, case.expectation.canonical_manufacturer_part_number
    )

    assert assessment.match_type is IdentityMatchType.EXACT
    assert assessment.requested_part_number == "PK8071305072902"


# ---------------------------------------------------------------------------
# Normalized exact
# ---------------------------------------------------------------------------


def test_the_punctuation_variant_case_qualifies_under_normalization() -> None:
    """SYN-0008 against REAL-0005's canonical part number.

    Lower case with the hyphen written as a space differs only by formatting the
    approved profile covers. The corpus is deliberately silent about the
    mechanism — it records only which product is right — so this asserts the
    mechanism the implementation chose, not a corpus expectation about it.

    This case is the whole evidential basis for the whitespace/hyphen
    equivalence, and 2A-FU1 kept it while withdrawing the substitutions it does
    *not* evidence: one case about one separator is not a licence to treat `_`,
    `/`, and `.` as interchangeable too.
    """
    case = CORPUS.case("SYN-0008")
    request = case.input.as_research_request()

    assessment = compare_request_to_candidate(
        request, case.expectation.canonical_manufacturer_part_number
    )

    assert assessment.match_type is IdentityMatchType.NORMALIZED_EXACT
    assert assessment.is_established
    assert assessment.normalized_requested_part_number == "BCM957504-N425G"


# ---------------------------------------------------------------------------
# Not established
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "case",
    [case for case in CASES if case.expectation.must_not_resolve_to],
    ids=_case_ids,
)
def test_no_forbidden_identity_is_reachable_by_part_number_comparison(case) -> None:
    """The corpus's own false-confidence trap, applied to this primitive.

    Every identity a case forbids as *the answer* must not be reachable by
    comparing part numbers — near misses, truncations, fictitious identities,
    crossed brands, and description-only requests alike. This is the assertion
    that would fail first if the normalization profile were widened carelessly.
    """
    request = case.input.as_research_request()

    for forbidden in case.expectation.must_not_resolve_to:
        assessment = compare_request_to_candidate(request, forbidden)

        assert not assessment.is_established, (
            f"{case.case_id}: comparing {assessment.requested_part_number!r} with "
            f"{forbidden!r} established a part-number identity the corpus forbids"
        )
        assert assessment.match_type is IdentityMatchType.UNKNOWN


def test_the_near_miss_case_does_not_become_the_verified_part_number() -> None:
    """SYN-0005: two trailing zeros written as the letter O.

    The single most expensive failure mode in the corpus, and the one a fuzzy
    comparator would fall for.
    """
    case = CORPUS.case("SYN-0005")
    request = case.input.as_research_request()

    assessment = compare_request_to_candidate(request, "MZ-QL23T800")

    assert assessment.match_type is IdentityMatchType.UNKNOWN
    assert (
        assessment.normalized_requested_part_number
        != assessment.normalized_candidate_part_number
    )


def test_the_partial_case_does_not_become_the_suffixed_part_number() -> None:
    """SYN-0007: the configuration suffix dropped at the hyphen.

    Removing separators must not remove the content after them, and containment
    is not identity.
    """
    case = CORPUS.case("SYN-0007")
    request = case.input.as_research_request()

    assessment = compare_request_to_candidate(request, "MTFDKCC3T8TFR-1BC1ZABYY")

    assert assessment.match_type is IdentityMatchType.UNKNOWN
    assert assessment.match_type is not IdentityMatchType.PARTIAL


@pytest.mark.parametrize(
    "case",
    [case for case in CASES if not case.input.manufacturer_part_number.strip()],
    ids=_case_ids,
)
def test_a_description_only_case_establishes_nothing(case) -> None:
    """However strong the description is, it is not part-number evidence."""
    request = case.input.as_research_request()

    for candidate in (
        "MZ-QL23T800",
        "MTFDKCC3T8TFR-1BC1ZABYY",
        "PK8071305072902",
    ):
        assert not compare_request_to_candidate(request, candidate).is_established


def test_the_conflicting_brand_case_is_unknown_rather_than_conflict() -> None:
    """SYN-0012: a verified memory part number against a processor's.

    The corpus expects the *system* to report a conflict, which is a conclusion
    drawn from part number and description together. The narrow comparator does
    not invent that conclusion from two strings; it reports that it established
    nothing.
    """
    case = CORPUS.case("SYN-0012")
    request = case.input.as_research_request()

    assessment = compare_request_to_candidate(request, "PK8071305072902")

    assert assessment.match_type is IdentityMatchType.UNKNOWN
    assert assessment.match_type is not IdentityMatchType.CONFLICT


def test_the_description_conflict_case_still_compares_its_part_number_truthfully() -> (
    None
):
    """SYN-0006: a verified part number paired with a contradicting description.

    The comparator sees one thing and says what it saw. Suppressing the match
    because a description it never read disagrees would make this primitive
    responsible for a conclusion it has no evidence for — and the conflict is
    still detectable by the later phase that holds both sides.
    """
    case = CORPUS.case("SYN-0006")
    request = case.input.as_research_request()

    assessment = compare_request_to_candidate(request, "MZ-QL23T800")

    assert assessment.match_type is IdentityMatchType.EXACT


@pytest.mark.parametrize(
    "case",
    [CORPUS.case("SYN-0009"), CORPUS.case("SYN-0011")],
    ids=_case_ids,
)
def test_a_fictitious_part_number_matches_nothing_verified(case) -> None:
    request = case.input.as_research_request()

    for real in CORPUS.real_verified:
        canonical = real.expectation.canonical_manufacturer_part_number
        assert not compare_request_to_candidate(request, canonical).is_established


# ---------------------------------------------------------------------------
# Cross-case sweeps
# ---------------------------------------------------------------------------


def test_the_verified_part_numbers_do_not_match_each_other() -> None:
    """Five distinct products stay five distinct identities."""
    part_numbers = [
        case.expectation.canonical_manufacturer_part_number
        for case in CORPUS.real_verified
    ]

    for left in part_numbers:
        for right in part_numbers:
            if left == right:
                continue
            assert not compare_part_numbers(left, right).is_established


@pytest.mark.parametrize(
    "case",
    [
        case
        for case in CASES
        if case.expectation.resolution is ExpectedResolution.EXACT_IDENTITY
        and case.input.manufacturer_part_number.strip()
    ],
    ids=_case_ids,
)
def test_every_exact_identity_case_that_supplies_a_part_number_is_established(
    case,
) -> None:
    """True of every such case in the corpus today, and asserted deliberately.

    It is not a rule the corpus format guarantees: a future `EXACT_IDENTITY`
    case could reach its answer through evidence other than the supplied part
    number, and that case would belong outside this sweep. Excluding it would be
    the correct response — weakening the comparator to keep the sweep passing
    would not.
    """
    request = case.input.as_research_request()

    assessment = compare_request_to_candidate(
        request, case.expectation.canonical_manufacturer_part_number
    )

    assert assessment.is_established, (
        f"{case.case_id}: {assessment.requested_part_number!r} did not establish "
        f"{case.expectation.canonical_manufacturer_part_number!r}"
    )


def test_the_corpus_still_loads_unchanged() -> None:
    """A blunt canary: neither 2A nor its follow-up edited benchmark truth."""
    assert len(CORPUS) == 19
    assert len(CORPUS.real_verified) == 5
    assert len(CORPUS.synthetic) == 14
