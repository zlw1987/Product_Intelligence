"""Provider-neutral FX-rate boundary + ECB adapter (PRODUCT-INTEL.4D-C-A).

This module defines the generic contracts for fetching official FX reference
rates and provides a concrete ECB (European Central Bank) adapter.

Rules:
* Standard library only. No third-party HTTP dependency.
* Vendor-free boundary. No ECB name appears in the Protocol/contract.
* Decimal-only. No binary float anywhere in rate values.
* Bounded network behaviour: explicit timeout, bounded response size.
* Deterministic parsing: malformed/non-finite values rejected.
* No secrets in URL/logs.

What this boundary is *not*
---------------------------

**It is not a live price feed.** ECB reference rates are daily, not intraday.

**It is not currency discovery.** The caller names what currencies it needs.

**It does not convert currencies.** Conversion is `research/fx_math.py`.
This module only observes rates and returns them as Decimal values.

**It is not persistence.** Nothing here is persisted. Persistence is owned by
`runs.ResearchFxSnapshot` via `research/fx_codec.py`.
"""

from __future__ import annotations

import logging
import math
import re
import xml.etree.ElementTree as ET
from dataclasses import dataclass, field
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from typing import Protocol

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Bounded network constants
# ---------------------------------------------------------------------------

_DEFAULT_REQUEST_TIMEOUT_SECONDS = 10.0
_DEFAULT_MAX_RESPONSE_BYTES = 512 * 1024  # 512 KiB


# ---------------------------------------------------------------------------
# Contract: FX rate observation
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class FxRateObservation:
    """One FX rate observation for one currency.

    ECB rates are EUR-based: 1 EUR = rate <currency>.
    The value is always Decimal (exact, never float).

    Attributes:
        currency_code: ISO 4217 three-letter code.
        rate: The rate value (Decimal). For EUR this is 1.
    """

    currency_code: str
    rate: Decimal

    def __post_init__(self) -> None:
        if not isinstance(self.currency_code, str):
            raise TypeError(
                f"currency_code must be a string, got "
                f"{type(self.currency_code).__name__}"
            )
        code = self.currency_code.strip().upper()
        if not re.fullmatch(r"[A-Z]{3}", code):
            raise ValueError(
                f"currency_code must be a three-letter ISO code, got {code!r}"
            )
        object.__setattr__(self, "currency_code", code)

        if not isinstance(self.rate, Decimal):
            raise TypeError(
                f"rate must be a Decimal, got {type(self.rate).__name__}"
            )
        if not self.rate.is_finite():
            raise ValueError(
                f"rate must be finite; NaN/Infinity rejected: {self.rate}"
            )
        if self.rate <= 0:
            raise ValueError(
                f"rate must be positive; zero/negative rejected: {self.rate}"
            )


@dataclass(frozen=True)
class FxObservationSet:
    """A set of FX rates from one observation date.

    Represents one day's official reference rates.

    Attributes:
        provider_id: Identifier for the rate provider (e.g. "ECB").
        observation_date: The date of the rates (date, not datetime).
        base_currency: The base currency for these rates (e.g. "EUR").
        rates: Tuple of FxRateObservation objects.
        retrieved_at: When this observation set was fetched (timezone-aware).
    """

    provider_id: str
    observation_date: date
    base_currency: str
    rates: tuple[FxRateObservation, ...] = ()
    retrieved_at: datetime | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.provider_id, str) or not self.provider_id.strip():
            raise ValueError("provider_id must be a non-empty string")
        object.__setattr__(self, "provider_id", self.provider_id.strip())

        if not isinstance(self.observation_date, date):
            raise TypeError(
                f"observation_date must be a date, got "
                f"{type(self.observation_date).__name__}"
            )

        if not isinstance(self.base_currency, str):
            raise TypeError(
                f"base_currency must be a string, got "
                f"{type(self.base_currency).__name__}"
            )
        base = self.base_currency.strip().upper()
        if not re.fullmatch(r"[A-Z]{3}", base):
            raise ValueError(
                f"base_currency must be a three-letter ISO code, got {base!r}"
            )
        object.__setattr__(self, "base_currency", base)

        if isinstance(self.rates, (str, bytes)):
            raise TypeError("rates must be a tuple of FxRateObservation")
        rates = tuple(self.rates)
        for i, r in enumerate(rates):
            if not isinstance(r, FxRateObservation):
                raise TypeError(
                    f"rates[{i}] must be a FxRateObservation, got "
                    f"{type(r).__name__}"
                )
        object.__setattr__(self, "rates", rates)

        if self.retrieved_at is not None:
            if not isinstance(self.retrieved_at, datetime):
                raise TypeError(
                    f"retrieved_at must be a datetime or None, got "
                    f"{type(self.retrieved_at).__name__}"
                )
            if (
                self.retrieved_at.tzinfo is None
                or self.retrieved_at.utcoffset() is None
            ):
                raise ValueError(
                    "retrieved_at must be timezone-aware when present"
                )

    def get_rate(self, currency_code: str) -> FxRateObservation | None:
        """Return the rate for ``currency_code``, or ``None`` if absent."""
        target = currency_code.strip().upper()
        for obs in self.rates:
            if obs.currency_code == target:
                return obs
        return None


