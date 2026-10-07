"""Architecture guards for the S2-B persisted semantic-decision envelope
(S2-B / S2-B-FU1).

S2-B-FU1 split the durable persistence ENVELOPE (contract-agnostic) from
the Semantic V1 contract adapter (version-specific). The guarded modules:

* ``semantic_decision_record.py`` — the universal envelope foundation
  (canonical encoding discipline, strict decode helpers, the universal
  persistence binding, bounded errors, the adapter extension point);
* ``semantic_decision_codec.py`` — the universal envelope codec (the
  envelope schema-version gate, the universal framing, the no-float
  discipline, the explicit adapter registry + fail-closed dispatch);
* ``semantic_decision_replay.py`` — the universal zero-live replay
  dispatch (exact-recorded-binding gate + explicit adapter selection);
* ``semantic_decision_v1.py`` — the FIRST registered version-specific
  adapter (the V1 contract identity, the V1 pinned route, the V1 section
  shapes, the V1 record, the V1 codec, the V1 replay, the V1
  run-binding check).

These guards enforce, mechanically:

* they import only stdlib and ``product_intelligence``;
* they import no persistence (django / runs), no providers, no web, no
  execution, no benchmark (evaluation), and NO production semantic runtime
  surface (semantic.* — the V1 adapter's mirror vocabularies exist
  precisely so the pure research layer never imports the runtime);
* they perform no network / file I/O and read no clock (timestamps are
  validated as strings, never produced);
* the V1 adapter's mirrored runtime-provenance vocabularies are drift-
  pinned to the frozen FU3A runtime (exact value sets, in order);
* the V1 adapter's mirrored route constants are drift-pinned to the
  frozen FU3A route;
* they carry no mutable global state;
* they name no external vendor or calling-system token;
* they do not reference the S2-A contract module by name (they consume
  the frozen V2 contract through the research package's public export
  surface);
* S2-B-FU1: the three UNIVERSAL modules own no Semantic V1 assumption
  (no V1 provider/model route tokens, no quoted V1 contract/prompt
  literals) — the V1 pins live ONLY in the V1 adapter module; the codec
  registry is the explicit version-adapter extension point (fail closed
  for every unregistered semantic contract).
"""

from __future__ import annotations

import ast
import sys
from pathlib import Path

import pytest

from tests.domain.test_domain_boundaries import (
    CALLER_TOKENS,
    VENDOR_TOKENS,
    _find_tokens,
)

REPO_ROOT = Path(__file__).resolve().parents[2]
RESEARCH_ROOT = REPO_ROOT / "product_intelligence" / "research"

MODULES = (
    RESEARCH_ROOT / "semantic_decision_record.py",
    RESEARCH_ROOT / "semantic_decision_codec.py",
    RESEARCH_ROOT / "semantic_decision_replay.py",
    RESEARCH_ROOT / "semantic_decision_v1.py",
)

#: The three contract-AGNOSTIC universal modules (the envelope foundation,
#: the universal codec, the universal replay dispatch). They must not own
#: any Semantic V1 assumption (S2-B-FU1).
UNIVERSAL_MODULES = MODULES[:3]

#: The V1 adapter module — the one place the V1 route/contract pins live.
V1_MODULE = RESEARCH_ROOT / "semantic_decision_v1.py"

#: The frozen FU3A V1 route tokens (provider/model pair, today's V1 route).
V1_ROUTE_TOKENS = (
    "amax",
    "qwen3.8-27b",
    "vllm-262k",
    "Qwen3.6-27B-262K",
)


def _imported_modules(path: Path) -> set[str]:
    modules: set[str] = set()
    for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
        if isinstance(node, ast.Import):
            modules.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module and not node.level:
            modules.add(node.module)
    return modules


# ---------------------------------------------------------------------------
# Import discipline
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("path", list(MODULES), ids=lambda p: p.name)
def test_imports_only_stdlib_and_product_intelligence(path: Path) -> None:
    modules = _imported_modules(path)
    disallowed = {
        module
        for module in modules
        if module.split(".")[0] != "product_intelligence"
        and module.split(".")[0] not in sys.stdlib_module_names
        and not module.split(".")[0].startswith("_")
    }
    assert not disallowed, f"{path.name} imports {sorted(disallowed)}"


