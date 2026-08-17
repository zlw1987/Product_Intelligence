"""Architecture guards for the web layer (PRODUCT-INTEL.1B).

The dependency arrow points one way. The web layer is allowed to know about
transports, callers, forms, and HTML; the domain, the research core, and the
persistence layer are not allowed to know the web layer exists. A view imported
by a model is how a "quick fix" turns a caller-independent core into a
web application.

Two further things this phase must not have quietly acquired: a second model
(persistence stays in `runs`), and a provider dependency (1B added no search or
LLM capability, and could not have).

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
    """Persistence stays in `runs`: a run belongs to no caller (AD-025)."""
    from django.apps import apps

    assert not list(WEB_ROOT.rglob("models.py"))
    assert not list(WEB_ROOT.rglob("migrations"))
    assert {model._meta.label for model in apps.get_models()} == {"runs.ResearchRun"}
    assert not apps.get_app_config("web").models


@pytest.mark.parametrize("path", _python_files(WEB_ROOT), ids=lambda p: p.name)
def test_the_web_layer_names_no_external_vendor(path: Path) -> None:
    found = _find_tokens(path.read_text(encoding="utf-8"), VENDOR_TOKENS)

    assert not found, f"{path.name} references external vendors {found}"


@pytest.mark.parametrize("path", _python_files(WEB_ROOT), ids=lambda p: p.name)
def test_the_web_layer_pulls_in_no_provider_or_research_capability(path: Path) -> None:
    """1B added no search, no LLM, and no engine — including transitively."""
    modules = _top_level_imports(path.read_text(encoding="utf-8"))
    forbidden = {"requests", "httpx", "urllib3", "socket", "http"}

    assert not modules & forbidden, (
        f"{path.name} imports {sorted(modules & forbidden)}; the web shell "
        "performs no network access of any kind."
    )

    imported = _imported_modules(path)
    assert not any(
        module.startswith("product_intelligence.providers") for module in imported
    ), f"{path.name} imports a provider; none exists, and 1B adds none."


def test_the_web_layer_does_not_transition_a_run() -> None:
    """Nothing in the shell moves a run out of CREATED, because nothing can.

    A lexical check on purpose: the point is that the *name* does not appear.
    The flow tests prove the behaviour; this makes an accidental "just mark it
    running" fail loudly rather than quietly become a fake progress indicator.
    """
    for path in _python_files(WEB_ROOT):
        source = path.read_text(encoding="utf-8")
        assert "transition_to(" not in source, path
