"""Tests for the compact quote browser presentation (PRODUCT-INTEL.4D-C).

``web/compact_quote_presentation.py`` is a pure display-only module.
These tests prove the display rules without any database, execution,
provider, or research authority involvement:

* vendor source labels: " (Vendor API)" appended exactly once
* public source display: hostname with leading "www." stripped
* vendor rows never receive a source URL
* public row URLs come only from their actual bucket-member assessment
  in deterministic iteration order
* safe URL -> link target; unsafe/missing URL -> plain text
* mapping mismatch fails closed (no guessed links)
* cell values pass through the frozen CompactQuoteRow strings unchanged
"""

from __future__ import annotations

from decimal import Decimal

import pytest

from product_intelligence.domain import ResearchRequest
from product_intelligence.domain.enums import (
    ConfidenceLevel,
    EvidenceDecision,
    IdentityMatchType,
    VerificationStatus,
)
from product_intelligence.research.aggregation import (
    PriceAggregateBucket,
    PriceAggregationResult,
)
from product_intelligence.research.compact_quote import (
    CompactQuoteProjection,
    CompactQuoteRow,
)
from product_intelligence.research.listings import (
    ExtractionMethod,
    ListingObservation,
)
from product_intelligence.research.matching import (
    EvidenceSource,
    ListingIdentityAssessment,
)
from product_intelligence.research.normalization import (
    NormalizedAvailability,
    NormalizedCondition,
    NormalizedListingObservation,
)
from product_intelligence.web.compact_quote_presentation import (
    CompactQuotePresentation,
    CompactQuoteRowDisplay,
    _public_source_display,
    _vendor_source_display,
    build_compact_quote_presentation,
)


# ---------------------------------------------------------------------------
# Builders
# ---------------------------------------------------------------------------


def _vendor_row(
    *,
    source: str = "Ingram",
    price_amount: Decimal = Decimal("2023.27"),
    currency: str = "USD",
    usd_equivalent: str = "$2,023.27 USD",
    usd_amount: Decimal = Decimal("2023.27"),
    inventory: str = "In Stock",
    brand_new: str = "Yes",
    note: "str | None" = None,
) -> CompactQuoteRow:
    return CompactQuoteRow(
        source=source,
        source_type="VENDOR_API",
        price_original=f"${price_amount} {currency}",
        price_amount=price_amount,
        price_currency=currency,
        usd_equivalent=usd_equivalent,
        usd_equivalent_amount=usd_amount,
        inventory=inventory,
        brand_new=brand_new,
        note=note,
    )


def _public_row(
    *,
    source: str = "www.example.com",
    price_amount: Decimal = Decimal("1500.00"),
    currency: str = "EUR",
    price_original: "str | None" = None,
    usd_equivalent: str = "Unavailable",
    usd_amount: "Decimal | None" = None,
    inventory: str = "In Stock",
    brand_new: str = "Yes",
    note: "str | None" = None,
) -> CompactQuoteRow:
    return CompactQuoteRow(
        source=source,
        source_type="PUBLIC_LISTING",
        price_original=price_original if price_original is not None else f"{price_amount} {currency}",
        price_amount=price_amount,
        price_currency=currency,
        usd_equivalent=usd_equivalent,
        usd_equivalent_amount=usd_amount,
        inventory=inventory,
        brand_new=brand_new,
        note=note,
    )


def _make_result(
    mpn: str,
    assessments: tuple[ListingIdentityAssessment, ...],
    buckets: tuple[PriceAggregateBucket, ...],
) -> PriceAggregationResult:
    if len(buckets) == 0:
        status = VerificationStatus.UNKNOWN
    elif len(buckets) == 1:
        status = VerificationStatus.VERIFIED
    else:
        status = VerificationStatus.AMBIGUOUS
    return PriceAggregationResult(
        request=ResearchRequest(manufacturer_part_number=mpn, description="x"),
        assessments=assessments,
        buckets=buckets,
        exclusions=(),
        verification_status=status,
    )


