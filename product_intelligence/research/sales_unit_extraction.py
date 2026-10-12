"""Bounded sales-unit evidence extraction (PRODUCT-INTEL.Q3-B5-P2).

The Q3-B4 authority-boundary decision (``docs/PRODUCT_INTEL_SEMANTIC_V2_
Q3B4_AUTHORITY_BOUNDARY_DECISION.md``, section 4.4 / 5.1 / 9, roadmap row
P2) identifies packaging extraction as the independent observability phase
of the approved Option D firewall: the extractor publishes the bounded
packaging / sales-unit field with source provenance, so that the
separately versioned sales-unit authority derivation (the recorded-channel
function of the firewall contract) derives from RECORDED published
evidence instead of a channel that is always ``UNAVAILABLE`` on live
pages.

This module is the PURE EXTRACTION AND VALIDATION LAYER of that phase. It is
deliberately bounded:

* **Input** — one ``ListingObservation`` (one offer as one page published
  it, the frozen 3A contract) plus, when a source publishes one, the
  explicit page-published structured packaging field value (plain text as
  published). Those are the only fields the extractor may read. The
  identifier fields (MPN / SKU) are examined ONLY to record that a
  packaging-like token in them was deliberately set aside (identifier
  fields are never packaging evidence). The opaque ``raw_reference`` is
  never read or parsed (AD-040: no business rule may parse it). No other
  observation field, no price, no availability, no description text, and
  no model output is an input.
* **Output** — a versioned, immutable, self-verifying
  ``SalesUnitExtractionResult`` (schema v1) that distinguishes, with
  explicit provenance for every cue:

  - ``OBSERVED_UNAMBIGUOUS`` — the published cues establish exactly one
    bounded commercial unit (kind + quantity where published) and no
    independently unresolved ambiguous cue of ANY kind is present (a
    same-kind ambiguous cue is admitted only as a genuine duplicate /
    subsumed cue deterministically proven by the exact published spans
    — the documented subsumption rule of the Q3-B5-P2-FU1 correction);
  - ``CONTRADICTED_CUES`` — two or more published cues establish
    incompatible units (different kinds, or different published
    quantities within a kind); every side is recorded with provenance;
  - ``AMBIGUOUS_CUE`` — a packaging cue is present but cannot be bound to
    a bounded observation (a pack without a count, a bundle without
    published contents — a bare bundle word or a bundle count alone,
    since a published count is not the complete identity of a bundle —
    a non-canonical / capacity-attached number, a structured field with
    no packaging vocabulary, or an established claim blocked by an
    independently unresolved ambiguous cue of any kind, including the
    established kind);
  - ``NO_PACKAGING_PUBLISHED`` — no packaging cue is present in any
    examined published field (the recorded absence).

* **Fail-closed mapping** — ``sales_unit_channel_from_extraction`` maps a
  result onto the frozen S2-C-FU1 recorded channel
  (``CandidateSalesUnitEvidenceV2``) WITHOUT changing that contract:
  ``OBSERVED_UNAMBIGUOUS`` becomes an ``OBSERVED`` channel (kind +
  quantity where published + the exact published cue text as raw detail +
  the cue's recorded provenance source); EVERY other state maps to the
  canonical ``UNAVAILABLE`` state. The frozen channel has no ambiguous or
  contradicted state, and recording either side of a contradiction as
  ``OBSERVED`` would be an unsafe workaround — the fail-closed mapping
  keeps both sides in the versioned extraction result (audit) and in the
  channel only the recorded absence (FU3 then derives UNPROVEN, never
  PROVEN_EQUIVALENT, never CONTRADICTED). A future versioned input schema
  may add explicit channel conflict states; that is a separately
  approval-gated decision and is NOT made here.
* **Never inferred** — no sales-unit value is derived from price,
  availability, condition, seller, an exact MPN, one listing, one price,
  or one product image. A missing packaging field is
  ``NO_PACKAGING_PUBLISHED`` (recorded absence), never SINGLE_UNIT.
  Specification quantities are not sales quantities: the frozen cue
  vocabulary requires an explicit packaging word (pack / tray / bundle /
  factory pack / oem pack / oem tray / single unit / 1 unit / N-unit
  compound), so ``4 TB`` capacity, ``2U`` / ``1U`` chassis height,
  ``Dual-Port`` networking, ``8-channel`` memory, ``PCIe 4.0 x4``, ``1 DWPD``,
  and product revision numbers never match. A quantity token attached to a
  capacity unit (``pack of 4TB``), a non-canonical number (``pack of 3.84``,
  ``pack of 04``, ``pack of 100000``), a bare ``pack`` / ``bundle`` word,
  or a bundle count without published contents (``bundle of N`` /
  ``N-unit bundle`` — a published count is not the complete identity of
  a bundle; its composition is unverified) is an AMBIGUOUS cue (recorded,
  never established; the count stays verbatim in the cue text and is
  never bound to a quantity).
* **Provenance** — every cue records the examined field, its bounded
  provenance source (the frozen ``CandidateEvidenceSourceV2`` members
  ``LISTING_TITLE`` / ``PUBLISHED_STRUCTURED_FIELD`` — no member is a model
  claim, and the other two members are rejected at construction), the full
  field value as published, and the exact cue text with its span (verified
  to be a verbatim substring of the field value). The result is bound to
  the exact examined input by an ``input_digest`` (SHA-256 over the
  canonical named-field document; ``raw_reference`` deliberately excluded)
  and self-verified by a ``result_digest`` (SHA-256 over the canonical
  result minus the digest itself). The channel mapping re-verifies the
  result digest before mapping: a hand-forged or tampered result produces
  no channel (``SalesUnitExtractionIntegrityError``).
* **No authority, no wiring** — the extraction result is commercial
  observation evidence. It cannot ground the authority-side
  ``ProductEvidenceProfileV2`` (no member of the candidate source
  vocabulary is a model claim, and the authority builder has no extraction
  input), it grants no pricing authority, and it is referenced by no live
  path: the frozen live input construction (S2-C-FU1) still records
  ``UNAVAILABLE`` from the main-flow extractor, and the separately gated
  integration proposal (recorded in the phase documentation) is the only
  path by which an extracted channel may later reach a recorded V2 input.
  ``V2_AUTHORITY_QUALIFIED`` stays False.

Pure research-layer module: stdlib + the research package's public surface
(the frozen 3A observation contract, the frozen S2-C-FU1 channel and
provenance vocabulary). No Django, no I/O, no clock, no network, no LLM,
no mutable global state, no vendor names.
"""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass
from enum import Enum
from typing import Final

from product_intelligence.research.listings import ListingObservation
from product_intelligence.research.semantic_v2 import (
    CandidateEvidenceSourceV2,
    CandidateSalesUnitEvidenceV2,
    PackagingEvidenceStateV2,
    SALES_UNIT_EVIDENCE_UNAVAILABLE,
    SalesUnitKindV2,
)

__all__ = [
    "SALES_UNIT_EXTRACTION_SCHEMA_VERSION",
    "SalesUnitCueDisposition",
    "SalesUnitCueField",
    "SalesUnitCueReason",
    "SalesUnitCueV1",
    "SalesUnitExtractionIntegrityError",
    "SalesUnitExtractionResult",
    "SalesUnitExtractionState",
    "SalesUnitIdentifierFieldNoteV1",
    "extract_and_map_sales_unit_evidence",
    "extract_sales_unit_evidence",
    "sales_unit_channel_from_extraction",
]


