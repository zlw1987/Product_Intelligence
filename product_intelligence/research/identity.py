"""Deterministic part-number identity comparison (PRODUCT-INTEL.2A, 2A-FU1).

One primitive, with one question to answer:

```text
requested part number + candidate part number
        -> EXACT | NORMALIZED_EXACT | UNKNOWN
```

`NORMALIZED_EXACT` means the two values **differ only by an approved formatting
equivalence while describing the same identifier structure**. It does not mean
"the same alphanumeric characters survive after deleting separators" — that is
what 2A's first implementation did, and it was too permissive: it collapsed
`AB-C123` and `ABC-123` onto one key and reported them as the same part number
(2A-FU1, AD-037). Separator *position* is part of the identifier, so
normalization canonicalizes how a boundary was written and never whether one
exists.

What this module is *not*
-------------------------

**It is not product resolution.** An `EXACT` result says the two supplied
strings are the same part number under the canonical input semantics, and
nothing else. It does not say the manufacturer is right, that the description
agrees, that a listing genuinely belongs to the product, that specifications
match, or that the source is trustworthy. A request whose part number matches a
candidate exactly while its description names a different product still gets an
`EXACT` part-number comparison from here — detecting that cross-evidence
disagreement needs evidence this primitive does not have, and pretending
otherwise would make a narrow comparator quietly responsible for a conclusion it
cannot support.

**It holds no catalog.** No part number is mapped to a manufacturer, a product,
a family, or a category anywhere in this module, and none may be added. Those
facts exist in the evaluation corpus as benchmark truth; importing benchmark
answers into runtime resolution would be test leakage, and this package never
reads the corpus (`product_intelligence.evaluation` is a test-side dependency
only).

**It discovers nothing.** There is no search, no candidate source, no network,
no persistence, and no model call. Candidates arrive from somewhere else once a
later phase produces them; 2A only compares two strings it is handed.

**It scores nothing.** No numeric confidence is computed and no
`ConfidenceLevel` is assigned. Confidence is a judgement about evidence quality,
and a string comparison is not evidence quality — `EXACT` is not a synonym for
`HIGH`.

What "not established" means
----------------------------

Anything that is not `EXACT` or `NORMALIZED_EXACT` is `UNKNOWN`: part-number
identity was not established. `UNKNOWN` is a correct answer, not a failure, so
missing or unusable input returns it rather than raising. `CONFLICT` is
deliberately never returned — it means evidence is incompatible, and two
different strings are not enough to support that wider claim. `PARTIAL` is not
returned either: classifying partial part-number overlap is 3C's work, and
approximating it here would be exactly the recall-for-identity trade the design
forbids.
"""

from __future__ import annotations

from dataclasses import dataclass

from product_intelligence.domain import ResearchRequest
from product_intelligence.domain.enums import (
    ESTABLISHED_MATCH_TYPES,
    IdentityMatchType,
)

# ---------------------------------------------------------------------------
# The normalization profile
# ---------------------------------------------------------------------------
#
# One profile, written out character by character, because the difference
# between "formatting" and "data" is the whole of this phase and a reader has to
# be able to check it without running anything.
#
# ASCII whitespace. A run of it *inside* an identifier is how a person or a
# catalog wrote a separator, so it is canonicalized — not deleted. Deleting it
# would throw away the fact that a boundary is there at all.
ASCII_WHITESPACE: frozenset[str] = frozenset(" \t\n\r\f\v")

# What an internal whitespace run is written as in the normalized key. The
# hyphen is the marker because the equivalence this profile approves is exactly
# "an internal whitespace run and a hyphen at the same boundary are the same
# boundary" — the one formatting variation the evaluation corpus actually
# evidences (a part number written `bcm957504 n425g` for `BCM957504-N425G`).
CANONICAL_SEPARATOR = "-"

# Separators that are **data** in this profile: preserved exactly, and never
# interchangeable with a hyphen or with each other. `ABC_123`, `ABC/123`,
# `ABC.123`, and `ABC-123` are four different identifiers here.
#
# 2A originally treated all four as one interchangeable formatting class. That
# was a guess dressed as a rule: the corpus evidences one substitution, and five
# verified part numbers cannot show that every manufacturer treats every
# separator as decorative (AD-037). Widening this needs evidence, per separator.
PRESERVED_SEPARATORS: frozenset[str] = frozenset("_/.")

