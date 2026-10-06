"""Architecture guards for the S2-A Semantic Authority Contract V2 module.

``product_intelligence/research/semantic_authority_v2.py`` is a bounded pure
contract module. These guards enforce, mechanically:

* it imports only stdlib, the domain contracts, and the frozen research
  sub-modules it derives from (identity / matching / listings);
* it imports no persistence, provider, benchmark, web, execution, semantic,
  or network/file I/O module;
* it computes no arithmetic (no price or number is minted here);
* its contract tables are immutable data (no mutable global state);
* it references no external vendor or calling-system token.

Together with the auto-expanded research-core scans in
``test_research_identity_boundaries.py`` and the no-wiring tests in
``test_semantic_authority_v2.py``, these guards prove S2-A is contract-only.
"""

from __future__ import annotations

import ast
import sys
from pathlib import Path

from tests.domain.test_domain_boundaries import (
    CALLER_TOKENS,
    VENDOR_TOKENS,
    _find_tokens,
)

REPO_ROOT = Path(__file__).resolve().parents[2]
PACKAGE_ROOT = REPO_ROOT / "product_intelligence"
RESEARCH_ROOT = PACKAGE_ROOT / "research"
V2_MODULE = RESEARCH_ROOT / "semantic_authority_v2.py"


def test_the_v2_contract_module_exists_and_is_nonempty() -> None:
    assert V2_MODULE.exists()
    assert V2_MODULE.read_text(encoding="utf-8").strip()


def test_v2_imports_only_authorized_modules() -> None:
    """stdlib + product_intelligence (domain / research) only."""
    tree = ast.parse(V2_MODULE.read_text(encoding="utf-8"))
    imported: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module and not node.level:
            imported.add(node.module)

    disallowed = set()
    for module in imported:
        top = module.split(".")[0]
        if top == "product_intelligence":
            continue
        if top in sys.stdlib_module_names:
            continue
        if top.startswith("_"):
            continue
        disallowed.add(module)

    assert not disallowed, f"semantic_authority_v2.py imports {sorted(disallowed)}"


def test_v2_imports_no_persistence_provider_web_benchmark_execution_or_semantic() -> None:
    tree = ast.parse(V2_MODULE.read_text(encoding="utf-8"))
    imported: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module and not node.level:
            imported.add(node.module)

    for forbidden in (
        "django",
        "product_intelligence.runs",
        "product_intelligence.providers",
        "product_intelligence.evaluation",
        "product_intelligence.web",
        "product_intelligence.execution",
        "product_intelligence.semantic",
    ):
        offending = {
            module
            for module in imported
            if module == forbidden or module.startswith(f"{forbidden}.")
        }
        assert not offending, f"semantic_authority_v2.py imports {sorted(offending)}"


def test_v2_imports_no_network_or_file_io() -> None:
    """The contract module computes over values it is handed and reaches
    nothing: no network stack, no filesystem, no subprocess, no clock."""
    tree = ast.parse(V2_MODULE.read_text(encoding="utf-8"))
    imported: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module and not node.level:
            imported.add(node.module)

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
        "datetime",
    }
    offending = {
        module
        for module in imported
        for name in forbidden
        if module == name or module.startswith(f"{name}.")
    }
    assert not offending, (
        f"semantic_authority_v2.py imports I/O modules {sorted(offending)}; "
        "the pure contract performs no I/O and no clock reads"
    )


def test_v2_computes_no_arithmetic() -> None:
    """Authority derivation is vocabulary application, not number work."""
    tree = ast.parse(V2_MODULE.read_text(encoding="utf-8"))
    imported: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module and not node.level:
            imported.add(node.module)

    forbidden = {"decimal", "statistics", "math", "fractions", "numbers"}
    offending = imported & forbidden
    assert not offending, (
        f"semantic_authority_v2.py imports arithmetic modules "
        f"{sorted(offending)}"
    )


