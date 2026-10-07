"""The universal semantic-decision persistence envelope foundation (S2-B /
S2-B-FU1).

PRODUCT-INTEL.SEMANTIC-AUTHORITY-V2-S2-B-FU1 decoupled the durable
persistence ENVELOPE from the semantic contract it contains. This module is
the version-independent foundation of that envelope. It owns:

* the canonical encoding discipline (``canonical_sha256``: sorted keys,
  compact separators, ASCII, no floats) and the bounded
  ``CanonicalDigestError``;
* the strict value-validation and strict JSON decode helpers shared by the
  universal envelope codec and the version-specific contract adapters
  (exact key sets, strict enums, explicit nullability, sorted-unique set
  encodings, float refusal);
* the universal persistence binding (run UUID, assessment index, source
  URL) — the addressing every semantic contract shares with the
  ``runs.SemanticDecisionRecord`` row — and its section encoding /
  validation;
* the bounded error vocabulary (``SemanticDecisionCodecError``,
  ``SemanticDecisionReplayError``) and the
  ``SemanticDecisionContractAdapter`` extension point.

The envelope's version axes are INDEPENDENT of one another:

    payload/envelope schema version
        (the format of the persisted JSON envelope; gated by
        ``semantic_decision_codec``)
    != semantic contract version
        (which semantic contract produced the evaluation; the payload's
        ``contract`` section dispatch key)
    != prompt version
    != semantic input / output schema versions
    != runtime route (provider/model) pinning

The opaque payload explicitly identifies its semantic contract version in
its ``contract`` section; the universal codec dispatches interpretation to a
REGISTERED version-specific contract adapter (currently exactly two: the
Semantic V1 adapter, ``research/semantic_decision_v1.py``, and the final
Semantic V2 adapter, ``research/semantic_decision_v2.py``). A future
semantic contract registers a future adapter; this module, the codec, the
replay dispatch, the runs model, and the migration own NO assumption that
any particular semantic contract version, prompt version, or provider/model
route is the only possible one.

Interpretation discipline: the storage/transport layer can durably
identify/version an artifact without assuming all future semantic contracts
are any one contract. Interpretation/replay, however, always requires a
registered, explicitly supported version-specific adapter — unknown or
future semantic contracts fail closed and are never silently reinterpreted
under a different contract.

This module is pure research-layer contract: stdlib only, no Django, no I/O,
no clock, no float authority data, no network.
"""

from __future__ import annotations

import hashlib
import json
import re
import uuid
from dataclasses import dataclass
from datetime import datetime
from typing import Final

__all__ = [
    "CanonicalDigestError",
    "SemanticDecisionCodecError",
    "SemanticDecisionContractAdapter",
    "SemanticDecisionReplayError",
    "canonical_sha256",
]


# ---------------------------------------------------------------------------
# Bounded error vocabulary (shared by the codec and the replay dispatch)
# ---------------------------------------------------------------------------


class CanonicalDigestError(ValueError):
    """A section value cannot be canonically encoded (not JSON-native)."""


class SemanticDecisionCodecError(ValueError):
    """Raised when a persisted semantic-decision payload cannot be decoded.

    Universal causes: an unsupported envelope schema version, an envelope
    framing mismatch between the row and the payload, a malformed universal
    binding, a payload that names a semantic contract version with no
    registered adapter, or float values anywhere in the payload.
    Version-specific causes (raised by a registered adapter): an unsupported
    or mismatched contract binding, malformed version-owned sections,
    missing or extra fields, unknown enums, wrong types, duplicate set
    members, and any structural failure of the adapter's record constructor
    during decode (including its self-verifying digest checks).

    Messages are bounded: they name the failing path, never raw payload
    content that may carry external text.
    """


class SemanticDecisionReplayError(ValueError):
    """The persisted artifact cannot be safely replayed.

    Bounded causes: an unknown / unsupported contract binding (including
    any future version this code does not know — the replay dispatch refuses
    it explicitly), recorded inputs that violate the bound contract, or
    stored derived audit snapshots that do not agree with re-derivation
    (tamper / version drift).

    Messages name the failing check, never raw payload content.
    """


