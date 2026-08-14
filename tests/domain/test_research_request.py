"""Contract tests for ResearchRequest."""

from __future__ import annotations

import dataclasses

import pytest

from product_intelligence.domain import DomainValidationError, ResearchRequest


def test_normal_request_is_representable() -> None:
    request = ResearchRequest(
        manufacturer_part_number="ABC123-X",
        description="24-port gigabit managed switch",
    )

    assert request.manufacturer_part_number == "ABC123-X"
    assert request.description == "24-port gigabit managed switch"
    assert request.has_manufacturer_part_number
    assert request.has_description


def test_surrounding_whitespace_is_stripped() -> None:
    request = ResearchRequest(
        manufacturer_part_number="  ABC123-X \t\r\n",
        description="\n  24-port gigabit managed switch  ",
    )

    assert request.manufacturer_part_number == "ABC123-X"
    assert request.description == "24-port gigabit managed switch"


def test_interior_characters_are_preserved_exactly() -> None:
    """Only surrounding whitespace is touched.

    A part number that differs by one character may be a different product,
    so the contract must not rewrite the interior of the value. Normalization
    for matching purposes is a separate, later, deterministic step.
    """
    request = ResearchRequest(
        manufacturer_part_number=" ABC 123/X-1.5 ",
        description=" 1/2 in. brass  fitting ",
    )

    assert request.manufacturer_part_number == "ABC 123/X-1.5"
    assert request.description == "1/2 in. brass  fitting"


@pytest.mark.parametrize(
    ("mpn", "description"),
    [
        ("", ""),
        ("   ", ""),
        ("", "\t\n "),
        ("  ", "   "),
    ],
)
def test_completely_empty_input_is_rejected(mpn: str, description: str) -> None:
    with pytest.raises(DomainValidationError):
        ResearchRequest(manufacturer_part_number=mpn, description=description)


def test_part_number_alone_is_accepted() -> None:
    request = ResearchRequest(manufacturer_part_number="ABC123-X", description="")

    assert request.has_manufacturer_part_number
    assert not request.has_description


def test_description_alone_is_accepted() -> None:
    """A description-only request is valid input, not an error.

    It may only ever support a description-level answer, but that is a
    research outcome to be reported, not an intake failure.
    """
    request = ResearchRequest(
        manufacturer_part_number="",
        description="24-port gigabit managed switch",
    )

    assert not request.has_manufacturer_part_number
    assert request.has_description


@pytest.mark.parametrize("bad_value", [None, 123, b"ABC123", ["ABC123"]])
def test_non_string_input_is_rejected(bad_value: object) -> None:
    with pytest.raises(DomainValidationError):
        ResearchRequest(manufacturer_part_number=bad_value, description="anything")


def test_request_is_immutable() -> None:
    request = ResearchRequest(manufacturer_part_number="ABC123-X", description="switch")

    with pytest.raises(dataclasses.FrozenInstanceError):
        request.manufacturer_part_number = "SOMETHING-ELSE"


def test_request_carries_only_product_input_fields() -> None:
    """The canonical request is MPN + description and nothing else.

    Caller identity, transport details, and audit metadata belong to the
    intake boundary. Adding them here would let the research core behave
    differently depending on who called it.
    """
    field_names = {f.name for f in dataclasses.fields(ResearchRequest)}

    assert field_names == {"manufacturer_part_number", "description"}


def test_equal_input_produces_equal_requests() -> None:
    first = ResearchRequest(manufacturer_part_number=" ABC123 ", description=" switch ")
    second = ResearchRequest(manufacturer_part_number="ABC123", description="switch")

    assert first == second