@pytest.mark.parametrize("path", list(MODULES), ids=lambda p: p.name)
def test_imports_no_persistence_providers_web_execution_or_benchmark(
    path: Path,
) -> None:
    modules = _imported_modules(path)
    for forbidden in (
        "django",
        "product_intelligence.runs",
        "product_intelligence.providers",
        "product_intelligence.web",
        "product_intelligence.execution",
        "product_intelligence.evaluation",
    ):
        offending = {
            module
            for module in modules
            if module == forbidden or module.startswith(f"{forbidden}.")
        }
        assert not offending, f"{path.name} imports {sorted(offending)}"


@pytest.mark.parametrize("path", list(MODULES), ids=lambda p: p.name)
def test_imports_no_production_semantic_runtime_surface(path: Path) -> None:
    """The pure research layer never imports the semantic runtime /
    transport / contract: the artifact's runtime-provenance vocabularies
    are MIRRORS, drift-pinned below (exactly as V2SemanticDecision mirrors
    the frozen V1 decision vocabulary)."""
    modules = _imported_modules(path)
    offending = {
        module
        for module in modules
        if module == "product_intelligence.semantic"
        or module.startswith("product_intelligence.semantic.")
    }
    assert not offending, f"{path.name} imports {sorted(offending)}"


@pytest.mark.parametrize("path", list(MODULES), ids=lambda p: p.name)
def test_performs_no_network_or_file_io(path: Path) -> None:
    modules = _imported_modules(path)
    forbidden = {
        "requests",
        "httpx",
        "urllib.request",
        "urllib.error",
        "urllib.robotparser",
        "urllib3",
        "socket",
        "ssl",
        "http",
        "pathlib",
        "sqlite3",
        "os",
        "shutil",
        "tempfile",
        "subprocess",
        "webbrowser",
        "time",
    }
    offending = {
        module
        for module in modules
        for name in forbidden
        if module == name or module.startswith(f"{name}.")
    }
    assert not offending, f"{path.name} imports I/O modules {sorted(offending)}"


@pytest.mark.parametrize("path", list(MODULES), ids=lambda p: p.name)
def test_reads_no_clock(path: Path) -> None:
    """Timestamps in the artifact are validated as recorded strings; these
    modules never PRODUCE an instant (no clock read of any kind)."""
    source = path.read_text(encoding="utf-8")
    for token in (
        "utcnow",
        "datetime.now",
        "time.time",
        "time.monotonic",
        "perf_counter",
        "timezone.now",
    ):
        assert token not in source, f"{path.name} reads a clock: {token!r}"


@pytest.mark.parametrize("path", list(MODULES), ids=lambda p: p.name)
def test_does_not_reference_the_s2a_contract_module_by_name(path: Path) -> None:
    """The S2-A no-wiring lexical guard forbids the module name in every
    research file except the contract module and the package __init__
    (the public export surface). Pin it here for the S2-B modules
    explicitly: they consume the frozen V2 contract through the package's
    public exports, never by module name."""
    source = path.read_text(encoding="utf-8")
    assert "semantic_authority_v2" not in source, (
        f"{path.name} references the S2-A contract module by name; it must "
        "consume the frozen V2 contract through the research package's "
        "public export surface"
    )


# ---------------------------------------------------------------------------
# Mirror drift pins (artifact vocabularies == frozen FU3A runtime)
# ---------------------------------------------------------------------------


def test_mirror_attempt_outcome_vocabulary_is_pinned() -> None:
    from product_intelligence.research import AttemptOutcome
    from product_intelligence.semantic.runtime import SemanticAttemptStatus

    runtime = [member.value for member in SemanticAttemptStatus]
    artifact = [member.value for member in AttemptOutcome]
    assert artifact == runtime, (
        "the artifact's AttemptOutcome mirror has drifted from the frozen "
        f"runtime vocabulary; missing={set(runtime) - set(artifact)} "
        f"extra={set(artifact) - set(runtime)}"
    )


def test_mirror_failure_class_vocabulary_is_pinned() -> None:
    from product_intelligence.research import SemanticFailureClass
    from product_intelligence.semantic.runtime import (
        SemanticRuntimeErrorType,
    )

    runtime = [member.value for member in SemanticRuntimeErrorType]
    artifact = [member.value for member in SemanticFailureClass]
    assert artifact == runtime, (
        "the artifact's SemanticFailureClass mirror has drifted from the "
        "frozen runtime error-type vocabulary"
    )


