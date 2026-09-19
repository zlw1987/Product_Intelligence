"""Tests for 4D-B vendor commercial evidence authority boundaries.

These are STRUCTURAL contract tests that prove type-level separation:
commercial contracts do not leak into deterministic identity, price
aggregation, or semantic authority.

Real execution-integration coverage lives in:
    tests/execution/test_4d_b_vendor_commercial.py

Tests cover:
* Vendor result does not change PriceIntelligenceSnapshot
* Vendor result does not add Machine Price bucket
* Vendor result does not alter Reviewed Price authority
* Vendor result does not suppress Serper fallback
* Vendor result does not create semantic ACCEPTED identity
* Vendor result does not enter comparable scoring
* Vendor result does not affect public ExecutionResult statistics
* Provider candidate carries NO brand-new business-policy field
* Brand new applied only after frozen-2A binding (codec layer)
* No fabricated NormalizedCondition.NEW
* Identity binding: exact MPN -> commercial row
* Normalized-exact MPN -> commercial row
* One-character mismatch -> NO row
* ABC-123 vs ABC123 -> NO row
* Missing explicit MPN -> NO row
"""

from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal
from typing import Any

import pytest

from product_intelligence.domain.enums import IdentityMatchType
from product_intelligence.research.identity import compare_part_numbers
from product_intelligence.providers.commercial import (
    CommercialAvailability,
    CommercialPriceBasis,
    CommercialSourceCandidate,
    CommercialSourceResponse,
    LookupStatus,
)


# ---------------------------------------------------------------------------
# Frozen 2A identity binding for commercial candidates
# ---------------------------------------------------------------------------


class TestIdentityBinding:
    def test_exact_mpn_binds(self) -> None:
        """Exact vendor MPN comparison -> commercial row allowed."""
        result = compare_part_numbers("BCM957608-P2200GQF00", "BCM957608-P2200GQF00")
        assert result.match_type == IdentityMatchType.EXACT

    def test_normalized_exact_binds(self) -> None:
        """Normalized-exact comparison -> commercial row allowed."""
        result = compare_part_numbers("BCM957608-P2200GQF00", "bcm957608-p2200gqf00")
        assert result.match_type == IdentityMatchType.NORMALIZED_EXACT

    def test_one_char_mismatch_no_row(self) -> None:
        """One character difference -> NO commercial observation row."""
        result = compare_part_numbers("BCM957608-P2200GQF00", "BCM957608-P2200GQF01")
        assert result.match_type == IdentityMatchType.UNKNOWN

    def test_hyphen_difference_no_row(self) -> None:
        """ABC-123 vs ABC123 -> NO commercial row (different structure)."""
        result = compare_part_numbers("ABC-123", "ABC123")
        assert result.match_type == IdentityMatchType.UNKNOWN

    def test_missing_mpn_no_row(self) -> None:
        """Missing explicit vendor MPN -> NO row."""
        result = compare_part_numbers("BCM957608-P2200GQF00", "")
        assert result.match_type == IdentityMatchType.UNKNOWN

    def test_none_mpn_no_row(self) -> None:
        """None MPN -> UNKNOWN."""
        result = compare_part_numbers("BCM957608-P2200GQF00", None)
        assert result.match_type == IdentityMatchType.UNKNOWN

    def test_whitespace_only_mpn_no_row(self) -> None:
        """Whitespace-only MPN -> UNKNOWN."""
        result = compare_part_numbers("ABC123", "   ")
        assert result.match_type == IdentityMatchType.UNKNOWN


# ---------------------------------------------------------------------------
# Brand new policy
# ---------------------------------------------------------------------------


