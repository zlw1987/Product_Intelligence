"""The normalization profile itself (PRODUCT-INTEL.2A, corrected in 2A-FU1).

Normalization is tested separately from comparison because it is the piece with
a real design decision in it: exactly which differences are formatting, and
exactly which are structure. Testing it only through `compare_part_numbers`
would prove that two strings matched without proving *why*, and the why is what
stops the profile from widening one convenient character at a time.

2A-FU1 narrowed the profile. The original version deleted every approved
separator wherever it appeared, which discarded separator *position* and made
`AB-C123` and `ABC-123` the same key. The key now preserves structure, so the
tests below assert what a key looks like, not merely which pairs collide.
"""

from __future__ import annotations

import pytest

from product_intelligence.research.identity import (
    ASCII_WHITESPACE,
    CANONICAL_SEPARATOR,
    PRESERVED_SEPARATORS,
    STRUCTURAL_CHARACTERS,
    normalize_part_number,
)


def test_the_structural_character_set_is_exactly_the_approved_profile() -> None:
    """The sets are closed. Widening one is a decision, not a side effect."""
    assert ASCII_WHITESPACE == set(" \t\n\r\f\v")
    assert CANONICAL_SEPARATOR == "-"
    assert PRESERVED_SEPARATORS == {"_", "/", "."}
    assert STRUCTURAL_CHARACTERS == ASCII_WHITESPACE | {"-", "_", "/", "."}


def test_surrounding_whitespace_is_removed() -> None:
    assert normalize_part_number("  ABC-123 \n") == "ABC-123"


def test_ascii_letters_fold_to_upper_case() -> None:
    assert normalize_part_number("abc123x") == "ABC123X"


# ---------------------------------------------------------------------------
# Structure is preserved (PRODUCT-INTEL.2A-FU1)
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "value, expected",
    [
        ("ABC123", "ABC123"),  # no boundary
        ("ABC-123", "ABC-123"),  # hyphen boundary, kept where it is
        ("AB-C123", "AB-C123"),  # the same characters, a different boundary
        ("A-B-C-1-2-3", "A-B-C-1-2-3"),  # five boundaries, all kept
        ("ABC--123", "ABC--123"),  # repeated punctuation is not collapsed
        ("ABC123-A", "ABC123-A"),  # suffix kept, boundary kept
    ],
)
def test_the_key_keeps_the_identifier_structure(value: str, expected: str) -> None:
    """A separator is never deleted, and never moves.

    The 2A-FU1 defect in one assertion: under the old profile every value here
    keyed to `ABC123` or `ABC123A`, so a part number with a boundary and one
    without were indistinguishable.
    """
    assert normalize_part_number(value) == expected


@pytest.mark.parametrize(
    "value, expected",
    [
        ("ABC_123", "ABC_123"),
        ("ABC/123", "ABC/123"),
        ("ABC.123", "ABC.123"),
        ("ABC_123/AM.1", "ABC_123/AM.1"),
    ],
)
def test_the_preserved_separators_are_data(value: str, expected: str) -> None:
    """`_`, `/`, and `.` are kept verbatim and never become a hyphen.

    2A treated all four separators as one interchangeable class. The corpus
    evidences one substitution (whitespace against hyphen) and five verified
    part numbers cannot show that every manufacturer treats every separator as
    decorative, so the other three were withdrawn.
    """
    assert normalize_part_number(value) == expected


# ---------------------------------------------------------------------------
# The one approved formatting equivalence
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "value",
    ["ABC 123", "ABC\t123", "ABC  123", "ABC\n123", "abc 123"],
)
def test_an_internal_whitespace_run_becomes_one_canonical_separator(
    value: str,
) -> None:
    """The single equivalence the corpus evidences, and nothing more.

    A run collapses because `ABC  123` and `ABC 123` are the same identifier
    with a typist's extra space. What the run does *not* do is vanish: the
    boundary it marks survives as a hyphen.
    """
    assert normalize_part_number(value) == "ABC-123"


def test_whitespace_around_punctuation_is_not_quietly_merged() -> None:
    """Three boundaries written, three boundaries kept.

    Deciding that `ABC - 123` is one boundary would need a rule about padded
    separators that no phase has approved. The conservative answer is that the
    two values differ.
    """
    assert normalize_part_number("ABC - 123") == "ABC---123"
    assert normalize_part_number("ABC - 123") != normalize_part_number("ABC-123")


