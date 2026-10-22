"""Regression evidence for PRODUCT-INTEL.PILOT-VALUE-EVIDENCE-A1 (FU2 base).

Provenance of record (verified 2026-10-20, one bounded developer GET per URL
through the frozen 3A ``HttpPageFetcher``; captures preserved as untracked
``tmp_a1_evidence/capture_*.html``):

* Central Computer 96 GB module page (production run
  ``2db82a51298c4c8bb312a88cbf07dfb0`` / ``b60a0dc4ea0e42b79d19cf5301ec61d1``
  / ``422b469c277f41b3b0b31556c1ccdc7b``, requested MPN
  ``M321RYGA0PB2-CCP``): the visible body publishes the manufacturer part
  number twice — an inline detail span ``Model #: M321RYGA0PB2-CCP`` (with the
  retailer ``Item #: MEMSAM59664S`` beside it) and a definition-table row
  ``<td>Manufacturer Part Number</td><td>M321RYGA0PB2-CCP</td>``. The JSON-LD
  ``Product`` node publishes the retailer SKU (``MEMSAM59664S``) and price
  (``4099.99`` USD) but no ``mpn``. The page records 2,704 bounded visible
  identity elements — above the previous 2,048 capture bound, so the bound
  erased every element and the authorized visible-labeled-MPN path never saw
  the evidence.
* Central Computer 64 GB module page (production run
  ``b0543af1933c447ca8680380a1afbfaf``, requested MPN
  ``M321R8GA0PB2-CCP``): the same shape (SKU ``MEMSAM56464S``, price
  ``3499.99`` USD, 2,706 elements).
* ServerOrbit Seagate page (production run
  ``7b9cd5f484144eeeb30425f85ba1e575``, requested MPN ``XP15360SE70005``):
  the visible description list publishes ``<li><strong>Model Number:</strong>
  XP15360SE70005</li>``; the JSON-LD ``Product`` publishes SKU
  ``XP15360SE70005`` (equal to the requested MPN), price ``0`` USD and
  ``NewCondition``. That run predates the authorized visible-labeled-MPN path;
  the current extractor already captures the visible field, so this file pins
  the adjudication rather than changing any ServerOrbit behavior.

The documents below are constructed inline and are synthetic; they reuse the
recorded field values verbatim so the regression is tied to the production
evidence. The recorded JSON-LD ``description`` texts are pinned where the
frozen contract says they must NOT gain visible authority: a label inside a
``<script>`` block is not a visible field.

Frozen authorities exercised here (all unchanged by this phase): 3B
normalization (``UNKNOWN`` condition is never inferred as ``NEW``; the
published ``0`` price is the page's own value), 3C acceptance (``ACCEPTED``
only through ``EXACT`` / ``NORMALIZED_EXACT`` on an explicit or bounded
visible labeled MPN), 4A aggregation (``UNKNOWN_CONDITION`` and
``IDENTITY_NOT_ACCEPTED`` exclusions), and the FU3B human-review eligibility
predicate.
"""

from __future__ import annotations

import json
from decimal import Decimal

from product_intelligence.domain import ResearchRequest
from product_intelligence.domain.enums import EvidenceDecision, IdentityMatchType
from product_intelligence.research.aggregation import (
    PriceAggregationExclusionReason,
    aggregate_listing_prices,
)
from product_intelligence.research.extraction import extract_listing_observations
from product_intelligence.research.listings import ExtractionMethod
from product_intelligence.research.matching import (
    EvidenceSource,
    assess_listing_identities,
    is_human_review_eligible_assessment,
)
from product_intelligence.research.normalization import (
    NormalizedCondition,
    normalize_listing_observations,
)

URL = "https://probe.example/pilot-a1"

# Recorded production values (Central Computer 96 GB module page).
CC96_MPN = "M321RYGA0PB2-CCP"
CC96_SKU = "MEMSAM59664S"
CC96_TITLE = (
    "Samsung 96GB DDR5 6400mhz ECC RDIMM 2Rx4 PC5-51200R Dual Rank x4 REG "
    "Server Module Memory"
)
CC96_PRICE = "4099.99"

# Recorded production values (Central Computer 64 GB module page).
CC64_MPN = "M321R8GA0PB2-CCP"
CC64_SKU = "MEMSAM56464S"

# Recorded production values (ServerOrbit Seagate page).
SO_MPN = "XP15360SE70005"

# The verified CC pages record 2,704 / 2,706 bounded visible identity
# elements. 2,700 filler leaves is the scale of the verified product page.
CC_PAGE_CHROME_ELEMENTS = 2700


def _json_ld(node: object) -> str:
    return (
        '<script type="application/ld+json">'
        + json.dumps(node, ensure_ascii=False)
        + "</script>"
    )


def _extract(document: str) -> tuple:
    return extract_listing_observations(document, source_url=URL)


def _chrome_spans(count: int) -> str:
    """Inert navigation-chrome leaves: identifier-shaped but never labeled."""
    return "".join(f"<span>chrome{i:05d}</span>" for i in range(count))


def _cc96_product_node(description: str | None = None) -> dict:
    """The recorded CC96 JSON-LD shape: retailer SKU + price, no ``mpn``."""
    node = {
        "@context": "https://schema.org",
        "@type": "Product",
        "brand": {"@type": "Brand", "name": "Samsung"},
        "name": CC96_TITLE,
        "sku": CC96_SKU,
        "productID": CC96_SKU,
        "offers": {
            "@type": "https://schema.org/Offer",
            "availability": "https://schema.org/InStock",
            "price": CC96_PRICE,
            "priceCurrency": "USD",
        },
    }
    if description is not None:
        node["description"] = description
    return node


def _cc96_description_table() -> str:
    """The recorded CC96 JSON-LD ``description``: an HTML table in script text."""
    return (
        "<table><tr><td colspan=\"2\"><strong>General Information</strong></td></tr>"
        f"<tr><td>Brand Name</td><td>Samsung</td></tr>"
        f"<tr><td>Manufacturer Part Number</td><td>{CC96_MPN}</td></tr>"
        "<tr><td>Manufacturer Website Address</td>"
        "<td>http://www.samsung.com/us</td></tr>"
        "<tr><td colspan=\"2\"><strong>Technical Information</strong></td></tr>"
        "<tr><td>Memory Voltage</td><td>1.10 V</td></tr>"
        "</table>"
    )


def _cc96_visible_detail(
    *, table_row: bool = True, inline_span: bool = True
) -> str:
    """The recorded visible detail shape: inline Model # span + spec table."""
    parts = []
    if inline_span:
        parts.append(
            "<span class=\"mfg\">Model #: " + CC96_MPN + "</span> "
            "<span class=\"central\">Item #: " + CC96_SKU + "</span>"
        )
    if table_row:
        parts.append(
            "<table><tbody>"
            "<tr><td>Product Type</td><td>RAM Module</td></tr>"
            f"<tr><td>Manufacturer Part Number</td><td>{CC96_MPN}</td></tr>"
            "<tr><td>Memory Voltage</td><td>1.10 V</td></tr>"
            "</tbody></table>"
        )
    return "<div class=\"detail\">" + "".join(parts) + "</div>"


