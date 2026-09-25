"""End-to-end historical report tests for the 4D-D alias section.

Real ``GET /research/<uuid>`` with persisted
``PriceIntelligenceSnapshot`` + ``ResearchMicronAliasSnapshot``:

* ESTABLISHED audit renders (source-published BASE, Micron, SSD,
  customer-rule distinction);
* alias exclusion references render in their own section only —
  absent from Compact Quote, Machine Price rows, Reviewed Price,
  and Comparable;
* no snapshot -> no alias section; bounded non-established -> no
  reference authority; malformed/tampered/version-mismatched/
  provenance-mismatched -> bounded "unavailable", main report
  still renders;
* programming RuntimeError propagates (never "unavailable");
* the historical GET performs ZERO live Micron / search / page /
  vendor / FX / semantic / generic-urllib work (armed fail-fast).
"""

from __future__ import annotations

from contextlib import contextmanager
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path
from unittest.mock import MagicMock, patch

from django.test import Client, TestCase
from django.urls import reverse

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
from product_intelligence.providers.http_page import HttpPageFetcher
from product_intelligence.providers.page import FetchedPage
from product_intelligence.providers.internal_vendor import InternalVendorAdapter
from product_intelligence.providers.fx import EcbFxProvider
from product_intelligence.providers.serper import SerperSearchProvider
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
from product_intelligence.research.micron_alias_codec import (
    encode_micron_alias_snapshot,
)
from product_intelligence.research.micron_packaging_alias import (
    MICRON_7500_REQUESTED_CATALOG_URL,
)
from product_intelligence.research.normalization import (
    NormalizedAvailability,
    NormalizedCondition,
    NormalizedListingObservation,
)
from product_intelligence.research.price_result_codec import (
    encode_price_aggregation_result,
)
from product_intelligence.runs.models import (
    PriceIntelligenceSnapshot,
    ResearchMicronAliasSnapshot,
    ResearchRun,
)
from product_intelligence.semantic.runtime import SemanticRuntime
from product_intelligence.execution import semantic_integration

BASE = "MTFDKCC3T8TGP-1BK1DABYY"
BASER = f"{BASE}R"
DESC = "Micron 7500 3.84TB datacenter SSD"
SIBLING_URL = "https://sibling-report.example/listing"
ACCEPTED_URL = "https://accepted-report.example/listing"
FIXTURES = Path(__file__).resolve().parents[1] / "fixtures" / "pages"


# ---------------------------------------------------------------------------
# Builders
# ---------------------------------------------------------------------------


def _assessment(
    *,
    requested: str,
    source_url: str,
    mpn: "str | None",
    sku: "str | None",
    decision: EvidenceDecision,
    rejection: "IdentityRejectionReason | None",
    match_type: IdentityMatchType,
    source: EvidenceSource,
    compared: str,
    price: Decimal,
) -> ListingIdentityAssessment:
    obs = ListingObservation(
        source_url=source_url,
        extraction_method=ExtractionMethod.JSON_LD,
        product_title="Micron 7500 3.84TB datacenter SSD",
        manufacturer_part_number_text=mpn,
        sku_text=sku,
        brand_text=None,
        price_text=str(price),
        currency_text="USD",
        availability_text="In Stock",
        condition_text="New",
        seller_text=None,
        offer_url_text=None,
        raw_reference=None,
    )
    norm = NormalizedListingObservation(
        observation=obs,
        price_amount=price,
        currency_code="USD",
        availability=NormalizedAvailability.IN_STOCK,
        condition=NormalizedCondition.NEW,
        seller_name=None,
        normalization_issues=(),
    )
    return ListingIdentityAssessment(
        normalized_listing=norm,
        requested_part_number=requested,
        candidate_part_number_raw=compared,
        candidate_part_number_compared=compared,
        candidate_evidence_source=source,
        match_type=match_type,
        decision=decision,
        rejection_reason=rejection,
    )


