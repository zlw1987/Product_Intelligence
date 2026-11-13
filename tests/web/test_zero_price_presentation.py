"""Zero / placeholder price quality — B1 presentation-notice contract.

PRODUCT-INTEL.PILOT-VALUE-PRICE-QUALITY-B1 (bounded evidence investigation
+ conditional implementation; base = verified FU2 baseline).

The three distinct concepts this file keeps apart:

* SOURCE_PUBLISHED_PRICE — the monetary amount the source actually
  published, including ``0``. The frozen 3B grammar parses a published
  ``"0"`` / ``"0.00"`` into a numeric Decimal, and the raw evidence is
  preserved verbatim. Neither fact is changed here.
* PRICE_ELIGIBILITY — the frozen 4A contract. A published zero, with
  accepted identity, a currency, and a known condition, remains
  bucket-eligible exactly like any other numeric price; ``0`` is never
  converted to missing, inferred to another value, or excluded. The
  Reviewed Price authority applies the same non-identity criteria.
* PROCUREMENT_ACTIONABILITY — whether a purchasing employee should treat
  the offer as suitable for obtaining a real supplier quote or placing an
  order. B1 makes ONLY this last concept visible: the Quote & Market
  Summary appends a bounded, neutral verification note to rows whose
  source-published price is exactly zero. The note does not call the
  source fraudulent, does not claim the price is definitely a placeholder
  or a free product, and does not claim supplier availability has been
  confirmed.

Everything in this file is synthetic (example hostnames, a generic test
MPN). No production URL, customer part number, credential, or commercial
value is recorded here.

Frozen surfaces re-proven unchanged by these tests: normalization, 4A
aggregation (Machine Price), Reviewed Price aggregation, the
PriceIntelligenceSnapshot codec, and the compact-quote projection
authority (``project_public_rows`` / ``project_condition_unknown_quote_rows``
read frozen 4A bucket membership exactly as before).
"""

from __future__ import annotations

from decimal import Decimal
from html.parser import HTMLParser

import pytest
from django.test import Client
from django.urls import reverse

from product_intelligence.domain import ResearchRequest
from product_intelligence.domain.enums import (
    EvidenceDecision,
    IdentityMatchType,
    VerificationStatus,
)
from product_intelligence.research.aggregation import (
    PriceAggregationExclusionReason,
    aggregate_listing_prices,
    aggregate_reviewed_listing_prices,
)
from product_intelligence.research.compact_quote import (
    CompactQuoteProjection,
    CompactQuoteRow,
    project_condition_unknown_quote_rows,
    project_public_rows,
)
from product_intelligence.research.listings import ExtractionMethod, ListingObservation
from product_intelligence.research.matching import (
    EvidenceSource,
    IdentityRejectionReason,
    ListingIdentityAssessment,
)
from product_intelligence.research.normalization import (
    NormalizedAvailability,
    NormalizedCondition,
    NormalizedListingObservation,
    normalize_listing_observation,
)
from product_intelligence.research.price_result_codec import (
    decode_price_aggregation_result,
    encode_price_aggregation_result,
)
from product_intelligence.web.compact_quote_presentation import (
    build_compact_quote_presentation,
)

# ---------------------------------------------------------------------------
# Synthetic constants — no production values are recorded in this file.
# ---------------------------------------------------------------------------

MPN = "B1-ZERO-TEST-MPN"
ZERO_HOST_URL = "https://zero-offer.example/product"
POS_HOST_URL = "https://positive-offer.example/product"
HC_HOST_URL = "https://confirmed-offer.example/product"


def _expected_zero_note(price_original: str) -> str:
    """The exact bounded neutral B1 notice for one published price string."""
    return (
        f"Source-published price: {price_original}"
        " \u2014 Verify price and purchasing availability with the supplier."
    )


# ---------------------------------------------------------------------------
# Builders
# ---------------------------------------------------------------------------


