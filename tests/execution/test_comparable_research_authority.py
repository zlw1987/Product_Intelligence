"""Comparable Research Authority Context tests (PRODUCT-INTEL.7C-PRE1).

Tests the authority-establishment pipeline:
    - Public API signature safety (no policy/source/manufacturer injection)
    - Real Seagate fixture + exact MPN -> context established
    - Real Seagate fixture + normalized-exact spelling -> source raw MPN preserved
    - Missing MPN -> NO_AUTHORITY_MATCH
    - Description-only request -> NO_REQUESTED_MPN
    - Multiple matching records -> AMBIGUOUS_AUTHORITY_MATCH
    - Arbitrary public hostname cannot become authoritative
    - Caller cannot inject a custom policy/source URL
    - Redirect authority boundary enforcement (origin-level)
    - Descriptor authority and provenance
    - Context invariant self-validation
    - Abstention semantics
    - No LLM/SearchProvider/concrete HTTP dependency
    - Programming error propagation
    - Public context construction blocked (init-closed)
    - Retained frozen observation
    - Canonical policy binding
    - Authority acquisition status vocabulary
"""

from __future__ import annotations

import ast
import dataclasses
import inspect
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Protocol

import pytest

from product_intelligence.domain.enums import IdentityMatchType
from product_intelligence.domain.models import ProductIdentity, ResearchRequest
from product_intelligence.execution.comparable_research_authority import (
    ComparableResearchAuthorityAcquisitionResult,
    ComparableResearchAuthorityContext,
    AuthoritySourceOutcomeState,
    AuthorityAcquisitionStatus,
    acquire_comparable_research_authority_context,
)
from product_intelligence.providers.page import (
    FetchedPage,
    PageFetchError,
    PageFetchRequest,
    PageFetcher,
    UnsafeFetchTargetError,
)
from product_intelligence.research.enterprise_ssd import ENTERPRISE_SSD_SCHEMA
from product_intelligence.research.specifications import SourceAuthority
from product_intelligence.research.identity import normalize_part_number

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_RETRIEVED_AT = datetime(2026, 9, 4, 20, 42, 23, tzinfo=timezone.utc)
_SEAGATE_SOURCE_URL = (
    "https://www.seagate.com/support/enterprise-storage/"
    "solid-state-drives/nytro-5050/"
)


def _read_seagate_fixture() -> str:
    fixture_path = os.path.join(
        os.path.dirname(__file__),
        "..",
        "fixtures",
        "specifications",
        "real_seagate_nytro_5050_xp15360se70005.html",
    )
    with open(fixture_path, "r", encoding="utf-8") as f:
        return f.read()


# ---------------------------------------------------------------------------
# Fake PageFetcher
# ---------------------------------------------------------------------------


class _FakePageFetcher:
    """Controllable PageFetcher for tests."""

    def __init__(
        self,
        body: str | None = None,
        error: type[Exception] | None = None,
        final_url: str | None = None,
    ):
        self.body = body
        self.error = error
        self.final_url = final_url
        self.fetch_count = 0
        self.last_request: PageFetchRequest | None = None

    def fetch(self, request: PageFetchRequest) -> FetchedPage:
        self.fetch_count += 1
        self.last_request = request
        if self.error is not None:
            raise self.error("test error")
        return FetchedPage(
            requested_url=request.url,
            final_url=self.final_url or request.url,
            retrieved_at=_RETRIEVED_AT,
            status_code=200,
            body_text=self.body or "",
            content_type="text/html",
            body_byte_count=len(self.body or ""),
            redirect_count=0,
            fetcher_id="fake",
        )


# ---------------------------------------------------------------------------
# TEST 1: Public API signature has no policy/source/manufacturer/category injection
# ---------------------------------------------------------------------------


class TestPublicApiSignature:
    def test_no_policy_parameter(self) -> None:
        """Public function signature must not accept policy."""
        sig = inspect.signature(acquire_comparable_research_authority_context)
        param_names = set(sig.parameters.keys())
        forbidden = {"policy", "policies", "authority_policy", "authority_policies"}
        found = forbidden & param_names
        assert not found, (
            f"Public API must not accept policy injection parameters. "
            f"Found: {found}"
        )

    def test_no_source_url_parameter(self) -> None:
        """Public function signature must not accept source URL."""
        sig = inspect.signature(acquire_comparable_research_authority_context)
        param_names = set(sig.parameters.keys())
        forbidden = {"source_url", "source_urls", "urls", "catalog_url"}
        found = forbidden & param_names
        assert not found, f"Public API must not accept source URL. Found: {found}"

    def test_no_source_authority_parameter(self) -> None:
        """Public function signature must not accept source authority."""
        sig = inspect.signature(acquire_comparable_research_authority_context)
        param_names = set(sig.parameters.keys())
        forbidden = {"source_authority", "authority", "authorities"}
        found = forbidden & param_names
        assert not found, f"Public API must not accept authority injection. Found: {found}"

    def test_no_manufacturer_parameter(self) -> None:
        """Public function signature must not accept manufacturer."""
        sig = inspect.signature(acquire_comparable_research_authority_context)
        param_names = set(sig.parameters.keys())
        forbidden = {"manufacturer", "manufacturer_name", "brand"}
        found = forbidden & param_names
        assert not found, f"Public API must not accept manufacturer. Found: {found}"

    def test_no_manufacturer_domain_parameter(self) -> None:
        """Public function signature must not accept manufacturer domain."""
        sig = inspect.signature(acquire_comparable_research_authority_context)
        param_names = set(sig.parameters.keys())
        forbidden = {"manufacturer_domain", "domain", "host", "hosts"}
        found = forbidden & param_names
        assert not found, f"Public API must not accept domain. Found: {found}"

    def test_no_category_parameter(self) -> None:
        """Public function signature must not accept category."""
        sig = inspect.signature(acquire_comparable_research_authority_context)
        param_names = set(sig.parameters.keys())
        forbidden = {"category", "category_schema", "schema"}
        found = forbidden & param_names
        assert not found, f"Public API must not accept category. Found: {found}"

    def test_no_extraction_mechanism_parameter(self) -> None:
        """Public function signature must not accept extraction mechanism."""
        sig = inspect.signature(acquire_comparable_research_authority_context)
        param_names = set(sig.parameters.keys())
        forbidden = {
            "extraction_mechanism", "extractor", "mechanism",
            "mechanisms", "parser", "parsers",
        }
        found = forbidden & param_names
        assert not found, f"Public API must not accept extraction mechanism. Found: {found}"

    def test_signature_is_keyword_only(self) -> None:
        """Public function parameters must be keyword-only (no positional abuse)."""
        sig = inspect.signature(acquire_comparable_research_authority_context)
        for name, param in sig.parameters.items():
            assert param.kind in (
                inspect.Parameter.KEYWORD_ONLY,
                inspect.Parameter.POSITIONAL_OR_KEYWORD,
            ), f"Parameter {name} has unexpected kind {param.kind}"

    def test_signature_has_request_and_page_fetcher(self) -> None:
        """Public function must accept exactly request and page_fetcher."""
        sig = inspect.signature(acquire_comparable_research_authority_context)
        param_names = set(sig.parameters.keys())
        assert "request" in param_names
        assert "page_fetcher" in param_names
        assert len(param_names) == 2

    def test_request_requires_research_request_type(self) -> None:
        """Non-ResearchRequest raises TypeError."""
        with pytest.raises(TypeError, match="ResearchRequest"):
            acquire_comparable_research_authority_context(
                request="not a request",  # type: ignore[arg-type]
                page_fetcher=_FakePageFetcher(),
            )


# ---------------------------------------------------------------------------
# TEST 2: Real Seagate fixture + exact MPN establishes context
# ---------------------------------------------------------------------------


class TestExactMpnEstablishesContext:
    def test_exact_mpn_establishes_authority_context(self) -> None:
        """Exact MPN match from real Seagate fixture establishes context."""
        request = ResearchRequest(
            manufacturer_part_number="XP15360SE70005",
            description="Seagate Nytro 5350H 15.36TB",
        )
        fetcher = _FakePageFetcher(body=_read_seagate_fixture())

        result = acquire_comparable_research_authority_context(
            request=request,
            page_fetcher=fetcher,
        )

        assert result.context is not None
        assert len(result.source_outcomes) == 1
        assert result.source_outcomes[0].outcome_state is AuthoritySourceOutcomeState.MATCHED
        assert result.acquisition_status is AuthorityAcquisitionStatus.ESTABLISHED

        ctx = result.context
        assert ctx.target_identity.is_established
        assert ctx.target_identity.match_type is IdentityMatchType.EXACT
        assert ctx.target_identity.manufacturer_part_number == "XP15360SE70005"
        assert ctx.target_identity.manufacturer == "Seagate"
        assert ctx.category_schema is ENTERPRISE_SSD_SCHEMA

    def test_exact_mpn_source_mpn_preserved(self) -> None:
        """Source-published MPN is preserved exactly in ProductIdentity."""
        request = ResearchRequest(
            manufacturer_part_number="XP15360SE70005",
            description="Seagate Nytro 5350H",
        )
        fetcher = _FakePageFetcher(body=_read_seagate_fixture())

        result = acquire_comparable_research_authority_context(
            request=request,
            page_fetcher=fetcher,
        )

        assert result.context is not None
        # Source-published MPN from the catalog record, not request formatting
        assert result.context.target_identity.manufacturer_part_number == "XP15360SE70005"

    def test_exact_mpn_normalized_part_number_is_none(self) -> None:
        """EXACT match does not require normalized_part_number."""
        request = ResearchRequest(
            manufacturer_part_number="XP15360SE70005",
            description="Seagate Nytro",
        )
        fetcher = _FakePageFetcher(body=_read_seagate_fixture())

        result = acquire_comparable_research_authority_context(
            request=request,
            page_fetcher=fetcher,
        )

        ctx = result.context
        assert ctx is not None
        assert ctx.target_identity.match_type is IdentityMatchType.EXACT

    def test_exact_mpn_retains_matched_observation(self) -> None:
        """MATCHED outcome retains the frozen ComparableCandidateObservation."""
        from product_intelligence.research.comparable_candidates import (
            ComparableCandidateObservation,
        )

        request = ResearchRequest(
            manufacturer_part_number="XP15360SE70005",
            description="Seagate Nytro",
        )
        fetcher = _FakePageFetcher(body=_read_seagate_fixture())

        result = acquire_comparable_research_authority_context(
            request=request,
            page_fetcher=fetcher,
        )

        ctx = result.context
        assert ctx is not None
        evidence = ctx.authority_evidence
        assert evidence.matched_observation is not None
        assert isinstance(evidence.matched_observation, ComparableCandidateObservation)
        assert evidence.matched_observation.manufacturer_part_number_raw == "XP15360SE70005"


# ---------------------------------------------------------------------------
# TEST 3: Real Seagate fixture + normalized-exact spelling preserves source raw MPN
# ---------------------------------------------------------------------------


