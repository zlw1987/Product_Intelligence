"""Semantic Authority Contract V2, S2-A-FU4 — separately versioned
bundle-composition authority (CONTRACT ONLY).

PRODUCT-INTEL.SEMANTIC-AUTHORITY-V2-Q3-B5-P4 (this module) implements the
approved Q3-B5-P3-FU1 bundle-composition authority design
(``docs/PRODUCT_INTEL_Q3B5_P3_BUNDLE_COMPOSITION_DESIGN.md`` — the
CORRECTED design: Blocker A quantity completeness, Blocker B composition
completeness) as an isolated, deterministic, versioned research contract.
It introduces the separately versioned authority contract token
``SEMANTIC_AUTHORITY_V2_S2A_FU4`` and, behind that token ONLY:

1. **The versioned bundle-composition evidence schema (v1)** — the
   five-way ``BundleCompositionStateV2FU4`` vocabulary
   (``SYNTACTICALLY_VALID`` / ``ESTABLISHED`` / ``PARTIAL`` / ``ABSENT`` /
   ``CONTRADICTED_PUBLISHED``), the candidate-side record
   (``CandidateBundleCompositionEvidenceV2FU4``, built ONLY from a
   verified schema-v1 extraction result or from a recorded OBSERVED
   BUNDLE channel — the two bounded bases), the target-side versioned
   record (``TargetSalesUnitEvidenceV2FU4``), the two attestation
   records (``CompositionCompletenessAttestationV2FU4`` — the exact
   evidence for ``ESTABLISHED``; ``QuantityCompletenessAttestationV2FU4``
   — the exact evidence lifting an asymmetric quantity gap), the versioned
   clause extraction + textual-closure classification + completeness-
   marker detection, and the versioned materiality grammar (textual
   agreement / material difference ONLY — never completeness, never
   quantity).
2. **The FU4 bundle rule (D6)** — ``PROVEN_EQUIVALENT`` for a bundle only
   when ALL hold: matching BUNDLE form; composition ``ESTABLISHED`` on
   BOTH sides (each side with its OWN verified completeness attestation);
   the clauses TEXTUALLY AGREE (byte-identical, or equal multisets under
   the versioned full-parse grammar — textual agreement only, never
   completeness); and the quantity axis SATISFIED (``CONSISTENT`` /
   ``BOTH_UNPUBLISHED`` / ``ATTESTED_NOT_MATERIAL`` — the asymmetric
   unattested gap is ``UNDETERMINED`` ⇒ UNPROVEN, never silently
   immaterial). A published incompatibility independently established on
   either axis (a count difference over textually-agreed clauses, or a
   materially established difference between two ``ESTABLISHED``
   clauses) ⇒ ``CONTRADICTED``; every other combination ⇒ ``UNPROVEN``.
   The quantity-axis state is a DETERMINED, RECORDED state in every
   bundle comparison — the determination is never silent (D20).
3. **``AuthorityDecisionV2FU4``** — the FU3 decision record's field set
   with the same construction invariants, PLUS the bounded bundle-axis
   audit fields (the quantity-axis state, the candidate / target
   composition states, the completeness-attestation digests, the
   quantity-attestation digest — exactly None for non-bundle channels).
   The frozen restrict-only ceilings (``CEILING_SALES_UNIT_NOT_PROVEN`` /
   ``CEILING_SALES_UNIT_CONTRADICTED``) apply unchanged; the FU4 rule
   vocabulary mirrors the FU3 set exactly.
4. **The FU4 superset dispatch** (``derive_authority_tier_for_contract_
   fu4``): the historical ``FU2`` / ``FU3`` bindings delegate to their
   UNCHANGED frozen derivations (byte-identical; composition /
   attestation inputs under either historical token are contract
   misuse); the ``FU4`` token runs the FU4 derivation (the recorded
   channel REQUIRED); unknown tokens fail closed
   (``UnknownAuthorityContractTokenError``, reused from the frozen FU3
   module).

What this module deliberately is NOT:

* **Not an amendment.** The frozen S2-A module (token
  ``SEMANTIC_AUTHORITY_V2_S2A_FU2``), the frozen FU3 module (token
  ``SEMANTIC_AUTHORITY_V2_S2A_FU3``), the frozen S2-C-FU1 channel
  (``CandidateSalesUnitEvidenceV2``), the extraction schema v1, and the
  Prompt 2.0 / 2.1 contracts are BYTE-FROZEN inputs.
* **Not a registration.** Nothing in the production codec, the replay
  registry, the corpus / harness registries, or the live record type
  knows the FU4 token: the contract phase registers nothing (the
  separately gated registration step is specified in the design's
  section 7.3, not executed here).
* **Not a wiring.** No live path references this module (the P2 AST-pin /
  FU3 lexical-guard discipline); ``V2_AUTHORITY_QUALIFIED`` stays False
  in both pinned locations; no V2 pricing consumer reads FU4 states.
* **Not a promotion.** PROVEN_EQUIVALENT under this token changes no
  consumer behavior until the separately gated wiring + guard +
  qualification all exist.

Pure research-layer contract: stdlib + the research package's public
surface + the frozen FU3 / FU2 / S2-C / extraction modules. No Django, no
I/O, no clock, no network, no LLM, no mutable global state, no vendor
names.
"""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass
from enum import Enum
from typing import Final

from product_intelligence.research import (
    AUTHORITY_CONTRACT_VERSION_V2,
    AuthorityRuleV2,
    AuthorityTier,
    ContextProvenance,
    HumanReviewStateV2,
    IdentityStateAssessmentV2,
    ProductEvidenceProfileV2,
    ProductEvidenceQuality,
    RelationshipAuthority,
    SemanticEvaluationV2,
    derive_authority_tier,
)
from product_intelligence.research.sales_unit_extraction import (
    SalesUnitCueDisposition,
    SalesUnitCueField,
    SalesUnitExtractionResult,
    SalesUnitExtractionState,
)
from product_intelligence.research.semantic_authority_fu3 import (
    AUTHORITY_CONTRACT_VERSION_V2_FU3,
    AuthorityRuleV2FU3,
    IdentityResolutionBoundV2,
    SalesUnitAuthorityV2,
    TargetSalesUnitEvidenceSourceV2,
    TargetSalesUnitEvidenceV2,
    TargetSalesUnitFormV2,
    UnknownAuthorityContractTokenError,
    derive_authority_tier_for_contract as _fu3_dispatch,
    derive_identity_resolution_bound,
    sales_unit_authority_from_channel as _fu3_unit_from_channel,
)
from product_intelligence.research.semantic_v2 import (
    CandidateEvidenceSourceV2,
    CandidateSalesUnitEvidenceV2,
    PackagingEvidenceStateV2,
    SalesUnitKindV2,
    SemanticMatchCaseV2,
)

__all__ = [
    "AUTHORITY_CONTRACT_VERSION_V2_FU4",
    "AuthorityDecisionV2FU4",
    "AuthorityRuleV2FU4",
    "BUNDLE_COMPOSITION_EVIDENCE_VERSION_FU4",
    "BundleCompositionEvidenceIntegrityError",
    "BundleCompositionStateV2FU4",
    "BundleQuantityAxisStateV2FU4",
    "CandidateBundleCompositionEvidenceV2FU4",
    "CandidateCompositionEvidenceBasisV2FU4",
    "CompletenessBasisV2FU4",
    "CompositionCompletenessAttestationV2FU4",
    "EvidenceSideV2FU4",
    "KNOWN_AUTHORITY_CONTRACT_TOKENS_FU4",
    "QuantityCompletenessAttestationV2FU4",
    "QuantityNonMaterialityReasonV2FU4",
    "TargetSalesUnitEvidenceV2FU4",
    "candidate_composition_from_channel",
    "candidate_composition_from_extraction",
    "classify_clause_closure",
    "derive_authority_tier_for_contract_fu4",
    "derive_authority_tier_fu4",
    "derive_sales_unit_authority_fu4",
    "derive_sales_unit_authority_fu4_case",
    "extract_published_bundle_clause",
    "is_known_authority_contract_token_fu4",
]


# ---------------------------------------------------------------------------
# The separately versioned authority contract token
# ---------------------------------------------------------------------------


AUTHORITY_CONTRACT_VERSION_V2_FU4: Final[str] = "SEMANTIC_AUTHORITY_V2_S2A_FU4"
"""The identity of the Semantic Authority Contract V2 AS AMENDED BY
S2-A-FU4 — the separately versioned bundle-composition authority (the
corrected Q3-B5-P3 design: Blocker A quantity completeness + Blocker B
composition completeness). Records bound to this token derive through
``derive_authority_tier_fu4``. No production record is bound to this
token: the contract phase registers NOTHING (the production codec, the
replay registry, the corpus / harness registries, and the live record
type all still know only the historical bindings — the separately gated
registration step of the design's section 7.3 is not this module)."""


#: The authority contract tokens this module can derive under: exactly the
#: three historical + new tokens (the FU4 superset dispatch, design T8).
#: Both historical tokens delegate to their UNCHANGED frozen derivations.
KNOWN_AUTHORITY_CONTRACT_TOKENS_FU4: Final[frozenset[str]] = frozenset(
    {
        AUTHORITY_CONTRACT_VERSION_V2,
        AUTHORITY_CONTRACT_VERSION_V2_FU3,
        AUTHORITY_CONTRACT_VERSION_V2_FU4,
    }
)


def is_known_authority_contract_token_fu4(token: object) -> bool:
    """True only for an exact string match of a known authority contract
    token in the FU4 superset (FU2 / FU3 / FU4). Fails closed with
    ``TypeError`` on a non-string input."""
    if not isinstance(token, str):
        raise TypeError(
            "token must be str, got "
            f"{type(token).__name__ if token is not None else 'None'}"
        )
    return token in KNOWN_AUTHORITY_CONTRACT_TOKENS_FU4


# ---------------------------------------------------------------------------
# The versioned bundle-composition evidence schema (v1)
# ---------------------------------------------------------------------------


BUNDLE_COMPOSITION_EVIDENCE_VERSION_FU4: Final[int] = 1
"""The version of the FU4 bundle-composition evidence schema: it covers
the clause extraction grammar, the textual-closure classification, the
incompleteness-marker list, the completeness-marker list + the bounded
marker-delimiter set, the materiality grammar, the state / basis / side /
axis vocabularies, and the two attestation record shapes. Any change is a
NEW version (or a new authority token) — never a silent edit (design T5 /
T9)."""


class BundleCompositionEvidenceIntegrityError(ValueError):
    """A presented bundle-composition evidence record or attestation
    record fails its own integrity checks (a tampered digest, a forged
    basis / subject-side / source-class, an attestation bound to a
    different clause). Fail closed: the record produces no derivation
    input (no unit is derived from it)."""


class BundleCompositionStateV2FU4(str, Enum):
    """The bounded publication states of a bundle's composition
    (S2-A-FU4; the CORRECTED five-way vocabulary — Blocker B).

    Syntactic validity is a TEXTUAL property only; commercial
    completeness is an ATTESTED property (a separate axis). The two are
    never conflated: a closed, marker-free clause is
    ``SYNTACTICALLY_VALID`` and its completeness is UNKNOWN — it can
    never by itself contribute to PROVEN_EQUIVALENT (D19).
    """

    SYNTACTICALLY_VALID = "SYNTACTICALLY_VALID"
    """A non-empty, closed, verbatim published contents clause with no
    explicit incompleteness marker (the textual-closure grammar of
    design section 3.5a). A TEXTUAL property only: the statement is a
    complete published sentence, not necessarily a complete ENUMERATION
    of what the bundle contains — the commercial completeness of the
    composition is UNKNOWN. This state can never by itself contribute to
    PROVEN_EQUIVALENT, on either side (D19; the U15 row). (This is what
    the pre-correction design's ``ESTABLISHED`` denoted.)"""

    ESTABLISHED = "ESTABLISHED"
    """``SYNTACTICALLY_VALID`` PLUS a bounded, independently supported
    completeness attestation
    (``CompositionCompletenessAttestationV2FU4``) establishing that the
    published clause is the bundle's COMPLETE commercial composition —
    the subject's own published explicit completeness statement (the
    versioned marker, detected deterministically from the recorded text)
    or, target-side only, a recorded review composition attestation.
    Only this state may enter the PROVEN conjunction (D6). The
    attestation is trusted as recorded (the T3 / T3' epistemic boundary);
    physical truth remains the publisher's claim or the reviewer's
    determination."""

    PARTIAL = "PARTIAL"
    """Partially enumerated contents: the publication is explicitly
    incomplete or not closed — an incompleteness marker inside the
    clause, an unclosed paren form, or a dangling trailing separator /
    incomplete quantity token. The clause text is recorded for audit; it
    can never contribute to SYNTACTICALLY_VALID, ESTABLISHED, or
    PROVEN_EQUIVALENT, and a completeness marker can never rescue it
    (D5)."""

    ABSENT = "ABSENT"
    """No contents clause is published: a bare bundle word, a count-only
    bundle phrase (``bundle of N`` / ``N-unit bundle``), or an empty
    marker clause (``bundle:`` / ``bundle ()``). The count, when
    published, stays verbatim in the source text and is never bound to a
    quantity (the P2-FU1 rule, preserved; D17)."""

    CONTRADICTED_PUBLISHED = "CONTRADICTED_PUBLISHED"
    """Candidate-side ONLY: two or more published contents clauses
    (across the examined fields, e.g. title vs structured field) that
    differ textually (byte comparison over the clause form). EVERY clause
    is recorded with its full provenance AND its own textual state (and
    its own published attestation, if the marker was present); NONE is
    adopted. The derivation returns UNPROVEN for every target shape (D8)
    — a self-contradiction is not a contradiction against the target,
    and neither side may be presented as THE composition."""


class CandidateCompositionEvidenceBasisV2FU4(str, Enum):
    """The bounded bases a candidate-side composition record may rest on
    (S2-A-FU4, D3)."""

    EXTRACTION_RESULT_V1 = "EXTRACTION_RESULT_V1"
    """Built from a verified sales-unit-extraction schema-v1 result (the
    result's FULL cue list is read; the record is digest-bound to it).
    Detects CONTRADICTED_PUBLISHED (D3 / D8)."""

    RECORDED_CHANNEL = "RECORDED_CHANNEL"
    """Built from a recorded OBSERVED BUNDLE channel alone (corpus-shaped
    / supplied channels; the single-clause view, design T6)."""


class EvidenceSideV2FU4(str, Enum):
    """The two bounded sides of a bundle comparison (S2-A-FU4): the
    attestation's SUBJECT — the side whose publication the attestation
    speaks about."""

    CANDIDATE = "CANDIDATE"
    TARGET = "TARGET"


class CompletenessBasisV2FU4(str, Enum):
    """The bounded bases a composition-completeness attestation may rest
    on (S2-A-FU4, D19). No other evidence — syntactic closure,
    byte-identity, multiset equality, same-page repetition, a model
    output, an MPN, a price, an absence — establishes completeness."""

    PUBLISHED_COMPLETENESS_STATEMENT = "PUBLISHED_COMPLETENESS_STATEMENT"
    """The subject side's OWN recorded publication contains an explicit
    bounded completeness statement tied to the clause: detected
    deterministically from recorded text by the versioned marker list
    (the verbatim marker segment IS the recorded attestation text), or,
    target-side, recorded by the review as the statement the target's
    own source published. Candidate- or target-side (each side's own
    source)."""

    REVIEWED_COMPOSITION_ATTESTATION = "REVIEWED_COMPOSITION_ATTESTATION"
    """A recorded review determination that the subject's published
    clause is the bundle's complete commercial composition (TARGET-SIDE
    ONLY — the review process is the contract's attestation authority
    for the target side; the attestation text records the review's
    anchor, e.g. the manufacturer-published bundle specification the
    clause was verified against). The derivation trusts the record as
    reviewed (the T3 / T3' epistemic boundary); a copied, unverified
    attestation is a review-governance failure — the record must not
    have been created — not a contract state."""


