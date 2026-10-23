"""PILOT-UX-WORKBENCH-A1 workbench contracts.

Additive presentation tests for the professional redesign of the research
intake page and the top of the research report (the quote workbench).

These tests render the real documents through the Django test client and
pin the NEW design contracts (landmarks, light enterprise theme, report
header, quote summary stat strip, deliberate narrow-viewport overflow) on
top of the frozen B1 contracts already pinned by the existing suites.

Isolation: every DB-touching case is a ``django.test.TestCase`` (per-test
transaction rollback), so this file introduces no persistent
``ResearchRun`` leakage into the session-scoped test database.
"""

from __future__ import annotations

import re
from datetime import date, datetime, timezone
from decimal import Decimal
from html.parser import HTMLParser
from unittest.mock import patch

from django.test import Client, SimpleTestCase, TestCase
from django.urls import reverse

from product_intelligence.domain import ResearchRequest
from product_intelligence.domain.enums import (
    ConfidenceLevel,
    EvidenceDecision,
    IdentityMatchType,
    ResearchRunState,
    VerificationStatus,
)
from product_intelligence.runs.models import (
    TERMINAL_STATES,
)
from product_intelligence.research import (
    ListingIdentityAssessment,
    ListingObservation,
    PriceAggregateBucket,
    PriceAggregationResult,
    encode_price_aggregation_result,
)
from product_intelligence.research.fx_codec import encode_fx_observation
from product_intelligence.research.listings import ExtractionMethod
from product_intelligence.research.matching import (
    EvidenceSource,
    IdentityRejectionReason,
)
from product_intelligence.research.normalization import (
    NormalizedAvailability,
    NormalizedCondition,
    NormalizedListingObservation,
)
from product_intelligence.providers.fx import FxRateObservation
from product_intelligence.runs.models import (
    AiAssistedReviewCandidate,
    ComparableResearchExecution,
    ComparableResearchState,
    PriceIntelligenceSnapshot,
    ResearchFxSnapshot,
    ResearchRun,
    ResearchSupplementSnapshot,
)

ALLOWED_CIDRS = "10.0.0.0/8"
ALLOWED_ADDR = "10.0.0.1"
DENIED_ADDR = "192.0.2.1"  # TEST-NET-1 (RFC 5737) — never assigned
SENTINEL_VENDOR_PRICE = "55512.07"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _mock_settings(cidrs: str = ALLOWED_CIDRS) -> object:
    return type("Settings", (), {"PI_VENDOR_PRICE_ALLOWED_CIDRS": cidrs})()


def _create_run(
    mpn: str = "WB-A1-MPN",
    description: str = "workbench audit product",
    state: "ResearchRunState | None" = None,
    created_at: "datetime | None" = None,
) -> ResearchRun:
    run = ResearchRun.objects.create_from_request(
        ResearchRequest(manufacturer_part_number=mpn, description=description),
        created_at=created_at,
    )
    if state is not None:
        # The frozen lifecycle only admits CREATED -> RUNNING -> terminal,
        # so terminal states are reached through RUNNING.
        if state in TERMINAL_STATES:
            run.transition_to(ResearchRunState.RUNNING)
        run.transition_to(state)
    return run


def _detail_url(run: ResearchRun) -> str:
    return reverse("research-detail", kwargs={"run_id": run.id})


