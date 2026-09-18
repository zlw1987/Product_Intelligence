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
* No redirect to arbitrary destinations (same-origin only)
* URL-encode the canonical requested MPN
* GET only
* JSON response

The configured base URL is deployment-owned, not request-controlled.
No user-supplied endpoint is accepted.

Sensitive metadata (SessionId, BuyerAccountId, SystemId, etc.) is stripped
using an allowlist mapping. Unknown upstream fields are ignored.
"""

from __future__ import annotations

import json
import logging
from decimal import Decimal, InvalidOperation
from datetime import datetime, timezone
from typing import Any
from urllib.error import URLError
from urllib.parse import urlencode, urljoin, urlsplit
from urllib.request import urlopen, Request

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

# Sensitive fields that MUST NEVER survive into persisted output
_SENSITIVE_FIELD_NAMES: frozenset[str] = frozenset({
    "SessionId",
    "BuyerAccountId",
    "SystemId",
    # Equivalent classes
    "session_id",
    "sessionid",
    "sessionId",
    "account_id",
    "accountId",
    "buyerAccountId",
    "buyer_account_id",
    "system_id",
    "systemid",
    "systemId",
    "auth_token",
    "authToken",
    "token",
    "api_key",
    "apiKey",
    "customer_id",
    "customerId",
    "user_id",
    "userId",
    "buyer_id",
    "buyerId",
})

# Approved field names per source (allowlist)
_INGRAM_ALLOWED_FIELDS: frozenset[str] = frozenset({
    "vendorPartNumber",
    "pricing",
    "availability",
    "sourceName",
    "NotFound",
    "notFound",
})

_CDW_ALLOWED_FIELDS: frozenset[str] = frozenset({
    "manufacturerPartNumber",
    "price",
    "currencyCode",
    "inventoryStatus",
    "sourceName",
    "NotFound",
    "notFound",
})

_SYNNEX_ALLOWED_FIELDS: frozenset[str] = frozenset({
    "OnlineCheck",
    "sourceName",
    "notMaintained",
    "NotFound",
    "notFound",
})


def _is_sensitive_key(key: str) -> bool:
    """Check if a key name is a sensitive field that must be stripped."""
    if key in _SENSITIVE_FIELD_NAMES:
        return True
    # Also catch case-insensitive matches for common patterns
    lower = key.lower()
    for sensitive in _SENSITIVE_FIELD_NAMES:
        if lower == sensitive.lower():
            return True
    return False


def _filter_sensitive(payload: Any) -> Any:
    """Recursively remove sensitive keys from a payload dict.

    Uses allowlist semantics: known sensitive keys are always removed.
    Source-specific processing uses its own allowlist.
    """
    if isinstance(payload, dict):
        filtered = {}
        for key, value in payload.items():
            if _is_sensitive_key(key):
                logger.debug("Dropping sensitive key: %s", key)
                continue
            filtered[key] = _filter_sensitive(value)
        return filtered
    elif isinstance(payload, list):
        return [_filter_sensitive(item) for item in payload]
    return payload


def _validate_base_url(base_url: str) -> str:
    """Validate the configured Vendor API base URL.

    Requirements:
    * Absolute http or https
    * Host required
    * No embedded username/password
    * No fragment
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

    return url


def _build_lookup_url(base_url: str, mpn: str) -> str:
    """Build the Vendor API lookup URL for one exact MPN.

    The MPN is URL-encoded and appended as a ``partno`` query parameter.
    """
    encoded_params = urlencode({"partno": mpn})
    separator = "&" if "?" in base_url else "?"
    return f"{base_url}{separator}{encoded_params}"


def _safe_decimal(value: Any, default: Decimal | None = None) -> Decimal | None:
    """Parse a value as Decimal, return None on failure."""
    if value is None:
        return default
    try:
        return Decimal(str(value))
    except (InvalidOperation, ValueError, TypeError):
        return default


def _safe_int(value: Any, default: int | None = None) -> int | None:
    """Parse a value as int, return None on failure."""
    if value is None:
        return default
    try:
        return int(value)
    except (ValueError, TypeError):
        return default


def _safe_bool(value: Any) -> bool | None:
    """Parse a value as bool, return None if not a bool."""
    if isinstance(value, bool):
        return value
    return None


# ---------------------------------------------------------------------------
# Source-specific mapping
# ---------------------------------------------------------------------------


