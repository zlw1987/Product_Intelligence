"""Tests for PRODUCT-INTEL.4D-A (Preferred Source Acquisition Optimization).

Covers:
* Generic DirectSource boundary (vendor-neutral, network-free)
* DirectMacro adapter (URL encoding, zero network calls)
* Preferred-source configuration (PI_PREFERRED_SEARCH_DOMAINS)
* Execution orchestration changes (direct -> fallback semantics)
* Fallback triggering (4A bucket check)
* Lazy Serper construction
* Execution evidence records (SEARCH, AGGREGATE)
* Deduplication across direct + fallback
* Authority invariants (frozen 3C, 4A unchanged)
"""

from __future__ import annotations

import os
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path
from typing import TYPE_CHECKING
from unittest.mock import MagicMock, patch

import pytest

from product_intelligence.domain import ResearchRequest
from product_intelligence.domain.enums import (
    EvidenceDecision,
    IdentityMatchType,
    ResearchRunState,
    VerificationStatus,
)
from product_intelligence.domain.evidence import ExecutionOutcome, ExecutionStage
from product_intelligence.execution import execute_research_run, ExecutionError
from product_intelligence.execution.deduplication import CandidateDeduplicator
from product_intelligence.execution.evidence_writer import ExecutionEvidenceWriter
from product_intelligence.providers.direct_source import (
    DirectSourceLocator,
    DirectSourceQuery,
    DirectSourceTarget,
)
from product_intelligence.providers.page import (
    FetchedPage,
    PageFetchError,
    PageFetcher,
    PageFetchRequest,
)
from product_intelligence.providers.search import (
    SearchProvider,
    SearchQuery,
    SearchResponse,
    SearchResult,
)
from product_intelligence.research.aggregation import (
    PriceAggregationExclusionReason,
    PriceAggregationResult,
    aggregate_listing_prices,
)
from product_intelligence.research.matching import (
    EvidenceSource,
    IdentityRejectionReason,
    ListingIdentityAssessment,
)
from product_intelligence.research.normalization import (
    NormalizedAvailability,
    NormalizedCondition,
    NormalizedListingObservation,
)
from product_intelligence.runs.models import ResearchRun

if TYPE_CHECKING:
    from collections.abc import Sequence


# ---------------------------------------------------------------------------
# Section 1: Generic DirectSource boundary
# ---------------------------------------------------------------------------


class TestDirectSourceBoundary:
    """Test the generic DirectSource boundary is vendor-neutral and network-free."""

    def test_direct_source_query_requires_non_empty_mpn(self) -> None:
        """DirectSourceQuery rejects empty MPN."""
        with pytest.raises(ValueError, match="manufacturer_part_number"):
            DirectSourceQuery(manufacturer_part_number="")

        with pytest.raises(ValueError, match="manufacturer_part_number"):
            DirectSourceQuery(manufacturer_part_number="  ")

    def test_direct_source_query_strips_whitespace(self) -> None:
        """DirectSourceQuery strips surrounding whitespace."""
        query = DirectSourceQuery(manufacturer_part_number="  BCM957608  ")
        assert query.manufacturer_part_number == "BCM957608"

    def test_direct_source_query_rejects_non_string(self) -> None:
        """DirectSourceQuery rejects non-string MPN."""
        with pytest.raises(TypeError):
            DirectSourceQuery(manufacturer_part_number=12345)  # type: ignore

    def test_direct_source_target_validates_url(self) -> None:
        """DirectSourceTarget validates URL is safe absolute http(s)."""
        target = DirectSourceTarget(url="https://example.com/path?q=test")
        assert target.url == "https://example.com/path?q=test"

        with pytest.raises(ValueError):
            DirectSourceTarget(url="javascript:alert(1)")

        with pytest.raises(ValueError):
            DirectSourceTarget(url="//evil.com/path")

        with pytest.raises(ValueError):
            DirectSourceTarget(url="https://user:pass@example.com/")

    def test_direct_source_locator_is_protocol(self) -> None:
        """DirectSourceLocator is a Protocol."""
        from typing import Protocol as TypingProtocol
        assert issubclass(DirectSourceLocator, TypingProtocol)

    def test_direct_source_module_is_stdlib_only(self) -> None:
        """direct_source.py imports only stdlib modules."""
        import sys
        import ast

        path = Path(__file__).resolve().parents[2] / "product_intelligence" / "providers" / "direct_source.py"
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    top = alias.name.split(".")[0]
                    if top != "product_intelligence":
                        assert top in sys.stdlib_module_names, (
                            f"direct_source.py imports non-stdlib {top}"
                        )
            elif isinstance(node, ast.ImportFrom) and node.module:
                if not node.level:
                    top = node.module.split(".")[0]
                    if top != "product_intelligence":
                        assert top in sys.stdlib_module_names, (
                            f"direct_source.py imports non-stdlib {top}"
                        )

    def test_direct_source_module_has_no_vendor_names(self) -> None:
        """direct_source.py names no vendor."""
        path = Path(__file__).resolve().parents[2] / "product_intelligence" / "providers" / "direct_source.py"
        source = path.read_text(encoding="utf-8")
        for vendor in ("serper", "tavily", "google", "bing", "directmacro"):
            assert vendor not in source.lower(), (
                f"direct_source.py references vendor '{vendor}'"
            )

    def test_direct_source_module_opens_no_connection(self) -> None:
        """direct_source.py imports no network modules."""
        import ast

        path = Path(__file__).resolve().parents[2] / "product_intelligence" / "providers" / "direct_source.py"
        tree = ast.parse(path.read_text(encoding="utf-8"))
        network = {"urllib.request", "urllib.error", "http.client", "socket", "ssl"}
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    assert not any(alias.name.startswith(n) for n in network)
            elif isinstance(node, ast.ImportFrom) and node.module:
                assert not any(node.module.startswith(n) for n in network)


# ---------------------------------------------------------------------------
# Section 2: DirectMacro adapter
# ---------------------------------------------------------------------------


class TestDirectMacroAdapter:
    """Test the DirectMacro adapter."""

    def test_direct_macro_url_encodes_exact_mpn(self) -> None:
        """DirectMacro adapter URL-encodes the exact MPN."""
        from product_intelligence.providers.directmacro import DirectMacroLocator

        locator = DirectMacroLocator()
        query = DirectSourceQuery(manufacturer_part_number="BCM957608-P2200GQF00")
        targets = locator.locate(query)

        assert len(targets) == 1
        assert targets[0].url == (
            "https://directmacro.com/catalogsearch/result/?q=BCM957608-P2200GQF00"
        )

    def test_direct_macro_url_encodes_special_chars(self) -> None:
        """DirectMacro adapter URL-encodes special characters in MPN."""
        from product_intelligence.providers.directmacro import DirectMacroLocator

        locator = DirectMacroLocator()
        query = DirectSourceQuery(manufacturer_part_number="TEST/MPN+123")
        targets = locator.locate(query)

        assert len(targets) == 1
        # / and + should be percent-encoded
        assert "TEST%2FMPN%2B123" in targets[0].url

    def test_direct_macro_makes_zero_network_calls(self) -> None:
        """DirectMacro adapter makes zero network calls."""
        from product_intelligence.providers.directmacro import DirectMacroLocator

        locator = DirectMacroLocator()
        query = DirectSourceQuery(manufacturer_part_number="BCM957608-P2200GQF00")

        # No network modules should be involved — this is pure URL construction.
        # If the adapter tried to open a connection, this would fail in an
        # offline test environment.
        targets = locator.locate(query)
        assert len(targets) == 1

    def test_direct_macro_does_not_synthesize_product_slug(self) -> None:
        """DirectMacro adapter returns search-results URL, not product slug."""
        from product_intelligence.providers.directmacro import DirectMacroLocator

        locator = DirectMacroLocator()
        query = DirectSourceQuery(manufacturer_part_number="BCM957608-P2200GQF00")
        targets = locator.locate(query)

        assert len(targets) == 1
        # URL should be the search-results page, NOT a fabricated product slug
        assert "/catalogsearch/result/" in targets[0].url
        assert targets[0].url.endswith("q=BCM957608-P2200GQF00")

    def test_direct_macro_does_not_map_sku_to_mpn(self) -> None:
        """DirectMacro adapter does not map SKU to MPN."""
        from product_intelligence.providers.directmacro import DirectMacroLocator

        # The adapter only constructs URLs — it does no identity work.
        # This is proven by the fact that locate() takes only DirectSourceQuery
        # and returns DirectSourceTarget, with no SKU/MPN semantics.
        locator = DirectMacroLocator()
        query = DirectSourceQuery(manufacturer_part_number="SKU-123")
        targets = locator.locate(query)

        # The URL just encodes whatever MPN was given — no SKU transformation
        assert "SKU-123" in targets[0].url

    def test_direct_macro_does_not_extract_price(self) -> None:
        """DirectMacro adapter extracts no price — it only constructs URLs."""
        from product_intelligence.providers.directmacro import DirectMacroLocator

        locator = DirectMacroLocator()
        query = DirectSourceQuery(manufacturer_part_number="BCM957608-P2200GQF00")
        targets = locator.locate(query)

        # DirectSourceTarget has only a URL field — no price, no identity
        assert hasattr(targets[0], "url")
        assert not hasattr(targets[0], "price")
        assert not hasattr(targets[0], "mpn")
        assert not hasattr(targets[0], "sku")

    def test_direct_macro_requires_correct_query_type(self) -> None:
        """DirectMacro.locate raises TypeError for wrong query type."""
        from product_intelligence.providers.directmacro import DirectMacroLocator

        locator = DirectMacroLocator()
        with pytest.raises(TypeError, match="DirectSourceQuery"):
            locator.locate("BCM957608")  # type: ignore

    def test_direct_macro_conforms_to_locator_protocol(self) -> None:
        """DirectMacroLocator conforms to DirectSourceLocator protocol."""
        from product_intelligence.providers.directmacro import DirectMacroLocator
        from typing import Protocol as TypingProtocol

        # DirectSourceLocator is a Protocol; DirectMacroLocator should conform
        # by structural typing (has locate method returning tuple)
        locator = DirectMacroLocator()
        query = DirectSourceQuery(manufacturer_part_number="TEST")
        result = locator.locate(query)
        assert isinstance(result, tuple)
        assert all(isinstance(t, DirectSourceTarget) for t in result)


