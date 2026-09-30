"""Pure FX observation-cache contracts (PRODUCT-INTEL.8A-FX-A1).

This module defines the pure contracts for cross-run reuse of the
canonical production ECB daily FX observation set:

* ``fx_document_content_sha256`` — the deterministic canonical content
  digest of the FULL parsed daily rate observation (content identity,
  post-fetch);
* ``project_required_rates`` — the projection of the full parsed rate
  set to a run's required currencies (the same document-order filter
  the ECB adapter performs after parsing; shared by the LIVE and
  CACHE_HIT paths so both produce byte-identical run payloads);
* ``no_publication_possible_between`` — the freshness predicate that
  decides whether a live proof of an observation at instant T may be
  reused at a later instant N.

Rules:
* Standard library only. No Django, no providers, no I/O, no network.
* Timezone-aware datetime inputs only: naive or malformed datetime
  values fail closed (``TypeError``), and an impossible ordering
  (proof after use) fails closed (``ValueError``).
* The publication-contract zone is a PARAMETER: production passes
  ``Europe/Brussels`` (CET/CEST, DST-aware via ``zoneinfo``); tests may
  pin fixed offsets or the real zone. The system-local timezone is
  never consulted implicitly.
* The digest is computed from the canonical representation of the FULL
  PARSED rate observation — never from a raw provider body (raw bodies
  remain unpersisted by design).
* Provider class identity is NOT a contract of this module and must not
  be used as cache-eligibility semantics (eligibility is declared at the
  canonical-default construction site in the execution layer).
"""

from __future__ import annotations

import hashlib
import json
import re
from datetime import date, datetime as _dt_cls, timedelta
from datetime import timezone as _dt_timezone
import datetime as _dt_module
from decimal import Decimal
from typing import Sequence

# The tzinfo base class lives on the datetime MODULE (datetime.tzinfo);
# it is the type test for the publication-contract zone parameter.
_tzinfo_cls = _dt_module.tzinfo

_WEEKEND_WEEKDAYS = (5, 6)  # date.weekday(): Monday=0 ... Saturday=5, Sunday=6


# ---------------------------------------------------------------------------
# Canonical content digest (post-fetch content identity)
# ---------------------------------------------------------------------------


def fx_document_content_sha256(
    *,
    provider_id: str,
    base_currency: str,
    observation_date: date,
    rates: Sequence[tuple[str, Decimal]],
) -> str:
    """Deterministic canonical SHA-256 of the FULL parsed rate observation.

    The digest is the post-fetch CONTENT identity of one parsed daily
    document: a correction/republication for the same ``observation_date``
    with changed rates produces a different digest and therefore a
    distinct content identity. The same content re-fetched at any later
    instant produces the SAME digest (the retrieval instant is NOT
    content).

    Determinism contract:
    * stable currency ordering — the rate pairs are sorted by currency
      code; the result never depends on input order or Python
      dict-order;
    * exact Decimal textual representation — ``str(Decimal)`` verbatim;
      no float conversion, no locale formatting, no exponent
      normalization;
    * provider/base/observation identity included (an observation is
      provider_id + base_currency + observation_date + full rate set);
    * ASCII-only canonical JSON (``sort_keys``, compact separators,
      ``ensure_ascii``) so the encoding is byte-stable across platforms.

    Inputs are validated fail-closed: malformed codes, non-Decimal or
    non-finite/non-positive rates, and a datetime passed as
    ``observation_date`` are programming/contract defects and raise.
    """
    if not isinstance(provider_id, str) or not provider_id.strip():
        raise ValueError("provider_id must be a non-empty string")
    if not isinstance(base_currency, str) or not base_currency.strip():
        raise ValueError("base_currency must be a non-empty string")
    if isinstance(observation_date, _dt_cls):
        raise TypeError(
            "observation_date must be a date, not a datetime "
            "(the observation date is the document date)"
        )
    if not isinstance(observation_date, date):
        raise TypeError(
            f"observation_date must be a date, got {type(observation_date).__name__}"
        )
    if rates is None or isinstance(rates, (str, bytes)):
        raise TypeError("rates must be a sequence of (currency_code, rate) pairs")

    pairs: list[tuple[str, str]] = []
    for index, pair in enumerate(rates):
        if not isinstance(pair, (tuple, list)) or len(pair) != 2:
            raise TypeError(
                f"rates[{index}] must be a (currency_code, rate) pair, "
                f"got {type(pair).__name__}"
            )
        code, rate = pair
        if not isinstance(code, str):
            raise TypeError(
                f"rates[{index}][0] must be a currency code string, got "
                f"{type(code).__name__}"
            )
        cleaned = code.strip().upper()
        if not re.fullmatch(r"[A-Z]{3}", cleaned):
            raise ValueError(
                f"rates[{index}][0] must be a three-letter ISO currency code, "
                f"got {code!r}"
            )
        if not isinstance(rate, Decimal):
            raise TypeError(
                f"rates[{index}][1] must be a Decimal, got {type(rate).__name__}"
            )
        if not rate.is_finite():
            raise ValueError(
                f"rates[{index}][1] must be finite; NaN/Infinity rejected"
            )
        if rate <= 0:
            raise ValueError(f"rates[{index}][1] must be positive: {rate}")
        pairs.append((cleaned, str(rate)))

    # Stable ordering: sorted by currency code. Duplicates (same code,
    # different or equal values) keep their relative order via a stable
    # sort on the code only — the canonical form is the parsed content,
    # not an interpretation of it.
    pairs.sort(key=lambda item: item[0])

    canonical = {
        "provider_id": provider_id.strip(),
        "base_currency": base_currency.strip().upper(),
        "observation_date": observation_date.isoformat(),
        "rates": pairs,
    }
    blob = json.dumps(
        canonical, sort_keys=True, separators=(",", ":"), ensure_ascii=True
    )
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()


