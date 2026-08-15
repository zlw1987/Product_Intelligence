"""Core domain contracts.

Plain frozen dataclasses, standard library only. No modelling framework is
introduced at this phase: these types carry no persistence, serialization, or
transport concerns.

Scope note (PRODUCT-INTEL.0A): these are contracts plus contract-level
validation. Part-number normalization, identity matching, evidence
collection, price aggregation, and persistence are later phases and are
intentionally absent.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from product_intelligence.domain.enums import (
    ESTABLISHED_MATCH_TYPES,
    ConfidenceLevel,
    EvidenceDecision,
    IdentityMatchType,
)
from product_intelligence.domain.errors import DomainValidationError


def _require_text(value: object, field_name: str) -> str:
    """Return ``value`` stripped of surrounding whitespace, or raise."""
    if not isinstance(value, str):
        raise DomainValidationError(
            f"{field_name} must be a string, got {type(value).__name__}"
        )
    return value.strip()


def _optional_text(value: object, field_name: str) -> str | None:
    """Normalize an optional text field.

    Surrounding whitespace is stripped; a value that is empty afterwards
    becomes ``None``. Absent information stays absent — nothing is inferred
    or substituted.
    """
    if value is None:
        return None
    return _require_text(value, field_name) or None


@dataclass(frozen=True)
class ResearchRequest:
    """The canonical research input, independent of how it arrived.

    Every intake mechanism — the standalone web form, a structured API, a
    legacy desktop launcher passing plain URL parameters, a batch process, or
    any future calling system — normalizes into this same object. The research
    core cannot tell which one produced it, and must never be able to.

    Caller identity, transport details, request encoding, and audit metadata
    are deliberately *not* fields here. If a later phase needs them, they
    belong to the intake/application boundary that wraps this request, not to
    the product's identity.

    Contract:

    * Both fields are strings; surrounding whitespace is stripped.
    * At least one of the two must be non-empty after stripping.
    * A part number alone is valid.
    * A description alone is valid (it may only ever support a
      description-level answer, which is a research outcome, not an error).
    * Nothing is inferred, looked up, or filled in.
    """

    manufacturer_part_number: str
    description: str

    def __post_init__(self) -> None:
        mpn = _require_text(self.manufacturer_part_number, "manufacturer_part_number")
        description = _require_text(self.description, "description")

        if not mpn and not description:
            raise DomainValidationError(
                "A research request requires at least a manufacturer part "
                "number or a description; both were empty."
            )

        object.__setattr__(self, "manufacturer_part_number", mpn)
        object.__setattr__(self, "description", description)

    @property
    def has_manufacturer_part_number(self) -> bool:
        return bool(self.manufacturer_part_number)

    @property
    def has_description(self) -> bool:
        return bool(self.description)


@dataclass(frozen=True)
class ProductIdentity:
    """What the system believes the requested product actually is.

    Every descriptive field is optional and defaults to ``None``. An unknown
    manufacturer stays unknown: the system does not guess one, and an empty
    string is normalized to ``None`` rather than presented as a fact.

    ``normalized_part_number`` is a slot for the output of a deterministic
    normalization step. That normalization is not implemented in this phase,
    so the field is only ever what a caller explicitly supplies.

    ``match_type`` and ``confidence`` both default to UNKNOWN: an identity is
    unestablished until evidence establishes it.

    Structural invariant: **an established identity must carry the part-number
    evidence its match type claims.**

    * ``EXACT`` requires a ``manufacturer_part_number``. A match asserted to be
      character-for-character against nothing is not a weak match, it is an
      impossible one.
    * ``NORMALIZED_EXACT`` requires both a ``manufacturer_part_number`` and the
      ``normalized_part_number`` that actually did the matching. Recording the
      normalized form is what distinguishes this from ``EXACT``, so an identity
      claiming it without one is likewise impossible.

    This is a structural rule about what an identity may *represent*; it is not
    matching. Nothing here compares part numbers, normalizes one, or decides a
    match type — those belong to the deterministic identity model (2A) and the
    matching phase (3C). The weaker match types are deliberately unconstrained:
    ``DESCRIPTION_ONLY`` in particular means no part-number evidence exists.
    """

    manufacturer: str | None = None
    manufacturer_part_number: str | None = None
    normalized_part_number: str | None = None
    product_name: str | None = None
    product_family: str | None = None
    category: str | None = None
    match_type: IdentityMatchType = IdentityMatchType.UNKNOWN
    confidence: ConfidenceLevel = ConfidenceLevel.UNKNOWN

    def __post_init__(self) -> None:
        for name in (
            "manufacturer",
            "manufacturer_part_number",
            "normalized_part_number",
            "product_name",
            "product_family",
            "category",
        ):
            object.__setattr__(self, name, _optional_text(getattr(self, name), name))

        if not isinstance(self.match_type, IdentityMatchType):
            raise DomainValidationError("match_type must be an IdentityMatchType")
        if not isinstance(self.confidence, ConfidenceLevel):
            raise DomainValidationError("confidence must be a ConfidenceLevel")

        if self.match_type in ESTABLISHED_MATCH_TYPES:
            if self.manufacturer_part_number is None:
                raise DomainValidationError(
                    f"an identity claiming {self.match_type.value} requires a "
                    "manufacturer_part_number; a part-number-level match cannot "
                    "be established without a part number"
                )
            if (
                self.match_type is IdentityMatchType.NORMALIZED_EXACT
                and self.normalized_part_number is None
            ):
                raise DomainValidationError(
                    "an identity claiming NORMALIZED_EXACT requires a "
                    "normalized_part_number; the normalized form is what "
                    "distinguishes this match type from EXACT"
                )

    @property
    def is_established(self) -> bool:
        """True only for a part-number-level match, exact or normalized.

        Construction enforces the evidence this reports, so a ``True`` here
        always implies a present ``manufacturer_part_number`` — the property
        reads the invariant rather than compensating for its absence.
        """
        return self.match_type in ESTABLISHED_MATCH_TYPES


@dataclass(frozen=True)
class EvidenceReference:
    """A single attributable observation behind a conclusion.

    Evidence-first rule: a market price or product fact the system reports
    must be traceable to one of these. Both accepted and rejected evidence is
    retained, and a rejection must say why.

    ``source`` is a free-form identifier for wherever the observation came
    from. It is intentionally a string and not a fixed set of values: the
    domain must not enumerate, or otherwise encode knowledge of, specific
    external vendors.

    ``retrieved_at`` must be timezone-aware. The domain never generates a
    timestamp itself, so callers stay in control of time and tests stay
    deterministic.
    """

    source: str
    retrieved_at: datetime
    source_url: str | None = None
    raw_reference: str | None = None
    normalized_value: str | None = None
    decision: EvidenceDecision = EvidenceDecision.UNDECIDED
    reason: str | None = None
    confidence: ConfidenceLevel = ConfidenceLevel.UNKNOWN

    def __post_init__(self) -> None:
        source = _require_text(self.source, "source")
        if not source:
            raise DomainValidationError("Evidence requires a non-empty source")
        object.__setattr__(self, "source", source)

        if not isinstance(self.retrieved_at, datetime):
            raise DomainValidationError("retrieved_at must be a datetime")
        if self.retrieved_at.tzinfo is None or (
            self.retrieved_at.utcoffset() is None
        ):
            raise DomainValidationError("retrieved_at must be timezone-aware")

        for name in ("source_url", "raw_reference", "normalized_value", "reason"):
            object.__setattr__(self, name, _optional_text(getattr(self, name), name))

        if not isinstance(self.decision, EvidenceDecision):
            raise DomainValidationError("decision must be an EvidenceDecision")
        if not isinstance(self.confidence, ConfidenceLevel):
            raise DomainValidationError("confidence must be a ConfidenceLevel")

        if self.decision is EvidenceDecision.REJECTED and not self.reason:
            raise DomainValidationError("Rejected evidence requires a reason")