# ---------------------------------------------------------------------------
# Section 3: Preferred-source configuration
# ---------------------------------------------------------------------------


class TestPreferredSourceConfig:
    """Test PI_PREFERRED_SEARCH_DOMAINS configuration resolution."""

    def test_missing_config_preserves_old_behavior(self) -> None:
        """Missing PI_PREFERRED_SEARCH_DOMAINS preserves old behavior."""
        from product_intelligence.providers.preferred_source_config import (
            is_directmacro_enabled,
            resolve_preferred_domains,
        )

        with patch.dict(os.environ, {}, clear=False):
            # Remove the env var entirely
            env_copy = dict(os.environ)
            env_copy.pop("PI_PREFERRED_SEARCH_DOMAINS", None)
            with patch.dict(os.environ, env_copy, clear=True):
                assert resolve_preferred_domains() == frozenset()
                assert not is_directmacro_enabled()

    def test_blank_config_preserves_old_behavior(self) -> None:
        """Blank config preserves old behavior."""
        from product_intelligence.providers.preferred_source_config import (
            is_directmacro_enabled,
            resolve_preferred_domains,
        )

        with patch.dict(os.environ, {"PI_PREFERRED_SEARCH_DOMAINS": ""}):
            assert resolve_preferred_domains() == frozenset()
            assert not is_directmacro_enabled()

    def test_config_with_all_12_domains_activates_only_directmacro(self) -> None:
        """Config with all 12 domains activates only DirectMacro."""
        from product_intelligence.providers.preferred_source_config import (
            is_directmacro_enabled,
            resolve_preferred_domains,
        )

        all_domains = (
            "directmacro.com,esaitech.com,serversupply.com,dihuni.com,"
            "memory4less.com,fs.com,cdw.com,newegg.com,harddiskdirect.com,"
            "serverorbit.com,centralcomputer.com,naddod.com"
        )
        with patch.dict(os.environ, {"PI_PREFERRED_SEARCH_DOMAINS": all_domains}):
            domains = resolve_preferred_domains()
            # Only DIRECT domains activate (only directmacro.com)
            assert domains == frozenset({"directmacro.com"})
            assert is_directmacro_enabled()

    def test_config_with_directmacro_only(self) -> None:
        """Config with only directmacro.com enables DirectMacro."""
        from product_intelligence.providers.preferred_source_config import (
            is_directmacro_enabled,
            resolve_preferred_domains,
        )

        with patch.dict(
            os.environ,
            {"PI_PREFERRED_SEARCH_DOMAINS": "directmacro.com"},
        ):
            assert resolve_preferred_domains() == frozenset({"directmacro.com"})
            assert is_directmacro_enabled()

    def test_config_case_insensitive(self) -> None:
        """Domain names are case-insensitive."""
        from product_intelligence.providers.preferred_source_config import (
            is_directmacro_enabled,
        )

        with patch.dict(
            os.environ,
            {"PI_PREFERRED_SEARCH_DOMAINS": "DIRECTMACRO.COM"},
        ):
            assert is_directmacro_enabled()

    def test_config_whitespace_handling(self) -> None:
        """Whitespace in domain names is handled correctly."""
        from product_intelligence.providers.preferred_source_config import (
            is_directmacro_enabled,
        )

        with patch.dict(
            os.environ,
            {"PI_PREFERRED_SEARCH_DOMAINS": "  directmacro.com  , esaitech.com "},
        ):
            assert is_directmacro_enabled()

    def test_unsupported_domains_ignored(self) -> None:
        """Unsupported domains (SERPER_FALLBACK, UNSUITABLE) are ignored."""
        from product_intelligence.providers.preferred_source_config import (
            is_directmacro_enabled,
            resolve_preferred_domains,
        )

        with patch.dict(
            os.environ,
            {"PI_PREFERRED_SEARCH_DOMAINS": "esaitech.com,serversupply.com"},
        ):
            assert resolve_preferred_domains() == frozenset()
            assert not is_directmacro_enabled()


# ---------------------------------------------------------------------------
# Section 4: DirectMacro fixture verification
# ---------------------------------------------------------------------------


class TestDirectMacroFixture:
    """Test that the DirectMacro fixture produces correct 3A extractions."""

    def test_fixture_extracts_sku_only_identity(self) -> None:
        """BCM957608-P2200GQF00 fixture produces SKU-only identity (no explicit MPN)."""
        from product_intelligence.research.extraction import (
            extract_listing_observations,
        )

        fixture_path = Path(__file__).resolve().parents[1] / "fixtures" / "pages" / "directmacro_bcm957608_p2200gqf00_search.html"
        html = fixture_path.read_text(encoding="utf-8")

        observations = extract_listing_observations(
            html,
            source_url="https://directmacro.com/catalogsearch/result/?q=BCM957608-P2200GQF00",
        )

        assert len(observations) == 1
        obs = observations[0]

        # 4D-PRE verified: no explicit MPN field for the Broadcom product
        assert obs.manufacturer_part_number_text is None
        assert obs.sku_text == "BCM957608-P2200GQF00"
        assert obs.product_title is not None
        assert "BCM957608-P2200GQF00" in obs.product_title
        assert obs.brand_text == "Broadcom"
        assert obs.price_text == "2120.002"
        assert obs.currency_text == "USD"
        assert obs.availability_text == "http://schema.org/InStock"
        assert obs.condition_text is None

    def test_fixture_sku_only_is_rejected_by_frozen_3c(self) -> None:
        """SKU-only evidence from DirectMacro is REJECTED by frozen 3C."""
        from product_intelligence.research.extraction import (
            extract_listing_observations,
        )
        from product_intelligence.research.normalization import (
            normalize_listing_observation,
        )
        from product_intelligence.research.matching import (
            assess_listing_identity,
        )

        fixture_path = Path(__file__).resolve().parents[1] / "fixtures" / "pages" / "directmacro_bcm957608_p2200gqf00_search.html"
        html = fixture_path.read_text(encoding="utf-8")

        observations = extract_listing_observations(
            html,
            source_url="https://directmacro.com/catalogsearch/result/?q=BCM957608-P2200GQF00",
        )

        # Normalize
        normalized = normalize_listing_observation(observations[0])

        # Assess identity against the requested MPN
        request = ResearchRequest(
            manufacturer_part_number="BCM957608-P2200GQF00",
            description="Broadcom 400GbE Dual-Port QSFP112 Network Adapter",
        )
        assessment = assess_listing_identity(request, normalized)

        # SKU-only evidence is REJECTED by frozen 3C
        assert assessment.decision is EvidenceDecision.REJECTED
        assert assessment.rejection_reason is IdentityRejectionReason.NO_EXPLICIT_MPN_EVIDENCE
        assert assessment.candidate_evidence_source is EvidenceSource.SKU_FIELD

    def test_fixture_produces_rejected_assessment_with_price(self) -> None:
        """DirectMacro fixture produces REJECTED assessment with valid price.

        This proves the 4D-PRE finding: DirectMacro provides price evidence
        but frozen 3C rejects the identity (SKU-only).
        """
        from product_intelligence.research.extraction import (
            extract_listing_observations,
        )
        from product_intelligence.research.normalization import (
            normalize_listing_observation,
        )
        from product_intelligence.research.matching import (
            assess_listing_identity,
        )

        fixture_path = Path(__file__).resolve().parents[1] / "fixtures" / "pages" / "directmacro_bcm957608_p2200gqf00_search.html"
        html = fixture_path.read_text(encoding="utf-8")

        observations = extract_listing_observations(
            html,
            source_url="https://directmacro.com/catalogsearch/result/?q=BCM957608-P2200GQF00",
        )

        normalized = normalize_listing_observation(observations[0])
        request = ResearchRequest(
            manufacturer_part_number="BCM957608-P2200GQF00",
            description="Broadcom 400GbE Dual-Port QSFP112 Network Adapter",
        )
        assessment = assess_listing_identity(request, normalized)

        # REJECTED identity
        assert assessment.decision is EvidenceDecision.REJECTED

        # But price IS present and valid
        assert normalized.price_amount == Decimal("2120.002")
        assert normalized.currency_code == "USD"
        assert normalized.availability == NormalizedAvailability.IN_STOCK

        # Condition is UNKNOWN (no condition_text in fixture)
        assert normalized.condition == NormalizedCondition.UNKNOWN

        # This assessment would be excluded from 4A for IDENTITY_NOT_ACCEPTED
        # (not because of missing price, but because of rejected identity)


