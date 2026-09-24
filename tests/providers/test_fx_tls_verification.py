"""FX/TLS production-issue regression tests (PROD-FIX1, defect 6).

Production observation: a ZAR 4A bucket triggered an FX fetch, but the
provider connection failed with ``ssl.SSLCertVerificationError`` /
``CERTIFICATE_VERIFY_FAILED`` / ``unable to get local issuer certificate``.
The correct conclusion:

* The provider's secure HTTPS verification WORKED as designed — it refused
  an untrusted certificate chain.
* The provider correctly converts the failure to ``FxNetworkError`` and
  orchestration correctly treats FX failure as display-supplemental /
  nonfatal (no ResearchFxSnapshot, original price survives, USD Equivalent
  unavailable).
* The trust-chain repair is an OPERATIONAL server action (install/update
  the CA trust store on the production host). It is NOT solved by an
  insecure TLS bypass in code.

This file locks that in:

1. The exact production error class is classified as ``FxNetworkError``
   (bounded, nonfatal) — via the real stdlib wrapping path (urllib wraps
   ``OSError``/SSL errors from the request into ``URLError``).
2. The FX provider source contains NO insecure TLS bypass: no unverified
   context, no CERT_NONE, no verify=False, no disabled hostname check,
   and urlopen is called WITHOUT any custom SSL context argument.
"""

from __future__ import annotations

import ssl
import urllib.error
from pathlib import Path
from unittest.mock import patch

import pytest

from product_intelligence.providers.fx import (
    EcbFxProvider,
    FxNetworkError,
    FxProviderError,
)

PACKAGE_ROOT = Path(__file__).resolve().parents[2] / "product_intelligence"


class TestSslCertVerificationErrorClassification:
    """The production TLS failure is a bounded FX network error."""

    def _production_error(self) -> ssl.SSLCertVerificationError:
        return ssl.SSLCertVerificationError(
            1,
            "certificate verify failed: unable to get local issuer certificate",
        )

    def test_urlerror_wrapping_ssl_verification_error_is_fx_network_error(self) -> None:
        """Real stdlib path: urllib.do_open wraps the handshake OSError
        (SSLCertVerificationError) into URLError; the provider classifies
        URLError as FxNetworkError (nonfatal, display-supplemental)."""
        provider = EcbFxProvider()
        with patch(
            "urllib.request.urlopen",
            side_effect=urllib.error.URLError(self._production_error()),
        ):
            with pytest.raises(FxNetworkError):
                provider.fetch_rates(requested_currencies=frozenset({"USD"}))

    def test_fx_network_error_is_a_bounded_provider_error(self) -> None:
        """FxNetworkError is within the taxonomy orchestration catches as
        NONFATAL — the run still completes without an FX snapshot."""
        assert issubclass(FxNetworkError, FxProviderError)

    def test_error_is_not_swallowed_silently(self) -> None:
        """The failure raises (bounded) rather than returning fabricated
        rates."""
        provider = EcbFxProvider()
        with patch(
            "urllib.request.urlopen",
            side_effect=urllib.error.URLError(self._production_error()),
        ):
            with pytest.raises(FxProviderError):
                provider.fetch_rates()


class TestNoInsecureTlsBypass:
    """The FX provider must keep secure HTTPS verification.

    These are mechanical source guards: any future edit that introduces an
    unverified SSL context, disables certificate validation, or points the
    client at an untrusted HTTP endpoint fails here.
    """

    def _fx_source(self) -> str:
        return (
            (PACKAGE_ROOT / "providers" / "fx.py").read_text(encoding="utf-8")
        )

    def test_no_unverified_ssl_context(self) -> None:
        source = self._fx_source()
        assert "_create_unverified_context" not in source
        assert "SSLContext(" not in source or "create_default" in source

    def test_no_cert_none(self) -> None:
        assert "CERT_NONE" not in self._fx_source()

    def test_no_verify_false(self) -> None:
        assert "verify=False" not in self._fx_source()
        assert "verify = False" not in self._fx_source()

    def test_hostname_check_not_disabled(self) -> None:
        assert "check_hostname" not in self._fx_source()

    def test_urlopen_called_without_custom_context(self) -> None:
        """The client uses the default (verifying) SSL context: urlopen is
        called with no ``context=`` argument anywhere in the provider."""
        source = self._fx_source()
        call = source.split("urllib.request.urlopen(", 1)[1]
        # the single call site in this module
        assert "urllib.request.urlopen(" in source
        assert "context=" not in call.split(")")[0]

    def test_provider_stays_https(self) -> None:
        """The FX endpoint remains the official HTTPS URL — no silent
        fallback to an untrusted HTTP endpoint."""
        source = self._fx_source()
        assert 'http://www.ecb.europa.eu' not in source
        assert "https://www.ecb.europa.eu/stats/eurofxref/eurofxref-daily.xml" in source