def _document_cc96(
    *,
    chrome: int = CC_PAGE_CHROME_ELEMENTS,
    description: str | None = None,
    table_row: bool = True,
    inline_span: bool = True,
    inert_body: bool = False,
) -> str:
    body = _chrome_spans(chrome)
    if inert_body:
        body += "<p>Server memory modules from trusted brands.</p>"
    elif inline_span or table_row:
        body += _cc96_visible_detail(table_row=table_row, inline_span=inline_span)
    return "<html><head>" + _json_ld(_cc96_product_node(description)) + "</head><body>" + body + "</body></html>"


def _so_product_node(description: str | None = None) -> dict:
    """The recorded SO JSON-LD shape: SKU equals the requested MPN, price 0, NEW."""
    node = {
        "@context": "http://schema.org/",
        "@type": "http://schema.org/Product",
        "brand": {"@type": "Brand", "name": "Seagate"},
        "name": (
            "Seagate " + SO_MPN + " nytro 5350H 15.36tb RI PCI Express Gen4 x4 "
            "NVMe 2.5 inch 15mm Solid State Drive. New Sealed in Box (NIB) "
            "with 3 years Warranty"
        ),
        "sku": SO_MPN,
        "offers": [
            {
                "@type": "http://schema.org/Offer",
                "availability": "InStock",
                "price": 0,
                "priceCurrency": "USD",
                "itemCondition": "https://schema.org/NewCondition",
            }
        ],
    }
    if description is not None:
        node["description"] = description
    return node


def _so_description_text() -> str:
    """The recorded SO JSON-LD ``description``: labeled text inside a script."""
    return (
        "Main Details of Seagate 15.36TB Gen4 SSD\n"
        "Brand Details\n"
        "Brand: Seagate\n"
        "Model Number: " + SO_MPN + "\n"
        "Drive Type: Internal Solid State Drive\n"
        "Technical Specifications\n"
    )


def _so_visible_features() -> str:
    """The recorded SO visible feature block: a non-approved ``SKU/MPN`` label."""
    return (
        "<div class=\"ty-features-list\">"
        "<span class=\"ty-control-group\" data-feature-id=\"mpn\">"
        "<span class=\"ty-product-feature__label\">SKU/MPN</span>"
        "<span><em><b>" + SO_MPN + "</b></em></span>"
        "</span>"
        "</div>"
    )


def _so_visible_description_list() -> str:
    return (
        "<h3>Brand Details</h3><ul>"
        "<li><strong>Brand:</strong> Seagate</li>"
        "<li><strong>Model Number:</strong> " + SO_MPN + "</li>"
        "<li><strong>Drive Type:</strong> Internal Solid State Drive</li>"
        "</ul>"
    )


def _document_so(
    *,
    description: str | None = None,
    visible_label: bool = True,
) -> str:
    body = _so_visible_features()
    if visible_label:
        body += _so_visible_description_list()
    return "<html><head>" + _json_ld(_so_product_node(description)) + "</head><body>" + body + "</body></html>"


class TestVisibleMpnCaptureBound:
    """The verified product-page scale must pass the capture bound."""

    def test_recorded_product_page_scale_is_not_refused_by_the_bound(self) -> None:
        """2,700 chrome leaves (the verified CC scale) no longer erase evidence."""
        observation = _extract(_document_cc96())[0]

        assert observation.extraction_method is ExtractionMethod.JSON_LD_WITH_VISIBLE_MPN
        assert observation.manufacturer_part_number_text == CC96_MPN
        # The structured offer data is preserved exactly as published.
        assert observation.sku_text == CC96_SKU
        assert observation.price_text == CC96_PRICE
        assert observation.currency_text == "USD"
        assert observation.brand_text == "Samsung"
        assert observation.product_title == CC96_TITLE

    def test_pathological_element_proliferation_still_fails_closed(self) -> None:
        """A page above the bound is still refused for visible identity."""
        # 16,390 inert leaves saturate the 16,384 bound; the labeled detail
        # published after the chrome is never captured — the bound's
        # fail-closed response (no visible identity evidence at all) stands.
        document = (
            "<html><head>" + _json_ld(_cc96_product_node()) + "</head><body>"
            + _chrome_spans(16390)
            + _cc96_visible_detail()
            + "</body></html>"
        )

        observation = _extract(document)[0]

        assert observation.manufacturer_part_number_text is None
        assert observation.extraction_method is ExtractionMethod.JSON_LD
        # The structured offer survives the identity refusal.
        assert observation.price_text == CC96_PRICE
        assert observation.sku_text == CC96_SKU

    def test_bound_refusal_is_identity_only_never_offer_data(self) -> None:
        """Refusal touches only the missing-MPN enrichment, not the offer."""
        document = (
            "<html><head>" + _json_ld(_cc96_product_node()) + "</head><body>"
            + _chrome_spans(16390)
            + "</body></html>"
        )

        observations = _extract(document)

        assert len(observations) == 1
        assert observations[0].extraction_method is ExtractionMethod.JSON_LD
        assert observations[0].manufacturer_part_number_text is None
        assert observations[0].price_text == CC96_PRICE
        assert observations[0].currency_text == "USD"
        assert observations[0].availability_text == "https://schema.org/InStock"
        assert observations[0].condition_text is None


class TestVisibleDefinitionTablePair:
    """The verified definition-table shape: td label cell, td value cell."""

    def test_recorded_cc_table_row_captures_the_visible_mpn(self) -> None:
        observation = _extract(_document_cc96(inline_span=False, chrome=0))[0]

        assert observation.manufacturer_part_number_text == CC96_MPN
        assert observation.extraction_method is ExtractionMethod.JSON_LD_WITH_VISIBLE_MPN
        assert observation.sku_text == CC96_SKU
        assert observation.price_text == CC96_PRICE

    def test_inline_span_and_table_row_agreeing_is_not_a_conflict(self) -> None:
        """The real CC page publishes both lines; same value = one evidence."""
        observation = _extract(_document_cc96(chrome=0))[0]

        assert observation.manufacturer_part_number_text == CC96_MPN
        assert observation.extraction_method is ExtractionMethod.JSON_LD_WITH_VISIBLE_MPN

    def test_table_label_and_value_in_separate_rows_do_not_pair(self) -> None:
        document = (
            "<html><head>" + _json_ld(_cc96_product_node()) + "</head><body>"
            "<table><tbody>"
            f"<tr><td>Manufacturer Part Number</td></tr>"
            f"<tr><td>{CC96_MPN}</td></tr>"
            "</tbody></table>"
            + "</body></html>"
        )

        observation = _extract(document)[0]
        assert observation.manufacturer_part_number_text is None
        assert observation.extraction_method is ExtractionMethod.JSON_LD

    def test_table_label_with_non_identifier_value_does_not_pair(self) -> None:
        document = (
            "<html><head>" + _json_ld(_cc96_product_node()) + "</head><body>"
            "<table><tbody>"
            "<tr><td>Manufacturer Part Number</td><td>See product page</td></tr>"
            "</tbody></table>"
            + "</body></html>"
        )

        observation = _extract(document)[0]
        assert observation.manufacturer_part_number_text is None

    def test_retailer_table_labels_do_not_gain_mpn_authority(self) -> None:
        document = (
            "<html><head>" + _json_ld(_cc96_product_node()) + "</head><body>"
            "<table><tbody>"
            f"<tr><td>Item #</td><td>{CC96_SKU}</td></tr>"
            f"<tr><td>SKU</td><td>{CC96_SKU}</td></tr>"
            "<tr><td>Product Name</td><td>RAM Module</td></tr>"
            "</tbody></table>"
            + "</body></html>"
        )

        observation = _extract(document)[0]
        assert observation.manufacturer_part_number_text is None
        assert observation.sku_text == CC96_SKU
        assert observation.extraction_method is ExtractionMethod.JSON_LD

    def test_conflicting_visible_values_still_fail_closed(self) -> None:
        document = (
            "<html><head>" + _json_ld(_cc96_product_node()) + "</head><body>"
            "<table><tbody>"
            f"<tr><td>Manufacturer Part Number</td><td>{CC96_MPN}</td></tr>"
            "</tbody></table>"
            "<div>Model #: " + CC64_MPN + "</div>"
            + "</body></html>"
        )

        observation = _extract(document)[0]
        assert observation.manufacturer_part_number_text is None
        assert observation.extraction_method is ExtractionMethod.JSON_LD


