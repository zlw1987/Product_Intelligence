"""Comparable Research Authority Context (PRODUCT-INTEL.7C-PRE1).

Establishes the authority context required before production comparable
research can run. Produces, when evidence permits:

    - an established target ProductIdentity
    - the frozen ENTERPRISE_SSD_SCHEMA category binding
    - an AUTHORITATIVE SpecificationEvidenceSource
    - an AUTHORITATIVE ComparableCandidateSource
    - auditable authority-establishment provenance

Scope: Seagate Enterprise SSD using the already-proven Seagate Nytro
support catalog fixture/source and the already-proven supportSpecsData
structural mechanism.

Everything else abstains. No guessing.

Authority Rule #1: Public callers may NOT supply authority policy.
Authority Rule #2: Policy owns source authority; document owns MPN proof.
Authority Rule #3: Redirects must not escape authority boundary.

This module reuses frozen 7A structural extraction and frozen 2A part-number
comparison. No duplicate parser.
"""

from __future__ import annotations

import dataclasses
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Final
from urllib.parse import urlsplit

from product_intelligence.domain.enums import (
    ESTABLISHED_MATCH_TYPES,
    IdentityMatchType,
)
from product_intelligence.domain.models import ProductIdentity, ResearchRequest
from product_intelligence.providers.page import (
    FetchedPage,
    PageFetchError,
    PageFetchRequest,
    PageFetcher,
    UnsafeFetchTargetError,
    require_fetchable_url,
)
from product_intelligence.research.comparable_candidates import (
    ComparableCandidateObservation,
    ComparableCandidateSource,
)
from product_intelligence.research.enterprise_ssd import (
    ENTERPRISE_SSD_SCHEMA,
)
from product_intelligence.research.enterprise_ssd_candidate_extraction import (
    extract_enterprise_ssd_candidate_observations,
)
from product_intelligence.research.identity import (
    PartNumberMatchAssessment,
    compare_part_numbers,
    normalize_part_number,
)
from product_intelligence.research.specifications import (
    CategorySchema,
    SourceAuthority,
)
from product_intelligence.execution.specification_evidence import (
    SpecificationEvidenceSource,
)


# ---------------------------------------------------------------------------
# Module-private authority policy
# ---------------------------------------------------------------------------

# Canonical reviewed policies are module-private production data.
# No public injection surface. No registry. No factory. No caller supply.


@dataclass(frozen=True)
class _AuthorityPolicy:
    """One reviewed authority policy record.

    Module-private. Defines the approved source identity, URL, authority
    origin boundary, manufacturer claim, and category schema binding for one
    approved manufacturer catalog.

    This is reviewed production configuration-as-code.
    Not environment configuration, not database content, not caller input.
    """

    policy_id: str
    manufacturer: str
    source_name: str
    requested_source_url: str
    approved_authority_origin: str
    category_schema: CategorySchema

    def __post_init__(self) -> None:
        # policy_id
        if not isinstance(self.policy_id, str) or not self.policy_id.strip():
            raise ValueError("policy_id must be non-empty")
        object.__setattr__(self, "policy_id", self.policy_id.strip())

        # manufacturer
        if not isinstance(self.manufacturer, str) or not self.manufacturer.strip():
            raise ValueError("manufacturer must be non-empty")
        object.__setattr__(self, "manufacturer", self.manufacturer.strip())

        # source_name
        if not isinstance(self.source_name, str) or not self.source_name.strip():
            raise ValueError("source_name must be non-empty")
        object.__setattr__(self, "source_name", self.source_name.strip())

        # requested_source_url
        object.__setattr__(
            self,
            "requested_source_url",
            require_fetchable_url(self.requested_source_url, "requested_source_url"),
        )

        # approved_authority_origin — explicit, validated origin (scheme+host+port)
        if not isinstance(self.approved_authority_origin, str):
            raise TypeError("approved_authority_origin must be a string")
        origin_text = self.approved_authority_origin.strip()
        if not origin_text:
            raise ValueError("approved_authority_origin must not be empty")
        # Validate it is a parseable origin
        parsed = urlsplit(origin_text)
        if parsed.scheme.lower() not in ("http", "https"):
            raise ValueError(
                f"approved_authority_origin must be a valid http(s) origin, "
                f"got {origin_text!r}"
            )
        if not parsed.hostname:
            raise ValueError(
                f"approved_authority_origin must include a host, got {origin_text!r}"
            )
        object.__setattr__(
            self, "approved_authority_origin", origin_text.lower()
        )

        # category_schema
        if not isinstance(self.category_schema, CategorySchema):
            raise TypeError("category_schema must be a CategorySchema")


#: The only approved authority policies.
#: Extending this requires code review — not runtime configuration.
_AUTHORITY_POLICIES: Final[tuple[_AuthorityPolicy, ...]] = (
    _AuthorityPolicy(
        policy_id="seagate-enterprise-ssd-nytro-support-catalog-v1",
        manufacturer="Seagate",
        source_name="Seagate Enterprise Support",
        requested_source_url=(
            "https://www.seagate.com/support/enterprise-storage/"
            "solid-state-drives/nytro-5050/"
        ),
        approved_authority_origin="https://www.seagate.com",
        category_schema=ENTERPRISE_SSD_SCHEMA,
    ),
)


# ---------------------------------------------------------------------------
# Abstention vocabulary
# ---------------------------------------------------------------------------


