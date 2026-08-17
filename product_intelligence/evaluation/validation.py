"""Deterministic validation of the evaluation corpus.

Parsing and validation are the same pass: a raw JSON-decoded object either
becomes a fully valid ``EvaluationCase``, or raises ``CorpusValidationError``
naming the case and the field. Nothing half-valid is representable, so a
consumer never has to re-check what the loader already accepted.

Everything here is pure: dictionaries in, case objects out. No file access, no
clock, no network — in particular, ``source_url`` is validated as a string and
is never fetched.

Unknown keys are rejected everywhere. A corpus is a benchmark reviewed by
people; a typo that silently does nothing (``challenge_tag`` instead of
``challenge_tags``) would quietly weaken it.
"""

from __future__ import annotations

from datetime import date
from typing import Any, Iterable, Mapping, Sequence

from product_intelligence.domain import DomainValidationError
from product_intelligence.evaluation.cases import (
    AuthoritativeProvenance,
    CaseInput,
    EvaluationCase,
    EvaluationCorpus,
    Expectation,
    SyntheticProvenance,
)
from product_intelligence.evaluation.vocabulary import (
    AUTHORITATIVE_PROVENANCE_KINDS,
    CaseKind,
    ChallengeTag,
    ExpectedResolution,
    ProvenanceKind,
)

SUPPORTED_CORPUS_VERSION = 1
"""The only corpus file format this code understands.

Bumping it is a deliberate act with a migration, not a silent tolerance of two
shapes at once.
"""

# A case id is a stable handle that later phases, reports, and review notes
# refer to. Uppercase and punctuation-light so it survives being pasted into a
# spreadsheet, a URL, or a commit message unchanged.
_CASE_ID_ALLOWED_CHARACTERS = frozenset("ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-")

_FILE_REQUIRED_KEYS = frozenset({"corpus_version", "declared_case_kind", "cases"})
_FILE_OPTIONAL_KEYS = frozenset({"note"})

_CASE_REQUIRED_KEYS = frozenset(
    {"case_id", "case_kind", "input", "expectation", "challenge_tags", "provenance"}
)
_CASE_OPTIONAL_KEYS = frozenset({"notes", "deliberately_shares_identity"})

_INPUT_REQUIRED_KEYS = frozenset({"manufacturer_part_number", "description"})

_EXPECTATION_REQUIRED_KEYS = frozenset({"resolution"})
_EXPECTATION_OPTIONAL_KEYS = frozenset(
    {
        "manufacturer",
        "canonical_manufacturer_part_number",
        "product_name",
        "product_family",
        "must_not_resolve_to",
        "reason",
    }
)

_AUTHORITATIVE_PROVENANCE_REQUIRED_KEYS = frozenset(
    {"kind", "source_name", "source_url", "verification_note", "verified_on"}
)
_SYNTHETIC_PROVENANCE_REQUIRED_KEYS = frozenset({"kind", "construction"})
_SYNTHETIC_PROVENANCE_OPTIONAL_KEYS = frozenset({"derived_from_case_ids"})

# Provenance URLs are recorded so a human can re-check a claim. Requiring https
# is a string-level sanity check on the recorded citation; it is emphatically
# not a reachability check, and nothing in this module opens a connection.
_REQUIRED_URL_PREFIX = "https://"


class CorpusValidationError(ValueError):
    """Raised when a corpus record violates the evaluation corpus contract.

    Distinct from ``DomainValidationError``: that one means a runtime contract
    was misused, this one means the benchmark data itself is malformed.
    """


def _fail(where: str, message: str) -> None:
    raise CorpusValidationError(f"{where}: {message}")


def _require_mapping(value: Any, where: str) -> Mapping[str, Any]:
    if not isinstance(value, dict):
        _fail(where, f"expected an object, got {type(value).__name__}")
    return value


def _require_keys(
    mapping: Mapping[str, Any],
    where: str,
    *,
    required: Iterable[str],
    optional: Iterable[str] = (),
) -> None:
    present = set(mapping)
    missing = sorted(set(required) - present)
    if missing:
        _fail(where, f"missing required field(s) {missing}")
    unknown = sorted(present - set(required) - set(optional))
    if unknown:
        _fail(where, f"unknown field(s) {unknown}")


def _require_text(mapping: Mapping[str, Any], key: str, where: str) -> str:
    value = mapping[key]
    if not isinstance(value, str):
        _fail(f"{where}.{key}", f"expected a string, got {type(value).__name__}")
    if not value.strip():
        _fail(f"{where}.{key}", "must not be empty")
    return value


