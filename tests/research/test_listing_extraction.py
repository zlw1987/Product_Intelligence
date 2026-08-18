"""Extraction edge cases (PRODUCT-INTEL.3A).

Every document in this file is **synthetic** and written inline, deliberately
and visibly. It covers behaviours that cannot be isolated from a recorded page:
a page with several offers, an `AggregateOffer`, an `@graph` wrapper, a
malformed block beside a valid one, and the refusals that keep visible text out
of a price field.

The real recorded pages are exercised separately, in
`test_listing_extraction_recorded_pages.py`. Nothing here is a stand-in for
them: a synthetic page proves the parser handles a shape, and only a recording
proves real pages have it.
"""

from __future__ import annotations

import json

import pytest

from product_intelligence.research.extraction import (
    MAX_JSON_LD_BLOCKS,
    MAX_JSON_LD_DEPTH,
    extract_listing_observations,
)
from product_intelligence.research.listings import ExtractionMethod

URL = "https://example.com/product/1"


def _page(*bodies: str) -> str:
    return "<html><head>" + "".join(bodies) + "</head><body></body></html>"


def _json_ld(payload) -> str:
    text = payload if isinstance(payload, str) else json.dumps(payload)
    return f'<script type="application/ld+json">{text}</script>'


def _extract(document: str):
    return extract_listing_observations(document, source_url=URL)


class TestArguments:
    def test_a_non_string_document_is_a_caller_defect(self) -> None:
        with pytest.raises(TypeError):
            extract_listing_observations(b"<html></html>", source_url=URL)  # type: ignore[arg-type]

    def test_a_blank_source_url_is_refused(self) -> None:
        """An observation nobody can re-open is not evidence."""
        with pytest.raises(ValueError):
            extract_listing_observations("<html></html>", source_url="   ")

    def test_an_empty_document_yields_nothing_rather_than_raising(self) -> None:
        assert _extract("") == ()

    def test_the_source_url_is_used_as_supplied(self) -> None:
        """Research generates no provenance; the caller passes the final URL."""
        document = _page(_json_ld({"@type": "Product", "name": "Thing"}))

        observations = extract_listing_observations(
            document, source_url="https://elsewhere.example/x"
        )

        assert observations[0].source_url == "https://elsewhere.example/x"


class TestJsonLdShapes:
    def test_a_bare_product_object_is_recognized(self) -> None:
        document = _page(
            _json_ld({"@type": "Product", "name": "Thing", "mpn": "ABC-123"})
        )

        observations = _extract(document)

        assert len(observations) == 1
        assert observations[0].product_title == "Thing"
        assert observations[0].manufacturer_part_number_text == "ABC-123"
        assert observations[0].extraction_method is ExtractionMethod.JSON_LD

    def test_a_top_level_list_is_traversed(self) -> None:
        document = _page(
            _json_ld(
                [
                    {"@type": "Organization", "name": "Shop"},
                    {"@type": "Product", "name": "Thing", "sku": "S1"},
                ]
            )
        )

        observations = _extract(document)

        assert [o.sku_text for o in observations] == ["S1"]

    def test_a_graph_wrapper_is_traversed(self) -> None:
        document = _page(
            _json_ld(
                {
                    "@context": "https://schema.org",
                    "@graph": [
                        {"@type": "WebPage", "name": "Page"},
                        {"@type": "Product", "name": "Thing", "sku": "S2"},
                    ],
                }
            )
        )

        assert [o.sku_text for o in _extract(document)] == ["S2"]

    def test_a_fully_qualified_type_url_is_the_same_claim(self) -> None:
        document = _page(_json_ld({"@type": "https://schema.org/Product", "name": "T"}))

        assert len(_extract(document)) == 1

    def test_a_list_valued_type_is_recognized(self) -> None:
        document = _page(_json_ld({"@type": ["Thing", "Product"], "name": "T"}))

        assert len(_extract(document)) == 1

    @pytest.mark.parametrize(
        "node_type", ["Organization", "BreadcrumbList", "ImageObject", "WebAPI", "Article"]
    )
    def test_a_non_product_node_is_ignored_rather_than_guessed_at(
        self, node_type: str
    ) -> None:
        document = _page(_json_ld({"@type": node_type, "name": "Not a product"}))

        assert _extract(document) == ()


