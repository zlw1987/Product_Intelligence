"""Tests for the commercial supplement codec (PRODUCT-INTEL.4D-B).

Tests cover:
* V1 encode/decode round trip
* Strict required keys
* Reject extra keys (fail closed)
* Decimal exactness preserved
* Timezone-aware retrieved_at preserved
* Malformed payload fails closed
* Extra keys fail closed
* Unknown enum values rejected
"""

from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal

import pytest

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
                    detail="CDW: MPN not found",
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
        assert (
            decoded.vendor_commercial_result.retrieved_at
            == "2025-01-15T12:00:00+00:00"
        )
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
        assert issue.detail == "CDW: MPN not found"

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
                        "price_amount": 100.00,  # float instead of string
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
                        "brand_new": "true",  # string instead of bool
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
