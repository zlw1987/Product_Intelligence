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
* no ambient proxy; explicit empty ProxyHandler({}) disables environment proxy routing
* URL-encode the canonical requested MPN
* GET only
* Response body: one of two bounded upstream contracts (Decimal-aware parse
  for monetary values in both):
  1. the canonical JSON wrapper document, or
  2. (PROD-FIX1; FU1; FU3; FU4) the exact production section-oriented
     body (``Ingram Product: { ... }`` / ``CDW Product: {Not Found}`` /
     ``Synnex EU Product: { ... }``) parsed by a strict bounded
     recursive-descent literal parser — no eval, no literal_eval,
     no generic HTML scraping. FU3: the observed production endpoint
     wraps each section line in an exact HTML paragraph opener, so each
     known label is additionally recognized in the exact
     ``<p>Ingram Product: ...`` form. The paragraph support is the
     observed literal only — optional leading whitespace + optional
     exact ``<p>`` + exact known label. It is NOT a generic HTML parser:
     no other tags, no attributes, no nesting, no tag stripping, no
     generic HTML unescaping. FU4 (exact entity literals corrected by
     FU4-FU1): the observed text/html transport additionally encodes
     three characters of the paragraph-form section value text with
     exact entity literals — ``&quot;`` (decoded as U+0022), the exact
     hexadecimal numeric LF entity formed by ``"&" + "#xA;"`` (decoded
     as LF U+000A), and the exact hexadecimal numeric CR entity formed
     by ``"&" + "#xD;"`` (decoded as CR U+000D); ONLY those three exact
     literals are decoded, and ONLY on the FU3 exact paragraph-envelope
     path (the retained plain-text form is never decoded) — still no
     html.unescape, no other named entity (the unsupported ``&nbsp;`` /
     ``&cr;`` spellings are NOT decoded), no other numeric entity,
     no case/format variant.
     FU4: the current real nested Synnex wire represents
     ``OnlineCheck.Item.AvailabilityTotal`` as a non-negative integer,
     observed as an ASCII decimal digit string; a narrow Synnex-
     specific reading accepts that exact string form on the REAL
     nested path only — the global ``_safe_int`` contract is unchanged
     and still rejects strings. The ACTUAL production Ingram placement is
     the hybrid form (explicit vendorPartNumber + nested pricing block +
     top-level boolean availability + top-level Avl_Quantity); the flat
     field forms remain supported as separately tested compatibility
     forms. Unknown/interstitial text between complete section literals
     is ignored (never parsed into data); malformed content INSIDE a
     section literal still fails that source closed.

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
import re
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


def _availability_flag_table(
    available: bool | None, quantity: int | None
) -> tuple[CommercialAvailability, int | None]:
    """Bounded availability truth table for sections publishing a flag.

    Contradiction or insufficient evidence => UNKNOWN (never fabricated).
    """
    if available is True:
        if quantity is None:
            return CommercialAvailability.IN_STOCK, None
        if quantity > 0:
            return CommercialAvailability.IN_STOCK, quantity
        return CommercialAvailability.UNKNOWN, quantity
    if available is False:
        if quantity is None:
            return CommercialAvailability.UNKNOWN, None
        if quantity == 0:
            return CommercialAvailability.OUT_OF_STOCK, quantity
        return CommercialAvailability.UNKNOWN, quantity
    # available is None
    if quantity is None:
        return CommercialAvailability.UNKNOWN, None
    if quantity > 0:
        return CommercialAvailability.IN_STOCK, quantity
    return CommercialAvailability.UNKNOWN, quantity