class TestOffers:
    def test_a_single_offer_is_mapped_field_by_field(self) -> None:
        document = _page(
            _json_ld(
                {
                    "@type": "Product",
                    "name": "Thing",
                    "mpn": "ABC-123",
                    "brand": {"@type": "Brand", "name": "Acme"},
                    "offers": {
                        "@type": "Offer",
                        "price": "199.00",
                        "priceCurrency": "USD",
                        "availability": "https://schema.org/InStock",
                        "itemCondition": "https://schema.org/UsedCondition",
                        "seller": {"@type": "Organization", "name": "Reseller Ltd"},
                        "url": "https://example.com/offer/1",
                    },
                }
            )
        )

        observation = _extract(document)[0]

        assert observation.price_text == "199.00"
        assert observation.currency_text == "USD"
        assert observation.availability_text == "https://schema.org/InStock"
        assert observation.condition_text == "https://schema.org/UsedCondition"
        assert observation.seller_text == "Reseller Ltd"
        assert observation.offer_url_text == "https://example.com/offer/1"
        assert observation.brand_text == "Acme"

    def test_several_offers_do_not_collapse_into_one(self) -> None:
        """A page publishing three offers is publishing three offers.

        Collapsing them would silently reduce a count 4A depends on, and
        choosing which one survives would be an aggregation decision taken in an
        extractor.
        """
        document = _page(
            _json_ld(
                {
                    "@type": "Product",
                    "name": "Thing",
                    "mpn": "ABC-123",
                    "offers": [
                        {"@type": "Offer", "price": "199.00", "priceCurrency": "USD"},
                        {"@type": "Offer", "price": "210.50", "priceCurrency": "USD"},
                        {"@type": "Offer", "price": "185.00", "priceCurrency": "EUR"},
                    ],
                }
            )
        )

        observations = _extract(document)

        assert [o.price_text for o in observations] == ["199.00", "210.50", "185.00"]
        assert [o.currency_text for o in observations] == ["USD", "USD", "EUR"]
        assert all(o.manufacturer_part_number_text == "ABC-123" for o in observations)

    def test_mixed_currencies_are_recorded_side_by_side_and_never_combined(self) -> None:
        """No conversion, no rate, no blending. FX is not part of any phase here."""
        document = _page(
            _json_ld(
                {
                    "@type": "Product",
                    "name": "Thing",
                    "offers": [
                        {"@type": "Offer", "price": "100", "priceCurrency": "USD"},
                        {"@type": "Offer", "price": "95", "priceCurrency": "EUR"},
                        {"@type": "Offer", "price": "82", "priceCurrency": "GBP"},
                    ],
                }
            )
        )

        observations = _extract(document)

        assert {o.currency_text for o in observations} == {"USD", "EUR", "GBP"}
        assert [o.price_text for o in observations] == ["100", "95", "82"]

    def test_a_product_with_no_offer_still_yields_an_observation(self) -> None:
        """A manufacturer page publishing a part number and no price is evidence."""
        document = _page(_json_ld({"@type": "Product", "name": "T", "mpn": "ABC-123"}))

        observation = _extract(document)[0]

        assert observation.manufacturer_part_number_text == "ABC-123"
        assert observation.price_text is None
        assert observation.has_price_text is False

    def test_an_aggregate_offer_yields_no_price(self) -> None:
        """A low and a high across sellers is a range, not this product's price.

        Picking either end would be the lowest-wins rule wearing a schema name.
        The node survives in the raw reference for 3B.
        """
        document = _page(
            _json_ld(
                {
                    "@type": "Product",
                    "name": "Thing",
                    "offers": {
                        "@type": "AggregateOffer",
                        "lowPrice": "180.00",
                        "highPrice": "240.00",
                        "priceCurrency": "USD",
                        "offerCount": "7",
                    },
                }
            )
        )

        observation = _extract(document)[0]

        assert observation.price_text is None
        assert observation.currency_text == "USD"
        preserved = json.loads(observation.raw_reference or "{}")
        assert preserved["offers"]["lowPrice"] == "180.00"
        assert preserved["offers"]["highPrice"] == "240.00"

    def test_an_aggregate_that_publishes_its_own_offers_yields_those(self) -> None:
        """Reading published concrete offers is not inference."""
        document = _page(
            _json_ld(
                {
                    "@type": "Product",
                    "name": "Thing",
                    "offers": {
                        "@type": "AggregateOffer",
                        "lowPrice": "180.00",
                        "highPrice": "240.00",
                        "offers": [
                            {"@type": "Offer", "price": "180.00", "priceCurrency": "USD"},
                            {"@type": "Offer", "price": "240.00", "priceCurrency": "USD"},
                        ],
                    },
                }
            )
        )

        assert [o.price_text for o in _extract(document)] == ["180.00", "240.00"]


