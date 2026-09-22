"""Tests for the vendor commercial price network access gate (PRODUCT-INTEL.4D-C-SEC).

This module tests product_intelligence.web.commercial_access:
- _parse_allowed_cidrs (pure parsing function)
- vendor_price_access_allowed (Django request integration)
- Fail-closed semantics on all error paths
- IPv4 and IPv6 support
- REMOTE_ADDR-only address resolution (no forwarded headers)
- Configuration error handling
"""

from __future__ import annotations

import ast
import ipaddress
import re
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from product_intelligence.web.commercial_access import (
    CommercialPriceAccessConfigurationError,
    _parse_allowed_cidrs,
    vendor_price_access_allowed,
)


def _live_boundary_boom(*args, **kwargs):
    """Sentinel for the zero-live-work test: any call to a live
    provider/network/semantic boundary during a historical report GET is a
    contract violation and must fail fast with RuntimeError.
    """
    raise RuntimeError(
        "live provider/network/semantic boundary touched during "
        "historical report GET — zero-live-work contract violated"
    )


# ============================================================================
# _parse_allowed_cidrs — pure parsing tests
# ============================================================================


class TestParseAllowedCidrs:
    """Test the pure CIDR parsing function."""

    # --- None / blank / empty input ---

    def test_none_input_returns_empty_tuple(self) -> None:
        assert _parse_allowed_cidrs(None) == ()

    def test_empty_string_returns_empty_tuple(self) -> None:
        assert _parse_allowed_cidrs("") == ()

    def test_whitespace_only_returns_empty_tuple(self) -> None:
        assert _parse_allowed_cidrs("   ") == ()

    def test_only_commas_returns_empty_tuple(self) -> None:
        """Commas with no real entries -> empty."""
        assert _parse_allowed_cidrs(",,,") == ()

    def test_commas_and_whitespace_returns_empty_tuple(self) -> None:
        assert _parse_allowed_cidrs(" , , ") == ()

    # --- Single valid CIDR ---

    def test_single_ipv4_cidr(self) -> None:
        result = _parse_allowed_cidrs("10.0.0.0/8")
        assert result == (ipaddress.IPv4Network("10.0.0.0/8"),)

    def test_single_ipv4_cidr_with_whitespace(self) -> None:
        result = _parse_allowed_cidrs("  10.0.0.0/8  ")
        assert result == (ipaddress.IPv4Network("10.0.0.0/8"),)

    def test_single_ipv6_cidr(self) -> None:
        result = _parse_allowed_cidrs("fd00::/8")
        assert result == (ipaddress.IPv6Network("fd00::/8"),)

    def test_single_ipv6_cidr_with_whitespace(self) -> None:
        result = _parse_allowed_cidrs("  fd00::/8  ")
        assert result == (ipaddress.IPv6Network("fd00::/8"),)

    def test_single_host_network(self) -> None:
        """A /32 host network is valid."""
        result = _parse_allowed_cidrs("192.168.1.1/32")
        assert result == (ipaddress.IPv4Network("192.168.1.1/32"),)

    def test_single_host_without_prefix(self) -> None:
        """A bare IP address without /prefix resolves to the /32 exact host.

        Under strict=True this is narrower, not broader: a bare IP has no
        host bits set, so it is accepted as the /32 (or /128) host network.
        """
        result = _parse_allowed_cidrs("10.1.2.3")
        assert result == (ipaddress.IPv4Network("10.1.2.3/32"),)

    # --- Multiple CIDRs ---

    def test_multiple_ipv4_cidrs(self) -> None:
        result = _parse_allowed_cidrs("10.0.0.0/8,192.168.1.0/24")
        assert len(result) == 2
        assert ipaddress.IPv4Network("10.0.0.0/8") in result
        assert ipaddress.IPv4Network("192.168.1.0/24") in result

    def test_mixed_ipv4_and_ipv6(self) -> None:
        result = _parse_allowed_cidrs("10.0.0.0/8,fd00::/8")
        assert len(result) == 2
        assert ipaddress.IPv4Network("10.0.0.0/8") in result
        assert ipaddress.IPv6Network("fd00::/8") in result

    def test_multiple_with_whitespace(self) -> None:
        result = _parse_allowed_cidrs(" 10.0.0.0/8 , 192.168.1.0/24 , 172.16.0.0/12 ")
        assert len(result) == 3
        assert ipaddress.IPv4Network("10.0.0.0/8") in result
        assert ipaddress.IPv4Network("192.168.1.0/24") in result
        assert ipaddress.IPv4Network("172.16.0.0/12") in result

    def test_trailing_comma_tolerated(self) -> None:
        """Trailing comma produces an empty entry which is ignored."""
        result = _parse_allowed_cidrs("10.0.0.0/8,")
        assert len(result) == 1
        assert result == (ipaddress.IPv4Network("10.0.0.0/8"),)

    def test_leading_comma_tolerated(self) -> None:
        result = _parse_allowed_cidrs(",10.0.0.0/8")
        assert len(result) == 1

    def test_multiple_consecutive_commas_tolerated(self) -> None:
        result = _parse_allowed_cidrs("10.0.0.0/8,,192.168.1.0/24")
        assert len(result) == 2

    # --- Malformed CIDR -> raises ConfigurationError ---

    def test_malformed_cidr_raises(self) -> None:
        with pytest.raises(CommercialPriceAccessConfigurationError):
            _parse_allowed_cidrs("not-a-cidr")

    def test_partial_cidr_raises(self) -> None:
        with pytest.raises(CommercialPriceAccessConfigurationError):
            _parse_allowed_cidrs("10.0.0")

    def test_invalid_prefix_length_raises(self) -> None:
        with pytest.raises(CommercialPriceAccessConfigurationError):
            _parse_allowed_cidrs("10.0.0.0/33")

    def test_non_numeric_cidr_raises(self) -> None:
        with pytest.raises(CommercialPriceAccessConfigurationError):
            _parse_allowed_cidrs("10.0.0.0/abc")

    def test_negative_prefix_raises(self) -> None:
        with pytest.raises(CommercialPriceAccessConfigurationError):
            _parse_allowed_cidrs("10.0.0.0/-1")

    def test_one_valid_one_malformed_raises(self) -> None:
        """Even one malformed entry fails the whole config (fail-closed)."""
        with pytest.raises(CommercialPriceAccessConfigurationError):
            _parse_allowed_cidrs("10.0.0.0/8,garbage")

    def test_malformed_ipv6_raises(self) -> None:
        with pytest.raises(CommercialPriceAccessConfigurationError):
            _parse_allowed_cidrs("not::valid::cidr::gggg/129")

    def test_configuration_error_message_contains_malformed_value(self) -> None:
        """Error message should identify the problematic CIDR."""
        with pytest.raises(
            CommercialPriceAccessConfigurationError, match="not-a-cidr"
        ):
            _parse_allowed_cidrs("not-a-cidr")

    def test_configuration_error_is_chained_from_value_error(self) -> None:
        """The ConfigurationError should chain from the original ValueError."""
        with pytest.raises(CommercialPriceAccessConfigurationError) as info:
            _parse_allowed_cidrs("bad")
        assert info.value.__cause__ is not None

    # --- Return type ---

    def test_returns_tuple_not_list(self) -> None:
        """Return type is tuple for immutability."""
        result = _parse_allowed_cidrs("10.0.0.0/8")
        assert type(result) is tuple

    # --- strict=True network semantics (fail-closed configuration) ---
    #
    # An authorization allowlist must never silently broaden: an entry with
    # host bits set is a configuration error, not a network to normalize.

    def test_ipv4_host_bit_cidr_rejected(self) -> None:
        """192.168.1.128/24 has host bits set: must be rejected.

        strict=False would silently normalize it to 192.168.1.0/24,
        broadening authorization. The parser must fail closed instead.
        """
        with pytest.raises(
            CommercialPriceAccessConfigurationError, match="192.168.1.128/24"
        ):
            _parse_allowed_cidrs("192.168.1.128/24")

    def test_ipv4_broadening_prefix_with_host_bits_rejected(self) -> None:
        """10.1.2.3/8 would normalize to 10.0.0.0/8 — a massive broadening.

        Must be a configuration error, never silently widened.
        """
        with pytest.raises(
            CommercialPriceAccessConfigurationError, match="10.1.2.3/8"
        ):
            _parse_allowed_cidrs("10.1.2.3/8")

    def test_ipv6_host_bit_cidr_rejected(self) -> None:
        """An IPv6 network with host bits set must be rejected.

        2001:db8::1/32 has host bits set within the /32 prefix; it must not
        be normalized to 2001:db8::/32.
        """
        with pytest.raises(
            CommercialPriceAccessConfigurationError, match="2001:db8::1/32"
        ):
            _parse_allowed_cidrs("2001:db8::1/32")

    def test_ipv6_canonical_network_accepted(self) -> None:
        """A canonical IPv6 network (no host bits set) is valid."""
        result = _parse_allowed_cidrs("2001:db8::/32")
        assert result == (ipaddress.IPv6Network("2001:db8::/32"),)

    def test_ipv6_exact_host_network_accepted(self) -> None:
        """An IPv6 /128 exact host is valid."""
        result = _parse_allowed_cidrs("2001:db8::abcd/128")
        assert result == (ipaddress.IPv6Network("2001:db8::abcd/128"),)

    def test_ipv4_canonical_networks_and_hosts_accepted(self) -> None:
        """Canonical IPv4 networks and exact hosts remain valid."""
        for cidr in ("10.0.0.0/8", "192.168.1.0/24", "192.168.1.100/32"):
            result = _parse_allowed_cidrs(cidr)
            assert result == (ipaddress.ip_network(cidr),)


