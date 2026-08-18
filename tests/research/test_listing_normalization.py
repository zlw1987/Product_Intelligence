"""Synthetic normalization edge cases (PRODUCT-INTEL.3B).

Every observation in this file is constructed inline. Real recorded pages are
exercised separately in `test_listing_normalization_recorded_pages.py`; this
file is where every difficult shape from the phase instructions gets a direct,
labelled test — including the abstention paths, which get exactly as much
attention as the successful ones.
"""

from __future__ import annotations

from decimal import Decimal

import pytest

from product_intelligence.research.listings import ExtractionMethod, ListingObservation
from product_intelligence.research.normalization import (
    NormalizationIssue,
    NormalizationIssueCode,
    NormalizedAvailability,
    NormalizedCondition,
    NormalizedListingObservation,
    normalize_listing_observation,
    normalize_listing_observations,
)

URL = "https://example.com/product/1"


def _observation(**fields) -> ListingObservation:
    return ListingObservation(
        source_url=URL, extraction_method=ExtractionMethod.JSON_LD, **fields
    )


class TestArguments:
    def test_a_non_observation_argument_is_a_caller_defect(self) -> None:
        with pytest.raises(TypeError):
            normalize_listing_observation("not an observation")  # type: ignore[arg-type]

    def test_an_observation_with_nothing_published_normalizes_to_all_absent(self) -> None:
        normalized = normalize_listing_observation(_observation())

        assert normalized.price_amount is None
        assert normalized.currency_code is None
        assert normalized.availability is NormalizedAvailability.UNKNOWN
        assert normalized.condition is NormalizedCondition.UNKNOWN
        assert normalized.seller_name is None
        assert normalized.normalization_issues == ()

    def test_the_raw_observation_is_referenced_not_copied(self) -> None:
        observation = _observation(price_text="199.00")
        normalized = normalize_listing_observation(observation)

        assert normalized.observation is observation


class TestPriceGrammarValid:
    @pytest.mark.parametrize(
        ("raw", "expected"),
        [
            ("1055.85", Decimal("1055.85")),
            ("1300.53", Decimal("1300.53")),
            ("1,055.85", Decimal("1055.85")),
            ("10,055.85", Decimal("10055.85")),
            ("1200", Decimal("1200")),
            ("$1,055.85", Decimal("1055.85")),
            ("$399.00", Decimal("399.00")),
            ("EUR 1055.85", Decimal("1055.85")),
            ("0.00", Decimal("0.00")),
        ],
    )
    def test_unambiguous_price_text_becomes_a_decimal(
        self, raw: str, expected: Decimal
    ) -> None:
        normalized = normalize_listing_observation(_observation(price_text=raw))

        assert normalized.price_amount == expected
        assert isinstance(normalized.price_amount, Decimal)
        assert normalized.normalization_issues == ()

    def test_a_valid_price_is_never_represented_as_a_float(self) -> None:
        normalized = normalize_listing_observation(_observation(price_text="1055.85"))

        assert not isinstance(normalized.price_amount, float)
        # Decimal("1055.85") must equal the exact value; a float round-trip
        # through 1055.85 is not guaranteed to.
        assert normalized.price_amount == Decimal("1055.85")


class TestPriceGrammarRefused:
    @pytest.mark.parametrize(
        "raw",
        [
            "undefined",
            "N/A",
            "Call for price",
            "Contact us",
            "from $399",
            "$399 - $449",
            "$399/$449",
            "$2,135.00 $2,700.00",
            "$33/mo",
            "As low as $102.98/mo",
            "20% OFF",
            "You save $565",
            "1.055,85",
            "1,00,055",
        ],
    )
    def test_ambiguous_or_unparseable_price_text_never_becomes_one_amount(
        self, raw: str
    ) -> None:
        normalized = normalize_listing_observation(_observation(price_text=raw))

        assert normalized.price_amount is None
        assert normalized.has_normalization_issues is True
        issue = normalized.normalization_issues[0]
        assert issue.field == "price"
        assert issue.code in (
            NormalizationIssueCode.INVALID_PRICE,
            NormalizationIssueCode.AMBIGUOUS_PRICE,
        )
        assert issue.raw_value == raw

    def test_undefined_does_not_become_zero(self) -> None:
        """The exact failure mode 3A's manufacturer fixture demonstrated."""
        normalized = normalize_listing_observation(_observation(price_text="undefined"))

        assert normalized.price_amount is None
        assert normalized.price_amount != Decimal("0")

    @pytest.mark.parametrize(
        "raw",
        [
            "from $399",
            "$399 - $449",
            "$399/$449",
            "$2,135.00 $2,700.00",
            "$33/mo",
            "As low as $102.98/mo",
            "You save $565",
        ],
    )
    def test_range_financing_and_discount_text_is_classified_ambiguous(
        self, raw: str
    ) -> None:
        """A single amount is never chosen from text naming more than one."""
        normalized = normalize_listing_observation(_observation(price_text=raw))

        assert normalized.normalization_issues[0].code is (
            NormalizationIssueCode.AMBIGUOUS_PRICE
        )

    def test_no_price_published_leaves_price_absent_without_an_issue(self) -> None:
        """Absence is not an error; there is nothing to fail to normalize."""
        normalized = normalize_listing_observation(_observation())

        assert normalized.price_amount is None
        assert normalized.normalization_issues == ()


