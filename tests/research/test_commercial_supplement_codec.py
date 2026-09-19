"""Tests for the commercial supplement codec (PRODUCT-INTEL.4D-B).

Tests cover:
* V1 encode/decode round trip
* retrieved_at decoded as timezone-aware datetime (not string)
* Strict required keys
* Reject extra keys (fail closed)
* Decimal exactness preserved
* Malformed payload fails closed
* Extra keys fail closed
* Unknown enum values rejected
* NaN/Infinity decimal rejected (encode + decode)
* Naive datetime rejected on encode
* Malformed retrieved_at rejected on decode
* Non-UTC retrieved_at rejected
* Bool quantity rejected
* Negative quantity rejected
* Invalid brand_new_basis rejected
* Invalid vendor_mpn_match_type rejected
* Round trip returns aware datetime
* Encode-side enum/status validation
* __post_init__ validation on domain objects
"""

from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal

import pytest

from product_intelligence.providers.commercial import (
    CommercialAvailability,
    CommercialPriceBasis,
)
from product_intelligence.research.commercial_supplement_codec import (
    ResearchSupplementResult,
    SupplementCodecError,
    SupplementSourceObservation,
    SupplementSourceIssue,
    VendorCommercialResult,
    decode_research_supplement_result,
    encode_research_supplement_result,
)


def _make_result(**overrides) -> ResearchSupplementResult:
    defaults = dict(
        vendor_commercial_result=VendorCommercialResult(
            lookup_status="SUCCESS",
            retrieved_at=datetime(2025, 1, 15, 12, 0, 0, tzinfo=timezone.utc),
            observations=(
                SupplementSourceObservation(
                    source_name="Ingram",
                    explicit_candidate_mpn="BCM957608-P2200GQF00",
                    vendor_mpn_match_type="EXACT",
                    price_amount=Decimal("2120.00"),
                    currency_code="USD",
                    availability="IN_STOCK",
                    price_basis="CUSTOMER_PRICE",
                    quantity=10,
                    note_kind=None,
                    brand_new=True,
                    brand_new_basis="VENDOR_API_POLICY",
                ),
            ),
            source_issues=(
                SupplementSourceIssue(
                    source_name="CDW",
                    outcome="NOT_FOUND",
                    detail=None,
                ),
            ),
        ),
    )
    defaults.update(overrides)
    return ResearchSupplementResult(**defaults)