class AuthoritySourceOutcomeState(str, Enum):
    """Bounded per-source acquisition outcome.

    Distinguishes why one approved source did not produce an authoritative
    identity match, without inventing manufacturer/category knowledge.
    """

    MATCHED = "MATCHED"
    NO_REQUESTED_MPN = "NO_REQUESTED_MPN"
    NO_MPN_IN_SOURCE = "NO_MPN_IN_SOURCE"
    AMBIGUOUS_MPN_MATCH = "AMBIGUOUS_MPN_MATCH"
    AUTHORITY_HOST_ESCAPED = "AUTHORITY_HOST_ESCAPED"
    AUTHORITY_SOURCE_REFUSED = "AUTHORITY_SOURCE_REFUSED"
    AUTHORITY_FETCH_FAILED = "AUTHORITY_FETCH_FAILED"
    NO_STRUCTURAL_OBSERVATIONS = "NO_STRUCTURAL_OBSERVATIONS"


class AuthorityAcquisitionStatus(str, Enum):
    """Result-level acquisition status derived from source outcomes.

    ESTABLISHED: exactly one authoritative match, context present.
    NO_AUTHORITY_MATCH: no source produced a matching record.
    AMBIGUOUS_AUTHORITY_MATCH: ambiguity at source or cross-policy level.
    NO_REQUESTED_MPN: request carried no MPN to match.
    """

    ESTABLISHED = "ESTABLISHED"
    NO_AUTHORITY_MATCH = "NO_AUTHORITY_MATCH"
    AMBIGUOUS_AUTHORITY_MATCH = "AMBIGUOUS_AUTHORITY_MATCH"
    NO_REQUESTED_MPN = "NO_REQUESTED_MPN"


# ---------------------------------------------------------------------------
# Per-source outcome
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class _AuthoritySourceOutcome:
    """Bounded outcome for one reviewed authority policy attempt.

    Preserves enough provenance to audit why a source matched or abstained.
    """

    policy_id: str
    outcome_state: AuthoritySourceOutcomeState
    requested_source_url: str | None = None
    fetched_final_url: str | None = None
    retrieved_at: datetime | None = None
    matching_mpn_evidence: str | None = None
    matched_observation: ComparableCandidateObservation | None = None
    part_number_match_assessment: PartNumberMatchAssessment | None = None

    def __post_init__(self) -> None:
        # outcome_state must be controlled enum
        if not isinstance(self.outcome_state, AuthoritySourceOutcomeState):
            raise TypeError(
                f"outcome_state must be AuthoritySourceOutcomeState, got "
                f"{type(self.outcome_state).__name__}"
            )

        # State-dependent invariants
        if self.outcome_state is AuthoritySourceOutcomeState.MATCHED:
            # MATCHED requires complete provenance
            if self.policy_id is None or not self.policy_id.strip():
                raise ValueError("MATCHED outcome requires policy_id")
            if self.requested_source_url is None:
                raise ValueError(
                    "MATCHED outcome requires requested_source_url"
                )
            if self.fetched_final_url is None:
                raise ValueError(
                    "MATCHED outcome requires fetched_final_url"
                )
            if self.retrieved_at is None:
                raise ValueError(
                    "MATCHED outcome requires retrieved_at"
                )
            if not isinstance(self.retrieved_at, datetime):
                raise TypeError(
                    f"retrieved_at must be a datetime, got "
                    f"{type(self.retrieved_at).__name__}"
                )
            if self.retrieved_at.tzinfo is None or self.retrieved_at.utcoffset() is None:
                raise ValueError("MATCHED outcome requires timezone-aware retrieved_at")
            if self.matching_mpn_evidence is None:
                raise ValueError(
                    "MATCHED outcome requires matching_mpn_evidence"
                )
            if self.matched_observation is None:
                raise ValueError(
                    "MATCHED outcome requires matched_observation"
                )
            if not isinstance(self.matched_observation, ComparableCandidateObservation):
                raise TypeError(
                    f"matched_observation must be ComparableCandidateObservation, "
                    f"got {type(self.matched_observation).__name__}"
                )
            if self.part_number_match_assessment is None:
                raise ValueError(
                    "MATCHED outcome requires part_number_match_assessment"
                )
            if not isinstance(
                self.part_number_match_assessment, PartNumberMatchAssessment
            ):
                raise TypeError(
                    f"part_number_match_assessment must be "
                    f"PartNumberMatchAssessment, got "
                    f"{type(self.part_number_match_assessment).__name__}"
                )

        elif self.outcome_state is AuthoritySourceOutcomeState.NO_REQUESTED_MPN:
            # NO_REQUESTED_MPN must NOT contain matched evidence
            if self.matching_mpn_evidence is not None:
                raise ValueError(
                    "NO_REQUESTED_MPN outcome must not contain matching_mpn_evidence"
                )
            if self.matched_observation is not None:
                raise ValueError(
                    "NO_REQUESTED_MPN outcome must not contain matched_observation"
                )
            if self.part_number_match_assessment is not None:
                raise ValueError(
                    "NO_REQUESTED_MPN outcome must not contain "
                    "part_number_match_assessment"
                )

        elif self.outcome_state in (
            AuthoritySourceOutcomeState.AUTHORITY_SOURCE_REFUSED,
            AuthoritySourceOutcomeState.AUTHORITY_FETCH_FAILED,
        ):
            # Refused/failed must not contain fetched-document provenance
            if self.fetched_final_url is not None:
                raise ValueError(
                    f"{self.outcome_state.value} outcome must not contain "
                    "fetched_final_url"
                )
            if self.retrieved_at is not None:
                raise ValueError(
                    f"{self.outcome_state.value} outcome must not contain "
                    "retrieved_at"
                )
            if self.matching_mpn_evidence is not None:
                raise ValueError(
                    f"{self.outcome_state.value} outcome must not contain "
                    "matching_mpn_evidence"
                )
            if self.matched_observation is not None:
                raise ValueError(
                    f"{self.outcome_state.value} outcome must not contain "
                    "matched_observation"
                )

        elif self.outcome_state is AuthoritySourceOutcomeState.AMBIGUOUS_MPN_MATCH:
            # Ambiguity: source was fetched, multiple records matched
            if self.fetched_final_url is None:
                raise ValueError(
                    "AMBIGUOUS_MPN_MATCH outcome requires fetched_final_url"
                )
            if self.retrieved_at is None:
                raise ValueError(
                    "AMBIGUOUS_MPN_MATCH outcome requires retrieved_at"
                )

        elif self.outcome_state is AuthoritySourceOutcomeState.AUTHORITY_HOST_ESCAPED:
            # Escaped: we know the final_url it escaped to
            if self.fetched_final_url is None:
                raise ValueError(
                    "AUTHORITY_HOST_ESCAPED outcome requires fetched_final_url"
                )

        elif self.outcome_state in (
            AuthoritySourceOutcomeState.NO_MPN_IN_SOURCE,
            AuthoritySourceOutcomeState.NO_STRUCTURAL_OBSERVATIONS,
        ):
            # No match / no observations: must not contain matched evidence
            if self.matching_mpn_evidence is not None:
                raise ValueError(
                    f"{self.outcome_state.value} outcome must not contain "
                    "matching_mpn_evidence"
                )
            if self.matched_observation is not None:
                raise ValueError(
                    f"{self.outcome_state.value} outcome must not contain "
                    "matched_observation"
                )


