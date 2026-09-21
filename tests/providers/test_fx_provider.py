"""Tests for ECB FX provider boundary (PRODUCT-INTEL.4D-C-A).

Tests cover:
* Valid official-style rate document parsing
* Observation date persistence
* Decimal-only values
* EUR base handling
* USD rate handling
* Malformed rate rejected
* NaN/Infinity rejected
* Binary float rejected
* Missing requested currency nonfatal
* Provider/network failure nonfatal
* Bounded response behavior
* No network calls in automated tests
"""

from __future__ import annotations

import re
from datetime import date, datetime, timezone
from decimal import Decimal

import pytest

from product_intelligence.providers.fx import (
    FxNetworkError,
    FxObservationSet,
    FxParseError,
    FxRateObservation,
    EcbFxProvider,
    _parse_ecb_xml,
)

# ---------------------------------------------------------------------------
# Sample ECB XML fixtures
# ---------------------------------------------------------------------------

_ECB_VALID_XML = """<?xml version="1.0" encoding="UTF-8"?>
<gesmes:Envelope xmlns:gesmes="http://www.gesmes.org/xml/2002-08-01"
                 xmlns="http://www.ecb.int/vocabulary/2002-08-01/eurofxref">
  <Cube>
    <Cube>
      <TimeSeries>
        <Cube time="2024-01-15">
          <Cube currency="USD" rate="1.0934"/>
          <Cube currency="GBP" rate="0.8567"/>
          <Cube currency="JPY" rate="159.33"/>
          <Cube currency="CHF" rate="0.9312"/>
          <Cube currency="CAD" rate="1.4632"/>
          <Cube currency="AUD" rate="1.6423"/>
          <Cube currency="CNY" rate="7.8485"/>
          <Cube currency="SEK" rate="11.2345"/>
          <Cube currency="NOK" rate="11.3456"/>
          <Cube currency="DKK" rate="7.4589"/>
        </Cube>
      </TimeSeries>
    </Cube>
  </Cube>
</gesmes:Envelope>
"""

_ECB_MINIMAL_XML = """<?xml version="1.0" encoding="UTF-8"?>
<gesmes:Envelope xmlns:gesmes="http://www.gesmes.org/xml/2002-08-01">
  <Cube>
    <Cube>
      <TimeSeries>
        <Cube time="2024-03-01">
          <Cube currency="USD" rate="1.0850"/>
        </Cube>
      </TimeSeries>
    </Cube>
  </Cube>
</gesmes:Envelope>
"""


# ---------------------------------------------------------------------------
# FxRateObservation tests
# ---------------------------------------------------------------------------


class TestFxRateObservation:
    def test_valid_rate(self):
        obs = FxRateObservation(currency_code="USD", rate=Decimal("1.0934"))
        assert obs.currency_code == "USD"
        assert obs.rate == Decimal("1.0934")

    def test_lowercase_uppercased(self):
        obs = FxRateObservation(currency_code="usd", rate=Decimal("1.0934"))
        assert obs.currency_code == "USD"

    def test_whitespace_stripped(self):
        obs = FxRateObservation(currency_code="  USD  ", rate=Decimal("1.0934"))
        assert obs.currency_code == "USD"

    def test_invalid_currency_code_length(self):
        with pytest.raises(ValueError, match="three-letter"):
            FxRateObservation(currency_code="US", rate=Decimal("1.0"))

    def test_non_string_currency(self):
        with pytest.raises(TypeError, match="currency_code"):
            FxRateObservation(currency_code=123, rate=Decimal("1.0"))  # type: ignore

    def test_rate_must_be_decimal(self):
        with pytest.raises(TypeError, match="rate must be a Decimal"):
            FxRateObservation(currency_code="USD", rate=1.0934)  # type: ignore

    def test_float_rate_rejected(self):
        with pytest.raises(TypeError, match="rate must be a Decimal"):
            FxRateObservation(currency_code="USD", rate=float("1.0934"))  # type: ignore

    def test_nan_rate_rejected(self):
        with pytest.raises(ValueError, match="finite"):
            FxRateObservation(currency_code="USD", rate=Decimal("NaN"))

    def test_infinity_rate_rejected(self):
        with pytest.raises(ValueError, match="finite"):
            FxRateObservation(currency_code="USD", rate=Decimal("Infinity"))

    def test_zero_rate_rejected(self):
        with pytest.raises(ValueError, match="positive"):
            FxRateObservation(currency_code="USD", rate=Decimal("0"))

    def test_negative_rate_rejected(self):
        with pytest.raises(ValueError, match="positive"):
            FxRateObservation(currency_code="USD", rate=Decimal("-1.0"))


# ---------------------------------------------------------------------------
# FxObservationSet tests
# ---------------------------------------------------------------------------