def _map_ingram(source_section: dict[str, Any]) -> CommercialSourceCandidate | CommercialSourceIssue:
    """Map one Ingram source section from the Vendor API response.

    Reads only approved fields. Bounded forms are supported:

    * Canonical JSON wrapper form:
      - pricing.customerPrice, pricing.retailPrice, pricing.currencyCode
      - availability.available, availability.Avl_Quantity
    * Production hybrid section form (FU1): the ACTUAL production wire
      placement observed for the requested part — explicit vendorPartNumber,
      nested ``pricing`` (customerPrice / retailPrice / currencyCode) PLUS a
      TOP-LEVEL boolean availability signal and a TOP-LEVEL Avl_Quantity.
      The canonical nested availability dict and the hybrid top-level
      placement are mutually exclusive readings of the same bounded fields;
      contradictions fail closed to UNKNOWN exactly like every other
      availability reading.
    * Flat production section form (PROD-FIX1 compatibility form):
      - customerPrice, retailPrice (fallback only), currency
      - quantity (and optional boolean available flag)

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
    if pricing is not None:
        # ---- Canonical JSON wrapper form ----
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

        # Availability (allowlisted fields only). Two bounded placements:
        #
        # * Canonical nested availability DICT:
        #   availability.available + availability.Avl_Quantity (unchanged).
        # * Production-observed hybrid placement (FU1): a TOP-LEVEL boolean
        #   availability signal + TOP-LEVEL Avl_Quantity next to the nested
        #   pricing block. The same bounded truth table applies: a
        #   contradiction (or a lone signal that cannot be cross-checked)
        #   fails closed to UNKNOWN; false + 0 => OUT_OF_STOCK; true +
        #   positive => IN_STOCK. Stock is never inferred from vendor
        #   reputation or unrelated fields.
        #
        # A non-dict `availability` value is the flag itself (the hybrid
        # placement), NOT a malformed nested dict: the bounded truth table
        # handles it exactly like the nested reading.
        availability_section = source_section.get("availability")
        if isinstance(availability_section, dict):
            available = _safe_bool(availability_section.get("available"))
            qty_raw = availability_section.get("Avl_Quantity")
            quantity = _safe_int(qty_raw)  # negative already rejected by _safe_int
            availability, quantity = _availability_flag_table(
                available, quantity
            )
        else:
            available = _safe_bool(availability_section)
            qty_raw = source_section.get("Avl_Quantity")
            quantity = _safe_int(qty_raw)  # negative already rejected by _safe_int
            availability, quantity = _availability_flag_table(
                available, quantity
            )

        return CommercialSourceCandidate(
            source_name=source_name,
            explicit_candidate_mpn=str(vendor_mpn).strip(),
            price_amount=price,
            currency_code=currency,
            availability=availability,
            quantity=quantity,
            price_basis=price_basis,
        )

    # ---- Flat production section form (PROD-FIX1) ----
    # Price: customerPrice primary (present => authoritative, no fallback);
    # retailPrice fallback only when customerPrice is absent.
    if "customerPrice" in source_section:
        price = _safe_decimal(source_section["customerPrice"])
        if price is None or not price.is_finite() or price < 0:
            return CommercialSourceIssue(
                source_name=source_name,
                outcome=SourceOutcome.MALFORMED_SECTION)
        price_basis = CommercialPriceBasis.CUSTOMER_PRICE
    elif "retailPrice" in source_section:
        price = _safe_decimal(source_section["retailPrice"])
        if price is None or not price.is_finite() or price < 0:
            return CommercialSourceIssue(
                source_name=source_name,
                outcome=SourceOutcome.MALFORMED_SECTION)
        price_basis = CommercialPriceBasis.RETAIL_PRICE_FALLBACK
    else:
        return CommercialSourceIssue(
            source_name=source_name,
            outcome=SourceOutcome.MALFORMED_SECTION)

    # Currency — flat field name: currency (must be str, nonempty)
    currency_raw = source_section.get("currency")
    if not isinstance(currency_raw, str) or not currency_raw.strip():
        return CommercialSourceIssue(
            source_name=source_name,
            outcome=SourceOutcome.MALFORMED_SECTION)
    currency = currency_raw.strip().upper()

    # Availability: optional boolean flag + quantity.
    # Without a published flag, quantity is the only stock signal:
    # > 0 => In Stock, 0 => Out of Stock, absent => Unknown (faithful).
    available = _safe_bool(source_section.get("available"))
    quantity = _safe_int(source_section.get("quantity"))
    if available is None:
        if quantity is None:
            availability = CommercialAvailability.UNKNOWN
        elif quantity > 0:
            availability = CommercialAvailability.IN_STOCK
        else:
            availability = CommercialAvailability.OUT_OF_STOCK
    else:
        availability, quantity = _availability_flag_table(available, quantity)

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

    Reads only approved fields. Two bounded forms are supported:

    * Canonical JSON wrapper form:
      - manufacturerPartNumber, price, currencyCode
      - inventoryStatus.stockStatus, inventoryStatus.Avl_Quantity
    * Flat production section form (PROD-FIX1):
      - manufacturerPartNumber, price, currency
      - stockStatus, quantity / Avl_Quantity (top level)

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


    # Currency — must be str and nonempty (canonical: currencyCode,
    # flat production form: currency)
    currency_raw = source_section.get("currencyCode")
    if currency_raw is None:
        currency_raw = source_section.get("currency")
    if not isinstance(currency_raw, str) or not currency_raw.strip():
        return CommercialSourceIssue(
            source_name=source_name,
            outcome=SourceOutcome.MALFORMED_SECTION)

    currency = currency_raw.strip().upper()

    # Availability
    inventory = source_section.get("inventoryStatus")
    flat_inventory = inventory is None
    if isinstance(inventory, dict):
        stock_status = inventory.get("stockStatus", "")
        qty_raw = inventory.get("Avl_Quantity")
    else:
        # Flat production form: top-level stockStatus + quantity /
        # Avl_Quantity. A non-dict inventoryStatus is ignored exactly as
        # before (treated as absent), never a programming error.
        stock_status = source_section.get("stockStatus", "")
        if not isinstance(stock_status, str):
            stock_status = ""
        qty_raw = source_section.get("Avl_Quantity")
        if qty_raw is None:
            qty_raw = source_section.get("quantity")

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
    elif flat_inventory:
        # Flat production form (PROD-FIX1) without a published stockStatus:
        # quantity is the only stock signal (faithful mapping).
        if quantity is None:
            availability = CommercialAvailability.UNKNOWN
        elif quantity > 0:
            availability = CommercialAvailability.IN_STOCK
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


# FU4: the current real nested Synnex wire represents
# OnlineCheck.Item.AvailabilityTotal as a non-negative integer, and the
# observed production value is the ASCII decimal digit STRING "0" (the
# observed UnitPriceAmount is likewise a numeric string, already
# supported by the existing _safe_decimal). The narrow Synnex-specific
# reading below accepts exactly that production-observed string form IN
# ADDITION to the existing _safe_int readings (non-negative int / finite
# integral Decimal). The GLOBAL _safe_int contract is UNCHANGED: it
# still rejects strings everywhere else (Ingram / CDW / flat Synnex /
# all other code paths).
_SYNNEX_AVAILABILITY_DIGITS_RE = re.compile(r"[0-9]{1,15}")


def _synnex_availability_total(value: Any) -> int | None:
    """Narrow Synnex-specific reading of the REAL nested wire field
    ``OnlineCheck.Item.AvailabilityTotal`` (FU4).

    Accepted:
    - non-negative int (exact type; bool rejected) — via _safe_int
    - finite integral, non-negative Decimal — via _safe_int
    - str: ASCII decimal digits only, non-negative, no sign, no decimal
      point, no exponent, no whitespace coercion, bounded to 15 digits
      ("0" -> 0, "1" -> 1, "12" -> 12)

    Rejected (returns None; the mapper then fails to UNKNOWN and never
    fabricates a stock state):
    - "-1" / "+1" / "1.0" / "1e2" / " 0 " / "" / "abc" / any non-digit
      character / over-bounded digit strings
    - bool, float, list, dict, None
    """
    if type(value) is str:
        if _SYNNEX_AVAILABILITY_DIGITS_RE.fullmatch(value) is None:
            return None
        return int(value)
    return _safe_int(value)


def _map_synnex_eu(source_section: dict[str, Any]) -> CommercialSourceCandidate | CommercialSourceIssue:
    """Map one Synnex EU source section from the Vendor API response.

    Reads only approved fields. Two bounded forms are supported:

    * Canonical JSON wrapper form:
      - OnlineCheck.Header.CurrencyCode
      - OnlineCheck.Item.ManufacturerItemIdentifier
      - OnlineCheck.Item.UnitPriceAmount
      - OnlineCheck.Item.AvailabilityTotal
      - OnlineCheck.Item.Note (bounded meanings only)
    * Flat production section form (PROD-FIX1):
      - ManufacturerItemIdentifier, UnitPriceAmount
      - currency / CurrencyCode, AvailabilityTotal, Note

    - documented not-found marker (NotFound, notFound, "Not Found")
    - documented not-maintained semantics

    Not-maintained detection (before normal fields):
    If the Note contains "not maintained" text, the result is NOT_FOUND
    with no candidate. All non-allowlisted fields (e.g. session/account/
    system identifiers) are ignored by construction.
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


    # Synnex EU uses OnlineCheck nesting (canonical form)
    online_check = source_section.get("OnlineCheck")
    if online_check is None:
        # ---- Flat production section form (PROD-FIX1) ----
        note_raw = source_section.get("Note")
        if isinstance(note_raw, str) and note_raw.strip():
            if "not maintained" in note_raw.strip().lower():
                # Not maintained in catalogue -> NOT_FOUND, no candidate
                return CommercialSourceIssue(
                    source_name=source_name,
                    outcome=SourceOutcome.NOT_FOUND)

        # Currency — flat field name: currency (canonical: CurrencyCode)
        currency_raw = source_section.get("currency")
        if currency_raw is None:
            currency_raw = source_section.get("CurrencyCode")
        if not isinstance(currency_raw, str) or not currency_raw.strip():
            return CommercialSourceIssue(
                source_name=source_name,
                outcome=SourceOutcome.MALFORMED_SECTION)
        currency_val = currency_raw.strip().upper()

        # Explicit MPN (required)
        vendor_mpn = source_section.get("ManufacturerItemIdentifier")
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
        price = _safe_decimal(source_section.get("UnitPriceAmount"))
        if price is None or not price.is_finite() or price < 0:
            return CommercialSourceIssue(
                source_name=source_name,
                outcome=SourceOutcome.MALFORMED_SECTION)

        # Availability: numeric AvailabilityTotal (> 0 In Stock, 0 Out of
        # Stock, missing/unparseable Unknown) — faithful to the flat form.
        avail_int = _safe_int(source_section.get("AvailabilityTotal"))
        if avail_int is not None and avail_int > 0:
            availability = CommercialAvailability.IN_STOCK
            quantity = avail_int
        elif avail_int is not None and avail_int == 0:
            availability = CommercialAvailability.OUT_OF_STOCK
            quantity = 0
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


    # Availability (FU4: the current real nested wire represents
    # AvailabilityTotal as a non-negative integer, sometimes as an ASCII
    # decimal digit string — narrow Synnex-specific reading; the global
    # _safe_int contract is unchanged).
    avail_raw = item.get("AvailabilityTotal")
    avail_int = _synnex_availability_total(avail_raw)
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
    elif "ManufacturerItemIdentifier" in source_section:
        # Flat production section form (PROD-FIX1): Synnex EU flat marker
        return _map_synnex_eu(source_section)

    # Unknown source structure
    return CommercialSourceIssue(
        source_name="Unknown",
        outcome=SourceOutcome.MALFORMED_SECTION)