# ---------------------------------------------------------------------------
# Canonical encoding + digests (universal discipline)
# ---------------------------------------------------------------------------

_TIMESTAMP_PATTERN = re.compile(
    r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(\.\d{1,6})?Z$"
)
_DIGEST_PATTERN = re.compile(r"^[0-9a-f]{64}$")


def canonical_sha256(value: object) -> str:
    """SHA-256 hex digest of the canonical JSON encoding of ``value``.

    Canonical encoding: sorted mapping keys, compact separators, ASCII.
    The value must be JSON-native (dict / list / str / int / bool / None) —
    this function refuses anything else rather than silently formatting it,
    and refuses floats outright (no float authority data).
    """
    _assert_json_native(value, "<canonical>")
    encoded = json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=True
    )
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()


def _assert_json_native(value: object, path: str) -> None:
    if value is None or isinstance(value, (str, bool)):
        return
    if isinstance(value, float):
        raise CanonicalDigestError(
            f"{path}: float values are not permitted in the canonical "
            "encoding (no float authority data, no lossy serialization)"
        )
    if isinstance(value, int):
        return
    if isinstance(value, dict):
        for key, item in value.items():
            if not isinstance(key, str):
                raise CanonicalDigestError(
                    f"{path}: mapping keys must be str, got "
                    f"{type(key).__name__}"
                )
            _assert_json_native(item, f"{path}.{key}")
        return
    if isinstance(value, (list, tuple)):
        for i, item in enumerate(value):
            _assert_json_native(item, f"{path}[{i}]")
        return
    raise CanonicalDigestError(
        f"{path}: value of type {type(value).__name__} is not JSON-native"
    )


# ---------------------------------------------------------------------------
# Strict value validation (shared by the adapters and the universal codec)
# ---------------------------------------------------------------------------


def _validate_timestamp(value: str | None, path: str) -> None:
    """Strict ISO-8601 UTC 'Z' instant grammar (microsecond precision)."""
    if value is None:
        return
    if not isinstance(value, str):
        raise TypeError(f"{path} must be str or None")
    if not _TIMESTAMP_PATTERN.match(value):
        raise ValueError(
            f"{path}: must be an ISO-8601 UTC instant ending in 'Z' "
            f"('YYYY-MM-DDTHH:MM:SS[.ffffff]Z'), got {value!r}"
        )
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        raise ValueError(
            f"{path}: not a valid calendar instant: {value!r}"
        ) from None
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise ValueError(f"{path}: must be a timezone-aware UTC instant")


def _validate_digest(value: str, path: str) -> None:
    if not isinstance(value, str) or not _DIGEST_PATTERN.match(value):
        raise ValueError(
            f"{path}: must be a 64-character lowercase hex SHA-256 digest"
        )


def _validate_str(
    value: object, path: str, *, allow_empty: bool = True
) -> None:
    if not isinstance(value, str):
        raise TypeError(f"{path} must be str, got {type(value).__name__}")
    if not allow_empty and not value:
        raise ValueError(f"{path} must be non-empty")


def _validate_str_tuple(value: object, path: str) -> None:
    if not isinstance(value, tuple):
        raise TypeError(f"{path} must be a tuple, got {type(value).__name__}")
    for i, item in enumerate(value):
        if not isinstance(item, str):
            raise TypeError(f"{path}[{i}] must be str, got {type(item).__name__}")


# ---------------------------------------------------------------------------
# Strict JSON decode helpers (shared by the adapters and the universal codec)
# ---------------------------------------------------------------------------


def _dec_mapping(raw: object, path: str) -> dict[str, object]:
    if not isinstance(raw, dict):
        raise SemanticDecisionCodecError(
            f"{path}: expected mapping, got {type(raw).__name__}"
        )
    return raw


def _dec_list(raw: object, path: str) -> list[object]:
    if not isinstance(raw, list):
        raise SemanticDecisionCodecError(
            f"{path}: expected list, got {type(raw).__name__}"
        )
    return raw


def _dec_required(
    data: dict[str, object], key: str, path: str
) -> object:
    if key not in data:
        raise SemanticDecisionCodecError(
            f"{path}: missing required key {key!r}"
        )
    return data[key]