def _optional_text(mapping: Mapping[str, Any], key: str, where: str) -> str | None:
    if key not in mapping:
        return None
    return _require_text(mapping, key, where)


def _require_verbatim_text(mapping: Mapping[str, Any], key: str, where: str) -> str:
    """A case input value: any string, whitespace and emptiness included.

    Whitespace and emptiness are exactly what several challenge classes are
    made of, so nothing is stripped or rejected here.
    """
    value = mapping[key]
    if not isinstance(value, str):
        _fail(f"{where}.{key}", f"expected a string, got {type(value).__name__}")
    return value


def _require_enum(mapping: Mapping[str, Any], key: str, where: str, enum_cls: Any) -> Any:
    raw = mapping[key]
    if not isinstance(raw, str):
        _fail(f"{where}.{key}", f"expected a string, got {type(raw).__name__}")
    try:
        return enum_cls(raw)
    except ValueError:
        allowed = sorted(member.value for member in enum_cls)
        _fail(f"{where}.{key}", f"{raw!r} is not one of {allowed}")


def _require_string_sequence(
    mapping: Mapping[str, Any], key: str, where: str
) -> tuple[str, ...]:
    if key not in mapping:
        return ()
    raw = mapping[key]
    if not isinstance(raw, list):
        _fail(f"{where}.{key}", f"expected a list, got {type(raw).__name__}")
    values: list[str] = []
    for index, item in enumerate(raw):
        position = f"{where}.{key}[{index}]"
        if not isinstance(item, str):
            _fail(position, f"expected a string, got {type(item).__name__}")
        if not item.strip():
            _fail(position, "must not be empty")
        values.append(item)
    duplicates = sorted({value for value in values if values.count(value) > 1})
    if duplicates:
        _fail(f"{where}.{key}", f"contains duplicate entries {duplicates}")
    return tuple(values)


def _require_bool(mapping: Mapping[str, Any], key: str, where: str, default: bool) -> bool:
    if key not in mapping:
        return default
    value = mapping[key]
    if not isinstance(value, bool):
        _fail(f"{where}.{key}", f"expected a boolean, got {type(value).__name__}")
    return value


def _build_input(raw: Any, where: str) -> CaseInput:
    mapping = _require_mapping(raw, where)
    _require_keys(mapping, where, required=_INPUT_REQUIRED_KEYS)

    case_input = CaseInput(
        manufacturer_part_number=_require_verbatim_text(
            mapping, "manufacturer_part_number", where
        ),
        description=_require_verbatim_text(mapping, "description", where),
    )

    # Every case must be something a caller could actually submit. Proving it
    # against the real contract — rather than re-deriving the rule here — is
    # what keeps the corpus and the intake boundary from drifting apart.
    try:
        case_input.as_research_request()
    except DomainValidationError as error:
        _fail(where, f"is not a valid ResearchRequest ({error})")

    return case_input


def _build_expectation(raw: Any, where: str) -> Expectation:
    mapping = _require_mapping(raw, where)
    _require_keys(
        mapping,
        where,
        required=_EXPECTATION_REQUIRED_KEYS,
        optional=_EXPECTATION_OPTIONAL_KEYS,
    )

    resolution = _require_enum(mapping, "resolution", where, ExpectedResolution)
    expectation = Expectation(
        resolution=resolution,
        manufacturer=_optional_text(mapping, "manufacturer", where),
        canonical_manufacturer_part_number=_optional_text(
            mapping, "canonical_manufacturer_part_number", where
        ),
        product_name=_optional_text(mapping, "product_name", where),
        product_family=_optional_text(mapping, "product_family", where),
        must_not_resolve_to=_require_string_sequence(
            mapping, "must_not_resolve_to", where
        ),
        reason=_optional_text(mapping, "reason", where),
    )

    if resolution is ExpectedResolution.EXACT_IDENTITY:
        if expectation.canonical_manufacturer_part_number is None:
            _fail(
                where,
                "EXACT_IDENTITY requires canonical_manufacturer_part_number; an "
                "exact answer the corpus cannot name is not an expectation",
            )
        if expectation.manufacturer is None:
            _fail(where, "EXACT_IDENTITY requires manufacturer")
    else:
        if expectation.canonical_manufacturer_part_number is not None:
            _fail(
                where,
                f"{resolution.value} must not claim a "
                "canonical_manufacturer_part_number; expecting abstention and "
                "naming the answer at the same time is a contradiction",
            )
        if expectation.reason is None:
            _fail(
                where,
                f"{resolution.value} requires reason, explaining why abstention "
                "is the correct answer",
            )

    forbidden = expectation.must_not_resolve_to
    canonical = expectation.canonical_manufacturer_part_number
    if canonical is not None and canonical in forbidden:
        _fail(
            where,
            f"must_not_resolve_to forbids {canonical!r}, which is also the "
            "expected canonical identity",
        )

    return expectation


