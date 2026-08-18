"""Normalization against recorded real pages (PRODUCT-INTEL.3B).

Offline, like `test_listing_extraction_recorded_pages.py`. Every fixture here
is the same real, recorded page used by 3A's extraction tests, run one step
further: `extract_listing_observations()` -> `normalize_listing_observation()`.
Nothing here fetches, and nothing here fabricates a page — the fixtures and
the extraction step are exactly 3A's.
"""

from __future__ import annotations

from decimal import Decimal
from pathlib import Path

from product_intelligence.research.extraction import extract_listing_observations
from product_intelligence.research.listings import ExtractionMethod
from product_intelligence.research.normalization import (
    NormalizationIssueCode,
    NormalizedAvailability,
    NormalizedCondition,
    normalize_listing_observation,
)

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


def _normalized(name: str, url: str):
    observations = extract_listing_observations(_document(name), source_url=url)
    return [normalize_listing_observation(observation) for observation in observations]


class TestManufacturerPage:
    """`samsung_us_pm9a3_mz_ql23t800.html` — publishes `price: "undefined"`."""

    def test_the_broken_published_price_does_not_become_a_number(self) -> None:
        normalized = _normalized("samsung_us_pm9a3_mz_ql23t800.html", SAMSUNG_URL)[0]

        assert normalized.observation.price_text == "undefined"
        assert normalized.price_amount is None
        assert normalized.has_normalization_issues is True
        assert any(
            issue.field == "price" and issue.code == NormalizationIssueCode.INVALID_PRICE
            for issue in normalized.normalization_issues
        )

    def test_the_published_currency_normalizes_cleanly(self) -> None:
        normalized = _normalized("samsung_us_pm9a3_mz_ql23t800.html", SAMSUNG_URL)[0]

        assert normalized.currency_code == "USD"
        assert not any(
            issue.field == "currency" for issue in normalized.normalization_issues
        )

    def test_the_new_condition_normalizes_from_its_schema_org_form(self) -> None:
        normalized = _normalized("samsung_us_pm9a3_mz_ql23t800.html", SAMSUNG_URL)[0]

        assert normalized.condition is NormalizedCondition.NEW

    def test_the_raw_observation_is_still_reachable(self) -> None:
        normalized = _normalized("samsung_us_pm9a3_mz_ql23t800.html", SAMSUNG_URL)[0]

        assert normalized.observation.extraction_method is ExtractionMethod.JSON_LD
        assert normalized.observation.sku_text == "MZ-QL23T800"

    def test_no_availability_was_published_and_none_is_invented(self) -> None:
        normalized = _normalized("samsung_us_pm9a3_mz_ql23t800.html", SAMSUNG_URL)[0]

        assert normalized.observation.availability_text is None
        assert normalized.availability is NormalizedAvailability.UNKNOWN
        assert not any(
            issue.field == "availability" for issue in normalized.normalization_issues
        )


class TestRetailerPageWithJsonLd:
    """`oempcworld_pm9a3_mz_ql23t800.html` — a clean price and a real OutOfStock."""

    def test_the_published_price_becomes_a_decimal(self) -> None:
        normalized = _normalized("oempcworld_pm9a3_mz_ql23t800.html", OEMPCWORLD_URL)[0]

        assert normalized.price_amount == Decimal("1055.85")
        assert isinstance(normalized.price_amount, Decimal)
        assert normalized.normalization_issues == ()

    def test_the_published_currency_normalizes_cleanly(self) -> None:
        normalized = _normalized("oempcworld_pm9a3_mz_ql23t800.html", OEMPCWORLD_URL)[0]

        assert normalized.currency_code == "USD"

    def test_the_out_of_stock_availability_normalizes_from_its_schema_org_form(
        self,
    ) -> None:
        normalized = _normalized("oempcworld_pm9a3_mz_ql23t800.html", OEMPCWORLD_URL)[0]

        assert normalized.observation.availability_text == "http://schema.org/OutOfStock"
        assert normalized.availability is NormalizedAvailability.OUT_OF_STOCK

    def test_none_of_the_price_shaped_noise_on_the_page_affected_the_result(self) -> None:
        """The extractor already refused this noise (3A); normalization sees
        only the one observation extraction produced."""
        normalized_list = _normalized("oempcworld_pm9a3_mz_ql23t800.html", OEMPCWORLD_URL)

        assert len(normalized_list) == 1
        assert normalized_list[0].price_amount == Decimal("1055.85")


