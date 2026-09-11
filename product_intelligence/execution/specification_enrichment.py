"""Specification enrichment from authoritative datasheets (PRODUCT-INTEL.6D — execution layer).

Acquires manufacturer PDF datasheets, extracts specification observations
through deterministic table interpretation, normalizes through frozen 6B,
and resolves through frozen 6A into a complete ProductSpecificationSet.

    DATASHEET SOURCE (from structured support record)
            ↓
    DocumentFetcher acquisition (PDF bytes + provenance)
            ↓
    pdfplumber table extraction
            ↓
    enterprise_ssd_datasheet pure interpretation
            ↓
    SpecificationObservation(s)
            ↓
    frozen 6B normalize_enterprise_ssd_observation()
            ↓
    NormalizedSpecificationObservation(s)
            ↓
    frozen 6A resolve_specification()
            ↓
    complete ProductSpecificationSet

This module depends on DocumentFetcher protocol (imported from providers.document),
not HttpPdfFetcher concrete implementation. Research extractor does NOT
import providers.

Datasheet URL discovery is structural: the exact datasheet path from the
manufacturer's own supportSpecsData JSON record for the exact matching skuNumber.

AUTHORITATIVE-only enforcement: DatasheetSource requires SourceAuthority.AUTHORITATIVE.
SECONDARY sources are rejected before any fetch.

Bounded parser exception handling: only documented pdfminer.pdfparser.PDFSyntaxError
and pdfminer.pdfminer.PDFMinerException are caught as PARSE_FAILED.
RuntimeError, TypeError, AssertionError propagate.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Any
from urllib.parse import urljoin

import pdfplumber

from product_intelligence.domain.models import ProductIdentity
from product_intelligence.execution.comparable_discovery import (
    ComparableCandidateDiscoveryResult,
    ComparableCandidateSourceOutcome,
    ComparableCandidateSourceOutcomeState as DiscoverySourceOutcomeState,
)
from product_intelligence.providers.document import (
    DocumentFetchError,
    DocumentFetchRequest,
    DocumentFetcher,
    FetchedDocument,
    UnsafeDocumentTargetError,
)
from product_intelligence.providers.page import (
    FetchedPage,
    PageFetchError,
    PageFetchRequest,
    PageFetcher,
    UnsafeFetchTargetError,
)
from product_intelligence.research.datasheet_link_extractor import (
    extract_datasheet_link,
)
from product_intelligence.research.enterprise_ssd import (
    ENTERPRISE_SSD_SCHEMA,
    normalize_enterprise_ssd_observation,
)
from product_intelligence.research.enterprise_ssd_datasheet import (
    extract_datasheet_observations_from_document,
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
# Source descriptor — AUTHORITATIVE only
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class DatasheetSource:
    """One explicitly identified manufacturer datasheet source.

    The source_url is validated at construction. Authority is
    SourceAuthority.AUTHORITATIVE only — manufacturer datasheets are
    authoritative evidence. SECONDARY is rejected at construction.

    The datasheet URL must be mechanically derived from the manufacturer's
    own supportSpecsData JSON record via the 6D datasheet-link extraction
    contract. A caller cannot gain AUTHORITATIVE datasheet authority merely
    by constructing DatasheetSource(url="https://...") with an arbitrary URL.

    Attributes
    ----------
    product_identity : ProductIdentity
        Must be established. The identity this datasheet is about.
    source_name : str
        Human-readable source name (e.g. "Seagate Datasheet").
    source_url : str
        The absolute URL to the PDF datasheet.
    source_authority : SourceAuthority
        Must be AUTHORITATIVE. SECONDARY rejected at construction.
    """

    product_identity: ProductIdentity
    source_name: str
    source_url: str
    source_authority: SourceAuthority

    def __post_init__(self) -> None:
        if not isinstance(self.product_identity, ProductIdentity):
            raise TypeError(
                f"product_identity must be a ProductIdentity, got "
                f"{type(self.product_identity).__name__}"
            )
        if not self.product_identity.is_established:
            raise ValueError(
                "DatasheetSource requires an established ProductIdentity; "
                f"got match_type={self.product_identity.match_type.value}"
            )

        if not isinstance(self.source_name, str) or not self.source_name.strip():
            raise ValueError("source_name must be a non-empty string")
        object.__setattr__(self, "source_name", self.source_name.strip())

        # Validate URL structure
        url = self.source_url.strip()
        _validate_document_url(url, "source_url")
        object.__setattr__(self, "source_url", url)

        if not isinstance(self.source_authority, SourceAuthority):
            raise TypeError(
                f"source_authority must be a SourceAuthority, got "
                f"{type(self.source_authority).__name__}"
            )

        # AUTHORITATIVE-only enforcement
        if self.source_authority is not SourceAuthority.AUTHORITATIVE:
            raise ValueError(
                f"DatasheetSource requires SourceAuthority.AUTHORITATIVE, "
                f"got {self.source_authority.value}. "
                "Manufacturer datasheets are authoritative evidence; "
                "SECONDARY sources are not accepted."
            )


def _validate_document_url(url: str, field_name: str = "url") -> None:
    """Validate a document URL structurally.

    Requirements:
        - absolute http(s) URL
        - hostname present
        - no embedded credentials
    """
    if not isinstance(url, str) or not url.strip():
        raise ValueError(f"{field_name} must be a non-empty string")

    from urllib.parse import urlsplit
    parts = urlsplit(url)

    if parts.scheme.lower() not in ("http", "https"):
        raise ValueError(
            f"{field_name} must be an absolute http:// or https:// URL, got {url!r}"
        )
    if not parts.hostname:
        raise ValueError(f"{field_name} must include a host, got {url!r}")
    if parts.username is not None or parts.password is not None:
        raise ValueError(
            f"{field_name} must not embed credentials, got {url!r}"
        )


# ---------------------------------------------------------------------------
# Source outcome
# ---------------------------------------------------------------------------


class DatasheetOutcomeState(str, Enum):
    """Bounded vocabulary for datasheet acquisition outcomes."""

    ENRICHED = "ENRICHED"
    NO_OBSERVATIONS = "NO_OBSERVATIONS"
    FETCH_FAILED = "FETCH_FAILED"
    SOURCE_REFUSED = "SOURCE_REFUSED"
    PARSE_FAILED = "PARSE_FAILED"


@dataclass(frozen=True)
class DatasheetSourceOutcome:
    """Auditable outcome for one datasheet source.

    Preserves the complete source descriptor and acquisition outcome.

    Self-consistency:
    ENRICHED: final_url present, retrieved_at present, observation_count > 0
    NO_OBSERVATIONS: final_url present, retrieved_at present, observation_count == 0
    FETCH_FAILED: final_url None, retrieved_at None, observation_count == 0
    SOURCE_REFUSED: final_url None, retrieved_at None, observation_count == 0
    PARSE_FAILED: final_url present, retrieved_at present, observation_count == 0
    """

    source: DatasheetSource
    final_url: str | None
    retrieved_at: datetime | None
    outcome_state: DatasheetOutcomeState
    observation_count: int

    def __post_init__(self) -> None:
        if not isinstance(self.source, DatasheetSource):
            raise TypeError(
                f"source must be a DatasheetSource, got "
                f"{type(self.source).__name__}"
            )

        if self.final_url is not None:
            if not isinstance(self.final_url, str) or not self.final_url.strip():
                raise ValueError("final_url must be a non-empty string or None")
            _validate_document_url(self.final_url, "final_url")

        if self.retrieved_at is not None:
            if not isinstance(self.retrieved_at, datetime):
                raise TypeError(
                    f"retrieved_at must be a datetime or None, got "
                    f"{type(self.retrieved_at).__name__}"
                )
            if self.retrieved_at.tzinfo is None or self.retrieved_at.utcoffset() is None:
                raise ValueError("retrieved_at must be timezone-aware")

        if not isinstance(self.outcome_state, DatasheetOutcomeState):
            raise TypeError(
                f"outcome_state must be a DatasheetOutcomeState, got "
                f"{type(self.outcome_state).__name__}"
            )

        if isinstance(self.observation_count, bool) or not isinstance(
            self.observation_count, int
        ):
            raise TypeError(
                f"observation_count must be an int, got "
                f"{type(self.observation_count).__name__}"
            )
        if self.observation_count < 0:
            raise ValueError("observation_count must be non-negative")

        # Self-consistency
        success_states = {
            DatasheetOutcomeState.ENRICHED,
            DatasheetOutcomeState.NO_OBSERVATIONS,
            DatasheetOutcomeState.PARSE_FAILED,
        }
        failure_states = {
            DatasheetOutcomeState.FETCH_FAILED,
            DatasheetOutcomeState.SOURCE_REFUSED,
        }

        if self.outcome_state in success_states:
            if self.final_url is None:
                raise ValueError(f"{self.outcome_state.value} requires final_url")
            if self.retrieved_at is None:
                raise ValueError(f"{self.outcome_state.value} requires retrieved_at")
            if self.outcome_state is DatasheetOutcomeState.ENRICHED:
                if self.observation_count == 0:
                    raise ValueError("ENRICHED requires observation_count > 0")
            else:
                if self.observation_count != 0:
                    raise ValueError(
                        f"{self.outcome_state.value} requires observation_count == 0"
                    )
        elif self.outcome_state in failure_states:
            if self.final_url is not None:
                raise ValueError(f"{self.outcome_state.value} requires final_url None")
            if self.retrieved_at is not None:
                raise ValueError(f"{self.outcome_state.value} requires retrieved_at None")
            if self.observation_count != 0:
                raise ValueError(f"{self.outcome_state.value} requires observation_count 0")


# ---------------------------------------------------------------------------
# Result contract — fully self-auditing
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class SpecificationEnrichmentResult:
    """Complete specification enrichment result from datasheet evidence.

    Immutable and self-validating. Contains:
    - The target product identity
    - Datasheet source outcomes
    - Extracted raw observations
    - Normalized observations
    - Complete ProductSpecificationSet (after 6A resolution)

    Validates at construction that all components are consistent, including:
    - Every raw observation traces to exactly one ENRICHED DatasheetSourceOutcome
    - Exact result product_identity on every observation
    - Exact ENTERPRISE_SSD_SCHEMA definition on every observation
    - source_name, source_authority, source_url, retrieved_at all match outcome
    - Per-source observation_count equals raw observations tracing to that outcome
    - normalized_observations are one-to-one with raw_observations
    - ProductSpecificationSet resolutions are mechanically derived from
      THIS result's normalized_observations (no foreign evidence)
    """

    product_identity: ProductIdentity
    source_outcomes: tuple[DatasheetSourceOutcome, ...]
    raw_observations: tuple[SpecificationObservation, ...]
    normalized_observations: tuple[NormalizedSpecificationObservation, ...]
    product_specification_set: ProductSpecificationSet

    def __post_init__(self) -> None:
        # Identity
        if not isinstance(self.product_identity, ProductIdentity):
            raise TypeError(
                f"product_identity must be a ProductIdentity, got "
                f"{type(self.product_identity).__name__}"
            )
        if not self.product_identity.is_established:
            raise ValueError(
                "SpecificationEnrichmentResult requires an established ProductIdentity"
            )

        # Source outcomes
        if not isinstance(self.source_outcomes, tuple):
            raise TypeError("source_outcomes must be a tuple")
        for outcome in self.source_outcomes:
            if not isinstance(outcome, DatasheetSourceOutcome):
                raise TypeError(
                    f"source_outcomes must contain only DatasheetSourceOutcome, "
                    f"got {type(outcome).__name__}"
                )
            if outcome.source.product_identity is not self.product_identity:
                raise ValueError(
                    "Cross-product source outcome rejected"
                )

        # Raw observations
        if not isinstance(self.raw_observations, tuple):
            raise TypeError("raw_observations must be a tuple")
        for obs in self.raw_observations:
            if not isinstance(obs, SpecificationObservation):
                raise TypeError(
                    f"raw_observations must contain only SpecificationObservation, "
                    f"got {type(obs).__name__}"
                )
            if obs.product_identity is not self.product_identity:
                raise ValueError(
                    "Cross-product raw observation rejected"
                )
            # Must trace to ENTERPRISE_SSD_SCHEMA
            schema_def = ENTERPRISE_SSD_SCHEMA.definitions.get(
                obs.definition.key
            )
            if schema_def is not obs.definition:
                raise ValueError(
                    f"Raw observation's definition '{obs.definition.key}' "
                    "does not belong to ENTERPRISE_SSD_SCHEMA"
                )

        # Normalized observations
        if not isinstance(self.normalized_observations, tuple):
            raise TypeError("normalized_observations must be a tuple")
        for norm_obs in self.normalized_observations:
            if not isinstance(norm_obs, NormalizedSpecificationObservation):
                raise TypeError(
                    f"normalized_observations must contain only "
                    f"NormalizedSpecificationObservation, got "
                    f"{type(norm_obs).__name__}"
                )
            if norm_obs.observation.product_identity is not self.product_identity:
                raise ValueError(
                    "Cross-product normalized observation rejected"
                )

        # ProductSpecificationSet
        if not isinstance(self.product_specification_set, ProductSpecificationSet):
            raise TypeError(
                f"product_specification_set must be a ProductSpecificationSet, got "
                f"{type(self.product_specification_set).__name__}"
            )
        if self.product_specification_set.product_identity is not self.product_identity:
            raise ValueError(
                "ProductSpecificationSet identity does not match result identity"
            )
        if self.product_specification_set.category_schema is not ENTERPRISE_SSD_SCHEMA:
            raise ValueError(
                "ProductSpecificationSet schema is not ENTERPRISE_SSD_SCHEMA"
            )

        # --- Audit 1: raw -> outcome provenance trace ---
        _validate_raw_observation_provenance(
            self.source_outcomes,
            self.raw_observations,
        )

        # --- Audit 2: raw -> normalized exact binding ---
        _validate_raw_normalized_binding(
            self.raw_observations,
            self.normalized_observations,
        )

        # --- Audit 3: normalized -> resolution re-derivation ---
        _validate_resolution_rederviation(
            self.product_identity,
            self.normalized_observations,
            self.product_specification_set,
        )


def _validate_raw_observation_provenance(
    source_outcomes: tuple[DatasheetSourceOutcome, ...],
    raw_observations: tuple[SpecificationObservation, ...],
) -> None:
    """Validate that every raw observation traces to exactly one ENRICHED outcome.

    Per-source: observation_count must equal the number of raw observations
    tracing to that exact ENRICHED outcome.

    Evidence cannot trace to:
        FETCH_FAILED, SOURCE_REFUSED, PARSE_FAILED, NO_OBSERVATIONS,
        foreign source, foreign final_url, wrong timestamp, wrong authority,
        wrong identity.

    When raw_observations is empty:
        - ENRICHED outcome with positive observation_count is REJECTED
          (fabricated evidence with zero raw observations)
        - Non-ENRICHED outcomes with zero count are valid
    """
    # Build ENRICHED outcome pool
    enriched_outcomes = [
        o for o in source_outcomes
        if o.outcome_state is DatasheetOutcomeState.ENRICHED
    ]

    # When raw_observations is empty: no ENRICHED outcome may claim positive count.
    # ENRICHED + count > 0 + zero raw = fabricated evidence.
    # Non-ENRICHED (FETCH_FAILED, SOURCE_REFUSED, PARSE_FAILED, NO_OBSERVATIONS)
    # with zero raw are valid per their contracts.
    if not raw_observations:
        for outcome in enriched_outcomes:
            if outcome.observation_count > 0:
                raise ValueError(
                    f"ENRICHED outcome for '{outcome.source.source_name}' "
                    f"(final_url={outcome.final_url}) claims observation_count="
                    f"{outcome.observation_count} but zero raw observations "
                    "are present. Every ENRICHED outcome must have traceable "
                    "raw observations — fabricated evidence rejected."
                )
        return

    # Reject ambiguous duplicate provenance FIRST: if two ENRICHED outcomes
    # share identical provenance, a raw observation cannot trace unambiguously.
    provenance_keys: list[tuple] = []
    for outcome in enriched_outcomes:
        key = (
            outcome.source.source_name,
            outcome.source.source_authority,
            outcome.final_url,
            outcome.retrieved_at,
        )
        provenance_keys.append(key)
    if len(provenance_keys) != len(set(provenance_keys)):
        raise ValueError(
            "Ambiguous duplicate provenance: multiple ENRICHED outcomes "
            "share identical provenance keys (source_name, source_authority, "
            "final_url, retrieved_at). A raw observation cannot trace to "
            "more than one outcome unambiguously."
        )

    # Build a pool of ENRICHED outcomes with remaining capacity
    available: list[dict] = []
    for outcome in source_outcomes:
        if outcome.outcome_state is DatasheetOutcomeState.ENRICHED:
            available.append({
                "outcome": outcome,
                "remaining": outcome.observation_count,
                "matched": 0,
            })

    for obs in raw_observations:
        matched_entry = None
        for entry in available:
            outcome = entry["outcome"]
            source = outcome.source

            # All provenance fields must match exactly
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

            matched_entry = entry
            break

        if matched_entry is None:
            raise ValueError(
                f"Raw observation from source '{obs.source_name}' "
                f"(url={obs.source_url}, authority={obs.source_authority.value}, "
                f"retrieved_at={obs.retrieved_at.isoformat()}) "
                f"does not trace to any ENRICHED source outcome with "
                f"remaining capacity."
            )

        matched_entry["remaining"] -= 1
        matched_entry["matched"] += 1

    # Verify per-source observation_count is exact
    for entry in available:
        outcome = entry["outcome"]
        if entry["matched"] != outcome.observation_count:
            raise ValueError(
                f"Per-source audit: outcome for '{outcome.source.source_name}' "
                f"(final_url={outcome.final_url}) claims observation_count="
                f"{outcome.observation_count} but only {entry['matched']} "
                f"raw observations trace to it."
            )


def _validate_raw_normalized_binding(
    raw_observations: tuple[SpecificationObservation, ...],
    normalized_observations: tuple[NormalizedSpecificationObservation, ...],
) -> None:
    """Validate exact one-to-one binding between raw and normalized observations.

    normalized[n].observation must be raw[n] for all n.
    No foreign/reordered/substituted normalized observation.
    """
    if len(raw_observations) != len(normalized_observations):
        raise ValueError(
            f"Result audit: len(raw_observations) "
            f"={len(raw_observations)} != len(normalized_observations) "
            f"={len(normalized_observations)}"
        )

    for i, (raw_obs, norm_obs) in enumerate(zip(raw_observations, normalized_observations)):
        if norm_obs.observation is not raw_obs:
            raise ValueError(
                f"Raw-normalized binding broken at index {i}: "
                f"normalized_observation[{i}].observation is not "
                f"raw_observations[{i}]. Evidence cannot be reordered or "
                f"substituted between raw and normalized."
            )


def _validate_resolution_rederviation(
    product_identity: ProductIdentity,
    normalized_observations: tuple[NormalizedSpecificationObservation, ...],
    product_specification_set: ProductSpecificationSet,
) -> None:
    """Re-derive resolutions from this result's normalized observations.

    For every schema definition:
        1. Group normalized_observations by exact schema definition
        2. Call frozen resolve_specification(...)
        3. Require the supplied resolution equals the derived resolution

    A caller must not be able to supply a ProductSpecificationSet
    built from different evidence.
    """
    # Group normalized observations by definition
    obs_by_definition: dict[str, list[NormalizedSpecificationObservation]] = {
        key: [] for key in ENTERPRISE_SSD_SCHEMA.definitions
    }
    for norm_obs in normalized_observations:
        key = norm_obs.observation.definition.key
        if key in obs_by_definition:
            obs_by_definition[key].append(norm_obs)

    for key, definition in ENTERPRISE_SSD_SCHEMA.definitions.items():
        obs_tuple = tuple(obs_by_definition[key])
        derived_resolution = resolve_specification(
            product_identity, definition, obs_tuple
        )

        supplied_resolution = product_specification_set.resolutions.get(key)
        if supplied_resolution is None:
            raise ValueError(
                f"Resolution for '{key}' is missing from "
                "ProductSpecificationSet"
            )

        # Verify state matches
        if derived_resolution.state is not supplied_resolution.state:
            raise ValueError(
                f"Resolution for '{key}' state mismatch: "
                f"derived {derived_resolution.state.value}, "
                f"supplied {supplied_resolution.state.value}. "
                "Resolutions must be derived from this result's evidence."
            )

        # Verify resolved_value matches
        if derived_resolution.resolved_value is not None and \
           supplied_resolution.resolved_value is not None:
            if derived_resolution.resolved_value.value != \
               supplied_resolution.resolved_value.value:
                raise ValueError(
                    f"Resolution for '{key}' value mismatch: "
                    f"derived {derived_resolution.resolved_value.value!r}, "
                    f"supplied {supplied_resolution.resolved_value.value!r}"
                )
            if type(derived_resolution.resolved_value.value) is not \
               type(supplied_resolution.resolved_value.value):
                raise ValueError(
                    f"Resolution for '{key}' type mismatch: "
                    f"derived {type(derived_resolution.resolved_value.value).__name__}, "
                    f"supplied {type(supplied_resolution.resolved_value.value).__name__}"
                )
        elif derived_resolution.resolved_value is None and \
             supplied_resolution.resolved_value is not None:
            raise ValueError(
                f"Resolution for '{key}' should be None (derived), "
                f"but supplied {supplied_resolution.resolved_value.value!r}"
            )
        elif derived_resolution.resolved_value is not None and \
             supplied_resolution.resolved_value is None:
            raise ValueError(
                f"Resolution for '{key}' should have value "
                f"{derived_resolution.resolved_value.value!r}, but supplied None"
            )

        # Verify evidence tuple is identity-equal
        if derived_resolution.evidence is not supplied_resolution.evidence:
            # Both have same elements; check identity
            if len(derived_resolution.evidence) != len(supplied_resolution.evidence):
                raise ValueError(
                    f"Resolution for '{key}' evidence count mismatch: "
                    f"derived {len(derived_resolution.evidence)}, "
                    f"supplied {len(supplied_resolution.evidence)}"
                )
            for i, (expected, actual) in enumerate(
                zip(derived_resolution.evidence, supplied_resolution.evidence)
            ):
                if expected is not actual:
                    raise ValueError(
                        f"Resolution for '{key}' evidence[{i}] is not the "
                        "same object as the derived evidence. "
                        "Evidence must be the exact normalized observations "
                        "from this result, not substituted."
                    )


# ---------------------------------------------------------------------------
# Bounded parser exceptions
# ---------------------------------------------------------------------------
# Only known PDF parser exceptions are caught as PARSE_FAILED.
# Programming exceptions (RuntimeError, TypeError, AssertionError) propagate.


def _is_pdf_parser_exception(exc: BaseException) -> bool:
    """Check if an exception is a known PDF parser/document error.

    Catches ONLY explicit verified parser/document exception classes:

    From pdfminer (pdfplumber's underlying parser):
        - pdfminer.pdfparser.PDFSyntaxError

    From pdfplumber (wraps pdfminer exceptions):
        - pdfplumber.utils.exceptions.PdfminerException

    Does NOT catch:
        - RuntimeError (programming error — propagates)
        - TypeError (programming error — propagates)
        - AssertionError (programming error — propagates)
        - KeyError, IndexError, ValueError (programming errors — propagate)
        - arbitrary Exception
        - ANY exception classified by module-name substring

    Programming exceptions raised while inside pdfplumber.open() or
    page.extract_tables() must propagate rather than become PARSE_FAILED.
    """
    # Only explicit verified parser/document exception classes.
    # NO module-name substring matching — that would catch programming
    # errors (RuntimeError, TypeError) raised inside pdfplumber/pdfminer.

    # pdfplumber wraps all pdfminer exceptions in its own wrapper.
    # This is the primary path: pdfplumber.open() raises PdfminerException.
    try:
        from pdfplumber.utils.exceptions import PdfminerException
        if isinstance(exc, PdfminerException):
            return True
    except ImportError:
        pass

    # Direct pdfminer exceptions (rare — only if code calls pdfminer directly)
    try:
        from pdfminer.pdfparser import PDFSyntaxError
        if isinstance(exc, PDFSyntaxError):
            return True
    except ImportError:
        pass

    return False


# ---------------------------------------------------------------------------
# Public execution operation
# ---------------------------------------------------------------------------


def _enrich_from_datasheet_sources_internal(
    *,
    product_identity: ProductIdentity,
    sources: tuple[DatasheetSource, ...],
    document_fetcher: DocumentFetcher,
) -> SpecificationEnrichmentResult:
    """Low-level enrichment from already-derived DatasheetSource objects.

    INTERNAL — does NOT establish authority. The public authority path is
    through derive_datasheet_source_from_discovery() which grounds authority
    in a frozen 7A ComparableCandidateDiscoveryResult.

    This helper is used internally by the public authority-establishing
    path after datasheet URLs have been mechanically derived from 7A evidence.
    """
    if not isinstance(product_identity, ProductIdentity):
        raise TypeError(
            f"product_identity must be a ProductIdentity, got "
            f"{type(product_identity).__name__}"
        )
    if not product_identity.is_established:
        raise ValueError(
            "enrich_enterprise_ssd_specifications requires an established "
            f"ProductIdentity (match_type={product_identity.match_type.value})"
        )

    # Validate sources
    for source in sources:
        if not isinstance(source, DatasheetSource):
            raise TypeError(
                f"sources must contain only DatasheetSource, got "
                f"{type(source).__name__}"
            )
        if source.product_identity is not product_identity:
            raise ValueError(
                "Cross-product source rejected: source's product_identity "
                "does not match the target identity"
            )

    # Deduplicate by exact URL — one fetch per datasheet
    seen_urls: set[str] = set()
    unique_sources: list[DatasheetSource] = []
    for source in sources:
        if source.source_url not in seen_urls:
            seen_urls.add(source.source_url)
            unique_sources.append(source)

    # Process each unique source
    source_outcomes: list[DatasheetSourceOutcome] = []
    all_raw_observations: list[SpecificationObservation] = []

    for source in unique_sources:
        outcome, observations = _process_datasheet_source(
            source, product_identity, document_fetcher
        )
        source_outcomes.append(outcome)
        all_raw_observations.extend(observations)

    # Normalize via frozen 6B
    normalized_observations: list[NormalizedSpecificationObservation] = []
    for obs in all_raw_observations:
        normalized = normalize_enterprise_ssd_observation(obs)
        normalized_observations.append(normalized)

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

    return SpecificationEnrichmentResult(
        product_identity=product_identity,
        source_outcomes=tuple(source_outcomes),
        raw_observations=tuple(all_raw_observations),
        normalized_observations=tuple(normalized_observations),
        product_specification_set=product_specification_set,
    )


# ---------------------------------------------------------------------------
# Public authority-establishing enrichment
# ---------------------------------------------------------------------------


def enrich_enterprise_ssd_specifications(
    *,
    product_identity: ProductIdentity,
    discovery_result: ComparableCandidateDiscoveryResult,
    source_outcome: ComparableCandidateSourceOutcome,
    page_fetcher: PageFetcher,
    document_fetcher: DocumentFetcher,
) -> SpecificationEnrichmentResult:
    """Enrich Enterprise SSD specifications from manufacturer PDF datasheets.

    Public entry point for 6D single-product specification enrichment pipeline.

    Authority chain:
        frozen 7A ComparableCandidateDiscoveryResult
          -> exact EXTRACTED AUTHORITATIVE source outcome (identity-verified member)
          -> support-page fetch via page_fetcher
          -> exact supportSpecsData skuNumber
          -> exact datasheet field
          -> resolved PDF URL
          -> PDF fetch via document_fetcher
          -> evidence

    A caller CANNOT establish AUTHORITATIVE datasheet evidence by passing
    arbitrary DatasheetSource objects or URLs. Authority must be grounded
    in a frozen 7A ComparableCandidateDiscoveryResult.

    Parameters
    ----------
    product_identity : ProductIdentity
        Established product identity whose MPN is the skuNumber.
    discovery_result : ComparableCandidateDiscoveryResult
        Frozen 7A discovery result (exact type required).
    source_outcome : ComparableCandidateSourceOutcome
        One EXTRACTED outcome from the discovery_result.
    page_fetcher : PageFetcher
        Page acquisition protocol (for support page fetch).
    document_fetcher : DocumentFetcher
        Document acquisition protocol (for PDF fetch).

    Returns
    -------
    SpecificationEnrichmentResult
        Complete enrichment result from the derived datasheet.

    Raises
    ------
    TypeError
        If discovery_result is not ComparableCandidateDiscoveryResult.
        If source_outcome is not ComparableCandidateSourceOutcome.
        If product_identity is not ProductIdentity.
    ValueError
        If source_outcome is not a member of discovery_result.source_outcomes.
        If source_outcome.outcome_state is not EXTRACTED.
        If source_outcome.source.source_authority is not AUTHORITATIVE.
    """
    # --- Validate product_identity ---
    if not isinstance(product_identity, ProductIdentity):
        raise TypeError(
            f"product_identity must be a ProductIdentity, got "
            f"{type(product_identity).__name__}"
        )
    if not product_identity.is_established:
        raise ValueError(
            "enrich_enterprise_ssd_specifications requires an established "
            f"ProductIdentity (match_type={product_identity.match_type.value})"
        )

    # --- Validate exact frozen 7A discovery result type BEFORE any fetch ---
    if type(discovery_result) is not ComparableCandidateDiscoveryResult:
        raise TypeError(
            f"discovery_result must be a ComparableCandidateDiscoveryResult, got "
            f"{type(discovery_result).__name__}. "
            "Authority must be grounded in a frozen 7A discovery result."
        )

    # --- Validate source_outcome is an EXACT member (identity check) ---
    if not isinstance(source_outcome, ComparableCandidateSourceOutcome):
        raise TypeError(
            f"source_outcome must be a ComparableCandidateSourceOutcome, got "
            f"{type(source_outcome).__name__}"
        )

    found_outcome = None
    for outcome in discovery_result.source_outcomes:
        if outcome is source_outcome:
            found_outcome = outcome
            break

    if found_outcome is None:
        raise ValueError(
            "source_outcome is not a member of the given discovery_result. "
            "It must be the exact object from one of the discovery_result's "
            "source_outcomes (object identity)."
        )

    # --- Must be EXTRACTED ---
    if source_outcome.outcome_state is not DiscoverySourceOutcomeState.EXTRACTED:
        raise ValueError(
            f"source_outcome must be EXTRACTED, got "
            f"{source_outcome.outcome_state.value}. "
            "Only EXTRACTED AUTHORITATIVE sources from 7A may establish datasheet authority."
        )

    # --- Source must be AUTHORITATIVE ---
    if source_outcome.source.source_authority is not SourceAuthority.AUTHORITATIVE:
        raise ValueError(
            f"source_outcome.source must be AUTHORITATIVE, got "
            f"{source_outcome.source.source_authority.value}"
        )

    # --- Derive DatasheetSource through the authority chain ---
    datasheet_source = derive_datasheet_source_from_discovery(
        product_identity=product_identity,
        discovery_result=discovery_result,
        source_outcome=source_outcome,
        page_fetcher=page_fetcher,
    )

    if datasheet_source is None:
        # Derivation failed (page fetch error, no skuNumber match, no datasheet
        # field). No datasheet source was established — return empty result with
        # zero source_outcomes. Do NOT invent a DatasheetSourceOutcome.
        return SpecificationEnrichmentResult(
            product_identity=product_identity,
            source_outcomes=(),
            raw_observations=(),
            normalized_observations=(),
            product_specification_set=_build_empty_spec_set(product_identity),
        )

    # --- Enrich from the derived authoritative DatasheetSource ---
    return _enrich_from_datasheet_sources_internal(
        product_identity=product_identity,
        sources=(datasheet_source,),
        document_fetcher=document_fetcher,
    )


def _build_empty_spec_set(
    product_identity: ProductIdentity,
) -> ProductSpecificationSet:
    """Build an empty ProductSpecificationSet (all fields UNKNOWN)."""
    from product_intelligence.research.specifications import resolve_specification

    resolutions: dict[str, SpecificationResolution] = {}
    for key, definition in ENTERPRISE_SSD_SCHEMA.definitions.items():
        resolutions[key] = resolve_specification(product_identity, definition, ())
    return ProductSpecificationSet(
        product_identity=product_identity,
        category_schema=ENTERPRISE_SSD_SCHEMA,
        resolutions=resolutions,
    )


# ---------------------------------------------------------------------------
# Internal source processing
# ---------------------------------------------------------------------------


def _process_datasheet_source(
    source: DatasheetSource,
    target_identity: ProductIdentity,
    document_fetcher: DocumentFetcher,
) -> tuple[DatasheetSourceOutcome, list[SpecificationObservation]]:
    """Process one datasheet source: fetch, parse, extract, return outcome + observations."""

    fetch_request = DocumentFetchRequest(url=source.source_url)

    # Attempt fetch
    try:
        fetched = document_fetcher.fetch(fetch_request)
    except UnsafeDocumentTargetError:
        return (
            DatasheetSourceOutcome(
                source=source,
                final_url=None,
                retrieved_at=None,
                outcome_state=DatasheetOutcomeState.SOURCE_REFUSED,
                observation_count=0,
            ),
            [],
        )
    except DocumentFetchError:
        return (
            DatasheetSourceOutcome(
                source=source,
                final_url=None,
                retrieved_at=None,
                outcome_state=DatasheetOutcomeState.FETCH_FAILED,
                observation_count=0,
            ),
            [],
        )

    # Parse PDF tables via pdfplumber — bounded exception handling
    pdf = None
    try:
        import io
        try:
            pdf = pdfplumber.open(io.BytesIO(fetched.body_bytes))
        except Exception as exc:
            if _is_pdf_parser_exception(exc):
                return (
                    DatasheetSourceOutcome(
                        source=source,
                        final_url=fetched.final_url,
                        retrieved_at=fetched.retrieved_at,
                        outcome_state=DatasheetOutcomeState.PARSE_FAILED,
                        observation_count=0,
                    ),
                    [],
                )
            # Programming exception — propagate
            raise

        # Extract all tables with page/table indices
        all_tables: list[tuple[int, int, list[list[str | None]]]] = []

        for page_idx, page in enumerate(pdf.pages):
            try:
                tables = page.extract_tables()
            except Exception as exc:
                if _is_pdf_parser_exception(exc):
                    # Parser error during table extraction -> PARSE_FAILED
                    return (
                        DatasheetSourceOutcome(
                            source=source,
                            final_url=fetched.final_url,
                            retrieved_at=fetched.retrieved_at,
                            outcome_state=DatasheetOutcomeState.PARSE_FAILED,
                            observation_count=0,
                        ),
                        [],
                    )
                # Programming exception — propagate
                raise

            if not tables:
                continue
            for table_idx, table in enumerate(tables):
                if not table:
                    continue
                all_tables.append((page_idx, table_idx, table))

        # Extract observations using whole-document MPN uniqueness
        all_observations: list[SpecificationObservation] = []

        if all_tables:
            try:
                all_observations = extract_datasheet_observations_from_document(
                    product_identity=target_identity,
                    all_tables=all_tables,
                    source_name=source.source_name,
                    source_url=fetched.final_url,
                    retrieved_at=fetched.retrieved_at,
                    source_authority=source.source_authority,
                )
            except ValueError:
                # MPN ambiguity (ValueError) propagates — this is a research
                # error, not a parser error. The caller must handle ambiguous
                # MPN at the application level.
                raise
            except Exception as exc:
                if _is_pdf_parser_exception(exc):
                    return (
                        DatasheetSourceOutcome(
                            source=source,
                            final_url=fetched.final_url,
                            retrieved_at=fetched.retrieved_at,
                            outcome_state=DatasheetOutcomeState.PARSE_FAILED,
                            observation_count=0,
                        ),
                        [],
                    )
                # Programming exception — propagate
                raise

    finally:
        if pdf is not None:
            pdf.close()

    if all_observations:
        outcome_state = DatasheetOutcomeState.ENRICHED
    else:
        outcome_state = DatasheetOutcomeState.NO_OBSERVATIONS

    return (
        DatasheetSourceOutcome(
            source=source,
            final_url=fetched.final_url,
            retrieved_at=fetched.retrieved_at,
            outcome_state=outcome_state,
            observation_count=len(all_observations),
        ),
        all_observations,
    )


# ---------------------------------------------------------------------------
# 6C + 6D evidence composition
# ---------------------------------------------------------------------------


def compose_6c_6d_specifications(
    *,
    product_identity: ProductIdentity,
    frozen_6c_spec_set: ProductSpecificationSet,
    enrichment_result: SpecificationEnrichmentResult,
) -> ProductSpecificationSet:
    """Combine specification EVIDENCE from frozen 6C + 6D datasheet enrichment.

    Does NOT copy VERIFIED values directly. Instead gathers the underlying
    normalized evidence from both sources and runs the frozen 6A resolver
    again across the complete 12-field schema.

    Fails closed for:
        - cross-product identity
        - wrong schema
        - foreign definition
        - duplicated/contradictory evidence per frozen 6A semantics

    Parameters
    ----------
    product_identity : ProductIdentity
        Target established product identity (must match both inputs).
    frozen_6c_spec_set : ProductSpecificationSet
        Complete specification set from frozen 6C extraction.
    enrichment_result : SpecificationEnrichmentResult
        Complete 6D datasheet enrichment result.

    Returns
    -------
    ProductSpecificationSet
        Complete combined specification set with all 12 fields resolved.

    Raises
    ------
    ValueError
        If identities don't match, schemas are wrong, or evidence is foreign.
    TypeError
        If inputs are wrong type.
    """
    if not isinstance(product_identity, ProductIdentity):
        raise TypeError(
            f"product_identity must be a ProductIdentity, got "
            f"{type(product_identity).__name__}"
        )

    if not isinstance(frozen_6c_spec_set, ProductSpecificationSet):
        raise TypeError(
            f"frozen_6c_spec_set must be a ProductSpecificationSet, got "
            f"{type(frozen_6c_spec_set).__name__}"
        )

    if not isinstance(enrichment_result, SpecificationEnrichmentResult):
        raise TypeError(
            f"enrichment_result must be a SpecificationEnrichmentResult, got "
            f"{type(enrichment_result).__name__}"
        )

    # Validate identity consistency
    if frozen_6c_spec_set.product_identity is not product_identity:
        raise ValueError(
            "Cross-product identity: frozen 6C spec_set identity does not "
            "match the target product_identity"
        )
    if enrichment_result.product_identity is not product_identity:
        raise ValueError(
            "Cross-product identity: enrichment result identity does not "
            "match the target product_identity"
        )

    # Validate schema consistency
    if frozen_6c_spec_set.category_schema is not ENTERPRISE_SSD_SCHEMA:
        raise ValueError(
            "frozen 6C spec_set schema is not ENTERPRISE_SSD_SCHEMA"
        )
    if enrichment_result.product_specification_set.category_schema is not \
       ENTERPRISE_SSD_SCHEMA:
        raise ValueError(
            "enrichment result spec_set schema is not ENTERPRISE_SSD_SCHEMA"
        )

    # Gather all normalized evidence from both sources
    # From 6C: extract evidence from each resolution
    all_normalized: list[NormalizedSpecificationObservation] = []
    for key, resolution in frozen_6c_spec_set.resolutions.items():
        if resolution.definition is not ENTERPRISE_SSD_SCHEMA.definitions.get(key):
            raise ValueError(
                f"Foreign definition in frozen 6C resolution for '{key}'"
            )
        all_normalized.extend(resolution.evidence)

    # From 6D: use the enrichment result's normalized observations
    all_normalized.extend(enrichment_result.normalized_observations)

    # Group by schema definition
    observations_by_definition: dict[str, list[NormalizedSpecificationObservation]] = {
        key: [] for key in ENTERPRISE_SSD_SCHEMA.definitions
    }
    for norm_obs in all_normalized:
        key = norm_obs.observation.definition.key
        if key in observations_by_definition:
            observations_by_definition[key].append(norm_obs)

    # Resolve every definition via frozen 6A
    resolutions: dict[str, SpecificationResolution] = {}
    for key, definition in ENTERPRISE_SSD_SCHEMA.definitions.items():
        obs_tuple = tuple(observations_by_definition[key])
        resolution = resolve_specification(product_identity, definition, obs_tuple)
        resolutions[key] = resolution

    return ProductSpecificationSet(
        product_identity=product_identity,
        category_schema=ENTERPRISE_SSD_SCHEMA,
        resolutions=resolutions,
    )


# ---------------------------------------------------------------------------
# 6D Authority Chain — PUBLIC authority-establishing operations
# ---------------------------------------------------------------------------
# Grounded in frozen 7A ComparableCandidateDiscoveryResult.
# Arbitrary caller-provided DatasheetSource/URL objects cannot enter
# the public authority path.


def derive_datasheet_source_from_discovery(
    *,
    product_identity: ProductIdentity,
    discovery_result: ComparableCandidateDiscoveryResult,
    source_outcome: ComparableCandidateSourceOutcome,
    page_fetcher: PageFetcher,
) -> DatasheetSource | None:
    """Derive an authoritative DatasheetSource from a frozen 7A EXTRACTED source outcome.

    This is the PUBLIC 6D authority-establishing path. A caller CANNOT gain
    AUTHORITATIVE datasheet authority by constructing
    DatasheetSource(url="https://...") with an arbitrary URL. Instead, the
    datasheet URL must be mechanically derived from the manufacturer's own
    supportSpecsData JSON record via the 6D datasheet-link extraction contract.

    Authority chain:
        frozen 7A ComparableCandidateDiscoveryResult
          -> EXTRACTED AUTHORITATIVE source outcome
          -> exact source descriptor object (object identity verified)
          -> support-page fetch
          -> exact supportSpecsData skuNumber
          -> exact datasheet field
          -> resolved PDF URL
          -> PDF fetch
          -> evidence

    Validates BEFORE any fetch:
        1. discovery_result is EXACTLY a ComparableCandidateDiscoveryResult
        2. source_outcome is EXACTLY an EXTRACTED outcome from that result
        3. source_outcome.source_authority is AUTHORITATIVE
        4. source_outcome.source is the exact frozen 7A object (identity check)

    Abstention rules:
        - Fetch failure -> None
        - No supportSpecsData anchor -> None
        - No matching skuNumber record -> None
        - No datasheet field -> None
        - Ambiguous skuNumber -> raises ValueError (fail closed)

    Parameters
    ----------
    product_identity : ProductIdentity
        Must be established. The identity whose MPN is the skuNumber.
    discovery_result : ComparableCandidateDiscoveryResult
        Frozen 7A discovery result (exact type required).
    source_outcome : ComparableCandidateSourceOutcome
        One EXTRACTED outcome from the discovery result.
    page_fetcher : PageFetcher
        Page acquisition protocol.

    Returns
    -------
    DatasheetSource | None
        The derived authoritative datasheet source, or None if not found.

    Raises
    ------
    TypeError
        If discovery_result is not a ComparableCandidateDiscoveryResult.
        If source_outcome is not a ComparableCandidateSourceOutcome.
    ValueError
        If source_outcome is not EXTRACTED.
        If source_outcome is not from the given discovery_result.
        If skuNumber matches multiple records (ambiguous -> fail closed).
    """
    # --- EXACT type check BEFORE any fetch ---
    if type(discovery_result) is not ComparableCandidateDiscoveryResult:
        raise TypeError(
            f"discovery_result must be a ComparableCandidateDiscoveryResult, got "
            f"{type(discovery_result).__name__}. "
            "Authority must be grounded in a frozen 7A discovery result."
        )

    if not isinstance(source_outcome, ComparableCandidateSourceOutcome):
        raise TypeError(
            f"source_outcome must be a ComparableCandidateSourceOutcome, got "
            f"{type(source_outcome).__name__}"
        )

    # Validate that source_outcome is EXACTLY an EXTRACTED outcome from this result
    found_outcome = None
    for outcome in discovery_result.source_outcomes:
        if outcome is source_outcome:
            found_outcome = outcome
            break

    if found_outcome is None:
        raise ValueError(
            f"source_outcome is not from the given discovery_result. "
            f"The source_outcome must be the exact object from one of the "
            f"discovery_result's source_outcomes (object identity). "
            f"Found {len(discovery_result.source_outcomes)} outcomes in result, "
            f"none match by identity."
        )

    # Must be EXTRACTED
    if source_outcome.outcome_state is not DiscoverySourceOutcomeState.EXTRACTED:
        raise ValueError(
            f"source_outcome must be EXTRACTED, got "
            f"{source_outcome.outcome_state.value}. "
            "Only EXTRACTED AUTHORITATIVE sources from 7A may derive datasheets."
        )

    # Source must be AUTHORITATIVE (7A invariant, but re-check for safety)
    if source_outcome.source.source_authority is not SourceAuthority.AUTHORITATIVE:
        raise ValueError(
            f"source_outcome.source must be AUTHORITATIVE, got "
            f"{source_outcome.source.source_authority.value}"
        )

    # Validate product_identity
    if not isinstance(product_identity, ProductIdentity):
        raise TypeError(
            f"product_identity must be a ProductIdentity, got "
            f"{type(product_identity).__name__}"
        )
    if not product_identity.is_established:
        raise ValueError(
            "derive_datasheet_source_from_discovery requires an established ProductIdentity"
        )

    # Validate page_fetcher has fetch method
    if not hasattr(page_fetcher, "fetch"):
        raise TypeError(
            f"page_fetcher must implement PageFetcher protocol (has fetch()), got "
            f"{type(page_fetcher).__name__}"
        )

    # Fetch the support page
    source = source_outcome.source
    fetch_request = PageFetchRequest(url=source.source_url)
    try:
        fetched_page: FetchedPage = page_fetcher.fetch(fetch_request)
    except UnsafeFetchTargetError:
        return None
    except PageFetchError:
        return None

    # Extract datasheet link from supportSpecsData for exact skuNumber
    sku_number = product_identity.manufacturer_part_number
    if not sku_number:
        return None

    try:
        link = extract_datasheet_link(
            document=fetched_page.body_text,
            sku_number=sku_number,
        )
    except ValueError:
        # Ambiguous skuNumber -> fail closed (re-raise)
        raise

    if link is None:
        return None

    # Resolve relative path against the support page's final URL
    absolute_url = urljoin(fetched_page.final_url, link.datasheet_path)

    # Validate the resolved URL structurally
    _validate_document_url(absolute_url, "datasheet_url")

    return DatasheetSource(
        product_identity=product_identity,
        source_name=f"{source.source_name} Datasheet",
        source_url=absolute_url,
        source_authority=SourceAuthority.AUTHORITATIVE,
    )


def _derive_datasheet_source_internal(
    *,
    product_identity: ProductIdentity,
    discovery_source: Any,
    page_fetcher: PageFetcher,
) -> DatasheetSource | None:
    """Internal: derive datasheet from a ComparableCandidateSource descriptor.

    Used internally by the batch function after source descriptors have been
    extracted from and validated against a frozen 7A discovery result.

    Does NOT validate the source's origin — the caller must have already
    established authority through derive_datasheet_source_from_discovery()
    or the batch discovery_result validation.
    """
    from product_intelligence.research.comparable_candidates import (
        ComparableCandidateSource,
    )

    if not isinstance(discovery_source, ComparableCandidateSource):
        raise TypeError(
            f"discovery_source must be a ComparableCandidateSource, got "
            f"{type(discovery_source).__name__}"
        )
    if discovery_source.source_authority is not SourceAuthority.AUTHORITATIVE:
        raise ValueError(
            f"discovery_source must be AUTHORITATIVE, got "
            f"{discovery_source.source_authority.value}"
        )

    fetch_request = PageFetchRequest(url=discovery_source.source_url)
    try:
        fetched_page: FetchedPage = page_fetcher.fetch(fetch_request)
    except UnsafeFetchTargetError:
        return None
    except PageFetchError:
        return None

    sku_number = product_identity.manufacturer_part_number
    if not sku_number:
        return None

    try:
        link = extract_datasheet_link(
            document=fetched_page.body_text,
            sku_number=sku_number,
        )
    except ValueError:
        raise

    if link is None:
        return None

    absolute_url = urljoin(fetched_page.final_url, link.datasheet_path)
    _validate_document_url(absolute_url, "datasheet_url")

    return DatasheetSource(
        product_identity=product_identity,
        source_name=f"{discovery_source.source_name} Datasheet",
        source_url=absolute_url,
        source_authority=SourceAuthority.AUTHORITATIVE,
    )


# ---------------------------------------------------------------------------
# 6D Batch Execution — shared PDF fetch across product identities
# ---------------------------------------------------------------------------
# Grounded in frozen 7A ComparableCandidateDiscoveryResult.


@dataclass(frozen=True)
class BatchEnrichmentIdentityResult:
    """One identity's result within a batch enrichment run.

    Attributes
    ----------
    product_identity : ProductIdentity
        The identity this result is for.
    enrichment_result : SpecificationEnrichmentResult | None
        The enrichment result, or None if no datasheet was found.
    datasheet_source : DatasheetSource | None
        The derived datasheet source, or None if derivation failed.
    """

    product_identity: ProductIdentity
    enrichment_result: SpecificationEnrichmentResult | None
    datasheet_source: DatasheetSource | None


def enrich_enterprise_ssd_specifications_batch(
    *,
    identities: tuple[ProductIdentity, ...],
    discovery_result: ComparableCandidateDiscoveryResult,
    page_fetcher: PageFetcher,
    document_fetcher: DocumentFetcher,
) -> list[BatchEnrichmentIdentityResult]:
    """Batch-enrich specifications for multiple identities with shared fetching.

    This is the PUBLIC 6D batch authority-establishing operation.
    Grounded in a frozen 7A ComparableCandidateDiscoveryResult.

    Authority chain:
        frozen 7A ComparableCandidateDiscoveryResult
          -> EXTRACTED AUTHORITATIVE source outcomes
          -> deduplicated source descriptors (object identity preserved)
          -> support-page fetch (one per unique source)
          -> datasheet link derivation per identity
          -> deduplicated PDF fetch (one per unique URL)
          -> PDF parse (one per unique URL, fail-closed)
          -> per-identity observation extraction
          -> normalization, resolution, result

    Validates BEFORE any fetch:
        1. discovery_result is EXACTLY a ComparableCandidateDiscoveryResult
        2. Only EXTRACTED AUTHORITATIVE outcomes are used
        3. Exact frozen 7A source descriptor objects are preserved

    Pipeline:
        1. Validate discovery_result type
        2. Extract EXTRACTED source outcomes
        3. Deduplicate source descriptors (value equality, first-seen wins)
        4. Fetch each unique support page ONCE
        5. Derive datasheet links per identity
        6. Deduplicate datasheet URLs
        7. Fetch each unique PDF ONCE (SOURCE_REFUSED vs FETCH_FAILED tracked)
        8. Parse each unique PDF ONCE (fail-closed on parser exception)
        9. Extract per-identity observations from held PDF data
        10. Normalize, resolve, return per-identity results

    Parameters
    ----------
    identities : tuple of ProductIdentity
        Target identities to enrich (all must be established).
    discovery_result : ComparableCandidateDiscoveryResult
        Frozen 7A discovery result (exact type required).
    page_fetcher : PageFetcher
        Page acquisition protocol.
    document_fetcher : DocumentFetcher
        Document (PDF) acquisition protocol.

    Returns
    -------
    list[BatchEnrichmentIdentityResult]
        One result per identity (same order as input).

    Raises
    ------
    TypeError
        If discovery_result is not a ComparableCandidateDiscoveryResult.
    ValueError
        If inputs are invalid.
    """
    from product_intelligence.research.comparable_candidates import (
        ComparableCandidateSource,
    )

    # --- EXACT type check BEFORE any fetch ---
    if type(discovery_result) is not ComparableCandidateDiscoveryResult:
        raise TypeError(
            f"discovery_result must be a ComparableCandidateDiscoveryResult, got "
            f"{type(discovery_result).__name__}. "
            "Authority must be grounded in a frozen 7A discovery result."
        )

    # Validate identities
    if not isinstance(identities, tuple):
        raise TypeError("identities must be a tuple")
    for identity in identities:
        if not isinstance(identity, ProductIdentity):
            raise TypeError(
                f"identities must contain only ProductIdentity, got "
                f"{type(identity).__name__}"
            )
        if not identity.is_established:
            raise ValueError("All identities must be established")

    if not hasattr(page_fetcher, "fetch"):
        raise TypeError("page_fetcher must implement PageFetcher protocol")

    # ------------------------------------------------------------------
    # Step 1: Extract EXTRACTED source outcomes from discovery result
    # Only EXTRACTED outcomes may establish datasheet authority.
    # Deduplicate by source descriptor (value equality, first-seen wins).
    # ------------------------------------------------------------------

    extracted_7a_outcomes = [
        outcome
        for outcome in discovery_result.source_outcomes
        if outcome.outcome_state is DiscoverySourceOutcomeState.EXTRACTED
    ]

    # Deduplicate source descriptors — ComparableCandidateSource is frozen
    # dataclass so value equality = structural equality.
    seen_sources: dict[ComparableCandidateSource, ComparableCandidateSourceOutcome] = {}
    for outcome in extracted_7a_outcomes:
        source = outcome.source
        if source not in seen_sources:
            seen_sources[source] = outcome

    # ------------------------------------------------------------------
    # Step 2: Fetch each unique EXTRACTED support page ONCE
    # Map: source -> (body_text, final_url, retrieved_at)
    # ------------------------------------------------------------------

    fetched_support_pages: dict[ComparableCandidateSource, tuple[str, str, datetime]] = {}

    for source in seen_sources:
        try:
            fetch_request = PageFetchRequest(url=source.source_url)
            fetched_page = page_fetcher.fetch(fetch_request)
            fetched_support_pages[source] = (
                fetched_page.body_text,
                fetched_page.final_url,
                fetched_page.retrieved_at,
            )
        except UnsafeFetchTargetError:
            pass
        except PageFetchError:
            pass

    # ------------------------------------------------------------------
    # Step 3: For each identity, derive datasheet sources
    # ------------------------------------------------------------------

    identity_sources: dict[ProductIdentity, list[DatasheetSource]] = {}

    for identity in identities:
        sources_for_identity: list[DatasheetSource] = []
        sku_number = identity.manufacturer_part_number
        if not sku_number:
            identity_sources[identity] = []
            continue

        for source in seen_sources:
            if source not in fetched_support_pages:
                continue

            body_text, final_url, retrieved_at = fetched_support_pages[source]

            try:
                link = extract_datasheet_link(
                    document=body_text,
                    sku_number=sku_number,
                )
            except ValueError:
                raise

            if link is None:
                continue

            absolute_url = urljoin(final_url, link.datasheet_path)
            _validate_document_url(absolute_url, "datasheet_url")

            datasheet_source = DatasheetSource(
                product_identity=identity,
                source_name=f"{source.source_name} Datasheet",
                source_url=absolute_url,
                source_authority=SourceAuthority.AUTHORITATIVE,
            )
            sources_for_identity.append(datasheet_source)

        identity_sources[identity] = sources_for_identity

    # ------------------------------------------------------------------
    # Step 4: Deduplicate datasheet URLs across all identities
    # ------------------------------------------------------------------

    url_to_identities: dict[str, set[ProductIdentity]] = {}
    url_to_source: dict[str, DatasheetSource] = {}

    for identity, sources in identity_sources.items():
        for source in sources:
            url = source.source_url
            if url not in url_to_identities:
                url_to_identities[url] = set()
                url_to_source[url] = source
            url_to_identities[url].add(identity)

    # ------------------------------------------------------------------
    # Step 5: Fetch each unique PDF ONCE
    # Track acquisition state: SOURCE_REFUSED vs FETCH_FAILED vs FETCHED
    # ------------------------------------------------------------------

    class _PdfAcquisitionState:
        __slots__ = ("state", "fetched_doc")
        state: DatasheetOutcomeState
        fetched_doc: FetchedDocument | None

        def __init__(self):
            self.state = DatasheetOutcomeState.FETCH_FAILED
            self.fetched_doc = None

    pdf_acquisition: dict[str, _PdfAcquisitionState] = {}

    for url in url_to_identities:
        acq = _PdfAcquisitionState()
        try:
            fetch_request = DocumentFetchRequest(url=url)
            fetched = document_fetcher.fetch(fetch_request)
            acq.state = DatasheetOutcomeState.ENRICHED  # tentative, may change to PARSE_FAILED
            acq.fetched_doc = fetched
        except UnsafeDocumentTargetError:
            acq.state = DatasheetOutcomeState.SOURCE_REFUSED
        except DocumentFetchError:
            acq.state = DatasheetOutcomeState.FETCH_FAILED
        pdf_acquisition[url] = acq

    # ------------------------------------------------------------------
    # Step 6: Parse each unique PDF ONCE (fail-closed)
    # On parser exception: discard ALL tables, mark PARSE_FAILED
    # ------------------------------------------------------------------

    parsed_tables: dict[str, list[tuple[int, int, list[list[str | None]]]]] = {}

    for url in url_to_identities:
        acq = pdf_acquisition[url]
        if acq.state not in (DatasheetOutcomeState.ENRICHED,):
            # Not fetched — skip parsing
            continue
        if acq.fetched_doc is None:
            continue

        pdf = None
        try:
            import io
            pdf = pdfplumber.open(io.BytesIO(acq.fetched_doc.body_bytes))

            all_tables: list[tuple[int, int, list[list[str | None]]]] = []
            for page_idx, page in enumerate(pdf.pages):
                tables = page.extract_tables()
                if not tables:
                    continue
                for table_idx, table in enumerate(tables):
                    if not table:
                        continue
                    all_tables.append((page_idx, table_idx, table))

            # All pages parsed successfully — store tables
            parsed_tables[url] = all_tables

        except Exception as exc:
            if _is_pdf_parser_exception(exc):
                # Parser exception — discard ALL tables for this URL
                # Mark as PARSE_FAILED
                parsed_tables[url] = []  # explicitly empty
                acq.state = DatasheetOutcomeState.PARSE_FAILED
            else:
                # Programming exception — propagate
                raise
        finally:
            if pdf is not None:
                pdf.close()

    # ------------------------------------------------------------------
    # Step 7: Extract per-identity observations from held PDF data
    # ------------------------------------------------------------------

    results: list[BatchEnrichmentIdentityResult] = []

    for identity in identities:
        sources = identity_sources.get(identity, [])
        if not sources:
            results.append(
                BatchEnrichmentIdentityResult(
                    product_identity=identity,
                    enrichment_result=None,
                    datasheet_source=None,
                )
            )
            continue

        all_raw_observations: list[SpecificationObservation] = []
        source_outcomes: list[DatasheetSourceOutcome] = []

        for source in sources:
            url = source.source_url
            acq = pdf_acquisition.get(url)

            if acq is None or acq.state is DatasheetOutcomeState.SOURCE_REFUSED:
                # PDF was refused
                source_outcomes.append(
                    DatasheetSourceOutcome(
                        source=source,
                        final_url=None,
                        retrieved_at=None,
                        outcome_state=DatasheetOutcomeState.SOURCE_REFUSED,
                        observation_count=0,
                    )
                )
                continue
            if acq is None or acq.state is DatasheetOutcomeState.FETCH_FAILED:
                # PDF fetch failed
                source_outcomes.append(
                    DatasheetSourceOutcome(
                        source=source,
                        final_url=None,
                        retrieved_at=None,
                        outcome_state=DatasheetOutcomeState.FETCH_FAILED,
                        observation_count=0,
                    )
                )
                continue
            if acq.state is DatasheetOutcomeState.PARSE_FAILED:
                # PDF parse failed — fail-closed
                source_outcomes.append(
                    DatasheetSourceOutcome(
                        source=source,
                        final_url=acq.fetched_doc.final_url if acq.fetched_doc else None,
                        retrieved_at=acq.fetched_doc.retrieved_at if acq.fetched_doc else None,
                        outcome_state=DatasheetOutcomeState.PARSE_FAILED,
                        observation_count=0,
                    )
                )
                continue

            # PDF was successfully parsed
            tables = parsed_tables.get(url, [])
            if not tables:
                source_outcomes.append(
                    DatasheetSourceOutcome(
                        source=source,
                        final_url=acq.fetched_doc.final_url,
                        retrieved_at=acq.fetched_doc.retrieved_at,
                        outcome_state=DatasheetOutcomeState.NO_OBSERVATIONS,
                        observation_count=0,
                    )
                )
                continue

            # Extract observations from shared tables
            try:
                observations = extract_datasheet_observations_from_document(
                    product_identity=identity,
                    all_tables=tables,
                    source_name=source.source_name,
                    source_url=acq.fetched_doc.final_url,
                    retrieved_at=acq.fetched_doc.retrieved_at,
                    source_authority=source.source_authority,
                )
            except ValueError:
                raise
            except Exception as exc:
                if _is_pdf_parser_exception(exc):
                    source_outcomes.append(
                        DatasheetSourceOutcome(
                            source=source,
                            final_url=acq.fetched_doc.final_url,
                            retrieved_at=acq.fetched_doc.retrieved_at,
                            outcome_state=DatasheetOutcomeState.PARSE_FAILED,
                            observation_count=0,
                        )
                    )
                    continue
                raise

            all_raw_observations.extend(observations)

            if observations:
                outcome_state = DatasheetOutcomeState.ENRICHED
            else:
                outcome_state = DatasheetOutcomeState.NO_OBSERVATIONS

            source_outcomes.append(
                DatasheetSourceOutcome(
                    source=source,
                    final_url=acq.fetched_doc.final_url,
                    retrieved_at=acq.fetched_doc.retrieved_at,
                    outcome_state=outcome_state,
                    observation_count=len(observations),
                )
            )

        # Normalize via frozen 6B
        normalized_observations: list[NormalizedSpecificationObservation] = []
        for obs in all_raw_observations:
            normalized = normalize_enterprise_ssd_observation(obs)
            normalized_observations.append(normalized)

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
            resolution = resolve_specification(identity, definition, obs_tuple)
            resolutions[key] = resolution

        # Build complete ProductSpecificationSet
        product_specification_set = ProductSpecificationSet(
            product_identity=identity,
            category_schema=ENTERPRISE_SSD_SCHEMA,
            resolutions=resolutions,
        )

        # Build self-validating result
        enrichment_result = SpecificationEnrichmentResult(
            product_identity=identity,
            source_outcomes=tuple(source_outcomes),
            raw_observations=tuple(all_raw_observations),
            normalized_observations=tuple(normalized_observations),
            product_specification_set=product_specification_set,
        )

        results.append(
            BatchEnrichmentIdentityResult(
                product_identity=identity,
                enrichment_result=enrichment_result,
                datasheet_source=sources[0] if sources else None,
            )
        )

    return results