#: The versioned identity of this extraction contract (schema v1). A
#: future change to the cue table, the state vocabulary, or the mapping
#: rule is a NEW schema version, never a silent edit of v1.
SALES_UNIT_EXTRACTION_SCHEMA_VERSION: Final[int] = 1


class SalesUnitExtractionState(str, Enum):
    """The bounded outcome states of one extraction (schema v1).

    Exactly four states; there is no state that says "probably a single
    unit" and no state that silently drops a published contradiction.
    """

    NO_PACKAGING_PUBLISHED = "NO_PACKAGING_PUBLISHED"
    """No packaging cue is present in any examined published field. This
    is the RECORDED ABSENCE: the honest state where nothing is published,
    and the only extraction state a silent multi-pack can have. It maps to
    the frozen channel's ``UNAVAILABLE`` (FU3: UNPROVEN — absence is never
    single unit, never equivalence)."""

    OBSERVED_UNAMBIGUOUS = "OBSERVED_UNAMBIGUOUS"
    """The published cues establish exactly one bounded commercial unit:
    a single kind, at most one published quantity, and no independently
    unresolved ambiguous cue of ANY kind present (Q3-B5-P2-FU1: matching
    packaging kinds alone never prove that an ambiguous cue describes the
    same commercial unit). A same-kind ambiguous cue is admitted only as
    a genuine duplicate / subsumed cue, deterministically proven by the
    exact published spans (the documented subsumption rule: same
    examined field, the ambiguous cue's span contained in the established
    cue's span, same kind). Maps to the frozen channel's ``OBSERVED``
    state with the cue's recorded provenance."""

    AMBIGUOUS_CUE = "AMBIGUOUS_CUE"
    """A packaging cue is present but cannot be bound to a bounded
    observation (pack without count, bundle without published contents
    — a bare bundle word or a bundle count alone — non-canonical /
    capacity-attached quantity, structured field with no packaging
    vocabulary, or an established claim blocked by an independently
    unresolved ambiguous cue of any kind, including the established
    kind). Every such cue is recorded with its reason. Maps to the frozen
    channel's ``UNAVAILABLE`` (fail closed: the channel cannot represent
    ambiguity, and guessing a value from it would be an inference)."""

    CONTRADICTED_CUES = "CONTRADICTED_CUES"
    """Two or more published cues establish incompatible commercial units
    (different kinds, or different published quantities within a kind —
    e.g. a structured field saying single unit and the title saying pack
    of four). EVERY side is recorded with its full provenance. Maps to the
    frozen channel's ``UNAVAILABLE`` (fail closed: neither side may be
    presented as THE recorded unit)."""


class SalesUnitCueDisposition(str, Enum):
    """Bounded disposition of one recorded cue."""

    ESTABLISHED = "ESTABLISHED"
    """The cue establishes a bounded commercial unit (kind, plus the
    published quantity where the phrase carries one)."""

    AMBIGUOUS = "AMBIGUOUS"
    """The cue names packaging but cannot be bound to a bounded
    observation (the reason records which bounded rule it missed)."""


class SalesUnitCueField(str, Enum):
    """The bounded set of fields the extractor may examine for packaging
    cues. Exactly two members — there is no model-claim member and no
    raw-reference member; a cue from any other position cannot exist in
    the schema. The declaration order is the canonical examination order
    (the deliberately published structured field precedes the raw title).
    """

    STRUCTURED_PACKAGING_FIELD = "STRUCTURED_PACKAGING_FIELD"
    """An explicit packaging / sales-unit field the page deliberately
    published as structured data (the value is plain text as published).
    Today the main-flow extractor carries no such field; a future
    extractor or reviewed source fills the same bounded input."""

    PRODUCT_TITLE = "PRODUCT_TITLE"
    """The page-published listing title (RAW observation text; a cue is a
    verbatim, span-bound substring of it)."""


class SalesUnitCueReason(str, Enum):
    """The bounded reasons a cue is recorded as ambiguous (schema v1).
    ``None`` (no reason) is the established case; an ambiguous cue always
    carries exactly one of these."""

    PACK_WITHOUT_COUNT = "PACK_WITHOUT_COUNT"
    """A ``pack`` word with no published count (a pack without a count is
    outside the frozen channel contract)."""

    BUNDLE_WITHOUT_CONTENTS = "BUNDLE_WITHOUT_CONTENTS"
    """The bundle's composition is not published: a bare ``bundle`` word,
    or a bundle with a published count but no contents (``bundle of N`` /
    ``N-unit bundle``). A published count alone is not the complete
    identity of a bundle (the bundle's commercial unit is its composition,
    never just its count — two bundles with equal counts and different
    contents are not commercially equivalent; Q3-B5-P2-FU1). The approved
    2.1 design's P6 shape: unclear wording is unproven packaging
    evidence, never an established conflict. The count stays verbatim in
    the cue text and is never bound to a quantity."""

    NON_CANONICAL_QUANTITY = "NON_CANONICAL_QUANTITY"
    """The number after the packaging word is not a canonical count
    (decimal, leading zero, or above the bounded 99999)."""

    CAPACITY_ATTACHED_QUANTITY = "CAPACITY_ATTACHED_QUANTITY"
    """The number after the packaging word is immediately attached to a
    capacity unit (``pack of 4TB``): it is a specification quantity, not a
    sales quantity (the capacity-vs-count distinction is not resolvable
    deterministically from the attached form)."""

    NO_PACKAGING_VOCABULARY = "NO_PACKAGING_VOCABULARY"
    """A structured packaging field published a value that contains no
    bounded packaging vocabulary (the page published something in a
    packaging position; the extractor does not interpret it)."""


#: The exact provenance source a cue may carry per examined field (the
#: frozen S2-C-FU1 vocabulary). No member is a model claim; the other two
#: members of ``CandidateEvidenceSourceV2`` (SPECIFICATION_TEXT,
#: REVIEWED_PRODUCT_CONTEXT) are NOT extractor outputs: the main flow
#: carries no specification text, and a reviewed product context is not
#: extracted from a page. A cue presenting either is rejected at
#: construction. (A tuple of pairs, not a dict: the module carries no
#: mutable global state.)
_CUE_SOURCE_PAIRS: Final[tuple[tuple[SalesUnitCueField, CandidateEvidenceSourceV2], ...]] = (
    (SalesUnitCueField.PRODUCT_TITLE, CandidateEvidenceSourceV2.LISTING_TITLE),
    (
        SalesUnitCueField.STRUCTURED_PACKAGING_FIELD,
        CandidateEvidenceSourceV2.PUBLISHED_STRUCTURED_FIELD,
    ),
)


def _cue_source_for(field: SalesUnitCueField) -> CandidateEvidenceSourceV2:
    """The bounded provenance source for one examined field (import-
    self-checked to cover exactly the field vocabulary)."""
    for pair_field, pair_source in _CUE_SOURCE_PAIRS:
        if pair_field is field:
            return pair_source
    raise ValueError(
        f"no extractor provenance source is defined for field {field!r}"
    )


#: The bounded count: a canonical positive integer 1..99999 (no leading
#: zero, no decimal point, no surrounding digits). Anything else after a
#: packaging word is non-canonical (never a guessed count).
_QUANTITY: Final[str] = r"(?<![0-9.])([1-9][0-9]{0,4})(?![0-9.])"

#: Capacity units that turn an attached number into a specification
#: quantity rather than a sales count (checked in the cue handler, not in
#: the pattern, so the span stays the published phrase). Decimal and
#: binary notations alike.
_CAPACITY_ATTACHED = re.compile(r"(?i)^(TB|TiB|GB|GiB|PB|PiB|MB|MiB)(?![A-Za-z])")

