"""The universal semantic-decision envelope codec (S2-B / S2-B-FU1).

Encodes a registered contract adapter's typed record into the opaque
versioned JSON-serialisable payload stored in the
``runs.SemanticDecisionRecord`` row, and decodes a persisted payload back
into the registered adapter's validated typed record.

PRODUCT-INTEL.SEMANTIC-AUTHORITY-V2-S2-B-FU1 made this codec
contract-agnostic. It is the universal STORAGE/TRANSPORT layer of the
semantic-decision envelope. It owns:

* the envelope schema version gate (``SEMANTIC_DECISION_SCHEMA_VERSION`` —
  the version of the persisted JSON ENVELOPE format; independent of the
  semantic contract version recorded inside the payload);
* the universal envelope framing: the payload's declared envelope version
  must agree with the row's, the universal binding section (run UUID,
  assessment index, source URL) is exact and validated here, and the
  payload's ``contract`` section must identify its semantic contract
  version (the dispatch key);
* the no-float discipline for every persisted payload;
* the adapter REGISTRY — the explicit version-adapter extension point:
  ``_REGISTERED_SEMANTIC_CONTRACT_ADAPTERS`` currently names exactly two
  adapters (the Semantic V1 adapter, ``research/semantic_decision_v1.py``,
  and the final Semantic V2 adapter, ``research/semantic_decision_v2.py``
  — registered in S2-C through this same explicit extension point).
  Decoding dispatches on the RECORDED (envelope schema version, semantic
  contract version) pair to the registered adapter; unknown or future
  semantic contracts fail closed with an explicit "no registered adapter"
  error — never best-effort decoded, never reinterpreted under a
  different contract;
* ``canonical_payload_digest`` — the whole-artifact tamper anchor value
  the persistence service stores in the row's separate digest column.

This module owns NO semantic-contract-specific assumption: no semantic
contract version is required to be any particular value, no prompt
version, no provider/model route, no section shape beyond the universal
framing. All of that lives in the registered version-specific adapters.

This module is **pure research-layer serialisation**. It may import stdlib
and research contracts. It must not import Django, ``runs``, ``web``,
``execution``, ``providers``, ``semantic``, ``evaluation``, network
libraries, or filesystem libraries.

The discipline follows the frozen price-result codec precedent:

* exact envelope schema version (anything unregistered fails closed — no
  best-effort migration, no permissive unknown-field acceptance);
* strict field sets at every level (missing keys AND extra keys rejected —
  the version-owned section shapes are enforced by the registered adapter);
* strict enums (unknown enum values rejected — a value the bound contract
  vocabulary does not define never decodes);
* no float authority data (refused anywhere in the payload, before
  dispatch);
* no lossy serialization (order-significant lists keep their order;
  order-insensitive sets are encoded sorted and duplicates are rejected);
* no silent defaulting of missing safety fields (nullable means the key is
  present with a null value; an absent key is a codec error);
* decode wraps every constructor/validation failure in the bounded
  ``SemanticDecisionCodecError``.

The payload is what the ``runs.SemanticDecisionRecord`` row stores in its
opaque ``payload`` column; the row's separate ``payload_digest`` column
holds ``canonical_payload_digest(payload)`` computed at write time, so a
whole-artifact tamper is provable from outside the payload itself.
"""

from __future__ import annotations

from typing import Final

from product_intelligence.research.semantic_decision_record import (
    SemanticDecisionCodecError,
    SemanticDecisionContractAdapter,
    _BINDING_KEYS,
    _binding_section,
    _check_keys,
    _dec_int,
    _dec_mapping,
    _dec_required,
    _dec_str,
    _refuse_floats_anywhere,
    _validate_binding_fields,
    canonical_sha256,
)
from product_intelligence.research.semantic_decision_v1 import (
    SEMANTIC_V1_ADAPTER,
)
from product_intelligence.research.semantic_decision_v2 import (
    SEMANTIC_V2_ADAPTER,
)

__all__ = [
    "SEMANTIC_DECISION_SCHEMA_VERSION",
    "SemanticDecisionCodecError",
    "adapter_for_record",
    "canonical_payload_digest",
    "decode_semantic_decision_record",
    "encode_semantic_decision_record",
    "registered_envelope_schema_versions",
    "registered_semantic_contract_adapter",
    "supported_contract_bindings",
]


