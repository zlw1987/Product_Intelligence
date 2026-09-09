"""Enterprise SSD candidate similarity scoring execution (PRODUCT-INTEL.7B).

Composes candidate specification research and deterministic similarity scoring
into an auditable batch pipeline:

    frozen 7A ComparableCandidateDiscoveryResult
            ↓
    establish candidate ProductIdentity (7B bridge)
            ↓
    fetch each EXTRACTED source ONCE
            ↓
    call frozen 6C extraction per candidate identity
            ↓
    frozen 6B normalization
            ↓
    frozen 6A resolve_specification()
            ↓
    ComparableCandidateSpecificationProfile
            ↓
    7B pure similarity scoring
            ↓
    EnterpriseSsdSimilarityResult

This module depends on PageFetcher protocol (imported from providers.page),
not HttpPageFetcher concrete implementation.

7B execution does NOT rediscover candidates. Inputs come from frozen 7A.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import Enum

from product_intelligence.domain.models import ProductIdentity
from product_intelligence.providers.page import (
    FetchedPage,
    PageFetchError,
    PageFetchRequest,
    PageFetcher,
    UnsafeFetchTargetError,
    require_fetchable_url,
)
from product_intelligence.execution.comparable_discovery import (
    ComparableCandidateDiscoveryResult,
    ComparableCandidateSourceOutcome as DiscoverySourceOutcome,
    ComparableCandidateSourceOutcomeState as DiscoverySourceOutcomeState,
)
from product_intelligence.research.comparable_candidates import (
    ComparableCandidate,
    ComparableCandidateSource,
)
from product_intelligence.research.enterprise_ssd import (
    ENTERPRISE_SSD_SCHEMA,
    normalize_enterprise_ssd_observation,
)
from product_intelligence.research.enterprise_ssd_extraction import (
    extract_enterprise_ssd_specification_observations,
)
from product_intelligence.research.enterprise_ssd_similarity import (
    ComparableCandidateSpecificationProfile,
    EnterpriseSsdCandidateSimilarity,
    establish_candidate_product_identity,
    score_enterprise_ssd_candidate_similarity,
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
# 7B Source outcome
# ---------------------------------------------------------------------------


class ComparableSimilaritySourceOutcomeState(str, Enum):
    """Bounded vocabulary for 7B source acquisition outcomes.

    FETCHED — page was fetched and document is available for extraction.
    FETCH_FAILED — page fetch failed (PageFetchError).
    SOURCE_REFUSED — page fetch was refused (UnsafeFetchTargetError).
    """

    FETCHED = "FETCHED"
    FETCH_FAILED = "FETCH_FAILED"
    SOURCE_REFUSED = "SOURCE_REFUSED"


@dataclass(frozen=True)
class ComparableSimilaritySourceOutcome:
    """Auditable outcome for one source used in 7B candidate spec research.

    Preserves complete source descriptor (exact 7A object) and acquisition
    outcome.

    Self-consistency:
        FETCHED: final_url present + structurally validated, retrieved_at
            present + timezone-aware
        FETCH_FAILED: final_url None, retrieved_at None
        SOURCE_REFUSED: final_url None, retrieved_at None
    """

    source: ComparableCandidateSource
    final_url: str | None
    retrieved_at: datetime | None
    outcome_state: ComparableSimilaritySourceOutcomeState

    def __post_init__(self) -> None:
        # source — exact frozen 7A source descriptor (no substitutes)
        if type(self.source) is not ComparableCandidateSource:
            raise TypeError(
                f"source must be a ComparableCandidateSource, got "
                f"{type(self.source).__name__}"
            )

        # source_authority must be AUTHORITATIVE (7A v1 invariant, enforced
        # at 7A construction and re-checked here)
        if self.source.source_authority is not SourceAuthority.AUTHORITATIVE:
            raise ValueError(
                f"7B source must be AUTHORITATIVE, got "
                f"{self.source.source_authority.value}. "
                "Only AUTHORITATIVE sources from 7A may proceed to 7B."
            )

        # final_url — structurally validated by require_fetchable_url
        if self.final_url is not None:
            require_fetchable_url(self.final_url, "final_url")

        # retrieved_at
        if self.retrieved_at is not None:
            if not isinstance(self.retrieved_at, datetime):
                raise TypeError(
                    f"retrieved_at must be a datetime or None, got "
                    f"{type(self.retrieved_at).__name__}"
                )
            if (
                self.retrieved_at.tzinfo is None
                or self.retrieved_at.utcoffset() is None
            ):
                raise ValueError("retrieved_at must be timezone-aware")

        # outcome_state
        if not isinstance(self.outcome_state, ComparableSimilaritySourceOutcomeState):
            raise TypeError(
                f"outcome_state must be a ComparableSimilaritySourceOutcomeState, got "
                f"{type(self.outcome_state).__name__}"
            )

        # Self-consistency: state-dependent invariants
        if self.outcome_state is ComparableSimilaritySourceOutcomeState.FETCHED:
            if self.final_url is None:
                raise ValueError(
                    "FETCHED outcome requires final_url to be present"
                )
            if self.retrieved_at is None:
                raise ValueError(
                    "FETCHED outcome requires retrieved_at to be present"
                )
        elif self.outcome_state in (
            ComparableSimilaritySourceOutcomeState.FETCH_FAILED,
            ComparableSimilaritySourceOutcomeState.SOURCE_REFUSED,
        ):
            if self.final_url is not None:
                raise ValueError(
                    f"{self.outcome_state.value} outcome requires "
                    "final_url to be None"
                )
            if self.retrieved_at is not None:
                raise ValueError(
                    f"{self.outcome_state.value} outcome requires "
                    "retrieved_at to be None"
                )


# ---------------------------------------------------------------------------
# EnterpriseSsdSimilarityResult (execution-owned)
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class EnterpriseSsdSimilarityResult:
    """Complete 7B similarity result.

    Immutable and self-validating. Contains:
    - The frozen 7A discovery result
    - 7B source outcomes (one per unique EXTRACTED source)
    - Candidate specification profiles (one per candidate)
    - Candidate similarities (one per candidate)

    Validates at construction:
    A. discovery_result is EXACTLY a ComparableCandidateDiscoveryResult
    B. source_outcomes is a tuple of ComparableSimilaritySourceOutcome
    C. candidate_profiles is a tuple of ComparableCandidateSpecificationProfile
    D. similarities is a tuple of EnterpriseSsdCandidateSimilarity
    E. profile count == candidate count from discovery result
    F. similarity count == profile count == candidate count
    G. profiles match discovery result candidate order (exact object identity)
    H. each similarity.candidate_profile is the matching profile object
    I. each similarity.target_specification_set is discovery_result's target
    J. candidate spec evidence is traced to FETCHED 7B source outcomes
    """

    discovery_result: ComparableCandidateDiscoveryResult
    source_outcomes: tuple[ComparableSimilaritySourceOutcome, ...]
    candidate_profiles: tuple[ComparableCandidateSpecificationProfile, ...]
    similarities: tuple[EnterpriseSsdCandidateSimilarity, ...]

    def __post_init__(self) -> None:
        # A. discovery_result — EXACT type (no duck typing, no subclasses)
        if type(self.discovery_result) is not ComparableCandidateDiscoveryResult:
            raise TypeError(
                f"discovery_result must be a ComparableCandidateDiscoveryResult, got "
                f"{type(self.discovery_result).__name__}"
            )

        # B. source_outcomes — exact types
        if not isinstance(self.source_outcomes, tuple):
            raise TypeError(
                f"source_outcomes must be a tuple, got "
                f"{type(self.source_outcomes).__name__}"
            )
        for i, outcome in enumerate(self.source_outcomes):
            if not isinstance(outcome, ComparableSimilaritySourceOutcome):
                raise TypeError(
                    f"source_outcomes[{i}] must be a "
                    f"ComparableSimilaritySourceOutcome, got "
                    f"{type(outcome).__name__}"
                )

        # C. candidate_profiles — exact types
        if not isinstance(self.candidate_profiles, tuple):
            raise TypeError(
                f"candidate_profiles must be a tuple, got "
                f"{type(self.candidate_profiles).__name__}"
            )
        for i, profile in enumerate(self.candidate_profiles):
            if not isinstance(profile, ComparableCandidateSpecificationProfile):
                raise TypeError(
                    f"candidate_profiles[{i}] must be a "
                    f"ComparableCandidateSpecificationProfile, got "
                    f"{type(profile).__name__}"
                )

        # D. similarities — exact types
        if not isinstance(self.similarities, tuple):
            raise TypeError(
                f"similarities must be a tuple, got "
                f"{type(self.similarities).__name__}"
            )
        for i, sim in enumerate(self.similarities):
            if not isinstance(sim, EnterpriseSsdCandidateSimilarity):
                raise TypeError(
                    f"similarities[{i}] must be an "
                    f"EnterpriseSsdCandidateSimilarity, got "
                    f"{type(sim).__name__}"
                )

        # E. Counts must match candidate count
        candidate_count = len(self.discovery_result.candidates)
        if len(self.candidate_profiles) != candidate_count:
            raise ValueError(
                f"candidate_profiles has {len(self.candidate_profiles)} items "
                f"but discovery result has {candidate_count} candidates. "
                "Every candidate must have exactly one profile."
            )
        if len(self.similarities) != candidate_count:
            raise ValueError(
                f"similarities has {len(self.similarities)} items "
                f"but discovery result has {candidate_count} candidates. "
                "Every candidate must have exactly one similarity."
            )

        # G. Profiles must match discovery result candidate order
        for i, profile in enumerate(self.candidate_profiles):
            expected_candidate = self.discovery_result.candidates[i]
            if profile.candidate is not expected_candidate:
                raise ValueError(
                    f"candidate_profiles[{i}] is for candidate "
                    f"'{profile.candidate.normalized_part_number}' but position "
                    f"{i} expects '{expected_candidate.normalized_part_number}'. "
                    "Profile order must match discovery candidate order."
                )

        # H. Each similarity.candidate_profile must be the matching profile
        for i, sim in enumerate(self.similarities):
            if sim.candidate_profile is not self.candidate_profiles[i]:
                raise ValueError(
                    f"similarities[{i}].candidate_profile is not the same "
                    f"object as candidate_profiles[{i}]. Each similarity must "
                    "reference its own profile object."
                )

        # I. Each similarity.target_specification_set must be discovery target
        for i, sim in enumerate(self.similarities):
            if (
                sim.target_specification_set
                is not self.discovery_result.target_specification_set
            ):
                raise ValueError(
                    f"similarities[{i}].target_specification_set is not the "
                    "same object as discovery_result.target_specification_set. "
                    "All similarities must target the discovery spec set."
                )

        # K. Source binding: every 7B source outcome must reuse the exact
        #    source descriptor object from a frozen 7A EXTRACTED outcome.
        #    Deduplication semantics match the public 7B operation:
        #    ComparableCandidateSource value equality, first-seen wins.
        extracted_7a_outcomes = [
            o for o in self.discovery_result.source_outcomes
            if o.outcome_state is DiscoverySourceOutcomeState.EXTRACTED
        ]

        # Build canonical source list (exact dedup semantics from pipeline):
        # ComparableCandidateSource value equality, first-seen wins.
        canonical_sources: list[ComparableCandidateSource] = []
        seen_sources: set[ComparableCandidateSource] = set()
        for outcome in extracted_7a_outcomes:
            source = outcome.source
            if source not in seen_sources:
                seen_sources.add(source)
                canonical_sources.append(source)

        # Counts must match: one 7B outcome per unique 7A EXTRACTED source
        if len(self.source_outcomes) != len(canonical_sources):
            raise ValueError(
                f"source_outcomes has {len(self.source_outcomes)} items but "
                f"discovery result has {len(canonical_sources)} unique EXTRACTED "
                "source descriptors. Every unique 7A source must have exactly "
                "one corresponding 7B outcome."
            )

        # Object identity: each 7B outcome.source must be the exact 7A object
        for i, outcome in enumerate(self.source_outcomes):
            expected_source = canonical_sources[i]
            if outcome.source is not expected_source:
                raise ValueError(
                    f"source_outcomes[{i}].source is not the same object as "
                    f"the canonical 7A EXTRACTED source at position {i}. "
                    "7B source outcomes must reuse the exact frozen 7A source "
                    "descriptor object (object identity), not a value-equal copy."
                )

        # J. Candidate spec evidence provenance audit
        # Build lookup of FETCHED outcomes by source
        fetched_outcomes = [
            o for o in self.source_outcomes
            if o.outcome_state is ComparableSimilaritySourceOutcomeState.FETCHED
        ]

        for profile in self.candidate_profiles:
            for resolution in profile.specification_set.resolutions.values():
                for evidence in resolution.evidence:
                    obs = evidence.observation

                    # Evidence must bind to this profile's candidate identity
                    if obs.product_identity is not profile.candidate_identity:
                        raise ValueError(
                            f"Evidence for '{resolution.definition.key}' in "
                            f"candidate '{profile.candidate.normalized_part_number}' "
                            f"has product_identity "
                            f"'{obs.product_identity.manufacturer_part_number}' "
                            f"but profile identity is "
                            f"'{profile.candidate_identity.manufacturer_part_number}'. "
                            "Evidence must bind to the candidate it belongs to."
                        )

                    # Evidence must trace to a FETCHED 7B source outcome
                    matched = False
                    for outcome in fetched_outcomes:
                        if (
                            obs.source_name == outcome.source.source_name
                            and obs.source_authority is outcome.source.source_authority
                            and obs.source_url == outcome.final_url
                            and obs.retrieved_at == outcome.retrieved_at
                        ):
                            matched = True
                            break

                    if not matched:
                        raise ValueError(
                            f"Evidence for '{resolution.definition.key}' in "
                            f"candidate '{profile.candidate.normalized_part_number}' "
                            f"from source '{obs.source_name}' "
                            f"(url={obs.source_url}, "
                            f"retrieved_at={obs.retrieved_at.isoformat()}) "
                            f"does not trace to any FETCHED 7B source outcome. "
                            "All specification evidence must come from successfully "
                            "fetched 7B sources."
                        )


# ---------------------------------------------------------------------------
# Public execution operation
# ---------------------------------------------------------------------------


def research_and_score_enterprise_ssd_candidates(
    *,
    discovery_result: ComparableCandidateDiscoveryResult,
    page_fetcher: PageFetcher,
) -> EnterpriseSsdSimilarityResult:
    """Research specifications and compute similarity for all candidates.

    Full 7B pipeline:
    1. Validate discovery result from frozen 7A (EXACT type, BEFORE FETCH)
    2. Identify EXTRACTED source outcomes (actual evidence sources)
    3. Fetch each unique EXTRACTED source exactly ONCE
    4. For each candidate:
       a. Establish candidate ProductIdentity via 7B bridge
       b. Extract spec observations from each fetched document
       c. Normalize via frozen 6B
       d. Resolve via frozen 6A
       e. Build ComparableCandidateSpecificationProfile
    5. Score each candidate against target via pure 7B scoring
    6. Return self-validating EnterpriseSsdSimilarityResult

    Does NOT rediscover candidates — inputs come from frozen 7A.
    Uses only source descriptors already present in discovery_result.
    Does NOT use SearchProvider.

    Parameters
    ----------
    discovery_result : ComparableCandidateDiscoveryResult
        Frozen 7A discovery result (target identity, spec set, candidates).
    page_fetcher : PageFetcher
        Page acquisition protocol.

    Returns
    -------
    EnterpriseSsdSimilarityResult
        Complete auditable similarity result.

    Raises
    ------
    TypeError
        If discovery_result is not a ComparableCandidateDiscoveryResult
        (checked BEFORE any fetch).
    ValueError
        If discovery result is invalid or inconsistent.
    """
    # --- EXACT type check BEFORE any fetch ---
    if type(discovery_result) is not ComparableCandidateDiscoveryResult:
        raise TypeError(
            f"discovery_result must be a ComparableCandidateDiscoveryResult, got "
            f"{type(discovery_result).__name__}"
        )

    target_identity = discovery_result.target_identity
    target_specification_set = discovery_result.target_specification_set
    candidates = discovery_result.candidates
    source_outcomes_7a = discovery_result.source_outcomes

    # Validate target identity
    if not isinstance(target_identity, ProductIdentity):
        raise TypeError(
            f"target_identity must be a ProductIdentity, got "
            f"{type(target_identity).__name__}"
        )
    if not target_identity.is_established:
        raise ValueError(
            "research_and_score_enterprise_ssd_candidates requires an "
            f"established target ProductIdentity "
            f"(match_type={target_identity.match_type.value})"
        )

    # Validate target spec set
    if (
        target_specification_set.product_identity is not target_identity
    ):
        raise ValueError(
            "target_specification_set identity does not match "
            "discovery_result target_identity"
        )

    # Validate page_fetcher has fetch method (structural check —
    # PageFetcher is a Protocol, not @runtime_checkable)
    if not hasattr(page_fetcher, "fetch"):
        raise TypeError(
            f"page_fetcher must implement PageFetcher protocol (has fetch()), got "
            f"{type(page_fetcher).__name__}"
        )

    # ------------------------------------------------------------------
    # Step 1: Identify EXTRACTED sources from discovery result
    # These are the sources that actually produced candidate evidence.
    # ------------------------------------------------------------------

    extracted_7a_outcomes = [
        outcome
        for outcome in source_outcomes_7a
        if outcome.outcome_state is DiscoverySourceOutcomeState.EXTRACTED
    ]

    # Deduplicate by exact source descriptor to avoid duplicate fetches.
    # One unique source fetch per source descriptor; the fetched document
    # is reused in memory for all candidates.
    seen_sources: dict[ComparableCandidateSource, DiscoverySourceOutcome] = {}
    for outcome in extracted_7a_outcomes:
        source = outcome.source
        if source not in seen_sources:
            seen_sources[source] = outcome

    # ------------------------------------------------------------------
    # Step 2: Fetch each unique EXTRACTED source exactly ONCE
    # Build 7B source outcome records and fetched document list.
    # ------------------------------------------------------------------

    # Maps source -> (body_text, final_url, retrieved_at)
    fetched_documents: dict[ComparableCandidateSource, tuple[str, str, datetime]] = {}
    source_outcome_records: list[ComparableSimilaritySourceOutcome] = []

    for source in seen_sources:
        # URL already validated at 7A ComparableCandidateSource construction

        try:
            fetch_request = PageFetchRequest(url=source.source_url)
            fetched_page = page_fetcher.fetch(fetch_request)
        except UnsafeFetchTargetError:
            source_outcome_records.append(
                ComparableSimilaritySourceOutcome(
                    source=source,
                    final_url=None,
                    retrieved_at=None,
                    outcome_state=ComparableSimilaritySourceOutcomeState.SOURCE_REFUSED,
                )
            )
            continue
        except PageFetchError:
            source_outcome_records.append(
                ComparableSimilaritySourceOutcome(
                    source=source,
                    final_url=None,
                    retrieved_at=None,
                    outcome_state=ComparableSimilaritySourceOutcomeState.FETCH_FAILED,
                )
            )
            continue

        fetched_documents[source] = (
            fetched_page.body_text,
            fetched_page.final_url,
            fetched_page.retrieved_at,
        )

        source_outcome_records.append(
            ComparableSimilaritySourceOutcome(
                source=source,
                final_url=fetched_page.final_url,
                retrieved_at=fetched_page.retrieved_at,
                outcome_state=ComparableSimilaritySourceOutcomeState.FETCHED,
            )
        )

    # ------------------------------------------------------------------
    # Step 3: For each candidate, research specifications and build profile
    # ------------------------------------------------------------------

    candidate_profiles: list[ComparableCandidateSpecificationProfile] = []

    for candidate in candidates:
        # a. Establish candidate ProductIdentity via 7B bridge
        candidate_identity = establish_candidate_product_identity(candidate)

        # b. Extract spec observations from each fetched document
        #    (reuse fetched documents, do NOT refetch per candidate)
        all_observations = []
        for source in fetched_documents:
            body_text, final_url, retrieved_at = fetched_documents[source]
            observations = extract_enterprise_ssd_specification_observations(
                product_identity=candidate_identity,
                document=body_text,
                source_name=source.source_name,
                source_url=source.source_url,
                final_url=final_url,
                retrieved_at=retrieved_at,
                source_authority=source.source_authority,
            )
            all_observations.extend(observations)

        # c. Normalize via frozen 6B
        normalized_observations: list[NormalizedSpecificationObservation] = []
        for obs in all_observations:
            normalized = normalize_enterprise_ssd_observation(obs)
            normalized_observations.append(normalized)

        # d. Group by definition and resolve via frozen 6A
        observations_by_definition: dict[str, list[NormalizedSpecificationObservation]] = {
            key: [] for key in ENTERPRISE_SSD_SCHEMA.definitions
        }
        for norm_obs in normalized_observations:
            key = norm_obs.observation.definition.key
            if key in observations_by_definition:
                observations_by_definition[key].append(norm_obs)

        resolutions: dict[str, SpecificationResolution] = {}
        for key, definition in ENTERPRISE_SSD_SCHEMA.definitions.items():
            obs_tuple = tuple(observations_by_definition[key])
            resolution = resolve_specification(
                candidate_identity, definition, obs_tuple
            )
            resolutions[key] = resolution

        # e. Build complete ProductSpecificationSet
        candidate_spec_set = ProductSpecificationSet(
            product_identity=candidate_identity,
            category_schema=ENTERPRISE_SSD_SCHEMA,
            resolutions=resolutions,
        )

        # f. Build ComparableCandidateSpecificationProfile
        profile = ComparableCandidateSpecificationProfile(
            candidate=candidate,
            candidate_identity=candidate_identity,
            specification_set=candidate_spec_set,
        )
        candidate_profiles.append(profile)

    # ------------------------------------------------------------------
    # Step 4: Score each candidate against target via pure 7B scoring
    # ------------------------------------------------------------------

    similarities: list[EnterpriseSsdCandidateSimilarity] = []

    for profile in candidate_profiles:
        similarity = score_enterprise_ssd_candidate_similarity(
            target_specification_set=target_specification_set,
            candidate_profile=profile,
        )
        similarities.append(similarity)

    # ------------------------------------------------------------------
    # Step 5: Build self-validating result with retained source outcomes
    # ------------------------------------------------------------------

    return EnterpriseSsdSimilarityResult(
        discovery_result=discovery_result,
        source_outcomes=tuple(source_outcome_records),
        candidate_profiles=tuple(candidate_profiles),
        similarities=tuple(similarities),
    )
