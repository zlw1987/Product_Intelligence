"""The universal zero-live replay dispatch for persisted semantic-decision
artifacts (S2-B / S2-B-FU1).

``replay_semantic_decision`` is the ZERO-LIVE reconstruction entry point:
from a persisted (decoded) adapter record it dispatches, on the EXPLICITLY
RECORDED contract/version identity, to the registered version-specific
contract adapter, whose replay reconstructs — under the EXACT contract
binding the artifact was produced under — the historical semantic
evaluation, the authority inputs, and the re-derivation agreement proof.

Contract-version discipline (the anti-reinterpretation rule)
------------------------------------------------------------

The universal dispatch owns NO semantic-contract-specific interpretation.
It knows the exact set of contract bindings this code can safely replay
(``SUPPORTED_CONTRACT_BINDINGS`` — the union of the registered adapters'
``supported_bindings``; the registry itself is the codec's explicit
version-adapter extension point) and refuses EXPLICITLY any other binding
(``SemanticDecisionReplayError``). A record bound to a semantic contract,
prompt, input/output schema, or authority contract version no registered
adapter knows — including a FUTURE newer version this code does not know —
is never silently reinterpreted under a newer contract, and the historical
recorded values are never substituted by current module constants: the
gate reads the RECORD's versions.

After the gate, dispatch selects the exact registered adapter whose
supported bindings contain the record's binding, and that adapter performs
the version-specific reconstruction, re-derivation, and
derived-agreement proof (the V1 adapter: the frozen V1 semantic contract,
prompt v1.1, the V1 pinned route, and the S2-A authority contract as
frozen through S2-A-FU2).

Zero live work
--------------

This module is pure: stdlib + the research contracts only. It imports no
runtime, no transport, no network or file I/O, no Django, and reads no
clock. It performs zero live AI calls and zero provider/network calls by
construction (the recorded values are re-read and re-derived by the
dispatched adapter, never re-requested). Boundary tests enforce the import
discipline; replay tests arm fail-fast sentinels on the live runtime and
network surfaces.
"""

from __future__ import annotations

from typing import Final

from product_intelligence.research.semantic_decision_codec import (
    _REGISTERED_SEMANTIC_CONTRACT_ADAPTERS,
    supported_contract_bindings,
)
from product_intelligence.research.semantic_decision_record import (
    SemanticDecisionReplayError,
)
from product_intelligence.research.semantic_decision_v1 import (
    SemanticDecisionReplay,
)

__all__ = [
    "SUPPORTED_CONTRACT_BINDINGS",
    "SemanticDecisionReplay",
    "SemanticDecisionReplayError",
    "replay_semantic_decision",
]


#: The exact (semantic contract, prompt, input schema, output schema,
#: authority contract) bindings this code can safely replay: the union of
#: the registered adapters' supported bindings. Currently one entry — the
#: frozen V1 semantic contract (prompt v1.1) under the S2-A authority
#: contract as frozen through S2-A-FU2, via the Semantic V1 adapter. A
#: future binding is a future registered adapter — never an implicit
#: reinterpretation.
SUPPORTED_CONTRACT_BINDINGS: Final[
    tuple[tuple[str, str, int, int, str], ...]
] = supported_contract_bindings()


def _contract_binding(record: object) -> tuple[str, str, int, int, str]:
    """The record's EXPLICITLY RECORDED contract identity (read from the
    record, never from current module constants). Every registered
    adapter record exposes the contract-identity attributes (the universal
    adapter-record convention)."""
    return (
        record.semantic_contract_version,
        record.prompt_version,
        record.input_schema_version,
        record.output_schema_version,
        record.authority_contract_version,
    )


def _adapter_for_binding(
    binding: tuple[str, str, int, int, str],
):
    """The registered adapter whose supported bindings contain
    ``binding`` (defensive: the gate above already verified membership in
    the union)."""
    for adapter in _REGISTERED_SEMANTIC_CONTRACT_ADAPTERS:
        if binding in adapter.supported_bindings:
            return adapter
    return None


def replay_semantic_decision(record: object) -> SemanticDecisionReplay:
    """Pure zero-live replay of one persisted semantic-decision record,
    dispatched by its explicitly recorded contract/version.

    Steps (each fails closed with ``SemanticDecisionReplayError``):

    1. **Contract-binding gate (universal).** The record's exact
       (semantic contract, prompt, input schema, output schema, authority
       contract) binding must be one this code can safely replay
       (``SUPPORTED_CONTRACT_BINDINGS`` — the union of the registered
       adapters' supported bindings). Unknown or future versions are
       refused explicitly — never silently reinterpreted, and never
       replayed "as if" the current module constants applied.
    2. **Explicit version-specific dispatch.** The registered adapter
       whose supported bindings contain the record's binding is selected;
       the version-owned interpretation (reconstruction, re-derivation
       under the bound authority contract, derived-agreement proof) is
       performed by THAT adapter alone.

    Performs zero live AI calls and zero provider/network calls: the
    recorded values are re-read and re-derived, never re-requested.
    """
    binding = _contract_binding(record)
    if binding not in SUPPORTED_CONTRACT_BINDINGS:
        raise SemanticDecisionReplayError(
            "unsupported contract binding "
            f"(semantic contract {binding[0]!r}, prompt {binding[1]!r}, "
            f"input schema {binding[2]}, output schema {binding[3]}, "
            f"authority contract {binding[4]!r}); this code cannot safely "
            "replay it and refuses to reinterpret a historical decision "
            "under a contract it does not know"
        )
    adapter = _adapter_for_binding(binding)
    if adapter is None:
        # Defensive: the gate verified membership in the union of the
        # registered adapters' supported bindings, so this cannot fire
        # unless the registry and the gate drifted apart. Fail closed.
        raise SemanticDecisionReplayError(
            "no registered contract adapter claims the record's binding; "
            "the replay dispatch is inconsistent and fails closed"
        )
    return adapter.replay(record)