class TestCurrency:
    @pytest.mark.parametrize(
        ("raw", "expected"),
        [
            ("USD", "USD"),
            ("usd", "USD"),
            ("EUR", "EUR"),
            ("GBP", "GBP"),
            ("€", "EUR"),
            ("£", "GBP"),
        ],
    )
    def test_recognized_currency_text_normalizes(self, raw: str, expected: str) -> None:
        normalized = normalize_listing_observation(_observation(currency_text=raw))

        assert normalized.currency_code == expected
        assert normalized.normalization_issues == ()

    @pytest.mark.parametrize("raw", ["$", "¥", "nonsense", "Dollars", "US$"])
    def test_unrecognized_or_ambiguous_currency_text_abstains(self, raw: str) -> None:
        """`$` and `¥` are shared by several currencies and are never guessed."""
        normalized = normalize_listing_observation(_observation(currency_text=raw))

        assert normalized.currency_code is None
        assert any(
            issue.field == "currency"
            and issue.code == NormalizationIssueCode.UNRECOGNIZED_CURRENCY
            for issue in normalized.normalization_issues
        )

    def test_a_dollar_sign_in_a_price_does_not_imply_usd_currency(self) -> None:
        """`$` establishing USD globally is exactly the inference this module refuses."""
        normalized = normalize_listing_observation(_observation(price_text="$1,055.85"))

        assert normalized.price_amount == Decimal("1055.85")
        assert normalized.currency_code is None

    def test_price_and_currency_are_independent_state_a(self) -> None:
        normalized = normalize_listing_observation(
            _observation(price_text="1055.85", currency_text="USD")
        )

        assert normalized.price_amount == Decimal("1055.85")
        assert normalized.currency_code == "USD"

    def test_price_and_currency_are_independent_state_b(self) -> None:
        """A valid price with no currency evidence."""
        normalized = normalize_listing_observation(_observation(price_text="1300.53"))

        assert normalized.price_amount == Decimal("1300.53")
        assert normalized.currency_code is None

    def test_price_and_currency_are_independent_state_c(self) -> None:
        """Currency evidence with no usable price."""
        normalized = normalize_listing_observation(
            _observation(price_text="undefined", currency_text="USD")
        )

        assert normalized.price_amount is None
        assert normalized.currency_code == "USD"

    def test_price_and_currency_are_independent_state_d(self) -> None:
        normalized = normalize_listing_observation(_observation())

        assert normalized.price_amount is None
        assert normalized.currency_code is None

    def test_no_fx_conversion_exists_between_currencies(self) -> None:
        """Two observations in different currencies stay in their own currencies."""
        usd = normalize_listing_observation(
            _observation(price_text="100", currency_text="USD")
        )
        eur = normalize_listing_observation(
            _observation(price_text="90", currency_text="EUR")
        )

        assert usd.currency_code == "USD"
        assert eur.currency_code == "EUR"
        assert usd.price_amount == Decimal("100")
        assert eur.price_amount == Decimal("90")
        # Nothing here converts, compares magnitude across currencies, or
        # picks a min/max between them — that is 4A's, with comparability
        # rules this module does not implement.