SEMANTIC_DECISION_SCHEMA_VERSION: int = 1
"""The current semantic-decision payload ENVELOPE schema version — the
format version of the persisted JSON envelope (framing: declared envelope
version, universal binding, contract dispatch key, version-owned sections,
integrity sections) stored in the row.

This axis is INDEPENDENT of the semantic contract version recorded in the
payload's ``contract`` section: the envelope identifies which semantic
contract produced an artifact without assuming it is any particular one,
and the row's ``schema_version`` column tracks this envelope version (not
the semantic contract). A future semantic contract may reuse this envelope
format (registering a new adapter) or introduce a new envelope format
version (registering adapters for it) — either without redesigning the
other axis.
"""


# ---------------------------------------------------------------------------
# The adapter registry — the explicit version-adapter extension point
# ---------------------------------------------------------------------------


#: The registered version-specific semantic contract adapters, in
#: registration order. Currently exactly two: the Semantic V1 adapter
#: (envelope schema version 1, semantic contract V1 — the frozen FU3A
#: production semantic contract) and the final Semantic V2 adapter
#: (envelope schema version 1, semantic contract V2 — the S2-C final V2
#: contract, registered through the same explicit extension point: the
#: envelope, the row, the migration, and the service did not change).
#: Registering a future semantic contract is a matter of adding its
#: adapter here — the envelope, the row, the migration, and the service
#: do not change. Frozen tuple of frozen adapter instances: no mutable
#: global state.
_REGISTERED_SEMANTIC_CONTRACT_ADAPTERS: Final[
    tuple[SemanticDecisionContractAdapter, ...]
] = (
    SEMANTIC_V1_ADAPTER,
    SEMANTIC_V2_ADAPTER,
)


def registered_semantic_contract_adapter(
    envelope_schema_version: object,
    semantic_contract_version: object,
) -> SemanticDecisionContractAdapter | None:
    """The registered adapter for one (envelope schema version, semantic
    contract version) pair, or None when no adapter is registered for it.

    Interpretation of a persisted payload requires an explicit registered
    adapter: this lookup is the fail-closed dispatch of the universal
    codec. Unknown or future semantic contracts return None (and are
    refused), never guessed.
    """
    if isinstance(envelope_schema_version, bool) or not isinstance(
        envelope_schema_version, int
    ):
        raise TypeError(
            "envelope_schema_version must be int, got "
            f"{type(envelope_schema_version).__name__}"
        )
    if not isinstance(semantic_contract_version, str):
        raise TypeError(
            "semantic_contract_version must be str, got "
            f"{type(semantic_contract_version).__name__}"
        )
    for adapter in _REGISTERED_SEMANTIC_CONTRACT_ADAPTERS:
        if (
            adapter.envelope_schema_version == envelope_schema_version
            and adapter.semantic_contract_version == semantic_contract_version
        ):
            return adapter
    return None


def registered_envelope_schema_versions() -> tuple[int, ...]:
    """The envelope schema versions that have at least one registered
    adapter (the versions the universal codec can frame/decode)."""
    return tuple(
        sorted(
            {
                adapter.envelope_schema_version
                for adapter in _REGISTERED_SEMANTIC_CONTRACT_ADAPTERS
            }
        )
    )


def supported_contract_bindings() -> tuple[tuple[str, str, int, int, str], ...]:
    """The EXACT (semantic contract, prompt, input schema, output schema,
    authority contract) bindings this code can interpret and replay: the
    union of the registered adapters' ``supported_bindings``, in
    registration order. Anything outside this union fails closed."""
    return tuple(
        binding
        for adapter in _REGISTERED_SEMANTIC_CONTRACT_ADAPTERS
        for binding in adapter.supported_bindings
    )


def adapter_for_record(
    record: object,
) -> SemanticDecisionContractAdapter | None:
    """The registered adapter whose typed record ``record`` is an instance
    of, or None (an unregistered artifact type cannot be persisted or
    interpreted)."""
    for adapter in _REGISTERED_SEMANTIC_CONTRACT_ADAPTERS:
        if isinstance(record, adapter.record_type):
            return adapter
    return None