class TestCodecRoundTrip:
    def test_basic_round_trip(self) -> None:
        original = _make_result()
        encoded = encode_research_supplement_result(original)
        decoded = decode_research_supplement_result(encoded)

        assert decoded.vendor_commercial_result.lookup_status == "SUCCESS"
        # retrieved_at must be a timezone-aware datetime, not a string
        retrieved = decoded.vendor_commercial_result.retrieved_at
        assert isinstance(retrieved, datetime)
        assert retrieved.tzinfo is not None
        assert retrieved == datetime(2025, 1, 15, 12, 0, 0, tzinfo=timezone.utc)

        obs = decoded.vendor_commercial_result.observations[0]
        assert obs.source_name == "Ingram"
        assert obs.explicit_candidate_mpn == "BCM957608-P2200GQF00"
        assert obs.vendor_mpn_match_type == "EXACT"
        assert obs.price_amount == Decimal("2120.00")
        assert obs.currency_code == "USD"
        assert obs.availability == "IN_STOCK"
        assert obs.price_basis == "CUSTOMER_PRICE"
        assert obs.quantity == 10
        assert obs.note_kind is None
        assert obs.brand_new is True
        assert obs.brand_new_basis == "VENDOR_API_POLICY"

        issue = decoded.vendor_commercial_result.source_issues[0]
        assert issue.source_name == "CDW"
        assert issue.outcome == "NOT_FOUND"
        assert issue.detail is None

    def test_decimal_exactness(self) -> None:
        """Decimal values survive round trip without precision loss."""
        original = _make_result(
            vendor_commercial_result=VendorCommercialResult(
                lookup_status="SUCCESS",
                retrieved_at=None,
                observations=(
                    SupplementSourceObservation(
                        source_name="Test",
                        explicit_candidate_mpn="ABC123",
                        vendor_mpn_match_type="NORMALIZED_EXACT",
                        price_amount=Decimal("1234.567890123"),
                        currency_code="EUR",
                        availability="UNKNOWN",
                        price_basis="RETAIL_PRICE_FALLBACK",
                        quantity=0,
                        note_kind=None,
                        brand_new=True,
                        brand_new_basis="VENDOR_API_POLICY",
                    ),
                ),
                source_issues=(),
            ),
        )
        encoded = encode_research_supplement_result(original)
        decoded = decode_research_supplement_result(encoded)

        obs = decoded.vendor_commercial_result.observations[0]
        assert obs.price_amount == Decimal("1234.567890123")

    def test_failed_status_no_retrieved_at(self) -> None:
        original = _make_result(
            vendor_commercial_result=VendorCommercialResult(
                lookup_status="FAILED",
                retrieved_at=None,
                observations=(),
                source_issues=(),
            ),
        )
        encoded = encode_research_supplement_result(original)
        decoded = decode_research_supplement_result(encoded)

        assert decoded.vendor_commercial_result.lookup_status == "FAILED"
        assert decoded.vendor_commercial_result.retrieved_at is None

    def test_note_kind_preserved(self) -> None:
        original = _make_result(
            vendor_commercial_result=VendorCommercialResult(
                lookup_status="SUCCESS",
                retrieved_at=None,
                observations=(
                    SupplementSourceObservation(
                        source_name="Synnex EU",
                        explicit_candidate_mpn="ABC123",
                        vendor_mpn_match_type="EXACT",
                        price_amount=Decimal("100.00"),
                        currency_code="EUR",
                        availability="IN_STOCK",
                        price_basis="LIST_PRICE",
                        quantity=30,
                        note_kind="NO_RETURNS",
                        brand_new=True,
                        brand_new_basis="VENDOR_API_POLICY",
                    ),
                ),
                source_issues=(),
            ),
        )
        encoded = encode_research_supplement_result(original)
        decoded = decode_research_supplement_result(encoded)

        obs = decoded.vendor_commercial_result.observations[0]
        assert obs.note_kind == "NO_RETURNS"

    def test_empty_observations(self) -> None:
        original = _make_result(
            vendor_commercial_result=VendorCommercialResult(
                lookup_status="PARTIAL",
                retrieved_at=datetime(2025, 1, 1, 0, 0, 0, tzinfo=timezone.utc),
                observations=(),
                source_issues=(
                    SupplementSourceIssue(
                        source_name="Ingram",
                        outcome="NOT_FOUND",
                        detail=None,
                    ),
                ),
            ),
        )
        encoded = encode_research_supplement_result(original)
        decoded = decode_research_supplement_result(encoded)

        assert len(decoded.vendor_commercial_result.observations) == 0
        assert len(decoded.vendor_commercial_result.source_issues) == 1

    def test_round_trip_returns_aware_datetime(self) -> None:
        """Round trip must return timezone-aware datetime, not string."""
        dt = datetime(2025, 6, 15, 14, 30, 0, tzinfo=timezone.utc)
        original = _make_result(
            vendor_commercial_result=VendorCommercialResult(
                lookup_status="SUCCESS",
                retrieved_at=dt,
                observations=(),
                source_issues=(),
            ),
        )
        encoded = encode_research_supplement_result(original)
        decoded = decode_research_supplement_result(encoded)

        result_dt = decoded.vendor_commercial_result.retrieved_at
        assert isinstance(result_dt, datetime)
        assert result_dt.tzinfo is not None
        assert result_dt == dt