def _build_provenance(
    raw: Any, where: str, *, case_kind: CaseKind
) -> AuthoritativeProvenance | SyntheticProvenance:
    mapping = _require_mapping(raw, where)
    if "kind" not in mapping:
        _fail(where, "missing required field ['kind']")
    kind = _require_enum(mapping, "kind", where, ProvenanceKind)

    if case_kind is CaseKind.REAL_VERIFIED:
        if kind not in AUTHORITATIVE_PROVENANCE_KINDS:
            _fail(
                where,
                f"a REAL_VERIFIED case requires authoritative provenance; "
                f"{kind.value} is not authoritative",
            )
        _require_keys(
            mapping, where, required=_AUTHORITATIVE_PROVENANCE_REQUIRED_KEYS
        )
        source_url = _require_text(mapping, "source_url", where)
        if not source_url.startswith(_REQUIRED_URL_PREFIX):
            _fail(
                f"{where}.source_url",
                f"must start with {_REQUIRED_URL_PREFIX!r} (recorded as data; "
                "never fetched)",
            )
        verified_on_raw = _require_text(mapping, "verified_on", where)
        try:
            verified_on = date.fromisoformat(verified_on_raw)
        except ValueError:
            _fail(f"{where}.verified_on", f"{verified_on_raw!r} is not an ISO date")
        return AuthoritativeProvenance(
            kind=kind,
            source_name=_require_text(mapping, "source_name", where),
            source_url=source_url,
            verification_note=_require_text(mapping, "verification_note", where),
            verified_on=verified_on,
        )

    # Synthetic. The strict key check is what stops a constructed case from
    # carrying source-shaped provenance: a fabricated citation would read as
    # authoritative to a later reviewer, which is worse than having none.
    if kind is not ProvenanceKind.SYNTHETIC_CONSTRUCTION:
        _fail(
            where,
            f"a SYNTHETIC case requires SYNTHETIC_CONSTRUCTION provenance, not "
            f"{kind.value}; a constructed case must never present itself as "
            "sourced",
        )
    _require_keys(
        mapping,
        where,
        required=_SYNTHETIC_PROVENANCE_REQUIRED_KEYS,
        optional=_SYNTHETIC_PROVENANCE_OPTIONAL_KEYS,
    )
    return SyntheticProvenance(
        kind=kind,
        construction=_require_text(mapping, "construction", where),
        derived_from_case_ids=_require_string_sequence(
            mapping, "derived_from_case_ids", where
        ),
    )


def _build_challenge_tags(raw: Any, where: str) -> tuple[ChallengeTag, ...]:
    if not isinstance(raw, list):
        _fail(where, f"expected a list, got {type(raw).__name__}")
    if not raw:
        _fail(where, "at least one challenge tag is required")

    tags: list[ChallengeTag] = []
    for index, item in enumerate(raw):
        position = f"{where}[{index}]"
        if not isinstance(item, str):
            _fail(position, f"expected a string, got {type(item).__name__}")
        try:
            tag = ChallengeTag(item)
        except ValueError:
            allowed = sorted(member.value for member in ChallengeTag)
            _fail(position, f"{item!r} is not one of {allowed}")
        if tag in tags:
            _fail(position, f"{item!r} is listed more than once")
        tags.append(tag)
    return tuple(tags)


