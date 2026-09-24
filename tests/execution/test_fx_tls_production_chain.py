"""Execution-level proof for the FX/TLS production issue (PROD-FIX1,
defect 6).

Locked behavior chain when the FX provider fails with a TLS trust-chain
error (classified as ``FxNetworkError``):

* the run still completes (FX is display-supplemental / nonfatal);
* NO ResearchFxSnapshot is persisted;
* the original non-USD price survives in the PriceIntelligenceSnapshot
  (Machine Price is deterministic-only and untouched);
* the Compact Quote replay renders the original price with USD Equivalent
  "Unavailable" (no fabricated conversion, no caching hiding the failure).
"""

from __future__ import annotations

import ssl
import urllib.error
from datetime import datetime, timezone
from decimal import Decimal
from unittest.mock import MagicMock, patch

from django.test import TestCase

from product_intelligence.domain import ResearchRequest
from product_intelligence.domain.enums import ResearchRunState
from product_intelligence.execution import replay_compact_quote_projection
from product_intelligence.providers.fx import FxNetworkError, FxProviderError
from product_intelligence.research.price_result_codec import (
    decode_price_aggregation_result,
)
from product_intelligence.runs.models import (
    PriceIntelligenceSnapshot,
    ResearchFxSnapshot,
    ResearchRun,
)


class _TlsFailingFxProvider:
    """An FX provider that fails exactly like production did: the TLS
    trust-chain verification error surfaces as FxNetworkError."""

    def __init__(self) -> None:
        self.call_count = 0

    def fetch_rates(self, requested_currencies=None) -> None:
        self.call_count += 1
        raise FxNetworkError(
            "ECB network error: "
            + str(
                urllib.error.URLError(
                    ssl.SSLCertVerificationError(
                        1,
                        "certificate verify failed: unable to get local "
                        "issuer certificate",
                    )
                )
            )
        )


def _zar_listing_html() -> str:
    return """
    <html><head>
    <script type="application/ld+json">
    {
        "@context": "https://schema.org",
        "@type": "Product",
        "name": "Zar Product",
        "mpn": "TLS-ZAR-MPN",
        "offers": {
            "@type": "Offer",
            "price": "30999.0",
            "priceCurrency": "ZAR",
            "availability": "https://schema.org/InStock",
            "itemCondition": "https://schema.org/NewCondition"
        }
    }
    </script></head><body>Zar Product</body></html>
    """


class TestFxTlsFailureChain(TestCase):
    """FX TLS failure: nonfatal, no snapshot, price survives, USD Unavailable."""

    def _run_with_zar_bucket(self):
        from product_intelligence.providers.search import SearchResponse, SearchQuery
        from product_intelligence.providers.search import SearchResult
        from product_intelligence.providers.http_page import FetchedPage, PageFetchRequest

        request = ResearchRequest(
            manufacturer_part_number="TLS-ZAR-MPN",
            description="ZAR product",
        )
        run = ResearchRun.objects.create_from_request(request)

        search_result = SearchResult(
            source_url="https://zar.example.com/product",
            title="Zar Product",
            snippet="test",
            price_hint_text=None,
            part_number_hint="TLS-ZAR-MPN",
            raw_reference=None,
        )
        search_response = SearchResponse(
            provider_id="test",
            query=SearchQuery(text="tls zar mpn"),
            retrieved_at=datetime.now(tz=timezone.utc),
            results=(search_result,),
            raw_response_reference=None,
        )
        provider = MagicMock()
        provider.search.return_value = search_response

        def fake_fetch(fetch_request: PageFetchRequest) -> FetchedPage:
            html = _zar_listing_html()
            return FetchedPage(
                requested_url=fetch_request.url,
                final_url=fetch_request.url,
                retrieved_at=datetime.now(tz=timezone.utc),
                status_code=200,
                body_text=html,
                content_type="text/html",
                body_byte_count=len(html.encode("utf-8")),
                redirect_count=0,
                fetcher_id="test",
            )

        page_fetcher = MagicMock()
        page_fetcher.fetch.side_effect = fake_fetch

        fx_provider = _TlsFailingFxProvider()

        with patch.dict(
            "os.environ", {"PI_VENDOR_LOOKUP_BASE_URL": ""}, clear=False
        ):
            import os

            os.environ.pop("PI_VENDOR_LOOKUP_BASE_URL", None)
            from product_intelligence.execution import execute_research_run

            result = execute_research_run(
                str(run.id),
                search_provider=provider,
                page_fetcher=page_fetcher,
                fx_provider=fx_provider,
            )
        return run, fx_provider, result

    def test_tls_fx_failure_nonfatal_chain(self) -> None:
        run, fx_provider, result = self._run_with_zar_bucket()

        # 1. Provider was invoked and failed (TLS trust chain)
        assert fx_provider.call_count == 1

        # 2. Run still COMPLETED — FX failure is display-supplemental
        run.refresh_from_db()
        assert run.current_state == ResearchRunState.COMPLETED

        # 3. NO ResearchFxSnapshot persisted
        with self.assertRaises(ResearchFxSnapshot.DoesNotExist):
            ResearchFxSnapshot.objects.get(run=run)

        # 4. Original ZAR price survives in the Machine Price snapshot
        snapshot = PriceIntelligenceSnapshot.objects.get(run=run)
        decoded = decode_price_aggregation_result(
            snapshot.payload, schema_version=snapshot.schema_version
        )
        assert len(decoded.buckets) == 1
        bucket = decoded.buckets[0]
        assert bucket.currency_code == "ZAR"
        assert bucket.median == Decimal("30999.0")

        # 5. Compact Quote replay: original price + USD Equivalent
        #    "Unavailable" (never fabricated, never hidden by caching)
        replay = replay_compact_quote_projection(str(run.id))
        rows = list(replay.projection.rows)
        assert len(rows) == 1
        assert rows[0].price_original == "ZAR 30,999.0"
        assert rows[0].usd_equivalent == "Unavailable"
        assert rows[0].usd_equivalent_amount is None

    def test_tls_error_classification_is_bounded(self) -> None:
        """The exact production error class converts to FxNetworkError via
        the real stdlib wrapping path, and FxNetworkError is the bounded
        nonfatal taxonomy (FxProviderError)."""
        from product_intelligence.providers.fx import EcbFxProvider

        provider = EcbFxProvider()
        err = urllib.error.URLError(
            ssl.SSLCertVerificationError(
                1, "certificate verify failed: unable to get local "
                "issuer certificate"
            )
        )
        with patch("urllib.request.urlopen", side_effect=err):
            try:
                provider.fetch_rates()
            except FxProviderError as caught:
                assert isinstance(caught, FxNetworkError)
            else:
                self.fail("TLS verification failure must raise FxNetworkError")
