"""Real-page fixture aggregation test (PRODUCT-INTEL.4A).

Exercises the full 3A -> 3B -> 3C -> 4A pipeline against the five recorded
real-page fixtures. No live fetch, no Serper call.

The expected result for the canonical MZ-QL23T800 request is:

    no comparable 4A bucket
    VerificationStatus.UNKNOWN

Because:
- Samsung publishes a broken/non-numeric price ("undefined") and only SKU
  identity evidence (REJECTED by 3C).
- OEMPCWorld publishes a numeric USD price but no explicit MPN (SKU only,
  REJECTED by 3C).
- ExxactCorp publishes the 3C-accepted explicit MPN and a numeric price, but
  no currency on the page (excluded by 4A as NO_COMPARABLE_CURRENCY).
- NewEgg and FusionWW yield zero listing observations.

The accepted Exxact listing should remain visible as a NO_COMPARABLE_CURRENCY
exclusion, not assigned USD by assumption.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from product_intelligence.domain import ResearchRequest
from product_intelligence.domain.enums import VerificationStatus
from product_intelligence.research.aggregation import (
    PriceAggregationExclusionReason,
    aggregate_listing_prices,
)
from product_intelligence.research.extraction import extract_listing_observations
from product_intelligence.research.matching import assess_listing_identities
from product_intelligence.research.normalization import normalize_listing_observations


# Path to the recorded page fixtures
FIXTURES_DIR = Path(__file__).resolve().parent.parent / "fixtures" / "pages"


def _load_fixture(filename: str) -> str:
    return (FIXTURES_DIR / filename).read_text(encoding="utf-8")


# The five recorded real pages from 3A
FIXTURE_FILES = [
    "samsung_us_pm9a3_mz_ql23t800.html",
    "oempcworld_pm9a3_mz_ql23t800.html",
    "exxactcorp_pm9a3_mz_ql23t800.html",
    "newegg_pm9a3_mz_ql23t800.html",
    "fusionww_access_restricted.html",
]


def test_real_fixture_snapshot_yields_unknown() -> None:
    """The full pipeline over the five real recorded pages produces UNKNOWN."""
    request = ResearchRequest("MZ-QL23T800", "Samsung PM9A3 SSD")

    all_observations = []
    for filename in FIXTURE_FILES:
        html = _load_fixture(filename)
        url = f"https://example.com/{filename}"
        observations = extract_listing_observations(html, source_url=url)
        all_observations.extend(observations)

    # 3B: normalize
    normalized = normalize_listing_observations(tuple(all_observations))

    # 3C: assess identity
    assessments = assess_listing_identities(request, normalized)

    # 4A: aggregate
    result = aggregate_listing_prices(request, assessments)

    # The canonical result: no comparable bucket
    assert result.verification_status is VerificationStatus.UNKNOWN
    assert len(result.buckets) == 0

    # All input assessments must be accounted for
    total = len(result.buckets) * 0 + len(result.exclusions)
    # Each bucket contributes len(bucket.assessments)
    bucket_count = sum(len(b.assessments) for b in result.buckets)
    total_accounted = bucket_count + len(result.exclusions)
    assert total_accounted == len(assessments)

    # The Exxact listing should be ACCEPTED by 3C (explicit MPN match)
    # but excluded by 4A for NO_COMPARABLE_CURRENCY (no currency on page)
    exxact_exclusions = [
        e for e in result.exclusions
        if e.reason is PriceAggregationExclusionReason.NO_COMPARABLE_CURRENCY
    ]
    # At least one accepted listing with no currency
    assert len(exxact_exclusions) >= 1, (
        "Expected at least one NO_COMPARABLE_CURRENCY exclusion "
        "(ExxactCorp has accepted MPN but no currency)"
    )

    # Other pages should produce IDENTITY_NOT_ACCEPTED exclusions
    identity_exclusions = [
        e for e in result.exclusions
        if e.reason is PriceAggregationExclusionReason.IDENTITY_NOT_ACCEPTED
    ]
    # Samsung (SKU only), OEMPCWorld (SKU only) should be identity-rejected
    assert len(identity_exclusions) >= 1, (
        "Expected at least one IDENTITY_NOT_ACCEPTED exclusion "
        "(Samsung/OEMPCWorld have SKU only, not explicit MPN)"
    )


def test_real_fixture_observations_count() -> None:
    """Verify the expected number of observations from real fixtures.

    This documents the real evidence so future fixture changes are visible.
    """
    all_observations = []
    for filename in FIXTURE_FILES:
        html = _load_fixture(filename)
        url = f"https://example.com/{filename}"
        observations = extract_listing_observations(html, source_url=url)
        all_observations.extend(observations)

    # Three pages publish structured data, two yield nothing
    # Samsung: 1 observation (Product + broken Offer)
    # OEMPCWorld: 1 observation (Product + Offer, JSON-LD takes precedence)
    # ExxactCorp: 1 observation (flat meta: mpn, price, etc.)
    # NewEgg: 0 observations (no static product data)
    # FusionWW: 0 observations (WebAPI, not Product)
    assert len(all_observations) == 3, (
        f"Expected 3 observations from 5 fixtures, got {len(all_observations)}; "
        "if this changes, review which fixtures publish structured data"
    )
