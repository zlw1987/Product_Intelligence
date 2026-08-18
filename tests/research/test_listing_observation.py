"""The raw listing observation contract (PRODUCT-INTEL.3A).

What it accepts, what it refuses, and — most of what matters — which fields it
deliberately does not have. A numeric price field on this contract would let a
page's text enter arithmetic as though it were a verified market observation,
which is the same argument that kept one off `SearchResult` in 2B (AD-039).
"""

from __future__ import annotations

from dataclasses import fields

import pytest

from product_intelligence.research.listings import ExtractionMethod, ListingObservation

URL = "https://example.com/product/1"


def _observation(**overrides) -> ListingObservation:
    values = {"source_url": URL, "extraction_method": ExtractionMethod.JSON_LD}
    values.update(overrides)
    return ListingObservation(**values)


class TestTheFieldList:
    def test_the_contract_is_exactly_these_fields(self) -> None:
        """Asserted exactly, so a later phase widening it has to say so.

        The absent fields are the point: no `Decimal`, no currency enum, no
        quantity, no unit price, no condition or availability vocabulary, no
        accept/reject decision, no score, no confidence.
        """
        assert [field.name for field in fields(ListingObservation)] == [
            "source_url",
            "extraction_method",
            "product_title",
            "manufacturer_part_number_text",
            "sku_text",
            "brand_text",
            "price_text",
            "currency_text",
            "availability_text",
            "condition_text",
            "seller_text",
            "offer_url_text",
            "raw_reference",
        ]

    @pytest.mark.parametrize(
        "forbidden",
        [
            "price",
            "price_decimal",
            "amount",
            "currency",
            "unit_price",
            "quantity",
            "pack_size",
            "condition",
            "availability",
            "accepted",
            "rejected",
            "decision",
            "reason",
            "confidence",
            "score",
            "match_type",
            "identity",
            "rank",
            "shipping_cost",
        ],
    )
    def test_no_normalized_or_decided_field_exists(self, forbidden: str) -> None:
        assert forbidden not in {field.name for field in fields(ListingObservation)}

    def test_every_observed_field_is_text_or_absent(self) -> None:
        """The type annotations are part of the guarantee, not decoration."""
        annotations = {field.name: field.type for field in fields(ListingObservation)}

        for name, annotation in annotations.items():
            if name == "extraction_method":
                continue
            assert "str" in str(annotation), (name, annotation)


class TestConstruction:
    def test_it_records_what_a_page_published(self) -> None:
        observation = _observation(
            product_title="A Thing",
            manufacturer_part_number_text="ABC-123",
            sku_text="R-99",
            brand_text="Acme",
            price_text="199.00",
            currency_text="USD",
            availability_text="https://schema.org/InStock",
            condition_text="https://schema.org/NewCondition",
            seller_text="Reseller Ltd",
            offer_url_text="/offers/1",
            raw_reference='{"@type": "Product"}',
        )

        assert observation.price_text == "199.00"
        assert observation.has_price_text is True
        assert observation.has_published_part_number is True

    def test_a_source_url_is_required(self) -> None:
        with pytest.raises(ValueError, match="re-open"):
            _observation(source_url="   ")

    def test_the_extraction_method_must_be_a_vocabulary_member(self) -> None:
        with pytest.raises(TypeError):
            _observation(extraction_method="JSON_LD")

    def test_an_absent_field_stays_absent(self) -> None:
        observation = _observation()

        assert observation.price_text is None
        assert observation.has_price_text is False
        assert observation.has_published_part_number is False

    def test_a_blank_value_is_the_same_as_absent(self) -> None:
        """"The page said nothing here" gets one representation."""
        assert _observation(price_text="   ").price_text is None

    def test_it_is_frozen(self) -> None:
        observation = _observation(price_text="199.00")

        with pytest.raises(Exception):
            observation.price_text = "1.00"  # type: ignore[misc]

    @pytest.mark.parametrize("value", [199.0, 199, True, ["199"], {"v": "199"}])
    def test_a_non_text_observation_is_a_caller_defect(self, value: object) -> None:
        """Converting on the way in is what this contract exists to prevent."""
        with pytest.raises(TypeError):
            _observation(price_text=value)

    def test_a_non_string_raw_reference_is_refused(self) -> None:
        """Preserved material is opaque, not a structure to read a key out of."""
        with pytest.raises(TypeError):
            _observation(raw_reference={"@type": "Product"})


class TestValuesAreKeptAsPublished:
    @pytest.mark.parametrize(
        "published",
        [
            "1,055.85",
            "$1055.85",
            "USD 1,055.85",
            "undefined",
            "Call for pricing",
            "0.00",
            "1055.85 - 1299.00",
        ],
    )
    def test_a_price_is_stored_character_for_character(self, published: str) -> None:
        assert _observation(price_text=published).price_text == published

    def test_a_published_part_number_keeps_a_prefix_a_real_page_wrote(self) -> None:
        """Stripping `mpn:` is a normalization rule, and 3A makes none."""
        observation = _observation(manufacturer_part_number_text="mpn:MZ-QL23T800")

        assert observation.manufacturer_part_number_text == "mpn:MZ-QL23T800"

    def test_interior_whitespace_is_never_rewritten(self) -> None:
        assert _observation(product_title="A   spaced   name").product_title == (
            "A   spaced   name"
        )

    def test_a_non_vocabulary_availability_is_kept(self) -> None:
        assert _observation(availability_text="false").availability_text == "false"


class TestExtractionMethod:
    def test_exactly_two_mechanisms_are_declared(self) -> None:
        """A vocabulary member nothing produces is a placeholder for unbuilt
        behaviour. A per-source strategy is described in the plan and is not
        implemented, so it is not named here."""
        assert {member.name for member in ExtractionMethod} == {"JSON_LD", "META"}

    def test_a_mechanism_is_not_a_trustworthiness_rating(self) -> None:
        """No ordering, no score, no confidence mapping.

        A JSON-LD price is still one page's claim — the recorded manufacturer
        fixture publishes the literal string `undefined` in exactly that
        position.
        """
        assert not hasattr(ExtractionMethod, "confidence")
        for member in ExtractionMethod:
            assert isinstance(member.value, str)