def _make_assessment(
    mpn: str,
    *,
    source_url: "str | None",
    price_amount: Decimal,
    currency_code: str,
) -> ListingIdentityAssessment:
    obs = ListingObservation(
        source_url=source_url,
        extraction_method=ExtractionMethod.JSON_LD,
        product_title="T",
        manufacturer_part_number_text=mpn,
        sku_text=None,
        brand_text=None,
        price_text=str(price_amount),
        currency_text=currency_code,
        availability_text="In Stock",
        condition_text="New",
        seller_text=None,
        offer_url_text=None,
        raw_reference=None,
    )
    norm = NormalizedListingObservation(
        observation=obs,
        price_amount=price_amount,
        currency_code=currency_code,
        availability=NormalizedAvailability.IN_STOCK,
        condition=NormalizedCondition.NEW,
        seller_name=None,
        normalization_issues=(),
    )
    return ListingIdentityAssessment(
        normalized_listing=norm,
        requested_part_number=mpn,
        candidate_part_number_raw=mpn,
        candidate_part_number_compared=mpn,
        candidate_evidence_source=EvidenceSource.EXPLICIT_MPN_FIELD,
        match_type=IdentityMatchType.EXACT,
        decision=EvidenceDecision.ACCEPTED,
        rejection_reason=None,
    )


def _single_bucket(
    mpn: str,
    assessment: ListingIdentityAssessment,
    currency_code: str,
    price_amount: Decimal,
) -> PriceAggregateBucket:
    return PriceAggregateBucket(
        currency_code=currency_code,
        condition=NormalizedCondition.NEW,
        assessments=(assessment,),
        count=1,
        low=price_amount,
        median=price_amount,
        high=price_amount,
        market_range_low=None,
        market_range_high=None,
        confidence=ConfidenceLevel.LOW,
    )


MPN = "PRESENTATION-MPN"


# ---------------------------------------------------------------------------
# Source display rules
# ---------------------------------------------------------------------------


class TestVendorSourceDisplay:
    def test_ingram_gets_suffix(self) -> None:
        assert _vendor_source_display("Ingram") == "Ingram (Vendor API)"

    def test_cdw_gets_suffix(self) -> None:
        assert _vendor_source_display("CDW") == "CDW (Vendor API)"

    def test_synnex_suffix_not_duplicated(self) -> None:
        assert (
            _vendor_source_display("Synnex EU (Vendor API)")
            == "Synnex EU (Vendor API)"
        )

    def test_synnex_base_gets_suffix(self) -> None:
        assert _vendor_source_display("Synnex EU") == "Synnex EU (Vendor API)"

    def test_unknown_vendor_name_gets_suffix(self) -> None:
        assert (
            _vendor_source_display("INTERNAL_VENDOR")
            == "INTERNAL_VENDOR (Vendor API)"
        )


class TestPublicSourceDisplay:
    def test_leading_www_stripped(self) -> None:
        assert _public_source_display("www.example.com") == "example.com"

    def test_no_www_unchanged(self) -> None:
        assert _public_source_display("example.com") == "example.com"

    def test_www_only_strips_leading(self) -> None:
        # "www" mid-label is not a leading host prefix
        assert _public_source_display("sub.www.example.com") == (
            "sub.www.example.com"
        )


# ---------------------------------------------------------------------------
# Vendor rows: display + never a URL
# ---------------------------------------------------------------------------


class TestVendorRowDisplay:
    def test_vendor_row_display_values_pass_through(self) -> None:
        row = _vendor_row(
            source="Ingram",
            inventory="In Stock",
            brand_new="Yes",
            note="CUSTOMER_PRICE",
        )
        result = _make_result(MPN, (), ())
        presentation = build_compact_quote_presentation(
            projection=CompactQuoteProjection(rows=(row,)),
            price_result=result,
        )

        assert isinstance(presentation, CompactQuotePresentation)
        display = presentation.rows[0]
        assert isinstance(display, CompactQuoteRowDisplay)
        assert display.source_display == "Ingram (Vendor API)"
        assert display.source_url is None
        assert display.source_url_safe is False
        assert display.price == row.price_original
        assert display.usd_equivalent == row.usd_equivalent
        assert display.inventory == "In Stock"
        assert display.brand_new == "Yes"
        assert display.note == "CUSTOMER_PRICE"

    def test_vendor_row_never_receives_url_even_if_public_link_matches(self) -> None:
        assessment = _make_assessment(
            MPN,
            source_url="https://www.example.com/product/abc",
            price_amount=Decimal("1500.00"),
            currency_code="EUR",
        )
        result = _make_result(
            MPN, (assessment,), (_single_bucket(MPN, assessment, "EUR", Decimal("1500.00")),)
        )
        vendor = _vendor_row(source="CDW")
        presentation = build_compact_quote_presentation(
            projection=CompactQuoteProjection(rows=(vendor,)),
            price_result=result,
        )
        assert presentation.rows[0].source_display == "CDW (Vendor API)"
        assert presentation.rows[0].source_url is None
        assert presentation.rows[0].source_url_safe is False


