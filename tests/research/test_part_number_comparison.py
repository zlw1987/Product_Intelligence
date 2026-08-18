"""The deterministic part-number comparison primitive (2A, corrected in 2A-FU1).

Three groups, in the order they matter:

* what may be called an established identity (`EXACT`, `NORMALIZED_EXACT`);
* what must **not** be, which is most of this file — a comparator that is
  generous is worse than one that abstains, because the expensive failure this
  system can produce is a confident wrong match;
* what the result exposes, so a decision can be audited from its own values.
"""

from __future__ import annotations

import pytest

from product_intelligence.domain import (
    ESTABLISHED_MATCH_TYPES,
    IdentityMatchType,
    ResearchRequest,
)
from product_intelligence.research.identity import (
    PartNumberMatchAssessment,
    compare_part_numbers,
    compare_request_to_candidate,
    normalize_part_number,
)


# ---------------------------------------------------------------------------
# EXACT
# ---------------------------------------------------------------------------


def test_identical_part_numbers_are_exact() -> None:
    assessment = compare_part_numbers("ABC123-X", "ABC123-X")

    assert assessment.match_type is IdentityMatchType.EXACT
    assert assessment.is_established


def test_surrounding_whitespace_on_the_candidate_does_not_prevent_exact() -> None:
    """Boundary whitespace is the only rewriting EXACT tolerates.

    A request that arrived through `ResearchRequest` has already had it removed;
    a candidate extracted from somewhere untidy has not, and bringing the two to
    the same footing is canonicalization rather than normalization.
    """
    assessment = compare_part_numbers("ABC123-X", "  ABC123-X\n")

    assert assessment.match_type is IdentityMatchType.EXACT
    assert assessment.candidate_part_number == "ABC123-X"


def test_a_request_that_arrived_with_padding_still_compares_exactly() -> None:
    request = ResearchRequest(
        manufacturer_part_number="   ABC123-X  ", description="\t widget \n"
    )

    assessment = compare_request_to_candidate(request, "ABC123-X")

    assert assessment.match_type is IdentityMatchType.EXACT


@pytest.mark.parametrize(
    "requested, candidate",
    [
        ("ABC123-X", "abc123-x"),  # case differs
        ("ABC123-X", "ABC123X"),  # a boundary is present on one side only
        ("ABC123-X", "ABC123 X"),  # the same boundary, written differently
    ],
)
def test_formatting_differences_are_not_exact(requested: str, candidate: str) -> None:
    """None of these is EXACT, whatever the normalized comparison then says.

    Calling a normalized match "exact" would lose the one distinction the
    vocabulary exists to keep.
    """
    assert compare_part_numbers(requested, candidate).match_type is not (
        IdentityMatchType.EXACT
    )


# ---------------------------------------------------------------------------
# NORMALIZED_EXACT
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "requested, candidate",
    [
        ("abc123-x", "ABC123-X"),  # ASCII case only
        ("abc-123", "ABC-123"),  # ASCII case only
        ("ABC 123", "ABC-123"),  # whitespace against hyphen, same boundary
        ("ABC\t123", "ABC-123"),  # tab against hyphen, same boundary
        ("ABC  123", "ABC-123"),  # a whitespace run is still one boundary
        ("  abc 123  ", "ABC-123"),  # padding, case, and separator style
        ("A B-C 1", "A-B-C-1"),  # several boundaries, each written either way
    ],
)
def test_approved_formatting_variants_are_normalized_exact(
    requested: str, candidate: str
) -> None:
    """The whole approved equivalence: ASCII case, and how a boundary is written.

    Every pair here has the *same boundaries in the same places*; only the
    spelling differs.
    """
    assessment = compare_part_numbers(requested, candidate)

    assert assessment.match_type is IdentityMatchType.NORMALIZED_EXACT
    assert assessment.is_established


def test_the_punctuation_variant_from_the_corpus_is_normalized_exact() -> None:
    """The formatting case the corpus records (SYN-0008 against REAL-0005).

    Lower case with the hyphen written as a space is a formatting difference at
    the same structural boundary. The corpus is deliberately silent about *how*
    a resolver should reach the right answer; this asserts only what the
    primitive does with the two strings.

    It is also the *only* separator substitution the corpus evidences, which is
    why 2A-FU1 withdrew the other three (`_`, `/`, `.`) rather than keeping them
    on the strength of this one case.
    """
    assessment = compare_part_numbers("bcm957504 n425g", "BCM957504-N425G")

    assert assessment.match_type is IdentityMatchType.NORMALIZED_EXACT
    assert assessment.normalized_requested_part_number == "BCM957504-N425G"
    assert assessment.normalized_candidate_part_number == "BCM957504-N425G"


