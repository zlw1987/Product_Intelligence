"""Micron 7500 SSD packaging-alias retrieval contracts (PRODUCT-INTEL.4D-D).

v1 SCOPE (binding): Micron 7500 SSD ONLY. This module is not generic
Micron memory, not DRAM, not a generic Micron SSD family, and not an
arbitrary-manufacturer alias mechanism. Extending it to any other
manufacturer, family, or suffix set requires additional reviewed
authority policies and recorded manufacturer evidence.

Authority split (binding, per 4D-D-PRE2):

* Manufacturer / category / base identity — Micron catalog evidence,
  verified at runtime against the reviewed v1 policy
  (``MICRON_7500_*`` constants below). The structured family-catalog
  record owns the exact-MPN proof and the ``is-ssd`` category proof.
* R/T retrieval relation — a CUSTOMER-DEFINED retrieval rule. No
  manufacturer document states that a final R/T on the 7500 family
  denotes packaging; this module must never claim otherwise.

What this module is *not*

**It is not identity authority.** Nothing here makes BASE and BASE+R
"the same part number". ``compare_part_numbers`` (frozen 2A) is used
only (a) to match the lookup base candidate against source-published
catalog rows, and (b) to verify that a listing-published candidate MPN
is EXACT/NORMALIZED_EXACT to one of the alias identifiers themselves
(reference labeling only). No new match type is introduced, and frozen
2A/3C semantics are unchanged.

**It performs no I/O.** Catalog-record extraction is a pure function
over an already-fetched body string. Acquisition (who fetches, which
URL, origin enforcement) belongs to the execution layer
(``execution/micron_alias_authority.py``).

**It is not a general JSON catalog parser.** The structural rules below
are the exact shape of the reviewed 4D-D-PRE2 recorded fixture
(``tests/fixtures/pages/micron_7500_part_catalog.json``) and nothing
more. The parser is deterministic and fails closed: any structural
corruption of the document it was asked to read raises
``MicronCatalogParseError`` rather than guessing.
"""

from __future__ import annotations

import json
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Final
from urllib.parse import urlsplit

from product_intelligence.domain import ResearchRequest
from product_intelligence.domain.enums import (
    ESTABLISHED_MATCH_TYPES,
)
from product_intelligence.research.identity import (
    PartNumberMatchAssessment,
    compare_part_numbers,
    normalize_part_number,
)


# ---------------------------------------------------------------------------
# Reviewed v1 authority policy constants (Micron 7500 SSD ONLY)
#
# These are reviewed production configuration-as-code. They are the single
# source of truth the execution-layer module-private policy object is built
# from, and the codec/contract self-validation pins every established result
# against them so a tampered persisted payload cannot re-label a foreign
# manufacturer, category, URL, or origin as v1 authority.
# Extending this (new manufacturer / family / suffix / endpoint) requires
# code review — no environment, database, or caller injection exists.
# ---------------------------------------------------------------------------

MICRON_7500_POLICY_ID: Final[str] = "micron-7500-ssd-part-catalog-v1"
"""Reviewed v1 policy identifier. The only policy 4D-D v1 may carry."""

MICRON_7500_MANUFACTURER: Final[str] = "Micron"
"""Manufacturer established by the reviewed policy (origin + catalog)."""

MICRON_7500_CATEGORY: Final[str] = "SSD"
"""Category established by source-published ``is-ssd`` row evidence."""

MICRON_7500_REQUESTED_CATALOG_URL: Final[str] = (
    "https://www.micron.com/content/micron/us/en/products/storage/ssd/"
    "data-center-ssd/7500-ssd/part-catalog/"
    "_jcr_content.products.json/getpartcatalog/storage/7500-ssd/-/en_US"
)
"""Exact reviewed 4D-D-PRE2 family-catalog endpoint (requested URL)."""

MICRON_7500_APPROVED_ORIGIN: Final[str] = "https://www.micron.com"
"""The only origin a successful authority fetch may remain inside."""

MICRON_7500_SOURCE_NAME: Final[str] = "Micron 7500 SSD catalog"
"""Human-facing provenance label for the reviewed source."""


# ---------------------------------------------------------------------------
# Customer rule constants (retrieval only — NOT identity)
# ---------------------------------------------------------------------------

PACKAGING_ALIAS_SUFFIXES: Final[frozenset[str]] = frozenset({"R", "T"})
"""The ONLY final characters that participate in the v1 customer rule.

Uppercase only, final position only. Lowercase ``r``/``t`` deliberately do
NOT invoke the rule, and the rule is never generalized to other
manufacturers, families, or suffix sets.
"""

SSD_EVIDENCE_ATTR_ID: Final[str] = "is-ssd"
"""The catalog attribute id that carries the structured SSD flag."""


# ---------------------------------------------------------------------------
# Catalog-record extraction (pure, deterministic, fail-closed)
# ---------------------------------------------------------------------------