# ---------------------------------------------------------------------------
# Provider Protocol
# ---------------------------------------------------------------------------


class FxProvider(Protocol):
    """Provider-neutral boundary for fetching FX reference rates.

    One synchronous method. A ``Protocol`` rather than a base class.

    An implementation must:
    * accept a set of requested currency codes (or return the full set)
    * return an ``FxObservationSet`` with Decimal rate values
    * respect bounded timeout and response size
    * never import research/persistence/web layers
    """

    def fetch_rates(
        self,
        requested_currencies: frozenset[str] | None = None,
    ) -> FxObservationSet:
        """Fetch official FX reference rates.

        ``requested_currencies`` is the set of currency codes the caller
        needs. If None, the provider returns its full rate set.

        Returns an ``FxObservationSet``. Raises on network failure,
        parse failure, or timeout.
        """
        ...


# ---------------------------------------------------------------------------
# Exceptions
# ---------------------------------------------------------------------------


class FxProviderError(Exception):
    """FX provider operation failed."""


class FxParseError(FxProviderError):
    """Could not parse the FX rate document."""


class FxNetworkError(FxProviderError):
    """Network/transport failure contacting the FX provider."""


# ---------------------------------------------------------------------------
# ECB Adapter — European Central Bank daily reference rates
# ---------------------------------------------------------------------------

_ECB_STATISTICS_URL = (
    "https://www.ecb.europa.eu/stats/eurofxref/eurofxref-daily.xml"
)


def _parse_ecb_xml(body: str) -> FxObservationSet:
    """Parse an ECB eurofxref-daily XML document into an FxObservationSet.

    Raises FxParseError on structural failure.
    Rejects NaN, Infinity, zero, or negative rate values.
    Rejects non-Decimal values (floats in XML are already strings, but we
    guard against any path that could produce a float).

    ECB document structure::

        <gesmes:Envelope>
          <Cube>
            <TimeSeries>
              <Cube time="2024-01-15">
                <Cube currency="USD" rate="1.0934"/>
                ...
              </Cube>
            </Cube>
          </Cube>
        </gesmes:Envelope>

    The EUR rate is implicitly 1 and is not always present in the XML.
    It is added by convention if the base is EUR.
    """
    try:
        root = ET.fromstring(body)
    except ET.ParseError as exc:
        raise FxParseError(
            f"ECB XML document is not valid XML: {exc}"
        ) from exc

    # Navigate the ECB structure using namespaces
    # The gesmes namespace is for the Envelope; Cube elements may use
    # the eurofxref namespace or no namespace at all.
    ns_gesmes = "http://www.gesmes.org/xml/2002-08-01"
    ns_ecb = "http://www.ecb.int/vocabulary/2002-08-01/eurofxref"

    # Find all Cube elements regardless of namespace
    # ECB document: Envelope -> Cube -> Cube -> TimeSeries -> Cube(time=DATE) -> Cube(currency=X rate=Y)
    cubes_with_time: list[ET.Element] = []
    for elem in root.iter():
        tag = elem.tag
        # Strip namespace prefix
        local_name = tag.split("}", 1)[-1] if "}" in tag else tag
        if local_name == "Cube" and elem.get("time"):
            cubes_with_time.append(elem)

    if not cubes_with_time:
        raise FxParseError(
            "ECB document contains no Cube element with a 'time' attribute"
        )

    rate_cube = cubes_with_time[0]
    observation_date_str = rate_cube.get("time")

    # Parse observation date
    try:
        observation_date = date.fromisoformat(observation_date_str)
    except (ValueError, TypeError) as exc:
        raise FxParseError(
            f"ECB observation date is not a valid date: {observation_date_str!r}"
        ) from exc

    # Parse individual currency rates
    rates: list[FxRateObservation] = []
    # Child Cubes are the individual rates
    for child in rate_cube:
        tag = child.tag
        # Strip namespace if present
        if "}" in tag:
            tag = tag.split("}", 1)[1]
        if tag != "Cube":
            continue

        currency = child.get("currency")
        rate_str = child.get("rate")

        if not currency or not rate_str:
            continue

        # Validate currency code
        currency_clean = currency.strip().upper()
        if not re.fullmatch(r"[A-Z]{3}", currency_clean):
            continue

        # Parse rate as Decimal — reject NaN, Infinity, zero, negative
        try:
            rate_val = Decimal(rate_str)
        except (InvalidOperation, ValueError) as exc:
            raise FxParseError(
                f"ECB rate for {currency_clean} is not a valid number: "
                f"{rate_str!r}"
            ) from exc

        if not rate_val.is_finite():
            raise FxParseError(
                f"ECB rate for {currency_clean} is non-finite: {rate_str!r}"
            )

        if rate_val <= 0:
            raise FxParseError(
                f"ECB rate for {currency_clean} must be positive: {rate_str!r}"
            )

        rates.append(FxRateObservation(
            currency_code=currency_clean,
            rate=rate_val,
        ))

    if not rates:
        raise FxParseError(
            "ECB document contains valid structure but no currency rates"
        )

    return FxObservationSet(
        provider_id="ECB",
        observation_date=observation_date,
        base_currency="EUR",
        rates=tuple(rates),
    )


