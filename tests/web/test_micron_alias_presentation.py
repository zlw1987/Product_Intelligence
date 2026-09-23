"""Display-module tests for the 4D-D Micron alias presentation.

Proves the presentation layer is pure display:

* ESTABLISHED audit projection (bounded provenance only);
* alias reference rows come ONLY from persisted EXCLUDED assessments
  whose published compared MPN mechanically matches an established
  alias identifier; bucket members never produce reference rows;
* safe source URLs flagged linkable, unsafe URLs plain text;
* the exact customer-rule wording, with no claim that Micron
  officially defines R/T packaging semantics;
* the module performs no DB/provider/execution/network authority work
  (AST import boundary).
"""

from __future__ import annotations

import ast
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path
from unittest.mock import MagicMock

from product_intelligence.domain import ResearchRequest
from product_intelligence.domain.enums import (
    ConfidenceLevel,
    EvidenceDecision,
    IdentityMatchType,
    VerificationStatus,
)
from product_intelligence.execution.micron_alias_authority import (
    acquire_micron_alias_eligibility,
)
from product_intelligence.providers.page import FetchedPage, PageFetcher
from product_intelligence.research.aggregation import (
    PriceAggregateBucket,
    PriceAggregationExclusion,
    PriceAggregationExclusionReason,
    PriceAggregationResult,
)
from product_intelligence.research.listings import (
    ExtractionMethod,
    ListingObservation,
)
from product_intelligence.research.matching import (
    EvidenceSource,
    IdentityRejectionReason,
    ListingIdentityAssessment,
)
from product_intelligence.research.micron_packaging_alias import (
    MICRON_7500_REQUESTED_CATALOG_URL,
)
from product_intelligence.research.normalization import (
    NormalizedAvailability,
    NormalizedCondition,
    NormalizedListingObservation,
)
from product_intelligence.web.micron_alias_presentation import (
    ALIAS_REFERENCE_NOTE,
    ALIAS_RELATION_NOTE,
    build_micron_alias_presentation,
)

BASE = "MTFDKCC3T8TGP-1BK1DABYY"
BASER = f"{BASE}R"
BASET = f"{BASE}T"
FIXTURES = Path(__file__).resolve().parents[1] / "fixtures" / "pages"
RETRIEVED_AT = datetime(2026, 9, 22, 23, 20, 25, tzinfo=timezone.utc)


# ---------------------------------------------------------------------------
# Builders
# ---------------------------------------------------------------------------


def _established_result(mpn: str = BASER):
    """One real ESTABLISHED acquisition via the fake fetch + real fixture."""
    catalog_body = (
        FIXTURES / "micron_7500_part_catalog.json"
    ).read_text(encoding="utf-8")
    fetcher = MagicMock(spec=PageFetcher)
    fetcher.fetch.return_value = FetchedPage(
        requested_url=MICRON_7500_REQUESTED_CATALOG_URL,
        final_url=MICRON_7500_REQUESTED_CATALOG_URL,
        retrieved_at=RETRIEVED_AT,
        status_code=200,
        body_text=catalog_body,
        content_type="application/json;charset=utf-8",
        body_byte_count=len(catalog_body.encode("utf-8")),
        redirect_count=0,
        fetcher_id="test",
    )
    result = acquire_micron_alias_eligibility(
        request=ResearchRequest(
            manufacturer_part_number=mpn,
            description="Micron 7500 3.84TB datacenter SSD",
        ),
        page_fetcher=fetcher,
    )
    assert result.is_established
    return result


def _rejected_sku_assessment(
    requested_mpn: str,
    *,
    sku: str,
    source_url: str,
    price: "Decimal | None" = Decimal("2400.00"),
    currency: str = "USD",
) -> ListingIdentityAssessment:
    obs = ListingObservation(
        source_url=source_url,
        extraction_method=ExtractionMethod.JSON_LD,
        product_title="Micron 7500 3.84TB datacenter SSD",
        manufacturer_part_number_text=None,
        sku_text=sku,
        brand_text=None,
        price_text=str(price) if price is not None else None,
        currency_text=currency if price is not None else None,
        availability_text="In Stock",
        condition_text="New",
        seller_text=None,
        offer_url_text=None,
        raw_reference=None,
    )
    norm = NormalizedListingObservation(
        observation=obs,
        price_amount=price,
        currency_code=currency if price is not None else None,
        availability=NormalizedAvailability.IN_STOCK,
        condition=NormalizedCondition.NEW,
        seller_name=None,
        normalization_issues=(),
    )
    return ListingIdentityAssessment(
        normalized_listing=norm,
        requested_part_number=requested_mpn,
        candidate_part_number_raw=sku,
        candidate_part_number_compared=sku,
        candidate_evidence_source=EvidenceSource.SKU_FIELD,
        match_type=IdentityMatchType.UNKNOWN,
        decision=EvidenceDecision.REJECTED,
        rejection_reason=IdentityRejectionReason.NO_EXPLICIT_MPN_EVIDENCE,
    )