class TestCodecStrictValidation:
    def test_extra_top_level_keys_rejected(self) -> None:
        payload = {
            "schema_version": 1,
            "vendor_commercial_result": {
                "lookup_status": "SUCCESS",
                "retrieved_at": None,
                "observations": [],
                "source_issues": [],
            },
            "extra_field": "should fail",
        }
        with pytest.raises(SupplementCodecError, match="unexpected.*top-level"):
            decode_research_supplement_result(payload)

    def test_missing_top_level_keys_rejected(self) -> None:
        payload = {
            "schema_version": 1,
        }
        with pytest.raises(SupplementCodecError, match="missing.*top-level"):
            decode_research_supplement_result(payload)

    def test_wrong_schema_version_rejected(self) -> None:
        payload = {
            "schema_version": 2,
            "vendor_commercial_result": {
                "lookup_status": "SUCCESS",
                "retrieved_at": None,
                "observations": [],
                "source_issues": [],
            },
        }
        with pytest.raises(SupplementCodecError, match="unsupported schema_version"):
            decode_research_supplement_result(payload)

    def test_invalid_lookup_status_rejected(self) -> None:
        payload = {
            "schema_version": 1,
            "vendor_commercial_result": {
                "lookup_status": "INVALID_STATUS",
                "retrieved_at": None,
                "observations": [],
                "source_issues": [],
            },
        }
        with pytest.raises(SupplementCodecError, match="invalid lookup_status"):
            decode_research_supplement_result(payload)

    def test_extra_keys_in_observations_rejected(self) -> None:
        payload = {
            "schema_version": 1,
            "vendor_commercial_result": {
                "lookup_status": "SUCCESS",
                "retrieved_at": None,
                "observations": [
                    {
                        "source_name": "Test",
                        "explicit_candidate_mpn": "ABC123",
                        "vendor_mpn_match_type": "EXACT",
                        "price_amount": "100.00",
                        "currency_code": "USD",
                        "availability": "IN_STOCK",
                        "price_basis": "CUSTOMER_PRICE",
                        "quantity": None,
                        "note_kind": None,
                        "brand_new": True,
                        "brand_new_basis": "VENDOR_API_POLICY",
                        "extra_obs_field": "bad",
                    },
                ],
                "source_issues": [],
            },
        }
        with pytest.raises(SupplementCodecError, match="unexpected keys in observations"):
            decode_research_supplement_result(payload)

    def test_missing_keys_in_observations_rejected(self) -> None:
        payload = {
            "schema_version": 1,
            "vendor_commercial_result": {
                "lookup_status": "SUCCESS",
                "retrieved_at": None,
                "observations": [
                    {
                        "source_name": "Test",
                        "explicit_candidate_mpn": "ABC123",
                        # missing vendor_mpn_match_type, price_amount, etc.
                    },
                ],
                "source_issues": [],
            },
        }
        with pytest.raises(SupplementCodecError, match="missing keys in observations"):
            decode_research_supplement_result(payload)

    def test_invalid_availability_rejected(self) -> None:
        payload = {
            "schema_version": 1,
            "vendor_commercial_result": {
                "lookup_status": "SUCCESS",
                "retrieved_at": None,
                "observations": [
                    {
                        "source_name": "Test",
                        "explicit_candidate_mpn": "ABC123",
                        "vendor_mpn_match_type": "EXACT",
                        "price_amount": "100.00",
                        "currency_code": "USD",
                        "availability": "INVALID_AVAIL",
                        "price_basis": "CUSTOMER_PRICE",
                        "quantity": None,
                        "note_kind": None,
                        "brand_new": True,
                        "brand_new_basis": "VENDOR_API_POLICY",
                    },
                ],
                "source_issues": [],
            },
        }
        with pytest.raises(SupplementCodecError, match="invalid availability"):
            decode_research_supplement_result(payload)

    def test_invalid_note_kind_rejected(self) -> None:
        payload = {
            "schema_version": 1,
            "vendor_commercial_result": {
                "lookup_status": "SUCCESS",
                "retrieved_at": None,
                "observations": [
                    {
                        "source_name": "Test",
                        "explicit_candidate_mpn": "ABC123",
                        "vendor_mpn_match_type": "EXACT",
                        "price_amount": "100.00",
                        "currency_code": "USD",
                        "availability": "IN_STOCK",
                        "price_basis": "CUSTOMER_PRICE",
                        "quantity": None,
                        "note_kind": "RANDOM_NOTE",
                        "brand_new": True,
                        "brand_new_basis": "VENDOR_API_POLICY",
                    },
                ],
                "source_issues": [],
            },
        }
        with pytest.raises(SupplementCodecError, match="invalid note_kind"):
            decode_research_supplement_result(payload)

    def test_invalid_match_type_rejected(self) -> None:
        payload = {
            "schema_version": 1,
            "vendor_commercial_result": {
                "lookup_status": "SUCCESS",
                "retrieved_at": None,
                "observations": [
                    {
                        "source_name": "Test",
                        "explicit_candidate_mpn": "ABC123",
                        "vendor_mpn_match_type": "PARTIAL",
                        "price_amount": "100.00",
                        "currency_code": "USD",
                        "availability": "IN_STOCK",
                        "price_basis": "CUSTOMER_PRICE",
                        "quantity": None,
                        "note_kind": None,
                        "brand_new": True,
                        "brand_new_basis": "VENDOR_API_POLICY",
                    },
                ],
                "source_issues": [],
            },
        }
        with pytest.raises(SupplementCodecError, match="invalid vendor_mpn_match_type"):
            decode_research_supplement_result(payload)

    def test_invalid_outcome_rejected(self) -> None:
        payload = {
            "schema_version": 1,
            "vendor_commercial_result": {
                "lookup_status": "SUCCESS",
                "retrieved_at": None,
                "observations": [],
                "source_issues": [
                    {
                        "source_name": "Test",
                        "outcome": "UNKNOWN_OUTCOME",
                        "detail": None,
                    },
                ],
            },
        }
        with pytest.raises(SupplementCodecError, match="invalid outcome"):
            decode_research_supplement_result(payload)

    def test_non_dict_payload_rejected(self) -> None:
        with pytest.raises(SupplementCodecError, match="must be a dict"):
            decode_research_supplement_result("not a dict")  # type: ignore[arg-type]

    def test_decimal_as_float_rejected(self) -> None:
        """Decimal values must be strings, not floats."""
        payload = {
            "schema_version": 1,
            "vendor_commercial_result": {
                "lookup_status": "SUCCESS",
                "retrieved_at": None,
                "observations": [
                    {
                        "source_name": "Test",
                        "explicit_candidate_mpn": "ABC123",
                        "vendor_mpn_match_type": "EXACT",
                        "price_amount": 100.00,
                        "currency_code": "USD",
                        "availability": "IN_STOCK",
                        "price_basis": "CUSTOMER_PRICE",
                        "quantity": None,
                        "note_kind": None,
                        "brand_new": True,
                        "brand_new_basis": "VENDOR_API_POLICY",
                    },
                ],
                "source_issues": [],
            },
        }
        with pytest.raises(SupplementCodecError, match="must be a string"):
            decode_research_supplement_result(payload)

    def test_brand_new_must_be_bool(self) -> None:
        payload = {
            "schema_version": 1,
            "vendor_commercial_result": {
                "lookup_status": "SUCCESS",
                "retrieved_at": None,
                "observations": [
                    {
                        "source_name": "Test",
                        "explicit_candidate_mpn": "ABC123",
                        "vendor_mpn_match_type": "EXACT",
                        "price_amount": "100.00",
                        "currency_code": "USD",
                        "availability": "IN_STOCK",
                        "price_basis": "CUSTOMER_PRICE",
                        "quantity": None,
                        "note_kind": None,
                        "brand_new": "true",
                        "brand_new_basis": "VENDOR_API_POLICY",
                    },
                ],
                "source_issues": [],
            },
        }
        with pytest.raises(SupplementCodecError, match="must be a bool"):
            decode_research_supplement_result(payload)

    def test_extra_keys_in_source_issues_rejected(self) -> None:
        payload = {
            "schema_version": 1,
            "vendor_commercial_result": {
                "lookup_status": "SUCCESS",
                "retrieved_at": None,
                "observations": [],
                "source_issues": [
                    {
                        "source_name": "Test",
                        "outcome": "NOT_FOUND",
                        "detail": None,
                        "extra_issue_field": "bad",
                    },
                ],
            },
        }
        with pytest.raises(SupplementCodecError, match="unexpected keys in source_issues"):
            decode_research_supplement_result(payload)