# ============================================================================
# vendor_price_access_allowed — Django request integration
# ============================================================================


class TestVendorPriceAccessAllowed:
    """Test the full Django-request-aware access gate."""

    # --- No configured CIDRs -> deny (fail-closed default) ---

    def test_no_cidrs_configured_denies(self) -> None:
        """When allowed_cidrs is None and settings has no value -> False."""
        request = MagicMock()
        request.META = {"REMOTE_ADDR": "10.0.0.1"}
        # Explicitly pass None to bypass any settings value.
        # With Django settings defaulting to None, this denies.
        assert vendor_price_access_allowed(request, allowed_cidrs=None) is False

    def test_no_cidrs_denies_even_trusted_ip(self) -> None:
        """No configured CIDRs denies even an obviously private IP."""
        request = MagicMock()
        request.META = {"REMOTE_ADDR": "10.0.0.1"}
        # Pass empty string to simulate no config
        assert vendor_price_access_allowed(request, allowed_cidrs="") is False

    def test_no_cidrs_denies_with_allowed_cidrs_none(self) -> None:
        """Explicit allowed_cidrs=None means settings will be checked.
        If settings has no value, deny."""
        from unittest.mock import patch

        request = MagicMock()
        request.META = {"REMOTE_ADDR": "10.0.0.1"}
        # Mock settings to have no PI_VENDOR_PRICE_ALLOWED_CIDRS
        mock_settings = MagicMock()
        mock_settings.PI_VENDOR_PRICE_ALLOWED_CIDRS = None

        with patch(
            "product_intelligence.web.commercial_access._django_settings",
            mock_settings,
        ):
            assert vendor_price_access_allowed(request) is False

    # --- Missing REMOTE_ADDR -> deny ---

    def test_missing_remote_addr_denies(self) -> None:
        request = MagicMock()
        request.META = {}
        assert vendor_price_access_allowed(
            request, allowed_cidrs="10.0.0.0/8"
        ) is False

    def test_empty_remote_addr_denies(self) -> None:
        request = MagicMock()
        request.META = {"REMOTE_ADDR": ""}
        assert vendor_price_access_allowed(
            request, allowed_cidrs="10.0.0.0/8"
        ) is False

    def test_none_remote_addr_denies(self) -> None:
        request = MagicMock()
        request.META = {"REMOTE_ADDR": None}
        assert vendor_price_access_allowed(
            request, allowed_cidrs="10.0.0.0/8"
        ) is False

    # --- Invalid REMOTE_ADDR -> deny ---

    def test_invalid_remote_addr_denies(self) -> None:
        request = MagicMock()
        request.META = {"REMOTE_ADDR": "not-an-ip"}
        assert vendor_price_access_allowed(
            request, allowed_cidrs="10.0.0.0/8"
        ) is False

    def test_empty_string_remote_addr_denies(self) -> None:
        request = MagicMock()
        request.META = {"REMOTE_ADDR": "   "}
        assert vendor_price_access_allowed(
            request, allowed_cidrs="10.0.0.0/8"
        ) is False

    # --- IPv4: allowed ---

    def test_ipv4_inside_network_allowed(self) -> None:
        request = MagicMock()
        request.META = {"REMOTE_ADDR": "10.1.2.3"}
        assert vendor_price_access_allowed(
            request, allowed_cidrs="10.0.0.0/8"
        ) is True

    def test_ipv4_network_boundary_allowed(self) -> None:
        """IP at the edge of the network is included."""
        request = MagicMock()
        request.META = {"REMOTE_ADDR": "10.255.255.255"}
        assert vendor_price_access_allowed(
            request, allowed_cidrs="10.0.0.0/8"
        ) is True

    def test_ipv4_exact_host_network_allowed(self) -> None:
        request = MagicMock()
        request.META = {"REMOTE_ADDR": "192.168.1.100"}
        assert vendor_price_access_allowed(
            request, allowed_cidrs="192.168.1.100/32"
        ) is True

    def test_ipv4_in_multiple_networks_any_match(self) -> None:
        """IP in at least one of several networks -> allowed."""
        request = MagicMock()
        request.META = {"REMOTE_ADDR": "10.5.6.7"}
        assert vendor_price_access_allowed(
            request, allowed_cidrs="192.168.1.0/24,10.0.0.0/8,172.16.0.0/12"
        ) is True

    # --- IPv4: denied ---

    def test_ipv4_outside_network_denied(self) -> None:
        request = MagicMock()
        request.META = {"REMOTE_ADDR": "203.0.113.1"}
        assert vendor_price_access_allowed(
            request, allowed_cidrs="10.0.0.0/8"
        ) is False

    def test_ipv4_in_no_network_denied(self) -> None:
        request = MagicMock()
        request.META = {"REMOTE_ADDR": "8.8.8.8"}
        assert vendor_price_access_allowed(
            request, allowed_cidrs="10.0.0.0/8,192.168.1.0/24"
        ) is False

    def test_ipv4_single_bit_off_denied(self) -> None:
        """10.0.0.0/8 does NOT include 11.0.0.1."""
        request = MagicMock()
        request.META = {"REMOTE_ADDR": "11.0.0.1"}
        assert vendor_price_access_allowed(
            request, allowed_cidrs="10.0.0.0/8"
        ) is False

    # --- IPv6: allowed ---

    def test_ipv6_inside_network_allowed(self) -> None:
        request = MagicMock()
        request.META = {"REMOTE_ADDR": "fd00::1"}
        assert vendor_price_access_allowed(
            request, allowed_cidrs="fd00::/8"
        ) is True

    def test_ipv6_full_address_allowed(self) -> None:
        request = MagicMock()
        request.META = {"REMOTE_ADDR": "2001:db8::1"}
        assert vendor_price_access_allowed(
            request, allowed_cidrs="2001:db8::/32"
        ) is True

    def test_ipv6_exact_host_network_allowed(self) -> None:
        request = MagicMock()
        request.META = {"REMOTE_ADDR": "2001:db8::1"}
        assert vendor_price_access_allowed(
            request, allowed_cidrs="2001:db8::1/128"
        ) is True

    # --- IPv6: denied ---

    def test_ipv6_outside_network_denied(self) -> None:
        request = MagicMock()
        request.META = {"REMOTE_ADDR": "2001:db9::1"}
        assert vendor_price_access_allowed(
            request, allowed_cidrs="2001:db8::/32"
        ) is False

    def test_ipv4_ip_against_ipv6_network_denied(self) -> None:
        """An IPv4 address does not match an IPv6 network."""
        request = MagicMock()
        request.META = {"REMOTE_ADDR": "10.0.0.1"}
        assert vendor_price_access_allowed(
            request, allowed_cidrs="fd00::/8"
        ) is False

    def test_ipv6_ip_against_ipv4_network_denied(self) -> None:
        """An IPv6 address does not match an IPv4 network."""
        request = MagicMock()
        request.META = {"REMOTE_ADDR": "fd00::1"}
        assert vendor_price_access_allowed(
            request, allowed_cidrs="10.0.0.0/8"
        ) is False

    # --- Mixed IPv4/IPv6 networks ---

    def test_mixed_networks_ipv4_match(self) -> None:
        request = MagicMock()
        request.META = {"REMOTE_ADDR": "10.0.0.1"}
        assert vendor_price_access_allowed(
            request, allowed_cidrs="fd00::/8,10.0.0.0/8"
        ) is True

    def test_mixed_networks_ipv6_match(self) -> None:
        request = MagicMock()
        request.META = {"REMOTE_ADDR": "fd00::1"}
        assert vendor_price_access_allowed(
            request, allowed_cidrs="10.0.0.0/8,fd00::/8"
        ) is True

    def test_mixed_networks_no_match(self) -> None:
        request = MagicMock()
        request.META = {"REMOTE_ADDR": "203.0.113.1"}
        assert vendor_price_access_allowed(
            request, allowed_cidrs="10.0.0.0/8,fd00::/8"
        ) is False

    # --- Forwarded headers must NOT be trusted ---

    def test_x_forwarded_for_not_trusted(self) -> None:
        """X-Forwarded-For must not override REMOTE_ADDR."""
        request = MagicMock()
        request.META = {
            "REMOTE_ADDR": "203.0.113.1",  # Untrusted public IP
            "HTTP_X_FORWARDED_FOR": "10.0.0.1",  # Would be trusted if checked
        }
        assert vendor_price_access_allowed(
            request, allowed_cidrs="10.0.0.0/8"
        ) is False

    def test_x_real_ip_not_trusted(self) -> None:
        """X-Real-IP must not override REMOTE_ADDR."""
        request = MagicMock()
        request.META = {
            "REMOTE_ADDR": "203.0.113.1",
            "HTTP_X_REAL_IP": "10.0.0.1",
        }
        assert vendor_price_access_allowed(
            request, allowed_cidrs="10.0.0.0/8"
        ) is False

    def test_x_forwarded_for_multiple_not_trusted(self) -> None:
        """Even a chain of X-Forwarded-For addresses is ignored."""
        request = MagicMock()
        request.META = {
            "REMOTE_ADDR": "203.0.113.1",
            "HTTP_X_FORWARDED_FOR": "10.0.0.1, 192.168.1.1, 172.16.0.1",
        }
        assert vendor_price_access_allowed(
            request, allowed_cidrs="10.0.0.0/8,192.168.1.0/24,172.16.0.0/12"
        ) is False

    def test_forwarded_header_not_trusted(self) -> None:
        """RFC 7239 Forwarded header must not be trusted."""
        request = MagicMock()
        request.META = {
            "REMOTE_ADDR": "203.0.113.1",
            "HTTP_FORWARDED": "for=10.0.0.1",
        }
        assert vendor_price_access_allowed(
            request, allowed_cidrs="10.0.0.0/8"
        ) is False

    def test_x_forwarded_for_trusted_when_remote_addr_also_trusted(self) -> None:
        """When REMOTE_ADDR itself is trusted, forwarded headers don't matter."""
        request = MagicMock()
        request.META = {
            "REMOTE_ADDR": "10.0.0.1",
            "HTTP_X_FORWARDED_FOR": "8.8.8.8",
        }
        assert vendor_price_access_allowed(
            request, allowed_cidrs="10.0.0.0/8"
        ) is True

    # --- REMOTE_ADDR is the ONLY source ---

    def test_only_remote_addr_considered(self) -> None:
        """Only REMOTE_ADDR matters; all other headers ignored."""
        request = MagicMock()
        request.META = {
            "REMOTE_ADDR": "10.0.0.1",
            "HTTP_X_FORWARDED_FOR": "8.8.8.8",
            "HTTP_X_REAL_IP": "8.8.8.8",
            "HTTP_FORWARDED": "for=8.8.8.8",
        }
        assert vendor_price_access_allowed(
            request, allowed_cidrs="10.0.0.0/8"
        ) is True
        # The decision came from REMOTE_ADDR alone

    def test_no_remote_addr_with_forwarded_headers_denies(self) -> None:
        """No REMOTE_ADDR + forwarded headers -> deny."""
        request = MagicMock()
        request.META = {
            "HTTP_X_FORWARDED_FOR": "10.0.0.1",
            "HTTP_X_REAL_IP": "10.0.0.1",
        }
        assert vendor_price_access_allowed(
            request, allowed_cidrs="10.0.0.0/8"
        ) is False

    # --- Malformed CIDR configuration -> deny (fail-closed) ---

    def test_malformed_cidr_denies_access(self) -> None:
        """Malformed CIDR in config -> deny rather than allow all."""
        request = MagicMock()
        request.META = {"REMOTE_ADDR": "10.0.0.1"}
        assert vendor_price_access_allowed(
            request, allowed_cidrs="not-valid-cidr"
        ) is False

    def test_malformed_cidr_does_not_allow_anyone(self) -> None:
        """Even a suspiciously well-placed IP is denied on bad config."""
        request = MagicMock()
        request.META = {"REMOTE_ADDR": "192.168.1.1"}
        assert vendor_price_access_allowed(
            request, allowed_cidrs="garbage,bad,invalid"
        ) is False

    def test_mixed_valid_and_malformed_cidr_denies(self) -> None:
        """One valid + one malformed entry -> deny all (fail-closed)."""
        request = MagicMock()
        request.META = {"REMOTE_ADDR": "10.0.0.1"}
        assert vendor_price_access_allowed(
            request, allowed_cidrs="10.0.0.0/8,not-valid"
        ) is False

    # --- Noncanonical (host bits set) CIDR configuration -> DENY ---
    #
    # CommercialPriceAccessConfigurationError on any entry means the ENTIRE
    # configuration is rejected and every client address is denied.
    # No noncanonical network may be auto-widened at the public gate.

    def test_host_bit_cidr_configuration_denies_access(self) -> None:
        """192.168.1.128/24 is noncanonical: the whole config is rejected.

        A REMOTE_ADDR inside the would-be-normalized 192.168.1.0/24 must
        still be denied.
        """
        request = MagicMock()
        request.META = {"REMOTE_ADDR": "192.168.1.5"}
        assert vendor_price_access_allowed(
            request, allowed_cidrs="192.168.1.128/24"
        ) is False

    def test_host_bit_cidr_does_not_broaden_authorized_range(self) -> None:
        """An IP in the normalized network of a rejected entry is denied.

        Proves the gate did not silently widen 192.168.1.128/24 to
        192.168.1.0/24.
        """
        request = MagicMock()
        request.META = {"REMOTE_ADDR": "192.168.1.200"}
        assert vendor_price_access_allowed(
            request, allowed_cidrs="192.168.1.128/24"
        ) is False

    def test_broadening_prefix_configuration_denies_all(self) -> None:
        """10.1.2.3/8 must not be widened to 10.0.0.0/8.

        Even a REMOTE_ADDR inside 10.0.0.0/8 is denied because the entry
        is noncanonical and the entire configuration fails closed.
        """
        request = MagicMock()
        request.META = {"REMOTE_ADDR": "10.0.0.1"}
        assert vendor_price_access_allowed(
            request, allowed_cidrs="10.1.2.3/8"
        ) is False

    def test_host_bit_ipv6_cidr_configuration_denies_access(self) -> None:
        """An IPv6 entry with host bits set rejects the whole config."""
        request = MagicMock()
        request.META = {"REMOTE_ADDR": "2001:db8::5"}
        assert vendor_price_access_allowed(
            request, allowed_cidrs="2001:db8::1/32"
        ) is False

    def test_mixed_valid_and_noncanonical_cidr_denies(self) -> None:
        """One valid + one noncanonical (host bits set) entry -> deny all.

        The valid 10.0.0.0/8 must not survive alongside a rejected
        entry: the entire configuration fails closed.
        """
        request = MagicMock()
        request.META = {"REMOTE_ADDR": "10.0.0.1"}
        assert vendor_price_access_allowed(
            request, allowed_cidrs="10.0.0.0/8,192.168.1.128/24"
        ) is False

    # --- Django settings integration ---

    def test_reads_from_django_settings(self) -> None:
        """When allowed_cidrs is not provided, read from Django settings."""
        from unittest.mock import patch

        request = MagicMock()
        request.META = {"REMOTE_ADDR": "192.168.50.50"}

        mock_settings = MagicMock()
        mock_settings.PI_VENDOR_PRICE_ALLOWED_CIDRS = "192.168.50.0/24"

        with patch(
            "product_intelligence.web.commercial_access._django_settings",
            mock_settings,
        ):
            assert vendor_price_access_allowed(request) is True

    def test_settings_absent_denies(self) -> None:
        """When Django setting is absent (no attribute), deny."""
        from unittest.mock import patch

        request = MagicMock()
        request.META = {"REMOTE_ADDR": "10.0.0.1"}

        class NoSetting:
            pass

        with patch(
            "product_intelligence.web.commercial_access._django_settings",
            NoSetting(),
        ):
            assert vendor_price_access_allowed(request) is False

    def test_settings_blank_string_denies(self) -> None:
        """When Django setting is blank, deny."""
        from unittest.mock import patch

        request = MagicMock()
        request.META = {"REMOTE_ADDR": "10.0.0.1"}

        mock_settings = MagicMock()
        mock_settings.PI_VENDOR_PRICE_ALLOWED_CIDRS = ""

        with patch(
            "product_intelligence.web.commercial_access._django_settings",
            mock_settings,
        ):
            assert vendor_price_access_allowed(request) is False

    def test_explicit_cidrs_overrides_settings(self) -> None:
        """Explicit allowed_cidrs parameter takes priority over settings."""
        from unittest.mock import patch

        request = MagicMock()
        request.META = {"REMOTE_ADDR": "172.16.0.1"}

        mock_settings = MagicMock()
        mock_settings.PI_VENDOR_PRICE_ALLOWED_CIDRS = "10.0.0.0/8"

        with patch(
            "product_intelligence.web.commercial_access._django_settings",
            mock_settings,
        ):
            # Settings says 10.0.0.0/8, but explicit param says 172.16.0.0/12
            assert (
                vendor_price_access_allowed(
                    request, allowed_cidrs="172.16.0.0/12"
                )
                is True
            )

    # --- Example deployment value from spec ---

    def test_example_deployment_value(self) -> None:
        """The example deployment CIDRs from the spec work correctly."""
        cidrs = "10.0.0.0/8,192.168.50.0/24,172.16.8.0/21"

        # Allowed IPs
        for addr in ("10.1.2.3", "192.168.50.100", "172.16.8.1", "172.16.15.255"):
            request = MagicMock()
            request.META = {"REMOTE_ADDR": addr}
            assert vendor_price_access_allowed(
                request, allowed_cidrs=cidrs
            ), f"{addr} should be allowed"

        # Denied IPs
        for addr in ("203.0.113.1", "192.168.51.1", "172.16.16.0", "8.8.8.8"):
            request = MagicMock()
            request.META = {"REMOTE_ADDR": addr}
            assert not vendor_price_access_allowed(
                request, allowed_cidrs=cidrs
            ), f"{addr} should be denied"

    # --- Whitespace tolerance in CIDR strings ---

    def test_whitespace_around_cidrs(self) -> None:
        request = MagicMock()
        request.META = {"REMOTE_ADDR": "10.0.0.1"}
        assert vendor_price_access_allowed(
            request, allowed_cidrs="  10.0.0.0/8  "
        ) is True

    def test_whitespace_between_cidrs(self) -> None:
        request = MagicMock()
        request.META = {"REMOTE_ADDR": "10.0.0.1"}
        assert vendor_price_access_allowed(
            request, allowed_cidrs=" 10.0.0.0/8 , 192.168.1.0/24 "
        ) is True