#: The frozen cue table (schema v1). One ordered master scan per field:
#: Python's alternation is ordered, and the MOST SPECIFIC phrase forms
#: come first so a compound cue consumes its text before a shorter
#: alternative could re-match part of it. Every alternative is an exact
#: published phrase shape with an explicit packaging word — a bare number
#: (capacity, chassis height, lane count, channel count, DWPD rate,
#: revision digit) can never match, because no packaging word is present.
_CUE_MASTER = re.compile(
    r"(?xi)"
    # 1. N-unit compounds: "10-unit factory pack", "4 unit pack", ...
    #    (the count + the complete kind phrase, so "1-unit bundle" is a
    #    bundle, never the single-unit phrase "1 unit"; a bare "1 unit
    #    SSD" still reaches the single-unit alternative because no kind
    #    word follows). A "N-unit bundle" publishes a count WITHOUT the
    #    composition: the bundle's identity is its contents, never just
    #    its count, so the cue is ambiguous (BUNDLE_WITHOUT_CONTENTS),
    #    never established (Q3-B5-P2-FU1).
    r"(?P<nu_q>" + _QUANTITY + r")\s*[- ]\s*unit\s+"
    r"(?P<nu_kind>factory\s+pack|oem\s+pack|oem\s+tray|tray|bundle|pack)\b"
    r"|"
    # 2. factory / oem compounds with "of N": "factory pack of 10", ...
    #    (a sentence-final period is not part of the number: the group
    #    must not end with a dot).
    r"\b(?P<fo_kind>factory\s+pack|oem\s+pack|oem\s+tray)\s+of\s+"
    r"(?P<fo_num>[0-9][0-9.]*(?<![.]))"
    r"|"
    # 3. bare factory / oem compounds: "Factory Pack", "OEM Tray"
    r"\b(?P<fo_bare>factory\s+pack|oem\s+pack|oem\s+tray)\b"
    r"|"
    # 4. "pack of N" / "tray of N" / "bundle of N" (N captured for the
    #    canonical check: decimal / leading-zero / oversized numbers are
    #    NON_CANONICAL, attached capacity units are CAPACITY_ATTACHED;
    #    a sentence-final period is not part of the number). A
    #    "bundle of N" publishes a count WITHOUT the composition:
    #    ambiguous (BUNDLE_WITHOUT_CONTENTS), never established
    #    (Q3-B5-P2-FU1 — a published count is not the complete identity
    #    of a bundle).
    r"\b(?P<of_kind>pack|tray|bundle)\s+of\s+(?P<of_num>[0-9][0-9.]*(?<![.]))"
    r"|"
    # 5. "N-pack" / "N pack" (retail pack of N; the count is canonical by
    #    the pattern's own guards; not capacity-attached).
    r"(?P<npack_q>" + _QUANTITY + r")\s*[-\s]\s*pack\b(?!(?:TB|GB|PB|MB)\b)"
    r"|"
    # 5b. a non-canonical count before "pack" (leading zero, or above the
    #     bounded 99999): the page published a count-like token that is
    #     not canonical — recorded as NON_CANONICAL (never established).
    r"(?P<npack_bad>(?<![0-9.])(0[0-9]{1,6}|[0-9]{6,7}))[ -]pack\b"
    r"|"
    # 6. bundle with an explicit contents marker: "bundle: X + Y",
    #    "bundle (X + Y)".
    r"\b(?P<bundle_mark>bundle)\s*[:(]"
    r"|"
    # 7. bare tray: "(tray)" is an established tray cue (the approved 2.1
    #    design's raw-cue example); the quantity is optional when
    #    published.
    r"\b(?P<tray_bare>tray)\b"
    r"|"
    # 8. single retail unit phrases: "single unit", "1 unit", "1-unit".
    r"\b(?P<single>single[- ]unit|1[- ]unit)\b"
    r"|"
    # 9. bare pack (no count): ambiguous, never established.
    r"\b(?P<pack_bare>pack)\b"
    r"|"
    # 10. bare bundle (no count, no contents marker): ambiguous.
    r"\b(?P<bundle_bare>bundle)\b"
)

#: Packaging-vocabulary tokens the IDENTIFIER fields (MPN / SKU) are
#: scanned for, ONLY to record that they were set aside. A deliberately
#: looser match than the cue table (no left word boundary): a seller SKU
#: like ``4PACK-SSD-001`` names a packaging-like token that must be
#: recorded as out-of-scope evidence, not silently invisible.
_IDENTIFIER_TOKEN = re.compile(
    r"(?i)(pack|tray|bundle|oem|factory|kit|case)(?![a-z])"
)

#: The observed fields the input digest is computed over — every named
#: field of the frozen 3A contract EXCEPT the opaque ``raw_reference``
#: (no business rule may parse it; two observations identical in every
#: named field are the same extraction input whatever their raw
#: reference).
_DIGEST_FIELD_NAMES: Final[tuple[str, ...]] = (
    "availability_text",
    "brand_text",
    "condition_text",
    "currency_text",
    "manufacturer_part_number_text",
    "offer_url_text",
    "price_text",
    "product_title",
    "sku_text",
    "source_url",
)


class SalesUnitExtractionIntegrityError(ValueError):
    """A presented extraction result fails its own integrity checks
    (hand-forged fields, a tampered digest, or a cue text that its field
    never published). Fail closed: the result produces no channel."""