# ---------------------------------------------------------------------------
# Datetime validation
# ---------------------------------------------------------------------------


class TestDatetimeValidation:
    def test_naive_datetime_rejected_on_encode(self) -> None:
        """Naive datetime must be rejected at domain object construction."""
        naive_dt = datetime(2025, 1, 15, 12, 0, 0)
        with pytest.raises(ValueError, match="timezone-aware"):
            VendorCommercialResult(
                lookup_status="SUCCESS",
                retrieved_at=naive_dt,
                observations=(),
                source_issues=(),
            )

    def test_malformed_retrieved_at_rejected(self) -> None:
        """Malformed datetime string rejected on decode."""
        payload = {
            "schema_version": 1,
            "vendor_commercial_result": {
                "lookup_status": "SUCCESS",
                "retrieved_at": "not-a-datetime",
                "observations": [],
                "source_issues": [],
            },
        }
        with pytest.raises(SupplementCodecError, match="retrieved_at"):
            decode_research_supplement_result(payload)

    def test_non_utc_retrieved_at_rejected(self) -> None:
        """Non-UTC offset in persisted datetime is rejected."""
        payload = {
            "schema_version": 1,
            "vendor_commercial_result": {
                "lookup_status": "SUCCESS",
                "retrieved_at": "2025-01-15T12:00:00+05:00",
                "observations": [],
                "source_issues": [],
            },
        }
        with pytest.raises(SupplementCodecError, match="must be UTC"):
            decode_research_supplement_result(payload)

    def test_zulu_datetime_accepted(self) -> None:
        """Z suffix (UTC) is accepted on decode."""
        payload = {
            "schema_version": 1,
            "vendor_commercial_result": {
                "lookup_status": "SUCCESS",
                "retrieved_at": "2025-01-15T12:00:00Z",
                "observations": [],
                "source_issues": [],
            },
        }
        decoded = decode_research_supplement_result(payload)
        dt = decoded.vendor_commercial_result.retrieved_at
        assert isinstance(dt, datetime)
        assert dt.tzinfo is not None
        assert dt == datetime(2025, 1, 15, 12, 0, 0, tzinfo=timezone.utc)

    def test_null_retrieved_at_decoded_as_none(self) -> None:
        payload = {
            "schema_version": 1,
            "vendor_commercial_result": {
                "lookup_status": "FAILED",
                "retrieved_at": None,
                "observations": [],
                "source_issues": [],
            },
        }
        decoded = decode_research_supplement_result(payload)
        assert decoded.vendor_commercial_result.retrieved_at is None


