"""Semantic Authority Contract V2 — frozen vocabulary and derivation (S2-A,
as corrected by S2-A-FU1 and S2-A-FU2).

PRODUCT-INTEL.SEMANTIC-AUTHORITY-V2-S2-A is a **bounded contract-only phase**:
it establishes the V2 deterministic state overlay vocabulary, the bounded
near-miss relationship signals, the structured conflict taxonomy, the context
provenance classes, the authority-tier matrix, and the future UI display
vocabulary **in code**. It wires nothing into production:

PRODUCT-INTEL.SEMANTIC-AUTHORITY-V2-S2-A-FU1 (this module as corrected)
fixed two independent-review blockers in the S2-A contract:

1. **U4 description-match was re-conservatized.** S2-A made
   ``ContextQuality.STRONG`` globally equivalent to the presence of
   ``MANUFACTURER_RELATION_AUTHORITY``; since the matrix's only
   ``AI_ASSISTED_COMPARABLE`` row is MATCH + HIGH + STRONG, a U4_NO_MPN
candidate — which by definition has no candidate identifier for a
   manufacturer source to establish a relationship for — could never reach
   the automatic tier. The authority prerequisites are now TWO ORTHOGONAL
   dimensions, each derived independently:

   * **A. Product evidence quality** (``ProductEvidenceQuality``:
     STRONG / LIMITED / WEAK) — derived ONLY from the bounded
     product/description evidence profile (usable product title + bounded
     matched-attribute facts grounded in frozen page or reviewed product
     evidence) and from reviewed product grounding provenance classes.
     Never from model confidence, decisions, or model-claimed attributes.
     A matched-attribute fact can be grounded ONLY in the bounded sources
     ``LISTING_PRODUCT_TITLE`` or ``REVIEWED_PRODUCT_CONTEXT`` — the
     vocabulary has no member for a model claim, so the future semantic
     runtime cannot self-promote its authority by asserting attributes.

   * **B. Identifier relationship authority** (``RelationshipAuthority``:
     ESTABLISHED / NOT_ESTABLISHED / NOT_APPLICABLE) — derived from the
     candidate state (does an identifier-relationship question exist?) and
     from the context provenance classes (``MANUFACTURER_RELATION_AUTHORITY``
     is the class that may answer it; ``CUSTOMER_RETRIEVAL_RELATION``
     confers ZERO relationship authority).

   The matrix is keyed on product evidence quality. The
   identifier-relationship question is state-specific: it does NOT exist for
   U4_NO_MPN (NOT_APPLICABLE — no candidate identifier exists for a
   relationship to establish), so U4 auto-authority never requires
   ``MANUFACTURER_RELATION_AUTHORITY``. For U1/U2/U3/U5 the question DOES
   exist, and reaching ``AI_ASSISTED_COMPARABLE`` requires it to be answered
   ESTABLISHED (the NM-2 ceiling, Product-lead amendment 1, remains the
   explicit frozen form of that requirement for U5 +
   NEAR_MISS_SUBSTITUTION).

2. **Frozen contract tables were mutable dicts.** ``Final[dict[...]]`` is
   not runtime immutability. Every authority/context/display mapping in this
   module is now a frozen tuple of immutable entries (tuples, enums, frozen
   dataclasses, frozensets, str) with a pure lookup function, self-checked
   for completeness at import. No mutable global state of any kind exists in
   this module.

PRODUCT-INTEL.SEMANTIC-AUTHORITY-V2-S2-A-FU2 (this module as further
corrected) fixed a third independent-review blocker in the S2-A-FU1
contract: the identifier-relationship gate was over-broad. FU1 required
``RelationshipAuthority.ESTABLISHED`` for EVERY U1/U2/U3/U5 candidate
before ``AI_ASSISTED_COMPARABLE`` was allowed. The relationship
requirement itself must be STATE-SPECIFIC bounded contract data — not an
ad hoc gate and not a global U1-U5 rule. It is now the frozen
``SUBSTATE_RELATIONSHIP_REQUIREMENTS`` table: one
``RelationshipRequirement`` per permitted (sub-state, primary
identifier-relationship signal) combination, import-self-checked for
completeness, with a pure fail-closed lookup
(``substate_relationship_requirement``):

* U1_TITLE_MPN -> NOT_REQUIRED. The state exists precisely because
deterministic 3C refuses to treat title text as manufacturer identity
authority; the semantic evaluation determines whether the MPN denotes the
product or is merely compatibility/reference/SEO text. MATCH + HIGH +
STRONG bounded product evidence + no HARD/REVIEWABLE conflict reaches the
automatic tier WITHOUT MANUFACTURER_RELATION_AUTHORITY.
COMPATIBILITY_WORDING / accessory / product-role conflicts remain safety
inputs through the structured conflict taxonomy.
* U2_SKU_ONLY -> primary-signal-specific: SKU_EQUALS_TARGET ->
NOT_APPLICABLE (the published SKU is frozen-2A identical to the target: the
relationship is deterministically established, so there is nothing for a
reviewed source to establish); SKU_NOT_TARGET ->
REVIEWED_RELATION_AUTHORITY_REQUIRED (the conservative explicit policy: the
published SKU is not the target).
* U3_PARTIAL_BOUNDARY -> REVIEWED_RELATION_AUTHORITY_REQUIRED (the
conservative explicit policy: partial boundary evidence is weaker than
U1's exact-title-MPN).
* U4_NO_MPN -> NOT_APPLICABLE (FU1 behavior unchanged: no candidate
identifier exists).
* U5_NEAR_MISS_MPN -> primary-signal-specific: NEAR_MISS_TRUNCATION (NM-1)
-> REVIEWED_RELATION_AUTHORITY_REQUIRED (explicit bounded NM-1 policy:
strict prefix/truncation is uncertainty only, never identity proof);
NEAR_MISS_SUBSTITUTION (NM-2) -> REVIEWED_RELATION_AUTHORITY_REQUIRED (the
frozen NM-2 ceiling, Product-lead amendment 1, keeps its own audit rule).
* Verified / C1 / E1 / E2 -> NOT_APPLICABLE (no AI-authority path
consults the requirement).

The automatic tier is capped at NEEDS_REVIEW (fired rule
CEILING_IDENTIFIER_RELATIONSHIP_NOT_ESTABLISHED) when — and only when —
the candidate's table entry requires REVIEWED_RELATION_AUTHORITY and
dimension B is not ESTABLISHED. CUSTOMER_RETRIEVAL_RELATION confers zero
relationship authority and never satisfies the requirement. Dimensions A
and B themselves (``derive_product_evidence_quality`` /
``derive_relationship_authority``) are unchanged from FU1.

It wires nothing into production:

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
   ``NEEDS_REVIEW`` — even for MATCH + HIGH + strong product evidence. The
   ceiling is data in the authority matrix, not a prompt convention.
2. **Distinct context provenance classes.** ``MANUFACTURER_PRODUCT_CONTEXT``
   (reviewed manufacturer product facts — base MPN/category/family; may
   strengthen PRODUCT evidence grounding but does NOT establish the
   identifier relationship), ``MANUFACTURER_RELATION_AUTHORITY`` (reviewed
   manufacturer / approved authoritative source explicitly establishing the
   relevant identifier relationship — the class that may answer the
   identifier-relationship question ESTABLISHED where that question exists),
   and ``CUSTOMER_RETRIEVAL_RELATION`` (project-defined retrieval recall aid;
   NEVER identity authority, NEVER an alias/equivalence proof, ZERO
   relationship authority, no product grounding, never enters 4A) are
   distinct bounded classes with disjoint capability sets.
3. **Summary wording.** The future display summary is
   ``"Market evidence found: N listings"`` (NEEDS_REVIEW counts under market
   evidence), with a separate
   ``"Pricing-eligible comparable listings: N"`` line (NEEDS_REVIEW never
   counts as pricing-eligible; no price statistic may include Needs Review
   before confirmation). The legacy machine line
   ``"N comparable NEW listings (machine-verified)"`` may remain. The
   misleading "Comparable evidence: N listings" headline is forbidden when
   the count contains NEEDS_REVIEW items.

S2-A-FU1 corrections (frozen here)
----------------------------------

* ``ContextQuality`` / ``derive_context_quality`` (the S2-A global
  RELATION-iff-STRONG coupling) are REMOVED and replaced by the two
  orthogonal dimensions above (``ProductEvidenceQuality`` +
  ``RelationshipAuthority``).
* ``ProductEvidenceProfileV2`` is the bounded future-V2 input for product/
  description evidence: a usable-product-title fact plus bounded
  matched-attribute facts (dimension + grounded candidate-side sources).
  The STRONG bar is bounded and testable: a usable title AND at least
  ``STRONG_PRODUCT_EVIDENCE_MIN_MATCHED_FACTS`` matched facts spanning at
  least ``STRONG_PRODUCT_EVIDENCE_MIN_MATCHED_DIMENSIONS`` distinct hard
  product dimensions. A title alone is NOT strong; a model claim is NOT a
  source.
* ``derive_relationship_authority`` is state-specific: U4_NO_MPN is
  NOT_APPLICABLE (the identifier-relationship question does not exist);
  U1/U2/U3/U5 are ESTABLISHED only with reviewed relationship provenance;
  verified states are ESTABLISHED by the frozen deterministic comparator;
  C1 is NOT_ESTABLISHED; E1/E2 are NOT_APPLICABLE.
* The authority matrix is keyed on (decision, confidence, PRODUCT evidence
  quality); reaching ``AI_ASSISTED_COMPARABLE`` additionally requires the
  state-specific identifier-relationship question to be NOT_APPLICABLE
  (U4) or ESTABLISHED (U1/U2/U3/U5) — the general form of the NM-2
  ceiling, which remains its own frozen audit rule for U5 +
  NEAR_MISS_SUBSTITUTION.
  CORRECTED BY S2-A-FU2: the blanket ESTABLISHED requirement for
  U1/U2/U3/U5 was over-broad. The relationship requirement is now the
  frozen state/sub-state-specific ``SUBSTATE_RELATIONSHIP_REQUIREMENTS``
  table: U1_TITLE_MPN and U2 + SKU_EQUALS_TARGET do NOT require reviewed
  relationship authority; U2 + SKU_NOT_TARGET, U3, U5 + NM-1, and U5 +
  NM-2 do; U4 behavior is unchanged. The NM-2 ceiling remains its own
  frozen audit rule.
* Every frozen contract mapping in this module is a runtime-immutable
  tuple of immutable entries plus a pure lookup function (no mutable
  global state, no ``dict`` anywhere in the module's globals).

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
    "CandidateProductEvidenceSource",
    "ConflictClass",
    "ConflictSeverity",
    "ConflictSubstateV2",
    "ContextCapability",
    "ContextProvenance",
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
    "ProductEvidenceDimension",
    "ProductEvidenceFactV2",
    "ProductEvidenceProfileV2",
    "ProductEvidenceQuality",
    "REVIEWABLE_CONFLICT_CLASSES",
    "RelationshipAuthority",
    "RelationshipRequirement",
    "SEMANTIC_OUTCOME_TIER_MATRIX",
    "SemanticEvaluationStateV2",
    "SemanticEvaluationV2",
    "STRONG_PRODUCT_EVIDENCE_MIN_MATCHED_DIMENSIONS",
    "STRONG_PRODUCT_EVIDENCE_MIN_MATCHED_FACTS",
    "SUBSTATE_RELATIONSHIP_REQUIREMENTS",
    "TierSummaryV2",
    "UNAVAILABLE_IS_NEVER_NO_MATCH",
    "UncertainSubstateV2",
    "UnevaluableSubstateV2",
    "UI_ATTENTION_ORDER",
    "V2Confidence",
    "V2SemanticDecision",
    "VerifiedSubstateV2",
    "authority_tier_badge",
    "conflict_class_severity",
    "context_provenance_capabilities",
    "derive_authority_tier",
    "derive_identity_state_v2",
    "derive_product_evidence_quality",
    "derive_relationship_authority",
    "derive_tier_summary",
    "deterministic_state_policy",
    "has_relationship_authority",
    "is_hard_conflict_class",
    "is_near_miss_substitution",
    "is_near_miss_truncation",
    "is_price_dimension_only_class",
    "is_reviewable_conflict_class",
    "is_v2_semantic_entry_point",
    "near_miss_shape",
    "semantic_outcome_tier",
    "substate_relationship_requirement",
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
    never automatic identity).

    S2-A-FU2: relationship requirement NOT_REQUIRED — the semantic
    evaluation resolves whether the title MPN denotes the product or is
    merely compatibility/reference/SEO text; the automatic tier never
    requires reviewed relationship authority (conflicts remain safety
    inputs through the taxonomy)."""

    U2_SKU_ONLY = "U2_SKU_ONLY"
    """The listing published a SKU field and no explicit MPN field.

    S2-A-FU2: relationship requirement is primary-signal-specific —
    SKU_EQUALS_TARGET: NOT_APPLICABLE (frozen-2A identical to the target);
    SKU_NOT_TARGET: REVIEWED_RELATION_AUTHORITY_REQUIRED (conservative
    explicit policy)."""

    U3_PARTIAL_BOUNDARY = "U3_PARTIAL_BOUNDARY"
    """Frozen 3C classified a PARTIAL boundary overlap (3C PARTIAL_MPN_ONLY).

    S2-A-FU2: relationship requirement
    REVIEWED_RELATION_AUTHORITY_REQUIRED (conservative explicit policy:
    partial boundary evidence is weaker than U1's exact-title-MPN)."""

    U4_NO_MPN = "U4_NO_MPN"
    """No usable manufacturer MPN evidence, but usable product title
    evidence. Intentional recall feature for future semantic evaluation;
    eligibility does not mean authority.

    S2-A-FU2: relationship requirement NOT_APPLICABLE (FU1 behavior
    unchanged: no candidate identifier exists)."""

    U5_NEAR_MISS_MPN = "U5_NEAR_MISS_MPN"
    """Explicit MPN mismatch in a bounded near-miss shape (NM-1 or NM-2).
    Near-miss membership is NEVER identity authority.

    S2-A-FU2: relationship requirement is near-miss-shape-specific — NM-1
    (NEAR_MISS_TRUNCATION) and NM-2 (NEAR_MISS_SUBSTITUTION) are each
    REVIEWED_RELATION_AUTHORITY_REQUIRED (explicit bounded U5 policies;
    NM-2 keeps its frozen ceiling audit rule)."""


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
# construction time (fail closed). Frozen tuple of immutable entries with a
# pure lookup helper (S2-A-FU1: no mutable global state).
_PRIMARY_SIGNALS_BY_SUBSTATE: Final[
    tuple[tuple[str, frozenset[IdentityRelationshipSignal]], ...]
] = (
    ("C1_INCOMPATIBLE_EXPLICIT_MPN", frozenset({IdentityRelationshipSignal.NO_RELATION})),
    ("E1_NO_TARGET_MPN", frozenset({IdentityRelationshipSignal.NO_RELATION})),
    ("E2_NO_CANDIDATE_EVIDENCE", frozenset(
        {
            IdentityRelationshipSignal.NO_RELATION,
            IdentityRelationshipSignal.EMPTY_MPN_FIELD,
        }
    )),
    ("U1_TITLE_MPN", frozenset({IdentityRelationshipSignal.TITLE_MPN_TOKEN})),
    ("U2_SKU_ONLY", frozenset(
        {
            IdentityRelationshipSignal.SKU_EQUALS_TARGET,
            IdentityRelationshipSignal.SKU_NOT_TARGET,
        }
    )),
    ("U3_PARTIAL_BOUNDARY", frozenset(
        {IdentityRelationshipSignal.PARTIAL_BOUNDARY}
    )),
    ("U4_NO_MPN", frozenset(
        {
            IdentityRelationshipSignal.NO_RELATION,
            IdentityRelationshipSignal.EMPTY_MPN_FIELD,
        }
    )),
    ("U5_NEAR_MISS_MPN", frozenset(
        {
            IdentityRelationshipSignal.NEAR_MISS_TRUNCATION,
            IdentityRelationshipSignal.NEAR_MISS_SUBSTITUTION,
        }
    )),
    ("V_EXACT", frozenset({IdentityRelationshipSignal.EXACT})),
    ("V_NORMALIZED_EXACT", frozenset(
        {IdentityRelationshipSignal.NORMALIZED_EXACT}
    )),
)