class MicronCatalogParseError(ValueError):
    """The fetched body is not a structurally valid Micron 7500 catalog.

    Covers: non-JSON body, missing/non-list ``details``, non-mapping rows
    or attribute entries, and attribute values that are not JSON scalars.
    This is a bounded evidence failure (the catalog said nothing usable),
    not a programming error: the execution layer maps it to the
    ``PARSE_FAILED`` eligibility status.
    """


@dataclass(frozen=True)
class MicronCatalogAttr:
    """One structured attribute entry from a catalog row.

    Values are preserved as JSON scalars (bool / str / int / float /
    None) exactly as published; nothing is coerced, case-folded, or
    stripped.
    """

    name: str | None
    attr_id: str | None
    value: object

    def __post_init__(self) -> None:
        for field in ("name", "attr_id"):
            value = getattr(self, field)
            if value is not None and not isinstance(value, str):
                raise TypeError(f"{field} must be str or None")
        if not isinstance(self.value, (bool, str, int, float)) and self.value is not None:
            raise TypeError(
                f"value must be a JSON scalar or None, got {type(self.value).__name__}"
            )


@dataclass(frozen=True)
class MicronCatalogRecord:
    """One usable source-published catalog row.

    ``part_number`` is the RAW source-published value, preserved exactly
    (never stripped, re-cased, or synthesized). ``part_name`` and
    ``attr`` are preserved for audit; only ``part_number`` and the
    ``is-ssd`` attribute carry authority.
    """

    part_number: str
    part_name: str
    attr: tuple[MicronCatalogAttr, ...]

    def __post_init__(self) -> None:
        if not isinstance(self.part_number, str) or not self.part_number:
            raise ValueError("part_number must be a non-empty string")
        if not isinstance(self.part_name, str):
            raise TypeError("part_name must be a string")
        if not isinstance(self.attr, tuple):
            raise TypeError("attr must be a tuple")
        for entry in self.attr:
            if not isinstance(entry, MicronCatalogAttr):
                raise TypeError(
                    f"attr entries must be MicronCatalogAttr, got "
                    f"{type(entry).__name__}"
                )


def _parse_attr_entry(entry: object, path: str) -> MicronCatalogAttr:
    """Parse one ``attr[]`` entry, failing closed on structural corruption."""
    if not isinstance(entry, dict):
        raise MicronCatalogParseError(
            f"{path}: attribute entry must be a mapping, "
            f"got {type(entry).__name__}"
        )
    name = entry.get("name")
    if name is not None and not isinstance(name, str):
        raise MicronCatalogParseError(
            f"{path}: 'name' must be a string when present"
        )
    attr_id = entry.get("id")
    if attr_id is not None and not isinstance(attr_id, str):
        raise MicronCatalogParseError(
            f"{path}: 'id' must be a string when present"
        )
    value = entry.get("value")
    if value is not None and not isinstance(value, (bool, str, int, float)):
        raise MicronCatalogParseError(
            f"{path}: attribute value must be a JSON scalar, "
            f"got {type(value).__name__}"
        )
    return MicronCatalogAttr(name=name, attr_id=attr_id, value=value)


def extract_micron_7500_catalog_records(
    body_text: str,
) -> tuple[MicronCatalogRecord, ...]:
    """Extract usable catalog rows from one fetched family-catalog body.

    Structural rules (the exact shape of the reviewed PRE2 fixture):

    * the body must parse as JSON (``MicronCatalogParseError`` otherwise);
    * the top level must be a mapping with a ``details`` list;
    * every ``details`` row must be a mapping (corruption fails closed);
    * a row is USABLE when its ``part-number`` is a non-empty string;
      rows without a usable part number are skipped (they cannot match);
    * a usable row's ``part-name`` (string, default ``""``) and ``attr``
      (list, default empty) are preserved; a non-list ``attr`` on a usable
      row is structural corruption and fails closed;
    * the published row order is preserved.

    No inference: the SSD category is read only from the matched row's
    structured attributes (see ``verify_ssd_category_evidence``), never
    from a URL path, filename, MPN prefix, description, or model
    knowledge.
    """
    if not isinstance(body_text, str):
        raise TypeError(
            f"body_text must be a string, got {type(body_text).__name__}"
        )
    try:
        document = json.loads(body_text)
    except json.JSONDecodeError as exc:
        raise MicronCatalogParseError(
            "catalog body is not valid JSON"
        ) from exc

    if not isinstance(document, dict):
        raise MicronCatalogParseError(
            f"catalog top level must be a mapping, got {type(document).__name__}"
        )
    if "details" not in document:
        raise MicronCatalogParseError("catalog is missing 'details'")
    details = document["details"]
    if not isinstance(details, list):
        raise MicronCatalogParseError(
            f"'details' must be a list, got {type(details).__name__}"
        )

    records: list[MicronCatalogRecord] = []
    for index, row in enumerate(details):
        path = f"details[{index}]"
        if not isinstance(row, dict):
            raise MicronCatalogParseError(
                f"{path}: row must be a mapping, got {type(row).__name__}"
            )
        part_number = row.get("part-number")
        if not isinstance(part_number, str) or not part_number:
            # Unusable row: no source-published part number to match.
            continue
        part_name = row.get("part-name", "")
        if not isinstance(part_name, str):
            raise MicronCatalogParseError(
                f"{path}: 'part-name' must be a string when present"
            )
        attr_raw = row.get("attr", [])
        if not isinstance(attr_raw, list):
            raise MicronCatalogParseError(
                f"{path}: 'attr' must be a list, got {type(attr_raw).__name__}"
            )
        records.append(
            MicronCatalogRecord(
                part_number=part_number,
                part_name=part_name,
                attr=tuple(
                    _parse_attr_entry(entry, f"{path}.attr[{j}]")
                    for j, entry in enumerate(attr_raw)
                ),
            )
        )
    return tuple(records)