# ============================================================================
# Module-level invariants
# ============================================================================


class TestModuleInvariants:
    """Test module-level architectural invariants."""

    def test_module_imports_without_django_models(self) -> None:
        """The module must not define any Django models."""
        import product_intelligence.web.commercial_access as mod

        assert not hasattr(mod, "models")

    def test_configuration_error_is_exception(self) -> None:
        """CommercialPriceAccessConfigurationError must be a proper Exception."""
        assert issubclass(
            CommercialPriceAccessConfigurationError, Exception
        )

    def test_parse_allowed_cidrs_is_pure(self) -> None:
        """_parse_allowed_cidrs must not depend on Django at all.
        It should work with pure Python inputs only."""
        # This test exercises the function without any Django setup
        result = _parse_allowed_cidrs("10.0.0.0/8,192.168.1.0/24")
        assert len(result) == 2
        assert ipaddress.IPv4Network("10.0.0.0/8") in result

    # Detector helpers for the hardcoded-network guard. The guard's goal:
    # production executable configuration must not contain a hardcoded
    # allowed customer network. Docstrings/comments may carry documentation
    # examples; executable string constants (assignments, defaults, return
    # values, call arguments) may not.

    _IPV4_NETWORK_RE = re.compile(
        r"(?<![\d.])\d{1,3}(?:\.\d{1,3}){3}/\d{1,2}(?!\d)"
    )
    _IPV6_NETWORK_RE = re.compile(
        r"(?i)(?:[0-9a-f]{0,4}:){1,7}[0-9a-f]{0,4}/\d{1,3}(?!\d)"
    )

    @staticmethod
    def _executable_string_constants(
        tree: ast.AST,
    ) -> list[tuple[int, str]]:
        """Collect (lineno, value) of string constants in executable code.

        Docstrings — the first statement of a module, class, or function
        body — are excluded, so documentation examples do not trip the
        guard. Every other string constant (assignments, defaults,
        returns, call arguments, f-string static parts) is executable
        configuration surface.
        """
        docstring_ids: set[int] = set()
        for node in ast.walk(tree):
            if isinstance(
                node,
                (ast.Module, ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef),
            ):
                body = node.body
                if (
                    body
                    and isinstance(body[0], ast.Expr)
                    and isinstance(body[0].value, ast.Constant)
                    and isinstance(body[0].value.value, str)
                ):
                    docstring_ids.add(id(body[0].value))

        found: list[tuple[int, str]] = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Constant) and isinstance(node.value, str):
                if id(node) in docstring_ids:
                    continue
                found.append((node.lineno, node.value))
        return found

    @classmethod
    def _contains_network_literal(cls, value: str) -> bool:
        """True if value contains an IPv4 or IPv6 network literal."""
        return (
            cls._IPV4_NETWORK_RE.search(value) is not None
            or cls._IPV6_NETWORK_RE.search(value) is not None
        )

    def _guarded_source_files(self) -> tuple[Path, Path]:
        """The production files where a hardcoded allowed network could live:
        the access-gate module and the Django settings default.
        """
        import product_intelligence.web.commercial_access as mod

        gate = Path(mod.__file__).resolve()
        settings = gate.parents[2] / "config" / "settings.py"
        return gate, settings

    def test_no_hardcoded_cidrs_in_source(self) -> None:
        """No executable production code may hardcode an allowed customer
        network.

        The allowed CIDR list belongs in the server environment
        (PI_VENDOR_PRICE_ALLOWED_CIDRS). Documentation examples in
        docstrings or comments are permitted; any executable string
        constant containing a network literal is a regression.
        """
        for path in self._guarded_source_files():
            tree = ast.parse(path.read_text(encoding="utf-8"))
            for lineno, value in self._executable_string_constants(tree):
                assert not self._contains_network_literal(value), (
                    f"{path}:{lineno} hardcodes a network literal in "
                    f"executable code: {value!r}. Allowed customer "
                    "networks must come from the "
                    "PI_VENDOR_PRICE_ALLOWED_CIDRS environment, never "
                    "from source."
                )

    def test_hardcoded_cidr_detector_controls(self) -> None:
        """Non-vacuity proof for the hardcoded-network detector.

        The detector must actually catch executable network literals
        (positive controls) and must not flag documentation examples
        (negative controls). If a positive control fails, the guard is
        vacuous; if a negative control fails, the guard is broken.
        """

        def detects(source: str) -> bool:
            tree = ast.parse(source)
            return any(
                self._contains_network_literal(value)
                for _, value in self._executable_string_constants(tree)
            )

        # Positive controls: executable literals are detected.
        assert detects('DEFAULT = "10.0.0.0/8"')
        assert detects('def f():\n    return "192.168.50.0/24"')
        assert detects('ALLOWED = "fd00::/8,2001:db8::/32"')
        assert detects('x = "192.168.1.128/24"')

        # Negative controls: docstring examples are NOT flagged.
        assert not detects(
            'def f():\n    """Example: 10.0.0.0/8,192.168.50.0/24."""\n'
            "    return None"
        )
        assert not detects('"""Module example: fd00::/8"""')

        # Negative control: unrelated executable strings are NOT flagged.
        assert not detects('SETTING = "PI_VENDOR_PRICE_ALLOWED_CIDRS"')

    def test_remote_addr_only_in_source(self) -> None:
        """The module must reference REMOTE_ADDR and NOT forwarded headers."""
        import product_intelligence.web.commercial_access as mod
        source = open(mod.__file__).read()

        assert "REMOTE_ADDR" in source

        # These must not be used as client address sources
        # (they may appear in comments/docstrings)
        code_lines = []
        in_docstring = False
        for line in source.split("\n"):
            stripped = line.strip()
            if stripped.startswith('"""') or stripped.startswith("'''"):
                in_docstring = not in_docstring
                continue
            if not in_docstring:
                code_lines.append(line)

        code_text = "\n".join(code_lines)
        # The function must NOT use any forwarded header
        assert "X_FORWARDED_FOR" not in code_text
        assert "X_REAL_IP" not in code_text
        assert "HTTP_FORWARDED" not in code_text