def _check_keys(data: dict[str, object], allowed: frozenset[str], path: str) -> None:
    missing = allowed - set(data.keys())
    if missing:
        raise SemanticDecisionCodecError(
            f"{path}: missing required keys {sorted(missing)}"
        )
    extra = set(data.keys()) - allowed
    if extra:
        raise SemanticDecisionCodecError(
            f"{path}: unexpected keys {sorted(extra)}"
        )


def _dec_str(raw: object, path: str, *, allow_empty: bool = True) -> str:
    if not isinstance(raw, str):
        raise SemanticDecisionCodecError(
            f"{path}: expected string, got {type(raw).__name__}"
        )
    if not allow_empty and not raw:
        raise SemanticDecisionCodecError(f"{path}: must be non-empty")
    return raw


def _dec_optional_str(raw: object, path: str) -> str | None:
    if raw is None:
        return None
    return _dec_str(raw, path)


def _dec_int(raw: object, path: str) -> int:
    if isinstance(raw, bool) or not isinstance(raw, int):
        raise SemanticDecisionCodecError(
            f"{path}: expected int, got {type(raw).__name__}"
        )
    return raw


def _dec_bool(raw: object, path: str) -> bool:
    if not isinstance(raw, bool):
        raise SemanticDecisionCodecError(
            f"{path}: expected bool, got {type(raw).__name__}"
        )
    return raw


def _dec_str_enum(enum_cls: type, raw: object, path: str):
    """Decode a string into an exact enum member; unknown values fail."""
    value = _dec_str(raw, path, allow_empty=False)
    for member in enum_cls:
        if member.value == value:
            return member
    raise SemanticDecisionCodecError(
        f"{path}: unknown {enum_cls.__name__} value {value!r}"
    )


def _dec_optional_str_enum(enum_cls: type, raw: object, path: str):
    if raw is None:
        return None
    return _dec_str_enum(enum_cls, raw, path)


def _dec_sorted_unique_str_list(raw: object, path: str) -> list[str]:
    """Decode a sorted list of unique non-empty strings (set encoding).

    The canonical form of a frozenset is its sorted unique values; a list
    that is not sorted or has duplicates is not the strict encoding and is
    rejected (no lossy collapsing).
    """
    items = _dec_list(raw, path)
    out: list[str] = []
    for i, item in enumerate(items):
        out.append(_dec_str(item, f"{path}[{i}]", allow_empty=False))
    if out != sorted(out):
        raise SemanticDecisionCodecError(
            f"{path}: set values must be encoded in sorted order"
        )
    if len(out) != len(set(out)):
        raise SemanticDecisionCodecError(
            f"{path}: set values must be unique"
        )
    return out


def _dec_str_list(raw: object, path: str) -> tuple[str, ...]:
    """Decode an order-significant list of strings."""
    items = _dec_list(raw, path)
    return tuple(_dec_str(item, f"{path}[{i}]") for i, item in enumerate(items))


def _refuse_floats_anywhere(value: object, path: str) -> None:
    """Walk a persisted payload and refuse float values outright.

    No float authority data, no lossy serialization: a float anywhere in a
    persisted semantic artifact is rejected, not rounded. Universal
    discipline — every registered contract adapter's payload is subject to
    it.
    """
    if isinstance(value, dict):
        for key, item in value.items():
            _refuse_floats_anywhere(item, f"{path}.{key}")
        return
    if isinstance(value, list):
        for i, item in enumerate(value):
            _refuse_floats_anywhere(item, f"{path}[{i}]")
        return
    if isinstance(value, float):
        raise SemanticDecisionCodecError(
            f"{path}: float values are not permitted in a semantic "
            "decision payload (no float authority data)"
        )


# ---------------------------------------------------------------------------
# The universal persistence binding (shared by every semantic contract)
# ---------------------------------------------------------------------------

#: The exact key set of the universal envelope binding section. This is the
#: addressing contract between the payload and the
#: ``runs.SemanticDecisionRecord`` row (one record per (run,
#: assessment_index), bound to the listing's source URL). It is a property
#: of the persistence envelope, not of any semantic contract version.
_BINDING_KEYS: Final[frozenset[str]] = frozenset(
    {"run_id", "assessment_index", "source_url"}
)


