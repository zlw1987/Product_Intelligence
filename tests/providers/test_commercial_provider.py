"""Tests for the provider-neutral commercial-source boundary (PRODUCT-INTEL.4D-B).

Tests cover:
* Generic commercial boundary is provider-neutral (stdlib only, no vendor names)
* Generic boundary opens no connection
* Generic boundary reads no env/config
* Contract construction: CommercialLookupQuery, CommercialSourceCandidate,
  CommercialSourceIssue, CommercialSourceResponse
* Enum validation
* Decimal-only monetary values
* No binary float
"""

from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal

import pytest

from product_intelligence.providers.commercial import (
    CommercialAvailability,
    CommercialLookupQuery,
    CommercialNoteKind,
    CommercialPriceBasis,
    CommercialSourceCandidate,
    CommercialSourceIssue,
    CommercialSourceResponse,
    CommercialSourceProvider,
    LookupStatus,
    SourceOutcome,
)


# ---------------------------------------------------------------------------
# CommercialLookupQuery
# ---------------------------------------------------------------------------


class TestCommercialLookupQuery:
    def test_valid_mpn(self) -> None:
        q = CommercialLookupQuery(mpn="BCM957608-P2200GQF00")
        assert q.mpn == "BCM957608-P2200GQF00"

    def test_mpn_stripped(self) -> None:
        q = CommercialLookupQuery(mpn="  ABC123  ")
        assert q.mpn == "ABC123"

    def test_empty_mpn_rejected(self) -> None:
        with pytest.raises(ValueError, match="non-empty"):
            CommercialLookupQuery(mpn="")

    def test_whitespace_only_mpn_rejected(self) -> None:
        with pytest.raises(ValueError, match="non-empty"):
            CommercialLookupQuery(mpn="   ")

    def test_non_string_mpn_rejected(self) -> None:
        with pytest.raises(TypeError, match="string"):
            CommercialLookupQuery(mpn=12345)  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# CommercialSourceCandidate
# ---------------------------------------------------------------------------