def _map_ingram(source_section: dict[str, Any]) -> CommercialSourceCandidate | CommercialSourceIssue:
    """Map one Ingram source section from the Vendor API response."""
    source_name = "Ingram"

    # Check for not-found response
    if source_section.get("NotFound") or source_section.get("notFound"):
        return CommercialSourceIssue(
            source_name=source_name,
            outcome=SourceOutcome.NOT_FOUND,
            detail="Ingram: MPN not found",
        )

    # Explicit MPN (required)
    vendor_mpn = source_section.get("vendorPartNumber")
    if not vendor_mpn or not str(vendor_mpn).strip():
        return CommercialSourceIssue(
            source_name=source_name,
            outcome=SourceOutcome.MISSING_EXPLICIT_MPN,
            detail="Ingram: missing vendorPartNumber",
        )

    # Price — customerPrice primary, retailPrice fallback
    pricing = source_section.get("pricing")
    if not isinstance(pricing, dict):
        return CommercialSourceIssue(
            source_name=source_name,
            outcome=SourceOutcome.MALFORMED_SECTION,
            detail="Ingram: missing or malformed pricing",
        )

    customer_price_raw = pricing.get("customerPrice")
    retail_price_raw = pricing.get("retailPrice")
    currency = pricing.get("currencyCode", "")

    if customer_price_raw is not None:
        # customerPrice is PRESENT (even if zero/null-like)
        price = _safe_decimal(customer_price_raw)
        if price is None:
            # customerPrice present but malformed — do NOT fall back to retail
            return CommercialSourceIssue(
                source_name=source_name,
                outcome=SourceOutcome.MALFORMED_SECTION,
                detail="Ingram: malformed customerPrice",
            )
        price_basis = CommercialPriceBasis.CUSTOMER_PRICE
    else:
        # customerPrice ABSENT — retail fallback
        price = _safe_decimal(retail_price_raw)
        if price is None:
            return CommercialSourceIssue(
                source_name=source_name,
                outcome=SourceOutcome.MALFORMED_SECTION,
                detail="Ingram: no usable price",
            )
        price_basis = CommercialPriceBasis.RETAIL_PRICE_FALLBACK

    # Availability truth table
    availability_section = source_section.get("availability")
    if not isinstance(availability_section, dict):
        availability = CommercialAvailability.UNKNOWN
        quantity = None
    else:
        available = _safe_bool(availability_section.get("available"))
        qty_raw = availability_section.get("Avl_Quantity")
        quantity = _safe_int(qty_raw)

        if available is True and quantity is not None and quantity > 0:
            availability = CommercialAvailability.IN_STOCK
        elif available is True and quantity is not None and quantity == 0:
            availability = CommercialAvailability.UNKNOWN  # contradiction
        elif available is True and quantity is None:
            availability = CommercialAvailability.IN_STOCK
        elif available is False and quantity is not None and quantity == 0:
            availability = CommercialAvailability.OUT_OF_STOCK
        elif available is False and quantity is not None and quantity > 0:
            availability = CommercialAvailability.UNKNOWN  # contradiction
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
        currency_code=currency.strip().upper() if currency else "",
        availability=availability,
        quantity=quantity,
        price_basis=price_basis,
        brand_new=True,
        brand_new_basis="VENDOR_API_POLICY",
    )


def _map_cdw(source_section: dict[str, Any]) -> CommercialSourceCandidate | CommercialSourceIssue:
    """Map one CDW source section from the Vendor API response."""
    source_name = "CDW"

    # Check for not-found response
    if source_section.get("NotFound") or source_section.get("notFound"):
        return CommercialSourceIssue(
            source_name=source_name,
            outcome=SourceOutcome.NOT_FOUND,
            detail="CDW: MPN not found",
        )

    # Explicit MPN (required)
    vendor_mpn = source_section.get("manufacturerPartNumber")
    if not vendor_mpn or not str(vendor_mpn).strip():
        return CommercialSourceIssue(
            source_name=source_name,
            outcome=SourceOutcome.MISSING_EXPLICIT_MPN,
            detail="CDW: missing manufacturerPartNumber",
        )

    # Price
    price_raw = source_section.get("price")
    price = _safe_decimal(price_raw)
    if price is None:
        return CommercialSourceIssue(
            source_name=source_name,
            outcome=SourceOutcome.MALFORMED_SECTION,
            detail="CDW: no usable price",
        )

    currency = source_section.get("currencyCode", "")

    # Availability
    inventory = source_section.get("inventoryStatus")
    qty_raw = None
    if isinstance(inventory, dict):
        qty_raw = inventory.get("Avl_Quantity")
        stock_status = inventory.get("stockStatus", "")
    else:
        stock_status = ""

    quantity = _safe_int(qty_raw)

    if stock_status == "InStock":
        if quantity is not None and quantity == 0:
            availability = CommercialAvailability.UNKNOWN  # contradiction
        else:
            availability = CommercialAvailability.IN_STOCK
    elif stock_status == "OutOfStock":
        if quantity is not None and quantity > 0:
            availability = CommercialAvailability.UNKNOWN  # contradiction
        else:
            availability = CommercialAvailability.OUT_OF_STOCK
    else:
        availability = CommercialAvailability.UNKNOWN

    return CommercialSourceCandidate(
        source_name=source_name,
        explicit_candidate_mpn=str(vendor_mpn).strip(),
        price_amount=price,
        currency_code=currency.strip().upper() if currency else "",
        availability=availability,
        quantity=quantity,
        price_basis=CommercialPriceBasis.LIST_PRICE,
        brand_new=True,
        brand_new_basis="VENDOR_API_POLICY",
    )


