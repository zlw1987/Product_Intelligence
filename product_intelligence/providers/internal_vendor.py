"""Concrete internal vendor adapter (PRODUCT-INTEL.4D-B).

This adapter reads the configured ``PI_VENDOR_LOOKUP_BASE_URL`` from the
server environment and performs at most ONE Vendor API network call per
lookup. The Vendor API returns structured commercial observations from
upstream sources (Ingram, CDW, Synnex EU).

Key constraints:
* At most ONE network call per lookup
* No retries
* No fanout
* No per-vendor network calls
* No alias expansion
* No Micron R/T handling
* No browser
* No proxy/bot-bypass machinery
* No cookies
* No Authorization
* Bounded timeout (10s)
* Bounded response size (1 MiB)
* NO redirects followed (refuse 30x entirely)
* NO ambient proxy (dedicated opener, no ProxyHandler)
* URL-encode the canonical requested MPN
* GET only
* JSON response (Decimal-aware parse for monetary values)

The configured base URL is deployment-owned, not request-controlled.
No user-supplied endpoint is accepted. Base URL must not carry query
parameters, fragments, or credentials.

Sensitive metadata (SessionId, BuyerAccountId, SystemId, etc.) is stripped
by construction: source mappers read ONLY approved allowlisted fields.
Unknown upstream fields are ignored.
"""

from __future__ import annotations

import json
import logging
from decimal import Decimal, InvalidOperation
from datetime import datetime, timezone
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode, urlsplit
from urllib.request import (
    HTTPRedirectHandler,
    OpenerDirector,
    ProxyHandler,
    Request,
    build_opener,
)

from product_intelligence.providers.commercial import (
    CommercialAvailability,
    CommercialLookupQuery,
    CommercialNoteKind,
    CommercialPriceBasis,
    CommercialSourceCandidate,
    CommercialSourceIssue,
    CommercialSourceProvider,
    CommercialSourceResponse,
    LookupStatus,
    SourceOutcome,
)

logger = logging.getLogger(__name__)

# Bounded network parameters
_VENDOR_TIMEOUT = 10  # seconds
_VENDOR_MAX_BODY = 1 * 1024 * 1024  # 1 MiB

# Bounded source name vocabulary
_ALLOWED_SOURCE_NAMES: frozenset[str] = frozenset({
    "Ingram",
    "CDW",
    "Synnex EU",
    "Unknown",
})

# ---------------------------------------------------------------------------
# Dedicated network opener — no ambient proxy, no redirect following
# ---------------------------------------------------------------------------


class _NoRedirectHandler(HTTPRedirectHandler):
    """Refuse ALL HTTP redirects (3xx). Never follow, never escape.

    Subclassing HTTPRedirectHandler so that build_opener registers our
    methods into the opener's dispatch tables (handle_open / handle_error
    / process_request / process_response). HTTPDefaultErrorHandler does not
    own those registrations.

    redirect_request() always raises so no subclass redirect logic fires.
    """

    def redirect_request(
        self,
        req: Request,
        fp: Any,
        code: int,
        msg: str,
        headers: Any,
        newurl: str,
    ) -> None:
        raise HTTPError(
            req.full_url, code, f"Redirect refused: {msg}", headers, fp
        )

    def http_error_301(
        self, req: Request, fp: Any, code: int, msg: str, headers: Any
    ) -> None:
        raise HTTPError(
            req.full_url, code, f"Redirect refused: {msg}", headers, fp
        )

    def http_error_302(
        self, req: Request, fp: Any, code: int, msg: str, headers: Any
    ) -> None:
        raise HTTPError(
            req.full_url, code, f"Redirect refused: {msg}", headers, fp
        )

    def http_error_303(
        self, req: Request, fp: Any, code: int, msg: str, headers: Any
    ) -> None:
        raise HTTPError(
            req.full_url, code, f"Redirect refused: {msg}", headers, fp
        )

    def http_error_307(
        self, req: Request, fp: Any, code: int, msg: str, headers: Any
    ) -> None:
        raise HTTPError(
            req.full_url, code, f"Redirect refused: {msg}", headers, fp
        )

    def http_error_308(
        self, req: Request, fp: Any, code: int, msg: str, headers: Any
    ) -> None:
        raise HTTPError(
            req.full_url, code, f"Redirect refused: {msg}", headers, fp
        )


