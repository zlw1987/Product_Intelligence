"""Comparable similarity execution tests (PRODUCT-INTEL.7B).

Tests the execution layer: source acquisition, one-fetch-per-source,
candidate spec research, batch similarity scoring, provenance auditing,
fake discovery result rejection, and result-level provenance adversarial tests.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any

import pytest

from product_intelligence.domain.enums import IdentityMatchType
from product_intelligence.domain.models import ProductIdentity
from product_intelligence.execution.comparable_discovery import (
    ComparableCandidateDiscoveryResult,
    ComparableCandidateSource as DiscoveryComparableCandidateSource,
    ComparableCandidateSourceOutcome,
    ComparableCandidateSourceOutcomeState as DiscoverySourceOutcomeState,
    discover_enterprise_ssd_comparable_candidates,
)
from product_intelligence.execution.comparable_similarity import (
    ComparableSimilaritySourceOutcome,
    ComparableSimilaritySourceOutcomeState,
    EnterpriseSsdSimilarityResult,
    research_and_score_enterprise_ssd_candidates,
)
from product_intelligence.providers.page import (
    FetchedPage,
    PageFetchError,
    PageFetchRequest,
    PageFetcher,
    UnsafeFetchTargetError,
)
from product_intelligence.research.comparable_candidates import (
    ComparableCandidateSource,
)
from product_intelligence.research.enterprise_ssd import ENTERPRISE_SSD_SCHEMA
from product_intelligence.research.enterprise_ssd_similarity import (
    ComparableCandidateSpecificationProfile,
    EnterpriseSsdCandidateSimilarity,
    establish_candidate_product_identity,
)
from product_intelligence.research.specifications import (
    NormalizedSpecificationObservation,
    ProductSpecificationSet,
    ResolutionState,
    SpecificationResolution,
    SourceAuthority,
    resolve_specification,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_RETRIEVED_AT = datetime(2026, 9, 4, 20, 42, 23, tzinfo=timezone.utc)
_SOURCE_NAME = "Seagate Enterprise Support"
_SOURCE_URL = "https://www.seagate.com/support/enterprise-storage/solid-state-drives/nytro-5050/"


def _make_target(mpn: str = "XP15360SE70005") -> ProductIdentity:
    return ProductIdentity(
        manufacturer="Seagate",
        manufacturer_part_number=mpn,
        normalized_part_number=mpn.upper(),
        match_type=IdentityMatchType.EXACT,
    )


def _make_empty_spec_set(
    identity: ProductIdentity,
) -> ProductSpecificationSet:
    resolutions: dict[str, SpecificationResolution] = {}
    for key, definition in ENTERPRISE_SSD_SCHEMA.definitions.items():
        resolution = resolve_specification(identity, definition, ())
        resolutions[key] = resolution
    return ProductSpecificationSet(
        product_identity=identity,
        category_schema=ENTERPRISE_SSD_SCHEMA,
        resolutions=resolutions,
    )


def _make_source(
    source_url: str = _SOURCE_URL,
    source_name: str = _SOURCE_NAME,
) -> ComparableCandidateSource:
    return ComparableCandidateSource(
        source_name=source_name,
        source_url=source_url,
        source_authority=SourceAuthority.AUTHORITATIVE,
    )


def _read_fixture() -> str:
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
# SOURCE CONTRACT
# ---------------------------------------------------------------------------


class TestSourceContract:
    def test_discovery_result_required(self) -> None:
        """A valid discovery result is required."""
        fetcher = _FakePageFetcher(body=_read_fixture())
        with pytest.raises(TypeError):
            research_and_score_enterprise_ssd_candidates(
                discovery_result="not a result",  # type: ignore[arg-type]
                page_fetcher=fetcher,
            )

    def test_source_extraction_outcomes_used(self) -> None:
        """Only EXTRACTED source outcomes are fetched for 7B spec research."""
        target = _make_target()
        spec_set = _make_empty_spec_set(target)
        source = _make_source()
        fetcher = _FakePageFetcher(body=_read_fixture())

        discovery_result = discover_enterprise_ssd_comparable_candidates(
            target_identity=target,
            target_specification_set=spec_set,
            sources=(source,),
            page_fetcher=fetcher,
        )

        assert len(discovery_result.source_outcomes) == 1
        assert (
            discovery_result.source_outcomes[0].outcome_state
            is DiscoverySourceOutcomeState.EXTRACTED
        )

        # Now run 7B
        score_fetcher = _FakePageFetcher(body=_read_fixture())
        similarity_result = research_and_score_enterprise_ssd_candidates(
            discovery_result=discovery_result,
            page_fetcher=score_fetcher,
        )
        assert len(similarity_result.candidate_profiles) == len(
            discovery_result.candidates
        )


# ---------------------------------------------------------------------------
# ONE FETCH PER SOURCE
# ---------------------------------------------------------------------------


class TestOneFetchPerSource:
    def test_one_fetch_per_source(self) -> None:
        """Each unique source is fetched exactly once, not once per candidate."""
        target = _make_target()
        spec_set = _make_empty_spec_set(target)
        source = _make_source()
        discovery_fetcher = _FakePageFetcher(body=_read_fixture())

        discovery_result = discover_enterprise_ssd_comparable_candidates(
            target_identity=target,
            target_specification_set=spec_set,
            sources=(source,),
            page_fetcher=discovery_fetcher,
        )

        assert len(discovery_result.candidates) == 80

        # 7B should fetch the source ONCE, not 80 times
        score_fetcher = _FakePageFetcher(body=_read_fixture())
        similarity_result = research_and_score_enterprise_ssd_candidates(
            discovery_result=discovery_result,
            page_fetcher=score_fetcher,
        )

        assert score_fetcher.fetch_count == 1
        assert len(similarity_result.candidate_profiles) == 80
        assert len(similarity_result.similarities) == 80

    def test_duplicate_sources_deduplicated(self) -> None:
        """Duplicate source URLs are fetched only once."""
        target = _make_target()
        spec_set = _make_empty_spec_set(target)
        source1 = _make_source(source_url=_SOURCE_URL)
        source2 = _make_source(
            source_url=_SOURCE_URL,
            source_name=_SOURCE_NAME,
        )
        discovery_fetcher = _FakePageFetcher(body=_read_fixture())

        discovery_result = discover_enterprise_ssd_comparable_candidates(
            target_identity=target,
            target_specification_set=spec_set,
            sources=(source1, source2),
            page_fetcher=discovery_fetcher,
        )

        score_fetcher = _FakePageFetcher(body=_read_fixture())
        similarity_result = research_and_score_enterprise_ssd_candidates(
            discovery_result=discovery_result,
            page_fetcher=score_fetcher,
        )

        # Two EXTRACTED outcomes but same URL -> one fetch
        assert score_fetcher.fetch_count == 1


# ---------------------------------------------------------------------------
# FETCH ERRORS
# ---------------------------------------------------------------------------


class TestFetchErrors:
    def test_page_fetch_error_bounded(self) -> None:
        """PageFetchError -> FETCH_FAILED, bounded.

        Outcome state is FETCH_FAILED, final_url and retrieved_at are None.
        All candidates still produce profiles and similarities.
        Programming exception does NOT propagate.
        """
        target = _make_target()
        spec_set = _make_empty_spec_set(target)
        source = _make_source()
        discovery_fetcher = _FakePageFetcher(body=_read_fixture())

        discovery_result = discover_enterprise_ssd_comparable_candidates(
            target_identity=target,
            target_specification_set=spec_set,
            sources=(source,),
            page_fetcher=discovery_fetcher,
        )

        score_fetcher = _FakePageFetcher(error=PageFetchError)
        similarity_result = research_and_score_enterprise_ssd_candidates(
            discovery_result=discovery_result,
            page_fetcher=score_fetcher,
        )

        # Source outcome: FETCH_FAILED with None final_url and retrieved_at
        assert len(similarity_result.source_outcomes) == 1
        outcome = similarity_result.source_outcomes[0]
        assert outcome.outcome_state is ComparableSimilaritySourceOutcomeState.FETCH_FAILED
        assert outcome.final_url is None
        assert outcome.retrieved_at is None

        # All candidates still produce profiles and similarities
        assert len(similarity_result.candidate_profiles) == len(
            discovery_result.candidates
        )

    def test_unsafe_fetch_target_error_bounded(self) -> None:
        """UnsafeFetchTargetError -> SOURCE_REFUSED, bounded.

        Outcome state is SOURCE_REFUSED, final_url and retrieved_at are None.
        All candidates still produce profiles and similarities.
        """
        target = _make_target()
        spec_set = _make_empty_spec_set(target)
        source = _make_source()
        discovery_fetcher = _FakePageFetcher(body=_read_fixture())

        discovery_result = discover_enterprise_ssd_comparable_candidates(
            target_identity=target,
            target_specification_set=spec_set,
            sources=(source,),
            page_fetcher=discovery_fetcher,
        )

        score_fetcher = _FakePageFetcher(error=UnsafeFetchTargetError)
        similarity_result = research_and_score_enterprise_ssd_candidates(
            discovery_result=discovery_result,
            page_fetcher=score_fetcher,
        )

        # Source outcome: SOURCE_REFUSED with None final_url and retrieved_at
        assert len(similarity_result.source_outcomes) == 1
        outcome = similarity_result.source_outcomes[0]
        assert outcome.outcome_state is ComparableSimilaritySourceOutcomeState.SOURCE_REFUSED
        assert outcome.final_url is None
        assert outcome.retrieved_at is None

        assert len(similarity_result.candidate_profiles) == len(
            discovery_result.candidates
        )

    def test_programming_exception_propagates(self, monkeypatch) -> None:
        """Programming exception from extraction propagates."""
        import product_intelligence.execution.comparable_similarity as mod

        def _raising_extraction(**kwargs: Any) -> list:
            raise RuntimeError("test programming defect")

        monkeypatch.setattr(
            mod,
            "extract_enterprise_ssd_specification_observations",
            _raising_extraction,
        )

        target = _make_target()
        spec_set = _make_empty_spec_set(target)
        source = _make_source()
        discovery_fetcher = _FakePageFetcher(body=_read_fixture())

        discovery_result = discover_enterprise_ssd_comparable_candidates(
            target_identity=target,
            target_specification_set=spec_set,
            sources=(source,),
            page_fetcher=discovery_fetcher,
        )

        score_fetcher = _FakePageFetcher(body=_read_fixture())
        with pytest.raises(RuntimeError, match="test programming defect"):
            research_and_score_enterprise_ssd_candidates(
                discovery_result=discovery_result,
                page_fetcher=score_fetcher,
            )


# ---------------------------------------------------------------------------
# PROVENANCE
# ---------------------------------------------------------------------------


class TestProvenance:
    def test_final_url_provenance(self) -> None:
        """When source is fetched, final_url is preserved in outcome AND
        traced through candidate evidence observations."""
        target = _make_target()
        spec_set = _make_empty_spec_set(target)
        source = _make_source()
        discovery_fetcher = _FakePageFetcher(body=_read_fixture())

        discovery_result = discover_enterprise_ssd_comparable_candidates(
            target_identity=target,
            target_specification_set=spec_set,
            sources=(source,),
            page_fetcher=discovery_fetcher,
        )

        expected_final_url = "https://www.seagate.com/support/redirect/"
        score_fetcher = _FakePageFetcher(
            body=_read_fixture(),
            final_url=expected_final_url,
        )
        similarity_result = research_and_score_enterprise_ssd_candidates(
            discovery_result=discovery_result,
            page_fetcher=score_fetcher,
        )

        # All candidates have profiles
        assert len(similarity_result.candidate_profiles) == 80

        # Source outcome has the correct final_url
        assert len(similarity_result.source_outcomes) == 1
        outcome = similarity_result.source_outcomes[0]
        assert outcome.outcome_state is ComparableSimilaritySourceOutcomeState.FETCHED
        assert outcome.final_url == expected_final_url

        # Candidate evidence observations carry the correct source_url (final_url)
        for profile in similarity_result.candidate_profiles:
            for resolution in profile.specification_set.resolutions.values():
                for evidence in resolution.evidence:
                    assert evidence.observation.source_url == expected_final_url

    def test_retrieved_at_provenance(self) -> None:
        """Retrieved_at is preserved from the fetch in outcome AND traced
        through candidate evidence observations."""
        target = _make_target()
        spec_set = _make_empty_spec_set(target)
        source = _make_source()
        discovery_fetcher = _FakePageFetcher(body=_read_fixture())

        discovery_result = discover_enterprise_ssd_comparable_candidates(
            target_identity=target,
            target_specification_set=spec_set,
            sources=(source,),
            page_fetcher=discovery_fetcher,
        )

        score_fetcher = _FakePageFetcher(body=_read_fixture())
        similarity_result = research_and_score_enterprise_ssd_candidates(
            discovery_result=discovery_result,
            page_fetcher=score_fetcher,
        )

        # Source outcome has the correct retrieved_at
        assert len(similarity_result.source_outcomes) == 1
        outcome = similarity_result.source_outcomes[0]
        assert outcome.outcome_state is ComparableSimilaritySourceOutcomeState.FETCHED
        expected_timestamp = outcome.retrieved_at
        assert expected_timestamp is not None

        # Candidate evidence observations carry the correct retrieved_at
        for profile in similarity_result.candidate_profiles:
            for resolution in profile.specification_set.resolutions.values():
                for evidence in resolution.evidence:
                    assert evidence.observation.retrieved_at == expected_timestamp

        # All profiles have complete 12-field spec sets
        for profile in similarity_result.candidate_profiles:
            assert len(
                profile.specification_set.resolutions
            ) == len(ENTERPRISE_SSD_SCHEMA.definitions)


# ---------------------------------------------------------------------------
# RESULT AUDIT
# ---------------------------------------------------------------------------


class TestResultAudit:
    def test_candidate_profiles_complete(self) -> None:
        """Every candidate profile has complete 12-field spec set."""
        target = _make_target()
        spec_set = _make_empty_spec_set(target)
        source = _make_source()
        discovery_fetcher = _FakePageFetcher(body=_read_fixture())

        discovery_result = discover_enterprise_ssd_comparable_candidates(
            target_identity=target,
            target_specification_set=spec_set,
            sources=(source,),
            page_fetcher=discovery_fetcher,
        )

        score_fetcher = _FakePageFetcher(body=_read_fixture())
        similarity_result = research_and_score_enterprise_ssd_candidates(
            discovery_result=discovery_result,
            page_fetcher=score_fetcher,
        )

        for profile in similarity_result.candidate_profiles:
            assert (
                len(profile.specification_set.resolutions)
                == len(ENTERPRISE_SSD_SCHEMA.definitions)
            )
            assert (
                profile.specification_set.product_identity
                is profile.candidate_identity
            )
            assert (
                profile.specification_set.category_schema
                is ENTERPRISE_SSD_SCHEMA
            )

    def test_similarity_order_matches_candidate_order(self) -> None:
        """Similarity order exactly matches discovery candidate order."""
        target = _make_target()
        spec_set = _make_empty_spec_set(target)
        source = _make_source()
        discovery_fetcher = _FakePageFetcher(body=_read_fixture())

        discovery_result = discover_enterprise_ssd_comparable_candidates(
            target_identity=target,
            target_specification_set=spec_set,
            sources=(source,),
            page_fetcher=discovery_fetcher,
        )

        score_fetcher = _FakePageFetcher(body=_read_fixture())
        similarity_result = research_and_score_enterprise_ssd_candidates(
            discovery_result=discovery_result,
            page_fetcher=score_fetcher,
        )

        for i, candidate in enumerate(discovery_result.candidates):
            assert similarity_result.candidate_profiles[i].candidate is candidate
            assert (
                similarity_result.similarities[i].candidate_profile
                is similarity_result.candidate_profiles[i]
            )

    def test_no_ranking_fields(self) -> None:
        """No ranking or top-N fields on the result."""
        target = _make_target()
        spec_set = _make_empty_spec_set(target)
        source = _make_source()
        discovery_fetcher = _FakePageFetcher(body=_read_fixture())

        discovery_result = discover_enterprise_ssd_comparable_candidates(
            target_identity=target,
            target_specification_set=spec_set,
            sources=(source,),
            page_fetcher=discovery_fetcher,
        )

        score_fetcher = _FakePageFetcher(body=_read_fixture())
        similarity_result = research_and_score_enterprise_ssd_candidates(
            discovery_result=discovery_result,
            page_fetcher=score_fetcher,
        )

        for field_name in ("rank", "top_n", "best", "recommended"):
            assert not hasattr(similarity_result, field_name)
        for similarity in similarity_result.similarities:
            for field_name in ("rank", "top_n", "best", "recommended"):
                assert not hasattr(similarity, field_name)

    def test_missing_candidate_profile_rejected(self) -> None:
        """Missing candidate profile is rejected by result."""
        target = _make_target()
        spec_set = _make_empty_spec_set(target)
        source = _make_source()
        discovery_fetcher = _FakePageFetcher(body=_read_fixture())

        discovery_result = discover_enterprise_ssd_comparable_candidates(
            target_identity=target,
            target_specification_set=spec_set,
            sources=(source,),
            page_fetcher=discovery_fetcher,
        )

        # Provide one fewer profile than candidates
        score_fetcher = _FakePageFetcher(body=_read_fixture())
        full_result = research_and_score_enterprise_ssd_candidates(
            discovery_result=discovery_result,
            page_fetcher=score_fetcher,
        )

        with pytest.raises(ValueError, match="candidates"):
            EnterpriseSsdSimilarityResult(
                discovery_result=discovery_result,
                source_outcomes=full_result.source_outcomes,
                candidate_profiles=full_result.candidate_profiles[:-1],
                similarities=full_result.similarities[:-1],
            )

    def test_foreign_candidate_profile_rejected(self) -> None:
        """Profile for a foreign candidate is rejected."""
        target = _make_target()
        spec_set = _make_empty_spec_set(target)
        source = _make_source()
        discovery_fetcher = _FakePageFetcher(body=_read_fixture())

        discovery_result = discover_enterprise_ssd_comparable_candidates(
            target_identity=target,
            target_specification_set=spec_set,
            sources=(source,),
            page_fetcher=discovery_fetcher,
        )

        score_fetcher = _FakePageFetcher(body=_read_fixture())
        full_result = research_and_score_enterprise_ssd_candidates(
            discovery_result=discovery_result,
            page_fetcher=score_fetcher,
        )

        # Use a profile from a different candidate position
        with pytest.raises(ValueError, match="different candidate|position"):
            EnterpriseSsdSimilarityResult(
                discovery_result=discovery_result,
                source_outcomes=full_result.source_outcomes,
                candidate_profiles=(
                    full_result.candidate_profiles[1],  # wrong candidate for [0]
                    *full_result.candidate_profiles[1:],
                ),
                similarities=full_result.similarities,
            )

    def test_duplicate_candidate_profile_rejected(self) -> None:
        """Two profiles for the same candidate at different positions are rejected."""
        target = _make_target()
        spec_set = _make_empty_spec_set(target)
        source = _make_source()
        discovery_fetcher = _FakePageFetcher(body=_read_fixture())

        discovery_result = discover_enterprise_ssd_comparable_candidates(
            target_identity=target,
            target_specification_set=spec_set,
            sources=(source,),
            page_fetcher=discovery_fetcher,
        )

        score_fetcher = _FakePageFetcher(body=_read_fixture())
        full_result = research_and_score_enterprise_ssd_candidates(
            discovery_result=discovery_result,
            page_fetcher=score_fetcher,
        )

        # Duplicate: first candidate's profile appears twice (at pos 0 and 1)
        duplicated_profiles = (
            full_result.candidate_profiles[0],
            full_result.candidate_profiles[0],  # duplicate!
            *full_result.candidate_profiles[2:],
        )
        with pytest.raises(ValueError, match="Duplicate|different candidate|position"):
            EnterpriseSsdSimilarityResult(
                discovery_result=discovery_result,
                source_outcomes=full_result.source_outcomes,
                candidate_profiles=duplicated_profiles,
                similarities=full_result.similarities,
            )


# ---------------------------------------------------------------------------
# FAKE DISCOVERY RESULT
# ---------------------------------------------------------------------------


@dataclass
class _FakeDiscoveryResult:
    """Fake object exposing ComparableCandidateDiscoveryResult attributes
    but NOT the actual class. Used to prove no duck-typing."""

    target_identity: ProductIdentity
    target_specification_set: ProductSpecificationSet
    source_outcomes: tuple
    observations: tuple
    assessments: tuple
    candidates: tuple


class TestFakeDiscoveryResult:
    def test_fake_discovery_result_rejected_by_pipeline(self) -> None:
        """Pipeline rejects a fake discovery result with TypeError BEFORE fetch."""
        target = _make_target()
        spec_set = _make_empty_spec_set(target)

        fake = _FakeDiscoveryResult(
            target_identity=target,
            target_specification_set=spec_set,
            source_outcomes=(),
            observations=(),
            assessments=(),
            candidates=(),
        )

        # Must NOT be a real PageFetcher since we want to prove NO FETCH happens
        fetcher = _FakePageFetcher(body=_read_fixture())

        with pytest.raises(TypeError, match="ComparableCandidateDiscoveryResult"):
            research_and_score_enterprise_ssd_candidates(
                discovery_result=fake,  # type: ignore[arg-type]
                page_fetcher=fetcher,
            )

        # Fetch count must be 0 — no fetch was attempted
        assert fetcher.fetch_count == 0

    def test_fake_discovery_result_rejected_by_direct_construction(self) -> None:
        """Direct construction rejects a fake discovery result."""
        target = _make_target()
        spec_set = _make_empty_spec_set(target)

        fake = _FakeDiscoveryResult(
            target_identity=target,
            target_specification_set=spec_set,
            source_outcomes=(),
            observations=(),
            assessments=(),
            candidates=(),
        )

        with pytest.raises(TypeError, match="ComparableCandidateDiscoveryResult"):
            EnterpriseSsdSimilarityResult(
                discovery_result=fake,  # type: ignore[arg-type]
                source_outcomes=(),
                candidate_profiles=(),
                similarities=(),
            )


# ---------------------------------------------------------------------------
# PROVENANCE ADVERSARIAL TESTS
# ---------------------------------------------------------------------------
#
# These tests use TEST-ONLY object.__setattr__ tampering to build states
# that frozen contracts normally prevent. They prove the 7B provenance
# audit catches evidence from wrong sources, wrong timestamps,
# cross-candidate evidence, etc.
#


class TestProvenanceAdversarial:
    def _build_result_with_evidence(
        self,
    ) -> EnterpriseSsdSimilarityResult:
        """Build a valid result with real evidence from a FETCHED source."""
        target = _make_target()
        spec_set = _make_empty_spec_set(target)
        source = _make_source()
        discovery_fetcher = _FakePageFetcher(body=_read_fixture())

        discovery_result = discover_enterprise_ssd_comparable_candidates(
            target_identity=target,
            target_specification_set=spec_set,
            sources=(source,),
            page_fetcher=discovery_fetcher,
        )

        score_fetcher = _FakePageFetcher(body=_read_fixture())
        return research_and_score_enterprise_ssd_candidates(
            discovery_result=discovery_result,
            page_fetcher=score_fetcher,
        )

    def test_foreign_final_url_evidence_rejected(self) -> None:
        """Evidence with a foreign final_url is rejected by provenance audit."""
        result = self._build_result_with_evidence()

        # Tamper: change one observation's source_url to a foreign URL
        # Find a candidate with evidence
        for profile in result.candidate_profiles:
            for resolution in profile.specification_set.resolutions.values():
                for evidence in resolution.evidence:
                    object.__setattr__(
                        evidence.observation,
                        "source_url",
                        "https://evil.example.com/foreign/",
                    )
                    # Now try to construct — should fail
                    with pytest.raises(ValueError, match="does not trace to any FETCHED"):
                        EnterpriseSsdSimilarityResult(
                            discovery_result=result.discovery_result,
                            source_outcomes=result.source_outcomes,
                            candidate_profiles=result.candidate_profiles,
                            similarities=result.similarities,
                        )
                    return  # one tamper is enough

        pytest.fail("No evidence found to tamper")

    def test_wrong_retrieved_at_evidence_rejected(self) -> None:
        """Evidence with wrong retrieved_at is rejected by provenance audit."""
        result = self._build_result_with_evidence()

        wrong_time = datetime(2020, 1, 1, 0, 0, 0, tzinfo=timezone.utc)

        for profile in result.candidate_profiles:
            for resolution in profile.specification_set.resolutions.values():
                for evidence in resolution.evidence:
                    object.__setattr__(
                        evidence.observation,
                        "retrieved_at",
                        wrong_time,
                    )
                    with pytest.raises(ValueError, match="does not trace to any FETCHED"):
                        EnterpriseSsdSimilarityResult(
                            discovery_result=result.discovery_result,
                            source_outcomes=result.source_outcomes,
                            candidate_profiles=result.candidate_profiles,
                            similarities=result.similarities,
                        )
                    return

        pytest.fail("No evidence found to tamper")

    def test_wrong_source_name_evidence_rejected(self) -> None:
        """Evidence with wrong source_name is rejected by provenance audit."""
        result = self._build_result_with_evidence()

        for profile in result.candidate_profiles:
            for resolution in profile.specification_set.resolutions.values():
                for evidence in resolution.evidence:
                    object.__setattr__(
                        evidence.observation,
                        "source_name",
                        "Foreign Source",
                    )
                    with pytest.raises(ValueError, match="does not trace to any FETCHED"):
                        EnterpriseSsdSimilarityResult(
                            discovery_result=result.discovery_result,
                            source_outcomes=result.source_outcomes,
                            candidate_profiles=result.candidate_profiles,
                            similarities=result.similarities,
                        )
                    return

        pytest.fail("No evidence found to tamper")

    def test_wrong_authority_evidence_rejected(self) -> None:
        """Evidence with wrong source_authority is rejected by provenance audit."""
        result = self._build_result_with_evidence()

        for profile in result.candidate_profiles:
            for resolution in profile.specification_set.resolutions.values():
                for evidence in resolution.evidence:
                    object.__setattr__(
                        evidence.observation,
                        "source_authority",
                        SourceAuthority.SECONDARY,
                    )
                    with pytest.raises(ValueError, match="does not trace to any FETCHED"):
                        EnterpriseSsdSimilarityResult(
                            discovery_result=result.discovery_result,
                            source_outcomes=result.source_outcomes,
                            candidate_profiles=result.candidate_profiles,
                            similarities=result.similarities,
                        )
                    return

        pytest.fail("No evidence found to tamper")

    def test_cross_candidate_product_identity_rejected(self) -> None:
        """Evidence bound to a different candidate identity is rejected."""
        result = self._build_result_with_evidence()

        # Get two profiles for cross-candidate swap
        profiles = list(result.candidate_profiles)
        assert len(profiles) >= 2

        # Find evidence in profile[0] and tamper its product_identity to profile[1]'s identity
        for resolution in profiles[0].specification_set.resolutions.values():
            for evidence in resolution.evidence:
                object.__setattr__(
                    evidence.observation,
                    "product_identity",
                    profiles[1].candidate_identity,
                )
                with pytest.raises(ValueError, match="product_identity"):
                    EnterpriseSsdSimilarityResult(
                        discovery_result=result.discovery_result,
                        source_outcomes=result.source_outcomes,
                        candidate_profiles=result.candidate_profiles,
                        similarities=result.similarities,
                    )
                return

        pytest.fail("No evidence found to tamper")

    def test_evidence_claiming_fetch_failed_source_rejected(self) -> None:
        """Evidence that would trace to a FETCH_FAILED source is rejected."""
        # Build result, then tamper source outcome to FETCH_FAILED
        # The evidence still has the original final_url and retrieved_at,
        # but no FETCHED outcome matches it
        result = self._build_result_with_evidence()

        # Tamper the source outcome state to FETCH_FAILED
        original_outcome = result.source_outcomes[0]
        object.__setattr__(original_outcome, "outcome_state", ComparableSimilaritySourceOutcomeState.FETCH_FAILED)
        object.__setattr__(original_outcome, "final_url", None)
        object.__setattr__(original_outcome, "retrieved_at", None)

        with pytest.raises(ValueError, match="does not trace to any FETCHED"):
            EnterpriseSsdSimilarityResult(
                discovery_result=result.discovery_result,
                source_outcomes=result.source_outcomes,
                candidate_profiles=result.candidate_profiles,
                similarities=result.similarities,
            )

    def test_evidence_claiming_source_refused_rejected(self) -> None:
        """Evidence that would trace to a SOURCE_REFUSED source is rejected."""
        result = self._build_result_with_evidence()

        original_outcome = result.source_outcomes[0]
        object.__setattr__(original_outcome, "outcome_state", ComparableSimilaritySourceOutcomeState.SOURCE_REFUSED)
        object.__setattr__(original_outcome, "final_url", None)
        object.__setattr__(original_outcome, "retrieved_at", None)

        with pytest.raises(ValueError, match="does not trace to any FETCHED"):
            EnterpriseSsdSimilarityResult(
                discovery_result=result.discovery_result,
                source_outcomes=result.source_outcomes,
                candidate_profiles=result.candidate_profiles,
                similarities=result.similarities,
            )

    def test_unaccounted_source_evidence_rejected(self) -> None:
        """Evidence from a source not in 7B source_outcomes is rejected.

        With empty source_outcomes, the source binding count check fires
        first (no 7B outcomes for 7A EXTRACTED sources). This proves the
        result rejects the incomplete acquisition chain at the source level,
        before reaching the evidence-provenance check.
        """
        result = self._build_result_with_evidence()

        with pytest.raises(ValueError, match="unique EXTRACTED|does not trace"):
            EnterpriseSsdSimilarityResult(
                discovery_result=result.discovery_result,
                source_outcomes=(),  # empty — no sources to match
                candidate_profiles=result.candidate_profiles,
                similarities=result.similarities,
            )


# ---------------------------------------------------------------------------
# SOURCE DESCRIPTOR IDENTITY BINDING
# ---------------------------------------------------------------------------


class TestSourceDescriptorBinding:
    def test_source_outcome_reuses_7a_source_descriptor(self) -> None:
        """7B source outcome uses the exact 7A source descriptor object."""
        target = _make_target()
        spec_set = _make_empty_spec_set(target)
        source = _make_source()
        discovery_fetcher = _FakePageFetcher(body=_read_fixture())

        discovery_result = discover_enterprise_ssd_comparable_candidates(
            target_identity=target,
            target_specification_set=spec_set,
            sources=(source,),
            page_fetcher=discovery_fetcher,
        )

        score_fetcher = _FakePageFetcher(body=_read_fixture())
        similarity_result = research_and_score_enterprise_ssd_candidates(
            discovery_result=discovery_result,
            page_fetcher=score_fetcher,
        )

        # 7B source outcome must use the exact 7A source descriptor
        assert len(similarity_result.source_outcomes) == 1
        seven_b_outcome = similarity_result.source_outcomes[0]

        # Find the matching 7A outcome
        seven_a_outcome = discovery_result.source_outcomes[0]

        # Object identity: same source descriptor
        assert seven_b_outcome.source is seven_a_outcome.source


# ---------------------------------------------------------------------------
# SOURCE OUTCOMES RETAINED
# ---------------------------------------------------------------------------


class TestRetainedSourceOutcomes:
    def test_source_outcomes_present_in_result(self) -> None:
        """Result contains source_outcomes (not discarded)."""
        target = _make_target()
        spec_set = _make_empty_spec_set(target)
        source = _make_source()
        discovery_fetcher = _FakePageFetcher(body=_read_fixture())

        discovery_result = discover_enterprise_ssd_comparable_candidates(
            target_identity=target,
            target_specification_set=spec_set,
            sources=(source,),
            page_fetcher=discovery_fetcher,
        )

        score_fetcher = _FakePageFetcher(body=_read_fixture())
        similarity_result = research_and_score_enterprise_ssd_candidates(
            discovery_result=discovery_result,
            page_fetcher=score_fetcher,
        )

        assert isinstance(similarity_result.source_outcomes, tuple)
        assert len(similarity_result.source_outcomes) == 1
        outcome = similarity_result.source_outcomes[0]
        assert isinstance(outcome, ComparableSimilaritySourceOutcome)
        assert outcome.outcome_state is ComparableSimilaritySourceOutcomeState.FETCHED
        assert outcome.final_url is not None
        assert outcome.retrieved_at is not None

    def test_source_outcomes_present_on_failure(self) -> None:
        """Source outcomes are still present when fetch fails."""
        target = _make_target()
        spec_set = _make_empty_spec_set(target)
        source = _make_source()
        discovery_fetcher = _FakePageFetcher(body=_read_fixture())

        discovery_result = discover_enterprise_ssd_comparable_candidates(
            target_identity=target,
            target_specification_set=spec_set,
            sources=(source,),
            page_fetcher=discovery_fetcher,
        )

        score_fetcher = _FakePageFetcher(error=PageFetchError)
        similarity_result = research_and_score_enterprise_ssd_candidates(
            discovery_result=discovery_result,
            page_fetcher=score_fetcher,
        )

        assert isinstance(similarity_result.source_outcomes, tuple)
        assert len(similarity_result.source_outcomes) == 1
        outcome = similarity_result.source_outcomes[0]
        assert outcome.outcome_state is ComparableSimilaritySourceOutcomeState.FETCH_FAILED
        assert outcome.final_url is None
        assert outcome.retrieved_at is None


class TestSourceBindingAdversarial:
    """Adversarial tests proving the 7A source binding invariant.

    These tests prove that EnterpriseSsdSimilarityResult rejects:
    - foreign (copied/value-equal) source descriptors
    - missing source outcomes
    The frozen 7A source descriptor chain must be provably intact.
    """

    def test_foreign_7a_source_outcome_rejected(self) -> None:
        """A copied/value-equal source descriptor is rejected.

        The 7B source outcome must use the exact 7A ComparableCandidateSource
        object (identity), not a value-equal substitute.
        """
        target = _make_target()
        spec_set = _make_empty_spec_set(target)
        real_source = _make_source()
        discovery_fetcher = _FakePageFetcher(body=_read_fixture())

        discovery_result = discover_enterprise_ssd_comparable_candidates(
            target_identity=target,
            target_specification_set=spec_set,
            sources=(real_source,),
            page_fetcher=discovery_fetcher,
        )

        score_fetcher = _FakePageFetcher(body=_read_fixture())
        full_result = research_and_score_enterprise_ssd_candidates(
            discovery_result=discovery_result,
            page_fetcher=score_fetcher,
        )

        # Create a NEW ComparableCandidateSource with same values but
        # different object identity
        foreign_source = ComparableCandidateSource(
            source_name=real_source.source_name,
            source_url=real_source.source_url,
            source_authority=SourceAuthority.AUTHORITATIVE,
        )
        assert foreign_source is not real_source  # different object
        assert foreign_source.source_name == real_source.source_name
        assert foreign_source.source_url == real_source.source_url

        # Create a 7B outcome using the foreign source
        foreign_outcome = ComparableSimilaritySourceOutcome(
            source=foreign_source,
            final_url=full_result.source_outcomes[0].final_url,
            retrieved_at=full_result.source_outcomes[0].retrieved_at,
            outcome_state=ComparableSimilaritySourceOutcomeState.FETCHED,
        )

        # Result construction must reject the foreign source
        with pytest.raises(ValueError, match="not the same object"):
            EnterpriseSsdSimilarityResult(
                discovery_result=discovery_result,
                source_outcomes=(foreign_outcome,),
                candidate_profiles=full_result.candidate_profiles,
                similarities=full_result.similarities,
            )

    def test_missing_unique_source_outcome_rejected(self) -> None:
        """Empty source_outcomes when 7A has EXTRACTED sources is rejected.

        The complete 7B acquisition audit must be present.
        """
        target = _make_target()
        spec_set = _make_empty_spec_set(target)
        source = _make_source()
        discovery_fetcher = _FakePageFetcher(body=_read_fixture())

        discovery_result = discover_enterprise_ssd_comparable_candidates(
            target_identity=target,
            target_specification_set=spec_set,
            sources=(source,),
            page_fetcher=discovery_fetcher,
        )

        # discovery_result has 1 EXTRACTED source outcome
        assert any(
            o.outcome_state is DiscoverySourceOutcomeState.EXTRACTED
            for o in discovery_result.source_outcomes
        )

        # Run pipeline to get valid profiles/similarities
        score_fetcher = _FakePageFetcher(body=_read_fixture())
        full_result = research_and_score_enterprise_ssd_candidates(
            discovery_result=discovery_result,
            page_fetcher=score_fetcher,
        )

        # Construct result with empty source_outcomes — must fail
        with pytest.raises(ValueError, match="unique EXTRACTED"):
            EnterpriseSsdSimilarityResult(
                discovery_result=discovery_result,
                source_outcomes=(),  # missing!
                candidate_profiles=full_result.candidate_profiles,
                similarities=full_result.similarities,
            )


class TestSourceOutcomeSelfConsistency:
    """Constructor-level self-consistency for ComparableSimilaritySourceOutcome."""

    def test_fetch_failed_non_none_final_url_rejected(self) -> None:
        """FETCH_FAILED with non-None final_url is rejected."""
        source = _make_source()
        with pytest.raises(ValueError, match="final_url"):
            ComparableSimilaritySourceOutcome(
                source=source,
                final_url="https://example.com/",  # should be None
                retrieved_at=None,
                outcome_state=ComparableSimilaritySourceOutcomeState.FETCH_FAILED,
            )

    def test_source_refused_non_none_retrieved_at_rejected(self) -> None:
        """SOURCE_REFUSED with non-None retrieved_at is rejected."""
        source = _make_source()
        with pytest.raises(ValueError, match="retrieved_at"):
            ComparableSimilaritySourceOutcome(
                source=source,
                final_url=None,
                retrieved_at=_RETRIEVED_AT,  # should be None
                outcome_state=ComparableSimilaritySourceOutcomeState.SOURCE_REFUSED,
            )

    def test_fetched_invalid_final_url_rejected(self) -> None:
        """FETCHED with structurally invalid final_url is rejected
        through require_fetchable_url."""
        source = _make_source()
        with pytest.raises(ValueError, match="fetchable|http"):
            ComparableSimilaritySourceOutcome(
                source=source,
                final_url="not-a-url",  # invalid URL
                retrieved_at=_RETRIEVED_AT,
                outcome_state=ComparableSimilaritySourceOutcomeState.FETCHED,
            )


# ---------------------------------------------------------------------------
# REAL E2E — frozen 6C -> 7A -> 7B
# ---------------------------------------------------------------------------


class TestRealE2E:
    def test_real_seagate_6c_7a_7b(self) -> None:
        """Full pipeline: frozen 6C -> frozen 7A -> 7B.

        Real Seagate fixture, no live web fetch.
        """
        from product_intelligence.execution.specification_evidence import (
            SpecificationEvidenceSource,
            research_enterprise_ssd_specifications,
        )

        target = _make_target("XP15360SE70005")
        source = _make_source()

        # Phase 6C: Real specification extraction
        spec_source = SpecificationEvidenceSource(
            product_identity=target,
            source_name=source.source_name,
            source_url=source.source_url,
            source_authority=source.source_authority,
        )
        spec_fetcher = _FakePageFetcher(body=_read_fixture())

        spec_result = research_enterprise_ssd_specifications(
            product_identity=target,
            sources=(spec_source,),
            page_fetcher=spec_fetcher,
        )

        spec_set = spec_result.product_specification_set
        assert spec_set.product_identity is target

        # Verify target physical_form_factor is VERIFIED
        ff_resolution = spec_set.resolutions["physical_form_factor"]
        assert ff_resolution.state is ResolutionState.VERIFIED
        assert ff_resolution.resolved_value.value == "2.5-inch"

        # Phase 7A: Real candidate discovery
        discovery_fetcher = _FakePageFetcher(body=_read_fixture())
        discovery_result = discover_enterprise_ssd_comparable_candidates(
            target_identity=target,
            target_specification_set=spec_set,
            sources=(source,),
            page_fetcher=discovery_fetcher,
        )

        assert len(discovery_result.observations) == 81
        assert len(discovery_result.assessments) == 81
        assert len(discovery_result.candidates) == 80

        # Phase 7B: Real similarity scoring
        score_fetcher = _FakePageFetcher(body=_read_fixture())
        similarity_result = research_and_score_enterprise_ssd_candidates(
            discovery_result=discovery_result,
            page_fetcher=score_fetcher,
        )

        # 80 candidates, 80 profiles, 80 similarities
        assert len(similarity_result.candidate_profiles) == 80
        assert len(similarity_result.similarities) == 80

        # One fetch per unique source (not 80)
        assert score_fetcher.fetch_count == 1

        # Source outcomes retained
        assert len(similarity_result.source_outcomes) == 1
        outcome = similarity_result.source_outcomes[0]
        assert outcome.outcome_state is ComparableSimilaritySourceOutcomeState.FETCHED

        # Known sibling XP15360SE70015
        sibling_idx = None
        for i, candidate in enumerate(discovery_result.candidates):
            if candidate.normalized_part_number == "XP15360SE70015":
                sibling_idx = i
                break
        assert sibling_idx is not None, "XP15360SE70015 not found in candidates"

        sibling_similarity = similarity_result.similarities[sibling_idx]
        sibling_profile = similarity_result.candidate_profiles[sibling_idx]

        # Report actual scoreable fields for XP15360SE70015
        scored_fields = [
            a
            for a in sibling_similarity.field_assessments
            if a.comparison_state.value == "SCORED"
        ]
        assert len(scored_fields) >= 1

        # Form Factor should be VERIFIED on both sides (same page, same extraction)
        ff_assessment = None
        for a in sibling_similarity.field_assessments:
            if a.definition.key == "physical_form_factor":
                ff_assessment = a
                break
        assert ff_assessment is not None
        assert ff_assessment.comparison_state.value == "SCORED"
        assert ff_assessment.field_similarity == 1

        # Report real candidate coverage distribution
        coverage_values = [
            s.evidence_coverage for s in similarity_result.similarities
        ]
        scored_counts = [s.scored_field_count for s in similarity_result.similarities]

        # All similarities target the same spec set
        for similarity in similarity_result.similarities:
            assert (
                similarity.target_specification_set
                is discovery_result.target_specification_set
            )

        # --- Real-data assertions ---
        # Under current frozen 6C extraction capability (only "Form Factor" label
        # is mapped), each candidate gets exactly 1 scoreable field when it appears
        # in the same source as the target.

        # All candidates have 1 scored field (physical_form_factor)
        assert all(c == 1 for c in scored_counts), (
            f"Expected 1 scored field per candidate, got {set(scored_counts)}"
        )

        # All candidates have coverage = 1/12
        expected_coverage = Decimal("1") / Decimal("12")
        assert all(c == expected_coverage for c in coverage_values), (
            f"Expected coverage {expected_coverage}, got {set(coverage_values)}"
        )

        # All observed similarities are 1 (same form factor across siblings)
        assert all(
            s.observed_similarity == Decimal("1")
            for s in similarity_result.similarities
        )

        # All evidence-weighted similarities = 1/12
        expected_weighted = Decimal("1") / Decimal("12")
        assert all(
            s.evidence_weighted_similarity == expected_weighted
            for s in similarity_result.similarities
        )

        # Evidence sparsity conclusion:
        # Current candidate specification evidence is too sparse for useful
        # differentiation (only 1 of 12 fields scoreable per candidate).
        # This is a limitation of frozen 6C extraction capability (only
        # "Form Factor" label mapped), not a 7B failure.
