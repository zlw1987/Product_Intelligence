"""Offline integration of the sales-unit extraction layer against the
RECORDED LISTING FIXTURES (PRODUCT-INTEL.SEMANTIC-AUTHORITY-V2-Q3-B5-P2).

Like the 3A / 3B recorded-page tests, every fixture here is the same real,
recorded page used by the extraction phase, run one step further through
the NEW bounded extractor:

    extract_listing_observations() -> extract_sales_unit_evidence()
                                     -> sales_unit_channel_from_extraction()

Nothing here fetches, and nothing here fabricates a page. The recorded
pages publish no packaging field (the 3A extractor carries none), and
their titles carry specification quantities (capacity, chassis height,
port / lane / channel counts) that must NOT be read as sales quantities.
Every recorded observation therefore extracts to the recorded absence
(``NO_PACKAGING_PUBLISHED`` -> the frozen channel's ``UNAVAILABLE``), and
the separately gated integration shape (recorded input construction with
the extracted channel) stays fail-closed over the real evidence: the
silent residual remains UNPROVEN (the R1 / R14 live-audit watch item),
while the frozen live builder still records UNAVAILABLE byte-for-byte.
"""

from __future__ import annotations

import dataclasses
from pathlib import Path

from product_intelligence.domain import ResearchRequest
from product_intelligence.research import (
    AUTHORITY_CONTRACT_VERSION_V2,
    AUTHORITY_CONTRACT_VERSION_V2_FU3,
    CandidateSalesUnitEvidenceV2,
    ListingObservation,
    PackagingEvidenceStateV2,
    SalesUnitKindV2,
    SalesUnitAuthorityV2,
    assess_listing_identity,
    build_candidate_commercial_evidence_v2,
    build_semantic_match_case_v2,
    build_v2_product_evidence_profile,
    derive_authority_tier_for_contract,
    derive_identity_state_v2,
    normalize_listing_observation,
    sales_unit_authority_from_channel,
)
import pytest

from product_intelligence.research import sales_unit_extraction as sui
from product_intelligence.research.extraction import extract_listing_observations
from product_intelligence.research.semantic_v2 import SemanticMatchCaseV2

FIXTURE_ROOT = Path(__file__).resolve().parents[1] / "fixtures" / "pages"

SAMSUNG_URL = (
    "https://www.samsung.com/us/business/memory-storage/nvme-ssd/"
    "pm9a3-nvme-u-2-ssd-3-8tb-sku-mz-ql23t800/"
)
OEMPCWORLD_URL = (
    "https://oempcworld.com/products/samsung-pm9a3-3-84tb-mz-ql23t800-nvme-pcie-4-0-x4"
)
EXXACT_URL = "https://www.exxactcorp.com/Samsung-MZ-QL23T800-E5387548"
DIRECTMACRO_URL = "https://www.directd.com/product/BCM957608-P2200GQF00"
NEWEGG_URL = "https://www.newegg.com/p/2RC-0034-00762"
FUSIONWW_URL = "https://www.fusionww.com/shop/product/4267839/MZ-QL23T800"


def _observations(name: str, url: str) -> tuple[ListingObservation, ...]:
    document = (FIXTURE_ROOT / name).read_text(encoding="utf-8")
    return extract_listing_observations(document, source_url=url)