def _build_vendor_opener() -> OpenerDirector:
    """Build a dedicated OpenerDirector with NO proxy and NO redirect following.

    Uses explicit ProxyHandler({}) so ambient HTTP_PROXY / HTTPS_PROXY
    environment variables are NEVER honoured.

    Redirects (30x) are refused entirely — the one-network-call invariant
    is preserved by never making a second request.

    Uses build_opener's native add_handler to populate dispatch tables
    (handle_open / handle_error / process_request / process_response).
    Does NOT manually assign .handlers.
    """
    opener = build_opener(
        ProxyHandler({}),
        _NoRedirectHandler(),
    )
    opener.addheaders = []  # no default headers
    return opener


# Global opener — built once, reused
_VENDOR_OPENER: OpenerDirector | None = None


def _get_vendor_opener() -> OpenerDirector:
    global _VENDOR_OPENER
    if _VENDOR_OPENER is None:
        _VENDOR_OPENER = _build_vendor_opener()
    return _VENDOR_OPENER


# ---------------------------------------------------------------------------
# Configuration validation
# ---------------------------------------------------------------------------


def _validate_base_url(base_url: str) -> str:
    """Validate the configured Vendor API base URL.

    Requirements:
    * Absolute http or https
    * Host required
    * No embedded username/password
    * No fragment
    * No query string (base must be clean path; params added by adapter)
    """
    if not base_url or not base_url.strip():
        raise ValueError(
            "PI_VENDOR_LOOKUP_BASE_URL is not configured; "
            "vendor commercial lookup is unavailable"
        )

    url = base_url.strip()
    parts = urlsplit(url)

    if parts.scheme.lower() not in ("http", "https"):
        raise ValueError(
            f"PI_VENDOR_LOOKUP_BASE_URL must use http or https, "
            f"got scheme {parts.scheme!r}"
        )

    if not parts.netloc:
        raise ValueError(
            "PI_VENDOR_LOOKUP_BASE_URL must include a host"
        )

    # Reject embedded credentials
    if parts.username or parts.password:
        raise ValueError(
            "PI_VENDOR_LOOKUP_BASE_URL must not contain embedded credentials"
        )

    # Reject fragments
    if parts.fragment:
        raise ValueError(
            "PI_VENDOR_LOOKUP_BASE_URL must not contain a fragment"
        )

    # Reject query strings — base must be clean
    if parts.query:
        raise ValueError(
            "PI_VENDOR_LOOKUP_BASE_URL must not contain query parameters"
        )

    return url


def _build_lookup_url(base_url: str, mpn: str) -> str:
    """Build the Vendor API lookup URL for one exact MPN.

    The MPN is URL-encoded and appended as a ``partno`` query parameter.
    Base URL is guaranteed to have no query string by _validate_base_url.
    """
    encoded_params = urlencode({"partno": mpn})
    return f"{base_url}?{encoded_params}"


# ---------------------------------------------------------------------------
# JSON parse constants (non-standard)
# ---------------------------------------------------------------------------


class _InvalidVendorJsonConstant(ValueError):
    """Raised when a non-standard JSON constant (NaN/Infinity) is encountered.

    This is a bounded external-data exception. It is NOT a programming error
    and does NOT log the raw token or payload.
    """

    pass


def _reject_json_constant(token: str) -> None:
    """Reject non-standard JSON constants at parse boundary.

    Python's json.loads accepts NaN, Infinity, -Infinity by default.
    This callback raises a bounded exception instead.

    Raises:
        _InvalidVendorJsonConstant: always, for any non-standard constant token.
    """
    raise _InvalidVendorJsonConstant(
        f"Non-standard JSON constant rejected: {token!r}"
    )


# ---------------------------------------------------------------------------
# Safe value helpers
# ---------------------------------------------------------------------------