# ---------------------------------------------------------------------------
# Section-oriented production response (PROD-FIX1)
# ---------------------------------------------------------------------------
#
# The production Vendor API answers HTTP 200 with
# ``Content-Type: text/html; charset=utf-8`` and a body that is NOT one JSON
# document. The body contains exactly three bounded section labels, one per
# known upstream source::
#
#     Ingram Product: { ... }
#     CDW Product: {Not Found}
#     Synnex EU Product: { ... }
#
# FU3: the observed production body wraps each section line in an exact
# HTML paragraph opener, i.e. the observed line form is::
#
#     <p>Ingram Product: { ... }</p>
#     <p>CDW Product: {Not Found}</p>
#     <p>Synnex EU Product: { ... }</p>
#
# (plus the retained plain line-anchored forms). The paragraph support is
# the EXACT literal "<p>" immediately before a known label — NOT a generic
# HTML parser: no other tags, no attributes, no nesting, no stripping,
# no generic unescaping, no DOM search. FU4 (exact entity literals
# corrected by FU4-FU1): the observed text/html transport encodes three
# characters of the paragraph-form section value text with exact entity
# literals (&quot; / the exact hex numeric LF entity "&" + "#xA;" /
# the exact hex numeric CR entity "&" + "#xD;"); ONLY those three exact
# literals are decoded on the paragraph path — still not a generic HTML
# unescape (the unsupported &nbsp; / &cr; spellings are NOT decoded) —
# and the retained plain-text form is never decoded.
#
# Each section value is either the exact bounded not-found marker
# ``{Not Found}`` or a bounded literal mapping whose fields are read by the
# SAME allowlist mappers used for the canonical JSON wrapper contract. The
# mapping is parsed by a strict recursive-descent parser below — no eval,
# no literal_eval, no code execution. Only the three exact labels are
# recognized; arbitrary section labels are never trusted as sections, and
# their content is never parsed into data or persisted (it is ignored
# interstitial text — FU1). The raw body is never logged or persisted.
#

