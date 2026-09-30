"""Pure FX observation-cache contract tests (PRODUCT-INTEL.8A-FX-A1).

Covers the stdlib-only research contract
``product_intelligence/research/fx_cache_contract.py``:

* canonical content digest: determinism, order-independence, Decimal
  exactness, correction sensitivity, identity inclusion, fail-closed
  input validation;
* projection: document-order preservation, equivalence with the ECB
  adapter's own post-parse filter (mirror-lock), fail-closed inputs;
* freshness predicate: the Europe/Brussels (CET/CEST) weekend-stretch
  closure policy over ACTUAL proof/use instants — working-day
  conservatism, weekend boundaries, DST transitions, UTC-vs-Brussels
  date divergence, and fail-closed contract violations.

No Django, no database, no network. Every test is deterministic by
construction (pinned instants / fixed offsets) and runs on any weekday.
"""

from __future__ import annotations

import ast
import sys
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from pathlib import Path
from unittest.mock import MagicMock, patch
from zoneinfo import ZoneInfo

import pytest

from product_intelligence.providers.fx import (
    EcbFxProvider,
    FxObservationSet,
    FxRateObservation,
)
from product_intelligence.research.fx_cache_contract import (
    fx_document_content_sha256,
    no_publication_possible_between,
    project_required_rates,
)

BRUSSELS = ZoneInfo("Europe/Brussels")
CET = timezone(timedelta(hours=1))
CEST = timezone(timedelta(hours=2))
UTC = timezone.utc

# Pinned instants (2026): Fri 2026-01-09, Sat 2026-01-10,
# Sun 2026-01-11, Mon 2026-01-12.
FRI = date(2026, 1, 9)
SAT = date(2026, 1, 10)
SUN = date(2026, 1, 11)
MON = date(2026, 1, 12)


def _dt(d: date, hour: int, minute: int = 0, second: int = 0,
        micro: int = 0, tzinfo=CET) -> datetime:
    return datetime(d.year, d.month, d.day, hour, minute, second, micro,
                    tzinfo=tzinfo)


# ===========================================================================
# Canonical content digest
# ===========================================================================