# Characters that can only ever be structure, never content. A value built
# purely from these carries no part number at all, however many characters it
# has — which is what stops `"-"` and `"_"` from being compared as though they
# were identifiers. Nothing else is in this set: `+`, `#`, `@`, `:`,
# parentheses, other punctuation, and every non-ASCII character are content.
#
# "Strip everything non-alphanumeric" is the tempting one-liner and it is wrong
# twice over: it erases characters that distinguish real products, and it widens
# by accident every time an unusual character appears.
STRUCTURAL_CHARACTERS: frozenset[str] = (
    ASCII_WHITESPACE | {CANONICAL_SEPARATOR} | PRESERVED_SEPARATORS
)

# ASCII-only case folding. `str.upper()` is deliberately not used: it applies
# Unicode case mappings that expand and rewrite characters (one code point
# becoming two, locale-shaped mappings), which is a semantic decision about
# identifier equivalence that no phase has approved. A part number is an
# identifier, so every non-ASCII code point *inside* it is carried through
# unchanged; surrounding whitespace is the one exception, and it follows
# `ResearchRequest` / `str.strip()` semantics, which are Unicode-aware.
_ASCII_CASE_FOLD = str.maketrans(
    "abcdefghijklmnopqrstuvwxyz", "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
)


def _canonical_text(value: str | None, field_name: str) -> str:
    """Return `value` with surrounding whitespace removed.

    This is the only rewriting `EXACT` tolerates, and it is deliberately the
    same operation `ResearchRequest` already performs on a requested part
    number — `str.strip()`, which removes Unicode whitespace as well as ASCII —
    so a request that came through the canonical contract is unchanged here and
    a candidate extracted from somewhere untidy is brought to the same footing.

    A missing value is `None` or empty, and both mean "no part number", which is
    an ordinary research outcome rather than an error. A value of the wrong
    *type* is a caller defect and raises.
    """
    if value is None:
        return ""
    if not isinstance(value, str):
        raise TypeError(
            f"{field_name} must be a string or None, got {type(value).__name__}"
        )
    return value.strip()


def _has_part_number_content(canonical_text: str) -> bool:
    """True when anything in the value is more than structure."""
    return any(
        character not in STRUCTURAL_CHARACTERS for character in canonical_text
    )


def _structural_key(canonical_text: str) -> str:
    """Fold ASCII case and write each internal whitespace run as one separator.

    Every other character — hyphens, the preserved separators, alphanumerics,
    unlisted punctuation, non-ASCII — is copied through in place, so the key has
    the same structure as the value it came from.
    """
    folded = canonical_text.translate(_ASCII_CASE_FOLD)

    key: list[str] = []
    in_whitespace_run = False
    for character in folded:
        if character in ASCII_WHITESPACE:
            # A run collapses to one separator: `ABC  123` and `ABC 123` were
            # written the same way, with a typist's extra space. Repeated
            # *punctuation* is not collapsed — see `normalize_part_number`.
            if not in_whitespace_run:
                key.append(CANONICAL_SEPARATOR)
                in_whitespace_run = True
            continue
        in_whitespace_run = False
        key.append(character)

    return "".join(key)


def normalize_part_number(value: str | None) -> str:
    """Return the comparison key for one part number.

    The algorithm, in full:

    1. surrounding whitespace is removed (`str.strip()`, as `ResearchRequest`
       does);
    2. a value carrying nothing but `STRUCTURAL_CHARACTERS` yields `""` — there
       is no part number in it to compare;
    3. ASCII letters `a-z` fold to `A-Z`, and nothing else is case-mapped;
    4. each run of internal ASCII whitespace becomes one `CANONICAL_SEPARATOR`;
    5. every other character is kept, in place.

    So the key **preserves the identifier's structure**. `ABC-123` keys to
    `ABC-123`, `abc 123` keys to `ABC-123`, and `ABC123` keys to `ABC123` — the
    first two describe the same identifier written two ways, and the third is a
    different identifier that happens to share its alphanumerics.

    What deliberately does *not* happen: no separator is deleted, none is
    substituted for another (`_`, `/`, and `.` are data), repeated punctuation
    is not collapsed (`ABC--123` keeps both hyphens, because no approved rule
    says a doubled hyphen is a single boundary), characters and tokens are not
    reordered, letters and digits are never removed, `O`/`0` and `I`/`l`/`1` are
    never interchanged, nothing is truncated, no prefix or suffix is guessed,
    and no fuzzy, edit-distance, similarity, or model-assisted comparison exists
    here or anywhere else in this module. A one-character alphanumeric
    difference stays a difference.

    Returns `""` for a missing part number and for a value that is only
    structure. Callers must not treat two empty keys as a match; see
    `compare_part_numbers`.
    """
    canonical_text = _canonical_text(value, "part number")
    if not _has_part_number_content(canonical_text):
        return ""
    return _structural_key(canonical_text)