def _observation(
    *,
    source_url: str,
    price_text: "str | None",
    currency_text: "str | None" = "USD",
    condition_text: "str | None" = "New",
    availability_text: "str | None" = None,
) -> ListingObservation:
    return ListingObservation(
        source_url=source_url,
        extraction_method=ExtractionMethod.JSON_LD,
        product_title="B1 Zero Price Test Product",
        manufacturer_part_number_text=MPN,
        sku_text=None,
        brand_text=None,
        price_text=price_text,
        currency_text=currency_text,
        availability_text=availability_text,
        condition_text=condition_text,
        seller_text=None,
        offer_url_text=None,
        raw_reference=None,
    )


def _accepted_assessment(
    observation: ListingObservation,
    price_amount: Decimal,
    currency_code: str,
    condition: NormalizedCondition,
    availability: NormalizedAvailability = NormalizedAvailability.UNKNOWN,
) -> ListingIdentityAssessment:
    norm = NormalizedListingObservation(
        observation=observation,
        price_amount=price_amount,
        currency_code=currency_code,
        availability=availability,
        condition=condition,
        seller_name=None,
        normalization_issues=(),
    )
    return ListingIdentityAssessment(
        normalized_listing=norm,
        requested_part_number=MPN,
        candidate_part_number_raw=MPN,
        candidate_part_number_compared=MPN,
        candidate_evidence_source=EvidenceSource.EXPLICIT_MPN_FIELD,
        match_type=IdentityMatchType.EXACT,
        decision=EvidenceDecision.ACCEPTED,
        rejection_reason=None,
    )


def _human_eligible_rejected_assessment(
    observation: ListingObservation,
    price_amount: Decimal,
    currency_code: str,
    condition: NormalizedCondition,
) -> ListingIdentityAssessment:
    """The frozen FU3B semantic-eligible shape: REJECTED +
    NO_EXPLICIT_MPN_EVIDENCE + SKU_FIELD (human-review eligible).

    The observation publishes NO explicit MPN field — only the retailer
    SKU — so the assessment's evidence provenance is consistent with the
    underlying listing (the 3C constructor refuses fabricated evidence).
    """
    norm = NormalizedListingObservation(
        observation=observation,
        price_amount=price_amount,
        currency_code=currency_code,
        availability=NormalizedAvailability.UNKNOWN,
        condition=condition,
        seller_name=None,
        normalization_issues=(),
    )
    return ListingIdentityAssessment(
        normalized_listing=norm,
        requested_part_number=MPN,
        candidate_part_number_raw="B1-ZERO-SKU",
        candidate_part_number_compared="B1-ZERO-SKU",
        candidate_evidence_source=EvidenceSource.SKU_FIELD,
        match_type=IdentityMatchType.UNKNOWN,
        decision=EvidenceDecision.REJECTED,
        rejection_reason=IdentityRejectionReason.NO_EXPLICIT_MPN_EVIDENCE,
    )


def _request() -> ResearchRequest:
    return ResearchRequest(manufacturer_part_number=MPN, description="B1 zero price")


def _presentation_for(
    result,
    projection: CompactQuoteProjection,
    *,
    confirmed: "frozenset[int] | None" = None,
):
    return build_compact_quote_presentation(
        projection=projection,
        price_result=result,
        confirmed_assessment_indices=confirmed,
    ), result


# ---------------------------------------------------------------------------
# SOURCE_PUBLISHED_PRICE — a published zero stays a published zero
# ---------------------------------------------------------------------------


