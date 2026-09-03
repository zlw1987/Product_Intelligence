"""Architecture guards for the web layer (PRODUCT-INTEL.1B).

The dependency arrow points one way. The web layer is allowed to know about
transports, callers, forms, and HTML; the domain, the research core, and the
persistence layer are not allowed to know the web layer exists.

Two further things this phase must not have quietly acquired: all Django
models remain in `runs/` (including `PriceIntelligenceSnapshot`, added in 4B),
and the web layer does not import `providers/`.

Deliberately small. These are targeted checks, not a static-analysis framework.
"""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

# Reused rather than restated, so the lists cannot drift apart.
from tests.domain.test_domain_boundaries import (
    VENDOR_TOKENS,
    _find_tokens,
    _python_files,
    _top_level_imports,
)

REPO_ROOT = Path(__file__).resolve().parents[2]
PACKAGE_ROOT = REPO_ROOT / "product_intelligence"
WEB_ROOT = PACKAGE_ROOT / "web"

# The layers that must stay unaware of the web layer.
INNER_ROOTS = [
    PACKAGE_ROOT / "domain",
    PACKAGE_ROOT / "research",
    PACKAGE_ROOT / "runs",
    PACKAGE_ROOT / "evaluation",
]

# ---------------------------------------------------------------------------
# Shared research-import allowlist (single source of truth)
# ---------------------------------------------------------------------------

ALLOWED_RESEARCH_IMPORTS: dict[str, set[str]] = {
    "product_intelligence.research.price_result_codec": {
        "PriceResultCodecError",
        "decode_price_aggregation_result",
    },
    "product_intelligence.research.aggregation": {
        "PriceAggregationResult",
        "aggregate_reviewed_listing_prices",  # HUMAN-REVIEW: read-side reviewed aggregation
    },
    "product_intelligence.research.matching": {
        "ListingIdentityAssessment",
        "is_human_review_eligible_assessment",  # FU3B authority alignment: binding predicate
    },
}

ALLOWED_EXECUTION_IMPORTS: set[str] = {
    "execute_research_run",
    "ExecutionError",
}


def _research_import_violation(source: str) -> str | None:
    """Return a violation message if *source* imports from research/
    in a way not on the read-side allowlist, or None if it passes.

    This is the single AST policy shared by the real per-file guard and
    the adversarial regression tests.
    """
    tree = ast.parse(source)
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                if alias.name.startswith("product_intelligence.research"):
                    return (
                        f"'import {alias.name}' from research/ is not permitted; "
                        "only 'from ... import ...' with approved symbols is allowed."
                    )
        elif isinstance(node, ast.ImportFrom):
            if not node.module or node.level:
                continue
            if not node.module.startswith("product_intelligence.research"):
                continue
            # Package-level import (via __init__) is not permitted.
            if node.module == "product_intelligence.research":
                return (
                    "from 'product_intelligence.research' import ... is not permitted; "
                    "name the submodule explicitly."
                )
            # research/identity is a research decision primitive.
            if node.module.endswith(".identity"):
                return (
                    "imports from research/identity; "
                    "web layer may not pull in research decision primitives."
                )
            # Check symbol-level allowlist for approved modules.
            if node.module in ALLOWED_RESEARCH_IMPORTS:
                imported_names = {alias.name for alias in node.names}
                excess = imported_names - ALLOWED_RESEARCH_IMPORTS[node.module]
                if excess:
                    return (
                        f"imports from {node.module} include unapproved symbols "
                        f"{sorted(excess)}; allowed: "
                        f"{sorted(ALLOWED_RESEARCH_IMPORTS[node.module])}."
                    )
            else:
                return (
                    f"imports from {node.module!r} which is "
                    "not in the approved research allowlist."
                )
    return None


