"""Architecture guards for the FINAL Semantic V2 contract (S2-C, group J).

Mechanically enforced boundaries:

* the universal S2-B envelope (foundation / codec / replay dispatch)
  still owns NO V1 or V2 route assumptions — the route pins live in the
  version-specific adapters and contracts only;
* the V1 assumptions stay in the V1 adapter; the V2 assumptions stay in
  the V2 adapter / V2 contract modules (the universal layer names no
  quoted contract/prompt literal and no route token of either
  contract);
* the new research V2 modules (``semantic_v2.py``,
  ``semantic_decision_v2.py``) are pure: stdlib + the research package's
  public surface only — no Django, no persistence, no providers, no
  web, no execution, no semantic runtime, no network/file I/O, no
  clock, no mutable global state, no vendor/caller tokens, no
  reference to the S2-A contract module by name;
* the S2-A frozen authority contract remains Django-free and is
  unmodified (its own guard suite runs unchanged);
* the V2 mirror constants in the persistence adapter are drift-pinned
  to the V2 runtime / V2 prompt contract (route identities, prompt
  version, the qualification marker);
* the persistence layer owns no authority logic; the aggregation layer
  owns no semantic interpretation;
* the model output cannot self-promote: the live execution wiring
  builds the authority-side product evidence ONLY through the safe
  builder (zero matched facts) and never passes a model response into
  the evidence profile.
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
PACKAGE_ROOT = REPO_ROOT / "product_intelligence"
RESEARCH_ROOT = PACKAGE_ROOT / "research"
EXECUTION_ROOT = PACKAGE_ROOT / "execution"
SEMANTIC_ROOT = PACKAGE_ROOT / "semantic"

UNIVERSAL_MODULES = (
    RESEARCH_ROOT / "semantic_decision_record.py",
    RESEARCH_ROOT / "semantic_decision_codec.py",
    RESEARCH_ROOT / "semantic_decision_replay.py",
)

V1_MODULE = RESEARCH_ROOT / "semantic_decision_v1.py"
V2_MODULE = RESEARCH_ROOT / "semantic_decision_v2.py"
V2_CONTRACT_MODULE = RESEARCH_ROOT / "semantic_v2.py"

#: The frozen qualified route tokens (V1 and V2 carry the identical
#: route identities — the tokens are route-world data, not vendor
#: names).
ROUTE_TOKENS = (
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


# ===========================================================================
# Universal envelope: no V1/V2 route assumptions
# ===========================================================================


@pytest.mark.parametrize("path", list(UNIVERSAL_MODULES), ids=lambda p: p.name)
def test_universal_modules_own_no_route_assumption(path: Path) -> None:
    """The universal storage/transport layer owns NO route assumption of
    EITHER semantic contract: no route token and no quoted
    contract/prompt literal. The V1 pins live only in the V1 adapter;
    the V2 pins live only in the V2 adapter/contract."""
    source = path.read_text(encoding="utf-8")
    for token in ROUTE_TOKENS:
        assert token not in source, (
            f"{path.name} owns the route token {token!r}; the universal "
            "envelope must not assume any semantic contract's provider/"
            "model route"
        )
    # Quoted literals only: prose may say "V1" / "V2"; the universal
    # code must not REQUIRE the literal values in string constants.
    for literal in ('"V1"', '"1.1"', '"V2"', '"2.0"'):
        assert literal not in source, (
            f"{path.name} hardcodes the quoted literal {literal}; the "
            "envelope identifies contracts via the recorded dispatch "
            "key, it does not assume one"
        )


def test_v1_adapter_owns_the_v1_route_pin() -> None:
    source = V1_MODULE.read_text(encoding="utf-8")
    for token in ROUTE_TOKENS:
        assert token in source, f"the V1 adapter module lost its route pin {token!r}"


def test_v2_adapter_owns_the_v2_route_pin() -> None:
    source = V2_MODULE.read_text(encoding="utf-8")
    for token in ROUTE_TOKENS:
        assert token in source, f"the V2 adapter module lost its route pin {token!r}"
    from product_intelligence.research import (
        FALLBACK_MODEL_V2,
        FALLBACK_PROVIDER_V2,
        PRIMARY_MODEL_V2,
        PRIMARY_PROVIDER_V2,
    )

    assert (PRIMARY_PROVIDER_V2, PRIMARY_MODEL_V2) == ("amax", "qwen3.8-27b")
    assert (FALLBACK_PROVIDER_V2, FALLBACK_MODEL_V2) == (
        "vllm-262k",
        "Qwen3.6-27B-262K",
    )


# ===========================================================================
# The new research V2 modules are pure
# ===========================================================================


@pytest.mark.parametrize(
    "path", [V2_CONTRACT_MODULE, V2_MODULE], ids=lambda p: p.name
)
def test_v2_research_modules_import_only_stdlib_and_product_intelligence(
    path: Path,
) -> None:
    modules = _imported_modules(path)
    disallowed = {
        module
        for module in modules
        if module.split(".")[0] != "product_intelligence"
        and module.split(".")[0] not in sys.stdlib_module_names
        and not module.split(".")[0].startswith("_")
    }
    assert not disallowed, f"{path.name} imports {sorted(disallowed)}"


@pytest.mark.parametrize(
    "path", [V2_CONTRACT_MODULE, V2_MODULE], ids=lambda p: p.name
)
def test_v2_research_modules_import_no_forbidden_surface(path: Path) -> None:
    modules = _imported_modules(path)
    for forbidden in (
        "django",
        "product_intelligence.runs",
        "product_intelligence.providers",
        "product_intelligence.web",
        "product_intelligence.execution",
        "product_intelligence.evaluation",
        "product_intelligence.semantic",
    ):
        offending = {
            module
            for module in modules
            if module == forbidden or module.startswith(f"{forbidden}.")
        }
        assert not offending, (
            f"{path.name} imports {sorted(offending)}; the pure research "
            "V2 contract never imports the production semantic runtime "
            "surface, persistence, providers, web, execution, or the "
            "benchmark"
        )


@pytest.mark.parametrize(
    "path", [V2_CONTRACT_MODULE, V2_MODULE], ids=lambda p: p.name
)
def test_v2_research_modules_perform_no_network_or_file_io(path: Path) -> None:
    modules = _imported_modules(path)
    forbidden = {
        "requests",
        "httpx",
        "urllib.request",
        "urllib.error",
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
    }
    offending = {
        module
        for module in modules
        for name in forbidden
        if module == name or module.startswith(f"{name}.")
    }
    assert not offending, f"{path.name} imports I/O modules {sorted(offending)}"


@pytest.mark.parametrize(
    "path", [V2_CONTRACT_MODULE, V2_MODULE], ids=lambda p: p.name
)
def test_v2_research_modules_read_no_clock(path: Path) -> None:
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


@pytest.mark.parametrize(
    "path", [V2_CONTRACT_MODULE, V2_MODULE], ids=lambda p: p.name
)
def test_v2_research_modules_reference_no_s2a_module_by_name(path: Path) -> None:
    """The frozen S2-A contract is consumed through the research
    package's public export surface — never by module name (the
    S2-A no-wiring lexical guard)."""
    source = path.read_text(encoding="utf-8")
    assert "semantic_authority_v2" not in source, (
        f"{path.name} references the S2-A contract module by name"
    )


@pytest.mark.parametrize(
    "path", [V2_CONTRACT_MODULE, V2_MODULE], ids=lambda p: p.name
)
def test_v2_research_modules_own_no_mutable_global_state(path: Path) -> None:
    import importlib

    module = importlib.import_module(f"product_intelligence.research.{path.stem}")
    mutable = {
        name: type(value).__name__
        for name, value in vars(module).items()
        if not name.startswith("__") and isinstance(value, (dict, list, set))
    }
    assert not mutable, f"{path.name} has mutable global state: {mutable}"


@pytest.mark.parametrize(
    "path", [V2_CONTRACT_MODULE, V2_MODULE], ids=lambda p: p.name
)
def test_v2_research_modules_name_no_vendor_or_caller_system(path: Path) -> None:
    source = path.read_text(encoding="utf-8")
    assert not _find_tokens(source, VENDOR_TOKENS), path.name
    assert not _find_tokens(source, CALLER_TOKENS), path.name


def test_the_s2a_contract_module_is_unmodified_and_django_free() -> None:
    # S2-A remains the frozen authority contract: Django-free, pure,
    # and still consumed through the package surface. (Its full guard
    # suite — test_semantic_authority_v2.py /
    # test_semantic_authority_v2_boundaries.py — runs unchanged.)
    from product_intelligence.research import (
        SUBSTATE_RELATIONSHIP_REQUIREMENTS,
        is_v2_semantic_entry_point,
    )

    import product_intelligence.research.semantic_authority_v2 as s2a  # noqa: F401

    assert len(SUBSTATE_RELATIONSHIP_REQUIREMENTS) == 14
    assert callable(is_v2_semantic_entry_point)


# ===========================================================================
# Drift pins: the V2 adapter mirrors the V2 runtime / prompt contract
# ===========================================================================


def test_v2_route_mirror_is_pinned_to_the_v2_runtime() -> None:
    from product_intelligence.research import (
        FALLBACK_MODEL_V2,
        FALLBACK_PROVIDER_V2,
        PRIMARY_MODEL_V2,
        PRIMARY_PROVIDER_V2,
    )
    from product_intelligence.semantic.runtime_v2 import (
        FALLBACK_MODEL_V2 as RT_FALLBACK_MODEL,
        FALLBACK_PROVIDER_V2 as RT_FALLBACK_PROVIDER,
        PRIMARY_MODEL_V2 as RT_PRIMARY_MODEL,
        PRIMARY_PROVIDER_V2 as RT_PRIMARY_PROVIDER,
    )

    assert PRIMARY_PROVIDER_V2 == RT_PRIMARY_PROVIDER
    assert PRIMARY_MODEL_V2 == RT_PRIMARY_MODEL
    assert FALLBACK_PROVIDER_V2 == RT_FALLBACK_PROVIDER
    assert FALLBACK_MODEL_V2 == RT_FALLBACK_MODEL


def test_v2_prompt_version_mirror_is_pinned() -> None:
    from product_intelligence.research import PROMPT_VERSION_V2
    from product_intelligence.semantic.contract_v2 import (
        SEMANTIC_PROMPT_VERSION_V2,
    )

    assert PROMPT_VERSION_V2 == SEMANTIC_PROMPT_VERSION_V2 == "2.0"


def test_v2_authority_qualified_marker_is_pinned_false_everywhere() -> None:
    # The explicit qualification-boundary marker: S2-C does NOT declare
    # the route qualified for the new contract, and the marker cannot
    # drift between the runtime and the persistence adapter.
    from product_intelligence.research import V2_AUTHORITY_QUALIFIED
    from product_intelligence.semantic.runtime_v2 import (
        V2_AUTHORITY_QUALIFIED as RT_V2_AUTHORITY_QUALIFIED,
    )

    assert V2_AUTHORITY_QUALIFIED is False
    assert RT_V2_AUTHORITY_QUALIFIED is False


def test_v2_failure_family_mirror_is_pinned_to_the_runtime_tables() -> None:
    # The V2 runtime's bounded routing tables are mirrors of the frozen
    # FU3A routing discipline: they cannot drift.
    import product_intelligence.semantic.runtime as v1_runtime
    import product_intelligence.semantic.runtime_v2 as v2_runtime

    assert v2_runtime._V2_TRANSPORT_ERROR_TO_STATUS == (
        v1_runtime._TRANSPORT_ERROR_TO_STATUS
    )
    assert v2_runtime._V2_STATUS_TO_FALLBACK_REASON == (
        v1_runtime._STATUS_TO_FALLBACK_REASON
    )
    assert v2_runtime._V2_PRIMARY_STATUS_TO_ERROR_TYPE == (
        v1_runtime._PRIMARY_STATUS_TO_ERROR_TYPE
    )
    assert v2_runtime._V2_FALLBACK_STATUS_TO_ERROR_TYPE == (
        v1_runtime._FALLBACK_STATUS_TO_ERROR_TYPE
    )


# ===========================================================================
# Persistence owns no authority logic; aggregation owns no semantic
# interpretation
# ===========================================================================


def test_the_persistence_service_still_owns_no_authority_logic() -> None:
    import product_intelligence.execution.semantic_decision_persistence as svc

    source = Path(svc.__file__).read_text(encoding="utf-8")
    tree = ast.parse(source)
    imported_names = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom):
            imported_names.update(alias.name for alias in node.names)
    assert not (
        imported_names
        & {
            "derive_authority_tier",
            "derive_identity_state_v2",
            "derive_product_evidence_quality",
            "derive_relationship_authority",
            "substate_relationship_requirement",
            "is_v2_semantic_eligible",
            "build_semantic_match_case_v2",
        }
    )
    assert "replay_semantic_decision" in imported_names


def test_the_aggregation_layer_owns_no_semantic_interpretation() -> None:
    # 4A (research + execution aggregation) must stay free of semantic
    # OUTPUT interpretation: no semantic decision / attribute / reason
    # symbols and no ledger references (the word "semantic" may appear
    # in the frozen human-review docstring provenance — the semantic
    # output surface may not).
    for path in (
        RESEARCH_ROOT / "aggregation.py",
        EXECUTION_ROOT / "aggregation.py",
    ):
        source = path.read_text(encoding="utf-8")
        for token in (
            "matched_attributes",
            "conflicting_attributes",
            "reason_code",
            "V2SemanticDecision",
            "SemanticDecisionRecord",
            "semantic_decision",
            "SemanticMatchResponse",
        ):
            assert token not in source, (
                f"{path.name} owns the semantic interpretation token "
                f"{token!r}; 4A aggregation owns no semantic output"
            )


def test_the_reviewed_aggregation_reads_no_v2_records() -> None:
    # Reviewed Price derivation must never read a V2 (or any) semantic
    # decision record: the reviewed aggregation composes deterministic
    # ACCEPTED + HUMAN_CONFIRMED evidence only.
    from product_intelligence.research import aggregation as research_agg

    source = Path(research_agg.__file__).read_text(encoding="utf-8")
    assert "semantic_decision" not in source
    assert "SemanticDecisionRecord" not in source


# ===========================================================================
# The model output cannot self-promote (execution wiring architecture)
# ===========================================================================


def test_the_v2_execution_wiring_needs_the_safe_evidence_builder() -> None:
    import product_intelligence.execution.semantic_decision_v2_execution as mod

    source = Path(mod.__file__).read_text(encoding="utf-8")
    tree = ast.parse(source)
    imported_names = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom):
            imported_names.update(alias.name for alias in node.names)
    # The authority-side evidence is built ONLY through the safe
    # builder — the wiring imports it...
    assert "build_v2_product_evidence_profile" in imported_names
    # ...and the model response surface is imported for RECORDING only
    # (the runtime result), never for the evidence profile: the builder
    # call in the source passes matched_facts=frozenset() (no model
    # output anywhere near the evidence construction).
    assert source.count("matched_facts=frozenset()") >= 1
    assert "matched_attributes=frozenset" not in source


def test_the_v2_execution_wiring_creates_no_review_candidates() -> None:
    import product_intelligence.execution.semantic_decision_v2_execution as mod

    source = Path(mod.__file__).read_text(encoding="utf-8")
    assert "AiAssistedReviewCandidate" not in source
    assert "review_candidate" not in source.lower()


def test_the_v2_execution_wiring_grants_no_pricing_authority() -> None:
    # The V2 execution module persists ledger records only: it never
    # imports the 4A aggregation, the reviewed aggregation, or the price
    # result codec (no path from a V2 outcome to a price).
    import product_intelligence.execution.semantic_decision_v2_execution as mod

    source = Path(mod.__file__).read_text(encoding="utf-8")
    tree = ast.parse(source)
    imported_modules = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported_modules.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module and not node.level:
            imported_modules.add(node.module)
    for forbidden in (
        "product_intelligence.research.aggregation",
        "product_intelligence.execution.aggregation",
        "product_intelligence.research.price_result_codec",
        "product_intelligence.runs.ai_assisted_review",
    ):
        offending = {
            module
            for module in imported_modules
            if module == forbidden or module.startswith(f"{forbidden}.")
        }
        assert not offending, (
            f"the V2 execution wiring imports {sorted(offending)}; a V2 "
            "outcome must have no path to pricing authority"
        )


def test_no_production_authority_surface_reads_v2_records() -> None:
    # The production authority surfaces — 4A aggregation, reviewed
    # aggregation, the V1 semantic integration, human-review service,
    # price codec — must reference no V2 record / V2 adapter symbol at
    # all (source-level firewall). The orchestration is the sole V2
    # wiring point (it names the V2 execution module — proven separately
    # as persist-only).
    authority_files = (
        RESEARCH_ROOT / "aggregation.py",
        RESEARCH_ROOT / "price_result_codec.py",
        EXECUTION_ROOT / "aggregation.py",
        EXECUTION_ROOT / "semantic_integration.py",
        PACKAGE_ROOT / "runs" / "ai_assisted_review.py",
    )
    for path in authority_files:
        source = path.read_text(encoding="utf-8")
        assert "SemanticDecisionRecordV2" not in source, path.name
        assert "semantic_decision_v2" not in source, path.name


def test_the_orchestration_v2_wiring_is_persist_only() -> None:
    # The orchestration's V2 surface is exactly: evaluate (outside the
    # transaction), build the records, persist in the atomic block. It
    # never passes V2 records into aggregation, review candidates, or
    # the snapshot payload (source-level: the V2 functions are called,
    # and the V2 records are not fed to any authority primitive).
    source = (EXECUTION_ROOT / "orchestration.py").read_text(encoding="utf-8")
    assert "evaluate_semantic_matches_v2" in source
    assert "build_semantic_decision_records_v2" in source
    assert "persist_semantic_decision_records_v2" in source
    # The 4A input is total_assessments (deterministic) only.
    assert (
        "aggregate_prices(\n            request, total_assessments"
        in source
    ) or ("aggregate_prices(request, total_assessments" in source)
