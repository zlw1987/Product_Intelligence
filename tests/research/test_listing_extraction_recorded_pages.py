"""Extraction against recorded real pages (PRODUCT-INTEL.3A).

Offline. Every fixture in `tests/fixtures/pages/` is a real public product page
fetched once on 2026-08-17, reduced and documented in that directory's README.
These tests run the actual extractor over that real material — not over a
hand-authored payload standing in for it, which would pass regardless of what
real pages do.

`tests/research/test_listing_extraction.py` holds the synthetic edge cases,
labelled as such and kept in a separate file so the two can never be confused.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from product_intelligence.research.extraction import extract_listing_observations
from product_intelligence.research.listings import ExtractionMethod

FIXTURE_ROOT = Path(__file__).resolve().parents[1] / "fixtures" / "pages"

SAMSUNG_URL = (
    "https://www.samsung.com/us/business/memory-storage/nvme-ssd/"
    "pm9a3-nvme-u-2-ssd-3-8tb-sku-mz-ql23t800/"
)
OEMPCWORLD_URL = (
    "https://oempcworld.com/products/samsung-pm9a3-3-84tb-mz-ql23t800-nvme-pcie-4-0-x4"
)
EXXACT_URL = "https://www.exxactcorp.com/Samsung-MZ-QL23T800-E5387548"
NEWEGG_URL = "https://www.newegg.com/p/2RC-0034-00762"
FUSIONWW_URL = "https://www.fusionww.com/shop/product/4267839/MZ-QL23T800"


def _document(name: str) -> str:
    return (FIXTURE_ROOT / name).read_text(encoding="utf-8")


def _extract(name: str, url: str):
    return extract_listing_observations(_document(name), source_url=url)


def test_every_recorded_fixture_is_documented() -> None:
    """A recording with no provenance is not evidence."""
    readme = (FIXTURE_ROOT / "README.md").read_text(encoding="utf-8")
    fixtures = sorted(path.name for path in FIXTURE_ROOT.glob("*.html"))

    assert fixtures, "the fixture directory is empty"
    for name in fixtures:
        assert name in readme, f"{name} is not documented in the fixtures README"


class TestManufacturerPage:
    """`samsung_us_pm9a3_mz_ql23t800.html` — the manufacturer-controlled page."""

    def test_it_yields_one_observation_from_json_ld(self) -> None:
        observations = _extract("samsung_us_pm9a3_mz_ql23t800.html", SAMSUNG_URL)

        assert len(observations) == 1
        assert observations[0].extraction_method is ExtractionMethod.JSON_LD

    def test_the_published_part_number_is_preserved_where_the_page_put_it(self) -> None:
        """This page puts the MPN in `sku`, not in `mpn`.

        Both fields are preserved separately and neither is inferred from the
        other: which field a manufacturer uses is an observation, and reconciling
        them is 3C's decision with a recorded reason.
        """
        observation = _extract("samsung_us_pm9a3_mz_ql23t800.html", SAMSUNG_URL)[0]

        assert observation.sku_text == "MZ-QL23T800"
        assert observation.manufacturer_part_number_text is None
        assert observation.has_published_part_number is False

    def test_a_broken_published_price_is_preserved_exactly(self) -> None:
        """The single clearest reason 3A stores text.

        This page publishes `"price": "undefined"` inside a well-formed
        `schema.org` Offer — a template that failed, served as structured data.
        A converting extractor would raise on it or silently drop the offer, and
        neither outcome is visible to a reviewer. It is kept verbatim, and what
        it means is 3B's problem, with a reason attached.
        """
        observation = _extract("samsung_us_pm9a3_mz_ql23t800.html", SAMSUNG_URL)[0]

        assert observation.price_text == "undefined"
        assert observation.has_price_text is True
        assert observation.currency_text == "USD"

    def test_condition_is_preserved_in_the_vocabulary_the_page_used(self) -> None:
        observation = _extract("samsung_us_pm9a3_mz_ql23t800.html", SAMSUNG_URL)[0]

        assert observation.condition_text == "https://schema.org/NewCondition"

    def test_brand_is_read_from_the_nested_object_form(self) -> None:
        observation = _extract("samsung_us_pm9a3_mz_ql23t800.html", SAMSUNG_URL)[0]

        assert observation.brand_text == "Samsung"

    def test_the_breadcrumb_sibling_node_is_ignored(self) -> None:
        """A non-Product node is not an offer, and one observation proves it."""
        assert len(_extract("samsung_us_pm9a3_mz_ql23t800.html", SAMSUNG_URL)) == 1


class TestRetailerPageWithJsonLd:
    """`oempcworld_pm9a3_mz_ql23t800.html` — a storefront with both mechanisms."""

    def test_it_yields_one_observation_with_the_published_price(self) -> None:
        observations = _extract("oempcworld_pm9a3_mz_ql23t800.html", OEMPCWORLD_URL)

        assert len(observations) == 1
        observation = observations[0]
        assert observation.extraction_method is ExtractionMethod.JSON_LD
        assert observation.price_text == "1055.85"
        assert observation.currency_text == "USD"

    def test_the_same_offer_published_twice_does_not_become_two_observations(
        self,
    ) -> None:
        """This page carries `"1055.85"` in JSON-LD and `"1,055.85"` in OpenGraph.

        Running both mechanisms would double one offer, and 4A counts
        observations. The JSON-LD representation wins because it exists.
        """
        observations = _extract("oempcworld_pm9a3_mz_ql23t800.html", OEMPCWORLD_URL)

        assert len(observations) == 1
        assert "og:price:amount" in _document("oempcworld_pm9a3_mz_ql23t800.html")
        assert observations[0].price_text == "1055.85"

    def test_the_retailer_sku_is_not_promoted_to_a_part_number(self) -> None:
        """`501489` is this shop's internal number, and the page publishes no MPN.

        The part number appears only inside the product title, and nothing here
        reads it out of there — that is inference from noisy text (3A/3C
        rejection reasoning), not a published field.
        """
        observation = _extract("oempcworld_pm9a3_mz_ql23t800.html", OEMPCWORLD_URL)[0]

        assert observation.sku_text == "501489"
        assert observation.manufacturer_part_number_text is None
        assert "MZ-QL23T800" in (observation.product_title or "")

    def test_availability_is_preserved_without_being_interpreted(self) -> None:
        observation = _extract("oempcworld_pm9a3_mz_ql23t800.html", OEMPCWORLD_URL)[0]

        assert observation.availability_text == "http://schema.org/OutOfStock"

    def test_the_offers_own_variant_url_is_kept(self) -> None:
        """A page can price several variants at several addresses."""
        observation = _extract("oempcworld_pm9a3_mz_ql23t800.html", OEMPCWORLD_URL)[0]

        assert observation.offer_url_text is not None
        assert "variant=48871019151587" in observation.offer_url_text
        assert observation.source_url == OEMPCWORLD_URL

    @pytest.mark.parametrize(
        "amount", ["$8.85", "$6.85", "$13.75", "$129.98", "$527.92", "$30,000.00"]
    )
    def test_price_shaped_noise_in_the_real_page_is_not_read_as_a_price(
        self, amount: str
    ) -> None:
        """Every one of these is really on this page, and none of them is the price.

        Four are recommended products, written in markup identical to the
        product's own price element. One is a financing instalment
        (`price_per_term`). One is a financing plan's upper bound. A
        first-match, lowest-match, or largest-match visible-text rule returns a
        wrong number here with complete confidence — which is why no such rule
        exists.
        """
        document = _document("oempcworld_pm9a3_mz_ql23t800.html")
        assert amount in document, "the fixture must really contain this noise"

        observations = _extract("oempcworld_pm9a3_mz_ql23t800.html", OEMPCWORLD_URL)

        assert [o.price_text for o in observations] == ["1055.85"]

    def test_no_observation_carries_a_numeric_price(self) -> None:
        observation = _extract("oempcworld_pm9a3_mz_ql23t800.html", OEMPCWORLD_URL)[0]

        assert isinstance(observation.price_text, str)
        assert not hasattr(observation, "price")
        assert not hasattr(observation, "price_decimal")


class TestRetailerPageWithMetaOnly:
    """`exxactcorp_pm9a3_mz_ql23t800.html` — the page that justifies META."""

    def test_a_page_with_no_json_ld_still_yields_its_published_record(self) -> None:
        """Without the meta path, a page plainly stating its MPN and price
        would produce nothing."""
        observations = _extract("exxactcorp_pm9a3_mz_ql23t800.html", EXXACT_URL)

        assert 'type="application/ld+json"' not in _document(
            "exxactcorp_pm9a3_mz_ql23t800.html"
        )
        assert len(observations) == 1
        assert observations[0].extraction_method is ExtractionMethod.META

    def test_the_published_mpn_keeps_its_prefix(self) -> None:
        """The page writes `mpn:MZ-QL23T800`. Stripping the prefix is a
        normalization rule, and 3A makes none."""
        observation = _extract("exxactcorp_pm9a3_mz_ql23t800.html", EXXACT_URL)[0]

        assert observation.manufacturer_part_number_text == "mpn:MZ-QL23T800"

    def test_a_price_with_no_currency_stays_a_price_with_no_currency(self) -> None:
        """This page publishes no currency anywhere. Nothing infers one."""
        observation = _extract("exxactcorp_pm9a3_mz_ql23t800.html", EXXACT_URL)[0]

        assert observation.price_text == "1300.53"
        assert observation.currency_text is None

    def test_a_non_vocabulary_availability_is_preserved_as_written(self) -> None:
        """`"false"` is no `schema.org` term. It is 3B's problem, visibly."""
        observation = _extract("exxactcorp_pm9a3_mz_ql23t800.html", EXXACT_URL)[0]

        assert observation.availability_text == "false"

    def test_the_retailer_sku_and_brand_are_kept_separately(self) -> None:
        observation = _extract("exxactcorp_pm9a3_mz_ql23t800.html", EXXACT_URL)[0]

        assert observation.sku_text == "SAM-MZ-QL23T800-00"
        assert observation.brand_text == "Samsung"