class TestSourcePublishedPriceContract:
    def test_published_zero_point_zero_remains_a_numeric_decimal(self) -> None:
        normalized = normalize_listing_observation(
            _observation(source_url=ZERO_HOST_URL, price_text="0.00")
        )
        assert normalized.price_amount == Decimal("0.00")
        assert isinstance(normalized.price_amount, Decimal)
        assert not isinstance(normalized.price_amount, float)
        assert normalized.normalization_issues == ()

    def test_published_bare_zero_remains_a_numeric_decimal(self) -> None:
        normalized = normalize_listing_observation(
            _observation(source_url=ZERO_HOST_URL, price_text="0")
        )
        assert normalized.price_amount == Decimal("0")
        assert isinstance(normalized.price_amount, Decimal)
        assert normalized.normalization_issues == ()

    def test_zero_with_symbol_remains_numeric_and_currency_preserved(self) -> None:
        normalized = normalize_listing_observation(
            _observation(source_url=ZERO_HOST_URL, price_text="$0.00")
        )
        assert normalized.price_amount == Decimal("0.00")
        # "$" alone never resolves a currency; the separately published
        # USD evidence is the source of the code, unchanged by B1.
        assert normalized.currency_code == "USD"

    def test_raw_price_evidence_is_unchanged_for_a_published_zero(self) -> None:
        observation = _observation(source_url=ZERO_HOST_URL, price_text="0.00")
        normalized = normalize_listing_observation(observation)
        # The exact raw observation is preserved, byte-for-byte fields.
        assert normalized.observation is observation
        assert observation.price_text == "0.00"
        assert observation.currency_text == "USD"
        assert observation.condition_text == "New"
        assert normalized.price_amount == Decimal("0.00")
        assert normalized.currency_code == "USD"
        assert normalized.condition is NormalizedCondition.NEW

    def test_missing_price_is_never_represented_as_zero(self) -> None:
        normalized = normalize_listing_observation(
            _observation(source_url=ZERO_HOST_URL, price_text="undefined")
        )
        assert normalized.price_amount is None
        assert normalized.price_amount != Decimal("0")

    def test_ambiguous_price_is_never_represented_as_zero(self) -> None:
        normalized = normalize_listing_observation(
            _observation(source_url=ZERO_HOST_URL, price_text="$0.00 - $50.00")
        )
        assert normalized.price_amount is None

    def test_zero_price_with_absent_condition_stays_unknown(self) -> None:
        normalized = normalize_listing_observation(
            _observation(source_url=ZERO_HOST_URL, price_text="0", condition_text=None)
        )
        assert normalized.price_amount == Decimal("0")
        assert normalized.condition is NormalizedCondition.UNKNOWN


# ---------------------------------------------------------------------------
# PRICE_ELIGIBILITY — frozen 4A / Reviewed Price authority unchanged
# ---------------------------------------------------------------------------