class TestEmbeddedCurrencyReconciliation:
    """A currency embedded in price_text is real evidence, and evidence that
    disagrees with currency_text must not be silently discarded — the defect
    this class exists to pin down."""

    def test_a_currency_embedded_as_a_leading_code_is_used_when_currency_text_is_absent(
        self,
    ) -> None:
        normalized = normalize_listing_observation(_observation(price_text="EUR 100"))

        assert normalized.price_amount == Decimal("100")
        assert normalized.currency_code == "EUR"
        assert normalized.normalization_issues == ()

    def test_a_currency_embedded_as_a_trailing_code_is_used_when_currency_text_is_absent(
        self,
    ) -> None:
        normalized = normalize_listing_observation(_observation(price_text="100 EUR"))

        assert normalized.price_amount == Decimal("100")
        assert normalized.currency_code == "EUR"

    def test_a_currency_embedded_as_an_unambiguous_symbol_is_used(self) -> None:
        normalized = normalize_listing_observation(_observation(price_text="€100"))

        assert normalized.price_amount == Decimal("100")
        assert normalized.currency_code == "EUR"

    def test_a_dollar_sign_alone_still_leaves_currency_unknown(self) -> None:
        normalized = normalize_listing_observation(_observation(price_text="$100"))

        assert normalized.price_amount == Decimal("100")
        assert normalized.currency_code is None
        assert not any(
            issue.field == "currency" for issue in normalized.normalization_issues
        )

    def test_currency_text_alone_still_applies_when_price_has_no_embedded_currency(
        self,
    ) -> None:
        normalized = normalize_listing_observation(
            _observation(price_text="$100", currency_text="USD")
        )

        assert normalized.price_amount == Decimal("100")
        assert normalized.currency_code == "USD"
        assert normalized.normalization_issues == ()

    def test_agreeing_embedded_and_published_currency_reinforce_one_result(
        self,
    ) -> None:
        normalized = normalize_listing_observation(
            _observation(price_text="EUR 100", currency_text="EUR")
        )

        assert normalized.price_amount == Decimal("100")
        assert normalized.currency_code == "EUR"
        assert normalized.normalization_issues == ()

    def test_conflicting_embedded_code_and_published_currency_abstain(self) -> None:
        normalized = normalize_listing_observation(
            _observation(price_text="EUR 100", currency_text="USD")
        )

        assert normalized.price_amount == Decimal("100")
        assert normalized.currency_code is None
        assert any(
            issue.field == "currency"
            and issue.code == NormalizationIssueCode.CONFLICTING_CURRENCY
            for issue in normalized.normalization_issues
        )

    def test_conflicting_embedded_symbol_and_published_currency_abstain(self) -> None:
        normalized = normalize_listing_observation(
            _observation(price_text="€100", currency_text="USD")
        )

        assert normalized.price_amount == Decimal("100")
        assert normalized.currency_code is None
        assert any(
            issue.field == "currency"
            and issue.code == NormalizationIssueCode.CONFLICTING_CURRENCY
            for issue in normalized.normalization_issues
        )

    def test_a_price_conflict_does_not_remove_an_otherwise_valid_amount(self) -> None:
        """The amount and its comparability are separate questions."""
        normalized = normalize_listing_observation(
            _observation(price_text="EUR 100", currency_text="USD")
        )

        assert normalized.price_amount is not None
        assert normalized.price_amount == Decimal("100")

    @pytest.mark.parametrize(
        "raw",
        ["EUR 100 USD", "EUR 100 GBP", "€100 GBP", "$100 EUR"],
    )
    def test_double_currency_decoration_never_normalizes_cleanly(
        self, raw: str
    ) -> None:
        """A currency marker on both sides of the amount is never accepted,
        agreeing or not — see the module docstring on why."""
        normalized = normalize_listing_observation(_observation(price_text=raw))

        assert normalized.price_amount is None
        assert normalized.has_normalization_issues is True
        assert normalized.normalization_issues[0].field == "price"

    def test_double_decoration_does_not_silently_pick_either_side(self) -> None:
        normalized = normalize_listing_observation(
            _observation(price_text="EUR 100 USD", currency_text="GBP")
        )

        # The price itself failed to parse, so there is no embedded currency
        # to reconcile; only the separately published currency_text applies.
        assert normalized.price_amount is None
        assert normalized.currency_code == "GBP"


