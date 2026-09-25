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
* BLOCKER 1 (FU2): Public authority comes from actual PriceAggregationResult
  bucket membership, not independent assessment re-evaluation
* BLOCKER 2 (FU2): Vendor authority requires exact SupplementSourceObservation
  type, not duck-typed substitutes
* BLOCKER 3 (FU2): Private scalar builders cannot establish reportability
"""

from __future__ import annotations

from decimal import Decimal

import pytest

from product_intelligence.research.compact_quote import (
    _build_compact_quote_projection,
    _build_public_listing_row,
    _build_vendor_api_row,
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

    def test_preorder(self):
        label, note = _map_vendor_api_inventory("PREORDER")
        assert label == "Out of Stock"
        assert note == "PREORDER"

    def test_backorder(self):
        label, note = _map_vendor_api_inventory("BACKORDER")
        assert label == "Out of Stock"
        assert note == "BACKORDER"

    def test_discontinued(self):
        label, note = _map_vendor_api_inventory("DISCONTINUED")
        assert label == "Out of Stock"
        assert note == "DISCONTINUED"

    def test_unknown(self):
        label, note = _map_vendor_api_inventory("UNKNOWN")
        assert label == "Unknown"
        assert note is None


# ---------------------------------------------------------------------------
# Brand New mapping
# ---------------------------------------------------------------------------


class TestPublicListingBrandNewMapping:
    def test_new(self):
        assert _map_public_listing_brand_new("NEW") == "Yes"

    def test_used(self):
        assert _map_public_listing_brand_new("USED") == "No"

    def test_refurbished(self):
        assert _map_public_listing_brand_new("REFURBISHED") == "No"

    def test_damaged(self):
        assert _map_public_listing_brand_new("DAMAGED") == "No"

    def test_unknown(self):
        assert _map_public_listing_brand_new("UNKNOWN") == "Unknown"


# ---------------------------------------------------------------------------
# PRIVATE vendor API row builder tests (formatting only, no authority)
# ---------------------------------------------------------------------------


class TestBuildVendorApiRow:
    def test_ingram(self):
        row = _build_vendor_api_row(
            source_name="Ingram Micro",
            price_amount=Decimal("2023.27"),
            currency_code="USD",
            availability="IN_STOCK",
            brand_new=True,
        )
        assert row.source == "Ingram"

    def test_cdw(self):
        row = _build_vendor_api_row(
            source_name="CDW",
            price_amount=Decimal("1700.00"),
            currency_code="EUR",
            availability="IN_STOCK",
            brand_new=True,
        )
        assert row.source == "CDW"

    def test_synnex(self):
        row = _build_vendor_api_row(
            source_name="Synnex EU",
            price_amount=Decimal("1600.00"),
            currency_code="EUR",
            availability="IN_STOCK",
            brand_new=True,
        )
        assert row.source == "Synnex EU (Vendor API)"

    def test_unknown_vendor(self):
        row = _build_vendor_api_row(
            source_name="Other Vendor",
            price_amount=Decimal("1500.00"),
            currency_code="GBP",
            availability="OUT_OF_STOCK",
            brand_new=True,
        )
        assert row.source == "Other Vendor"

    def test_brand_new_true_display_yes(self):
        row = _build_vendor_api_row(
            source_name="Ingram",
            price_amount=Decimal("2000.00"),
            currency_code="USD",
            availability="IN_STOCK",
            brand_new=True,
        )
        assert row.brand_new == "Yes"
        assert row.source_type == "VENDOR_API"

    def test_brand_new_false_display_no(self):
        row = _build_vendor_api_row(
            source_name="Ingram",
            price_amount=Decimal("1800.00"),
            currency_code="USD",
            availability="IN_STOCK",
            brand_new=False,
        )
        assert row.brand_new == "No"
        assert row.source_type == "VENDOR_API"

    def test_inventory_out_of_stock(self):
        row = _build_vendor_api_row(
            source_name="CDW",
            price_amount=Decimal("1700.00"),
            currency_code="USD",
            availability="OUT_OF_STOCK",
            brand_new=True,
        )
        assert row.inventory == "Out of Stock"

    def test_inventory_limited(self):
        row = _build_vendor_api_row(
            source_name="CDW",
            price_amount=Decimal("1700.00"),
            currency_code="USD",
            availability="LIMITED",
            brand_new=True,
        )
        assert row.inventory == "In Stock"
        assert row.note == "Limited"

    def test_limited_note_combined(self):
        row = _build_vendor_api_row(
            source_name="Ingram",
            price_amount=Decimal("2100.00"),
            currency_code="USD",
            availability="LIMITED",
            brand_new=True,
            note="Volume pricing",
        )
        assert row.note == "Limited; Volume pricing"

    def test_no_fx_unavailable(self):
        row = _build_vendor_api_row(
            source_name="CDW",
            price_amount=Decimal("1700.00"),
            currency_code="EUR",
            availability="IN_STOCK",
            brand_new=True,
            fx_snapshot=None,
        )
        assert row.usd_equivalent == "Unavailable"
        assert row.usd_equivalent_amount is None

    def test_with_fx_equivalent(self):
        fx = _make_fx_snapshot()
        row = _build_vendor_api_row(
            source_name="CDW",
            price_amount=Decimal("1700.00"),
            currency_code="EUR",
            availability="IN_STOCK",
            brand_new=True,
            fx_snapshot=fx,
        )
        assert row.usd_equivalent != "Unavailable"
        assert row.usd_equivalent_amount is not None

    def test_usd_same_value(self):
        fx = _make_fx_snapshot()
        row = _build_vendor_api_row(
            source_name="CDW",
            price_amount=Decimal("2023.27"),
            currency_code="USD",
            availability="IN_STOCK",
            brand_new=True,
            fx_snapshot=fx,
        )
        assert row.price_amount == row.usd_equivalent_amount

    def test_price_original_preserved(self):
        row = _build_vendor_api_row(
            source_name="CDW",
            price_amount=Decimal("1700.00"),
            currency_code="EUR",
            availability="IN_STOCK",
            brand_new=True,
        )
        # Price original contains amount and currency
        assert "1,700" in row.price_original or "1700" in row.price_original
        assert "EUR" in row.price_original


# ---------------------------------------------------------------------------
# PRIVATE public listing row builder tests (formatting only, no authority)
# ---------------------------------------------------------------------------


class TestBuildPublicListingRow:
    def test_new_condition_brand_new_yes(self):
        row = _build_public_listing_row(
            source_name="Amazon",
            price_amount=Decimal("2500.00"),
            currency_code="USD",
            availability="IN_STOCK",
            condition="NEW",
        )
        assert row.brand_new == "Yes"
        assert row.source_type == "PUBLIC_LISTING"

    def test_used_condition_brand_new_no(self):
        row = _build_public_listing_row(
            source_name="eBay",
            price_amount=Decimal("1800.00"),
            currency_code="USD",
            availability="IN_STOCK",
            condition="USED",
        )
        assert row.brand_new == "No"

    def test_refurbished_condition_brand_new_no(self):
        row = _build_public_listing_row(
            source_name="eBay",
            price_amount=Decimal("1500.00"),
            currency_code="USD",
            availability="IN_STOCK",
            condition="REFURBISHED",
        )
        assert row.brand_new == "No"

    def test_damaged_condition_brand_new_no(self):
        row = _build_public_listing_row(
            source_name="eBay",
            price_amount=Decimal("1200.00"),
            currency_code="USD",
            availability="IN_STOCK",
            condition="DAMAGED",
        )
        assert row.brand_new == "No"

    def test_unknown_condition_brand_new_unknown(self):
        row = _build_public_listing_row(
            source_name="SomeSource",
            price_amount=Decimal("2000.00"),
            currency_code="USD",
            availability="IN_STOCK",
            condition="UNKNOWN",
        )
        assert row.brand_new == "Unknown"

    def test_inventory_in_stock(self):
        row = _build_public_listing_row(
            source_name="Amazon",
            price_amount=Decimal("2500.00"),
            currency_code="USD",
            availability="IN_STOCK",
            condition="NEW",
        )
        assert row.inventory == "In Stock"

    def test_inventory_out_of_stock(self):
        row = _build_public_listing_row(
            source_name="Amazon",
            price_amount=Decimal("2500.00"),
            currency_code="USD",
            availability="OUT_OF_STOCK",
            condition="NEW",
        )
        assert row.inventory == "Out of Stock"

    def test_inventory_limited_note(self):
        row = _build_public_listing_row(
            source_name="Amazon",
            price_amount=Decimal("2500.00"),
            currency_code="USD",
            availability="LIMITED",
            condition="NEW",
        )
        assert row.inventory == "In Stock"
        assert row.note == "Limited"

    def test_inventory_preorder_note(self):
        row = _build_public_listing_row(
            source_name="Amazon",
            price_amount=Decimal("2500.00"),
            currency_code="USD",
            availability="PREORDER",
            condition="NEW",
        )
        assert row.inventory == "Out of Stock"
        assert row.note == "PREORDER"

    def test_no_fx_unavailable(self):
        row = _build_public_listing_row(
            source_name="Amazon",
            price_amount=Decimal("2500.00"),
            currency_code="EUR",
            availability="IN_STOCK",
            condition="NEW",
            fx_snapshot=None,
        )
        assert row.usd_equivalent == "Unavailable"
        assert row.usd_equivalent_amount is None

    def test_with_fx_equivalent(self):
        fx = _make_fx_snapshot()
        row = _build_public_listing_row(
            source_name="Amazon",
            price_amount=Decimal("1700.00"),
            currency_code="EUR",
            availability="IN_STOCK",
            condition="NEW",
            fx_snapshot=fx,
        )
        assert row.usd_equivalent != "Unavailable"
        assert row.usd_equivalent_amount is not None

    def test_source_name_preserved(self):
        # _build_public_listing_row preserves source_name as-is.
        # URL extraction (hostname parsing) is done by project_public_rows,
        # not by _build_public_listing_row.
        row = _build_public_listing_row(
            source_name="www.amazon.com",
            price_amount=Decimal("2500.00"),
            currency_code="USD",
            availability="IN_STOCK",
            condition="NEW",
        )
        assert row.source == "www.amazon.com"

    def test_unknown_source_fallback(self):
        row = _build_public_listing_row(
            source_name="",
            price_amount=Decimal("2500.00"),
            currency_code="USD",
            availability="IN_STOCK",
            condition="NEW",
        )
        assert row.source == "Unknown Source"


# ---------------------------------------------------------------------------
# CompactQuoteRow unit tests
# ---------------------------------------------------------------------------


class TestCompactQuoteRow:
    def test_source_type_vendor_api(self):
        from product_intelligence.research.compact_quote import CompactQuoteRow
        row = CompactQuoteRow(
            source="Ingram",
            source_type="VENDOR_API",
            price_original="$2,023.27 USD",
            price_amount=Decimal("2023.27"),
            price_currency="USD",
            usd_equivalent="$2,023.27 USD",
            usd_equivalent_amount=Decimal("2023.27"),
            inventory="In Stock",
            brand_new="Yes",
        )
        assert row.source_type == "VENDOR_API"

    def test_source_type_public_listing(self):
        from product_intelligence.research.compact_quote import CompactQuoteRow
        row = CompactQuoteRow(
            source="Amazon",
            source_type="PUBLIC_LISTING",
            price_original="$2,500.00 USD",
            price_amount=Decimal("2500.00"),
            price_currency="USD",
            usd_equivalent="Unavailable",
            usd_equivalent_amount=None,
            inventory="In Stock",
            brand_new="Yes",
        )
        assert row.source_type == "PUBLIC_LISTING"

    def test_invalid_source_type_rejected(self):
        from product_intelligence.research.compact_quote import CompactQuoteRow
        with pytest.raises(ValueError, match="source_type"):
            CompactQuoteRow(
                source="Test",
                source_type="INVALID",
                price_original="$1.00 USD",
                price_amount=Decimal("1.00"),
                price_currency="USD",
                usd_equivalent="Unavailable",
                usd_equivalent_amount=None,
                inventory="Unknown",
                brand_new="Unknown",
            )

    def test_decimal_amount_required(self):
        from product_intelligence.research.compact_quote import CompactQuoteRow
        with pytest.raises(TypeError, match="Decimal"):
            CompactQuoteRow(
                source="Test",
                source_type="PUBLIC_LISTING",
                price_original="$1.00 USD",
                price_amount="1.00",  # Wrong type
                price_currency="USD",
                usd_equivalent="Unavailable",
                usd_equivalent_amount=None,
                inventory="Unknown",
                brand_new="Unknown",
            )

    def test_optional_note(self):
        from product_intelligence.research.compact_quote import CompactQuoteRow
        row = CompactQuoteRow(
            source="Amazon",
            source_type="PUBLIC_LISTING",
            price_original="$2,500.00 USD",
            price_amount=Decimal("2500.00"),
            price_currency="USD",
            usd_equivalent="Unavailable",
            usd_equivalent_amount=None,
            inventory="In Stock",
            brand_new="Yes",
            note="Limited",
        )
        assert row.note == "Limited"


# ---------------------------------------------------------------------------
# CompactQuoteProjection tests
# ---------------------------------------------------------------------------


class TestCompactQuoteProjection:
    def test_empty_projection(self):
        proj = _build_compact_quote_projection()
        assert len(proj.rows) == 0

    def test_vendor_rows_first(self):
        vendor_row = _build_vendor_api_row(
            source_name="Ingram",
            price_amount=Decimal("2000.00"),
            currency_code="USD",
            availability="IN_STOCK",
            brand_new=True,
        )
        public_row = _build_public_listing_row(
            source_name="Amazon",
            price_amount=Decimal("2500.00"),
            currency_code="USD",
            availability="IN_STOCK",
            condition="NEW",
        )
        proj = _build_compact_quote_projection(
            vendor_rows=(vendor_row,),
            public_rows=(public_row,),
        )
        assert proj.rows[0].source_type == "VENDOR_API"
        assert proj.rows[1].source_type == "PUBLIC_LISTING"

    def test_multiple_rows(self):
        rows = tuple(
            _build_vendor_api_row(
                source_name="Ingram",
                price_amount=Decimal("2000.00"),
                currency_code="USD",
                availability="IN_STOCK",
                brand_new=True,
            )
            for _ in range(3)
        )
        proj = _build_compact_quote_projection(vendor_rows=rows)
        assert len(proj.rows) == 3


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
        """Compact quote module does not import aggregation functions.

        BLOCKER 1 (FU2): project_public_rows reads PriceAggregationResult
        via an internal function-level import for exact type checking.
        This is permitted — it is a type-check boundary, not aggregation
        logic (no aggregate_listing_prices call, no bucket construction,
        no price arithmetic).

        This test verifies there is no import of the aggregation FUNCTIONS,
        not the type.
        """
        import product_intelligence.research.compact_quote as cq
        source = open(cq.__file__).read()
        # No call to aggregation pipeline functions
        assert "aggregate_listing_prices" not in source
        # The internal type check (isinstance(price_result, PriceAggregationResult))
        # uses a function-level import for the type — this is permitted as a
        # boundary check, not aggregation logic.

    def test_projection_does_not_import_matching(self):
        """Compact quote module does not import matching/identity at module level."""
        import product_intelligence.research.compact_quote as cq
        source = open(cq.__file__).read()
        lines = source.split("\n")
        # No module-level imports from matching/identity
        # (imports inside function bodies are OK for authority boundary checks)
        for line in lines:
            # Check for import at column 0 (module level)
            if line.startswith("from product_intelligence.research.matching") or \
               line.startswith("import product_intelligence.research.matching") or \
               line.startswith("from product_intelligence.research.identity") or \
               line.startswith("import product_intelligence.research.identity"):
                assert False, f"Module-level import of matching/identity found: {line.strip()}"

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
        row1 = _build_vendor_api_row(
            source_name="Ingram",
            price_amount=Decimal("2023.27"),
            currency_code="USD",
            availability="IN_STOCK",
            brand_new=True,
            fx_snapshot=fx,
        )
        row2 = _build_vendor_api_row(
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
        row = _build_vendor_api_row(
            source_name="Ingram",
            price_amount=original_amount,
            currency_code=original_currency,
            availability="IN_STOCK",
            brand_new=True,
        )
        assert row.price_amount == original_amount
        assert row.price_currency == original_currency.upper()


# ---------------------------------------------------------------------------
# Authority-safe vendor API projection tests
# ---------------------------------------------------------------------------

from product_intelligence.domain.enums import EvidenceDecision
from product_intelligence.research.commercial_supplement_codec import (
    SupplementSourceObservation,
)
from product_intelligence.research.matching import ListingIdentityAssessment
from product_intelligence.research.normalization import (
    NormalizedCondition,
    NormalizedAvailability,
    normalize_listing_observation,
)
from product_intelligence.research.listings import ListingObservation
from product_intelligence.research.compact_quote import (
    CompactQuoteProjectionError,
    project_vendor_api_row,
)
from product_intelligence.research.aggregation import aggregate_listing_prices, PriceAggregationExclusionReason


class TestProjectVendorApiRowAuthority:
    """Authority-safe vendor API projection requires exact SupplementSourceObservation.

    BLOCKER 2 (FU2): Exact type check — duck-typed fakes are rejected.
    """

    def test_real_supplement_source_observation_projects(self) -> None:
        """A real SupplementSourceObservation with EXACT match and brand_new=True
        produces a valid vendor API quote row."""
        obs = SupplementSourceObservation(
            source_name="Ingram Micro",
            explicit_candidate_mpn="TEST-MPN",
            vendor_mpn_match_type="EXACT",
            price_amount=Decimal("2023.27"),
            currency_code="USD",
            availability="IN_STOCK",
            price_basis="LIST_PRICE",
            quantity=1,
            note_kind=None,
            brand_new=True,
            brand_new_basis="VENDOR_API_POLICY",
        )
        row = project_vendor_api_row(obs)
        assert row.source_type == "VENDOR_API"
        assert row.brand_new == "Yes"
        assert row.source == "Ingram"

    def test_normalized_exact_match_projects(self) -> None:
        """NORMALIZED_EXACT match type also projects with real object."""
        obs = SupplementSourceObservation(
            source_name="CDW",
            explicit_candidate_mpn="TEST-MPN",
            vendor_mpn_match_type="NORMALIZED_EXACT",
            price_amount=Decimal("1900.00"),
            currency_code="USD",
            availability="IN_STOCK",
            price_basis="LIST_PRICE",
            quantity=None,
            note_kind=None,
            brand_new=True,
            brand_new_basis="VENDOR_API_POLICY",
        )
        row = project_vendor_api_row(obs)
        assert row.source_type == "VENDOR_API"

    def test_partial_match_rejected_at_construction(self) -> None:
        """PARTIAL match type cannot be constructed — __post_init__ enforces EXACT/NORMALIZED_EXACT.

        The SupplementSourceObservation dataclass validates vendor_mpn_match_type
        at construction time (not at projection time). PARTIAL cannot be instantiated.
        """
        with pytest.raises(ValueError, match="EXACT or NORMALIZED_EXACT"):
            SupplementSourceObservation(
                source_name="Synnex",
                explicit_candidate_mpn="TEST-MPN",
                vendor_mpn_match_type="PARTIAL",  # __post_init__ rejects
                price_amount=Decimal("1800.00"),
                currency_code="EUR",
                availability="IN_STOCK",
                price_basis="LIST_PRICE",
                quantity=1,
                note_kind=None,
                brand_new=True,
                brand_new_basis="VENDOR_API_POLICY",
            )

    def test_brand_new_false_rejected(self) -> None:
        """brand_new=False cannot produce a vendor API quote row."""
        obs = SupplementSourceObservation(
            source_name="Ingram",
            explicit_candidate_mpn="TEST-MPN",
            vendor_mpn_match_type="EXACT",
            price_amount=Decimal("2000.00"),
            currency_code="USD",
            availability="IN_STOCK",
            price_basis="LIST_PRICE",
            quantity=1,
            note_kind=None,
            brand_new=False,  # Wrong
            brand_new_basis="VENDOR_API_POLICY",
        )
        with pytest.raises(CompactQuoteProjectionError, match="brand_new=True"):
            project_vendor_api_row(obs)

    def test_wrong_brand_new_basis_rejected_at_construction(self) -> None:
        """brand_new_basis other than VENDOR_API_POLICY cannot be constructed.

        The SupplementSourceObservation dataclass validates brand_new_basis
        at construction time.
        """
        with pytest.raises(ValueError, match="VENDOR_API_POLICY"):
            SupplementSourceObservation(
                source_name="Ingram",
                explicit_candidate_mpn="TEST-MPN",
                vendor_mpn_match_type="EXACT",
                price_amount=Decimal("2000.00"),
                currency_code="USD",
                availability="IN_STOCK",
                price_basis="LIST_PRICE",
                quantity=1,
                note_kind=None,
                brand_new=True,
                brand_new_basis="SOME_OTHER_BASIS",  # Wrong — __post_init__ rejects
            )

    def test_unknown_match_rejected_at_construction(self) -> None:
        """UNKNOWN match type cannot be constructed — __post_init__ enforces EXACT/NORMALIZED_EXACT.

        The SupplementSourceObservation dataclass validates vendor_mpn_match_type
        at construction time. UNKNOWN cannot be instantiated.
        """
        with pytest.raises(ValueError, match="EXACT or NORMALIZED_EXACT"):
            SupplementSourceObservation(
                source_name="Ingram",
                explicit_candidate_mpn="TEST-MPN",
                vendor_mpn_match_type="UNKNOWN",  # __post_init__ rejects
                price_amount=Decimal("2000.00"),
                currency_code="USD",
                availability="IN_STOCK",
                price_basis="LIST_PRICE",
                quantity=1,
                note_kind=None,
                brand_new=True,
                brand_new_basis="VENDOR_API_POLICY",
            )

    def test_duck_typed_fake_is_rejected(self) -> None:
        """BLOCKER 2 KEY NEGATIVE: A duck-typed fake object with
        identical attributes to SupplementSourceObservation is REJECTED.

        The exact type check must reject anything that is not an actual
        SupplementSourceObservation instance, even if it has all the
        same attributes.
        """
        class _DuckTypedFake:
            """Fake with ALL the same attributes as SupplementSourceObservation."""
            source_name = "Ingram"
            explicit_candidate_mpn = "TEST-MPN"
            vendor_mpn_match_type = "EXACT"
            price_amount = Decimal("2023.27")
            currency_code = "USD"
            availability = "IN_STOCK"
            price_basis = "LIST_PRICE"
            quantity = 1
            note_kind = None
            brand_new = True
            brand_new_basis = "VENDOR_API_POLICY"

        with pytest.raises(CompactQuoteProjectionError, match="SupplementSourceObservation"):
            project_vendor_api_row(_DuckTypedFake())

    def test_missing_attributes_rejected(self) -> None:
        """An object missing required attributes is rejected."""
        class BadObject:
            pass

        with pytest.raises(CompactQuoteProjectionError, match="SupplementSourceObservation"):
            project_vendor_api_row(BadObject())


# ---------------------------------------------------------------------------
# BLOCKER 1 (FU2): Public listing authority comes from actual 4A bucket membership
# ---------------------------------------------------------------------------

from product_intelligence.research.aggregation import (
    ConfidenceLevel,
    PriceAggregationResult,
    PriceAggregateBucket,
)
from product_intelligence.research.compact_quote import project_public_rows
from product_intelligence.domain.enums import VerificationStatus


def _make_real_listing_identity_assessment(
    decision_value: str,
    price_amount: Decimal | None,
    currency_code: str | None,
    condition: str,
    source_url: str = "https://example.com/product",
) -> ListingIdentityAssessment:
    """Helper: build a real ListingIdentityAssessment for projection tests.

    Creates the minimal chain of real objects needed for projection tests.
    """
    from product_intelligence.domain import ResearchRequest
    from product_intelligence.research.listings import ExtractionMethod
    from product_intelligence.domain.enums import IdentityMatchType
    from product_intelligence.research.matching import (
        IdentityRejectionReason,
        EvidenceSource,
    )

    request = ResearchRequest(
        manufacturer_part_number="TEST-MPN",
        description="Test Product",
    )

    obs = ListingObservation(
        source_url=source_url,
        extraction_method=ExtractionMethod.JSON_LD,
        product_title="Test Product",
        manufacturer_part_number_text="TEST-MPN",
        sku_text=None,
        brand_text="TestBrand",
        price_text=str(price_amount) if price_amount else None,
        currency_text=currency_code,
        availability_text="https://schema.org/InStock",
        condition_text=condition,
        seller_text=None,
        offer_url_text=None,
        raw_reference=None,
    )

    normalized = normalize_listing_observation(obs)

    decision = EvidenceDecision(decision_value)
    if decision == EvidenceDecision.REJECTED:
        rejection = IdentityRejectionReason.MPN_MISMATCH
    elif decision == EvidenceDecision.UNDECIDED:
        rejection = IdentityRejectionReason.NO_REQUESTED_MPN
    else:
        rejection = None

    match_type = (
        IdentityMatchType.UNKNOWN
        if decision == EvidenceDecision.UNDECIDED
        else IdentityMatchType.EXACT
    )

    requested_pn = (
        ""
        if decision == EvidenceDecision.UNDECIDED
        and rejection == IdentityRejectionReason.NO_REQUESTED_MPN
        else "TEST-MPN"
    )

    return ListingIdentityAssessment(
        normalized_listing=normalized,
        requested_part_number=requested_pn,
        candidate_part_number_raw="TEST-MPN",
        candidate_part_number_compared="TEST-MPN",
        candidate_evidence_source=EvidenceSource.EXPLICIT_MPN_FIELD,
        match_type=match_type,
        decision=decision,
        rejection_reason=rejection,
    )


def _make_price_aggregation_result(
    buckets: list[PriceAggregateBucket],
) -> PriceAggregationResult:
    """Helper: build a PriceAggregationResult from a list of PriceAggregateBucket.

    The assessments tuple must contain all assessments from all buckets
    (PriceAggregationResult __post_init__ enforces this invariant).

    verification_status follows the 4A policy:
      0 buckets -> UNKNOWN
      1 bucket  -> VERIFIED
      2+ buckets -> AMBIGUOUS
    """
    from product_intelligence.domain import ResearchRequest

    # Collect all assessments from all buckets
    all_assessments: list[ListingIdentityAssessment] = []
    for bucket in buckets:
        all_assessments.extend(bucket.assessments)

    n = len(buckets)
    if n == 0:
        status = VerificationStatus.UNKNOWN
    elif n == 1:
        status = VerificationStatus.VERIFIED
    else:
        status = VerificationStatus.AMBIGUOUS

    request = ResearchRequest(
        manufacturer_part_number="TEST-MPN",
        description="Test Product",
    )
    return PriceAggregationResult(
        request=request,
        assessments=tuple(all_assessments),
        buckets=tuple(buckets) if buckets else (),
        exclusions=(),
        verification_status=status,
    )


class TestProjectPublicRowsAuthority:
    """BLOCKER 1 (FU2): Public authority comes from actual 4A bucket membership.

    The project_public_rows function reads assessments ONLY from
    price_result.buckets[*].assessments — the authority is READ from
    frozen 4A bucket membership, not independently re-derived.

    Required negatives:
    1. ACCEPTED assessment not in any bucket cannot project
    2. Assessment in price_result.exclusions cannot project
    3. UNKNOWN_CONDITION bucket member cannot project (if condition==UNKNOWN)
    4. REJECTED assessment cannot project (would not be in bucket per 4A)
    5. Duck-typed fake cannot project
    6. Assessment from a different PriceAggregationResult cannot project
    """

    def _make_bucket(
        self,
        currency: str,
        condition: str,
        assessments: tuple[ListingIdentityAssessment, ...],
    ) -> PriceAggregateBucket:
        """Build a PriceAggregateBucket for testing.

        confidence follows the 4A policy: LOW for count < 3, MEDIUM for count >= 3.
        The bucket must pass the self-audit __post_init__ which verifies
        statistics from the retained assessments.
        """
        from product_intelligence.research.normalization import NormalizedCondition
        cond = NormalizedCondition(condition)
        n = len(assessments)
        conf = (
            ConfidenceLevel.MEDIUM
            if n >= 3
            else ConfidenceLevel.LOW
        )
        prices: list[Decimal] = []
        for a in assessments:
            price = a.normalized_listing.price_amount
            if price is not None:
                prices.append(price)

        if prices:
            prices_sorted = sorted(prices)
            low = prices_sorted[0]
            high = prices_sorted[-1]
            mid_idx = len(prices_sorted) // 2
            if len(prices_sorted) % 2 == 0:
                median = (prices_sorted[mid_idx - 1] + prices_sorted[mid_idx]) / 2
            else:
                median = prices_sorted[mid_idx]
            market_low = prices_sorted[0] if n >= 3 else None
            market_high = prices_sorted[-1] if n >= 3 else None
        else:
            low = Decimal("0")
            median = Decimal("0")
            high = Decimal("0")
            market_low = None
            market_high = None

        return PriceAggregateBucket(
            currency_code=currency.upper(),
            condition=cond,
            assessments=assessments,
            count=n,
            low=low,
            median=median,
            high=high,
            market_range_low=market_low,
            market_range_high=market_high,
            confidence=conf,
        )

    # ------------------------------------------------------------------
    # Positive tests: bucket membership establishes reportability
    # ------------------------------------------------------------------

    def test_single_usd_bucket_member_projects(self) -> None:
        """A real ACCEPTED assessment in a USD bucket produces one row."""
        assessment = _make_real_listing_identity_assessment(
            decision_value="ACCEPTED",
            price_amount=Decimal("2500.00"),
            currency_code="USD",
            condition="NEW",
        )
        bucket = self._make_bucket("USD", "NEW", (assessment,))
        result = _make_price_aggregation_result([bucket])

        rows = project_public_rows(result)

        assert len(rows) == 1
        assert rows[0].source_type == "PUBLIC_LISTING"
        assert rows[0].brand_new == "Yes"
        assert rows[0].price_amount == Decimal("2500.00")

    def test_used_condition_in_bucket_maps_no(self) -> None:
        """A USED-condition bucket member maps brand_new=No."""
        assessment = _make_real_listing_identity_assessment(
            decision_value="ACCEPTED",
            price_amount=Decimal("1800.00"),
            currency_code="USD",
            condition="USED",
        )
        bucket = self._make_bucket("USD", "USED", (assessment,))
        result = _make_price_aggregation_result([bucket])

        rows = project_public_rows(result)

        assert len(rows) == 1
        assert rows[0].brand_new == "No"

    def test_multiple_bucket_members_produce_multiple_rows(self) -> None:
        """Multiple assessments in buckets produce multiple rows."""
        a1 = _make_real_listing_identity_assessment(
            decision_value="ACCEPTED",
            price_amount=Decimal("2500.00"),
            currency_code="USD",
            condition="NEW",
        )
        a2 = _make_real_listing_identity_assessment(
            decision_value="ACCEPTED",
            price_amount=Decimal("2300.00"),
            currency_code="USD",
            condition="NEW",
        )
        bucket = self._make_bucket("USD", "NEW", (a1, a2))
        result = _make_price_aggregation_result([bucket])

        rows = project_public_rows(result)

        assert len(rows) == 2

    def test_multiple_buckets_all_project(self) -> None:
        """Assessments from multiple buckets all project."""
        a1 = _make_real_listing_identity_assessment(
            decision_value="ACCEPTED",
            price_amount=Decimal("2500.00"),
            currency_code="USD",
            condition="NEW",
        )
        a2 = _make_real_listing_identity_assessment(
            decision_value="ACCEPTED",
            price_amount=Decimal("1700.00"),
            currency_code="EUR",
            condition="NEW",
        )
        bucket1 = self._make_bucket("USD", "NEW", (a1,))
        bucket2 = self._make_bucket("EUR", "NEW", (a2,))
        result = _make_price_aggregation_result([bucket1, bucket2])

        rows = project_public_rows(result)

        assert len(rows) == 2
        currencies = {r.price_currency for r in rows}
        assert currencies == {"USD", "EUR"}

    def test_empty_buckets_produce_empty_tuple(self) -> None:
        """A result with no buckets produces an empty tuple."""
        result = _make_price_aggregation_result([])
        rows = project_public_rows(result)
        assert rows == ()

    def test_zero_assessments_in_bucket_rejected(self) -> None:
        """PriceAggregateBucket requires at least one assessment.

        We cannot construct a bucket with zero assessments (the __post_init__
        rejects it). This test verifies that trying to create such a bucket
        raises ValueError.
        """
        from product_intelligence.research.aggregation import PriceAggregateBucket
        from product_intelligence.research.normalization import NormalizedCondition
        with pytest.raises(ValueError, match="at least one assessment"):
            PriceAggregateBucket(
                currency_code="USD",
                condition=NormalizedCondition("NEW"),
                assessments=(),
                count=0,
                low=Decimal("0"),
                median=Decimal("0"),
                high=Decimal("0"),
                market_range_low=None,
                market_range_high=None,
                confidence=ConfidenceLevel.LOW,
            )

    def test_fx_snapshot_applied_to_all_rows(self) -> None:
        """FX snapshot produces USD equivalents on all rows."""
        assessment = _make_real_listing_identity_assessment(
            decision_value="ACCEPTED",
            price_amount=Decimal("1700.00"),
            currency_code="EUR",
            condition="NEW",
        )
        bucket = self._make_bucket("EUR", "NEW", (assessment,))
        result = _make_price_aggregation_result([bucket])
        fx = _make_fx_snapshot()

        rows = project_public_rows(result, fx_snapshot=fx)

        assert len(rows) == 1
        assert rows[0].usd_equivalent_amount is not None
        assert rows[0].usd_equivalent != "Unavailable"

    # ------------------------------------------------------------------
    # Negative tests: authority is READ from 4A, not re-derived
    # ------------------------------------------------------------------

    def test_not_a_price_aggregation_result_raises(self) -> None:
        """BLOCKER 1 KEY NEGATIVE: Passing a non-PriceAggregationResult object
        raises CompactQuoteProjectionError — authority cannot be established
        without the actual 4A result."""

        class NotAResult:
            buckets = []

        with pytest.raises(CompactQuoteProjectionError, match="PriceAggregationResult"):
            project_public_rows(NotAResult())

    def test_none_raises(self) -> None:
        """None cannot establish authority."""
        with pytest.raises(CompactQuoteProjectionError, match="PriceAggregationResult"):
            project_public_rows(None)  # type: ignore

    def test_dict_with_buckets_raises(self) -> None:
        """BLOCKER 1: A duck-typed dict with 'buckets' key cannot project.

        A dict with a 'buckets' key is NOT a PriceAggregationResult.
        Only an actual PriceAggregationResult instance carries frozen 4A
        authority provenance.
        """
        fake_result = {"buckets": []}

        with pytest.raises(CompactQuoteProjectionError, match="PriceAggregationResult"):
            project_public_rows(fake_result)  # type: ignore

    def test_rejected_assessment_not_in_bucket_means_no_row(self) -> None:
        """BLOCKER 2 (FU3): REAL REJECTED assessment excluded by frozen 4A -> no row.

        A real ListingIdentityAssessment with decision=REJECTED, passed
        through the frozen aggregate_listing_prices() function, lands in
        result.exclusions (not result.buckets), and produces no projection row.

        This tests the authority location — the test proves 4A placed the
        assessment in exclusions, not that an empty tuple produces an empty tuple.
        """
        from product_intelligence.domain import ResearchRequest

        rejected = _make_real_listing_identity_assessment(
            decision_value="REJECTED",
            price_amount=Decimal("1500.00"),
            currency_code="USD",
            condition="NEW",
        )
        request = ResearchRequest(
            manufacturer_part_number="TEST-MPN",
            description="Test Product",
        )

        # Pass through the frozen 4A aggregate — this is the authority source
        result = aggregate_listing_prices(request, (rejected,))

        # The REJECTED assessment must be in exclusions (not buckets)
        assert result.buckets == ()  # No bucket — REJECTED never enters a bucket
        assert len(result.exclusions) == 1
        assert result.exclusions[0].assessment is rejected
        assert result.exclusions[0].reason is PriceAggregationExclusionReason.IDENTITY_NOT_ACCEPTED

        # project_public_rows reads only buckets — exclusion means no row
        rows = project_public_rows(result)
        assert rows == ()

    def test_duck_typed_assessment_in_bucket_raises(self) -> None:
        """BLOCKER 1 KEY NEGATIVE: A duck-typed assessment object placed
        inside a bucket is rejected by the exact type check.

        The bucket can technically hold any object (via PriceAggregateBucket's
        generic assessments tuple), but _project_one_public_listing_row
        performs an exact isinstance(assessment, ListingIdentityAssessment)
        check and raises if it fails.

        Note: We test this via project_public_rows, which calls the helper.
        A real PriceAggregationResult built from only real ListingIdentityAssessment
        objects will produce rows; a bucket with a fake cannot.
        """
        class _DuckTypedFakeAssessment:
            """Fake with same attributes but not a real ListingIdentityAssessment."""
            decision = EvidenceDecision.ACCEPTED
            normalized_listing = None

        # We can't actually put this in a real PriceAggregateBucket
        # (the type annotation would reject it at runtime), but we can
        # test the helper directly
        from product_intelligence.research.compact_quote import (
            _project_one_public_listing_row,
        )
        with pytest.raises(CompactQuoteProjectionError, match="ListingIdentityAssessment"):
            _project_one_public_listing_row(_DuckTypedFakeAssessment(), None)

    def test_scalar_builders_cannot_establish_reportability(self) -> None:
        """BLOCKER 2 (FU3): Public/private API proof — private helpers exist,
        old public helpers do not, and scalar/row inputs are rejected.

        Corrected wording: The production design uses PRIVATE _build_* helpers.
        This test proves the supported PUBLIC authority surface instead:

        1. Old public build_public_listing_row does not exist
        2. Old public build_vendor_api_row does not exist
        3. Supported public projection requires PriceAggregationResult
        4. Passing CompactQuoteRow or arbitrary scalars to project_public_rows
           is rejected (CompactQuoteRow is not a PriceAggregationResult)

        The mere existence of a raw CompactQuoteRow is not proof that it is
        authority-bearing. Private helper formatting coverage is verified
        separately (TestBuildPublicListingRow, TestBuildVendorApiRow).
        """
        import product_intelligence.research.compact_quote as cq
        source = open(cq.__file__).read()

        # Old public helpers do NOT exist — they were made private
        assert "def build_public_listing_row(" not in source
        assert "def build_vendor_api_row(" not in source

        # Private helpers exist (they are still imported by test modules)
        assert hasattr(cq, "_build_public_listing_row")
        assert hasattr(cq, "_build_vendor_api_row")

        # The only supported public projection entry points are:
        # project_public_rows(price_result: PriceAggregationResult, ...)
        # project_vendor_api_row(observation: SupplementSourceObservation, ...)
        # Both require specific frozen types, not arbitrary scalars.

        # Passing a CompactQuoteRow to project_public_rows raises
        # CompactQuoteProjectionError — CompactQuoteRow is not PriceAggregationResult
        row = cq._build_public_listing_row(
            source_name="Test",
            price_amount=Decimal("1000"),
            currency_code="USD",
            availability="IN_STOCK",
            condition="NEW",
        )
        with pytest.raises(CompactQuoteProjectionError, match="PriceAggregationResult"):
            project_public_rows(row)  # type: ignore — CompactQuoteRow is not PriceAggregationResult

    def test_unknown_condition_assessment_not_in_bucket_produces_no_row(self) -> None:
        """BLOCKER 2 (FU3): REAL UNKNOWN_CONDITION assessment excluded by frozen 4A.

        A real ListingIdentityAssessment with ACCEPTED identity but
        condition=UNKNOWN, passed through the frozen aggregate_listing_prices(),
        lands in result.exclusions (not result.buckets) with reason
        UNKNOWN_CONDITION, and produces no projection row.

        This tests the authority location — the test proves 4A excluded the
        assessment, not that an empty result produces an empty tuple.
        """
        from product_intelligence.domain import ResearchRequest
        from product_intelligence.research.normalization import NormalizedCondition

        # Build a real assessment with ACCEPTED identity but UNKNOWN condition
        unknown_condition_assessment = _make_real_listing_identity_assessment(
            decision_value="ACCEPTED",
            price_amount=Decimal("2000.00"),
            currency_code="USD",
            condition="UNKNOWN",  # UNKNOWN condition — excluded by 4A
        )

        request = ResearchRequest(
            manufacturer_part_number="TEST-MPN",
            description="Test Product",
        )

        # Pass through the frozen 4A aggregate
        result = aggregate_listing_prices(request, (unknown_condition_assessment,))

        # The UNKNOWN_CONDITION assessment must be in exclusions
        assert len(result.exclusions) == 1
        assert result.exclusions[0].assessment is unknown_condition_assessment
        assert result.exclusions[0].reason is PriceAggregationExclusionReason.UNKNOWN_CONDITION

        # No bucket (UNKNOWN condition is excluded from buckets per 4A)
        assert result.buckets == ()

        # project_public_rows reads only buckets — exclusion means no MARKET row
        rows = project_public_rows(result)
        assert rows == ()

        from product_intelligence.research.compact_quote import (
            project_condition_unknown_quote_rows,
        )

        quote_rows = project_condition_unknown_quote_rows(result)
        assert len(quote_rows) == 1
        quote = quote_rows[0]
        assert quote.source_type == "PUBLIC_QUOTE_ONLY"
        assert quote.price_amount == Decimal("2000.00")
        assert quote.price_currency == "USD"
        assert quote.brand_new == "Unknown"
        assert quote.note == "Quote only — condition not stated"
        assert result.buckets == ()
        assert result.verification_status is VerificationStatus.UNKNOWN

    def test_quote_only_projection_rejects_non_price_result(self) -> None:
        from product_intelligence.research.compact_quote import (
            project_condition_unknown_quote_rows,
        )
        with pytest.raises(
            CompactQuoteProjectionError,
            match="PriceAggregationResult",
        ):
            project_condition_unknown_quote_rows(object())

    def test_exclusion_not_in_bucket_produces_no_row(self) -> None:
        """BLOCKER 2 (FU3): Real excluded assessment -> no bucket membership -> no row.

        An assessment that lands in result.exclusions (not result.buckets)
        through the frozen aggregate_listing_prices() is not in any bucket
        and project_public_rows produces no row for it.

        This tests the actual authority path: an exclusion cannot be
        projected because bucket membership is the only authority source.
        """
        from product_intelligence.domain import ResearchRequest

        # Create an ACCEPTED assessment with NO numeric price — this goes
        # to exclusions for NO_NUMERIC_PRICE
        no_price_assessment = _make_real_listing_identity_assessment(
            decision_value="ACCEPTED",
            price_amount=None,  # No price — excluded by 4A
            currency_code="USD",
            condition="NEW",
        )

        request = ResearchRequest(
            manufacturer_part_number="TEST-MPN",
            description="Test Product",
        )

        result = aggregate_listing_prices(request, (no_price_assessment,))

        # The assessment is in exclusions, not in any bucket
        assert len(result.exclusions) == 1
        assert result.exclusions[0].assessment is no_price_assessment
        assert result.exclusions[0].reason is PriceAggregationExclusionReason.NO_NUMERIC_PRICE
        assert result.buckets == ()  # No bucket — excluded

        rows = project_public_rows(result)
        assert rows == ()


class TestStandaloneAssessmentRejection:
    """STANDALONE ASSESSMENT NEGATIVE — BLOCKER 2 (FU3).

    A standalone ListingIdentityAssessment is not a PriceAggregationResult.
    It cannot establish reportability because there is no authority binding
    to frozen 4A bucket membership.

    project_public_rows requires a PriceAggregationResult (the frozen 4A
    output that carries bucket/exclusion provenance). Passing a bare
    ListingIdentityAssessment must raise CompactQuoteProjectionError.
    """

    def test_standalone_listing_identity_assessment_rejected(self) -> None:
        """BLOCKER 2 (FU3): A standalone ListingIdentityAssessment
        passed to project_public_rows raises CompactQuoteProjectionError.

        A bare ListingIdentityAssessment is not a PriceAggregationResult
        and cannot establish reportability. The authority-safe API requires
        the frozen 4A output that carries bucket membership provenance.

        This uses a REAL ListingIdentityAssessment (not a fake class)
        to prove the contract.
        """
        # Build a real ListingIdentityAssessment (not in any result)
        standalone_assessment = _make_real_listing_identity_assessment(
            decision_value="ACCEPTED",
            price_amount=Decimal("2500.00"),
            currency_code="USD",
            condition="NEW",
        )

        # Passing it directly to project_public_rows is rejected —
        # a standalone assessment is not a PriceAggregationResult and
        # cannot establish reportability.
        with pytest.raises(CompactQuoteProjectionError, match="PriceAggregationResult"):
            project_public_rows(standalone_assessment)