# ---------------------------------------------------------------------------
# Decimal / NaN / Infinity validation
# ---------------------------------------------------------------------------


class TestDecimalValidation:
    def test_nan_decimal_rejected_on_decode(self) -> None:
        payload = {
            "schema_version": 1,
            "vendor_commercial_result": {
                "lookup_status": "SUCCESS",
                "retrieved_at": None,
                "observations": [
                    {
                        "source_name": "Test",
                        "explicit_candidate_mpn": "ABC123",
                        "vendor_mpn_match_type": "EXACT",
                        "price_amount": "NaN",
                        "currency_code": "USD",
                        "availability": "IN_STOCK",
                        "price_basis": "CUSTOMER_PRICE",
                        "quantity": None,
                        "note_kind": None,
                        "brand_new": True,
                        "brand_new_basis": "VENDOR_API_POLICY",
                    },
                ],
                "source_issues": [],
            },
        }
        with pytest.raises(SupplementCodecError, match="non-finite"):
            decode_research_supplement_result(payload)

    def test_infinity_decimal_rejected_on_decode(self) -> None:
        payload = {
            "schema_version": 1,
            "vendor_commercial_result": {
                "lookup_status": "SUCCESS",
                "retrieved_at": None,
                "observations": [
                    {
                        "source_name": "Test",
                        "explicit_candidate_mpn": "ABC123",
                        "vendor_mpn_match_type": "EXACT",
                        "price_amount": "Infinity",
                        "currency_code": "USD",
                        "availability": "IN_STOCK",
                        "price_basis": "CUSTOMER_PRICE",
                        "quantity": None,
                        "note_kind": None,
                        "brand_new": True,
                        "brand_new_basis": "VENDOR_API_POLICY",
                    },
                ],
                "source_issues": [],
            },
        }
        with pytest.raises(SupplementCodecError, match="non-finite"):
            decode_research_supplement_result(payload)

    def test_negative_infinity_rejected_on_decode(self) -> None:
        payload = {
            "schema_version": 1,
            "vendor_commercial_result": {
                "lookup_status": "SUCCESS",
                "retrieved_at": None,
                "observations": [
                    {
                        "source_name": "Test",
                        "explicit_candidate_mpn": "ABC123",
                        "vendor_mpn_match_type": "EXACT",
                        "price_amount": "-Infinity",
                        "currency_code": "USD",
                        "availability": "IN_STOCK",
                        "price_basis": "CUSTOMER_PRICE",
                        "quantity": None,
                        "note_kind": None,
                        "brand_new": True,
                        "brand_new_basis": "VENDOR_API_POLICY",
                    },
                ],
                "source_issues": [],
            },
        }
        with pytest.raises(SupplementCodecError, match="non-finite"):
            decode_research_supplement_result(payload)

    def test_nan_decimal_rejected_in_domain_object(self) -> None:
        """NaN Decimal rejected at SupplementSourceObservation construction."""
        with pytest.raises(ValueError, match="finite"):
            SupplementSourceObservation(
                source_name="Test",
                explicit_candidate_mpn="ABC123",
                vendor_mpn_match_type="EXACT",
                price_amount=Decimal("NaN"),
                currency_code="USD",
                availability="IN_STOCK",
                price_basis="CUSTOMER_PRICE",
                quantity=None,
                note_kind=None,
                brand_new=True,
                brand_new_basis="VENDOR_API_POLICY",
            )

    def test_negative_price_rejected_in_domain_object(self) -> None:
        with pytest.raises(ValueError, match="not be negative"):
            SupplementSourceObservation(
                source_name="Test",
                explicit_candidate_mpn="ABC123",
                vendor_mpn_match_type="EXACT",
                price_amount=Decimal("-100.00"),
                currency_code="USD",
                availability="IN_STOCK",
                price_basis="CUSTOMER_PRICE",
                quantity=None,
                note_kind=None,
                brand_new=True,
                brand_new_basis="VENDOR_API_POLICY",
            )