# ---------------------------------------------------------------------------
# Section 5: Execution orchestration — direct acquisition + fallback
# ---------------------------------------------------------------------------


class TestDirectAcquisitionExecution:
    """Test execution with direct acquisition and fallback semantics."""

    def _make_page_fetcher_from_fixture(
        self, fixture_name: str, url: str,
    ) -> PageFetcher:
        """Build a fake PageFetcher returning a real fixture."""
        fixture_path = Path(__file__).resolve().parents[1] / "fixtures" / "pages" / fixture_name
        html = fixture_path.read_text(encoding="utf-8")

        fake_fetcher = MagicMock(spec=PageFetcher)
        fake_fetcher.fetch.return_value = FetchedPage(
            requested_url=url,
            final_url=url,
            retrieved_at=datetime.now(tz=timezone.utc),
            status_code=200,
            body_text=html,
            content_type="text/html",
            body_byte_count=len(html.encode("utf-8")),
            redirect_count=0,
            fetcher_id="test",
        )
        return fake_fetcher

    def _make_empty_page_fetcher(self) -> PageFetcher:
        """Build a fake PageFetcher returning an empty page."""
        fake_fetcher = MagicMock(spec=PageFetcher)
        fake_fetcher.fetch.return_value = FetchedPage(
            requested_url="https://example.com",
            final_url="https://example.com",
            retrieved_at=datetime.now(tz=timezone.utc),
            status_code=200,
            body_text="<html><body>No listings</body></html>",
            content_type="text/html",
            body_byte_count=35,
            redirect_count=0,
            fetcher_id="test",
        )
        return fake_fetcher

    def _make_serper_fallback_provider(
        self, results: tuple[SearchResult, ...] = (),
    ) -> SearchProvider:
        """Build a fake SearchProvider returning specified results."""
        provider = MagicMock(spec=SearchProvider)
        provider.search.return_value = SearchResponse(
            provider_id="test",
            query=SearchQuery(text="test"),
            retrieved_at=datetime.now(tz=timezone.utc),
            results=results,
        )
        return provider

    # -- description-only request skips direct acquisition --

    def test_description_only_request_skips_direct_acquisition(
        self,
        research_run: ResearchRun,
    ) -> None:
        """Description-only request skips direct acquisition entirely."""
        # Create a description-only run
        from product_intelligence.runs.models import ResearchRun as RR
        request = ResearchRequest(
            manufacturer_part_number="",
            description="Some product description",
        )
        run = RR.objects.create_from_request(request)

        # Enable direct acquisition
        with patch.dict(
            os.environ,
            {"PI_PREFERRED_SEARCH_DOMAINS": "directmacro.com"},
        ):
            # Provide an empty Serper fallback (direct not tried, so fallback fires)
            provider = self._make_serper_fallback_provider()
            fetcher = self._make_empty_page_fetcher()

            result = execute_research_run(
                str(run.id),
                search_provider=provider,
                page_fetcher=fetcher,
            )

        # Should complete without error
        assert result.run.current_state == ResearchRunState.COMPLETED
        # Search was called because no direct acquisition was attempted
        provider.search.assert_called_once()

    # -- direct fetch failure -> fallback --

    def test_direct_fetch_failure_falls_back_to_search(
        self,
        research_run: ResearchRun,
    ) -> None:
        """Direct fetch failure triggers exactly one SearchProvider call."""
        # Page fetcher raises the classified transport failure on every
        # fetch (candidate fetch path records NETWORK_ERROR; the 4D-D
        # authority path bounds it to FETCH_FAILED — both expected, both
        # bounded; the run continues to the one fallback search).
        failing_fetcher = MagicMock(spec=PageFetcher)
        failing_fetcher.fetch.side_effect = PageFetchError("Network error")

        with patch.dict(
            os.environ,
            {"PI_PREFERRED_SEARCH_DOMAINS": "directmacro.com"},
        ):
            provider = self._make_serper_fallback_provider()
            result = execute_research_run(
                str(research_run.id),
                search_provider=provider,
                page_fetcher=failing_fetcher,
            )

        assert result.run.current_state == ResearchRunState.COMPLETED
        provider.search.assert_called_once()

    # -- direct empty extraction -> fallback --

    def test_direct_empty_extraction_falls_back_to_search(
        self,
        research_run: ResearchRun,
    ) -> None:
        """Direct source with zero observations triggers fallback."""
        with patch.dict(
            os.environ,
            {"PI_PREFERRED_SEARCH_DOMAINS": "directmacro.com"},
        ):
            provider = self._make_serper_fallback_provider()
            fetcher = self._make_empty_page_fetcher()
            result = execute_research_run(
                str(research_run.id),
                search_provider=provider,
                page_fetcher=fetcher,
            )

        assert result.run.current_state == ResearchRunState.COMPLETED
        provider.search.assert_called_once()

    # -- direct SKU-only evidence -> fallback --

    def test_direct_sku_only_evidence_falls_back_to_search(
        self,
        research_run: ResearchRun,
    ) -> None:
        """Direct source with SKU-only evidence (rejected by 3C) triggers fallback."""
        with patch.dict(
            os.environ,
            {"PI_PREFERRED_SEARCH_DOMAINS": "directmacro.com"},
        ):
            provider = self._make_serper_fallback_provider()
            # DirectMacro fixture produces SKU-only identity -> REJECTED by 3C
            # -> zero 4A buckets -> fallback required
            fetcher = self._make_page_fetcher_from_fixture(
                "directmacro_bcm957608_p2200gqf00_search.html",
                "https://directmacro.com/catalogsearch/result/?q=BCM957608-P2200GQF00",
            )
            result = execute_research_run(
                str(research_run.id),
                search_provider=provider,
                page_fetcher=fetcher,
            )

        # The DirectMacro fixture produces SKU-only evidence, rejected by 3C.
        # Zero 4A buckets -> fallback search required.
        provider.search.assert_called_once()

    # -- direct title-only evidence -> fallback --

    def test_direct_title_only_evidence_falls_back_to_search(
        self,
        research_run: ResearchRun,
    ) -> None:
        """Direct source with title-only evidence triggers fallback."""
        # Build a page with only title text (no SKU, no MPN)
        title_only_html = """
        <html><head>
        <script type="application/ld+json">
        {"@context":"https://schema.org","@type":"Product","name":"Some product MZ-QL23T800"}
        </script></head><body></body></html>
        """
        fake_fetcher = MagicMock(spec=PageFetcher)
        fake_fetcher.fetch.return_value = FetchedPage(
            requested_url="https://example.com",
            final_url="https://example.com",
            retrieved_at=datetime.now(tz=timezone.utc),
            status_code=200,
            body_text=title_only_html,
            content_type="text/html",
            body_byte_count=100,
            redirect_count=0,
            fetcher_id="test",
        )

        with patch.dict(
            os.environ,
            {"PI_PREFERRED_SEARCH_DOMAINS": "directmacro.com"},
        ):
            provider = self._make_serper_fallback_provider()
            result = execute_research_run(
                str(research_run.id),
                search_provider=provider,
                page_fetcher=fake_fetcher,
            )

        provider.search.assert_called_once()

    # -- direct accepted identity but missing price -> fallback --

    def test_direct_accepted_identity_missing_price_falls_back(
        self,
        research_run: ResearchRun,
    ) -> None:
        """Direct source with ACCEPTED identity but missing price triggers fallback."""
        # Build a page with explicit MPN but no price
        no_price_html = """
        <html><head>
        <script type="application/ld+json">
        {
          "@context":"https://schema.org",
          "@type":"Product",
          "name":"Test Product",
          "mpn":"MZ-QL23T800",
          "offers":{"@type":"Offer","priceCurrency":"USD"}
        }
        </script></head><body></body></html>
        """
        fake_fetcher = MagicMock(spec=PageFetcher)
        fake_fetcher.fetch.return_value = FetchedPage(
            requested_url="https://example.com",
            final_url="https://example.com",
            retrieved_at=datetime.now(tz=timezone.utc),
            status_code=200,
            body_text=no_price_html,
            content_type="text/html",
            body_byte_count=100,
            redirect_count=0,
            fetcher_id="test",
        )

        with patch.dict(
            os.environ,
            {"PI_PREFERRED_SEARCH_DOMAINS": "directmacro.com"},
        ):
            provider = self._make_serper_fallback_provider()
            result = execute_research_run(
                str(research_run.id),
                search_provider=provider,
                page_fetcher=fake_fetcher,
            )

        # ACCEPTED identity but NO_NUMERIC_PRICE -> zero 4A buckets -> fallback
        provider.search.assert_called_once()

    # -- direct accepted price but unknown condition -> fallback --

    def test_direct_accepted_price_unknown_condition_falls_back(
        self,
        research_run: ResearchRun,
    ) -> None:
        """Direct source with valid price but UNKNOWN condition triggers fallback."""
        # Build a page with explicit MPN + price but no condition
        no_condition_html = """
        <html><head>
        <script type="application/ld+json">
        {
          "@context":"https://schema.org",
          "@type":"Product",
          "name":"Test Product",
          "mpn":"MZ-QL23T800",
          "offers":{"@type":"Offer","price":"100.00","priceCurrency":"USD"}
        }
        </script></head><body></body></html>
        """
        fake_fetcher = MagicMock(spec=PageFetcher)
        fake_fetcher.fetch.return_value = FetchedPage(
            requested_url="https://example.com",
            final_url="https://example.com",
            retrieved_at=datetime.now(tz=timezone.utc),
            status_code=200,
            body_text=no_condition_html,
            content_type="text/html",
            body_byte_count=100,
            redirect_count=0,
            fetcher_id="test",
        )

        with patch.dict(
            os.environ,
            {"PI_PREFERRED_SEARCH_DOMAINS": "directmacro.com"},
        ):
            provider = self._make_serper_fallback_provider()
            result = execute_research_run(
                str(research_run.id),
                search_provider=provider,
                page_fetcher=fake_fetcher,
            )

        # ACCEPTED + price + currency but UNKNOWN condition -> zero 4A buckets
        provider.search.assert_called_once()

    # -- direct sufficient (>= 1 valid 4A bucket) -> NO search --

    def test_direct_sufficient_produces_zero_search_calls(
        self,
        research_run: ResearchRun,
    ) -> None:
        """Direct evidence with >= 1 valid 4A bucket produces ZERO search calls."""
        # Build a page with explicit MPN + price + currency + condition
        sufficient_html = """
        <html><head>
        <script type="application/ld+json">
        {
          "@context":"https://schema.org",
          "@type":"Product",
          "name":"Test Product",
          "mpn":"MZ-QL23T800",
          "offers":{
            "@type":"Offer",
            "price":"100.00",
            "priceCurrency":"USD",
            "itemCondition":"https://schema.org/NewCondition"
          }
        }
        </script></head><body></body></html>
        """
        fake_fetcher = MagicMock(spec=PageFetcher)
        fake_fetcher.fetch.return_value = FetchedPage(
            requested_url="https://example.com",
            final_url="https://example.com",
            retrieved_at=datetime.now(tz=timezone.utc),
            status_code=200,
            body_text=sufficient_html,
            content_type="text/html",
            body_byte_count=100,
            redirect_count=0,
            fetcher_id="test",
        )

        with patch.dict(
            os.environ,
            {"PI_PREFERRED_SEARCH_DOMAINS": "directmacro.com"},
        ):
            provider = self._make_serper_fallback_provider()
            result = execute_research_run(
                str(research_run.id),
                search_provider=provider,
                page_fetcher=fake_fetcher,
            )

        # Direct evidence produces 1 valid 4A bucket -> NO search call
        provider.search.assert_not_called()
        assert result.search_result_count == 0
        assert result.run.current_state == ResearchRunState.COMPLETED
        assert result.price_buckets == 1

    # -- direct-sufficient writes NO SEARCH evidence record --

    def test_direct_sufficient_writes_no_search_evidence(
        self,
        research_run: ResearchRun,
    ) -> None:
        """Direct-sufficient run writes no SEARCH execution-evidence record."""
        sufficient_html = """
        <html><head>
        <script type="application/ld+json">
        {
          "@context":"https://schema.org",
          "@type":"Product",
          "name":"Test Product",
          "mpn":"MZ-QL23T800",
          "offers":{
            "@type":"Offer",
            "price":"100.00",
            "priceCurrency":"USD",
            "itemCondition":"https://schema.org/NewCondition"
          }
        }
        </script></head><body></body></html>
        """
        fake_fetcher = MagicMock(spec=PageFetcher)
        fake_fetcher.fetch.return_value = FetchedPage(
            requested_url="https://example.com",
            final_url="https://example.com",
            retrieved_at=datetime.now(tz=timezone.utc),
            status_code=200,
            body_text=sufficient_html,
            content_type="text/html",
            body_byte_count=100,
            redirect_count=0,
            fetcher_id="test",
        )

        with patch.dict(
            os.environ,
            {"PI_PREFERRED_SEARCH_DOMAINS": "directmacro.com"},
        ):
            provider = self._make_serper_fallback_provider()
            execute_research_run(
                str(research_run.id),
                search_provider=provider,
                page_fetcher=fake_fetcher,
            )

        # Check evidence records
        evidence = research_run.execution_evidence.all()
        search_records = [r for r in evidence if r.stage == ExecutionStage.SEARCH.value]
        assert len(search_records) == 0, (
            f"Direct-sufficient run should have no SEARCH evidence, "
            f"got {len(search_records)}"
        )

    # -- fallback run writes exactly one SEARCH attempt --

    def test_fallback_run_writes_one_search_attempt(
        self,
        research_run: ResearchRun,
    ) -> None:
        """Fallback run writes exactly one SEARCH evidence record."""
        with patch.dict(
            os.environ,
            {"PI_PREFERRED_SEARCH_DOMAINS": "directmacro.com"},
        ):
            provider = self._make_serper_fallback_provider()
            fetcher = self._make_empty_page_fetcher()
            execute_research_run(
                str(research_run.id),
                search_provider=provider,
                page_fetcher=fetcher,
            )

        evidence = research_run.execution_evidence.all()
        search_records = [r for r in evidence if r.stage == ExecutionStage.SEARCH.value]
        assert len(search_records) == 1

    # -- final execution writes exactly one AGGREGATE attempt --

    def test_final_execution_writes_one_aggregate_attempt(
        self,
        research_run: ResearchRun,
    ) -> None:
        """Final execution writes exactly one AGGREGATE evidence record."""
        with patch.dict(
            os.environ,
            {"PI_PREFERRED_SEARCH_DOMAINS": "directmacro.com"},
        ):
            provider = self._make_serper_fallback_provider()
            fetcher = self._make_empty_page_fetcher()
            execute_research_run(
                str(research_run.id),
                search_provider=provider,
                page_fetcher=fetcher,
            )

        evidence = research_run.execution_evidence.all()
        aggregate_records = [
            r for r in evidence if r.stage == ExecutionStage.AGGREGATE.value
        ]
        assert len(aggregate_records) == 1

    # -- lazy Serper construction --

    def test_serper_not_constructed_when_direct_sufficient(
        self,
        research_run: ResearchRun,
    ) -> None:
        """SerperSearchProvider is not constructed when direct evidence is sufficient."""
        sufficient_html = """
        <html><head>
        <script type="application/ld+json">
        {
          "@context":"https://schema.org",
          "@type":"Product",
          "name":"Test Product",
          "mpn":"MZ-QL23T800",
          "offers":{
            "@type":"Offer",
            "price":"100.00",
            "priceCurrency":"USD",
            "itemCondition":"https://schema.org/NewCondition"
          }
        }
        </script></head><body></body></html>
        """
        fake_fetcher = MagicMock(spec=PageFetcher)
        fake_fetcher.fetch.return_value = FetchedPage(
            requested_url="https://example.com",
            final_url="https://example.com",
            retrieved_at=datetime.now(tz=timezone.utc),
            status_code=200,
            body_text=sufficient_html,
            content_type="text/html",
            body_byte_count=100,
            redirect_count=0,
            fetcher_id="test",
        )

        with patch.dict(
            os.environ,
            {"PI_PREFERRED_SEARCH_DOMAINS": "directmacro.com"},
        ):
            # search_provider=None -> lazy construction
            # Direct evidence sufficient -> SerperSearchProvider.from_environment() never called
            result = execute_research_run(
                str(research_run.id),
                search_provider=None,
                page_fetcher=fake_fetcher,
            )

        assert result.run.current_state == ResearchRunState.COMPLETED
        assert result.search_result_count == 0

    def test_serper_not_constructed_when_injected_but_not_needed(
        self,
        research_run: ResearchRun,
    ) -> None:
        """Injected SearchProvider is not called when direct evidence is sufficient."""
        sufficient_html = """
        <html><head>
        <script type="application/ld+json">
        {
          "@context":"https://schema.org",
          "@type":"Product",
          "name":"Test Product",
          "mpn":"MZ-QL23T800",
          "offers":{
            "@type":"Offer",
            "price":"100.00",
            "priceCurrency":"USD",
            "itemCondition":"https://schema.org/NewCondition"
          }
        }
        </script></head><body></body></html>
        """
        fake_fetcher = MagicMock(spec=PageFetcher)
        fake_fetcher.fetch.return_value = FetchedPage(
            requested_url="https://example.com",
            final_url="https://example.com",
            retrieved_at=datetime.now(tz=timezone.utc),
            status_code=200,
            body_text=sufficient_html,
            content_type="text/html",
            body_byte_count=100,
            redirect_count=0,
            fetcher_id="test",
        )

        with patch.dict(
            os.environ,
            {"PI_PREFERRED_SEARCH_DOMAINS": "directmacro.com"},
        ):
            provider = self._make_serper_fallback_provider()
            result = execute_research_run(
                str(research_run.id),
                search_provider=provider,
                page_fetcher=fake_fetcher,
            )

        # Injected provider is still not called
        provider.search.assert_not_called()

    # -- fallback SearchProvider failure retains FAILED semantics --

    def test_fallback_search_provider_failure_causes_failed_run(
        self,
        research_run: ResearchRun,
    ) -> None:
        """Failed fallback SearchProvider causes run to fail."""
        from product_intelligence.providers.search import SearchProviderError

        # Direct acquisition enabled but fetcher fails -> fallback needed.
        # PageFetchError is the classified transport failure: bounded to
        # FETCH_FAILED on the 4D-D authority path, then the search failure
        # below owns the run outcome.
        failing_fetcher = MagicMock(spec=PageFetcher)
        failing_fetcher.fetch.side_effect = PageFetchError("Network error")

        # SearchProvider also fails
        failing_provider = MagicMock(spec=SearchProvider)
        failing_provider.search.side_effect = SearchProviderError("Search failed")

        with patch.dict(
            os.environ,
            {"PI_PREFERRED_SEARCH_DOMAINS": "directmacro.com"},
        ):
            with pytest.raises(ExecutionError, match="Search provider call failed"):
                execute_research_run(
                    str(research_run.id),
                    search_provider=failing_provider,
                    page_fetcher=failing_fetcher,
                )

        research_run.refresh_from_db()
        assert research_run.current_state == ResearchRunState.FAILED

    # -- direct + fallback assessments combined --

    def test_direct_and_fallback_assessments_both_preserved(
        self,
        research_run: ResearchRun,
    ) -> None:
        """Direct + fallback assessments are both preserved in the snapshot."""
        from product_intelligence.research.price_result_codec import (
            decode_price_aggregation_result,
        )

        # DirectMacro fixture (SKU-only, rejected)
        direct_fetcher = self._make_page_fetcher_from_fixture(
            "directmacro_bcm957608_p2200gqf00_search.html",
            "https://directmacro.com/catalogsearch/result/?q=BCM957608-P2200GQF00",
        )

        # Fallback returns a page with explicit MPN
        fallback_html = """
        <html><head>
        <script type="application/ld+json">
        {
          "@context":"https://schema.org",
          "@type":"Product",
          "name":"Fallback Product",
          "mpn":"MZ-QL23T800",
          "offers":{
            "@type":"Offer",
            "price":"200.00",
            "priceCurrency":"USD",
            "itemCondition":"https://schema.org/NewCondition"
          }
        }
        </script></head><body></body></html>
        """

        # Make a page fetcher that returns different pages for different URLs
        def fetch_side_effect(request: PageFetchRequest) -> FetchedPage:
            if "directmacro" in request.url:
                return direct_fetcher.fetch(request)
            return FetchedPage(
                requested_url=request.url,
                final_url=request.url,
                retrieved_at=datetime.now(tz=timezone.utc),
                status_code=200,
                body_text=fallback_html,
                content_type="text/html",
                body_byte_count=100,
                redirect_count=0,
                fetcher_id="test",
            )

        combined_fetcher = MagicMock(spec=PageFetcher)
        combined_fetcher.fetch.side_effect = fetch_side_effect

        # Serper returns one fallback URL
        serper_result = SearchResult(
            source_url="https://fallback.example.com/product",
            title="Fallback Product",
            snippet="Fallback snippet",
        )
        fallback_provider = self._make_serper_fallback_provider((serper_result,))

        with patch.dict(
            os.environ,
            {"PI_PREFERRED_SEARCH_DOMAINS": "directmacro.com"},
        ):
            result = execute_research_run(
                str(research_run.id),
                search_provider=fallback_provider,
                page_fetcher=combined_fetcher,
            )

        # Decode snapshot
        decoded = decode_price_aggregation_result(
            result.snapshot.payload,
            schema_version=result.snapshot.schema_version,
        )

        # Should have assessments from both direct and fallback
        # Direct: 1 SKU-only (REJECTED)
        # Fallback: 1 explicit MPN (ACCEPTED)
        assert len(decoded.assessments) == 2

        # One from DirectMacro (source URL contains directmacro.com)
        direct_assessments = [
            a for a in decoded.assessments
            if "directmacro.com" in a.normalized_listing.observation.source_url
        ]
        assert len(direct_assessments) == 1
        assert direct_assessments[0].decision is EvidenceDecision.REJECTED

        # One from fallback
        fallback_assessments = [
            a for a in decoded.assessments
            if "directmacro.com" not in a.normalized_listing.observation.source_url
        ]
        assert len(fallback_assessments) == 1
        assert fallback_assessments[0].decision is EvidenceDecision.ACCEPTED

    # -- deduplication across direct + fallback --

    def test_same_url_fetched_only_once(self, research_run: ResearchRun) -> None:
        """Same URL from direct and fallback is fetched only once.

        Direct evidence is deliberately 4A-ineligible (SKU-only identity)
        so that fallback fires. The fallback returns the SAME URL.
        ONE shared CandidateDeduplicator across direct + fallback ensures
        only one actual fetch.
        """
        target_url = "https://directmacro.com/catalogsearch/result/?q=MZ-QL23T800"

        # SKU-only page (4A-ineligible: no explicit MPN)
        sku_only_html = """
        <html><head>
        <script type="application/ld+json">
        {
          "@context":"https://schema.org",
          "@type":"Product",
          "name":"Product MZ-QL23T800",
          "sku":"MZ-QL23T800",
          "offers":{
            "@type":"Offer",
            "price":"100.00",
            "priceCurrency":"USD",
            "itemCondition":"https://schema.org/NewCondition"
          }
        }
        </script></head><body></body></html>
        """

        fetch_urls: list[str] = []

        def counting_fetch(request: PageFetchRequest) -> FetchedPage:
            fetch_urls.append(request.url)
            return FetchedPage(
                requested_url=request.url,
                final_url=request.url,
                retrieved_at=datetime.now(tz=timezone.utc),
                status_code=200,
                body_text=sku_only_html,
                content_type="text/html",
                body_byte_count=len(sku_only_html.encode("utf-8")),
                redirect_count=0,
                fetcher_id="test",
            )

        counting_fetcher = MagicMock(spec=PageFetcher)
        counting_fetcher.fetch.side_effect = counting_fetch

        # Serper returns the SAME DirectMacro URL
        serper_result = SearchResult(
            source_url=target_url,
            title="Duplicate URL",
            snippet="Same as direct",
        )
        fallback_provider = self._make_serper_fallback_provider((serper_result,))

        with patch.dict(
            os.environ,
            {"PI_PREFERRED_SEARCH_DOMAINS": "directmacro.com"},
        ):
            result = execute_research_run(
                str(research_run.id),
                search_provider=fallback_provider,
                page_fetcher=counting_fetcher,
            )

        # The SAME URL is fetched exactly once (deduplicated across direct +
        # fallback). The one other fetch is the bounded 4D-D alias-authority
        # fetch of the reviewed Micron 7500 catalog URL (one per
        # direct-insufficient non-empty-MPN run; this SKU-only body bounds it
        # to PARSE_FAILED, which grants no authority and changes no query).
        from product_intelligence.research.micron_packaging_alias import (
            MICRON_7500_REQUESTED_CATALOG_URL,
        )
        assert fetch_urls.count(target_url) == 1
        assert fetch_urls.count(MICRON_7500_REQUESTED_CATALOG_URL) == 1
        assert len(fetch_urls) == 2

        # Fallback DID occur because SKU-only = zero 4A buckets
        fallback_provider.search.assert_called_once()

    # -- Machine Price remains deterministic ACCEPTED-only --

    def test_machine_price_remains_deterministic_accepted_only(
        self,
        research_run: ResearchRun,
    ) -> None:
        """Machine Price aggregation includes only ACCEPTED assessments."""
        from product_intelligence.research.price_result_codec import (
            decode_price_aggregation_result,
        )

        # DirectMacro fixture (SKU-only, rejected by 3C)
        direct_fetcher = self._make_page_fetcher_from_fixture(
            "directmacro_bcm957608_p2200gqf00_search.html",
            "https://directmacro.com/catalogsearch/result/?q=BCM957608-P2200GQF00",
        )

        with patch.dict(
            os.environ,
            {"PI_PREFERRED_SEARCH_DOMAINS": "directmacro.com"},
        ):
            # No fallback results (empty Serper)
            provider = self._make_serper_fallback_provider()
            result = execute_research_run(
                str(research_run.id),
                search_provider=provider,
                page_fetcher=direct_fetcher,
            )

        decoded = decode_price_aggregation_result(
            result.snapshot.payload,
            schema_version=result.snapshot.schema_version,
        )

        # Zero price buckets (SKU-only rejected by 3C)
        assert len(decoded.buckets) == 0
        # The rejected assessment is excluded for IDENTITY_NOT_ACCEPTED
        identity_exclusions = [
            e for e in decoded.exclusions
            if e.reason is PriceAggregationExclusionReason.IDENTITY_NOT_ACCEPTED
        ]
        assert len(identity_exclusions) >= 1