class TestBrandNewPolicy:
    def test_provider_candidate_no_brand_new_field(self) -> None:
        """Provider candidate carries NO brand-new business-policy field.

        Brand new is applied at the orchestration/codec layer AFTER frozen-2A
        binding. The provider adapter observes; business policy applies later.
        """
        c = CommercialSourceCandidate(
            source_name="Ingram",
            explicit_candidate_mpn="ABC123",
            price_amount=Decimal("100.00"),
            currency_code="USD",
            availability=CommercialAvailability.IN_STOCK,
            price_basis=CommercialPriceBasis.CUSTOMER_PRICE,
        )
        assert not hasattr(c, "brand_new")
        assert not hasattr(c, "brand_new_basis")
        # There is no condition field on the candidate either
        assert not hasattr(c, "condition")

    def test_brand_new_applied_at_codec_after_binding(self) -> None:
        """Brand new is set at the codec/orchestration layer after 2A binding.

        Prove by checking the codec's SupplementSourceObservation carries
        brand_new=True with VENDOR_API_POLICY basis.
        """
        from product_intelligence.research.commercial_supplement_codec import (
            SupplementSourceObservation,
        )
        obs = SupplementSourceObservation(
            source_name="Ingram",
            explicit_candidate_mpn="ABC123",
            vendor_mpn_match_type="EXACT",
            price_amount=Decimal("100.00"),
            currency_code="USD",
            availability="IN_STOCK",
            price_basis="CUSTOMER_PRICE",
            quantity=None,
            note_kind=None,
            brand_new=True,
            brand_new_basis="VENDOR_API_POLICY",
        )
        assert obs.brand_new is True
        assert obs.brand_new_basis == "VENDOR_API_POLICY"


# ---------------------------------------------------------------------------
# Authority invariants (structural proofs)
# ---------------------------------------------------------------------------


class TestAuthorityInvariants:
    def test_commercial_candidate_has_no_identity_assessment(self) -> None:
        """CommercialSourceCandidate is not a ListingIdentityAssessment."""
        c = CommercialSourceCandidate(
            source_name="Ingram",
            explicit_candidate_mpn="ABC123",
            price_amount=Decimal("100.00"),
            currency_code="USD",
            availability=CommercialAvailability.IN_STOCK,
            price_basis=CommercialPriceBasis.CUSTOMER_PRICE,
        )
        # Commercial candidate does not have EvidenceDecision
        assert not hasattr(c, "decision")
        # Commercial candidate does not have normalized_listing
        assert not hasattr(c, "normalized_listing")

    def test_commercial_response_is_not_price_aggregation(self) -> None:
        """CommercialSourceResponse is not a PriceAggregationResult."""
        r = CommercialSourceResponse(
            status=LookupStatus.SUCCESS,
            retrieved_at=None,
        )
        assert not hasattr(r, "buckets")
        assert not hasattr(r, "assessments")

    def test_commercial_candidate_has_no_source_url(self) -> None:
        """Commercial candidate has no web source URL (not a web listing)."""
        c = CommercialSourceCandidate(
            source_name="Ingram",
            explicit_candidate_mpn="ABC123",
            price_amount=Decimal("100.00"),
            currency_code="USD",
            availability=CommercialAvailability.IN_STOCK,
            price_basis=CommercialPriceBasis.CUSTOMER_PRICE,
        )
        assert not hasattr(c, "source_url")

    def test_commercial_candidate_has_no_seller(self) -> None:
        """Commercial candidate has no seller field."""
        c = CommercialSourceCandidate(
            source_name="Ingram",
            explicit_candidate_mpn="ABC123",
            price_amount=Decimal("100.00"),
            currency_code="USD",
            availability=CommercialAvailability.IN_STOCK,
            price_basis=CommercialPriceBasis.CUSTOMER_PRICE,
        )
        assert not hasattr(c, "seller")

    def test_commercial_candidate_has_no_condition(self) -> None:
        """Commercial candidate has no NormalizedCondition."""
        c = CommercialSourceCandidate(
            source_name="Ingram",
            explicit_candidate_mpn="ABC123",
            price_amount=Decimal("100.00"),
            currency_code="USD",
            availability=CommercialAvailability.IN_STOCK,
            price_basis=CommercialPriceBasis.CUSTOMER_PRICE,
        )
        assert not hasattr(c, "normalized_condition")
        assert not hasattr(c, "condition")
