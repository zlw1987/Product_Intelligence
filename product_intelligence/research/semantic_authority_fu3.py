"""Semantic Authority Contract V2, S2-A-FU3 — separately versioned
identity-resolution and sales-unit firewall (CONTRACT ONLY).

PRODUCT-INTEL.SEMANTIC-AUTHORITY-V2-Q3-B4-FU1 (this module) implements the
bounded, versioned foundation of the Q3-B4 authority-boundary decision
(``docs/PRODUCT_INTEL_SEMANTIC_V2_Q3B4_AUTHORITY_BOUNDARY_DECISION.md``,
Task A Option B + Task B Option D). It introduces the separately versioned
authority contract token ``SEMANTIC_AUTHORITY_V2_S2A_FU3`` and, behind
that token ONLY:

1. **``IdentityResolutionBoundV2``** (PART_NUMBER / FAMILY_DESCRIPTION /
   DESCRIPTION / NONE) — independently derived from the RECORDED
   deterministic state (sub-state + primary relationship signal, including
   the already-recorded COMPATIBILITY_WORDING overlay) and the RECORDED
   reviewed context provenances. The model's output never sets it; the
   derivation takes no semantic evaluation input at all. Description and
   family-level matching never becomes part-number ground;
   ``CUSTOMER_RETRIEVAL_RELATION`` confers zero bound authority.
2. **``SalesUnitAuthorityV2``** (PROVEN_EQUIVALENT / UNPROVEN /
   CONTRADICTED) — derived from the RECORDED candidate sales-unit channel
   (the explicit S2-C-FU1 state with its published provenance) plus an
   OPTIONAL explicit target-side unit evidence record with a bounded
   provenance class. The default target commercial unit is the single unit
   of the requested part (the Q1(a) contract default). The fail-closed
   default is UNPROVEN: a recorded absence (channel UNAVAILABLE) never
   becomes proven equivalence, and model-generated attribute claims have no
   path into this derivation (the inputs are the recorded channel and the
   explicit target-side evidence only).
3. **``CEILING_SALES_UNIT_NOT_PROVEN``** — a restrict-only ceiling on the
   AUTOMATIC tier: a would-be ``AI_ASSISTED_COMPARABLE`` with an UNPROVEN
   unit is capped at ``NEEDS_REVIEW``. It never lifts, it never touches
   ``MACHINE_VERIFIED`` (the deterministic path never consults the
   semantic layer), it never overrides ``HARD_CONFLICT`` supersession
   (which stays last), and the human overlay precedence
   (HARD_CONFLICT > HUMAN_CONFIRMED > AI) is unchanged: a human may
   confirm a ceiling-capped candidate (explicit, run-scoped, persisted,
   auditable). A published incompatible unit is CONTRADICTED, not
   UNPROVEN: the absolute rule decides at the decision level and the
   frozen HARD_CONFLICT supersession excludes it (frozen semantics,
   unchanged).
4. **Per-binding dispatch** (``derive_authority_tier_for_contract``): the
   recorded authority token selects the derivation. The old token
   (``SEMANTIC_AUTHORITY_V2_S2A_FU2``) dispatches to the UNCHANGED frozen
   derivation — historical V1 and Prompt 2.0 records replay identically
   under their original binding. Unknown / unrecognized tokens fail
   closed (``UnknownAuthorityContractTokenError``; never silently
   reinterpreted).

What this module deliberately is NOT:

* An in-place amendment. The frozen S2-A module (token
  ``SEMANTIC_AUTHORITY_V2_S2A_FU2``) — its tables, functions, token, and
  semantics — is byte- and behavior-unchanged; its tests stand untouched
  under the old token. Any proposed change to the frozen contract is
  isolated behind the new FU3 token.
* A wiring. Nothing in the live V2 runtime, the V2 persistence adapter,
  the replay dispatch, the execution orchestration, the pricing
  aggregation, or the web layer references this module: the V2 record
  type still pins the old token at construction, the V2 adapter still
  supports exactly the old binding, and ``V2_AUTHORITY_QUALIFIED`` stays
  False. No production record can currently carry the FU3 token, so no
  FU3 tier can reach any consumer.
* An authority promotion. No pricing path is activated; the ceiling can
  only restrict automatic tiers, never promote them; and no model, no
  capture, no deployment, no migration.

The post-freeze acceptance-text conflict ratified with this token (the
Q3-B4 document, section 3.6 / AD-Q3B4-4): under THIS token only, the
S2-A-FU1/FU2 auto-authority behaviors (U1 / U2 + SKU_EQUALS_TARGET /
U4: MATCH + HIGH + STRONG + clean => ``AI_ASSISTED_COMPARABLE``) become
CONDITIONAL on ``SalesUnitAuthorityV2 == PROVEN_EQUIVALENT``; while the
unit is UNPROVEN the automatic tier is capped at ``NEEDS_REVIEW``. The
old token's semantics, records, tests, and replays are unchanged.

Pure research-layer contract: stdlib + the research package's public
surface + the frozen S2-C input-contract module (the recorded channel).
No Django, no I/O, no clock, no network, no LLM, no mutable global state,
no vendor names.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Final

from product_intelligence.research import (
    AUTHORITY_CONTRACT_VERSION_V2,
    AuthorityDecisionV2,
    AuthorityRuleV2,
    AuthorityTier,
    ConflictSubstateV2,
    ContextProvenance,
    HumanReviewStateV2,
    IdentityRelationshipSignal,
    IdentityStateAssessmentV2,
    ProductEvidenceProfileV2,
    ProductEvidenceQuality,
    RelationshipAuthority,
    SemanticEvaluationV2,
    SUBSTATE_RELATIONSHIP_REQUIREMENTS,
    UncertainSubstateV2,
    UnevaluableSubstateV2,
    VerifiedSubstateV2,
    derive_authority_tier,
    has_relationship_authority,
)
from product_intelligence.research.semantic_v2 import (
    CandidateSalesUnitEvidenceV2,
    PackagingEvidenceStateV2,
    SalesUnitKindV2,
    SemanticMatchCaseV2,
)

__all__ = [
    "AUTHORITY_CONTRACT_VERSION_V2_FU3",
    "AuthorityDecisionV2FU3",
    "AuthorityRuleV2FU3",
    "IDENTITY_RESOLUTION_BOUND_TABLE",
    "IdentityResolutionBoundV2",
    "KNOWN_AUTHORITY_CONTRACT_TOKENS",
    "SalesUnitAuthorityV2",
    "TargetSalesUnitEvidenceSourceV2",
    "TargetSalesUnitEvidenceV2",
    "TargetSalesUnitFormV2",
    "UnknownAuthorityContractTokenError",
    "derive_authority_tier_for_contract",
    "derive_authority_tier_fu3",
    "derive_identity_resolution_bound",
    "derive_sales_unit_authority",
    "identity_resolution_bound",
    "is_known_authority_contract_token",
    "sales_unit_authority_from_channel",
]


# ---------------------------------------------------------------------------
# The separately versioned authority contract token
# ---------------------------------------------------------------------------


AUTHORITY_CONTRACT_VERSION_V2_FU3: Final[str] = "SEMANTIC_AUTHORITY_V2_S2A_FU3"
"""The identity of the Semantic Authority Contract V2 AS AMENDED BY
S2-A-FU3 — the separately versioned identity-resolution bound,
sales-unit authority state, and restrict-only sales-unit ceiling. Records
bound to this token derive through ``derive_authority_tier_fu3``; records
bound to the frozen ``SEMANTIC_AUTHORITY_V2_S2A_FU2`` token derive through
the UNCHANGED frozen derivation. No production record is bound to this
token yet: the live V2 adapter, record type, and replay dispatch still
know only the old binding (a future 2.1 production binding is a separate
approval-gated decision — Q3-B4 AD-Q3B4-5)."""


class UnknownAuthorityContractTokenError(ValueError):
    """The recorded authority contract token is not one this code knows
    (fail closed; a historical or future decision is never silently
    reinterpreted under a contract this code cannot verify)."""


#: The authority contract tokens this code can derive under. Both are
#: exact strings; whitespace variants and unknown spellings fail closed.
KNOWN_AUTHORITY_CONTRACT_TOKENS: Final[frozenset[str]] = frozenset(
    {AUTHORITY_CONTRACT_VERSION_V2, AUTHORITY_CONTRACT_VERSION_V2_FU3}
)


def is_known_authority_contract_token(token: object) -> bool:
    """True only for an exact string match of a known authority contract
    token (the frozen FU2 token or the FU3 token). Fails closed with
    ``TypeError`` on a non-string input."""
    if not isinstance(token, str):
        raise TypeError(
            "token must be str, got "
            f"{type(token).__name__ if token is not None else 'None'}"
        )
    return token in KNOWN_AUTHORITY_CONTRACT_TOKENS


# ---------------------------------------------------------------------------
# IdentityResolutionBoundV2 — the maximum identity resolution the RECORDED
# deterministic + reviewed evidence can support for an equivalence MATCH
# (Q3-B4 Task A, Option B). The model never sets it.
# ---------------------------------------------------------------------------


class IdentityResolutionBoundV2(str, Enum):
    """The bounded identity-resolution levels a recorded deterministic
    context can support (S2-A-FU3).

    The bound records what the evidence CAN support — it is not a claim
    that the candidate IS at that resolution (the semantic evaluation
    still decides MATCH / NO_MATCH / UNCERTAIN), and it is never an
    upgrade: a recorded context below part-number level cannot be raised
    by confidence, alignment, provenance abundance, or model output.
    """

    PART_NUMBER = "PART_NUMBER"
    """Part-number identity ground: the frozen deterministic comparator
    (verified states), an exact title MPN in identity wording (U1 without
    compatibility wording), the published SKU frozen-2A identical to the
    target (U2 + SKU_EQUALS_TARGET), or a specifically related part whose
    relationship is established by reviewed manufacturer relation
    authority (U5 with MANUFACTURER_RELATION_AUTHORITY)."""

    FAMILY_DESCRIPTION = "FAMILY_DESCRIPTION"
    """Family + description ground: a consistent partial form (U3
    PARTIAL_BOUNDARY). The shared prefix is never the complete number it
    truncates: family membership is grounded, part-number identity is not."""

    DESCRIPTION = "DESCRIPTION"
    """Description ground: no identifier question exists (U4_NO_MPN) or
    the published identifier is not the target (U2 + SKU_NOT_TARGET), or
    the title MPN is compatibility/reference wording (U1 +
    COMPATIBILITY_WORDING — the token is not an identifier ground). The
    same description can be published by different products."""

    NONE = "NONE"
    """No identity resolution is grounded: the recorded context is a
    deterministic conflict / unevaluable state, or a near-miss (U5)
    WITHOUT reviewed manufacturer relation authority (customer-retrieval
    relations confer zero authority). A MATCH on a NONE bound is the
    CRITICAL false-MATCH shape the qualification corpus guards against."""


#: Frozen identity-resolution bound table (S2-A-FU3): runtime-immutable
#: tuple of (sub-state, primary signal, bound) entries with a pure lookup
#: function. The table covers EXACTLY the (sub-state, primary signal)
#: combinations the frozen S2-A derivation permits (import-self-checked
#: against the frozen relationship-requirement table's key set); unknown
#: combinations fail closed in the lookup.
#:
#: Two entries are refined by ``derive_identity_resolution_bound`` from
#: additional RECORDED facts (still deterministic / reviewed only):
#: U1_TITLE_MPN is PART_NUMBER in identity wording but DESCRIPTION when
#: the COMPATIBILITY_WORDING overlay is recorded; U5_NEAR_MISS_MPN is NONE
#: by default and PART_NUMBER only with reviewed manufacturer relation
#: authority present.
IDENTITY_RESOLUTION_BOUND_TABLE: Final[
    tuple[
        tuple[
            (
                VerifiedSubstateV2
                | UncertainSubstateV2
                | ConflictSubstateV2
                | UnevaluableSubstateV2
            ),
            IdentityRelationshipSignal,
            IdentityResolutionBoundV2,
        ],
        ...
    ]
] = (
    (
        VerifiedSubstateV2.V_EXACT,
        IdentityRelationshipSignal.EXACT,
        IdentityResolutionBoundV2.PART_NUMBER,
    ),
    (
        VerifiedSubstateV2.V_NORMALIZED_EXACT,
        IdentityRelationshipSignal.NORMALIZED_EXACT,
        IdentityResolutionBoundV2.PART_NUMBER,
    ),
    (
        UncertainSubstateV2.U1_TITLE_MPN,
        IdentityRelationshipSignal.TITLE_MPN_TOKEN,
        IdentityResolutionBoundV2.PART_NUMBER,
    ),
    (
        UncertainSubstateV2.U2_SKU_ONLY,
        IdentityRelationshipSignal.SKU_EQUALS_TARGET,
        IdentityResolutionBoundV2.PART_NUMBER,
    ),
    (
        UncertainSubstateV2.U2_SKU_ONLY,
        IdentityRelationshipSignal.SKU_NOT_TARGET,
        IdentityResolutionBoundV2.DESCRIPTION,
    ),
    (
        UncertainSubstateV2.U3_PARTIAL_BOUNDARY,
        IdentityRelationshipSignal.PARTIAL_BOUNDARY,
        IdentityResolutionBoundV2.FAMILY_DESCRIPTION,
    ),
    (
        UncertainSubstateV2.U4_NO_MPN,
        IdentityRelationshipSignal.NO_RELATION,
        IdentityResolutionBoundV2.DESCRIPTION,
    ),
    (
        UncertainSubstateV2.U4_NO_MPN,
        IdentityRelationshipSignal.EMPTY_MPN_FIELD,
        IdentityResolutionBoundV2.DESCRIPTION,
    ),
    (
        UncertainSubstateV2.U5_NEAR_MISS_MPN,
        IdentityRelationshipSignal.NEAR_MISS_TRUNCATION,
        IdentityResolutionBoundV2.NONE,
    ),
    (
        UncertainSubstateV2.U5_NEAR_MISS_MPN,
        IdentityRelationshipSignal.NEAR_MISS_SUBSTITUTION,
        IdentityResolutionBoundV2.NONE,
    ),
    (
        ConflictSubstateV2.C1_INCOMPATIBLE_EXPLICIT_MPN,
        IdentityRelationshipSignal.NO_RELATION,
        IdentityResolutionBoundV2.NONE,
    ),
    (
        UnevaluableSubstateV2.E1_NO_TARGET_MPN,
        IdentityRelationshipSignal.NO_RELATION,
        IdentityResolutionBoundV2.NONE,
    ),
    (
        UnevaluableSubstateV2.E2_NO_CANDIDATE_EVIDENCE,
        IdentityRelationshipSignal.NO_RELATION,
        IdentityResolutionBoundV2.NONE,
    ),
    (
        UnevaluableSubstateV2.E2_NO_CANDIDATE_EVIDENCE,
        IdentityRelationshipSignal.EMPTY_MPN_FIELD,
        IdentityResolutionBoundV2.NONE,
    ),
)


def identity_resolution_bound(
    substate: (
        VerifiedSubstateV2
        | UncertainSubstateV2
        | ConflictSubstateV2
        | UnevaluableSubstateV2
    ),
    primary_signal: IdentityRelationshipSignal,
) -> IdentityResolutionBoundV2:
    """Pure lookup of the frozen base bound for one (sub-state, primary
    signal) combination (S2-A-FU3).

    Fails closed: ``TypeError`` on a non-V2 sub-state or non-signal
    input; ``ValueError`` on a combination the frozen table does not
    define (an unknown combination never gains a bound — and therefore
    never gains identity).
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
    for entry_substate, entry_signal, bound in IDENTITY_RESOLUTION_BOUND_TABLE:
        if entry_substate is substate and entry_signal is primary_signal:
            return bound
    raise ValueError(
        f"(sub-state {substate.value}, primary signal "
        f"{primary_signal.value}) has no frozen identity-resolution bound "
        "in the S2-A-FU3 contract; unknown combinations fail closed"
    )