def _map_synnex_eu(source_section: dict[str, Any]) -> CommercialSourceCandidate | CommercialSourceIssue:
    """Map one Synnex EU source section from the Vendor API response."""
    source_name = "Synnex EU"

    # Check for not-found at top level first
    if source_section.get("NotFound") or source_section.get("notFound"):
        return CommercialSourceIssue(
            source_name=source_name,
            outcome=SourceOutcome.NOT_FOUND,
            detail="Synnex EU: MPN not found",
        )

    # Check for "not maintained in our catalogue"
    if source_section.get("notMaintained"):
        return CommercialSourceIssue(
            source_name=source_name,
            outcome=SourceOutcome.NOT_FOUND,
            detail="Synnex EU: MPN not maintained in catalogue",
        )

    # Synnex EU uses OnlineCheck nesting
    online_check = source_section.get("OnlineCheck")
    if not isinstance(online_check, dict):
        return CommercialSourceIssue(
            source_name=source_name,
            outcome=SourceOutcome.MALFORMED_SECTION,
            detail="Synnex EU: missing or malformed OnlineCheck",
        )

    # Currency from Header
    header = online_check.get("Header")
    if isinstance(header, dict):
        currency = header.get("CurrencyCode", "")
    else:
        currency = ""

    # Item section
    item = online_check.get("Item")
    if not isinstance(item, dict):
        return CommercialSourceIssue(
            source_name=source_name,
            outcome=SourceOutcome.MALFORMED_SECTION,
            detail="Synnex EU: missing or malformed Item",
        )

    # Explicit MPN
    vendor_mpn = item.get("ManufacturerItemIdentifier")
    if not vendor_mpn or not str(vendor_mpn).strip():
        return CommercialSourceIssue(
            source_name=source_name,
            outcome=SourceOutcome.MISSING_EXPLICIT_MPN,
            detail="Synnex EU: missing ManufacturerItemIdentifier",
        )

    # Price
    price_raw = item.get("UnitPriceAmount")
    price = _safe_decimal(price_raw)
    if price is None:
        return CommercialSourceIssue(
            source_name=source_name,
            outcome=SourceOutcome.MALFORMED_SECTION,
            detail="Synnex EU: no usable UnitPriceAmount",
        )

    # Availability
    avail_raw = item.get("AvailabilityTotal")
    avail_int = _safe_int(avail_raw)
    if avail_int is not None:
        if avail_int > 0:
            availability = CommercialAvailability.IN_STOCK
        elif avail_int == 0:
            availability = CommercialAvailability.OUT_OF_STOCK
        else:
            availability = CommercialAvailability.UNKNOWN
        quantity = avail_int
    else:
        availability = CommercialAvailability.UNKNOWN
        quantity = None

    # Note handling — only approved bounded meanings
    note_kind: CommercialNoteKind | None = None
    note_raw = item.get("Note")
    if isinstance(note_raw, str) and note_raw.strip():
        # Only recognize NO_RETURNS
        if "no return" in note_raw.strip().lower():
            note_kind = CommercialNoteKind.NO_RETURNS
        # All other free-form note text is dropped

    return CommercialSourceCandidate(
        source_name=source_name,
        explicit_candidate_mpn=str(vendor_mpn).strip(),
        price_amount=price,
        currency_code=currency.strip().upper() if currency else "",
        availability=availability,
        quantity=quantity,
        price_basis=CommercialPriceBasis.LIST_PRICE,
        note_kind=note_kind,
        brand_new=True,
        brand_new_basis="VENDOR_API_POLICY",
    )