class TestAvailability:
    @pytest.mark.parametrize(
        ("raw", "expected"),
        [
            ("https://schema.org/InStock", NormalizedAvailability.IN_STOCK),
            ("http://schema.org/InStock", NormalizedAvailability.IN_STOCK),
            ("https://schema.org/OutOfStock", NormalizedAvailability.OUT_OF_STOCK),
            ("http://schema.org/OutOfStock", NormalizedAvailability.OUT_OF_STOCK),
            ("in stock", NormalizedAvailability.IN_STOCK),
            ("out of stock", NormalizedAvailability.OUT_OF_STOCK),
            ("InStock", NormalizedAvailability.IN_STOCK),
            ("preorder", NormalizedAvailability.PREORDER),
            ("pre-order", NormalizedAvailability.PREORDER),
            ("backorder", NormalizedAvailability.BACKORDER),
        ],
    )
    def test_recognized_availability_text_normalizes(
        self, raw: str, expected: NormalizedAvailability
    ) -> None:
        normalized = normalize_listing_observation(_observation(availability_text=raw))

        assert normalized.availability is expected
        assert normalized.normalization_issues == ()

    @pytest.mark.parametrize("raw", ["false", "true", "yes", "in transit", "limited-ish"])
    def test_unrecognized_availability_text_abstains_rather_than_guessing(
        self, raw: str
    ) -> None:
        normalized = normalize_listing_observation(_observation(availability_text=raw))

        assert normalized.availability is NormalizedAvailability.UNKNOWN
        assert any(
            issue.field == "availability"
            and issue.code == NormalizationIssueCode.UNRECOGNIZED_AVAILABILITY
            for issue in normalized.normalization_issues
        )

    def test_false_specifically_does_not_become_out_of_stock(self) -> None:
        """The exact real-world case this module must not guess at."""
        normalized = normalize_listing_observation(_observation(availability_text="false"))

        assert normalized.availability is not NormalizedAvailability.OUT_OF_STOCK
        assert normalized.availability is NormalizedAvailability.UNKNOWN

    def test_no_availability_published_leaves_it_unknown_without_an_issue(self) -> None:
        normalized = normalize_listing_observation(_observation())

        assert normalized.availability is NormalizedAvailability.UNKNOWN
        assert normalized.normalization_issues == ()


class TestCondition:
    @pytest.mark.parametrize(
        ("raw", "expected"),
        [
            ("https://schema.org/NewCondition", NormalizedCondition.NEW),
            ("http://schema.org/NewCondition", NormalizedCondition.NEW),
            ("UsedCondition", NormalizedCondition.USED),
            ("RefurbishedCondition", NormalizedCondition.REFURBISHED),
            ("DamagedCondition", NormalizedCondition.DAMAGED),
            ("new", NormalizedCondition.NEW),
            ("used", NormalizedCondition.USED),
            ("refurbished", NormalizedCondition.REFURBISHED),
            ("refurb", NormalizedCondition.REFURBISHED),
        ],
    )
    def test_recognized_condition_text_normalizes(
        self, raw: str, expected: NormalizedCondition
    ) -> None:
        normalized = normalize_listing_observation(_observation(condition_text=raw))

        assert normalized.condition is expected
        assert normalized.normalization_issues == ()

    @pytest.mark.parametrize("raw", ["open box", "like new", "mint", "gently used"])
    def test_unmapped_marketing_prose_is_not_classified(self, raw: str) -> None:
        """No deliberate, tested policy exists for these yet — abstention is correct."""
        normalized = normalize_listing_observation(_observation(condition_text=raw))

        assert normalized.condition is NormalizedCondition.UNKNOWN
        assert any(
            issue.field == "condition"
            and issue.code == NormalizationIssueCode.UNRECOGNIZED_CONDITION
            for issue in normalized.normalization_issues
        )

    def test_no_condition_published_leaves_it_unknown_without_an_issue(self) -> None:
        normalized = normalize_listing_observation(_observation())

        assert normalized.condition is NormalizedCondition.UNKNOWN
        assert normalized.normalization_issues == ()