def verify_ssd_category_evidence(record: MicronCatalogRecord) -> bool:
    """True when the matched row carries usable structured SSD evidence.

    The evidence is the row's own attribute with ``id == "is-ssd"`` and
    ``value is True`` (exact boolean). Rules:

    * zero ``is-ssd`` entries -> False (missing evidence fails closed);
    * any ``is-ssd`` entry whose value is not exactly ``True`` -> False;
    * one or more ``is-ssd`` entries, all exactly ``True`` -> True.

    SSD is never inferred from the request description, the URL path,
    a filename, an MPN prefix, or model knowledge.
    """
    if not isinstance(record, MicronCatalogRecord):
        raise TypeError(
            f"record must be a MicronCatalogRecord, got {type(record).__name__}"
        )
    entries = [a for a in record.attr if a.attr_id == SSD_EVIDENCE_ATTR_ID]
    if not entries:
        return False
    return all(a.value is True for a in entries)


def matched_ssd_category_evidence(record: MicronCatalogRecord) -> MicronCatalogAttr:
    """Return the first usable ``is-ssd == True`` attribute of a verified row.

    Raises ``ValueError`` when the row does not carry usable SSD evidence
    (the caller should have checked ``verify_ssd_category_evidence``).
    """
    for entry in record.attr:
        if entry.attr_id == SSD_EVIDENCE_ATTR_ID and entry.value is True:
            return entry
    raise ValueError("record carries no usable is-ssd=True evidence")


# ---------------------------------------------------------------------------
# Origin boundary (pure string check; not a fetcher)
# ---------------------------------------------------------------------------


def _origin_of(url: str) -> str | None:
    """Normalized origin (scheme + host + effective port) of one URL.

    Returns None for anything unparseable or non-http(s) — fail closed.
    """
    try:
        parsed = urlsplit(url)
    except ValueError:
        return None
    scheme = parsed.scheme.lower()
    if scheme not in ("http", "https"):
        return None
    host = (parsed.hostname or "").lower()
    if not host:
        return None
    port = parsed.port
    if port is not None and not (
        (scheme == "http" and port == 80) or (scheme == "https" and port == 443)
    ):
        return f"{scheme}://{host}:{port}"
    return f"{scheme}://{host}"


def url_within_origin(url: str, approved_origin: str) -> bool:
    """True when ``url``'s origin exactly matches ``approved_origin``.

    Scheme downgrade, host escape, and port change all fail closed.
    Unparseable URLs fail closed. Path changes on the approved origin are
    allowed (a redirect that stays on the reviewed origin is not an
    escape).
    """
    if not isinstance(url, str) or not isinstance(approved_origin, str):
        return False
    target = _origin_of(url)
    approved = _origin_of(approved_origin)
    if target is None or approved is None:
        return False
    return target == approved


# ---------------------------------------------------------------------------
# Lookup base candidate (NOT identity authority)
# ---------------------------------------------------------------------------


def derive_lookup_base_candidate(mpn: str | None) -> str | None:
    """Derive the LOOKUP BASE CANDIDATE for one requested MPN.

    This is a retrieval pointer, not identity: it exists ONLY to identify
    which manufacturer catalog record must be verified. By itself it
    establishes no manufacturer, no category, no identity, no pricing
    authority.

    Rules (v1 customer rule, final uppercase R/T only):

    * missing/empty MPN -> None;
    * MPN ending in exactly one final uppercase ``R`` or ``T`` and with a
      non-empty, content-bearing remainder -> that remainder;
    * final lowercase ``r``/``t`` does NOT invoke the rule (the full MPN
      is the candidate);
    * degenerate inputs whose remainder carries no part-number content
      (e.g. ``"R"``, ``"T"``, ``"-R"``) -> None (fail safe).
    """
    if mpn is None:
        return None
    if not isinstance(mpn, str):
        raise TypeError(f"mpn must be a string or None, got {type(mpn).__name__}")
    if not mpn:
        return None
    if mpn[-1] in PACKAGING_ALIAS_SUFFIXES:
        candidate = mpn[:-1]
        if not normalize_part_number(candidate):
            return None
        return candidate
    if not normalize_part_number(mpn):
        return None
    return mpn