# ---------------------------------------------------------------------------
# Quantity validation
# ---------------------------------------------------------------------------


class TestQuantityValidation:
    def test_bool_quantity_rejected_on_decode(self) -> None:
        """bool is subclass of int but must be rejected."""
        payload = {
            "schema_version": 1,
            "vendor_commercial_result": {
                "lookup_status": "SUCCESS",
                "retrieved_at": None,
                "observations": [
                    {
                        "source_name": "Test",
                        "explicit_candidate_mpn": "ABC123",
                        "vendor_mpn_match_type": "EXACT",
                        "price_amount": "100.00",
                        "currency_code": "USD",
                        "availability": "IN_STOCK",
                        "price_basis": "CUSTOMER_PRICE",
                        "quantity": True,  # bool instead of int
                        "note_kind": None,
                        "brand_new": True,
                        "brand_new_basis": "VENDOR_API_POLICY",
                    },
                ],
                "source_issues": [],
            },
        }
        with pytest.raises(SupplementCodecError, match="must be an int"):
            decode_research_supplement_result(payload)

    def test_negative_quantity_rejected_on_decode(self) -> None:
        payload = {
            "schema_version": 1,
            "vendor_commercial_result": {
                "lookup_status": "SUCCESS",
                "retrieved_at": None,
                "observations": [
                    {
                        "source_name": "Test",
                        "explicit_candidate_mpn": "ABC123",
                        "vendor_mpn_match_type": "EXACT",
                        "price_amount": "100.00",
                        "currency_code": "USD",
                        "availability": "IN_STOCK",
                        "price_basis": "CUSTOMER_PRICE",
                        "quantity": -5,
                        "note_kind": None,
                        "brand_new": True,
                        "brand_new_basis": "VENDOR_API_POLICY",
                    },
                ],
                "source_issues": [],
            },
        }
        with pytest.raises(SupplementCodecError, match="non-negative"):
            decode_research_supplement_result(payload)

    def test_negative_quantity_rejected_in_domain_object(self) -> None:
        with pytest.raises(ValueError, match="not be negative"):
            SupplementSourceObservation(
                source_name="Test",
                explicit_candidate_mpn="ABC123",
                vendor_mpn_match_type="EXACT",
                price_amount=Decimal("100.00"),
                currency_code="USD",
                availability="IN_STOCK",
                price_basis="CUSTOMER_PRICE",
                quantity=-1,
                note_kind=None,
                brand_new=True,
                brand_new_basis="VENDOR_API_POLICY",
            )

    def test_bool_quantity_rejected_in_domain_object(self) -> None:
        """bool quantity rejected at domain object construction."""
        with pytest.raises(TypeError, match="must be an int"):
            SupplementSourceObservation(
                source_name="Test",
                explicit_candidate_mpn="ABC123",
                vendor_mpn_match_type="EXACT",
                price_amount=Decimal("100.00"),
                currency_code="USD",
                availability="IN_STOCK",
                price_basis="CUSTOMER_PRICE",
                quantity=True,
                note_kind=None,
                brand_new=True,
                brand_new_basis="VENDOR_API_POLICY",
            )