def derive_identity_resolution_bound(
    assessment_v2: IdentityStateAssessmentV2,
    context_provenances: frozenset[ContextProvenance] = frozenset(),
) -> IdentityResolutionBoundV2:
    """Derive the maximum identity resolution the RECORDED evidence
    supports for one candidate (S2-A-FU3, Task A).

    Input: the frozen deterministic V2 state overlay (sub-state +
    relationship signals, including the recorded COMPATIBILITY_WORDING
    overlay) and the recorded reviewed context provenances ONLY. There is
    no semantic-evaluation input: the model's decision, confidence,
    reason code, and attribute lists can never set, raise, or lower the
    bound.

    Refinements over the base table (both from recorded facts):

    * U1_TITLE_MPN: PART_NUMBER in identity wording; DESCRIPTION when the
      COMPATIBILITY_WORDING overlay is recorded (the title token is
      compatibility/reference/SEO positioning, not an identifier ground —
      the decision then rests on product evidence).
    * U5_NEAR_MISS_MPN: NONE by default; PART_NUMBER only when reviewed
      manufacturer relation authority is present (the labeled authority
      is the ground for the specifically related part).
      ``MANUFACTURER_PRODUCT_CONTEXT`` grounds product facts, not the
      identifier relation; ``CUSTOMER_RETRIEVAL_RELATION`` confers ZERO
      bound authority (retrieval hint only — the 0018/0022 shape).

    Pure, deterministic, fail-closed (``TypeError`` on foreign inputs).
    """
    if not isinstance(assessment_v2, IdentityStateAssessmentV2):
        raise TypeError(
            "assessment_v2 must be IdentityStateAssessmentV2, "
            f"got {type(assessment_v2).__name__}"
        )
    if not isinstance(context_provenances, frozenset):
        raise TypeError("context_provenances must be a frozenset")

    base = identity_resolution_bound(
        assessment_v2.substate, assessment_v2.primary_relationship_signal
    )
    if assessment_v2.substate is UncertainSubstateV2.U1_TITLE_MPN:
        if assessment_v2.has_signal(
            IdentityRelationshipSignal.COMPATIBILITY_WORDING
        ):
            return IdentityResolutionBoundV2.DESCRIPTION
        return IdentityResolutionBoundV2.PART_NUMBER
    if assessment_v2.substate is UncertainSubstateV2.U5_NEAR_MISS_MPN:
        if has_relationship_authority(context_provenances):
            return IdentityResolutionBoundV2.PART_NUMBER
        return IdentityResolutionBoundV2.NONE
    return base


