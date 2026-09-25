"""End-to-end acceptance tests for the compact quote browser rendering
(PRODUCT-INTEL.4D-C).

These tests exercise the real ``GET /research/<uuid>`` route through
Django's test client with persisted artifacts:

* real PriceIntelligenceSnapshot (public bucket-member rows)
* real ResearchSupplementSnapshot (vendor commercial rows, sentinel price)
* persisted ResearchFxSnapshot (USD-equivalent display)

Hard acceptance criteria proven here:

1. DENIED path must not touch the supplemental artifact access path
   (armed RuntimeError fail-fast on the exact lookup/decode/replay paths)
   while still returning 200 with public compact rows.
2. ALLOWED path renders vendor + public rows (vendor first) with exact
   display labels, original prices, persisted-FX USD equivalents,
   inventory, brand new, and bounded notes — with zero live provider,
   network, or semantic work (armed fail-fast).
3. DENIED path renders public rows only; vendor rows are ABSENT from the
   template context (the security boolean is never the row-hiding
   mechanism) and no vendor data leaks into the HTML.
4. Public source links: safe full URL as link target, "www."-stripped
   hostname as display text; unsafe schemes never become hrefs.
5. Fail-closed error behavior: malformed supplemental or FX artifacts ->
   "Quote & Market Summary unavailable." (no partial compact table);
   programming errors propagate (never converted to "unavailable");
   a malformed supplemental payload is irrelevant on the denied path.
6. No-data states: zero rows -> "No compact quote evidence is
   available."; no price snapshot -> no compact section (existing report
   error behavior preserved).
"""

from __future__ import annotations

from contextlib import contextmanager
from datetime import date, datetime, timezone
from decimal import Decimal
from html.parser import HTMLParser
from unittest.mock import patch

import pytest
from django.test import Client
from django.urls import reverse

from product_intelligence.domain import ResearchRequest
from product_intelligence.domain.enums import (
    ConfidenceLevel,
    EvidenceDecision,
    IdentityMatchType,
    VerificationStatus,
)
from product_intelligence.providers.fx import EcbFxProvider, FxRateObservation
from product_intelligence.providers.http_page import HttpPageFetcher
from product_intelligence.providers.internal_vendor import InternalVendorAdapter
from product_intelligence.providers.serper import SerperSearchProvider
from product_intelligence.research import (
    ListingIdentityAssessment,
    ListingObservation,
    PriceAggregateBucket,
    PriceAggregationResult,
    encode_price_aggregation_result,
)
from product_intelligence.research.commercial_supplement_codec import (
    ResearchSupplementResult,
    SupplementAvailability,
    SupplementLookupStatus,
    SupplementPriceBasis,
    SupplementSourceObservation,
    VendorCommercialResult,
    encode_research_supplement_result,
)
from product_intelligence.research.fx_codec import encode_fx_observation
from product_intelligence.research.listings import ExtractionMethod
from product_intelligence.research.matching import EvidenceSource
from product_intelligence.research.normalization import (
    NormalizedAvailability,
    NormalizedCondition,
    NormalizedListingObservation,
)
from product_intelligence.runs.models import (
    PriceIntelligenceSnapshot,
    ResearchFxSnapshot,
    ResearchRun,
    ResearchSupplementSnapshot,
)
from product_intelligence.semantic.runtime import SemanticRuntime
from product_intelligence.execution import semantic_integration


ALLOWED_CIDRS = "10.0.0.0/8"
ALLOWED_ADDR = "10.0.0.1"
DENIED_ADDR = "192.0.2.1"  # TEST-NET-1 (RFC 5737) — never assigned

SENTINEL_VENDOR_PRICE = "91827.43"

PUBLIC_SOURCE_URL = "https://www.example.com/product/abc"
PUBLIC_PRICE = Decimal("1500.00")
USD_RATE = Decimal("1.0934")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _mock_settings(cidrs: "str | None" = ALLOWED_CIDRS):
    return type("Settings", (), {"PI_VENDOR_PRICE_ALLOWED_CIDRS": cidrs})()