class TestContentDigest:
    """Deterministic canonical digest of the FULL parsed rate set."""

    RATES = (
        ("USD", Decimal("1.0934")),
        ("GBP", Decimal("0.8567")),
        ("ZAR", Decimal("18.6836")),
    )

    def test_deterministic(self) -> None:
        a = fx_document_content_sha256(
            provider_id="ECB", base_currency="EUR",
            observation_date=date(2026, 1, 9), rates=self.RATES,
        )
        b = fx_document_content_sha256(
            provider_id="ECB", base_currency="EUR",
            observation_date=date(2026, 1, 9), rates=self.RATES,
        )
        assert a == b
        assert len(a) == 64  # SHA-256 hex

    def test_rate_ordering_does_not_affect_digest(self) -> None:
        base = fx_document_content_sha256(
            provider_id="ECB", base_currency="EUR",
            observation_date=FRI, rates=self.RATES,
        )
        shuffled = fx_document_content_sha256(
            provider_id="ECB", base_currency="EUR",
            observation_date=FRI,
            rates=list(reversed(self.RATES)),
        )
        assert base == shuffled

    def test_decimal_remains_exact_no_float_conversion(self) -> None:
        # The exact textual representation is part of the content:
        # "1.0934" and "1.09340" are distinct canonical representations.
        a = fx_document_content_sha256(
            provider_id="ECB", base_currency="EUR",
            observation_date=FRI, rates=[("USD", Decimal("1.0934"))],
        )
        b = fx_document_content_sha256(
            provider_id="ECB", base_currency="EUR",
            observation_date=FRI, rates=[("USD", Decimal("1.09340"))],
        )
        assert a != b
        # And a float input is a contract violation (never coerced).
        with pytest.raises(TypeError):
            fx_document_content_sha256(
                provider_id="ECB", base_currency="EUR",
                observation_date=FRI, rates=[("USD", 1.0934)],
            )

    def test_same_date_corrected_rates_different_digest(self) -> None:
        a = fx_document_content_sha256(
            provider_id="ECB", base_currency="EUR",
            observation_date=FRI, rates=self.RATES,
        )
        corrected = [
            pair if pair[0] != "USD" else ("USD", Decimal("1.0950"))
            for pair in self.RATES
        ]
        b = fx_document_content_sha256(
            provider_id="ECB", base_currency="EUR",
            observation_date=FRI, rates=corrected,
        )
        assert a != b

    def test_identity_dimensions_included(self) -> None:
        base = fx_document_content_sha256(
            provider_id="ECB", base_currency="EUR",
            observation_date=FRI, rates=self.RATES,
        )
        assert base != fx_document_content_sha256(
            provider_id="ECB", base_currency="EUR",
            observation_date=date(2026, 1, 12), rates=self.RATES,
        )
        assert base != fx_document_content_sha256(
            provider_id="OTHER", base_currency="EUR",
            observation_date=FRI, rates=self.RATES,
        )
        assert base != fx_document_content_sha256(
            provider_id="ECB", base_currency="USD",
            observation_date=FRI, rates=self.RATES,
        )

    def test_no_dict_order_dependence(self) -> None:
        # The same observation expressed with differently-ordered input
        # pairs (a stand-in for any dict-order variation) digests the same.
        a = fx_document_content_sha256(
            provider_id="ECB", base_currency="EUR",
            observation_date=FRI, rates=self.RATES,
        )
        b = fx_document_content_sha256(
            provider_id="ECB", base_currency="EUR",
            observation_date=FRI,
            rates=list(self.RATES)[::-1] + list(self.RATES)[:0],
        )
        assert a == b

    def test_malformed_inputs_fail_closed(self) -> None:
        with pytest.raises(ValueError):
            fx_document_content_sha256(
                provider_id="", base_currency="EUR",
                observation_date=FRI, rates=self.RATES,
            )
        with pytest.raises(ValueError):
            fx_document_content_sha256(
                provider_id="ECB", base_currency="EUR",
                observation_date=FRI, rates=[("US", Decimal("1"))],
            )
        with pytest.raises(ValueError):
            fx_document_content_sha256(
                provider_id="ECB", base_currency="EUR",
                observation_date=FRI,
                rates=[("USD", Decimal("NaN"))],
            )
        with pytest.raises(ValueError):
            fx_document_content_sha256(
                provider_id="ECB", base_currency="EUR",
                observation_date=FRI,
                rates=[("USD", Decimal("-1"))],
            )
        with pytest.raises(ValueError):
            fx_document_content_sha256(
                provider_id="ECB", base_currency="EUR",
                observation_date=FRI,
                rates=[("USD", Decimal("0"))],
            )
        with pytest.raises(TypeError):
            fx_document_content_sha256(
                provider_id="ECB", base_currency="EUR",
                observation_date=datetime(2026, 1, 9, tzinfo=UTC),
                rates=self.RATES,
            )
        with pytest.raises(TypeError):
            fx_document_content_sha256(
                provider_id="ECB", base_currency="EUR",
                observation_date=FRI, rates=[("USD", "1.0934")],
            )


# ===========================================================================
# Projection (full set -> required currencies)
# ===========================================================================