# ---------------------------------------------------------------------------
# Acquisition result (public)
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class ComparableResearchAuthorityAcquisitionResult:
    """Public result of authority-context acquisition.

    Carries either a successful ComparableResearchAuthorityContext or
    per-source abstention outcomes. Never both.

    Programming errors propagate. This result type carries only bounded
    evidence-backed outcomes.
    """

    context: ComparableResearchAuthorityContext | None
    source_outcomes: tuple[_AuthoritySourceOutcome, ...]

    @property
    def acquisition_status(self) -> AuthorityAcquisitionStatus:
        """Derive the result-level acquisition status from source outcomes.

        This is a derived property — not independently stored — so the
        status is always mechanically consistent with the actual outcomes.
        """
        has_context = self.context is not None

        # Compute source-truth metrics once
        has_ambiguous = any(
            o.outcome_state is AuthoritySourceOutcomeState.AMBIGUOUS_MPN_MATCH
            for o in self.source_outcomes
        )
        matched_count = sum(
            1 for o in self.source_outcomes
            if o.outcome_state is AuthoritySourceOutcomeState.MATCHED
        )

        # Ambiguity always overrides — even if context is somehow present
        if has_ambiguous or matched_count > 1:
            return AuthorityAcquisitionStatus.AMBIGUOUS_AUTHORITY_MATCH

        if has_context:
            return AuthorityAcquisitionStatus.ESTABLISHED

        # No context — derive from outcomes
        all_no_requested_mpn = all(
            o.outcome_state is AuthoritySourceOutcomeState.NO_REQUESTED_MPN
            for o in self.source_outcomes
        )
        if all_no_requested_mpn and self.source_outcomes:
            return AuthorityAcquisitionStatus.NO_REQUESTED_MPN

        # Ambiguity or multiple matches (already checked above, but
        # the earlier check was inside the has_ambiguous branch that
        # returns AMBIGUOUS_AUTHORITY_MATCH before reaching here)
        # This branch is reachable only when has_ambiguous is False and
        # matched_count <= 1, so we can return NO_AUTHORITY_MATCH.
        return AuthorityAcquisitionStatus.NO_AUTHORITY_MATCH

    def __post_init__(self) -> None:
        if not isinstance(self.source_outcomes, tuple):
            raise TypeError("source_outcomes must be a tuple")
        for i, outcome in enumerate(self.source_outcomes):
            if not isinstance(outcome, _AuthoritySourceOutcome):
                raise TypeError(
                    f"source_outcomes[{i}] must be _AuthoritySourceOutcome, got "
                    f"{type(outcome).__name__}"
                )

        has_context = self.context is not None

        # context type check
        if has_context:
            if not isinstance(self.context, ComparableResearchAuthorityContext):
                raise TypeError(
                    f"context must be ComparableResearchAuthorityContext or None, "
                    f"got {type(self.context).__name__}"
                )

        match_count = sum(
            1 for o in self.source_outcomes
            if o.outcome_state is AuthoritySourceOutcomeState.MATCHED
        )
        ambiguous_count = sum(
            1 for o in self.source_outcomes
            if o.outcome_state is AuthoritySourceOutcomeState.AMBIGUOUS_MPN_MATCH
        )

        # ESTABLISHED invariant: exactly one MATCHED, ZERO AMBIGUOUS,
        # context present, evidence object-identical to the one MATCHED outcome
        if has_context:
            if match_count != 1:
                raise ValueError(
                    f"ESTABLISHED result requires exactly one MATCHED source outcome, "
                    f"got {match_count}"
                )
            if ambiguous_count != 0:
                raise ValueError(
                    f"ESTABLISHED result cannot coexist with {ambiguous_count} "
                    f"AMBIGUOUS_MPN_MATCH source outcome(s). "
                    "Ambiguity evidence requires context=None."
                )
            # context.authority_evidence must be by object identity one member
            evidence_in_outcomes = any(
                o is self.context.authority_evidence
                for o in self.source_outcomes
            )
            if not evidence_in_outcomes:
                raise ValueError(
                    "ESTABLISHED result: context.authority_evidence is not "
                    "object-identical to any source_outcome member"
                )

        # NO_AUTHORITY_MATCH invariant: no MATCHED or AMBIGUOUS
        elif match_count == 0 and ambiguous_count == 0:
            # context=None and no matched outcomes — consistent
            pass

        # AMBIGUOUS_AUTHORITY_MATCH invariant: context=None with ambiguity evidence
        elif not has_context and (ambiguous_count > 0 or match_count > 1):
            # context=None and ambiguity evidence present — consistent
            pass

        # Reject impossible: context=None but exactly one MATCHED
        elif not has_context and match_count == 1:
            raise ValueError(
                "Result has exactly one MATCHED source outcome but no context. "
                "A single match must produce context."
            )

        # Reject impossible: context present but no MATCHED
        elif has_context and match_count == 0:
            raise ValueError(
                "Result has context but no source outcome is MATCHED. "
                "Context requires a matched source."
            )