# ---------------------------------------------------------------------------
# brand_new_basis validation
# ---------------------------------------------------------------------------


class TestBrandNewBasisValidation:
    def test_invalid_brand_new_basis_rejected_on_decode(self) -> None:
        payload = {
            "schema_version": 1,
            "vendor_commercial_result": {
                "lookup_status": "SUCCESS",
                "retrieved_at": None,
                "observations": [
                    {
                        "source_name": "Test",
                        "explicit_candidate_mpn": "ABC123",
                        "vendor_mpn_match_type": "EXACT",
                        "price_amount": "100.00",
                        "currency_code": "USD",
                        "availability": "IN_STOCK",
                        "price_basis": "CUSTOMER_PRICE",
                        "quantity": None,
                        "note_kind": None,
                        "brand_new": True,
                        "brand_new_basis": "UNKNOWN_POLICY",
                    },
                ],
                "source_issues": [],
            },
        }
        with pytest.raises(SupplementCodecError, match="invalid brand_new_basis"):
            decode_research_supplement_result(payload)

    def test_invalid_brand_new_basis_rejected_in_domain_object(self) -> None:
        with pytest.raises(ValueError, match="VENDOR_API_POLICY"):
            SupplementSourceObservation(
                source_name="Test",
                explicit_candidate_mpn="ABC123",
                vendor_mpn_match_type="EXACT",
                price_amount=Decimal("100.00"),
                currency_code="USD",
                availability="IN_STOCK",
                price_basis="CUSTOMER_PRICE",
                quantity=None,
                note_kind=None,
                brand_new=True,
                brand_new_basis="WRONG_POLICY",
            )


# ---------------------------------------------------------------------------
# Encode-side validation
# ---------------------------------------------------------------------------


class TestEncodeSideValidation:
    def test_invalid_lookup_status_rejected_on_encode(self) -> None:
        """Invalid lookup_status rejected at domain object construction."""
        with pytest.raises(ValueError, match="invalid lookup_status"):
            VendorCommercialResult(
                lookup_status="INVALID",
                retrieved_at=None,
                observations=(),
                source_issues=(),
            )

    def test_naive_datetime_rejected_on_encode_via_codec(self) -> None:
        """Naive datetime in VendorCommercialResult rejected at construction."""
        naive_dt = datetime(2025, 1, 15, 12, 0, 0)
        with pytest.raises(ValueError, match="timezone-aware"):
            VendorCommercialResult(
                lookup_status="SUCCESS",
                retrieved_at=naive_dt,
                observations=(),
                source_issues=(),
            )

    def test_nan_decimal_rejected_on_encode(self) -> None:
        """NaN Decimal rejected at domain object construction."""
        with pytest.raises(ValueError, match="finite"):
            SupplementSourceObservation(
                source_name="Test",
                explicit_candidate_mpn="ABC123",
                vendor_mpn_match_type="EXACT",
                price_amount=Decimal("NaN"),
                currency_code="USD",
                availability="IN_STOCK",
                price_basis="CUSTOMER_PRICE",
                quantity=None,
                note_kind=None,
                brand_new=True,
                brand_new_basis="VENDOR_API_POLICY",
            )


