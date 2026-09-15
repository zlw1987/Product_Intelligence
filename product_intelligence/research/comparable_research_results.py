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
from datetime import datetime as _datetime
from decimal import Decimal
from enum import Enum

from product_intelligence.research.enterprise_ssd import (
    ENTERPRISE_SSD_SCHEMA,
)
from product_intelligence.research.enterprise_ssd_similarity import (
    ComparisonState,
)
from product_intelligence.research.identity import (
    compare_part_numbers,
    normalize_part_number,
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
# Timestamp validation helper (stdlib only, no execution/provider imports)
# ---------------------------------------------------------------------------


def _validate_iso8601_tz(ts: str, field_name: str) -> None:
    """Validate non-empty ISO-8601 with timezone offset using stdlib only.

    Raises ValueError if the string is not a valid ISO-8601 timestamp
    with timezone information (UTC offset).
    """
    if not isinstance(ts, str) or not ts.strip():
        raise ValueError(
            f"{field_name} must be a non-empty ISO-8601 string"
        )
    try:
        parsed = _datetime.fromisoformat(ts)
    except (ValueError, TypeError) as exc:
        raise ValueError(
            f"{field_name} must be a valid ISO-8601 timestamp, got {ts!r}"
        ) from exc
    if parsed.tzinfo is None:
        raise ValueError(
            f"{field_name} must be timezone-aware (have UTC offset), "
            f"got {ts!r}"
        )


# ---------------------------------------------------------------------------
# Cross-object evidence-to-audit validation (BLOCKER 1)
# ---------------------------------------------------------------------------


def _validate_evidence_references_against_audit(
    evidence_refs: tuple[EvidenceSourceReference, ...],
    audit: ProductEnrichmentAudit,
    side_label: str,
) -> None:
    """Validate DATASHEET_PDF evidence references against a ProductEnrichmentAudit.

    Every EvidenceSourceReference with evidence_layer == DATASHEET_PDF must
    trace to exactly one ENRICHED DatasheetAttemptResult in the audit with
    matching source_name, final_url, and retrieved_at.

    Rules:
    - DATASHEET_PDF evidence requires source_authority == AUTHORITATIVE.
      SUPPORT_PAGE is not subject to this rule.
    - If audit has NO_DATASHEET_SOURCE outcome, zero DATASHEET_PDF evidence
      references are permitted.
    - Non-ENRICHED outcomes (FETCH_FAILED, SOURCE_REFUSED, PARSE_FAILED,
      NO_OBSERVATIONS) must never authorize DATASHEET_PDF evidence.
    - SUPPORT_PAGE evidence is always permitted regardless of audit state.
    """
    # Collect ENRICHED attempts for provenance matching
    enriched_attempts = [
        a for a in audit.attempts
        if a.outcome is DatasheetAuditOutcomeKind.ENRICHED
    ]

    has_no_datasheet = any(
        a.outcome is DatasheetAuditOutcomeKind.NO_DATASHEET_SOURCE
        for a in audit.attempts
    )

    for ref in evidence_refs:
        if ref.evidence_layer is not EvidenceLayer.DATASHEET_PDF:
            # SUPPORT_PAGE evidence is not subject to datasheet audit rules
            continue

        # RULE 1: DATASHEET_PDF must be AUTHORITATIVE
        if ref.source_authority is not SourceAuthority.AUTHORITATIVE:
            raise ValueError(
                f"{side_label} DATASHEET_PDF evidence reference must have "
                f"source_authority=AUTHORITATIVE, got "
                f"{ref.source_authority.value}"
            )

        # RULE 2: If audit is NO_DATASHEET_SOURCE, zero DATASHEET_PDF refs
        if has_no_datasheet:
            raise ValueError(
                f"{side_label} DATASHEET_PDF evidence reference exists but "
                f"enrichment audit is NO_DATASHEET_SOURCE; "
                "no datasheet evidence may be claimed without a datasheet"
            )

        # RULE 3: Must match an ENRICHED attempt with matching provenance
        found_match = False
        for attempt in enriched_attempts:
            if (
                attempt.source_name == ref.source_name
                and attempt.final_url == ref.source_url
                and attempt.retrieved_at == ref.retrieved_at
            ):
                found_match = True
                break

        if not found_match:
            raise ValueError(
                f"{side_label} DATASHEET_PDF evidence reference "
                f"(source_name={ref.source_name!r}, "
                f"source_url={ref.source_url!r}, "
                f"retrieved_at={ref.retrieved_at!r}) "
                f"has no matching ENRICHED attempt in the enrichment audit"
            )


# ---------------------------------------------------------------------------
# AuthorityAttemptResult
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class AuthorityAttemptResult:
    """The audited outcome of one authority-support-page attempt.

    Mirrors the serializable audit subset of the frozen PRE1
    _AuthoritySourceOutcome that can be mapped directly without reaching
    into private policy configuration.

    policy_id : str
        The authority policy that was attempted. Always non-empty.

    outcome : AuthorityAuditOutcomeKind
        The result of this attempt.

    requested_source_url : str | None
        The URL that was attempted. Set for all source-backed outcomes.
        None only for NO_REQUESTED_MPN (no source attempted).

    fetched_final_url : str | None
        The final URL after redirects. Set when a fetch occurred.

    retrieved_at : str | None
        ISO-8601 retrieval timestamp. Set when a fetch occurred.

    matching_mpn : str | None
        The MPN that was matched. REQUIRED for MATCHED, MUST be None
        for every non-MATCHED outcome.
    """

    policy_id: str
    outcome: AuthorityAuditOutcomeKind
    requested_source_url: str | None = None
    fetched_final_url: str | None = None
    retrieved_at: str | None = None
    matching_mpn: str | None = None

    def __post_init__(self) -> None:
        # policy_id — always required and non-empty
        if not isinstance(self.policy_id, str):
            raise TypeError(
                f"policy_id must be a string, got "
                f"{type(self.policy_id).__name__}"
            )
        if not self.policy_id.strip():
            raise ValueError("policy_id must be a non-empty string")

        # outcome must be exact enum type
        if not isinstance(self.outcome, AuthorityAuditOutcomeKind):
            raise TypeError(
                f"outcome must be AuthorityAuditOutcomeKind, got "
                f"{type(self.outcome).__name__}"
            )

        # State-dependent field shape (mirrors frozen PRE1 truth)
        if self.outcome is AuthorityAuditOutcomeKind.MATCHED:
            # MATCHED requires complete provenance
            if self.requested_source_url is None or not self.requested_source_url.strip():
                raise ValueError(
                    "MATCHED outcome requires a non-empty requested_source_url"
                )
            if self.fetched_final_url is None or not self.fetched_final_url.strip():
                raise ValueError(
                    "MATCHED outcome requires a non-empty fetched_final_url"
                )
            if self.retrieved_at is None or not self.retrieved_at.strip():
                raise ValueError(
                    "MATCHED outcome requires a non-empty retrieved_at"
                )
            _validate_iso8601_tz(self.retrieved_at, "AuthorityAttemptResult.retrieved_at")
            if self.matching_mpn is None or not self.matching_mpn.strip():
                raise ValueError(
                    "MATCHED outcome requires a non-empty matching_mpn"
                )

        elif self.outcome is AuthorityAuditOutcomeKind.NO_REQUESTED_MPN:
            # No source attempted — source URL set but no fetch evidence
            if self.requested_source_url is None or not self.requested_source_url.strip():
                raise ValueError(
                    "NO_REQUESTED_MPN requires a non-empty requested_source_url"
                )
            if self.fetched_final_url is not None:
                raise ValueError(
                    "NO_REQUESTED_MPN must not have fetched_final_url"
                )
            if self.retrieved_at is not None:
                raise ValueError(
                    "NO_REQUESTED_MPN must not have retrieved_at"
                )
            if self.matching_mpn is not None:
                raise ValueError(
                    "NO_REQUESTED_MPN must not have matching_mpn"
                )

        elif self.outcome in (
            AuthorityAuditOutcomeKind.AUTHORITY_FETCH_FAILED,
            AuthorityAuditOutcomeKind.AUTHORITY_SOURCE_REFUSED,
        ):
            # Fetch failed/refused — URL known but no response
            if self.requested_source_url is None or not self.requested_source_url.strip():
                raise ValueError(
                    f"{self.outcome.value} requires a non-empty "
                    "requested_source_url"
                )
            if self.fetched_final_url is not None:
                raise ValueError(
                    f"{self.outcome.value} must not have fetched_final_url"
                )
            if self.retrieved_at is not None:
                raise ValueError(
                    f"{self.outcome.value} must not have retrieved_at"
                )
            if self.matching_mpn is not None:
                raise ValueError(
                    f"{self.outcome.value} must not have matching_mpn"
                )

        elif self.outcome is AuthorityAuditOutcomeKind.AUTHORITY_HOST_ESCAPED:
            # Escaped — we know where it escaped to
            if self.requested_source_url is None or not self.requested_source_url.strip():
                raise ValueError(
                    "AUTHORITY_HOST_ESCAPED requires a non-empty "
                    "requested_source_url"
                )
            if self.fetched_final_url is None or not self.fetched_final_url.strip():
                raise ValueError(
                    "AUTHORITY_HOST_ESCAPED requires a non-empty fetched_final_url"
                )
            if self.matching_mpn is not None:
                raise ValueError(
                    "AUTHORITY_HOST_ESCAPED must not have matching_mpn"
                )

        elif self.outcome is AuthorityAuditOutcomeKind.AMBIGUOUS_MPN_MATCH:
            # Ambiguity: source was fetched, multiple records matched
            if self.requested_source_url is None or not self.requested_source_url.strip():
                raise ValueError(
                    "AMBIGUOUS_MPN_MATCH requires a non-empty "
                    "requested_source_url"
                )
            if self.fetched_final_url is None or not self.fetched_final_url.strip():
                raise ValueError(
                    "AMBIGUOUS_MPN_MATCH requires a non-empty fetched_final_url"
                )
            if self.retrieved_at is None or not self.retrieved_at.strip():
                raise ValueError(
                    "AMBIGUOUS_MPN_MATCH requires a non-empty retrieved_at"
                )
            _validate_iso8601_tz(self.retrieved_at, "AuthorityAttemptResult.retrieved_at")
            if self.matching_mpn is not None:
                raise ValueError(
                    "AMBIGUOUS_MPN_MATCH must not have matching_mpn"
                )

        elif self.outcome in (
            AuthorityAuditOutcomeKind.NO_MPN_IN_SOURCE,
            AuthorityAuditOutcomeKind.NO_STRUCTURAL_OBSERVATIONS,
        ):
            # Fetched but no match / no observations
            if self.requested_source_url is None or not self.requested_source_url.strip():
                raise ValueError(
                    f"{self.outcome.value} requires a non-empty "
                    "requested_source_url"
                )
            if self.fetched_final_url is None or not self.fetched_final_url.strip():
                raise ValueError(
                    f"{self.outcome.value} requires a non-empty fetched_final_url"
                )
            if self.retrieved_at is None or not self.retrieved_at.strip():
                raise ValueError(
                    f"{self.outcome.value} requires a non-empty retrieved_at"
                )
            _validate_iso8601_tz(self.retrieved_at, "AuthorityAttemptResult.retrieved_at")
            if self.matching_mpn is not None:
                raise ValueError(
                    f"{self.outcome.value} must not have matching_mpn"
                )


# ---------------------------------------------------------------------------
# DatasheetAttemptResult
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class DatasheetAttemptResult:
    """The audited outcome of one datasheet-PDF enrichment attempt.

    Mechanically preserves the frozen 6D DatasheetSourceOutcome contract.

    ENRICHED:
        source_name non-empty, source_url non-empty,
        final_url non-empty, retrieved_at non-empty (TZ-aware),
        observation_count is exact int > 0

    NO_OBSERVATIONS:
        source_name non-empty, source_url non-empty,
        final_url non-empty, retrieved_at non-empty (TZ-aware),
        observation_count == 0

    PARSE_FAILED:
        source_name non-empty, source_url non-empty,
        final_url non-empty, retrieved_at non-empty (TZ-aware),
        observation_count == 0

    FETCH_FAILED:
        source_name non-empty, source_url non-empty,
        final_url is None, retrieved_at is None,
        observation_count == 0

    SOURCE_REFUSED:
        source_name non-empty, source_url non-empty,
        final_url is None, retrieved_at is None,
        observation_count == 0

    NO_DATASHEET_SOURCE:
        source_name is None, source_url is None,
        final_url is None, retrieved_at is None,
        observation_count is None
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
            # Source-backed outcome — source_name and source_url always required
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

            # --- Per-outcome shape (mirrors frozen 6D DatasheetSourceOutcome) ---

            if self.outcome is DatasheetAuditOutcomeKind.ENRICHED:
                # ENRICHED: full provenance + positive observation count
                if self.final_url is None or not self.final_url.strip():
                    raise ValueError(
                        "ENRICHED outcome requires a non-empty final_url"
                    )
                if self.retrieved_at is None or not self.retrieved_at.strip():
                    raise ValueError(
                        "ENRICHED outcome requires a non-empty retrieved_at"
                    )
                _validate_iso8601_tz(self.retrieved_at, "DatasheetAttemptResult.retrieved_at")
                if self.observation_count is None:
                    raise ValueError(
                        "ENRICHED outcome requires observation_count"
                    )
                if isinstance(self.observation_count, bool):
                    raise TypeError(
                        "observation_count must be int, got bool"
                    )
                if not isinstance(self.observation_count, int):
                    raise TypeError(
                        f"observation_count must be int, got "
                        f"{type(self.observation_count).__name__}"
                    )
                if self.observation_count <= 0:
                    raise ValueError(
                        f"ENRICHED outcome requires observation_count > 0, "
                        f"got {self.observation_count}"
                    )

            elif self.outcome in (
                DatasheetAuditOutcomeKind.NO_OBSERVATIONS,
                DatasheetAuditOutcomeKind.PARSE_FAILED,
            ):
                # Fetched and parsed (or attempted parse), but zero observations
                if self.final_url is None or not self.final_url.strip():
                    raise ValueError(
                        f"{self.outcome.value} requires a non-empty final_url"
                    )
                if self.retrieved_at is None or not self.retrieved_at.strip():
                    raise ValueError(
                        f"{self.outcome.value} requires a non-empty retrieved_at"
                    )
                _validate_iso8601_tz(self.retrieved_at, "DatasheetAttemptResult.retrieved_at")
                if self.observation_count is None:
                    raise ValueError(
                        f"{self.outcome.value} requires observation_count"
                    )
                if isinstance(self.observation_count, bool):
                    raise TypeError(
                        "observation_count must be int, got bool"
                    )
                if not isinstance(self.observation_count, int):
                    raise TypeError(
                        f"observation_count must be int, got "
                        f"{type(self.observation_count).__name__}"
                    )
                if self.observation_count != 0:
                    raise ValueError(
                        f"{self.outcome.value} requires observation_count == 0, "
                        f"got {self.observation_count}"
                    )

            elif self.outcome in (
                DatasheetAuditOutcomeKind.FETCH_FAILED,
                DatasheetAuditOutcomeKind.SOURCE_REFUSED,
            ):
                # Fetch attempted but failed — no response received
                if self.final_url is not None:
                    raise ValueError(
                        f"{self.outcome.value} must not have final_url"
                    )
                if self.retrieved_at is not None:
                    raise ValueError(
                        f"{self.outcome.value} must not have retrieved_at"
                    )
                if self.observation_count is None:
                    raise ValueError(
                        f"{self.outcome.value} requires observation_count"
                    )
                if isinstance(self.observation_count, bool):
                    raise TypeError(
                        "observation_count must be int, got bool"
                    )
                if not isinstance(self.observation_count, int):
                    raise TypeError(
                        f"observation_count must be int, got "
                        f"{type(self.observation_count).__name__}"
                    )
                if self.observation_count != 0:
                    raise ValueError(
                        f"{self.outcome.value} requires observation_count == 0, "
                        f"got {self.observation_count}"
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
        Non-empty. If any attempt is NO_DATASHEET_SOURCE, it must be
        the ONLY attempt because NO_DATASHEET_SOURCE means no
        DatasheetSource was established.
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

        # attempts — must be non-empty (7C-B will always create at least
        # one NO_DATASHEET_SOURCE attempt when no enrichment was available)
        if not isinstance(self.attempts, tuple):
            raise TypeError(
                f"attempts must be a tuple, got "
                f"{type(self.attempts).__name__}"
            )
        if not self.attempts:
            raise ValueError(
                "attempts must be non-empty; "
                "every product must have at least one enrichment attempt "
                "recorded (including NO_DATASHEET_SOURCE)"
            )
        for i, attempt in enumerate(self.attempts):
            if not isinstance(attempt, DatasheetAttemptResult):
                raise TypeError(
                    f"attempts[{i}] must be DatasheetAttemptResult, got "
                    f"{type(attempt).__name__}"
                )

        # NO_DATASHEET_SOURCE must be the ONLY attempt
        # because it means no DatasheetSource was established
        no_datasheet_count = sum(
            1 for a in self.attempts
            if a.outcome is DatasheetAuditOutcomeKind.NO_DATASHEET_SOURCE
        )
        if no_datasheet_count > 0 and len(self.attempts) > 1:
            raise ValueError(
                "NO_DATASHEET_SOURCE must be the only attempt; "
                "it means no datasheet source was established, "
                f"but {len(self.attempts)} attempts were recorded"
            )
        if no_datasheet_count > 1:
            raise ValueError(
                "Multiple NO_DATASHEET_SOURCE attempts; "
                "at most one is permitted per product"
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
        ISO-8601 retrieval timestamp (timezone-aware). Serializable/read-model representation.
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

        # Validate timezone-aware ISO-8601
        _validate_iso8601_tz(self.retrieved_at, "EvidenceSourceReference.retrieved_at")


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

    ResolutionState -> value/evidence contracts (BLOCKER 4):
        VERIFIED:
            resolved display value must be non-None
            evidence tuple must be non-empty
            at least one evidence reference must be AUTHORITATIVE
        UNVERIFIED:
            resolved display value must be non-None
            evidence tuple must be non-empty
        CONFLICT:
            resolved display value must be None
            evidence tuple must be non-empty
        UNKNOWN:
            resolved display value must be None
            evidence MAY be empty or non-empty
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

        # --- BLOCKER 3: Re-derive comparison_state from resolution states ---
        target_verified = (
            self.target_resolution_state is ResolutionState.VERIFIED
        )
        candidate_verified = (
            self.candidate_resolution_state is ResolutionState.VERIFIED
        )

        if target_verified and candidate_verified:
            expected_comparison = ComparisonState.SCORED
        elif target_verified:
            expected_comparison = ComparisonState.CANDIDATE_NOT_VERIFIED
        elif candidate_verified:
            expected_comparison = ComparisonState.TARGET_NOT_VERIFIED
        else:
            expected_comparison = ComparisonState.BOTH_NOT_VERIFIED

        if self.comparison_state is not expected_comparison:
            raise ValueError(
                f"comparison_state {self.comparison_state.value} does not match "
                f"the re-derived state {expected_comparison.value} for "
                f"target state {self.target_resolution_state.value} and "
                f"candidate state {self.candidate_resolution_state.value}"
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

        # --- BLOCKER 4: ResolutionState -> value/evidence contracts ---
        # Each side independently validated.

        # Target side
        self._validate_resolution_side(
            self.target_resolution_state,
            self.target_value,
            self.target_evidence,
            "target",
        )

        # Candidate side
        self._validate_resolution_side(
            self.candidate_resolution_state,
            self.candidate_value,
            self.candidate_evidence,
            "candidate",
        )

    @staticmethod
    def _validate_resolution_side(
        state: ResolutionState,
        resolved_value: str | None,
        evidence: tuple[EvidenceSourceReference, ...],
        side_label: str,
    ) -> None:
        """Validate value and evidence invariants for one resolution side."""
        if state is ResolutionState.VERIFIED:
            # VERIFIED: value must be present, evidence non-empty,
            # at least one AUTHORITATIVE reference
            if resolved_value is None:
                raise ValueError(
                    f"VERIFIED {side_label} must have a non-None resolved value"
                )
            if not evidence:
                raise ValueError(
                    f"VERIFIED {side_label} must have non-empty evidence"
                )
            has_authoritative = any(
                ref.source_authority is SourceAuthority.AUTHORITATIVE
                for ref in evidence
            )
            if not has_authoritative:
                raise ValueError(
                    f"VERIFIED {side_label} must have at least one "
                    "AUTHORITATIVE evidence reference"
                )

        elif state is ResolutionState.UNVERIFIED:
            # UNVERIFIED: value must be present, evidence non-empty
            # (do NOT require all evidence to be SECONDARY — issue-only
            # authoritative evidence can coexist with the usable secondary value)
            if resolved_value is None:
                raise ValueError(
                    f"UNVERIFIED {side_label} must have a non-None resolved value"
                )
            if not evidence:
                raise ValueError(
                    f"UNVERIFIED {side_label} must have non-empty evidence"
                )

        elif state is ResolutionState.CONFLICT:
            # CONFLICT: value must be None, evidence non-empty
            if resolved_value is not None:
                raise ValueError(
                    f"CONFLICT {side_label} must have resolved_value=None, "
                    f"got {resolved_value!r}"
                )
            if not evidence:
                raise ValueError(
                    f"CONFLICT {side_label} must have non-empty evidence"
                )

        elif state is ResolutionState.UNKNOWN:
            # UNKNOWN: value must be None, evidence may be empty or non-empty
            if resolved_value is not None:
                raise ValueError(
                    f"UNKNOWN {side_label} must have resolved_value=None, "
                    f"got {resolved_value!r}"
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
        Must follow the exact canonical order of ENTERPRISE_SSD_SCHEMA
        definitions.

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

        # --- BLOCKER FU4: Candidate identity self-audit ---
        # candidate_normalized_mpn must equal the deterministic normalization
        # of candidate_mpn (frozen 2A normalize_part_number).
        computed_normalized = normalize_part_number(self.candidate_mpn)
        if computed_normalized != self.candidate_normalized_mpn:
            raise ValueError(
                f"candidate_normalized_mpn {self.candidate_normalized_mpn!r} "
                f"does not match the deterministic normalization of "
                f"candidate_mpn {self.candidate_mpn!r} "
                f"(expected {computed_normalized!r}). "
                "Use frozen 2A normalize_part_number."
            )

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

        # --- ENRICHMENT BINDING: candidate audit MPN must match candidate MPN ---
        if self.enrichment_audit.product_mpn != self.candidate_mpn:
            raise ValueError(
                f"enrichment_audit.product_mpn {self.enrichment_audit.product_mpn!r} "
                f"does not match candidate_mpn {self.candidate_mpn!r}. "
                "Enrichment audit must belong to this candidate."
            )

        # --- Field set validation against ENTERPRISE_SSD_SCHEMA ---
        schema_keys = set(ENTERPRISE_SSD_SCHEMA.definitions.keys())
        total_field_count = len(schema_keys)

        if len(self.field_assessments) != total_field_count:
            raise ValueError(
                f"field_assessments has {len(self.field_assessments)} items, "
                f"but ENTERPRISE_SSD_SCHEMA has {total_field_count} definitions. "
                "Every definition must have exactly one assessment."
            )

        assessment_keys = [fa.definition_key for fa in self.field_assessments]

        # Check for duplicate definition_keys
        if len(set(assessment_keys)) != len(assessment_keys):
            duplicates = [
                k for k in assessment_keys
                if assessment_keys.count(k) > 1
            ]
            raise ValueError(
                f"Duplicate definition_keys in field_assessments: "
                f"{sorted(set(duplicates))}"
            )

        # Check that assessment keys exactly match schema definitions
        if set(assessment_keys) != schema_keys:
            missing = schema_keys - set(assessment_keys)
            extra = set(assessment_keys) - schema_keys
            raise ValueError(
                f"field_assessments definition_keys do not match "
                f"ENTERPRISE_SSD_SCHEMA.definitions. "
                f"Missing: {sorted(missing) if missing else 'none'}, "
                f"Extra: {sorted(extra) if extra else 'none'}"
            )

        # --- PRESERVE EXACT FROZEN 7B FIELD ORDER ---
        canonical_order = tuple(ENTERPRISE_SSD_SCHEMA.definitions.keys())
        actual_order = tuple(fa.definition_key for fa in self.field_assessments)
        if actual_order != canonical_order:
            raise ValueError(
                f"field_assessments must follow the canonical schema definition order. "
                f"Expected: {canonical_order}, "
                f"Got: {actual_order}"
            )

        # --- Re-derive aggregate scalars from field_assessments ---
        scored_similarities: list[Decimal] = [
            fa.field_similarity
            for fa in self.field_assessments
            if fa.comparison_state is ComparisonState.SCORED
        ]
        expected_scored_count = len(scored_similarities)

        if self.scored_field_count != expected_scored_count:
            raise ValueError(
                f"scored_field_count {self.scored_field_count} does not match "
                f"re-derived count {expected_scored_count} from field_assessments"
            )

        # Re-derive evidence_coverage
        expected_coverage = Decimal(expected_scored_count) / Decimal(total_field_count)
        if self.evidence_coverage != expected_coverage:
            raise ValueError(
                f"evidence_coverage {self.evidence_coverage} does not match "
                f"re-derived coverage {expected_coverage} "
                f"({expected_scored_count}/{total_field_count})"
            )

        # Re-derive observed_similarity and evidence_weighted_similarity
        if expected_scored_count == 0:
            if self.observed_similarity is not None:
                raise ValueError(
                    "scored_field_count == 0 requires observed_similarity=None"
                )
            if self.evidence_weighted_similarity is not None:
                raise ValueError(
                    "scored_field_count == 0 requires "
                    "evidence_weighted_similarity=None"
                )
        else:
            if self.observed_similarity is None:
                raise ValueError(
                    "scored_field_count > 0 requires observed_similarity to be set"
                )
            if self.evidence_weighted_similarity is None:
                raise ValueError(
                    "scored_field_count > 0 requires "
                    "evidence_weighted_similarity to be set"
                )

            sum_scored = sum(scored_similarities, Decimal("0"))
            expected_observed = sum_scored / Decimal(expected_scored_count)
            if self.observed_similarity != expected_observed:
                raise ValueError(
                    f"observed_similarity {self.observed_similarity} does not match "
                    f"re-derived value {expected_observed} (mean of {expected_scored_count} "
                    f"scored field similarities)"
                )

            expected_weighted = sum_scored / Decimal(total_field_count)
            if self.evidence_weighted_similarity != expected_weighted:
                raise ValueError(
                    f"evidence_weighted_similarity {self.evidence_weighted_similarity} "
                    f"does not match re-derived value {expected_weighted} "
                    f"(sum of scored similarities / {total_field_count})"
                )

        # --- BLOCKER FU4: Candidate evidence binding to enrichment audit ---
        # Every field_assessment's candidate_evidence must validate against
        # self.enrichment_audit.
        for fa in self.field_assessments:
            _validate_evidence_references_against_audit(
                fa.candidate_evidence,
                self.enrichment_audit,
                f"candidate ({self.candidate_mpn})",
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

        # --- BLOCKER FU4: Type shape hardening ---
        if not isinstance(self.target_mpn, str):
            raise TypeError(
                f"target_mpn must be a string, got "
                f"{type(self.target_mpn).__name__}"
            )
        if self.target_manufacturer is not None:
            if not isinstance(self.target_manufacturer, str):
                raise TypeError(
                    f"target_manufacturer must be a string or None, got "
                    f"{type(self.target_manufacturer).__name__}"
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

        # --- BLOCKER FU4: Candidate normalized-key uniqueness ---
        # No two candidates may share the same candidate_normalized_mpn.
        # Mirrors frozen 7A normalized-key deduplication.
        normalized_keys = [c.candidate_normalized_mpn for c in self.candidates]
        if len(set(normalized_keys)) != len(normalized_keys):
            duplicates = [
                k for k in normalized_keys if normalized_keys.count(k) > 1
            ]
            raise ValueError(
                f"Candidates must have unique normalized MPNs; "
                f"duplicates: {sorted(set(duplicates))}"
            )

        # --- BLOCKER FU4: Target-self exclusion ---
        # A candidate that is the target itself must be rejected.
        if self.candidates and self.target_mpn.strip():
            for candidate in self.candidates:
                cmp_result = compare_part_numbers(
                    self.target_mpn,
                    candidate.candidate_mpn,
                )
                from product_intelligence.domain.enums import (
                    ESTABLISHED_MATCH_TYPES,
                )
                if cmp_result.match_type in ESTABLISHED_MATCH_TYPES:
                    raise ValueError(
                        f"Candidate {candidate.candidate_mpn!r} is the target "
                        f"itself (target_mpn={self.target_mpn!r}, "
                        f"match_type={cmp_result.match_type.value}). "
                        "A product cannot be its own comparable."
                    )

        # --- BLOCKER 3: unique policy_ids across all authority_audit ---
        # PRE1 evaluates each approved policy exactly once.
        policy_ids = [a.policy_id for a in self.authority_audit]
        if len(set(policy_ids)) != len(policy_ids):
            duplicates = [
                pid for pid in policy_ids if policy_ids.count(pid) > 1
            ]
            raise ValueError(
                f"authority_audit must not contain duplicate policy_ids: "
                f"{sorted(set(duplicates))}"
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
        - BLOCKER 3: matched attempt's matching_mpn == target_mpn
        - BLOCKER 3: unique policy_ids across authority_audit
        """
        if not self.target_mpn.strip():
            raise ValueError("FULL kind requires a non-empty target_mpn")

        if not self.target_manufacturer or not self.target_manufacturer.strip():
            raise ValueError("FULL kind requires a non-empty target_manufacturer")

        matched_attempts = [
            a for a in self.authority_audit
            if a.outcome is AuthorityAuditOutcomeKind.MATCHED
        ]
        matched_count = len(matched_attempts)
        if matched_count != 1:
            raise ValueError(
                f"FULL kind requires exactly one MATCHED authority attempt, "
                f"got {matched_count}"
            )

        # --- BLOCKER 3: bind matching_mpn to target_mpn ---
        matched_attempt = matched_attempts[0]
        if matched_attempt.matching_mpn != self.target_mpn:
            raise ValueError(
                f"FULL kind: matched attempt's matching_mpn "
                f"{matched_attempt.matching_mpn!r} does not equal "
                f"target_mpn {self.target_mpn!r}. "
                "Authority evidence must be bound to the exact target."
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

        # --- ENRICHMENT BINDING: target audit MPN must match target MPN ---
        if self.target_enrichment_audit.product_mpn != self.target_mpn:
            raise ValueError(
                f"target_enrichment_audit.product_mpn "
                f"{self.target_enrichment_audit.product_mpn!r} does not match "
                f"target_mpn {self.target_mpn!r}. "
                "Target enrichment audit must belong to this target."
            )

        # --- BLOCKER FU4: Target evidence binding to enrichment audit ---
        # Every candidate's field_assessment target_evidence must validate
        # against self.target_enrichment_audit.
        # If zero candidates, no target field projections to cross-check.
        for candidate in self.candidates:
            for fa in candidate.field_assessments:
                _validate_evidence_references_against_audit(
                    fa.target_evidence,
                    self.target_enrichment_audit,
                    f"target ({self.target_mpn})",
                )
                break  # target evidence is the same across all fields

    def _validate_no_authority_match(self) -> None:
        """NO_AUTHORITY_MATCH requires:
        - candidates == ()
        - authority_audit non-empty
        - EVERY attempt is NO_MPN_IN_SOURCE
        - target_enrichment_audit is None (no authority-established target)
        - target_manufacturer is None (no authority-established manufacturer)
        - target_mpn must be non-empty (original request-side MPN)
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

        if self.target_enrichment_audit is not None:
            raise ValueError(
                "NO_AUTHORITY_MATCH kind must have target_enrichment_audit=None; "
                "no authority-established target exists"
            )

        if self.target_manufacturer is not None:
            raise ValueError(
                "NO_AUTHORITY_MATCH kind must have target_manufacturer=None; "
                "no authority-established manufacturer may leak into an abstention result"
            )

        if not self.target_mpn.strip():
            raise ValueError(
                "NO_AUTHORITY_MATCH kind requires a non-empty target_mpn; "
                "this represents the original request-side MPN"
            )

    def _validate_no_requested_mpn(self) -> None:
        """NO_REQUESTED_MPN requires:
        - candidates == ()
        - authority_audit non-empty
        - EVERY attempt is NO_REQUESTED_MPN
        - target_enrichment_audit is None (no authority-established target)
        - target_manufacturer is None (no authority-established manufacturer)
        - target_mpn must be empty (no MPN was requested)
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

        if self.target_enrichment_audit is not None:
            raise ValueError(
                "NO_REQUESTED_MPN kind must have target_enrichment_audit=None; "
                "no authority-established target exists"
            )

        if self.target_manufacturer is not None:
            raise ValueError(
                "NO_REQUESTED_MPN kind must have target_manufacturer=None; "
                "no authority-established manufacturer may leak into an abstention result"
            )

        if self.target_mpn.strip():
            raise ValueError(
                "NO_REQUESTED_MPN kind requires an empty target_mpn; "
                "no MPN was requested for this research"
            )

    def _validate_ambiguous_authority(self) -> None:
        """AMBIGUOUS_AUTHORITY requires:
        - candidates == ()
        - authority_audit non-empty
        - ZERO fatal/incomplete outcomes:
            AUTHORITY_FETCH_FAILED
            AUTHORITY_SOURCE_REFUSED
            AUTHORITY_HOST_ESCAPED
            NO_STRUCTURAL_OBSERVATIONS
        - ZERO NO_REQUESTED_MPN
        - at least one AMBIGUOUS_MPN_MATCH OR matched_count > 1
        - MAY additionally contain NO_MPN_IN_SOURCE outcomes
        - target_enrichment_audit is None (no authority-established target)
        - target_manufacturer is None (no authority-established manufacturer)
        - target_mpn must be non-empty (original request-side MPN)
        """
        if self.candidates:
            raise ValueError(
                "AMBIGUOUS_AUTHORITY kind must have empty candidates"
            )

        # target_enrichment_audit and target_manufacturer must be None
        # (no authority-established target)
        if self.target_enrichment_audit is not None:
            raise ValueError(
                "AMBIGUOUS_AUTHORITY kind must have target_enrichment_audit=None; "
                "no authority-established target exists"
            )

        if self.target_manufacturer is not None:
            raise ValueError(
                "AMBIGUOUS_AUTHORITY kind must have target_manufacturer=None; "
                "no authority-established manufacturer may leak into an abstention result"
            )

        # target_mpn must be non-empty (original request-side MPN state)
        if not self.target_mpn.strip():
            raise ValueError(
                "AMBIGUOUS_AUTHORITY kind requires a non-empty target_mpn; "
                "this represents the original request-side MPN"
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
            # NO_MPN_IN_SOURCE is PERMITTED alongside AMBIGUOUS_MPN_MATCH
            # because ambiguity/multiple matches dominate successfully
            # evaluated non-match policies

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