class TestJsonLdDescriptionTextIsNotVisibleEvidence:
    """A label inside a <script> is script text, not a visible field.

    This is the critical boundary from the task evidence: the recorded CC and
    SO pages carry their labeled MPN in the JSON-LD ``description``. That text
    alone never establishes manufacturer-MPN authority.
    """

    def test_cc_description_table_alone_does_not_enrich(self) -> None:
        observation = _extract(
            _document_cc96(
                description=_cc96_description_table(),
                inline_span=False,
                table_row=False,
                inert_body=True,
            )
        )[0]

        assert observation.manufacturer_part_number_text is None
        assert observation.extraction_method is ExtractionMethod.JSON_LD
        assert observation.sku_text == CC96_SKU
        assert observation.price_text == CC96_PRICE

    def test_so_description_text_alone_does_not_enrich(self) -> None:
        observation = _extract(
            _document_so(description=_so_description_text(), visible_label=False)
        )[0]

        assert observation.manufacturer_part_number_text is None
        assert observation.extraction_method is ExtractionMethod.JSON_LD
        # The SKU equal to the requested MPN stays a SKU: no promotion.
        assert observation.sku_text == SO_MPN


class TestFrozenPipelineOverVerifiedShapes:
    """3B / 3C / 4A over the verified shapes — the frozen authorities decide."""

    def _cc96_pipeline(self, requested_mpn: str) -> tuple:
        request = ResearchRequest(
            manufacturer_part_number=requested_mpn,
            description="Samsung DDR5-6400 ECC RDIMM server module memory",
        )
        normalized = normalize_listing_observations(_extract(_document_cc96()))
        assessments = assess_listing_identities(request, normalized)
        result = aggregate_listing_prices(request, assessments)
        return request, normalized, assessments, result

    def test_cc96_visible_mpn_is_accepted_by_the_frozen_3c_policy(self) -> None:
        request, normalized, assessments, _ = self._cc96_pipeline(CC96_MPN)

        assessment = assessments[0]
        assert assessment.decision is EvidenceDecision.ACCEPTED
        assert assessment.match_type is IdentityMatchType.EXACT
        assert assessment.candidate_evidence_source is EvidenceSource.VISIBLE_LABELED_MPN_FIELD
        assert assessment.candidate_part_number_raw == CC96_MPN
        # The observation carries the bounded visible provenance.
        assert normalized[0].observation.extraction_method is ExtractionMethod.JSON_LD_WITH_VISIBLE_MPN

    def test_cc96_unknown_condition_remains_quote_only_never_new(self) -> None:
        """Condition is absent on the recorded page: UNKNOWN, and stays out of 4A."""
        _, normalized, _, result = self._cc96_pipeline(CC96_MPN)

        assert normalized[0].condition is NormalizedCondition.UNKNOWN
        assert normalized[0].price_amount == Decimal(CC96_PRICE)
        assert normalized[0].currency_code == "USD"
        # 4A: no bucket, recorded exclusion, never silently NEW.
        assert result.buckets == ()
        assert len(result.exclusions) == 1
        assert result.exclusions[0].reason is PriceAggregationExclusionReason.UNKNOWN_CONDITION

    def test_cc96_accepted_listing_is_not_human_review_eligible(self) -> None:
        """Frozen FU3B eligibility: a deterministic ACCEPTED needs no review."""
        _, _, assessments, _ = self._cc96_pipeline(CC96_MPN)

        assert is_human_review_eligible_assessment(assessments[0]) is False

    def test_cross_cc_mpn_request_is_mismatched_not_accepted(self) -> None:
        """The 64 GB request against the 96 GB page: mismatch, never acceptance."""
        request, _, assessments, result = self._cc96_pipeline(CC64_MPN)

        assessment = assessments[0]
        assert assessment.decision is EvidenceDecision.REJECTED
        assert assessment.rejection_reason.value == "MPN_MISMATCH"
        assert assessment.match_type is IdentityMatchType.UNKNOWN
        # The captured candidate is still recorded — evidence, never identity.
        assert assessment.candidate_evidence_source is EvidenceSource.VISIBLE_LABELED_MPN_FIELD
        assert assessment.candidate_part_number_raw == CC96_MPN
        assert is_human_review_eligible_assessment(assessment) is False
        # 4A: identity-refused, before any price consideration.
        assert result.buckets == ()
        assert result.exclusions[0].reason is PriceAggregationExclusionReason.IDENTITY_NOT_ACCEPTED

    def test_sku_equal_to_requested_mpn_without_visible_label_stays_rejected(self) -> None:
        """The recorded SO shape minus the visible label: SKU is never MPN."""
        request = ResearchRequest(
            manufacturer_part_number=SO_MPN,
            description="Seagate Nytro 5350H 15.36TB read-intensive NVMe SSD",
        )
        normalized = normalize_listing_observations(
            _extract(_document_so(visible_label=False))
        )
        assessments = assess_listing_identities(request, normalized)
        result = aggregate_listing_prices(request, assessments)

        assessment = assessments[0]
        assert assessment.decision is EvidenceDecision.REJECTED
        assert assessment.candidate_evidence_source is EvidenceSource.SKU_FIELD
        assert assessment.rejection_reason.value == "NO_EXPLICIT_MPN_EVIDENCE"
        # Frozen FU3B eligibility for this recorded shape is unchanged.
        assert is_human_review_eligible_assessment(assessment) is True
        assert result.buckets == ()
        assert result.exclusions[0].reason is PriceAggregationExclusionReason.IDENTITY_NOT_ACCEPTED

    def test_so_visible_model_number_flows_over_the_published_values(self) -> None:
        """Case B adjudication: the current extractor already captures SO.

        The published price is ``0`` and the published condition is NEW; the
        frozen 3B/4A authorities process those published values unchanged.
        """
        request = ResearchRequest(
            manufacturer_part_number=SO_MPN,
            description="Seagate Nytro 5350H 15.36TB read-intensive NVMe SSD",
        )
        normalized = normalize_listing_observations(_extract(_document_so()))
        assessments = assess_listing_identities(request, normalized)
        result = aggregate_listing_prices(request, assessments)

        assessment = assessments[0]
        assert assessment.decision is EvidenceDecision.ACCEPTED
        assert assessment.match_type is IdentityMatchType.EXACT
        assert assessment.candidate_evidence_source is EvidenceSource.VISIBLE_LABELED_MPN_FIELD
        assert assessment.candidate_part_number_raw == SO_MPN

        listing = normalized[0]
        assert listing.price_amount == Decimal("0")
        assert listing.currency_code == "USD"
        assert listing.condition is NormalizedCondition.NEW

        assert len(result.buckets) == 1
        bucket = result.buckets[0]
        assert bucket.currency_code == "USD"
        assert bucket.condition is NormalizedCondition.NEW
        assert bucket.count == 1
        assert bucket.low == bucket.median == bucket.high == Decimal("0")
        # One observed value is not a market range: frozen 4A keeps it None.
        assert bucket.market_range_low is None
        assert bucket.market_range_high is None