# ---------------------------------------------------------------------------
# Public rows: hostname display + safe URL link target
# ---------------------------------------------------------------------------


class TestPublicRowDisplay:
    def test_safe_public_url_link_target(self) -> None:
        assessment = _make_assessment(
            MPN,
            source_url="https://www.example.com/product/abc",
            price_amount=Decimal("1500.00"),
            currency_code="EUR",
        )
        result = _make_result(
            MPN, (assessment,), (_single_bucket(MPN, assessment, "EUR", Decimal("1500.00")),)
        )
        row = _public_row(source="www.example.com")
        presentation = build_compact_quote_presentation(
            projection=CompactQuoteProjection(rows=(row,)),
            price_result=result,
        )

        display = presentation.rows[0]
        # Display: hostname with leading www. stripped
        assert display.source_display == "example.com"
        # Link target: the full SAFE source URL from the bucket-member
        # assessment
        assert display.source_url == "https://www.example.com/product/abc"
        assert display.source_url_safe is True

    def test_javascript_url_not_a_link(self) -> None:
        assessment = _make_assessment(
            MPN,
            source_url="javascript:alert(1)",
            price_amount=Decimal("1500.00"),
            currency_code="EUR",
        )
        result = _make_result(
            MPN, (assessment,), (_single_bucket(MPN, assessment, "EUR", Decimal("1500.00")),)
        )
        # The frozen projection derives the source label from the URL;
        # for a scheme-only URL there is no hostname -> "Unknown Source".
        row = _public_row(source="Unknown Source")
        presentation = build_compact_quote_presentation(
            projection=CompactQuoteProjection(rows=(row,)),
            price_result=result,
        )
        display = presentation.rows[0]
        assert display.source_url_safe is False
        assert display.source_url is None
        assert display.source_display == "Unknown Source"

    def test_data_url_not_a_link(self) -> None:
        assessment = _make_assessment(
            MPN,
            source_url="data:text/html;base64,PHNjcmlwdD4=",
            price_amount=Decimal("1500.00"),
            currency_code="EUR",
        )
        result = _make_result(
            MPN, (assessment,), (_single_bucket(MPN, assessment, "EUR", Decimal("1500.00")),)
        )
        row = _public_row(source="Unknown Source")
        presentation = build_compact_quote_presentation(
            projection=CompactQuoteProjection(rows=(row,)),
            price_result=result,
        )
        assert presentation.rows[0].source_url_safe is False
        assert presentation.rows[0].source_url is None

    def test_file_url_not_a_link(self) -> None:
        assessment = _make_assessment(
            MPN,
            source_url="file:///etc/passwd",
            price_amount=Decimal("1500.00"),
            currency_code="EUR",
        )
        result = _make_result(
            MPN, (assessment,), (_single_bucket(MPN, assessment, "EUR", Decimal("1500.00")),)
        )
        row = _public_row(source="Unknown Source")
        presentation = build_compact_quote_presentation(
            projection=CompactQuoteProjection(rows=(row,)),
            price_result=result,
        )
        assert presentation.rows[0].source_url_safe is False
        assert presentation.rows[0].source_url is None

    def test_unsafe_relative_url_renders_plain_text(self) -> None:
        """A non-http(s) source string is plain text — never an href."""
        assessment = _make_assessment(
            MPN,
            source_url="not-a-url",
            price_amount=Decimal("1500.00"),
            currency_code="EUR",
        )
        result = _make_result(
            MPN, (assessment,), (_single_bucket(MPN, assessment, "EUR", Decimal("1500.00")),)
        )
        row = _public_row(source="Unknown Source")
        presentation = build_compact_quote_presentation(
            projection=CompactQuoteProjection(rows=(row,)),
            price_result=result,
        )
        display = presentation.rows[0]
        assert display.source_display == "Unknown Source"
        assert display.source_url is None
        assert display.source_url_safe is False

    def test_public_cell_values_pass_through(self) -> None:
        assessment = _make_assessment(
            MPN,
            source_url="https://example.com/p",
            price_amount=Decimal("1864.62"),
            currency_code="USD",
        )
        result = _make_result(
            MPN, (assessment,), (_single_bucket(MPN, assessment, "USD", Decimal("1864.62")),)
        )
        row = _public_row(
            source="example.com",
            price_amount=Decimal("1864.62"),
            currency="USD",
            price_original="$1,864.62 USD",
            usd_equivalent="$1,864.62 USD",
            usd_amount=Decimal("1864.62"),
            inventory="Out of Stock",
            brand_new="Unknown",
            note="PREORDER",
        )
        presentation = build_compact_quote_presentation(
            projection=CompactQuoteProjection(rows=(row,)),
            price_result=result,
        )
        display = presentation.rows[0]
        # The frozen row's display strings pass through verbatim —
        # the presentation layer never recomputes them.
        assert display.price == "$1,864.62 USD"
        assert display.usd_equivalent == "$1,864.62 USD"
        assert display.inventory == "Out of Stock"
        assert display.brand_new == "Unknown"
        assert display.note == "PREORDER"


