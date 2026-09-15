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

The read-model projection is pure: scalar fields and tuples only.
No ProductIdentity, no ComparableCandidate, no ProductSpecificationSet,
no SpecificationResolution — those are raw graph objects not required
by the durable field-level projection.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from enum import Enum

from product_intelligence.research.enterprise_ssd_similarity import (
    ComparisonState,
)
from product_intelligence.research.specifications import (
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
        The MPN that was matched. REQUIRED for MATCHED, MUST be None
        for every non-MATCHED outcome.

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
                # Non-MATCHED, source-backed outcomes:
                # matched_mpn MUST be None — never fabricate a match
                if self.matched_mpn is not None:
                    raise ValueError(
                        f"non-MATCHED outcome {self.outcome.value} must not "
                        f"have matched_mpn; got {self.matched_mpn!r}. "
                        "Only MATCHED outcomes may carry a matched_mpn."
                    )

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
# ProductEnrichmentAudit — per-product 6D enrichment audit only
# ---------------------------------------------------------------------------
#
# This represents ONLY the datasheet enrichment audit for one product.
# Authority establishment is a TARGET-level concern owned by
# ComparableResearchResult.authority_audit.
#
# Candidates do NOT independently run PRE1 authority establishment,
# so ProductEnrichmentAudit must NOT carry authority_audit, ProductIdentity,
# or ProductSpecificationSet.


@dataclass(frozen=True)
class ProductEnrichmentAudit:
    """Specification enrichment audit for one product identity.

    Represents only the per-product 6D (datasheet) enrichment audit.
    Authority establishment is TARGET-only and lives at the
    ComparableResearchResult level.

    product_mpn : str
        The product MPN this enrichment audit belongs to.

    attempts : tuple[DatasheetAttemptResult, ...]
        The datasheet-PDF enrichment attempt results for this product.
        May be empty if no datasheet enrichment was attempted.
    """

    product_mpn: str
    attempts: tuple[DatasheetAttemptResult, ...] = ()

    def __post_init__(self) -> None:
        # product_mpn
        if not isinstance(self.product_mpn, str):
            raise TypeError(
                f"product_mpn must be a string, got "
                f"{type(self.product_mpn).__name__}"
            )
        if not self.product_mpn.strip():
            raise ValueError("product_mpn must be a non-empty string")

        # attempts
        if not isinstance(self.attempts, tuple):
            raise TypeError(
                f"attempts must be a tuple, got "
                f"{type(self.attempts).__name__}"
            )
        for i, attempt in enumerate(self.attempts):
            if not isinstance(attempt, DatasheetAttemptResult):
                raise TypeError(
                    f"attempts[{i}] must be DatasheetAttemptResult, got "
                    f"{type(attempt).__name__}"
                )


# ---------------------------------------------------------------------------
# EvidenceSourceReference
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class EvidenceSourceReference:
    """Represents actual evidence that supported a resolved field.

    Preserves the frozen PRE2 provenance contract.

    source_name : str
        The evidence source name.

    source_url : str
        The evidence source URL.

    evidence_layer : EvidenceLayer
        SUPPORT_PAGE or DATASHEET_PDF.

    source_authority : SourceAuthority
        The authority tier of the evidence source.

    retrieved_at : str
        ISO-8601 retrieval timestamp. Serializable/read-model representation.
    """

    source_name: str
    source_url: str
    evidence_layer: EvidenceLayer
    source_authority: SourceAuthority
    retrieved_at: str

    def __post_init__(self) -> None:
        if not isinstance(self.source_name, str) or not self.source_name.strip():
            raise ValueError("source_name must be a non-empty string")

        if not isinstance(self.source_url, str) or not self.source_url.strip():
            raise ValueError("source_url must be a non-empty string")

        if not isinstance(self.evidence_layer, EvidenceLayer):
            raise TypeError(
                f"evidence_layer must be EvidenceLayer, got "
                f"{type(self.evidence_layer).__name__}"
            )

        if not isinstance(self.source_authority, SourceAuthority):
            raise TypeError(
                f"source_authority must be SourceAuthority, got "
                f"{type(self.source_authority).__name__}"
            )

        if not isinstance(self.retrieved_at, str) or not self.retrieved_at.strip():
            raise ValueError("retrieved_at must be a non-empty ISO-8601 string")


# ---------------------------------------------------------------------------
# FieldAssessmentResult
# ---------------------------------------------------------------------------
#
# Pure field-level projection sufficient to map directly from frozen:
#     SpecificationSimilarityFieldAssessment
# without dropping semantic fields.
#
# Does NOT recompute the 7B scoring formula. Frozen 7B already owns scoring.
# Uses frozen pure enums: ComparisonState, ResolutionState.
# Decimal similarity values stored as strings in the codec.


@dataclass(frozen=True)
class FieldAssessmentResult:
    """Assessment of one specification field for comparison.

    definition_key : str
        The schema definition key (e.g. "capacity").

    comparison_state : ComparisonState
        SCORED, TARGET_NOT_VERIFIED, CANDIDATE_NOT_VERIFIED, or BOTH_NOT_VERIFIED.

    target_resolution_state : ResolutionState
        The target's resolution state for this field.

    candidate_resolution_state : ResolutionState
        The candidate's resolution state for this field.

    field_similarity : Decimal | None
        Similarity score in [0, 1] when comparison_state is SCORED.
        None for all non-SCORED states.

    target_value : str | None
        The target's resolved value for this field.

    candidate_value : str | None
        The candidate's resolved value for this field.

    target_evidence : tuple[EvidenceSourceReference, ...]
        Evidence sources supporting the target value.

    candidate_evidence : tuple[EvidenceSourceReference, ...]
        Evidence sources supporting the candidate value.

    Invariants:
        - comparison_state == SCORED  -> field_similarity is Decimal in [0, 1]
        - non-SCORED                  -> field_similarity is None
    """

    definition_key: str
    comparison_state: ComparisonState
    target_resolution_state: ResolutionState
    candidate_resolution_state: ResolutionState
    field_similarity: Decimal | None
    target_value: str | None
    candidate_value: str | None
    target_evidence: tuple[EvidenceSourceReference, ...] = ()
    candidate_evidence: tuple[EvidenceSourceReference, ...] = ()

    def __post_init__(self) -> None:
        # definition_key
        if not isinstance(self.definition_key, str) or not self.definition_key.strip():
            raise ValueError("definition_key must be a non-empty string")

        # comparison_state must be exact enum
        if not isinstance(self.comparison_state, ComparisonState):
            raise TypeError(
                f"comparison_state must be ComparisonState, got "
                f"{type(self.comparison_state).__name__}"
            )

        # resolution states must be exact enums
        if not isinstance(self.target_resolution_state, ResolutionState):
            raise TypeError(
                f"target_resolution_state must be ResolutionState, got "
                f"{type(self.target_resolution_state).__name__}"
            )
        if not isinstance(self.candidate_resolution_state, ResolutionState):
            raise TypeError(
                f"candidate_resolution_state must be ResolutionState, got "
                f"{type(self.candidate_resolution_state).__name__}"
            )

        # SCORED -> field_similarity must be Decimal in [0, 1]
        # non-SCORED -> field_similarity must be None
        if self.comparison_state is ComparisonState.SCORED:
            if self.field_similarity is None:
                raise ValueError(
                    "SCORED comparison requires a field_similarity value"
                )
            if type(self.field_similarity) is not Decimal:
                raise TypeError(
                    f"field_similarity must be Decimal, got "
                    f"{type(self.field_similarity).__name__}"
                )
            if not (Decimal("0") <= self.field_similarity <= Decimal("1")):
                raise ValueError(
                    f"field_similarity {self.field_similarity} is not in "
                    "range [0, 1]"
                )
        else:
            if self.field_similarity is not None:
                raise ValueError(
                    f"Non-SCORED comparison state "
                    f"{self.comparison_state.value} must have "
                    "field_similarity=None, got "
                    f"{self.field_similarity!r}"
                )

        # target_value
        if self.target_value is not None:
            if not isinstance(self.target_value, str):
                raise TypeError(
                    f"target_value must be a string or None, got "
                    f"{type(self.target_value).__name__}"
                )

        # candidate_value
        if self.candidate_value is not None:
            if not isinstance(self.candidate_value, str):
                raise TypeError(
                    f"candidate_value must be a string or None, got "
                    f"{type(self.candidate_value).__name__}"
                )

        # evidence tuples
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
#
# Pure scalar projection sufficient to map directly from frozen:
#     EnterpriseSsdCandidateSimilarity
# without dropping semantic fields.
#
# Does NOT carry ComparableCandidate, ProductIdentity, or
# ProductSpecificationSet graphs. The field-level durable projection
# is already provided by FieldAssessmentResult + EvidenceSourceReference.


@dataclass(frozen=True)
class ComparableCandidateResult:
    """The research result for one discovered comparable candidate.

    candidate_mpn : str
        The candidate's manufacturer part number.

    candidate_normalized_mpn : str
        The candidate's normalized part number.

    scored_field_count : int
        Number of fields that were scored (both sides VERIFIED).

    evidence_coverage : Decimal
        scored_field_count / total_fields (e.g. 7/12).

    observed_similarity : Decimal | None
        Mean of scored field similarities. None if zero scored fields.

    evidence_weighted_similarity : Decimal | None
        Sum of scored similarities / total_fields. None if zero scored fields.

    field_assessments : tuple[FieldAssessmentResult, ...]
        Per-field comparison assessments between target and this candidate.

    enrichment_audit : ProductEnrichmentAudit
        Specification enrichment audit for this candidate.
    """

    candidate_mpn: str
    candidate_normalized_mpn: str
    scored_field_count: int
    evidence_coverage: Decimal
    observed_similarity: Decimal | None
    evidence_weighted_similarity: Decimal | None
    field_assessments: tuple[FieldAssessmentResult, ...]
    enrichment_audit: ProductEnrichmentAudit

    def __post_init__(self) -> None:
        # candidate_mpn
        if not isinstance(self.candidate_mpn, str):
            raise TypeError(
                f"candidate_mpn must be a string, got "
                f"{type(self.candidate_mpn).__name__}"
            )
        if not self.candidate_mpn.strip():
            raise ValueError("candidate_mpn must be a non-empty string")

        # candidate_normalized_mpn
        if not isinstance(self.candidate_normalized_mpn, str):
            raise TypeError(
                f"candidate_normalized_mpn must be a string, got "
                f"{type(self.candidate_normalized_mpn).__name__}"
            )
        if not self.candidate_normalized_mpn.strip():
            raise ValueError("candidate_normalized_mpn must be a non-empty string")

        # scored_field_count — exact int type
        if type(self.scored_field_count) is not int:
            raise TypeError(
                f"scored_field_count must be int, got "
                f"{type(self.scored_field_count).__name__}"
            )
        if self.scored_field_count < 0:
            raise ValueError(
                f"scored_field_count must be >= 0, got {self.scored_field_count}"
            )

        # evidence_coverage — exact Decimal type
        if type(self.evidence_coverage) is not Decimal:
            raise TypeError(
                f"evidence_coverage must be Decimal, got "
                f"{type(self.evidence_coverage).__name__}"
            )
        if not (Decimal("0") <= self.evidence_coverage <= Decimal("1")):
            raise ValueError(
                f"evidence_coverage {self.evidence_coverage} is not in "
                "range [0, 1]"
            )

        # observed_similarity
        if self.observed_similarity is not None:
            if type(self.observed_similarity) is not Decimal:
                raise TypeError(
                    f"observed_similarity must be Decimal or None, got "
                    f"{type(self.observed_similarity).__name__}"
                )
            if not (Decimal("0") <= self.observed_similarity <= Decimal("1")):
                raise ValueError(
                    f"observed_similarity {self.observed_similarity} is not in "
                    "range [0, 1]"
                )

        # evidence_weighted_similarity
        if self.evidence_weighted_similarity is not None:
            if type(self.evidence_weighted_similarity) is not Decimal:
                raise TypeError(
                    f"evidence_weighted_similarity must be Decimal or None, got "
                    f"{type(self.evidence_weighted_similarity).__name__}"
                )
            if not (Decimal("0") <= self.evidence_weighted_similarity <= Decimal("1")):
                raise ValueError(
                    f"evidence_weighted_similarity "
                    f"{self.evidence_weighted_similarity} is not in range [0, 1]"
                )

        # scored_field_count == 0 -> observed_similarity and
        # evidence_weighted_similarity must be None
        if self.scored_field_count == 0:
            if self.observed_similarity is not None:
                raise ValueError(
                    "scored_field_count == 0 requires observed_similarity=None"
                )
            if self.evidence_weighted_similarity is not None:
                raise ValueError(
                    "scored_field_count == 0 requires "
                    "evidence_weighted_similarity=None"
                )

        # field_assessments
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

        # enrichment_audit
        if not isinstance(self.enrichment_audit, ProductEnrichmentAudit):
            raise TypeError(
                f"enrichment_audit must be ProductEnrichmentAudit, got "
                f"{type(self.enrichment_audit).__name__}"
            )


# ---------------------------------------------------------------------------
# ComparableResearchResult
# ---------------------------------------------------------------------------
#
# Top-level result. Authority_audit is TARGET authority establishment only.
# Each ComparableCandidateResult carries its own enrichment_audit.
# No redundant candidate_enrichment_audits tuple.


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
        Datasheet enrichment audit for the target product. Set for FULL kind.
        None for NO_AUTHORITY_MATCH, AMBIGUOUS_AUTHORITY, NO_REQUESTED_MPN.

    authority_audit : tuple[AuthorityAttemptResult, ...]
        The authority-support-page attempt results for the TARGET.
        Non-empty. This is the single source of authority truth.
        TARGET authority establishment only.

    candidates : tuple[ComparableCandidateResult, ...]
        The research results for each discovered comparable candidate.
        Each candidate carries its own enrichment_audit.
        Empty for non-FULL kinds.
    """

    kind: ComparableResultKind
    target_mpn: str
    target_manufacturer: str | None
    target_enrichment_audit: ProductEnrichmentAudit | None
    authority_audit: tuple[AuthorityAttemptResult, ...]
    candidates: tuple[ComparableCandidateResult, ...]

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