class TestPagesThatYieldNothing:
    def test_a_client_rendered_page_yields_no_observation(self) -> None:
        """`newegg_pm9a3_mz_ql23t800.html`: HTTP 200, ~203 KB, no product data.

        The only structured nodes are a BreadcrumbList and an ImageObject, and
        the price is nowhere in the static document. Zero observations is the
        honest answer; filling it in from a search snippet is not.
        """
        assert _extract("newegg_pm9a3_mz_ql23t800.html", NEWEGG_URL) == ()

    def test_an_access_restricted_interstitial_yields_no_observation(self) -> None:
        """`fusionww_access_restricted.html`: a soft block served as HTTP 200."""
        assert _extract("fusionww_access_restricted.html", FUSIONWW_URL) == ()

    def test_instructions_embedded_in_a_fetched_page_are_data(self) -> None:
        """That fixture's structured data addresses its automated reader directly.

        It is a `WebAPI` node telling a crawler to call a different service
        instead. The extractor's correct output is zero observations — a
        `WebAPI` node is not an offer — and nothing in this repository acts on
        text found in a fetched page (§19).
        """
        document = _document("fusionww_access_restricted.html")

        assert "WebAPI" in document
        assert "instead of crawling" in document
        assert _extract("fusionww_access_restricted.html", FUSIONWW_URL) == ()