class TestPricingAuthorityUnchanged:
    def test_published_zero_still_enters_the_machine_price_bucket(self) -> None:
        obs = _observation(source_url=ZERO_HOST_URL, price_text="0")
        assessment = _accepted_assessment(obs, Decimal("0"), "USD", NormalizedCondition.NEW)
        result = aggregate_listing_prices(_request(), (assessment,))

        assert result.verification_status is VerificationStatus.VERIFIED
        assert result.exclusions == ()
        assert len(result.buckets) == 1
        bucket = result.buckets[0]
        assert bucket.currency_code == "USD"
        assert bucket.condition is NormalizedCondition.NEW
        assert bucket.count == 1
        assert bucket.low == bucket.median == bucket.high == Decimal("0")
        # One observation is not a market range: frozen 4A keeps it None.
        assert bucket.market_range_low is None
        assert bucket.market_range_high is None

    def test_published_zero_still_combines_with_positive_prices(self) -> None:
        a_zero = _accepted_assessment(
            _observation(source_url=ZERO_HOST_URL, price_text="0"),
            Decimal("0"),
            "USD",
            NormalizedCondition.NEW,
        )
        a_pos = _accepted_assessment(
            _observation(source_url=POS_HOST_URL, price_text="1500.00"),
            Decimal("1500.00"),
            "USD",
            NormalizedCondition.NEW,
        )
        result = aggregate_listing_prices(_request(), (a_zero, a_pos))

        # Frozen 4A behavior of record: the zero contributes to the same
        # bucket and moves low and median exactly as any numeric value.
        assert len(result.buckets) == 1
        bucket = result.buckets[0]
        assert bucket.count == 2
        assert bucket.low == Decimal("0")
        assert bucket.median == Decimal("750.00")
        assert bucket.high == Decimal("1500.00")

    def test_zero_price_with_unknown_condition_is_still_excluded(self) -> None:
        obs = _observation(source_url=ZERO_HOST_URL, price_text="0", condition_text=None)
        assessment = _accepted_assessment(obs, Decimal("0"), "USD", NormalizedCondition.UNKNOWN)
        result = aggregate_listing_prices(_request(), (assessment,))

        assert result.buckets == ()
        assert result.verification_status is VerificationStatus.UNKNOWN
        assert len(result.exclusions) == 1
        assert result.exclusions[0].reason is PriceAggregationExclusionReason.UNKNOWN_CONDITION
        # The zero is not relabelled, inferred, or dropped: it is retained.
        assert result.exclusions[0].assessment is assessment

    def test_reviewed_price_authority_unchanged_for_published_zero(self) -> None:
        obs = _observation(source_url=ZERO_HOST_URL, price_text="0")
        assessment = _accepted_assessment(obs, Decimal("0"), "USD", NormalizedCondition.NEW)
        reviewed = aggregate_reviewed_listing_prices(
            _request(), (assessment,), frozenset()
        )

        assert reviewed.verification_status is VerificationStatus.VERIFIED
        assert len(reviewed.buckets) == 1
        bucket = reviewed.buckets[0]
        assert bucket.low == bucket.median == bucket.high == Decimal("0")
        assert bucket.deterministic_count == 1
        assert bucket.human_confirmed_count == 0

    def test_snapshot_codec_round_trip_preserves_a_zero_bucket(self) -> None:
        obs = _observation(source_url=ZERO_HOST_URL, price_text="0")
        assessment = _accepted_assessment(obs, Decimal("0"), "USD", NormalizedCondition.NEW)
        result = aggregate_listing_prices(_request(), (assessment,))

        payload = encode_price_aggregation_result(result)
        decoded = decode_price_aggregation_result(payload, schema_version=1)

        # Historical snapshot interpretation remains intact: the persisted
        # zero bucket decodes to the identical frozen result.
        assert decoded == result
        assert decoded.buckets[0].low == Decimal("0")
        # The raw published evidence survives the round trip verbatim.
        decoded_assessment = decoded.assessments[0]
        assert decoded_assessment.normalized_listing.observation.price_text == "0"
        assert decoded_assessment.normalized_listing.price_amount == Decimal("0")


# ---------------------------------------------------------------------------
# PROCUREMENT_ACTIONABILITY — the bounded neutral B1 notice
# ---------------------------------------------------------------------------