# ---------------------------------------------------------------------------
# SalesUnitAuthorityV2 — the recorded commercial sales-unit question
# (Q3-B4 Task B). Fail-closed default: UNPROVEN.
# ---------------------------------------------------------------------------


class SalesUnitAuthorityV2(str, Enum):
    """The bounded sales-unit authority states (S2-A-FU3, Task B).

    This is COMMERCIAL evidence authority, not identity authority: it
    answers "is the candidate's commercial sales unit proven equivalent
    to the target's?", which is a different question from "is the
    candidate the same physical product?" (the identity-resolution bound)
    and from "does the candidate's price enter a statistic?" (the tier).
    """

    PROVEN_EQUIVALENT = "PROVEN_EQUIVALENT"
    """The RECORDED published channel (with its explicit provenance) and
    the target-side established unit agree: the candidate is published as
    sold in the same commercial unit as the target. Only published,
    independently recorded evidence can establish this — never absence,
    never a model claim."""

    UNPROVEN = "UNPROVEN"
    """The fail-closed default: the recorded absence (channel
    UNAVAILABLE — "do not infer a single unit") or any recorded shape the
    bounded derivation does not prove equivalent. An UNPROVEN unit never
    becomes proven equivalence; it caps the automatic tier at
    NEEDS_REVIEW (CEILING_SALES_UNIT_NOT_PROVEN) and is admissible to a
    price statistic only through the explicit human-confirmed path (the
    future W1 consumer guard)."""

    CONTRADICTED = "CONTRADICTED"
    """The recorded published channel is incompatible with the target's
    commercial unit (e.g. target single unit, candidate a pack of 4 / a
    tray / a bundle). At the decision level the frozen absolute rule
    applies (NO_MATCH + PACKAGING_QUANTITY / BUNDLE); at the tier level
    the frozen HARD_CONFLICT supersession excludes the candidate —
    including against human confirmation (frozen semantics, unchanged).
    The restrict-only ceiling does NOT fire for CONTRADICTED: the
    absolute rule, not the unit ceiling, owns this shape."""