# ---------------------------------------------------------------------------
# Fail-closed mapping reconciliation
# ---------------------------------------------------------------------------


class TestMappingMismatchFailsClosed:
    def test_count_mismatch_withholds_all_links(self) -> None:
        """Two public rows but one bucket-member assessment: the counts
        cannot be reconciled, so NO row receives a guessed link."""
        assessment = _make_assessment(
            MPN,
            source_url="https://www.example.com/product/abc",
            price_amount=Decimal("1500.00"),
            currency_code="EUR",
        )
        result = _make_result(
            MPN, (assessment,), (_single_bucket(MPN, assessment, "EUR", Decimal("1500.00")),)
        )
        row_a = _public_row(source="www.example.com")
        row_b = _public_row(source="other.example.com")
        presentation = build_compact_quote_presentation(
            projection=CompactQuoteProjection(rows=(row_a, row_b)),
            price_result=result,
        )
        for display in presentation.rows:
            assert display.source_url is None
            assert display.source_url_safe is False

    def test_source_label_mismatch_withholds_that_link(self) -> None:
        """The public row's source does not match its paired assessment's
        hostname — the link is withheld for that row (no guess)."""
        assessment = _make_assessment(
            MPN,
            source_url="https://www.example.com/product/abc",
            price_amount=Decimal("1500.00"),
            currency_code="EUR",
        )
        result = _make_result(
            MPN, (assessment,), (_single_bucket(MPN, assessment, "EUR", Decimal("1500.00")),)
        )
        # Row claims a different source than the paired assessment.
        row = _public_row(source="attacker.example.net")
        presentation = build_compact_quote_presentation(
            projection=CompactQuoteProjection(rows=(row,)),
            price_result=result,
        )
        assert presentation.rows[0].source_display == "attacker.example.net"
        assert presentation.rows[0].source_url is None
        assert presentation.rows[0].source_url_safe is False

    def test_deterministic_order_pairs_row_i_with_assessment_i(self) -> None:
        """Two bucket members in two DIFFERENT buckets: row i pairs with
        the i-th assessment in deterministic bucket iteration order —
        each row gets its OWN assessment URL, not the other one's."""
        a1 = _make_assessment(
            MPN,
            source_url="https://www.one.example.com/p1",
            price_amount=Decimal("100.00"),
            currency_code="USD",
        )
        a2 = _make_assessment(
            MPN,
            source_url="https://two.example.com/p2",
            price_amount=Decimal("200.00"),
            currency_code="EUR",
        )
        bucket1 = _single_bucket(MPN, a1, "USD", Decimal("100.00"))
        bucket2 = _single_bucket(MPN, a2, "EUR", Decimal("200.00"))
        result = _make_result(MPN, (a1, a2), (bucket1, bucket2))

        row1 = _public_row(source="www.one.example.com", price_amount=Decimal("100.00"), currency="USD")
        row2 = _public_row(source="two.example.com", price_amount=Decimal("200.00"), currency="EUR")
        presentation = build_compact_quote_presentation(
            projection=CompactQuoteProjection(rows=(row1, row2)),
            price_result=result,
        )
        assert presentation.rows[0].source_url == "https://www.one.example.com/p1"
        assert presentation.rows[0].source_url_safe is True
        assert presentation.rows[0].source_display == "one.example.com"
        assert presentation.rows[1].source_url == "https://two.example.com/p2"
        assert presentation.rows[1].source_url_safe is True
        assert presentation.rows[1].source_display == "two.example.com"