class TestSeller:
    def test_surrounding_whitespace_is_removed(self) -> None:
        normalized = normalize_listing_observation(
            _observation(seller_text="  Acme Direct  ")
        )
        # ListingObservation itself already strips surrounding whitespace on
        # construction; this proves normalization does not reintroduce it and
        # is exercised again below with internal whitespace, which
        # ListingObservation does not touch.
        assert normalized.seller_name == "Acme Direct"

    def test_internal_whitespace_runs_collapse(self) -> None:
        normalized = normalize_listing_observation(
            _observation(seller_text="Acme    Direct\tStore")
        )

        assert normalized.seller_name == "Acme Direct Store"

    def test_seller_identity_is_not_resolved(self) -> None:
        """No entity resolution: distinct spellings of one real seller stay distinct."""
        amazon_dot_com = normalize_listing_observation(
            _observation(seller_text="Amazon.com")
        )
        amazon = normalize_listing_observation(_observation(seller_text="Amazon"))

        assert amazon_dot_com.seller_name == "Amazon.com"
        assert amazon.seller_name == "Amazon"
        assert amazon_dot_com.seller_name != amazon.seller_name

    def test_seller_punctuation_and_case_are_preserved(self) -> None:
        normalized = normalize_listing_observation(
            _observation(seller_text="ACME, Inc.")
        )

        assert normalized.seller_name == "ACME, Inc."

    def test_no_seller_published_stays_none(self) -> None:
        normalized = normalize_listing_observation(_observation())

        assert normalized.seller_name is None


class TestNoIdentityFieldsAreTouched:
    def test_the_published_mpn_text_is_not_normalized_or_altered(self) -> None:
        """3B normalizes commercial attributes, never identity (§24)."""
        observation = _observation(manufacturer_part_number_text="mpn:MZ-QL23T800")
        normalized = normalize_listing_observation(observation)

        assert normalized.observation.manufacturer_part_number_text == "mpn:MZ-QL23T800"

    def test_the_identity_comparator_is_never_imported_or_called(self) -> None:
        import ast

        import product_intelligence.research.normalization as normalization_module

        source = open(normalization_module.__file__, encoding="utf-8").read()
        assert "compare_part_numbers" not in source
        assert "compare_request_to_candidate" not in source

        tree = ast.parse(source)
        imported = {
            alias.name
            for node in ast.walk(tree)
            if isinstance(node, ast.ImportFrom)
            for alias in node.names
        } | {
            node.module
            for node in ast.walk(tree)
            if isinstance(node, ast.ImportFrom) and node.module
        }
        assert "product_intelligence.research.identity" not in imported


class TestNoAcceptanceOrAggregationFields:
    def test_the_normalized_contract_carries_no_acceptance_or_match_field(self) -> None:
        from dataclasses import fields

        names = {field.name for field in fields(NormalizedListingObservation)}

        for forbidden in (
            "accepted",
            "rejected",
            "valid_listing",
            "identity_match",
            "confidence",
            "should_use_for_price",
            "aggregate_eligible",
            "match_type",
            "score",
            "quantity",
            "pack_size",
            "unit_price",
        ):
            assert forbidden not in names, forbidden

    def test_the_normalized_contract_has_no_min_max_median_or_range(self) -> None:
        from dataclasses import fields

        names = {field.name for field in fields(NormalizedListingObservation)}

        for forbidden in ("min", "max", "median", "average", "market_range", "estimate"):
            assert forbidden not in names


class TestBulkNormalization:
    def test_normalizing_an_empty_iterable_yields_nothing(self) -> None:
        assert normalize_listing_observations([]) == ()

    def test_normalizing_several_observations_preserves_order_and_count(self) -> None:
        observations = [
            _observation(price_text="100.00"),
            _observation(price_text="undefined"),
            _observation(price_text="200.00"),
        ]

        normalized = normalize_listing_observations(observations)

        assert len(normalized) == 3
        assert [n.price_amount for n in normalized] == [
            Decimal("100.00"),
            None,
            Decimal("200.00"),
        ]

    def test_it_performs_no_orchestration(self) -> None:
        """No fetching, no searching, no persistence — pure transformation only."""
        import product_intelligence.research.normalization as normalization_module

        source = open(normalization_module.__file__, encoding="utf-8").read()
        for forbidden in ("requests", "urlopen", "search(", ".save(", ".objects."):
            assert forbidden not in source


class TestDeterminism:
    def test_repeated_normalization_of_the_same_observation_is_identical(self) -> None:
        observation = _observation(
            price_text="1,055.85",
            currency_text="USD",
            availability_text="https://schema.org/InStock",
            condition_text="new",
            seller_text="Acme  Direct",
        )

        results = [normalize_listing_observation(observation) for _ in range(5)]

        assert all(result == results[0] for result in results)

    def test_equal_but_distinct_observations_normalize_identically(self) -> None:
        one = _observation(price_text="199.00", currency_text="USD")
        other = _observation(price_text="199.00", currency_text="USD")

        assert normalize_listing_observation(one) == normalize_listing_observation(other)