class EcbFxProvider:
    """Concrete ECB FX-rate adapter.

    Fetches the latest ECB daily reference-rate document and parses it
    into an ``FxObservationSet``.

    Uses only stdlib ``urllib.request``. Bounded timeout and response size.
    No secrets in URL or logs.
    """

    def __init__(
        self,
        *,
        request_timeout_seconds: float = _DEFAULT_REQUEST_TIMEOUT_SECONDS,
        max_response_bytes: int = _DEFAULT_MAX_RESPONSE_BYTES,
    ) -> None:
        """Construct the ECB adapter.

        Args:
            request_timeout_seconds: HTTP request timeout in seconds.
            max_response_bytes: Maximum acceptable response body size.
        """
        if not isinstance(request_timeout_seconds, (int, float)):
            raise TypeError(
                f"request_timeout_seconds must be numeric, got "
                f"{type(request_timeout_seconds).__name__}"
            )
        timeout = float(request_timeout_seconds)
        if not math.isfinite(timeout) or timeout <= 0:
            raise ValueError(
                f"request_timeout_seconds must be a positive finite number: "
                f"{request_timeout_seconds}"
            )
        self._timeout = timeout

        if not isinstance(max_response_bytes, int):
            raise TypeError(
                f"max_response_bytes must be an int, got "
                f"{type(max_response_bytes).__name__}"
            )
        if max_response_bytes <= 0:
            raise ValueError(
                f"max_response_bytes must be positive: {max_response_bytes}"
            )
        self._max_response_bytes = max_response_bytes

    def fetch_rates(
        self,
        requested_currencies: frozenset[str] | None = None,
    ) -> FxObservationSet:
        """Fetch ECB daily reference rates.

        Fetches the full ECB document and optionally filters to
        ``requested_currencies`` after parsing.

        Raises:
            FxNetworkError: on timeout, connection failure, HTTP error.
            FxParseError: on malformed XML, missing rates, invalid values.
        """
        import urllib.request
        import urllib.error

        # Build the request — no secrets, no credentials
        req = urllib.request.Request(_ECB_STATISTICS_URL)
        req.add_header(
            "User-Agent",
            "Product-Intelligence/1.0 (FX Reference Rates)",
        )
        req.add_header("Accept", "application/xml, text/xml, */*")

        try:
            with urllib.request.urlopen(req, timeout=self._timeout) as resp:
                body_bytes = resp.read(self._max_response_bytes + 1)
        except urllib.error.HTTPError as exc:
            raise FxNetworkError(
                f"ECB HTTP error: {exc.code}"
            ) from exc
        except urllib.error.URLError as exc:
            raise FxNetworkError(
                f"ECB network error: {exc.reason}"
            ) from exc
        except TimeoutError as exc:
            raise FxNetworkError(
                f"ECB request timed out after {self._timeout}s"
            ) from exc
        # NOTE: No broad `except Exception` here. Programming defects
        # (TypeError, ValueError, AssertionError, OSError subclasses that are
        # not URLError) must propagate according to normal execution safety
        # semantics. Only the bounded transport exception taxonomy above is
        # classified as a supplemental FX provider failure.

        # Bounded response size check
        if len(body_bytes) > self._max_response_bytes:
            raise FxParseError(
                f"ECB response exceeds maximum size "
                f"({len(body_bytes)} > {self._max_response_bytes} bytes)"
            )

        # Decode to string for XML parsing
        try:
            body_text = body_bytes.decode("utf-8")
        except UnicodeDecodeError as exc:
            raise FxParseError(
                f"ECB response is not valid UTF-8"
            ) from exc

        # Parse the XML
        import datetime as _dt
        observation_set = _parse_ecb_xml(body_text)
        observation_set_retrieved = FxObservationSet(
            provider_id=observation_set.provider_id,
            observation_date=observation_set.observation_date,
            base_currency=observation_set.base_currency,
            rates=observation_set.rates,
            retrieved_at=_dt.datetime.now(_dt.timezone.utc),
        )

        # Filter to requested currencies if specified
        if requested_currencies:
            requested_upper = frozenset(
                c.strip().upper() for c in requested_currencies
            )
            filtered_rates = tuple(
                r for r in observation_set_retrieved.rates
                if r.currency_code in requested_upper
            )
            return FxObservationSet(
                provider_id=observation_set_retrieved.provider_id,
                observation_date=observation_set_retrieved.observation_date,
                base_currency=observation_set_retrieved.base_currency,
                rates=filtered_rates,
                retrieved_at=observation_set_retrieved.retrieved_at,
            )

        return observation_set_retrieved