def _report_price_result(run: ResearchRun) -> PriceAggregationResult:
    mpn = run.manufacturer_part_number
    accepted = _assessment(
        requested=mpn,
        source_url=ACCEPTED_URL,
        mpn=mpn,
        sku=None,
        decision=EvidenceDecision.ACCEPTED,
        rejection=None,
        match_type=IdentityMatchType.EXACT,
        source=EvidenceSource.EXPLICIT_MPN_FIELD,
        compared=mpn,
        price=Decimal("2500.00"),
    )
    sibling = _assessment(
        requested=mpn,
        source_url=SIBLING_URL,
        mpn=None,
        sku=BASE,
        decision=EvidenceDecision.REJECTED,
        rejection=IdentityRejectionReason.NO_EXPLICIT_MPN_EVIDENCE,
        match_type=IdentityMatchType.UNKNOWN,
        source=EvidenceSource.SKU_FIELD,
        compared=BASE,
        price=Decimal("2400.00"),
    )
    return PriceAggregationResult(
        request=run.to_research_request(),
        assessments=(accepted, sibling),
        exclusions=(
            PriceAggregationExclusion(
                assessment=sibling,
                reason=PriceAggregationExclusionReason.IDENTITY_NOT_ACCEPTED,
            ),
        ),
        buckets=(
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
        ),
        verification_status=VerificationStatus.VERIFIED,
    )


def _persist_price_snapshot(run: ResearchRun, result: PriceAggregationResult) -> None:
    PriceIntelligenceSnapshot.objects.create(
        run=run,
        schema_version=1,
        payload=encode_price_aggregation_result(result),
    )


def _acquire_for(mpn: str, description: str = DESC):
    catalog_body = (
        FIXTURES / "micron_7500_part_catalog.json"
    ).read_text(encoding="utf-8")
    fetcher = MagicMock(spec=HttpPageFetcher)
    fetcher.fetch.return_value = FetchedPage(
        requested_url=MICRON_7500_REQUESTED_CATALOG_URL,
        final_url=MICRON_7500_REQUESTED_CATALOG_URL,
        retrieved_at=datetime(2026, 9, 22, 23, 20, 25, tzinfo=timezone.utc),
        status_code=200,
        body_text=catalog_body,
        content_type="application/json;charset=utf-8",
        body_byte_count=len(catalog_body.encode("utf-8")),
        redirect_count=0,
        fetcher_id="test",
    )
    return acquire_micron_alias_eligibility(
        request=ResearchRequest(
            manufacturer_part_number=mpn, description=description
        ),
        page_fetcher=fetcher,
    )


def _established_payload(mpn: str = BASER, description: str = DESC) -> dict:
    return encode_micron_alias_snapshot(_acquire_for(mpn, description))


def _make_run(
    mpn: str = BASER,
    description: str = DESC,
    *,
    alias_payload: "dict | None" = None,
    alias_version: int = 1,
) -> ResearchRun:
    run = ResearchRun.objects.create_from_request(
        ResearchRequest(manufacturer_part_number=mpn, description=description)
    )
    _persist_price_snapshot(run, _report_price_result(run))
    if alias_payload is not None:
        ResearchMicronAliasSnapshot.objects.create(
            run=run, schema_version=alias_version, payload=alias_payload
        )
    return run


def _section(html: str, heading: str) -> str:
    """Text of the page from ``<h2>heading</h2>`` to the next ``<h2>``."""
    marker = f"<h2>{heading}</h2>"
    start = html.find(marker)
    if start == -1:
        return ""
    rest = html[start + len(marker):]
    nxt = rest.find("<h2>")
    return rest[:nxt] if nxt != -1 else rest