class TargetSalesUnitFormV2(str, Enum):
    """The bounded commercial form a target-side unit evidence record may
    establish for the REQUESTED part (S2-A-FU3).

    The vocabulary mirrors the candidate channel's sales-unit kinds
    exactly (import-self-checked): the two sides of the comparison speak
    the same bounded language.
    """

    SINGLE_UNIT = "SINGLE_UNIT"
    """One retail unit — the DEFAULT target commercial unit (the single
    unit of the requested part, the Q1(a) contract default)."""

    PACK_QUANTITY = "PACK_QUANTITY"
    """A pack of N — the bounded positive quantity is required."""

    TRAY_OR_FACTORY_PACK = "TRAY_OR_FACTORY_PACK"
    """A tray / factory pack — quantity optional when published."""

    BUNDLE = "BUNDLE"
    """A bundle — quantity optional when published."""


class TargetSalesUnitEvidenceSourceV2(str, Enum):
    """The bounded provenance classes for an EXPLICIT target-side unit
    evidence record (S2-A-FU3).

    Both members are SUPPLIED, independently recorded evidence about the
    REQUESTED product:

    * ``REVIEWED_TARGET_CONTEXT`` — a reviewed target context (the main
      execution flow's reviewed manufacturer target context) explicitly
      establishes the requested part's commercial form.
    * ``REQUEST_DESCRIPTION`` — the requested description explicitly
      establishes a different form for the requested part (a structured
      claim supplied with the request, carried with this provenance
      label).

    No member is a model claim: the V2 model's output can never establish
    target-side unit evidence, and a target form is NEVER inferred from
    price, availability, or any other commercial fact. Absence of a
    record is the default single unit — an explicit None, never a guess.
    """

    REVIEWED_TARGET_CONTEXT = "REVIEWED_TARGET_CONTEXT"
    REQUEST_DESCRIPTION = "REQUEST_DESCRIPTION"


@dataclass(frozen=True)
class TargetSalesUnitEvidenceV2:
    """One EXPLICIT target-side commercial-form evidence record
    (S2-A-FU3).

    Immutable and fail-closed at construction: the form vocabulary is
    bounded; the provenance is explicit (no member is a model claim); the
    quantity rules mirror the candidate channel (required positive int
    for PACK_QUANTITY, forbidden for SINGLE_UNIT, optional positive int
    for tray / bundle).
    """

    form: TargetSalesUnitFormV2
    quantity: int | None
    source: TargetSalesUnitEvidenceSourceV2

    def __post_init__(self) -> None:
        if not isinstance(self.form, TargetSalesUnitFormV2):
            raise TypeError(
                "form must be TargetSalesUnitFormV2, "
                f"got {type(self.form).__name__}"
            )
        if not isinstance(self.source, TargetSalesUnitEvidenceSourceV2):
            raise TypeError(
                "source must be TargetSalesUnitEvidenceSourceV2, "
                f"got {type(self.source).__name__}"
            )
        if self.quantity is not None:
            if type(self.quantity) is not int or self.quantity < 1:
                raise ValueError(
                    "a target-side sales-unit quantity must be a positive "
                    f"int (got {self.quantity!r})"
                )
        if (
            self.form is TargetSalesUnitFormV2.PACK_QUANTITY
            and self.quantity is None
        ):
            raise ValueError(
                "a PACK_QUANTITY target form requires the bounded "
                "positive quantity (a pack without a count is outside the "
                "contract)"
            )
        if (
            self.form is TargetSalesUnitFormV2.SINGLE_UNIT
            and self.quantity is not None
        ):
            raise ValueError(
                "a SINGLE_UNIT target form carries no quantity (the unit "
                "is the bounded value)"
            )


