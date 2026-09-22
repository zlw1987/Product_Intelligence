"""Vendor commercial price network access gate (PRODUCT-INTEL.4D-C-SEC).

SERVER-SIDE network access policy for Vendor commercial price visibility.

This module implements a fail-closed, CIDR-based access gate that determines
whether a given HTTP request originates from an approved corporate subnet.

Key invariants:
- PI_VENDOR_PRICE_ALLOWED_CIDRS absent or blank -> DENY (fail-closed)
- REMOTE_ADDR is the ONLY accepted client-address source
- Forwarded headers (X-Forwarded-For, X-Real-IP, etc.) are NEVER trusted
- Malformed CIDR configuration -> DENY (fail-closed)
- Noncanonical CIDR configuration (host bits set) -> DENY (fail-closed).
  Entries are parsed with strict=True: an entry such as 192.168.1.128/24
  is a configuration error, never silently normalized to 192.168.1.0/24,
  because normalization would broaden the authorization allowlist.
- No identity authority, pricing authority, or research logic changes

This is HTTP request authorization / presentation visibility policy.
It belongs at the web / presentation access boundary, NOT in research/,
providers/, or domain/.
"""

from __future__ import annotations

import ipaddress
import logging

logger = logging.getLogger(__name__)


class CommercialPriceAccessConfigurationError(Exception):
    """Raised when PI_VENDOR_PRICE_ALLOWED_CIDRS is syntactically malformed.

    The caller must treat this as DENY — malformed configuration must never
    silently broaden access.
    """


def _parse_allowed_cidrs(cidrs: str | None) -> tuple[ipaddress.IPv4Network | ipaddress.IPv6Network, ...]:
    """Parse a comma-separated CIDR string into a tuple of Networks.

    This is the pure parsing/evaluation portion, separately testable.

    Args:
        cidrs: Comma-separated CIDR notation strings (e.g. "10.0.0.0/8,192.168.1.0/24").
               May contain whitespace around entries. May be None or blank.

    Returns:
        Tuple of ipaddress.IPv4Network or ipaddress.IPv6Network objects.
        Empty tuple if cidrs is None, blank, or contains only empty entries.

    Raises:
        CommercialPriceAccessConfigurationError: If any non-empty entry is
            not a strict, canonical network. Fail-closed: a malformed or
            noncanonical entry (e.g. an IPv4/IPv6 network with host bits
            set) must never be silently normalized, because normalization
            would broaden the authorization allowlist.

    Network semantics (strict=True):
        - "10.0.0.0/8", "192.168.1.0/24", canonical IPv6 networks: valid.
        - "192.168.1.100/32", IPv6 "/128": valid exact host.
        - A bare IP without a prefix resolves to the /32 or /128 exact
          host network (narrower, not broader): valid.
        - "192.168.1.128/24", "10.1.2.3/8", or any entry with host bits
          set: configuration error.
    """
    if not cidrs or not cidrs.strip():
        return ()

    networks: list[ipaddress.IPv4Network | ipaddress.IPv6Network] = []

    for raw in cidrs.split(","):
        entry = raw.strip()
        if not entry:
            # Empty entries between commas are tolerated safely.
            continue

        try:
            # strict=True: the entry must already be a canonical network
            # address (or a bare IP, which resolves to /32 or /128).
            # Host bits set is rejected, never normalized, because
            # normalization would silently broaden the allowlist.
            network = ipaddress.ip_network(entry, strict=True)
        except ValueError as exc:
            raise CommercialPriceAccessConfigurationError(
                f"Malformed or noncanonical CIDR in vendor price access "
                f"configuration: {entry!r} ({exc}). Access denied."
            ) from exc

        networks.append(network)

    return tuple(networks)


def _resolve_client_address(request: "HttpRequest") -> str | None:
    """Extract the client address from the request.

    ONLY accepts REMOTE_ADDR. Does NOT trust any forwarded header.

    Args:
        request: Django HttpRequest instance.

    Returns:
        The REMOTE_ADDR value, or None if not present.
    """
    return request.META.get("REMOTE_ADDR")


def vendor_price_access_allowed(
    request: "HttpRequest",
    *,
    allowed_cidrs: str | None = None,
) -> bool:
    """Determine whether a request is allowed to view Vendor commercial prices.

    This is the primary entry point for the commercial price access gate.

    Decision table:
    1. No configured allowed CIDRs (None or blank) -> False
    2. Malformed or noncanonical (host bits set) CIDR configuration ->
       False (fail-closed, entire configuration rejected)
    3. Missing REMOTE_ADDR -> False
    4. Invalid/unparseable REMOTE_ADDR -> False
    5. Valid REMOTE_ADDR outside all configured networks -> False
    6. Valid REMOTE_ADDR inside at least one configured network -> True

    The function supports both IPv4 and IPv6 addresses and networks.

    Args:
        request: Django HttpRequest. The client address is read from
            request.META["REMOTE_ADDR"] ONLY. Forwarded headers are ignored.
        allowed_cidrs: Comma-separated CIDR notation string. If None, the
            Django setting PI_VENDOR_PRICE_ALLOWED_CIDRS is read.

    Returns:
        True if the request's REMOTE_ADDR falls within at least one allowed
        network. False otherwise (including configuration errors).
    """
    # Resolve the CIDR configuration.
    if allowed_cidrs is None:
        allowed_cidrs = _get_allowed_cidrs_from_settings()

    # Parse the allowed CIDRs. Fail-closed on configuration error.
    try:
        networks = _parse_allowed_cidrs(allowed_cidrs)
    except CommercialPriceAccessConfigurationError:
        logger.warning(
            "Vendor price access denied: malformed CIDR configuration."
        )
        return False

    # No configured networks -> deny (fail-closed default).
    if not networks:
        return False

    # Resolve client address from REMOTE_ADDR only.
    client_address = _resolve_client_address(request)

    if not client_address:
        return False

    # Parse the client address. Fail-closed on invalid address.
    try:
        client_ip = ipaddress.ip_address(client_address)
    except ValueError:
        logger.warning(
            "Vendor price access denied: invalid client address %r.",
            client_address,
        )
        return False

    # Check membership against all configured networks.
    for network in networks:
        if client_ip in network:
            return True

    return False


# Lazy import for type annotations only (avoid Django dependency at import time
# for the pure parsing function).
try:
    from django.conf import settings as _django_settings
    from django.http import HttpRequest  # noqa: F401
except ImportError:
    # Allow importing the module and using _parse_allowed_cidrs without Django.
    _django_settings = None  # type: ignore[assignment,misc]


def _get_allowed_cidrs_from_settings() -> str | None:
    """Read PI_VENDOR_PRICE_ALLOWED_CIDRS from Django settings.

    Returns None if settings is unavailable (no Django) or the setting
    is not configured.
    """
    if _django_settings is None:
        return None
    return getattr(_django_settings, "PI_VENDOR_PRICE_ALLOWED_CIDRS", None)