# ---------------------------------------------------------------------------
# Full-set -> required-currencies projection
# ---------------------------------------------------------------------------


def project_required_rates(
    full_rates: Sequence,
    required_currencies: frozenset[str] | set[str] | None,
) -> tuple:
    """Project the FULL parsed rate set to the required currencies.

    Mirrors the ECB adapter's own post-parse filter exactly: document
    order is preserved and the comparison is case-insensitive over
    stripped codes. ``None`` returns the full set unchanged (the
    provider contract's unfiltered form).

    ``full_rates`` is duck-typed over entries carrying a string
    ``currency_code`` attribute — both the provider's rate observation
    objects and the codec's ``FxRateEntry`` entries satisfy it. This
    keeps the research layer provider-import-free and class-free.

    A ``required_currencies`` string (a single code, not a set of codes)
    is a programming defect and fails closed.
    """
    if full_rates is None:
        raise TypeError("full_rates must be a sequence of rate entries")
    if isinstance(full_rates, (str, bytes)):
        raise TypeError("full_rates must be a sequence of rate entries")
    if required_currencies is None:
        return tuple(full_rates)
    if isinstance(required_currencies, (str, bytes)):
        raise TypeError(
            "required_currencies must be a set of currency codes or None"
        )
    requested_upper = frozenset(str(c).strip().upper() for c in required_currencies)
    projected = []
    for index, entry in enumerate(full_rates):
        code = getattr(entry, "currency_code", None)
        if not isinstance(code, str):
            raise TypeError(
                f"full_rates[{index}] must carry a string currency_code, got "
                f"{type(code).__name__}"
            )
        if code in requested_upper:
            projected.append(entry)
    return tuple(projected)


# ---------------------------------------------------------------------------
# Freshness predicate (pure temporal contract)
# ---------------------------------------------------------------------------


def _require_aware_datetime(value: object, field_name: str) -> _dt_cls:
    """Fail closed on non-datetime or naive datetime inputs."""
    if not isinstance(value, _dt_cls):
        raise TypeError(
            f"{field_name} must be a datetime, got {type(value).__name__}"
        )
    if value.tzinfo is None or value.utcoffset() is None:
        raise TypeError(f"{field_name} must be timezone-aware")
    return value


def no_publication_possible_between(
    proof_instant: _dt_cls,
    use_instant: _dt_cls,
    zone: _tzinfo_cls,
) -> bool:
    """True iff no ECB working day overlaps the closed interval [T, N].

    T is the ACTUAL live proof instant (``last_proven_at``) and N is the
    ACTUAL current use instant. T is NEVER collapsed to a date before
    evaluation: the interval is closed at T, so a proof on a working day
    is never sufficient for any N >= T (a delayed working-day publication
    is not excludable).

    The policy consumes exactly two deterministic consequences of the
    ECB's documented regular publication schedule (reference rates are
    normally updated on working days around 16:00 CET, except TARGET
    closing days):

    * C1 (closure): Saturday and Sunday are NEVER working days, in any
      year, under any DST arrangement — hence no publication event can
      occur at any instant whose ``zone`` calendar day is a weekend day.
    * C2 (working-day risk): at any instant whose ``zone`` calendar day
      is Monday-Friday, a publication event is NOT excludable (publication
      timing is approximate; delayed publication and corrections are
      possible). TARGET closing days have no authoritative calendar
      contract in A1 and are treated conservatively like working days.

    Therefore reuse is possible only while EVERY ``zone`` calendar day
    that overlaps [T, N] is a weekend day — i.e. T and N lie in the same
    ``zone`` weekend stretch [Saturday 00:00, Monday 00:00).

    The zone is the publication-contract zone (production:
    ``Europe/Brussels``, CET/CEST via ``zoneinfo``; DST boundaries are
    handled by the zone conversion, never by fixed offsets). This is an
    explicit conservative A1 freshness POLICY; it does not claim that the
    ECB is physically incapable of an exceptional weekend correction.

    Contract violations fail closed: naive T or N -> ``TypeError``;
    T > N (impossible ordering) -> ``ValueError``; a non-tzinfo zone ->
    ``TypeError``.
    """
    t = _require_aware_datetime(proof_instant, "proof_instant")
    n = _require_aware_datetime(use_instant, "use_instant")
    if not isinstance(zone, _tzinfo_cls):
        raise TypeError(
            f"zone must be a datetime.tzinfo, got {type(zone).__name__}"
        )
    if t > n:
        raise ValueError(
            "proof_instant may not be after use_instant "
            "(a proof can only cover the interval up to the present)"
        )

    day = t.astimezone(zone).date()
    last_day = n.astimezone(zone).date()
    while day <= last_day:
        if day.weekday() not in _WEEKEND_WEEKDAYS:
            return False
        day += timedelta(days=1)
    return True