def _safe_decimal(value: Any, default: Decimal | None = None) -> Decimal | None:
    """Parse a value as exact Decimal, return default on failure.

    Accepted:
    - Decimal (finite, returned as-is)
    - int (exact type, converted to Decimal)
    - numeric string (parsed as Decimal, require finite)

    Rejected (returns default):
    - bool (explicit type reject; Decimal(True) == Decimal("1"))
    - float (binary float must never traverse a monetary value)
    - None
    - NaN / Infinity (even as strings, after Decimal construction)
    - list / dict / arbitrary object
    """
    if value is None:
        return default
    # Explicitly reject bool — Decimal(True) == Decimal("1") which would
    # allow an external boolean to become a valid commercial price of 1.
    if type(value) is bool:
        return default
    # Explicitly reject binary float — must never become monetary value
    if isinstance(value, float):
        return default
    # Accept Decimal directly (must be finite)
    if isinstance(value, Decimal):
        if not value.is_finite():
            return default
        return value
    # Accept exact int (type check excludes bool which is subclass of int)
    if type(value) is int:
        return Decimal(value)
    # Accept numeric string only
    if isinstance(value, str):
        try:
            result = Decimal(value)
            if not result.is_finite():
                return default
            return result
        except (InvalidOperation, ValueError):
            return default
    # Everything else (list, dict, arbitrary object) -> reject
    return default


def _safe_int(value: Any, default: int | None = None) -> int | None:
    """Parse a value as an exact non-fractional int, return default on failure.

    Explicit type allowlist — no generic int() coercion on arbitrary types.

    Accepted:
    - int (exact type, >= 0)
    - Decimal (finite, mathematically integral, >= 0, converted exactly)

    Rejected (returns default):
    - bool (exact type check)
    - float (never accepted; int(3.7) == 3 is silent truncation)
    - Decimal fraction (e.g. Decimal("3.7") — must NOT truncate)
    - negative int
    - string (no documented Vendor API evidence for string quantities)
    - None
    - list / dict / arbitrary object
    """
    if value is None:
        return default
    # Exact bool check before int — bool is subclass of int
    if type(value) is bool:
        return default
    # Accept int directly (type excludes bool)
    if type(value) is int:
        if value < 0:
            return default
        return value
    # Decimal: must be finite and equal to its integral value
    if isinstance(value, Decimal):
        if not value.is_finite():
            return default
        if value != value.to_integral_value():
            # Fractional (e.g. 3.7 != 4) — reject, do NOT truncate
            return default
        int_val = int(value)
        if int_val < 0:
            return default
        return int_val
    # No generic int(value) fallback — explicit type allowlist only.
    # Float, str, list, dict, arbitrary objects all rejected.
    return default


def _safe_bool(value: Any) -> bool | None:
    """Parse a value as bool, return None if not a bool."""
    if isinstance(value, bool):
        return value
    return None


# ---------------------------------------------------------------------------
# Source-specific mapping — ALLOWLIST semantics only
# Each mapper reads ONLY the approved fields for its source.
# Unknown upstream fields are ignored by construction.
# ---------------------------------------------------------------------------