class TestValuesStayRaw:
    def test_a_json_number_price_keeps_its_source_representation(self) -> None:
        """Parsed with `parse_float=str`, so no float ever holds a price.

        `1055.85` through a float and back is not guaranteed to be the same
        characters, and the page's own representation is what a reviewer checks.
        """
        document = _page(
            _json_ld('{"@type": "Product", "name": "T", '
                     '"offers": {"@type": "Offer", "price": 1055.85}}')
        )

        observation = _extract(document)[0]

        assert observation.price_text == "1055.85"
        assert isinstance(observation.price_text, str)

    def test_a_large_integer_price_keeps_its_source_representation(self) -> None:
        document = _page(
            _json_ld('{"@type": "Product", "name": "T", '
                     '"offers": {"@type": "Offer", "price": 1200}}')
        )

        assert _extract(document)[0].price_text == "1200"

    @pytest.mark.parametrize(
        "published",
        ["1,055.85", "$1055.85", "USD 1055.85", "Call for pricing", "undefined", "0.00"],
    )
    def test_price_text_is_never_cleaned_up(self, published: str) -> None:
        """Stripping a symbol or a separator is normalization, and that is 3B."""
        document = _page(
            _json_ld(
                {
                    "@type": "Product",
                    "name": "T",
                    "offers": {"@type": "Offer", "price": published},
                }
            )
        )

        assert _extract(document)[0].price_text == published

    def test_a_boolean_availability_keeps_its_published_spelling(self) -> None:
        document = _page(
            _json_ld(
                {
                    "@type": "Product",
                    "name": "T",
                    "offers": {"@type": "Offer", "price": "1", "availability": False},
                }
            )
        )

        assert _extract(document)[0].availability_text == "false"

    def test_a_structurally_unreadable_scalar_is_left_absent(self) -> None:
        """Guessing which element of a list was meant is not this layer's job."""
        document = _page(
            _json_ld(
                {
                    "@type": "Product",
                    "name": "T",
                    "offers": {"@type": "Offer", "price": ["199", "210"]},
                }
            )
        )

        assert _extract(document)[0].price_text is None

    def test_a_brand_given_as_a_plain_string_is_read(self) -> None:
        document = _page(_json_ld({"@type": "Product", "name": "T", "brand": "Acme"}))

        assert _extract(document)[0].brand_text == "Acme"