# ---------------------------------------------------------------------------
# Packaging alias relation (customer-defined retrieval metadata)
# ---------------------------------------------------------------------------


def packaging_alias_family(base_mpn: str) -> tuple[str, str, str]:
    """The deterministic v1 family: ``(base, base + "R", base + "T")``.

    ``base_mpn`` must be the exact source-published base MPN. The family
    is a retrieval shape only — it is not a claim that the manufacturer
    publishes R/T as packaging variants.
    """
    if not isinstance(base_mpn, str) or not base_mpn:
        raise ValueError("base_mpn must be a non-empty string")
    return (base_mpn, base_mpn + "R", base_mpn + "T")


@dataclass(frozen=True)
class MicronPackagingAliasRelation:
    """Customer-defined packaging-alias RETRIEVAL relation for one request.

    This is retrieval/reference metadata, NOT manufacturer-published
    packaging identity and NOT product identity. It may guide one
    alias-expanded paid search query and label clearly-marked reference
    rows. It must never enter Machine Price, Reviewed Price,
    deterministic/semantic identity authority, or comparable scoring.

    Fields:

    * ``requested_mpn`` — the request's MPN exactly as canonical.
    * ``base_mpn`` — the EXACT source-published Micron catalog base MPN
      (never a synthesized or re-cased value).
    * ``aliases`` — the family members other than the requested form, in
      deterministic family order (base, base+R, base+T). Always two for
      v1; no duplicates; the requested form is excluded.

    Self-validation re-derives every binding through frozen 2A and the
    customer rule; a relation that cannot be mechanically reproduced
    from ``(requested_mpn, base_mpn)`` is rejected at construction.
    """

    requested_mpn: str
    base_mpn: str
    aliases: tuple[str, ...]

    def __post_init__(self) -> None:
        if not isinstance(self.requested_mpn, str) or not self.requested_mpn:
            raise ValueError("requested_mpn must be a non-empty string")
        if not isinstance(self.base_mpn, str) or not self.base_mpn:
            raise ValueError("base_mpn must be a non-empty string (source-published)")
        if not isinstance(self.aliases, tuple):
            raise TypeError("aliases must be a tuple")
        for alias in self.aliases:
            if not isinstance(alias, str) or not alias:
                raise ValueError("aliases must be non-empty strings")
        if len(set(self.aliases)) != len(self.aliases):
            raise ValueError("aliases must not contain duplicates")

        family = packaging_alias_family(self.base_mpn)
        for alias in self.aliases:
            if alias not in family:
                raise ValueError(
                    f"alias {alias!r} is not a member of the family derived "
                    f"from source-published base {self.base_mpn!r}"
                )

        # The requested form must be established (frozen 2A) to EXACTLY ONE
        # family member — the customer rule never spans two forms.
        established_members = tuple(
            member
            for member in family
            if compare_part_numbers(self.requested_mpn, member).match_type
            in ESTABLISHED_MATCH_TYPES
        )
        if len(established_members) != 1:
            raise ValueError(
                "requested_mpn must be established (EXACT/NORMALIZED_EXACT) to "
                f"exactly one family member; found {len(established_members)}"
            )

        # The customer-rule derivation must mechanically land on this
        # source-published base: final uppercase R/T strips to a candidate
        # that is 2A-equivalent to base (or the request IS the base form).
        candidate = derive_lookup_base_candidate(self.requested_mpn)
        if candidate is None or compare_part_numbers(
            candidate, self.base_mpn
        ).match_type not in ESTABLISHED_MATCH_TYPES:
            raise ValueError(
                "requested_mpn is not mechanically consistent with the "
                "source-published base under the v1 customer rule "
                "(final uppercase R/T only)"
            )

        # aliases == family minus the established requested form, in
        # deterministic family order. Re-derived, never trusted.
        expected = tuple(m for m in family if m not in established_members)
        if self.aliases != expected:
            raise ValueError(
                f"aliases {self.aliases!r} do not equal the re-derived family "
                f"minus the requested form {expected!r}"
            )


def build_packaging_alias_relation(
    requested_mpn: str,
    source_base_mpn: str,
) -> MicronPackagingAliasRelation:
    """Build the customer-defined retrieval relation for one established base.

    ``source_base_mpn`` must be the exact source-published catalog base MPN.
    The relation's aliases are the family members other than the requested
    form (deterministic order, no duplicates). Any inconsistency between the
    requested form and the source base under the v1 customer rule raises
    ``ValueError`` (programming/invariant error — the authority flow should
    never construct a relation for such a pair).
    """
    family = packaging_alias_family(source_base_mpn)
    established_members = tuple(
        member
        for member in family
        if compare_part_numbers(requested_mpn, member).match_type
        in ESTABLISHED_MATCH_TYPES
    )
    if len(established_members) != 1:
        raise ValueError(
            "build_packaging_alias_relation requires the requested MPN to be "
            "established to exactly one family member of the source base"
        )
    aliases = tuple(m for m in family if m not in established_members)
    return MicronPackagingAliasRelation(
        requested_mpn=requested_mpn,
        base_mpn=source_base_mpn,
        aliases=aliases,
    )