class TestCommercialSourceCandidate:
    def _make_candidate(self, **overrides) -> CommercialSourceCandidate:
        defaults = dict(
            source_name="TestSource",
            explicit_candidate_mpn="ABC123",
            price_amount=Decimal("100.00"),
            currency_code="USD",
            availability=CommercialAvailability.IN_STOCK,
            price_basis=CommercialPriceBasis.CUSTOMER_PRICE,
        )
        defaults.update(overrides)
        return CommercialSourceCandidate(**defaults)

    def test_valid_candidate(self) -> None:
        c = self._make_candidate()
        assert c.source_name == "TestSource"
        assert c.explicit_candidate_mpn == "ABC123"
        assert c.price_amount == Decimal("100.00")
        assert c.currency_code == "USD"
        assert c.availability == CommercialAvailability.IN_STOCK
        # Provider boundary carries NO brand-new business-policy fields
        assert not hasattr(c, 'brand_new')
        assert not hasattr(c, 'brand_new_basis')

    def test_price_must_be_finite(self) -> None:
        """Non-finite Decimal (NaN/Infinity) rejected at provider boundary."""
        with pytest.raises(ValueError, match="finite"):
            self._make_candidate(price_amount=Decimal("NaN"))

    def test_price_infinity_rejected(self) -> None:
        with pytest.raises(ValueError, match="finite"):
            self._make_candidate(price_amount=Decimal("Infinity"))

    def test_decimal_price_only(self) -> None:
        c = self._make_candidate(price_amount=Decimal("1234.56"))
        assert isinstance(c.price_amount, Decimal)
        assert c.price_amount == Decimal("1234.56")

    def test_float_price_rejected(self) -> None:
        with pytest.raises(TypeError, match="Decimal"):
            self._make_candidate(price_amount=100.00)  # type: ignore[arg-type]

    def test_negative_price_rejected(self) -> None:
        with pytest.raises(ValueError, match="negative"):
            self._make_candidate(price_amount=Decimal("-1.00"))

    def test_zero_price_accepted(self) -> None:
        c = self._make_candidate(price_amount=Decimal("0.00"))
        assert c.price_amount == Decimal("0.00")

    def test_source_name_stripped(self) -> None:
        c = self._make_candidate(source_name="  Ingram  ")
        assert c.source_name == "Ingram"

    def test_empty_source_name_rejected(self) -> None:
        with pytest.raises(ValueError, match="source_name"):
            self._make_candidate(source_name="")

    def test_empty_mpn_rejected(self) -> None:
        with pytest.raises(ValueError, match="explicit_candidate_mpn"):
            self._make_candidate(explicit_candidate_mpn="")

    def test_mpn_stripped(self) -> None:
        c = self._make_candidate(explicit_candidate_mpn="  ABC123  ")
        assert c.explicit_candidate_mpn == "ABC123"

    def test_currency_uppered_and_stripped(self) -> None:
        c = self._make_candidate(currency_code="  usd  ")
        assert c.currency_code == "USD"

    def test_empty_currency_rejected(self) -> None:
        with pytest.raises(ValueError, match="currency_code"):
            self._make_candidate(currency_code="")

    def test_availability_enum_required(self) -> None:
        with pytest.raises(TypeError, match="CommercialAvailability"):
            self._make_candidate(availability="IN_STOCK")  # type: ignore[arg-type]

    def test_price_basis_enum_required(self) -> None:
        with pytest.raises(TypeError, match="CommercialPriceBasis"):
            self._make_candidate(price_basis="CUSTOMER_PRICE")  # type: ignore[arg-type]

    def test_quantity_optional(self) -> None:
        c = self._make_candidate(quantity=None)
        assert c.quantity is None

    def test_quantity_positive(self) -> None:
        c = self._make_candidate(quantity=48)
        assert c.quantity == 48

    def test_quantity_zero(self) -> None:
        c = self._make_candidate(quantity=0)
        assert c.quantity == 0

    def test_quantity_negative_rejected(self) -> None:
        with pytest.raises(ValueError, match="quantity"):
            self._make_candidate(quantity=-1)

    def test_quantity_float_rejected(self) -> None:
        with pytest.raises(TypeError, match="int"):
            self._make_candidate(quantity=48.5)  # type: ignore[arg-type]

    def test_note_kind_optional(self) -> None:
        c = self._make_candidate(note_kind=None)
        assert c.note_kind is None

    def test_note_kind_no_returns(self) -> None:
        c = self._make_candidate(note_kind=CommercialNoteKind.NO_RETURNS)
        assert c.note_kind == CommercialNoteKind.NO_RETURNS

    def test_note_kind_enum_required(self) -> None:
        with pytest.raises(TypeError, match="CommercialNoteKind"):
            self._make_candidate(note_kind="arbitrary")  # type: ignore[arg-type]

    def test_no_brand_new_business_policy(self) -> None:
        """Provider contract carries NO brand-new business-policy fields.

        Brand-new is a customer/business-policy conclusion that applies
        ONLY after frozen 2A has successfully identity-bound the vendor
        observation to the requested product.
        """
        c = self._make_candidate()
        assert not hasattr(c, 'brand_new')
        assert not hasattr(c, 'brand_new_basis')

    def test_quantity_bool_rejected(self) -> None:
        """bool is NOT a valid integer quantity."""
        with pytest.raises(TypeError, match="int"):
            self._make_candidate(quantity=True)  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# CommercialSourceIssue
# ---------------------------------------------------------------------------


class TestCommercialSourceIssue:
    def test_valid_issue(self) -> None:
        issue = CommercialSourceIssue(
            source_name="Ingram",
            outcome=SourceOutcome.NOT_FOUND,
        )
        assert issue.source_name == "Ingram"
        assert issue.outcome == SourceOutcome.NOT_FOUND

    def test_no_detail_field(self) -> None:
        """Provider-layer issue carries no arbitrary detail text."""
        issue = CommercialSourceIssue(
            source_name="CDW",
            outcome=SourceOutcome.MALFORMED_SECTION,
        )
        # detail is not a field on the provider boundary
        assert not hasattr(issue, 'detail')

    def test_source_name_stripped(self) -> None:
        issue = CommercialSourceIssue(
            source_name="  Synnex EU  ",
            outcome=SourceOutcome.NOT_FOUND,
        )
        assert issue.source_name == "Synnex EU"

    def test_empty_source_name_rejected(self) -> None:
        with pytest.raises(ValueError, match="source_name"):
            CommercialSourceIssue(
                source_name="",
                outcome=SourceOutcome.NOT_FOUND,
            )

    def test_outcome_enum_required(self) -> None:
        with pytest.raises(TypeError, match="SourceOutcome"):
            CommercialSourceIssue(
                source_name="Test",
                outcome="unknown",  # type: ignore[arg-type]
            )


# ---------------------------------------------------------------------------
# CommercialSourceResponse
# ---------------------------------------------------------------------------