def _accepted_assessment(
    requested_mpn: str, *, source_url: str
) -> ListingIdentityAssessment:
    obs = ListingObservation(
        source_url=source_url,
        extraction_method=ExtractionMethod.JSON_LD,
        product_title="Micron 7500 3.84TB datacenter SSD",
        manufacturer_part_number_text=requested_mpn,
        sku_text=None,
        brand_text=None,
        price_text="2500.00",
        currency_text="USD",
        availability_text="In Stock",
        condition_text="New",
        seller_text=None,
        offer_url_text=None,
        raw_reference=None,
    )
    norm = NormalizedListingObservation(
        observation=obs,
        price_amount=Decimal("2500.00"),
        currency_code="USD",
        availability=NormalizedAvailability.IN_STOCK,
        condition=NormalizedCondition.NEW,
        seller_name=None,
        normalization_issues=(),
    )
    return ListingIdentityAssessment(
        normalized_listing=norm,
        requested_part_number=requested_mpn,
        candidate_part_number_raw=requested_mpn,
        candidate_part_number_compared=requested_mpn,
        candidate_evidence_source=EvidenceSource.EXPLICIT_MPN_FIELD,
        match_type=IdentityMatchType.EXACT,
        decision=EvidenceDecision.ACCEPTED,
        rejection_reason=None,
    )


def _price_result(
    request: ResearchRequest,
    *,
    accepted: "ListingIdentityAssessment | None",
    excluded: "tuple[ListingIdentityAssessment, ...]",
) -> PriceAggregationResult:
    buckets = ()
    if accepted is not None:
        buckets = (
            PriceAggregateBucket(
                currency_code="USD",
                condition=NormalizedCondition.NEW,
                assessments=(accepted,),
                count=1,
                low=Decimal("2500.00"),
                median=Decimal("2500.00"),
                high=Decimal("2500.00"),
                market_range_low=None,
                market_range_high=None,
                confidence=ConfidenceLevel.LOW,
            ),
        )
    return PriceAggregationResult(
        request=request,
        assessments=tuple([*(excluded), accepted] if accepted else list(excluded)),
        exclusions=tuple(
            PriceAggregationExclusion(
                assessment=a,
                reason=PriceAggregationExclusionReason.IDENTITY_NOT_ACCEPTED,
            )
            for a in excluded
        ),
        buckets=buckets,
        verification_status=(
            VerificationStatus.VERIFIED if accepted else VerificationStatus.UNKNOWN
        ),
    )


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestEstablishedAuditProjection:
    def test_established_fields_projected(self) -> None:
        alias_result = _established_result(BASER)
        presentation = build_micron_alias_presentation(alias_result, None)
        assert presentation.status == "ESTABLISHED"
        assert presentation.established is True
        assert presentation.requested_mpn == BASER
        assert presentation.lookup_base_candidate == BASE
        assert presentation.manufacturer == "Micron"
        assert presentation.category == "SSD"
        assert presentation.matched_base_mpn == BASE
        assert presentation.requested_source_url == MICRON_7500_REQUESTED_CATALOG_URL
        assert presentation.requested_source_url_safe is True
        assert presentation.fetched_final_url == MICRON_7500_REQUESTED_CATALOG_URL
        assert presentation.fetched_final_url_safe is True
        assert presentation.ssd_attr_id == "is-ssd"
        assert presentation.ssd_attr_value == "True"
        assert len(presentation.body_sha256) == 64
        assert presentation.alias_identifiers == (BASE, BASET)
        assert presentation.reference_rows == []

    def test_non_established_bounded_result_projects_no_reference_rows(
        self,
    ) -> None:
        fetcher = MagicMock(spec=PageFetcher)
        fetcher.fetch.side_effect = Exception  # never used; abstention below

        # NO_REQUESTED_MPN abstention: no fetch, bounded, not established.
        result = acquire_micron_alias_eligibility(
            request=ResearchRequest(manufacturer_part_number="", description="d"),
            page_fetcher=fetcher,
        )
        presentation = build_micron_alias_presentation(result, None)
        assert presentation.established is False
        assert presentation.reference_rows == []
        assert presentation.matched_base_mpn is None
        assert presentation.body_sha256 is None