# ---------------------------------------------------------------------------
# PRODUCT-INTEL.PILOT-VALUE-EVIDENCE-A1-FU1 — declared non-primary regions
# ---------------------------------------------------------------------------
# The independent review HOLD on A1 reproduced an unsafe cross-product
# association: once the capture bound admitted the page, an unrelated
# recommendation ``<aside>`` publishing its OWN product's
# ``Manufacturer Part Number`` row was read as the main product's MPN
# (``OTHER-22`` assigned to MAIN PRODUCT A at the main product's own 299 USD
# price, method ``JSON_LD_WITH_VISIBLE_MPN``). The correction is bounded and
# declarative: regions the page itself marks non-primary (``<nav>``,
# ``<aside>``, ``role="navigation"``, ``role="complementary"``) are not
# eligible main-product identity evidence. Exclusion keys on the declaration,
# never on a CSS class, and fails closed: it can remove a wrong MPN, never
# add one.
ADVERSARIAL_SIDEBAR_MPN = "OTHER-22"
ADVERSARIAL_MAIN_MPN = "MAIN-777"
# More than the pre-A1 2,048 capture bound, so the original FU2 extractor
# erased the whole page (no MPN) while the A1-FU1 extractor must still refuse
# the sidebar and preserve the main product's structured offer.
ADVERSARIAL_NAV_ELEMENTS = 2200


def _main_product_node() -> dict:
    """The adversarial main product: retailer SKU, 299 USD, NEW, no ``mpn``."""
    return {
        "@context": "https://schema.org",
        "@type": "Product",
        "name": "MAIN PRODUCT A",
        "sku": "MAIN-SKU-1",
        "offers": {
            "@type": "Offer",
            "price": "299",
            "priceCurrency": "USD",
            "itemCondition": "https://schema.org/NewCondition",
            "availability": "https://schema.org/InStock",
        },
    }


def _nav_chrome(count: int) -> str:
    """Ordinary unlabeled navigation leaves preceding the product content."""
    return "".join(f"<span>nav{i:05d}</span>" for i in range(count))


def _recommendation_sidebar(tag: str = "aside", attrs: str = ' class="recommended"') -> str:
    """The unrelated recommendation region with its own labeled MPN row."""
    return (
        f"<{tag}{attrs}>"
        "<h3>Other product</h3>"
        "<table><tr><td>Manufacturer Part Number</td><td>"
        + ADVERSARIAL_SIDEBAR_MPN
        + "</td></tr></table>"
        f"</{tag}>"
    )


def _document_adversarial(
    *,
    nav: int = ADVERSARIAL_NAV_ELEMENTS,
    sidebar: str | None = None,
    main_visible_mpn: str | None = None,
) -> str:
    """The exact blocking repro: MAIN PRODUCT A + chrome + recommendation rail.

    ``sidebar`` defaults to the recommendation ``<aside>``.
    ``main_visible_mpn`` optionally publishes the main product's OWN labeled
    MPN in the primary region (recall-preservation case).
    """
    if sidebar is None:
        sidebar = _recommendation_sidebar()

    main_region = '<div class="main-product"><h1>MAIN PRODUCT A</h1>'
    if main_visible_mpn is not None:
        main_region += (
            "<table><tr><td>Manufacturer Part Number</td><td>"
            + main_visible_mpn
            + "</td></tr></table>"
        )
    main_region += "<p>Primary product details.</p></div>"

    body = _nav_chrome(nav) + main_region + sidebar
    return (
        "<html><head>"
        + _json_ld(_main_product_node())
        + "</head><body>"
        + body
        + "</body></html>"
    )