def sales_unit_authority_from_channel(
    channel: CandidateSalesUnitEvidenceV2,
    target_evidence: TargetSalesUnitEvidenceV2 | None = None,
) -> SalesUnitAuthorityV2:
    """Derive the sales-unit authority state from the RECORDED candidate
    sales-unit channel and the OPTIONAL explicit target-side unit
    evidence (S2-A-FU3, Task B).

    Pure, deterministic, zero-live, replayable:

    * The default target commercial unit is the SINGLE UNIT of the
      requested part (the Q1(a) contract default); ``target_evidence``
      may explicitly establish a different form (pack quantity / tray /
      bundle) with its bounded provenance.
    * Channel ``UNAVAILABLE`` -> UNPROVEN, for EVERY target-side shape:
      absence is a recorded absence, never "single unit", never
      equivalence (the fail-closed default).
    * Channel ``OBSERVED SINGLE_UNIT`` -> PROVEN_EQUIVALENT against the
      single-unit target (default or explicit); CONTRADICTED when the
      target-side evidence establishes a pack / tray / bundle.
    * Channel ``OBSERVED PACK_QUANTITY n`` -> PROVEN_EQUIVALENT only when
      the target-side evidence establishes the SAME pack n; otherwise
      CONTRADICTED (a published multi-pack against a single-unit target
      is the absolute rule's derivation-level twin).
    * Channel ``OBSERVED TRAY_OR_FACTORY_PACK`` / ``BUNDLE`` ->
      CONTRADICTED against the default single-unit target;
      PROVEN_EQUIVALENT only with the matching target-side established
      kind (and matching quantity when both sides publish one).
    * Never an input: model confidence, model matched/conflicting/
      missing-critical attributes (a model claim of "packaging matched"
      is not independent verification), price, availability, or any other
      commercial fact.

    Fails closed: ``TypeError`` on a foreign channel / target-evidence
    input.
    """
    if not isinstance(channel, CandidateSalesUnitEvidenceV2):
        raise TypeError(
            "channel must be CandidateSalesUnitEvidenceV2 (the recorded "
            f"sales-unit channel), got {type(channel).__name__}"
        )
    if target_evidence is not None and not isinstance(
        target_evidence, TargetSalesUnitEvidenceV2
    ):
        raise TypeError(
            "target_evidence must be TargetSalesUnitEvidenceV2 or None "
            f"(the default single unit), got {type(target_evidence).__name__}"
        )

    if channel.state is PackagingEvidenceStateV2.UNAVAILABLE:
        # Recorded absence: never proven, for every target-side shape.
        return SalesUnitAuthorityV2.UNPROVEN

    # OBSERVED: the channel constructor guarantees kind + raw detail +
    # explicit provenance (and the bounded quantity where the kind
    # carries one).
    kind = channel.kind
    target_form = (
        target_evidence.form if target_evidence is not None else TargetSalesUnitFormV2.SINGLE_UNIT
    )
    if kind is SalesUnitKindV2.SINGLE_UNIT:
        if target_form is TargetSalesUnitFormV2.SINGLE_UNIT:
            return SalesUnitAuthorityV2.PROVEN_EQUIVALENT
        return SalesUnitAuthorityV2.CONTRADICTED
    if kind is SalesUnitKindV2.PACK_QUANTITY:
        if (
            target_evidence is not None
            and target_form is TargetSalesUnitFormV2.PACK_QUANTITY
            and target_evidence.quantity == channel.quantity
        ):
            return SalesUnitAuthorityV2.PROVEN_EQUIVALENT
        return SalesUnitAuthorityV2.CONTRADICTED
    # TRAY_OR_FACTORY_PACK / BUNDLE: proven only with the matching
    # established kind (and matching quantity when both are published).
    if target_form is not TargetSalesUnitFormV2(kind.value):
        return SalesUnitAuthorityV2.CONTRADICTED
    if (
        channel.quantity is not None
        and target_evidence is not None
        and target_evidence.quantity is not None
        and channel.quantity != target_evidence.quantity
    ):
        return SalesUnitAuthorityV2.CONTRADICTED
    return SalesUnitAuthorityV2.PROVEN_EQUIVALENT


def derive_sales_unit_authority(
    case_v2: SemanticMatchCaseV2,
    target_evidence: TargetSalesUnitEvidenceV2 | None = None,
) -> SalesUnitAuthorityV2:
    """The FU3 specification entry point over a RECORDED V2 input: the
    sales-unit authority of one ``SemanticMatchCaseV2`` (S2-A-FU3, Task
    B).

    A pure function of the input's explicit sales-unit channel
    (``candidate_commercial.sales_unit`` — the state is always recorded,
    live always UNAVAILABLE until the P2 extraction phase) and the
    optional explicit target-side evidence. Zero live work, replayable:
    the same recorded input always derives the same state.
    """
    if not isinstance(case_v2, SemanticMatchCaseV2):
        raise TypeError(
            "case_v2 must be SemanticMatchCaseV2 (the recorded V2 input), "
            f"got {type(case_v2).__name__}"
        )
    return sales_unit_authority_from_channel(
        case_v2.candidate_commercial.sales_unit, target_evidence
    )


# ---------------------------------------------------------------------------
# The FU3 audit-rule vocabulary and decision record
# ---------------------------------------------------------------------------