class TestProjection:
    """The shared LIVE/CACHE_HIT projection contract."""

    FULL = (
        FxRateObservation(currency_code="USD", rate=Decimal("1.0934")),
        FxRateObservation(currency_code="GBP", rate=Decimal("0.8567")),
        FxRateObservation(currency_code="EUR", rate=Decimal("1.0")),
        FxRateObservation(currency_code="ZAR", rate=Decimal("18.6836")),
    )

    def test_document_order_preserved(self) -> None:
        projected = project_required_rates(
            self.FULL, frozenset({"GBP", "USD", "ZAR"}),
        )
        assert [r.currency_code for r in projected] == ["USD", "GBP", "ZAR"]

    def test_none_returns_full_set(self) -> None:
        assert project_required_rates(self.FULL, None) == self.FULL

    def test_case_insensitive_and_stripped(self) -> None:
        projected = project_required_rates(self.FULL, frozenset({" usd ", "zar"}))
        assert [r.currency_code for r in projected] == ["USD", "ZAR"]

    def test_empty_required_yields_empty(self) -> None:
        assert project_required_rates(self.FULL, frozenset()) == ()

    def test_missing_currency_projected_absent(self) -> None:
        projected = project_required_rates(self.FULL, frozenset({"USD", "AUD"}))
        assert [r.currency_code for r in projected] == ["USD"]

    def test_mirror_lock_equivalence_with_provider_filter(self) -> None:
        """The research projection MUST equal the ECB adapter's own
        post-parse filter for the same document (byte-identity basis)."""
        xml = """<?xml version="1.0" encoding="UTF-8"?>
<gesmes:Envelope xmlns:gesmes="http://www.gesmes.org/xml/2002-08-01"
                 xmlns="http://www.ecb.int/vocabulary/2002-08-01/eurofxref">
  <Cube><Cube><TimeSeries>
    <Cube time="2026-01-09">
      <Cube currency="USD" rate="1.0934"/>
      <Cube currency="JPY" rate="160.1234"/>
      <Cube currency="GBP" rate="0.8567"/>
      <Cube currency="EUR" rate="1.0"/>
      <Cube currency="ZAR" rate="18.6836"/>
    </Cube>
  </TimeSeries></Cube></Cube>
</gesmes:Envelope>
"""

        class _Resp:
            def __init__(self, body: bytes) -> None:
                self._body = body

            def read(self, size: int = -1) -> bytes:
                return self._body

            def __enter__(self):
                return self

            def __exit__(self, *args):
                return None

        provider = EcbFxProvider()
        with patch("urllib.request.urlopen") as mock_urlopen:
            mock_urlopen.return_value = _Resp(xml.encode("utf-8"))
            full = provider.fetch_rates(requested_currencies=None)
            filtered = provider.fetch_rates(
                requested_currencies=frozenset({"GBP", "USD"}),
            )
        assert [r.currency_code for r in filtered.rates] == [
            r.currency_code for r in
            project_required_rates(full.rates, frozenset({"GBP", "USD"}))
        ]
        # Exact value equality, same order, same single retrieved_at.
        assert all(
            a.currency_code == b.currency_code and a.rate == b.rate
            for a, b in zip(filtered.rates,
                            project_required_rates(full.rates,
                                                   frozenset({"GBP", "USD"})))
        )
        assert filtered.retrieved_at is not None

    def test_accepts_codec_entries_too(self) -> None:
        # Duck typing over .currency_code: codec FxRateEntry objects
        # (the CACHE_HIT path shape) are projected identically.
        from product_intelligence.research.fx_codec import FxRateEntry

        entries = (
            FxRateEntry(currency_code="USD", rate=Decimal("1.0934")),
            FxRateEntry(currency_code="GBP", rate=Decimal("0.8567")),
        )
        projected = project_required_rates(entries, frozenset({"USD"}))
        assert [e.currency_code for e in projected] == ["USD"]

    def test_malformed_inputs_fail_closed(self) -> None:
        with pytest.raises(TypeError):
            project_required_rates(self.FULL, "USD")  # single code string
        with pytest.raises(TypeError):
            project_required_rates(None, frozenset({"USD"}))

        class _Bad:
            currency_code = 123

        with pytest.raises(TypeError):
            project_required_rates((_Bad(),), frozenset({"USD"}))


# ===========================================================================
# Freshness predicate (pure temporal contract)
# ===========================================================================