@dataclass(frozen=True)
class SalesUnitCueV1:
    """One recorded packaging cue with its full provenance (schema v1).

    ``cue_text`` is the exact published phrase (original case) and is
    verified to be the verbatim substring ``raw_field_value[cue_start:
    cue_end]`` — a cue cannot claim text its field never published. The
    provenance ``source`` is bounded to the two extractor members of the
    frozen S2-C-FU1 vocabulary (``LISTING_TITLE`` for title cues,
    ``PUBLISHED_STRUCTURED_FIELD`` for structured-field cues): no member
    is a model claim, and the other two vocabulary members are rejected
    at construction (a forged / model-generated cue has no representable
    source).
    """

    field: SalesUnitCueField
    source: CandidateEvidenceSourceV2
    raw_field_value: str
    cue_text: str
    cue_start: int
    cue_end: int
    kind: SalesUnitKindV2 | None
    quantity: int | None
    disposition: SalesUnitCueDisposition
    reason: SalesUnitCueReason | None

    def __post_init__(self) -> None:
        if not isinstance(self.field, SalesUnitCueField):
            raise TypeError(
                "field must be SalesUnitCueField, "
                f"got {type(self.field).__name__}"
            )
        expected_source = _cue_source_for(self.field)
        if not isinstance(self.source, CandidateEvidenceSourceV2):
            raise TypeError(
                "source must be CandidateEvidenceSourceV2, "
                f"got {type(self.source).__name__}"
            )
        if self.source is not expected_source:
            raise ValueError(
                "a cue from the "
                f"{self.field.value} field carries the "
                f"{expected_source.value} provenance; the other "
                "CandidateEvidenceSourceV2 members (specification text, "
                "reviewed product context) are not extractor outputs, and "
                "no member is a model claim"
            )
        if not isinstance(self.raw_field_value, str) or not self.raw_field_value:
            raise ValueError(
                "raw_field_value must be the non-empty published field text"
            )
        if not isinstance(self.cue_text, str) or not self.cue_text:
            raise ValueError("cue_text must be the non-empty published phrase")
        if not isinstance(self.cue_start, int) or not isinstance(self.cue_end, int):
            raise TypeError("cue_start / cue_end must be int spans")
        if self.cue_start < 0 or self.cue_end <= self.cue_start:
            raise ValueError("the cue span must be a non-empty positive range")
        if self.raw_field_value[self.cue_start : self.cue_end] != self.cue_text:
            raise ValueError(
                "cue_text must be the verbatim published substring of the "
                "field value (a cue cannot claim text its field never "
                "published)"
            )
        if self.kind is not None and not isinstance(self.kind, SalesUnitKindV2):
            raise TypeError(
                "kind must be SalesUnitKindV2 or None, "
                f"got {type(self.kind).__name__}"
            )
        if self.quantity is not None:
            if type(self.quantity) is not int or self.quantity < 1:
                raise ValueError(
                    "a cue quantity must be a positive int "
                    f"(got {self.quantity!r})"
                )
        if not isinstance(self.disposition, SalesUnitCueDisposition):
            raise TypeError(
                "disposition must be SalesUnitCueDisposition, "
                f"got {type(self.disposition).__name__}"
            )
        if (
            self.reason is not None
            and not isinstance(self.reason, SalesUnitCueReason)
        ):
            raise TypeError(
                "reason must be SalesUnitCueReason or None, "
                f"got {type(self.reason).__name__}"
            )
        if self.disposition is SalesUnitCueDisposition.ESTABLISHED:
            if self.kind is None:
                raise ValueError(
                    "an ESTABLISHED cue requires a bounded kind (the cue "
                    "table publishes one with every established phrase)"
                )
            if self.reason is not None:
                raise ValueError(
                    "an ESTABLISHED cue carries no ambiguity reason"
                )
            # The frozen channel's quantity rules, mirrored: a pack always
            # publishes its count, a single unit carries none.
            if self.kind is SalesUnitKindV2.PACK_QUANTITY and self.quantity is None:
                raise ValueError(
                    "an established PACK_QUANTITY cue requires the "
                    "published count"
                )
            if self.kind is SalesUnitKindV2.SINGLE_UNIT and self.quantity is not None:
                raise ValueError(
                    "an established SINGLE_UNIT cue carries no quantity"
                )
        else:  # AMBIGUOUS
            if self.reason is None:
                raise ValueError(
                    "an AMBIGUOUS cue requires exactly one bounded reason"
                )
            if self.quantity is not None:
                raise ValueError(
                    "an AMBIGUOUS cue never carries a quantity (no count "
                    "is ever inferred or salvaged from an ambiguous phrase)"
                )


@dataclass(frozen=True)
class SalesUnitIdentifierFieldNoteV1:
    """A packaging-like token found in an IDENTIFIER field (MPN / SKU),
    recorded ONLY to evidence that the field was examined and set aside.
    Identifier fields are never packaging evidence: the note cannot
    change the result state and has no kind / quantity / source."""

    field_name: str
    token_text: str

    def __post_init__(self) -> None:
        if self.field_name not in ("sku", "mpn"):
            raise ValueError(
                "an identifier-field note names exactly the sku or mpn "
                f"field, got {self.field_name!r}"
            )
        if not isinstance(self.token_text, str) or not self.token_text:
            raise ValueError("token_text must be the non-empty published token")


