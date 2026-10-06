"""Semantic Authority Contract V2 — frozen vocabulary and derivation (S2-A).

PRODUCT-INTEL.SEMANTIC-AUTHORITY-V2-S2-A is a **bounded contract-only phase**:
it establishes the V2 deterministic state overlay vocabulary, the bounded
near-miss relationship signals, the structured conflict taxonomy, the context
provenance classes, the authority-tier matrix, and the future UI display
vocabulary **in code**. It wires nothing into production:

* V2 is NOT called from execution, semantic, runs, web, or providers.
* The frozen 2A comparator, 3C assessment, rejection reasons, Price
  Intelligence Snapshot V1, 4A aggregation, the current semantic V1 contract
  (prompt v1.1, parser, runtime route, eligibility), and the V1 human-review
  eligibility predicate are unchanged.
* No DB migration, no AI call, no UI behavior, no replay behavior, no
  deployment. Production behavior after S2-A is identical to the starting
  SHA; V3 qualification has NOT happened and AI authority has NOT expanded.

What this module is
-------------------

A pure, deterministic overlay over the frozen ``ListingIdentityAssessment``
(3C). It consumes only frozen deterministic facts — the assessment's recorded
decision, rejection reason, evidence source, match type, and the identifier
strings it already carries — and re-derives the frozen 2A normalized keys
through the existing comparator (the same call 3C itself makes in its
constructor invariants). No database, no Django, no network, no LLM, no
mutable global state, no clock.

The V2 states

* ``DETERMINISTIC_VERIFIED``   — the frozen 3C assessment ACCEPTED identity
  (EXACT / NORMALIZED_EXACT). Machine authority; no AI needed.
* ``DETERMINISTIC_UNCERTAIN``  — the frozen 3C assessment REJECTED without an
  explicit incompatible MPN: title-MPN (U1), SKU-only (U2), partial boundary
  (U3), no-MPN usable-title (U4), near-miss MPN (U5). Future semantic AI
  entry point; eligibility is NOT authority.
* ``DETERMINISTIC_CONFLICT``   — the frozen 3C assessment REJECTED with an
  explicit MPN_MISMATCH that is outside the bounded near-miss shapes
  (C1). Hard conflict; AI not eligible; human cannot confirm.
* ``DETERMINISTIC_UNEVALUABLE`` — no target MPN (E1) or no candidate
  evidence at all (E2). No AI authority.

Product-lead amendments frozen here
-----------------------------------

1. **NM-2 auto-authority ceiling.** A same-length one-character substitution
   (NM-2) MAY classify as ``U5_NEAR_MISS_MPN`` and MAY be evaluated by future
   semantic AI, but WITHOUT reviewed authoritative relationship context
   (``MANUFACTURER_RELATION_AUTHORITY`` or another future reviewed
   relationship-authority provenance) its maximum automatic workflow tier is
   ``NEEDS_REVIEW``. The ceiling is data in the authority matrix, not a
   prompt convention.
2. **Distinct context provenance classes.** ``MANUFACTURER_PRODUCT_CONTEXT``
   (reviewed manufacturer product facts — base MPN/category/family; does NOT
   establish the identifier relationship), ``MANUFACTURER_RELATION_AUTHORITY``
   (reviewed manufacturer / approved authoritative source explicitly
   establishing the relevant identifier relationship), and
   ``CUSTOMER_RETRIEVAL_RELATION`` (project-defined retrieval recall aid;
   NEVER identity authority, NEVER an alias/equivalence proof, never raises
   context to authoritative STRONG, never enters 4A) are distinct bounded
   classes with disjoint capability sets.
3. **Summary wording.** The future display summary is
   ``"Market evidence found: N listings"`` (NEEDS_REVIEW counts under market
   evidence), with a separate
   ``"Pricing-eligible comparable listings: N"`` line (NEEDS_REVIEW never
   counts as pricing-eligible; no price statistic may include Needs Review
   before confirmation). The legacy machine line
   ``"N comparable NEW listings (machine-verified)"`` may remain. The
   misleading "Comparable evidence: N listings" headline is forbidden when
   the count contains NEEDS_REVIEW items.

Deliberately NOT implemented (out of contract):

* Levenshtein or any other edit-distance fuzzy matching;
* arbitrary substring matching (NM-1 is a strict PREFIX relationship only);
* generic containment authority;
* suffix stripping;
* manufacturer-specific acceptance rules (the NM-2 ceiling is generic);
* any change to the frozen 2A normalization profile.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from enum import Enum
from typing import Final

from product_intelligence.domain.enums import (
    EvidenceDecision,
    IdentityMatchType,
)
from product_intelligence.research.identity import (
    compare_part_numbers,
)
from product_intelligence.research.matching import (
    EvidenceSource,
    IdentityRejectionReason,
    ListingIdentityAssessment,
)

__all__ = [
    "ALWAYS_HARD_CONFLICT_CLASSES",
    "AUTHORITY_TIER_BADGES",
    "AuthorityDecisionV2",
    "AuthorityRuleV2",
    "AuthorityTier",
    "ConflictClass",
    "ConflictSeverity",
    "ConflictSubstateV2",
    "ContextCapability",
    "ContextProvenance",
    "ContextQuality",
    "DETERMINISTIC_STATE_POLICIES",
    "DeterministicStatePolicy",
    "FORBIDDEN_MARKET_EVIDENCE_HEADLINE",
    "HARD_CONFLICT_SUPERSEDES_HUMAN",
    "HumanReviewStateV2",
    "IdentityRelationshipSignal",
    "IdentityStateAssessmentV2",
    "IdentityStateV2",
    "LEAD_MARKET_EVIDENCE_SUMMARY_TEMPLATE",
    "LEGACY_MACHINE_VERIFIED_LINE_TEMPLATE",
    "MARKET_EVIDENCE_TIERS",
    "NEAR_MISS_SUBSTITUTION_WITHOUT_RELATION_AUTHORITY",
    "NearMissShape",
    "PRICING_ELIGIBLE_SUMMARY_TEMPLATE",
    "PRICING_ELIGIBLE_TIERS",
    "PRICE_DIMENSION_ONLY_CONFLICT_CLASSES",
    "REVIEWABLE_CONFLICT_CLASSES",
    "SEMANTIC_OUTCOME_TIER_MATRIX",
    "SemanticEvaluationStateV2",
    "SemanticEvaluationV2",
    "TierSummaryV2",
    "UNAVAILABLE_IS_NEVER_NO_MATCH",
    "UncertainSubstateV2",
    "UnevaluableSubstateV2",
    "UI_ATTENTION_ORDER",
    "V2Confidence",
    "V2SemanticDecision",
    "VerifiedSubstateV2",
    "conflict_class_severity",
    "derive_authority_tier",
    "derive_context_quality",
    "derive_identity_state_v2",
    "derive_tier_summary",
    "has_relationship_authority",
    "is_hard_conflict_class",
    "is_near_miss_substitution",
    "is_near_miss_truncation",
    "is_price_dimension_only_class",
    "is_reviewable_conflict_class",
    "is_v2_semantic_entry_point",
    "near_miss_shape",
    "CONTEXT_PROVENANCE_CAPABILITIES",
    "COMPATIBILITY_WORDING_VOCABULARY",
]


# ---------------------------------------------------------------------------
# V2 top-level states and sub-states
# ---------------------------------------------------------------------------


class IdentityStateV2(str, Enum):
    """Top-level deterministic states of the V2 identity overlay.

    These are derived states over the frozen 3C assessment; they carry no
    pricing authority of their own and change no production behavior.
    """

    DETERMINISTIC_VERIFIED = "DETERMINISTIC_VERIFIED"
    """Frozen 3C accepted the listing identity (exact or normalized exact)."""

    DETERMINISTIC_UNCERTAIN = "DETERMINISTIC_UNCERTAIN"
    """Frozen 3C rejected without an explicit incompatible MPN. Future
    semantic AI entry point; eligibility is not authority."""

    DETERMINISTIC_CONFLICT = "DETERMINISTIC_CONFLICT"
    """Frozen 3C rejected on an explicit MPN mismatch outside the bounded
    near-miss shapes. Hard conflict."""

    DETERMINISTIC_UNEVALUABLE = "DETERMINISTIC_UNEVALUABLE"
    """Nothing can be evaluated: no target MPN or no candidate evidence."""


class VerifiedSubstateV2(str, Enum):
    """Bounded sub-states of ``DETERMINISTIC_VERIFIED``."""

    V_EXACT = "V_EXACT"
    """Frozen 2A reported EXACT."""

    V_NORMALIZED_EXACT = "V_NORMALIZED_EXACT"
    """Frozen 2A reported NORMALIZED_EXACT."""


class UncertainSubstateV2(str, Enum):
    """Bounded sub-states of ``DETERMINISTIC_UNCERTAIN``."""

    U1_TITLE_MPN = "U1_TITLE_MPN"
    """The requested MPN appears in the listing title text (recorded only;
    never automatic identity)."""

    U2_SKU_ONLY = "U2_SKU_ONLY"
    """The listing published a SKU field and no explicit MPN field."""

    U3_PARTIAL_BOUNDARY = "U3_PARTIAL_BOUNDARY"
    """Frozen 3C classified a PARTIAL boundary overlap (3C PARTIAL_MPN_ONLY)."""

    U4_NO_MPN = "U4_NO_MPN"
    """No usable manufacturer MPN evidence, but usable product title
    evidence. Intentional recall feature for future semantic evaluation;
    eligibility does not mean authority."""

    U5_NEAR_MISS_MPN = "U5_NEAR_MISS_MPN"
    """Explicit MPN mismatch in a bounded near-miss shape (NM-1 or NM-2).
    Near-miss membership is NEVER identity authority."""


class ConflictSubstateV2(str, Enum):
    """Bounded sub-states of ``DETERMINISTIC_CONFLICT``."""

    C1_INCOMPATIBLE_EXPLICIT_MPN = "C1_INCOMPATIBLE_EXPLICIT_MPN"
    """Explicit MPN mismatch outside the bounded NM-1/NM-2 shapes."""


class UnevaluableSubstateV2(str, Enum):
    """Bounded sub-states of ``DETERMINISTIC_UNEVALUABLE``."""

    E1_NO_TARGET_MPN = "E1_NO_TARGET_MPN"
    """The request carries no target MPN to compare against."""

    E2_NO_CANDIDATE_EVIDENCE = "E2_NO_CANDIDATE_EVIDENCE"
    """The listing publishes no candidate identifier and no usable product
    title text."""


# ---------------------------------------------------------------------------
# Bounded near-miss relationship signals
# ---------------------------------------------------------------------------


class IdentityRelationshipSignal(str, Enum):
    """Bounded relationship signals between requested and candidate
    identifiers (and one text-positioning overlay).

    Near-miss membership (NEAR_MISS_TRUNCATION / NEAR_MISS_SUBSTITUTION) is
    NEVER identity authority: it classifies an assessment as uncertain for
    future semantic/human inspection, and nothing more.
    """

    EXACT = "EXACT"
    """Frozen 2A character-for-character equality."""

    NORMALIZED_EXACT = "NORMALIZED_EXACT"
    """Frozen 2A equality under the frozen normalization profile only."""

    TITLE_MPN_TOKEN = "TITLE_MPN_TOKEN"
    """The requested MPN appears as a token in the listing title."""

    SKU_EQUALS_TARGET = "SKU_EQUALS_TARGET"
    """The published SKU establishes frozen-2A identity with the target."""

    SKU_NOT_TARGET = "SKU_NOT_TARGET"
    """The published SKU does not establish frozen-2A identity with the
    target."""

    PARTIAL_BOUNDARY = "PARTIAL_BOUNDARY"
    """Frozen 3C PARTIAL boundary overlap."""

    NEAR_MISS_TRUNCATION = "NEAR_MISS_TRUNCATION"
    """NM-1: strict prefix/truncation relationship on the frozen normalized
    MPN keys (either direction). Not identity authority."""

    NEAR_MISS_SUBSTITUTION = "NEAR_MISS_SUBSTITUTION"
    """NM-2: same-length, exactly one-character substitution on the frozen
    normalized MPN keys. Not identity authority; subject to the NM-2
    auto-authority ceiling."""

    COMPATIBILITY_WORDING = "COMPATIBILITY_WORDING"
    """Overlay signal: the listing title uses bounded compatibility/
    replacement wording. A positioning fact, never identity authority."""

    EMPTY_MPN_FIELD = "EMPTY_MPN_FIELD"
    """An explicit MPN field was published but carries no part-number
    content after the frozen wrapper cleanup."""

    NO_RELATION = "NO_RELATION"
    """No bounded identifier relationship is established."""


class NearMissShape(str, Enum):
    """The two and only two bounded near-miss shapes (S2-A contract)."""

    NM1_TRUNCATION = "NM1_TRUNCATION"
    """Strict prefix/truncation on the frozen normalized MPN keys."""

    NM2_SUBSTITUTION = "NM2_SUBSTITUTION"
    """Same length, exactly one substituted character."""


def is_near_miss_truncation(
    requested_key: str, candidate_key: str
) -> bool:
    """NM-1 predicate over FROZEN normalized MPN keys.

    True when one key is a strict prefix of the other (either direction).
    Equal keys are not near-misses (they are identity); empty keys are not
    near-misses (there is no identifier). No substring matching: the shared
    text must begin at position zero.
    """
    if not requested_key or not candidate_key:
        return False
    if requested_key == candidate_key:
        return False
    return candidate_key.startswith(requested_key) or requested_key.startswith(
        candidate_key
    )


def is_near_miss_substitution(
    requested_key: str, candidate_key: str
) -> bool:
    """NM-2 predicate over FROZEN normalized MPN keys.

    True when the keys have the same length and differ in exactly one
    character position. Unequal lengths are not NM-2 (an insertion or
    deletion is truncation-shaped at best). No Levenshtein: two differences,
    or any other edit shape, is outside the contract.
    """
    if not requested_key or not candidate_key:
        return False
    if len(requested_key) != len(candidate_key):
        return False
    if requested_key == candidate_key:
        return False
    differences = sum(
        1
        for requested_char, candidate_char in zip(requested_key, candidate_key)
        if requested_char != candidate_char
    )
    return differences == 1


def near_miss_shape(
    requested_key: str, candidate_key: str
) -> NearMissShape | None:
    """Classify the pair into a bounded near-miss shape, or ``None``.

    NM-1 is checked first: a pair that is both a strict prefix relation and
    (impossibly, since the lengths would differ) a same-length substitution
    can only be NM-1. Unequal-length pairs are never NM-2.
    """
    if is_near_miss_truncation(requested_key, candidate_key):
        return NearMissShape.NM1_TRUNCATION
    if is_near_miss_substitution(requested_key, candidate_key):
        return NearMissShape.NM2_SUBSTITUTION
    return None


# Bounded compatibility-wording vocabulary (deterministic, frozen in S2-A).
# Word-boundary matched, case-insensitively, against the listing title text
# only. This is a positioning signal for future semantic/human inspection;
# it never establishes or refutes identity by itself.
COMPATIBILITY_WORDING_VOCABULARY: Final[frozenset[str]] = frozenset(
    {"compatible", "replacement", "interchangeable", "drop-in"}
)

_COMPATIBILITY_WORDING_PATTERN = re.compile(
    r"(?<![A-Za-z0-9])(?:"
    + "|".join(re.escape(token) for token in sorted(COMPATIBILITY_WORDING_VOCABULARY))
    + r")(?![A-Za-z0-9])",
    re.IGNORECASE,
)


def _has_compatibility_wording(title: str | None) -> bool:
    """Bounded compatibility-wording detection over the frozen title text."""
    if not title:
        return False
    return _COMPATIBILITY_WORDING_PATTERN.search(title) is not None


# ---------------------------------------------------------------------------
# The frozen V2 state derivation
# ---------------------------------------------------------------------------

# The per-substate sets of permitted primary relationship signals. A direct
# construction that mixes a sub-state with a foreign signal is rejected at
# construction time (fail closed).
_PRIMARY_SIGNALS_BY_SUBSTATE: Final[dict[str, frozenset[IdentityRelationshipSignal]]] = (
    {
        "V_EXACT": frozenset({IdentityRelationshipSignal.EXACT}),
        "V_NORMALIZED_EXACT": frozenset({IdentityRelationshipSignal.NORMALIZED_EXACT}),
        "U1_TITLE_MPN": frozenset({IdentityRelationshipSignal.TITLE_MPN_TOKEN}),
        "U2_SKU_ONLY": frozenset(
            {
                IdentityRelationshipSignal.SKU_EQUALS_TARGET,
                IdentityRelationshipSignal.SKU_NOT_TARGET,
            }
        ),
        "U3_PARTIAL_BOUNDARY": frozenset(
            {IdentityRelationshipSignal.PARTIAL_BOUNDARY}
        ),
        "U4_NO_MPN": frozenset(
            {
                IdentityRelationshipSignal.NO_RELATION,
                IdentityRelationshipSignal.EMPTY_MPN_FIELD,
            }
        ),
        "U5_NEAR_MISS_MPN": frozenset(
            {
                IdentityRelationshipSignal.NEAR_MISS_TRUNCATION,
                IdentityRelationshipSignal.NEAR_MISS_SUBSTITUTION,
            }
        ),
        "C1_INCOMPATIBLE_EXPLICIT_MPN": frozenset(
            {IdentityRelationshipSignal.NO_RELATION}
        ),
        "E1_NO_TARGET_MPN": frozenset({IdentityRelationshipSignal.NO_RELATION}),
        "E2_NO_CANDIDATE_EVIDENCE": frozenset(
            {
                IdentityRelationshipSignal.NO_RELATION,
                IdentityRelationshipSignal.EMPTY_MPN_FIELD,
            }
        ),
    }
)

_STATE_OF_SUBSTATE: Final[dict[str, IdentityStateV2]] = {
    "V_EXACT": IdentityStateV2.DETERMINISTIC_VERIFIED,
    "V_NORMALIZED_EXACT": IdentityStateV2.DETERMINISTIC_VERIFIED,
    "U1_TITLE_MPN": IdentityStateV2.DETERMINISTIC_UNCERTAIN,
    "U2_SKU_ONLY": IdentityStateV2.DETERMINISTIC_UNCERTAIN,
    "U3_PARTIAL_BOUNDARY": IdentityStateV2.DETERMINISTIC_UNCERTAIN,
    "U4_NO_MPN": IdentityStateV2.DETERMINISTIC_UNCERTAIN,
    "U5_NEAR_MISS_MPN": IdentityStateV2.DETERMINISTIC_UNCERTAIN,
    "C1_INCOMPATIBLE_EXPLICIT_MPN": IdentityStateV2.DETERMINISTIC_CONFLICT,
    "E1_NO_TARGET_MPN": IdentityStateV2.DETERMINISTIC_UNEVALUABLE,
    "E2_NO_CANDIDATE_EVIDENCE": IdentityStateV2.DETERMINISTIC_UNEVALUABLE,
}


@dataclass(frozen=True)
class IdentityStateAssessmentV2:
    """The pure V2 deterministic state overlay for one frozen 3C assessment.

    Derived, never stored by production (S2-A wires nothing). Immutable and
    auditable: the frozen normalized keys are carried so a reviewer can
    re-derive every signal without the module source.
    """

    state: IdentityStateV2
    substate: (
        VerifiedSubstateV2
        | UncertainSubstateV2
        | ConflictSubstateV2
        | UnevaluableSubstateV2
    )
    relationship_signals: frozenset[IdentityRelationshipSignal]
    normalized_requested_part_number: str
    normalized_candidate_part_number: str

    def __post_init__(self) -> None:
        if not isinstance(self.state, IdentityStateV2):
            raise TypeError(
                "state must be IdentityStateV2, "
                f"got {type(self.state).__name__}"
            )
        substate_type = type(self.substate)
        if substate_type not in (
            VerifiedSubstateV2,
            UncertainSubstateV2,
            ConflictSubstateV2,
            UnevaluableSubstateV2,
        ):
            raise TypeError(
                "substate must be a V2 sub-state enum member, "
                f"got {substate_type.__name__}"
            )
        if not isinstance(self.relationship_signals, frozenset):
            raise TypeError(
                "relationship_signals must be a frozenset, "
                f"got {type(self.relationship_signals).__name__}"
            )
        for signal in self.relationship_signals:
            if not isinstance(signal, IdentityRelationshipSignal):
                raise TypeError(
                    "relationship_signals must contain only "
                    f"IdentityRelationshipSignal members, got {signal!r}"
                )
        if not isinstance(self.normalized_requested_part_number, str):
            raise TypeError("normalized_requested_part_number must be str")
        if not isinstance(self.normalized_candidate_part_number, str):
            raise TypeError("normalized_candidate_part_number must be str")

        # State/sub-state consistency: the sub-state enum family must match
        # the top-level state (U3 in a CONFLICT overlay is impossible).
        expected_state = _STATE_OF_SUBSTATE.get(self.substate.value)
        if expected_state is not self.state:
            raise ValueError(
                f"sub-state {self.substate.value} belongs to "
                f"{expected_state.value if expected_state else '<no state>'}, "
                f"not {self.state.value}"
            )

        # Exactly one primary identifier-relationship signal is required;
        # COMPATIBILITY_WORDING is the only permitted overlay signal.
        primary = self.relationship_signals - frozenset(
            {IdentityRelationshipSignal.COMPATIBILITY_WORDING}
        )
        if len(primary) != 1:
            raise ValueError(
                "relationship_signals must contain exactly one primary "
                f"identifier-relationship signal, got {sorted(s.value for s in primary)}"
            )
        permitted = _PRIMARY_SIGNALS_BY_SUBSTATE[self.substate.value]
        if not primary <= permitted:
            raise ValueError(
                f"sub-state {self.substate.value} does not permit primary "
                f"signal {next(iter(primary)).value}; "
                f"permitted: {sorted(s.value for s in permitted)}"
            )

    @property
    def primary_relationship_signal(self) -> IdentityRelationshipSignal:
        """The single primary identifier-relationship signal."""
        primary = self.relationship_signals - frozenset(
            {IdentityRelationshipSignal.COMPATIBILITY_WORDING}
        )
        return next(iter(primary))

    def has_signal(self, signal: IdentityRelationshipSignal) -> bool:
        return signal in self.relationship_signals

    @property
    def near_miss_substitution_active(self) -> bool:
        """True for U5 in the bounded NM-2 shape (the ceiling's trigger)."""
        return (
            self.substate is UncertainSubstateV2.U5_NEAR_MISS_MPN
            and self.has_signal(IdentityRelationshipSignal.NEAR_MISS_SUBSTITUTION)
        )

    @property
    def is_semantic_entry_point(self) -> bool:
        """Future semantic AI entry point: uncertain states only."""
        return self.state is IdentityStateV2.DETERMINISTIC_UNCERTAIN


def _has_usable_product_text(observation) -> bool:
    """Usable product text for U4: the frozen V1 usability gate.

    Mirrors the frozen FU3B ``_has_usable_evidence`` contract exactly: a
    non-empty product title. This is a recall gate (is there anything to
    evaluate), not an authority grant.
    """
    return bool(observation.product_title)


def derive_identity_state_v2(
    assessment: ListingIdentityAssessment,
) -> IdentityStateAssessmentV2:
    """Derive the pure V2 deterministic state overlay for one frozen 3C
    assessment.

    Consumes ONLY frozen deterministic facts: the assessment's recorded
    decision / rejection reason / evidence source / match type and its
    carried identifier strings. The frozen 2A comparator is re-run on the
    same two strings 3C compared (``requested_part_number`` and
    ``candidate_part_number_compared``) to recover the frozen normalized
    keys — this is the same call the assessment's own constructor invariants
    make, so no new normalization exists.

    No database, no Django, no network, no LLM, no mutable global state.

    Mapping (frozen 3C state -> V2 state/sub-state/primary signal):

    * UNDECIDED + NO_REQUESTED_MPN                     -> E1_NO_TARGET_MPN
    * ACCEPTED + EXACT                                 -> V_EXACT
    * ACCEPTED + NORMALIZED_EXACT                      -> V_NORMALIZED_EXACT
    * REJECTED + NO_EXPLICIT_MPN_EVIDENCE + TITLE_TEXT -> U1_TITLE_MPN
    * REJECTED + NO_EXPLICIT_MPN_EVIDENCE + SKU_FIELD  -> U2_SKU_ONLY
      (SKU_EQUALS_TARGET when the frozen 2A comparator establishes identity
      with the SKU, otherwise SKU_NOT_TARGET)
    * REJECTED + PARTIAL_MPN_ONLY                      -> U3_PARTIAL_BOUNDARY
    * REJECTED + NO_EXPLICIT_MPN_EVIDENCE + NONE       -> U4_NO_MPN when the
      listing carries a usable product title, else E2_NO_CANDIDATE_EVIDENCE
    * REJECTED + NO_EXPLICIT_MPN_EVIDENCE + explicit
      MPN source (empty field)                         -> U4_NO_MPN when the
      listing carries a usable product title, else E2_NO_CANDIDATE_EVIDENCE
      (primary signal EMPTY_MPN_FIELD)
    * REJECTED + MPN_MISMATCH + explicit MPN source    -> U5_NEAR_MISS_MPN
      (NEAR_MISS_TRUNCATION for NM-1 / NEAR_MISS_SUBSTITUTION for NM-2) or
      C1_INCOMPATIBLE_EXPLICIT_MPN (NO_RELATION) when outside the bounded
      near-miss shapes

    The COMPATIBILITY_WORDING overlay signal is added whenever the bounded
    vocabulary matches the frozen listing title, in any state.

    Raises ``ValueError`` for any assessment combination the frozen 3C
    contract does not define (fail closed).
    """
    if not isinstance(assessment, ListingIdentityAssessment):
        raise TypeError(
            "assessment must be ListingIdentityAssessment, "
            f"got {type(assessment).__name__}"
        )

    observation = assessment.normalized_listing.observation
    decision = assessment.decision
    rejection = assessment.rejection_reason
    source = assessment.candidate_evidence_source
    match_type = assessment.match_type

    frozen_comparison = compare_part_numbers(
        assessment.requested_part_number,
        assessment.candidate_part_number_compared,
    )
    requested_key = frozen_comparison.normalized_requested_part_number
    candidate_key = frozen_comparison.normalized_candidate_part_number
    signals: set[IdentityRelationshipSignal] = set()
    if _has_compatibility_wording(observation.product_title):
        signals.add(IdentityRelationshipSignal.COMPATIBILITY_WORDING)

    explicit_mpn_sources = (
        EvidenceSource.EXPLICIT_MPN_FIELD,
        EvidenceSource.VISIBLE_LABELED_MPN_FIELD,
    )

    if decision is EvidenceDecision.UNDECIDED:
        if rejection is not IdentityRejectionReason.NO_REQUESTED_MPN:
            raise ValueError(
                "UNDECIDED assessment without NO_REQUESTED_MPN is outside "
                "the frozen 3C contract; V2 derivation fails closed"
            )
        state = IdentityStateV2.DETERMINISTIC_UNEVALUABLE
        substate = UnevaluableSubstateV2.E1_NO_TARGET_MPN
        signals.add(IdentityRelationshipSignal.NO_RELATION)

    elif decision is EvidenceDecision.ACCEPTED:
        if source not in explicit_mpn_sources:
            raise ValueError(
                "ACCEPTED assessment without an explicit MPN evidence "
                "source is outside the frozen 3C contract; V2 derivation "
                "fails closed"
            )
        if match_type is IdentityMatchType.EXACT:
            state = IdentityStateV2.DETERMINISTIC_VERIFIED
            substate = VerifiedSubstateV2.V_EXACT
            signals.add(IdentityRelationshipSignal.EXACT)
        elif match_type is IdentityMatchType.NORMALIZED_EXACT:
            state = IdentityStateV2.DETERMINISTIC_VERIFIED
            substate = VerifiedSubstateV2.V_NORMALIZED_EXACT
            signals.add(IdentityRelationshipSignal.NORMALIZED_EXACT)
        else:
            raise ValueError(
                f"ACCEPTED assessment with match type {match_type.value} is "
                "outside the frozen 3C contract; V2 derivation fails closed"
            )

    elif decision is EvidenceDecision.REJECTED:
        if rejection is IdentityRejectionReason.NO_EXPLICIT_MPN_EVIDENCE:
            if source is EvidenceSource.TITLE_TEXT:
                state = IdentityStateV2.DETERMINISTIC_UNCERTAIN
                substate = UncertainSubstateV2.U1_TITLE_MPN
                signals.add(IdentityRelationshipSignal.TITLE_MPN_TOKEN)
            elif source is EvidenceSource.SKU_FIELD:
                state = IdentityStateV2.DETERMINISTIC_UNCERTAIN
                substate = UncertainSubstateV2.U2_SKU_ONLY
                if (
                    requested_key
                    and candidate_key
                    and frozen_comparison.is_established
                ):
                    signals.add(IdentityRelationshipSignal.SKU_EQUALS_TARGET)
                else:
                    signals.add(IdentityRelationshipSignal.SKU_NOT_TARGET)
            elif source in explicit_mpn_sources:
                # Explicit MPN field carried no part-number content after
                # the frozen wrapper cleanup.
                if _has_usable_product_text(observation):
                    state = IdentityStateV2.DETERMINISTIC_UNCERTAIN
                    substate = UncertainSubstateV2.U4_NO_MPN
                else:
                    state = IdentityStateV2.DETERMINISTIC_UNEVALUABLE
                    substate = UnevaluableSubstateV2.E2_NO_CANDIDATE_EVIDENCE
                signals.add(IdentityRelationshipSignal.EMPTY_MPN_FIELD)
            elif source is EvidenceSource.NONE:
                if _has_usable_product_text(observation):
                    state = IdentityStateV2.DETERMINISTIC_UNCERTAIN
                    substate = UncertainSubstateV2.U4_NO_MPN
                    signals.add(IdentityRelationshipSignal.NO_RELATION)
                else:
                    state = IdentityStateV2.DETERMINISTIC_UNEVALUABLE
                    substate = UnevaluableSubstateV2.E2_NO_CANDIDATE_EVIDENCE
                    signals.add(IdentityRelationshipSignal.NO_RELATION)
            else:  # pragma: no cover - the enum is closed
                raise ValueError(
                    f"NO_EXPLICIT_MPN_EVIDENCE with evidence source "
                    f"{source.value} is outside the frozen 3C contract; V2 "
                    "derivation fails closed"
                )

        elif rejection is IdentityRejectionReason.PARTIAL_MPN_ONLY:
            if source not in explicit_mpn_sources:
                raise ValueError(
                    "PARTIAL_MPN_ONLY without an explicit MPN evidence "
                    "source is outside the frozen 3C contract; V2 "
                    "derivation fails closed"
                )
            state = IdentityStateV2.DETERMINISTIC_UNCERTAIN
            substate = UncertainSubstateV2.U3_PARTIAL_BOUNDARY
            signals.add(IdentityRelationshipSignal.PARTIAL_BOUNDARY)

        elif rejection is IdentityRejectionReason.MPN_MISMATCH:
            if source not in explicit_mpn_sources:
                raise ValueError(
                    "MPN_MISMATCH without an explicit MPN evidence source "
                    "is outside the frozen 3C contract; V2 derivation "
                    "fails closed"
                )
            shape = near_miss_shape(requested_key, candidate_key)
            if shape is NearMissShape.NM1_TRUNCATION:
                state = IdentityStateV2.DETERMINISTIC_UNCERTAIN
                substate = UncertainSubstateV2.U5_NEAR_MISS_MPN
                signals.add(IdentityRelationshipSignal.NEAR_MISS_TRUNCATION)
            elif shape is NearMissShape.NM2_SUBSTITUTION:
                state = IdentityStateV2.DETERMINISTIC_UNCERTAIN
                substate = UncertainSubstateV2.U5_NEAR_MISS_MPN
                signals.add(IdentityRelationshipSignal.NEAR_MISS_SUBSTITUTION)
            else:
                # Anything outside the bounded NM-1/NM-2 shapes remains a
                # deterministic conflict where the frozen assessment is an
                # explicit MPN_MISMATCH.
                state = IdentityStateV2.DETERMINISTIC_CONFLICT
                substate = ConflictSubstateV2.C1_INCOMPATIBLE_EXPLICIT_MPN
                signals.add(IdentityRelationshipSignal.NO_RELATION)

        elif rejection is IdentityRejectionReason.NO_REQUESTED_MPN:
            raise ValueError(
                "NO_REQUESTED_MPN requires the UNDECIDED decision in the "
                "frozen 3C contract; V2 derivation fails closed"
            )
        else:  # pragma: no cover - the enum is closed
            raise ValueError(
                f"REJECTED assessment with reason {rejection!r} is outside "
                "the frozen 3C contract; V2 derivation fails closed"
            )

    else:  # pragma: no cover - the enum is closed
        raise ValueError(
            f"Decision {decision!r} is outside the frozen 3C contract; "
            "V2 derivation fails closed"
        )

    return IdentityStateAssessmentV2(
        state=state,
        substate=substate,
        relationship_signals=frozenset(signals),
        normalized_requested_part_number=requested_key,
        normalized_candidate_part_number=candidate_key,
    )


def is_v2_semantic_entry_point(
    assessment_v2: IdentityStateAssessmentV2,
) -> bool:
    """Future semantic AI entry point: the uncertain states only.

    Contract-only in S2-A: this predicate is NOT the production eligibility
    gate (the frozen FU3B predicate in execution remains the only one that
    gates live calls). U4 is deliberately an entry point — the no-MPN
    usable-title recall feature — while eligibility never means authority.
    """
    if not isinstance(assessment_v2, IdentityStateAssessmentV2):
        raise TypeError(
            "assessment_v2 must be IdentityStateAssessmentV2, "
            f"got {type(assessment_v2).__name__}"
        )
    return assessment_v2.state is IdentityStateV2.DETERMINISTIC_UNCERTAIN


# ---------------------------------------------------------------------------
# Structured conflict taxonomy
# ---------------------------------------------------------------------------


class ConflictClass(str, Enum):
    """Bounded classes of material conflicts between target and candidate.

    A conflict class names WHAT differs; the severity sets below name what
    that difference MAY do to workflow authority. CONDITION is not an
    identity conflict at all — it is a price/condition dimension.
    """

    MPN_IDENTITY = "MPN_IDENTITY"
    """The identifiers assert different products outright."""

    REVISION_OR_SUFFIX = "REVISION_OR_SUFFIX"
    """A revision/suffix difference (possibly packaging, possibly product)."""

    BRAND = "BRAND"
    """Brand disagreement. Reviewable: a private-label repack of the same
    manufacturer product is real market evidence."""

    PRODUCT_FAMILY = "PRODUCT_FAMILY"
    GENERATION = "GENERATION"
    CAPACITY = "CAPACITY"
    INTERFACE = "INTERFACE"
    FORM_FACTOR = "FORM_FACTOR"
    PRODUCT_ROLE = "PRODUCT_ROLE"
    ACCESSORY_RELATION = "ACCESSORY_RELATION"
    """A drive-tray / caddy / enclosure vs the drive itself."""

    PACKAGING_QUANTITY = "PACKAGING_QUANTITY"
    """Single vs multipack. Tray-vs-retail wording alone is NOT this class
    and is not hard by itself."""

    BUNDLE = "BUNDLE"
    CONDITION = "CONDITION"
    """New/refurbished/used condition. A price dimension, never identity."""

    OTHER_MATERIAL_CONFLICT = "OTHER_MATERIAL_CONFLICT"


class ConflictSeverity(str, Enum):
    """The three and only three bounded conflict severities."""

    ALWAYS_HARD = "ALWAYS_HARD"
    """Deterministic identity conflict: AI not eligible, human cannot
    confirm, hard-conflict precedence."""

    REVIEWABLE = "REVIEWABLE"
    """Material but resolvable by inspection: caps automatic authority at
    NEEDS_REVIEW."""

    PRICE_DIMENSION_ONLY = "PRICE_DIMENSION_ONLY"
    """Not an identity conflict: it stays in the price/condition bucket and
    never caps identity authority."""


#: Frozen default severity sets (S2-A contract).
ALWAYS_HARD_CONFLICT_CLASSES: Final[frozenset[ConflictClass]] = frozenset(
    {
        ConflictClass.MPN_IDENTITY,
        ConflictClass.PRODUCT_FAMILY,
        ConflictClass.GENERATION,
        ConflictClass.CAPACITY,
        ConflictClass.INTERFACE,
        ConflictClass.FORM_FACTOR,
        ConflictClass.PRODUCT_ROLE,
        ConflictClass.ACCESSORY_RELATION,
        ConflictClass.PACKAGING_QUANTITY,
        ConflictClass.BUNDLE,
    }
)

REVIEWABLE_CONFLICT_CLASSES: Final[frozenset[ConflictClass]] = frozenset(
    {
        ConflictClass.REVISION_OR_SUFFIX,
        ConflictClass.BRAND,
        ConflictClass.OTHER_MATERIAL_CONFLICT,
    }
)

PRICE_DIMENSION_ONLY_CONFLICT_CLASSES: Final[frozenset[ConflictClass]] = (
    frozenset({ConflictClass.CONDITION})
)


def conflict_class_severity(conflict_class: ConflictClass) -> ConflictSeverity:
    """The bounded severity of one conflict class.

    Fails closed on anything that is not a ``ConflictClass`` member.
    """
    if not isinstance(conflict_class, ConflictClass):
        raise TypeError(
            "conflict_class must be ConflictClass, "
            f"got {type(conflict_class).__name__}"
        )
    if conflict_class in ALWAYS_HARD_CONFLICT_CLASSES:
        return ConflictSeverity.ALWAYS_HARD
    if conflict_class in REVIEWABLE_CONFLICT_CLASSES:
        return ConflictSeverity.REVIEWABLE
    if conflict_class in PRICE_DIMENSION_ONLY_CONFLICT_CLASSES:
        return ConflictSeverity.PRICE_DIMENSION_ONLY
    raise ValueError(
        f"conflict class {conflict_class.value} has no bounded severity; "
        "the taxonomy sets must cover the whole vocabulary"
    )


def is_hard_conflict_class(conflict_class: ConflictClass) -> bool:
    return conflict_class in ALWAYS_HARD_CONFLICT_CLASSES


def is_reviewable_conflict_class(conflict_class: ConflictClass) -> bool:
    return conflict_class in REVIEWABLE_CONFLICT_CLASSES


def is_price_dimension_only_class(conflict_class: ConflictClass) -> bool:
    return conflict_class in PRICE_DIMENSION_ONLY_CONFLICT_CLASSES


# ---------------------------------------------------------------------------
# Context provenance classes (Product-lead amendment 2)
# ---------------------------------------------------------------------------


class ContextProvenance(str, Enum):
    """Distinct bounded context provenance classes.

    These are deliberately separate classes, not one ambiguous boolean:

    * ``MANUFACTURER_PRODUCT_CONTEXT`` — a reviewed manufacturer source
      establishes facts about the base product (base MPN / category /
      family). It does NOT establish the relationship between the requested
      and the candidate MPN.
    * ``MANUFACTURER_RELATION_AUTHORITY`` — a reviewed manufacturer or
      equivalent approved authoritative source explicitly establishes the
      relevant relationship/equivalence between identifiers. This is the
      class that MAY raise relationship authority / context quality.
    * ``CUSTOMER_RETRIEVAL_RELATION`` — a customer/project-defined
      relationship existing solely to improve retrieval recall. It is NOT
      manufacturer-published identity/equivalence authority and MUST NEVER,
      by itself: establish identity, produce machine-verified authority,
      raise NM-2 to automatic comparable, raise context quality to
      authoritative STRONG, override conflict, enter 4A, or be described to
      the model as manufacturer-established equivalence.
    """

    MANUFACTURER_PRODUCT_CONTEXT = "MANUFACTURER_PRODUCT_CONTEXT"
    MANUFACTURER_RELATION_AUTHORITY = "MANUFACTURER_RELATION_AUTHORITY"
    CUSTOMER_RETRIEVAL_RELATION = "CUSTOMER_RETRIEVAL_RELATION"


class ContextCapability(str, Enum):
    """What a context provenance class is permitted to do."""

    GROUND_PRODUCT_FACTS = "GROUND_PRODUCT_FACTS"
    """Reviewed product facts (base MPN / category / family grounding)."""

    ESTABLISH_IDENTIFIER_RELATIONSHIP = "ESTABLISH_IDENTIFIER_RELATIONSHIP"
    """A reviewed authoritative identifier relationship/equivalence. The
    only capability that can satisfy the matrix's relationship-context gate
    and raise context quality to authoritative STRONG."""

    RETRIEVAL_RECALL_ONLY = "RETRIEVAL_RECALL_ONLY"
    """Recall aid. No identity, no equivalence, no authority of any kind."""


CONTEXT_PROVENANCE_CAPABILITIES: Final[dict[ContextProvenance, frozenset[ContextCapability]]] = (
    {
        ContextProvenance.MANUFACTURER_PRODUCT_CONTEXT: frozenset(
            {ContextCapability.GROUND_PRODUCT_FACTS}
        ),
        ContextProvenance.MANUFACTURER_RELATION_AUTHORITY: frozenset(
            {
                ContextCapability.GROUND_PRODUCT_FACTS,
                ContextCapability.ESTABLISH_IDENTIFIER_RELATIONSHIP,
            }
        ),
        ContextProvenance.CUSTOMER_RETRIEVAL_RELATION: frozenset(
            {ContextCapability.RETRIEVAL_RECALL_ONLY}
        ),
    }
)


def _union_capabilities(
    provenances: frozenset[ContextProvenance],
) -> frozenset[ContextCapability]:
    capabilities: set[ContextCapability] = set()
    for provenance in provenances:
        if not isinstance(provenance, ContextProvenance):
            raise TypeError(
                "context provenances must be ContextProvenance members, "
                f"got {provenance!r}"
            )
        capabilities |= CONTEXT_PROVENANCE_CAPABILITIES[provenance]
    return frozenset(capabilities)


def has_relationship_authority(
    provenances: frozenset[ContextProvenance],
) -> bool:
    """Reviewed authoritative relationship context present?

    True only when some provenance carries the
    ``ESTABLISH_IDENTIFIER_RELATIONSHIP`` capability (today:
    ``MANUFACTURER_RELATION_AUTHORITY``; a future reviewed authoritative
    relationship source would be a new class holding this capability).
    ``CUSTOMER_RETRIEVAL_RELATION`` can never make this True.
    """
    if not isinstance(provenances, frozenset):
        raise TypeError("provenances must be a frozenset")
    capabilities = _union_capabilities(provenances)
    return ContextCapability.ESTABLISH_IDENTIFIER_RELATIONSHIP in capabilities


class ContextQuality(str, Enum):
    """Bounded context quality vocabulary."""

    STRONG = "STRONG"
    """Authoritative: a reviewed identifier relationship is established."""

    LIMITED = "LIMITED"
    """Reviewed product grounding without an identifier relationship."""

    WEAK = "WEAK"
    """No reviewed product/relationship grounding (or retrieval aid only)."""


def derive_context_quality(
    provenances: frozenset[ContextProvenance],
) -> ContextQuality:
    """Compute context quality from persisted/extracted provenance classes.

    Conservative by contract:

    * quality is computed ONLY from provenance classes — never from model
      confidence and never from AI ``matched_attributes`` (the matrix takes
      no AI-input context quality; an AI outcome cannot raise its own
      authority);
    * ``CUSTOMER_RETRIEVAL_RELATION`` alone cannot raise context to
      authoritative STRONG (it is WEAK);
    * ``MANUFACTURER_PRODUCT_CONTEXT`` may strengthen product grounding
      (LIMITED) but does not prove identifier equivalence;
    * ``MANUFACTURER_RELATION_AUTHORITY`` is the class that establishes a
      reviewed identifier relationship (STRONG), regardless of what else is
      present.
    """
    if not isinstance(provenances, frozenset):
        raise TypeError("provenances must be a frozenset")
    capabilities = _union_capabilities(provenances)
    if ContextCapability.ESTABLISH_IDENTIFIER_RELATIONSHIP in capabilities:
        return ContextQuality.STRONG
    if ContextCapability.GROUND_PRODUCT_FACTS in capabilities:
        return ContextQuality.LIMITED
    return ContextQuality.WEAK


# ---------------------------------------------------------------------------
# Authority tier vocabulary
# ---------------------------------------------------------------------------


class AuthorityTier(str, Enum):
    """Bounded derived workflow authority vocabulary (S2-A contract only).

    NOT wired into any runtime in this phase. The tiers are what a future
    V2 workflow derivation will present; today they exist as frozen
    contract data.
    """

    MACHINE_VERIFIED = "MACHINE_VERIFIED"
    """Frozen deterministic exact identity. Automatic authority."""

    AI_ASSISTED_COMPARABLE = "AI_ASSISTED_COMPARABLE"
    """Future semantic AI matched with HIGH confidence under the full
    contract-approved context/conflict gates. Never machine-verified."""

    NEEDS_REVIEW = "NEEDS_REVIEW"
    """Not verified. Review candidate; never pricing-eligible before
    confirmation."""

    HUMAN_CONFIRMED = "HUMAN_CONFIRMED"
    """A human confirmed the identity after inspection."""

    HUMAN_REJECTED = "HUMAN_REJECTED"
    """A human rejected the candidate."""

    HARD_CONFLICT = "HARD_CONFLICT"
    """Deterministic incompatible identity. Excluded; AI not eligible;
    human cannot confirm."""

    EXCLUDED_LOW_CONFIDENCE = "EXCLUDED_LOW_CONFIDENCE"
    """Weak/insufficient evidence. Excluded from comparable authority."""

    SEMANTIC_UNAVAILABLE = "SEMANTIC_UNAVAILABLE"
    """The semantic evaluation failed at runtime. Never interpreted as
    NO_MATCH and never as exclusion on evidence grounds."""


class V2SemanticDecision(str, Enum):
    """Bounded future semantic AI decision vocabulary for matrix purposes.

    Mirrors (but is independent of) the frozen semantic V1 contract, so the
    matrix is pure data that a future phase can feed from the runtime
    without the runtime importing this module's authority semantics.
    """

    MATCH = "MATCH"
    NO_MATCH = "NO_MATCH"
    UNCERTAIN = "UNCERTAIN"


class V2Confidence(str, Enum):
    """Bounded future semantic AI confidence vocabulary for matrix
    purposes."""

    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"


class SemanticEvaluationStateV2(str, Enum):
    """Whether a (future) semantic evaluation happened, and how it ended."""

    NOT_EVALUATED = "NOT_EVALUATED"
    """No semantic call; the deterministic state governs."""

    EVALUATED = "EVALUATED"
    """A semantic decision with confidence was produced."""

    RUNTIME_FAILURE = "RUNTIME_FAILURE"
    """The semantic call failed at runtime. SEMANTIC_UNAVAILABLE — never
    interpreted as NO_MATCH."""


@dataclass(frozen=True)
class SemanticEvaluationV2:
    """One bounded future semantic evaluation outcome for matrix input.

    Fail-closed construction: NOT_EVALUATED and RUNTIME_FAILURE carry no
    decision/confidence/conflicts; EVALUATED carries all of them. A
    runtime failure may never be shaped like a NO_MATCH.
    """

    evaluation_state: SemanticEvaluationStateV2
    decision: V2SemanticDecision | None = None
    confidence: V2Confidence | None = None
    conflict_classes: frozenset[ConflictClass] = frozenset()

    def __post_init__(self) -> None:
        if not isinstance(self.evaluation_state, SemanticEvaluationStateV2):
            raise TypeError(
                "evaluation_state must be SemanticEvaluationStateV2, "
                f"got {type(self.evaluation_state).__name__}"
            )
        if self.decision is not None and not isinstance(
            self.decision, V2SemanticDecision
        ):
            raise TypeError(
                "decision must be V2SemanticDecision or None, "
                f"got {type(self.decision).__name__}"
            )
        if self.confidence is not None and not isinstance(
            self.confidence, V2Confidence
        ):
            raise TypeError(
                "confidence must be V2Confidence or None, "
                f"got {type(self.confidence).__name__}"
            )
        if not isinstance(self.conflict_classes, frozenset):
            raise TypeError(
                "conflict_classes must be a frozenset, "
                f"got {type(self.conflict_classes).__name__}"
            )
        for conflict in self.conflict_classes:
            if not isinstance(conflict, ConflictClass):
                raise TypeError(
                    "conflict_classes must contain only ConflictClass "
                    f"members, got {conflict!r}"
                )

        if self.evaluation_state is SemanticEvaluationStateV2.EVALUATED:
            if self.decision is None:
                raise ValueError(
                    "EVALUATED requires a decision"
                )
            if self.confidence is None:
                raise ValueError(
                    "EVALUATED requires a confidence"
                )
        else:
            if self.decision is not None:
                raise ValueError(
                    f"{self.evaluation_state.value} may not carry a "
                    "decision; a runtime failure is never interpreted as "
                    "NO_MATCH"
                )
            if self.confidence is not None:
                raise ValueError(
                    f"{self.evaluation_state.value} may not carry a "
                    "confidence"
                )
            if self.conflict_classes:
                raise ValueError(
                    f"{self.evaluation_state.value} may not carry conflict "
                    "classes; conflicts are observed by an evaluation"
                )

    @classmethod
    def not_evaluated(cls) -> "SemanticEvaluationV2":
        return cls(evaluation_state=SemanticEvaluationStateV2.NOT_EVALUATED)

    @classmethod
    def runtime_failure(cls) -> "SemanticEvaluationV2":
        return cls(evaluation_state=SemanticEvaluationStateV2.RUNTIME_FAILURE)

    @classmethod
    def evaluated(
        cls,
        decision: V2SemanticDecision,
        confidence: V2Confidence,
        conflict_classes: frozenset[ConflictClass] = frozenset(),
    ) -> "SemanticEvaluationV2":
        return cls(
            evaluation_state=SemanticEvaluationStateV2.EVALUATED,
            decision=decision,
            confidence=confidence,
            conflict_classes=conflict_classes,
        )


# ---------------------------------------------------------------------------
# Authority matrix (pure contract data)
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class DeterministicStatePolicy:
    """The deterministic (no-semantic-outcome) policy of one V2 state.

    * ``deterministic_tier`` — the workflow tier when nothing is evaluated;
    * ``semantic_eligible`` — whether future semantic AI may be invoked at
      all for this state;
    * ``ai_authority_permitted`` — whether a semantic MATCH may ever reach
      AI_ASSISTED_COMPARABLE for this state;
    * ``human_confirmation_permitted`` — whether a human confirmation
      overlay may apply to this state (a hard conflict cannot be confirmed).
    """

    deterministic_tier: AuthorityTier
    semantic_eligible: bool
    ai_authority_permitted: bool
    human_confirmation_permitted: bool


DETERMINISTIC_STATE_POLICIES: Final[dict[IdentityStateV2, DeterministicStatePolicy]] = (
    {
        IdentityStateV2.DETERMINISTIC_VERIFIED: DeterministicStatePolicy(
            deterministic_tier=AuthorityTier.MACHINE_VERIFIED,
            semantic_eligible=False,
            ai_authority_permitted=False,
            human_confirmation_permitted=False,
        ),
        IdentityStateV2.DETERMINISTIC_CONFLICT: DeterministicStatePolicy(
            deterministic_tier=AuthorityTier.HARD_CONFLICT,
            semantic_eligible=False,
            ai_authority_permitted=False,
            human_confirmation_permitted=False,
        ),
        IdentityStateV2.DETERMINISTIC_UNEVALUABLE: DeterministicStatePolicy(
            deterministic_tier=AuthorityTier.EXCLUDED_LOW_CONFIDENCE,
            semantic_eligible=False,
            ai_authority_permitted=False,
            human_confirmation_permitted=False,
        ),
        IdentityStateV2.DETERMINISTIC_UNCERTAIN: DeterministicStatePolicy(
            deterministic_tier=AuthorityTier.NEEDS_REVIEW,
            semantic_eligible=True,
            ai_authority_permitted=True,
            human_confirmation_permitted=True,
        ),
    }
)


#: The semantic outcome matrix, as data: (decision, confidence, context
#: quality) -> tier, BEFORE ceilings and before hard-conflict supersession.
#:
#: Frozen rules (S2-A contract):
#:
#: * MATCH + HIGH requires authoritative STRONG context (only reviewed
#:   relationship authority produces it) to reach AI_ASSISTED_COMPARABLE;
#:   incomplete (LIMITED/WEAK) context caps it at NEEDS_REVIEW.
#: * MATCH + MEDIUM is always at most NEEDS_REVIEW.
#: * MATCH + LOW, and every NO_MATCH, is EXCLUDED_LOW_CONFIDENCE.
#: * UNCERTAIN with actionable context (LIMITED/STRONG) is NEEDS_REVIEW;
#:   with no actionable context (WEAK) it is EXCLUDED_LOW_CONFIDENCE.
#: * UNCERTAIN + LOW is weak evidence: EXCLUDED_LOW_CONFIDENCE.
#:
#: All 27 (decision x confidence x quality) combinations are defined; the
#: matrix lookup fails closed on anything outside this table.
SEMANTIC_OUTCOME_TIER_MATRIX: Final[
    dict[tuple[V2SemanticDecision, V2Confidence, ContextQuality], AuthorityTier]
] = {
    (V2SemanticDecision.MATCH, V2Confidence.HIGH, ContextQuality.STRONG): (
        AuthorityTier.AI_ASSISTED_COMPARABLE
    ),
    (V2SemanticDecision.MATCH, V2Confidence.HIGH, ContextQuality.LIMITED): (
        AuthorityTier.NEEDS_REVIEW
    ),
    (V2SemanticDecision.MATCH, V2Confidence.HIGH, ContextQuality.WEAK): (
        AuthorityTier.NEEDS_REVIEW
    ),
    (V2SemanticDecision.MATCH, V2Confidence.MEDIUM, ContextQuality.STRONG): (
        AuthorityTier.NEEDS_REVIEW
    ),
    (V2SemanticDecision.MATCH, V2Confidence.MEDIUM, ContextQuality.LIMITED): (
        AuthorityTier.NEEDS_REVIEW
    ),
    (V2SemanticDecision.MATCH, V2Confidence.MEDIUM, ContextQuality.WEAK): (
        AuthorityTier.NEEDS_REVIEW
    ),
    (V2SemanticDecision.MATCH, V2Confidence.LOW, ContextQuality.STRONG): (
        AuthorityTier.EXCLUDED_LOW_CONFIDENCE
    ),
    (V2SemanticDecision.MATCH, V2Confidence.LOW, ContextQuality.LIMITED): (
        AuthorityTier.EXCLUDED_LOW_CONFIDENCE
    ),
    (V2SemanticDecision.MATCH, V2Confidence.LOW, ContextQuality.WEAK): (
        AuthorityTier.EXCLUDED_LOW_CONFIDENCE
    ),
    (V2SemanticDecision.NO_MATCH, V2Confidence.HIGH, ContextQuality.STRONG): (
        AuthorityTier.EXCLUDED_LOW_CONFIDENCE
    ),
    (V2SemanticDecision.NO_MATCH, V2Confidence.HIGH, ContextQuality.LIMITED): (
        AuthorityTier.EXCLUDED_LOW_CONFIDENCE
    ),
    (V2SemanticDecision.NO_MATCH, V2Confidence.HIGH, ContextQuality.WEAK): (
        AuthorityTier.EXCLUDED_LOW_CONFIDENCE
    ),
    (V2SemanticDecision.NO_MATCH, V2Confidence.MEDIUM, ContextQuality.STRONG): (
        AuthorityTier.EXCLUDED_LOW_CONFIDENCE
    ),
    (V2SemanticDecision.NO_MATCH, V2Confidence.MEDIUM, ContextQuality.LIMITED): (
        AuthorityTier.EXCLUDED_LOW_CONFIDENCE
    ),
    (V2SemanticDecision.NO_MATCH, V2Confidence.MEDIUM, ContextQuality.WEAK): (
        AuthorityTier.EXCLUDED_LOW_CONFIDENCE
    ),
    (V2SemanticDecision.NO_MATCH, V2Confidence.LOW, ContextQuality.STRONG): (
        AuthorityTier.EXCLUDED_LOW_CONFIDENCE
    ),
    (V2SemanticDecision.NO_MATCH, V2Confidence.LOW, ContextQuality.LIMITED): (
        AuthorityTier.EXCLUDED_LOW_CONFIDENCE
    ),
    (V2SemanticDecision.NO_MATCH, V2Confidence.LOW, ContextQuality.WEAK): (
        AuthorityTier.EXCLUDED_LOW_CONFIDENCE
    ),
    (V2SemanticDecision.UNCERTAIN, V2Confidence.HIGH, ContextQuality.STRONG): (
        AuthorityTier.NEEDS_REVIEW
    ),
    (V2SemanticDecision.UNCERTAIN, V2Confidence.HIGH, ContextQuality.LIMITED): (
        AuthorityTier.NEEDS_REVIEW
    ),
    (V2SemanticDecision.UNCERTAIN, V2Confidence.HIGH, ContextQuality.WEAK): (
        AuthorityTier.EXCLUDED_LOW_CONFIDENCE
    ),
    (V2SemanticDecision.UNCERTAIN, V2Confidence.MEDIUM, ContextQuality.STRONG): (
        AuthorityTier.NEEDS_REVIEW
    ),
    (V2SemanticDecision.UNCERTAIN, V2Confidence.MEDIUM, ContextQuality.LIMITED): (
        AuthorityTier.NEEDS_REVIEW
    ),
    (V2SemanticDecision.UNCERTAIN, V2Confidence.MEDIUM, ContextQuality.WEAK): (
        AuthorityTier.EXCLUDED_LOW_CONFIDENCE
    ),
    (V2SemanticDecision.UNCERTAIN, V2Confidence.LOW, ContextQuality.STRONG): (
        AuthorityTier.EXCLUDED_LOW_CONFIDENCE
    ),
    (V2SemanticDecision.UNCERTAIN, V2Confidence.LOW, ContextQuality.LIMITED): (
        AuthorityTier.EXCLUDED_LOW_CONFIDENCE
    ),
    (V2SemanticDecision.UNCERTAIN, V2Confidence.LOW, ContextQuality.WEAK): (
        AuthorityTier.EXCLUDED_LOW_CONFIDENCE
    ),
}


#: The NM-2 auto-authority ceiling (Product-lead amendment 1): for
#: U5_NEAR_MISS_MPN + NEAR_MISS_SUBSTITUTION without reviewed relationship
#: authority, the maximum automatic tier is NEEDS_REVIEW — even for
#: MATCH + HIGH + STRONG-context-shaped inputs from other sub-states. This
#: is a generic safety rule, not a manufacturer special case.
NEAR_MISS_SUBSTITUTION_WITHOUT_RELATION_AUTHORITY: Final[AuthorityTier] = (
    AuthorityTier.NEEDS_REVIEW
)

#: Reviewable conflicts cap a MATCH at NEEDS_REVIEW (they never cap an
#: already-more-restrictive outcome).
HARD_CONFLICT_SUPERSEDES_HUMAN: Final[AuthorityTier] = AuthorityTier.HARD_CONFLICT

#: A runtime failure is never interpreted as NO_MATCH (or anything else
#: evidence-shaped): it is SEMANTIC_UNAVAILABLE, full stop.
UNAVAILABLE_IS_NEVER_NO_MATCH: Final[AuthorityTier] = (
    AuthorityTier.SEMANTIC_UNAVAILABLE
)


class AuthorityRuleV2(str, Enum):
    """Audit rules fired by one authority derivation (bounded)."""

    STATE_POLICY_DETERMINISTIC = "STATE_POLICY_DETERMINISTIC"
    """The deterministic state policy produced the tier (no semantic
    outcome consumed)."""

    SEMANTIC_OUTCOME_MATRIX = "SEMANTIC_OUTCOME_MATRIX"
    """The (decision, confidence, context quality) matrix entry produced
    the base tier."""

    INELIGIBLE_STATE_IGNORES_SEMANTIC = "INELIGIBLE_STATE_IGNORES_SEMANTIC"
    """A semantic outcome was supplied for a state that is not semantic-
    eligible; it is ignored and the deterministic tier stands (fail
    closed)."""

    RUNTIME_FAILURE = "RUNTIME_FAILURE"
    """The semantic evaluation failed at runtime; the tier is
    SEMANTIC_UNAVAILABLE and is never interpreted as NO_MATCH."""

    CEILING_REVIEWABLE_CONFLICT = "CEILING_REVIEWABLE_CONFLICT"
    """A reviewable conflict capped a MATCH at NEEDS_REVIEW."""

    CEILING_NEAR_MISS_SUBSTITUTION_WITHOUT_RELATION_AUTHORITY = (
        "CEILING_NEAR_MISS_SUBSTITUTION_WITHOUT_RELATION_AUTHORITY"
    )
    """The NM-2 ceiling capped a MATCH at NEEDS_REVIEW (no reviewed
    relationship authority)."""

    HARD_CONFLICT_SUPERSEDES = "HARD_CONFLICT_SUPERSEDES"
    """An ALWAYS_HARD conflict superseded everything else, including any
    human outcome."""

    HUMAN_CONFIRMED_APPLIED = "HUMAN_CONFIRMED_APPLIED"
    """Human confirmation was applied on an uncertain state (human
    authority outranks AI authority)."""

    HUMAN_REJECTED_APPLIED = "HUMAN_REJECTED_APPLIED"
    """Human rejection was applied on an uncertain state."""

    HARD_CONFLICT_SUPERSEDES_HUMAN = "HARD_CONFLICT_SUPERSEDES_HUMAN"
    """A hard conflict stands above any human outcome (precedence:
    HARD_CONFLICT > HUMAN_CONFIRMED > AI authority)."""

    HUMAN_OUTCOME_NOT_APPLICABLE = "HUMAN_OUTCOME_NOT_APPLICABLE"
    """A human outcome was supplied for a state where the deterministic
    policy does not admit a human overlay; the deterministic tier stands."""


def _apply_needs_review_ceiling(tier: AuthorityTier) -> AuthorityTier:
    """Cap ``tier`` at NEEDS_REVIEW without lifting more-restrictive tiers.

    The ceiling restricts: AI_ASSISTED_COMPARABLE drops to NEEDS_REVIEW;
    NEEDS_REVIEW and EXCLUDED_LOW_CONFIDENCE are unchanged; non-AI tiers
    (MACHINE_VERIFIED, HARD_CONFLICT, SEMANTIC_UNAVAILABLE, human tiers)
    are outside the ceiling's reach entirely.
    """
    if tier is AuthorityTier.AI_ASSISTED_COMPARABLE:
        return AuthorityTier.NEEDS_REVIEW
    return tier


class HumanReviewStateV2(str, Enum):
    """Bounded human review outcome vocabulary for the matrix overlay."""

    CONFIRMED = "CONFIRMED"
    REJECTED = "REJECTED"


@dataclass(frozen=True)
class AuthorityDecisionV2:
    """The pure authority derivation result for one candidate.

    ``tier`` is the derived workflow tier; ``fired_rules`` is the bounded
    audit trail of which contract rules produced it; ``context_quality`` is
    the provenance-derived quality (never AI-derived).
    """

    tier: AuthorityTier
    fired_rules: frozenset[AuthorityRuleV2]
    context_quality: ContextQuality

    def __post_init__(self) -> None:
        if not isinstance(self.tier, AuthorityTier):
            raise TypeError(
                "tier must be AuthorityTier, got "
                f"{type(self.tier).__name__}"
            )
        if not isinstance(self.fired_rules, frozenset):
            raise TypeError(
                "fired_rules must be a frozenset, "
                f"got {type(self.fired_rules).__name__}"
            )
        if not self.fired_rules:
            raise ValueError(
                "an authority decision must record at least one fired rule"
            )
        for rule in self.fired_rules:
            if not isinstance(rule, AuthorityRuleV2):
                raise TypeError(
                    "fired_rules must contain only AuthorityRuleV2 "
                    f"members, got {rule!r}"
                )
        if not isinstance(self.context_quality, ContextQuality):
            raise TypeError(
                "context_quality must be ContextQuality, "
                f"got {type(self.context_quality).__name__}"
            )


def derive_authority_tier(
    assessment_v2: IdentityStateAssessmentV2,
    evaluation: SemanticEvaluationV2 | None = None,
    context_provenances: frozenset[ContextProvenance] = frozenset(),
    human_review: HumanReviewStateV2 | None = None,
) -> AuthorityDecisionV2:
    """Derive the bounded workflow authority tier for one candidate.

    Pure contract data application. Precedence (frozen):

        HARD_CONFLICT > HUMAN_CONFIRMED > AI authority

    and, inside the AI path, the NEEDS_REVIEW ceilings (reviewable
    conflict; NM-2 without relationship authority) restrict but never lift.

    * ``DETERMINISTIC_VERIFIED`` -> MACHINE_VERIFIED, no AI needed: any
      supplied semantic outcome is ignored (ineligible state).
    * ``DETERMINISTIC_CONFLICT`` -> HARD_CONFLICT: AI not eligible, human
      cannot confirm; any supplied semantic or human outcome is superseded.
    * ``DETERMINISTIC_UNEVALUABLE`` -> no AI authority: EXCLUDED_
      LOW_CONFIDENCE stands; outcomes are ignored/superseded.
    * ``DETERMINISTIC_UNCERTAIN`` -> the future semantic AI entry point:
      no evaluation -> NEEDS_REVIEW; runtime failure -> SEMANTIC_
      UNAVAILABLE (never NO_MATCH); a decision -> the 27-entry matrix
      (decision x confidence x provenance-derived context quality), then
      the ceilings, then hard-conflict supersession, then the human
      overlay.
    """
    if not isinstance(assessment_v2, IdentityStateAssessmentV2):
        raise TypeError(
            "assessment_v2 must be IdentityStateAssessmentV2, "
            f"got {type(assessment_v2).__name__}"
        )
    if evaluation is None:
        evaluation = SemanticEvaluationV2.not_evaluated()
    if not isinstance(evaluation, SemanticEvaluationV2):
        raise TypeError(
            "evaluation must be SemanticEvaluationV2, "
            f"got {type(evaluation).__name__}"
        )
    if not isinstance(context_provenances, frozenset):
        raise TypeError("context_provenances must be a frozenset")
    if human_review is not None and not isinstance(
        human_review, HumanReviewStateV2
    ):
        raise TypeError(
            "human_review must be HumanReviewStateV2 or None, "
            f"got {type(human_review).__name__}"
        )

    policy = DETERMINISTIC_STATE_POLICIES[assessment_v2.state]
    context_quality = derive_context_quality(context_provenances)
    rules: set[AuthorityRuleV2] = set()

    if not policy.semantic_eligible:
        # Deterministic authority governs. A semantic outcome supplied for
        # an ineligible state is ignored, never a path to authority.
        tier = policy.deterministic_tier
        rules.add(AuthorityRuleV2.STATE_POLICY_DETERMINISTIC)
        if evaluation.evaluation_state is SemanticEvaluationStateV2.EVALUATED:
            rules.add(AuthorityRuleV2.INELIGIBLE_STATE_IGNORES_SEMANTIC)
    else:
        if evaluation.evaluation_state is (
            SemanticEvaluationStateV2.RUNTIME_FAILURE
        ):
            tier = AuthorityTier.SEMANTIC_UNAVAILABLE
            rules.add(AuthorityRuleV2.RUNTIME_FAILURE)
        elif evaluation.evaluation_state is (
            SemanticEvaluationStateV2.NOT_EVALUATED
        ):
            tier = policy.deterministic_tier
            rules.add(AuthorityRuleV2.STATE_POLICY_DETERMINISTIC)
        else:
            assert evaluation.decision is not None
            assert evaluation.confidence is not None
            base_tier = SEMANTIC_OUTCOME_TIER_MATRIX.get(
                (
                    evaluation.decision,
                    evaluation.confidence,
                    context_quality,
                )
            )
            if base_tier is None:
                # Fail closed: any combination the matrix does not define
                # is treated as weak evidence, never as authority.
                base_tier = AuthorityTier.EXCLUDED_LOW_CONFIDENCE
                rules.add(AuthorityRuleV2.INELIGIBLE_STATE_IGNORES_SEMANTIC)
            else:
                rules.add(AuthorityRuleV2.SEMANTIC_OUTCOME_MATRIX)
            tier = base_tier

            hard_conflicts = evaluation.conflict_classes & ALWAYS_HARD_CONFLICT_CLASSES
            reviewable_conflicts = (
                evaluation.conflict_classes & REVIEWABLE_CONFLICT_CLASSES
            )

            # Ceilings (restrict only; a condition-only conflict is a price
            # dimension and caps nothing).
            if (
                evaluation.decision is V2SemanticDecision.MATCH
                and reviewable_conflicts
            ):
                tier = _apply_needs_review_ceiling(tier)
                rules.add(AuthorityRuleV2.CEILING_REVIEWABLE_CONFLICT)
            if (
                evaluation.decision is V2SemanticDecision.MATCH
                and assessment_v2.near_miss_substitution_active
                and not has_relationship_authority(context_provenances)
            ):
                tier = _apply_needs_review_ceiling(tier)
                rules.add(
                    AuthorityRuleV2
                    .CEILING_NEAR_MISS_SUBSTITUTION_WITHOUT_RELATION_AUTHORITY
                )

            # Hard-conflict supersession (always last inside the AI path).
            if hard_conflicts:
                tier = AuthorityTier.HARD_CONFLICT
                rules.add(AuthorityRuleV2.HARD_CONFLICT_SUPERSEDES)

    # Human overlay. Precedence: HARD_CONFLICT > HUMAN_CONFIRMED > AI.
    if human_review is not None:
        if tier is AuthorityTier.HARD_CONFLICT or not (
            policy.human_confirmation_permitted
        ):
            # A hard conflict cannot be confirmed (or changed) by a human;
            # states without a reviewable uncertainty admit no overlay.
            rules.add(AuthorityRuleV2.HARD_CONFLICT_SUPERSEDES_HUMAN)
            if tier is not AuthorityTier.HARD_CONFLICT:
                rules.add(AuthorityRuleV2.HUMAN_OUTCOME_NOT_APPLICABLE)
        elif human_review is HumanReviewStateV2.CONFIRMED:
            tier = AuthorityTier.HUMAN_CONFIRMED
            rules.add(AuthorityRuleV2.HUMAN_CONFIRMED_APPLIED)
        else:
            tier = AuthorityTier.HUMAN_REJECTED
            rules.add(AuthorityRuleV2.HUMAN_REJECTED_APPLIED)

    return AuthorityDecisionV2(
        tier=tier,
        fired_rules=frozenset(rules),
        context_quality=context_quality,
    )


# ---------------------------------------------------------------------------
# Future UI display vocabulary (S2-A contract only; no UI implemented)
# ---------------------------------------------------------------------------

#: Mandatory future badge concepts, one per authority tier.
AUTHORITY_TIER_BADGES: Final[dict[AuthorityTier, str]] = {
    AuthorityTier.MACHINE_VERIFIED: "Machine Verified",
    AuthorityTier.AI_ASSISTED_COMPARABLE: "AI-Assisted Comparable — not machine verified",
    AuthorityTier.NEEDS_REVIEW: "Needs Review — not verified",
    AuthorityTier.HUMAN_CONFIRMED: "Human Confirmed",
    AuthorityTier.HUMAN_REJECTED: "Human Rejected",
    AuthorityTier.HARD_CONFLICT: "Hard Conflict — excluded",
    AuthorityTier.EXCLUDED_LOW_CONFIDENCE: "Low Confidence",
    AuthorityTier.SEMANTIC_UNAVAILABLE: "AI Evidence Unavailable",
}

#: Frozen future attention order. Ordering means ATTENTION, not authority:
#: 1. NEEDS REVIEW; 2. AI-ASSISTED COMPARABLE; 3. RESOLVED (HUMAN CONFIRMED,
#: MACHINE VERIFIED); 4. EXCLUDED / LOW / HARD / UNAVAILABLE.
UI_ATTENTION_ORDER: Final[tuple[AuthorityTier, ...]] = (
    AuthorityTier.NEEDS_REVIEW,
    AuthorityTier.AI_ASSISTED_COMPARABLE,
    AuthorityTier.HUMAN_CONFIRMED,
    AuthorityTier.MACHINE_VERIFIED,
    AuthorityTier.HUMAN_REJECTED,
    AuthorityTier.HARD_CONFLICT,
    AuthorityTier.EXCLUDED_LOW_CONFIDENCE,
    AuthorityTier.SEMANTIC_UNAVAILABLE,
)

#: Product-lead amendment 3 (summary wording): the future headline for the
#: market-evidence summary. NEEDS_REVIEW items count under market evidence.
LEAD_MARKET_EVIDENCE_SUMMARY_TEMPLATE: Final[str] = (
    "Market evidence found: {count} listings"
)

#: The separate pricing-eligible line. NEEDS_REVIEW never counts as
#: pricing-eligible; no price statistic may include Needs Review before
#: confirmation.
PRICING_ELIGIBLE_SUMMARY_TEMPLATE: Final[str] = (
    "Pricing-eligible comparable listings: {count}"
)

#: The legacy machine line that MAY remain when the V2 UI ships.
LEGACY_MACHINE_VERIFIED_LINE_TEMPLATE: Final[str] = (
    "{count} comparable NEW listings (machine-verified)"
)

#: The misleading headline that must NOT be used when the count contains
#: NEEDS_REVIEW items.
FORBIDDEN_MARKET_EVIDENCE_HEADLINE: Final[str] = "Comparable evidence"

#: Tiers that count under "Market evidence found".
MARKET_EVIDENCE_TIERS: Final[frozenset[AuthorityTier]] = frozenset(
    {
        AuthorityTier.MACHINE_VERIFIED,
        AuthorityTier.AI_ASSISTED_COMPARABLE,
        AuthorityTier.HUMAN_CONFIRMED,
        AuthorityTier.NEEDS_REVIEW,
    }
)

#: Tiers that count as pricing-eligible (a strict subset of market
#: evidence).
PRICING_ELIGIBLE_TIERS: Final[frozenset[AuthorityTier]] = frozenset(
    {
        AuthorityTier.MACHINE_VERIFIED,
        AuthorityTier.AI_ASSISTED_COMPARABLE,
        AuthorityTier.HUMAN_CONFIRMED,
    }
)


# Mechanical self-consistency of the frozen count sets, verified once at
# import (pure data check, no mutable state): market evidence is exactly the
# pricing-eligible tiers plus NEEDS_REVIEW, and NEEDS_REVIEW is never
# pricing-eligible. If a future edit breaks the amendment-3 wording
# contract, the module refuses to import.
if MARKET_EVIDENCE_TIERS != PRICING_ELIGIBLE_TIERS | {AuthorityTier.NEEDS_REVIEW}:
    raise RuntimeError(
        "MARKET_EVIDENCE_TIERS must equal PRICING_ELIGIBLE_TIERS plus "
        "NEEDS_REVIEW (amendment 3 summary wording contract)"
    )
if PRICING_ELIGIBLE_TIERS & {AuthorityTier.NEEDS_REVIEW}:
    raise RuntimeError(
        "NEEDS_REVIEW must never count as pricing-eligible (no price "
        "statistic may include Needs Review before confirmation)"
    )
if (
    len(UI_ATTENTION_ORDER) != len(AuthorityTier)
    or frozenset(UI_ATTENTION_ORDER) != set(AuthorityTier)
):
    raise RuntimeError(
        "UI_ATTENTION_ORDER must list every authority tier exactly once"
    )
if set(AUTHORITY_TIER_BADGES) != set(AuthorityTier):
    raise RuntimeError(
        "AUTHORITY_TIER_BADGES must define one badge per authority tier"
    )
if (
    ALWAYS_HARD_CONFLICT_CLASSES
    | REVIEWABLE_CONFLICT_CLASSES
    | PRICE_DIMENSION_ONLY_CONFLICT_CLASSES
) != set(ConflictClass):
    raise RuntimeError(
        "the conflict severity sets must cover the whole ConflictClass "
        "vocabulary exactly once"
    )
if (
    ALWAYS_HARD_CONFLICT_CLASSES & REVIEWABLE_CONFLICT_CLASSES
    or ALWAYS_HARD_CONFLICT_CLASSES & PRICE_DIMENSION_ONLY_CONFLICT_CLASSES
    or REVIEWABLE_CONFLICT_CLASSES & PRICE_DIMENSION_ONLY_CONFLICT_CLASSES
):
    raise RuntimeError("the conflict severity sets must be disjoint")
if len(SEMANTIC_OUTCOME_TIER_MATRIX) != len(V2SemanticDecision) * len(
    V2Confidence
) * len(ContextQuality):
    raise RuntimeError(
        "SEMANTIC_OUTCOME_TIER_MATRIX must define every (decision, "
        "confidence, context quality) combination"
    )
if set(SEMANTIC_OUTCOME_TIER_MATRIX) != {
    (decision, confidence, quality)
    for decision in V2SemanticDecision
    for confidence in V2Confidence
    for quality in ContextQuality
}:
    raise RuntimeError(
        "SEMANTIC_OUTCOME_TIER_MATRIX must define exactly the (decision, "
        "confidence, context quality) grid"
    )


@dataclass(frozen=True)
class TierSummaryV2:
    """The frozen future summary counts for one set of candidate tiers."""

    market_evidence_count: int
    pricing_eligible_count: int
    needs_review_count: int
    per_tier_counts: frozenset[tuple[AuthorityTier, int]]

    def __post_init__(self) -> None:
        for field_name in (
            "market_evidence_count",
            "pricing_eligible_count",
            "needs_review_count",
        ):
            value = getattr(self, field_name)
            if not isinstance(value, int) or isinstance(value, bool):
                raise TypeError(f"{field_name} must be int")
        if not isinstance(self.per_tier_counts, frozenset):
            raise TypeError("per_tier_counts must be a frozenset")
        seen_tiers: set[AuthorityTier] = set()
        for item in self.per_tier_counts:
            if (
                not isinstance(item, tuple)
                or len(item) != 2
                or not isinstance(item[0], AuthorityTier)
                or not isinstance(item[1], int)
                or isinstance(item[1], bool)
            ):
                raise TypeError(
                    "per_tier_counts must hold (AuthorityTier, int) pairs"
                )
            if item[0] in seen_tiers:
                raise ValueError(
                    f"duplicate tier in per_tier_counts: {item[0].value}"
                )
            seen_tiers.add(item[0])

    @property
    def market_evidence_headline(self) -> str:
        return LEAD_MARKET_EVIDENCE_SUMMARY_TEMPLATE.format(
            count=self.market_evidence_count
        )

    @property
    def pricing_eligible_headline(self) -> str:
        return PRICING_ELIGIBLE_SUMMARY_TEMPLATE.format(
            count=self.pricing_eligible_count
        )


def derive_tier_summary(
    tiers: tuple[AuthorityTier, ...] | list[AuthorityTier],
) -> TierSummaryV2:
    """Compute the frozen summary counts for one set of candidate tiers.

    * ``market_evidence_count`` — tiers in MARKET_EVIDENCE_TIERS
      (NEEDS_REVIEW included);
    * ``pricing_eligible_count`` — tiers in PRICING_ELIGIBLE_TIERS
      (NEEDS_REVIEW NEVER included);
    * ``needs_review_count`` — the explicit review-candidate count, so a
      future presenter can show the breakdown;
    * ``per_tier_counts`` — the exact tier breakdown.
    """
    if isinstance(tiers, (tuple, list)):
        tier_tuple: tuple[AuthorityTier, ...] = tuple(tiers)
    else:
        raise TypeError("tiers must be a tuple or list of AuthorityTier")
    counts: dict[AuthorityTier, int] = {}
    for tier in tier_tuple:
        if not isinstance(tier, AuthorityTier):
            raise TypeError(
                f"tiers must hold AuthorityTier members, got {tier!r}"
            )
        counts[tier] = counts.get(tier, 0) + 1

    market_evidence_count = sum(
        count for tier, count in counts.items() if tier in MARKET_EVIDENCE_TIERS
    )
    pricing_eligible_count = sum(
        count for tier, count in counts.items() if tier in PRICING_ELIGIBLE_TIERS
    )
    needs_review_count = counts.get(AuthorityTier.NEEDS_REVIEW, 0)

    return TierSummaryV2(
        market_evidence_count=market_evidence_count,
        pricing_eligible_count=pricing_eligible_count,
        needs_review_count=needs_review_count,
        per_tier_counts=frozenset(counts.items()),
    )