class TestMalformedInput:
    def test_a_malformed_block_does_not_erase_its_valid_siblings(self) -> None:
        """A broken block on a page is common; losing the page to it is an
        outage caused by someone else's typo."""
        document = _page(
            _json_ld("{ this is not json ]"),
            _json_ld({"@type": "Product", "name": "Thing", "sku": "S9"}),
            _json_ld("{{{"),
        )

        observations = _extract(document)

        assert [o.sku_text for o in observations] == ["S9"]

    def test_a_malformed_block_alone_yields_nothing_rather_than_raising(self) -> None:
        assert _extract(_page(_json_ld("not json at all"))) == ()

    def test_an_empty_block_is_skipped(self) -> None:
        assert _extract(_page(_json_ld("   "))) == ()

    def test_a_json_scalar_block_is_skipped(self) -> None:
        assert _extract(_page(_json_ld('"just a string"'))) == ()

    def test_unclosed_markup_does_not_lose_an_earlier_valid_block(self) -> None:
        document = (
            "<html><head>"
            + _json_ld({"@type": "Product", "name": "T", "sku": "S1"})
            + "<div><span><p>unclosed"
        )

        assert [o.sku_text for o in _extract(document)] == ["S1"]

    def test_a_script_tag_inside_a_json_string_does_not_mis_slice_the_page(self) -> None:
        """The reason this uses a parser rather than a regular expression."""
        document = _page(
            _json_ld({"@type": "Product", "name": "T", "sku": "S1"}),
            "<script>var x = '</scr' + 'ipt>';</script>",
            _json_ld({"@type": "Product", "name": "U", "sku": "S2"}),
        )

        assert [o.sku_text for o in _extract(document)] == ["S1", "S2"]

    def test_deeply_nested_json_does_not_exhaust_the_stack(self) -> None:
        """Untrusted JSON nests as deeply as its author likes."""
        payload: object = {"@type": "Product", "name": "Deep", "sku": "S1"}
        for _ in range(MAX_JSON_LD_DEPTH * 4):
            payload = {"nested": payload}

        assert _extract(_page(_json_ld(payload))) == ()

    def test_a_document_with_absurdly_many_blocks_is_bounded(self) -> None:
        blocks = [
            _json_ld({"@type": "Product", "name": f"P{index}", "sku": f"S{index}"})
            for index in range(MAX_JSON_LD_BLOCKS + 25)
        ]

        assert len(_extract(_page(*blocks))) == MAX_JSON_LD_BLOCKS

    def test_a_script_of_another_type_is_not_read_as_structured_data(self) -> None:
        document = _page(
            '<script type="text/javascript">'
            '{"@type": "Product", "name": "Fake", "offers": {"price": "1.00"}}'
            "</script>"
        )

        assert _extract(document) == ()


class TestMetaExtraction:
    def test_flat_product_meta_is_read_when_there_is_no_json_ld(self) -> None:
        document = _page(
            '<meta name="mpn" content="ABC-123">',
            '<meta name="sku" content="R-99">',
            '<meta name="brand" content="Acme">',
            '<meta name="price" content="199.00">',
            '<meta name="availability" content="false">',
        )

        observation = _extract(document)[0]

        assert observation.extraction_method is ExtractionMethod.META
        assert observation.manufacturer_part_number_text == "ABC-123"
        assert observation.sku_text == "R-99"
        assert observation.price_text == "199.00"
        assert observation.availability_text == "false"

    def test_open_graph_price_meta_is_read(self) -> None:
        document = _page(
            '<meta property="og:title" content="A Thing">',
            '<meta property="og:price:amount" content="1,055.85">',
            '<meta property="og:price:currency" content="USD">',
        )

        observation = _extract(document)[0]

        assert observation.product_title == "A Thing"
        assert observation.price_text == "1,055.85"
        assert observation.currency_text == "USD"

    def test_json_ld_takes_precedence_and_meta_does_not_also_run(self) -> None:
        """One document, one mechanism — otherwise one offer becomes two."""
        document = _page(
            _json_ld(
                {
                    "@type": "Product",
                    "name": "Thing",
                    "offers": {"@type": "Offer", "price": "1055.85"},
                }
            ),
            '<meta property="og:price:amount" content="1,055.85">',
        )

        observations = _extract(document)

        assert len(observations) == 1
        assert observations[0].extraction_method is ExtractionMethod.JSON_LD
        assert observations[0].price_text == "1055.85"

    def test_meta_runs_when_json_ld_produced_no_product(self) -> None:
        """A page with a non-product JSON-LD node still has its meta read."""
        document = _page(
            _json_ld({"@type": "BreadcrumbList", "name": "Crumbs"}),
            '<meta name="mpn" content="ABC-123">',
            '<meta name="price" content="42.00">',
        )

        observation = _extract(document)[0]

        assert observation.extraction_method is ExtractionMethod.META
        assert observation.manufacturer_part_number_text == "ABC-123"

    def test_a_page_with_only_a_title_is_not_a_listing(self) -> None:
        """Inventing an observation from a title is the guess this phase avoids."""
        document = _page(
            '<meta property="og:title" content="Some Page">',
            '<meta property="og:type" content="website">',
        )

        assert _extract(document) == ()

    def test_meta_yields_at_most_one_observation(self) -> None:
        """Flat meta has no structure in which a second offer could be expressed."""
        document = _page(
            '<meta name="price" content="199.00">',
            '<meta name="price" content="210.00">',
            '<meta name="mpn" content="ABC-123">',
        )

        observations = _extract(document)

        assert len(observations) == 1
        assert observations[0].price_text == "199.00"

    def test_a_self_closing_meta_tag_is_read(self) -> None:
        document = _page('<meta name="price" content="199.00"/>')

        assert _extract(document)[0].price_text == "199.00"