# ============================================================================
# Cross-cutting: architecture guard
# ============================================================================


class TestCommercialAccessLocation:
    """Verify the module lives in the correct layer."""

    def test_module_is_in_web_package(self) -> None:
        """commercial_access must be in the web/ package, not research/ or domain/."""
        import product_intelligence.web.commercial_access as mod
        assert "product_intelligence.web" in mod.__name__

    def test_module_does_not_import_research(self) -> None:
        """The access gate must not import research/ layer."""
        import ast
        import product_intelligence.web.commercial_access as mod

        source = open(mod.__file__).read()
        tree = ast.parse(source)
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom) and node.module:
                assert not node.module.startswith(
                    "product_intelligence.research"
                ), (
                    f"commercial_access imports {node.module}; "
                    "access gate must not import research/"
                )
            if isinstance(node, ast.Import):
                for alias in node.names:
                    assert not alias.name.startswith(
                        "product_intelligence.research"
                    )

    def test_module_does_not_import_domain(self) -> None:
        """The access gate must not import domain/ layer."""
        import ast
        import product_intelligence.web.commercial_access as mod

        source = open(mod.__file__).read()
        tree = ast.parse(source)
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom) and node.module:
                assert not node.module.startswith(
                    "product_intelligence.domain"
                )
            if isinstance(node, ast.Import):
                for alias in node.names:
                    assert not alias.name.startswith(
                        "product_intelligence.domain"
                    )

    def test_module_does_not_import_providers(self) -> None:
        """The access gate must not import providers/ layer."""
        import ast
        import product_intelligence.web.commercial_access as mod

        source = open(mod.__file__).read()
        tree = ast.parse(source)
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom) and node.module:
                assert not node.module.startswith(
                    "product_intelligence.providers"
                )
            if isinstance(node, ast.Import):
                for alias in node.names:
                    assert not alias.name.startswith(
                        "product_intelligence.providers"
                    )

    def test_module_does_not_import_runs(self) -> None:
        """The access gate must not import runs/ persistence layer."""
        import ast
        import product_intelligence.web.commercial_access as mod

        source = open(mod.__file__).read()
        tree = ast.parse(source)
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom) and node.module:
                assert not node.module.startswith(
                    "product_intelligence.runs"
                )
            if isinstance(node, ast.Import):
                for alias in node.names:
                    assert not alias.name.startswith(
                        "product_intelligence.runs"
                    )