# ---------------------------------------------------------------------------
# Authority Context (public, frozen, self-validating, init-closed)
# ---------------------------------------------------------------------------


@dataclass(frozen=True, init=False)
class ComparableResearchAuthorityContext:
    """Established authority context for comparable research.

    Represents a complete authority-establishment result:
        - verified target ProductIdentity (source-published MPN preserved)
        - frozen category schema binding (ENTERPRISE_SSD_SCHEMA by identity)
        - AUTHORITATIVE SpecificationEvidenceSource descriptor
        - AUTHORITATIVE ComparableCandidateSource descriptor
        - full authority-establishment provenance
        - retained frozen 7A ComparableCandidateObservation

    This class cannot be constructed directly by public callers.
    Construction is restricted to the module-private verified factory
    (_build_authority_context) which binds all fields to the canonical
    reviewed policy via object.__new__ and controlled field assignment.

    Public external code calling ComparableResearchAuthorityContext(...)
    raises TypeError because no __init__ exists.

    Constructor invariants re-derive every important binding including
    canonical policy self-audit.
    No similarity, score, ranking, recommendation, persistence, or web fields.
    """

    request: ResearchRequest
    target_identity: ProductIdentity
    category_schema: CategorySchema
    specification_source: SpecificationEvidenceSource
    comparable_source: ComparableCandidateSource
    authority_evidence: _AuthoritySourceOutcome

    def _validate(self) -> None:
        # request
        if not isinstance(self.request, ResearchRequest):
            raise TypeError(
                f"request must be a ResearchRequest, got "
                f"{type(self.request).__name__}"
            )

        # target_identity must be established
        if not isinstance(self.target_identity, ProductIdentity):
            raise TypeError(
                f"target_identity must be a ProductIdentity, got "
                f"{type(self.target_identity).__name__}"
            )
        if not self.target_identity.is_established:
            raise ValueError(
                "ComparableResearchAuthorityContext requires an established "
                f"ProductIdentity (match_type={self.target_identity.match_type.value})"
            )

        # category_schema must be ENTERPRISE_SSD_SCHEMA by exact identity
        if not isinstance(self.category_schema, CategorySchema):
            raise TypeError(
                f"category_schema must be a CategorySchema, got "
                f"{type(self.category_schema).__name__}"
            )
        if self.category_schema is not ENTERPRISE_SSD_SCHEMA:
            raise ValueError(
                "category_schema must be the frozen ENTERPRISE_SSD_SCHEMA "
                f"by exact object identity, got schema_id={self.category_schema.schema_id}"
            )

        # specification_source must be AUTHORITATIVE
        if not isinstance(self.specification_source, SpecificationEvidenceSource):
            raise TypeError(
                f"specification_source must be a SpecificationEvidenceSource, got "
                f"{type(self.specification_source).__name__}"
            )
        if self.specification_source.source_authority is not SourceAuthority.AUTHORITATIVE:
            raise ValueError(
                "specification_source must be AUTHORITATIVE, got "
                f"{self.specification_source.source_authority.value}"
            )

        # comparable_source must be AUTHORITATIVE
        if not isinstance(self.comparable_source, ComparableCandidateSource):
            raise TypeError(
                f"comparable_source must be a ComparableCandidateSource, got "
                f"{type(self.comparable_source).__name__}"
            )
        if self.comparable_source.source_authority is not SourceAuthority.AUTHORITATIVE:
            raise ValueError(
                "comparable_source must be AUTHORITATIVE, got "
                f"{self.comparable_source.source_authority.value}"
            )

        # authority_evidence must be MATCHED
        if not isinstance(self.authority_evidence, _AuthoritySourceOutcome):
            raise TypeError(
                f"authority_evidence must be _AuthoritySourceOutcome, got "
                f"{type(self.authority_evidence).__name__}"
            )
        if self.authority_evidence.outcome_state is not AuthoritySourceOutcomeState.MATCHED:
            raise ValueError(
                "authority_evidence must be MATCHED, got "
                f"{self.authority_evidence.outcome_state.value}"
            )

        # ---- Re-derive identity binding through frozen 2A ----
        comparison = compare_part_numbers(
            self.request.manufacturer_part_number,
            self.target_identity.manufacturer_part_number,
        )

        # The re-derived match type must agree with target_identity.match_type
        if comparison.match_type not in ESTABLISHED_MATCH_TYPES:
            raise ValueError(
                f"Re-derived comparison of request MPN '{self.request.manufacturer_part_number}' "
                f"vs target source MPN '{self.target_identity.manufacturer_part_number}' "
                f"yields {comparison.match_type.value}, but target_identity claims "
                f"{self.target_identity.match_type.value}. "
                "Authority context requires established identity."
            )
        if comparison.match_type is not self.target_identity.match_type:
            raise ValueError(
                f"Re-derived match_type {comparison.match_type.value} disagrees with "
                f"target_identity.match_type {self.target_identity.match_type.value}. "
                "Authority context identity must be mechanically self-consistent."
            )

        # NORMALIZED_EXACT requires normalized_part_number
        if (
            self.target_identity.match_type is IdentityMatchType.NORMALIZED_EXACT
            and not self.target_identity.normalized_part_number
        ):
            raise ValueError(
                "NORMALIZED_EXACT identity requires normalized_part_number"
            )

        # ---- Re-derive normalized key consistency ----
        if self.target_identity.normalized_part_number:
            expected_normalized = normalize_part_number(
                self.target_identity.manufacturer_part_number
            )
            if self.target_identity.normalized_part_number != expected_normalized:
                raise ValueError(
                    f"target_identity.normalized_part_number "
                    f"'{self.target_identity.normalized_part_number}' does not match "
                    f"frozen 2A normalize_part_number() output "
                    f"'{expected_normalized}' for source-published MPN "
                    f"'{self.target_identity.manufacturer_part_number}'"
                )

        # ---- specification_source.product_identity must be target_identity by object identity ----
        if self.specification_source.product_identity is not self.target_identity:
            raise ValueError(
                "specification_source.product_identity is not the same object as "
                "target_identity. Authority context must bind descriptors to the "
                "exact same target identity object."
            )

        # ---- authority_evidence.matching_mpn_evidence == target_identity.manufacturer_part_number ----
        if (
            self.authority_evidence.matching_mpn_evidence
            != self.target_identity.manufacturer_part_number
        ):
            raise ValueError(
                "authority_evidence.matching_mpn_evidence does not equal "
                "target_identity.manufacturer_part_number. "
                "Evidence must point to the exact source-published MPN."
            )

        # ---- BLOCKER 2: Canonical policy self-audit ----
        # Resolve authority_evidence.policy_id against module-private _AUTHORITY_POLICIES
        policy_id = self.authority_evidence.policy_id
        canonical_policies = [
            p for p in _AUTHORITY_POLICIES if p.policy_id == policy_id
        ]
        if len(canonical_policies) != 1:
            raise ValueError(
                f"authority_evidence.policy_id '{policy_id}' does not resolve to "
                f"exactly one canonical policy (found {len(canonical_policies)}). "
                "This is a programming/invariant error."
            )
        canonical = canonical_policies[0]

        # target_identity.manufacturer == canonical manufacturer
        if self.target_identity.manufacturer != canonical.manufacturer:
            raise ValueError(
                f"target_identity.manufacturer '{self.target_identity.manufacturer}' "
                f"does not match canonical policy manufacturer '{canonical.manufacturer}'"
            )

        # category_schema is canonical policy.category_schema
        if self.category_schema is not canonical.category_schema:
            raise ValueError(
                f"category_schema is not canonical policy.category_schema by identity. "
                f"Got schema_id={self.category_schema.schema_id}, expected "
                f"{canonical.category_schema.schema_id}"
            )

        # specification_source.source_name == canonical source_name
        if self.specification_source.source_name != canonical.source_name:
            raise ValueError(
                f"specification_source.source_name '{self.specification_source.source_name}' "
                f"does not match canonical source_name '{canonical.source_name}'"
            )

        # comparable_source.source_name == canonical source_name
        if self.comparable_source.source_name != canonical.source_name:
            raise ValueError(
                f"comparable_source.source_name '{self.comparable_source.source_name}' "
                f"does not match canonical source_name '{canonical.source_name}'"
            )

        # specification_source.source_url == canonical requested_source_url
        if self.specification_source.source_url != canonical.requested_source_url:
            raise ValueError(
                f"specification_source.source_url does not match canonical "
                f"requested_source_url"
            )

        # comparable_source.source_url == canonical requested_source_url
        if self.comparable_source.source_url != canonical.requested_source_url:
            raise ValueError(
                f"comparable_source.source_url does not match canonical "
                f"requested_source_url"
            )

        # authority_evidence.requested_source_url == canonical requested_source_url
        if self.authority_evidence.requested_source_url != canonical.requested_source_url:
            raise ValueError(
                f"authority_evidence.requested_source_url does not match canonical "
                f"requested_source_url"
            )

        # authority_evidence.fetched_final_url remains within canonical approved origin
        if self.authority_evidence.fetched_final_url is None:
            raise ValueError(
                "authority_evidence.fetched_final_url is None; required for MATCHED"
            )
        if not _final_url_within_authority_origin(
            self.authority_evidence.fetched_final_url,
            canonical.approved_authority_origin,
        ):
            raise ValueError(
                "authority_evidence.fetched_final_url has escaped canonical "
                "approved authority origin"
            )

        # matched_observation checks
        if self.authority_evidence.matched_observation is None:
            raise ValueError(
                "MATCHED authority evidence must carry matched_observation"
            )
        matched_obs = self.authority_evidence.matched_observation

        # matched_observation.source_name == canonical source_name
        if matched_obs.source_name != canonical.source_name:
            raise ValueError(
                f"matched_observation.source_name '{matched_obs.source_name}' does "
                f"not match canonical source_name '{canonical.source_name}'"
            )

        # matched_observation.source_url == canonical requested_source_url
        if matched_obs.source_url != canonical.requested_source_url:
            raise ValueError(
                f"matched_observation.source_url does not match canonical "
                f"requested_source_url"
            )

        # matched_observation.source_authority is AUTHORITATIVE
        if matched_obs.source_authority is not SourceAuthority.AUTHORITATIVE:
            raise ValueError(
                f"matched_observation.source_authority is not AUTHORITATIVE, got "
                f"{matched_obs.source_authority.value}"
            )

        # matched_observation.retrieved_at == authority_evidence.retrieved_at
        if self.authority_evidence.retrieved_at is None:
            raise ValueError(
                "authority_evidence.retrieved_at is None; required for MATCHED"
            )
        if matched_obs.retrieved_at != self.authority_evidence.retrieved_at:
            raise ValueError(
                "matched_observation.retrieved_at does not equal "
                "authority_evidence.retrieved_at"
            )

        # matched_observation.manufacturer_part_number_raw ==
        # target_identity.manufacturer_part_number
        if (
            matched_obs.manufacturer_part_number_raw
            != self.target_identity.manufacturer_part_number
        ):
            raise ValueError(
                "matched_observation.manufacturer_part_number_raw does not equal "
                "target_identity.manufacturer_part_number"
            )

        # ---- BLOCKER 3: Full frozen 2A assessment equality ----
        assessment = self.authority_evidence.part_number_match_assessment
        if assessment is None:
            raise ValueError(
                "MATCHED authority evidence must carry a "
                "part_number_match_assessment for audit."
            )
        # Re-derive: the COMPLETE assessment must match what 2A produces for
        # request MPN vs the matched observation's source MPN
        expected_assessment = compare_part_numbers(
            self.request.manufacturer_part_number,
            matched_obs.manufacturer_part_number_raw,
        )
        # Full dataclass equality — all fields must match exactly
        if assessment != expected_assessment:
            raise ValueError(
                f"authority_evidence.part_number_match_assessment does not match "
                f"the expected frozen 2A comparison result. "
                f"Got: {assessment!r}, Expected: {expected_assessment!r}"
            )
        if assessment.match_type not in ESTABLISHED_MATCH_TYPES:
            raise ValueError(
                f"authority_evidence.part_number_match_assessment.match_type "
                f"{assessment.match_type.value} is not an established match type"
            )