class TestZeroPriceQuoteSummaryNotice:
    def test_zero_public_listing_row_carries_the_verification_notice(self) -> None:
        obs = _observation(source_url=ZERO_HOST_URL, price_text="0")
        assessment = _accepted_assessment(obs, Decimal("0"), "USD", NormalizedCondition.NEW)
        result = aggregate_listing_prices(_request(), (assessment,))
        projection = CompactQuoteProjection(rows=project_public_rows(result))
        presentation, _ = _presentation_for(result, projection)

        assert len(presentation.rows) == 1
        row = presentation.rows[0]
        assert row.note == _expected_zero_note("$0 USD")
        # Published value and currency preserved exactly.
        assert row.price == "$0 USD"
        assert row.usd_equivalent == "$0 USD"
        # Source/provenance/market labels intact.
        assert row.market_use == "Included in public market"
        assert row.condition == "New"
        assert row.match_evidence == "Exact MPN"
        assert row.source_display == "zero-offer.example"

    def test_zero_point_zero_published_value_is_preserved_in_the_notice(self) -> None:
        obs = _observation(source_url=ZERO_HOST_URL, price_text="0.00")
        assessment = _accepted_assessment(
            obs, Decimal("0.00"), "USD", NormalizedCondition.NEW
        )
        result = aggregate_listing_prices(_request(), (assessment,))
        projection = CompactQuoteProjection(rows=project_public_rows(result))
        presentation, _ = _presentation_for(result, projection)

        row = presentation.rows[0]
        assert row.price == "$0.00 USD"
        assert row.note == _expected_zero_note("$0.00 USD")

    def test_zero_vendor_row_carries_the_notice_and_preserves_existing_note(self) -> None:
        obs = _observation(source_url=ZERO_HOST_URL, price_text="0")
        assessment = _accepted_assessment(obs, Decimal("0"), "USD", NormalizedCondition.NEW)
        result = aggregate_listing_prices(_request(), (assessment,))
        vendor_row = CompactQuoteRow(
            source="Ingram",
            source_type="VENDOR_API",
            price_original="$0.00 USD",
            price_amount=Decimal("0.00"),
            price_currency="USD",
            usd_equivalent="$0.00 USD",
            usd_equivalent_amount=Decimal("0.00"),
            inventory="In Stock",
            brand_new="Yes",
            note="NO_RETURNS",
        )
        projection = CompactQuoteProjection(rows=project_public_rows(result) + (vendor_row,))
        presentation, _ = _presentation_for(result, projection)

        vendor_display = [r for r in presentation.rows if r.source_type == "VENDOR_API"][0]
        # The existing bounded note is preserved verbatim; the zero note is
        # appended, never replaced.
        assert vendor_display.note == (
            "NO_RETURNS; " + _expected_zero_note("$0.00 USD")
        )
        assert vendor_display.price == "$0.00 USD"
        assert vendor_display.market_use == "Quote only \u2014 Vendor supplemental"

    def test_zero_condition_unknown_quote_only_row_stays_not_stated(self) -> None:
        obs = _observation(source_url=ZERO_HOST_URL, price_text="0", condition_text=None)
        assessment = _accepted_assessment(
            obs, Decimal("0"), "USD", NormalizedCondition.UNKNOWN
        )
        result = aggregate_listing_prices(_request(), (assessment,))
        assert result.buckets == ()
        quote_only = project_condition_unknown_quote_rows(result)
        assert len(quote_only) == 1
        assert quote_only[0].source_type == "PUBLIC_QUOTE_ONLY"
        # The frozen quote-only note passes through unchanged.
        assert quote_only[0].note == "Quote only \u2014 condition not stated"
        projection = CompactQuoteProjection(rows=quote_only)
        presentation, _ = _presentation_for(result, projection)

        row = presentation.rows[0]
        assert row.condition == "Not stated"
        assert row.market_use == "Quote only \u2014 condition not stated"
        assert row.note == (
            "Quote only \u2014 condition not stated; "
            + _expected_zero_note("$0 USD")
        )
        assert row.price == "$0 USD"

    def test_zero_human_confirmed_row_keeps_provenance_and_carries_notice(self) -> None:
        # The persisted assessment is human-review eligible (semantic shape)
        # with a source-published zero price. No explicit MPN field — only
        # the retailer SKU — on the underlying observation.
        hc_obs = ListingObservation(
            source_url=HC_HOST_URL,
            extraction_method=ExtractionMethod.JSON_LD,
            product_title="B1 Zero Price Test Product",
            manufacturer_part_number_text=None,
            sku_text="B1-ZERO-SKU",
            brand_text=None,
            price_text="0",
            currency_text="USD",
            availability_text=None,
            condition_text="New",
            seller_text=None,
            offer_url_text=None,
            raw_reference=None,
        )
        hc_assessment = _human_eligible_rejected_assessment(
            hc_obs, Decimal("0"), "USD", NormalizedCondition.NEW
        )
        result = aggregate_listing_prices(_request(), (hc_assessment,))
        assert result.exclusions[0].reason is PriceAggregationExclusionReason.IDENTITY_NOT_ACCEPTED

        human_row = CompactQuoteRow(
            source="confirmed-offer.example",
            source_type="HUMAN_CONFIRMED",
            price_original="$0.00 USD",
            price_amount=Decimal("0.00"),
            price_currency="USD",
            usd_equivalent="$0.00 USD",
            usd_equivalent_amount=Decimal("0.00"),
            inventory="Unknown",
            brand_new="Yes",
            note="Human Confirmed",
        )
        projection = CompactQuoteProjection(rows=(human_row,))
        presentation, _ = _presentation_for(
            result, projection, confirmed=frozenset({0})
        )

        row = presentation.rows[0]
        assert row.match_evidence == "AI-assisted \u2014 Human confirmed"
        assert row.condition == "New"
        # The "Human Confirmed" provenance note is preserved; the zero
        # verification note is appended.
        assert row.note == "Human Confirmed; " + _expected_zero_note("$0.00 USD")
        assert row.price == "$0.00 USD"

    def test_positive_price_rows_do_not_receive_the_zero_notice(self) -> None:
        a1 = _accepted_assessment(
            _observation(source_url=POS_HOST_URL, price_text="1500.00"),
            Decimal("1500.00"),
            "USD",
            NormalizedCondition.NEW,
            availability=NormalizedAvailability.IN_STOCK,
        )
        a2 = _accepted_assessment(
            _observation(
                source_url="https://second-offer.example/product",
                price_text="1600.00",
                currency_text="EUR",
            ),
            Decimal("1600.00"),
            "EUR",
            NormalizedCondition.NEW,
        )
        result = aggregate_listing_prices(_request(), (a1, a2))
        projection = CompactQuoteProjection(rows=project_public_rows(result))
        presentation, _ = _presentation_for(result, projection)

        for row in presentation.rows:
            assert row.note is None

    def test_nonzero_sub_cent_price_does_not_receive_the_zero_notice(self) -> None:
        a = _accepted_assessment(
            _observation(source_url=POS_HOST_URL, price_text="0.01"),
            Decimal("0.01"),
            "USD",
            NormalizedCondition.NEW,
        )
        result = aggregate_listing_prices(_request(), (a,))
        projection = CompactQuoteProjection(rows=project_public_rows(result))
        presentation, _ = _presentation_for(result, projection)
        assert presentation.rows[0].note is None
        assert presentation.rows[0].price == "$0.01 USD"

    def test_missing_price_is_never_a_zero_price_row(self) -> None:
        # An accepted listing with no parseable price is excluded from 4A
        # and can produce no compact row — so no zero notice can appear for
        # a missing or ambiguous price.
        obs = _observation(source_url=ZERO_HOST_URL, price_text="undefined", currency_text=None)
        norm = normalize_listing_observation(obs)
        assert norm.price_amount is None
        # An accepted listing whose price did not normalize carries no
        # numeric price: 4A excludes it, no compact row exists, and no
        # zero notice can appear for a missing or ambiguous price.
        assessment = ListingIdentityAssessment(
            normalized_listing=NormalizedListingObservation(
                observation=obs,
                price_amount=None,
                currency_code=None,
                availability=NormalizedAvailability.UNKNOWN,
                condition=NormalizedCondition.UNKNOWN,
                seller_name=None,
                normalization_issues=norm.normalization_issues,
            ),
            requested_part_number=MPN,
            candidate_part_number_raw=MPN,
            candidate_part_number_compared=MPN,
            candidate_evidence_source=EvidenceSource.EXPLICIT_MPN_FIELD,
            match_type=IdentityMatchType.EXACT,
            decision=EvidenceDecision.ACCEPTED,
            rejection_reason=None,
        )
        result = aggregate_listing_prices(_request(), (assessment,))
        assert result.buckets == ()
        assert result.exclusions[0].reason is PriceAggregationExclusionReason.NO_NUMERIC_PRICE
        rows = project_public_rows(result)
        assert rows == ()

    def test_summary_metrics_and_frozen_rows_unchanged_for_zero_rows(self) -> None:
        a_zero = _accepted_assessment(
            _observation(source_url=ZERO_HOST_URL, price_text="0"),
            Decimal("0"),
            "USD",
            NormalizedCondition.NEW,
            availability=NormalizedAvailability.IN_STOCK,
        )
        a_pos = _accepted_assessment(
            _observation(source_url=POS_HOST_URL, price_text="1500.00"),
            Decimal("1500.00"),
            "USD",
            NormalizedCondition.NEW,
            availability=NormalizedAvailability.IN_STOCK,
        )
        result = aggregate_listing_prices(_request(), (a_zero, a_pos))
        projection = CompactQuoteProjection(rows=project_public_rows(result))
        presentation, result_after = _presentation_for(result, projection)

        # Frozen quote metrics: the zero still moves the span low and the
        # lowest-in-stock metric (B1 does not alter these).
        assert presentation.quotes_found == 2
        assert presentation.in_stock_count == 2
        assert presentation.lowest_in_stock_price == "$0.00 USD"
        assert presentation.lowest_in_stock_source == "zero-offer.example"
        assert presentation.quote_span_low == "$0.00 USD"
        assert presentation.quote_span_high == "$1,500.00 USD"
        # Frozen 4A market summary: unchanged statistics over the bucket.
        assert presentation.public_market_count == 2
        assert presentation.public_market_low == "$0.00 USD"
        assert presentation.public_market_high == "$1,500.00 USD"
        assert presentation.public_market_median is None
        assert "fewer than 3" in presentation.public_market_median_note
        # The underlying frozen result and projection rows are unmutated.
        assert result_after is result
        assert result.buckets[0].low == Decimal("0")
        assert result.buckets[0].median == Decimal("750.00")
        zero_row = [r for r in projection.rows if r.price_amount == 0][0]
        assert zero_row.note is None
        positive_row = [r for r in projection.rows if r.price_amount != 0][0]
        assert positive_row.note is None

        display_zero = [r for r in presentation.rows if r.source_display == "zero-offer.example"][0]
        display_pos = [r for r in presentation.rows if r.source_display == "positive-offer.example"][0]
        assert display_zero.note == _expected_zero_note("$0 USD")
        assert display_pos.note is None