@dataclass(frozen=True)
class SalesUnitExtractionResult:
    """The versioned, immutable, self-verifying extraction result
    (schema v1).

    The constructor is the validator: it fails closed on every
    inconsistency between the state, the cues, and the established unit
    (an ``OBSERVED_UNAMBIGUOUS`` result with no consistent established
    claim, a ``CONTRADICTED_CUES`` result with one kind and one quantity,
    an ambiguous reason on an established cue, a cue text its field never
    published, a non-canonical digest), so a hand-forged result cannot be
    built into a misleading shape. The cues are canonicalized (field
    order, then span order) so equal inputs always produce byte-equal
    results.

    * ``input_digest`` — SHA-256 over the canonical document of the exact
      examined input (every named 3A field of the observation EXCEPT the
      opaque ``raw_reference``, plus the structured packaging field when
      present). Binds the result to the input that produced it.
    * ``result_digest`` — SHA-256 over the canonical result minus the
      digest itself. Self-verification anchor:
      ``sales_unit_channel_from_extraction`` recomputes it and refuses a
      tampered result before mapping.
    """

    schema_version: int
    state: SalesUnitExtractionState
    cues: tuple[SalesUnitCueV1, ...]
    identifier_field_notes: tuple[SalesUnitIdentifierFieldNoteV1, ...]
    established_kind: SalesUnitKindV2 | None
    established_quantity: int | None
    input_digest: str
    result_digest: str

    def __post_init__(self) -> None:
        if self.schema_version != SALES_UNIT_EXTRACTION_SCHEMA_VERSION:
            raise ValueError(
                f"schema_version must be "
                f"{SALES_UNIT_EXTRACTION_SCHEMA_VERSION}, got "
                f"{self.schema_version!r} (an unknown extraction schema "
                "version is never silently reinterpreted)"
            )
        if not isinstance(self.state, SalesUnitExtractionState):
            raise TypeError(
                "state must be SalesUnitExtractionState, "
                f"got {type(self.state).__name__}"
            )
        if not isinstance(self.cues, tuple):
            raise TypeError("cues must be a tuple (immutable, ordered)")
        for cue in self.cues:
            if not isinstance(cue, SalesUnitCueV1):
                raise TypeError(
                    "cues must contain only SalesUnitCueV1, got "
                    f"{type(cue).__name__}"
                )
        if not isinstance(self.identifier_field_notes, tuple):
            raise TypeError("identifier_field_notes must be a tuple")
        for note in self.identifier_field_notes:
            if not isinstance(note, SalesUnitIdentifierFieldNoteV1):
                raise TypeError(
                    "identifier_field_notes must contain only "
                    f"SalesUnitIdentifierFieldNoteV1, got {type(note).__name__}"
                )
        if self.established_kind is not None and not isinstance(
            self.established_kind, SalesUnitKindV2
        ):
            raise TypeError(
                "established_kind must be SalesUnitKindV2 or None, got "
                f"{type(self.established_kind).__name__}"
            )
        if self.established_quantity is not None:
            if type(self.established_quantity) is not int or (
                self.established_quantity < 1
            ):
                raise ValueError(
                    "established_quantity must be a positive int (got "
                    f"{self.established_quantity!r})"
                )
        for name in ("input_digest", "result_digest"):
            value = getattr(self, name)
            if not isinstance(value, str) or len(value) != 64:
                raise ValueError(f"{name} must be a 64-character hex digest")
            if any(ch not in "0123456789abcdef" for ch in value):
                raise ValueError(f"{name} must be a lowercase hex digest")

        # Canonical cue order (field order, then span order).
        ordered = tuple(
            sorted(
                self.cues,
                key=lambda c: (
                    list(SalesUnitCueField).index(c.field),
                    c.cue_start,
                    c.cue_end,
                ),
            )
        )
        object.__setattr__(self, "cues", ordered)

        established = [
            c for c in ordered if c.disposition is SalesUnitCueDisposition.ESTABLISHED
        ]
        ambiguous = [
            c for c in ordered if c.disposition is SalesUnitCueDisposition.AMBIGUOUS
        ]
        if self.state is SalesUnitExtractionState.NO_PACKAGING_PUBLISHED:
            if established or ambiguous:
                raise ValueError(
                    "NO_PACKAGING_PUBLISHED carries no cue of any "
                    "disposition (a published cue must be recorded)"
                )
        elif self.state is SalesUnitExtractionState.AMBIGUOUS_CUE:
            if not ambiguous:
                raise ValueError(
                    "AMBIGUOUS_CUE requires at least one recorded ambiguous "
                    "cue"
                )
        elif self.state is SalesUnitExtractionState.CONTRADICTED_CUES:
            kinds = {c.kind for c in established}
            quantities = {
                c.quantity for c in established if c.quantity is not None
            }
            if not (len(kinds) > 1 or (len(kinds) == 1 and len(quantities) > 1)):
                raise ValueError(
                    "CONTRADICTED_CUES requires at least two established "
                    "cues with incompatible units (different kinds, or "
                    "different published quantities within a kind)"
                )
        else:  # OBSERVED_UNAMBIGUOUS
            if self.established_kind is None:
                raise ValueError(
                    "OBSERVED_UNAMBIGUOUS requires the established kind"
                )
            kinds = {c.kind for c in established}
            if kinds != {self.established_kind}:
                raise ValueError(
                    "OBSERVED_UNAMBIGUOUS established cues must all carry "
                    "the established kind"
                )
            quantities = {c.quantity for c in established if c.quantity is not None}
            if len(quantities) > 1:
                raise ValueError(
                    "OBSERVED_UNAMBIGUOUS established cues publish at most "
                    "one distinct quantity"
                )
            if quantities:
                if next(iter(quantities)) != self.established_quantity:
                    raise ValueError(
                        "established_quantity must be the published "
                        "quantity of the established cues"
                    )
            elif self.established_quantity is not None:
                raise ValueError(
                    "established_quantity must be None when no established "
                    "cue published a count (no quantity is inferred)"
                )
            if self.established_kind is SalesUnitKindV2.PACK_QUANTITY and (
                self.established_quantity is None
            ):
                raise ValueError(
                    "an established PACK_QUANTITY requires the published "
                    "count (a pack without a count is ambiguous)"
                )
            if self.established_kind is SalesUnitKindV2.SINGLE_UNIT and (
                self.established_quantity is not None
            ):
                raise ValueError(
                    "an established SINGLE_UNIT carries no quantity"
                )
            # The same safety rule as state resolution (Q3-B5-P2-FU1):
            # an independently unresolved ambiguous cue — of ANY kind,
            # including the established kind — blocks the established
            # claim; matching packaging kinds alone never prove that the
            # ambiguous cue describes the same commercial unit. An
            # ambiguous cue is admitted only as a genuine duplicate /
            # subsumed cue, deterministically proven by the exact
            # published spans (same field, span contained in an
            # established cue's span, same kind).
            if any(
                not _is_subsumed_by_established(c, established)
                for c in ambiguous
            ):
                raise ValueError(
                    "OBSERVED_UNAMBIGUOUS admits an ambiguous cue only "
                    "when its relationship to an established cue is "
                    "deterministically proven by the exact published "
                    "spans (the documented subsumed-duplicate rule); an "
                    "independently unresolved ambiguous cue of any kind "
                    "blocks the established claim (AMBIGUOUS_CUE)"
                )
        # The established unit fields exist only in the OBSERVED state.
        if self.state is not SalesUnitExtractionState.OBSERVED_UNAMBIGUOUS:
            if self.established_kind is not None or (
                self.established_quantity is not None
            ):
                raise ValueError(
                    "a non-OBSERVED state carries no established unit "
                    "(the cues are recorded, but no unit is claimed)"
                )

        recomputed = _result_digest(
            self.schema_version,
            self.state,
            ordered,
            self.identifier_field_notes,
            self.established_kind,
            self.established_quantity,
            self.input_digest,
        )
        if recomputed != self.result_digest:
            raise SalesUnitExtractionIntegrityError(
                "result_digest does not verify against the result content "
                "(the result was tampered with or forged)"
            )

    # -- canonical form / self-verification ---------------------------------

    def canonical(self) -> dict[str, object]:
        """The canonical (sorted-keys) document of the result minus its
        own digest (the digest is verified, not re-serialized)."""
        return {
            "schema_version": self.schema_version,
            "state": self.state.value,
            "cues": [
                {
                    "field": c.field.value,
                    "source": c.source.value,
                    "raw_field_value": c.raw_field_value,
                    "cue_text": c.cue_text,
                    "cue_start": c.cue_start,
                    "cue_end": c.cue_end,
                    "kind": c.kind.value if c.kind is not None else None,
                    "quantity": c.quantity,
                    "disposition": c.disposition.value,
                    "reason": c.reason.value if c.reason is not None else None,
                }
                for c in self.cues
            ],
            "identifier_field_notes": [
                {"field_name": n.field_name, "token_text": n.token_text}
                for n in self.identifier_field_notes
            ],
            "established_kind": (
                self.established_kind.value
                if self.established_kind is not None
                else None
            ),
            "established_quantity": self.established_quantity,
            "input_digest": self.input_digest,
        }

    def verify_integrity(self) -> None:
        """Re-verify the self-consistency of the result (digest + cue
        span containment). Raises ``SalesUnitExtractionIntegrityError``
        on any mismatch. The constructor already guarantees this for
        constructed results; the channel mapping calls it as the
        anti-forgery gate for PRESENTED results."""
        if not all(
            cue.raw_field_value[cue.cue_start : cue.cue_end] == cue.cue_text
            for cue in self.cues
        ):
            raise SalesUnitExtractionIntegrityError(
                "a cue text no longer matches its field value span (the "
                "result was tampered with)"
            )
        recomputed = _result_digest(
            self.schema_version,
            self.state,
            self.cues,
            self.identifier_field_notes,
            self.established_kind,
            self.established_quantity,
            self.input_digest,
        )
        if recomputed != self.result_digest:
            raise SalesUnitExtractionIntegrityError(
                "result_digest does not verify against the result content "
                "(the result was tampered with or forged)"
            )


# ---------------------------------------------------------------------------
# The deterministic cue engine (frozen phrase table, schema v1)
# ---------------------------------------------------------------------------


def _canonical_count(text: str) -> int | None:
    """The canonical positive integer 1..99999 if *text* is exactly one;
    None for decimals, leading zeros, oversized counts, and the empty
    string."""
    if not text.isdigit():
        return None
    if len(text) > 1 and text.startswith("0"):
        return None
    value = int(text)
    if value < 1 or value > 99999:
        return None
    return value


def _capacity_attached(field_text: str, after: int) -> bool:
    """True when the character run immediately after *after* (no
    whitespace) is a capacity unit — the number is then a specification
    quantity, not a sales count (``pack of 4TB`` / ``pack of 4TiB``)."""
    return _CAPACITY_ATTACHED.match(field_text[after:]) is not None