# ---------------------------------------------------------------------------
# Internal helper: check if final_url stays inside approved authority origin
# ---------------------------------------------------------------------------


def _normalize_origin(url: str) -> str:
    """Normalize a URL to its origin (scheme + host + effective port).

    e.g. "https://www.seagate.com/path" -> "https://www.seagate.com"
         "http://example.com:8080/" -> "http://example.com:8080"
    """
    parsed = urlsplit(url)
    scheme = parsed.scheme.lower()
    host = (parsed.hostname or "").lower()
    port = parsed.port
    # Include port only if non-default
    if port is not None and not (
        (scheme == "http" and port == 80)
        or (scheme == "https" and port == 443)
    ):
        return f"{scheme}://{host}:{port}"
    return f"{scheme}://{host}"


def _final_url_within_authority_origin(
    final_url: str,
    approved_origin: str,
) -> bool:
    """Check whether the fetched final_url origin matches the
    policy's explicit approved authority origin.

    Compares normalized scheme + hostname + effective port.
    Path changes on the same approved origin are allowed.

    This is origin boundary verification, not hostname inference.
    Authority is supplied by reviewed policy; runtime merely verifies.
    """
    try:
        final_origin = _normalize_origin(final_url)
    except Exception:
        return False

    # approved_origin is already normalized (set in __post_init__)
    approved_normalized = _normalize_origin(approved_origin)
    return final_origin == approved_normalized