# ---------------------------------------------------------------------------
# Mixed projection: order preserved, vendor first, public linked
# ---------------------------------------------------------------------------


class TestMixedProjection:
    def test_row_order_preserved_vendor_first(self) -> None:
        assessment = _make_assessment(
            MPN,
            source_url="https://www.example.com/product/abc",
            price_amount=Decimal("1500.00"),
            currency_code="EUR",
        )
        result = _make_result(
            MPN, (assessment,), (_single_bucket(MPN, assessment, "EUR", Decimal("1500.00")),)
        )
        ingram = _vendor_row(source="Ingram")
        synnex = _vendor_row(source="Synnex EU (Vendor API)")
        public = _public_row(source="www.example.com")
        presentation = build_compact_quote_presentation(
            projection=CompactQuoteProjection(rows=(ingram, synnex, public)),
            price_result=result,
        )
        displays = presentation.rows
        assert len(displays) == 3
        assert displays[0].source_display == "Ingram (Vendor API)"
        assert displays[1].source_display == "Synnex EU (Vendor API)"
        assert displays[2].source_display == "example.com"
        assert displays[0].source_url is None
        assert displays[1].source_url is None
        assert displays[2].source_url == "https://www.example.com/product/abc"

    def test_empty_projection_yields_zero_rows(self) -> None:
        result = _make_result(MPN, (), ())
        presentation = build_compact_quote_presentation(
            projection=CompactQuoteProjection(rows=()),
            price_result=result,
        )
        assert presentation.rows == ()


# ---------------------------------------------------------------------------
# Display module does not recompute authority
# ---------------------------------------------------------------------------


class TestNoAuthorityRecomputation:
    def test_unavailable_usd_string_preserved(self) -> None:
        """'Unavailable' produced by the frozen row passes through verbatim
        — the display module never recomputes FX or prices."""
        result = _make_result(MPN, (), ())
        row = _public_row(usd_equivalent="Unavailable", usd_amount=None)
        presentation = build_compact_quote_presentation(
            projection=CompactQuoteProjection(rows=(row,)),
            price_result=result,
        )
        assert presentation.rows[0].usd_equivalent == "Unavailable"

    def test_note_none_renders_blank(self) -> None:
        result = _make_result(MPN, (), ())
        row = _vendor_row(note=None)
        presentation = build_compact_quote_presentation(
            projection=CompactQuoteProjection(rows=(row,)),
            price_result=result,
        )
        assert presentation.rows[0].note is None

# ---------------------------------------------------------------------------
# Public quote-only rows
# ---------------------------------------------------------------------------


class TestPublicQuoteOnlyRowDisplay:
    def test_quote_only_row_gets_exact_safe_source(self) -> None:
        from dataclasses import replace

        from product_intelligence.research.aggregation import (
            PriceAggregationExclusion,
            PriceAggregationExclusionReason,
        )
        from product_intelligence.research.compact_quote import (
            project_condition_unknown_quote_rows,
        )

        base = _make_assessment(
            MPN,
            source_url="https://www.example.com/condition-unstated",
            price_amount=Decimal("3149.99"),
            currency_code="USD",
        )
        base_norm = base.normalized_listing
        unknown = replace(
            base,
            normalized_listing=replace(
                base_norm,
                observation=replace(base_norm.observation, condition_text=None),
                condition=NormalizedCondition.UNKNOWN,
            ),
        )
        result = PriceAggregationResult(
            request=ResearchRequest(
                manufacturer_part_number=MPN,
                description="x",
            ),
            assessments=(unknown,),
            exclusions=(
                PriceAggregationExclusion(
                    assessment=unknown,
                    reason=PriceAggregationExclusionReason.UNKNOWN_CONDITION,
                ),
            ),
            buckets=(),
            verification_status=VerificationStatus.UNKNOWN,
        )
        projection = CompactQuoteProjection(
            rows=project_condition_unknown_quote_rows(result)
        )
        presentation = build_compact_quote_presentation(
            projection=projection,
            price_result=result,
        )
        assert len(presentation.rows) == 1
        display = presentation.rows[0]
        assert display.source_display == "example.com"
        assert display.source_url == "https://www.example.com/condition-unstated"
        assert display.source_url_safe is True
        assert display.brand_new == "Unknown"
        assert display.note == "Quote only — condition not stated"