# ---------------------------------------------------------------------------
# Not established
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "requested, candidate, why",
    [
        ("ABC123-A", "ABC123-B", "one suffix character substituted"),
        ("ABC123", "ABC124", "one digit substituted"),
        ("ABC-123", "ABC-124", "one digit substituted, with separators"),
        ("ABC123", "ABC1234", "an extra trailing character"),
        ("ABC1234", "ABC123", "a missing trailing character"),
        ("MZ-QL23T800", "MZ-QL23T8OO", "zeros written as the letter O"),
        ("ABC123", "321CBA", "the same characters in another order"),
        ("ABC123", "XYZ789", "unrelated part numbers"),
    ],
)
def test_alphanumeric_differences_are_never_established(
    requested: str, candidate: str, why: str
) -> None:
    assessment = compare_part_numbers(requested, candidate)

    assert assessment.match_type is IdentityMatchType.UNKNOWN, why
    assert not assessment.is_established


@pytest.mark.parametrize(
    "requested, candidate",
    [
        ("MZ-QL23", "MZ-QL23T800"),  # a prefix of the candidate
        ("MTFDKCC3T8TFR", "MTFDKCC3T8TFR-1BC1ZABYY"),  # suffix dropped
        ("ABC123", "ABC123-X"),  # the shorter one is contained in the longer
    ],
)
def test_partial_and_truncated_part_numbers_are_not_established(
    requested: str, candidate: str
) -> None:
    """Containment is not identity, and 2A implements no partial matching.

    A prefix identifies a family at best. Classifying partial part-number
    overlap belongs to listing matching (3C); reaching for it here would raise
    recall by weakening identity, which is the trade the design forbids.
    """
    assessment = compare_part_numbers(requested, candidate)

    assert assessment.match_type is IdentityMatchType.UNKNOWN
    assert assessment.match_type is not IdentityMatchType.PARTIAL


@pytest.mark.parametrize(
    "requested, candidate",
    [
        ("ABC+123", "ABC123"),
        ("ABC#123", "ABC123"),
        ("ABC@123", "ABC123"),
        ("ABC:123", "ABC123"),
        ("ABC(123)", "ABC123"),
        ("ABC–123", "ABC-123"),  # en dash against hyphen-minus
    ],
)
def test_punctuation_outside_the_profile_keeps_two_values_apart(
    requested: str, candidate: str
) -> None:
    """No separator is deleted, and unlisted punctuation is not even structure."""
    assert compare_part_numbers(requested, candidate).match_type is (
        IdentityMatchType.UNKNOWN
    )


def test_a_separator_does_not_take_the_suffix_after_it_with_it() -> None:
    """The base part and its configuration suffix are different identities.

    This is the failure a careless "drop the punctuation" rule produces.
    """
    assessment = compare_part_numbers("ABC123/AM", "ABC123")

    assert assessment.match_type is IdentityMatchType.UNKNOWN
    assert assessment.normalized_requested_part_number == "ABC123/AM"
    assert assessment.normalized_candidate_part_number == "ABC123"


# ---------------------------------------------------------------------------
# PRODUCT-INTEL.2A-FU1: separator position is part of the identifier.
#
# The defect these cover: 2A deleted every approved separator wherever it
# appeared, so `AB-C123`, `ABC-123`, `ABC123`, and `A-B-C-1-2-3` all collapsed
# onto the key `ABC123` and were reported as the same part number. A false
# exact is the most expensive answer this system can produce, and five verified
# corpus part numbers are not evidence that separator position is globally
# irrelevant.
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "requested, candidate, why",
    [
        ("AB-C123", "ABC-123", "the same characters, the boundary moved"),
        ("ABC123", "ABC-123", "a boundary on one side only"),
        ("ABC-123", "ABC123", "a boundary on one side only, reversed"),
        ("ABC123", "A-B-C-1-2-3", "five boundaries against none"),
        ("ABC 123", "ABC123", "a whitespace boundary against none"),
        ("AB C123", "ABC-123", "both written loosely, boundaries in different places"),
    ],
)
def test_a_moved_or_missing_boundary_is_a_different_identifier(
    requested: str, candidate: str, why: str
) -> None:
    assessment = compare_part_numbers(requested, candidate)

    assert assessment.match_type is IdentityMatchType.UNKNOWN, why
    assert not assessment.is_established
    assert (
        assessment.normalized_requested_part_number
        != assessment.normalized_candidate_part_number
    )