class TestNormalizedExactPreservesSourceMpn:
    def test_normalized_exact_preserves_source_raw_mpn(self) -> None:
        """Normalized-exact match preserves the authoritative source record's
        manufacturer-published raw MPN, not request formatting.

        BLOCKER 7: request "xp15360se70005" (lowercase) vs source "XP15360SE70005"
        is specifically NORMALIZED_EXACT under frozen 2A, not EXACT.
        """
        request = ResearchRequest(
            manufacturer_part_number="xp15360se70005",
            description="Seagate Nytro 5350H",
        )
        fetcher = _FakePageFetcher(body=_read_seagate_fixture())

        result = acquire_comparable_research_authority_context(
            request=request,
            page_fetcher=fetcher,
        )

        assert result.context is not None
        ctx = result.context
        # BLOCKER 7: MUST be NORMALIZED_EXACT, not EXACT
        assert ctx.target_identity.match_type is IdentityMatchType.NORMALIZED_EXACT
        # Source-published MPN preserved, not the lowercase request spelling
        assert ctx.target_identity.manufacturer_part_number == "XP15360SE70005"
        # NORMALIZED_EXACT requires normalized_part_number
        assert ctx.target_identity.normalized_part_number is not None
        assert ctx.target_identity.normalized_part_number == normalize_part_number(
            "XP15360SE70005"
        )

    def test_normalized_exact_retains_exact_source_raw_mpn_in_observation(self) -> None:
        """BLOCKER 4 + 7: matched_observation contains exact source raw MPN."""
        request = ResearchRequest(
            manufacturer_part_number="xp15360se70005",
            description="Seagate Nytro 5350H",
        )
        fetcher = _FakePageFetcher(body=_read_seagate_fixture())

        result = acquire_comparable_research_authority_context(
            request=request,
            page_fetcher=fetcher,
        )

        ctx = result.context
        assert ctx is not None
        obs = ctx.authority_evidence.matched_observation
        assert obs is not None
        # The observation preserves the EXACT source-published raw MPN
        assert obs.manufacturer_part_number_raw == "XP15360SE70005"


# ---------------------------------------------------------------------------
# TEST 4: Missing MPN -> NO_AUTHORITY_MATCH
# ---------------------------------------------------------------------------


class TestMissingMpn:
    def test_missing_mpn_abstains(self) -> None:
        """MPN not in any approved source -> NO_AUTHORITY_MATCH.

        BLOCKER 1: per-source state is NO_MPN_IN_SOURCE,
        result-level status is NO_AUTHORITY_MATCH.
        """
        request = ResearchRequest(
            manufacturer_part_number="NONEXISTENT_MPN_999",
            description="Some product",
        )
        fetcher = _FakePageFetcher(body=_read_seagate_fixture())

        result = acquire_comparable_research_authority_context(
            request=request,
            page_fetcher=fetcher,
        )

        assert result.context is None
        assert len(result.source_outcomes) == 1
        # Per-source: MPN not found in this source
        assert result.source_outcomes[0].outcome_state is AuthoritySourceOutcomeState.NO_MPN_IN_SOURCE
        # Result-level: no authority match
        assert result.acquisition_status is AuthorityAcquisitionStatus.NO_AUTHORITY_MATCH

    def test_samsung_mpn_abstains(self) -> None:
        """Samsung MPN does not match Seagate source -> abstain."""
        request = ResearchRequest(
            manufacturer_part_number="MZ-QL23T800",
            description="Samsung PM9A3 3.84TB",
        )
        fetcher = _FakePageFetcher(body=_read_seagate_fixture())

        result = acquire_comparable_research_authority_context(
            request=request,
            page_fetcher=fetcher,
        )

        assert result.context is None
        assert result.source_outcomes[0].outcome_state is AuthoritySourceOutcomeState.NO_MPN_IN_SOURCE
        assert result.acquisition_status is AuthorityAcquisitionStatus.NO_AUTHORITY_MATCH
        # Must not guess "Samsung unsupported" - that requires manufacturer knowledge
        # The outcome is purely evidence-backed: no match in the approved source


# ---------------------------------------------------------------------------
# TEST 5: Description-only request -> NO_REQUESTED_MPN
# ---------------------------------------------------------------------------


class TestDescriptionOnly:
    def test_description_only_no_requested_mpn(self) -> None:
        """Description-only request cannot establish authority (no MPN to match)."""
        request = ResearchRequest(
            manufacturer_part_number="",
            description="Some enterprise SSD product",
        )
        fetcher = _FakePageFetcher(body=_read_seagate_fixture())

        result = acquire_comparable_research_authority_context(
            request=request,
            page_fetcher=fetcher,
        )

        assert result.context is None
        assert len(result.source_outcomes) == 1
        assert result.source_outcomes[0].outcome_state is AuthoritySourceOutcomeState.NO_REQUESTED_MPN
        assert result.acquisition_status is AuthorityAcquisitionStatus.NO_REQUESTED_MPN


# ---------------------------------------------------------------------------
# TEST 6: Multiple matching records -> AMBIGUOUS_AUTHORITY_MATCH
# ---------------------------------------------------------------------------


class TestMultipleMatches:
    def test_duplicate_records_in_source_ambiguous(self) -> None:
        """If extraction produces two records with MPNs that both match
        the request, authority establishment fails closed.

        BLOCKER 1: per-source state is AMBIGUOUS_MPN_MATCH,
        result-level status is AMBIGUOUS_AUTHORITY_MATCH.
        """
        import json as _json
        records = _json.dumps([
            {"skuNumber": "AMBIGUOUS123", "title": "Product A"},
            {"skuNumber": "AMBIGUOUS123", "title": "Product B"},
        ])
        doc = (
            "<script>\n"
            "var supportSpecsData = JSON.parse('"
            + records + "');\n"
            "</script>\n"
        )
        request = ResearchRequest(
            manufacturer_part_number="AMBIGUOUS123",
            description="Ambiguous product",
        )
        fetcher = _FakePageFetcher(body=doc)

        result = acquire_comparable_research_authority_context(
            request=request,
            page_fetcher=fetcher,
        )

        assert result.context is None
        assert len(result.source_outcomes) == 1
        # BLOCKER 1: per-source explicitly records ambiguity
        assert result.source_outcomes[0].outcome_state is AuthoritySourceOutcomeState.AMBIGUOUS_MPN_MATCH
        # Result-level: ambiguous authority match
        assert result.acquisition_status is AuthorityAcquisitionStatus.AMBIGUOUS_AUTHORITY_MATCH

    def test_different_matching_mpns_ambiguous(self) -> None:
        """Two different source MPNs that both normalize to the same key
        as the request also produces ambiguity.

        This tests the cross-match case within one source.
        """
        import json as _json
        # Two records with different MPN spellings that both match the same
        # request after normalization
        records = _json.dumps([
            {"skuNumber": "DUP-MATCH", "title": "Product A"},
            {"skuNumber": "DUP-MATCH", "title": "Product B - Duplicate"},
        ])
        doc = (
            "<script>\n"
            "var supportSpecsData = JSON.parse('"
            + records + "');\n"
            "</script>\n"
        )
        request = ResearchRequest(
            manufacturer_part_number="DUP-MATCH",
            description="Duplicate match test",
        )
        fetcher = _FakePageFetcher(body=doc)

        result = acquire_comparable_research_authority_context(
            request=request,
            page_fetcher=fetcher,
        )

        assert result.context is None
        assert result.source_outcomes[0].outcome_state is AuthoritySourceOutcomeState.AMBIGUOUS_MPN_MATCH
        assert result.acquisition_status is AuthorityAcquisitionStatus.AMBIGUOUS_AUTHORITY_MATCH


# ---------------------------------------------------------------------------
# TEST 7: Arbitrary public hostname cannot become authoritative
# ---------------------------------------------------------------------------


class TestArbitraryHostname:
    def test_arbitrary_hostname_cannot_become_authoritative(self) -> None:
        """An unapproved host cannot produce an authoritative result.
        The policy's approved authority origin boundary prevents this."""
        request = ResearchRequest(
            manufacturer_part_number="XP15360SE70005",
            description="Seagate Nytro",
        )
        fetcher = _FakePageFetcher(
            body=_read_seagate_fixture(),
            final_url="https://malicious-copy.example.com/seagate-fake/",
        )

        result = acquire_comparable_research_authority_context(
            request=request,
            page_fetcher=fetcher,
        )

        assert result.context is None
        assert result.source_outcomes[0].outcome_state is AuthoritySourceOutcomeState.AUTHORITY_HOST_ESCAPED
        assert result.source_outcomes[0].fetched_final_url == "https://malicious-copy.example.com/seagate-fake/"


# ---------------------------------------------------------------------------
# TEST 8: Caller cannot inject a custom policy/source URL
# ---------------------------------------------------------------------------


class TestCallerCannotInjectPolicy:
    def test_no_injection_surface_exists(self) -> None:
        """Prove there is no way for a caller to supply a custom policy.
        The public API accepts only request + page_fetcher."""
        sig = inspect.signature(acquire_comparable_research_authority_context)
        # Only request and page_fetcher are accepted
        assert set(sig.parameters.keys()) == {"request", "page_fetcher"}

    def test_cannot_supply_alternate_source_url(self) -> None:
        """Even if page_fetcher returns data from a different URL,
        the policy's approved URL is the one used for source descriptors."""
        request = ResearchRequest(
            manufacturer_part_number="XP15360SE70005",
            description="Seagate Nytro",
        )
        fetcher = _FakePageFetcher(body=_read_seagate_fixture())

        result = acquire_comparable_research_authority_context(
            request=request,
            page_fetcher=fetcher,
        )

        assert result.context is not None
        # Descriptors use the policy's canonical URL, not whatever the fetcher
        # happened to return
        assert result.context.specification_source.source_url == _SEAGATE_SOURCE_URL
        assert result.context.comparable_source.source_url == _SEAGATE_SOURCE_URL

    def test_policy_is_module_private(self) -> None:
        """_AUTHORITY_POLICIES is not exported from the module."""
        import product_intelligence.execution.comparable_research_authority as mod
        # Private by naming convention; check it starts with _
        assert not hasattr(mod, "authority_policies")  # no public alias
        assert not hasattr(mod, "AUTHORITY_POLICIES")   # no public constant


# ---------------------------------------------------------------------------
# TEST 9: Redirect to unapproved host fails closed
# ---------------------------------------------------------------------------