# ---------------------------------------------------------------------------
# Section 6: Blocker 1 — 4A contract errors must propagate
# ---------------------------------------------------------------------------


class Test4AContractErrorPropagation:
    """Regression: _has_valid_4a_buckets must NOT swallow 4A contract errors."""

    def _make_serper_fallback_provider(
        self, results: tuple = (),
    ) -> MagicMock:
        """Build a fake SearchProvider."""
        from datetime import datetime, timezone
        from unittest.mock import MagicMock
        from product_intelligence.providers.search import (
            SearchProvider,
            SearchQuery,
            SearchResponse,
        )
        provider = MagicMock(spec=SearchProvider)
        provider.search.return_value = SearchResponse(
            provider_id="test",
            query=SearchQuery(text="test"),
            retrieved_at=datetime.now(tz=timezone.utc),
            results=results,
        )
        return provider

    def test_4a_duplicate_assessment_error_propagates(
        self,
        research_run: ResearchRun,
    ) -> None:
        """Exact duplicate assessments provoke a 4A ValueError that propagates.

        aggregate_listing_prices rejects exact duplicate input assessments with
        ValueError. This is a programming/contract failure and MUST propagate to
        the outer catastrophic boundary — it must NOT trigger Serper fallback,
        consume a paid search credit, or be reclassified as "insufficient".
        """
        from product_intelligence.research.extraction import (
            extract_listing_observations,
        )
        from product_intelligence.research.normalization import (
            normalize_listing_observation,
        )
        from product_intelligence.research.matching import (
            assess_listing_identity,
        )
        from product_intelligence.research.aggregation import (
            aggregate_listing_prices,
        )

        # Build two identical assessments from a valid listing
        sufficient_html = """
        <html><head>
        <script type="application/ld+json">
        {
          "@context":"https://schema.org",
          "@type":"Product",
          "name":"Test Product",
          "mpn":"MZ-QL23T800",
          "offers":{
            "@type":"Offer",
            "price":"100.00",
            "priceCurrency":"USD",
            "itemCondition":"https://schema.org/NewCondition"
          }
        }
        </script></head><body></body></html>
        """
        observations = extract_listing_observations(
            sufficient_html,
            source_url="https://example.com/product",
        )
        assert len(observations) == 1
        normalized = normalize_listing_observation(observations[0])
        request = ResearchRequest(
            manufacturer_part_number="MZ-QL23T800",
            description="Test product",
        )
        assessment = assess_listing_identity(request, normalized)
        assert assessment.decision.name == "ACCEPTED"

        # Feed two identical assessments to aggregate_listing_prices
        # This MUST raise ValueError (exact duplicates)
        with pytest.raises(ValueError, match="duplicate"):
            aggregate_listing_prices(request, (assessment, assessment))

    def test_4a_contract_failure_terminalizes_run(
        self,
        research_run: ResearchRun,
    ) -> None:
        """A 4A contract failure during preliminary bucket check propagates.

        When _has_valid_4a_buckets receives assessments that trigger a
        ValueError in the 4A primitive, the error MUST propagate to the
        outer catastrophic boundary. SearchProvider.search() is NOT called.
        """
        # Build a page that extracts one valid listing
        sufficient_html = """
        <html><head>
        <script type="application/ld+json">
        {
          "@context":"https://schema.org",
          "@type":"Product",
          "name":"Test Product",
          "mpn":"MZ-QL23T800",
          "offers":{
            "@type":"Offer",
            "price":"100.00",
            "priceCurrency":"USD",
            "itemCondition":"https://schema.org/NewCondition"
          }
        }
        </script></head><body></body></html>
        """

        # A fetcher that returns the SAME page for every URL
        def always_same(request: PageFetchRequest) -> FetchedPage:
            return FetchedPage(
                requested_url=request.url,
                final_url=request.url,
                retrieved_at=datetime.now(tz=timezone.utc),
                status_code=200,
                body_text=sufficient_html,
                content_type="text/html",
                body_byte_count=len(sufficient_html.encode("utf-8")),
                redirect_count=0,
                fetcher_id="test",
            )

        fake_fetcher = MagicMock(spec=PageFetcher)
        fake_fetcher.fetch.side_effect = always_same

        # Fallback provider (should NOT be called)
        fallback_provider = self._make_serper_fallback_provider()

        # We need to provoke a duplicate assessment through the pipeline.
        # The deduplication layer (_deduplicate_exact_observations) removes
        # exact structural duplicates from the SAME URL's extraction.
        # To get duplicates into _has_valid_4a_buckets, we need direct
        # acquisition to produce an assessment AND fallback to produce
        # the SAME assessment value.
        # This is actually the cross-source dedup case: if dedup fails,
        # duplicates would hit 4A. But the dedup layer prevents this.
        # So the contract failure is really about the try/except removal:
        # if 4A ever raises ValueError, it propagates. This test proves
        # the ValueError IS propagated by showing the run fails.

        with patch.dict(
            os.environ,
            {"PI_PREFERRED_SEARCH_DOMAINS": "directmacro.com"},
        ):
            with patch(
                "product_intelligence.execution.orchestration.aggregate_listing_prices"
            ) as mock_aggregate:
                # Simulate a 4A contract failure during the preliminary check
                mock_aggregate.side_effect = ValueError(
                    "one or more assessments are exact duplicates"
                )

                with pytest.raises(ExecutionError):
                    execute_research_run(
                        str(research_run.id),
                        search_provider=fallback_provider,
                        page_fetcher=fake_fetcher,
                    )

        # SearchProvider.search() was NOT called
        fallback_provider.search.assert_not_called()

        research_run.refresh_from_db()
        assert research_run.current_state == ResearchRunState.FAILED