def _scan_field(
    field: SalesUnitCueField,
    field_text: str,
) -> list[SalesUnitCueV1]:
    """Scan one published field with the frozen cue table and return its
    recorded cues (established and ambiguous), in span order. Deterministic
    and total: every packaging-shaped phrase the table knows is recorded;
    nothing else matches (a bare number is never a cue)."""
    source = _cue_source_for(field)
    cues: list[SalesUnitCueV1] = []

    def _add(
        span: tuple[int, int],
        kind: SalesUnitKindV2 | None,
        quantity: int | None,
        disposition: SalesUnitCueDisposition,
        reason: SalesUnitCueReason | None,
    ) -> None:
        start, end = span
        cues.append(
            SalesUnitCueV1(
                field=field,
                source=source,
                raw_field_value=field_text,
                cue_text=field_text[start:end],
                cue_start=start,
                cue_end=end,
                kind=kind,
                quantity=quantity,
                disposition=disposition,
                reason=reason,
            )
        )

    for match in _CUE_MASTER.finditer(field_text):
        if match.group("nu_q") is not None:
            # "N-unit <kind>" compounds (the count is canonical by the
            # pattern's own guards).
            word = re.sub(r"\s+", " ", match.group("nu_kind")).lower()
            if word in ("factory pack", "oem pack", "oem tray", "tray"):
                kind = SalesUnitKindV2.TRAY_OR_FACTORY_PACK
            elif word == "bundle":
                kind = SalesUnitKindV2.BUNDLE
            else:  # "pack"
                kind = SalesUnitKindV2.PACK_QUANTITY
            if kind is SalesUnitKindV2.BUNDLE:
                # Q3-B5-P2-FU1: a bundle count without published contents
                # is NOT the complete commercial unit (observed bundle
                # form + count; composition unverified): ambiguous,
                # never established. The published count stays verbatim
                # in the cue text and is never bound to a quantity.
                _add(
                    match.span(),
                    kind,
                    None,
                    SalesUnitCueDisposition.AMBIGUOUS,
                    SalesUnitCueReason.BUNDLE_WITHOUT_CONTENTS,
                )
            else:
                _add(
                    match.span(),
                    kind,
                    int(match.group("nu_q")),
                    SalesUnitCueDisposition.ESTABLISHED,
                    None,
                )
        elif match.group("fo_num") is not None:
            kind = SalesUnitKindV2.TRAY_OR_FACTORY_PACK
            num = match.group("fo_num")
            start, end = match.span()
            if _capacity_attached(field_text, end):
                _add(
                    (start, end),
                    kind,
                    None,
                    SalesUnitCueDisposition.AMBIGUOUS,
                    SalesUnitCueReason.CAPACITY_ATTACHED_QUANTITY,
                )
            else:
                count = _canonical_count(num)
                if count is None:
                    _add(
                        (start, end),
                        kind,
                        None,
                        SalesUnitCueDisposition.AMBIGUOUS,
                        SalesUnitCueReason.NON_CANONICAL_QUANTITY,
                    )
                else:
                    _add(
                        (start, end),
                        kind,
                        count,
                        SalesUnitCueDisposition.ESTABLISHED,
                        None,
                    )
        elif match.group("fo_bare") is not None:
            # A bare "Factory Pack" / "OEM Tray" establishes the kind;
            # the quantity is optional when published (absent here).
            _add(
                match.span(),
                SalesUnitKindV2.TRAY_OR_FACTORY_PACK,
                None,
                SalesUnitCueDisposition.ESTABLISHED,
                None,
            )
        elif match.group("of_num") is not None:
            word = match.group("of_kind").lower()
            kind = {
                "pack": SalesUnitKindV2.PACK_QUANTITY,
                "tray": SalesUnitKindV2.TRAY_OR_FACTORY_PACK,
                "bundle": SalesUnitKindV2.BUNDLE,
            }[word]
            num = match.group("of_num")
            start, end = match.span()
            if _capacity_attached(field_text, end):
                _add(
                    (start, end),
                    kind,
                    None,
                    SalesUnitCueDisposition.AMBIGUOUS,
                    SalesUnitCueReason.CAPACITY_ATTACHED_QUANTITY,
                )
            else:
                count = _canonical_count(num)
                if count is None:
                    _add(
                        (start, end),
                        kind,
                        None,
                        SalesUnitCueDisposition.AMBIGUOUS,
                        SalesUnitCueReason.NON_CANONICAL_QUANTITY,
                    )
                elif kind is SalesUnitKindV2.BUNDLE:
                    # Q3-B5-P2-FU1: "bundle of N" — a published count
                    # alone is not the complete identity of a bundle
                    # (the composition is unverified; two bundles with
                    # equal counts and different contents are not
                    # commercially equivalent): ambiguous, never
                    # established. The count stays verbatim in the cue
                    # text and is never bound to a quantity.
                    _add(
                        (start, end),
                        kind,
                        None,
                        SalesUnitCueDisposition.AMBIGUOUS,
                        SalesUnitCueReason.BUNDLE_WITHOUT_CONTENTS,
                    )
                else:
                    _add(
                        (start, end),
                        kind,
                        count,
                        SalesUnitCueDisposition.ESTABLISHED,
                        None,
                    )
        elif match.group("npack_q") is not None:
            # "N-pack" / "N pack" (the pattern's guards already reject
            # non-canonical counts and capacity-attached forms).
            _add(
                match.span(),
                SalesUnitKindV2.PACK_QUANTITY,
                int(match.group("npack_q")),
                SalesUnitCueDisposition.ESTABLISHED,
                None,
            )
        elif match.group("npack_bad") is not None:
            # "014-pack" / "100000-pack": a published count-like token in
            # non-canonical form — ambiguous (never a guessed count).
            _add(
                match.span(),
                SalesUnitKindV2.PACK_QUANTITY,
                None,
                SalesUnitCueDisposition.AMBIGUOUS,
                SalesUnitCueReason.NON_CANONICAL_QUANTITY,
            )
        elif match.group("bundle_mark") is not None:
            # "bundle: ..." / "bundle (...)" — the contents marker
            # establishes the kind; the quantity is optional when
            # published (absent here). The cue span extends over the
            # published contents clause (for ":" up to the next
            # comma / semicolon / closing paren, for "(" up to the
            # closing paren, bounded and verbatim) so the raw detail
            # records what the page says the bundle contains.
            start = match.start()
            end = match.end()
            if field_text[end - 1] == "(":
                close = field_text.find(")", end)
                end = close + 1 if close != -1 else len(field_text)
            else:
                for i in range(end, len(field_text)):
                    if field_text[i] in ",;)":
                        break
                    end = i + 1
            _add(
                (start, end),
                SalesUnitKindV2.BUNDLE,
                None,
                SalesUnitCueDisposition.ESTABLISHED,
                None,
            )
        elif match.group("tray_bare") is not None:
            # A bare "tray" is an established tray cue (the approved 2.1
            # design's raw-cue example: "(tray)" establishes the form);
            # the quantity, when absent, is simply not published.
            _add(
                match.span(),
                SalesUnitKindV2.TRAY_OR_FACTORY_PACK,
                None,
                SalesUnitCueDisposition.ESTABLISHED,
                None,
            )
        elif match.group("single") is not None:
            # "single unit" / "1 unit" / "1-unit" — the single retail
            # unit IS the bounded value; no quantity field exists.
            _add(
                match.span(),
                SalesUnitKindV2.SINGLE_UNIT,
                None,
                SalesUnitCueDisposition.ESTABLISHED,
                None,
            )
        elif match.group("pack_bare") is not None:
            # A "pack" word with no published count: the frozen channel
            # requires the count for a pack, so this is ambiguous (never
            # established, never silently dropped).
            _add(
                match.span(),
                SalesUnitKindV2.PACK_QUANTITY,
                None,
                SalesUnitCueDisposition.AMBIGUOUS,
                SalesUnitCueReason.PACK_WITHOUT_COUNT,
            )
        elif match.group("bundle_bare") is not None:
            # A "bundle" word with no count and no contents marker:
            # contents unclear (the approved 2.1 design's P6 shape —
            # unproven packaging evidence, never an established
            # conflict).
            _add(
                match.span(),
                SalesUnitKindV2.BUNDLE,
                None,
                SalesUnitCueDisposition.AMBIGUOUS,
                SalesUnitCueReason.BUNDLE_WITHOUT_CONTENTS,
            )

    if (
        field is SalesUnitCueField.STRUCTURED_PACKAGING_FIELD
        and not cues
    ):
        # The page published a value in a packaging position but it
        # carries no bounded packaging vocabulary: record the field as an
        # ambiguous cue (the extractor does not interpret it).
        _add(
            (0, len(field_text)),
            None,
            None,
            SalesUnitCueDisposition.AMBIGUOUS,
            SalesUnitCueReason.NO_PACKAGING_VOCABULARY,
        )
    return cues