# ---------------------------------------------------------------------------
# Internal helper: process one authority policy
# ---------------------------------------------------------------------------


def _process_authority_policy(
    *,
    policy: _AuthorityPolicy,
    request: ResearchRequest,
    page_fetcher: PageFetcher,
) -> _AuthoritySourceOutcome:
    """Attempt to establish authority for one reviewed policy.

    Returns a bounded _AuthoritySourceOutcome.
    Programming errors propagate.
    """

    # Guard: request must carry an MPN for authority matching
    if not request.has_manufacturer_part_number:
        return _AuthoritySourceOutcome(
            policy_id=policy.policy_id,
            outcome_state=AuthoritySourceOutcomeState.NO_REQUESTED_MPN,
            requested_source_url=policy.requested_source_url,
        )

    # Fetch the approved policy source
    try:
        fetched_page = page_fetcher.fetch(
            PageFetchRequest(url=policy.requested_source_url)
        )
    except UnsafeFetchTargetError:
        return _AuthoritySourceOutcome(
            policy_id=policy.policy_id,
            outcome_state=AuthoritySourceOutcomeState.AUTHORITY_SOURCE_REFUSED,
            requested_source_url=policy.requested_source_url,
        )
    except PageFetchError:
        return _AuthoritySourceOutcome(
            policy_id=policy.policy_id,
            outcome_state=AuthoritySourceOutcomeState.AUTHORITY_FETCH_FAILED,
            requested_source_url=policy.requested_source_url,
        )

    # Authority Rule #3: verify final_url stayed inside approved origin
    if not _final_url_within_authority_origin(
        fetched_page.final_url,
        policy.approved_authority_origin,
    ):
        return _AuthoritySourceOutcome(
            policy_id=policy.policy_id,
            outcome_state=AuthoritySourceOutcomeState.AUTHORITY_HOST_ESCAPED,
            requested_source_url=policy.requested_source_url,
            fetched_final_url=fetched_page.final_url,
        )

    # Reuse frozen 7A structural extraction
    observations = extract_enterprise_ssd_candidate_observations(
        document=fetched_page.body_text,
        source_name=policy.source_name,
        source_url=policy.requested_source_url,
        retrieved_at=fetched_page.retrieved_at,
        source_authority=SourceAuthority.AUTHORITATIVE,
    )

    if not observations:
        return _AuthoritySourceOutcome(
            policy_id=policy.policy_id,
            outcome_state=AuthoritySourceOutcomeState.NO_STRUCTURAL_OBSERVATIONS,
            requested_source_url=policy.requested_source_url,
            fetched_final_url=fetched_page.final_url,
            retrieved_at=fetched_page.retrieved_at,
        )

    # Compare each source-published MPN to the request using frozen 2A
    matching_records: list[ComparableCandidateObservation] = []
    matching_comparisons: list[PartNumberMatchAssessment] = []

    for obs in observations:
        comparison = compare_part_numbers(
            request.manufacturer_part_number,
            obs.manufacturer_part_number_raw,
        )

        if comparison.match_type in ESTABLISHED_MATCH_TYPES:
            matching_records.append(obs)
            matching_comparisons.append(comparison)

    # Zero matches across this source
    if not matching_records:
        return _AuthoritySourceOutcome(
            policy_id=policy.policy_id,
            outcome_state=AuthoritySourceOutcomeState.NO_MPN_IN_SOURCE,
            requested_source_url=policy.requested_source_url,
            fetched_final_url=fetched_page.final_url,
            retrieved_at=fetched_page.retrieved_at,
        )

    # More than one matching record across this source -> ambiguous
    if len(matching_records) > 1:
        return _AuthoritySourceOutcome(
            policy_id=policy.policy_id,
            outcome_state=AuthoritySourceOutcomeState.AMBIGUOUS_MPN_MATCH,
            requested_source_url=policy.requested_source_url,
            fetched_final_url=fetched_page.final_url,
            retrieved_at=fetched_page.retrieved_at,
        )

    # Exactly one match — return evidence for global aggregation
    matched_obs = matching_records[0]
    source_mpn = matched_obs.manufacturer_part_number_raw
    matching_comparison = matching_comparisons[0]

    return _AuthoritySourceOutcome(
        policy_id=policy.policy_id,
        outcome_state=AuthoritySourceOutcomeState.MATCHED,
        requested_source_url=policy.requested_source_url,
        fetched_final_url=fetched_page.final_url,
        retrieved_at=fetched_page.retrieved_at,
        matching_mpn_evidence=source_mpn,
        matched_observation=matched_obs,
        part_number_match_assessment=matching_comparison,
    )


