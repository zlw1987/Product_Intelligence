"""Comparable-product candidate discovery contracts (PRODUCT-INTEL.7A).

Pure research layer: defines the immutable data contracts for candidate
product discovery from approved manufacturer-catalog sources.

This module owns:
    ComparableCandidateObservation    one raw catalog record
    ComparableCandidateSource         one approved source descriptor
    CandidateDisposition              CANDIDATE / TARGET_SELF
    ComparableCandidateAssessment     one observation assessed vs target
    ComparableCandidate               one distinct deduplicated candidate

These types are Django-free, provider-free, and perform no I/O. They carry
no score, no rank, no similarity, no compatibility, and no recommendation.

A CANDIDATE means only: a distinct product identity discovered from accepted
source evidence and eligible to proceed to later similarity research (7B+).

Candidate != comparable.  7B decides comparability.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from urllib.parse import urlsplit

from product_intelligence.domain.models import ProductIdentity
from product_intelligence.research.identity import (
    compare_part_numbers,
    normalize_part_number,
)
from product_intelligence.research.specifications import SourceAuthority


#: The only schemes a fetchable URL may use (stdlib check, mirrors providers.page).
_FETCHABLE_SCHEMES: frozenset[str] = frozenset({"http", "https"})


def _require_fetchable_url(value: object, field_name: str = "url") -> str:
    """Return an absolute, credential-free http(s) URL, or raise ValueError.

    Stdlib-only mirror of the providers.page contract, so the research
    layer stays provider-free while enforcing the same URL rules.
    """
    if not isinstance(value, str):
        raise TypeError(f"{field_name} must be a string, got {type(value).__name__}")
    text = value.strip()
    if not text:
        raise ValueError(f"{field_name} is required; there is nothing to fetch")

    parts = urlsplit(text)
    if parts.scheme.lower() not in _FETCHABLE_SCHEMES:
        raise ValueError(
            f"{field_name} must be an absolute http:// or https:// URL, got {text!r}"
        )
    if not parts.hostname:
        raise ValueError(f"{field_name} must include a host, got {text!r}")
    if parts.username is not None or parts.password is not None:
        raise ValueError(
            f"{field_name} must not embed credentials; a fetch target carries no "
            "authentication"
        )
    return text


# ---------------------------------------------------------------------------
# Candidate disposition
# ---------------------------------------------------------------------------


class CandidateDisposition(str, Enum):
    """Disposition of one candidate observation relative to the target.

    CANDIDATE — a distinct product identity eligible for later comparison.
    TARGET_SELF — the observation is the target product itself (excluded).
    """

    CANDIDATE = "CANDIDATE"
    TARGET_SELF = "TARGET_SELF"


# ---------------------------------------------------------------------------
# ComparableCandidateSource — approved source descriptor
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class ComparableCandidateSource:
    """One explicitly approved manufacturer-catalog candidate source.

    Source authority is supplied explicitly, never inferred from hostname,
    URL structure, or document content.

    The source_url is validated structurally (absolute http(s), host present,
    no credentials) at construction.
    """

    source_name: str
    source_url: str
    source_authority: SourceAuthority

    def __post_init__(self) -> None:
        # Source name
        if not isinstance(self.source_name, str) or not self.source_name.strip():
            raise ValueError("source_name must be a non-empty string")
        object.__setattr__(self, "source_name", self.source_name.strip())

        # Source URL — validated structurally (stdlib only)
        object.__setattr__(
            self,
            "source_url",
            _require_fetchable_url(self.source_url, "source_url"),
        )

        # Source authority must be exact enum type
        if not isinstance(self.source_authority, SourceAuthority):
            raise TypeError(
                f"source_authority must be a SourceAuthority, got "
                f"{type(self.source_authority).__name__}"
            )


# ---------------------------------------------------------------------------
# ComparableCandidateObservation — one raw catalog record
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class ComparableCandidateObservation:
    """One raw manufacturer-catalog product record.

    Represents exactly one catalog row extracted from one approved source
    at one point in time. Preserves source-published text verbatim.

    manufacturer_part_number_raw is the exact source-published MPN text.
    It is NOT normalized in this type — normalization is a later assessment step.

    product_name_raw is the exact source-published title when present.
    It is never used as identity authority.

    No score, no rank, no similarity, no compatibility fields.
    """

    manufacturer_part_number_raw: str
    product_name_raw: str | None
    source_name: str
    source_url: str
    retrieved_at: datetime
    source_authority: SourceAuthority
    raw_reference: str | None = None

    def __post_init__(self) -> None:
        # manufacturer_part_number_raw — exact source text, preserved verbatim.
        # Validate with strip (must be non-empty after stripping) but
        # store the exact original string.
        if not isinstance(self.manufacturer_part_number_raw, str):
            raise TypeError(
                f"manufacturer_part_number_raw must be a string, got "
                f"{type(self.manufacturer_part_number_raw).__name__}"
            )
        if not self.manufacturer_part_number_raw.strip():
            raise ValueError(
                "manufacturer_part_number_raw must not be empty; "
                "a candidate observation requires a part number"
            )
        # Do NOT strip — preserve exact source text

        # product_name_raw — exact source text, optional.
        # If source field is a string, preserve the exact string as published.
        # If absent / not a string, store None.
        if self.product_name_raw is not None:
            if not isinstance(self.product_name_raw, str):
                raise TypeError(
                    f"product_name_raw must be a string or None, got "
                    f"{type(self.product_name_raw).__name__}"
                )
            # Do NOT strip — preserve exact source text

        # source_name
        if not isinstance(self.source_name, str) or not self.source_name.strip():
            raise ValueError("source_name must be a non-empty string")
        object.__setattr__(self, "source_name", self.source_name.strip())

        # source_url — validated through existing fetchable-URL contract (stdlib)
        object.__setattr__(
            self,
            "source_url",
            _require_fetchable_url(self.source_url, "source_url"),
        )

        # retrieved_at — timezone-aware
        if not isinstance(self.retrieved_at, datetime):
            raise TypeError(
                f"retrieved_at must be a datetime, got "
                f"{type(self.retrieved_at).__name__}"
            )
        if self.retrieved_at.tzinfo is None or self.retrieved_at.utcoffset() is None:
            raise ValueError("retrieved_at must be timezone-aware")

        # source_authority
        if not isinstance(self.source_authority, SourceAuthority):
            raise TypeError(
                f"source_authority must be a SourceAuthority, got "
                f"{type(self.source_authority).__name__}"
            )

        # raw_reference — optional, bounded provenance
        if self.raw_reference is not None:
            if not isinstance(self.raw_reference, str):
                raise TypeError(
                    f"raw_reference must be a string or None, got "
                    f"{type(self.raw_reference).__name__}"
                )
            stripped = self.raw_reference.strip()
            object.__setattr__(self, "raw_reference", stripped if stripped else None)


# ---------------------------------------------------------------------------
# ComparableCandidateAssessment — one observation assessed vs target
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class ComparableCandidateAssessment:
    """One candidate observation assessed against an established target identity.

    Disposition is mechanically derived from frozen 2A compare_part_numbers():
        EXACT or NORMALIZED_EXACT -> TARGET_SELF
        anything else             -> CANDIDATE

    The assessment stores the exact target_identity so __post_init__ can
    re-derive disposition from target + observation, making it impossible
    to fabricate a CANDIDATE disposition for the target itself or vice versa.

    target_identity: the established ProductIdentity being compared against.
    observation: the raw catalog record being assessed.
    normalized_part_number: frozen 2A normalize_part_number(observation MPN).
    disposition: CANDIDATE or TARGET_SELF, derived from comparison.
    """

    target_identity: ProductIdentity
    observation: ComparableCandidateObservation
    normalized_part_number: str
    disposition: CandidateDisposition

    @staticmethod
    def build(
        target_identity: ProductIdentity,
        observation: ComparableCandidateObservation,
    ) -> ComparableCandidateAssessment:
        """Build an assessment by comparing observation against target identity.

        Uses frozen 2A compare_part_numbers() for target-self exclusion.
        Uses frozen 2A normalize_part_number() for the normalized key.

        Raises ValueError if target_identity is not established.
        Raises TypeError if inputs are wrong type.
        """
        if not type(target_identity) is ProductIdentity:
            raise TypeError(
                f"target_identity must be a ProductIdentity, got "
                f"{type(target_identity).__name__}"
            )
        if not target_identity.is_established:
            raise ValueError(
                "ComparableCandidateAssessment requires an established "
                f"ProductIdentity (match_type={target_identity.match_type.value})"
            )

        if not isinstance(observation, ComparableCandidateObservation):
            raise TypeError(
                f"observation must be a ComparableCandidateObservation, got "
                f"{type(observation).__name__}"
            )

        # Compute normalized key using frozen 2A
        normalized = normalize_part_number(
            observation.manufacturer_part_number_raw
        )

        if not normalized:
            raise ValueError(
                "Cannot assess a candidate observation whose MPN normalizes "
                "to an empty key; no part-number content to assess"
            )

        # Derive disposition using frozen 2A comparison
        from product_intelligence.domain.enums import IdentityMatchType

        comparison = compare_part_numbers(
            target_identity.manufacturer_part_number,
            observation.manufacturer_part_number_raw,
        )

        if comparison.match_type in (
            IdentityMatchType.EXACT,
            IdentityMatchType.NORMALIZED_EXACT,
        ):
            disposition = CandidateDisposition.TARGET_SELF
        else:
            disposition = CandidateDisposition.CANDIDATE

        return ComparableCandidateAssessment(
            target_identity=target_identity,
            observation=observation,
            normalized_part_number=normalized,
            disposition=disposition,
        )

    def __post_init__(self) -> None:
        # target_identity must be exact ProductIdentity type
        if not type(self.target_identity) is ProductIdentity:
            raise TypeError(
                f"target_identity must be a ProductIdentity, got "
                f"{type(self.target_identity).__name__}"
            )
        # target_identity must be established
        if not self.target_identity.is_established:
            raise ValueError(
                "ComparableCandidateAssessment requires an established "
                f"ProductIdentity (match_type={self.target_identity.match_type.value})"
            )

        # observation
        if not isinstance(self.observation, ComparableCandidateObservation):
            raise TypeError(
                f"observation must be a ComparableCandidateObservation, got "
                f"{type(self.observation).__name__}"
            )

        # normalized_part_number must be non-empty and self-consistent
        if not isinstance(self.normalized_part_number, str):
            raise TypeError(
                f"normalized_part_number must be a string, got "
                f"{type(self.normalized_part_number).__name__}"
            )
        if not self.normalized_part_number:
            raise ValueError(
                "normalized_part_number must not be empty; "
                "it must equal frozen normalize_part_number(observation.manufacturer_part_number_raw)"
            )

        # Self-consistency: normalized_part_number must match what frozen 2A produces
        expected_normalized = normalize_part_number(
            self.observation.manufacturer_part_number_raw
        )
        if self.normalized_part_number != expected_normalized:
            raise ValueError(
                f"normalized_part_number '{self.normalized_part_number}' does not "
                f"match frozen 2A normalize_part_number() output "
                f"'{expected_normalized}' for this observation's MPN"
            )

        # disposition
        if not isinstance(self.disposition, CandidateDisposition):
            raise TypeError(
                f"disposition must be a CandidateDisposition, got "
                f"{type(self.disposition).__name__}"
            )

        # Re-derive disposition from target_identity + observation
        from product_intelligence.domain.enums import IdentityMatchType

        comparison = compare_part_numbers(
            self.target_identity.manufacturer_part_number,
            self.observation.manufacturer_part_number_raw,
        )

        if comparison.match_type in (
            IdentityMatchType.EXACT,
            IdentityMatchType.NORMALIZED_EXACT,
        ):
            expected_disposition = CandidateDisposition.TARGET_SELF
        else:
            expected_disposition = CandidateDisposition.CANDIDATE

        if self.disposition is not expected_disposition:
            raise ValueError(
                f"ComparableCandidateAssessment disposition {self.disposition.value} "
                f"does not match the mechanically derived disposition "
                f"{expected_disposition.value} for target "
                f"'{self.target_identity.manufacturer_part_number}' vs observation "
                f"MPN '{self.observation.manufacturer_part_number_raw}'. "
                "Disposition must be derived from target + observation, not fabricated."
            )


# ---------------------------------------------------------------------------
# ComparableCandidate — one distinct deduplicated candidate identity
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class ComparableCandidate:
    """One distinct discovered product identity.

    Represents one candidate product that is NOT the target itself.
    Multiple authoritative observations that normalize to the same key
    merge into one candidate, preserving ALL evidence.

    manufacturer_part_number is a stable representative spelling from the
    first evidence occurrence.

    normalized_part_number MUST equal frozen normalize_part_number(...) and
    must be non-empty.

    Every evidence item normalizes to exactly the same normalized key.
    Every evidence item has disposition CANDIDATE (no TARGET_SELF).
    Evidence is non-empty.

    No score, no rank, no similarity, no compatibility fields.
    """

    manufacturer_part_number: str
    normalized_part_number: str
    evidence: tuple[ComparableCandidateAssessment, ...]

    def __post_init__(self) -> None:
        # manufacturer_part_number
        if not isinstance(self.manufacturer_part_number, str):
            raise TypeError(
                f"manufacturer_part_number must be a string, got "
                f"{type(self.manufacturer_part_number).__name__}"
            )
        if not self.manufacturer_part_number.strip():
            raise ValueError(
                "manufacturer_part_number must not be empty"
            )
        object.__setattr__(
            self,
            "manufacturer_part_number",
            self.manufacturer_part_number.strip(),
        )

        # normalized_part_number
        if not isinstance(self.normalized_part_number, str):
            raise TypeError(
                f"normalized_part_number must be a string, got "
                f"{type(self.normalized_part_number).__name__}"
            )
        if not self.normalized_part_number:
            raise ValueError(
                "normalized_part_number must not be empty"
            )

        # Self-derive normalized key from representative MPN
        expected_normalized = normalize_part_number(
            self.manufacturer_part_number
        )
        if self.normalized_part_number != expected_normalized:
            raise ValueError(
                f"normalized_part_number '{self.normalized_part_number}' does not "
                f"match frozen 2A normalize_part_number() output "
                f"'{expected_normalized}' for representative MPN"
            )

        # evidence must be a non-empty tuple
        if not isinstance(self.evidence, tuple):
            raise TypeError(
                f"evidence must be a tuple, got {type(self.evidence).__name__}"
            )
        if not self.evidence:
            raise ValueError(
                "ComparableCandidate requires non-empty evidence"
            )

        # Every evidence item must share the same target_identity
        canonical_target = self.evidence[0].target_identity
        for i, assessment in enumerate(self.evidence):
            if not isinstance(assessment, ComparableCandidateAssessment):
                raise TypeError(
                    f"evidence[{i}] must be a ComparableCandidateAssessment, got "
                    f"{type(assessment).__name__}"
                )
            if assessment.target_identity is not canonical_target:
                raise ValueError(
                    f"ComparableCandidate evidence[{i}] target_identity is not "
                    "the same object as the canonical target_identity from "
                    f"evidence[0]. All evidence in one candidate must bind "
                    "to the exact same target product identity."
                )

            # Every assessment must be CANDIDATE, never TARGET_SELF
            if assessment.disposition is not CandidateDisposition.CANDIDATE:
                raise ValueError(
                    f"ComparableCandidate evidence[{i}] has disposition "
                    f"{assessment.disposition.value}, but only CANDIDATE "
                    "assessments may appear in a candidate. "
                    "TARGET_SELF is excluded from candidate evidence."
                )

            # Every assessment must normalize to the same key
            if assessment.normalized_part_number != self.normalized_part_number:
                raise ValueError(
                    f"ComparableCandidate evidence[{i}] normalized key "
                    f"'{assessment.normalized_part_number}' does not match "
                    f"candidate key '{self.normalized_part_number}'. "
                    "All evidence must share the same normalized identity."
                )

            # Every evidence item must be from an AUTHORITATIVE source
            if assessment.observation.source_authority is not SourceAuthority.AUTHORITATIVE:
                raise ValueError(
                    f"ComparableCandidate evidence[{i}] source authority is "
                    f"{assessment.observation.source_authority.value}. "
                    "7A v1 accepts only AUTHORITATIVE candidate evidence."
                )

    @staticmethod
    def build(
        assessments: tuple[ComparableCandidateAssessment, ...],
    ) -> ComparableCandidate:
        """Build one ComparableCandidate from CANDIDATE assessments sharing a key.

        Takes assessments that have already been grouped by normalized key.
        The representative MPN is the manufacturer_part_number_raw from the
        first assessment (stable first-seen order).

        Raises ValueError if assessments is empty or contains TARGET_SELF.
        """
        if not assessments:
            raise ValueError("Cannot build a candidate from empty assessments")

        # Use first assessment as representative (stable order)
        representative = assessments[0]

        return ComparableCandidate(
            manufacturer_part_number=representative.observation.manufacturer_part_number_raw,
            normalized_part_number=representative.normalized_part_number,
            evidence=assessments,
        )


# ---------------------------------------------------------------------------
# Deduplication helper
# ---------------------------------------------------------------------------


def deduplicate_candidate_assessments(
    assessments: tuple[ComparableCandidateAssessment, ...],
) -> tuple[ComparableCandidate, ...]:
    """Group and deduplicate candidate assessments into distinct candidates.

    Deduplicates ONLY by frozen 2A normalized key. Does NOT merge by title,
    family, manufacturer string, URL, or any other field.

    Returns candidates in stable first-seen order (not ranking).
    Only CANDIDATE assessments are included; TARGET_SELF is excluded.

    Every piece of CANDIDATE evidence is preserved — duplicates are not
    discarded.

    Raises ValueError if assessments belonging to the same normalized key
    have different target_identity objects (cross-target evidence is
    not allowed within one candidate group).
    """
    from collections import OrderedDict

    # Group by normalized key, preserving first-seen order
    groups: dict[str, list[ComparableCandidateAssessment]] = OrderedDict()

    for assessment in assessments:
        if assessment.disposition is not CandidateDisposition.CANDIDATE:
            continue

        key = assessment.normalized_part_number
        if key not in groups:
            groups[key] = []
        else:
            # Cross-target check: all assessments for the same normalized
            # key must bind to the exact same target_identity object.
            canonical_target = groups[key][0].target_identity
            if assessment.target_identity is not canonical_target:
                raise ValueError(
                    f"Assessments with the same normalized key '{key}' "
                    "reference different target_identity objects. "
                    "Cross-target candidate evidence is not allowed."
                )
        groups[key].append(assessment)

    # Build one candidate per group
    candidates: list[ComparableCandidate] = []
    for key, group in groups.items():
        candidate = ComparableCandidate.build(tuple(group))
        candidates.append(candidate)

    return tuple(candidates)