def _public_result(
    run: ResearchRun,
    *,
    source_url: str = PUBLIC_SOURCE_URL,
    price: Decimal = PUBLIC_PRICE,
    currency: str = "EUR",
) -> PriceAggregationResult:
    mpn = run.manufacturer_part_number or "CQ-MPN"
    obs = ListingObservation(
        source_url=source_url,
        extraction_method=ExtractionMethod.JSON_LD,
        product_title="Compact Quote Test Product",
        manufacturer_part_number_text=mpn,
        sku_text=None,
        brand_text=None,
        price_text=str(price),
        currency_text=currency,
        availability_text="In Stock",
        condition_text="New",
        seller_text="Example Store",
        offer_url_text=None,
        raw_reference=None,
    )
    norm = NormalizedListingObservation(
        observation=obs,
        price_amount=price,
        currency_code=currency,
        availability=NormalizedAvailability.IN_STOCK,
        condition=NormalizedCondition.NEW,
        seller_name="Example Store",
        normalization_issues=(),
    )
    assess = ListingIdentityAssessment(
        normalized_listing=norm,
        requested_part_number=mpn,
        candidate_part_number_raw=mpn,
        candidate_part_number_compared=mpn,
        candidate_evidence_source=EvidenceSource.EXPLICIT_MPN_FIELD,
        match_type=IdentityMatchType.EXACT,
        decision=EvidenceDecision.ACCEPTED,
        rejection_reason=None,
    )
    return PriceAggregationResult(
        request=run.to_research_request(),
        assessments=(assess,),
        exclusions=(),
        buckets=(
            PriceAggregateBucket(
                currency_code=currency,
                condition=NormalizedCondition.NEW,
                assessments=(assess,),
                count=1,
                low=price,
                median=price,
                high=price,
                market_range_low=None,
                market_range_high=None,
                confidence=ConfidenceLevel.LOW,
            ),
        ),
        verification_status=VerificationStatus.VERIFIED,
    )


def _unknown_result(run: ResearchRun) -> PriceAggregationResult:
    mpn = run.manufacturer_part_number or "CQ-MPN"
    obs = ListingObservation(
        source_url="https://example.com/wrong",
        extraction_method=ExtractionMethod.JSON_LD,
        product_title="Different Product",
        manufacturer_part_number_text="WRONG-MPN",
        sku_text=None,
        brand_text=None,
        price_text="$50.00",
        currency_text="USD",
        availability_text="In Stock",
        condition_text="New",
        seller_text=None,
        offer_url_text=None,
        raw_reference=None,
    )
    norm = NormalizedListingObservation(
        observation=obs,
        price_amount=Decimal("50.00"),
        currency_code="USD",
        availability=NormalizedAvailability.IN_STOCK,
        condition=NormalizedCondition.NEW,
        seller_name=None,
        normalization_issues=(),
    )
    from product_intelligence.research.aggregation import (
        PriceAggregationExclusion,
        PriceAggregationExclusionReason,
    )
    from product_intelligence.research.matching import IdentityRejectionReason

    assess = ListingIdentityAssessment(
        normalized_listing=norm,
        requested_part_number=mpn,
        candidate_part_number_raw="WRONG-MPN",
        candidate_part_number_compared="WRONG-MPN",
        candidate_evidence_source=EvidenceSource.EXPLICIT_MPN_FIELD,
        match_type=IdentityMatchType.UNKNOWN,
        decision=EvidenceDecision.REJECTED,
        rejection_reason=IdentityRejectionReason.MPN_MISMATCH,
    )
    return PriceAggregationResult(
        request=run.to_research_request(),
        assessments=(assess,),
        exclusions=(
            PriceAggregationExclusion(
                assessment=assess,
                reason=PriceAggregationExclusionReason.IDENTITY_NOT_ACCEPTED,
            ),
        ),
        buckets=(),
        verification_status=VerificationStatus.UNKNOWN,
    )


def _persist_price_snapshot(run: ResearchRun, result: PriceAggregationResult) -> None:
    PriceIntelligenceSnapshot.objects.create(
        run=run,
        schema_version=1,
        payload=encode_price_aggregation_result(result),
    )


def _persist_fx(run: ResearchRun) -> None:
    payload = encode_fx_observation(
        provider_id="ECB",
        observation_date=date(2024, 1, 15),
        base_currency="EUR",
        rates=(
            FxRateObservation(currency_code="USD", rate=USD_RATE),
            FxRateObservation(currency_code="EUR", rate=Decimal("1.0")),
        ),
        retrieved_at=datetime(2024, 1, 15, 12, 0, 0, tzinfo=timezone.utc),
    )
    ResearchFxSnapshot.objects.create(run=run, schema_version=1, payload=payload)


def _vendor_observation(
    run: ResearchRun,
    *,
    source_name: str,
    price: Decimal,
    currency: str,
    availability: str = "IN_STOCK",
    note_kind: "str | None" = None,
) -> SupplementSourceObservation:
    return SupplementSourceObservation(
        source_name=source_name,
        explicit_candidate_mpn=run.manufacturer_part_number or "CQ-MPN",
        vendor_mpn_match_type="EXACT",
        price_amount=price,
        currency_code=currency,
        availability=availability,
        price_basis=SupplementPriceBasis.CUSTOMER_PRICE,
        quantity=1,
        note_kind=note_kind,
        brand_new=True,
        brand_new_basis="VENDOR_API_POLICY",
    )


