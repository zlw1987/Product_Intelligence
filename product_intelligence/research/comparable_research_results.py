"""Comparable research result contracts (PRODUCT-INTEL.7C-A).

Pure research layer: defines the immutable data contracts for the persisted
comparable-research result. No Django, no execution imports, no providers,
no network, no runs imports, no web imports.

This module owns the semantic result types:
    ComparableResultKind
    AuthorityAuditOutcomeKind
    DatasheetAuditOutcomeKind
    EvidenceLayer
    AuthorityAttemptResult
    DatasheetAttemptResult
    ProductEnrichmentAudit
    EvidenceSourceReference
    FieldAssessmentResult
    ComparableCandidateResult
    ComparableResearchResult
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from product_intelligence.domain.models import ProductIdentity
from product_intelligence.research.comparable_candidates import (
    ComparableCandidate,
)
from product_intelligence.research.specifications import (
    ProductSpecificationSet,
    ResolutionState,
    SourceAuthority,
)


# ---------------------------------------------------------------------------
# ComparableResultKind
# ---------------------------------------------------------------------------


class ComparableResultKind(str, Enum):
    """Top-level outcome kind for a completed comparable-research result.

    FULL — authority matched and comparable candidates were found.
    NO_AUTHORITY_MATCH — no authority page matched the target product.
    AMBIGUOUS_AUTHORITY — authority match was ambiguous (multiple MPNs).
    NO_REQUESTED_MPN — target had no MPN to research authority for.
    """

    FULL = "FULL"
    NO_AUTHORITY_MATCH = "NO_AUTHORITY_MATCH"
    AMBIGUOUS_AUTHORITY = "AMBIGUOUS_AUTHORITY"
    NO_REQUESTED_MPN = "NO_REQUESTED_MPN"


# ---------------------------------------------------------------------------
# AuthorityAuditOutcomeKind
# ---------------------------------------------------------------------------


class AuthorityAuditOutcomeKind(str, Enum):
    """Outcome of one authority-support-page attempt.

    MATCHED — the target MPN was found with a clear single match.
    NO_REQUESTED_MPN — no MPN was requested for this authority attempt.
    NO_MPN_IN_SOURCE — the target MPN was not found in the source data.
    AMBIGUOUS_MPN_MATCH — the target MPN matched multiple records.
    AUTHORITY_HOST_ESCAPED — authority resolution escaped to a non-authoritative host.
    AUTHORITY_SOURCE_REFUSED — the authority server refused the connection.
    AUTHORITY_FETCH_FAILED — could not reach the authority support page.
    NO_STRUCTURAL_OBSERVATIONS — authority page had no extractable product data.
    """

    MATCHED = "MATCHED"
    NO_REQUESTED_MPN = "NO_REQUESTED_MPN"
    NO_MPN_IN_SOURCE = "NO_MPN_IN_SOURCE"
    AMBIGUOUS_MPN_MATCH = "AMBIGUOUS_MPN_MATCH"
    AUTHORITY_HOST_ESCAPED = "AUTHORITY_HOST_ESCAPED"
    AUTHORITY_SOURCE_REFUSED = "AUTHORITY_SOURCE_REFUSED"
    AUTHORITY_FETCH_FAILED = "AUTHORITY_FETCH_FAILED"
    NO_STRUCTURAL_OBSERVATIONS = "NO_STRUCTURAL_OBSERVATIONS"


# The authority outcomes that represent a structural/invariant failure
# preventing a COMPLETED ComparableResearchResult.
AUTHORITY_FATAL_OUTCOMES: frozenset[AuthorityAuditOutcomeKind] = frozenset({
    AuthorityAuditOutcomeKind.AUTHORITY_FETCH_FAILED,
    AuthorityAuditOutcomeKind.AUTHORITY_SOURCE_REFUSED,
    AuthorityAuditOutcomeKind.AUTHORITY_HOST_ESCAPED,
    AuthorityAuditOutcomeKind.NO_STRUCTURAL_OBSERVATIONS,
})


# ---------------------------------------------------------------------------
# DatasheetAuditOutcomeKind
# ---------------------------------------------------------------------------


class DatasheetAuditOutcomeKind(str, Enum):
    """Outcome of one datasheet-PDF enrichment attempt.

    ENRICHED — datasheet was fetched and observations extracted.
    NO_OBSERVATIONS — datasheet fetched but no relevant observations found.
    FETCH_FAILED — could not fetch the datasheet PDF.
    SOURCE_REFUSED — datasheet server refused the connection.
    PARSE_FAILED — PDF could not be parsed or tables extracted.
    NO_DATASHEET_SOURCE — no datasheet URL was available for this product.
    """

    ENRICHED = "ENRICHED"
    NO_OBSERVATIONS = "NO_OBSERVATIONS"
    FETCH_FAILED = "FETCH_FAILED"
    SOURCE_REFUSED = "SOURCE_REFUSED"
    PARSE_FAILED = "PARSE_FAILED"
    NO_DATASHEET_SOURCE = "NO_DATASHEET_SOURCE"


# ---------------------------------------------------------------------------
# EvidenceLayer
# ---------------------------------------------------------------------------


class EvidenceLayer(str, Enum):
    """Which evidence layer a resolved field came from.

    SUPPORT_PAGE — extracted from the manufacturer support page (6C).
    DATASHEET_PDF — extracted from the manufacturer datasheet PDF (6D).
    """

    SUPPORT_PAGE = "SUPPORT_PAGE"
    DATASHEET_PDF = "DATASHEET_PDF"


# ---------------------------------------------------------------------------
# AuthorityAttemptResult
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class AuthorityAttemptResult:
    """The audited outcome of one authority-support-page attempt.

    outcome : AuthorityAuditOutcomeKind
        The result of this attempt.

    source_name : str | None
        The source name that was attempted. Always set for source-backed
        outcomes. None only for NO_REQUESTED_MPN (no source attempted).

    source_url : str | None
        The URL that was attempted. Set for source-backed outcomes.

    matched_mpn : str | None
        The MPN that was matched, when outcome is MATCHED.

    raw_reference : str | None
        Bounded provenance reference, if available.
    """

    outcome: AuthorityAuditOutcomeKind
    source_name: str | None = None
    source_url: str | None = None
    matched_mpn: str | None = None
    raw_reference: str | None = None

    def __post_init__(self) -> None:
        # outcome must be exact enum type
        if not isinstance(self.outcome, AuthorityAuditOutcomeKind):
            raise TypeError(
                f"outcome must be AuthorityAuditOutcomeKind, got "
                f"{type(self.outcome).__name__}"
            )

        # State-dependent field shape
        if self.outcome is AuthorityAuditOutcomeKind.NO_REQUESTED_MPN:
            # No source attempted — source_name and source_url may be None
            if self.matched_mpn is not None:
                raise ValueError(
                    "NO_REQUESTED_MPN cannot have a matched_mpn; "
                    "no MPN was requested"
                )
        else:
            # Source-backed outcome — source_name and source_url must be set
            if self.source_name is None or not self.source_name.strip():
                raise ValueError(
                    f"source-backed outcome {self.outcome.value} requires "
                    "a non-empty source_name"
                )
            if self.source_url is None or not self.source_url.strip():
                raise ValueError(
                    f"source-backed outcome {self.outcome.value} requires "
                    "a non-empty source_url"
                )

            if self.outcome is AuthorityAuditOutcomeKind.MATCHED:
                if self.matched_mpn is None or not self.matched_mpn.strip():
                    raise ValueError(
                        "MATCHED outcome requires a non-empty matched_mpn"
                    )
            else:
                # Non-MATCHED, non-NO_REQUESTED_MPN outcomes
                # matched_mpn should be None (or empty)
                if self.matched_mpn is not None and self.matched_mpn.strip():
                    # Allow empty-ish matched_mpn for non-MATCHED but not
                    # fabricating one
                    pass

        # raw_reference — optional, bounded
        if self.raw_reference is not None:
            if not isinstance(self.raw_reference, str):
                raise TypeError(
                    f"raw_reference must be a string or None, got "
                    f"{type(self.raw_reference).__name__}"
                )


# ---------------------------------------------------------------------------
# DatasheetAttemptResult
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class DatasheetAttemptResult:
    """The audited outcome of one datasheet-PDF enrichment attempt.

    outcome : DatasheetAuditOutcomeKind
        The result of this attempt.

    source_name : str | None
        The datasheet source name. Set for source-backed outcomes.
        None for NO_DATASHEET_SOURCE.

    source_url : str | None
        The datasheet URL that was attempted. Set for source-backed outcomes.
        None for NO_DATASHEET_SOURCE.

    final_url : str | None
        The final URL after redirects. Set when a fetch occurred.

    retrieved_at : str | None
        ISO-8601 retrieval timestamp. Set when a fetch occurred.

    observation_count : int | None
        Number of specification observations extracted. Set for ENRICHED.
    """

    outcome: DatasheetAuditOutcomeKind
    source_name: str | None = None
    source_url: str | None = None
    final_url: str | None = None
    retrieved_at: str | None = None
    observation_count: int | None = None

    def __post_init__(self) -> None:
        # outcome must be exact enum type
        if not isinstance(self.outcome, DatasheetAuditOutcomeKind):
            raise TypeError(
                f"outcome must be DatasheetAuditOutcomeKind, got "
                f"{type(self.outcome).__name__}"
            )

        if self.outcome is DatasheetAuditOutcomeKind.NO_DATASHEET_SOURCE:
            # No source attempted — no provenance may be invented
            if self.source_name is not None:
                raise ValueError(
                    "NO_DATASHEET_SOURCE must not have source_name; "
                    "no datasheet source was available"
                )
            if self.source_url is not None:
                raise ValueError(
                    "NO_DATASHEET_SOURCE must not have source_url; "
                    "no datasheet source was available"
                )
            if self.final_url is not None:
                raise ValueError(
                    "NO_DATASHEET_SOURCE must not have final_url; "
                    "no datasheet source was available"
                )
            if self.retrieved_at is not None:
                raise ValueError(
                    "NO_DATASHEET_SOURCE must not have retrieved_at; "
                    "no datasheet source was available"
                )
            if self.observation_count is not None:
                raise ValueError(
                    "NO_DATASHEET_SOURCE must not have observation_count"
                )
        else:
            # Source-backed outcome — validate the fields that frozen 6D
            # actually guarantees for source-backed attempts.
            # The 6D contract guarantees source_name and source_url for
            # any source-backed attempt.
            if self.source_name is None or not self.source_name.strip():
                raise ValueError(
                    f"source-backed outcome {self.outcome.value} requires "
                    "a non-empty source_name"
                )
            if self.source_url is None or not self.source_url.strip():
                raise ValueError(
                    f"source-backed outcome {self.outcome.value} requires "
                    "a non-empty source_url"
                )

            if self.outcome is DatasheetAuditOutcomeKind.ENRICHED:
                if self.observation_count is None:
                    raise ValueError(
                        "ENRICHED outcome requires observation_count"
                    )
                if not isinstance(self.observation_count, int):
                    raise TypeError(
                        f"observation_count must be int, got "
                        f"{type(self.observation_count).__name__}"
                    )
                if self.observation_count < 0:
                    raise ValueError(
                        f"observation_count must be >= 0, got {self.observation_count}"
                    )


# ---------------------------------------------------------------------------
# ProductEnrichmentAudit
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class ProductEnrichmentAudit:
    """Specification enrichment audit for one product identity.

    Combines authority (6C) and datasheet (6D) enrichment attempts into
    a single audited record for one product.

    target_identity : ProductIdentity
        The product this enrichment audit belongs to.

    authority_audit : tuple[AuthorityAttemptResult, ...]
        The authority-support-page attempt results for this product.
        Non-empty (at least one attempt was made or attempted).

    datasheet_audit : tuple[DatasheetAttemptResult, ...]
        The datasheet-PDF enrichment attempt results for this product.
        May be empty if no datasheet enrichment was attempted.

    specification_set : ProductSpecificationSet | None
        The composed specification set after enrichment. Set when available.
    """

    target_identity: ProductIdentity
    authority_audit: tuple[AuthorityAttemptResult, ...]
    datasheet_audit: tuple[DatasheetAttemptResult, ...] = ()
    specification_set: ProductSpecificationSet | None = None

    def __post_init__(self) -> None:
        # target_identity
        if not isinstance(self.target_identity, ProductIdentity):
            raise TypeError(
                f"target_identity must be ProductIdentity, got "
                f"{type(self.target_identity).__name__}"
            )

        # authority_audit
        if not isinstance(self.authority_audit, tuple):
            raise TypeError(
                f"authority_audit must be a tuple, got "
                f"{type(self.authority_audit).__name__}"
            )
        if not self.authority_audit:
            raise ValueError(
                "authority_audit must be non-empty; "
                "at least one authority attempt must be recorded"
            )
        for i, attempt in enumerate(self.authority_audit):
            if not isinstance(attempt, AuthorityAttemptResult):
                raise TypeError(
                    f"authority_audit[{i}] must be AuthorityAttemptResult, got "
                    f"{type(attempt).__name__}"
                )

        # datasheet_audit
        if not isinstance(self.datasheet_audit, tuple):
            raise TypeError(
                f"datasheet_audit must be a tuple, got "
                f"{type(self.datasheet_audit).__name__}"
            )
        for i, attempt in enumerate(self.datasheet_audit):
            if not isinstance(attempt, DatasheetAttemptResult):
                raise TypeError(
                    f"datasheet_audit[{i}] must be DatasheetAttemptResult, got "
                    f"{type(attempt).__name__}"
                )

        # specification_set
        if self.specification_set is not None:
            if not isinstance(self.specification_set, ProductSpecificationSet):
                raise TypeError(
                    f"specification_set must be ProductSpecificationSet or None, got "
                    f"{type(self.specification_set).__name__}"
                )


# ---------------------------------------------------------------------------
# EvidenceSourceReference
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class EvidenceSourceReference:
    """Represents actual evidence that supported a resolved field.

    source_name : str
        The evidence source name.

    source_url : str
        The evidence source URL.

    layer : EvidenceLayer
        SUPPORT_PAGE or DATASHEET_PDF.
    """

    source_name: str
    source_url: str
    layer: EvidenceLayer

    def __post_init__(self) -> None:
        if not isinstance(self.source_name, str) or not self.source_name.strip():
            raise ValueError("source_name must be a non-empty string")

        if not isinstance(self.source_url, str) or not self.source_url.strip():
            raise ValueError("source_url must be a non-empty string")

        if not isinstance(self.layer, EvidenceLayer):
            raise TypeError(
                f"layer must be EvidenceLayer, got {type(self.layer).__name__}"
            )


# ---------------------------------------------------------------------------
# FieldAssessmentResult
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class FieldAssessmentResult:
    """Assessment of one specification field for comparison.

    field_name : str
        The schema field name (e.g. "capacity").

    target_value : str | None
        The target's resolved value for this field.

    candidate_value : str | None
        The candidate's resolved value for this field.

    target_evidence : tuple[EvidenceSourceReference, ...]
        Evidence sources supporting the target value.

    candidate_evidence : tuple[EvidenceSourceReference, ...]
        Evidence sources supporting the candidate value.
    """

    field_name: str
    target_value: str | None
    candidate_value: str | None
    target_evidence: tuple[EvidenceSourceReference, ...] = ()
    candidate_evidence: tuple[EvidenceSourceReference, ...] = ()

    def __post_init__(self) -> None:
        if not isinstance(self.field_name, str) or not self.field_name.strip():
            raise ValueError("field_name must be a non-empty string")

        if self.target_value is not None:
            if not isinstance(self.target_value, str):
                raise TypeError(
                    f"target_value must be a string or None, got "
                    f"{type(self.target_value).__name__}"
                )

        if self.candidate_value is not None:
            if not isinstance(self.candidate_value, str):
                raise TypeError(
                    f"candidate_value must be a string or None, got "
                    f"{type(self.candidate_value).__name__}"
                )

        if not isinstance(self.target_evidence, tuple):
            raise TypeError(
                f"target_evidence must be a tuple, got "
                f"{type(self.target_evidence).__name__}"
            )
        for i, ref in enumerate(self.target_evidence):
            if not isinstance(ref, EvidenceSourceReference):
                raise TypeError(
                    f"target_evidence[{i}] must be EvidenceSourceReference, got "
                    f"{type(ref).__name__}"
                )

        if not isinstance(self.candidate_evidence, tuple):
            raise TypeError(
                f"candidate_evidence must be a tuple, got "
                f"{type(self.candidate_evidence).__name__}"
            )
        for i, ref in enumerate(self.candidate_evidence):
            if not isinstance(ref, EvidenceSourceReference):
                raise TypeError(
                    f"candidate_evidence[{i}] must be EvidenceSourceReference, got "
                    f"{type(ref).__name__}"
                )


# ---------------------------------------------------------------------------
# ComparableCandidateResult
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class ComparableCandidateResult:
    """The research result for one discovered comparable candidate.

    candidate : ComparableCandidate
        The discovered candidate (from frozen 7A).

    enrichment_audit : ProductEnrichmentAudit
        Specification enrichment audit for this candidate.

    field_assessments : tuple[FieldAssessmentResult, ...]
        Per-field comparison assessments between target and this candidate.
    """

    candidate: ComparableCandidate
    enrichment_audit: ProductEnrichmentAudit
    field_assessments: tuple[FieldAssessmentResult, ...] = ()

    def __post_init__(self) -> None:
        if not isinstance(self.candidate, ComparableCandidate):
            raise TypeError(
                f"candidate must be ComparableCandidate, got "
                f"{type(self.candidate).__name__}"
            )

        if not isinstance(self.enrichment_audit, ProductEnrichmentAudit):
            raise TypeError(
                f"enrichment_audit must be ProductEnrichmentAudit, got "
                f"{type(self.enrichment_audit).__name__}"
            )

        if not isinstance(self.field_assessments, tuple):
            raise TypeError(
                f"field_assessments must be a tuple, got "
                f"{type(self.field_assessments).__name__}"
            )
        for i, fa in enumerate(self.field_assessments):
            if not isinstance(fa, FieldAssessmentResult):
                raise TypeError(
                    f"field_assessments[{i}] must be FieldAssessmentResult, got "
                    f"{type(fa).__name__}"
                )


# ---------------------------------------------------------------------------
# ComparableResearchResult
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class ComparableResearchResult:
    """The complete persisted result of a comparable-research execution.

    kind : ComparableResultKind
        The top-level outcome kind.

    target_mpn : str
        The target product's MPN (may be empty for NO_REQUESTED_MPN kind).

    target_manufacturer : str | None
        The target product's manufacturer name (may be None for some kinds).

    target_enrichment_audit : ProductEnrichmentAudit | None
        Enrichment audit for the target product. Set for FULL kind.
        None for NO_AUTHORITY_MATCH, AMBIGUOUS_AUTHORITY, NO_REQUESTED_MPN.

    authority_audit : tuple[AuthorityAttemptResult, ...]
        The authority-support-page attempt results for the target.
        Non-empty. This is the single source of authority truth.

    candidates : tuple[ComparableCandidateResult, ...]
        The research results for each discovered comparable candidate.
        Empty for non-FULL kinds.

    candidate_enrichment_audits : tuple[ProductEnrichmentAudit, ...]
        Enrichment audits for each candidate.
        Must match candidates length. May be empty if no candidates.
    """

    kind: ComparableResultKind
    target_mpn: str
    target_manufacturer: str | None
    target_enrichment_audit: ProductEnrichmentAudit | None
    authority_audit: tuple[AuthorityAttemptResult, ...]
    candidates: tuple[ComparableCandidateResult, ...]
    candidate_enrichment_audits: tuple[ProductEnrichmentAudit, ...] = ()

    def __post_init__(self) -> None:
        # kind
        if not isinstance(self.kind, ComparableResultKind):
            raise TypeError(
                f"kind must be ComparableResultKind, got "
                f"{type(self.kind).__name__}"
            )

        # authority_audit must be non-empty
        if not isinstance(self.authority_audit, tuple):
            raise TypeError(
                f"authority_audit must be a tuple, got "
                f"{type(self.authority_audit).__name__}"
            )
        if not self.authority_audit:
            raise ValueError(
                "authority_audit must be non-empty; "
                "at least one authority attempt must be recorded"
            )
        for i, attempt in enumerate(self.authority_audit):
            if not isinstance(attempt, AuthorityAttemptResult):
                raise TypeError(
                    f"authority_audit[{i}] must be AuthorityAttemptResult, got "
                    f"{type(attempt).__name__}"
                )

        # Check that authority audit does not contain fatal outcomes
        # (which would mean this should have been a FAILED execution)
        for i, attempt in enumerate(self.authority_audit):
            if attempt.outcome in AUTHORITY_FATAL_OUTCOMES:
                raise ValueError(
                    f"authority_audit[{i}] has fatal outcome "
                    f"{attempt.outcome.value}; this cannot be represented "
                    "as a COMPLETED ComparableResearchResult. "
                    "The execution should have FAILED instead."
                )

        # candidates
        if not isinstance(self.candidates, tuple):
            raise TypeError(
                f"candidates must be a tuple, got "
                f"{type(self.candidates).__name__}"
            )
        for i, candidate in enumerate(self.candidates):
            if not isinstance(candidate, ComparableCandidateResult):
                raise TypeError(
                    f"candidates[{i}] must be ComparableCandidateResult, got "
                    f"{type(candidate).__name__}"
                )

        # candidate_enrichment_audits
        if not isinstance(self.candidate_enrichment_audits, tuple):
            raise TypeError(
                f"candidate_enrichment_audits must be a tuple, got "
                f"{type(self.candidate_enrichment_audits).__name__}"
            )
        if len(self.candidate_enrichment_audits) != len(self.candidates):
            raise ValueError(
                f"candidate_enrichment_audits length "
                f"({len(self.candidate_enrichment_audits)}) must match "
                f"candidates length ({len(self.candidates)})"
            )
        for i, audit in enumerate(self.candidate_enrichment_audits):
            if not isinstance(audit, ProductEnrichmentAudit):
                raise TypeError(
                    f"candidate_enrichment_audits[{i}] must be "
                    f"ProductEnrichmentAudit, got {type(audit).__name__}"
                )

        # --- Kind-specific invariants ---
        if self.kind is ComparableResultKind.FULL:
            self._validate_full()
        elif self.kind is ComparableResultKind.NO_AUTHORITY_MATCH:
            self._validate_no_authority_match()
        elif self.kind is ComparableResultKind.NO_REQUESTED_MPN:
            self._validate_no_requested_mpn()
        elif self.kind is ComparableResultKind.AMBIGUOUS_AUTHORITY:
            self._validate_ambiguous_authority()

        # --- Cross-kind contradiction check ---
        self._check_no_contradictory_authority_mix()

    # -- Kind-specific validation --

    def _validate_full(self) -> None:
        """FULL requires:
        - non-empty target_mpn
        - non-empty target_manufacturer
        - non-empty authority_audit
        - exactly one MATCHED
        - zero AMBIGUOUS_MPN_MATCH
        - zero AUTHORITY_FETCH_FAILED / AUTHORITY_SOURCE_REFUSED /
          AUTHORITY_HOST_ESCAPED / NO_STRUCTURAL_OBSERVATIONS
        - every non-MATCHED attempt is NO_MPN_IN_SOURCE
        - candidates may be empty or non-empty
        - target_enrichment_audit must be set
        """
        if not self.target_mpn.strip():
            raise ValueError("FULL kind requires a non-empty target_mpn")

        if not self.target_manufacturer or not self.target_manufacturer.strip():
            raise ValueError("FULL kind requires a non-empty target_manufacturer")

        matched_count = sum(
            1 for a in self.authority_audit
            if a.outcome is AuthorityAuditOutcomeKind.MATCHED
        )
        if matched_count != 1:
            raise ValueError(
                f"FULL kind requires exactly one MATCHED authority attempt, "
                f"got {matched_count}"
            )

        for i, attempt in enumerate(self.authority_audit):
            if attempt.outcome is AuthorityAuditOutcomeKind.AMBIGUOUS_MPN_MATCH:
                raise ValueError(
                    f"FULL kind cannot have AMBIGUOUS_MPN_MATCH in authority_audit[{i}]"
                )
            if attempt.outcome is not AuthorityAuditOutcomeKind.MATCHED:
                if attempt.outcome is not AuthorityAuditOutcomeKind.NO_MPN_IN_SOURCE:
                    raise ValueError(
                        f"FULL kind requires every non-MATCHED authority attempt "
                        f"to be NO_MPN_IN_SOURCE, got {attempt.outcome.value} at [{i}]"
                    )

        if self.target_enrichment_audit is None:
            raise ValueError("FULL kind requires target_enrichment_audit to be set")

    def _validate_no_authority_match(self) -> None:
        """NO_AUTHORITY_MATCH requires:
        - candidates == ()
        - authority_audit non-empty
        - EVERY attempt is NO_MPN_IN_SOURCE
        - no fabricated target manufacturer
        """
        if self.candidates:
            raise ValueError(
                "NO_AUTHORITY_MATCH kind must have empty candidates"
            )

        for i, attempt in enumerate(self.authority_audit):
            if attempt.outcome is not AuthorityAuditOutcomeKind.NO_MPN_IN_SOURCE:
                raise ValueError(
                    f"NO_AUTHORITY_MATCH requires all authority_audit attempts "
                    f"to be NO_MPN_IN_SOURCE, got {attempt.outcome.value} at [{i}]"
                )

        # No fabricated target manufacturer: if we have no authority match,
        # target_manufacturer should not be asserted.
        if self.target_manufacturer is not None and self.target_manufacturer.strip():
            raise ValueError(
                "NO_AUTHORITY_MATCH kind must not have a fabricated "
                "target_manufacturer"
            )

    def _validate_no_requested_mpn(self) -> None:
        """NO_REQUESTED_MPN requires:
        - candidates == ()
        - authority_audit non-empty
        - EVERY attempt is NO_REQUESTED_MPN
        - target MPN may be empty
        - no fabricated target manufacturer
        """
        if self.candidates:
            raise ValueError(
                "NO_REQUESTED_MPN kind must have empty candidates"
            )

        for i, attempt in enumerate(self.authority_audit):
            if attempt.outcome is not AuthorityAuditOutcomeKind.NO_REQUESTED_MPN:
                raise ValueError(
                    f"NO_REQUESTED_MPN requires all authority_audit attempts "
                    f"to be NO_REQUESTED_MPN, got {attempt.outcome.value} at [{i}]"
                )

        # No fabricated target manufacturer
        if self.target_manufacturer is not None and self.target_manufacturer.strip():
            raise ValueError(
                "NO_REQUESTED_MPN kind must not have a fabricated "
                "target_manufacturer"
            )

    def _validate_ambiguous_authority(self) -> None:
        """AMBIGUOUS_AUTHORITY requires:
        - candidates == ()
        - authority_audit non-empty
        - zero incomplete/failure audit states
        - at least one AMBIGUOUS_MPN_MATCH OR more than one MATCHED
        """
        if self.candidates:
            raise ValueError(
                "AMBIGUOUS_AUTHORITY kind must have empty candidates"
            )

        # Check for incomplete/failure states
        for i, attempt in enumerate(self.authority_audit):
            if attempt.outcome in AUTHORITY_FATAL_OUTCOMES:
                raise ValueError(
                    f"AMBIGUOUS_AUTHORITY cannot have fatal outcome "
                    f"{attempt.outcome.value} in authority_audit[{i}]"
                )
            if attempt.outcome is AuthorityAuditOutcomeKind.NO_REQUESTED_MPN:
                raise ValueError(
                    f"AMBIGUOUS_AUTHORITY cannot have NO_REQUESTED_MPN in "
                    f"authority_audit[{i}]"
                )
            if attempt.outcome is AuthorityAuditOutcomeKind.NO_MPN_IN_SOURCE:
                raise ValueError(
                    f"AMBIGUOUS_AUTHORITY cannot have NO_MPN_IN_SOURCE in "
                    f"authority_audit[{i}]"
                )

        ambiguous_count = sum(
            1 for a in self.authority_audit
            if a.outcome is AuthorityAuditOutcomeKind.AMBIGUOUS_MPN_MATCH
        )
        matched_count = sum(
            1 for a in self.authority_audit
            if a.outcome is AuthorityAuditOutcomeKind.MATCHED
        )

        if ambiguous_count < 1 and matched_count < 2:
            raise ValueError(
                "AMBIGUOUS_AUTHORITY requires at least one AMBIGUOUS_MPN_MATCH "
                f"or more than one MATCHED (got {ambiguous_count} ambiguous, "
                f"{matched_count} matched)"
            )

    # -- Anti-contradiction check --
    # Prevent NO_MPN_IN_SOURCE + NO_REQUESTED_MPN mixing in one result.

    def _check_no_contradictory_authority_mix(self) -> None:
        """A single result must not mix NO_MPN_IN_SOURCE and NO_REQUESTED_MPN."""
        outcomes = {a.outcome for a in self.authority_audit}
        has_no_mpn = AuthorityAuditOutcomeKind.NO_MPN_IN_SOURCE in outcomes
        has_no_requested = AuthorityAuditOutcomeKind.NO_REQUESTED_MPN in outcomes
        if has_no_mpn and has_no_requested:
            raise ValueError(
                "ComparableResearchResult authority audit must not mix "
                "NO_MPN_IN_SOURCE and NO_REQUESTED_MPN; they represent "
                "contradictory completion conditions"
            )