def _identifier_notes(observation: ListingObservation) -> tuple[SalesUnitIdentifierFieldNoteV1, ...]:
    """The set-aside record for the identifier fields (MPN / SKU): every
    packaging-like token they publish is noted (provenance that the field
    was examined and deliberately not used). A note never changes the
    state."""
    notes: list[SalesUnitIdentifierFieldNoteV1] = []
    for field_name, value in (
        ("sku", observation.sku_text),
        ("mpn", observation.manufacturer_part_number_text),
    ):
        if value is None:
            continue
        for match in _IDENTIFIER_TOKEN.finditer(value):
            notes.append(
                SalesUnitIdentifierFieldNoteV1(
                    field_name=field_name, token_text=match.group(0)
                )
            )
    return tuple(notes)


def _is_subsumed_by_established(
    cue: SalesUnitCueV1,
    established: "tuple[SalesUnitCueV1, ...] | list[SalesUnitCueV1]",
) -> bool:
    """The documented subsumed-duplicate rule (Q3-B5-P2-FU1): a recorded
    ambiguous cue is a GENUINE duplicate / subsumed cue of an established
    claim only when its relationship is deterministically proven by the
    EXACT PUBLISHED SPANS: the ambiguous cue sits in the SAME examined
    field, its ``[cue_start, cue_end)`` span lies inside the established
    cue's published span, and it carries the same kind. The ambiguous
    reading is then a fragment of the established published phrase (one
    published claim read two ways), not an independent claim. Matching
    packaging kinds alone never prove the relationship: a second
    published occurrence of the same kind (a separate span) is an
    independent, unresolved cue. Applied identically by state resolution
    (``_resolve_state``) and by the result constructor (fail closed)."""
    return any(
        e.field is cue.field
        and e.kind is cue.kind
        and e.cue_start <= cue.cue_start
        and cue.cue_end <= e.cue_end
        for e in established
    )


def _resolve_state(
    cues: tuple[SalesUnitCueV1, ...],
) -> tuple[SalesUnitExtractionState, SalesUnitKindV2 | None, int | None]:
    """The bounded state resolution over the recorded cues (deterministic
    and fail-closed). See the module docstring for the contract."""
    established = [
        c for c in cues if c.disposition is SalesUnitCueDisposition.ESTABLISHED
    ]
    ambiguous = [
        c for c in cues if c.disposition is SalesUnitCueDisposition.AMBIGUOUS
    ]
    if not established:
        if ambiguous:
            return SalesUnitExtractionState.AMBIGUOUS_CUE, None, None
        return SalesUnitExtractionState.NO_PACKAGING_PUBLISHED, None, None

    kinds = {c.kind for c in established}
    if len(kinds) > 1:
        return SalesUnitExtractionState.CONTRADICTED_CUES, None, None
    kind = next(iter(kinds))
    quantities = {c.quantity for c in established if c.quantity is not None}
    if len(quantities) > 1:
        return SalesUnitExtractionState.CONTRADICTED_CUES, None, None
    quantity = next(iter(quantities)) if quantities else None
    # Q3-B5-P2-FU1: an independently unresolved ambiguous cue — of ANY
    # kind, INCLUDING the established kind — blocks the established claim:
    # matching packaging kinds alone never prove that the ambiguous cue
    # describes the same commercial unit. An ambiguous cue is admitted as
    # a genuine duplicate / subsumed cue only when its relationship to an
    # established cue is deterministically proven by the exact published
    # spans (the documented subsumption rule). Every cue stays recorded
    # with its full provenance in the AMBIGUOUS_CUE result.
    if any(not _is_subsumed_by_established(c, established) for c in ambiguous):
        return SalesUnitExtractionState.AMBIGUOUS_CUE, None, None
    return SalesUnitExtractionState.OBSERVED_UNAMBIGUOUS, kind, quantity


# ---------------------------------------------------------------------------
# The extraction entry point
# ---------------------------------------------------------------------------


def _input_digest(
    observation: ListingObservation,
    structured_packaging_text: str | None,
) -> str:
    document = {
        "extraction_method": observation.extraction_method.value,
        "fields": {
            name: getattr(observation, name) for name in _DIGEST_FIELD_NAMES
        },
        "structured_packaging_field": structured_packaging_text,
    }
    encoded = json.dumps(
        document, sort_keys=True, separators=(",", ":"), ensure_ascii=True
    )
    return hashlib.sha256(encoded.encode("ascii")).hexdigest()


def _result_digest(
    schema_version: int,
    state: SalesUnitExtractionState,
    cues: tuple[SalesUnitCueV1, ...],
    identifier_field_notes: tuple[SalesUnitIdentifierFieldNoteV1, ...],
    established_kind: SalesUnitKindV2 | None,
    established_quantity: int | None,
    input_digest: str,
) -> str:
    document = {
        "schema_version": schema_version,
        "state": state.value,
        "cues": [
            {
                "field": c.field.value,
                "source": c.source.value,
                "raw_field_value": c.raw_field_value,
                "cue_text": c.cue_text,
                "cue_start": c.cue_start,
                "cue_end": c.cue_end,
                "kind": c.kind.value if c.kind is not None else None,
                "quantity": c.quantity,
                "disposition": c.disposition.value,
                "reason": c.reason.value if c.reason is not None else None,
            }
            for c in cues
        ],
        "identifier_field_notes": [
            {"field_name": n.field_name, "token_text": n.token_text}
            for n in identifier_field_notes
        ],
        "established_kind": (
            established_kind.value if established_kind is not None else None
        ),
        "established_quantity": established_quantity,
        "input_digest": input_digest,
    }
    encoded = json.dumps(
        document, sort_keys=True, separators=(",", ":"), ensure_ascii=True
    )
    return hashlib.sha256(encoded.encode("ascii")).hexdigest()