def _execution_import_violation(source: str) -> str | None:
    """Return a violation message if *source* imports from execution/
    in an unauthorized way, or None if it passes.

    Web layer may import only the public API: execute_research_run, ExecutionError.
    """
    tree = ast.parse(source)
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                if alias.name == "product_intelligence.execution":
                    return (
                        "'import product_intelligence.execution' is not permitted; "
                        "use 'from product_intelligence.execution import ...' with approved symbols."
                    )
                if alias.name.startswith("product_intelligence.execution."):
                    return (
                        f"'import {alias.name}' (execution submodule) is not permitted."
                    )
        elif isinstance(node, ast.ImportFrom):
            if not node.module or node.level:
                continue
            if not node.module.startswith("product_intelligence.execution"):
                continue
            # Package-level import (via __init__) is not permitted.
            if node.module == "product_intelligence.execution":
                imported_names = {alias.name for alias in node.names}
                excess = imported_names - ALLOWED_EXECUTION_IMPORTS
                if excess:
                    return (
                        f"imports from product_intelligence.execution include unapproved symbols "
                        f"{sorted(excess)}; allowed: {sorted(ALLOWED_EXECUTION_IMPORTS)}."
                    )
            # Submodule imports are forbidden
            else:
                return (
                    f"import from {node.module} is not permitted; "
                    "web layer may only import from the public execution API."
                )
    return None


def _imported_modules(path: Path) -> set[str]:
    """Every dotted module name imported by a file, absolute imports only."""
    modules: set[str] = set()
    for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
        if isinstance(node, ast.Import):
            modules.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module and not node.level:
            modules.add(node.module)
    return modules


# ---------------------------------------------------------------------------
# Real-file guards (enforced via parametrization)
# ---------------------------------------------------------------------------

def test_web_package_has_source_files_to_check() -> None:
    """Guard against the scans below silently passing on an empty set."""
    assert _python_files(WEB_ROOT)


@pytest.mark.parametrize(
    "path",
    [path for root in INNER_ROOTS for path in _python_files(root)],
    ids=lambda p: f"{p.parent.name}/{p.name}",
)
def test_the_inner_layers_do_not_import_the_web_layer(path: Path) -> None:
    offending = {
        module
        for module in _imported_modules(path)
        if module.startswith("product_intelligence.web")
    }

    assert not offending, (
        f"{path} imports the web layer {sorted(offending)}; transport and "
        "presentation depend on the core, never the reverse."
    )


def test_the_web_layer_depends_on_the_domain_and_the_run_lifecycle() -> None:
    """The permitted direction, asserted so the guard above cannot pass vacuously."""
    imported = {module for path in _python_files(WEB_ROOT) for module in _imported_modules(path)}

    assert any(module.startswith("product_intelligence.domain") for module in imported)
    assert any(module.startswith("product_intelligence.runs") for module in imported)


def test_the_web_layer_defines_no_model() -> None:
    """Persistence stays in `runs`: a run belongs to no caller (AD-025).

    4B added PriceIntelligenceSnapshot; HUMAN-REVIEW added AiAssistedReviewCandidate.
    All models remain in the persistence package, not here.
    """
    from django.apps import apps

    assert not list(WEB_ROOT.rglob("models.py"))
    assert not list(WEB_ROOT.rglob("migrations"))
    expected = {"runs.ResearchRun", "runs.PriceIntelligenceSnapshot", "runs.ExecutionEvidenceRecord", "runs.AiAssistedReviewCandidate"}
    assert {model._meta.label for model in apps.get_models()} == expected
    assert not apps.get_app_config("web").models


@pytest.mark.parametrize("path", _python_files(WEB_ROOT), ids=lambda p: p.name)
def test_web_names_no_external_vendor(path: Path) -> None:
    found = _find_tokens(path.read_text(encoding="utf-8"), VENDOR_TOKENS)

    assert not found, f"{path.name} references external vendors {found}"


@pytest.mark.parametrize("path", _python_files(WEB_ROOT), ids=lambda p: p.name)
def test_web_uses_only_read_side_research_apis(path: Path) -> None:
    """The web layer may import from research/ only via an explicit
    symbol-level allowlist. Future imports of research execution
    primitives must mechanically fail.

    Approved modules and their allowed symbols:

    * ``price_result_codec`` — PriceResultCodecError, decode_price_aggregation_result
    * ``aggregation`` — PriceAggregationResult
    * ``matching`` — ListingIdentityAssessment, is_human_review_eligible_assessment

    Package-level ``product_intelligence.research`` (via ``__init__``) is banned.
    ``research/identity`` is banned (research decision logic, not display).
    ``import X`` (ast.Import) forms are banned for all research submodules —
    only ``from ... import ...`` with the exact approved symbols is permitted.
    """
    source = path.read_text(encoding="utf-8")
    violation = _research_import_violation(source)
    assert violation is None, f"{path.name}: {violation}"


