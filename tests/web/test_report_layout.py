"""Desktop layout contract for the durable research report
(PRODUCT-INTEL.PILOT-UX-QUOTE-SUMMARY-B2-FU1).

The 8-column "Quote & Market Summary" table must be readable on a wide
desktop: the report document declares a content column wider than the
base stylesheet's narrow 44rem default, while

* unrelated pages (the intake form) keep the narrow 44rem column;
* the base 44rem fallback for the page column is preserved (the fix is
  a declared wider value, not a removal of the width cap);
* the column stays capped (widened, not full-bleed);
* the horizontal-overflow safety (``.spec-table-wrapper {
  overflow-x: auto }``) and the table's ``width: 100%`` remain in
  place for genuinely narrow screens.

Strategy (matches the project's server-rendered/template tests):
render the real documents through the Django test client and assert on
the declared layout values, scoped to the width rules and the actual
"Quote & Market Summary" table region — never the whole rendered
document.
"""

from __future__ import annotations

import re
from decimal import Decimal
from unittest.mock import patch

from django.test import TestCase
from django.urls import reverse

from product_intelligence.domain import ResearchRequest
from product_intelligence.domain.enums import (
    ConfidenceLevel,
    EvidenceDecision,
    IdentityMatchType,
    VerificationStatus,
)
from product_intelligence.research import (
    ListingIdentityAssessment,
    ListingObservation,
    PriceAggregateBucket,
    PriceAggregationResult,
    encode_price_aggregation_result,
)
from product_intelligence.research.listings import ExtractionMethod
from product_intelligence.research.matching import EvidenceSource
from product_intelligence.research.normalization import (
    NormalizedAvailability,
    NormalizedCondition,
    NormalizedListingObservation,
)
from product_intelligence.runs.models import (
    PriceIntelligenceSnapshot,
    ResearchRun,
)

#: The base stylesheet's narrow page column, in rem.
BASE_COLUMN_REM = 44.0

#: The page column must be widened, but it stays a capped reading
#: width (no uncapped full-bleed page, no giant arbitrary width).
WIDENED_COLUMN_MAX_REM = 100.0

#: TEST-NET-1 (RFC 5737) — never assigned; denied against the pinned
#: 10.0.0.0/8 gate, mirroring tests/web/test_compact_quote_report.py.
DENIED_ADDR = "192.0.2.1"

_PAGE_MAX_WIDTH_RE = re.compile(
    r"--pi-page-max-width\s*:\s*([0-9]+(?:\.[0-9]+)?)rem\b"
)


def _declared_page_max_width_rems(html: str) -> float | None:
    """The ``--pi-page-max-width`` value declared in *html*, in rem.

    ``None`` means the document does not widen the page column and uses
    the base stylesheet's 44rem fallback.
    """
    match = _PAGE_MAX_WIDTH_RE.search(html)
    return float(match.group(1)) if match is not None else None


def _css_rule_block(html: str, selector: str) -> str:
    """The declaration block of the first exact-*selector* CSS rule in
    *html*. Asserts the rule exists (the base stylesheet is part of the
    rendered document, so a missing rule is a layout regression)."""
    match = re.search(re.escape(selector) + r"\s*\{([^}]*)\}", html)
    assert match is not None, f"CSS rule for {selector!r} not found"
    return match.group(1)


def _mock_settings(cidrs: str = "10.0.0.0/8") -> object:
    return type("Settings", (), {"PI_VENDOR_PRICE_ALLOWED_CIDRS": cidrs})()


def _create_run(mpn: str = "LAYOUT-MPN") -> ResearchRun:
    return ResearchRun.objects.create_from_request(
        ResearchRequest(manufacturer_part_number=mpn, description="Layout contract")
    )


def _detail_url(run: ResearchRun) -> str:
    return reverse("research-detail", kwargs={"run_id": run.id})