def _persist_supplement(
    run: ResearchRun, observations: tuple[SupplementSourceObservation, ...]
) -> None:
    result = ResearchSupplementResult(
        vendor_commercial_result=VendorCommercialResult(
            lookup_status=SupplementLookupStatus.SUCCESS,
            retrieved_at=datetime(2025, 1, 15, 12, 0, 0, tzinfo=timezone.utc),
            observations=observations,
            source_issues=(),
        ),
    )
    ResearchSupplementSnapshot.objects.create(
        run=run,
        schema_version=1,
        payload=encode_research_supplement_result(result),
    )


def _create_quote_run(
    mpn: str = "CQ-REPORT-MPN",
    *,
    with_supplement: bool = True,
    vendor_observations: "tuple | None" = None,
    malformed_supplement: bool = False,
    malformed_fx: bool = False,
    unknown: bool = False,
) -> ResearchRun:
    run = ResearchRun.objects.create_from_request(
        ResearchRequest(manufacturer_part_number=mpn, description="Compact quote report")
    )
    _persist_price_snapshot(
        run, _unknown_result(run) if unknown else _public_result(run)
    )
    if not malformed_fx:
        _persist_fx(run)
    if malformed_fx:
        ResearchFxSnapshot.objects.create(
            run=run, schema_version=1, payload={"garbage": True}
        )
    if with_supplement:
        if malformed_supplement:
            ResearchSupplementSnapshot.objects.create(
                run=run, schema_version=1, payload={"garbage": True}
            )
        else:
            if vendor_observations is None:
                vendor_observations = (
                    _vendor_observation(
                        run,
                        source_name="Ingram",
                        price=Decimal("2023.27"),
                        currency="USD",
                    ),
                    _vendor_observation(
                        run,
                        source_name="CDW",
                        price=Decimal("1999.99"),
                        currency="USD",
                        availability="OUT_OF_STOCK",
                    ),
                    _vendor_observation(
                        run,
                        source_name="Synnex EU",
                        price=Decimal("1705.35"),
                        currency="EUR",
                        note_kind="NO_RETURNS",
                    ),
                )
            _persist_supplement(run, vendor_observations)
    return run


def _detail_url(run: ResearchRun) -> str:
    return reverse("research-detail", kwargs={"run_id": run.id})


def _get(client: Client, url: str, remote_addr: str) -> "object":
    return client.get(url, REMOTE_ADDR=remote_addr)


@contextmanager
def _armed_live_boundaries():
    """Arm every live provider/network/semantic boundary (FU1 fail-fast)."""
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
    """Non-vacuity proof: the armed sentinels really do raise."""
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
        with pytest.raises(RuntimeError, match="live provider/network"):
            touch()


class _CompactTableRowParser(HTMLParser):
    """Extract the cell texts of every <tr> in the compact quote table.

    Scopes rendering assertions to the actual table rows/cells of the
    rendered "Quote & Market Summary" section — never to the whole page
    (unrelated sections may legitimately contain other text).
    """

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
            self._current_row.append(self._cell_text.strip())

    def handle_data(self, data) -> None:
        if self.in_cell:
            self._cell_text += data


def _compact_table_rows(html: str) -> list[list[str]]:
    """Parse the cell texts of the rendered compact quote table.

    Only the section between the "Quote & Market Summary" heading and the
    next top-level "Price intelligence" heading is parsed, so the
    assertions are narrowly scoped to the compact table rows/cells.
    """
    section_start = html.index("<h2>Quote & Market Summary</h2>")
    section_end = html.index("<h2>Price intelligence</h2>")
    section = html[section_start:section_end]
    assert '<table class="spec-table">' in section
    parser = _CompactTableRowParser()
    parser.feed(section)
    assert parser.rows, "compact quote table rows not found"
    return parser.rows


@contextmanager
def _armed_supplement_boundaries():
    """Arm the exact supplemental artifact access path used by the
    authorized replay. If the denied route reads
    ResearchSupplementSnapshot, calls decode_research_supplement_result,
    or calls replay_compact_quote_projection, this raises RuntimeError."""

    def _boom(*args, **kwargs):
        raise RuntimeError(
            "denied path touched vendor supplemental artifact access"
        )

    with (
        patch.object(
            ResearchSupplementSnapshot.objects, "get", side_effect=_boom
        ),
        patch.object(
            ResearchSupplementSnapshot.objects, "filter", side_effect=_boom
        ),
        patch(
            "product_intelligence.research.commercial_supplement_codec"
            ".decode_research_supplement_result",
            side_effect=_boom,
        ),
        patch(
            "product_intelligence.web.views.replay_compact_quote_projection",
            side_effect=_boom,
        ),
    ):
        yield


def _compact_rows(response) -> list:
    """The display rows actually placed in the template context."""
    compact = response.context["compact_quote"]
    assert compact is not None
    return list(compact.rows)


# ---------------------------------------------------------------------------
# Authorized vendor table
# ---------------------------------------------------------------------------