def _binding_section(
    run_id: str, assessment_index: int, source_url: str
) -> dict[str, object]:
    """The universal binding section (every adapter payload carries it)."""
    return {
        "run_id": run_id,
        "assessment_index": assessment_index,
        "source_url": source_url,
    }


def _validate_binding_fields(
    run_id: object, assessment_index: object, source_url: object
) -> None:
    """Validate the universal persistence binding (fail closed).

    ``run_id`` must be a canonical UUID string (the run's identity in the
    persistence row); ``assessment_index`` a non-negative int (the stable
    position in the run's ordered assessment tuple); ``source_url`` a
    non-empty string (the listing's stable identity).
    """
    _validate_str(run_id, "run_id", allow_empty=False)
    try:
        parsed_run = uuid.UUID(run_id)
    except ValueError:
        raise ValueError(
            f"run_id must be a canonical UUID string, got {run_id!r}"
        ) from None
    if str(parsed_run) != run_id:
        raise ValueError(
            f"run_id must be in canonical UUID form, got {run_id!r}"
        )
    if isinstance(assessment_index, bool) or not isinstance(
        assessment_index, int
    ):
        raise TypeError(
            "assessment_index must be int, "
            f"got {type(assessment_index).__name__}"
        )
    if assessment_index < 0:
        raise ValueError(
            f"assessment_index must be >= 0, got {assessment_index}"
        )
    _validate_str(source_url, "source_url", allow_empty=False)


# ---------------------------------------------------------------------------
# The version-adapter extension point
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class SemanticDecisionContractAdapter:
    """A registered, version-specific semantic contract adapter.

    The universal persistence envelope (the runs row, the codec's framing
    and dispatch, the replay dispatch, the persistence service) is
    contract-agnostic; ALL semantic-contract-specific interpretation lives
    in a registered adapter:

    * ``envelope_schema_version`` — the payload format version this adapter
      speaks (the row's ``schema_version``);
    * ``semantic_contract_version`` — the semantic contract identity this
      adapter interprets (the payload's ``contract`` dispatch key);
    * ``supported_bindings`` — the EXACT (semantic contract, prompt, input
      schema, output schema, authority contract) tuples this adapter
      interprets and replays; anything else fails closed;
    * ``record_type`` — the adapter's validated typed record. Every adapter
      record exposes the universal binding attributes (``run_id``,
      ``assessment_index``, ``source_url``) and the contract-identity
      attributes (``semantic_contract_version``, ``prompt_version``,
      ``input_schema_version``, ``output_schema_version``,
      ``authority_contract_version``).

    Registering a new semantic contract (e.g. the final S2-C contract) is a
    matter of adding a new adapter and a registry entry — the persistence
    envelope, the migration, the row, and the service do not change.
    Unknown / future semantic contracts are never interpreted implicitly.
    """

    envelope_schema_version: int
    semantic_contract_version: str
    supported_bindings: tuple[tuple[str, str, int, int, str], ...]
    record_type: type

    def encode(self, record: object) -> dict[str, object]:
        """Encode the adapter's typed record into the full framed payload."""
        raise NotImplementedError

    def decode(self, payload: dict[str, object]) -> object:
        """Strictly decode an already-dispatched payload into the adapter's
        validated typed record (raises ``SemanticDecisionCodecError``)."""
        raise NotImplementedError

    def replay(self, record: object) -> object:
        """The adapter's pure zero-live replay of its typed record (raises
        ``SemanticDecisionReplayError``)."""
        raise NotImplementedError

    def run_binding_violation(
        self,
        record: object,
        *,
        request_mpn: str,
        request_description: str,
    ) -> str | None:
        """The adapter-specific check that the record's recorded request
        identity binds to the run's canonical request. Returns a bounded
        violation message, or None when the binding holds. The universal
        parts (the row exists, the digest verifies, the recorded index is in
        range, the recorded source URL matches the run's persisted
        assessment at that index) are checked by the service, not here."""
        return None