@contextmanager
def _armed_live_boundaries():
    """Arm every live provider/network/semantic boundary (fail-fast)."""
    import urllib.request

    def _boom(*args, **kwargs):
        raise RuntimeError("live provider/network boundary touched")

    with (
        patch.object(SerperSearchProvider, "search", side_effect=_boom),
        patch.object(HttpPageFetcher, "fetch", side_effect=_boom),
        patch.object(InternalVendorAdapter, "lookup", side_effect=_boom),
        patch.object(EcbFxProvider, "__init__", side_effect=_boom),
        patch.object(EcbFxProvider, "fetch_rates", side_effect=_boom),
        patch.object(SemanticRuntime, "evaluate", side_effect=_boom),
        patch.object(
            semantic_integration,
            "evaluate_semantic_matches",
            side_effect=_boom,
        ),
        patch("urllib.request.urlopen", side_effect=_boom),
        patch("urllib.request.OpenerDirector.open", side_effect=_boom),
    ):
        yield


def _assert_armed_boundaries_raise() -> None:
    import urllib.request

    for touch in (
        lambda: urllib.request.urlopen("http://127.0.0.1/"),
        lambda: EcbFxProvider.__init__(None),
        lambda: EcbFxProvider.fetch_rates(None),
        lambda: InternalVendorAdapter.lookup(None),
        lambda: SerperSearchProvider.search(None),
        lambda: HttpPageFetcher.fetch(None),
        lambda: SemanticRuntime.evaluate(None),
        lambda: semantic_integration.evaluate_semantic_matches(),
    ):
        try:
            touch()
        except RuntimeError as exc:
            assert "live provider/network" in str(exc)
        else:  # pragma: no cover - sentinel must raise
            raise AssertionError("armed sentinel did not raise")