# ---------------------------------------------------------------------------
# End-to-end: the rendered Quote & Market Summary page
# ---------------------------------------------------------------------------


class _QuoteSummaryRowParser(HTMLParser):
    """Cell texts of the rendered Quote & Market Summary compact table."""

    def __init__(self) -> None:
        super().__init__()
        self.in_table = False
        self.in_row = False
        self.in_cell = False
        self._cell_text = ""
        self._current_row: list[str] = []
        self.rows: list[list[str]] = []

    def handle_starttag(self, tag, attrs) -> None:
        if tag == "table":
            self.in_table = True
        elif tag == "tr" and self.in_table:
            self.in_row = True
            self._current_row = []
        elif tag in ("td", "th") and self.in_row:
            self.in_cell = True
            self._cell_text = ""

    def handle_endtag(self, tag) -> None:
        if tag == "table":
            self.in_table = False
            self.in_row = False
        elif tag == "tr" and self.in_row:
            self.in_row = False
            self.rows.append(self._current_row)
        elif tag in ("td", "th") and self.in_cell:
            self.in_cell = False
            self._current_row.append(" ".join(self._cell_text.split()))

    def handle_data(self, data) -> None:
        if self.in_cell:
            self._cell_text += data


def _quote_summary_table_rows(html: str) -> list[list[str]]:
    start = html.index("<h2>Quote & Market Summary</h2>")
    end = html.index("<h2>Price intelligence</h2>", start)
    section = html[start:end]
    assert '<table class="spec-table">' in section
    parser = _QuoteSummaryRowParser()
    parser.feed(section)
    assert parser.rows, "compact quote table rows not found"
    return parser.rows


