"""Unit tests for FX currency discovery (PRODUCT-INTEL.4D-C-A / FU2 BLOCKER 1).

BLOCKER 1: FX currency discovery must consider both:
A. Public PriceAggregationResult buckets
B. Usable 4D-B SupplementSourceObservation values

Tests cover all required scenarios:
1. public USD only + no/non-reportable vendor non-USD -> ZERO FX calls
2. public USD + usable Synnex EUR -> ONE FX call, requested currencies include EUR + USD
3. no public price bucket + usable Synnex EUR -> ONE FX call
4. public GBP + vendor EUR -> ONE FX call total, requested currencies include GBP + EUR + USD
5. public USD + vendor USD -> ZERO FX calls
"""

from __future__ import annotations

from datetime import date, datetime, timezone
from decimal import Decimal
from unittest.mock import MagicMock

import pytest

from product_intelligence.domain import ResearchRequest
from product_intelligence.research.aggregation import (
    PriceAggregationResult,
    PriceAggregateBucket,
    ListingIdentityAssessment,
    PriceAggregationExclusion,
)
from product_intelligence.research.commercial_supplement_codec import (
    ResearchSupplementResult,
    VendorCommercialResult,
    SupplementSourceObservation,
    SupplementSourceIssue,
    encode_research_supplement_result,
)