def _primary_signals_for_substate(
    substate_value: str,
) -> frozenset[IdentityRelationshipSignal]:
    """Pure lookup over the frozen per-substate primary-signal table."""
    for value, signals in _PRIMARY_SIGNALS_BY_SUBSTATE:
        if value == substate_value:
            return signals
    raise ValueError(
        f"sub-state {substate_value} has no permitted primary relationship "
        "signals in the frozen V2 contract; fail closed"
    )


_STATE_OF_SUBSTATE: Final[tuple[tuple[str, IdentityStateV2], ...]] = (
    ("C1_INCOMPATIBLE_EXPLICIT_MPN", IdentityStateV2.DETERMINISTIC_CONFLICT),
    ("E1_NO_TARGET_MPN", IdentityStateV2.DETERMINISTIC_UNEVALUABLE),
    ("E2_NO_CANDIDATE_EVIDENCE", IdentityStateV2.DETERMINISTIC_UNEVALUABLE),
    ("U1_TITLE_MPN", IdentityStateV2.DETERMINISTIC_UNCERTAIN),
    ("U2_SKU_ONLY", IdentityStateV2.DETERMINISTIC_UNCERTAIN),
    ("U3_PARTIAL_BOUNDARY", IdentityStateV2.DETERMINISTIC_UNCERTAIN),
    ("U4_NO_MPN", IdentityStateV2.DETERMINISTIC_UNCERTAIN),
    ("U5_NEAR_MISS_MPN", IdentityStateV2.DETERMINISTIC_UNCERTAIN),
    ("V_EXACT", IdentityStateV2.DETERMINISTIC_VERIFIED),
    ("V_NORMALIZED_EXACT", IdentityStateV2.DETERMINISTIC_VERIFIED),
)


