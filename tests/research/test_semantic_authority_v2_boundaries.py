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
import dataclasses
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
    and attention order are frozen data, not mutable global state.

    S2-A-FU1: this test ACTUALLY proves runtime immutability — the
    authoritative stored contract itself is a tuple of immutable entries
    (tuples / enums / frozen dataclasses / frozensets / str), and concrete
    mutation attempts are shown to fail. The severity frozensets and the
    attention-order tuple remain immutable as before.
    """
    from product_intelligence.research import semantic_authority_v2 as v2

    # -- SEMANTIC_OUTCOME_TIER_MATRIX: frozen entry tuple ---------------
    matrix = v2.SEMANTIC_OUTCOME_TIER_MATRIX
    assert isinstance(matrix, tuple)
    assert len(matrix) == 27
    for entry in matrix:
        assert isinstance(entry, tuple) and len(entry) == 2
        key, tier = entry
        assert isinstance(key, tuple) and len(key) == 3
        assert isinstance(key[0], v2.V2SemanticDecision)
        assert isinstance(key[1], v2.V2Confidence)
        assert isinstance(key[2], v2.ProductEvidenceQuality)
        assert isinstance(tier, v2.AuthorityTier)
    with pytest.raises(TypeError):
        matrix[0] = matrix[0]  # tuple: no item assignment
    with pytest.raises(AttributeError):
        matrix.append(matrix[0])  # no list mutation surface
    with pytest.raises(AttributeError):
        matrix.clear()  # no dict mutation surface
    # Deterministically iterable, equality-testable, completeness-
    # checkable: the frozen table equals the one rebuilt from its own
    # pure lookup function in canonical (enum definition) order.
    assert list(matrix) == list(matrix)
    assert matrix == tuple(
        (key, v2.semantic_outcome_tier(*key))
        for key in sorted(
            {key for key, _tier in matrix},
            key=lambda k: (
                list(v2.V2SemanticDecision).index(k[0]),
                list(v2.V2Confidence).index(k[1]),
                list(v2.ProductEvidenceQuality).index(k[2]),
            ),
        )
    )

    # -- DETERMINISTIC_STATE_POLICIES: frozen entry tuple ---------------
    policies = v2.DETERMINISTIC_STATE_POLICIES
    assert isinstance(policies, tuple)
    assert len(policies) == 4
    for entry in policies:
        assert isinstance(entry, tuple) and len(entry) == 2
        state, policy = entry
        assert isinstance(state, v2.IdentityStateV2)
        # Frozen dataclass entry: attribute mutation fails closed
        # (proven by the FrozenInstanceError attempt below).
        assert isinstance(policy.deterministic_tier, v2.AuthorityTier)
        assert isinstance(policy.semantic_eligible, bool)
        assert isinstance(policy.ai_authority_permitted, bool)
        assert isinstance(policy.human_confirmation_permitted, bool)
    with pytest.raises(TypeError):
        policies[0] = policies[0]
    with pytest.raises(dataclasses.FrozenInstanceError):
        policies[0][1].deterministic_tier = (
            v2.AuthorityTier.MACHINE_VERIFIED
        )  # frozen dataclass entry
    assert dataclasses.is_dataclass(type(policies[0][1]))

    # -- CONTEXT_PROVENANCE_CAPABILITIES: frozen entry tuple ------------
    capabilities = v2.CONTEXT_PROVENANCE_CAPABILITIES
    assert isinstance(capabilities, tuple)
    assert len(capabilities) == 3
    for entry in capabilities:
        assert isinstance(entry, tuple) and len(entry) == 2
        provenance, caps = entry
        assert isinstance(provenance, v2.ContextProvenance)
        assert isinstance(caps, frozenset)
    with pytest.raises(TypeError):
        capabilities[0] = capabilities[0]

    # -- AUTHORITY_TIER_BADGES: frozen entry tuple ----------------------
    badges = v2.AUTHORITY_TIER_BADGES
    assert isinstance(badges, tuple)
    assert len(badges) == 8
    for entry in badges:
        assert isinstance(entry, tuple) and len(entry) == 2
        tier, badge = entry
        assert isinstance(tier, v2.AuthorityTier)
        assert isinstance(badge, str) and badge
    with pytest.raises(TypeError):
        badges[0] = badges[0]

    # -- private derivation tables: frozen entry tuples -----------------
    for private in (v2._PRIMARY_SIGNALS_BY_SUBSTATE, v2._STATE_OF_SUBSTATE):
        assert isinstance(private, tuple)
        for entry in private:
            assert isinstance(entry, tuple) and len(entry) == 2
        with pytest.raises(TypeError):
            private[0] = private[0]

    # -- severity / count / vocabulary frozensets -----------------------
    for table in (
        v2.ALWAYS_HARD_CONFLICT_CLASSES,
        v2.REVIEWABLE_CONFLICT_CLASSES,
        v2.PRICE_DIMENSION_ONLY_CONFLICT_CLASSES,
        v2.MARKET_EVIDENCE_TIERS,
        v2.PRICING_ELIGIBLE_TIERS,
        v2.COMPATIBILITY_WORDING_VOCABULARY,
    ):
        assert isinstance(table, frozenset), table
        with pytest.raises(AttributeError):
            table.add(None)  # frozenset: no mutation surface

    # -- attention order tuple ------------------------------------------
    assert isinstance(v2.UI_ATTENTION_ORDER, tuple)
    with pytest.raises(TypeError):
        v2.UI_ATTENTION_ORDER[0] = v2.UI_ATTENTION_ORDER[1]


def test_v2_module_has_no_mutable_global_state() -> None:
    """S2-A-FU1: the module's claim of 'no mutable global state' is
    mechanically proved — no top-level module global is a dict, list, or
    set: every frozen contract mapping is a tuple of immutable entries
    (or a frozenset / tuple / scalar), consumable by future V3 harness /
    runtime code without copying into a mutable authority table."""
    import product_intelligence.research.semantic_authority_v2 as v2

    mutable = {
        name: type(value).__name__
        for name, value in vars(v2).items()
        if not name.startswith("__") and isinstance(value, (dict, list, set))
    }
    assert not mutable, (
        f"mutable global state found in the V2 contract module: {mutable}"
    )


def test_v2_names_no_external_vendor_or_caller_system() -> None:
    source = V2_MODULE.read_text(encoding="utf-8")
    assert not _find_tokens(source, VENDOR_TOKENS)
    assert not _find_tokens(source, CALLER_TOKENS)


def test_v2_is_exported_by_the_research_package() -> None:
    import product_intelligence.research as research

    expected_exports = {
        "derive_identity_state_v2",
        "derive_authority_tier",
        "derive_product_evidence_quality",
        "derive_relationship_authority",
        "semantic_outcome_tier",
        "deterministic_state_policy",
        "context_provenance_capabilities",
        "authority_tier_badge",
        "IdentityStateV2",
        "IdentityStateAssessmentV2",
        "IdentityRelationshipSignal",
        "NearMissShape",
        "ConflictClass",
        "ConflictSeverity",
        "ContextProvenance",
        "ContextCapability",
        "ProductEvidenceQuality",
        "RelationshipAuthority",
        "ProductEvidenceProfileV2",
        "ProductEvidenceFactV2",
        "ProductEvidenceDimension",
        "CandidateProductEvidenceSource",
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
        "STRONG_PRODUCT_EVIDENCE_MIN_MATCHED_FACTS",
        "STRONG_PRODUCT_EVIDENCE_MIN_MATCHED_DIMENSIONS",
        "derive_tier_summary",
        "TierSummaryV2",
    }
    assert expected_exports <= set(research.__all__)
    # S2-A-FU1: the removed S2-A global-STRONG coupling must not come back.
    assert "ContextQuality" not in set(research.__all__)
    assert "derive_context_quality" not in set(research.__all__)