def _map_ingram(source_section: dict[str, Any]) -> CommercialSourceCandidate | CommercialSourceIssue:
    """Map one Ingram source section from the Vendor API response.

    Reads only approved fields:
    - vendorPartNumber
    - pricing.customerPrice, pricing.retailPrice, pricing.currencyCode
    - availability.available, availability.Avl_Quantity
    - documented not-found marker (NotFound, notFound, "Not Found")
    """
    source_name = "Ingram"

    # Check for not-found response (all documented forms)
    if (
        source_section.get("NotFound")
        or source_section.get("notFound")
        or source_section.get("Not Found")
    ):
        return CommercialSourceIssue(
            source_name=source_name,
            outcome=SourceOutcome.NOT_FOUND)


    # Explicit MPN (required)
    # Type check FIRST: non-string type is MALFORMED, not MISSING
    # But None / absent -> MISSING (no value at all)
    vendor_mpn = source_section.get("vendorPartNumber")
    if vendor_mpn is None:
        return CommercialSourceIssue(
            source_name=source_name,
            outcome=SourceOutcome.MISSING_EXPLICIT_MPN)
    if not isinstance(vendor_mpn, str):
        return CommercialSourceIssue(
            source_name=source_name,
            outcome=SourceOutcome.MALFORMED_SECTION)
    if not vendor_mpn or not vendor_mpn.strip():
        return CommercialSourceIssue(
            source_name=source_name,
            outcome=SourceOutcome.MISSING_EXPLICIT_MPN)


    # Price — customerPrice primary, retailPrice fallback
    pricing = source_section.get("pricing")
    if not isinstance(pricing, dict):
        return CommercialSourceIssue(
            source_name=source_name,
            outcome=SourceOutcome.MALFORMED_SECTION)


    # KEY RULE: if customerPrice key is PRESENT (even if null/malformed),
    # it is authoritative. Do NOT fall back to retailPrice.
    if "customerPrice" in pricing:
        customer_price_raw = pricing["customerPrice"]
        price = _safe_decimal(customer_price_raw)
        if price is None or not price.is_finite() or price < 0:
            # customerPrice present but malformed/non-finite/negative
            return CommercialSourceIssue(
                source_name=source_name,
                outcome=SourceOutcome.MALFORMED_SECTION)

        price_basis = CommercialPriceBasis.CUSTOMER_PRICE
    else:
        # customerPrice ABSENT — retail fallback allowed
        retail_price_raw = pricing.get("retailPrice")
        price = _safe_decimal(retail_price_raw)
        if price is None or not price.is_finite() or price < 0:
            return CommercialSourceIssue(
                source_name=source_name,
                outcome=SourceOutcome.MALFORMED_SECTION)

        price_basis = CommercialPriceBasis.RETAIL_PRICE_FALLBACK

    # Currency — must be str and nonempty
    currency_raw = pricing.get("currencyCode")
    if not isinstance(currency_raw, str) or not currency_raw.strip():
        return CommercialSourceIssue(
            source_name=source_name,
            outcome=SourceOutcome.MALFORMED_SECTION)

    currency = currency_raw.strip().upper()

    # Availability (allowlisted fields only)
    availability_section = source_section.get("availability")
    if not isinstance(availability_section, dict):
        availability = CommercialAvailability.UNKNOWN
        quantity = None
    else:
        available = _safe_bool(availability_section.get("available"))
        qty_raw = availability_section.get("Avl_Quantity")
        quantity = _safe_int(qty_raw)  # negative already rejected by _safe_int

        if available is True and quantity is not None and quantity > 0:
            availability = CommercialAvailability.IN_STOCK
        elif available is True and quantity is not None and quantity == 0:
            availability = CommercialAvailability.UNKNOWN
        elif available is True and quantity is None:
            availability = CommercialAvailability.IN_STOCK
        elif available is False and quantity is not None and quantity == 0:
            availability = CommercialAvailability.OUT_OF_STOCK
        elif available is False and quantity is not None and quantity > 0:
            availability = CommercialAvailability.UNKNOWN
        elif available is False and quantity is None:
            availability = CommercialAvailability.UNKNOWN
        elif available is None and quantity is not None and quantity > 0:
            availability = CommercialAvailability.IN_STOCK
        elif available is None and quantity is not None and quantity == 0:
            availability = CommercialAvailability.UNKNOWN
        elif available is None and quantity is None:
            availability = CommercialAvailability.UNKNOWN
        else:
            availability = CommercialAvailability.UNKNOWN

    return CommercialSourceCandidate(
        source_name=source_name,
        explicit_candidate_mpn=str(vendor_mpn).strip(),
        price_amount=price,
        currency_code=currency,
        availability=availability,
        quantity=quantity,
        price_basis=price_basis,
    )