def _state_for_substate(substate_value: str) -> IdentityStateV2 | None:
    """Pure lookup over the frozen sub-state -> state table (None if absent)."""
    for value, state in _STATE_OF_SUBSTATE:
        if value == substate_value:
            return state
    return None


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
        expected_state = _state_for_substate(self.substate.value)
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
        permitted = _primary_signals_for_substate(self.substate.value)
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
# Orthogonal authority prerequisites (Product-lead amendment 2, as
# corrected by S2-A-FU1)
#
# The S2-A contract coupled context quality to identifier-relationship
# authority (STRONG iff MANUFACTURER_RELATION_AUTHORITY present), which
# re-conservatized U4_NO_MPN: a no-MPN candidate has no identifier
# relationship for a manufacturer source to establish, and was therefore
# locked out of the automatic tier. The authority prerequisites are now
# TWO ORTHOGONAL dimensions, each derived independently:
#
#   A. Product evidence quality (ProductEvidenceQuality) — how strongly
#      the candidate's product/description evidence is grounded (bounded
#      evidence bar; never derived from model output).
#   B. Identifier relationship authority (RelationshipAuthority) — state-
#      specific: does the candidate pose an identifier-relationship
#      question, and if so, is it answered by reviewed authoritative
#      relationship provenance?
# ---------------------------------------------------------------------------


class ContextProvenance(str, Enum):
    """Distinct bounded context provenance classes.

    These are deliberately separate classes, not one ambiguous boolean:

    * ``MANUFACTURER_PRODUCT_CONTEXT`` — a reviewed manufacturer source
      establishes facts about the base product (base MPN / category /
      family). It may strengthen PRODUCT evidence grounding. It does NOT
      establish the identifier relationship.
    * ``MANUFACTURER_RELATION_AUTHORITY`` — a reviewed manufacturer or
      equivalent approved authoritative source explicitly establishes the
      relevant relationship/equivalence between identifiers. This is the
      class that MAY answer the identifier-relationship question
      ESTABLISHED where that question exists. It also carries reviewed
      product grounding.
    * ``CUSTOMER_RETRIEVAL_RELATION`` — a customer/project-defined
      relationship existing solely to improve retrieval recall. It is NOT
      manufacturer-published identity/equivalence authority and MUST NEVER,
      by itself: establish identity, produce machine-verified authority,
      raise NM-2 to automatic comparable, confer any relationship
      authority, ground product evidence, override conflict, enter 4A, or
      be described to the model as manufacturer-established equivalence.
    """

    MANUFACTURER_PRODUCT_CONTEXT = "MANUFACTURER_PRODUCT_CONTEXT"
    MANUFACTURER_RELATION_AUTHORITY = "MANUFACTURER_RELATION_AUTHORITY"
    CUSTOMER_RETRIEVAL_RELATION = "CUSTOMER_RETRIEVAL_RELATION"


class ContextCapability(str, Enum):
    """What a context provenance class is permitted to do."""

    GROUND_PRODUCT_FACTS = "GROUND_PRODUCT_FACTS"
    """Reviewed product facts (base MPN / category / family grounding).
    May ground matched-attribute facts and raise product evidence quality
    to LIMITED; does NOT establish the identifier relationship."""

    ESTABLISH_IDENTIFIER_RELATIONSHIP = "ESTABLISH_IDENTIFIER_RELATIONSHIP"
    """A reviewed authoritative identifier relationship/equivalence. The
    only capability that can answer the state-specific
    identifier-relationship question ESTABLISHED. It does NOT by itself
    supply product evidence quality (that is dimension A)."""

    RETRIEVAL_RECALL_ONLY = "RETRIEVAL_RECALL_ONLY"
    """Recall aid. No identity, no equivalence, no authority of any kind,
    and no product grounding."""


#: Frozen capability table (S2-A contract; S2-A-FU1 representation):
#: runtime-immutable tuple of (provenance, capabilities) entries with a
#: pure lookup function.
CONTEXT_PROVENANCE_CAPABILITIES: Final[
    tuple[tuple[ContextProvenance, frozenset[ContextCapability]], ...]
] = (
    (
        ContextProvenance.MANUFACTURER_PRODUCT_CONTEXT,
        frozenset({ContextCapability.GROUND_PRODUCT_FACTS}),
    ),
    (
        ContextProvenance.MANUFACTURER_RELATION_AUTHORITY,
        frozenset(
            {
                ContextCapability.GROUND_PRODUCT_FACTS,
                ContextCapability.ESTABLISH_IDENTIFIER_RELATIONSHIP,
            }
        ),
    ),
    (
        ContextProvenance.CUSTOMER_RETRIEVAL_RELATION,
        frozenset({ContextCapability.RETRIEVAL_RECALL_ONLY}),
    ),
)


