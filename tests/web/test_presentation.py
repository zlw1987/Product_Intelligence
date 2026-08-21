"""Tests for the web presentation helper (PRODUCT-INTEL.4B).

Tests URL safety logic, display data construction, and that the
presentation helper never recomputes 4A values.
"""

from __future__ import annotations

from decimal import Decimal

import pytest

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
    PriceAggregationExclusion,
    PriceAggregationExclusionReason,
    PriceAggregationResult,
)
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
from product_intelligence.web.presentation import (
    _is_safe_href_url,
    build_report_presentation,
    ReportPresentation,
)


@pytest.fixture
def simple_result() -> PriceAggregationResult:
    obs = ListingObservation(
        source_url="https://example.com/product",
        extraction_method=ExtractionMethod.JSON_LD,
        product_title="Test Product",
        manufacturer_part_number_text="TEST-1",
        sku_text=None,
        brand_text=None,
        price_text="$50.00",
        currency_text="USD",
        availability_text="In Stock",
        condition_text="New",
        seller_text="Test Seller",
        offer_url_text=None,
        raw_reference=None,
    )
    norm = NormalizedListingObservation(
        observation=obs,
        price_amount=Decimal("50.00"),
        currency_code="USD",
        availability=NormalizedAvailability.IN_STOCK,
        condition=NormalizedCondition.NEW,
        seller_name="Test Seller",
        normalization_issues=(),
    )
    assess = ListingIdentityAssessment(
        normalized_listing=norm,
        requested_part_number="TEST-1",
        candidate_part_number_raw="TEST-1",
        candidate_part_number_compared="TEST-1",
        candidate_evidence_source=EvidenceSource.EXPLICIT_MPN_FIELD,
        match_type=IdentityMatchType.EXACT,
        decision=EvidenceDecision.ACCEPTED,
        rejection_reason=None,
    )
    return PriceAggregationResult(
        request=ResearchRequest(
            manufacturer_part_number="TEST-1",
            description="Test product",
        ),
        assessments=(assess,),
        exclusions=(),
        buckets=(
            PriceAggregateBucket(
                currency_code="USD",
                condition=NormalizedCondition.NEW,
                assessments=(assess,),
                count=1,
                low=Decimal("50.00"),
                median=Decimal("50.00"),
                high=Decimal("50.00"),
                market_range_low=None,
                market_range_high=None,
                confidence=ConfidenceLevel.LOW,
            ),
        ),
        verification_status=VerificationStatus.VERIFIED,
    )


class TestURLSafety:
    """_is_safe_href_url only allows absolute http/https URLs with a hostname."""

    def test_http_url_is_safe(self) -> None:
        assert _is_safe_href_url("https://example.com/product") is True

    def test_http_lower_is_safe(self) -> None:
        assert _is_safe_href_url("http://example.com/product") is True

    def test_https_with_path_is_safe(self) -> None:
        assert _is_safe_href_url("https://example.com/path/to/page") is True

    def test_https_with_query_is_safe(self) -> None:
        assert _is_safe_href_url("https://example.com/path?foo=bar") is True

    def test_empty_string_is_not_safe(self) -> None:
        assert _is_safe_href_url("") is False

    def test_none_is_safe(self) -> None:
        assert _is_safe_href_url("none") is False  # "none" string

    def test_javascript_url_is_not_safe(self) -> None:
        assert _is_safe_href_url("javascript:alert('xss')") is False

    def test_data_url_is_not_safe(self) -> None:
        assert _is_safe_href_url("data:text/html,<script>alert(1)</script>") is False

    def test_file_url_is_not_safe(self) -> None:
        assert _is_safe_href_url("file:///etc/passwd") is False

    def test_relative_url_is_not_safe(self) -> None:
        assert _is_safe_href_url("/relative/path") is False

    def test_scheme_relative_url_is_not_safe(self) -> None:
        assert _is_safe_href_url("//example.com/evil") is False

    def test_http_no_host_is_not_safe(self) -> None:
        """http:// with no authority before the path."""
        assert _is_safe_href_url("http:///no-host") is False

    def test_ftp_url_is_not_safe(self) -> None:
        assert _is_safe_href_url("ftp://files.example.com/file") is False

    def test_malicious_html_in_url_is_not_safe(self) -> None:
        """URL with angle brackets is suspicious."""
        url = 'https://example.com/path"><script>alert(1)</script><a href="http://evil.com'
        # Contains angle brackets in the URL text; should not be safe as href
        assert _is_safe_href_url(url) is False  # contains < in the URL

    # --- Issue 3: URL parsing fail-closed ---

    def test_malformed_ipv6_no_exception(self) -> None:
        """Malformed bracketed IPv6 must return False, not raise."""
        url = "https://[::1:invalid]/path"
        assert _is_safe_href_url(url) is False

    def test_malformed_url_no_exception(self) -> None:
        """Any malformed URL must return False, not raise ValueError."""
        url = "https://[not-an-ip/"
        assert _is_safe_href_url(url) is False

    def test_credentials_url_rejected(self) -> None:
        """URLs with userinfo credentials are rejected."""
        assert _is_safe_href_url("https://user:pass@example.com/x") is False

    def test_credentials_username_only_rejected(self) -> None:
        """URL with just a username (no password) is rejected."""
        assert _is_safe_href_url("https://user@example.com/x") is False

    def test_http_auth_at_sign_rejected(self) -> None:
        """http://@/x is rejected (empty credentials, no host)."""
        assert _is_safe_href_url("http://@/x") is False

    def test_http_port_only_no_host(self) -> None:
        """http://:80/x has no hostname, rejected."""
        assert _is_safe_href_url("http://:80/x") is False

    def test_http_query_only_no_host(self) -> None:
        """https://?x has no hostname, rejected."""
        assert _is_safe_href_url("https://?x") is False

    def test_uppercase_scheme_is_safe(self) -> None:
        """HTTPS://example.com/x is safe (scheme is case-insensitive)."""
        assert _is_safe_href_url("HTTPS://example.com/x") is True