class TestSameUrlFetchedOnlyOnce:
    """Blocker 3: Cross-source dedup must exercise fallback path.

    The original test_same_url_fetched_only_once did NOT exercise fallback
    because its direct page already produced a valid 4A bucket.
    """

    def test_same_url_from_direct_and_fallback_fetched_once(
        self,
        research_run: ResearchRun,
    ) -> None:
        """Direct SKU-only evidence falls back; same URL deduplicated.

        Constructs direct evidence at the DirectMacro URL that is
        deliberately 4A-ineligible (SKU-only identity). Fallback MUST
        occur. The injected SearchProvider returns the EXACT SAME
        DirectMacro URL. Assert dedup works.
        """
        target_url = (
            "https://directmacro.com/catalogsearch/result/?q=MZ-QL23T800"
        )

        # SKU-only page (4A-ineligible: no explicit MPN)
        sku_only_html = """
        <html><head>
        <script type="application/ld+json">
        {
          "@context":"https://schema.org",
          "@type":"Product",
          "name":"Product MZ-QL23T800",
          "sku":"MZ-QL23T800",
          "offers":{
            "@type":"Offer",
            "price":"100.00",
            "priceCurrency":"USD",
            "itemCondition":"https://schema.org/NewCondition"
          }
        }
        </script></head><body></body></html>
        """

        fetch_urls: list[str] = []

        def counting_fetch(request: PageFetchRequest) -> FetchedPage:
            fetch_urls.append(request.url)
            return FetchedPage(
                requested_url=request.url,
                final_url=request.url,
                retrieved_at=datetime.now(tz=timezone.utc),
                status_code=200,
                body_text=sku_only_html,
                content_type="text/html",
                body_byte_count=len(sku_only_html.encode("utf-8")),
                redirect_count=0,
                fetcher_id="test",
            )

        counting_fetcher = MagicMock(spec=PageFetcher)
        counting_fetcher.fetch.side_effect = counting_fetch

        # Serper returns the SAME DirectMacro URL
        serper_result = SearchResult(
            source_url=target_url,
            title="Duplicate URL from Serper",
            snippet="Same as direct",
        )
        fallback_provider = MagicMock(spec=SearchProvider)
        fallback_provider.search.return_value = SearchResponse(
            provider_id="test",
            query=SearchQuery(text="test"),
            retrieved_at=datetime.now(tz=timezone.utc),
            results=(serper_result,),
        )

        with patch.dict(
            os.environ,
            {"PI_PREFERRED_SEARCH_DOMAINS": "directmacro.com"},
        ):
            result = execute_research_run(
                str(research_run.id),
                search_provider=fallback_provider,
                page_fetcher=counting_fetcher,
            )

        # The SAME URL is fetched exactly once (deduplicated across direct +
        # fallback). The one other fetch is the bounded 4D-D alias-authority
        # fetch of the reviewed Micron 7500 catalog URL (one per
        # direct-insufficient non-empty-MPN run; this SKU-only body bounds it
        # to PARSE_FAILED, which grants no authority and changes no query).
        from product_intelligence.research.micron_packaging_alias import (
            MICRON_7500_REQUESTED_CATALOG_URL,
        )
        assert fetch_urls.count(target_url) == 1
        assert fetch_urls.count(MICRON_7500_REQUESTED_CATALOG_URL) == 1
        assert len(fetch_urls) == 2

        # Fallback DID occur (SKU-only = zero 4A buckets)
        fallback_provider.search.assert_called_once()

        # Check evidence records
        evidence = research_run.execution_evidence.all()
        # One FETCH SUCCESS (the actual fetch)
        fetch_records = [
            r for r in evidence
            if r.stage == ExecutionStage.FETCH.value
        ]
        success_fetches = [
            r for r in fetch_records
            if r.outcome == ExecutionOutcome.SUCCESS.value
        ]
        assert len(success_fetches) == 1
        # One FETCH SKIPPED (the duplicate)
        skipped_fetches = [
            r for r in fetch_records
            if r.outcome == ExecutionOutcome.SKIPPED.value
        ]
        assert len(skipped_fetches) == 1

        # Run completed
        assert result.run.current_state == ResearchRunState.COMPLETED