class QuantityNonMaterialityReasonV2FU4(str, Enum):
    """The bounded reasons a review may record for the non-materiality of
    a MISSING bundle quantity (S2-A-FU4, D20). These are the only
    behavior-driving content of a quantity attestation; the recorded
    determination text is the audit anchor (AUDIT-ONLY, never read by
    the derivation)."""

    SUBJECT_SOURCE_STRUCTURALLY_WITHOUT_BUNDLE_COUNTS = (
        "SUBJECT_SOURCE_STRUCTURALLY_WITHOUT_BUNDLE_COUNTS"
    )
    """The subject side's source structurally publishes no bundle
    quantities for this offer shape; the published composition clause is
    the source's complete statement of the commercial unit, so the
    missing quantity is not a material difference between the two
    publications (the review's recorded determination)."""

    PUBLISHED_COUNT_NOT_UNIT_MULTIPLICITY = "PUBLISHED_COUNT_NOT_UNIT_MULTIPLICITY"
    """The OTHER side's published count does not denote the commercial
    unit's multiplicity (the review's recorded determination, e.g. a
    promotional multi-set count), so the subject side's silence on it is
    not a material unit difference."""


class BundleQuantityAxisStateV2FU4(str, Enum):
    """The DETERMINED quantity-axis outcome of a bundle comparison
    (S2-A-FU4, D20: the determination is never silent — recorded on the
    decision's audit surface in every bundle comparison)."""

    CONSISTENT = "CONSISTENT"
    """Both sides publish a count; the counts are equal. SATISFIED."""

    BOTH_UNPUBLISHED = "BOTH_UNPUBLISHED"
    """Neither side publishes a count. SATISFIED — a determined,
    recorded state (no published quantity exists on either side for the
    other side's silence to mask), NOT a silence."""

    ATTESTED_NOT_MATERIAL = "ATTESTED_NOT_MATERIAL"
    """Exactly one side publishes; a verified
    ``QuantityCompletenessAttestationV2FU4`` stands on the missing side.
    SATISFIED (D20)."""

    CONTRADICTED = "CONTRADICTED"
    """Both sides publish; the counts differ. The quantity axis
    independently establishes published incompatibility (unit
    CONTRADICTED — the U16 row)."""

    UNDETERMINED = "UNDETERMINED"
    """Exactly one side publishes; no verified attestation stands on the
    missing side. Blocks PROVEN (unit UNPROVEN — the U18 row) unless
    another axis independently establishes a contradiction (U17)."""


#: The frozen candidate-side non-model provenance classes (the two
#: extractor members of the frozen S2-C-FU1 vocabulary — a cue from any
#: other provenance is un-constructible; no member is a model claim).
_CANDIDATE_NON_MODEL_SOURCES: Final[tuple[CandidateEvidenceSourceV2, ...]] = (
    CandidateEvidenceSourceV2.LISTING_TITLE,
    CandidateEvidenceSourceV2.PUBLISHED_STRUCTURED_FIELD,
)


# ---------------------------------------------------------------------------
# The attestation records (design section 3.8 — Blocker A / B)
# ---------------------------------------------------------------------------


def _is_hex_digest(value: object) -> bool:
    return (
        isinstance(value, str)
        and len(value) == 64
        and all(ch in "0123456789abcdef" for ch in value)
    )


def _canonical_digest(document: dict[str, object]) -> str:
    """SHA-256 over the canonical (sorted-keys, compact, ASCII) document
    (the P2 result / FU2 record discipline)."""
    encoded = json.dumps(
        document, sort_keys=True, separators=(",", ":"), ensure_ascii=True
    )
    return hashlib.sha256(encoded.encode("ascii")).hexdigest()


def _clause_digest(clause: str) -> str:
    """SHA-256 of the attested clause (the clause form, original case /
    spacing, UTF-8 bytes)."""
    return hashlib.sha256(clause.encode("utf-8")).hexdigest()


@dataclass(frozen=True)
class CompositionCompletenessAttestationV2FU4:
    """The recorded, bounded, independently supported evidence that a
    published bundle composition clause is the bundle's COMPLETE
    commercial composition (S2-A-FU4, D19 — the exact evidence for the
    ``ESTABLISHED`` state).

    The ``source`` is the SUBJECT SIDE's frozen non-model class: a
    CANDIDATE subject carries exactly ``LISTING_TITLE`` /
    ``PUBLISHED_STRUCTURED_FIELD``; a TARGET subject carries exactly
    ``REVIEWED_TARGET_CONTEXT`` / ``REQUEST_DESCRIPTION``. A
    basis/source-class mismatch is un-constructible; a candidate-side
    record with basis ``REVIEWED_COMPOSITION_ATTESTATION`` is
    un-constructible (a review attests the target side, not the
    candidate listing's own completeness). ``clause_digest`` binds the
    attestation to the EXACT clause. ``attestation_text`` is the verbatim
    recorded statement / determination — AUDIT-ONLY: it is never read by
    the derivation (design F4). Neither attestation is ever produced by
    the derivation or by a fuzzy / similarity computation: the
    completeness attestation is machine-constructed ONLY from the
    recorded marker detection (deterministic, bounded, over recorded
    text) or review-constructed (target side).

    The record is review- or marker-constructed only — the validated
    constructor is the sole creation path.
    """

    schema_version: int
    subject_side: EvidenceSideV2FU4
    basis: CompletenessBasisV2FU4
    source: CandidateEvidenceSourceV2 | TargetSalesUnitEvidenceSourceV2
    clause_digest: str
    attestation_text: str
    attestation_digest: str

    def __post_init__(self) -> None:
        if type(self.schema_version) is not int or (
            self.schema_version != BUNDLE_COMPOSITION_EVIDENCE_VERSION_FU4
        ):
            raise ValueError(
                "schema_version must be "
                f"{BUNDLE_COMPOSITION_EVIDENCE_VERSION_FU4}, got "
                f"{self.schema_version!r} (an unknown evidence version is "
                "never silently reinterpreted)"
            )
        if not isinstance(self.subject_side, EvidenceSideV2FU4):
            raise TypeError(
                "subject_side must be EvidenceSideV2FU4, "
                f"got {type(self.subject_side).__name__}"
            )
        if not isinstance(self.basis, CompletenessBasisV2FU4):
            raise TypeError(
                "basis must be CompletenessBasisV2FU4, "
                f"got {type(self.basis).__name__}"
            )
        # The subject side's frozen non-model class (basis/source-class
        # coherence; a basis/source-class mismatch is un-constructible).
        if self.subject_side is EvidenceSideV2FU4.CANDIDATE:
            if (
                not isinstance(self.source, CandidateEvidenceSourceV2)
                or self.source not in _CANDIDATE_NON_MODEL_SOURCES
            ):
                raise ValueError(
                    "a CANDIDATE-subject completeness attestation carries "
                    "exactly the frozen candidate non-model classes "
                    "(LISTING_TITLE / PUBLISHED_STRUCTURED_FIELD); no "
                    "member is a model claim, and a target-side class "
                    "cannot attest a candidate publication"
                )
        else:
            if not isinstance(self.source, TargetSalesUnitEvidenceSourceV2):
                raise ValueError(
                    "a TARGET-subject completeness attestation carries "
                    "exactly the frozen target classes "
                    "(REVIEWED_TARGET_CONTEXT / REQUEST_DESCRIPTION); a "
                    "candidate-side class cannot attest a target "
                    "publication"
                )
        if (
            self.basis is CompletenessBasisV2FU4.REVIEWED_COMPOSITION_ATTESTATION
            and self.subject_side is EvidenceSideV2FU4.CANDIDATE
        ):
            raise ValueError(
                "a candidate-side record with basis "
                "REVIEWED_COMPOSITION_ATTESTATION is un-constructible (a "
                "review attests the target side, not the candidate "
                "listing's own completeness)"
            )
        if not _is_hex_digest(self.clause_digest):
            raise ValueError("clause_digest must be a 64-character hex digest")
        if not isinstance(self.attestation_text, str) or not self.attestation_text:
            raise ValueError(
                "attestation_text must be the non-empty verbatim recorded "
                "statement / determination (AUDIT-ONLY)"
            )
        if not _is_hex_digest(self.attestation_digest):
            raise ValueError(
                "attestation_digest must be a 64-character hex digest"
            )
        if _canonical_digest(self.canonical()) != self.attestation_digest:
            raise BundleCompositionEvidenceIntegrityError(
                "attestation_digest does not verify against the "
                "attestation content (the attestation was tampered with "
                "or forged)"
            )

    def canonical(self) -> dict[str, object]:
        """The canonical (sorted-keys) document of the attestation minus
        its own digest."""
        return {
            "schema_version": self.schema_version,
            "subject_side": self.subject_side.value,
            "basis": self.basis.value,
            "source": self.source.value,
            "clause_digest": self.clause_digest,
            "attestation_text": self.attestation_text,
        }

    def verify(self) -> None:
        """Re-verify the self-consistency of a PRESENTED attestation
        (digest self-verification — the anti-forgery gate before any
        axis uses it). Raises
        ``BundleCompositionEvidenceIntegrityError`` on any mismatch."""
        if _canonical_digest(self.canonical()) != self.attestation_digest:
            raise BundleCompositionEvidenceIntegrityError(
                "attestation_digest does not verify against the "
                "attestation content (the attestation was tampered with "
                "or forged)"
            )


@dataclass(frozen=True)
class QuantityCompletenessAttestationV2FU4:
    """The recorded, bounded, REVIEW-CONSTRUCTED evidence that a MISSING
    bundle quantity is not a material difference between the two
    publications (S2-A-FU4, D20 — the exact evidence lifting the
    asymmetric quantity gap to ``ATTESTED_NOT_MATERIAL``).

    The ``subject_side`` is the side where the quantity is MISSING (the
    derivation enforces the match: an attestation whose subject is not
    the actually-missing side is an integrity error). The ``source`` is
    exactly one of the two frozen non-model attestation classes — the
    review process is the contract's SOLE quantity-attestation authority
    for EITHER subject side (a page never self-attests the
    non-materiality of its own silence; the candidate-side gap is
    attested by the review record with ``subject_side = CANDIDATE``,
    design T10). ``attestation_text`` is the verbatim recorded
    determination — AUDIT-ONLY: never read by the derivation. The
    attestation never supplies a quantity VALUE (there is no value
    field — a reviewed value enters through the record's quantity field,
    the frozen mechanism).

    Review-constructed ONLY: there is no machine path (non-materiality
    is a determination, not a text pattern).
    """

    schema_version: int
    subject_side: EvidenceSideV2FU4
    reason: QuantityNonMaterialityReasonV2FU4
    source: TargetSalesUnitEvidenceSourceV2
    attestation_text: str
    attestation_digest: str

    def __post_init__(self) -> None:
        if type(self.schema_version) is not int or (
            self.schema_version != BUNDLE_COMPOSITION_EVIDENCE_VERSION_FU4
        ):
            raise ValueError(
                "schema_version must be "
                f"{BUNDLE_COMPOSITION_EVIDENCE_VERSION_FU4}, got "
                f"{self.schema_version!r} (an unknown evidence version is "
                "never silently reinterpreted)"
            )
        if not isinstance(self.subject_side, EvidenceSideV2FU4):
            raise TypeError(
                "subject_side must be EvidenceSideV2FU4, "
                f"got {type(self.subject_side).__name__}"
            )
        if not isinstance(self.reason, QuantityNonMaterialityReasonV2FU4):
            raise TypeError(
                "reason must be QuantityNonMaterialityReasonV2FU4, "
                f"got {type(self.reason).__name__}"
            )
        if not isinstance(self.source, TargetSalesUnitEvidenceSourceV2):
            raise ValueError(
                "a quantity attestation carries exactly the two frozen "
                "non-model attestation classes (REVIEWED_TARGET_CONTEXT / "
                "REQUEST_DESCRIPTION) — the review process is the "
                "contract's sole quantity-attestation authority; a page "
                "never self-attests the non-materiality of its own "
                "silence"
            )
        if not isinstance(self.attestation_text, str) or not self.attestation_text:
            raise ValueError(
                "attestation_text must be the non-empty verbatim recorded "
                "determination (AUDIT-ONLY)"
            )
        if not _is_hex_digest(self.attestation_digest):
            raise ValueError(
                "attestation_digest must be a 64-character hex digest"
            )
        if _canonical_digest(self.canonical()) != self.attestation_digest:
            raise BundleCompositionEvidenceIntegrityError(
                "attestation_digest does not verify against the "
                "attestation content (the attestation was tampered with "
                "or forged)"
            )

    def canonical(self) -> dict[str, object]:
        """The canonical (sorted-keys) document of the attestation minus
        its own digest."""
        return {
            "schema_version": self.schema_version,
            "subject_side": self.subject_side.value,
            "reason": self.reason.value,
            "source": self.source.value,
            "attestation_text": self.attestation_text,
        }

    def verify(self) -> None:
        """Re-verify the self-consistency of a PRESENTED attestation
        (digest self-verification — the anti-forgery gate before any
        axis uses it). Raises
        ``BundleCompositionEvidenceIntegrityError`` on any mismatch."""
        if _canonical_digest(self.canonical()) != self.attestation_digest:
            raise BundleCompositionEvidenceIntegrityError(
                "attestation_digest does not verify against the "
                "attestation content (the attestation was tampered with "
                "or forged)"
            )


# ---------------------------------------------------------------------------
# The candidate-side composition evidence record (design section 3.2)
# ---------------------------------------------------------------------------


def _clause_is_textually_valid(clause: str) -> bool:
    """The deterministic clause-level slice of the textual-closure
    classification (design section 3.5a) over a clause whose paren-form
    closure fact is not in evidence (the record constructors see only the
    clause text): non-empty, no explicit incompleteness marker, not
    ending on a dangling separator or an incomplete quantity token."""
    if not isinstance(clause, str) or not clause.strip():
        return False
    if _clause_has_incomplete_marker(clause):
        return False
    if _clause_ends_dangling(clause):
        return False
    return True