class TestRetailerPageWithMetaOnly:
    """`exxactcorp_pm9a3_mz_ql23t800.html` — no currency, and `availability: "false"`."""

    def test_the_published_price_becomes_a_decimal(self) -> None:
        normalized = _normalized("exxactcorp_pm9a3_mz_ql23t800.html", EXXACT_URL)[0]

        assert normalized.price_amount == Decimal("1300.53")

    def test_a_missing_currency_stays_missing_rather_than_being_guessed(self) -> None:
        normalized = _normalized("exxactcorp_pm9a3_mz_ql23t800.html", EXXACT_URL)[0]

        assert normalized.observation.currency_text is None
        assert normalized.currency_code is None
        assert not any(
            issue.field == "currency" for issue in normalized.normalization_issues
        ), "absence is not an error; nothing was published to fail to normalize"

    def test_false_is_not_confidently_out_of_stock(self) -> None:
        """The single clearest reason this module abstains rather than guesses."""
        normalized = _normalized("exxactcorp_pm9a3_mz_ql23t800.html", EXXACT_URL)[0]

        assert normalized.observation.availability_text == "false"
        assert normalized.availability is NormalizedAvailability.UNKNOWN
        assert normalized.availability is not NormalizedAvailability.OUT_OF_STOCK
        assert any(
            issue.field == "availability"
            and issue.code == NormalizationIssueCode.UNRECOGNIZED_AVAILABILITY
            for issue in normalized.normalization_issues
        )

    def test_the_published_mpn_prefix_is_untouched_by_normalization(self) -> None:
        """3B normalizes commercial attributes, never identity fields (§24)."""
        observations = extract_listing_observations(
            _document("exxactcorp_pm9a3_mz_ql23t800.html"), source_url=EXXACT_URL
        )
        normalized = normalize_listing_observation(observations[0])

        assert normalized.observation.manufacturer_part_number_text == "mpn:MZ-QL23T800"


class TestPagesThatYieldNothing:
    def test_a_page_with_no_observations_normalizes_to_nothing(self) -> None:
        from product_intelligence.research.normalization import normalize_listing_observations

        observations = extract_listing_observations(
            _document("newegg_pm9a3_mz_ql23t800.html"), source_url=NEWEGG_URL
        )
        assert observations == ()
        assert normalize_listing_observations(observations) == ()

    def test_the_access_restricted_page_normalizes_to_nothing(self) -> None:
        from product_intelligence.research.normalization import normalize_listing_observations

        observations = extract_listing_observations(
            _document("fusionww_access_restricted.html"), source_url=FUSIONWW_URL
        )
        assert observations == ()
        assert normalize_listing_observations(observations) == ()


class TestDeterminism:
    def test_normalizing_the_same_observation_twice_is_identical(self) -> None:
        observations = extract_listing_observations(
            _document("oempcworld_pm9a3_mz_ql23t800.html"), source_url=OEMPCWORLD_URL
        )

        first = normalize_listing_observation(observations[0])
        second = normalize_listing_observation(observations[0])

        assert first == second

    def test_every_recorded_fixture_normalizes_without_raising(self) -> None:
        """Every real fixture, run end to end, whatever it yields."""
        from product_intelligence.research.normalization import normalize_listing_observations

        for name, url in [
            ("samsung_us_pm9a3_mz_ql23t800.html", SAMSUNG_URL),
            ("oempcworld_pm9a3_mz_ql23t800.html", OEMPCWORLD_URL),
            ("exxactcorp_pm9a3_mz_ql23t800.html", EXXACT_URL),
            ("newegg_pm9a3_mz_ql23t800.html", NEWEGG_URL),
            ("fusionww_access_restricted.html", FUSIONWW_URL),
        ]:
            observations = extract_listing_observations(_document(name), source_url=url)
            normalize_listing_observations(observations)  # must not raise