# ---------------------------------------------------------------------------
# Reference labeling (retrieval metadata only — NOT identity)
# ---------------------------------------------------------------------------


def find_alias_reference(
    alias_identifiers: Sequence[str],
    published_candidate_mpn: str | None,
) -> str | None:
    """Answer ONE question: does an excluded listing publish one of the
    customer-defined alias identifiers from an already-established relation?

    The published candidate MPN is compared (frozen 2A) ONLY against the
    alias identifiers themselves. The requested MPN is never the comparison
    target here, and no request-side comparison result is reinterpreted.
    This is reference labeling, not identity: a returned value means "this
    excluded listing publishes an alias identifier", nothing more.

    * ``alias_identifiers`` — a sequence of unique non-empty strings (the
      established relation's aliases, in relation order).
    * ``published_candidate_mpn`` — the listing's published candidate MPN
      (the compared form from the frozen 3C assessment). ``None``/empty
      yields ``None``.

    Returns the first alias identifier (in the given order) that is
    EXACT or NORMALIZED_EXACT to the published value, or ``None``.
    """
    if isinstance(alias_identifiers, (str, bytes)) or not hasattr(
        alias_identifiers, "__iter__"
    ):
        raise TypeError("alias_identifiers must be a sequence of strings")
    identifiers = tuple(alias_identifiers)
    for alias in identifiers:
        if not isinstance(alias, str) or not alias:
            raise ValueError("alias identifiers must be non-empty strings")
    if len(set(identifiers)) != len(identifiers):
        raise ValueError("alias identifiers must not contain duplicates")
    if published_candidate_mpn is None:
        return None
    if not isinstance(published_candidate_mpn, str):
        raise TypeError(
            "published_candidate_mpn must be a string or None, got "
            f"{type(published_candidate_mpn).__name__}"
        )
    if not published_candidate_mpn:
        return None
    for alias in identifiers:
        comparison = compare_part_numbers(published_candidate_mpn, alias)
        if comparison.match_type in ESTABLISHED_MATCH_TYPES:
            return alias
    return None


# ---------------------------------------------------------------------------
# Eligibility status vocabulary (bounded, result-level)
# ---------------------------------------------------------------------------


class MicronAliasEligibilityStatus(str, Enum):
    """Result-level outcome of one 4D-D v1 alias-authority acquisition.

    ESTABLISHED is the only status that may carry manufacturer/category
    authority, the source-published base MPN, SSD evidence, and an alias
    relation. Every other status is a bounded abstention or failure: no
    alias relation, no authority, no query or pricing behavior change.

    The two pre-fetch abstentions are distinct persisted audit states and
    must never be conflated:

    * NO_REQUESTED_MPN — the request MPN is actually absent/empty. There
      is no input to derive a lookup base from.
    * INVALID_LOOKUP_BASE — the request MPN is non-empty but structurally
      unusable under the v1 customer rule (e.g. "-R" / "-T" / "R":
      stripping the final uppercase suffix leaves no content-bearing base).
      This is an invalid structural input, not a missing input.

    Both perform zero fetches. Every other status is a bounded acquisition
    outcome (fetch attempted or not) with no authority.
    """

    ESTABLISHED = "ESTABLISHED"
    NO_REQUESTED_MPN = "NO_REQUESTED_MPN"
    INVALID_LOOKUP_BASE = "INVALID_LOOKUP_BASE"
    NO_AUTHORITY_MATCH = "NO_AUTHORITY_MATCH"
    AMBIGUOUS_AUTHORITY_MATCH = "AMBIGUOUS_AUTHORITY_MATCH"
    CATEGORY_NOT_SSD = "CATEGORY_NOT_SSD"
    FETCH_FAILED = "FETCH_FAILED"
    SOURCE_REFUSED = "SOURCE_REFUSED"
    HOST_ESCAPED = "HOST_ESCAPED"
    PARSE_FAILED = "PARSE_FAILED"


_ESTABLISHED = MicronAliasEligibilityStatus.ESTABLISHED
_FETCHED_STATES = frozenset(
    {
        MicronAliasEligibilityStatus.HOST_ESCAPED,
        MicronAliasEligibilityStatus.PARSE_FAILED,
        MicronAliasEligibilityStatus.NO_AUTHORITY_MATCH,
        MicronAliasEligibilityStatus.AMBIGUOUS_AUTHORITY_MATCH,
        MicronAliasEligibilityStatus.CATEGORY_NOT_SSD,
        MicronAliasEligibilityStatus.ESTABLISHED,
    }
)
_NO_FETCH_STATES = frozenset(
    {
        MicronAliasEligibilityStatus.NO_REQUESTED_MPN,
        MicronAliasEligibilityStatus.INVALID_LOOKUP_BASE,
        MicronAliasEligibilityStatus.FETCH_FAILED,
        MicronAliasEligibilityStatus.SOURCE_REFUSED,
    }
)


