"""Tests for 3C matching against recorded real-page fixtures.

These use the same reduced HTML fixtures from 3A, extracted through the real
extractor and normalized through the real normaliser, and assessed through
the real matcher. They prove that real-world pages classify as expected.
"""

from __future__ import annotations

from pathlib import Path

from product_intelligence.domain import ResearchRequest
from product_intelligence.domain.enums import (
    EvidenceDecision,
    IdentityMatchType,
)
from product_intelligence.research import (
    EvidenceSource,
    IdentityRejectionReason,
    extract_listing_observations,
    normalize_listing_observations,
    assess_listing_identity,
)

FIXTURES_DIR = Path(__file__).resolve().parent.parent / "fixtures" / "pages"

# The canonical request for all five fixtures — the Samsung PM9A3 enterprise SSD.
CANONICAL_REQUEST = ResearchRequest(
    manufacturer_part_number="MZ-QL23T800",
    description="Samsung PM9A3 3.84TB NVMe U.2 SSD",
)

# Alternative request formats the same MPN (normalisation should still match).
CASE_VARIATION_REQUEST = ResearchRequest(
    manufacturer_part_number="mz-ql23t800",
    description="Samsung PM9A3 3.84TB NVMe U.2 SSD",
)


# -- Samsung manufacturer page --


class TestSamsungManufacturerPage:
    """Samsung publishes ``sku: "MZ-QL23T800"``, no MPN field.

    The manufacturer calls it a SKU, not an MPN. The matcher records the SKU as
    evidence but does not automatically accept it — SKU alone is not enough.
    """

    def test_sku_only_not_accepted(self) -> None:
        html = (FIXTURES_DIR / "samsung_us_pm9a3_mz_ql23t800.html").read_text()
        url = "https://www.samsung.com/us/business/memory-storage/nvme-ssd/pm9a3-nvme-u-2-ssd-3-8tb-sku-mz-ql23t800/"

        raw = extract_listing_observations(html, source_url=url)
        norms = normalize_listing_observations(raw)

        assert len(norms) > 0
        for norm in norms:
            result = assess_listing_identity(CANONICAL_REQUEST, norm)
            # SKU field with matching text is still REJECTED.
            if result.candidate_evidence_source is EvidenceSource.SKU_FIELD:
                assert result.decision is EvidenceDecision.REJECTED
                assert result.rejection_reason is IdentityRejectionReason.NO_EXPLICIT_MPN_EVIDENCE

    def test_sku_value_is_mz_ql23t800(self) -> None:
        html = (FIXTURES_DIR / "samsung_us_pm9a3_mz_ql23t800.html").read_text()
        url = "https://www.samsung.com/us/business/memory-storage/nvme-ssd/pm9a3-nvme-u-2-ssd-3-8tb-sku-mz-ql23t800/"

        raw = extract_listing_observations(html, source_url=url)

        sku_obs = [r for r in raw if r.sku_text is not None]
        assert len(sku_obs) > 0
        assert sku_obs[0].sku_text == "MZ-QL23T800"


# -- OEMPCWorld retailer page --


class TestOempcworldPage:
    """OEMPCWorld publishes ``sku: "501489"`` (retailer internal), no MPN.

    The MPN appears only in the product title. Title text is recorded but never
    automatically accepted.
    """

    def test_internal_sku_rejected(self) -> None:
        html = (FIXTURES_DIR / "oempcworld_pm9a3_mz_ql23t800.html").read_text()
        url = "https://oempcworld.com/products/samsung-pm9a3-3-84tb-mz-ql23t800-nvme-pcie-4-0-x4"

        raw = extract_listing_observations(html, source_url=url)
        norms = normalize_listing_observations(raw)

        assert len(norms) > 0
        # Prove the fixture actually produces an observation with an SKU.
        sku_norms = [
            n for n in norms
            if n.observation.sku_text is not None
        ]
        assert len(sku_norms) > 0, "OEMPCWorld fixture should produce at least one observation with an SKU"
        # The SKU is the retailer's internal number, not the MPN.
        assert sku_norms[0].observation.sku_text == "501489"

        for norm in norms:
            result = assess_listing_identity(CANONICAL_REQUEST, norm)
            # Every observation from this page is REJECTED.
            assert result.decision is EvidenceDecision.REJECTED
            # The SKU field is found first (higher priority than title text).
            if result.candidate_evidence_source is EvidenceSource.SKU_FIELD:
                assert result.rejection_reason is IdentityRejectionReason.NO_EXPLICIT_MPN_EVIDENCE

    def test_title_mpn_does_not_cause_acceptance_when_sku_present(self) -> None:
        """OEMPCWorld publishes sku='501489' and title containing 'MZ-QL23T800'.

        Since the SKU field exists, it is selected as the evidence source over
        title text. The listing is REJECTED with NO_EXPLICIT_MPN_EVIDENCE.
        The MPN appearing in the title does not change the outcome.
        """
        html = (FIXTURES_DIR / "oempcworld_pm9a3_mz_ql23t800.html").read_text()
        url = "https://oempcworld.com/products/samsung-pm9a3-3-84tb-mz-ql23t800-nvme-pcie-4-0-x4"

        raw = extract_listing_observations(html, source_url=url)
        norms = normalize_listing_observations(raw)

        assert len(norms) > 0
        for norm in norms:
            result = assess_listing_identity(CANONICAL_REQUEST, norm)
            # The listing is REJECTED — title text alone never produces ACCEPTED.
            assert result.decision is EvidenceDecision.REJECTED
            # SKU takes priority over title; the candidate evidence source is
            # SKU_FIELD, not TITLE_TEXT.
            if norm.observation.sku_text is not None:
                assert result.candidate_evidence_source is EvidenceSource.SKU_FIELD