# ============================================================================
# BLOCKER 2 — Real web-path tests (Django test client)
# ============================================================================


class TestResearchDetailAccessIntegration:
    """Exercise the access gate through the actual GET /research/<uuid> view.

    Uses Django's test client with REMOTE_ADDR keyword argument to control
    the client address.  The session-scoped django_test_database fixture
    from conftest.py provides the database.
    """

    def _create_run_with_supplement(
        self,
        *,
        mpn: str = "SENTINEL-MPN-001",
        description: str = "Sentinel test product",
        vendor_price: "Decimal" = None,
    ) -> "ResearchRun":
        """Create a ResearchRun with a ResearchSupplementSnapshot containing
        a vendor commercial observation.

        The snapshot uses a sentinel price (Decimal('91827.43')) that is
        highly unlikely to appear in ordinary test data. This enables
        binary-search leak detection.
        """
        from datetime import datetime, timezone
        from decimal import Decimal

        from product_intelligence.domain import ResearchRequest
        from product_intelligence.research.commercial_supplement_codec import (
            ResearchSupplementResult,
            SupplementAvailability,
            SupplementLookupStatus,
            SupplementPriceBasis,
            SupplementSourceObservation,
            VendorCommercialResult,
            encode_research_supplement_result,
        )
        from product_intelligence.runs.models import (
            ResearchRun,
            ResearchSupplementSnapshot,
        )

        if vendor_price is None:
            vendor_price = Decimal("91827.43")

        run = ResearchRun.objects.create_from_request(
            ResearchRequest(
                manufacturer_part_number=mpn,
                description=description,
            ),
        )

        result = ResearchSupplementResult(
            vendor_commercial_result=VendorCommercialResult(
                lookup_status=SupplementLookupStatus.SUCCESS,
                retrieved_at=datetime(2025, 1, 15, 12, 0, 0, tzinfo=timezone.utc),
                observations=(
                    SupplementSourceObservation(
                        source_name="INTERNAL_VENDOR",
                        explicit_candidate_mpn=mpn,
                        vendor_mpn_match_type="EXACT",
                        price_amount=vendor_price,
                        currency_code="USD",
                        availability=SupplementAvailability.IN_STOCK,
                        price_basis=SupplementPriceBasis.CUSTOMER_PRICE,
                        quantity=None,
                        note_kind=None,
                        brand_new=True,
                        brand_new_basis="VENDOR_API_POLICY",
                    ),
                ),
                source_issues=(),
            ),
        )

        payload = encode_research_supplement_result(result)
        ResearchSupplementSnapshot.objects.create(
            run=run,
            schema_version=1,
            payload=payload,
        )

        return run

    def test_allowed_remote_addr_context_access_true(self) -> None:
        "BLOCKER 2.1: allowed REMOTE_ADDR -> context vendor_commercial_access_allowed=True."
        from unittest.mock import patch
        from django.test import Client
        from django.urls import reverse

        run = self._create_run_with_supplement()
        url = reverse("research-detail", kwargs={"run_id": run.id})

        mock_settings = type("Settings", (), {
            "PI_VENDOR_PRICE_ALLOWED_CIDRS": "10.0.0.0/8"
        })()

        with patch(
            "product_intelligence.web.commercial_access._django_settings",
            mock_settings,
        ):
            client = Client()
            response = client.get(url, REMOTE_ADDR="10.0.0.1")

            assert response.status_code == 200
            context = response.context
            assert context is not None
            assert context["vendor_commercial_access_allowed"] is True

    def test_denied_remote_addr_context_access_false(self) -> None:
        "BLOCKER 2.2: denied REMOTE_ADDR -> context vendor_commercial_access_allowed=False."
        from unittest.mock import patch
        from django.test import Client
        from django.urls import reverse

        run = self._create_run_with_supplement()
        url = reverse("research-detail", kwargs={"run_id": run.id})

        mock_settings = type("Settings", (), {
            "PI_VENDOR_PRICE_ALLOWED_CIDRS": "10.0.0.0/8"
        })()

        with patch(
            "product_intelligence.web.commercial_access._django_settings",
            mock_settings,
        ):
            client = Client()
            # 192.0.2.0/24 is TEST-NET-1 (RFC 5737) - never assigned to anyone
            response = client.get(url, REMOTE_ADDR="192.0.2.100")

            assert response.status_code == 200
            context = response.context
            assert context is not None
            assert context["vendor_commercial_access_allowed"] is False

    def test_absent_configuration_context_access_false(self) -> None:
        "BLOCKER 2.3: absent PI_VENDOR_PRICE_ALLOWED_CIDRS -> access=False (fail-closed)."
        from unittest.mock import patch
        from django.test import Client
        from django.urls import reverse

        run = self._create_run_with_supplement()
        url = reverse("research-detail", kwargs={"run_id": run.id})

        mock_settings = type("Settings", (), {
            "PI_VENDOR_PRICE_ALLOWED_CIDRS": None
        })()

        with patch(
            "product_intelligence.web.commercial_access._django_settings",
            mock_settings,
        ):
            client = Client()
            response = client.get(url, REMOTE_ADDR="10.0.0.1")

            assert response.status_code == 200
            context = response.context
            assert context is not None
            assert context["vendor_commercial_access_allowed"] is False

    def test_denied_remote_with_spoofed_forwarded_for_access_false(self) -> None:
        "BLOCKER 2.4: denied REMOTE_ADDR + spoofed X-Forwarded-For -> access=False."
        from unittest.mock import patch
        from django.test import Client
        from django.urls import reverse

        run = self._create_run_with_supplement()
        url = reverse("research-detail", kwargs={"run_id": run.id})

        mock_settings = type("Settings", (), {
            "PI_VENDOR_PRICE_ALLOWED_CIDRS": "10.0.0.0/8"
        })()

        with patch(
            "product_intelligence.web.commercial_access._django_settings",
            mock_settings,
        ):
            client = Client()
            # REMOTE_ADDR is 203.0.113.1 (TEST-NET-3, RFC 5737) - denied
            # X-Forwarded-For claims to be 10.0.0.1 - must NOT be trusted
            response = client.get(
                url,
                REMOTE_ADDR="203.0.113.1",
                HTTP_X_FORWARDED_FOR="10.0.0.1",
            )

            assert response.status_code == 200
            context = response.context
            assert context is not None
            assert context["vendor_commercial_access_allowed"] is False

    def test_denied_remote_with_spoofed_x_real_ip_access_false(self) -> None:
        "BLOCKER 2.5: denied REMOTE_ADDR + spoofed X-Real-IP -> access=False."
        from unittest.mock import patch
        from django.test import Client
        from django.urls import reverse

        run = self._create_run_with_supplement()
        url = reverse("research-detail", kwargs={"run_id": run.id})

        mock_settings = type("Settings", (), {
            "PI_VENDOR_PRICE_ALLOWED_CIDRS": "10.0.0.0/8"
        })()

        with patch(
            "product_intelligence.web.commercial_access._django_settings",
            mock_settings,
        ):
            client = Client()
            response = client.get(
                url,
                REMOTE_ADDR="203.0.113.1",
                HTTP_X_REAL_IP="10.0.0.1",
            )

            assert response.status_code == 200
            context = response.context
            assert context is not None
            assert context["vendor_commercial_access_allowed"] is False

    def test_allowed_remote_with_unrelated_forwarded_headers_remains_allowed(self) -> None:
        "BLOCKER 2.6: allowed REMOTE_ADDR with malicious forwarded headers -> still allowed."
        from unittest.mock import patch
        from django.test import Client
        from django.urls import reverse

        run = self._create_run_with_supplement()
        url = reverse("research-detail", kwargs={"run_id": run.id})

        mock_settings = type("Settings", (), {
            "PI_VENDOR_PRICE_ALLOWED_CIDRS": "10.0.0.0/8"
        })()

        with patch(
            "product_intelligence.web.commercial_access._django_settings",
            mock_settings,
        ):
            client = Client()
            response = client.get(
                url,
                REMOTE_ADDR="10.0.0.1",
                HTTP_X_FORWARDED_FOR="203.0.113.1, 8.8.8.8",
                HTTP_X_REAL_IP="203.0.113.1",
                HTTP_FORWARDED="for=203.0.113.1",
            )

            assert response.status_code == 200
            context = response.context
            assert context is not None
            assert context["vendor_commercial_access_allowed"] is True

    def test_query_parameter_cannot_authorize(self) -> None:
        "BLOCKER 2.7: query parameters have no effect on authorization."
        from unittest.mock import patch
        from django.test import Client
        from django.urls import reverse

        run = self._create_run_with_supplement()

        mock_settings = type("Settings", (), {
            "PI_VENDOR_PRICE_ALLOWED_CIDRS": "10.0.0.0/8"
        })()

        with patch(
            "product_intelligence.web.commercial_access._django_settings",
            mock_settings,
        ):
            client = Client()
            # REMOTE_ADDR is denied, query params must not override
            for flag in ("trusted=1", "internal=1", "vendor_access=1", "admin=1"):
                url = reverse("research-detail", kwargs={"run_id": run.id})
                response = client.get(f"{url}?{flag}", REMOTE_ADDR="192.0.2.1")
                assert response.status_code == 200
                context = response.context
                assert context is not None
                assert context["vendor_commercial_access_allowed"] is False, (
                    f"Query flag {flag!r} must not authorize access"
                )

    def test_cookies_cannot_authorize(self) -> None:
        "BLOCKER 2.8: cookies with access-like values have no effect."
        from unittest.mock import patch
        from django.test import Client
        from django.urls import reverse

        run = self._create_run_with_supplement()
        url = reverse("research-detail", kwargs={"run_id": run.id})

        mock_settings = type("Settings", (), {
            "PI_VENDOR_PRICE_ALLOWED_CIDRS": "10.0.0.0/8"
        })()

        with patch(
            "product_intelligence.web.commercial_access._django_settings",
            mock_settings,
        ):
            client = Client()
            response = client.get(
                url,
                REMOTE_ADDR="192.0.2.1",
                HTTP_COOKIE="vendor_access=true; internal_user=1; trusted=1",
            )

            assert response.status_code == 200
            context = response.context
            assert context is not None
            assert context["vendor_commercial_access_allowed"] is False

    def test_report_uuid_cannot_authorize(self) -> None:
        "BLOCKER 2.9: the UUID path segment itself does not authorize."
        from unittest.mock import patch
        from django.test import Client
        from django.urls import reverse

        run = self._create_run_with_supplement()
        url = reverse("research-detail", kwargs={"run_id": run.id})

        mock_settings = type("Settings", (), {
            "PI_VENDOR_PRICE_ALLOWED_CIDRS": "10.0.0.0/8"
        })()

        with patch(
            "product_intelligence.web.commercial_access._django_settings",
            mock_settings,
        ):
            # The URL already contains the UUID - but access depends on REMOTE_ADDR
            client = Client()
            response = client.get(url, REMOTE_ADDR="192.0.2.1")

            assert response.status_code == 200
            context = response.context
            assert context is not None
            assert context["vendor_commercial_access_allowed"] is False