def _is_sha256_hex(value: object) -> bool:
    if not isinstance(value, str) or len(value) != 64:
        return False
    try:
        int(value, 16)
    except ValueError:
        return False
    return all(c in "0123456789abcdef" for c in value.lower()) and (
        value == value.lower()
    )


# ---------------------------------------------------------------------------
# SSD category evidence (positive, self-validating)
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class MicronSsdCategoryEvidence:
    """The matched row's structured SSD evidence, preserved for audit.

    Only the positive form is representable: ``attr_id`` must be the
    reviewed ``is-ssd`` id and ``attr_value`` must be exactly ``True``
    (boolean type). ``attr_name`` is the source-published display label
    (e.g. "SSD") — auxiliary provenance only, so it may be ``None``
    when the row carries no name; the authority is the id + boolean.
    A result in a non-established state never carries this evidence.
    """

    attr_name: str | None
    attr_id: str
    attr_value: bool

    def __post_init__(self) -> None:
        if self.attr_name is not None:
            if not isinstance(self.attr_name, str) or not self.attr_name:
                raise ValueError(
                    "attr_name must be a non-empty string or None"
                )
        if self.attr_id != SSD_EVIDENCE_ATTR_ID:
            raise ValueError(
                f"attr_id must be {SSD_EVIDENCE_ATTR_ID!r}, got {self.attr_id!r}"
            )
        if type(self.attr_value) is not bool or self.attr_value is not True:
            raise ValueError("attr_value must be exactly True (boolean)")