class TestRecordedPagesPublishNoPackagingEvidence:
    """The real recorded retail pages: specification quantities in the
    titles are NOT sales quantities, no packaging field is published, and
    the extractor records the absence (never invents a unit)."""

    def test_samsung_recorded_page(self) -> None:
        observations = _observations(
            "samsung_us_pm9a3_mz_ql23t800.html", SAMSUNG_URL
        )
        assert len(observations) == 1
        observation = observations[0]
        # "PM9A3 NVMe U.2 3.84TB": capacity (3.84TB) and form (U.2) —
        # no packaging word.
        assert "3.84TB" in (observation.product_title or "")
        result = sui.extract_sales_unit_evidence(observation)
        assert result.state is sui.SalesUnitExtractionState.NO_PACKAGING_PUBLISHED
        assert result.cues == ()
        assert result.established_kind is None
        channel = sui.sales_unit_channel_from_extraction(result)
        assert channel.state is PackagingEvidenceStateV2.UNAVAILABLE

    def test_oempcworld_recorded_page(self) -> None:
        observations = _observations(
            "oempcworld_pm9a3_mz_ql23t800.html", OEMPCWORLD_URL
        )
        assert len(observations) == 1
        observation = observations[0]
        # "PCIe 4.0 x4": interface + lane count — not a four-pack.
        assert observation.product_title == (
            "Samsung PM9A3 3.84TB MZ-QL23T800 NVMe PCIe 4.0 x4"
        )
        result = sui.extract_sales_unit_evidence(observation)
        assert result.state is sui.SalesUnitExtractionState.NO_PACKAGING_PUBLISHED
        assert result.cues == ()
        channel = sui.sales_unit_channel_from_extraction(result)
        assert channel.state is PackagingEvidenceStateV2.UNAVAILABLE

    def test_exxactcorp_recorded_page(self) -> None:
        observations = _observations("exxactcorp_pm9a3_mz_ql23t800.html", EXXACT_URL)
        assert len(observations) == 1
        observation = observations[0]
        # "2.5" form factor, "1 DWPD", "256-bit AES" — specification
        # quantities, none of them a sales quantity.
        result = sui.extract_sales_unit_evidence(observation)
        assert result.state is sui.SalesUnitExtractionState.NO_PACKAGING_PUBLISHED
        assert result.cues == ()
        channel = sui.sales_unit_channel_from_extraction(result)
        assert channel.state is PackagingEvidenceStateV2.UNAVAILABLE

    def test_directmacro_recorded_page_dual_port_is_not_a_two_pack(self) -> None:
        observations = _observations(
            "directmacro_bcm957608_p2200gqf00_search.html", DIRECTMACRO_URL
        )
        assert len(observations) == 1
        observation = observations[0]
        assert "Dual-Port" in (observation.product_title or "")
        result = sui.extract_sales_unit_evidence(observation)
        assert result.state is sui.SalesUnitExtractionState.NO_PACKAGING_PUBLISHED
        assert result.cues == ()
        channel = sui.sales_unit_channel_from_extraction(result)
        assert channel.state is PackagingEvidenceStateV2.UNAVAILABLE

    def test_newegg_and_fusionww_publish_no_observations(self) -> None:
        # The recorded page publishes no extractable offer (access
        # restricted / no structured data): there is nothing to extract,
        # and no observation — let alone packaging evidence — is
        # fabricated.
        assert _observations("newegg_pm9a3_mz_ql23t800.html", NEWEGG_URL) == ()
        assert _observations("fusionww_access_restricted.html", FUSIONWW_URL) == ()