class TestReferenceRows:
    def test_rows_only_from_excluded_alias_publishers(self) -> None:
        alias_result = _established_result(BASER)
        request = alias_result.request
        bucket_url = "https://bucket.example/accepted"
        ex_alias = _rejected_sku_assessment(
            BASER, sku=BASE, source_url="https://ref.example/alias"
        )
        ex_other = _rejected_sku_assessment(
            BASER, sku="COMPLETELY-OTHER", source_url="https://ref.example/other"
        )
        accepted = _accepted_assessment(BASER, source_url=bucket_url)
        price_result = _price_result(
            request, accepted=accepted, excluded=(ex_alias, ex_other)
        )
        presentation = build_micron_alias_presentation(alias_result, price_result)
        assert len(presentation.reference_rows) == 1
        row = presentation.reference_rows[0]
        assert row.source_url == "https://ref.example/alias"
        assert row.source_url_safe is True
        assert row.published_candidate_mpn == BASE
        assert row.referenced_alias == BASE
        assert row.decision == "REJECTED"
        assert row.exclusion_reason == "IDENTITY_NOT_ACCEPTED"
        # Bucket members never appear as reference rows.
        assert bucket_url not in {r.source_url for r in presentation.reference_rows}

    def test_unsafe_source_url_not_linkable(self) -> None:
        alias_result = _established_result(BASER)
        ex = _rejected_sku_assessment(
            BASER, sku=BASE, source_url="javascript:alert(1)"
        )
        price_result = _price_result(
            alias_result.request, accepted=None, excluded=(ex,)
        )
        presentation = build_micron_alias_presentation(alias_result, price_result)
        assert len(presentation.reference_rows) == 1
        assert presentation.reference_rows[0].source_url_safe is False

    def test_no_price_result_no_reference_rows(self) -> None:
        alias_result = _established_result(BASER)
        presentation = build_micron_alias_presentation(alias_result, None)
        assert presentation.reference_rows == []


class TestWording:
    def test_reference_note_exact_wording(self) -> None:
        assert ALIAS_REFERENCE_NOTE == (
            "Customer-defined packaging alias reference — excluded from "
            "pricing authority"
        )

    def test_relation_note_disclaims_manufacturer_semantics(self) -> None:
        assert (
            "Not manufacturer-published packaging identity"
            in ALIAS_RELATION_NOTE
        )
        assert "customer-defined" in ALIAS_RELATION_NOTE.lower()

    def test_module_makes_no_official_manufacturer_claim(self) -> None:
        source = (
            Path(__file__).resolve().parents[2]
            / "product_intelligence"
            / "web"
            / "micron_alias_presentation.py"
        ).read_text(encoding="utf-8")
        lowered = source.lower()
        assert "officially" not in lowered
        assert "micron defines" not in lowered
        assert "manufacturer-defined" not in lowered
        assert "rt packaging semantics" not in lowered


class TestDisplayModuleAuthorityBoundary:
    FORBIDDEN_TOPS = {
        "django",
        "urllib",
        "socket",
        "http",
        "ssl",
        "requests",
        "httpx",
    }
    FORBIDDEN_PACKAGE_PREFIXES = (
        "product_intelligence.providers",
        "product_intelligence.execution",
        "product_intelligence.semantic",
        "product_intelligence.runs",
        "product_intelligence.web.views",
    )

    def _top_level_imports(self) -> "set[str]":
        source = (
            Path(__file__).resolve().parents[2]
            / "product_intelligence"
            / "web"
            / "micron_alias_presentation.py"
        ).read_text(encoding="utf-8")
        tree = ast.parse(source)
        tops: set[str] = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    tops.add(alias.name)
            elif isinstance(node, ast.ImportFrom):
                module = node.module or ""
                if node.level == 0 and module:
                    tops.add(module)
        return tops

    def test_no_db_provider_network_or_execution_imports(self) -> None:
        tops = self._top_level_imports()
        for top in tops:
            assert top.split(".")[0] not in self.FORBIDDEN_TOPS, top
            assert not any(
                top.startswith(prefix) for prefix in self.FORBIDDEN_PACKAGE_PREFIXES
            ), top
        # Only stdlib + pure research/web display imports remain.
        for top in tops:
            if top.startswith("product_intelligence"):
                assert top in (
                    "product_intelligence.research.aggregation",
                    "product_intelligence.research.matching",
                    "product_intelligence.research.micron_packaging_alias",
                ), top
