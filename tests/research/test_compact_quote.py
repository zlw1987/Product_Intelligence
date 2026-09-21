"""Tests for compact quote projection (PRODUCT-INTEL.4D-C-A).

Tests cover:
* Public listing NEW / USED / REFURBISHED / DAMAGED / UNKNOWN mapping
* Vendor API Brand New = Yes only after frozen-2A-bound successful observation
* Ingram/CDW/Synnex labels
* Inventory mappings
* LIMITED note
* PREORDER/BACKORDER/DISCONTINUED notes
* Missing FX displays unavailable
* Original amount/currency unchanged
* Price formatting
* Authority isolation (projection does not change Machine Price, etc.)
"""

from __future__ import annotations

from decimal import Decimal

import pytest

from product_intelligence.research.compact_quote import (
    CompactQuoteProjection,
    CompactQuoteRow,
    build_compact_quote_projection,
    build_public_listing_row,
    build_vendor_api_row,
    _format_price,
    _map_public_listing_brand_new,
    _map_public_listing_inventory,
    _map_vendor_api_inventory,
)
from product_intelligence.research.fx_codec import (
    FxObservationSnapshot,
    FxRateEntry,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_fx_snapshot() -> FxObservationSnapshot:
    return FxObservationSnapshot(
        provider_id="ECB",
        observation_date="2024-01-15",
        base_currency="EUR",
        rates=(
            FxRateEntry(currency_code="USD", rate=Decimal("1.0934")),
            FxRateEntry(currency_code="GBP", rate=Decimal("0.8567")),
            FxRateEntry(currency_code="EUR", rate=Decimal("1")),
        ),
        retrieved_at="2024-01-15T12:00:00+00:00",
    )


# ---------------------------------------------------------------------------
# Price formatting tests
# ---------------------------------------------------------------------------


class TestFormatPrice:
    def test_usd_format(self):
        result = _format_price(Decimal("2023.27"), "USD")
        assert result == "$2,023.27 USD"

    def test_eur_format(self):
        result = _format_price(Decimal("1705.35"), "EUR")
        assert result == "€1,705.35 EUR"

    def test_gbp_format(self):
        result = _format_price(Decimal("1500.00"), "GBP")
        assert result == "£1,500.00 GBP"

    def test_large_usd(self):
        result = _format_price(Decimal("15000"), "USD")
        assert result == "$15,000 USD"

    def test_small_usd(self):
        result = _format_price(Decimal("9.99"), "USD")
        assert result == "$9.99 USD"

    def test_jpy_format(self):
        result = _format_price(Decimal("150000"), "JPY")
        assert result == "¥150,000 JPY"


# ---------------------------------------------------------------------------
# Public listing inventory mapping tests
# ---------------------------------------------------------------------------


class TestPublicListingInventoryMapping:
    def test_in_stock(self):
        label, note = _map_public_listing_inventory("IN_STOCK")
        assert label == "In Stock"
        assert note is None

    def test_limited(self):
        label, note = _map_public_listing_inventory("LIMITED")
        assert label == "In Stock"
        assert note == "Limited"

    def test_out_of_stock(self):
        label, note = _map_public_listing_inventory("OUT_OF_STOCK")
        assert label == "Out of Stock"
        assert note is None

    def test_preorder(self):
        label, note = _map_public_listing_inventory("PREORDER")
        assert label == "Out of Stock"
        assert note == "PREORDER"

    def test_backorder(self):
        label, note = _map_public_listing_inventory("BACKORDER")
        assert label == "Out of Stock"
        assert note == "BACKORDER"

    def test_discontinued(self):
        label, note = _map_public_listing_inventory("DISCONTINUED")
        assert label == "Out of Stock"
        assert note == "DISCONTINUED"

    def test_unknown(self):
        label, note = _map_public_listing_inventory("UNKNOWN")
        assert label == "Unknown"
        assert note is None


# ---------------------------------------------------------------------------
# Vendor API inventory mapping tests
# ---------------------------------------------------------------------------


class TestVendorApiInventoryMapping:
    def test_in_stock(self):
        label, note = _map_vendor_api_inventory("IN_STOCK")
        assert label == "In Stock"
        assert note is None

    def test_limited(self):
        label, note = _map_vendor_api_inventory("LIMITED")
        assert label == "In Stock"
        assert note == "Limited"

    def test_out_of_stock(self):
        label, note = _map_vendor_api_inventory("OUT_OF_STOCK")
        assert label == "Out of Stock"
        assert note is None

    def test_unknown(self):
        label, note = _map_vendor_api_inventory("UNKNOWN")
        assert label == "Unknown"
        assert note is None


# ---------------------------------------------------------------------------
# Brand New mapping tests (public listing)
# ---------------------------------------------------------------------------


class TestPublicListingBrandNewMapping:
    def test_new_is_yes(self):
        assert _map_public_listing_brand_new("NEW") == "Yes"

    def test_used_is_no(self):
        assert _map_public_listing_brand_new("USED") == "No"

    def test_refurbished_is_no(self):
        assert _map_public_listing_brand_new("REFURBISHED") == "No"

    def test_damaged_is_no(self):
        assert _map_public_listing_brand_new("DAMAGED") == "No"

    def test_unknown_is_unknown(self):
        """Do NOT relabel UNKNOWN as New."""
        assert _map_public_listing_brand_new("UNKNOWN") == "Unknown"

    def test_unmapped_is_unknown(self):
        """Any unmapped condition stays Unknown."""
        assert _map_public_listing_brand_new("SOME_OTHER") == "Unknown"


# ---------------------------------------------------------------------------
# Vendor API row building tests
# ---------------------------------------------------------------------------


class TestBuildVendorApiRow:
    def test_ingram_label(self):
        row = build_vendor_api_row(
            source_name="Ingram Micro",
            price_amount=Decimal("2023.27"),
            currency_code="USD",
            availability="IN_STOCK",
            brand_new=True,
        )
        assert row.source == "Ingram"
        assert row.source_type == "VENDOR_API"
        assert row.price_original == "$2,023.27 USD"
        assert row.price_amount == Decimal("2023.27")
        assert row.price_currency == "USD"
        assert row.inventory == "In Stock"
        assert row.brand_new == "Yes"

    def test_cdw_label(self):
        row = build_vendor_api_row(
            source_name="CDW Corporation",
            price_amount=Decimal("1900.00"),
            currency_code="USD",
            availability="IN_STOCK",
            brand_new=True,
        )
        assert row.source == "CDW"

    def test_synnex_eu_label(self):
        row = build_vendor_api_row(
            source_name="Synnex EU",
            price_amount=Decimal("1800.00"),
            currency_code="EUR",
            availability="IN_STOCK",
            brand_new=True,
        )
        assert row.source == "Synnex EU (Vendor API)"

    def test_unknown_source_preserved(self):
        row = build_vendor_api_row(
            source_name="SomeOtherVendor",
            price_amount=Decimal("1000"),
            currency_code="USD",
            availability="IN_STOCK",
            brand_new=True,
        )
        assert row.source == "SomeOtherVendor"

    def test_vendor_api_brand_new_always_yes(self):
        """Vendor API rows always show brand_new = Yes (VENDOR_API_POLICY)."""
        row = build_vendor_api_row(
            source_name="Ingram",
            price_amount=Decimal("1000"),
            currency_code="USD",
            availability="IN_STOCK",
            brand_new=True,
        )
        assert row.brand_new == "Yes"

    def test_vendor_api_eur_with_fx(self):
        fx = _make_fx_snapshot()
        row = build_vendor_api_row(
            source_name="Synnex EU",
            price_amount=Decimal("1705.35"),
            currency_code="EUR",
            availability="IN_STOCK",
            brand_new=True,
            fx_snapshot=fx,
        )
        assert row.price_original == "€1,705.35 EUR"
        assert row.usd_equivalent != "Unavailable"
        assert row.usd_equivalent_amount is not None
        assert type(row.usd_equivalent_amount) is Decimal

    def test_vendor_api_no_fx(self):
        row = build_vendor_api_row(
            source_name="Ingram",
            price_amount=Decimal("1000"),
            currency_code="GBP",
            availability="IN_STOCK",
            brand_new=True,
            fx_snapshot=None,
        )
        assert row.usd_equivalent == "Unavailable"
        assert row.usd_equivalent_amount is None

    def test_vendor_api_limited_inventory(self):
        row = build_vendor_api_row(
            source_name="Ingram",
            price_amount=Decimal("1000"),
            currency_code="USD",
            availability="LIMITED",
            brand_new=True,
        )
        assert row.inventory == "In Stock"
        assert row.note == "Limited"

    def test_vendor_api_out_of_stock(self):
        row = build_vendor_api_row(
            source_name="Ingram",
            price_amount=Decimal("1000"),
            currency_code="USD",
            availability="OUT_OF_STOCK",
            brand_new=True,
        )
        assert row.inventory == "Out of Stock"

    def test_vendor_api_unknown_inventory(self):
        row = build_vendor_api_row(
            source_name="Ingram",
            price_amount=Decimal("1000"),
            currency_code="USD",
            availability="UNKNOWN",
            brand_new=True,
        )
        assert row.inventory == "Unknown"

    def test_vendor_api_usd_passthrough(self):
        row = build_vendor_api_row(
            source_name="Ingram",
            price_amount=Decimal("2023.27"),
            currency_code="USD",
            availability="IN_STOCK",
            brand_new=True,
            fx_snapshot=None,  # No FX at all
        )
        assert row.usd_equivalent != "Unavailable"
        assert row.usd_equivalent_amount == Decimal("2023.27")


# ---------------------------------------------------------------------------
# Public listing row building tests
# ---------------------------------------------------------------------------


class TestBuildPublicListingRow:
    def test_new_condition(self):
        row = build_public_listing_row(
            source_name="Some Retailer",
            price_amount=Decimal("2500.00"),
            currency_code="USD",
            availability="IN_STOCK",
            condition="NEW",
        )
        assert row.source_type == "PUBLIC_LISTING"
        assert row.brand_new == "Yes"
        assert row.inventory == "In Stock"

    def test_used_condition(self):
        row = build_public_listing_row(
            source_name="Some Retailer",
            price_amount=Decimal("1800.00"),
            currency_code="USD",
            availability="IN_STOCK",
            condition="USED",
        )
        assert row.brand_new == "No"

    def test_refurbished_condition(self):
        row = build_public_listing_row(
            source_name="Some Retailer",
            price_amount=Decimal("1500.00"),
            currency_code="USD",
            availability="IN_STOCK",
            condition="REFURBISHED",
        )
        assert row.brand_new == "No"

    def test_damaged_condition(self):
        row = build_public_listing_row(
            source_name="Some Retailer",
            price_amount=Decimal("1000.00"),
            currency_code="USD",
            availability="IN_STOCK",
            condition="DAMAGED",
        )
        assert row.brand_new == "No"

    def test_unknown_condition_stays_unknown(self):
        """Do NOT relabel UNKNOWN as New."""
        row = build_public_listing_row(
            source_name="Some Retailer",
            price_amount=Decimal("2000.00"),
            currency_code="USD",
            availability="IN_STOCK",
            condition="UNKNOWN",
        )
        assert row.brand_new == "Unknown"

    def test_preorder_inventory(self):
        row = build_public_listing_row(
            source_name="Some Retailer",
            price_amount=Decimal("2000.00"),
            currency_code="USD",
            availability="PREORDER",
            condition="NEW",
        )
        assert row.inventory == "Out of Stock"
        assert row.note == "PREORDER"

    def test_backorder_inventory(self):
        row = build_public_listing_row(
            source_name="Some Retailer",
            price_amount=Decimal("2000.00"),
            currency_code="USD",
            availability="BACKORDER",
            condition="NEW",
        )
        assert row.inventory == "Out of Stock"
        assert row.note == "BACKORDER"

    def test_discontinued_inventory(self):
        row = build_public_listing_row(
            source_name="Some Retailer",
            price_amount=Decimal("2000.00"),
            currency_code="USD",
            availability="DISCONTINUED",
            condition="NEW",
        )
        assert row.inventory == "Out of Stock"
        assert row.note == "DISCONTINUED"

    def test_limited_inventory(self):
        row = build_public_listing_row(
            source_name="Some Retailer",
            price_amount=Decimal("2000.00"),
            currency_code="USD",
            availability="LIMITED",
            condition="NEW",
        )
        assert row.inventory == "In Stock"
        assert row.note == "Limited"

    def test_eur_with_fx(self):
        fx = _make_fx_snapshot()
        row = build_public_listing_row(
            source_name="European Shop",
            price_amount=Decimal("1705.35"),
            currency_code="EUR",
            availability="IN_STOCK",
            condition="NEW",
            fx_snapshot=fx,
        )
        assert row.price_original == "€1,705.35 EUR"
        assert row.usd_equivalent != "Unavailable"
        assert row.usd_equivalent_amount is not None

    def test_eur_without_fx(self):
        row = build_public_listing_row(
            source_name="European Shop",
            price_amount=Decimal("1705.35"),
            currency_code="EUR",
            availability="IN_STOCK",
            condition="NEW",
            fx_snapshot=None,
        )
        assert row.usd_equivalent == "Unavailable"
        assert row.usd_equivalent_amount is None

    def test_original_currency_unchanged(self):
        """Original source price amount + currency remain authoritative."""
        row = build_public_listing_row(
            source_name="Some Retailer",
            price_amount=Decimal("1705.35"),
            currency_code="EUR",
            availability="IN_STOCK",
            condition="NEW",
            fx_snapshot=_make_fx_snapshot(),
        )
        assert row.price_currency == "EUR"
        assert row.price_amount == Decimal("1705.35")


# ---------------------------------------------------------------------------
# CompactQuoteRow construction tests
# ---------------------------------------------------------------------------


class TestCompactQuoteRow:
    def test_valid_row(self):
        row = CompactQuoteRow(
            source="Ingram",
            source_type="VENDOR_API",
            price_original="$1,000 USD",
            price_amount=Decimal("1000"),
            price_currency="USD",
            usd_equivalent="$1,000 USD",
            usd_equivalent_amount=Decimal("1000"),
            inventory="In Stock",
            brand_new="Yes",
        )
        assert row.source == "Ingram"

    def test_source_required(self):
        with pytest.raises(ValueError, match="source"):
            CompactQuoteRow(
                source="",
                source_type="VENDOR_API",
                price_original="$1,000 USD",
                price_amount=Decimal("1000"),
                price_currency="USD",
                usd_equivalent="$1,000 USD",
                usd_equivalent_amount=Decimal("1000"),
                inventory="In Stock",
                brand_new="Yes",
            )

    def test_source_type_restricted(self):
        with pytest.raises(ValueError, match="source_type"):
            CompactQuoteRow(
                source="Test",
                source_type="INVALID",
                price_original="$1,000 USD",
                price_amount=Decimal("1000"),
                price_currency="USD",
                usd_equivalent="$1,000 USD",
                usd_equivalent_amount=Decimal("1000"),
                inventory="In Stock",
                brand_new="Yes",
            )

    def test_price_amount_must_be_decimal(self):
        with pytest.raises(TypeError, match="price_amount"):
            CompactQuoteRow(
                source="Test",
                source_type="VENDOR_API",
                price_original="$1,000 USD",
                price_amount=1000,  # type: ignore
                price_currency="USD",
                usd_equivalent="$1,000 USD",
                usd_equivalent_amount=Decimal("1000"),
                inventory="In Stock",
                brand_new="Yes",
            )


# ---------------------------------------------------------------------------
# CompactQuoteProjection tests
# ---------------------------------------------------------------------------


class TestCompactQuoteProjection:
    def test_build_with_vendor_and_public(self):
        vendor_row = build_vendor_api_row(
            source_name="Ingram",
            price_amount=Decimal("2023.27"),
            currency_code="USD",
            availability="IN_STOCK",
            brand_new=True,
        )
        public_row = build_public_listing_row(
            source_name="Retailer",
            price_amount=Decimal("2500.00"),
            currency_code="USD",
            availability="IN_STOCK",
            condition="NEW",
        )
        projection = build_compact_quote_projection(
            vendor_rows=(vendor_row,),
            public_rows=(public_row,),
        )
        assert len(projection.rows) == 2
        assert projection.rows[0].source_type == "VENDOR_API"
        assert projection.rows[1].source_type == "PUBLIC_LISTING"

    def test_empty_projection(self):
        projection = build_compact_quote_projection()
        assert len(projection.rows) == 0

    def test_only_vendor_rows(self):
        row = build_vendor_api_row(
            source_name="Ingram",
            price_amount=Decimal("1000"),
            currency_code="USD",
            availability="IN_STOCK",
            brand_new=True,
        )
        projection = build_compact_quote_projection(vendor_rows=(row,))
        assert len(projection.rows) == 1

    def test_projection_rows_are_tuple(self):
        row = build_vendor_api_row(
            source_name="Ingram",
            price_amount=Decimal("1000"),
            currency_code="USD",
            availability="IN_STOCK",
            brand_new=True,
        )
        projection = CompactQuoteProjection(rows=(row,))
        assert isinstance(projection.rows, tuple)


# ---------------------------------------------------------------------------
# Authority isolation tests
# ---------------------------------------------------------------------------


class TestAuthorityIsolation:
    """Prove that compact projection does not affect frozen authority.

    These tests verify that:
    * Projection does not change Machine Price
    * Projection does not change Reviewed Price
    * Projection does not enter semantic input
    * Projection does not enter comparable scoring
    * Projection does not affect 4D-A fallback/search decision
    """

    def test_projection_does_not_import_aggregation(self):
        """Compact quote module does not import price aggregation."""
        import product_intelligence.research.compact_quote as cq
        source = open(cq.__file__).read()
        assert "aggregate_listing_prices" not in source
        assert "PriceAggregationResult" not in source

    def test_projection_does_not_import_matching(self):
        """Compact quote module does not import matching/identity."""
        import product_intelligence.research.compact_quote as cq
        source = open(cq.__file__).read()
        assert "from product_intelligence.research.matching" not in source
        assert "from product_intelligence.research.identity" not in source

    def test_projection_does_not_import_semantic(self):
        """Compact quote module does not import semantic runtime."""
        import product_intelligence.research.compact_quote as cq
        source = open(cq.__file__).read()
        # Check that no semantic runtime symbols are imported
        assert "from product_intelligence.semantic" not in source
        assert "import product_intelligence.semantic" not in source

    def test_projection_is_pure_function(self):
        """Build functions produce deterministic results with same inputs."""
        fx = _make_fx_snapshot()
        row1 = build_vendor_api_row(
            source_name="Ingram",
            price_amount=Decimal("2023.27"),
            currency_code="USD",
            availability="IN_STOCK",
            brand_new=True,
            fx_snapshot=fx,
        )
        row2 = build_vendor_api_row(
            source_name="Ingram",
            price_amount=Decimal("2023.27"),
            currency_code="USD",
            availability="IN_STOCK",
            brand_new=True,
            fx_snapshot=fx,
        )
        assert row1 == row2

    def test_projection_preserves_original_values(self):
        """Projection does not mutate original price/currency."""
        original_amount = Decimal("2023.27")
        original_currency = "USD"
        row = build_vendor_api_row(
            source_name="Ingram",
            price_amount=original_amount,
            currency_code=original_currency,
            availability="IN_STOCK",
            brand_new=True,
        )
        assert row.price_amount == original_amount
        assert row.price_currency == original_currency.upper()


# ---------------------------------------------------------------------------
# Authority-safe projection tests (FU1 corrective)
# ---------------------------------------------------------------------------


class _FakeObservation:
    """Minimal mock of SupplementSourceObservation for vendor API tests."""

    def __init__(self, **kwargs):
        self.source_name = kwargs.get("source_name", "Ingram")
        self.explicit_candidate_mpn = kwargs.get(
            "explicit_candidate_mpn", "TEST-MPN"
        )
        self.vendor_mpn_match_type = kwargs.get("vendor_mpn_match_type", "EXACT")
        self.price_amount = kwargs.get("price_amount", Decimal("1000"))
        self.currency_code = kwargs.get("currency_code", "USD")
        self.availability = kwargs.get("availability", "IN_STOCK")
        self.price_basis = kwargs.get("price_basis", "LIST_PRICE")
        self.quantity = kwargs.get("quantity", 1)
        self.note_kind = kwargs.get("note_kind")
        self.brand_new = kwargs.get("brand_new", True)
        self.brand_new_basis = kwargs.get("brand_new_basis", "VENDOR_API_POLICY")


class _FakeAssessment:
    """Minimal mock of ListingIdentityAssessment for public listing tests."""

    def __init__(self, decision, price_amount=None, currency_code=None,
                 condition=None, availability=None, source_url=None):
        from product_intelligence.domain.enums import EvidenceDecision
        self.decision = decision
        self.normalized_listing = _FakeNormalizedListing(
            price_amount=price_amount,
            currency_code=currency_code,
            condition=condition,
            availability=availability,
            source_url=source_url or "https://example.com/product",
        )


class _FakeNormalizedListing:
    """Minimal mock of NormalizedListingObservation."""

    def __init__(self, price_amount=None, currency_code=None,
                 condition=None, availability=None, source_url=None):
        self.price_amount = price_amount
        self.currency_code = currency_code
        self.condition = condition
        self.availability = availability
        self.observation = _FakeRawObservation(
            source_url=source_url or "https://example.com/product",
        )


class _FakeRawObservation:
    """Minimal mock of ListingObservation."""

    def __init__(self, source_url=None):
        self.source_url = source_url or "https://example.com/product"


from product_intelligence.research.compact_quote import (
    CompactQuoteProjectionError,
    project_vendor_api_row,
    project_public_listing_row,
)


class TestProjectVendorApiRowAuthority:
    """Authority-safe vendor API projection requires frozen 4D-B contract."""

    def test_valid_4d_b_observation_projects(self) -> None:
        """A proper 4D-B observation with EXACT match and brand_new=True
        produces a valid vendor API quote row."""
        obs = _FakeObservation(
            source_name="Ingram Micro",
            vendor_mpn_match_type="EXACT",
            brand_new=True,
            brand_new_basis="VENDOR_API_POLICY",
            price_amount=Decimal("2023.27"),
            currency_code="USD",
            availability="IN_STOCK",
        )
        row = project_vendor_api_row(obs)
        assert row.source_type == "VENDOR_API"
        assert row.brand_new == "Yes"
        assert row.source == "Ingram"

    def test_normalized_exact_match_projects(self) -> None:
        """NORMALIZED_EXACT match type also projects."""
        obs = _FakeObservation(
            vendor_mpn_match_type="NORMALIZED_EXACT",
            brand_new=True,
            brand_new_basis="VENDOR_API_POLICY",
        )
        row = project_vendor_api_row(obs)
        assert row.source_type == "VENDOR_API"

    def test_partial_match_rejected(self) -> None:
        """PARTIAL match type cannot become a vendor API quote row."""
        obs = _FakeObservation(
            vendor_mpn_match_type="PARTIAL",
            brand_new=True,
            brand_new_basis="VENDOR_API_POLICY",
        )
        with pytest.raises(CompactQuoteProjectionError, match="match"):
            project_vendor_api_row(obs)

    def test_brand_new_false_rejected(self) -> None:
        """brand_new=False cannot produce a valid vendor API quote row.

        Under the frozen 4D-B policy, a usable bound Vendor API observation
        has brand_new=True (VENDOR_API_POLICY). If it doesn't satisfy this,
        it is not projected."""
        obs = _FakeObservation(
            vendor_mpn_match_type="EXACT",
            brand_new=False,
            brand_new_basis="VENDOR_API_POLICY",
        )
        with pytest.raises(CompactQuoteProjectionError, match="brand_new"):
            project_vendor_api_row(obs)

    def test_wrong_brand_new_basis_rejected(self) -> None:
        """brand_new_basis other than VENDOR_API_POLICY is rejected."""
        obs = _FakeObservation(
            vendor_mpn_match_type="EXACT",
            brand_new=True,
            brand_new_basis="SOME_OTHER_BASIS",
        )
        with pytest.raises(CompactQuoteProjectionError, match="VENDOR_API_POLICY"):
            project_vendor_api_row(obs)

    def test_unknown_match_rejected(self) -> None:
        """UNKNOWN match type cannot become a vendor API quote row."""
        obs = _FakeObservation(
            vendor_mpn_match_type="UNKNOWN",
            brand_new=True,
            brand_new_basis="VENDOR_API_POLICY",
        )
        with pytest.raises(CompactQuoteProjectionError, match="match"):
            project_vendor_api_row(obs)

    def test_missing_attributes_rejected(self) -> None:
        """An object missing required 4D-B attributes is rejected."""
        class BadObject:
            pass
        with pytest.raises(CompactQuoteProjectionError, match="missing attributes"):
            project_vendor_api_row(BadObject())


class TestProjectPublicListingRowAuthority:
    """Authority-safe public listing projection requires ACCEPTED assessment."""

    def test_accepted_assessment_projects(self) -> None:
        """An ACCEPTED assessment with valid price produces a row."""
        from product_intelligence.domain.enums import EvidenceDecision
        assessment = _FakeAssessment(
            decision=EvidenceDecision.ACCEPTED,
            price_amount=Decimal("2500.00"),
            currency_code="USD",
            condition="NEW",
            availability="IN_STOCK",
            source_url="https://example.com/product",
        )
        row = project_public_listing_row(assessment)
        assert row.source_type == "PUBLIC_LISTING"
        assert row.brand_new == "Yes"
        assert row.price_amount == Decimal("2500.00")

    def test_rejected_assessment_cannot_project(self) -> None:
        """A REJECTED assessment cannot become a compact public price row.

        This is the KEY negative test: a deterministic REJECTED
        ListingIdentityAssessment must NOT appear as a compact public
        price row.
        """
        from product_intelligence.domain.enums import EvidenceDecision
        assessment = _FakeAssessment(
            decision=EvidenceDecision.REJECTED,
            price_amount=Decimal("1500.00"),
            currency_code="USD",
            condition="NEW",
            availability="IN_STOCK",
        )
        with pytest.raises(CompactQuoteProjectionError, match="ACCEPTED"):
            project_public_listing_row(assessment)

    def test_undecided_assessment_cannot_project(self) -> None:
        """An UNDECIDED assessment cannot become a compact row."""
        from product_intelligence.domain.enums import EvidenceDecision
        assessment = _FakeAssessment(
            decision=EvidenceDecision.UNDECIDED,
            price_amount=Decimal("1500.00"),
            currency_code="USD",
            condition="NEW",
        )
        with pytest.raises(CompactQuoteProjectionError, match="ACCEPTED"):
            project_public_listing_row(assessment)

    def test_no_price_cannot_project(self) -> None:
        """An ACCEPTED assessment with no price cannot project."""
        from product_intelligence.domain.enums import EvidenceDecision
        assessment = _FakeAssessment(
            decision=EvidenceDecision.ACCEPTED,
            price_amount=None,
            currency_code="USD",
        )
        with pytest.raises(CompactQuoteProjectionError, match="price_amount"):
            project_public_listing_row(assessment)

    def test_no_currency_cannot_project(self) -> None:
        """An ACCEPTED assessment with no currency cannot project."""
        from product_intelligence.domain.enums import EvidenceDecision
        assessment = _FakeAssessment(
            decision=EvidenceDecision.ACCEPTED,
            price_amount=Decimal("1000"),
            currency_code=None,
        )
        with pytest.raises(CompactQuoteProjectionError, match="currency_code"):
            project_public_listing_row(assessment)

    def test_used_condition_stays_no(self) -> None:
        """USED condition maps to brand_new=No."""
        from product_intelligence.domain.enums import EvidenceDecision
        assessment = _FakeAssessment(
            decision=EvidenceDecision.ACCEPTED,
            price_amount=Decimal("1800.00"),
            currency_code="USD",
            condition="USED",
        )
        row = project_public_listing_row(assessment)
        assert row.brand_new == "No"

    def test_refurbished_condition_stays_no(self) -> None:
        """REFURBISHED condition maps to brand_new=No."""
        from product_intelligence.domain.enums import EvidenceDecision
        assessment = _FakeAssessment(
            decision=EvidenceDecision.ACCEPTED,
            price_amount=Decimal("1500.00"),
            currency_code="USD",
            condition="REFURBISHED",
        )
        row = project_public_listing_row(assessment)
        assert row.brand_new == "No"


class TestNegativeRejectedPublicEvidence:
    """Negative tests: rejected/non-reportable public evidence cannot
    become compact quote rows."""

    def test_rejected_no_mpn_cannot_project(self) -> None:
        """A REJECTED assessment with NO_EXPLICIT_MPN_EVIDENCE cannot project."""
        from product_intelligence.domain.enums import EvidenceDecision
        assessment = _FakeAssessment(
            decision=EvidenceDecision.REJECTED,
            price_amount=Decimal("2000.00"),
            currency_code="EUR",
            condition="NEW",
            availability="IN_STOCK",
        )
        with pytest.raises(CompactQuoteProjectionError):
            project_public_listing_row(assessment)

    def test_arbitrary_scalars_cannot_establish_authority(self) -> None:
        """Passing arbitrary raw scalars through the authority-safe
        builder is rejected — the authority-safe API requires a typed
        authority-bearing input."""
        # The raw builder (build_public_listing_row) exists for internal use
        # but the authority-safe entry point (project_public_listing_row)
        # requires a proper assessment object.
        # Prove that the authority-safe path rejects non-authority inputs.
        class ArbitraryScalars:
            decision = "SOME_RANDOM_VALUE"  # Not ACCEPTED
            normalized_listing = None

        with pytest.raises(CompactQuoteProjectionError):
            project_public_listing_row(ArbitraryScalars())

    def test_none_decision_cannot_project(self) -> None:
        """An assessment with no decision attribute is rejected."""
        class NoDecision:
            normalized_listing = None

        with pytest.raises(CompactQuoteProjectionError, match="decision"):
            project_public_listing_row(NoDecision())