# ---------------------------------------------------------------------------
# Module-private verified factory
# ---------------------------------------------------------------------------


def _build_authority_context(
    *,
    request: ResearchRequest,
    matched_outcome: _AuthoritySourceOutcome,
) -> ComparableResearchAuthorityContext:
    """Build authority context from verified matched outcome and canonical policy.

    Module-private factory. Resolves the canonical policy internally from
    matched_outcome.policy_id. This is the ONLY construction path for
    ComparableResearchAuthorityContext.

    Uses object.__new__ to bypass any public constructor and assigns fields
    directly, then validates via _validate().

    Raises ValueError if any field cannot be bound to the canonical policy.
    """
    # matched_outcome must be MATCHED
    if matched_outcome.outcome_state is not AuthoritySourceOutcomeState.MATCHED:
        raise ValueError(
            f"Cannot build authority context from non-MATCHED outcome "
            f"({matched_outcome.outcome_state.value})"
        )

    # Resolve canonical policy from matched_outcome.policy_id
    # This ensures we never accept an arbitrary caller-created _AuthorityPolicy
    policy_id = matched_outcome.policy_id
    canonical_policies = [
        p for p in _AUTHORITY_POLICIES if p.policy_id == policy_id
    ]
    if len(canonical_policies) != 1:
        raise ValueError(
            f"matched_outcome.policy_id '{policy_id}' does not resolve to "
            f"exactly one canonical policy (found {len(canonical_policies)}). "
            "This is a programming/invariant error."
        )
    policy = canonical_policies[0]

    # authority_evidence.requested_source_url == canonical policy URL
    if (
        matched_outcome.requested_source_url
        != policy.requested_source_url
    ):
        raise ValueError(
            "authority_evidence.requested_source_url does not match canonical "
            "policy requested_source_url"
        )

    # authority_evidence.fetched_final_url inside approved origin
    if matched_outcome.fetched_final_url is None:
        raise ValueError(
            "Cannot build authority context: fetched_final_url is None"
        )
    if not _final_url_within_authority_origin(
        matched_outcome.fetched_final_url,
        policy.approved_authority_origin,
    ):
        raise ValueError(
            "fetched_final_url has escaped approved authority origin boundary"
        )

    # retrieved_at must be present for MATCHED
    if matched_outcome.retrieved_at is None:
        raise ValueError(
            "Cannot build authority context: retrieved_at is None for MATCHED outcome"
        )

    # authority evidence source MPN == target identity source MPN
    matched_obs = matched_outcome.matched_observation
    if matched_obs is None:
        raise ValueError(
            "Cannot build authority context: matched_observation is None"
        )
    if (
        matched_obs.manufacturer_part_number_raw
        != matched_outcome.matching_mpn_evidence
    ):
        raise ValueError(
            "matched_observation MPN does not match authority_evidence MPN"
        )

    # target_identity.manufacturer == canonical policy manufacturer
    source_mpn = matched_outcome.matching_mpn_evidence
    if source_mpn is None:
        raise ValueError(
            "Cannot build authority context: matching_mpn_evidence is None"
        )

    comparison = matched_outcome.part_number_match_assessment
    if comparison is None:
        raise ValueError(
            "Cannot build authority context: part_number_match_assessment is None"
        )

    match_type = comparison.match_type
    normalized_key = normalize_part_number(source_mpn)

    target_identity = ProductIdentity(
        manufacturer=policy.manufacturer,
        manufacturer_part_number=source_mpn,
        normalized_part_number=normalized_key
        if match_type is IdentityMatchType.NORMALIZED_EXACT
        else None,
        match_type=match_type,
    )

    # Build authoritative source descriptors from the exact policy
    specification_source = SpecificationEvidenceSource(
        product_identity=target_identity,
        source_name=policy.source_name,
        source_url=policy.requested_source_url,
        source_authority=SourceAuthority.AUTHORITATIVE,
    )

    comparable_source = ComparableCandidateSource(
        source_name=policy.source_name,
        source_url=policy.requested_source_url,
        source_authority=SourceAuthority.AUTHORITATIVE,
    )

    # Construct via object.__new__ (no public __init__ exists)
    context = object.__new__(ComparableResearchAuthorityContext)
    object.__setattr__(context, "request", request)
    object.__setattr__(context, "target_identity", target_identity)
    object.__setattr__(context, "category_schema", policy.category_schema)
    object.__setattr__(context, "specification_source", specification_source)
    object.__setattr__(context, "comparable_source", comparable_source)
    object.__setattr__(context, "authority_evidence", matched_outcome)

    # Run full self-validation (canonical policy audit + all invariants)
    context._validate()

    return context


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------