# Exact production section labels (case-sensitive) -> bounded source name
_SECTION_HEADER_TO_SOURCE = (
    ("Ingram Product", "Ingram"),
    ("CDW Product", "CDW"),
    ("Synnex EU Product", "Synnex EU"),
)

# FU3: the exact observed production paragraph opener. Only this literal
# three-character sequence immediately before a known section label is
# recognized as the observed HTML paragraph-prefix form. Nothing broader:
# no other tag, no attributes, no nesting, no stripping, no unescaping.
_PARAGRAPH_PREFIX = "<p>"

# FU4 (exact entity literals corrected by FU4-FU1): the EXACT observed
# production paragraph-envelope entity literals.
# A production-safe read-only probe of the observed response (Content-
# Type: text/html; charset=utf-8) established the exact entity
# vocabulary inside the section values: Ingram — &quot; (166
# occurrences), the exact hexadecimal numeric LF entity formed by
# "&" + "#xA;", and the exact hexadecimal numeric CR entity formed by
# "&" + "#xD;"; CDW — none; Synnex EU — &quot; (154 occurrences).
# No other named entity (&apos; / &lsquo; / &rsquo; / &amp; / &lt; /
# &gt; / &nbsp; / &cr; / ...) and no OTHER numeric entity (decimal, or
# any other hex case/format spelling) was observed. After replacing
# EXACTLY these three literals — &quot; -> U+0022 (literal double
# quote), the LF entity -> U+000A (LF), the CR entity -> U+000D (CR)
# — no recognized HTML entity remained and the unchanged strict
# bounded literal parser succeeded. These three exact literals are the
# ONLY decodings (see _decode_paragraph_entities): no html.unescape,
# no generic entity table, no arbitrary entity regex, no case/format
# variant. The two approved hex numeric literals are exactly five
# characters each, verified character-by-character (visual-ambiguity
# guard):
#   LF entity: 0x26 '&'  0x23 '#'  0x78 'x'  0x41 'A'  0x3B ';'
#   CR entity: 0x26 '&'  0x23 '#'  0x78 'x'  0x44 'D'  0x3B ';'
# FU4-FU1: the earlier FU4 spelling "&nbsp;" / "&cr;" was an
# unsupported substitution for the two observed hex numeric entities;
# those spellings are NOT decoded here. Decoding applies ONLY on the
# FU3 exact paragraph-envelope path; the retained plain-text section
# form is never decoded.
assert "&#xA;" == "&" + "#xA;"
assert "&#xD;" == "&" + "#xD;"
assert [ord(c) for c in "&#xA;"] == [0x26, 0x23, 0x78, 0x41, 0x3B]
assert [ord(c) for c in "&#xD;"] == [0x26, 0x23, 0x78, 0x44, 0x3B]
_PARAGRAPH_ENTITY_LITERALS: tuple[tuple[str, str], ...] = (
    ("&quot;", '"'),
    ("&#xA;", "\n"),
    ("&#xD;", "\r"),
)