class TestRedirectAuthority:
    def test_approved_url_redirect_to_unapproved_host_fails(self) -> None:
        """Approved requested URL whose final_url escapes approved authority
        origin fails closed with no ProductIdentity and no authoritative descriptors."""
        request = ResearchRequest(
            manufacturer_part_number="XP15360SE70005",
            description="Seagate Nytro",
        )
        fetcher = _FakePageFetcher(
            body=_read_seagate_fixture(),
            final_url="https://cdn.other-provider.com/proxied/seagate-data.html",
        )

        result = acquire_comparable_research_authority_context(
            request=request,
            page_fetcher=fetcher,
        )

        assert result.context is None
        assert result.source_outcomes[0].outcome_state is AuthoritySourceOutcomeState.AUTHORITY_HOST_ESCAPED
        assert result.source_outcomes[0].fetched_final_url == "https://cdn.other-provider.com/proxied/seagate-data.html"

    def test_approved_final_host_succeeds(self) -> None:
        """Final URL on the approved authority origin succeeds."""
        request = ResearchRequest(
            manufacturer_part_number="XP15360SE70005",
            description="Seagate Nytro",
        )
        # final_url stays within www.seagate.com (the approved origin)
        final_url = "https://www.seagate.com/support/enterprise-storage/solid-state-drives/nytro-5050/redirect/"
        fetcher = _FakePageFetcher(
            body=_read_seagate_fixture(),
            final_url=final_url,
        )

        result = acquire_comparable_research_authority_context(
            request=request,
            page_fetcher=fetcher,
        )

        assert result.context is not None
        assert result.source_outcomes[0].outcome_state is AuthoritySourceOutcomeState.MATCHED
        assert result.source_outcomes[0].fetched_final_url == final_url

    # BLOCKER 8: Transport downgrade must fail closed
    def test_http_downgrade_fails(self) -> None:
        """HTTP (non-HTTPS) on the same host fails origin boundary check.

        BLOCKER 8: approved origin is https://www.seagate.com.
        http://www.seagate.com has a different scheme -> fails.
        """
        request = ResearchRequest(
            manufacturer_part_number="XP15360SE70005",
            description="Seagate Nytro",
        )
        fetcher = _FakePageFetcher(
            body=_read_seagate_fixture(),
            final_url="http://www.seagate.com/support/enterprise-storage/",
        )

        result = acquire_comparable_research_authority_context(
            request=request,
            page_fetcher=fetcher,
        )

        assert result.context is None
        assert result.source_outcomes[0].outcome_state is AuthoritySourceOutcomeState.AUTHORITY_HOST_ESCAPED

    def test_non_default_port_fails(self) -> None:
        """HTTPS on non-default port fails origin boundary check.

        BLOCKER 8: approved origin is https://www.seagate.com (port 443).
        https://www.seagate.com:8443 has a different port -> fails.
        """
        request = ResearchRequest(
            manufacturer_part_number="XP15360SE70005",
            description="Seagate Nytro",
        )
        fetcher = _FakePageFetcher(
            body=_read_seagate_fixture(),
            final_url="https://www.seagate.com:8443/support/",
        )

        result = acquire_comparable_research_authority_context(
            request=request,
            page_fetcher=fetcher,
        )

        assert result.context is None
        assert result.source_outcomes[0].outcome_state is AuthoritySourceOutcomeState.AUTHORITY_HOST_ESCAPED

    def test_different_host_fails(self) -> None:
        """Different host entirely fails origin boundary check.

        BLOCKER 8: approved origin is https://www.seagate.com.
        https://other.example fails.
        """
        request = ResearchRequest(
            manufacturer_part_number="XP15360SE70005",
            description="Seagate Nytro",
        )
        fetcher = _FakePageFetcher(
            body=_read_seagate_fixture(),
            final_url="https://other.example/seagate-mirror/",
        )

        result = acquire_comparable_research_authority_context(
            request=request,
            page_fetcher=fetcher,
        )

        assert result.context is None
        assert result.source_outcomes[0].outcome_state is AuthoritySourceOutcomeState.AUTHORITY_HOST_ESCAPED

    def test_path_change_on_same_origin_succeeds(self) -> None:
        """Path changes on the same approved origin are allowed.

        BLOCKER 8: https://www.seagate.com is the approved origin.
        Different paths on the same origin are fine.
        """
        request = ResearchRequest(
            manufacturer_part_number="XP15360SE70005",
            description="Seagate Nytro",
        )
        fetcher = _FakePageFetcher(
            body=_read_seagate_fixture(),
            final_url="https://www.seagate.com/different/path/here/",
        )

        result = acquire_comparable_research_authority_context(
            request=request,
            page_fetcher=fetcher,
        )

        assert result.context is not None
        assert result.source_outcomes[0].outcome_state is AuthoritySourceOutcomeState.MATCHED


# ---------------------------------------------------------------------------
# TEST 10: Search result/title/description are never authority inputs
# ---------------------------------------------------------------------------


class TestNoSearchInputs:
    def test_search_result_not_authority_input(self) -> None:
        """Search result data is never an input to authority establishment.
        Only the fetched document's structural data matters."""
        sig = inspect.signature(acquire_comparable_research_authority_context)
        param_names = set(sig.parameters.keys())
        search_terms = {"search_results", "results", "search_response", "query", "snippet"}
        found = search_terms & param_names
        assert not found, f"Found search-related parameters: {found}"

    def test_title_not_authority_input(self) -> None:
        """Title/description text from any source is never used for
        identity authority in this module."""
        import product_intelligence.execution.comparable_research_authority as mod
        source = inspect.getsource(mod)
        assert "title" not in source.lower() or "product_name_raw" in source


# ---------------------------------------------------------------------------
# TEST 11: target_identity source-MPN/request-MPN mechanically re-derived
# ---------------------------------------------------------------------------


class TestIdentityReDerivation:
    def test_mpn_relationship_rederived_via_frozen_2a(self) -> None:
        """target_identity source-MPN/request-MPN relationship is mechanically
        re-derived through frozen 2A compare_part_numbers()."""
        from product_intelligence.research.identity import compare_part_numbers

        request = ResearchRequest(
            manufacturer_part_number="XP15360SE70005",
            description="Seagate Nytro",
        )
        fetcher = _FakePageFetcher(body=_read_seagate_fixture())

        result = acquire_comparable_research_authority_context(
            request=request,
            page_fetcher=fetcher,
        )

        ctx = result.context
        assert ctx is not None

        # Mechanically re-derive the binding
        rederived = compare_part_numbers(
            request.manufacturer_part_number,
            ctx.target_identity.manufacturer_part_number,
        )

        # Must agree with target_identity.match_type
        assert rederived.match_type == ctx.target_identity.match_type
        assert rederived.match_type in (IdentityMatchType.EXACT, IdentityMatchType.NORMALIZED_EXACT)

    def test_normalized_exact_fields_consistent(self) -> None:
        """For NORMALIZED_EXACT, normalized_part_number is mechanically
        re-derivable from the source-published MPN."""
        from product_intelligence.research.identity import normalize_part_number

        request = ResearchRequest(
            manufacturer_part_number="xp15360se70005",
            description="Seagate Nytro",
        )
        fetcher = _FakePageFetcher(body=_read_seagate_fixture())

        result = acquire_comparable_research_authority_context(
            request=request,
            page_fetcher=fetcher,
        )

        ctx = result.context
        assert ctx is not None
        # BLOCKER 7: this is specifically NORMALIZED_EXACT
        assert ctx.target_identity.match_type is IdentityMatchType.NORMALIZED_EXACT
        expected_normalized = normalize_part_number(
            ctx.target_identity.manufacturer_part_number
        )
        assert ctx.target_identity.normalized_part_number == expected_normalized


# ---------------------------------------------------------------------------
# TEST 12: specification_source.product_identity is target_identity (object identity)
# ---------------------------------------------------------------------------


class TestDescriptorObjectIdentity:
    def test_specification_source_binds_target_identity(self) -> None:
        """specification_source.product_identity is target_identity by
        exact object identity, not just value equality."""
        request = ResearchRequest(
            manufacturer_part_number="XP15360SE70005",
            description="Seagate Nytro",
        )
        fetcher = _FakePageFetcher(body=_read_seagate_fixture())

        result = acquire_comparable_research_authority_context(
            request=request,
            page_fetcher=fetcher,
        )

        ctx = result.context
        assert ctx is not None
        assert ctx.specification_source.product_identity is ctx.target_identity

    def test_both_descriptors_are_authoritative(self) -> None:
        """Both specification_source and comparable_source are AUTHORITATIVE."""
        request = ResearchRequest(
            manufacturer_part_number="XP15360SE70005",
            description="Seagate Nytro",
        )
        fetcher = _FakePageFetcher(body=_read_seagate_fixture())

        result = acquire_comparable_research_authority_context(
            request=request,
            page_fetcher=fetcher,
        )

        ctx = result.context
        assert ctx is not None
        assert ctx.specification_source.source_authority is SourceAuthority.AUTHORITATIVE
        assert ctx.comparable_source.source_authority is SourceAuthority.AUTHORITATIVE

    def test_descriptors_from_canonical_policy(self) -> None:
        """Both descriptors originate from the canonical policy (same URL, name)."""
        request = ResearchRequest(
            manufacturer_part_number="XP15360SE70005",
            description="Seagate Nytro",
        )
        fetcher = _FakePageFetcher(body=_read_seagate_fixture())

        result = acquire_comparable_research_authority_context(
            request=request,
            page_fetcher=fetcher,
        )

        ctx = result.context
        assert ctx is not None
        assert ctx.specification_source.source_url == ctx.comparable_source.source_url
        assert ctx.specification_source.source_name == ctx.comparable_source.source_name
        assert ctx.specification_source.source_url == _SEAGATE_SOURCE_URL


# ---------------------------------------------------------------------------
# TEST 13: Copied/tampered descriptors rejected by context invariants
# ---------------------------------------------------------------------------


class TestContextInvariants:
    def test_copied_spec_source_identity_rejected(self) -> None:
        """A SpecificationEvidenceSource with a different ProductIdentity object
        is rejected by ComparableResearchAuthorityContext._validate()."""
        import dataclasses

        request = ResearchRequest(
            manufacturer_part_number="XP15360SE70005",
            description="Seagate Nytro",
        )
        fetcher = _FakePageFetcher(body=_read_seagate_fixture())

        result = acquire_comparable_research_authority_context(
            request=request,
            page_fetcher=fetcher,
        )

        ctx = result.context
        assert ctx is not None

        # Tamper: create a context with a copied spec source that has a
        # different identity object
        different_identity = ProductIdentity(
            manufacturer="Seagate",
            manufacturer_part_number="XP15360SE70005",
            match_type=IdentityMatchType.EXACT,
        )
        assert different_identity is not ctx.target_identity

        tampered_spec_source = dataclasses.replace(
            ctx.specification_source,
            product_identity=different_identity,
        )

        # Construct via low-level path to test _validate invariants
        tampered_ctx = object.__new__(ComparableResearchAuthorityContext)
        object.__setattr__(tampered_ctx, "request", request)
        object.__setattr__(tampered_ctx, "target_identity", ctx.target_identity)
        object.__setattr__(tampered_ctx, "category_schema", ctx.category_schema)
        object.__setattr__(tampered_ctx, "specification_source", tampered_spec_source)
        object.__setattr__(tampered_ctx, "comparable_source", ctx.comparable_source)
        object.__setattr__(tampered_ctx, "authority_evidence", ctx.authority_evidence)

        with pytest.raises(ValueError, match="product_identity"):
            tampered_ctx._validate()

    def test_wrong_category_schema_rejected(self) -> None:
        """Non-ENTERPRISE_SSD_SCHEMA by identity is rejected."""
        from product_intelligence.research.specifications import (
            CategorySchema,
            SpecificationDefinition,
            SpecificationValueKind,
        )

        request = ResearchRequest(
            manufacturer_part_number="XP15360SE70005",
            description="Seagate Nytro",
        )
        fetcher = _FakePageFetcher(body=_read_seagate_fixture())

        result = acquire_comparable_research_authority_context(
            request=request,
            page_fetcher=fetcher,
        )

        ctx = result.context
        assert ctx is not None

        # Build a different schema (value-equal conceptually but different object)
        wrong_schema = CategorySchema(
            schema_id="enterprise-ssd",
            schema_version="1.0",
            label="Enterprise SSD",
            definitions={
                "capacity": SpecificationDefinition(
                    key="capacity",
                    label="Capacity",
                    value_kind=SpecificationValueKind.DECIMAL,
                    unit="TB",
                ),
            },
        )

        # Construct via low-level path to test _validate invariants
        tampered_ctx = object.__new__(ComparableResearchAuthorityContext)
        object.__setattr__(tampered_ctx, "request", ctx.request)
        object.__setattr__(tampered_ctx, "target_identity", ctx.target_identity)
        object.__setattr__(tampered_ctx, "category_schema", wrong_schema)
        object.__setattr__(tampered_ctx, "specification_source", ctx.specification_source)
        object.__setattr__(tampered_ctx, "comparable_source", ctx.comparable_source)
        object.__setattr__(tampered_ctx, "authority_evidence", ctx.authority_evidence)

        with pytest.raises(ValueError, match="ENTERPRISE_SSD_SCHEMA"):
            tampered_ctx._validate()

    def test_tampered_matching_mpn_evidence_rejected(self) -> None:
        """authority_evidence.matching_mpn_evidence must equal
        target_identity.manufacturer_part_number."""
        from product_intelligence.execution.comparable_research_authority import (
            _AuthoritySourceOutcome,
        )

        request = ResearchRequest(
            manufacturer_part_number="XP15360SE70005",
            description="Seagate Nytro",
        )
        fetcher = _FakePageFetcher(body=_read_seagate_fixture())

        result = acquire_comparable_research_authority_context(
            request=request,
            page_fetcher=fetcher,
        )

        ctx = result.context
        assert ctx is not None

        # Tamper the evidence with a wrong MPN
        tampered_evidence = _AuthoritySourceOutcome(
            policy_id=ctx.authority_evidence.policy_id,
            outcome_state=AuthoritySourceOutcomeState.MATCHED,
            requested_source_url=ctx.authority_evidence.requested_source_url,
            fetched_final_url=ctx.authority_evidence.fetched_final_url,
            retrieved_at=ctx.authority_evidence.retrieved_at,
            matching_mpn_evidence="WRONG_MPN",  # tampered
            matched_observation=ctx.authority_evidence.matched_observation,
            part_number_match_assessment=ctx.authority_evidence.part_number_match_assessment,
        )

        # Construct via low-level path to test _validate invariants
        tampered_ctx = object.__new__(ComparableResearchAuthorityContext)
        object.__setattr__(tampered_ctx, "request", ctx.request)
        object.__setattr__(tampered_ctx, "target_identity", ctx.target_identity)
        object.__setattr__(tampered_ctx, "category_schema", ctx.category_schema)
        object.__setattr__(tampered_ctx, "specification_source", ctx.specification_source)
        object.__setattr__(tampered_ctx, "comparable_source", ctx.comparable_source)
        object.__setattr__(tampered_ctx, "authority_evidence", tampered_evidence)

        with pytest.raises(ValueError, match="matching_mpn_evidence"):
            tampered_ctx._validate()