def acquire_comparable_research_authority_context(
    *,
    request: ResearchRequest,
    page_fetcher: PageFetcher,
) -> ComparableResearchAuthorityAcquisitionResult:
    """Acquire the authority context required for comparable research.

    Public production function. No policy, source, manufacturer, category,
    or extraction mechanism injection. Authority policy is module-private
    reviewed configuration-as-code.

    Pipeline:
    1. Validate inputs
    2. For each approved authority policy:
       a. Fetch the approved source URL via injected PageFetcher
       b. Verify final_url stayed inside approved authority origin boundary
       c. Run frozen 7A structural extraction (supportSpecsData)
       d. Compare each source-published MPN to request via frozen 2A
       e. Require exactly one EXACT/NORMALIZED_EXACT match
    3. Aggregate all policy outcomes
    4. If exactly one policy produces exactly one match -> establish context
    5. If zero matches -> abstain with per-source outcomes (NO_AUTHORITY_MATCH)
    6. If multiple matches across policies -> fail closed as ambiguous
    7. If any source has multiple matching records -> fail closed as ambiguous

    Parameters
    ----------
    request : ResearchRequest
        The research request to establish authority for.
    page_fetcher : PageFetcher
        Page acquisition protocol (injected dependency).

    Returns
    -------
    ComparableResearchAuthorityAcquisitionResult
        Contains either an authority context or per-source abstention outcomes.

    Raises
    ------
    TypeError
        If request is not a ResearchRequest.
    """
    # Validate inputs
    if not isinstance(request, ResearchRequest):
        raise TypeError(
            f"request must be a ResearchRequest, got {type(request).__name__}"
        )

    # Process each approved policy — collect all outcomes first
    outcomes: list[_AuthoritySourceOutcome] = []

    for policy in _AUTHORITY_POLICIES:
        outcome = _process_authority_policy(
            policy=policy,
            request=request,
            page_fetcher=page_fetcher,
        )
        outcomes.append(outcome)

    # Aggregate ALL outcomes before deciding (BLOCKER 4)
    # Check for ANY ambiguity first
    has_ambiguous = any(
        o.outcome_state is AuthoritySourceOutcomeState.AMBIGUOUS_MPN_MATCH
        for o in outcomes
    )

    matched_outcomes: list[tuple[_AuthorityPolicy, _AuthoritySourceOutcome]] = []
    for policy, outcome in zip(_AUTHORITY_POLICIES, outcomes):
        if outcome.outcome_state is AuthoritySourceOutcomeState.MATCHED:
            matched_outcomes.append((policy, outcome))

    # Decision order: ambiguity > multiple matches > single match > abstention
    if has_ambiguous:
        # ANY source ambiguity fails closed
        return ComparableResearchAuthorityAcquisitionResult(
            context=None,
            source_outcomes=tuple(outcomes),
        )
    elif len(matched_outcomes) > 1:
        # Multiple policies independently matched -> ambiguous
        return ComparableResearchAuthorityAcquisitionResult(
            context=None,
            source_outcomes=tuple(outcomes),
        )
    elif len(matched_outcomes) == 1:
        # Exactly one policy produced exactly one match -> establish
        _, matched_outcome = matched_outcomes[0]
        context = _build_authority_context(
            request=request,
            matched_outcome=matched_outcome,
        )
        return ComparableResearchAuthorityAcquisitionResult(
            context=context,
            source_outcomes=tuple(outcomes),
        )
    else:
        # No matches -> bounded abstention
        return ComparableResearchAuthorityAcquisitionResult(
            context=None,
            source_outcomes=tuple(outcomes),
        )
