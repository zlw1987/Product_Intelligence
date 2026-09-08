"""Comparable discovery execution tests (PRODUCT-INTEL.7A).

Tests the execution layer: source contract, target binding, fetch outcomes,
and result self-audit invariants.
"""

from __future__ import annotations

import os
from datetime import datetime, timezone
from typing import Protocol

import pytest

from product_intelligence.domain.enums import IdentityMatchType
from product_intelligence.domain.models import ProductIdentity
from product_intelligence.execution.comparable_discovery import (
    ComparableCandidateDiscoveryResult,
    ComparableCandidateSourceOutcome,
    ComparableCandidateSourceOutcomeState,
    discover_enterprise_ssd_comparable_candidates,
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
from product_intelligence.research.specifications import (
    ProductSpecificationSet,
    ResolutionState,
    SpecificationDefinition,
    SpecificationObservation,
    SpecificationResolution,
    SpecificationValue,
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
    """Build a complete ProductSpecificationSet with all UNKNOWN resolutions."""
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
    def test_authoritative_required(self) -> None:
        """AUTHORITATIVE sources work."""
        target = _make_target()
        spec_set = _make_empty_spec_set(target)
        source = _make_source()
        fetcher = _FakePageFetcher(body="")
        result = discover_enterprise_ssd_comparable_candidates(
            target_identity=target,
            target_specification_set=spec_set,
            sources=(source,),
            page_fetcher=fetcher,
        )
        assert len(result.source_outcomes) == 1

    def test_secondary_rejected_before_fetch(self) -> None:
        """SECONDARY authority source is rejected before any fetch."""
        target = _make_target()
        spec_set = _make_empty_spec_set(target)
        secondary_source = ComparableCandidateSource(
            source_name="Secondary Source",
            source_url=_SOURCE_URL,
            source_authority=SourceAuthority.SECONDARY,
        )
        fetcher = _FakePageFetcher(body=_read_fixture())
        with pytest.raises(ValueError, match="SECONDARY"):
            discover_enterprise_ssd_comparable_candidates(
                target_identity=target,
                target_specification_set=spec_set,
                sources=(secondary_source,),
                page_fetcher=fetcher,
            )
        assert fetcher.fetch_count == 0

    def test_invalid_url_rejected(self) -> None:
        """Invalid URL is rejected at source construction."""
        with pytest.raises(ValueError):
            ComparableCandidateSource(
                source_name="Bad URL",
                source_url="not-a-url",
                source_authority=SourceAuthority.AUTHORITATIVE,
            )

    def test_source_name_validation(self) -> None:
        """Empty source name is rejected."""
        with pytest.raises(ValueError):
            ComparableCandidateSource(
                source_name="",
                source_url=_SOURCE_URL,
                source_authority=SourceAuthority.AUTHORITATIVE,
            )


# ---------------------------------------------------------------------------
# TARGET BINDING
# ---------------------------------------------------------------------------


class TestTargetBinding:
    def test_target_must_be_established(self) -> None:
        target = ProductIdentity(
            manufacturer_part_number="ABC",
            match_type=IdentityMatchType.UNKNOWN,
        )
        spec_set = _make_empty_spec_set(target) if target.is_established else None
        source = _make_source()
        fetcher = _FakePageFetcher(body="")
        with pytest.raises(ValueError):
            discover_enterprise_ssd_comparable_candidates(
                target_identity=target,
                target_specification_set=spec_set or _make_empty_spec_set(_make_target()),
                sources=(source,),
                page_fetcher=fetcher,
            )

    def test_target_spec_set_identity_mismatch_rejected(self) -> None:
        """Specification set for different identity is rejected."""
        target = _make_target("XP15360SE70005")
        other_identity = _make_target("DIFFERENT_MPN")
        spec_set = _make_empty_spec_set(other_identity)
        source = _make_source()
        fetcher = _FakePageFetcher(body=_read_fixture())
        with pytest.raises(ValueError):
            discover_enterprise_ssd_comparable_candidates(
                target_identity=target,
                target_specification_set=spec_set,
                sources=(source,),
                page_fetcher=fetcher,
            )
        assert fetcher.fetch_count == 0

    def test_wrong_category_schema_rejected(self) -> None:
        """Non-ENTERPRISE_SSD_SCHEMA spec set is rejected with ValueError
        before any fetch occurs."""
        import pytest

        from product_intelligence.research.specifications import (
            CategorySchema,
            SpecificationDefinition,
            SpecificationValueKind,
        )

        # Construct a valid alternate schema using frozen 6A contracts
        alternate_schema = CategorySchema(
            schema_id="fake-schema",
            schema_version="1.0",
            label="Fake Schema",
            definitions={
                "fake_field": SpecificationDefinition(
                    key="fake_field",
                    label="Fake Field",
                    value_kind=SpecificationValueKind.TEXT,
                ),
            },
        )

        target = _make_target("XP15360SE70005")
        # Build a spec set using the wrong schema
        resolutions: dict[str, SpecificationResolution] = {}
        for key, definition in alternate_schema.definitions.items():
            resolution = resolve_specification(target, definition, ())
            resolutions[key] = resolution
        wrong_spec_set = ProductSpecificationSet(
            product_identity=target,
            category_schema=alternate_schema,
            resolutions=resolutions,
        )

        source = _make_source()
        fetcher = _FakePageFetcher(body=_read_fixture())

        with pytest.raises(ValueError, match="ENTERPRISE_SSD_SCHEMA"):
            discover_enterprise_ssd_comparable_candidates(
                target_identity=target,
                target_specification_set=wrong_spec_set,
                sources=(source,),
                page_fetcher=fetcher,
            )
        # No fetch should have occurred
        assert fetcher.fetch_count == 0


# ---------------------------------------------------------------------------
# FETCH
# ---------------------------------------------------------------------------


class TestFetchOutcomes:
    def test_successful_source(self) -> None:
        target = _make_target()
        spec_set = _make_empty_spec_set(target)
        source = _make_source()
        fetcher = _FakePageFetcher(body=_read_fixture())
        result = discover_enterprise_ssd_comparable_candidates(
            target_identity=target,
            target_specification_set=spec_set,
            sources=(source,),
            page_fetcher=fetcher,
        )
        assert len(result.source_outcomes) == 1
        assert result.source_outcomes[0].outcome_state is ComparableCandidateSourceOutcomeState.EXTRACTED

    def test_requested_not_equal_final_url_provenance(self) -> None:
        """When fetch redirects, observation uses final_url (like 6C)."""
        target = _make_target()
        spec_set = _make_empty_spec_set(target)
        source_url = "https://www.seagate.com/support/test/"
        source = _make_source(source_url=source_url)
        final = "https://www.seagate.com/support/enterprise-storage/solid-state-drives/nytro-5050/"
        fetcher = _FakePageFetcher(
            body=_read_fixture(),
            final_url=final,
        )
        result = discover_enterprise_ssd_comparable_candidates(
            target_identity=target,
            target_specification_set=spec_set,
            sources=(source,),
            page_fetcher=fetcher,
        )
        outcome = result.source_outcomes[0]
        assert outcome.final_url == final
        # Observations use final_url (like frozen 6C SpecificationObservation)
        assert result.observations[0].source_url == final

    def test_no_observations(self) -> None:
        """Empty body produces NO_OBSERVATIONS."""
        target = _make_target()
        spec_set = _make_empty_spec_set(target)
        source = _make_source()
        fetcher = _FakePageFetcher(body="<html><body>no data</body></html>")
        result = discover_enterprise_ssd_comparable_candidates(
            target_identity=target,
            target_specification_set=spec_set,
            sources=(source,),
            page_fetcher=fetcher,
        )
        assert result.source_outcomes[0].outcome_state is ComparableCandidateSourceOutcomeState.NO_OBSERVATIONS
        assert result.source_outcomes[0].observation_count == 0

    def test_page_fetch_error(self) -> None:
        """PageFetchError -> FETCH_FAILED, next source continues."""
        target = _make_target()
        spec_set = _make_empty_spec_set(target)
        fetcher_fails = _FakePageFetcher(error=PageFetchError)
        source1 = _make_source(source_url="https://fail.example.com/1/")
        source2 = _make_source(
            source_url=_SOURCE_URL,
            source_name="Source 2",
        )
        fetcher_succeeds = _FakePageFetcher(body=_read_fixture())
        # Use a fetcher that fails first then succeeds
        call_count = [0]
        def _fetch(request: PageFetchRequest) -> FetchedPage:
            call_count[0] += 1
            if call_count[0] == 1:
                raise PageFetchError("simulated failure")
            return FetchedPage(
                requested_url=request.url,
                final_url=request.url,
                retrieved_at=_RETRIEVED_AT,
                status_code=200,
                body_text=_read_fixture(),
                content_type="text/html",
                body_byte_count=0,
                redirect_count=0,
                fetcher_id="fake",
            )

        class _SequentialFetcher:
            def fetch(self, request: PageFetchRequest) -> FetchedPage:
                return _fetch(request)

        result = discover_enterprise_ssd_comparable_candidates(
            target_identity=target,
            target_specification_set=spec_set,
            sources=(source1, source2),
            page_fetcher=_SequentialFetcher(),
        )
        assert result.source_outcomes[0].outcome_state is ComparableCandidateSourceOutcomeState.FETCH_FAILED
        assert result.source_outcomes[1].outcome_state is ComparableCandidateSourceOutcomeState.EXTRACTED

    def test_unsafe_fetch_target_error(self) -> None:
        """UnsafeFetchTargetError -> SOURCE_REFUSED, next source continues."""
        target = _make_target()
        spec_set = _make_empty_spec_set(target)
        source1 = ComparableCandidateSource(
            source_name="Unsafe Source",
            source_url="http://untrusted.example.com/catalog/",
            source_authority=SourceAuthority.AUTHORITATIVE,
        )
        source2 = _make_source()

        call_count = [0]
        def _fetch(request: PageFetchRequest) -> FetchedPage:
            call_count[0] += 1
            if call_count[0] == 1:
                raise UnsafeFetchTargetError("refused destination")
            return FetchedPage(
                requested_url=request.url,
                final_url=request.url,
                retrieved_at=_RETRIEVED_AT,
                status_code=200,
                body_text=_read_fixture(),
                content_type="text/html",
                body_byte_count=0,
                redirect_count=0,
                fetcher_id="fake",
            )

        class _SequentialFetcher:
            def fetch(self, request: PageFetchRequest) -> FetchedPage:
                return _fetch(request)

        result = discover_enterprise_ssd_comparable_candidates(
            target_identity=target,
            target_specification_set=spec_set,
            sources=(source1, source2),
            page_fetcher=_SequentialFetcher(),
        )
        assert result.source_outcomes[0].outcome_state is ComparableCandidateSourceOutcomeState.SOURCE_REFUSED
        assert result.source_outcomes[1].outcome_state is ComparableCandidateSourceOutcomeState.EXTRACTED

    def test_programming_exception_propagates(self, monkeypatch) -> None:
        """Programming exception from extraction propagates as RuntimeError.
        It must NOT become NO_OBSERVATIONS, FETCH_FAILED, or SOURCE_REFUSED."""
        import pytest

        # Monkeypatch at the module where the function is actually called
        import product_intelligence.execution.comparable_discovery as mod

        def _raising_extraction(**kwargs):
            raise RuntimeError("test programming defect")

        monkeypatch.setattr(
            mod,
            "extract_enterprise_ssd_candidate_observations",
            _raising_extraction,
        )

        target = _make_target()
        spec_set = _make_empty_spec_set(target)
        source = _make_source()
        fetcher = _FakePageFetcher(body=_read_fixture())

        with pytest.raises(RuntimeError, match="test programming defect"):
            discover_enterprise_ssd_comparable_candidates(
                target_identity=target,
                target_specification_set=spec_set,
                sources=(source,),
                page_fetcher=fetcher,
            )

    def test_each_source_fetched_once(self) -> None:
        """Each source is fetched exactly once."""
        target = _make_target()
        spec_set = _make_empty_spec_set(target)
        source1 = _make_source(source_url="https://www.seagate.com/support/test1/")
        source2 = _make_source(
            source_url="https://www.seagate.com/support/test2/",
            source_name="Source 2",
        )
        fetcher = _FakePageFetcher(body=_read_fixture())
        discover_enterprise_ssd_comparable_candidates(
            target_identity=target,
            target_specification_set=spec_set,
            sources=(source1, source2),
            page_fetcher=fetcher,
        )
        assert fetcher.fetch_count == 2


# ---------------------------------------------------------------------------
# RESULT AUDIT
# ---------------------------------------------------------------------------


class TestResultAudit:
    def test_count_mismatch_rejected(self) -> None:
        """Result construction rejects observation count mismatch."""
        import pytest as _pytest

        target = _make_target()
        spec_set = _make_empty_spec_set(target)
        source = _make_source()
        outcome = ComparableCandidateSourceOutcome(
            source=source,
            final_url=_SOURCE_URL,
            retrieved_at=_RETRIEVED_AT,
            outcome_state=ComparableCandidateSourceOutcomeState.EXTRACTED,
            observation_count=5,  # claims 5 but we provide 3
        )
        from product_intelligence.research.comparable_candidates import (
            ComparableCandidateObservation,
        )
        obs1 = ComparableCandidateObservation(
            manufacturer_part_number_raw="ABC1",
            product_name_raw=None,
            source_name=_SOURCE_NAME,
            source_url=_SOURCE_URL,
            retrieved_at=_RETRIEVED_AT,
            source_authority=SourceAuthority.AUTHORITATIVE,
        )
        with _pytest.raises(ValueError):
            ComparableCandidateDiscoveryResult(
                target_identity=target,
                target_specification_set=spec_set,
                source_outcomes=(outcome,),
                observations=(obs1,),
                assessments=(),
                candidates=(),
            )

    def test_observation_from_unaccounted_source_rejected(self) -> None:
        """Observation from a non-EXTRACTED source is rejected."""
        import pytest as _pytest

        target = _make_target()
        spec_set = _make_empty_spec_set(target)
        source = _make_source()
        # EXTRACTED with count=1
        outcome = ComparableCandidateSourceOutcome(
            source=source,
            final_url=_SOURCE_URL,
            retrieved_at=_RETRIEVED_AT,
            outcome_state=ComparableCandidateSourceOutcomeState.EXTRACTED,
            observation_count=1,
        )
        # Observation from different source
        from product_intelligence.research.comparable_candidates import (
            ComparableCandidateObservation,
        )
        other_obs = ComparableCandidateObservation(
            manufacturer_part_number_raw="ABC1",
            product_name_raw=None,
            source_name="Other Source",
            source_url="https://other.example.com/",
            retrieved_at=_RETRIEVED_AT,
            source_authority=SourceAuthority.AUTHORITATIVE,
        )
        from product_intelligence.research.comparable_candidates import (
            ComparableCandidateAssessment,
        )
        assessment = ComparableCandidateAssessment.build(target, other_obs)
        with _pytest.raises(ValueError):
            ComparableCandidateDiscoveryResult(
                target_identity=target,
                target_specification_set=spec_set,
                source_outcomes=(outcome,),
                observations=(other_obs,),
                assessments=(assessment,),
                candidates=(),
            )

    def test_fabricated_target_self_rejected(self) -> None:
        """Result's independent fail-closed protection rejects a tampered
        assessment whose disposition no longer matches the re-derived value.

        We create a valid assessment via .build() then deliberately tamper
        with the frozen object using object.__setattr__ (test-only) to prove
        the result's audit catches it."""
        import pytest as _pytest

        target = _make_target()
        spec_set = _make_empty_spec_set(target)
        source = _make_source()
        outcome = ComparableCandidateSourceOutcome(
            source=source,
            final_url=_SOURCE_URL,
            retrieved_at=_RETRIEVED_AT,
            outcome_state=ComparableCandidateSourceOutcomeState.EXTRACTED,
            observation_count=1,
        )
        from product_intelligence.research.comparable_candidates import (
            ComparableCandidateObservation,
            ComparableCandidateAssessment,
            CandidateDisposition,
        )

        obs = ComparableCandidateObservation(
            manufacturer_part_number_raw="DIFFERENT_MPN",
            product_name_raw=None,
            source_name=_SOURCE_NAME,
            source_url=_SOURCE_URL,
            retrieved_at=_RETRIEVED_AT,
            source_authority=SourceAuthority.AUTHORITATIVE,
        )
        # Build a correct assessment (will be CANDIDATE)
        assessment = ComparableCandidateAssessment.build(target, obs)
        assert assessment.disposition is CandidateDisposition.CANDIDATE

        # Tamper: change disposition to TARGET_SELF (impossible for this MPN)
        object.__setattr__(assessment, "disposition", CandidateDisposition.TARGET_SELF)

        with _pytest.raises(ValueError, match="disposition"):
            ComparableCandidateDiscoveryResult(
                target_identity=target,
                target_specification_set=spec_set,
                source_outcomes=(outcome,),
                observations=(obs,),
                assessments=(assessment,),
                candidates=(),
            )

    def test_target_assessment_injected_into_candidate_rejected(self) -> None:
        """TARGET_SELF assessment cannot appear in candidate evidence."""
        import pytest as _pytest

        target = _make_target()
        spec_set = _make_empty_spec_set(target)
        source = _make_source()
        outcome = ComparableCandidateSourceOutcome(
            source=source,
            final_url=_SOURCE_URL,
            retrieved_at=_RETRIEVED_AT,
            outcome_state=ComparableCandidateSourceOutcomeState.EXTRACTED,
            observation_count=2,
        )
        from product_intelligence.research.comparable_candidates import (
            ComparableCandidateObservation,
            ComparableCandidateAssessment,
            ComparableCandidate,
        )
        target_obs = ComparableCandidateObservation(
            manufacturer_part_number_raw="XP15360SE70005",
            product_name_raw=None,
            source_name=_SOURCE_NAME,
            source_url=_SOURCE_URL,
            retrieved_at=_RETRIEVED_AT,
            source_authority=SourceAuthority.AUTHORITATIVE,
        )
        other_obs = ComparableCandidateObservation(
            manufacturer_part_number_raw="DIFFERENT",
            product_name_raw=None,
            source_name=_SOURCE_NAME,
            source_url=_SOURCE_URL,
            retrieved_at=_RETRIEVED_AT,
            source_authority=SourceAuthority.AUTHORITATIVE,
        )
        target_assessment = ComparableCandidateAssessment.build(target, target_obs)
        other_assessment = ComparableCandidateAssessment.build(target, other_obs)
        assert target_assessment.disposition.value == "TARGET_SELF"
        assert other_assessment.disposition.value == "CANDIDATE"

        # The dedup should exclude TARGET_SELF, so if we try to inject it manually:
        # Candidate.build requires all CANDIDATE — it will reject
        with _pytest.raises(ValueError):
            ComparableCandidate.build((target_assessment, other_assessment))

    def test_candidate_missing_eligible_assessment_rejected(self) -> None:
        """If a CANDIDATE assessment exists in result but not in any candidate,
        the result rejects it."""
        import pytest as _pytest

        target = _make_target()
        spec_set = _make_empty_spec_set(target)
        source = _make_source()
        outcome = ComparableCandidateSourceOutcome(
            source=source,
            final_url=_SOURCE_URL,
            retrieved_at=_RETRIEVED_AT,
            outcome_state=ComparableCandidateSourceOutcomeState.EXTRACTED,
            observation_count=1,
        )
        from product_intelligence.research.comparable_candidates import (
            ComparableCandidateObservation,
            ComparableCandidateAssessment,
        )
        obs = ComparableCandidateObservation(
            manufacturer_part_number_raw="ABC123",
            product_name_raw=None,
            source_name=_SOURCE_NAME,
            source_url=_SOURCE_URL,
            retrieved_at=_RETRIEVED_AT,
            source_authority=SourceAuthority.AUTHORITATIVE,
        )
        assessment = ComparableCandidateAssessment.build(target, obs)
        assert assessment.disposition.value == "CANDIDATE"
        # Result has the assessment but no candidates
        with _pytest.raises(ValueError):
            ComparableCandidateDiscoveryResult(
                target_identity=target,
                target_specification_set=spec_set,
                source_outcomes=(outcome,),
                observations=(obs,),
                assessments=(assessment,),
                candidates=(),
            )

    def test_duplicate_candidate_normalized_keys_rejected(self) -> None:
        """Duplicate normalized keys in candidates are rejected."""
        import pytest as _pytest

        target = _make_target("ZZZ999")
        spec_set = _make_empty_spec_set(target)
        source = _make_source()
        outcome = ComparableCandidateSourceOutcome(
            source=source,
            final_url=_SOURCE_URL,
            retrieved_at=_RETRIEVED_AT,
            outcome_state=ComparableCandidateSourceOutcomeState.EXTRACTED,
            observation_count=1,
        )
        from product_intelligence.research.comparable_candidates import (
            ComparableCandidateObservation,
            ComparableCandidateAssessment,
            ComparableCandidate,
        )
        obs = ComparableCandidateObservation(
            manufacturer_part_number_raw="ABC123",
            product_name_raw=None,
            source_name=_SOURCE_NAME,
            source_url=_SOURCE_URL,
            retrieved_at=_RETRIEVED_AT,
            source_authority=SourceAuthority.AUTHORITATIVE,
        )
        assessment = ComparableCandidateAssessment.build(target, obs)
        candidate = ComparableCandidate.build((assessment,))
        # Two candidates with same normalized key
        with _pytest.raises(ValueError):
            ComparableCandidateDiscoveryResult(
                target_identity=target,
                target_specification_set=spec_set,
                source_outcomes=(outcome,),
                observations=(obs,),
                assessments=(assessment,),
                candidates=(candidate, candidate),
            )

    # ------------------------------------------------------------------
    # Adversarial: result-provenance identity tests
    # ------------------------------------------------------------------

    def test_secondary_source_outcome_rejected_in_result(self) -> None:
        """SECONDARY source outcome is rejected in 7A v1 result.
        Even with exact target observation + TARGET_SELF and no candidates."""
        import pytest as _pytest

        target = _make_target("XP15360SE70005")
        spec_set = _make_empty_spec_set(target)
        secondary_source = ComparableCandidateSource(
            source_name=_SOURCE_NAME,
            source_url=_SOURCE_URL,
            source_authority=SourceAuthority.SECONDARY,
        )
        outcome = ComparableCandidateSourceOutcome(
            source=secondary_source,
            final_url=_SOURCE_URL,
            retrieved_at=_RETRIEVED_AT,
            outcome_state=ComparableCandidateSourceOutcomeState.EXTRACTED,
            observation_count=1,
        )
        from product_intelligence.research.comparable_candidates import (
            ComparableCandidateObservation,
            ComparableCandidateAssessment,
        )
        obs = ComparableCandidateObservation(
            manufacturer_part_number_raw="XP15360SE70005",
            product_name_raw=None,
            source_name=_SOURCE_NAME,
            source_url=_SOURCE_URL,
            retrieved_at=_RETRIEVED_AT,
            source_authority=SourceAuthority.SECONDARY,
        )
        assessment = ComparableCandidateAssessment.build(target, obs)
        # TARGET_SELF + no candidates
        with _pytest.raises(ValueError, match="AUTHORITATIVE"):
            ComparableCandidateDiscoveryResult(
                target_identity=target,
                target_specification_set=spec_set,
                source_outcomes=(outcome,),
                observations=(obs,),
                assessments=(assessment,),
                candidates=(),
            )

    def test_wrong_final_url_rejected(self) -> None:
        """Observation source_url does not match outcome final_url."""
        import pytest as _pytest

        target = _make_target("ZZZ999")
        spec_set = _make_empty_spec_set(target)
        source = _make_source()
        wrong_url = "https://wrong.example.com/catalog/"
        outcome = ComparableCandidateSourceOutcome(
            source=source,
            final_url=wrong_url,  # different from observation's source_url
            retrieved_at=_RETRIEVED_AT,
            outcome_state=ComparableCandidateSourceOutcomeState.EXTRACTED,
            observation_count=1,
        )
        from product_intelligence.research.comparable_candidates import (
            ComparableCandidateObservation,
            ComparableCandidateAssessment,
        )
        obs = ComparableCandidateObservation(
            manufacturer_part_number_raw="ABC123",
            product_name_raw=None,
            source_name=_SOURCE_NAME,
            source_url=_SOURCE_URL,  # matches outcome.source.source_url, not final_url
            retrieved_at=_RETRIEVED_AT,
            source_authority=SourceAuthority.AUTHORITATIVE,
        )
        assessment = ComparableCandidateAssessment.build(target, obs)
        with _pytest.raises(ValueError, match="provenance|trace"):
            ComparableCandidateDiscoveryResult(
                target_identity=target,
                target_specification_set=spec_set,
                source_outcomes=(outcome,),
                observations=(obs,),
                assessments=(assessment,),
                candidates=(),
            )

    def test_wrong_retrieved_at_rejected(self) -> None:
        """Observation retrieved_at does not match outcome retrieved_at."""
        import pytest as _pytest

        target = _make_target("ZZZ999")
        spec_set = _make_empty_spec_set(target)
        source = _make_source()
        other_time = _RETRIEVED_AT.replace(minute=59) if _RETRIEVED_AT.minute < 59 else _RETRIEVED_AT.replace(minute=0)
        outcome = ComparableCandidateSourceOutcome(
            source=source,
            final_url=_SOURCE_URL,
            retrieved_at=other_time,
            outcome_state=ComparableCandidateSourceOutcomeState.EXTRACTED,
            observation_count=1,
        )
        from product_intelligence.research.comparable_candidates import (
            ComparableCandidateObservation,
            ComparableCandidateAssessment,
        )
        obs = ComparableCandidateObservation(
            manufacturer_part_number_raw="ABC123",
            product_name_raw=None,
            source_name=_SOURCE_NAME,
            source_url=_SOURCE_URL,
            retrieved_at=_RETRIEVED_AT,  # different from outcome
            source_authority=SourceAuthority.AUTHORITATIVE,
        )
        assessment = ComparableCandidateAssessment.build(target, obs)
        with _pytest.raises(ValueError):
            ComparableCandidateDiscoveryResult(
                target_identity=target,
                target_specification_set=spec_set,
                source_outcomes=(outcome,),
                observations=(obs,),
                assessments=(assessment,),
                candidates=(),
            )

    def test_observation_assessment_identity_mismatch_rejected(self) -> None:
        """Swapping assessment relative to observation is rejected.
        Two distinct observations with same normalized key and disposition;
        assessments built for each; then swapped."""
        import pytest as _pytest

        target = _make_target("ZZZ999")
        spec_set = _make_empty_spec_set(target)
        source = _make_source()
        outcome = ComparableCandidateSourceOutcome(
            source=source,
            final_url=_SOURCE_URL,
            retrieved_at=_RETRIEVED_AT,
            outcome_state=ComparableCandidateSourceOutcomeState.EXTRACTED,
            observation_count=2,
        )
        from product_intelligence.research.comparable_candidates import (
            ComparableCandidateObservation,
            ComparableCandidateAssessment,
        )

        # Two distinct observations with same provenance but different raw_reference
        obs1 = ComparableCandidateObservation(
            manufacturer_part_number_raw="ABC123",
            product_name_raw=None,
            source_name=_SOURCE_NAME,
            source_url=_SOURCE_URL,
            retrieved_at=_RETRIEVED_AT,
            source_authority=SourceAuthority.AUTHORITATIVE,
            raw_reference="json[0].record[0]",
        )
        obs2 = ComparableCandidateObservation(
            manufacturer_part_number_raw="ABC123",
            product_name_raw=None,
            source_name=_SOURCE_NAME,
            source_url=_SOURCE_URL,
            retrieved_at=_RETRIEVED_AT,
            source_authority=SourceAuthority.AUTHORITATIVE,
            raw_reference="json[0].record[1]",
        )
        a1 = ComparableCandidateAssessment.build(target, obs1)  # a1 -> obs1
        a2 = ComparableCandidateAssessment.build(target, obs2)  # a2 -> obs2

        # Swap: obs1 gets a2, obs2 gets a1
        with _pytest.raises(ValueError, match="same object"):
            ComparableCandidateDiscoveryResult(
                target_identity=target,
                target_specification_set=spec_set,
                source_outcomes=(outcome,),
                observations=(obs1, obs2),
                assessments=(a2, a1),  # swapped
                candidates=(),
            )

    def test_assessment_target_identity_mismatch_rejected(self) -> None:
        """Assessment refers to a different target_identity object."""
        import pytest as _pytest

        result_target = _make_target("XP15360SE70005")
        spec_set = _make_empty_spec_set(result_target)
        other_target = _make_target("XP15360SE70005")  # same MPN, different object
        source = _make_source()
        outcome = ComparableCandidateSourceOutcome(
            source=source,
            final_url=_SOURCE_URL,
            retrieved_at=_RETRIEVED_AT,
            outcome_state=ComparableCandidateSourceOutcomeState.EXTRACTED,
            observation_count=1,
        )
        from product_intelligence.research.comparable_candidates import (
            ComparableCandidateObservation,
            ComparableCandidateAssessment,
        )
        obs = ComparableCandidateObservation(
            manufacturer_part_number_raw="DIFFERENT_MPN",
            product_name_raw=None,
            source_name=_SOURCE_NAME,
            source_url=_SOURCE_URL,
            retrieved_at=_RETRIEVED_AT,
            source_authority=SourceAuthority.AUTHORITATIVE,
        )
        # Build assessment against the OTHER target
        assessment = ComparableCandidateAssessment.build(other_target, obs)

        with _pytest.raises(ValueError, match="target_identity"):
            ComparableCandidateDiscoveryResult(
                target_identity=result_target,
                target_specification_set=spec_set,
                source_outcomes=(outcome,),
                observations=(obs,),
                assessments=(assessment,),
                candidates=(),
            )

    def test_foreign_assessment_rejected(self) -> None:
        """An assessment not in the result's assessments tuple cannot
        appear in candidate evidence.

        Constructs:
        - obs1/a1: a result observation + its assessment (CANDIDATE, same target)
        - obs_dummy: a second observation to satisfy count invariant
        - a_dummy: assessment for obs_dummy (included in result)
        - a_foreign: a separate CANDIDATE assessment for obs1 with same target
          object, same normalized key, AUTHORITATIVE evidence.

        Candidate evidence contains both a1 AND a_foreign. Both normalize to
        the same key and share the same target_identity. ComparableCandidate
        construction succeeds. But a_foreign is NOT in result.assessments,
        so the result's foreign-evidence guard catches it.
        """
        import pytest as _pytest

        target = _make_target("ZZZ999")
        spec_set = _make_empty_spec_set(target)
        source = _make_source()
        outcome = ComparableCandidateSourceOutcome(
            source=source,
            final_url=_SOURCE_URL,
            retrieved_at=_RETRIEVED_AT,
            outcome_state=ComparableCandidateSourceOutcomeState.EXTRACTED,
            observation_count=2,
        )
        from product_intelligence.research.comparable_candidates import (
            ComparableCandidateObservation,
            ComparableCandidateAssessment,
            ComparableCandidate,
        )
        obs1 = ComparableCandidateObservation(
            manufacturer_part_number_raw="ABC123",
            product_name_raw=None,
            source_name=_SOURCE_NAME,
            source_url=_SOURCE_URL,
            retrieved_at=_RETRIEVED_AT,
            source_authority=SourceAuthority.AUTHORITATIVE,
        )
        obs_dummy = ComparableCandidateObservation(
            manufacturer_part_number_raw="DUMMY999",
            product_name_raw=None,
            source_name=_SOURCE_NAME,
            source_url=_SOURCE_URL,
            retrieved_at=_RETRIEVED_AT,
            source_authority=SourceAuthority.AUTHORITATIVE,
        )
        a1 = ComparableCandidateAssessment.build(target, obs1)
        a_dummy = ComparableCandidateAssessment.build(target, obs_dummy)

        # Build a FOREIGN assessment for obs1 — same target object, same
        # normalized key (both are CANDIDATE for ABC123), AUTHORITATIVE.
        # This is a separate ComparableCandidateAssessment object.
        a_foreign = ComparableCandidateAssessment.build(target, obs1)
        assert a_foreign is not a1
        assert a_foreign.disposition.value == "CANDIDATE"
        assert a_foreign.normalized_part_number == a1.normalized_part_number
        assert a_foreign.target_identity is target

        # ComparableCandidate with both a1 and a_foreign succeeds
        # (same normalized key, same target, both CANDIDATE, both AUTHORITATIVE)
        candidate_abc = ComparableCandidate.build((a1, a_foreign))
        # Second candidate for a_dummy (so a_dummy is not "missing")
        candidate_dummy = ComparableCandidate.build((a_dummy,))

        # Result has a1 + a_dummy in assessments, but candidate_abc contains
        # a_foreign which is NOT in result.assessments. The result's
        # foreign-evidence guard catches it.
        with _pytest.raises(ValueError, match="not from the result assessments"):
            ComparableCandidateDiscoveryResult(
                target_identity=target,
                target_specification_set=spec_set,
                source_outcomes=(outcome,),
                observations=(obs1, obs_dummy),
                assessments=(a1, a_dummy),  # a_foreign is NOT here
                candidates=(candidate_abc, candidate_dummy),
            )


# ---------------------------------------------------------------------------
# REAL E2E
# ---------------------------------------------------------------------------


class TestRealE2E:
    def test_real_seagate_fixture_via_6c(self) -> None:
        """Full pipeline: frozen 6C produces target spec set,
        then 7A discovers candidates from the same fixture.

        This proves the target actually passed through 6C extraction
        and resolution, not a synthetic all-UNKNOWN spec set."""
        from product_intelligence.execution.specification_evidence import (
            SpecificationEvidenceSource,
            research_enterprise_ssd_specifications,
        )

        target = _make_target("XP15360SE70005")
        source = _make_source()

        # Phase 1: Run frozen 6C to get real ProductSpecificationSet
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

        # Prove 6C produced correct target spec set
        spec_set = spec_result.product_specification_set
        assert spec_set.product_identity is target
        assert spec_set.category_schema is ENTERPRISE_SSD_SCHEMA

        # Prove physical_form_factor is VERIFIED with canonical value "2.5-inch"
        ff_resolution = spec_set.resolutions["physical_form_factor"]
        from product_intelligence.research.specifications import ResolutionState
        assert ff_resolution.state is ResolutionState.VERIFIED
        assert ff_resolution.resolved_value is not None
        assert ff_resolution.resolved_value.value == "2.5-inch"

        # Phase 2: Pass the real 6C spec set into 7A
        candidate_fetcher = _FakePageFetcher(body=_read_fixture())

        result = discover_enterprise_ssd_comparable_candidates(
            target_identity=target,
            target_specification_set=spec_set,
            sources=(source,),
            page_fetcher=candidate_fetcher,
        )

        # Source outcome
        assert len(result.source_outcomes) == 1
        assert result.source_outcomes[0].outcome_state is ComparableCandidateSourceOutcomeState.EXTRACTED

        # 81 observations (one per product record)
        assert len(result.observations) == 81

        # 81 assessments (one per observation)
        assert len(result.assessments) == 81

        # 1 TARGET_SELF
        target_self_count = sum(
            1 for a in result.assessments
            if a.disposition.value == "TARGET_SELF"
        )
        assert target_self_count == 1

        # 80 candidates
        assert len(result.candidates) == 80

        # Target absent from candidates
        candidate_mpns = {c.normalized_part_number for c in result.candidates}
        assert "XP15360SE70005" not in candidate_mpns

        # Known siblings present
        assert "XP15360SE70015" in candidate_mpns
        assert "XP3840SE70005" in candidate_mpns

        # Evidence remains AUTHORITATIVE
        for obs in result.observations:
            assert obs.source_authority is SourceAuthority.AUTHORITATIVE

        # Raw MPN preserved exactly
        for obs in result.observations:
            assert obs.manufacturer_part_number_raw.strip() == obs.manufacturer_part_number_raw

        # No score/rank fields
        for candidate in result.candidates:
            for field_name in ("score", "rank", "similarity", "compatibility",
                               "distance", "weight", "threshold"):
                assert not hasattr(candidate, field_name)

        # Zero similarity/ranking behavior
        for candidate in result.candidates:
            assert len(candidate.evidence) >= 1
            for assessment in candidate.evidence:
                assert not hasattr(assessment, "score")
                assert not hasattr(assessment, "similarity")

        # Per-operation fetch count: 6C fetched once, 7A fetched once
        assert spec_fetcher.fetch_count == 1
        assert candidate_fetcher.fetch_count == 1