class AuthorityRuleV2FU3(str, Enum):
    """The S2-A-FU3 audit-rule vocabulary: the frozen S2-A rule values
    (mirrored by value, so a FU3 decision's rule trail projects exactly
    onto the frozen vocabulary) plus EXACTLY ONE new restrict-only rule.
    Import-self-checked to be the frozen set + the ceiling — nothing else
    may appear in a FU3 audit trail.
    """

    STATE_POLICY_DETERMINISTIC = "STATE_POLICY_DETERMINISTIC"
    SEMANTIC_OUTCOME_MATRIX = "SEMANTIC_OUTCOME_MATRIX"
    INELIGIBLE_STATE_IGNORES_SEMANTIC = "INELIGIBLE_STATE_IGNORES_SEMANTIC"
    RUNTIME_FAILURE = "RUNTIME_FAILURE"
    CEILING_REVIEWABLE_CONFLICT = "CEILING_REVIEWABLE_CONFLICT"
    CEILING_NEAR_MISS_SUBSTITUTION_WITHOUT_RELATION_AUTHORITY = (
        "CEILING_NEAR_MISS_SUBSTITUTION_WITHOUT_RELATION_AUTHORITY"
    )
    CEILING_IDENTIFIER_RELATIONSHIP_NOT_ESTABLISHED = (
        "CEILING_IDENTIFIER_RELATIONSHIP_NOT_ESTABLISHED"
    )
    CEILING_SALES_UNIT_NOT_PROVEN = "CEILING_SALES_UNIT_NOT_PROVEN"
    """The restrict-only sales-unit ceiling (S2-A-FU3, Task B): a would-be
    AI_ASSISTED_COMPARABLE with an UNPROVEN sales unit is capped at
    NEEDS_REVIEW. It fires ONLY on the automatic AI tier, NEVER lifts a
    more-restrictive outcome, never touches MACHINE_VERIFIED /
    HARD_CONFLICT / the human overlay, and a CONTRADICTED unit does not
    fire it (the frozen absolute rule + HARD_CONFLICT supersession own
    that shape). Human confirmation remains the explicit, auditable path
    above the ceiling."""
    HARD_CONFLICT_SUPERSEDES = "HARD_CONFLICT_SUPERSEDES"
    HUMAN_CONFIRMED_APPLIED = "HUMAN_CONFIRMED_APPLIED"
    HUMAN_REJECTED_APPLIED = "HUMAN_REJECTED_APPLIED"
    HARD_CONFLICT_SUPERSEDES_HUMAN = "HARD_CONFLICT_SUPERSEDES_HUMAN"
    HUMAN_OUTCOME_NOT_APPLICABLE = "HUMAN_OUTCOME_NOT_APPLICABLE"


def _to_fu3_rule(rule: AuthorityRuleV2) -> AuthorityRuleV2FU3:
    """Exact-value projection of a frozen audit rule onto the FU3
    vocabulary (import-self-checked to always exist)."""
    return AuthorityRuleV2FU3(rule.value)


@dataclass(frozen=True)
class AuthorityDecisionV2FU3:
    """The S2-A-FU3 authority derivation result for one candidate.

    Extends the frozen ``AuthorityDecisionV2`` audit surface with the two
    independently derived recorded facts: ``identity_resolution_bound``
    (Task A — the maximum identity resolution the recorded evidence
    supports) and ``sales_unit_authority`` (Task B — the recorded
    commercial sales-unit state). ``fired_rules`` is the FU3 audit trail
    (the frozen rules projected by value, plus the ceiling rule when it
    fired); ``frozen_fired_rules`` projects the trail back onto the
    frozen vocabulary (the ceiling rule has no frozen counterpart and is
    excluded).

    Construction fails closed on the firewall invariant itself: an
    ``AI_ASSISTED_COMPARABLE`` tier with an UNPROVEN unit is
    un-constructible under FU3 (the restrict-only ceiling must have
    fired), and the ceiling rule may only appear with an UNPROVEN unit
    on a NEEDS_REVIEW tier.
    """

    tier: AuthorityTier
    fired_rules: frozenset[AuthorityRuleV2FU3]
    product_evidence_quality: ProductEvidenceQuality
    relationship_authority: RelationshipAuthority
    identity_resolution_bound: IdentityResolutionBoundV2
    sales_unit_authority: SalesUnitAuthorityV2

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
                "an FU3 authority decision must record at least one "
                "fired rule"
            )
        for rule in self.fired_rules:
            if not isinstance(rule, AuthorityRuleV2FU3):
                raise TypeError(
                    "fired_rules must contain only AuthorityRuleV2FU3 "
                    f"members, got {rule!r}"
                )
        if not isinstance(self.product_evidence_quality, ProductEvidenceQuality):
            raise TypeError(
                "product_evidence_quality must be ProductEvidenceQuality, "
                f"got {type(self.product_evidence_quality).__name__}"
            )
        if not isinstance(self.relationship_authority, RelationshipAuthority):
            raise TypeError(
                "relationship_authority must be RelationshipAuthority, "
                f"got {type(self.relationship_authority).__name__}"
            )
        if not isinstance(self.identity_resolution_bound, IdentityResolutionBoundV2):
            raise TypeError(
                "identity_resolution_bound must be IdentityResolutionBoundV2, "
                f"got {type(self.identity_resolution_bound).__name__}"
            )
        if not isinstance(self.sales_unit_authority, SalesUnitAuthorityV2):
            raise TypeError(
                "sales_unit_authority must be SalesUnitAuthorityV2, "
                f"got {type(self.sales_unit_authority).__name__}"
            )
        # The firewall invariant, enforced at construction: the
        # unproven-unit exposure is un-constructible, not merely
        # un-derivable.
        if (
            self.tier is AuthorityTier.AI_ASSISTED_COMPARABLE
            and self.sales_unit_authority is SalesUnitAuthorityV2.UNPROVEN
        ):
            raise ValueError(
                "an unproven sales unit can never hold the automatic "
                "comparable tier under the FU3 contract; the "
                "restrict-only ceiling must have capped it at "
                "NEEDS_REVIEW"
            )
        if AuthorityRuleV2FU3.CEILING_SALES_UNIT_NOT_PROVEN in self.fired_rules:
            if (
                self.sales_unit_authority is not SalesUnitAuthorityV2.UNPROVEN
                or self.tier is not AuthorityTier.NEEDS_REVIEW
            ):
                raise ValueError(
                    "the sales-unit ceiling rule fires only for an "
                    "UNPROVEN unit on a NEEDS_REVIEW tier (restrict "
                    "only; never lifts, never fires elsewhere)"
                )

    @property
    def frozen_fired_rules(self) -> frozenset[AuthorityRuleV2]:
        """The FU3 audit trail projected onto the frozen rule vocabulary
        (the ceiling rule — which has no frozen counterpart — is
        excluded). When the ceiling did not fire this equals the frozen
        derivation's rule trail exactly."""
        return frozenset(
            AuthorityRuleV2(rule.value)
            for rule in self.fired_rules
            if rule is not AuthorityRuleV2FU3.CEILING_SALES_UNIT_NOT_PROVEN
        )