class TestProvenance:
    @pytest.mark.parametrize(
        ("name", "url"),
        [
            ("samsung_us_pm9a3_mz_ql23t800.html", SAMSUNG_URL),
            ("oempcworld_pm9a3_mz_ql23t800.html", OEMPCWORLD_URL),
            ("exxactcorp_pm9a3_mz_ql23t800.html", EXXACT_URL),
        ],
    )
    def test_every_observation_is_traceable_to_its_page(
        self, name: str, url: str
    ) -> None:
        for observation in _extract(name, url):
            assert observation.source_url == url
            assert observation.raw_reference

    def test_the_raw_reference_preserves_material_the_contract_does_not_carry(
        self,
    ) -> None:
        """The contract stays small without discarding evidence.

        This page publishes a GTIN, a category, and a long description, none of
        which is a `ListingObservation` field. All three survive in the raw
        reference for a later phase that needs them.
        """
        observation = _extract("oempcworld_pm9a3_mz_ql23t800.html", OEMPCWORLD_URL)[0]
        preserved = json.loads(observation.raw_reference or "{}")

        assert preserved["gtin"] == "0095779460575"
        assert preserved["category"] == "STORAGE"
        assert "offers" in preserved

    def test_no_observation_is_accepted_rejected_or_scored(self) -> None:
        """3A observes. 3C decides, with a recorded reason."""
        from dataclasses import fields

        from product_intelligence.research.listings import ListingObservation

        names = {field.name for field in fields(ListingObservation)}

        for forbidden in (
            "accepted",
            "rejected",
            "decision",
            "reason",
            "confidence",
            "score",
            "match_type",
            "rank",
        ):
            assert forbidden not in names
