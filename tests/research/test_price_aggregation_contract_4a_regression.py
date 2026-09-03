"""Regression tests proving the frozen 4A result types reject AI_ASSISTED_MATCH.

PRODUCT-INTEL.HUMAN-REVIEW.4A-CONTRACT-REGRESSION.

These tests exist solely to prevent regression of the frozen 4A contract:
PriceAggregationResult, PriceAggregationExclusion, and PriceAggregateBucket
are deterministic-only. AI_ASSISTED_MATCH does not enter any frozen 4A type.

This file may be freely extended; the four frozen test files must not be
modified (per the AGENTS.md contract).
"""

from __future__ import annotations

from decimal import Decimal

import pytest

from product_intelligence.domain import ResearchRequest
from product_intelligence.domain.enums import (
    ConfidenceLevel,
    EvidenceDecision,
    IdentityMatchType,
)
from product_intelligence.research.aggregation import (
    PriceAggregationExclusion,
    PriceAggregationExclusionReason,
    PriceAggregateBucket,
    aggregate_listing_prices,
)
from product_intelligence.research.matching import (
    EvidenceSource,
    IdentityRejectionReason,
    ListingIdentityAssessment,
)
from product_intelligence.research.normalization import (
    NormalizedAvailability,
    NormalizedCondition,
    NormalizedListingObservation,
)
from product_intelligence.research.listings import (
    ExtractionMethod,
    ListingObservation,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_listing(
    url: str,
    price: Decimal,
    currency: str = "USD",
    condition: str = "NEW",
    mpn: str = "TEST-MPN",
) -> ListingObservation:
    return ListingObservation(
        source_url=url,
        extraction_method=ExtractionMethod.JSON_LD,
        manufacturer_part_number_text=mpn,
        sku_text="SKU-001",
        price_text=str(price),
        currency_text=currency,
        condition_text=condition,
    )


def _make_assessment(
    url: str = "https://example.com/1",
    decision: EvidenceDecision = EvidenceDecision.ACCEPTED,
    price: Decimal | None = Decimal("100.00"),
    currency: str | None = "USD",
    condition: NormalizedCondition = NormalizedCondition.NEW,
) -> ListingIdentityAssessment:
    price_amount = price if price is not None else Decimal("100.00")

    if decision is EvidenceDecision.AI_ASSISTED_MATCH:
        # AI-assisted: no structured identifier
        obs = ListingObservation(
            source_url=url,
            extraction_method=ExtractionMethod.JSON_LD,
            price_text=str(price_amount) if price is not None else None,
            currency_text=currency,
            condition_text="NEW",
        )
    else:
        obs = _make_listing(url, price_amount, currency, condition)

    normalized = NormalizedListingObservation(
        observation=obs,
        price_amount=price,
        currency_code=currency,
        condition=condition,
        availability=NormalizedAvailability.UNKNOWN,
        seller_name="Test Seller",
        normalization_issues=(),
    )

    if decision is EvidenceDecision.ACCEPTED:
        return ListingIdentityAssessment(
            normalized_listing=normalized,
            requested_part_number="TEST-MPN",
            candidate_part_number_raw="TEST-MPN",
            candidate_part_number_compared="TEST-MPN",
            candidate_evidence_source=EvidenceSource.EXPLICIT_MPN_FIELD,
            match_type=IdentityMatchType.EXACT,
            decision=decision,
            rejection_reason=None,
        )
    elif decision is EvidenceDecision.AI_ASSISTED_MATCH:
        return ListingIdentityAssessment(
            normalized_listing=normalized,
            requested_part_number="TEST-MPN",
            candidate_part_number_raw="",
            candidate_part_number_compared="",
            candidate_evidence_source=EvidenceSource.NONE,
            match_type=IdentityMatchType.UNKNOWN,
            decision=decision,
            rejection_reason=None,
        )
    else:
        return ListingIdentityAssessment(
            normalized_listing=normalized,
            requested_part_number="TEST-MPN",
            candidate_part_number_raw="",
            candidate_part_number_compared="",
            candidate_evidence_source=EvidenceSource.NONE,
            match_type=IdentityMatchType.UNKNOWN,
            decision=decision,
            rejection_reason=IdentityRejectionReason.NO_EXPLICIT_MPN_EVIDENCE,
        )


RESEARCH_REQUEST = ResearchRequest(
    manufacturer_part_number="TEST-MPN",
    description="Test product",
)


# ---------------------------------------------------------------------------
# Regression: PriceAggregationExclusion rejects AI_ASSISTED_MATCH
# ---------------------------------------------------------------------------


class TestFrozenExclusionRejectsAIAssisted:
    """Prove that the frozen PriceAggregationExclusion type does NOT accept
    AI_ASSISTED_MATCH for any reason that requires deterministic ACCEPTED.
    """

    def test_no_numeric_price_requires_accepted_not_ai_assisted(self) -> None:
        """AI_ASSISTED_MATCH + NO_NUMERIC_PRICE must raise ValueError.

        The frozen contract requires ACCEPTED identity for price-level
        exclusions. AI_ASSISTED_MATCH is not ACCEPTED.
        """
        assessment = _make_assessment(
            decision=EvidenceDecision.AI_ASSISTED_MATCH,
            price=None,
        )
        with pytest.raises(ValueError, match="NO_NUMERIC_PRICE requires ACCEPTED identity"):
            PriceAggregationExclusion(
                assessment=assessment,
                reason=PriceAggregationExclusionReason.NO_NUMERIC_PRICE,
            )

    def test_no_comparable_currency_requires_accepted_not_ai_assisted(self) -> None:
        """AI_ASSISTED_MATCH + NO_COMPARABLE_CURRENCY must raise ValueError."""
        assessment = _make_assessment(
            decision=EvidenceDecision.AI_ASSISTED_MATCH,
            currency=None,
        )
        with pytest.raises(ValueError, match="NO_COMPARABLE_CURRENCY requires ACCEPTED identity"):
            PriceAggregationExclusion(
                assessment=assessment,
                reason=PriceAggregationExclusionReason.NO_COMPARABLE_CURRENCY,
            )

    def test_unknown_condition_requires_accepted_not_ai_assisted(self) -> None:
        """AI_ASSISTED_MATCH + UNKNOWN_CONDITION must raise ValueError."""
        assessment = _make_assessment(
            decision=EvidenceDecision.AI_ASSISTED_MATCH,
            condition=NormalizedCondition.UNKNOWN,
        )
        with pytest.raises(ValueError, match="UNKNOWN_CONDITION requires ACCEPTED identity"):
            PriceAggregationExclusion(
                assessment=assessment,
                reason=PriceAggregationExclusionReason.UNKNOWN_CONDITION,
            )

    def test_identity_not_accepted_allows_ai_assisted(self) -> None:
        """IDENTITY_NOT_ACCEPTED is valid for AI_ASSISTED_MATCH because it IS
        non-ACCEPTED. The exclusion reason correctly reflects the identity gap.
        """
        assessment = _make_assessment(
            decision=EvidenceDecision.AI_ASSISTED_MATCH,
        )
        exclusion = PriceAggregationExclusion(
            assessment=assessment,
            reason=PriceAggregationExclusionReason.IDENTITY_NOT_ACCEPTED,
        )
        assert exclusion.reason is PriceAggregationExclusionReason.IDENTITY_NOT_ACCEPTED


# ---------------------------------------------------------------------------
# Regression: PriceAggregateBucket rejects AI_ASSISTED_MATCH
# ---------------------------------------------------------------------------


class TestFrozenBucketRejectsAIAssisted:
    """Prove that frozen PriceAggregateBucket does NOT accept AI_ASSISTED_MATCH."""

    def test_bucket_refuses_ai_assisted_member(self) -> None:
        """A bucket member with AI_ASSISTED_MATCH must raise ValueError."""
        assessment = _make_assessment(
            decision=EvidenceDecision.AI_ASSISTED_MATCH,
        )
        with pytest.raises(ValueError, match="only ACCEPTED listings contribute to a bucket"):
            PriceAggregateBucket(
                currency_code="USD",
                condition=NormalizedCondition.NEW,
                assessments=(assessment,),
                count=1,
                low=Decimal("100.00"),
                median=Decimal("100.00"),
                high=Decimal("100.00"),
                market_range_low=None,
                market_range_high=None,
                confidence=ConfidenceLevel.LOW,
            )


# ---------------------------------------------------------------------------
# Regression: aggregate_listing_prices excludes AI_ASSISTED_MATCH
# ---------------------------------------------------------------------------


class TestFrozenAggregationExcludesAIAssisted:
    """Prove that aggregate_listing_prices() excludes AI_ASSISTED_MATCH with
    IDENTITY_NOT_ACCEPTED and never includes it in a bucket.
    """

    def test_aggregate_excludes_ai_assisted_as_identity_not_accepted(self) -> None:
        """AI_ASSISTED_MATCH listings are excluded, not bucketed."""
        accepted = _make_assessment(
            decision=EvidenceDecision.ACCEPTED,
            url="https://example.com/accepted",
        )
        ai_assisted = _make_assessment(
            decision=EvidenceDecision.AI_ASSISTED_MATCH,
            url="https://example.com/ai",
        )
        result = aggregate_listing_prices(
            RESEARCH_REQUEST,
            (accepted, ai_assisted),
        )

        # The AI-assisted listing must be excluded
        exclusion_assessments = [e.assessment for e in result.exclusions]
        assert ai_assisted in exclusion_assessments

        # The exclusion reason must be IDENTITY_NOT_ACCEPTED
        ai_exclusion = next(
            e for e in result.exclusions if e.assessment is ai_assisted
        )
        assert ai_exclusion.reason is PriceAggregationExclusionReason.IDENTITY_NOT_ACCEPTED

        # The AI-assisted listing must NOT be in any bucket
        for bucket in result.buckets:
            assert ai_assisted not in bucket.assessments

    def test_aggregate_only_ai_assisted_produces_zero_buckets(self) -> None:
        """When all listings are AI_ASSISTED_MATCH, no buckets are produced."""
        ai1 = _make_assessment(
            decision=EvidenceDecision.AI_ASSISTED_MATCH,
            url="https://example.com/a",
        )
        ai2 = _make_assessment(
            decision=EvidenceDecision.AI_ASSISTED_MATCH,
            url="https://example.com/b",
        )
        result = aggregate_listing_prices(
            RESEARCH_REQUEST,
            (ai1, ai2),
        )

        assert len(result.buckets) == 0
        assert len(result.exclusions) == 2
        for e in result.exclusions:
            assert e.reason is PriceAggregationExclusionReason.IDENTITY_NOT_ACCEPTED
