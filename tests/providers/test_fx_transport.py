"""Tests for EcbFxProvider.fetch_rates() transport layer (PRODUCT-INTEL.4D-C-A / FU1).

Tests cover:
* Successful fetch -> real XML parse -> FxObservationSet
* Explicit timeout is passed
* Response read is bounded to max_response_bytes + 1
* Oversized response -> bounded failure
* HTTPError -> FxNetworkError
* URLError / timeout -> FxNetworkError
* requested-currency filtering
* Required USD rate can be retained for non-USD conversion
* No real network call
* Arbitrary programming exception is NOT silently converted into
  a supplemental network failure
"""

from __future__ import annotations

from datetime import date, datetime, timezone
from decimal import Decimal
from unittest.mock import MagicMock, patch

import pytest

from product_intelligence.providers.fx import (
    EcbFxProvider,
    FxNetworkError,
    FxObservationSet,
    FxParseError,
    FxRateObservation,
)

# ---------------------------------------------------------------------------
# ECB XML fixture
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
          <Cube currency="EUR" rate="1.0"/>
        </Cube>
      </TimeSeries>
    </Cube>
  </Cube>
</gesmes:Envelope>
"""


class _FakeResponse:
    """Fake HTTP response for urllib.request.urlopen mock."""

    def __init__(self, body: bytes, status: int = 200) -> None:
        self._body = body
        self._status = status
        self._read_size = 0

    def read(self, size: int = -1) -> bytes:
        """Read up to size bytes."""
        if size < 0:
            return self._body
        chunk = self._body[:size]
        self._read_size = size
        return chunk

    @property
    def read_limit_used(self) -> int:
        return self._read_size

    def __enter__(self) -> "_FakeResponse":
        return self

    def __exit__(self, *args: object) -> None:
        pass

    def getcode(self) -> int:
        return self._status


# ---------------------------------------------------------------------------
# Successful fetch tests
# ---------------------------------------------------------------------------


class TestEcbFxProviderSuccessfulFetch:
    """Test successful fetch -> real XML parse -> FxObservationSet."""

    def test_successful_fetch_returns_observation_set(self) -> None:
        """A valid ECB response returns a proper FxObservationSet."""
        provider = EcbFxProvider()
        body = _ECB_VALID_XML.encode("utf-8")

        with patch("urllib.request.urlopen") as mock_urlopen:
            mock_urlopen.return_value = _FakeResponse(body)
            result = provider.fetch_rates()

        assert isinstance(result, FxObservationSet)
        assert result.provider_id == "ECB"
        assert result.observation_date == date(2024, 1, 15)
        assert result.base_currency == "EUR"
        assert len(result.rates) == 3
        assert result.retrieved_at is not None
        assert result.retrieved_at.tzinfo is not None

    def test_successful_fetch_uses_timeout(self) -> None:
        """Explicit timeout is passed to urlopen."""
        provider = EcbFxProvider(request_timeout_seconds=15.0)
        body = _ECB_VALID_XML.encode("utf-8")

        with patch("urllib.request.urlopen") as mock_urlopen:
            mock_urlopen.return_value = _FakeResponse(body)
            provider.fetch_rates()

        mock_urlopen.assert_called_once()
        call_kwargs = mock_urlopen.call_args
        assert call_kwargs[1]["timeout"] == 15.0

    def test_successful_fetch_response_bounded(self) -> None:
        """Response read is bounded to max_response_bytes + 1."""
        provider = EcbFxProvider(max_response_bytes=1024)
        body = _ECB_VALID_XML.encode("utf-8")

        with patch("urllib.request.urlopen") as mock_urlopen:
            fake_resp = _FakeResponse(body)
            mock_urlopen.return_value = fake_resp
            provider.fetch_rates()

        # Read should use max_response_bytes + 1 as the limit
        assert fake_resp.read_limit_used == 1025

    def test_usd_rate_present_for_conversion(self) -> None:
        """USD rate is present in the full response for ECB formula."""
        provider = EcbFxProvider()
        body = _ECB_VALID_XML.encode("utf-8")

        with patch("urllib.request.urlopen") as mock_urlopen:
            mock_urlopen.return_value = _FakeResponse(body)
            result = provider.fetch_rates()

        usd_rate = result.get_rate("USD")
        assert usd_rate is not None
        assert usd_rate.rate == Decimal("1.0934")

    def test_all_rates_are_decimal(self) -> None:
        """All rate values are Decimal, not float."""
        provider = EcbFxProvider()
        body = _ECB_VALID_XML.encode("utf-8")

        with patch("urllib.request.urlopen") as mock_urlopen:
            mock_urlopen.return_value = _FakeResponse(body)
            result = provider.fetch_rates()

        for rate in result.rates:
            assert type(rate.rate) is Decimal

    def test_no_real_network_call(self) -> None:
        """Prove no real network call is made (urllib patched)."""
        provider = EcbFxProvider()
        body = _ECB_VALID_XML.encode("utf-8")

        with patch("urllib.request.urlopen") as mock_urlopen:
            mock_urlopen.return_value = _FakeResponse(body)
            provider.fetch_rates()

        mock_urlopen.assert_called_once()


# ---------------------------------------------------------------------------
# Requested currency filtering tests
# ---------------------------------------------------------------------------


class TestEcbFxProviderRequestedCurrencies:
    """Test requested-currency filtering."""

    def test_filters_to_requested_currencies(self) -> None:
        """Only requested currencies are returned."""
        provider = EcbFxProvider()
        body = _ECB_VALID_XML.encode("utf-8")

        with patch("urllib.request.urlopen") as mock_urlopen:
            mock_urlopen.return_value = _FakeResponse(body)
            result = provider.fetch_rates(
                requested_currencies=frozenset({"USD", "GBP"}),
            )

        currencies = {r.currency_code for r in result.rates}
        assert currencies == {"USD", "GBP"}
        assert len(result.rates) == 2

    def test_requested_usd_retained_for_conversion(self) -> None:
        """USD rate is retained when explicitly requested for conversion."""
        provider = EcbFxProvider()
        body = _ECB_VALID_XML.encode("utf-8")

        with patch("urllib.request.urlopen") as mock_urlopen:
            mock_urlopen.return_value = _FakeResponse(body)
            result = provider.fetch_rates(
                requested_currencies=frozenset({"GBP", "USD"}),
            )

        usd = result.get_rate("USD")
        assert usd is not None
        gbp = result.get_rate("GBP")
        assert gbp is not None

    def test_unrequested_currency_excluded(self) -> None:
        """Currency not in requested set is excluded."""
        provider = EcbFxProvider()
        body = _ECB_VALID_XML.encode("utf-8")

        with patch("urllib.request.urlopen") as mock_urlopen:
            mock_urlopen.return_value = _FakeResponse(body)
            result = provider.fetch_rates(
                requested_currencies=frozenset({"USD"}),
            )

        assert len(result.rates) == 1
        assert result.rates[0].currency_code == "USD"

    def test_case_insensitive_currency_filtering(self) -> None:
        """Currency filtering is case-insensitive."""
        provider = EcbFxProvider()
        body = _ECB_VALID_XML.encode("utf-8")

        with patch("urllib.request.urlopen") as mock_urlopen:
            mock_urlopen.return_value = _FakeResponse(body)
            result = provider.fetch_rates(
                requested_currencies=frozenset({"usd", "gbp"}),
            )

        currencies = {r.currency_code for r in result.rates}
        assert currencies == {"USD", "GBP"}


# ---------------------------------------------------------------------------
# Failure tests — bounded transport exceptions
# ---------------------------------------------------------------------------


class TestEcbFxProviderNetworkFailures:
    """Test that bounded transport failures become FxNetworkError."""

    def test_http_error_becomes_fx_network_error(self) -> None:
        """HTTPError from urllib -> FxNetworkError."""
        import urllib.error

        provider = EcbFxProvider()
        err = urllib.error.HTTPError(
            url="https://example.com",
            code=503,
            msg="Service Unavailable",
            hdrs={},
            fp=None,
        )

        with patch("urllib.request.urlopen", side_effect=err):
            with pytest.raises(FxNetworkError, match="HTTP error"):
                provider.fetch_rates()

    def test_url_error_becomes_fx_network_error(self) -> None:
        """URLError from urllib -> FxNetworkError."""
        import urllib.error

        provider = EcbFxProvider()
        err = urllib.error.URLError("DNS resolution failed")

        with patch("urllib.request.urlopen", side_effect=err):
            with pytest.raises(FxNetworkError, match="network error"):
                provider.fetch_rates()

    def test_timeout_error_becomes_fx_network_error(self) -> None:
        """TimeoutError -> FxNetworkError."""
        provider = EcbFxProvider(request_timeout_seconds=5.0)

        with patch("urllib.request.urlopen", side_effect=TimeoutError("timed out")):
            with pytest.raises(FxNetworkError, match="timed out"):
                provider.fetch_rates()

    def test_url_error_with_timeout_reason(self) -> None:
        """URLError with timeout reason -> FxNetworkError."""
        import urllib.error
        import socket

        provider = EcbFxProvider()
        err = urllib.error.URLError(socket.timeout("timed out"))

        with patch("urllib.request.urlopen", side_effect=err):
            with pytest.raises(FxNetworkError, match="network error"):
                provider.fetch_rates()


# ---------------------------------------------------------------------------
# Oversized response test
# ---------------------------------------------------------------------------


class TestEcbFxProviderOversizedResponse:
    """Test bounded response size handling."""

    def test_oversized_response_fails(self) -> None:
        """Response exceeding max_response_bytes raises FxParseError."""
        provider = EcbFxProvider(max_response_bytes=100)
        # Body is larger than 100 bytes
        body = _ECB_VALID_XML.encode("utf-8")  # ~550 bytes

        with patch("urllib.request.urlopen") as mock_urlopen:
            mock_urlopen.return_value = _FakeResponse(body)
            with pytest.raises(FxParseError, match="exceeds maximum size"):
                provider.fetch_rates()

    def test_exact_size_response_succeeds(self) -> None:
        """Response exactly at max_response_bytes succeeds."""
        body = _ECB_VALID_XML.encode("utf-8")
        provider = EcbFxProvider(max_response_bytes=len(body))

        with patch("urllib.request.urlopen") as mock_urlopen:
            mock_urlopen.return_value = _FakeResponse(body)
            result = provider.fetch_rates()

        assert isinstance(result, FxObservationSet)


# ---------------------------------------------------------------------------
# Programming defect isolation tests
# ---------------------------------------------------------------------------


class TestEcbFxProviderProgrammingDefects:
    """Prove programming defects are NOT silently converted to FxNetworkError."""

    def test_type_error_propagates(self) -> None:
        """A TypeError from the transport is NOT caught as FxNetworkError."""
        provider = EcbFxProvider()

        with patch("urllib.request.urlopen", side_effect=TypeError("bad type")):
            with pytest.raises(TypeError, match="bad type"):
                provider.fetch_rates()

    def test_value_error_propagates(self) -> None:
        """A ValueError from the transport is NOT caught as FxNetworkError."""
        provider = EcbFxProvider()

        with patch("urllib.request.urlopen", side_effect=ValueError("bad value")):
            with pytest.raises(ValueError, match="bad value"):
                provider.fetch_rates()

    def test_assertion_error_propagates(self) -> None:
        """An AssertionError is NOT caught as FxNetworkError."""
        provider = EcbFxProvider()

        with patch("urllib.request.urlopen", side_effect=AssertionError("invariant")):
            with pytest.raises(AssertionError, match="invariant"):
                provider.fetch_rates()

    def test_key_error_propagates(self) -> None:
        """A KeyError from the transport is NOT caught as FxNetworkError."""
        provider = EcbFxProvider()

        with patch("urllib.request.urlopen", side_effect=KeyError("missing_key")):
            with pytest.raises(KeyError, match="missing_key"):
                provider.fetch_rates()

    def test_runtime_error_propagates(self) -> None:
        """A RuntimeError is NOT caught as FxNetworkError."""
        provider = EcbFxProvider()

        with patch("urllib.request.urlopen", side_effect=RuntimeError("unexpected")):
            with pytest.raises(RuntimeError, match="unexpected"):
                provider.fetch_rates()

    def test_fx_parse_error_from_malformed_xml_propagates(self) -> None:
        """FxParseError from XML parsing is NOT an FxNetworkError."""
        provider = EcbFxProvider()
        bad_body = b"this is not xml at all"

        with patch("urllib.request.urlopen") as mock_urlopen:
            mock_urlopen.return_value = _FakeResponse(bad_body)
            with pytest.raises(FxParseError, match="not valid XML"):
                provider.fetch_rates()

    def test_unicode_decode_error_is_parse_error(self) -> None:
        """Invalid UTF-8 response raises FxParseError, not FxNetworkError."""
        provider = EcbFxProvider()
        bad_body = b"\x80\x81\x82\x83"

        with patch("urllib.request.urlopen") as mock_urlopen:
            mock_urlopen.return_value = _FakeResponse(bad_body)
            with pytest.raises(FxParseError, match="not valid UTF-8"):
                provider.fetch_rates()

    def test_bounded_taxonomy_only(self) -> None:
        """Only HTTPError, URLError, TimeoutError become FxNetworkError.

        This test proves the bounded transport exception taxonomy:
        exactly these three types are classified as network failure.
        """
        import urllib.error

        # These SHOULD become FxNetworkError
        for exc_class, exc_factory in [
            (urllib.error.HTTPError, lambda: urllib.error.HTTPError(
                url="x", code=500, msg="err", hdrs={}, fp=None,
            )),
            (urllib.error.URLError, lambda: urllib.error.URLError("fail")),
            (TimeoutError, lambda: TimeoutError()),
        ]:
            provider = EcbFxProvider()
            with patch("urllib.request.urlopen", side_effect=exc_factory()):
                with pytest.raises(FxNetworkError):
                    provider.fetch_rates()

        # These must NOT become FxNetworkError
        for exc_class in [TypeError, ValueError, AssertionError, KeyError, RuntimeError]:
            provider = EcbFxProvider()
            with patch("urllib.request.urlopen", side_effect=exc_class("defect")):
                with pytest.raises(exc_class):
                    provider.fetch_rates()