@dataclass(frozen=True)
class PartNumberMatchAssessment:
    """The result of one deterministic part-number comparison.

    Immutable, and deliberately verbose enough to audit: a reviewer can see both
    values as they were compared, both normalized keys, and the outcome, and can
    re-derive the decision from those four strings without the code in front of
    them. That is why normalization is not hidden inside a boolean — a
    `NORMALIZED_EXACT` nobody can explain is not much better than a guess.

    The two part-number fields hold the values **as compared**: surrounding
    whitespace removed and nothing else, with a missing value represented as
    `""`. The normalized fields hold the keys produced by
    `normalize_part_number`, which keep the identifier's structure — so a
    reviewer can see that `bcm957504 n425g` and `BCM957504-N425G` both key to
    `BCM957504-N425G` and matched, while `AB-C123` keys to `AB-C123` against
    `ABC-123` and did not.

    There is deliberately no confidence, no score, no manufacturer, no product
    name, and no evidence attached. This is a comparison, not a conclusion, and
    it is not persisted — no model, no table, no row.
    """

    requested_part_number: str
    candidate_part_number: str
    normalized_requested_part_number: str
    normalized_candidate_part_number: str
    match_type: IdentityMatchType

    @property
    def is_established(self) -> bool:
        """True only for a part-number-level match, exact or normalized.

        Reads the same `ESTABLISHED_MATCH_TYPES` the domain uses, so this
        primitive and `ProductIdentity` cannot drift apart about what
        "established" means.
        """
        return self.match_type in ESTABLISHED_MATCH_TYPES

    @property
    def has_requested_part_number(self) -> bool:
        return bool(self.normalized_requested_part_number)

    @property
    def has_candidate_part_number(self) -> bool:
        return bool(self.normalized_candidate_part_number)


def compare_part_numbers(
    requested: str | None, candidate: str | None
) -> PartNumberMatchAssessment:
    """Compare a requested part number with a candidate one.

    The decision, in order:

    * **Either side carries no part-number content** — absent, empty, or nothing
      but structural characters — so nothing can be established: `UNKNOWN`. This
      test comes first on purpose. Without it, `"-"` against `"_"` would key to
      two empty strings, compare equal, and report an established identity built
      from no part number at all.
    * **The two values are character-for-character equal** after surrounding
      whitespace is removed: `EXACT`.
    * **Their normalized keys are equal**: `NORMALIZED_EXACT`. The values differ
      only by ASCII letter case and by how one structural boundary was written —
      an internal whitespace run against a hyphen. They describe the same
      identifier structure; a value with a boundary the other does not have is a
      different identifier, and `ABC-123` therefore does not match `ABC123`.
    * **Otherwise**: `UNKNOWN`. Not "nearly", not "partially", not "probably" —
      the comparison did not establish a part-number identity, and a later phase
      with real evidence may still say something useful about the pair.

    Raises `TypeError` if either argument is neither a string nor `None`. A
    missing part number never raises: "identity could not be established" is a
    research outcome, and only a structurally invalid argument is a caller bug.
    """
    requested_text = _canonical_text(requested, "requested part number")
    candidate_text = _canonical_text(candidate, "candidate part number")

    normalized_requested = normalize_part_number(requested_text)
    normalized_candidate = normalize_part_number(candidate_text)

    if not normalized_requested or not normalized_candidate:
        match_type = IdentityMatchType.UNKNOWN
    elif requested_text == candidate_text:
        match_type = IdentityMatchType.EXACT
    elif normalized_requested == normalized_candidate:
        match_type = IdentityMatchType.NORMALIZED_EXACT
    else:
        match_type = IdentityMatchType.UNKNOWN

    return PartNumberMatchAssessment(
        requested_part_number=requested_text,
        candidate_part_number=candidate_text,
        normalized_requested_part_number=normalized_requested,
        normalized_candidate_part_number=normalized_candidate,
        match_type=match_type,
    )


def compare_request_to_candidate(
    request: ResearchRequest, candidate_part_number: str | None
) -> PartNumberMatchAssessment:
    """Compare the part number a request carries with a candidate's.

    A convenience over `compare_part_numbers` that takes the canonical contract
    rather than a loose string, so callers consume `ResearchRequest` the way the
    rest of the system does. It reads one field and adds no rule of its own.

    A description-only request is entirely valid and simply has no part number
    to compare, so the result is `UNKNOWN`. Nothing here reads the description,
    infers a part number from it, or interprets it in any way: description
    semantics are not implemented, here or anywhere.
    """
    if not isinstance(request, ResearchRequest):
        raise TypeError(
            "a part-number comparison takes a canonical ResearchRequest, got "
            f"{type(request).__name__}"
        )

    return compare_part_numbers(
        request.manufacturer_part_number, candidate_part_number
    )