def extract_sales_unit_evidence(
    observation: ListingObservation,
    structured_packaging_text: str | None = None,
) -> SalesUnitExtractionResult:
    """Deterministically extract the published sales-unit / packaging
    evidence of ONE offer (one observation) with explicit provenance.

    Input: the frozen 3A ``ListingObservation`` (the examined fields are
    the published title and, when present, the explicit structured
    packaging field value — the identifier fields are examined only for
    the set-aside record; ``raw_reference`` is never read) and the
    structured packaging text (None when the page / source publishes no
    such field, which is today's live main-flow reality).

    Output: the versioned, immutable, self-verifying
    ``SalesUnitExtractionResult`` (schema v1) — pure, deterministic,
    zero-live: the same input always produces the byte-equal result.
    Fail closed: ``TypeError`` on a foreign observation / text input,
    ``ValueError`` on an empty structured field.
    """
    if not isinstance(observation, ListingObservation):
        raise TypeError(
            "observation must be ListingObservation (the frozen 3A "
            f"contract), got {type(observation).__name__}"
        )
    if structured_packaging_text is not None:
        if not isinstance(structured_packaging_text, str):
            raise TypeError(
                "structured_packaging_text must be str (the value as "
                f"published) or None, got {type(structured_packaging_text).__name__}"
            )
        if not structured_packaging_text.strip():
            raise ValueError(
                "structured_packaging_text must be a non-empty published "
                "value when present (an absent field is explicit None, "
                "never an empty sentinel)"
            )

    cues: list[SalesUnitCueV1] = []
    if structured_packaging_text is not None:
        cues.extend(
            _scan_field(
                SalesUnitCueField.STRUCTURED_PACKAGING_FIELD,
                structured_packaging_text,
            )
        )
    if observation.product_title is not None:
        cues.extend(
            _scan_field(SalesUnitCueField.PRODUCT_TITLE, observation.product_title)
        )
    ordered_cues = tuple(
        sorted(
            cues,
            key=lambda c: (
                list(SalesUnitCueField).index(c.field),
                c.cue_start,
                c.cue_end,
            ),
        )
    )
    state, kind, quantity = _resolve_state(ordered_cues)
    input_digest = _input_digest(observation, structured_packaging_text)
    notes = _identifier_notes(observation)
    result_digest = _result_digest(
        SALES_UNIT_EXTRACTION_SCHEMA_VERSION,
        state,
        ordered_cues,
        notes,
        kind,
        quantity,
        input_digest,
    )
    return SalesUnitExtractionResult(
        schema_version=SALES_UNIT_EXTRACTION_SCHEMA_VERSION,
        state=state,
        cues=ordered_cues,
        identifier_field_notes=notes,
        established_kind=kind,
        established_quantity=quantity,
        input_digest=input_digest,
        result_digest=result_digest,
    )


# ---------------------------------------------------------------------------
# The fail-closed mapping onto the frozen S2-C-FU1 recorded channel
# ---------------------------------------------------------------------------


def sales_unit_channel_from_extraction(
    result: SalesUnitExtractionResult,
) -> CandidateSalesUnitEvidenceV2:
    """Map ONE extraction result onto the frozen recorded sales-unit
    channel (``CandidateSalesUnitEvidenceV2``) WITHOUT changing that
    contract (the channel's field set, its states, and its provenance
    vocabulary are the frozen S2-C-FU1 ones).

    * The anti-forgery gate runs first: the presented result re-verifies
      its own digest and cue spans (``SalesUnitExtractionIntegrityError``
      on any mismatch — a hand-forged or tampered result produces no
      channel).
    * ``OBSERVED_UNAMBIGUOUS`` -> an ``OBSERVED`` channel: the established
      kind, the published quantity (None for single unit / an uncounted
      tray or bundle), the PRIMARY established cue's exact published text
      as ``raw_detail`` (the structured-field cue when one is
      established, else the first title cue in span order), and that
      cue's recorded provenance source. The channel's own constructor
      re-validates the shape (second fail-closed gate).
    * ``NO_PACKAGING_PUBLISHED`` / ``AMBIGUOUS_CUE`` /
      ``CONTRADICTED_CUES`` -> the canonical ``UNAVAILABLE`` state: the
      frozen channel has no ambiguity or contradiction state, and
      recording either side of a contradiction as ``OBSERVED`` would
      present one published claim as THE recorded unit (an unsafe
      workaround the schema refuses). The full cue record with both
      sides' provenance stays in the versioned result for audit; the
      FU3 derivation over the mapped channel then yields UNPROVEN (never
      PROVEN_EQUIVALENT, never CONTRADICTED) — fail closed.

    The mapping grants no authority: the channel is commercial
    observation evidence, and no authority-side profile or pricing path
    consumes it (see the module docstring).
    """
    if not isinstance(result, SalesUnitExtractionResult):
        raise TypeError(
            "result must be SalesUnitExtractionResult, "
            f"got {type(result).__name__}"
        )
    result.verify_integrity()
    if result.state is not SalesUnitExtractionState.OBSERVED_UNAMBIGUOUS:
        return SALES_UNIT_EVIDENCE_UNAVAILABLE
    established = [
        c
        for c in result.cues
        if c.disposition is SalesUnitCueDisposition.ESTABLISHED
    ]
    structured = [c for c in established if c.field is SalesUnitCueField.STRUCTURED_PACKAGING_FIELD]
    primary = (structured or established)[0]
    return CandidateSalesUnitEvidenceV2(
        state=PackagingEvidenceStateV2.OBSERVED,
        kind=primary.kind,
        quantity=result.established_quantity,
        raw_detail=primary.cue_text,
        source=primary.source,
    )


def extract_and_map_sales_unit_evidence(
    observation: ListingObservation,
    structured_packaging_text: str | None = None,
) -> tuple[SalesUnitExtractionResult, CandidateSalesUnitEvidenceV2]:
    """The offline convenience composition: extract over one observation
    and map the result onto the frozen channel (the audit record AND the
    recorded channel together, the shape a separately gated live
    integration would persist). Pure and deterministic."""
    result = extract_sales_unit_evidence(
        observation, structured_packaging_text
    )
    return result, sales_unit_channel_from_extraction(result)


# ---------------------------------------------------------------------------
# Mechanical self-consistency of the extraction contract data, verified
# once at import (pure data check, no mutable state). If a future edit
# breaks any of these contracts, the module refuses to import.
# ---------------------------------------------------------------------------

if {state.value for state in SalesUnitExtractionState} != {
    "NO_PACKAGING_PUBLISHED",
    "OBSERVED_UNAMBIGUOUS",
    "AMBIGUOUS_CUE",
    "CONTRADICTED_CUES",
}:
    raise RuntimeError(
        "the extraction state vocabulary is bounded to exactly four "
        "states (sales-unit extraction schema v1)"
    )
if {disposition.value for disposition in SalesUnitCueDisposition} != {
    "ESTABLISHED",
    "AMBIGUOUS",
}:
    raise RuntimeError(
        "the cue disposition vocabulary is bounded to exactly ESTABLISHED "
        "/ AMBIGUOUS (sales-unit extraction schema v1)"
    )
if {field.value for field in SalesUnitCueField} != {
    "PRODUCT_TITLE",
    "STRUCTURED_PACKAGING_FIELD",
}:
    raise RuntimeError(
        "the examined-field vocabulary is bounded to exactly the published "
        "title and the explicit structured packaging field (sales-unit "
        "extraction schema v1; no model-claim member, no raw-reference "
        "member)"
    )
if {source for _field, source in _CUE_SOURCE_PAIRS} != {
    CandidateEvidenceSourceV2.LISTING_TITLE,
    CandidateEvidenceSourceV2.PUBLISHED_STRUCTURED_FIELD,
}:
    raise RuntimeError(
        "the extractor's cue provenance is exactly the frozen "
        "LISTING_TITLE / PUBLISHED_STRUCTURED_FIELD members (no member is "
        "a model claim; the other two vocabulary members are not "
        "extractor outputs)"
    )
if SALES_UNIT_EXTRACTION_SCHEMA_VERSION != 1:
    raise RuntimeError(
        "the shipped extraction contract is schema v1 (a change is a new "
        "version, never a silent edit)"
    )
for _global_name, _global_value in list(globals().items()):
    if _global_name.startswith("__"):
        continue
    if isinstance(_global_value, (dict, list, set)):
        raise RuntimeError(
            f"sales_unit_extraction global {_global_name} is a mutable "
            "container; frozen contract data must be runtime-immutable "
            "(sales-unit extraction schema v1 discipline)"
        )