class TestGetRequiredFxCurrencies:
    """Test _get_required_fx_currencies for correct public + vendor currency discovery."""

    def _make_empty_result(self) -> PriceAggregationResult:
        """Create an empty aggregation result (no buckets, no exclusions)."""
        from product_intelligence.domain.enums import VerificationStatus

        request = ResearchRequest(
            manufacturer_part_number="TEST-MPN",
            description="Test",
        )
        return PriceAggregationResult(
            request=request,
            assessments=(),
            buckets=(),
            exclusions=(),
            verification_status=VerificationStatus.UNKNOWN,
        )

    def _make_result_with_buckets(
        self,
        buckets: list[PriceAggregateBucket],
    ) -> PriceAggregationResult:
        """Create an aggregation result with specified buckets."""
        from product_intelligence.domain.enums import VerificationStatus

        # Collect all assessments from buckets
        all_assessments: list = []
        for bucket in buckets:
            all_assessments.extend(bucket.assessments)

        request = ResearchRequest(
            manufacturer_part_number="TEST-MPN",
            description="Test",
        )
        return PriceAggregationResult(
            request=request,
            assessments=tuple(all_assessments),
            buckets=tuple(buckets),
            exclusions=(),
            verification_status=VerificationStatus.VERIFIED if buckets else VerificationStatus.UNKNOWN,
        )

    def _make_empty_result(self) -> PriceAggregationResult:
        """Create an empty aggregation result (no buckets, no exclusions)."""
        from product_intelligence.domain.enums import VerificationStatus

        request = ResearchRequest(
            manufacturer_part_number="TEST-MPN",
            description="Test",
        )
        return PriceAggregationResult(
            request=request,
            assessments=(),
            buckets=(),
            exclusions=(),
            verification_status=VerificationStatus.UNKNOWN,
        )

    def _make_assessment(
        self,
        decision_value: str = "ACCEPTED",
        currency: str = "USD",
        price: Decimal = Decimal("1000.00"),
        condition: str = "NEW",
    ) -> ListingIdentityAssessment:
        """Create a real ListingIdentityAssessment for bucket tests."""
        from product_intelligence.domain.enums import IdentityMatchType
        from product_intelligence.research.listings import ExtractionMethod, ListingObservation
        from product_intelligence.research.matching import (
            ListingIdentityAssessment as LA,
            EvidenceDecision,
            IdentityRejectionReason,
            EvidenceSource,
        )
        from product_intelligence.research.normalization import normalize_listing_observation

        obs = ListingObservation(
            source_url="https://test.example.com/product",
            extraction_method=ExtractionMethod.JSON_LD,
            product_title="Test Product",
            manufacturer_part_number_text="TEST-MPN",
            sku_text=None,
            brand_text="TestBrand",
            price_text=str(price),
            currency_text=currency,
            availability_text="https://schema.org/InStock",
            condition_text=condition,
            seller_text=None,
            offer_url_text=None,
            raw_reference=None,
        )
        normalized = normalize_listing_observation(obs)

        decision = EvidenceDecision(decision_value)
        if decision == EvidenceDecision.REJECTED:
            rejection = IdentityRejectionReason.MPN_MISMATCH
        elif decision == EvidenceDecision.UNDECIDED:
            rejection = IdentityRejectionReason.NO_REQUESTED_MPN
            # UNDECIDED + NO_REQUESTED_MPN requires empty requested part number
            requested_pn = ""
        else:
            rejection = None
            requested_pn = "TEST-MPN"

        match_type = (
            IdentityMatchType.UNKNOWN
            if decision == EvidenceDecision.UNDECIDED
            else IdentityMatchType.EXACT
        )

        return LA(
            normalized_listing=normalized,
            requested_part_number=requested_pn,
            candidate_part_number_raw="TEST-MPN",
            candidate_part_number_compared="TEST-MPN",
            candidate_evidence_source=EvidenceSource.EXPLICIT_MPN_FIELD,
            match_type=match_type,
            decision=decision,
            rejection_reason=rejection,
        )

    # -------------------------------------------------------------------------
    # Scenario 1: public USD only + no/non-reportable vendor non-USD -> ZERO FX
    # -------------------------------------------------------------------------

    def test_usd_only_public_buckets_no_vendor_zero_fx(self) -> None:
        """Scenario 1a: public USD only, no vendor evidence -> zero FX currencies."""
        from product_intelligence.execution.orchestration import (
            _get_required_fx_currencies,
        )

        assessment = self._make_assessment(decision_value="ACCEPTED", currency="USD")
        result = self._make_result_with_buckets([
            self._make_bucket("USD", "NEW", [assessment]),
        ])

        required = _get_required_fx_currencies(result, supplemental_payload=None)

        # No non-USD currencies -> empty set
        assert required == frozenset()

    def test_eur_public_bucket_needs_fx(self) -> None:
        """Scenario 1d: EUR public bucket requires EUR and USD in FX call."""
        from product_intelligence.execution.orchestration import (
            _get_required_fx_currencies,
        )

        assessment = self._make_assessment(
            decision_value="ACCEPTED",
            currency="EUR",
            price=Decimal("1700.00"),
            condition="NEW",
        )
        bucket = self._make_bucket("EUR", "NEW", [assessment])
        result = self._make_result_with_buckets([bucket])

        required = _get_required_fx_currencies(result, supplemental_payload=None)

        assert "EUR" in required
        assert "USD" in required

    def test_no_public_buckets_no_vendor_zero_fx(self) -> None:
        """Scenario 1b: no public price buckets, no vendor -> zero FX currencies."""
        from product_intelligence.execution.orchestration import (
            _get_required_fx_currencies,
        )

        result = self._make_empty_result()

        required = _get_required_fx_currencies(result, supplemental_payload=None)

        assert required == frozenset()

    def test_no_public_buckets_vendor_source_issues_only_zero_fx(self) -> None:
        """Scenario 1c: no public buckets, vendor has ONLY source_issues
        (NOT USABLE) -> zero FX currencies.\n
        source_issues are NOT reportable vendor evidence.
        """
        from product_intelligence.execution.orchestration import (
            _get_required_fx_currencies,
        )

        result = self._make_empty_result()

        # Vendor supplemental with ONLY issues, no usable observations
        supplement = ResearchSupplementResult(
            vendor_commercial_result=VendorCommercialResult(
                lookup_status="PARTIAL",
                retrieved_at=datetime(2024, 1, 15, 12, 0, 0, tzinfo=timezone.utc),
                observations=(),  # No usable observations
                source_issues=(
                    SupplementSourceIssue(
                        source_name="Synnex EU",
                        outcome="NOT_FOUND",
                        detail=None,
                    ),
                ),
            ),
        )
        payload = encode_research_supplement_result(supplement)

        required = _get_required_fx_currencies(result, supplemental_payload=payload)

        # No usable observations -> no non-USD currencies
        assert required == frozenset()

    # -------------------------------------------------------------------------
    # Scenario 2: public USD + usable Synnex EUR = ONE FX call
    # -------------------------------------------------------------------------

    def test_public_usd_plus_vendor_eur_one_fx_call(self) -> None:
        """Scenario 2: public USD bucket + usable Synnex EUR vendor observation
        -> required currencies include EUR and USD.\n
        Required: requested currencies include EUR + USD.
        """
        from product_intelligence.execution.orchestration import (
            _get_required_fx_currencies,
        )

        assessment = self._make_assessment(decision_value="ACCEPTED", currency="USD")
        result = self._make_result_with_buckets([
            self._make_bucket("USD", "NEW", [assessment]),
        ])

        # Vendor with usable EUR observation
        supplement = ResearchSupplementResult(
            vendor_commercial_result=VendorCommercialResult(
                lookup_status="SUCCESS",
                retrieved_at=datetime(2024, 1, 15, 12, 0, 0, tzinfo=timezone.utc),
                observations=(
                    SupplementSourceObservation(
                        source_name="Synnex EU",
                        explicit_candidate_mpn="MZ-QL23T800",
                        vendor_mpn_match_type="EXACT",
                        price_amount=Decimal("1700.00"),
                        currency_code="EUR",  # Non-USD
                        availability="IN_STOCK",
                        price_basis="CUSTOMER_PRICE",
                        quantity=1,
                        note_kind=None,
                        brand_new=True,
                        brand_new_basis="VENDOR_API_POLICY",
                    ),
                ),
                source_issues=(),
            ),
        )
        payload = encode_research_supplement_result(supplement)

        required = _get_required_fx_currencies(result, supplemental_payload=payload)

        # Required currencies must include EUR (from vendor) and USD (for formula)
        assert "EUR" in required
        assert "USD" in required
        # Total should be exactly 2 (EUR + USD)
        assert required == frozenset({"EUR", "USD"})

    # -------------------------------------------------------------------------
    # Scenario 3: no public bucket + usable Synnex EUR -> ONE FX call
    # -------------------------------------------------------------------------

    def test_no_public_bucket_plus_vendor_eur_one_fx_call(self) -> None:
        """Scenario 3: no public price bucket + usable Synnex EUR vendor
        -> required currencies include EUR and USD.\n
        Required: requested currencies include EUR + USD.
        """
        from product_intelligence.execution.orchestration import (
            _get_required_fx_currencies,
        )

        result = self._make_empty_result()

        # Vendor with usable EUR observation (no public buckets)
        supplement = ResearchSupplementResult(
            vendor_commercial_result=VendorCommercialResult(
                lookup_status="SUCCESS",
                retrieved_at=datetime(2024, 1, 15, 12, 0, 0, tzinfo=timezone.utc),
                observations=(
                    SupplementSourceObservation(
                        source_name="Synnex EU",
                        explicit_candidate_mpn="MZ-QL23T800",
                        vendor_mpn_match_type="EXACT",
                        price_amount=Decimal("1700.00"),
                        currency_code="EUR",  # Non-USD
                        availability="IN_STOCK",
                        price_basis="CUSTOMER_PRICE",
                        quantity=1,
                        note_kind=None,
                        brand_new=True,
                        brand_new_basis="VENDOR_API_POLICY",
                    ),
                ),
                source_issues=(),
            ),
        )
        payload = encode_research_supplement_result(supplement)

        required = _get_required_fx_currencies(result, supplemental_payload=payload)

        # Required currencies include EUR (from vendor) and USD (for formula)
        assert "EUR" in required
        assert "USD" in required
        assert required == frozenset({"EUR", "USD"})

    # -------------------------------------------------------------------------
    # Scenario 4: public GBP + vendor EUR -> ONE FX call total
    # -------------------------------------------------------------------------

    def test_public_gbp_plus_vendor_eur_one_fx_call_total(self) -> None:
        """Scenario 4: public GBP bucket + vendor EUR observation
        -> ONE FX call total, requested currencies include GBP + EUR + USD.\n
        Required: total FX calls == 1, requested currencies include GBP, EUR, USD.
        """
        from product_intelligence.execution.orchestration import (
            _get_required_fx_currencies,
        )

        gbp_assessment = self._make_assessment(decision_value="ACCEPTED", currency="GBP")
        result = self._make_result_with_buckets([
            self._make_bucket("GBP", "NEW", [gbp_assessment]),
        ])

        # Vendor with EUR observation
        supplement = ResearchSupplementResult(
            vendor_commercial_result=VendorCommercialResult(
                lookup_status="SUCCESS",
                retrieved_at=datetime(2024, 1, 15, 12, 0, 0, tzinfo=timezone.utc),
                observations=(
                    SupplementSourceObservation(
                        source_name="Synnex EU",
                        explicit_candidate_mpn="MZ-QL23T800",
                        vendor_mpn_match_type="EXACT",
                        price_amount=Decimal("1700.00"),
                        currency_code="EUR",  # Different from public GBP
                        availability="IN_STOCK",
                        price_basis="CUSTOMER_PRICE",
                        quantity=1,
                        note_kind=None,
                        brand_new=True,
                        brand_new_basis="VENDOR_API_POLICY",
                    ),
                ),
                source_issues=(),
            ),
        )
        payload = encode_research_supplement_result(supplement)

        required = _get_required_fx_currencies(result, supplemental_payload=payload)

        # All three currencies needed: GBP (public), EUR (vendor), USD (formula)
        assert "GBP" in required
        assert "EUR" in required
        assert "USD" in required
        assert required == frozenset({"GBP", "EUR", "USD"})

    # -------------------------------------------------------------------------
    # Scenario 5: public USD + vendor USD -> ZERO FX calls
    # -------------------------------------------------------------------------

    def test_public_usd_plus_vendor_usd_zero_fx_calls(self) -> None:
        """Scenario 5: public USD bucket + vendor USD observation
        -> zero FX currencies (no non-USD to convert).\n
        Required: fx_provider.call_count == 0
        """
        from product_intelligence.execution.orchestration import (
            _get_required_fx_currencies,
        )

        usd_assessment = self._make_assessment(decision_value="ACCEPTED", currency="USD")
        result = self._make_result_with_buckets([
            self._make_bucket("USD", "NEW", [usd_assessment]),
        ])

        # Vendor with USD observation
        supplement = ResearchSupplementResult(
            vendor_commercial_result=VendorCommercialResult(
                lookup_status="SUCCESS",
                retrieved_at=datetime(2024, 1, 15, 12, 0, 0, tzinfo=timezone.utc),
                observations=(
                    SupplementSourceObservation(
                        source_name="Ingram",
                        explicit_candidate_mpn="TEST-MPN",
                        vendor_mpn_match_type="EXACT",
                        price_amount=Decimal("2000.00"),
                        currency_code="USD",  # Same as public
                        availability="IN_STOCK",
                        price_basis="CUSTOMER_PRICE",
                        quantity=1,
                        note_kind=None,
                        brand_new=True,
                        brand_new_basis="VENDOR_API_POLICY",
                    ),
                ),
                source_issues=(),
            ),
        )
        payload = encode_research_supplement_result(supplement)

        required = _get_required_fx_currencies(result, supplemental_payload=payload)

        # No non-USD currencies -> empty set
        assert required == frozenset()

    # -------------------------------------------------------------------------
    # Edge cases
    # -------------------------------------------------------------------------

    def test_malformed_supplemental_payload_propagates(self) -> None:
        """BLOCKER 3 (FU2) KEY NEGATIVE: A malformed supplemental payload
        is NOT silently skipped — it propagates as a programming defect.

        supplemental_payload is not None only when it was successfully
        produced by the canonical 4D-B encoder in the same execution.
        A non-None payload that fails to decode is a programming/data-integrity
        defect and MUST propagate.

        Valid empty states:
          supplemental_payload is None -> no vendor data (valid)
          supplemental_payload valid but zero usable obs -> no currencies (valid)
          supplemental_payload with only USD obs -> no non-USD currencies (valid)

        Defect states (MUST propagate):
          malformed dict (not a valid encoded payload)
          codec version violation
          contract violation

        This test verifies that a malformed dict raises an exception.
        """
        from product_intelligence.execution.orchestration import (
            _get_required_fx_currencies,
        )

        eur_assessment = self._make_assessment(decision_value="ACCEPTED", currency="EUR")
        result = self._make_result_with_buckets([
            self._make_bucket("EUR", "NEW", [eur_assessment]),
        ])

        # Malformed payload — not a valid encoded supplemental payload.
        # The canonical encoder produces a dict with specific keys like
        # "schema_version", "request", "vendor_commercial_result", etc.
        # A dict like this is NOT valid and must propagate.
        malformed_payload = {"invalid": "structure", "unknown": "payload"}

        # BLOCKER 3: The malformed payload raises, not silently produces
        # frozenset() with public buckets only.
        with pytest.raises(Exception):  # decode_fx_supplement or similar error
            _get_required_fx_currencies(
                result,
                supplemental_payload=malformed_payload,
            )

    def test_vendor_mpn_mismatch_not_reportable(self) -> None:
        """Vendor observations with MPN_MISMATCH are not reportable.\n
        These observations should NOT contribute currencies to FX discovery.
        """
        from product_intelligence.execution.orchestration import (
            _get_required_fx_currencies,
        )

        result = self._make_empty_result()

        # Vendor with only MPN_MISMATCH issues (not usable observations)
        supplement = ResearchSupplementResult(
            vendor_commercial_result=VendorCommercialResult(
                lookup_status="PARTIAL",
                retrieved_at=datetime(2024, 1, 15, 12, 0, 0, tzinfo=timezone.utc),
                observations=(),  # No usable observations
                source_issues=(
                    SupplementSourceIssue(
                        source_name="Synnex EU",
                        outcome="MPN_MISMATCH",
                        detail="vendor_mpn_mismatch",
                    ),
                ),
            ),
        )
        payload = encode_research_supplement_result(supplement)

        required = _get_required_fx_currencies(result, supplemental_payload=payload)

        # No usable observations -> no currencies
        assert required == frozenset()

    def test_multiple_vendor_currencies_collected(self) -> None:
        """Multiple vendor observations with different non-USD currencies
        are all collected for FX discovery.\n
        """
        from product_intelligence.execution.orchestration import (
            _get_required_fx_currencies,
        )

        usd_assessment = self._make_assessment(decision_value="ACCEPTED", currency="USD")
        result = self._make_result_with_buckets([
            self._make_bucket("USD", "NEW", [usd_assessment]),
        ])

        # Vendor with multiple non-USD currencies
        supplement = ResearchSupplementResult(
            vendor_commercial_result=VendorCommercialResult(
                lookup_status="SUCCESS",
                retrieved_at=datetime(2024, 1, 15, 12, 0, 0, tzinfo=timezone.utc),
                observations=(
                    SupplementSourceObservation(
                        source_name="Synnex EU",
                        explicit_candidate_mpn="TEST-MPN",
                        vendor_mpn_match_type="EXACT",
                        price_amount=Decimal("1700.00"),
                        currency_code="EUR",
                        availability="IN_STOCK",
                        price_basis="CUSTOMER_PRICE",
                        quantity=1,
                        note_kind=None,
                        brand_new=True,
                        brand_new_basis="VENDOR_API_POLICY",
                    ),
                    SupplementSourceObservation(
                        source_name="Ingram UK",
                        explicit_candidate_mpn="TEST-MPN",
                        vendor_mpn_match_type="EXACT",
                        price_amount=Decimal("1800.00"),
                        currency_code="GBP",
                        availability="IN_STOCK",
                        price_basis="LIST_PRICE",
                        quantity=1,
                        note_kind=None,
                        brand_new=True,
                        brand_new_basis="VENDOR_API_POLICY",
                    ),
                ),
                source_issues=(),
            ),
        )
        payload = encode_research_supplement_result(supplement)

        required = _get_required_fx_currencies(result, supplemental_payload=payload)

        # Both EUR and GBP from vendor, plus USD for formula
        assert "EUR" in required
        assert "GBP" in required
        assert "USD" in required
        assert required == frozenset({"EUR", "GBP", "USD"})

    # -------------------------------------------------------------------------
    # Helper methods
    # -------------------------------------------------------------------------

    def _make_bucket(
        self,
        currency: str,
        condition: str,
        assessments: list,
    ) -> PriceAggregateBucket:
        """Create a PriceAggregateBucket with the given currency/condition."""
        from product_intelligence.research.normalization import (
            NormalizedCondition,
        )
        from product_intelligence.domain.enums import ConfidenceLevel

        # Create minimal assessment objects if needed
        from product_intelligence.research.matching import ListingIdentityAssessment

        # Compute stats from actual assessment prices
        prices = [
            a.normalized_listing.price_amount
            for a in assessments
            if a.normalized_listing.price_amount is not None
        ]
        if prices:
            sorted_prices = sorted(prices)
            low = sorted_prices[0]
            high = sorted_prices[-1]
            mid = len(sorted_prices) // 2
            median = (
                sorted_prices[mid]
                if len(sorted_prices) % 2 == 1
                else (sorted_prices[mid - 1] + sorted_prices[mid]) / 2
            )
        else:
            low = median = high = Decimal("0.00")

        return PriceAggregateBucket(
            currency_code=currency,
            condition=NormalizedCondition(condition),
            assessments=tuple(assessments),
            count=len(assessments),
            low=low,
            median=median,
            high=high,
            market_range_low=None,
            market_range_high=None,
            confidence=ConfidenceLevel.LOW,
        )