# ---------------------------------------------------------------------------
# Envelope framing
# ---------------------------------------------------------------------------


def canonical_payload_digest(payload: dict[str, object]) -> str:
    """The canonical SHA-256 digest of a full payload.

    This is what the persistence layer stores in the row's separate
    ``payload_digest`` column at write time and re-verifies at read time:
    a whole-artifact tamper anchor that cannot be regenerated from within
    the payload alone. Universal — it covers the entire payload whatever
    semantic contract produced it.
    """
    return canonical_sha256(payload)


def _decode_envelope(
    payload: dict[str, object], *, schema_version: int
) -> tuple[str, int, str, str]:
    """Validate the universal envelope framing of a payload.

    Returns (run_id, assessment_index, source_url, contract dispatch
    key). Checks, in order (each fails closed):

    * the payload's declared ``schema_version`` is present, is an int, and
      agrees with the row's envelope schema version (the envelope framing
      and the row must not disagree about the format);
    * the universal binding section is present, exact, and valid (run UUID
      canonical, assessment index non-negative int, source URL non-empty);
    * the ``contract`` section is present, is a mapping, and identifies its
      semantic contract version (a non-empty string — the dispatch key).

    Nothing else is assumed: the version-owned sections (and the rest of
    the contract section) are interpreted by the registered adapter.
    """
    declared = _dec_required(payload, "schema_version", "top-level")
    if isinstance(declared, bool) or not isinstance(declared, int):
        raise SemanticDecisionCodecError(
            f"top-level.schema_version: expected int, got "
            f"{type(declared).__name__}"
        )
    if declared != schema_version:
        raise SemanticDecisionCodecError(
            f"top-level.schema_version {declared} does not match the "
            f"row's envelope schema_version {schema_version}; the stored "
            "payload's envelope framing and the row disagree"
        )

    binding = _dec_mapping(
        _dec_required(payload, "binding", "top-level"), "binding"
    )
    _check_keys(binding, _BINDING_KEYS, "binding")
    run_id = _dec_str(
        _dec_required(binding, "run_id", "binding"),
        "binding.run_id",
        allow_empty=False,
    )
    assessment_index = _dec_int(
        _dec_required(binding, "assessment_index", "binding"),
        "binding.assessment_index",
    )
    source_url = _dec_str(
        _dec_required(binding, "source_url", "binding"),
        "binding.source_url",
        allow_empty=False,
    )
    try:
        _validate_binding_fields(run_id, assessment_index, source_url)
    except (TypeError, ValueError):
        raise SemanticDecisionCodecError(
            "the universal binding section is invalid; the payload does "
            "not carry a valid (run, assessment_index, source_url) "
            "envelope binding"
        ) from None

    contract = _dec_mapping(
        _dec_required(payload, "contract", "top-level"), "contract"
    )
    contract_key = _dec_str(
        _dec_required(contract, "semantic_contract_version", "contract"),
        "contract.semantic_contract_version",
        allow_empty=False,
    )
    return run_id, assessment_index, source_url, contract_key


def _check_encoded_envelope(
    payload: dict[str, object],
    adapter: SemanticDecisionContractAdapter,
    record: object,
) -> None:
    """Universal framing self-check after an adapter encode (defense in
    depth: a registered adapter is trusted, but the envelope invariants
    must hold in the produced payload)."""
    if not isinstance(payload, dict):
        raise SemanticDecisionCodecError(
            f"the {adapter.semantic_contract_version} adapter produced a "
            "non-mapping payload"
        )
    if payload.get("schema_version") != adapter.envelope_schema_version:
        raise SemanticDecisionCodecError(
            f"the {adapter.semantic_contract_version} adapter produced a "
            "payload whose declared envelope schema version does not match "
            "the adapter's"
        )
    expected_binding = _binding_section(
        record.run_id, record.assessment_index, record.source_url
    )
    if payload.get("binding") != expected_binding:
        raise SemanticDecisionCodecError(
            f"the {adapter.semantic_contract_version} adapter produced a "
            "payload whose binding section does not match the record's "
            "universal binding"
        )
    contract = payload.get("contract")
    if not isinstance(contract, dict) or contract.get(
        "semantic_contract_version"
    ) != adapter.semantic_contract_version:
        raise SemanticDecisionCodecError(
            f"the {adapter.semantic_contract_version} adapter produced a "
            "payload whose contract dispatch key does not match the "
            "adapter's semantic contract version"
        )