# ---------------------------------------------------------------------------
# Section 8: Blocker 4 — Lazy Serper / no-key contract
# ---------------------------------------------------------------------------


class TestLazySerperNoKeyContract:
    """Prove real lazy Serper construction with no SERPER_API_KEY."""

    def _make_sufficient_fetcher(self) -> PageFetcher:
        """Page fetcher returning a valid 4A bucket."""
        sufficient_html = """
        <html><head>
        <script type="application/ld+json">
        {
          "@context":"https://schema.org",
          "@type":"Product",
          "name":"Test Product",
          "mpn":"MZ-QL23T800",
          "offers":{
            "@type":"Offer",
            "price":"100.00",
            "priceCurrency":"USD",
            "itemCondition":"https://schema.org/NewCondition"
          }
        }
        </script></head><body></body></html>
        """
        fake_fetcher = MagicMock(spec=PageFetcher)
        fake_fetcher.fetch.return_value = FetchedPage(
            requested_url="https://example.com",
            final_url="https://example.com",
            retrieved_at=datetime.now(tz=timezone.utc),
            status_code=200,
            body_text=sufficient_html,
            content_type="text/html",
            body_byte_count=len(sufficient_html.encode("utf-8")),
            redirect_count=0,
            fetcher_id="test",
        )
        return fake_fetcher

    def test_direct_sufficient_no_serper_construction(
        self,
        research_run: ResearchRun,
    ) -> None:
        """Direct-sufficient run: SerperSearchProvider.from_environment NOT called.

        During the test:
        - PI_PREFERRED_SEARCH_DOMAINS includes directmacro.com
        - SERPER_API_KEY is removed from environment
        - search_provider=None
        - direct evidence produces a valid 4A bucket

        Assert:
        - from_environment NOT called
        - run COMPLETED
        - search_result_count == 0
        - zero SEARCH evidence
        """
        # Build env with direct acquisition enabled but no SERPER_API_KEY
        env_copy = dict(os.environ)
        env_copy["PI_PREFERRED_SEARCH_DOMAINS"] = "directmacro.com"
        env_copy.pop("SERPER_API_KEY", None)

        with patch.dict(os.environ, env_copy, clear=True):
            with patch(
                "product_intelligence.providers.serper.SerperSearchProvider.from_environment"
            ) as mock_from_env:
                # If called, raise an error to make the test fail loudly
                mock_from_env.side_effect = RuntimeError(
                    "SerperSearchProvider.from_environment() was called "
                    "but direct evidence was sufficient"
                )

                result = execute_research_run(
                    str(research_run.id),
                    search_provider=None,
                    page_fetcher=self._make_sufficient_fetcher(),
                )

        # from_environment was NOT called
        mock_from_env.assert_not_called()

        # Run completed
        assert result.run.current_state == ResearchRunState.COMPLETED
        assert result.search_result_count == 0

        # Zero SEARCH evidence
        evidence = research_run.execution_evidence.all()
        search_records = [
            r for r in evidence
            if r.stage == ExecutionStage.SEARCH.value
        ]
        assert len(search_records) == 0

    def test_direct_insufficient_lazy_serper_construction(
        self,
        research_run: ResearchRun,
    ) -> None:
        """Direct-insufficient: from_environment called exactly once.

        Direct evidence insufficient.
        search_provider=None.
        Patch from_environment to return a fake SearchProvider.
        """
        # Empty page -> no direct assessments -> fallback needed
        empty_fetcher = MagicMock(spec=PageFetcher)
        empty_fetcher.fetch.return_value = FetchedPage(
            requested_url="https://example.com",
            final_url="https://example.com",
            retrieved_at=datetime.now(tz=timezone.utc),
            status_code=200,
            body_text="<html><body>No listings</body></html>",
            content_type="text/html",
            body_byte_count=35,
            redirect_count=0,
            fetcher_id="test",
        )

        # Fake search provider to be returned by from_environment
        fake_provider = MagicMock(spec=SearchProvider)
        fake_provider.search.return_value = SearchResponse(
            provider_id="fake",
            query=SearchQuery(text="test"),
            retrieved_at=datetime.now(tz=timezone.utc),
            results=(),
        )

        # Remove SERPER_API_KEY from env
        env_copy = dict(os.environ)
        env_copy.pop("SERPER_API_KEY", None)
        env_copy["PI_PREFERRED_SEARCH_DOMAINS"] = "directmacro.com"

        with patch.dict(os.environ, env_copy, clear=True):
            with patch(
                "product_intelligence.providers.serper.SerperSearchProvider.from_environment",
                return_value=fake_provider,
            ) as mock_from_env:
                result = execute_research_run(
                    str(research_run.id),
                    search_provider=None,
                    page_fetcher=empty_fetcher,
                )

        # from_environment called exactly once
        mock_from_env.assert_called_once()
        # fake provider.search called exactly once
        fake_provider.search.assert_called_once()

        # Run completed
        assert result.run.current_state == ResearchRunState.COMPLETED
        assert result.search_result_count == 0

        # Exactly one SEARCH evidence record (ZERO_RESULTS)
        evidence = research_run.execution_evidence.all()
        search_records = [
            r for r in evidence
            if r.stage == ExecutionStage.SEARCH.value
        ]
        assert len(search_records) == 1