class TestDeclaredNonPrimaryRegionExclusion:
    """A1-FU1: other-product evidence in declared non-primary regions."""

    def test_recommendation_sidebar_mpn_is_never_assigned_to_main_product(
        self,
    ) -> None:
        """The exact blocking repro: >2,048 nav leaves + a labeled ``<aside>``.

        Negative regression: the unrelated ``OTHER-22`` is never assigned to
        MAIN PRODUCT A. The mixed-provenance method must not appear, and the
        main product's own structured offer (299 USD / NEW / SKU) is
        preserved untouched.
        """
        observation = _extract(_document_adversarial())[0]

        assert observation.manufacturer_part_number_text is None
        assert observation.manufacturer_part_number_text != ADVERSARIAL_SIDEBAR_MPN
        assert observation.extraction_method is ExtractionMethod.JSON_LD
        assert observation.product_title == "MAIN PRODUCT A"
        assert observation.sku_text == "MAIN-SKU-1"
        assert observation.price_text == "299"
        assert observation.currency_text == "USD"
        assert observation.condition_text == "https://schema.org/NewCondition"
        assert observation.availability_text == "https://schema.org/InStock"

    def test_sidebar_exclusion_is_not_a_function_of_the_capture_bound(
        self,
    ) -> None:
        """The same labeled ``<aside>`` with zero chrome: still not main evidence.

        The declaration, not the element count, is what excludes the region.
        """
        observation = _extract(_document_adversarial(nav=0))[0]

        assert observation.manufacturer_part_number_text is None
        assert observation.extraction_method is ExtractionMethod.JSON_LD

    def test_region_exclusion_does_not_require_a_css_class(self) -> None:
        """An ``<aside>`` with no class attribute at all is still excluded."""
        observation = _extract(
            _document_adversarial(
                nav=0, sidebar=_recommendation_sidebar(tag="aside", attrs="")
            )
        )[0]

        assert observation.manufacturer_part_number_text is None
        assert observation.extraction_method is ExtractionMethod.JSON_LD

    def test_navigation_region_labels_are_not_main_product_evidence(
        self,
    ) -> None:
        """A declared ``<nav>`` publishing a labeled part number is excluded."""
        document = (
            "<html><head>"
            + _json_ld(_main_product_node())
            + "</head><body>"
            + "<nav><h3>Catalog</h3><table><tr>"
            f"<td>Manufacturer Part Number</td><td>{ADVERSARIAL_SIDEBAR_MPN}"
            "</td></tr></table></nav>"
            + '<div class="main-product"><h1>MAIN PRODUCT A</h1>'
            "<p>Primary product details.</p></div>"
            + "</body></html>"
        )

        observation = _extract(document)[0]
        assert observation.manufacturer_part_number_text is None
        assert observation.extraction_method is ExtractionMethod.JSON_LD

    def test_role_navigation_declaration_excludes_the_same_evidence(
        self,
    ) -> None:
        """``role="navigation"`` carries the declaration on a plain element."""
        document = (
            "<html><head>"
            + _json_ld(_main_product_node())
            + "</head><body>"
            + '<div role="navigation"><table><tr>'
            f"<td>Manufacturer Part Number</td><td>{ADVERSARIAL_SIDEBAR_MPN}"
            "</td></tr></table></div>"
            + "</body></html>"
        )

        observation = _extract(document)[0]
        assert observation.manufacturer_part_number_text is None
        assert observation.extraction_method is ExtractionMethod.JSON_LD

    def test_role_complementary_declaration_excludes_the_same_evidence(
        self,
    ) -> None:
        """``role="complementary"`` carries the declaration on a plain element."""
        document = (
            "<html><head>"
            + _json_ld(_main_product_node())
            + "</head><body>"
            + '<div role="complementary"><table><tr>'
            f"<td>Manufacturer Part Number</td><td>{ADVERSARIAL_SIDEBAR_MPN}"
            "</td></tr></table></div>"
            + "</body></html>"
        )

        observation = _extract(document)[0]
        assert observation.manufacturer_part_number_text is None
        assert observation.extraction_method is ExtractionMethod.JSON_LD

    def test_main_product_labeled_mpn_still_recovers_with_sidebar_present(
        self,
    ) -> None:
        """Primary-region evidence wins; the sidebar is invisible to it.

        Without the exclusion, the main label and the sidebar label would
        disagree and the page would fail closed to no MPN. With it, the
        sidebar never enters the stream, so the main product's own labeled
        MPN recovers — and ``OTHER-22`` can neither be chosen nor counted as
        a conflict. This is the recall-preservation half of the contract.
        """
        observation = _extract(
            _document_adversarial(main_visible_mpn=ADVERSARIAL_MAIN_MPN)
        )[0]

        assert observation.manufacturer_part_number_text == ADVERSARIAL_MAIN_MPN
        assert observation.manufacturer_part_number_text != ADVERSARIAL_SIDEBAR_MPN
        assert observation.extraction_method is ExtractionMethod.JSON_LD_WITH_VISIBLE_MPN
        # The structured offer is still untouched by the enrichment.
        assert observation.price_text == "299"
        assert observation.sku_text == "MAIN-SKU-1"

    def test_sidebar_mpn_request_is_rejected_against_main_product_observation(
        self,
    ) -> None:
        """End-to-end negative over the frozen 3C policy.

        A request for the OTHER product's MPN against MAIN PRODUCT A's page
        yields no acceptance: the sidebar value never reached the main
        product's observation, so there is no explicit MPN candidate at all.
        """
        request = ResearchRequest(
            manufacturer_part_number=ADVERSARIAL_SIDEBAR_MPN,
            description="unrelated recommendation product",
        )
        normalized = normalize_listing_observations(_extract(_document_adversarial()))
        assessments = assess_listing_identities(request, normalized)

        assert assessments[0].decision is EvidenceDecision.REJECTED
        assert assessments[0].rejection_reason.value == "NO_EXPLICIT_MPN_EVIDENCE"
        # The only candidate is the main product's own retailer SKU —
        # never the sidebar's OTHER-22.
        assert assessments[0].candidate_evidence_source is EvidenceSource.SKU_FIELD
        assert assessments[0].candidate_part_number_raw == "MAIN-SKU-1"


# ---------------------------------------------------------------------------
# PRODUCT-INTEL.PILOT-VALUE-EVIDENCE-A1-FU2 — structural barriers and the
# primary-product evidence association
# ---------------------------------------------------------------------------
# The independent A1-FU1 review held the correction with two authority
# regressions, both reproduced verbatim by the documents below:
#
# BLOCKER 1 — the declared non-primary exclusion FILTERS excluded elements
# out of the evidence stream, and the pairing pass read "next recorded
# element with the same parent" as "sibling". Removing the ``<aside>`` from
# the stream collapsed a DOM gap: a label span and a value span that are NOT
# siblings (an aside sits between them) paired anyway, and ``WRONG-33`` was
# recovered as the visible manufacturer MPN. Corrected: every unrecorded
# element — an excluded region, a container, an over-long element — is a
# structural barrier; a split label and value pair only when the value's
# immediately preceding recorded DOM sibling is the label.
#
# BLOCKER 2 — a recommendation rail the page does NOT declare
# (``<div class="recommended"><span>Model #: OTHER-22</span></div>``) after
# 2,200 ordinary navigation leaves: pristine FU2 returned no MPN (the 2,048
# capture bound erased the page), A1-FU1 assigned ``OTHER-22`` to the primary
# product (the 16,384 bound admitted the rail). No CSS class may be read as a
# trust signal, so the correction is the primary-product ASSOCIATION
# contract: when the document declares a primary region (``<main>`` /
# ``role="main"``), visible identity evidence is eligible only from inside it;
# when it declares none, the FU2 page-level single-product contract applies
# and an undeclared labeled field is associated with the primary product only
# through an exact page-published co-reference — its value equals a published
# identifier (SKU / title), the page re-publishes a published identifier in a
# visible ``Item #``/``SKU`` field, the field shares a non-document block
# container with a visible occurrence of the published title, or the visible
# body contains nothing but the product's own fields (other rows of the same
# specification table included). A labeled value with no such association is
# another product's evidence and fails closed to no MPN.
BARRIER_WRONG_MPN = "WRONG-33"
BARRIER_GOOD_MPN = "GOOD-44"
BARRIER_BAD_MPN = "BAD-55"


def _product_node(name: str, sku: str) -> dict:
    """A primary product node: title + retailer SKU + 299 USD, no ``mpn``."""
    return {
        "@context": "https://schema.org",
        "@type": "Product",
        "name": name,
        "sku": sku,
        "offers": {
            "@type": "Offer",
            "price": "299",
            "priceCurrency": "USD",
            "itemCondition": "https://schema.org/NewCondition",
            "availability": "https://schema.org/InStock",
        },
    }


def _barrier_document(*, in_main: bool = False) -> str:
    """BLOCKER 1 verbatim: label span, an <aside> between, value span."""
    inner = (
        "<div>"
        "<span>Manufacturer Part Number</span>"
        "<aside><span>" + ADVERSARIAL_SIDEBAR_MPN + "</span></aside>"
        "<span>" + BARRIER_WRONG_MPN + "</span>"
        "</div>"
    )
    body = "<main>" + inner + "</main>" if in_main else inner
    return (
        "<html><head>"
        + _json_ld(_main_product_node())
        + "</head><body>"
        + body
        + "</body></html>"
    )


def _undeclared_recommendation_document(*, nav: int = ADVERSARIAL_NAV_ELEMENTS,
                                        wrap: bool = False) -> str:
    """BLOCKER 2: ordinary (undeclared) nav leaves + an undeclared rail."""
    chrome = _nav_chrome(nav)
    rail = (
        '<div class="recommended"><span>Model #: '
        + ADVERSARIAL_SIDEBAR_MPN
        + "</span></div>"
    )
    body = chrome + rail
    if wrap:
        body = "<div>" + body + "</div>"
    return (
        "<html><head>"
        + _json_ld(_main_product_node())
        + "</head><body>"
        + body
        + "</body></html>"
    )