@pytest.mark.parametrize("path", _python_files(WEB_ROOT), ids=lambda p: p.name)
def test_web_pulls_in_no_provider_or_research_capability(path: Path) -> None:
    """The web shell performs no network access (1B) and does not bypass the
    provider boundary (4B).

    ``views.py`` imports the codec from ``research/`` for the report view
    (4B), and ``presentation.py`` imports research contracts for display.
    Neither touches providers, providers packages, or network libraries.
    """
    modules = _top_level_imports(path.read_text(encoding="utf-8"))
    forbidden = {"requests", "httpx", "urllib3", "socket", "http"}

    assert not modules & forbidden, (
        f"{path.name} imports {sorted(modules & forbidden)}; the web shell "
        "performs no network access of any kind."
    )

    imported = _imported_modules(path)
    assert not any(
        module.startswith("product_intelligence.providers") for module in imported
    ), f"{path.name} imports a provider; web must not import providers."


@pytest.mark.parametrize("path", _python_files(WEB_ROOT), ids=lambda p: p.name)
def test_web_does_not_transition_a_run(path: Path) -> None:
    """Nothing in the shell moves a run out of CREATED, because nothing can.

    A lexical check on purpose: the point is that the *name* does not appear.
    The flow tests prove the behaviour; this makes an accidental "just mark it
    running" fail loudly rather than quietly become a fake progress indicator.
    """
    source = path.read_text(encoding="utf-8")
    assert "transition_to(" not in source, path


@pytest.mark.parametrize("path", _python_files(WEB_ROOT), ids=lambda p: p.name)
def test_execution_import_violation(path: Path) -> None:
    """Web layer may import only execute_research_run and ExecutionError from execution."""
    source = path.read_text(encoding="utf-8")
    violation = _execution_import_violation(source)
    assert violation is None, f"{path.name}: {violation}"


# ---------------------------------------------------------------------------
# Mechanical regressions: ast.Import bypass + symbol allowlist integrity
# ---------------------------------------------------------------------------


def test_guard_rejects_ast_import_bypass() -> None:
    """import X as codec form must be rejected — it bypasses the symbol
    allowlist."""
    assert _research_import_violation(
        "import product_intelligence.research.price_result_codec as codec"
    ) is not None


def test_guard_rejects_unapproved_symbol_from_approved_module() -> None:
    """from approved module import unapproved symbol must be rejected."""
    assert _research_import_violation(
        "from product_intelligence.research.price_result_codec import "
        "encode_price_aggregation_result"
    ) is not None


def test_guard_rejects_unapproved_function_from_aggregation() -> None:
    """Importing aggregate_listing_prices (execution primitive) must fail."""
    assert _research_import_violation(
        "from product_intelligence.research.aggregation import "
        "aggregate_listing_prices"
    ) is not None


def test_guard_allows_approved_imports() -> None:
    """All three approved ImportFrom pairs must pass."""
    source = """\
from product_intelligence.research.price_result_codec import (
    PriceResultCodecError,
    decode_price_aggregation_result,
)
from product_intelligence.research.aggregation import PriceAggregationResult
from product_intelligence.research.matching import ListingIdentityAssessment
"""
    assert _research_import_violation(source) is None


# ---------------------------------------------------------------------------
# Execution API guards
# ---------------------------------------------------------------------------


def test_guard_allows_execution_api_import() -> None:
    """Web layer may import execute_research_run and ExecutionError."""
    source = """\
from product_intelligence.execution import (
    execute_research_run,
    ExecutionError,
)
"""
    assert _execution_import_violation(source) is None


def test_guard_rejects_execution_submodule_import() -> None:
    """Web layer may not import execution internals."""
    source = "from product_intelligence.execution.orchestration import something"
    assert _execution_import_violation(source) is not None


def test_guard_rejects_execution_package_import() -> None:
    """Web layer may not 'import product_intelligence.execution'."""
    source = "import product_intelligence.execution"
    assert _execution_import_violation(source) is not None