# ---------------------------------------------------------------------------
# Section 9: Blocker 5 — Direct semantic / human-review authority
# ---------------------------------------------------------------------------


class TestDirectSemanticAuthority:
    """Direct-source unresolved evidence uses semantic/human-review path
    WITHOUT changing Machine Price authority.

    These tests run through execute_research_run and intercept semantic
    integration using the established test patterns from
    tests/execution/test_semantic_integration.py.
    """

    def test_direct_sku_only_assessment_enters_semantic_integration(
        self,
        research_run: ResearchRun,
    ) -> None:
        """DirectMacro SKU-only assessment:
        - runs through execute_research_run
        - the direct-source ListingIdentityAssessment is frozen-3C REJECTED
        - that exact direct assessment is included in assessments passed to
          evaluate_semantic_matches
        - semantic evaluation does not mutate the deterministic EvidenceDecision
        - Machine Price still excludes it
        """
        from product_intelligence.research.aggregation import aggregate_listing_prices
        from product_intelligence.runs.models import ResearchRun as RR
        from product_intelligence.execution.semantic_integration import (
            evaluate_semantic_matches,
        )

        # Use the DirectMacro fixture (SKU-only -> REJECTED)
        direct_fetcher = self._make_page_fetcher_from_fixture(
            "directmacro_bcm957608_p2200gqf00_search.html",
            "https://directmacro.com/catalogsearch/result/?q=BCM957608-P2200GQF00",
        )

        # Empty fallback provider (direct SKU-only won't produce 4A bucket)
        fallback_provider = self._make_serper_fallback_provider()

        # Intercept evaluate_semantic_matches to spy on what assessments
        # are passed to it
        captured_assessments = []

        def spy_semantic_integration(
            request, assessments, evidence_writer, runtime=None
        ):
            captured_assessments.extend(assessments)
            # Return empty results (no semantic runtime configured)
            return ()

        with patch(
            "product_intelligence.execution.orchestration.evaluate_semantic_matches",
            side_effect=spy_semantic_integration,
        ):
            with patch.dict(
                os.environ,
                {"PI_PREFERRED_SEARCH_DOMAINS": "directmacro.com"},
            ):
                result = execute_research_run(
                    str(research_run.id),
                    search_provider=fallback_provider,
                    page_fetcher=direct_fetcher,
                )

        # Run completed
        assert result.run.current_state == ResearchRunState.COMPLETED

        # evaluate_semantic_matches was called with the direct-source assessment
        assert len(captured_assessments) == 1
        direct_assessment = captured_assessments[0]

        # The direct assessment is frozen-3C REJECTED
        assert direct_assessment.decision is EvidenceDecision.REJECTED
        assert (
            direct_assessment.rejection_reason
            is IdentityRejectionReason.NO_EXPLICIT_MPN_EVIDENCE
        )
        assert direct_assessment.candidate_evidence_source is EvidenceSource.SKU_FIELD

        # Machine Price excludes it (4A IDENTITY_NOT_ACCEPTED)
        agg = aggregate_listing_prices(
            research_run.to_research_request(),
            (direct_assessment,),
        )
        assert len(agg.buckets) == 0

        # Zero search calls (direct was the only source, fallback was empty)
        # Actually fallback DID fire because SKU-only = zero 4A buckets
        fallback_provider.search.assert_called_once()

    def test_ai_assisted_match_creates_review_candidate_not_machine_price(
        self,
        research_run: ResearchRun,
    ) -> None:
        """AI-assisted MATCH from a direct-source eligible REJECTED assessment:
        - AiAssistedReviewCandidate is actually persisted
        - original deterministic assessment remains REJECTED
        - Machine Price buckets do NOT gain that assessment
        - human-review authority remains Reviewed Price only
        """
        import hashlib
        from product_intelligence.research.aggregation import aggregate_listing_prices
        from product_intelligence.runs.models import (
            AiAssistedReviewCandidate,
            PriceIntelligenceSnapshot,
        )
        from product_intelligence.execution.semantic_integration import (
            AiAssistedMatchResult,
        )
        from product_intelligence.semantic import (
            ConfidenceLevel,
            SemanticDecision,
            SemanticRuntimeResult,
        )

        # DirectMacro fixture (SKU-only -> REJECTED, semantic-eligible)
        direct_fetcher = self._make_page_fetcher_from_fixture(
            "directmacro_bcm957608_p2200gqf00_search.html",
            "https://directmacro.com/catalogsearch/result/?q=BCM957608-P2200GQF00",
        )

        # Build the fake semantic response for the DirectMacro assessment
        url = "https://directmacro.com/catalogsearch/result/?q=BCM957608-P2200GQF00"
        url_hash = hashlib.sha256(url.encode()).hexdigest()[:8]
        case_id = f"candidate-{url_hash}-0"

        response_json = (
            '{'
            f'"decision": "{SemanticDecision.MATCH.value}", '
            '"confidence": "HIGH", '
            '"matched_attributes": ["brand"], '
            '"conflicting_attributes": [], '
            '"missing_critical_attributes": [], '
            '"reason_code": "brand_sku_match"'
            '}'
        )

        from product_intelligence.semantic import (
            SemanticRuntime,
            SemanticRuntimeConfig,
        )
        from product_intelligence.semantic.transport import FakeSemanticModelTransport

        transport = FakeSemanticModelTransport(
            responses={case_id: response_json},
            case_ids=(case_id,),
            provider_reported_model="nemotron-3-super",
        )
        fake_runtime = SemanticRuntime(config=SemanticRuntimeConfig(), primary_transport=transport)

        # Patch get_default_runtime so semantic integration uses our fake
        fallback_provider = self._make_serper_fallback_provider()

        with patch(
            "product_intelligence.execution.semantic_integration.get_default_runtime",
            return_value=fake_runtime,
        ):
            with patch.dict(
                os.environ,
                {"PI_PREFERRED_SEARCH_DOMAINS": "directmacro.com"},
            ):
                result = execute_research_run(
                    str(research_run.id),
                    search_provider=fallback_provider,
                    page_fetcher=direct_fetcher,
                )

        # Run completed
        assert result.run.current_state == ResearchRunState.COMPLETED

        # AiAssistedReviewCandidate was persisted
        candidates = AiAssistedReviewCandidate.objects.filter(run=research_run)
        assert candidates.count() == 1

        candidate = candidates.first()
        assert candidate is not None
        # Candidate points to the direct-source assessment
        assert "directmacro.com" in candidate.source_url

        # The original deterministic assessment remains REJECTED
        # (semantic MATCH is advisory, never mutates deterministic decision)
        assert result.ai_assisted_match_count == 1
        match_result = result.ai_assisted_matches[0]
        assert match_result.original_assessment.decision is EvidenceDecision.REJECTED

        # Machine Price does NOT gain the assessment
        decoded = self._decode_snapshot(result.snapshot)
        assert len(decoded.buckets) == 0

        # No ACCEPTED assessments
        assert sum(
            1 for a in decoded.assessments
            if a.decision is EvidenceDecision.ACCEPTED
        ) == 0

    # Helper methods (same pattern as TestDirectAcquisitionExecution)

    def _make_page_fetcher_from_fixture(
        self, fixture_name: str, url: str,
    ) -> PageFetcher:
        """Build a fake PageFetcher returning a real fixture."""
        fixture_path = Path(__file__).resolve().parents[1] / "fixtures" / "pages" / fixture_name
        html = fixture_path.read_text(encoding="utf-8")

        fake_fetcher = MagicMock(spec=PageFetcher)
        fake_fetcher.fetch.return_value = FetchedPage(
            requested_url=url,
            final_url=url,
            retrieved_at=datetime.now(tz=timezone.utc),
            status_code=200,
            body_text=html,
            content_type="text/html",
            body_byte_count=len(html.encode("utf-8")),
            redirect_count=0,
            fetcher_id="test",
        )
        return fake_fetcher

    def _make_serper_fallback_provider(
        self, results: tuple = (),
    ) -> MagicMock:
        """Build a fake SearchProvider returning specified results."""
        provider = MagicMock(spec=SearchProvider)
        provider.search.return_value = SearchResponse(
            provider_id="test",
            query=SearchQuery(text="test"),
            retrieved_at=datetime.now(tz=timezone.utc),
            results=results,
        )
        return provider

    def _decode_snapshot(self, snapshot) -> object:
        """Decode a PriceIntelligenceSnapshot payload."""
        from product_intelligence.research.price_result_codec import (
            decode_price_aggregation_result,
        )
        return decode_price_aggregation_result(
            snapshot.payload,
            schema_version=snapshot.schema_version,
        )