def build_case(raw: Any, *, declared_case_kind: CaseKind, where: str) -> EvaluationCase:
    """Validate one raw case record and return it as an ``EvaluationCase``."""
    mapping = _require_mapping(raw, where)
    _require_keys(
        mapping, where, required=_CASE_REQUIRED_KEYS, optional=_CASE_OPTIONAL_KEYS
    )

    case_id = _require_text(mapping, "case_id", where)
    if set(case_id) - _CASE_ID_ALLOWED_CHARACTERS:
        _fail(
            f"{where}.case_id",
            f"{case_id!r} must use only uppercase letters, digits, and hyphens",
        )
    where = f"{where} ({case_id})"

    case_kind = _require_enum(mapping, "case_kind", where, CaseKind)
    if case_kind is not declared_case_kind:
        _fail(
            where,
            f"declares case_kind {case_kind.value} in a "
            f"{declared_case_kind.value} corpus file; real and synthetic cases "
            "are kept apart so neither can be mistaken for the other",
        )

    return EvaluationCase(
        case_id=case_id,
        case_kind=case_kind,
        input=_build_input(mapping["input"], f"{where}.input"),
        expectation=_build_expectation(
            mapping["expectation"], f"{where}.expectation"
        ),
        challenge_tags=_build_challenge_tags(
            mapping["challenge_tags"], f"{where}.challenge_tags"
        ),
        provenance=_build_provenance(
            mapping["provenance"], f"{where}.provenance", case_kind=case_kind
        ),
        notes=_optional_text(mapping, "notes", where),
        deliberately_shares_identity=_require_bool(
            mapping, "deliberately_shares_identity", where, default=False
        ),
    )


def build_corpus_file(payload: Any, *, where: str) -> tuple[EvaluationCase, ...]:
    """Validate one decoded corpus file and return its cases."""
    mapping = _require_mapping(payload, where)
    _require_keys(
        mapping, where, required=_FILE_REQUIRED_KEYS, optional=_FILE_OPTIONAL_KEYS
    )

    version = mapping["corpus_version"]
    if isinstance(version, bool) or not isinstance(version, int):
        _fail(f"{where}.corpus_version", "expected an integer")
    if version != SUPPORTED_CORPUS_VERSION:
        _fail(
            f"{where}.corpus_version",
            f"{version} is not the supported version {SUPPORTED_CORPUS_VERSION}",
        )

    declared_case_kind = _require_enum(mapping, "declared_case_kind", where, CaseKind)
    _optional_text(mapping, "note", where)

    raw_cases = mapping["cases"]
    if not isinstance(raw_cases, list):
        _fail(f"{where}.cases", f"expected a list, got {type(raw_cases).__name__}")
    if not raw_cases:
        _fail(f"{where}.cases", "must contain at least one case")

    return tuple(
        build_case(
            raw_case,
            declared_case_kind=declared_case_kind,
            where=f"{where}.cases[{index}]",
        )
        for index, raw_case in enumerate(raw_cases)
    )


def validate_corpus(cases: Sequence[EvaluationCase]) -> EvaluationCorpus:
    """Check the invariants that only hold across cases, and build the corpus.

    Per-case validity is already settled by ``build_case``. What is left is
    everything a single record cannot know about itself: whether its id is
    unique, whether it silently duplicates a real identity, and whether the
    cases it claims to derive from exist.

    Challenge-tag coverage is deliberately *not* checked here — this function
    must be able to validate any corpus, including one file or a subset, and a
    coverage rule would make that impossible. The tests own coverage.
    """
    seen: dict[str, EvaluationCase] = {}
    for case in cases:
        if case.case_id in seen:
            _fail("corpus", f"duplicate case_id {case.case_id!r}")
        seen[case.case_id] = case

    real_identities: dict[str, list[EvaluationCase]] = {}
    for case in cases:
        if not case.is_real_verified:
            continue
        canonical = case.expectation.canonical_manufacturer_part_number
        if canonical is None:
            _fail(
                f"corpus ({case.case_id})",
                "a REAL_VERIFIED case must expect a canonical identity",
            )
        real_identities.setdefault(canonical, []).append(case)

    for canonical, sharing in real_identities.items():
        if len(sharing) == 1:
            continue
        accidental = [
            case.case_id for case in sharing if not case.deliberately_shares_identity
        ]
        if accidental:
            _fail(
                "corpus",
                f"REAL_VERIFIED cases {sorted(accidental)} repeat the identity "
                f"{canonical!r} without deliberately_shares_identity; a seed "
                "recorded twice by accident inflates the benchmark",
            )

    for case in cases:
        provenance = case.provenance
        if not isinstance(provenance, SyntheticProvenance):
            continue
        for referenced in provenance.derived_from_case_ids:
            if referenced not in seen:
                _fail(
                    f"corpus ({case.case_id})",
                    f"derived_from_case_ids references unknown case "
                    f"{referenced!r}",
                )
            if referenced == case.case_id:
                _fail(
                    f"corpus ({case.case_id})",
                    "derived_from_case_ids references the case itself",
                )

    return EvaluationCorpus(cases=tuple(cases))