def _decode_paragraph_entities(text: str) -> str:
    """Apply ONLY the FU4 observed exact paragraph-envelope entity
    decodings (FU4-FU1: the exact observed literals) to one
    paragraph-form section value text.

    Exactly three bounded literal replacements (see
    ``_PARAGRAPH_ENTITY_LITERALS``): ``&quot;`` -> U+0022, the exact
    hexadecimal numeric LF entity (``"&" + "#xA;"``) -> U+000A (LF),
    the exact hexadecimal numeric CR entity (``"&" + "#xD;"``) ->
    U+000D (CR). Nothing broader is decoded — this is not
    html.unescape, not a generic entity table, and not a regex over
    arbitrary entities: no other named entity (the unsupported
    ``&nbsp;`` / ``&cr;`` spellings are NOT decoded), no other numeric
    entity (decimal, or any other hex case/format spelling), and no
    case/format variant of the two approved hex numeric entities. The
    DECODED values (``"`` / LF / CR) contain no ``&`` or ``;``
    characters, so the replacements cannot create new entity-like
    sequences (each ``str.replace`` pass is single-pass and never
    re-scans its own output). Unknown/unapproved entity forms are left
    untouched and remain fail-closed under the strict bounded literal
    grammar.
    """
    for literal, decoded in _PARAGRAPH_ENTITY_LITERALS:
        text = text.replace(literal, decoded)
    return text


# Bounded parse limits (external content must not recurse/expand unbounded)
_SECTION_MAX_DEPTH = 32
_SECTION_MAX_ENTRIES = 256

# Exact bounded not-found marker: { Not Found } (whitespace-tolerant).
# Matched as the BEGINNING of a section value (FU1): unknown interstitial
# text after the complete marker is ignored, exactly like trailing text
# after a complete mapping literal.
_SECTION_NOT_FOUND_RE = re.compile(r"\s*Not\s+Found\s*\}")


class _SectionValueParseError(ValueError):
    """One section value deviated from the bounded literal grammar.

    This is a bounded external-data failure (like a JSON decode error), not
    a programming defect. It is raised per-section so one malformed source
    cannot destroy independently valid siblings, and it never carries raw
    upstream content in its message.
    """


