"""Tests for PRODUCT-INTEL.6C — Specification evidence execution.

Tests the execution layer composition:
    research_enterprise_ssd_specifications(...)

Uses fake PageFetcher instances. Covers source contract, acquisition,
pipeline, provenance, self-consistency, and all required test cases.
"""

from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
from typing import Any

import pytest

from product_intelligence.domain.enums import IdentityMatchType
from product_intelligence.domain.models import ProductIdentity
from product_intelligence.providers.page import (
    FetchedPage,
    PageFetchError,
    PageFetchRequest,
    UnsafeFetchTargetError,
)
from product_intelligence.research.enterprise_ssd import ENTERPRISE_SSD_SCHEMA
from product_intelligence.research.specifications import (
    NormalizedSpecificationObservation,
    ProductSpecificationSet,
    ResolutionState,
    SourceAuthority,
    SpecificationObservation,
    SpecificationResolution,
    SpecificationValue,
    resolve_specification,
)
from product_intelligence.execution.specification_evidence import (
    SpecificationEvidenceResult,
    SpecificationEvidenceSource,
    SpecificationSourceOutcome,
    SourceOutcomeState,
    research_enterprise_ssd_specifications,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

def _identity() -> ProductIdentity:
    return ProductIdentity(
        manufacturer_part_number="MZ-QL23T800",
        match_type=IdentityMatchType.EXACT,
    )


def _seagate_identity() -> ProductIdentity:
    return ProductIdentity(
        manufacturer_part_number="XP15360SE70005",
        match_type=IdentityMatchType.EXACT,
    )


def _now() -> datetime:
    return datetime(2025, 8, 20, 12, 0, 0, tzinfo=timezone.utc)


def _different_identity() -> ProductIdentity:
    return ProductIdentity(
        manufacturer_part_number="DIFFERENT-001",
        match_type=IdentityMatchType.EXACT,
    )


def _unestablished_identity() -> ProductIdentity:
    return ProductIdentity(match_type=IdentityMatchType.UNKNOWN)


def _make_embedded_json_document(
    sku_number: str,
    features: list[tuple[str, str]],
) -> str:
    """Build a minimal HTML document with embedded JSON product data.

    Uses the same structure as the real Seagate fixture:
        var supportSpecsData = JSON.parse('[...]')
    """
    import json
    records = [
        {
            "skuNumber": sku_number,
            "features": [
                {"title": title, "value": value}
                for title, value in features
            ],
        }
    ]
    json_str = json.dumps(records)
    js_escaped = json_str.replace("\\", "\\\\").replace("'", "\\'")
    return (
        '<script>\n'
        'var supportSpecsData = JSON.parse(\''
        f'{js_escaped}'
        '\');\n'
        '</script>'
    )


def _fake_fetched_page(
    *,
    requested_url: str = "https://example.com/req",
    final_url: str = "https://example.com/final",
    body_text: str = "",
    retrieved_at: datetime | None = None,
) -> FetchedPage:
    return FetchedPage(
        requested_url=requested_url,
        final_url=final_url,
        retrieved_at=retrieved_at or _now(),
        status_code=200,
        body_text=body_text,
        content_type="text/html; charset=utf-8",
        body_byte_count=len(body_text),
        redirect_count=0,
        fetcher_id="fake",
    )


# ---------------------------------------------------------------------------
# Fake PageFetcher
# ---------------------------------------------------------------------------


class _FakePageFetcher:
    """Controllable PageFetcher for tests."""

    def __init__(
        self,
        *,
        fetched_page: FetchedPage | None = None,
        raise_error: Exception | None = None,
    ) -> None:
        self._fetched_page = fetched_page
        self._raise_error = raise_error
        self.fetch_calls: list[PageFetchRequest] = []

    def fetch(self, request: PageFetchRequest) -> FetchedPage:
        self.fetch_calls.append(request)
        if self._raise_error is not None:
            raise self._raise_error
        if self._fetched_page is None:
            return _fake_fetched_page(body_text="")
        return self._fetched_page


def _make_source(
    identity: ProductIdentity,
    *,
    name: str = "Test",
    url: str = "https://example.com",
    authority: SourceAuthority = SourceAuthority.AUTHORITATIVE,
) -> SpecificationEvidenceSource:
    return SpecificationEvidenceSource(
        product_identity=identity,
        source_name=name,
        source_url=url,
        source_authority=authority,
    )


# ===================================================================
# A. Source contract
# ===================================================================


class TestSourceContract:
    """Test SpecificationEvidenceSource validation."""

    def test_established_identity_required(self) -> None:
        with pytest.raises(ValueError, match="established ProductIdentity"):
            SpecificationEvidenceSource(
                product_identity=_unestablished_identity(),
                source_name="Test",
                source_url="https://example.com",
                source_authority=SourceAuthority.AUTHORITATIVE,
            )

    def test_source_name_validation(self) -> None:
        with pytest.raises(ValueError, match="source_name"):
            SpecificationEvidenceSource(
                product_identity=_identity(),
                source_name="",
                source_url="https://example.com",
                source_authority=SourceAuthority.AUTHORITATIVE,
            )

    def test_source_url_validation_empty(self) -> None:
        with pytest.raises(ValueError, match="source_url"):
            SpecificationEvidenceSource(
                product_identity=_identity(),
                source_name="Test",
                source_url="",
                source_authority=SourceAuthority.AUTHORITATIVE,
            )

    def test_source_url_validation_not_http(self) -> None:
        with pytest.raises(ValueError, match="source_url"):
            SpecificationEvidenceSource(
                product_identity=_identity(),
                source_name="Test",
                source_url="ftp://example.com/page",
                source_authority=SourceAuthority.AUTHORITATIVE,
            )

    def test_source_url_validation_no_host(self) -> None:
        with pytest.raises(ValueError, match="source_url"):
            SpecificationEvidenceSource(
                product_identity=_identity(),
                source_name="Test",
                source_url="https:///relative",
                source_authority=SourceAuthority.AUTHORITATIVE,
            )

    def test_source_url_validation_credentials_rejected(self) -> None:
        with pytest.raises(ValueError, match="source_url"):
            SpecificationEvidenceSource(
                product_identity=_identity(),
                source_name="Test",
                source_url="https://user:pass@example.com",
                source_authority=SourceAuthority.AUTHORITATIVE,
            )

    def test_source_authority_exact_type(self) -> None:
        with pytest.raises(TypeError, match="source_authority must be a SourceAuthority"):
            SpecificationEvidenceSource(
                product_identity=_identity(),
                source_name="Test",
                source_url="https://example.com",
                source_authority="AUTHORITATIVE",  # type: ignore
            )

    def test_valid_source(self) -> None:
        source = SpecificationEvidenceSource(
            product_identity=_identity(),
            source_name="Samsung Business",
            source_url="https://www.samsung.com/us/product",
            source_authority=SourceAuthority.AUTHORITATIVE,
        )
        assert source.source_name == "Samsung Business"
        assert source.source_authority is SourceAuthority.AUTHORITATIVE


# ===================================================================
# B. Cross-product fail-closed
# ===================================================================


class TestCrossProductFailClosed:
    """Cross-product source input fails closed BEFORE acquisition."""

    def test_cross_product_source_rejected_before_fetch(self) -> None:
        target = _identity()
        other = _different_identity()
        fetcher = _FakePageFetcher()

        source = SpecificationEvidenceSource(
            product_identity=other,
            source_name="Other",
            source_url="https://example.com",
            source_authority=SourceAuthority.SECONDARY,
        )

        with pytest.raises(ValueError, match="Cross-product source rejected"):
            research_enterprise_ssd_specifications(
                product_identity=target,
                sources=(source,),
                page_fetcher=fetcher,
            )

        assert len(fetcher.fetch_calls) == 0


# ===================================================================
# C. Acquisition
# ===================================================================


class TestAcquisition:
    """Test page acquisition and extraction outcomes."""

    def test_successful_source(self) -> None:
        identity = _identity()
        document = _make_embedded_json_document(
            "MZ-QL23T800",
            [("Form Factor", "2.5 in")],
        )
        fetcher = _FakePageFetcher(
            fetched_page=_fake_fetched_page(body_text=document),
        )
        source = _make_source(identity)
        result = research_enterprise_ssd_specifications(
            product_identity=identity,
            sources=(source,),
            page_fetcher=fetcher,
        )
        assert len(result.source_outcomes) == 1
        assert result.source_outcomes[0].outcome_state is SourceOutcomeState.EXTRACTED
        assert result.source_outcomes[0].observation_count == 1

    def test_requested_url_is_source_url(self) -> None:
        """The requested URL is always available from source.source_url.
        There is no separate requested_url field on the outcome."""
        identity = _identity()
        document = _make_embedded_json_document(
            "MZ-QL23T800",
            [("Form Factor", "2.5 in")],
        )
        fetcher = _FakePageFetcher(
            fetched_page=_fake_fetched_page(
                requested_url="https://example.com/redirect-source",
                final_url="https://example.com/final-destination",
                body_text=document,
            ),
        )
        source = _make_source(
            identity,
            url="https://example.com/redirect-source",
        )
        result = research_enterprise_ssd_specifications(
            product_identity=identity,
            sources=(source,),
            page_fetcher=fetcher,
        )
        outcome = result.source_outcomes[0]
        # Requested URL is available from source.source_url
        assert outcome.source.source_url == "https://example.com/redirect-source"
        assert outcome.final_url == "https://example.com/final-destination"

    def test_retrieved_at_from_fetched_page(self) -> None:
        identity = _identity()
        custom_time = datetime(2025, 7, 15, 8, 30, 0, tzinfo=timezone.utc)
        document = _make_embedded_json_document(
            "MZ-QL23T800",
            [("Form Factor", "2.5 in")],
        )
        fetcher = _FakePageFetcher(
            fetched_page=_fake_fetched_page(
                body_text=document,
                retrieved_at=custom_time,
            ),
        )
        source = _make_source(identity)
        result = research_enterprise_ssd_specifications(
            product_identity=identity,
            sources=(source,),
            page_fetcher=fetcher,
        )
        outcome = result.source_outcomes[0]
        assert outcome.retrieved_at == custom_time
        obs = result.normalized_observations[0].observation
        assert obs.retrieved_at == custom_time

    def test_page_fetch_error_becomes_fetch_failed(self) -> None:
        identity = _identity()
        fetcher = _FakePageFetcher(
            raise_error=PageFetchError("connection refused"),
        )
        source = _make_source(identity)
        result = research_enterprise_ssd_specifications(
            product_identity=identity,
            sources=(source,),
            page_fetcher=fetcher,
        )
        outcome = result.source_outcomes[0]
        assert outcome.outcome_state is SourceOutcomeState.FETCH_FAILED
        assert outcome.observation_count == 0

    def test_unsafe_fetch_target_error_becomes_source_refused(self) -> None:
        identity = _identity()
        fetcher = _FakePageFetcher(
            raise_error=UnsafeFetchTargetError("private address"),
        )
        source = _make_source(identity)
        result = research_enterprise_ssd_specifications(
            product_identity=identity,
            sources=(source,),
            page_fetcher=fetcher,
        )
        outcome = result.source_outcomes[0]
        assert outcome.outcome_state is SourceOutcomeState.SOURCE_REFUSED
        assert outcome.observation_count == 0

    def test_successful_zero_extraction_becomes_no_observations(self) -> None:
        identity = _identity()
        fetcher = _FakePageFetcher(
            fetched_page=_fake_fetched_page(body_text="<html><body>No specs</body></html>"),
        )
        source = _make_source(identity)
        result = research_enterprise_ssd_specifications(
            product_identity=identity,
            sources=(source,),
            page_fetcher=fetcher,
        )
        outcome = result.source_outcomes[0]
        assert outcome.outcome_state is SourceOutcomeState.NO_OBSERVATIONS
        assert outcome.observation_count == 0

    def test_next_source_runs_after_fetch_failure(self) -> None:
        identity = _identity()
        document = _make_embedded_json_document(
            "MZ-QL23T800",
            [("Form Factor", "2.5 in")],
        )

        class _SequentialFetcher:
            def __init__(self) -> None:
                self._call_count = 0

            def fetch(self, request: PageFetchRequest) -> FetchedPage:
                self._call_count += 1
                if self._call_count == 1:
                    raise PageFetchError("fail")
                return _fake_fetched_page(body_text=document)

        source1 = _make_source(identity, name="Source1", url="https://example.com/1", authority=SourceAuthority.SECONDARY)
        source2 = _make_source(identity, name="Source2", url="https://example.com/2")
        result = research_enterprise_ssd_specifications(
            product_identity=identity,
            sources=(source1, source2),
            page_fetcher=_SequentialFetcher(),
        )
        assert result.source_outcomes[0].outcome_state is SourceOutcomeState.FETCH_FAILED
        assert result.source_outcomes[1].outcome_state is SourceOutcomeState.EXTRACTED

    def test_source_outcome_preserves_source_authority(self) -> None:
        identity = _identity()
        document = _make_embedded_json_document(
            "MZ-QL23T800",
            [("Form Factor", "2.5 in")],
        )
        fetcher = _FakePageFetcher(
            fetched_page=_fake_fetched_page(body_text=document),
        )
        source = _make_source(identity, authority=SourceAuthority.SECONDARY)
        result = research_enterprise_ssd_specifications(
            product_identity=identity,
            sources=(source,),
            page_fetcher=fetcher,
        )
        outcome = result.source_outcomes[0]
        assert outcome.source.source_authority is SourceAuthority.SECONDARY
        assert outcome.source.source_name == "Test"


# ===================================================================
# D. Pipeline — extraction → 6B normalization → 6A resolution
# ===================================================================


class TestPipeline:
    """Test the full pipeline from extraction through resolution."""

    def test_full_pipeline(self) -> None:
        identity = _identity()
        document = _make_embedded_json_document(
            "MZ-QL23T800",
            [("Form Factor", "2.5 in")],
        )
        fetcher = _FakePageFetcher(
            fetched_page=_fake_fetched_page(body_text=document),
        )
        source = _make_source(identity)
        result = research_enterprise_ssd_specifications(
            product_identity=identity,
            sources=(source,),
            page_fetcher=fetcher,
        )
        assert len(result.normalized_observations) == 1
        assert len(result.product_specification_set.resolutions) == 12

    def test_all_12_resolutions_always_exist(self) -> None:
        identity = _identity()
        fetcher = _FakePageFetcher(
            fetched_page=_fake_fetched_page(body_text="<html></html>"),
        )
        source = _make_source(identity)
        result = research_enterprise_ssd_specifications(
            product_identity=identity,
            sources=(source,),
            page_fetcher=fetcher,
        )
        assert len(result.product_specification_set.resolutions) == 12
        for key in ENTERPRISE_SSD_SCHEMA.definitions:
            assert key in result.product_specification_set.resolutions

    def test_unknown_explicit_for_missing_fields(self) -> None:
        identity = _identity()
        document = _make_embedded_json_document(
            "MZ-QL23T800",
            [("Form Factor", "2.5 in")],
        )
        fetcher = _FakePageFetcher(
            fetched_page=_fake_fetched_page(body_text=document),
        )
        source = _make_source(identity)
        result = research_enterprise_ssd_specifications(
            product_identity=identity,
            sources=(source,),
            page_fetcher=fetcher,
        )
        assert (
            result.product_specification_set.resolutions["physical_form_factor"].state
            is ResolutionState.VERIFIED
        )
        assert (
            result.product_specification_set.resolutions["endurance_dwpd"].state
            is ResolutionState.UNKNOWN
        )

    def test_authoritative_evidence_produces_verified(self) -> None:
        identity = _identity()
        document = _make_embedded_json_document(
            "MZ-QL23T800",
            [("Form Factor", "2.5 in")],
        )
        fetcher = _FakePageFetcher(
            fetched_page=_fake_fetched_page(body_text=document),
        )
        source = _make_source(identity, authority=SourceAuthority.AUTHORITATIVE)
        result = research_enterprise_ssd_specifications(
            product_identity=identity,
            sources=(source,),
            page_fetcher=fetcher,
        )
        resolution = result.product_specification_set.resolutions["physical_form_factor"]
        assert resolution.state is ResolutionState.VERIFIED

    def test_secondary_only_produces_unverified(self) -> None:
        identity = _identity()
        document = _make_embedded_json_document(
            "MZ-QL23T800",
            [("Form Factor", "2.5 in")],
        )
        fetcher = _FakePageFetcher(
            fetched_page=_fake_fetched_page(body_text=document),
        )
        source = _make_source(identity, authority=SourceAuthority.SECONDARY)
        result = research_enterprise_ssd_specifications(
            product_identity=identity,
            sources=(source,),
            page_fetcher=fetcher,
        )
        resolution = result.product_specification_set.resolutions["physical_form_factor"]
        assert resolution.state is ResolutionState.UNVERIFIED

    def test_conflict_produces_conflict(self) -> None:
        """Two sources with different form factor values -> CONFLICT."""
        identity = _identity()
        doc1 = _make_embedded_json_document(
            "MZ-QL23T800",
            [("Form Factor", "2.5 in")],
        )
        doc2 = _make_embedded_json_document(
            "MZ-QL23T800",
            [("Form Factor", "M.2")],
        )

        class _DualFetcher:
            def __init__(self) -> None:
                self._call_count = 0

            def fetch(self, request: PageFetchRequest) -> FetchedPage:
                self._call_count += 1
                if self._call_count == 1:
                    return _fake_fetched_page(body_text=doc1)
                return _fake_fetched_page(body_text=doc2)

        source1 = _make_source(identity, authority=SourceAuthority.AUTHORITATIVE)
        source2 = _make_source(identity, authority=SourceAuthority.SECONDARY)
        result = research_enterprise_ssd_specifications(
            product_identity=identity,
            sources=(source1, source2),
            page_fetcher=_DualFetcher(),
        )
        resolution = result.product_specification_set.resolutions["physical_form_factor"]
        assert resolution.state is ResolutionState.CONFLICT

    def test_source_outcomes_retained_even_if_no_observation(self) -> None:
        identity = _identity()
        fetcher = _FakePageFetcher(
            fetched_page=_fake_fetched_page(body_text="<html>No specs</html>"),
        )
        source = _make_source(identity)
        result = research_enterprise_ssd_specifications(
            product_identity=identity,
            sources=(source,),
            page_fetcher=fetcher,
        )
        assert len(result.source_outcomes) == 1
        assert result.source_outcomes[0].outcome_state is SourceOutcomeState.NO_OBSERVATIONS

    def test_no_majority_voting_end_to_end(self) -> None:
        """9 SECONDARY sources -> Form Factor 2.5in,
        1 AUTHORITATIVE source -> Form Factor M.2.

        Result: CONFLICT (no majority voting).
        """
        identity = _identity()

        doc_secondary = _make_embedded_json_document(
            "MZ-QL23T800",
            [("Form Factor", "2.5 in")],
        )
        doc_authoritative = _make_embedded_json_document(
            "MZ-QL23T800",
            [("Form Factor", "M.2")],
        )

        class _MajorityFetcher:
            def __init__(self) -> None:
                self._call_count = 0
                self.fetch_calls: list[PageFetchRequest] = []

            def fetch(self, request: PageFetchRequest) -> FetchedPage:
                self._call_count += 1
                self.fetch_calls.append(request)
                if self._call_count == 10:
                    return _fake_fetched_page(body_text=doc_authoritative)
                return _fake_fetched_page(body_text=doc_secondary)

        secondary_sources = tuple(
            _make_source(
                identity,
                name=f"Secondary-{i}",
                url=f"https://example.com/secondary-{i}",
                authority=SourceAuthority.SECONDARY,
            )
            for i in range(9)
        )
        authoritative_source = _make_source(
            identity,
            name="Authoritative",
            url="https://example.com/authoritative",
            authority=SourceAuthority.AUTHORITATIVE,
        )
        all_sources = secondary_sources + (authoritative_source,)

        fetcher = _MajorityFetcher()
        result = research_enterprise_ssd_specifications(
            product_identity=identity,
            sources=all_sources,
            page_fetcher=fetcher,
        )

        assert len(fetcher.fetch_calls) == 10
        assert len(result.source_outcomes) == 10

        ff_resolution = result.product_specification_set.resolutions["physical_form_factor"]
        assert ff_resolution.state is ResolutionState.CONFLICT
        assert ff_resolution.resolved_value is None

        assert len(result.normalized_observations) == 10

        extracted_count = sum(
            outcome.observation_count
            for outcome in result.source_outcomes
            if outcome.outcome_state is SourceOutcomeState.EXTRACTED
        )
        assert extracted_count == len(result.normalized_observations)


# ===================================================================
# E. Provenance
# ===================================================================


class TestProvenance:
    """Test that the result preserves full provenance chains."""

    def test_result_identity_is_target_identity(self) -> None:
        target = _identity()
        document = _make_embedded_json_document(
            "MZ-QL23T800",
            [("Form Factor", "2.5 in")],
        )
        fetcher = _FakePageFetcher(
            fetched_page=_fake_fetched_page(body_text=document),
        )
        source = _make_source(target)
        result = research_enterprise_ssd_specifications(
            product_identity=target,
            sources=(source,),
            page_fetcher=fetcher,
        )
        assert result.product_identity is target

    def test_product_specification_set_identity_equals_result_identity(self) -> None:
        target = _identity()
        document = _make_embedded_json_document(
            "MZ-QL23T800",
            [("Form Factor", "2.5 in")],
        )
        fetcher = _FakePageFetcher(
            fetched_page=_fake_fetched_page(body_text=document),
        )
        source = _make_source(target)
        result = research_enterprise_ssd_specifications(
            product_identity=target,
            sources=(source,),
            page_fetcher=fetcher,
        )
        assert result.product_specification_set.product_identity is target

    def test_source_authority_preserved_through_chain(self) -> None:
        identity = _identity()
        document = _make_embedded_json_document(
            "MZ-QL23T800",
            [("Form Factor", "2.5 in")],
        )
        fetcher = _FakePageFetcher(
            fetched_page=_fake_fetched_page(body_text=document),
        )
        source = _make_source(identity, authority=SourceAuthority.SECONDARY)
        result = research_enterprise_ssd_specifications(
            product_identity=identity,
            sources=(source,),
            page_fetcher=fetcher,
        )
        norm_obs = result.normalized_observations[0]
        assert norm_obs.observation.source_authority is SourceAuthority.SECONDARY


# ===================================================================
# F. Programming exception propagation
# ===================================================================


class TestProgrammingExceptions:
    """Programming bugs propagate, they are not turned into UNKNOWN."""

    def test_established_identity_required_for_pipeline(self) -> None:
        with pytest.raises(ValueError, match="established ProductIdentity"):
            research_enterprise_ssd_specifications(
                product_identity=_unestablished_identity(),
                sources=(),
                page_fetcher=_FakePageFetcher(),
            )

    def test_non_product_identity_rejected(self) -> None:
        with pytest.raises(TypeError, match="product_identity must be a ProductIdentity"):
            research_enterprise_ssd_specifications(
                product_identity="not-an-identity",  # type: ignore
                sources=(),
                page_fetcher=_FakePageFetcher(),
            )


# ===================================================================
# G. Source outcome self-consistency (adversarial constructor tests)
# ===================================================================


class TestSourceOutcomeSelfConsistency:
    """SpecificationSourceOutcome rejects impossible state combinations."""

    def _make_source(self) -> SpecificationEvidenceSource:
        return _make_source(_identity())

    def test_extracted_requires_final_url(self) -> None:
        with pytest.raises(ValueError, match="EXTRACTED.*final_url"):
            SpecificationSourceOutcome(
                source=self._make_source(),
                final_url=None,
                retrieved_at=_now(),
                outcome_state=SourceOutcomeState.EXTRACTED,
                observation_count=1,
            )

    def test_extracted_requires_retrieved_at(self) -> None:
        with pytest.raises(ValueError, match="EXTRACTED.*retrieved_at"):
            SpecificationSourceOutcome(
                source=self._make_source(),
                final_url="https://example.com/final",
                retrieved_at=None,
                outcome_state=SourceOutcomeState.EXTRACTED,
                observation_count=1,
            )

    def test_extracted_requires_observation_count_gt_0(self) -> None:
        with pytest.raises(ValueError, match="EXTRACTED.*observation_count"):
            SpecificationSourceOutcome(
                source=self._make_source(),
                final_url="https://example.com/final",
                retrieved_at=_now(),
                outcome_state=SourceOutcomeState.EXTRACTED,
                observation_count=0,
            )

    def test_no_observations_requires_final_url(self) -> None:
        with pytest.raises(ValueError, match="NO_OBSERVATIONS.*final_url"):
            SpecificationSourceOutcome(
                source=self._make_source(),
                final_url=None,
                retrieved_at=_now(),
                outcome_state=SourceOutcomeState.NO_OBSERVATIONS,
                observation_count=0,
            )

    def test_no_observations_requires_retrieved_at(self) -> None:
        with pytest.raises(ValueError, match="NO_OBSERVATIONS.*retrieved_at"):
            SpecificationSourceOutcome(
                source=self._make_source(),
                final_url="https://example.com/final",
                retrieved_at=None,
                outcome_state=SourceOutcomeState.NO_OBSERVATIONS,
                observation_count=0,
            )

    def test_no_observations_requires_observation_count_0(self) -> None:
        with pytest.raises(ValueError, match="NO_OBSERVATIONS.*observation_count"):
            SpecificationSourceOutcome(
                source=self._make_source(),
                final_url="https://example.com/final",
                retrieved_at=_now(),
                outcome_state=SourceOutcomeState.NO_OBSERVATIONS,
                observation_count=5,
            )

    def test_fetch_failed_requires_no_final_url(self) -> None:
        with pytest.raises(ValueError, match="FETCH_FAILED.*final_url"):
            SpecificationSourceOutcome(
                source=self._make_source(),
                final_url="https://example.com/final",
                retrieved_at=_now(),
                outcome_state=SourceOutcomeState.FETCH_FAILED,
                observation_count=0,
            )

    def test_fetch_failed_requires_no_retrieved_at(self) -> None:
        with pytest.raises(ValueError, match="FETCH_FAILED.*retrieved_at"):
            SpecificationSourceOutcome(
                source=self._make_source(),
                final_url=None,
                retrieved_at=_now(),
                outcome_state=SourceOutcomeState.FETCH_FAILED,
                observation_count=0,
            )

    def test_fetch_failed_requires_observation_count_0(self) -> None:
        with pytest.raises(ValueError, match="FETCH_FAILED.*observation_count"):
            SpecificationSourceOutcome(
                source=self._make_source(),
                final_url=None,
                retrieved_at=None,
                outcome_state=SourceOutcomeState.FETCH_FAILED,
                observation_count=3,
            )

    def test_source_refused_requires_no_final_url(self) -> None:
        with pytest.raises(ValueError, match="SOURCE_REFUSED.*final_url"):
            SpecificationSourceOutcome(
                source=self._make_source(),
                final_url="https://example.com/final",
                retrieved_at=_now(),
                outcome_state=SourceOutcomeState.SOURCE_REFUSED,
                observation_count=0,
            )

    def test_source_refused_requires_no_retrieved_at(self) -> None:
        with pytest.raises(ValueError, match="SOURCE_REFUSED.*retrieved_at"):
            SpecificationSourceOutcome(
                source=self._make_source(),
                final_url=None,
                retrieved_at=_now(),
                outcome_state=SourceOutcomeState.SOURCE_REFUSED,
                observation_count=0,
            )

    def test_source_refused_requires_observation_count_0(self) -> None:
        with pytest.raises(ValueError, match="SOURCE_REFUSED.*observation_count"):
            SpecificationSourceOutcome(
                source=self._make_source(),
                final_url=None,
                retrieved_at=None,
                outcome_state=SourceOutcomeState.SOURCE_REFUSED,
                observation_count=7,
            )

    def test_valid_extracted_outcome(self) -> None:
        outcome = SpecificationSourceOutcome(
            source=self._make_source(),
            final_url="https://example.com/final",
            retrieved_at=_now(),
            outcome_state=SourceOutcomeState.EXTRACTED,
            observation_count=5,
        )
        assert outcome.outcome_state is SourceOutcomeState.EXTRACTED
        assert outcome.observation_count == 5

    def test_valid_fetch_failed_outcome(self) -> None:
        outcome = SpecificationSourceOutcome(
            source=self._make_source(),
            final_url=None,
            retrieved_at=None,
            outcome_state=SourceOutcomeState.FETCH_FAILED,
            observation_count=0,
        )
        assert outcome.outcome_state is SourceOutcomeState.FETCH_FAILED


# ===================================================================
# H. Result audit consistency
# ===================================================================


class TestResultAuditConsistency:
    """SpecificationEvidenceResult enforces audit consistency."""

    def test_audit_extracted_count_matches_normalized_observations(self) -> None:
        identity = _identity()
        document = _make_embedded_json_document(
            "MZ-QL23T800",
            [("Form Factor", "2.5 in")],
        )
        fetcher = _FakePageFetcher(
            fetched_page=_fake_fetched_page(body_text=document),
        )
        source = _make_source(identity)
        result = research_enterprise_ssd_specifications(
            product_identity=identity,
            sources=(source,),
            page_fetcher=fetcher,
        )
        extracted_count = sum(
            outcome.observation_count
            for outcome in result.source_outcomes
            if outcome.outcome_state is SourceOutcomeState.EXTRACTED
        )
        assert extracted_count == len(result.normalized_observations)

    def test_audit_multi_source(self) -> None:
        identity = _identity()
        doc = _make_embedded_json_document(
            "MZ-QL23T800",
            [("Form Factor", "2.5 in")],
        )

        class _MixedFetcher:
            def __init__(self) -> None:
                self._call_count = 0

            def fetch(self, request: PageFetchRequest) -> FetchedPage:
                self._call_count += 1
                if self._call_count == 2:
                    raise PageFetchError("fail")
                return _fake_fetched_page(body_text=doc)

        source1 = _make_source(identity, name="S1", url="https://example.com/1")
        source2 = _make_source(identity, name="S2", url="https://example.com/2")
        source3 = _make_source(identity, name="S3", url="https://example.com/3")
        result = research_enterprise_ssd_specifications(
            product_identity=identity,
            sources=(source1, source2, source3),
            page_fetcher=_MixedFetcher(),
        )
        extracted_count = sum(
            outcome.observation_count
            for outcome in result.source_outcomes
            if outcome.outcome_state is SourceOutcomeState.EXTRACTED
        )
        assert extracted_count == len(result.normalized_observations)


# ===================================================================
# I. Provenance trace enforcement (adversarial)
# ===================================================================


class TestProvenanceTrace:
    """Adversarial tests for normalized-observation -> source-outcome trace."""

    def test_observation_from_unaccounted_source_rejected(self) -> None:
        """A normalized observation from a source not in EXTRACTED outcomes
        is rejected at result construction."""
        identity = _identity()
        document = _make_embedded_json_document(
            "MZ-QL23T800",
            [("Form Factor", "2.5 in")],
        )

        # Build a result where the outcome says EXTRACTED(1) but
        # from a DIFFERENT source than the observation
        source_a = _make_source(identity, name="Source A")
        outcome = SpecificationSourceOutcome(
            source=source_a,
            final_url="https://source-a.com",
            retrieved_at=_now(),
            outcome_state=SourceOutcomeState.EXTRACTED,
            observation_count=1,
        )

        # But the observation claims to be from "Ghost Source"
        schema_def = ENTERPRISE_SSD_SCHEMA.definitions["physical_form_factor"]
        raw_obs = SpecificationObservation(
            product_identity=identity,
            definition=schema_def,
            source_name="Ghost Source",  # Not in any EXTRACTED outcome
            source_url="https://ghost.example.com",
            retrieved_at=_now(),
            raw_value="2.5 in",
            source_authority=SourceAuthority.AUTHORITATIVE,
        )
        norm_obs = NormalizedSpecificationObservation(
            observation=raw_obs,
            canonical_value=SpecificationValue("2.5-inch"),
        )

        # Build a ProductSpecificationSet with this observation
        resolutions = {}
        for key, definition in ENTERPRISE_SSD_SCHEMA.definitions.items():
            obs_for_def = (norm_obs,) if key == "physical_form_factor" else ()
            resolutions[key] = resolve_specification(identity, definition, obs_for_def)
        spec_set = ProductSpecificationSet(
            product_identity=identity,
            category_schema=ENTERPRISE_SSD_SCHEMA,
            resolutions=resolutions,
        )

        with pytest.raises(ValueError, match="Provenance trace failed"):
            SpecificationEvidenceResult(
                product_identity=identity,
                source_outcomes=(outcome,),
                normalized_observations=(norm_obs,),
                product_specification_set=spec_set,
            )

    def test_same_count_wrong_source_rejected(self) -> None:
        """Same observation count but wrong source name is rejected."""
        identity = _identity()
        document = _make_embedded_json_document(
            "MZ-QL23T800",
            [("Form Factor", "2.5 in")],
        )

        # Outcome from "Source A" with 1 observation
        source_a = _make_source(identity, name="Source A")
        outcome = SpecificationSourceOutcome(
            source=source_a,
            final_url="https://source-a.com",
            retrieved_at=_now(),
            outcome_state=SourceOutcomeState.EXTRACTED,
            observation_count=1,
        )

        # But the observation claims to be from "Source B"
        schema_def = ENTERPRISE_SSD_SCHEMA.definitions["physical_form_factor"]
        raw_obs = SpecificationObservation(
            product_identity=identity,
            definition=schema_def,
            source_name="Source B",  # Different from outcome's source
            source_url="https://source-b.com",
            retrieved_at=_now(),
            raw_value="2.5 in",
            source_authority=SourceAuthority.AUTHORITATIVE,
        )
        norm_obs = NormalizedSpecificationObservation(
            observation=raw_obs,
            canonical_value=SpecificationValue("2.5-inch"),
        )
        resolutions = {}
        for key, definition in ENTERPRISE_SSD_SCHEMA.definitions.items():
            obs_for_def = (norm_obs,) if key == "physical_form_factor" else ()
            resolutions[key] = resolve_specification(identity, definition, obs_for_def)
        spec_set = ProductSpecificationSet(
            product_identity=identity,
            category_schema=ENTERPRISE_SSD_SCHEMA,
            resolutions=resolutions,
        )

        with pytest.raises(ValueError, match="Provenance trace failed"):
            SpecificationEvidenceResult(
                product_identity=identity,
                source_outcomes=(outcome,),
                normalized_observations=(norm_obs,),
                product_specification_set=spec_set,
            )

    def test_wrong_source_authority_rejected(self) -> None:
        """Wrong source authority in observation vs outcome is rejected."""
        identity = _identity()
        source = _make_source(identity, authority=SourceAuthority.AUTHORITATIVE)
        outcome = SpecificationSourceOutcome(
            source=source,
            final_url="https://example.com",
            retrieved_at=_now(),
            outcome_state=SourceOutcomeState.EXTRACTED,
            observation_count=1,
        )

        schema_def = ENTERPRISE_SSD_SCHEMA.definitions["physical_form_factor"]
        raw_obs = SpecificationObservation(
            product_identity=identity,
            definition=schema_def,
            source_name="Test",
            source_url="https://example.com",
            retrieved_at=_now(),
            raw_value="2.5 in",
            source_authority=SourceAuthority.SECONDARY,  # Different from source
        )
        norm_obs = NormalizedSpecificationObservation(
            observation=raw_obs,
            canonical_value=SpecificationValue("2.5-inch"),
        )
        resolutions = {}
        for key, definition in ENTERPRISE_SSD_SCHEMA.definitions.items():
            obs_for_def = (norm_obs,) if key == "physical_form_factor" else ()
            resolutions[key] = resolve_specification(identity, definition, obs_for_def)
        spec_set = ProductSpecificationSet(
            product_identity=identity,
            category_schema=ENTERPRISE_SSD_SCHEMA,
            resolutions=resolutions,
        )

        with pytest.raises(ValueError, match="Provenance trace failed"):
            SpecificationEvidenceResult(
                product_identity=identity,
                source_outcomes=(outcome,),
                normalized_observations=(norm_obs,),
                product_specification_set=spec_set,
            )

    def test_wrong_final_url_rejected(self) -> None:
        """Wrong final_url in observation vs outcome is rejected."""
        identity = _identity()
        source = _make_source(identity)
        outcome = SpecificationSourceOutcome(
            source=source,
            final_url="https://example.com/final",
            retrieved_at=_now(),
            outcome_state=SourceOutcomeState.EXTRACTED,
            observation_count=1,
        )

        schema_def = ENTERPRISE_SSD_SCHEMA.definitions["physical_form_factor"]
        raw_obs = SpecificationObservation(
            product_identity=identity,
            definition=schema_def,
            source_name="Test",
            source_url="https://different.com",  # Different final_url
            retrieved_at=_now(),
            raw_value="2.5 in",
            source_authority=SourceAuthority.AUTHORITATIVE,
        )
        norm_obs = NormalizedSpecificationObservation(
            observation=raw_obs,
            canonical_value=SpecificationValue("2.5-inch"),
        )
        resolutions = {}
        for key, definition in ENTERPRISE_SSD_SCHEMA.definitions.items():
            obs_for_def = (norm_obs,) if key == "physical_form_factor" else ()
            resolutions[key] = resolve_specification(identity, definition, obs_for_def)
        spec_set = ProductSpecificationSet(
            product_identity=identity,
            category_schema=ENTERPRISE_SSD_SCHEMA,
            resolutions=resolutions,
        )

        with pytest.raises(ValueError, match="Provenance trace failed"):
            SpecificationEvidenceResult(
                product_identity=identity,
                source_outcomes=(outcome,),
                normalized_observations=(norm_obs,),
                product_specification_set=spec_set,
            )

    def test_wrong_retrieved_at_rejected(self) -> None:
        """Wrong retrieved_at in observation vs outcome is rejected."""
        identity = _identity()
        outcome_time = _now()
        different_time = datetime(2025, 1, 1, 0, 0, 0, tzinfo=timezone.utc)
        source = _make_source(identity)
        outcome = SpecificationSourceOutcome(
            source=source,
            final_url="https://example.com",
            retrieved_at=outcome_time,
            outcome_state=SourceOutcomeState.EXTRACTED,
            observation_count=1,
        )

        schema_def = ENTERPRISE_SSD_SCHEMA.definitions["physical_form_factor"]
        raw_obs = SpecificationObservation(
            product_identity=identity,
            definition=schema_def,
            source_name="Test",
            source_url="https://example.com",
            retrieved_at=different_time,  # Different time
            raw_value="2.5 in",
            source_authority=SourceAuthority.AUTHORITATIVE,
        )
        norm_obs = NormalizedSpecificationObservation(
            observation=raw_obs,
            canonical_value=SpecificationValue("2.5-inch"),
        )
        resolutions = {}
        for key, definition in ENTERPRISE_SSD_SCHEMA.definitions.items():
            obs_for_def = (norm_obs,) if key == "physical_form_factor" else ()
            resolutions[key] = resolve_specification(identity, definition, obs_for_def)
        spec_set = ProductSpecificationSet(
            product_identity=identity,
            category_schema=ENTERPRISE_SSD_SCHEMA,
            resolutions=resolutions,
        )

        with pytest.raises(ValueError, match="Provenance trace failed"):
            SpecificationEvidenceResult(
                product_identity=identity,
                source_outcomes=(outcome,),
                normalized_observations=(norm_obs,),
                product_specification_set=spec_set,
            )


# ===================================================================
# J. ProductSpecificationSet evidence consistency (adversarial)
# ===================================================================


class TestResolutionEvidenceConsistency:
    """ProductSpecificationSet evidence must equal normalized observations
    for each definition. Fabricated evidence is rejected."""

    def test_fabricated_evidence_rejected(self) -> None:
        """A resolution containing evidence not in normalized_observations
        is rejected at result construction."""
        identity = _identity()

        # Create a normalized observation for physical_form_factor
        schema_def = ENTERPRISE_SSD_SCHEMA.definitions["physical_form_factor"]
        raw_obs = SpecificationObservation(
            product_identity=identity,
            definition=schema_def,
            source_name="Test",
            source_url="https://example.com",
            retrieved_at=_now(),
            raw_value="2.5 in",
            source_authority=SourceAuthority.AUTHORITATIVE,
        )
        norm_obs = NormalizedSpecificationObservation(
            observation=raw_obs,
            canonical_value=SpecificationValue("2.5-inch"),
        )

        # Create a DIFFERENT observation for the SAME definition
        fabricated_raw_obs = SpecificationObservation(
            product_identity=identity,
            definition=schema_def,
            source_name="Fabricated",
            source_url="https://fabricated.com",
            retrieved_at=_now(),
            raw_value="E1.S",
            source_authority=SourceAuthority.SECONDARY,
        )
        fabricated_norm_obs = NormalizedSpecificationObservation(
            observation=fabricated_raw_obs,
            canonical_value=SpecificationValue("E1.S"),
        )

        resolutions = {}
        for key, definition in ENTERPRISE_SSD_SCHEMA.definitions.items():
            if key == "physical_form_factor":
                resolutions[key] = resolve_specification(
                    identity, definition, (fabricated_norm_obs,)
                )
            else:
                resolutions[key] = resolve_specification(identity, definition, ())
        spec_set = ProductSpecificationSet(
            product_identity=identity,
            category_schema=ENTERPRISE_SSD_SCHEMA,
            resolutions=resolutions,
        )

        source = _make_source(identity)
        outcome = SpecificationSourceOutcome(
            source=source,
            final_url="https://example.com",
            retrieved_at=_now(),
            outcome_state=SourceOutcomeState.EXTRACTED,
            observation_count=1,
        )

        with pytest.raises(ValueError, match="Resolution evidence"):
            SpecificationEvidenceResult(
                product_identity=identity,
                source_outcomes=(outcome,),
                normalized_observations=(norm_obs,),
                product_specification_set=spec_set,
            )


# ===================================================================
# K. Real fixture end-to-end
# ===================================================================


class TestRealFixtureEndToEnd:
    """End-to-end tests with the real Seagate fixture."""

    def test_real_seagate_vertical_slice(self) -> None:
        """Real Seagate fixture: embedded JSON -> extraction -> normalization
        -> resolution.

        The real Seagate source publishes 'Form Factor' = '2.5in' (no space).
        After evidence-backed 6B correction, '2.5in' normalizes to '2.5-inch'.
        Resolution is VERIFIED (AUTHORITATIVE source, single canonical value).
        """
        identity = _seagate_identity()

        def _read_fixture(name: str) -> str:
            import os
            path = os.path.join(
                os.path.dirname(__file__),
                "..",
                "research",
                "..",
                "fixtures",
                "specifications",
                name,
            )
            with open(path, "r", encoding="utf-8") as f:
                return f.read()

        document = _read_fixture("real_seagate_nytro_5050_xp15360se70005.html")
        fetcher = _FakePageFetcher(
            fetched_page=_fake_fetched_page(body_text=document),
        )
        source = _make_source(
            identity,
            name="Seagate",
            url="https://www.seagate.com/support/enterprise-storage/solid-state-drives/nytro-5050/",
            authority=SourceAuthority.AUTHORITATIVE,
        )
        result = research_enterprise_ssd_specifications(
            product_identity=identity,
            sources=(source,),
            page_fetcher=fetcher,
        )

        # Source outcome
        assert len(result.source_outcomes) == 1
        assert result.source_outcomes[0].outcome_state is SourceOutcomeState.EXTRACTED
        assert result.source_outcomes[0].observation_count >= 1

        # At least one normalized observation
        assert len(result.normalized_observations) >= 1

        # Physical form factor: raw '2.5in' normalizes to '2.5-inch'
        # after evidence-backed 6B correction.
        ff_resolution = result.product_specification_set.resolutions["physical_form_factor"]
        assert ff_resolution.state is ResolutionState.VERIFIED
        assert ff_resolution.resolved_value.value == "2.5-inch"

        # The raw observation preserves the source value exactly
        ff_obs = [
            obs for obs in result.normalized_observations
            if obs.observation.definition.key == "physical_form_factor"
        ]
        assert len(ff_obs) >= 1
        assert ff_obs[0].observation.raw_value == "2.5in"
        assert ff_obs[0].normalization_issue is None
        assert ff_obs[0].canonical_value.value == "2.5-inch"

        # All 12 resolutions present
        assert len(result.product_specification_set.resolutions) == 12


# ===================================================================
# L. Provenance multiplicity (adversarial)
# ===================================================================


class TestProvenanceMultiplicity:
    """Multiplicity-aware provenance: each EXTRACTED outcome contributes
    capacity equal to its observation_count. Each observation consumes
    one unit of capacity.
    """

    def _build_norm_obs(
        self,
        identity: ProductIdentity,
        source_name: str,
        source_url: str,
        retrieved_at: datetime,
        authority: SourceAuthority,
        raw_value: str = "2.5in",
    ) -> NormalizedSpecificationObservation:
        schema_def = ENTERPRISE_SSD_SCHEMA.definitions["physical_form_factor"]
        raw_obs = SpecificationObservation(
            product_identity=identity,
            definition=schema_def,
            source_name=source_name,
            source_url=source_url,
            retrieved_at=retrieved_at,
            raw_value=raw_value,
            source_authority=authority,
        )
        return NormalizedSpecificationObservation(
            observation=raw_obs,
            canonical_value=SpecificationValue("2.5-inch"),
        )

    def _build_spec_set(
        self,
        identity: ProductIdentity,
        norm_obs_for_ff: tuple[NormalizedSpecificationObservation, ...],
    ) -> ProductSpecificationSet:
        resolutions = {}
        for key, definition in ENTERPRISE_SSD_SCHEMA.definitions.items():
            obs_for_def = norm_obs_for_ff if key == "physical_form_factor" else ()
            resolutions[key] = resolve_specification(identity, definition, obs_for_def)
        return ProductSpecificationSet(
            product_identity=identity,
            category_schema=ENTERPRISE_SSD_SCHEMA,
            resolutions=resolutions,
        )

    # Scenario A: one EXTRACTED outcome count=2 + two matching observations -> accepted
    def test_one_source_count_2_two_observations_accepted(self) -> None:
        """One EXTRACTED outcome with count=2 can support two matching
        normalized observations."""
        identity = _identity()
        time = _now()
        source = _make_source(identity, name="Source A")
        outcome = SpecificationSourceOutcome(
            source=source,
            final_url="https://example.com",
            retrieved_at=time,
            outcome_state=SourceOutcomeState.EXTRACTED,
            observation_count=2,
        )

        obs1 = self._build_norm_obs(identity, "Source A", "https://example.com", time, SourceAuthority.AUTHORITATIVE)
        obs2 = self._build_norm_obs(identity, "Source A", "https://example.com", time, SourceAuthority.AUTHORITATIVE)

        spec_set = self._build_spec_set(identity, (obs1, obs2))

        # Should not raise
        result = SpecificationEvidenceResult(
            product_identity=identity,
            source_outcomes=(outcome,),
            normalized_observations=(obs1, obs2),
            product_specification_set=spec_set,
        )
        assert len(result.normalized_observations) == 2

    # Scenario B: one EXTRACTED outcome count=1 + two matching observations -> rejected
    def test_one_source_count_1_two_observations_rejected(self) -> None:
        """One EXTRACTED outcome with count=1 cannot support two observations.
        Total count is wrong (1 != 2) so the outer audit catches it."""
        identity = _identity()
        time = _now()
        source = _make_source(identity, name="Source A")
        outcome = SpecificationSourceOutcome(
            source=source,
            final_url="https://example.com",
            retrieved_at=time,
            outcome_state=SourceOutcomeState.EXTRACTED,
            observation_count=1,
        )

        obs1 = self._build_norm_obs(identity, "Source A", "https://example.com", time, SourceAuthority.AUTHORITATIVE)
        obs2 = self._build_norm_obs(identity, "Source A", "https://example.com", time, SourceAuthority.AUTHORITATIVE)

        spec_set = self._build_spec_set(identity, (obs1, obs2))

        # Total count mismatch: 1 != 2
        with pytest.raises(ValueError, match="Result audit inconsistency"):
            SpecificationEvidenceResult(
                product_identity=identity,
                source_outcomes=(outcome,),
                normalized_observations=(obs1, obs2),
                product_specification_set=spec_set,
            )

    # Scenario C: two EXTRACTED outcomes each count=1 + two observations -> accepted
    def test_two_sources_each_count_1_accepted(self) -> None:
        """Two EXTRACTED outcomes each with count=1 can support two
        corresponding observations."""
        identity = _identity()
        time = _now()
        source_a = _make_source(identity, name="Source A", url="https://a.com")
        source_b = _make_source(identity, name="Source B", url="https://b.com")

        outcome_a = SpecificationSourceOutcome(
            source=source_a,
            final_url="https://a.com",
            retrieved_at=time,
            outcome_state=SourceOutcomeState.EXTRACTED,
            observation_count=1,
        )
        outcome_b = SpecificationSourceOutcome(
            source=source_b,
            final_url="https://b.com",
            retrieved_at=time,
            outcome_state=SourceOutcomeState.EXTRACTED,
            observation_count=1,
        )

        obs_a = self._build_norm_obs(identity, "Source A", "https://a.com", time, SourceAuthority.AUTHORITATIVE)
        obs_b = self._build_norm_obs(identity, "Source B", "https://b.com", time, SourceAuthority.AUTHORITATIVE)

        spec_set = self._build_spec_set(identity, (obs_a, obs_b))

        # Should not raise
        result = SpecificationEvidenceResult(
            product_identity=identity,
            source_outcomes=(outcome_a, outcome_b),
            normalized_observations=(obs_a, obs_b),
            product_specification_set=spec_set,
        )
        assert len(result.normalized_observations) == 2

    # Scenario D: total count correct but wrong provenance -> rejected
    def test_correct_count_wrong_provenance_rejected(self) -> None:
        """Total count is correct (2=2) but provenance distribution is wrong.
        Two observations both claim 'Source A' but only one outcome is
        from 'Source A' (count=1) and the other is 'Source B' (count=1)."""
        identity = _identity()
        time = _now()
        source_a = _make_source(identity, name="Source A", url="https://a.com")
        source_b = _make_source(identity, name="Source B", url="https://b.com")

        outcome_a = SpecificationSourceOutcome(
            source=source_a,
            final_url="https://a.com",
            retrieved_at=time,
            outcome_state=SourceOutcomeState.EXTRACTED,
            observation_count=1,
        )
        outcome_b = SpecificationSourceOutcome(
            source=source_b,
            final_url="https://b.com",
            retrieved_at=time,
            outcome_state=SourceOutcomeState.EXTRACTED,
            observation_count=1,
        )

        # Both observations claim to be from Source A
        obs_a1 = self._build_norm_obs(identity, "Source A", "https://a.com", time, SourceAuthority.AUTHORITATIVE)
        obs_a2 = self._build_norm_obs(identity, "Source A", "https://a.com", time, SourceAuthority.AUTHORITATIVE)

        spec_set = self._build_spec_set(identity, (obs_a1, obs_a2))

        # Provenance trace fails: second observation from "Source A" has no
        # remaining capacity (outcome_a has count=1, consumed by obs_a1)
        with pytest.raises(ValueError, match="Provenance trace failed"):
            SpecificationEvidenceResult(
                product_identity=identity,
                source_outcomes=(outcome_a, outcome_b),
                normalized_observations=(obs_a1, obs_a2),
                product_specification_set=spec_set,
            )


# ===================================================================
# M. Final URL validation
# ===================================================================


class TestFinalUrlValidation:
    """SpecificationSourceOutcome validates final_url through
    require_fetchable_url when not None."""

    def _make_source(self) -> SpecificationEvidenceSource:
        return _make_source(_identity())

    def test_valid_final_url_accepted(self) -> None:
        outcome = SpecificationSourceOutcome(
            source=self._make_source(),
            final_url="https://example.com/final",
            retrieved_at=_now(),
            outcome_state=SourceOutcomeState.EXTRACTED,
            observation_count=1,
        )
        assert outcome.final_url == "https://example.com/final"

    def test_ftp_url_rejected(self) -> None:
        with pytest.raises((ValueError, TypeError), match="final_url"):
            SpecificationSourceOutcome(
                source=self._make_source(),
                final_url="ftp://example.com/file",
                retrieved_at=_now(),
                outcome_state=SourceOutcomeState.EXTRACTED,
                observation_count=1,
            )

    def test_file_url_rejected(self) -> None:
        with pytest.raises((ValueError, TypeError), match="final_url"):
            SpecificationSourceOutcome(
                source=self._make_source(),
                final_url="file:///local/path",
                retrieved_at=_now(),
                outcome_state=SourceOutcomeState.EXTRACTED,
                observation_count=1,
            )

    def test_missing_host_rejected(self) -> None:
        with pytest.raises((ValueError, TypeError), match="final_url"):
            SpecificationSourceOutcome(
                source=self._make_source(),
                final_url="https:///relative",
                retrieved_at=_now(),
                outcome_state=SourceOutcomeState.EXTRACTED,
                observation_count=1,
            )

    def test_embedded_credentials_rejected(self) -> None:
        with pytest.raises((ValueError, TypeError), match="final_url"):
            SpecificationSourceOutcome(
                source=self._make_source(),
                final_url="https://user:pass@example.com/page",
                retrieved_at=_now(),
                outcome_state=SourceOutcomeState.EXTRACTED,
                observation_count=1,
            )