# ---------------------------------------------------------------------------
# The FU3 tier derivation: the frozen S2-A derivation + the restrict-only
# sales-unit ceiling (never more, never less)
# ---------------------------------------------------------------------------


def derive_authority_tier_fu3(
    assessment_v2: IdentityStateAssessmentV2,
    sales_unit_channel: CandidateSalesUnitEvidenceV2,
    evaluation: SemanticEvaluationV2 | None = None,
    context_provenances: frozenset[ContextProvenance] = frozenset(),
    product_evidence: ProductEvidenceProfileV2 | None = None,
    human_review: HumanReviewStateV2 | None = None,
    *,
    target_unit_evidence: TargetSalesUnitEvidenceV2 | None = None,
) -> AuthorityDecisionV2FU3:
    """Derive the bounded workflow authority tier under the S2-A-FU3
    contract (Q3-B4 Task B, Option D, derivation layer).

    The derivation is the FROZEN S2-A-FU2 derivation (byte-unchanged;
    called, never re-implemented) PLUS exactly one restrict-only step:

    1. The frozen derivation runs over the identical inputs (assessment,
       evaluation, provenances, product evidence, human overlay) and
       produces the old token's tier + rule trail.
    2. The two recorded facts are derived independently:
       ``identity_resolution_bound`` (from the deterministic state +
       reviewed provenances; no model input) and ``sales_unit_authority``
       (from the recorded channel + optional explicit target-side
       evidence; no model input).
    3. The restrict-only ceiling: when — and only when — the frozen
       result is ``AI_ASSISTED_COMPARABLE`` and the unit is UNPROVEN, the
       tier is capped at ``NEEDS_REVIEW`` and
       ``CEILING_SALES_UNIT_NOT_PROVEN`` is recorded. Interaction with
       the frozen ceilings is by the frozen "restrict only, never lift"
       order: a tier already capped (requirement ceiling, NM-2 ceiling,
       reviewable-conflict ceiling) is unchanged and gets no redundant
       rule; HARD_CONFLICT supersession stays last (it ran inside the
       frozen derivation); the human overlay precedence (HARD_CONFLICT >
       HUMAN_CONFIRMED > AI) is unchanged and applies above the AI path,
       exactly as with the NM-2 ceiling — a human may confirm a
       ceiling-capped candidate (explicit, auditable), and a generic
       semantic MATCH never infers unit confirmation.

    The ceiling NEVER lifts, NEVER touches MACHINE_VERIFIED (the
    deterministic path), and does NOT fire for CONTRADICTED units (the
    frozen absolute rule + HARD_CONFLICT supersession own that shape).

    ``TypeError`` / ``ValueError`` on foreign inputs (fail closed); the
    frozen derivation's own state-consistency failures propagate
    unchanged.
    """
    if not isinstance(assessment_v2, IdentityStateAssessmentV2):
        raise TypeError(
            "assessment_v2 must be IdentityStateAssessmentV2, "
            f"got {type(assessment_v2).__name__}"
        )
    if not isinstance(sales_unit_channel, CandidateSalesUnitEvidenceV2):
        raise TypeError(
            "sales_unit_channel must be CandidateSalesUnitEvidenceV2 (the "
            f"recorded sales-unit channel), got {type(sales_unit_channel).__name__}"
        )
    if target_unit_evidence is not None and not isinstance(
        target_unit_evidence, TargetSalesUnitEvidenceV2
    ):
        raise TypeError(
            "target_unit_evidence must be TargetSalesUnitEvidenceV2 or "
            f"None (the default single unit), got {type(target_unit_evidence).__name__}"
        )

    # 1. The frozen derivation, byte-unchanged (the old token's
    #    semantics; its failures — state-inconsistent profiles,
    #    unsupported provenances — propagate unchanged).
    frozen_decision = derive_authority_tier(
        assessment_v2,
        evaluation,
        context_provenances,
        product_evidence,
        human_review,
    )
    # 2. The independently derived recorded facts.
    bound = derive_identity_resolution_bound(
        assessment_v2, context_provenances
    )
    unit = sales_unit_authority_from_channel(
        sales_unit_channel, target_unit_evidence
    )
    # 3. The restrict-only ceiling (never lifts; automatic tier only).
    tier = frozen_decision.tier
    rules = frozenset(_to_fu3_rule(rule) for rule in frozen_decision.fired_rules)
    if (
        tier is AuthorityTier.AI_ASSISTED_COMPARABLE
        and unit is SalesUnitAuthorityV2.UNPROVEN
    ):
        tier = AuthorityTier.NEEDS_REVIEW
        rules = rules | frozenset(
            {AuthorityRuleV2FU3.CEILING_SALES_UNIT_NOT_PROVEN}
        )

    return AuthorityDecisionV2FU3(
        tier=tier,
        fired_rules=rules,
        product_evidence_quality=frozen_decision.product_evidence_quality,
        relationship_authority=frozen_decision.relationship_authority,
        identity_resolution_bound=bound,
        sales_unit_authority=unit,
    )


# ---------------------------------------------------------------------------
# Per-binding dispatch: the recorded authority token selects the
# derivation (Q3-B4 section 6.5). Unknown tokens fail closed.
# ---------------------------------------------------------------------------