class TestRecordedPageIntegrationShapes:
    """The two coexisting channel constructions over the SAME recorded
    evidence: the frozen live builder (S2-C behavior, always UNAVAILABLE)
    and the separately gated integration shape (extracted channel into a
    recorded input). Neither activates V2 authority or pricing."""

    def test_frozen_live_builder_and_extractor_agree_on_recorded_evidence(
        self,
    ) -> None:
        for name, url in (
            ("samsung_us_pm9a3_mz_ql23t800.html", SAMSUNG_URL),
            ("oempcworld_pm9a3_mz_ql23t800.html", OEMPCWORLD_URL),
            ("exxactcorp_pm9a3_mz_ql23t800.html", EXXACT_URL),
            ("directmacro_bcm957608_p2200gqf00_search.html", DIRECTMACRO_URL),
        ):
            for observation in _observations(name, url):
                # Frozen S2-C behavior: the live builder records the
                # explicit UNAVAILABLE state (byte-for-byte the canonical
                # absence).
                commercial = build_candidate_commercial_evidence_v2(observation)
                assert commercial.sales_unit.state is (
                    PackagingEvidenceStateV2.UNAVAILABLE
                )
                assert commercial.sales_unit.kind is None
                assert commercial.sales_unit.quantity is None
                assert commercial.sales_unit.raw_detail is None
                assert commercial.sales_unit.source is None
                # The extractor over the same observation: the recorded
                # absence (no packaging published on any recorded page).
                result = sui.extract_sales_unit_evidence(observation)
                assert result.state is (
                    sui.SalesUnitExtractionState.NO_PACKAGING_PUBLISHED
                )
                channel = sui.sales_unit_channel_from_extraction(result)
                assert channel.state is PackagingEvidenceStateV2.UNAVAILABLE

    def test_gated_integration_shape_stays_fail_closed_on_recorded_evidence(
        self,
    ) -> None:
        """Recorded input construction: the real frozen chain (3A -> 3B
        -> 3C -> S2-A -> the V2 case builder) over the oempcworld
        recorded page (U2_SKU_ONLY, V2-eligible). The frozen builder's
        case records UNAVAILABLE; the gated integration shape replaces
        ONLY the channel with the extractor's output — and over this
        recorded page the extracted channel is the same recorded
        absence, so the FU3 derivation stays UNPROVEN (the silent
        residual: never proven, never auto-priced)."""
        observations = _observations(
            "oempcworld_pm9a3_mz_ql23t800.html", OEMPCWORLD_URL
        )
        observation = observations[0]
        request = ResearchRequest(
            manufacturer_part_number="MZ-QL23T800",
            description="3.84TB U.2 NVMe SSD",
        )
        assessment = assess_listing_identity(
            request, normalize_listing_observation(observation)
        )
        context = derive_identity_state_v2(assessment)
        profile = build_v2_product_evidence_profile(
            observation=assessment.normalized_listing.observation,
            context_provenances=frozenset(),
            matched_facts=frozenset(),
        )
        case = build_semantic_match_case_v2(
            case_id="p2-recorded-0",
            request=request,
            assessment=assessment,
            context=context,
            product_evidence=profile,
            context_provenances=frozenset(),
            reviewed_target_context=None,
        )
        assert isinstance(case, SemanticMatchCaseV2)
        # Frozen live shape: the recorded absence.
        assert case.candidate_commercial.sales_unit.state is (
            PackagingEvidenceStateV2.UNAVAILABLE
        )
        # Gated integration shape: the extracted channel replaces the
        # frozen one (the same recorded absence for this page).
        result = sui.extract_sales_unit_evidence(observation)
        channel = sui.sales_unit_channel_from_extraction(result)
        replaced = dataclasses.replace(
            case,
            candidate_commercial=dataclasses.replace(
                case.candidate_commercial, sales_unit=channel
            ),
        )
        assert isinstance(replaced, SemanticMatchCaseV2)
        assert (
            sales_unit_authority_from_channel(
                replaced.candidate_commercial.sales_unit
            )
            is SalesUnitAuthorityV2.UNPROVEN
        )
        # The same shape, with a HYPOTHETICAL published pack (the
        # recorded page publishes none — this is the integration's
        # fail-closed behavior, not a claim about the page): the
        # candidate-internal contradiction and the published-incompatible
        # unit behave exactly as the FU3 contract specifies.
        hypothetical_pack: CandidateSalesUnitEvidenceV2 = (
            sui.sales_unit_channel_from_extraction(
                sui.extract_sales_unit_evidence(
                    dataclasses.replace(
                        observation, product_title="Samsung PM9A3 3.84TB (pack of 4)"
                    )
                )
            )
        )
        assert hypothetical_pack.state is PackagingEvidenceStateV2.OBSERVED
        assert hypothetical_pack.kind is SalesUnitKindV2.PACK_QUANTITY
        assert hypothetical_pack.quantity == 4
        pack_case = dataclasses.replace(
            case,
            candidate_commercial=dataclasses.replace(
                case.candidate_commercial, sales_unit=hypothetical_pack
            ),
        )
        assert (
            sales_unit_authority_from_channel(
                pack_case.candidate_commercial.sales_unit
            )
            is SalesUnitAuthorityV2.CONTRADICTED
        )
        assert (
            sales_unit_authority_from_channel(
                pack_case.candidate_commercial.sales_unit
            )
            is SalesUnitAuthorityV2.CONTRADICTED
        )
        # The old token's replay is unchanged by any of this: the frozen
        # derivation has no sales-unit input (contract misuse fails
        # closed; the extractor never reinterprets old records).
        with pytest.raises(ValueError, match="no sales-unit input"):
            derive_authority_tier_for_contract(
                AUTHORITY_CONTRACT_VERSION_V2,
                context,
                None,
                frozenset(),
                profile,
                None,
                sales_unit_channel=pack_case.candidate_commercial.sales_unit,
            )
        # The FU3 token is the separately versioned one the gated
        # integration will derive under (still unreachable from any live
        # path: no production record can carry it today).
        assert AUTHORITY_CONTRACT_VERSION_V2_FU3 == "SEMANTIC_AUTHORITY_V2_S2A_FU3"