def test_v2_uses_only_authorized_research_submodules() -> None:
    """The derivation may read the frozen 2A comparator (identity) and the
    frozen 3C assessment contract (matching) and the observation it carries
    (listings) — nothing else in the research core."""
    tree = ast.parse(V2_MODULE.read_text(encoding="utf-8"))
    imported: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and node.module and not node.level:
            imported.add(node.module)

    research_imports = {
        module for module in imported if module.startswith("product_intelligence.research.")
    }
    allowed = {
        "product_intelligence.research.identity",
        "product_intelligence.research.listings",
        "product_intelligence.research.matching",
    }
    unexpected = research_imports - allowed
    assert not unexpected, (
        f"semantic_authority_v2.py imports unexpected research submodules "
        f"{sorted(unexpected)}; allowed: {sorted(allowed)}"
    )


def test_v2_contract_tables_are_immutable_data() -> None:
    """The matrix, policies, severity sets, capability table, badge map,
    and attention order are frozen data, not mutable global state."""
    from product_intelligence.research import semantic_authority_v2 as v2

    assert isinstance(v2.SEMANTIC_OUTCOME_TIER_MATRIX, dict)
    for key, value in v2.SEMANTIC_OUTCOME_TIER_MATRIX.items():
        assert isinstance(key, tuple) and len(key) == 3
        assert isinstance(value, v2.AuthorityTier)

    assert len(v2.DETERMINISTIC_STATE_POLICIES) == 4
    for state, policy in v2.DETERMINISTIC_STATE_POLICIES.items():
        assert isinstance(state, v2.IdentityStateV2)
        assert isinstance(policy.deterministic_tier, v2.AuthorityTier)
        assert isinstance(policy.semantic_eligible, bool)
        assert isinstance(policy.ai_authority_permitted, bool)
        assert isinstance(policy.human_confirmation_permitted, bool)

    for table in (
        v2.ALWAYS_HARD_CONFLICT_CLASSES,
        v2.REVIEWABLE_CONFLICT_CLASSES,
        v2.PRICE_DIMENSION_ONLY_CONFLICT_CLASSES,
        v2.MARKET_EVIDENCE_TIERS,
        v2.PRICING_ELIGIBLE_TIERS,
        v2.COMPATIBILITY_WORDING_VOCABULARY,
    ):
        assert isinstance(table, frozenset), table

    assert isinstance(v2.CONTEXT_PROVENANCE_CAPABILITIES, dict)
    for provenance, capabilities in v2.CONTEXT_PROVENANCE_CAPABILITIES.items():
        assert isinstance(provenance, v2.ContextProvenance)
        assert isinstance(capabilities, frozenset)

    assert isinstance(v2.UI_ATTENTION_ORDER, tuple)
    assert isinstance(v2.AUTHORITY_TIER_BADGES, dict)
    for tier, badge in v2.AUTHORITY_TIER_BADGES.items():
        assert isinstance(tier, v2.AuthorityTier)
        assert isinstance(badge, str) and badge


def test_v2_names_no_external_vendor_or_caller_system() -> None:
    source = V2_MODULE.read_text(encoding="utf-8")
    assert not _find_tokens(source, VENDOR_TOKENS)
    assert not _find_tokens(source, CALLER_TOKENS)


def test_v2_is_exported_by_the_research_package() -> None:
    import product_intelligence.research as research

    expected_exports = {
        "derive_identity_state_v2",
        "derive_authority_tier",
        "derive_context_quality",
        "IdentityStateV2",
        "IdentityStateAssessmentV2",
        "IdentityRelationshipSignal",
        "NearMissShape",
        "ConflictClass",
        "ConflictSeverity",
        "ContextProvenance",
        "ContextCapability",
        "ContextQuality",
        "AuthorityTier",
        "SemanticEvaluationV2",
        "AuthorityDecisionV2",
        "DETERMINISTIC_STATE_POLICIES",
        "SEMANTIC_OUTCOME_TIER_MATRIX",
        "ALWAYS_HARD_CONFLICT_CLASSES",
        "REVIEWABLE_CONFLICT_CLASSES",
        "PRICE_DIMENSION_ONLY_CONFLICT_CLASSES",
        "UI_ATTENTION_ORDER",
        "AUTHORITY_TIER_BADGES",
        "derive_tier_summary",
        "TierSummaryV2",
    }
    assert expected_exports <= set(research.__all__)
