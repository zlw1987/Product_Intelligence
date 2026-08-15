"""Contract tests for ProductIdentity."""

from __future__ import annotations

import pytest

from product_intelligence.domain import (
    ESTABLISHED_MATCH_TYPES,
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


# ---------------------------------------------------------------------------
# PRODUCT-INTEL.0A-FU1: an established identity must carry its own evidence.
#
# The defect these cover: an identity could claim EXACT with no part number at
# all and still report `is_established`. High confidence in a match against
# nothing is not a weak result, it is an impossible one, and the type must not
# be able to represent it.
# ---------------------------------------------------------------------------


def test_an_exact_identity_with_a_part_number_is_valid() -> None:
    identity = ProductIdentity(
        manufacturer_part_number="ABC123-X",
        match_type=IdentityMatchType.EXACT,
        confidence=ConfidenceLevel.HIGH,
    )

    assert identity.manufacturer_part_number == "ABC123-X"
    assert identity.is_established


@pytest.mark.parametrize("missing", [None, "", "   ", "\t\n"])
def test_an_exact_identity_without_a_part_number_is_rejected(missing) -> None:
    """The reported defect: EXACT + HIGH confidence + no MPN was constructible."""
    with pytest.raises(DomainValidationError) as excinfo:
        ProductIdentity(
            manufacturer_part_number=missing,
            match_type=IdentityMatchType.EXACT,
            confidence=ConfidenceLevel.HIGH,
        )

    assert "manufacturer_part_number" in str(excinfo.value)


def test_a_normalized_exact_identity_with_both_part_numbers_is_valid() -> None:
    identity = ProductIdentity(
        manufacturer_part_number="ABC 123-X",
        normalized_part_number="ABC123X",
        match_type=IdentityMatchType.NORMALIZED_EXACT,
        confidence=ConfidenceLevel.MEDIUM,
    )

    assert identity.normalized_part_number == "ABC123X"
    assert identity.is_established


@pytest.mark.parametrize("missing", [None, "", "   "])
def test_a_normalized_exact_identity_without_the_normalized_form_is_rejected(
    missing,
) -> None:
    """The normalized form is what distinguishes this match type from EXACT.

    The value is whatever the caller supplied. Nothing here normalizes a part
    number or checks how one was derived — that algorithm is a later phase.
    """
    with pytest.raises(DomainValidationError) as excinfo:
        ProductIdentity(
            manufacturer_part_number="ABC 123-X",
            normalized_part_number=missing,
            match_type=IdentityMatchType.NORMALIZED_EXACT,
        )

    assert "normalized_part_number" in str(excinfo.value)


def test_a_normalized_exact_identity_without_a_part_number_is_rejected() -> None:
    with pytest.raises(DomainValidationError):
        ProductIdentity(
            normalized_part_number="ABC123X",
            match_type=IdentityMatchType.NORMALIZED_EXACT,
        )


@pytest.mark.parametrize(
    "match_type",
    [
        IdentityMatchType.PARTIAL,
        IdentityMatchType.DESCRIPTION_ONLY,
        IdentityMatchType.CONFLICT,
        IdentityMatchType.UNKNOWN,
    ],
)
def test_unestablished_match_types_need_no_part_number(match_type) -> None:
    """DESCRIPTION_ONLY in particular *means* there is no part-number evidence.

    The invariant constrains only what an identity may claim to have
    established; it must not force evidence onto outcomes that assert none.
    """
    identity = ProductIdentity(match_type=match_type)

    assert identity.manufacturer_part_number is None
    assert not identity.is_established


def test_the_default_identity_is_still_constructible() -> None:
    """The invariant must not make the unresolved starting state illegal."""
    identity = ProductIdentity()

    assert identity.match_type is IdentityMatchType.UNKNOWN
    assert not identity.is_established


def test_an_established_identity_always_carries_a_part_number() -> None:
    """The property `is_established` reports; construction guarantees.

    Sweeping the whole vocabulary keeps the two definitions from drifting: if a
    future match type joins the established set without evidence requirements,
    this fails.
    """
    for match_type in IdentityMatchType:
        try:
            identity = ProductIdentity(match_type=match_type)
        except DomainValidationError:
            assert match_type in ESTABLISHED_MATCH_TYPES
            continue

        if identity.is_established:  # pragma: no cover - guarded by the raise
            raise AssertionError(
                f"{match_type} reported an established identity with no "
                "manufacturer_part_number"
            )


def test_the_established_set_is_exactly_the_two_part_number_matches() -> None:
    assert ESTABLISHED_MATCH_TYPES == {
        IdentityMatchType.EXACT,
        IdentityMatchType.NORMALIZED_EXACT,
    }