class TestAuthorizedVendorTable:
    def test_vendor_and_public_rows_render_authorized(self) -> None:
        """ALLOWED REMOTE_ADDR: vendor rows + public rows render, vendor
        first, with exact display labels, original prices, persisted-FX
        USD equivalents, inventory, brand new, bounded note — and zero
        live provider/network/semantic work."""
        run = _create_quote_run()
        url = _detail_url(run)

        with (
            patch(
                "product_intelligence.web.commercial_access._django_settings",
                _mock_settings(),
            ),
            _armed_live_boundaries(),
        ):
            _assert_armed_boundaries_raise()
            client = Client()
            response = _get(client, url, ALLOWED_ADDR)

        assert response.status_code == 200
        html = response.content.decode()

        # --- Context: exact row order (vendor first, then public) ---
        rows = _compact_rows(response)
        assert [r.source_display for r in rows] == [
            "Ingram (Vendor API)",
            "CDW (Vendor API)",
            "Synnex EU (Vendor API)",
            "example.com",
        ]

        # --- Ingram: USD original preserved, pass-through equivalent ---
        ingram = rows[0]
        assert ingram.price == "$2,023.27 USD"
        assert ingram.usd_equivalent == "$2,023.27 USD"
        assert ingram.inventory == "In Stock"
        assert ingram.brand_new == "Yes"
        assert ingram.note is None
        assert ingram.source_url is None  # vendor rows never receive a URL
        assert ingram.source_url_safe is False

        # --- CDW: out of stock rendered ---
        cdw = rows[1]
        assert cdw.price == "$1,999.99 USD"
        assert cdw.usd_equivalent == "$1,999.99 USD"
        assert cdw.inventory == "Out of Stock"
        assert cdw.brand_new == "Yes"
        assert cdw.source_url is None

        # --- Synnex EU: EUR original preserved, persisted-FX equivalent ---
        synnex = rows[2]
        assert synnex.price == "€1,705.35 EUR"
        assert synnex.usd_equivalent == "$1,864.629690 USD"
        assert synnex.inventory == "In Stock"
        assert synnex.brand_new == "Yes"
        assert synnex.note == "NO_RETURNS"
        assert synnex.source_url is None

        # --- Public row: hostname display + full safe URL link target ---
        pub = rows[3]
        assert pub.source_display == "example.com"
        assert pub.source_url == PUBLIC_SOURCE_URL
        assert pub.source_url_safe is True
        assert pub.price == "€1,500.00 EUR"
        assert pub.usd_equivalent == "$1,640.100000 USD"
        assert pub.inventory == "In Stock"
        assert pub.brand_new == "Yes"

        # --- HTML: table rendered near the top, vendor rows before public ---
        compact_start = html.index("Quote & Market Summary")
        price_section_start = html.index("Price intelligence")
        assert compact_start < price_section_start
        assert html.index("Ingram (Vendor API)") < html.index("example.com</a>")
        assert 'href="https://www.example.com/product/abc">example.com</a>' in html
        assert "$2,023.27 USD" in html
        assert "€1,705.35 EUR" in html
        assert "€1,500.00 EUR" in html
        assert "1,864.629690" in html
        assert "1,640.10" in html
        assert "In Stock" in html
        assert "Out of Stock" in html
        assert "NO_RETURNS" in html

        # --- Exact-once vendor labels, no double suffix ---
        assert html.count("Ingram (Vendor API)") == 1
        assert html.count("CDW (Vendor API)") == 1
        assert html.count("Synnex EU (Vendor API)") == 1
        assert "(Vendor API) (Vendor API)" not in html

        # --- Unified business summary ---
        assert "Quote & Market Summary" in html
        assert "<dt>Quotes found</dt>" in html
        assert "<dd>4</dd>" in html
        assert "Lowest in-stock quote" in html
        assert "Comparable public market" in html
        assert "fewer than 3 comparable NEW listings" in html
        # Primary summary does not expose a two-observation/one-observation median.
        primary = html.split("Quote & Market Summary", 1)[1].split(
            "Advanced Evidence & Audit", 1
        )[0]
        assert "<strong>Median:</strong> €1,500.00 EUR" not in primary

        # --- No raw payload / no sensitive metadata in HTML ---
        for forbidden in (
            "SessionId",
            "BuyerAccountId",
            "SystemId",
            "vendor_commercial_result",
            "lookup_status",
            "price_basis",
            "VENDOR_API_POLICY",
            "CUSTOMER_PRICE",
            "LIST_PRICE",
            "explicit_candidate_mpn",
        ):
            assert forbidden not in html

        # --- Existing detailed report sections remain ---
        assert "Price aggregation status:" in html
        assert "VERIFIED" in html
        assert "Median" in html

    def test_authorized_context_contains_vendor_rows(self) -> None:
        run = _create_quote_run()
        url = _detail_url(run)
        with patch(
            "product_intelligence.web.commercial_access._django_settings",
            _mock_settings(),
        ):
            response = _get(Client(), url, ALLOWED_ADDR)
        assert response.status_code == 200
        assert response.context["vendor_commercial_access_allowed"] is True
        rows = _compact_rows(response)
        assert any("(Vendor API)" in r.source_display for r in rows)