@dataclass(frozen=True)
class CandidateBundleCompositionEvidenceV2FU4:
    """The bounded candidate-side bundle-composition evidence record
    (S2-A-FU4, schema v1).

    Every composition fact is (a) a verbatim published text span with
    span-bound provenance (the frozen extractor's recorded cues, or the
    frozen recorded channel) or (b) a versioned completeness attestation
    constructed ONLY from the recorded marker detection — no member of
    the provenance vocabulary is a model claim; no LLM output enters.

    The constructor is the validator (fail closed, the P2
    result-constructor pattern): the schema version is bounded; the
    state/coherence matrix is exact (ABSENT carries no clause / no
    attestation / no additional clauses; SYNTACTICALLY_VALID and PARTIAL
    carry exactly one clause and NO attestation; ESTABLISHED carries
    exactly one textually valid clause with its coherent verified
    attestation (subject CANDIDATE, basis PUBLISHED_COMPLETENESS_
    STATEMENT, source = the record's source, clause_digest over exactly
    the record's clause); CONTRADICTED_PUBLISHED carries the primary
    clause + the non-empty set of other published clause forms, every
    clause differing from every other); SYNTACTICALLY_VALID /
    ESTABLISHED clauses must pass the textual-closure checks (D5 at the
    type level); the basis / extraction-digest coherence is exact; the
    source is one of the two frozen candidate non-model members; and
    ``evidence_digest`` re-verifies at construction and on every
    presentation (a tampered record — including a tampered embedded
    attestation — produces no derivation input:
    ``BundleCompositionEvidenceIntegrityError``).
    """

    schema_version: int
    basis: CandidateCompositionEvidenceBasisV2FU4
    state: BundleCompositionStateV2FU4
    completeness_attestation: CompositionCompletenessAttestationV2FU4 | None
    composition_clause: str | None
    additional_clauses: tuple[str, ...]
    source: CandidateEvidenceSourceV2
    channel_quantity: int | None
    extraction_result_digest: str | None
    extraction_input_digest: str | None
    evidence_digest: str

    def __post_init__(self) -> None:
        if type(self.schema_version) is not int or (
            self.schema_version != BUNDLE_COMPOSITION_EVIDENCE_VERSION_FU4
        ):
            raise ValueError(
                "schema_version must be "
                f"{BUNDLE_COMPOSITION_EVIDENCE_VERSION_FU4}, got "
                f"{self.schema_version!r} (an unknown evidence version is "
                "never silently reinterpreted)"
            )
        if not isinstance(self.basis, CandidateCompositionEvidenceBasisV2FU4):
            raise TypeError(
                "basis must be CandidateCompositionEvidenceBasisV2FU4, "
                f"got {type(self.basis).__name__}"
            )
        if not isinstance(self.state, BundleCompositionStateV2FU4):
            raise TypeError(
                "state must be BundleCompositionStateV2FU4, "
                f"got {type(self.state).__name__}"
            )
        if (
            not isinstance(self.source, CandidateEvidenceSourceV2)
            or self.source not in _CANDIDATE_NON_MODEL_SOURCES
        ):
            raise ValueError(
                "the candidate-side composition record carries exactly the "
                "two frozen candidate non-model provenance members "
                "(LISTING_TITLE / PUBLISHED_STRUCTURED_FIELD); no member "
                "is a model claim, and any other value is un-constructible"
            )
        if not isinstance(self.additional_clauses, tuple):
            raise TypeError("additional_clauses must be a tuple (immutable)")
        for clause in self.additional_clauses:
            if not isinstance(clause, str):
                raise TypeError(
                    "additional_clauses must contain only verbatim str "
                    "clauses"
                )
        if self.composition_clause is not None and not isinstance(
            self.composition_clause, str
        ):
            raise TypeError("composition_clause must be str or None")
        if self.channel_quantity is not None:
            if type(self.channel_quantity) is not int or self.channel_quantity < 1:
                raise ValueError(
                    "channel_quantity must be the frozen channel's published "
                    f"bundle quantity (a positive int or None; never "
                    f"inferred), got {self.channel_quantity!r}"
                )
        for name in ("extraction_result_digest", "extraction_input_digest"):
            value = getattr(self, name)
            if value is not None and not _is_hex_digest(value):
                raise ValueError(f"{name} must be a 64-character hex digest")
        if self.basis is CandidateCompositionEvidenceBasisV2FU4.EXTRACTION_RESULT_V1:
            if (
                self.extraction_result_digest is None
                or self.extraction_input_digest is None
            ):
                raise ValueError(
                    "an EXTRACTION_RESULT_V1 record carries both extraction "
                    "digests (the verified result_digest + the input_digest "
                    "audit anchors)"
                )
        else:  # RECORDED_CHANNEL
            if (
                self.extraction_result_digest is not None
                or self.extraction_input_digest is not None
            ):
                raise ValueError(
                    "a RECORDED_CHANNEL record carries no extraction digests "
                    "(it is built from the recorded channel alone)"
                )
        if self.completeness_attestation is not None and not isinstance(
            self.completeness_attestation, CompositionCompletenessAttestationV2FU4
        ):
            raise TypeError(
                "completeness_attestation must be "
                "CompositionCompletenessAttestationV2FU4 or None, got "
                f"{type(self.completeness_attestation).__name__}"
            )

        # The state/coherence matrix (design section 3.2, CORRECTED).
        if self.state is BundleCompositionStateV2FU4.ABSENT:
            if (
                self.composition_clause is not None
                or self.completeness_attestation is not None
                or self.additional_clauses != ()
            ):
                raise ValueError(
                    "an ABSENT composition record carries no clause, no "
                    "attestation, and no additional clauses"
                )
        elif self.state in (
            BundleCompositionStateV2FU4.SYNTACTICALLY_VALID,
            BundleCompositionStateV2FU4.PARTIAL,
        ):
            if (
                self.composition_clause is None
                or self.completeness_attestation is not None
                or self.additional_clauses != ()
            ):
                raise ValueError(
                    "a SYNTACTICALLY_VALID / PARTIAL composition record "
                    "carries exactly one clause, NO completeness "
                    "attestation (a SYNTACTICALLY_VALID clause is "
                    "completeness-unknown — the attested and unattested "
                    "shapes are type-distinguishable, never conflated), "
                    "and no additional clauses"
                )
            if self.state is BundleCompositionStateV2FU4.SYNTACTICALLY_VALID and not _clause_is_textually_valid(
                self.composition_clause
            ):
                raise ValueError(
                    "a SYNTACTICALLY_VALID clause must pass the textual "
                    "closure checks (an empty / truncated / incomplete "
                    "clause is un-constructible as SYNTACTICALLY_VALID "
                    "— D5 at the type level)"
                )
        elif self.state is BundleCompositionStateV2FU4.ESTABLISHED:
            if (
                self.composition_clause is None
                or self.additional_clauses != ()
            ):
                raise ValueError(
                    "an ESTABLISHED composition record carries exactly one "
                    "clause and no additional clauses"
                )
            if not _clause_is_textually_valid(self.composition_clause):
                raise ValueError(
                    "an ESTABLISHED clause must be textually valid (an "
                    "empty / truncated / incomplete clause is "
                    "un-constructible as ESTABLISHED — D5 at the type "
                    "level; a completeness marker can never rescue an "
                    "unclosed clause)"
                )
            att = self.completeness_attestation
            if att is None:
                raise ValueError(
                    "an ESTABLISHED composition requires its verified "
                    "completeness attestation (D19: only a bounded, "
                    "independently supported attestation establishes "
                    "completeness — syntactic closure never does)"
                )
            if att.subject_side is not EvidenceSideV2FU4.CANDIDATE:
                raise ValueError(
                    "the candidate-side record's embedded attestation "
                    "subjects the CANDIDATE side"
                )
            if att.basis is not (
                CompletenessBasisV2FU4.PUBLISHED_COMPLETENESS_STATEMENT
            ):
                raise ValueError(
                    "a candidate-side ESTABLISHED record carries only the "
                    "PUBLISHED_COMPLETENESS_STATEMENT basis (a candidate-"
                    "side record cannot carry a review basis — a review "
                    "attests the target side, not the candidate listing's "
                    "own completeness)"
                )
            if att.source is not self.source:
                raise ValueError(
                    "the candidate-side record's embedded attestation "
                    "carries the record's recorded source (the clause's "
                    "recorded provenance)"
                )
            if att.clause_digest != _clause_digest(self.composition_clause):
                raise BundleCompositionEvidenceIntegrityError(
                    "the candidate-side record's embedded attestation is "
                    "bound to a different clause (clause_digest mismatch)"
                )
            att.verify()
        else:  # CONTRADICTED_PUBLISHED
            if (
                self.completeness_attestation is not None
                or not self.additional_clauses
            ):
                raise ValueError(
                    "a CONTRADICTED_PUBLISHED record carries no single "
                    "adopted attestation (NONE of the published clauses is "
                    "adopted) and a non-empty set of other published "
                    "clauses"
                )
            clauses = [self.composition_clause] if self.composition_clause is not None else []
            clauses.extend(self.additional_clauses)
            if len(clauses) < 2:
                raise ValueError(
                    "a CONTRADICTED_PUBLISHED record requires two or more "
                    "published clauses that differ textually (record the "
                    "primary clause and the other published clause forms)"
                )
            for i in range(len(clauses)):
                for j in range(i + 1, len(clauses)):
                    if clauses[i] == clauses[j]:
                        raise ValueError(
                            "a CONTRADICTED_PUBLISHED record's clauses must "
                            "differ from every other (byte comparison over "
                            "the clause form); identical repeated clauses "
                            "are ONE clause (consistency is textual "
                            "agreement with itself, never completeness)"
                        )
        if not _is_hex_digest(self.evidence_digest):
            raise ValueError("evidence_digest must be a 64-character hex digest")
        if _canonical_digest(self.canonical()) != self.evidence_digest:
            raise BundleCompositionEvidenceIntegrityError(
                "evidence_digest does not verify against the record "
                "content (the record was tampered with or forged)"
            )

    def canonical(self) -> dict[str, object]:
        """The canonical (sorted-keys) document of the record minus its
        own digest (the embedded attestation's canonical document — WITH
        its own verified digest — is part of the record's digest)."""
        return {
            "schema_version": self.schema_version,
            "basis": self.basis.value,
            "state": self.state.value,
            "completeness_attestation": (
                self.completeness_attestation.canonical()
                if self.completeness_attestation is not None
                else None
            ),
            "composition_clause": self.composition_clause,
            "additional_clauses": list(self.additional_clauses),
            "source": self.source.value,
            "channel_quantity": self.channel_quantity,
            "extraction_result_digest": self.extraction_result_digest,
            "extraction_input_digest": self.extraction_input_digest,
        }

    def verify(self) -> None:
        """Re-verify a PRESENTED record (the anti-forgery gate before any
        derivation input): the ``evidence_digest`` over the full record
        (the embedded attestation within) plus the embedded attestation's
        own digest. Raises
        ``BundleCompositionEvidenceIntegrityError`` on any mismatch."""
        if _canonical_digest(self.canonical()) != self.evidence_digest:
            raise BundleCompositionEvidenceIntegrityError(
                "evidence_digest does not verify against the record "
                "content (the record was tampered with or forged)"
            )
        if self.completeness_attestation is not None:
            self.completeness_attestation.verify()


# ---------------------------------------------------------------------------
# The target-side composition evidence record (design section 3.3)
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class TargetSalesUnitEvidenceV2FU4:
    """The versioned successor of the frozen FU3 target-side record
    (S2-A-FU4): the same form / quantity / source fields with the same
    constructor rules (mirrored from the frozen record), plus the bounded
    composition fields for the BUNDLE form.

    ``composition_clause`` is the verbatim published contents clause of
    the requested part's bundle, exactly as published in the source the
    review attests; ``composition_state`` is the bounded classification
    of that clause (the same closure grammar as the candidate side; the
    target side has no CONTRADICTED_PUBLISHED — one reviewed attestation
    is one record, design T7); ``completeness_attestation`` is present
    EXACTLY when the state is ESTABLISHED (subject TARGET; basis
    PUBLISHED_COMPLETENESS_STATEMENT — the target's own source published
    the statement, the review records it — or REVIEWED_COMPOSITION_
    ATTESTATION — the review's determination over the clause).
    Non-BUNDLE forms carry exactly (None, None, None): composition is a
    bundle-only fact. The record is REVIEW-CONSTRUCTED only — the
    validated constructor is the sole creation path (there is no machine
    derivation of a target-side record).
    """

    schema_version: int
    form: TargetSalesUnitFormV2
    quantity: int | None
    source: TargetSalesUnitEvidenceSourceV2
    composition_clause: str | None
    composition_state: BundleCompositionStateV2FU4 | None
    completeness_attestation: CompositionCompletenessAttestationV2FU4 | None
    evidence_digest: str

    def __post_init__(self) -> None:
        # The frozen FU3 rules verbatim.
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
        if type(self.schema_version) is not int or (
            self.schema_version != BUNDLE_COMPOSITION_EVIDENCE_VERSION_FU4
        ):
            raise ValueError(
                "schema_version must be "
                f"{BUNDLE_COMPOSITION_EVIDENCE_VERSION_FU4}, got "
                f"{self.schema_version!r} (an unknown evidence version is "
                "never silently reinterpreted)"
            )
        if self.composition_clause is not None and not isinstance(
            self.composition_clause, str
        ):
            raise TypeError("composition_clause must be str or None")
        if self.completeness_attestation is not None and not isinstance(
            self.completeness_attestation, CompositionCompletenessAttestationV2FU4
        ):
            raise TypeError(
                "completeness_attestation must be "
                "CompositionCompletenessAttestationV2FU4 or None, got "
                f"{type(self.completeness_attestation).__name__}"
            )

        # The bundle composition coherence (design section 3.3).
        if self.form is not TargetSalesUnitFormV2.BUNDLE:
            if (
                self.composition_clause is not None
                or self.composition_state is not None
                or self.completeness_attestation is not None
            ):
                raise ValueError(
                    "composition is a bundle-only fact: a non-BUNDLE target "
                    "form carries exactly (None, None, None) for the "
                    "composition clause / state / attestation"
                )
            self._verify_target_digest()
            return
        if self.composition_state is None:
            raise ValueError(
                "a BUNDLE-form target record REQUIRES the bounded "
                "composition-state classification (composition ABSENT is "
                "the explicit state, never a silent None)"
            )
        if (
            self.composition_state
            is BundleCompositionStateV2FU4.CONTRADICTED_PUBLISHED
        ):
            raise ValueError(
                "the target side has no CONTRADICTED_PUBLISHED state (one "
                "reviewed attestation is one record; a self-contradictory "
                "source is a review-governance failure, not a contract "
                "state — design T7)"
            )
        if self.composition_state is BundleCompositionStateV2FU4.ABSENT:
            if (
                self.composition_clause is not None
                or self.completeness_attestation is not None
            ):
                raise ValueError(
                    "an ABSENT target composition carries no clause and no "
                    "attestation"
                )
        elif self.composition_state in (
            BundleCompositionStateV2FU4.SYNTACTICALLY_VALID,
            BundleCompositionStateV2FU4.PARTIAL,
        ):
            if (
                self.composition_clause is None
                or self.completeness_attestation is not None
            ):
                raise ValueError(
                    "a SYNTACTICALLY_VALID / PARTIAL target composition "
                    "carries its clause and NO completeness attestation "
                    "(a SYNTACTICALLY_VALID target clause is "
                    "completeness-unknown and can never prove)"
                )
            if (
                self.composition_state
                is BundleCompositionStateV2FU4.SYNTACTICALLY_VALID
                and not _clause_is_textually_valid(self.composition_clause)
            ):
                raise ValueError(
                    "a SYNTACTICALLY_VALID target clause must pass the "
                    "textual closure checks (D5 at the type level)"
                )
        else:  # ESTABLISHED
            if (
                self.composition_clause is None
                or not _clause_is_textually_valid(self.composition_clause)
                or self.completeness_attestation is None
            ):
                raise ValueError(
                    "an ESTABLISHED target composition carries its "
                    "textually valid clause and its verified completeness "
                    "attestation (D19)"
                )
            att = self.completeness_attestation
            if att.subject_side is not EvidenceSideV2FU4.TARGET:
                raise ValueError(
                    "the target-side record's embedded attestation subjects "
                    "the TARGET side"
                )
            if att.source is not self.source:
                raise ValueError(
                    "the target-side record's embedded attestation carries "
                    "the record's recorded source (the clause's recorded "
                    "provenance)"
                )
            if att.clause_digest != _clause_digest(self.composition_clause):
                raise BundleCompositionEvidenceIntegrityError(
                    "the target-side record's embedded attestation is "
                    "bound to a different clause (clause_digest mismatch)"
                )
            att.verify()
        self._verify_target_digest()

    def _verify_target_digest(self) -> None:
        if not _is_hex_digest(self.evidence_digest):
            raise ValueError(
                "evidence_digest must be a 64-character hex digest"
            )
        if _canonical_digest(self.canonical()) != self.evidence_digest:
            raise BundleCompositionEvidenceIntegrityError(
                "evidence_digest does not verify against the record "
                "content (the record was tampered with or forged)"
            )

    def canonical(self) -> dict[str, object]:
        """The canonical (sorted-keys) document of the record minus its
        own digest (the embedded attestation's canonical document — WITH
        its own verified digest — is part of the record's digest)."""
        return {
            "schema_version": self.schema_version,
            "form": self.form.value,
            "quantity": self.quantity,
            "source": self.source.value,
            "composition_clause": self.composition_clause,
            "composition_state": (
                self.composition_state.value
                if self.composition_state is not None
                else None
            ),
            "completeness_attestation": (
                self.completeness_attestation.canonical()
                if self.completeness_attestation is not None
                else None
            ),
        }

    def verify(self) -> None:
        """Re-verify a PRESENTED record (the anti-forgery gate before any
        derivation input): the ``evidence_digest`` over the full record
        (the embedded attestation within) plus the embedded attestation's
        own digest. Raises
        ``BundleCompositionEvidenceIntegrityError`` on any mismatch."""
        if _canonical_digest(self.canonical()) != self.evidence_digest:
            raise BundleCompositionEvidenceIntegrityError(
                "evidence_digest does not verify against the record "
                "content (the record was tampered with or forged)"
            )
        if self.completeness_attestation is not None:
            self.completeness_attestation.verify()