class TestNormalizationIssueConstruction:
    def test_a_blank_field_is_rejected(self) -> None:
        with pytest.raises(ValueError):
            NormalizationIssue(
                field="   ",
                code=NormalizationIssueCode.INVALID_PRICE,
                raw_value="x",
                reason="because",
            )

    def test_a_blank_reason_is_rejected(self) -> None:
        with pytest.raises(ValueError):
            NormalizationIssue(
                field="price",
                code=NormalizationIssueCode.INVALID_PRICE,
                raw_value="x",
                reason="   ",
            )

    def test_a_non_enum_code_is_a_caller_defect(self) -> None:
        with pytest.raises(TypeError):
            NormalizationIssue(
                field="price", code="INVALID_PRICE", raw_value="x", reason="because"  # type: ignore[arg-type]
            )


class TestNoFloatEverEntersMoney:
    def test_the_normalization_module_never_imports_or_constructs_a_float_for_price(
        self,
    ) -> None:
        import ast

        import product_intelligence.research.normalization as normalization_module

        tree = ast.parse(open(normalization_module.__file__, encoding="utf-8").read())
        float_calls = [
            node
            for node in ast.walk(tree)
            if isinstance(node, ast.Call)
            and isinstance(node.func, ast.Name)
            and node.func.id == "float"
        ]
        assert float_calls == []


class TestCurrencyIsNeverInferredFromSourceOrDomain:
    def test_a_dollar_priced_item_from_a_dot_com_domain_gets_no_currency(self) -> None:
        """The source URL's TLD is not currency evidence; nothing here reads it."""
        observation = ListingObservation(
            source_url="https://shop.example.com/product/1",
            extraction_method=ExtractionMethod.JSON_LD,
            price_text="$199.00",
        )

        normalized = normalize_listing_observation(observation)

        assert normalized.price_amount == Decimal("199.00")
        assert normalized.currency_code is None

    def test_currency_normalization_never_looks_at_source_url(self) -> None:
        import ast

        import product_intelligence.research.normalization as normalization_module

        tree = ast.parse(open(normalization_module.__file__, encoding="utf-8").read())
        source_url_reads = [
            node
            for node in ast.walk(tree)
            if isinstance(node, ast.Attribute) and node.attr == "source_url"
        ]
        assert source_url_reads == []


class TestMalformedAndUnusualInputDoesNotCrash:
    @pytest.mark.parametrize(
        "raw",
        [
            "",  # would already be None via ListingObservation, tested directly here
            "   ",
            "-199.00",
            "199.00.50",
            "9" * 200,
            "1,055.85 ",
            " $1,055.85",
            " 199.00 ",  # surrounding whitespace; ListingObservation already strips it
            " 199.00 ",  # non-breaking space padding
            "😀199",
            "价格未知",
            "\t\n199.00\t\n",
        ],
    )
    def test_unusual_price_text_never_raises(self, raw: str) -> None:
        observation = ListingObservation(
            source_url=URL, extraction_method=ExtractionMethod.JSON_LD, price_text=raw or None
        )

        normalize_listing_observation(observation)  # must not raise

    def test_a_negative_looking_price_is_not_silently_made_positive(self) -> None:
        """No sign handling is implemented; a leading '-' must not parse to a
        positive amount by accident of the regex stripping it unnoticed."""
        normalized = normalize_listing_observation(_observation(price_text="-199.00"))

        assert normalized.price_amount is None

    def test_a_price_with_trailing_whitespace_still_parses(self) -> None:
        normalized = normalize_listing_observation(_observation(price_text="1,055.85 "))

        assert normalized.price_amount == Decimal("1055.85")

    def test_tabs_and_newlines_around_a_price_still_parse(self) -> None:
        normalized = normalize_listing_observation(
            _observation(price_text="\t\n199.00\t\n")
        )

        assert normalized.price_amount == Decimal("199.00")


class TestReprAndEquality:
    def test_a_normalized_observation_has_a_usable_repr(self) -> None:
        normalized = normalize_listing_observation(
            _observation(price_text="199.00", currency_text="USD")
        )

        text = repr(normalized)

        assert "199.00" in text
        assert "USD" in text

    def test_two_normalizations_of_equal_observations_are_equal(self) -> None:
        first = normalize_listing_observation(_observation(price_text="199.00"))
        second = normalize_listing_observation(_observation(price_text="199.00"))

        assert first == second
        assert hash(first) == hash(second)