def test_mirror_fallback_reason_vocabulary_is_pinned() -> None:
    from product_intelligence.research import SemanticFallbackReason
    from product_intelligence.semantic.runtime import (
        SemanticRuntimeFallbackReason,
    )

    runtime = [member.value for member in SemanticRuntimeFallbackReason]
    artifact = [member.value for member in SemanticFallbackReason]
    assert artifact == runtime, (
        "the artifact's SemanticFallbackReason mirror has drifted from the "
        "frozen runtime fallback-reason vocabulary"
    )


def test_mirror_prompt_version_is_pinned() -> None:
    from product_intelligence.research import PROMPT_VERSION_V1
    from product_intelligence.semantic.contract import SEMANTIC_PROMPT_VERSION

    assert PROMPT_VERSION_V1 == SEMANTIC_PROMPT_VERSION


def test_mirror_route_constants_are_pinned() -> None:
    from product_intelligence.research import (
        FALLBACK_MODEL_V1,
        FALLBACK_PROVIDER_V1,
        PRIMARY_MODEL_V1,
        PRIMARY_PROVIDER_V1,
    )
    from product_intelligence.semantic.runtime import (
        FALLBACK_MODEL,
        FALLBACK_PROVIDER,
        PRIMARY_MODEL,
        PRIMARY_PROVIDER,
    )

    assert PRIMARY_PROVIDER_V1 == PRIMARY_PROVIDER
    assert PRIMARY_MODEL_V1 == PRIMARY_MODEL
    assert FALLBACK_PROVIDER_V1 == FALLBACK_PROVIDER
    assert FALLBACK_MODEL_V1 == FALLBACK_MODEL


# ---------------------------------------------------------------------------
# Shape discipline
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("path", list(MODULES), ids=lambda p: p.name)
def test_no_mutable_global_state(path: Path) -> None:
    """Contract data in these modules is tuples / frozensets / scalars:
    no dict, list, or set survives at module level."""
    import importlib

    module = importlib.import_module(
        f"product_intelligence.research.{path.stem}"
    )
    mutable = {
        name: type(value).__name__
        for name, value in vars(module).items()
        if not name.startswith("__") and isinstance(value, (dict, list, set))
    }
    assert not mutable, f"{path.name} has mutable global state: {mutable}"


@pytest.mark.parametrize("path", list(MODULES), ids=lambda p: p.name)
def test_names_no_external_vendor_or_caller_system(path: Path) -> None:
    source = path.read_text(encoding="utf-8")
    assert not _find_tokens(source, VENDOR_TOKENS), path.name
    assert not _find_tokens(source, CALLER_TOKENS), path.name


def test_modules_exist_and_are_nonempty() -> None:
    for path in MODULES:
        assert path.exists(), path
        assert path.read_text(encoding="utf-8").strip(), path


def test_replay_module_is_exported_by_the_research_package() -> None:
    import product_intelligence.research as research

    expected = {
        # Universal envelope (S2-B-FU1): foundation / codec / dispatch /
        # registry.
        "SemanticDecisionContractAdapter",
        "SemanticDecisionCodecError",
        "SemanticDecisionReplayError",
        "SEMANTIC_DECISION_SCHEMA_VERSION",
        "SUPPORTED_CONTRACT_BINDINGS",
        "adapter_for_record",
        "canonical_payload_digest",
        "canonical_sha256",
        "decode_semantic_decision_record",
        "encode_semantic_decision_record",
        "registered_envelope_schema_versions",
        "registered_semantic_contract_adapter",
        "replay_semantic_decision",
        "supported_contract_bindings",
        # The registered Semantic V1 contract adapter (first version-
        # specific interpretation layer).
        "AttemptOutcome",
        "AttemptRole",
        "AUTHORITY_CONTRACT_VERSION",
        "FALLBACK_MODEL_V1",
        "FALLBACK_PROVIDER_V1",
        "PRIMARY_MODEL_V1",
        "PRIMARY_PROVIDER_V1",
        "PROMPT_VERSION_V1",
        "SEMANTIC_CONTRACT_VERSION",
        "SEMANTIC_INPUT_SCHEMA_VERSION",
        "SEMANTIC_OUTPUT_SCHEMA_VERSION",
        "SEMANTIC_V1_ADAPTER",
        "SemanticDecisionAttempt",
        "SemanticDecisionReplay",
        "SemanticDecisionRecordV1",
        "SemanticFallbackReason",
        "SemanticFailureClass",
        "SemanticPromptInput",
        "SemanticV1ContractAdapter",
        "V1_CONTRACT_BINDING",
        "reconstruct_identity_context",
        "reconstruct_semantic_evaluation",
        "record_input_digest",
        "record_output_digest",
        "replay_v1_record",
    }
    assert expected <= set(research.__all__)