class TestFreshnessPredicate:
    """no_publication_possible_between over ACTUAL instants (T, N)."""

    # --- weekend interior (reusable) ---

    def test_saturday_to_saturday(self) -> None:
        assert no_publication_possible_between(
            _dt(SAT, 9), _dt(SAT, 12), CET,
        ) is True

    def test_sunday_to_sunday(self) -> None:
        assert no_publication_possible_between(
            _dt(SUN, 23), _dt(SUN, 23, 59), CET,
        ) is True

    def test_saturday_to_sunday(self) -> None:
        assert no_publication_possible_between(
            _dt(SAT, 9), _dt(SUN, 18), CET,
        ) is True

    def test_proof_and_use_same_instant_weekend(self) -> None:
        t = _dt(SAT, 9)
        assert no_publication_possible_between(t, t, CET) is True

    def test_proof_exactly_at_weekend_start(self) -> None:
        # Saturday 00:00:00 exactly: T's zone day is Saturday -> the
        # closed interval [T, T] contains no working day.
        assert no_publication_possible_between(
            _dt(SAT, 0, 0, 0), _dt(SAT, 0, 0, 0), CET,
        ) is True

    def test_proof_immediately_before_weekend_never_reuses(self) -> None:
        # Friday 23:59 CET proof: T's zone day is Friday (C2) -> a
        # delayed Friday publication is not excludable.
        assert no_publication_possible_between(
            _dt(FRI, 23, 59), _dt(SAT, 0, 1), CET,
        ) is False

    # --- boundaries (not reusable) ---

    def test_friday_to_saturday_boundary(self) -> None:
        assert no_publication_possible_between(
            _dt(FRI, 16, 30), _dt(SAT, 9), CET,
        ) is False

    def test_sunday_to_monday_boundary(self) -> None:
        assert no_publication_possible_between(
            _dt(SUN, 23, 30), _dt(MON, 0, 30), CET,
        ) is False

    def test_current_instant_exactly_at_monday_start(self) -> None:
        # N exactly at Monday 00:00: N's zone day is Monday (C2).
        assert no_publication_possible_between(
            _dt(SAT, 9), _dt(MON, 0, 0, 0), CET,
        ) is False

    def test_one_second_before_monday_start(self) -> None:
        # One second before Monday 00:00 is still Sunday: reusable.
        assert no_publication_possible_between(
            _dt(SAT, 9), _dt(SUN, 23, 59, 59, 999999), CET,
        ) is True

    def test_working_day_proof_never_reuses_same_day(self) -> None:
        # Post-publication working-day proof (documents the v1
        # conservatism): Mon 17:00 -> Mon 23:00 is NOT reusable.
        assert no_publication_possible_between(
            _dt(MON, 17), _dt(MON, 23), CET,
        ) is False

    def test_working_week_gap_not_reusable(self) -> None:
        # Saturday -> next Saturday: Mon-Fri inside [T, N].
        next_sat = SAT + timedelta(days=7)
        assert no_publication_possible_between(
            _dt(SAT, 9), _dt(next_sat, 9), CET,
        ) is False

    def test_workday_between_two_weekends_not_reusable(self) -> None:
        # Sun 23:00 -> Tue 09:00: Monday inside the interval.
        tue = MON + timedelta(days=1)
        assert no_publication_possible_between(
            _dt(SUN, 23), _dt(tue, 9), CET,
        ) is False

    # --- timezone semantics (aware conversion, Brussels, DST) ---

    def test_utc_instants_converted_to_brussels_days(self) -> None:
        # The predicate consumes ACTUAL instants: the same weekend
        # expressed in UTC offsets (different wall clocks, same instants)
        # must evaluate identically to the CET expression.
        t_cet = _dt(SAT, 9, tzinfo=CET)
        n_cet = _dt(SUN, 18, tzinfo=CET)
        assert t_cet.hour != t_cet.astimezone(UTC).hour  # wall clocks differ
        assert t_cet == t_cet.astimezone(UTC)  # ...same instant
        assert no_publication_possible_between(
            t_cet.astimezone(UTC), n_cet.astimezone(UTC), CET,
        ) is True

    def test_aware_utc_conversion_brussels_zone(self) -> None:
        # 2026-01-10 08:30 UTC = 09:30 Saturday Brussels (CET, +1).
        t = datetime(2026, 1, 10, 8, 30, tzinfo=UTC)
        n = datetime(2026, 1, 11, 17, 0, tzinfo=UTC)  # 18:00 Sun Brussels
        assert no_publication_possible_between(t, n, BRUSSELS) is True

    def test_dst_spring_transition_brussels(self) -> None:
        # EU spring-forward 2026: Sunday 2026-03-29 01:00 UTC
        # (CET -> CEST). A Saturday->Sunday weekend stretch across the
        # transition is one weekend in Brussels time.
        t = datetime(2026, 3, 28, 9, 0, tzinfo=CET)   # Sat 09:00 +01
        n = datetime(2026, 3, 29, 23, 59, tzinfo=CEST)  # Sun 23:59 +02
        assert no_publication_possible_between(t, n, BRUSSELS) is True
        # ...and the same instants under the REAL zone, not fixed offsets.
        assert no_publication_possible_between(
            t.astimezone(BRUSSELS), n.astimezone(BRUSSELS), BRUSSELS,
        ) is True

    def test_dst_fall_transition_brussels(self) -> None:
        # EU fall-back 2026: Sunday 2026-10-25 01:00 UTC (CEST -> CET).
        t = datetime(2026, 10, 24, 9, 0, tzinfo=CEST)  # Sat 09:00 +02
        n = datetime(2026, 10, 25, 23, 59, tzinfo=CET)  # Sun 23:59 +01
        assert no_publication_possible_between(t, n, BRUSSELS) is True

    def test_dst_transition_does_not_create_a_fake_workday(self) -> None:
        # Sunday 2026-10-25 spans two UTC offsets inside Brussels; the
        # zone-date walk must still see only Saturday + Sunday.
        t = datetime(2026, 10, 24, 8, 0, tzinfo=UTC)  # Sat 10:00 CEST
        n = datetime(2026, 10, 25, 22, 59, tzinfo=UTC)  # Sun 23:59 CET
        assert no_publication_possible_between(t, n, BRUSSELS) is True

    def test_utc_date_differs_from_brussels_date(self) -> None:
        # UTC calendar days and Brussels calendar days diverge around
        # midnight; the predicate must walk BRUSSELS dates.
        #
        # Dangerous direction (UTC days look like one weekend, Brussels
        # days span into Monday): T = Sun 2026-01-11 00:30 Brussels
        # (= Sat 2026-01-10 23:30 UTC), N = Mon 2026-01-12 00:00
        # Brussels (= Sun 2026-01-11 23:00 UTC). A naive UTC-day rule
        # sees only Sat/Sun and would REUSE across the Monday boundary;
        # the Brussels walk sees Sunday + Monday -> NOT reusable.
        t = datetime(2026, 1, 10, 23, 30, tzinfo=UTC)  # Sun 00:30 Brussels
        n = datetime(2026, 1, 11, 23, 0, tzinfo=UTC)   # Mon 00:00 Brussels
        assert t.date() != t.astimezone(BRUSSELS).date()
        assert no_publication_possible_between(t, n, BRUSSELS) is False
        # Contrast: the UTC days in [t, n] are both weekend days — a
        # UTC-day predicate would have (wrongly) said True.
        assert t.date().weekday() in (5, 6)
        assert n.date().weekday() in (5, 6)

    def test_utc_weekend_divergence_other_direction(self) -> None:
        # Conservative direction (UTC days span Fri+Sat, Brussels days
        # are one Saturday): T = Fri 2026-01-09 23:30 UTC = Sat 00:30
        # Brussels, N = Sat 2026-01-10 09:00 UTC = Sat 10:00 Brussels.
        # Brussels walk: Saturday only -> REUSABLE; a naive UTC-day
        # rule would see Friday in the interval (wrongly conservative).
        t = datetime(2026, 1, 9, 23, 30, tzinfo=UTC)   # Sat 00:30 Brussels
        n = datetime(2026, 1, 10, 9, 0, tzinfo=UTC)    # Sat 10:00 Brussels
        assert t.date() != t.astimezone(BRUSSELS).date()
        assert no_publication_possible_between(t, n, BRUSSELS) is True

    def test_target_closing_day_independence(self) -> None:
        # 2026-12-28 (Monday) is a known TARGET closing day. The
        # predicate references NO calendar data: the adjacent weekend
        # evaluates identically to any other weekend.
        sat = date(2026, 12, 26)
        sun = date(2026, 12, 27)
        assert no_publication_possible_between(
            _dt(sat, 9), _dt(sun, 18), CET,
        ) is True
        # And the following working day (closing day or not) breaks it.
        mon = date(2026, 12, 28)
        assert no_publication_possible_between(
            _dt(sat, 9), _dt(mon, 9), CET,
        ) is False

    # --- fail-closed contract violations ---

    def test_naive_proof_rejected(self) -> None:
        with pytest.raises(TypeError):
            no_publication_possible_between(
                _dt(SAT, 9).replace(tzinfo=None), _dt(SAT, 12), CET,
            )

    def test_naive_use_rejected(self) -> None:
        with pytest.raises(TypeError):
            no_publication_possible_between(
                _dt(SAT, 9), _dt(SAT, 12).replace(tzinfo=None), CET,
            )

    def test_non_datetime_rejected(self) -> None:
        with pytest.raises(TypeError):
            no_publication_possible_between(SAT, _dt(SAT, 12), CET)  # type: ignore[arg-type]

    def test_proof_after_use_rejected(self) -> None:
        with pytest.raises(ValueError):
            no_publication_possible_between(
                _dt(SAT, 12), _dt(SAT, 9), CET,
            )

    def test_non_tzinfo_zone_rejected(self) -> None:
        with pytest.raises(TypeError):
            no_publication_possible_between(
                _dt(SAT, 9), _dt(SAT, 12), "Europe/Brussels",  # type: ignore[arg-type]
            )