class TestBuildReportPresentation:
    """build_report_presentation creates display data without recomputing."""

    def test_returns_presentation_object(self, simple_result: PriceAggregationResult) -> None:
        presentation = build_report_presentation(simple_result)
        assert isinstance(presentation, ReportPresentation)

    def test_verification_status_is_string(self, simple_result: PriceAggregationResult) -> None:
        presentation = build_report_presentation(simple_result)
        assert presentation.verification_status == "VERIFIED"

    def test_bucket_count_matches(self, simple_result: PriceAggregationResult) -> None:
        presentation = build_report_presentation(simple_result)
        assert len(presentation.buckets) == 1
        assert presentation.buckets[0].count == 1

    def test_median_is_string_not_decimal(self, simple_result: PriceAggregationResult) -> None:
        presentation = build_report_presentation(simple_result)
        bucket = presentation.buckets[0]
        assert isinstance(bucket.median, str)
        assert bucket.median == "50.00"

    def test_low_is_string_not_decimal(self, simple_result: PriceAggregationResult) -> None:
        presentation = build_report_presentation(simple_result)
        assert presentation.buckets[0].low == "50.00"

    def test_high_is_string_not_decimal(self, simple_result: PriceAggregationResult) -> None:
        presentation = build_report_presentation(simple_result)
        assert presentation.buckets[0].high == "50.00"

    def test_confidence_is_string(self, simple_result: PriceAggregationResult) -> None:
        presentation = build_report_presentation(simple_result)
        assert presentation.buckets[0].confidence == "LOW"

    def test_source_url_safety_is_set(self, simple_result: PriceAggregationResult) -> None:
        presentation = build_report_presentation(simple_result)
        assessment = presentation.buckets[0].assessments[0]
        assert assessment.source_url_safe is True

    def test_has_market_range_is_false_when_none(self, simple_result: PriceAggregationResult) -> None:
        presentation = build_report_presentation(simple_result)
        assert presentation.buckets[0].has_market_range is False

    def test_no_exclusions_produces_empty_list(self, simple_result: PriceAggregationResult) -> None:
        presentation = build_report_presentation(simple_result)
        assert presentation.exclusions == []


class TestBuildReportWithExclusions:
    def test_excluded_assessments_shown(self) -> None:
        obs = ListingObservation(
            source_url="https://example.com/wrong",
            extraction_method=ExtractionMethod.META,
            product_title="Wrong Product",
            manufacturer_part_number_text="WRONG",
            sku_text=None,
            brand_text=None,
            price_text="$50.00",
            currency_text="USD",
            availability_text="In Stock",
            condition_text="New",
            seller_text="Wrong Seller",
            offer_url_text=None,
            raw_reference=None,
        )
        norm = NormalizedListingObservation(
            observation=obs,
            price_amount=Decimal("50.00"),
            currency_code="USD",
            availability=NormalizedAvailability.IN_STOCK,
            condition=NormalizedCondition.NEW,
            seller_name="Wrong Seller",
            normalization_issues=(),
        )
        assess = ListingIdentityAssessment(
            normalized_listing=norm,
            requested_part_number="TEST-1",
            candidate_part_number_raw="WRONG",
            candidate_part_number_compared="WRONG",
            candidate_evidence_source=EvidenceSource.EXPLICIT_MPN_FIELD,
            match_type=IdentityMatchType.UNKNOWN,
            decision=EvidenceDecision.REJECTED,
            rejection_reason=IdentityRejectionReason.MPN_MISMATCH,
        )
        result = PriceAggregationResult(
            request=ResearchRequest(
                manufacturer_part_number="TEST-1",
                description="Test product",
            ),
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

        presentation = build_report_presentation(result)

        assert len(presentation.exclusions) == 1
        assert presentation.exclusions[0].exclusion_reason == "IDENTITY_NOT_ACCEPTED"
        assert len(presentation.buckets) == 0