# ---------------------------------------------------------------------------
# The versioned clause extraction (design section 3.4 — marker strip)
# ---------------------------------------------------------------------------

#: The canonical bundle count: 1..99999, no leading zero (verbatim-checked
#: — packaging words are case-insensitive, the number is not).
_CANONICAL_COUNT: Final[str] = r"[1-9][0-9]{0,4}"

#: Count-only bundle phrases (design section 3.4 step 1 — WHOLE-TEXT
#: match; the count stays verbatim and is never bound to a quantity).
_COUNT_ONLY_BUNDLE_PATTERNS: Final[tuple[re.Pattern[str], ...]] = (
    re.compile(r"(?i)^bundle$"),
    re.compile(rf"(?i)^bundle\s+of\s+({_CANONICAL_COUNT})$"),
    re.compile(rf"^({_CANONICAL_COUNT})\s*[- ]\s*(?i:unit)\s+(?i:bundle)$"),
)

#: Marker forms (design section 3.4 step 2): the word ``bundle`` +
#: optional whitespace + ``:`` or ``(``, INCLUDING the count-prefixed
#: variants (in which the published count is IGNORED by the clause
#: extraction — it stays the channel / target's quantity fact, never
#: re-bound into the clause, D17a).
_MARKER_BARE: Final[re.Pattern[str]] = re.compile(r"(?i)^bundle\s*([:(])")
_MARKER_COUNT_OF: Final[re.Pattern[str]] = re.compile(
    rf"(?i)^bundle\s+of\s+{_CANONICAL_COUNT}\s*([:(])"
)
_MARKER_COUNT_NUNIT: Final[re.Pattern[str]] = re.compile(
    rf"^({_CANONICAL_COUNT})\s*[- ]\s*(?i:unit)\s+(?i:bundle)\s*([:(])"
)


def _extract_clause_full(
    text: str,
) -> tuple[str | None, bool, bool]:
    """The full internal clause extraction over one verbatim published
    span: returns ``(clause, was_paren_form, paren_closed)``.

    * Step 1 — count-only bundle phrase (whole-text match): the clause is
      None (composition ABSENT; the count is never bound, P2-FU1 / D17).
    * Step 2 — marker form: strip the marker prefix; for the paren form,
      strip the ENCLOSING closing paren when present (the cue span
      includes it) and report the closure; the clause is the residue
      (original case / spacing preserved).
    * Step 3 — no marker, not count-only (the corpus shape: the
      structured field's value IS the contents): the clause is the whole
      text (trimmed of the span's edge whitespace).
    """
    s = text.strip()
    for pattern in _COUNT_ONLY_BUNDLE_PATTERNS:
        if pattern.match(s) is not None:
            return None, False, True
    match = (
        _MARKER_COUNT_OF.match(s)
        or _MARKER_COUNT_NUNIT.match(s)
        or _MARKER_BARE.match(s)
    )
    if match is not None:
        # The count-prefixed variant captures the marker character in a
        # later group; the bare form captures it in group 1.
        marker_char = match.group(match.lastindex)
        residue = s[match.end() :]
        if marker_char == "(":
            if residue.endswith(")"):
                return residue[:-1].strip(), True, True
            return residue.strip(), True, False
        return residue.strip(), False, True
    return s, False, True


def extract_published_bundle_clause(
    text: str,
) -> tuple[str | None, bool]:
    """The versioned bounded clause extraction (design section 3.4): one
    verbatim published span (an established cue text or a recorded
    channel ``raw_detail``) → ``(clause, was_paren_form)``.

    The steps are deterministic and total: count-only bundle phrase
    (whole-text match) → no clause (ABSENT); marker form (``bundle`` +
    optional whitespace + ``:`` or ``(``, including the count-prefixed
    variants, in which the published count is IGNORED by the clause
    extraction) → the residue, the enclosing closing paren stripped when
    present; no marker, not count-only → the whole text. An input
    matching none is treated as step 3 (a recorded channel
    ``raw_detail`` is by contract "the observed value as published").
    """
    if not isinstance(text, str):
        raise TypeError(
            "text must be str (a verbatim published span), got "
            f"{type(text).__name__}"
        )
    clause, was_paren, _closed = _extract_clause_full(text)
    return clause, was_paren


# ---------------------------------------------------------------------------
# The textual closure classification + completeness-marker detection
# (design section 3.5a / 3.5b — CORRECTED)
# ---------------------------------------------------------------------------

#: The bounded versioned incompleteness-marker list (design section 3.5a).
#: A single-word member matches as a complete whitespace-delimited token
#: anywhere in the clause (casefolded); a multi-word member matches as a
#: maximal whitespace-delimited run; the ellipsis character (``…``) or
#: the dot-triplet token (``...``) matches anywhere.
_INCOMPLETE_MARKERS: Final[tuple[str, ...]] = (
    "etc.",
    "etc",
    "…",
    "...",
    "and more",
    "+ more",
    "and so on",
    "among others",
    "and other",
)

#: The single-word (complete-token) incompleteness members.
_INCOMPLETE_TOKEN_MARKERS: Final[tuple[str, ...]] = ("etc.", "etc")

#: The multi-word (maximal whitespace-delimited run) incompleteness
#: members.
_INCOMPLETE_RUN_MARKERS: Final[tuple[str, ...]] = (
    "and more",
    "+ more",
    "and so on",
    "among others",
    "and other",
)

#: The versioned completeness-marker list (design section 3.5b; the T9
#: discipline — any addition / removal / rewording is a new version).
_COMPLETENESS_MARKERS: Final[tuple[str, ...]] = (
    "complete list",
    "all items listed",
    "everything included",
    "all included",
    "full contents",
    "nothing else included",
)

#: The bounded versioned marker-delimiter set (design section 3.5b): the
#: delimiter is whitespace-prefixed in-clause (``+`` / `,` / ``&`` /
#: ``;`` / "and" / em-dash / en-dash / ``(``).
_COMPLETENESS_MARKER_DELIMITERS: Final[tuple[str, ...]] = (
    "+",
    ",",
    "&",
    ";",
    "and",
    "—",
    "–",
    "(",
)

#: The punctuation characters stripped from a whitespace-delimited token
#: before incompleteness-marker comparison (the marker "etc." in
#: "etc.," or "and more." is the same published marker; the stripping
#: is symmetric, so no new phrasing is admitted — an unlisted phrasing
#: stays unattested, the safe direction).
_PUNCT_STRIP: Final[str] = ",;:()[]\"'.!?"


def _incomplete_token_key(token: str) -> str:
    return token.casefold().strip(_PUNCT_STRIP)


#: The normalized single-word incompleteness keys (import-self-checked
#: against the versioned member list above).
_INCOMPLETE_TOKEN_KEYS: Final[frozenset[str]] = frozenset(
    _incomplete_token_key(member) for member in _INCOMPLETE_TOKEN_MARKERS
)

#: The normalized multi-word run keys.
_INCOMPLETE_RUN_KEYS: Final[frozenset[str]] = frozenset(
    _incomplete_token_key(member) for member in _INCOMPLETE_RUN_MARKERS
)

#: The dangling trailing separator / incomplete quantity token (design
#: section 3.5a PARTIAL): positive evidence the published statement
#: continues beyond the examined text.
_DANGLING_END_RE: Final[re.Pattern[str]] = re.compile(r"[0-9]+\s*[x×]\s*$")


def _clause_has_incomplete_marker(clause: str) -> bool:
    """True when the clause contains an explicit incompleteness marker
    from the bounded versioned list (the matching precision of design
    section 3.5a: a single-word member matches as a complete
    whitespace-delimited token anywhere in the clause — a trailing
    sentence-final punctuation is not part of the token's identity —;
    a multi-word member matches as a maximal whitespace-delimited run;
    the ellipsis character (``…``) or the dot-triplet token (``...``)
    matches anywhere)."""
    if "…" in clause or "..." in clause:
        return True
    tokens = clause.split()
    keys = [_incomplete_token_key(token) for token in tokens]
    for key in keys:
        if key in _INCOMPLETE_TOKEN_KEYS:
            return True
    count = len(keys)
    for start in range(count):
        for end in range(start + 1, count + 1):
            if " ".join(keys[start:end]) in _INCOMPLETE_RUN_KEYS:
                return True
    return False


def _clause_ends_dangling(clause: str) -> bool:
    """True when the clause ends on a dangling separator (``+`` / `,` /
    ``&`` / `;` or whitespace after one) or on an incomplete quantity
    token (a trailing ``N x`` / ``Nx`` with no item following)."""
    s = clause.rstrip()
    if not s:
        return True
    if s[-1] in "+,&;":
        return True
    return _DANGLING_END_RE.search(s) is not None


def classify_clause_closure(
    clause: str | None,
    was_paren_form: bool = False,
    paren_closed: bool = True,
) -> BundleCompositionStateV2FU4:
    """The versioned textual-closure classification (design section
    3.5a): ``ABSENT`` | ``PARTIAL`` | ``SYNTACTICALLY_VALID``.

    An empty / None clause is ABSENT immediately. PARTIAL when any
    holds: an explicit incompleteness marker inside the clause (the
    bounded versioned list); the paren form's enclosure is not closed
    (``was_paren_form`` with ``paren_closed`` False — the published span
    ends without the closing paren, the clause truncated at the field
    boundary); the clause ends on a dangling separator / incomplete
    quantity token. SYNTACTICALLY_VALID otherwise — a textually complete
    published statement; the ENUMERATION's completeness is UNKNOWN (the
    state is a textual property only, never a completeness claim).

    The completeness marker can never rescue an unclosed clause: this
    classification runs BEFORE any marker detection, and an
    incompleteness marker always dominates (D5).
    """
    if clause is None or not clause.strip():
        return BundleCompositionStateV2FU4.ABSENT
    if was_paren_form and not paren_closed:
        return BundleCompositionStateV2FU4.PARTIAL
    if _clause_has_incomplete_marker(clause):
        return BundleCompositionStateV2FU4.PARTIAL
    if _clause_ends_dangling(clause):
        return BundleCompositionStateV2FU4.PARTIAL
    return BundleCompositionStateV2FU4.SYNTACTICALLY_VALID


def _marker_tail_span(text: str) -> tuple[int, int] | None:
    """The versioned completeness-marker detection (design section
    3.5b) over ONE text: returns ``(d_start, m_end)`` when the text ends
    with a bounded delimiter D + a versioned marker member M (M a
    maximal whitespace-delimited run at the text's end, D the delimiter
    immediately before it — `,` / `;` may attach to the preceding word,
    the other members are standalone tokens; whitespace is required
    between D and M), else None. The verbatim D+M segment is
    ``text[d_start:m_end]`` (the attestation text); the residual clause
    is ``text[:d_start]`` (trailing whitespace excluded).

    A marker-ONLY text (the text is exactly the marker) is NOT returned
    here — the caller classifies it ABSENT (an empty composition with a
    marker; the marker names no contents).
    """
    s = text.rstrip(" \t")
    if not s:
        return None
    cf = s.casefold()
    for marker in _COMPLETENESS_MARKERS:
        if not cf.endswith(marker):
            continue
        m_start = len(s) - len(marker)
        if m_start == 0:
            return None  # marker-only text
        if s[m_start - 1].isalnum():
            continue  # M is not a whitespace-delimited run
        t = s[:m_start].rstrip(" \t")
        if not t:
            continue  # D is missing (the marker sits at the text's start)
        last = t[-1]
        if last in ",;":
            # `,` / `;` may attach to the preceding word; M must be
            # whitespace-separated from the symbol.
            if m_start - len(t) == 0:
                continue
            d_start = len(t) - 1
        elif last in "+&(—–":
            # A standalone symbol: the character before it is not a word
            # character; M may sit directly after it (" (all items listed").
            if len(t) >= 2 and t[-2].isalnum():
                continue  # a symbol glued to a word is not a delimiter
            d_start = len(t) - 1
        elif t.casefold().endswith("and"):
            # The word "and" as a standalone delimiter; M must be
            # whitespace-separated from it.
            if len(t) > 3 and t[-4].isalnum():
                continue  # "and" must be the complete word
            if m_start - len(t) == 0:
                continue
            d_start = len(t) - 3
        else:
            continue
        return (d_start, len(s))
    return None


def _detect_continuation_marker(
    field_text: str, cue_end: int,
) -> str | None:
    """The EXTRACTION-basis continuation detection (design section 3.5b):
    the frozen cue engine's COLON-form span stops at the first comma /
    semicolon / closing paren, so the marker segment may sit in the
    RECORDED field text immediately after the cue span. Returns the
    verbatim recorded D+M segment when the continuation begins, after
    any whitespace, with a bounded delimiter + a marker member (no other
    text between the span end and the delimiter), else None."""
    continuation = field_text[cue_end:]
    span = _marker_tail_span(continuation)
    if span is None:
        return None
    d_start, m_end = span
    if continuation[:d_start].strip() != "":
        return None
    return continuation[d_start:m_end]


