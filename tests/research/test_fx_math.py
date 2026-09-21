"""Tests for FX mathematics (PRODUCT-INTEL.4D-C-A).

Tests cover:
* USD passthrough exact
* EUR -> USD conversion
* Another ECB currency -> USD conversion
* Missing rate -> unavailable
* Decimal precision preserved
* No float intermediate
* UsdEquivalentResult validation
* ECB formula: USD = amount_C / rate_C * rate_USD
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal

import pytest

from product_intelligence.research.fx_codec import (
    FxObservationSnapshot,
    FxRateEntry,
)
from product_intelligence.research.fx_math import (
    UsdEquivalentResult,
    compute_usd_equivalent,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_fx_snapshot(
    rates: list[tuple[str, Decimal]] | None = None,
) -> FxObservationSnapshot:
    """Build a test FX observation snapshot."""
    if rates is None:
        rates = [
            ("USD", Decimal("1.0934")),
            ("GBP", Decimal("0.8567")),
            ("JPY", Decimal("159.33")),
            ("CHF", Decimal("0.9312")),
            ("SEK", Decimal("11.2345")),
        ]
    return FxObservationSnapshot(
        provider_id="ECB",
        observation_date="2024-01-15",
        base_currency="EUR",
        rates=tuple(
            FxRateEntry(currency_code=code, rate=rate)
            for code, rate in rates
        ),
        retrieved_at="2024-01-15T12:00:00+00:00",
    )


# ---------------------------------------------------------------------------
# UsdEquivalentResult tests
# ---------------------------------------------------------------------------


class TestUsdEquivalentResult:
    def test_conversion_available(self):
        result = UsdEquivalentResult(
            original_amount=Decimal("1000"),
            original_currency="USD",
            usd_equivalent=Decimal("1000"),
            conversion_available=True,
        )
        assert result.conversion_available is True
        assert result.usd_equivalent == Decimal("1000")
        assert result.reason is None

    def test_conversion_unavailable(self):
        result = UsdEquivalentResult(
            original_amount=Decimal("1000"),
            original_currency="XYZ",
            usd_equivalent=None,
            conversion_available=False,
            reason="rate for XYZ not available",
        )
        assert result.conversion_available is False
        assert result.usd_equivalent is None
        assert result.reason is not None

    def test_consistency_check_available_requires_usd(self):
        with pytest.raises(ValueError, match="requires a non-None usd_equivalent"):
            UsdEquivalentResult(
                original_amount=Decimal("1000"),
                original_currency="USD",
                usd_equivalent=None,
                conversion_available=True,
            )

    def test_consistency_check_available_requires_no_reason(self):
        with pytest.raises(ValueError, match="requires reason=None"):
            UsdEquivalentResult(
                original_amount=Decimal("1000"),
                original_currency="USD",
                usd_equivalent=Decimal("1000"),
                conversion_available=True,
                reason="some reason",
            )

    def test_consistency_check_unavailable_requires_no_usd(self):
        with pytest.raises(ValueError, match="requires usd_equivalent=None"):
            UsdEquivalentResult(
                original_amount=Decimal("1000"),
                original_currency="USD",
                usd_equivalent=Decimal("1000"),
                conversion_available=False,
                reason="some reason",
            )

    def test_non_decimal_amount_rejected(self):
        with pytest.raises(TypeError, match="must be a Decimal"):
            UsdEquivalentResult(
                original_amount=1000,  # type: ignore
                original_currency="USD",
                usd_equivalent=Decimal("1000"),
                conversion_available=True,
            )

    def test_float_usd_equivalent_rejected(self):
        with pytest.raises(TypeError, match="usd_equivalent must be a Decimal"):
            UsdEquivalentResult(
                original_amount=Decimal("1000"),
                original_currency="USD",
                usd_equivalent=1000.0,  # type: ignore
                conversion_available=True,
            )


# ---------------------------------------------------------------------------
# USD passthrough tests
# ---------------------------------------------------------------------------


class TestUsdPassthrough:
    def test_usd_passthrough_with_fx(self):
        """USD source prices pass through exactly."""
        fx = _make_fx_snapshot()
        result = compute_usd_equivalent(
            amount=Decimal("2023.27"),
            currency="USD",
            fx_snapshot=fx,
        )
        assert result.conversion_available is True
        assert result.usd_equivalent == Decimal("2023.27")
        assert result.original_amount == Decimal("2023.27")
        assert result.original_currency == "USD"

    def test_usd_passthrough_no_fx(self):
        """USD passthrough works even without FX evidence."""
        result = compute_usd_equivalent(
            amount=Decimal("500.00"),
            currency="USD",
            fx_snapshot=None,
        )
        assert result.conversion_available is True
        assert result.usd_equivalent == Decimal("500.00")

    def test_usd_passthrough_exact_decimal(self):
        """No precision loss in USD passthrough."""
        fx = _make_fx_snapshot()
        amount = Decimal("2023.27000")
        result = compute_usd_equivalent(
            amount=amount,
            currency="USD",
            fx_snapshot=fx,
        )
        assert result.usd_equivalent == amount


# ---------------------------------------------------------------------------
# EUR -> USD conversion tests
# ---------------------------------------------------------------------------


class TestEurToUsd:
    def test_eur_to_usd_basic(self):
        """EUR converts to USD via rate_USD."""
        fx = _make_fx_snapshot(rates=[
            ("USD", Decimal("1.0934")),
        ])
        result = compute_usd_equivalent(
            amount=Decimal("1705.35"),
            currency="EUR",
            fx_snapshot=fx,
        )
        assert result.conversion_available is True
        # EUR is base: USD = amount * rate_USD
        expected = Decimal("1705.35") * Decimal("1.0934")
        assert result.usd_equivalent == expected

    def test_eur_to_usd_result_is_decimal(self):
        fx = _make_fx_snapshot(rates=[
            ("USD", Decimal("1.0934")),
        ])
        result = compute_usd_equivalent(
            amount=Decimal("1000"),
            currency="EUR",
            fx_snapshot=fx,
        )
        assert isinstance(result.usd_equivalent, Decimal)
        assert type(result.usd_equivalent) is Decimal

    def test_eur_no_usd_rate(self):
        """EUR without USD rate -> unavailable."""
        fx = _make_fx_snapshot(rates=[
            ("GBP", Decimal("0.8567")),
        ])
        result = compute_usd_equivalent(
            amount=Decimal("1000"),
            currency="EUR",
            fx_snapshot=fx,
        )
        assert result.conversion_available is False
        assert result.usd_equivalent is None
        assert "USD rate not available" in result.reason


# ---------------------------------------------------------------------------
# Other currency -> USD conversion tests
# ---------------------------------------------------------------------------


class TestOtherCurrencyToUsd:
    def test_gbp_to_usd(self):
        """GBP converts to USD via ECB formula."""
        fx = _make_fx_snapshot()
        result = compute_usd_equivalent(
            amount=Decimal("1000"),
            currency="GBP",
            fx_snapshot=fx,
        )
        assert result.conversion_available is True
        # ECB formula: USD = amount / rate_GBP * rate_USD
        expected = (Decimal("1000") / Decimal("0.8567")) * Decimal("1.0934")
        assert result.usd_equivalent == expected

    def test_jpy_to_usd(self):
        fx = _make_fx_snapshot()
        result = compute_usd_equivalent(
            amount=Decimal("150000"),
            currency="JPY",
            fx_snapshot=fx,
        )
        assert result.conversion_available is True
        expected = (Decimal("150000") / Decimal("159.33")) * Decimal("1.0934")
        assert result.usd_equivalent == expected

    def test_sek_to_usd(self):
        fx = _make_fx_snapshot()
        result = compute_usd_equivalent(
            amount=Decimal("11234.50"),
            currency="SEK",
            fx_snapshot=fx,
        )
        assert result.conversion_available is True
        expected = (Decimal("11234.50") / Decimal("11.2345")) * Decimal("1.0934")
        assert result.usd_equivalent == expected

    def test_chf_to_usd(self):
        fx = _make_fx_snapshot()
        result = compute_usd_equivalent(
            amount=Decimal("1000"),
            currency="CHF",
            fx_snapshot=fx,
        )
        assert result.conversion_available is True
        expected = (Decimal("1000") / Decimal("0.9312")) * Decimal("1.0934")
        assert result.usd_equivalent == expected


# ---------------------------------------------------------------------------
# Missing rate tests
# ---------------------------------------------------------------------------


class TestMissingRate:
    def test_unknown_currency_no_fx(self):
        result = compute_usd_equivalent(
            amount=Decimal("1000"),
            currency="XYZ",
            fx_snapshot=None,
        )
        assert result.conversion_available is False
        assert result.usd_equivalent is None
        assert "no FX evidence" in result.reason

    def test_unknown_currency_with_fx(self):
        fx = _make_fx_snapshot()
        result = compute_usd_equivalent(
            amount=Decimal("1000"),
            currency="BRL",
            fx_snapshot=fx,
        )
        assert result.conversion_available is False
        assert result.usd_equivalent is None
        assert "BRL" in result.reason

    def test_fx_without_usd_rate(self):
        fx = _make_fx_snapshot(rates=[
            ("GBP", Decimal("0.8567")),
        ])
        result = compute_usd_equivalent(
            amount=Decimal("1000"),
            currency="GBP",
            fx_snapshot=fx,
        )
        assert result.conversion_available is False
        assert "USD rate not available" in result.reason


# ---------------------------------------------------------------------------
# Decimal precision tests
# ---------------------------------------------------------------------------


class TestDecimalPrecision:
    def test_no_float_in_result(self):
        """Result usd_equivalent is always Decimal, never float."""
        fx = _make_fx_snapshot()
        result = compute_usd_equivalent(
            amount=Decimal("1705.35"),
            currency="GBP",
            fx_snapshot=fx,
        )
        assert result.conversion_available is True
        assert result.usd_equivalent is not None
        assert type(result.usd_equivalent) is Decimal

    def test_precision_preserved(self):
        """High-precision values maintain Decimal exactness."""
        fx = _make_fx_snapshot()
        amount = Decimal("1000.000000000000000001")
        result = compute_usd_equivalent(
            amount=amount,
            currency="USD",
            fx_snapshot=fx,
        )
        assert result.usd_equivalent == amount

    def test_conversion_maintains_decimal(self):
        """GBR -> USD conversion produces exact Decimal, not approximate float."""
        fx = _make_fx_snapshot()
        result = compute_usd_equivalent(
            amount=Decimal("1"),
            currency="GBP",
            fx_snapshot=fx,
        )
        # The result should be exact: 1 / 0.8567 * 1.0934
        # NOT a float approximation
        assert result.usd_equivalent is not None
        assert type(result.usd_equivalent) is Decimal


# ---------------------------------------------------------------------------
# Input validation tests
# ---------------------------------------------------------------------------


class TestInputValidation:
    def test_non_decimal_amount_rejected(self):
        with pytest.raises(TypeError, match="amount must be a Decimal"):
            compute_usd_equivalent(
                amount=1000.0,  # type: ignore
                currency="USD",
                fx_snapshot=None,
            )

    def test_float_amount_rejected(self):
        with pytest.raises(TypeError, match="amount must be a Decimal"):
            compute_usd_equivalent(
                amount=float("1000"),  # type: ignore
                currency="USD",
                fx_snapshot=None,
            )

    def test_nan_amount_rejected(self):
        with pytest.raises(ValueError, match="finite"):
            compute_usd_equivalent(
                amount=Decimal("NaN"),
                currency="USD",
                fx_snapshot=None,
            )

    def test_infinity_amount_rejected(self):
        with pytest.raises(ValueError, match="finite"):
            compute_usd_equivalent(
                amount=Decimal("Infinity"),
                currency="USD",
                fx_snapshot=None,
            )


# ---------------------------------------------------------------------------
# Case sensitivity tests
# ---------------------------------------------------------------------------


class TestCaseSensitivity:
    def test_lowercase_currency(self):
        fx = _make_fx_snapshot()
        result = compute_usd_equivalent(
            amount=Decimal("1000"),
            currency="usd",
            fx_snapshot=fx,
        )
        assert result.conversion_available is True
        assert result.original_currency == "USD"

    def test_mixed_case_currency(self):
        fx = _make_fx_snapshot()
        result = compute_usd_equivalent(
            amount=Decimal("1000"),
            currency="GbP",
            fx_snapshot=fx,
        )
        assert result.conversion_available is True
        assert result.original_currency == "GBP"