# ---------------------------------------------------------------------------
# FU1: NOTE NONE must render BLANK (never the literal text "None")
# ---------------------------------------------------------------------------


class TestNoteCellNoneRendersBlank:
    def test_none_note_cell_blank_real_note_still_renders(self) -> None:
        """End-to-end through the real GET /research/<uuid> with an
        authorized REMOTE_ADDR.

        The persisted run carries (default fixture):
        * an Ingram Vendor row with note=None
        * a CDW Vendor row with note=None (OUT_OF_STOCK display note is
          None because availability maps cleanly)
        * a Synnex EU Vendor row with the real bounded note NO_RETURNS
        * one public row

        Proves, in the rendered unified quote table (parsed row/cell,
        narrowly scoped):
        1. missing notes never render the literal text "None"
        2. the Synnex bounded NO_RETURNS note still renders under Market Use
        3. no Vendor/security behavior changes (context rows and labels
           remain provider-safe)
        """
        run = _create_quote_run(mpn="NOTE-NONE-FU1-MPN")
        url = _detail_url(run)
        with patch(
            "product_intelligence.web.commercial_access._django_settings",
            _mock_settings(),
        ):
            response = _get(Client(), url, ALLOWED_ADDR)

        assert response.status_code == 200
        html = response.content.decode()

        # --- Frozen CompactQuoteRow semantics unchanged in context ---
        rows = _compact_rows(response)
        assert [r.source_display for r in rows] == [
            "Ingram (Vendor API)",
            "CDW (Vendor API)",
            "Synnex EU (Vendor API)",
            "example.com",
        ]
        assert rows[0].note is None          # Ingram: real Python None
        assert rows[1].note is None          # CDW: real Python None
        assert rows[2].note == "NO_RETURNS"  # Synnex EU: real bounded note

        # --- Parse the actually rendered compact quote table ---
        table_rows = _compact_table_rows(html)
        # First row is the unified business-facing quote table header.
        assert table_rows[0] == [
            "Source", "Price", "USD Equivalent", "Availability",
            "Condition", "Match / Evidence", "Market Use", "Actions",
        ]
        data_rows = table_rows[1:]
        assert [r[0] for r in data_rows] == [
            "Ingram (Vendor API)",
            "CDW (Vendor API)",
            "Synnex EU (Vendor API)",
            "example.com",
        ]

        # 1 + 2. Ingram row: the Note cell (last column) is EMPTY and the
        # literal text "None" does not appear in it.
        ingram_row = data_rows[0]
        assert len(ingram_row) == 8
        assert ingram_row[6].startswith("Quote only — Vendor supplemental")
        assert "None" not in ingram_row[6]

        # CDW row: also a real None note -> also blank
        assert "None" not in data_rows[1][6]

        # The literal "None" does not appear anywhere in the compact
        # quote table section (narrowly scoped, not whole page).
        section_start = html.index("<h2>Quote & Market Summary</h2>")
        section_end = html.index("<h2>Price intelligence</h2>")
        assert "None" not in html[section_start:section_end]

        # 3. Synnex real bounded note still renders in its Note cell
        synnex_row = data_rows[2]
        assert len(synnex_row) == 8
        assert "NO_RETURNS" in synnex_row[6]

        # 4. No Vendor/security behavior changes: remaining columns of
        # the vendor rows render exactly as the frozen display contract.
        assert ingram_row[1] == "$2,023.27 USD"
        assert ingram_row[2] == "$2,023.27 USD"
        assert ingram_row[3] == "In Stock"
        assert ingram_row[4] == "New"
        assert synnex_row[1] == "\u20ac1,705.35 EUR"
        assert synnex_row[2] == "$1,864.629690 USD"
        assert data_rows[3][1] == "\u20ac1,500.00 EUR"
        assert "(Vendor API) (Vendor API)" not in html
        assert html.count("Ingram (Vendor API)") == 1
        assert html.count("CDW (Vendor API)") == 1
        assert html.count("Synnex EU (Vendor API)") == 1


# ---------------------------------------------------------------------------
# CRITICAL: denied path must not touch the supplemental artifact access
# ---------------------------------------------------------------------------


