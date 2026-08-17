"""Read-only evaluation case objects.

Frozen dataclasses with tuple collections, so a loaded corpus cannot be edited
in place by whatever is measuring itself against it. All validation lives in
``validation.py``: these types are what a validated case *is*, and they are
constructed only by that module (or by a test constructing a case on purpose).

Nothing here resolves, matches, normalizes, or scores anything.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from types import MappingProxyType
from typing import Iterable, Mapping

from product_intelligence.domain import ResearchRequest
from product_intelligence.evaluation.vocabulary import (
    CaseKind,
    ChallengeTag,
    ExpectedResolution,
    ProvenanceKind,
)


@dataclass(frozen=True)
class CaseInput:
    """Exactly what a caller would supply: a part number and a description.

    Stored **verbatim**, including surrounding whitespace. That is not sloppy
    corpus hygiene — whitespace tolerance is itself a challenge class, and a
    corpus that pre-cleaned its inputs could not test it. Normalization is the
    job of the system under evaluation, and ``as_research_request`` is where it
    happens, through the real domain contract.
    """

    manufacturer_part_number: str
    description: str

    def as_research_request(self) -> ResearchRequest:
        """Return this input as the canonical request the core would receive."""
        return ResearchRequest(
            manufacturer_part_number=self.manufacturer_part_number,
            description=self.description,
        )


@dataclass(frozen=True)
class Expectation:
    """What a correct answer looks like for one case.

    Records truth, never implementation. There is deliberately no field for a
    required query, provider, prompt, ranking, similarity threshold, or numeric
    confidence: those are later phases' decisions, and a benchmark that
    pre-decided them would measure obedience rather than correctness.

    ``manufacturer`` and ``canonical_manufacturer_part_number`` are present only
    when ``resolution`` is ``EXACT_IDENTITY``. For the abstaining resolutions,
    claiming a canonical identity would contradict the expectation itself, so
    validation forbids it and requires ``reason`` instead.

    ``must_not_resolve_to`` lists canonical part numbers that must not be
    **reported as this request's resolved identity**. It does not forbid
    surfacing them as candidates or as evidence — a near-miss part number that a
    report shows and explicitly rejects is the desired behaviour; the same part
    number presented as the answer is the failure.
    """

    resolution: ExpectedResolution
    manufacturer: str | None = None
    canonical_manufacturer_part_number: str | None = None
    product_name: str | None = None
    product_family: str | None = None
    must_not_resolve_to: tuple[str, ...] = ()
    reason: str | None = None

    @property
    def requires_abstention(self) -> bool:
        """True when no single identity may be presented as settled."""
        return self.resolution is not ExpectedResolution.EXACT_IDENTITY


@dataclass(frozen=True)
class AuthoritativeProvenance:
    """Why a REAL_VERIFIED expected identity is trusted.

    ``source_url`` is **data**. The loader, the validator, and the tests never
    fetch it: a benchmark that needed the network to load would be neither
    deterministic nor durable, and a page that has changed must be re-reviewed
    by a person, not silently re-scraped.
    """

    kind: ProvenanceKind
    source_name: str
    source_url: str
    verification_note: str
    verified_on: date


@dataclass(frozen=True)
class SyntheticProvenance:
    """How and why a synthetic case was constructed.

    It has no source fields by construction. ``derived_from_case_ids`` records
    which real cases a mutation was built from, so a reviewer can see that (for
    example) a near-miss part number is a deliberate one-character edit of a
    verified identity rather than a product someone believed in.
    """

    kind: ProvenanceKind
    construction: str
    derived_from_case_ids: tuple[str, ...] = ()


@dataclass(frozen=True)
class EvaluationCase:
    """One evaluation case: an input, the expected class of answer, and why."""

    case_id: str
    case_kind: CaseKind
    input: CaseInput
    expectation: Expectation
    challenge_tags: tuple[ChallengeTag, ...]
    provenance: AuthoritativeProvenance | SyntheticProvenance
    notes: str | None = None
    deliberately_shares_identity: bool = False
    """Set only when a real case intentionally repeats another's identity.

    Two REAL_VERIFIED cases expecting the same canonical part number is usually
    an accident — a seed added twice. Requiring the flag makes the intentional
    version explicit rather than indistinguishable from the mistake.
    """

    @property
    def is_real_verified(self) -> bool:
        return self.case_kind is CaseKind.REAL_VERIFIED

    @property
    def is_synthetic(self) -> bool:
        return self.case_kind is CaseKind.SYNTHETIC

    def has_challenge_tag(self, tag: ChallengeTag) -> bool:
        return tag in self.challenge_tags


@dataclass(frozen=True)
class EvaluationCorpus:
    """An immutable collection of validated cases with a read-only index."""

    cases: tuple[EvaluationCase, ...]
    _by_id: Mapping[str, EvaluationCase] = field(
        init=False, repr=False, compare=False, default_factory=dict
    )

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "_by_id",
            MappingProxyType({case.case_id: case for case in self.cases}),
        )

    def __len__(self) -> int:
        return len(self.cases)

    def __iter__(self) -> Iterable[EvaluationCase]:
        return iter(self.cases)

    @property
    def by_id(self) -> Mapping[str, EvaluationCase]:
        """Read-only ``case_id`` -> case mapping."""
        return self._by_id

    def case(self, case_id: str) -> EvaluationCase:
        """Return one case by id, or raise ``KeyError``."""
        return self._by_id[case_id]

    @property
    def real_verified(self) -> tuple[EvaluationCase, ...]:
        return tuple(case for case in self.cases if case.is_real_verified)

    @property
    def synthetic(self) -> tuple[EvaluationCase, ...]:
        return tuple(case for case in self.cases if case.is_synthetic)

    def with_challenge_tag(self, tag: ChallengeTag) -> tuple[EvaluationCase, ...]:
        return tuple(case for case in self.cases if case.has_challenge_tag(tag))

    def with_resolution(
        self, resolution: ExpectedResolution
    ) -> tuple[EvaluationCase, ...]:
        return tuple(
            case for case in self.cases if case.expectation.resolution is resolution
        )

    def challenge_tag_counts(
        self, cases: Iterable[EvaluationCase] | None = None
    ) -> Mapping[ChallengeTag, int]:
        """Read-only tag -> case count, over ``cases`` or the whole corpus."""
        population = self.cases if cases is None else tuple(cases)
        counts = {tag: 0 for tag in ChallengeTag}
        for case in population:
            for tag in case.challenge_tags:
                counts[tag] += 1
        return MappingProxyType(counts)
