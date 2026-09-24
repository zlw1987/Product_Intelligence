"""Focused currency-formatting tests for the Compact Quote price formatter
(PRODUCT-INTEL.PILOT-RELEASE-2-PROD-FIX1, defect 2).

Production rendered ``ZAR30,999.0 ZAR`` — the formatter used the currency
CODE as the fallback prefix and then appended the code again. Corrected
behavior:

* Known symbol currencies keep the current form:
    $1,515.72 USD
    €962.86 EUR
* Currencies without a configured symbol render the code ONLY ONCE as a
  leading prefix:
    ZAR 30,999.0
  and NEVER ``ZAR30,999.0 ZAR``.

Decimal values and FX math are not altered — display formatting only.
"""

from __future__ import annotations

from decimal import Decimal

from product_intelligence.research.compact_quote import _format_price


class TestKnownSymbolCurrencies:
    def test_usd(self) -> None:
        assert _format_price(Decimal("1515.72"), "USD") == "$1,515.72 USD"

    def test_eur(self) -> None:
        assert _format_price(Decimal("962.86"), "EUR") == "€962.86 EUR"

    def test_gbp(self) -> None:
        assert _format_price(Decimal("1500.00"), "GBP") == "£1,500.00 GBP"

    def test_jpy(self) -> None:
        assert _format_price(Decimal("150000"), "JPY") == "¥150,000 JPY"

    def test_cad(self) -> None:
        assert _format_price(Decimal("10.50"), "CAD") == "C$10.50 CAD"

    def test_aud(self) -> None:
        assert _format_price(Decimal("10.50"), "AUD") == "A$10.50 AUD"

    def test_cny(self) -> None:
        assert _format_price(Decimal("100"), "CNY") == "¥100 CNY"

    def test_usd_thousands_grouping(self) -> None:
        assert _format_price(Decimal("15000"), "USD") == "$15,000 USD"

    def test_usd_small(self) -> None:
        assert _format_price(Decimal("9.99"), "USD") == "$9.99 USD"


class TestNoSymbolCurrencies:
    def test_zar_renders_code_once(self) -> None:
        """The exact production defect: ZAR30,999.0 ZAR is forbidden."""
        result = _format_price(Decimal("30999.0"), "ZAR")
        assert result == "ZAR 30,999.0"
        assert result != "ZAR30,999.0 ZAR"
        # The code appears exactly once
        assert result.count("ZAR") == 1

    def test_chf_renders_code_once(self) -> None:
        """CHF has no display symbol (its code was not a symbol): once only."""
        result = _format_price(Decimal("1705.35"), "CHF")
        assert result == "CHF 1,705.35"
        assert result.count("CHF") == 1

    def test_zar_decimal_value_unchanged(self) -> None:
        """Formatting must not alter the Decimal value or its precision."""
        amount = Decimal("30999.0")
        _format_price(amount, "ZAR")
        assert amount == Decimal("30999.0")
        assert str(amount) == "30999.0"

    def test_zar_whole_number(self) -> None:
        assert _format_price(Decimal("1234567"), "ZAR") == "ZAR 1,234,567"

    def test_zar_small(self) -> None:
        assert _format_price(Decimal("12.34"), "ZAR") == "ZAR 12.34"

    def test_sek_no_symbol(self) -> None:
        assert _format_price(Decimal("150.00"), "SEK") == "SEK 150.00"

    def test_lowercase_code_symbol_lookup_is_case_insensitive(self) -> None:
        # The symbol lookup is case-insensitive; the display code is kept
        # exactly as supplied by the caller (rows always pass the uppercased
        # code) — pre-existing behavior preserved.
        assert _format_price(Decimal("1.00"), "usd") == "$1.00 usd"
        assert _format_price(Decimal("1.00"), "zar") == "zar 1.00"