@pytest.mark.parametrize(
    "requested, candidate",
    [
        ("ABC_123", "ABC-123"),
        ("ABC/123", "ABC-123"),
        ("ABC.123", "ABC-123"),
        ("ABC_123", "ABC/123"),
        ("ABC.123", "ABC/123"),
    ],
)
def test_the_withdrawn_separator_substitutions_no_longer_match(
    requested: str, candidate: str
) -> None:
    """`_`, `/`, and `.` are data in this profile, not spellings of a hyphen.

    2A treated all four separators as one interchangeable class on the strength
    of a single corpus case about whitespace and hyphens. Re-approving any of
    these needs its own evidence, per separator.
    """
    assert compare_part_numbers(requested, candidate).match_type is (
        IdentityMatchType.UNKNOWN
    )


def test_repeated_punctuation_is_not_quietly_collapsed() -> None:
    """No approved rule says a doubled hyphen is a single boundary.

    A whitespace *run* collapses because it is one boundary a typist spaced out;
    extending that to punctuation would be a new equivalence, so the
    conservative answer stands.
    """
    assessment = compare_part_numbers("ABC--123", "ABC-123")

    assert assessment.match_type is IdentityMatchType.UNKNOWN
    assert assessment.normalized_requested_part_number == "ABC--123"


@pytest.mark.parametrize(
    "requested, candidate",
    [
        (None, "ABC123"),
        ("", "ABC123"),
        ("   ", "ABC123"),
        ("ABC123", None),
        ("ABC123", ""),
        ("ABC123", "  \t "),
        (None, None),
        ("", ""),
    ],
)
def test_missing_part_number_evidence_is_not_established_and_does_not_raise(
    requested, candidate
) -> None:
    """Identity that could not be established is an outcome, not an error."""
    assessment = compare_part_numbers(requested, candidate)

    assert assessment.match_type is IdentityMatchType.UNKNOWN
    assert not assessment.is_established


@pytest.mark.parametrize(
    "requested, candidate",
    [
        ("-", "-"),
        ("-", "_"),
        ("---", "..."),
        ("   ", ""),
        ("/", "."),
        ("_", None),
    ],
)
def test_values_that_are_only_structure_can_never_match(
    requested, candidate
) -> None:
    """Two empty normalized keys must not compare equal.

    Without this rule, normalization itself would manufacture an established
    identity out of two values that carry no part number at all — including the
    case where both sides are literally the same character.
    """
    assessment = compare_part_numbers(requested, candidate)

    assert assessment.normalized_requested_part_number == ""
    assert assessment.match_type is IdentityMatchType.UNKNOWN


def test_a_mismatch_is_unknown_and_never_conflict() -> None:
    """Two different strings do not establish that evidence is incompatible.

    `CONFLICT` is a claim about evidence pointing at incompatible identities,
    which needs more than a string comparison. Reporting it here would be the
    narrow comparator inventing a semantic conclusion.
    """
    assessment = compare_part_numbers("KSM48R40BS4TMM-32HMR", "PK8071305072902")

    assert assessment.match_type is IdentityMatchType.UNKNOWN
    assert assessment.match_type is not IdentityMatchType.CONFLICT


def test_only_the_two_part_number_match_types_are_ever_returned() -> None:
    """A sweep, so a future outcome cannot appear without this failing."""
    produced = {
        compare_part_numbers(requested, candidate).match_type
        for requested, candidate in [
            ("ABC123", "ABC123"),
            ("abc 123", "ABC-123"),
            ("ABC123", "ABC124"),
            ("ABC123", None),
            (None, None),
            ("-", "-"),
        ]
    }

    assert produced <= {
        IdentityMatchType.EXACT,
        IdentityMatchType.NORMALIZED_EXACT,
        IdentityMatchType.UNKNOWN,
    }


# ---------------------------------------------------------------------------
# Requests
# ---------------------------------------------------------------------------


def test_a_part_number_only_request_is_comparable() -> None:
    request = ResearchRequest(manufacturer_part_number="ABC123-X", description="")

    assert compare_request_to_candidate(request, "ABC123-X").match_type is (
        IdentityMatchType.EXACT
    )


def test_a_description_only_request_cannot_establish_part_number_identity() -> None:
    """A description-only request is valid, and carries no part-number evidence.

    Nothing reads the description, infers a part number from it, or scores it:
    description semantics are not implemented anywhere in this phase.
    """
    request = ResearchRequest(
        manufacturer_part_number="",
        description="quad port 25GbE OCP 3.0 network adapter",
    )

    assessment = compare_request_to_candidate(request, "BCM957504-N425G")

    assert assessment.match_type is IdentityMatchType.UNKNOWN
    assert assessment.requested_part_number == ""
    assert not assessment.has_requested_part_number
    assert assessment.has_candidate_part_number