def test_universal_modules_own_no_v1_assumption() -> None:
    """S2-B-FU1 proof: the universal storage/transport layer (envelope
    foundation, universal codec, universal replay dispatch) owns NO
    Semantic V1 assumption — no V1 provider/model route tokens and no
    quoted V1 contract/prompt literals. The V1 pins live only in the V1
    adapter module."""
    for path in UNIVERSAL_MODULES:
        source = path.read_text(encoding="utf-8")
        for token in V1_ROUTE_TOKENS:
            assert token not in source, (
                f"{path.name} owns the V1 route token {token!r}; the "
                "universal envelope must not assume today's V1 provider/"
                "model route (it belongs to the V1 adapter)"
            )
        # Quoted literals only: prose may say "V1"; the universal code
        # must not REQUIRE the literal value in a string constant.
        assert '"V1"' not in source, (
            f"{path.name} hardcodes the quoted V1 semantic-contract "
            "literal; the envelope identifies contracts via the recorded "
            "dispatch key, it does not assume one"
        )
        assert '"1.1"' not in source, (
            f"{path.name} hardcodes the quoted V1 prompt version; the "
            "prompt version is a V1-adapter pin, not an envelope rule"
        )


def test_v1_adapter_module_owns_the_v1_route_pin() -> None:
    """S2-B-FU1 proof (ownership side): the exact route validation lives
    in the V1 adapter module, which pins the frozen FU3A route."""
    source = V1_MODULE.read_text(encoding="utf-8")
    for token in V1_ROUTE_TOKENS:
        assert token in source, (
            f"the V1 adapter module lost its route pin {token!r}"
        )
    from product_intelligence.research import (
        FALLBACK_MODEL_V1,
        FALLBACK_PROVIDER_V1,
        PRIMARY_MODEL_V1,
        PRIMARY_PROVIDER_V1,
    )

    assert (PRIMARY_PROVIDER_V1, PRIMARY_MODEL_V1) == ("amax", "qwen3.8-27b")
    assert (
        FALLBACK_PROVIDER_V1,
        FALLBACK_MODEL_V1,
    ) == ("vllm-262k", "Qwen3.6-27B-262K")


def test_registry_is_the_explicit_version_adapter_extension_point() -> None:
    """S2-B-FU1 proof: interpretation requires a REGISTERED, explicitly
    supported version-specific adapter — the registry is a frozen tuple
    of adapters (no mutable global state), currently exactly the V1
    adapter, and fail-closed for every unregistered (envelope version,
    semantic contract) pair."""
    import product_intelligence.research.semantic_decision_codec as codec

    registry = codec._REGISTERED_SEMANTIC_CONTRACT_ADAPTERS
    assert isinstance(registry, tuple)
    assert len(registry) == 1
    from product_intelligence.research import SEMANTIC_V1_ADAPTER

    assert registry[0] is SEMANTIC_V1_ADAPTER
    # The V1 adapter speaks exactly one envelope version and one semantic
    # contract, with exactly one supported binding.
    assert SEMANTIC_V1_ADAPTER.envelope_schema_version == 1
    assert SEMANTIC_V1_ADAPTER.semantic_contract_version == "V1"
    assert SEMANTIC_V1_ADAPTER.supported_bindings == (
        ("V1", "1.1", 1, 1, "SEMANTIC_AUTHORITY_V2_S2A_FU2"),
    )
    # The codec's envelope version constant and the V1 adapter's envelope
    # version cannot drift apart.
    from product_intelligence.research import (
        SEMANTIC_DECISION_SCHEMA_VERSION,
        registered_semantic_contract_adapter,
    )

    assert SEMANTIC_V1_ADAPTER.envelope_schema_version == (
        SEMANTIC_DECISION_SCHEMA_VERSION
    )
    assert (
        registered_semantic_contract_adapter(1, "V1") is SEMANTIC_V1_ADAPTER
    )
    # Fail closed: unknown / future semantic contracts and unknown / future
    # envelope versions have no registered adapter.
    for pair in ((1, "V2"), (1, "V9"), (1, "SEMANTIC_FUTURE"), (2, "V1"),
                 (2, "V2"), (0, "V1")):
        assert registered_semantic_contract_adapter(*pair) is None, pair