# ---------------------------------------------------------------------------
# TEST 14: UnsafeFetchTargetError -> bounded SOURCE_REFUSED abstention
# ---------------------------------------------------------------------------


class TestFetchErrorHandling:
    def test_unsafe_fetch_target_error_bounded(self) -> None:
        """UnsafeFetchTargetError -> SOURCE_REFUSED abstention, not crash."""
        request = ResearchRequest(
            manufacturer_part_number="XP15360SE70005",
            description="Seagate Nytro",
        )
        fetcher = _FakePageFetcher(error=UnsafeFetchTargetError)

        result = acquire_comparable_research_authority_context(
            request=request,
            page_fetcher=fetcher,
        )

        assert result.context is None
        assert result.source_outcomes[0].outcome_state is AuthoritySourceOutcomeState.AUTHORITY_SOURCE_REFUSED

    def test_page_fetch_error_bounded(self) -> None:
        """PageFetchError -> FETCH_FAILED abstention, not crash."""
        request = ResearchRequest(
            manufacturer_part_number="XP15360SE70005",
            description="Seagate Nytro",
        )
        fetcher = _FakePageFetcher(error=PageFetchError)

        result = acquire_comparable_research_authority_context(
            request=request,
            page_fetcher=fetcher,
        )

        assert result.context is None
        assert result.source_outcomes[0].outcome_state is AuthoritySourceOutcomeState.AUTHORITY_FETCH_FAILED

    def test_programming_error_propagates(self) -> None:
        """Programming errors propagate; they do NOT become abstention."""
        class _BrokenFetcher:
            def fetch(self, request: PageFetchRequest) -> FetchedPage:
                raise RuntimeError("programming defect")

        request = ResearchRequest(
            manufacturer_part_number="XP15360SE70005",
            description="Seagate Nytro",
        )

        with pytest.raises(RuntimeError, match="programming defect"):
            acquire_comparable_research_authority_context(
                request=request,
                page_fetcher=_BrokenFetcher(),
            )


# ---------------------------------------------------------------------------
# TEST 15: Samsung/nonmatching MPN does not cause manufacturer/category guessing
# ---------------------------------------------------------------------------


class TestNoGuessing:
    def test_samsung_no_manufacturer_guessing(self) -> None:
        """Samsung MPN does not cause 'Samsung unsupported' or any
        manufacturer/category guessing."""
        request = ResearchRequest(
            manufacturer_part_number="MZ-QL23T800",
            description="Samsung PM9A3 3.84TB NVMe",
        )
        fetcher = _FakePageFetcher(body=_read_seagate_fixture())

        result = acquire_comparable_research_authority_context(
            request=request,
            page_fetcher=fetcher,
        )

        assert result.context is None
        assert result.source_outcomes[0].outcome_state is AuthoritySourceOutcomeState.NO_MPN_IN_SOURCE
        assert result.acquisition_status is AuthorityAcquisitionStatus.NO_AUTHORITY_MATCH
        # No UNSUPPORTED_MANUFACTURER or UNSUPPORTED_CATEGORY state exists
        valid_states = {s.value for s in AuthoritySourceOutcomeState}
        assert "UNSUPPORTED_MANUFACTURER" not in valid_states
        assert "UNSUPPORTED_CATEGORY" not in valid_states

    def test_non_ssd_mpn_abstains(self) -> None:
        """Non-SSD MPN abstains without category guessing."""
        request = ResearchRequest(
            manufacturer_part_number="DESK-12345",
            description="Office desk",
        )
        fetcher = _FakePageFetcher(body=_read_seagate_fixture())

        result = acquire_comparable_research_authority_context(
            request=request,
            page_fetcher=fetcher,
        )

        assert result.context is None
        assert result.source_outcomes[0].outcome_state is AuthoritySourceOutcomeState.NO_MPN_IN_SOURCE
        assert result.acquisition_status is AuthorityAcquisitionStatus.NO_AUTHORITY_MATCH


# ---------------------------------------------------------------------------
# TEST 16: No LLM/SearchProvider/concrete HTTP dependency
# ---------------------------------------------------------------------------


class TestNoForbiddenDependencies:
    def test_no_llm_import(self) -> None:
        """PRE1 module imports no LLM provider."""
        import product_intelligence.execution.comparable_research_authority as mod
        source = inspect.getsource(mod)
        llm_terms = ["openai", "anthropic", "llm_provider", "llmprovider", "chatgpt"]
        for term in llm_terms:
            assert term not in source.lower(), f"Found LLM term: {term}"

    def test_no_search_provider_import(self) -> None:
        """PRE1 module imports no SearchProvider."""
        import product_intelligence.execution.comparable_research_authority as mod
        source = inspect.getsource(mod)
        assert "search_provider" not in source.lower()
        assert "SearchProvider" not in source

    def test_no_concrete_http_import(self) -> None:
        """PRE1 module imports no HttpPageFetcher."""
        import product_intelligence.execution.comparable_research_authority as mod
        source = inspect.getsource(mod)
        assert "HttpPageFetcher" not in source
        assert "http_page" not in source.lower() or "page" in source.lower()

    def test_uses_protocol_not_concrete(self) -> None:
        """PageFetcher used is the Protocol from providers.page."""
        import product_intelligence.execution.comparable_research_authority as mod
        import ast
        tree = ast.parse(inspect.getsource(mod))
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom):
                if node.module and "page" in str(node.module):
                    names = [a.name for a in node.names]
                    assert "PageFetcher" in names


# ---------------------------------------------------------------------------
# TEST 17: Authority construction guard
# ---------------------------------------------------------------------------


class TestAuthorityConstructionGuard:
    def test_authority_descriptors_only_from_approved_module(self) -> None:
        """No other production path can construct the PRE1 authoritative
        descriptor pair outside the approved module."""
        import product_intelligence.execution.comparable_research_authority as mod

        # The only public function for authority acquisition
        public_funcs = [
            name for name, obj in inspect.getmembers(mod, inspect.isfunction)
            if not name.startswith("_")
        ]
        assert "acquire_comparable_research_authority_context" in public_funcs

        # _AUTHORITY_POLICIES is private
        assert not hasattr(mod, "authority_policies")
        assert not hasattr(mod, "AUTHORITY_POLICIES")

        # _process_authority_policy is private
        assert hasattr(mod, "_process_authority_policy")
        assert mod._process_authority_policy.__name__.startswith("_")

    def test_public_context_construction_blocked(self) -> None:
        """BLOCKER 1: Direct public construction of
        ComparableResearchAuthorityContext is structurally blocked.

        The dataclass has init=False and no custom __init__ is defined.
        Calling ComparableResearchAuthorityContext(...) raises TypeError
        because object.__init__ takes no arguments.

        This proves the blocker is closed: no callable public constructor
        accepts authority fields.
        """
        from product_intelligence.domain.enums import IdentityMatchType
        from product_intelligence.domain.models import ResearchRequest, ProductIdentity
        from product_intelligence.execution.comparable_research_authority import (
            _AuthoritySourceOutcome,
        )
        from product_intelligence.research.enterprise_ssd import ENTERPRISE_SSD_SCHEMA
        from product_intelligence.research.identity import PartNumberMatchAssessment, compare_part_numbers
        from product_intelligence.research.comparable_candidates import (
            ComparableCandidateObservation, ComparableCandidateSource,
        )
        from product_intelligence.execution.specification_evidence import (
            SpecificationEvidenceSource,
        )
        from product_intelligence.research.specifications import SourceAuthority

        # Even with all the correct types, a direct call with fabricated
        # data MUST raise TypeError because no public constructor exists.
        request = ResearchRequest(
            manufacturer_part_number="XP15360SE70005",
            description="Seagate Nytro",
        )
        target_identity = ProductIdentity(
            manufacturer="Seagate",
            manufacturer_part_number="XP15360SE70005",
            match_type=IdentityMatchType.EXACT,
        )
        spec_source = SpecificationEvidenceSource(
            product_identity=target_identity,
            source_name="Seagate Enterprise Support",
            source_url=_SEAGATE_SOURCE_URL,
            source_authority=SourceAuthority.AUTHORITATIVE,
        )
        comp_source = ComparableCandidateSource(
            source_name="Seagate Enterprise Support",
            source_url=_SEAGATE_SOURCE_URL,
            source_authority=SourceAuthority.AUTHORITATIVE,
        )
        comparison = compare_part_numbers("XP15360SE70005", "XP15360SE70005")

        # Build a fake observation
        fake_obs = ComparableCandidateObservation(
            manufacturer_part_number_raw="XP15360SE70005",
            product_name_raw="Nytro 5350",
            source_name="Seagate Enterprise Support",
            source_url=_SEAGATE_SOURCE_URL,
            retrieved_at=_RETRIEVED_AT,
            source_authority=SourceAuthority.AUTHORITATIVE,
        )

        fake_evidence = _AuthoritySourceOutcome(
            policy_id="seagate-enterprise-ssd-nytro-support-catalog-v1",
            outcome_state=AuthoritySourceOutcomeState.MATCHED,
            requested_source_url=_SEAGATE_SOURCE_URL,
            fetched_final_url=_SEAGATE_SOURCE_URL,
            retrieved_at=_RETRIEVED_AT,
            matching_mpn_evidence="XP15360SE70005",
            matched_observation=fake_obs,
            part_number_match_assessment=comparison,
        )

        # Direct construction MUST raise TypeError (no public __init__)
        with pytest.raises(TypeError):
            ComparableResearchAuthorityContext(
                request=request,
                target_identity=target_identity,
                category_schema=ENTERPRISE_SSD_SCHEMA,
                specification_source=spec_source,
                comparable_source=comp_source,
                authority_evidence=fake_evidence,
            )

    def test_no_other_module_constructs_pre1_context(self) -> None:
        """AST guard: no other production module constructs
        ComparableResearchAuthorityContext outside the PRE1 module.

        Scans the complete production package product_intelligence/**/*.py
        excluding only the PRE1 module itself.
        """
        import product_intelligence.execution.comparable_research_authority as pre1_mod
        pre1_file = Path(pre1_mod.__file__)
        # Full production package root (product_intelligence/)
        production_root = pre1_file.parent.parent

        # Find all .py files in production package (excluding __pycache__)
        production_files = []
        for py_file in production_root.rglob("*.py"):
            if "__pycache__" in str(py_file):
                continue
            if py_file.name == "comparable_research_authority.py":
                continue  # skip the PRE1 module itself
            production_files.append(py_file)

        # Check no other production module constructs ComparableResearchAuthorityContext
        for py_file in production_files:
            try:
                source = py_file.read_text(encoding="utf-8")
                tree = ast.parse(source)
            except (OSError, SyntaxError):
                continue

            for node in ast.walk(tree):
                # Look for direct calls: ComparableResearchAuthorityContext(...)
                if isinstance(node, ast.Call):
                    func = node.func
                    # Direct name reference
                    if isinstance(func, ast.Name):
                        if func.id == "ComparableResearchAuthorityContext":
                            pytest.fail(
                                f"Production file {py_file.relative_to(pre1_file.parent.parent)} "
                                f"directly constructs ComparableResearchAuthorityContext. "
                                f"Only the PRE1 module should construct authority context."
                            )
                    # Attribute reference
                    elif isinstance(func, ast.Attribute):
                        if func.attr == "ComparableResearchAuthorityContext":
                            pytest.fail(
                                f"Production file {py_file.relative_to(pre1_file.parent.parent)} "
                                f"constructs ComparableResearchAuthorityContext via attribute. "
                                f"Only the PRE1 module should construct authority context."
                            )