def _public_result(
    run: ResearchRun,
    *,
    source_url: str = "https://www.example.com/product/wb",
    price: Decimal = Decimal("1500.00"),
    currency: str = "EUR",
    availability: "NormalizedAvailability" = NormalizedAvailability.IN_STOCK,
) -> PriceAggregationResult:
    mpn = run.manufacturer_part_number or "WB-MPN"
    obs = ListingObservation(
        source_url=source_url,
        extraction_method=ExtractionMethod.JSON_LD,
        product_title="Workbench Product",
        manufacturer_part_number_text=mpn,
        sku_text=None,
        brand_text=None,
        price_text=str(price),
        currency_text=currency,
        availability_text="In Stock" if availability is NormalizedAvailability.IN_STOCK else "Out of Stock",
        condition_text="New",
        seller_text="Example Store",
        offer_url_text=None,
        raw_reference=None,
    )
    norm = NormalizedListingObservation(
        observation=obs,
        price_amount=price,
        currency_code=currency,
        availability=availability,
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


def _persist_price_snapshot(run: ResearchRun, result: PriceAggregationResult) -> None:
    PriceIntelligenceSnapshot.objects.create(
        run=run,
        schema_version=1,
        payload=encode_price_aggregation_result(result),
    )


def _persist_fx(run: ResearchRun) -> None:
    payload = encode_fx_observation(
        provider_id="ECB",
        observation_date=date(2024, 3, 1),
        base_currency="EUR",
        rates=(
            FxRateObservation(currency_code="USD", rate=Decimal("1.08")),
            FxRateObservation(currency_code="EUR", rate=Decimal("1.0")),
        ),
        retrieved_at=datetime(2024, 3, 1, 12, 0, 0, tzinfo=timezone.utc),
    )
    ResearchFxSnapshot.objects.create(run=run, schema_version=1, payload=payload)


def _persist_vendor_supplement(run: ResearchRun) -> None:
    from product_intelligence.research.commercial_supplement_codec import (
        ResearchSupplementResult,
        SupplementPriceBasis,
        SupplementSourceObservation,
        VendorCommercialResult,
        SupplementLookupStatus,
        encode_research_supplement_result,
    )

    observation = SupplementSourceObservation(
        source_name="Sentinel Vendor",
        explicit_candidate_mpn=run.manufacturer_part_number or "WB-MPN",
        vendor_mpn_match_type="EXACT",
        price_amount=Decimal(SENTINEL_VENDOR_PRICE),
        currency_code="USD",
        availability="IN_STOCK",
        price_basis=SupplementPriceBasis.CUSTOMER_PRICE,
        quantity=1,
        note_kind=None,
        brand_new=True,
        brand_new_basis="VENDOR_API_POLICY",
    )
    result = ResearchSupplementResult(
        vendor_commercial_result=VendorCommercialResult(
            lookup_status=SupplementLookupStatus.SUCCESS,
            retrieved_at=datetime(2024, 3, 1, 12, 0, 0, tzinfo=timezone.utc),
            observations=(observation,),
            source_issues=(),
        ),
    )
    ResearchSupplementSnapshot.objects.create(
        run=run,
        schema_version=1,
        payload=encode_research_supplement_result(result),
    )


def _css_rule_block(html: str, selector: str) -> str:
    """Declaration block of the first exact-*selector* CSS rule (mirrors
    tests/web/test_report_layout.py)."""
    match = re.search(re.escape(selector) + r"\s*\{([^}]*)\}", html)
    assert match is not None, f"CSS rule for {selector!r} not found"
    return match.group(1)


def _declared_page_max_width_rems(html: str) -> float | None:
    match = re.search(
        r"--pi-page-max-width\s*:\s*([0-9]+(?:\.[0-9]+)?)rem\b", html
    )
    return float(match.group(1)) if match is not None else None


class _BalanceChecker(HTMLParser):
    """Fails on unbalanced (stacked) non-void elements in the document."""

    VOID = {
        "area", "base", "br", "col", "embed", "hr", "img", "input",
        "link", "meta", "param", "source", "track", "wbr",
    }

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.stack: list[str] = []
        self.errors: list[str] = []
        self.h1_count = 0
        self.landmarks = {"header": 0, "main": 0, "footer": 0, "nav": 0}

    def handle_starttag(self, tag, attrs) -> None:
        if tag in self.VOID:
            return
        self.stack.append(tag)
        if tag == "h1":
            self.h1_count += 1
        if tag in self.landmarks:
            self.landmarks[tag] += 1

    def handle_endtag(self, tag) -> None:
        if tag in self.VOID:
            return
        if not self.stack or self.stack[-1] != tag:
            # Tolerate browser implicit closes only for <p>; everything
            # else is a real markup defect.
            if tag == "p" and "p" in self.stack:
                while self.stack and self.stack[-1] != "p":
                    self.stack.pop()
                if self.stack:
                    self.stack.pop()
                return
            self.errors.append(f"unbalanced </{tag}>; stack tail {self.stack[-3:]}")
            return
        self.stack.pop()


def _check_markup(html: str) -> _BalanceChecker:
    checker = _BalanceChecker()
    checker.feed(html)
    checker.close()
    return checker


class _QuoteTableParser(HTMLParser):
    """Cell texts of every <tr> in tables between the two section markers
    (mirrors the frozen B1 parser shape)."""

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
            self._current_row.append(" ".join(self._cell_text.split()))

    def handle_data(self, data) -> None:
        if self.in_cell:
            self._cell_text += data


def _quote_table_rows(html: str) -> list[list[str]]:
    start = html.index("<h2>Quote & Market Summary</h2>")
    end = html.index("<h2>Price intelligence</h2>", start)
    section = html[start:end]
    assert '<table class="spec-table">' in section
    parser = _QuoteTableParser()
    parser.feed(section)
    return parser.rows


# ---------------------------------------------------------------------------
# Page A — research intake workbench
# ---------------------------------------------------------------------------


class IntakeMarkupTests(SimpleTestCase):
    """The intake page is well-formed with the enterprise shell."""

    def test_intake_page_landmarks_and_single_h1(self) -> None:
        html = self.client.get(reverse("research-new")).content.decode()
        checker = _check_markup(html)
        self.assertEqual(checker.errors, [], "intake markup is unbalanced")
        self.assertEqual(checker.stack, [], "intake markup leaves open tags")
        self.assertEqual(checker.h1_count, 1)
        self.assertGreaterEqual(checker.landmarks["header"], 1)
        self.assertEqual(checker.landmarks["main"], 1)
        self.assertGreaterEqual(checker.landmarks["footer"], 1)
        self.assertGreaterEqual(checker.landmarks["nav"], 1)

    def test_intake_page_is_light_theme_with_focus_indicators(self) -> None:
        html = self.client.get(reverse("research-new")).content.decode()
        self.assertIn("color-scheme: light", html)
        # Accessible focus treatment exists and uses a visible outline.
        focus_rule = _css_rule_block(html, ":focus-visible")
        self.assertIn("outline", focus_rule)

    def test_intake_page_declares_no_page_width_override(self) -> None:
        html = self.client.get(reverse("research-new")).content.decode()
        self.assertIsNone(_declared_page_max_width_rems(html))
        self.assertIn(
            "var(--pi-page-max-width, 44rem)",
            _css_rule_block(html, "body"),
        )

    def test_intake_page_has_skip_link(self) -> None:
        html = self.client.get(reverse("research-new")).content.decode()
        self.assertIn('href="#pi-main"', html)
        self.assertIn("Skip to main content", html)


class IntakeFieldPresentationTests(TestCase):
    """MPN prominence, optionality honesty, prefill, and validation UX."""

    def test_mpn_input_is_the_prominent_monospace_field(self) -> None:
        html = self.client.get(reverse("research-new")).content.decode()
        rule = _css_rule_block(html, ".pi-intake-card input[type=\"text\"]")
        self.assertIn("monospace", rule)
        # Prominent: the MPN input is styled larger than the base 1rem.
        size = re.search(r"font-size:\s*([0-9.]+)rem", rule)
        self.assertIsNotNone(size)
        self.assertGreater(float(size.group(1)), 1.0)

    def test_description_is_explicitly_optional_mpn_is_not_required(self) -> None:
        html = self.client.get(reverse("research-new")).content.decode()
        # The optional tag sits on the description field only (before the
        # description input, after the MPN input).
        mpn_pos = html.index('name="manufacturer_part_number"')
        desc_pos = html.index('name="description"')
        opt_pos = html.index("(optional)")
        self.assertLess(mpn_pos, opt_pos)
        self.assertLess(opt_pos, desc_pos)
        # Neither input carries a required attribute: the "at least one"
        # rule belongs to the domain contract, not to a mandatory MPN.
        for field_id in ("id_manufacturer_part_number", "id_description"):
            tag = re.search(
                r"<(?:input|textarea)[^>]*id=\"%s\"[^>]*>" % field_id, html
            )
            self.assertIsNotNone(tag, field_id)
            self.assertNotIn("required", tag.group(0))
        # The purpose line keeps the honest either-field wording.
        self.assertIn("Either field may be left blank", html)

    def test_foxpro_style_prefill_renders_into_the_fields(self) -> None:
        response = self.client.get(
            reverse("research-new"),
            {"mpn": "MZ-V8P1T0B/AM", "description": "1TB NVMe M.2 SSD"},
        )
        html = response.content.decode()
        self.assertEqual(response.status_code, 200)
        self.assertIn('value="MZ-V8P1T0B/AM"', html)
        self.assertIn("1TB NVMe M.2 SSD", html)
        self.assertEqual(ResearchRun.objects.count(), 0)

    def test_empty_submission_error_renders_in_an_alert(self) -> None:
        response = self.client.post(
            reverse("research-new"),
            {"manufacturer_part_number": "", "description": ""},
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(ResearchRun.objects.count(), 0)
        html = response.content.decode()
        self.assertIn("role=\"alert\"", html)
        self.assertIn("at least a manufacturer part", html)
        # The error banner is the page's alert; the fields still render.
        self.assertIn('name="manufacturer_part_number"', html)
        self.assertIn('name="description"', html)

    def test_duplicate_submit_guard_contract_is_intact(self) -> None:
        html = self.client.get(reverse("research-new")).content.decode()
        self.assertIn('id="research-new-form"', html)
        self.assertIn('id="research-submit-button"', html)
        self.assertIn(">Run Market Research</button>", html)
        button_tag = re.search(
            r"<button[^>]*id=\"research-submit-button\"[^>]*>", html
        )
        self.assertIsNotNone(button_tag)
        self.assertNotIn("disabled", button_tag.group(0))
        self.assertIn('form.addEventListener("submit"', html)
        self.assertIn("button.disabled = true", html)
        self.assertIn("Researching\\u2026", html)
        self.assertIn("form.checkValidity", html)
        self.assertLess(
            html.index("form.checkValidity"),
            html.index("button.disabled = true"),
        )
        # The guard remains the page's first (and only) inline script.
        self.assertEqual(html.count("<script>"), 1)
        first_script = html.split("<script>")[1].split("</script>")[0]
        self.assertIn("research-new-form", first_script)
        self.assertNotIn("src=", first_script)


# ---------------------------------------------------------------------------
# Page B — report header and status presentation
# ---------------------------------------------------------------------------


class ReportHeaderTests(TestCase):
    """The compact page-level header contract."""

    def test_completed_header_shows_mpn_description_status_and_metadata(self) -> None:
        created_at = datetime(2026, 2, 3, 8, 0, 0, tzinfo=timezone.utc)
        run = _create_run(
            "WB-HEADER-MPN", "a header product", state=ResearchRunState.COMPLETED,
            created_at=created_at,
        )
        html = self.client.get(_detail_url(run)).content.decode()
        self.assertEqual(html.count("<h1"), 1)
        self.assertIn("WB-HEADER-MPN", html)
        self.assertIn("a header product", html)
        self.assertIn("<strong>COMPLETED</strong>", html)
        self.assertIn("<code>%s</code>" % run.id, html)
        self.assertIn("2026-02-03 08:00:00 UTC", html)
        # Terminal run: both timestamps are shown.
        self.assertIn("<dt>Started</dt>", html)
        self.assertIn("<dt>Finished</dt>", html)
        # New research navigation is reachable from the header area.
        self.assertIn("New research", html)

    def test_created_header_omits_absent_timestamps_and_fabricated_values(self) -> None:
        run = _create_run("WB-CREATED", "")
        html = self.client.get(_detail_url(run)).content.decode()
        self.assertNotIn("<dt>Started</dt>", html)
        self.assertNotIn("<dt>Finished</dt>", html)
        self.assertNotIn("Started", html)
        self.assertNotIn("Finished", html)
        self.assertIn("<strong>CREATED</strong>", html)
        self.assertIn("Not supplied", html)
        for fabricated in ("$", "0.00", "$0", "N/A", "109"):
            self.assertNotIn(fabricated, html)
        self.assertNotIn("Median", html)
        self.assertNotIn("median", html.lower())

    def test_running_header_shows_running_state_notice(self) -> None:
        run = _create_run(
            "WB-RUNNING", "", state=ResearchRunState.RUNNING
        )
        html = self.client.get(_detail_url(run)).content.decode()
        self.assertIn("<strong>RUNNING</strong>", html)
        self.assertIn("Research is currently running.", html)

    def test_failed_header_shows_failure_notice_and_retry_action(self) -> None:
        run = _create_run("WB-FAILED", "")
        run.transition_to(ResearchRunState.RUNNING)
        run.transition_to(ResearchRunState.FAILED)
        html = self.client.get(_detail_url(run)).content.decode()
        self.assertIn("<strong>FAILED</strong>", html)
        self.assertIn("Research did not complete successfully.", html)
        self.assertIn("Retry", html)
        self.assertIn(
            'action="%s"' % reverse("research-retry", kwargs={"run_id": run.id}),
            html,
        )
        self.assertIn("csrfmiddlewaretoken", html)

    def test_partially_completed_state_renders_neutral(self) -> None:
        """The state vocabulary includes PARTIALLY_COMPLETED; the report
        renders it plainly without inventing completion claims."""
        run = _create_run("WB-PARTIAL", "")
        run.transition_to(ResearchRunState.RUNNING)
        run.transition_to(ResearchRunState.PARTIALLY_COMPLETED)
        response = self.client.get(_detail_url(run))
        self.assertEqual(response.status_code, 200)
        html = response.content.decode()
        self.assertIn("<strong>PARTIALLY_COMPLETED</strong>", html)
        self.assertIn("partial result", html)

    def test_report_page_landmarks_and_balance(self) -> None:
        run = _create_run("WB-LANDMARK", "balanced")
        html = self.client.get(_detail_url(run)).content.decode()
        checker = _check_markup(html)
        self.assertEqual(checker.errors, [])
        self.assertEqual(checker.stack, [])
        self.assertEqual(checker.h1_count, 1)
        self.assertEqual(checker.landmarks["main"], 1)
        self.assertGreaterEqual(checker.landmarks["nav"], 1)


# ---------------------------------------------------------------------------
# Page B — Quote & Market Summary workbench
# ---------------------------------------------------------------------------


class QuoteSummaryWorkbenchTests(TestCase):
    """The primary business area: counts, span, missing-vs-zero honesty."""

    def _completed_run(self, mpn: str = "WB-QUOTE") -> ResearchRun:
        run = _create_run(mpn, "quote workbench product")
        run.transition_to(ResearchRunState.RUNNING)
        run.transition_to(ResearchRunState.COMPLETED)
        _persist_price_snapshot(run, _public_result(run))
        _persist_fx(run)
        return run

    def test_stat_strip_renders_counts_lowest_and_span(self) -> None:
        run = self._completed_run()
        html = self.client.get(_detail_url(run), REMOTE_ADDR=DENIED_ADDR).content.decode()
        summary = _css_rule_block(html, ".pi-summary")
        self.assertIn("grid", summary)
        self.assertIn("<dt>Quotes found</dt>", html)
        self.assertIn("<dt>In stock</dt>", html)
        self.assertIn("Lowest in-stock quote", html)
        self.assertIn("Observed quote span (USD equivalent)", html)
        self.assertIn("<dd>1</dd>", html)
        # USD equivalents render (persisted FX), with the source of the
        # lowest in-stock quote.
        self.assertIn("$1,620.00 USD", html)
        # The table still renders in the same document region.
        rows = _quote_table_rows(html)
        self.assertEqual(
            rows[0],
            ["Source", "Price", "USD Equivalent", "Availability",
             "Condition", "Match / Evidence", "Market Use", "Actions"],
        )

    def test_missing_values_render_unavailable_never_zero(self) -> None:
        """Out-of-stock listing + no FX evidence: lowest in-stock and
        span are MISSING (not zero) and the page never shows $0."""
        run = _create_run("WB-MISSING", "missing values product")
        run.transition_to(ResearchRunState.RUNNING)
        run.transition_to(ResearchRunState.COMPLETED)
        _persist_price_snapshot(
            run,
            _public_result(
                run,
                price=Decimal("900.00"),
                currency="USD",
                availability=NormalizedAvailability.OUT_OF_STOCK,
            ),
        )
        html = self.client.get(_detail_url(run), REMOTE_ADDR=DENIED_ADDR).content.decode()
        self.assertIn("Quote & Market Summary", html)
        # In-stock count is genuinely zero and renders as 0.
        self.assertIn("<dd>0</dd>", html)
        # The missing lowest/span values are labeled Unavailable.
        self.assertIn("Unavailable", html)
        self.assertNotIn("$0.00 USD", html)
        self.assertNotIn("$0 USD", html)

    def test_zero_price_row_keeps_b1_verification_note_in_its_row(self) -> None:
        from product_intelligence.research.aggregation import aggregate_listing_prices

        run = _create_run("WB-ZERO", "zero price product")
        run.transition_to(ResearchRunState.RUNNING)
        run.transition_to(ResearchRunState.COMPLETED)
        obs = ListingObservation(
            source_url="https://zero-offer.example/product/zero",
            extraction_method=ExtractionMethod.JSON_LD,
            product_title="Zero Offer Product",
            manufacturer_part_number_text="WB-ZERO",
            sku_text=None,
            brand_text=None,
            price_text="0",
            currency_text="USD",
            availability_text="In Stock",
            condition_text="New",
            seller_text="Zero Offer Store",
            offer_url_text=None,
            raw_reference=None,
        )
        norm = NormalizedListingObservation(
            observation=obs,
            price_amount=Decimal("0"),
            currency_code="USD",
            availability=NormalizedAvailability.IN_STOCK,
            condition=NormalizedCondition.NEW,
            seller_name="Zero Offer Store",
            normalization_issues=(),
        )
        assess = ListingIdentityAssessment(
            normalized_listing=norm,
            requested_part_number="WB-ZERO",
            candidate_part_number_raw="WB-ZERO",
            candidate_part_number_compared="WB-ZERO",
            candidate_evidence_source=EvidenceSource.EXPLICIT_MPN_FIELD,
            match_type=IdentityMatchType.EXACT,
            decision=EvidenceDecision.ACCEPTED,
            rejection_reason=None,
        )
        result = aggregate_listing_prices(run.to_research_request(), (assess,))
        _persist_price_snapshot(run, result)

        html = self.client.get(_detail_url(run)).content.decode()
        self.assertIn(
            "Source-published price: $0 USD — Verify price and purchasing "
            "availability with the supplier.",
            html,
        )
        rows = _quote_table_rows(html)
        body = [r for r in rows if r and r[0] != "Source"]
        self.assertEqual(len(body), 1)
        cells = " | ".join(body[0])
        self.assertIn("zero-offer.example", cells)
        self.assertIn("$0 USD", cells)
        self.assertIn("Verify price and purchasing availability with the supplier.", cells)
        # The zero row is NOT relabeled free/confirmed/recommended.
        for forbidden in ("free", "Free", "recommended", "purchasable"):
            self.assertNotIn(forbidden, cells)

    def test_positive_price_row_has_no_zero_note(self) -> None:
        run = self._completed_run("WB-POSITIVE")
        html = self.client.get(_detail_url(run), REMOTE_ADDR=DENIED_ADDR).content.decode()
        rows = _quote_table_rows(html)
        body = [r for r in rows if r and r[0] != "Source"]
        self.assertEqual(len(body), 1)
        cells = " | ".join(body[0])
        self.assertIn("€1,500.00 EUR", cells)
        self.assertNotIn("Source-published price:", cells)
        self.assertNotIn("Verify price and purchasing availability", cells)

    def test_public_market_line_and_median_gate(self) -> None:
        run = self._completed_run("WB-MARKET")
        html = self.client.get(_detail_url(run), REMOTE_ADDR=DENIED_ADDR).content.decode()
        self.assertIn("Comparable public market", html)
        self.assertIn("<strong>1</strong>", html)
        self.assertIn("comparable NEW listing", html)
        self.assertIn("Observed span:", html)
        self.assertIn("Not shown — fewer than 3 comparable NEW listings.", html)
        # No numeric median in the primary summary below 3 NEW listings.
        primary = html.split("Quote & Market Summary", 1)[1].split(
            "Advanced Evidence & Audit", 1
        )[0]
        self.assertNotIn("<strong>Median:</strong> $", primary)

    def test_unsafe_source_url_renders_plain_text_and_no_href(self) -> None:
        run = _create_run("WB-UNSAFE", "unsafe url product")
        run.transition_to(ResearchRunState.RUNNING)
        run.transition_to(ResearchRunState.COMPLETED)
        _persist_price_snapshot(
            run,
            _public_result(run, source_url="javascript:alert(1)"),
        )
        response = self.client.get(_detail_url(run), REMOTE_ADDR=DENIED_ADDR)
        self.assertEqual(response.status_code, 200)
        html = response.content.decode()
        self.assertNotIn('href="javascript:', html)
        self.assertIn("Unknown Source", html)
        self.assertIn("Quote & Market Summary", html)

    def test_denied_vendor_data_absent_and_notice_present(self) -> None:
        run = self._completed_run("WB-DENIED")
        _persist_vendor_supplement(run)
        with patch(
            "product_intelligence.web.commercial_access._django_settings",
            _mock_settings(),
        ):
            response = self.client.get(_detail_url(run), REMOTE_ADDR=DENIED_ADDR)
        self.assertEqual(response.status_code, 200)
        html = response.content.decode()
        self.assertIn(
            "Internal commercial pricing is unavailable for this connection.",
            html,
        )
        self.assertEqual(response.context["vendor_commercial_access_allowed"], False)
        # No hidden unauthorized data: no vendor label, price, or currency
        # anywhere in the page source.
        self.assertNotIn("Sentinel Vendor", html)
        self.assertNotIn(SENTINEL_VENDOR_PRICE, html)
        self.assertNotIn("55,512.07", html)
        self.assertNotIn("(Vendor API)", html)

    def test_allowed_vendor_rows_render_with_labels(self) -> None:
        run = self._completed_run("WB-ALLOWED")
        _persist_vendor_supplement(run)
        with patch(
            "product_intelligence.web.commercial_access._django_settings",
            _mock_settings(),
        ):
            response = self.client.get(_detail_url(run), REMOTE_ADDR=ALLOWED_ADDR)
        self.assertEqual(response.status_code, 200)
        html = response.content.decode()
        self.assertTrue(response.context["vendor_commercial_access_allowed"])
        self.assertIn("Sentinel Vendor (Vendor API)", html)
        self.assertEqual(html.count("Sentinel Vendor (Vendor API)"), 1)
        self.assertIn("$55,512.07 USD", html)


# ---------------------------------------------------------------------------
# Page B — narrow viewport and table overflow behavior
# ---------------------------------------------------------------------------


class NarrowViewportTests(TestCase):
    """Deliberate horizontal overflow for the 8-column quote table."""

    def _render_detail(self) -> str:
        run = _create_run("WB-NARROW", "narrow probe")
        run.transition_to(ResearchRunState.RUNNING)
        run.transition_to(ResearchRunState.COMPLETED)
        _persist_price_snapshot(run, _public_result(run))
        return self.client.get(_detail_url(run)).content.decode()

    def test_quote_table_declares_min_width_for_horizontal_overflow(self) -> None:
        html = self._render_detail()
        rule = _css_rule_block(html, ".pi-quote-wrapper .spec-table")
        value = re.search(r"min-width:\s*([0-9.]+)rem", rule)
        self.assertIsNotNone(value)
        self.assertGreaterEqual(float(value.group(1)), 48.0)
        # The wrapper still owns the overflow safety, and the table keeps
        # width: 100% for wide viewports.
        self.assertIn("overflow-x: auto", _css_rule_block(html, ".spec-table-wrapper"))
        self.assertIn("width: 100%", _css_rule_block(html, ".spec-table"))

    def test_detail_page_declares_widened_capped_column(self) -> None:
        run = _create_run("WB-WIDTH", "width probe")
        html = self.client.get(_detail_url(run)).content.decode()
        width = _declared_page_max_width_rems(html)
        self.assertIsNotNone(width)
        self.assertGreater(width, 44.0)
        self.assertLessEqual(width, 100.0)


# ---------------------------------------------------------------------------
# Page B — AI review workbench availability (historical, CSRF, no live work)
# ---------------------------------------------------------------------------


class _CandidateFixture:
    """A COMPLETED run with one binding-valid NEEDS_REVIEW candidate.

    Built exactly like the frozen HUMAN-REVIEW fixtures: the persisted
    assessment is the ORIGINAL deterministic REJECTED
    (NO_EXPLICIT_MPN_EVIDENCE + TITLE_TEXT); the candidate is the separate
    semantic authority mapped to it.
    """

    @staticmethod
    def build() -> tuple[ResearchRun, AiAssistedReviewCandidate]:
        from product_intelligence.research.aggregation import aggregate_listing_prices
        from product_intelligence.research.price_result_codec import (
            PRICE_RESULT_SCHEMA_VERSION,
        )

        request = ResearchRequest(
            manufacturer_part_number="WB-AI-001",
            description="AI review probe",
        )
        run = ResearchRun.objects.create_from_request(request)
        run.transition_to(ResearchRunState.RUNNING)
        run.transition_to(ResearchRunState.COMPLETED)

        obs = ListingObservation(
            source_url="https://example.com/product/wb-ai",
            extraction_method=ExtractionMethod.JSON_LD,
            manufacturer_part_number_text="",
            sku_text=None,
            product_title="AI probe product for WB-AI-001",
            price_text="99.99",
            currency_text="USD",
            condition_text="new",
        )
        norm = NormalizedListingObservation(
            observation=obs,
            price_amount=Decimal("99.99"),
            currency_code="USD",
            condition=NormalizedCondition.NEW,
            availability=NormalizedAvailability.UNKNOWN,
            seller_name="Probe Seller",
            normalization_issues=(),
        )
        assessment = ListingIdentityAssessment(
            normalized_listing=norm,
            requested_part_number="WB-AI-001",
            candidate_part_number_raw="WB-AI-001",
            candidate_part_number_compared="WB-AI-001",
            candidate_evidence_source=EvidenceSource.TITLE_TEXT,
            match_type=IdentityMatchType.UNKNOWN,
            decision=EvidenceDecision.REJECTED,
            rejection_reason=IdentityRejectionReason.NO_EXPLICIT_MPN_EVIDENCE,
        )
        price_result = aggregate_listing_prices(request, (assessment,))
        PriceIntelligenceSnapshot.objects.create(
            run=run,
            schema_version=PRICE_RESULT_SCHEMA_VERSION,
            payload=encode_price_aggregation_result(price_result),
        )
        candidate = AiAssistedReviewCandidate.objects.create(
            run=run,
            assessment_index=0,
            source_url=obs.source_url,
            target_mpn=request.manufacturer_part_number,
            target_description=request.description,
            candidate_title=obs.product_title or "",
            candidate_mpn_field=obs.manufacturer_part_number_text or "",
            candidate_sku=obs.sku_text or "",
            evidence_source="TITLE_TEXT",
            actual_provider="amax",
            actual_model="nemotron-3-super",
            prompt_version="v1.1",
        )
        return run, candidate


class AIReviewWorkbenchTests(TestCase):
    """AI review actions stay available, historical, and CSRF-protected."""

    def test_review_section_renders_candidate_actions_and_csrf(self) -> None:
        run, candidate = _CandidateFixture.build()
        html = self.client.get(_detail_url(run)).content.decode()
        self.assertIn("<h2>AI-assisted evidence & review</h2>", html)
        self.assertIn(
            "AI confidence is a workflow tier, not a calibrated probability.",
            html,
        )
        self.assertIn('id="ai-candidate-%s"' % candidate.id, html)
        self.assertIn("Possible matches — needs review", html)
        # The review form posts to the frozen endpoint with CSRF.
        self.assertIn(
            'action="%s"' % reverse(
                "research-review",
                kwargs={"run_id": run.id, "candidate_id": candidate.id},
            ),
            html,
        )
        self.assertIn('name="action" value="confirm"', html)
        self.assertIn('name="action" value="reject"', html)
        self.assertIn("csrfmiddlewaretoken", html)

    def test_review_post_requires_csrf(self) -> None:
        run, candidate = _CandidateFixture.build()
        strict_client = Client(enforce_csrf_checks=True)
        url = reverse(
            "research-review",
            kwargs={"run_id": run.id, "candidate_id": candidate.id},
        )
        response = strict_client.post(url, {"action": "confirm"})
        self.assertEqual(response.status_code, 403)
        candidate.refresh_from_db()
        self.assertEqual(
            candidate.review_state,
            AiAssistedReviewCandidate.REVIEW_STATE_UNREVIEWED,
        )

    def test_historical_ai_review_get_performs_zero_live_work(self) -> None:
        import urllib.request

        from product_intelligence.providers.serper import SerperSearchProvider
        from product_intelligence.providers.http_page import HttpPageFetcher
        from product_intelligence.providers.internal_vendor import (
            InternalVendorAdapter,
        )
        from product_intelligence.providers.fx import EcbFxProvider
        from product_intelligence.semantic.runtime import SemanticRuntime
        from product_intelligence.execution import semantic_integration

        run, _ = _CandidateFixture.build()

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
            response = self.client.get(_detail_url(run))
        self.assertEqual(response.status_code, 200)
        html = response.content.decode()
        self.assertIn("<h2>AI-assisted evidence & review</h2>", html)

    def test_review_state_change_renders_historically(self) -> None:
        run, candidate = _CandidateFixture.build()
        url = reverse(
            "research-review",
            kwargs={"run_id": run.id, "candidate_id": candidate.id},
        )
        response = self.client.post(url, {"action": "reject"})
        self.assertEqual(response.status_code in (301, 302), True)
        candidate.refresh_from_db()
        self.assertEqual(
            candidate.review_state,
            AiAssistedReviewCandidate.REVIEW_STATE_REJECTED,
        )
        html = self.client.get(_detail_url(run)).content.decode()
        self.assertIn("Rejected AI-assisted sources", html)


# ---------------------------------------------------------------------------
# Page B — comparable section states (presentation availability only)
# ---------------------------------------------------------------------------


class ComparableWorkbenchTests(TestCase):
    def test_completed_run_offers_comparable_trigger_with_csrf(self) -> None:
        run = _create_run("WB-COMP", "")
        run.transition_to(ResearchRunState.RUNNING)
        run.transition_to(ResearchRunState.COMPLETED)
        html = self.client.get(_detail_url(run)).content.decode()
        self.assertIn("<h2>Comparable products</h2>", html)
        self.assertIn("Research Comparable Products", html)
        self.assertIn(
            'action="%s"' % reverse("research-comparables", kwargs={"run_id": run.id}),
            html,
        )
        self.assertIn("csrfmiddlewaretoken", html)

    def test_non_completed_run_shows_availability_notice(self) -> None:
        run = _create_run("WB-COMP-CREATED", "")
        html = self.client.get(_detail_url(run)).content.decode()
        self.assertIn(
            "Comparable research is available for completed research runs.",
            html,
        )
        self.assertNotIn("Research Comparable Products", html)

    def test_failed_comparable_child_shows_retry_action(self) -> None:
        run = _create_run("WB-COMP-FAIL", "")
        run.transition_to(ResearchRunState.RUNNING)
        run.transition_to(ResearchRunState.COMPLETED)
        ComparableResearchExecution.objects.create(
            parent_run=run,
            state=ComparableResearchState.FAILED,
            active_slot=None,
            started_at=datetime(2026, 3, 1, 10, 0, 0, tzinfo=timezone.utc),
            finished_at=datetime(2026, 3, 1, 10, 1, 0, tzinfo=timezone.utc),
            failure_reason="DISCOVERY_FAILED",
        )
        html = self.client.get(_detail_url(run)).content.decode()
        self.assertIn("Comparable research did not complete successfully.", html)
        self.assertIn("Retry Comparable Research", html)
        self.assertIn("DISCOVERY_FAILED", html)

    def test_completed_comparable_child_renders_result_section(self) -> None:
        from product_intelligence.research.comparable_result_codec import (
            encode_comparable_result,
        )
        from product_intelligence.research.comparable_research_results import (
            AuthorityAttemptResult,
            AuthorityAuditOutcomeKind,
            ComparableResearchResult,
            ComparableResultKind,
        )

        run = _create_run("", "comparable probe description")
        run.transition_to(ResearchRunState.RUNNING)
        run.transition_to(ResearchRunState.COMPLETED)
        result = ComparableResearchResult(
            kind=ComparableResultKind.NO_REQUESTED_MPN,
            target_mpn="",
            target_manufacturer=None,
            target_enrichment_audit=None,
            authority_audit=(
                AuthorityAttemptResult(
                    policy_id="wb-a1-policy",
                    outcome=AuthorityAuditOutcomeKind.NO_REQUESTED_MPN,
                    requested_source_url="https://example.com/support",
                ),
            ),
            candidates=(),
        )
        ComparableResearchExecution.objects.create(
            parent_run=run,
            state=ComparableResearchState.COMPLETED,
            active_slot=None,
            started_at=datetime(2026, 3, 1, 10, 0, 0, tzinfo=timezone.utc),
            finished_at=datetime(2026, 3, 1, 10, 1, 0, tzinfo=timezone.utc),
            result_payload=encode_comparable_result(result),
            result_schema_version=1,
        )
        html = self.client.get(_detail_url(run)).content.decode()
        self.assertIn(
            "Comparable research could not establish a target because no MPN was supplied.",
            html,
        )