def _persist_public_price_snapshot(run: ResearchRun) -> None:
    """Persist one accepted public listing so the compact quote table
    renders. Denied path: no vendor artifacts and no FX evidence are
    needed (the USD-equivalent display is simply unavailable)."""
    mpn = run.manufacturer_part_number
    price = Decimal("1500.00")
    obs = ListingObservation(
        source_url="https://www.example.com/product/layout",
        extraction_method=ExtractionMethod.JSON_LD,
        product_title="Layout Contract Product",
        manufacturer_part_number_text=mpn,
        sku_text=None,
        brand_text=None,
        price_text=str(price),
        currency_text="EUR",
        availability_text="In Stock",
        condition_text="New",
        seller_text="Example Store",
        offer_url_text=None,
        raw_reference=None,
    )
    norm = NormalizedListingObservation(
        observation=obs,
        price_amount=price,
        currency_code="EUR",
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
    result = PriceAggregationResult(
        request=run.to_research_request(),
        assessments=(assess,),
        exclusions=(),
        buckets=(
            PriceAggregateBucket(
                currency_code="EUR",
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
    PriceIntelligenceSnapshot.objects.create(
        run=run,
        schema_version=1,
        payload=encode_price_aggregation_result(result),
    )


class ReportPageWidthTests(TestCase):
    """The research detail document's desktop content column."""

    def test_detail_page_declares_a_wider_content_column_than_the_base_default(self) -> None:
        """Regression guard for the restrictive desktop container: the
        report document must not be pinned to the narrow 44rem base
        column that compressed the Quote & Market Summary table."""
        html = self.client.get(_detail_url(_create_run())).content.decode()

        width = _declared_page_max_width_rems(html)
        self.assertIsNotNone(
            width,
            "research detail page no longer declares a widened page "
            "column; the Quote & Market Summary table is compressed back "
            "to the narrow 44rem base default",
        )
        self.assertGreater(width, BASE_COLUMN_REM)
        self.assertLessEqual(width, WIDENED_COLUMN_MAX_REM)

    def test_detail_page_keeps_the_base_fallback_in_the_body_rule(self) -> None:
        """The body rule must keep the 44rem fallback: the fix is a
        declared wider value for the report document, not a removal of
        the page width cap."""
        html = self.client.get(_detail_url(_create_run())).content.decode()

        self.assertIn(
            "var(--pi-page-max-width, 44rem)",
            _css_rule_block(html, "body"),
        )


class UnrelatedPageWidthTests(TestCase):
    """Pages other than the report keep the narrow base column."""

    def test_intake_form_keeps_the_narrow_base_column(self) -> None:
        html = self.client.get(reverse("research-new")).content.decode()

        self.assertIsNone(
            _declared_page_max_width_rems(html),
            "the intake form page must keep the narrow 44rem base "
            "column; only the report page widens it",
        )
        self.assertIn(
            "var(--pi-page-max-width, 44rem)",
            _css_rule_block(html, "body"),
        )


class NarrowScreenSafetyTests(TestCase):
    """Overflow protection for genuinely narrow screens is preserved."""

    def test_table_overflow_wrapper_safety_is_preserved(self) -> None:
        html = self.client.get(_detail_url(_create_run())).content.decode()

        self.assertIn(
            "overflow-x: auto",
            _css_rule_block(html, ".spec-table-wrapper"),
        )
        self.assertIn("width: 100%", _css_rule_block(html, ".spec-table"))


class QuoteTableInWidenedDocumentTests(TestCase):
    """The layout contract bound to the actual table region."""

    def test_quote_table_renders_inside_the_widened_detail_document(self) -> None:
        """A report with compact quote rows renders the Quote & Market
        Summary table in the same document that declares the widened
        desktop content column (denied path: public row only, zero
        vendor artifact access)."""
        run = _create_run("LAYOUT-QUOTE-MPN")
        _persist_public_price_snapshot(run)

        with patch(
            "product_intelligence.web.commercial_access._django_settings",
            _mock_settings(),
        ):
            response = self.client.get(_detail_url(run), REMOTE_ADDR=DENIED_ADDR)

        self.assertEqual(response.status_code, 200)
        html = response.content.decode()

        # Scope assertions to the actual Quote & Market Summary region.
        section = html[
            html.index("<h2>Quote & Market Summary</h2>") : html.index(
                "<h2>Price intelligence</h2>"
            )
        ]
        self.assertIn('<table class="spec-table">', section)
        self.assertIn("<th>Source</th>", section)
        self.assertIn("<th>Actions</th>", section)

        # That document declares the widened desktop column.
        width = _declared_page_max_width_rems(html)
        self.assertIsNotNone(width)
        self.assertGreater(width, BASE_COLUMN_REM)
        self.assertLessEqual(width, WIDENED_COLUMN_MAX_REM)