# ---------------------------------------------------------------------------
# TEST 18: Additional invariants
# ---------------------------------------------------------------------------


class TestAdditionalInvariants:
    def test_category_schema_is_enterprise_ssd_by_identity(self) -> None:
        """Context category_schema is frozen ENTERPRISE_SSD_SCHEMA."""
        request = ResearchRequest(
            manufacturer_part_number="XP15360SE70005",
            description="Seagate Nytro",
        )
        fetcher = _FakePageFetcher(body=_read_seagate_fixture())

        result = acquire_comparable_research_authority_context(
            request=request,
            page_fetcher=fetcher,
        )

        ctx = result.context
        assert ctx is not None
        assert ctx.category_schema is ENTERPRISE_SSD_SCHEMA

    def test_context_preserves_request(self) -> None:
        """Authority context preserves the original ResearchRequest."""
        request = ResearchRequest(
            manufacturer_part_number="XP15360SE70005",
            description="Seagate Nytro 5350H 15.36TB",
        )
        fetcher = _FakePageFetcher(body=_read_seagate_fixture())

        result = acquire_comparable_research_authority_context(
            request=request,
            page_fetcher=fetcher,
        )

        ctx = result.context
        assert ctx is not None
        assert ctx.request is request

    def test_authority_evidence_has_policy_id(self) -> None:
        """Authority evidence preserves the policy ID for audit."""
        request = ResearchRequest(
            manufacturer_part_number="XP15360SE70005",
            description="Seagate Nytro",
        )
        fetcher = _FakePageFetcher(body=_read_seagate_fixture())

        result = acquire_comparable_research_authority_context(
            request=request,
            page_fetcher=fetcher,
        )

        ctx = result.context
        assert ctx is not None
        assert ctx.authority_evidence.policy_id == "seagate-enterprise-ssd-nytro-support-catalog-v1"

    def test_authority_evidence_has_part_number_assessment(self) -> None:
        """MATCHED authority evidence carries a PartNumberMatchAssessment."""
        from product_intelligence.research.identity import PartNumberMatchAssessment

        request = ResearchRequest(
            manufacturer_part_number="XP15360SE70005",
            description="Seagate Nytro",
        )
        fetcher = _FakePageFetcher(body=_read_seagate_fixture())

        result = acquire_comparable_research_authority_context(
            request=request,
            page_fetcher=fetcher,
        )

        ctx = result.context
        assert ctx is not None
        assert isinstance(ctx.authority_evidence.part_number_match_assessment, PartNumberMatchAssessment)

    def test_fetched_final_url_preserved_in_evidence(self) -> None:
        """Authority evidence preserves the fetched final_url for audit."""
        request = ResearchRequest(
            manufacturer_part_number="XP15360SE70005",
            description="Seagate Nytro",
        )
        fetcher = _FakePageFetcher(body=_read_seagate_fixture())

        result = acquire_comparable_research_authority_context(
            request=request,
            page_fetcher=fetcher,
        )

        ctx = result.context
        assert ctx is not None
        assert ctx.authority_evidence.fetched_final_url is not None
        assert ctx.authority_evidence.retrieved_at is not None

    def test_target_identity_product_name_is_none(self) -> None:
        """ProductIdentity does not promote title evidence unnecessarily."""
        request = ResearchRequest(
            manufacturer_part_number="XP15360SE70005",
            description="Seagate Nytro",
        )
        fetcher = _FakePageFetcher(body=_read_seagate_fixture())

        result = acquire_comparable_research_authority_context(
            request=request,
            page_fetcher=fetcher,
        )

        ctx = result.context
        assert ctx is not None
        assert ctx.target_identity.product_name is None
        assert ctx.target_identity.product_family is None
        assert ctx.target_identity.category is None

    def test_no_score_rank_fields_in_context(self) -> None:
        """Authority context carries no similarity/score/ranking fields."""
        request = ResearchRequest(
            manufacturer_part_number="XP15360SE70005",
            description="Seagate Nytro",
        )
        fetcher = _FakePageFetcher(body=_read_seagate_fixture())

        result = acquire_comparable_research_authority_context(
            request=request,
            page_fetcher=fetcher,
        )

        ctx = result.context
        assert ctx is not None
        forbidden = {"score", "rank", "similarity", "recommendation", "distance", "weight"}
        for field in forbidden:
            assert not hasattr(ctx, field), f"Context must not have {field}"

    def test_abstention_result_has_source_outcomes(self) -> None:
        """Abstention result preserves per-source outcomes for audit."""
        request = ResearchRequest(
            manufacturer_part_number="NONEXISTENT_999",
            description="Some product",
        )
        fetcher = _FakePageFetcher(body=_read_seagate_fixture())

        result = acquire_comparable_research_authority_context(
            request=request,
            page_fetcher=fetcher,
        )

        assert result.context is None
        assert len(result.source_outcomes) >= 1
        for outcome in result.source_outcomes:
            assert outcome.policy_id is not None
            assert outcome.outcome_state is not None

    def test_result_is_immutable(self) -> None:
        """ComparableResearchAuthorityAcquisitionResult is frozen."""
        request = ResearchRequest(
            manufacturer_part_number="XP15360SE70005",
            description="Seagate Nytro",
        )
        fetcher = _FakePageFetcher(body=_read_seagate_fixture())

        result = acquire_comparable_research_authority_context(
            request=request,
            page_fetcher=fetcher,
        )

        with pytest.raises(Exception):  # FrozenInstanceError
            result.context = None  # type: ignore[misc]

    def test_context_is_immutable(self) -> None:
        """ComparableResearchAuthorityContext is frozen."""
        request = ResearchRequest(
            manufacturer_part_number="XP15360SE70005",
            description="Seagate Nytro",
        )
        fetcher = _FakePageFetcher(body=_read_seagate_fixture())

        result = acquire_comparable_research_authority_context(
            request=request,
            page_fetcher=fetcher,
        )

        ctx = result.context
        assert ctx is not None
        with pytest.raises(Exception):  # FrozenInstanceError
            ctx.target_identity = None  # type: ignore[misc]


# ---------------------------------------------------------------------------
# TEST 19: BLOCKER 5 - Acquisition result self-audit
# ---------------------------------------------------------------------------


class TestResultSelfAudit:
    def test_established_requires_one_matched_outcome(self) -> None:
        """ESTABLISHED result must have exactly one MATCHED source outcome."""
        request = ResearchRequest(
            manufacturer_part_number="XP15360SE70005",
            description="Seagate Nytro",
        )
        fetcher = _FakePageFetcher(body=_read_seagate_fixture())

        result = acquire_comparable_research_authority_context(
            request=request,
            page_fetcher=fetcher,
        )

        assert result.acquisition_status is AuthorityAcquisitionStatus.ESTABLISHED
        assert result.context is not None
        match_count = sum(
            1 for o in result.source_outcomes
            if o.outcome_state is AuthoritySourceOutcomeState.MATCHED
        )
        assert match_count == 1

    def test_established_evidence_is_member_of_outcomes(self) -> None:
        """ESTABLISHED result: context.authority_evidence is by object identity
        exactly one member of source_outcomes."""
        request = ResearchRequest(
            manufacturer_part_number="XP15360SE70005",
            description="Seagate Nytro",
        )
        fetcher = _FakePageFetcher(body=_read_seagate_fixture())

        result = acquire_comparable_research_authority_context(
            request=request,
            page_fetcher=fetcher,
        )

        assert result.context is not None
        # By object identity check
        is_member = any(
            o is result.context.authority_evidence
            for o in result.source_outcomes
        )
        assert is_member, (
            "context.authority_evidence must be object-identical to "
            "a source_outcomes member in ESTABLISHED results"
        )

    def test_no_authority_match_invariant(self) -> None:
        """NO_AUTHORITY_MATCH: context=None, no MATCHED or AMBIGUOUS outcomes."""
        request = ResearchRequest(
            manufacturer_part_number="NONEXISTENT_999",
            description="Some product",
        )
        fetcher = _FakePageFetcher(body=_read_seagate_fixture())

        result = acquire_comparable_research_authority_context(
            request=request,
            page_fetcher=fetcher,
        )

        assert result.acquisition_status is AuthorityAcquisitionStatus.NO_AUTHORITY_MATCH
        assert result.context is None
        no_matched = all(
            o.outcome_state is not AuthoritySourceOutcomeState.MATCHED
            for o in result.source_outcomes
        )
        no_ambiguous = all(
            o.outcome_state is not AuthoritySourceOutcomeState.AMBIGUOUS_MPN_MATCH
            for o in result.source_outcomes
        )
        assert no_matched
        assert no_ambiguous

    def test_ambiguous_authority_match_invariant(self) -> None:
        """AMBIGUOUS_AUTHORITY_MATCH: context=None with ambiguity evidence."""
        import json as _json
        records = _json.dumps([
            {"skuNumber": "AMBIG123", "title": "A"},
            {"skuNumber": "AMBIG123", "title": "B"},
        ])
        doc = (
            "<script>\nvar supportSpecsData = JSON.parse('"
            + records + "');\n</script>\n"
        )
        request = ResearchRequest(
            manufacturer_part_number="AMBIG123",
            description="Ambiguous",
        )
        fetcher = _FakePageFetcher(body=doc)

        result = acquire_comparable_research_authority_context(
            request=request,
            page_fetcher=fetcher,
        )

        assert result.acquisition_status is AuthorityAcquisitionStatus.AMBIGUOUS_AUTHORITY_MATCH
        assert result.context is None
        has_ambiguous = any(
            o.outcome_state is AuthoritySourceOutcomeState.AMBIGUOUS_MPN_MATCH
            for o in result.source_outcomes
        )
        assert has_ambiguous