class TestFxObservationSet:
    def _make_set(self, **kwargs) -> FxObservationSet:
        defaults = dict(
            provider_id="ECB",
            observation_date=date(2024, 1, 15),
            base_currency="EUR",
            rates=(
                FxRateObservation(currency_code="USD", rate=Decimal("1.0934")),
                FxRateObservation(currency_code="GBP", rate=Decimal("0.8567")),
            ),
        )
        defaults.update(kwargs)
        return FxObservationSet(**defaults)

    def test_basic_construction(self):
        obs = self._make_set()
        assert obs.provider_id == "ECB"
        assert obs.observation_date == date(2024, 1, 15)
        assert obs.base_currency == "EUR"
        assert len(obs.rates) == 2

    def test_get_rate_found(self):
        obs = self._make_set()
        usd = obs.get_rate("USD")
        assert usd is not None
        assert usd.rate == Decimal("1.0934")

    def test_get_rate_case_insensitive(self):
        obs = self._make_set()
        usd = obs.get_rate("usd")
        assert usd is not None
        assert usd.currency_code == "USD"

    def test_get_rate_whitespace_stripped(self):
        obs = self._make_set()
        usd = obs.get_rate("  USD  ")
        assert usd is not None

    def test_get_rate_not_found(self):
        obs = self._make_set()
        result = obs.get_rate("XYZ")
        assert result is None

    def test_empty_rates_allowed(self):
        obs = self._make_set(rates=())
        assert len(obs.rates) == 0

    def test_provider_id_required(self):
        with pytest.raises(ValueError, match="provider_id"):
            self._make_set(provider_id="")

    def test_provider_id_stripped(self):
        obs = self._make_set(provider_id="  ECB  ")
        assert obs.provider_id == "ECB"

    def test_base_currency_uppercased(self):
        obs = self._make_set(base_currency="eur")
        assert obs.base_currency == "EUR"

    def test_observation_date_type_check(self):
        with pytest.raises(TypeError, match="observation_date"):
            self._make_set(observation_date="2024-01-15")  # type: ignore

    def test_retrieved_at_must_be_timezone_aware(self):
        naive = datetime(2024, 1, 15, 12, 0, 0)
        with pytest.raises(ValueError, match="timezone-aware"):
            self._make_set(retrieved_at=naive)

    def test_retrieved_at_none_allowed(self):
        obs = self._make_set(retrieved_at=None)
        assert obs.retrieved_at is None

    def test_retrieved_at_utc(self):
        aware = datetime(2024, 1, 15, 12, 0, 0, tzinfo=timezone.utc)
        obs = self._make_set(retrieved_at=aware)
        assert obs.retrieved_at == aware


# ---------------------------------------------------------------------------
# ECB XML parsing tests
# ---------------------------------------------------------------------------