class TestExcludedRegionStructuralBarrier:
    """A1-FU2 blocker 1: excluded regions are pairing barriers, not holes."""

    def test_excluded_region_between_label_and_value_does_not_pair(self) -> None:
        """BLOCKER 1 verbatim — the aside sits between the label and the
        value in the DOM; removing it must not manufacture the pairing.

        Fails before the correction (A1-FU1 recovered ``WRONG-33``), passes
        after: no MPN, plain structured method, offer untouched.
        """
        observation = _extract(_barrier_document())[0]

        assert observation.manufacturer_part_number_text is None
        assert observation.manufacturer_part_number_text != BARRIER_WRONG_MPN
        assert observation.extraction_method is ExtractionMethod.JSON_LD
        assert observation.price_text == "299"
        assert observation.sku_text == "MAIN-SKU-1"

    def test_barrier_holds_even_inside_a_declared_primary_region(self) -> None:
        """The same DOM gap inside ``<main>``: the association is fully open
        here (the region is declared primary), so only the structural
        barrier can stop the pairing. Fails before the correction.
        """
        observation = _extract(_barrier_document(in_main=True))[0]

        assert observation.manufacturer_part_number_text is None
        assert observation.extraction_method is ExtractionMethod.JSON_LD
        assert observation.price_text == "299"

    def test_true_siblings_still_pair_when_an_excluded_region_is_elsewhere(
        self,
    ) -> None:
        """Guard: the barrier is at the gap, not global. A genuine
        adjacent cell pair in the spec table still recovers while an
        unrelated aside sits elsewhere in the same declared region.
        """
        document = (
            "<html><head>"
            + _json_ld(_main_product_node())
            + "</head><body><main>"
            "<table><tr><td>Manufacturer Part Number</td><td>"
            + BARRIER_GOOD_MPN
            + "</td></tr></table>"
            "<aside><span>" + ADVERSARIAL_SIDEBAR_MPN + "</span></aside>"
            "</main></body></html>"
        )

        observation = _extract(document)[0]
        assert observation.manufacturer_part_number_text == BARRIER_GOOD_MPN
        assert observation.extraction_method is ExtractionMethod.JSON_LD_WITH_VISIBLE_MPN

    def test_unrecorded_content_between_label_and_value_does_not_pair(self) -> None:
        """No excluded region at all: an unrecorded container (an empty div
        holding only a void element) between the label and the value is the
        same DOM gap and the same barrier. Fails before the correction.
        """
        document = (
            "<html><head>"
            + _json_ld(_main_product_node())
            + "</head><body><div>"
            "<span>Manufacturer Part Number</span>"
            '<div><img src="x.png"></div>'
            "<span>" + BARRIER_WRONG_MPN + "</span>"
            "</div></body></html>"
        )

        observation = _extract(document)[0]
        assert observation.manufacturer_part_number_text is None
        assert observation.extraction_method is ExtractionMethod.JSON_LD

    def test_overlong_element_between_label_and_value_does_not_pair(self) -> None:
        """An over-long (unrecorded) element between the label and the value
        is a barrier too. Fails before the correction.
        """
        document = (
            "<html><head>"
            + _json_ld(_main_product_node())
            + "</head><body><div>"
            "<span>Manufacturer Part Number</span>"
            "<span>" + "x" * 300 + "</span>"
            "<span>" + BARRIER_WRONG_MPN + "</span>"
            "</div></body></html>"
        )

        observation = _extract(document)[0]
        assert observation.manufacturer_part_number_text is None
        assert observation.extraction_method is ExtractionMethod.JSON_LD