def derive_authority_tier_for_contract(
    token: str,
    assessment_v2: IdentityStateAssessmentV2,
    evaluation: SemanticEvaluationV2 | None = None,
    context_provenances: frozenset[ContextProvenance] = frozenset(),
    product_evidence: ProductEvidenceProfileV2 | None = None,
    human_review: HumanReviewStateV2 | None = None,
    *,
    sales_unit_channel: CandidateSalesUnitEvidenceV2 | None = None,
    target_unit_evidence: TargetSalesUnitEvidenceV2 | None = None,
) -> AuthorityDecisionV2 | AuthorityDecisionV2FU3:
    """Replay-dispatch one authority derivation under the RECORDED
    authority contract token (S2-A-FU3, per-binding replay discipline).

    * ``SEMANTIC_AUTHORITY_V2_S2A_FU2`` (the frozen token) -> the
      UNCHANGED frozen derivation, returned as the frozen
      ``AuthorityDecisionV2``: historical V1 and Prompt 2.0 records
      replay identically under their original binding. The FU2 contract
      has NO sales-unit input: passing one under the old token is
      contract misuse and fails closed (the firewall can never be
      silently applied to old-binding records).
    * ``SEMANTIC_AUTHORITY_V2_S2A_FU3`` -> the FU3 derivation
      (``derive_authority_tier_fu3``): the frozen derivation plus the
      restrict-only ceiling and the two independently derived recorded
      facts. The recorded sales-unit channel is REQUIRED (the V2 input
      always carries one explicitly; omitting it is contract misuse and
      fails closed).
    * Anything else (unknown spelling, future token, whitespace variant,
      empty string) -> ``UnknownAuthorityContractTokenError``: a
      historical or future decision is never silently reinterpreted.
    * A non-string token -> ``TypeError``.
    """
    if not isinstance(token, str):
        raise TypeError(
            "token must be str (the recorded authority contract token), "
            f"got {type(token).__name__}"
        )
    if token == AUTHORITY_CONTRACT_VERSION_V2:
        if sales_unit_channel is not None or target_unit_evidence is not None:
            raise ValueError(
                "the frozen S2-A-FU2 contract has no sales-unit input; "
                "passing one under the old token is contract misuse (the "
                "FU3 firewall is isolated behind its own token)"
            )
        return derive_authority_tier(
            assessment_v2,
            evaluation,
            context_provenances,
            product_evidence,
            human_review,
        )
    if token == AUTHORITY_CONTRACT_VERSION_V2_FU3:
        if sales_unit_channel is None:
            raise ValueError(
                "the S2-A-FU3 contract requires the recorded sales-unit "
                "channel (the V2 input carries it explicitly); an absent "
                "channel is contract misuse and fails closed"
            )
        return derive_authority_tier_fu3(
            assessment_v2,
            sales_unit_channel,
            evaluation,
            context_provenances,
            product_evidence,
            human_review,
            target_unit_evidence=target_unit_evidence,
        )
    raise UnknownAuthorityContractTokenError(
        "unknown authority contract token; the derivation refuses to "
        "reinterpret a decision under a contract it does not know "
        "(fail closed — the known tokens are the frozen S2-A-FU2 token "
        "and the S2-A-FU3 token)"
    )


# ---------------------------------------------------------------------------
# Mechanical self-consistency of the FU3 contract data, verified once at
# import (pure data check, no mutable state). If a future edit breaks any
# of these contracts, the module refuses to import.
# ---------------------------------------------------------------------------

if (
    len(IDENTITY_RESOLUTION_BOUND_TABLE)
    != len(
        {
            (entry_substate, entry_signal)
            for entry_substate, entry_signal, _bound
            in IDENTITY_RESOLUTION_BOUND_TABLE
        }
    )
    or {
        (entry_substate, entry_signal)
        for entry_substate, entry_signal, _bound
        in IDENTITY_RESOLUTION_BOUND_TABLE
    }
    != {
        (entry_substate, entry_signal)
        for entry_substate, entry_signal, _requirement
        in SUBSTATE_RELATIONSHIP_REQUIREMENTS
    }
):
    raise RuntimeError(
        "IDENTITY_RESOLUTION_BOUND_TABLE must define exactly one base "
        "bound per (sub-state, primary signal) combination the frozen "
        "S2-A derivation permits (S2-A-FU3 completeness check)"
    )
if (
    {rule.value for rule in AuthorityRuleV2FU3}
    != {rule.value for rule in AuthorityRuleV2} | {"CEILING_SALES_UNIT_NOT_PROVEN"}
):
    raise RuntimeError(
        "the FU3 rule vocabulary must be exactly the frozen S2-A rule "
        "values plus CEILING_SALES_UNIT_NOT_PROVEN (S2-A-FU3)"
    )
if {form.value for form in TargetSalesUnitFormV2} != {
    kind.value for kind in SalesUnitKindV2
}:
    raise RuntimeError(
        "the target-side unit form vocabulary must mirror the candidate "
        "channel's sales-unit kinds exactly (S2-A-FU3)"
    )
if {state.value for state in SalesUnitAuthorityV2} != {
    "PROVEN_EQUIVALENT",
    "UNPROVEN",
    "CONTRADICTED",
}:
    raise RuntimeError(
        "the sales-unit authority vocabulary is bounded to exactly "
        "PROVEN_EQUIVALENT / UNPROVEN / CONTRADICTED (S2-A-FU3)"
    )
if AUTHORITY_CONTRACT_VERSION_V2_FU3 == AUTHORITY_CONTRACT_VERSION_V2:
    raise RuntimeError(
        "the FU3 token must be separately versioned from the frozen "
        "S2-A-FU2 token"
    )
if KNOWN_AUTHORITY_CONTRACT_TOKENS != frozenset(
    {AUTHORITY_CONTRACT_VERSION_V2, AUTHORITY_CONTRACT_VERSION_V2_FU3}
):
    raise RuntimeError(
        "the known authority contract tokens are exactly the frozen "
        "S2-A-FU2 token and the S2-A-FU3 token"
    )
for _global_name, _global_value in list(globals().items()):
    if _global_name.startswith("__"):
        continue
    if isinstance(_global_value, (dict, list, set)):
        raise RuntimeError(
            f"semantic_authority_fu3 global {_global_name} is a mutable "
            "container; frozen contract data must be runtime-immutable "
            "(S2-A-FU1 discipline, extended to S2-A-FU3)"
        )