# ---------------------------------------------------------------------------
# Everything else is data
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "value, expected",
    [
        ("ABC+123", "ABC+123"),
        ("ABC#123", "ABC#123"),
        ("ABC@123", "ABC@123"),
        ("ABC:123", "ABC:123"),
        ("ABC(123)", "ABC(123)"),
        ("ABC,123", "ABC,123"),
        ("ABC*123", "ABC*123"),
        ("ABC%123", "ABC%123"),
        ("ABC&123", "ABC&123"),
        ("ABC'123", "ABC'123"),
        ("ABC–123", "ABC–123"),
    ],
)
def test_punctuation_outside_the_profile_is_kept(value: str, expected: str) -> None:
    """Removing every non-alphanumeric character would be the wrong rule.

    The last case is an en dash, not a hyphen-minus: a character that *looks*
    like the canonical separator is not one, because approving it would be a
    Unicode equivalence decision no phase has taken.
    """
    assert normalize_part_number(value) == expected


def test_letters_and_digits_are_never_removed() -> None:
    assert normalize_part_number("MZ-QL23T800") == "MZ-QL23T800"


def test_characters_are_never_reordered() -> None:
    assert normalize_part_number("ABC123") != normalize_part_number("321CBA")


@pytest.mark.parametrize(
    "left, right",
    [
        ("ABC123", "ABC124"),  # one digit substituted
        ("ABC123", "ABD123"),  # one letter substituted
        ("MZ-QL23T800", "MZ-QL23T8OO"),  # zero / letter O transcription error
        ("ABC1", "ABCI"),  # one / letter I
        ("ABC1", "ABCl"),  # one / lower-case L
        ("ABC123", "ABC1234"),  # extra character
        ("ABC123", "ABC12"),  # missing character
    ],
)
def test_one_character_differences_survive_normalization(left: str, right: str) -> None:
    """No character-confusion table, no spelling correction, no fuzziness."""
    assert normalize_part_number(left) != normalize_part_number(right)


def test_non_ascii_code_points_inside_the_identifier_are_preserved_exactly() -> None:
    """No broad compatibility transform runs over an identifier.

    Each of these is a character a compatibility normalization such as NFKC
    would rewrite or expand. Part numbers are identifiers, and merging code
    points whose equivalence nobody approved is how a comparator starts matching
    things that are not the same.

    Surrounding whitespace is the one exception, and it is not this rule's
    business: boundary handling is `str.strip()`, the same Unicode-aware
    operation `ResearchRequest` applies.
    """
    for value in ("ABC１２３", "ABC①", "ABCß", "İABC"):
        assert normalize_part_number(value) == value


def test_a_non_ascii_space_inside_the_identifier_is_not_a_separator() -> None:
    """Only ASCII whitespace is the approved separator form.

    A non-breaking space is kept as data, so a part number written with one does
    not normalize onto its ASCII-hyphen spelling. That is the conservative
    direction: the failure is abstention, not a false match.
    """
    assert normalize_part_number("ABC 123") == "ABC 123"
    assert normalize_part_number("ABC 123") != normalize_part_number("ABC-123")


def test_boundary_stripping_follows_the_research_request_contract() -> None:
    """`str.strip()` semantics, which remove Unicode whitespace at the edges."""
    assert normalize_part_number("  ABC-123  ") == "ABC-123"


def test_case_folding_does_not_expand_or_rewrite_non_ascii_characters() -> None:
    """`str.upper()` would turn one character into two here; this must not."""
    assert normalize_part_number("ß") == "ß"
    assert len(normalize_part_number("straße")) == len("straße")


@pytest.mark.parametrize(
    "value",
    [None, "", "   ", "\t\n", "-", "---", "_", "/", ".", "-_/.", " - "],
)
def test_a_value_that_is_only_structure_has_no_part_number_to_compare(value) -> None:
    """An empty key is what stops two such values from being compared.

    Structure with nothing attached to it is not a part number, however many
    characters it has.
    """
    assert normalize_part_number(value) == ""


def test_a_non_string_part_number_is_a_caller_defect() -> None:
    with pytest.raises(TypeError):
        normalize_part_number(12345)