class TestPrimaryProductAssociation:
    """A1-FU2 blocker 2: which product an undeclared visible label is about."""

    def test_undeclared_recommendation_mpn_is_never_assigned_to_primary_product(
        self,
    ) -> None:
        """BLOCKER 2 verbatim — 2,200 ordinary navigation leaves, then an
        undeclared recommendation div carrying ``Model #: OTHER-22``; the
        primary JSON-LD Product has a retailer SKU and 299 USD but no MPN.

        Fails before the correction (A1-FU1 assigned ``OTHER-22``); pristine
        FU2 also returned no MPN. The offer is preserved untouched.
        """
        observation = _extract(_undeclared_recommendation_document())[0]

        assert observation.manufacturer_part_number_text is None
        assert observation.manufacturer_part_number_text != ADVERSARIAL_SIDEBAR_MPN
        assert observation.extraction_method is ExtractionMethod.JSON_LD
        assert observation.product_title == "MAIN PRODUCT A"
        assert observation.sku_text == "MAIN-SKU-1"
        assert observation.price_text == "299"
        assert observation.currency_text == "USD"
        assert observation.condition_text == "https://schema.org/NewCondition"
        assert observation.availability_text == "https://schema.org/InStock"

    def test_undeclared_recommendation_is_refused_at_any_chrome_scale(self) -> None:
        """Two nav leaves instead of 2,200: the association is not a function
        of the element count. Fails before the correction.
        """
        observation = _extract(_undeclared_recommendation_document(nav=2))[0]

        assert observation.manufacturer_part_number_text is None
        assert observation.extraction_method is ExtractionMethod.JSON_LD

    def test_recommendation_sharing_a_wrapper_div_with_chrome_is_refused(self) -> None:
        """Chrome and the rail share one arbitrary wrapper div: a wrapper is
        not a product region (region coverage is scoped to tables), so the
        rail is still unassociated. Fails before the correction.
        """
        observation = _extract(_undeclared_recommendation_document(nav=2, wrap=True))[0]

        assert observation.manufacturer_part_number_text is None
        assert observation.extraction_method is ExtractionMethod.JSON_LD

    def test_visible_labeled_value_equal_to_structured_sku_is_associated(self) -> None:
        """The recorded ServerOrbit adjudication at chrome scale: the page
        declares no region, but the labeled value exactly equals the SKU the
        structured product published — the page's own co-reference.
        """
        document = (
            "<html><head>"
            + _json_ld(_product_node("SOLO DRIVE", "SKUV-1"))
            + "</head><body>"
            + _nav_chrome(50)
            + "<div>Model #: SKUV-1</div>"
            + "</body></html>"
        )

        observation = _extract(document)[0]
        assert observation.manufacturer_part_number_text == "SKUV-1"
        assert observation.extraction_method is ExtractionMethod.JSON_LD_WITH_VISIBLE_MPN
        assert observation.sku_text == "SKUV-1"
        assert observation.price_text == "299"

    def test_visible_identifier_field_republishing_the_structured_sku_anchors(
        self,
    ) -> None:
        """The page visibly re-publishes its own structured SKU in a
        retailer-identifier field (``Item #:``) in the same bounded
        product-detail container as the labeled MPN field (the recorded
        layout, per the FU3 adjudication fixture-fidelity correction);
        the undeclared labeled MPN field is associated with the primary
        product.
        """
        document = (
            "<html><head>"
            + _json_ld(_product_node("SOLO DRIVE", "ANCHOR-SKU"))
            + "</head><body>"
            + _nav_chrome(50)
            + "<div>"
            + "<div>Model #: ANCHOR-MPN</div>"
            + "<span>Item #:</span><span>ANCHOR-SKU</span>"
            + "</div>"
            + "</body></html>"
        )

        observation = _extract(document)[0]
        assert observation.manufacturer_part_number_text == "ANCHOR-MPN"
        assert observation.extraction_method is ExtractionMethod.JSON_LD_WITH_VISIBLE_MPN
        assert observation.sku_text == "ANCHOR-SKU"

    def test_visible_title_in_the_same_container_anchors_the_field(self) -> None:
        """A visible occurrence of the product's own published title in the
        same container as the labeled field associates the field (the
        F6 shape: chrome + titled spec block).
        """
        document = (
            "<html><head>"
            + _json_ld(_main_product_node())
            + "</head><body>"
            + _nav_chrome(50)
            + '<div><h1>MAIN PRODUCT A</h1><table><tr>'
            "<td>Manufacturer Part Number</td><td>TITLED-1</td>"
            "</tr></table></div>"
            + "</body></html>"
        )

        observation = _extract(document)[0]
        assert observation.manufacturer_part_number_text == "TITLED-1"
        assert observation.extraction_method is ExtractionMethod.JSON_LD_WITH_VISIBLE_MPN

    def test_visible_title_in_a_different_container_does_not_associate(self) -> None:
        """The title sits in a DIFFERENT container (the whole body is not a
        region): the rail is still unassociated. Fails before the
        correction (A1-FU1 assigned ``OTHER-22``).
        """
        document = (
            "<html><head>"
            + _json_ld(_main_product_node())
            + "</head><body>"
            + _nav_chrome(50)
            + '<div><h1>MAIN PRODUCT A</h1></div>'
            + '<div class="recommended"><span>Model #: '
            + ADVERSARIAL_SIDEBAR_MPN
            + "</span></div>"
            + "</body></html>"
        )

        observation = _extract(document)[0]
        assert observation.manufacturer_part_number_text is None
        assert observation.extraction_method is ExtractionMethod.JSON_LD

    def test_primary_region_scopes_eligible_evidence_and_conflict_cannot_veto(
        self,
    ) -> None:
        """A declared primary region scopes eligibility: the conflicting
        undeclared field outside ``<main>`` is not primary-product evidence
        and cannot veto the field inside it. Fails before the correction
        (A1-FU1 saw both values and failed closed to no MPN).
        """
        document = (
            "<html><head>"
            + _json_ld(_main_product_node())
            + "</head><body>"
            + _nav_chrome(50)
            + "<main><table><tr><td>Manufacturer Part Number</td><td>"
            + BARRIER_GOOD_MPN
            + "</td></tr></table></main>"
            + "<div>Model #: " + BARRIER_BAD_MPN + "</div>"
            + "</body></html>"
        )

        observation = _extract(document)[0]
        assert observation.manufacturer_part_number_text == BARRIER_GOOD_MPN
        assert observation.extraction_method is ExtractionMethod.JSON_LD_WITH_VISIBLE_MPN

    def test_role_main_declaration_scopes_the_same_way(self) -> None:
        """``role="main"`` carries the primary declaration on a plain
        element, exactly as the ``<main>`` element does.
        """
        document = (
            "<html><head>"
            + _json_ld(_main_product_node())
            + "</head><body>"
            + _nav_chrome(50)
            + '<div role="main"><table><tr><td>Manufacturer Part Number</td><td>'
            + BARRIER_GOOD_MPN
            + "</td></tr></table></div>"
            + "<div>Model #: " + BARRIER_BAD_MPN + "</div>"
            + "</body></html>"
        )

        observation = _extract(document)[0]
        assert observation.manufacturer_part_number_text == BARRIER_GOOD_MPN
        assert observation.extraction_method is ExtractionMethod.JSON_LD_WITH_VISIBLE_MPN

    def test_labeled_field_outside_declared_primary_region_is_never_assigned(
        self,
    ) -> None:
        """The document declares where the primary product lives; a labeled
        field outside that region is not primary-product evidence even when
        it is the page's only labeled field. Fails before the correction.
        """
        document = (
            "<html><head>"
            + _json_ld(_main_product_node())
            + "</head><body>"
            + _nav_chrome(50)
            + "<main><p>Primary product details.</p></main>"
            + "<div>Model #: " + ADVERSARIAL_SIDEBAR_MPN + "</div>"
            + "</body></html>"
        )

        observation = _extract(document)[0]
        assert observation.manufacturer_part_number_text is None
        assert observation.extraction_method is ExtractionMethod.JSON_LD

    def test_product_only_visible_body_still_recovers_the_mpn(self) -> None:
        """The FU2 page-level contract, preserved: a visible body that
        publishes nothing but the labeled field is a page about one product.
        """
        document = (
            "<html><head>"
            + _json_ld(_product_node("SOLO DRIVE", "SOLO-SKU-1"))
            + "</head><body><div>Model #: SOLO-1</div></body></html>"
        )

        observation = _extract(document)[0]
        assert observation.manufacturer_part_number_text == "SOLO-1"
        assert observation.extraction_method is ExtractionMethod.JSON_LD_WITH_VISIBLE_MPN

    def test_spec_table_rows_are_product_content_for_the_association(self) -> None:
        """The recorded Central Computer table shape: the specification
        table's other rows (Product Type, Memory Voltage) are part of the
        same table's product data display, so the product-only test holds
        and the MPN recovers from a visible body that is nothing but that
        table.
        """
        document = (
            "<html><head>"
            + _json_ld(_product_node("SOLO DRIVE", "SOLO-SKU-1"))
            + "</head><body>"
            + "<table><tbody>"
            "<tr><td>Product Type</td><td>RAM Module</td></tr>"
            "<tr><td>Manufacturer Part Number</td><td>SOLO-1</td></tr>"
            "<tr><td>Memory Voltage</td><td>1.10 V</td></tr>"
            + "</tbody></table>"
            + "</body></html>"
        )

        observation = _extract(document)[0]
        assert observation.manufacturer_part_number_text == "SOLO-1"
        assert observation.extraction_method is ExtractionMethod.JSON_LD_WITH_VISIBLE_MPN

    def test_undeclared_recommendation_mpn_request_is_rejected_over_the_frozen_3c(
        self,
    ) -> None:
        """End-to-end negative over the frozen 3C policy. A request for the
        RECOMMENDED product's MPN against the primary product's page yields
        no acceptance: the rail's value never reached the primary product's
        observation, so the only candidate is the primary product's own
        retailer SKU. Fails before the correction (A1-FU1 ACCEPTED the
        request against ``OTHER-22``).
        """
        request = ResearchRequest(
            manufacturer_part_number=ADVERSARIAL_SIDEBAR_MPN,
            description="unrelated recommendation product",
        )
        normalized = normalize_listing_observations(
            _extract(_undeclared_recommendation_document())
        )
        assessments = assess_listing_identities(request, normalized)
        result = aggregate_listing_prices(request, assessments)

        assert assessments[0].decision is EvidenceDecision.REJECTED
        assert assessments[0].rejection_reason.value == "NO_EXPLICIT_MPN_EVIDENCE"
        assert assessments[0].candidate_evidence_source is EvidenceSource.SKU_FIELD
        assert assessments[0].candidate_part_number_raw == "MAIN-SKU-1"
        assert result.buckets == ()
        assert result.exclusions[0].reason is PriceAggregationExclusionReason.IDENTITY_NOT_ACCEPTED


