"""Specification evidence extraction and resolution (PRODUCT-INTEL.6C — execution layer).

Composes approved-source acquisition, deterministic extraction, 6B normalization,
and 6A resolution into a complete auditable specification research pipeline.

    EXPLICIT APPROVED SOURCE
            ↓
    existing PageFetcher acquisition
            ↓
    fetched document
            ↓
    deterministic raw specification extraction
            ↓
    SpecificationObservation(s)
            ↓
    frozen 6B normalization
            ↓
    NormalizedSpecificationObservation(s)
            ↓
    frozen 6A resolve_specification()
            ↓
    complete ProductSpecificationSet

This module depends on PageFetcher protocol (imported from providers.page),
not HttpPageFetcher concrete implementation. Research extractor does NOT
import providers.
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
from product_intelligence.research.enterprise_ssd import (
    ENTERPRISE_SSD_SCHEMA,
    normalize_enterprise_ssd_observation,
)
from product_intelligence.research.enterprise_ssd_extraction import (
    extract_enterprise_ssd_specification_observations,
)
from product_intelligence.research.specifications import (
    NormalizedSpecificationObservation,
    ProductSpecificationSet,
    ResolutionState,
    SourceAuthority,
    SpecificationDefinition,
    SpecificationObservation,
    SpecificationResolution,
    resolve_specification,
)


# ---------------------------------------------------------------------------
# Source descriptor
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class SpecificationEvidenceSource:
    """One explicitly approved specification evidence source.

    The source descriptor names one approved URL that is explicitly about
    one established ProductIdentity. Authority is supplied explicitly,
    never inferred from hostname or URL.

    The source_url is validated at construction through the same
    ``require_fetchable_url`` contract used by ``PageFetchRequest``.
    An invalid URL raises ``TypeError``/``ValueError`` immediately —
    it does NOT slip through to become ``SOURCE_REFUSED`` at fetch time.

    Attributes
    ----------
    product_identity : ProductIdentity
        Must be established. Every source must match the target identity.
    source_name : str
        Human-readable source name (e.g. "Samsung Business").
    source_url : str
        The URL to fetch. Must be absolute http(s), no credentials.
    source_authority : SourceAuthority
        Explicitly supplied authority tier. Never inferred.
    """

    product_identity: ProductIdentity
    source_name: str
    source_url: str
    source_authority: SourceAuthority

    def __post_init__(self) -> None:
        # Product identity must be established
        if not isinstance(self.product_identity, ProductIdentity):
            raise TypeError(
                f"product_identity must be a ProductIdentity, got "
                f"{type(self.product_identity).__name__}"
            )
        if not self.product_identity.is_established:
            raise ValueError(
                "SpecificationEvidenceSource requires an established ProductIdentity; "
                f"got match_type={self.product_identity.match_type.value}"
            )

        # Source name
        if not isinstance(self.source_name, str) or not self.source_name.strip():
            raise ValueError("source_name must be a non-empty string")
        object.__setattr__(self, "source_name", self.source_name.strip())

        # Source URL — validated through the same contract as PageFetchRequest.
        # Invalid URLs are rejected at construction, not deferred to fetch time.
        object.__setattr__(
            self, "source_url", require_fetchable_url(self.source_url, "source_url")
        )

        # Source authority must be exact type
        if not isinstance(self.source_authority, SourceAuthority):
            raise TypeError(
                f"source_authority must be a SourceAuthority, got "
                f"{type(self.source_authority).__name__}"
            )


# ---------------------------------------------------------------------------
# Source outcome
# ---------------------------------------------------------------------------


class SourceOutcomeState(str, Enum):
    """Bounded vocabulary for source acquisition outcomes."""

    EXTRACTED = "EXTRACTED"
    NO_OBSERVATIONS = "NO_OBSERVATIONS"
    FETCH_FAILED = "FETCH_FAILED"
    SOURCE_REFUSED = "SOURCE_REFUSED"


@dataclass(frozen=True)
class SpecificationSourceOutcome:
    """Auditable outcome for one specification evidence source.

    Preserves the complete source descriptor and acquisition outcome
    without raw exception text.

    The requested URL is always ``source.source_url`` — there is no
    separate ``requested_url`` field.

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

    Attributes
    ----------
    source : SpecificationEvidenceSource
        The complete source descriptor (identity, name, url, authority).
    final_url : str | None
        The actual URL evidence came from (after redirects). None if fetch failed.
    retrieved_at : datetime | None
        Retrieval timestamp from FetchedPage. None if fetch failed.
    outcome_state : SourceOutcomeState
        The acquisition outcome.
    observation_count : int
        Number of raw observations extracted (0 if fetch failed or no extraction).
    """

    source: SpecificationEvidenceSource
    final_url: str | None
    retrieved_at: datetime | None
    outcome_state: SourceOutcomeState
    observation_count: int

    def __post_init__(self) -> None:
        # Source must be a valid SpecificationEvidenceSource
        if not isinstance(self.source, SpecificationEvidenceSource):
            raise TypeError(
                f"source must be a SpecificationEvidenceSource, got "
                f"{type(self.source).__name__}"
            )

        # final_url — validated through the same URL contract as source_url
        if self.final_url is not None:
            if not isinstance(self.final_url, str) or not self.final_url.strip():
                raise ValueError("final_url must be a non-empty string or None")
            # Validate final_url uses the same structural contract as source_url
            # (absolute http(s), no credentials, valid host)
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
        if not isinstance(self.outcome_state, SourceOutcomeState):
            raise TypeError(
                f"outcome_state must be a SourceOutcomeState, got "
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
        if self.outcome_state is SourceOutcomeState.EXTRACTED:
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

        elif self.outcome_state is SourceOutcomeState.NO_OBSERVATIONS:
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

        elif self.outcome_state is SourceOutcomeState.FETCH_FAILED:
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

        elif self.outcome_state is SourceOutcomeState.SOURCE_REFUSED:
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
class SpecificationEvidenceResult:
    """Complete specification evidence research result.

    Immutable and self-validating. Contains:
    - The target product identity
    - Source outcomes (fetch/refusal/no-observation states preserved)
    - Normalized observations (after 6B normalization)
    - Complete ProductSpecificationSet (after 6A resolution)

    Validates at construction that all components are consistent, including:
    - sum(EXTRACTED observation_count) == len(normalized_observations)
    - Every normalized observation traces to an EXTRACTED source outcome
      matching product_identity, source_name, source_authority, final_url,
      retrieved_at (multiplicity-aware)
    - ProductSpecificationSet resolutions use exactly the normalized
      observations for each definition (no missing, foreign, or substituted)
    """

    product_identity: ProductIdentity
    source_outcomes: tuple[SpecificationSourceOutcome, ...]
    normalized_observations: tuple[NormalizedSpecificationObservation, ...]
    product_specification_set: ProductSpecificationSet

    def __post_init__(self) -> None:
        # Identity must be established
        if not isinstance(self.product_identity, ProductIdentity):
            raise TypeError(
                f"product_identity must be a ProductIdentity, got "
                f"{type(self.product_identity).__name__}"
            )
        if not self.product_identity.is_established:
            raise ValueError(
                "SpecificationEvidenceResult requires an established ProductIdentity"
            )

        # Source outcomes must be a tuple
        if not isinstance(self.source_outcomes, tuple):
            raise TypeError("source_outcomes must be a tuple")
        for outcome in self.source_outcomes:
            if not isinstance(outcome, SpecificationSourceOutcome):
                raise TypeError(
                    f"source_outcomes must contain only SpecificationSourceOutcome, "
                    f"got {type(outcome).__name__}"
                )
            # Every source outcome identity must equal result identity
            if outcome.source.product_identity is not self.product_identity:
                raise ValueError(
                    "Cross-product source outcome rejected: outcome identity "
                    "does not match result identity"
                )

        # Normalized observations must be a tuple
        if not isinstance(self.normalized_observations, tuple):
            raise TypeError("normalized_observations must be a tuple")
        for obs in self.normalized_observations:
            if not isinstance(obs, NormalizedSpecificationObservation):
                raise TypeError(
                    f"normalized_observations must contain only "
                    f"NormalizedSpecificationObservation, got {type(obs).__name__}"
                )
            # Every normalized observation must belong to result identity
            if obs.observation.product_identity is not self.product_identity:
                raise ValueError(
                    "Cross-product normalized observation rejected: observation "
                    "identity does not match result identity"
                )
            # Every normalized observation must use Enterprise SSD schema definitions
            schema_def = ENTERPRISE_SSD_SCHEMA.definitions.get(
                obs.observation.definition.key
            )
            if schema_def is not obs.observation.definition:
                raise ValueError(
                    f"Normalized observation's definition '{obs.observation.definition.key}' "
                    f"does not belong to ENTERPRISE_SSD_SCHEMA"
                )

        # ProductSpecificationSet identity must equal result identity
        if not isinstance(self.product_specification_set, ProductSpecificationSet):
            raise TypeError(
                f"product_specification_set must be a ProductSpecificationSet, got "
                f"{type(self.product_specification_set).__name__}"
            )
        if self.product_specification_set.product_identity is not self.product_identity:
            raise ValueError(
                "ProductSpecificationSet identity does not match result identity"
            )
        # ProductSpecificationSet schema must be ENTERPRISE_SSD_SCHEMA
        if self.product_specification_set.category_schema is not ENTERPRISE_SSD_SCHEMA:
            raise ValueError(
                "ProductSpecificationSet schema is not ENTERPRISE_SSD_SCHEMA"
            )

        # --- Audit 1: observation count consistency ---
        extracted_count = sum(
            outcome.observation_count
            for outcome in self.source_outcomes
            if outcome.outcome_state is SourceOutcomeState.EXTRACTED
        )
        if extracted_count != len(self.normalized_observations):
            raise ValueError(
                f"Result audit inconsistency: sum(EXTRACTED observation_count) "
                f"={extracted_count} != len(normalized_observations) "
                f"={len(self.normalized_observations)}"
            )

        # --- Audit 2: provenance trace ---
        # Every normalized observation must trace to an EXTRACTED source outcome.
        # Multiplicity-aware: if 2 sources each produced 1 observation of the same
        # type, both observations must find matching outcomes.
        _validate_provenance_trace(
            self.source_outcomes,
            self.normalized_observations,
        )

        # --- Audit 3: ProductSpecificationSet evidence consistency ---
        # Every resolution's evidence must equal the normalized observations
        # for that exact definition. No missing, foreign, or substituted evidence.
        _validate_resolution_evidence_consistency(
            self.normalized_observations,
            self.product_specification_set,
        )


def _validate_provenance_trace(
    source_outcomes: tuple[SpecificationSourceOutcome, ...],
    normalized_observations: tuple[NormalizedSpecificationObservation, ...],
) -> None:
    """Validate that every normalized observation traces to an EXTRACTED source outcome.

    Multiplicity-aware matching: each EXTRACTED outcome contributes capacity
    equal to its observation_count. Each observation consumes one unit of
    capacity from a matching outcome.

    Matching provenance:
        - product_identity (already validated at outer level)
        - source_name
        - source_authority
        - final_url (from outcome) == source_url (from observation)
        - retrieved_at
    """
    if not normalized_observations:
        return

    # Build a mutable pool of available EXTRACTED outcomes with remaining capacity.
    # Each outcome contributes capacity equal to its observation_count.
    available: list[dict] = []
    for idx, outcome in enumerate(source_outcomes):
        if outcome.outcome_state is SourceOutcomeState.EXTRACTED:
            available.append({
                "index": idx,
                "outcome": outcome,
                "remaining": outcome.observation_count,
            })

    for norm_obs in normalized_observations:
        raw_obs = norm_obs.observation

        # Find a matching available outcome with remaining capacity
        matched_entry = None
        for entry in available:
            outcome = entry["outcome"]
            source = outcome.source

            # All provenance fields must match
            if source.source_name != raw_obs.source_name:
                continue
            if source.source_authority is not raw_obs.source_authority:
                continue
            if outcome.final_url != raw_obs.source_url:
                continue
            if outcome.retrieved_at != raw_obs.retrieved_at:
                continue
            if entry["remaining"] <= 0:
                continue

            matched_entry = entry
            break

        if matched_entry is None:
            raise ValueError(
                f"Provenance trace failed: normalized observation from "
                f"source '{raw_obs.source_name}' (url={raw_obs.source_url}, "
                f"authority={raw_obs.source_authority.value}, "
                f"retrieved_at={raw_obs.retrieved_at.isoformat()}) "
                f"does not trace to any EXTRACTED source outcome with "
                f"remaining capacity."
            )

        # Consume one unit of capacity from this outcome
        matched_entry["remaining"] -= 1


def _validate_resolution_evidence_consistency(
    normalized_observations: tuple[NormalizedSpecificationObservation, ...],
    product_specification_set: ProductSpecificationSet,
) -> None:
    """Validate that ProductSpecificationSet resolutions use exactly the
    normalized observations for each definition.

    For every schema definition:
        - resolution.evidence must be identity-equal to the subset of
          normalized_observations belonging to that definition
        - No evidence is missing
        - No foreign evidence is present
        - No evidence is silently substituted
    """
    # Group normalized observations by definition
    obs_by_definition: dict[str, list[NormalizedSpecificationObservation]] = {
        key: [] for key in ENTERPRISE_SSD_SCHEMA.definitions
    }
    for norm_obs in normalized_observations:
        key = norm_obs.observation.definition.key
        obs_by_definition[key].append(norm_obs)

    for key in ENTERPRISE_SSD_SCHEMA.definitions:
        resolution = product_specification_set.resolutions.get(key)
        if resolution is None:
            # Should not happen — ProductSpecificationSet already validates completeness
            continue

        expected_obs = tuple(obs_by_definition[key])
        actual_evidence = resolution.evidence

        # Identity check: the evidence tuple must be exactly the observations
        # for this definition (same objects, same order)
        if len(actual_evidence) != len(expected_obs):
            raise ValueError(
                f"Resolution evidence count mismatch for '{key}': "
                f"expected {len(expected_obs)} evidence items, "
                f"got {len(actual_evidence)}"
            )

        for i, (expected, actual) in enumerate(zip(expected_obs, actual_evidence)):
            if expected is not actual:
                raise ValueError(
                    f"Resolution evidence identity mismatch for '{key}' "
                    f"at index {i}: expected the same NormalizedSpecificationObservation "
                    f"object, but got a different one. Evidence must be the exact "
                    f"normalized observations from the pipeline, not substituted."
                )


# ---------------------------------------------------------------------------
# Public execution operation
# ---------------------------------------------------------------------------


def research_enterprise_ssd_specifications(
    *,
    product_identity: ProductIdentity,
    sources: tuple[SpecificationEvidenceSource, ...],
    page_fetcher: PageFetcher,
) -> SpecificationEvidenceResult:
    """Research Enterprise SSD specifications from approved sources.

    Public entry point for 6C specification evidence pipeline.

    Pipeline:
    1. Validate that product_identity is established
    2. Validate that every source's product_identity matches the target
    3. For each source:
       a. Acquire via PageFetcher (catching PageFetchError / UnsafeFetchTargetError)
       b. Extract raw SpecificationObservations
       c. Normalize via frozen 6B normalize_enterprise_ssd_observation()
    4. Group normalized observations by schema definition
    5. Resolve every definition via frozen 6A resolve_specification()
    6. Build complete ProductSpecificationSet (all 12 definitions present)
    7. Return self-validating SpecificationEvidenceResult

    Parameters
    ----------
    product_identity : ProductIdentity
        Target established product identity.
    sources : tuple[SpecificationEvidenceSource, ...]
        Explicitly approved sources.
    page_fetcher : PageFetcher
        Page acquisition protocol (e.g. HttpPageFetcher).

    Returns
    -------
    SpecificationEvidenceResult
        Complete auditable result with source outcomes, normalized observations,
        and resolved ProductSpecificationSet.

    Raises
    ------
    ValueError
        If product_identity is not established, or a source's product_identity
        does not match the target, or provenance trace fails, or resolution
        evidence is inconsistent.
    TypeError
        If product_identity is not a ProductIdentity.
    """
    # Validate target identity
    if not isinstance(product_identity, ProductIdentity):
        raise TypeError(
            f"product_identity must be a ProductIdentity, got "
            f"{type(product_identity).__name__}"
        )
    if not product_identity.is_established:
        raise ValueError(
            "research_enterprise_ssd_specifications requires an established "
            f"ProductIdentity (match_type={product_identity.match_type.value})"
        )

    # Validate sources: every source must match target identity
    for source in sources:
        if not isinstance(source, SpecificationEvidenceSource):
            raise TypeError(
                f"sources must contain only SpecificationEvidenceSource, got "
                f"{type(source).__name__}"
            )
        if source.product_identity is not product_identity:
            raise ValueError(
                "Cross-product source rejected: source's product_identity "
                "does not match the target identity. "
                f"Source identity: {source.product_identity}, "
                f"Target identity: {product_identity}"
            )

    # Process each source — collect outcomes and observations
    source_outcomes: list[SpecificationSourceOutcome] = []
    all_raw_observations: list[SpecificationObservation] = []

    for source in sources:
        source_outcome, observations = _process_source_and_extract(
            source, product_identity, page_fetcher
        )
        source_outcomes.append(source_outcome)
        all_raw_observations.extend(observations)

    # Normalize via frozen 6B
    normalized_observations: list[NormalizedSpecificationObservation] = []
    for obs in all_raw_observations:
        try:
            normalized = normalize_enterprise_ssd_observation(obs)
            normalized_observations.append(normalized)
        except (TypeError, ValueError):
            # Programming exception from 6B — propagate
            raise

    # Group by schema definition
    observations_by_definition: dict[str, list[NormalizedSpecificationObservation]] = {
        key: [] for key in ENTERPRISE_SSD_SCHEMA.definitions
    }
    for norm_obs in normalized_observations:
        key = norm_obs.observation.definition.key
        if key in observations_by_definition:
            observations_by_definition[key].append(norm_obs)

    # Resolve every definition via frozen 6A
    resolutions: dict[str, SpecificationResolution] = {}
    for key, definition in ENTERPRISE_SSD_SCHEMA.definitions.items():
        obs_tuple = tuple(observations_by_definition[key])
        resolution = resolve_specification(product_identity, definition, obs_tuple)
        resolutions[key] = resolution

    # Build complete ProductSpecificationSet
    product_specification_set = ProductSpecificationSet(
        product_identity=product_identity,
        category_schema=ENTERPRISE_SSD_SCHEMA,
        resolutions=resolutions,
    )

    # Build self-validating result
    return SpecificationEvidenceResult(
        product_identity=product_identity,
        source_outcomes=tuple(source_outcomes),
        normalized_observations=tuple(normalized_observations),
        product_specification_set=product_specification_set,
    )


def _process_source_and_extract(
    source: SpecificationEvidenceSource,
    target_identity: ProductIdentity,
    page_fetcher: PageFetcher,
) -> tuple[SpecificationSourceOutcome, list[SpecificationObservation]]:
    """Process one source: fetch, extract, return outcome + observations.

    Note: URL validation occurs at SpecificationEvidenceSource construction
    via ``require_fetchable_url``, so PageFetchRequest creation will always
    succeed here. The only runtime failures come from the fetch itself.
    """

    # Create fetch request — URL already validated at source construction
    fetch_request = PageFetchRequest(url=source.source_url)

    # Attempt fetch
    try:
        fetched_page = page_fetcher.fetch(fetch_request)
    except UnsafeFetchTargetError:
        return (
            SpecificationSourceOutcome(
                source=source,
                final_url=None,
                retrieved_at=None,
                outcome_state=SourceOutcomeState.SOURCE_REFUSED,
                observation_count=0,
            ),
            [],
        )
    except PageFetchError:
        return (
            SpecificationSourceOutcome(
                source=source,
                final_url=None,
                retrieved_at=None,
                outcome_state=SourceOutcomeState.FETCH_FAILED,
                observation_count=0,
            ),
            [],
        )

    # Extract observations
    try:
        observations = list(
            extract_enterprise_ssd_specification_observations(
                product_identity=target_identity,
                document=fetched_page.body_text,
                source_name=source.source_name,
                source_url=source.source_url,
                final_url=fetched_page.final_url,
                retrieved_at=fetched_page.retrieved_at,
                source_authority=source.source_authority,
            )
        )
    except Exception:
        # Programming exception in extraction — propagate
        raise

    # Determine outcome state
    if observations:
        outcome_state = SourceOutcomeState.EXTRACTED
    else:
        outcome_state = SourceOutcomeState.NO_OBSERVATIONS

    return (
        SpecificationSourceOutcome(
            source=source,
            final_url=fetched_page.final_url,
            retrieved_at=fetched_page.retrieved_at,
            outcome_state=outcome_state,
            observation_count=len(observations),
        ),
        observations,
    )