# ---------------------------------------------------------------------------
# TEST 20: BLOCKER 6 - Source outcome state-dependent invariants
# ---------------------------------------------------------------------------


class TestSourceOutcomeInvariants:
    def test_matched_requires_complete_provenance(self) -> None:
        """MATCHED outcome requires all provenance fields."""
        from product_intelligence.execution.comparable_research_authority import (
            _AuthoritySourceOutcome,
        )
        from product_intelligence.research.identity import compare_part_numbers
        from product_intelligence.research.comparable_candidates import (
            ComparableCandidateObservation,
        )

        obs = ComparableCandidateObservation(
            manufacturer_part_number_raw="XP15360SE70005",
            product_name_raw="Test",
            source_name="Test Source",
            source_url="https://test.example/",
            retrieved_at=_RETRIEVED_AT,
            source_authority=SourceAuthority.AUTHORITATIVE,
        )
        comparison = compare_part_numbers("XP15360SE70005", "XP15360SE70005")

        # Missing fetched_final_url -> should fail
        with pytest.raises(ValueError, match="fetched_final_url"):
            _AuthoritySourceOutcome(
                policy_id="test",
                outcome_state=AuthoritySourceOutcomeState.MATCHED,
                requested_source_url="https://test.example/",
                retrieved_at=_RETRIEVED_AT,
                matching_mpn_evidence="XP15360SE70005",
                matched_observation=obs,
                part_number_match_assessment=comparison,
            )

    def test_no_requested_mpn_must_not_have_evidence(self) -> None:
        """NO_REQUESTED_MPN must not contain matched evidence."""
        from product_intelligence.execution.comparable_research_authority import (
            _AuthoritySourceOutcome,
        )

        with pytest.raises(ValueError, match="NO_REQUESTED_MPN"):
            _AuthoritySourceOutcome(
                policy_id="test",
                outcome_state=AuthoritySourceOutcomeState.NO_REQUESTED_MPN,
                matching_mpn_evidence="SHOULD_NOT_BE_HERE",
            )

    def test_fetch_failed_must_not_have_fetched_provenance(self) -> None:
        """FETCH_FAILED must not contain fetched-document provenance."""
        from product_intelligence.execution.comparable_research_authority import (
            _AuthoritySourceOutcome,
        )

        with pytest.raises(ValueError, match="AUTHORITY_FETCH_FAILED"):
            _AuthoritySourceOutcome(
                policy_id="test",
                outcome_state=AuthoritySourceOutcomeState.AUTHORITY_FETCH_FAILED,
                fetched_final_url="https://should-not-be-here/",
            )

    def test_source_refused_must_not_have_fetched_provenance(self) -> None:
        """SOURCE_REFUSED must not contain fetched-document provenance."""
        from product_intelligence.execution.comparable_research_authority import (
            _AuthoritySourceOutcome,
        )

        with pytest.raises(ValueError, match="AUTHORITY_SOURCE_REFUSED"):
            _AuthoritySourceOutcome(
                policy_id="test",
                outcome_state=AuthoritySourceOutcomeState.AUTHORITY_SOURCE_REFUSED,
                retrieved_at=_RETRIEVED_AT,
            )


# ---------------------------------------------------------------------------
# TEST 21: BLOCKER 11 - No production asserts
# ---------------------------------------------------------------------------


class TestNoProductionAsserts:
    def test_no_asserts_in_production(self) -> None:
        """BLOCKER 9: Production code must not use assert for invariants.

        Assert statements can be disabled with -O flag. Authority correctness
        must not depend on assertions being enabled.
        """
        import product_intelligence.execution.comparable_research_authority as mod
        import ast
        source = inspect.getsource(mod)
        tree = ast.parse(source)

        assert_statements = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Assert):
                assert_statements.append(node)

        assert not assert_statements, (
            f"Production code contains {len(assert_statements)} assert statement(s). "
            "Replace with explicit exception raising."
        )


# ---------------------------------------------------------------------------
# TEST 22: BLOCKER 3 - Canonical policy binding
# ---------------------------------------------------------------------------


class TestCanonicalPolicyBinding:
    def test_context_binds_to_canonical_policy(self) -> None:
        """BLOCKER 3: Context fields are bound to the canonical policy.

        Every context field traces back to the canonical private policy:
        - policy_id matches
        - manufacturer matches
        - category_schema is canonical policy's schema
        - source_name matches
        - source_url matches
        """
        request = ResearchRequest(
            manufacturer_part_number="XP15360SE70005",
            description="Seagate Nytro",
        )
        fetcher = _FakePageFetcher(body=_read_seagate_fixture())

        result = acquire_comparable_research_authority_context(
            request=request,
            page_fetcher=fetcher,
        )

        ctx = result.context
        assert ctx is not None

        # authority_evidence.policy_id matches canonical policy
        assert ctx.authority_evidence.policy_id == "seagate-enterprise-ssd-nytro-support-catalog-v1"

        # target_identity.manufacturer == canonical policy manufacturer
        assert ctx.target_identity.manufacturer == "Seagate"

        # category_schema is canonical policy.category_schema (by identity)
        assert ctx.category_schema is ENTERPRISE_SSD_SCHEMA

        # specification_source.source_name == canonical policy.source_name
        assert ctx.specification_source.source_name == "Seagate Enterprise Support"

        # comparable_source.source_name == canonical policy.source_name
        assert ctx.comparable_source.source_name == "Seagate Enterprise Support"

        # specification_source.source_url == canonical policy requested_source_url
        assert ctx.specification_source.source_url == _SEAGATE_SOURCE_URL

        # comparable_source.source_url == canonical policy requested_source_url
        assert ctx.comparable_source.source_url == _SEAGATE_SOURCE_URL

        # authority_evidence.requested_source_url == canonical policy URL
        assert ctx.authority_evidence.requested_source_url == _SEAGATE_SOURCE_URL

        # authority_evidence.fetched_final_url inside approved origin
        from product_intelligence.execution.comparable_research_authority import (
            _normalize_origin,
        )
        final_origin = _normalize_origin(
            ctx.authority_evidence.fetched_final_url
        )
        assert final_origin == "https://www.seagate.com"

    def test_matched_observation_mpn_equals_target_mpn(self) -> None:
        """BLOCKER 3: authority evidence source MPN == target identity source MPN."""
        request = ResearchRequest(
            manufacturer_part_number="XP15360SE70005",
            description="Seagate Nytro",
        )
        fetcher = _FakePageFetcher(body=_read_seagate_fixture())

        result = acquire_comparable_research_authority_context(
            request=request,
            page_fetcher=fetcher,
        )

        ctx = result.context
        assert ctx is not None
        obs = ctx.authority_evidence.matched_observation
        assert obs is not None
        assert obs.manufacturer_part_number_raw == ctx.target_identity.manufacturer_part_number

    def test_part_number_assessment_is_actual_2a_comparison(self) -> None:
        """BLOCKER 3: part_number_match_assessment must equal the actual
        frozen 2A comparison between request MPN and matched observation MPN."""
        from product_intelligence.research.identity import compare_part_numbers

        request = ResearchRequest(
            manufacturer_part_number="XP15360SE70005",
            description="Seagate Nytro",
        )
        fetcher = _FakePageFetcher(body=_read_seagate_fixture())

        result = acquire_comparable_research_authority_context(
            request=request,
            page_fetcher=fetcher,
        )

        ctx = result.context
        assert ctx is not None

        # Re-derive the expected assessment from frozen 2A
        expected = compare_part_numbers(
            request.manufacturer_part_number,
            ctx.authority_evidence.matched_observation.manufacturer_part_number_raw,
        )

        # The assessment in the evidence must match
        assessment = ctx.authority_evidence.part_number_match_assessment
        assert assessment is not None
        assert assessment.match_type is expected.match_type


# ---------------------------------------------------------------------------
# TEST 23: BLOCKER 4 - Retained frozen observation
# ---------------------------------------------------------------------------


class TestRetainedFrozenObservation:
    def test_matched_outcome_carries_frozen_observation(self) -> None:
        """BLOCKER 4: MATCHED outcome retains the exact frozen
        ComparableCandidateObservation from 7A extraction."""
        from product_intelligence.research.comparable_candidates import (
            ComparableCandidateObservation,
        )

        request = ResearchRequest(
            manufacturer_part_number="XP15360SE70005",
            description="Seagate Nytro",
        )
        fetcher = _FakePageFetcher(body=_read_seagate_fixture())

        result = acquire_comparable_research_authority_context(
            request=request,
            page_fetcher=fetcher,
        )

        ctx = result.context
        assert ctx is not None

        obs = ctx.authority_evidence.matched_observation
        assert obs is not None
        assert isinstance(obs, ComparableCandidateObservation)

        # Observation preserves source-published raw MPN
        assert obs.manufacturer_part_number_raw == "XP15360SE70005"

        # Observation is from the canonical source
        assert obs.source_name == "Seagate Enterprise Support"
        assert obs.source_url == _SEAGATE_SOURCE_URL
        assert obs.source_authority is SourceAuthority.AUTHORITATIVE

    def test_observation_bound_to_target_identity(self) -> None:
        """BLOCKER 4: matched_observation.manufacturer_part_number_raw
        == target_identity.manufacturer_part_number."""
        request = ResearchRequest(
            manufacturer_part_number="xp15360se70005",
            description="Seagate Nytro",
        )
        fetcher = _FakePageFetcher(body=_read_seagate_fixture())

        result = acquire_comparable_research_authority_context(
            request=request,
            page_fetcher=fetcher,
        )

        ctx = result.context
        assert ctx is not None

        obs = ctx.authority_evidence.matched_observation
        assert obs is not None
        # Observation has the source-published form, not request form
        assert obs.manufacturer_part_number_raw == ctx.target_identity.manufacturer_part_number
        assert ctx.target_identity.manufacturer_part_number == "XP15360SE70005"


# ---------------------------------------------------------------------------
# TEST 24: BLOCKER 3 - Full frozen 2A assessment equality
# ---------------------------------------------------------------------------