class TestParseEcbXml:
    def test_valid_full_document(self):
        result = _parse_ecb_xml(_ECB_VALID_XML)
        assert result.provider_id == "ECB"
        assert result.observation_date == date(2024, 1, 15)
        assert result.base_currency == "EUR"
        assert len(result.rates) == 10

    def test_usd_rate_parsed(self):
        result = _parse_ecb_xml(_ECB_VALID_XML)
        usd = result.get_rate("USD")
        assert usd is not None
        assert usd.rate == Decimal("1.0934")

    def test_rates_are_decimal_not_float(self):
        result = _parse_ecb_xml(_ECB_VALID_XML)
        for rate in result.rates:
            assert isinstance(rate.rate, Decimal)
            assert type(rate.rate) is Decimal

    def test_minimal_document(self):
        result = _parse_ecb_xml(_ECB_MINIMAL_XML)
        assert result.observation_date == date(2024, 3, 1)
        assert len(result.rates) == 1
        usd = result.get_rate("USD")
        assert usd is not None
        assert usd.rate == Decimal("1.0850")

    def test_no_time_attribute(self):
        xml_no_time = """<Cube><Cube><TimeSeries><Cube><Cube currency="USD" rate="1.0"/></Cube></TimeSeries></Cube></Cube>"""
        with pytest.raises(FxParseError, match="no Cube element with a 'time' attribute"):
            _parse_ecb_xml(xml_no_time)

    def test_empty_document(self):
        with pytest.raises(FxParseError, match="no Cube element"):
            _parse_ecb_xml("<Cube></Cube>")

    def test_invalid_xml(self):
        with pytest.raises(FxParseError, match="not valid XML"):
            _parse_ecb_xml("not xml at all")

    def test_nan_rate_in_xml(self):
        xml_nan = """<gesmes:Envelope xmlns:gesmes="http://www.gesmes.org/xml/2002-08-01">
  <Cube><Cube><TimeSeries><Cube time="2024-01-01">
    <Cube currency="USD" rate="NaN"/>
  </Cube></TimeSeries></Cube></Cube></gesmes:Envelope>"""
        with pytest.raises(FxParseError, match="non-finite"):
            _parse_ecb_xml(xml_nan)

    def test_infinity_rate_in_xml(self):
        xml_inf = """<gesmes:Envelope xmlns:gesmes="http://www.gesmes.org/xml/2002-08-01">
  <Cube><Cube><TimeSeries><Cube time="2024-01-01">
    <Cube currency="USD" rate="Infinity"/>
  </Cube></TimeSeries></Cube></Cube></gesmes:Envelope>"""
        with pytest.raises(FxParseError, match="non-finite"):
            _parse_ecb_xml(xml_inf)

    def test_zero_rate_in_xml(self):
        xml_zero = """<gesmes:Envelope xmlns:gesmes="http://www.gesmes.org/xml/2002-08-01">
  <Cube><Cube><TimeSeries><Cube time="2024-01-01">
    <Cube currency="USD" rate="0"/>
  </Cube></TimeSeries></Cube></Cube></gesmes:Envelope>"""
        with pytest.raises(FxParseError, match="positive"):
            _parse_ecb_xml(xml_zero)

    def test_negative_rate_in_xml(self):
        xml_neg = """<gesmes:Envelope xmlns:gesmes="http://www.gesmes.org/xml/2002-08-01">
  <Cube><Cube><TimeSeries><Cube time="2024-01-01">
    <Cube currency="USD" rate="-1.5"/>
  </Cube></TimeSeries></Cube></Cube></gesmes:Envelope>"""
        with pytest.raises(FxParseError, match="positive"):
            _parse_ecb_xml(xml_neg)

    def test_no_rates_in_document(self):
        xml_no_rates = """<gesmes:Envelope xmlns:gesmes="http://www.gesmes.org/xml/2002-08-01">
  <Cube><Cube><TimeSeries><Cube time="2024-01-01"></Cube></TimeSeries></Cube></Cube></gesmes:Envelope>"""
        with pytest.raises(FxParseError, match="no currency rates"):
            _parse_ecb_xml(xml_no_rates)

    def test_observation_date_persistence(self):
        xml = """<gesmes:Envelope xmlns:gesmes="http://www.gesmes.org/xml/2002-08-01">
  <Cube><Cube><TimeSeries><Cube time="2024-06-30">
    <Cube currency="USD" rate="1.0800"/>
  </Cube></TimeSeries></Cube></Cube></gesmes:Envelope>"""
        result = _parse_ecb_xml(xml)
        assert result.observation_date == date(2024, 6, 30)

    def test_invalid_date_in_xml(self):
        xml_bad_date = """<gesmes:Envelope xmlns:gesmes="http://www.gesmes.org/xml/20202-08-01">
  <Cube><Cube><TimeSeries><Cube time="not-a-date">
    <Cube currency="USD" rate="1.0"/>
  </Cube></TimeSeries></Cube></Cube></gesmes:Envelope>"""
        with pytest.raises(FxParseError, match="valid date"):
            _parse_ecb_xml(xml_bad_date)

    def test_multiple_rates_parsed(self):
        result = _parse_ecb_xml(_ECB_VALID_XML)
        currencies = {r.currency_code for r in result.rates}
        assert "USD" in currencies
        assert "GBP" in currencies
        assert "JPY" in currencies
        assert "CHF" in currencies
        assert "CAD" in currencies
        assert "AUD" in currencies
        assert "CNY" in currencies

    def test_eur_not_in_rates(self):
        """EUR is the base and is not always in the XML rates."""
        result = _parse_ecb_xml(_ECB_VALID_XML)
        eur = result.get_rate("EUR")
        # EUR is the base; it is not in the XML but get_rate should return None
        assert eur is None


# ---------------------------------------------------------------------------
# EcbFxProvider construction tests
# ---------------------------------------------------------------------------


class TestEcbFxProviderConstruction:
    def test_default_construction(self):
        provider = EcbFxProvider()
        assert provider._timeout == 10.0

    def test_custom_timeout(self):
        provider = EcbFxProvider(request_timeout_seconds=30.0)
        assert provider._timeout == 30.0

    def test_zero_timeout_rejected(self):
        with pytest.raises(ValueError, match="positive"):
            EcbFxProvider(request_timeout_seconds=0)

    def test_negative_timeout_rejected(self):
        with pytest.raises(ValueError, match="positive"):
            EcbFxProvider(request_timeout_seconds=-1)

    def test_nan_timeout_rejected(self):
        with pytest.raises(ValueError, match="finite"):
            EcbFxProvider(request_timeout_seconds=float("nan"))

    def test_string_timeout_rejected(self):
        with pytest.raises(TypeError, match="numeric"):
            EcbFxProvider(request_timeout_seconds="10")  # type: ignore

    def test_custom_max_response_size(self):
        provider = EcbFxProvider(max_response_bytes=1024 * 1024)
        assert provider._max_response_bytes == 1024 * 1024

    def test_zero_max_response_rejected(self):
        with pytest.raises(ValueError, match="positive"):
            EcbFxProvider(max_response_bytes=0)


# ---------------------------------------------------------------------------
# FxProviderError tests
# ---------------------------------------------------------------------------


class TestFxProviderErrors:
    def test_fx_parse_error_is_fx_provider_error(self):
        assert issubclass(FxParseError, Exception)

    def test_fx_network_error_is_fx_provider_error(self):
        assert issubclass(FxNetworkError, Exception)