# ===========================================================================
# Module purity guards
# ===========================================================================


class TestModulePurity:
    """The freshness/cache contract is pure: stdlib only, no Django,
    no provider, no network, no system-local timezone."""

    MODULE = (
        Path(__file__).resolve().parents[2]
        / "product_intelligence" / "research" / "fx_cache_contract.py"
    )

    def test_top_level_imports_are_stdlib_only(self) -> None:
        tree = ast.parse(self.MODULE.read_text(encoding="utf-8"))
        modules = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                modules.update(a.name for a in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module and not node.level:
                modules.add(node.module)
        disallowed = {
            m for m in modules
            if m not in sys.stdlib_module_names
        }
        assert not disallowed, f"non-stdlib imports: {sorted(disallowed)}"

    def test_no_django_provider_network_or_localtime(self) -> None:
        source = self.MODULE.read_text(encoding="utf-8")
        assert "django" not in source
        assert "product_intelligence" not in source
        assert "urllib" not in source
        assert "requests" not in source
        # No implicit system-local timezone: astimezone() with no
        # argument converts to the SYSTEM local zone and must not appear.
        assert "astimezone()" not in source
        # No provider class identity as cache semantics: the module must
        # not reference ANY provider class name, so no
        # isinstance/issubclass provider-identity logic can exist here.
        for provider_name in (
            "EcbFxProvider", "FxProvider", "FxObservationSet",
            "FxRateObservation",
        ):
            assert provider_name not in source