# ---------------------------------------------------------------------------
# The versioned materiality grammar (design section 3.7 — CORRECTED scope:
# the TEXTUAL-AGREEMENT axis and the MATERIAL-DIFFERENCE test ONLY — never
# completeness, never quantity)
# ---------------------------------------------------------------------------

#: The grammar's separators (split the clause into entries): ``+`` / `,`
#: / ``&`` / `` and `` (case-insensitive).
_GRAMMAR_SEPARATOR_RE: Final[re.Pattern[str]] = re.compile(
    r"\s*(?:[+,&]|\band\b)\s*", re.IGNORECASE
)

#: The item token: alphanumerics with internal single spaces / ``.`` /
#: ``-`` / ``_`` (starts and ends on an alphanumeric).
_ITEM_TOKEN_RE: Final[re.Pattern[str]] = re.compile(
    r"^[0-9A-Za-z](?:[0-9A-Za-z \.\-_]*[0-9A-Za-z])?$"
)


def _is_canonical_count(digits: str) -> bool:
    """The canonical integer 1..99999 (no leading zero) check over an
    already-digit string."""
    if len(digits) > 1 and digits.startswith("0"):
        return False
    value = int(digits)
    return 1 <= value <= 99999


def _normalize_item(item: str) -> str:
    """The grammar-internal normalization (D16): casefold +
    leading/trailing whitespace strip + internal whitespace collapse to
    single spaces. Applies ONLY inside the grammar — never to the
    primary byte-identity comparison."""
    return re.sub(r"\s+", " ", item.strip()).casefold()


def _parse_entry(part: str) -> tuple[int, str] | None:
    """Parse ONE entry of the versioned materiality grammar: an optional
    quantity (a canonical integer 1..99999, no leading zero, followed by
    ``x`` / ``×`` (any case) and optional whitespace — or by whitespace
    when the ``x`` is absent) then a non-empty item token. Returns
    ``(quantity, normalized item)`` or None when the entry is not
    fully parseable (a residual — the safe direction).

    A digit run attached to a letter (``960GB SSD``) is item text, never
    a quantity (design F2); a non-canonical digit run followed by
    ``x`` / ``×`` (``04x RAM``) is NOT fully parseable (design B8).
    """
    i = 0
    while i < len(part) and part[i].isdigit():
        i += 1
    if i > 0:
        digits = part[:i]
        rest = part[i:]
        if rest.startswith(("x", "×")):
            item_part = rest[1:].lstrip(" \t")
        elif rest.startswith((" ", "\t")):
            item_part = rest.lstrip(" \t")
        else:
            item_part = None
        if item_part is not None:
            if not _is_canonical_count(digits) or not item_part or not _ITEM_TOKEN_RE.match(
                item_part
            ):
                return None
            return int(digits), _normalize_item(item_part)
    if part and _ITEM_TOKEN_RE.match(part):
        return 1, _normalize_item(part)
    return None


def _full_parse_clause(clause: str) -> tuple[tuple[tuple[int, str], ...] | None]:
    """The versioned materiality grammar's full parse (design section
    3.7): the trimmed clause decomposes EXACTLY into entries joined by
    the grammar's separators, with no residual. Returns the multiset —
    the sorted tuple of ``(quantity, item)`` pairs — or None when the
    clause is not fully parseable (ANY residual: parenthesized
    qualifiers, trailing punctuation not a separator, unknown tokens,
    non-canonical quantities)."""
    text = clause.strip()
    if not text:
        return None
    parts = _GRAMMAR_SEPARATOR_RE.split(text)
    if any(part.strip() == "" for part in parts):
        return None
    entries: list[tuple[int, str]] = []
    for part in parts:
        parsed = _parse_entry(part)
        if parsed is None:
            return None
        entries.append(parsed)
    return tuple(sorted(entries))


_T_TEXTUAL_AGREEMENT = "T-AGREE"
_T_DIFFERENCE_MATERIAL = "T-DIFF-MATERIAL"
_T_DIFFERENCE_UNESTABLISHED = "T-DIFF-UNESTABLISHED"


def _textual_relation(clause_a: str, clause_b: str) -> str:
    """The TEXTUAL-AGREEMENT axis between two clauses (design section
    3.7 / D16 — CORRECTED: textual agreement only, never completeness):

    * byte-identity over the clause form (the primary path) → T-AGREE;
    * otherwise, both clauses fully parse and the multisets are equal →
      T-AGREE (the secondary path — order / formatting differences are
      immaterial);
    * otherwise, both clauses fully parse and the multisets differ →
      T-DIFF-MATERIAL (a materially established difference);
    * otherwise (at least one side not fully parseable) →
      T-DIFF-UNESTABLISHED (the difference is textual but not
      materially established — D7's safe direction: UNPROVEN, never
      CONTRADICTED on unparseable text).
    """
    if clause_a == clause_b:
        return _T_TEXTUAL_AGREEMENT
    parsed_a = _full_parse_clause(clause_a)
    parsed_b = _full_parse_clause(clause_b)
    if parsed_a is not None and parsed_b is not None:
        if parsed_a == parsed_b:
            return _T_TEXTUAL_AGREEMENT
        return _T_DIFFERENCE_MATERIAL
    return _T_DIFFERENCE_UNESTABLISHED


# ---------------------------------------------------------------------------
# The construction entry points (fail closed — design section 6)
# ---------------------------------------------------------------------------


def _build_candidate_record(
    basis: CandidateCompositionEvidenceBasisV2FU4,
    state: BundleCompositionStateV2FU4,
    clause: str | None,
    additional_clauses: tuple[str, ...],
    attestation: CompositionCompletenessAttestationV2FU4 | None,
    source: CandidateEvidenceSourceV2,
    channel_quantity: int | None,
    extraction_result_digest: str | None,
    extraction_input_digest: str | None,
) -> CandidateBundleCompositionEvidenceV2FU4:
    """The internal record assembly (the digest is computed over the
    canonical document minus the digest itself — the constructor
    re-verifies it)."""
    document = {
        "schema_version": BUNDLE_COMPOSITION_EVIDENCE_VERSION_FU4,
        "basis": basis.value,
        "state": state.value,
        "completeness_attestation": (
            attestation.canonical() if attestation is not None else None
        ),
        "composition_clause": clause,
        "additional_clauses": list(additional_clauses),
        "source": source.value,
        "channel_quantity": channel_quantity,
        "extraction_result_digest": extraction_result_digest,
        "extraction_input_digest": extraction_input_digest,
    }
    return CandidateBundleCompositionEvidenceV2FU4(
        schema_version=BUNDLE_COMPOSITION_EVIDENCE_VERSION_FU4,
        basis=basis,
        state=state,
        completeness_attestation=attestation,
        composition_clause=clause,
        additional_clauses=additional_clauses,
        source=source,
        channel_quantity=channel_quantity,
        extraction_result_digest=extraction_result_digest,
        extraction_input_digest=extraction_input_digest,
        evidence_digest=_canonical_digest(document),
    )


def _candidate_published_attestation(
    source: CandidateEvidenceSourceV2,
    clause: str,
    attestation_text: str,
) -> CompositionCompletenessAttestationV2FU4:
    """The PUBLISHED-basis candidate attestation machine-constructed from
    the recorded marker detection (design section 3.8: the only machine
    path for a completeness attestation — deterministic, bounded, over
    recorded text). The attestation's digest is computed over its
    canonical document; the constructor re-verifies it."""
    clause_digest = _clause_digest(clause)
    attestation = CompositionCompletenessAttestationV2FU4(
        schema_version=BUNDLE_COMPOSITION_EVIDENCE_VERSION_FU4,
        subject_side=EvidenceSideV2FU4.CANDIDATE,
        basis=CompletenessBasisV2FU4.PUBLISHED_COMPLETENESS_STATEMENT,
        source=source,
        clause_digest=clause_digest,
        attestation_text=attestation_text,
        attestation_digest=_canonical_digest(
            {
                "schema_version": BUNDLE_COMPOSITION_EVIDENCE_VERSION_FU4,
                "subject_side": EvidenceSideV2FU4.CANDIDATE.value,
                "basis": CompletenessBasisV2FU4.PUBLISHED_COMPLETENESS_STATEMENT.value,
                "source": source.value,
                "clause_digest": clause_digest,
                "attestation_text": attestation_text,
            }
        ),
    )
    return attestation


def _determine_clause_form(
    text: str,
    allow_continuation: bool,
    field_text: str | None = None,
    cue_end: int | None = None,
) -> tuple[str | None, BundleCompositionStateV2FU4, str | None]:
    """The versioned determination over ONE verbatim published span
    (design sections 3.4 + 3.5a + 3.5b): the clause form, its textual
    state, and the verbatim published marker segment when the span's
    textually valid clause carries one (the PUBLISHED-basis
    attestation's text).

    * The clause is extracted (3.4) and closure-classified (3.5a).
    * A marker-ONLY clause (the span is exactly a completeness marker)
      is an empty composition with a marker: ABSENT (the marker names
      no contents).
    * A published marker tail (P + D + M) over the textually valid
      clause: the residue P is the clause — ESTABLISHED with the
      verbatim D+M segment as attestation text, when the residue is
      itself textually valid; a completeness marker can never rescue a
      dangling residue (D5): the clause stands as PARTIAL, recorded for
      audit, with NO attestation.
    * ``allow_continuation`` (the EXTRACTION basis, colon-form cues only):
      the frozen cue engine's COLON-form span stops at the first comma /
      semicolon / closing paren, so the marker segment may sit in the
      RECORDED field text immediately after the cue span (3.5b) — the
      verbatim recorded segment is the attestation text over the
      unchanged clause.
    """
    clause, was_paren, paren_closed = _extract_clause_full(text)
    state = classify_clause_closure(clause, was_paren, paren_closed)
    att_text: str | None = None
    if state is BundleCompositionStateV2FU4.ABSENT:
        return None, state, None
    assert clause is not None  # classify returned non-ABSENT ⇒ non-empty
    if state is BundleCompositionStateV2FU4.SYNTACTICALLY_VALID:
        if clause.strip().casefold() in _COMPLETENESS_MARKERS:
            # Marker-only: an empty composition with a marker.
            return None, BundleCompositionStateV2FU4.ABSENT, None
        span = _marker_tail_span(clause)
        if span is not None:
            d_start, m_end = span
            residue = clause[:d_start].rstrip(" \t")
            if _clause_is_textually_valid(residue):
                att_text = clause[d_start:m_end]
                return (
                    residue,
                    BundleCompositionStateV2FU4.ESTABLISHED,
                    att_text,
                )
            # D5: the marker can never rescue a dangling residue.
            return clause, BundleCompositionStateV2FU4.PARTIAL, None
        if (
            allow_continuation
            and not was_paren
            and field_text is not None
            and cue_end is not None
        ):
            continuation = _detect_continuation_marker(field_text, cue_end)
            if continuation is not None:
                return (
                    clause,
                    BundleCompositionStateV2FU4.ESTABLISHED,
                    continuation,
                )
    return clause, state, None


def candidate_composition_from_extraction(
    result: SalesUnitExtractionResult,
) -> CandidateBundleCompositionEvidenceV2FU4 | None:
    """The EXTRACTION_RESULT_V1-basis construction entry point (design
    section 6, item 4).

    Re-verifies the presented result FIRST (``verify_integrity`` — a
    tampered / forged result produces no evidence record). Returns None
    for every non-``OBSERVED_UNAMBIGUOUS`` state and for a non-BUNDLE
    established kind. For an OBSERVED BUNDLE result, reads the result's
    FULL established BUNDLE cue list (primary = the channel mapping's
    primary-cue rule: structured first, else first title span order):
    each established cue's clause is extracted (design section 3.4) and
    closure-classified (3.5a); the completeness marker is detected over
    each textually valid clause (3.5b, incl. the recorded field-text
    continuation for colon-form cues) ⇒ the PUBLISHED_COMPLETENESS_
    STATEMENT attestation when present.

    One textually differing clause pair ⇒ CONTRADICTED_PUBLISHED (every
    clause recorded with its own textual state; NONE adopted — the
    embedded attestation is None). Identical repeated clauses (byte-
    identical after marker strip) ⇒ one clause — repetition is textual
    agreement with itself, NOT completeness (consistency ≠
    completeness); the single clause is attested ONLY when the
    PUBLISHED marker sits over a cue whose recorded source is the
    record's recorded source (the primary cue's own marker, or a
    repeated cue in the same field): the attestation must bind the
    record's source, and a marker in a different field than the record's
    recorded clause is a self-inconsistent publication — not adopted.
    The pathological mixed corner (one cue publishes a clause, another
    publishes none — e.g. title ``bundle:`` + structured ``bundle:
    2x RAM``) is fail-closed: PARTIAL when the primary cue carries a
    clause (the publication is incomplete as a whole; the clause is
    recorded for audit; no attestation), ABSENT when the primary cue
    carries none — never ESTABLISHED, never PROVEN-reachable.
    """
    if not isinstance(result, SalesUnitExtractionResult):
        raise TypeError(
            "result must be SalesUnitExtractionResult (the verified "
            f"schema-v1 result), got {type(result).__name__}"
        )
    # The anti-forgery gate runs FIRST (a tampered / forged extraction
    # result produces no evidence record — the P2 gate).
    result.verify_integrity()
    if result.state is not SalesUnitExtractionState.OBSERVED_UNAMBIGUOUS:
        return None
    if result.established_kind is not SalesUnitKindV2.BUNDLE:
        return None

    established = [
        cue
        for cue in result.cues
        if cue.disposition is SalesUnitCueDisposition.ESTABLISHED
    ]
    if not established:
        return None
    structured = [
        cue
        for cue in established
        if cue.field is SalesUnitCueField.STRUCTURED_PACKAGING_FIELD
    ]
    primary = (structured or established)[0]

    # Per established cue (the result's canonical cue order — field
    # order, then span order): the determined clause form, its textual
    # state, and its own published marker attestation text (if any).
    per_cue: list[tuple[object, str | None, BundleCompositionStateV2FU4, str | None]] = [
        (
            cue,
            *_determine_clause_form(
                cue.cue_text,
                allow_continuation=True,
                field_text=cue.raw_field_value,
                cue_end=cue.cue_end,
            ),
        )
        for cue in established
    ]

    # The distinct clause forms (byte comparison over the clause form;
    # a None clause — a count-only / empty-marker cue — is a form of its
    # own).
    distinct: list[str | None] = []
    for _cue, clause, _state, _att in per_cue:
        if clause not in distinct:
            distinct.append(clause)

    primary_entry = next(entry for entry in per_cue if entry[0] is primary)
    _primary_cue, primary_clause, primary_state, primary_att_text = (
        primary_entry
    )

    if len(distinct) > 1:
        if any(clause is None for clause in distinct):
            # The mixed corner: fail closed (PARTIAL when the primary
            # cue carries a clause — the clause is recorded for audit,
            # no attestation; ABSENT when it carries none).
            if primary_clause is not None:
                state = BundleCompositionStateV2FU4.PARTIAL
                clause = primary_clause
            else:
                state = BundleCompositionStateV2FU4.ABSENT
                clause = None
        else:
            # Two or more published clauses that differ textually:
            # CONTRADICTED_PUBLISHED — every clause recorded (the
            # primary clause form + the other published clause forms in
            # canonical cue order, deduplicated), NONE adopted.
            state = BundleCompositionStateV2FU4.CONTRADICTED_PUBLISHED
            clause = primary_clause
            additional: list[str] = []
            for _cue, entry_clause, _entry_state, _entry_att in per_cue:
                if (
                    entry_clause is None
                    or entry_clause == primary_clause
                    or entry_clause in additional
                ):
                    continue
                additional.append(entry_clause)
            return _build_candidate_record(
                basis=CandidateCompositionEvidenceBasisV2FU4.EXTRACTION_RESULT_V1,
                state=state,
                clause=clause,
                additional_clauses=tuple(additional),
                attestation=None,
                source=primary.source,
                channel_quantity=result.established_quantity,
                extraction_result_digest=result.result_digest,
                extraction_input_digest=result.input_digest,
            )
    else:
        # One distinct clause form (a single cue, or identical repeated
        # clauses): repetition is textual agreement with itself, NOT
        # completeness (consistency ≠ completeness). The single clause's
        # state is the MOST RESTRICTIVE of the cues' determinations over
        # that form (a truncated / incomplete co-publication of the same
        # clause form — e.g. an unclosed paren span — is PARTIAL and
        # blocks attestation), and the published marker attests the
        # single clause only when it was detected over a cue whose
        # recorded source is the record's recorded source (the
        # attestation must bind the clause's recorded provenance — a
        # marker in a different field is a self-inconsistent
        # publication, not adopted).
        clause = primary_clause
        form_entries = [
            (cue, clause, state, att)
            for cue, clause, state, att in per_cue
            if clause == primary_clause
        ]
        if any(
            state is BundleCompositionStateV2FU4.PARTIAL
            for _cue, _clause, state, _att in form_entries
        ):
            state = BundleCompositionStateV2FU4.PARTIAL
            att_text = None
        else:
            state = primary_state
            att_text = primary_att_text
            if att_text is None:
                for cue, entry_clause, entry_state, entry_att_text in per_cue:
                    if (
                        entry_att_text is not None
                        and entry_clause == clause
                        and cue.source is primary.source
                    ):
                        att_text = entry_att_text
                        state = BundleCompositionStateV2FU4.ESTABLISHED
                        break

    attestation = (
        _candidate_published_attestation(primary.source, clause, att_text)
        if state is BundleCompositionStateV2FU4.ESTABLISHED
        and clause is not None
        and att_text is not None
        else None
    )
    return _build_candidate_record(
        basis=CandidateCompositionEvidenceBasisV2FU4.EXTRACTION_RESULT_V1,
        state=state,
        clause=clause,
        additional_clauses=(),
        attestation=attestation,
        source=primary.source,
        channel_quantity=result.established_quantity,
        extraction_result_digest=result.result_digest,
        extraction_input_digest=result.input_digest,
    )