class TestMicronAliasReport(TestCase):
    def _get(self, run: ResearchRun) -> "object":
        url = reverse("research-detail", kwargs={"run_id": run.id})
        return Client().get(url)

    def test_established_audit_renders_in_own_section(self) -> None:
        run = _make_run(alias_payload=_established_payload())
        response = self._get(run)
        self.assertEqual(response.status_code, 200)
        html = response.content.decode("utf-8")
        section = _section(html, "Micron packaging alias evidence")
        self.assertTrue(section, "alias section missing")
        # ESTABLISHED audit projection
        self.assertIn("ESTABLISHED", section)
        self.assertIn(
            "established from the reviewed Micron 7500 SSD family catalog",
            section,
        )
        # Source-published BASE retained and rendered
        self.assertIn(f"<code>{BASE}</code>", section)
        # Manufacturer Micron + category SSD
        self.assertIn("Micron", section)
        self.assertIn(">SSD<", section.replace("<code>", ">").replace("</code>", "<"))
        # Customer-rule distinction (no official-semantics claim)
        self.assertIn(
            "Customer-defined retrieval relation (retrieval recall only).",
            section,
        )
        self.assertIn("Not manufacturer-published packaging identity.", section)
        self.assertNotIn("officially", section.lower())
        # Alias exclusion references in their own section, with the
        # exact reference wording.
        self.assertIn(
            "Customer-defined packaging alias reference — excluded from "
            "pricing authority",
            section,
        )
        self.assertIn(SIBLING_URL, section)

    def test_alias_references_absent_from_other_authority_sections(self) -> None:
        run = _make_run(alias_payload=_established_payload())
        html = self._get(run).content.decode("utf-8")
        # Exactly two legitimate locations: the alias reference section
        # and the frozen 4A "Excluded listings" display. Each renders an
        # <a href="URL">URL</a> link, so the URL string appears twice per
        # location.
        self.assertEqual(html.count(SIBLING_URL), 4)
        for heading in (
            "Quote & Market Summary",
            "Reviewed price",
            "Comparable products",
        ):
            self.assertNotIn(
                SIBLING_URL, _section(html, heading),
                f"alias reference leaked into {heading!r}",
            )
        # Machine Price: the rendered comparable price group (bucket
        # member) rows show the accepted source only, never the sibling.
        price_section = _section(html, "Price intelligence")
        self.assertIn("Comparable price group", price_section)
        group_start = price_section.find("<h3>Comparable price group</h3>")
        group = price_section[group_start: price_section.find("</div>", group_start)]
        self.assertNotIn(SIBLING_URL, group)
        self.assertIn(ACCEPTED_URL, group)

    def test_no_snapshot_no_alias_section(self) -> None:
        run = _make_run(alias_payload=None)
        html = self._get(run).content.decode("utf-8")
        self.assertEqual(html.count("<h2>Micron packaging alias evidence</h2>"), 0)
        # Main report still renders.
        self.assertIn("<h2>Price intelligence</h2>", html)

    def test_bounded_non_established_no_reference_authority(self) -> None:
        mpn = "NOT-IN-CATALOG"
        payload = encode_micron_alias_snapshot(_acquire_for(mpn))
        run = _make_run(mpn=mpn, alias_payload=payload)
        html = self._get(run).content.decode("utf-8")
        section = _section(html, "Micron packaging alias evidence")
        self.assertTrue(section)
        self.assertIn("NO_AUTHORITY_MATCH", section)
        self.assertIn(
            "bounded non-established result; no alias-expanded retrieval "
            "was used",
            section,
        )
        # No reference table, no reference rows, no relation claim.
        self.assertNotIn(
            "Customer-defined packaging alias reference", section
        )
        self.assertNotIn(SIBLING_URL, section)
        self.assertNotIn("<code>MTFDKCC3T8TGP-1BK1DABYY</code>", section)

    def test_malformed_snapshot_bounded_unavailable_main_report_renders(self) -> None:
        run = _make_run(alias_payload={"garbage": True})
        response = self._get(run)
        self.assertEqual(response.status_code, 200)
        html = response.content.decode("utf-8")
        section = _section(html, "Micron packaging alias evidence")
        self.assertIn("Micron alias evidence unavailable.", section)
        # No partial alias rows; main report intact.
        self.assertNotIn("ESTABLISHED", section)
        self.assertIn("<h2>Price intelligence</h2>", html)
        self.assertIn("Comparable price group", html)

    def test_version_mismatch_snapshot_bounded_unavailable(self) -> None:
        run = _make_run(
            alias_payload=_established_payload(), alias_version=2
        )
        html = self._get(run).content.decode("utf-8")
        section = _section(html, "Micron packaging alias evidence")
        self.assertIn("Micron alias evidence unavailable.", section)

    def test_tampered_payload_bounded_unavailable(self) -> None:
        payload = _established_payload()
        payload["matched_base_mpn"] = None  # ESTABLISHED without a base
        run = _make_run(alias_payload=payload)
        html = self._get(run).content.decode("utf-8")
        section = _section(html, "Micron packaging alias evidence")
        self.assertIn("Micron alias evidence unavailable.", section)
        self.assertNotIn(f"<code>{BASE}</code>", section)

    def test_request_run_provenance_mismatch_fails_closed(self) -> None:
        # Persisted audit binds the BASE request; the run requests BASER.
        run = _make_run(alias_payload=_established_payload(mpn=BASE))
        html = self._get(run).content.decode("utf-8")
        section = _section(html, "Micron packaging alias evidence")
        self.assertIn("Micron alias evidence unavailable.", section)
        self.assertNotIn("ESTABLISHED", section)

    def test_programming_runtime_error_propagates(self) -> None:
        run = _make_run(alias_payload=_established_payload())
        with patch(
            "product_intelligence.web.views.decode_micron_alias_snapshot",
            side_effect=RuntimeError("programming defect"),
        ):
            with self.assertRaises(RuntimeError):
                self._get(run)

    def test_historical_get_performs_zero_live_work(self) -> None:
        run = _make_run(alias_payload=_established_payload())
        with _armed_live_boundaries():
            _assert_armed_boundaries_raise()
            response = self._get(run)
        self.assertEqual(response.status_code, 200)
        html = response.content.decode("utf-8")
        self.assertIn("ESTABLISHED", _section(html, "Micron packaging alias evidence"))