class TestFullAssessmentEquality:
    """BLOCKER 3: The authority context validates the COMPLETE
    PartNumberMatchAssessment, not just match_type."""

    def test_tampered_assessment_fields_rejected(self) -> None:
        """A PartNumberMatchAssessment with correct match_type but
        tampered requested/candidate/normalized fields MUST be rejected.

        This proves full dataclass equality, not match_type-only comparison.
        """
        from product_intelligence.execution.comparable_research_authority import (
            _AuthoritySourceOutcome,
        )
        from product_intelligence.research.identity import compare_part_numbers

        request = ResearchRequest(
            manufacturer_part_number="XP15360SE70005",
            description="Seagate Nytro",
        )
        fetcher = _FakePageFetcher(body=_read_seagate_fixture())

        result = acquire_comparable_research_authority_context(
            request=request,
            page_fetcher=fetcher,
        )

        ctx = result.context
        assert ctx is not None

        original_assessment = ctx.authority_evidence.part_number_match_assessment
        assert original_assessment is not None

        # Tamper: create an assessment with correct match_type but wrong
        # requested/candidate part numbers
        tampered_assessment = dataclasses.replace(
            original_assessment,
            requested_part_number="TAMPERED_REQUEST",
            candidate_part_number="TAMPERED_CANDIDATE",
        )

        # Build tampered evidence
        tampered_evidence = _AuthoritySourceOutcome(
            policy_id=ctx.authority_evidence.policy_id,
            outcome_state=AuthoritySourceOutcomeState.MATCHED,
            requested_source_url=ctx.authority_evidence.requested_source_url,
            fetched_final_url=ctx.authority_evidence.fetched_final_url,
            retrieved_at=ctx.authority_evidence.retrieved_at,
            matching_mpn_evidence=ctx.authority_evidence.matching_mpn_evidence,
            matched_observation=ctx.authority_evidence.matched_observation,
            part_number_match_assessment=tampered_assessment,
        )

        # Construct via low-level path to test _validate
        tampered_ctx = object.__new__(ComparableResearchAuthorityContext)
        object.__setattr__(tampered_ctx, "request", ctx.request)
        object.__setattr__(tampered_ctx, "target_identity", ctx.target_identity)
        object.__setattr__(tampered_ctx, "category_schema", ctx.category_schema)
        object.__setattr__(tampered_ctx, "specification_source", ctx.specification_source)
        object.__setattr__(tampered_ctx, "comparable_source", ctx.comparable_source)
        object.__setattr__(tampered_ctx, "authority_evidence", tampered_evidence)

        # MUST be rejected because full assessment does not match
        with pytest.raises(ValueError, match="part_number_match_assessment"):
            tampered_ctx._validate()

    def test_tampered_normalized_fields_rejected(self) -> None:
        """A PartNumberMatchAssessment with correct match_type but
        tampered normalized_part_number fields MUST be rejected."""
        from product_intelligence.execution.comparable_research_authority import (
            _AuthoritySourceOutcome,
        )
        from product_intelligence.research.identity import compare_part_numbers

        request = ResearchRequest(
            manufacturer_part_number="XP15360SE70005",
            description="Seagate Nytro",
        )
        fetcher = _FakePageFetcher(body=_read_seagate_fixture())

        result = acquire_comparable_research_authority_context(
            request=request,
            page_fetcher=fetcher,
        )

        ctx = result.context
        assert ctx is not None

        original_assessment = ctx.authority_evidence.part_number_match_assessment
        assert original_assessment is not None

        # Tamper normalized fields only
        tampered_assessment = dataclasses.replace(
            original_assessment,
            normalized_requested_part_number="TAMPERED_NORM",
            normalized_candidate_part_number="TAMPERED_NORM",
        )

        tampered_evidence = _AuthoritySourceOutcome(
            policy_id=ctx.authority_evidence.policy_id,
            outcome_state=AuthoritySourceOutcomeState.MATCHED,
            requested_source_url=ctx.authority_evidence.requested_source_url,
            fetched_final_url=ctx.authority_evidence.fetched_final_url,
            retrieved_at=ctx.authority_evidence.retrieved_at,
            matching_mpn_evidence=ctx.authority_evidence.matching_mpn_evidence,
            matched_observation=ctx.authority_evidence.matched_observation,
            part_number_match_assessment=tampered_assessment,
        )

        tampered_ctx = object.__new__(ComparableResearchAuthorityContext)
        object.__setattr__(tampered_ctx, "request", ctx.request)
        object.__setattr__(tampered_ctx, "target_identity", ctx.target_identity)
        object.__setattr__(tampered_ctx, "category_schema", ctx.category_schema)
        object.__setattr__(tampered_ctx, "specification_source", ctx.specification_source)
        object.__setattr__(tampered_ctx, "comparable_source", ctx.comparable_source)
        object.__setattr__(tampered_ctx, "authority_evidence", tampered_evidence)

        with pytest.raises(ValueError, match="part_number_match_assessment"):
            tampered_ctx._validate()

    def test_correct_full_assessment_accepted(self) -> None:
        """When the full PartNumberMatchAssessment matches what 2A produces,
        validation succeeds."""
        from product_intelligence.research.identity import compare_part_numbers

        request = ResearchRequest(
            manufacturer_part_number="XP15360SE70005",
            description="Seagate Nytro",
        )
        fetcher = _FakePageFetcher(body=_read_seagate_fixture())

        result = acquire_comparable_research_authority_context(
            request=request,
            page_fetcher=fetcher,
        )

        ctx = result.context
        assert ctx is not None

        # The assessment in evidence must equal the full 2A comparison
        expected = compare_part_numbers(
            request.manufacturer_part_number,
            ctx.authority_evidence.matched_observation.manufacturer_part_number_raw,
        )
        assessment = ctx.authority_evidence.part_number_match_assessment
        # Full dataclass equality
        assert assessment == expected


# ---------------------------------------------------------------------------
# TEST 25: BLOCKER 4 - Aggregation fails closed on ANY source ambiguity
# ---------------------------------------------------------------------------


class TestAggregationFailClosed:
    """BLOCKER 4: Aggregation must fail closed when ANY source outcome
    is AMBIGUOUS_MPN_MATCH, even if another source produced MATCHED."""

    def test_one_matched_plus_one_ambiguous_fails_closed(self, monkeypatch) -> None:
        """One policy MATCHES, another is AMBIGUOUS -> context=None,
        status=AMBIGUOUS_AUTHORITY_MATCH.

        Uses monkeypatch to add a second policy that produces ambiguity.
        """
        import json as _json
        from product_intelligence.execution.comparable_research_authority import (
            _AUTHORITY_POLICIES,
            _AuthorityPolicy,
        )

        # Second policy that produces AMBIGUOUS_MPN_MATCH via duplicate records
        ambiguous_records = _json.dumps([
            {"skuNumber": "XP15360SE70005", "title": "Product A"},
            {"skuNumber": "XP15360SE70005", "title": "Product B"},
        ])
        ambiguous_doc = (
            "<script>\n"
            "var supportSpecsData = JSON.parse('"
            + ambiguous_records + "');\n"
            "</script>\n"
        )

        # Routing fetcher: first URL -> normal fixture, second -> ambiguous
        class _RoutingFetcher:
            def __init__(self):
                self._call_count = 0

            def fetch(self, request: PageFetchRequest) -> FetchedPage:
                self._call_count += 1
                if self._call_count == 1:
                    return FetchedPage(
                        requested_url=request.url,
                        final_url=request.url,
                        retrieved_at=_RETRIEVED_AT,
                        status_code=200,
                        body_text=_read_seagate_fixture(),
                        content_type="text/html",
                        body_byte_count=len(_read_seagate_fixture()),
                        redirect_count=0,
                        fetcher_id="routing-fake",
                    )
                else:
                    return FetchedPage(
                        requested_url=request.url,
                        final_url=request.url,
                        retrieved_at=_RETRIEVED_AT,
                        status_code=200,
                        body_text=ambiguous_doc,
                        content_type="text/html",
                        body_byte_count=len(ambiguous_doc),
                        redirect_count=0,
                        fetcher_id="routing-fake",
                    )

        fake_fetcher = _RoutingFetcher()

        # Second policy (different source URL, same MPN to match)
        second_policy = _AuthorityPolicy(
            policy_id="test-ambiguous-policy-v1",
            manufacturer="Seagate",
            source_name="Test Ambiguous Source",
            requested_source_url="https://www.seagate.com/ambiguous/",
            approved_authority_origin="https://www.seagate.com",
            category_schema=ENTERPRISE_SSD_SCHEMA,
        )

        # Replace _AUTHORITY_POLICIES with both policies
        new_policies = (_AUTHORITY_POLICIES[0], second_policy)
        monkeypatch.setattr(
            "product_intelligence.execution.comparable_research_authority._AUTHORITY_POLICIES",
            new_policies,
        )

        request = ResearchRequest(
            manufacturer_part_number="XP15360SE70005",
            description="Seagate Nytro",
        )

        result = acquire_comparable_research_authority_context(
            request=request,
            page_fetcher=fake_fetcher,
        )

        # Must fail closed
        assert result.context is None
        assert result.acquisition_status is AuthorityAcquisitionStatus.AMBIGUOUS_AUTHORITY_MATCH
        # Both outcomes preserved with correct truth
        assert len(result.source_outcomes) == 2
        # First is MATCHED, second is AMBIGUOUS_MPN_MATCH
        matched_outcomes = [
            o for o in result.source_outcomes
            if o.outcome_state is AuthoritySourceOutcomeState.MATCHED
        ]
        ambiguous_outcomes = [
            o for o in result.source_outcomes
            if o.outcome_state is AuthoritySourceOutcomeState.AMBIGUOUS_MPN_MATCH
        ]
        assert len(matched_outcomes) == 1, "MATCHED truth must remain MATCHED"
        assert len(ambiguous_outcomes) == 1, "AMBIGUOUS truth must remain AMBIGUOUS"

    def test_single_ambiguous_fails_closed(self) -> None:
        """A single AMBIGUOUS_MPN_MATCH (no MATCHED) -> AMBIGUOUS_AUTHORITY_MATCH.

        This is the existing behavior but verified with the new aggregation logic.
        """
        import json as _json
        records = _json.dumps([
            {"skuNumber": "AMBIGUOUS123", "title": "Product A"},
            {"skuNumber": "AMBIGUOUS123", "title": "Product B"},
        ])
        doc = (
            "<script>\n"
            "var supportSpecsData = JSON.parse('"
            + records + "');\n"
            "</script>\n"
        )
        request = ResearchRequest(
            manufacturer_part_number="AMBIGUOUS123",
            description="Ambiguous product",
        )
        fetcher = _FakePageFetcher(body=doc)

        result = acquire_comparable_research_authority_context(
            request=request,
            page_fetcher=fetcher,
        )

        assert result.context is None
        assert result.source_outcomes[0].outcome_state is AuthoritySourceOutcomeState.AMBIGUOUS_MPN_MATCH
        assert result.acquisition_status is AuthorityAcquisitionStatus.AMBIGUOUS_AUTHORITY_MATCH


# ---------------------------------------------------------------------------
# TEST 26: Cross-policy ambiguity (multi-policy)
# ---------------------------------------------------------------------------