def test_a_matching_part_number_stays_exact_when_the_description_disagrees() -> None:
    """The semantic boundary this phase must not blur.

    The corpus records this shape (SYN-0006) as a conflict to be *reported* —
    a conclusion drawn from part number and description together. The
    part-number comparator has one input and truthfully reports what it
    compared; a comparator that guessed at the wider conclusion would be
    claiming knowledge it has no access to.
    """
    request = ResearchRequest(
        manufacturer_part_number="MZ-QL23T800",
        description="Samsung PM9A3 NVMe U.2 1.92TB enterprise SSD",
    )

    assessment = compare_request_to_candidate(request, "MZ-QL23T800")

    assert assessment.match_type is IdentityMatchType.EXACT


def test_a_comparison_requires_the_canonical_request_contract() -> None:
    with pytest.raises(TypeError):
        compare_request_to_candidate("ABC123-X", "ABC123-X")


def test_a_non_string_candidate_is_a_caller_defect() -> None:
    with pytest.raises(TypeError):
        compare_part_numbers("ABC123", 123)


# ---------------------------------------------------------------------------
# Auditability
# ---------------------------------------------------------------------------


def test_the_result_shows_both_values_and_both_normalized_keys() -> None:
    """A reviewer must be able to re-derive the decision from the result alone."""
    assessment = compare_part_numbers("  bcm957504 n425g ", "BCM957504-N425G")

    assert assessment.requested_part_number == "bcm957504 n425g"
    assert assessment.candidate_part_number == "BCM957504-N425G"
    assert assessment.normalized_requested_part_number == "BCM957504-N425G"
    assert assessment.normalized_candidate_part_number == "BCM957504-N425G"
    assert assessment.match_type is IdentityMatchType.NORMALIZED_EXACT


def test_a_mismatch_preserves_the_differing_normalized_keys() -> None:
    assessment = compare_part_numbers("MZ-QL23T800", "MZ-QL23T8OO")

    assert assessment.normalized_requested_part_number == "MZ-QL23T800"
    assert assessment.normalized_candidate_part_number == "MZ-QL23T8OO"
    assert (
        assessment.normalized_requested_part_number
        != assessment.normalized_candidate_part_number
    )


def test_a_structural_mismatch_is_visible_in_the_keys() -> None:
    """The 2A-FU1 auditability requirement, stated as a contrast.

    A reviewer reading only the two results can see that one pair describes the
    same identifier written two ways and the other does not.
    """
    matched = compare_part_numbers("bcm957504 n425g", "BCM957504-N425G")
    unmatched = compare_part_numbers("AB-C123", "ABC-123")

    assert (
        matched.normalized_requested_part_number
        == matched.normalized_candidate_part_number
        == "BCM957504-N425G"
    )
    assert unmatched.normalized_requested_part_number == "AB-C123"
    assert unmatched.normalized_candidate_part_number == "ABC-123"


def test_the_normalized_keys_are_what_the_public_normalizer_produces() -> None:
    """No second, private normalization exists behind the comparison."""
    for value in ("ABC 123", "abc-123", "ABC+123", "", "-"):
        assessment = compare_part_numbers(value, "ANYTHING")
        assert assessment.normalized_requested_part_number == normalize_part_number(
            value
        )


def test_an_assessment_is_immutable() -> None:
    """A recorded comparison must not be editable after the fact."""
    assessment = compare_part_numbers("ABC123", "ABC123")

    with pytest.raises(Exception):
        assessment.match_type = IdentityMatchType.UNKNOWN  # type: ignore[misc]


def test_the_assessment_carries_no_confidence_or_product_facts() -> None:
    """No score, no manufacturer, no product name, no family, no category.

    Confidence is a judgement about evidence quality, and a string comparison is
    not evidence quality: EXACT is not a synonym for HIGH. Product facts would
    have to come from a catalog this phase deliberately does not have.
    """
    fields = set(PartNumberMatchAssessment.__dataclass_fields__)

    assert fields == {
        "requested_part_number",
        "candidate_part_number",
        "normalized_requested_part_number",
        "normalized_candidate_part_number",
        "match_type",
    }


def test_established_means_the_same_thing_here_as_in_the_domain() -> None:
    """One definition of "established", read from the domain vocabulary."""
    for requested, candidate in [("ABC123", "ABC123"), ("abc 123", "ABC-123")]:
        assessment = compare_part_numbers(requested, candidate)
        assert assessment.is_established
        assert assessment.match_type in ESTABLISHED_MATCH_TYPES
