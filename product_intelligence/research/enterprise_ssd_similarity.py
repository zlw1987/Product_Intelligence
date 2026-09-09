"""Enterprise SSD deterministic similarity scoring (PRODUCT-INTEL.7B).

Given verified specification evidence for a target and a discovered candidate,
compute how similar their observable specifications are.

This module is PURE: no I/O, no providers, no Django, no network, no LLM,
no candidate discovery, and no ranking.

7B answers:
    "Given verified specification evidence for the target and candidate,
     how similar are their observable specifications?"

7B does NOT answer:
    "Is this drive guaranteed compatible?"
    "Can this drive replace the target?"
    "Which one should the user buy?"
    "Which candidate is best?"

Similarity != compatibility certification.

No score, rank, recommendation, or compatibility label is produced.
Only auditable field-level similarity evidence.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from enum import Enum

from product_intelligence.domain.enums import IdentityMatchType
from product_intelligence.domain.models import ProductIdentity
from product_intelligence.research.comparable_candidates import (
    ComparableCandidate,
)
from product_intelligence.research.enterprise_ssd import (
    ENTERPRISE_SSD_SCHEMA,
)
from product_intelligence.research.specifications import (
    ProductSpecificationSet,
    ResolutionState,
    SpecificationDefinition,
    SpecificationResolution,
    SourceAuthority,
)


# ---------------------------------------------------------------------------
# 7B bridge: ComparableCandidate -> ProductIdentity
# ---------------------------------------------------------------------------
#
# 7A deliberately did NOT reuse ProductIdentity for discovered candidates.
# 7B now requires candidate ProductIdentity because frozen 6C specification
# extraction/resolution requires ProductIdentity.
#
# This bridge is evidence-backed: all candidate evidence is AUTHORITATIVE
# (guaranteed by frozen 7A), all evidence binds to the exact same target
# identity (frozen 7A invariant), and the candidate's own MPN is established
# by the AUTHORITATIVE manufacturer catalog that explicitly published it.


def establish_candidate_product_identity(
    candidate: ComparableCandidate,
) -> ProductIdentity:
    """Establish a ProductIdentity for a discovered candidate.

    Bridge from ComparableCandidate (7A discovery output) to ProductIdentity
    (required by frozen 6C specification extraction).

    Rules:
        - candidate.manufacturer_part_number becomes the identity's MPN
        - candidate.normalized_part_number becomes the identity's normalized MPN
        - match_type = EXACT (the AUTHORITATIVE manufacturer catalog explicitly
          published the candidate's skuNumber; this establishes the candidate's
          own MPN for specification research)
        - manufacturer = None (NOT guessed from source hostname, source name,
          or target manufacturer)
        - product_name = None (NOT inferred from evidence titles)

    The EXACT match_type here means "the candidate's own MPN is established by
    authoritative evidence." It does NOT mean the candidate equals the target.
    Candidate/target relationship remains a 7A/7B concern.

    Raises:
        TypeError: candidate is not a ComparableCandidate.
        ValueError: candidate has no evidence, or evidence is not all
            AUTHORITATIVE, or evidence binds to different target identities.
    """
    if type(candidate) is not ComparableCandidate:
        raise TypeError(
            f"candidate must be a ComparableCandidate, got "
            f"{type(candidate).__name__}"
        )

    # ComparableCandidate.__post_init__ already validates:
    #   - evidence is non-empty
    #   - all evidence is CANDIDATE disposition
    #   - all evidence shares the same target_identity
    #   - all evidence normalizes to the same key
    #   - all evidence is AUTHORITATIVE
    # We re-check the AUTHORITATIVE invariant explicitly for safety.

    if not candidate.evidence:
        raise ValueError(
            "Cannot establish product identity for a candidate with no evidence"
        )

    # Re-check AUTHORITATIVE invariant
    for i, assessment in enumerate(candidate.evidence):
        if (
            assessment.observation.source_authority
            is not SourceAuthority.AUTHORITATIVE
        ):
            raise ValueError(
                f"Cannot establish product identity from non-AUTHORITATIVE "
                f"evidence[{i}] (authority={assessment.observation.source_authority.value}). "
                "Only AUTHORITATIVE evidence establishes candidate identity."
            )

    # Re-check all evidence binds to the same target identity
    canonical_target = candidate.evidence[0].target_identity
    for i, assessment in enumerate(candidate.evidence):
        if assessment.target_identity is not canonical_target:
            raise ValueError(
                f"Candidate evidence[{i}] binds to a different target_identity "
                "than evidence[0]. All evidence must bind to the same target."
            )

    return ProductIdentity(
        manufacturer=None,
        manufacturer_part_number=candidate.manufacturer_part_number,
        normalized_part_number=candidate.normalized_part_number,
        product_name=None,
        product_family=None,
        category=None,
        match_type=IdentityMatchType.EXACT,
    )


# ---------------------------------------------------------------------------
# ComparableCandidateSpecificationProfile
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class ComparableCandidateSpecificationProfile:
    """Binds a discovered candidate to its researched specification set.

    This object says "these specifications belong to this discovered candidate."
    It does NOT say the candidate is similar to the target — that is 7B's job.

    Self-validating invariants:
        - candidate is EXACTLY a ComparableCandidate (exact type)
        - candidate_identity is EXACTLY a ProductIdentity (exact type)
        - candidate_identity is established
        - candidate_identity is the EXACT output of
          establish_candidate_product_identity(candidate) — same MPN, same
          normalized key, EXACT match type, manufacturer/product_name/
          product_family/category all None, bridge/default confidence
        - specification_set is a ProductSpecificationSet
        - specification_set.product_identity is candidate_identity
        - specification_set.category_schema is ENTERPRISE_SSD_SCHEMA
    """

    candidate: ComparableCandidate
    candidate_identity: ProductIdentity
    specification_set: ProductSpecificationSet

    def __post_init__(self) -> None:
        # candidate — EXACT type (7A frozen contract object, no substitutes)
        if type(self.candidate) is not ComparableCandidate:
            raise TypeError(
                f"candidate must be a ComparableCandidate, got "
                f"{type(self.candidate).__name__}"
            )

        # candidate_identity — EXACT type (no subclasses, no substitutes)
        if type(self.candidate_identity) is not ProductIdentity:
            raise TypeError(
                f"candidate_identity must be a ProductIdentity, got "
                f"{type(self.candidate_identity).__name__}"
            )
        if not self.candidate_identity.is_established:
            raise ValueError(
                "candidate_identity must be established for specification "
                "binding; got match_type="
                f"{self.candidate_identity.match_type.value}"
            )

        # candidate_identity must be the EXACT bridge output. The bridge is
        # re-run against this candidate and the supplied identity must equal
        # it in every field: MPN, normalized key, EXACT match type, and
        # manufacturer/product_name/product_family/category all None with the
        # bridge/default confidence. Callers may not enrich the identity.
        expected_identity = establish_candidate_product_identity(self.candidate)
        if self.candidate_identity != expected_identity:
            raise ValueError(
                "candidate_identity is not the exact output of "
                "establish_candidate_product_identity() for this candidate. "
                "The 7B bridge is the only identity authority for a "
                "discovered candidate; candidate specification facts belong "
                "in the ProductSpecificationSet, not in ProductIdentity "
                "metadata."
            )

        # specification_set type
        if not isinstance(self.specification_set, ProductSpecificationSet):
            raise TypeError(
                f"specification_set must be a ProductSpecificationSet, got "
                f"{type(self.specification_set).__name__}"
            )

        # specification_set identity must be candidate_identity (same object)
        if (
            self.specification_set.product_identity
            is not self.candidate_identity
        ):
            raise ValueError(
                "specification_set.product_identity is not the same object as "
                "candidate_identity. The spec set must be bound to the exact "
                "candidate identity."
            )

        # specification_set schema must be ENTERPRISE_SSD_SCHEMA
        if (
            self.specification_set.category_schema
            is not ENTERPRISE_SSD_SCHEMA
        ):
            raise ValueError(
                "specification_set.category_schema is not "
                "ENTERPRISE_SSD_SCHEMA. Only the Enterprise SSD schema is "
                "supported for 7B similarity scoring."
            )


# ---------------------------------------------------------------------------
# Comparison states
# ---------------------------------------------------------------------------


class ComparisonState(str, Enum):
    """The comparison state for one specification field.

    SCORED — both target and candidate are VERIFIED; similarity is computed.
    TARGET_NOT_VERIFIED — target resolution is not VERIFIED.
    CANDIDATE_NOT_VERIFIED — candidate resolution is not VERIFIED.
    BOTH_NOT_VERIFIED — neither side is VERIFIED.

    UNKNOWN / UNVERIFIED / CONFLICT are NOT mismatches.
    They mean evidence is unavailable / non-authoritative / conflicting.
    """

    SCORED = "SCORED"
    TARGET_NOT_VERIFIED = "TARGET_NOT_VERIFIED"
    CANDIDATE_NOT_VERIFIED = "CANDIDATE_NOT_VERIFIED"
    BOTH_NOT_VERIFIED = "BOTH_NOT_VERIFIED"


# ---------------------------------------------------------------------------
# SpecificationSimilarityFieldAssessment
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class SpecificationSimilarityFieldAssessment:
    """Similarity assessment for one specification field.

    Binds:
        - the specification definition
        - the target resolution
        - the candidate resolution
        - the comparison state (SCORED or a not-verified state)
        - the field similarity (Decimal 0-1, only when SCORED)

    Self-validating:
        - comparison_state is re-derived from resolution states
        - field_similarity is re-derived when SCORED
    """

    definition: SpecificationDefinition
    target_resolution: SpecificationResolution
    candidate_resolution: SpecificationResolution
    comparison_state: ComparisonState
    field_similarity: Decimal | None

    def __post_init__(self) -> None:
        # Types
        if not isinstance(self.definition, SpecificationDefinition):
            raise TypeError(
                f"definition must be a SpecificationDefinition, got "
                f"{type(self.definition).__name__}"
            )
        if not isinstance(self.target_resolution, SpecificationResolution):
            raise TypeError(
                f"target_resolution must be a SpecificationResolution, got "
                f"{type(self.target_resolution).__name__}"
            )
        if not isinstance(self.candidate_resolution, SpecificationResolution):
            raise TypeError(
                f"candidate_resolution must be a SpecificationResolution, got "
                f"{type(self.candidate_resolution).__name__}"
            )

        # All resolutions must be for the same definition
        if self.target_resolution.definition is not self.definition:
            raise ValueError(
                f"target_resolution definition key "
                f"{self.target_resolution.definition.key!r} does not match "
                f"assessment definition key {self.definition.key!r}"
            )
        if self.candidate_resolution.definition is not self.definition:
            raise ValueError(
                f"candidate_resolution definition key "
                f"{self.candidate_resolution.definition.key!r} does not match "
                f"assessment definition key {self.definition.key!r}"
            )

        # comparison_state type
        if not isinstance(self.comparison_state, ComparisonState):
            raise TypeError(
                f"comparison_state must be a ComparisonState, got "
                f"{type(self.comparison_state).__name__}"
            )

        # Re-derive comparison_state from resolution states
        target_verified = (
            self.target_resolution.state is ResolutionState.VERIFIED
        )
        candidate_verified = (
            self.candidate_resolution.state is ResolutionState.VERIFIED
        )

        if target_verified and candidate_verified:
            expected_state = ComparisonState.SCORED
        elif target_verified:
            expected_state = ComparisonState.CANDIDATE_NOT_VERIFIED
        elif candidate_verified:
            expected_state = ComparisonState.TARGET_NOT_VERIFIED
        else:
            expected_state = ComparisonState.BOTH_NOT_VERIFIED

        if self.comparison_state is not expected_state:
            raise ValueError(
                f"comparison_state {self.comparison_state.value} does not match "
                f"the re-derived state {expected_state.value} for "
                f"target state {self.target_resolution.state.value} and "
                f"candidate state {self.candidate_resolution.state.value}"
            )

        # When SCORED, field_similarity must be the EXACT re-derived score.
        # The supplied value is never trusted: the production formula is
        # recomputed here and the supplied value must equal it.
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
            expected_similarity = _compute_field_similarity(
                self.definition,
                self.target_resolution,
                self.candidate_resolution,
            )
            if self.field_similarity != expected_similarity:
                raise ValueError(
                    f"field_similarity {self.field_similarity} does not match "
                    f"the re-derived score {expected_similarity} for "
                    f"definition '{self.definition.key}'. "
                    "field_similarity is computed, never supplied."
                )
        else:
            # Non-SCORED states must have None similarity
            if self.field_similarity is not None:
                raise ValueError(
                    f"Non-SCORED comparison state "
                    f"{self.comparison_state.value} must have "
                    "field_similarity=None, got "
                    f"{self.field_similarity!r}"
                )


# ---------------------------------------------------------------------------
# Field similarity computation
# ---------------------------------------------------------------------------


def _compute_field_similarity(
    definition: SpecificationDefinition,
    target_resolution: SpecificationResolution,
    candidate_resolution: SpecificationResolution,
) -> Decimal:
    """Compute similarity for one field where both sides are VERIFIED.

    Uses the frozen SpecificationDefinition.value_kind:

    TEXT — exact canonical string equality: 1 if equal, 0 if not.
    ENUM — exact canonical enum string equality: 1 if equal, 0 if not.
    BOOLEAN — exact equality: 1 if equal, 0 if not.
    DECIMAL — min(target, candidate) / max(target, candidate) for
              positive values. Programming error if invalid.

    Both resolutions MUST be VERIFIED when this is called.
    """
    target_value = target_resolution.resolved_value
    candidate_value = candidate_resolution.resolved_value

    if target_value is None or candidate_value is None:
        # Should not happen if both are VERIFIED, but fail closed
        raise ValueError(
            "Cannot compute similarity: VERIFIED resolution has no "
            "resolved_value. This is a contract error."
        )

    if definition.value_kind.value == "TEXT":
        return Decimal("1") if target_value.value == candidate_value.value else Decimal("0")

    if definition.value_kind.value == "ENUM":
        return Decimal("1") if target_value.value == candidate_value.value else Decimal("0")

    if definition.value_kind.value == "BOOLEAN":
        return Decimal("1") if target_value.value == candidate_value.value else Decimal("0")

    if definition.value_kind.value == "DECIMAL":
        t = target_value.value
        c = candidate_value.value

        # Both must be Decimal (frozen 6B contract)
        if type(t) is not Decimal or type(c) is not Decimal:
            raise ValueError(
                f"DECIMAL field '{definition.key}' has non-Decimal canonical "
                f"value: target {type(t).__name__}, candidate {type(c).__name__}. "
                "This is a frozen 6B contract error."
            )

        # Must be finite and positive (frozen 6B contract)
        if not t.is_finite() or not c.is_finite():
            raise ValueError(
                f"DECIMAL field '{definition.key}' has non-finite canonical "
                f"value: target {t}, candidate {c}. This is a contract error."
            )
        if t <= 0 or c <= 0:
            raise ValueError(
                f"DECIMAL field '{definition.key}' has non-positive canonical "
                f"value: target {t}, candidate {c}. This is a contract error."
            )

        min_val = min(t, c)
        max_val = max(t, c)
        return min_val / max_val

    # Unknown value kind — programming error
    raise ValueError(
        f"Unknown value_kind '{definition.value_kind.value}' for definition "
        f"'{definition.key}'. This is a programming error."
    )


# ---------------------------------------------------------------------------
# EnterpriseSsdCandidateSimilarity
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class EnterpriseSsdCandidateSimilarity:
    """Complete similarity assessment for one candidate against the target.

    Self-validating: the constructor re-derives every computed field from
    the raw specification resolutions. A caller cannot fabricate a higher
    score, fake coverage, drop a mismatch field, or substitute resolutions.

    Fields:
        candidate_profile — the candidate's specification profile
        target_specification_set — the target's complete spec set
        field_assessments — exactly 12 assessments (one per schema definition)
        scored_field_count — number of assessments with SCORED state
        evidence_coverage — scored_field_count / 12
        observed_similarity — mean of scored field similarities (None if 0 scored)
        evidence_weighted_similarity — sum of scored similarities / 12
            (None if 0 scored)

    Note: evidence_weighted_similarity == observed_similarity * evidence_coverage
    (subject only to exact Decimal arithmetic)
    """

    candidate_profile: ComparableCandidateSpecificationProfile
    target_specification_set: ProductSpecificationSet
    field_assessments: tuple[SpecificationSimilarityFieldAssessment, ...]
    scored_field_count: int
    evidence_coverage: Decimal
    observed_similarity: Decimal | None
    evidence_weighted_similarity: Decimal | None

    def __post_init__(self) -> None:
        # --- Exact scalar types (bool/int/float substitutes rejected even
        #     though they may compare numerically equal) ---
        if type(self.scored_field_count) is not int:
            raise TypeError(
                f"scored_field_count must be an int, got "
                f"{type(self.scored_field_count).__name__}"
            )
        if type(self.evidence_coverage) is not Decimal:
            raise TypeError(
                f"evidence_coverage must be a Decimal, got "
                f"{type(self.evidence_coverage).__name__}"
            )
        if self.observed_similarity is not None and type(
            self.observed_similarity
        ) is not Decimal:
            raise TypeError(
                f"observed_similarity must be a Decimal or None, got "
                f"{type(self.observed_similarity).__name__}"
            )
        if self.evidence_weighted_similarity is not None and type(
            self.evidence_weighted_similarity
        ) is not Decimal:
            raise TypeError(
                f"evidence_weighted_similarity must be a Decimal or None, got "
                f"{type(self.evidence_weighted_similarity).__name__}"
            )

        # --- Type checks ---
        if not isinstance(self.candidate_profile, ComparableCandidateSpecificationProfile):
            raise TypeError(
                f"candidate_profile must be a ComparableCandidateSpecificationProfile, "
                f"got {type(self.candidate_profile).__name__}"
            )
        if not isinstance(self.target_specification_set, ProductSpecificationSet):
            raise TypeError(
                f"target_specification_set must be a ProductSpecificationSet, got "
                f"{type(self.target_specification_set).__name__}"
            )

        # --- candidate_profile identity binding ---
        if (
            self.candidate_profile.specification_set.product_identity
            is not self.candidate_profile.candidate_identity
        ):
            raise ValueError(
                "candidate_profile's specification_set is not bound to its "
                "own candidate_identity"
            )

        # --- target_specification_set schema must match ---
        if (
            self.target_specification_set.category_schema
            is not ENTERPRISE_SSD_SCHEMA
        ):
            raise ValueError(
                "target_specification_set schema is not ENTERPRISE_SSD_SCHEMA"
            )

        # --- field_assessments: exactly 12, one per schema definition ---
        if not isinstance(self.field_assessments, tuple):
            raise TypeError(
                f"field_assessments must be a tuple, got "
                f"{type(self.field_assessments).__name__}"
            )

        schema_definitions = tuple(
            ENTERPRISE_SSD_SCHEMA.definitions.values()
        )

        if len(self.field_assessments) != len(schema_definitions):
            raise ValueError(
                f"field_assessments has {len(self.field_assessments)} items, "
                f"but ENTERPRISE_SSD_SCHEMA has {len(schema_definitions)} "
                "definitions. Every definition must have exactly one assessment."
            )

        # --- Re-derive every field assessment and compare ---
        scored_similarities: list[Decimal] = []

        for i, (definition, assessment) in enumerate(
            zip(schema_definitions, self.field_assessments)
        ):
            if not isinstance(assessment, SpecificationSimilarityFieldAssessment):
                raise TypeError(
                    f"field_assessments[{i}] must be a "
                    "SpecificationSimilarityFieldAssessment, got "
                    f"{type(assessment).__name__}"
                )

            # Assessment definition must match schema definition
            if assessment.definition is not definition:
                raise ValueError(
                    f"field_assessments[{i}] definition key "
                    f"{assessment.definition.key!r} does not match schema "
                    f"definition order (expected {definition.key!r}). "
                    "Assessment order must match schema definition order."
                )

            # Assessment target resolution must be the exact resolution from
            # target_specification_set
            target_res = self.target_specification_set.resolutions.get(
                definition.key
            )
            if target_res is None:
                raise ValueError(
                    f"target_specification_set has no resolution for "
                    f"'{definition.key}'. The target spec set must be complete."
                )
            if assessment.target_resolution is not target_res:
                raise ValueError(
                    f"field_assessments[{i}] target_resolution is not the "
                    f"exact resolution from target_specification_set for "
                    f"'{definition.key}'. Resolutions must not be substituted."
                )

            # Assessment candidate resolution must be the exact resolution from
            # candidate profile's spec set
            candidate_res = (
                self.candidate_profile.specification_set.resolutions.get(
                    definition.key
                )
            )
            if candidate_res is None:
                raise ValueError(
                    f"candidate profile's specification_set has no resolution "
                    f"for '{definition.key}'. The candidate spec set must be "
                    "complete."
                )
            if assessment.candidate_resolution is not candidate_res:
                raise ValueError(
                    f"field_assessments[{i}] candidate_resolution is not the "
                    f"exact resolution from candidate specification_set for "
                    f"'{definition.key}'. Resolutions must not be substituted."
                )

            # Collect scored similarities for aggregate check
            if assessment.comparison_state is ComparisonState.SCORED:
                scored_similarities.append(assessment.field_similarity)

        # --- Re-derive scored_field_count ---
        expected_scored_count = len(scored_similarities)
        if self.scored_field_count != expected_scored_count:
            raise ValueError(
                f"scored_field_count {self.scored_field_count} does not match "
                f"re-derived count {expected_scored_count}"
            )

        # --- Re-derive evidence_coverage ---
        total_definitions = Decimal(len(schema_definitions))
        expected_coverage = Decimal(expected_scored_count) / total_definitions
        if self.evidence_coverage != expected_coverage:
            raise ValueError(
                f"evidence_coverage {self.evidence_coverage} does not match "
                f"re-derived coverage {expected_coverage}"
            )

        # --- Re-derive observed_similarity and evidence_weighted_similarity ---
        if expected_scored_count == 0:
            if self.observed_similarity is not None:
                raise ValueError(
                    "observed_similarity must be None when scored_field_count is 0"
                )
            if self.evidence_weighted_similarity is not None:
                raise ValueError(
                    "evidence_weighted_similarity must be None when "
                    "scored_field_count is 0"
                )
        else:
            if self.observed_similarity is None:
                raise ValueError(
                    "observed_similarity must not be None when "
                    "scored_field_count > 0"
                )
            if self.evidence_weighted_similarity is None:
                raise ValueError(
                    "evidence_weighted_similarity must not be None when "
                    "scored_field_count > 0"
                )

            # observed_similarity = sum(scored) / scored_count
            sum_scored = sum(scored_similarities, Decimal("0"))
            expected_observed = sum_scored / Decimal(expected_scored_count)
            if self.observed_similarity != expected_observed:
                raise ValueError(
                    f"observed_similarity {self.observed_similarity} does not "
                    f"match re-derived value {expected_observed}"
                )

            # evidence_weighted_similarity = sum(scored) / total_definitions
            expected_weighted = sum_scored / total_definitions
            if self.evidence_weighted_similarity != expected_weighted:
                raise ValueError(
                    f"evidence_weighted_similarity {self.evidence_weighted_similarity} "
                    f"does not match re-derived value {expected_weighted}"
                )


# ---------------------------------------------------------------------------
# Pure scoring function
# ---------------------------------------------------------------------------


def score_enterprise_ssd_candidate_similarity(
    *,
    target_specification_set: ProductSpecificationSet,
    candidate_profile: ComparableCandidateSpecificationProfile,
) -> EnterpriseSsdCandidateSimilarity:
    """Compute deterministic similarity between target and candidate specs.

    PURE function. No I/O, no providers, no network, no LLM.

    For each of the 12 ENTERPRISE_SSD_SCHEMA definitions:
        1. Get target resolution from target_specification_set
        2. Get candidate resolution from candidate_profile.specification_set
        3. Determine comparison state (SCORED only if both VERIFIED)
        4. Compute field similarity if SCORED

    All fields have equal weight (no domain-business weights in 7B v1).

    Parameters
    ----------
    target_specification_set : ProductSpecificationSet
        Complete specification set for the target product.
    candidate_profile : ComparableCandidateSpecificationProfile
        Candidate's specification profile (candidate + identity + spec set).

    Returns
    -------
    EnterpriseSsdCandidateSimilarity
        Complete auditable similarity assessment.

    Raises
    ------
    ValueError
        If inputs are inconsistent (wrong schema, incomplete spec sets, etc.)
    TypeError
        If inputs are wrong type.
    """
    # Validate target spec set
    if not isinstance(target_specification_set, ProductSpecificationSet):
        raise TypeError(
            f"target_specification_set must be a ProductSpecificationSet, got "
            f"{type(target_specification_set).__name__}"
        )
    if (
        target_specification_set.category_schema
        is not ENTERPRISE_SSD_SCHEMA
    ):
        raise ValueError(
            "target_specification_set schema is not ENTERPRISE_SSD_SCHEMA"
        )

    # Validate candidate profile
    if not isinstance(candidate_profile, ComparableCandidateSpecificationProfile):
        raise TypeError(
            f"candidate_profile must be a ComparableCandidateSpecificationProfile, "
            f"got {type(candidate_profile).__name__}"
        )

    # Compute field assessments in schema definition order
    field_assessments: list[SpecificationSimilarityFieldAssessment] = []

    for definition in ENTERPRISE_SSD_SCHEMA.definitions.values():
        target_res = target_specification_set.resolutions[definition.key]
        candidate_res = candidate_profile.specification_set.resolutions[
            definition.key
        ]

        target_verified = target_res.state is ResolutionState.VERIFIED
        candidate_verified = candidate_res.state is ResolutionState.VERIFIED

        if target_verified and candidate_verified:
            comparison_state = ComparisonState.SCORED
            field_similarity = _compute_field_similarity(
                definition, target_res, candidate_res
            )
        elif target_verified:
            comparison_state = ComparisonState.CANDIDATE_NOT_VERIFIED
            field_similarity = None
        elif candidate_verified:
            comparison_state = ComparisonState.TARGET_NOT_VERIFIED
            field_similarity = None
        else:
            comparison_state = ComparisonState.BOTH_NOT_VERIFIED
            field_similarity = None

        field_assessments.append(
            SpecificationSimilarityFieldAssessment(
                definition=definition,
                target_resolution=target_res,
                candidate_resolution=candidate_res,
                comparison_state=comparison_state,
                field_similarity=field_similarity,
            )
        )

    # Aggregate
    scored_assessments = [
        a for a in field_assessments
        if a.comparison_state is ComparisonState.SCORED
    ]
    scored_field_count = len(scored_assessments)

    total_definitions = Decimal(len(ENTERPRISE_SSD_SCHEMA.definitions))
    evidence_coverage = Decimal(scored_field_count) / total_definitions

    if scored_field_count == 0:
        observed_similarity = None
        evidence_weighted_similarity = None
    else:
        sum_scored = sum(
            (a.field_similarity for a in scored_assessments),
            Decimal("0"),
        )
        observed_similarity = sum_scored / Decimal(scored_field_count)
        evidence_weighted_similarity = sum_scored / total_definitions

    return EnterpriseSsdCandidateSimilarity(
        candidate_profile=candidate_profile,
        target_specification_set=target_specification_set,
        field_assessments=tuple(field_assessments),
        scored_field_count=scored_field_count,
        evidence_coverage=evidence_coverage,
        observed_similarity=observed_similarity,
        evidence_weighted_similarity=evidence_weighted_similarity,
    )