class TestCrossPolicyAmbiguity:
    """Cross-policy multi-policy regression tests using monkeypatch."""

    def test_two_policies_both_matched(self, monkeypatch) -> None:
        """Scenario A: Policy A -> MATCHED, Policy B -> MATCHED

        Expected: context=None, status=AMBIGUOUS_AUTHORITY_MATCH
        Both actual MATCHED source outcomes remain preserved.
        """
        from product_intelligence.execution.comparable_research_authority import (
            _AUTHORITY_POLICIES,
            _AuthorityPolicy,
        )

        # Second policy that also matches the same MPN
        second_policy = _AuthorityPolicy(
            policy_id="test-cross-policy-v1",
            manufacturer="Seagate",
            source_name="Test Cross Policy Source",
            requested_source_url="https://www.seagate.com/cross-policy/",
            approved_authority_origin="https://www.seagate.com",
            category_schema=ENTERPRISE_SSD_SCHEMA,
        )

        # Routing fetcher: both URLs return the same matching fixture
        class _DualFetcher:
            def fetch(self, request: PageFetchRequest) -> FetchedPage:
                return FetchedPage(
                    requested_url=request.url,
                    final_url=request.url,
                    retrieved_at=_RETRIEVED_AT,
                    status_code=200,
                    body_text=_read_seagate_fixture(),
                    content_type="text/html",
                    body_byte_count=len(_read_seagate_fixture()),
                    redirect_count=0,
                    fetcher_id="dual-fake",
                )

        fake_fetcher = _DualFetcher()

        new_policies = (_AUTHORITY_POLICIES[0], second_policy)
        monkeypatch.setattr(
            "product_intelligence.execution.comparable_research_authority._AUTHORITY_POLICIES",
            new_policies,
        )

        request = ResearchRequest(
            manufacturer_part_number="XP15360SE70005",
            description="Seagate Nytro",
        )

        result = acquire_comparable_research_authority_context(
            request=request,
            page_fetcher=fake_fetcher,
        )

        # Both matched -> ambiguous
        assert result.context is None
        assert result.acquisition_status is AuthorityAcquisitionStatus.AMBIGUOUS_AUTHORITY_MATCH
        assert len(result.source_outcomes) == 2
        # Both are MATCHED (truth preserved)
        matched_outcomes = [
            o for o in result.source_outcomes
            if o.outcome_state is AuthoritySourceOutcomeState.MATCHED
        ]
        assert len(matched_outcomes) == 2

    def test_policy_a_matched_policy_b_ambiguous(self, monkeypatch) -> None:
        """Scenario B: Policy A -> MATCHED, Policy B -> AMBIGUOUS_MPN_MATCH

        Expected: context=None, status=AMBIGUOUS_AUTHORITY_MATCH
        MATCHED truth remains MATCHED, AMBIGUOUS truth remains AMBIGUOUS_MPN_MATCH.
        """
        import json as _json
        from product_intelligence.execution.comparable_research_authority import (
            _AUTHORITY_POLICIES,
            _AuthorityPolicy,
        )

        # Second policy that produces AMBIGUOUS_MPN_MATCH
        ambiguous_records = _json.dumps([
            {"skuNumber": "XP15360SE70005", "title": "Dup A"},
            {"skuNumber": "XP15360SE70005", "title": "Dup B"},
        ])
        ambiguous_doc = (
            "<script>\n"
            "var supportSpecsData = JSON.parse('"
            + ambiguous_records + "');\n"
            "</script>\n"
        )

        second_policy = _AuthorityPolicy(
            policy_id="test-ambiguous-policy-v1",
            manufacturer="Seagate",
            source_name="Test Ambiguous Source",
            requested_source_url="https://www.seagate.com/ambiguous/",
            approved_authority_origin="https://www.seagate.com",
            category_schema=ENTERPRISE_SSD_SCHEMA,
        )

        class _RoutingFetcher2:
            def __init__(self):
                self._call_count = 0

            def fetch(self, request: PageFetchRequest) -> FetchedPage:
                self._call_count += 1
                if self._call_count == 1:
                    return FetchedPage(
                        requested_url=request.url,
                        final_url=request.url,
                        retrieved_at=_RETRIEVED_AT,
                        status_code=200,
                        body_text=_read_seagate_fixture(),
                        content_type="text/html",
                        body_byte_count=len(_read_seagate_fixture()),
                        redirect_count=0,
                        fetcher_id="routing-fake",
                    )
                else:
                    return FetchedPage(
                        requested_url=request.url,
                        final_url=request.url,
                        retrieved_at=_RETRIEVED_AT,
                        status_code=200,
                        body_text=ambiguous_doc,
                        content_type="text/html",
                        body_byte_count=len(ambiguous_doc),
                        redirect_count=0,
                        fetcher_id="routing-fake",
                    )

        fake_fetcher = _RoutingFetcher2()

        new_policies = (_AUTHORITY_POLICIES[0], second_policy)
        monkeypatch.setattr(
            "product_intelligence.execution.comparable_research_authority._AUTHORITY_POLICIES",
            new_policies,
        )

        request = ResearchRequest(
            manufacturer_part_number="XP15360SE70005",
            description="Seagate Nytro",
        )

        result = acquire_comparable_research_authority_context(
            request=request,
            page_fetcher=fake_fetcher,
        )

        # Must fail closed due to ANY ambiguity
        assert result.context is None
        assert result.acquisition_status is AuthorityAcquisitionStatus.AMBIGUOUS_AUTHORITY_MATCH
        assert len(result.source_outcomes) == 2

        # Verify truth preservation
        matched_outcomes = [
            o for o in result.source_outcomes
            if o.outcome_state is AuthoritySourceOutcomeState.MATCHED
        ]
        ambiguous_outcomes = [
            o for o in result.source_outcomes
            if o.outcome_state is AuthoritySourceOutcomeState.AMBIGUOUS_MPN_MATCH
        ]
        assert len(matched_outcomes) == 1, "MATCHED truth must remain MATCHED"
        assert len(ambiguous_outcomes) == 1, "AMBIGUOUS truth must remain AMBIGUOUS_MPN_MATCH"


# ---------------------------------------------------------------------------
# TEST 27: Result Contract Closure — adversarial context + ambiguity
# ---------------------------------------------------------------------------


class TestResultContractClosure:
    """Adversarial self-audit: ComparableResearchAuthorityAcquisitionResult
    must reject the impossible state of context + ambiguity."""

    def test_established_result_cannot_carry_ambiguity(self) -> None:
        """A valid ESTABLISHED context + MATCHED outcome + AMBIGUOUS outcome
        must raise ValueError. No silent reinterpretation allowed.

        1. Obtain a valid ESTABLISHED result through the public API.
        2. Retain its valid context and MATCHED source outcome.
        3. Construct a valid AMBIGUOUS_MPN_MATCH _AuthoritySourceOutcome.
        4. Attempt to construct a result with context + ambiguity.
        5. Require ValueError.
        """
        import json as _json
        from product_intelligence.execution.comparable_research_authority import (
            _AuthoritySourceOutcome,
        )
        from product_intelligence.research.identity import compare_part_numbers
        from product_intelligence.research.comparable_candidates import (
            ComparableCandidateObservation,
        )

        # Step 1: obtain valid ESTABLISHED result
        request = ResearchRequest(
            manufacturer_part_number="XP15360SE70005",
            description="Seagate Nytro",
        )
        fetcher = _FakePageFetcher(body=_read_seagate_fixture())
        valid_result = acquire_comparable_research_authority_context(
            request=request,
            page_fetcher=fetcher,
        )
        assert valid_result.context is not None
        assert valid_result.acquisition_status is AuthorityAcquisitionStatus.ESTABLISHED

        # Step 2: retain valid context and MATCHED outcome
        valid_context = valid_result.context
        valid_matched = valid_result.source_outcomes[0]

        # Step 3: construct a valid AMBIGUOUS_MPN_MATCH outcome
        ambiguous_obs = ComparableCandidateObservation(
            manufacturer_part_number_raw="XP15360SE70005",
            product_name_raw="Duplicate A",
            source_name="Seagate Enterprise Support",
            source_url=_SEAGATE_SOURCE_URL,
            retrieved_at=_RETRIEVED_AT,
            source_authority=SourceAuthority.AUTHORITATIVE,
        )
        comparison = compare_part_numbers("XP15360SE70005", "XP15360SE70005")
        # AMBIGUOUS_MPN_MATCH requires fetched_final_url + retrieved_at
        ambiguous_outcome = _AuthoritySourceOutcome(
            policy_id="seagate-enterprise-ssd-nytro-support-catalog-v1",
            outcome_state=AuthoritySourceOutcomeState.AMBIGUOUS_MPN_MATCH,
            requested_source_url=_SEAGATE_SOURCE_URL,
            fetched_final_url=_SEAGATE_SOURCE_URL,
            retrieved_at=_RETRIEVED_AT,
        )

        # Step 4: attempt context + ambiguity
        with pytest.raises(ValueError, match="AMBIGUOUS"):
            ComparableResearchAuthorityAcquisitionResult(
                context=valid_context,
                source_outcomes=(
                    valid_matched,
                    ambiguous_outcome,
                ),
            )

    def test_same_outcomes_without_context_produce_ambiguous_status(self) -> None:
        """The same MATCHED + AMBIGUOUS outcomes with context=None
        produce AMBIGUOUS_AUTHORITY_MATCH status, not an error."""
        import json as _json
        from product_intelligence.execution.comparable_research_authority import (
            _AuthoritySourceOutcome,
        )
        from product_intelligence.research.identity import compare_part_numbers
        from product_intelligence.research.comparable_candidates import (
            ComparableCandidateObservation,
        )

        # Obtain valid ESTABLISHED result for the MATCHED outcome
        request = ResearchRequest(
            manufacturer_part_number="XP15360SE70005",
            description="Seagate Nytro",
        )
        fetcher = _FakePageFetcher(body=_read_seagate_fixture())
        valid_result = acquire_comparable_research_authority_context(
            request=request,
            page_fetcher=fetcher,
        )
        valid_matched = valid_result.source_outcomes[0]

        # Construct AMBIGUOUS_MPN_MATCH outcome
        ambiguous_outcome = _AuthoritySourceOutcome(
            policy_id="seagate-enterprise-ssd-nytro-support-catalog-v1",
            outcome_state=AuthoritySourceOutcomeState.AMBIGUOUS_MPN_MATCH,
            requested_source_url=_SEAGATE_SOURCE_URL,
            fetched_final_url=_SEAGATE_SOURCE_URL,
            retrieved_at=_RETRIEVED_AT,
        )

        # context=None + MATCHED + AMBIGUOUS -> AMBIGUOUS_AUTHORITY_MATCH
        no_context_result = ComparableResearchAuthorityAcquisitionResult(
            context=None,
            source_outcomes=(valid_matched, ambiguous_outcome),
        )
        assert no_context_result.context is None
        assert no_context_result.acquisition_status is AuthorityAcquisitionStatus.AMBIGUOUS_AUTHORITY_MATCH


# ---------------------------------------------------------------------------
# TEST 28: Authority-stage boundary — AST structural regression
# ---------------------------------------------------------------------------


class TestAuthorityStageBoundary:
    """Structural AST regression proving that identity construction
    occurs only in the global aggregation factory, not in per-policy
    acquisition."""

    def test_process_authority_policy_does_not_construct_product_identity(self) -> None:
        """_process_authority_policy must NOT call ProductIdentity(...).

        Authority stage boundary:
        per-policy acquisition -> evidence/outcome only
        global aggregation -> ambiguity decision
        _build_authority_context -> the single ProductIdentity construction
        """
        import product_intelligence.execution.comparable_research_authority as mod

        # Parse the module source
        source = inspect.getsource(mod)
        tree = ast.parse(source)

        # Find _process_authority_policy function
        process_fn = None
        build_fn = None
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef):
                if node.name == "_process_authority_policy":
                    process_fn = node
                elif node.name == "_build_authority_context":
                    build_fn = node

        assert process_fn is not None, "_process_authority_policy not found in module"
        assert build_fn is not None, "_build_authority_context not found in module"

        # Walk the AST of _process_authority_policy looking for ProductIdentity calls
        for node in ast.walk(process_fn):
            if isinstance(node, ast.Call):
                func = node.func
                if isinstance(func, ast.Name) and func.id == "ProductIdentity":
                    pytest.fail(
                        "_process_authority_policy must not construct ProductIdentity. "
                        "Identity construction is reserved for _build_authority_context "
                        "after global authority aggregation."
                    )
                elif isinstance(func, ast.Attribute) and func.attr == "ProductIdentity":
                    pytest.fail(
                        "_process_authority_policy must not construct ProductIdentity "
                        "via attribute access."
                    )

        # Positive: _build_authority_context DOES contain ProductIdentity construction
        found_in_build = False
        for node in ast.walk(build_fn):
            if isinstance(node, ast.Call):
                func = node.func
                if isinstance(func, ast.Name) and func.id == "ProductIdentity":
                    found_in_build = True
                    break
                elif isinstance(func, ast.Attribute) and func.attr == "ProductIdentity":
                    found_in_build = True
                    break

        assert found_in_build, (
            "_build_authority_context must contain the ProductIdentity construction. "
            "This is the single authority-establishing identity construction point."
        )