class TestDeniedPathNeverTouchesSupplement:
    def test_denied_get_returns_200_public_rows_supplement_armed(self) -> None:
        """Hard acceptance criterion.

        The run carries a real ResearchSupplementSnapshot with the
        recognizable sentinel vendor price 91827.43. The exact lookup/
        decode/replay paths used by the authorized replay are armed with
        RuntimeError. The denied GET must still return 200 and display
        public compact rows — proving the security decision occurs
        BEFORE any vendor commercial artifact access.
        """
        run = ResearchRun.objects.create_from_request(
            ResearchRequest(
                manufacturer_part_number="DENIED-SENTINEL-MPN",
                description="Compact quote report",
            )
        )
        _persist_price_snapshot(run, _public_result(run))
        _persist_fx(run)
        _persist_supplement(
            run,
            (
                _vendor_observation(
                    run,
                    source_name="Ingram",
                    price=Decimal(SENTINEL_VENDOR_PRICE),
                    currency="USD",
                ),
            ),
        )
        url = _detail_url(run)

        with (
            patch(
                "product_intelligence.web.commercial_access._django_settings",
                _mock_settings(),
            ),
            _armed_supplement_boundaries(),
            _armed_live_boundaries(),
        ):
            _assert_armed_boundaries_raise()
            client = Client()
            response = _get(client, url, DENIED_ADDR)

        assert response.status_code == 200
        html = response.content.decode()
        assert response.context["vendor_commercial_access_allowed"] is False

        # Public compact row rendered
        rows = _compact_rows(response)
        assert [r.source_display for r in rows] == ["example.com"]
        assert rows[0].price == "€1,500.00 EUR"
        assert rows[0].source_url == PUBLIC_SOURCE_URL
        assert rows[0].source_url_safe is True

        # Sentinel vendor price absent in BOTH raw and formatted form
        assert SENTINEL_VENDOR_PRICE not in html
        assert "91,827.43" not in html

        # Vendor source labels absent
        assert "Ingram" not in html
        assert "CDW" not in html
        assert "Synnex" not in html
        assert "(Vendor API)" not in html

        # Neutral access-denied notice present
        assert (
            "Internal commercial pricing is unavailable for this connection."
            in html
        )

        # Existing detailed public report still renders
        assert "Price aggregation status:" in html
        assert "VERIFIED" in html
        assert "Median" in html
        assert "Quote & Market Summary unavailable." not in html


# ---------------------------------------------------------------------------
# Denied public table
# ---------------------------------------------------------------------------


class TestDeniedPublicTable:
    def test_denied_public_row_present_vendor_rows_absent(self) -> None:
        run = _create_quote_run(mpn="DENIED-TABLE-MPN")
        url = _detail_url(run)
        with patch(
            "product_intelligence.web.commercial_access._django_settings",
            _mock_settings(),
        ), _armed_supplement_boundaries():
            response = _get(Client(), url, DENIED_ADDR)

        assert response.status_code == 200
        html = response.content.decode()

        # Public compact row present
        rows = _compact_rows(response)
        assert [r.source_display for r in rows] == ["example.com"]
        assert "€1,500.00 EUR" in html
        assert 'href="https://www.example.com/product/abc">example.com</a>' in html

        # Vendor rows absent from context AND HTML
        assert all("(Vendor API)" not in r.source_display for r in rows)
        assert all(r.source_url is None or r.source_url == PUBLIC_SOURCE_URL for r in rows)
        for forbidden in (
            "Ingram (Vendor API)",
            "CDW (Vendor API)",
            "Synnex EU (Vendor API)",
            "$2,023.27 USD",
            "$1,999.99 USD",
            "€1,705.35 EUR",
        ):
            assert forbidden not in html

        # Detailed public report renders normally
        assert "Price aggregation status:" in html
        assert "Median" in html

    def test_denied_security_boolean_is_not_row_hiding_mechanism(self) -> None:
        """The DENIED template context contains no vendor display rows at
        all — the boolean may remain for neutral messaging but is not the
        thing preventing vendor data from reaching the template."""
        run = _create_quote_run(mpn="DENIED-CTX-MPN")
        url = _detail_url(run)
        with patch(
            "product_intelligence.web.commercial_access._django_settings",
            _mock_settings(),
        ):
            response = _get(Client(), url, DENIED_ADDR)

        assert response.status_code == 200
        assert response.context["vendor_commercial_access_allowed"] is False
        rows = _compact_rows(response)
        # Context rows are public-only: every row is linked or plain
        # public display; zero vendor display rows exist in the context.
        for row in rows:
            assert "(Vendor API)" not in row.source_display
            assert row.price in ("€1,500.00 EUR",)


# ---------------------------------------------------------------------------
# Public source links
# ---------------------------------------------------------------------------