def _map_cdw(source_section: dict[str, Any]) -> CommercialSourceCandidate | CommercialSourceIssue:
    """Map one CDW source section from the Vendor API response.

    Reads only approved fields:
    - manufacturerPartNumber
    - price
    - currencyCode
    - inventoryStatus.stockStatus, inventoryStatus.Avl_Quantity
    - documented not-found marker (NotFound, notFound, "Not Found")
    """
    source_name = "CDW"

    # Check for not-found response (all documented forms)
    if (
        source_section.get("NotFound")
        or source_section.get("notFound")
        or source_section.get("Not Found")
    ):
        return CommercialSourceIssue(
            source_name=source_name,
            outcome=SourceOutcome.NOT_FOUND)


    # Explicit MPN (required)
    # Type check FIRST: non-string type is MALFORMED, not MISSING
    # But None / absent -> MISSING (no value at all)
    vendor_mpn = source_section.get("manufacturerPartNumber")
    if vendor_mpn is None:
        return CommercialSourceIssue(
            source_name=source_name,
            outcome=SourceOutcome.MISSING_EXPLICIT_MPN)
    if not isinstance(vendor_mpn, str):
        return CommercialSourceIssue(
            source_name=source_name,
            outcome=SourceOutcome.MALFORMED_SECTION)
    if not vendor_mpn or not vendor_mpn.strip():
        return CommercialSourceIssue(
            source_name=source_name,
            outcome=SourceOutcome.MISSING_EXPLICIT_MPN)


    # Price — must be finite, nonnegative Decimal
    price_raw = source_section.get("price")
    price = _safe_decimal(price_raw)
    if price is None or not price.is_finite() or price < 0:
        return CommercialSourceIssue(
            source_name=source_name,
            outcome=SourceOutcome.MALFORMED_SECTION)


    # Currency — must be str and nonempty
    currency_raw = source_section.get("currencyCode")
    if not isinstance(currency_raw, str) or not currency_raw.strip():
        return CommercialSourceIssue(
            source_name=source_name,
            outcome=SourceOutcome.MALFORMED_SECTION)

    currency = currency_raw.strip().upper()

    # Availability
    inventory = source_section.get("inventoryStatus")
    qty_raw = None
    if isinstance(inventory, dict):
        qty_raw = inventory.get("Avl_Quantity")
        stock_status = inventory.get("stockStatus", "")
    else:
        stock_status = ""

    quantity = _safe_int(qty_raw)  # negative already rejected by _safe_int

    if stock_status == "InStock":
        if quantity is not None and quantity == 0:
            availability = CommercialAvailability.UNKNOWN
        else:
            availability = CommercialAvailability.IN_STOCK
    elif stock_status == "OutOfStock":
        if quantity is not None and quantity > 0:
            availability = CommercialAvailability.UNKNOWN
        else:
            availability = CommercialAvailability.OUT_OF_STOCK
    else:
        availability = CommercialAvailability.UNKNOWN

    return CommercialSourceCandidate(
        source_name=source_name,
        explicit_candidate_mpn=vendor_mpn.strip(),
        price_amount=price,
        currency_code=currency,
        availability=availability,
        quantity=quantity,
        price_basis=CommercialPriceBasis.LIST_PRICE,
    )