# ---------------------------------------------------------------------------
# Issue detail controlled vocabulary
# ---------------------------------------------------------------------------


class TestIssueDetailControlledVocabulary:
    """Prove SupplementSourceIssue.detail is restricted to controlled constants."""

    def test_detail_none_allowed(self) -> None:
        """detail=None is always allowed."""
        issue = SupplementSourceIssue(
            source_name="Ingram",
            outcome="NOT_FOUND",
            detail=None,
        )
        assert issue.detail is None

    def test_detail_vendor_mpn_mismatch_allowed(self) -> None:
        """detail='vendor_mpn_mismatch' is the only non-None allowed value."""
        issue = SupplementSourceIssue(
            source_name="CDW",
            outcome="MPN_MISMATCH",
            detail="vendor_mpn_mismatch",
        )
        assert issue.detail == "vendor_mpn_mismatch"

    def test_arbitrary_detail_rejected_in_domain_object(self) -> None:
        """Arbitrary free-form detail is rejected at construction."""
        with pytest.raises(ValueError, match="detail must be"):
            SupplementSourceIssue(
                source_name="Ingram",
                outcome="MALFORMED_SECTION",
                detail="some arbitrary free text from the vendor",
            )

    def test_arbitrary_detail_rejected_on_decode(self) -> None:
        """Arbitrary free-form detail rejected during codec decode."""
        payload = {
            "schema_version": 1,
            "vendor_commercial_result": {
                "lookup_status": "SUCCESS",
                "retrieved_at": None,
                "observations": [],
                "source_issues": [
                    {
                        "source_name": "Ingram",
                        "outcome": "MALFORMED_SECTION",
                        "detail": "raw upstream error: connection reset by peer",
                    },
                ],
            },
        }
        with pytest.raises(SupplementCodecError, match="invalid detail"):
            decode_research_supplement_result(payload)


class TestProviderContractNoBrandNew:
    """Prove CommercialSourceCandidate carries NO brand-new business-policy."""

    def test_provider_candidate_no_brand_new(self) -> None:
        """CommercialSourceCandidate has no brand_new field."""
        from product_intelligence.providers.commercial import (
            CommercialSourceCandidate,
        )
        c = CommercialSourceCandidate(
            source_name="Ingram",
            explicit_candidate_mpn="ABC123",
            price_amount=Decimal("100.00"),
            currency_code="USD",
            availability=CommercialAvailability.IN_STOCK,
            price_basis=CommercialPriceBasis.CUSTOMER_PRICE,
        )
        assert not hasattr(c, 'brand_new')
        assert not hasattr(c, 'brand_new_basis')

    def test_provider_candidate_decimal_is_finite(self) -> None:
        """Provider contract enforces finite Decimal price."""
        from product_intelligence.providers.commercial import (
            CommercialSourceCandidate,
        )
        with pytest.raises(ValueError, match="finite"):
            CommercialSourceCandidate(
                source_name="Ingram",
                explicit_candidate_mpn="ABC123",
                price_amount=Decimal("NaN"),
                currency_code="USD",
                availability=CommercialAvailability.IN_STOCK,
                price_basis=CommercialPriceBasis.CUSTOMER_PRICE,
            )

    def test_provider_candidate_no_float_price(self) -> None:
        """Binary float rejected at provider contract."""
        from product_intelligence.providers.commercial import (
            CommercialSourceCandidate,
        )
        with pytest.raises(TypeError, match="Decimal"):
            CommercialSourceCandidate(
                source_name="Ingram",
                explicit_candidate_mpn="ABC123",
                price_amount=100.00,  # type: ignore[arg-type]
                currency_code="USD",
                availability=CommercialAvailability.IN_STOCK,
                price_basis=CommercialPriceBasis.CUSTOMER_PRICE,
            )