class TestPublicSourceLinks:
    def test_safe_public_url_hostname_display_and_link_target(self) -> None:
        run = _create_quote_run(mpn="LINK-MPN")
        url = _detail_url(run)
        with patch(
            "product_intelligence.web.commercial_access._django_settings",
            _mock_settings(),
        ):
            response = _get(Client(), url, ALLOWED_ADDR)

        assert response.status_code == 200
        html = response.content.decode()
        # Display: www.-stripped hostname; target: the full safe URL
        assert 'href="https://www.example.com/product/abc">example.com</a>' in html

    def test_unsafe_schemes_never_become_href(self) -> None:
        for bad_url in (
            "javascript:alert(1)",
            "data:text/html;base64,PHNjcmlwdD4=",
            "file:///etc/passwd",
        ):
            run = _create_quote_run(
                mpn=f"UNSAFE-{bad_url[:8].replace(':', '')}",
            )
            # Re-persist the price snapshot with the unsafe public URL
            PriceIntelligenceSnapshot.objects.filter(run=run).delete()
            _persist_price_snapshot(run, _public_result(run, source_url=bad_url))
            detail = _detail_url(run)
            with patch(
                "product_intelligence.web.commercial_access._django_settings",
                _mock_settings(),
            ):
                response = _get(Client(), detail, DENIED_ADDR)
            assert response.status_code == 200
            html = response.content.decode()
            assert f'href="{bad_url}"' not in html
            assert "href='javascript:" not in html
            assert "href=\"javascript:" not in html
            assert "href=\"data:" not in html
            assert "href=\"file:" not in html
            # The unsafe source renders as plain text (no link)
            assert "Unknown Source" in html


# ---------------------------------------------------------------------------
# No-data behavior
# ---------------------------------------------------------------------------


class TestNoDataBehavior:
    def test_no_buckets_shows_neutral_state(self) -> None:
        run = _create_quote_run(
            mpn="NO-BUCKETS-MPN", unknown=True, with_supplement=False
        )
        url = _detail_url(run)
        with patch(
            "product_intelligence.web.commercial_access._django_settings",
            _mock_settings(),
        ):
            for addr in (ALLOWED_ADDR, DENIED_ADDR):
                response = _get(Client(), url, addr)
                assert response.status_code == 200
                html = response.content.decode()
                assert "Quote & Market Summary" in html
                assert "No quote evidence is available." in html
                # No empty misleading table
                assert "USD Equivalent" not in html

    def test_no_price_snapshot_no_compact_section(self) -> None:
        run = ResearchRun.objects.create_from_request(
            ResearchRequest(
                manufacturer_part_number="NO-SNAP-MPN", description="x"
            )
        )
        url = _detail_url(run)
        with patch(
            "product_intelligence.web.commercial_access._django_settings",
            _mock_settings(),
        ):
            response = _get(Client(), url, ALLOWED_ADDR)
        assert response.status_code == 200
        html = response.content.decode()
        # Existing report behavior preserved; no compact table rendered
        assert "No research result available." in html
        assert "Quote & Market Summary" not in html


# ---------------------------------------------------------------------------
# Error behavior
# ---------------------------------------------------------------------------