@pytest.mark.django_db
class TestZeroPriceNoticeEndToEnd:
    def test_zero_price_row_renders_the_notice_in_quote_and_market_summary(self) -> None:
        from product_intelligence.runs.models import (
            PriceIntelligenceSnapshot,
            ResearchRun,
        )

        run = ResearchRun.objects.create_from_request(_request())
        obs = _observation(source_url=ZERO_HOST_URL, price_text="0")
        assessment = _accepted_assessment(obs, Decimal("0"), "USD", NormalizedCondition.NEW)
        result = aggregate_listing_prices(run.to_research_request(), (assessment,))
        PriceIntelligenceSnapshot.objects.create(
            run=run,
            schema_version=1,
            payload=encode_price_aggregation_result(result),
        )

        client = Client()
        response = client.get(
            reverse("research-detail", kwargs={"run_id": run.id})
        )
        assert response.status_code == 200
        html = response.content.decode()

        assert "<h2>Quote & Market Summary</h2>" in html

        # The bounded neutral notice is visible on the zero-price row.
        assert _expected_zero_note("$0 USD") in html

        rows = _quote_summary_table_rows(html)
        body = [r for r in rows if r and r[0] != "Source"]
        assert len(body) == 1
        cells = " | ".join(body[0])
        # Source/provenance/price columns intact, exact published value kept.
        assert "zero-offer.example" in cells
        assert "$0 USD" in cells
        assert "New" in cells
        assert "Exact MPN" in cells
        # Market use label intact; the notice is appended under it.
        assert "Included in public market" in cells
        assert "Verify price and purchasing availability with the supplier." in cells
        # No availability claim was added by the notice.
        assert "In Stock" not in cells

        # Frozen 4A market summary unchanged: the zero is still the
        # observed span (authority untouched; the notice identifies the row).
        assert "<strong>1</strong>" in html
        assert "comparable NEW listing" in html
        assert "$0.00 USD \u2014 $0.00 USD" in html
        assert "Not shown \u2014 fewer than 3 comparable NEW listings." in html

        # The stored snapshot is byte-for-byte the pre-render result.
        snapshot = PriceIntelligenceSnapshot.objects.get(run=run)
        decoded = decode_price_aggregation_result(snapshot.payload, schema_version=1)
        assert decoded == result
        assert decoded.buckets[0].low == Decimal("0")

    def test_positive_price_row_renders_without_the_notice(self) -> None:
        from product_intelligence.runs.models import (
            PriceIntelligenceSnapshot,
            ResearchRun,
        )

        run = ResearchRun.objects.create_from_request(_request())
        obs = _observation(source_url=POS_HOST_URL, price_text="1500.00")
        assessment = _accepted_assessment(
            obs, Decimal("1500.00"), "USD", NormalizedCondition.NEW
        )
        result = aggregate_listing_prices(run.to_research_request(), (assessment,))
        PriceIntelligenceSnapshot.objects.create(
            run=run,
            schema_version=1,
            payload=encode_price_aggregation_result(result),
        )

        client = Client()
        response = client.get(
            reverse("research-detail", kwargs={"run_id": run.id})
        )
        assert response.status_code == 200
        html = response.content.decode()
        assert "<h2>Quote & Market Summary</h2>" in html
        rows = _quote_summary_table_rows(html)
        body = [r for r in rows if r and r[0] != "Source"]
        assert len(body) == 1
        cells = " | ".join(body[0])
        assert "$1,500.00 USD" in cells
        assert "Verify price and purchasing availability with the supplier." not in cells
        assert "Source-published price:" not in cells