class TestExtractObservationCountSemantics:
    """extract_observation_count reflects extracted observations, not assessments.

    extract_observation_count increments by len(unique_listings) after successful
    extraction/dedupe, BEFORE normalization/matching can drop a listing.
    A later normalization or matching failure must NOT retroactively erase the fact
    that an observation was extracted.
    """

    def test_extract_observation_count_survives_matching_failure(
        self,
        research_run: ResearchRun,
    ) -> None:
        """extract_observation_count = 1 even when matching drops the observation.

        Scenario:
        - extraction successfully produces exactly 1 unique ListingObservation
        - matching primitive is patched to return empty assessments
        - final assessments from that URL = 0
        - extract_observation_count MUST still equal 1

        This test FAILS against the old FU0 implementation:
            extract_observation_count = len(total_assessments)
        because total_assessments would be 0 but extract_observation_count is 1.
        """
        # Page that extracts exactly 1 valid listing (with explicit MPN)
        product_html = """
        <html><head>
        <script type="application/ld+json">
        {
          "@context":"https://schema.org",
          "@type":"Product",
          "name":"Product MZ-QL23T800",
          "mpn":"MZ-QL23T800",
          "offers":{
            "@type":"Offer",
            "price":"100.00",
            "priceCurrency":"USD",
            "itemCondition":"https://schema.org/NewCondition"
          }
        }
        </script></head><body></body></html>
        """
        fake_fetcher = MagicMock(spec=PageFetcher)
        fake_fetcher.fetch.return_value = FetchedPage(
            requested_url="https://example.com",
            final_url="https://example.com",
            retrieved_at=datetime.now(tz=timezone.utc),
            status_code=200,
            body_text=product_html,
            content_type="text/html",
            body_byte_count=len(product_html.encode("utf-8")),
            redirect_count=0,
            fetcher_id="test",
        )

        # Empty fallback provider
        fallback_provider = MagicMock(spec=SearchProvider)
        fallback_provider.search.return_value = SearchResponse(
            provider_id="test",
            query=SearchQuery(text="test"),
            retrieved_at=datetime.now(tz=timezone.utc),
            results=(),
        )

        # Patch matching to return empty assessments
        with patch(
            "product_intelligence.execution.matching.assess_identity",
            return_value=([], "NO_LISTINGS"),
        ):
            with patch.dict(
                os.environ,
                {"PI_PREFERRED_SEARCH_DOMAINS": "directmacro.com"},
            ):
                result = execute_research_run(
                    str(research_run.id),
                    search_provider=fallback_provider,
                    page_fetcher=fake_fetcher,
                )

        # extract_observation_count = 1 (one observation was extracted)
        # even though matching returned 0 assessments
        assert result.extract_observation_count == 1

        # FETCH succeeded
        assert result.fetch_success_count >= 1

        # No assessments because matching was patched to return empty
        assert result.accepted_assessment_count == 0

        # Zero buckets because no assessments
        assert result.price_buckets == 0

        # Verify evidence records show successful EXTRACT
        evidence = research_run.execution_evidence.all()
        extract_records = [
            r for r in evidence
            if r.stage == ExecutionStage.EXTRACT.value
            and r.outcome == ExecutionOutcome.SUCCESS.value
        ]
        assert len(extract_records) >= 1