class _BoundedLiteralParser:
    """Strict recursive-descent parser for bounded upstream literals.

    Grammar (nothing else is accepted — no eval, no literal_eval, no code):

        value    := mapping | list | string | number | identifier
        mapping  := '{' [entry (',' entry)* [',']] '}'
        entry    := string ':' value
        list     := '[' [value (',' value)* [',']] ']'
        string   := (' | ") chars (' | ")   (escapes: backslash forms for
                     quote/backslash/newline/tab/CR/BS/FF and \\uXXXX hex)
        number   := ['-']? digits ['.' digits]   (finite Decimal, exact text)
        identifier := True | False | true | false | None | null

    * Numbers are parsed directly from the text token into ``Decimal`` —
      no binary float ever touches a value.
    * Mapping keys must be strings; duplicate keys are rejected.
    * Nesting depth and per-container entry counts are bounded.
    """

    _ESCAPES = {
        "n": "\n",
        "t": "\t",
        "r": "\r",
        "b": "\b",
        "f": "\f",
        "'": "'",
        '"': '"',
        "\\": "\\",
    }
    _IDENTIFIERS = {
        "True": True,
        "False": False,
        "true": True,
        "false": False,
        "None": None,
        "null": None,
    }

    def __init__(self, text: str, start: int = 0) -> None:
        self._text = text
        self._pos = start
        self._depth = 0

    # -- low-level cursor helpers -----------------------------------------

    def _peek(self) -> str:
        if self._pos >= len(self._text):
            return ""
        return self._text[self._pos]

    def _advance(self) -> str:
        ch = self._peek()
        if ch == "":
            raise _SectionValueParseError("unexpected end of section value")
        self._pos += 1
        return ch

    def _expect(self, expected: str) -> None:
        ch = self._advance()
        if ch != expected:
            raise _SectionValueParseError(
                f"expected {expected!r} in section value"
            )

    def _skip_ws(self) -> None:
        while self._pos < len(self._text) and self._text[self._pos].isspace():
            self._pos += 1

    # -- grammar ------------------------------------------------------------

    def parse_value(self):
        self._skip_ws()
        ch = self._peek()
        if ch == "":
            raise _SectionValueParseError("empty section value")
        if ch == "{":
            return self._parse_mapping()
        if ch == "[":
            return self._parse_list()
        if ch in ("'", '"'):
            return self._parse_string()
        if ch in "-0123456789.":
            return self._parse_number()
        return self._parse_identifier()

    def _parse_mapping(self) -> dict:
        if self._depth >= _SECTION_MAX_DEPTH:
            raise _SectionValueParseError("section literal too deep")
        self._depth += 1
        try:
            self._expect("{")
            result: dict = {}
            self._skip_ws()
            if self._peek() == "}":
                self._advance()
                return result
            while True:
                self._skip_ws()
                if self._peek() not in ("'", '"'):
                    raise _SectionValueParseError(
                        "mapping key must be a quoted string"
                    )
                key = self._parse_string()
                self._skip_ws()
                self._expect(":")
                value = self.parse_value()
                if key in result:
                    raise _SectionValueParseError("duplicate mapping key")
                result[key] = value
                if len(result) > _SECTION_MAX_ENTRIES:
                    raise _SectionValueParseError("too many mapping entries")
                self._skip_ws()
                ch = self._peek()
                if ch == ",":
                    self._advance()
                    self._skip_ws()
                    if self._peek() == "}":  # trailing comma tolerated
                        self._advance()
                        return result
                    continue
                if ch == "}":
                    self._advance()
                    return result
                raise _SectionValueParseError(
                    "expected ',' or '}' in mapping"
                )
        finally:
            self._depth -= 1

    def _parse_list(self) -> list:
        if self._depth >= _SECTION_MAX_DEPTH:
            raise _SectionValueParseError("section literal too deep")
        self._depth += 1
        try:
            self._expect("[")
            result: list = []
            self._skip_ws()
            if self._peek() == "]":
                self._advance()
                return result
            while True:
                value = self.parse_value()
                result.append(value)
                if len(result) > _SECTION_MAX_ENTRIES:
                    raise _SectionValueParseError("too many list entries")
                self._skip_ws()
                ch = self._peek()
                if ch == ",":
                    self._advance()
                    self._skip_ws()
                    if self._peek() == "]":  # trailing comma tolerated
                        self._advance()
                        return result
                    continue
                if ch == "]":
                    self._advance()
                    return result
                raise _SectionValueParseError(
                    "expected ',' or ']' in list"
                )
        finally:
            self._depth -= 1

    def _parse_string(self) -> str:
        quote = self._advance()
        out: list = []
        while True:
            if self._pos >= len(self._text):
                raise _SectionValueParseError("unterminated string")
            ch = self._text[self._pos]
            if ch == quote:
                self._pos += 1
                return "".join(out)
            if ch == "\\":
                self._pos += 1
                if self._pos >= len(self._text):
                    raise _SectionValueParseError("unterminated escape")
                esc = self._text[self._pos]
                if esc in self._ESCAPES:
                    out.append(self._ESCAPES[esc])
                    self._pos += 1
                elif esc == "u":
                    hexdigits = self._text[self._pos + 1:self._pos + 5]
                    if len(hexdigits) != 4 or not re.fullmatch(
                        r"[0-9a-fA-F]{4}", hexdigits
                    ):
                        raise _SectionValueParseError(
                            "invalid unicode escape"
                        )
                    out.append(chr(int(hexdigits, 16)))
                    self._pos += 5
                else:
                    raise _SectionValueParseError("invalid escape sequence")
            else:
                out.append(ch)
                self._pos += 1

    def _parse_number(self) -> Decimal:
        start = self._pos
        if self._peek() == "-":
            self._advance()
        saw_digit = False
        saw_dot = False
        while self._pos < len(self._text):
            ch = self._text[self._pos]
            if ch in "0123456789":
                saw_digit = True
                self._pos += 1
            elif ch == "." and not saw_dot:
                saw_dot = True
                self._pos += 1
            else:
                break
        if not saw_digit:
            raise _SectionValueParseError("malformed number literal")
        token = self._text[start:self._pos]
        try:
            value = Decimal(token)  # exact: parsed from text, never float
        except InvalidOperation:
            raise _SectionValueParseError("malformed number literal") from None
        if not value.is_finite():
            raise _SectionValueParseError("non-finite number literal")
        return value

    def _parse_identifier(self):
        start = self._pos
        while self._pos < len(self._text):
            ch = self._text[self._pos]
            if ch.isascii() and (ch.isalnum() or ch == "_"):
                self._pos += 1
            else:
                break
        word = self._text[start:self._pos]
        if word in self._IDENTIFIERS:
            return self._IDENTIFIERS[word]
        raise _SectionValueParseError("unrecognized literal token")