def _map_synnex_eu(source_section: dict[str, Any]) -> CommercialSourceCandidate | CommercialSourceIssue:
    """Map one Synnex EU source section from the Vendor API response.

    Reads only approved fields:
    - OnlineCheck.Header.CurrencyCode
    - OnlineCheck.Item.ManufacturerItemIdentifier
    - OnlineCheck.Item.UnitPriceAmount
    - OnlineCheck.Item.AvailabilityTotal
    - OnlineCheck.Item.Note (bounded meanings only)
    - documented not-found marker (NotFound, notFound, "Not Found")
    - documented not-maintained semantics

    Not-maintained detection (before normal fields):
    If OnlineCheck.Item.Note contains "not maintained" text,
    result is NOT_FOUND with no candidate.
    """
    source_name = "Synnex EU"

    # Check for not-found at top level (all documented forms)
    if (
        source_section.get("NotFound")
        or source_section.get("notFound")
        or source_section.get("Not Found")
    ):
        return CommercialSourceIssue(
            source_name=source_name,
            outcome=SourceOutcome.NOT_FOUND)


    # Check for "not maintained" at top level flag
    if source_section.get("notMaintained"):
        return CommercialSourceIssue(
            source_name=source_name,
            outcome=SourceOutcome.NOT_FOUND)


    # Synnex EU uses OnlineCheck nesting
    online_check = source_section.get("OnlineCheck")
    if not isinstance(online_check, dict):
        return CommercialSourceIssue(
            source_name=source_name,
            outcome=SourceOutcome.MALFORMED_SECTION)


    # Check for not-maintained Note BEFORE requiring MPN/price
    item = online_check.get("Item")
    if isinstance(item, dict):
        note_raw = item.get("Note")
        if isinstance(note_raw, str) and note_raw.strip():
            note_lower = note_raw.strip().lower()
            if "not maintained" in note_lower:
                # Not maintained in catalogue -> NOT_FOUND, no candidate
                return CommercialSourceIssue(
                    source_name=source_name,
                    outcome=SourceOutcome.NOT_FOUND)


    if not isinstance(item, dict):
        return CommercialSourceIssue(
            source_name=source_name,
            outcome=SourceOutcome.MALFORMED_SECTION)


    # Currency from Header (allowlisted field only)
    # Type check: must be str, nonempty after strip
    header = online_check.get("Header")
    currency: str | None = None
    if isinstance(header, dict):
        currency = header.get("CurrencyCode")
    if not isinstance(currency, str) or not currency.strip():
        return CommercialSourceIssue(
            source_name=source_name,
            outcome=SourceOutcome.MALFORMED_SECTION)

    # Explicit MPN (required)
    # Type check FIRST: non-string type is MALFORMED, not MISSING
    # But None / absent -> MISSING (no value at all)
    vendor_mpn = item.get("ManufacturerItemIdentifier")
    if vendor_mpn is None:
        return CommercialSourceIssue(
            source_name=source_name,
            outcome=SourceOutcome.MISSING_EXPLICIT_MPN)
    if not isinstance(vendor_mpn, str):
        return CommercialSourceIssue(
            source_name=source_name,
            outcome=SourceOutcome.MALFORMED_SECTION)
    if not vendor_mpn or not vendor_mpn.strip():
        return CommercialSourceIssue(
            source_name=source_name,
            outcome=SourceOutcome.MISSING_EXPLICIT_MPN)


    # Price — must be finite, nonnegative Decimal
    price_raw = item.get("UnitPriceAmount")
    price = _safe_decimal(price_raw)
    if price is None or not price.is_finite() or price < 0:
        return CommercialSourceIssue(
            source_name=source_name,
            outcome=SourceOutcome.MALFORMED_SECTION)


    # Availability
    avail_raw = item.get("AvailabilityTotal")
    avail_int = _safe_int(avail_raw)
    if avail_int is not None:
        if avail_int > 0:
            availability = CommercialAvailability.IN_STOCK
        elif avail_int == 0:
            availability = CommercialAvailability.OUT_OF_STOCK
        else:
            # Negative quantity -> UNKNOWN, discard quantity
            availability = CommercialAvailability.UNKNOWN
            quantity = None
        if availability != CommercialAvailability.UNKNOWN:
            quantity = avail_int
        else:
            quantity = None
    else:
        availability = CommercialAvailability.UNKNOWN
        quantity = None

    # Note handling — only approved bounded meanings
    note_kind: CommercialNoteKind | None = None
    if isinstance(note_raw, str) and note_raw.strip():
        if "no return" in note_raw.strip().lower():
            note_kind = CommercialNoteKind.NO_RETURNS
        # "not maintained" already handled above
        # All other free-form note text is dropped

    # Currency — already validated as non-None str above
    currency_val = currency.strip().upper()  # type: ignore[union-attr]


    return CommercialSourceCandidate(
        source_name=source_name,
        explicit_candidate_mpn=str(vendor_mpn).strip(),
        price_amount=price,
        currency_code=currency_val,
        availability=availability,
        quantity=quantity,
        price_basis=CommercialPriceBasis.LIST_PRICE,
        note_kind=note_kind,
    )


