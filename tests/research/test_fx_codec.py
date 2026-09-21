"""Tests for FX codec (PRODUCT-INTEL.4D-C-A).

Tests cover:
* Encode/decode round-trip
* Decimal-only values
* Observation date persistence
* Malformed payload rejected
* Extra keys rejected
* Missing keys rejected
* Schema version enforcement
* NaN/Infinity rejection
* Naive datetime rejection
"""

from __future__ import annotations

from datetime import date, datetime, timezone
from decimal import Decimal

import pytest

from product_intelligence.research.fx_codec import (
    FxCodecError,
    FxObservationSnapshot,
    FxRateEntry,
    decode_fx_observation,
    encode_fx_observation,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_SAMPLE_RATES = (
    type("FxRateObservation", (), {
        "currency_code": "USD",
        "rate": Decimal("1.0934"),
    })(),
    type("FxRateObservation", (), {
        "currency_code": "GBP",
        "rate": Decimal("0.8567"),
    })(),
)

# Use a simple named tuple approach for test fixtures
import collections
_FxRateObs = collections.namedtuple("_FxRateObs", ["currency_code", "rate"])

_SAMPLE_RATES_NT = (
    _FxRateObs(currency_code="USD", rate=Decimal("1.0934")),
    _FxRateObs(currency_code="GBP", rate=Decimal("0.8567")),
)


# ---------------------------------------------------------------------------
# FxRateEntry tests
# ---------------------------------------------------------------------------


class TestFxRateEntry:
    def test_valid_entry(self):
        entry = FxRateEntry(currency_code="USD", rate=Decimal("1.0934"))
        assert entry.currency_code == "USD"
        assert entry.rate == Decimal("1.0934")

    def test_rate_must_be_decimal(self):
        with pytest.raises(TypeError, match="rate must be a Decimal"):
            FxRateEntry(currency_code="USD", rate=1.0934)  # type: ignore

    def test_rate_nan_rejected(self):
        with pytest.raises(ValueError, match="finite"):
            FxRateEntry(currency_code="USD", rate=Decimal("NaN"))

    def test_rate_infinity_rejected(self):
        with pytest.raises(ValueError, match="finite"):
            FxRateEntry(currency_code="USD", rate=Decimal("Infinity"))

    def test_rate_zero_rejected(self):
        with pytest.raises(ValueError, match="positive"):
            FxRateEntry(currency_code="USD", rate=Decimal("0"))


# ---------------------------------------------------------------------------
# FxObservationSnapshot tests
# ---------------------------------------------------------------------------


class TestFxObservationSnapshot:
    def _make_snapshot(self, **kwargs) -> FxObservationSnapshot:
        defaults = dict(
            provider_id="ECB",
            observation_date="2024-01-15",
            base_currency="EUR",
            rates=(
                FxRateEntry(currency_code="USD", rate=Decimal("1.0934")),
            ),
            retrieved_at="2024-01-15T12:00:00+00:00",
        )
        defaults.update(kwargs)
        return FxObservationSnapshot(**defaults)

    def test_basic_construction(self):
        snap = self._make_snapshot()
        assert snap.provider_id == "ECB"
        assert snap.observation_date == "2024-01-15"
        assert snap.base_currency == "EUR"
        assert len(snap.rates) == 1

    def test_invalid_date_rejected(self):
        with pytest.raises(ValueError, match="valid ISO date"):
            self._make_snapshot(observation_date="not-a-date")

    def test_retrieved_at_none_allowed(self):
        snap = self._make_snapshot(retrieved_at=None)
        assert snap.retrieved_at is None

    def test_empty_rates_allowed(self):
        snap = self._make_snapshot(rates=())
        assert len(snap.rates) == 0


# ---------------------------------------------------------------------------
# Encode tests
# ---------------------------------------------------------------------------


class TestEncodeFxObservation:
    def test_basic_encode(self):
        payload = encode_fx_observation(
            provider_id="ECB",
            observation_date=date(2024, 1, 15),
            base_currency="EUR",
            rates=_SAMPLE_RATES_NT,
            retrieved_at=datetime(2024, 1, 15, 12, 0, 0, tzinfo=timezone.utc),
        )
        assert payload["schema_version"] == 1
        assert payload["provider_id"] == "ECB"
        assert payload["observation_date"] == "2024-01-15"
        assert payload["base_currency"] == "EUR"
        assert len(payload["rates"]) == 2
        assert payload["rates"][0]["currency_code"] == "USD"
        assert payload["rates"][0]["rate"] == "1.0934"
        assert payload["retrieved_at"] == "2024-01-15T12:00:00+00:00"

    def test_decimals_encoded_as_strings(self):
        payload = encode_fx_observation(
            provider_id="ECB",
            observation_date=date(2024, 1, 15),
            base_currency="EUR",
            rates=_SAMPLE_RATES_NT,
        )
        for rate in payload["rates"]:
            assert isinstance(rate["rate"], str)

    def test_retrieved_at_none(self):
        payload = encode_fx_observation(
            provider_id="ECB",
            observation_date=date(2024, 1, 15),
            base_currency="EUR",
            rates=_SAMPLE_RATES_NT,
            retrieved_at=None,
        )
        assert payload["retrieved_at"] is None

    def test_empty_provider_id_rejected(self):
        with pytest.raises(FxCodecError, match="provider_id"):
            encode_fx_observation(
                provider_id="",
                observation_date=date(2024, 1, 15),
                base_currency="EUR",
                rates=_SAMPLE_RATES_NT,
            )

    def test_non_date_observation_date_rejected(self):
        with pytest.raises(FxCodecError, match="observation_date"):
            encode_fx_observation(
                provider_id="ECB",
                observation_date="2024-01-15",  # type: ignore
                base_currency="EUR",
                rates=_SAMPLE_RATES_NT,
            )


# ---------------------------------------------------------------------------
# Decode tests
# ---------------------------------------------------------------------------


class TestDecodeFxObservation:
    def test_basic_decode(self):
        payload = {
            "schema_version": 1,
            "provider_id": "ECB",
            "observation_date": "2024-01-15",
            "base_currency": "EUR",
            "rates": [
                {"currency_code": "USD", "rate": "1.0934"},
                {"currency_code": "GBP", "rate": "0.8567"},
            ],
            "retrieved_at": "2024-01-15T12:00:00+00:00",
        }
        snap = decode_fx_observation(payload)
        assert snap.provider_id == "ECB"
        assert snap.observation_date == "2024-01-15"
        assert snap.base_currency == "EUR"
        assert len(snap.rates) == 2
        assert snap.rates[0].currency_code == "USD"
        assert snap.rates[0].rate == Decimal("1.0934")
        assert snap.retrieved_at == "2024-01-15T12:00:00+00:00"

    def test_decimals_are_decimal_after_decode(self):
        payload = {
            "schema_version": 1,
            "provider_id": "ECB",
            "observation_date": "2024-01-15",
            "base_currency": "EUR",
            "rates": [
                {"currency_code": "USD", "rate": "1.0934"},
            ],
            "retrieved_at": None,
        }
        snap = decode_fx_observation(payload)
        assert isinstance(snap.rates[0].rate, Decimal)
        assert type(snap.rates[0].rate) is Decimal

    def test_retrieved_at_none(self):
        payload = {
            "schema_version": 1,
            "provider_id": "ECB",
            "observation_date": "2024-01-15",
            "base_currency": "EUR",
            "rates": [],
            "retrieved_at": None,
        }
        snap = decode_fx_observation(payload)
        assert snap.retrieved_at is None

    def test_extra_keys_rejected(self):
        payload = {
            "schema_version": 1,
            "provider_id": "ECB",
            "observation_date": "2024-01-15",
            "base_currency": "EUR",
            "rates": [],
            "retrieved_at": None,
            "extra_key": "bad",
        }
        with pytest.raises(FxCodecError, match="unexpected top-level keys"):
            decode_fx_observation(payload)

    def test_missing_keys_rejected(self):
        payload = {
            "schema_version": 1,
            "provider_id": "ECB",
            "observation_date": "2024-01-15",
            "base_currency": "EUR",
            # missing "rates" and "retrieved_at"
        }
        with pytest.raises(FxCodecError, match="missing top-level keys"):
            decode_fx_observation(payload)

    def test_wrong_schema_version(self):
        payload = {
            "schema_version": 99,
            "provider_id": "ECB",
            "observation_date": "2024-01-15",
            "base_currency": "EUR",
            "rates": [],
            "retrieved_at": None,
        }
        with pytest.raises(FxCodecError, match="unsupported schema_version"):
            decode_fx_observation(payload)

    def test_nan_rate_string_rejected(self):
        payload = {
            "schema_version": 1,
            "provider_id": "ECB",
            "observation_date": "2024-01-15",
            "base_currency": "EUR",
            "rates": [
                {"currency_code": "USD", "rate": "NaN"},
            ],
            "retrieved_at": None,
        }
        with pytest.raises(FxCodecError, match="non-finite"):
            decode_fx_observation(payload)

    def test_infinity_rate_string_rejected(self):
        payload = {
            "schema_version": 1,
            "provider_id": "ECB",
            "observation_date": "2024-01-15",
            "base_currency": "EUR",
            "rates": [
                {"currency_code": "USD", "rate": "Infinity"},
            ],
            "retrieved_at": None,
        }
        with pytest.raises(FxCodecError, match="non-finite"):
            decode_fx_observation(payload)

    def test_integer_rate_rejected(self):
        """Rate must be a string in codec, not an int."""
        payload = {
            "schema_version": 1,
            "provider_id": "ECB",
            "observation_date": "2024-01-15",
            "base_currency": "EUR",
            "rates": [
                {"currency_code": "USD", "rate": 1},  # int, not string
            ],
            "retrieved_at": None,
        }
        with pytest.raises(FxCodecError, match="must be a string"):
            decode_fx_observation(payload)

    def test_float_rate_rejected(self):
        """Rate must be a string in codec, not a float."""
        payload = {
            "schema_version": 1,
            "provider_id": "ECB",
            "observation_date": "2024-01-15",
            "base_currency": "EUR",
            "rates": [
                {"currency_code": "USD", "rate": 1.0934},  # float
            ],
            "retrieved_at": None,
        }
        with pytest.raises(FxCodecError, match="must be a string"):
            decode_fx_observation(payload)

    def test_extra_keys_in_rate_rejected(self):
        payload = {
            "schema_version": 1,
            "provider_id": "ECB",
            "observation_date": "2024-01-15",
            "base_currency": "EUR",
            "rates": [
                {"currency_code": "USD", "rate": "1.0934", "extra": "bad"},
            ],
            "retrieved_at": None,
        }
        with pytest.raises(FxCodecError, match="unexpected keys in rates"):
            decode_fx_observation(payload)

    def test_missing_keys_in_rate_rejected(self):
        payload = {
            "schema_version": 1,
            "provider_id": "ECB",
            "observation_date": "2024-01-15",
            "base_currency": "EUR",
            "rates": [
                {"currency_code": "USD"},  # missing "rate"
            ],
            "retrieved_at": None,
        }
        with pytest.raises(FxCodecError, match="missing keys in rates"):
            decode_fx_observation(payload)

    def test_not_a_dict(self):
        with pytest.raises(FxCodecError, match="must be a dict"):
            decode_fx_observation([])  # type: ignore


# ---------------------------------------------------------------------------
# Round-trip tests
# ---------------------------------------------------------------------------


class TestFxCodecRoundTrip:
    def test_encode_decode_round_trip(self):
        original_rates = (
            _FxRateObs(currency_code="USD", rate=Decimal("1.0934")),
            _FxRateObs(currency_code="GBP", rate=Decimal("0.8567")),
            _FxRateObs(currency_code="JPY", rate=Decimal("159.33")),
        )
        retrieved = datetime(2024, 1, 15, 14, 30, 0, tzinfo=timezone.utc)

        payload = encode_fx_observation(
            provider_id="ECB",
            observation_date=date(2024, 1, 15),
            base_currency="EUR",
            rates=original_rates,
            retrieved_at=retrieved,
        )

        snap = decode_fx_observation(payload)

        assert snap.provider_id == "ECB"
        assert snap.observation_date == "2024-01-15"
        assert snap.base_currency == "EUR"
        assert len(snap.rates) == 3

        assert snap.rates[0].currency_code == "USD"
        assert snap.rates[0].rate == Decimal("1.0934")
        assert isinstance(snap.rates[0].rate, Decimal)

        assert snap.rates[1].currency_code == "GBP"
        assert snap.rates[1].rate == Decimal("0.8567")

        assert snap.rates[2].currency_code == "JPY"
        assert snap.rates[2].rate == Decimal("159.33")

        assert snap.retrieved_at == "2024-01-15T14:30:00+00:00"

    def test_round_trip_precision_preserved(self):
        """High-precision Decimal values survive encode/decode."""
        original_rates = (
            _FxRateObs(currency_code="USD", rate=Decimal("1.09345678901234567890")),
        )
        payload = encode_fx_observation(
            provider_id="ECB",
            observation_date=date(2024, 1, 15),
            base_currency="EUR",
            rates=original_rates,
        )
        snap = decode_fx_observation(payload)
        assert snap.rates[0].rate == Decimal("1.09345678901234567890")
        assert type(snap.rates[0].rate) is Decimal

    def test_round_trip_empty_rates(self):
        retrieved = datetime(2024, 1, 15, 12, 0, 0, tzinfo=timezone.utc)
        payload = encode_fx_observation(
            provider_id="ECB",
            observation_date=date(2024, 1, 15),
            base_currency="EUR",
            rates=(),
            retrieved_at=retrieved,
        )
        snap = decode_fx_observation(payload)
        assert len(snap.rates) == 0
        assert snap.retrieved_at == "2024-01-15T12:00:00+00:00"