class TestWhatIsNeverRead:
    @pytest.mark.parametrize(
        "markup",
        [
            '<span class="price">$1,055.85</span>',
            '<div class="our-price">1055.85 USD</div>',
            "<p>Was $2,700.00, now $2,135.00 — you save $565.00</p>",
            "<p>As low as $102.98/mo</p>",
            "<p>Free shipping on orders over $50.00</p>",
            "<td>$1055.85</td>",
        ],
    )
    def test_visible_text_is_never_read_as_a_price(self, markup: str) -> None:
        """No first-match, lowest-match, or largest-match rule exists.

        The last two strings are real: they are snippets from the recorded
        search fixture behind this phase. A current price, a struck-through list
        price, a saving, and a monthly instalment are four different numbers,
        and nothing in the text says which is which.
        """
        document = "<html><body>" + markup + "</body></html>"

        assert extract_listing_observations(document, source_url=URL) == ()

    def test_a_part_number_in_a_title_is_not_read_as_a_published_part_number(
        self,
    ) -> None:
        """Inference from noisy text is 3A/3C rejection reasoning, not a field."""
        document = _page(
            _json_ld({"@type": "Product", "name": "Samsung MZ-QL23T800 3.84TB SSD"})
        )

        observation = _extract(document)[0]

        assert "MZ-QL23T800" in (observation.product_title or "")
        assert observation.manufacturer_part_number_text is None

    def test_a_part_number_in_the_url_is_not_read_as_a_published_part_number(
        self,
    ) -> None:
        document = _page(_json_ld({"@type": "Product", "name": "A drive"}))

        observations = extract_listing_observations(
            document, source_url="https://example.com/p/MZ-QL23T800"
        )

        assert observations[0].manufacturer_part_number_text is None

    def test_extraction_makes_no_identity_decision(self) -> None:
        """A published MPN is preserved; nothing here says it matches anything.

        The 2A comparator exists and is not called from extraction — an
        extractor that decided identity would be judging its own evidence. What
        3A guarantees is that the raw string survives intact for 3C to hand to
        the comparator later.
        """
        from product_intelligence.research.identity import compare_part_numbers
        from product_intelligence.domain import IdentityMatchType

        document = _page(
            _json_ld({"@type": "Product", "name": "T", "mpn": "MZ-QL23T800"})
        )

        observation = _extract(document)[0]

        assert observation.manufacturer_part_number_text == "MZ-QL23T800"
        # Demonstrated here, by a test, and nowhere in the extraction code.
        assessment = compare_part_numbers(
            "MZ-QL23T800", observation.manufacturer_part_number_text
        )
        assert assessment.match_type is IdentityMatchType.EXACT