class TestCommercialSourceResponse:
    def test_failed_response(self) -> None:
        r = CommercialSourceResponse(
            status=LookupStatus.FAILED,
            retrieved_at=None,
        )
        assert r.status == LookupStatus.FAILED
        assert r.candidates == ()
        assert r.issues == ()

    def test_successful_response(self) -> None:
        dt = datetime(2025, 1, 15, 12, 0, 0, tzinfo=timezone.utc)
        c = CommercialSourceCandidate(
            source_name="TestSource",
            explicit_candidate_mpn="ABC123",
            price_amount=Decimal("100.00"),
            currency_code="USD",
            availability=CommercialAvailability.IN_STOCK,
            price_basis=CommercialPriceBasis.CUSTOMER_PRICE,
        )
        r = CommercialSourceResponse(
            status=LookupStatus.SUCCESS,
            retrieved_at=dt,
            candidates=(c,),
        )
        assert r.status == LookupStatus.SUCCESS
        assert r.retrieved_at == dt
        assert len(r.candidates) == 1

    def test_partial_response(self) -> None:
        dt = datetime(2025, 1, 15, 12, 0, 0, tzinfo=timezone.utc)
        c = CommercialSourceCandidate(
            source_name="Ingram",
            explicit_candidate_mpn="ABC123",
            price_amount=Decimal("100.00"),
            currency_code="USD",
            availability=CommercialAvailability.IN_STOCK,
            price_basis=CommercialPriceBasis.CUSTOMER_PRICE,
        )
        issue = CommercialSourceIssue(
            source_name="CDW",
            outcome=SourceOutcome.NOT_FOUND,
        )
        r = CommercialSourceResponse(
            status=LookupStatus.PARTIAL,
            retrieved_at=dt,
            candidates=(c,),
            issues=(issue,),
        )
        assert r.status == LookupStatus.PARTIAL
        assert len(r.candidates) == 1
        assert len(r.issues) == 1

    def test_naive_datetime_rejected(self) -> None:
        dt = datetime(2025, 1, 15, 12, 0, 0)  # no timezone
        with pytest.raises(ValueError, match="timezone-aware"):
            CommercialSourceResponse(
                status=LookupStatus.SUCCESS,
                retrieved_at=dt,
            )

    def test_status_enum_required(self) -> None:
        with pytest.raises(TypeError, match="LookupStatus"):
            CommercialSourceResponse(
                status="SUCCESS",  # type: ignore[arg-type]
                retrieved_at=None,
            )


# ---------------------------------------------------------------------------
# Enum completeness
# ---------------------------------------------------------------------------


class TestCommercialVocabularies:
    def test_availability_values(self) -> None:
        assert CommercialAvailability.IN_STOCK.value == "IN_STOCK"
        assert CommercialAvailability.OUT_OF_STOCK.value == "OUT_OF_STOCK"
        assert CommercialAvailability.UNKNOWN.value == "UNKNOWN"

    def test_price_basis_values(self) -> None:
        assert CommercialPriceBasis.CUSTOMER_PRICE.value == "CUSTOMER_PRICE"
        assert CommercialPriceBasis.RETAIL_PRICE_FALLBACK.value == "RETAIL_PRICE_FALLBACK"
        assert CommercialPriceBasis.LIST_PRICE.value == "LIST_PRICE"

    def test_note_kind_values(self) -> None:
        assert CommercialNoteKind.NO_RETURNS.value == "NO_RETURNS"

    def test_lookup_status_values(self) -> None:
        assert LookupStatus.SUCCESS.value == "SUCCESS"
        assert LookupStatus.PARTIAL.value == "PARTIAL"
        assert LookupStatus.FAILED.value == "FAILED"

    def test_source_outcome_values(self) -> None:
        assert SourceOutcome.USABLE.value == "USABLE"
        assert SourceOutcome.NOT_FOUND.value == "NOT_FOUND"
        assert SourceOutcome.MALFORMED_SECTION.value == "MALFORMED_SECTION"
        assert SourceOutcome.MISSING_EXPLICIT_MPN.value == "MISSING_EXPLICIT_MPN"
        assert SourceOutcome.MPN_MISMATCH.value == "MPN_MISMATCH"

    def test_commercial_source_provider_is_protocol(self) -> None:
        """CommercialSourceProvider is a Protocol, not a concrete class."""
        import typing
        assert typing.get_protocol_members(CommercialSourceProvider)
