"""Architecture guards for the web layer (PRODUCT-INTEL.1B).

The dependency arrow points one way. The web layer is allowed to know about
transports, callers, forms, and HTML; the domain, the research core, and the
persistence layer are not allowed to know the web layer exists. A view imported
by a model is how a "quick fix" turns a caller-independent core into a
web application.

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
    },
    "product_intelligence.research.matching": {
        "ListingIdentityAssessment",
    },
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


def _imported_modules(path: Path) -> set[str]:
    """Every dotted module name imported by a file, absolute imports only."""
    modules: set[str] = set()
    for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
        if isinstance(node, ast.Import):
            modules.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module and not node.level:
            modules.add(node.module)
    return modules


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

    4B added PriceIntelligenceSnapshot to `runs/`, so two models now exist —
    still both in the persistence package, not here.
    """
    from django.apps import apps

    assert not list(WEB_ROOT.rglob("models.py"))
    assert not list(WEB_ROOT.rglob("migrations"))
    expected = {"runs.ResearchRun", "runs.PriceIntelligenceSnapshot"}
    assert {model._meta.label for model in apps.get_models()} == expected
    assert not apps.get_app_config("web").models


@pytest.mark.parametrize("path", _python_files(WEB_ROOT), ids=lambda p: p.name)
def test_the_web_layer_names_no_external_vendor(path: Path) -> None:
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
    * ``matching`` — ListingIdentityAssessment

    Package-level ``product_intelligence.research`` (via ``__init__``) is banned.
    ``research/identity`` is banned (research decision logic, not display).
    ``import X`` (ast.Import) forms are banned for all research submodules —
    only ``from ... import ...`` with the exact approved symbols is permitted.
    """
    source = path.read_text(encoding="utf-8")
    violation = _research_import_violation(source)
    assert violation is None, f"{path.name}: {violation}"


@pytest.mark.parametrize("path", _python_files(WEB_ROOT), ids=lambda p: p.name)
def test_the_web_layer_pulls_in_no_provider_or_research_capability(path: Path) -> None:
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


def test_the_web_layer_does_not_transition_a_run() -> None:
    """Nothing in the shell moves a run out of CREATED, because nothing can.

    A lexical check on purpose: the point is that the *name* does not appear.
    The flow tests prove the behaviour; this makes an accidental "just mark it
    running" fail loudly rather than quietly become a fake progress indicator.
    """
    for path in _python_files(WEB_ROOT):
        source = path.read_text(encoding="utf-8")
        assert "transition_to(" not in source, path


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
