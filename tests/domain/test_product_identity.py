"""Contract tests for ProductIdentity."""

from __future__ import annotations

import pytest

from product_intelligence.domain import (
    ConfidenceLevel,
    DomainValidationError,
    IdentityMatchType,
    ProductIdentity,
)


def test_default_identity_is_unknown_and_invents_nothing() -> None:
    identity = ProductIdentity()

    assert identity.manufacturer is None
    assert identity.manufacturer_part_number is None
    assert identity.normalized_part_number is None
    assert identity.product_name is None
    assert identity.product_family is None
    assert identity.category is None
    assert identity.match_type is IdentityMatchType.UNKNOWN
    assert identity.confidence is ConfidenceLevel.UNKNOWN
    assert not identity.is_established


def test_blank_manufacturer_stays_absent_rather_than_becoming_empty_text() -> None:
    identity = ProductIdentity(manufacturer="   ", manufacturer_part_number="ABC123")

    assert identity.manufacturer is None
    assert identity.manufacturer_part_number == "ABC123"


def test_supplied_values_are_kept_verbatim_after_trimming() -> None:
    identity = ProductIdentity(
        manufacturer=" Acme Industrial ",
        manufacturer_part_number=" ABC123-X ",
        normalized_part_number="ABC123X",
        product_name="Acme 24-port switch",
        product_family="Acme 2400 series",
        category="network switch",
        match_type=IdentityMatchType.EXACT,
        confidence=ConfidenceLevel.HIGH,
    )

    assert identity.manufacturer == "Acme Industrial"
    assert identity.manufacturer_part_number == "ABC123-X"
    assert identity.normalized_part_number == "ABC123X"
    assert identity.is_established


@pytest.mark.parametrize(
    "match_type",
    [
        IdentityMatchType.PARTIAL,
        IdentityMatchType.DESCRIPTION_ONLY,
        IdentityMatchType.CONFLICT,
        IdentityMatchType.UNKNOWN,
    ],
)
def test_weaker_matches_do_not_count_as_established_identity(
    match_type: IdentityMatchType,
) -> None:
    """Semantic or partial similarity is not exact product identity."""
    identity = ProductIdentity(
        manufacturer_part_number="ABC123-X",
        match_type=match_type,
        confidence=ConfidenceLevel.HIGH,
    )

    assert not identity.is_established


def test_match_type_and_confidence_must_use_the_controlled_vocabulary() -> None:
    with pytest.raises(DomainValidationError):
        ProductIdentity(match_type="EXACT")

    with pytest.raises(DomainValidationError):
        ProductIdentity(confidence="HIGH")