# ---------------------------------------------------------------------------
# Eligibility result (bounded, self-validating)
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class MicronAliasEligibilityResult:
    """One bounded 4D-D v1 alias-authority acquisition outcome.

    The contract re-derives every authority-bearing binding at
    construction (frozen 2A comparison, customer-rule derivation, policy
    constants, origin boundary, SSD evidence), so a result that does not
    mechanically agree with its own provenance cannot exist.

    ESTABLISHED carries, in addition to full fetch provenance:

    * ``manufacturer`` / ``category`` pinned to the reviewed v1 policy;
    * ``matched_base_mpn`` — the EXACT source-published catalog base MPN
      (never replaced by a synthesized value);
    * ``part_number_match`` — the complete frozen-2A assessment of the
      lookup base candidate against that source row;
    * ``ssd_category_evidence`` — the matched row's ``is-ssd == True``
      attribute;
    * ``alias_relation`` — the customer-defined retrieval relation.

    Every non-ESTABLISHED status carries NONE of the authority fields and
    therefore cannot supply manufacturer/category authority, cannot
    modify query behavior, and cannot change pricing behavior.
    """

    status: MicronAliasEligibilityStatus
    request: ResearchRequest
    lookup_base_candidate: str | None
    policy_id: str
    manufacturer: str | None
    category: str | None
    requested_source_url: str | None
    fetched_final_url: str | None
    retrieved_at: datetime | None
    source_name: str | None
    matched_base_mpn: str | None
    part_number_match: PartNumberMatchAssessment | None
    ssd_category_evidence: MicronSsdCategoryEvidence | None
    alias_relation: MicronPackagingAliasRelation | None
    body_sha256: str | None

    def __post_init__(self) -> None:
        # -- controlled vocabulary / types --
        if not isinstance(self.status, MicronAliasEligibilityStatus):
            raise TypeError(
                f"status must be MicronAliasEligibilityStatus, got "
                f"{type(self.status).__name__}"
            )
        if not isinstance(self.request, ResearchRequest):
            raise TypeError(
                f"request must be a ResearchRequest, got {type(self.request).__name__}"
            )

        # -- v1 policy pin (no foreign policy may ride this contract) --
        if self.policy_id != MICRON_7500_POLICY_ID:
            raise ValueError(
                f"policy_id must be {MICRON_7500_POLICY_ID!r} (v1 only), "
                f"got {self.policy_id!r}"
            )

        # -- lookup base candidate re-derivation (customer rule) --
        expected_candidate = derive_lookup_base_candidate(
            self.request.manufacturer_part_number
        )
        if self.lookup_base_candidate != expected_candidate:
            raise ValueError(
                "lookup_base_candidate does not re-derive from the request "
                f"MPN under the v1 customer rule (expected "
                f"{expected_candidate!r}, got {self.lookup_base_candidate!r})"
            )

        # -- optional-field type guards --
        for name in (
            "manufacturer",
            "category",
            "requested_source_url",
            "fetched_final_url",
            "source_name",
            "matched_base_mpn",
            "body_sha256",
        ):
            value = getattr(self, name)
            if value is not None and not isinstance(value, str):
                raise TypeError(f"{name} must be str or None")
        if self.retrieved_at is not None:
            if not isinstance(self.retrieved_at, datetime):
                raise TypeError(
                    f"retrieved_at must be datetime or None, got "
                    f"{type(self.retrieved_at).__name__}"
                )
            if self.retrieved_at.tzinfo is None or self.retrieved_at.utcoffset() is None:
                raise ValueError("retrieved_at must be timezone-aware")
        if self.part_number_match is not None and not isinstance(
            self.part_number_match, PartNumberMatchAssessment
        ):
            raise TypeError(
                "part_number_match must be PartNumberMatchAssessment or None"
            )
        if self.ssd_category_evidence is not None and not isinstance(
            self.ssd_category_evidence, MicronSsdCategoryEvidence
        ):
            raise TypeError(
                "ssd_category_evidence must be MicronSsdCategoryEvidence or None"
            )
        if self.alias_relation is not None and not isinstance(
            self.alias_relation, MicronPackagingAliasRelation
        ):
            raise TypeError(
                "alias_relation must be MicronPackagingAliasRelation or None"
            )
        if self.body_sha256 is not None and not _is_sha256_hex(self.body_sha256):
            raise ValueError("body_sha256 must be a lowercase 64-char SHA-256 hex string")

        status = self.status

        if status is _ESTABLISHED:
            self._validate_established()
        else:
            self._validate_non_established()

    # -- state-specific invariants -------------------------------------

    def _validate_established(self) -> None:
        # Authority fields are pinned to the reviewed v1 policy.
        if self.manufacturer != MICRON_7500_MANUFACTURER:
            raise ValueError(
                f"ESTABLISHED manufacturer must be {MICRON_7500_MANUFACTURER!r}, "
                f"got {self.manufacturer!r}"
            )
        if self.category != MICRON_7500_CATEGORY:
            raise ValueError(
                f"ESTABLISHED category must be {MICRON_7500_CATEGORY!r}, "
                f"got {self.category!r}"
            )
        if self.requested_source_url != MICRON_7500_REQUESTED_CATALOG_URL:
            raise ValueError(
                "ESTABLISHED requested_source_url must be the reviewed v1 "
                "catalog URL"
            )
        if self.source_name != MICRON_7500_SOURCE_NAME:
            raise ValueError(
                f"ESTABLISHED source_name must be {MICRON_7500_SOURCE_NAME!r}"
            )
        if self.fetched_final_url is None:
            raise ValueError("ESTABLISHED requires fetched_final_url")
        if not url_within_origin(
            self.fetched_final_url, MICRON_7500_APPROVED_ORIGIN
        ):
            raise ValueError(
                "ESTABLISHED fetched_final_url must remain inside the reviewed "
                f"{MICRON_7500_APPROVED_ORIGIN!r} origin"
            )
        if self.retrieved_at is None:
            raise ValueError("ESTABLISHED requires retrieved_at")
        if self.matched_base_mpn is None:
            raise ValueError("ESTABLISHED requires the source-published base MPN")
        if self.part_number_match is None:
            raise ValueError("ESTABLISHED requires the frozen-2A match evidence")
        if self.ssd_category_evidence is None:
            raise ValueError("ESTABLISHED requires the SSD category evidence")
        if self.alias_relation is None:
            raise ValueError("ESTABLISHED requires the alias relation")

        # The complete frozen-2A assessment must re-derive exactly from the
        # lookup base candidate and the source-published row.
        expected_match = compare_part_numbers(
            self.lookup_base_candidate, self.matched_base_mpn
        )
        if self.part_number_match != expected_match:
            raise ValueError(
                "part_number_match does not re-derive from the lookup base "
                "candidate and the source-published base MPN"
            )
        if self.part_number_match.match_type not in ESTABLISHED_MATCH_TYPES:
            raise ValueError(
                "ESTABLISHED requires an EXACT/NORMALIZED_EXACT catalog match"
            )
        if self.lookup_base_candidate is None:
            raise ValueError("ESTABLISHED requires a lookup base candidate")

        # The relation must bind to the same source row and the same request.
        if self.alias_relation.base_mpn != self.matched_base_mpn:
            raise ValueError(
                "alias_relation.base_mpn must be the exact source-published "
                "matched base MPN"
            )
        if self.alias_relation.requested_mpn != self.request.manufacturer_part_number:
            raise ValueError(
                "alias_relation.requested_mpn must be the request MPN"
            )

    def _validate_non_established(self) -> None:
        # No authority may leak out of a non-established state.
        if self.manufacturer is not None:
            raise ValueError(
                f"non-ESTABLISHED status {self.status.value} must not carry "
                "manufacturer authority"
            )
        if self.category is not None:
            raise ValueError(
                f"non-ESTABLISHED status {self.status.value} must not carry "
                "category authority"
            )
        if self.matched_base_mpn is not None:
            raise ValueError(
                f"non-ESTABLISHED status {self.status.value} must not carry a "
                "matched base MPN"
            )
        if self.part_number_match is not None:
            raise ValueError(
                f"non-ESTABLISHED status {self.status.value} must not carry a "
                "part-number match assessment"
            )
        if self.ssd_category_evidence is not None:
            raise ValueError(
                f"non-ESTABLISHED status {self.status.value} must not carry SSD "
                "category evidence"
            )
        if self.alias_relation is not None:
            raise ValueError(
                f"non-ESTABLISHED status {self.status.value} must not carry an "
                "alias relation"
            )

        # Fetch provenance follows the state.
        if self.status in _NO_FETCH_STATES:
            if self.status is MicronAliasEligibilityStatus.NO_REQUESTED_MPN:
                # Missing input: the request carried no MPN at all.
                # A non-empty MPN that cannot yield a lookup base is a
                # distinct persisted state (INVALID_LOOKUP_BASE).
                if self.request.manufacturer_part_number:
                    raise ValueError(
                        "NO_REQUESTED_MPN requires an absent/empty request "
                        "MPN; a non-empty MPN that cannot yield a lookup "
                        "base is INVALID_LOOKUP_BASE"
                    )
                if self.requested_source_url is not None:
                    raise ValueError(
                        "NO_REQUESTED_MPN must not carry fetch provenance"
                    )
            elif self.status is MicronAliasEligibilityStatus.INVALID_LOOKUP_BASE:
                # Present but structurally unusable input (e.g. "-R"): a
                # distinct persisted state, never conflated with missing input.
                if not self.request.manufacturer_part_number:
                    raise ValueError(
                        "INVALID_LOOKUP_BASE requires a non-empty request "
                        "MPN; an absent/empty MPN is NO_REQUESTED_MPN"
                    )
                if self.requested_source_url is not None:
                    raise ValueError(
                        "INVALID_LOOKUP_BASE must not carry fetch provenance"
                    )
            else:
                # FETCH_FAILED / SOURCE_REFUSED: the reviewed URL was
                # attempted; nothing was fetched.
                if self.requested_source_url != MICRON_7500_REQUESTED_CATALOG_URL:
                    raise ValueError(
                        f"{self.status.value} requires the reviewed v1 catalog URL"
                    )
            for name in (
                "fetched_final_url",
                "retrieved_at",
                "source_name",
                "body_sha256",
            ):
                if getattr(self, name) is not None:
                    raise ValueError(
                        f"{self.status.value} must not carry {name}"
                    )
        elif self.status in _FETCHED_STATES:
            if self.requested_source_url != MICRON_7500_REQUESTED_CATALOG_URL:
                raise ValueError(
                    f"{self.status.value} requires the reviewed v1 catalog URL"
                )
            if self.fetched_final_url is None:
                raise ValueError(f"{self.status.value} requires fetched_final_url")
            if self.retrieved_at is None:
                raise ValueError(f"{self.status.value} requires retrieved_at")
            if self.status is MicronAliasEligibilityStatus.HOST_ESCAPED:
                # An escaped final URL must actually be outside the origin —
                # a URL inside the origin is not an escape.
                if url_within_origin(
                    self.fetched_final_url, MICRON_7500_APPROVED_ORIGIN
                ):
                    raise ValueError(
                        "HOST_ESCAPED requires fetched_final_url outside the "
                        "approved origin"
                    )
                for name in ("source_name", "body_sha256"):
                    if getattr(self, name) is not None:
                        raise ValueError(
                            f"HOST_ESCAPED must not carry {name} (the source "
                            "was not held inside the approved origin)"
                        )
            else:
                if not url_within_origin(
                    self.fetched_final_url, MICRON_7500_APPROVED_ORIGIN
                ):
                    raise ValueError(
                        f"{self.status.value} requires fetched_final_url inside "
                        "the approved origin"
                    )
                if self.source_name != MICRON_7500_SOURCE_NAME:
                    raise ValueError(
                        f"{self.status.value} requires the reviewed source name"
                    )
                if self.body_sha256 is None:
                    raise ValueError(
                        f"{self.status.value} requires the body SHA-256 audit "
                        "value"
                    )

    # -- derived views ---------------------------------------------------

    @property
    def is_established(self) -> bool:
        """True only for the single authority-bearing status."""
        return self.status is _ESTABLISHED

    @property
    def can_supply_alias_relation(self) -> bool:
        """ESTABLISHED is the only status that may drive alias retrieval."""
        return self.is_established

    @property
    def can_supply_authority(self) -> bool:
        """ESTABLISHED is the only status that may supply manufacturer/
        category authority. Every other status is a bounded abstention."""
        return self.is_established


# ---------------------------------------------------------------------------
# 2A regression invariant (documented for tests and future phases)
# ---------------------------------------------------------------------------
#
# 4D-D must NEVER make any pair of family forms established under frozen 2A.
# The invariant, asserted by the test suite against ``compare_part_numbers``:
#
#     compare_part_numbers(BASE, BASE + "R")   -> UNKNOWN
#     compare_part_numbers(BASE, BASE + "T")   -> UNKNOWN
#     compare_part_numbers(BASE + "R", BASE + "T") -> UNKNOWN
#
# The alias relation above is retrieval metadata that rides alongside, but
# never into, that comparator.