# ============================================================================
# BLOCKER 3 — Sentinel Vendor price HTML non-leak tests
# ============================================================================


class TestVendorPriceNoLeak:
    """Assert the sentinel vendor price Decimal('91827.43') never appears in
    HTML responses, regardless of REMOTE_ADDR authorization state.

    This proves the access gate is an authorization check only - it does not
    yet decode/project vendor commercial rows into the template context.

    4D-C browser rendering is NOT implemented; this guard will catch any
    accidental leakage when it is.
    """

    SENTINEL_PRICE = "91827.43"

    def _create_run_with_sentinel_supplement(
        self,
        *,
        vendor_price: "Decimal" = None,
    ) -> "ResearchRun":
        """Create a ResearchRun with a ResearchSupplementSnapshot containing
        the sentinel vendor price Decimal('91827.43').
        """
        from datetime import datetime, timezone
        from decimal import Decimal

        from product_intelligence.domain import ResearchRequest
        from product_intelligence.research.commercial_supplement_codec import (
            ResearchSupplementResult,
            SupplementAvailability,
            SupplementLookupStatus,
            SupplementPriceBasis,
            SupplementSourceObservation,
            VendorCommercialResult,
            encode_research_supplement_result,
        )
        from product_intelligence.runs.models import (
            ResearchRun,
            ResearchSupplementSnapshot,
        )

        if vendor_price is None:
            vendor_price = Decimal(self.SENTINEL_PRICE)

        run = ResearchRun.objects.create_from_request(
            ResearchRequest(
                manufacturer_part_number="SENTINEL-MPN-001",
                description="Sentinel test product",
            ),
        )

        result = ResearchSupplementResult(
            vendor_commercial_result=VendorCommercialResult(
                lookup_status=SupplementLookupStatus.SUCCESS,
                retrieved_at=datetime(2025, 1, 15, 12, 0, 0, tzinfo=timezone.utc),
                observations=(
                    SupplementSourceObservation(
                        source_name="INTERNAL_VENDOR",
                        explicit_candidate_mpn="SENTINEL-MPN-001",
                        vendor_mpn_match_type="EXACT",
                        price_amount=vendor_price,
                        currency_code="USD",
                        availability=SupplementAvailability.IN_STOCK,
                        price_basis=SupplementPriceBasis.CUSTOMER_PRICE,
                        quantity=None,
                        note_kind=None,
                        brand_new=True,
                        brand_new_basis="VENDOR_API_POLICY",
                    ),
                ),
                source_issues=(),
            ),
        )

        payload = encode_research_supplement_result(result)
        ResearchSupplementSnapshot.objects.create(
            run=run,
            schema_version=1,
            payload=payload,
        )

        return run

    def test_allowed_ip_response_does_not_leak_sentinel_price(self) -> None:
        "BLOCKER 3.A: allowed REMOTE_ADDR -> HTML must not contain sentinel price."
        from unittest.mock import patch
        from django.test import Client
        from django.urls import reverse

        run = self._create_run_with_sentinel_supplement()
        url = reverse("research-detail", kwargs={"run_id": run.id})

        mock_settings = type("Settings", (), {
            "PI_VENDOR_PRICE_ALLOWED_CIDRS": "10.0.0.0/8"
        })()

        with patch(
            "product_intelligence.web.commercial_access._django_settings",
            mock_settings,
        ):
            client = Client()
            response = client.get(url, REMOTE_ADDR="10.0.0.1")

            assert response.status_code == 200
            assert self.SENTINEL_PRICE.encode() not in response.content, (
                f"Sentinel price {self.SENTINEL_PRICE!r} must not appear in "
                "HTML response when authorized - 4D-C rendering not implemented"
            )

    def test_denied_ip_response_does_not_leak_sentinel_price(self) -> None:
        "BLOCKER 3.B: denied REMOTE_ADDR -> HTML must not contain sentinel price."
        from unittest.mock import patch
        from django.test import Client
        from django.urls import reverse

        run = self._create_run_with_sentinel_supplement()
        url = reverse("research-detail", kwargs={"run_id": run.id})

        mock_settings = type("Settings", (), {
            "PI_VENDOR_PRICE_ALLOWED_CIDRS": "10.0.0.0/8"
        })()

        with patch(
            "product_intelligence.web.commercial_access._django_settings",
            mock_settings,
        ):
            client = Client()
            response = client.get(url, REMOTE_ADDR="192.0.2.1")

            assert response.status_code == 200
            assert self.SENTINEL_PRICE.encode() not in response.content, (
                f"Sentinel price {self.SENTINEL_PRICE!r} must not appear in "
                "HTML response when denied either"
            )

    def test_raw_supplement_payload_not_in_response(self) -> None:
        "The raw JSON supplement payload must not appear in the HTML response."
        from unittest.mock import patch
        from django.test import Client
        from django.urls import reverse

        run = self._create_run_with_sentinel_supplement()
        url = reverse("research-detail", kwargs={"run_id": run.id})

        mock_settings = type("Settings", (), {
            "PI_VENDOR_PRICE_ALLOWED_CIDRS": "10.0.0.0/8"
        })()

        with patch(
            "product_intelligence.web.commercial_access._django_settings",
            mock_settings,
        ):
            client = Client()
            response = client.get(url, REMOTE_ADDR="10.0.0.1")

            assert response.status_code == 200
            content_str = response.content.decode("utf-8", errors="replace")

            # The sentinel price must not appear
            assert self.SENTINEL_PRICE not in content_str

            # The internal vendor source name must not appear
            assert "INTERNAL_VENDOR" not in content_str

            # Note: the run's own manufacturer_part_number IS legitimately
            # shown in the report. We do NOT assert SENTINEL-MPN-001 is absent
            # in the general HTML - it is the run's own MPN, not vendor data.