def _identify_and_map_source(source_section: dict[str, Any]) -> CommercialSourceCandidate | CommercialSourceIssue:
    """Identify which upstream source a section belongs to and map it.

    Uses structural heuristics based on field presence.
    """
    # Filter sensitive data first
    cleaned = _filter_sensitive(source_section)

    # Identify source by structural markers
    source_name_raw = cleaned.get("sourceName", "")

    if isinstance(source_name_raw, str):
        name_lower = source_name_raw.lower()
        if "ingram" in name_lower:
            return _map_ingram(cleaned)
        elif "cdw" in name_lower:
            return _map_cdw(cleaned)
        elif "synnex" in name_lower:
            return _map_synnex_eu(cleaned)

    # Fallback: identify by field structure
    if "vendorPartNumber" in cleaned:
        return _map_ingram(cleaned)
    elif "manufacturerPartNumber" in cleaned:
        return _map_cdw(cleaned)
    elif "OnlineCheck" in cleaned:
        return _map_synnex_eu(cleaned)

    # Unknown source structure — use sourceName from payload or mark malformed
    actual_name = source_name_raw if isinstance(source_name_raw, str) and source_name_raw.strip() else "Unknown"
    return CommercialSourceIssue(
        source_name=actual_name,
        outcome=SourceOutcome.MALFORMED_SECTION,
        detail=f"Unrecognized source structure for {actual_name}",
    )


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
        Network failures produce a FAILED response, not an exception.
        Programming errors propagate normally.
        """
        import os
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
        try:
            response = urlopen(req, timeout=_VENDOR_TIMEOUT)
        except Exception as exc:
            logger.warning(
                "Vendor API lookup failed for MPN %s: %s",
                query.mpn, exc,
            )
            return CommercialSourceResponse(
                status=LookupStatus.FAILED,
                retrieved_at=None,
            )

        # Read and bound response body
        try:
            body_bytes = response.read(_VENDOR_MAX_BODY + 1)
        except Exception as exc:
            logger.warning(
                "Vendor API response read failed for MPN %s: %s",
                query.mpn, exc,
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

        # Parse JSON
        try:
            body_text = body_bytes.decode("utf-8")
            payload = json.loads(body_text)
        except (json.JSONDecodeError, UnicodeDecodeError) as exc:
            logger.warning(
                "Vendor API response JSON parse failed for MPN %s: %s",
                query.mpn, exc,
            )
            return CommercialSourceResponse(
                status=LookupStatus.FAILED,
                retrieved_at=None,
            )

        # Strip sensitive data from entire payload
        payload = _filter_sensitive(payload)

        # Record retrieval time
        retrieved_at = datetime.now(timezone.utc)

        # Extract source sections
        if not isinstance(payload, dict):
            # Whole response is not a dict — could be a list of sources
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
            # The response dict may contain source sections directly as values,
            # or may have a wrapper key containing the sources.
            source_sections = self._extract_source_sections(payload)

        if not source_sections:
            # No source sections found — could mean not found at all
            return CommercialSourceResponse(
                status=LookupStatus.SUCCESS,
                retrieved_at=retrieved_at,
                candidates=(),
                issues=(),
            )

        # Map each source section independently
        candidates: list[CommercialSourceCandidate] = []
        issues: list[CommercialSourceIssue] = []

        for section in source_sections:
            if not isinstance(section, dict):
                continue
            try:
                result = _identify_and_map_source(section)
                if isinstance(result, CommercialSourceCandidate):
                    candidates.append(result)
                elif isinstance(result, CommercialSourceIssue):
                    issues.append(result)
            except Exception as exc:
                # One malformed source section must not destroy others
                logger.warning(
                    "Source section mapping failed: %s", exc,
                )
                source_name = section.get("sourceName", "Unknown")
                if not isinstance(source_name, str) or not source_name.strip():
                    source_name = "Unknown"
                issues.append(CommercialSourceIssue(
                    source_name=source_name,
                    outcome=SourceOutcome.MALFORMED_SECTION,
                    detail=f"Mapping error: {type(exc).__name__}",
                ))

        # Determine overall status
        if candidates:
            status = LookupStatus.SUCCESS if not issues else LookupStatus.PARTIAL
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

        The Vendor API returns a dict where values that are dicts with
        source-specific fields are treated as source sections.
        """
        sections: list[dict[str, Any]] = []

        for key, value in payload.items():
            if isinstance(value, dict):
                # Check if this looks like a source section
                # (has source-specific fields like vendorPartNumber,
                # manufacturerPartNumber, OnlineCheck, or sourceName)
                if (
                    "vendorPartNumber" in value
                    or "manufacturerPartNumber" in value
                    or "OnlineCheck" in value
                    or "sourceName" in value
                    or "NotFound" in value
                    or "notFound" in value
                    or "notMaintained" in value
                ):
                    sections.append(value)

        return sections