class TestErrorBehavior:
    def test_authorized_malformed_supplement_unavailable_no_partial(self) -> None:
        run = _create_quote_run(
            mpn="ERR-SUPP-MPN", malformed_supplement=True
        )
        url = _detail_url(run)
        with patch(
            "product_intelligence.web.commercial_access._django_settings",
            _mock_settings(),
        ):
            response = _get(Client(), url, ALLOWED_ADDR)

        assert response.status_code == 200
        html = response.content.decode()
        # Compact summary unavailable — no partial compact table
        assert "Quote & Market Summary unavailable." in html
        assert "USD Equivalent" not in html
        assert "€1,500.00 EUR" not in html.split("Quote & Market Summary")[-1].split("Price intelligence")[0]
        # Detailed existing report still renders
        assert "Price aggregation status:" in html
        assert "Median" in html
        # No sensitive payload / error text in HTML
        for forbidden in (
            "SupplementCodecError",
            "garbage",
            "unexpected top-level keys",
            "Traceback",
        ):
            assert forbidden not in html

    def test_denied_malformed_supplement_is_irrelevant(self) -> None:
        """On the denied path supplemental data is never accessed, so a
        malformed supplemental payload cannot affect the public compact
        summary — it renders from valid public + FX evidence."""
        run = _create_quote_run(
            mpn="ERR-DENIED-SUPP-MPN", malformed_supplement=True
        )
        url = _detail_url(run)
        with patch(
            "product_intelligence.web.commercial_access._django_settings",
            _mock_settings(),
        ), _armed_supplement_boundaries():
            response = _get(Client(), url, DENIED_ADDR)

        assert response.status_code == 200
        html = response.content.decode()
        # Public compact table renders normally
        assert "USD Equivalent" in html
        assert "€1,500.00 EUR" in html
        assert 'href="https://www.example.com/product/abc">example.com</a>' in html
        assert "Quote & Market Summary unavailable." not in html

    def test_authorized_malformed_fx_unavailable(self) -> None:
        run = _create_quote_run(mpn="ERR-FX-MPN", malformed_fx=True)
        url = _detail_url(run)
        with patch(
            "product_intelligence.web.commercial_access._django_settings",
            _mock_settings(),
        ):
            response = _get(Client(), url, ALLOWED_ADDR)

        assert response.status_code == 200
        html = response.content.decode()
        assert "Quote & Market Summary unavailable." in html
        assert "USD Equivalent" not in html
        # Detailed report still renders
        assert "Price aggregation status:" in html
        # No error text leaked
        assert "FxCodecError" not in html
        assert "garbage" not in html

    def test_denied_malformed_fx_unavailable(self) -> None:
        run = _create_quote_run(mpn="ERR-DENIED-FX-MPN", malformed_fx=True)
        url = _detail_url(run)
        with patch(
            "product_intelligence.web.commercial_access._django_settings",
            _mock_settings(),
        ):
            response = _get(Client(), url, DENIED_ADDR)

        assert response.status_code == 200
        html = response.content.decode()
        assert "Quote & Market Summary unavailable." in html
        assert "USD Equivalent" not in html
        assert "FxCodecError" not in html
        assert "garbage" not in html

    def test_authorized_programming_error_propagates(self) -> None:
        """A RuntimeError injected into the authorized replay is a
        programming defect: it propagates and is NOT converted into
        'unavailable'."""
        run = _create_quote_run(mpn="ERR-PROG-MPN")
        url = _detail_url(run)
        with patch(
            "product_intelligence.web.commercial_access._django_settings",
            _mock_settings(),
        ), patch(
            "product_intelligence.web.views.replay_compact_quote_projection",
            side_effect=RuntimeError("injected programming defect"),
        ):
            with pytest.raises(RuntimeError, match="injected programming defect"):
                _get(Client(), url, ALLOWED_ADDR)

    def test_denied_programming_error_propagates(self) -> None:
        run = _create_quote_run(mpn="ERR-DENIED-PROG-MPN")
        url = _detail_url(run)
        with patch(
            "product_intelligence.web.commercial_access._django_settings",
            _mock_settings(),
        ), patch(
            "product_intelligence.web.views.replay_public_compact_quote_projection",
            side_effect=RuntimeError("injected programming defect"),
        ):
            with pytest.raises(RuntimeError, match="injected programming defect"):
                _get(Client(), url, DENIED_ADDR)


# ---------------------------------------------------------------------------
# Zero live work (FU1 fail-fast) on GET, both branches
# ---------------------------------------------------------------------------


class TestZeroLiveWorkOnGet:
    def test_allowed_get_zero_live_work(self) -> None:
        run = _create_quote_run(mpn="ZLW-ALLOWED-MPN")
        url = _detail_url(run)
        with (
            patch(
                "product_intelligence.web.commercial_access._django_settings",
                _mock_settings(),
            ),
            _armed_live_boundaries(),
        ):
            _assert_armed_boundaries_raise()
            response = _get(Client(), url, ALLOWED_ADDR)

        assert response.status_code == 200
        assert response.context["vendor_commercial_access_allowed"] is True
        rows = _compact_rows(response)
        assert len(rows) == 4  # 3 vendor + 1 public

    def test_denied_get_zero_live_work(self) -> None:
        run = _create_quote_run(mpn="ZLW-DENIED-MPN")
        url = _detail_url(run)
        with (
            patch(
                "product_intelligence.web.commercial_access._django_settings",
                _mock_settings(),
            ),
            _armed_live_boundaries(),
            _armed_supplement_boundaries(),
        ):
            _assert_armed_boundaries_raise()
            response = _get(Client(), url, DENIED_ADDR)

        assert response.status_code == 200
        assert response.context["vendor_commercial_access_allowed"] is False
        rows = _compact_rows(response)
        assert [r.source_display for r in rows] == ["example.com"]
        html = response.content.decode()
        assert "(Vendor API)" not in html


# ---------------------------------------------------------------------------
# No authority expansion: Machine Price / Reviewed Price untouched
# ---------------------------------------------------------------------------


class TestNoAuthorityExpansion:
    def test_machine_price_section_unchanged_by_compact_summary(self) -> None:
        """The compact summary is display-supplemental: the existing
        Machine Price evidence (frozen 4A bucket statistics) renders
        exactly as before — public bucket values, no vendor values."""
        run = _create_quote_run(mpn="AUTH-MPN")
        url = _detail_url(run)
        with patch(
            "product_intelligence.web.commercial_access._django_settings",
            _mock_settings(),
        ):
            response = _get(Client(), url, ALLOWED_ADDR)

        assert response.status_code == 200
        html = response.content.decode()

        # The detailed bucket section shows ONLY the public EUR value
        price_section = html.split("Price intelligence", 1)[1]
        assert "1500.00" in price_section
        # Vendor prices never enter the detailed price-intelligence
        # audit/evidence sections
        assert "$2,023.27" not in price_section
        assert "1705.35" not in price_section
        assert "1999.99" not in price_section