# ---------------------------------------------------------------------------
# PRODUCT-INTEL.PILOT-VALUE-EVIDENCE-A1-FU3 — the local association
# ---------------------------------------------------------------------------
# The FU3 adjudication held two structural variants open over the proposed
# local association test and product-only predicate, and required both to
# fail closed:
#
# C1 — the shared generic layout wrapper. The page publishes an
# ``Item #: MAIN-SKU-1`` field in one child div and a ``Model #: OTHER-22``
# field in a sibling child div of an arbitrary ``page-layout`` wrapper. The
# wrapper is not the anchor's bounded product-detail container: it merely
# holds the two fields as separate child subtrees. The other product's MPN
# is never assigned to the primary product, and the primary product's 299
# USD price never enters a Machine Price bucket for ``OTHER-22``.
#
# C2 — the sparse main region. The declared primary region contains a title
# section and a different section with a labeled ``Model #: OTHER-22``
# field. Declaring ``<main>`` scopes the evidence pool; it is not a
# co-reference. A title in one section does not make a labeled field in
# another section the product's own display, and the field's value is not a
# published identifier.
#
# Both variants fail before the correction: A1-FU2 accepted ``OTHER-22``
# through the page-global identifier anchor (C1) and the blanket primary
# region (C2), and the previously proposed FU3 candidate accepted them
# through any shared non-document-level ancestor (C1) and the product-only
# predicate over a title plus an unrelated labeled field (C2).

def _c1_layout_wrapper_document() -> str:
    """C1 verbatim: two fields in sibling child divs of a generic wrapper."""
    return (
        "<html><head>"
        + _json_ld(_main_product_node())
        + "</head><body>"
        + '<div class="page-layout">'
        + "<div><span>Item #: MAIN-SKU-1</span></div>"
        + "<div><span>Model #: OTHER-22</span></div>"
        + "</div>"
        + "</body></html>"
    )


def _c2_sparse_main_document() -> str:
    """C2 verbatim: a title section and a labeled-field section in <main>."""
    return (
        "<html><head>"
        + _json_ld(_main_product_node())
        + "</head><body>"
        + "<main>"
        + "<section><h1>MAIN PRODUCT A</h1></section>"
        + "<section><span>Model #: OTHER-22</span></section>"
        + "</main>"
        + "</body></html>"
    )


class TestFU3LocalAssociationBarriers:
    """A1-FU3: the shared wrapper and the sparse main region fail closed."""

    def test_shared_generic_layout_wrapper_does_not_associate_the_fields(self) -> None:
        """C1 — the page-layout wrapper holds the two fields as separate
        child subtrees; it is not the anchor's bounded product-detail
        container. The other product's MPN is never assigned, and the
        original structured offer remains intact.
        """
        observation = _extract(_c1_layout_wrapper_document())[0]

        assert observation.manufacturer_part_number_text is None
        assert observation.manufacturer_part_number_text != ADVERSARIAL_SIDEBAR_MPN
        assert observation.extraction_method is ExtractionMethod.JSON_LD
        assert observation.product_title == "MAIN PRODUCT A"
        assert observation.sku_text == "MAIN-SKU-1"
        assert observation.price_text == "299"
        assert observation.currency_text == "USD"
        assert observation.condition_text == "https://schema.org/NewCondition"
        assert observation.availability_text == "https://schema.org/InStock"

    def test_shared_generic_layout_wrapper_is_rejected_over_the_frozen_pipeline(self) -> None:
        """C1 end-to-end over the frozen 3C / 4A policies: a request for the
        wrapper's other-product MPN yields no acceptance, and the primary
        product's 299 USD price never enters a Machine Price bucket for it.
        Fails before the correction (A1-FU2 and the FU3 candidate both
        ACCEPTED the request against ``OTHER-22`` at 299 USD).
        """
        request = ResearchRequest(
            manufacturer_part_number=ADVERSARIAL_SIDEBAR_MPN,
            description="unrelated other product",
        )
        normalized = normalize_listing_observations(
            _extract(_c1_layout_wrapper_document())
        )
        assessments = assess_listing_identities(request, normalized)
        result = aggregate_listing_prices(request, assessments)

        assert assessments[0].decision is EvidenceDecision.REJECTED
        assert assessments[0].rejection_reason.value == "NO_EXPLICIT_MPN_EVIDENCE"
        assert assessments[0].candidate_evidence_source is EvidenceSource.SKU_FIELD
        assert assessments[0].candidate_part_number_raw == "MAIN-SKU-1"
        assert result.buckets == ()
        assert result.exclusions[0].reason is PriceAggregationExclusionReason.IDENTITY_NOT_ACCEPTED

    def test_sparse_main_region_title_and_field_in_separate_sections_are_not_associated(
        self,
    ) -> None:
        """C2 — declaring the primary region scopes the evidence pool; the
        title in one section does not make the labeled field in another
        section the product's own display. The other product's MPN is never
        assigned, and the original structured offer remains intact.
        """
        observation = _extract(_c2_sparse_main_document())[0]

        assert observation.manufacturer_part_number_text is None
        assert observation.manufacturer_part_number_text != ADVERSARIAL_SIDEBAR_MPN
        assert observation.extraction_method is ExtractionMethod.JSON_LD
        assert observation.product_title == "MAIN PRODUCT A"
        assert observation.sku_text == "MAIN-SKU-1"
        assert observation.price_text == "299"
        assert observation.currency_text == "USD"
        assert observation.condition_text == "https://schema.org/NewCondition"
        assert observation.availability_text == "https://schema.org/InStock"

    def test_sparse_main_region_is_rejected_over_the_frozen_pipeline(self) -> None:
        """C2 end-to-end over the frozen 3C / 4A policies: a request for the
        other section's MPN yields no acceptance, and the primary product's
        299 USD price never enters a Machine Price bucket for it. Fails
        before the correction (A1-FU2 and the FU3 candidate both ACCEPTED
        the request against ``OTHER-22`` at 299 USD).
        """
        request = ResearchRequest(
            manufacturer_part_number=ADVERSARIAL_SIDEBAR_MPN,
            description="unrelated other product",
        )
        normalized = normalize_listing_observations(_extract(_c2_sparse_main_document()))
        assessments = assess_listing_identities(request, normalized)
        result = aggregate_listing_prices(request, assessments)

        assert assessments[0].decision is EvidenceDecision.REJECTED
        assert assessments[0].rejection_reason.value == "NO_EXPLICIT_MPN_EVIDENCE"
        assert assessments[0].candidate_evidence_source is EvidenceSource.SKU_FIELD
        assert assessments[0].candidate_part_number_raw == "MAIN-SKU-1"
        assert result.buckets == ()
        assert result.exclusions[0].reason is PriceAggregationExclusionReason.IDENTITY_NOT_ACCEPTED