# ---------------------------------------------------------------------------
# Universal encode / decode entries
# ---------------------------------------------------------------------------


def encode_semantic_decision_record(
    record: object,
) -> dict[str, object]:
    """Encode a registered adapter's typed record into the opaque framed
    payload (the universal entry point of the write path).

    Dispatches on the record's type to its registered contract adapter
    (the adapter owns the version-owned sections: the contract identity,
    the version-specific body, and the version-specific integrity
    sections). The returned dict contains only native JSON types (str,
    int, bool, list, dict, None) — no enum members, no dataclass objects,
    no floats.

    Raises ``TypeError`` if the input is not a registered adapter's typed
    record (caller defect: an unregistered semantic contract cannot be
    persisted through this codec).
    """
    adapter = adapter_for_record(record)
    if adapter is None:
        raise TypeError(
            "encode_semantic_decision_record: expected a registered "
            "semantic-decision record artifact (see the codec's adapter "
            f"registry), got {type(record).__name__}"
        )
    payload = adapter.encode(record)
    _check_encoded_envelope(payload, adapter, record)
    return payload


def decode_semantic_decision_record(
    payload: object,
    *,
    schema_version: int,
) -> object:
    """Decode a persisted payload into the registered adapter's validated
    typed record (the universal entry point of the read path).

    The payload is treated as untrusted/corruptible state. The universal
    envelope checks, in order (each fails closed):

    * the row's ``schema_version`` must be an int naming an envelope
      format with at least one registered adapter (unsupported versions
      fail — no best-effort migration, no permissive acceptance);
    * the payload must be a mapping with no float values anywhere;
    * the universal envelope framing must hold (the payload's declared
      envelope version agrees with the row's; the binding is exact and
      valid; the ``contract`` section identifies its semantic contract
      version);
    * the RECORDED (envelope schema version, semantic contract version)
      pair must have a registered adapter — unknown or future semantic
      contracts are refused explicitly ("no registered adapter"), never
      decoded best-effort and never reinterpreted under a different
      contract.

    Interpretation of the version-owned sections (their exact shapes,
    enums, contract values, route rules, and integrity) is then delegated
    to the registered adapter, whose decode is strict and wraps every
    constructor/validation failure in the bounded
    ``SemanticDecisionCodecError``.

    Returns a fully validated adapter record or raises. Never returns a
    partially decoded object.
    """
    if isinstance(schema_version, bool) or not isinstance(schema_version, int):
        raise SemanticDecisionCodecError(
            f"schema_version must be int, got {type(schema_version).__name__}"
        )
    if schema_version not in registered_envelope_schema_versions():
        raise SemanticDecisionCodecError(
            f"unsupported schema_version {schema_version}; registered "
            f"envelope schema versions: {registered_envelope_schema_versions()} "
            "(no adapter is registered for this payload format)"
        )
    if not isinstance(payload, dict):
        raise SemanticDecisionCodecError(
            f"payload must be a mapping, got {type(payload).__name__}"
        )
    _refuse_floats_anywhere(payload, "top-level")
    _run_id, _assessment_index, _source_url, contract_key = (
        _decode_envelope(payload, schema_version=schema_version)
    )
    adapter = registered_semantic_contract_adapter(schema_version, contract_key)
    if adapter is None:
        raise SemanticDecisionCodecError(
            f"unsupported semantic contract version {contract_key!r} "
            f"(envelope schema version {schema_version}): no registered "
            "contract adapter interprets this payload; decoding fails "
            "closed (a historical decision is never reinterpreted under "
            "a different contract)"
        )
    try:
        return adapter.decode(payload)
    except SemanticDecisionCodecError:
        raise
    except (TypeError, ValueError):
        raise SemanticDecisionCodecError(
            f"stored semantic decision payload violates the "
            f"{contract_key} artifact contract"
        ) from None
