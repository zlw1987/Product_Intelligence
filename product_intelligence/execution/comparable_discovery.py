"""Comparable-product candidate discovery (PRODUCT-INTEL.7A — execution layer).

Composes approved-source acquisition, deterministic candidate extraction,
target-self exclusion, identity deduplication, and provenance auditing
into a complete auditable candidate discovery pipeline.

    EXPLICIT APPROVED SOURCE
            ↓
    existing PageFetcher acquisition
            ↓
    fetched document
            ↓
    deterministic raw candidate extraction
            ↓
    ComparableCandidateObservation(s)
            ↓
    target-self exclusion (frozen 2A compare_part_numbers)
            ↓
    ComparableCandidateAssessment(s)
            ↓
    normalized-key deduplication (frozen 2A normalize_part_number)
            ↓
    ComparableCandidate(s)
            ↓
    ComparableCandidateDiscoveryResult (self-auditing)

This module depends on PageFetcher protocol (imported from providers.page),
not HttpPageFetcher concrete implementation.

7A DOES NOT score, rank, or assess similarity. 7B owns that.
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
)
from product_intelligence.research.comparable_candidates import (
    ComparableCandidate,
    ComparableCandidateAssessment,
    ComparableCandidateObservation,
    ComparableCandidateSource,
    CandidateDisposition,
    deduplicate_candidate_assessments,
)
from product_intelligence.research.enterprise_ssd import (
    ENTERPRISE_SSD_SCHEMA,
)
from product_intelligence.research.enterprise_ssd_candidate_extraction import (
    extract_enterprise_ssd_candidate_observations,
)
from product_intelligence.research.specifications import (
    ProductSpecificationSet,
    SourceAuthority,
)


# ---------------------------------------------------------------------------
# Source outcome state
# ---------------------------------------------------------------------------


class ComparableCandidateSourceOutcomeState(str, Enum):
    """Bounded vocabulary for candidate source acquisition outcomes."""

    EXTRACTED = "EXTRACTED"
    NO_OBSERVATIONS = "NO_OBSERVATIONS"
    FETCH_FAILED = "FETCH_FAILED"
    SOURCE_REFUSED = "SOURCE_REFUSED"


# ---------------------------------------------------------------------------
# Source outcome
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class ComparableCandidateSourceOutcome:
    """Auditable outcome for one candidate discovery source.

    Preserves the complete source descriptor and acquisition outcome
    without raw exception text.

    Self-consistency invariants (enforced at construction):

    EXTRACTED:
        final_url present (non-empty string)
        retrieved_at present + timezone-aware datetime
        observation_count > 0

    NO_OBSERVATIONS:
        final_url present (non-empty string)
        retrieved_at present + timezone-aware datetime
        observation_count == 0

    FETCH_FAILED:
        final_url is None
        retrieved_at is None
        observation_count == 0

    SOURCE_REFUSED:
        final_url is None
        retrieved_at is None
        observation_count == 0
    """

    source: ComparableCandidateSource
    final_url: str | None
    retrieved_at: datetime | None
    outcome_state: ComparableCandidateSourceOutcomeState
    observation_count: int

    def __post_init__(self) -> None:
        # Source must be a valid ComparableCandidateSource
        if not isinstance(self.source, ComparableCandidateSource):
            raise TypeError(
                f"source must be a ComparableCandidateSource, got "
                f"{type(self.source).__name__}"
            )

        # final_url — validated through the same URL contract as source_url
        if self.final_url is not None:
            if not isinstance(self.final_url, str) or not self.final_url.strip():
                raise ValueError("final_url must be a non-empty string or None")
            from product_intelligence.providers.page import require_fetchable_url
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
        if not isinstance(self.outcome_state, ComparableCandidateSourceOutcomeState):
            raise TypeError(
                f"outcome_state must be a ComparableCandidateSourceOutcomeState, got "
                f"{type(self.outcome_state).__name__}"
            )

        # observation_count
        if isinstance(self.observation_count, bool) or not isinstance(
            self.observation_count, int
        ):
            raise TypeError(
                f"observation_count must be an int, got "
                f"{type(self.observation_count).__name__}"
            )
        if self.observation_count < 0:
            raise ValueError("observation_count must be a non-negative integer")

        # --- Self-consistency: state-dependent invariants ---
        if self.outcome_state is ComparableCandidateSourceOutcomeState.EXTRACTED:
            if self.final_url is None or not self.final_url.strip():
                raise ValueError(
                    "EXTRACTED outcome requires final_url to be present"
                )
            if self.retrieved_at is None:
                raise ValueError(
                    "EXTRACTED outcome requires retrieved_at to be present"
                )
            if self.observation_count == 0:
                raise ValueError(
                    "EXTRACTED outcome requires observation_count > 0"
                )

        elif self.outcome_state is ComparableCandidateSourceOutcomeState.NO_OBSERVATIONS:
            if self.final_url is None or not self.final_url.strip():
                raise ValueError(
                    "NO_OBSERVATIONS outcome requires final_url to be present"
                )
            if self.retrieved_at is None:
                raise ValueError(
                    "NO_OBSERVATIONS outcome requires retrieved_at to be present"
                )
            if self.observation_count != 0:
                raise ValueError(
                    "NO_OBSERVATIONS outcome requires observation_count == 0"
                )

        elif self.outcome_state is ComparableCandidateSourceOutcomeState.FETCH_FAILED:
            if self.final_url is not None:
                raise ValueError(
                    "FETCH_FAILED outcome requires final_url to be None"
                )
            if self.retrieved_at is not None:
                raise ValueError(
                    "FETCH_FAILED outcome requires retrieved_at to be None"
                )
            if self.observation_count != 0:
                raise ValueError(
                    "FETCH_FAILED outcome requires observation_count == 0"
                )

        elif self.outcome_state is ComparableCandidateSourceOutcomeState.SOURCE_REFUSED:
            if self.final_url is not None:
                raise ValueError(
                    "SOURCE_REFUSED outcome requires final_url to be None"
                )
            if self.retrieved_at is not None:
                raise ValueError(
                    "SOURCE_REFUSED outcome requires retrieved_at to be None"
                )
            if self.observation_count != 0:
                raise ValueError(
                    "SOURCE_REFUSED outcome requires observation_count == 0"
                )


# ---------------------------------------------------------------------------
# Result contract
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class ComparableCandidateDiscoveryResult:
    """Complete candidate discovery result.

    Immutable and self-validating. Contains:
    - The target product identity
    - The target specification set (proves 6A/6B/6C pipeline completed)
    - Source outcomes (fetch/refusal/no-observation states preserved)
    - Raw observations (one per catalog record extracted)
    - Assessments (one per observation, disposition derived from target)
    - Candidates (deduplicated, TARGET_SELF excluded)

    Validates at construction that all components are consistent:
    A. target identity is established
    B. target spec set identity is exact target object, schema is ENTERPRISE_SSD_SCHEMA
    C. sum(EXTRACTED observation_count) == len(observations)
    D. each observation traces to one EXTRACTED source outcome
    E. exactly one assessment exists per observation
    F. assessment disposition can be re-derived from target + observation
    G. TARGET_SELF assessments appear in NO candidate
    H. every CANDIDATE assessment appears in exactly one candidate evidence group
    I. candidate normalized keys are unique
    J. candidate evidence group equals all CANDIDATE assessments/observations
       for that normalized key
    """

    target_identity: ProductIdentity
    target_specification_set: ProductSpecificationSet
    source_outcomes: tuple[ComparableCandidateSourceOutcome, ...]
    observations: tuple[ComparableCandidateObservation, ...]
    assessments: tuple[ComparableCandidateAssessment, ...]
    candidates: tuple[ComparableCandidate, ...]

    def __post_init__(self) -> None:
        # A. Target identity must be established
        if not isinstance(self.target_identity, ProductIdentity):
            raise TypeError(
                f"target_identity must be a ProductIdentity, got "
                f"{type(self.target_identity).__name__}"
            )
        if not self.target_identity.is_established:
            raise ValueError(
                "ComparableCandidateDiscoveryResult requires an established "
                "ProductIdentity"
            )

        # B. Target specification set
        if not isinstance(self.target_specification_set, ProductSpecificationSet):
            raise TypeError(
                f"target_specification_set must be a ProductSpecificationSet, got "
                f"{type(self.target_specification_set).__name__}"
            )
        if (
            self.target_specification_set.product_identity
            is not self.target_identity
        ):
            raise ValueError(
                "target_specification_set identity does not match target_identity"
            )
        if (
            self.target_specification_set.category_schema
            is not ENTERPRISE_SSD_SCHEMA
        ):
            raise ValueError(
                "target_specification_set schema is not ENTERPRISE_SSD_SCHEMA"
            )

        # Source outcomes must be a tuple
        if not isinstance(self.source_outcomes, tuple):
            raise TypeError("source_outcomes must be a tuple")
        for outcome in self.source_outcomes:
            if not isinstance(outcome, ComparableCandidateSourceOutcome):
                raise TypeError(
                    f"source_outcomes must contain only "
                    f"ComparableCandidateSourceOutcome, got "
                    f"{type(outcome).__name__}"
                )

        # Observations must be a tuple
        if not isinstance(self.observations, tuple):
            raise TypeError("observations must be a tuple")
        for obs in self.observations:
            if not isinstance(obs, ComparableCandidateObservation):
                raise TypeError(
                    f"observations must contain only "
                    f"ComparableCandidateObservation, got {type(obs).__name__}"
                )

        # Assessments must be a tuple
        if not isinstance(self.assessments, tuple):
            raise TypeError("assessments must be a tuple")
        for assessment in self.assessments:
            if not isinstance(assessment, ComparableCandidateAssessment):
                raise TypeError(
                    f"assessments must contain only "
                    f"ComparableCandidateAssessment, got {type(assessment).__name__}"
                )

        # Candidates must be a tuple
        if not isinstance(self.candidates, tuple):
            raise TypeError("candidates must be a tuple")
        for candidate in self.candidates:
            if not isinstance(candidate, ComparableCandidate):
                raise TypeError(
                    f"candidates must contain only ComparableCandidate, got "
                    f"{type(candidate).__name__}"
                )

        # C. Observation count consistency
        extracted_count = sum(
            outcome.observation_count
            for outcome in self.source_outcomes
            if outcome.outcome_state
            is ComparableCandidateSourceOutcomeState.EXTRACTED
        )
        if extracted_count != len(self.observations):
            raise ValueError(
                f"Result audit inconsistency: sum(EXTRACTED observation_count) "
                f"={extracted_count} != len(observations) ={len(self.observations)}"
            )

        # D. Each observation traces to one EXTRACTED source outcome
        _validate_observation_provenance(
            self.source_outcomes,
            self.observations,
        )

        # E. Exactly one assessment per observation
        if len(self.assessments) != len(self.observations):
            raise ValueError(
                f"Result audit: len(assessments)={len(self.assessments)} != "
                f"len(observations)={len(self.observations)}. "
                "Each observation must have exactly one assessment."
            )

        # E1. Each assessment is bound to the exact same observation object
        for i, (obs, assessment) in enumerate(zip(self.observations, self.assessments)):
            if assessment.observation is not obs:
                raise ValueError(
                    f"Assessment[{i}] observation is not the same object as "
                    f"the result's observation[{i}. "
                    "Each assessment must reference the exact observation it "
                    "assesses, not a value-equal substitute."
                )
            # assessment target_identity must match result target_identity
            if assessment.target_identity is not self.target_identity:
                raise ValueError(
                    f"Assessment[{i}] target_identity is not the same object as "
                    f"the result's target_identity. "
                    "All assessments must refer to the exact same target."
                )

        # E2. AUTHORITATIVE-only result invariant (7A v1)
        for i, outcome in enumerate(self.source_outcomes):
            if outcome.source.source_authority is not SourceAuthority.AUTHORITATIVE:
                raise ValueError(
                    f"Source outcome[{i}] has authority "
                    f"{outcome.source.source_authority.value}. "
                    "7A v1 result accepts only AUTHORITATIVE sources."
                )
        for i, obs in enumerate(self.observations):
            if obs.source_authority is not SourceAuthority.AUTHORITATIVE:
                raise ValueError(
                    f"Observation[{i}] has authority "
                    f"{obs.source_authority.value}. "
                    "7A v1 result accepts only AUTHORITATIVE evidence."
                )

        # F. Assessment disposition can be re-derived
        _validate_assessment_dispositions(
            self.target_identity,
            self.observations,
            self.assessments,
        )

        # G. TARGET_SELF assessments appear in NO candidate
        target_self_assessments = frozenset(
            id(a) for a in self.assessments
            if a.disposition is CandidateDisposition.TARGET_SELF
        )
        for candidate in self.candidates:
            for assessment in candidate.evidence:
                if id(assessment) in target_self_assessments:
                    raise ValueError(
                        "TARGET_SELF assessment found in candidate evidence. "
                        "TARGET_SELF observations must be excluded from candidates."
                    )

        # H. Every CANDIDATE assessment appears in exactly one candidate evidence
        candidate_assessments_in_result = frozenset(
            id(a) for a in self.assessments
            if a.disposition is CandidateDisposition.CANDIDATE
        )
        seen_in_candidates: set[int] = set()
        for candidate in self.candidates:
            for assessment in candidate.evidence:
                assessment_id = id(assessment)
                if assessment_id in seen_in_candidates:
                    raise ValueError(
                        "Candidate assessment appears in multiple candidates. "
                        "Each assessment must appear in exactly one candidate."
                    )
                seen_in_candidates.add(assessment_id)

        # All CANDIDATE assessments from result must appear in candidates
        missing = candidate_assessments_in_result - seen_in_candidates
        if missing:
            raise ValueError(
                f"{len(missing)} CANDIDATE assessment(s) from the result "
                f"are not present in any candidate evidence. "
                "No hidden dropped evidence is allowed."
            )

        # Extra assessments in candidates that are not in result
        extra = seen_in_candidates - candidate_assessments_in_result
        if extra:
            raise ValueError(
                f"{len(extra)} assessment(s) in candidate evidence are not "
                f"from the result assessments. No foreign evidence allowed."
            )

        # I. Candidate normalized keys are unique
        seen_keys: set[str] = set()
        for candidate in self.candidates:
            if candidate.normalized_part_number in seen_keys:
                raise ValueError(
                    f"Duplicate candidate normalized key: "
                    f"{candidate.normalized_part_number}. "
                    "Candidate keys must be unique."
                )
            seen_keys.add(candidate.normalized_part_number)

        # J. Candidate evidence group equals all CANDIDATE assessments for that key
        # Group result assessments by normalized key
        assessments_by_key: dict[str, list[ComparableCandidateAssessment]] = {}
        for assessment in self.assessments:
            if assessment.disposition is CandidateDisposition.CANDIDATE:
                key = assessment.normalized_part_number
                if key not in assessments_by_key:
                    assessments_by_key[key] = []
                assessments_by_key[key].append(assessment)

        for candidate in self.candidates:
            key = candidate.normalized_part_number
            expected_assessments = assessments_by_key.get(key, [])
            if len(candidate.evidence) != len(expected_assessments):
                raise ValueError(
                    f"Candidate '{key}' evidence count mismatch: "
                    f"expected {len(expected_assessments)}, "
                    f"got {len(candidate.evidence)}"
                )
            # Check identity — evidence must be the exact same objects
            candidate_evidence_ids = frozenset(id(a) for a in candidate.evidence)
            expected_ids = frozenset(id(a) for a in expected_assessments)
            if candidate_evidence_ids != expected_ids:
                raise ValueError(
                    f"Candidate '{key}' evidence does not match the "
                    f"CANDIDATE assessments for that normalized key. "
                    "No hidden dropped evidence is allowed."
                )


def _validate_observation_provenance(
    source_outcomes: tuple[ComparableCandidateSourceOutcome, ...],
    observations: tuple[ComparableCandidateObservation, ...],
) -> None:
    """Validate that each observation traces to an EXTRACTED source outcome.

    Multiplicity-aware matching: each EXTRACTED outcome contributes capacity
    equal to its observation_count. Each observation consumes one unit.
    """
    if not observations:
        return

    # Build a mutable pool of available EXTRACTED outcomes
    available: list[dict] = []
    for outcome in source_outcomes:
        if outcome.outcome_state is ComparableCandidateSourceOutcomeState.EXTRACTED:
            available.append({
                "outcome": outcome,
                "remaining": outcome.observation_count,
            })

    for obs in observations:
        matched = False
        for entry in available:
            outcome = entry["outcome"]
            source = outcome.source

            if source.source_name != obs.source_name:
                continue
            if source.source_authority is not obs.source_authority:
                continue
            if outcome.final_url != obs.source_url:
                continue
            if outcome.retrieved_at != obs.retrieved_at:
                continue
            if entry["remaining"] <= 0:
                continue

            entry["remaining"] -= 1
            matched = True
            break

        if not matched:
            raise ValueError(
                f"Observation from source '{obs.source_name}' "
                f"(url={obs.source_url}, retrieved_at={obs.retrieved_at.isoformat()}) "
                f"does not trace to any EXTRACTED source outcome."
            )


def _validate_assessment_dispositions(
    target_identity: ProductIdentity,
    observations: tuple[ComparableCandidateObservation, ...],
    assessments: tuple[ComparableCandidateAssessment, ...],
) -> None:
    """Validate that each assessment's disposition can be re-derived from
    target_identity + observation using ComparableCandidateAssessment.build().
    """
    for i, (obs, assessment) in enumerate(zip(observations, assessments)):
        # Re-derive using the same frozen 2A logic
        rebuilt = ComparableCandidateAssessment.build(target_identity, obs)
        if rebuilt.disposition != assessment.disposition:
            raise ValueError(
                f"Assessment[{i}] disposition {assessment.disposition.value} "
                f"cannot be re-derived. Expected {rebuilt.disposition.value} "
                f"for observation MPN '{obs.manufacturer_part_number_raw}' "
                f"against target '{target_identity.manufacturer_part_number}'."
            )
        if rebuilt.normalized_part_number != assessment.normalized_part_number:
            raise ValueError(
                f"Assessment[{i}] normalized_part_number "
                f"'{assessment.normalized_part_number}' does not match "
                f"re-derived '{rebuilt.normalized_part_number}'."
            )


# ---------------------------------------------------------------------------
# Public execution operation
# ---------------------------------------------------------------------------


def discover_enterprise_ssd_comparable_candidates(
    *,
    target_identity: ProductIdentity,
    target_specification_set: ProductSpecificationSet,
    sources: tuple[ComparableCandidateSource, ...],
    page_fetcher: PageFetcher,
) -> ComparableCandidateDiscoveryResult:
    """Discover comparable-product candidates from approved sources.

    Public entry point for 7A candidate discovery pipeline.

    Pipeline:
    1. Validate target identity, specification set, and all sources
    2. For each source:
       a. Acquire via PageFetcher
       b. Extract raw ComparableCandidateObservations
    3. Build ComparableCandidateAssessment for each observation
    4. Deduplicate CANDIDATE assessments into ComparableCandidate objects
    5. Return self-validating ComparableCandidateDiscoveryResult

    This operation discovers candidates — it does NOT score, rank, or
    assess similarity. Those are 7B+.

    Parameters
    ----------
    target_identity : ProductIdentity
        Established target product identity.
    target_specification_set : ProductSpecificationSet
        Complete specification set for the target (proves 6A/6B/6C done).
    sources : tuple[ComparableCandidateSource, ...]
        Explicitly approved candidate sources.
    page_fetcher : PageFetcher
        Page acquisition protocol.

    Returns
    -------
    ComparableCandidateDiscoveryResult
        Complete auditable candidate discovery result.

    Raises
    ------
    ValueError
        If target identity is not established, spec set doesn't match,
        or a source is misconfigured (SECONDARY authority, invalid URL).
    TypeError
        If target_identity is not a ProductIdentity.
    """
    # Validate target identity
    if not isinstance(target_identity, ProductIdentity):
        raise TypeError(
            f"target_identity must be a ProductIdentity, got "
            f"{type(target_identity).__name__}"
        )
    if not target_identity.is_established:
        raise ValueError(
            "discover_enterprise_ssd_comparable_candidates requires an "
            f"established ProductIdentity (match_type={target_identity.match_type.value})"
        )

    # Validate target specification set
    if not isinstance(target_specification_set, ProductSpecificationSet):
        raise TypeError(
            f"target_specification_set must be a ProductSpecificationSet, got "
            f"{type(target_specification_set).__name__}"
        )
    if (
        target_specification_set.product_identity is not target_identity
    ):
        raise ValueError(
            "target_specification_set identity does not match target_identity. "
            "The specification set must be for the exact same target product."
        )
    if (
        target_specification_set.category_schema is not ENTERPRISE_SSD_SCHEMA
    ):
        raise ValueError(
            f"target_specification_set schema is "
            f"{target_specification_set.category_schema.schema_id}, "
            "but ENTERPRISE_SSD_SCHEMA is required for enterprise SSD candidate "
            "discovery."
        )

    # Validate sources: AUTHORITATIVE required in v1
    if not isinstance(sources, tuple):
        raise TypeError("sources must be a tuple")
    for source in sources:
        if not isinstance(source, ComparableCandidateSource):
            raise TypeError(
                f"sources must contain only ComparableCandidateSource, got "
                f"{type(source).__name__}"
            )
        if source.source_authority is not SourceAuthority.AUTHORITATIVE:
            raise ValueError(
                f"Source '{source.source_name}' has authority "
                f"{source.source_authority.value}. 7A v1 requires "
                "AUTHORITATIVE sources. SECONDARY sources are not accepted."
            )

    # Process each source — collect outcomes and observations
    source_outcomes: list[ComparableCandidateSourceOutcome] = []
    all_observations: list[ComparableCandidateObservation] = []

    for source in sources:
        outcome, observations = _process_source(
            source, page_fetcher
        )
        source_outcomes.append(outcome)
        all_observations.extend(observations)

    # Build assessments for each observation
    assessments: list[ComparableCandidateAssessment] = []
    for obs in all_observations:
        assessment = ComparableCandidateAssessment.build(
            target_identity, obs
        )
        assessments.append(assessment)

    # Deduplicate into candidates (TARGET_SELF excluded)
    candidates = deduplicate_candidate_assessments(tuple(assessments))

    # Build self-validating result
    return ComparableCandidateDiscoveryResult(
        target_identity=target_identity,
        target_specification_set=target_specification_set,
        source_outcomes=tuple(source_outcomes),
        observations=tuple(all_observations),
        assessments=tuple(assessments),
        candidates=candidates,
    )


def _process_source(
    source: ComparableCandidateSource,
    page_fetcher: PageFetcher,
) -> tuple[ComparableCandidateSourceOutcome, list[ComparableCandidateObservation]]:
    """Process one source: fetch, extract candidates, return outcome + observations.

    URL validation occurs at ComparableCandidateSource construction.
    """
    fetch_request = PageFetchRequest(url=source.source_url)

    # Attempt fetch
    try:
        fetched_page = page_fetcher.fetch(fetch_request)
    except UnsafeFetchTargetError:
        return (
            ComparableCandidateSourceOutcome(
                source=source,
                final_url=None,
                retrieved_at=None,
                outcome_state=ComparableCandidateSourceOutcomeState.SOURCE_REFUSED,
                observation_count=0,
            ),
            [],
        )
    except PageFetchError:
        return (
            ComparableCandidateSourceOutcome(
                source=source,
                final_url=None,
                retrieved_at=None,
                outcome_state=ComparableCandidateSourceOutcomeState.FETCH_FAILED,
                observation_count=0,
            ),
            [],
        )

    # Extract candidate observations
    try:
        observations = list(
            extract_enterprise_ssd_candidate_observations(
                document=fetched_page.body_text,
                source_name=source.source_name,
                source_url=fetched_page.final_url,
                retrieved_at=fetched_page.retrieved_at,
                source_authority=source.source_authority,
            )
        )
    except Exception:
        # Programming exception in extraction — propagate
        raise

    # Determine outcome state
    if observations:
        outcome_state = ComparableCandidateSourceOutcomeState.EXTRACTED
    else:
        outcome_state = ComparableCandidateSourceOutcomeState.NO_OBSERVATIONS

    return (
        ComparableCandidateSourceOutcome(
            source=source,
            final_url=fetched_page.final_url,
            retrieved_at=fetched_page.retrieved_at,
            outcome_state=outcome_state,
            observation_count=len(observations),
        ),
        observations,
    )