def _scan_section_oriented_body(body_text: str) -> list | None:
    """Scan a plain-text body for the exact production section labels.

    Returns a list of ``(source_name, value_text)`` in document order, or
    ``None`` when no recognized section label is present (the body is not
    the section-oriented production contract).

    Strictness:
    * Only the three exact labels are recognized (case-sensitive).
    * A label must start at the beginning of a line (leading whitespace
      tolerated) and be followed by ':' then whitespace or end-of-line.
    * FU3: each label is additionally recognized in the exact observed
      production paragraph-prefix form — an exact literal ``<p>``
      immediately before the label (leading whitespace before ``<p>``
      tolerated). The contract is exactly
      ``optional whitespace + optional exact "<p>" + exact bounded known
      label``. Nothing broader: no other tags (``<div>`` / ``<span>`` /
      ``<script>`` / ...), no attributes (``<p class=...>``), no nesting
      (``<p><span>``), no case variants, no text before ``<p>`` on the
      line, no HTML stripping or generic unescaping — this is NOT a
      generic HTML parser.
    * FU4 (exact entity literals corrected by FU4-FU1): the observed
      text/html transport encodes three characters of the
      paragraph-form section value text with exact entity literals;
      ONLY those three exact literals are decoded, and ONLY on this
      paragraph path: ``&quot;`` -> U+0022, the exact hexadecimal
      numeric LF entity (``"&" + "#xA;"``) -> U+000A (LF), the exact
      hexadecimal numeric CR entity (``"&" + "#xD;"``) -> U+000D (CR).
      No html.unescape, no other named entity (the unsupported
      ``&nbsp;`` / ``&cr;`` spellings are NOT decoded), no other
      numeric entity (decimal, or any other hex case/format spelling),
      no case/format variant — the retained plain-text section form is
      NEVER decoded. Unknown/unapproved entity forms are left raw and
      remain fail-closed under the strict bounded literal grammar (a
      bare entity token outside a string fails the parse; inside a
      string it is inert raw text, never interpreted).
    * A section's value text is the remainder of the header line plus all
      following lines up to the next recognized label line (or end of
      body). Unknown labels and interstitial lines inside that range are
      NOT sections and NOT data: the strict parser treats the complete
      bounded literal as authoritative and ignores anything after it
      (never parsed into data, never persisted — FU1), while malformed
      content INSIDE the literal still fails that section closed. A
      trailing observed ``</p>`` after a COMPLETE bounded literal is such
      ignored post-literal interstitial material (FU3); it cannot weaken
      malformed-in-literal rejection.
    * If a label repeats, only the first occurrence is used (deterministic).
    """
    lines = body_text.splitlines()
    found: list = []  # (line_idx, label, source, para_prefix_len)
    for idx, line in enumerate(lines):
        stripped = line.lstrip()
        para_len = 0
        head = stripped
        if stripped.startswith(_PARAGRAPH_PREFIX):
            # Exact observed paragraph-prefix form (FU3): the known label
            # must begin IMMEDIATELY after the exact "<p>" opener.
            para_len = len(_PARAGRAPH_PREFIX)
            head = stripped[para_len:]
        for label, source in _SECTION_HEADER_TO_SOURCE:
            if head.startswith(label + ":"):
                nxt = head[len(label) + 1:]
                if nxt == "" or nxt[0].isspace():
                    found.append((idx, label, source, para_len))
                    break
    if not found:
        return None
    sections: list = []
    seen_sources: set = set()
    for pos, (idx, label, source, para_len) in enumerate(found):
        if source in seen_sources:
            continue  # duplicate label: first occurrence wins
        seen_sources.add(source)
        end_idx = found[pos + 1][0] if pos + 1 < len(found) else len(lines)
        line = lines[idx]
        prefix_len = len(line) - len(line.lstrip())
        remainder = line[prefix_len + para_len + len(label) + 1:]
        value_text = "\n".join([remainder] + lines[idx + 1:end_idx])
        if para_len:
            # FU4: the observed transport entity encoding exists ONLY on
            # the exact paragraph-envelope path. The retained plain-text
            # form is never decoded.
            value_text = _decode_paragraph_entities(value_text)
        sections.append((source, value_text))
    return sections


def _parse_section_value(value_text: str) -> tuple:
    """Parse one section value strictly.

    Returns ``("not_found", None)`` for the exact bounded not-found form
    ``{Not Found}``, or ``("mapping", dict)`` for a strict bounded literal
    mapping. Raises ``_SectionValueParseError`` on any deviation from the
    bounded literal grammar itself.

    The value must BEGIN with the bounded literal (leading whitespace
    tolerated). Once the COMPLETE literal has parsed, any remaining text is
    unknown interstitial content between this section and the next
    recognized header: it is ignored — never parsed, never persisted,
    never data (FU1). It cannot alter the complete mapping and cannot
    poison the section; the scanner guarantees it contains no recognized
    section header. Malformed content INSIDE the literal (unterminated
    string, duplicate key, expression, code-looking token, non-literal
    value, ...) still fails that section closed.
    """
    text = value_text
    pos = 0
    while pos < len(text) and text[pos].isspace():
        pos += 1
    if pos >= len(text) or text[pos] != "{":
        raise _SectionValueParseError("section value must start with '{'")
    # Exact bounded not-found form: { Not Found } — the marker must begin
    # the value; unknown interstitial content after it is ignored.
    if _SECTION_NOT_FOUND_RE.match(text[pos + 1:]):
        return ("not_found", None)
    parser = _BoundedLiteralParser(text, start=pos)
    value = parser.parse_value()
    if not isinstance(value, dict):
        raise _SectionValueParseError("section value must be a mapping")
    # Trailing content after the complete bounded literal is unknown
    # interstitial text: ignored by contract (never data). The strict
    # grammar above already refused every malformed in-literal form.
    return ("mapping", value)