# ============================================================================
# BLOCKER 2 (real) — zero-live-work historical report GET, fail-fast armed
# ============================================================================


class TestZeroLiveWorkHistoricalReport:
    """Prove that GET /research/<uuid> performs ZERO live provider,
    network, or semantic work.

    The real research-detail route is executed with Django's test client
    while every live boundary in the system is armed with a RuntimeError
    sentinel: touching any armed boundary fails the test immediately.

    The run carries BOTH a decoded PriceIntelligenceSnapshot (real
    historical report content that must render) AND a
    ResearchSupplementSnapshot with the sentinel vendor price (commercial
    data that must exist in the database yet be neither re-fetched live nor
    leaked into HTML).

    An HTTP 200 alone would not prove this (a provider could still have
    been called); the armed sentinels make any live work fail fast.
    """

    SENTINEL_PRICE = "91827.43"

    def _create_historical_run(self) -> "ResearchRun":
        """Create a run with a real historical price snapshot plus a vendor
        supplement snapshot containing the sentinel commercial price.
        """
        from datetime import datetime, timezone
        from decimal import Decimal

        from product_intelligence.domain import ResearchRequest
        from product_intelligence.domain.enums import (
            ConfidenceLevel,
            EvidenceDecision,
            IdentityMatchType,
            VerificationStatus,
        )
        from product_intelligence.research import (
            ListingIdentityAssessment,
            ListingObservation,
            PriceAggregateBucket,
            PriceAggregationResult,
            encode_price_aggregation_result,
        )
        from product_intelligence.research.commercial_supplement_codec import (
            ResearchSupplementResult,
            SupplementAvailability,
            SupplementLookupStatus,
            SupplementPriceBasis,
            SupplementSourceObservation,
            VendorCommercialResult,
            encode_research_supplement_result,
        )
        from product_intelligence.research.listings import ExtractionMethod
        from product_intelligence.research.matching import EvidenceSource
        from product_intelligence.research.normalization import (
            NormalizedAvailability,
            NormalizedCondition,
            NormalizedListingObservation,
        )
        from product_intelligence.runs.models import (
            PriceIntelligenceSnapshot,
            ResearchRun,
            ResearchSupplementSnapshot,
        )

        mpn = "ZERO-LIVE-MPN-42"
        run = ResearchRun.objects.create_from_request(
            ResearchRequest(
                manufacturer_part_number=mpn,
                description="Zero-live work historical report test",
            ),
        )

        # --- Historical price intelligence snapshot (real report content) ---
        obs = ListingObservation(
            source_url="https://example.com/ssd-1tb",
            extraction_method=ExtractionMethod.JSON_LD,
            product_title="Samsung 980 PRO 1TB",
            manufacturer_part_number_text=mpn,
            sku_text="SSD-980-1T",
            brand_text="Samsung",
            price_text="$109.99",
            currency_text="USD",
            availability_text="In Stock",
            condition_text="New",
            seller_text="Example Store",
            offer_url_text=None,
            raw_reference="https://example.com/ssd-1tb",
        )
        norm = NormalizedListingObservation(
            observation=obs,
            price_amount=Decimal("109.99"),
            currency_code="USD",
            availability=NormalizedAvailability.IN_STOCK,
            condition=NormalizedCondition.NEW,
            seller_name="Example Store",
            normalization_issues=(),
        )
        assess = ListingIdentityAssessment(
            normalized_listing=norm,
            requested_part_number=mpn,
            candidate_part_number_raw=mpn,
            candidate_part_number_compared=mpn,
            candidate_evidence_source=EvidenceSource.EXPLICIT_MPN_FIELD,
            match_type=IdentityMatchType.EXACT,
            decision=EvidenceDecision.ACCEPTED,
            rejection_reason=None,
        )
        result = PriceAggregationResult(
            request=run.to_research_request(),
            assessments=(assess,),
            exclusions=(),
            buckets=(
                PriceAggregateBucket(
                    currency_code="USD",
                    condition=NormalizedCondition.NEW,
                    assessments=(assess,),
                    count=1,
                    low=Decimal("109.99"),
                    median=Decimal("109.99"),
                    high=Decimal("109.99"),
                    market_range_low=None,
                    market_range_high=None,
                    confidence=ConfidenceLevel.LOW,
                ),
            ),
            verification_status=VerificationStatus.VERIFIED,
        )
        PriceIntelligenceSnapshot.objects.create(
            run=run,
            schema_version=1,
            payload=encode_price_aggregation_result(result),
        )

        # --- Vendor supplement snapshot (commercial price exists in DB) ---
        supplement = ResearchSupplementResult(
            vendor_commercial_result=VendorCommercialResult(
                lookup_status=SupplementLookupStatus.SUCCESS,
                retrieved_at=datetime(
                    2025, 1, 15, 12, 0, 0, tzinfo=timezone.utc
                ),
                observations=(
                    SupplementSourceObservation(
                        source_name="INTERNAL_VENDOR",
                        explicit_candidate_mpn=mpn,
                        vendor_mpn_match_type="EXACT",
                        price_amount=Decimal(self.SENTINEL_PRICE),
                        currency_code="USD",
                        availability=SupplementAvailability.IN_STOCK,
                        price_basis=SupplementPriceBasis.CUSTOMER_PRICE,
                        quantity=None,
                        note_kind=None,
                        brand_new=True,
                        brand_new_basis="VENDOR_API_POLICY",
                    ),
                ),
                source_issues=(),
            ),
        )
        ResearchSupplementSnapshot.objects.create(
            run=run,
            schema_version=1,
            payload=encode_research_supplement_result(supplement),
        )

        return run

    @staticmethod
    def _armed_live_boundaries():
        """Arm every live provider/network/semantic boundary with the
        RuntimeError sentinel.

        Patched boundaries (exact repository symbols):
        - SerperSearchProvider.search            (search provider)
        - HttpPageFetcher.fetch                  (page fetch provider)
        - InternalVendorAdapter.lookup           (Vendor commercial API)
        - EcbFxProvider.__init__                 (FX provider construction)
        - EcbFxProvider.fetch_rates              (FX live fetch)
        - SemanticRuntime.evaluate               (semantic runtime entry)
        - semantic_integration.evaluate_semantic_matches (semantic
          evaluation entry point)
        - urllib.request.urlopen                 (raw stdlib HTTP)
        - urllib.request.OpenerDirector.open     (opener-based HTTP used by
          http_page / internal_vendor)
        """
        from contextlib import contextmanager
        import urllib.request
        from unittest.mock import patch
        from product_intelligence.execution import semantic_integration
        from product_intelligence.providers.fx import EcbFxProvider
        from product_intelligence.providers.http_page import HttpPageFetcher
        from product_intelligence.providers.internal_vendor import (
            InternalVendorAdapter,
        )
        from product_intelligence.providers.serper import SerperSearchProvider
        from product_intelligence.semantic.runtime import SemanticRuntime

        @contextmanager
        def _armed():
            with (
                patch.object(
                    SerperSearchProvider, "search", _live_boundary_boom
                ),
                patch.object(
                    HttpPageFetcher, "fetch", _live_boundary_boom
                ),
                patch.object(
                    InternalVendorAdapter, "lookup", _live_boundary_boom
                ),
                patch.object(
                    EcbFxProvider, "__init__", _live_boundary_boom
                ),
                patch.object(
                    EcbFxProvider, "fetch_rates", _live_boundary_boom
                ),
                patch.object(
                    SemanticRuntime, "evaluate", _live_boundary_boom
                ),
                patch.object(
                    semantic_integration,
                    "evaluate_semantic_matches",
                    _live_boundary_boom,
                ),
                patch(
                    "urllib.request.urlopen", _live_boundary_boom
                ),
                patch(
                    "urllib.request.OpenerDirector.open",
                    _live_boundary_boom,
                ),
            ):
                yield

        return _armed()

    def _assert_live_boundaries_are_armed(self) -> None:
        """Non-vacuity proof: every armed sentinel must actually raise
        RuntimeError when touched. If a sentinel were inert, the zero-live
        proof would be meaningless.
        """
        import urllib.request
        from product_intelligence.execution import semantic_integration
        from product_intelligence.providers.fx import EcbFxProvider
        from product_intelligence.providers.http_page import HttpPageFetcher
        from product_intelligence.providers.internal_vendor import (
            InternalVendorAdapter,
        )
        from product_intelligence.providers.serper import SerperSearchProvider
        from product_intelligence.semantic.runtime import SemanticRuntime

        armed = (
            lambda: SerperSearchProvider.search(None),
            lambda: HttpPageFetcher.fetch(None),
            lambda: InternalVendorAdapter.lookup(None),
            lambda: EcbFxProvider.__init__(None),
            lambda: EcbFxProvider.fetch_rates(None),
            lambda: SemanticRuntime.evaluate(None),
            lambda: semantic_integration.evaluate_semantic_matches(
                None, (), None
            ),
            lambda: urllib.request.urlopen("http://127.0.0.1/"),
        )
        for touch in armed:
            with pytest.raises(RuntimeError, match="live provider/network"):
                touch()

    def test_zero_live_work_on_allowed_historical_report_get(self) -> None:
        ("Authorized GET /research/<uuid> renders the historical report and "
        "evaluates commercial access with zero live work — no armed "
        "boundary may be touched.")
        from unittest.mock import patch

        from django.test import Client
        from django.urls import reverse

        run = self._create_historical_run()
        url = reverse("research-detail", kwargs={"run_id": run.id})

        mock_settings = type("Settings", (), {
            "PI_VENDOR_PRICE_ALLOWED_CIDRS": "10.0.0.0/8"
        })()

        with patch(
            "product_intelligence.web.commercial_access._django_settings",
            mock_settings,
        ), self._armed_live_boundaries():
            self._assert_live_boundaries_are_armed()

            client = Client()
            response = client.get(url, REMOTE_ADDR="10.0.0.1")

            # The real route executed and succeeded.
            assert response.status_code == 200
            assert response.context is not None
            # Commercial access gate evaluated to allowed.
            assert response.context["vendor_commercial_access_allowed"] is True
            # The historical report really rendered (not an empty/error
            # page): the run's MPN is shown in the report header.
            assert run.manufacturer_part_number.encode() in response.content
            # The vendor price present in the DB never leaked into HTML.
            assert self.SENTINEL_PRICE.encode() not in response.content

    def test_zero_live_work_on_denied_historical_report_get(self) -> None:
        ("Denied GET /research/<uuid> also performs zero live work — the "
        "gate's deny path must not trigger any provider, network, or "
        "semantic call.")
        from unittest.mock import patch

        from django.test import Client
        from django.urls import reverse

        run = self._create_historical_run()
        url = reverse("research-detail", kwargs={"run_id": run.id})

        mock_settings = type("Settings", (), {
            "PI_VENDOR_PRICE_ALLOWED_CIDRS": "10.0.0.0/8"
        })()

        with patch(
            "product_intelligence.web.commercial_access._django_settings",
            mock_settings,
        ), self._armed_live_boundaries():
            self._assert_live_boundaries_are_armed()

            client = Client()
            # 192.0.2.0/24 is TEST-NET-1 (RFC 5737) — never assigned, denied.
            response = client.get(url, REMOTE_ADDR="192.0.2.1")

            assert response.status_code == 200
            assert response.context is not None
            assert response.context["vendor_commercial_access_allowed"] is False
            assert run.manufacturer_part_number.encode() in response.content
            assert self.SENTINEL_PRICE.encode() not in response.content