def _identify_and_map_source(source_section: dict[str, Any]) -> CommercialSourceCandidate | CommercialSourceIssue:
    """Identify which upstream source a section belongs to and map it.

    Uses structural heuristics based on field presence.
    Programming defects in mappers propagate (no broad exception catch).
    """
    # Identify source by sourceName field (bounded vocabulary only)
    source_name_raw = source_section.get("sourceName", "")

    if isinstance(source_name_raw, str):
        name_lower = source_name_raw.lower()
        if "ingram" in name_lower:
            return _map_ingram(source_section)
        elif "cdw" in name_lower:
            return _map_cdw(source_section)
        elif "synnex" in name_lower:
            return _map_synnex_eu(source_section)

    # Fallback: identify by field structure (allowlisted markers only)
    if "vendorPartNumber" in source_section:
        return _map_ingram(source_section)
    elif "manufacturerPartNumber" in source_section:
        return _map_cdw(source_section)
    elif "OnlineCheck" in source_section:
        return _map_synnex_eu(source_section)

    # Unknown source structure
    return CommercialSourceIssue(
        source_name="Unknown",
        outcome=SourceOutcome.MALFORMED_SECTION)



# ---------------------------------------------------------------------------
# Concrete adapter
# ---------------------------------------------------------------------------


class InternalVendorAdapter:
    """Concrete adapter for the internal Vendor API.

    Reads ``PI_VENDOR_LOOKUP_BASE_URL`` from the server environment.
    Performs at most ONE network call per lookup.
    """

    def __init__(self) -> None:
        """Initialize without reading configuration.

        Configuration is validated lazily on first lookup.
        """
        self._base_url: str | None = None
        self._validated = False

    def _ensure_configured(self) -> str:
        """Validate and return the configured base URL.

        Raises ValueError if not properly configured.
        """
        if self._validated:
            return self._base_url  # type: ignore[return-value]

        import os
        raw = os.environ.get("PI_VENDOR_LOOKUP_BASE_URL", "")
        self._base_url = _validate_base_url(raw)
        self._validated = True
        return self._base_url

    def lookup(self, query: CommercialLookupQuery) -> CommercialSourceResponse:
        """Execute one Vendor API lookup for the given MPN.

        Returns a CommercialSourceResponse with normalized observations.
        Network/transport failures produce a FAILED response.
        Programming errors propagate normally.
        """
        from datetime import datetime, timezone

        base_url = self._ensure_configured()
        lookup_url = _build_lookup_url(base_url, query.mpn)

        # Build the request
        req = Request(
            lookup_url,
            method="GET",
            headers={
                "Accept": "application/json",
                "User-Agent": "ProductIntelligenceVendorBot/0.1",
            },
        )

        # Execute the single network call (no retries)
        # Uses dedicated opener: no proxy, no redirect following
        opener = _get_vendor_opener()
        try:
            response = opener.open(req, timeout=_VENDOR_TIMEOUT)
        except (URLError, HTTPError, OSError, TimeoutError) as exc:
            # Bounded transport failures -> FAILED response
            # Log only bounded info (class name, MPN); never raw exception text
            logger.warning(
                "Vendor API lookup failed for MPN %s (class=%s)",
                query.mpn, type(exc).__name__,
            )
            return CommercialSourceResponse(
                status=LookupStatus.FAILED,
                retrieved_at=None,
            )

        # Read and bound response body
        try:
            body_bytes = response.read(_VENDOR_MAX_BODY + 1)
        except (URLError, OSError) as exc:
            logger.warning(
                "Vendor API response read failed for MPN %s (class=%s)",
                query.mpn, type(exc).__name__,
            )
            return CommercialSourceResponse(
                status=LookupStatus.FAILED,
                retrieved_at=None,
            )

        if len(body_bytes) > _VENDOR_MAX_BODY:
            logger.warning(
                "Vendor API response exceeded %d bytes for MPN %s",
                _VENDOR_MAX_BODY, query.mpn,
            )
            return CommercialSourceResponse(
                status=LookupStatus.FAILED,
                retrieved_at=None,
            )

        # Parse JSON with Decimal for exact monetary values.
        # parse_float=Decimal preserves precision; no binary float conversion.
        # parse_constant=_reject_json_constant rejects NaN/Infinity/-Infinity.
        try:
            body_text = body_bytes.decode("utf-8")
            payload = json.loads(
                body_text,
                parse_float=Decimal,
                parse_constant=_reject_json_constant,
            )
        except (
            json.JSONDecodeError,
            UnicodeDecodeError,
            _InvalidVendorJsonConstant,
        ) as exc:
            logger.warning(
                "Vendor API response JSON parse failed for MPN %s",
                query.mpn,
            )
            return CommercialSourceResponse(
                status=LookupStatus.FAILED,
                retrieved_at=None,
            )

        # Record retrieval time
        retrieved_at = datetime.now(timezone.utc)

        # Extract source sections
        if not isinstance(payload, dict):
            if isinstance(payload, list):
                source_sections = payload
            else:
                logger.warning(
                    "Vendor API response is unexpected type %s for MPN %s",
                    type(payload).__name__, query.mpn,
                )
                return CommercialSourceResponse(
                    status=LookupStatus.FAILED,
                    retrieved_at=retrieved_at,
                )
        else:
            source_sections = self._extract_source_sections(payload)

        # No source sections found
        if not source_sections:
            # Whole response with unrecognized shape -> FAILED
            return CommercialSourceResponse(
                status=LookupStatus.FAILED,
                retrieved_at=retrieved_at,
            )

        # Map each source section independently
        candidates: list[CommercialSourceCandidate] = []
        issues: list[CommercialSourceIssue] = []

        for section in source_sections:
            if not isinstance(section, dict):
                continue
            # Programming defects in mappers propagate — no broad catch
            result = _identify_and_map_source(section)
            if isinstance(result, CommercialSourceCandidate):
                candidates.append(result)
            elif isinstance(result, CommercialSourceIssue):
                issues.append(result)

        # Determine overall status
        if candidates:
            status = LookupStatus.SUCCESS if not issues else LookupStatus.PARTIAL
        elif issues:
            # All sources had issues (NOT_FOUND, MALFORMED, etc.)
            status = LookupStatus.PARTIAL if any(
                i.outcome == SourceOutcome.NOT_FOUND for i in issues
            ) else LookupStatus.FAILED
        else:
            status = LookupStatus.FAILED

        return CommercialSourceResponse(
            status=status,
            retrieved_at=retrieved_at,
            candidates=tuple(candidates),
            issues=tuple(issues),
        )

    def _extract_source_sections(self, payload: dict[str, Any]) -> list[dict[str, Any]]:
        """Extract individual source sections from the Vendor API response.

        The Vendor API returns a dict where top-level keys are source names
        (e.g. "Ingram", "CDW", "Synnex EU") and values are the source sections.

        For bounded known source names, the top-level key is used as a
        ``sourceName`` hint when the inner section lacks one. This is critical
        for wrapper shapes like:

            {"Ingram": {"Not Found": true}}

        where the inner dict has no ``sourceName`` but the wrapper key
        identifies the source. Arbitrary unknown wrapper names are NOT
        persisted — only bounded known names are injected.
        """
        sections: list[dict[str, Any]] = []

        for key, value in payload.items():
            if not isinstance(value, dict):
                continue

            # Check if this inner dict looks like a source section
            is_source_section = (
                "vendorPartNumber" in value
                or "manufacturerPartNumber" in value
                or "OnlineCheck" in value
                or "sourceName" in value
                or "NotFound" in value
                or "notFound" in value
                or "Not Found" in value
                or "notMaintained" in value
            )

            if is_source_section:
                section = dict(value)
                # If inner section lacks sourceName, inject from bounded
                # top-level wrapper key (only for known source names)
                if "sourceName" not in section and key in _ALLOWED_SOURCE_NAMES:
                    section["sourceName"] = key
                sections.append(section)

        return sections