# Bounded source name -> allowlist mapper (defined above in this module)
_SECTION_SOURCE_TO_MAPPER = {
    "Ingram": _map_ingram,
    "CDW": _map_cdw,
    "Synnex EU": _map_synnex_eu,
}


def _parse_and_map_section(
    source_name: str, value_text: str
) -> CommercialSourceCandidate | CommercialSourceIssue:
    """Parse one bounded section value and map it through its source mapper.

    One malformed section yields a bounded MALFORMED_SECTION issue and does
    NOT destroy independently valid sibling sections. Programming defects in
    the mappers propagate (no broad exception catch).
    """
    try:
        kind, section = _parse_section_value(value_text)
    except _SectionValueParseError:
        logger.warning(
            "Vendor API section value failed bounded parsing for source %s",
            source_name,
        )
        return CommercialSourceIssue(
            source_name=source_name,
            outcome=SourceOutcome.MALFORMED_SECTION,
        )
    if kind == "not_found":
        return CommercialSourceIssue(
            source_name=source_name,
            outcome=SourceOutcome.NOT_FOUND,
        )
    mapper = _SECTION_SOURCE_TO_MAPPER[source_name]
    return mapper(section)


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

        # Parse the response body against the bounded upstream contracts.
        #
        # Contract 1 (canonical): one JSON document. Decimal-aware parse
        # (parse_float=Decimal preserves precision; no binary float
        # conversion). parse_constant=_reject_json_constant rejects
        # NaN/Infinity/-Infinity.
        #
        # Contract 2 (production, PROD-FIX1; FU3 paragraph envelope):
        # the real Vendor API answers
        # with Content-Type text/html and a body that is NOT one JSON
        # document — a section-oriented body with the three
        # exact bounded section labels (Ingram / CDW / Synnex EU), each
        # optionally preceded by the exact observed "<p>" paragraph
        # opener (FU3: narrow literal, not a generic HTML parser). When
        # contract 1 fails, the strict section parser is attempted before
        # the lookup is failed. The raw body is never logged or persisted.
        try:
            body_text = body_bytes.decode("utf-8")
        except UnicodeDecodeError:
            logger.warning(
                "Vendor API response is not valid UTF-8 for MPN %s",
                query.mpn,
            )
            return CommercialSourceResponse(
                status=LookupStatus.FAILED,
                retrieved_at=None,
            )

        json_parse_failed = False
        payload = None
        try:
            payload = json.loads(
                body_text,
                parse_float=Decimal,
                parse_constant=_reject_json_constant,
            )
        except (json.JSONDecodeError, _InvalidVendorJsonConstant):
            json_parse_failed = True

        if json_parse_failed:
            # -------- production section-oriented contract (PROD-FIX1) -----
            # The body is NOT one JSON document. Attempt the strict bounded
            # section parser before failing the lookup.
            return self._lookup_from_section_body(body_text, query.mpn)

        # ---------------- canonical JSON wrapper contract ----------------
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

    def _lookup_from_section_body(
        self, body_text: str, mpn: str
    ) -> CommercialSourceResponse:
        """Parse the production section-oriented body (PROD-FIX1; FU3).

        Strict bounded parsing only:
        * exactly three recognized section labels (never arbitrary labels)
        * FU3: each label is recognized in the existing plain
          line-anchored form and in the exact observed "<p>" paragraph-
          prefix form (nothing broader — not a generic HTML parser)
        * exact ``{Not Found}`` bounded not-found marker
        * strict recursive-descent literal grammar (no eval / literal_eval)
        * one malformed section yields a bounded issue and does NOT destroy
          independently valid sibling sections

        The raw body text is never logged or persisted; only normalized,
        allowlist-mapped observations reach the response.
        """
        sections = _scan_section_oriented_body(body_text)
        if sections is None:
            # Neither supported contract recognized -> FAILED.
            logger.warning(
                "Vendor API response matched no supported contract for MPN %s",
                mpn,
            )
            return CommercialSourceResponse(
                status=LookupStatus.FAILED,
                retrieved_at=None,
            )

        # Parse and map each section independently
        candidates: list[CommercialSourceCandidate] = []
        issues: list[CommercialSourceIssue] = []
        for source_name, value_text in sections:
            result = _parse_and_map_section(source_name, value_text)
            if isinstance(result, CommercialSourceCandidate):
                candidates.append(result)
            else:
                issues.append(result)

        # Record retrieval time (contract recognized and parsed)
        retrieved_at = datetime.now(timezone.utc)

        # Determine overall status (same bounded rules as the JSON contract)
        if candidates:
            status = (
                LookupStatus.SUCCESS if not issues else LookupStatus.PARTIAL
            )
        elif issues:
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
                or "ManufacturerItemIdentifier" in value  # PROD-FIX1 flat form
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