def candidate_composition_from_channel(
    channel: CandidateSalesUnitEvidenceV2,
) -> CandidateBundleCompositionEvidenceV2FU4:
    """The RECORDED_CHANNEL-basis construction entry point (design
    section 6, item 4): the single-clause view over the channel's
    ``raw_detail`` (design section 3.4 steps 1–3 + 3.5a / 3.5b in-clause
    marker detection — the corpus-shaped / supplied channels where no
    extraction result is in evidence, design T6: a channel alone cannot
    detect two published clauses).

    OBSERVED BUNDLE only; anything else is contract misuse (ValueError).
    A corpus-shaped ``raw_detail`` carrying a recorded marker (e.g.
    ``"… bracket kit, complete list"``) attests via the PUBLISHED basis
    (pinned in design B1).
    """
    if not isinstance(channel, CandidateSalesUnitEvidenceV2):
        raise TypeError(
            "channel must be CandidateSalesUnitEvidenceV2 (the frozen "
            f"recorded channel), got {type(channel).__name__}"
        )
    if (
        channel.state is not PackagingEvidenceStateV2.OBSERVED
        or channel.kind is not SalesUnitKindV2.BUNDLE
        or channel.raw_detail is None
        or channel.source is None
    ):
        raise ValueError(
            "candidate_composition_from_channel is the RECORDED_CHANNEL "
            "basis over an OBSERVED BUNDLE channel alone (a non-bundle or "
            "unavailable channel has no composition fact to read — "
            "contract misuse)"
        )
    clause, state, att_text = _determine_clause_form(
        channel.raw_detail, allow_continuation=False
    )
    attestation = (
        _candidate_published_attestation(channel.source, clause, att_text)
        if state is BundleCompositionStateV2FU4.ESTABLISHED
        and clause is not None
        and att_text is not None
        else None
    )
    return _build_candidate_record(
        basis=CandidateCompositionEvidenceBasisV2FU4.RECORDED_CHANNEL,
        state=state,
        clause=clause,
        additional_clauses=(),
        attestation=attestation,
        source=channel.source,
        channel_quantity=channel.quantity,
        extraction_result_digest=None,
        extraction_input_digest=None,
    )


# ---------------------------------------------------------------------------
# The FU4 rule vocabulary + decision record (design D10 / D11)
# ---------------------------------------------------------------------------


class AuthorityRuleV2FU4(str, Enum):
    """The S2-A-FU4 audit-rule vocabulary: EXACTLY the FU3 set (the frozen
    S2-A rule values + the two restrict-only sales-unit firewall rules) —
    import-self-checked to be equal. FU4 introduces no new ``AuthorityRule``
    member (D10): the two frozen FU3 restrict-only ceilings cover every
    FU4 unit state (``UNPROVEN`` ⇒ ``CEILING_SALES_UNIT_NOT_PROVEN``;
    ``CONTRADICTED`` ⇒ ``CEILING_SALES_UNIT_CONTRADICTED``)."""

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
    CEILING_SALES_UNIT_CONTRADICTED = "CEILING_SALES_UNIT_CONTRADICTED"
    HARD_CONFLICT_SUPERSEDES = "HARD_CONFLICT_SUPERSEDES"
    HUMAN_CONFIRMED_APPLIED = "HUMAN_CONFIRMED_APPLIED"
    HUMAN_REJECTED_APPLIED = "HUMAN_REJECTED_APPLIED"
    HARD_CONFLICT_SUPERSEDES_HUMAN = "HARD_CONFLICT_SUPERSEDES_HUMAN"
    HUMAN_OUTCOME_NOT_APPLICABLE = "HUMAN_OUTCOME_NOT_APPLICABLE"


def _to_fu4_rule(rule: AuthorityRuleV2) -> AuthorityRuleV2FU4:
    """Exact-value projection of a frozen audit rule onto the FU4
    vocabulary (import-self-checked to always exist)."""
    return AuthorityRuleV2FU4(rule.value)