# -- ExxactCorp retailer page --


class TestExxactcorpPage:
    """ExxactCorp publishes ``mpn: "mpn:MZ-QL23T800"`` (with wrapper).

    After ``mpn:`` wrapper cleanup, this matches EXACT and produces ACCEPTED.
    This is the canonical real-page evidence for the wrapper cleanup rule.
    """

    def test_wrapper_mpn_accepted_exact(self) -> None:
        html = (FIXTURES_DIR / "exxactcorp_pm9a3_mz_ql23t800.html").read_text()
        url = "https://www.exxactcorp.com/samsung-mz-ql23t800-pm9a3-3-84-tb-ssd"

        raw = extract_listing_observations(html, source_url=url)
        norms = normalize_listing_observations(raw)

        assert len(norms) > 0
        mpn_norms = [
            n for n in norms
            if n.observation.manufacturer_part_number_text is not None
        ]
        assert len(mpn_norms) > 0

        result = assess_listing_identity(CANONICAL_REQUEST, mpn_norms[0])

        assert result.decision is EvidenceDecision.ACCEPTED
        assert result.match_type is IdentityMatchType.EXACT
        assert result.candidate_evidence_source is EvidenceSource.EXPLICIT_MPN_FIELD
        assert result.candidate_part_number_raw == "mpn:MZ-QL23T800"
        assert result.candidate_part_number_compared == "MZ-QL23T800"
        assert result.rejection_reason is None

    def test_wrapper_mpn_case_variation(self) -> None:
        html = (FIXTURES_DIR / "exxactcorp_pm9a3_mz_ql23t800.html").read_text()
        url = "https://www.exxactcorp.com/samsung-mz-ql23t800-pm9a3-3-84-tb-ssd"

        raw = extract_listing_observations(html, source_url=url)
        norms = normalize_listing_observations(raw)

        result = assess_listing_identity(CASE_VARIATION_REQUEST, norms[0])

        # Lowercase request matches the uppercase fixture after normalization.
        assert result.decision is EvidenceDecision.ACCEPTED
        assert result.match_type in (
            IdentityMatchType.EXACT,
            IdentityMatchType.NORMALIZED_EXACT,
        )

    def test_exxactcorp_sku_not_used_when_mpn_present(self) -> None:
        """ExxactCorp publishes both mpn and sku; mpn takes priority."""
        html = (FIXTURES_DIR / "exxactcorp_pm9a3_mz_ql23t800.html").read_text()
        url = "https://www.exxactcorp.com/samsung-mz-ql23t800-pm9a3-3-84-tb-ssd"

        raw = extract_listing_observations(html, source_url=url)
        norms = normalize_listing_observations(raw)

        for norm in norms:
            result = assess_listing_identity(CANONICAL_REQUEST, norm)
            assert result.candidate_evidence_source is not EvidenceSource.SKU_FIELD

    def test_description_only_wrapped_mpn_undecided(self) -> None:
        """D: Description-only request + real Exxact fixture (mpn:MZ-QL23T800).

        Regression: proves the full pipeline
        extraction -> normalization -> assess_listing_identity
        returns UNDECIDED for a description-only request against the
        Exxact page whose MPN field publishes "mpn:MZ-QL23T800".
        No exception must be raised.
        """
        from product_intelligence.domain import ResearchRequest

        html = (FIXTURES_DIR / "exxactcorp_pm9a3_mz_ql23t800.html").read_text()
        url = "https://www.exxactcorp.com/samsung-mz-ql23t800-pm9a3-3-84-tb-ssd"

        raw = extract_listing_observations(html, source_url=url)
        norms = normalize_listing_observations(raw)

        assert len(norms) > 0
        desc_request = ResearchRequest(
            manufacturer_part_number="",
            description="Samsung PM9A3 SSD",
        )

        # Full pipeline must not raise
        result = assess_listing_identity(desc_request, norms[0])

        assert result.decision is EvidenceDecision.UNDECIDED
        assert result.match_type is IdentityMatchType.UNKNOWN
        assert result.rejection_reason is IdentityRejectionReason.NO_REQUESTED_MPN
        assert result.candidate_evidence_source is EvidenceSource.EXPLICIT_MPN_FIELD
        assert result.candidate_part_number_raw == "mpn:MZ-QL23T800"
        assert result.candidate_part_number_compared == "MZ-QL23T800"


# -- Newegg marketplace page --


class TestNeweggPage:
    """Newegg yields zero observations (client-side rendering).

    Zero observations means zero assessments — nothing to reject.
    """

    def test_zero_observations(self) -> None:
        html = (FIXTURES_DIR / "newegg_pm9a3_mz_ql23t800.html").read_text()
        url = "https://www.newegg.com/samsung-mz-ql23t800/p/N82E16820157284"

        raw = extract_listing_observations(html, source_url=url)

        assert len(raw) == 0


# -- FusionWW access-restricted page --


class TestFusionwwPage:
    """FusionWW returns a soft block with no product data.

    Zero observations, no assessment possible.
    """

    def test_zero_observations(self) -> None:
        html = (FIXTURES_DIR / "fusionww_access_restricted.html").read_text()
        url = "https://www.fusionww.com/samsung-mz-ql23t800-pm9a3"

        raw = extract_listing_observations(html, source_url=url)

        assert len(raw) == 0