def context_provenance_capabilities(
    provenance: ContextProvenance,
) -> frozenset[ContextCapability]:
    """Pure lookup of the frozen capability set of one provenance class.

    Fails closed on anything that is not a ``ContextProvenance`` member or
    that the frozen table does not define.
    """
    if not isinstance(provenance, ContextProvenance):
        raise TypeError(
            "provenance must be ContextProvenance, "
            f"got {type(provenance).__name__}"
        )
    for entry_provenance, capabilities in CONTEXT_PROVENANCE_CAPABILITIES:
        if entry_provenance is provenance:
            return capabilities
    raise ValueError(
        f"provenance {provenance.value} has no frozen capability entry; "
        "the capability table must cover the whole vocabulary"
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
        capabilities |= context_provenance_capabilities(provenance)
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

    Note: presence of relationship provenance is necessary but NOT
    sufficient for relationship authority to be ESTABLISHED — the question
    must exist for the candidate state (see
    ``derive_relationship_authority``: U4_NO_MPN is NOT_APPLICABLE even
    with relationship provenance present).
    """
    if not isinstance(provenances, frozenset):
        raise TypeError("provenances must be a frozenset")
    capabilities = _union_capabilities(provenances)
    return ContextCapability.ESTABLISH_IDENTIFIER_RELATIONSHIP in capabilities


class RelationshipAuthority(str, Enum):
    """Dimension B — the state-specific identifier-relationship question.

    Orthogonal to product evidence quality: relationship authority answers
    "does a reviewed authoritative source establish the identifier
    relationship for this candidate?", which is a different question from
    "how well grounded is the candidate's product evidence?".
    """

    ESTABLISHED = "ESTABLISHED"
    """The identifier-relationship question is answered: by the frozen
    deterministic comparator (verified states) or by reviewed authoritative
    relationship provenance (MANUFACTURER_RELATION_AUTHORITY)."""

    NOT_ESTABLISHED = "NOT_ESTABLISHED"
    """The candidate poses an identifier-relationship question (U1/U2/U3/U5)
    that no reviewed authoritative relationship provenance answers."""

    NOT_APPLICABLE = "NOT_APPLICABLE"
    """No identifier-relationship question exists for this candidate
    (U4_NO_MPN: there is no candidate identifier for a relationship to
    establish; E1/E2: no target or no candidate evidence at all).
    Relationship provenance cannot change this: there is nothing for it to
    establish."""


def derive_relationship_authority(
    assessment_v2: IdentityStateAssessmentV2,
    provenances: frozenset[ContextProvenance],
) -> RelationshipAuthority:
    """Derive dimension B for one candidate: state-specific.

    * U4_NO_MPN -> NOT_APPLICABLE, regardless of provenance: by definition
      the candidate publishes no usable identifier, so there is no
      identifier relationship for any source to establish. U4 auto-
      authority therefore NEVER requires
      ``MANUFACTURER_RELATION_AUTHORITY``.
    * U1 / U2 / U3 / U5 -> the identifier-relationship question EXISTS
      (the candidate published identifier-like evidence the frozen 3C gate
      could not resolve). ESTABLISHED only with reviewed authoritative
      relationship provenance (``has_relationship_authority``); otherwise
      NOT_ESTABLISHED. ``CUSTOMER_RETRIEVAL_RELATION`` confers zero
      relationship authority.
    * Verified states -> ESTABLISHED: the relationship is established by
      the frozen deterministic comparator (the assessment itself is the
      authority).
    * C1 -> NOT_ESTABLISHED: the question exists and the explicit
      mismatch is deterministic (AI-ineligible state regardless).
    * E1 / E2 -> NOT_APPLICABLE: no target MPN / no candidate evidence.

    Note: this derivation records the FACTUAL answer for audit (dimension
    B). Whether the automatic tier DEPENDS on it is a separate, state/
    sub-state-specific policy: the frozen
    ``SUBSTATE_RELATIONSHIP_REQUIREMENTS`` table (S2-A-FU2) — U1_TITLE_MPN
    and U2 + SKU_EQUALS_TARGET carry no reviewed-relationship requirement
    even though dimension B reads NOT_ESTABLISHED without reviewed
    provenance.
    """
    if not isinstance(assessment_v2, IdentityStateAssessmentV2):
        raise TypeError(
            "assessment_v2 must be IdentityStateAssessmentV2, "
            f"got {type(assessment_v2).__name__}"
        )
    if not isinstance(provenances, frozenset):
        raise TypeError("provenances must be a frozenset")

    if assessment_v2.substate is UncertainSubstateV2.U4_NO_MPN:
        return RelationshipAuthority.NOT_APPLICABLE
    if assessment_v2.state is IdentityStateV2.DETERMINISTIC_VERIFIED:
        return RelationshipAuthority.ESTABLISHED
    if assessment_v2.state is IdentityStateV2.DETERMINISTIC_UNCERTAIN:
        if has_relationship_authority(provenances):
            return RelationshipAuthority.ESTABLISHED
        return RelationshipAuthority.NOT_ESTABLISHED
    if assessment_v2.state is IdentityStateV2.DETERMINISTIC_CONFLICT:
        return RelationshipAuthority.NOT_ESTABLISHED
    return RelationshipAuthority.NOT_APPLICABLE


# ---------------------------------------------------------------------------
# State/sub-state-specific relationship requirement (S2-A-FU2)
#
# S2-A-FU1 gated the automatic tier on RelationshipAuthority being
# ESTABLISHED for EVERY U1/U2/U3/U5 candidate. That was over-broad: the
# relationship requirement itself must be state-specific bounded contract
# data (the purpose of semantic AI is to resolve deterministic
# uncertainty; absence of manufacturer relationship proof must not force
# every uncertain identifier-shaped listing into human review). The frozen
# table below assigns exactly one RelationshipRequirement per permitted
# (sub-state, primary signal) combination; only
# REVIEWED_RELATION_AUTHORITY_REQUIRED entries cap the automatic tier.
# ---------------------------------------------------------------------------


class RelationshipRequirement(str, Enum):
    """The state/sub-state-specific reviewed-relationship requirement for
    reaching ``AI_ASSISTED_COMPARABLE`` (S2-A-FU2).

    This is POLICY, not a derived fact: it decides whether the automatic
    tier depends on dimension B (``RelationshipAuthority``) being
    ESTABLISHED. It is frozen data (``SUBSTATE_RELATIONSHIP_REQUIREMENTS``),
    completeness-checked at import, fail-closed in the lookup, and
    consumable by a future V3 harness without copying.
    """

    NOT_APPLICABLE = "NOT_APPLICABLE"
    """No reviewed-relationship requirement gates the automatic tier for
    this entry. Either the state admits no AI authority at all (verified,
    C1, E1, E2 — the requirement is never consulted), no
    identifier-relationship question exists for the candidate (U4_NO_MPN:
    there is no candidate identifier for a relationship to establish), or
    the relationship is already established by the frozen deterministic
    comparator (U2 + SKU_EQUALS_TARGET: the published SKU is frozen-2A
    identical to the target, so there is nothing for a reviewed source to
    establish). Dimension B may still read NOT_ESTABLISHED where no
    reviewed provenance is present; nothing is REQUIRED.

    S2-A-FU2: U4_NO_MPN keeps its FU1 behavior (NOT_APPLICABLE).
    """

    NOT_REQUIRED = "NOT_REQUIRED"
    """An identifier-relationship question exists, but reaching
    AI_ASSISTED_COMPARABLE does NOT require reviewed relationship
    authority. The bounded state-specific policy delegates the question
    to the semantic evaluation itself, gated by the product-evidence bar
    (dimension A) and the structured conflict taxonomy: U1_TITLE_MPN
    exists precisely because deterministic 3C refuses to treat title text
    as manufacturer identity authority — the semantic evaluation
    determines whether the MPN denotes the product or is merely
    compatibility/reference/SEO text. COMPATIBILITY_WORDING and
    accessory / product-role conflicts remain safety inputs through the
    taxonomy (ALWAYS_HARD supersession; reviewable ceiling).
    """

    REVIEWED_RELATION_AUTHORITY_REQUIRED = "REVIEWED_RELATION_AUTHORITY_REQUIRED"
    """Reaching AI_ASSISTED_COMPARABLE requires
    ``RelationshipAuthority.ESTABLISHED`` — reviewed authoritative
    relationship provenance (``MANUFACTURER_RELATION_AUTHORITY`` or a
    future reviewed relationship-authority class).
    ``CUSTOMER_RETRIEVAL_RELATION`` confers zero relationship authority
    and never satisfies this requirement. The bounded forms: U2 +
    SKU_NOT_TARGET (the published SKU is not the target — more
    conservative than the exact-title-MPN case), U3_PARTIAL_BOUNDARY
    (partial boundary evidence is weaker than U1's exact-title-MPN),
    U5 + NEAR_MISS_TRUNCATION (NM-1 is uncertainty only, never identity
    proof), and U5 + NEAR_MISS_SUBSTITUTION (the frozen NM-2 ceiling,
    Product-lead amendment 1, which also keeps its own audit rule).
    """


#: Frozen state/sub-state-specific relationship requirement table
#: (S2-A-FU2): runtime-immutable tuple of (sub-state, primary signal,
#: requirement) entries with a pure lookup function. The table covers
#: EXACTLY the (sub-state, primary signal) combinations the frozen
#: derivation permits (import-self-checked against
#: ``_PRIMARY_SIGNALS_BY_SUBSTATE``); unknown combinations fail closed in
#: the lookup. Each entry is an explicit bounded policy — no global
#: U1-U5 rule.
SUBSTATE_RELATIONSHIP_REQUIREMENTS: Final[
    tuple[
        tuple[
            (
                VerifiedSubstateV2
                | UncertainSubstateV2
                | ConflictSubstateV2
                | UnevaluableSubstateV2
            ),
            IdentityRelationshipSignal,
            RelationshipRequirement,
        ],
        ...
    ]
] = (
    (
        VerifiedSubstateV2.V_EXACT,
        IdentityRelationshipSignal.EXACT,
        RelationshipRequirement.NOT_APPLICABLE,
    ),
    (
        VerifiedSubstateV2.V_NORMALIZED_EXACT,
        IdentityRelationshipSignal.NORMALIZED_EXACT,
        RelationshipRequirement.NOT_APPLICABLE,
    ),
    (
        UncertainSubstateV2.U1_TITLE_MPN,
        IdentityRelationshipSignal.TITLE_MPN_TOKEN,
        RelationshipRequirement.NOT_REQUIRED,
    ),
    (
        UncertainSubstateV2.U2_SKU_ONLY,
        IdentityRelationshipSignal.SKU_EQUALS_TARGET,
        RelationshipRequirement.NOT_APPLICABLE,
    ),
    (
        UncertainSubstateV2.U2_SKU_ONLY,
        IdentityRelationshipSignal.SKU_NOT_TARGET,
        RelationshipRequirement.REVIEWED_RELATION_AUTHORITY_REQUIRED,
    ),
    (
        UncertainSubstateV2.U3_PARTIAL_BOUNDARY,
        IdentityRelationshipSignal.PARTIAL_BOUNDARY,
        RelationshipRequirement.REVIEWED_RELATION_AUTHORITY_REQUIRED,
    ),
    (
        UncertainSubstateV2.U4_NO_MPN,
        IdentityRelationshipSignal.NO_RELATION,
        RelationshipRequirement.NOT_APPLICABLE,
    ),
    (
        UncertainSubstateV2.U4_NO_MPN,
        IdentityRelationshipSignal.EMPTY_MPN_FIELD,
        RelationshipRequirement.NOT_APPLICABLE,
    ),
    (
        UncertainSubstateV2.U5_NEAR_MISS_MPN,
        IdentityRelationshipSignal.NEAR_MISS_TRUNCATION,
        RelationshipRequirement.REVIEWED_RELATION_AUTHORITY_REQUIRED,
    ),
    (
        UncertainSubstateV2.U5_NEAR_MISS_MPN,
        IdentityRelationshipSignal.NEAR_MISS_SUBSTITUTION,
        RelationshipRequirement.REVIEWED_RELATION_AUTHORITY_REQUIRED,
    ),
    (
        ConflictSubstateV2.C1_INCOMPATIBLE_EXPLICIT_MPN,
        IdentityRelationshipSignal.NO_RELATION,
        RelationshipRequirement.NOT_APPLICABLE,
    ),
    (
        UnevaluableSubstateV2.E1_NO_TARGET_MPN,
        IdentityRelationshipSignal.NO_RELATION,
        RelationshipRequirement.NOT_APPLICABLE,
    ),
    (
        UnevaluableSubstateV2.E2_NO_CANDIDATE_EVIDENCE,
        IdentityRelationshipSignal.NO_RELATION,
        RelationshipRequirement.NOT_APPLICABLE,
    ),
    (
        UnevaluableSubstateV2.E2_NO_CANDIDATE_EVIDENCE,
        IdentityRelationshipSignal.EMPTY_MPN_FIELD,
        RelationshipRequirement.NOT_APPLICABLE,
    ),
)


def substate_relationship_requirement(
    substate: (
        VerifiedSubstateV2
        | UncertainSubstateV2
        | ConflictSubstateV2
        | UnevaluableSubstateV2
    ),
    primary_signal: IdentityRelationshipSignal,
) -> RelationshipRequirement:
    """Pure lookup of the frozen state/sub-state-specific relationship
    requirement for one (sub-state, primary signal) combination
    (S2-A-FU2).

    This is the bounded contract data the automatic tier consults:
    ``derive_authority_tier`` caps a would-be
    ``AI_ASSISTED_COMPARABLE`` at ``NEEDS_REVIEW`` (fired rule
    ``CEILING_IDENTIFIER_RELATIONSHIP_NOT_ESTABLISHED``) when — and only
    when — the requirement is
    ``REVIEWED_RELATION_AUTHORITY_REQUIRED`` and dimension B is not
    ESTABLISHED. A future V3 harness can consume the frozen table / this
    lookup directly.

    Fails closed: TypeError on a non-V2 sub-state or non-signal input;
    ValueError on a combination the frozen table does not define (an
    unknown combination never gains authority).
    """
    substate_type = type(substate)
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
    if not isinstance(primary_signal, IdentityRelationshipSignal):
        raise TypeError(
            "primary_signal must be IdentityRelationshipSignal, "
            f"got {type(primary_signal).__name__}"
        )
    for entry_substate, entry_signal, requirement in (
        SUBSTATE_RELATIONSHIP_REQUIREMENTS
    ):
        if entry_substate is substate and entry_signal is primary_signal:
            return requirement
    raise ValueError(
        f"(sub-state {substate.value}, primary signal "
        f"{primary_signal.value}) has no frozen relationship requirement "
        "in the V2 contract; unknown combinations fail closed (S2-A-FU2)"
    )


class ProductEvidenceQuality(str, Enum):
    """Dimension A — how strongly the candidate's product/description
    evidence is grounded. Orthogonal to identifier relationship authority.

    Computed ONLY from the bounded product-evidence profile (usable
    product title + grounded matched-attribute facts) and reviewed product
    grounding provenance classes — never from model confidence, model
    decisions, or model-claimed matched attributes.
    """

    STRONG = "STRONG"
    """Meets the full bounded STRONG evidence bar: a usable product title
    plus at least ``STRONG_PRODUCT_EVIDENCE_MIN_MATCHED_FACTS`` bounded
    matched-attribute facts spanning at least
    ``STRONG_PRODUCT_EVIDENCE_MIN_MATCHED_DIMENSIONS`` distinct hard
    product dimensions, each grounded in frozen page evidence or reviewed
    product context."""

    LIMITED = "LIMITED"
    """Some product grounding exists (usable title, reviewed product
    grounding, or at least one matched fact) but the full bounded STRONG
    bar is not met."""

    WEAK = "WEAK"
    """No usable product title, no reviewed product grounding, and no
    bounded matched facts (or retrieval-aid provenance only, which grounds
    nothing)."""


class ProductEvidenceDimension(str, Enum):
    """Bounded hard product-identity dimensions a matched-attribute fact
    may name (S2-A-FU1).

    The vocabulary mirrors the ALWAYS_HARD conflict classes of the same
    name: a MATCH on one of these dimensions is the positive of a hard
    conflict on it, so a STRONG profile corroborates exactly the identity
    dimensions a conflict would break. Deliberately excluded: price /
    packaging / condition dimensions (not product identity) and reviewable
    dimensions (REVISION_OR_SUFFIX / BRAND — a reviewable difference is not
    strong corroboration). Extending the vocabulary is a future reviewed
    change, not a runtime decision.
    """

    PRODUCT_FAMILY = "PRODUCT_FAMILY"
    GENERATION = "GENERATION"
    CAPACITY = "CAPACITY"
    INTERFACE = "INTERFACE"
    FORM_FACTOR = "FORM_FACTOR"
    PRODUCT_ROLE = "PRODUCT_ROLE"


class CandidateProductEvidenceSource(str, Enum):
    """Bounded candidate-side sources that may ground a matched-attribute
    fact (S2-A-FU1).

    Only frozen page evidence and reviewed product context qualify. The
    vocabulary deliberately has NO member for a model claim: the future
    semantic runtime's output cannot ground its own evidence, so a model
    cannot self-promote its authority by asserting arbitrary matched
    attributes.
    """

    LISTING_PRODUCT_TITLE = "LISTING_PRODUCT_TITLE"
    """The candidate's frozen listing product title text (page evidence).
    Requires the profile to carry a usable product title."""

    REVIEWED_PRODUCT_CONTEXT = "REVIEWED_PRODUCT_CONTEXT"
    """A reviewed product-context provenance (one carrying
    ``GROUND_PRODUCT_FACTS``: MANUFACTURER_PRODUCT_CONTEXT or
    MANUFACTURER_RELATION_AUTHORITY). Requires such a provenance to be
    present; CUSTOMER_RETRIEVAL_RELATION can never ground a fact."""


#: Bounded STRONG evidence bar (S2-A-FU1, future-qualifiable by V3): the
#: minimum number of bounded matched-attribute facts, and the minimum
#: number of DISTINCT hard product dimensions they must span, required for
#: STRONG product evidence quality (together with a usable product title).
STRONG_PRODUCT_EVIDENCE_MIN_MATCHED_FACTS: Final[int] = 2
STRONG_PRODUCT_EVIDENCE_MIN_MATCHED_DIMENSIONS: Final[int] = 2


@dataclass(frozen=True)
class ProductEvidenceFactV2:
    """One bounded matched-attribute fact (S2-A-FU1).

    Asserts that the requested product and the candidate agree on one hard
    product dimension, with the candidate-side value grounded in at least
    one bounded candidate-side source. Construction fails closed on an
    empty source set: an ungrounded (model-claimed) fact is outside the
    contract.
    """

    dimension: ProductEvidenceDimension
    sources: frozenset[CandidateProductEvidenceSource]

    def __post_init__(self) -> None:
        if not isinstance(self.dimension, ProductEvidenceDimension):
            raise TypeError(
                "dimension must be ProductEvidenceDimension, "
                f"got {type(self.dimension).__name__}"
            )
        if not isinstance(self.sources, frozenset):
            raise TypeError(
                "sources must be a frozenset, "
                f"got {type(self.sources).__name__}"
            )
        if not self.sources:
            raise ValueError(
                "a matched-attribute fact requires at least one bounded "
                "candidate-side source; an ungrounded (model-claimed) fact "
                "is outside the contract and cannot carry authority"
            )
        for source in self.sources:
            if not isinstance(source, CandidateProductEvidenceSource):
                raise TypeError(
                    "sources must contain only CandidateProductEvidenceSource "
                    f"members, got {source!r}"
                )


@dataclass(frozen=True)
class ProductEvidenceProfileV2:
    """The bounded product/description evidence profile of one candidate
    (S2-A-FU1).

    This is the future-V2 input contract for dimension A: what the V2
    harness may supply as product evidence. It is derived from FROZEN
    evidence (the listing's product title, reviewed product context) —
    never from model output. The authority contract, not the model, decides
    which inputs can satisfy the auto-authority bar.

    Cross-consistency (fail closed): a fact grounded in the listing product
    title requires the profile to carry a usable product title.
    """

    has_usable_product_title: bool
    matched_facts: frozenset[ProductEvidenceFactV2]

    def __post_init__(self) -> None:
        if not isinstance(self.has_usable_product_title, bool):
            raise TypeError("has_usable_product_title must be bool")
        if not isinstance(self.matched_facts, frozenset):
            raise TypeError(
                "matched_facts must be a frozenset, "
                f"got {type(self.matched_facts).__name__}"
            )
        for fact in self.matched_facts:
            if not isinstance(fact, ProductEvidenceFactV2):
                raise TypeError(
                    "matched_facts must contain only ProductEvidenceFactV2, "
                    f"got {fact!r}"
                )
            if (
                CandidateProductEvidenceSource.LISTING_PRODUCT_TITLE
                in fact.sources
                and not self.has_usable_product_title
            ):
                raise ValueError(
                    "a matched-attribute fact grounded in the listing "
                    "product title requires a usable product title; the "
                    "profile is internally inconsistent"
                )


def derive_product_evidence_quality(
    profile: ProductEvidenceProfileV2,
    provenances: frozenset[ContextProvenance],
) -> ProductEvidenceQuality:
    """Derive dimension A for one candidate (S2-A-FU1).

    Bounded, testable STRONG bar (frozen; future-qualifiable by V3):

    * STRONG <=> the profile carries a usable product title AND at least
      ``STRONG_PRODUCT_EVIDENCE_MIN_MATCHED_FACTS`` bounded matched facts
      spanning at least
      ``STRONG_PRODUCT_EVIDENCE_MIN_MATCHED_DIMENSIONS`` distinct hard
      product dimensions.
    * LIMITED <=> not STRONG, and some product grounding exists: a usable
      product title, reviewed product grounding (a provenance carrying
      ``GROUND_PRODUCT_FACTS``), or at least one matched fact.
    * WEAK <=> no usable title, no reviewed product grounding, no matched
      facts. ``CUSTOMER_RETRIEVAL_RELATION`` alone is WEAK (it carries no
      grounding capability).

    A title alone is NOT strong: corroboration across distinct hard product
    dimensions is the bar. Model confidence / decisions / claimed
    attributes never enter this derivation.

    Fails closed (ValueError) on an unsupported profile: a fact grounded in
    ``REVIEWED_PRODUCT_CONTEXT`` requires a provenance carrying
    ``GROUND_PRODUCT_FACTS`` to be present (customer retrieval can never
    ground a fact).
    """
    if not isinstance(profile, ProductEvidenceProfileV2):
        raise TypeError(
            "profile must be ProductEvidenceProfileV2, "
            f"got {type(profile).__name__}"
        )
    if not isinstance(provenances, frozenset):
        raise TypeError("provenances must be a frozenset")

    capabilities = _union_capabilities(provenances)
    reviewed_grounding = (
        ContextCapability.GROUND_PRODUCT_FACTS in capabilities
    )
    for fact in profile.matched_facts:
        if (
            CandidateProductEvidenceSource.REVIEWED_PRODUCT_CONTEXT
            in fact.sources
            and not reviewed_grounding
        ):
            raise ValueError(
                "a matched-attribute fact grounded in reviewed product "
                "context requires a reviewed product provenance "
                "(MANUFACTURER_PRODUCT_CONTEXT or MANUFACTURER_RELATION_"
                "AUTHORITY); the profile is unsupported"
            )

    distinct_dimensions = {fact.dimension for fact in profile.matched_facts}
    if (
        profile.has_usable_product_title
        and len(profile.matched_facts)
        >= STRONG_PRODUCT_EVIDENCE_MIN_MATCHED_FACTS
        and len(distinct_dimensions)
        >= STRONG_PRODUCT_EVIDENCE_MIN_MATCHED_DIMENSIONS
    ):
        return ProductEvidenceQuality.STRONG
    if (
        profile.has_usable_product_title
        or reviewed_grounding
        or profile.matched_facts
    ):
        return ProductEvidenceQuality.LIMITED
    return ProductEvidenceQuality.WEAK


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


#: Frozen per-state policies (S2-A contract; S2-A-FU1 representation):
#: runtime-immutable tuple of (state, policy) entries with a pure lookup
#: function.
DETERMINISTIC_STATE_POLICIES: Final[
    tuple[tuple[IdentityStateV2, DeterministicStatePolicy], ...]
] = (
    (
        IdentityStateV2.DETERMINISTIC_VERIFIED,
        DeterministicStatePolicy(
            deterministic_tier=AuthorityTier.MACHINE_VERIFIED,
            semantic_eligible=False,
            ai_authority_permitted=False,
            human_confirmation_permitted=False,
        ),
    ),
    (
        IdentityStateV2.DETERMINISTIC_UNCERTAIN,
        DeterministicStatePolicy(
            deterministic_tier=AuthorityTier.NEEDS_REVIEW,
            semantic_eligible=True,
            ai_authority_permitted=True,
            human_confirmation_permitted=True,
        ),
    ),
    (
        IdentityStateV2.DETERMINISTIC_CONFLICT,
        DeterministicStatePolicy(
            deterministic_tier=AuthorityTier.HARD_CONFLICT,
            semantic_eligible=False,
            ai_authority_permitted=False,
            human_confirmation_permitted=False,
        ),
    ),
    (
        IdentityStateV2.DETERMINISTIC_UNEVALUABLE,
        DeterministicStatePolicy(
            deterministic_tier=AuthorityTier.EXCLUDED_LOW_CONFIDENCE,
            semantic_eligible=False,
            ai_authority_permitted=False,
            human_confirmation_permitted=False,
        ),
    ),
)


def deterministic_state_policy(
    state: IdentityStateV2,
) -> DeterministicStatePolicy:
    """Pure lookup of the frozen policy of one V2 state.

    Fails closed on anything that is not an ``IdentityStateV2`` member or
    that the frozen table does not define.
    """
    if not isinstance(state, IdentityStateV2):
        raise TypeError(
            "state must be IdentityStateV2, "
            f"got {type(state).__name__}"
        )
    for entry_state, policy in DETERMINISTIC_STATE_POLICIES:
        if entry_state is state:
            return policy
    raise ValueError(
        f"state {state.value} has no frozen policy entry; the policy "
        "table must cover the whole state vocabulary"
    )


#: The semantic outcome matrix, as data: (decision, confidence, PRODUCT
#: evidence quality) -> tier, BEFORE ceilings and before hard-conflict
#: supersession. S2-A-FU1: the quality dimension is the orthogonal
#: ProductEvidenceQuality (bounded product/description evidence bar), NOT
#: identifier-relationship authority. Runtime-immutable tuple of
#: ((key), tier) entries with a pure lookup function.
#:
#: Frozen rules (S2-A contract, S2-A-FU1 key):
#:
#: * MATCH + HIGH requires STRONG product evidence to reach
#:   AI_ASSISTED_COMPARABLE (the row base; the state-specific
#:   identifier-relationship gate then applies on top); incomplete
#:   (LIMITED/WEAK) product evidence caps it at NEEDS_REVIEW.
#: * MATCH + MEDIUM is always at most NEEDS_REVIEW.
#: * MATCH + LOW, and every NO_MATCH, is EXCLUDED_LOW_CONFIDENCE.
#: * UNCERTAIN with actionable product evidence (LIMITED/STRONG) is
#:   NEEDS_REVIEW; with no actionable product evidence (WEAK) it is
#:   EXCLUDED_LOW_CONFIDENCE.
#: * UNCERTAIN + LOW is weak evidence: EXCLUDED_LOW_CONFIDENCE.
#:
#: All 27 (decision x confidence x product evidence quality) combinations
#: are defined; the matrix lookup fails closed on anything outside this
#: table.
SEMANTIC_OUTCOME_TIER_MATRIX: Final[
    tuple[
        tuple[tuple[V2SemanticDecision, V2Confidence, ProductEvidenceQuality], AuthorityTier],
        ...
    ]
] = (
    ((V2SemanticDecision.MATCH, V2Confidence.HIGH, ProductEvidenceQuality.STRONG), (
        AuthorityTier.AI_ASSISTED_COMPARABLE
    )),
    ((V2SemanticDecision.MATCH, V2Confidence.HIGH, ProductEvidenceQuality.LIMITED), (
        AuthorityTier.NEEDS_REVIEW
    )),
    ((V2SemanticDecision.MATCH, V2Confidence.HIGH, ProductEvidenceQuality.WEAK), (
        AuthorityTier.NEEDS_REVIEW
    )),
    ((V2SemanticDecision.MATCH, V2Confidence.MEDIUM, ProductEvidenceQuality.STRONG), (
        AuthorityTier.NEEDS_REVIEW
    )),
    ((V2SemanticDecision.MATCH, V2Confidence.MEDIUM, ProductEvidenceQuality.LIMITED), (
        AuthorityTier.NEEDS_REVIEW
    )),
    ((V2SemanticDecision.MATCH, V2Confidence.MEDIUM, ProductEvidenceQuality.WEAK), (
        AuthorityTier.NEEDS_REVIEW
    )),
    ((V2SemanticDecision.MATCH, V2Confidence.LOW, ProductEvidenceQuality.STRONG), (
        AuthorityTier.EXCLUDED_LOW_CONFIDENCE
    )),
    ((V2SemanticDecision.MATCH, V2Confidence.LOW, ProductEvidenceQuality.LIMITED), (
        AuthorityTier.EXCLUDED_LOW_CONFIDENCE
    )),
    ((V2SemanticDecision.MATCH, V2Confidence.LOW, ProductEvidenceQuality.WEAK), (
        AuthorityTier.EXCLUDED_LOW_CONFIDENCE
    )),
    ((V2SemanticDecision.NO_MATCH, V2Confidence.HIGH, ProductEvidenceQuality.STRONG), (
        AuthorityTier.EXCLUDED_LOW_CONFIDENCE
    )),
    ((V2SemanticDecision.NO_MATCH, V2Confidence.HIGH, ProductEvidenceQuality.LIMITED), (
        AuthorityTier.EXCLUDED_LOW_CONFIDENCE
    )),
    ((V2SemanticDecision.NO_MATCH, V2Confidence.HIGH, ProductEvidenceQuality.WEAK), (
        AuthorityTier.EXCLUDED_LOW_CONFIDENCE
    )),
    ((V2SemanticDecision.NO_MATCH, V2Confidence.MEDIUM, ProductEvidenceQuality.STRONG), (
        AuthorityTier.EXCLUDED_LOW_CONFIDENCE
    )),
    ((V2SemanticDecision.NO_MATCH, V2Confidence.MEDIUM, ProductEvidenceQuality.LIMITED), (
        AuthorityTier.EXCLUDED_LOW_CONFIDENCE
    )),
    ((V2SemanticDecision.NO_MATCH, V2Confidence.MEDIUM, ProductEvidenceQuality.WEAK), (
        AuthorityTier.EXCLUDED_LOW_CONFIDENCE
    )),
    ((V2SemanticDecision.NO_MATCH, V2Confidence.LOW, ProductEvidenceQuality.STRONG), (
        AuthorityTier.EXCLUDED_LOW_CONFIDENCE
    )),
    ((V2SemanticDecision.NO_MATCH, V2Confidence.LOW, ProductEvidenceQuality.LIMITED), (
        AuthorityTier.EXCLUDED_LOW_CONFIDENCE
    )),
    ((V2SemanticDecision.NO_MATCH, V2Confidence.LOW, ProductEvidenceQuality.WEAK), (
        AuthorityTier.EXCLUDED_LOW_CONFIDENCE
    )),
    ((V2SemanticDecision.UNCERTAIN, V2Confidence.HIGH, ProductEvidenceQuality.STRONG), (
        AuthorityTier.NEEDS_REVIEW
    )),
    ((V2SemanticDecision.UNCERTAIN, V2Confidence.HIGH, ProductEvidenceQuality.LIMITED), (
        AuthorityTier.NEEDS_REVIEW
    )),
    ((V2SemanticDecision.UNCERTAIN, V2Confidence.HIGH, ProductEvidenceQuality.WEAK), (
        AuthorityTier.EXCLUDED_LOW_CONFIDENCE
    )),
    ((V2SemanticDecision.UNCERTAIN, V2Confidence.MEDIUM, ProductEvidenceQuality.STRONG), (
        AuthorityTier.NEEDS_REVIEW
    )),
    ((V2SemanticDecision.UNCERTAIN, V2Confidence.MEDIUM, ProductEvidenceQuality.LIMITED), (
        AuthorityTier.NEEDS_REVIEW
    )),
    ((V2SemanticDecision.UNCERTAIN, V2Confidence.MEDIUM, ProductEvidenceQuality.WEAK), (
        AuthorityTier.EXCLUDED_LOW_CONFIDENCE
    )),
    ((V2SemanticDecision.UNCERTAIN, V2Confidence.LOW, ProductEvidenceQuality.STRONG), (
        AuthorityTier.EXCLUDED_LOW_CONFIDENCE
    )),
    ((V2SemanticDecision.UNCERTAIN, V2Confidence.LOW, ProductEvidenceQuality.LIMITED), (
        AuthorityTier.EXCLUDED_LOW_CONFIDENCE
    )),
    ((V2SemanticDecision.UNCERTAIN, V2Confidence.LOW, ProductEvidenceQuality.WEAK), (
        AuthorityTier.EXCLUDED_LOW_CONFIDENCE
    )),
)


def semantic_outcome_tier(
    decision: V2SemanticDecision,
    confidence: V2Confidence,
    quality: ProductEvidenceQuality,
) -> AuthorityTier | None:
    """Pure lookup of the frozen matrix entry for one combination.

    Returns the base tier BEFORE ceilings and before hard-conflict
    supersession. Returns ``None`` when the combination is outside the
    frozen table (the caller fails closed). No mutable lookup cache
    exists: the frozen tuple is scanned directly.
    """
    if not isinstance(decision, V2SemanticDecision):
        raise TypeError(
            "decision must be V2SemanticDecision, "
            f"got {type(decision).__name__}"
        )
    if not isinstance(confidence, V2Confidence):
        raise TypeError(
            "confidence must be V2Confidence, "
            f"got {type(confidence).__name__}"
        )
    if not isinstance(quality, ProductEvidenceQuality):
        raise TypeError(
            "quality must be ProductEvidenceQuality, "
            f"got {type(quality).__name__}"
        )
    for (entry_decision, entry_confidence, entry_quality), tier in (
        SEMANTIC_OUTCOME_TIER_MATRIX
    ):
        if (
            entry_decision is decision
            and entry_confidence is confidence
            and entry_quality is quality
        ):
            return tier
    return None


#: The NM-2 auto-authority ceiling (Product-lead amendment 1): for
#: U5_NEAR_MISS_MPN + NEAR_MISS_SUBSTITUTION without reviewed relationship
#: authority, the maximum automatic tier is NEEDS_REVIEW — even for
#: MATCH + HIGH + STRONG product evidence. This is a generic safety rule,
#: not a manufacturer special case, and it cannot be bypassed by
#: excellent description/product alignment.
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

    CEILING_IDENTIFIER_RELATIONSHIP_NOT_ESTABLISHED = (
        "CEILING_IDENTIFIER_RELATIONSHIP_NOT_ESTABLISHED"
    )
    """The state/sub-state-specific relationship requirement (S2-A-FU2)
    is REVIEWED_RELATION_AUTHORITY_REQUIRED (U2 + SKU_NOT_TARGET,
    U3_PARTIAL_BOUNDARY, U5 + NEAR_MISS_TRUNCATION, U5 +
    NEAR_MISS_SUBSTITUTION) and no reviewed authoritative relationship
    provenance answers it, so the automatic tier was capped at
    NEEDS_REVIEW. Never applies where the frozen requirement table says
    NOT_REQUIRED (U1_TITLE_MPN) or NOT_APPLICABLE (U2 + SKU_EQUALS_TARGET,
    U4_NO_MPN; verified / C1 / E1 / E2 admit no AI-authority path)."""

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
    audit trail of which contract rules produced it; the two orthogonal
    prerequisites (S2-A-FU1) are recorded for audit: ``product_evidence_
    quality`` (dimension A — bounded product/description evidence, never
    model-derived) and ``relationship_authority`` (dimension B — state-
    specific identifier-relationship answer).
    """

    tier: AuthorityTier
    fired_rules: frozenset[AuthorityRuleV2]
    product_evidence_quality: ProductEvidenceQuality
    relationship_authority: RelationshipAuthority

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
        if not isinstance(self.product_evidence_quality, ProductEvidenceQuality):
            raise TypeError(
                "product_evidence_quality must be ProductEvidenceQuality, "
                f"got {type(self.product_evidence_quality).__name__}"
            )
        if not isinstance(
            self.relationship_authority, RelationshipAuthority
        ):
            raise TypeError(
                "relationship_authority must be RelationshipAuthority, "
                f"got {type(self.relationship_authority).__name__}"
            )


def _default_product_evidence_profile(
    assessment_v2: IdentityStateAssessmentV2,
) -> ProductEvidenceProfileV2:
    """The conservative default profile when none is supplied (S2-A-FU1).

    The usable-title fact is state-derived where the frozen derivation
    already established it (U4: usable title; every other state: not
    asserted). No matched facts are ever assumed: automatic authority
    requires an explicit bounded profile, so the default can at most reach
    LIMITED and never STRONG.
    """
    has_title = assessment_v2.substate is UncertainSubstateV2.U4_NO_MPN
    return ProductEvidenceProfileV2(
        has_usable_product_title=has_title,
        matched_facts=frozenset(),
    )


def _validate_profile_against_state(
    assessment_v2: IdentityStateAssessmentV2,
    profile: ProductEvidenceProfileV2,
) -> None:
    """Fail closed on a product-evidence profile that contradicts the
    derived state (S2-A-FU1): U4 candidates were derived through the
    frozen usable-title gate (a usable title exists); E2 candidates carry
    no usable product title at all.
    """
    if (
        assessment_v2.substate is UncertainSubstateV2.U4_NO_MPN
        and not profile.has_usable_product_title
    ):
        raise ValueError(
            "U4_NO_MPN candidates are derived through the frozen usable-"
            "title gate; a product-evidence profile without a usable "
            "product title contradicts the state"
        )
    if (
        assessment_v2.substate
        is UnevaluableSubstateV2.E2_NO_CANDIDATE_EVIDENCE
        and profile.has_usable_product_title
    ):
        raise ValueError(
            "E2_NO_CANDIDATE_EVIDENCE candidates carry no usable product "
            "title; a product-evidence profile with one contradicts the "
            "state"
        )


def derive_authority_tier(
    assessment_v2: IdentityStateAssessmentV2,
    evaluation: SemanticEvaluationV2 | None = None,
    context_provenances: frozenset[ContextProvenance] = frozenset(),
    product_evidence: ProductEvidenceProfileV2 | None = None,
    human_review: HumanReviewStateV2 | None = None,
) -> AuthorityDecisionV2:
    """Derive the bounded workflow authority tier for one candidate.

    Pure contract data application over TWO ORTHOGONAL prerequisites
    (S2-A-FU1): product evidence quality (dimension A, from the bounded
    product-evidence profile + reviewed product grounding) and identifier
    relationship authority (dimension B, state-specific). Precedence
    (frozen):

        HARD_CONFLICT > HUMAN_CONFIRMED > AI authority

    and, inside the AI path, the NEEDS_REVIEW ceilings (reviewable
    conflict; NM-2 without relationship authority; state/sub-state-
    specific relationship requirement unanswered — S2-A-FU2) restrict
    but never lift.

    * ``DETERMINISTIC_VERIFIED`` -> MACHINE_VERIFIED, no AI needed: any
      supplied semantic outcome is ignored (ineligible state).
    * ``DETERMINISTIC_CONFLICT`` -> HARD_CONFLICT: AI not eligible, human
      cannot confirm; any supplied semantic or human outcome is superseded.
    * ``DETERMINISTIC_UNEVALUABLE`` -> no AI authority: EXCLUDED_
      LOW_CONFIDENCE stands; outcomes are ignored/superseded.
    * ``DETERMINISTIC_UNCERTAIN`` -> the future semantic AI entry point:
      no evaluation -> NEEDS_REVIEW; runtime failure -> SEMANTIC_
      UNAVAILABLE (never NO_MATCH); a decision -> the 27-entry matrix
      (decision x confidence x product evidence quality), then the
      ceilings, then hard-conflict supersession, then the human overlay.
      Reaching AI_ASSISTED_COMPARABLE is additionally governed by the
      frozen state/sub-state-specific relationship requirement table
      (``SUBSTATE_RELATIONSHIP_REQUIREMENTS``, S2-A-FU2): the tier is
      capped at NEEDS_REVIEW (fired rule
      CEILING_IDENTIFIER_RELATIONSHIP_NOT_ESTABLISHED) when — and only
      when — the candidate's entry requires
      REVIEWED_RELATION_AUTHORITY (U2 + SKU_NOT_TARGET, U3_PARTIAL_
      BOUNDARY, U5 + NEAR_MISS_TRUNCATION, U5 + NEAR_MISS_SUBSTITUTION)
      and dimension B is not ESTABLISHED. U1_TITLE_MPN (NOT_REQUIRED)
      and U2 + SKU_EQUALS_TARGET (NOT_APPLICABLE: the published SKU is
      frozen-2A identical to the target) carry no reviewed-relationship
      requirement; U4_NO_MPN is NOT_APPLICABLE (FU1 behavior unchanged).

    ``product_evidence`` defaults to the conservative state-derived
    profile (the U4 usable-title fact, else no title; no matched facts),
    which can never by itself reach STRONG: an explicit bounded profile is
    required for automatic authority.

    Fails closed (ValueError) on a profile that contradicts the derived
    state (U4 without a usable title; E2 with one) and on an unsupported
    profile (reviewed-context-grounded facts without reviewed product
    provenance).
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
    if product_evidence is None:
        product_evidence = _default_product_evidence_profile(assessment_v2)
    elif not isinstance(product_evidence, ProductEvidenceProfileV2):
        raise TypeError(
            "product_evidence must be ProductEvidenceProfileV2 or None, "
            f"got {type(product_evidence).__name__}"
        )
    _validate_profile_against_state(assessment_v2, product_evidence)
    if human_review is not None and not isinstance(
        human_review, HumanReviewStateV2
    ):
        raise TypeError(
            "human_review must be HumanReviewStateV2 or None, "
            f"got {type(human_review).__name__}"
        )

    policy = deterministic_state_policy(assessment_v2.state)
    product_evidence_quality = derive_product_evidence_quality(
        product_evidence, context_provenances
    )
    relationship_authority = derive_relationship_authority(
        assessment_v2, context_provenances
    )
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
            base_tier = semantic_outcome_tier(
                evaluation.decision,
                evaluation.confidence,
                product_evidence_quality,
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
            # State/sub-state-specific relationship requirement
            # (S2-A-FU2): the frozen table decides whether the automatic
            # tier depends on dimension B being ESTABLISHED. Only
            # REVIEWED_RELATION_AUTHORITY_REQUIRED entries (U2 +
            # SKU_NOT_TARGET, U3_PARTIAL_BOUNDARY, U5 + NM-1, U5 + NM-2)
            # cap a would-be AI_ASSISTED_COMPARABLE. U1_TITLE_MPN (NOT_
            # REQUIRED) and U2 + SKU_EQUALS_TARGET / U4_NO_MPN (NOT_
            # APPLICABLE) never fire this gate; CUSTOMER_RETRIEVAL_
            # RELATION confers zero relationship authority and cannot
            # clear it.
            if (
                tier is AuthorityTier.AI_ASSISTED_COMPARABLE
                and substate_relationship_requirement(
                    assessment_v2.substate,
                    assessment_v2.primary_relationship_signal,
                )
                is RelationshipRequirement.REVIEWED_RELATION_AUTHORITY_REQUIRED
                and relationship_authority
                is not RelationshipAuthority.ESTABLISHED
            ):
                tier = AuthorityTier.NEEDS_REVIEW
                rules.add(
                    AuthorityRuleV2
                    .CEILING_IDENTIFIER_RELATIONSHIP_NOT_ESTABLISHED
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
        product_evidence_quality=product_evidence_quality,
        relationship_authority=relationship_authority,
    )


# ---------------------------------------------------------------------------
# Future UI display vocabulary (S2-A contract only; no UI implemented)
# ---------------------------------------------------------------------------

#: Mandatory future badge concepts, one per authority tier. Frozen tuple
#: of (tier, badge) entries with a pure lookup function (S2-A-FU1).
AUTHORITY_TIER_BADGES: Final[tuple[tuple[AuthorityTier, str], ...]] = (
    (AuthorityTier.MACHINE_VERIFIED, "Machine Verified"),
    (
        AuthorityTier.AI_ASSISTED_COMPARABLE,
        "AI-Assisted Comparable — not machine verified",
    ),
    (AuthorityTier.NEEDS_REVIEW, "Needs Review — not verified"),
    (AuthorityTier.HUMAN_CONFIRMED, "Human Confirmed"),
    (AuthorityTier.HUMAN_REJECTED, "Human Rejected"),
    (AuthorityTier.HARD_CONFLICT, "Hard Conflict — excluded"),
    (AuthorityTier.EXCLUDED_LOW_CONFIDENCE, "Low Confidence"),
    (AuthorityTier.SEMANTIC_UNAVAILABLE, "AI Evidence Unavailable"),
)


def authority_tier_badge(tier: AuthorityTier) -> str:
    """Pure lookup of the frozen badge concept for one authority tier.

    Fails closed on anything that is not an ``AuthorityTier`` member or
    that the frozen table does not define.
    """
    if not isinstance(tier, AuthorityTier):
        raise TypeError(
            "tier must be AuthorityTier, got "
            f"{type(tier).__name__}"
        )
    for entry_tier, badge in AUTHORITY_TIER_BADGES:
        if entry_tier is tier:
            return badge
    raise ValueError(
        f"tier {tier.value} has no frozen badge entry; the badge table "
        "must define one badge per authority tier"
    )

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


# Mechanical self-consistency of the frozen contract data, verified once
# at import (pure data check, no mutable state): market evidence is
# exactly the pricing-eligible tiers plus NEEDS_REVIEW, NEEDS_REVIEW is
# never pricing-eligible, the attention order / badges / policies /
# capabilities / matrix / relationship-requirement tables are complete
# over their vocabularies, and
# (S2-A-FU1) the module's global namespace carries NO mutable containers
# at all. If a future edit breaks any of these contracts, the module
# refuses to import.
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
if {
    entry_tier for entry_tier, _badge in AUTHORITY_TIER_BADGES
} != set(AuthorityTier) or len(AUTHORITY_TIER_BADGES) != len(AuthorityTier):
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
if len(DETERMINISTIC_STATE_POLICIES) != len(IdentityStateV2) or {
    entry_state for entry_state, _policy in DETERMINISTIC_STATE_POLICIES
} != set(IdentityStateV2):
    raise RuntimeError(
        "DETERMINISTIC_STATE_POLICIES must define exactly one policy per "
        "V2 state"
    )
if len(CONTEXT_PROVENANCE_CAPABILITIES) != len(ContextProvenance) or {
    entry_provenance
    for entry_provenance, _capabilities in CONTEXT_PROVENANCE_CAPABILITIES
} != set(ContextProvenance):
    raise RuntimeError(
        "CONTEXT_PROVENANCE_CAPABILITIES must define exactly one "
        "capability entry per provenance class"
    )
if len(SEMANTIC_OUTCOME_TIER_MATRIX) != len(V2SemanticDecision) * len(
    V2Confidence
) * len(ProductEvidenceQuality):
    raise RuntimeError(
        "SEMANTIC_OUTCOME_TIER_MATRIX must define every (decision, "
        "confidence, product evidence quality) combination"
    )
if {
    key for key, _tier in SEMANTIC_OUTCOME_TIER_MATRIX
} != {
    (decision, confidence, quality)
    for decision in V2SemanticDecision
    for confidence in V2Confidence
    for quality in ProductEvidenceQuality
}:
    raise RuntimeError(
        "SEMANTIC_OUTCOME_TIER_MATRIX must define exactly the (decision, "
        "confidence, product evidence quality) grid"
    )
if len(SUBSTATE_RELATIONSHIP_REQUIREMENTS) != len(
    {
        (entry_substate, entry_signal)
        for entry_substate, entry_signal, _requirement
        in SUBSTATE_RELATIONSHIP_REQUIREMENTS
    }
) or {
    (entry_substate, entry_signal)
    for entry_substate, entry_signal, _requirement
    in SUBSTATE_RELATIONSHIP_REQUIREMENTS
} != {
    (member, signal)
    for value, signals in _PRIMARY_SIGNALS_BY_SUBSTATE
    for family in (
        VerifiedSubstateV2,
        UncertainSubstateV2,
        ConflictSubstateV2,
        UnevaluableSubstateV2,
    )
    for member in family
    if member.value == value
    for signal in signals
}:
    raise RuntimeError(
        "SUBSTATE_RELATIONSHIP_REQUIREMENTS must define exactly one "
        "relationship requirement per (sub-state, primary signal) "
        "combination the frozen V2 derivation permits (S2-A-FU2 "
        "completeness check)"
    )
for _global_name, _global_value in list(globals().items()):
    if _global_name.startswith("__"):
        continue
    if isinstance(_global_value, (dict, list, set)):
        raise RuntimeError(
            f"semantic_authority_v2 global {_global_name} is a mutable "
            "container; frozen contract data must be runtime-immutable "
            "(S2-A-FU1)"
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