def test_guard_rejects_execution_result_import() -> None:
    """Web layer may not import ExecutionResult (not needed by web)."""
    source = "from product_intelligence.execution import ExecutionResult"
    assert _execution_import_violation(source) is not None


def test_guard_rejects_provider_import() -> None:
    """Web layer may not import providers."""
    source = "from product_intelligence.providers.serper import SerperSearchProvider"
    tree = ast.parse(source)
    modules = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and node.module:
            modules.add(node.module)
    assert any(m.startswith("product_intelligence.providers") for m in modules)


# ---------------------------------------------------------------------------
# Runs import guard (4C-C)
# ---------------------------------------------------------------------------

# Web layer is allowed to import:
#   from product_intelligence.runs import <public symbols>
# But MUST NOT import any runs/ submodules directly:
#   from product_intelligence.runs.<submodule> import ...
# (except models -- but only through the public package, not directly)

ALLOWED_RUNS_SUBMODULES: frozenset[str] = frozenset()  # none - all submodule imports forbidden

FORBIDDEN_RUNS_SUBMODULE_PATTERN = "product_intelligence.runs."


def _runs_import_violation(source: str) -> str | None:
    """Check if source imports runs submodules that web layer may not use.

    Web layer may import from 'product_intelligence.runs' (the package, via its
    public __init__ lazy-loading API), but MUST NOT import directly from any
    runs/ submodule other than models.py for the existing approved read/persistence
    symbols.

    Allowed direct imports from runs.models:
      ResearchRun, PriceIntelligenceSnapshot (for exception catching via .DoesNotExist),
      AiAssistedReviewCandidate (HUMAN-REVIEW)

    Forbidden: from product_intelligence.runs.execution_claims import ...
               from product_intelligence.runs.errors import ...
               any other runs.internal submodule
    """
    tree = ast.parse(source)
    ALLOWED_MODELS_IMPORTS = frozenset({"ResearchRun", "PriceIntelligenceSnapshot", "AiAssistedReviewCandidate"})
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom):
            if not node.module or node.level:
                continue
            if node.module == "product_intelligence.runs.models":
                # Direct from runs.models - only allow specific approved symbols
                imported = {alias.name for alias in node.names}
                excess = imported - ALLOWED_MODELS_IMPORTS
                if excess:
                    return (
                        f"imports from product_intelligence.runs.models include "
                        f"unapproved symbols {sorted(excess)}; allowed: "
                        f"{sorted(ALLOWED_MODELS_IMPORTS)}."
                    )
            elif node.module.startswith(FORBIDDEN_RUNS_SUBMODULE_PATTERN):
                # Any other runs.submodule import is forbidden
                return (
                    f"imports from {node.module!r} which is a runs internal "
                    "submodule; web layer must use the product_intelligence.runs "
                    "public package API instead."
                )
    return None


@pytest.mark.parametrize("path", _python_files(WEB_ROOT), ids=lambda p: p.name)
def test_web_runs_import_guard(path: Path) -> None:
    """Web layer may import product_intelligence.runs but not its internals."""
    source = path.read_text(encoding="utf-8")
    violation = _runs_import_violation(source)
    assert violation is None, f"{path.name}: {violation}"


def test_guard_rejects_runs_execution_claims_import() -> None:
    """Web layer may not import product_intelligence.runs.execution_claims directly."""
    source = "from product_intelligence.runs.execution_claims import retry_run"
    assert _runs_import_violation(source) is not None


def test_guard_rejects_runs_models_with_unapproved_symbols() -> None:
    """Web layer may not import unapproved symbols from product_intelligence.runs.models."""
    source = "from product_intelligence.runs.models import ExecutionEvidenceRecord"
    assert _runs_import_violation(source) is not None


def test_guard_allows_runs_models_approved_symbols() -> None:
    """Web layer may import ResearchRun and PriceIntelligenceSnapshot from runs.models."""
    source = "from product_intelligence.runs.models import ResearchRun, PriceIntelligenceSnapshot, AiAssistedReviewCandidate"
    assert _runs_import_violation(source) is None


def test_guard_allows_runs_public_package_import() -> None:
    """Web layer may import from product_intelligence.runs public API."""
    source = """\
from product_intelligence.runs import (
    ClaimExecutionFailed,
    retry_run,
    ResearchRun,
)
"""
    assert _runs_import_violation(source) is None