@dataclass(frozen=True)
class AuthorityDecisionV2FU4:
    """The S2-A-FU4 authority derivation result for one candidate
    (design D11 — CORRECTED audit surface).

    The FU3 record's field set with the same construction invariants
    (an ``AI_ASSISTED_COMPARABLE`` tier with an UNPROVEN or a
    CONTRADICTED unit is un-constructible; the unproven-unit ceiling may
    only appear with an UNPROVEN unit on a NEEDS_REVIEW tier; the
    contradiction ceiling only with a CONTRADICTED unit on NEEDS_REVIEW;
    ``frozen_fired_rules`` projects the trail back onto the frozen
    vocabulary), PLUS the bounded bundle-axis audit fields — for BUNDLE
    channels: the quantity-axis state (``BundleQuantityAxisStateV2FU4``),
    the candidate / target composition states, the
    completeness-attestation digests, the quantity-attestation digest;
    for non-bundle channels: exactly None. The determinations are
    RECORDED, never silent (D19 / D20). An FU4 decision is
    type-distinguishable from an FU3 decision at replay.
    """

    tier: AuthorityTier
    fired_rules: frozenset[AuthorityRuleV2FU4]
    product_evidence_quality: ProductEvidenceQuality
    relationship_authority: RelationshipAuthority
    identity_resolution_bound: IdentityResolutionBoundV2
    sales_unit_authority: SalesUnitAuthorityV2
    quantity_axis_state: BundleQuantityAxisStateV2FU4 | None
    candidate_composition_state: BundleCompositionStateV2FU4 | None
    target_composition_state: BundleCompositionStateV2FU4 | None
    candidate_completeness_attestation_digest: str | None
    target_completeness_attestation_digest: str | None
    quantity_attestation_digest: str | None

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
                "an FU4 authority decision must record at least one "
                "fired rule"
            )
        for rule in self.fired_rules:
            if not isinstance(rule, AuthorityRuleV2FU4):
                raise TypeError(
                    "fired_rules must contain only AuthorityRuleV2FU4 "
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
        for name in (
            "quantity_axis_state",
            "candidate_composition_state",
            "target_composition_state",
        ):
            value = getattr(self, name)
            if value is None:
                continue
            expected = (
                BundleQuantityAxisStateV2FU4
                if name == "quantity_axis_state"
                else BundleCompositionStateV2FU4
            )
            if not isinstance(value, expected):
                raise TypeError(
                    f"{name} must be {expected.__name__} or None (the "
                    f"bounded bundle-axis audit field), got "
                    f"{type(value).__name__}"
                )
        for name in (
            "candidate_completeness_attestation_digest",
            "target_completeness_attestation_digest",
            "quantity_attestation_digest",
        ):
            value = getattr(self, name)
            if value is not None and not _is_hex_digest(value):
                raise ValueError(
                    f"{name} must be a 64-character hex digest or None"
                )
        # The firewall invariants, enforced at construction (the FU3
        # invariants, preserved verbatim): the unproven-unit and
        # contradicted-unit exposures are un-constructible, not merely
        # un-derivable.
        if (
            self.tier is AuthorityTier.AI_ASSISTED_COMPARABLE
            and self.sales_unit_authority is SalesUnitAuthorityV2.UNPROVEN
        ):
            raise ValueError(
                "an unproven sales unit can never hold the automatic "
                "comparable tier under the FU4 contract; the "
                "restrict-only ceiling must have capped it at "
                "NEEDS_REVIEW"
            )
        if (
            self.tier is AuthorityTier.AI_ASSISTED_COMPARABLE
            and self.sales_unit_authority is SalesUnitAuthorityV2.CONTRADICTED
        ):
            raise ValueError(
                "a contradicted (published incompatible) sales unit can "
                "never hold the automatic comparable tier under the FU4 "
                "contract; the restrict-only contradiction ceiling must "
                "have capped it at NEEDS_REVIEW"
            )
        if AuthorityRuleV2FU4.CEILING_SALES_UNIT_NOT_PROVEN in self.fired_rules:
            if (
                self.sales_unit_authority is not SalesUnitAuthorityV2.UNPROVEN
                or self.tier is not AuthorityTier.NEEDS_REVIEW
            ):
                raise ValueError(
                    "the sales-unit ceiling rule fires only for an "
                    "UNPROVEN unit on a NEEDS_REVIEW tier (restrict "
                    "only; never lifts, never fires elsewhere)"
                )
        if (
            AuthorityRuleV2FU4.CEILING_SALES_UNIT_CONTRADICTED
            in self.fired_rules
        ):
            if (
                self.sales_unit_authority
                is not SalesUnitAuthorityV2.CONTRADICTED
                or self.tier is not AuthorityTier.NEEDS_REVIEW
            ):
                raise ValueError(
                    "the sales-unit contradiction ceiling rule fires "
                    "only for a CONTRADICTED unit on a NEEDS_REVIEW "
                    "tier (restrict only; never lifts, never fires "
                    "elsewhere)"
                )

    @property
    def frozen_fired_rules(self) -> frozenset[AuthorityRuleV2]:
        """The FU4 audit trail projected onto the frozen rule vocabulary
        (the two restrict-only firewall rules — which have no frozen
        counterpart — are excluded). When neither fired this equals the
        frozen derivation's rule trail exactly."""
        return frozenset(
            AuthorityRuleV2(rule.value)
            for rule in self.fired_rules
            if rule
            not in (
                AuthorityRuleV2FU4.CEILING_SALES_UNIT_NOT_PROVEN,
                AuthorityRuleV2FU4.CEILING_SALES_UNIT_CONTRADICTED,
            )
        )


# ---------------------------------------------------------------------------
# The FU4 unit derivation (design section 5 — the CORRECTED decision table)
# ---------------------------------------------------------------------------


def _verify_candidate_composition(
    record: CandidateBundleCompositionEvidenceV2FU4,
    channel: CandidateSalesUnitEvidenceV2,
) -> None:
    """The anti-forgery gate over a PRESENTED candidate record: the
    ``evidence_digest`` re-verification (the embedded attestation within)
    plus the embedded attestation's coherence (subject CANDIDATE, basis
    PUBLISHED_COMPLETENESS_STATEMENT, source = the record's source,
    clause_digest over exactly the record's clause) plus the binding to
    the presented channel (the record's ``source`` and
    ``channel_quantity`` must agree with the channel's — a record cannot
    claim provenance the channel never recorded)."""
    record.verify()
    att = record.completeness_attestation
    if att is not None:
        if att.subject_side is not EvidenceSideV2FU4.CANDIDATE:
            raise BundleCompositionEvidenceIntegrityError(
                "the candidate-side record's embedded attestation does "
                "not subject the CANDIDATE side (forged or misplaced)"
            )
        if att.basis is not (
            CompletenessBasisV2FU4.PUBLISHED_COMPLETENESS_STATEMENT
        ):
            raise BundleCompositionEvidenceIntegrityError(
                "the candidate-side record's embedded attestation does "
                "not rest on the PUBLISHED_COMPLETENESS_STATEMENT basis "
                "(a candidate-side record cannot carry a review basis)"
            )
        if att.source is not record.source:
            raise BundleCompositionEvidenceIntegrityError(
                "the candidate-side record's embedded attestation does "
                "not carry the record's recorded source"
            )
        if att.clause_digest != _clause_digest(record.composition_clause or ""):
            raise BundleCompositionEvidenceIntegrityError(
                "the candidate-side record's embedded attestation is "
                "bound to a different clause (clause_digest mismatch)"
            )
    if record.source is not channel.source:
        raise BundleCompositionEvidenceIntegrityError(
            "the candidate composition record claims a provenance the "
            "presented channel never recorded (source mismatch)"
        )
    if record.channel_quantity is not channel.quantity:
        raise BundleCompositionEvidenceIntegrityError(
            "the candidate composition record claims a published "
            "quantity the presented channel never recorded "
            "(channel_quantity mismatch)"
        )


def _verify_target_evidence(
    record: TargetSalesUnitEvidenceV2FU4,
) -> None:
    """The anti-forgery gate over a PRESENTED target-side record: the
    ``evidence_digest`` re-verification (the embedded attestation
    within) plus the embedded attestation's coherence (subject TARGET,
    source = the record's source, clause_digest over exactly the
    record's clause)."""
    record.verify()
    att = record.completeness_attestation
    if att is not None:
        if att.subject_side is not EvidenceSideV2FU4.TARGET:
            raise BundleCompositionEvidenceIntegrityError(
                "the target-side record's embedded attestation does not "
                "subject the TARGET side (forged or misplaced)"
            )
        if att.source is not record.source:
            raise BundleCompositionEvidenceIntegrityError(
                "the target-side record's embedded attestation does not "
                "carry the record's recorded source"
            )
        if att.clause_digest != _clause_digest(record.composition_clause or ""):
            raise BundleCompositionEvidenceIntegrityError(
                "the target-side record's embedded attestation is "
                "bound to a different clause (clause_digest mismatch)"
            )


def derive_sales_unit_authority_fu4(
    channel: CandidateSalesUnitEvidenceV2,
    candidate_composition: CandidateBundleCompositionEvidenceV2FU4 | None,
    target_evidence: (
        TargetSalesUnitEvidenceV2FU4 | TargetSalesUnitEvidenceV2 | None
    ),
    quantity_attestation: QuantityCompletenessAttestationV2FU4 | None = None,
) -> SalesUnitAuthorityV2:
    """The FU4 sales-unit derivation (design section 5 — the CORRECTED
    decision table U0–U21): pure, deterministic, zero-live, replayable.

    Preconditions (fail closed): the channel is the frozen type
    (``UNAVAILABLE`` ⇒ UNPROVEN for every target, and a composition
    record or quantity attestation over it is contract misuse); the
    candidate record (when present) re-verifies its ``evidence_digest``
    — including its embedded completeness attestation — and its binding
    to the presented channel (a non-BUNDLE channel with a composition
    record is contract misuse, D9); the target evidence is None (the
    default single unit), the frozen FU3 record (read as
    composition-ABSENT — D18, no implicit upgrade), or the FU4 record
    (digest re-verified — including its embedded completeness
    attestation); the quantity attestation (when present) is
    digest-verified BEFORE any axis uses it and is admissible ONLY over
    an asymmetric quantity axis with its subject side the
    actually-missing side (a subject mismatch is an integrity error; a
    presentation over a non-asymmetric or non-bundle axis is contract
    misuse).

    The non-bundle arms (``SINGLE_UNIT`` / ``PACK_QUANTITY`` /
    ``TRAY_OR_FACTORY_PACK``) delegate to the frozen FU3 derivation
    (byte-identical behavior — D9). The BUNDLE arm applies the CORRECTED
    D6 conjunction: the form rule before any composition is read (U9);
    missing / partial / self-contradicted composition on either side ⇒
    UNPROVEN (U10–U14); over the two textually-valid clauses, the
    quantity axis (D20) and the textual-agreement axis (D16):
    ``CONTRADICTED`` iff the quantity axis is CONTRADICTED over
    textually-agreed clauses (U16) or a materially established
    difference over two ESTABLISHED clauses (U17); ``PROVEN_
    EQUIVALENT`` iff both sides ESTABLISHED (each with its own verified
    attestation), the clauses textually agree, and the quantity axis is
    SATISFIED (U19 / U20); every other combination UNPROVEN (U15 / U18 /
    U21).

    Never an input, never inferred: model confidence, model matched /
    conflicting / missing-critical attributes (a model claim of "bundle
    contents matched" OR of "the composition is complete" is not
    independent verification — only the attestation records are),
    product-title similarity beyond the recorded verbatim clause, price,
    availability, or any other commercial fact; no quantity is inferred
    from a bundle item count, a missing value, an MPN, a price, a model
    output, or an absence (D17c); no completeness is inferred from
    syntactic closure, byte-identity, multiset equality, same-page
    repetition, or an absence (D17d / D19); the attestations' recorded
    text is never an input (the bounded fields drive behavior; F4).
    """
    unit, _audit = _derive_unit_and_audit(
        channel, candidate_composition, target_evidence, quantity_attestation
    )
    return unit


def derive_sales_unit_authority_fu4_case(
    case_v2: SemanticMatchCaseV2,
    candidate_composition: CandidateBundleCompositionEvidenceV2FU4 | None,
    target_evidence: (
        TargetSalesUnitEvidenceV2FU4 | TargetSalesUnitEvidenceV2 | None
    ),
    quantity_attestation: QuantityCompletenessAttestationV2FU4 | None = None,
) -> SalesUnitAuthorityV2:
    """The FU4 specification entry point over a RECORDED V2 input: the
    sales-unit authority of one ``SemanticMatchCaseV2`` (mirroring the
    frozen ``derive_sales_unit_authority``) — a pure function of the
    input's explicit sales-unit channel
    (``candidate_commercial.sales_unit``) and the derivation-side
    records. Zero live work, replayable: the same recorded input always
    derives the same state."""
    if not isinstance(case_v2, SemanticMatchCaseV2):
        raise TypeError(
            "case_v2 must be SemanticMatchCaseV2 (the recorded V2 "
            f"input), got {type(case_v2).__name__}"
        )
    return derive_sales_unit_authority_fu4(
        case_v2.candidate_commercial.sales_unit,
        candidate_composition,
        target_evidence,
        quantity_attestation,
    )


def _derive_unit_and_audit(
    channel: CandidateSalesUnitEvidenceV2,
    candidate_composition: CandidateBundleCompositionEvidenceV2FU4 | None,
    target_evidence: (
        TargetSalesUnitEvidenceV2FU4 | TargetSalesUnitEvidenceV2 | None
    ),
    quantity_attestation: QuantityCompletenessAttestationV2FU4 | None,
) -> tuple[
    SalesUnitAuthorityV2,
    tuple[
        BundleQuantityAxisStateV2FU4 | None,
        BundleCompositionStateV2FU4 | None,
        BundleCompositionStateV2FU4 | None,
        str | None,
        str | None,
        str | None,
    ],
]:
    """The internal unit + bundle-axis audit derivation (the decision
    table U0–U21 over the three recorded axes: form,
    composition-with-completeness, quantity). Returns the unit plus
    ``(quantity_axis_state, candidate_composition_state,
    target_composition_state, candidate_attestation_digest,
    target_attestation_digest, quantity_attestation_digest)`` — the
    audit fields are exactly None for non-bundle channels."""
    if not isinstance(channel, CandidateSalesUnitEvidenceV2):
        raise TypeError(
            "channel must be CandidateSalesUnitEvidenceV2 (the recorded "
            f"sales-unit channel), got {type(channel).__name__}"
        )
    if candidate_composition is not None and not isinstance(
        candidate_composition, CandidateBundleCompositionEvidenceV2FU4
    ):
        raise TypeError(
            "candidate_composition must be "
            "CandidateBundleCompositionEvidenceV2FU4 or None, got "
            f"{type(candidate_composition).__name__}"
        )
    if target_evidence is not None and not isinstance(
        target_evidence,
        (TargetSalesUnitEvidenceV2FU4, TargetSalesUnitEvidenceV2),
    ):
        raise TypeError(
            "target_evidence must be TargetSalesUnitEvidenceV2FU4, the "
            f"frozen TargetSalesUnitEvidenceV2, or None (the default "
            f"single unit), got {type(target_evidence).__name__}"
        )
    if quantity_attestation is not None and not isinstance(
        quantity_attestation, QuantityCompletenessAttestationV2FU4
    ):
        raise TypeError(
            "quantity_attestation must be "
            f"QuantityCompletenessAttestationV2FU4 or None, got "
            f"{type(quantity_attestation).__name__}"
        )

    # U0 — recorded absence (FU3-identical): UNPROVEN for every target.
    if channel.state is PackagingEvidenceStateV2.UNAVAILABLE:
        if candidate_composition is not None or quantity_attestation is not None:
            raise ValueError(
                "the recorded absence (an UNAVAILABLE channel) admits no "
                "composition evidence and no quantity attestation "
                "(contract misuse — fail closed)"
            )
        return (
            SalesUnitAuthorityV2.UNPROVEN,
            (None, None, None, None, None, None),
        )

    # The presented candidate record: the anti-forgery gate + the
    # channel binding (a record cannot claim provenance the channel
    # never recorded).
    if candidate_composition is not None:
        if channel.kind is not SalesUnitKindV2.BUNDLE:
            raise ValueError(
                "a composition record over a non-BUNDLE channel is "
                "contract misuse (composition is a bundle-only fact; the "
                "non-bundle arms are the frozen FU3 behavior — D9)"
            )
        _verify_candidate_composition(candidate_composition, channel)

    # The quantity attestation: digest-verified BEFORE any axis uses it
    # (a tampered attestation produces no derivation input).
    if quantity_attestation is not None:
        quantity_attestation.verify()
        if channel.kind is not SalesUnitKindV2.BUNDLE:
            raise ValueError(
                "a quantity attestation over a non-BUNDLE channel is "
                "contract misuse (the quantity axis is a bundle-only "
                "fact; the non-bundle arms are the frozen FU3 behavior "
                "— D9)"
            )

    # D9 — the non-bundle arms delegate to the frozen FU3 derivation
    # (byte-identical behavior; the FU4 record's form / quantity /
    # source project onto the frozen record for the delegation).
    if channel.kind is not SalesUnitKindV2.BUNDLE:
        frozen_target = None
        if isinstance(target_evidence, TargetSalesUnitEvidenceV2FU4):
            frozen_target = TargetSalesUnitEvidenceV2(
                form=target_evidence.form,
                quantity=target_evidence.quantity,
                source=target_evidence.source,
            )
        elif target_evidence is not None:
            frozen_target = target_evidence
        unit = _fu3_unit_from_channel(channel, frozen_target)
        return unit, (None, None, None, None, None, None)

    # The BUNDLE arm. The target's normalized shape:
    if target_evidence is None:
        target_form = TargetSalesUnitFormV2.SINGLE_UNIT
        target_quantity: int | None = None
        target_state: BundleCompositionStateV2FU4 | None = None
        target_clause: str | None = None
        target_att_digest: str | None = None
    elif isinstance(target_evidence, TargetSalesUnitEvidenceV2FU4):
        _verify_target_evidence(target_evidence)
        target_form = target_evidence.form
        target_quantity = target_evidence.quantity
        target_state = None
        target_clause = None
        target_att_digest = None
        if target_form is TargetSalesUnitFormV2.BUNDLE:
            target_state = target_evidence.composition_state
            target_clause = target_evidence.composition_clause
            if target_evidence.completeness_attestation is not None:
                target_att_digest = (
                    target_evidence.completeness_attestation.attestation_digest
                )
    else:
        # D18 — the frozen target record is read exactly as its fields
        # state: form + count, composition ABSENT (the field does not
        # exist; no implicit upgrade).
        target_form = target_evidence.form
        target_quantity = target_evidence.quantity
        target_state = None
        target_clause = None
        target_att_digest = None
        if target_form is TargetSalesUnitFormV2.BUNDLE:
            target_state = BundleCompositionStateV2FU4.ABSENT
            target_clause = None
            target_att_digest = None

    cand_state = (
        candidate_composition.state
        if candidate_composition is not None
        else BundleCompositionStateV2FU4.ABSENT
    )
    cand_clause = (
        candidate_composition.composition_clause
        if candidate_composition is not None
        else None
    )
    cand_att_digest = (
        candidate_composition.completeness_attestation.attestation_digest
        if candidate_composition is not None
        and candidate_composition.completeness_attestation is not None
        else None
    )

    # U9 — the form rule before any composition is read: a bundle is
    # never pricing-comparable to a non-bundle target (the default
    # single unit included).
    if target_form is not TargetSalesUnitFormV2.BUNDLE:
        return (
            SalesUnitAuthorityV2.CONTRADICTED,
            (
                None,
                cand_state,
                None,
                cand_att_digest,
                None,
                None,
            ),
        )

    # The quantity axis (D20 — a DETERMINED, RECORDED state in every
    # bundle comparison; the published counts side-by-side only, D17a).
    if quantity_attestation is not None:
        # Admissible ONLY over an asymmetric quantity axis (exactly one
        # side publishes a count) — presentation over a both-published
        # or both-unpublished axis is contract misuse.
        asymmetric = (channel.quantity is None) != (target_quantity is None)
        if not asymmetric:
            raise ValueError(
                "a quantity attestation is admissible only over an "
                "asymmetric quantity axis (exactly one side publishes a "
                "count); this axis is both-published or both-unpublished "
                "(contract misuse)"
            )
    candidate_qty = channel.quantity
    target_qty = target_quantity
    if candidate_qty is not None and target_qty is not None:
        axis = (
            BundleQuantityAxisStateV2FU4.CONSISTENT
            if candidate_qty == target_qty
            else BundleQuantityAxisStateV2FU4.CONTRADICTED
        )
    elif candidate_qty is None and target_qty is None:
        axis = BundleQuantityAxisStateV2FU4.BOTH_UNPUBLISHED
    else:
        missing_side = (
            EvidenceSideV2FU4.TARGET
            if candidate_qty is not None
            else EvidenceSideV2FU4.CANDIDATE
        )
        if quantity_attestation is None:
            axis = BundleQuantityAxisStateV2FU4.UNDETERMINED
        elif quantity_attestation.subject_side is not missing_side:
            raise BundleCompositionEvidenceIntegrityError(
                "the quantity attestation does not stand on the "
                "actually-missing side (an attestation whose subject is "
                "not the missing side produces no derivation — fail "
                "closed)"
            )
        else:
            axis = BundleQuantityAxisStateV2FU4.ATTESTED_NOT_MATERIAL
    qty_att_digest = (
        quantity_attestation.attestation_digest
        if quantity_attestation is not None and axis is (
            BundleQuantityAxisStateV2FU4.ATTESTED_NOT_MATERIAL
        )
        else None
    )

    audit = (
        axis,
        cand_state,
        target_state,
        cand_att_digest,
        target_att_digest,
        qty_att_digest,
    )

    # U10–U14 — missing / partial / self-contradicted composition on
    # either side ⇒ UNPROVEN (never PROVEN, and a self-contradiction
    # never contradicts — D8; an asymmetric unattested quantity is
    # never silently immaterial — D20).
    if cand_state is BundleCompositionStateV2FU4.ABSENT:
        return SalesUnitAuthorityV2.UNPROVEN, audit
    if cand_state is BundleCompositionStateV2FU4.PARTIAL:
        return SalesUnitAuthorityV2.UNPROVEN, audit
    if cand_state is BundleCompositionStateV2FU4.CONTRADICTED_PUBLISHED:
        return SalesUnitAuthorityV2.UNPROVEN, audit
    if target_state is BundleCompositionStateV2FU4.ABSENT:
        return SalesUnitAuthorityV2.UNPROVEN, audit
    if target_state is BundleCompositionStateV2FU4.PARTIAL:
        return SalesUnitAuthorityV2.UNPROVEN, audit

    # Both sides textually valid (U15–U21): the two comparison axes —
    # the textual-agreement axis (D16: textual agreement only, never
    # completeness) and the quantity axis (D20).
    cand_established = cand_state is BundleCompositionStateV2FU4.ESTABLISHED
    tgt_established = target_state is BundleCompositionStateV2FU4.ESTABLISHED
    relation = _textual_relation(cand_clause or "", target_clause or "")

    if (
        axis is BundleQuantityAxisStateV2FU4.CONTRADICTED
        and relation is _T_TEXTUAL_AGREEMENT
    ):
        # U16 — a count difference over the same stated composition is
        # a published incompatibility that completeness does not gate
        # (no longer requires both sides ESTABLISHED).
        return SalesUnitAuthorityV2.CONTRADICTED, audit
    if (
        relation is _T_DIFFERENCE_MATERIAL
        and cand_established
        and tgt_established
    ):
        # U17 — complete but materially different composition: the
        # versioned bounded item grammar fully parses BOTH clauses and
        # the multisets differ (the UNDETERMINED quantity gap is
        # recorded, does not shield the contradiction).
        return SalesUnitAuthorityV2.CONTRADICTED, audit
    if (
        relation is _T_TEXTUAL_AGREEMENT
        and cand_established
        and tgt_established
        and axis
        in (
            BundleQuantityAxisStateV2FU4.CONSISTENT,
            BundleQuantityAxisStateV2FU4.BOTH_UNPUBLISHED,
            BundleQuantityAxisStateV2FU4.ATTESTED_NOT_MATERIAL,
        )
    ):
        # U19 / U20 — the CORRECTED intended capability: textually
        # agreed compositions, each side independently attested
        # complete, quantity axis determined.
        return SalesUnitAuthorityV2.PROVEN_EQUIVALENT, audit
    # U15 / U18 / U21 — every other combination: UNPROVEN (a
    # completeness-unknown clause never proves; a missing quantity is
    # never silently immaterial; a difference the grammar cannot
    # establish as material is never a contradiction).
    return SalesUnitAuthorityV2.UNPROVEN, audit


# ---------------------------------------------------------------------------
# The FU4 tier derivation (design section 5.3 — the unchanged machinery,
# the CORRECTED inputs)
# ---------------------------------------------------------------------------


def derive_authority_tier_fu4(
    assessment_v2: IdentityStateAssessmentV2,
    sales_unit_channel: CandidateSalesUnitEvidenceV2,
    evaluation: SemanticEvaluationV2 | None = None,
    context_provenances: frozenset[ContextProvenance] = frozenset(),
    product_evidence: ProductEvidenceProfileV2 | None = None,
    human_review: HumanReviewStateV2 | None = None,
    *,
    target_unit_evidence: (
        TargetSalesUnitEvidenceV2FU4 | TargetSalesUnitEvidenceV2 | None
    ),
    candidate_composition: CandidateBundleCompositionEvidenceV2FU4 | None,
    quantity_attestation: QuantityCompletenessAttestationV2FU4 | None = None,
) -> AuthorityDecisionV2FU4:
    """Derive the bounded workflow authority tier under the S2-A-FU4
    contract (design section 5.3).

    The derivation is the FROZEN S2-A-FU2 derivation (byte-unchanged;
    called, never re-implemented) + the FU3 ``IdentityResolutionBoundV2``
    (delegated — byte-identical) + the FU4 unit derivation (the
    CORRECTED D6 conjunction) + the SAME two restrict-only ceilings on
    the automatic tier (``UNPROVEN`` ⇒ ``CEILING_SALES_UNIT_NOT_PROVEN``;
    ``CONTRADICTED`` ⇒ ``CEILING_SALES_UNIT_CONTRADICTED``;
    ``PROVEN_EQUIVALENT`` ⇒ the automatic tier stands). Result: a NEW
    ``AuthorityDecisionV2FU4`` with the FU3 record's field set PLUS the
    bounded bundle-axis audit fields (the quantity-axis state, the
    composition states, the attestation digests — None for non-bundle
    channels) and the same construction invariants.

    Human overlay precedence (HARD_CONFLICT > HUMAN_CONFIRMED > AI)
    unchanged: a human may confirm a firewall-capped bundle candidate —
    the explicit, auditable path is preserved.

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
            "sales_unit_channel must be CandidateSalesUnitEvidenceV2 "
            f"(the recorded sales-unit channel), got "
            f"{type(sales_unit_channel).__name__}"
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
    unit, (
        axis,
        cand_state,
        tgt_state,
        cand_att_digest,
        tgt_att_digest,
        qty_att_digest,
    ) = _derive_unit_and_audit(
        sales_unit_channel,
        candidate_composition,
        target_unit_evidence,
        quantity_attestation,
    )
    # 3. The restrict-only sales-unit firewall (never lifts; automatic
    #    tier only; a unit is exactly one of the three states).
    tier = frozen_decision.tier
    rules = frozenset(
        _to_fu4_rule(rule) for rule in frozen_decision.fired_rules
    )
    if tier is AuthorityTier.AI_ASSISTED_COMPARABLE:
        if unit is SalesUnitAuthorityV2.UNPROVEN:
            tier = AuthorityTier.NEEDS_REVIEW
            rules = rules | frozenset(
                {AuthorityRuleV2FU4.CEILING_SALES_UNIT_NOT_PROVEN}
            )
        elif unit is SalesUnitAuthorityV2.CONTRADICTED:
            tier = AuthorityTier.NEEDS_REVIEW
            rules = rules | frozenset(
                {AuthorityRuleV2FU4.CEILING_SALES_UNIT_CONTRADICTED}
            )
        # PROVEN_EQUIVALENT: the automatic tier stands.

    return AuthorityDecisionV2FU4(
        tier=tier,
        fired_rules=rules,
        product_evidence_quality=frozen_decision.product_evidence_quality,
        relationship_authority=frozen_decision.relationship_authority,
        identity_resolution_bound=bound,
        sales_unit_authority=unit,
        quantity_axis_state=axis,
        candidate_composition_state=cand_state,
        target_composition_state=tgt_state,
        candidate_completeness_attestation_digest=cand_att_digest,
        target_completeness_attestation_digest=tgt_att_digest,
        quantity_attestation_digest=qty_att_digest,
    )


# ---------------------------------------------------------------------------
# Per-binding dispatch: the FU4 superset (design section 5.4 — T8)
# ---------------------------------------------------------------------------


def derive_authority_tier_for_contract_fu4(
    token: str,
    assessment_v2: IdentityStateAssessmentV2,
    evaluation: SemanticEvaluationV2 | None = None,
    context_provenances: frozenset[ContextProvenance] = frozenset(),
    product_evidence: ProductEvidenceProfileV2 | None = None,
    human_review: HumanReviewStateV2 | None = None,
    *,
    sales_unit_channel: CandidateSalesUnitEvidenceV2 | None = None,
    target_unit_evidence: (
        TargetSalesUnitEvidenceV2FU4 | TargetSalesUnitEvidenceV2 | None
    ) = None,
    candidate_composition: CandidateBundleCompositionEvidenceV2FU4 | None =
        None,
    quantity_attestation: QuantityCompletenessAttestationV2FU4 | None =
        None,
) -> AuthorityDecisionV2FU4 | object:
    """Replay-dispatch one authority derivation under the RECORDED
    authority contract token (S2-A-FU4, the superset dispatch — design
    section 5.4 / T8):

    * ``SEMANTIC_AUTHORITY_V2_S2A_FU2`` ⇒ the UNCHANGED frozen
      derivation (delegated; sales-unit inputs are contract misuse —
      the frozen rule, preserved; composition / attestation inputs are
      FU4-only and refuse under the historical token).
    * ``SEMANTIC_AUTHORITY_V2_S2A_FU3`` ⇒ the frozen
      ``derive_authority_tier_fu3`` (delegated byte-identically through
      the frozen dispatch: the historical token replays exactly as it
      always did; composition / attestation inputs — and the FU4 target
      record — are contract misuse under FU3: the FU3 contract has no
      composition axis, and silently dropping or interpreting them would
      be a re-interpretation of a frozen contract).
    * ``SEMANTIC_AUTHORITY_V2_S2A_FU4`` ⇒ ``derive_authority_tier_fu4``
      (the channel REQUIRED, as under FU3).
    * anything else ⇒ ``UnknownAuthorityContractTokenError`` (reused
      from the frozen FU3 module — the exception is vocabulary);
      non-string ⇒ ``TypeError``.

    The delegation identity (FU4-dispatch arm ⇒ frozen function, same
    inputs ⇒ same output, same exceptions) is a pinned test property
    (design A2 / A7).
    """
    if not isinstance(token, str):
        raise TypeError(
            "token must be str (the recorded authority contract token), "
            f"got {type(token).__name__}"
        )
    if token == AUTHORITY_CONTRACT_VERSION_V2:
        if candidate_composition is not None or quantity_attestation is not None:
            raise ValueError(
                "the frozen S2-A-FU2 contract has no composition axis; "
                "passing composition / attestation inputs under the old "
                "token is contract misuse (fail closed)"
            )
        return _fu3_dispatch(
            token,
            assessment_v2,
            evaluation,
            context_provenances,
            product_evidence,
            human_review,
            sales_unit_channel=sales_unit_channel,
            target_unit_evidence=target_unit_evidence,
        )
    if token == AUTHORITY_CONTRACT_VERSION_V2_FU3:
        if (
            candidate_composition is not None
            or quantity_attestation is not None
            or isinstance(target_unit_evidence, TargetSalesUnitEvidenceV2FU4)
        ):
            raise ValueError(
                "the S2-A-FU3 contract has no composition axis: "
                "composition / attestation inputs (and the FU4 target "
                "record) under FU3 are contract misuse — silently "
                "dropping or interpreting them would be a "
                "re-interpretation of a frozen contract"
            )
        return _fu3_dispatch(
            token,
            assessment_v2,
            evaluation,
            context_provenances,
            product_evidence,
            human_review,
            sales_unit_channel=sales_unit_channel,
            target_unit_evidence=target_unit_evidence,
        )
    if token == AUTHORITY_CONTRACT_VERSION_V2_FU4:
        if sales_unit_channel is None:
            raise ValueError(
                "the S2-A-FU4 contract requires the recorded sales-unit "
                "channel (the V2 input carries it explicitly); an absent "
                "channel is contract misuse and fails closed"
            )
        return derive_authority_tier_fu4(
            assessment_v2,
            sales_unit_channel,
            evaluation,
            context_provenances,
            product_evidence,
            human_review,
            target_unit_evidence=target_unit_evidence,
            candidate_composition=candidate_composition,
            quantity_attestation=quantity_attestation,
        )
    raise UnknownAuthorityContractTokenError(
        "unknown authority contract token; the derivation refuses to "
        "reinterpret a decision under a contract it does not know "
        "(fail closed — the known tokens are the frozen S2-A-FU2 token, "
        "the S2-A-FU3 token, and the S2-A-FU4 token)"
    )


# ---------------------------------------------------------------------------
# Mechanical self-consistency of the FU4 contract data, verified once at
# import (pure data check, no mutable state). If a future edit breaks any
# of these contracts, the module refuses to import.
# ---------------------------------------------------------------------------

if {state.value for state in BundleCompositionStateV2FU4} != {
    "SYNTACTICALLY_VALID",
    "ESTABLISHED",
    "PARTIAL",
    "ABSENT",
    "CONTRADICTED_PUBLISHED",
}:
    raise RuntimeError(
        "the bundle composition state vocabulary is bounded to exactly "
        "the five corrected states (S2-A-FU4)"
    )
if {side.value for side in EvidenceSideV2FU4} != {"CANDIDATE", "TARGET"}:
    raise RuntimeError(
        "the evidence-side vocabulary is bounded to exactly CANDIDATE / "
        "TARGET (S2-A-FU4)"
    )
if {basis.value for basis in CompletenessBasisV2FU4} != {
    "PUBLISHED_COMPLETENESS_STATEMENT",
    "REVIEWED_COMPOSITION_ATTESTATION",
}:
    raise RuntimeError(
        "the completeness-basis vocabulary is bounded to exactly the "
        "published statement + the target-side review attestation "
        "(S2-A-FU4)"
    )
if {
    reason.value for reason in QuantityNonMaterialityReasonV2FU4
} != {
    "SUBJECT_SOURCE_STRUCTURALLY_WITHOUT_BUNDLE_COUNTS",
    "PUBLISHED_COUNT_NOT_UNIT_MULTIPLICITY",
}:
    raise RuntimeError(
        "the quantity non-materiality reason vocabulary is bounded to "
        "exactly the two reviewed reasons (S2-A-FU4)"
    )
if {state.value for state in BundleQuantityAxisStateV2FU4} != {
    "CONSISTENT",
    "BOTH_UNPUBLISHED",
    "ATTESTED_NOT_MATERIAL",
    "CONTRADICTED",
    "UNDETERMINED",
}:
    raise RuntimeError(
        "the bundle quantity-axis state vocabulary is bounded to exactly "
        "the five determined states (S2-A-FU4)"
    )
if {
    basis.value for basis in CandidateCompositionEvidenceBasisV2FU4
} != {"EXTRACTION_RESULT_V1", "RECORDED_CHANNEL"}:
    raise RuntimeError(
        "the candidate composition evidence basis vocabulary is bounded "
        "to exactly the two bases (S2-A-FU4)"
    )
if _COMPLETENESS_MARKERS != (
    "complete list",
    "all items listed",
    "everything included",
    "all included",
    "full contents",
    "nothing else included",
):
    raise RuntimeError(
        "the versioned completeness-marker list is bounded to exactly "
        "the six corrected members (S2-A-FU4; design T9)"
    )
if _COMPLETENESS_MARKER_DELIMITERS != (
    "+",
    ",",
    "&",
    ";",
    "and",
    "—",
    "–",
    "(",
):
    raise RuntimeError(
        "the versioned completeness-marker delimiter set is bounded to "
        "exactly the corrected members (S2-A-FU4; design T9)"
    )
if _INCOMPLETE_MARKERS != (
    "etc.",
    "etc",
    "…",
    "...",
    "and more",
    "+ more",
    "and so on",
    "among others",
    "and other",
):
    raise RuntimeError(
        "the versioned incompleteness-marker list is bounded to exactly "
        "the corrected members (S2-A-FU4)"
    )
if BUNDLE_COMPOSITION_EVIDENCE_VERSION_FU4 != 1:
    raise RuntimeError(
        "the shipped bundle-composition evidence schema is version 1 "
        "(a change is a new version, never a silent edit)"
    )
if {rule.value for rule in AuthorityRuleV2FU4} != {
    rule.value for rule in AuthorityRuleV2FU3
}:
    raise RuntimeError(
        "the FU4 rule vocabulary must mirror the FU3 set exactly (S2-A-"
        "FU4: no new audit rule — D10)"
    )
if {rule.value for rule in AuthorityRuleV2FU4} != (
    {rule.value for rule in AuthorityRuleV2}
    | {
        "CEILING_SALES_UNIT_NOT_PROVEN",
        "CEILING_SALES_UNIT_CONTRADICTED",
    }
):
    raise RuntimeError(
        "the FU4 rule vocabulary must be the frozen S2-A rule values "
        "plus exactly the two restrict-only sales-unit firewall rules "
        "(S2-A-FU4)"
    )
if AUTHORITY_CONTRACT_VERSION_V2_FU4 in (
    AUTHORITY_CONTRACT_VERSION_V2,
    AUTHORITY_CONTRACT_VERSION_V2_FU3,
) or AUTHORITY_CONTRACT_VERSION_V2_FU3 == AUTHORITY_CONTRACT_VERSION_V2:
    raise RuntimeError(
        "the FU4 token must be separately versioned from the frozen "
        "S2-A-FU2 / S2-A-FU3 tokens"
    )
if KNOWN_AUTHORITY_CONTRACT_TOKENS_FU4 != frozenset(
    {
        AUTHORITY_CONTRACT_VERSION_V2,
        AUTHORITY_CONTRACT_VERSION_V2_FU3,
        AUTHORITY_CONTRACT_VERSION_V2_FU4,
    }
):
    raise RuntimeError(
        "the known FU4 authority contract tokens are exactly the frozen "
        "S2-A-FU2 token, the S2-A-FU3 token, and the S2-A-FU4 token"
    )
for _global_name, _global_value in list(globals().items()):
    if _global_name.startswith("__"):
        continue
    if isinstance(_global_value, (dict, list, set)):
        raise RuntimeError(
            f"semantic_authority_fu4 global {_global_name} is a mutable "
            "container; frozen contract data must be runtime-immutable "
            "(S2-A-FU4 discipline)"
        )
