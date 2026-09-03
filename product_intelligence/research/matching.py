"""Deterministic MPN matching and listing rejection (PRODUCT-INTEL.3C).

Given a ``ResearchRequest`` and a ``NormalizedListingObservation``, this module
decides whether the listing carries enough deterministic part-number evidence
to say it belongs to the requested product.

```text
ResearchRequest  +  NormalizedListingObservation
        ↓
  deterministic MPN evidence assessment
        ↓
  ACCEPTED / REJECTED / UNDECIDED  +  IdentityMatchType  +  reason
```

What this module is *not*
-------------------------

**It does not calculate price.** A valid price is not evidence of product
identity, and a missing price does not disprove it. 3C judges identity only.

**It does not import an LLM.** All decisions are deterministic string
comparisons against the existing 2A comparator. No model call, no prompt, no
embedding.

**It does not persist anything.** The assessment is a pure function result.
4A and later phases consume it; no model or migration is added.

**It does not orchestrate.** No search, no fetch, no extraction, no
normalization, no run transition. It takes values it is handed.

Acceptance policy
-----------------

A listing is ACCEPTED on part-number identity **only** when an explicit
manufacturer-part-number field exists and the existing 2A comparator
(``identity.compare_part_numbers``) returns ``EXACT`` or ``NORMALIZED_EXACT``
after the narrowly permitted ``mpn:`` wrapper cleanup.

No other evidence source — SKU, title text, URL — automatically establishes
identity. Unknown beats fabricated certainty.

Evidence sources
----------------

The same character sequence has different semantics depending on which field
published it:

* ``EXPLICIT_MPN_FIELD`` — the page published a structured MPN field
* ``SKU_FIELD`` — the page published a structured SKU field
* ``TITLE_TEXT`` — the requested MPN appears in the product title
* ``NONE`` — no candidate identifier was found

Only an explicit MPN field can produce ACCEPTED.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from product_intelligence.domain import ResearchRequest
from product_intelligence.domain.enums import (
    EvidenceDecision,
    IdentityMatchType,
)
from product_intelligence.research.identity import (
    compare_part_numbers,
)
from product_intelligence.research.listings import ListingObservation
from product_intelligence.research.normalization import (
    NormalizedListingObservation,
)


# ---------------------------------------------------------------------------
# Evidence-source vocabulary
# ---------------------------------------------------------------------------


class EvidenceSource(str, Enum):
    """Where a candidate part-number identifier was found on a listing."""

    EXPLICIT_MPN_FIELD = "EXPLICIT_MPN_FIELD"
    """The page published a structured MPN field."""

    SKU_FIELD = "SKU_FIELD"
    """The page published a structured SKU field."""

    TITLE_TEXT = "TITLE_TEXT"
    """The requested MPN appears in the product title text."""

    NONE = "NONE"
    """No candidate identifier was found."""


# ---------------------------------------------------------------------------
# Rejection-reason vocabulary
# ---------------------------------------------------------------------------


class IdentityRejectionReason(str, Enum):
    """Why a listing was not accepted for price aggregation.

    Small and deliberate: only the reasons this module actually produces.
    Price, currency, availability, and condition issues are *not* identity
    reasons and do not belong here.
    """

    NO_REQUESTED_MPN = "NO_REQUESTED_MPN"
    """The request carries no MPN to compare against."""

    NO_EXPLICIT_MPN_EVIDENCE = "NO_EXPLICIT_MPN_EVIDENCE"
    """The request has an MPN but the listing publishes none."""

    MPN_MISMATCH = "MPN_MISMATCH"
    """The listing publishes an explicit MPN that does not match the request."""

    PARTIAL_MPN_ONLY = "PARTIAL_MPN_ONLY"
    """The listing publishes an MPN that partially overlaps the request."""


# ---------------------------------------------------------------------------
# Narrow MPN-field wrapper cleanup
# ---------------------------------------------------------------------------

# Real recorded page evidence: ``exxactcorp_pm9a3_mz_ql23t800.html`` publishes
# its structured MPN value as ``"mpn:MZ-QL23T800"``.  The ``mpn:`` prefix is
# a field-label wrapper, not part of the identifier itself.  This is the only
# real evidence for a wrapper cleanup rule, so the rule is narrowly scoped to
# exactly this literal prefix on an explicit MPN field only.
#
# This is evidence-source cleanup, not universal part-number normalization.
# ``identity.normalize_part_number`` is deliberately unchanged.
_MPN_WRAPPER_PREFIX = "mpn:"
_MPN_WRAPPER_PREFIX_LEN = len(_MPN_WRAPPER_PREFIX)


def _clean_mpn_field_wrapper(raw_mpn: str) -> str:
    """Strip the ``mpn:`` field-label wrapper from an explicit MPN field.

    Narrow and conservative:

    * Recognises the literal ``mpn:`` prefix only (case-insensitive).
    * Applies to an explicit structured MPN field only — never to a SKU,
      a title, or any other text.
    * Returns the exact raw value when no wrapper is present.

    Does NOT generalise into arbitrary ``key:`` stripping, manufacturer
    prefixes, or arbitrary colon-prefix removal without real fixture evidence.
    """
    stripped = raw_mpn.strip()
    if stripped.lower().startswith(_MPN_WRAPPER_PREFIX):
        return stripped[_MPN_WRAPPER_PREFIX_LEN:]
    return stripped


# ---------------------------------------------------------------------------
# Raw → compared derivation (shared by builder and constructor)             
# ---------------------------------------------------------------------------


def _candidate_compared_from_evidence(
    source: EvidenceSource,
    raw: str,
) -> str:
    """Derive the compared candidate text from the raw evidence.

    This is the single authority for how raw text becomes the text
    actually handed to the 2A comparator (or compared against in
    ``ListingIdentityAssessment.__post_init__``).

    * ``EXPLICIT_MPN_FIELD`` — apply narrow ``mpn:`` wrapper cleanup.
    * ``SKU_FIELD`` / ``TITLE_TEXT`` / ``NONE`` — no transformation.

    Both the normal builder (``assess_listing_identity``) and the
    constructor invariant check call this to prevent drift.
    """
    if source is EvidenceSource.EXPLICIT_MPN_FIELD:
        return _clean_mpn_field_wrapper(raw)
    return raw


# ---------------------------------------------------------------------------
# Narrow PARTIAL classification
# ---------------------------------------------------------------------------


def _classify_partial(
    requested_key: str,
    candidate_key: str,
) -> IdentityMatchType | None:
    """Return ``PARTIAL`` when one key is a strict prefix of the other
    at an explicit preserved identifier boundary.

    Both keys are normalised (structure-preserving) forms from 2A.

    Rules:

    1. Both keys must be non-empty and not equal (equal is handled by 2A).
    2. One must be a strict prefix of the other.
    3. The prefix must end at a boundary in the longer form — that is, the
       character immediately after the prefix in the longer form must be a
       preserved separator (``-``, ``_``, ``/``, ``.``) or a whitespace-derived
       canonical separator (``-``).  A mid-alphanumeric-token prefix like
       ``ABC123`` vs ``ABC1234`` does *not* qualify.

    Returns ``None`` when the rule does not fire, meaning the comparison
    stays ``UNKNOWN`` from 2A's result.
    """
    if not requested_key or not candidate_key:
        return None
    if requested_key == candidate_key:
        return None

    # Determine which is shorter and check strict prefix.
    if len(requested_key) < len(candidate_key):
        short, long_key = requested_key, candidate_key
    elif len(candidate_key) < len(requested_key):
        short, long_key = candidate_key, requested_key
    else:
        # Same length but not equal — not a prefix relation.
        return None

    if not long_key.startswith(short):
        return None

    # The prefix must end at an explicit boundary in the longer form.
    # The character right after the prefix position must be a preserved
    # separator or the canonical separator (a hyphen, which covers both
    # the original hyphen and whitespace-derived boundaries).
    boundary_char = long_key[len(short)]
    if boundary_char not in "-_/.":
        return None

    return IdentityMatchType.PARTIAL


# ---------------------------------------------------------------------------
# Assessment contract
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class ListingIdentityAssessment:
    """The identity decision for one normalised listing.

    Immutable and auditable. A reviewer can trace every field back to the raw
    evidence:

    * ``normalized_listing`` holds the exact ``NormalizedListingObservation``.
    * ``normalized_listing.observation`` holds the exact raw
      ``ListingObservation``.
    * ``candidate_part_number_raw`` is the raw text as published.
    * ``candidate_part_number_compared`` is the text actually handed to the
      2A comparator (after any wrapper cleanup).

    No numeric confidence score is stored.
    """

    # The full normalised observation (which itself carries the raw observation).
    normalized_listing: NormalizedListingObservation

    # The MPN the request was looking for (may be empty for description-only).
    requested_part_number: str

    # The raw candidate identifier found on the listing (may be empty).
    candidate_part_number_raw: str

    # The candidate text actually compared (after wrapper cleanup, may differ
    # from raw when cleanup occurred).
    candidate_part_number_compared: str

    # Where the candidate was found.
    candidate_evidence_source: EvidenceSource

    # The 2A + 3C combined match classification.
    match_type: IdentityMatchType

    # The accept/reject/undecided outcome.
    decision: EvidenceDecision

    # Why it was rejected or undecided. Always present for REJECTED / UNDECIDED.
    rejection_reason: IdentityRejectionReason | None

    def __post_init__(self) -> None:
        """Enforce the 3C state invariants on direct construction.

        ``ListingIdentityAssessment`` is an exported public research contract.
        Its normal builder (``assess_listing_identity``) produces valid states,
        but a frozen dataclass that anyone can construct directly must reject
        impossible combinations at construction time — ``ACCEPTED`` with
        ``MPN_MISMATCH``, ``REJECTED`` with no reason, ``UNDECIDED`` with
        ``EXACT`` match, or any other contradictory mix.

        No override framework is built: an impossible state raises ``ValueError``
        or ``TypeError`` (for structural type violations).
        """
        # -- Basic type validation --
        # These checks catch direct construction with plain strings where
        # enum instances are expected, preventing enum bypass.
        if not isinstance(self.normalized_listing, NormalizedListingObservation):
            raise TypeError(
                f"normalized_listing must be NormalizedListingObservation, "
                f"got {type(self.normalized_listing).__name__}"
            )
        if not isinstance(self.requested_part_number, str):
            raise TypeError(
                f"requested_part_number must be str, "
                f"got {type(self.requested_part_number).__name__}"
            )
        if not isinstance(self.candidate_part_number_raw, str):
            raise TypeError(
                f"candidate_part_number_raw must be str, "
                f"got {type(self.candidate_part_number_raw).__name__}"
            )
        if not isinstance(self.candidate_part_number_compared, str):
            raise TypeError(
                f"candidate_part_number_compared must be str, "
                f"got {type(self.candidate_part_number_compared).__name__}"
            )
        if not isinstance(self.candidate_evidence_source, EvidenceSource):
            raise TypeError(
                f"candidate_evidence_source must be EvidenceSource, "
                f"got {type(self.candidate_evidence_source).__name__}"
            )
        if not isinstance(self.match_type, IdentityMatchType):
            raise TypeError(
                f"match_type must be IdentityMatchType, "
                f"got {type(self.match_type).__name__}"
            )
        if not isinstance(self.decision, EvidenceDecision):
            raise TypeError(
                f"decision must be EvidenceDecision, "
                f"got {type(self.decision).__name__}"
            )
        if self.rejection_reason is not None and not isinstance(
            self.rejection_reason, IdentityRejectionReason
        ):
            raise TypeError(
                f"rejection_reason must be IdentityRejectionReason or None, "
                f"got {type(self.rejection_reason).__name__}"
            )

        decision = self.decision
        match_type = self.match_type
        evidence_source = self.candidate_evidence_source
        rejection = self.rejection_reason

        if decision is EvidenceDecision.ACCEPTED:
            if evidence_source is not EvidenceSource.EXPLICIT_MPN_FIELD:
                raise ValueError(
                    f"ACCEPTED requires EXPLICIT_MPN_FIELD evidence, "
                    f"got {evidence_source.value}; "
                    "only an explicit MPN field can establish identity"
                )
            if match_type not in (
                IdentityMatchType.EXACT,
                IdentityMatchType.NORMALIZED_EXACT,
            ):
                raise ValueError(
                    f"ACCEPTED requires EXACT or NORMALIZED_EXACT match, "
                    f"got {match_type.value}; "
                    "weaker matches do not establish identity"
                )
            if rejection is not None:
                raise ValueError(
                    f"ACCEPTED must have no rejection reason, "
                    f"got {rejection.value}"
                )

            # -- Fabricated-ACCEPTED guard --
            # The stored strings must actually produce the claimed match type
            # through the authoritative 2A comparator. This prevents direct
            # construction of ACCEPTED states that the comparator would never
            # produce (e.g. ABC-123 vs XYZ-999 claiming EXACT).
            assessment_2a = compare_part_numbers(
                self.requested_part_number,
                self.candidate_part_number_compared,
            )
            if not assessment_2a.is_established:
                raise ValueError(
                    f"ACCEPTED requires established identity, "
                    f"but compare_part_numbers({self.requested_part_number!r}, "
                    f"{self.candidate_part_number_compared!r}) "
                    f"returned {assessment_2a.match_type.value}"
                )
            if assessment_2a.match_type is not self.match_type:
                raise ValueError(
                    f"ACCEPTED claims {self.match_type.value} match, "
                    f"but compare_part_numbers({self.requested_part_number!r}, "
                    f"{self.candidate_part_number_compared!r}) "
                    f"returned {assessment_2a.match_type.value}; "
                    "the match type must match the authoritative comparator"
                )

        elif decision is EvidenceDecision.REJECTED:
            if rejection is None:
                raise ValueError(
                    "REJECTED must carry a rejection reason; "
                    "a listing is not rejected without one"
                )

        elif decision is EvidenceDecision.UNDECIDED:
            if match_type is not IdentityMatchType.UNKNOWN:
                raise ValueError(
                    f"UNDECIDED requires UNKNOWN match type, "
                    f"got {match_type.value}"
                )
            if rejection is not IdentityRejectionReason.NO_REQUESTED_MPN:
                raise ValueError(
                    f"UNDECIDED requires NO_REQUESTED_MPN reason, "
                    f"got {rejection.value if rejection is not None else 'None'}"
                )

        # -- NO_REQUESTED_MPN consistency --
        # NO_REQUESTED_MPN must describe an actually absent requested MPN.
        if rejection is IdentityRejectionReason.NO_REQUESTED_MPN:
            if self.requested_part_number:
                raise ValueError(
                    f"NO_REQUESTED_MPN requires an empty requested part number, "
                    f"got {self.requested_part_number!r}"
                )
            if decision is not EvidenceDecision.UNDECIDED:
                raise ValueError(
                    f"NO_REQUESTED_MPN requires UNDECIDED decision, "
                    f"got {decision.value}"
                )

        # -- PARTIAL bidirectional invariant --
        # Forward: PARTIAL match_type -> REJECTED + PARTIAL_MPN_ONLY
        if match_type is IdentityMatchType.PARTIAL:
            if decision is not EvidenceDecision.REJECTED:
                raise ValueError(
                    f"PARTIAL match must be REJECTED, "
                    f"got {decision.value}; "
                    "partial overlap is not price-eligible identity evidence"
                )
            if rejection is not IdentityRejectionReason.PARTIAL_MPN_ONLY:
                raise ValueError(
                    f"PARTIAL match must have PARTIAL_MPN_ONLY reason, "
                    f"got {rejection.value if rejection is not None else 'None'}"
                )

            # -- PARTIAL actual-evidence validation --
            # The stored strings must actually produce PARTIAL through
            # 2A -> UNKNOWN followed by _classify_partial -> PARTIAL.
            assessment_2a = compare_part_numbers(
                self.requested_part_number,
                self.candidate_part_number_compared,
            )
            if assessment_2a.match_type is not IdentityMatchType.UNKNOWN:
                raise ValueError(
                    f"PARTIAL requires 2A to return UNKNOWN first, "
                    f"but compare_part_numbers({self.requested_part_number!r}, "
                    f"{self.candidate_part_number_compared!r}) "
                    f"returned {assessment_2a.match_type.value}"
                )
            actual_partial = _classify_partial(
                assessment_2a.normalized_requested_part_number,
                assessment_2a.normalized_candidate_part_number,
            )
            if actual_partial is not IdentityMatchType.PARTIAL:
                raise ValueError(
                    f"PARTIAL requires _classify_partial to confirm PARTIAL, "
                    f"but it returned {actual_partial}"
                )

        # Reverse: PARTIAL_MPN_ONLY -> PARTIAL match_type + REJECTED
        elif rejection is IdentityRejectionReason.PARTIAL_MPN_ONLY:
            if match_type is not IdentityMatchType.PARTIAL:
                raise ValueError(
                    f"PARTIAL_MPN_ONLY requires PARTIAL match type, "
                    f"got {match_type.value}"
                )
            if decision is not EvidenceDecision.REJECTED:
                raise ValueError(
                    f"PARTIAL_MPN_ONLY requires REJECTED decision, "
                    f"got {decision.value}"
                )

        # -- Evidence provenance: source and raw must come from the
        #    underlying ListingObservation, not be fabricated.          --
        # This is the upstream check: even if raw->compared->2A->decision
        # are internally consistent, the evidence must actually exist on
        # the listing. Otherwise a future 4A could consume a price from
        # listing A while identity evidence was invented independently.
        observation = self.normalized_listing.observation
        expected_source, expected_raw = _find_evidence(
            observation,
            self.requested_part_number,
        )
        if self.candidate_evidence_source is not expected_source:
            raise ValueError(
                f"candidate_evidence_source {self.candidate_evidence_source.value} "
                f"does not match the underlying listing's strongest evidence "
                f"({expected_source.value}); "
                "an assessment cannot claim evidence the listing did not publish"
            )
        if self.candidate_part_number_raw != expected_raw:
            raise ValueError(
                f"candidate_part_number_raw {self.candidate_part_number_raw!r} "
                f"does not match the underlying listing's published value "
                f"({expected_raw!r}) for source {self.candidate_evidence_source.value}; "
                "an assessment cannot fabricate raw evidence"
            )

        # -- Raw -> compared audit chain (all sources) --
        # For EXPLICIT_MPN_FIELD, the compared value derives from the raw
        # through narrow mpn: wrapper cleanup. For all other sources,
        # compared must equal raw — no normalization or mutation is permitted.
        expected_compared = _candidate_compared_from_evidence(
            evidence_source, self.candidate_part_number_raw
        )

        if self.candidate_part_number_compared != expected_compared:
            raise ValueError(
                f"{evidence_source.value} candidate_part_number_compared "
                f"{self.candidate_part_number_compared!r} does not derive "
                f"from raw {self.candidate_part_number_raw!r} "
                f"(expected {expected_compared!r}{" after wrapper cleanup" if evidence_source is EvidenceSource.EXPLICIT_MPN_FIELD else ""})"
            )


# ---------------------------------------------------------------------------
# Evidence-source detection
# ---------------------------------------------------------------------------


def _find_evidence(
    observation: ListingObservation,
    requested_mpn: str,
) -> tuple[EvidenceSource, str]:
    """Return the strongest evidence source and the candidate text.

    Priority order:

    1. Explicit MPN field — the page published a structured MPN.
    2. SKU field — the page published a structured SKU (retailer internal or
       manufacturer public; 3C has no general source-specific knowledge to
       distinguish).
    3. Title text — the requested MPN appears as a token in the product title
       (only recorded, never used for automatic acceptance).
    4. None.

    Returns ``(source, candidate_text)`` where candidate text is ``""`` when
    the source is ``NONE``.
    """
    # 1. Explicit MPN field.
    if observation.manufacturer_part_number_text is not None:
        return EvidenceSource.EXPLICIT_MPN_FIELD, observation.manufacturer_part_number_text

    # 2. SKU field.
    if observation.sku_text is not None:
        return EvidenceSource.SKU_FIELD, observation.sku_text

    # 3. Title text — only if there's something to look for.
    if observation.product_title is not None and requested_mpn:
        # Check if the requested MPN appears as a standalone token in the
        # title. We use a conservative substring check: the MPN appears as a
        # word boundary-delimited token. This is for recording evidence only,
        # never for automatic acceptance.
        title = observation.product_title
        mpn = requested_mpn
        # Simple token check: MPN appears at start/end or between
        # non-alphanumeric characters.
        import re

        pattern = r"(?<![A-Za-z0-9])" + re.escape(mpn) + r"(?![A-Za-z0-9])"
        if re.search(pattern, title):
            return EvidenceSource.TITLE_TEXT, requested_mpn

    return EvidenceSource.NONE, ""


# ---------------------------------------------------------------------------
# Public entry points
# ---------------------------------------------------------------------------


def assess_listing_identity(
    request: ResearchRequest,
    normalized_listing: NormalizedListingObservation,
) -> ListingIdentityAssessment:
    """Decide whether a normalised listing belongs to the requested product.

    Pure and deterministic. Takes a canonical request and one normalised
    observation, returns an immutable assessment with full audit trail.

    No I/O, no Django, no provider call, no clock, no environment access, and
    no LLM call. The existing 2A comparator owns EXACT / NORMALIZED_EXACT.
    """
    observation = normalized_listing.observation
    requested_mpn = request.manufacturer_part_number

    # --- Find the strongest evidence ---
    evidence_source, candidate_raw = _find_evidence(observation, requested_mpn)

    # --- No requested MPN: undecided ---
    if not requested_mpn:
        candidate_compared = _candidate_compared_from_evidence(
            evidence_source, candidate_raw
        )
        return ListingIdentityAssessment(
            normalized_listing=normalized_listing,
            requested_part_number="",
            candidate_part_number_raw=candidate_raw,
            candidate_part_number_compared=candidate_compared,
            candidate_evidence_source=evidence_source,
            match_type=IdentityMatchType.UNKNOWN,
            decision=EvidenceDecision.UNDECIDED,
            rejection_reason=IdentityRejectionReason.NO_REQUESTED_MPN,
        )

    # --- Request has MPN, listing has no explicit MPN ---
    if evidence_source is EvidenceSource.NONE:
        return ListingIdentityAssessment(
            normalized_listing=normalized_listing,
            requested_part_number=requested_mpn,
            candidate_part_number_raw="",
            candidate_part_number_compared="",
            candidate_evidence_source=EvidenceSource.NONE,
            match_type=IdentityMatchType.UNKNOWN,
            decision=EvidenceDecision.REJECTED,
            rejection_reason=IdentityRejectionReason.NO_EXPLICIT_MPN_EVIDENCE,
        )

    # --- SKU or title only: never automatically accepted ---
    if evidence_source in (EvidenceSource.SKU_FIELD, EvidenceSource.TITLE_TEXT):
        return ListingIdentityAssessment(
            normalized_listing=normalized_listing,
            requested_part_number=requested_mpn,
            candidate_part_number_raw=candidate_raw,
            candidate_part_number_compared=candidate_raw,
            candidate_evidence_source=evidence_source,
            match_type=IdentityMatchType.UNKNOWN,
            decision=EvidenceDecision.REJECTED,
            rejection_reason=IdentityRejectionReason.NO_EXPLICIT_MPN_EVIDENCE,
        )

    # --- Explicit MPN field: compare with 2A ---
    assert evidence_source is EvidenceSource.EXPLICIT_MPN_FIELD

    # Apply narrow wrapper cleanup.
    candidate_compared = _clean_mpn_field_wrapper(candidate_raw)

    # Run the existing 2A comparator.
    assessment_2a = compare_part_numbers(requested_mpn, candidate_compared)

    # If the explicit field carried no part-number content after cleanup
    # (e.g. "mpn:" -> "", or structure-only value), treat it as though no
    # explicit MPN were published rather than inventing a mismatch.
    if not assessment_2a.normalized_candidate_part_number:
        return ListingIdentityAssessment(
            normalized_listing=normalized_listing,
            requested_part_number=requested_mpn,
            candidate_part_number_raw=candidate_raw,
            candidate_part_number_compared=candidate_compared,
            candidate_evidence_source=evidence_source,
            match_type=IdentityMatchType.UNKNOWN,
            decision=EvidenceDecision.REJECTED,
            rejection_reason=IdentityRejectionReason.NO_EXPLICIT_MPN_EVIDENCE,
        )

    if assessment_2a.is_established:
        # EXACT or NORMALIZED_EXACT from 2A — accepted.
        return ListingIdentityAssessment(
            normalized_listing=normalized_listing,
            requested_part_number=requested_mpn,
            candidate_part_number_raw=candidate_raw,
            candidate_part_number_compared=candidate_compared,
            candidate_evidence_source=evidence_source,
            match_type=assessment_2a.match_type,
            decision=EvidenceDecision.ACCEPTED,
            rejection_reason=None,
        )

    # --- 2A returned UNKNOWN: check for narrow PARTIAL ---
    partial_type = _classify_partial(
        assessment_2a.normalized_requested_part_number,
        assessment_2a.normalized_candidate_part_number,
    )

    if partial_type is IdentityMatchType.PARTIAL:
        return ListingIdentityAssessment(
            normalized_listing=normalized_listing,
            requested_part_number=requested_mpn,
            candidate_part_number_raw=candidate_raw,
            candidate_part_number_compared=candidate_compared,
            candidate_evidence_source=evidence_source,
            match_type=IdentityMatchType.PARTIAL,
            decision=EvidenceDecision.REJECTED,
            rejection_reason=IdentityRejectionReason.PARTIAL_MPN_ONLY,
        )

    # --- UNKNOWN, no partial — rejected ---
    return ListingIdentityAssessment(
        normalized_listing=normalized_listing,
        requested_part_number=requested_mpn,
        candidate_part_number_raw=candidate_raw,
        candidate_part_number_compared=candidate_compared,
        candidate_evidence_source=evidence_source,
        match_type=IdentityMatchType.UNKNOWN,
        decision=EvidenceDecision.REJECTED,
        rejection_reason=IdentityRejectionReason.MPN_MISMATCH,
    )


def assess_listing_identities(
    request: ResearchRequest,
    normalized_listings: tuple[NormalizedListingObservation, ...],
) -> tuple[ListingIdentityAssessment, ...]:
    """Assess identity for a sequence of normalised listings.

    Applies ``assess_listing_identity`` to each observation in order.
    Returns a tuple of assessments — both accepted and rejected, in the
    same order as the input.

    Not orchestration: no fetching, no searching, no persistence.
    """
    return tuple(
        assess_listing_identity(request, listing)
        for listing in normalized_listings
    )


# ---------------------------------------------------------------------------
# Human-review eligibility predicate
# ---------------------------------------------------------------------------


def is_human_review_eligible_assessment(
    assessment: ListingIdentityAssessment,
) -> bool:
    """Return True if this assessment is eligible for human review.

    This mirrors the frozen FU3B semantic-eligible assessment states — the
    ONLY assessments that can appear as ``AiAssistedMatchResult.original_assessment``
    in a real execution snapshot.

    Eligible (returns True):

    - REJECTED + NO_EXPLICIT_MPN_EVIDENCE + TITLE_TEXT
    - REJECTED + NO_EXPLICIT_MPN_EVIDENCE + SKU_FIELD
    - REJECTED + PARTIAL_MPN_ONLY

    NOT eligible (returns False):

    - ACCEPTED
    - UNDECIDED
    - REJECTED + MPN_MISMATCH
    - REJECTED + NO_EXPLICIT_MPN_EVIDENCE + NONE
    - any other unsupported state

    This is a pure predicate. It does not import any execution, semantic,
    or persistence module.
    """
    if assessment.decision is not EvidenceDecision.REJECTED:
        return False

    if assessment.rejection_reason is IdentityRejectionReason.PARTIAL_MPN_ONLY:
        return True

    if assessment.rejection_reason is IdentityRejectionReason.NO_EXPLICIT_MPN_EVIDENCE:
        if assessment.candidate_evidence_source in (
            EvidenceSource.TITLE_TEXT,
            EvidenceSource.SKU_FIELD,
        ):
            return True

    return False
